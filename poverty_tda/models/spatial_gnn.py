"""
Graph Neural Network for LSOA spatial poverty analysis.

This module implements a Graph Neural Network (GNN) architecture that models
Lower Layer Super Output Areas (LSOAs) as nodes in a spatial graph, with edges
representing geographic adjacency (queen contiguity). The GNN learns to predict
economic mobility by aggregating information from spatially-connected neighborhoods.

Key Components:
- Adjacency graph construction from LSOA polygon boundaries
- Node feature extraction from IMD domain scores
- GNN architecture (GraphSAGE) for spatial learning
- Training pipeline with spatial train/val/test splits

Architecture:
    GraphSAGE with 2-3 message passing layers
    - Input: IMD domain features (7 domains) per LSOA
    - Output: Mobility proxy prediction (regression)
    - Aggregation: Mean pooling over spatial neighborhoods

Data Sources:
    - LSOA boundaries from ONS Open Geography Portal
    - IMD 2019 domain scores for node features
    - Mobility proxy (computed from IMD change) as target

Dependencies:
    - PyTorch for neural network implementation
    - PyTorch Geometric for GNN layers
    - libpysal for spatial adjacency computation
    - GeoPandas for spatial data handling
"""

from __future__ import annotations

import logging
from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd
import torch
from libpysal.weights import Queen

logger = logging.getLogger(__name__)

# Optional: Check for PyTorch Geometric availability
try:
    from torch_geometric.nn import SAGEConv

    HAS_TORCH_GEOMETRIC = True
except ImportError:
    HAS_TORCH_GEOMETRIC = False
    logger.warning(
        "PyTorch Geometric not installed. GNN training will not be available. "
        "Install with: pip install torch-geometric torch-scatter torch-sparse"
    )


def build_lsoa_adjacency_graph(
    gdf: gpd.GeoDataFrame,
    contiguity_type: Literal["queen", "rook"] = "queen",
) -> tuple[torch.Tensor, np.ndarray]:
    """
    Build adjacency graph from LSOA geometries using spatial contiguity.

    Constructs a spatial graph where nodes are LSOAs and edges exist between
    spatially contiguous areas. Uses queen contiguity (shared boundary or vertex)
    by default, which captures both direct neighbors and corner connections.

    Args:
        gdf: GeoDataFrame with LSOA boundaries. Must have Polygon/MultiPolygon
            geometries and LSOA21CD column for identification.
        contiguity_type: Type of spatial contiguity:
            - "queen": Shared boundary or vertex (recommended)
            - "rook": Shared boundary only (stricter)

    Returns:
        Tuple of (edge_index, lsoa_codes):
            - edge_index: Tensor of shape [2, num_edges] in PyTorch Geometric format
                where edge_index[0] = source nodes, edge_index[1] = target nodes
            - lsoa_codes: Array of LSOA codes corresponding to node indices

    Raises:
        ValueError: If gdf lacks required columns or has invalid geometries.
        ImportError: If libpysal is not installed.

    Example:
        >>> from poverty_tda.data.census_shapes import load_lsoa_boundaries
        >>> gdf = load_lsoa_boundaries()
        >>> edge_index, lsoa_codes = build_lsoa_adjacency_graph(gdf)
        >>> print(f"Graph: {len(lsoa_codes)} nodes, {edge_index.shape[1]} edges")
    """
    # Validate input
    if "LSOA21CD" not in gdf.columns:
        raise ValueError("GeoDataFrame must contain 'LSOA21CD' column")

    if not all(gdf.geometry.is_valid):
        logger.warning("Some geometries are invalid. Attempting to fix...")
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.buffer(0)

    logger.info(f"Building {contiguity_type} contiguity graph for {len(gdf)} LSOAs")

    # Extract LSOA codes as node identifiers
    lsoa_codes = gdf["LSOA21CD"].values

    # Build spatial weights matrix using libpysal
    # Queen contiguity: neighbors share boundary or vertex
    # Rook contiguity: neighbors share only boundary (stricter)
    if contiguity_type == "queen":
        w = Queen.from_dataframe(gdf, use_index=False, silence_warnings=True)
    else:
        from libpysal.weights import Rook

        w = Rook.from_dataframe(gdf, use_index=False, silence_warnings=True)

    # Convert libpysal weights to edge list format
    edge_list = []
    for i in range(len(gdf)):
        neighbors = w.neighbors[i]
        for j in neighbors:
            # Add edge in both directions for undirected graph
            edge_list.append([i, j])

    # Convert to PyTorch Geometric format: [2, num_edges]
    if len(edge_list) == 0:
        logger.warning("No edges found in adjacency graph!")
        edge_index = torch.zeros((2, 0), dtype=torch.long)
    else:
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()

    logger.info(
        f"Built adjacency graph: {len(lsoa_codes)} nodes, {edge_index.shape[1]} edges"
    )

    # Log connectivity statistics
    if edge_index.shape[1] > 0:
        avg_degree = edge_index.shape[1] / len(lsoa_codes)
        logger.info(f"Average node degree: {avg_degree:.2f}")

    return edge_index, lsoa_codes


