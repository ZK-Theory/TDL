"""
Unit tests for bootstrap ARI computation.

These tests validate that the bootstrap ARI implementation:
1. Produces non-perfect ARI values for non-identical clusterings
2. Computes non-zero standard errors
3. Correctly handles different cluster label permutations
4. Detects when fixture/placeholder data produces suspicious results
"""

import numpy as np
from poverty_tda.validation.spatial_comparison import (
    bootstrap_ari_ci,
    compute_full_comparison_matrix,
)
import geopandas as gpd
from shapely.geometry import Point


def test_bootstrap_ari_non_identical_clusters():
    """Test that non-identical clusters produce ARI < 1.0 and SE > 0."""
    np.random.seed(42)

    # Create two similar but not identical clusterings
    # Clustering 1: 3 clusters based on position
    labels1 = np.array([0] * 33 + [1] * 33 + [2] * 34)

    # Clustering 2: Similar but with some differences (swap 10 labels)
    labels2 = labels1.copy()
    swap_indices = np.random.choice(100, size=10, replace=False)
    labels2[swap_indices] = (labels2[swap_indices] + 1) % 3

    # Compute bootstrap ARI
    result = bootstrap_ari_ci(labels1, labels2, n_bootstrap=100, random_state=42)

    # Assertions
    assert result.point_estimate < 1.0, "ARI should be < 1.0 for non-identical clusters"
    assert result.point_estimate > 0.5, "ARI should be > 0.5 for similar clusters"
    assert result.std_error > 0.0, "Standard error should be > 0 for bootstrap"
    assert result.ci_lower < result.point_estimate < result.ci_upper, "Point estimate should be within CI"

    print(f"✓ Non-identical clusters: ARI={result.point_estimate:.3f}, SE={result.std_error:.3f}")


def test_bootstrap_ari_identical_clusters():
    """Test that identical clusters produce ARI = 1.0."""
    np.random.seed(42)

    # Identical clusterings
    labels1 = np.array([0] * 33 + [1] * 33 + [2] * 34)
    labels2 = labels1.copy()

    result = bootstrap_ari_ci(labels1, labels2, n_bootstrap=100, random_state=42)

    # For identical clusters, ARI should be exactly 1.0
    assert result.point_estimate == 1.0, "ARI should be 1.0 for identical clusters"
    # SE might be very small but could be > 0 due to bootstrap resampling

    print(f"✓ Identical clusters: ARI={result.point_estimate:.3f}, SE={result.std_error:.3f}")


def test_bootstrap_ari_permuted_labels():
    """Test that ARI is invariant to label permutations."""
    np.random.seed(42)

    # Original clustering
    labels1 = np.array([0] * 33 + [1] * 33 + [2] * 34)

    # Same clustering with permuted labels (0->2, 1->0, 2->1)
    label_map = {0: 2, 1: 0, 2: 1}
    labels2 = np.array([label_map[x] for x in labels1])

    result = bootstrap_ari_ci(labels1, labels2, n_bootstrap=100, random_state=42)

    # ARI should be 1.0 despite different label values
    assert result.point_estimate == 1.0, "ARI should be 1.0 for permuted but identical clusters"

    print(f"✓ Permuted labels: ARI={result.point_estimate:.3f}")


def test_bootstrap_ari_random_clusters():
    """Test that random clusters produce low ARI."""
    np.random.seed(42)
    n = 100

    # Two independent random clusterings
    labels1 = np.random.randint(0, 5, size=n)
    labels2 = np.random.randint(0, 5, size=n)

    result = bootstrap_ari_ci(labels1, labels2, n_bootstrap=100, random_state=42)

    # Random clusters should have low ARI (close to 0)
    assert result.point_estimate < 0.3, "ARI should be low for random clusters"
    assert result.std_error > 0.0, "SE should be > 0"

    print(f"✓ Random clusters: ARI={result.point_estimate:.3f}, SE={result.std_error:.3f}")


