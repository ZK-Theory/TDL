# Research context: TDA-Research/00-Meta/Discovery/pl-time-resolved-transition-graphs-prereg-2026-07-10.md
# Purpose: LOCKED confirmatory battery — persistent-Laplacian Fiedler structure on
#   TIME-RESOLVED employment transition graphs. Primary statistic Var_t(IFA_t)
#   across eligible waves; both substrates; wave floor 500 transitions; two-sided
#   test; BH-FDR across the 2 substrates. Null: Markov-1 parametric bootstrap
#   fitted to the POOLED counts (stationary), B=1000, seed 42, per-draw seeds 42+b.
#
#   DESIGN ORIGIN (do not undo): this battery descends from the C1 post-mortem.
#   C1 tested IFA on the AGGREGATE transition graph against a Markov-1 null fitted
#   to the same aggregate counts — the statistic was a deterministic function of
#   the null's own sufficient statistic, so the null was structurally centered on
#   the observed value and could not reject (permanent note
#   Markov-k-null-cannot-reject-statistics-of-the-order-k-sufficient-statistic).
#   Var_t(IFA_t) is a function of the PER-WAVE count matrices, which the pooled
#   matrix does not determine. Any change that collapses the statistic back to a
#   function of the aggregate count matrix reintroduces the defect this design
#   exists to avoid.
"""Time-resolved persistent-Laplacian battery (pre-registration LOCKED 2026-07-10).

Usage::

    # Feasibility benchmark + invariance/centering audit (required first):
    uv run --no-sync --env-file .env python trajectory_tda/scripts/run_pl_time_resolved_battery.py --audit-only

    # Full locked battery:
    uv run --no-sync --env-file .env python trajectory_tda/scripts/run_pl_time_resolved_battery.py

Outputs:
    WORKTREE/results/trajectory_tda_bhps/pl_time_resolved_<date>.json   (committed)
    PROJ_ROOT/results/trajectory_tda_bhps/pl_checkpoints/<...>.npz      (gitignored)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr

from trajectory_tda.scripts.c1_pl_fiedler_null_battery import (
    build_counts_from_idx,
    estimate_markov1,
    markov1_synthetic_idx,
)
from trajectory_tda.topology.persistent_laplacian import (
    build_undirected_graph,
    compute_fiedler_curve,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pl_time_resolved_battery")

_TRAPZ = getattr(np, "trapezoid", np.trapz)

# ── Two-path output roots (APM two-path rule) ────────────────────────────────

PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", r"C:\Users\steph\TDL"))
WORKTREE = Path(__file__).resolve().parent.parent.parent

# ── LOCKED parameters (pre-reg pl-time-resolved-transition-graphs-prereg-2026-07-10) ──

SCHEMA_VERSION = "pl-time-resolved/v1"
B_LOCKED = 1000
SEED = 42
ALPHA = 0.05
NULL_MODEL = "markov-1-pooled"
WAVE_FLOOR = 500
MIN_ELIGIBLE_WAVES = 5
REDUNDANCY_GATE = 0.95

STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}
N_STATES = len(STATES)

SUBSTRATES: dict[str, dict[str, str]] = {
    "bhps": {
        "sequences": "results/trajectory_tda_bhps/01_trajectories_sequences.json",
        "sha256": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
    },
    "integration": {
        "sequences": "results/trajectory_tda_integration/01_trajectories_sequences.json",
        "sha256": "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8",
    },
}

RESULT_DIR = WORKTREE / "results/trajectory_tda_bhps"
CHECKPOINT_DIR = PROJ_ROOT / "results/trajectory_tda_bhps/pl_checkpoints"


# ── Input resolution + provenance ────────────────────────────────────────────


def _resolve_input(relpath: str) -> Path:
    """Resolve an input that may be committed (worktree) or gitignored (PROJ_ROOT)."""
    for root in (WORKTREE, PROJ_ROOT):
        candidate = root / relpath
        if candidate.is_file():
            return candidate
    raise SystemExit(f"STOP: input not found at WORKTREE or PROJ_ROOT: {relpath}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_substrate(substrate: str) -> tuple[list[list[str]], str, Path]:
    """Load one substrate's sequences and verify its locked sha256."""
    spec = SUBSTRATES[substrate]
    path = _resolve_input(spec["sequences"])
    sha = _sha256(path)
    if sha != spec["sha256"]:
        raise SystemExit(f"STOP: {substrate} substrate sha256 mismatch\n  expected {spec['sha256']}\n  got      {sha}")
    sequences = json.loads(path.read_text())
    logger.info("[%s] substrate OK: %d trajectories (sha256 verified)", substrate, len(sequences))
    return sequences, sha, path


