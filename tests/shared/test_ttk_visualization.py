"""
Tests for shared TTK visualization utilities.

Tests persistence curve generation and plotting functions.
"""

import numpy as np
import pytest

from shared.ttk_visualization import (
    create_persistence_curve,
    plot_persistence_comparison,
    plot_persistence_curve,
)
from shared.ttk_visualization.persistence_curves import (
    PersistenceCurveData,
    _compute_cumulative_curve,
    export_diagram_to_vtk,
)


@pytest.fixture
def sample_diagrams():
    """Create sample persistence diagrams for testing."""
    # Diagram 1: Simple features
    diagram1 = np.array(
        [
            [0.0, 1.0, 0],  # H0 feature
            [0.5, 2.0, 1],  # H1 feature
            [0.2, 1.5, 1],  # H1 feature
            [0.1, 3.0, 2],  # H2 feature
        ]
    )

    # Diagram 2: Different distribution
    diagram2 = np.array(
        [
            [0.0, 0.8, 0],  # H0 feature
            [0.3, 1.5, 1],  # H1 feature
            [0.4, 2.5, 1],  # H1 feature
            [0.2, 2.0, 2],  # H2 feature
        ]
    )

    return [diagram1, diagram2]


@pytest.fixture
def empty_diagram():
    """Create empty persistence diagram."""
    return np.array([]).reshape(0, 3)


