"""
FRED (Federal Reserve Economic Data) fetcher for macroeconomic indicators.

This module provides functions to fetch economic time series data from the
Federal Reserve Bank of St. Louis FRED database. Supports single series,
multiple series, and convenience functions for common macroeconomic indicators.

Requires FRED API key via environment variable FRED_API_KEY or function parameter.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import pandas as pd
from fredapi import Fred

logger = logging.getLogger(__name__)

# Required macroeconomic series for financial TDA analysis
MACRO_SERIES = {
    "VIXCLS": "VIX Volatility Index",
    "DGS10": "10-Year Treasury Yield",
    "DGS2": "2-Year Treasury Yield",
    "T10Y2Y": "10Y-2Y Yield Spread",
    "UNRATE": "Unemployment Rate",
    "FEDFUNDS": "Federal Funds Rate",
}

# FRED API rate limit: 120 requests/minute
RATE_LIMIT_DELAY = 0.5  # 500ms between requests = 120/min


def get_fred_client(api_key: str | None = None) -> Fred:
    """
    Get configured FRED API client.

    API key is loaded from environment variable FRED_API_KEY if not provided.
    Set up your API key at: https://fred.stlouisfed.org/docs/api/api_key.html

    Args:
        api_key: FRED API key. If None, reads from FRED_API_KEY env variable.

    Returns:
        Configured fredapi.Fred client instance.

    Raises:
        ValueError: If API key not provided and FRED_API_KEY env var not set.

    Examples:
        >>> client = get_fred_client()  # Uses FRED_API_KEY env var
        >>> client = get_fred_client("your-api-key")  # Explicit key
    """
    if api_key is None:
        api_key = os.environ.get("FRED_API_KEY")

    if not api_key:
        raise ValueError(
            "FRED API key not found. Set FRED_API_KEY environment variable "
            "or pass api_key parameter. "
            "Get your key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    return Fred(api_key=api_key)


def fetch_series(
    series_id: str,
    start_date: str,
    end_date: str,
    *,
    api_key: str | None = None,
    max_retries: int = 5,
    base_delay: int = 60,
) -> pd.Series:
    """
    Fetch single FRED time series.

    Implements exponential backoff retry logic for network errors and rate limits.
    Returns data with datetime index and series values.

    Args:
        series_id: FRED series identifier (e.g., 'VIXCLS', 'DGS10').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        api_key: FRED API key. If None, uses FRED_API_KEY env variable.
        max_retries: Maximum retry attempts for transient errors (default: 5).
        base_delay: Base delay in seconds for exponential backoff (default: 60).

    Returns:
        Series with datetime index and values for the requested period.
        Returns empty Series if no data available.

    Raises:
        ValueError: If API key not configured or series_id invalid.

    Examples:
        >>> vix = fetch_series('VIXCLS', '2020-01-01', '2021-01-01')
        >>> print(vix.name)
        VIXCLS
    """
    client = get_fred_client(api_key)

    for attempt in range(max_retries):
        try:
            series = client.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date,
            )

            if series.empty:
                logger.warning(
                    f"No data returned for series {series_id} "
                    f"from {start_date} to {end_date}"
                )
                return pd.Series(dtype=float)

            series.name = series_id
            logger.info(f"Fetched {len(series)} observations for {series_id}")
            return series

        except ValueError as e:
            # Invalid series ID or API key - not retryable
            logger.error(f"Invalid series ID or API key: {series_id}")
            raise ValueError(f"Failed to fetch series {series_id}: {e}") from e

        except Exception as e:
            # Network errors, rate limits - retryable
            if attempt < max_retries - 1:
                wait_time = base_delay * (2**attempt)
                logger.warning(
                    f"Error fetching {series_id}: {e}. "
                    f"Retrying in {wait_time} seconds "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Failed to fetch {series_id} after {max_retries} attempts: {e}"
                )
                raise

    # Should not reach here, but for type safety
    return pd.Series(dtype=float)


def fetch_multiple_series(
    series_ids: list[str],
    start_date: str,
    end_date: str,
    *,
    api_key: str | None = None,
    align_method: str = "ffill",
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Fetch multiple FRED series and align to common date index.

    Different FRED series have different observation frequencies (daily, weekly,
    monthly). This function fetches all series and aligns them using forward-fill
    to handle missing values from lower-frequency series.

    Date Alignment Strategy:
    - Creates union of all series dates as index
    - Forward-fills lower-frequency data (e.g., monthly unemployment)
    - Preserves original observations without interpolation
    - NaN values remain at start of series before first observation

    Args:
        series_ids: List of FRED series identifiers to fetch.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        api_key: FRED API key. If None, uses FRED_API_KEY env variable.
        align_method: Alignment method for missing values (default: 'ffill').
            Options: 'ffill' (forward-fill), 'bfill' (back-fill), None (no fill).
        **kwargs: Additional arguments passed to fetch_series().

    Returns:
        DataFrame with datetime index and one column per series.
        Column names match series_ids.

    Raises:
        ValueError: If API key not configured or any series_id invalid.

    Examples:
        >>> df = fetch_multiple_series(
        ...     ['VIXCLS', 'DGS10', 'UNRATE'],
        ...     '2020-01-01', '2021-01-01'
        ... )
        >>> print(df.columns.tolist())
        ['VIXCLS', 'DGS10', 'UNRATE']

    Notes:
        FRED API rate limit is 120 requests/minute. This function adds 500ms
        delay between requests to stay within limits.
    """
    series_data = {}

    for i, series_id in enumerate(series_ids):
        try:
            # Add delay between requests to respect rate limits
            if i > 0:
                time.sleep(RATE_LIMIT_DELAY)

            series = fetch_series(
                series_id,
                start_date,
                end_date,
                api_key=api_key,
                **kwargs,
            )

            if not series.empty:
                series_data[series_id] = series
            else:
                logger.warning(f"Series {series_id} returned no data")

        except Exception as e:
            logger.error(f"Failed to fetch series {series_id}: {e}")
            # Continue fetching other series instead of failing completely

    if not series_data:
        logger.warning("No series data successfully fetched")
        return pd.DataFrame()

    # Combine series into DataFrame with common index
    df = pd.DataFrame(series_data)

    # Apply alignment method for missing values
    if align_method == "ffill":
        df = df.fillna(method="ffill")
    elif align_method == "bfill":
        df = df.fillna(method="bfill")
    # If None, leave NaN values as-is

    logger.info(f"Fetched {len(df)} observations across {len(df.columns)} series")
    return df


