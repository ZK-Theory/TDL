"""
Phase 10B - Task A.1: τ Spike Identification
=============================================

Purpose:
    Identify all dates where |τ| > 0.5 and compute forward returns/drawdowns
    to characterize the predictive content of τ spikes.

Input:
    outputs/phase_10/continuous_signal_2000_2025.csv

Output:
    outputs/phase_10b/tau_spikes_events.csv

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import timedelta

# ============================================================================
# CONFIGURATION (LOCKED - NO P-HACKING)
# ============================================================================
TAU_SPIKE_THRESHOLD = 0.5  # |τ| > 0.5 defines a spike
FORWARD_WINDOWS = [30, 60, 90]  # Days to look ahead

# Known crisis events for labeling
KNOWN_CRISES = {
    "2000 Dotcom": ("2000-03-10", "2002-10-09"),
    "2008 GFC": ("2007-10-09", "2009-03-09"),
    "2010 Flash Crash": ("2010-05-06", "2010-05-06"),
    "2011 Debt Crisis": ("2011-08-01", "2011-10-04"),
    "2015 China Crash": ("2015-08-18", "2015-08-25"),
    "2018 Vol Spike": ("2018-02-01", "2018-02-09"),
    "2020 COVID": ("2020-02-19", "2020-03-23"),
    "2022 Crypto/Fed": ("2022-01-03", "2022-10-12"),
}

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
INPUT_FILE = BASE_DIR / "outputs" / "phase_10" / "continuous_signal_2000_2025.csv"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b"


def ensure_dirs():
    """Create output directories if needed."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def load_tau_series():
    """Load the continuous τ series from Phase 10."""
    print(f"Loading τ series from: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, index_col=0, parse_dates=True)
    print(f"  Loaded {len(df)} days from {df.index.min()} to {df.index.max()}")
    return df


def fetch_spx_data(start_date, end_date):
    """Fetch S&P 500 daily data for return/drawdown calculations."""
    print(f"Fetching S&P 500 data from {start_date} to {end_date}...")
    # Extend end date to cover forward windows
    extended_end = pd.to_datetime(end_date) + timedelta(days=120)

    spx = yf.download("^GSPC", start=start_date, end=extended_end, progress=False)
    if spx.empty:
        raise ValueError("Failed to fetch S&P 500 data")

    # Handle MultiIndex columns from yfinance
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)

    print(f"  Fetched {len(spx)} days")
    return spx["Close"]


def compute_forward_returns(date, spx_close, windows):
    """Compute forward returns for given windows."""
    results = {}
    try:
        # Get the index position of the date
        date = pd.to_datetime(date)
        if date not in spx_close.index:
            # Find nearest date
            idx = spx_close.index.get_indexer([date], method="nearest")[0]
            date = spx_close.index[idx]

        current_price = spx_close.loc[date]
        date_idx = spx_close.index.get_loc(date)

        for w in windows:
            future_idx = date_idx + w
            if future_idx < len(spx_close):
                future_price = spx_close.iloc[future_idx]
                results[f"fwd_ret_{w}d"] = (future_price - current_price) / current_price
            else:
                results[f"fwd_ret_{w}d"] = np.nan
    except Exception as e:
        print(f"  Warning: Could not compute returns for {date}: {e}")
        for w in windows:
            results[f"fwd_ret_{w}d"] = np.nan

    return results


def compute_max_drawdown(date, spx_close, windows):
    """Compute maximum drawdown in forward windows."""
    results = {}
    try:
        date = pd.to_datetime(date)
        if date not in spx_close.index:
            idx = spx_close.index.get_indexer([date], method="nearest")[0]
            date = spx_close.index[idx]

        current_price = spx_close.loc[date]
        date_idx = spx_close.index.get_loc(date)

        for w in windows:
            future_idx = min(date_idx + w, len(spx_close) - 1)
            if date_idx < len(spx_close) - 1:
                # Get price series for the window
                window_prices = spx_close.iloc[date_idx : future_idx + 1]
                # Calculate drawdown from starting price
                min_price = window_prices.min()
                max_drawdown = (current_price - min_price) / current_price
                results[f"max_dd_{w}d"] = max_drawdown
            else:
                results[f"max_dd_{w}d"] = np.nan
    except Exception as e:
        print(f"  Warning: Could not compute drawdown for {date}: {e}")
        for w in windows:
            results[f"max_dd_{w}d"] = np.nan

    return results


