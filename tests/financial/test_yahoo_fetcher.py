"""
Tests for Yahoo Finance data fetcher.

This module contains both unit tests (mocked) and integration tests (real API calls).
Integration tests are marked with @pytest.mark.integration and validate against
known historical data during financial crisis periods.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from yfinance.exceptions import (
    YFPricesMissingError,
    YFRateLimitError,
    YFTickerMissingError,
)

from financial_tda.data.fetchers.yahoo import (
    fetch_index,
    fetch_multiple,
    fetch_ticker,
)

# ============================================================================
# UNIT TESTS (MOCKED - ALWAYS RUN)
# ============================================================================


class TestFetchTickerUnit:
    """Unit tests for fetch_ticker() with mocked API responses."""

    @patch("financial_tda.data.fetchers.yahoo.yf.Ticker")
    def test_fetch_ticker_success(self, mock_ticker_cls):
        """Test successful single ticker data fetch."""
        # Mock successful response
        mock_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0],
                "High": [105.0, 106.0, 107.0],
                "Low": [99.0, 100.0, 101.0],
                "Close": [104.0, 105.0, 106.0],
                "Volume": [1000000, 1100000, 1200000],
            },
            index=pd.date_range("2020-01-01", periods=3, freq="D"),
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_data
        mock_ticker_cls.return_value = mock_ticker

        # Execute
        result = fetch_ticker("AAPL", "2020-01-01", "2020-01-04")

        # Validate
        assert not result.empty
        assert len(result) == 3
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert result["Close"].iloc[0] == 104.0

    @patch("financial_tda.data.fetchers.yahoo.yf.Ticker")
    def test_fetch_ticker_empty_data(self, mock_ticker_cls):
        """Test handling of empty data response (no trading data)."""
        # Mock empty response
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_ticker

        # Execute
        result = fetch_ticker("INVALID", "2020-01-01", "2020-01-04")

        # Validate
        assert result.empty

    @patch("financial_tda.data.fetchers.yahoo.yf.Ticker")
    @patch("financial_tda.data.fetchers.yahoo.time.sleep")
    def test_fetch_ticker_rate_limit_retry(self, mock_sleep, mock_ticker_cls):
        """Test exponential backoff retry logic on rate limit."""
        # Mock rate limit on first two attempts, success on third
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = [
            YFRateLimitError(),
            YFRateLimitError(),
            pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [105.0],
                    "Low": [99.0],
                    "Close": [104.0],
                    "Volume": [1000000],
                },
                index=pd.date_range("2020-01-01", periods=1, freq="D"),
            ),
        ]
        mock_ticker_cls.return_value = mock_ticker

        # Execute
        result = fetch_ticker("AAPL", "2020-01-01", "2020-01-02", base_delay=1)

        # Validate retry logic
        assert mock_ticker.history.call_count == 3
        assert mock_sleep.call_count == 2
        # Check exponential backoff: 1s, 2s
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2
        assert not result.empty

    @patch("financial_tda.data.fetchers.yahoo.yf.Ticker")
    @patch("financial_tda.data.fetchers.yahoo.time.sleep")
    def test_fetch_ticker_rate_limit_max_retries(self, mock_sleep, mock_ticker_cls):
        """Test that rate limit error is raised after max retries."""
        # Mock persistent rate limiting
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = YFRateLimitError()
        mock_ticker_cls.return_value = mock_ticker

        # Execute and validate exception
        with pytest.raises(YFRateLimitError):
            fetch_ticker(
                "AAPL", "2020-01-01", "2020-01-02", max_retries=3, base_delay=1
            )

        # Should attempt 3 times (0, 1, 2), sleep 2 times (after attempts 0 and 1)
        assert mock_ticker.history.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("financial_tda.data.fetchers.yahoo.yf.Ticker")
    def test_fetch_ticker_invalid_symbol(self, mock_ticker_cls):
        """Test handling of invalid ticker symbols."""
        # Mock invalid ticker response
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = YFTickerMissingError(
            "INVALID", "Ticker not found"
        )
        mock_ticker_cls.return_value = mock_ticker

        # Execute and validate exception
        with pytest.raises(ValueError, match="Invalid ticker symbol"):
            fetch_ticker("INVALID", "2020-01-01", "2020-01-02")

    @patch("financial_tda.data.fetchers.yahoo.yf.Ticker")
    def test_fetch_ticker_missing_prices(self, mock_ticker_cls):
        """Test handling of missing price data (delisted ticker)."""
        # Mock missing prices response
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = YFPricesMissingError("DELISTED", {})
        mock_ticker_cls.return_value = mock_ticker

        # Execute
        result = fetch_ticker("DELISTED", "2020-01-01", "2020-01-02")

        # Should return empty DataFrame, not raise
        assert result.empty


class TestFetchMultipleUnit:
    """Unit tests for fetch_multiple() with mocked API responses."""

    @patch("financial_tda.data.fetchers.yahoo.yf.download")
    def test_fetch_multiple_success(self, mock_download):
        """Test successful batch download of multiple tickers."""
        # Mock multi-ticker response with MultiIndex columns
        mock_data = pd.DataFrame(
            {
                ("AAPL", "Open"): [100.0, 101.0],
                ("AAPL", "High"): [105.0, 106.0],
                ("AAPL", "Low"): [99.0, 100.0],
                ("AAPL", "Close"): [104.0, 105.0],
                ("AAPL", "Volume"): [1000000, 1100000],
                ("MSFT", "Open"): [200.0, 201.0],
                ("MSFT", "High"): [205.0, 206.0],
                ("MSFT", "Low"): [199.0, 200.0],
                ("MSFT", "Close"): [204.0, 205.0],
                ("MSFT", "Volume"): [2000000, 2100000],
            },
            index=pd.date_range("2020-01-01", periods=2, freq="D"),
        )
        mock_data.columns = pd.MultiIndex.from_tuples(mock_data.columns)
        mock_download.return_value = mock_data

        # Execute
        result = fetch_multiple(["AAPL", "MSFT"], "2020-01-01", "2020-01-03")

        # Validate
        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result
        assert len(result["AAPL"]) == 2
        assert result["AAPL"]["Close"].iloc[0] == 104.0
        assert result["MSFT"]["Close"].iloc[0] == 204.0

    @patch("financial_tda.data.fetchers.yahoo.yf.download")
    def test_fetch_multiple_single_ticker(self, mock_download):
        """Test batch download with single ticker (no MultiIndex)."""
        # Mock single ticker response (no MultiIndex)
        mock_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [99.0, 100.0],
                "Close": [104.0, 105.0],
                "Volume": [1000000, 1100000],
            },
            index=pd.date_range("2020-01-01", periods=2, freq="D"),
        )
        mock_download.return_value = mock_data

        # Execute
        result = fetch_multiple(["AAPL"], "2020-01-01", "2020-01-03")

        # Validate
        assert len(result) == 1
        assert "AAPL" in result
        assert len(result["AAPL"]) == 2

    @patch("financial_tda.data.fetchers.yahoo.yf.download")
    def test_fetch_multiple_empty_result(self, mock_download):
        """Test handling of empty batch download result."""
        mock_download.return_value = pd.DataFrame()

        # Execute
        result = fetch_multiple(["INVALID1", "INVALID2"], "2020-01-01", "2020-01-03")

        # Validate
        assert len(result) == 0


class TestFetchIndexUnit:
    """Unit tests for fetch_index() convenience wrapper."""

    @patch("financial_tda.data.fetchers.yahoo.fetch_ticker")
    def test_fetch_index_sp500(self, mock_fetch_ticker):
        """Test fetching S&P 500 index by friendly name."""
        mock_data = pd.DataFrame(
            {
                "Open": [3000.0],
                "High": [3100.0],
                "Low": [2950.0],
                "Close": [3050.0],
                "Volume": [5000000],
            },
            index=pd.date_range("2020-01-01", periods=1, freq="D"),
        )
        mock_fetch_ticker.return_value = mock_data

        # Execute
        result = fetch_index("sp500", "2020-01-01", "2020-01-02")

        # Validate
        mock_fetch_ticker.assert_called_once_with("^GSPC", "2020-01-01", "2020-01-02")
        assert not result.empty

    @patch("financial_tda.data.fetchers.yahoo.fetch_ticker")
    def test_fetch_index_case_insensitive(self, mock_fetch_ticker):
        """Test that index names are case-insensitive."""
        mock_fetch_ticker.return_value = pd.DataFrame()

        fetch_index("SP500", "2020-01-01", "2020-01-02")
        mock_fetch_ticker.assert_called_with("^GSPC", "2020-01-01", "2020-01-02")

        mock_fetch_ticker.reset_mock()

        fetch_index("FTSE100", "2020-01-01", "2020-01-02")
        mock_fetch_ticker.assert_called_with("^FTSE", "2020-01-01", "2020-01-02")

    def test_fetch_index_invalid_name(self):
        """Test that invalid index names raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported index name"):
            fetch_index("invalid_index", "2020-01-01", "2020-01-02")