def compute_edge_features(
    gdf: gpd.GeoDataFrame,
    edge_index: torch.Tensor,
    feature_type: Literal["distance", "inverse_distance"] = "inverse_distance",
    commuting_flows: pd.DataFrame | None = None,
) -> torch.Tensor:
    """
    Compute edge features for the spatial graph.

    Calculates edge attributes that capture the strength of spatial relationships
    between LSOAs. By default, uses inverse distance as a proximity measure
    (closer neighbors have stronger connections).

    Args:
        gdf: GeoDataFrame with LSOA boundaries.
        edge_index: Tensor of shape [2, num_edges] with node adjacency.
        feature_type: Type of edge feature to compute:
            - "distance": Geographic distance between centroids (meters)
            - "inverse_distance": 1 / (distance + 1), emphasizes proximity
        commuting_flows: Optional DataFrame with commuting flow data from
            Census WU03UK table (LSOA origin-destination matrix). If provided,
            uses commuting volume as edge weight. Columns: origin_lsoa, dest_lsoa, flow

    Returns:
        Tensor of shape [num_edges, 1] with edge features.

    Example:
        >>> edge_index, lsoa_codes = build_lsoa_adjacency_graph(gdf)
        >>> edge_features = compute_edge_features(gdf, edge_index)
        >>> print(edge_features.shape)
        torch.Size([num_edges, 1])
    """
    num_edges = edge_index.shape[1]

    if num_edges == 0:
        logger.warning("No edges to compute features for")
        return torch.zeros((0, 1), dtype=torch.float32)

    # Compute centroids for distance calculation
    centroids = gdf.geometry.centroid
    centroid_coords = np.array([[c.x, c.y] for c in centroids])

    # Extract source and target node indices
    src_idx = edge_index[0].numpy()
    dst_idx = edge_index[1].numpy()

    # Compute distances between connected nodes
    distances = np.linalg.norm(
        centroid_coords[src_idx] - centroid_coords[dst_idx], axis=1
    )

    if feature_type == "distance":
        edge_features = distances.reshape(-1, 1)
    elif feature_type == "inverse_distance":
        # Inverse distance: closer neighbors have higher weight
        # Add 1 to avoid division by zero (some centroids may be identical)
        edge_features = (1.0 / (distances + 1.0)).reshape(-1, 1)
    else:
        raise ValueError(
            f"Unknown feature_type: {feature_type}. "
            "Use 'distance' or 'inverse_distance'"
        )

    # Optional: Incorporate commuting flow data if available
    if commuting_flows is not None:
        logger.info("Incorporating commuting flow data into edge features")
        # TODO: Implement commuting flow integration when Census OD data is available
        # This would merge origin-destination pairs from commuting_flows DataFrame
        # with edge_index to augment edge features
        logger.warning("Commuting flow integration not yet implemented")

    edge_features_tensor = torch.tensor(edge_features, dtype=torch.float32)

    logger.info(
        f"Computed {feature_type} edge features: "
        f"shape {edge_features_tensor.shape}, "
        f"mean={edge_features_tensor.mean():.4f}, "
        f"std={edge_features_tensor.std():.4f}"
    )

    return edge_features_tensor


