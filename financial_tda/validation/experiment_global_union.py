"""
Exploratory Experiment: Global Union (9 Indices)
Combines all utilized indices into a single high-dimensional point cloud to test
if "more data = better signal" or if noise increases.

Indices (9):
US: ^GSPC, ^DJI, ^IXIC, ^RUT
Int: ^FTSE, ^GDAXI, ^FCHI, ^N225, ^HSI
"""

import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf
import gudhi as gd
from scipy.stats import kendalltau

# Output setup
OUTPUT_DIR = "outputs/exploratory"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuration
INDICES = ["^GSPC", "^DJI", "^IXIC", "^RUT", "^FTSE", "^GDAXI", "^FCHI", "^N225", "^HSI"]
START_DATE = "2006-01-01"
END_DATE = "2022-12-31"  # Covers 2008 and 2020
WINDOW_SIZE_POINT_CLOUD = 50
DIMENSION_PER_INDEX = 2  # 2 lags per index -> 18 dimensions total
ROLLING_WINDOW = 500
PRE_CRISIS_WINDOW = 250

EVENTS = [{"name": "2008 GFC", "date": "2008-09-15"}, {"name": "2020 COVID", "date": "2020-03-16"}]


def fetch_and_preprocess():
    print("Fetching data for Global Union (9 indices)...")
    # Fetch all at once
    df = yf.download(INDICES, start=START_DATE, end=END_DATE)

    # Handle MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]

    # Forward fill to handle timezone differences (e.g. US open while Japan closed)
    # Then drop rows where ANY remaining NaNs exist (strict intersection)
    prices = prices.ffill().dropna()

    print(f"Data shape after alignment: {prices.shape}")

    # Log returns
    log_returns = np.log(prices / prices.shift(1)).dropna()

    # Standardize
    standardized = (log_returns - log_returns.mean()) / log_returns.std()

    return standardized


def compute_lp_norms(data):
    print("Computing persistence landscapes (18-dimensional embedding)...")
    results = []
    values = data.values
    dates = data.index

    for i in range(WINDOW_SIZE_POINT_CLOUD, len(values)):
        # Construct Point Cloud: [t, t-1] for all 9 indices
        window = values[i - WINDOW_SIZE_POINT_CLOUD : i]
        point_cloud = []
        for j in range(1, WINDOW_SIZE_POINT_CLOUD):
            point = []
            for col in range(data.shape[1]):  # 9 indices
                point.append(window[j, col])
                point.append(window[j - 1, col])
            point_cloud.append(point)

        # Persistent Homology
        # Using sparse rips for high dimension speedup if available, but GUDHI is fast enough for D=18, N=50
        rips = gd.RipsComplex(points=point_cloud)
        st = rips.create_simplex_tree(max_dimension=2)
        st.compute_persistence()
        persistence = st.persistence_intervals_in_dimension(1)

        if len(persistence) == 0:
            results.append({"Date": dates[i], "L1": 0.0, "L2": 0.0})
            continue

        lifetimes = persistence[:, 1] - persistence[:, 0]
        l1 = np.sum(lifetimes)
        l2 = np.sqrt(np.sum(lifetimes**2))

        results.append({"Date": dates[i], "L1": l1, "L2": l2})

        if i % 500 == 0:
            sys.stdout.write(f"\rProcessed {i}/{len(values)}")

    return pd.DataFrame(results).set_index("Date")


def analyze_event(norms, event):
    print(f"\nAnalyzing {event['name']} ({event['date']})...")
    event_date = pd.to_datetime(event["date"])

    # Calculate Variance Rolling
    norms["L2_Var"] = norms["L2"].rolling(window=ROLLING_WINDOW).var()
    norms["L1_Var"] = norms["L1"].rolling(window=ROLLING_WINDOW).var()

    # Extract Pre-Crisis Window
    # Find index of event date
    locs = norms.index.get_indexer([event_date], method="nearest")
    end_loc = locs[0]
    start_loc = end_loc - PRE_CRISIS_WINDOW

    if start_loc < 0:
        print("Insufficient history.")
        return

    # Compute Tau
    l2_series = norms["L2_Var"].iloc[start_loc:end_loc].dropna()
    l1_series = norms["L1_Var"].iloc[start_loc:end_loc].dropna()

    tau2, p2 = kendalltau(np.arange(len(l2_series)), l2_series.values)
    tau1, p1 = kendalltau(np.arange(len(l1_series)), l1_series.values)

    print(f"Global Union Results for {event['name']}:")
    print(f"  L2 Variance Tau: {tau2:.4f} (p={p2:.2e})")
    print(f"  L1 Variance Tau: {tau1:.4f} (p={p1:.2e})")


def main():
    data = fetch_and_preprocess()
    norms = compute_lp_norms(data)

    for event in EVENTS:
        analyze_event(norms, event)

    norms.to_csv(os.path.join(OUTPUT_DIR, "global_union_norms.csv"))


if __name__ == "__main__":
    main()
