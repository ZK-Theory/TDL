"""
Data fetchers for financial market data from various sources.
"""

from financial_tda.data.fetchers.crypto import (
    COIN_IDS,
    fetch_historical_range,
    fetch_market_chart,
    fetch_multiple_coins,
    fetch_ohlc,
)
from financial_tda.data.fetchers.fred import (
    MACRO_SERIES,
    fetch_macro_indicators,
    fetch_multiple_series,
    fetch_series,
    get_fred_client,
)
from financial_tda.data.fetchers.yahoo import (
    INDEX_SYMBOLS,
    fetch_index,
    fetch_multiple,
    fetch_ticker,
)

__all__ = [
    # Yahoo Finance
    "fetch_ticker",
    "fetch_multiple",
    "fetch_index",
    "INDEX_SYMBOLS",
    # FRED
    "get_fred_client",
    "fetch_series",
    "fetch_multiple_series",
    "fetch_macro_indicators",
    "MACRO_SERIES",
    # Crypto (CoinGecko)
    "fetch_ohlc",
    "fetch_market_chart",
    "fetch_historical_range",
    "fetch_multiple_coins",
    "COIN_IDS",
]
