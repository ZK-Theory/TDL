"""
Exploratory Experiment: Market Basket Analysis
Comparing TDA signal strength across different index compositions ("Baskets")
and crises (Dotcom, GFC, COVID).

Baskets:
1. Global (9): US(4) + EU(3) + Asia(2)
2. Transatlantic (7): US(4) + EU(3) (Removing Nikkei/Hang Seng)

Hypothesis: Removing Asian markets (timezone/correlation mismatch) will restore
signal strength for the Transatlantic-centric crises (2008, 2020), potentially
improving on the 9-market failure.
"""

import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf
import gudhi as gd
from scipy.stats import kendalltau

OUTPUT_DIR = "outputs/exploratory_baskets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Baskets
INDICES_ALL = {"US": ["^GSPC", "^DJI", "^IXIC", "^RUT"], "EU": ["^FTSE", "^GDAXI", "^FCHI"], "ASIA": ["^N225", "^HSI"]}

BASKETS = {
    "Global_9": INDICES_ALL["US"] + INDICES_ALL["EU"] + INDICES_ALL["ASIA"],
    "Transatlantic_7": INDICES_ALL["US"] + INDICES_ALL["EU"],
}

# Configuration
# Start early enough for Dotcom (2000)
START_DATE = "1995-01-01"
END_DATE = "2022-12-31"
WINDOW_SIZE_POINT_CLOUD = 50
ROLLING_WINDOW = 500
PRE_CRISIS_WINDOW = 250

EVENTS = [
    {"name": "2000 Dotcom", "date": "2000-03-10"},
    {"name": "2008 GFC", "date": "2008-09-15"},
    {"name": "2020 COVID", "date": "2020-03-16"},
]


def fetch_data(basket_name, tickers):
    print(f"\nFetching data for {basket_name}...")
    df = yf.download(tickers, start=START_DATE, end=END_DATE, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]

    prices = prices.ffill().dropna()
    print(f"  Shape: {prices.shape}")

    log_returns = np.log(prices / prices.shift(1)).dropna()
    standardized = (log_returns - log_returns.mean()) / log_returns.std()
    return standardized


def compute_persistence(data):
    print("  Computing persistence...")
    results = []
    values = data.values
    dates = data.index

    # Pre-computation to save time if we run multiple
    # Dimension is len(columns) * 2

    for i in range(WINDOW_SIZE_POINT_CLOUD, len(values)):
        window = values[i - WINDOW_SIZE_POINT_CLOUD : i]

        point_cloud = []
        for j in range(1, WINDOW_SIZE_POINT_CLOUD):
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
            l1, l2 = 0.0, 0.0
        else:
            lifetimes = persistence[:, 1] - persistence[:, 0]
            l1 = np.sum(lifetimes)
            l2 = np.sqrt(np.sum(lifetimes**2))

        results.append({"Date": dates[i], "L1": l1, "L2": l2})

        if i % 1000 == 0:
            sys.stdout.write(f"\r  Processed {i}/{len(values)}")

    return pd.DataFrame(results).set_index("Date")


def analyze_events(norms, basket_name):
    norms["L2_Var"] = norms["L2"].rolling(window=ROLLING_WINDOW).var()

    print(f"\n  Results for {basket_name}:")
    for event in EVENTS:
        event_date = pd.to_datetime(event["date"])

        # Check if event is in range
        if event_date < norms.index[0] or event_date > norms.index[-1]:
            print(f"    {event['name']}: Out of data range.")
            continue

        if event_date not in norms.index:
            locs = norms.index.get_indexer([event_date], method="nearest")
            event_date = norms.index[locs[0]]

        end_loc = norms.index.get_loc(event_date)
        start_loc = end_loc - PRE_CRISIS_WINDOW

        if start_loc < 0:
            print(f"    {event['name']}: Insufficient history.")
            continue

        series = norms["L2_Var"].iloc[start_loc:end_loc].dropna()
        if len(series) < 100:
            print(f"    {event['name']}: Segment too short.")
            continue

        tau, p = kendalltau(np.arange(len(series)), series.values)
        print(f"    {event['name']}: Tau = {tau:.4f} (p={p:.2e})")


def main():
    for basket_name, tickers in BASKETS.items():
        data = fetch_data(basket_name, tickers)
        if data.empty:
            print("  Dataset empty, skipping.")
            continue

        norms = compute_persistence(data)
        analyze_events(norms, basket_name)
        norms.to_csv(os.path.join(OUTPUT_DIR, f"{basket_name}_norms.csv"))


if __name__ == "__main__":
    main()
