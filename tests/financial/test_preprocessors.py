"""
Tests for financial data preprocessors.

This test suite validates mathematical correctness of returns, volatility,
normalization, and windowing calculations against known results.
"""

import numpy as np
import pandas as pd
import pytest

from financial_tda.data.preprocessors import normalization, returns, windowing


class TestReturnsCalculations:
    """Test suite for returns calculations."""

    def test_log_returns_known_sequence(self):
        """Test log returns against known mathematical results."""
        # Known sequence: 100 -> 105 -> 103 -> 108
        prices = pd.Series([100, 105, 103, 108])

        log_rets = returns.compute_log_returns(prices)

        # Expected: log(105/100), log(103/105), log(108/103)
        expected = pd.Series(
            [
                np.nan,
                np.log(105 / 100),
                np.log(103 / 105),
                np.log(108 / 103),
            ]
        )

        pd.testing.assert_series_equal(log_rets, expected, check_names=False)

    def test_simple_returns_known_sequence(self):
        """Test simple returns against known mathematical results."""
        prices = pd.Series([100, 105, 103, 108])

        simple_rets = returns.compute_simple_returns(prices)

        # Expected: (105-100)/100, (103-105)/105, (108-103)/103
        expected = pd.Series([np.nan, 0.05, -0.019047619047619046, 0.04854368932038835])

        pd.testing.assert_series_equal(simple_rets, expected, check_names=False)

    def test_cumulative_returns_roundtrip(self):
        """Test that cumulative returns can reconstruct price series."""
        # Start with prices, compute returns, then cumulative
        prices = pd.Series([100, 105, 103, 108, 110])
        simple_rets = returns.compute_simple_returns(prices)
        cum_rets = returns.compute_cumulative_returns(simple_rets, log_returns=False)

        # Cumulative returns should match price changes from first price
        # cum_ret = (final_price / initial_price) - 1
        expected_cum = (prices / prices.iloc[0]) - 1

        pd.testing.assert_series_equal(
            cum_rets, expected_cum, check_names=False, rtol=1e-10
        )

    def test_cumulative_log_returns(self):
        """Test cumulative log returns calculation."""
        log_rets = pd.Series([0.0, 0.05, -0.02, 0.03])
        cum_rets = returns.compute_cumulative_returns(log_rets, log_returns=True)

        # For log returns: cum_return = exp(sum(log_returns)) - 1
        expected = np.exp(log_rets.fillna(0).cumsum()) - 1

        pd.testing.assert_series_equal(cum_rets, expected, check_names=False)

    def test_returns_dataframe_input(self):
        """Test that returns functions work with DataFrame input."""
        prices = pd.DataFrame({"AAPL": [100, 105, 103], "GOOGL": [2000, 2050, 2030]})

        log_rets = returns.compute_log_returns(prices)
        simple_rets = returns.compute_simple_returns(prices)

        assert isinstance(log_rets, pd.DataFrame)
        assert isinstance(simple_rets, pd.DataFrame)
        assert list(log_rets.columns) == ["AAPL", "GOOGL"]
        assert log_rets.iloc[0].isna().all()  # First row is NaN

    def test_empty_series_handling(self):
        """Test that empty series are handled gracefully."""
        empty = pd.Series([], dtype=float)

        log_rets = returns.compute_log_returns(empty)
        simple_rets = returns.compute_simple_returns(empty)

        assert len(log_rets) == 0
        assert len(simple_rets) == 0