class TestPersistenceCurves:
    """Tests for persistence curve generation."""

    def test_compute_cumulative_curve(self):
        """Test cumulative curve computation."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        curve = _compute_cumulative_curve(values, n_bins=5)

        # Check shape
        assert curve.shape == (5, 2)

        # Check monotonicity
        assert np.all(curve[1:, 1] >= curve[:-1, 1])

        # Check bounds
        assert curve[-1, 1] <= 1.0
        assert curve[0, 1] >= 0.0

    def test_compute_cumulative_curve_identical_values(self):
        """Test curve with all identical values."""
        values = np.array([1.0, 1.0, 1.0, 1.0])
        curve = _compute_cumulative_curve(values, n_bins=10)

        # Should return two points at the same value
        assert curve.shape == (2, 2)
        assert curve[0, 0] == curve[1, 0] == 1.0

    def test_compute_cumulative_curve_empty(self):
        """Test curve with empty values."""
        values = np.array([])
        curve = _compute_cumulative_curve(values, n_bins=10)

        # Should return minimal curve
        assert curve.shape == (2, 2)

    def test_create_persistence_curve_basic(self, sample_diagrams):
        """Test basic persistence curve creation."""
        curves = create_persistence_curve(sample_diagrams, labels=["Diag1", "Diag2"])

        # Check structure
        assert isinstance(curves, PersistenceCurveData)
        assert len(curves.labels) == 2
        assert curves.labels == ["Diag1", "Diag2"]
        assert len(curves.birth_curves) == 2
        assert len(curves.death_curves) == 2
        assert len(curves.persistence_curves) == 2
        assert len(curves.n_features) == 2

        # Check feature counts
        assert curves.n_features[0] == 4
        assert curves.n_features[1] == 4

    def test_create_persistence_curve_dimension_filter(self, sample_diagrams):
        """Test dimension filtering."""
        # Only H1 features
        curves = create_persistence_curve(sample_diagrams, dimensions=[1])

        # Should only include H1 features (2 per diagram)
        assert curves.n_features[0] == 2
        assert curves.n_features[1] == 2
        assert curves.dimensions == [1]

    def test_create_persistence_curve_curve_type(self, sample_diagrams):
        """Test different curve types."""
        # Birth only
        curves_birth = create_persistence_curve(sample_diagrams, curve_type="birth")
        assert len(curves_birth.birth_curves) == 2
        assert len(curves_birth.death_curves) == 0
        assert len(curves_birth.persistence_curves) == 0

        # Death only
        curves_death = create_persistence_curve(sample_diagrams, curve_type="death")
        assert len(curves_death.birth_curves) == 0
        assert len(curves_death.death_curves) == 2
        assert len(curves_death.persistence_curves) == 0

        # Persistence only
        curves_pers = create_persistence_curve(sample_diagrams, curve_type="persistence")
        assert len(curves_pers.birth_curves) == 0
        assert len(curves_pers.death_curves) == 0
        assert len(curves_pers.persistence_curves) == 2

    def test_create_persistence_curve_auto_labels(self, sample_diagrams):
        """Test automatic label generation."""
        curves = create_persistence_curve(sample_diagrams)

        assert curves.labels == ["Dataset 0", "Dataset 1"]

    def test_create_persistence_curve_empty_list(self):
        """Test with empty diagram list."""
        with pytest.raises(ValueError, match="diagrams list cannot be empty"):
            create_persistence_curve([])

    def test_create_persistence_curve_invalid_shape(self):
        """Test with invalid diagram shape."""
        invalid_diagram = np.array([[1.0, 2.0]])  # Missing dimension column

        with pytest.raises(ValueError, match="invalid shape"):
            create_persistence_curve([invalid_diagram])

    def test_create_persistence_curve_label_mismatch(self, sample_diagrams):
        """Test with mismatched labels."""
        with pytest.raises(ValueError, match="Number of labels"):
            create_persistence_curve(sample_diagrams, labels=["Only one label"])


class TestExportDiagramToVTK:
    """Tests for VTK export functionality."""

    def test_export_diagram_to_vtk(self, sample_diagrams, tmp_path):
        """Test VTK export."""
        pytest.importorskip("pyvista")

        output_path = tmp_path / "diagram.vtp"
        result_path = export_diagram_to_vtk(sample_diagrams[0], output_path)

        # Check file created
        assert result_path.exists()
        assert result_path == output_path

    def test_export_diagram_dimension_filter(self, sample_diagrams, tmp_path):
        """Test VTK export with dimension filtering."""
        pytest.importorskip("pyvista")

        output_path = tmp_path / "diagram_h1.vtp"
        result_path = export_diagram_to_vtk(sample_diagrams[0], output_path, dimension=1)

        assert result_path.exists()

    def test_export_diagram_invalid_shape(self, tmp_path):
        """Test VTK export with invalid shape."""
        pytest.importorskip("pyvista")

        invalid_diagram = np.array([[1.0, 2.0]])
        output_path = tmp_path / "diagram.vtp"

        with pytest.raises(ValueError, match="must have shape"):
            export_diagram_to_vtk(invalid_diagram, output_path)


class TestPlottingFunctions:
    """Tests for plotting functions."""

    def test_plot_persistence_curve_basic(self, sample_diagrams):
        """Test basic curve plotting."""
        pytest.importorskip("matplotlib")

        curves = create_persistence_curve(sample_diagrams, labels=["A", "B"])
        fig = plot_persistence_curve(curves, curve_type="persistence")

        assert fig is not None
        assert len(fig.axes) == 1

    def test_plot_persistence_curve_invalid_type(self, sample_diagrams):
        """Test with invalid curve type."""
        pytest.importorskip("matplotlib")

        curves = create_persistence_curve(sample_diagrams)

        with pytest.raises(ValueError, match="Invalid curve_type"):
            plot_persistence_curve(curves, curve_type="invalid")

    def test_plot_persistence_comparison(self, sample_diagrams):
        """Test comparison plotting."""
        pytest.importorskip("matplotlib")

        curves = create_persistence_curve(sample_diagrams, labels=["Crisis", "Normal"])
        fig = plot_persistence_comparison(curves)

        assert fig is not None
        # Should have 3 subplots (birth, death, persistence)
        assert len(fig.axes) == 3


class TestDistanceVisualization:
    """Tests for distance matrix visualization."""

    def test_plot_distance_heatmap(self):
        """Test distance heatmap plotting."""
        pytest.importorskip("matplotlib")

        from shared.ttk_visualization.ttk_plots import plot_distance_heatmap

        # Create sample distance matrix
        distances = np.array([[0.0, 0.5, 0.8], [0.5, 0.0, 0.3], [0.8, 0.3, 0.0]])

        labels = ["2008", "2015", "2020"]

        fig = plot_distance_heatmap(distances, labels, metric="Bottleneck")

        assert fig is not None
        assert len(fig.axes) == 2  # Main plot + colorbar

    def test_plot_distance_heatmap_invalid_shape(self):
        """Test with non-square matrix."""
        pytest.importorskip("matplotlib")

        from shared.ttk_visualization.ttk_plots import plot_distance_heatmap

        distances = np.array([[0.0, 0.5], [0.5, 0.0], [0.8, 0.3]])
        labels = ["A", "B", "C"]

        with pytest.raises(ValueError, match="must be square"):
            plot_distance_heatmap(distances, labels)

    def test_plot_distance_heatmap_label_mismatch(self):
        """Test with mismatched labels."""
        pytest.importorskip("matplotlib")

        from shared.ttk_visualization.ttk_plots import plot_distance_heatmap

        distances = np.array([[0.0, 0.5], [0.5, 0.0]])
        labels = ["A", "B", "C"]  # Too many labels

        with pytest.raises(ValueError, match="Number of labels"):
            plot_distance_heatmap(distances, labels)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