def validate_adjacency_graph(
    edge_index: torch.Tensor,
    num_nodes: int,
    check_symmetry: bool = True,
) -> dict[str, float | int]:
    """
    Validate adjacency graph properties.

    Performs sanity checks on the constructed adjacency graph to ensure
    correctness and identify potential issues.

    Args:
        edge_index: Tensor of shape [2, num_edges] with node adjacency.
        num_nodes: Total number of nodes in the graph.
        check_symmetry: If True, verify that graph is undirected (symmetric).

    Returns:
        Dictionary with validation statistics:
            - num_edges: Total edge count
            - avg_degree: Average node degree
            - min_degree: Minimum node degree
            - max_degree: Maximum node degree
            - isolated_nodes: Count of nodes with zero degree
            - is_symmetric: Whether graph is undirected (if check_symmetry=True)

    Example:
        >>> stats = validate_adjacency_graph(edge_index, len(lsoa_codes))
        >>> print(f"Isolated nodes: {stats['isolated_nodes']}")
    """
    num_edges = edge_index.shape[1]

    # Compute node degrees
    unique_nodes, degree_counts = torch.unique(edge_index[0], return_counts=True)
    degrees = torch.zeros(num_nodes, dtype=torch.long)
    degrees[unique_nodes] = degree_counts

    stats = {
        "num_edges": num_edges,
        "avg_degree": float(degree_counts.float().mean()),
        "min_degree": int(degrees.min()),
        "max_degree": int(degrees.max()),
        "isolated_nodes": int((degrees == 0).sum()),
    }

    # Check for isolated nodes (should be rare in spatial graphs)
    if stats["isolated_nodes"] > 0:
        logger.warning(
            f"Found {stats['isolated_nodes']} isolated nodes (no neighbors). "
            "This is unusual for spatial contiguity graphs."
        )

    # Check graph symmetry (should be symmetric for undirected spatial graphs)
    if check_symmetry and num_edges > 0:
        # Create reverse edges and check if they all exist
        reverse_edges = torch.stack([edge_index[1], edge_index[0]], dim=0)

        # Convert to set for efficient lookup
        edge_set = set(
            zip(edge_index[0].tolist(), edge_index[1].tolist(), strict=False)
        )
        reverse_set = set(
            zip(reverse_edges[0].tolist(), reverse_edges[1].tolist(), strict=False)
        )

        is_symmetric = edge_set == reverse_set
        stats["is_symmetric"] = is_symmetric

        if not is_symmetric:
            logger.warning(
                "Adjacency graph is not symmetric! "
                "Expected undirected graph for spatial contiguity."
            )

    logger.info(f"Graph validation: {stats}")
    return stats


