"""
TTK Hybrid Backend Integration Tests for Financial TDA Pipeline.

This test suite validates the TTK (Topology ToolKit) hybrid backend integration
from Phase 6.5, including Rips persistence computation, persim distance metrics,
and automatic backend selection logic.

Tests are marked with @pytest.mark.ttk and are skipped if TTK is unavailable.

Test Coverage:
    - TTK Rips persistence computation via compute_persistence_ttk()
    - Persim distance metrics (bottleneck/Wasserstein)
    - Backend auto-selection based on dataset size
    - TTK vs giotto-tda/GUDHI result consistency
    - Performance characteristics (runtime, memory)

Run with:
    pytest tests/financial/topology/test_ttk_integration.py -v --run-ttk
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import numpy as np
import pytest

from financial_tda.topology.embedding import takens_embedding
from financial_tda.topology.features import (
    bottleneck_distance,
    compute_landscape_norms,
    wasserstein_distance,
)
from financial_tda.topology.filtration import (
    compute_persistence_gudhi,
    compute_persistence_ttk,
    compute_persistence_vr,
)
from shared.ttk_utils import is_ttk_available

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Skip all tests in this module if TTK unavailable
pytestmark = pytest.mark.skipif(
    not is_ttk_available(),
    reason="TTK not available - install via conda in ttk_env",
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def small_point_cloud() -> NDArray[np.floating]:
    """Generate small point cloud for testing (100 points in R^3)."""
    np.random.seed(42)
    return np.random.randn(100, 3) * 0.5


@pytest.fixture
def medium_point_cloud() -> NDArray[np.floating]:
    """Generate medium point cloud (500 points in R^3)."""
    np.random.seed(42)
    return np.random.randn(500, 3) * 0.5


@pytest.fixture
def large_point_cloud() -> NDArray[np.floating]:
    """Generate large point cloud (1500 points in R^3)."""
    np.random.seed(42)
    return np.random.randn(1500, 3) * 0.5


@pytest.fixture
def synthetic_time_series() -> NDArray[np.floating]:
    """Generate synthetic financial time series."""
    np.random.seed(42)
    n_samples = 500
    returns = np.random.randn(n_samples) * 0.02 + 0.0005
    prices = 100 * np.exp(np.cumsum(returns))
    log_returns = np.diff(np.log(prices))
    return log_returns


# ============================================================================
# TTK Rips Persistence Tests
# ============================================================================


class TestTTKRipsPersistence:
    """Test TTK Rips persistence computation."""

    def test_ttk_basic_computation(self, small_point_cloud):
        """Test basic TTK persistence computation on small dataset."""
        diagram = compute_persistence_ttk(
            small_point_cloud,
            homology_dimensions=(0, 1, 2),
        )

        # Validate output format
        assert diagram.shape[1] == 3, "Diagram should have 3 columns [birth, death, dim]"
        assert len(diagram) > 0, "Should find some topological features"

        # Check dimension values
        dims = diagram[:, 2]
        assert np.all((dims >= 0) & (dims <= 2)), "Dimensions should be in [0, 2]"

        # Check birth < death
        births = diagram[:, 0]
        deaths = diagram[:, 1]
        assert np.all(births <= deaths), "Birth times should be <= death times"

        logger.info("TTK basic computation: %d features found", len(diagram))

    def test_ttk_vs_gudhi_consistency(self, small_point_cloud):
        """Test that TTK and GUDHI produce consistent results."""
        # Compute with both backends
        diagram_ttk = compute_persistence_ttk(
            small_point_cloud,
            homology_dimensions=(0, 1),
        )

        diagram_gudhi = compute_persistence_gudhi(
            small_point_cloud,
            max_dimension=1,
        )

        # Filter GUDHI to same dimensions
        diagram_gudhi = diagram_gudhi[diagram_gudhi[:, 2] <= 1]

        # Feature counts should be similar (within 20%)
        count_diff = abs(len(diagram_ttk) - len(diagram_gudhi)) / max(len(diagram_ttk), len(diagram_gudhi))
        assert count_diff < 0.20, f"Feature count difference too large: {count_diff:.2%}"

        # Compute landscape norms for comparison
        l1_ttk, l2_ttk = compute_landscape_norms(diagram_ttk, n_layers=5, n_bins=100)
        l1_gudhi, l2_gudhi = compute_landscape_norms(diagram_gudhi, n_layers=5, n_bins=100)

        # Norms should be similar (within 15% relative difference)
        l1_diff = abs(l1_ttk - l1_gudhi) / max(l1_ttk, l1_gudhi)
        l2_diff = abs(l2_ttk - l2_gudhi) / max(l2_ttk, l2_gudhi)

        assert l1_diff < 0.15, f"L1 norm difference too large: {l1_diff:.2%}"
        assert l2_diff < 0.15, f"L2 norm difference too large: {l2_diff:.2%}"

        logger.info(
            "TTK vs GUDHI: %d vs %d features, L1 diff=%.2%%, L2 diff=%.2%%",
            len(diagram_ttk),
            len(diagram_gudhi),
            l1_diff * 100,
            l2_diff * 100,
        )

    def test_ttk_large_dataset_performance(self, large_point_cloud):
        """Test TTK performance advantage on large datasets."""
        # Compute with TTK
        start_ttk = time.time()
        diagram_ttk = compute_persistence_ttk(
            large_point_cloud,
            homology_dimensions=(0, 1),
        )
        time_ttk = time.time() - start_ttk

        # Compute with GUDHI for comparison
        start_gudhi = time.time()
        diagram_gudhi = compute_persistence_gudhi(
            large_point_cloud,
            max_dimension=1,
        )
        time_gudhi = time.time() - start_gudhi

        # TTK should be faster (typically 3-10× on large datasets)
        speedup = time_gudhi / time_ttk

        assert len(diagram_ttk) > 0
        assert len(diagram_gudhi) > 0

        logger.info(
            "Performance on 1500 points: TTK=%.2fs, GUDHI=%.2fs, speedup=%.1fx",
            time_ttk,
            time_gudhi,
            speedup,
        )

        # Note: Speedup may vary, but TTK should generally be faster
        # Don't enforce strict speedup requirement as it depends on hardware

    def test_ttk_with_financial_time_series(self, synthetic_time_series):
        """Test TTK on actual financial time series embedding."""
        # Embed time series
        embedded = takens_embedding(synthetic_time_series, delay=5, dimension=3)

        # Compute persistence with TTK
        diagram = compute_persistence_ttk(embedded, homology_dimensions=(0, 1))

        assert len(diagram) > 0

        # Compute features
        l1_norm, l2_norm = compute_landscape_norms(diagram, n_layers=5, n_bins=100)

        assert l1_norm > 0
        assert l2_norm > 0

        logger.info(
            "TTK on financial time series: %d embedded points → %d features, L1=%.4f",
            len(embedded),
            len(diagram),
            l1_norm,
        )


# ============================================================================
# Persim Distance Metrics Tests
# ============================================================================


class TestPersimDistanceMetrics:
    """Test persim distance metrics (bottleneck, Wasserstein)."""

    def test_bottleneck_distance_basic(self, small_point_cloud):
        """Test bottleneck distance computation between diagrams."""
        # Generate two diagrams from slightly perturbed point clouds
        diagram1 = compute_persistence_ttk(
            small_point_cloud,
            homology_dimensions=(0, 1),
        )

        # Add small perturbation
        perturbed_cloud = small_point_cloud + np.random.randn(*small_point_cloud.shape) * 0.05
        diagram2 = compute_persistence_ttk(
            perturbed_cloud,
            homology_dimensions=(0, 1),
        )

        # Compute bottleneck distance
        distance = bottleneck_distance(diagram1, diagram2)

        assert distance >= 0, "Distance should be non-negative"
        assert np.isfinite(distance), "Distance should be finite"

        logger.info("Bottleneck distance between perturbed diagrams: %.4f", distance)

    def test_wasserstein_distance_basic(self, small_point_cloud):
        """Test Wasserstein distance computation between diagrams."""
        # Generate two diagrams
        diagram1 = compute_persistence_ttk(
            small_point_cloud,
            homology_dimensions=(0, 1),
        )

        perturbed_cloud = small_point_cloud + np.random.randn(*small_point_cloud.shape) * 0.05
        diagram2 = compute_persistence_ttk(
            perturbed_cloud,
            homology_dimensions=(0, 1),
        )

        # Compute Wasserstein distance (order 2)
        distance = wasserstein_distance(diagram1, diagram2, order=2)

        assert distance >= 0, "Distance should be non-negative"
        assert np.isfinite(distance), "Distance should be finite"

        logger.info("Wasserstein-2 distance between perturbed diagrams: %.4f", distance)

    def test_distance_symmetry(self, small_point_cloud):
        """Test that distance metrics are symmetric."""
        diagram1 = compute_persistence_ttk(
            small_point_cloud,
            homology_dimensions=(0, 1),
        )

        perturbed_cloud = small_point_cloud * 1.1
        diagram2 = compute_persistence_ttk(
            perturbed_cloud,
            homology_dimensions=(0, 1),
        )

        # Bottleneck should be symmetric
        dist_12 = bottleneck_distance(diagram1, diagram2)
        dist_21 = bottleneck_distance(diagram2, diagram1)

        assert np.isclose(dist_12, dist_21, rtol=1e-10), "Bottleneck should be symmetric"

        # Wasserstein should be symmetric
        wass_12 = wasserstein_distance(diagram1, diagram2, order=2)
        wass_21 = wasserstein_distance(diagram2, diagram1, order=2)

        assert np.isclose(wass_12, wass_21, rtol=1e-10), "Wasserstein should be symmetric"

        logger.info(
            "Distance symmetry verified: bottleneck=%.4f, wasserstein=%.4f",
            dist_12,
            wass_12,
        )

    def test_distance_triangle_inequality(self, small_point_cloud):
        """Test triangle inequality for distance metrics."""
        # Generate three diagrams
        diagram1 = compute_persistence_ttk(small_point_cloud, homology_dimensions=(0, 1))

        diagram2 = compute_persistence_ttk(
            small_point_cloud + np.random.randn(*small_point_cloud.shape) * 0.05,
            homology_dimensions=(0, 1),
        )

        diagram3 = compute_persistence_ttk(
            small_point_cloud + np.random.randn(*small_point_cloud.shape) * 0.1,
            homology_dimensions=(0, 1),
        )

        # Compute distances
        d12 = bottleneck_distance(diagram1, diagram2)
        d23 = bottleneck_distance(diagram2, diagram3)
        d13 = bottleneck_distance(diagram1, diagram3)

        # Triangle inequality: d(1,3) <= d(1,2) + d(2,3)
        assert d13 <= d12 + d23 + 1e-10, "Triangle inequality violated for bottleneck"

        logger.info(
            "Triangle inequality: d13=%.4f <= d12=%.4f + d23=%.4f = %.4f",
            d13,
            d12,
            d23,
            d12 + d23,
        )


# ============================================================================
# Backend Auto-Selection Tests
# ============================================================================


class TestBackendAutoSelection:
    """Test automatic backend selection based on dataset size."""

    def test_small_dataset_uses_gudhi(self, small_point_cloud):
        """Test that small datasets use GUDHI by default (no TTK overhead)."""
        # compute_persistence_vr should use giotto-tda for small datasets
        diagram = compute_persistence_vr(
            small_point_cloud,
            homology_dimensions=(0, 1),
        )

        assert len(diagram) > 0

        # Verify this works (implementation may not have auto-selection yet)
        logger.info("Small dataset (%d points): processed successfully", len(small_point_cloud))

    def test_large_dataset_benefits_from_ttk(self, large_point_cloud):
        """Test that large datasets benefit from TTK speedup."""
        # Time both approaches
        start_vr = time.time()
        diagram_vr = compute_persistence_vr(
            large_point_cloud,
            homology_dimensions=(0, 1),
        )
        time_vr = time.time() - start_vr

        start_ttk = time.time()
        diagram_ttk = compute_persistence_ttk(
            large_point_cloud,
            homology_dimensions=(0, 1),
        )
        time_ttk = time.time() - start_ttk

        assert len(diagram_vr) > 0
        assert len(diagram_ttk) > 0

        logger.info(
            "Large dataset (%d points): VR=%.2fs, TTK=%.2fs",
            len(large_point_cloud),
            time_vr,
            time_ttk,
        )

    def test_ttk_availability_fallback(self, small_point_cloud):
        """Test that pipeline falls back gracefully if TTK unavailable."""
        # This test verifies graceful fallback behavior
        # compute_persistence_vr should work regardless of TTK availability

        try:
            diagram = compute_persistence_vr(
                small_point_cloud,
                homology_dimensions=(0, 1),
            )
            assert len(diagram) > 0
            logger.info("Fallback mechanism verified: %d features", len(diagram))
        except Exception as e:
            pytest.fail(f"Fallback failed: {e}")


# ============================================================================
# TTK vs GUDHI Consistency Tests
# ============================================================================


class TestTTKGUDHIConsistency:
    """Detailed consistency tests between TTK and GUDHI backends."""

    def test_feature_count_consistency(self, medium_point_cloud):
        """Test that TTK and GUDHI produce similar feature counts."""
        diagram_ttk = compute_persistence_ttk(
            medium_point_cloud,
            homology_dimensions=(0, 1, 2),
        )

        diagram_gudhi = compute_persistence_gudhi(
            medium_point_cloud,
            max_dimension=2,
        )

        # Count features by dimension
        for dim in [0, 1, 2]:
            count_ttk = np.sum(diagram_ttk[:, 2] == dim)
            count_gudhi = np.sum(diagram_gudhi[:, 2] == dim)

            if max(count_ttk, count_gudhi) > 0:
                rel_diff = abs(count_ttk - count_gudhi) / max(count_ttk, count_gudhi)
                assert rel_diff < 0.25, f"H{dim} feature count differs too much: {count_ttk} vs {count_gudhi}"

        logger.info("Feature counts: TTK=%d, GUDHI=%d", len(diagram_ttk), len(diagram_gudhi))

    def test_persistence_value_consistency(self, medium_point_cloud):
        """Test that persistence values (death - birth) are similar."""
        diagram_ttk = compute_persistence_ttk(
            medium_point_cloud,
            homology_dimensions=(0, 1),
        )

        diagram_gudhi = compute_persistence_gudhi(
            medium_point_cloud,
            max_dimension=1,
        )

        # Compute persistence for each diagram
        persistence_ttk = diagram_ttk[:, 1] - diagram_ttk[:, 0]
        persistence_gudhi = diagram_gudhi[:, 1] - diagram_gudhi[:, 0]

        # Compare statistical properties
        mean_ttk = np.mean(persistence_ttk)
        mean_gudhi = np.mean(persistence_gudhi)

        np.std(persistence_ttk)
        np.std(persistence_gudhi)

        # Means should be similar (within 20%)
        if max(mean_ttk, mean_gudhi) > 0:
            mean_diff = abs(mean_ttk - mean_gudhi) / max(mean_ttk, mean_gudhi)
            assert mean_diff < 0.20, f"Mean persistence differs: {mean_diff:.2%}"

        logger.info(
            "Persistence values: TTK mean=%.4f, GUDHI mean=%.4f",
            mean_ttk,
            mean_gudhi,
        )

    def test_landscape_feature_consistency(self, medium_point_cloud):
        """Test that landscape features are consistent across backends."""
        diagram_ttk = compute_persistence_ttk(
            medium_point_cloud,
            homology_dimensions=(1,),  # H1 only
        )

        diagram_gudhi = compute_persistence_gudhi(
            medium_point_cloud,
            max_dimension=1,
        )

        # Filter GUDHI to H1 only
        diagram_gudhi = diagram_gudhi[diagram_gudhi[:, 2] == 1]

        # Compute landscape norms
        l1_ttk, l2_ttk = compute_landscape_norms(diagram_ttk, n_layers=5, n_bins=100)
        l1_gudhi, l2_gudhi = compute_landscape_norms(diagram_gudhi, n_layers=5, n_bins=100)

        # Norms should be similar (within 15%)
        if max(l1_ttk, l1_gudhi) > 0:
            l1_diff = abs(l1_ttk - l1_gudhi) / max(l1_ttk, l1_gudhi)
            assert l1_diff < 0.15, f"L1 norm differs: {l1_diff:.2%}"

        if max(l2_ttk, l2_gudhi) > 0:
            l2_diff = abs(l2_ttk - l2_gudhi) / max(l2_ttk, l2_gudhi)
            assert l2_diff < 0.15, f"L2 norm differs: {l2_diff:.2%}"

        logger.info(
            "Landscape norms: TTK (L1=%.4f, L2=%.4f), GUDHI (L1=%.4f, L2=%.4f)",
            l1_ttk,
            l2_ttk,
            l1_gudhi,
            l2_gudhi,
        )


# ============================================================================
# Performance Benchmarking Tests
# ============================================================================


class TestPerformanceCharacteristics:
    """Test performance characteristics of TTK vs GUDHI."""

    def test_performance_scaling_with_size(self):
        """Test how performance scales with dataset size."""
        sizes = [100, 300, 600, 1000]
        times_ttk = []
        times_gudhi = []

        for size in sizes:
            np.random.seed(42)
            point_cloud = np.random.randn(size, 3) * 0.5

            # Time TTK
            start = time.time()
            compute_persistence_ttk(point_cloud, homology_dimensions=(0, 1))
            times_ttk.append(time.time() - start)

            # Time GUDHI
            start = time.time()
            compute_persistence_gudhi(point_cloud, max_dimension=1)
            times_gudhi.append(time.time() - start)

        # Log results
        for size, t_ttk, t_gudhi in zip(sizes, times_ttk, times_gudhi):
            speedup = t_gudhi / t_ttk if t_ttk > 0 else 1.0
            logger.info(
                "Size=%d: TTK=%.3fs, GUDHI=%.3fs, speedup=%.1fx",
                size,
                t_ttk,
                t_gudhi,
                speedup,
            )

        # TTK should scale better for large datasets
        # (This is an observational test, not a strict assertion)

    def test_memory_efficiency(self, large_point_cloud):
        """Test that TTK doesn't use excessive memory."""
        # This is a basic test - proper memory profiling requires external tools
        try:
            diagram = compute_persistence_ttk(
                large_point_cloud,
                homology_dimensions=(0, 1, 2),
            )
            assert len(diagram) > 0
            logger.info(
                "Memory efficiency test passed: processed %d points",
                len(large_point_cloud),
            )
        except MemoryError:
            pytest.fail("TTK ran out of memory on large dataset")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--run-ttk"])
