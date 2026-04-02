"""P04 Production Run: Permutation Nulls + Baseline + Regime Overlay.

Executes the full P04 computation pipeline:
  1. Observed bifiltration (2,000 landmarks, quantile grid)
  2. 999 income-label permutation null tests
  3. P01 single-parameter baseline comparison
  4. GMM regime overlay on signed measure

Usage:
    uv run python trajectory_tda/scripts/p04_run_nulls.py
    uv run python trajectory_tda/scripts/p04_run_nulls.py --n-perms 99  # quick test

Output:
    results/p04_multipers/p04_results.json
    figures/trajectory_tda/p04/
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT / "results" / "p04_multipers"
FIGURE_DIR = ROOT / "figures" / "trajectory_tda" / "p04"


def plot_null_distribution(
    null_result,
    output_dir: Path,
) -> None:
    """Plot permutation null distribution with observed value."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("P04 Permutation Null Test: Income-Label Shuffles", fontsize=14)

    # H1 low-income fraction
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
    ax.set_title(f"Primary: H1 Low-Income Fraction (p = {null_result.p_value:.4f})")
    ax.legend(fontsize=9)

    # Q1/Q3 ratio
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
    ax.set_title(f"Secondary: Q1/Q3 Ratio (p = {null_result.p_value_q1_q3:.4f})")
    ax.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(output_dir / "null_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved null distribution figure")