def extract_node_features(
    lsoa_codes: np.ndarray | list,
    imd_data: pd.DataFrame,
    feature_columns: list[str] | None = None,
    normalization: Literal["zscore", "minmax", "none"] = "zscore",
    handle_missing: Literal["mean", "median", "drop", "zero"] = "mean",
) -> torch.Tensor:
    """
    Extract node features from IMD domain scores.

    Extracts IMD domain scores for each LSOA as node features for the GNN.
    By default uses all 7 IMD domain scores: income, employment, education,
    health, crime, housing, and environment.

    Args:
        lsoa_codes: Array or list of LSOA codes (e.g., ["E01000001", "E01000002"]).
        imd_data: DataFrame with IMD data. Must contain 'lsoa_code' column
            and domain score columns.
        feature_columns: List of column names to use as features. If None,
            uses default IMD domain scores:
            ['income_score', 'employment_score', 'education_score',
             'health_score', 'crime_score', 'housing_score', 'environment_score']
        normalization: Feature normalization method:
            - "zscore": z-score normalization (mean=0, std=1)
            - "minmax": min-max scaling to [0, 1]
            - "none": no normalization
        handle_missing: How to handle missing values:
            - "mean": impute with column mean
            - "median": impute with column median
            - "drop": drop LSOAs with missing values (not recommended)
            - "zero": fill with zeros

    Returns:
        Tensor of shape [num_nodes, num_features] with node features.

    Raises:
        ValueError: If required columns are missing or no valid features found.

    Example:
        >>> from poverty_tda.data.opportunity_atlas import load_imd_data
        >>> imd_data = load_imd_data()
        >>> lsoa_codes = ["E01000001", "E01000002", "E01000003"]
        >>> features = extract_node_features(lsoa_codes, imd_data)
        >>> print(features.shape)
        torch.Size([3, 7])
    """
    if "lsoa_code" not in imd_data.columns:
        raise ValueError("imd_data must contain 'lsoa_code' column")

    # Default IMD domain score columns
    if feature_columns is None:
        feature_columns = [
            "income_score",
            "employment_score",
            "education_score",
            "health_score",
            "crime_score",
            "housing_score",
            "environment_score",
        ]

    # Check which feature columns exist in the data
    available_features = [col for col in feature_columns if col in imd_data.columns]

    if len(available_features) == 0:
        raise ValueError(
            f"None of the requested feature columns found in imd_data. "
            f"Requested: {feature_columns}, Available: {list(imd_data.columns)}"
        )

    if len(available_features) < len(feature_columns):
        missing = set(feature_columns) - set(available_features)
        logger.warning(
            f"Some feature columns not found in imd_data: {missing}. "
            f"Using {len(available_features)} available features."
        )

    # Filter IMD data to requested LSOAs
    lsoa_codes_array = np.array(lsoa_codes)
    imd_filtered = imd_data[imd_data["lsoa_code"].isin(lsoa_codes_array)].copy()

    # Ensure correct order matching lsoa_codes
    imd_filtered["_order"] = imd_filtered["lsoa_code"].apply(
        lambda x: np.where(lsoa_codes_array == x)[0][0] if x in lsoa_codes_array else -1
    )
    imd_filtered = imd_filtered.sort_values("_order")

    # Extract feature matrix
    feature_matrix = imd_filtered[available_features].values

    # Handle missing values
    if np.any(np.isnan(feature_matrix)):
        logger.warning(f"Found {np.isnan(feature_matrix).sum()} missing values")

        if handle_missing == "mean":
            col_means = np.nanmean(feature_matrix, axis=0)
            for col_idx in range(feature_matrix.shape[1]):
                nan_mask = np.isnan(feature_matrix[:, col_idx])
                feature_matrix[nan_mask, col_idx] = col_means[col_idx]
        elif handle_missing == "median":
            col_medians = np.nanmedian(feature_matrix, axis=0)
            for col_idx in range(feature_matrix.shape[1]):
                nan_mask = np.isnan(feature_matrix[:, col_idx])
                feature_matrix[nan_mask, col_idx] = col_medians[col_idx]
        elif handle_missing == "zero":
            feature_matrix = np.nan_to_num(feature_matrix, nan=0.0)
        elif handle_missing == "drop":
            raise NotImplementedError(
                "handle_missing='drop' not implemented. "
                "This would change the number of nodes, causing index mismatch."
            )

    # Normalize features
    if normalization == "zscore":
        mean = feature_matrix.mean(axis=0)
        std = feature_matrix.std(axis=0)
        # Avoid division by zero
        std[std == 0] = 1.0
        feature_matrix = (feature_matrix - mean) / std
    elif normalization == "minmax":
        min_val = feature_matrix.min(axis=0)
        max_val = feature_matrix.max(axis=0)
        # Avoid division by zero
        range_val = max_val - min_val
        range_val[range_val == 0] = 1.0
        feature_matrix = (feature_matrix - min_val) / range_val
    elif normalization == "none":
        pass  # No normalization
    else:
        raise ValueError(
            f"Unknown normalization: {normalization}. Use 'zscore', 'minmax', or 'none'"
        )

    features_tensor = torch.tensor(feature_matrix, dtype=torch.float32)

    logger.info(
        f"Extracted node features: shape {features_tensor.shape}, "
        f"normalization={normalization}, "
        f"mean={features_tensor.mean():.4f}, std={features_tensor.std():.4f}"
    )

    return features_tensor


