"""
Phase 10.3: Time-Stability Analysis
===================================

Purpose:
    Check if the Tau-VIX relationship is stable across different market regimes.
    This tests the "Cherry-Picking" hypothesis.

    Eras:
    1. 2000-2008 (Pre-GFC / Gidea & Katz era)
    2. 2008-2016 (GFC & Post-Crisis)
    3. 2016-2024 (Modern / COVID)

Input:
    - outputs/phase_10/continuous_signal_2000_2025.csv

Output:
    - outputs/phase_10/time_stability_report.txt
"""

import pandas as pd
from scipy.stats import pearsonr

SIGNAL_FILE = "outputs/phase_10/continuous_signal_2000_2025.csv"
REPORT_FILE = "outputs/phase_10/time_stability_report.txt"


def run_stability_analysis():
    print("=" * 80)
    print("PHASE 10.3: TIME-STABILITY ANALYSIS")
    print("=" * 80)

    # 1. Load Data
    print(f"Loading signal data from {SIGNAL_FILE}...")
    df = pd.read_csv(SIGNAL_FILE, index_col=0, parse_dates=True)

    # 2. Define Eras
    eras = [
        ("Era 1: Pre-GFC", "2000-01-01", "2008-01-01"),
        ("Era 2: Crisis & Post", "2008-01-01", "2016-01-01"),
        ("Era 3: Modern/COVID", "2016-01-01", "2024-12-31"),
    ]

    results = []
    results.append("TIME-STABILITY ANALYSIS REPORT")
    results.append("==============================")

    # 3. Analyze Each Era
    for name, start, end in eras:
        sub_df = df[start:end]
        n_obs = len(sub_df)

        results.append(f"\n{name} ({start} to {end})")
        results.append("-" * 40)
        results.append(f"Observations: {n_obs}")

        if n_obs < 100:
            results.append(">> INSUFFICIENT DATA")
            continue

        # Correlations
        r, p = pearsonr(sub_df["Tau"], sub_df["VIX"])
        results.append(f"Correlation (Tau vs VIX): {r:.4f} (p={p:.4e})")

        # Mean Values
        results.append(f"Mean Tau: {sub_df['Tau'].mean():.4f}")
        results.append(f"Mean VIX: {sub_df['VIX'].mean():.4f}")

        # Interpretation
        if abs(r) > 0.6:
            results.append(">> STATUS: Strong Coupling (Tau ~ VIX)")
        else:
            results.append(">> STATUS: Decoupled / Independent")

    # 4. Save Report
    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(results) + "\n")

    print("\n".join(results))
    print(f"\nReport saved to {REPORT_FILE}")


if __name__ == "__main__":
    run_stability_analysis()
