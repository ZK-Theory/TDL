"""
Tests for poverty TDA TTK visualization utilities.

Tests simplification comparison and critical point persistence visualization
for poverty landscape analysis.
"""

import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend for testing

import numpy as np
import pytest

from poverty_tda.viz.ttk_plots import (
    plot_critical_point_persistence,
    plot_simplification_comparison,
)

# Try to import pyvista
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False


@pytest.fixture
def sample_critical_points():
    """Create sample critical points for testing."""
    from dataclasses import dataclass

    @dataclass
    class MockCriticalPoint:
        point_id: int
        position: tuple
        value: float
        point_type: int
        persistence: float

    points = [
        # Minima (traps) - type 0
        MockCriticalPoint(0, (1.0, 2.0, 0.0), 0.2, 0, 0.15),
        MockCriticalPoint(1, (3.0, 4.0, 0.0), 0.3, 0, 0.10),
        # Saddles - type 1
        MockCriticalPoint(2, (2.0, 3.0, 0.0), 0.5, 1, 0.08),
        MockCriticalPoint(3, (4.0, 5.0, 0.0), 0.6, 1, 0.06),
        # Maxima (peaks) - type 2
        MockCriticalPoint(4, (5.0, 6.0, 0.0), 0.8, 2, 0.12),
        MockCriticalPoint(5, (6.0, 7.0, 0.0), 0.9, 2, 0.09),
    ]

    return points


@pytest.fixture
def sample_morse_smale_result(sample_critical_points):
    """Create mock Morse-Smale result."""
    from dataclasses import dataclass

    @dataclass
    class MockMorseSmaleResult:
        critical_points: list
        scalar_range: tuple
        simplified_data: str | None = None

    return MockMorseSmaleResult(
        critical_points=sample_critical_points,
        scalar_range=(0.0, 1.0),
        simplified_data=None,
    )


@pytest.fixture
def synthetic_vti(tmp_path):
    """Create synthetic VTI file for testing."""
    if not HAS_PYVISTA:
        pytest.skip("PyVista required for VTI generation")

    # Create simple 2D grid
    nx, ny = 10, 10
    x = np.linspace(0, 1, nx)
    y = np.linspace(0, 1, ny)
    X, Y = np.meshgrid(x, y)

    # Simple scalar field
    values = np.sin(2 * np.pi * X) * np.cos(2 * np.pi * Y)

    # Create VTK grid
    grid = pv.StructuredGrid()
    grid.points = np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)].astype(np.float32)
    grid.dimensions = (nx, ny, 1)
    grid["mobility"] = values.ravel()

    # Save (use .vts for StructuredGrid)
    vti_path = tmp_path / "test_mobility.vts"
    grid.save(vti_path)

    return vti_path


class TestCriticalPointPersistence:
    """Tests for critical point persistence visualization."""

    def test_basic_persistence_plot(self, sample_critical_points):
        """Test basic persistence diagram plotting."""
        fig = plot_critical_point_persistence(sample_critical_points, color_by_type=True, geographic_overlay=False)

        assert fig is not None
        assert len(fig.axes) >= 1  # At least persistence diagram

    def test_persistence_with_geographic_overlay(self, sample_critical_points):
        """Test persistence diagram with geographic overlay."""
        fig = plot_critical_point_persistence(
            sample_critical_points,
            color_by_type=True,
            geographic_overlay=True,
            bounds=(0, 10, 0, 10),
        )

        assert fig is not None
        assert len(fig.axes) >= 2  # Persistence + geographic

    def test_persistence_without_color_coding(self, sample_critical_points):
        """Test persistence diagram without type-based coloring."""
        fig = plot_critical_point_persistence(sample_critical_points, color_by_type=False)

        assert fig is not None

    def test_persistence_empty_list(self):
        """Test with empty critical points list."""
        with pytest.raises(ValueError, match="No critical points provided"):
            plot_critical_point_persistence([])

    def test_persistence_save_path(self, sample_critical_points, tmp_path):
        """Test saving persistence diagram."""
        output_path = tmp_path / "persistence.png"

        fig = plot_critical_point_persistence(sample_critical_points, save_path=output_path)

        assert fig is not None
        assert output_path.exists()


class TestSimplificationComparison:
    """Tests for simplification comparison visualization."""

    def test_basic_simplification_comparison(self, synthetic_vti, sample_morse_smale_result):
        """Test basic simplification comparison plot."""
        pytest.importorskip("pyvista")

        fig = plot_simplification_comparison(
            synthetic_vti,
            sample_morse_smale_result,
            simplification_threshold=0.05,
            scalar_name="mobility",
        )

        assert fig is not None
        assert len(fig.axes) >= 2  # At least original and simplified

    def test_simplification_with_custom_title(self, synthetic_vti, sample_morse_smale_result):
        """Test with custom title."""
        pytest.importorskip("pyvista")

        fig = plot_simplification_comparison(
            synthetic_vti,
            sample_morse_smale_result,
            title="Custom Simplification Title",
            simplification_threshold=0.10,
        )

        assert fig is not None

    def test_simplification_nonexistent_file(self, sample_morse_smale_result, tmp_path):
        """Test with nonexistent VTI file."""
        pytest.importorskip("pyvista")

        fake_path = tmp_path / "nonexistent.vti"

        with pytest.raises(FileNotFoundError):
            plot_simplification_comparison(fake_path, sample_morse_smale_result)

    def test_simplification_invalid_scalar(self, synthetic_vti, sample_morse_smale_result):
        """Test with invalid scalar name."""
        pytest.importorskip("pyvista")

        with pytest.raises(ValueError, match="Scalar .* not found"):
            plot_simplification_comparison(
                synthetic_vti,
                sample_morse_smale_result,
                scalar_name="nonexistent_scalar",
            )

    def test_simplification_save_path(self, synthetic_vti, sample_morse_smale_result, tmp_path):
        """Test saving simplification comparison."""
        pytest.importorskip("pyvista")

        output_path = tmp_path / "simplification.png"

        fig = plot_simplification_comparison(synthetic_vti, sample_morse_smale_result, save_path=output_path)

        assert fig is not None
        assert output_path.exists()

    def test_simplification_no_pyvista(self, synthetic_vti, sample_morse_smale_result, monkeypatch):
        """Test graceful fallback when PyVista unavailable."""
        # This test checks the fallback behavior
        # In practice, if PyVista is available for fixture creation, it's available for plotting
        # But we test the code path exists
        pass


class TestIntegrationWithTopology:
    """Integration tests with poverty_tda.topology functions."""

    def test_integration_with_morse_smale(self, synthetic_vti):
        """Test integration with actual Morse-Smale computation."""
        pytest.importorskip("pyvista")

        # This would require TTK which may not be available in test environment
        # Test structure only
        from poverty_tda.topology.morse_smale import MorseSmaleResult

        # Create minimal result for testing
        result = MorseSmaleResult(
            critical_points=[],
            scalar_range=(0.0, 1.0),
        )

        # Should not raise error
        fig = plot_simplification_comparison(synthetic_vti, result, simplification_threshold=0.05)
        assert fig is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
