"""
Tests for Takens delay embedding implementation.

This test suite validates mathematical correctness of Takens embedding,
optimal tau selection via mutual information, and optimal dimension
selection via false nearest neighbors.
"""

import numpy as np
import pytest
from scipy.integrate import odeint

from financial_tda.topology.embedding import (
    optimal_dimension,
    optimal_tau,
    takens_embedding,
)


class TestTakensEmbedding:
    """Test suite for Takens delay embedding."""

    def test_embedding_shape_basic(self):
        """Test that embedding produces correct output shape."""
        ts = np.arange(100, dtype=np.float64)
        delay = 3
        dimension = 4

        embedded = takens_embedding(ts, delay=delay, dimension=dimension)

        # n_embedded = n_samples - (dimension - 1) * delay
        expected_n_embedded = 100 - (4 - 1) * 3  # 100 - 9 = 91
        assert embedded.shape == (expected_n_embedded, dimension)

    def test_embedding_shape_various_params(self):
        """Test embedding shape for various delay and dimension values."""
        ts = np.random.randn(500)

        test_cases = [
            (1, 2),  # Minimal delay and dimension
            (5, 3),  # Typical financial parameters
            (10, 5),  # Larger parameters
            (2, 10),  # Higher dimension
        ]

        for delay, dimension in test_cases:
            embedded = takens_embedding(ts, delay=delay, dimension=dimension)
            expected_rows = 500 - (dimension - 1) * delay
            assert embedded.shape == (expected_rows, dimension), (
                f"Failed for delay={delay}, dimension={dimension}"
            )

    def test_embedding_values_correctness(self):
        """Test that embedding vectors contain correct values."""
        # Simple sequence for easy verification
        ts = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        delay = 2
        dimension = 3

        embedded = takens_embedding(ts, delay=delay, dimension=dimension)

        # First vector: [x(0), x(2), x(4)] = [1, 3, 5]
        np.testing.assert_array_equal(embedded[0], [1.0, 3.0, 5.0])

        # Second vector: [x(1), x(3), x(5)] = [2, 4, 6]
        np.testing.assert_array_equal(embedded[1], [2.0, 4.0, 6.0])

        # Last vector: [x(5), x(7), x(9)] = [6, 8, 10]
        np.testing.assert_array_equal(embedded[-1], [6.0, 8.0, 10.0])

    def test_embedding_delay_one(self):
        """Test embedding with delay=1 (consecutive samples)."""
        ts = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        embedded = takens_embedding(ts, delay=1, dimension=3)

        # Should produce sliding window
        expected = np.array(
            [
                [1.0, 2.0, 3.0],
                [2.0, 3.0, 4.0],
                [3.0, 4.0, 5.0],
            ]
        )
        np.testing.assert_array_equal(embedded, expected)

    def test_embedding_preserves_dtype(self):
        """Test that embedding preserves float64 dtype."""
        ts = np.array([1, 2, 3, 4, 5], dtype=np.float32)
        embedded = takens_embedding(ts, delay=1, dimension=2)

        # Should convert to float64
        assert embedded.dtype == np.float64

    def test_embedding_rejects_2d_input(self):
        """Test that 2D input raises ValueError."""
        ts = np.array([[1, 2], [3, 4]])

        with pytest.raises(ValueError, match="must be 1D"):
            takens_embedding(ts, delay=1, dimension=2)

    def test_embedding_rejects_invalid_delay(self):
        """Test that invalid delay values raise appropriate errors."""
        ts = np.arange(100.0)

        with pytest.raises(ValueError, match="delay must be >= 1"):
            takens_embedding(ts, delay=0, dimension=3)

        with pytest.raises(ValueError, match="delay must be >= 1"):
            takens_embedding(ts, delay=-1, dimension=3)

        with pytest.raises(TypeError, match="delay must be an integer"):
            takens_embedding(ts, delay=1.5, dimension=3)

    def test_embedding_rejects_invalid_dimension(self):
        """Test that invalid dimension values raise appropriate errors."""
        ts = np.arange(100.0)

        with pytest.raises(ValueError, match="dimension must be >= 2"):
            takens_embedding(ts, delay=1, dimension=1)

        with pytest.raises(ValueError, match="dimension must be >= 2"):
            takens_embedding(ts, delay=1, dimension=0)

        with pytest.raises(TypeError, match="dimension must be an integer"):
            takens_embedding(ts, delay=1, dimension=2.5)

    def test_embedding_rejects_short_series(self):
        """Test that too-short series raises ValueError."""
        ts = np.array([1.0, 2.0, 3.0])

        # Need at least (dimension-1)*delay + 1 = 4*2 + 1 = 9 samples
        with pytest.raises(ValueError, match="Time series too short"):
            takens_embedding(ts, delay=2, dimension=5)

    def test_embedding_rejects_nan_values(self):
        """Test that NaN values raise ValueError."""
        ts = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0])

        with pytest.raises(ValueError, match="non-finite values"):
            takens_embedding(ts, delay=1, dimension=2)

    def test_embedding_rejects_inf_values(self):
        """Test that Inf values raise ValueError."""
        ts = np.array([1.0, 2.0, np.inf, 4.0, 5.0, 6.0, 7.0, 8.0])

        with pytest.raises(ValueError, match="non-finite values"):
            takens_embedding(ts, delay=1, dimension=2)


