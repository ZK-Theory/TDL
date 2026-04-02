"""P04 Scale Sensitivity: 5,000-landmark computation.

Runs the full P04 pipeline at 5,000 landmarks to test whether
2,000-landmark findings are qualitatively stable at higher density.

Outputs go to separate directories so 2k results are preserved:
    results/p04_multipers_5k/
    figures/trajectory_tda/p04_5k/

Usage:
    uv run python trajectory_tda/scripts/p04_run_5k.py
    uv run python trajectory_tda/scripts/p04_run_5k.py --n-perms 99  # quick test
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT / "results" / "p04_multipers_5k"
FIGURE_DIR = ROOT / "figures" / "trajectory_tda" / "p04_5k"


def plot_null_distribution(null_result, output_dir: Path) -> None:
    """Plot permutation null distribution with observed value."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        "P04 Permutation Null Test (5k landmarks): Income-Label Shuffles",
        fontsize=14,
    )

    ax = axes[0]
    ax.hist(
        null_result.null_h1_low_fractions,
        bins=30,
        color="steelblue",
        alpha=0.7,
        edgecolor="white",
        label="Null distribution",
    )
    ax.axvline(
        null_result.observed_h1_low_fraction,
        color="red",
        linewidth=2,
        linestyle="--",
        label=f"Observed = {null_result.observed_h1_low_fraction:.3f}",
    )
    ax.axvline(0.5, color="gray", linewidth=1, linestyle=":", label="Expected = 0.50")
    ax.set_xlabel("H1 Low-Income Fraction")
    ax.set_ylabel("Count")
    ax.set_title(f"H1 Low-Income Fraction (p = {null_result.p_value:.4f})")
    ax.legend(fontsize=9)

    ax = axes[1]
    ax.hist(
        null_result.null_q1_q3_ratios,
        bins=30,
        color="coral",
        alpha=0.7,
        edgecolor="white",
        label="Null distribution",
    )
    ax.axvline(
        null_result.observed_q1_q3_ratio,
        color="red",
        linewidth=2,
        linestyle="--",
        label=f"Observed = {null_result.observed_q1_q3_ratio:.3f}",
    )
    ax.axvline(1.0, color="gray", linewidth=1, linestyle=":", label="Expected = 1.0")
    ax.set_xlabel("Q1/Q3 Mass Ratio")
    ax.set_ylabel("Count")
    ax.set_title(f"Q1/Q3 Ratio (p = {null_result.p_value_q1_q3:.4f})")
    ax.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(output_dir / "null_distribution_5k.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved null distribution figure")


