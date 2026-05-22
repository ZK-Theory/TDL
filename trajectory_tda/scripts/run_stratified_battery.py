# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Stage 1 stratified Markov-1 battery — per-regime W₂ tests at L=5000, B=100,
#   Markov-1 null, for USoc (7 regimes) and BHPS (8 regimes). Applies BH-FDR and
#   locks A/B/C outcome per pre-registration 2026-05-13.
"""
Stage 1 stratified Markov-1 battery.

For each regime in USoc and BHPS, runs W₂ Markov-1 permutation tests at the
pre-registered parameters (L=5000, B=100, seed=42) and applies BH-FDR correction
across all (dataset × regime × dimension) tests to lock the A/B/C decision outcome.

Usage:
    python -m trajectory_tda.scripts.run_stratified_battery

Pre-registration: 2026-05-13 vault entry PRE-REGISTRATION — Stratified Markov-1 Battery
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Pre-registered parameters (locked 2026-05-13)
DEFAULT_L = 5000
DEFAULT_B = 100
DEFAULT_SEED = 42
DEFAULT_K_MAX = 5
DEFAULT_N_POINTS = 200
DEFAULT_MARKOV_ORDER = 1
FDR_ALPHA = 0.05
# Outcome-A threshold: majority of regimes significant (H0 or H1) in a dataset
OUTCOME_A_MIN_FRAC = 0.5


def _convert_numpy(obj: object) -> object:
    """Recursively convert numpy types for JSON serialisation."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    return obj


