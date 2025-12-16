"""
Six Market Tau Analysis
=======================
Calculates Kendall Tau for the 6-market global basket (2008 vs 2023).
Also checks data continuity to diagnose 'missing patches' in heatmaps.
"""

import pandas as pd
import numpy as np
from scipy.stats import kendalltau
from pathlib import Path

DATA_DIR = Path("outputs/six_markets")
WINDOW_SIZE = 500


def load_stats(filename):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"Missing: {path}")
        return None

    stats = pd.read_csv(path, index_col=0)
    stats.index = pd.to_datetime(stats.index, utc=True)
    if stats.index.tz is not None:
        stats.index = stats.index.tz_localize(None)

    # Check for gaps
    dates = stats.index
    diffs = dates.to_series().diff().dt.days
    gaps = diffs[diffs > 3]  # More than a weekend
    if not gaps.empty:
        print(f"  [WARN] Found {len(gaps)} large gaps (>3 days) in {filename}")
        print(f"  Max Gap: {diffs.max()} days")
    else:
        print("  [OK] Data is continuous (no gaps >3 days)")

    return stats


def compute_period_tau(stats, name, analysis_window=200):
    print(f"\n--- {name} (Window={analysis_window}) ---")

    # Use tail of valid data
    # stats includes NaNs at start? six_market_analysis saved computed stats.
    # It might have saved NaNs.

    valid_stats = stats.dropna()
    print(f"  Valid Rows: {len(valid_stats)} / {len(stats)} Total")

    if len(valid_stats) < 50:
        print("  [ERR] Insufficient data for Tau")
        return

    # Take the 'Analysis Window' (e.g. 200 days)
    # For 2008, we want pre-crisis. For 2023, we want the whole period or worst window?
    # Let's compute Max Tau across sliding windows, or simpler: Tau of the whole "Stress" period?
    # G&K use sliding window.
    # Let's simply compute Tau for the LAST 250 days of the dataset (as a proxy for specific period performance)
    # OR better: Compute Max Rolling Tau (window=250) like in the heatmaps.

    metrics = [c for c in valid_stats.columns if "variance" in c or "spectral" in c or "acf" in c]

    max_taus = {}

    for metric in metrics:
        y = valid_stats[metric].values
        x = np.arange(len(y))

        # Overall Tau (Linear Trend of entire period)
        tau_overall, _ = kendalltau(x, y)

        # Max Rolling Tau (250 days)
        max_rolling = -1.0
        if len(y) > 250:
            for i in range(250, len(y), 10):
                y_win = y[i - 250 : i]
                x_win = np.arange(len(y_win))
                t, _ = kendalltau(x_win, y_win)
                if t > max_rolling:
                    max_rolling = t
        else:
            max_rolling = tau_overall

        max_taus[metric] = max_rolling
        print(f"  {metric:<30} | Max Rolling Tau: {max_rolling:.4f}")


def main():
    # 2008
    s08 = load_stats("2008_gfc_stats.csv")
    if s08 is not None:
        compute_period_tau(s08, "2008 Global Financial Crisis")

    # 2023
    s23 = load_stats("2023_2025_stats.csv")
    if s23 is not None:
        compute_period_tau(s23, "2023-2025 Validation")

    # 2000
    s00 = load_stats("2000_dotcom_stats.csv")
    if s00 is not None:
        compute_period_tau(s00, "2000 Dotcom")


if __name__ == "__main__":
    main()
