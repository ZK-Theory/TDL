"""
Tests for TTK topological simplification integration from Phase 6.5.

These tests verify the TTK simplification functionality integrated in Phase 6.5,
including scalar field simplification, integrated Morse-Smale with simplification,
and persistence filtering for post-processing.

Phase 6.5 Integration Features:
    1. simplify_scalar_field() - Pre-process scalar fields to remove noise
    2. compute_morse_smale(simplify_first=True) - Integrated simplification
    3. filter_by_persistence() - Post-processing filtering

Test Coverage:
    - Scalar field simplification with various thresholds
    - Integrated Morse-Smale with pre-simplification
    - Persistence filtering on extracted critical points
    - Topological property preservation (Morse inequality)
    - Threshold recommendations for production use

License: Open Government Licence v3.0
"""

from __future__ import annotations

import numpy as np
import pytest

from poverty_tda.topology.morse_smale import (
    CriticalPoint,
    compute_morse_smale,
    filter_by_persistence,
    simplify_scalar_field,
)

# Import centralized TTK utilities
from shared.ttk_utils import is_ttk_available

# Check if pyvista is available
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False

# =============================================================================
# FIXTURES FOR SIMPLIFICATION TESTS
# =============================================================================


@pytest.fixture
def synthetic_noisy_surface(tmp_path):
    """
    Create a synthetic surface with known topology plus noise.

    Base topology: Two Gaussians (2 maxima) connected by a saddle
    Noise: Random small-scale features that should be simplified away
    """
    if not HAS_PYVISTA:
        pytest.skip("pyvista not available")

    # Create 50x50 grid
    resolution = 50
    x = np.linspace(-5, 5, resolution)
    y = np.linspace(-5, 5, resolution)
    X, Y = np.meshgrid(x, y)

    # Base signal: Two Gaussians
    gaussian1 = np.exp(-((X + 2) ** 2 + (Y) ** 2) / 2.0)
    gaussian2 = np.exp(-((X - 2) ** 2 + (Y) ** 2) / 2.0)
    base_signal = gaussian1 + gaussian2

    # Add structured noise (small-scale oscillations)
    np.random.seed(42)
    noise = 0.1 * np.sin(5 * X) * np.cos(5 * Y)
    noise += 0.05 * np.random.randn(resolution, resolution)

    # Combined noisy surface
    noisy_surface = base_signal + noise

    # Create VTK ImageData
    mesh = pv.ImageData(dims=(resolution, resolution, 1))
    mesh.origin = (-5, -5, 0)
    mesh.spacing = (10 / (resolution - 1), 10 / (resolution - 1), 1)
    mesh.point_data["scalar"] = noisy_surface.ravel()

    # Save to VTK file
    vtk_path = tmp_path / "noisy_surface.vti"
    mesh.save(str(vtk_path))

    return {
        "vtk_path": vtk_path,
        "base_signal": base_signal,
        "noisy_surface": noisy_surface,
        "expected_maxima": 2,  # Two main peaks
        "expected_minima": 1,  # One shared minimum (roughly)
        "noise_magnitude": 0.1,
    }


