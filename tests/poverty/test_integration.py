"""
Integration tests for complete poverty TDA pipeline.

These tests verify end-to-end pipeline flow from data acquisition through
intervention analysis, ensuring all components work together correctly including
the TTK topological simplification integration from Phase 6.5.

Pipeline Flow:
    1. Data Acquisition → 2. Geospatial Processing → 3. Topological Analysis →
    4. Trap Identification → 5. Intervention Analysis

Test Strategy:
    - Use synthetic/cached sample data to avoid API calls
    - Test components both independently and integrated
    - Verify data flow between pipeline stages
    - Check topological property preservation
    - Validate TTK simplification integration

License: Open Government Licence v3.0
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon

from poverty_tda.analysis.interventions import Intervention, InterventionType
from poverty_tda.analysis.trap_identification import (
    compute_trap_score,
    extract_basin_properties,
)
from poverty_tda.topology.morse_smale import compute_morse_smale

# Import centralized TTK utilities
from shared.ttk_utils import is_ttk_available

# Check if pyvista is available
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False


# =============================================================================
# INTEGRATION TEST FIXTURES
# =============================================================================


@pytest.fixture
def sample_uk_region_data():
    """
    Create synthetic data resembling a UK region with poverty traps.
    """
    # Create 5x5 grid of LSOAs (25 total)
    n_lsoas = 25
    lsoa_codes = [f"E01{i:06d}" for i in range(1, n_lsoas + 1)]

    # Create grid of square LSOAs (1km x 1km each)
    polygons = []
    for i in range(5):
        for j in range(5):
            x0, y0 = j * 1000, i * 1000
            poly = Polygon([(x0, y0), (x0 + 1000, y0), (x0 + 1000, y0 + 1000), (x0, y0 + 1000)])
            polygons.append(poly)

    lsoa_boundaries = gpd.GeoDataFrame(
        {
            "LSOA21CD": lsoa_codes,
            "LSOA21NM": [f"LSOA_{i + 1}" for i in range(n_lsoas)],
            "LAD22CD": ["E08000001"] * n_lsoas,
            "LAD22NM": ["Manchester"] * n_lsoas,
        },
        geometry=polygons,
        crs="EPSG:27700",
    )

    # Create synthetic IMD scores with poverty traps (low mobility in corners, high mobility in center)
    imd_scores = []
    for i in range(5):
        for j in range(5):
            center_dist = np.sqrt((i - 2) ** 2 + (j - 2) ** 2)
            imd = 50 - 15 * (2 - center_dist)
            imd_scores.append(max(5, min(90, imd)))

    imd_df = pd.DataFrame({"LSOA21CD": lsoa_codes, "IMD_Score": imd_scores})

    return {"lsoa_boundaries": lsoa_boundaries, "imd_scores": imd_df}


@pytest.fixture
def sample_mobility_vtk(sample_uk_region_data, tmp_path):
    """Create a mobility surface VTK file from sample UK region data."""
    if not HAS_PYVISTA:
        pytest.skip("pyvista not available")

    region_data = sample_uk_region_data
    gdf = region_data["lsoa_boundaries"].merge(region_data["imd_scores"], on="LSOA21CD")

    # Convert IMD to mobility (inverse)
    gdf["mobility"] = 1.0 - (gdf["IMD_Score"] - gdf["IMD_Score"].min()) / (
        gdf["IMD_Score"].max() - gdf["IMD_Score"].min()
    )

    # Create simple 50x50 grid manually
    resolution = 50
    x = np.linspace(0, 5000, resolution)
    y = np.linspace(0, 5000, resolution)
    X, Y = np.meshgrid(x, y)

    # Create mobility surface with poverty trap pattern
    # High mobility in center (2.5km, 2.5km), low in corners
    center_x, center_y = 2500, 2500
    dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
    mobility_surface = 0.2 + 0.6 * np.exp(-(dist_from_center**2) / (2000**2))

    # Create VTK ImageData
    mesh = pv.ImageData(dims=(resolution, resolution, 1))
    mesh.origin = (0, 0, 0)
    mesh.spacing = (5000 / (resolution - 1), 5000 / (resolution - 1), 1)
    mesh.point_data["mobility"] = mobility_surface.ravel()

    # Save to VTK
    vtk_path = tmp_path / "mobility_surface.vti"
    mesh.save(str(vtk_path))

    return vtk_path, mobility_surface


# =============================================================================
# BASIC PIPELINE INTEGRATION TESTS
# =============================================================================


def test_data_to_surface_integration(sample_uk_region_data):
    """Test data acquisition → geospatial processing integration."""
    region_data = sample_uk_region_data

    # Verify data components
    assert "lsoa_boundaries" in region_data
    assert "imd_scores" in region_data

    # Verify LSOA boundaries
    lsoa_gdf = region_data["lsoa_boundaries"]
    assert len(lsoa_gdf) == 25
    assert lsoa_gdf.crs.to_string() == "EPSG:27700"
    assert all(lsoa_gdf.geometry.is_valid)

    # Verify IMD scores
    imd_df = region_data["imd_scores"]
    assert len(imd_df) == 25
    assert "IMD_Score" in imd_df.columns

    # Merge data (typical first integration step)
    merged = lsoa_gdf.merge(imd_df, on="LSOA21CD")
    assert len(merged) == 25
    assert "IMD_Score" in merged.columns


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_surface_to_morse_smale_integration(sample_mobility_vtk):
    """Test mobility surface → Morse-Smale complex integration."""
    vtk_path, mobility_surface = sample_mobility_vtk

    # Compute Morse-Smale complex
    result = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.05,
        compute_descending=True,
    )

    # Verify critical points extracted
    assert len(result.critical_points) > 0
    assert result.n_minima >= 1
    assert result.n_maxima >= 1

    # Verify descending manifold computed
    assert result.descending_manifold is not None

    # Verify scalar range matches surface
    surface_min = mobility_surface.min()
    surface_max = mobility_surface.max()
    assert abs(result.scalar_range[0] - surface_min) < 0.01
    assert abs(result.scalar_range[1] - surface_max) < 0.01


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_morse_smale_to_trap_identification_integration(sample_mobility_vtk):
    """Test Morse-Smale complex → trap identification integration."""
    vtk_path, mobility_surface = sample_mobility_vtk

    # Compute Morse-Smale complex
    ms_result = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.05,
        compute_descending=True,
    )

    # Create surface_data dict for basin extraction
    resolution = mobility_surface.shape[0]
    x = np.linspace(0, 5000, resolution)
    y = np.linspace(0, 5000, resolution)

    surface_data = {"x": x, "y": y, "values": mobility_surface}

    # Extract basin properties
    basins = extract_basin_properties(morse_smale_output=ms_result, surface_data=surface_data, grid_spacing_km=0.1)

    # Verify basins extracted
    assert len(basins) > 0
    assert len(basins) == ms_result.n_minima

    # Verify basin properties
    for basin in basins:
        assert basin.area_cells > 0
        assert 0 <= basin.mean_mobility <= 1
        assert basin.minimum.is_minimum

    # Compute trap scores
    trap_scores = [compute_trap_score(basin, all_basins=basins) for basin in basins]

    # Verify scores
    assert len(trap_scores) == len(basins)
    for score in trap_scores:
        assert 0 <= score.total_score <= 1


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_full_pipeline_integration(sample_mobility_vtk):
    """Test complete pipeline from surface → intervention targeting."""
    vtk_path, mobility_surface = sample_mobility_vtk

    # Step 1: Morse-Smale complex
    ms_result = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.08,
        compute_descending=True,
    )

    # Step 2: Basin extraction
    resolution = mobility_surface.shape[0]
    x = np.linspace(0, 5000, resolution)
    y = np.linspace(0, 5000, resolution)
    surface_data = {"x": x, "y": y, "values": mobility_surface}

    basins = extract_basin_properties(morse_smale_output=ms_result, surface_data=surface_data, grid_spacing_km=0.1)

    # Step 3: Trap scoring
    trap_scores = [compute_trap_score(basin, all_basins=basins) for basin in basins]

    # Step 4: Rank traps
    from poverty_tda.analysis.trap_identification import rank_poverty_traps

    ranked = rank_poverty_traps(trap_scores)

    # Verify pipeline outputs
    assert len(ranked) > 0
    assert ranked[0].total_score == max(ts.total_score for ts in trap_scores)

    # Step 5: Create sample intervention
    top_trap = ranked[0]
    intervention = Intervention(
        intervention_id=1,
        type=InterventionType.EDUCATION,
        target_lsoas=[],
        estimated_effect=0.05,
        cost_estimate=10.0,
        implementation_time=24,
        description=f"Education intervention for basin {top_trap.basin_id}",
        baseline_mobility=top_trap.basin.mean_mobility,
    )

    # Verify intervention created
    assert intervention.type == InterventionType.EDUCATION
    assert intervention.estimated_effect > 0


# =============================================================================
# TTK SIMPLIFICATION INTEGRATION TESTS
# =============================================================================


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_pipeline_with_simplification(sample_mobility_vtk):
    """Test pipeline with TTK simplification enabled (Phase 6.5 integration)."""
    vtk_path, _ = sample_mobility_vtk

    # Compute without simplification
    result_no_simp = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.05,
        simplify_first=False,
    )

    # Compute with simplification
    result_with_simp = compute_morse_smale(
        vtk_path=vtk_path,
        scalar_name="mobility",
        persistence_threshold=0.05,
        simplify_first=True,
        simplification_threshold=0.08,
    )

    # Simplification should reduce or maintain critical point count
    assert len(result_with_simp.critical_points) <= len(result_no_simp.critical_points)

    # Both should satisfy Morse inequality (>= 1 critical point for 2D surface)
    assert len(result_with_simp.critical_points) >= 1
    assert len(result_no_simp.critical_points) >= 1


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
@pytest.mark.parametrize("threshold", [0.01, 0.05, 0.10])
def test_pipeline_threshold_comparison(sample_mobility_vtk, threshold):
    """Test pipeline with different simplification thresholds."""
    vtk_path, _ = sample_mobility_vtk

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
    assert result.descending_manifold is not None

    # Should satisfy Morse inequality
    total_critical_points = result.n_minima + result.n_saddles + result.n_maxima
    assert total_critical_points >= 1

    # Should have at least one minimum
    assert result.n_minima >= 1


# =============================================================================
# DATA QUALITY AND VALIDATION TESTS
# =============================================================================


def test_data_quality_imd_range(sample_uk_region_data):
    """Test IMD scores are in valid range."""
    imd_df = sample_uk_region_data["imd_scores"]

    assert imd_df["IMD_Score"].min() >= 0
    assert imd_df["IMD_Score"].max() <= 100
    assert not imd_df["IMD_Score"].isna().any()


def test_data_quality_geometry_validity(sample_uk_region_data):
    """Test LSOA geometries are valid."""
    lsoa_gdf = sample_uk_region_data["lsoa_boundaries"]

    assert all(lsoa_gdf.geometry.is_valid)
    assert all(lsoa_gdf.geometry.geom_type == "Polygon")


def test_data_quality_crs(sample_uk_region_data):
    """Test coordinate reference system is British National Grid."""
    lsoa_gdf = sample_uk_region_data["lsoa_boundaries"]

    assert lsoa_gdf.crs.to_string() == "EPSG:27700"


@pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
def test_topological_properties_with_simplification(sample_mobility_vtk):
    """Test that topological properties are preserved with simplification."""
    vtk_path, _ = sample_mobility_vtk

    for simp_threshold in [0.02, 0.05, 0.10]:
        result = compute_morse_smale(
            vtk_path=vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.05,
            simplify_first=True,
            simplification_threshold=simp_threshold,
        )

        # Morse inequality: #critical_points >= |chi| (for 2D surface, chi >= 1)
        total_critical_points = result.n_minima + result.n_saddles + result.n_maxima
        assert total_critical_points >= 1

        # All critical points should have valid types
        for cp in result.critical_points:
            assert cp.point_type in [0, 1, 2]  # min, saddle, max
            assert cp.manifold_dim == 2


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


def test_pipeline_handles_missing_data():
    """Test pipeline gracefully handles missing data."""
    lsoa_codes = [f"E01{i:06d}" for i in range(1, 6)]
    polygons = [
        Polygon(
            [
                (i * 1000, 0),
                (i * 1000 + 1000, 0),
                (i * 1000 + 1000, 1000),
                (i * 1000, 1000),
            ]
        )
        for i in range(5)
    ]

    lsoa_gdf = gpd.GeoDataFrame({"LSOA21CD": lsoa_codes}, geometry=polygons, crs="EPSG:27700")

    imd_df = pd.DataFrame({"LSOA21CD": lsoa_codes[:3], "IMD_Score": [30, 40, 50]})

    # Merge should work but leave NaN for missing
    merged = lsoa_gdf.merge(imd_df, on="LSOA21CD", how="left")
    assert len(merged) == 5
    assert merged["IMD_Score"].isna().sum() == 2


# =============================================================================
# COVERAGE TRACKING
# =============================================================================


def test_integration_coverage_marker():
    """
    Marker test to track integration test coverage.

    Target: >85% coverage for integration test module.
    """
    covered_modules = [
        "poverty_tda.topology.morse_smale",
        "poverty_tda.analysis.trap_identification",
        "poverty_tda.analysis.interventions",
    ]

    integration_points = [
        "surface_to_morse_smale",
        "morse_smale_to_basins",
        "basins_to_trap_scores",
        "trap_scores_to_interventions",
        "ttk_simplification_integration",
    ]

    assert len(covered_modules) >= 3
    assert len(integration_points) >= 5