def _bh_fdr(pvalues: list[float], alpha: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg FDR correction.

    Args:
        pvalues: Raw p-values.
        alpha: FDR level.

    Returns:
        Boolean list — True where the null is rejected at FDR level alpha.
    """
    m = len(pvalues)
    if m == 0:
        return []
    sorted_idx = np.argsort(pvalues)
    sorted_p = np.array(pvalues)[sorted_idx]
    bh_thresholds = alpha * np.arange(1, m + 1) / m
    reject_sorted = sorted_p <= bh_thresholds
    if not np.any(reject_sorted):
        return [False] * m
    # All tests up to and including the largest k with p_(k) ≤ k*alpha/m are rejected
    max_k = int(np.max(np.where(reject_sorted)[0]))
    reject_final = np.zeros(m, dtype=bool)
    reject_final[: max_k + 1] = True
    result = [False] * m
    for rank, orig in enumerate(sorted_idx):
        result[orig] = bool(reject_final[rank])
    return result


def _run_regime_battery(
    checkpoint_dir: Path,
    analysis_json_path: Path,
    n_permutations: int,
    n_landmarks: int,
    seed: int,
    label: str,
) -> dict[str, Any]:
    """Run per-regime W₂ + landscape L² battery for one dataset.

    For each regime r, filters to regime-r trajectories, fits a Markov-1 null
    on those trajectories, runs n_permutations permutations, and computes W₂
    and landscape L² statistics via _aggregate_combined.

    Args:
        checkpoint_dir: Path to checkpoint directory (embeddings.npy + 01_trajectories_sequences.json).
        analysis_json_path: Path to 05_analysis.json containing gmm_labels.
        n_permutations: Number of Markov-1 permutations per regime.
        n_landmarks: Target landmark count (capped at regime size).
        seed: Master random seed.
        label: Dataset label for logging.

    Returns:
        Dict mapping "R{regime_int}" → {n, n_landmarks_used, h0: {...}, h1: {...}}
        or → {skipped: True, n: int} for tiny regimes.
    """
    from joblib import Parallel, delayed

    from poverty_tda.topology.multidim_ph import compute_rips_ph
    from trajectory_tda.scripts.run_stage1_battery import _aggregate_combined
    from trajectory_tda.scripts.run_wasserstein_battery import (
        load_checkpoint,
        load_regime_labels,
    )
    from trajectory_tda.topology.permutation_nulls import (
        _single_permutation,
        maxmin_landmarks,
    )

    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    regime_labels: NDArray[np.int_] = load_regime_labels(analysis_json_path)

    if len(regime_labels) != embeddings.shape[0]:
        raise ValueError(
            f"Regime label length {len(regime_labels)} does not match embedding rows {embeddings.shape[0]}"
        )

    unique_regimes = sorted(np.unique(regime_labels).tolist())
    logger.info("%s: %d regimes: %s", label, len(unique_regimes), unique_regimes)

    traj_arr = list(trajectories)
    regime_results: dict[str, Any] = {}

    for r in unique_regimes:
        regime_key = f"R{r}"
        mask = regime_labels == r
        n_r = int(mask.sum())
        logger.info("%s %s: %d trajectories", label, regime_key, n_r)

        if n_r < 10:
            logger.warning(
                "%s %s: only %d trajectories — skipping (too small for PH)",
                label,
                regime_key,
                n_r,
            )
            regime_results[regime_key] = {"skipped": True, "n": n_r}
            continue

        emb_r: NDArray[np.float64] = embeddings[mask]
        traj_r = [t for t, m in zip(traj_arr, mask.tolist()) if m]

        actual_lm = min(n_landmarks, n_r)
        if actual_lm < n_r:
            _, obs_lm = maxmin_landmarks(emb_r, actual_lm, seed=seed)
        else:
            obs_lm = emb_r
        ph_obs = compute_rips_ph(obs_lm, max_dim=1)

        # Seed offset per regime avoids seed collisions across regimes
        seeds_list = [seed + r * 1000 + i + 1 for i in range(n_permutations)]

        logger.info(
            "%s %s: %d Markov-1 permutations (L=%d)...",
            label,
            regime_key,
            n_permutations,
            actual_lm,
        )
        t0 = time.time()
        null_results = Parallel(n_jobs=4, verbose=0)(
            delayed(_single_permutation)(
                "markov",
                emb_r,
                traj_r,
                None,
                s,
                1,
                actual_lm,
                "wasserstein",
                DEFAULT_MARKOV_ORDER,
                embed_kwargs,
                ph_observed=ph_obs,
            )
            for s in seeds_list
        )
        logger.info("%s %s: done in %.1fs", label, regime_key, time.time() - t0)

        combined = _aggregate_combined(
            null_results,
            ph_obs,
            n_permutations,
            1,
            DEFAULT_K_MAX,
            DEFAULT_N_POINTS,
            seed,
        )
        regime_results[regime_key] = {
            "n": n_r,
            "n_landmarks_used": actual_lm,
            **combined,
        }

    return regime_results


def _apply_bh_and_classify(
    usoc_results: dict[str, Any],
    bhps_results: dict[str, Any],
    alpha: float = FDR_ALPHA,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Apply BH-FDR over W₂ p-values and classify A/B/C outcome.

    BH correction is applied jointly over all (dataset × regime × dimension) tests.
    Outcome A: majority of regimes in at least one dataset show a significant W₂
      p-value (q < alpha) in H0 or H1.
    Outcome B: at least one regime significant but not majority in any dataset.
    Outcome C: no regime significant.

    Returns:
        Tuple of (fdr_table, per_dataset_summary, outcome_letter).
    """
    # Collect raw p-values in deterministic order
    test_ids: list[tuple[str, str, str]] = []
    pvalues: list[float] = []

    for ds_label, results in [("usoc", usoc_results), ("bhps", bhps_results)]:
        for rk in sorted(results.keys()):
            r = results[rk]
            if r.get("skipped"):
                continue
            for dim in ["h0", "h1"]:
                cell = r.get(dim)
                if cell and "w2_pvalue" in cell:
                    test_ids.append((ds_label, rk, dim))
                    pvalues.append(float(cell["w2_pvalue"]))

    rejected = _bh_fdr(pvalues, alpha=alpha)

    fdr_table: dict[str, dict[str, object]] = {}
    for (ds, rk, dim), p, rej in zip(test_ids, pvalues, rejected):
        fdr_table[f"{ds}_{rk}_{dim}"] = {"raw_pvalue": p, "rejected": bool(rej)}

    # Per-dataset summary: how many regimes have ≥1 significant dimension
    per_dataset: dict[str, dict[str, Any]] = {}
    for ds_label, results in [("usoc", usoc_results), ("bhps", bhps_results)]:
        n_regimes_tested = sum(1 for r in results.values() if not r.get("skipped"))
        sig_regimes: list[str] = []
        for rk in sorted(results.keys()):
            if results[rk].get("skipped"):
                continue
            regime_sig = any(fdr_table.get(f"{ds_label}_{rk}_{dim}", {}).get("rejected", False) for dim in ["h0", "h1"])
            if regime_sig:
                sig_regimes.append(rk)
        per_dataset[ds_label] = {
            "n_regimes_tested": n_regimes_tested,
            "n_significant": len(sig_regimes),
            "significant_regimes": sig_regimes,
            "frac_significant": len(sig_regimes) / n_regimes_tested if n_regimes_tested > 0 else 0.0,
        }

    # A/B/C: majority in at least one dataset → A; any → B; none → C
    total_sig = sum(d["n_significant"] for d in per_dataset.values())
    majority_in_any = any(d["frac_significant"] >= OUTCOME_A_MIN_FRAC for d in per_dataset.values())

    if total_sig == 0:
        outcome = "C"
    elif majority_in_any:
        outcome = "A"
    else:
        outcome = "B"

    return fdr_table, per_dataset, outcome


def main() -> None:
    """Entry point for the stratified Markov-1 battery."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Stage 1 stratified Markov-1 battery")
    parser.add_argument("--usoc-dir", default="results/trajectory_tda_integration")
    parser.add_argument("--bhps-dir", default="results/trajectory_tda_bhps")
    parser.add_argument(
        "--usoc-analysis",
        default=None,
        help="Path to USoc 05_analysis.json (defaults to <usoc-dir>/05_analysis.json)",
    )
    parser.add_argument(
        "--bhps-analysis",
        default=None,
        help="Path to BHPS 05_analysis.json (defaults to <bhps-dir>/05_analysis.json)",
    )
    parser.add_argument("--n-perms", type=int, default=DEFAULT_B)
    parser.add_argument("--landmarks", type=int, default=DEFAULT_L)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    today = date.today().isoformat()
    usoc_dir = Path(args.usoc_dir)
    bhps_dir = Path(args.bhps_dir)
    usoc_analysis = Path(args.usoc_analysis) if args.usoc_analysis else usoc_dir / "05_analysis.json"
    bhps_analysis = Path(args.bhps_analysis) if args.bhps_analysis else bhps_dir / "05_analysis.json"
    output_path = (
        Path(args.output)
        if args.output
        else Path(f"results/trajectory_tda_integration/stage1/stratified_markov1_battery_{today}.json")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info(
        "Stage 1 stratified Markov-1 battery: L=%d, B=%d, seed=%d",
        args.landmarks,
        args.n_perms,
        args.seed,
    )
    logger.info("Output: %s", output_path)
    logger.info("=" * 70)

    t_total = time.time()
    usoc_results = _run_regime_battery(usoc_dir, usoc_analysis, args.n_perms, args.landmarks, args.seed, "USoc")
    bhps_results = _run_regime_battery(bhps_dir, bhps_analysis, args.n_perms, args.landmarks, args.seed, "BHPS")

    fdr_table, per_dataset, outcome = _apply_bh_and_classify(usoc_results, bhps_results)

    logger.info("=" * 70)
    logger.info("OUTCOME: %s", outcome)
    for ds, summary in per_dataset.items():
        logger.info(
            "  %s: %d/%d regimes significant (%.0f%%): %s",
            ds,
            summary["n_significant"],
            summary["n_regimes_tested"],
            100 * summary["frac_significant"],
            summary["significant_regimes"],
        )
    logger.info("Total elapsed: %.1fs", time.time() - t_total)
    logger.info("=" * 70)

    output: dict[str, Any] = {
        "pre_registration": "2026-05-13",
        "params": {
            "L": args.landmarks,
            "B": args.n_perms,
            "null": "markov-1 per regime",
            "seed": args.seed,
            "k_max": DEFAULT_K_MAX,
            "n_points": DEFAULT_N_POINTS,
            "fdr_alpha": FDR_ALPHA,
            "outcome_a_min_frac": OUTCOME_A_MIN_FRAC,
        },
        "outcome": outcome,
        "outcome_rule": (
            f"A: frac_significant >= {OUTCOME_A_MIN_FRAC} in ≥1 dataset; B: any significant; C: none significant"
        ),
        "per_dataset": per_dataset,
        "fdr_tests": fdr_table,
        "usoc": usoc_results,
        "bhps": bhps_results,
        "date": today,
    }

    with open(output_path, "w") as f:
        json.dump(_convert_numpy(output), f, indent=2)
    logger.info("Saved: %s", output_path)


if __name__ == "__main__":
    main()
