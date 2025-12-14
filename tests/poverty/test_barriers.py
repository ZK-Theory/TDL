"""
Tests for separatrix extraction and barrier analysis.

Tests cover:
- Separatrix extraction from Morse-Smale complex
- Barrier strength computation (persistence, height, width)
- Geographic mapping to LSOA boundaries
- Barrier ranking and impact analysis
- Validation of separatrix topology (connects saddle to extremum)
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Polygon

from poverty_tda.analysis.barriers import (
    BarrierProperties,
    analyze_barrier_impact,
    barrier_summary_report,
    compute_barrier_impacts,
    compute_barrier_strength,
    create_barrier_properties,
    extract_separatrices,
    map_barriers_to_geography,
    rank_barriers,
)
from poverty_tda.topology.morse_smale import (
    CriticalPoint,
    MorseSmaleResult,
    Separatrix,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def simple_morse_smale_with_separatrices():
    """
    Create a simple Morse-Smale complex with known separatrix structure.

    Surface: z = x² - y² (saddle surface with known separatrices)
    Critical points:
    - Saddle at (0, 0) with value 0
    - Minimum at (-1, 0) with value -1
    - Maximum at (1, 0) with value 1
    """
    # Create critical points
    minimum = CriticalPoint(
        point_id=0,
        position=(-1.0, 0.0, 0.0),
        value=-1.0,
        point_type=0,  # minimum
        manifold_dim=2,
        persistence=1.0,
    )

    saddle = CriticalPoint(
        point_id=1,
        position=(0.0, 0.0, 0.0),
        value=0.0,
        point_type=1,  # saddle
        manifold_dim=2,
        persistence=1.0,
    )

    maximum = CriticalPoint(
        point_id=2,
        position=(1.0, 0.0, 0.0),
        value=1.0,
        point_type=2,  # maximum
        manifold_dim=2,
        persistence=1.0,
    )

    # Create separatrices
    # Descending: saddle → minimum
    desc_points = np.array(
        [
            [0.0, 0.0, 0.0],  # Start at saddle
            [-0.5, 0.0, 0.0],  # Along x-axis
            [-1.0, 0.0, 0.0],  # End at minimum
        ]
    )
    desc_values = np.array([0.0, -0.25, -1.0])

    desc_sep = Separatrix(
        separatrix_id=0,
        source_id=1,  # saddle
        destination_id=0,  # minimum
        separatrix_type=0,  # descending
        points=desc_points,
        values=desc_values,
    )

    # Ascending: saddle → maximum
    asc_points = np.array(
        [
            [0.0, 0.0, 0.0],  # Start at saddle
            [0.5, 0.0, 0.0],  # Along x-axis
            [1.0, 0.0, 0.0],  # End at maximum
        ]
    )
    asc_values = np.array([0.0, 0.25, 1.0])

    asc_sep = Separatrix(
        separatrix_id=1,
        source_id=1,  # saddle
        destination_id=2,  # maximum
        separatrix_type=1,  # ascending
        points=asc_points,
        values=asc_values,
    )

    # Create MorseSmaleResult
    ms_result = MorseSmaleResult(
        critical_points=[minimum, saddle, maximum],
        separatrices_1d=[desc_sep, asc_sep],
        persistence_threshold=0.0,
        scalar_range=(-1.0, 1.0),
    )

    surface_data = {
        "scalar_field": np.array([[-1.0, 0.0, 1.0]]),
        "x_coords": np.array([-1.0, 0.0, 1.0]),
        "y_coords": np.array([0.0]),
    }

    return ms_result, surface_data


@pytest.fixture
def lsoa_boundaries_for_barriers():
    """Create synthetic LSOA boundaries for barrier mapping tests."""
    lsoas = [
        {
            "lsoa_code": "E01000001",
            "lad_name": "Test District",
            "geometry": Polygon([(-2, -1), (0, -1), (0, 1), (-2, 1)]),
        },
        {
            "lsoa_code": "E01000002",
            "lad_name": "Test District",
            "geometry": Polygon([(0, -1), (2, -1), (2, 1), (0, 1)]),
        },
    ]
    gdf = gpd.GeoDataFrame(lsoas, crs="EPSG:27700")
    return gdf


# =============================================================================
# SEPARATRIX EXTRACTION TESTS
# =============================================================================


def test_extract_separatrices_basic(simple_morse_smale_with_separatrices):
    """Test separatrix extraction and type separation."""
    ms_result, _ = simple_morse_smale_with_separatrices

    descending, ascending = extract_separatrices(ms_result)

    # Should have 1 descending and 1 ascending
    assert len(descending) == 1
    assert len(ascending) == 1

    # Check types
    assert descending[0].separatrix_type == 0
    assert ascending[0].separatrix_type == 1

    # Check IDs
    assert descending[0].separatrix_id == 0
    assert ascending[0].separatrix_id == 1


def test_extract_separatrices_empty():
    """Test extraction from empty Morse-Smale result."""
    ms_empty = MorseSmaleResult()

    descending, ascending = extract_separatrices(ms_empty)

    assert descending == []
    assert ascending == []


def test_separatrix_topology_validation(simple_morse_smale_with_separatrices):
    """Test that separatrices correctly connect saddles to extrema."""
    ms_result, _ = simple_morse_smale_with_separatrices

    descending, ascending = extract_separatrices(ms_result)

    # Descending should connect saddle (1) to minimum (0)
    desc = descending[0]
    assert desc.source_id == 1  # saddle
    assert desc.destination_id == 0  # minimum

    # Get critical points
    saddle = next(cp for cp in ms_result.critical_points if cp.point_id == 1)
    minimum = next(cp for cp in ms_result.critical_points if cp.point_id == 0)

    assert saddle.is_saddle
    assert minimum.is_minimum

    # Ascending should connect saddle (1) to maximum (2)
    asc = ascending[0]
    assert asc.source_id == 1  # saddle
    assert asc.destination_id == 2  # maximum

    maximum = next(cp for cp in ms_result.critical_points if cp.point_id == 2)
    assert maximum.is_maximum


# =============================================================================
# BARRIER STRENGTH COMPUTATION TESTS
# =============================================================================


def test_compute_barrier_strength_basic(simple_morse_smale_with_separatrices):
    """Test barrier strength computation with known values."""
    ms_result, surface_data = simple_morse_smale_with_separatrices

    # Get descending separatrix
    desc_sep = ms_result.separatrices_1d[0]
    saddle = ms_result.critical_points[1]
    minimum = ms_result.critical_points[0]

    strength = compute_barrier_strength(desc_sep, saddle, minimum, surface_data)

    # Check persistence
    assert strength["persistence"] == 1.0

    # Check barrier height (max along path - saddle value)
    # Path goes from 0 → -0.25 → -1.0, max is 0, saddle is 0
    # So barrier height = 0 - 0 = 0
    assert strength["barrier_height"] >= 0.0

    # Check barrier width
    # Path length from (0,0) → (-0.5,0) → (-1,0) = 1.0 km
    # 1m = 0.001km
    assert strength["barrier_width_km"] == pytest.approx(0.001, abs=0.0001)


def test_compute_barrier_strength_without_path():
    """Test strength computation when separatrix has no path data."""
    # Create separatrix without points
    sep = Separatrix(
        separatrix_id=0,
        source_id=0,
        destination_id=1,
        separatrix_type=0,
        points=None,
        values=None,
    )

    saddle = CriticalPoint(
        point_id=0,
        position=(0.0, 0.0, 0.0),
        value=0.5,
        point_type=1,
        manifold_dim=2,
        persistence=0.8,
    )

    minimum = CriticalPoint(
        point_id=1,
        position=(1.0, 1.0, 0.0),
        value=0.1,
        point_type=0,
        manifold_dim=2,
    )

    strength = compute_barrier_strength(sep, saddle, minimum)

    # Should still compute persistence
    assert strength["persistence"] == 0.8

    # Should estimate width from straight-line distance
    # Distance = sqrt((1-0)² + (1-0)²) = sqrt(2) ≈ 1.414 m = 0.001414 km
    assert strength["barrier_width_km"] > 0.0


def test_create_barrier_properties(simple_morse_smale_with_separatrices):
    """Test creation of BarrierProperties from separatrices."""
    ms_result, surface_data = simple_morse_smale_with_separatrices

    descending, _ = extract_separatrices(ms_result)

    barriers = create_barrier_properties(descending, ms_result, surface_data)

    assert len(barriers) == 1

    barrier = barriers[0]
    assert barrier.barrier_id == 0
    assert barrier.barrier_type == "descending"
    assert barrier.saddle.point_id == 1
    assert barrier.terminus.point_id == 0
    assert barrier.persistence == 1.0
    assert barrier.geometry is not None
    assert isinstance(barrier.geometry, LineString)


# =============================================================================
# GEOGRAPHIC MAPPING TESTS
# =============================================================================


def test_map_barriers_to_geography(
    simple_morse_smale_with_separatrices,
    lsoa_boundaries_for_barriers,
):
    """Test mapping barriers to LSOA boundaries."""
    ms_result, surface_data = simple_morse_smale_with_separatrices
    lsoa_gdf = lsoa_boundaries_for_barriers

    descending, _ = extract_separatrices(ms_result)
    barriers = create_barrier_properties(descending, ms_result, surface_data)

    # Map to geography
    barriers = map_barriers_to_geography(barriers, lsoa_gdf, buffer_meters=500.0)

    # Barrier goes from (0,0) to (-1,0), should intersect both LSOAs
    barrier = barriers[0]
    assert len(barrier.lsoa_codes) > 0


def test_map_barriers_handles_missing_geometry():
    """Test that mapping handles barriers without geometry gracefully."""
    # Create barrier without geometry
    sep = Separatrix(
        separatrix_id=0,
        source_id=0,
        destination_id=1,
        separatrix_type=0,
    )
    saddle = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0, point_type=1, manifold_dim=2
    )
    terminus = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=1, point_type=0, manifold_dim=2
    )

    barrier = BarrierProperties(
        separatrix=sep,
        barrier_id=0,
        saddle=saddle,
        terminus=terminus,
        barrier_type="descending",
        geometry=None,  # No geometry
    )

    lsoa_gdf = gpd.GeoDataFrame(
        [
            {
                "lsoa_code": "E01000001",
                "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            }
        ],
        crs="EPSG:27700",
    )

    barriers = map_barriers_to_geography([barrier], lsoa_gdf)

    # Should not crash, lsoa_codes should remain empty
    assert barriers[0].lsoa_codes == []


# =============================================================================
# BARRIER RANKING TESTS
# =============================================================================


def test_rank_barriers_by_persistence():
    """Test barrier ranking by persistence."""
    # Create barriers with different persistence values
    saddle1 = CriticalPoint(
        point_id=0,
        position=(0, 0, 0),
        value=0,
        point_type=1,
        manifold_dim=2,
        persistence=0.9,
    )
    saddle2 = CriticalPoint(
        point_id=1,
        position=(1, 1, 0),
        value=0,
        point_type=1,
        manifold_dim=2,
        persistence=0.5,
    )
    saddle3 = CriticalPoint(
        point_id=2,
        position=(2, 2, 0),
        value=0,
        point_type=1,
        manifold_dim=2,
        persistence=0.7,
    )

    min_cp = CriticalPoint(
        point_id=3, position=(0, 0, 0), value=-1, point_type=0, manifold_dim=2
    )

    barriers = [
        BarrierProperties(
            separatrix=Separatrix(0, 0, 3, 0),
            barrier_id=0,
            saddle=saddle1,
            terminus=min_cp,
            barrier_type="descending",
            persistence=0.9,
        ),
        BarrierProperties(
            separatrix=Separatrix(1, 1, 3, 0),
            barrier_id=1,
            saddle=saddle2,
            terminus=min_cp,
            barrier_type="descending",
            persistence=0.5,
        ),
        BarrierProperties(
            separatrix=Separatrix(2, 2, 3, 0),
            barrier_id=2,
            saddle=saddle3,
            terminus=min_cp,
            barrier_type="descending",
            persistence=0.7,
        ),
    ]

    top_barriers = rank_barriers(barriers, top_n=2, rank_by="persistence")

    assert len(top_barriers) == 2
    assert top_barriers[0].barrier_id == 0  # Highest persistence (0.9)
    assert top_barriers[1].barrier_id == 2  # Second highest (0.7)


def test_rank_barriers_by_height():
    """Test barrier ranking by height."""
    saddle = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0, point_type=1, manifold_dim=2
    )
    min_cp = CriticalPoint(
        point_id=1, position=(0, 0, 0), value=-1, point_type=0, manifold_dim=2
    )

    barriers = [
        BarrierProperties(
            separatrix=Separatrix(0, 0, 1, 0),
            barrier_id=0,
            saddle=saddle,
            terminus=min_cp,
            barrier_type="descending",
            barrier_height=0.3,
        ),
        BarrierProperties(
            separatrix=Separatrix(1, 0, 1, 0),
            barrier_id=1,
            saddle=saddle,
            terminus=min_cp,
            barrier_type="descending",
            barrier_height=0.8,
        ),
    ]

    top_barriers = rank_barriers(barriers, top_n=1, rank_by="height")

    assert len(top_barriers) == 1
    assert top_barriers[0].barrier_id == 1  # Highest height (0.8)


def test_rank_barriers_empty():
    """Test ranking with empty list."""
    top_barriers = rank_barriers([])
    assert top_barriers == []


# =============================================================================
# BARRIER IMPACT ANALYSIS TESTS
# =============================================================================


def test_analyze_barrier_impact_basic():
    """Test barrier impact analysis with population and mobility."""
    saddle = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0, point_type=1, manifold_dim=2
    )
    min_cp = CriticalPoint(
        point_id=1, position=(0, 0, 0), value=-1, point_type=0, manifold_dim=2
    )

    barrier = BarrierProperties(
        separatrix=Separatrix(0, 0, 1, 0),
        barrier_id=0,
        saddle=saddle,
        terminus=min_cp,
        barrier_type="descending",
    )

    basin_left = {
        "basin_id": 0,
        "population": 5000,
        "mean_mobility": 0.3,
    }

    basin_right = {
        "basin_id": 1,
        "population": 3000,
        "mean_mobility": 0.7,
    }

    impact = analyze_barrier_impact(barrier, basin_left, basin_right)

    assert impact.population_separated == 8000  # 5000 + 3000
    assert impact.mobility_differential == pytest.approx(0.4)  # |0.3 - 0.7|
    assert impact.basin_left_pop == 5000
    assert impact.basin_right_pop == 3000
    assert impact.impact_score > 0  # Should have positive impact


def test_analyze_barrier_impact_zero_differential():
    """Test impact analysis when basins have same mobility."""
    saddle = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0, point_type=1, manifold_dim=2
    )
    min_cp = CriticalPoint(
        point_id=1, position=(0, 0, 0), value=-1, point_type=0, manifold_dim=2
    )

    barrier = BarrierProperties(
        separatrix=Separatrix(0, 0, 1, 0),
        barrier_id=0,
        saddle=saddle,
        terminus=min_cp,
        barrier_type="descending",
    )

    basin_left = {
        "basin_id": 0,
        "population": 5000,
        "mean_mobility": 0.5,
    }

    basin_right = {
        "basin_id": 1,
        "population": 3000,
        "mean_mobility": 0.5,
    }

    impact = analyze_barrier_impact(barrier, basin_left, basin_right)

    assert impact.mobility_differential == 0.0
    assert impact.impact_score == 0.0  # No differential = no impact


def test_compute_barrier_impacts():
    """Test computing impacts for multiple barriers."""
    saddle = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0, point_type=1, manifold_dim=2
    )
    min1 = CriticalPoint(
        point_id=1, position=(-1, 0, 0), value=-1, point_type=0, manifold_dim=2
    )
    min2 = CriticalPoint(
        point_id=2, position=(1, 0, 0), value=-0.5, point_type=0, manifold_dim=2
    )

    barriers = [
        BarrierProperties(
            separatrix=Separatrix(0, 0, 1, 0),
            barrier_id=0,
            saddle=saddle,
            terminus=min1,
            barrier_type="descending",
        ),
        BarrierProperties(
            separatrix=Separatrix(1, 0, 2, 0),
            barrier_id=1,
            saddle=saddle,
            terminus=min2,
            barrier_type="descending",
        ),
    ]

    basins = [
        {"basin_id": 1, "population": 5000, "mean_mobility": 0.3},
        {"basin_id": 2, "population": 3000, "mean_mobility": 0.6},
    ]

    impacts = compute_barrier_impacts(barriers, basins)

    # Should create impacts for barriers with basin data
    assert len(impacts) >= 1


# =============================================================================
# REPORTING TESTS
# =============================================================================


def test_barrier_summary_report():
    """Test barrier summary report generation."""
    saddle = CriticalPoint(
        point_id=0,
        position=(0, 0, 0),
        value=0,
        point_type=1,
        manifold_dim=2,
        persistence=0.8,
    )
    min_cp = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=-1, point_type=0, manifold_dim=2
    )

    barriers = [
        BarrierProperties(
            separatrix=Separatrix(0, 0, 1, 0),
            barrier_id=0,
            saddle=saddle,
            terminus=min_cp,
            barrier_type="descending",
            persistence=0.8,
            barrier_height=0.5,
            barrier_width_km=2.3,
            lsoa_codes=["E01000001", "E01000002"],
        ),
    ]

    report = barrier_summary_report(barriers)

    assert isinstance(report, pd.DataFrame)
    assert len(report) == 1

    expected_columns = [
        "barrier_id",
        "barrier_type",
        "persistence",
        "barrier_height",
        "barrier_width_km",
        "n_lsoas",
        "saddle_id",
        "terminus_id",
    ]
    for col in expected_columns:
        assert col in report.columns

    # Check values
    assert report.iloc[0]["barrier_id"] == 0
    assert report.iloc[0]["barrier_type"] == "descending"
    assert report.iloc[0]["persistence"] == 0.8
    assert report.iloc[0]["n_lsoas"] == 2


def test_barrier_summary_report_empty():
    """Test summary report with empty input."""
    report = barrier_summary_report([])
    assert isinstance(report, pd.DataFrame)
    assert len(report) == 0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


def test_barrier_properties_type_checks():
    """Test barrier type property checks."""
    saddle = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0, point_type=1, manifold_dim=2
    )
    min_cp = CriticalPoint(
        point_id=1, position=(0, 0, 0), value=-1, point_type=0, manifold_dim=2
    )
    max_cp = CriticalPoint(
        point_id=2, position=(0, 0, 0), value=1, point_type=2, manifold_dim=2
    )

    desc_barrier = BarrierProperties(
        separatrix=Separatrix(0, 0, 1, 0),
        barrier_id=0,
        saddle=saddle,
        terminus=min_cp,
        barrier_type="descending",
    )

    asc_barrier = BarrierProperties(
        separatrix=Separatrix(1, 0, 2, 1),
        barrier_id=1,
        saddle=saddle,
        terminus=max_cp,
        barrier_type="ascending",
    )

    assert desc_barrier.is_descending
    assert not desc_barrier.is_ascending

    assert asc_barrier.is_ascending
    assert not asc_barrier.is_descending


def test_barrier_strength_score():
    """Test barrier strength score computation."""
    saddle1 = CriticalPoint(
        point_id=0,
        position=(0, 0, 0),
        value=0,
        point_type=1,
        manifold_dim=2,
        persistence=0.8,
    )
    saddle2 = CriticalPoint(
        point_id=1,
        position=(0, 0, 0),
        value=0,
        point_type=1,
        manifold_dim=2,
        persistence=None,
    )

    min_cp = CriticalPoint(
        point_id=2, position=(0, 0, 0), value=-1, point_type=0, manifold_dim=2
    )

    barrier1 = BarrierProperties(
        separatrix=Separatrix(0, 0, 2, 0),
        barrier_id=0,
        saddle=saddle1,
        terminus=min_cp,
        barrier_type="descending",
        persistence=0.8,
    )

    barrier2 = BarrierProperties(
        separatrix=Separatrix(1, 1, 2, 0),
        barrier_id=1,
        saddle=saddle2,
        terminus=min_cp,
        barrier_type="descending",
        persistence=None,
    )

    assert barrier1.strength_score == 0.8
    assert barrier2.strength_score == 0.0  # No persistence
