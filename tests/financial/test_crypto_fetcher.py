"""
Tests for cryptocurrency data fetcher (CoinGecko API).

This module contains both unit tests (mocked) and integration tests (real API calls).
Integration tests validate 2022 crypto winter period data.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from financial_tda.data.fetchers.crypto import (
    COINGECKO_API_KEY,
    fetch_historical_range,
    fetch_market_chart,
    fetch_multiple_coins,
    fetch_ohlc,
)

# ============================================================================
# UNIT TESTS (MOCKED - ALWAYS RUN)
# ============================================================================


class TestFetchOHLC:
    """Unit tests for fetch_ohlc() with mocked API responses."""

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_ohlc_success(self, mock_get):
        """Test successful OHLC data fetch."""
        # Mock CoinGecko OHLC response format
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [1609459200000, 29000.0, 29500.0, 28500.0, 29200.0],
            [1609545600000, 29200.0, 30000.0, 29000.0, 29800.0],
            [1609632000000, 29800.0, 30500.0, 29500.0, 30200.0],
        ]
        mock_get.return_value = mock_response

        # Execute
        result = fetch_ohlc("bitcoin", vs_currency="usd", days=7)

        # Validate
        assert not result.empty
        assert len(result) == 3
        assert list(result.columns) == ["Open", "High", "Low", "Close"]
        assert result["Close"].iloc[0] == 29200.0

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_ohlc_coin_id_mapping(self, mock_get):
        """Test that short coin IDs are mapped to full names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Execute with short ID
        fetch_ohlc("btc", days=7)

        # Validate that 'bitcoin' was used in URL
        call_args = mock_get.call_args
        assert "bitcoin" in call_args[0][0]

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_ohlc_empty_response(self, mock_get):
        """Test handling of empty API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Execute
        result = fetch_ohlc("invalid_coin", days=7)

        # Validate
        assert result.empty

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    @patch("financial_tda.data.fetchers.crypto.time.sleep")
    def test_fetch_ohlc_rate_limit_retry(self, mock_sleep, mock_get):
        """Test exponential backoff on rate limit (HTTP 429)."""
        # First two attempts return 429, third succeeds
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [
            [1609459200000, 29000.0, 29500.0, 28500.0, 29200.0],
        ]

        mock_get.side_effect = [
            mock_response_429,
            mock_response_429,
            mock_response_success,
        ]

        # Execute
        result = fetch_ohlc("bitcoin", days=7)

        # Validate retry logic
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        # Check exponential backoff: 30s, 60s
        assert mock_sleep.call_args_list[0][0][0] == 30
        assert mock_sleep.call_args_list[1][0][0] == 60
        assert not result.empty

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    @patch("financial_tda.data.fetchers.crypto.time.sleep")
    def test_fetch_ohlc_rate_limit_exceeded(self, mock_sleep, mock_get):
        """Test that rate limit error is raised after max retries."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        # Execute and validate exception
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            fetch_ohlc("bitcoin", days=7, max_retries=3)

        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_ohlc_invalid_coin(self, mock_get):
        """Test error handling for invalid coin ID (HTTP 404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Execute and validate exception
        with pytest.raises(ValueError, match="Invalid coin ID"):
            fetch_ohlc("invalid_coin_xyz", days=7)


class TestFetchMarketChart:
    """Unit tests for fetch_market_chart() with mocked API responses."""

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_market_chart_success(self, mock_get):
        """Test successful market chart fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prices": [
                [1609459200000, 29000.0],
                [1609545600000, 29500.0],
            ],
            "market_caps": [
                [1609459200000, 550000000000],
                [1609545600000, 560000000000],
            ],
            "total_volumes": [
                [1609459200000, 35000000000],
                [1609545600000, 38000000000],
            ],
        }
        mock_get.return_value = mock_response

        # Execute
        result = fetch_market_chart("ethereum", days=7)

        # Validate
        assert not result.empty
        assert len(result) == 2
        assert list(result.columns) == ["Price", "MarketCap", "Volume"]
        assert result["Price"].iloc[0] == 29000.0

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_market_chart_missing_fields(self, mock_get):
        """Test handling of response with missing optional fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Only prices provided (market_caps, volumes optional)
        mock_response.json.return_value = {
            "prices": [
                [1609459200000, 29000.0],
            ],
        }
        mock_get.return_value = mock_response

        # Execute
        result = fetch_market_chart("bitcoin", days=7)

        # Should still work with NaN for missing fields
        assert not result.empty
        assert "Price" in result.columns


class TestFetchHistoricalRange:
    """Unit tests for fetch_historical_range() with mocked responses."""

    @patch("financial_tda.data.fetchers.crypto.requests.get")
    def test_fetch_historical_range_success(self, mock_get):
        """Test successful historical range fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prices": [
                [1609459200000, 29000.0],
                [1609545600000, 29500.0],
            ],
            "market_caps": [
                [1609459200000, 550000000000],
                [1609545600000, 560000000000],
            ],
            "total_volumes": [
                [1609459200000, 35000000000],
                [1609545600000, 38000000000],
            ],
        }
        mock_get.return_value = mock_response

        # Execute
        result = fetch_historical_range("bitcoin", "usd", "2021-01-01", "2021-01-31")

        # Validate
        assert not result.empty
        assert len(result) == 2
        assert list(result.columns) == ["Price", "MarketCap", "Volume"]

    def test_fetch_historical_range_invalid_date(self):
        """Test error handling for invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            fetch_historical_range("bitcoin", "usd", "2021/01/01", "2021-01-31")


class TestFetchMultipleCoins:
    """Unit tests for fetch_multiple_coins() with mocked responses."""

    @patch("financial_tda.data.fetchers.crypto.fetch_ohlc")
    @patch("financial_tda.data.fetchers.crypto.time.sleep")
    def test_fetch_multiple_success(self, mock_sleep, mock_fetch_ohlc):
        """Test successful fetch of multiple coins."""
        # Mock individual fetch responses
        btc_data = pd.DataFrame(
            {"Open": [29000], "High": [30000], "Low": [28500], "Close": [29500]},
            index=pd.DatetimeIndex(["2021-01-01"]),
        )
        eth_data = pd.DataFrame(
            {"Open": [1200], "High": [1250], "Low": [1180], "Close": [1230]},
            index=pd.DatetimeIndex(["2021-01-01"]),
        )

        mock_fetch_ohlc.side_effect = [btc_data, eth_data]

        # Execute
        result = fetch_multiple_coins(["bitcoin", "ethereum"], days=7)

        # Validate
        assert len(result) == 2
        assert "bitcoin" in result
        assert "ethereum" in result
        assert not result["bitcoin"].empty

        # Should sleep once (between 1st and 2nd request)
        assert mock_sleep.call_count == 1

    @patch("financial_tda.data.fetchers.crypto.fetch_ohlc")
    @patch("financial_tda.data.fetchers.crypto.time.sleep")
    def test_fetch_multiple_partial_failure(self, mock_sleep, mock_fetch_ohlc):
        """Test that partial failures don't prevent other coins."""
        btc_data = pd.DataFrame(
            {"Open": [29000], "High": [30000], "Low": [28500], "Close": [29500]},
            index=pd.DatetimeIndex(["2021-01-01"]),
        )

        # First succeeds, second fails, third succeeds
        mock_fetch_ohlc.side_effect = [
            btc_data,
            Exception("Network error"),
            btc_data,
        ]

        # Execute
        result = fetch_multiple_coins(["btc1", "btc2", "btc3"], days=7)

        # Should have btc1 and btc3, but not btc2
        assert len(result) == 2
        assert "btc1" in result
        assert "btc3" in result
        assert "btc2" not in result

    @patch("financial_tda.data.fetchers.crypto.fetch_market_chart")
    def test_fetch_multiple_use_market_chart(self, mock_fetch_chart):
        """Test using market chart instead of OHLC."""
        mock_fetch_chart.return_value = pd.DataFrame(
            {"Price": [29000], "MarketCap": [550000000000], "Volume": [35000000000]},
            index=pd.DatetimeIndex(["2021-01-01"]),
        )

        # Execute with use_ohlc=False
        result = fetch_multiple_coins(["bitcoin"], days=7, use_ohlc=False)

        # Validate market chart was used
        assert mock_fetch_chart.called
        assert not result["bitcoin"].empty


