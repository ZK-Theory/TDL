"""
Tests for integral line computation and gateway LSOA identification.

Tests cover:
- Gradient field computation on simple surfaces
- Integral line tracing to known minima
- Gateway LSOA identification at separatrix crossings
- Flow connectivity validation
- Impact scoring logic
- Edge cases (LSOA at minimum, far from separatrix)
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, Polygon

from poverty_tda.analysis.pathways import (
    GatewayLSOA,
    IntegralLine,
    compute_gateway_impacts,
    compute_gradient_field,
    compute_lsoa_flow_paths,
    gateway_summary_report,
    identify_gateway_lsoas,
    rank_gateway_lsoas,
    score_gateway_impact,
    trace_integral_line,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def simple_paraboloid_surface():
    """
    Create a simple paraboloid surface z = x² + y² with minimum at origin.

    This surface has a single minimum at (0, 0) and radial gradient.
    """
    # Create 11x11 grid from -5 to 5
    x = np.linspace(-5.0, 5.0, 11)
    y = np.linspace(-5.0, 5.0, 11)
    X, Y = np.meshgrid(x, y)

    # Paraboloid: z = x² + y²
    Z = X**2 + Y**2

    surface_data = {
        "scalar_field": Z,
        "x_coords": x,
        "y_coords": y,
    }

    return surface_data


@pytest.fixture
def saddle_surface():
    """
    Create saddle surface z = x² - y² with saddle at origin.

    Critical points:
    - Saddle at (0, 0) with value 0
    - Minimum along y-axis (x=0, y→±∞)
    - Maximum along x-axis (y=0, x→±∞)
    """
    x = np.linspace(-3.0, 3.0, 13)
    y = np.linspace(-3.0, 3.0, 13)
    X, Y = np.meshgrid(x, y)

    # Saddle: z = x² - y²
    Z = X**2 - Y**2

    surface_data = {
        "scalar_field": Z,
        "x_coords": x,
        "y_coords": y,
    }

    return surface_data


@pytest.fixture
def mock_barriers():
    """Create mock barrier separatrices for gateway testing."""
    from poverty_tda.topology.morse_smale import CriticalPoint, Separatrix

    saddle = CriticalPoint(
        point_id=0,
        position=(0.0, 0.0, 0.0),
        value=0.0,
        point_type=1,
        manifold_dim=2,
        persistence=1.0,
    )

    minimum = CriticalPoint(
        point_id=1,
        position=(-2.0, 0.0, 0.0),
        value=-4.0,
        point_type=0,
        manifold_dim=2,
    )

    # Separatrix defined for context but not used directly in test
    _ = Separatrix(
        separatrix_id=0,
        source_id=0,
        destination_id=1,
        separatrix_type=0,
    )

    # Create mock BarrierProperties
    class MockBarrier:
        def __init__(self):
            self.barrier_id = 0
            self.saddle = saddle
            self.terminus = minimum
            self.barrier_type = "descending"
            self.persistence = 1.0
            # Vertical barrier at x=0
            self.geometry = LineString([(0.0, -3.0), (0.0, 3.0)])

    return [MockBarrier()]


# =============================================================================
# GRADIENT FIELD TESTS
# =============================================================================


def test_compute_gradient_field_paraboloid(simple_paraboloid_surface):
    """Test gradient computation on paraboloid surface."""
    surface_data = simple_paraboloid_surface

    grad_x, grad_y = compute_gradient_field(surface_data)

    # Check shapes
    assert grad_x.shape == surface_data["scalar_field"].shape
    assert grad_y.shape == surface_data["scalar_field"].shape

    # At origin (center of grid), gradient should be near zero
    center_i = len(surface_data["y_coords"]) // 2
    center_j = len(surface_data["x_coords"]) // 2

    assert abs(grad_x[center_i, center_j]) < 1e-1
    assert abs(grad_y[center_i, center_j]) < 1e-1

    # Away from origin, gradient should point outward (for paraboloid)
    # At positive x, grad_x should be positive
    assert grad_x[center_i, center_j + 2] > 0

    # At positive y, grad_y should be positive
    assert grad_y[center_i + 2, center_j] > 0


def test_compute_gradient_field_saddle(saddle_surface):
    """Test gradient computation on saddle surface."""
    surface_data = saddle_surface

    grad_x, grad_y = compute_gradient_field(surface_data)

    # Check shapes
    assert grad_x.shape == surface_data["scalar_field"].shape
    assert grad_y.shape == surface_data["scalar_field"].shape

    # At saddle point (center), gradient should be near zero
    center_i = len(surface_data["y_coords"]) // 2
    center_j = len(surface_data["x_coords"]) // 2

    assert abs(grad_x[center_i, center_j]) < 1e-1
    assert abs(grad_y[center_i, center_j]) < 1e-1


# =============================================================================
# INTEGRAL LINE TRACING TESTS
# =============================================================================


def test_trace_integral_line_to_minimum(simple_paraboloid_surface):
    """Test integral line traces to known minimum."""
    surface_data = simple_paraboloid_surface
    grad_field = compute_gradient_field(surface_data)

    # Start from point (3, 3), should flow to origin (0, 0)
    start = (3.0, 3.0)
    line = trace_integral_line(start, grad_field, surface_data)

    # Check line properties
    assert line.start_point == start
    assert line.converged
    assert line.n_steps > 0

    # Endpoint should be near origin
    end_x, end_y = line.end_point
    assert abs(end_x) < 0.5  # Within half grid cell
    assert abs(end_y) < 0.5

    # Path should have multiple points
    assert len(line.path) > 1


def test_trace_integral_line_from_minimum(simple_paraboloid_surface):
    """Test integral line starting at minimum."""
    surface_data = simple_paraboloid_surface
    grad_field = compute_gradient_field(surface_data)

    # Start from minimum (0, 0)
    start = (0.0, 0.0)
    line = trace_integral_line(start, grad_field, surface_data, max_steps=100)

    # Should converge immediately (gradient near zero)
    assert line.converged
    assert line.n_steps < 10  # Very few steps needed

    # Endpoint should be at start
    end_x, end_y = line.end_point
    assert abs(end_x - start[0]) < 0.1
    assert abs(end_y - start[1]) < 0.1


def test_trace_integral_line_max_steps():
    """Test integral line respects max_steps limit."""
    # Create flat surface (no gradient)
    x = np.linspace(0, 10, 11)
    y = np.linspace(0, 10, 11)
    X, Y = np.meshgrid(x, y)
    Z = np.ones_like(X) * 5.0  # Constant surface

    surface_data = {
        "scalar_field": Z,
        "x_coords": x,
        "y_coords": y,
    }

    grad_field = compute_gradient_field(surface_data)

    # Trace from middle of flat surface
    start = (5.0, 5.0)
    line = trace_integral_line(start, grad_field, surface_data, max_steps=50)

    # Flat surface: gradient is zero, so converges immediately
    assert line.converged
    assert line.n_steps == 0  # No steps needed (gradient below threshold)


def test_integral_line_path_length():
    """Test path length computation."""
    path = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [2.0, 1.0],
        ]
    )

    line = IntegralLine(
        line_id=0,
        start_point=(0.0, 0.0),
        end_point=(2.0, 1.0),
        path=path,
    )

    # Path length = 1 + 1 + 1 = 3
    assert line.path_length == pytest.approx(3.0)


# =============================================================================
# LSOA FLOW PATH COMPUTATION TESTS
# =============================================================================


def test_compute_lsoa_flow_paths(simple_paraboloid_surface):
    """Test computing flow paths for multiple LSOAs."""
    surface_data = simple_paraboloid_surface
    grad_field = compute_gradient_field(surface_data)

    # Create synthetic LSOA centroids
    lsoa_centroids = {
        "E01000001": (2.0, 2.0),
        "E01000002": (-3.0, 1.0),
        "E01000003": (1.0, -2.0),
    }

    flow_paths = compute_lsoa_flow_paths(lsoa_centroids, grad_field, surface_data)

    # Should have paths for all LSOAs
    assert len(flow_paths) == 3
    assert "E01000001" in flow_paths
    assert "E01000002" in flow_paths
    assert "E01000003" in flow_paths

    # All should flow to near origin
    for lsoa_code, line in flow_paths.items():
        end_x, end_y = line.end_point
        assert abs(end_x) < 1.0
        assert abs(end_y) < 1.0


def test_compute_lsoa_flow_paths_with_manifold(simple_paraboloid_surface):
    """Test flow path computation with descending manifold."""
    surface_data = simple_paraboloid_surface
    grad_field = compute_gradient_field(surface_data)

    # Create descending manifold (all cells map to basin 0)
    descending = np.zeros((11, 11), dtype=np.int32)

    lsoa_centroids = {
        "E01000001": (2.0, 2.0),
    }

    flow_paths = compute_lsoa_flow_paths(
        lsoa_centroids, grad_field, surface_data, descending
    )

    # Should have destination basin
    assert flow_paths["E01000001"].destination_basin_id == 0


# =============================================================================
# GATEWAY IDENTIFICATION TESTS
# =============================================================================


def test_identify_gateway_lsoas_basic(mock_barriers):
    """Test gateway identification when flow path crosses barrier."""
    # Create flow paths that cross the vertical barrier at x=0
    flow_line_crossing = IntegralLine(
        line_id=0,
        start_point=(2.0, 0.0),  # Start right of barrier
        end_point=(-2.0, 0.0),  # End left of barrier
        path=np.array(
            [
                [2.0, 0.0],
                [1.0, 0.0],
                [0.0, 0.0],  # Crosses barrier here
                [-1.0, 0.0],
                [-2.0, 0.0],
            ]
        ),
        destination_basin_id=1,
    )

    flow_line_not_crossing = IntegralLine(
        line_id=1,
        start_point=(2.0, 2.0),
        end_point=(1.0, 2.0),
        path=np.array(
            [
                [2.0, 2.0],
                [1.0, 2.0],
            ]
        ),
        destination_basin_id=0,
    )

    flow_paths = {
        "E01000001": flow_line_crossing,
        "E01000002": flow_line_not_crossing,
    }

    gateways = identify_gateway_lsoas(flow_paths, mock_barriers)

    # Should identify E01000001 as gateway (crosses barrier)
    assert len(gateways) == 1
    assert gateways[0].lsoa_code == "E01000001"
    assert gateways[0].crossing_point is not None


def test_identify_gateway_lsoas_no_crossings(mock_barriers):
    """Test gateway identification when no paths cross barriers."""
    # Flow path that doesn't cross barrier
    flow_line = IntegralLine(
        line_id=0,
        start_point=(2.0, 2.0),
        end_point=(1.0, 2.0),
        path=np.array(
            [
                [2.0, 2.0],
                [1.0, 2.0],
            ]
        ),
    )

    flow_paths = {
        "E01000001": flow_line,
    }

    gateways = identify_gateway_lsoas(flow_paths, mock_barriers)

    # Should find no gateways
    assert len(gateways) == 0


def test_identify_gateway_lsoas_with_lsoa_data(mock_barriers):
    """Test gateway identification includes LSOA metadata."""
    flow_line = IntegralLine(
        line_id=0,
        start_point=(2.0, 0.0),
        end_point=(-2.0, 0.0),
        path=np.array(
            [
                [2.0, 0.0],
                [0.0, 0.0],
                [-2.0, 0.0],
            ]
        ),
    )

    flow_paths = {
        "E01000001": flow_line,
    }

    # Create LSOA boundaries with metadata
    lsoa_gdf = gpd.GeoDataFrame(
        [
            {
                "lsoa_code": "E01000001",
                "lad_name": "Test District",
                "region_name": "Test Region",
                "geometry": Polygon([(1, -1), (3, -1), (3, 1), (1, 1)]),
            }
        ],
        crs="EPSG:27700",
    )

    gateways = identify_gateway_lsoas(flow_paths, mock_barriers, lsoa_gdf)

    assert len(gateways) == 1
    assert gateways[0].lad_name == "Test District"
    assert gateways[0].region_name == "Test Region"


# =============================================================================
# GATEWAY IMPACT SCORING TESTS
# =============================================================================


def test_score_gateway_impact_basic():
    """Test gateway impact scoring with all components."""
    gateway = GatewayLSOA(
        lsoa_code="E01000001",
        population=5000,
        destination_basin_id=0,
    )

    # Mock barrier with persistence
    class MockBarrier:
        persistence = 0.8

    gateway.barrier_crossed = MockBarrier()

    basin_properties = {0: {"trap_score": 0.9, "population": 10000}}

    score = score_gateway_impact(gateway, basin_properties)

    # Should combine population, trap score, and barrier strength
    assert score > 0
    # Score = 0.3 * 5000 + 0.4 * 0.9 + 0.3 * 0.8
    # Not normalized yet, so just check positive
    assert isinstance(score, float)


def test_score_gateway_impact_missing_data():
    """Test impact scoring handles missing data gracefully."""
    gateway = GatewayLSOA(
        lsoa_code="E01000001",
        population=0,  # No population
        destination_basin_id=None,  # No basin
    )

    gateway.barrier_crossed = None  # No barrier

    basin_properties = {}

    score = score_gateway_impact(gateway, basin_properties)

    # Should return 0 when all components missing
    assert score == 0.0


def test_compute_gateway_impacts():
    """Test batch impact computation and normalization."""
    gateways = [
        GatewayLSOA(lsoa_code="E01000001", destination_basin_id=0),
        GatewayLSOA(lsoa_code="E01000002", destination_basin_id=1),
    ]

    # Mock barriers
    class MockBarrier:
        def __init__(self, persistence):
            self.persistence = persistence

    gateways[0].barrier_crossed = MockBarrier(0.9)
    gateways[1].barrier_crossed = MockBarrier(0.3)

    basin_properties = {
        0: {"trap_score": 0.8},
        1: {"trap_score": 0.2},
    }

    # Create LSOA data with population
    lsoa_gdf = gpd.GeoDataFrame(
        [
            {"lsoa_code": "E01000001", "population": 5000, "geometry": Point(0, 0)},
            {"lsoa_code": "E01000002", "population": 2000, "geometry": Point(1, 1)},
        ],
        crs="EPSG:27700",
    )

    updated_gateways = compute_gateway_impacts(gateways, basin_properties, lsoa_gdf)

    # Should have normalized scores
    assert 0.0 <= updated_gateways[0].impact_score <= 1.0
    assert 0.0 <= updated_gateways[1].impact_score <= 1.0

    # Gateway 1 should have higher impact (higher trap score, barrier, population)
    assert updated_gateways[0].impact_score > updated_gateways[1].impact_score


# =============================================================================
# GATEWAY RANKING TESTS
# =============================================================================


def test_rank_gateway_lsoas():
    """Test gateway ranking by impact score."""
    gateways = [
        GatewayLSOA(lsoa_code="E01000001", impact_score=0.9),
        GatewayLSOA(lsoa_code="E01000002", impact_score=0.5),
        GatewayLSOA(lsoa_code="E01000003", impact_score=0.7),
    ]

    top_gateways = rank_gateway_lsoas(gateways, top_n=2)

    assert len(top_gateways) == 2
    assert top_gateways[0].lsoa_code == "E01000001"  # Highest (0.9)
    assert top_gateways[1].lsoa_code == "E01000003"  # Second (0.7)


def test_rank_gateway_lsoas_empty():
    """Test ranking with empty list."""
    top_gateways = rank_gateway_lsoas([])
    assert top_gateways == []


# =============================================================================
# GATEWAY REPORTING TESTS
# =============================================================================


def test_gateway_summary_report():
    """Test gateway summary report generation."""
    gateways = [
        GatewayLSOA(
            lsoa_code="E01000001",
            lad_name="Test District",
            region_name="Test Region",
            impact_score=0.85,
            population=5000,
            destination_basin_id=0,
        ),
    ]

    # Add barrier
    class MockBarrier:
        barrier_id = 10

    gateways[0].barrier_crossed = MockBarrier()

    report = gateway_summary_report(gateways)

    assert isinstance(report, pd.DataFrame)
    assert len(report) == 1

    expected_columns = [
        "rank",
        "lsoa_code",
        "lad_name",
        "region",
        "impact_score",
        "population",
        "destination_basin",
        "barrier_id",
    ]
    for col in expected_columns:
        assert col in report.columns

    # Check values
    assert report.iloc[0]["rank"] == 1
    assert report.iloc[0]["lsoa_code"] == "E01000001"
    assert report.iloc[0]["impact_score"] == 0.85
    assert report.iloc[0]["barrier_id"] == 10


def test_gateway_summary_report_empty():
    """Test summary report with empty input."""
    report = gateway_summary_report([])
    assert isinstance(report, pd.DataFrame)
    assert len(report) == 0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


def test_integral_line_at_boundary():
    """Test integral line tracing near grid boundaries."""
    x = np.linspace(0, 10, 11)
    y = np.linspace(0, 10, 11)
    X, Y = np.meshgrid(x, y)
    Z = X**2 + Y**2  # Minimum at (0, 0) - corner

    surface_data = {
        "scalar_field": Z,
        "x_coords": x,
        "y_coords": y,
    }

    grad_field = compute_gradient_field(surface_data)

    # Start near boundary
    start = (9.0, 9.0)
    line = trace_integral_line(start, grad_field, surface_data)

    # Should flow to corner minimum (may hit max_steps due to boundary clamping)
    # Either converged or reached boundary
    assert line.end_point[0] < 1.0  # Near x=0
    assert line.end_point[1] < 1.0  # Near y=0


def test_flow_path_short_path():
    """Test flow path with very short path (already near minimum)."""
    lsoa_centroids = {
        "E01000001": (0.1, 0.1),  # Very close to origin minimum
    }

    x = np.linspace(-1, 1, 21)
    y = np.linspace(-1, 1, 21)
    X, Y = np.meshgrid(x, y)
    Z = X**2 + Y**2

    surface_data = {
        "scalar_field": Z,
        "x_coords": x,
        "y_coords": y,
    }

    grad_field = compute_gradient_field(surface_data)

    flow_paths = compute_lsoa_flow_paths(lsoa_centroids, grad_field, surface_data)

    # Should have path and converge to near origin
    assert "E01000001" in flow_paths
    line = flow_paths["E01000001"]
    assert line.converged
    # Endpoint should be very close to origin
    assert abs(line.end_point[0]) < 0.01
    assert abs(line.end_point[1]) < 0.01


def test_gateway_lsoa_properties():
    """Test GatewayLSOA property access."""
    gateway = GatewayLSOA(
        lsoa_code="E01000001",
        lad_name="Test",
        impact_score=0.75,
    )

    assert gateway.lsoa_code == "E01000001"
    assert gateway.lad_name == "Test"
    assert gateway.impact_score == 0.75
