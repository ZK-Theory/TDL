"""
Exploratory Experiment: Crypto Re-evaluation
Investigating TDA signals on BTC-USD and ETH-USD with "Crypto-Native" parameters.

Hypothesis: Previous failure (F1=0.0) was due to standard parameters (W=500, P=250) being too slow
for 24/7 crypto markets. We test faster reaction times:
- Rolling Window: 300 days
- Pre-Crisis Window: 150 days

Events:
1. 2017 Crash (Dec 2017)
2. 2021 Crash (May 2021)
3. 2022 FTX Collapse (Nov 2022)
"""

import os
import numpy as np
import pandas as pd
import yfinance as yf
import gudhi as gd
from scipy.stats import kendalltau

OUTPUT_DIR = "outputs/exploratory_crypto"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TICKERS = ["BTC-USD", "ETH-USD"]
START_DATE = "2016-01-01"
END_DATE = "2023-12-31"

# Crypto-Native Parameters (Faster)
WINDOW_SIZE_POINT_CLOUD = 50
DIMENSION = 2
ROLLING_WINDOW = 300
PRE_CRISIS_WINDOW = 150

EVENTS = [
    {"name": "2018 Crash", "date": "2017-12-17"},
    {"name": "2021 May Crash", "date": "2021-05-19"},
    {"name": "FTX Collapse", "date": "2022-11-08"},
]


def fetch_data():
    print("Fetching Crypto Data...")
    df = yf.download(TICKERS, start=START_DATE, end=END_DATE)
    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df["Adj Close"]

    prices = prices.dropna()
    log_returns = np.log(prices / prices.shift(1)).dropna()
    standardized = (log_returns - log_returns.mean()) / log_returns.std()
    return standardized


def compute_tda(data):
    print("Computing TDA on Crypto...")
    results = []
    values = data.values
    dates = data.index

    # Combined embedding of BTC+ETH? Or separate?
    # Paper method uses "market" state, so we combine them into one point cloud if we treat them as a "system".
    # Let's try "Crypto System" (BTC + ETH) first.

    for i in range(WINDOW_SIZE_POINT_CLOUD, len(values)):
        window = values[i - WINDOW_SIZE_POINT_CLOUD : i]

        # Point Cloud Construction (Time Delay Embedding on Multiplex)
        # Vector: [BTC_t, ETH_t, BTC_t-1, ETH_t-1]
        point_cloud = []
        for j in range(1, len(window)):
            point = []
            for col in range(data.shape[1]):
                point.append(window[j, col])
                point.append(window[j - 1, col])
            point_cloud.append(point)

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

    return pd.DataFrame(results).set_index("Date")


def analyze(norms):
    norms["L2_Var"] = norms["L2"].rolling(window=ROLLING_WINDOW).var()

    for event in EVENTS:
        event_date = pd.to_datetime(event["date"])
        if event_date not in norms.index:
            # Find nearest
            locs = norms.index.get_indexer([event_date], method="nearest")
            event_date = norms.index[locs[0]]

        end_loc = norms.index.get_loc(event_date)
        start_loc = end_loc - PRE_CRISIS_WINDOW

        if start_loc < 0:
            print(f"Skipping {event['name']} (insufficient data)")
            continue

        segment = norms["L2_Var"].iloc[start_loc:end_loc].dropna()
        if len(segment) < 20:
            print(f"Skipping {event['name']} (segment too short)")
            continue

        tau, p = kendalltau(np.arange(len(segment)), segment.values)
        print(f"Crypto Event {event['name']}: Tau={tau:.4f}, p={p:.4f}")


def main():
    data = fetch_data()
    norms = compute_tda(data)
    analyze(norms)
    norms.to_csv(os.path.join(OUTPUT_DIR, "crypto_results.csv"))


if __name__ == "__main__":
    main()
