"""Grid search for Mapper hyperparameters.

Evaluates Mapper graph quality across combinations of cover resolution,
overlap fraction, and lens function to identify parameter regimes that
produce informative topological summaries.
"""

from __future__ import annotations

import logging
from itertools import product

import numpy as np

from trajectory_tda.mapper.mapper_pipeline import (
    build_mapper_graph,
    mapper_graph_summary,
)

logger = logging.getLogger(__name__)

_DEFAULT_N_CUBES = [10, 15, 20, 25, 30]
_DEFAULT_OVERLAPS = [0.2, 0.3, 0.4, 0.5]
_DEFAULT_PROJECTIONS = ["pca_2d", "l2norm"]


def parameter_grid_search(
    embeddings: np.ndarray,
    n_cubes_range: list[int] | None = None,
    overlap_range: list[float] | None = None,
    projections: list[str] | None = None,
    n_jobs: int = 1,
) -> dict:
    """Search over Mapper hyperparameters and collect graph statistics.

    Args:
        embeddings: (N, D) point cloud to build Mapper graphs from.
        n_cubes_range: List of n_cubes values to try.
            Default: [10, 15, 20, 25, 30].
        overlap_range: List of overlap fractions to try.
            Default: [0.2, 0.3, 0.4, 0.5].
        projections: List of projection/lens names to try.
            Default: ["pca_2d", "l2norm"].
        n_jobs: Number of parallel jobs (reserved for future use;
            currently runs sequentially).

    Returns:
        Dict with keys:
            - 'results': list of dicts, each with 'params' and 'summary'
            - 'best': params dict for configuration with most nodes
            - 'n_evaluated': total number of configurations tested
    """
    if n_cubes_range is None:
        n_cubes_range = _DEFAULT_N_CUBES
    if overlap_range is None:
        overlap_range = _DEFAULT_OVERLAPS
    if projections is None:
        projections = _DEFAULT_PROJECTIONS

    configs = list(product(projections, n_cubes_range, overlap_range))
    logger.info("Parameter search: %d configurations to evaluate", len(configs))

    results = []
    best_score = -1
    best_params: dict = {}

    for i, (proj, nc, ov) in enumerate(configs):
        params = {"projection": proj, "n_cubes": nc, "overlap_frac": ov}
        try:
            graph, _ = build_mapper_graph(
                embeddings,
                projection=proj,
                n_cubes=nc,
                overlap_frac=ov,
                verbose=0,
            )
            summary = mapper_graph_summary(graph)
            results.append({"params": params, "summary": summary})

            # Score: prefer graphs with many nodes and good coverage
            score = summary["n_nodes"] * summary["coverage"]
            if score > best_score:
                best_score = score
                best_params = params

            if (i + 1) % 10 == 0:
                logger.info(
                    "  [%d/%d] proj=%s n_cubes=%d overlap=%.1f -> %d nodes, %d edges",
                    i + 1,
                    len(configs),
                    proj,
                    nc,
                    ov,
                    summary["n_nodes"],
                    summary["n_edges"],
                )
        except Exception:
            logger.warning("Failed for params %s", params, exc_info=True)
            results.append({"params": params, "summary": None})

    logger.info(
        "Parameter search complete: %d/%d succeeded, best=%s",
        sum(1 for r in results if r["summary"] is not None),
        len(configs),
        best_params,
    )

    return {
        "results": results,
        "best": best_params,
        "n_evaluated": len(configs),
    }


def mapper_parameter_search(
    embeddings: np.ndarray,
    n_cubes_range: list[int] | None = None,
    overlap_range: list[float] | None = None,
    projection: str = "pca_2d",
    clusterer: str = "dbscan",
) -> dict:
    """Grid search over Mapper hyperparameters.

    For each (n_cubes, overlap) pair, builds a Mapper graph and computes
    summary statistics including node/edge counts, connected components,
    mean node size, and point coverage.

    Args:
        embeddings: (N, D) point cloud to build Mapper graphs from.
        n_cubes_range: List of n_cubes values to try.
            Default: [10, 15, 20, 25].
        overlap_range: List of overlap fractions to try.
            Default: [0.2, 0.3, 0.4, 0.5].
        projection: Lens function name for all configurations.
        clusterer: Clustering algorithm name for all configurations.

    Returns:
        Dict with keys:
            - 'results': list of dicts with n_cubes, overlap_frac, n_nodes,
              n_edges, n_components, mean_node_size, coverage.
            - 'best_by_coverage': params dict for config with highest coverage.
            - 'best_by_components': params dict for config with fewest
              connected components (most connected graph).
    """
    if n_cubes_range is None:
        n_cubes_range = [10, 15, 20, 25]
    if overlap_range is None:
        overlap_range = [0.2, 0.3, 0.4, 0.5]

    configs = list(product(n_cubes_range, overlap_range))
    logger.info("mapper_parameter_search: %d configurations to evaluate", len(configs))

    results = []
    best_coverage = -1.0
    best_coverage_params: dict = {}
    best_components = float("inf")
    best_components_params: dict = {}

    for i, (nc, ov) in enumerate(configs):
        try:
            graph, _ = build_mapper_graph(
                embeddings,
                projection=projection,
                n_cubes=nc,
                overlap_frac=ov,
                clusterer=clusterer,
                verbose=0,
            )
            summary = mapper_graph_summary(graph)
            entry = {
                "n_cubes": nc,
                "overlap_frac": ov,
                "n_nodes": summary["n_nodes"],
                "n_edges": summary["n_edges"],
                "n_components": summary["n_connected_components"],
                "mean_node_size": summary["mean_node_size"],
                "coverage": summary["coverage"],
            }
            results.append(entry)

            if summary["coverage"] > best_coverage:
                best_coverage = summary["coverage"]
                best_coverage_params = {"n_cubes": nc, "overlap_frac": ov}

            if summary["n_connected_components"] < best_components:
                best_components = summary["n_connected_components"]
                best_components_params = {"n_cubes": nc, "overlap_frac": ov}

            if (i + 1) % 5 == 0:
                logger.info(
                    "  [%d/%d] n_cubes=%d overlap=%.1f -> %d nodes, %d edges, %d components",
                    i + 1,
                    len(configs),
                    nc,
                    ov,
                    summary["n_nodes"],
                    summary["n_edges"],
                    summary["n_connected_components"],
                )
        except Exception:
            logger.warning("Failed for n_cubes=%d, overlap=%.2f", nc, ov, exc_info=True)
            results.append(
                {
                    "n_cubes": nc,
                    "overlap_frac": ov,
                    "n_nodes": 0,
                    "n_edges": 0,
                    "n_components": 0,
                    "mean_node_size": 0.0,
                    "coverage": 0.0,
                }
            )

    logger.info(
        "mapper_parameter_search complete: %d configs, best_coverage=%s, best_components=%s",
        len(configs),
        best_coverage_params,
        best_components_params,
    )

    return {
        "results": results,
        "best_by_coverage": best_coverage_params,
        "best_by_components": best_components_params,
    }
