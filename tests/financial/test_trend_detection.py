"""
Unit tests for G&K Trend Analysis Validator.

Tests the complete Gidea & Katz (2018) methodology including rolling statistics,
spectral density computation, and Kendall-tau trend analysis.
"""

import numpy as np
import pandas as pd
import pytest

from financial_tda.validation.trend_analysis_validator import (
    analyze_gk_precrash_trend,
    compute_gk_rolling_statistics,
    load_lp_norms_from_csv,
    validate_gk_event,
)


class TestComputeGKRollingStatistics:
    """Test G&K rolling statistics computation."""

    def test_basic_computation(self):
        """Test that all 6 statistics are computed."""
        norms_df = pd.DataFrame(
            {
                "L1_norm": np.random.randn(1000) + 2.0,
                "L2_norm": np.random.randn(1000) + 3.0,
            },
            index=pd.date_range("2006-01-01", periods=1000),
        )

        stats_df = compute_gk_rolling_statistics(norms_df, window_size=100)

        # Should have 6 columns (3 stats × 2 norms)
        assert len(stats_df.columns) == 6
        assert "L1_norm_variance" in stats_df.columns
        assert "L1_norm_spectral_density_low" in stats_df.columns
        assert "L1_norm_acf_lag1" in stats_df.columns
        assert "L2_norm_variance" in stats_df.columns
        assert "L2_norm_spectral_density_low" in stats_df.columns
        assert "L2_norm_acf_lag1" in stats_df.columns

        # First (window_size - 1) values should be NaN
        assert stats_df["L1_norm_variance"].iloc[:99].isna().all()
        # After window, should have values
        assert not stats_df["L1_norm_variance"].iloc[100:].isna().all()

    def test_variance_computation(self):
        """Test variance statistic."""
        # Create data with known variance
        norms_df = pd.DataFrame(
            {"L1_norm": [1.0] * 50 + [2.0] * 50, "L2_norm": [1.0] * 100},
            index=pd.date_range("2006-01-01", periods=100),
        )

        stats_df = compute_gk_rolling_statistics(norms_df, window_size=50)

        # First 49 should be NaN
        assert stats_df["L1_norm_variance"].iloc[:49].isna().all()
        # At index 49 (window 0-49), variance of [1,1,...,1] should be 0
        assert stats_df["L1_norm_variance"].iloc[49] == 0.0
        # At index 99 (window 50-99), variance of [2,2,...,2] should be 0
        assert stats_df["L1_norm_variance"].iloc[99] == 0.0

    def test_spectral_density_strong_trend(self):
        """Test spectral density on data with strong low-frequency component."""
        # Create data with strong low-frequency trend
        t = np.linspace(0, 10 * np.pi, 1000)
        low_freq_signal = np.sin(0.1 * t)  # Low frequency
        norms_df = pd.DataFrame(
            {"L1_norm": low_freq_signal, "L2_norm": low_freq_signal},
            index=pd.date_range("2006-01-01", periods=1000),
        )

        stats_df = compute_gk_rolling_statistics(norms_df, window_size=200)

        # Spectral density should be computed
        assert not stats_df["L1_norm_spectral_density_low"].iloc[200:].isna().all()
        # Should be positive
        assert (stats_df["L1_norm_spectral_density_low"].dropna() > 0).any()

    def test_acf_autocorrelated_data(self):
        """Test ACF on autocorrelated data."""
        # Create autocorrelated data (random walk)
        np.random.seed(42)
        random_walk = np.cumsum(np.random.randn(1000))
        norms_df = pd.DataFrame(
            {"L1_norm": random_walk, "L2_norm": random_walk},
            index=pd.date_range("2006-01-01", periods=1000),
        )

        stats_df = compute_gk_rolling_statistics(norms_df, window_size=200)

        # ACF lag-1 for random walk should be high (close to 1)
        acf_values = stats_df["L1_norm_acf_lag1"].dropna()
        assert (acf_values > 0.9).any(), "Random walk should have high ACF lag-1"

    def test_missing_columns_error(self):
        """Test error handling for missing columns."""
        bad_df = pd.DataFrame({"wrong_col": range(100)}, index=pd.date_range("2006-01-01", periods=100))

        with pytest.raises(ValueError, match="Missing required columns"):
            compute_gk_rolling_statistics(bad_df)

    def test_invalid_index_error(self):
        """Test error handling for non-DatetimeIndex."""
        bad_df = pd.DataFrame({"L1_norm": range(100), "L2_norm": range(100)})

        with pytest.raises(ValueError, match="DatetimeIndex"):
            compute_gk_rolling_statistics(bad_df)


