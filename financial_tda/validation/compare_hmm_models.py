"""
Phase 10B - Task B.4: HMM Model Comparison
==========================================

Purpose:
    Compare baseline HMM (VIX only) vs τ-augmented HMM.
    Determine if τ adds informational value for regime detection.

Input:
    outputs/phase_10b/hmm_baseline_states.csv
    outputs/phase_10b/hmm_tau_states.csv

Output:
    outputs/phase_10b/hmm_comparison_report.md

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b"
BASELINE_FILE = OUTPUT_DIR / "hmm_baseline_states.csv"
TAU_FILE = OUTPUT_DIR / "hmm_tau_states.csv"
REPORT_FILE = OUTPUT_DIR / "hmm_comparison_report.md"

# Metrics from the model runs (manually extracted or re-run)
# These will be updated based on actual runs
BASELINE_METRICS = {
    "log_prob": -26429.63,
    "aic": 52991.27,
    "bic": 53433.30,
    "n_params": 66,  # 5 features
    "features": "ret_1d, ret_5d, ret_21d, vix, vix_5d_chg",
}

TAU_METRICS = {
    "log_prob": -34384.19,
    "aic": 68942.38,
    "bic": 69525.06,
    "n_params": 87,  # 6 features
    "features": "ret_1d, ret_5d, ret_21d, vix, vix_5d_chg, τ",
}

# Known crisis periods
CRISIS_PERIODS = {
    "2008 GFC": ("2008-09-15", "2009-03-09"),
    "2020 COVID": ("2020-02-20", "2020-04-01"),
    "2022 Bear Market": ("2022-06-01", "2022-10-15"),
}


def load_states():
    """Load state assignments from both models."""
    print("Loading state assignments...")

    baseline = pd.read_csv(BASELINE_FILE, index_col=0, parse_dates=True)
    tau = pd.read_csv(TAU_FILE, index_col=0, parse_dates=True)

    print(f"  Baseline: {len(baseline)} days")
    print(f"  τ-augmented: {len(tau)} days")

    return baseline, tau


def compute_state_agreement(baseline, tau):
    """Compute agreement between models on state assignments."""
    # Map labels for comparison
    agreement = (baseline["state_label"] == tau["state_label"]).mean()

    # Agreement by state
    state_agreement = {}
    for state in ["Calm", "Transition", "Crisis"]:
        mask = baseline["state_label"] == state
        if mask.sum() > 0:
            state_agreement[state] = (baseline.loc[mask, "state_label"] == tau.loc[mask, "state_label"]).mean()

    return agreement, state_agreement


def evaluate_crisis_detection(df, state_col):
    """Evaluate crisis detection accuracy."""
    results = {}
    for crisis_name, (start, end) in CRISIS_PERIODS.items():
        mask = (df.index >= start) & (df.index <= end)
        crisis_days = mask.sum()

        if crisis_days == 0:
            continue

        crisis_pct = (df.loc[mask, state_col] == "Crisis").mean()
        results[crisis_name] = crisis_pct

    return results


def generate_report(baseline, tau, agreement, state_agreement):
    """Generate comparison report."""
    report = []
    report.append("# HMM Model Comparison Report")
    report.append("")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    report.append("## Executive Summary")
    report.append("")
    report.append("This report compares two HMM regime detection models:")
    report.append("- **Baseline:** Uses returns + VIX only")
    report.append("- **τ-Augmented:** Uses returns + VIX + τ (topological complexity)")
    report.append("")

    # Model comparison table
    report.append("## Model Fit Comparison")
    report.append("")
    report.append("| Metric | Baseline | τ-Augmented | Winner |")
    report.append("|--------|----------|-------------|--------|")

    # AIC comparison (lower is better)
    aic_winner = "Baseline ✅" if BASELINE_METRICS["aic"] < TAU_METRICS["aic"] else "τ-Augmented ✅"
    report.append(f"| AIC | {BASELINE_METRICS['aic']:.2f} | {TAU_METRICS['aic']:.2f} | {aic_winner} |")

    # BIC comparison (lower is better)
    bic_winner = "Baseline ✅" if BASELINE_METRICS["bic"] < TAU_METRICS["bic"] else "τ-Augmented ✅"
    report.append(f"| BIC | {BASELINE_METRICS['bic']:.2f} | {TAU_METRICS['bic']:.2f} | {bic_winner} |")

    # Log-likelihood (higher is better, but more params)
    ll_winner = "Baseline ✅" if BASELINE_METRICS["log_prob"] > TAU_METRICS["log_prob"] else "τ-Augmented ✅"
    report.append(
        f"| Log-likelihood | {BASELINE_METRICS['log_prob']:.2f} | {TAU_METRICS['log_prob']:.2f} | {ll_winner} |"
    )

    report.append(f"| Parameters | {BASELINE_METRICS['n_params']} | {TAU_METRICS['n_params']} | — |")
    report.append("")

    # State agreement
    report.append("## State Agreement")
    report.append("")
    report.append(f"Overall agreement between models: **{agreement*100:.1f}%**")
    report.append("")
    report.append("| State | Agreement |")
    report.append("|-------|-----------|")
    for state, pct in state_agreement.items():
        report.append(f"| {state} | {pct*100:.1f}% |")
    report.append("")

    # Crisis detection comparison
    report.append("## Crisis Detection Comparison")
    report.append("")

    baseline_crisis = evaluate_crisis_detection(baseline, "state_label")
    tau_crisis = evaluate_crisis_detection(tau, "state_label")

    report.append("| Crisis | Baseline | τ-Augmented | Difference |")
    report.append("|--------|----------|-------------|------------|")
    for crisis_name in CRISIS_PERIODS.keys():
        b_pct = baseline_crisis.get(crisis_name, 0) * 100
        t_pct = tau_crisis.get(crisis_name, 0) * 100
        diff = t_pct - b_pct
        diff_str = f"+{diff:.1f}%" if diff >= 0 else f"{diff:.1f}%"
        report.append(f"| {crisis_name} | {b_pct:.1f}% | {t_pct:.1f}% | {diff_str} |")
    report.append("")

    # Interpretation
    report.append("## Interpretation")
    report.append("")

    # The key question: does τ add value?
    aic_diff = TAU_METRICS["aic"] - BASELINE_METRICS["aic"]
    bic_diff = TAU_METRICS["bic"] - BASELINE_METRICS["bic"]

    if aic_diff < 0 and bic_diff < 0:
        report.append("> [!IMPORTANT]")
        report.append("> **τ ADDS VALUE:** The τ-augmented model has lower AIC and BIC,")
        report.append("> indicating that the topological signal provides additional information")
        report.append("> for regime detection beyond what VIX alone captures.")
    elif aic_diff > 0 and bic_diff > 0:
        report.append("> [!NOTE]")
        report.append("> **τ DOES NOT ADD VALUE (by AIC/BIC):** The baseline model has")
        report.append("> lower information criteria, suggesting the additional τ feature")
        report.append("> does not sufficiently improve model fit to justify its complexity.")
        report.append("")
        report.append("However, this does NOT mean τ is useless. It may:")
        report.append("- Capture different aspects of market structure not reflected in regime classification")
        report.append("- Provide value through the conditional analysis (Track A)")
        report.append("- Be more useful as a complementary signal rather than regime input")
    else:
        report.append("> **MIXED RESULTS:** AIC and BIC give conflicting signals.")

    report.append("")

    # Why might τ not help HMM?
    report.append("### Why τ May Not Improve HMM")
    report.append("")
    report.append("1. **τ is a trend signal, not a level:** HMM detects regime levels (high/low VIX),")
    report.append("   while τ measures the *trend* in topological variance. These are different signals.")
    report.append("")
    report.append("2. **τ is already partially captured by VIX:** The 21% correlation between τ and VIX")
    report.append("   means some information overlaps.")
    report.append("")
    report.append("3. **HMM may not be the right model for τ:** A changepoint model or")
    report.append("   early warning system might better utilize the trend information in τ.")
    report.append("")

    report.append("## Conclusions")
    report.append("")

    if aic_diff > 0 and bic_diff > 0:
        report.append("- ❌ τ does not improve regime detection by AIC/BIC criteria")
        report.append("- ✅ But Track A showed τ has predictive value for drawdowns")
        report.append("- 💡 τ may be better used as a *complementary* early warning signal,")
        report.append("  not as an input to regime classification")
    else:
        report.append("- ✅ τ improves regime detection by information criteria")
        report.append("- Combined with Track A results, τ provides actionable signal")

    report.append("")
    report.append("---")
    report.append("*Generated by Phase 10B Task B.4*")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK B.4: HMM MODEL COMPARISON")
    print("=" * 60)

    # Load states
    baseline, tau = load_states()

    # Compute agreement
    print("\nComputing state agreement...")
    agreement, state_agreement = compute_state_agreement(baseline, tau)
    print(f"  Overall agreement: {agreement*100:.1f}%")
    for state, pct in state_agreement.items():
        print(f"  {state}: {pct*100:.1f}%")

    # Generate report
    print("\nGenerating comparison report...")
    report = generate_report(baseline, tau, agreement, state_agreement)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Saved report to: {REPORT_FILE}")

    # Key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    aic_diff = TAU_METRICS["aic"] - BASELINE_METRICS["aic"]
    bic_diff = TAU_METRICS["bic"] - BASELINE_METRICS["bic"]

    print(f"\nAIC difference (τ - baseline): {aic_diff:+.2f}")
    print(f"BIC difference (τ - baseline): {bic_diff:+.2f}")

    if aic_diff > 0 and bic_diff > 0:
        print("\nCONCLUSION: τ does NOT improve HMM regime detection by information criteria.")
        print("However, Track A showed τ has predictive value for drawdowns.")
    else:
        print("\nCONCLUSION: τ IMPROVES HMM regime detection.")

    print("\n" + "=" * 60)
    print("TASK B.4 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