def plot_baseline_comparison(baseline: dict, output_dir: Path) -> None:
    """Plot P01 baseline vs bifiltration comparison."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("P01 Baseline: Single-Parameter VR PH by Income Subset", fontsize=14)

    # H1 count by subset
    ax = axes[0]
    labels = ["Full", "Low (Q1)", "High (Q4)"]
    counts = [
        baseline["full"]["h1_count"],
        baseline["low_income_q1"]["h1_count"],
        baseline["high_income_q4"]["h1_count"],
    ]
    colors = ["gray", "#d62728", "#2ca02c"]
    ax.bar(labels, counts, color=colors)
    ax.set_ylabel("H1 Feature Count")
    ax.set_title("H1 Features by Income Subset")

    # H1 density (features per point)
    ax = axes[1]
    densities = [
        baseline["h1_density_full"],
        baseline["h1_density_low"],
        baseline["h1_density_high"],
    ]
    ax.bar(labels, densities, color=colors)
    ax.set_ylabel("H1 Features per Point")
    ax.set_title("H1 Density (normalised by subset size)")

    plt.tight_layout()
    fig.savefig(output_dir / "baseline_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved baseline comparison figure")


def plot_regime_income(regime: dict, output_dir: Path) -> None:
    """Plot GMM regime income distribution."""
    import matplotlib.pyplot as plt

    stats = regime["regime_income_stats"]
    regimes = sorted(stats.keys(), key=int)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("P01 GMM Regimes: Income Distribution", fontsize=14)

    # Mean income by regime
    ax = axes[0]
    means = [stats[r]["mean_income"] for r in regimes]
    counts = [stats[r]["count"] for r in regimes]
    colors = plt.cm.Set3(np.linspace(0, 1, len(regimes)))
    ax.bar([f"R{r}" for r in regimes], means, color=colors)
    ax.set_ylabel("Mean Income Score")
    ax.set_title("Mean Income by GMM Regime")
    for i, (m, c) in enumerate(zip(means, counts)):
        ax.text(i, m + 0.02, f"n={c}", ha="center", fontsize=8)

    # Low-income percentage by regime
    ax = axes[1]
    low_pcts = [stats[r]["low_income_pct"] * 100 for r in regimes]
    ax.bar([f"R{r}" for r in regimes], low_pcts, color=colors)
    ax.set_ylabel("% Below Median Income")
    ax.set_title("Low-Income Concentration by Regime")
    ax.axhline(50, color="gray", linestyle="--", alpha=0.5, label="50%")
    ax.legend()

    plt.tight_layout()
    fig.savefig(output_dir / "regime_income.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved regime income figure")


def main() -> None:
    """Run the full P04 computation pipeline."""
    parser = argparse.ArgumentParser(description="P04 Multipers Null Testing")
    parser.add_argument(
        "--n-landmarks", type=int, default=2000, help="Number of landmarks"
    )
    parser.add_argument(
        "--n-perms", type=int, default=999, help="Number of permutations"
    )
    parser.add_argument(
        "--n-jobs", type=int, default=-1, help="Parallelism (-1=all cores)"
    )
    args = parser.parse_args()

    from trajectory_tda.topology.multipers_bifiltration import (
        auto_rips_radius,
        compute_regime_overlay,
        load_embeddings_and_income,
        maxmin_landmarks,
        run_p01_baseline_comparison,
        run_permutation_null,
        save_results,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    embeddings, income_scores = load_embeddings_and_income()

    # Landmark
    logger.info("Selecting %d maxmin landmarks...", args.n_landmarks)
    lm_idx = maxmin_landmarks(embeddings, args.n_landmarks)
    pts = embeddings[lm_idx]
    income = income_scores[lm_idx]

    # Rips radius
    radius = auto_rips_radius(pts)

    # ── Step 1+2: Observed bifiltration + permutation nulls ──
    logger.info("=" * 70)
    logger.info("STEP 1+2: Bifiltration + Permutation Null Testing")
    logger.info("=" * 70)
    observed, null_result = run_permutation_null(
        pts,
        income,
        radius,
        n_permutations=args.n_perms,
        n_jobs=args.n_jobs,
    )
    plot_null_distribution(null_result, FIGURE_DIR)

    # ── Step 3: P01 baseline comparison ──
    logger.info("=" * 70)
    logger.info("STEP 3: P01 Single-Parameter Baseline Comparison")
    logger.info("=" * 70)
    baseline = run_p01_baseline_comparison(pts, income, radius)
    plot_baseline_comparison(baseline, FIGURE_DIR)

    # ── Step 4: GMM regime overlay ──
    logger.info("=" * 70)
    logger.info("STEP 4: GMM Regime Overlay")
    logger.info("=" * 70)
    regime = compute_regime_overlay(pts, income, lm_idx, embeddings_full=embeddings)
    plot_regime_income(regime, FIGURE_DIR)

    # ── Save everything ──
    save_results(observed, null_result, baseline, regime)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("P04 MULTIPERS COMPUTATION COMPLETE")
    print("=" * 70)
    print(f"Landmarks: {args.n_landmarks}")
    print(f"Rips radius: {radius:.3f}")
    print(f"Simplices: {observed.n_simplices}")
    print()
    print("-- Observed --")
    print(
        f"  H1 low-income fraction: {observed.h1.stratification.low_income_fraction:.3f}"
    )
    print(
        f"  H1 quartile masses: {[f'{m:.0f}' for m in observed.h1.quartile_decomposition.masses]}"
    )
    print(f"  Q1/Q3 ratio: {observed.h1.quartile_decomposition.ratio_q1_q3:.3f}")
    print()
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
    print(f"  Time: {null_result.total_time_s:.0f}s")
    print()
    print("-- P01 Baseline --")
    print(
        f"  Full: H1={baseline['full']['h1_count']} ({baseline['full']['n_points']} pts)"
    )
    print(
        f"  Low Q1: H1={baseline['low_income_q1']['h1_count']} ({baseline['low_income_q1']['n_points']} pts)"
    )
    print(
        f"  High Q4: H1={baseline['high_income_q4']['h1_count']} ({baseline['high_income_q4']['n_points']} pts)"
    )
    print(
        f"  H1 density: full={baseline['h1_density_full']:.4f}, "
        f"low={baseline['h1_density_low']:.4f}, "
        f"high={baseline['h1_density_high']:.4f}"
    )
    print()
    print("-- GMM Regimes --")
    for r, stats in sorted(
        regime["regime_income_stats"].items(), key=lambda x: int(x[0])
    ):
        print(
            f"  R{r}: n={stats['count']}, mean_income={stats['mean_income']:.2f}, "
            f"low_pct={stats['low_income_pct']:.1%}"
        )
    print()
    print(f"Results: {RESULTS_DIR / 'p04_results.json'}")
    print(f"Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
