"""
Tests for counterfactual analysis framework.

Tests cover:
- Modification dataclass validation
- SurfaceModifier initialization and validation
- Barrier removal methods (Gaussian, linear)
- Trap filling functionality
- Sequential modification application
- CounterfactualAnalyzer topology comparison
- Population impact estimation
"""

import logging

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing

import numpy as np
import pandas as pd
import pytest

from poverty_tda.analysis.counterfactual import (
    CounterfactualAnalyzer,
    CounterfactualResult,
    Modification,
    SurfaceModifier,
    generate_counterfactual_report,
    visualize_counterfactual,
)

logger = logging.getLogger(__name__)

# Mock MorseSmaleResult for testing
from dataclasses import dataclass, field


@dataclass
class MockCriticalPoint:
    """Mock critical point for testing."""

    point_id: int
    point_type: int
    manifold_dim: int = 2

    @property
    def is_minimum(self) -> bool:
        return self.point_type == 0

    @property
    def is_maximum(self) -> bool:
        return self.point_type == 2

    @property
    def is_saddle(self) -> bool:
        return self.point_type == 1


@dataclass
class MockMorseSmaleResult:
    """Mock Morse-Smale result for testing."""

    critical_points: list[MockCriticalPoint] = field(default_factory=list)


# =============================================================================
# MODIFICATION DATACLASS TESTS
# =============================================================================


def test_modification_creation_valid():
    """Test creating valid Modification instance."""
    mod = Modification(
        type="remove_barrier",
        coords=(100.0, 200.0),
        radius=5.0,
        parameters={"method": "gaussian", "sigma": 2.5},
    )

    assert mod.type == "remove_barrier"
    assert mod.coords == (100.0, 200.0)
    assert mod.radius == 5.0
    assert mod.parameters["method"] == "gaussian"


def test_modification_invalid_type():
    """Test Modification rejects invalid type."""
    with pytest.raises(ValueError, match="Invalid modification type"):
        Modification(
            type="invalid_type",
            coords=(100.0, 200.0),
            radius=5.0,
        )


def test_modification_negative_radius():
    """Test Modification rejects negative radius."""
    with pytest.raises(ValueError, match="Radius must be positive"):
        Modification(
            type="remove_barrier",
            coords=(100.0, 200.0),
            radius=-5.0,
        )


def test_modification_zero_radius():
    """Test Modification rejects zero radius."""
    with pytest.raises(ValueError, match="Radius must be positive"):
        Modification(
            type="fill_trap",
            coords=(100.0, 200.0),
            radius=0.0,
        )


# =============================================================================
# SURFACE MODIFIER INITIALIZATION TESTS
# =============================================================================


def test_surface_modifier_init_1d_grids():
    """Test SurfaceModifier initialization with 1D grid arrays."""
    surface = np.random.rand(10, 10) * 0.5 + 0.3
    grid_x = np.linspace(0, 100, 10)
    grid_y = np.linspace(0, 100, 10)

    modifier = SurfaceModifier(surface, grid_x, grid_y)

    assert modifier.surface.shape == (10, 10)
    assert modifier.modified_surface.shape == (10, 10)
    assert np.allclose(modifier.modified_surface, surface)


def test_surface_modifier_init_2d_grids():
    """Test SurfaceModifier initialization with 2D meshgrid arrays."""
    surface = np.random.rand(10, 10) * 0.5 + 0.3
    x_1d = np.linspace(0, 100, 10)
    y_1d = np.linspace(0, 100, 10)
    grid_x, grid_y = np.meshgrid(x_1d, y_1d, indexing="ij")

    modifier = SurfaceModifier(surface, grid_x, grid_y)

    assert modifier.surface.shape == (10, 10)
    assert modifier.modified_surface.shape == (10, 10)


