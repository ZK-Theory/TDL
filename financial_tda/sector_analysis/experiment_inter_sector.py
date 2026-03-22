"""
Experiment A: Inter-Sector Topology

Builds a 9-dimensional point cloud from sector ETF returns and computes
rolling persistent homology (H₁) to detect structural changes in the
inter-sector relationship manifold.

Hypothesis:
- Pre-crisis: Sectors begin correlating abnormally → topological signature changes
- Different crises should show different sector-specific signatures

Expected Outcomes:
- XLK (Tech) shows elevated τ before Dotcom 2000
- XLF (Financials) shows elevated τ before GFC 2008
- XLE (Energy) shows elevated τ before COVID 2020
"""

import sys
import os
import numpy as np
import pandas as pd
import gudhi as gd
from scipy.stats import kendalltau

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sector_analysis.fetch_sector_data import fetch_sector_data, compute_log_returns, OUTPUT_DIR

# Configuration - MUST MATCH G&K METHODOLOGY
WINDOW_SIZE_POINT_CLOUD = 50  # Days per point cloud
ROLLING_VAR_WINDOW = 500  # Rolling variance window (G&K standard - CRITICAL)
PRE_CRISIS_WINDOW = 250  # ~1 trading year before crisis

# Crisis events to analyze
EVENTS = [
    {"name": "2000 Dotcom", "date": "2000-03-10", "expected_sector": "XLK"},
    {"name": "2008 GFC", "date": "2008-09-15", "expected_sector": "XLF"},
    {"name": "2020 COVID", "date": "2020-03-16", "expected_sector": "XLE"},
    {"name": "2022 Rate Shock", "date": "2022-06-13", "expected_sector": "XLK"},
]


def build_point_cloud(window_data, use_lags=True):
    """
    Build point cloud from windowed returns.

    Args:
        window_data: 2D array (time x sectors) of returns
        use_lags: If True, include t-1 lag for each sector (doubles dimensions)

    Returns:
        List of points for Rips complex
    """
    n_days, n_sectors = window_data.shape
    point_cloud = []

    start_idx = 1 if use_lags else 0
    for t in range(start_idx, n_days):
        point = []
        for s in range(n_sectors):
            point.append(window_data[t, s])
            if use_lags:
                point.append(window_data[t - 1, s])  # t-1 lag
        point_cloud.append(point)

    return point_cloud


def compute_persistence_norms(point_cloud, max_dimension=2):
    """
    Compute H₁ persistence and return L¹/L² norms of lifetimes.
    """
    rips = gd.RipsComplex(points=point_cloud)
    st = rips.create_simplex_tree(max_dimension=max_dimension)
    st.compute_persistence()

    # Get H₁ intervals (loops)
    h1_intervals = st.persistence_intervals_in_dimension(1)

    if len(h1_intervals) == 0:
        return 0.0, 0.0, 0

    # Filter out infinite intervals
    finite = h1_intervals[np.isfinite(h1_intervals[:, 1])]
    if len(finite) == 0:
        return 0.0, 0.0, len(h1_intervals)

    lifetimes = finite[:, 1] - finite[:, 0]
    l1_norm = np.sum(lifetimes)
    l2_norm = np.sqrt(np.sum(lifetimes**2))

    return l1_norm, l2_norm, len(h1_intervals)


def run_rolling_persistence(returns, window_size=WINDOW_SIZE_POINT_CLOUD, use_lags=True, verbose=True):
    """
    Compute rolling persistence norms over the entire time series.

    Returns:
        DataFrame with Date, L1, L2, H1_Count columns
    """
    values = returns.values
    dates = returns.index
    results = []

    total = len(values) - window_size
    for i in range(window_size, len(values)):
        window = values[i - window_size : i]
        point_cloud = build_point_cloud(window, use_lags=use_lags)
        l1, l2, h1_count = compute_persistence_norms(point_cloud)

        results.append({"Date": dates[i], "L1": l1, "L2": l2, "H1_Count": h1_count})

        if verbose and (i - window_size) % 500 == 0:
            progress = (i - window_size) / total * 100
            sys.stdout.write(f"\r  Progress: {progress:.1f}% ({i-window_size}/{total})")
            sys.stdout.flush()

    if verbose:
        print()  # Newline after progress

    return pd.DataFrame(results).set_index("Date")


