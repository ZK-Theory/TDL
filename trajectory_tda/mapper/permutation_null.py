"""Permutation null tests for Mapper sub-regime structure.

Tests whether the observed number of sub-regime nodes (nodes whose
outcome mean deviates from the regime mean by more than *threshold_std*
standard deviations) exceeds what would be expected under a null model
that shuffles regime labels.

Two null strategies:

1. **regime_shuffle**: Permute regime labels across all trajectories,
   rebuild the Mapper graph, and recount sub-regime nodes. This tests
   whether the observed sub-regime count reflects genuine geometric
   correspondence between regimes and local Mapper structure.

2. **within_node_shuffle**: Fix the Mapper graph, permute outcome values
   within each regime, and recount sub-regime nodes. This tests whether
   within-regime heterogeneity on the outcome variable is spatially
   structured (concentrated in specific nodes) or randomly distributed.

Both use joblib parallelisation following the pattern in
``trajectory_tda.topology.permutation_nulls``.
"""

from __future__ import annotations

import logging

import numpy as np
from joblib import Parallel, delayed
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _single_regime_shuffle_perm(
    embeddings: NDArray[np.float64],
    regime_labels: NDArray[np.int64],
    outcome_values: NDArray[np.float64],
    n_regimes: int,
    build_kwargs: dict,
    threshold_std: float,
    seed: int,
) -> int:
    """Run one permutation: shuffle regime labels, build Mapper, count sub-regime nodes."""
    from trajectory_tda.mapper.mapper_pipeline import build_mapper_graph
    from trajectory_tda.mapper.validation import identify_subregime_structure

    rng = np.random.RandomState(seed)
    shuffled_labels = regime_labels.copy()
    rng.shuffle(shuffled_labels)

    graph, _ = build_mapper_graph(embeddings, verbose=0, **build_kwargs)
    result = identify_subregime_structure(graph, shuffled_labels, outcome_values, threshold_std=threshold_std)
    return result["n_total"]


def _single_within_node_shuffle_perm(
    graph: dict,
    regime_labels: NDArray[np.int64],
    outcome_values: NDArray[np.float64],
    threshold_std: float,
    seed: int,
) -> int:
    """Run one permutation: shuffle outcomes within each regime, recount sub-regime nodes."""
    from trajectory_tda.mapper.validation import identify_subregime_structure

    rng = np.random.RandomState(seed)
    shuffled_outcomes = outcome_values.copy()

    unique_regimes = np.unique(regime_labels)
    for r in unique_regimes:
        mask = regime_labels == r
        indices = np.where(mask)[0]
        perm = rng.permutation(len(indices))
        shuffled_outcomes[indices] = outcome_values[indices[perm]]

    result = identify_subregime_structure(graph, regime_labels, shuffled_outcomes, threshold_std=threshold_std)
    return result["n_total"]


