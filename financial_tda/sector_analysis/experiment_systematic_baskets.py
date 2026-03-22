"""
Experiment F: Systematic Hybrid Basket Testing

Systematically test different base basket configurations combined with
sector ETFs to find the best-performing combinations for crisis detection.

Key insight from previous experiments:
- XLB (Materials) and XLE (Energy) appeared as consistent leaders
- These may be "market fundamentals" indicators worth testing across baskets

Base Baskets to Test:
1. US-Only: GSPC, IXIC, DJI, RUT (4 US)
2. US-Tech-Heavy: GSPC, IXIC (2 US, tech-weighted)
3. Trans-Atlantic: GSPC, IXIC, FTSE, DAX (2 US + 2 EU)
4. Broad US: GSPC, DJI (2 US, non-tech)

Sector Additions to Test:
- XLB (Materials) - appeared as leader in GFC
- XLE (Energy) - appeared as leader in multiple crises
- Both XLB + XLE together
"""

import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf
import gudhi as gd
from scipy.stats import kendalltau

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sector_analysis.fetch_sector_data import OUTPUT_DIR

# Configuration - MUST MATCH G&K METHODOLOGY
WINDOW_SIZE = 50  # Point cloud window (G&K standard)
ROLLING_WINDOW = 500  # Rolling statistics window (G&K standard - CRITICAL)
PRE_CRISIS_WINDOW = 250  # Pre-crisis analysis window (G&K standard)
START_DATE = "1999-01-01"
END_DATE = "2024-12-31"

# Base baskets to test
BASE_BASKETS = {
    "US_4": ["^GSPC", "^IXIC", "^DJI", "^RUT"],
    "US_Tech": ["^GSPC", "^IXIC"],
    "US_Broad": ["^GSPC", "^DJI"],
    "Trans_Atlantic": ["^GSPC", "^IXIC", "^FTSE", "^GDAXI"],
    "US_EU_6": ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^GDAXI", "^FCHI"],
}

# Sector additions to test (based on previous findings)
SECTOR_ADDITIONS = {
    "None": [],
    "XLB": ["XLB"],
    "XLE": ["XLE"],
    "XLB_XLE": ["XLB", "XLE"],
    "XLF": ["XLF"],  # For comparison
    "XLK": ["XLK"],  # For comparison
}

# Crisis events
EVENTS = [
    {"name": "2008 GFC", "date": "2008-09-15"},
    {"name": "2020 COVID", "date": "2020-03-16"},
]


def fetch_data(tickers, start=START_DATE, end=END_DATE):
    """Fetch and preprocess data."""
    df = yf.download(tickers, start=start, end=end, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]

    # Ensure correct column order
    prices = prices[tickers].ffill().dropna()
    log_returns = np.log(prices / prices.shift(1)).dropna()
    standardized = (log_returns - log_returns.mean()) / log_returns.std()
    return standardized


def compute_h1_l2_variance_series(data, window=WINDOW_SIZE, var_window=ROLLING_WINDOW):
    """Compute rolling H₁ L² variance."""
    values = data.values
    dates = data.index
    l2_values = []

    for i in range(window, len(values)):
        window_data = values[i - window : i]

        # Build delay-embedded point cloud
        cloud = []
        for t in range(1, window):
            point = []
            for col in range(data.shape[1]):
                point.extend([window_data[t, col], window_data[t - 1, col]])
            cloud.append(point)

        # Compute H₁ persistence
        rips = gd.RipsComplex(points=cloud)
        st = rips.create_simplex_tree(max_dimension=2)
        st.compute_persistence()
        h1 = st.persistence_intervals_in_dimension(1)

        if len(h1) == 0:
            l2 = 0.0
        else:
            finite = h1[np.isfinite(h1[:, 1])]
            l2 = np.sqrt(np.sum((finite[:, 1] - finite[:, 0]) ** 2)) if len(finite) > 0 else 0.0

        l2_values.append({"Date": dates[i], "L2": l2})

    df = pd.DataFrame(l2_values).set_index("Date")
    df["L2_Var"] = df["L2"].rolling(var_window).var()
    return df


def compute_tau(norms_df, event_date, pre_crisis_days=PRE_CRISIS_WINDOW):
    """Compute Kendall-τ for pre-crisis window."""
    if event_date < norms_df.index[0] or event_date > norms_df.index[-1]:
        return np.nan, np.nan

    if event_date not in norms_df.index:
        locs = norms_df.index.get_indexer([event_date], method="nearest")
        event_date = norms_df.index[locs[0]]

    end_loc = norms_df.index.get_loc(event_date)
    start_loc = max(0, end_loc - pre_crisis_days)

    series = norms_df["L2_Var"].iloc[start_loc:end_loc].dropna()
    if len(series) < 50:
        return np.nan, np.nan

    tau, p = kendalltau(np.arange(len(series)), series.values)
    return tau, p