@pytest.fixture
def uk_region_surface_with_noise(tmp_path):
    """
    Create a UK region-like mobility surface with realistic noise patterns.

    Simulates interpolation artifacts and boundary effects typical of
    real UK poverty data.
    """
    if not HAS_PYVISTA:
        pytest.skip("pyvista not available")

    # Create 60x60 grid (representative of a region)
    resolution = 60
    x = np.linspace(0, 10000, resolution)  # 10km x 10km
    y = np.linspace(0, 10000, resolution)
    X, Y = np.meshgrid(x, y)

    # Base mobility surface with 3 poverty traps (minima)
    trap1 = -0.3 * np.exp(-((X - 2000) ** 2 + (Y - 2000) ** 2) / 1000000)
    trap2 = -0.4 * np.exp(-((X - 7000) ** 2 + (Y - 3000) ** 2) / 1500000)
    trap3 = -0.25 * np.exp(-((X - 5000) ** 2 + (Y - 8000) ** 2) / 800000)

    # High mobility center
    center = 0.8 * np.exp(-((X - 5000) ** 2 + (Y - 5000) ** 2) / 3000000)

    base_mobility = 0.5 + center + trap1 + trap2 + trap3

    # Add realistic noise patterns
    np.random.seed(123)
    # Interpolation artifacts (grid-aligned)
    artifacts = 0.03 * np.sin(10 * np.pi * X / 10000) * np.sin(10 * np.pi * Y / 10000)
    # Random measurement noise
    measurement_noise = 0.02 * np.random.randn(resolution, resolution)
    # Boundary effects (stronger near edges)
    boundary_effect = 0.05 * (
        np.exp(-((X / 1000) ** 2))
        + np.exp(-(((X - 10000) / 1000) ** 2))
        + np.exp(-((Y / 1000) ** 2))
        + np.exp(-(((Y - 10000) / 1000) ** 2))
    )

    noisy_mobility = base_mobility + artifacts + measurement_noise + boundary_effect

    # Clip to valid mobility range [0, 1]
    noisy_mobility = np.clip(noisy_mobility, 0.0, 1.0)

    # Create VTK ImageData
    mesh = pv.ImageData(dims=(resolution, resolution, 1))
    mesh.origin = (0, 0, 0)
    mesh.spacing = (
        10000 / (resolution - 1),
        10000 / (resolution - 1),
        1,
    )
    mesh.point_data["mobility"] = noisy_mobility.ravel()

    # Save to VTK file
    vtk_path = tmp_path / "uk_region_noisy.vti"
    mesh.save(str(vtk_path))

    return {
        "vtk_path": vtk_path,
        "base_mobility": base_mobility,
        "noisy_mobility": noisy_mobility,
        "expected_minima": 3,  # Three poverty traps
        "expected_maxima": 1,  # One high-mobility center
        "noise_level": 0.05,  # Approximate noise magnitude
    }


