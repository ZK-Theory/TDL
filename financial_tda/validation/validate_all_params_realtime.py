"""
Validation of All Parameter Configurations on Real-Time Data (2023-2025)
========================================================================

Validates False Positive Rates for:
1. Standard (GFC): W=500, P=250
2. COVID-Optimized: W=450, P=200
3. Dotcom-Optimized: W=550, P=225

Generates statistics for Table 6 update.
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
    print("VALIDATING ALL PARAMETER SETS ON 2023-2025 DATA")
    print("=" * 80)
    ensure_output_dirs()

    # 1. Fetch Data
    norms_file = "outputs/2019_2025_realtime_lp_norms.csv"

    if os.path.exists(norms_file):
        print(f"\nLoading existing norms from {norms_file}...")
        norms_df = pd.read_csv(norms_file, index_col=0, parse_dates=True)
    else:
        print("\nFetching market data (2019-01-01 to Present)...")
        prices_dict = fetch_historical_data("2019-01-01", "2025-12-31")
        if not prices_dict:
            raise ValueError("No data fetched")

        print("Computing L^p Norms...")
        norms_df = compute_persistence_landscape_norms(prices=prices_dict, window_size=50, stride=1, n_layers=5)
        norms_df.to_csv(norms_file)
        print(f"Saved norms to {norms_file}")

    # CONFIGURATIONS
    configs = [
        {"name": "Standard (GFC)", "W": 500, "P": 250},
        {"name": "COVID Optimized", "W": 450, "P": 200},
        {"name": "Dotcom Optimized", "W": 550, "P": 225},
    ]

    metrics = [
        "L1_norm_variance",
        "L2_norm_variance",
        "L1_norm_spectral_density_low",
        "L2_norm_spectral_density_low",
    ]

    summary_stats = []

    for config in configs:
        name = config["name"]
        W = config["W"]
        P = config["P"]

        print(f"\nAnalyzing Config: {name} (W={W}, P={P})...")

        # 3. Compute Rolling Statistics
        stats_df = compute_gk_rolling_statistics(norms_df, window_size=W)

        # 4. Compute Daily Kendall-Tau
        results = []
        dates = []
        start_idx = W + P

        if start_idx >= len(stats_df):
            print(f"Warning: Not enough data. Length={len(stats_df)}, Required={start_idx}")
            continue

        print(f"Computing daily Tau for {len(stats_df) - start_idx} days...")

        for i in range(start_idx, len(stats_df)):
            # Extract window for Tau computation: [i-P+1, i]
            # Note: iloc is exclusive on end, so i+1 includes index i
            window_stats = stats_df.iloc[i - P + 1 : i + 1]

            row = {"Date": stats_df.index[i]}
            max_tau = -1.0

            for metric in metrics:
                if metric not in window_stats.columns:
                    continue

                y = window_stats[metric].values
                valid_mask = ~np.isnan(y)
                if valid_mask.sum() < P * 0.9:
                    continue

                x = np.arange(len(y))
                # Compute tau
                try:
                    tau, _ = kendalltau(x[valid_mask], y[valid_mask])
                    if not np.isnan(tau):
                        max_tau = max(max_tau, tau)
                except Exception as e:
                    print(
                        f"Error computing Kendall tau for metric '{metric}' on date "
                        f"{stats_df.index[i]}: {e}"
                    )

            if max_tau > -1.0:
                results.append(max_tau)
                dates.append(stats_df.index[i])

        if not results:
            print("No valid results computed.")
            continue

        results_array = np.array(results)
        dates_array = np.array(dates)

        # Create detailed DataFrame
        detail_df = pd.DataFrame({"Date": dates_array, "Tau": results_array})
        detail_df.set_index("Date", inplace=True)
        detail_filename = f"outputs/daily_tau_{name.replace(' ', '_').replace('(', '').replace(')', '')}.csv"
        detail_df.to_csv(detail_filename)

        avg_tau = np.mean(results_array)
        max_tau_val = np.max(results_array)
        std_tau = np.std(results_array)

        fp_count = np.sum(results_array >= 0.70)
        warning_count = np.sum(results_array >= 0.60)

        print(f"  Avg Tau: {avg_tau:.4f}")
        print(f"  Max Tau: {max_tau_val:.4f}")
        print(f"  False Positives (>=0.70): {fp_count}")

        # Print Top 5 Dates
        print("  Top 5 Crisis Dates:")
        top_5 = detail_df.sort_values("Tau", ascending=False).head(5)
        print(top_5)

        summary_stats.append(
            {
                "Configuration": name,
                "Parameters": f"W={W}, P={P}",
                "Average Tau": avg_tau,
                "Max Tau": max_tau_val,
                "Std Dev": std_tau,
                "False Positives (>=0.70)": fp_count,
                "Warnings (>=0.60)": warning_count,
                "N_Valid_Days": len(results_array),
            }
        )

    # 6. Save Summary
    summary_df = pd.DataFrame(summary_stats)
    print("\n" + "=" * 80)
    print("FINAL SUMMARY REPORT")
    print("=" * 80)
    print(summary_df.to_string(index=False))

    summary_df.to_csv("outputs/2023_2025_validation_summary_all_params.csv", index=False)
    print("\nSaved to outputs/2023_2025_validation_summary_all_params.csv")


if __name__ == "__main__":
    run_validation()
