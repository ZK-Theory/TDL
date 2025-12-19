"""
Phase 10B - Task A.2: Conditional Return Analysis
==================================================

Purpose:
    Compare return distributions across τ spike groups to test if τ sign
    predicts crisis type/severity (endogenous vs exogenous).

Input:
    outputs/phase_10b/tau_spikes_events.csv
    outputs/phase_10/continuous_signal_2000_2025.csv

Output:
    outputs/phase_10b/conditional_returns_report.md

Hypothesis:
    - Positive τ spikes (variance increasing) → Endogenous crisis buildup
    - Negative τ spikes (variance decreasing) → Exogenous shock signature

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, mannwhitneyu
from pathlib import Path
import yfinance as yf
from datetime import timedelta

# ============================================================================
# CONFIGURATION (LOCKED - NO P-HACKING)
# ============================================================================
TAU_HIGH_THRESHOLD = 0.5  # Positive spike: τ > +0.5
TAU_LOW_THRESHOLD = -0.5  # Negative spike: τ < -0.5
TAU_CONTROL_RANGE = 0.3  # Control: |τ| < 0.3

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
SPIKES_FILE = BASE_DIR / "outputs" / "phase_10b" / "tau_spikes_events.csv"
TAU_FILE = BASE_DIR / "outputs" / "phase_10" / "continuous_signal_2000_2025.csv"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b"
REPORT_FILE = OUTPUT_DIR / "conditional_returns_report.md"


def load_data():
    """Load spike events and full τ series."""
    print("Loading data...")

    # Load spike events
    spikes_df = pd.read_csv(SPIKES_FILE, index_col=0, parse_dates=True)
    print(f"  Loaded {len(spikes_df)} spike events")

    # Load full τ series for control group
    tau_df = pd.read_csv(TAU_FILE, index_col=0, parse_dates=True)
    print(f"  Loaded {len(tau_df)} days of τ data")

    return spikes_df, tau_df


def fetch_spx_returns(start_date, end_date):
    """Fetch S&P 500 data and compute forward returns for all days."""
    print("Fetching S&P 500 data...")
    extended_end = pd.to_datetime(end_date) + timedelta(days=120)

    spx = yf.download("^GSPC", start=start_date, end=extended_end, progress=False)
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)

    close = spx["Close"]

    # Compute forward 30d returns and max drawdowns for all days
    fwd_ret_30d = close.pct_change(periods=30).shift(-30)

    # Max drawdown in next 30 days
    max_dd_30d = pd.Series(index=close.index, dtype=float)
    for i in range(len(close) - 30):
        window = close.iloc[i : i + 31]
        current = close.iloc[i]
        min_future = window.min()
        max_dd_30d.iloc[i] = (current - min_future) / current

    return pd.DataFrame({"fwd_ret_30d": fwd_ret_30d, "max_dd_30d": max_dd_30d})


def create_control_group(tau_df, spikes_df, spx_returns):
    """Create control group: days where |τ| < 0.3."""
    print("Creating control group...")

    # Control: |τ| < 0.3 and not a spike day
    control_mask = tau_df["Tau"].abs() < TAU_CONTROL_RANGE
    control_dates = tau_df[control_mask].index

    # Exclude spike dates
    spike_dates = set(spikes_df.index)
    control_dates = [d for d in control_dates if d not in spike_dates]

    # Get returns for control dates
    control_returns = spx_returns.loc[spx_returns.index.isin(control_dates)].dropna()
    print(f"  Control group: {len(control_returns)} days")

    return control_returns


def statistical_tests(group1, group2, name1, name2, metric):
    """Perform t-test and Mann-Whitney U test."""
    g1 = group1[metric].dropna()
    g2 = group2[metric].dropna()

    # T-test
    t_stat, t_pval = ttest_ind(g1, g2, equal_var=False)

    # Mann-Whitney U (non-parametric)
    u_stat, u_pval = mannwhitneyu(g1, g2, alternative="two-sided")

    return {
        "n1": len(g1),
        "n2": len(g2),
        "mean1": g1.mean(),
        "mean2": g2.mean(),
        "std1": g1.std(),
        "std2": g2.std(),
        "t_stat": t_stat,
        "t_pval": t_pval,
        "u_stat": u_stat,
        "u_pval": u_pval,
        "diff": g1.mean() - g2.mean(),
    }


def compute_drawdown_probability(df, threshold=0.05):
    """Compute probability of >5% drawdown."""
    vals = df["max_dd_30d"].dropna()
    if len(vals) == 0:
        return np.nan
    return (vals > threshold).mean()


def generate_report(pos_spikes, neg_spikes, control, all_results):
    """Generate markdown report."""

    report = []
    report.append("# Phase 10B: Conditional Returns Analysis Report")
    report.append("")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")
    report.append("## Executive Summary")
    report.append("")
    report.append("This analysis tests whether τ sign predicts crisis type:")
    report.append("- **Positive τ spikes** (τ > +0.5): Variance increasing → Endogenous crisis?")
    report.append("- **Negative τ spikes** (τ < -0.5): Variance decreasing → Exogenous shock?")
    report.append("")

    # Group sizes
    report.append("## Sample Sizes")
    report.append("")
    report.append("| Group | N | Description |")
    report.append("|-------|---|-------------|")
    report.append(f"| Positive Spikes | {len(pos_spikes)} | τ > +0.5 |")
    report.append(f"| Negative Spikes | {len(neg_spikes)} | τ < -0.5 |")
    report.append(f"| Control | {len(control)} | \\|τ\\| < 0.3 |")
    report.append("")

    # Forward Returns Analysis
    report.append("## Forward 30-Day Returns")
    report.append("")
    report.append("| Comparison | Mean₁ | Mean₂ | Diff | t-stat | p-value | Significant? |")
    report.append("|------------|-------|-------|------|--------|---------|--------------|")

    for name, res in all_results["fwd_ret_30d"].items():
        sig = "✅ Yes" if res["t_pval"] < 0.05 else "❌ No"
        report.append(
            f"| {name} | {res['mean1']*100:.2f}% | {res['mean2']*100:.2f}% | {res['diff']*100:.2f}% | {res['t_stat']:.2f} | {res['t_pval']:.4f} | {sig} |"
        )

    report.append("")

    # Drawdown Analysis
    report.append("## Maximum 30-Day Drawdown")
    report.append("")
    report.append("| Comparison | Mean₁ | Mean₂ | Diff | t-stat | p-value | Significant? |")
    report.append("|------------|-------|-------|------|--------|---------|--------------|")

    for name, res in all_results["max_dd_30d"].items():
        sig = "✅ Yes" if res["t_pval"] < 0.05 else "❌ No"
        report.append(
            f"| {name} | {res['mean1']*100:.2f}% | {res['mean2']*100:.2f}% | {res['diff']*100:.2f}% | {res['t_stat']:.2f} | {res['t_pval']:.4f} | {sig} |"
        )

    report.append("")

    # Drawdown Probability
    report.append("## Probability of >5% Drawdown")
    report.append("")
    p_pos = compute_drawdown_probability(pos_spikes)
    p_neg = compute_drawdown_probability(neg_spikes)
    p_ctrl = compute_drawdown_probability(control)

    report.append("| Group | P(Drawdown > 5%) |")
    report.append("|-------|------------------|")
    report.append(f"| Positive Spikes | {p_pos*100:.1f}% |")
    report.append(f"| Negative Spikes | {p_neg*100:.1f}% |")
    report.append(f"| Control | {p_ctrl*100:.1f}% |")
    report.append("")

    # Non-parametric tests
    report.append("## Non-Parametric Tests (Mann-Whitney U)")
    report.append("")
    report.append("| Comparison | Metric | U-statistic | p-value | Significant? |")
    report.append("|------------|--------|-------------|---------|--------------|")

    for metric in ["fwd_ret_30d", "max_dd_30d"]:
        for name, res in all_results[metric].items():
            sig = "✅ Yes" if res["u_pval"] < 0.05 else "❌ No"
            report.append(f"| {name} | {metric} | {res['u_stat']:.0f} | {res['u_pval']:.4f} | {sig} |")

    report.append("")

    # Interpretation
    report.append("## Interpretation")
    report.append("")

    # Check positive spike hypothesis
    pos_vs_ctrl_ret = all_results["fwd_ret_30d"]["Pos vs Control"]
    pos_vs_ctrl_dd = all_results["max_dd_30d"]["Pos vs Control"]
    neg_vs_ctrl_ret = all_results["fwd_ret_30d"]["Neg vs Control"]
    neg_vs_ctrl_dd = all_results["max_dd_30d"]["Neg vs Control"]

    report.append("### Positive τ Spikes (Endogenous Crisis Hypothesis)")
    report.append("")
    if pos_vs_ctrl_dd["t_pval"] < 0.05 and pos_vs_ctrl_dd["diff"] > 0:
        report.append("> [!IMPORTANT]")
        report.append("> **CONFIRMED:** Positive τ spikes have significantly higher drawdowns than control")
        report.append(f"> (+{pos_vs_ctrl_dd['diff']*100:.2f}%, p={pos_vs_ctrl_dd['t_pval']:.4f}).")
        report.append("> This supports the **endogenous crisis buildup** interpretation.")
    elif pos_vs_ctrl_dd["t_pval"] < 0.05:
        report.append(f"> Result is significant but in unexpected direction (diff={pos_vs_ctrl_dd['diff']*100:.2f}%)")
    else:
        report.append(f"> **NOT CONFIRMED:** No significant difference in drawdowns (p={pos_vs_ctrl_dd['t_pval']:.4f})")

    report.append("")
    report.append("### Negative τ Spikes (Exogenous Shock Hypothesis)")
    report.append("")
    if neg_vs_ctrl_dd["t_pval"] < 0.05:
        report.append("> [!NOTE]")
        report.append("> Negative τ spikes show significantly different drawdowns from control")
        report.append(f"> (diff={neg_vs_ctrl_dd['diff']*100:.2f}%, p={neg_vs_ctrl_dd['t_pval']:.4f}).")
    else:
        report.append(f"> **NOT CONFIRMED:** No significant difference in drawdowns (p={neg_vs_ctrl_dd['t_pval']:.4f})")

    report.append("")

    # Pos vs Neg comparison
    pos_vs_neg_ret = all_results["fwd_ret_30d"]["Pos vs Neg"]
    pos_vs_neg_dd = all_results["max_dd_30d"]["Pos vs Neg"]

    report.append("### Positive vs Negative Spikes (Direct Comparison)")
    report.append("")
    if pos_vs_neg_dd["t_pval"] < 0.05:
        direction = "higher" if pos_vs_neg_dd["diff"] > 0 else "lower"
        report.append(f"> Positive spikes have **{direction}** drawdowns than negative spikes")
        report.append(f"> (diff={pos_vs_neg_dd['diff']*100:.2f}%, p={pos_vs_neg_dd['t_pval']:.4f}).")
    else:
        report.append("> No significant difference in drawdowns between positive and negative spikes.")

    report.append("")
    report.append("## Conclusions")
    report.append("")

    # Overall assessment
    confirmed_hypotheses = 0
    if pos_vs_ctrl_dd["t_pval"] < 0.05 and pos_vs_ctrl_dd["diff"] > 0:
        confirmed_hypotheses += 1
    if neg_vs_ctrl_dd["t_pval"] < 0.05:
        confirmed_hypotheses += 1

    if confirmed_hypotheses >= 1:
        report.append("Track A analysis provides **partial evidence** that τ sign contains predictive information:")
        report.append("")
        if pos_vs_ctrl_dd["t_pval"] < 0.05 and pos_vs_ctrl_dd["diff"] > 0:
            report.append("- ✅ Positive τ spikes predict higher drawdown risk (endogenous buildup)")
        if neg_vs_ctrl_dd["t_pval"] < 0.05:
            report.append("- ✅ Negative τ spikes show distinct behavior (potential exogenous signature)")
    else:
        report.append("Track A analysis did **not confirm** the hypotheses about τ sign predicting crisis type.")

    report.append("")
    report.append("---")
    report.append("")
    report.append("*Generated by Phase 10B Task A.2*")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK A.2: CONDITIONAL RETURN ANALYSIS")
    print("=" * 60)

    # Load data
    spikes_df, tau_df = load_data()

    # Split spikes by sign
    pos_spikes = spikes_df[spikes_df["tau_sign"] == "positive"]
    neg_spikes = spikes_df[spikes_df["tau_sign"] == "negative"]
    print(f"\nPositive spikes: {len(pos_spikes)}")
    print(f"Negative spikes: {len(neg_spikes)}")

    # Fetch SPX returns for control group
    start_date = tau_df.index.min()
    end_date = tau_df.index.max()
    spx_returns = fetch_spx_returns(start_date, end_date)

    # Create control group
    control = create_control_group(tau_df, spikes_df, spx_returns)

    # Statistical tests
    print("\nRunning statistical tests...")
    all_results = {"fwd_ret_30d": {}, "max_dd_30d": {}}

    for metric in ["fwd_ret_30d", "max_dd_30d"]:
        # Pos vs Control
        all_results[metric]["Pos vs Control"] = statistical_tests(pos_spikes, control, "Positive", "Control", metric)

        # Neg vs Control
        all_results[metric]["Neg vs Control"] = statistical_tests(neg_spikes, control, "Negative", "Control", metric)

        # Pos vs Neg
        all_results[metric]["Pos vs Neg"] = statistical_tests(pos_spikes, neg_spikes, "Positive", "Negative", metric)

    # Generate report
    print("\nGenerating report...")
    report = generate_report(pos_spikes, neg_spikes, control, all_results)

    # Save report
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\nSaved report to: {REPORT_FILE}")

    # Print key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    for metric in ["fwd_ret_30d", "max_dd_30d"]:
        print(f"\n{metric}:")
        for name, res in all_results[metric].items():
            sig = "***" if res["t_pval"] < 0.05 else ""
            print(f"  {name}: diff={res['diff']*100:.2f}%, p={res['t_pval']:.4f} {sig}")

    print("\n" + "=" * 60)
    print("TASK A.2 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