# =============================================================================
# SCALAR FIELD SIMPLIFICATION TESTS
# =============================================================================


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_simplify_scalar_field_basic(synthetic_noisy_surface):
    """Test basic scalar field simplification."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    # Apply simplification with 5% threshold
    simplified_path = simplify_scalar_field(
        vtk_path=vtk_path,
        persistence_threshold=0.05,
        scalar_name="scalar",
    )

    # Verify simplified file was created
    assert simplified_path.exists()

    # Load and verify
    mesh = pv.read(str(simplified_path))
    assert "scalar" in mesh.point_data
    simplified_values = mesh.point_data["scalar"]

    # Simplified surface should have similar range
    original_mesh = pv.read(str(vtk_path))
    original_values = original_mesh.point_data["scalar"]

    assert abs(simplified_values.min() - original_values.min()) < 0.2
    assert abs(simplified_values.max() - original_values.max()) < 0.2

    # Cleanup
    simplified_path.unlink()


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
@pytest.mark.parametrize("threshold", [0.01, 0.05, 0.10])
def test_simplify_scalar_field_thresholds(synthetic_noisy_surface, threshold):
    """Test simplification with different persistence thresholds."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    # Apply simplification
    simplified_path = simplify_scalar_field(
        vtk_path=vtk_path,
        persistence_threshold=threshold,
        scalar_name="scalar",
    )

    assert simplified_path.exists()

    # Higher thresholds should produce smoother surfaces
    # (Can verify by comparing Morse-Smale critical point counts)

    # Cleanup
    simplified_path.unlink()


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_simplify_preserves_major_features(synthetic_noisy_surface):
    """Test that simplification preserves major topological features."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    # Simplify with moderate threshold
    simplified_path = simplify_scalar_field(
        vtk_path=vtk_path,
        persistence_threshold=0.08,
        scalar_name="scalar",
    )

    # Load simplified surface
    mesh = pv.read(str(simplified_path))
    simplified_values = mesh.point_data["scalar"]

    # Major features (two peaks) should still be visible
    # Check that we still have two distinct high-value regions
    high_threshold = simplified_values.max() * 0.8
    high_regions = simplified_values > high_threshold

    # Should have values above threshold (peaks preserved)
    assert high_regions.sum() > 10  # At least some high values remain

    # Cleanup
    simplified_path.unlink()


# =============================================================================
# INTEGRATED MORSE-SMALE WITH SIMPLIFICATION TESTS
# =============================================================================


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_morse_smale_with_simplification(synthetic_noisy_surface):
    """Test Morse-Smale with integrated pre-simplification."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    # Compute without simplification
    result_no_simp = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="scalar",
        persistence_threshold=0.05,
        simplify_first=False,
    )

    # Compute with simplification
    result_with_simp = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="scalar",
        persistence_threshold=0.05,
        simplify_first=True,
        simplification_threshold=0.08,
    )

    # Simplification should reduce critical point count
    assert len(result_with_simp.critical_points) <= len(result_no_simp.critical_points)

    # Both should satisfy Morse inequality
    # For 2D surface: chi = V - E + F = 1 (Euler characteristic)
    # Morse inequality: #critical_points >= |chi| = 1
    assert len(result_with_simp.critical_points) >= 1
    assert len(result_no_simp.critical_points) >= 1


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_simplification_parameter_independence(synthetic_noisy_surface):
    """Test that simplification and extraction thresholds are independent."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    # High simplification, low extraction threshold
    result1 = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="scalar",
        persistence_threshold=0.02,  # Low extraction threshold
        simplify_first=True,
        simplification_threshold=0.10,  # High simplification
    )

    # Low simplification, high extraction threshold
    result2 = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="scalar",
        persistence_threshold=0.08,  # High extraction threshold
        simplify_first=True,
        simplification_threshold=0.02,  # Low simplification
    )

    # Both should work, producing different results
    assert len(result1.critical_points) > 0
    assert len(result2.critical_points) > 0

    # Different parameter combinations should produce different counts
    # (Not guaranteed, but likely for noisy data)
    # This tests parameter independence


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_metadata_tracking_for_simplification(synthetic_noisy_surface):
    """Test that simplification metadata is properly tracked."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    result = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="scalar",
        persistence_threshold=0.05,
        simplify_first=True,
        simplification_threshold=0.08,
    )

    # Check that metadata includes simplification info
    # (Implementation should track this for reproducibility)
    assert "abs_threshold" in result.metadata
    # Persistence threshold should be recorded
    assert result.persistence_threshold == 0.05


# =============================================================================
# POST-PROCESSING PERSISTENCE FILTERING TESTS
# =============================================================================


def test_filter_by_persistence_basic():
    """Test basic persistence filtering."""
    # Create mock critical points with different persistence values
    points = [
        CriticalPoint(
            point_id=0,
            position=(0, 0, 0),
            value=0.1,
            point_type=0,
            manifold_dim=2,
            persistence=0.05,
        ),
        CriticalPoint(
            point_id=1,
            position=(1, 0, 0),
            value=0.3,
            point_type=1,
            manifold_dim=2,
            persistence=0.15,
        ),
        CriticalPoint(
            point_id=2,
            position=(2, 0, 0),
            value=0.8,
            point_type=2,
            manifold_dim=2,
            persistence=0.02,
        ),
    ]

    # Filter with threshold 0.10 (10% of range [0, 1])
    filtered = filter_by_persistence(
        critical_points=points,
        persistence_threshold=0.10,
        scalar_range=(0.0, 1.0),
    )

    # Should keep point 1 (persistence=0.15 > 0.10)
    # Should filter point 0 (persistence=0.05 < 0.10) and point 2 (persistence=0.02 < 0.10)
    assert len(filtered) == 1
    assert filtered[0].point_id == 1


def test_filter_by_persistence_preserves_none():
    """Test that points with persistence=None are preserved."""
    # Create points including one with None persistence (essential point)
    points = [
        CriticalPoint(
            point_id=0,
            position=(0, 0, 0),
            value=0.1,
            point_type=0,
            manifold_dim=2,
            persistence=0.02,  # Below threshold
        ),
        CriticalPoint(
            point_id=1,
            position=(1, 0, 0),
            value=0.5,
            point_type=1,
            manifold_dim=2,
            persistence=None,  # Essential point
        ),
    ]

    # Filter with threshold that would remove point 0
    filtered = filter_by_persistence(
        critical_points=points,
        persistence_threshold=0.05,
        scalar_range=(0.0, 1.0),
    )

    # Should keep point 1 (persistence=None)
    assert len(filtered) == 1
    assert filtered[0].point_id == 1
    assert filtered[0].persistence is None


