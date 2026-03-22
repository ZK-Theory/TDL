"""
Debug Data Inspection
=====================
Inspects the value ranges and NaN counts of the standard rolling statistics outputs
to diagnose heatmap normalization and missing data issues.
"""

import pandas as pd
from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

DATA_DIR = Path("outputs")


def inspect_file(filename):
    print(f"\n--- Inspecting {filename} ---")
    path = DATA_DIR / filename
    if not path.exists():
        print("File not found.")
        return

    # Load Norms
    norms_df = pd.read_csv(path, index_col=0, parse_dates=True)
    print(f"Norms Shape: {norms_df.shape}")
    print(f"Date Range: {norms_df.index.min()} to {norms_df.index.max()}")

    # Compute Stats
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=500)
    print(f"Stats Shape: {stats_df.shape}")

    # Check for NaNs
    nan_counts = stats_df.isna().sum()
    print("\nNaN Counts per column:")
    print(nan_counts[nan_counts > 0])

    # Check Value Ranges (ignoring NaNs)
    print("\nValue Ranges (Min / Max / Mean):")
    for col in stats_df.columns:
        valid = stats_df[col].dropna()
        if not valid.empty:
            print(f"{col}: {valid.min():.4e} / {valid.max():.4e} / {valid.mean():.4e}")
        else:
            print(f"{col}: ALL NANS")


def main():
    files = ["2008_gfc_lp_norms.csv", "2023_2025_realtime_lp_norms.csv"]

    for f in files:
        inspect_file(f)


if __name__ == "__main__":
    main()
