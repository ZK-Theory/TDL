"""
Phase 10B - Task C.3: Compare Diagram Statistics
=================================================

Purpose:
    Quantitative comparison of persistence diagram statistics between
    GFC and COVID to understand why τ behaves differently.

Input:
    outputs/phase_10b/persistence_diagrams/gfc_2007_2008/diagram_summary.csv
    outputs/phase_10b/persistence_diagrams/covid_2019_2020/diagram_summary.csv

Output:
    outputs/phase_10b/diagram_comparison_report.md

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
from scipy.stats import ttest_ind, mannwhitneyu
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DIAGRAMS_DIR = BASE_DIR / "outputs" / "phase_10b" / "persistence_diagrams"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b"
REPORT_FILE = OUTPUT_DIR / "diagram_comparison_report.md"

# Crisis configurations
CRISIS_CONFIGS = {
    "gfc_2007_2008": {
        "name": "2008 GFC",
        "tau_sign": "positive",  # From Phase 10 findings
        "interpretation": "Endogenous buildup - variance increasing",
    },
    "covid_2019_2020": {
        "name": "2020 COVID",
        "tau_sign": "negative",  # From Phase 10 findings
        "interpretation": "Exogenous shock - variance decreasing",
    },
}


def load_summaries():
    """Load diagram summaries for both crises."""
    summaries = {}
    for crisis_id, config in CRISIS_CONFIGS.items():
        summary_file = DIAGRAMS_DIR / crisis_id / "diagram_summary.csv"
        if summary_file.exists():
            df = pd.read_csv(summary_file, index_col=0, parse_dates=True)
            summaries[crisis_id] = df
            print(f"Loaded {crisis_id}: {len(df)} days")
        else:
            print(f"Warning: {summary_file} not found")
    return summaries


def compute_statistics(df, name):
    """Compute summary statistics for a crisis period."""
    stats = {
        "name": name,
        "n_days": len(df),
        "n_h1_mean": df["n_h1"].mean(),
        "n_h1_std": df["n_h1"].std(),
        "h1_total_mean": df["h1_total_persistence"].mean(),
        "h1_total_std": df["h1_total_persistence"].std(),
        "h1_total_var": df["h1_total_persistence"].var(),
        "h1_lifetime_mean": df["h1_mean_lifetime"].mean(),
        "h1_lifetime_std": df["h1_mean_lifetime"].std(),
        "h1_max_mean": df["h1_max_lifetime"].mean(),
        "h1_max_std": df["h1_max_lifetime"].std(),
    }

    # Compute trend (variance of persistence over time)
    # This is what τ captures
    rolling_var = df["h1_total_persistence"].rolling(20, min_periods=5).var()
    stats["variance_of_variance"] = rolling_var.var()
    stats["variance_trend"] = rolling_var.iloc[-5:].mean() - rolling_var.iloc[:5].mean()

    return stats


def compare_statistics(summaries):
    """Compare statistics between crises with statistical tests."""
    gfc = summaries["gfc_2007_2008"]
    covid = summaries["covid_2019_2020"]

    metrics = ["n_h1", "h1_total_persistence", "h1_mean_lifetime", "h1_max_lifetime"]
    comparisons = {}

    for metric in metrics:
        gfc_vals = gfc[metric].dropna()
        covid_vals = covid[metric].dropna()

        # T-test
        t_stat, t_pval = ttest_ind(gfc_vals, covid_vals, equal_var=False)

        # Mann-Whitney
        u_stat, u_pval = mannwhitneyu(gfc_vals, covid_vals, alternative="two-sided")

        comparisons[metric] = {
            "gfc_mean": gfc_vals.mean(),
            "gfc_std": gfc_vals.std(),
            "covid_mean": covid_vals.mean(),
            "covid_std": covid_vals.std(),
            "diff": gfc_vals.mean() - covid_vals.mean(),
            "t_stat": t_stat,
            "t_pval": t_pval,
            "u_pval": u_pval,
        }

    return comparisons


def interpret_findings(gfc_stats, covid_stats, comparisons):
    """Generate interpretation of the topological differences."""
    interpretations = []

    # Key observation 1: Variance of persistence
    var_ratio = gfc_stats["h1_total_var"] / covid_stats["h1_total_var"]

    if var_ratio > 1.5:
        interpretations.append(
            f"**GFC had {var_ratio:.1f}x higher H1 persistence variance** than COVID. "
            "This means the topological structure was more volatile during the GFC buildup."
        )
    else:
        interpretations.append(f"H1 persistence variance was similar (ratio: {var_ratio:.1f}x).")

    # Key observation 2: Trend direction
    if gfc_stats["variance_trend"] > 0 and covid_stats["variance_trend"] < 0:
        interpretations.append(
            "**Variance trend directions are opposite:** GFC variance increased pre-crisis "
            "(positive τ), while COVID variance decreased (negative τ). This confirms "
            "the Phase 10 finding."
        )

    # Key observation 3: Number of features
    n_diff = comparisons["n_h1"]["diff"]
    if abs(n_diff) > 0.5:
        more_or_fewer = "more" if n_diff > 0 else "fewer"
        interpretations.append(f"GFC had {abs(n_diff):.1f} {more_or_fewer} H1 features on average than COVID.")

    # Key observation 4: Persistence magnitude
    pers_diff = comparisons["h1_total_persistence"]["diff"]
    pct_diff = pers_diff / covid_stats["h1_total_mean"] * 100 if covid_stats["h1_total_mean"] > 0 else 0
    if abs(pct_diff) > 20:
        higher_or_lower = "higher" if pers_diff > 0 else "lower"
        interpretations.append(f"GFC total H1 persistence was {abs(pct_diff):.0f}% {higher_or_lower} than COVID.")

    return interpretations


def generate_report(summaries, comparisons, gfc_stats, covid_stats, interpretations):
    """Generate markdown report."""
    report = []
    report.append("# Phase 10B: Persistence Diagram Comparison Report")
    report.append("")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    report.append("## Executive Summary")
    report.append("")
    report.append("This analysis compares the raw topology (H1 persistence diagrams) between")
    report.append("the 2008 GFC and 2020 COVID crises to understand WHY τ has opposite signs.")
    report.append("")
    report.append("| Crisis | τ Sign | Interpretation |")
    report.append("|--------|--------|----------------|")
    for crisis_id, config in CRISIS_CONFIGS.items():
        report.append(f"| {config['name']} | {config['tau_sign']} | {config['interpretation']} |")
    report.append("")

    report.append("## Sample Sizes")
    report.append("")
    report.append("| Period | Days Analyzed |")
    report.append("|--------|---------------|")
    report.append(f"| 2008 GFC | {gfc_stats['n_days']} |")
    report.append(f"| 2020 COVID | {covid_stats['n_days']} |")
    report.append("")

    report.append("## Topological Statistics Comparison")
    report.append("")
    report.append("| Metric | GFC (Mean ± SD) | COVID (Mean ± SD) | Diff | p-value |")
    report.append("|--------|-----------------|-------------------|------|---------|")

    for metric, comp in comparisons.items():
        metric_name = metric.replace("h1_", "H1 ").replace("_", " ").title()
        gfc_str = f"{comp['gfc_mean']:.4f} ± {comp['gfc_std']:.4f}"
        covid_str = f"{comp['covid_mean']:.4f} ± {comp['covid_std']:.4f}"
        diff_str = f"{comp['diff']:+.4f}"
        sig = (
            "***" if comp["t_pval"] < 0.001 else "**" if comp["t_pval"] < 0.01 else "*" if comp["t_pval"] < 0.05 else ""
        )
        report.append(f"| {metric_name} | {gfc_str} | {covid_str} | {diff_str} | {comp['t_pval']:.4f}{sig} |")

    report.append("")

    report.append("## Variance Analysis (Key to τ Signal)")
    report.append("")
    report.append("| Statistic | GFC | COVID | Ratio |")
    report.append("|-----------|-----|-------|-------|")
    report.append(
        f"| H1 Persistence Variance | {gfc_stats['h1_total_var']:.6f} | {covid_stats['h1_total_var']:.6f} | {gfc_stats['h1_total_var']/covid_stats['h1_total_var']:.1f}x |"
    )
    report.append(f"| Variance Trend | {gfc_stats['variance_trend']:+.6f} | {covid_stats['variance_trend']:+.6f} | — |")
    report.append("")

    report.append("## Key Findings")
    report.append("")
    for i, interp in enumerate(interpretations, 1):
        report.append(f"{i}. {interp}")
    report.append("")

    report.append("## Interpretation: Why τ is Positive Pre-GFC but Negative Pre-COVID")
    report.append("")
    report.append("### The Topological Mechanism")
    report.append("")
    report.append("1. **GFC (τ = +0.88):** The financial system was experiencing a gradual")
    report.append("   **buildup of interconnected stress**. As subprime mortgages deteriorated,")
    report.append("   correlations between assets increased erratically, creating new topological")
    report.append("   loops (H1 features) that appeared and disappeared. This **increased variance**")
    report.append("   in topological complexity signals growing structural instability.")
    report.append("")
    report.append("2. **COVID (τ = -0.80):** The pandemic was an **exogenous shock** that hit")
    report.append("   all markets simultaneously. There was no gradual buildup—instead, all")
    report.append("   assets became highly correlated very quickly. The topology became **more**")
    report.append("   **stable** (lower variance) as the market structure collapsed into a")
    report.append("   single correlated mass.")
    report.append("")

    report.append("### Implications for Crisis Prediction")
    report.append("")
    report.append("| τ Pattern | Crisis Type | Mechanism | Lead Time |")
    report.append("|-----------|-------------|-----------|-----------|")
    report.append("| Rising τ (positive) | Endogenous | Internal stress accumulation | Months |")
    report.append("| Falling τ (negative) | Exogenous | Sudden external shock | Days/Weeks |")
    report.append("")

    report.append("This explains why positive τ spikes have **higher** drawdown probability")
    report.append("(confirmed in Track A): they signal crises that are truly building, giving")
    report.append("more warning time but also more potential for large moves.")
    report.append("")

    report.append("---")
    report.append("*Generated by Phase 10B Task C.3*")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK C.3: DIAGRAM COMPARISON STATISTICS")
    print("=" * 60)

    # Load summaries
    summaries = load_summaries()

    if len(summaries) < 2:
        print("Error: Need both crisis summaries")
        return

    # Compute statistics
    print("\nComputing statistics...")
    gfc_stats = compute_statistics(summaries["gfc_2007_2008"], "2008 GFC")
    covid_stats = compute_statistics(summaries["covid_2019_2020"], "2020 COVID")

    # Compare
    print("Comparing distributions...")
    comparisons = compare_statistics(summaries)

    # Interpret
    print("Generating interpretations...")
    interpretations = interpret_findings(gfc_stats, covid_stats, comparisons)

    # Generate report
    report = generate_report(summaries, comparisons, gfc_stats, covid_stats, interpretations)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\nSaved report to: {REPORT_FILE}")

    # Print key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    for interp in interpretations:
        print(f"\n• {interp}")

    print("\n" + "=" * 60)
    print("TASK C.3 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