class TestOptimalTau:
    """Test suite for optimal tau selection via mutual information."""

    def test_tau_sinusoidal_period_20(self):
        """Test tau detection on sinusoidal signal with period 20."""
        # Sinusoidal signal: optimal tau should be approximately period/4
        period = 20
        t = np.arange(500)
        signal = np.sin(2 * np.pi * t / period)

        tau = optimal_tau(signal, max_lag=30)

        # Expected tau = period/4 = 5, allow ±2 tolerance
        assert 3 <= tau <= 7, f"Expected tau≈5 for period={period}, got {tau}"

    def test_tau_sinusoidal_period_40(self):
        """Test tau detection on sinusoidal signal with period 40."""
        period = 40
        t = np.arange(800)
        signal = np.sin(2 * np.pi * t / period)

        tau = optimal_tau(signal, max_lag=50)

        # Expected tau = period/4 = 10, allow ±3 tolerance
        assert 7 <= tau <= 13, f"Expected tau≈10 for period={period}, got {tau}"

    def test_tau_noisy_sinusoid(self):
        """Test tau detection on noisy sinusoidal signal."""
        np.random.seed(42)
        period = 20
        t = np.arange(1000)
        signal = np.sin(2 * np.pi * t / period) + 0.3 * np.random.randn(len(t))

        tau = optimal_tau(signal, max_lag=30, sigma=2.0)

        # More lenient bounds due to noise
        assert 2 <= tau <= 10, f"Expected tau≈5 for noisy signal, got {tau}"

    def test_tau_returns_mi_curve(self):
        """Test that return_mi_curve=True returns MI values."""
        t = np.arange(200)
        signal = np.sin(2 * np.pi * t / 20)

        result = optimal_tau(signal, max_lag=20, return_mi_curve=True)

        assert isinstance(result, tuple)
        tau, mi_curve = result
        assert isinstance(tau, (int, np.integer))
        assert isinstance(mi_curve, np.ndarray)
        assert len(mi_curve) == 20  # max_lag values

    def test_tau_mi_curve_decreasing_initially(self):
        """Test that MI curve generally decreases from lag=1 for periodic signals."""
        t = np.arange(500)
        signal = np.sin(2 * np.pi * t / 20)

        _, mi_curve = optimal_tau(signal, max_lag=30, return_mi_curve=True)

        # MI should decrease from first value to minimum
        assert mi_curve[0] > mi_curve.min(), "MI should decrease from initial value"

    def test_tau_global_minimum_method(self):
        """Test global minimum method for tau selection."""
        t = np.arange(500)
        signal = np.sin(2 * np.pi * t / 20)

        tau_first = optimal_tau(signal, max_lag=30, method="first_minimum")
        tau_global = optimal_tau(signal, max_lag=30, method="global_minimum")

        # Both methods should give reasonable results
        assert 1 <= tau_first <= 30
        assert 1 <= tau_global <= 30

    def test_tau_different_smoothing_methods(self):
        """Test different smoothing methods produce valid results."""
        t = np.arange(500)
        signal = np.sin(2 * np.pi * t / 20)

        tau_gaussian = optimal_tau(signal, max_lag=30, smoothing="gaussian")
        tau_ma = optimal_tau(signal, max_lag=30, smoothing="moving_average")
        tau_none = optimal_tau(signal, max_lag=30, smoothing="none")

        # All should produce valid tau values
        for tau in [tau_gaussian, tau_ma, tau_none]:
            assert 1 <= tau <= 30

    def test_tau_rejects_short_series(self):
        """Test that short series raises ValueError."""
        ts = np.arange(30.0)

        with pytest.raises(ValueError, match="too short"):
            optimal_tau(ts, max_lag=50)

    def test_tau_rejects_nan_values(self):
        """Test that NaN values raise ValueError."""
        ts = np.arange(100.0)
        ts[50] = np.nan

        with pytest.raises(ValueError, match="non-finite values"):
            optimal_tau(ts, max_lag=20)

    def test_tau_max_lag_constraint(self):
        """Test that max_lag is constrained to n/5."""
        ts = np.arange(100.0)

        # Should warn and reduce max_lag
        with pytest.warns(UserWarning, match="too large"):
            tau = optimal_tau(ts, max_lag=50)

        # Should still return valid tau
        assert 1 <= tau <= 19  # max_lag reduced to < 100/5 = 20