def get_mobility_labels(
    lsoa_codes: np.ndarray | list,
    mobility_data: pd.DataFrame,
    label_column: str = "mobility_proxy",
) -> torch.Tensor:
    """
    Extract mobility proxy labels for target variable.

    Extracts the mobility proxy score for each LSOA to use as the target
    variable for supervised learning. The mobility proxy combines deprivation
    change, educational upward mobility, and income growth indicators.

    Args:
        lsoa_codes: Array or list of LSOA codes (e.g., ["E01000001", "E01000002"]).
        mobility_data: DataFrame with mobility proxy data. Must contain
            'lsoa_code' and label_column columns.
        label_column: Name of column containing mobility labels.
            Default: "mobility_proxy"

    Returns:
        Tensor of shape [num_nodes] with mobility labels.

    Raises:
        ValueError: If required columns are missing.

    Example:
        >>> from poverty_tda.data.mobility_proxy import compute_mobility_proxy
        >>> imd_data = load_imd_data()
        >>> mobility_df = compute_mobility_proxy(imd_data)
        >>> lsoa_codes = ["E01000001", "E01000002", "E01000003"]
        >>> labels = get_mobility_labels(lsoa_codes, mobility_df)
        >>> print(labels.shape)
        torch.Size([3])
    """
    if "lsoa_code" not in mobility_data.columns:
        raise ValueError("mobility_data must contain 'lsoa_code' column")

    if label_column not in mobility_data.columns:
        raise ValueError(
            f"mobility_data must contain '{label_column}' column. "
            f"Available columns: {list(mobility_data.columns)}"
        )

    # Filter mobility data to requested LSOAs
    lsoa_codes_array = np.array(lsoa_codes)
    mobility_filtered = mobility_data[
        mobility_data["lsoa_code"].isin(lsoa_codes_array)
    ].copy()

    # Ensure correct order matching lsoa_codes
    mobility_filtered["_order"] = mobility_filtered["lsoa_code"].apply(
        lambda x: np.where(lsoa_codes_array == x)[0][0] if x in lsoa_codes_array else -1
    )
    mobility_filtered = mobility_filtered.sort_values("_order")

    # Extract labels
    labels = mobility_filtered[label_column].values

    # Check for missing values
    if np.any(np.isnan(labels)):
        num_missing = np.isnan(labels).sum()
        logger.warning(
            f"Found {num_missing} missing mobility labels. "
            "Consider imputing or filtering these LSOAs."
        )

    labels_tensor = torch.tensor(labels, dtype=torch.float32)

    logger.info(
        f"Extracted mobility labels: shape {labels_tensor.shape}, "
        f"mean={labels_tensor.mean():.4f}, std={labels_tensor.std():.4f}, "
        f"min={labels_tensor.min():.4f}, max={labels_tensor.max():.4f}"
    )

    return labels_tensor


# ============================================================================
# GNN ARCHITECTURE
# ============================================================================