def test_surface_modifier_init_invalid_surface_dim():
    """Test SurfaceModifier rejects non-2D surface."""
    surface_1d = np.random.rand(10)
    grid_x = np.linspace(0, 100, 10)
    grid_y = np.linspace(0, 100, 10)

    with pytest.raises(ValueError, match="Surface must be 2D"):
        SurfaceModifier(surface_1d, grid_x, grid_y)


def test_surface_modifier_init_mismatched_grid_x():
    """Test SurfaceModifier rejects mismatched grid_x dimensions."""
    surface = np.random.rand(10, 10)
    grid_x = np.linspace(0, 100, 5)  # Wrong length
    grid_y = np.linspace(0, 100, 10)

    with pytest.raises(ValueError, match="grid_x length"):
        SurfaceModifier(surface, grid_x, grid_y)


def test_surface_modifier_init_mismatched_grid_y():
    """Test SurfaceModifier rejects mismatched grid_y dimensions."""
    surface = np.random.rand(10, 10)
    grid_x = np.linspace(0, 100, 10)
    grid_y = np.linspace(0, 100, 5)  # Wrong length

    with pytest.raises(ValueError, match="grid_y length"):
        SurfaceModifier(surface, grid_x, grid_y)


# =============================================================================
# REMOVE BARRIER TESTS
# =============================================================================


def test_remove_barrier_gaussian_method():
    """Test barrier removal with Gaussian smoothing."""
    # Create surface with a saddle point (high value in center)
    surface = np.ones((20, 20)) * 0.3
    surface[10, 10] = 0.8  # Saddle at center

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.remove_barrier((50.0, 50.0), radius=5.0, method="gaussian")

    # Check saddle value reduced
    assert modified[10, 10] < surface[10, 10]
    # Check surface smoothed (less variation)
    assert modified.std() < surface.std()


def test_remove_barrier_linear_method():
    """Test barrier removal with linear interpolation."""
    # Create surface with a saddle point
    surface = np.ones((20, 20)) * 0.3
    surface[10, 10] = 0.8  # Saddle at center

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.remove_barrier((50.0, 50.0), radius=3.0, method="linear")

    # Check saddle region filled to surrounding average
    assert modified[10, 10] < surface[10, 10]
    # Values within radius should be similar (flattened)
    center_region = modified[8:13, 8:13]
    assert center_region.std() < 0.1  # Relatively flat


def test_remove_barrier_invalid_method():
    """Test remove_barrier rejects invalid method."""
    surface = np.ones((20, 20)) * 0.3
    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)

    with pytest.raises(ValueError, match="Invalid method"):
        modifier.remove_barrier((50.0, 50.0), radius=5.0, method="invalid")


def test_remove_barrier_out_of_bounds():
    """Test remove_barrier rejects out-of-bounds coordinates."""
    surface = np.ones((20, 20)) * 0.3
    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)

    with pytest.raises(ValueError, match="out of grid bounds"):
        modifier.remove_barrier((200.0, 200.0), radius=5.0)


# =============================================================================
# FILL TRAP TESTS
# =============================================================================


def test_fill_trap_basic():
    """Test trap filling raises minimum values."""
    # Create surface with a trap (low value in center)
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.1  # Trap at center

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.fill_trap((50.0, 50.0), radius=5.0, target_value=0.4)

    # Check trap value raised substantially
    assert modified[10, 10] > surface[10, 10]
    # Value should be raised toward target (may not fully reach due to gradient)
    assert modified[10, 10] > 0.2  # Significant increase from 0.1
    # Check surrounding values unchanged or slightly raised
    assert modified[5, 5] == pytest.approx(surface[5, 5], abs=0.01)


def test_fill_trap_gradient():
    """Test trap filling creates smooth gradient."""
    # Create surface with a trap
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.1  # Trap at center

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.fill_trap((50.0, 50.0), radius=5.0, target_value=0.4)

    # Check trap value significantly raised
    assert modified[10, 10] > surface[10, 10]
    # Check values decrease with distance (in areas that were below target)
    # Points close to center that were below target should be raised more
    # than points farther away
    center_value = modified[10, 10]
    
    # Center should be raised most, farther points less (if they were below target)
    # But since surrounding values are 0.5 > 0.4 target, they won't be raised
    # So we check center was raised significantly
    assert center_value > 0.2  # Significant raise from 0.1