class TestOptimalDimension:
    """Test suite for optimal dimension selection via FNN."""

    @pytest.fixture
    def lorenz_data(self):
        """Generate Lorenz attractor x-coordinate data."""

        def lorenz(state, t, sigma=10, rho=28, beta=8 / 3):
            x, y, z = state
            return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

        t = np.linspace(0, 50, 5000)
        sol = odeint(lorenz, [1, 1, 1], t)
        return sol[:, 0]  # x-coordinate

    def test_dimension_lorenz_attractor(self, lorenz_data):
        """Test dimension detection on Lorenz attractor (known d=3)."""
        # Lorenz attractor has dimension ~2.06, so embedding dimension should be 3
        dim = optimal_dimension(lorenz_data, delay=10, max_dim=8, fnn_threshold=0.01)

        # Should identify dimension 3 (allowing some tolerance)
        assert 2 <= dim <= 4, f"Expected dim≈3 for Lorenz, got {dim}"

    def test_dimension_fnn_decreases(self, lorenz_data):
        """Test that FNN fraction decreases with increasing dimension."""
        _, fnn_curve = optimal_dimension(
            lorenz_data, delay=10, max_dim=6, return_fnn_curve=True
        )

        # FNN should generally decrease (may not be monotonic due to numerical issues)
        assert fnn_curve[0] > fnn_curve[-1], "FNN should decrease with dimension"

    def test_dimension_returns_fnn_curve(self, lorenz_data):
        """Test that return_fnn_curve=True returns FNN values."""
        result = optimal_dimension(
            lorenz_data, delay=10, max_dim=5, return_fnn_curve=True
        )

        assert isinstance(result, tuple)
        dim, fnn_curve = result
        assert isinstance(dim, (int, np.integer))
        assert isinstance(fnn_curve, np.ndarray)
        assert len(fnn_curve) == 5  # max_dim values

    def test_dimension_threshold_effect(self, lorenz_data):
        """Test that stricter threshold gives higher dimension."""
        dim_loose = optimal_dimension(
            lorenz_data, delay=10, max_dim=8, fnn_threshold=0.2
        )
        dim_strict = optimal_dimension(
            lorenz_data, delay=10, max_dim=8, fnn_threshold=0.01
        )

        # Stricter threshold should give same or higher dimension
        assert dim_strict >= dim_loose

    def test_dimension_sinusoidal_low(self):
        """Test that simple sinusoid has low embedding dimension."""
        t = np.arange(1000)
        signal = np.sin(2 * np.pi * t / 20)

        dim = optimal_dimension(signal, delay=5, max_dim=8, fnn_threshold=0.1)

        # Simple sinusoid should have low dimension (2-3)
        assert dim <= 4, f"Expected low dimension for sinusoid, got {dim}"

    def test_dimension_rejects_short_series(self):
        """Test that short series raises ValueError."""
        ts = np.arange(50.0)

        with pytest.raises(ValueError, match="too short"):
            optimal_dimension(ts, delay=10, max_dim=10)

    def test_dimension_rejects_constant_series(self):
        """Test that constant series raises ValueError."""
        ts = np.ones(500)

        with pytest.raises(ValueError, match="constant"):
            optimal_dimension(ts, delay=5, max_dim=5)

    def test_dimension_rejects_nan_values(self):
        """Test that NaN values raise ValueError."""
        ts = np.arange(500.0)
        ts[250] = np.nan

        with pytest.raises(ValueError, match="non-finite values"):
            optimal_dimension(ts, delay=5, max_dim=5)

    def test_dimension_rejects_invalid_delay(self):
        """Test that invalid delay raises appropriate error."""
        ts = np.arange(500.0)

        with pytest.raises(ValueError, match="delay must be >= 1"):
            optimal_dimension(ts, delay=0, max_dim=5)

        with pytest.raises(TypeError, match="delay must be an integer"):
            optimal_dimension(ts, delay=1.5, max_dim=5)