class TestVolatilityCalculations:
    """Test suite for volatility calculations."""

    def test_rolling_volatility_known_variance(self):
        """Test rolling volatility with synthetic data of known variance."""
        # Generate returns with known std (0.02 daily)
        np.random.seed(42)
        daily_std = 0.02
        rets = pd.Series(np.random.randn(100) * daily_std)

        vol = returns.compute_rolling_volatility(rets, window=50, annualize=False)

        # Rolling vol should converge to true std (0.02)
        assert abs(vol.iloc[-1] - daily_std) < 0.005  # Within 0.5%

    def test_volatility_annualization(self):
        """Test that annualization factor is correctly applied."""
        np.random.seed(42)
        rets = pd.Series(np.random.randn(100) * 0.01)

        vol_daily = returns.compute_rolling_volatility(
            rets, window=20, annualize=False, periods_per_year=252
        )
        vol_annual = returns.compute_rolling_volatility(
            rets, window=20, annualize=True, periods_per_year=252
        )

        # Annual vol should be daily vol * sqrt(252)
        expected_annual = vol_daily * np.sqrt(252)
        pd.testing.assert_series_equal(
            vol_annual, expected_annual, check_names=False, rtol=1e-10
        )

    def test_ewma_volatility_responsiveness(self):
        """Test that EWMA volatility responds to regime changes."""
        # Create returns with two regimes: low vol then high vol
        low_vol_returns = pd.Series(np.random.randn(50) * 0.01)
        high_vol_returns = pd.Series(np.random.randn(50) * 0.03)
        rets = pd.concat([low_vol_returns, high_vol_returns], ignore_index=True)

        ewma_vol = returns.compute_ewma_volatility(rets, span=20, annualize=False)

        # EWMA vol in second half should be higher than first half
        assert ewma_vol.iloc[-10:].mean() > ewma_vol.iloc[30:40].mean()

    def test_realized_volatility_parkinson(self):
        """Test Parkinson realized volatility estimator."""
        # Create synthetic OHLC data
        np.random.seed(42)
        n = 100
        close = pd.Series(100 + np.cumsum(np.random.randn(n) * 2))
        high = close + np.random.uniform(1, 3, n)
        low = close - np.random.uniform(1, 3, n)
        open_prices = close.shift(1).fillna(close.iloc[0])

        ohlc = pd.DataFrame(
            {"Open": open_prices, "High": high, "Low": low, "Close": close}
        )

        vol = returns.compute_realized_volatility(
            ohlc, window=20, method="parkinson", annualize=False
        )

        # Vol should be positive and non-NaN after window period
        assert (vol.iloc[20:] > 0).all()
        assert not vol.iloc[20:].isna().any()

    def test_realized_volatility_garman_klass(self):
        """Test Garman-Klass realized volatility estimator."""
        np.random.seed(42)
        n = 100
        close = pd.Series(100 + np.cumsum(np.random.randn(n) * 2))
        high = close + np.random.uniform(1, 3, n)
        low = close - np.random.uniform(1, 3, n)
        open_prices = close.shift(1).fillna(close.iloc[0])

        ohlc = pd.DataFrame(
            {"Open": open_prices, "High": high, "Low": low, "Close": close}
        )

        vol = returns.compute_realized_volatility(
            ohlc, window=20, method="garman_klass", annualize=False
        )

        # Vol should be positive and non-NaN after window period
        assert (vol.iloc[20:] > 0).all()
        assert not vol.iloc[20:].isna().any()

    def test_realized_volatility_invalid_method(self):
        """Test that invalid method raises error."""
        ohlc = pd.DataFrame({"Open": [100], "High": [105], "Low": [95], "Close": [102]})

        with pytest.raises(ValueError, match="Unknown method"):
            returns.compute_realized_volatility(ohlc, window=1, method="invalid")

    def test_realized_volatility_missing_columns(self):
        """Test that missing OHLC columns raise error."""
        df = pd.DataFrame({"Close": [100, 101, 102]})

        with pytest.raises(ValueError, match="must contain columns"):
            returns.compute_realized_volatility(df, window=2)