# ── Time-resolved transition graphs ──────────────────────────────────────────


def per_wave_counts(seqs_idx: list[NDArray[np.int64]], n_waves: int) -> list[NDArray[np.int64]]:
    """Per-wave 9x9 transition-count matrices C_t (wave position t -> t+1).

    A trajectory contributes to wave ``t`` only when it is observed at both ``t``
    and ``t+1`` (i.e. ``len(seq) > t + 1``).

    Args:
        seqs_idx: Per-trajectory integer state-index arrays.
        n_waves: Number of wave positions to build (``max_length - 1``).

    Returns:
        List of ``n_waves`` count matrices.
    """
    mats = [np.zeros((N_STATES, N_STATES), dtype=np.int64) for _ in range(n_waves)]
    for seq in seqs_idx:
        for t in range(min(len(seq) - 1, n_waves)):
            mats[t][seq[t], seq[t + 1]] += 1
    return mats


def eligible_wave_indices(mats: list[NDArray[np.int64]]) -> list[int]:
    """Wave indices whose transition count meets the locked floor of 500."""
    return [t for t, c in enumerate(mats) if int(c.sum()) >= WAVE_FLOOR]


def grid_sha256(grid: list[float]) -> str:
    """Stable digest of the threshold grid, used to prove observed/null grid identity."""
    return hashlib.sha256(json.dumps(grid).encode()).hexdigest()


def build_fixed_grid(mats: list[NDArray[np.int64]], waves: list[int]) -> list[float]:
    """The ONE locked global grid: sorted union of finite off-diagonal distances.

    Built from the eligible OBSERVED per-wave graphs only, then reused unchanged
    for every null draw (pre-registration: "identical grid for observed and every
    null draw").
    """
    values: set[float] = set()
    for t in waves:
        D = build_undirected_graph(mats[t])
        for i in range(N_STATES):
            for j in range(i + 1, N_STATES):
                if np.isfinite(D[i, j]):
                    values.add(float(D[i, j]))
    return sorted(values)


def ifa_for_wave(counts: NDArray[np.int64], grid: list[float]) -> float:
    """IFA_t: trapezoid integral of the per-wave Fiedler curve on the fixed grid."""
    D = build_undirected_graph(counts)
    curve = compute_fiedler_curve(D, thresholds=grid, backend="auto", include_inactive=True)
    lambda1 = np.asarray(curve["lambda1"], dtype=np.float64)
    return float(_TRAPZ(lambda1, np.asarray(grid, dtype=np.float64)))


def spectral_gap(counts: NDArray[np.int64]) -> float:
    """1 - |lambda_2| of the row-normalised transition matrix (C1/Spike 5' baseline)."""
    p = counts.astype(np.float64)
    row = p.sum(axis=1, keepdims=True)
    row[row == 0] = 1.0
    p /= row
    eig = np.sort(np.abs(np.linalg.eigvals(p)))[::-1]
    return float(1.0 - eig[1])


def transition_entropy(counts: NDArray[np.int64]) -> float:
    """Entropy (nats) of the normalised transition-frequency matrix."""
    q = counts.astype(np.float64)
    total = q.sum()
    if total == 0:
        return float("nan")
    q /= total
    nz = q[q > 0]
    return float(-(nz * np.log(nz)).sum())