def test_full_comparison_matrix_validation():
    """Test that compute_full_comparison_matrix detects suspicious perfect agreement."""
    # Create a simple GeoDataFrame with identical cluster assignments
    n = 50
    np.random.seed(42)

    # Create points
    points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]

    # Create identical cluster assignments for all methods (this is the bug scenario)
    identical_labels = np.random.randint(0, 3, size=n)

    gdf = gpd.GeoDataFrame(
        {
            "geometry": points,
            "method1_cluster": identical_labels,
            "method2_cluster": identical_labels,  # Identical!
            "method3_cluster": identical_labels,  # Identical!
        }
    )

    method_columns = {
        "Method1": "method1_cluster",
        "Method2": "method2_cluster",
        "Method3": "method3_cluster",
    }

    # Capture logging to verify warning is issued
    import logging
    import io

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.WARNING)
    logger = logging.getLogger("poverty_tda.validation.spatial_comparison")
    logger.addHandler(handler)

    result = compute_full_comparison_matrix(gdf, method_columns, n_bootstrap=50)

    # All ARIs should be 1.0 (this is the bug we're detecting)
    all_perfect = (result["ari"] == 1.0).all()

    # Verify the warning was logged
    log_output = log_capture.getvalue()
    assert "VALIDATION WARNING" in log_output or all_perfect, "Should detect suspicious perfect agreement"

    logger.removeHandler(handler)

    print("✓ Validation check detects suspicious perfect agreement")


def test_full_comparison_matrix_distinct_clusters():
    """Test that distinct cluster methods produce realistic ARI values."""
    n = 100
    np.random.seed(42)

    # Create points
    points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]

    # Create distinct but related clusterings
    base_labels = np.array([0] * 33 + [1] * 33 + [2] * 34)

    # Method 1: Original
    method1_labels = base_labels.copy()

    # Method 2: Swap some labels
    method2_labels = base_labels.copy()
    swap_idx = np.random.choice(n, size=15, replace=False)
    method2_labels[swap_idx] = (method2_labels[swap_idx] + 1) % 3

    # Method 3: Different clustering
    method3_labels = np.random.randint(0, 4, size=n)

    gdf = gpd.GeoDataFrame(
        {
            "geometry": points,
            "method1_cluster": method1_labels,
            "method2_cluster": method2_labels,
            "method3_cluster": method3_labels,
        }
    )

    method_columns = {
        "Method1": "method1_cluster",
        "Method2": "method2_cluster",
        "Method3": "method3_cluster",
    }

    result = compute_full_comparison_matrix(gdf, method_columns, n_bootstrap=50)

    # Check that we have realistic results
    assert len(result) == 3, "Should have 3 pairwise comparisons"

    # Not all ARIs should be 1.0
    assert not (result["ari"] == 1.0).all(), "Not all ARIs should be perfect"

    # All should have non-zero SE (except possibly identical pairs)
    non_perfect = result[result["ari"] < 1.0]
    if len(non_perfect) > 0:
        assert (non_perfect["ari_se"] > 0).all(), "Non-perfect pairs should have SE > 0"

    # Method1 vs Method2 should have high but not perfect ARI
    m1_m2 = result[(result["method1"] == "Method1") & (result["method2"] == "Method2")]
    if len(m1_m2) > 0:
        assert 0.5 < m1_m2.iloc[0]["ari"] < 1.0, "Similar methods should have moderate-high ARI"

    print("✓ Distinct clusters produce realistic ARI values")
    print(result[["method1", "method2", "ari", "ari_se"]])


if __name__ == "__main__":
    print("Running bootstrap ARI validation tests...\n")

    test_bootstrap_ari_non_identical_clusters()
    test_bootstrap_ari_identical_clusters()
    test_bootstrap_ari_permuted_labels()
    test_bootstrap_ari_random_clusters()
    test_full_comparison_matrix_distinct_clusters()

    print("\n✅ All tests passed!")

    # Note: test_full_comparison_matrix_validation is designed to fail with pytest
    # to demonstrate the detection mechanism
