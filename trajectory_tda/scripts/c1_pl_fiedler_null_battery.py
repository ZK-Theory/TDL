# Research context: TDA-Research/00-Meta/Discovery/c1-persistent-laplacian-dispatch-prereg-draft-2026-07-03.md
# Purpose: T-C1-1 — persistent-Laplacian non-harmonic spectrum (Fiedler curve lambda1(t))
#   of the observed BHPS 9-state employment-state transition graph vs a Markov-1 null
#   (B=1000). Primary statistic: Integrated Fiedler Area (IFA), one-sided permutation
#   p-value. Secondary: pointwise lambda1(t) comparison at each of the 35 filtration
#   thresholds with Benjamini-Hochberg FDR (alpha=0.05). Emits the date-suffixed result
#   JSON validated by contracts/discovery-harness/c1-pl-fiedler-null-result.yaml.
#
# Locked design: results/trajectory_tda_bhps/pre_registrations_2026-07-07.json (T-C1-1).
# Null construction: Markov-1 shuffle — estimate the first-order transition matrix and
#   initial-state distribution from all 8509 observed trajectories, generate synthetic
#   trajectories of matching lengths, rebuild the 9x9 count matrix and float32 distance
#   matrix from the SYNTHETIC trajectories, then compute the 35-step Fiedler curve on
#   that null graph (a rebuild, NOT a shuffle of a cached scalar or of D itself).
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from joblib import Parallel, delayed
from numpy.typing import NDArray

from trajectory_tda.topology.persistent_laplacian import (
    PETLS_AVAILABLE,
    PETLS_BACKEND_NAME,
    build_undirected_graph,
    compute_fiedler_curve,
)

# ── Paths (two-path rule) ────────────────────────────────────────────────────
WORKTREE = Path(__file__).resolve().parents[2]
# PROJ_ROOT is the project-canonical intermediates root (two-path rule). Default is the
# locked Windows path; TDL_PROJ_ROOT overrides it so checkpoint writes/--resume stay
# valid on other hosts (matches the run_*.py scripts in this package).
PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", r"C:\Users\steph\TDL"))
SEQ_PATH = WORKTREE / "results/trajectory_tda_bhps/01_trajectories_sequences.json"
PRE_REGISTRATION = "results/trajectory_tda_bhps/pre_registrations_2026-07-07.json"
EXPECTED_SHA256 = "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490"
CHECKPOINT_PATH = PROJ_ROOT / "results/trajectory_tda_bhps/c1_pl_fiedler_null_checkpoint.npz"

STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}
N_STATES = len(STATES)

_TRAPZ = getattr(np, "trapezoid", np.trapz)


# ── Transition-graph construction (index space) ──────────────────────────────
def build_counts_from_idx(seqs: list[NDArray[np.int64]]) -> NDArray[np.int64]:
    """Directed 9x9 transition-count matrix from integer state-index sequences."""
    C = np.zeros((N_STATES, N_STATES), dtype=np.int64)
    for seq in seqs:
        if len(seq) < 2:
            continue
        np.add.at(C, (seq[:-1], seq[1:]), 1)
    return C


def build_counts_from_str(seqs: list[list[str]]) -> NDArray[np.int64]:
    """Directed 9x9 transition-count matrix from string state sequences (observed)."""
    C = np.zeros((N_STATES, N_STATES), dtype=np.int64)
    for seq in seqs:
        for a, b in zip(seq[:-1], seq[1:]):
            if a in STATE_TO_IDX and b in STATE_TO_IDX:
                C[STATE_TO_IDX[a], STATE_TO_IDX[b]] += 1
    return C


