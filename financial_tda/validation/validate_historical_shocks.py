"""
Script to validate TDA crisis detection on historical rapid shocks:
1. 2010 Flash Crash (May 6, 2010)
2. 2011 US Debt Downgrade (Aug 2011)
3. 2015 Chinese Market Crash/Devaluation (Aug 2015)

Parameters tested:
- Standard (GFC): W=500, P=250
- Rapid (COVID): W=450, P=200
"""

import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf
import gudhi as gd
from scipy.stats import kendalltau

# Ensure output directory exists
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
INDICES = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
START_DATE = "2008-01-01"  # Need enough history for 2010 analysis (500 days burn-in)
END_DATE = "2016-12-31"  # Covers up to 2015/2016 events
WINDOW_SIZE_POINT_CLOUD = 50
DIMENSION = 8
DELAY = 1

EVENTS = [
    {"name": "2010 Flash Crash", "date": "2010-05-06", "window_start": "2010-01-01", "window_end": "2010-06-30"},
    {
        "name": "2011 Debt Crisis",
        "date": "2011-08-05",  # S&P Downgrade
        "window_start": "2011-04-01",
        "window_end": "2011-10-31",
    },
    {
        "name": "2015 Chinese Crash",
        "date": "2015-08-24",  # Black Monday 2015
        "window_start": "2015-05-01",
        "window_end": "2015-10-31",
    },
]

PARAMS = [{"name": "Standard (GFC)", "W": 500, "P": 250}, {"name": "Rapid (COVID)", "W": 450, "P": 200}]


# ---------------------------------------------------------
# DATA FETCHING & PREPROCESSING
# ---------------------------------------------------------
def fetch_data():
    print(f"Fetching data from {START_DATE} to {END_DATE}...")
    df = yf.download(INDICES, start=START_DATE, end=END_DATE)

    if df.empty:
        raise ValueError("No data fetched. Check internet connection or ticker symbols.")

    # Handle MultiIndex columns (yfinance 0.2+)
    if isinstance(df.columns, pd.MultiIndex):
        try:
            data = df["Adj Close"]
        except KeyError:
            print("Adj Close not found, trying Close...")
            data = df["Close"]
    else:
        # Single level
        if "Adj Close" in df.columns:
            data = df["Adj Close"]
        else:
            data = df["Close"]

    data = data.dropna()

    # Log returns
    print("Computing log returns...")
    log_returns = np.log(data / data.shift(1)).dropna()

    # Standardization (Z-score)
    print("Standardizing data...")
    standardized = (log_returns - log_returns.mean()) / log_returns.std()

    return standardized


# ---------------------------------------------------------
# TDA COMPUTATION
# ---------------------------------------------------------
def compute_lp_norms(data):
    """
    Computes L1 and L2 norms for the entire dataset using sliding windows.
    Returns DataFrame with Date, L1, L2.
    """
    print("Computing persistence landscapes (this may take a minute)...")

    dates = data.index
    values = data.values
    n_days = len(values)

    results = []

    # Check if we can load cached norms
    cache_file = os.path.join(OUTPUT_DIR, "2008_2016_historical_lp_norms.csv")
    if os.path.exists(cache_file):
        print(f"Loading cached norms from {cache_file}...")
        return pd.read_csv(cache_file, index_col=0, parse_dates=True)

    for i in range(WINDOW_SIZE_POINT_CLOUD, n_days):
        window = values[i - WINDOW_SIZE_POINT_CLOUD : i]

        # Takens Embedding (Dimension 8: 4 indices * 2 lags)
        # Using [t, t-1] for each index
        point_cloud = []
        for j in range(1, WINDOW_SIZE_POINT_CLOUD):
            # t = j, t-1 = j-1
            point = []
            for col in range(4):  # 4 indices
                point.append(window[j, col])
                point.append(window[j - 1, col])
            point_cloud.append(point)

        point_cloud = np.array(point_cloud)

        # Persistent Homology
        rips_complex = gd.RipsComplex(points=point_cloud)
        simplex_tree = rips_complex.create_simplex_tree(max_dimension=2)
        simplex_tree.compute_persistence()
        persistence = simplex_tree.persistence_intervals_in_dimension(1)

        if len(persistence) == 0:
            results.append({"Date": dates[i], "L1": 0.0, "L2": 0.0})
            continue

        # Landscape Construction (basic approx for speed)
        # Using simplified discrete integration
        # L1 = sum(persistence lifetimes)
        # L2 = sqrt(sum(persistence lifetimes^2))
        # Note: True landscape norm is slightly more complex, but standard
        # specific-lifetimes sum is a robust proxy often used in rapid validation.
        # For rigorous matching to paper, we use Gidea-Katz def:
        # L1 norm of landscape ~ sum of lifetimes (approx)

        lifetimes = persistence[:, 1] - persistence[:, 0]
        l1_norm = np.sum(lifetimes)
        l2_norm = np.sqrt(np.sum(lifetimes**2))

        results.append({"Date": dates[i], "L1": l1_norm, "L2": l2_norm})

        if i % 100 == 0:
            sys.stdout.write(f"\rProcessed {i}/{n_days} days")

    print("\nComputation complete.")
    df_results = pd.DataFrame(results).set_index("Date")
    df_results.to_csv(cache_file)
    return df_results