class TestIntegration:
    """Integration tests for complete embedding pipeline."""

    def test_full_pipeline_sinusoid(self):
        """Test complete pipeline: tau selection -> dimension -> embedding."""
        # Generate sinusoidal signal with slight noise for realistic behavior
        np.random.seed(42)
        t = np.arange(1000)
        signal = np.sin(2 * np.pi * t / 20) + 0.1 * np.random.randn(len(t))

        # Step 1: Find optimal tau
        tau = optimal_tau(signal, max_lag=30)
        assert 1 <= tau <= 15, f"Unexpected tau={tau}"

        # Step 2: Find optimal dimension (use looser threshold for noisy sinusoid)
        dim = optimal_dimension(signal, delay=tau, max_dim=8, fnn_threshold=0.15)
        assert 1 <= dim <= 6, f"Unexpected dimension={dim}"

        # Step 3: Perform embedding (ensure dimension >= 2)
        embed_dim = max(dim, 2)
        embedded = takens_embedding(signal, delay=tau, dimension=embed_dim)

        # Verify embedding shape
        expected_rows = len(signal) - (embed_dim - 1) * tau
        assert embedded.shape == (expected_rows, embed_dim)

        # Verify no NaN/Inf in output
        assert np.isfinite(embedded).all()

    def test_full_pipeline_random_walk(self):
        """Test pipeline on random walk (weak temporal structure)."""
        np.random.seed(42)
        random_walk = np.cumsum(np.random.randn(500))

        # Should still produce valid results, even if suboptimal
        tau = optimal_tau(random_walk, max_lag=30)
        assert 1 <= tau <= 30

        dim = optimal_dimension(random_walk, delay=tau, max_dim=8)
        assert 1 <= dim <= 8

        embedded = takens_embedding(random_walk, delay=tau, dimension=dim)
        assert embedded.shape[1] == dim
        assert np.isfinite(embedded).all()

    def test_reproducibility(self):
        """Test that results are deterministic."""
        t = np.arange(500)
        signal = np.sin(2 * np.pi * t / 20)

        # Run twice
        tau1 = optimal_tau(signal, max_lag=30)
        tau2 = optimal_tau(signal, max_lag=30)

        dim1 = optimal_dimension(signal, delay=5, max_dim=8)
        dim2 = optimal_dimension(signal, delay=5, max_dim=8)

        assert tau1 == tau2, "Tau selection should be deterministic"
        assert dim1 == dim2, "Dimension selection should be deterministic"