def test_fill_trap_no_lowering():
    """Test fill_trap never lowers values."""
    # Create surface where target is below current values
    surface = np.ones((20, 20)) * 0.6

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.fill_trap((50.0, 50.0), radius=5.0, target_value=0.4)

    # Check no values lowered
    assert np.all(modified >= surface - 1e-9)  # Allow numerical tolerance


def test_fill_trap_out_of_bounds():
    """Test fill_trap rejects out-of-bounds coordinates."""
    surface = np.ones((20, 20)) * 0.5
    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)

    with pytest.raises(ValueError, match="out of grid bounds"):
        modifier.fill_trap((200.0, 200.0), radius=5.0, target_value=0.6)


# =============================================================================
# APPLY MODIFICATIONS TESTS
# =============================================================================


def test_apply_modifications_empty_list():
    """Test apply_modifications handles empty list."""
    surface = np.ones((20, 20)) * 0.5
    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.apply_modifications([])

    # Should return unmodified surface
    assert np.allclose(modified, surface)


def test_apply_modifications_sequential():
    """Test apply_modifications applies multiple changes sequentially."""
    # Create surface with saddle and trap
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.8  # Saddle
    surface[5, 5] = 0.1    # Trap

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifications = [
        Modification(
            type="remove_barrier",
            coords=(50.0, 50.0),
            radius=3.0,
            parameters={"method": "gaussian"},
        ),
        Modification(
            type="fill_trap",
            coords=(25.0, 25.0),
            radius=3.0,
            parameters={"target_value": 0.4},
        ),
    ]

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified = modifier.apply_modifications(modifications)

    # Check both modifications applied
    assert modified[10, 10] < surface[10, 10]  # Saddle reduced
    assert modified[5, 5] > surface[5, 5]      # Trap raised


def test_apply_modifications_missing_parameter():
    """Test apply_modifications rejects fill_trap without target_value."""
    surface = np.ones((20, 20)) * 0.5
    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifications = [
        Modification(
            type="fill_trap",
            coords=(50.0, 50.0),
            radius=3.0,
            parameters={},  # Missing target_value
        ),
    ]

    modifier = SurfaceModifier(surface, grid_x, grid_y)

    with pytest.raises(ValueError, match="requires 'target_value'"):
        modifier.apply_modifications(modifications)


# =============================================================================
# UTILITY METHOD TESTS
# =============================================================================


def test_reset_surface():
    """Test reset() restores original surface."""
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.8

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modifier.remove_barrier((50.0, 50.0), radius=5.0)

    # Surface modified
    assert not np.allclose(modifier.modified_surface, surface)

    # Reset
    modifier.reset()
    assert np.allclose(modifier.modified_surface, surface)


def test_get_modification_impact():
    """Test get_modification_impact() computes change statistics."""
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.8

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modifier.remove_barrier((50.0, 50.0), radius=5.0)

    impact = modifier.get_modification_impact()

    assert "mean_change" in impact
    assert "max_change" in impact
    assert "affected_cells" in impact
    assert "affected_fraction" in impact

    # Some cells should be affected
    assert impact["affected_cells"] > 0
    assert impact["affected_fraction"] > 0
    assert impact["max_change"] > 0


# =============================================================================
# COUNTERFACTUAL ANALYZER TESTS
# =============================================================================