# ── Markov-1 estimation (once) and synthetic generation (per draw) ───────────
def estimate_markov1(
    seqs: list[list[str]],
) -> tuple[NDArray[np.float64], NDArray[np.float64], list[int]]:
    """First-order transition matrix, initial-state distribution, and lengths.

    Same estimation approach as trajectory_tda/topology/permutation_nulls.py
    _markov_shuffle(order=1); estimated once (deterministic, RNG-free) and reused
    across draws — identical to per-draw re-estimation but avoids re-scanning all
    8509 trajectories B times.
    """
    tm = np.zeros((N_STATES, N_STATES), dtype=np.float64)
    init_counts = np.zeros(N_STATES, dtype=np.float64)
    lengths: list[int] = []
    for seq in seqs:
        lengths.append(len(seq))
        if len(seq) == 0:
            continue
        s0 = STATE_TO_IDX.get(seq[0])
        if s0 is not None:
            init_counts[s0] += 1
        for t in range(len(seq) - 1):
            i, j = STATE_TO_IDX.get(seq[t]), STATE_TO_IDX.get(seq[t + 1])
            if i is not None and j is not None:
                tm[i, j] += 1
    row_sums = tm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    tm /= row_sums
    init_probs = init_counts / init_counts.sum() if init_counts.sum() > 0 else np.ones(N_STATES) / N_STATES
    return tm, init_probs, lengths


def markov1_synthetic_idx(
    tm: NDArray[np.float64],
    init_probs: NDArray[np.float64],
    lengths: list[int],
    rng: np.random.RandomState,
) -> list[NDArray[np.int64]]:
    """Generate synthetic index sequences matching observed lengths (Markov-1)."""
    cum_tm = np.cumsum(tm, axis=1)
    cum_init = np.cumsum(init_probs)
    synthetic: list[NDArray[np.int64]] = []
    for length in lengths:
        if length == 0:
            synthetic.append(np.empty(0, dtype=np.int64))
            continue
        seq = np.empty(length, dtype=np.int64)
        seq[0] = int(np.searchsorted(cum_init, rng.random_sample()))
        for t in range(1, length):
            seq[t] = int(np.searchsorted(cum_tm[seq[t - 1]], rng.random_sample()))
        synthetic.append(seq)
    return synthetic


# ── Module-level globals for loky workers (set in main before dispatch) ──────
_TM: NDArray[np.float64] | None = None
_INIT: NDArray[np.float64] | None = None
_LENGTHS: list[int] | None = None
_THRESHOLDS: list[float] | None = None
_OBSERVED_D: NDArray[np.float32] | None = None


def _init_worker(tm, init_probs, lengths, thresholds, observed_D) -> None:
    global _TM, _INIT, _LENGTHS, _THRESHOLDS, _OBSERVED_D
    _TM, _INIT, _LENGTHS, _THRESHOLDS, _OBSERVED_D = (
        tm,
        init_probs,
        lengths,
        thresholds,
        observed_D,
    )


def one_null_draw(seed: int) -> dict[str, Any]:
    """One Markov-1 null draw on the fixed 35-threshold grid.

    Rebuilds the distance matrix from synthetic trajectories, then evaluates the
    Fiedler curve on the observed grid with include_inactive=True (0.0-padded at
    inactive thresholds) so every draw yields a length-35 vector aligned to the
    observed curve.
    """
    rng = np.random.RandomState(seed)
    synth = markov1_synthetic_idx(_TM, _INIT, _LENGTHS, rng)
    D_null = build_undirected_graph(build_counts_from_idx(synth))
    curve = compute_fiedler_curve(D_null, thresholds=_THRESHOLDS, backend="auto", include_inactive=True)
    lambda1 = np.asarray(curve["lambda1"], dtype=np.float64)
    ifa = float(_TRAPZ(lambda1, np.asarray(_THRESHOLDS, dtype=np.float64)))
    return {
        "ifa": ifa,
        "lambda1": lambda1,
        "distance_matrix_differs": not np.array_equal(D_null, _OBSERVED_D),
    }


# ── Benjamini-Hochberg FDR ───────────────────────────────────────────────────
def bh_fdr_survivor_count(p_values: NDArray[np.float64], alpha: float) -> int:
    """Number of hypotheses surviving Benjamini-Hochberg FDR at level ``alpha``."""
    p = np.asarray(p_values, dtype=np.float64)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    thresh = alpha * (np.arange(1, m + 1) / m)
    below = ranked <= thresh
    if not below.any():
        return 0
    return int(np.max(np.nonzero(below)[0]) + 1)


