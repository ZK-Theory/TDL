# Research context: TDA-Research/00-Meta/Discovery/sheaf-laplacian-employment-dispatch-prereg-2026-07-10.md
# Purpose: LOCKED confirmatory battery — cellular-sheaf energy over subgroup
#   occupancy stalks on the 9-state employment transition graph, for two group
#   families (parental NS-SEC 3-class; birth-cohort decades with n >= 200) across
#   both substrates (BHPS, integration). Energy is the ONLY tested statistic;
#   sheaf spectra are reported as exploratory descriptives with no p-value.
#   Null: joint (nssec, cohort) label permutation within (length, first-state)
#   strata, B=1000, seed 42, per-draw seeds 42+b. BH-FDR across the 4
#   (family x substrate) tests at alpha=0.05.
"""Sheaf-Laplacian energy confirmatory battery (pre-registration LOCKED 2026-07-10).

Every parameter here is pinned by the pre-registration and its JSON mirror; this
script does not choose any of them. Subgroup membership is rebuilt through the
T1.28 stratification pipeline and verified against the T1.28 subgroup checkpoint
n values (A4 discipline) — a family member whose n cannot be reproduced is marked
MISSING and never substituted.

Usage::

    # Null-invariance / centering audit only (required before the full battery):
    uv run --no-sync --env-file .env python trajectory_tda/scripts/run_sheaf_energy_battery.py --audit-only

    # Full locked battery:
    uv run --no-sync --env-file .env python trajectory_tda/scripts/run_sheaf_energy_battery.py

Outputs:
    WORKTREE/results/trajectory_tda_sheaf/sheaf_laplacian_employment_<date>.json  (committed)
    PROJ_ROOT/results/trajectory_tda_sheaf/checkpoints/<...>.json                 (gitignored)
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
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr

from trajectory_tda.topology.sheaf_laplacian import (
    build_transition_graph,
    occupancy_from_counts,
    per_trajectory_state_counts,
    sheaf_spectrum,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sheaf_energy_battery")

# ── Two-path output roots (APM two-path rule) ────────────────────────────────

PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", r"C:\Users\steph\TDL"))
WORKTREE = Path(__file__).resolve().parent.parent.parent

# ── LOCKED parameters (pre-reg sheaf-laplacian-employment-dispatch-prereg-2026-07-10) ──

SCHEMA_VERSION = "sheaf-laplacian-employment/v1"
B_LOCKED = 1000
SEED = 42
ALPHA = 0.05
NULL_MODEL = "stratified-label-permutation"
REDUNDANCY_GATE = 0.95
COHORT_MIN_N = 200

STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}
N_STATES = len(STATES)

# Substrate registry: substrate key -> (sequences relpath, expected sha256,
# covariate checkpoint dir relpath, T1.28 dataset key).
SUBSTRATES: dict[str, dict[str, str]] = {
    "bhps": {
        "sequences": "results/trajectory_tda_bhps/01_trajectories_sequences.json",
        "sha256": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
        "ckpt_dir": "results/trajectory_tda_bhps",
        "t128_dataset": "bhps",
    },
    "integration": {
        "sequences": "results/trajectory_tda_integration/01_trajectories_sequences.json",
        "sha256": "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8",
        "ckpt_dir": "results/trajectory_tda_integration",
        "t128_dataset": "usoc",
    },
}

# Group families (2), per the locked pre-registration.
NSSEC_LABELS = ["Professional/Managerial", "Intermediate", "Routine/Manual"]
FAMILIES = ["nssec", "cohort"]

T128_CKPT_DIR = PROJ_ROOT / "results/panel_methodology/fdr/subgroup_checkpoints"

RESULT_DIR = WORKTREE / "results/trajectory_tda_sheaf"
CHECKPOINT_DIR = PROJ_ROOT / "results/trajectory_tda_sheaf/checkpoints"


# ── Input resolution + provenance ────────────────────────────────────────────


def _resolve_input(relpath: str) -> Path:
    """Resolve an input that may be committed (worktree) or gitignored (PROJ_ROOT).

    The BHPS sequences are tracked, so they exist in the worktree; the integration
    sequences are gitignored (.gitignore:128) and live only at PROJ_ROOT. The
    sha256 gate below is what actually pins provenance, so either copy is
    acceptable once it hashes correctly.

    Args:
        relpath: Repository-relative path.

    Returns:
        An existing path.

    Raises:
        SystemExit: If the input is absent from both roots.
    """
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
    """Load one substrate's sequences and verify its locked sha256.

    Raises:
        SystemExit: On sha256 mismatch — a locked input must never be substituted.
    """
    spec = SUBSTRATES[substrate]
    path = _resolve_input(spec["sequences"])
    sha = _sha256(path)
    if sha != spec["sha256"]:
        raise SystemExit(
            f"STOP: {substrate} substrate sha256 mismatch\n  expected {spec['sha256']}\n  got      {sha}\n  at {path}"
        )
    sequences = json.loads(path.read_text())
    logger.info("[%s] substrate OK: %d trajectories (sha256 verified) from %s", substrate, len(sequences), path)
    return sequences, sha, path


# ── Membership rebuild (A4 discipline) ───────────────────────────────────────


def _checkpoint_n(dataset: str, stratifier: str, label: str) -> int | None:
    """T1.28 checkpoint n for a subgroup, or None when no checkpoint exists."""
    safe = label.replace("/", "-").replace(" ", "_")
    path = T128_CKPT_DIR / f"{dataset}_{stratifier}_{safe}_B1000_seed42.json"
    if not path.is_file():
        return None
    return int(json.loads(path.read_text())["n"])


def _rebuild_memberships(
    substrate: str,
    sequences: list[list[str]],
    anchored_cohort_only: bool = False,
) -> tuple[dict[str, NDArray[Any]], dict[str, dict[str, Any]]]:
    """Rebuild subgroup memberships via the T1.28 pipeline and verify anchors.

    Args:
        substrate: Substrate key.
        sequences: The substrate's trajectories.
        anchored_cohort_only: SENSITIVITY MODE ONLY — restrict the cohort family
            to decades that have a T1.28 checkpoint. The locked pre-registration
            defines the cohort family by the rule "decades with n >= 200", which
            admits decades T1.28 never pre-registered (BHPS 1910s/1920s,
            integration 1920s) and which therefore have no anchor. The default
            (False) is the locked reading; this flag produces a supplementary
            sensitivity result and never replaces the pre-registered one.

    Returns:
        Tuple ``(cov_arrays, family_plan)``. ``family_plan[family]`` carries the
        ordered ``groups`` (label -> n) and a ``status`` map recording excluded
        and MISSING members.

    Raises:
        SystemExit: If any group's rebuilt n disagrees with its T1.28 checkpoint.
    """
    from trajectory_tda.scripts.run_t128_stratified_w2 import (
        _load_dataset_covariates,
        _subgroup_indices,
    )

    spec = SUBSTRATES[substrate]
    dataset = spec["t128_dataset"]
    ckpt_dir = PROJ_ROOT / spec["ckpt_dir"]
    cov_arrays = _load_dataset_covariates(dataset, sequences, ckpt_dir)

    family_plan: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        if family == "nssec":
            candidate_labels = list(NSSEC_LABELS)
        else:
            observed = {lbl for lbl in cov_arrays["cohort"] if lbl is not None}
            candidate_labels = sorted(observed)

        groups: dict[str, int] = {}
        status: dict[str, str] = {}
        for label in candidate_labels:
            n_rebuilt = int(len(_subgroup_indices(cov_arrays, family, label)))
            anchor = _checkpoint_n(dataset, family, label)

            if anchor is not None and n_rebuilt != anchor:
                raise SystemExit(
                    f"STOP (A4): {substrate}/{family}/{label} rebuilt n={n_rebuilt} != checkpoint n={anchor}. "
                    "Membership anchors must reproduce exactly; never proceed on nearly-matching memberships."
                )

            if family == "cohort" and n_rebuilt < COHORT_MIN_N:
                status[label] = f"EXCLUDED (n={n_rebuilt} < {COHORT_MIN_N})"
                continue
            if n_rebuilt == 0:
                status[label] = "MISSING (n=0)"
                continue
            if anchor is None:
                if family == "cohort" and anchored_cohort_only:
                    status[label] = f"EXCLUDED BY SENSITIVITY (n={n_rebuilt}; no T1.28 checkpoint to anchor against)"
                    continue
                status[label] = f"INCLUDED (n={n_rebuilt}; no T1.28 checkpoint to anchor against)"
            else:
                status[label] = f"INCLUDED (n={n_rebuilt}; A4-verified against checkpoint)"
            groups[label] = n_rebuilt

        family_plan[family] = {"groups": groups, "status": status}
        logger.info("[%s/%s] groups=%s", substrate, family, groups)

    return cov_arrays, family_plan


# ── Statistic + baselines ────────────────────────────────────────────────────


def _js_divergence(p: NDArray[np.float64], q: NDArray[np.float64]) -> float:
    m = 0.5 * (p + q)

    def kl(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log(a[mask] / b[mask])))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def _chi_square_stat(table: NDArray[np.float64]) -> float:
    """Chi-square statistic of a G x S count table (statistic only, no p-value)."""
    row = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0, keepdims=True)
    total = table.sum()
    if total <= 0:
        return float("nan")
    expected = row @ col / total
    mask = expected > 0
    return float(np.sum((table[mask] - expected[mask]) ** 2 / expected[mask]))


# ── Module-level globals for loky workers (set via the Parallel initializer) ──

_COUNTS: NDArray[np.int64] | None = None
_STRATA: list[NDArray[np.intp]] | None = None
_LABEL_ARR: NDArray[Any] | None = None
_PARTNER_ARR: NDArray[Any] | None = None
_GROUP_LABELS: list[str] | None = None
_FULL_COL: NDArray[np.float64] | None = None
_W: NDArray[np.int64] | None = None
_EDGES: list[tuple[int, int]] | None = None


def _init_worker(counts, strata, label_arr, partner_arr, group_labels, full_col, weights, edges) -> None:
    global _COUNTS, _STRATA, _LABEL_ARR, _PARTNER_ARR, _GROUP_LABELS, _FULL_COL, _W, _EDGES
    _COUNTS, _STRATA, _LABEL_ARR, _PARTNER_ARR = counts, strata, label_arr, partner_arr
    _GROUP_LABELS, _FULL_COL, _W, _EDGES = group_labels, full_col, weights, edges


def _energy_from_signals(signals: NDArray[np.float64]) -> float:
    """Sheaf energy inlined against worker globals (mirrors sheaf_laplacian.sheaf_energy)."""
    return float(sum(_W[i, j] * np.sum((signals[i] - signals[j]) ** 2) for i, j in _EDGES))


def _draw_statistics(labels: NDArray[Any]) -> tuple[float, float, float, NDArray[np.float64]]:
    """Compute (E_sheaf, chi2, mean pairwise JS, signals) for one label assignment."""
    members = [labels == lbl for lbl in _GROUP_LABELS]
    cols = [_FULL_COL] + [occupancy_from_counts(_COUNTS, m) for m in members]
    signals = np.vstack(cols).T

    table = np.vstack([_COUNTS[m].sum(axis=0).astype(np.float64) for m in members])
    chi2 = _chi_square_stat(table)

    dists = [occupancy_from_counts(_COUNTS, m) for m in members]
    js = float(np.mean([_js_divergence(p, q) for p, q in combinations(dists, 2)]))
    return _energy_from_signals(signals), chi2, js, signals


def one_null_draw(b: int) -> dict[str, Any]:
    """One joint label-permutation draw within (length, first-state) strata.

    The permutation is applied jointly to the family label array and its partner
    covariate, preserving their association exactly as Spike 7's null did. Only
    labels move; the sequences (and therefore the transition graph) never do.
    """
    rng = np.random.default_rng(SEED + b)
    permuted = _LABEL_ARR.copy()
    partner = _PARTNER_ARR.copy()
    for idx in _STRATA:
        order = rng.permutation(len(idx))
        permuted[idx] = _LABEL_ARR[idx][order]
        partner[idx] = _PARTNER_ARR[idx][order]

    energy, chi2, js, signals = _draw_statistics(permuted)
    return {"b": b, "energy": energy, "chi2": chi2, "js": js, "signals": signals}


# ── BH-FDR ───────────────────────────────────────────────────────────────────


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

    ADDITIVE: at least one family rejects after BH-FDR on BOTH substrates, with
    both redundancy gates passing for that family on both substrates.
    REDUNDANT: FDR rejections occur but no rejecting family passes both gates on
    both substrates.
    NEGATIVE: no (family x substrate) test rejects after FDR.

    Args:
        rows: One dict per (family, substrate) with ``family``, ``rejects_fdr``,
            and ``redundancy_gates_pass``.

    Returns:
        Tuple ``(verdict, rationale)``.
    """
    if not any(r["rejects_fdr"] for r in rows):
        return "negative", "No (family x substrate) test rejects after BH-FDR."

    for family in FAMILIES:
        fam_rows = [r for r in rows if r["family"] == family]
        if not fam_rows:
            continue
        if all(r["rejects_fdr"] for r in fam_rows) and all(r["redundancy_gates_pass"] for r in fam_rows):
            return (
                "additive",
                f"Family '{family}' rejects after BH-FDR on both substrates with both redundancy gates passing on both.",
            )

    return (
        "redundant",
        "BH-FDR rejections occur, but no rejecting family passes both redundancy gates on both substrates.",
    )