def analyze_crisis_signals(norms_df, events=EVENTS):
    """
    Compute Kendall-τ trend for the pre-crisis window of each event.

    Returns:
        List of result dicts with tau values and significance
    """
    # Add rolling variance
    norms_df = norms_df.copy()
    norms_df["L2_Var"] = norms_df["L2"].rolling(window=ROLLING_VAR_WINDOW).var()

    results = []
    for event in events:
        event_date = pd.to_datetime(event["date"])

        # Check if event is in range
        if event_date < norms_df.index[0] or event_date > norms_df.index[-1]:
            results.append(
                {
                    "Event": event["name"],
                    "Expected_Sector": event.get("expected_sector", "N/A"),
                    "Tau": np.nan,
                    "P_Value": np.nan,
                    "Status": "Out of range",
                }
            )
            continue

        # Find nearest date if exact match not found
        if event_date not in norms_df.index:
            locs = norms_df.index.get_indexer([event_date], method="nearest")
            event_date = norms_df.index[locs[0]]

        end_loc = norms_df.index.get_loc(event_date)
        start_loc = max(0, end_loc - PRE_CRISIS_WINDOW)

        if end_loc - start_loc < 100:
            results.append(
                {
                    "Event": event["name"],
                    "Expected_Sector": event.get("expected_sector", "N/A"),
                    "Tau": np.nan,
                    "P_Value": np.nan,
                    "Status": "Insufficient history",
                }
            )
            continue

        series = norms_df["L2_Var"].iloc[start_loc:end_loc].dropna()
        if len(series) < 50:
            results.append(
                {
                    "Event": event["name"],
                    "Expected_Sector": event.get("expected_sector", "N/A"),
                    "Tau": np.nan,
                    "P_Value": np.nan,
                    "Status": "Segment too short",
                }
            )
            continue

        tau, p_value = kendalltau(np.arange(len(series)), series.values)

        results.append(
            {
                "Event": event["name"],
                "Expected_Sector": event.get("expected_sector", "N/A"),
                "Tau": tau,
                "P_Value": p_value,
                "Status": "OK",
            }
        )

    return pd.DataFrame(results)


def main():
    print("=" * 60)
    print("Experiment A: Inter-Sector Topology")
    print("9-Sector Point Cloud with Delay Embedding")
    print("=" * 60)

    # Step 1: Fetch data
    print("\n[1] Fetching sector data...")
    prices = fetch_sector_data(save=True)
    returns = compute_log_returns(prices, standardize=True, save=True)
    print(f"    Returns shape: {returns.shape}")
    print(f"    Sectors: {list(returns.columns)}")

    # Step 2: Compute rolling persistence
    print("\n[2] Computing rolling H₁ persistence...")
    print(f"    Window size: {WINDOW_SIZE_POINT_CLOUD} days")
    print(f"    Dimensions: {returns.shape[1]} sectors × 2 lags = {returns.shape[1] * 2}D")

    norms = run_rolling_persistence(returns, use_lags=True, verbose=True)

    # Save results
    norms_path = os.path.join(OUTPUT_DIR, "inter_sector_norms.csv")
    norms.to_csv(norms_path)
    print(f"    Saved norms to {norms_path}")

    # Step 3: Analyze crisis signals
    print("\n[3] Analyzing pre-crisis signals...")
    results = analyze_crisis_signals(norms)

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS: Inter-Sector Topological Analysis")
    print("=" * 60)
    print(results.to_string(index=False))

    # Save results
    results_path = os.path.join(OUTPUT_DIR, "inter_sector_results.csv")
    results.to_csv(results_path, index=False)
    print(f"\nSaved results to {results_path}")

    # Interpretation
    print("\n--- Interpretation ---")
    for _, row in results.iterrows():
        if pd.notna(row["Tau"]):
            strength = "STRONG" if abs(row["Tau"]) >= 0.5 else "MODERATE" if abs(row["Tau"]) >= 0.3 else "WEAK"
            direction = "increasing" if row["Tau"] > 0 else "decreasing"
            print(f"{row['Event']}: τ = {row['Tau']:.4f} ({strength} {direction} trend)")

    return norms, results


if __name__ == "__main__":
    norms, results = main()
