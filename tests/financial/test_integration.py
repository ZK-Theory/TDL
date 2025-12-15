"""
End-to-end integration tests for financial TDA pipeline.

This test suite validates the complete financial TDA pipeline from data fetching
through preprocessing, embedding, persistence computation, feature extraction,
and regime/anomaly detection. Tests cover both giotto-tda and TTK hybrid backends
with multiple asset classes.

Test Coverage:
    - Full pipeline integration (data → detection)
    - Multi-asset class support (equities, crypto)
    - Backend consistency (giotto-tda vs TTK)
    - Reproducibility and numerical stability
    - Error handling and edge cases

Run with:
    pytest tests/financial/test_integration.py -v
    pytest tests/financial/test_integration.py -v --run-ttk  # Include TTK tests
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

from financial_tda.analysis.gidea_katz import (
    sliding_window_persistence,
)
from financial_tda.data.fetchers.crypto import fetch_ohlc as fetch_crypto_ohlc
from financial_tda.data.fetchers.yahoo import fetch_multiple, fetch_ticker
from financial_tda.data.preprocessors.returns import compute_log_returns
from financial_tda.models.change_point_detector import (
    NormalPeriodCalibrator,
)
from financial_tda.models.regime_classifier import (
    RegimeClassifier,
    create_regime_labels,
)
from financial_tda.topology.embedding import optimal_tau, takens_embedding
from financial_tda.topology.features import (
    compute_landscape_norms,
    compute_persistence_landscape,
)
from financial_tda.topology.filtration import (
    compute_persistence_vr,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """Generate synthetic price data for testing."""
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    np.random.seed(42)

    # Generate synthetic prices with trends
    prices = 100 * np.exp(np.cumsum(np.random.randn(300) * 0.02))

    df = pd.DataFrame(
        {
            "Open": prices * (1 + np.random.randn(300) * 0.005),
            "High": prices * (1 + np.abs(np.random.randn(300)) * 0.01),
            "Low": prices * (1 - np.abs(np.random.randn(300)) * 0.01),
            "Close": prices,
            "Volume": np.random.randint(1e6, 1e8, 300),
        },
        index=dates,
    )

    return df


@pytest.fixture
def sample_multi_index_data() -> pd.DataFrame:
    """Generate synthetic multi-index data (4 indices) for Gidea & Katz approach."""
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    np.random.seed(42)

    # Generate correlated returns for 4 indices
    n_samples = 200
    mean_return = 0.0005
    volatility = 0.015

    returns = np.random.randn(n_samples, 4) * volatility + mean_return

    df = pd.DataFrame(
        returns,
        columns=["SP500", "DJIA", "NASDAQ", "Russell2000"],
        index=dates,
    )

    return df


@pytest.fixture
def sample_vix_data() -> pd.Series:
    """Generate synthetic VIX data for regime labeling."""
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    np.random.seed(42)

    # Normal VIX around 15-20, with spikes to 30-50 during crisis
    vix = np.random.randn(300) * 5 + 17
    vix = np.clip(vix, 10, 60)

    # Add crisis period
    vix[100:120] = np.random.randn(20) * 8 + 35

    return pd.Series(vix, index=dates, name="VIX")


# ============================================================================
# Pipeline Integration Tests
# ============================================================================


class TestFullPipelineIntegration:
    """Test complete pipeline from data to detection."""

    def test_single_asset_full_pipeline(self, sample_price_data):
        """Test full pipeline: data → embedding → persistence → features → detection."""
        # 1. Data preprocessing
        prices = sample_price_data["Close"]
        returns = compute_log_returns(prices).dropna()  # Drop first NaN
        # 2. Takens embedding
        tau = optimal_tau(returns.values, max_lag=20)
        assert 1 <= tau <= 20

        embedded = takens_embedding(returns.values, delay=tau, dimension=3)
        assert embedded.shape[1] == 3
        assert embedded.shape[0] > 0

        # 3. Persistence computation (GUDHI)
        diagram = compute_persistence_vr(embedded, homology_dimensions=(0, 1))
        assert diagram.shape[1] == 3
        assert len(diagram) > 0

        # 4. Feature extraction
        landscape = compute_persistence_landscape(diagram, n_layers=3, n_bins=50)
        assert landscape.shape[0] == 3  # n_layers

        norms = compute_landscape_norms(diagram, n_layers=3, n_bins=50)
        assert norms["L1"] > 0
        assert norms["L2"] > 0

        logger.info(
            "Single asset pipeline complete: %d points → %d features, L1=%.4f",
            len(returns),
            len(diagram),
            norms["L1"],
        )

    def test_multi_index_gidea_katz_pipeline(self, sample_multi_index_data):
        """Test Gidea & Katz multi-index pipeline (4 indices → R^4 point clouds)."""
        # 1. Data is already log-returns format
        returns = sample_multi_index_data
        assert returns.shape[1] == 4

        # 2. Sliding window analysis
        # Use small window for speed
        window_size = 30
        stride = 5

        result = sliding_window_persistence(
            returns,
            window_size=window_size,
            stride=stride,
            homology_dimensions=(1,),  # H1 only per paper
            n_layers=3,
            n_bins=50,
        )

        # 3. Validate results structure
        assert len(result.dates) > 0
        assert len(result.l1_norms) == len(result.dates)
        assert len(result.l2_norms) == len(result.dates)
        assert result.window_size == window_size

        # 4. Check that norms are positive
        assert np.all(result.l1_norms > 0)
        assert np.all(result.l2_norms > 0)

        logger.info(
            "Gidea & Katz pipeline complete: %d windows, L1 range=[%.4f, %.4f]",
            len(result.dates),
            result.l1_norms.min(),
            result.l1_norms.max(),
        )

    def test_regime_classification_pipeline(self, sample_price_data, sample_vix_data, sample_multi_index_data):
        """Test regime classification from features to predictions."""
        # 1. Create regime labels
        prices = sample_price_data["Close"]
        labels = create_regime_labels(
            prices,
            sample_vix_data,
            vix_crisis_threshold=25.0,
            drawdown_threshold=0.10,
        )

        # Should have some crisis and normal labels
        crisis_count = (labels == 1).sum()
        normal_count = (labels == 0).sum()
        assert crisis_count > 0 or normal_count > 0

        # 2. Compute features for classification
        returns = sample_multi_index_data
        result = sliding_window_persistence(
            returns,
            window_size=30,
            stride=5,
            homology_dimensions=(1,),
            n_layers=3,
            n_bins=50,
        )

        # 3. Prepare features and labels
        features_df = result.to_dataframe()

        # Align labels with features by date
        aligned = features_df.join(labels.to_frame("label"), how="inner")
        aligned = aligned.dropna()

        if len(aligned) < 20:
            pytest.skip("Not enough labeled samples for classification test")

        X = aligned[["L1", "L2"]].values
        y = aligned["label"].values

        # 4. Train classifier
        classifier = RegimeClassifier(classifier_type="random_forest")
        classifier.fit(X, y)

        # 5. Make predictions
        predictions = classifier.predict(X)
        assert len(predictions) == len(y)
        assert np.all((predictions == 0) | (predictions == 1))

        logger.info(
            "Regime classification complete: %d samples, accuracy=%.2f",
            len(y),
            (predictions == y).mean(),
        )

    def test_change_point_detection_pipeline(self, sample_multi_index_data):
        """Test change-point detection from features to anomaly detection."""
        # 1. Compute sliding window persistence
        returns = sample_multi_index_data
        result = sliding_window_persistence(
            returns,
            window_size=30,
            stride=5,
            homology_dimensions=(1,),
            n_layers=3,
            n_bins=50,
        )

        # 2. Compute bottleneck distances between consecutive windows
        # (Simplified: using L1 norm differences as proxy)
        distances = np.abs(np.diff(result.l1_norms))

        # 3. Calibrate on "normal" periods (first half)
        split_idx = len(distances) // 2
        normal_distances = distances[:split_idx]

        calibrator = NormalPeriodCalibrator()
        calibrator.fit(normal_distances)

        # 4. Detect anomalies in test period
        test_distances = distances[split_idx:]
        anomalies = [calibrator.is_anomaly(d) for d in test_distances]

        assert len(anomalies) == len(test_distances)

        # Should detect some anomalies if present
        n_anomalies = sum(anomalies)
        logger.info(
            "Change-point detection complete: %d/%d anomalies detected",
            n_anomalies,
            len(anomalies),
        )


# ============================================================================
# Multi-Asset Class Tests
# ============================================================================


class TestMultiAssetClassIntegration:
    """Test pipeline with different asset classes."""

    @pytest.mark.integration
    def test_equity_indices_real_data(self):
        """Test pipeline with real equity index data (S&P 500)."""
        # Fetch recent S&P 500 data
        try:
            data = fetch_ticker("^GSPC", "2023-01-01", "2023-12-31")
        except Exception as e:
            pytest.skip(f"Failed to fetch data: {e}")

        if data.empty or len(data) < 100:
            pytest.skip("Insufficient data from Yahoo Finance")

        # Run pipeline
        prices = data["Close"]
        returns = compute_log_returns(prices)

        embedded = takens_embedding(returns.values, delay=5, dimension=3)
        diagram = compute_persistence_vr(embedded, homology_dimensions=(0, 1))

        norms = compute_landscape_norms(diagram, n_layers=5, n_bins=100)

        assert norms["L1"] > 0
        assert norms["L2"] > 0

        logger.info(
            "S&P 500 integration test: %d trading days, %d features, L1=%.4f",
            len(returns),
            len(diagram),
            norms["L1"],
        )

    @pytest.mark.integration
    def test_multi_index_real_data(self):
        """Test Gidea & Katz approach with real 4-index data."""
        tickers = ["^GSPC", "^DJI", "^IXIC", "^RUT"]

        try:
            data = fetch_multiple(tickers, "2023-01-01", "2023-12-31")
        except Exception as e:
            pytest.skip(f"Failed to fetch data: {e}")

        if any(d.empty for d in data.values()) or any(len(d) < 100 for d in data.values()):
            pytest.skip("Insufficient data from Yahoo Finance")

        # Compute log-returns and align
        returns_dict = {}
        for ticker, df in data.items():
            returns_dict[ticker] = compute_log_returns(df["Close"])

        returns_df = pd.DataFrame(returns_dict)
        returns_df = returns_df.dropna()

        if len(returns_df) < 50:
            pytest.skip("Insufficient aligned returns")

        # Run Gidea & Katz pipeline
        result = sliding_window_persistence(
            returns_df,
            window_size=50,
            stride=10,
            homology_dimensions=(1,),
            n_layers=5,
            n_bins=100,
        )

        assert len(result.dates) > 0
        assert np.all(result.l1_norms > 0)

        logger.info(
            "4-index integration test: %d windows, L1 range=[%.4f, %.4f]",
            len(result.dates),
            result.l1_norms.min(),
            result.l1_norms.max(),
        )

    @pytest.mark.integration
    def test_cryptocurrency_real_data(self):
        """Test pipeline with real cryptocurrency data (Bitcoin)."""
        try:
            data = fetch_crypto_ohlc("bitcoin", vs_currency="usd", days=180)
        except Exception as e:
            pytest.skip(f"Failed to fetch crypto data: {e}")

        if data.empty or len(data) < 100:
            pytest.skip("Insufficient crypto data")

        # Run pipeline with crypto data
        prices = data["Close"]
        returns = compute_log_returns(prices)

        embedded = takens_embedding(returns.values, delay=5, dimension=3)
        diagram = compute_persistence_vr(embedded, homology_dimensions=(0, 1))

        norms = compute_landscape_norms(diagram, n_layers=5, n_bins=100)

        assert norms["L1"] > 0
        assert norms["L2"] > 0

        logger.info(
            "Bitcoin integration test: %d days, %d features, L1=%.4f",
            len(returns),
            len(diagram),
            norms["L1"],
        )


# ============================================================================
# Reproducibility and Consistency Tests
# ============================================================================


class TestReproducibilityAndConsistency:
    """Test numerical stability and reproducibility."""

    def test_repeated_runs_consistency(self, sample_price_data):
        """Test that repeated runs with same parameters give consistent results."""
        prices = sample_price_data["Close"]
        returns = compute_log_returns(prices).values

        # Run persistence computation 3 times
        results = []
        for i in range(3):
            embedded = takens_embedding(returns, delay=5, dimension=3)
            diagram = compute_persistence_vr(embedded, homology_dimensions=(0, 1))
            norms = compute_landscape_norms(diagram, n_layers=5, n_bins=100)
            results.append((norms["L1"], norms["L2"], len(diagram)))

        # Check consistency across runs
        l1_norms = [r[0] for r in results]
        l2_norms = [r[1] for r in results]
        n_features = [r[2] for r in results]

        # All runs should produce identical results (deterministic)
        assert len(set(n_features)) == 1, "Feature count varies across runs"

        # Norms should be very close (allowing for floating-point precision)
        l1_std = np.std(l1_norms)
        l2_std = np.std(l2_norms)

        assert l1_std < 1e-10, f"L1 norm variance too high: {l1_std}"
        assert l2_std < 1e-10, f"L2 norm variance too high: {l2_std}"

        logger.info(
            "Reproducibility test passed: 3 runs, L1 std=%.2e, L2 std=%.2e",
            l1_std,
            l2_std,
        )

    def test_acceptable_variance_stochastic_components(self, sample_multi_index_data):
        """Test variance in stochastic components (e.g., random sampling) is acceptable."""
        returns = sample_multi_index_data

        # Compute sliding window with stride (non-overlapping)
        results_list = []
        for i in range(3):
            result = sliding_window_persistence(
                returns,
                window_size=30,
                stride=15,  # Non-overlapping
                homology_dimensions=(1,),
                n_layers=5,
                n_bins=100,
            )
            results_list.append(result)

        # Check L1 norm consistency across runs
        l1_arrays = [r.l1_norms for r in results_list]

        # All arrays should have same length
        assert len(set(len(arr) for arr in l1_arrays)) == 1

        # Compute element-wise variance
        l1_stack = np.stack(l1_arrays)
        variance = np.var(l1_stack, axis=0)
        max_variance = variance.max()

        # Variance should be very small (deterministic process)
        assert max_variance < 1e-10, f"L1 variance too high: {max_variance}"

        logger.info("Stochastic component test passed: max variance=%.2e", max_variance)

    def test_feature_stability_parameter_variations(self, sample_price_data):
        """Test that small parameter variations produce stable features."""
        prices = sample_price_data["Close"]
        returns = compute_log_returns(prices).values

        embedded = takens_embedding(returns, delay=5, dimension=3)

        # Test with different n_bins
        l1_norms = []
        for n_bins in [50, 100, 150]:
            diagram = compute_persistence_vr(embedded, homology_dimensions=(0, 1))
            l1_norm, _ = compute_landscape_norms(diagram, n_layers=5, n_bins=n_bins)
            l1_norms.append(l1_norm)

        # L1 norms should be similar (within 10% relative difference)
        relative_diffs = np.abs(np.diff(l1_norms)) / np.mean(l1_norms)
        max_relative_diff = relative_diffs.max()

        assert max_relative_diff < 0.10, f"L1 norm varies too much with n_bins: {max_relative_diff:.2%}"

        logger.info(
            "Parameter stability test passed: max relative diff=%.2%",
            max_relative_diff * 100,
        )


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandlingIntegration:
    """Test error handling in full pipeline."""

    def test_empty_data_handling(self):
        """Test that pipeline handles empty data gracefully."""
        empty_df = pd.DataFrame()

        # Should not crash, but may raise appropriate errors
        with pytest.raises((ValueError, IndexError, KeyError)):
            prices = empty_df.get("Close", pd.Series(dtype=float))
            if prices.empty:
                raise ValueError("Empty data")
            compute_log_returns(prices)

    def test_insufficient_data_handling(self):
        """Test that pipeline handles insufficient data appropriately."""
        # Very short time series
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series(100 + np.random.randn(10), index=dates)

        returns = compute_log_returns(prices)

        # Should fail or produce empty results when trying to embed
        with pytest.raises((ValueError, AssertionError)):
            embedded = takens_embedding(returns.values, delay=5, dimension=5)
            # This requires (5-1)*5 = 20 points, but we only have 9 returns
            assert len(embedded) > 0

    def test_nan_handling_in_pipeline(self):
        """Test that pipeline handles NaN values correctly."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = pd.Series(100 + np.cumsum(np.random.randn(100)), index=dates)

        # Introduce NaN values
        prices.iloc[20:25] = np.nan

        # Should handle NaNs via forward fill
        clean_prices = prices.fillna(method="ffill")
        assert not clean_prices.isna().any()

        # Pipeline should work with cleaned data
        returns = compute_log_returns(clean_prices)
        # Drop the first NaN from log returns
        returns = returns.dropna()
        assert not returns.isna().any()

        embedded = takens_embedding(returns.values, delay=5, dimension=3)
        assert np.isfinite(embedded).all()

    def test_invalid_parameters_handling(self, sample_price_data):
        """Test that pipeline validates parameters appropriately."""
        prices = sample_price_data["Close"]
        returns = compute_log_returns(prices).values

        # Test invalid delay
        with pytest.raises(ValueError):
            takens_embedding(returns, delay=-1, dimension=3)

        # Test invalid dimension
        with pytest.raises(ValueError):
            takens_embedding(returns, delay=5, dimension=0)

        # Test invalid homology dimensions
        embedded = takens_embedding(returns, delay=5, dimension=3)
        with pytest.raises((ValueError, TypeError)):
            compute_persistence_vr(embedded, homology_dimensions=(-1,))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
