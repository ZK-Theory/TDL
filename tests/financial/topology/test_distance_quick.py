"""
Quick validation tests for distance metrics.
"""

import numpy as np
import pytest

from financial_tda.topology.filtration import (
    compute_bottleneck_distance,
    compute_persistence_vr,
    compute_wasserstein_distance,
)


class TestDistanceMetrics:
    """Quick tests for distance metric computations."""

    def test_bottleneck_identical(self):
        """Bottleneck distance between identical diagrams should be 0."""
        np.random.seed(42)
        pc = np.random.randn(20, 2)
        diag = compute_persistence_vr(pc, homology_dimensions=(1,))

        distance = compute_bottleneck_distance(diag, diag)
        assert distance == pytest.approx(0.0, abs=1e-6)

    def test_bottleneck_symmetry(self):
        """Bottleneck distance should be symmetric."""
        np.random.seed(42)
        pc1 = np.random.randn(15, 2)
        pc2 = np.random.randn(15, 2) + 1

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        d12 = compute_bottleneck_distance(diag1, diag2)
        d21 = compute_bottleneck_distance(diag2, diag1)

        assert d12 == pytest.approx(d21, rel=1e-6)

    def test_wasserstein_identical(self):
        """Wasserstein distance between identical diagrams should be 0."""
        np.random.seed(42)
        pc = np.random.randn(20, 2)
        diag = compute_persistence_vr(pc, homology_dimensions=(1,))

        distance = compute_wasserstein_distance(diag, diag)
        assert distance == pytest.approx(0.0, abs=1e-6)

    def test_wasserstein_symmetry(self):
        """Wasserstein distance should be symmetric."""
        np.random.seed(42)
        pc1 = np.random.randn(15, 2)
        pc2 = np.random.randn(15, 2) + 1

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        d12 = compute_wasserstein_distance(diag1, diag2)
        d21 = compute_wasserstein_distance(diag2, diag1)

        assert d12 == pytest.approx(d21, rel=1e-6)

    def test_distances_positive(self):
        """Distances between different diagrams should be positive."""
        np.random.seed(42)
        pc1 = np.random.randn(15, 2)
        pc2 = np.random.randn(15, 2) + 2  # Different cloud

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(1,))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(1,))

        bottleneck = compute_bottleneck_distance(diag1, diag2)
        wasserstein = compute_wasserstein_distance(diag1, diag2)

        assert bottleneck > 0
        assert wasserstein > 0

    def test_dimension_filtering(self):
        """Distance computation should respect dimension filtering."""
        np.random.seed(42)
        pc1 = np.random.randn(20, 2)
        pc2 = np.random.randn(20, 2) + 0.5

        diag1 = compute_persistence_vr(pc1, homology_dimensions=(0, 1))
        diag2 = compute_persistence_vr(pc2, homology_dimensions=(0, 1))

        # H0 distance
        d_h0 = compute_bottleneck_distance(diag1, diag2, dimension=0)
        # H1 distance
        d_h1 = compute_bottleneck_distance(diag1, diag2, dimension=1)

        # Both should be valid distances
        assert d_h0 >= 0
        assert d_h1 >= 0
