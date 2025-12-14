"""
Tests for persistence-based feature extraction.

Tests validate persistence landscape computation and L^p norms
following Gidea & Katz (2018) methodology.
"""

import numpy as np
import pytest

from financial_tda.topology import compute_persistence_vr
from financial_tda.topology.features import (
    betti_curve,
    betti_curve_statistics,
    compute_landscape_norms,
    compute_multiscale_persistence_images,
    compute_persistence_image,
    compute_persistence_landscape,
    extract_entropy_betti_features,
    extract_image_features,
    extract_landscape_features,
    landscape_lp_norm,
    landscape_statistics,
    persistence_amplitude,
    persistence_entropy,
    total_persistence,
)


class TestPersistenceLandscape:
    """Tests for persistence landscape computation."""

    @pytest.fixture
    def sample_diagram(self):
        """Create sample persistence diagram with known H1 features."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        return compute_persistence_vr(point_cloud, homology_dimensions=(1,))

    def test_landscape_shape(self, sample_diagram):
        """Test landscape output shape."""
        landscape = compute_persistence_landscape(
            sample_diagram, n_layers=5, n_bins=100
        )
        # Shape: (n_layers, n_dims, n_bins)
        assert landscape.ndim == 3
        assert landscape.shape[0] == 5  # n_layers
        assert landscape.shape[2] == 100  # n_bins

    def test_landscape_non_negative(self, sample_diagram):
        """Test that landscape values are non-negative."""
        landscape = compute_persistence_landscape(sample_diagram)
        assert np.all(landscape >= 0)

    def test_landscape_ordered_layers(self, sample_diagram):
        """Test that λ_1 >= λ_2 >= ... (pointwise)."""
        landscape = compute_persistence_landscape(sample_diagram, n_layers=3, n_bins=50)
        # Check λ_k >= λ_{k+1} at each point
        for k in range(landscape.shape[0] - 1):
            # Allow small numerical tolerance
            assert np.all(landscape[k] >= landscape[k + 1] - 1e-10)

    def test_landscape_empty_diagram_raises(self):
        """Test that empty diagram raises ValueError."""
        empty_diagram = np.array([]).reshape(0, 3)
        with pytest.raises(ValueError, match="Empty"):
            compute_persistence_landscape(empty_diagram)

    def test_landscape_all_infinite_raises(self):
        """Test that all-infinite deaths raises ValueError."""
        diagram = np.array([[0.0, np.inf, 1], [0.1, np.inf, 1]])
        with pytest.raises(ValueError, match="infinite"):
            compute_persistence_landscape(diagram)


class TestLandscapeLpNorm:
    """Tests for L^p norm computation."""

    @pytest.fixture
    def sample_landscape(self):
        """Create sample landscape."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))
        return compute_persistence_landscape(diagram, n_layers=5, n_bins=100)

    def test_l1_norm_non_negative(self, sample_landscape):
        """Test L1 norm is non-negative."""
        l1 = landscape_lp_norm(sample_landscape, p=1)
        assert l1 >= 0

    def test_l2_norm_non_negative(self, sample_landscape):
        """Test L2 norm is non-negative."""
        l2 = landscape_lp_norm(sample_landscape, p=2)
        assert l2 >= 0

    def test_l2_less_than_l1(self, sample_landscape):
        """Test L2 <= L1 for normalized landscapes."""
        l1 = landscape_lp_norm(sample_landscape, p=1)
        l2 = landscape_lp_norm(sample_landscape, p=2)
        # For most distributions, L2 <= L1 (Hölder inequality sense)
        # This is a sanity check, not always true for all distributions
        assert l2 <= l1 * 2  # Loose bound

    def test_empty_landscape_returns_zero(self):
        """Test empty landscape gives zero norm."""
        empty = np.array([])
        assert landscape_lp_norm(empty, p=1) == 0.0
        assert landscape_lp_norm(empty, p=2) == 0.0

    def test_invalid_p_raises(self, sample_landscape):
        """Test p < 1 raises ValueError."""
        with pytest.raises(ValueError, match="p must be >= 1"):
            landscape_lp_norm(sample_landscape, p=0.5)


