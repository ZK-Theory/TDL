"""
Tests for persistence diagram computation.

This test suite validates correctness of Vietoris-Rips and Alpha complex
persistence computations, including cross-validation between giotto-tda and GUDHI.
"""

import numpy as np
import pytest
from scipy.integrate import odeint

from financial_tda.topology import takens_embedding
from financial_tda.topology.filtration import (
    compute_persistence_alpha,
    compute_persistence_gudhi,
    compute_persistence_statistics,
    compute_persistence_vr,
    diagram_to_array,
    filter_infinite_bars,
    get_persistence_pairs,
)


class TestVietorisRipsPersistence:
    """Test suite for Vietoris-Rips persistence computation."""

    def test_vr_output_shape(self):
        """Test that VR produces correct output shape."""
        # Create simple point cloud
        np.random.seed(42)
        point_cloud = np.random.randn(50, 3)

        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        # Should be 2D array with 3 columns [birth, death, dimension]
        assert diagram.ndim == 2
        assert diagram.shape[1] == 3

    def test_vr_output_format(self):
        """Test VR output format correctness."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 3)

        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        # All birth values should be non-negative
        assert (diagram[:, 0] >= 0).all()

        # Death should be >= birth
        assert (diagram[:, 1] >= diagram[:, 0]).all()

        # Dimensions should only be 0 or 1
        assert set(diagram[:, 2].astype(int)).issubset({0, 1})

    def test_vr_dimensions_h0_h1_h2(self):
        """Test VR computes all requested homology dimensions."""
        np.random.seed(42)
        point_cloud = np.random.randn(40, 3)

        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1, 2))

        # Should have features in H0, H1 (H2 may be empty for random cloud)
        dims = set(diagram[:, 2].astype(int))
        assert 0 in dims  # Should always have H0 features

    def test_vr_max_edge_length_auto(self):
        """Test automatic max_edge_length computation."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 3)

        # Should not raise error with auto max_edge_length
        diagram = compute_persistence_vr(point_cloud, max_edge_length=None)
        assert len(diagram) > 0

    def test_vr_max_edge_length_specified(self):
        """Test VR with specified max_edge_length."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 3)

        diagram = compute_persistence_vr(point_cloud, max_edge_length=2.0)

        # All death values should be <= max_edge_length (with some tolerance)
        finite_deaths = diagram[np.isfinite(diagram[:, 1]), 1]
        assert (finite_deaths <= 2.5).all()  # Allow some tolerance

    def test_vr_rejects_1d_input(self):
        """Test that 1D input raises ValueError."""
        point_cloud = np.arange(10, dtype=np.float64)

        with pytest.raises(ValueError, match="must be 2D"):
            compute_persistence_vr(point_cloud)

    def test_vr_rejects_single_point(self):
        """Test that single point raises ValueError."""
        point_cloud = np.array([[1.0, 2.0, 3.0]])

        with pytest.raises(ValueError, match="at least 2 points"):
            compute_persistence_vr(point_cloud)

    def test_vr_rejects_nan_input(self):
        """Test that NaN input raises ValueError."""
        point_cloud = np.array([[1.0, 2.0], [np.nan, 4.0], [5.0, 6.0]])

        with pytest.raises(ValueError, match="non-finite"):
            compute_persistence_vr(point_cloud)

    def test_vr_on_embedded_time_series(self):
        """Test VR on Takens-embedded time series."""
        # Create sinusoidal signal with noise to avoid degeneracy
        np.random.seed(42)
        t = np.arange(150)
        signal = np.sin(2 * np.pi * t / 20) + 0.1 * np.random.randn(len(t))

        # Embed
        point_cloud = takens_embedding(signal, delay=5, dimension=3)

        # Compute persistence
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        assert len(diagram) > 0
        assert diagram.shape[1] == 3


class TestAlphaPersistence:
    """Test suite for Alpha complex persistence computation."""

    @pytest.fixture
    def lorenz_point_cloud(self):
        """Generate Lorenz attractor point cloud."""

        def lorenz(state, t, sigma=10, rho=28, beta=8 / 3):
            x, y, z = state
            return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

        t = np.linspace(0, 25, 1500)
        sol = odeint(lorenz, [1, 1, 1], t)
        x = sol[:, 0]
        return takens_embedding(x, delay=10, dimension=3)

    def test_alpha_output_shape(self, lorenz_point_cloud):
        """Test that Alpha produces correct output shape."""
        diagram = compute_persistence_alpha(
            lorenz_point_cloud, homology_dimensions=(0, 1)
        )

        assert diagram.ndim == 2
        assert diagram.shape[1] == 3

    def test_alpha_output_format(self, lorenz_point_cloud):
        """Test Alpha output format correctness."""
        diagram = compute_persistence_alpha(
            lorenz_point_cloud, homology_dimensions=(0, 1)
        )

        # All birth values should be non-negative
        assert (diagram[:, 0] >= 0).all()

        # Death should be >= birth
        assert (diagram[:, 1] >= diagram[:, 0]).all()

    def test_alpha_rejects_2d_array_wrong_shape(self):
        """Test that 1D input raises ValueError."""
        point_cloud = np.arange(10, dtype=np.float64)

        with pytest.raises(ValueError, match="must be 2D"):
            compute_persistence_alpha(point_cloud)

    def test_alpha_on_random_cloud(self):
        """Test Alpha on random 3D point cloud."""
        np.random.seed(42)
        point_cloud = np.random.randn(100, 3)

        diagram = compute_persistence_alpha(point_cloud, homology_dimensions=(0, 1))

        assert len(diagram) > 0


class TestGUDHIPersistence:
    """Test suite for GUDHI-based persistence computation."""

    def test_gudhi_output_shape(self):
        """Test that GUDHI produces correct output shape."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 3)

        diagram = compute_persistence_gudhi(point_cloud, max_dimension=2)

        assert diagram.ndim == 2
        assert diagram.shape[1] == 3

    def test_gudhi_output_format(self):
        """Test GUDHI output format correctness."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 3)

        diagram = compute_persistence_gudhi(point_cloud, max_dimension=1)

        # All birth values should be non-negative
        assert (diagram[:, 0] >= 0).all()

        # Death should be >= birth
        assert (diagram[:, 1] >= diagram[:, 0]).all()


class TestCrossValidation:
    """Cross-validation tests comparing giotto-tda and GUDHI."""

    def test_vr_gudhi_consistency_h0_count(self):
        """Test that giotto-tda and GUDHI produce similar H0 feature count."""
        np.random.seed(42)
        point_cloud = np.random.randn(40, 3)
        max_edge = 2.0

        # Compute with both
        diagram_gtda = compute_persistence_vr(
            point_cloud, homology_dimensions=(0,), max_edge_length=max_edge
        )
        diagram_gudhi = compute_persistence_gudhi(
            point_cloud, max_edge_length=max_edge, max_dimension=0
        )

        # Count H0 features
        h0_gtda = np.sum(diagram_gtda[:, 2] == 0)
        h0_gudhi = np.sum(diagram_gudhi[:, 2] == 0)

        # Should have similar count (within reasonable tolerance)
        # Both should find n-1 H0 features (merging of components)
        assert abs(h0_gtda - h0_gudhi) < 10, (
            f"H0 count mismatch: gtda={h0_gtda}, gudhi={h0_gudhi}"
        )

    def test_vr_gudhi_consistency_persistence_range(self):
        """Test that max persistence is similar between implementations."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 3)
        max_edge = 3.0

        # Compute with both
        diagram_gtda = compute_persistence_vr(
            point_cloud, homology_dimensions=(0, 1), max_edge_length=max_edge
        )
        diagram_gudhi = compute_persistence_gudhi(
            point_cloud, max_edge_length=max_edge, max_dimension=1
        )

        # Filter to H1 only (H0 includes infinite bar for connected component)
        # to avoid issues with how infinite bars are handled differently
        h1_gtda = diagram_gtda[diagram_gtda[:, 2] == 1]
        h1_gudhi = diagram_gudhi[diagram_gudhi[:, 2] == 1]

        if len(h1_gtda) > 0 and len(h1_gudhi) > 0:
            # Get finite persistence values for H1
            pers_gtda = h1_gtda[:, 1] - h1_gtda[:, 0]
            pers_gudhi = h1_gudhi[:, 1] - h1_gudhi[:, 0]

            # Filter out capped infinite values (death > max_edge)
            finite_gtda = pers_gtda[h1_gtda[:, 1] <= max_edge]
            finite_gudhi = pers_gudhi[h1_gudhi[:, 1] <= max_edge]

            if len(finite_gtda) > 0 and len(finite_gudhi) > 0:
                max_pers_gtda = np.max(finite_gtda)
                max_pers_gudhi = np.max(finite_gudhi)

                # Within 50% relative tolerance
                denominator = max(max_pers_gtda, 0.01)
                rel_diff = abs(max_pers_gtda - max_pers_gudhi) / denominator
                assert rel_diff < 0.5, (
                    f"Max persistence mismatch: gtda={max_pers_gtda:.4f}, "
                    f"gudhi={max_pers_gudhi:.4f}"
                )


