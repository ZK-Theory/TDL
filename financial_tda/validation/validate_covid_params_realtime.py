"""
Validation of COVID-Optimized Parameters on Real-Time Data (2023-2025)
======================================================================
Checks for False Positives using W=450, P=200.
"""

import os
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
from scipy.stats import kendalltau
from financial_tda.validation.gidea_katz_replication import fetch_historical_data, compute_persistence_landscape_norms
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics


def ensure_output_dirs():
    os.makedirs("outputs", exist_ok=True)


def run_validation():
    print("=" * 80)
    print("VALIDATING COVID PARAMETERS (W=450, P=200) ON 2023-2025 DATA")
    print("=" * 80)
    ensure_output_dirs()

    # 1. Fetch Data
    print("\nFetching market data (2022-01-01 to Present)...")
    prices_dict = fetch_historical_data("2022-01-01", "2025-12-31")
    if not prices_dict:
        raise ValueError("No data fetched")

    # 2. Compute Norms
    print("Computing L^p Norms...")
    norms_df = compute_persistence_landscape_norms(prices=prices_dict, window_size=50, stride=1, n_layers=5)
    norms_df.to_csv("outputs/2023_2025_realtime_lp_norms.csv")

    # 3. Compute Rolling Statistics (W=450)
    W = 450
    print(f"Computing Rolling Statistics (Window W={W})...")
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=W)

    # 4. Compute Daily Kendall-Tau (P=200)
    P = 200
    metrics = [
        "L1_norm_variance",
        "L2_norm_variance",
        "L1_norm_spectral_density_low",
        "L2_norm_spectral_density_low",
        "L1_norm_acf_1",
        "L2_norm_acf_1",
    ]

    results = []

    # Start loop after we have enough data (W + P)
    # Actually rolling stats start at index W-1.
    # We need P points of rolling stats.
    # So start at index W + P.

    start_idx = W + P
    if start_idx >= len(stats_df):
        print(f"Warning: Not enough data. Length={len(stats_df)}, Required={start_idx}")
        return

    print(f"Computing Daily Kendall-Tau (P={P})...")

    # Iterate through days
    for i in range(start_idx, len(stats_df)):
        current_date = stats_df.index[i]

        # Extract window for Tau computation: [i-P+1, i]
        window_stats = stats_df.iloc[i - P + 1 : i + 1]

        row = {"Date": current_date}
        max_tau = -1.0
        max_metric = ""

        for metric in metrics:
            if metric not in window_stats.columns:
                continue

            y = window_stats[metric].values
            # Filter NaNs (though rolling stats shouldn't have NaNs after W)
            valid_mask = ~np.isnan(y)
            if valid_mask.sum() < P * 0.9:  # Require 90% valid data
                row[metric] = np.nan
                continue

            x = np.arange(len(y))
            tau, p = kendalltau(x[valid_mask], y[valid_mask])
            row[metric] = tau

            if tau > max_tau:
                max_tau = tau
                max_metric = metric

        row["Max_Tau"] = max_tau
        row["Max_Metric"] = max_metric
        results.append(row)

        if i % 100 == 0:
            print(f"Processed {current_date.date()}... Max Tau: {max_tau:.4f}")

    results_df = pd.DataFrame(results)
    results_df.set_index("Date", inplace=True)
    results_df.to_csv("outputs/2023_2025_covid_params_daily_tau.csv")

    # 5. Analysis
    print("\n" + "-" * 80)
    print("RESULTS SUMMARY")
    print("-" * 80)

    threshold = 0.70
    false_positives = results_df[results_df["Max_Tau"] >= threshold]
    elevated_risk = results_df[results_df["Max_Tau"] >= 0.60]

    print(f"Parameter Set: W={W}, P={P}")
    print(f"Total Days Analyzed: {len(results_df)}")
    print(f"False Positives (Tau >= 0.70): {len(false_positives)}")
    print(f"Elevated Risk (Tau >= 0.60): {len(elevated_risk)}")
    print(f"Global Max Tau: {results_df['Max_Tau'].max():.4f}")
    if not false_positives.empty:
        print("\nFalse Positive Dates:")
        print(false_positives[["Max_Tau", "Max_Metric"]])

    if not elevated_risk.empty:
        print("\nElevated Risk Dates (Top 5):")
        print(elevated_risk[["Max_Tau", "Max_Metric"]].sort_values("Max_Tau", ascending=False).head(5))


if __name__ == "__main__":
    run_validation()
