"""
Debug Normalization Ratios
==========================
Calculates the exact ratios of 2023 metrics against 2008 baselines
to investigate why L1 Variance appears 'Red'.
"""

import pandas as pd
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics
from pathlib import Path

DATA_DIR = Path("outputs")
WINDOW_SIZE = 500


def load_data(filename):
    path = DATA_DIR / filename
    norms = pd.read_csv(path, index_col=0)
    norms.index = pd.to_datetime(norms.index, utc=True)
    if norms.index.tz is not None:
        norms.index = norms.index.tz_localize(None)
    stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)
    return stats.iloc[WINDOW_SIZE:]


def main():
    s_08 = load_data("2008_gfc_lp_norms.csv")
    s_23 = load_data("2023_2025_realtime_lp_norms.csv")

    baselines = s_08.max()

    print(
        f"{'Metric':<30} | {'2008 Max':<12} | {'2023 Max':<12} | {'Max Ratio':<10} | {'Mean Ratio':<10} | {'Days > 0.7'}"
    )
    print("-" * 100)

    for col in baselines.index:
        if col not in s_23.columns:
            continue

        b_max = baselines[col]
        vals_23 = s_23[col]

        ratio_series = vals_23 / b_max
        max_ratio = ratio_series.max()
        mean_ratio = ratio_series.mean()
        days_red = (ratio_series > 0.7).sum()

        print(
            f"{col:<30} | {b_max:.2e}   | {vals_23.max():.2e}   | {max_ratio:.4f}     | {mean_ratio:.4f}     | {days_red}"
        )


if __name__ == "__main__":
    main()