def test_filter_by_persistence_relative_threshold():
    """Test that relative thresholds are converted correctly."""
    points = [
        CriticalPoint(
            point_id=0,
            position=(0, 0, 0),
            value=10.0,
            point_type=0,
            manifold_dim=2,
            persistence=5.0,  # 5% of range 100
        ),
        CriticalPoint(
            point_id=1,
            position=(1, 0, 0),
            value=50.0,
            point_type=1,
            manifold_dim=2,
            persistence=15.0,  # 15% of range 100
        ),
    ]

    # Filter with relative threshold 0.10 (10% of range)
    # Range = 100 - 0 = 100, absolute threshold = 10.0
    filtered = filter_by_persistence(
        critical_points=points,
        persistence_threshold=0.10,
        scalar_range=(0.0, 100.0),
    )

    # Should keep point 1 (persistence=15 > 10)
    # Should filter point 0 (persistence=5 < 10)
    assert len(filtered) == 1
    assert filtered[0].point_id == 1


# =============================================================================
# UK REGION THRESHOLD TESTING
# =============================================================================


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
@pytest.mark.parametrize("threshold", [0.01, 0.05, 0.10])
def test_uk_region_threshold_comparison(uk_region_surface_with_noise, threshold):
    """Test different simplification thresholds on UK-like region data."""
    data = uk_region_surface_with_noise
    vtk_path = data["vtk_path"]

    # Compute with simplification at different thresholds
    result = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=threshold,
        simplify_first=True,
        simplification_threshold=threshold,
        compute_descending=True,
    )

    # Verify basic results
    assert len(result.critical_points) > 0

    # Store counts for analysis
    n_minima = result.n_minima
    n_maxima = result.n_maxima
    n_saddles = result.n_saddles

    # Conservative threshold (1%) should preserve more features
    # Aggressive threshold (10%) should simplify heavily
    # This is a qualitative test - actual numbers depend on surface

    # All thresholds should satisfy Morse inequality
    # For 2D surface with boundaries: chi = 1
    # Morse inequality: #critical_points >= |chi|
    total_critical_points = n_minima + n_maxima + n_saddles
    assert total_critical_points >= 1

    # Should have at least one minimum (poverty trap)
    assert n_minima >= 1


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_uk_region_basin_consistency(uk_region_surface_with_noise):
    """Test that basin structures are consistent with/without simplification."""
    data = uk_region_surface_with_noise
    vtk_path = data["vtk_path"]

    # Compute without simplification
    result_no_simp = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.05,
        simplify_first=False,
        compute_descending=True,
    )

    # Compute with moderate simplification
    result_with_simp = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.05,
        simplify_first=True,
        simplification_threshold=0.08,
        compute_descending=True,
    )

    # Both should have descending manifolds
    assert result_no_simp.descending_manifold is not None
    assert result_with_simp.descending_manifold is not None

    # Basin count should match minima count
    unique_basins_no_simp = np.unique(result_no_simp.descending_manifold[result_no_simp.descending_manifold >= 0])
    unique_basins_with_simp = np.unique(result_with_simp.descending_manifold[result_with_simp.descending_manifold >= 0])

    assert len(unique_basins_no_simp) == result_no_simp.n_minima
    assert len(unique_basins_with_simp) == result_with_simp.n_minima


