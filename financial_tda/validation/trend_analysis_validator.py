"""
Trend Analysis Validator for Financial TDA - Gidea & Katz (2018) Methodology.

This module provides improved, reusable interfaces for the complete G&K trend detection
methodology, extracted and refactored from gidea_katz_replication.py for easier
application to multiple crisis events.

COMPLETE G&K METHODOLOGY (as validated with τ=0.814):
1. Compute L^p norms of persistence landscapes from sliding windows
2. Compute ROLLING STATISTICS over 500-day windows:
   - Variance (captures volatility changes)
   - Spectral density at low frequencies (PRIMARY METRIC - best performer)
   - Autocorrelation lag-1 (captures memory effects)
3. Analyze Kendall-tau correlation on 250-day pre-crisis windows
4. Success criteria: τ ≥ 0.70 (G&K achieved τ ≈ 0.89-1.00 for spectral density)

Key Improvements Over gidea_katz_replication.py:
- Modular functions for reuse across multiple events
- Cleaner API for applying full G&K methodology
- Better error handling and validation
- Maintains COMPLETE methodology (spectral density, variance, ACF)

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import signal
from scipy.stats import kendalltau

logger = logging.getLogger(__name__)


def compute_gk_rolling_statistics(
    norms_df: pd.DataFrame,
    window_size: int = 500,
) -> pd.DataFrame:
    """
    Compute rolling statistics over L^p norm time series (G&K methodology).

    This is the KEY transformation that makes G&K's approach work. Raw L^p norms
    show weak trends (τ ≈ 0.3), but rolling statistics amplify signals significantly
    (τ ≈ 0.8-1.0 for spectral density).

    Per G&K paper Section 3.2:
    - 500-day rolling window for statistical estimation
    - Variance (captures increasing volatility before crashes)
    - Average spectral density at low frequencies (PRIMARY METRIC)
    - ACF lag-1 (autocorrelation, captures persistence)

    Args:
        norms_df: DataFrame with DatetimeIndex and columns: L1_norm, L2_norm.
        window_size: Rolling window size in days (default: 500 per G&K).

    Returns:
        DataFrame with rolling statistics columns:
            - L1_norm_variance, L2_norm_variance
            - L1_norm_spectral_density_low, L2_norm_spectral_density_low
            - L1_norm_acf_lag1, L2_norm_acf_lag1

    Examples:
        >>> norms_df = pd.DataFrame({
        ...     'L1_norm': np.random.randn(1000),
        ...     'L2_norm': np.random.randn(1000)
        ... }, index=pd.date_range('2006-01-01', periods=1000))
        >>> stats_df = compute_gk_rolling_statistics(norms_df, window_size=500)
        >>> print(stats_df.columns)  # Shows variance, spectral_density, acf columns
    """
    logger.info(f"Computing G&K rolling statistics (window={window_size} days)...")

    if not isinstance(norms_df.index, pd.DatetimeIndex):
        # Try to convert to DatetimeIndex
        try:
            norms_df = norms_df.copy()
            # Remove timezone first if present
            if hasattr(norms_df.index, "tz") and norms_df.index.tz is not None:
                norms_df.index = norms_df.index.tz_localize(None)
            else:
                norms_df.index = pd.to_datetime(norms_df.index, utc=True).tz_localize(None)
        except Exception as e:
            raise ValueError(f"norms_df must have a DatetimeIndex or convertible index: {e}")

    required_cols = ["L1_norm", "L2_norm"]
    missing = set(required_cols) - set(norms_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    results = pd.DataFrame(index=norms_df.index)

    for norm_col in ["L1_norm", "L2_norm"]:
        # 1. Variance (simple but effective)
        results[f"{norm_col}_variance"] = norms_df[norm_col].rolling(window=window_size).var()

        # 2. ACF lag-1 (autocorrelation)
        def acf_lag1(x):
            if len(x) < 2:
                return np.nan
            try:
                return np.corrcoef(x[:-1], x[1:])[0, 1]
            except:
                return np.nan

        results[f"{norm_col}_acf_lag1"] = norms_df[norm_col].rolling(window=window_size).apply(acf_lag1, raw=True)

        # 3. Average spectral density at low frequencies (PRIMARY METRIC)
        # This is what achieved τ=0.814 in G&K replication
        def avg_spectral_density_low_freq(x):
            if len(x) < 10:
                return np.nan
            try:
                # Compute periodogram (power spectral density estimate)
                freqs, psd = signal.periodogram(x, detrend="constant")
                # Low frequencies: first 10% of spectrum (captures long-term trends)
                low_freq_mask = freqs <= freqs.max() * 0.1
                if low_freq_mask.sum() == 0:
                    return np.nan
                return psd[low_freq_mask].mean()
            except:
                return np.nan

        results[f"{norm_col}_spectral_density_low"] = (
            norms_df[norm_col].rolling(window=window_size).apply(avg_spectral_density_low_freq, raw=True)
        )

    logger.info(f"Computed {len(results.columns)} rolling statistics")
    return results


def analyze_gk_precrash_trend(
    stats_df: pd.DataFrame,
    crisis_date: str | pd.Timestamp,
    days_before: int = 250,
    tau_threshold: float = 0.70,
) -> dict[str, Any]:
    """
    Analyze Kendall-tau trends in rolling statistics for pre-crash window (G&K methodology).

    This implements G&K's trend analysis: compute Kendall-tau correlation coefficient
    to measure monotonic trends in the 250 days before crash.

    Expected results (from G&K paper Table 1):
    - 2000 dotcom crash: τ ≈ 0.89 (spectral density)
    - 2008 Lehman crisis: τ ≈ 1.00 (spectral density)

    Args:
        stats_df: DataFrame with rolling statistics (from compute_gk_rolling_statistics).
        crisis_date: Crisis date (string YYYY-MM-DD or Timestamp).
        days_before: Number of trading days before crash (default: 250 per G&K).
        tau_threshold: Success threshold (default: 0.70).

    Returns:
        Dictionary with structure:
            {
                'crisis_date': crisis date,
                'window_start': start date of analysis window,
                'window_end': end date of analysis window,
                'n_observations': number of days analyzed,
                'statistics': {
                    'L1_norm_variance': {'tau': float, 'p_value': float, 'n_samples': int},
                    'L2_norm_spectral_density_low': {'tau': float, 'p_value': float, ...},
                    ...  # all 6 statistics
                },
                'best_metric': name of metric with highest |tau|,
                'best_tau': highest |tau| value,
                'status': 'PASS' if best_tau >= tau_threshold else 'FAIL'
            }

    Examples:
        >>> stats_df = compute_gk_rolling_statistics(norms_df)
        >>> result = analyze_gk_precrash_trend(stats_df, '2008-09-15')
        >>> print(f"Spectral density τ: {result['statistics']['L2_norm_spectral_density_low']['tau']:.3f}")
    """
    logger.info(f"\nAnalyzing G&K pre-crash trend ({days_before} days before {crisis_date})...")

    # Parse crisis date
    if isinstance(crisis_date, str):
        crisis_date = pd.to_datetime(crisis_date)

    # Handle timezone compatibility
    if stats_df.index.tz is not None and crisis_date.tz is None:
        crisis_date = crisis_date.tz_localize(stats_df.index.tz)
    elif stats_df.index.tz is None and crisis_date.tz is not None:
        crisis_date = crisis_date.tz_localize(None)

    # Extract pre-crash window
    pre_crash_mask = stats_df.index < crisis_date
    pre_crash_data = stats_df[pre_crash_mask].tail(days_before)

    if len(pre_crash_data) < days_before:
        logger.warning(f"Only {len(pre_crash_data)} days available before crash (requested {days_before})")

    # Compute Kendall-tau for each statistic
    time_index = np.arange(len(pre_crash_data))
    statistics_results = {}
    best_tau = 0.0
    best_metric = None

    for col in stats_df.columns:
        if col not in pre_crash_data.columns:
            continue

        series = pre_crash_data[col].dropna()
        if len(series) < 10:
            statistics_results[col] = {
                "tau": np.nan,
                "p_value": np.nan,
                "n_samples": len(series),
            }
            continue

        # Kendall-tau correlation with time indices
        tau, p_value = kendalltau(time_index[: len(series)], series.values)
        statistics_results[col] = {
            "tau": float(tau),
            "p_value": float(p_value),
            "n_samples": len(series),
        }

        logger.info(f"  {col}: τ={tau:.4f}, p={p_value:.4e}, n={len(series)}")

        # Track best metric
        if abs(tau) > abs(best_tau):
            best_tau = tau
            best_metric = col

    # Determine status
    status = "PASS" if abs(best_tau) >= tau_threshold else "FAIL"

    result = {
        "crisis_date": str(crisis_date.date()) if hasattr(crisis_date, "date") else str(crisis_date),
        "window_start": str(pre_crash_data.index[0].date()) if len(pre_crash_data) > 0 else None,
        "window_end": str(pre_crash_data.index[-1].date()) if len(pre_crash_data) > 0 else None,
        "n_observations": len(pre_crash_data),
        "days_requested": days_before,
        "statistics": statistics_results,
        "best_metric": best_metric,
        "best_tau": float(best_tau),
        "tau_threshold": tau_threshold,
        "status": status,
    }

    logger.info(f"\nBest metric: {best_metric} (τ={best_tau:.4f})")
    logger.info(f"Status: {status} (threshold: τ ≥ {tau_threshold})")

    return result


def validate_gk_event(
    norms_df: pd.DataFrame,
    event_name: str,
    crisis_date: str,
    rolling_window: int = 500,
    precrash_window: int = 250,
    tau_threshold: float = 0.70,
) -> dict[str, Any]:
    """
    Complete G&K validation workflow for a single crisis event.

    Convenience function that runs the full pipeline:
    1. Compute rolling statistics (500-day windows)
    2. Analyze pre-crash trends (250-day window)
    3. Return comprehensive results

    Args:
        norms_df: DataFrame with L1_norm and L2_norm columns.
        event_name: Human-readable event name (e.g., "2008 GFC").
        crisis_date: Crisis date in YYYY-MM-DD format.
        rolling_window: Window for rolling statistics (default: 500).
        precrash_window: Window for trend analysis (default: 250).
        tau_threshold: Success threshold (default: 0.70).

    Returns:
        Dictionary with complete validation results including statistics and trends.

    Examples:
        >>> from financial_tda.validation.gidea_katz_replication import compute_persistence_landscape_norms
        >>> norms_df = compute_persistence_landscape_norms(prices)
        >>> result = validate_gk_event(norms_df, "2008 GFC", "2008-09-15")
        >>> print(result['status'])  # 'PASS' or 'FAIL'
    """
    logger.info(f"\n{'=' * 70}")
    logger.info(f"G&K Validation: {event_name}")
    logger.info(f"Crisis Date: {crisis_date}")
    logger.info(f"{'=' * 70}")

    # Step 1: Compute rolling statistics
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=rolling_window)

    # Step 2: Analyze pre-crash trends
    trend_result = analyze_gk_precrash_trend(
        stats_df,
        crisis_date=crisis_date,
        days_before=precrash_window,
        tau_threshold=tau_threshold,
    )

    # Combine results
    result = {
        "event_name": event_name,
        "rolling_window_size": rolling_window,
        "precrash_window_size": precrash_window,
        **trend_result,
    }

    return result


def load_lp_norms_from_csv(norms_file: Path | str) -> pd.DataFrame:
    """
    Load pre-computed L^p norms from CSV file.

    Args:
        norms_file: Path to CSV file with L1_norm and L2_norm columns.

    Returns:
        DataFrame with DatetimeIndex and L1_norm, L2_norm columns.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If required columns are missing.
    """
    norms_file = Path(norms_file)

    if not norms_file.exists():
        raise FileNotFoundError(f"Norms file not found: {norms_file}")

    logger.info(f"Loading L^p norms from: {norms_file}")

    norms_df = pd.read_csv(norms_file, index_col=0, parse_dates=True)

    required_columns = ["L1_norm", "L2_norm"]
    missing = set(required_columns) - set(norms_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    logger.info(f"Loaded {len(norms_df)} observations")

    return norms_df
