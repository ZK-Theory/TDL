"""
Graph Neural Network on Rips Complex for financial regime detection.

This module implements GNN architectures that learn directly on the Rips complex
structure of Takens embeddings, providing an alternative to persistence diagram
vectorization (Perslay) for regime discrimination.

Architecture:
    Time Series → Takens Embedding → Rips Graph → GNN → Classification

The Rips complex captures the topology of the point cloud at a fixed filtration
threshold, representing it as a graph where:
    - Nodes: Embedding points (coordinates as features)
    - Edges: Pairs of points within the filtration threshold
    - Edge attributes: Pairwise distances

References:
    Kipf, T. N., & Welling, M. (2017). Semi-Supervised Classification with
        Graph Convolutional Networks. ICLR 2017.
    Veličković, P., et al. (2018). Graph Attention Networks. ICLR 2018.
    Hamilton, W., et al. (2017). Inductive Representation Learning on
        Large Graphs. NeurIPS 2017.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import numpy as np
import torch
import torch.nn as nn
from scipy.spatial.distance import pdist, squareform
from torch import Tensor
from torch_geometric.data import Batch, Data
from torch_geometric.nn import (
    GATConv,
    GCNConv,
    SAGEConv,
    global_max_pool,
    global_mean_pool,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Type aliases
GNNArchitecture = Literal["gcn", "gat", "graphsage"]
ReadoutType = Literal["mean", "max"]


def build_rips_graph(
    point_cloud: NDArray[np.floating] | Tensor,
    filtration_threshold: float | None = None,
) -> Data:
    """
    Build a graph from point cloud using Rips complex construction.

    Creates a PyTorch Geometric graph where nodes correspond to points in the
    point cloud and edges connect pairs of points within the filtration threshold.

    Args:
        point_cloud: 2D array of shape (n_points, n_dimensions) representing
            the embedded time series point cloud (e.g., from Takens embedding).
        filtration_threshold: Maximum distance for edge creation. If None,
            uses 90th percentile of pairwise distances (matching VR persistence).

    Returns:
        PyTorch Geometric Data object with:
            - x: Node features (n_points, n_dimensions) - point coordinates
            - edge_index: Edge connectivity (2, num_edges) - symmetric
            - edge_attr: Edge attributes (num_edges, 1) - pairwise distances

    Raises:
        ValueError: If point_cloud is not 2D or has fewer than 2 points.

    Examples:
        >>> import numpy as np
        >>> from financial_tda.topology import takens_embedding
        >>> ts = np.sin(np.linspace(0, 4*np.pi, 100))
        >>> point_cloud = takens_embedding(ts, delay=3, dimension=3)
        >>> graph = build_rips_graph(point_cloud)
        >>> print(f"Nodes: {graph.num_nodes}, Edges: {graph.num_edges}")

    Notes:
        The 90th percentile threshold typically creates sparse graphs that
        capture local topology without excessive edges. Adjust threshold
        based on application requirements.
    """
    # Convert to numpy if tensor
    if isinstance(point_cloud, Tensor):
        point_cloud = point_cloud.numpy()

    point_cloud = np.asarray(point_cloud, dtype=np.float64)

    # Input validation
    if point_cloud.ndim != 2:
        raise ValueError(
            f"point_cloud must be 2D, got shape {point_cloud.shape}. "
            "Expected (n_points, n_dimensions)."
        )

    n_points, n_dims = point_cloud.shape

    if n_points < 2:
        raise ValueError(f"point_cloud must have at least 2 points, got {n_points}.")

    if not np.isfinite(point_cloud).all():
        raise ValueError("point_cloud contains non-finite values (NaN or Inf).")

    # Compute pairwise distances
    distances = pdist(point_cloud)
    distance_matrix = squareform(distances)

    # Compute filtration threshold if not provided (90th percentile)
    if filtration_threshold is None:
        filtration_threshold = float(np.percentile(distances, 90))
        logger.debug(
            "Auto-computed filtration_threshold=%.4f from 90th percentile",
            filtration_threshold,
        )

    # Ensure positive threshold
    if filtration_threshold <= 0:
        filtration_threshold = float(np.percentile(distances, 90))
        if filtration_threshold <= 0:
            filtration_threshold = 1.0
        logger.warning(
            "filtration_threshold was <= 0, defaulted to %.4f", filtration_threshold
        )

    # Build edge list: pairs (i, j) where i < j and distance <= threshold
    edge_pairs = np.argwhere(
        (distance_matrix <= filtration_threshold) & (distance_matrix > 0)
    )

    # Create symmetric edge_index (undirected graph)
    # edge_pairs already includes both (i,j) and (j,i) from squareform
    edge_index = edge_pairs.T  # Shape: (2, num_edges)

    # Get edge distances
    edge_distances = distance_matrix[edge_pairs[:, 0], edge_pairs[:, 1]]
    edge_attr = edge_distances.reshape(-1, 1)

    # Convert to PyTorch tensors
    x = torch.tensor(point_cloud, dtype=torch.float32)
    edge_index = torch.tensor(edge_index, dtype=torch.long)
    edge_attr = torch.tensor(edge_attr, dtype=torch.float32)

    # Create PyG Data object
    graph = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)

    logger.debug(
        "Built Rips graph: %d nodes, %d edges (threshold=%.4f, density=%.4f)",
        n_points,
        edge_index.shape[1],
        filtration_threshold,
        edge_index.shape[1] / (n_points * (n_points - 1)),
    )

    return graph


class RipsGraphDataset:
    """
    Dataset for batched Rips graph processing with regime labels.

    Converts time series windows into Rips graphs via Takens embedding,
    supporting batched loading for GNN training.

    Args:
        point_clouds: List of point clouds, each with shape (n_points, n_dims).
        labels: Tensor of regime labels with shape (n_samples,).
        filtration_threshold: Optional fixed threshold for all graphs.
            If None, computed per graph using 90th percentile.

    Attributes:
        graphs: List of PyG Data objects (computed lazily or at init).
        labels: Regime labels tensor.
        filtration_threshold: Threshold used for graph construction.

    Examples:
        >>> from financial_tda.topology import takens_embedding
        >>> # Create point clouds from multiple time windows
        >>> point_clouds = [takens_embedding(window, delay=3, dimension=3)
        ...                 for window in time_windows]
        >>> labels = torch.tensor([0, 1, 0, 1, ...])  # 0=normal, 1=crisis
        >>> dataset = RipsGraphDataset(point_clouds, labels)
        >>> print(f"Dataset size: {len(dataset)}")
    """

    def __init__(
        self,
        point_clouds: list[NDArray[np.floating] | Tensor],
        labels: Tensor,
        filtration_threshold: float | None = None,
    ):
        if len(point_clouds) != len(labels):
            raise ValueError(
                f"Number of point clouds ({len(point_clouds)}) must match "
                f"number of labels ({len(labels)})"
            )

        if len(point_clouds) == 0:
            raise ValueError("point_clouds cannot be empty")

        self.point_clouds = point_clouds
        self.labels = labels
        self.filtration_threshold = filtration_threshold

        # Build graphs at initialization
        self.graphs: list[Data] = []
        for i, pc in enumerate(point_clouds):
            try:
                graph = build_rips_graph(pc, filtration_threshold)
                graph.y = labels[i].unsqueeze(0) if labels[i].dim() == 0 else labels[i]
                self.graphs.append(graph)
            except ValueError as e:
                logger.warning("Skipping point cloud %d: %s", i, e)
                # Create minimal graph for invalid point clouds
                x = torch.zeros(2, pc.shape[1] if hasattr(pc, "shape") else 3)
                edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long)
                edge_attr = torch.ones(2, 1)
                graph = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
                graph.y = labels[i].unsqueeze(0) if labels[i].dim() == 0 else labels[i]
                self.graphs.append(graph)

        logger.info(
            "Created RipsGraphDataset with %d graphs (threshold=%s)",
            len(self.graphs),
            filtration_threshold,
        )

    def __len__(self) -> int:
        """Return number of graphs in dataset."""
        return len(self.graphs)

    def __getitem__(self, idx: int) -> Data:
        """Get graph at index."""
        return self.graphs[idx]

    def get_batch(self, indices: list[int]) -> Batch:
        """
        Create a batched graph from specified indices.

        Args:
            indices: List of graph indices to batch together.

        Returns:
            PyG Batch object with combined graphs.
        """
        graphs = [self.graphs[i] for i in indices]
        return Batch.from_data_list(graphs)

    @staticmethod
    def collate_fn(graphs: list[Data]) -> Batch:
        """
        Collate function for DataLoader.

        Args:
            graphs: List of Data objects.

        Returns:
            Batched graphs.
        """
        return Batch.from_data_list(graphs)


def create_rips_dataset_from_embeddings(
    embeddings: list[NDArray[np.floating]],
    labels: NDArray[np.integer] | Tensor,
    filtration_threshold: float | None = None,
) -> RipsGraphDataset:
    """
    Factory function to create RipsGraphDataset from Takens embeddings.

    Convenience function that handles label conversion and dataset creation.

    Args:
        embeddings: List of Takens embeddings (point clouds).
        labels: Array of integer regime labels.
        filtration_threshold: Optional fixed threshold.

    Returns:
        Configured RipsGraphDataset.

    Examples:
        >>> embeddings = [takens_embedding(w, 3, 3) for w in windows]
        >>> labels = np.array([0, 1, 0, 1, 0])
        >>> dataset = create_rips_dataset_from_embeddings(embeddings, labels)
    """
    if not isinstance(labels, Tensor):
        labels = torch.tensor(labels, dtype=torch.long)

    return RipsGraphDataset(
        point_clouds=embeddings,
        labels=labels,
        filtration_threshold=filtration_threshold,
    )


class RipsGNN(nn.Module):
    """
    Graph Neural Network for regime detection on Rips complex graphs.

    Implements three GNN architecture options (GCN, GAT, GraphSAGE) with
    flexible graph-level readout and classification for financial regime
    discrimination.

    Architecture:
        1. Message passing layers (2-3 layers)
        2. Graph-level pooling (mean or max)
        3. Classification head (MLP)

    Args:
        input_dim: Dimension of node features (embedding dimension).
        hidden_dim: Hidden dimension for message passing layers. Default 64.
        output_dim: Number of output classes. Default 2 (binary classification).
        num_layers: Number of message passing layers. Default 2.
        architecture: GNN architecture type. Options:
            - "gcn": Graph Convolutional Network (spectral, simpler)
            - "gat": Graph Attention Network (learns edge importance)
            - "graphsage": GraphSAGE (sampling-based, handles large graphs)
        readout: Graph-level pooling operation. Options:
            - "mean": Mean pooling over nodes
            - "max": Max pooling over nodes
        dropout: Dropout probability for regularization. Default 0.2.
        heads: Number of attention heads for GAT. Default 4.
            Only applicable when architecture="gat".

    Attributes:
        architecture: Type of GNN architecture used.
        readout: Graph pooling operation type.
        convs: List of message passing layers.
        batch_norms: List of batch normalization layers.
        classifier: Classification head MLP.

    Examples:
        >>> # GCN architecture
        >>> model = RipsGNN(
        ...     input_dim=3,
        ...     hidden_dim=64,
        ...     output_dim=2,
        ...     architecture="gcn"
        ... )
        >>> # GAT with attention
        >>> model = RipsGNN(
        ...     input_dim=3,
        ...     hidden_dim=64,
        ...     architecture="gat",
        ...     heads=4
        ... )

    References:
        GCN: Kipf & Welling (2017)
        GAT: Veličković et al. (2018)
        GraphSAGE: Hamilton et al. (2017)
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        output_dim: int = 2,
        num_layers: int = 2,
        architecture: GNNArchitecture = "gcn",
        readout: ReadoutType = "mean",
        dropout: float = 0.2,
        heads: int = 4,
    ):
        super().__init__()

        if architecture not in {"gcn", "gat", "graphsage"}:
            raise ValueError(
                f"Invalid architecture: {architecture}. "
                "Use 'gcn', 'gat', or 'graphsage'."
            )

        if readout not in {"mean", "max"}:
            raise ValueError(f"Invalid readout: {readout}. Use 'mean' or 'max'.")

        if num_layers < 1:
            raise ValueError(f"num_layers must be >= 1, got {num_layers}")

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        self.architecture = architecture
        self.readout = readout
        self.dropout = dropout
        self.heads = heads

        # Build message passing layers
        self.convs = nn.ModuleList()
        self.batch_norms = nn.ModuleList()

        for i in range(num_layers):
            in_channels = input_dim if i == 0 else hidden_dim
            out_channels = hidden_dim

            if architecture == "gcn":
                conv = GCNConv(in_channels, out_channels)

            elif architecture == "gat":
                # GAT uses multi-head attention
                # For hidden layers, concatenate heads; for last layer, average
                if i < num_layers - 1:
                    conv = GATConv(
                        in_channels,
                        out_channels // heads,
                        heads=heads,
                        dropout=dropout,
                        concat=True,
                    )
                else:
                    # Last layer: average heads to get hidden_dim output
                    conv = GATConv(
                        in_channels,
                        out_channels,
                        heads=heads,
                        dropout=dropout,
                        concat=False,
                    )

            elif architecture == "graphsage":
                conv = SAGEConv(in_channels, out_channels, aggr="mean")

            else:
                raise RuntimeError(f"Unexpected architecture: {architecture}")

            self.convs.append(conv)
            self.batch_norms.append(nn.BatchNorm1d(out_channels))

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim),
        )

        logger.info(
            "Initialized RipsGNN: %s, %d layers, hidden=%d, readout=%s, classes=%d",
            architecture.upper(),
            num_layers,
            hidden_dim,
            readout,
            output_dim,
        )

    def forward(self, batch: Batch) -> Tensor:
        """
        Forward pass through GNN.

        Args:
            batch: PyG Batch object containing batched graphs with:
                - x: Node features (num_nodes, input_dim)
                - edge_index: Edge connectivity (2, num_edges)
                - edge_attr: Optional edge attributes (num_edges, edge_dim)
                - batch: Batch assignment vector (num_nodes,)

        Returns:
            Logits of shape (batch_size, output_dim).
        """
        x, edge_index, batch_idx = batch.x, batch.edge_index, batch.batch
        # edge_attr available via batch.edge_attr if needed for edge-aware convs

        # Message passing layers
        for i, (conv, bn) in enumerate(zip(self.convs, self.batch_norms)):
            # Apply convolution
            if self.architecture in {"gcn", "gat"}:
                x = conv(x, edge_index)
            elif self.architecture == "graphsage":
                x = conv(x, edge_index)

            # Batch normalization
            x = bn(x)

            # Activation (ReLU for all but last layer)
            if i < self.num_layers - 1:
                x = torch.relu(x)
                x = torch.dropout(x, p=self.dropout, train=self.training)

        # Final activation after last message passing layer
        x = torch.relu(x)

        # Graph-level readout (pooling)
        if self.readout == "mean":
            x = global_mean_pool(x, batch_idx)
        elif self.readout == "max":
            x = global_max_pool(x, batch_idx)

        # Classification
        logits = self.classifier(x)

        return logits

    def predict_proba(self, batch: Batch) -> Tensor:
        """
        Predict class probabilities using softmax.

        Args:
            batch: PyG Batch object (see forward()).

        Returns:
            Probabilities of shape (batch_size, output_dim).
        """
        logits = self.forward(batch)
        probs = torch.softmax(logits, dim=1)
        return probs

    def predict(self, batch: Batch) -> Tensor:
        """
        Predict class labels (argmax).

        Args:
            batch: PyG Batch object (see forward()).

        Returns:
            Class labels of shape (batch_size,).
        """
        logits = self.forward(batch)
        predictions = torch.argmax(logits, dim=1)
        return predictions


