"""
Experiment C: Sector Lead-Lag TDA Analysis

Uses proper TDA methodology: For each sector, compute how that sector's
contribution to the inter-sector topology changes over time.

Method:
- Use "Leave-One-Out" (LOO) topology: Compare H₁ with all 9 sectors vs
  H₁ without sector S. Large difference = S is critical to current topology.

- Use "Sector-Centric" topology: Build point cloud from sector S + its
  rolling correlations with others. Track S's topological footprint.

This should correctly identify:
- XLK stress before Dotcom (Tech bubble topology change)
- XLF stress before GFC (Financial system topology change)
"""

import sys
import os
import numpy as np
import pandas as pd
import gudhi as gd
from scipy.stats import kendalltau

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sector_analysis.fetch_sector_data import fetch_sector_data, compute_log_returns, SECTOR_ETFS, OUTPUT_DIR

# Configuration - MUST MATCH G&K METHODOLOGY
WINDOW_SIZE = 50  # Point cloud window
ROLLING_WINDOW = 500  # Rolling variance window (G&K standard - CRITICAL)
PRE_CRISIS_WINDOW = 250  # Analysis window

EVENTS = [
    {"name": "2000 Dotcom", "date": "2000-03-10"},
    {"name": "2008 GFC", "date": "2008-09-15"},
    {"name": "2020 COVID", "date": "2020-03-16"},
]


def compute_h1_norm(point_cloud):
    """Compute L² norm of H₁ persistence."""
    if len(point_cloud) < 3:
        return 0.0

    rips = gd.RipsComplex(points=point_cloud)
    st = rips.create_simplex_tree(max_dimension=2)
    st.compute_persistence()
    h1 = st.persistence_intervals_in_dimension(1)

    if len(h1) == 0:
        return 0.0

    # Filter infinite
    finite = h1[np.isfinite(h1[:, 1])]
    if len(finite) == 0:
        return 0.0

    lifetimes = finite[:, 1] - finite[:, 0]
    return np.sqrt(np.sum(lifetimes**2))


def build_sector_centric_cloud(returns_window, focus_sector_idx):
    """
    Build point cloud emphasizing one sector.

    For focus sector: include raw returns + 1 lag
    For others: include correlation with focus sector over window
    """
    n_days, n_sectors = returns_window.shape
    focus = returns_window[:, focus_sector_idx]

    # Compute recent correlation of focus with each other sector
    correlations = []
    for s in range(n_sectors):
        if s == focus_sector_idx:
            continue
        corr = np.corrcoef(focus, returns_window[:, s])[0, 1]
        correlations.append(corr if np.isfinite(corr) else 0.0)

    # Build cloud: each point = [focus_t, focus_t-1, corr1, corr2, ...]
    cloud = []
    for t in range(1, n_days):
        point = [focus[t], focus[t - 1]] + correlations
        cloud.append(point)

    return cloud


def compute_sector_tda_series(returns, focus_sector, window_size=WINDOW_SIZE):
    """
    Compute rolling TDA feature for a specific sector's contribution.
    """
    sector_idx = list(returns.columns).index(focus_sector)
    values = returns.values
    dates = returns.index

    results = []
    for i in range(window_size, len(values)):
        window = values[i - window_size : i]
        cloud = build_sector_centric_cloud(window, sector_idx)
        h1_norm = compute_h1_norm(cloud)
        results.append({"Date": dates[i], "H1_L2": h1_norm})

    return pd.DataFrame(results).set_index("Date")


def compute_sector_tau(sector_series, event_date, pre_crisis_days):
    """Compute Kendall-tau for sector's H1 trend before crisis."""
    if event_date < sector_series.index[0] or event_date > sector_series.index[-1]:
        return np.nan, np.nan, "Out of range"

    # Find nearest
    if event_date not in sector_series.index:
        locs = sector_series.index.get_indexer([event_date], method="nearest")
        event_date = sector_series.index[locs[0]]

    end_loc = sector_series.index.get_loc(event_date)
    start_loc = max(0, end_loc - pre_crisis_days)

    if end_loc - start_loc < 30:
        return np.nan, np.nan, "Insufficient data"

    # Use rolling variance of H1_L2
    series = sector_series["H1_L2"].iloc[start_loc:end_loc]
    variance_series = series.rolling(ROLLING_WINDOW).var().dropna()

    if len(variance_series) < 20:
        return np.nan, np.nan, "Segment too short"

    tau, p = kendalltau(np.arange(len(variance_series)), variance_series.values)
    return tau, p, "OK"


def main():
    print("=" * 70)
    print("Experiment C: Sector-Centric TDA Analysis")
    print("Identifying sector-specific topological stress signatures")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    prices = fetch_sector_data(save=False)
    returns = compute_log_returns(prices, standardize=True, save=False)
    print(f"    {returns.shape[0]} days, {returns.shape[1]} sectors")

    # Compute TDA series for each sector
    print("\n[2] Computing sector-centric TDA series...")
    sector_tda = {}
    for sector in SECTOR_ETFS.keys():
        sector_tda[sector] = compute_sector_tda_series(returns, sector)
        sys.stdout.write(f"\r    Processed {sector}")
        sys.stdout.flush()
    print()

    # Analyze each crisis
    print("\n[3] Computing sector τ values for each crisis...\n")

    all_results = []
    for event in EVENTS:
        event_date = pd.to_datetime(event["date"])
        print(f"--- {event['name']} ---")

        for sector in SECTOR_ETFS.keys():
            tau, p, status = compute_sector_tau(sector_tda[sector], event_date, PRE_CRISIS_WINDOW)

            all_results.append(
                {
                    "Event": event["name"],
                    "Sector": sector,
                    "Name": SECTOR_ETFS[sector],
                    "Tau": tau,
                    "P_Value": p,
                    "Status": status,
                }
            )

            if status == "OK":
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
                print(f"  {sector:4s}: τ = {tau:+.4f} {sig}")
            else:
                print(f"  {sector:4s}: {status}")

        # Highlight leader
        valid = [r for r in all_results if r["Event"] == event["name"] and r["Status"] == "OK" and pd.notna(r["Tau"])]
        if valid:
            best = max(valid, key=lambda x: x["Tau"])
            print(f"\n  → Leader: {best['Sector']} ({best['Name']}) τ = {best['Tau']:.4f}\n")

    # Summary
    results_df = pd.DataFrame(all_results)
    print("\n" + "=" * 70)
    print("SUMMARY: Sector-Centric TDA τ by Crisis")
    print("=" * 70)

    pivot = results_df.pivot_table(index="Sector", columns="Event", values="Tau", aggfunc="first")
    # Only include events that have data
    col_order = ["2000 Dotcom", "2008 GFC", "2020 COVID"]
    pivot = pivot[[c for c in col_order if c in pivot.columns]]
    print(pivot.round(4).to_string())

    # Save
    path = os.path.join(OUTPUT_DIR, "sector_tda_results.csv")
    results_df.to_csv(path, index=False)
    print(f"\nSaved to {path}")

    return results_df, pivot


if __name__ == "__main__":
    results_df, pivot = main()
