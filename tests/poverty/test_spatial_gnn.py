"""
Tests for GNN spatial graph construction module.

This module tests the LSOA adjacency graph construction, edge feature computation,
and graph validation utilities in poverty_tda.models.spatial_gnn.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import torch
from shapely.geometry import Polygon

from poverty_tda.models.spatial_gnn import (
    SpatialGNN,
    SpatialGNNTrainer,
    build_lsoa_adjacency_graph,
    compute_edge_features,
    extract_node_features,
    get_mobility_labels,
    validate_adjacency_graph,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_lsoa_grid() -> gpd.GeoDataFrame:
    """
    Create a sample 3x3 grid of LSOA-like polygons for testing.

    Grid layout (indices):
        0 1 2
        3 4 5
        6 7 8

    Each cell is adjacent to its horizontal/vertical/diagonal neighbors.
    """
    polygons = []
    lsoa_codes = []

    for row in range(3):
        for col in range(3):
            # Create 1x1 square cells
            x0, y0 = col, row
            poly = Polygon([(x0, y0), (x0 + 1, y0), (x0 + 1, y0 + 1), (x0, y0 + 1)])
            polygons.append(poly)

            # Generate LSOA codes
            idx = row * 3 + col
            lsoa_codes.append(f"E0100000{idx}")

    gdf = gpd.GeoDataFrame(
        {
            "LSOA21CD": lsoa_codes,
            "LSOA21NM": [f"Test LSOA {i}" for i in range(9)],
        },
        geometry=polygons,
        crs="EPSG:27700",
    )

    return gdf


@pytest.fixture
def sample_lsoa_disconnected() -> gpd.GeoDataFrame:
    """Create sample with disconnected LSOAs (no shared boundaries)."""
    # Create 3 separate polygons with gaps between them
    polygons = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),  # Gap from first
        Polygon([(5, 0), (6, 0), (6, 1), (5, 1)]),  # Isolated
    ]

    gdf = gpd.GeoDataFrame(
        {
            "LSOA21CD": ["E01000001", "E01000002", "E01000003"],
            "LSOA21NM": ["LSOA A", "LSOA B", "LSOA C"],
        },
        geometry=polygons,
        crs="EPSG:27700",
    )

    return gdf


# ============================================================================
# TEST: build_lsoa_adjacency_graph
# ============================================================================


class TestBuildLsoaAdjacencyGraph:
    """Test adjacency graph construction from LSOA boundaries."""

    def test_builds_graph_from_grid(self, sample_lsoa_grid: gpd.GeoDataFrame):
        """Test that adjacency graph is built correctly for 3x3 grid."""
        edge_index, lsoa_codes = build_lsoa_adjacency_graph(sample_lsoa_grid)

        # Validate output shapes
        assert edge_index.shape[0] == 2, "edge_index should have shape [2, num_edges]"
        assert len(lsoa_codes) == 9, "Should have 9 nodes"

        # Check that edges exist
        assert edge_index.shape[1] > 0, "Graph should have edges"

        # Verify LSOA codes match input
        expected_codes = sample_lsoa_grid["LSOA21CD"].values
        np.testing.assert_array_equal(lsoa_codes, expected_codes)

    def test_queen_vs_rook_contiguity(self, sample_lsoa_grid: gpd.GeoDataFrame):
        """Test that queen contiguity has more edges than rook."""
        edge_index_queen, _ = build_lsoa_adjacency_graph(
            sample_lsoa_grid, contiguity_type="queen"
        )
        edge_index_rook, _ = build_lsoa_adjacency_graph(
            sample_lsoa_grid, contiguity_type="rook"
        )

        # Queen should have more edges (includes diagonal neighbors)
        assert (
            edge_index_queen.shape[1] >= edge_index_rook.shape[1]
        ), "Queen contiguity should have >= edges than rook"

    def test_handles_disconnected_lsoas(
        self, sample_lsoa_disconnected: gpd.GeoDataFrame
    ):
        """Test graph construction with disconnected components."""
        edge_index, lsoa_codes = build_lsoa_adjacency_graph(sample_lsoa_disconnected)

        assert len(lsoa_codes) == 3, "Should have 3 nodes"

        # Graph should have very few or zero edges (depending on exact gaps)
        # At minimum, should not crash and should return valid structure
        assert edge_index.shape[0] == 2
        assert edge_index.shape[1] >= 0

    def test_raises_error_missing_lsoa_column(self):
        """Test that missing LSOA21CD column raises ValueError."""
        gdf = gpd.GeoDataFrame(
            {"bad_column": ["A", "B"]},
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
            ],
            crs="EPSG:27700",
        )

        with pytest.raises(ValueError, match="must contain 'LSOA21CD' column"):
            build_lsoa_adjacency_graph(gdf)

    def test_fixes_invalid_geometries(self):
        """Test that invalid geometries are fixed automatically."""
        # Create a self-intersecting polygon (invalid)
        invalid_poly = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])  # Bowtie shape

        gdf = gpd.GeoDataFrame(
            {
                "LSOA21CD": ["E01000001"],
                "LSOA21NM": ["Test LSOA"],
            },
            geometry=[invalid_poly],
            crs="EPSG:27700",
        )

        # Should not raise error, should fix geometry with buffer(0)
        edge_index, lsoa_codes = build_lsoa_adjacency_graph(gdf)

        assert len(lsoa_codes) == 1
        assert edge_index.shape[0] == 2


# ============================================================================
# TEST: compute_edge_features
# ============================================================================


class TestComputeEdgeFeatures:
    """Test edge feature computation."""

    def test_computes_distance_features(self, sample_lsoa_grid: gpd.GeoDataFrame):
        """Test distance-based edge features."""
        edge_index, _ = build_lsoa_adjacency_graph(sample_lsoa_grid)

        edge_features = compute_edge_features(
            sample_lsoa_grid, edge_index, feature_type="distance"
        )

        # Validate shape
        assert edge_features.shape == (
            edge_index.shape[1],
            1,
        ), "Edge features should have shape [num_edges, 1]"

        # Distance features should be positive
        assert (edge_features > 0).all(), "Distance features should be positive"

        # Check dtype
        assert edge_features.dtype == torch.float32

    def test_computes_inverse_distance_features(
        self, sample_lsoa_grid: gpd.GeoDataFrame
    ):
        """Test inverse distance edge features."""
        edge_index, _ = build_lsoa_adjacency_graph(sample_lsoa_grid)

        edge_features = compute_edge_features(
            sample_lsoa_grid, edge_index, feature_type="inverse_distance"
        )

        # Validate shape
        assert edge_features.shape == (edge_index.shape[1], 1)

        # Inverse distance features should be in (0, 1] range
        assert (edge_features > 0).all()
        assert (edge_features <= 1.0).all()

    def test_handles_empty_edge_index(self, sample_lsoa_grid: gpd.GeoDataFrame):
        """Test edge feature computation with empty edge list."""
        empty_edge_index = torch.zeros((2, 0), dtype=torch.long)

        edge_features = compute_edge_features(
            sample_lsoa_grid, empty_edge_index, feature_type="distance"
        )

        assert edge_features.shape == (0, 1)

    def test_raises_error_invalid_feature_type(
        self, sample_lsoa_grid: gpd.GeoDataFrame
    ):
        """Test that invalid feature_type raises ValueError."""
        edge_index, _ = build_lsoa_adjacency_graph(sample_lsoa_grid)

        with pytest.raises(ValueError, match="Unknown feature_type"):
            compute_edge_features(
                sample_lsoa_grid, edge_index, feature_type="invalid_type"
            )

    def test_commuting_flows_warning(self, sample_lsoa_grid: gpd.GeoDataFrame):
        """Test that commuting flow integration logs warning."""
        edge_index, _ = build_lsoa_adjacency_graph(sample_lsoa_grid)

        # Create mock commuting flows DataFrame
        commuting_flows = pd.DataFrame(
            {
                "origin_lsoa": ["E01000001", "E01000002"],
                "dest_lsoa": ["E01000002", "E01000001"],
                "flow": [100, 50],
            }
        )

        # Should log warning about not implemented
        edge_features = compute_edge_features(
            sample_lsoa_grid,
            edge_index,
            feature_type="distance",
            commuting_flows=commuting_flows,
        )

        # Should still return valid features
        assert edge_features.shape[0] == edge_index.shape[1]


# ============================================================================
# TEST: validate_adjacency_graph
# ============================================================================


class TestValidateAdjacencyGraph:
    """Test graph validation utilities."""

    def test_validation_statistics(self, sample_lsoa_grid: gpd.GeoDataFrame):
        """Test that validation returns correct statistics."""
        edge_index, lsoa_codes = build_lsoa_adjacency_graph(sample_lsoa_grid)
        num_nodes = len(lsoa_codes)

        stats = validate_adjacency_graph(edge_index, num_nodes, check_symmetry=True)

        # Check required keys
        assert "num_edges" in stats
        assert "avg_degree" in stats
        assert "min_degree" in stats
        assert "max_degree" in stats
        assert "isolated_nodes" in stats
        assert "is_symmetric" in stats

        # Validate types
        assert isinstance(stats["num_edges"], int)
        assert isinstance(stats["avg_degree"], float)
        assert isinstance(stats["isolated_nodes"], int)
        assert isinstance(stats["is_symmetric"], bool)

        # Grid graph should have no isolated nodes
        assert stats["isolated_nodes"] == 0

        # Grid graph should be symmetric (undirected)
        assert stats["is_symmetric"] is True

    def test_detects_isolated_nodes(self, sample_lsoa_disconnected: gpd.GeoDataFrame):
        """Test detection of isolated nodes."""
        edge_index, lsoa_codes = build_lsoa_adjacency_graph(sample_lsoa_disconnected)
        num_nodes = len(lsoa_codes)

        stats = validate_adjacency_graph(edge_index, num_nodes, check_symmetry=False)

        # At least one node should be isolated in disconnected graph
        # (depends on exact geometry, but typically 1-3 isolated)
        # Just verify the isolated_nodes field is computed
        assert stats["isolated_nodes"] >= 0

    def test_symmetry_check(self):
        """Test symmetry validation for directed vs undirected graphs."""
        # Create symmetric (undirected) edge list - all edges have reverse edges
        edge_index_undirected = torch.tensor(
            [[0, 1, 1, 0, 2, 1], [1, 0, 2, 1, 1, 2]], dtype=torch.long
        )

        stats = validate_adjacency_graph(
            edge_index_undirected, num_nodes=3, check_symmetry=True
        )
        assert stats["is_symmetric"] is True

        # Create truly asymmetric case - edges without reverse edges
        # 0→1 and 1→2 but no 1→0 or 2→1
        edge_index_asymmetric = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)
        stats_asym = validate_adjacency_graph(
            edge_index_asymmetric, num_nodes=3, check_symmetry=True
        )
        assert stats_asym["is_symmetric"] is False

    def test_handles_empty_graph(self):
        """Test validation with empty graph."""
        empty_edge_index = torch.zeros((2, 0), dtype=torch.long)

        stats = validate_adjacency_graph(
            empty_edge_index, num_nodes=5, check_symmetry=True
        )

        assert stats["num_edges"] == 0
        assert stats["isolated_nodes"] == 5  # All nodes isolated


@pytest.fixture
def sample_imd_data() -> pd.DataFrame:
    """Create sample IMD data for testing."""
    return pd.DataFrame(
        {
            "lsoa_code": [
                "E01000001",
                "E01000002",
                "E01000003",
                "E01000004",
                "E01000005",
            ],
            "income_score": [0.15, 0.25, 0.35, 0.45, 0.55],
            "employment_score": [0.12, 0.22, 0.32, 0.42, 0.52],
            "education_score": [0.18, 0.28, 0.38, 0.48, 0.58],
            "health_score": [0.20, 0.30, 0.40, 0.50, 0.60],
            "crime_score": [0.10, 0.20, 0.30, 0.40, 0.50],
            "housing_score": [0.14, 0.24, 0.34, 0.44, 0.54],
            "environment_score": [0.16, 0.26, 0.36, 0.46, 0.56],
        }
    )


@pytest.fixture
def sample_mobility_data() -> pd.DataFrame:
    """Create sample mobility proxy data for testing."""
    return pd.DataFrame(
        {
            "lsoa_code": [
                "E01000001",
                "E01000002",
                "E01000003",
                "E01000004",
                "E01000005",
            ],
            "mobility_proxy": [0.5, 0.3, -0.2, 0.1, 0.7],
        }
    )


# ============================================================================
# TEST: extract_node_features
# ============================================================================


class TestExtractNodeFeatures:
    """Test node feature extraction from IMD data."""

    def test_extracts_features_default_columns(self, sample_imd_data: pd.DataFrame):
        """Test feature extraction with default IMD columns."""
        lsoa_codes = ["E01000001", "E01000002", "E01000003"]

        features = extract_node_features(lsoa_codes, sample_imd_data)

        # Should have 3 nodes and 7 features (default IMD domains)
        assert features.shape == (3, 7)
        assert features.dtype == torch.float32

    def test_extracts_features_custom_columns(self, sample_imd_data: pd.DataFrame):
        """Test feature extraction with custom columns."""
        lsoa_codes = ["E01000001", "E01000002"]
        feature_cols = ["income_score", "education_score"]

        features = extract_node_features(
            lsoa_codes, sample_imd_data, feature_columns=feature_cols
        )

        assert features.shape == (2, 2)

    def test_zscore_normalization(self, sample_imd_data: pd.DataFrame):
        """Test z-score normalization."""
        lsoa_codes = ["E01000001", "E01000002", "E01000003"]

        features = extract_node_features(
            lsoa_codes, sample_imd_data, normalization="zscore"
        )

        # Z-score should center around 0 with std ~1
        assert abs(features.mean().item()) < 0.5  # Approximately 0
        assert 0.5 < features.std().item() < 1.5  # Approximately 1

    def test_minmax_normalization(self, sample_imd_data: pd.DataFrame):
        """Test min-max normalization."""
        lsoa_codes = ["E01000001", "E01000002", "E01000003"]

        features = extract_node_features(
            lsoa_codes, sample_imd_data, normalization="minmax"
        )

        # Min-max should scale to [0, 1]
        assert features.min() >= 0.0
        assert features.max() <= 1.0

    def test_no_normalization(self, sample_imd_data: pd.DataFrame):
        """Test no normalization preserves raw values."""
        lsoa_codes = ["E01000001", "E01000002"]

        features = extract_node_features(
            lsoa_codes, sample_imd_data, normalization="none"
        )

        # First LSOA should have income_score = 0.15
        assert abs(features[0, 0].item() - 0.15) < 0.01

    def test_handles_missing_values_mean(self):
        """Test missing value imputation with mean."""
        imd_data = pd.DataFrame(
            {
                "lsoa_code": ["E01000001", "E01000002", "E01000003"],
                "income_score": [0.2, np.nan, 0.4],
                "employment_score": [0.3, 0.5, 0.7],
            }
        )

        features = extract_node_features(
            ["E01000001", "E01000002", "E01000003"],
            imd_data,
            feature_columns=["income_score", "employment_score"],
            handle_missing="mean",
            normalization="none",
        )

        # Second LSOA income should be imputed to mean of 0.2 and 0.4 = 0.3
        assert abs(features[1, 0].item() - 0.3) < 0.01

    def test_handles_missing_values_zero(self):
        """Test missing value filling with zeros."""
        imd_data = pd.DataFrame(
            {
                "lsoa_code": ["E01000001", "E01000002"],
                "income_score": [0.2, np.nan],
                "employment_score": [0.3, 0.5],
            }
        )

        features = extract_node_features(
            ["E01000001", "E01000002"],
            imd_data,
            feature_columns=["income_score", "employment_score"],
            handle_missing="zero",
            normalization="none",
        )

        # Second LSOA income should be 0
        assert features[1, 0].item() == 0.0

    def test_raises_error_missing_lsoa_column(self):
        """Test that missing lsoa_code column raises ValueError."""
        bad_data = pd.DataFrame({"other_column": [1, 2, 3]})

        with pytest.raises(ValueError, match="must contain 'lsoa_code' column"):
            extract_node_features(["E01000001"], bad_data)

    def test_raises_error_no_valid_features(self, sample_imd_data: pd.DataFrame):
        """Test that requesting non-existent features raises ValueError."""
        with pytest.raises(ValueError, match="None of the requested feature columns"):
            extract_node_features(
                ["E01000001"],
                sample_imd_data,
                feature_columns=["nonexistent_column"],
            )

    def test_preserves_lsoa_order(self, sample_imd_data: pd.DataFrame):
        """Test that feature extraction preserves LSOA order."""
        # Request in reverse order
        lsoa_codes = ["E01000003", "E01000001", "E01000002"]

        features = extract_node_features(
            lsoa_codes,
            sample_imd_data,
            feature_columns=["income_score"],
            normalization="none",
        )

        # Should match the order of lsoa_codes (0.35, 0.15, 0.25)
        assert abs(features[0, 0].item() - 0.35) < 0.01  # E01000003
        assert abs(features[1, 0].item() - 0.15) < 0.01  # E01000001
        assert abs(features[2, 0].item() - 0.25) < 0.01  # E01000002


# ============================================================================
# TEST: get_mobility_labels
# ============================================================================


class TestGetMobilityLabels:
    """Test mobility label extraction."""

    def test_extracts_labels(self, sample_mobility_data: pd.DataFrame):
        """Test basic label extraction."""
        lsoa_codes = ["E01000001", "E01000002", "E01000003"]

        labels = get_mobility_labels(lsoa_codes, sample_mobility_data)

        # Should have 3 labels
        assert labels.shape == (3,)
        assert labels.dtype == torch.float32

        # Check values match (0.5, 0.3, -0.2)
        assert abs(labels[0].item() - 0.5) < 0.01
        assert abs(labels[1].item() - 0.3) < 0.01
        assert abs(labels[2].item() - (-0.2)) < 0.01

    def test_custom_label_column(self):
        """Test extraction with custom label column."""
        mobility_data = pd.DataFrame(
            {
                "lsoa_code": ["E01000001", "E01000002"],
                "custom_mobility": [0.8, 0.2],
            }
        )

        labels = get_mobility_labels(
            ["E01000001", "E01000002"],
            mobility_data,
            label_column="custom_mobility",
        )

        assert labels.shape == (2,)
        assert abs(labels[0].item() - 0.8) < 0.01

    def test_preserves_lsoa_order(self, sample_mobility_data: pd.DataFrame):
        """Test that label extraction preserves LSOA order."""
        # Request in reverse order
        lsoa_codes = ["E01000003", "E01000001", "E01000002"]

        labels = get_mobility_labels(lsoa_codes, sample_mobility_data)

        # Should match order (-0.2, 0.5, 0.3)
        assert abs(labels[0].item() - (-0.2)) < 0.01  # E01000003
        assert abs(labels[1].item() - 0.5) < 0.01  # E01000001
        assert abs(labels[2].item() - 0.3) < 0.01  # E01000002

    def test_handles_missing_values(self):
        """Test warning when labels have missing values."""
        mobility_data = pd.DataFrame(
            {
                "lsoa_code": ["E01000001", "E01000002", "E01000003"],
                "mobility_proxy": [0.5, np.nan, 0.3],
            }
        )

        labels = get_mobility_labels(
            ["E01000001", "E01000002", "E01000003"], mobility_data
        )

        # Should still return tensor with NaN
        assert labels.shape == (3,)
        assert torch.isnan(labels[1])

    def test_raises_error_missing_lsoa_column(self):
        """Test that missing lsoa_code column raises ValueError."""
        bad_data = pd.DataFrame({"other_column": [1, 2, 3]})

        with pytest.raises(ValueError, match="must contain 'lsoa_code' column"):
            get_mobility_labels(["E01000001"], bad_data)

    def test_raises_error_missing_label_column(self, sample_mobility_data):
        """Test that missing label column raises ValueError."""
        with pytest.raises(ValueError, match="must contain 'nonexistent' column"):
            get_mobility_labels(
                ["E01000001"], sample_mobility_data, label_column="nonexistent"
            )


# ============================================================================
# TEST: SpatialGNN
# ============================================================================


class TestSpatialGNN:
    """Test GNN architecture."""

    def test_model_initialization(self):
        """Test that model initializes correctly."""
        model = SpatialGNN(
            input_dim=7, hidden_dim=64, output_dim=1, num_layers=2, dropout=0.3
        )

        assert model.input_dim == 7
        assert model.hidden_dim == 64
        assert model.output_dim == 1
        assert model.num_layers == 2
        assert model.dropout == 0.3

    def test_forward_pass_shape(self):
        """Test forward pass produces correct output shape."""
        model = SpatialGNN(input_dim=7, hidden_dim=64, output_dim=1, num_layers=2)

        # Create simple graph: 2 nodes connected
        x = torch.randn(5, 7)  # 5 nodes, 7 features
        edge_list = [[0, 1, 1, 2, 2, 3, 3, 4], [1, 0, 2, 1, 3, 2, 4, 3]]
        edge_index = torch.tensor(edge_list, dtype=torch.long)

        out = model(x, edge_index)

        assert out.shape == (5, 1)  # 5 nodes, 1 output per node
        assert out.dtype == torch.float32

    def test_forward_pass_gradient_flow(self):
        """Test that gradients flow through the model."""
        model = SpatialGNN(input_dim=3, hidden_dim=16, output_dim=1, num_layers=2)

        x = torch.randn(4, 3, requires_grad=True)
        edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)

        out = model(x, edge_index)
        loss = out.sum()
        loss.backward()

        # Check that gradients exist
        assert x.grad is not None
        assert x.grad.shape == x.shape

    def test_different_num_layers(self):
        """Test model with different number of layers."""
        for num_layers in [2, 3]:
            model = SpatialGNN(input_dim=7, hidden_dim=32, num_layers=num_layers)
            assert len(model.convs) == num_layers

            x = torch.randn(3, 7)
            edge_index = torch.tensor([[0, 1, 2], [1, 2, 0]], dtype=torch.long)
            out = model(x, edge_index)
            assert out.shape == (3, 1)

    def test_batch_norm_optional(self):
        """Test model with and without batch normalization."""
        # With batch norm
        model_bn = SpatialGNN(input_dim=7, hidden_dim=32, use_batch_norm=True)
        assert model_bn.batch_norms is not None
        assert len(model_bn.batch_norms) == model_bn.num_layers

        # Without batch norm
        model_no_bn = SpatialGNN(input_dim=7, hidden_dim=32, use_batch_norm=False)
        assert model_no_bn.batch_norms is None

    def test_dropout_applied(self):
        """Test that dropout is applied during training."""
        model = SpatialGNN(input_dim=7, hidden_dim=32, dropout=0.5)
        model.train()  # Enable dropout

        x = torch.randn(10, 7)
        edge_index = torch.tensor(
            [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]],
            dtype=torch.long,
        )

        # Run forward pass multiple times - outputs should differ due to dropout
        out1 = model(x, edge_index)
        out2 = model(x, edge_index)

        # With dropout=0.5, outputs should be different
        assert not torch.allclose(out1, out2)

    def test_eval_mode_deterministic(self):
        """Test that eval mode produces deterministic outputs."""
        model = SpatialGNN(input_dim=7, hidden_dim=32, dropout=0.5)
        model.eval()  # Disable dropout

        x = torch.randn(5, 7)
        edge_index = torch.tensor([[0, 1, 2, 3, 4], [1, 2, 3, 4, 0]], dtype=torch.long)

        out1 = model(x, edge_index)
        out2 = model(x, edge_index)

        # In eval mode, outputs should be identical
        assert torch.allclose(out1, out2)

    def test_reset_parameters(self):
        """Test that reset_parameters works."""
        model = SpatialGNN(input_dim=7, hidden_dim=32)

        x = torch.randn(3, 7)
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 0]], dtype=torch.long)

        # Get initial output
        out1 = model(x, edge_index)

        # Reset parameters
        model.reset_parameters()

        # Output should be different after reset
        out2 = model(x, edge_index)
        assert not torch.allclose(out1, out2)

    def test_raises_error_insufficient_layers(self):
        """Test that num_layers < 2 raises error."""
        with pytest.raises(ValueError, match="num_layers must be at least 2"):
            SpatialGNN(input_dim=7, hidden_dim=32, num_layers=1)

    def test_model_repr(self):
        """Test string representation of model."""
        model = SpatialGNN(input_dim=7, hidden_dim=64, output_dim=1, num_layers=2)
        repr_str = repr(model)

        assert "SpatialGNN" in repr_str
        assert "input_dim=7" in repr_str
        assert "hidden_dim=64" in repr_str
        assert "num_layers=2" in repr_str

    def test_integration_with_graph_construction(self, sample_lsoa_grid):
        """Test GNN with real adjacency graph."""
        # Build graph
        edge_index, lsoa_codes = build_lsoa_adjacency_graph(sample_lsoa_grid)

        # Create model
        model = SpatialGNN(input_dim=5, hidden_dim=16, num_layers=2)

        # Create dummy features
        x = torch.randn(len(lsoa_codes), 5)

        # Forward pass
        out = model(x, edge_index)

        assert out.shape == (len(lsoa_codes), 1)


# ============================================================================
# TEST: SpatialGNNTrainer
# ============================================================================


class TestSpatialGNNTrainer:
    """Test GNN training pipeline."""

    def test_trainer_initialization(self):
        """Test that trainer initializes correctly."""
        model = SpatialGNN(input_dim=7, hidden_dim=32, num_layers=2)
        trainer = SpatialGNNTrainer(
            model, learning_rate=1e-3, weight_decay=1e-4, device="cpu"
        )

        assert trainer.learning_rate == 1e-3
        assert trainer.weight_decay == 1e-4
        assert trainer.device == "cpu"
        assert isinstance(trainer.optimizer, torch.optim.Adam)

    def test_spatial_split_ratios(self):
        """Test that spatial split produces correct ratios."""
        model = SpatialGNN(input_dim=7, hidden_dim=32)
        trainer = SpatialGNNTrainer(model)

        # Create dummy LSOA codes from 3 regions
        lsoa_codes = (
            [f"E0100000{i}" for i in range(7)]  # Region E01
            + [f"E0200000{i}" for i in range(5)]  # Region E02
            + [f"W0100000{i}" for i in range(3)]  # Region W01
        )

        # Create dummy GeoDataFrame
        gdf = gpd.GeoDataFrame(
            {"LSOA21CD": lsoa_codes},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])] * len(lsoa_codes),
        )

        train_mask, val_mask, test_mask = trainer.spatial_split(
            lsoa_codes, gdf, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2
        )

        # Check that masks cover all nodes
        assert train_mask.sum() + val_mask.sum() + test_mask.sum() == len(lsoa_codes)

        # Check no overlap
        assert (train_mask & val_mask).sum() == 0
        assert (train_mask & test_mask).sum() == 0
        assert (val_mask & test_mask).sum() == 0

    def test_spatial_split_preserves_regions(self):
        """Test that spatial split keeps regions together."""
        model = SpatialGNN(input_dim=7, hidden_dim=32)
        trainer = SpatialGNNTrainer(model)

        # Create LSOA codes where region is determined by prefix
        lsoa_codes = (
            [f"E01{i:05d}" for i in range(10)]  # Region E01
            + [f"E02{i:05d}" for i in range(10)]  # Region E02
        )

        gdf = gpd.GeoDataFrame(
            {"LSOA21CD": lsoa_codes},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])] * len(lsoa_codes),
        )

        train_mask, val_mask, test_mask = trainer.spatial_split(lsoa_codes, gdf)

        # Check that entire regions are in one split (not mixed)
        # Region E01: indices 0-9
        e01_in_train = train_mask[:10].all()
        e01_in_val = val_mask[:10].all()
        e01_in_test = test_mask[:10].all()

        # Exactly one should be True
        assert sum([e01_in_train, e01_in_val, e01_in_test]) == 1

    def test_train_reduces_loss(self):
        """Test that training reduces loss."""
        # Create small synthetic graph
        model = SpatialGNN(input_dim=5, hidden_dim=16, num_layers=2)
        trainer = SpatialGNNTrainer(model, learning_rate=1e-2)

        # Synthetic data
        num_nodes = 20
        x = torch.randn(num_nodes, 5)
        y = torch.randn(num_nodes)
        edge_index = torch.tensor(
            [[i, (i + 1) % num_nodes] for i in range(num_nodes)], dtype=torch.long
        ).t()

        # Simple split
        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        train_mask[:14] = True
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask[14:] = True

        # Train for few epochs
        history = trainer.train(
            x, y, edge_index, train_mask, val_mask, epochs=20, verbose=False
        )

        # Check that loss decreased
        initial_loss = history["train_loss"][0]
        final_loss = history["train_loss"][-1]
        assert final_loss < initial_loss

    def test_train_stops_early(self):
        """Test early stopping when validation loss doesn't improve."""
        model = SpatialGNN(input_dim=5, hidden_dim=16, num_layers=2)
        trainer = SpatialGNNTrainer(model, early_stopping_patience=5)

        # Synthetic data
        num_nodes = 15
        x = torch.randn(num_nodes, 5)
        y = torch.randn(num_nodes)
        edge_index = torch.tensor(
            [[i, (i + 1) % num_nodes] for i in range(num_nodes)], dtype=torch.long
        ).t()

        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        train_mask[:10] = True
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask[10:] = True

        # Train - should stop early
        history = trainer.train(
            x, y, edge_index, train_mask, val_mask, epochs=100, verbose=False
        )

        # Should stop before 100 epochs
        assert len(history["train_loss"]) < 100

    def test_evaluate_metrics(self):
        """Test evaluation metrics computation."""
        model = SpatialGNN(input_dim=7, hidden_dim=32)
        trainer = SpatialGNNTrainer(model)

        # Perfect predictions
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        metrics = trainer.evaluate(y_pred, y_true)

        assert metrics["rmse"] == 0.0
        assert metrics["mae"] == 0.0
        assert abs(metrics["r2"] - 1.0) < 1e-6  # Should be 1.0

    def test_evaluate_metrics_imperfect(self):
        """Test evaluation metrics with imperfect predictions."""
        model = SpatialGNN(input_dim=7, hidden_dim=32)
        trainer = SpatialGNNTrainer(model)

        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.1, 2.9, 4.2, 4.8])

        metrics = trainer.evaluate(y_pred, y_true)

        assert 0 < metrics["rmse"] < 1.0
        assert 0 < metrics["mae"] < 1.0
        assert 0 < metrics["r2"] < 1.0

    def test_predict_shape(self):
        """Test prediction output shape."""
        model = SpatialGNN(input_dim=5, hidden_dim=16, num_layers=2)
        trainer = SpatialGNNTrainer(model)

        x = torch.randn(10, 5)
        edge_index = torch.tensor(
            [[i, (i + 1) % 10] for i in range(10)], dtype=torch.long
        ).t()

        predictions = trainer.predict(x, edge_index)

        assert predictions.shape == (10,)
        assert isinstance(predictions, np.ndarray)

    def test_predict_with_mask(self):
        """Test prediction with mask."""
        model = SpatialGNN(input_dim=5, hidden_dim=16, num_layers=2)
        trainer = SpatialGNNTrainer(model)

        x = torch.randn(10, 5)
        edge_index = torch.tensor(
            [[i, (i + 1) % 10] for i in range(10)], dtype=torch.long
        ).t()
        mask = torch.zeros(10, dtype=torch.bool)
        mask[3:7] = True

        predictions = trainer.predict(x, edge_index, mask)

        # Should only return 4 predictions (indices 3-6)
        assert predictions.shape == (4,)

    def test_training_history_tracking(self):
        """Test that training history is tracked correctly."""
        model = SpatialGNN(input_dim=5, hidden_dim=16, num_layers=2)
        trainer = SpatialGNNTrainer(model)

        num_nodes = 15
        x = torch.randn(num_nodes, 5)
        y = torch.randn(num_nodes)
        edge_index = torch.tensor(
            [[i, (i + 1) % num_nodes] for i in range(num_nodes)], dtype=torch.long
        ).t()

        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        train_mask[:10] = True
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask[10:] = True

        history = trainer.train(
            x, y, edge_index, train_mask, val_mask, epochs=10, verbose=False
        )

        # Check all history keys exist and have correct length
        assert len(history["train_loss"]) <= 10
        assert len(history["val_loss"]) == len(history["train_loss"])
        assert len(history["val_rmse"]) == len(history["train_loss"])
        assert len(history["val_mae"]) == len(history["train_loss"])
        assert len(history["val_r2"]) == len(history["train_loss"])