class SpatialGNN(torch.nn.Module):
    """
    GraphSAGE-based GNN for LSOA spatial mobility prediction.

    This model learns to predict economic mobility for each LSOA by aggregating
    information from spatially-connected neighbors. Uses GraphSAGE layers for
    efficient message passing on large graphs (~33K nodes).

    Architecture:
        - Input: Node features (IMD domain scores)
        - Message Passing: 2-3 GraphSAGE layers with mean aggregation
        - Regularization: Dropout + BatchNorm between layers
        - Output: Single value per node (mobility prediction)

    Args:
        input_dim: Number of input node features (default: 7 for IMD domains).
        hidden_dim: Hidden dimension for GNN layers (default: 64).
        output_dim: Output dimension (default: 1 for regression).
        num_layers: Number of GraphSAGE layers (default: 2, range: 2-3).
        dropout: Dropout probability (default: 0.3).
        use_batch_norm: Whether to use batch normalization (default: True).

    Example:
        >>> model = SpatialGNN(input_dim=7, hidden_dim=64, num_layers=2)
        >>> # Forward pass
        >>> edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long)
        >>> x = torch.randn(2, 7)  # 2 nodes, 7 features
        >>> out = model(x, edge_index)
        >>> print(out.shape)
        torch.Size([2, 1])
    """

    def __init__(
        self,
        input_dim: int = 7,
        hidden_dim: int = 64,
        output_dim: int = 1,
        num_layers: int = 2,
        dropout: float = 0.3,
        use_batch_norm: bool = True,
    ):
        super().__init__()

        if not HAS_TORCH_GEOMETRIC:
            raise ImportError(
                "PyTorch Geometric required for GNN. "
                "Install with: pip install torch-geometric torch-scatter torch-sparse"
            )

        if num_layers < 2:
            raise ValueError("num_layers must be at least 2")

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.use_batch_norm = use_batch_norm

        # Build GraphSAGE layers
        self.convs = torch.nn.ModuleList()
        self.batch_norms = torch.nn.ModuleList() if use_batch_norm else None

        # First layer: input_dim -> hidden_dim
        self.convs.append(SAGEConv(input_dim, hidden_dim, aggr="mean"))
        if use_batch_norm:
            self.batch_norms.append(torch.nn.BatchNorm1d(hidden_dim))

        # Hidden layers: hidden_dim -> hidden_dim
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim, aggr="mean"))
            if use_batch_norm:
                self.batch_norms.append(torch.nn.BatchNorm1d(hidden_dim))

        # Last layer: hidden_dim -> hidden_dim (before output projection)
        self.convs.append(SAGEConv(hidden_dim, hidden_dim, aggr="mean"))
        if use_batch_norm:
            self.batch_norms.append(torch.nn.BatchNorm1d(hidden_dim))

        # Output projection
        self.output_proj = torch.nn.Linear(hidden_dim, output_dim)

        # Dropout
        self.dropout_layer = torch.nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the GNN.

        Args:
            x: Node feature matrix of shape [num_nodes, input_dim].
            edge_index: Edge indices of shape [2, num_edges] (PyG format).

        Returns:
            Predictions of shape [num_nodes, output_dim].
        """
        # Message passing layers
        for i, conv in enumerate(self.convs):
            x = conv(x, edge_index)

            # Apply batch norm if enabled
            if self.use_batch_norm:
                x = self.batch_norms[i](x)

            # Apply activation (except on last layer before output)
            x = torch.nn.functional.relu(x)

            # Apply dropout
            x = self.dropout_layer(x)

        # Output projection
        x = self.output_proj(x)

        return x

    def reset_parameters(self):
        """Reset all learnable parameters."""
        for conv in self.convs:
            conv.reset_parameters()
        if self.use_batch_norm:
            for bn in self.batch_norms:
                bn.reset_parameters()
        self.output_proj.reset_parameters()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"input_dim={self.input_dim}, "
            f"hidden_dim={self.hidden_dim}, "
            f"output_dim={self.output_dim}, "
            f"num_layers={self.num_layers}, "
            f"dropout={self.dropout})"
        )
