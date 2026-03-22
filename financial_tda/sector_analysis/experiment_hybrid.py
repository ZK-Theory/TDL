"""
Experiment E: Hybrid Index + Sector Analysis

Combines the best-performing broad indices from the main paper
(S&P 500, NASDAQ, DAX, FTSE) with sector ETFs to create sector-enhanced
baskets that may better identify crisis origins.

Approach:
1. Core basket: 4 broad indices (GSPC, IXIC, GDAXI, FTSE) - proven τ > 0.7
2. For each crisis, add the hypothesized "epicenter" sector
3. Compare τ values: Does adding sector S improve signal for crisis type T?

Hypothesis:
- Adding XLK to Core improves Dotcom detection
- Adding XLF to Core improves GFC detection
- Adding XLE to Core improves COVID detection
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
WINDOW_SIZE = 50  # Point cloud window
ROLLING_WINDOW = 500  # Rolling statistics window (G&K standard - CRITICAL)
PRE_CRISIS_WINDOW = 250
START_DATE = "1999-01-01"
END_DATE = "2024-12-31"

# Core broad indices (best performers from main paper)
CORE_INDICES = ["^GSPC", "^IXIC", "^GDAXI", "^FTSE"]

# Sector ETFs to test
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLY": "Consumer Disc",
    "XLV": "Healthcare",
}

# Crises with expected sector epicenters
EVENTS = [
    {"name": "2000 Dotcom", "date": "2000-03-10", "epicenter": "XLK"},
    {"name": "2008 GFC", "date": "2008-09-15", "epicenter": "XLF"},
    {"name": "2020 COVID", "date": "2020-03-16", "epicenter": "XLE"},
]


def fetch_hybrid_data(tickers, start=START_DATE, end=END_DATE):
    """Fetch and preprocess data for a basket of tickers."""
    df = yf.download(tickers, start=start, end=end, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        prices = df["Adj Close"] if "Adj Close" in df.columns.get_level_values(0) else df["Close"]
    else:
        prices = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]

    prices = prices[tickers].ffill().dropna()
    log_returns = np.log(prices / prices.shift(1)).dropna()
    standardized = (log_returns - log_returns.mean()) / log_returns.std()

    return standardized


def compute_rolling_h1_var(data, window=WINDOW_SIZE, var_window=ROLLING_WINDOW):
    """Compute rolling H₁ L² variance using the main paper's methodology."""
    values = data.values
    dates = data.index
    results = []

    for i in range(window, len(values)):
        window_data = values[i - window : i]

        # Build point cloud with delay embedding
        cloud = []
        for t in range(1, window):
            point = []
            for col in range(data.shape[1]):
                point.extend([window_data[t, col], window_data[t - 1, col]])
            cloud.append(point)

        # Compute H₁
        rips = gd.RipsComplex(points=cloud)
        st = rips.create_simplex_tree(max_dimension=2)
        st.compute_persistence()
        h1 = st.persistence_intervals_in_dimension(1)

        if len(h1) == 0:
            l2 = 0.0
        else:
            finite = h1[np.isfinite(h1[:, 1])]
            if len(finite) == 0:
                l2 = 0.0
            else:
                lifetimes = finite[:, 1] - finite[:, 0]
                l2 = np.sqrt(np.sum(lifetimes**2))

        results.append({"Date": dates[i], "L2": l2})

    df = pd.DataFrame(results).set_index("Date")
    df["L2_Var"] = df["L2"].rolling(var_window).var()
    return df


def compute_tau_for_event(norms_df, event_date, pre_crisis_days=PRE_CRISIS_WINDOW):
    """Compute Kendall-τ for pre-crisis window."""
    if event_date < norms_df.index[0] or event_date > norms_df.index[-1]:
        return np.nan, np.nan, "Out of range"

    if event_date not in norms_df.index:
        locs = norms_df.index.get_indexer([event_date], method="nearest")
        event_date = norms_df.index[locs[0]]

    end_loc = norms_df.index.get_loc(event_date)
    start_loc = max(0, end_loc - pre_crisis_days)

    series = norms_df["L2_Var"].iloc[start_loc:end_loc].dropna()
    if len(series) < 50:
        return np.nan, np.nan, "Insufficient data"

    tau, p = kendalltau(np.arange(len(series)), series.values)
    return tau, p, "OK"