class TestAnalyzeGKPrecrashTrend:
    """Test G&K pre-crash trend analysis."""

    def test_strong_upward_trend(self):
        """Test detection of strong upward trend before crisis."""
        # Create stats with strong upward trend in all metrics
        dates = pd.date_range("2006-01-01", periods=500)
        trend_data = np.linspace(1.0, 3.0, 500)

        stats_df = pd.DataFrame(
            {
                "L1_norm_variance": trend_data,
                "L1_norm_spectral_density_low": trend_data * 1.5,
                "L1_norm_acf_lag1": trend_data * 0.5,
                "L2_norm_variance": trend_data * 1.2,
                "L2_norm_spectral_density_low": trend_data * 2.0,
                "L2_norm_acf_lag1": trend_data * 0.8,
            },
            index=dates,
        )

        result = analyze_gk_precrash_trend(stats_df, "2007-06-01", days_before=250)

        # Should detect strong trend
        assert result["status"] == "PASS"
        assert result["best_tau"] > 0.90, "Perfect linear trend should have tau > 0.90"
        assert result["best_metric"] is not None
        # Any metric can win with perfect linear trend, just verify it's one of the 6
        assert result["best_metric"] in stats_df.columns

        # Check all statistics are present
        assert len(result["statistics"]) == 6
        for stat_name, stat_values in result["statistics"].items():
            assert "tau" in stat_values
            assert "p_value" in stat_values
            assert "n_samples" in stat_values
            assert stat_values["tau"] > 0.90

    def test_no_trend(self):
        """Test detection of no trend (normal conditions)."""
        np.random.seed(42)
        dates = pd.date_range("2006-01-01", periods=500)

        stats_df = pd.DataFrame(
            {
                "L1_norm_variance": np.random.randn(500) + 1.0,
                "L1_norm_spectral_density_low": np.random.randn(500) + 2.0,
                "L1_norm_acf_lag1": np.random.randn(500) * 0.1 + 0.5,
                "L2_norm_variance": np.random.randn(500) + 1.5,
                "L2_norm_spectral_density_low": np.random.randn(500) + 2.5,
                "L2_norm_acf_lag1": np.random.randn(500) * 0.1 + 0.6,
            },
            index=dates,
        )

        result = analyze_gk_precrash_trend(stats_df, "2007-06-01", days_before=250)

        # Should not detect strong trend
        assert result["status"] == "FAIL"
        assert abs(result["best_tau"]) < 0.30, "Random data should have weak tau"

    def test_window_size_handling(self):
        """Test that window size is properly extracted."""
        dates = pd.date_range("2006-01-01", periods=500)
        stats_df = pd.DataFrame(
            {
                "L1_norm_variance": np.linspace(1, 2, 500),
                "L2_norm_variance": np.linspace(1, 2, 500),
                "L1_norm_spectral_density_low": np.linspace(1, 2, 500),
                "L2_norm_spectral_density_low": np.linspace(1, 2, 500),
                "L1_norm_acf_lag1": np.linspace(0.5, 0.8, 500),
                "L2_norm_acf_lag1": np.linspace(0.5, 0.8, 500),
            },
            index=dates,
        )

        result = analyze_gk_precrash_trend(stats_df, "2007-06-01", days_before=100)

        assert result["days_requested"] == 100
        assert result["n_observations"] <= 100

    def test_timezone_handling(self):
        """Test timezone-aware datetime handling."""
        dates = pd.date_range("2006-01-01", periods=500, tz="America/New_York")
        stats_df = pd.DataFrame(
            {
                "L1_norm_variance": np.linspace(1, 2, 500),
                "L2_norm_variance": np.linspace(1, 2, 500),
                "L1_norm_spectral_density_low": np.linspace(1, 2, 500),
                "L2_norm_spectral_density_low": np.linspace(1, 2, 500),
                "L1_norm_acf_lag1": np.linspace(0.5, 0.8, 500),
                "L2_norm_acf_lag1": np.linspace(0.5, 0.8, 500),
            },
            index=dates,
        )

        # Should handle timezone-naive crisis date
        result = analyze_gk_precrash_trend(stats_df, "2007-06-01")
        assert result["status"] == "PASS"


class TestValidateGKEvent:
    """Test complete G&K validation workflow."""

    def test_full_workflow(self):
        """Test complete validation workflow from norms to results."""
        # Create synthetic L^p norms with upward trend
        norms_df = pd.DataFrame(
            {
                "L1_norm": np.linspace(1.0, 2.0, 1000) + np.random.randn(1000) * 0.1,
                "L2_norm": np.linspace(1.5, 3.0, 1000) + np.random.randn(1000) * 0.15,
            },
            index=pd.date_range("2006-01-01", periods=1000),
        )

        result = validate_gk_event(
            norms_df,
            event_name="Test Crisis",
            crisis_date="2008-09-15",
            rolling_window=200,
            precrash_window=100,
        )

        # Check structure
        assert result["event_name"] == "Test Crisis"
        assert result["crisis_date"] == "2008-09-15"
        assert result["rolling_window_size"] == 200
        assert result["precrash_window_size"] == 100
        assert "statistics" in result
        assert "best_metric" in result
        assert "best_tau" in result
        assert "status" in result


class TestLoadLpNormsFromCSV:
    """Test CSV loading functionality."""

    def test_successful_load(self, tmp_path):
        """Test successful loading of valid CSV."""
        norms_df = pd.DataFrame(
            {"L1_norm": [1.0, 2.0, 3.0], "L2_norm": [1.5, 2.5, 3.5]},
            index=pd.date_range("2008-01-01", periods=3),
        )

        csv_file = tmp_path / "norms.csv"
        norms_df.to_csv(csv_file)

        loaded_df = load_lp_norms_from_csv(csv_file)

        assert len(loaded_df) == 3
        assert "L1_norm" in loaded_df.columns
        assert "L2_norm" in loaded_df.columns
        assert isinstance(loaded_df.index, pd.DatetimeIndex)
        assert np.allclose(loaded_df["L1_norm"].values, [1.0, 2.0, 3.0])

    def test_file_not_found(self, tmp_path):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            load_lp_norms_from_csv(tmp_path / "nonexistent.csv")

    def test_missing_columns(self, tmp_path):
        """Test error handling for missing required columns."""
        bad_df = pd.DataFrame({"wrong_col": [1, 2, 3]})
        csv_file = tmp_path / "bad.csv"
        bad_df.to_csv(csv_file)

        with pytest.raises(ValueError, match="Missing required columns"):
            load_lp_norms_from_csv(csv_file)