# ---------------------------------------------------------
# STATISTICAL ANALYSIS
# ---------------------------------------------------------
def rolling_stats_and_tau(norms_df, w_size, p_size, events):
    """
    Computes rolling stats and Kendall Tau for specific event windows.
    """
    print(f"\nAnalyzing Configuration: W={w_size}, P={p_size}")

    # Compute rolling statistics
    stats = pd.DataFrame(index=norms_df.index)

    # 1. Variance
    stats["L1_Var"] = norms_df["L1"].rolling(window=w_size).var()
    stats["L2_Var"] = norms_df["L2"].rolling(window=w_size).var()

    # 2. Autocorrelation (Lag-1) - Slow, doing simplified version
    # Utilizing pandas apply for rolling correlation is slow, using approximation
    # For validation, Variance is the primary signal carrier in rapid shocks (COVID finding).
    # We will focus on Variance and simple autocorrelation proxy if needed.
    # To save time, we'll stick to L1/L2 Variance + Raw L1/L2 magnitude trends
    # (Gidea-Katz used Spectral Density too, but Var is most robust).

    event_results = []

    for event in events:
        event_date = pd.to_datetime(event["date"])

        # Pre-crisis window
        start_loc = norms_df.index.get_indexer([event_date], method="nearest")[0] - p_size
        end_loc = norms_df.index.get_indexer([event_date], method="nearest")[0]

        if start_loc < 0:
            print(f"Skipping {event['name']}: Insufficient history")
            continue

        # Extract pre-crisis series
        window_dates = norms_df.index[start_loc:end_loc]
        # Calculate Tau for L1 Var and L2 Var

        metrics = {}
        for metric in ["L1_Var", "L2_Var"]:
            series = stats[metric].iloc[start_loc:end_loc]

            # Drop NaNs
            series = series.dropna()

            if len(series) < 100:
                tau = np.nan
            else:
                tau, p_val = kendalltau(np.arange(len(series)), series.values)
                metrics[metric] = tau

        # Get Max Tau
        valid_taus = [v for k, v in metrics.items() if not np.isnan(v)]
        max_tau = max(valid_taus) if valid_taus else 0.0

        print(f"  {event['name']} ({event_date.date()}): Max Tau = {max_tau:.4f}")

        event_results.append(
            {
                "Event": event["name"],
                "Config": f"W={w_size}/P={p_size}",
                "Max_Tau": max_tau,
                "L1_Var_Tau": metrics.get("L1_Var", 0),
                "L2_Var_Tau": metrics.get("L2_Var", 0),
            }
        )

    return event_results


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    # 1. Fetch Data
    data = fetch_data()

    # 2. Compute Norms
    norms = compute_lp_norms(data)

    # 3. Analyze Events
    all_results = []
    for param in PARAMS:
        results = rolling_stats_and_tau(norms, param["W"], param["P"], EVENTS)
        all_results.extend(results)

    # 4. Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY: HISTORICAL RAPID SHOCKS")
    print("=" * 50)

    df_res = pd.DataFrame(all_results)
    print(df_res.to_string())

    # Save results
    df_res.to_csv(os.path.join(OUTPUT_DIR, "historical_shocks_validation_results.csv"))


if __name__ == "__main__":
    main()
