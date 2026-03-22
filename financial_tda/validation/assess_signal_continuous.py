"""
Phase 10.1: Continuous Signal Analysis (2000-2025)
==================================================

Purpose:
    Generate the full time-series of Topological Complexity (Tau) for the entire 21st century
    and correlate it with VIX to assess information content.

Methodology:
    - STRICT COMPLIANCE with METHODOLOGY_REFERENCE.md
    - Standard Parameters: W=500 (Rolling Variance), P=250 (Trend Window)
    - Assets: Standard US Basket (^GSPC, ^DJI, ^IXIC, ^RUT)
    - Statistic: Kendall-Tau of L^2 Norm Variance

Output:
    - outputs/phase_10/continuous_signal_2000_2025.csv (Date, Tau, VIX)
    - outputs/phase_10/signal_correlation_report.txt
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import kendalltau, pearsonr, spearmanr
from financial_tda.validation.gidea_katz_replication import fetch_historical_data, compute_persistence_landscape_norms
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

# CONSTANTS
START_DATE = "1999-01-01"  # Start earlier to have buffer for W=500
END_DATE = "2025-12-31"
OUTPUT_DIR = "outputs/phase_10"
NORM_FILE = f"{OUTPUT_DIR}/lp_norms_2000_2025.csv"
SIGNAL_FILE = f"{OUTPUT_DIR}/continuous_signal_2000_2025.csv"
REPORT_FILE = f"{OUTPUT_DIR}/signal_correlation_report.txt"

# STRICT PARAMETERS
W = 500  # Rolling Variance Window
P = 250  # Trend Warning Window


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_vix():
    print("Fetching VIX data...")
    vix = yf.download("^VIX", start=START_DATE, end=END_DATE, progress=False)
    print(f"DEBUG: Raw VIX Shape: {vix.shape}")
    print(f"DEBUG: Raw VIX Columns: {vix.columns}")
    if vix.empty:
        print("CRITICAL: VIX download results in empty DataFrame.")

    if "Close" in vix.columns:
        vix = vix["Close"]
    else:
        # Fallback for some yfinance versions that might return different structure
        print("WARNING: 'Close' column not found, attempting iloc")
        vix = vix.iloc[:, 0]

    # Handle multi-level column if necessary
    if isinstance(vix, pd.DataFrame):
        vix = vix.iloc[:, 0]

    return vix


def run_analysis():
    ensure_dirs()
    print("=" * 80)
    print("PHASE 10.1: CONTINUOUS SIGNAL ANALYSIS (2000-2025)")
    print(f"Parameters: W={W}, P={P} (STRICT)")
    print("=" * 80)

    # 1. TDA Pipeline
    if os.path.exists(NORM_FILE):
        print(f"Loading existing norms from {NORM_FILE}...")
        norms_df = pd.read_csv(NORM_FILE, index_col=0, parse_dates=True)
    else:
        print(f"Fetching market data ({START_DATE} to {END_DATE})...")
        prices_dict = fetch_historical_data(START_DATE, END_DATE)

        print("Computing Persistence Landscapes and L^p Norms...")
        # Point Cloud Window = 50 (Standard)
        norms_df = compute_persistence_landscape_norms(prices=prices_dict, window_size=50, stride=1, n_layers=5)
        norms_df.to_csv(NORM_FILE)
        print(f"Saved norms to {NORM_FILE}")

    # 2. Compute Rolling Variance (Signal magnitude)
    print(f"Computing Rolling Statistics (W={W})...")
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=W)

    # 3. Compute Continuous Kendall-Tau
    print(f"Computing Continuous Kendall-Tau (P={P})...")

    # We want Tau for every possible day
    results = []
    dates = []

    # The first valid index for Tau is at W + P
    # But stats_df already accounts for W (it has NaNs for first W rows)
    # So we strictly iterate from index P in stats_df (where previous P rows are valid)

    # Check metric availability
    metric_col = "L2_norm_variance"
    if metric_col not in stats_df.columns:
        raise ValueError(f"Metric {metric_col} not found in rolling stats.")

    # Pre-compute valid mask to speed up
    y_full = stats_df[metric_col].values
    valid_mask_full = ~np.isnan(y_full)

    dates_full = stats_df.index
    n_days = len(dates_full)

    print(f"Total days: {n_days}. Estimating computation time...")

    for i in range(P, n_days):
        if i % 1000 == 0:
            print(f"Processing day {i}/{n_days} ({dates_full[i].date()})...")

        # Window: [i-P, i] (inclusive of i, length P+1 if we follow slicing,
        # but G&K usually imply analyzing previous P days)
        # We will use P window size ending at i (inclusive)

        # Slice: start=i-P+1, end=i+1 (python slice is exclusive at end)
        # This gives exactly P points
        window_y = y_full[i - P + 1 : i + 1]

        # Check validity
        if len(window_y) < P:
            continue

        # Check NaNs in window
        # (Since we start after W, ideally they are valid, but check just in case)
        if np.isnan(window_y).any():
            # If too many NaNs, skip
            if np.isnan(window_y).sum() > P * 0.1:
                continue

        # Compute Tau
        # x is just time index 0..P-1
        x = np.arange(len(window_y))

        try:
            tau, p_val = kendalltau(x, window_y, nan_policy="omit")
            if not np.isnan(tau):
                results.append(tau)
                dates.append(dates_full[i])
        except Exception:
            pass

    # 4. Compile Results
    tau_df = pd.DataFrame({"Tau": results}, index=dates)

    # 5. Integrate VIX
    vix_series = fetch_vix()

    # Align Data
    print(f"DEBUG: Tau Data Range: {tau_df.index.min()} to {tau_df.index.max()} (N={len(tau_df)})")

    # Normalize to midnight to ensure matching
    tau_df.index = tau_df.index.normalize()
    if not vix_series.empty:
        vix_series.index = vix_series.index.normalize()

    # Join Tau and VIX
    full_df = tau_df.join(vix_series, how="inner")

    full_df.columns = ["Tau", "VIX"]
    print(f"DEBUG: Combined Data (Tau + VIX) Count: {len(full_df)}")

    if len(full_df) < 10:
        print("CRITICAL ERROR: Not enough overlapping data between Tau and VIX.")
        print("Possible causes: Date mismatch, timezone issues, or missing VIX data.")
        return

    # Add rolling VIX correlation for stability analysis later
    full_df["Rolling_Corr_2y"] = full_df["Tau"].rolling(500).corr(full_df["VIX"])

    print(f"Saving combined signal data to {SIGNAL_FILE}...")
    full_df.to_csv(SIGNAL_FILE)

    # 6. Analysis and Reporting
    # Compute overall correlations
    pearson_r, _ = pearsonr(full_df["Tau"], full_df["VIX"])
    spearman_r, _ = spearmanr(full_df["Tau"], full_df["VIX"])

    report = []
    report.append("PHASE 10.1 SIGNAL ANALYSIS REPORT")
    report.append("=================================")
    report.append(f"Period: {full_df.index.min().date()} to {full_df.index.max().date()}")
    report.append(f"Count: {len(full_df)} trading days")
    report.append("")
    report.append("OVERALL CORRELATION (Tau vs VIX)")
    report.append(f"Pearson r:  {pearson_r:.4f}")
    report.append(f"Spearman r: {spearman_r:.4f}")
    report.append("")
    report.append("INTERPRETATION:")
    if pearson_r > 0.8:
        report.append(">> CRITICAL: High correlation (>0.8) suggests Tau is largely measuring Volatility.")
    elif pearson_r > 0.5:
        report.append(">> WARNING: Moderate correlation (0.5-0.8). Tau has significant overlap with Volatility.")
    else:
        report.append(">> POSITIVE: Low correlation (<0.5). Tau contains unique information.")

    report.append("")
    report.append("REGIME STABILITY")
    # Split into 3 eras as requested
    eras = [
        ("2000-2008 (Pre-GFC)", "2000-01-01", "2008-01-01"),
        ("2008-2016 (GFC & Post)", "2008-01-01", "2016-01-01"),
        ("2016-2024 (Modern/COVID)", "2016-01-01", "2024-12-31"),
    ]

    for name, start, end in eras:
        sub_df = full_df[start:end]
        if len(sub_df) > 100:
            r, _ = pearsonr(sub_df["Tau"], sub_df["VIX"])
            report.append(f"{name}: r = {r:.4f} (N={len(sub_df)})")
        else:
            report.append(f"{name}: Insufficient Data (N={len(sub_df)})")

    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(report))

    print("\nanalysis Complete.")
    print("\n".join(report))


if __name__ == "__main__":
    run_analysis()