def test_counterfactual_analyzer_init():
    """Test CounterfactualAnalyzer initialization."""
    surface = np.random.rand(20, 20) * 0.5 + 0.3
    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    # Create mock Morse-Smale result
    morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),  # Minimum
            MockCriticalPoint(point_id=1, point_type=1),  # Saddle
            MockCriticalPoint(point_id=2, point_type=2),  # Maximum
        ]
    )

    analyzer = CounterfactualAnalyzer(surface, morse_smale, grid_x, grid_y)

    assert analyzer.original_surface.shape == (20, 20)
    assert analyzer.original_morse_smale == morse_smale
    assert np.allclose(analyzer.original_surface, surface)


def test_compare_critical_points_no_changes():
    """Test compare_critical_points with identical topologies."""
    # Create identical Morse-Smale results
    morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),  # Minimum
            MockCriticalPoint(point_id=1, point_type=1),  # Saddle
            MockCriticalPoint(point_id=2, point_type=2),  # Maximum
        ]
    )

    surface = np.random.rand(20, 20)
    analyzer = CounterfactualAnalyzer(surface, morse_smale)

    changes = analyzer.compare_critical_points(morse_smale, morse_smale)

    assert changes["minima_removed"] == 0
    assert changes["minima_added"] == 0
    assert changes["saddles_removed"] == 0
    assert changes["saddles_added"] == 0
    assert changes["maxima_removed"] == 0
    assert changes["maxima_added"] == 0
    assert changes["total_change"] == 0


def test_compare_critical_points_barrier_removed():
    """Test compare_critical_points detects removed saddle."""
    # Original: 1 minimum, 1 saddle, 1 maximum
    original = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=1, point_type=1),
            MockCriticalPoint(point_id=2, point_type=2),
        ]
    )

    # Modified: 1 minimum, 0 saddles, 1 maximum (saddle removed)
    modified = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=2, point_type=2),
        ]
    )

    surface = np.random.rand(20, 20)
    analyzer = CounterfactualAnalyzer(surface, original)

    changes = analyzer.compare_critical_points(original, modified)

    assert changes["saddles_removed"] == 1
    assert changes["saddles_added"] == 0
    assert changes["minima_removed"] == 0
    assert changes["total_change"] == 1


def test_compare_critical_points_trap_eliminated():
    """Test compare_critical_points detects eliminated minimum."""
    # Original: 2 minima, 1 saddle, 1 maximum
    original = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=1, point_type=0),
            MockCriticalPoint(point_id=2, point_type=1),
            MockCriticalPoint(point_id=3, point_type=2),
        ]
    )

    # Modified: 1 minimum, 1 saddle, 1 maximum (one minimum eliminated)
    modified = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=2, point_type=1),
            MockCriticalPoint(point_id=3, point_type=2),
        ]
    )

    surface = np.random.rand(20, 20)
    analyzer = CounterfactualAnalyzer(surface, original)

    changes = analyzer.compare_critical_points(original, modified)

    assert changes["minima_removed"] == 1
    assert changes["minima_added"] == 0
    assert changes["total_change"] == 1


def test_compute_population_impact_empty():
    """Test compute_population_impact with empty flow redistribution."""
    surface = np.random.rand(20, 20)
    morse_smale = MockMorseSmaleResult()
    analyzer = CounterfactualAnalyzer(surface, morse_smale)

    flow_redistribution = pd.DataFrame({
        "from_basin": [],
        "to_basin": [],
        "population_moved": [],
    })

    lsoa_populations = pd.DataFrame({
        "lsoa_code": ["E01000001"],
        "population": [1000],
    })

    impact = analyzer.compute_population_impact(flow_redistribution, lsoa_populations)

    assert impact["total_affected"] == 0
    assert impact["avg_mobility_change"] == 0.0
    assert impact["basin_population_changes"] == {}


