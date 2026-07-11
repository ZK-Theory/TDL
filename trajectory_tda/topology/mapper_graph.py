# Research context: TDA-Research/00-Meta/Discovery/spike-06-mapper-reeb-fallback-result-2026-07-10.md
# Purpose: Deterministic Mapper graph construction for Discovery Spike 6
#   (Mapper/Reeb fallback): equal-length overlapping interval cover on a 2D
#   filter, per-bin DBSCAN with data-driven eps, nodes = clusters, edges =
#   shared membership. Toy/feasibility code path — no paper results produced
#   directly.
"""Deterministic Mapper graph for a 2D filter.

Cover: each filter dimension is split into ``n_intervals`` equal-length
intervals spanning the filter range with fractional ``overlap``; 2D bins are
the product. Within each non-empty bin, points are clustered in the ORIGINAL
space ``X`` by DBSCAN with ``eps`` = the median 5th-nearest-neighbour distance
inside the bin (bins with fewer than 6 points yield no clusters; DBSCAN noise
points are dropped). Each cluster becomes a node; nodes are connected when
their point memberships overlap. Everything is deterministic given the inputs.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
from numpy.typing import NDArray
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors


def _cover_intervals(values: NDArray[np.float64], n_intervals: int, overlap: float) -> list[tuple[float, float]]:
    """Equal-length overlapping intervals spanning [min, max] of ``values``."""
    lo, hi = float(values.min()), float(values.max())
    span = hi - lo
    if span == 0:
        return [(lo, hi)]
    length = span / (n_intervals - (n_intervals - 1) * overlap)
    step = length * (1 - overlap)
    return [(lo + i * step, lo + i * step + length) for i in range(n_intervals)]


def mapper_graph(
    X: NDArray[np.float64],
    filter_values: NDArray[np.float64],
    n_intervals: int,
    overlap: float,
    min_samples: int,
) -> nx.Graph:
    """Deterministic Mapper graph on a 2D filter.

    Args:
        X: (n, d) points clustered in their original space.
        filter_values: (n, 2) filter coordinates.
        n_intervals: Intervals per filter dimension.
        overlap: Fractional interval overlap in (0, 1).
        min_samples: DBSCAN ``min_samples``; also sets the k = 5th-NN eps rule.

    Returns:
        networkx.Graph whose nodes carry a ``members`` attribute (frozenset of
        row indices); edges connect nodes with overlapping membership.
    """
    X = np.asarray(X, dtype=np.float64)
    f = np.asarray(filter_values, dtype=np.float64)
    if f.ndim != 2 or f.shape[1] != 2:
        msg = f"filter_values must be (n, 2), got {f.shape}"
        raise ValueError(msg)
    if len(X) != len(f):
        msg = f"X ({len(X)}) and filter_values ({len(f)}) length mismatch"
        raise ValueError(msg)

    cover_x = _cover_intervals(f[:, 0], n_intervals, overlap)
    cover_y = _cover_intervals(f[:, 1], n_intervals, overlap)

    graph = nx.Graph()
    node_members: list[frozenset[int]] = []
    for x_lo, x_hi in cover_x:
        in_x = (f[:, 0] >= x_lo) & (f[:, 0] <= x_hi)
        for y_lo, y_hi in cover_y:
            idx = np.flatnonzero(in_x & (f[:, 1] >= y_lo) & (f[:, 1] <= y_hi))
            if len(idx) < min_samples + 1:
                continue
            sub = X[idx]
            k = min(5, len(sub) - 1)
            nn = NearestNeighbors(n_neighbors=k + 1).fit(sub)
            dists, _ = nn.kneighbors(sub)
            eps = float(np.median(dists[:, k]))
            if eps <= 0:
                eps = 1e-12
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(sub)
            for label in np.unique(labels):
                if label < 0:
                    continue  # noise dropped
                members = frozenset(int(i) for i in idx[labels == label])
                node_id = len(node_members)
                node_members.append(members)
                graph.add_node(node_id, members=members)

    for i in range(len(node_members)):
        for j in range(i + 1, len(node_members)):
            if node_members[i] & node_members[j]:
                graph.add_edge(i, j)
    return graph


def mapper_statistics(graph: nx.Graph) -> dict[str, float]:
    """Spike-6 summary statistics of a Mapper graph.

    Returns:
        Dict with n_nodes, n_edges, beta0, beta1 (= E − V + beta0),
        largest_component_fraction, mean_degree, degree_gini.
    """
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    if n_nodes == 0:
        return {
            "n_nodes": 0,
            "n_edges": 0,
            "beta0": 0,
            "beta1": 0,
            "largest_component_fraction": 0.0,
            "mean_degree": 0.0,
            "degree_gini": 0.0,
        }
    components = list(nx.connected_components(graph))
    beta0 = len(components)
    beta1 = n_edges - n_nodes + beta0
    largest = max(len(c) for c in components) / n_nodes
    degrees = np.asarray([d for _, d in graph.degree()], dtype=np.float64)
    mean_degree = float(degrees.mean())
    sorted_d = np.sort(degrees)
    n = len(sorted_d)
    if sorted_d.sum() == 0:
        gini = 0.0
    else:
        weighted_sum = float(np.sum(np.arange(1, n + 1) * sorted_d))
        gini = float(2 * weighted_sum / (n * sorted_d.sum()) - (n + 1) / n)
    return {
        "n_nodes": int(n_nodes),
        "n_edges": int(n_edges),
        "beta0": int(beta0),
        "beta1": int(beta1),
        "largest_component_fraction": float(largest),
        "mean_degree": mean_degree,
        "degree_gini": gini,
    }
