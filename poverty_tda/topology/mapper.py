"""
Mapper Algorithm for Deprivation Typology Discovery.

Implements the Mapper algorithm (Singh, Mémoli, Carlsson, 2007) for analyzing
the topological structure of multi-dimensional deprivation data.

Key Applications:
1. Typology Discovery: Identify distinct "types" of deprivation
2. Transition Analysis: Understand pathways between deprivation types
3. Cycle Detection: Find circular patterns (poverty traps, gentrification loops)
4. Structural Comparison: Compare deprivation structure across time or regions

Mathematical Background:
- Mapper creates a simplicial complex from high-dimensional data
- The complex captures "shape" while enabling visualization
- Based on fiber products from algebraic topology

Key Parameters:
- Filter function: Determines how data is "sliced" (1D or 2D)
- Cover: Overlapping intervals/regions in filter space
- Clustering: How to group points within each slice

References:
- Singh, G., Mémoli, F., & Carlsson, G. (2007). Topological Methods for the
  Analysis of High Dimensional Data Sets and 3D Object Recognition
- Nicolau, M., Levine, A. J., & Carlsson, G. (2011). Topology based data
  analysis identifies a subgroup of breast cancers with a unique mutational profile

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class MapperNode:
    """A node in the Mapper graph."""

    node_id: int
    members: list[int]  # Indices of data points in this node
    interval_index: int  # Which interval(s) this node came from
    centroid: np.ndarray | None = None  # Optional: centroid in feature space
    label: str = ""  # Optional: descriptive label

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass
class MapperEdge:
    """An edge in the Mapper graph."""

    source: int
    target: int
    weight: float = 1.0  # Number of shared members
    shared_members: list[int] = field(default_factory=list)


@dataclass
class MapperGraph:
    """Complete Mapper output."""

    nodes: list[MapperNode]
    edges: list[MapperEdge]
    n_data_points: int
    filter_name: str
    parameters: dict

    def to_networkx(self) -> nx.Graph:
        """Convert to NetworkX graph for analysis and visualization."""
        G = nx.Graph()

        for node in self.nodes:
            G.add_node(
                node.node_id,
                size=node.size,
                members=node.members,
                interval=node.interval_index,
                label=node.label,
            )

        for edge in self.edges:
            G.add_edge(edge.source, edge.target, weight=edge.weight, shared=edge.shared_members)

        return G

    def get_node_by_member(self, member_idx: int) -> list[int]:
        """Find all nodes containing a specific data point."""
        return [n.node_id for n in self.nodes if member_idx in n.members]

    def summary(self) -> dict:
        """Compute summary statistics of the Mapper graph."""
        G = self.to_networkx()

        return {
            "n_nodes": len(self.nodes),
            "n_edges": len(self.edges),
            "n_connected_components": nx.number_connected_components(G),
            "n_points_covered": sum(n.size for n in self.nodes),
            "avg_node_size": np.mean([n.size for n in self.nodes]),
            "max_node_size": max(n.size for n in self.nodes),
            "has_cycles": any(len(c) > 2 for c in nx.cycle_basis(G)),
            "density": nx.density(G),
            "filter": self.filter_name,
            "parameters": self.parameters,
        }


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================


def filter_by_column(data: pd.DataFrame, column: str) -> np.ndarray:
    """Use a single column as filter function."""
    return data[column].values.reshape(-1, 1)


def filter_by_pca(data: pd.DataFrame, n_components: int = 1, feature_columns: list[str] | None = None) -> np.ndarray:
    """Use PCA projection as filter function."""
    if feature_columns:
        X = data[feature_columns].values
    else:
        X = data.select_dtypes(include=[np.number]).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=n_components)
    return pca.fit_transform(X_scaled)


def filter_by_eccentricity(
    data: pd.DataFrame,
    feature_columns: list[str] | None = None,
    metric: str = "euclidean",
) -> np.ndarray:
    """
    Use eccentricity (distance to most different point) as filter.

    Eccentricity often reveals outliers and boundary points.
    """
    if feature_columns:
        X = data[feature_columns].values
    else:
        X = data.select_dtypes(include=[np.number]).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Compute pairwise distances
    dist_matrix = squareform(pdist(X_scaled, metric=metric))

    # Eccentricity = maximum distance to any other point
    eccentricity = dist_matrix.max(axis=1)

    return eccentricity.reshape(-1, 1)


def filter_by_density(
    data: pd.DataFrame,
    feature_columns: list[str] | None = None,
    k: int = 15,
    metric: str = "euclidean",
) -> np.ndarray:
    """
    Use local density as filter function.

    Density = 1 / (average distance to k nearest neighbors)
    High density points are in crowded regions.
    """
    if feature_columns:
        X = data[feature_columns].values
    else:
        X = data.select_dtypes(include=[np.number]).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Compute pairwise distances
    dist_matrix = squareform(pdist(X_scaled, metric=metric))

    # For each point, find k nearest neighbors
    densities = []
    for i in range(len(X_scaled)):
        distances = np.sort(dist_matrix[i])[1 : k + 1]  # Exclude self
        avg_dist = distances.mean()
        density = 1.0 / (avg_dist + 1e-10)
        densities.append(density)

    return np.array(densities).reshape(-1, 1)


def filter_2d(data: pd.DataFrame, column1: str, column2: str) -> np.ndarray:
    """Use two columns as 2D filter function."""
    return data[[column1, column2]].values


# =============================================================================
# COVER CONSTRUCTION
# =============================================================================


def create_1d_cover(filter_values: np.ndarray, n_cubes: int = 10, overlap: float = 0.3) -> list[tuple[float, float]]:
    """
    Create overlapping intervals covering the filter range.

    Args:
        filter_values: 1D array of filter values
        n_cubes: Number of intervals
        overlap: Fraction of overlap (0-1)

    Returns:
        List of (min, max) tuples defining intervals
    """
    f_min, f_max = filter_values.min(), filter_values.max()
    f_range = f_max - f_min

    # Interval width accounting for overlap
    step = f_range / (n_cubes - (n_cubes - 1) * overlap)

    intervals = []
    for i in range(n_cubes):
        start = f_min + i * step * (1 - overlap)
        end = start + step
        intervals.append((start, min(end, f_max + 1e-10)))

    return intervals


def create_2d_cover(
    filter_values: np.ndarray,
    n_cubes: tuple[int, int] = (10, 10),
    overlap: tuple[float, float] = (0.3, 0.3),
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """
    Create overlapping rectangles covering 2D filter space.

    Returns:
        List of ((x_min, x_max), (y_min, y_max)) tuples
    """
    x_intervals = create_1d_cover(filter_values[:, 0], n_cubes[0], overlap[0])
    y_intervals = create_1d_cover(filter_values[:, 1], n_cubes[1], overlap[1])

    rectangles = []
    for x_int in x_intervals:
        for y_int in y_intervals:
            rectangles.append((x_int, y_int))

    return rectangles


# =============================================================================
# CLUSTERING
# =============================================================================


def cluster_dbscan(X: np.ndarray, eps: float | None = None, min_samples: int = 3) -> np.ndarray:
    """Cluster using DBSCAN (handles noise, finds arbitrary shapes)."""
    if eps is None:
        # Auto-compute eps based on average nearest neighbor distance
        if len(X) < 2:
            return np.zeros(len(X), dtype=int)
        from sklearn.neighbors import NearestNeighbors

        nn = NearestNeighbors(n_neighbors=min(min_samples, len(X)))
        nn.fit(X)
        distances, _ = nn.kneighbors(X)
        eps = np.median(distances[:, -1]) * 1.5

    clusterer = DBSCAN(eps=eps, min_samples=min_samples)
    labels = clusterer.fit_predict(X)

    # DBSCAN labels -1 as noise; we reassign each noise point to its own cluster
    n_clusters = labels.max() + 1
    for i, label in enumerate(labels):
        if label == -1:
            labels[i] = n_clusters
            n_clusters += 1

    return labels


def cluster_agglomerative(
    X: np.ndarray,
    n_clusters: int | None = None,
    distance_threshold: float | None = None,
) -> np.ndarray:
    """Cluster using agglomerative (hierarchical) clustering."""
    if len(X) < 2:
        return np.zeros(len(X), dtype=int)

    if n_clusters is None and distance_threshold is None:
        # Auto-determine using silhouette score
        n_clusters = min(3, len(X))

    clusterer = AgglomerativeClustering(
        n_clusters=n_clusters,
        distance_threshold=distance_threshold if n_clusters is None else None,
    )
    return clusterer.fit_predict(X)


def cluster_single_linkage(X: np.ndarray, distance_threshold: float | None = None) -> np.ndarray:
    """Single-linkage clustering (good for detecting connected regions)."""
    if len(X) < 2:
        return np.zeros(len(X), dtype=int)

    if distance_threshold is None:
        # Use median pairwise distance
        dists = pdist(X)
        distance_threshold = np.median(dists) if len(dists) > 0 else 1.0

    clusterer = AgglomerativeClustering(n_clusters=None, distance_threshold=distance_threshold, linkage="single")
    return clusterer.fit_predict(X)


# =============================================================================
# MAIN MAPPER ALGORITHM
# =============================================================================


def compute_mapper(
    data: pd.DataFrame,
    filter_values: np.ndarray,
    feature_columns: list[str] | None = None,
    n_cubes: int = 10,
    overlap: float = 0.3,
    clustering: Literal["dbscan", "agglomerative", "single_linkage"] = "dbscan",
    clustering_params: dict | None = None,
    filter_name: str = "custom",
    min_cluster_size: int = 1,
) -> MapperGraph:
    """
    Compute Mapper graph from tabular data.

    Args:
        data: DataFrame with features and identifiers
        filter_values: Pre-computed filter values (n_samples, 1) or (n_samples, 2)
        feature_columns: Columns to use for clustering (default: all numeric)
        n_cubes: Number of intervals in cover
        overlap: Overlap fraction (0-1)
        clustering: Clustering algorithm
        clustering_params: Additional parameters for clustering
        filter_name: Name of filter for documentation
        min_cluster_size: Minimum points to form a cluster

    Returns:
        MapperGraph with nodes, edges, and metadata

    Example:
        >>> # Filter by overall IMD score, cluster by all domains
        >>> filter_vals = filter_by_column(lsoa_data, 'imd_score')
        >>> graph = compute_mapper(
        ...     lsoa_data,
        ...     filter_vals,
        ...     feature_columns=['income', 'employment', 'education', 'health'],
        ...     n_cubes=15,
        ...     overlap=0.4
        ... )
        >>> print(graph.summary())
    """
    clustering_params = clustering_params or {}

    # Get feature matrix for clustering
    if feature_columns:
        X_features = data[feature_columns].values
    else:
        X_features = data.select_dtypes(include=[np.number]).values

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_features)

    # Determine filter dimensionality
    filter_dim = filter_values.shape[1] if len(filter_values.shape) > 1 else 1
    filter_values = filter_values.reshape(-1, 1) if filter_dim == 1 else filter_values

    # Create cover
    if filter_dim == 1:
        intervals = create_1d_cover(filter_values[:, 0], n_cubes, overlap)
    else:
        intervals = create_2d_cover(filter_values, (n_cubes, n_cubes), (overlap, overlap))

    logger.info(f"Created {len(intervals)} intervals with {overlap * 100:.0f}% overlap")

    # Select clustering function
    cluster_funcs = {
        "dbscan": cluster_dbscan,
        "agglomerative": cluster_agglomerative,
        "single_linkage": cluster_single_linkage,
    }
    cluster_func = cluster_funcs[clustering]

    # For each interval, find points and cluster them
    nodes = []
    node_id = 0
    point_to_nodes: dict[int, list[int]] = {i: [] for i in range(len(data))}

    for interval_idx, interval in enumerate(intervals):
        # Find points in this interval
        if filter_dim == 1:
            low, high = interval
            mask = (filter_values[:, 0] >= low) & (filter_values[:, 0] <= high)
        else:
            (x_low, x_high), (y_low, y_high) = interval
            mask = (
                (filter_values[:, 0] >= x_low)
                & (filter_values[:, 0] <= x_high)
                & (filter_values[:, 1] >= y_low)
                & (filter_values[:, 1] <= y_high)
            )

        indices = np.where(mask)[0]

        if len(indices) < min_cluster_size:
            continue

        # Cluster points in this interval using full feature space
        X_interval = X_scaled[indices]

        if len(indices) == 1:
            cluster_labels = np.array([0])
        else:
            cluster_labels = cluster_func(X_interval, **clustering_params)

        # Create nodes for each cluster
        unique_labels = np.unique(cluster_labels)

        for label in unique_labels:
            cluster_mask = cluster_labels == label
            members = indices[cluster_mask].tolist()

            if len(members) < min_cluster_size:
                continue

            # Compute cluster centroid
            centroid = X_scaled[members].mean(axis=0)

            node = MapperNode(
                node_id=node_id,
                members=members,
                interval_index=interval_idx,
                centroid=centroid,
            )
            nodes.append(node)

            # Track which nodes each point belongs to
            for member in members:
                point_to_nodes[member].append(node_id)

            node_id += 1

    logger.info(f"Created {len(nodes)} nodes")

    # Build edges between nodes that share members
    edges = []
    node_pairs_checked = set()

    for point_idx, node_ids in point_to_nodes.items():
        if len(node_ids) > 1:
            # This point is shared between multiple nodes
            for i, n1 in enumerate(node_ids):
                for n2 in node_ids[i + 1 :]:
                    pair = (min(n1, n2), max(n1, n2))
                    if pair not in node_pairs_checked:
                        node_pairs_checked.add(pair)

    # For each pair, count shared members
    for n1, n2 in node_pairs_checked:
        node1 = nodes[n1]
        node2 = nodes[n2]
        shared = set(node1.members) & set(node2.members)

        if shared:
            edge = MapperEdge(source=n1, target=n2, weight=len(shared), shared_members=list(shared))
            edges.append(edge)

    logger.info(f"Created {len(edges)} edges")

    graph = MapperGraph(
        nodes=nodes,
        edges=edges,
        n_data_points=len(data),
        filter_name=filter_name,
        parameters={
            "n_cubes": n_cubes,
            "overlap": overlap,
            "clustering": clustering,
            "clustering_params": clustering_params,
            "n_features": X_features.shape[1],
        },
    )

    return graph


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================


def find_branches(graph: MapperGraph) -> list[list[int]]:
    """
    Identify linear branches in the Mapper graph.

    Branches often represent "types" or gradual transitions.
    """
    G = graph.to_networkx()

    # Find nodes with degree 1 (branch endpoints) or degree > 2 (branch points)
    endpoints = [n for n in G.nodes() if G.degree(n) == 1]
    branch_points = [n for n in G.nodes() if G.degree(n) > 2]

    branches = []
    visited_edges = set()

    for endpoint in endpoints:
        # Trace from endpoint until we hit another endpoint or branch point
        branch = [endpoint]
        current = endpoint

        while True:
            neighbors = list(G.neighbors(current))

            if not neighbors:
                break

            # Find unvisited neighbor
            next_node = None
            for n in neighbors:
                edge = (min(current, n), max(current, n))
                if edge not in visited_edges:
                    next_node = n
                    visited_edges.add(edge)
                    break

            if next_node is None:
                break

            branch.append(next_node)
            current = next_node

            if current in endpoints or current in branch_points:
                break

        if len(branch) > 1:
            branches.append(branch)

    return branches


def find_loops(graph: MapperGraph) -> list[list[int]]:
    """
    Find cycles in the Mapper graph.

    Loops may indicate:
    - Poverty cycles (feedback loops)
    - Return paths (gentrification → displacement → poverty)
    - Periodic structures
    """
    G = graph.to_networkx()
    return list(nx.cycle_basis(G))


def analyze_branch_characteristics(graph: MapperGraph, data: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """
    Analyze the characteristics of each branch.

    Returns DataFrame with mean feature values for each branch.
    """
    branches = find_branches(graph)

    results = []
    for branch_idx, branch in enumerate(branches):
        # Get all members of this branch
        branch_members = set()
        for node_id in branch:
            node = graph.nodes[node_id]
            branch_members.update(node.members)

        # Compute mean features
        branch_data = data.iloc[list(branch_members)]
        means = branch_data[feature_columns].mean().to_dict()

        means["branch_id"] = branch_idx
        means["branch_length"] = len(branch)
        means["n_members"] = len(branch_members)

        results.append(means)

    return pd.DataFrame(results)


def label_nodes_by_feature(
    graph: MapperGraph, data: pd.DataFrame, label_column: str, aggregation: str = "mode"
) -> MapperGraph:
    """
    Assign labels to nodes based on member characteristics.

    Args:
        graph: MapperGraph to label
        data: Original data
        label_column: Column to use for labeling (e.g., 'region', 'lad_name')
        aggregation: How to aggregate ('mode' for categorical, 'mean' for numeric)

    Returns:
        MapperGraph with node labels filled in
    """
    for node in graph.nodes:
        member_values = data.iloc[node.members][label_column]

        if aggregation == "mode":
            mode_result = member_values.mode()
            label = (
                mode_result.iloc[0]
                if len(mode_result) > 0
                else (str(member_values.iloc[0]) if len(member_values) > 0 else "")
            )
        elif aggregation == "mean":
            label = f"{label_column}={member_values.mean():.2f}"
        else:
            label = str(member_values.iloc[0]) if len(member_values) > 0 else ""

        node.label = str(label)

    return graph


def compute_node_features(graph: MapperGraph, data: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """
    Compute summary features for each Mapper node.

    Returns DataFrame indexed by node_id with mean, std, and member count
    for each feature.
    """
    results = []

    for node in graph.nodes:
        node_data = data.iloc[node.members][feature_columns]

        row = {"node_id": node.node_id, "n_members": node.size}

        for col in feature_columns:
            row[f"{col}_mean"] = node_data[col].mean()
            row[f"{col}_std"] = node_data[col].std()
            row[f"{col}_min"] = node_data[col].min()
            row[f"{col}_max"] = node_data[col].max()

        results.append(row)

    return pd.DataFrame(results)


# =============================================================================
# COMPARISON WITH OTHER METHODS
# =============================================================================


def compare_mapper_to_basins(graph: MapperGraph, basin_labels: np.ndarray) -> dict:
    """
    Compare Mapper nodes to Morse-Smale basin assignments.

    Tests whether Mapper nodes are coherent with respect to basins
    (i.e., do nodes contain members from single basins or multiple?)
    """
    node_basin_entropy = []
    node_dominant_basin = []

    for node in graph.nodes:
        member_basins = basin_labels[node.members]
        unique, counts = np.unique(member_basins, return_counts=True)

        # Entropy of basin distribution
        probs = counts / counts.sum()
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        node_basin_entropy.append(entropy)

        # Dominant basin
        dominant = unique[counts.argmax()]
        node_dominant_basin.append(dominant)

    # Low entropy = nodes are coherent (single basin per node)
    # High entropy = nodes span multiple basins

    return {
        "mean_node_entropy": np.mean(node_basin_entropy),
        "std_node_entropy": np.std(node_basin_entropy),
        "n_pure_nodes": sum(e < 0.5 for e in node_basin_entropy),
        "n_mixed_nodes": sum(e >= 0.5 for e in node_basin_entropy),
        "interpretation": (
            "Low entropy: Mapper nodes align with basins, both capture similar structure"
            if np.mean(node_basin_entropy) < 0.5
            else "High entropy: Mapper nodes cross basin boundaries, revealing different structure"
        ),
    }


# =============================================================================
# VISUALIZATION HELPERS
# =============================================================================


def export_to_json(graph: MapperGraph, filepath: str) -> None:
    """Export Mapper graph to JSON for visualization in D3.js or similar."""
    import json

    data = {
        "nodes": [
            {
                "id": n.node_id,
                "size": n.size,
                "interval": n.interval_index,
                "label": n.label,
            }
            for n in graph.nodes
        ],
        "links": [{"source": e.source, "target": e.target, "weight": e.weight} for e in graph.edges],
        "summary": graph.summary(),
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def plot_mapper_graph(
    graph: MapperGraph,
    node_color_values: np.ndarray | None = None,
    node_size_scale: float = 50,
    colormap: str = "viridis",
    title: str = "Mapper Graph",
) -> None:
    """
    Plot Mapper graph using matplotlib.

    Args:
        graph: MapperGraph to plot
        node_color_values: Optional array of values for coloring nodes
        node_size_scale: Scaling factor for node sizes
        colormap: Matplotlib colormap name
        title: Plot title
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available for plotting")
        return

    G = graph.to_networkx()

    # Compute layout
    pos = nx.spring_layout(G, seed=42, k=2 / np.sqrt(len(G.nodes())))

    # Node sizes based on member count
    node_sizes = [graph.nodes[n].size * node_size_scale for n in G.nodes()]

    # Node colors
    if node_color_values is not None:
        # Average value for each node
        node_colors = []
        for node in graph.nodes:
            avg_val = node_color_values[node.members].mean()
            node_colors.append(avg_val)
    else:
        node_colors = [n.interval_index for n in graph.nodes]

    fig, ax = plt.subplots(figsize=(12, 10))

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.5, ax=ax)

    # Draw nodes
    nodes = nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, cmap=colormap, ax=ax)

    # Add labels
    labels = {n.node_id: n.label if n.label else str(n.node_id) for n in graph.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)

    plt.colorbar(nodes, label="Filter value" if node_color_values is None else "Mean value")
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()

    return fig