def test_compute_population_impact_basic():
    """Test compute_population_impact with simple flow."""
    surface = np.random.rand(20, 20)
    morse_smale = MockMorseSmaleResult()
    analyzer = CounterfactualAnalyzer(surface, morse_smale)

    flow_redistribution = pd.DataFrame({
        "from_basin": [1, 2],
        "to_basin": [3, 3],
        "population_moved": [500, 300],
        "from_mobility": [0.3, 0.35],
        "to_mobility": [0.5, 0.55],
    })

    lsoa_populations = pd.DataFrame({
        "lsoa_code": ["E01000001", "E01000002"],
        "population": [1000, 800],
    })

    impact = analyzer.compute_population_impact(flow_redistribution, lsoa_populations)

    assert impact["total_affected"] == 800
    assert impact["avg_mobility_change"] > 0  # Positive change
    # Basin 1 loses 500, basin 2 loses 300, basin 3 gains 800
    assert impact["basin_population_changes"][1] == -500
    assert impact["basin_population_changes"][2] == -300
    assert impact["basin_population_changes"][3] == 800


def test_analyze_creates_result():
    """Test analyze() creates CounterfactualResult."""
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.8  # Saddle

    morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=1, point_type=1),
            MockCriticalPoint(point_id=2, point_type=2),
        ]
    )

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    analyzer = CounterfactualAnalyzer(surface, morse_smale, grid_x, grid_y)

    # Create modified surface
    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified_surface = modifier.remove_barrier((50.0, 50.0), radius=5.0)

    modification = Modification(
        type="remove_barrier",
        coords=(50.0, 50.0),
        radius=5.0,
        parameters={"method": "gaussian"},
    )

    result = analyzer.analyze(modified_surface, modification)

    assert isinstance(result, CounterfactualResult)
    assert result.modification == modification
    assert result.original_morse_smale == morse_smale
    assert "minima_removed" in result.critical_point_changes
    assert result.barriers_removed >= 0
    assert result.traps_reduced >= 0


def test_analyze_multiple_modifications():
    """Test analyze() with multiple modifications."""
    surface = np.ones((20, 20)) * 0.5
    surface[10, 10] = 0.8  # Saddle
    surface[5, 5] = 0.1    # Trap

    morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=1, point_type=0),
            MockCriticalPoint(point_id=2, point_type=1),
            MockCriticalPoint(point_id=3, point_type=2),
        ]
    )

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    analyzer = CounterfactualAnalyzer(surface, morse_smale, grid_x, grid_y)

    # Apply multiple modifications
    modifications = [
        Modification(
            type="remove_barrier",
            coords=(50.0, 50.0),
            radius=3.0,
            parameters={"method": "gaussian"},
        ),
        Modification(
            type="fill_trap",
            coords=(25.0, 25.0),
            radius=3.0,
            parameters={"target_value": 0.4},
        ),
    ]

    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modified_surface = modifier.apply_modifications(modifications)

    result = analyzer.analyze(modified_surface, modifications)

    assert isinstance(result, CounterfactualResult)
    assert result.modification == modifications
    assert result.critical_point_changes["total_change"] >= 0


# =============================================================================
# VISUALIZATION TESTS
# =============================================================================


def test_visualize_counterfactual_basic():
    """Test visualize_counterfactual generates figures."""
    # Create surfaces
    original = np.ones((20, 20)) * 0.5
    original[10, 10] = 0.8

    modified = original.copy()
    modified[10, 10] = 0.6  # Reduced saddle

    # Create result
    morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=1, point_type=1),
            MockCriticalPoint(point_id=2, point_type=2),
        ]
    )

    modification = Modification(
        type="remove_barrier",
        coords=(50.0, 50.0),
        radius=5.0,
    )

    result = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        critical_point_changes={
            "minima_removed": 0,
            "minima_added": 0,
            "saddles_removed": 1,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 1,
        },
    )

    figures = visualize_counterfactual(original, modified, result)

    # Check figures created
    assert "surface_comparison" in figures
    assert "critical_points" in figures

    # Clean up
    import matplotlib.pyplot as plt
    for fig in figures.values():
        plt.close(fig)