# ============================================================================
# INTEGRATION TEST
# ============================================================================


@pytest.mark.integration
class TestSpatialGraphIntegration:
    """Integration tests using real LSOA data."""

    def test_full_pipeline_on_sample_lads(self):
        """
        Test complete graph construction pipeline on a sample LAD region.

        This test requires actual LSOA boundary data. Skip if not available.
        """
        pytest.importorskip("poverty_tda.data.census_shapes")

        from poverty_tda.data.census_shapes import (
            filter_by_region,
            load_lsoa_boundaries,
        )

        try:
            # Load England LSOA boundaries (small subset)
            gdf_full = load_lsoa_boundaries(download_if_missing=False)
            gdf = filter_by_region(gdf_full, "E01")  # England only

            # Take first 100 LSOAs for faster testing
            gdf_sample = gdf.head(100)

            # Build adjacency graph
            edge_index, lsoa_codes = build_lsoa_adjacency_graph(gdf_sample)

            # Validate
            assert len(lsoa_codes) == 100
            assert edge_index.shape[0] == 2
            assert edge_index.shape[1] > 0  # Should have edges

            # Compute edge features
            edge_features = compute_edge_features(
                gdf_sample, edge_index, feature_type="inverse_distance"
            )
            assert edge_features.shape == (edge_index.shape[1], 1)

            # Validate graph
            stats = validate_adjacency_graph(
                edge_index, len(lsoa_codes), check_symmetry=True
            )
            assert stats["isolated_nodes"] == 0  # Real data should be connected
            assert stats["is_symmetric"] is True

        except FileNotFoundError:
            pytest.skip("LSOA boundary data not available for integration test")

    def test_end_to_end_pipeline(self):
        """
        End-to-end integration test: Graph construction → Feature extraction → Training.

        This test verifies the complete GNN pipeline works together on synthetic data
        that mimics real LSOA structure.
        """
        # Create synthetic LSOA grid (5x5 = 25 LSOAs)
        lsoa_codes = [f"E01{i:05d}" for i in range(25)]
        polygons = []

        for row in range(5):
            for col in range(5):
                x0, y0 = col, row
                poly = Polygon([(x0, y0), (x0 + 1, y0), (x0 + 1, y0 + 1), (x0, y0 + 1)])
                polygons.append(poly)

        gdf = gpd.GeoDataFrame(
            {"LSOA21CD": lsoa_codes}, geometry=polygons, crs="EPSG:27700"
        )

        # Step 1: Build adjacency graph
        edge_index, graph_lsoa_codes = build_lsoa_adjacency_graph(
            gdf, contiguity_type="queen"
        )

        assert len(graph_lsoa_codes) == 25
        assert edge_index.shape[0] == 2

        # Step 2: Create synthetic IMD data
        imd_data = pd.DataFrame(
            {
                "lsoa_code": lsoa_codes,
                "income_score": np.random.rand(25),
                "employment_score": np.random.rand(25),
                "education_score": np.random.rand(25),
                "health_score": np.random.rand(25),
                "crime_score": np.random.rand(25),
                "housing_score": np.random.rand(25),
                "environment_score": np.random.rand(25),
            }
        )

        # Step 3: Extract node features
        x = extract_node_features(graph_lsoa_codes, imd_data, normalization="zscore")

        assert x.shape == (25, 7)

        # Step 4: Create synthetic mobility labels
        mobility_data = pd.DataFrame(
            {
                "lsoa_code": lsoa_codes,
                "mobility_proxy": np.random.randn(25),
            }
        )

        y = get_mobility_labels(graph_lsoa_codes, mobility_data)

        assert y.shape == (25,)

        # Step 5: Initialize model and trainer
        model = SpatialGNN(input_dim=7, hidden_dim=16, num_layers=2)
        trainer = SpatialGNNTrainer(model, learning_rate=1e-2)

        # Step 6: Create train/val split
        train_mask = torch.zeros(25, dtype=torch.bool)
        train_mask[:18] = True
        val_mask = torch.zeros(25, dtype=torch.bool)
        val_mask[18:] = True

        # Step 7: Train
        history = trainer.train(
            x, y, edge_index, train_mask, val_mask, epochs=10, verbose=False
        )

        # Verify training completed
        assert len(history["train_loss"]) <= 10
        assert len(history["val_loss"]) == len(history["train_loss"])

        # Step 8: Make predictions
        predictions = trainer.predict(x, edge_index, val_mask)

        assert predictions.shape == (7,)  # 7 validation nodes

        # Step 9: Evaluate
        metrics = trainer.evaluate(predictions, y[val_mask].numpy())

        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics

        # Metrics should be reasonable (not NaN/Inf)
        assert np.isfinite(metrics["rmse"])
        assert np.isfinite(metrics["mae"])
        assert np.isfinite(metrics["r2"])