def label_crisis(date):
    """Label if a date falls within a known crisis period."""
    date = pd.to_datetime(date)
    for crisis_name, (start, end) in KNOWN_CRISES.items():
        crisis_start = pd.to_datetime(start)
        crisis_end = pd.to_datetime(end)
        # Check if date is within 60 days before crisis start or during crisis
        if crisis_start - timedelta(days=60) <= date <= crisis_end:
            return crisis_name
    return "None"


def identify_spikes(df):
    """Identify all τ spikes and compute metrics."""
    print(f"\nIdentifying τ spikes with |τ| > {TAU_SPIKE_THRESHOLD}...")

    # Filter for spikes
    spikes = df[df["Tau"].abs() > TAU_SPIKE_THRESHOLD].copy()
    print(f"  Found {len(spikes)} spike days")

    if len(spikes) == 0:
        print("  WARNING: No spikes found!")
        return pd.DataFrame()

    # Get date range for SPX data
    start_date = spikes.index.min() - timedelta(days=10)
    end_date = spikes.index.max()

    # Fetch SPX data
    spx_close = fetch_spx_data(start_date, end_date)

    # Compute metrics for each spike
    results = []
    for date, row in spikes.iterrows():
        spike_info = {
            "date": date,
            "tau": row["Tau"],
            "tau_sign": "positive" if row["Tau"] > 0 else "negative",
            "vix": row.get("VIX", np.nan),
        }

        # Forward returns
        fwd_returns = compute_forward_returns(date, spx_close, FORWARD_WINDOWS)
        spike_info.update(fwd_returns)

        # Max drawdowns
        max_dds = compute_max_drawdown(date, spx_close, FORWARD_WINDOWS)
        spike_info.update(max_dds)

        # Crisis label
        spike_info["crisis_label"] = label_crisis(date)

        results.append(spike_info)

    results_df = pd.DataFrame(results)
    results_df.set_index("date", inplace=True)

    return results_df


def summarize_spikes(df):
    """Print summary statistics of spike events."""
    print("\n" + "=" * 60)
    print("τ SPIKE IDENTIFICATION SUMMARY")
    print("=" * 60)

    n_total = len(df)
    n_pos = len(df[df["tau_sign"] == "positive"])
    n_neg = len(df[df["tau_sign"] == "negative"])

    print(f"\nTotal spikes (|τ| > {TAU_SPIKE_THRESHOLD}): {n_total}")
    print(f"  Positive spikes (τ > +{TAU_SPIKE_THRESHOLD}): {n_pos}")
    print(f"  Negative spikes (τ < -{TAU_SPIKE_THRESHOLD}): {n_neg}")

    # Crisis distribution
    print("\nSpikes by crisis label:")
    crisis_counts = df["crisis_label"].value_counts()
    for crisis, count in crisis_counts.items():
        print(f"  {crisis}: {count}")

    # Tau statistics by sign
    print("\nτ value statistics:")
    print(f"  Positive spikes - mean τ: {df[df['tau_sign']=='positive']['tau'].mean():.3f}")
    print(f"  Negative spikes - mean τ: {df[df['tau_sign']=='negative']['tau'].mean():.3f}")

    # Forward return preview
    print("\nForward 30d return preview:")
    print(f"  Positive spikes - mean: {df[df['tau_sign']=='positive']['fwd_ret_30d'].mean()*100:.2f}%")
    print(f"  Negative spikes - mean: {df[df['tau_sign']=='negative']['fwd_ret_30d'].mean()*100:.2f}%")

    # Max drawdown preview
    print("\nMax 30d drawdown preview:")
    print(f"  Positive spikes - mean: {df[df['tau_sign']=='positive']['max_dd_30d'].mean()*100:.2f}%")
    print(f"  Negative spikes - mean: {df[df['tau_sign']=='negative']['max_dd_30d'].mean()*100:.2f}%")


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK A.1: τ SPIKE IDENTIFICATION")
    print("=" * 60)

    ensure_dirs()

    # Load data
    tau_df = load_tau_series()

    # Identify spikes and compute metrics
    spikes_df = identify_spikes(tau_df)

    if len(spikes_df) == 0:
        print("\nERROR: No spikes found. Check input data.")
        return

    # Save results
    output_file = OUTPUT_DIR / "tau_spikes_events.csv"
    spikes_df.to_csv(output_file)
    print(f"\nSaved spike events to: {output_file}")

    # Print summary
    summarize_spikes(spikes_df)

    print("\n" + "=" * 60)
    print("TASK A.1 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
