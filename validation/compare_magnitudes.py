"""
Compare 2008 vs 2023 Magnitudes
===============================
Checks peak values of rolling stats to calibrate heatmap thresholds.
"""

import pandas as pd
from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

DATA_DIR = Path("outputs")
WINDOW_SIZE = 500


def get_max_stats(filename):
    path = DATA_DIR / filename
    norms = pd.read_csv(path, index_col=0, parse_dates=True)
    # Ensure datetime index
    norms.index = pd.to_datetime(norms.index, utc=True)
    if norms.index.tz is not None:
        norms.index = norms.index.tz_localize(None)

    stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)
    # Exclude burn-in
    valid = stats.iloc[WINDOW_SIZE:]
    return valid.max()


def main():
    max_2008 = get_max_stats("2008_gfc_lp_norms.csv")
    max_2023 = get_max_stats("2023_2025_realtime_lp_norms.csv")

    print(f"{'Metric':<30} | {'2008 Max':<15} | {'2023 Max':<15} | {'Ratio (2023/2008)':<15}")
    print("-" * 80)

    for col in max_2008.index:
        val_08 = max_2008.get(col, 0)
        val_23 = max_2023.get(col, 0)
        ratio = val_23 / val_08 if val_08 != 0 else 0
        print(f"{col:<30} | {val_08:.4e}      | {val_23:.4e}      | {ratio:.2f}")


if __name__ == "__main__":
    main()
