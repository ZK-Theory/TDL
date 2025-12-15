"""
Tests for financial TDA TTK visualization utilities.

Tests persistence curve comparison and distance matrix visualization
for market regime analysis.
"""

import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend for testing

import numpy as np
import pytest

from financial_tda.viz.ttk_plots import (
    plot_bottleneck_distance_matrix,
    plot_persistence_curve_comparison,
)


@pytest.fixture
def sample_regime_diagrams():
    """Create sample persistence diagrams for different market regimes."""
    # Crisis regime: More H1 features (loops), higher persistence
    crisis_diagram = np.array(
        [
            [0.0, 2.5, 0],  # H0: Long-lived component
            [0.2, 1.8, 1],  # H1: Significant loop
            [0.3, 1.5, 1],  # H1: Another loop
            [0.5, 1.2, 1],  # H1: Medium loop
            [0.1, 0.4, 1],  # H1: Small loop (noise)
            [0.2, 2.0, 2],  # H2: Void
        ]
    )

    # Normal regime: Fewer H1 features, lower persistence
    normal_diagram = np.array(
        [
            [0.0, 2.0, 0],  # H0: Component
            [0.4, 1.0, 1],  # H1: Small loop
            [0.5, 0.9, 1],  # H1: Smaller loop
            [0.3, 1.5, 2],  # H2: Small void
        ]
    )

    # Another crisis (similar to first)
    crisis2_diagram = np.array(
        [
            [0.0, 2.3, 0],
            [0.3, 1.7, 1],
            [0.4, 1.4, 1],
            [0.6, 1.1, 1],
            [0.2, 1.8, 2],
        ]
    )

    return [crisis_diagram, normal_diagram, crisis2_diagram]


@pytest.fixture
def empty_diagrams():
    """Create empty diagrams for edge case testing."""
    return [np.array([]).reshape(0, 3), np.array([]).reshape(0, 3)]


class TestPersistenceCurveComparison:
    """Tests for persistence curve comparison visualization."""

    def test_basic_comparison(self, sample_regime_diagrams):
        """Test basic regime comparison plot."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis 2008", "Normal 2007"]

        fig = plot_persistence_curve_comparison(diagrams, labels=labels, highlight_differences=False)

        assert fig is not None
        # Should have 3 subplots (birth, death, persistence)
        assert len(fig.axes) == 3

    def test_comparison_with_annotations(self, sample_regime_diagrams):
        """Test comparison with statistical annotations."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis", "Normal"]

        fig = plot_persistence_curve_comparison(diagrams, labels=labels, highlight_differences=True)

        assert fig is not None
        assert len(fig.axes) == 3

    def test_comparison_dimension_filter(self, sample_regime_diagrams):
        """Test comparison with dimension filtering."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis", "Normal"]

        # Only H1 features
        fig = plot_persistence_curve_comparison(diagrams, labels=labels, dimensions=[1])

        assert fig is not None

    def test_comparison_auto_labels(self, sample_regime_diagrams):
        """Test automatic label generation."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]

        fig = plot_persistence_curve_comparison(diagrams)

        assert fig is not None

    def test_comparison_empty_list(self):
        """Test with empty diagram list."""
        pytest.importorskip("matplotlib")

        with pytest.raises(ValueError, match="diagrams list cannot be empty"):
            plot_persistence_curve_comparison([])

    def test_comparison_label_mismatch(self, sample_regime_diagrams):
        """Test with mismatched labels."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Only one"]

        with pytest.raises(ValueError, match="Number of labels"):
            plot_persistence_curve_comparison(diagrams, labels=labels)

    def test_comparison_save_path(self, sample_regime_diagrams, tmp_path):
        """Test saving figure to file."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis", "Normal"]
        output_path = tmp_path / "comparison.png"

        fig = plot_persistence_curve_comparison(diagrams, labels=labels, save_path=output_path)

        assert fig is not None
        assert output_path.exists()


