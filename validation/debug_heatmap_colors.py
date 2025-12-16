"""
Debug Heatmap Colors
====================
Dumps formatted table of daily ratios and assigned colors
for 2023-2025 to verify user observations.
"""

import pandas as pd
from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

DATA_DIR = Path("outputs")
WINDOW_SIZE = 500


def get_color_name(ratio):
    # Bounds: [0.0, 0.5, 0.7, 0.9, 100.0]
    # Colors: Green, Yellow, Orange, Red
    if ratio < 0.5:
        return "Green"
    if ratio < 0.7:
        return "Yellow"
    if ratio < 0.9:
        return "Orange"
    return "RED"


def load_data(filename):
    path = DATA_DIR / filename
    norms = pd.read_csv(path, index_col=0)
    norms.index = pd.to_datetime(norms.index, utc=True)
    if norms.index.tz is not None:
        norms.index = norms.index.tz_localize(None)
    stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)
    return stats.iloc[WINDOW_SIZE:]


def main():
    # Load Baselines (2008 Max)
    s_08 = load_data("2008_gfc_lp_norms.csv")
    baselines = s_08.max()

    # Load 2023
    s_23 = load_data("2023_2025_realtime_lp_norms.csv")

    print(f"{'Date':<12} | {'L1 Var Ratio':<15} | {'Color':<10} | {'L1 SD Ratio':<15} | {'Color':<10}")
    print("-" * 80)

    # Sample every 30 days to save space, but cover the user's "Red" periods
    # User mentioned: "25-04 to 23-07" (Assuming 2023-04 to 2023-07?)
    # "23-05-2025 to 20-08-2025" (May-Aug 2025)

    for date in s_23.index[::10]:  # Every 10 days
        l1_var = s_23.loc[date, "L1_norm_variance"]
        l1_sd = s_23.loc[date, "L1_norm_spectral_density_low"]

        r_var = l1_var / baselines["L1_norm_variance"]
        r_sd = l1_sd / baselines["L1_norm_spectral_density_low"]

        print(
            f"{date.strftime('%Y-%m-%d'):<12} | {r_var:.4f}          | {get_color_name(r_var):<10} | {r_sd:.4f}          | {get_color_name(r_sd):<10}"
        )


if __name__ == "__main__":
    main()