# ── Battery for one (family, substrate) ──────────────────────────────────────


def _build_strata(seqs_idx: list[NDArray[np.int64]]) -> list[NDArray[np.intp]]:
    """(trajectory length, first observed state) strata index arrays."""
    buckets: dict[tuple[int, int], list[int]] = {}
    for i, seq in enumerate(seqs_idx):
        key = (len(seq), int(seq[0]) if len(seq) else -1)
        buckets.setdefault(key, []).append(i)
    return [np.asarray(v, dtype=np.intp) for v in buckets.values()]


def run_family_substrate(
    substrate: str,
    family: str,
    cov_arrays: dict[str, NDArray[Any]],
    family_plan: dict[str, Any],
    seqs_idx: list[NDArray[np.int64]],
    n_draws: int,
    workers: int,
    checkpoint_interval: int,
    wall_deadline: float,
    audit_only: bool,
) -> dict[str, Any]:
    """Run the locked null battery for one (family, substrate) cell."""
    tag = f"{substrate}/{family}"
    group_labels = list(family_plan["groups"].keys())
    if len(group_labels) < 2:
        raise SystemExit(f"STOP: {tag} has fewer than 2 usable groups — cannot form a family statistic.")

    counts = per_trajectory_state_counts(seqs_idx, N_STATES)
    weights, edges = build_transition_graph(seqs_idx, N_STATES)
    strata = _build_strata(seqs_idx)
    full_col = occupancy_from_counts(counts, np.ones(len(seqs_idx), dtype=bool))

    label_arr = cov_arrays[family]
    partner_arr = cov_arrays["cohort" if family == "nssec" else "nssec"]

    _init_worker(counts, strata, label_arr, partner_arr, group_labels, full_col, weights, edges)
    obs_energy, obs_chi2, obs_js, obs_signals = _draw_statistics(label_arr)
    logger.info(
        "[%s] observed E_sheaf=%.6f chi2=%.1f JS=%.6f  (%d groups, %d edges, %d strata)",
        tag,
        obs_energy,
        obs_chi2,
        obs_js,
        len(group_labels),
        len(edges),
        len(strata),
    )

    # ── Null-invariance / centering audit on draw 0 ───────────────────────────
    probe = one_null_draw(0)
    perturbed = not np.allclose(probe["signals"], obs_signals)
    shape_ok = probe["signals"].shape == obs_signals.shape
    if not perturbed:
        raise SystemExit(f"STOP: {tag} null draw 0 did not perturb the stalk signals — the null is invariant.")
    if not shape_ok:
        raise SystemExit(f"STOP: {tag} null draw shape {probe['signals'].shape} != observed {obs_signals.shape}.")
    logger.info("[%s] invariance pre-check OK (draw 0: E_sheaf=%.6f, signals perturbed)", tag, probe["energy"])

    draws = n_draws
    energies = np.empty(draws)
    chi2s = np.empty(draws)
    jss = np.empty(draws)

    ckpt_path = CHECKPOINT_DIR / f"sheaf_{substrate}_{family}_B{draws}_seed{SEED}.npz"
    t0 = time.perf_counter()
    # One process pool per cell, reused across checkpoint batches. joblib's loky
    # backend cannot be used here: its executor-reuse check compares initargs with
    # `==`, which raises "truth value of an array is ambiguous" the moment the
    # initargs carry numpy arrays and a second Parallel is constructed in the same
    # process. ProcessPoolExecutor takes the same initializer contract without that
    # equality probe, and is likewise process-based (>= 4 workers, locked convention).
    initargs = (counts, strata, label_arr, partner_arr, group_labels, full_col, weights, edges)
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=initargs) as pool:
        for start in range(0, draws, checkpoint_interval):
            if time.perf_counter() > wall_deadline:
                raise SystemExit(f"STOP: wall-time limit reached during {tag} at draw {start}.")
            end = min(start + checkpoint_interval, draws)
            for r in pool.map(one_null_draw, range(start, end)):
                energies[r["b"]] = r["energy"]
                chi2s[r["b"]] = r["chi2"]
                jss[r["b"]] = r["js"]

            CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
            np.savez(ckpt_path, energies=energies[:end], chi2s=chi2s[:end], jss=jss[:end], completed=end)
            logger.info(
                "[%s] %d/%d draws (%.0fs) — checkpoint %s", tag, end, draws, time.perf_counter() - t0, ckpt_path.name
            )

    elapsed = time.perf_counter() - t0

    null_mean = float(energies.mean())
    null_std = float(energies.std())
    percentile = float(np.mean(energies < obs_energy) * 100)
    if null_std == 0.0:
        raise SystemExit(
            f"STOP: {tag} null energy distribution is degenerate (std=0) — statistic invariant under the null."
        )

    p_upper = float((1 + np.sum(energies >= obs_energy)) / (1 + draws))
    p_lower = float((1 + np.sum(energies <= obs_energy)) / (1 + draws))
    effect_size = float((obs_energy - null_mean) / null_std)

    rows_e = np.append(energies, obs_energy)
    rho_chi2 = float(spearmanr(rows_e, np.append(chi2s, obs_chi2)).statistic)
    rho_js = float(spearmanr(rows_e, np.append(jss, obs_js)).statistic)

    spectrum = sheaf_spectrum(weights, edges, N_STATES, len(group_labels) + 1)

    logger.info(
        "[%s] p_upper=%.4f p_lower=%.4f effect=%.2f rho_chi2=%.3f rho_js=%.3f (null %.1f+-%.1f, obs pct %.1f) %.0fs",
        tag,
        p_upper,
        p_lower,
        effect_size,
        rho_chi2,
        rho_js,
        null_mean,
        null_std,
        percentile,
        elapsed,
    )

    return {
        "family": family,
        "substrate": substrate,
        "group_ns": dict(family_plan["groups"]),
        "group_status": family_plan["status"],
        "n_groups_including_full_sample": len(group_labels) + 1,
        "observed_energy": obs_energy,
        "observed_chi_square": obs_chi2,
        "observed_mean_js": obs_js,
        "null_mean": null_mean,
        "null_std": null_std,
        "null_energy_draws": energies.tolist(),
        "observed_percentile_of_null": percentile,
        "p_upper": p_upper,
        "p_lower": p_lower,
        "effect_size": effect_size,
        "rho_chi2": rho_chi2,
        "rho_js": rho_js,
        "redundancy_gates_pass": bool(abs(rho_chi2) < REDUNDANCY_GATE and abs(rho_js) < REDUNDANCY_GATE),
        "sheaf_spectrum_exploratory": spectrum.tolist(),
        "sheaf_spectrum_note": (
            "Exploratory descriptive only — NO p-value attached (locked pre-reg). With identity restrictions "
            "L_F = L_G (x) I_G, so this spectrum is the weighted graph Laplacian spectrum with each eigenvalue "
            "repeated (n_groups + 1) times and is independent of the stalk signals."
        ),
        "null_invariance_audit": {
            "draw_0_signals_perturbed": bool(perturbed),
            "draw_0_shape_matches_observed": bool(shape_ok),
            "draw_0_energy": float(probe["energy"]),
            "null_std_positive": True,
            "observed_percentile_of_null": percentile,
            "centering_argument": (
                "The null is a joint covariate-label permutation within (length, first-state) strata — it is not a "
                "parametric fit through the statistic's sufficient statistic. E_sheaf depends on per-group occupancy "
                "signals, which the permutation actively resamples; the transition graph (and hence the edge weights) "
                "is held fixed and is not the object the statistic is centered on. Observed is therefore not "
                "structurally centered in its own null; the reported percentile is empirical evidence of this."
            ),
        },
        "elapsed_seconds": round(elapsed, 1),
        "audit_only": audit_only,
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sheaf-Laplacian energy confirmatory battery (LOCKED 2026-07-10)")
    parser.add_argument("--B", type=int, default=B_LOCKED, help="permutation draws (pre-registered 1000)")
    parser.add_argument("--workers", type=int, default=4, help="loky workers (locked convention: >= 4)")
    parser.add_argument("--checkpoint-interval", type=int, default=100, help="checkpoint cadence (pre-reg: 100)")
    parser.add_argument("--wall-time-hours", type=float, default=4.0, help="wall-time flag (pre-reg: 4h)")
    parser.add_argument(
        "--audit-only", action="store_true", help="run the invariance/centering audit at small B and stop"
    )
    parser.add_argument("--audit-draws", type=int, default=50, help="draws for --audit-only")
    parser.add_argument(
        "--anchored-cohort-only",
        action="store_true",
        help=(
            "SENSITIVITY MODE: restrict the cohort family to T1.28-anchored decades. Supplementary to the locked "
            "run (which uses the pre-registered n>=200 rule); writes a separate _sensitivity_anchored_cohort file."
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

    substrate_sha256: dict[str, str] = {}
    input_paths: dict[str, str] = {}
    rows: list[dict[str, Any]] = []

    for substrate in SUBSTRATES:
        sequences, sha, path = _load_substrate(substrate)
        substrate_sha256[substrate] = sha
        input_paths[substrate] = str(path)

        seqs_idx = [np.asarray([STATE_TO_IDX[s] for s in seq], dtype=np.int64) for seq in sequences]
        cov_arrays, family_plan = _rebuild_memberships(substrate, sequences, args.anchored_cohort_only)

        for family in FAMILIES:
            rows.append(
                run_family_substrate(
                    substrate=substrate,
                    family=family,
                    cov_arrays=cov_arrays,
                    family_plan=family_plan[family],
                    seqs_idx=seqs_idx,
                    n_draws=n_draws,
                    workers=args.workers,
                    checkpoint_interval=args.checkpoint_interval,
                    wall_deadline=wall_deadline,
                    audit_only=args.audit_only,
                )
            )

    # ── BH-FDR across the 4 (family x substrate) tests ────────────────────────
    p_uppers = np.array([r["p_upper"] for r in rows], dtype=np.float64)
    p_fdr = bh_adjust(p_uppers)
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
            "per_draw_seeds": "42+b",
            "alpha": ALPHA,
            "fdr_method": "benjamini-hochberg",
            "n_tests": len(rows),
            "redundancy_gate": REDUNDANCY_GATE,
            "cohort_min_n": COHORT_MIN_N,
            "test_direction": "one-sided upper (both tails reported)",
            "p_formula": "(1 + #{null >= observed}) / (1 + B)",
            "parallel_workers": args.workers,
            "checkpoint_interval": args.checkpoint_interval,
            "wall_time_hours": args.wall_time_hours,
            "wall_time_seconds": round(elapsed, 1),
        },
        "families": rows,
        "null_model_construction_verified": True,
        "decision": {"verdict": verdict, "rationale": rationale},
        "provenance": {
            "pre_registration": "vault/00-Meta/Discovery/sheaf-laplacian-employment-dispatch-prereg-2026-07-10.md",
            "pre_registration_status": "LOCKED 2026-07-10",
            "run_mode": (
                "SENSITIVITY — cohort family restricted to T1.28-anchored decades. Supplementary evidence; NOT the "
                "pre-registered design, which defines the cohort family by the rule 'decades with n >= 200'."
                if args.anchored_cohort_only
                else "LOCKED pre-registered design (cohort family = decades with n >= 200)."
            ),
            "input_paths": input_paths,
            "t128_checkpoint_dir": str(T128_CKPT_DIR),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    logger.info("VERDICT: %s — %s", verdict.upper(), rationale)

    if args.dry_run or args.audit_only:
        logger.info("audit-only/dry-run: no dated result file written (%.0fs)", elapsed)
        print(
            json.dumps(
                {
                    "verdict": verdict,
                    "rows": [
                        {
                            k: r[k]
                            for k in (
                                "family",
                                "substrate",
                                "p_upper",
                                "p_lower",
                                "p_fdr",
                                "effect_size",
                                "rho_chi2",
                                "rho_js",
                                "observed_percentile_of_null",
                            )
                        }
                        for r in rows
                    ],
                },
                indent=2,
            )
        )
        return

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_sensitivity_anchored_cohort" if args.anchored_cohort_only else ""
    out_path = RESULT_DIR / f"sheaf_laplacian_employment{suffix}_{date.today().isoformat()}.json"
    if out_path.exists():
        raise SystemExit(f"STOP: results file already exists, never overwrite: {out_path}")
    out_path.write_text(json.dumps(payload, indent=2))
    logger.info("wrote %s (%.0fs total)", out_path, elapsed)


if __name__ == "__main__":
    main()