def wave_statistics(
    mats: list[NDArray[np.int64]],
    waves: list[int],
    grid: list[float],
) -> tuple[NDArray[np.float64], float, float, float]:
    """Per-wave IFA vector plus the three Var_t summaries.

    Returns:
        Tuple ``(ifa_t, var_ifa, var_gap, var_entropy)``. Variances are population
        variances (ddof=0) across the eligible waves.
    """
    ifa_t = np.array([ifa_for_wave(mats[t], grid) for t in waves], dtype=np.float64)
    gaps = np.array([spectral_gap(mats[t]) for t in waves], dtype=np.float64)
    ents = np.array([transition_entropy(mats[t]) for t in waves], dtype=np.float64)
    return ifa_t, float(np.var(ifa_t)), float(np.var(gaps)), float(np.var(ents))


# ── Module-level globals for worker processes ────────────────────────────────

_TM: NDArray[np.float64] | None = None
_INIT: NDArray[np.float64] | None = None
_LENGTHS: list[int] | None = None
_GRID: list[float] | None = None
_WAVES: list[int] | None = None
_N_WAVES: int | None = None
_POOLED_OBS: NDArray[np.int64] | None = None


def _init_worker(tm, init_probs, lengths, grid, waves, n_waves, pooled_obs) -> None:
    global _TM, _INIT, _LENGTHS, _GRID, _WAVES, _N_WAVES, _POOLED_OBS
    _TM, _INIT, _LENGTHS, _GRID = tm, init_probs, lengths, grid
    _WAVES, _N_WAVES, _POOLED_OBS = waves, n_waves, pooled_obs


def one_null_draw(b: int) -> dict[str, Any]:
    """One stationary Markov-1 parametric-bootstrap draw.

    Synthetic trajectories match the observed lengths exactly, so the per-wave
    sample sizes — and therefore the eligible wave set — are identical to the
    observed ones by construction. Only the transition structure varies.
    """
    rng = np.random.RandomState(SEED + b)
    synth = markov1_synthetic_idx(_TM, _INIT, _LENGTHS, rng)
    mats = per_wave_counts(synth, _N_WAVES)
    ifa_t, var_ifa, var_gap, var_ent = wave_statistics(mats, _WAVES, _GRID)
    return {
        "b": b,
        "var_ifa": var_ifa,
        "var_gap": var_gap,
        "var_entropy": var_ent,
        "ifa_len": int(ifa_t.size),
        "pooled_counts_differ": bool(not np.array_equal(build_counts_from_idx(synth), _POOLED_OBS)),
        # Digest of the grid this worker actually integrated over. The parent
        # asserts every draw reports the observed grid's digest, so the locked
        # "identical grid for observed and every null draw" clause is evidenced
        # by the run rather than merely asserted by construction.
        "grid_sha256": grid_sha256(_GRID),
    }


# ── BH-FDR + locked decision rule ────────────────────────────────────────────