def plot_baseline_comparison(baseline: dict, output_dir: Path) -> None:
    """Plot P01 baseline comparison at 5k scale."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("P01 Baseline: Single-Parameter VR PH (5k landmarks)", fontsize=14)

    labels = ["Full", "Low (Q1)", "High (Q4)"]
    counts = [
        baseline["full"]["h1_count"],
        baseline["low_income_q1"]["h1_count"],
        baseline["high_income_q4"]["h1_count"],
    ]
    colors = ["gray", "#d62728", "#2ca02c"]
    axes[0].bar(labels, counts, color=colors)
    axes[0].set_ylabel("H1 Feature Count")
    axes[0].set_title("H1 Features by Income Subset")

    densities = [
        baseline["h1_density_full"],
        baseline["h1_density_low"],
        baseline["h1_density_high"],
    ]
    axes[1].bar(labels, densities, color=colors)
    axes[1].set_ylabel("H1 Features per Point")
    axes[1].set_title("H1 Density (normalised by subset size)")

    plt.tight_layout()
    fig.savefig(output_dir / "baseline_comparison_5k.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved baseline comparison figure")


def plot_scale_comparison(results_2k_path: Path, results_5k: dict) -> None:
    """Plot 2k vs 5k comparison if 2k results exist."""
    import matplotlib.pyplot as plt

    if not results_2k_path.exists():
        logger.info("No 2k results at %s — skipping comparison plot", results_2k_path)
        return

    with open(results_2k_path) as f:
        r2k = json.load(f)

    bif_2k = r2k["bifiltration"]
    bif_5k = results_5k

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("P04 Scale Sensitivity: 2k vs 5k Landmarks", fontsize=14)

    # H1 low-income fraction
    ax = axes[0]
    vals = [
        bif_2k["h1"]["stratification"]["low_income_fraction"],
        bif_5k["h1"]["stratification"]["low_income_fraction"],
    ]
    ax.bar(["2k", "5k"], vals, color=["steelblue", "coral"])
    ax.set_ylabel("H1 Low-Income Fraction")
    ax.set_title("H1 Low-Income Fraction")
    ax.axhline(0.5, color="gray", linestyle=":", alpha=0.5)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=10)

    # Quartile decomposition
    ax = axes[1]
    q2k = bif_2k["h1"]["quartile_decomposition"]["masses"]
    q5k = bif_5k["h1"]["quartile_decomposition"]["masses"]
    x = np.arange(4)
    w = 0.35
    t2k = sum(q2k) if sum(q2k) > 0 else 1
    t5k = sum(q5k) if sum(q5k) > 0 else 1
    ax.bar(x - w / 2, [m / t2k for m in q2k], w, label="2k", color="steelblue")
    ax.bar(x + w / 2, [m / t5k for m in q5k], w, label="5k", color="coral")
    ax.set_xticks(x)
    ax.set_xticklabels(["Q1", "Q2", "Q3", "Q4"])
    ax.set_ylabel("Share of H1 Mass")
    ax.set_title("Quartile Decomposition")
    ax.legend()

    # Q1/Q3 ratio
    ax = axes[2]
    ratios = [
        bif_2k["h1"]["quartile_decomposition"]["ratio_q1_q3"],
        bif_5k["h1"]["quartile_decomposition"]["ratio_q1_q3"],
    ]
    ax.bar(["2k", "5k"], ratios, color=["steelblue", "coral"])
    ax.set_ylabel("Q1/Q3 Ratio")
    ax.set_title("Q1/Q3 Mass Ratio")
    ax.axhline(1.0, color="gray", linestyle=":", alpha=0.5)
    for i, v in enumerate(ratios):
        ax.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=10)

    plt.tight_layout()
    fig.savefig(FIGURE_DIR / "scale_comparison_2k_5k.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved 2k vs 5k comparison figure")


def main() -> None:
    """Run 5,000-landmark P04 computation."""
    parser = argparse.ArgumentParser(description="P04 5k-landmark scale test")
    parser.add_argument(
        "--n-landmarks", type=int, default=5000, help="Number of landmarks"
    )
    parser.add_argument(
        "--n-perms", type=int, default=999, help="Number of permutations"
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=2,
        help="Parallelism (default=2 for memory safety)",
    )
    parser.add_argument(
        "--skip-nulls", action="store_true", help="Skip permutation nulls"
    )
    parser.add_argument(
        "--skip-baseline", action="store_true", help="Skip gudhi baseline (slow at 5k)"
    )
    parser.add_argument(
        "--skip-appendix-b", action="store_true", help="Skip Hilbert/rank"
    )
    args = parser.parse_args()

    from dataclasses import asdict

    from trajectory_tda.topology.multipers_bifiltration import (
        auto_rips_radius,
        compute_regime_overlay,
        load_embeddings_and_income,
        maxmin_landmarks,
        run_appendix_b,
        run_bifiltration,
        run_p01_baseline_comparison,
        run_permutation_null,
        save_results,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    # Load data
    embeddings, income_scores = load_embeddings_and_income()

    # Landmark
    logger.info("Selecting %d maxmin landmarks...", args.n_landmarks)
    lm_idx = maxmin_landmarks(embeddings, args.n_landmarks)
    pts = embeddings[lm_idx]
    income = income_scores[lm_idx]

    # Rips radius
    radius = auto_rips_radius(pts)
    logger.info(
        "5k landmarks: mean_income=%.3f, std=%.3f, radius=%.3f",
        income.mean(),
        income.std(),
        radius,
    )

    # ── Step 1: Observed bifiltration ──
    if args.skip_nulls:
        logger.info("=" * 70)
        logger.info("STEP 1: Observed Bifiltration (no nulls)")
        logger.info("=" * 70)
        observed = run_bifiltration(pts, income, radius)
        null_result = None
    else:
        logger.info("=" * 70)
        logger.info("STEP 1+2: Bifiltration + %d Permutation Nulls", args.n_perms)
        logger.info("=" * 70)
        observed, null_result = run_permutation_null(
            pts,
            income,
            radius,
            n_permutations=args.n_perms,
            n_jobs=args.n_jobs,
        )
        plot_null_distribution(null_result, FIGURE_DIR)

    # ── Step 3: P01 baseline ──
    baseline = None
    if not args.skip_baseline:
        logger.info("=" * 70)
        logger.info("STEP 3: P01 Baseline Comparison")
        logger.info("=" * 70)
        baseline = run_p01_baseline_comparison(pts, income, radius)
        plot_baseline_comparison(baseline, FIGURE_DIR)
    else:
        logger.info("Skipping P01 baseline (--skip-baseline)")

    # ── Step 4: GMM regime overlay ──
    logger.info("=" * 70)
    logger.info("STEP 4: GMM Regime Overlay")
    logger.info("=" * 70)
    regime = compute_regime_overlay(pts, income, lm_idx, embeddings_full=embeddings)

    # ── Step 5: Appendix B (Hilbert + rank) ──
    appendix_b = None
    if not args.skip_appendix_b:
        logger.info("=" * 70)
        logger.info("STEP 5: Appendix B — Hilbert Function + Rank Invariant")
        logger.info("=" * 70)
        appendix_b = run_appendix_b(pts, income, radius, resolutions=[10, 20])

    # ── Save ──
    save_results(
        observed,
        null_result,
        baseline,
        regime,
        appendix_b=appendix_b,
        output_dir=RESULTS_DIR,
    )

    # ── Scale comparison plot ──
    results_2k = ROOT / "results" / "p04_multipers" / "p04_results.json"
    plot_scale_comparison(results_2k, asdict(observed))

    t_total = time.time() - t_start

    # ── Summary ──
    print("\n" + "=" * 70)
    print(f"P04 SCALE SENSITIVITY ({args.n_landmarks} LANDMARKS) COMPLETE")
    print("=" * 70)
    print(f"Landmarks: {args.n_landmarks}")
    print(f"Rips radius: {radius:.3f}")
    print(f"Simplices: {observed.n_simplices}")
    print(f"Total time: {t_total:.0f}s ({t_total / 60:.1f} min)")
    print()
    print("-- Observed --")
    h1s = observed.h1.stratification
    h1q = observed.h1.quartile_decomposition
    print(f"  H1 low-income fraction: {h1s.low_income_fraction:.3f}")
    print(f"  H1 quartile masses: {[f'{m:.0f}' for m in h1q.masses]}")
    print(f"  Q1/Q3 ratio: {h1q.ratio_q1_q3:.3f}")
    print()
    if null_result is not None:
        print("-- Permutation Null --")
        print(f"  N permutations: {null_result.n_permutations}")
        print(
            f"  H1 low-frac: observed={null_result.observed_h1_low_fraction:.3f}, "
            f"null_mean={np.mean(null_result.null_h1_low_fractions):.3f}, "
            f"p={null_result.p_value:.4f}"
        )
        print(
            f"  Q1/Q3: observed={null_result.observed_q1_q3_ratio:.3f}, "
            f"null_mean={np.mean(null_result.null_q1_q3_ratios):.3f}, "
            f"p={null_result.p_value_q1_q3:.4f}"
        )
        print(f"  Null time: {null_result.total_time_s:.0f}s")
        print()
    print("-- P01 Baseline --")
    if baseline is not None:
        print(
            f"  Full: H1={baseline['full']['h1_count']} ({baseline['full']['n_points']} pts)"
        )
        print(
            f"  Low Q1: H1={baseline['low_income_q1']['h1_count']} "
            f"({baseline['low_income_q1']['n_points']} pts)"
        )
        print(
            f"  High Q4: H1={baseline['high_income_q4']['h1_count']} "
            f"({baseline['high_income_q4']['n_points']} pts)"
        )
        print(
            f"  H1 density: full={baseline['h1_density_full']:.4f}, "
            f"low={baseline['h1_density_low']:.4f}, "
            f"high={baseline['h1_density_high']:.4f}"
        )
    else:
        print("  (skipped)")
    print()
    if appendix_b is not None:
        print("-- Appendix B --")
        for key, val in appendix_b.items():
            if hasattr(val, "low_income_fraction"):
                print(
                    f"  {key}: low_frac={val.low_income_fraction:.3f}, "
                    f"total={val.total_mass:.0f}"
                )
            elif hasattr(val, "income_persistence_stats"):
                stats = val.income_persistence_stats
                print(
                    f"  {key}: n={val.n_features}, "
                    f"born_low={stats.get('frac_born_low', 0):.3f}, "
                    f"persist_inf={stats.get('frac_persist_to_inf', 0):.3f}"
                )
        print()
    print(f"Results: {RESULTS_DIR / 'p04_results.json'}")
    print(f"Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
