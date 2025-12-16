"""
Test to verify the ARI matrix fix in results_framework.py

This test ensures that record_comparison_result() properly computes
and populates ARI scores between methods.
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import pytest

from poverty_tda.validation.results_framework import record_comparison_result


def test_ari_matrix_is_populated():
    """Test that ARI matrix is populated with pairwise scores."""
    # Create synthetic test data
    np.random.seed(42)
    n = 100

    points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]

    # Create different cluster assignments
    base_labels = np.array([0] * 33 + [1] * 33 + [2] * 34)
    method1_labels = base_labels.copy()
    method2_labels = base_labels.copy()
    # Swap some labels to make them similar but not identical
    swap_idx = np.random.choice(n, size=15, replace=False)
    method2_labels[swap_idx] = (method2_labels[swap_idx] + 1) % 3

    gdf = gpd.GeoDataFrame(
        {
            "geometry": points,
            "ms_basin": method1_labels,
            "kmeans": method2_labels,
            "life_expectancy": np.random.rand(n) * 20 + 70,
        }
    )

    # Call the function
    result = record_comparison_result(
        name="test_ari_fix",
        description="Test that ARI matrix is populated",
        region="Test Region",
        gdf=gdf,
        method_columns={
            "Morse-Smale": "ms_basin",
            "K-means": "kmeans",
        },
        outcome_column="life_expectancy",
        random_seed=42,
    )

    # Assertions
    assert result.ari_matrix is not None, "ARI matrix should not be None"
    assert len(result.ari_matrix) > 0, "ARI matrix should not be empty"
    assert "Morse-Smale vs K-means" in result.ari_matrix, "Should have MS vs KM pair"

    # Check ARI value is in valid range
    ari_value = result.ari_matrix["Morse-Smale vs K-means"]
    assert -1 <= ari_value <= 1, f"ARI should be in [-1, 1], got {ari_value}"


def test_method_ari_vs_others_populated():
    """Test that each method has ari_vs_others populated."""
    np.random.seed(42)
    n = 50

    points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]
    gdf = gpd.GeoDataFrame(
        {
            "geometry": points,
            "method1": np.random.randint(0, 3, n),
            "method2": np.random.randint(0, 3, n),
            "outcome": np.random.rand(n),
        }
    )

    result = record_comparison_result(
        name="test",
        description="Test",
        region="Test",
        gdf=gdf,
        method_columns={"M1": "method1", "M2": "method2"},
        outcome_column="outcome",
    )

    # Check both methods have ari_vs_others
    assert len(result.methods) == 2, "Should have 2 methods"

    for method in result.methods:
        assert method.ari_vs_others is not None, f"{method.name} ari_vs_others should not be None"
        assert len(method.ari_vs_others) > 0, f"{method.name} should have ari_vs_others entries"


def test_ari_values_are_symmetric():
    """Test that ARI(A,B) is accessible from both methods."""
    np.random.seed(42)
    n = 50

    points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]
    gdf = gpd.GeoDataFrame(
        {
            "geometry": points,
            "method1": np.random.randint(0, 3, n),
            "method2": np.random.randint(0, 3, n),
            "outcome": np.random.rand(n),
        }
    )

    result = record_comparison_result(
        name="test",
        description="Test",
        region="Test",
        gdf=gdf,
        method_columns={"M1": "method1", "M2": "method2"},
        outcome_column="outcome",
    )

    # Get ARI from both methods
    m1_ari = result.methods[0].ari_vs_others.get("M2")
    m2_ari = result.methods[1].ari_vs_others.get("M1")

    assert m1_ari is not None, "M1 should have ARI vs M2"
    assert m2_ari is not None, "M2 should have ARI vs M1"
    assert m1_ari == m2_ari, "ARI should be symmetric"


def test_multiple_methods():
    """Test ARI matrix with 3+ methods."""
    np.random.seed(42)
    n = 50

    points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]
    gdf = gpd.GeoDataFrame(
        {
            "geometry": points,
            "method1": np.random.randint(0, 3, n),
            "method2": np.random.randint(0, 3, n),
            "method3": np.random.randint(0, 3, n),
            "outcome": np.random.rand(n),
        }
    )

    result = record_comparison_result(
        name="test",
        description="Test",
        region="Test",
        gdf=gdf,
        method_columns={"M1": "method1", "M2": "method2", "M3": "method3"},
        outcome_column="outcome",
    )

    # With 3 methods, should have 3 pairwise comparisons
    assert len(result.ari_matrix) == 3, "Should have 3 pairwise ARIs for 3 methods"

    # Each method should have 2 ARI scores (vs the other 2 methods)
    for method in result.methods:
        assert len(method.ari_vs_others) == 2, f"{method.name} should have 2 ARI scores"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