def bh_adjust(p_values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Benjamini-Hochberg adjusted p-values (step-up, monotonised, capped at 1)."""
    p = np.asarray(p_values, dtype=np.float64)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.minimum(adjusted, 1.0)
    out = np.empty_like(adjusted)
    out[order] = adjusted
    return out


def classify_verdict(rows: list[dict[str, Any]]) -> tuple[str, str]:
    """Locked decision rule of the 2026-07-10 pre-registration.

    ADDITIVE: p_two (BH-FDR) <= 0.05 on BOTH substrates AND both redundancy gates
    pass on both substrates.
    PARTIAL-SIGNAL: rejection on exactly one substrate, gates passing there.
    REDUNDANT: rejections occur but a redundancy gate fails wherever rejection
    occurs (the residual rejecting case).
    NEGATIVE: no rejection after FDR.

    Raises:
        SystemExit: If the rows do not cover exactly the two locked substrates. Every
            branch of the locked rule is defined over BOTH substrates ("on BOTH", "on
            exactly one"), so a partial row set has no defined verdict — and on a
            single row ``all(rejects)`` would vacuously return ADDITIVE off one
            substrate, which the rule never permits.
    """
    seen = [r["substrate"] for r in rows]
    if sorted(seen) != sorted(SUBSTRATES):
        raise SystemExit(
            f"STOP: the locked decision rule is defined over both substrates {sorted(SUBSTRATES)}, "
            f"but this run covers {sorted(seen)}. A single-substrate run has no pre-registered verdict; "
            "use --dry-run or --audit-only for exploratory single-substrate work."
        )

    rejects = [r["rejects_fdr"] for r in rows]
    gates = [r["redundancy_gates_pass"] for r in rows]

    if not any(rejects):
        return "negative", "No substrate rejects after BH-FDR."
    if all(rejects) and all(gates):
        return "additive", "Both substrates reject after BH-FDR with both redundancy gates passing on both."
    if sum(rejects) == 1:
        idx = rejects.index(True)
        if gates[idx]:
            return (
                "partial-signal",
                f"Rejection on exactly one substrate ({rows[idx]['substrate']}) with both redundancy gates passing there.",
            )
    return (
        "redundant",
        "BH-FDR rejections occur but a redundancy gate fails wherever rejection occurs.",
    )


# ── Battery for one substrate ────────────────────────────────────────────────


def run_substrate(
    substrate: str,
    sequences: list[list[str]],
    n_draws: int,
    workers: int,
    checkpoint_interval: int,
    wall_deadline: float,
    audit_only: bool,
) -> dict[str, Any]:
    """Run the locked time-resolved PL battery for one substrate."""
    seqs_idx = [np.asarray([STATE_TO_IDX[s] for s in seq], dtype=np.int64) for seq in sequences]
    lengths = [len(s) for s in sequences]
    n_waves = max(lengths) - 1

    mats = per_wave_counts(seqs_idx, n_waves)
    per_wave_totals = [int(c.sum()) for c in mats]
    waves = eligible_wave_indices(mats)

    logger.info("[%s] %d wave positions; per-wave transitions %s", substrate, n_waves, per_wave_totals)
    logger.info("[%s] eligible waves (>= %d transitions): %s", substrate, WAVE_FLOOR, waves)

    # Gate 0 (locked): fewer than 5 eligible waves -> INFEASIBLE, escalate.
    if len(waves) < MIN_ELIGIBLE_WAVES:
        raise SystemExit(
            f"STOP (Gate 0): {substrate} has only {len(waves)} eligible waves (< {MIN_ELIGIBLE_WAVES}). "
            "The pre-registration marks this substrate INFEASIBLE — escalate, do not improvise."
        )

    grid = build_fixed_grid(mats, waves)
    grid_sha = grid_sha256(grid)
    logger.info("[%s] fixed threshold grid: %d values (sha256 %s)", substrate, len(grid), grid_sha[:12])

    t_obs = time.perf_counter()
    ifa_t, obs_var_ifa, obs_var_gap, obs_var_ent = wave_statistics(mats, waves, grid)
    obs_seconds = time.perf_counter() - t_obs
    logger.info(
        "[%s] observed Var_t(IFA_t)=%.6e (IFA_t over %d waves, %.1fs) gap_var=%.3e ent_var=%.3e",
        substrate,
        obs_var_ifa,
        len(waves),
        obs_seconds,
        obs_var_gap,
        obs_var_ent,
    )

    pooled = build_counts_from_idx(seqs_idx)
    tm, init_probs, fit_lengths = estimate_markov1(sequences)
    _init_worker(tm, init_probs, fit_lengths, grid, waves, n_waves, pooled)

    # ── Invariance / centering audit on draw 0 ────────────────────────────────
    t_draw = time.perf_counter()
    probe = one_null_draw(0)
    draw_seconds = time.perf_counter() - t_draw
    if probe["ifa_len"] != len(waves):
        raise SystemExit(f"STOP: {substrate} null draw IFA length {probe['ifa_len']} != observed {len(waves)}.")
    if not probe["pooled_counts_differ"]:
        raise SystemExit(f"STOP: {substrate} null draw reproduced the observed pooled counts exactly — null invariant.")
    logger.info(
        "[%s] invariance pre-check OK (draw 0: Var_t(IFA_t)=%.6e, %.1fs/draw)",
        substrate,
        probe["var_ifa"],
        draw_seconds,
    )

    # Project against the LOCKED B even in audit mode — the point of the benchmark is
    # to size the real battery, not the audit that measures it.
    projected_h = draw_seconds * B_LOCKED / max(workers, 1) / 3600
    logger.info(
        "[%s] benchmark %.2fs/draw -> projected LOCKED battery (B=%d) at %d workers: %.2f h",
        substrate,
        draw_seconds,
        B_LOCKED,
        workers,
        projected_h,
    )
    if projected_h > 12:
        raise SystemExit(
            f"STOP: {substrate} projects {projected_h:.1f} h for a single launch (> 12 h). "
            f"Measured {draw_seconds:.2f}s/draw x {B_LOCKED} draws / {workers} workers. Escalate with these numbers."
        )
    if projected_h > 2:
        logger.warning(
            "[%s] projected %.2f h exceeds 2 h — confirm against the pre-registration's 4 h wall-time budget.",
            substrate,
            projected_h,
        )

    var_ifas = np.empty(n_draws)
    var_gaps = np.empty(n_draws)
    var_ents = np.empty(n_draws)

    ckpt_path = CHECKPOINT_DIR / f"pl_time_resolved_{substrate}_B{n_draws}_seed{SEED}.npz"
    t0 = time.perf_counter()
    null_grid_shas: set[str] = {probe["grid_sha256"]}
    null_ifa_lengths: set[int] = {probe["ifa_len"]}
    initargs = (tm, init_probs, fit_lengths, grid, waves, n_waves, pooled)
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=initargs) as pool:
        for start in range(0, n_draws, checkpoint_interval):
            if time.perf_counter() > wall_deadline:
                raise SystemExit(f"STOP: wall-time limit reached during {substrate} at draw {start}.")
            end = min(start + checkpoint_interval, n_draws)
            for r in pool.map(one_null_draw, range(start, end)):
                var_ifas[r["b"]] = r["var_ifa"]
                var_gaps[r["b"]] = r["var_gap"]
                var_ents[r["b"]] = r["var_entropy"]
                null_grid_shas.add(r["grid_sha256"])
                null_ifa_lengths.add(r["ifa_len"])

            CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
            np.savez(
                ckpt_path, var_ifas=var_ifas[:end], var_gaps=var_gaps[:end], var_ents=var_ents[:end], completed=end
            )
            logger.info(
                "[%s] %d/%d draws (%.0fs) — checkpoint %s",
                substrate,
                end,
                n_draws,
                time.perf_counter() - t0,
                ckpt_path.name,
            )

    elapsed = time.perf_counter() - t0

    # Locked clause: "identical grid for observed and every null draw". Every draw
    # reports the digest of the grid it integrated over; they must all equal the
    # observed grid's digest, and every draw must yield one IFA per eligible wave.
    if null_grid_shas != {grid_sha}:
        raise SystemExit(
            f"STOP: {substrate} null draws did not all use the observed threshold grid "
            f"(observed sha {grid_sha[:12]}, draw shas {[s[:12] for s in sorted(null_grid_shas)]})."
        )
    if null_ifa_lengths != {len(waves)}:
        raise SystemExit(f"STOP: {substrate} null IFA vector lengths {sorted(null_ifa_lengths)} != {len(waves)}.")

    null_mean = float(var_ifas.mean())
    null_std = float(var_ifas.std())
    percentile = float(np.mean(var_ifas < obs_var_ifa) * 100)
    if null_std == 0.0:
        raise SystemExit(f"STOP: {substrate} null Var_t(IFA_t) distribution is degenerate (std=0).")

    p_upper = float((1 + np.sum(var_ifas >= obs_var_ifa)) / (1 + n_draws))
    p_lower = float((1 + np.sum(var_ifas <= obs_var_ifa)) / (1 + n_draws))
    p_two = float(min(1.0, 2.0 * min(p_lower, p_upper)))

    rows_ifa = np.append(var_ifas, obs_var_ifa)
    rho_gap_var = float(spearmanr(rows_ifa, np.append(var_gaps, obs_var_gap)).statistic)
    rho_entropy_var = float(spearmanr(rows_ifa, np.append(var_ents, obs_var_ent)).statistic)

    logger.info(
        "[%s] p_lower=%.4f p_upper=%.4f p_two=%.4f rho_gap=%.3f rho_ent=%.3f (null %.3e+-%.3e, obs pct %.1f) %.0fs",
        substrate,
        p_lower,
        p_upper,
        p_two,
        rho_gap_var,
        rho_entropy_var,
        null_mean,
        null_std,
        percentile,
        elapsed,
    )

    return {
        "substrate": substrate,
        "n_waves_total": n_waves,
        "per_wave_transition_counts": per_wave_totals,
        "eligible_waves": waves,
        "eligible_wave_transition_counts": [per_wave_totals[t] for t in waves],
        "excluded_waves": [
            {"wave_index": t, "transitions": per_wave_totals[t], "reason": f"below the locked floor of {WAVE_FLOOR}"}
            for t in range(n_waves)
            if t not in waves
        ],
        "grid_length": len(grid),
        "grid_sha256": grid_sha,
        "observed_ifa_t": ifa_t.tolist(),
        "observed_var_ifa": obs_var_ifa,
        "observed_var_gap": obs_var_gap,
        "observed_var_entropy": obs_var_ent,
        "null_var_ifa_draws": var_ifas.tolist(),
        "null_grid_sha256": grid_sha,
        "null_mean": null_mean,
        "null_std": null_std,
        "observed_percentile_of_null": percentile,
        "p_lower": p_lower,
        "p_upper": p_upper,
        "p_two": p_two,
        "rho_gap_var": rho_gap_var,
        "rho_entropy_var": rho_entropy_var,
        "redundancy_gates_pass": bool(abs(rho_gap_var) < REDUNDANCY_GATE and abs(rho_entropy_var) < REDUNDANCY_GATE),
        "null_invariance_audit": {
            "draw_0_ifa_length_matches_observed": True,
            "draw_0_pooled_counts_differ_from_observed": bool(probe["pooled_counts_differ"]),
            "draw_0_var_ifa": float(probe["var_ifa"]),
            "grid_identical_across_observed_and_null": True,
            "seconds_per_draw": round(draw_seconds, 2),
            "centering_argument": (
                "The null is a Markov-1 parametric bootstrap fitted to the POOLED counts, so it is centered on the "
                "pooled transition-count matrix. Var_t(IFA_t) is a function of the PER-WAVE count matrices, which the "
                "pooled matrix does not determine (the pooled matrix is their sum; a sum does not fix the dispersion of "
                "its summands). The statistic is therefore NOT a function of the null's sufficient statistic, which is "
                "exactly the defect that made the C1 stationary design unrejectable. Empirical confirmation: the "
                "observed percentile reported here is not pinned to the null centre."
            ),
        },
        "elapsed_seconds": round(elapsed, 1),
        "audit_only": audit_only,
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Time-resolved PL battery (LOCKED 2026-07-10)")
    parser.add_argument("--B", type=int, default=B_LOCKED, help="bootstrap draws (pre-registered 1000)")
    parser.add_argument("--workers", type=int, default=4, help="worker processes (locked convention: >= 4)")
    parser.add_argument("--checkpoint-interval", type=int, default=100, help="checkpoint cadence")
    parser.add_argument("--wall-time-hours", type=float, default=4.0, help="wall-time flag (pre-reg: 4h)")
    parser.add_argument("--audit-only", action="store_true", help="benchmark + invariance audit at small B, then stop")
    parser.add_argument("--audit-draws", type=int, default=20, help="draws for --audit-only")
    parser.add_argument(
        "--substrate",
        choices=["bhps", "integration", "all"],
        default="all",
        help=(
            "Substrates to run (default: all). A single substrate has NO pre-registered verdict — the locked rule "
            "is defined over both — so pair it with --dry-run/--audit-only; a single-substrate result write is refused."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="run fully but do not write the dated result file")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.workers < 4:
        raise SystemExit("STOP: workers must be >= 4 (locked convention).")
    if not args.audit_only and args.B != B_LOCKED:
        raise SystemExit(f"STOP: B={args.B} != pre-registered {B_LOCKED}. The pre-registration is normative.")

    t_start = time.perf_counter()
    wall_deadline = t_start + args.wall_time_hours * 3600
    n_draws = args.audit_draws if args.audit_only else args.B
    targets = list(SUBSTRATES) if args.substrate == "all" else [args.substrate]

    substrate_sha256: dict[str, str] = {}
    input_paths: dict[str, str] = {}
    rows: list[dict[str, Any]] = []

    for substrate in targets:
        sequences, sha, path = _load_substrate(substrate)
        substrate_sha256[substrate] = sha
        # Repository-relative identifier, never the machine-local absolute path: the
        # committed artifact must not carry a local username/worktree layout, and
        # provenance is pinned by substrate_sha256 above.
        input_paths[substrate] = SUBSTRATES[substrate]["sequences"]
        rows.append(
            run_substrate(
                substrate=substrate,
                sequences=sequences,
                n_draws=n_draws,
                workers=args.workers,
                checkpoint_interval=args.checkpoint_interval,
                wall_deadline=wall_deadline,
                audit_only=args.audit_only,
            )
        )

    p_twos = np.array([r["p_two"] for r in rows], dtype=np.float64)
    p_fdr = bh_adjust(p_twos)
    for row, adj in zip(rows, p_fdr):
        row["p_fdr"] = float(adj)
        row["rejects_fdr"] = bool(adj <= ALPHA)

    verdict, rationale = classify_verdict(rows)
    elapsed = time.perf_counter() - t_start

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "substrate_sha256": substrate_sha256,
        "params": {
            "B": n_draws,
            "seed": SEED,
            "null_model": NULL_MODEL,
            "wave_floor": WAVE_FLOOR,
            "per_draw_seeds": "42+b",
            "alpha": ALPHA,
            "fdr_method": "benjamini-hochberg",
            "n_tests": len(rows),
            "redundancy_gate": REDUNDANCY_GATE,
            "test_direction": "two-sided; p_two = min(1, 2*min(p_lower, p_upper))",
            "variance_ddof": 0,
            "parallel_workers": args.workers,
            "checkpoint_interval": args.checkpoint_interval,
            "wall_time_hours": args.wall_time_hours,
            "wall_time_seconds": round(elapsed, 1),
        },
        "eligible_waves": {
            r["substrate"]: dict(zip(map(str, r["eligible_waves"]), r["eligible_wave_transition_counts"])) for r in rows
        },
        "observed": {
            r["substrate"]: {
                "ifa_t": r["observed_ifa_t"],
                "var_ifa": r["observed_var_ifa"],
                "grid_length": r["grid_length"],
                "grid_sha256": r["grid_sha256"],
            }
            for r in rows
        },
        "null_distribution": {
            r["substrate"]: {
                "var_ifa_draws": r["null_var_ifa_draws"],
                "grid_sha256": r["null_grid_sha256"],
                "null_mean": r["null_mean"],
                "null_std": r["null_std"],
                "p_lower": r["p_lower"],
                "p_upper": r["p_upper"],
                "p_two": r["p_two"],
                "p_fdr": r["p_fdr"],
            }
            for r in rows
        },
        "redundancy": {
            r["substrate"]: {"rho_gap_var": r["rho_gap_var"], "rho_entropy_var": r["rho_entropy_var"]} for r in rows
        },
        "substrates": rows,
        "decision": {"verdict": verdict, "rationale": rationale},
        "provenance": {
            "pre_registration": "vault/00-Meta/Discovery/pl-time-resolved-transition-graphs-prereg-2026-07-10.md",
            "pre_registration_status": "LOCKED 2026-07-10",
            "input_paths": input_paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    logger.info("VERDICT: %s — %s", verdict.upper(), rationale)

    if args.dry_run or args.audit_only:
        logger.info("audit-only/dry-run: no dated result file written (%.0fs)", elapsed)
        return

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULT_DIR / f"pl_time_resolved_{date.today().isoformat()}.json"
    if out_path.exists():
        raise SystemExit(f"STOP: results file already exists, never overwrite: {out_path}")
    out_path.write_text(json.dumps(payload, indent=2))
    logger.info("wrote %s (%.0fs total)", out_path, elapsed)


if __name__ == "__main__":
    main()
