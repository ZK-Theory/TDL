"""Shared graph construction utilities for torch-geometric models.

Builds graphs used across trajectory_tda, poverty_tda, and financial_tda.
Domain-specific graph builders (e.g. LSOA adjacency, Rips filtration) live
in their respective domains; this module handles patterns used by 2+ domains.

Requires torch-geometric. Import is guarded — check HAS_TORCH_GEOMETRIC before
using functions that return Data/Batch objects.
"""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

try:
    from torch_geometric.data import Data  # noqa: F401

    HAS_TORCH_GEOMETRIC = True
except ImportError:
    HAS_TORCH_GEOMETRIC = False
    logger.warning("torch-geometric not available; graph construction functions will raise ImportError.")


def _require_pyg() -> None:
    if not HAS_TORCH_GEOMETRIC:
        raise ImportError("torch-geometric is required. Install with: pip install torch-geometric")


def build_state_transition_graph(
    transition_matrix: NDArray[np.float64],
    node_features: NDArray[np.float64] | None = None,
    threshold: float = 0.0,
) -> "Data":
    """Build a PyG Data object from an employment-state transition matrix.

    Used for the 9-state employment-income graph in Paper 7 (geometric
    trajectory forecasting). Edge weights are transition probabilities;
    edges below threshold are pruned.

    Args:
        transition_matrix: Square matrix of shape (n_states, n_states)
            where entry [i, j] is the probability of transitioning from
            state i to state j.
        node_features: Optional node feature matrix, shape (n_states, n_feats).
            If None, uses one-hot encoding.
        threshold: Minimum transition probability to include as an edge.

    Returns:
        PyG Data object with edge_index, edge_attr, and x.
    """
    _require_pyg()
    import torch

    n = transition_matrix.shape[0]

    if node_features is None:
        node_features = np.eye(n, dtype=np.float32)

    rows, cols = np.where(transition_matrix > threshold)
    edge_weights = transition_matrix[rows, cols]

    edge_index = torch.tensor(np.stack([rows, cols]), dtype=torch.long)
    edge_attr = torch.tensor(edge_weights, dtype=torch.float32).unsqueeze(1)
    x = torch.tensor(node_features, dtype=torch.float32)

    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)


def build_knn_graph(
    points: NDArray[np.float64],
    k: int = 10,
    loop: bool = False,
) -> "Data":
    """Build a k-nearest-neighbour graph from a point cloud.

    General-purpose graph builder used when we need a graph structure
    over a set of embedded points (e.g., trajectory embedding → graph
    for GNN-based trajectory analysis).

    Args:
        points: Point cloud, shape (n_points, n_dims).
        k: Number of nearest neighbours.
        loop: Whether to include self-loops.

    Returns:
        PyG Data object with edge_index and x set to points.
    """
    _require_pyg()
    import torch
    from scipy.spatial import cKDTree

    n_points = points.shape[0]
    if n_points == 0:
        raise ValueError("build_knn_graph requires at least one point.")

    # Handle trivial single-point case without querying the KD-tree
    if n_points == 1:
        if loop:
            edge_index = torch.tensor([[0], [0]], dtype=torch.long)
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
        x = torch.tensor(points, dtype=torch.float32)
        return Data(x=x, edge_index=edge_index)

    # Clamp k so that cKDTree.query never requests more neighbours than exist.
    effective_k = min(k, n_points - 1)

    # If effective_k < 1, no neighbours other than optional self-loops.
    if effective_k < 1:
        src_list: list[int] = []
        dst_list: list[int] = []
        if loop:
            for i in range(n_points):
                src_list.append(i)
                dst_list.append(i)
        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long) if src_list else torch.empty((2, 0), dtype=torch.long)
        x = torch.tensor(points, dtype=torch.float32)
        return Data(x=x, edge_index=edge_index)

    tree = cKDTree(points)
    # effective_k+1 to include self; distances unused (unweighted graph)
    _, indices = tree.query(points, k=effective_k + 1)

    src_list = []
    dst_list = []
    for i, neighbours in enumerate(indices):
        for j in neighbours:
            if j == i and not loop:
                continue
            src_list.append(i)
            dst_list.append(j)

    edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
    x = torch.tensor(points, dtype=torch.float32)
    return Data(x=x, edge_index=edge_index)


def persistence_diagram_to_graph(
    diagram: NDArray[np.float64],
    max_lifetime: float | None = None,
    connect_threshold: float = 0.3,
) -> "Data":
    """Convert a persistence diagram to a graph for GNN processing.

    Each persistence point becomes a node; edges connect nearby features
    in (birth, death) space. This allows a GNN to learn on the topological
    summary rather than treating diagram points as independent.

    Args:
        diagram: Persistence diagram, shape (n_pairs, 2) with (birth, death).
        max_lifetime: If set, clip infinite deaths to this value.
        connect_threshold: Maximum Euclidean distance in (birth, death) space
            to connect two persistence points with an edge.

    Returns:
        PyG Data object; each node feature is a (birth, death, lifetime) triple.
    """
    _require_pyg()
    import torch
    from scipy.spatial.distance import pdist, squareform

    if max_lifetime is not None:
        diagram = np.where(diagram == np.inf, max_lifetime, diagram)

    # Filter infinite deaths that weren't clipped
    finite_mask = np.isfinite(diagram).all(axis=1)
    diagram = diagram[finite_mask]

    if len(diagram) == 0:
        x = torch.zeros((1, 3), dtype=torch.float32)
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        return Data(x=x, edge_index=edge_index)

    lifetimes = (diagram[:, 1] - diagram[:, 0]).reshape(-1, 1)
    node_features = np.concatenate([diagram, lifetimes], axis=1).astype(np.float32)

    dists = squareform(pdist(diagram))
    rows, cols = np.where((dists < connect_threshold) & (dists > 0))
    edge_index = torch.tensor([rows.tolist(), cols.tolist()], dtype=torch.long)
    x = torch.tensor(node_features, dtype=torch.float32)

    return Data(x=x, edge_index=edge_index)


def add_household_edges(
    data: "Data",
    household_ids: NDArray[np.int64],
) -> "Data":
    """Add intra-household edges to an individual-level graph.

    For Paper 8 (GNNs on household social graphs): individuals sharing
    a household ID are connected bidirectionally.

    Args:
        data: Existing PyG Data with individual nodes.
        household_ids: Array of household ID for each node, shape (n_nodes,).

    Returns:
        Data with additional household edges (added to existing edge_index).
    """
    _require_pyg()
    import torch

    unique_hh = np.unique(household_ids)
    new_src: list[int] = []
    new_dst: list[int] = []

    for hh in unique_hh:
        members = np.where(household_ids == hh)[0]
        if len(members) < 2:  # noqa: PLR2004
            continue
        for i in members:
            for j in members:
                if i != j:
                    new_src.append(int(i))
                    new_dst.append(int(j))

    if not new_src:
        return data

    new_edges = torch.tensor([new_src, new_dst], dtype=torch.long)
    combined = torch.cat([data.edge_index, new_edges], dim=1)
    data.edge_index = combined
    return data