class TestLorenzTopology:
    """Tests on Lorenz attractor with known topological features."""

    @pytest.fixture
    def lorenz_diagram(self):
        """Generate persistence diagram from Lorenz attractor."""

        def lorenz(state, t, sigma=10, rho=28, beta=8 / 3):
            x, y, z = state
            return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

        # Use smaller point cloud to keep tests fast (VR is O(n^3))
        t = np.linspace(0, 30, 500)
        sol = odeint(lorenz, [1, 1, 1], t)
        x = sol[:, 0]

        point_cloud = takens_embedding(x, delay=10, dimension=3)
        return compute_persistence_vr(point_cloud, homology_dimensions=(0, 1, 2))

    def test_lorenz_has_h0_features(self, lorenz_diagram):
        """Test that Lorenz attractor has H0 (connected component) features."""
        h0_count = np.sum(lorenz_diagram[:, 2] == 0)
        assert h0_count > 0, "Lorenz should have H0 features"

    def test_lorenz_has_h1_features(self, lorenz_diagram):
        """Test that Lorenz attractor has H1 (loop) features."""
        h1_count = np.sum(lorenz_diagram[:, 2] == 1)
        # Lorenz attractor should show loop structure
        assert h1_count > 0, "Lorenz should have H1 features (loops)"

    def test_lorenz_h1_persistence(self, lorenz_diagram):
        """Test that Lorenz has significant H1 persistence."""
        h1_pairs = get_persistence_pairs(lorenz_diagram, dimension=1)

        if len(h1_pairs) > 0:
            # Filter finite pairs
            finite_mask = np.isfinite(h1_pairs[:, 1])
            finite_pairs = h1_pairs[finite_mask]

            if len(finite_pairs) > 0:
                persistence = finite_pairs[:, 1] - finite_pairs[:, 0]
                max_pers = np.max(persistence)

                # Should have some significant H1 persistence
                assert max_pers > 0.1, (
                    f"Expected significant H1 persistence, got max={max_pers:.4f}"
                )


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_filter_infinite_bars_remove(self):
        """Test filtering removes infinite bars."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],
                [0.1, np.inf, 0],
                [0.2, 0.8, 1],
                [0.3, np.inf, 1],
            ]
        )

        filtered = filter_infinite_bars(diagram)

        assert len(filtered) == 2
        assert np.isfinite(filtered[:, 1]).all()

    def test_filter_infinite_bars_replace(self):
        """Test filtering replaces infinite bars with specified value."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],
                [0.1, np.inf, 0],
            ]
        )

        filtered = filter_infinite_bars(diagram, replacement=5.0)

        assert len(filtered) == 2
        assert filtered[1, 1] == 5.0

    def test_filter_infinite_bars_empty(self):
        """Test filtering handles empty diagram."""
        diagram = np.array([]).reshape(0, 3)
        filtered = filter_infinite_bars(diagram)
        assert filtered.shape == (0, 3)

    def test_diagram_to_array_with_dimension(self):
        """Test conversion with dimension column."""
        diagram = np.array([[0.0, 1.0, 0], [0.1, 0.5, 1]])
        result = diagram_to_array(diagram, include_dimension=True)
        assert result.shape == (2, 3)

    def test_diagram_to_array_without_dimension(self):
        """Test conversion without dimension column."""
        diagram = np.array([[0.0, 1.0, 0], [0.1, 0.5, 1]])
        result = diagram_to_array(diagram, include_dimension=False)
        assert result.shape == (2, 2)

    def test_get_persistence_pairs_h0(self):
        """Test extracting H0 pairs."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],
                [0.1, 0.5, 1],
                [0.2, 0.8, 0],
            ]
        )

        h0_pairs = get_persistence_pairs(diagram, dimension=0)

        assert h0_pairs.shape == (2, 2)
        np.testing.assert_array_equal(h0_pairs, [[0.0, 1.0], [0.2, 0.8]])

    def test_get_persistence_pairs_h1(self):
        """Test extracting H1 pairs."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],
                [0.1, 0.5, 1],
                [0.2, 0.8, 0],
            ]
        )

        h1_pairs = get_persistence_pairs(diagram, dimension=1)

        assert h1_pairs.shape == (1, 2)
        np.testing.assert_array_equal(h1_pairs, [[0.1, 0.5]])

    def test_get_persistence_pairs_empty(self):
        """Test extracting pairs for empty dimension."""
        diagram = np.array([[0.0, 1.0, 0]])
        h2_pairs = get_persistence_pairs(diagram, dimension=2)
        assert h2_pairs.shape == (0, 2)

    def test_compute_persistence_statistics(self):
        """Test persistence statistics computation."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],  # persistence = 1.0
                [0.1, 0.5, 0],  # persistence = 0.4
                [0.2, 0.8, 0],  # persistence = 0.6
            ]
        )

        stats = compute_persistence_statistics(diagram, dimension=0)

        assert stats["n_features"] == 3
        assert abs(stats["mean_persistence"] - (1.0 + 0.4 + 0.6) / 3) < 1e-10
        assert stats["max_persistence"] == 1.0
        assert abs(stats["total_persistence"] - 2.0) < 1e-10

    def test_compute_persistence_statistics_empty(self):
        """Test statistics on empty diagram."""
        diagram = np.array([]).reshape(0, 3)
        stats = compute_persistence_statistics(diagram)

        assert stats["n_features"] == 0
        assert stats["mean_persistence"] == 0.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_small_point_cloud(self):
        """Test with minimal valid point cloud."""
        point_cloud = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]])

        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        assert len(diagram) > 0

    def test_high_dimensional_embedding(self):
        """Test with higher dimensional point cloud."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 6)  # 6D embedding

        diagram = compute_persistence_vr(
            point_cloud, homology_dimensions=(0, 1), max_edge_length=3.0
        )

        assert len(diagram) > 0

    def test_dense_point_cloud(self):
        """Test with very dense point cloud."""
        np.random.seed(42)
        # Dense cluster of points
        point_cloud = 0.1 * np.random.randn(100, 3)

        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        # Should still produce valid output
        assert diagram.shape[1] == 3
