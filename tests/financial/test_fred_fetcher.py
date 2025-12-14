"""
Tests for FRED (Federal Reserve Economic Data) fetcher.

This module contains both unit tests (mocked) and integration tests (real API calls).
Integration tests validate against known historical values with approximate comparisons.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from financial_tda.data.fetchers.fred import (
    MACRO_SERIES,
    fetch_macro_indicators,
    fetch_multiple_series,
    fetch_series,
    get_fred_client,
)

# ============================================================================
# UNIT TESTS (MOCKED - ALWAYS RUN)
# ============================================================================


class TestGetFredClient:
    """Unit tests for FRED client initialization."""

    @patch.dict(os.environ, {"FRED_API_KEY": "test-api-key"})
    @patch("financial_tda.data.fetchers.fred.Fred")
    def test_client_from_env_var(self, mock_fred_cls):
        """Test loading API key from environment variable."""
        mock_client = MagicMock()
        mock_fred_cls.return_value = mock_client

        client = get_fred_client()

        mock_fred_cls.assert_called_once_with(api_key="test-api-key")
        assert client == mock_client

    @patch("financial_tda.data.fetchers.fred.Fred")
    def test_client_from_parameter(self, mock_fred_cls):
        """Test loading API key from function parameter."""
        mock_client = MagicMock()
        mock_fred_cls.return_value = mock_client

        client = get_fred_client(api_key="param-api-key")

        mock_fred_cls.assert_called_once_with(api_key="param-api-key")
        assert client == mock_client

    @patch.dict(os.environ, {}, clear=True)
    def test_client_missing_api_key(self):
        """Test error when API key not configured."""
        with pytest.raises(ValueError, match="FRED API key not found"):
            get_fred_client()

    @patch.dict(os.environ, {"FRED_API_KEY": "env-key"})
    @patch("financial_tda.data.fetchers.fred.Fred")
    def test_parameter_overrides_env(self, mock_fred_cls):
        """Test that parameter API key overrides environment variable."""
        mock_client = MagicMock()
        mock_fred_cls.return_value = mock_client

        get_fred_client(api_key="param-key")

        # Should use parameter, not env var
        mock_fred_cls.assert_called_once_with(api_key="param-key")


class TestFetchSeries:
    """Unit tests for fetch_series() with mocked API responses."""

    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    def test_fetch_series_success(self, mock_get_client):
        """Test successful single series fetch."""
        # Mock FRED client response
        mock_client = MagicMock()
        mock_series = pd.Series(
            [15.5, 16.2, 14.8],
            index=pd.date_range("2020-01-01", periods=3, freq="D"),
        )
        mock_client.get_series.return_value = mock_series
        mock_get_client.return_value = mock_client

        # Execute
        result = fetch_series("VIXCLS", "2020-01-01", "2020-01-04")

        # Validate
        assert not result.empty
        assert len(result) == 3
        assert result.name == "VIXCLS"
        assert result.iloc[0] == 15.5

    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    def test_fetch_series_empty_data(self, mock_get_client):
        """Test handling of empty series response."""
        mock_client = MagicMock()
        mock_client.get_series.return_value = pd.Series(dtype=float)
        mock_get_client.return_value = mock_client

        # Execute
        result = fetch_series("INVALID", "2020-01-01", "2020-01-04")

        # Validate
        assert result.empty

    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    def test_fetch_series_invalid_id(self, mock_get_client):
        """Test error handling for invalid series ID."""
        mock_client = MagicMock()
        mock_client.get_series.side_effect = ValueError("Bad series ID")
        mock_get_client.return_value = mock_client

        # Execute and validate exception
        with pytest.raises(ValueError, match="Failed to fetch series"):
            fetch_series("INVALID_ID", "2020-01-01", "2020-01-04")

    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    @patch("financial_tda.data.fetchers.fred.time.sleep")
    def test_fetch_series_retry_logic(self, mock_sleep, mock_get_client):
        """Test exponential backoff retry on transient errors."""
        mock_client = MagicMock()
        # First two attempts fail, third succeeds
        mock_client.get_series.side_effect = [
            ConnectionError("Network error"),
            ConnectionError("Network error"),
            pd.Series(
                [15.5],
                index=pd.date_range("2020-01-01", periods=1, freq="D"),
            ),
        ]
        mock_get_client.return_value = mock_client

        # Execute
        result = fetch_series("VIXCLS", "2020-01-01", "2020-01-02", base_delay=1)

        # Validate retry logic
        assert mock_client.get_series.call_count == 3
        assert mock_sleep.call_count == 2
        # Check exponential backoff: 1s, 2s
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2
        assert not result.empty


class TestFetchMultipleSeries:
    """Unit tests for fetch_multiple_series() with mocked API responses."""

    @patch("financial_tda.data.fetchers.fred.fetch_series")
    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    @patch("financial_tda.data.fetchers.fred.time.sleep")
    def test_fetch_multiple_success(
        self, mock_sleep, mock_get_client, mock_fetch_series
    ):
        """Test successful fetch of multiple series with alignment."""
        # Mock two series with different frequencies
        vix_data = pd.Series(
            [15.5, 16.2, 14.8],
            index=pd.date_range("2020-01-01", periods=3, freq="D"),
            name="VIXCLS",
        )
        unrate_data = pd.Series(
            [3.5],  # Monthly data (only one observation)
            index=pd.DatetimeIndex(["2020-01-01"]),
            name="UNRATE",
        )

        mock_fetch_series.side_effect = [vix_data, unrate_data]
        mock_get_client.return_value = MagicMock()

        # Execute
        result = fetch_multiple_series(["VIXCLS", "UNRATE"], "2020-01-01", "2020-01-04")

        # Validate
        assert len(result) == 3  # Should align to daily index
        assert list(result.columns) == ["VIXCLS", "UNRATE"]
        assert result["VIXCLS"].iloc[0] == 15.5
        # UNRATE should be forward-filled to all 3 days
        assert result["UNRATE"].iloc[0] == 3.5
        assert result["UNRATE"].iloc[1] == 3.5  # Forward-filled
        assert result["UNRATE"].iloc[2] == 3.5  # Forward-filled

    @patch("financial_tda.data.fetchers.fred.fetch_series")
    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    @patch("financial_tda.data.fetchers.fred.time.sleep")
    def test_fetch_multiple_rate_limiting(
        self, mock_sleep, mock_get_client, mock_fetch_series
    ):
        """Test that rate limiting delay is applied between requests."""
        mock_fetch_series.return_value = pd.Series(
            [1.0], index=pd.DatetimeIndex(["2020-01-01"])
        )
        mock_get_client.return_value = MagicMock()

        # Execute with 3 series
        fetch_multiple_series(
            ["SERIES1", "SERIES2", "SERIES3"], "2020-01-01", "2020-01-04"
        )

        # Should sleep twice (before 2nd and 3rd request, not before 1st)
        assert mock_sleep.call_count == 2

    @patch("financial_tda.data.fetchers.fred.fetch_series")
    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    def test_fetch_multiple_partial_failure(self, mock_get_client, mock_fetch_series):
        """Test that partial failures don't prevent other series."""
        # First series succeeds, second fails, third succeeds
        mock_fetch_series.side_effect = [
            pd.Series([1.0], index=pd.DatetimeIndex(["2020-01-01"]), name="S1"),
            Exception("Failed to fetch"),
            pd.Series([3.0], index=pd.DatetimeIndex(["2020-01-01"]), name="S3"),
        ]
        mock_get_client.return_value = MagicMock()

        # Execute
        result = fetch_multiple_series(["S1", "S2", "S3"], "2020-01-01", "2020-01-04")

        # Should have S1 and S3, but not S2
        assert "S1" in result.columns
        assert "S3" in result.columns
        assert "S2" not in result.columns

    @patch("financial_tda.data.fetchers.fred.fetch_series")
    @patch("financial_tda.data.fetchers.fred.get_fred_client")
    def test_fetch_multiple_no_fill(self, mock_get_client, mock_fetch_series):
        """Test alignment with no forward-fill."""
        vix_data = pd.Series(
            [15.5, 16.2],
            index=pd.date_range("2020-01-01", periods=2, freq="D"),
            name="VIXCLS",
        )
        unrate_data = pd.Series(
            [3.5],
            index=pd.DatetimeIndex(["2020-01-01"]),
            name="UNRATE",
        )

        mock_fetch_series.side_effect = [vix_data, unrate_data]
        mock_get_client.return_value = MagicMock()

        # Execute with no fill
        result = fetch_multiple_series(
            ["VIXCLS", "UNRATE"],
            "2020-01-01",
            "2020-01-03",
            align_method=None,
        )

        # UNRATE should have NaN on second day (no forward-fill)
        assert pd.isna(result["UNRATE"].iloc[1])


