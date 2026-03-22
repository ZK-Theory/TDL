"""
Inspect ACF Statistics
======================
Checks the distribution (Min, Mean, Max, Std) of ACF Lag-1 values
for 2008 and 2023 to understand why they appear "always red".
"""

import pandas as pd
from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

DATA_DIR = Path("outputs")
WINDOW_SIZE = 500


def get_stats(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return None

    norms = pd.read_csv(path, index_col=0)
    norms.index = pd.to_datetime(norms.index, utc=True)
    if norms.index.tz is not None:
        norms.index = norms.index.tz_localize(None)

    stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)
    valid = stats.iloc[WINDOW_SIZE:]

    return valid


def main():
    df_08 = get_stats("2008_gfc_lp_norms.csv")
    df_23 = get_stats("2023_2025_realtime_lp_norms.csv")

    print(f"{'Metric':<30} | {'Period':<10} | {'Min':<10} | {'Mean':<10} | {'Max':<10} | {'Std':<10}")
    print("-" * 90)

    for col in ["L1_norm_acf_lag1", "L2_norm_acf_lag1"]:
        # Handle naming variation
        c_08 = col if col in df_08.columns else col.replace("lag1", "1")
        c_23 = col if col in df_23.columns else col.replace("lag1", "1")

        s_08 = df_08[c_08].dropna()
        s_23 = df_23[c_23].dropna()

        print(
            f"{col:<30} | 2008       | {s_08.min():.4f}     | {s_08.mean():.4f}     | {s_08.max():.4f}     | {s_08.std():.4f}"
        )
        print(
            f"{col:<30} | 2023       | {s_23.min():.4f}     | {s_23.mean():.4f}     | {s_23.max():.4f}     | {s_23.std():.4f}"
        )


if __name__ == "__main__":
    main()