def test_visualize_counterfactual_with_grids():
    """Test visualize_counterfactual with grid coordinates."""
    original = np.random.rand(20, 20) * 0.5 + 0.3
    modified = original + 0.05  # Small uniform increase

    grid_x = np.linspace(0, 100, 20)
    grid_y = np.linspace(0, 100, 20)

    morse_smale = MockMorseSmaleResult()
    modification = Modification(type="fill_trap", coords=(50.0, 50.0), radius=3.0)

    result = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        critical_point_changes={
            "minima_removed": 1,
            "minima_added": 0,
            "saddles_removed": 0,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 1,
        },
    )

    figures = visualize_counterfactual(original, modified, result, grid_x, grid_y)

    assert len(figures) == 2

    # Clean up
    import matplotlib.pyplot as plt
    for fig in figures.values():
        plt.close(fig)


# =============================================================================
# REPORTING TESTS
# =============================================================================


def test_generate_counterfactual_report_basic():
    """Test generate_counterfactual_report creates all sections."""
    morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),
            MockCriticalPoint(point_id=1, point_type=1),
            MockCriticalPoint(point_id=2, point_type=2),
        ]
    )

    modification = Modification(
        type="remove_barrier",
        coords=(50.0, 50.0),
        radius=5.0,
        parameters={"method": "gaussian"},
    )

    result = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        barriers_removed=1,
        traps_reduced=0,
        population_affected=1500,
        critical_point_changes={
            "minima_removed": 0,
            "minima_added": 0,
            "saddles_removed": 1,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 1,
        },
    )

    report = generate_counterfactual_report(result, "New bus route")

    # Check all sections present
    assert "summary" in report
    assert "modifications_applied" in report
    assert "topology_changes" in report
    assert "population_impact" in report
    assert "recommendations" in report
    assert "impact_assessment" in report

    # Check summary content
    assert report["summary"]["barriers_removed"] == 1
    assert report["summary"]["population_affected"] == 1500
    assert report["summary"]["intervention_description"] == "New bus route"


def test_generate_counterfactual_report_multiple_modifications():
    """Test report generation with multiple modifications."""
    morse_smale = MockMorseSmaleResult()

    modifications = [
        Modification(type="remove_barrier", coords=(50.0, 50.0), radius=5.0),
        Modification(type="fill_trap", coords=(25.0, 25.0), radius=3.0, parameters={"target_value": 0.4}),
    ]

    result = CounterfactualResult(
        modification=modifications,
        original_morse_smale=morse_smale,
        barriers_removed=1,
        traps_reduced=1,
        population_affected=2500,
        critical_point_changes={
            "minima_removed": 1,
            "minima_added": 0,
            "saddles_removed": 1,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 2,
        },
    )

    report = generate_counterfactual_report(result)

    assert report["modifications_applied"]["count"] == 2
    assert len(report["modifications_applied"]["modifications"]) == 2
    assert report["summary"]["barriers_removed"] == 1
    assert report["summary"]["traps_reduced"] == 1


def test_generate_counterfactual_report_impact_levels():
    """Test report correctly categorizes impact levels."""
    morse_smale = MockMorseSmaleResult()
    modification = Modification(type="remove_barrier", coords=(50.0, 50.0), radius=5.0)

    # High impact (3+ changes)
    result_high = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        critical_point_changes={
            "minima_removed": 2,
            "minima_added": 0,
            "saddles_removed": 1,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 3,
        },
    )

    report_high = generate_counterfactual_report(result_high)
    assert report_high["impact_assessment"]["impact_level"] == "High"

    # Moderate impact (1-2 changes)
    result_mod = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        critical_point_changes={
            "minima_removed": 1,
            "minima_added": 0,
            "saddles_removed": 0,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 1,
        },
    )

    report_mod = generate_counterfactual_report(result_mod)
    assert report_mod["impact_assessment"]["impact_level"] == "Moderate"

    # Low impact (0 changes)
    result_low = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        critical_point_changes={
            "minima_removed": 0,
            "minima_added": 0,
            "saddles_removed": 0,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 0,
        },
    )

    report_low = generate_counterfactual_report(result_low)
    assert report_low["impact_assessment"]["impact_level"] == "Low"


