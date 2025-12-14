"""
Tests for poverty trap basin analysis and scoring.

Tests cover:
- Basin property extraction from Morse-Smale descending manifolds
- Trap scoring formula and component normalization
- Population estimation from LSOA data
- Ranking and reporting functions
- Validation against known poverty trap areas
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon

from poverty_tda.analysis.trap_identification import (
    BasinProperties,
    TrapScore,
    compute_trap_score,
    estimate_basin_population,
    extract_basin_properties,
    rank_poverty_traps,
    trap_summary_report,
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
def simple_surface_with_basins():
    """
    Create a simple synthetic surface with two clear basins.

    Surface: Two minima at (1, 1) and (3, 3), saddle at (2, 2), max at (2, 0).
    Uses a 5x5 grid for simplicity.
    """
    # Create 5x5 grid
    resolution = 5
    x = np.linspace(0, 4, resolution)
    y = np.linspace(0, 4, resolution)
    X, Y = np.meshgrid(x, y)

    # Define scalar field with two basins
    # Basin 1 centered at (1, 1), Basin 2 centered at (3, 3)
    scalar = (
        2.0 * ((X - 1) ** 2 + (Y - 1) ** 2)  # Basin 1
        + 2.0 * ((X - 3) ** 2 + (Y - 3) ** 2)  # Basin 2
        - 5.0  # Offset to ensure minima are negative
    )

    # Create critical points
    # Minimum 1: point_id=0 at (1, 1)
    min1 = CriticalPoint(
        point_id=0,
        position=(1.0, 1.0, 0.0),
        value=-3.0,
        point_type=0,  # minimum
        manifold_dim=2,
        persistence=2.0,
    )

    # Minimum 2: point_id=1 at (3, 3)
    min2 = CriticalPoint(
        point_id=1,
        position=(3.0, 3.0, 0.0),
        value=-3.0,
        point_type=0,  # minimum
        manifold_dim=2,
        persistence=2.0,
    )

    # Saddle: point_id=2 at (2, 2)
    saddle = CriticalPoint(
        point_id=2,
        position=(2.0, 2.0, 0.0),
        value=0.0,  # Barrier height = 0 - (-3) = 3
        point_type=1,  # saddle
        manifold_dim=2,
        persistence=1.0,
    )

    # Maximum: point_id=3 at (2, 0)
    maximum = CriticalPoint(
        point_id=3,
        position=(2.0, 0.0, 0.0),
        value=5.0,
        point_type=2,  # maximum
        manifold_dim=2,
        persistence=3.0,
    )

    # Create descending manifold (each cell flows to nearest minimum)
    descending = np.zeros((resolution, resolution), dtype=np.int32)
    for i in range(resolution):
        for j in range(resolution):
            # Simple rule: left/top half → min1, right/bottom half → min2
            if i + j < resolution:
                descending[i, j] = 0  # flows to min1
            else:
                descending[i, j] = 1  # flows to min2

    # Create separatrices: saddle → minima
    sep1 = Separatrix(
        separatrix_id=0,
        source_id=2,  # saddle
        destination_id=0,  # min1
        separatrix_type=0,  # descending
    )
    sep2 = Separatrix(
        separatrix_id=1,
        source_id=2,  # saddle
        destination_id=1,  # min2
        separatrix_type=0,  # descending
    )

    # Create MorseSmaleResult
    ms_result = MorseSmaleResult(
        critical_points=[min1, min2, saddle, maximum],
        separatrices_1d=[sep1, sep2],
        descending_manifold=descending,
        persistence_threshold=0.0,
        scalar_range=(-3.0, 5.0),
    )

    # Create surface data dict
    surface_data = {
        "scalar_field": scalar,
        "x_coords": x,
        "y_coords": y,
    }

    return ms_result, surface_data, {"min1": min1, "min2": min2, "saddle": saddle}


@pytest.fixture
def lsoa_population_data():
    """
    Create synthetic LSOA data with population for testing.

    Creates 4 LSOAs in a 2x2 grid covering (0,0) to (4,4).
    """
    # Create 4 LSOA polygons
    lsoas = [
        # Bottom-left: (0,0) to (2,2)
        {
            "lsoa_code": "E01000001",
            "lad_name": "Test District A",
            "region": "Test Region",
            "population": 1500,
            "geometry": Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
        },
        # Bottom-right: (2,0) to (4,2)
        {
            "lsoa_code": "E01000002",
            "lad_name": "Test District A",
            "region": "Test Region",
            "population": 1200,
            "geometry": Polygon([(2, 0), (4, 0), (4, 2), (2, 2)]),
        },
        # Top-left: (0,2) to (2,4)
        {
            "lsoa_code": "E01000003",
            "lad_name": "Test District B",
            "region": "Test Region",
            "population": 2000,
            "geometry": Polygon([(0, 2), (2, 2), (2, 4), (0, 4)]),
        },
        # Top-right: (2,2) to (4,4)
        {
            "lsoa_code": "E01000004",
            "lad_name": "Test District B",
            "region": "Test Region",
            "population": 1800,
            "geometry": Polygon([(2, 2), (4, 2), (4, 4), (2, 4)]),
        },
    ]

    gdf = gpd.GeoDataFrame(lsoas, crs="EPSG:27700")
    return gdf


# =============================================================================
# BASIN EXTRACTION TESTS
# =============================================================================


def test_extract_basin_properties_basic(simple_surface_with_basins):
    """Test basin property extraction on simple synthetic surface."""
    ms_result, surface_data, crit_points = simple_surface_with_basins

    basins = extract_basin_properties(ms_result, surface_data, grid_spacing_km=1.0)

    # Should have 2 basins (2 minima)
    assert len(basins) == 2

    # Check basin IDs match minima
    basin_ids = {b.basin_id for b in basins}
    assert basin_ids == {0, 1}

    # Check each basin has properties
    for basin in basins:
        assert basin.area_cells > 0
        assert basin.area_km2 is not None
        assert basin.area_km2 > 0
        assert basin.mean_mobility != 0
        assert basin.centroid is not None

        # Each basin should be bounded by the saddle
        assert basin.n_saddles == 1
        assert len(basin.barrier_heights) == 1
        assert basin.barrier_heights[0] > 0  # Saddle higher than minimum


def test_extract_basin_properties_validates_inputs(simple_surface_with_basins):
    """Test that basin extraction validates required inputs."""
    ms_result, surface_data, _ = simple_surface_with_basins

    # Test missing descending manifold
    ms_empty = MorseSmaleResult(descending_manifold=None)
    with pytest.raises(ValueError, match="descending_manifold not available"):
        extract_basin_properties(ms_empty, surface_data)

    # Test missing surface data keys
    incomplete_data = {"scalar_field": surface_data["scalar_field"]}
    with pytest.raises(ValueError, match="missing keys"):
        extract_basin_properties(ms_result, incomplete_data)


def test_basin_properties_barrier_heights(simple_surface_with_basins):
    """Test that barrier heights are correctly computed."""
    ms_result, surface_data, crit_points = simple_surface_with_basins

    basins = extract_basin_properties(ms_result, surface_data)

    # Both basins should have same barrier height (saddle value - min value)
    # min1.value = -3.0, saddle.value = 0.0 → barrier = 3.0
    for basin in basins:
        assert len(basin.barrier_heights) == 1
        assert basin.barrier_heights[0] == pytest.approx(3.0, abs=0.1)
        assert basin.max_barrier_height == pytest.approx(3.0, abs=0.1)


# =============================================================================
# TRAP SCORING TESTS
# =============================================================================


def test_compute_trap_score_basic(simple_surface_with_basins):
    """Test trap score computation with expected ranges."""
    ms_result, surface_data, _ = simple_surface_with_basins

    basins = extract_basin_properties(ms_result, surface_data)
    scores = compute_trap_score(basins)

    # Should have same number of scores as basins
    assert len(scores) == len(basins)

    # Check score components are in [0, 1]
    for score in scores:
        assert 0.0 <= score.total_score <= 1.0
        assert 0.0 <= score.mobility_score <= 1.0
        assert 0.0 <= score.size_score <= 1.0
        assert 0.0 <= score.barrier_score <= 1.0

        # Check weighted sum formula
        expected = (
            0.4 * score.mobility_score
            + 0.3 * score.size_score
            + 0.3 * score.barrier_score
        )
        assert score.total_score == pytest.approx(expected)


def test_compute_trap_score_ranking_logic():
    """Test that scoring produces intuitive rankings."""
    # Create manual basins with varying properties

    # Basin 1: Low mobility, large area, high barrier → HIGH SCORE
    min1 = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.1, point_type=0, manifold_dim=2
    )
    saddle1 = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=0.9, point_type=1, manifold_dim=2
    )
    basin1 = BasinProperties(
        basin_id=0,
        minimum=min1,
        area_cells=1000,
        mean_mobility=0.1,  # Low mobility (bad)
        min_mobility=0.05,
        bounding_saddles=[saddle1],
        barrier_heights=[0.8],  # High barrier (hard to escape)
    )

    # Basin 2: High mobility, small area, low barrier → LOW SCORE
    min2 = CriticalPoint(
        point_id=2, position=(2, 2, 0), value=0.8, point_type=0, manifold_dim=2
    )
    saddle2 = CriticalPoint(
        point_id=3, position=(3, 3, 0), value=0.9, point_type=1, manifold_dim=2
    )
    basin2 = BasinProperties(
        basin_id=2,
        minimum=min2,
        area_cells=100,
        mean_mobility=0.9,  # High mobility (good)
        min_mobility=0.85,
        bounding_saddles=[saddle2],
        barrier_heights=[0.1],  # Low barrier (easy to escape)
    )

    basins = [basin1, basin2]
    scores = compute_trap_score(basins)

    # Basin 1 should have higher trap score (worse trap)
    score1 = next(s for s in scores if s.basin_id == 0)
    score2 = next(s for s in scores if s.basin_id == 2)

    assert score1.total_score > score2.total_score
    # Lower mobility = higher score
    assert score1.mobility_score > score2.mobility_score
    assert score1.size_score > score2.size_score  # Larger area = higher score
    assert score1.barrier_score > score2.barrier_score  # Higher barrier = higher score


def test_compute_trap_score_empty_list():
    """Test that empty basin list returns empty scores."""
    scores = compute_trap_score([])
    assert scores == []


def test_trap_score_severity_categories():
    """Test severity rank categorization."""
    # Create dummy basin
    min_cp = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.5, point_type=0, manifold_dim=2
    )
    basin = BasinProperties(basin_id=0, minimum=min_cp, area_cells=100)

    # Test each severity category
    score_critical = TrapScore(
        basin=basin,
        total_score=0.85,
        mobility_score=0.9,
        size_score=0.8,
        barrier_score=0.85,
    )
    assert score_critical.severity_rank == "Critical"

    score_severe = TrapScore(
        basin=basin,
        total_score=0.65,
        mobility_score=0.7,
        size_score=0.6,
        barrier_score=0.6,
    )
    assert score_severe.severity_rank == "Severe"

    score_moderate = TrapScore(
        basin=basin,
        total_score=0.45,
        mobility_score=0.5,
        size_score=0.4,
        barrier_score=0.4,
    )
    assert score_moderate.severity_rank == "Moderate"

    score_low = TrapScore(
        basin=basin,
        total_score=0.25,
        mobility_score=0.3,
        size_score=0.2,
        barrier_score=0.2,
    )
    assert score_low.severity_rank == "Low"

    score_minimal = TrapScore(
        basin=basin,
        total_score=0.1,
        mobility_score=0.1,
        size_score=0.1,
        barrier_score=0.1,
    )
    assert score_minimal.severity_rank == "Minimal"


# =============================================================================
# POPULATION ESTIMATION TESTS
# =============================================================================


def test_estimate_basin_population_basic(lsoa_population_data):
    """Test population estimation for a simple basin."""
    lsoa_gdf = lsoa_population_data

    # Create basin mask covering bottom-left quadrant
    basin_mask = np.zeros((5, 5), dtype=bool)
    basin_mask[0:2, 0:2] = True  # Cover bottom-left cells

    grid_bounds = {
        "x_min": 0.0,
        "x_max": 4.0,
        "y_min": 0.0,
        "y_max": 4.0,
        "resolution": 5,
    }

    population, lsoa_codes = estimate_basin_population(
        basin_mask, grid_bounds, lsoa_gdf
    )

    # Should primarily overlap with E01000001 (bottom-left LSOA)
    assert population > 0
    assert "E01000001" in lsoa_codes


def test_estimate_basin_population_handles_missing_data():
    """Test that population estimation handles missing data gracefully."""
    # Create LSOA data without population column
    gdf_no_pop = gpd.GeoDataFrame(
        [
            {
                "lsoa_code": "E01000001",
                "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            }
        ],
        crs="EPSG:27700",
    )

    basin_mask = np.ones((3, 3), dtype=bool)
    grid_bounds = {
        "x_min": 0.0,
        "x_max": 2.0,
        "y_min": 0.0,
        "y_max": 2.0,
        "resolution": 3,
    }

    population, lsoa_codes = estimate_basin_population(
        basin_mask, grid_bounds, gdf_no_pop
    )

    # Should return 0 when population column missing
    assert population == 0
    assert lsoa_codes == []


def test_estimate_basin_population_empty_basin():
    """Test population estimation for empty basin."""
    lsoa_gdf = gpd.GeoDataFrame(
        [
            {
                "lsoa_code": "E01000001",
                "population": 1000,
                "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            }
        ],
        crs="EPSG:27700",
    )

    # Empty basin mask
    basin_mask = np.zeros((3, 3), dtype=bool)
    grid_bounds = {
        "x_min": 0.0,
        "x_max": 2.0,
        "y_min": 0.0,
        "y_max": 2.0,
        "resolution": 3,
    }

    population, lsoa_codes = estimate_basin_population(
        basin_mask, grid_bounds, lsoa_gdf
    )

    assert population == 0
    assert lsoa_codes == []


# =============================================================================
# RANKING AND REPORTING TESTS
# =============================================================================


def test_rank_poverty_traps_basic():
    """Test that ranking returns traps sorted by score."""
    # Create dummy scores
    min1 = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.1, point_type=0, manifold_dim=2
    )
    min2 = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=0.5, point_type=0, manifold_dim=2
    )
    min3 = CriticalPoint(
        point_id=2, position=(2, 2, 0), value=0.3, point_type=0, manifold_dim=2
    )

    basin1 = BasinProperties(basin_id=0, minimum=min1, area_cells=100)
    basin2 = BasinProperties(basin_id=1, minimum=min2, area_cells=200)
    basin3 = BasinProperties(basin_id=2, minimum=min3, area_cells=150)

    score1 = TrapScore(
        basin=basin1,
        total_score=0.85,
        mobility_score=0.9,
        size_score=0.8,
        barrier_score=0.85,
    )
    score2 = TrapScore(
        basin=basin2,
        total_score=0.45,
        mobility_score=0.5,
        size_score=0.4,
        barrier_score=0.4,
    )
    score3 = TrapScore(
        basin=basin3,
        total_score=0.65,
        mobility_score=0.7,
        size_score=0.6,
        barrier_score=0.6,
    )

    scores = [score1, score2, score3]

    # Rank top 2
    top_traps = rank_poverty_traps(scores, top_n=2)

    assert len(top_traps) == 2
    assert top_traps[0].basin_id == 0  # Highest score (0.85)
    assert top_traps[1].basin_id == 2  # Second highest (0.65)


def test_rank_poverty_traps_empty():
    """Test ranking with empty list."""
    top_traps = rank_poverty_traps([])
    assert top_traps == []


def test_trap_summary_report_structure():
    """Test that summary report has correct structure."""
    min1 = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.1, point_type=0, manifold_dim=2
    )
    saddle1 = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=0.9, point_type=1, manifold_dim=2
    )

    basin1 = BasinProperties(
        basin_id=0,
        minimum=min1,
        area_cells=100,
        area_km2=10.0,
        mean_mobility=0.3,
        bounding_saddles=[saddle1],
        barrier_heights=[0.8],
    )

    score1 = TrapScore(
        basin=basin1,
        total_score=0.75,
        mobility_score=0.8,
        size_score=0.7,
        barrier_score=0.75,
        population_estimate=5000,
        lad_name="Blackpool",
        region_name="North West",
    )

    ranked = [score1]
    report = trap_summary_report(ranked)

    # Check DataFrame structure
    assert isinstance(report, pd.DataFrame)
    assert len(report) == 1

    expected_columns = [
        "rank",
        "basin_id",
        "total_score",
        "severity",
        "population",
        "area_km2",
        "mean_mobility",
        "max_barrier",
        "lad_name",
        "region",
    ]
    for col in expected_columns:
        assert col in report.columns

    # Check values
    assert report.iloc[0]["rank"] == 1
    assert report.iloc[0]["basin_id"] == 0
    assert report.iloc[0]["total_score"] == 0.75
    assert report.iloc[0]["severity"] == "Severe"
    assert report.iloc[0]["population"] == 5000
    assert report.iloc[0]["lad_name"] == "Blackpool"


def test_trap_summary_report_empty():
    """Test summary report with empty input."""
    report = trap_summary_report([])
    assert isinstance(report, pd.DataFrame)
    assert len(report) == 0


# =============================================================================
# INTEGRATION TESTS WITH KNOWN PATTERNS
# =============================================================================


def test_known_trap_areas_should_rank_high():
    """
    Test that known poverty trap areas rank highly in scoring.

    This test validates against Task 2.6 findings:
    - Blackpool, Knowsley, Middlesbrough should have high trap scores
    - These areas should appear in top rankings

    Note: This is a validation test that will be fully tested with
    real UK data in Phase 7. For now, we validate the logic with
    synthetic data mimicking these patterns.
    """
    # Create synthetic basins mimicking known trap patterns

    # Blackpool-like trap: Low mobility, large basin, high barriers
    min_blackpool = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.05, point_type=0, manifold_dim=2
    )
    saddle_blackpool = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=0.85, point_type=1, manifold_dim=2
    )
    basin_blackpool = BasinProperties(
        basin_id=0,
        minimum=min_blackpool,
        area_cells=2000,
        mean_mobility=0.05,  # Very low mobility
        bounding_saddles=[saddle_blackpool],
        barrier_heights=[0.8],  # High barrier
    )

    # Affluent area (e.g., Westminster-like): High mobility, small basin, low barriers
    min_affluent = CriticalPoint(
        point_id=2, position=(2, 2, 0), value=0.95, point_type=0, manifold_dim=2
    )
    saddle_affluent = CriticalPoint(
        point_id=3, position=(3, 3, 0), value=0.98, point_type=1, manifold_dim=2
    )
    basin_affluent = BasinProperties(
        basin_id=2,
        minimum=min_affluent,
        area_cells=100,
        mean_mobility=0.95,  # High mobility
        bounding_saddles=[saddle_affluent],
        barrier_heights=[0.03],  # Low barrier
    )

    basins = [basin_blackpool, basin_affluent]
    scores = compute_trap_score(basins)

    # Blackpool-like trap should score much higher
    blackpool_score = next(s for s in scores if s.basin_id == 0)
    affluent_score = next(s for s in scores if s.basin_id == 2)

    assert blackpool_score.total_score > affluent_score.total_score

    # Blackpool-like should be severe/critical
    assert blackpool_score.severity_rank in ["Severe", "Critical"]

    # Affluent area should be minimal/low
    assert affluent_score.severity_rank in ["Minimal", "Low"]

    # Test ranking
    top_traps = rank_poverty_traps(scores, top_n=1)
    assert top_traps[0].basin_id == 0  # Blackpool-like should be #1


def test_edge_case_single_basin():
    """Test scoring with single basin (edge case)."""
    min1 = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.5, point_type=0, manifold_dim=2
    )
    basin1 = BasinProperties(
        basin_id=0,
        minimum=min1,
        area_cells=100,
        mean_mobility=0.5,
        barrier_heights=[],
    )

    scores = compute_trap_score([basin1])

    # Should normalize to 0.5 for all components (single value)
    assert len(scores) == 1
    assert 0.0 <= scores[0].total_score <= 1.0


def test_edge_case_no_saddles():
    """Test basin with no bounding saddles."""
    min1 = CriticalPoint(
        point_id=0, position=(0, 0, 0), value=0.3, point_type=0, manifold_dim=2
    )
    basin1 = BasinProperties(
        basin_id=0,
        minimum=min1,
        area_cells=100,
        mean_mobility=0.3,
        bounding_saddles=[],  # No saddles
        barrier_heights=[],  # No barriers
    )

    min2 = CriticalPoint(
        point_id=1, position=(1, 1, 0), value=0.7, point_type=0, manifold_dim=2
    )
    saddle2 = CriticalPoint(
        point_id=2, position=(2, 2, 0), value=0.9, point_type=1, manifold_dim=2
    )
    basin2 = BasinProperties(
        basin_id=1,
        minimum=min2,
        area_cells=200,
        mean_mobility=0.7,
        bounding_saddles=[saddle2],
        barrier_heights=[0.2],
    )

    basins = [basin1, basin2]
    scores = compute_trap_score(basins)

    # Should handle gracefully - basin with no barriers gets barrier_score=0
    score1 = next(s for s in scores if s.basin_id == 0)
    assert score1.barrier_score == 0.0
    assert 0.0 <= score1.total_score <= 1.0