class TestNormalization:
    """Test suite for normalization functions."""

    def test_zscore_statistical_properties(self):
        """Test that z-score normalization produces mean≈0 and std≈1."""
        data = pd.Series(np.random.randn(1000) * 10 + 50)

        normalized = normalization.normalize_zscore(data)

        assert abs(normalized.mean()) < 0.1  # Mean ≈ 0
        assert abs(normalized.std() - 1.0) < 0.1  # Std ≈ 1

    def test_minmax_range(self):
        """Test that min-max normalization produces correct range."""
        data = pd.Series([10, 20, 30, 40, 50])

        # Test [0, 1] range
        normalized = normalization.normalize_minmax(data, feature_range=(0, 1))
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0

        # Test [-1, 1] range
        normalized = normalization.normalize_minmax(data, feature_range=(-1, 1))
        assert normalized.min() == -1.0
        assert normalized.max() == 1.0

    def test_robust_outlier_resistance(self):
        """Test that robust normalization is less sensitive to outliers."""
        # Data with outlier
        data_with_outlier = pd.Series([10, 11, 12, 13, 14, 100])
        data_without_outlier = pd.Series([10, 11, 12, 13, 14, 15])

        # Z-score normalization
        zscore_with = normalization.normalize_zscore(data_with_outlier)
        zscore_without = normalization.normalize_zscore(data_without_outlier)

        # Robust normalization
        robust_with = normalization.normalize_robust(data_with_outlier)
        robust_without = normalization.normalize_robust(data_without_outlier)

        # Robust should be more similar despite outlier
        # Check normalized values for typical points (indices 0-4)
        robust_diff = abs(robust_with.iloc[:5] - robust_without.iloc[:5]).mean()
        zscore_diff = abs(zscore_with.iloc[:5] - zscore_without.iloc[:5]).mean()

        assert robust_diff < zscore_diff  # Robust is less affected

    def test_rolling_normalization(self):
        """Test rolling window normalization."""
        data = pd.Series(np.random.randn(100) * 10 + 50)

        normalized = normalization.normalize_zscore(data, window=20)

        # Check that normalized values exist after window period
        assert not normalized.iloc[20:].isna().all()
        # First values should be NaN
        assert normalized.iloc[:19].isna().all()

    def test_log_normalization(self):
        """Test log transformation."""
        data = pd.Series([1, 10, 100, 1000])

        normalized = normalization.normalize_log(data)

        expected = pd.Series([np.log(1), np.log(10), np.log(100), np.log(1000)])
        pd.testing.assert_series_equal(normalized, expected, check_names=False)

    def test_log_normalization_negative_values(self):
        """Test that log normalization raises error for negative values."""
        data = pd.Series([1, -1, 10])

        with pytest.raises(ValueError, match="requires positive values"):
            normalization.normalize_log(data)

    def test_log1p_normalization(self):
        """Test log1p transformation handles zeros."""
        data = pd.Series([0, 1, 10, 100])

        normalized = normalization.normalize_log1p(data)

        expected = pd.Series([np.log1p(0), np.log1p(1), np.log1p(10), np.log1p(100)])
        pd.testing.assert_series_equal(normalized, expected, check_names=False)

    def test_dataframe_normalization(self):
        """Test that normalization works with DataFrames."""
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [10, 20, 30, 40, 50]})

        normalized = normalization.normalize_zscore(df)

        assert isinstance(normalized, pd.DataFrame)
        assert list(normalized.columns) == ["A", "B"]
        # Each column should be normalized independently
        assert abs(normalized["A"].mean()) < 0.1
        assert abs(normalized["B"].mean()) < 0.1