def regime_shuffle_null(
    embeddings: NDArray[np.float64],
    regime_labels: NDArray[np.int64],
    outcome_values: NDArray[np.float64],
    n_regimes: int = 7,
    n_perms: int = 100,
    threshold_std: float = 1.0,
    build_kwargs: dict | None = None,
    n_jobs: int = -1,
    random_seed: int = 42,
) -> dict:
    """Permutation test: shuffle regime labels and recompute sub-regime count.

    Args:
        embeddings: (N, D) point cloud.
        regime_labels: (N,) integer regime labels.
        outcome_values: (N,) outcome variable (e.g. PC1).
        n_regimes: Number of regimes.
        n_perms: Number of permutations.
        threshold_std: Z-score threshold for sub-regime detection.
        build_kwargs: Arguments for ``build_mapper_graph`` (projection,
            n_cubes, overlap_frac, clusterer, clusterer_params).
        n_jobs: Parallelism level for joblib (-1 = all cores).
        random_seed: Base seed for reproducibility.

    Returns:
        Dict with observed count, null distribution, p-value, and summary.
    """
    from trajectory_tda.mapper.mapper_pipeline import build_mapper_graph
    from trajectory_tda.mapper.validation import identify_subregime_structure

    if build_kwargs is None:
        build_kwargs = {
            "projection": "pca_2d",
            "n_cubes": 30,
            "overlap_frac": 0.5,
            "clusterer": "dbscan",
            "clusterer_params": {"eps": 0.5, "min_samples": 5},
        }

    # Observed count
    graph, _ = build_mapper_graph(embeddings, verbose=0, **build_kwargs)
    observed = identify_subregime_structure(graph, regime_labels, outcome_values, threshold_std=threshold_std)
    observed_count = observed["n_total"]

    logger.info("Observed sub-regime count: %d (threshold=%.1f)", observed_count, threshold_std)

    # Null distribution
    seeds = [random_seed + i for i in range(n_perms)]
    null_counts = Parallel(n_jobs=n_jobs, verbose=5)(
        delayed(_single_regime_shuffle_perm)(
            embeddings,
            regime_labels,
            outcome_values,
            n_regimes,
            build_kwargs,
            threshold_std,
            s,
        )
        for s in seeds
    )

    null_arr = np.array(null_counts, dtype=np.float64)
    p_value = float(np.mean(null_arr >= observed_count))

    logger.info(
        "Regime-shuffle null: observed=%d, null_mean=%.1f (sd=%.1f), p=%.4f",
        observed_count,
        null_arr.mean(),
        null_arr.std(),
        p_value,
    )

    return {
        "test": "regime_shuffle",
        "observed": observed_count,
        "null_mean": float(null_arr.mean()),
        "null_std": float(null_arr.std()),
        "null_min": int(null_arr.min()),
        "null_max": int(null_arr.max()),
        "p_value": p_value,
        "n_perms": n_perms,
        "threshold_std": threshold_std,
        "null_distribution": null_arr.tolist(),
    }


def within_node_shuffle_null(
    graph: dict,
    regime_labels: NDArray[np.int64],
    outcome_values: NDArray[np.float64],
    n_perms: int = 100,
    threshold_std: float = 1.0,
    n_jobs: int = -1,
    random_seed: int = 42,
) -> dict:
    """Permutation test: shuffle outcomes within regimes, recount sub-regime nodes.

    This fixes the Mapper graph and tests whether within-regime outcome
    variation is *spatially structured* (concentrated in specific nodes)
    or randomly distributed across nodes of the same regime.

    Args:
        graph: Pre-built KeplerMapper graph dict.
        regime_labels: (N,) integer regime labels.
        outcome_values: (N,) outcome variable.
        n_perms: Number of permutations.
        threshold_std: Z-score threshold for sub-regime detection.
        n_jobs: Parallelism level for joblib.
        random_seed: Base seed.

    Returns:
        Dict with observed count, null distribution, p-value.
    """
    from trajectory_tda.mapper.validation import identify_subregime_structure

    # Observed
    observed = identify_subregime_structure(graph, regime_labels, outcome_values, threshold_std=threshold_std)
    observed_count = observed["n_total"]

    # Null
    seeds = [random_seed + i for i in range(n_perms)]
    null_counts = Parallel(n_jobs=n_jobs, verbose=5)(
        delayed(_single_within_node_shuffle_perm)(graph, regime_labels, outcome_values, threshold_std, s) for s in seeds
    )

    null_arr = np.array(null_counts, dtype=np.float64)
    p_value = float(np.mean(null_arr >= observed_count))

    logger.info(
        "Within-node shuffle null: observed=%d, null_mean=%.1f (sd=%.1f), p=%.4f",
        observed_count,
        null_arr.mean(),
        null_arr.std(),
        p_value,
    )

    return {
        "test": "within_node_shuffle",
        "observed": observed_count,
        "null_mean": float(null_arr.mean()),
        "null_std": float(null_arr.std()),
        "null_min": int(null_arr.min()),
        "null_max": int(null_arr.max()),
        "p_value": p_value,
        "n_perms": n_perms,
        "threshold_std": threshold_std,
        "null_distribution": null_arr.tolist(),
    }
