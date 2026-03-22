"""
Phase 10 Remediation - Parts 1 & 2: Continuous τ Time Series
=============================================================

Purpose:
    Generate continuous τ series for ALL 6 G&K metrics from 2002-2025.
    This is the foundational data for complete analysis.

Statistics:
    1. L1_norm_variance
    2. L2_norm_variance
    3. L1_norm_spectral_density_low
    4. L2_norm_spectral_density_low
    5. L1_norm_acf_lag1
    6. L2_norm_acf_lag1

Output:
    outputs/foundation/gk_all_statistics.csv - Rolling statistics time series
    outputs/foundation/continuous_tau_all_metrics.csv - Daily τ for all 6 metrics

Author: Phase 10 Remediation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from scipy.stats import kendalltau
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# Import existing pipeline
from financial_tda.validation.gidea_katz_replication import compute_rolling_statistics

# ============================================================================
# CONFIGURATION (FIXED - NO TUNING)
# ============================================================================
W = 500  # Rolling window
P = 250  # Trend window
POINT_CLOUD_WINDOW = 50

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "foundation"
NORMS_CACHE = BASE_DIR / "outputs" / "phase_10c_complete" / "norms_cache_complete.csv"

# Statistics columns to process
STAT_COLUMNS = [
    "L1_norm_variance",
    "L2_norm_variance",
    "L1_norm_spectral_density_low",
    "L2_norm_spectral_density_low",
    "L1_norm_acf_lag1",
    "L2_norm_acf_lag1",
]

# Threshold for consensus
TAU_THRESHOLD = 0.5


def ensure_dirs():
    """Create output directories."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def load_norms():
    """Load cached norms from Phase 10C."""
    if not NORMS_CACHE.exists():
        raise FileNotFoundError(f"Norms cache not found: {NORMS_CACHE}")

    print(f"Loading norms from: {NORMS_CACHE}")
    norms_df = pd.read_csv(NORMS_CACHE, index_col=0, parse_dates=True)

    # Ensure index is DatetimeIndex first
    if not isinstance(norms_df.index, pd.DatetimeIndex):
        norms_df.index = pd.to_datetime(norms_df.index)

    # Remove timezone if present
    if norms_df.index.tz is not None:
        norms_df.index = norms_df.index.tz_localize(None)

    print(f"  Loaded {len(norms_df)} days ({norms_df.index[0].date()} to {norms_df.index[-1].date()})")
    return norms_df


def compute_rolling_tau(stats_df, stat_col, window=P):
    """Compute rolling Kendall-tau for a single statistic."""
    n = len(stats_df)
    tau_values = np.full(n, np.nan)
    p_values = np.full(n, np.nan)

    for i in range(window, n):
        segment = stats_df[stat_col].iloc[i - window : i]

        # Skip if too many NaNs
        valid_count = (~segment.isna()).sum()
        if valid_count < window * 0.5:
            continue

        # Compute Kendall-tau
        x = np.arange(len(segment))
        try:
            tau, p_val = kendalltau(x, segment.values, nan_policy="omit")
            tau_values[i] = tau
            p_values[i] = p_val
        except:
            continue

    return tau_values, p_values


def compute_all_continuous_tau(stats_df):
    """Compute continuous τ for all 6 statistics."""
    print("\nComputing continuous τ for all statistics...")

    results = pd.DataFrame(index=stats_df.index)
    results.index.name = "Date"

    for stat_col in STAT_COLUMNS:
        if stat_col not in stats_df.columns:
            print(f"  Warning: {stat_col} not in stats_df")
            continue

        print(f"  Processing {stat_col}...")
        tau_values, p_values = compute_rolling_tau(stats_df, stat_col)

        # Short column name
        short_name = stat_col.replace("_norm_", "_").replace("spectral_density_low", "spec").replace("variance", "var")
        results[f"{short_name}_tau"] = tau_values
        results[f"{short_name}_p"] = p_values

    # Compute consensus count (number of metrics with |τ| > threshold)
    tau_cols = [c for c in results.columns if c.endswith("_tau")]
    results["consensus_count"] = (np.abs(results[tau_cols]) > TAU_THRESHOLD).sum(axis=1)

    # Compute average absolute τ
    results["avg_abs_tau"] = np.abs(results[tau_cols]).mean(axis=1)

    # Drop rows with all NaN τ
    valid_mask = results[tau_cols].notna().any(axis=1)
    results = results[valid_mask]

    print(f"  Generated {len(results)} days with valid τ")
    return results


def save_outputs(stats_df, tau_df):
    """Save output files."""
    # Save rolling statistics
    stats_file = OUTPUT_DIR / "gk_all_statistics.csv"
    stats_df.to_csv(stats_file)
    print(f"\nSaved statistics to: {stats_file}")

    # Save continuous τ
    tau_file = OUTPUT_DIR / "continuous_tau_all_metrics.csv"
    tau_df.to_csv(tau_file)
    print(f"Saved continuous τ to: {tau_file}")


def print_summary(tau_df):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("CONTINUOUS τ SUMMARY")
    print("=" * 70)

    tau_cols = [c for c in tau_df.columns if c.endswith("_tau")]

    print("\nMean τ for each statistic:")
    for col in tau_cols:
        mean_tau = tau_df[col].mean()
        std_tau = tau_df[col].std()
        print(f"  {col:20s}: {mean_tau:+.3f} ± {std_tau:.3f}")

    print("\nConsensus distribution:")
    consensus_counts = tau_df["consensus_count"].value_counts().sort_index()
    for count, n_days in consensus_counts.items():
        pct = n_days / len(tau_df) * 100
        print(f"  {int(count)}/6 metrics: {n_days:5d} days ({pct:.1f}%)")

    # High consensus days (4+)
    high_consensus = tau_df[tau_df["consensus_count"] >= 4]
    print(f"\nHigh consensus days (≥4/6): {len(high_consensus)} ({len(high_consensus)/len(tau_df)*100:.1f}%)")

    if len(high_consensus) > 0:
        print("\nSample high-consensus periods:")
        for idx in high_consensus.head(10).index:
            row = high_consensus.loc[idx]
            print(f"  {idx.date()}: consensus={int(row['consensus_count'])}, avg|τ|={row['avg_abs_tau']:.2f}")


def main():
    """Main execution."""
    print("=" * 70)
    print("PHASE 10 REMEDIATION - CONTINUOUS τ TIME SERIES")
    print("=" * 70)
    print(f"Parameters: W={W}, P={P} (FIXED)")
    print(f"Threshold for consensus: |τ| > {TAU_THRESHOLD}")
    print("")

    ensure_dirs()

    # Load cached norms
    norms_df = load_norms()

    # Compute rolling statistics
    print("\nComputing rolling statistics...")
    stats_df = compute_rolling_statistics(norms_df, window_size=W)

    # Compute continuous τ for all metrics
    tau_df = compute_all_continuous_tau(stats_df)

    # Save outputs
    save_outputs(stats_df, tau_df)

    # Print summary
    print_summary(tau_df)

    print("\n" + "=" * 70)
    print("PARTS 1 & 2 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