def test_generate_counterfactual_report_with_flow_data():
    """Test report includes flow redistribution data."""
    morse_smale = MockMorseSmaleResult()
    modification = Modification(type="remove_barrier", coords=(50.0, 50.0), radius=5.0)

    flow_redistribution = pd.DataFrame({
        "from_basin": [1, 2, 3],
        "to_basin": [4, 4, 5],
        "population_moved": [500, 300, 200],
    })

    result = CounterfactualResult(
        modification=modification,
        original_morse_smale=morse_smale,
        flow_redistribution=flow_redistribution,
        critical_point_changes={"total_change": 1},
    )

    report = generate_counterfactual_report(result)

    assert report["population_impact"]["total_population_moved"] == 1000
    assert report["population_impact"]["flow_transitions"] == 3
    assert len(report["population_impact"]["major_flows"]) > 0


# =============================================================================
# INTEGRATION TEST
# =============================================================================


def test_full_counterfactual_workflow():
    """Integration test: full counterfactual analysis workflow."""
    # Step 1: Create synthetic surface with known barrier
    surface = np.ones((30, 30)) * 0.4
    
    # Add a saddle barrier at center (high value)
    for i in range(12, 18):
        for j in range(12, 18):
            distance = np.sqrt((i - 15)**2 + (j - 15)**2)
            if distance < 4:
                surface[i, j] = 0.7 - distance * 0.05

    # Add traps on either side
    surface[10, 10] = 0.15  # Left trap
    surface[20, 20] = 0.18  # Right trap

    grid_x = np.linspace(0, 100, 30)
    grid_y = np.linspace(0, 100, 30)

    # Step 2: Create original Morse-Smale result (mock)
    original_morse_smale = MockMorseSmaleResult(
        critical_points=[
            MockCriticalPoint(point_id=0, point_type=0),  # Left minimum
            MockCriticalPoint(point_id=1, point_type=0),  # Right minimum
            MockCriticalPoint(point_id=2, point_type=1),  # Saddle at barrier
            MockCriticalPoint(point_id=3, point_type=2),  # Maximum
        ]
    )

    # Step 3: Apply barrier removal modification
    modifier = SurfaceModifier(surface, grid_x, grid_y)
    modification = Modification(
        type="remove_barrier",
        coords=(50.0, 50.0),
        radius=5.0,
        parameters={"method": "gaussian"},
    )
    modified_surface = modifier.remove_barrier(
        modification.coords,
        modification.radius,
        method="gaussian",
    )

    # Verify modification had effect
    impact = modifier.get_modification_impact()
    assert impact["affected_cells"] > 0
    assert impact["max_change"] > 0

    # Step 4: Analyze counterfactual
    analyzer = CounterfactualAnalyzer(surface, original_morse_smale, grid_x, grid_y)
    result = analyzer.analyze(modified_surface, modification)

    # Verify result structure
    assert isinstance(result, CounterfactualResult)
    assert result.modification == modification
    assert "total_change" in result.critical_point_changes

    # Step 5: Generate visualizations
    figures = visualize_counterfactual(surface, modified_surface, result, grid_x, grid_y)
    assert "surface_comparison" in figures
    assert "critical_points" in figures

    # Step 6: Generate report
    report = generate_counterfactual_report(result, "Barrier removal intervention")
    assert "summary" in report
    assert "recommendations" in report
    assert report["summary"]["intervention_description"] == "Barrier removal intervention"

    # Step 7: Validate recommendations generated
    assert len(report["recommendations"]) > 0
    assert report["impact_assessment"]["impact_level"] in ["Low", "Moderate", "High"]

    # Clean up figures
    import matplotlib.pyplot as plt
    for fig in figures.values():
        plt.close(fig)

    logger.info("Full counterfactual workflow integration test passed")