# ============================================================================
# INTEGRATION TESTS (REAL API CALLS - REQUIRES NETWORK)
# ============================================================================


@pytest.mark.integration
class TestFetchTickerIntegration:
    """Integration tests for fetch_ticker() with real Yahoo Finance API."""

    def test_fetch_sp500_2008_crisis(self):
        """
        Test S&P 500 data during 2008 financial crisis.

        Validates data for the period including Black Monday (Sept 29, 2008),
        when markets crashed following Lehman Brothers bankruptcy.
        """
        # Fetch crisis period data
        data = fetch_ticker("^GSPC", "2008-09-01", "2008-12-31")

        # Validate data structure
        assert not data.empty
        assert len(data) > 60  # At least 3 months of trading days
        assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume"]

        # Validate crisis period characteristics
        # Sept 29, 2008: S&P 500 dropped ~8.8% (one of worst single days)
        sept_data = data.loc["2008-09"]
        assert sept_data["Close"].min() < 1200  # Significant drop below 1200

        # Check for high volatility (large daily ranges)
        daily_range = (data["High"] - data["Low"]) / data["Close"]
        avg_volatility = daily_range.mean()
        assert avg_volatility > 0.02  # >2% average daily range during crisis

    def test_fetch_2020_covid_crash(self):
        """
        Test S&P 500 data during COVID-19 crash (Feb-Mar 2020).

        Validates the rapid market decline and subsequent recovery.
        """
        data = fetch_ticker("^GSPC", "2020-02-01", "2020-04-30")

        assert not data.empty
        assert len(data) > 40  # At least 2 months of trading days

        # COVID crash: peak around Feb 19, bottom around Mar 23
        feb_high = data.loc["2020-02"].max()["Close"]
        mar_low = data.loc["2020-03"].min()["Close"]

        # Should show significant drawdown (>25%)
        drawdown = (mar_low - feb_high) / feb_high
        assert drawdown < -0.20  # At least 20% decline

    def test_fetch_multiple_indices(self):
        """Test fetching multiple major indices simultaneously."""
        tickers = ["^GSPC", "^FTSE", "^DJI"]
        data = fetch_multiple(tickers, "2020-01-01", "2020-02-01")

        # Validate all indices returned
        assert len(data) == 3
        for ticker in tickers:
            assert ticker in data
            assert not data[ticker].empty
            assert len(data[ticker]) > 15  # At least 15 trading days

    def test_fetch_index_vix_2015_china_devaluation(self):
        """
        Test VIX data during 2015 China devaluation crisis.

        In August 2015, China devalued its currency, causing global market turmoil.
        VIX spiked significantly during this period.
        """
        data = fetch_index("vix", "2015-08-01", "2015-09-01")

        assert not data.empty

        # VIX should show elevated levels and spike
        # Normal VIX ~15, during crisis often >25
        max_vix = data["Close"].max()
        assert max_vix > 25  # VIX spiked significantly in Aug 2015

    def test_fetch_2022_rate_hike_volatility(self):
        """
        Test S&P 500 data during 2022 Fed rate hike volatility.

        2022 saw aggressive rate hikes leading to market volatility.
        """
        data = fetch_ticker("^GSPC", "2022-01-01", "2022-10-31")

        assert not data.empty
        assert len(data) > 180  # ~9 months of trading days

        # 2022 was a down year with high volatility
        jan_close = data.loc["2022-01"].iloc[-1]["Close"]
        oct_close = data.loc["2022-10"].iloc[-1]["Close"]

        # Should show overall decline
        decline = (oct_close - jan_close) / jan_close
        assert decline < 0  # Negative return for the period

    def test_fetch_invalid_ticker_integration(self):
        """Test that invalid ticker symbols are handled gracefully."""
        # Use obviously invalid ticker
        # Note: yfinance behavior changed - now returns empty DataFrame
        # instead of raising
        result = fetch_ticker("INVALIDTICKER123456", "2020-01-01", "2020-01-02")

        # Should return empty DataFrame for invalid ticker
        assert result.empty

    def test_date_range_validation(self):
        """Test that date ranges work correctly (start inclusive, end exclusive)."""
        # Fetch single day (start inclusive, end exclusive)
        data = fetch_ticker("^GSPC", "2020-01-02", "2020-01-03")

        # Should get exactly one trading day (or zero if holiday/weekend)
        assert len(data) <= 1

        if len(data) == 1:
            # Verify the date is the start date
            assert data.index[0].strftime("%Y-%m-%d") == "2020-01-02"