def main():
    print("=" * 80)
    print("Experiment F: Systematic Hybrid Basket Testing")
    print("Finding optimal base basket + sector combinations")
    print("=" * 80)

    all_results = []

    # Test each base basket × sector addition combination
    total_tests = len(BASE_BASKETS) * len(SECTOR_ADDITIONS)
    test_num = 0

    for base_name, base_tickers in BASE_BASKETS.items():
        for sector_name, sector_tickers in SECTOR_ADDITIONS.items():
            test_num += 1

            # Create combined basket
            combined = base_tickers + sector_tickers
            basket_label = f"{base_name}" if sector_name == "None" else f"{base_name}+{sector_name}"

            print(f"\n[{test_num}/{total_tests}] Testing: {basket_label}")
            print(f"    Tickers: {combined}")

            try:
                data = fetch_data(combined)
                if len(data) < 500:
                    print(f"    ⚠ Insufficient data ({len(data)} days)")
                    continue

                print(f"    Data: {len(data)} days, {data.shape[1]}D → {data.shape[1]*2}D")

                norms = compute_h1_l2_variance_series(data)

                # Test each crisis
                for event in EVENTS:
                    tau, p = compute_tau(norms, pd.to_datetime(event["date"]))

                    all_results.append(
                        {
                            "Base": base_name,
                            "Sectors": sector_name,
                            "Basket": basket_label,
                            "Dimension": data.shape[1] * 2,
                            "Event": event["name"],
                            "Tau": tau,
                            "P_Value": p,
                        }
                    )

                    if pd.notna(tau):
                        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
                        print(f"    {event['name']:15s}: τ = {tau:+.4f} {sig}")

            except Exception as e:
                print(f"    ⚠ Error: {e}")
                continue

    # Create results DataFrame
    results_df = pd.DataFrame(all_results)

    # Summary tables
    print("\n" + "=" * 80)
    print("SUMMARY: τ Values by Base Basket and Sector Addition")
    print("=" * 80)

    for event in EVENTS:
        print(f"\n### {event['name']} ###")
        event_df = results_df[results_df["Event"] == event["name"]]

        if len(event_df) == 0:
            print("  No results")
            continue

        # Pivot table: Base × Sectors
        pivot = event_df.pivot_table(index="Base", columns="Sectors", values="Tau", aggfunc="first")

        # Reorder columns
        col_order = ["None", "XLB", "XLE", "XLB_XLE", "XLF", "XLK"]
        pivot = pivot[[c for c in col_order if c in pivot.columns]]

        print(pivot.round(4).to_string())

    # Find best combinations
    print("\n" + "=" * 80)
    print("TOP 5 BASKETS BY AVERAGE τ ACROSS CRISES")
    print("=" * 80)

    avg_tau = results_df.groupby("Basket")["Tau"].mean().sort_values(ascending=False)
    print(avg_tau.head(10).to_string())

    # Find consistently high performers (τ > 0.5 for all crises)
    print("\n" + "=" * 80)
    print("CONSISTENT PERFORMERS (τ > 0.4 for all crises)")
    print("=" * 80)

    consistent = results_df.groupby("Basket").agg({"Tau": ["min", "mean", "max"]})
    consistent.columns = ["Min_Tau", "Mean_Tau", "Max_Tau"]
    consistent = consistent[consistent["Min_Tau"] > 0.4].sort_values("Mean_Tau", ascending=False)
    print(consistent.to_string() if len(consistent) > 0 else "  None found")

    # Impact of adding XLB/XLE to each base
    print("\n" + "=" * 80)
    print("IMPACT OF ADDING XLB/XLE (Δ from base)")
    print("=" * 80)

    for event in EVENTS:
        print(f"\n### {event['name']} ###")
        event_df = results_df[results_df["Event"] == event["name"]]

        for base_name in BASE_BASKETS.keys():
            base_tau = event_df[(event_df["Base"] == base_name) & (event_df["Sectors"] == "None")]["Tau"].values
            xlb_xle_tau = event_df[(event_df["Base"] == base_name) & (event_df["Sectors"] == "XLB_XLE")]["Tau"].values

            if len(base_tau) > 0 and len(xlb_xle_tau) > 0:
                base_tau = base_tau[0]
                xlb_xle_tau = xlb_xle_tau[0]
                if pd.notna(base_tau) and pd.notna(xlb_xle_tau):
                    delta = xlb_xle_tau - base_tau
                    arrow = "↑" if delta > 0.05 else "↓" if delta < -0.05 else "≈"
                    print(f"  {base_name:15s}: {base_tau:+.4f} → {xlb_xle_tau:+.4f} (Δ={delta:+.4f}) {arrow}")

    # Save results
    path = os.path.join(OUTPUT_DIR, "systematic_basket_results.csv")
    results_df.to_csv(path, index=False)
    print(f"\nSaved to {path}")

    return results_df


if __name__ == "__main__":
    results_df = main()