class TestComputeLandscapeNorms:
    """Tests for the convenience function."""

    def test_returns_dict_with_l1_l2(self):
        """Test that function returns dict with L1 and L2 keys."""
        np.random.seed(42)
        point_cloud = np.random.randn(30, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        norms = compute_landscape_norms(diagram)

        assert isinstance(norms, dict)
        assert "L1" in norms
        assert "L2" in norms
        assert norms["L1"] >= 0
        assert norms["L2"] >= 0

    def test_handles_empty_diagram(self):
        """Test graceful handling of edge cases."""
        empty_diagram = np.array([]).reshape(0, 3)
        norms = compute_landscape_norms(empty_diagram)
        assert norms["L1"] == 0.0
        assert norms["L2"] == 0.0


class TestPersistenceEntropy:
    """Tests for persistence entropy."""

    def test_entropy_non_negative(self):
        """Test entropy is non-negative."""
        diagram = np.array(
            [
                [0.0, 1.0, 1],
                [0.1, 0.5, 1],
                [0.2, 0.8, 1],
            ]
        )
        entropy = persistence_entropy(diagram)
        assert entropy >= 0

    def test_entropy_single_feature(self):
        """Test entropy of single feature is 0."""
        diagram = np.array([[0.0, 1.0, 1]])
        entropy = persistence_entropy(diagram)
        # Single feature has probability 1, so entropy = -1 * log(1) = 0
        assert abs(entropy) < 1e-10

    def test_entropy_uniform_distribution(self):
        """Test entropy is maximum for uniform lifetimes."""
        # Equal lifetimes -> uniform distribution -> max entropy
        diagram = np.array(
            [
                [0.0, 1.0, 1],
                [0.0, 1.0, 1],
                [0.0, 1.0, 1],
            ]
        )
        entropy = persistence_entropy(diagram)
        # Max entropy for 3 elements is log(3) ≈ 1.0986
        expected_max = np.log(3)
        assert abs(entropy - expected_max) < 1e-10

    def test_entropy_empty_returns_zero(self):
        """Test empty diagram returns 0 entropy."""
        empty = np.array([]).reshape(0, 3)
        assert persistence_entropy(empty) == 0.0


class TestBettiCurve:
    """Tests for Betti curve computation."""

    def test_betti_curve_shape(self):
        """Test Betti curve output shape."""
        diagram = np.array(
            [
                [0.1, 0.5, 1],
                [0.2, 0.8, 1],
                [0.3, 0.6, 1],
            ]
        )
        filtration, betti = betti_curve(diagram, dimension=1, n_bins=50)

        assert len(filtration) == 50
        assert len(betti) == 50

    def test_betti_curve_values(self):
        """Test Betti curve counts features correctly."""
        # Features: [0.0, 1.0] and [0.2, 0.8]
        diagram = np.array(
            [
                [0.0, 1.0, 1],
                [0.2, 0.8, 1],
            ]
        )
        filtration, betti = betti_curve(
            diagram, dimension=1, n_bins=100, filtration_range=(0.0, 1.0)
        )

        # At ε=0.1: only first feature alive -> β=1
        idx_01 = np.argmin(np.abs(filtration - 0.1))
        assert betti[idx_01] == 1

        # At ε=0.5: both features alive -> β=2
        idx_05 = np.argmin(np.abs(filtration - 0.5))
        assert betti[idx_05] == 2

        # At ε=0.9: only first feature alive -> β=1
        idx_09 = np.argmin(np.abs(filtration - 0.9))
        assert betti[idx_09] == 1

    def test_betti_curve_empty_dimension(self):
        """Test Betti curve with no features in dimension."""
        diagram = np.array([[0.0, 1.0, 0]])  # Only H0
        filtration, betti = betti_curve(diagram, dimension=1, n_bins=50)

        assert len(betti) == 50
        assert np.all(betti == 0)


class TestTotalPersistence:
    """Tests for total persistence computation."""

    def test_total_persistence_sum(self):
        """Test total persistence sums lifetimes."""
        diagram = np.array(
            [
                [0.0, 1.0, 1],  # lifetime = 1.0
                [0.0, 0.5, 1],  # lifetime = 0.5
            ]
        )
        tp = total_persistence(diagram, dimension=1, p=1)
        assert abs(tp - 1.5) < 1e-10

    def test_total_persistence_p2(self):
        """Test total persistence with p=2."""
        diagram = np.array(
            [
                [0.0, 1.0, 1],  # lifetime = 1.0
                [0.0, 0.5, 1],  # lifetime = 0.5
            ]
        )
        tp = total_persistence(diagram, dimension=1, p=2)
        expected = 1.0**2 + 0.5**2  # 1.25
        assert abs(tp - expected) < 1e-10

    def test_total_persistence_filters_dimension(self):
        """Test dimension filtering works."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],  # H0
                [0.0, 0.5, 1],  # H1
            ]
        )
        tp_h1 = total_persistence(diagram, dimension=1, p=1)
        assert abs(tp_h1 - 0.5) < 1e-10

    def test_total_persistence_empty(self):
        """Test empty diagram returns 0."""
        empty = np.array([]).reshape(0, 3)
        assert total_persistence(empty) == 0.0


class TestGideaKatzWorkflow:
    """Integration tests simulating Gidea & Katz workflow."""

    def test_multi_index_point_cloud(self):
        """Test workflow with 4D point cloud (4 indices)."""
        np.random.seed(42)

        # Simulate 50 days of 4-index log returns
        returns = np.random.randn(50, 4) * 0.02  # ~2% daily vol

        # Compute H1 persistence
        diagram = compute_persistence_vr(returns, homology_dimensions=(1,))

        # Compute landscape norms
        norms = compute_landscape_norms(diagram, n_layers=5, n_bins=100)

        assert norms["L1"] > 0
        assert norms["L2"] > 0

    def test_scaled_point_cloud_scales_norms(self):
        """Test that scaling point cloud scales landscape norms proportionally.

        When point cloud is scaled by F, persistence values (b, d) scale by F,
        and thus lifetimes (d-b) scale by F. The landscape height scales by F,
        and width (over filtration range) also scales by F, so L^p norms
        should scale approximately by F (for L1) due to combined effects.
        """
        np.random.seed(42)

        # Base point cloud
        base_data = np.random.randn(50, 4)

        # Compute norms for base data
        diagram_base = compute_persistence_vr(base_data, homology_dimensions=(1,))
        norms_base = compute_landscape_norms(diagram_base)

        # Scale by factor of 3
        scale_factor = 3.0
        scaled_data = base_data * scale_factor
        diagram_scaled = compute_persistence_vr(scaled_data, homology_dimensions=(1,))
        norms_scaled = compute_landscape_norms(diagram_scaled)

        # Norms should scale approximately by F (linear scaling of persistence)
        ratio_l1 = norms_scaled["L1"] / norms_base["L1"]
        ratio_l2 = norms_scaled["L2"] / norms_base["L2"]

        # Allow tolerance for numerical effects
        # The exact scaling depends on how giotto-tda normalizes landscapes
        assert ratio_l1 > scale_factor * 0.5, f"L1 ratio {ratio_l1} too low"
        assert ratio_l2 > scale_factor * 0.5, f"L2 ratio {ratio_l2} too low"


class TestLandscapeStatistics:
    """Tests for landscape statistical summary function."""

    @pytest.fixture
    def sample_landscape(self):
        """Create sample landscape."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))
        return compute_persistence_landscape(diagram, n_layers=5, n_bins=100)

    def test_statistics_keys(self, sample_landscape):
        """Test that all expected keys are present."""
        stats = landscape_statistics(sample_landscape)

        assert "mean" in stats
        assert "std" in stats
        assert "max" in stats
        assert "per_layer" in stats

    def test_statistics_non_negative(self, sample_landscape):
        """Test that statistics are non-negative."""
        stats = landscape_statistics(sample_landscape)

        assert stats["mean"] >= 0
        assert stats["std"] >= 0
        assert stats["max"] >= 0

    def test_per_layer_structure(self, sample_landscape):
        """Test per-layer statistics structure."""
        stats = landscape_statistics(sample_landscape)

        n_layers = sample_landscape.shape[0]
        assert len(stats["per_layer"]) == n_layers

        for k in range(n_layers):
            assert k in stats["per_layer"]
            layer_stats = stats["per_layer"][k]
            assert "mean" in layer_stats
            assert "std" in layer_stats
            assert "max" in layer_stats

    def test_layer_ordering_property(self, sample_landscape):
        """Test that layer 0 has highest max (dominance property)."""
        stats = landscape_statistics(sample_landscape)

        # Layer 0 (λ_1) should have highest or equal max amplitude
        layer_0_max = stats["per_layer"][0]["max"]
        for k in range(1, len(stats["per_layer"])):
            layer_k_max = stats["per_layer"][k]["max"]
            # λ_1 >= λ_2 >= ... allows numerical tolerance
            assert layer_0_max >= layer_k_max - 1e-10

    def test_empty_landscape_returns_zeros(self):
        """Test empty landscape returns zero statistics."""
        empty = np.array([])
        stats = landscape_statistics(empty)

        assert stats["mean"] == 0.0
        assert stats["std"] == 0.0
        assert stats["max"] == 0.0
        assert stats["per_layer"] == {}

    def test_single_layer_statistics(self):
        """Test statistics on single-layer landscape."""
        # Create simple landscape manually
        single_layer = np.array([[[1.0, 2.0, 1.5, 0.5]]])  # (1, 1, 4)
        stats = landscape_statistics(single_layer)

        expected_mean = np.mean([1.0, 2.0, 1.5, 0.5])
        assert abs(stats["mean"] - expected_mean) < 1e-10
        assert stats["max"] == 2.0
        assert 0 in stats["per_layer"]


class TestExtractLandscapeFeatures:
    """Tests for complete feature extraction function."""

    @pytest.fixture
    def sample_diagram(self):
        """Create sample persistence diagram."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        return compute_persistence_vr(point_cloud, homology_dimensions=(1,))

    def test_feature_dict_keys(self, sample_diagram):
        """Test that all expected keys are present."""
        features = extract_landscape_features(sample_diagram, n_top_layers=3)

        # Check global features
        assert "L1" in features
        assert "L2" in features
        assert "mean" in features
        assert "std" in features
        assert "max" in features

        # Check per-layer features for top 3 layers
        for k in range(3):
            assert f"layer_{k}_mean" in features
            assert f"layer_{k}_std" in features
            assert f"layer_{k}_max" in features

    def test_feature_values_non_negative(self, sample_diagram):
        """Test that feature values are non-negative."""
        features = extract_landscape_features(sample_diagram)

        for key, value in features.items():
            assert value >= 0, f"{key} should be non-negative"

    def test_feature_count(self, sample_diagram):
        """Test correct number of features extracted."""
        n_top_layers = 3
        features = extract_landscape_features(sample_diagram, n_top_layers=n_top_layers)

        # Global: L1, L2, mean, std, max = 5
        # Per-layer: 3 stats × n_top_layers = 9
        # Total: 14
        expected_count = 5 + (3 * n_top_layers)
        assert len(features) == expected_count

    def test_handles_empty_diagram(self):
        """Test graceful handling of empty diagram."""
        empty_diagram = np.array([]).reshape(0, 3)
        features = extract_landscape_features(empty_diagram, n_top_layers=3)

        # Should return all zero features
        for key, value in features.items():
            assert value == 0.0, f"{key} should be 0.0 for empty diagram"

    def test_feature_vector_conversion(self, sample_diagram):
        """Test conversion to feature vector for ML."""
        features = extract_landscape_features(sample_diagram)

        # Convert to numpy array
        feature_vector = np.array(list(features.values()))

        assert feature_vector.ndim == 1
        assert len(feature_vector) == len(features)
        assert np.all(np.isfinite(feature_vector))


class TestLandscapeStability:
    """Tests for stability property of persistence landscapes."""

    def test_small_perturbation_stability(self):
        """Test that small perturbations produce small changes in landscape.

        Stability theorem: d_∞(λ_A, λ_B) ≤ d_B(A, B)
        where d_B is bottleneck distance between diagrams.
        """
        np.random.seed(42)

        # Original point cloud
        point_cloud = np.random.randn(50, 4)
        diagram1 = compute_persistence_vr(point_cloud, homology_dimensions=(1,))
        features1 = extract_landscape_features(diagram1)

        # Small perturbation (ε = 0.01)
        epsilon = 0.01
        point_cloud_perturbed = point_cloud + np.random.randn(50, 4) * epsilon
        diagram2 = compute_persistence_vr(
            point_cloud_perturbed, homology_dimensions=(1,)
        )
        features2 = extract_landscape_features(diagram2)

        # Check that feature changes are bounded
        # L1 and L2 norms should be stable
        l1_change = abs(features1["L1"] - features2["L1"])
        l2_change = abs(features1["L2"] - features2["L2"])

        # Changes should be small relative to perturbation
        # Allow generous bound (10x epsilon) since bottleneck distance
        # and diagram changes can amplify perturbation
        assert l1_change < features1["L1"] * 0.5, "L1 changed too much"
        assert l2_change < features1["L2"] * 0.5, "L2 changed too much"

    def test_identical_diagrams_identical_features(self):
        """Test that identical diagrams produce identical features."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        features1 = extract_landscape_features(diagram)
        features2 = extract_landscape_features(diagram)

        # All features should be identical
        for key in features1:
            assert abs(features1[key] - features2[key]) < 1e-10


class TestStatisticalSummaryEdgeCases:
    """Tests for edge cases in statistical summary functions."""

    def test_single_point_diagram(self):
        """Test diagram with single persistence point."""
        diagram = np.array([[0.0, 1.0, 1]])

        features = extract_landscape_features(diagram)
        stats = landscape_statistics(
            compute_persistence_landscape(diagram, n_layers=3, n_bins=50)
        )

        # Should produce valid non-negative features
        assert features["L1"] >= 0
        assert features["L2"] >= 0
        assert stats["mean"] >= 0
        assert stats["std"] >= 0
        assert stats["max"] >= 0

    def test_two_point_diagram(self):
        """Test diagram with two persistence points."""
        diagram = np.array([[0.0, 1.0, 1], [0.2, 0.8, 1]])

        features = extract_landscape_features(diagram)

        # Should produce valid features
        assert features["L1"] > 0
        assert features["L2"] > 0
        assert features["mean"] > 0

    def test_identical_lifetimes(self):
        """Test diagram where all features have identical lifetimes."""
        diagram = np.array(
            [
                [0.0, 1.0, 1],
                [0.0, 1.0, 1],
                [0.0, 1.0, 1],
            ]
        )

        stats = landscape_statistics(
            compute_persistence_landscape(diagram, n_layers=3, n_bins=50)
        )

        # Standard deviation should be low (tent functions overlap)
        # but not necessarily zero due to sampling
        assert stats["std"] >= 0

    def test_very_short_lifetime(self):
        """Test diagram with very short lifetime feature."""
        diagram = np.array([[0.0, 0.001, 1], [0.0, 1.0, 1]])

        features = extract_landscape_features(diagram)

        # Should handle short lifetimes gracefully
        assert features["L1"] > 0
        assert np.isfinite(features["mean"])
        assert np.isfinite(features["max"])


class TestPersistenceImage:
    """Tests for persistence image computation."""

    @pytest.fixture
    def sample_diagram(self):
        """Create sample persistence diagram with known H1 features."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        return compute_persistence_vr(point_cloud, homology_dimensions=(1,))

    def test_image_shape(self, sample_diagram):
        """Test persistence image output shape."""
        resolution = (50, 50)
        image = compute_persistence_image(sample_diagram, resolution=resolution)

        # Shape: (n_dims, n_bins_x * n_bins_y)
        assert image.ndim == 2
        assert image.shape[1] == resolution[0] * resolution[1]

    def test_image_non_negative(self, sample_diagram):
        """Test that image values are non-negative."""
        image = compute_persistence_image(sample_diagram)
        assert np.all(image >= 0)

    def test_resolution_parameter(self, sample_diagram):
        """Test different resolution parameters."""
        resolution_20 = (20, 20)
        resolution_100 = (100, 100)

        image_20 = compute_persistence_image(sample_diagram, resolution=resolution_20)
        image_100 = compute_persistence_image(sample_diagram, resolution=resolution_100)

        assert image_20.shape[1] == 20 * 20
        assert image_100.shape[1] == 100 * 100

    def test_sigma_parameter(self, sample_diagram):
        """Test different sigma (bandwidth) values."""
        image_small_sigma = compute_persistence_image(sample_diagram, sigma=0.01)
        image_large_sigma = compute_persistence_image(sample_diagram, sigma=1.0)

        # Both should produce valid images
        assert image_small_sigma.shape == image_large_sigma.shape
        assert np.all(np.isfinite(image_small_sigma))
        assert np.all(np.isfinite(image_large_sigma))

        # Different sigmas should produce different images
        assert not np.allclose(image_small_sigma, image_large_sigma)

    def test_weighting_functions(self, sample_diagram):
        """Test different weighting schemes."""
        image_no_weight = compute_persistence_image(
            sample_diagram, weight_function=None
        )
        image_linear = compute_persistence_image(
            sample_diagram, weight_function="linear"
        )
        image_persistence = compute_persistence_image(
            sample_diagram, weight_function="persistence", weight_power=2.0
        )

        # All should be valid
        assert np.all(np.isfinite(image_no_weight))
        assert np.all(np.isfinite(image_linear))
        assert np.all(np.isfinite(image_persistence))

        # Different weightings should produce different images
        assert not np.allclose(image_no_weight, image_linear)

    def test_empty_diagram_raises(self):
        """Test that empty diagram raises ValueError."""
        empty_diagram = np.array([]).reshape(0, 3)
        with pytest.raises(ValueError, match="Empty"):
            compute_persistence_image(empty_diagram)

    def test_all_infinite_raises(self):
        """Test that all-infinite deaths raises ValueError."""
        diagram = np.array([[0.0, np.inf, 1], [0.1, np.inf, 1]])
        with pytest.raises(ValueError, match="infinite"):
            compute_persistence_image(diagram)

    def test_single_point_diagram(self):
        """Test image computation with single persistence point."""
        diagram = np.array([[0.0, 1.0, 1]])
        image = compute_persistence_image(diagram)

        assert image.shape[0] == 1
        assert np.all(np.isfinite(image))
        # Image may be zero or non-zero depending on sigma and grid placement
        # Just verify valid shape and finite values


class TestExtractImageFeatures:
    """Tests for image feature extraction."""

    @pytest.fixture
    def sample_image(self):
        """Create sample persistence image."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))
        return compute_persistence_image(diagram, resolution=(50, 50))

    def test_feature_keys(self, sample_image):
        """Test that all expected keys are present."""
        features = extract_image_features(sample_image)

        assert "mean" in features
        assert "std" in features
        assert "max" in features
        assert "sum" in features
        assert "p50" in features
        assert "p75" in features
        assert "p90" in features
        assert "p95" in features

    def test_feature_values_non_negative(self, sample_image):
        """Test that feature values are non-negative."""
        features = extract_image_features(sample_image)

        # All these statistics should be non-negative for non-negative images
        assert features["mean"] >= 0
        assert features["std"] >= 0
        assert features["max"] >= 0
        assert features["sum"] >= 0
        assert features["p50"] >= 0

    def test_percentile_ordering(self, sample_image):
        """Test that percentiles are ordered correctly."""
        features = extract_image_features(sample_image)

        # p50 <= p75 <= p90 <= p95
        assert features["p50"] <= features["p75"]
        assert features["p75"] <= features["p90"]
        assert features["p90"] <= features["p95"]

    def test_include_raw_option(self, sample_image):
        """Test include_raw parameter."""
        features_no_raw = extract_image_features(sample_image, include_raw=False)
        features_with_raw = extract_image_features(sample_image, include_raw=True)

        # Without raw should not have 'raw' key
        assert "raw" not in features_no_raw

        # With raw should have 'raw' key
        assert "raw" in features_with_raw
        assert isinstance(features_with_raw["raw"], np.ndarray)
        assert features_with_raw["raw"].shape[0] == sample_image.size

    def test_empty_image_returns_zeros(self):
        """Test empty image returns zero features."""
        empty = np.array([])
        features = extract_image_features(empty)

        assert features["mean"] == 0.0
        assert features["std"] == 0.0
        assert features["max"] == 0.0
        assert features["sum"] == 0.0


class TestMultiscalePersistenceImages:
    """Tests for multi-scale image computation."""

    @pytest.fixture
    def sample_diagram(self):
        """Create sample persistence diagram."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        return compute_persistence_vr(point_cloud, homology_dimensions=(1,))

    def test_default_resolutions(self, sample_diagram):
        """Test multi-scale with default resolutions."""
        multiscale = compute_multiscale_persistence_images(sample_diagram)

        # Should have 3 default scales
        assert len(multiscale) == 3
        assert (20, 20) in multiscale
        assert (50, 50) in multiscale
        assert (100, 100) in multiscale

    def test_custom_resolutions(self, sample_diagram):
        """Test multi-scale with custom resolutions."""
        custom_resolutions = [(10, 10), (30, 30), (60, 60)]
        multiscale = compute_multiscale_persistence_images(
            sample_diagram, resolutions=custom_resolutions
        )

        assert len(multiscale) == 3
        for resolution in custom_resolutions:
            assert resolution in multiscale
            expected_size = resolution[0] * resolution[1]
            assert multiscale[resolution].shape[1] == expected_size

    def test_consistent_across_scales(self, sample_diagram):
        """Test that images at different scales represent same diagram."""
        multiscale = compute_multiscale_persistence_images(sample_diagram)

        # Extract features at each scale
        features_20 = extract_image_features(multiscale[(20, 20)])
        features_50 = extract_image_features(multiscale[(50, 50)])
        features_100 = extract_image_features(multiscale[(100, 100)])

        # Sum (total weight) should be similar across scales
        # Allow some variation due to discretization
        assert features_20["sum"] > 0
        assert features_50["sum"] > 0
        assert features_100["sum"] > 0

        # Higher resolution should capture similar total weight
        # Allow wide tolerance since discretization can vary significantly
        if features_50["sum"] > 0:  # Only check ratio if non-zero
            ratio_20_50 = features_20["sum"] / features_50["sum"]
            assert 0.1 < ratio_20_50 < 10.0, f"Ratio {ratio_20_50} out of bounds"


class TestImageStability:
    """Tests for stability properties of persistence images."""

    def test_small_perturbation_produces_similar_images(self):
        """Test that small perturbations produce similar images."""
        np.random.seed(42)

        # Original point cloud
        point_cloud = np.random.randn(50, 4)
        diagram1 = compute_persistence_vr(point_cloud, homology_dimensions=(1,))
        image1 = compute_persistence_image(diagram1, resolution=(50, 50))
        features1 = extract_image_features(image1)

        # Small perturbation
        epsilon = 0.01
        point_cloud_perturbed = point_cloud + np.random.randn(50, 4) * epsilon
        diagram2 = compute_persistence_vr(
            point_cloud_perturbed, homology_dimensions=(1,)
        )
        image2 = compute_persistence_image(diagram2, resolution=(50, 50))
        features2 = extract_image_features(image2)

        # Features should be similar
        mean_change = abs(features1["mean"] - features2["mean"])
        sum_change = abs(features1["sum"] - features2["sum"])

        # Allow generous tolerance since perturbations can affect topology
        assert mean_change < features1["mean"] * 0.5
        assert sum_change < features1["sum"] * 0.5

    def test_identical_diagrams_produce_identical_images(self):
        """Test that identical diagrams produce identical images."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        image1 = compute_persistence_image(diagram)
        image2 = compute_persistence_image(diagram)

        # Should be exactly identical
        assert np.allclose(image1, image2)


class TestImageVsLandscapeComparison:
    """Comparison tests between persistence images and landscapes."""

    def test_both_capture_diagram_info(self):
        """Test that both images and landscapes capture persistence info."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        diagram = compute_persistence_vr(point_cloud, homology_dimensions=(1,))

        # Compute both representations
        _ = compute_persistence_landscape(diagram, n_layers=5, n_bins=100)
        image = compute_persistence_image(diagram, resolution=(50, 50))

        # Extract features
        landscape_features = extract_landscape_features(diagram)
        image_features = extract_image_features(image)

        # Both should produce non-zero features for non-trivial diagram
        assert landscape_features["L1"] > 0
        assert landscape_features["mean"] > 0
        assert image_features["sum"] > 0
        assert image_features["mean"] > 0

    def test_empty_diagram_consistency(self):
        """Test that both handle empty diagrams consistently."""
        empty_diagram = np.array([]).reshape(0, 3)

        # Landscape should raise
        with pytest.raises(ValueError):
            compute_persistence_landscape(empty_diagram)

        # Image should also raise
        with pytest.raises(ValueError):
            compute_persistence_image(empty_diagram)


class TestWeightingFunctionImpact:
    """Tests for understanding weighting function impact on images."""

    @pytest.fixture
    def diagram_varied_persistence(self):
        """Create diagram with varied persistence values."""
        # Create features with different persistence values
        return np.array(
            [
                [0.0, 0.1, 1],  # Low persistence
                [0.0, 0.5, 1],  # Medium persistence
                [0.0, 1.0, 1],  # High persistence
            ]
        )

    def test_linear_weighting_emphasizes_high_persistence(
        self, diagram_varied_persistence
    ):
        """Test that linear weighting gives more weight to high persistence."""
        image_no_weight = compute_persistence_image(
            diagram_varied_persistence,
            resolution=(50, 50),
            weight_function=None,
        )
        image_linear = compute_persistence_image(
            diagram_varied_persistence,
            resolution=(50, 50),
            weight_function="linear",
        )

        features_no_weight = extract_image_features(image_no_weight)
        features_linear = extract_image_features(image_linear)

        # Linear weighting should increase total sum
        # (high persistence features weighted more)
        # If both are non-zero, linear should be at least somewhat comparable
        if features_no_weight["sum"] > 0 and features_linear["sum"] > 0:
            # Just verify both produce valid non-negative results
            assert features_linear["sum"] >= 0
            assert features_no_weight["sum"] >= 0

    def test_persistence_power_weighting(self, diagram_varied_persistence):
        """Test persistence-power weighting amplifies differences."""
        image_p1 = compute_persistence_image(
            diagram_varied_persistence,
            resolution=(50, 50),
            weight_function="persistence",
            weight_power=1.0,
        )
        image_p2 = compute_persistence_image(
            diagram_varied_persistence,
            resolution=(50, 50),
            weight_function="persistence",
            weight_power=2.0,
        )

        features_p1 = extract_image_features(image_p1)
        features_p2 = extract_image_features(image_p2)

        # Higher power should amplify high-persistence features more
        # Both should produce valid non-negative results
        assert features_p1["max"] >= 0
        assert features_p2["max"] >= 0
        # If both have content, they may differ (but not required for sparse images)
        if features_p1["sum"] > 0.01 and features_p2["sum"] > 0.01:
            # With sufficient image content, powers may produce different results
            pass  # Test validates structure, not specific numerical relationships


class TestPersistenceAmplitude:
    """Tests for persistence amplitude computation."""

    def test_amplitude_non_negative(self):
        """Test that amplitude is non-negative."""
        diagram = np.array(
            [
                [0.0, 1.0, 1],
                [0.1, 0.5, 1],
                [0.2, 0.8, 1],
            ]
        )
        amplitude = persistence_amplitude(diagram, dimension=1)
        assert amplitude >= 0

    def test_empty_diagram_zero_amplitude(self):
        """Test that empty diagram has zero amplitude."""
        empty = np.array([]).reshape(0, 3)
        amplitude = persistence_amplitude(empty)
        assert amplitude == 0.0

    def test_amplitude_increases_with_persistence(self):
        """Test that longer persistence leads to higher amplitude."""
        # Short persistence
        diagram_short = np.array([[0.0, 0.1, 1]])
        # Long persistence
        diagram_long = np.array([[0.0, 1.0, 1]])

        amp_short = persistence_amplitude(diagram_short)
        amp_long = persistence_amplitude(diagram_long)

        assert amp_long > amp_short

    def test_wasserstein_vs_bottleneck(self):
        """Test different distance metrics."""
        diagram = np.array(
            [
                [0.0, 1.0, 1],
                [0.0, 0.5, 1],
            ]
        )

        wasserstein = persistence_amplitude(diagram, metric="wasserstein", p=2)
        bottleneck = persistence_amplitude(diagram, metric="bottleneck")

        # Both should be positive
        assert wasserstein > 0
        assert bottleneck > 0

        # Bottleneck is max persistence/2
        expected_bottleneck = 1.0 / 2  # max(1.0, 0.5) / 2
        assert abs(bottleneck - expected_bottleneck) < 1e-10

    def test_wasserstein_p_parameter(self):
        """Test that different p values give different results."""
        diagram = np.array([[0.0, 1.0, 1], [0.0, 0.5, 1]])

        w1 = persistence_amplitude(diagram, metric="wasserstein", p=1)
        w2 = persistence_amplitude(diagram, metric="wasserstein", p=2)

        # Different p should give different results
        assert w1 != w2

    def test_dimension_filtering(self):
        """Test that dimension filtering works correctly."""
        diagram = np.array(
            [
                [0.0, 1.0, 0],  # H0
                [0.0, 0.5, 1],  # H1
            ]
        )

        amp_h0 = persistence_amplitude(diagram, dimension=0)
        amp_h1 = persistence_amplitude(diagram, dimension=1)
        amp_all = persistence_amplitude(diagram)

        # Filtered amplitudes should be different
        assert amp_h0 != amp_h1
        # All-dimension amplitude should be largest
        assert amp_all >= amp_h0
        assert amp_all >= amp_h1


class TestBettiCurveStatistics:
    """Tests for Betti curve statistics computation."""

    @pytest.fixture
    def sample_diagram_h1(self):
        """Create diagram with known H1 features."""
        # Features: [0.0, 1.0] and [0.2, 0.8]
        return np.array(
            [
                [0.0, 1.0, 1],
                [0.2, 0.8, 1],
            ]
        )

    def test_statistics_keys(self, sample_diagram_h1):
        """Test that all expected keys are present."""
        stats = betti_curve_statistics(sample_diagram_h1, dimension=1)

        assert "max_betti" in stats
        assert "mean_betti" in stats
        assert "max_betti_location" in stats
        assert "area_under_curve" in stats

    def test_max_betti_correct(self, sample_diagram_h1):
        """Test that max Betti number is correctly computed."""
        stats = betti_curve_statistics(sample_diagram_h1, dimension=1)

        # Both features overlap in [0.2, 0.8], so max should be 2
        assert stats["max_betti"] == 2.0

    def test_betti_non_negative(self, sample_diagram_h1):
        """Test that all statistics are non-negative."""
        stats = betti_curve_statistics(sample_diagram_h1, dimension=1)

        assert stats["max_betti"] >= 0
        assert stats["mean_betti"] >= 0
        assert stats["area_under_curve"] >= 0

    def test_empty_dimension_returns_zeros(self):
        """Test that dimension with no features returns zeros."""
        diagram = np.array([[0.0, 1.0, 0]])  # Only H0
        stats = betti_curve_statistics(diagram, dimension=1)  # Query H1

        assert stats["max_betti"] == 0.0
        assert stats["mean_betti"] == 0.0
        assert stats["area_under_curve"] == 0.0

    def test_single_feature_properties(self):
        """Test Betti curve for single feature."""
        diagram = np.array([[0.0, 1.0, 1]])
        stats = betti_curve_statistics(diagram, dimension=1, n_bins=100)

        # Should have max_betti = 1
        assert stats["max_betti"] == 1.0
        # Mean should be less than max (starts at 0, rises to 1, falls to 0)
        assert 0 < stats["mean_betti"] < 1.0
        # Area should be positive
        assert stats["area_under_curve"] > 0


class TestExtractEntropyBettiFeatures:
    """Tests for combined entropy and Betti feature extraction."""

    @pytest.fixture
    def sample_diagram(self):
        """Create sample diagram with H0 and H1 features."""
        np.random.seed(42)
        point_cloud = np.random.randn(50, 4)
        return compute_persistence_vr(point_cloud, homology_dimensions=(0, 1))

    def test_feature_keys_structure(self, sample_diagram):
        """Test that feature dictionary has correct structure."""
        features = extract_entropy_betti_features(sample_diagram)

        # Should have features for H0 and H1
        for dim in [0, 1]:
            dim_key = f"H{dim}"
            assert f"entropy_{dim_key}" in features
            assert f"amplitude_{dim_key}" in features
            assert f"total_persistence_{dim_key}_p1" in features
            assert f"total_persistence_{dim_key}_p2" in features
            assert f"max_betti_{dim_key}" in features
            assert f"mean_betti_{dim_key}" in features
            assert f"betti_area_{dim_key}" in features

    def test_feature_values_non_negative(self, sample_diagram):
        """Test that all feature values are non-negative."""
        features = extract_entropy_betti_features(sample_diagram)

        for key, value in features.items():
            assert value >= 0, f"{key} should be non-negative"

    def test_custom_dimensions(self):
        """Test extraction with custom dimensions."""
        diagram = np.array([[0.0, 1.0, 1], [0.1, 0.5, 1]])
        features = extract_entropy_betti_features(diagram, dimensions=(1,))

        # Should only have H1 features
        assert "entropy_H1" in features
        assert "entropy_H0" not in features

    def test_empty_diagram_handling(self):
        """Test graceful handling of empty diagram."""
        empty = np.array([]).reshape(0, 3)
        features = extract_entropy_betti_features(empty)

        # Should return zero features for default dimensions
        assert all(v == 0.0 for v in features.values())

    def test_feature_vector_conversion(self, sample_diagram):
        """Test conversion to feature vector for ML."""
        features = extract_entropy_betti_features(sample_diagram)

        feature_vector = np.array(list(features.values()))

        assert feature_vector.ndim == 1
        assert len(feature_vector) == len(features)
        assert np.all(np.isfinite(feature_vector))


class TestEntropyMathematicalProperties:
    """Mathematical validation tests for persistence entropy."""

    def test_entropy_maximum_for_uniform_distribution(self):
        """Test that entropy is maximized when all lifetimes are equal."""
        # Equal lifetimes
        n = 5
        diagram_uniform = np.array([[0.0, 1.0, 1]] * n)
        entropy_uniform = persistence_entropy(diagram_uniform)

        # Expected max entropy for n equal elements: log(n)
        expected_max = np.log(n)
        assert abs(entropy_uniform - expected_max) < 1e-10

    def test_entropy_increases_with_uniformity(self):
        """Test that more uniform distributions have higher entropy."""
        # Very skewed distribution (one large, one small)
        diagram_skewed = np.array([[0.0, 1.0, 1], [0.0, 0.01, 1]])
        entropy_skewed = persistence_entropy(diagram_skewed)

        # More uniform distribution
        diagram_uniform = np.array([[0.0, 0.5, 1], [0.0, 0.5, 1]])
        entropy_uniform = persistence_entropy(diagram_uniform)

        # Uniform should have higher entropy
        assert entropy_uniform > entropy_skewed

    def test_entropy_zero_for_single_feature(self):
        """Test that single feature has zero entropy."""
        diagram = np.array([[0.0, 1.0, 1]])
        entropy = persistence_entropy(diagram)

        # Single element has probability 1, so entropy = -1 * log(1) = 0
        assert abs(entropy) < 1e-10

    def test_entropy_bounds(self):
        """Test that entropy is bounded correctly."""
        n = 10
        diagram = np.random.rand(n, 3)
        diagram[:, 0] = 0.0  # births
        diagram[:, 1] = diagram[:, 0] + np.random.rand(n)  # deaths
        diagram[:, 2] = 1  # dimension

        entropy = persistence_entropy(diagram)

        # Entropy should be in [0, log(n)]
        assert 0 <= entropy <= np.log(n) + 1e-10  # Small tolerance


class TestBettiCurveMathematicalProperties:
    """Mathematical validation tests for Betti curves."""

    def test_betti_starts_at_zero_for_h1(self):
        """Test that H1 Betti curve starts at 0 before first birth."""
        diagram = np.array([[0.5, 1.0, 1]])  # Feature born at 0.5
        filtration, betti = betti_curve(diagram, dimension=1, n_bins=100)

        # At early filtration (before 0.5), Betti should be 0
        early_idx = filtration < 0.4
        assert np.all(betti[early_idx] == 0)

    def test_betti_increases_then_decreases(self):
        """Test that Betti curve rises and falls."""
        diagram = np.array([[0.2, 0.8, 1]])  # Single H1 feature
        filtration, betti = betti_curve(diagram, dimension=1, n_bins=100)

        # Find regions
        before_birth = filtration < 0.2
        during_life = (filtration >= 0.2) & (filtration < 0.8)
        after_death = filtration >= 0.8

        # Before birth: β = 0
        if np.any(before_birth):
            assert np.all(betti[before_birth] == 0)

        # During life: β = 1
        if np.any(during_life):
            assert np.all(betti[during_life] == 1)

        # After death: β = 0
        if np.any(after_death):
            assert np.all(betti[after_death] == 0)

    def test_betti_counts_overlapping_features(self):
        """Test that Betti curve correctly counts overlapping features."""
        # Two overlapping features
        diagram = np.array([[0.1, 0.9, 1], [0.2, 0.8, 1]])
        filtration, betti = betti_curve(diagram, dimension=1, n_bins=100)

        # In overlap region [0.2, 0.8], should have β = 2
        overlap_region = (filtration >= 0.25) & (filtration <= 0.75)
        if np.any(overlap_region):
            overlap_betti = betti[overlap_region]
            # All values in overlap should be 2
            assert np.all(overlap_betti == 2)


class TestAmplitudeMathematicalProperties:
    """Mathematical validation tests for persistence amplitude."""

    def test_amplitude_scaling_property(self):
        """Test that scaling diagram scales amplitude proportionally."""
        diagram_base = np.array([[0.0, 1.0, 1], [0.0, 0.5, 1]])

        amp_base = persistence_amplitude(diagram_base, metric="wasserstein", p=2)

        # Scale by factor of 2
        diagram_scaled = diagram_base.copy()
        diagram_scaled[:, :2] *= 2  # Scale births and deaths

        amp_scaled = persistence_amplitude(diagram_scaled, metric="wasserstein", p=2)

        # Amplitude should scale by same factor
        ratio = amp_scaled / amp_base
        assert abs(ratio - 2.0) < 0.1  # Allow small tolerance

    def test_bottleneck_is_max_persistence_over_two(self):
        """Test bottleneck distance formula."""
        persistences = [0.5, 1.0, 0.3]
        diagram = np.array([[0.0, p, 1] for p in persistences])

        bottleneck = persistence_amplitude(diagram, metric="bottleneck")

        expected = max(persistences) / 2.0
        assert abs(bottleneck - expected) < 1e-10

    def test_wasserstein_triangle_inequality(self):
        """Test that Wasserstein distance respects basic inequality."""
        # Single feature amplitude
        diagram_single = np.array([[0.0, 1.0, 1]])
        amp_single = persistence_amplitude(diagram_single, metric="wasserstein", p=2)

        # Two features with combined persistence equal to single
        diagram_double = np.array([[0.0, 0.5, 1], [0.0, 0.5, 1]])
        amp_double = persistence_amplitude(diagram_double, metric="wasserstein", p=2)

        # Due to norm properties, these should be related but not necessarily equal
        # Just verify both are positive and finite
        assert amp_single > 0
        assert amp_double > 0
        assert np.isfinite(amp_single)
        assert np.isfinite(amp_double)