class TestBottleneckDistanceMatrix:
    """Tests for bottleneck distance matrix visualization."""

    def test_basic_distance_matrix(self, sample_regime_diagrams):
        """Test basic distance matrix visualization."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams
        labels = ["Crisis 2008", "Normal 2007", "Crisis 2015"]

        fig = plot_bottleneck_distance_matrix(diagrams, labels, add_dendrogram=False)

        assert fig is not None
        # Should have at least main heatmap
        assert len(fig.axes) >= 1

    def test_distance_matrix_with_dendrogram(self, sample_regime_diagrams):
        """Test distance matrix with hierarchical clustering."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams
        labels = ["Crisis 2008", "Normal 2007", "Crisis 2015"]

        fig = plot_bottleneck_distance_matrix(diagrams, labels, add_dendrogram=True)

        assert fig is not None
        # Should have multiple subplots (dendrogram + heatmap + colorbar)
        assert len(fig.axes) >= 3

    def test_distance_matrix_dimension_filter(self, sample_regime_diagrams):
        """Test distance matrix with dimension filtering."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams
        labels = ["Crisis 2008", "Normal 2007", "Crisis 2015"]

        # Only H1 distances
        fig = plot_bottleneck_distance_matrix(diagrams, labels, dimension=1, add_dendrogram=False)

        assert fig is not None

    def test_distance_matrix_wasserstein(self, sample_regime_diagrams):
        """Test with Wasserstein distance metric."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis", "Normal"]

        fig = plot_bottleneck_distance_matrix(diagrams, labels, metric="wasserstein", add_dendrogram=False)

        assert fig is not None

    def test_distance_matrix_invalid_metric(self, sample_regime_diagrams):
        """Test with invalid distance metric."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis", "Normal"]

        with pytest.raises(ValueError, match="Invalid metric"):
            plot_bottleneck_distance_matrix(diagrams, labels, metric="invalid")

    def test_distance_matrix_empty_list(self):
        """Test with empty diagram list."""
        pytest.importorskip("matplotlib")

        with pytest.raises(ValueError, match="diagrams list cannot be empty"):
            plot_bottleneck_distance_matrix([], [])

    def test_distance_matrix_label_mismatch(self, sample_regime_diagrams):
        """Test with mismatched labels."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Only one"]

        with pytest.raises(ValueError, match="Number of labels"):
            plot_bottleneck_distance_matrix(diagrams, labels)

    def test_distance_matrix_two_diagrams(self, sample_regime_diagrams):
        """Test with only two diagrams (no dendrogram)."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams[:2]
        labels = ["Crisis", "Normal"]

        # Should work even with add_dendrogram=True (falls back to simple heatmap)
        fig = plot_bottleneck_distance_matrix(diagrams, labels, add_dendrogram=True)

        assert fig is not None

    def test_distance_matrix_save_path(self, sample_regime_diagrams, tmp_path):
        """Test saving distance matrix to file."""
        pytest.importorskip("matplotlib")

        diagrams = sample_regime_diagrams
        labels = ["Crisis 2008", "Normal 2007", "Crisis 2015"]
        output_path = tmp_path / "distance_matrix.png"

        fig = plot_bottleneck_distance_matrix(diagrams, labels, save_path=output_path, add_dendrogram=False)

        assert fig is not None
        assert output_path.exists()


class TestIntegrationWithTopology:
    """Integration tests with financial_tda.topology functions."""

    def test_integration_with_compute_persistence(self):
        """Test integration with actual persistence computation."""
        pytest.importorskip("matplotlib")

        # Import required functions
        from financial_tda.topology.embedding import takens_embedding
        from financial_tda.topology.filtration import compute_persistence_vr

        # Create synthetic time series
        np.random.seed(42)
        crisis_ts = np.random.randn(200).cumsum()  # Random walk (crisis volatility)
        normal_ts = np.sin(np.linspace(0, 4 * np.pi, 200)) + 0.1 * np.random.randn(200)  # Periodic + noise

        # Embed
        crisis_emb = takens_embedding(crisis_ts, delay=5, dimension=3)
        normal_emb = takens_embedding(normal_ts, delay=5, dimension=3)

        # Compute persistence
        crisis_diag = compute_persistence_vr(crisis_emb)
        normal_diag = compute_persistence_vr(normal_emb)

        # Plot comparison
        fig = plot_persistence_curve_comparison([crisis_diag, normal_diag], labels=["Crisis", "Normal"])

        assert fig is not None
        assert len(fig.axes) == 3

    def test_integration_distance_computation(self):
        """Test distance matrix with actual distance computation."""
        pytest.importorskip("matplotlib")

        from financial_tda.topology.embedding import takens_embedding
        from financial_tda.topology.filtration import compute_persistence_vr

        # Create three different regimes
        np.random.seed(42)
        ts1 = np.random.randn(150).cumsum()
        ts2 = np.sin(np.linspace(0, 4 * np.pi, 150))
        ts3 = np.random.randn(150).cumsum()  # Similar to ts1

        # Compute diagrams
        diagrams = []
        for ts in [ts1, ts2, ts3]:
            emb = takens_embedding(ts, delay=3, dimension=3)
            diag = compute_persistence_vr(emb)
            diagrams.append(diag)

        # Plot distance matrix
        labels = ["Regime 1", "Regime 2", "Regime 3"]
        fig = plot_bottleneck_distance_matrix(diagrams, labels, add_dendrogram=True)

        assert fig is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
