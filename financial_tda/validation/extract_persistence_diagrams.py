"""
Phase 10B - Task C.1: Extract Persistence Diagrams
===================================================

Purpose:
    Extract daily H0 and H1 persistence diagrams for GFC and COVID periods
    to understand WHY topological variance behaves differently.

Periods:
    - GFC: 2007-09-01 to 2008-09-15
    - COVID: 2019-12-01 to 2020-03-20

Output:
    outputs/phase_10b/persistence_diagrams/gfc_2007_2008/
    outputs/phase_10b/persistence_diagrams/covid_2019_2020/

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
import pickle

# Import TDA pipeline
from financial_tda.topology.filtration import compute_persistence_vr

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b" / "persistence_diagrams"

# Crisis periods for analysis
CRISIS_PERIODS = {
    "gfc_2007_2008": {
        "name": "2008 GFC",
        "data_start": "2007-06-01",  # Include lead-up period
        "data_end": "2008-09-30",
        "analysis_start": "2007-09-01",
        "analysis_end": "2008-09-15",
    },
    "covid_2019_2020": {
        "name": "2020 COVID",
        "data_start": "2019-09-01",  # Include lead-up period
        "data_end": "2020-04-15",
        "analysis_start": "2019-12-01",
        "analysis_end": "2020-03-20",
    },
}

# TDA Parameters (from METHODOLOGY_REFERENCE.md)
WINDOW_SIZE = 50  # Point cloud window
TICKERS = ["^GSPC", "^DJI", "^IXIC", "^RUT"]  # Standard US basket


def ensure_dirs():
    """Create output directories."""
    for crisis_id in CRISIS_PERIODS.keys():
        crisis_dir = OUTPUT_DIR / crisis_id
        crisis_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def fetch_data(start_date, end_date):
    """Fetch price data for the period."""
    print(f"Fetching data from {start_date} to {end_date}...")

    prices = {}
    for ticker in TICKERS:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        prices[ticker] = data["Close"]
        print(f"  {ticker}: {len(prices[ticker])} days")

    # Align and compute log returns
    aligned_df = pd.DataFrame(prices).dropna()
    log_returns = np.log(aligned_df / aligned_df.shift(1)).dropna()

    print(f"  Total aligned days: {len(log_returns)}")
    return log_returns


def compute_daily_diagrams(returns_df, start_date, end_date):
    """Compute persistence diagrams for each day in the analysis period."""
    print(f"\nComputing diagrams from {start_date} to {end_date}...")

    # Filter to analysis period
    mask = (returns_df.index >= start_date) & (returns_df.index <= end_date)
    analysis_returns = returns_df[mask]

    results = {}
    n_days = len(analysis_returns)

    for i, (date, _) in enumerate(analysis_returns.iterrows()):
        if i < WINDOW_SIZE:
            continue

        if i % 20 == 0:
            print(f"  Processing {date.date()} ({i}/{n_days})...")

        # Get window ending at this date
        window_end_idx = returns_df.index.get_loc(date)
        window_start_idx = window_end_idx - WINDOW_SIZE + 1

        if window_start_idx < 0:
            continue

        window_data = returns_df.iloc[window_start_idx : window_end_idx + 1].values

        # Compute persistence diagrams
        try:
            # H0 and H1
            diagram_h0 = compute_persistence_vr(window_data, homology_dimensions=(0,))
            diagram_h1 = compute_persistence_vr(window_data, homology_dimensions=(1,))

            # Store
            results[date] = {
                "H0": diagram_h0,
                "H1": diagram_h1,
                "n_h0_features": len(diagram_h0),
                "n_h1_features": len(diagram_h1),
            }

            # Compute summary statistics
            if len(diagram_h1) > 0:
                h1_lifetimes = diagram_h1[:, 1] - diagram_h1[:, 0]
                finite_mask = np.isfinite(h1_lifetimes)
                if finite_mask.any():
                    results[date]["h1_total_persistence"] = h1_lifetimes[finite_mask].sum()
                    results[date]["h1_mean_lifetime"] = h1_lifetimes[finite_mask].mean()
                    results[date]["h1_max_lifetime"] = h1_lifetimes[finite_mask].max()
                    results[date]["h1_n_finite"] = finite_mask.sum()
                else:
                    results[date]["h1_total_persistence"] = 0
                    results[date]["h1_mean_lifetime"] = 0
                    results[date]["h1_max_lifetime"] = 0
                    results[date]["h1_n_finite"] = 0
            else:
                results[date]["h1_total_persistence"] = 0
                results[date]["h1_mean_lifetime"] = 0
                results[date]["h1_max_lifetime"] = 0
                results[date]["h1_n_finite"] = 0

        except Exception as e:
            print(f"  Warning: Error at {date}: {e}")
            continue

    print(f"  Computed {len(results)} diagrams")
    return results


def save_diagrams(results, crisis_id):
    """Save persistence diagrams to disk."""
    crisis_dir = OUTPUT_DIR / crisis_id

    # Save raw diagrams as pickle
    diagrams_file = crisis_dir / "diagrams.pkl"
    with open(diagrams_file, "wb") as f:
        pickle.dump(results, f)
    print(f"  Saved diagrams to: {diagrams_file}")

    # Save summary statistics as CSV
    summary_data = []
    for date, data in results.items():
        summary_data.append(
            {
                "date": date,
                "n_h0": data["n_h0_features"],
                "n_h1": data["n_h1_features"],
                "h1_total_persistence": data.get("h1_total_persistence", 0),
                "h1_mean_lifetime": data.get("h1_mean_lifetime", 0),
                "h1_max_lifetime": data.get("h1_max_lifetime", 0),
                "h1_n_finite": data.get("h1_n_finite", 0),
            }
        )

    summary_df = pd.DataFrame(summary_data)
    summary_df.set_index("date", inplace=True)
    summary_file = crisis_dir / "diagram_summary.csv"
    summary_df.to_csv(summary_file)
    print(f"  Saved summary to: {summary_file}")

    return summary_df


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK C.1: EXTRACT PERSISTENCE DIAGRAMS")
    print("=" * 60)

    ensure_dirs()

    all_summaries = {}

    for crisis_id, config in CRISIS_PERIODS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {config['name']}")
        print(f"{'='*60}")

        # Fetch data
        returns_df = fetch_data(config["data_start"], config["data_end"])

        # Compute diagrams
        results = compute_daily_diagrams(returns_df, config["analysis_start"], config["analysis_end"])

        # Save
        summary_df = save_diagrams(results, crisis_id)
        all_summaries[crisis_id] = summary_df

    # Print comparison
    print("\n" + "=" * 60)
    print("SUMMARY COMPARISON")
    print("=" * 60)

    for crisis_id, summary_df in all_summaries.items():
        config = CRISIS_PERIODS[crisis_id]
        print(f"\n{config['name']}:")
        print(f"  Days analyzed: {len(summary_df)}")
        print(f"  Mean H1 features: {summary_df['n_h1'].mean():.1f}")
        print(f"  Mean H1 total persistence: {summary_df['h1_total_persistence'].mean():.3f}")
        print(f"  Mean H1 lifetime: {summary_df['h1_mean_lifetime'].mean():.4f}")
        print(f"  H1 persistence variance: {summary_df['h1_total_persistence'].var():.6f}")

    print("\n" + "=" * 60)
    print("TASK C.1 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
