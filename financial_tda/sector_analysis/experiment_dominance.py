"""
Experiment D: Sector Dominance Analysis

Alternative approach: For each sector S, measure how much S "drives"
the overall market topology by computing leave-one-out (LOO) persistence.

Method:
- Full persistence: H₁ on all 9 sectors
- LOO persistence: H₁ on 8 sectors (excluding S)
- Sector Dominance Score = |Full - LOO| / Full

High dominance = sector S is critical to current topology structure.
When S's dominance INCREASES over time, S is becoming the stress leader.

This is more aligned with the main paper's approach: measuring
topological change directly rather than correlation proxies.
"""

import sys
import os
import numpy as np
import pandas as pd
import gudhi as gd
from scipy.stats import kendalltau

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sector_analysis.fetch_sector_data import fetch_sector_data, compute_log_returns, SECTOR_ETFS, OUTPUT_DIR

# Configuration
WINDOW_SIZE = 40
PRE_CRISIS_WINDOW = 180

EVENTS = [
    {"name": "2000 Dotcom", "date": "2000-03-10", "expected": "XLK"},
    {"name": "2008 GFC", "date": "2008-09-15", "expected": "XLF"},
    {"name": "2020 COVID", "date": "2020-03-16", "expected": "XLE"},
]


def build_delay_cloud(window, sector_indices=None):
    """Build point cloud with delay embedding."""
    n_days, n_sectors = window.shape

    if sector_indices is None:
        sector_indices = list(range(n_sectors))

    cloud = []
    for t in range(1, n_days):
        point = []
        for s in sector_indices:
            point.extend([window[t, s], window[t - 1, s]])
        cloud.append(point)

    return cloud


def compute_h1_l2(cloud):
    """Compute H₁ L² norm."""
    if len(cloud) < 3:
        return 0.0

    rips = gd.RipsComplex(points=cloud)
    st = rips.create_simplex_tree(max_dimension=2)
    st.compute_persistence()
    h1 = st.persistence_intervals_in_dimension(1)

    if len(h1) == 0:
        return 0.0

    finite = h1[np.isfinite(h1[:, 1])]
    if len(finite) == 0:
        return 0.0

    lifetimes = finite[:, 1] - finite[:, 0]
    return np.sqrt(np.sum(lifetimes**2))


def compute_sector_dominance(returns, window_size=WINDOW_SIZE):
    """
    For each day and sector, compute sector dominance score.

    Returns DataFrame with columns: Date, Sector, Dominance
    """
    sectors = list(returns.columns)
    values = returns.values
    dates = returns.index
    n_sectors = len(sectors)

    results = []
    total = len(values) - window_size

    for i in range(window_size, len(values)):
        window = values[i - window_size : i]

        # Full topology (all 9 sectors)
        full_cloud = build_delay_cloud(window, list(range(n_sectors)))
        full_h1 = compute_h1_l2(full_cloud)

        # LOO topology for each sector
        for s_idx, sector in enumerate(sectors):
            loo_indices = [j for j in range(n_sectors) if j != s_idx]
            loo_cloud = build_delay_cloud(window, loo_indices)
            loo_h1 = compute_h1_l2(loo_cloud)

            # Dominance = how much removing this sector changes topology
            if full_h1 > 0:
                dominance = abs(full_h1 - loo_h1) / full_h1
            else:
                dominance = 0.0

            results.append(
                {"Date": dates[i], "Sector": sector, "Dominance": dominance, "Full_H1": full_h1, "LOO_H1": loo_h1}
            )

        if (i - window_size) % 200 == 0:
            pct = (i - window_size) / total * 100
            sys.stdout.write(f"\r  Progress: {pct:.1f}%")
            sys.stdout.flush()

    print()
    return pd.DataFrame(results)


def analyze_dominance_trends(dom_df, events=EVENTS):
    """Analyze dominance trends before each crisis."""
    results = []

    for event in events:
        event_date = pd.to_datetime(event["date"])
        print(f"\n--- {event['name']} (Expected: {event['expected']}) ---")

        for sector in SECTOR_ETFS.keys():
            sector_data = dom_df[dom_df["Sector"] == sector].set_index("Date")

            if event_date < sector_data.index[0] or event_date > sector_data.index[-1]:
                continue

            if event_date not in sector_data.index:
                locs = sector_data.index.get_indexer([event_date], method="nearest")
                event_date = sector_data.index[locs[0]]

            end_loc = sector_data.index.get_loc(event_date)
            start_loc = max(0, end_loc - PRE_CRISIS_WINDOW)

            if end_loc - start_loc < 30:
                continue

            series = sector_data["Dominance"].iloc[start_loc:end_loc].dropna()
            if len(series) < 20:
                continue

            tau, p = kendalltau(np.arange(len(series)), series.values)

            results.append(
                {"Event": event["name"], "Expected": event["expected"], "Sector": sector, "Tau": tau, "P_Value": p}
            )

            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            marker = " ← EXPECTED" if sector == event["expected"] else ""
            print(f"  {sector:4s}: τ = {tau:+.4f} {sig}{marker}")

        # Find leader
        event_results = [r for r in results if r["Event"] == event["name"]]
        if event_results:
            best = max(event_results, key=lambda x: x["Tau"])
            match = "✓ MATCH" if best["Sector"] == event["expected"] else "✗ MISMATCH"
            print(f"\n  Leader: {best['Sector']} (τ={best['Tau']:.4f}) {match}")

    return pd.DataFrame(results)


def main():
    print("=" * 70)
    print("Experiment D: Sector Dominance Analysis (LOO Approach)")
    print("Measuring sector contribution to market topology")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    prices = fetch_sector_data(save=False)
    returns = compute_log_returns(prices, standardize=True, save=False)
    print(f"    {returns.shape[0]} days, {returns.shape[1]} sectors")

    # Compute dominance (this is slow - 9 LOO computations per day)
    print("\n[2] Computing sector dominance scores...")
    print("    (Each day: 1 full + 9 LOO = 10 TDA computations)")

    dom_df = compute_sector_dominance(returns)

    # Analyze
    print("\n[3] Analyzing pre-crisis dominance trends...")
    results = analyze_dominance_trends(dom_df)

    # Summary pivot
    print("\n" + "=" * 70)
    print("SUMMARY: Sector Dominance τ by Crisis")
    print("=" * 70)

    pivot = results.pivot_table(index="Sector", columns="Event", values="Tau", aggfunc="first")
    pivot = pivot[["2000 Dotcom", "2008 GFC", "2020 COVID"]]
    print(pivot.round(4).to_string())

    # Save
    dom_path = os.path.join(OUTPUT_DIR, "sector_dominance.csv")
    dom_df.to_csv(dom_path, index=False)

    results_path = os.path.join(OUTPUT_DIR, "dominance_results.csv")
    results.to_csv(results_path, index=False)
    print(f"\nSaved dominance data to {dom_path}")
    print(f"Saved results to {results_path}")

    return dom_df, results


if __name__ == "__main__":
    dom_df, results = main()
