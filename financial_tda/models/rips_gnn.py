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


def train_val_test_split_temporal(
    dataset: RipsGraphDataset,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[list[int], list[int], list[int]]:
    """
    Split dataset indices into train/val/test with temporal ordering.

    For financial time series, maintains chronological order to prevent
    future leakage - training set comes from earlier time periods.

    Args:
        dataset: RipsGraphDataset to split.
        train_ratio: Fraction for training. Default 0.7.
        val_ratio: Fraction for validation. Default 0.15.
        test_ratio: Fraction for testing. Default 0.15.

    Returns:
        Tuple of (train_indices, val_indices, test_indices).

    Raises:
        ValueError: If ratios don't sum to 1.0.

    Examples:
        >>> dataset = RipsGraphDataset(point_clouds, labels)
        >>> train_idx, val_idx, test_idx = train_val_test_split_temporal(dataset)
    """
    if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
        raise ValueError(
            f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"
        )

    n_samples = len(dataset)
    n_train = int(n_samples * train_ratio)
    n_val = int(n_samples * val_ratio)

    train_idx = list(range(n_train))
    val_idx = list(range(n_train, n_train + n_val))
    test_idx = list(range(n_train + n_val, n_samples))

    logger.info(
        "Temporal split: train=%d, val=%d, test=%d",
        len(train_idx),
        len(val_idx),
        len(test_idx),
    )

    return train_idx, val_idx, test_idx


class RipsGNNTrainer:
    """
    Training pipeline for RipsGNN models with early stopping.

    Supports both GAT and GraphSAGE architectures with configurable
    hyperparameters, early stopping, and comprehensive metrics tracking.

    Args:
        model: RipsGNN model to train.
        dataset: RipsGraphDataset with training data.
        train_idx: Indices for training set.
        val_idx: Indices for validation set.
        lr: Learning rate. Default 1e-3.
        weight_decay: L2 regularization coefficient. Default 1e-4.
        patience: Early stopping patience (epochs). Default 10.
        device: Device for training ('cpu' or 'cuda'). Default 'cpu'.

    Attributes:
        model: GNN model being trained.
        dataset: Graph dataset.
        optimizer: Adam optimizer.
        criterion: Cross-entropy loss.
        history: Training history dict with losses and metrics.
        best_val_loss: Best validation loss achieved.
        patience_counter: Current patience counter value.

    Examples:
        >>> model = create_rips_gnn(input_dim=3, architecture="gat")
        >>> dataset = RipsGraphDataset(point_clouds, labels)
        >>> train_idx, val_idx, _ = train_val_test_split_temporal(dataset)
        >>> trainer = RipsGNNTrainer(model, dataset, train_idx, val_idx)
        >>> history = trainer.train(epochs=50)
    """

    def __init__(
        self,
        model: RipsGNN,
        dataset: RipsGraphDataset,
        train_idx: list[int],
        val_idx: list[int],
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        patience: int = 10,
        device: str = "cpu",
    ):
        self.model = model.to(device)
        self.dataset = dataset
        self.train_idx = train_idx
        self.val_idx = val_idx
        self.device = device

        self.optimizer = torch.optim.Adam(
            model.parameters(), lr=lr, weight_decay=weight_decay
        )
        self.criterion = nn.CrossEntropyLoss()

        # Early stopping
        self.patience = patience
        self.best_val_loss = float("inf")
        self.patience_counter = 0
        self.best_model_state = None

        # History tracking
        self.history = {
            "train_loss": [],
            "val_loss": [],
            "train_acc": [],
            "val_acc": [],
        }

        logger.info(
            "Initialized RipsGNNTrainer: %s, train=%d, val=%d, lr=%.4f, device=%s",
            model.architecture.upper(),
            len(train_idx),
            len(val_idx),
            lr,
            device,
        )

    def train_epoch(self) -> tuple[float, float]:
        """
        Train for one epoch.

        Returns:
            Tuple of (average_loss, accuracy).
        """
        self.model.train()

        # Get training batch
        train_batch = self.dataset.get_batch(self.train_idx).to(self.device)

        # Forward pass
        self.optimizer.zero_grad()
        logits = self.model(train_batch)
        loss = self.criterion(logits, train_batch.y.squeeze())

        # Backward pass
        loss.backward()
        self.optimizer.step()

        # Compute accuracy
        with torch.no_grad():
            preds = logits.argmax(dim=1)
            accuracy = (preds == train_batch.y.squeeze()).float().mean().item()

        return loss.item(), accuracy

    def validate(self) -> tuple[float, float]:
        """
        Validate on validation set.

        Returns:
            Tuple of (validation_loss, validation_accuracy).
        """
        self.model.eval()

        val_batch = self.dataset.get_batch(self.val_idx).to(self.device)

        with torch.no_grad():
            logits = self.model(val_batch)
            loss = self.criterion(logits, val_batch.y.squeeze())

            preds = logits.argmax(dim=1)
            accuracy = (preds == val_batch.y.squeeze()).float().mean().item()

        return loss.item(), accuracy

    def train(self, epochs: int = 100, verbose: bool = True) -> dict:
        """
        Train model with early stopping.

        Args:
            epochs: Maximum number of epochs. Default 100.
            verbose: Whether to print progress. Default True.

        Returns:
            Training history dictionary with losses and accuracies.
        """
        if verbose:
            arch = self.model.architecture.upper()
            print(f"Training {arch} for up to {epochs} epochs...")

        for epoch in range(epochs):
            # Train
            train_loss, train_acc = self.train_epoch()
            self.history["train_loss"].append(train_loss)
            self.history["train_acc"].append(train_acc)

            # Validate
            val_loss, val_acc = self.validate()
            self.history["val_loss"].append(val_loss)
            self.history["val_acc"].append(val_acc)

            # Early stopping check
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                # Save best model state
                self.best_model_state = {
                    k: v.cpu().clone() for k, v in self.model.state_dict().items()
                }
            else:
                self.patience_counter += 1

            # Print progress
            if verbose and (epoch + 1) % 10 == 0:
                print(
                    f"  Epoch {epoch + 1}/{epochs}: "
                    f"train_loss={train_loss:.4f}, train_acc={train_acc * 100:.1f}%, "
                    f"val_loss={val_loss:.4f}, val_acc={val_acc * 100:.1f}%"
                )

            # Early stopping
            if self.patience_counter >= self.patience:
                if verbose:
                    print(f"  Early stopping at epoch {epoch + 1}")
                break

        # Restore best model
        if self.best_model_state is not None:
            self.model.load_state_dict(self.best_model_state)
            if verbose:
                print(f"  Restored best model (val_loss={self.best_val_loss:.4f})")

        return self.history

    def evaluate(self, test_idx: list[int]) -> dict:
        """
        Evaluate model on test set.

        Args:
            test_idx: Indices for test set.

        Returns:
            Dictionary with test metrics (loss, accuracy, predictions).
        """
        self.model.eval()

        test_batch = self.dataset.get_batch(test_idx).to(self.device)

        with torch.no_grad():
            logits = self.model(test_batch)
            loss = self.criterion(logits, test_batch.y.squeeze())

            preds = logits.argmax(dim=1)
            probs = torch.softmax(logits, dim=1)
            accuracy = (preds == test_batch.y.squeeze()).float().mean().item()

        results = {
            "test_loss": loss.item(),
            "test_accuracy": accuracy,
            "predictions": preds.cpu().numpy(),
            "probabilities": probs.cpu().numpy(),
            "true_labels": test_batch.y.squeeze().cpu().numpy(),
        }

        logger.info(
            "Test evaluation: loss=%.4f, accuracy=%.2f%%",
            results["test_loss"],
            results["test_accuracy"] * 100,
        )

        return results


def compare_rips_vs_perslay(
    point_clouds: list[NDArray[np.floating]],
    labels: Tensor | NDArray[np.integer],
    gnn_architecture: GNNArchitecture = "gat",
    hidden_dim: int = 64,
    num_layers: int = 2,
    epochs: int = 50,
    device: str = "cpu",
) -> dict:
    """
    Compare RipsGNN approach against Perslay persistence diagram vectorization.

    Trains both approaches on the same data and compares accuracy, inference
    time, and other metrics. This utility helps determine which topological
    approach is better suited for a specific regime detection task.

    Args:
        point_clouds: List of Takens embeddings (point clouds).
        labels: Regime labels (0=normal, 1=crisis).
        gnn_architecture: GNN architecture to use. Default "gat".
        hidden_dim: Hidden dimension for both approaches. Default 64.
        num_layers: Number of layers for both approaches. Default 2.
        epochs: Training epochs for both models. Default 50.
        device: Device for training. Default "cpu".

    Returns:
        Dictionary with comparison results including:
            - rips_results: Metrics for RipsGNN approach
            - perslay_results: Metrics for Perslay approach
            - comparison: Summary comparison metrics

    Examples:
        >>> from financial_tda.topology import takens_embedding
        >>> # Create embeddings from time series
        >>> embeddings = [takens_embedding(ts, 3, 3) for ts in time_series]
        >>> labels = np.array([0, 1, 0, 1, ...])
        >>> results = compare_rips_vs_perslay(embeddings, labels)
        >>> print(f"RipsGNN: {results['rips_results']['test_accuracy']*100:.1f}%")
        >>> print(f"Perslay: {results['perslay_results']['test_accuracy']*100:.1f}%")

    Notes:
        Requires both torch-geometric (for RipsGNN) and giotto-tda (for Perslay)
        to be installed. This comparison helps answer:
        - Which approach achieves higher accuracy?
        - Which is faster for inference?
        - How do they scale with dataset size?
    """
    import time

    from financial_tda.models.persistence_layers import create_perslay
    from financial_tda.topology.filtration import compute_persistence_vr

    # Convert labels if needed
    if not isinstance(labels, Tensor):
        labels = torch.tensor(labels, dtype=torch.long)

    n_dims = point_clouds[0].shape[1]

    print("=" * 75)
    print("Comparison: RipsGNN vs Perslay")
    print("=" * 75)

    # ========== RipsGNN Approach ==========
    print("\n1. Training RipsGNN...")

    # Create Rips graph dataset
    rips_dataset = RipsGraphDataset(point_clouds, labels)
    train_idx, val_idx, test_idx = train_val_test_split_temporal(rips_dataset)

    # Create and train RipsGNN
    torch.manual_seed(42)
    rips_model = create_rips_gnn(
        input_dim=n_dims,
        hidden_dim=hidden_dim,
        output_dim=2,
        num_layers=num_layers,
        architecture=gnn_architecture,
        dropout=0.3,
    )

    rips_trainer = RipsGNNTrainer(
        model=rips_model,
        dataset=rips_dataset,
        train_idx=train_idx,
        val_idx=val_idx,
        lr=5e-4,
        device=device,
    )

    rips_start = time.perf_counter()
    rips_history = rips_trainer.train(epochs=epochs, verbose=False)
    rips_train_time = time.perf_counter() - rips_start

    rips_test_results = rips_trainer.evaluate(test_idx)

    # Measure RipsGNN inference time
    test_batch = rips_dataset.get_batch(test_idx).to(device)
    rips_model.eval()
    with torch.no_grad():
        inference_times = []
        for _ in range(50):
            start = time.perf_counter()
            _ = rips_model(test_batch)
            inference_times.append(time.perf_counter() - start)
    rips_inference_time = np.mean(inference_times) * 1000  # ms

    print(f"   Training time: {rips_train_time:.2f}s")
    print(f"   Test accuracy: {rips_test_results['test_accuracy'] * 100:.1f}%")
    print(f"   Inference time: {rips_inference_time:.2f} ms")

    # ========== Perslay Approach ==========
    print("\n2. Training Perslay...")

    # Compute persistence diagrams
    print("   Computing persistence diagrams...")
    persistence_diagrams = []
    for pc in point_clouds:
        try:
            diagram = compute_persistence_vr(pc, homology_dimensions=(0, 1))
            persistence_diagrams.append(
                torch.tensor(diagram[:, :2], dtype=torch.float32)
            )
        except Exception as e:
            logger.warning("Failed to compute persistence for cloud: %s", e)
            # Use empty diagram as fallback
            persistence_diagrams.append(torch.zeros(1, 2))

    # Create Perslay model (single time window, not sequential)
    torch.manual_seed(42)
    perslay = create_perslay(
        input_dim=2,
        hidden_dims=[hidden_dim, hidden_dim // 2],
        output_dim=hidden_dim,
        perm_op="mean",
        use_weight=True,
    )

    # Simple classifier on top of Perslay
    perslay_classifier = nn.Sequential(
        perslay,
        nn.Linear(hidden_dim, hidden_dim // 2),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(hidden_dim // 2, 2),
    ).to(device)

    # Train Perslay
    optimizer = torch.optim.Adam(
        perslay_classifier.parameters(), lr=5e-4, weight_decay=1e-4
    )
    criterion = nn.CrossEntropyLoss()

    # Use same train/val/test split
    train_diagrams = [persistence_diagrams[i] for i in train_idx]
    val_diagrams = [persistence_diagrams[i] for i in val_idx]
    test_diagrams = [persistence_diagrams[i] for i in test_idx]

    train_labels = labels[train_idx]
    val_labels = labels[val_idx]
    test_labels = labels[test_idx]

    perslay_start = time.perf_counter()
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(epochs):
        # Train
        perslay_classifier.train()
        optimizer.zero_grad()
        logits = perslay_classifier(train_diagrams)
        loss = criterion(logits, train_labels)
        loss.backward()
        optimizer.step()

        # Validate
        perslay_classifier.eval()
        with torch.no_grad():
            val_logits = perslay_classifier(val_diagrams)
            val_loss = criterion(val_logits, val_labels)

        if val_loss < best_val_loss:
            best_val_loss = val_loss.item()
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= 10:
            break

    perslay_train_time = time.perf_counter() - perslay_start

    # Test Perslay
    perslay_classifier.eval()
    with torch.no_grad():
        test_logits = perslay_classifier(test_diagrams)
        test_loss = criterion(test_logits, test_labels)
        test_preds = test_logits.argmax(dim=1)
        test_acc = (test_preds == test_labels).float().mean().item()

    # Measure Perslay inference time
    with torch.no_grad():
        inference_times = []
        for _ in range(50):
            start = time.perf_counter()
            _ = perslay_classifier(test_diagrams)
            inference_times.append(time.perf_counter() - start)
    perslay_inference_time = np.mean(inference_times) * 1000  # ms

    print(f"   Training time: {perslay_train_time:.2f}s")
    print(f"   Test accuracy: {test_acc * 100:.1f}%")
    print(f"   Inference time: {perslay_inference_time:.2f} ms")

    # ========== Comparison Summary ==========
    print("\n" + "=" * 75)
    print("3. Comparison Summary:")
    print("=" * 75)

    comparison = {
        "accuracy_diff": rips_test_results["test_accuracy"] - test_acc,
        "train_time_ratio": rips_train_time / perslay_train_time,
        "inference_time_ratio": rips_inference_time / perslay_inference_time,
    }

    print("\n   Accuracy:")
    print(f"      RipsGNN:  {rips_test_results['test_accuracy'] * 100:.1f}%")
    print(f"      Perslay:  {test_acc * 100:.1f}%")
    print(f"      Diff:     {comparison['accuracy_diff'] * 100:+.1f}%")

    print("\n   Training Time:")
    print(f"      RipsGNN:  {rips_train_time:.2f}s")
    print(f"      Perslay:  {perslay_train_time:.2f}s")
    print(f"      Ratio:    {comparison['train_time_ratio']:.2f}x")

    print("\n   Inference Time:")
    print(f"      RipsGNN:  {rips_inference_time:.2f} ms")
    print(f"      Perslay:  {perslay_inference_time:.2f} ms")
    print(f"      Ratio:    {comparison['inference_time_ratio']:.2f}x")

    # Determine winner
    print("\n   Recommendation:")
    acc_diff = comparison["accuracy_diff"] * 100
    if comparison["accuracy_diff"] > 0.05:
        print(f"      RipsGNN: Higher accuracy ({acc_diff:+.1f}%)")
    elif comparison["accuracy_diff"] < -0.05:
        print(f"      Perslay: Higher accuracy ({-acc_diff:+.1f}%)")
    else:
        print("      Similar accuracy (within 5%)")

    time_ratio = comparison["inference_time_ratio"]
    if time_ratio < 0.8:
        print(f"      RipsGNN: Faster inference ({1 / time_ratio:.1f}x)")
    elif time_ratio > 1.2:
        print(f"      Perslay: Faster inference ({time_ratio:.1f}x)")
    else:
        print("      Similar inference speed")

    print("=" * 75)

    return {
        "rips_results": {
            "test_accuracy": rips_test_results["test_accuracy"],
            "test_loss": rips_test_results["test_loss"],
            "train_time": rips_train_time,
            "inference_time_ms": rips_inference_time,
            "history": rips_history,
        },
        "perslay_results": {
            "test_accuracy": test_acc,
            "test_loss": test_loss.item(),
            "train_time": perslay_train_time,
            "inference_time_ms": perslay_inference_time,
        },
        "comparison": comparison,
    }
