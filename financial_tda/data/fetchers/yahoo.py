"""
Yahoo Finance data fetcher for equities and indices.

This module provides functions to fetch OHLCV (Open, High, Low, Close, Volume)
data from Yahoo Finance using the yfinance library. It supports single ticker
fetching, batch downloads, and convenient index symbol mapping.

Implements robust error handling for rate limits, missing data, and invalid tickers.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import yfinance as yf
from yfinance.exceptions import (
    YFPricesMissingError,
    YFRateLimitError,
    YFTickerMissingError,
)

logger = logging.getLogger(__name__)

# Index symbol mapping for convenience
INDEX_SYMBOLS = {
    "sp500": "^GSPC",
    "ftse100": "^FTSE",
    "stoxx600": "^STOXX",
    "dji": "^DJI",
    "nasdaq": "^IXIC",
    "vix": "^VIX",
}

# Default ticker lists for major indices
DEFAULT_TICKERS = {
    "sp500": "^GSPC",
    "ftse100": "^FTSE",
    "stoxx600": "^STOXX",
}


def fetch_ticker(
    ticker: str,
    start_date: str,
    end_date: str,
    *,
    max_retries: int = 5,
    base_delay: int = 60,
    timeout: int = 30,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a single ticker from Yahoo Finance.

    Implements exponential backoff retry logic for rate limit handling.
    Returns empty DataFrame if no data is available for the requested period.

    Args:
        ticker: Ticker symbol (e.g., 'AAPL', '^GSPC').
        start_date: Start date in YYYY-MM-DD format (inclusive).
        end_date: End date in YYYY-MM-DD format (exclusive).
        max_retries: Maximum number of retry attempts for rate limits (default: 5).
        base_delay: Base delay in seconds for exponential backoff (default: 60).
        timeout: Request timeout in seconds (default: 30).

    Returns:
        DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume.
        Returns empty DataFrame if no data available.

    Raises:
        ValueError: If ticker symbol is invalid or dates are malformed.
        YFRateLimitError: If rate limit exceeded after max retries.

    Examples:
        >>> data = fetch_ticker('AAPL', '2020-01-01', '2021-01-01')
        >>> print(data.columns)
        Index(['Open', 'High', 'Low', 'Close', 'Volume'], dtype='object')
    """
    ticker_obj = yf.Ticker(ticker)

    for attempt in range(max_retries):
        try:
            data = ticker_obj.history(
                start=start_date,
                end=end_date,
                auto_adjust=True,
                actions=False,
                repair=True,
                keepna=False,
                timeout=timeout,
            )

            if data.empty:
                logger.warning(
                    f"No data returned for ticker {ticker} "
                    f"from {start_date} to {end_date}"
                )
                return pd.DataFrame()

            # Select only OHLCV columns
            ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
            return data[ohlcv_cols]

        except YFRateLimitError:
            if attempt < max_retries - 1:
                wait_time = base_delay * (2**attempt)
                logger.warning(
                    f"Rate limit hit for {ticker}. "
                    f"Retrying in {wait_time} seconds "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Rate limit exceeded for {ticker} after {max_retries} attempts"
                )
                raise

        except YFPricesMissingError as e:
            logger.warning(f"No price data for {ticker}: {e.rationale}")
            return pd.DataFrame()

        except YFTickerMissingError as e:
            logger.error(f"Invalid ticker symbol: {ticker}")
            raise ValueError(f"Invalid ticker symbol: {ticker}") from e

    # Should not reach here, but for type safety
    return pd.DataFrame()


def fetch_multiple(
    tickers: list[str],
    start_date: str,
    end_date: str,
    *,
    threads: bool = True,
    max_retries: int = 5,
    base_delay: int = 60,
    timeout: int = 30,
) -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data for multiple tickers efficiently using batch download.

    Uses yfinance's multi-threaded download capability for improved performance.
    Handles individual ticker failures gracefully, returning available data.

    Args:
        tickers: List of ticker symbols to fetch.
        start_date: Start date in YYYY-MM-DD format (inclusive).
        end_date: End date in YYYY-MM-DD format (exclusive).
        threads: Enable multi-threaded downloads (default: True).
        max_retries: Maximum retry attempts for rate limits (default: 5).
        base_delay: Base delay in seconds for exponential backoff (default: 60).
        timeout: Request timeout in seconds (default: 30).

    Returns:
        Dictionary mapping ticker symbols to DataFrames with OHLCV data.
        Missing or failed tickers are excluded from the result.

    Raises:
        YFRateLimitError: If rate limit exceeded after max retries.

    Examples:
        >>> data = fetch_multiple(['AAPL', 'MSFT'], '2020-01-01', '2021-01-01')
        >>> print(data.keys())
        dict_keys(['AAPL', 'MSFT'])
    """
    for attempt in range(max_retries):
        try:
            # Download data with group_by='ticker' for easier parsing
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                threads=threads,
                group_by="ticker",
                auto_adjust=True,
                actions=False,
                repair=True,
                keepna=False,
                progress=False,
                timeout=timeout,
            )

            if data is None or data.empty:
                logger.warning(
                    f"No data returned for any tickers from {start_date} to {end_date}"
                )
                return {}

            result = {}

            # Handle single ticker case (data is not MultiIndex)
            if len(tickers) == 1:
                ticker = tickers[0]
                if not data.empty:
                    ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
                    result[ticker] = data[ohlcv_cols]
                return result

            # Handle multiple tickers (data has MultiIndex columns)
            for ticker in tickers:
                try:
                    ticker_data = data[ticker]
                    if not ticker_data.empty:
                        ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
                        result[ticker] = ticker_data[ohlcv_cols]
                    else:
                        logger.warning(f"No data for ticker {ticker}")
                except KeyError:
                    logger.warning(f"Ticker {ticker} not found in downloaded data")

            return result

        except YFRateLimitError:
            if attempt < max_retries - 1:
                wait_time = base_delay * (2**attempt)
                logger.warning(
                    f"Rate limit hit for batch download. "
                    f"Retrying in {wait_time} seconds "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Rate limit exceeded for batch download "
                    f"after {max_retries} attempts"
                )
                raise

    # Should not reach here, but for type safety
    return {}


def fetch_index(
    index_name: str,
    start_date: str,
    end_date: str,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a market index using friendly names.

    Convenience wrapper around fetch_ticker() that maps friendly index names
    to Yahoo Finance symbols (e.g., 'sp500' -> '^GSPC').

    Args:
        index_name: Friendly index name (case-insensitive).
            Supported: 'sp500', 'ftse100', 'stoxx600', 'dji', 'nasdaq', 'vix'.
        start_date: Start date in YYYY-MM-DD format (inclusive).
        end_date: End date in YYYY-MM-DD format (exclusive).
        **kwargs: Additional arguments passed to fetch_ticker().

    Returns:
        DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume.

    Raises:
        ValueError: If index_name is not recognized.

    Examples:
        >>> data = fetch_index('sp500', '2020-01-01', '2021-01-01')
        >>> print(data.index.name)
        Date
    """
    index_name_lower = index_name.lower()

    if index_name_lower not in INDEX_SYMBOLS:
        supported = ", ".join(INDEX_SYMBOLS.keys())
        raise ValueError(
            f"Unsupported index name: '{index_name}'. Supported indices: {supported}"
        )

    symbol = INDEX_SYMBOLS[index_name_lower]
    logger.info(f"Fetching index {index_name} (symbol: {symbol})")

    return fetch_ticker(symbol, start_date, end_date, **kwargs)