def create_rips_gnn(
    input_dim: int,
    hidden_dim: int = 64,
    output_dim: int = 2,
    num_layers: int = 2,
    architecture: GNNArchitecture = "gcn",
    readout: ReadoutType = "mean",
    dropout: float = 0.2,
    heads: int = 4,
) -> RipsGNN:
    """
    Factory function to create a RipsGNN model.

    Convenience function for creating GNN models with standard configurations.

    Args:
        input_dim: Dimension of node features (embedding dimension).
        hidden_dim: Hidden dimension for message passing. Default 64.
        output_dim: Number of output classes. Default 2.
        num_layers: Number of message passing layers. Default 2.
        architecture: GNN architecture ("gcn", "gat", "graphsage"). Default "gcn".
        readout: Graph pooling ("mean", "max"). Default "mean".
        dropout: Dropout probability. Default 0.2.
        heads: Number of attention heads for GAT. Default 4.

    Returns:
        Configured RipsGNN model.

    Examples:
        >>> # Simple GCN
        >>> model = create_rips_gnn(input_dim=3, architecture="gcn")
        >>> # GAT with 8 attention heads
        >>> model = create_rips_gnn(
        ...     input_dim=3,
        ...     architecture="gat",
        ...     heads=8,
        ...     hidden_dim=128
        ... )
    """
    return RipsGNN(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        output_dim=output_dim,
        num_layers=num_layers,
        architecture=architecture,
        readout=readout,
        dropout=dropout,
        heads=heads,
    )
