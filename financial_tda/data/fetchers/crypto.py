"""
Cryptocurrency data fetcher using CoinGecko API.

This module provides functions to fetch OHLC (Open, High, Low, Close) data,
market charts, and historical price data for cryptocurrencies from CoinGecko's
free API. No API key required for basic endpoints.

CoinGecko API Documentation: https://www.coingecko.com/en/api/documentation
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# CoinGecko base URL
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Optional API key support (CoinGecko now requires auth for many endpoints)
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Coin ID mapping for convenience
COIN_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "ada": "cardano",
    "bnb": "binancecoin",
    "xrp": "ripple",
}

# Rate limiting configuration
RATE_LIMIT_DELAY = 2.0  # 2 seconds between requests for free tier
BASE_RETRY_DELAY = 30  # 30 seconds base delay for rate limit backoff


def fetch_ohlc(
    coin_id: str,
    vs_currency: str = "usd",
    days: int = 30,
    *,
    max_retries: int = 5,
) -> pd.DataFrame:
    """
    Fetch OHLC (Open, High, Low, Close) data for a cryptocurrency.

    Uses CoinGecko's /coins/{id}/ohlc endpoint. Data granularity is automatic:
    - 1 day: 30-minute intervals
    - 7-90 days: 4-hour intervals
    - >90 days: 4-day intervals

    Args:
        coin_id: CoinGecko coin identifier (e.g., 'bitcoin', 'ethereum').
            Use COIN_IDS dict for convenience mappings.
        vs_currency: Target currency (default: 'usd'). Options: usd, eur, etc.
        days: Number of days of data (default: 30).
            Valid: 1, 7, 14, 30, 90, 180, 365, or 'max'.
        max_retries: Maximum retry attempts for rate limits (default: 5).

    Returns:
        DataFrame with DatetimeIndex and columns: Open, High, Low, Close.
        Returns empty DataFrame if no data available.

    Raises:
        ValueError: If coin_id is invalid or API request fails after retries.

    Examples:
        >>> btc = fetch_ohlc('bitcoin', vs_currency='usd', days=30)
        >>> print(btc.columns.tolist())
        ['Open', 'High', 'Low', 'Close']

    Notes:
        CoinGecko free tier rate limit: ~10-30 calls/minute.
        Valid days parameter: 1, 7, 14, 30, 90, 180, 365, max.
    """
    # Map short names to full coin IDs
    if coin_id in COIN_IDS:
        coin_id = COIN_IDS[coin_id]

    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/ohlc"
    params = {"vs_currency": vs_currency, "days": days}
    
    # Add API key to headers if available
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            # Check for rate limiting
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = BASE_RETRY_DELAY * (2**attempt)
                    logger.warning(
                        f"Rate limit hit for {coin_id}. "
                        f"Retrying in {wait_time} seconds "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        f"Rate limit exceeded for {coin_id} "
                        f"after {max_retries} attempts"
                    )
                    raise ValueError(f"Rate limit exceeded for {coin_id}")

            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(
                    f"No OHLC data returned for {coin_id} "
                    f"(currency: {vs_currency}, days: {days})"
                )
                return pd.DataFrame()

            # Parse OHLC data: [[timestamp, open, high, low, close], ...]
            df = pd.DataFrame(
                data, columns=["timestamp", "Open", "High", "Low", "Close"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df.index.name = "Date"

            logger.info(f"Fetched {len(df)} OHLC observations for {coin_id}")
            return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Invalid coin ID: {coin_id}")
                raise ValueError(f"Invalid coin ID: {coin_id}") from e
            elif e.response.status_code == 401:
                logger.error(
                    f"Unauthorized access for {coin_id}. "
                    "CoinGecko API now requires authentication. "
                    "Set COINGECKO_API_KEY environment variable."
                )
                raise ValueError(
                    "CoinGecko API authentication required. "
                    "Set COINGECKO_API_KEY environment variable."
                ) from e
            elif attempt < max_retries - 1:
                wait_time = BASE_RETRY_DELAY * (2**attempt)
                logger.warning(
                    f"HTTP error for {coin_id}: {e}. Retrying in {wait_time} seconds"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch {coin_id} after {max_retries} attempts")
                raise

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = BASE_RETRY_DELAY * (2**attempt)
                logger.warning(
                    f"Network error for {coin_id}: {e}. Retrying in {wait_time} seconds"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Network error for {coin_id} after {max_retries} attempts"
                )
                raise ValueError(f"Failed to fetch {coin_id}: {e}") from e

    # Should not reach here
    return pd.DataFrame()


def fetch_market_chart(
    coin_id: str,
    vs_currency: str = "usd",
    days: int = 30,
    *,
    max_retries: int = 5,
) -> pd.DataFrame:
    """
    Fetch market chart data (prices, market caps, volumes).

    Uses CoinGecko's /coins/{id}/market_chart endpoint.
    Provides higher resolution than OHLC for recent data.

    Data granularity (automatic):
    - 1 day: 5-minute intervals
    - 2-90 days: hourly intervals
    - >90 days: daily intervals

    Args:
        coin_id: CoinGecko coin identifier (e.g., 'bitcoin', 'ethereum').
        vs_currency: Target currency (default: 'usd').
        days: Number of days of data (default: 30).
        max_retries: Maximum retry attempts for rate limits (default: 5).

    Returns:
        DataFrame with DatetimeIndex and columns: Price, MarketCap, Volume.
        Returns empty DataFrame if no data available.

    Raises:
        ValueError: If coin_id is invalid or API request fails after retries.

    Examples:
        >>> eth = fetch_market_chart('ethereum', days=7)
        >>> print(eth.columns.tolist())
        ['Price', 'MarketCap', 'Volume']

    Notes:
        Market chart provides more frequent data points than OHLC
        for short time periods (e.g., 5-minute intervals for 1 day).
    """
    # Map short names to full coin IDs
    if coin_id in COIN_IDS:
        coin_id = COIN_IDS[coin_id]

    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}
    
    # Add API key to headers if available
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = BASE_RETRY_DELAY * (2**attempt)
                    logger.warning(
                        f"Rate limit hit for {coin_id}. "
                        f"Retrying in {wait_time} seconds "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise ValueError(f"Rate limit exceeded for {coin_id}")

            response.raise_for_status()
            data = response.json()

            if not data or "prices" not in data:
                logger.warning(f"No market chart data for {coin_id}")
                return pd.DataFrame()

            # Parse market chart data
            prices = pd.DataFrame(data["prices"], columns=["timestamp", "Price"])
            market_caps = pd.DataFrame(
                data.get("market_caps", []), columns=["timestamp", "MarketCap"]
            )
            volumes = pd.DataFrame(
                data.get("total_volumes", []), columns=["timestamp", "Volume"]
            )

            # Merge on timestamp
            df = prices.merge(market_caps, on="timestamp", how="left")
            df = df.merge(volumes, on="timestamp", how="left")

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df.index.name = "Date"

            logger.info(f"Fetched {len(df)} market chart observations for {coin_id}")
            return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Invalid coin ID: {coin_id}") from e
            elif e.response.status_code == 401:
                logger.error(
                    f"Unauthorized access for {coin_id}. "
                    "CoinGecko API now requires authentication. "
                    "Set COINGECKO_API_KEY environment variable."
                )
                raise ValueError(
                    "CoinGecko API authentication required. "
                    "Set COINGECKO_API_KEY environment variable."
                ) from e
            elif attempt < max_retries - 1:
                wait_time = BASE_RETRY_DELAY * (2**attempt)
                logger.warning(
                    f"HTTP error for {coin_id}: {e}. Retrying in {wait_time}s"
                )
                time.sleep(wait_time)
            else:
                raise

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = BASE_RETRY_DELAY * (2**attempt)
                time.sleep(wait_time)
            else:
                raise ValueError(f"Failed to fetch {coin_id}: {e}") from e

    return pd.DataFrame()


def fetch_historical_range(
    coin_id: str,
    vs_currency: str,
    start_date: str,
    end_date: str,
    *,
    max_retries: int = 5,
) -> pd.DataFrame:
    """
    Fetch cryptocurrency data for specific date range.

    Uses CoinGecko's /coins/{id}/market_chart/range endpoint.
    Converts dates to Unix timestamps for API compatibility.

    Args:
        coin_id: CoinGecko coin identifier (e.g., 'bitcoin', 'ethereum').
        vs_currency: Target currency (e.g., 'usd', 'eur').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        max_retries: Maximum retry attempts for rate limits (default: 5).

    Returns:
        DataFrame with DatetimeIndex and columns: Price, MarketCap, Volume.
        Returns empty DataFrame if no data available.

    Raises:
        ValueError: If dates invalid or API request fails after retries.

    Examples:
        >>> btc = fetch_historical_range(
        ...     'bitcoin', 'usd', '2022-01-01', '2022-12-31'
        ... )
        >>> print(len(btc))  # Full year of data

    Notes:
        Data granularity depends on date range length (same as market_chart).
    """
    # Map short names to full coin IDs
    if coin_id in COIN_IDS:
        coin_id = COIN_IDS[coin_id]

    # Convert dates to Unix timestamps
    try:
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}") from e

    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart/range"
    params = {
        "vs_currency": vs_currency,
        "from": start_ts,
        "to": end_ts,
    }
    
    # Add API key to headers if available
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = BASE_RETRY_DELAY * (2**attempt)
                    logger.warning(
                        f"Rate limit hit for {coin_id}. "
                        f"Retrying in {wait_time} seconds "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise ValueError(f"Rate limit exceeded for {coin_id}")

            response.raise_for_status()
            data = response.json()

            if not data or "prices" not in data:
                logger.warning(f"No data for {coin_id} from {start_date} to {end_date}")
                return pd.DataFrame()

            # Parse data (same format as market_chart)
            prices = pd.DataFrame(data["prices"], columns=["timestamp", "Price"])
            market_caps = pd.DataFrame(
                data.get("market_caps", []), columns=["timestamp", "MarketCap"]
            )
            volumes = pd.DataFrame(
                data.get("total_volumes", []), columns=["timestamp", "Volume"]
            )

            df = prices.merge(market_caps, on="timestamp", how="left")
            df = df.merge(volumes, on="timestamp", how="left")

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df.index.name = "Date"

            logger.info(
                f"Fetched {len(df)} observations for {coin_id} "
                f"from {start_date} to {end_date}"
            )
            return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Invalid coin ID: {coin_id}") from e
            elif e.response.status_code == 401:
                logger.error(
                    f"Unauthorized access for {coin_id}. "
                    "CoinGecko API now requires authentication. "
                    "Set COINGECKO_API_KEY environment variable."
                )
                raise ValueError(
                    "CoinGecko API authentication required. "
                    "Set COINGECKO_API_KEY environment variable."
                ) from e
            elif attempt < max_retries - 1:
                wait_time = BASE_RETRY_DELAY * (2**attempt)
                time.sleep(wait_time)
            else:
                raise

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = BASE_RETRY_DELAY * (2**attempt)
                time.sleep(wait_time)
            else:
                raise ValueError(f"Failed to fetch {coin_id}: {e}") from e

    return pd.DataFrame()


def fetch_multiple_coins(
    coin_ids: list[str],
    vs_currency: str = "usd",
    days: int = 30,
    *,
    use_ohlc: bool = True,
    **kwargs: Any,
) -> dict[str, pd.DataFrame]:
    """
    Fetch data for multiple cryptocurrencies.

    Implements rate limiting delays between requests to respect
    CoinGecko free tier limits (~10-30 calls/minute).

    Args:
        coin_ids: List of CoinGecko coin identifiers.
        vs_currency: Target currency (default: 'usd').
        days: Number of days of data (default: 30).
        use_ohlc: If True, fetch OHLC data; else fetch market chart
            (default: True).
        **kwargs: Additional arguments passed to fetch functions.

    Returns:
        Dictionary mapping coin_id to DataFrame.
        Missing or failed coins are excluded from result.

    Examples:
        >>> data = fetch_multiple_coins(['bitcoin', 'ethereum'], days=7)
        >>> print(data.keys())
        dict_keys(['bitcoin', 'ethereum'])

    Notes:
        Adds 2-second delay between requests to respect rate limits.
        Continues fetching remaining coins if individual requests fail.
    """
    fetch_func = fetch_ohlc if use_ohlc else fetch_market_chart
    results = {}

    for i, coin_id in enumerate(coin_ids):
        # Add delay between requests (except before first)
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY)

        try:
            df = fetch_func(
                coin_id,
                vs_currency=vs_currency,
                days=days,
                **kwargs,
            )

            if not df.empty:
                results[coin_id] = df
            else:
                logger.warning(f"No data returned for {coin_id}")

        except Exception as e:
            logger.error(f"Failed to fetch {coin_id}: {e}")
            # Continue with remaining coins

    logger.info(f"Successfully fetched {len(results)}/{len(coin_ids)} coins")
    return results
