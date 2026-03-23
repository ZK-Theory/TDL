"""Core KeplerMapper wrapper for trajectory embeddings.

Builds a Mapper graph from pre-computed PCA-20D embeddings produced by
the Paper 1 pipeline, with configurable lens functions, cover parameters,
and clustering algorithms.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import MinMaxScaler

try:
    import kmapper as km
except ImportError as exc:
    raise ImportError(
        "trajectory_tda.mapper requires the 'mapper' extra: "
        "pip install 'tdl[mapper]'"
    ) from exc

logger = logging.getLogger(__name__)


def load_embeddings(results_dir: str) -> tuple[np.ndarray, list[list[str]], dict]:
    """Load pre-computed PCA-20D embeddings, trajectories, and metadata
    from P01 results.

    Args:
        results_dir: Path to directory containing P01 results.

    Returns:
        Tuple of (embeddings, trajectories, metadata_dict) where:
            - embeddings: (N, 20) array of PCA-reduced n-gram embeddings
            - trajectories: list of N state-sequence lists
            - metadata_dict: dict with keys 'analysis', 'trajectory_meta', 'gmm'
    """
    rdir = Path(results_dir)

    # Load embeddings
    emb_path = rdir / "embeddings.npy"
    embeddings = np.load(emb_path)
    logger.info("Loaded embeddings: %s from %s", embeddings.shape, emb_path)

    # Load trajectory sequences
    seq_path = rdir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)
    logger.info("Loaded %d trajectory sequences", len(trajectories))

    # Load trajectory metadata
    meta_path = rdir / "01_trajectories.json"
    with open(meta_path) as f:
        trajectory_meta = json.load(f)

    # Load regime analysis
    analysis_path = rdir / "05_analysis.json"
    with open(analysis_path) as f:
        analysis = json.load(f)
    logger.info(
        "Loaded regime analysis: k_optimal=%s",
        analysis.get("regimes", {}).get("k_optimal", "?"),
    )

    # Load fitted GMM
    gmm_path = rdir / "05_gmm.joblib"
    gmm = joblib.load(gmm_path) if gmm_path.exists() else None
    if gmm is not None:
        logger.info("Loaded fitted GMM model")

    metadata = {
        "analysis": analysis,
        "trajectory_meta": trajectory_meta,
        "gmm": gmm,
    }

    return embeddings, trajectories, metadata


def build_mapper_graph(
    embeddings: np.ndarray,
    projection: str = "pca_2d",
    n_cubes: int = 15,
    overlap_frac: float = 0.3,
    clusterer: str = "dbscan",
    clusterer_params: dict | None = None,
    scaler: str = "minmax",
    verbose: int = 1,
) -> tuple[dict, km.KeplerMapper]:
    """Build KeplerMapper graph from pre-computed embeddings.

    Args:
        embeddings: (N, D) point cloud (PCA-20D from P01).
        projection: Lens function. One of "pca_2d", "sum", "l2norm",
            "density", or a callable taking embeddings and returning
            an (N, d) array.
        n_cubes: Number of intervals in each dimension of the cover.
        overlap_frac: Overlap fraction between cover elements in [0, 1).
        clusterer: Clustering algorithm, "dbscan" or "agglomerative".
        clusterer_params: Parameters for the clustering algorithm.
            DBSCAN defaults: {"eps": 0.5, "min_samples": 5}.
            Agglomerative defaults: {"threshold": 1.5}.
        scaler: Scaling for lens values. "minmax" or None.
        verbose: KeplerMapper verbosity level.

    Returns:
        Tuple of (graph, mapper_object) where graph is KeplerMapper's
        graph dict containing 'nodes' and 'links'.
    """
    mapper = km.KeplerMapper(verbose=verbose)

    # Create lens (projection)
    if projection == "pca_2d":
        lens = embeddings[:, :2]
    elif projection == "sum":
        lens = mapper.fit_transform(embeddings, projection="sum")
    elif projection == "l2norm":
        lens = mapper.fit_transform(embeddings, projection="l2norm")
    elif projection == "density":
        from sklearn.neighbors import KernelDensity

        kde = KernelDensity(bandwidth=1.0).fit(embeddings)
        lens = kde.score_samples(embeddings).reshape(-1, 1)
    elif callable(projection):
        lens = projection(embeddings)
    else:
        msg = f"Unknown projection: {projection}"
        raise ValueError(msg)

    logger.info("Lens shape: %s (projection=%s)", lens.shape, projection)

    # Scale lens
    if scaler == "minmax":
        lens = MinMaxScaler().fit_transform(lens)

    # Configure clusterer
    if clusterer_params is None:
        clusterer_params = {}

    if clusterer == "dbscan":
        cl = DBSCAN(
            eps=clusterer_params.get("eps", 0.5),
            min_samples=clusterer_params.get("min_samples", 5),
        )
    elif clusterer == "agglomerative":
        cl = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=clusterer_params.get("threshold", 1.5),
        )
    else:
        msg = f"Unknown clusterer: {clusterer}"
        raise ValueError(msg)

    # Build graph
    graph = mapper.map(
        lens,
        embeddings,
        cover=km.Cover(n_cubes=n_cubes, perc_overlap=overlap_frac),
        clusterer=cl,
    )

    summary = mapper_graph_summary(graph)
    logger.info(
        "Mapper graph: %d nodes, %d edges, %d components, coverage=%.2f",
        summary["n_nodes"],
        summary["n_edges"],
        summary["n_connected_components"],
        summary["coverage"],
    )

    return graph, mapper


def mapper_graph_summary(graph: dict) -> dict:
    """Extract summary statistics from a Mapper graph.

    Args:
        graph: KeplerMapper graph dict with 'nodes' and 'links' keys.

    Returns:
        Dict with keys: n_nodes, n_edges, mean_node_size, median_node_size,
        min_node_size, max_node_size, n_covered, coverage, n_connected_components.
    """
    nodes = graph.get("nodes", {})
    edges = graph.get("links", {})

    n_nodes = len(nodes)
    # KeplerMapper stores each undirected edge once (source -> [targets]),
    # so the sum of neighbour-list lengths equals the edge count directly.
    n_edges = sum(len(v) for v in edges.values())
    node_sizes = [len(members) for members in nodes.values()]

    # Coverage: fraction of data points in at least one node
    all_members: set[int] = set()
    for members in nodes.values():
        all_members.update(members)

    # Estimate total data points from max index
    if nodes:
        max_idx = max(max(m) for m in nodes.values()) + 1
    else:
        max_idx = 1

    return {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "mean_node_size": float(np.mean(node_sizes)) if node_sizes else 0,
        "median_node_size": float(np.median(node_sizes)) if node_sizes else 0,
        "min_node_size": int(min(node_sizes)) if node_sizes else 0,
        "max_node_size": int(max(node_sizes)) if node_sizes else 0,
        "n_covered": len(all_members),
        "coverage": len(all_members) / max(1, max_idx) if nodes else 0,
        "n_connected_components": _count_components(graph),
    }


def _count_components(graph: dict) -> int:
    """Count connected components via BFS on the Mapper graph.

    Args:
        graph: KeplerMapper graph dict with 'nodes' and 'links' keys.

    Returns:
        Number of connected components.
    """
    nodes = list(graph.get("nodes", {}).keys())
    edges = graph.get("links", {})

    if not nodes:
        return 0

    # Build adjacency list
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for node_id, neighbors in edges.items():
        if node_id in adj:
            for nb in neighbors:
                adj[node_id].add(nb)
                if nb in adj:
                    adj[nb].add(node_id)

    visited: set[str] = set()
    n_components = 0

    for start in nodes:
        if start in visited:
            continue
        n_components += 1
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for nb in adj.get(current, []):
                if nb not in visited:
                    queue.append(nb)

    return n_components


def save_mapper_graph(
    graph: dict,
    output_path: str,
    mapper_obj: km.KeplerMapper | None = None,
    color_values: np.ndarray | None = None,
) -> None:
    """Save Mapper graph as JSON and optionally as HTML visualization.

    The JSON file contains the graph structure (nodes as index lists,
    edges as adjacency lists) plus summary statistics.  If a KeplerMapper
    object is provided, an HTML visualization is also generated alongside
    the JSON file.

    Args:
        graph: KeplerMapper graph dict with 'nodes' and 'links' keys.
        output_path: Destination path for the JSON file.  The HTML file
            (if generated) is written to the same directory with a
            ``.html`` suffix.
        mapper_obj: Optional KeplerMapper instance used for HTML export.
        color_values: Optional (N,) array used to color the HTML graph.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Serialise graph to JSON-friendly format
    def _convert(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        return obj

    serialisable: dict[str, Any] = {
        "nodes": {k: list(v) for k, v in graph.get("nodes", {}).items()},
        "links": {k: list(v) for k, v in graph.get("links", {}).items()},
        "summary": mapper_graph_summary(graph),
    }

    with open(out, "w") as f:
        json.dump(serialisable, f, indent=2, default=_convert)
    logger.info("Saved Mapper graph JSON to %s", out)

    # Optional HTML visualization
    if mapper_obj is not None:
        html_path = out.with_suffix(".html")
        try:
            mapper_obj.visualize(
                graph,
                path_html=str(html_path),
                title="KeplerMapper Visualization",
                color_values=color_values,
            )
            logger.info("Saved Mapper HTML visualization to %s", html_path)
        except Exception:
            logger.warning("HTML visualization failed", exc_info=True)