class TestWindowing:
    """Test suite for windowing utilities."""

    def test_sliding_windows_count(self):
        """Test correct number of windows is created."""
        df = pd.DataFrame({"x": range(10)})

        windows = windowing.create_sliding_windows(df, window_size=3, stride=1)
        assert len(windows) == 8  # (10 - 3) / 1 + 1 = 8

        windows = windowing.create_sliding_windows(df, window_size=3, stride=2)
        assert len(windows) == 4  # (10 - 3) / 2 + 1 = 4

    def test_sliding_windows_content(self):
        """Test that windows contain correct data."""
        df = pd.DataFrame({"x": [0, 1, 2, 3, 4]})

        windows = windowing.create_sliding_windows(df, window_size=3, stride=1)

        # First window should be [0, 1, 2]
        assert list(windows[0]["x"]) == [0, 1, 2]
        # Second window should be [1, 2, 3]
        assert list(windows[1]["x"]) == [1, 2, 3]
        # Third window should be [2, 3, 4]
        assert list(windows[2]["x"]) == [2, 3, 4]

    def test_labeled_windows_last_position(self):
        """Test labeled windows with last position labeling."""
        df = pd.DataFrame({"x": [0, 1, 2, 3, 4]})
        labels = pd.Series(["a", "b", "c", "d", "e"])

        labeled = windowing.create_labeled_windows(
            df, labels, window_size=3, stride=1, label_position="last"
        )

        # First window [0,1,2] should have label 'c' (last position)
        assert labeled[0][1] == "c"
        # Second window [1,2,3] should have label 'd'
        assert labeled[1][1] == "d"

    def test_labeled_windows_first_position(self):
        """Test labeled windows with first position labeling."""
        df = pd.DataFrame({"x": [0, 1, 2, 3, 4]})
        labels = pd.Series(["a", "b", "c", "d", "e"])

        labeled = windowing.create_labeled_windows(
            df, labels, window_size=3, stride=1, label_position="first"
        )

        # First window [0,1,2] should have label 'a' (first position)
        assert labeled[0][1] == "a"
        # Second window [1,2,3] should have label 'b'
        assert labeled[1][1] == "b"

    def test_labeled_windows_middle_position(self):
        """Test labeled windows with middle position labeling."""
        df = pd.DataFrame({"x": [0, 1, 2, 3, 4]})
        labels = pd.Series(["a", "b", "c", "d", "e"])

        labeled = windowing.create_labeled_windows(
            df, labels, window_size=3, stride=1, label_position="middle"
        )

        # First window [0,1,2] should have label 'b' (middle position, idx 1)
        assert labeled[0][1] == "b"
        # Second window [1,2,3] should have label 'c'
        assert labeled[1][1] == "c"

    def test_labeled_windows_index_mismatch(self):
        """Test that mismatched indices raise error."""
        df = pd.DataFrame({"x": [0, 1, 2]})
        labels = pd.Series(["a", "b"], index=[5, 6])  # Different index

        with pytest.raises(ValueError, match="labels index must match"):
            windowing.create_labeled_windows(df, labels, window_size=2)

    def test_expanding_windows(self):
        """Test expanding windows creation."""
        df = pd.DataFrame({"x": [0, 1, 2, 3, 4]})

        windows = windowing.create_expanding_windows(
            df, min_window_size=2, max_window_size=4
        )

        assert len(windows) == 3  # Sizes 2, 3, 4
        assert len(windows[0]) == 2  # First window size 2
        assert len(windows[1]) == 3  # Second window size 3
        assert len(windows[2]) == 4  # Third window size 4

        # All windows start from beginning
        assert list(windows[0]["x"]) == [0, 1]
        assert list(windows[1]["x"]) == [0, 1, 2]
        assert list(windows[2]["x"]) == [0, 1, 2, 3]

    def test_future_window_pairs(self):
        """Test future window pairs creation."""
        df = pd.DataFrame({"x": [0, 1, 2, 3, 4, 5, 6]})

        pairs = windowing.create_future_window_pairs(
            df, window_size=3, forecast_horizon=2, stride=1
        )

        assert len(pairs) == 3  # (7 - 5) / 1 + 1 = 3

        # First pair: current [0,1,2], future [3,4]
        current, future = pairs[0]
        assert list(current["x"]) == [0, 1, 2]
        assert list(future["x"]) == [3, 4]

        # Second pair: current [1,2,3], future [4,5]
        current, future = pairs[1]
        assert list(current["x"]) == [1, 2, 3]
        assert list(future["x"]) == [4, 5]

    def test_window_size_validation(self):
        """Test that invalid window sizes raise errors."""
        df = pd.DataFrame({"x": [0, 1, 2]})

        with pytest.raises(ValueError, match="window_size must be positive"):
            windowing.create_sliding_windows(df, window_size=0)

        with pytest.raises(ValueError, match="cannot be larger than data length"):
            windowing.create_sliding_windows(df, window_size=5)

    def test_empty_dataframe_handling(self):
        """Test that empty DataFrames are handled gracefully."""
        empty_df = pd.DataFrame()

        windows = windowing.create_sliding_windows(empty_df, window_size=3)
        assert len(windows) == 0

        labeled = windowing.create_labeled_windows(
            empty_df, pd.Series(dtype=object), window_size=3
        )
        assert len(labeled) == 0