# ============================================================================
# INTEGRATION TESTS (REAL API CALLS - REQUIRES NETWORK)
# ============================================================================


@pytest.mark.integration
class TestCryptoIntegration:
    """Integration tests with real CoinGecko API calls."""

    def test_fetch_bitcoin_ohlc(self):
        """Test fetching real Bitcoin OHLC data."""
        btc = fetch_ohlc("bitcoin", vs_currency="usd", days=30)

        assert not btc.empty
        assert len(btc) > 20  # At least 20 observations in 30 days
        assert list(btc.columns) == ["Open", "High", "Low", "Close"]

        # Validate OHLC relationships
        assert (btc["High"] >= btc["Open"]).all()
        assert (btc["High"] >= btc["Close"]).all()
        assert (btc["Low"] <= btc["Open"]).all()
        assert (btc["Low"] <= btc["Close"]).all()

    def test_fetch_ethereum_market_chart(self):
        """Test fetching real Ethereum market chart data."""
        eth = fetch_market_chart("ethereum", vs_currency="usd", days=7)

        assert not eth.empty
        assert "Price" in eth.columns
        assert "MarketCap" in eth.columns
        assert "Volume" in eth.columns

        # Should have many observations (hourly for 7 days)
        assert len(eth) > 100

    @pytest.mark.skipif(
        not COINGECKO_API_KEY,
        reason="CoinGecko API key required (set COINGECKO_API_KEY env var)",
    )
    def test_crypto_winter_2022_bitcoin(self):
        """
        Test Bitcoin data during 2022 crypto winter.

        Bitcoin dropped from ~$47k (Jan 2022) to ~$16k (Nov 2022).
        Validates major drawdown period.
        """
        btc = fetch_historical_range("bitcoin", "usd", "2022-01-01", "2022-12-31")

        assert not btc.empty
        assert len(btc) > 300  # Full year of data

        # Find peak and trough
        jan_prices = btc.loc["2022-01"]["Price"]
        nov_prices = btc.loc["2022-11"]["Price"]

        jan_high = jan_prices.max()
        nov_low = nov_prices.min()

        # Bitcoin should show significant decline
        # Jan 2022: ~$47k, Nov 2022: ~$16k (65% drawdown)
        assert jan_high > 40000, f"Expected Jan high > $40k, got ${jan_high}"
        assert nov_low < 20000, f"Expected Nov low < $20k, got ${nov_low}"

        # Validate drawdown magnitude
        drawdown = (nov_low - jan_high) / jan_high
        assert drawdown < -0.50, f"Expected >50% drawdown, got {drawdown * 100:.1f}%"

    @pytest.mark.skipif(
        not COINGECKO_API_KEY,
        reason="CoinGecko API key required (set COINGECKO_API_KEY env var)",
    )
    def test_crypto_winter_2022_ethereum(self):
        """
        Test Ethereum data during 2022 crypto winter.

        Ethereum dropped from ~$3.8k (Jan 2022) to ~$1.2k (Nov 2022).
        """
        eth = fetch_historical_range("ethereum", "usd", "2022-01-01", "2022-12-31")

        assert not eth.empty

        jan_prices = eth.loc["2022-01"]["Price"]
        nov_prices = eth.loc["2022-11"]["Price"]

        jan_high = jan_prices.max()
        nov_low = nov_prices.min()

        # Ethereum: Jan ~$3.8k, Nov ~$1.2k
        assert jan_high > 3000, f"Expected Jan high > $3k, got ${jan_high}"
        assert nov_low < 1500, f"Expected Nov low < $1.5k, got ${nov_low}"

    @pytest.mark.skipif(
        not COINGECKO_API_KEY,
        reason="CoinGecko API key required (set COINGECKO_API_KEY env var)",
    )
    def test_terra_collapse_period_may_2022(self):
        """
        Test crypto market during Terra/LUNA collapse (May 2022).

        Bitcoin and Ethereum both saw sharp declines during this period.
        """
        btc = fetch_historical_range("bitcoin", "usd", "2022-05-01", "2022-05-31")

        assert not btc.empty

        # Bitcoin dropped from ~$38k to ~$29k during May 2022
        may_high = btc["Price"].max()
        may_low = btc["Price"].min()

        assert may_high > 35000
        assert may_low < 30000

        # High volatility period - large daily swings
        daily_range = (btc["Price"].max() - btc["Price"].min()) / btc["Price"].mean()
        assert daily_range > 0.20  # >20% range from high to low

    def test_fetch_multiple_coins_integration(self):
        """Test fetching multiple cryptocurrencies simultaneously."""
        coins = ["bitcoin", "ethereum"]
        data = fetch_multiple_coins(coins, vs_currency="usd", days=7)

        assert len(data) == 2
        assert "bitcoin" in data
        assert "ethereum" in data

        for coin, df in data.items():
            assert not df.empty
            assert list(df.columns) == ["Open", "High", "Low", "Close"]

    def test_coin_id_mapping_integration(self):
        """Test that short coin IDs work in real API calls."""
        # Use short ID 'btc' instead of 'bitcoin'
        btc = fetch_ohlc("btc", days=7)

        assert not btc.empty
        assert len(btc) > 5