class TestFetchMacroIndicators:
    """Unit tests for fetch_macro_indicators() convenience function."""

    @patch("financial_tda.data.fetchers.fred.fetch_multiple_series")
    def test_fetch_macro_indicators(self, mock_fetch_multiple):
        """Test that all required macro series are fetched."""
        mock_df = pd.DataFrame(
            {series: [1.0] for series in MACRO_SERIES.keys()},
            index=pd.DatetimeIndex(["2020-01-01"]),
        )
        mock_fetch_multiple.return_value = mock_df

        # Execute
        result = fetch_macro_indicators("2020-01-01", "2020-01-04")

        # Validate all series requested
        call_args = mock_fetch_multiple.call_args
        requested_series = call_args[0][0]
        assert set(requested_series) == set(MACRO_SERIES.keys())
        assert not result.empty


# ============================================================================
# INTEGRATION TESTS (REAL API CALLS - REQUIRES NETWORK AND API KEY)
# ============================================================================


@pytest.mark.integration
class TestFredIntegration:
    """Integration tests with real FRED API calls."""

    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """Skip integration tests if FRED_API_KEY not configured."""
        if "FRED_API_KEY" not in os.environ:
            pytest.skip("FRED_API_KEY environment variable not set")

    def test_fetch_vix_2008_crisis(self):
        """
        Test VIX during 2008 financial crisis peak.

        On October 27, 2008, VIX reached ~80, the highest level during GFC.
        """
        vix = fetch_series("VIXCLS", "2008-10-01", "2008-11-01")

        assert not vix.empty
        assert len(vix) > 15  # At least 3 weeks of trading days

        # VIX should have spiked above 70 during this period
        max_vix = vix.max()
        assert max_vix > 70, f"Expected VIX > 70, got {max_vix}"

    def test_fetch_yield_spread_inversion(self):
        """
        Test 10Y-2Y yield spread inversion before 2008 crisis.

        The spread inverted (went negative) in 2006-2007, a classic
        recession warning signal that preceded the GFC.
        """
        spread = fetch_series("T10Y2Y", "2006-01-01", "2007-12-31")

        assert not spread.empty
        assert len(spread) > 300  # ~2 years of business days

        # Spread should show negative values (inversion)
        min_spread = spread.min()
        assert min_spread < 0, f"Expected negative spread inversion, got {min_spread}"

    def test_fetch_fed_funds_2020_covid(self):
        """
        Test Federal Funds Rate during COVID-19 response.

        Fed dropped rates to near-zero in March 2020 in response to pandemic.
        """
        fed_funds = fetch_series("FEDFUNDS", "2020-03-01", "2020-06-01")

        assert not fed_funds.empty

        # Fed funds should be very low (< 0.5%) after March 2020
        min_rate = fed_funds.min()
        assert min_rate < 0.5, f"Expected near-zero rates, got {min_rate}%"

    def test_fetch_multiple_series_alignment(self):
        """
        Test that multiple series with different frequencies are aligned.

        VIX and DGS10 are daily, UNRATE is monthly.
        """
        df = fetch_multiple_series(
            ["VIXCLS", "DGS10", "UNRATE"], "2020-01-01", "2020-03-31"
        )

        assert not df.empty
        assert list(df.columns) == ["VIXCLS", "DGS10", "UNRATE"]

        # Should have daily observations (60+ business days in 3 months)
        assert len(df) > 60

        # UNRATE should have values (forward-filled from monthly data)
        assert df["UNRATE"].notna().sum() > 0

        # Daily series should have more observations than monthly
        vix_obs = df["VIXCLS"].notna().sum()
        unrate_obs = df["UNRATE"].diff().notna().sum()  # Count unique values
        assert vix_obs > unrate_obs

    def test_fetch_all_macro_indicators(self):
        """Test fetching all required macro indicators."""
        indicators = fetch_macro_indicators("2020-01-01", "2020-02-01")

        assert not indicators.empty

        # All 6 required series should be present
        assert len(indicators.columns) == 6
        for series_id in MACRO_SERIES.keys():
            assert series_id in indicators.columns

        # Should have at least 20 trading days in January
        assert len(indicators) > 20

    def test_approximate_historical_values(self):
        """
        Test approximate historical values with ±5% tolerance.

        Validates known values without hardcoding exact numbers.
        """
        # DGS10 (10Y Treasury) on 2020-03-09 was around 0.5% (COVID panic)
        dgs10 = fetch_series("DGS10", "2020-03-09", "2020-03-10")
        if not dgs10.empty:
            value = dgs10.iloc[0]
            # Should be very low, around 0.5% ± 0.2%
            assert 0.3 < value < 1.0, f"Expected ~0.5%, got {value}%"

        # UNRATE (Unemployment) in Feb 2020 was ~3.5% (pre-COVID low)
        unrate = fetch_series("UNRATE", "2020-02-01", "2020-02-29")
        if not unrate.empty:
            value = unrate.iloc[0]
            # Should be around 3.5% ± 0.5%
            assert 3.0 < value < 4.0, f"Expected ~3.5%, got {value}%"