def main():
    print("=" * 70)
    print("Experiment E: Hybrid Broad Index + Sector Analysis")
    print("Testing if sector-specific additions improve crisis detection")
    print("=" * 70)

    results = []

    # First: Baseline with core indices only
    print("\n[1] Computing baseline (Core indices only)...")
    print(f"    Basket: {CORE_INDICES}")

    core_data = fetch_hybrid_data(CORE_INDICES)
    print(f"    Data: {len(core_data)} days, {core_data.shape[1]}D → {core_data.shape[1]*2}D embedded")

    core_norms = compute_rolling_h1_var(core_data)

    print("\n    Baseline τ values:")
    for event in EVENTS:
        tau, p, status = compute_tau_for_event(core_norms, pd.to_datetime(event["date"]))
        if status == "OK":
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(f"    {event['name']:20s}: τ = {tau:+.4f} {sig}")
            results.append(
                {"Basket": "Core (4 indices)", "Event": event["name"], "AddedSector": None, "Tau": tau, "P_Value": p}
            )

    # Now test each sector addition
    print("\n[2] Testing sector additions...")

    for sector, sector_name in SECTOR_ETFS.items():
        print(f"\n    Testing Core + {sector} ({sector_name})...")

        hybrid_tickers = CORE_INDICES + [sector]
        hybrid_data = fetch_hybrid_data(hybrid_tickers)

        if len(hybrid_data) < 500:
            print("      Insufficient data, skipping")
            continue

        hybrid_norms = compute_rolling_h1_var(hybrid_data)

        for event in EVENTS:
            tau, p, status = compute_tau_for_event(hybrid_norms, pd.to_datetime(event["date"]))

            results.append(
                {
                    "Basket": f"Core + {sector}",
                    "Event": event["name"],
                    "AddedSector": sector,
                    "Tau": tau,
                    "P_Value": p,
                    "IsEpicenter": sector == event["epicenter"],
                }
            )

            if status == "OK":
                epic = " ← EPICENTER" if sector == event["epicenter"] else ""
                sig = "***" if p < 0.001 else "**" if p < 0.01 else ""
                print(f"      {event['name']:20s}: τ = {tau:+.4f} {sig}{epic}")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Summary: Compare Core vs Core+Epicenter for each crisis
    print("\n" + "=" * 70)
    print("SUMMARY: Does adding the epicenter sector improve detection?")
    print("=" * 70)

    for event in EVENTS:
        event_name = event["name"]
        epicenter = event["epicenter"]

        core_tau = results_df[(results_df["Basket"] == "Core (4 indices)") & (results_df["Event"] == event_name)][
            "Tau"
        ].values
        epic_tau = results_df[(results_df["AddedSector"] == epicenter) & (results_df["Event"] == event_name)][
            "Tau"
        ].values

        if len(core_tau) > 0 and len(epic_tau) > 0:
            core_tau = core_tau[0]
            epic_tau = epic_tau[0]
            delta = epic_tau - core_tau
            improved = "IMPROVED" if delta > 0.05 else "SIMILAR" if abs(delta) <= 0.05 else "WORSE"
            print(f"\n{event_name}:")
            print(f"  Core only:        τ = {core_tau:+.4f}")
            print(f"  Core + {epicenter}:     τ = {epic_tau:+.4f}")
            print(f"  Δ = {delta:+.4f} → {improved}")

    # Find best sector for each crisis
    print("\n" + "=" * 70)
    print("Best sector addition for each crisis:")
    print("=" * 70)

    for event in EVENTS:
        event_name = event["name"]
        event_results = results_df[
            (results_df["Event"] == event_name) & (results_df["AddedSector"].notna()) & (results_df["Tau"].notna())
        ]
        if len(event_results) > 0:
            best_idx = event_results["Tau"].idxmax()
            if pd.notna(best_idx):
                best = event_results.loc[best_idx]
                expected = event["epicenter"]
                match = "✓" if best["AddedSector"] == expected else "✗"
                print(
                    f"{event_name}: Best = {best['AddedSector']} (τ={best['Tau']:.4f}) "
                    f"Expected = {expected} {match}"
                )
            else:
                print(f"{event_name}: No valid τ values")
        else:
            print(f"{event_name}: No results available")

    # Save
    path = os.path.join(OUTPUT_DIR, "hybrid_results.csv")
    results_df.to_csv(path, index=False)
    print(f"\nSaved to {path}")

    return results_df


if __name__ == "__main__":
    results_df = main()