def classify_verdict(ifa_p_value: float, survivors: int) -> str:
    """Locked decision rule (pre_registrations_2026-07-07.json, T-C1-1)."""
    if ifa_p_value < 0.05 and survivors >= 1:
        return "positive"
    if (ifa_p_value < 0.05 and survivors == 0) or (ifa_p_value >= 0.05 and survivors >= 5):
        return "marginal"
    return "negative"


def main() -> None:
    parser = argparse.ArgumentParser(description="T-C1-1 Fiedler Markov-1 null battery")
    parser.add_argument("--B", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--checkpoint-interval", type=int, default=50)
    parser.add_argument("--wall-time-hours", type=float, default=2.0)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--resume", action="store_true", help="resume from checkpoint if present")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run the full pipeline but do not write the dated result file (smoke test)",
    )
    args = parser.parse_args()

    if args.workers < 4:
        raise SystemExit("parallel_workers must be >= 4 (locked convention)")

    t_start = time.perf_counter()

    # ── Provenance gate ──────────────────────────────────────────────────────
    raw = SEQ_PATH.read_bytes()
    substrate_sha256 = hashlib.sha256(raw).hexdigest()
    if substrate_sha256 != EXPECTED_SHA256:
        raise SystemExit(f"SUBSTRATE VINTAGE MISMATCH — STOP. got {substrate_sha256}, expected {EXPECTED_SHA256}")
    sequences = json.loads(raw)
    print(f"[provenance] SHA-256 OK ({substrate_sha256[:12]}...); n_trajectories={len(sequences)}")
    print(f"[backend] PETLS_AVAILABLE={PETLS_AVAILABLE} name={PETLS_BACKEND_NAME}")

    # ── Observed curve on the fixed 35-threshold grid ────────────────────────
    observed_D = build_undirected_graph(build_counts_from_str(sequences))
    thresholds = sorted(
        {
            float(observed_D[i, j])
            for i in range(N_STATES)
            for j in range(i + 1, N_STATES)
            if np.isfinite(observed_D[i, j])
        }
    )
    obs_curve = compute_fiedler_curve(observed_D, thresholds=thresholds, backend="auto", include_inactive=True)
    backend_used = obs_curve["backend"]
    observed_lambda1 = np.asarray(obs_curve["lambda1"], dtype=np.float64)
    n_thresholds = len(thresholds)
    if n_thresholds != 35 or observed_lambda1.size != 35:
        raise SystemExit(f"expected 35 fixed thresholds; got {n_thresholds} (curve {observed_lambda1.size})")
    observed_ifa = float(_TRAPZ(observed_lambda1, np.asarray(thresholds, dtype=np.float64)))
    print(f"[observed] backend_used={backend_used} IFA={observed_ifa:.6f} n_thresholds={n_thresholds}")

    # ── Markov-1 estimation (once) ───────────────────────────────────────────
    tm, init_probs, lengths = estimate_markov1(sequences)
    # Seed the parent-process globals too, as a safety net for any in-process execution
    # path; the loky workers are initialised authoritatively via the Parallel initializer.
    _init_worker(tm, init_probs, lengths, thresholds, observed_D)

    # ── Battery: batched parallel draws with checkpointing ───────────────────
    ifa_values = np.full(args.B, np.nan, dtype=np.float64)
    lambda1_matrix = np.full((args.B, n_thresholds), np.nan, dtype=np.float64)
    any_differs = False
    start_idx = 0

    if args.resume and CHECKPOINT_PATH.exists():
        ckpt = np.load(CHECKPOINT_PATH)
        done = int(ckpt["completed"])
        ifa_values[:done] = ckpt["ifa_values"][:done]
        lambda1_matrix[:done] = ckpt["lambda1_matrix"][:done]
        any_differs = bool(ckpt["any_differs"])
        start_idx = done
        print(f"[resume] loaded checkpoint at {done}/{args.B} draws")

    wall_limit_s = args.wall_time_hours * 3600.0
    interval = args.checkpoint_interval
    for batch_start in range(start_idx, args.B, interval):
        batch_end = min(batch_start + interval, args.B)
        seeds = [args.seed + i for i in range(batch_start, batch_end)]
        # Wire the null-model state into each loky worker explicitly via the backend
        # initializer, so one_null_draw() sees populated globals regardless of how the
        # module is imported in the child process (do not rely on cloudpickle capturing
        # __main__ globals by value).
        results = Parallel(
            n_jobs=args.workers,
            backend="loky",
            initializer=_init_worker,
            initargs=(tm, init_probs, lengths, thresholds, observed_D),
        )(delayed(one_null_draw)(s) for s in seeds)
        for offset, res in enumerate(results):
            idx = batch_start + offset
            ifa_values[idx] = res["ifa"]
            lambda1_matrix[idx] = res["lambda1"]
            any_differs = any_differs or bool(res["distance_matrix_differs"])
        CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            CHECKPOINT_PATH,
            completed=batch_end,
            ifa_values=ifa_values,
            lambda1_matrix=lambda1_matrix,
            any_differs=any_differs,
        )
        elapsed = time.perf_counter() - t_start
        print(f"[battery] {batch_end}/{args.B} draws  elapsed={elapsed:.1f}s")
        if elapsed > wall_limit_s and batch_end < args.B:
            raise SystemExit(
                f"WALL-TIME EXCEEDED at {batch_end}/{args.B} draws ({elapsed:.0f}s > {wall_limit_s:.0f}s); "
                f"checkpoint saved — rerun with --resume"
            )

    if np.isnan(ifa_values).any():
        raise SystemExit("incomplete battery: NaN IFA values remain")

    # ── Statistics ───────────────────────────────────────────────────────────
    r = int(np.sum(ifa_values >= observed_ifa))
    ifa_p_value = (r + 1) / (args.B + 1)
    # Pointwise: fraction of null draws with lambda1_null(t) >= lambda1_obs(t) (pre-reg def).
    pointwise_p = np.mean(lambda1_matrix >= observed_lambda1[None, :], axis=0)
    survivors = bh_fdr_survivor_count(pointwise_p, args.alpha)
    verdict = classify_verdict(ifa_p_value, survivors)
    null_std = float(np.std(ifa_values))
    null_model_construction_verified = bool(any_differs and null_std > 0.0)

    print(
        f"[result] IFA_obs={observed_ifa:.6f} r={r} IFA_p={ifa_p_value:.6f} "
        f"BH_survivors={survivors}/35 null_std={null_std:.6e} verdict={verdict}"
    )

    payload: dict[str, Any] = {
        "schema_version": "c1-pl-fiedler-null/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": "T-C1-1",
        "pre_registration": PRE_REGISTRATION,
        "substrate_sha256": substrate_sha256,
        "backend_used": backend_used,
        "null_model_construction_verified": null_model_construction_verified,
        "params": {
            "B": args.B,
            "seed": args.seed,
            "null_model": "markov-1",
            "n_filtration_thresholds": n_thresholds,
            "parallel_workers": args.workers,
            "wall_time_hours_budget": args.wall_time_hours,
        },
        "observed": {
            "ifa": observed_ifa,
            "lambda1_curve": observed_lambda1.tolist(),
        },
        "null_distribution": {
            "draws": args.B,
            "ifa_values": ifa_values.tolist(),
            "percentile_95": float(np.percentile(ifa_values, 95)),
        },
        "pointwise": {
            "p_values": pointwise_p.tolist(),
            "bh_fdr_survivors": survivors,
        },
        "decision": {
            "ifa_p_value": ifa_p_value,
            "pointwise_bh_survivors": survivors,
            "verdict": verdict,
        },
    }

    if args.dry_run:
        print("[dry-run] pipeline complete; result file NOT written")
        return

    date_suffix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = WORKTREE / f"results/trajectory_tda_bhps/c1_pl_fiedler_null_{date_suffix}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing result file: {out_path}")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[output] wrote {out_path}")


if __name__ == "__main__":
    main()
