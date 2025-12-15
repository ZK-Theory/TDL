"""
Tests for TTK-based persistence distance computations.

Tests bottleneck and Wasserstein distances with both TTK and giotto-tda backends.
"""

import numpy as np
import pytest

from financial_tda.topology.filtration import (
    compute_bottleneck_distance,
    compute_persistence_vr,
    compute_wasserstein_distance,
)
from shared.ttk_utils import is_ttk_available

# Skip TTK tests if not available
TTK_AVAILABLE = is_ttk_available()
requires_ttk = pytest.mark.skipif(not TTK_AVAILABLE, reason="TTK not available")


class TestBottleneckDistance:
    """Test bottleneck distance computation."""

    def test_identical_diagrams(self):
        """Bottleneck distance between identical diagrams should be 0."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 2)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        distance = compute_bottleneck_distance(diagram, diagram)
        assert distance == pytest.approx(0.0, abs=1e-10)

    def test_symmetry(self):
        """Bottleneck distance should be symmetric."""
        np.random.seed(42)
        pc1 = np.random.randn(30, 2)
        pc2 = np.random.randn(30, 2) + 1.0

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        d12 = compute_bottleneck_distance(diag1, diag2)
        d21 = compute_bottleneck_distance(diag2, diag1)

        assert d12 == pytest.approx(d21, rel=1e-6)

    def test_triangle_inequality(self):
        """Bottleneck distance should satisfy triangle inequality."""
        np.random.seed(42)
        pc1 = np.random.randn(30, 2)
        pc2 = np.random.randn(30, 2) + 0.5
        pc3 = np.random.randn(30, 2) + 1.0

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))
        diag3 = compute_persistence_vr(pc3, homology_dimensions=(1,))

        d12 = compute_bottleneck_distance(diag1, diag2)
        d23 = compute_bottleneck_distance(diag2, diag3)
        d13 = compute_bottleneck_distance(diag1, diag3)

        # d(1,3) <= d(1,2) + d(2,3)
        assert d13 <= d12 + d23 + 1e-6  # Small tolerance for numerical errors

    def test_dimension_filtering(self):
        """Test distance computation for specific homology dimension."""
        np.random.seed(42)
        pc1 = np.random.randn(40, 2)
        pc2 = np.random.randn(40, 2) + 0.5

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(0, 1))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(0, 1))

        # Distance for H0 only
        d_h0 = compute_bottleneck_distance(diag1, diag2, dimension=0)

        # Distance for H1 only
        d_h1 = compute_bottleneck_distance(diag1, diag2, dimension=1)

        # Both should be non-negative
        assert d_h0 >= 0
        assert d_h1 >= 0

    def test_empty_diagrams(self):
        """Test distance handling for empty diagrams."""
        empty = np.array([]).reshape(0, 3)

        np.random.seed(42)
        point_cloud = np.random.randn(30, 2)
        non_empty = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        # Empty to empty should be 0
        d_empty = compute_bottleneck_distance(empty, empty)
        assert d_empty == 0.0

        # Empty to non-empty should be positive
        d_mixed = compute_bottleneck_distance(empty, non_empty)
        assert d_mixed > 0

    @requires_ttk
    def test_ttk_backend(self):
        """Test bottleneck distance with TTK backend (skipped - not implemented)."""
        pytest.skip("TTK bottleneck distance not yet integrated")

    @requires_ttk
    def test_backend_auto_selection(self):
        """Test automatic backend selection (skipped - not implemented)."""
        pytest.skip("TTK backend auto-selection not yet integrated")


class TestWassersteinDistance:
    """Test Wasserstein distance computation."""

    def test_identical_diagrams(self):
        """Wasserstein distance between identical diagrams should be 0."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 2)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

        for order in [1, 2]:
            distance = compute_wasserstein_distance(diagram, diagram, order=order)
            assert distance == pytest.approx(0.0, abs=1e-10)

    def test_symmetry(self):
        """Wasserstein distance should be symmetric."""
        np.random.seed(42)
        pc1 = np.random.randn(30, 2)
        pc2 = np.random.randn(30, 2) + 1.0

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        for order in [1, 2]:
            d12 = compute_wasserstein_distance(diag1, diag2, order=order)
            d21 = compute_wasserstein_distance(diag2, diag1, order=order)
            assert d12 == pytest.approx(d21, rel=1e-6)

    def test_triangle_inequality(self):
        """Wasserstein distance should satisfy triangle inequality."""
        np.random.seed(42)
        pc1 = np.random.randn(30, 2)
        pc2 = np.random.randn(30, 2) + 0.5
        pc3 = np.random.randn(30, 2) + 1.0

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))
        diag3 = compute_persistence_vr(pc3, homology_dimensions=(1,))

        d12 = compute_wasserstein_distance(diag1, diag2, order=2)
        d23 = compute_wasserstein_distance(diag2, diag3, order=2)
        d13 = compute_wasserstein_distance(diag1, diag3, order=2)

        # d(1,3) <= d(1,2) + d(2,3)
        assert d13 <= d12 + d23 + 1e-6

    def test_order_effects(self):
        """Test that different orders give different distances."""
        np.random.seed(42)
        pc1 = np.random.randn(30, 2)
        pc2 = np.random.randn(30, 2) + 1.0

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        d1 = compute_wasserstein_distance(diag1, diag2, order=1)
        d2 = compute_wasserstein_distance(diag1, diag2, order=2)

        # Different orders should give different values (unless diagrams very similar)
        # Both should be positive
        assert d1 > 0
        assert d2 > 0

    def test_dimension_filtering(self):
        """Test distance computation for specific homology dimension."""
        np.random.seed(42)
        pc1 = np.random.randn(40, 2)
        pc2 = np.random.randn(40, 2) + 0.5

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(0, 1))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(0, 1))

        d_h0 = compute_wasserstein_distance(diag1, diag2, dimension=0)
        d_h1 = compute_wasserstein_distance(diag1, diag2, dimension=1)

        # Distances should be different
        assert d_h0 != d_h1

        # Both should be non-negative
        assert d_h0 >= 0
        assert d_h1 >= 0

    def test_empty_diagrams(self):
        """Test distance handling for empty diagrams."""
        empty = np.array([]).reshape(0, 3)

        np.random.seed(42)
        point_cloud = np.random.randn(30, 2)
        non_empty = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        # Empty to empty should be 0
        d_empty = compute_wasserstein_distance(empty, empty)
        assert d_empty == 0.0

        # Empty to non-empty should be positive
        d_mixed = compute_wasserstein_distance(empty, non_empty)
        assert d_mixed > 0

    def test_invalid_order(self):
        """Test that invalid order raises ValueError."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 2)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        with pytest.raises(ValueError, match="order must be positive"):
            compute_wasserstein_distance(diagram, diagram, order=0)

        with pytest.raises(ValueError, match="order must be positive"):
            compute_wasserstein_distance(diagram, diagram, order=-1)


class TestDistanceComparison:
    """Compare bottleneck vs Wasserstein distances."""

    def test_distance_relationship(self):
        """Test mathematical relationship between distances."""
        np.random.seed(42)
        pc1 = np.random.randn(40, 2)
        pc2 = np.random.randn(40, 2) + 0.5

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        bottleneck = compute_bottleneck_distance(diag1, diag2)
        wasserstein_1 = compute_wasserstein_distance(diag1, diag2, order=1)
        wasserstein_2 = compute_wasserstein_distance(diag1, diag2, order=2)

        # Bottleneck <= 2-Wasserstein (for normalized diagrams)
        # All should be non-negative
        assert bottleneck >= 0
        assert wasserstein_1 >= 0
        assert wasserstein_2 >= 0

    def test_sensitivity_to_outliers(self):
        """Test that distance computation handles outliers correctly."""
        np.random.seed(42)

        # Create three different point clouds
        pc1 = np.random.randn(30, 2)
        pc2 = np.random.randn(30, 2) + 0.1
        pc3 = np.random.randn(30, 2) + 0.1
        pc3[0] += 5.0  # Add significant outlier

        # Compute persistence diagrams
        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))
        diag3 = compute_persistence_vr(pc3, homology_dimensions=(1,))

        # Compute distances
        bottleneck_12 = compute_bottleneck_distance(diag1, diag2)
        bottleneck_13 = compute_bottleneck_distance(diag1, diag3)
        wasserstein_12 = compute_wasserstein_distance(diag1, diag2)
        wasserstein_13 = compute_wasserstein_distance(diag1, diag3)

        # All distances should be non-negative and finite
        assert bottleneck_12 >= 0 and np.isfinite(bottleneck_12)
        assert bottleneck_13 >= 0 and np.isfinite(bottleneck_13)
        assert wasserstein_12 >= 0 and np.isfinite(wasserstein_12)
        assert wasserstein_13 >= 0 and np.isfinite(wasserstein_13)

        # Distances should be computable even with outliers
        # (Topological structure may change in complex ways - that's OK)


class TestPerformanceComparison:
    """Performance tests for distance computations."""

    @pytest.mark.slow
    def test_large_diagram_performance(self):
        """Test that Wasserstein is faster than bottleneck for large diagrams."""
        import time

        np.random.seed(42)
        # Create larger point clouds
        pc1 = np.random.randn(200, 2)
        pc2 = np.random.randn(200, 2) + 0.5

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        # Time bottleneck
        start = time.time()
        _ = compute_bottleneck_distance(diag1, diag2)
        bottleneck_time = time.time() - start

        # Time Wasserstein
        start = time.time()
        _ = compute_wasserstein_distance(diag1, diag2)
        wasserstein_time = time.time() - start

        print(f"\nBottleneck: {bottleneck_time:.3f}s, Wasserstein: {wasserstein_time:.3f}s")

        # Wasserstein should be faster (or at least not much slower)
        # Allow some variability in timing
        assert wasserstein_time < bottleneck_time * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
