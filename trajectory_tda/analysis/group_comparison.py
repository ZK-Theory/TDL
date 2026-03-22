"""
Group comparison: test whether trajectory clouds differ topologically by group.

Stratifies by parental class, gender, birth cohort, etc. and compares
per-stratum persistence diagrams using Wasserstein distances and
persistence landscape statistics.
"""

from __future__ import annotations

import logging
from itertools import combinations

import numpy as np

from poverty_tda.topology.multidim_ph import (
    compute_rips_ph,
    persistence_summary,
)
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks
from trajectory_tda.topology.vectorisation import (
    persistence_landscape,
    wasserstein_distance,
)

logger = logging.getLogger(__name__)


def _compute_stratum_ph(
    embeddings: np.ndarray,
    max_dim: int = 1,
    n_landmarks: int = 2000,
    seed: int = 42,
):
    """Compute PH for a single stratum (subsample if needed)."""
    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)

    if actual_lm < n:
        _, landmarks = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        landmarks = embeddings

    return compute_rips_ph(landmarks, max_dim=max_dim)


def compare_groups(
    embeddings: np.ndarray,
    group_labels: np.ndarray,
    trajectories: list[list[str]] | None = None,
    max_dim: int = 1,
    n_landmarks: int = 2000,
    n_permutations: int = 100,
    seed: int = 42,
) -> dict:
    """Compare topological structure across groups.

    Args:
        embeddings: (N, K) trajectory embeddings
        group_labels: (N,) group assignment per trajectory
        trajectories: Raw state sequences (optional, for characterisation)
        max_dim: Maximum homology dimension
        n_landmarks: Landmarks per stratum
        n_permutations: Permutations for significance testing
        seed: Random seed

    Returns:
        Dict with:
            - per_group: PH summaries per group
            - pairwise_wasserstein: Wasserstein distances between all pairs
            - pairwise_p_values: permutation p-values for each pair
            - landscape_stats: per-group landscape integrals
    """
    unique_groups = np.unique(group_labels)
    n_groups = len(unique_groups)
    logger.info(f"Group comparison: {n_groups} groups, {len(embeddings)} total points")

    # Compute PH per group
    group_ph = {}
    group_summaries = {}
    group_indices = {}

    for g in unique_groups:
        mask = group_labels == g
        g_embeddings = embeddings[mask]
        g_idx = np.where(mask)[0]
        group_indices[g] = g_idx

        if len(g_embeddings) < 10:
            logger.warning(f"  Group '{g}': only {len(g_embeddings)} points, skipping")
            continue

        ph = _compute_stratum_ph(g_embeddings, max_dim, n_landmarks, seed)
        group_ph[g] = ph
        s = persistence_summary(ph)
        group_summaries[g] = {k: {kk: vv for kk, vv in v.items() if kk != "features"} for k, v in s.items()}

        logger.info(
            f"  Group '{g}': n={len(g_embeddings)}, "
            f"H0={s.get('H0', {}).get('n_finite', 0)} features, "
            f"H1={s.get('H1', {}).get('n_finite', 0)} features"
        )

    # Pairwise Wasserstein distances
    valid_groups = list(group_ph.keys())
    pairwise_wass = {}
    for g1, g2 in combinations(valid_groups, 2):
        for dim in range(max_dim + 1):
            key = f"H{dim}"
            dist = wasserstein_distance(group_ph[g1], group_ph[g2], dim=dim)
            pairwise_wass[(str(g1), str(g2), key)] = float(dist)
            logger.info(f"  W({g1}, {g2}) {key} = {dist:.4f}")

    # Permutation test for pairwise significance
    pairwise_pvals = {}
    if n_permutations > 0 and len(valid_groups) >= 2:
        rng = np.random.RandomState(seed)
        for g1, g2 in combinations(valid_groups, 2):
            idx1 = group_indices[g1]
            idx2 = group_indices[g2]
            combined_idx = np.concatenate([idx1, idx2])
            n1 = len(idx1)

            for dim in range(max_dim + 1):
                key = f"H{dim}"
                obs_dist = pairwise_wass.get((str(g1), str(g2), key), 0)

                null_dists = []
                for _ in range(n_permutations):
                    perm = rng.permutation(len(combined_idx))
                    perm_idx1 = combined_idx[perm[:n1]]
                    perm_idx2 = combined_idx[perm[n1:]]

                    ph_perm1 = _compute_stratum_ph(embeddings[perm_idx1], max_dim, n_landmarks, seed)
                    ph_perm2 = _compute_stratum_ph(embeddings[perm_idx2], max_dim, n_landmarks, seed)
                    null_dist = wasserstein_distance(ph_perm1, ph_perm2, dim=dim)
                    null_dists.append(null_dist)

                null_arr = np.array(null_dists)
                p_val = float(np.mean(null_arr >= obs_dist))
                pairwise_pvals[(str(g1), str(g2), key)] = {
                    "observed": obs_dist,
                    "null_mean": float(null_arr.mean()),
                    "p_value": p_val,
                    "significant_at_005": p_val < 0.05,
                }
                logger.info(f"  Perm test ({g1} vs {g2}) {key}: p={p_val:.4f}")

    # Landscape statistics per group
    landscape_stats = {}
    for g in valid_groups:
        for dim in range(max_dim + 1):
            _, landscapes = persistence_landscape(group_ph[g], dim=dim, k_max=3, n_points=100)
            # Integral of first landscape (total topological significance)
            l1_integral = float(np.trapz(landscapes[0]))
            landscape_stats[(str(g), f"H{dim}")] = {
                "l1_integral": l1_integral,
                "l1_max": float(landscapes[0].max()),
            }

    return {
        "per_group": group_summaries,
        "pairwise_wasserstein": pairwise_wass,
        "pairwise_p_values": pairwise_pvals,
        "landscape_stats": landscape_stats,
        "n_groups": n_groups,
        "group_sizes": {str(g): len(idx) for g, idx in group_indices.items()},
    }
