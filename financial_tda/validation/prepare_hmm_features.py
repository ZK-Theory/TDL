"""
Phase 10B - Task B.1: HMM Feature Preparation
==============================================

Purpose:
    Prepare feature matrix for HMM regime detection models.

Input:
    outputs/phase_10/continuous_signal_2000_2025.csv
    S&P 500 returns (via yfinance)

Output:
    outputs/phase_10b/hmm_features.csv

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
import yfinance as yf
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
TAU_FILE = BASE_DIR / "outputs" / "phase_10" / "continuous_signal_2000_2025.csv"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b"
OUTPUT_FILE = OUTPUT_DIR / "hmm_features.csv"


def load_tau_series():
    """Load the continuous τ series from Phase 10."""
    print(f"Loading τ series from: {TAU_FILE}")
    df = pd.read_csv(TAU_FILE, index_col=0, parse_dates=True)
    print(f"  Loaded {len(df)} days")
    return df


def fetch_market_data(start_date, end_date):
    """Fetch S&P 500 and VIX data."""
    print(f"Fetching market data from {start_date} to {end_date}...")

    # Fetch S&P 500
    spx = yf.download("^GSPC", start=start_date, end=end_date, progress=False)
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)

    # Fetch VIX
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)

    print(f"  SPX: {len(spx)} days, VIX: {len(vix)} days")

    return spx, vix


def create_features(tau_df, spx, vix):
    """Create feature matrix for HMM."""
    print("Creating feature matrix...")

    # Compute returns
    spx_close = spx["Close"]
    returns_1d = spx_close.pct_change()
    returns_5d = spx_close.pct_change(periods=5)
    returns_21d = spx_close.pct_change(periods=21)

    # VIX features
    vix_level = vix["Close"]
    vix_5d_change = vix_level.pct_change(periods=5)

    # Combine into DataFrame
    features = pd.DataFrame(index=tau_df.index)

    # Map market data to τ dates
    features["ret_1d"] = returns_1d.reindex(features.index, method="ffill")
    features["ret_5d"] = returns_5d.reindex(features.index, method="ffill")
    features["ret_21d"] = returns_21d.reindex(features.index, method="ffill")
    features["vix"] = vix_level.reindex(features.index, method="ffill")
    features["vix_5d_chg"] = vix_5d_change.reindex(features.index, method="ffill")
    features["tau"] = tau_df["Tau"]

    # Drop NaN rows
    features_clean = features.dropna()
    print(f"  Created {len(features_clean)} feature rows ({len(features_clean.columns)} features)")
    print(f"  Features: {list(features_clean.columns)}")

    return features_clean


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK B.1: HMM FEATURE PREPARATION")
    print("=" * 60)

    # Load τ series
    tau_df = load_tau_series()

    # Fetch market data
    start_date = tau_df.index.min()
    end_date = tau_df.index.max()
    spx, vix = fetch_market_data(start_date, end_date)

    # Create features
    features = create_features(tau_df, spx, vix)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT_FILE)
    print(f"\nSaved features to: {OUTPUT_FILE}")

    # Summary stats
    print("\nFeature Statistics:")
    print(features.describe())

    print("\n" + "=" * 60)
    print("TASK B.1 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