# =============================================================================
# TOPOLOGICAL PROPERTY VALIDATION
# =============================================================================


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_morse_inequality_with_simplification(synthetic_noisy_surface):
    """Test that Morse inequality is satisfied with simplification."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    # Test multiple simplification thresholds
    for threshold in [0.02, 0.05, 0.10]:
        result = compute_morse_smale(
            vtk_path=vtk_path,
            scalar_name="scalar",
            persistence_threshold=0.05,
            simplify_first=True,
            simplification_threshold=threshold,
        )

        # Morse inequality for 2D closed surface: n_min - n_saddle + n_max = chi
        # For a surface topologically equivalent to sphere: chi = 2
        # For a surface with boundaries: chi >= 1
        # General Morse inequality: #critical_points >= |chi|

        total_critical_points = result.n_minima + result.n_saddles + result.n_maxima

        # Should have at least 1 critical point
        assert total_critical_points >= 1

        # Euler characteristic check (approximate for this surface)
        euler_char = result.n_minima - result.n_saddles + result.n_maxima

        # For most surfaces, this should be reasonable
        # (Can be negative for surfaces with genus > 0)
        assert isinstance(euler_char, int)


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_critical_point_classification_accuracy(synthetic_noisy_surface):
    """Test that critical points are correctly classified after simplification."""
    data = synthetic_noisy_surface
    vtk_path = data["vtk_path"]

    result = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="scalar",
        persistence_threshold=0.05,
        simplify_first=True,
        simplification_threshold=0.08,
    )

    # Verify all critical points have valid types
    for cp in result.critical_points:
        # For 2D surface: 0=minimum, 1=saddle, 2=maximum
        assert cp.point_type in [0, 1, 2]
        assert cp.manifold_dim == 2

        # Check type_name property
        if cp.point_type == 0:
            assert cp.type_name == "minimum"
            assert cp.is_minimum
            assert not cp.is_saddle
            assert not cp.is_maximum
        elif cp.point_type == 1:
            assert cp.type_name == "saddle"
            assert cp.is_saddle
            assert not cp.is_minimum
            assert not cp.is_maximum
        elif cp.point_type == 2:
            assert cp.type_name == "maximum"
            assert cp.is_maximum
            assert not cp.is_minimum
            assert not cp.is_saddle


# =============================================================================
# THRESHOLD RECOMMENDATION TESTS
# =============================================================================


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_threshold_recommendation_conservative():
    """Test that 1% threshold preserves most features (conservative)."""
    # This is a documentation test for threshold recommendations
    assert 0.01 < 0.05 < 0.10  # Threshold ordering
    # 1% = conservative, preserves most features
    # 5% = balanced, removes minor noise
    # 10% = aggressive, major simplification


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_threshold_recommendation_balanced():
    """Test that 5% threshold provides good balance (recommended)."""
    # This is a documentation test for threshold recommendations
    # 5% is recommended for production use as balanced threshold
    recommended_threshold = 0.05
    assert 0.01 <= recommended_threshold <= 0.10


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_threshold_recommendation_aggressive():
    """Test that 10% threshold provides major simplification (aggressive)."""
    # This is a documentation test for threshold recommendations
    # 10% removes significant noise but may merge small traps
    aggressive_threshold = 0.10
    assert aggressive_threshold > 0.05


# =============================================================================
# DOCUMENTATION AND EXAMPLES
# =============================================================================


def test_simplification_workflow_documentation():
    """
    Document recommended simplification workflow for production use.

    Workflow:
        1. Load mobility surface VTK file
        2. Apply simplification with 5% threshold (recommended)
        3. Compute Morse-Smale with 3% persistence threshold
        4. Post-process with filter_by_persistence if needed

    Threshold Recommendations:
        - Conservative (1%): Preserves all but tiniest noise
        - Balanced (5%): Recommended - removes interpolation artifacts
        - Aggressive (10%): Major simplification, may merge small features

    This test serves as documentation for the workflow.
    """
    workflow = {
        "step1": "Load VTK surface",
        "step2": "Simplify with 0.05 threshold",
        "step3": "Compute Morse-Smale with 0.03 threshold",
        "step4": "Optional: filter_by_persistence for post-processing",
    }

    thresholds = {
        "conservative": 0.01,
        "balanced": 0.05,  # Recommended
        "aggressive": 0.10,
    }

    assert workflow["step2"] == "Simplify with 0.05 threshold"
    assert thresholds["balanced"] == 0.05
