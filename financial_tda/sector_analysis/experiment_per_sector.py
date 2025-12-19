"""
Experiment B: Per-Sector Topological Analysis

For each of the 9 sectors, compute sector-specific topological features
using a rolling correlation matrix approach. This identifies WHERE in
the market stress originates.

Key Insight: Instead of using individual stock constituents (data availability issues),
we use the correlation structure between each sector and all others, creating
a per-sector "stress signature."

Method:
- For each sector S, compute rolling correlation of S with all other sectors
- Track how S's correlation pattern changes over time
- High τ in sector S before crisis = S is the stress origin

Expected Outcomes:
- XLK shows elevated τ before Dotcom 2000
- XLF shows elevated τ before GFC 2008
- XLE shows elevated τ before COVID 2020
"""

import sys
import os
import numpy as np
import pandas as pd
from scipy.stats import kendalltau

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sector_analysis.fetch_sector_data import fetch_sector_data, compute_log_returns, SECTOR_ETFS, OUTPUT_DIR

# Configuration - MUST MATCH G&K METHODOLOGY
CORRELATION_WINDOW = 60  # Rolling correlation window
VARIANCE_WINDOW = 500  # Rolling variance window (G&K standard - CRITICAL)
PRE_CRISIS_WINDOW = 250  # Pre-crisis analysis window

# Crisis events
EVENTS = [
    {"name": "2000 Dotcom", "date": "2000-03-10"},
    {"name": "2008 GFC", "date": "2008-09-15"},
    {"name": "2020 COVID", "date": "2020-03-16"},
    {"name": "2022 Rate Shock", "date": "2022-06-13"},
]


def compute_sector_correlation_features(returns, sector):
    """
    For a given sector, compute rolling correlation with all other sectors.

    Returns:
        DataFrame with rolling mean correlation and correlation variance metrics
    """
    other_sectors = [s for s in returns.columns if s != sector]

    # Compute rolling correlation of this sector with each other
    correlations = pd.DataFrame(index=returns.index)
    for other in other_sectors:
        corr = returns[sector].rolling(CORRELATION_WINDOW).corr(returns[other])
        correlations[f"{sector}-{other}"] = corr

    # Key features:
    # 1. Mean correlation: How correlated is this sector with others?
    # 2. Correlation variance: How unstable is the correlation pattern?
    features = pd.DataFrame(index=returns.index)
    features["MeanCorr"] = correlations.mean(axis=1)
    features["CorrVar"] = correlations.var(axis=1)

    # Stressed sectors show INCREASING mean correlation (contagion)
    # and/or INCREASING correlation variance (instability)
    features["StressMetric"] = features["MeanCorr"].rolling(VARIANCE_WINDOW).var()

    return features.dropna()


def analyze_sector_for_crisis(features, sector, event_date, pre_crisis_window=PRE_CRISIS_WINDOW):
    """
    Compute Kendall-τ for a sector's stress metric before a crisis.
    """
    if event_date < features.index[0] or event_date > features.index[-1]:
        return np.nan, np.nan, "Out of range"

    # Find nearest date
    if event_date not in features.index:
        locs = features.index.get_indexer([event_date], method="nearest")
        event_date = features.index[locs[0]]

    end_loc = features.index.get_loc(event_date)
    start_loc = max(0, end_loc - pre_crisis_window)

    if end_loc - start_loc < 50:
        return np.nan, np.nan, "Insufficient data"

    series = features["StressMetric"].iloc[start_loc:end_loc].dropna()
    if len(series) < 30:
        return np.nan, np.nan, "Segment too short"

    tau, p_value = kendalltau(np.arange(len(series)), series.values)
    return tau, p_value, "OK"


def main():
    print("=" * 70)
    print("Experiment B: Per-Sector Topological Analysis")
    print("Identifying where stress originates before each crisis")
    print("=" * 70)

    # Fetch data
    print("\n[1] Loading sector data...")
    prices = fetch_sector_data(save=False)
    returns = compute_log_returns(prices, standardize=True, save=False)
    print(f"    Returns: {returns.shape[0]} days, {returns.shape[1]} sectors")
    print(f"    Date range: {returns.index[0].date()} to {returns.index[-1].date()}")

    # Compute features for each sector
    print("\n[2] Computing per-sector correlation features...")
    sector_features = {}
    for sector in SECTOR_ETFS.keys():
        sector_features[sector] = compute_sector_correlation_features(returns, sector)
        print(f"    {sector}: {len(sector_features[sector])} valid observations")

    # Analyze each crisis
    print("\n[3] Analyzing sector τ values for each crisis...\n")

    all_results = []
    for event in EVENTS:
        event_date = pd.to_datetime(event["date"])
        print(f"--- {event['name']} ({event['date']}) ---")

        crisis_results = []
        for sector in SECTOR_ETFS.keys():
            features = sector_features[sector]
            tau, p_val, status = analyze_sector_for_crisis(features, sector, event_date)

            crisis_results.append(
                {
                    "Event": event["name"],
                    "Sector": sector,
                    "SectorName": SECTOR_ETFS[sector],
                    "Tau": tau,
                    "P_Value": p_val,
                    "Status": status,
                }
            )

            if status == "OK":
                sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
                print(f"  {sector:4s} ({SECTOR_ETFS[sector]:22s}): τ = {tau:+.4f} {sig}")
            else:
                print(f"  {sector:4s} ({SECTOR_ETFS[sector]:22s}): {status}")

        all_results.extend(crisis_results)

        # Highlight highest τ sector
        valid = [r for r in crisis_results if r["Status"] == "OK" and pd.notna(r["Tau"])]
        if valid:
            best = max(valid, key=lambda x: x["Tau"])
            print(f"\n  → Highest τ: {best['Sector']} ({best['SectorName']}) = {best['Tau']:.4f}")
        print()

    # Create summary DataFrame
    results_df = pd.DataFrame(all_results)

    # Pivot table for cleaner view
    print("=" * 70)
    print("SUMMARY: Sector τ by Crisis")
    print("=" * 70)

    pivot = results_df.pivot_table(index="Sector", columns="Event", values="Tau", aggfunc="first")
    # Reorder columns chronologically (only include events that have data)
    col_order = ["2000 Dotcom", "2008 GFC", "2020 COVID", "2022 Rate Shock"]
    pivot = pivot[[c for c in col_order if c in pivot.columns]]
    print(pivot.round(4).to_string())

    # Identify stress origins
    print("\n--- Identified Stress Origins ---")
    for event in ["2000 Dotcom", "2008 GFC", "2020 COVID", "2022 Rate Shock"]:
        if event in pivot.columns:
            col = pivot[event].dropna()
            if len(col) > 0:
                leader = col.idxmax()
                leader_tau = col.max()
                print(f"  {event}: {leader} ({SECTOR_ETFS[leader]}) τ = {leader_tau:.4f}")

    # Save results
    results_path = os.path.join(OUTPUT_DIR, "per_sector_results.csv")
    results_df.to_csv(results_path, index=False)
    print(f"\nSaved to {results_path}")

    pivot_path = os.path.join(OUTPUT_DIR, "sector_tau_matrix.csv")
    pivot.to_csv(pivot_path)
    print(f"Saved matrix to {pivot_path}")

    return results_df, pivot


if __name__ == "__main__":
    results_df, pivot = main()
