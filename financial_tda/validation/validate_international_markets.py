"""
International Market Validation
===============================
Validates the TDA crisis detection methodology on a basket of non-US indices:
- ^FTSE (FTSE 100 - UK)
- ^GDAXI (DAX - Germany)
- ^FCHI (CAC 40 - France)
- ^N225 (Nikkei 225 - Japan)

Goals:
1. 2008 GFC: Confirm systemic detection (Universal Law check).
2. 2023-2025: Check for false positives (Robustness check).
"""

import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import kendalltau
from financial_tda.validation.gidea_katz_replication import (
    compute_persistence_landscape_norms,
    compute_rolling_statistics,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def fetch_international_data(start_date: str, end_date: str) -> dict[str, pd.Series]:
    """Fetch international indices."""
    tickers = {"FTSE": "^FTSE", "DAX": "^GDAXI", "CAC": "^FCHI", "Nikkei": "^N225"}

    prices = {}
    logger.info(f"Fetching international data ({start_date} to {end_date})...")

    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if not data.empty:
                # Handle MultiIndex columns if present (yfinance v0.2+)
                if isinstance(data.columns, pd.MultiIndex):
                    prices[name] = data["Close"][ticker]
                else:
                    prices[name] = data["Close"]
                logger.info(f"Fetched {name}: {len(prices[name])} records")
            else:
                logger.warning(f"No data for {name} ({ticker})")
        except Exception as e:
            logger.error(f"Error fetching {name}: {e}")

    return prices


def run_analysis(prices, label, crash_date=None, pre_crisis_window=250):
    """Run TDA pipeline and return stats."""

    # 1. Compute Norms
    logger.info(f"[{label}] Computing L^p Norms...")
    norms_df = compute_persistence_landscape_norms(prices=prices, window_size=50, stride=1, n_layers=5)

    # 2. Compute Rolling Statistics
    logger.info(f"[{label}] Computing Rolling Statistics (500 days)...")
    stats_df = compute_rolling_statistics(norms_df, window_size=500)

    # 3. Analyze Trends
    results = {}

    if crash_date:
        # Retrospective Analysis (e.g., 2008)
        logger.info(f"[{label}] analyzing pre-crash trend before {crash_date}...")
        results["type"] = "retrospective"

        # Ensure timezone compatibility
        if stats_df.index.tz is not None and crash_date.tz is None:
            crash_date_tz = crash_date.tz_localize(stats_df.index.tz)
        else:
            crash_date_tz = crash_date

        pre_crash_mask = stats_df.index < crash_date_tz
        window_data = stats_df[pre_crash_mask].tail(pre_crisis_window)

        metrics = [
            "L1_norm_variance",
            "L2_norm_variance",
            "L1_norm_spectral_density_low",
            "L2_norm_spectral_density_low",
        ]

        row = {}
        for metric in metrics:
            if metric in window_data.columns:
                series = window_data[metric].dropna()
                if len(series) > 10:
                    tau, p = kendalltau(np.arange(len(series)), series.values)
                    row[metric] = tau
        results["metrics"] = row

    else:
        # Prospective Analysis (e.g., 2023-2025)
        logger.info(f"[{label}] Analyzing full period for false positives...")
        results["type"] = "prospective"

        metrics = [
            "L1_norm_variance",
            "L2_norm_variance",
            "L1_norm_spectral_density_low",
            "L2_norm_spectral_density_low",
        ]

        daily_max_taus = []
        false_positives = 0
        elevated_risk = 0

        # Iterate daily (simulating real-time)
        # Start after enough data
        start_idx = 0  # compute_rolling_statistics already handles NaNs at start

        # We need to compute Kendall Tau on a rolling basis
        # This is computationally expensive for every day, so we'll do it for the existing stats_df
        # using the trailing 'pre_crisis_window'

        valid_indices = range(pre_crisis_window, len(stats_df))

        processed_count = 0
        for i in valid_indices:
            window_data = stats_df.iloc[i - pre_crisis_window : i]
            current_date = stats_df.index[i]

            day_max_tau = -1.0

            for metric in metrics:
                if metric not in window_data.columns:
                    continue
                y = window_data[metric].values
                if np.isnan(y).any():
                    continue  # Skip windows with NaNs

                tau, _ = kendalltau(np.arange(len(y)), y)
                if tau > day_max_tau:
                    day_max_tau = tau

            if day_max_tau > -1.0:
                daily_max_taus.append(day_max_tau)
                if day_max_tau >= 0.70:
                    false_positives += 1
                if day_max_tau >= 0.60:
                    elevated_risk += 1

            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count} days...")

        results["false_positives"] = false_positives
        results["elevated_risk"] = elevated_risk
        results["max_tau_observed"] = max(daily_max_taus) if daily_max_taus else 0.0
        results["days_analyzed"] = processed_count

    return results


def main():
    os.makedirs("outputs", exist_ok=True)

    # ---------------------------------------------------------
    # 1. Validation 1: 2008 Global Financial Crisis (Confirmation)
    # ---------------------------------------------------------
    start_2008 = "2006-01-01"
    end_2008 = "2010-12-31"
    prices_2008 = fetch_international_data(start_2008, end_2008)

    if len(prices_2008) == 4:
        res_2008 = run_analysis(
            prices_2008, "2008_GFC_International", crash_date=pd.Timestamp("2008-09-15"), pre_crisis_window=250
        )
        logger.info("\n" + "=" * 50)
        logger.info("2008 GFC INTERNATIONAL RESULTS")
        logger.info(res_2008)
        logger.info("=" * 50 + "\n")

        # Save simple report
        with open("outputs/international_vals_2008.txt", "w") as f:
            f.write(str(res_2008))
    else:
        logger.error("Failed to fetch all 2008 data")

    # ---------------------------------------------------------
    # 2. Validation 2: 2023-2025 (False Positives)
    # ---------------------------------------------------------
    start_curr = "2022-01-01"  # Need burn-in
    end_curr = "2025-11-30"
    prices_curr = fetch_international_data(start_curr, end_curr)

    if len(prices_curr) == 4:
        res_curr = run_analysis(
            prices_curr,
            "2023_2025_International_FalsePos",
            crash_date=None,  # Prospective
            pre_crisis_window=250,
        )
        logger.info("\n" + "=" * 50)
        logger.info("2023-2025 INTERNATIONAL FALSE POSITIVE CHECK")
        logger.info(res_curr)
        logger.info("=" * 50 + "\n")

        with open("outputs/international_vals_2023_2025.txt", "w") as f:
            f.write(str(res_curr))


if __name__ == "__main__":
    main()
