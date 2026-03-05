"""
P1.4: Phase-ordering null test with increased permutations.

Re-runs the phase-order shuffle test from Phase 6 with n ≥ 200
(default 500) permutations, augmenting the original n=20 run.
Computes p-values with bootstrap confidence intervals.

Saves:
    results/trajectory_tda_robustness/phase_ordering/
        phase_null_n{N}.json          – full null test results
        phase_null_H0_n{N}.npy        – H0 null distribution array
        phase_null_H1_n{N}.npy        – H1 null distribution array
        phase_ordering_summary.json   – summary with CIs

Usage:
    python -m trajectory_tda.scripts.run_phase_ordering \
        --phase6-dir results/trajectory_tda_phase6 \
        --output-dir results/trajectory_tda_robustness/phase_ordering \
        --n-permutations 500
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_json(data: dict, path: Path) -> None:
    """Save dict as JSON with numpy-safe conversion."""

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {path}")


def compute_p_value_ci(
    null_distribution: np.ndarray,
    observed: float,
    n_bootstrap: int = 10000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> dict:
    """Compute p-value with bootstrap confidence interval.

    Args:
        null_distribution: Array of null statistic values.
        observed: Observed statistic value.
        n_bootstrap: Number of bootstrap resamples for CI.
        ci_level: Confidence level (default: 0.95).
        seed: Random seed.

    Returns:
        Dict with p_value, ci_lower, ci_upper, n_perms.
    """
    rng = np.random.RandomState(seed)
    n = len(null_distribution)

    # Point estimate
    p_value = float(np.mean(null_distribution >= observed))

    # Bootstrap CI for the p-value
    boot_pvals = []
    for _ in range(n_bootstrap):
        boot_sample = rng.choice(null_distribution, size=n, replace=True)
        boot_p = float(np.mean(boot_sample >= observed))
        boot_pvals.append(boot_p)

    boot_pvals = np.array(boot_pvals)
    alpha = 1 - ci_level
    ci_lower = float(np.percentile(boot_pvals, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_pvals, 100 * (1 - alpha / 2)))

    return {
        "p_value": p_value,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "ci_level": ci_level,
        "n_perms": n,
    }


def run_phase_ordering(args: argparse.Namespace) -> dict:
    """Re-run phase-order shuffle test with more permutations."""
    from trajectory_tda.topology.permutation_nulls import phase_order_shuffle_test

    t0 = time.time()
    p6_dir = Path(args.phase6_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_perms = args.n_permutations

    # ─── Load Phase 6 artefacts ───
    logger.info("Loading Phase 6 artefacts...")

    # Window embeddings
    window_embeddings = np.load(p6_dir / "02_window_embeddings.npy")
    logger.info(f"Window embeddings: {window_embeddings.shape}")

    # Window metadata
    with open(p6_dir / "01_windows.json") as f:
        window_data = json.load(f)
    windows = window_data["windows"]
    logger.info(f"Windows: {len(windows)}")

    # Phase embeddings and indices (from Phase 6 step 6)
    phase_embeddings = np.load(p6_dir / "04_phase_embeddings.npy")
    logger.info(f"Phase embeddings: {phase_embeddings.shape}")

    # We need to reconstruct the phase_windows list (windows corresponding
    # to phase_embeddings). Phase 6 filtered to disadvantaged + sampled others.
    # Replicate the same selection logic to get the same subset.
    with open(p6_dir / "03_regime_sequences.json") as f:
        regime_seq_raw = json.load(f)
    # Handle nested structure: {regime_sequences: {pidp: [...]}}
    if "regime_sequences" in regime_seq_raw:
        regime_sequences = regime_seq_raw["regime_sequences"]
    else:
        regime_sequences = regime_seq_raw

    # Reconstruct disadvantaged set
    DISADVANTAGED_REGIMES = {2, 6}
    pidps_disadvantaged = set()
    for pidp, seq in regime_sequences.items():
        if any(s["regime"] in DISADVANTAGED_REGIMES for s in seq):
            pidps_disadvantaged.add(int(pidp))

    disadv_mask = np.array([w["pidp"] in pidps_disadvantaged for w in windows])
    other_mask = ~disadv_mask

    n_disadv = int(disadv_mask.sum())
    max_other = max(0, 50000 - n_disadv)
    other_indices = np.where(other_mask)[0]
    rng = np.random.RandomState(42)
    if len(other_indices) > max_other:
        sampled_other = rng.choice(other_indices, size=max_other, replace=False)
    else:
        sampled_other = other_indices

    phase_indices = np.concatenate([np.where(disadv_mask)[0], sampled_other])
    phase_indices.sort()

    # Verify we match the Phase 6 embeddings
    assert (
        len(phase_indices) == phase_embeddings.shape[0]
    ), f"Phase index mismatch: {len(phase_indices)} vs {phase_embeddings.shape[0]}"

    phase_windows = [windows[i] for i in phase_indices]
    logger.info(f"Phase windows reconstructed: {len(phase_windows)}")

    # ─── Load original n=20 results for comparison ───
    original_path = p6_dir / "06_phase_nulls.json"
    with open(original_path) as f:
        original = json.load(f)
    logger.info(
        f"Original results (n={original['n_permutations']}): "
        f"H0 p={original['p_values']['H0']}, H1 p={original['p_values']['H1']}"
    )

    # ─── Run new phase-order shuffle test ───
    result_path = out_dir / f"phase_null_n{n_perms}.json"
    if result_path.exists() and not args.force:
        logger.info(f"Loading cached results from {result_path}")
        with open(result_path) as f:
            null_result = json.load(f)
    else:
        logger.info("=" * 60)
        logger.info(f"Running phase-order shuffle: n={n_perms}")
        logger.info("=" * 60)

        null_result = phase_order_shuffle_test(
            phase_embeddings,
            phase_windows,
            n_permutations=n_perms,
            max_dim=1,
            n_landmarks=min(args.n_landmarks, phase_embeddings.shape[0]),
            n_jobs=args.n_jobs,
            seed=42,
        )

        _save_json(null_result, result_path)

        # Save null distributions as numpy
        for dim_key, vals in null_result["null_distributions"].items():
            arr = np.array(vals)
            np.save(out_dir / f"phase_null_{dim_key}_n{n_perms}.npy", arr)

    # ─── Compute p-value CIs ───
    logger.info("Computing p-value confidence intervals...")
    ci_results = {}
    for dim_key in ["H0", "H1"]:
        null_arr = np.array(null_result["null_distributions"][dim_key])
        observed = null_result["observed"][dim_key]

        ci = compute_p_value_ci(null_arr, observed, seed=42)
        ci_results[dim_key] = ci
        logger.info(f"  {dim_key}: p={ci['p_value']:.4f} " f"[{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}] (95% CI)")

    # ─── Summary ───
    summary = {
        "n_permutations_original": original["n_permutations"],
        "n_permutations_new": n_perms,
        "n_landmarks": min(args.n_landmarks, phase_embeddings.shape[0]),
        "n_phase_windows": len(phase_windows),
        "original_p_values": original["p_values"],
        "original_observed": original["observed"],
        "new_p_values": null_result["p_values"],
        "new_observed": null_result["observed"],
        "p_value_confidence_intervals": ci_results,
        "null_distribution_stats": {},
        "elapsed_seconds": time.time() - t0,
    }

    for dim_key in ["H0", "H1"]:
        null_arr = np.array(null_result["null_distributions"][dim_key])
        summary["null_distribution_stats"][dim_key] = {
            "mean": float(null_arr.mean()),
            "std": float(null_arr.std()),
            "min": float(null_arr.min()),
            "max": float(null_arr.max()),
            "p5": float(np.percentile(null_arr, 5)),
            "p95": float(np.percentile(null_arr, 95)),
        }

    _save_json(summary, out_dir / "phase_ordering_summary.json")

    logger.info("=" * 60)
    logger.info("Phase-Ordering Null Test Complete")
    logger.info(
        f"  Original (n={original['n_permutations']}): H0 p={original['p_values']['H0']}, H1 p={original['p_values']['H1']}"
    )
    logger.info(
        f"  New (n={n_perms}): H0 p={null_result['p_values']['H0']:.4f}, H1 p={null_result['p_values']['H1']:.4f}"
    )
    for dim_key in ["H0", "H1"]:
        ci = ci_results[dim_key]
        logger.info(f"  {dim_key} 95% CI: [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}]")
    logger.info(f"  Elapsed: {time.time() - t0:.1f}s")
    logger.info("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(description="P1.4: Phase-ordering null test with increased permutations")
    parser.add_argument(
        "--phase6-dir",
        type=str,
        default="results/trajectory_tda_phase6",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/trajectory_tda_robustness/phase_ordering",
    )
    parser.add_argument(
        "--n-permutations",
        type=int,
        default=500,
        help="Number of permutations (default: 500)",
    )
    parser.add_argument(
        "--n-landmarks",
        type=int,
        default=3000,
        help="Landmarks for PH (default: 3000)",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=4,
        help="Parallelism for permutations (default: 4, -1=all cores)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if cached results exist",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)
    run_phase_ordering(args)


if __name__ == "__main__":
    main()