def fetch_macro_indicators(
    start_date: str,
    end_date: str,
    *,
    api_key: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Fetch standard macroeconomic indicators for financial TDA analysis.

    Convenience function that fetches all required FRED series:
    - VIXCLS: VIX Volatility Index (crisis detection)
    - DGS10: 10-Year Treasury Yield (long-term rates)
    - DGS2: 2-Year Treasury Yield (short-term rates)
    - T10Y2Y: 10Y-2Y Yield Spread (recession indicator)
    - UNRATE: Unemployment Rate (economic health)
    - FEDFUNDS: Federal Funds Rate (monetary policy)

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        api_key: FRED API key. If None, uses FRED_API_KEY env variable.
        **kwargs: Additional arguments passed to fetch_multiple_series().

    Returns:
        DataFrame with datetime index and columns for each indicator.
        Data is forward-filled to align different observation frequencies.

    Raises:
        ValueError: If API key not configured.

    Examples:
        >>> indicators = fetch_macro_indicators('2020-01-01', '2021-01-01')
        >>> print(indicators.columns.tolist())
        ['VIXCLS', 'DGS10', 'DGS2', 'T10Y2Y', 'UNRATE', 'FEDFUNDS']

    Notes:
        This function may take several seconds due to rate limiting
        (500ms delay between series requests).
    """
    series_ids = list(MACRO_SERIES.keys())
    logger.info(f"Fetching {len(series_ids)} macro indicators from FRED")

    return fetch_multiple_series(
        series_ids,
        start_date,
        end_date,
        api_key=api_key,
        **kwargs,
    )
