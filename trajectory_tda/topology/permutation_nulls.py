"""
Trajectory-aware permutation null models for topological significance testing.

Four null types that progressively test different aspects of trajectory structure:

1. label_shuffle:  Permute trajectory→embedding assignments
2. cohort_shuffle: Permute within birth-cohort bins
3. order_shuffle:  Permute temporal order within each trajectory (preserves unigrams)
4. markov:         Generate from fitted Markov chain (preserves transition matrix)

All nulls use joblib parallelisation for the 1000-permutation regime.
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
from joblib import Parallel, delayed

from poverty_tda.topology.multidim_ph import (
    compute_rips_ph,
    persistence_summary,
)
from trajectory_tda.embedding.ngram_embed import STATES, ngram_embed
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Null model generators
# ─────────────────────────────────────────────────────────────────────


def _label_shuffle(
    embeddings: np.ndarray,
    rng: np.random.RandomState,
) -> np.ndarray:
    """Randomly permute rows of the embedding matrix.

    Preserves the set of embeddings but destroys any group-to-trajectory
    correspondence.
    """
    perm = rng.permutation(embeddings.shape[0])
    return embeddings[perm]


def _cohort_shuffle(
    embeddings: np.ndarray,
    metadata: dict,
    rng: np.random.RandomState,
) -> np.ndarray:
    """Permute embeddings within cohort bins.

    Preserves within-cohort structure, destroys between-cohort assignment.
    Requires 'cohort' in metadata.
    """
    cohorts = metadata.get("cohort")
    if cohorts is None:
        logger.warning("No cohort info, falling back to label_shuffle")
        return _label_shuffle(embeddings, rng)

    result = embeddings.copy()
    unique_cohorts = np.unique(cohorts)
    for c in unique_cohorts:
        mask = cohorts == c
        indices = np.where(mask)[0]
        perm = rng.permutation(len(indices))
        result[indices] = embeddings[indices[perm]]

    return result


def _order_shuffle(
    trajectories: list[list[str]],
    rng: np.random.RandomState,
    embed_kwargs: dict | None = None,
) -> np.ndarray:
    """Permute temporal order within each trajectory, then re-embed.

    Preserves state frequencies (unigrams) but destroys temporal order
    (bigrams). Tests whether transitions carry topological signal beyond
    state frequencies alone.
    """
    shuffled = []
    for traj in trajectories:
        perm = rng.permutation(len(traj))
        shuffled.append([traj[i] for i in perm])

    kwargs = embed_kwargs or {}
    embeddings, _ = ngram_embed(shuffled, **kwargs)
    return embeddings


def _markov_shuffle(
    trajectories: list[list[str]],
    rng: np.random.RandomState,
    markov_order: int = 1,
    embed_kwargs: dict | None = None,
) -> np.ndarray:
    """Generate synthetic trajectories from fitted Markov chain, then embed.

    Estimates the transition matrix (or higher-order) from all trajectories,
    then generates synthetic trajectories of the same lengths. Tests whether
    observed topology exceeds what a memoryless process produces.
    """
    state_to_idx = {s: i for i, s in enumerate(STATES)}
    n_states = len(STATES)

    if markov_order == 1:
        # Estimate first-order transition matrix
        tm = np.zeros((n_states, n_states), dtype=np.float64)
        initial_counts = np.zeros(n_states, dtype=np.float64)

        for traj in trajectories:
            if len(traj) == 0:
                continue
            s0 = state_to_idx.get(traj[0])
            if s0 is not None:
                initial_counts[s0] += 1
            for t in range(len(traj) - 1):
                i = state_to_idx.get(traj[t])
                j = state_to_idx.get(traj[t + 1])
                if i is not None and j is not None:
                    tm[i, j] += 1

        # Normalise
        row_sums = tm.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # avoid division by zero
        tm /= row_sums

        init_sum = initial_counts.sum()
        if init_sum > 0:
            initial_probs = initial_counts / init_sum
        else:
            initial_probs = np.ones(n_states) / n_states

        # Generate synthetic trajectories
        synthetic = []
        for traj in trajectories:
            length = len(traj)
            synth = []
            current = rng.choice(n_states, p=initial_probs)
            synth.append(STATES[current])
            for _ in range(length - 1):
                current = rng.choice(n_states, p=tm[current])
                synth.append(STATES[current])
            synthetic.append(synth)

    elif markov_order == 2:
        # Second-order: condition on (s_{t-1}, s_t)
        initial_counts = np.zeros(n_states, dtype=np.float64)
        bigram_counts: dict[tuple[int, int], np.ndarray] = {}

        for traj in trajectories:
            if len(traj) == 0:
                continue
            s0 = state_to_idx.get(traj[0])
            if s0 is not None:
                initial_counts[s0] += 1
            for t in range(len(traj) - 2):
                i = state_to_idx.get(traj[t])
                j = state_to_idx.get(traj[t + 1])
                k = state_to_idx.get(traj[t + 2])
                if i is not None and j is not None and k is not None:
                    key = (i, j)
                    if key not in bigram_counts:
                        bigram_counts[key] = np.zeros(n_states)
                    bigram_counts[key][k] += 1

        # Normalise
        bigram_probs = {}
        for key, counts in bigram_counts.items():
            total = counts.sum()
            if total > 0:
                bigram_probs[key] = counts / total
            else:
                bigram_probs[key] = np.ones(n_states) / n_states

        init_sum = initial_counts.sum()
        initial_probs = initial_counts / init_sum if init_sum > 0 else np.ones(n_states) / n_states

        # First-order fallback for unseen bigrams
        tm_fallback = np.zeros((n_states, n_states), dtype=np.float64)
        for traj in trajectories:
            for t in range(len(traj) - 1):
                i = state_to_idx.get(traj[t])
                j = state_to_idx.get(traj[t + 1])
                if i is not None and j is not None:
                    tm_fallback[i, j] += 1
        row_sums = tm_fallback.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        tm_fallback /= row_sums

        synthetic = []
        for traj in trajectories:
            length = len(traj)
            synth = []
            prev = rng.choice(n_states, p=initial_probs)
            synth.append(STATES[prev])
            if length > 1:
                current = rng.choice(n_states, p=tm_fallback[prev])
                synth.append(STATES[current])
                for _ in range(length - 2):
                    key = (prev, current)
                    if key in bigram_probs:
                        nxt = rng.choice(n_states, p=bigram_probs[key])
                    else:
                        nxt = rng.choice(n_states, p=tm_fallback[current])
                    synth.append(STATES[nxt])
                    prev = current
                    current = nxt
            synthetic.append(synth)

    else:
        raise ValueError(f"Unsupported Markov order: {markov_order}")

    kwargs = embed_kwargs or {}
    embeddings, _ = ngram_embed(synthetic, **kwargs)
    return embeddings


# ─────────────────────────────────────────────────────────────────────
# Phase-order shuffle (for Phase 6 career-phase analysis)
# ─────────────────────────────────────────────────────────────────────


def phase_order_shuffle_test(
    window_embeddings: np.ndarray,
    windows: list[dict],
    n_permutations: int = 200,
    max_dim: int = 1,
    n_landmarks: int = 3000,
    statistic: str = "total_persistence",
    n_jobs: int = -1,
    seed: int = 42,
) -> dict:
    """Permutation test shuffling temporal order of windows within individuals.

    For each permutation, randomly reorder the windows belonging to each
    individual while preserving the overall set of embeddings. Then
    re-assemble the embedding array and compute PH.

    This tests whether the temporal ordering of career phases carries
    topological signal beyond the marginal distribution of phase embeddings.

    Args:
        window_embeddings: (N_windows, K) point cloud.
        windows: Window records with 'pidp' and 'traj_idx' fields.
        n_permutations: Number of permutations (default: 200).
        max_dim: Maximum homology dimension.
        n_landmarks: Landmarks for PH subsampling.
        statistic: 'total_persistence' or 'max_persistence'.
        n_jobs: Parallelism (-1 = all cores).
        seed: Random seed.

    Returns:
        Dict with observed stats, null distributions, and p-values.
    """
    from collections import defaultdict

    # Build pidp → list of indices mapping
    pidp_to_indices: dict = defaultdict(list)
    for i, w in enumerate(windows):
        pidp_to_indices[w["pidp"]].append(i)

    # Observed PH
    n = window_embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, landmarks = maxmin_landmarks(window_embeddings, actual_lm, seed=seed)
    else:
        landmarks = window_embeddings
    ph_obs = compute_rips_ph(landmarks, max_dim=max_dim)
    obs_summary = persistence_summary(ph_obs)
    observed = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        observed[key] = obs_summary.get(key, {}).get(statistic, 0.0)

    logger.info(f"Phase-order shuffle: observed {observed}")

    # Single permutation function
    def _run_one(perm_seed: int) -> dict[str, float]:
        rng = np.random.RandomState(perm_seed)
        perm_embeddings = window_embeddings.copy()

        # Shuffle indices within each individual
        for indices in pidp_to_indices.values():
            if len(indices) > 1:
                shuffled = rng.permutation(indices)
                perm_embeddings[indices] = window_embeddings[shuffled]

        lm_count = min(n_landmarks, perm_embeddings.shape[0])
        if lm_count < perm_embeddings.shape[0]:
            _, lm = maxmin_landmarks(perm_embeddings, lm_count, seed=perm_seed)
        else:
            lm = perm_embeddings

        ph = compute_rips_ph(lm, max_dim=max_dim)
        s = persistence_summary(ph)
        return {f"H{d}": s.get(f"H{d}", {}).get(statistic, 0.0) for d in range(max_dim + 1)}

    # Run permutations
    seeds = [seed + i + 1 for i in range(n_permutations)]
    null_stats = Parallel(n_jobs=n_jobs, verbose=0)(delayed(_run_one)(s) for s in seeds)

    # Assemble results
    null_distributions: dict[str, list[float]] = {f"H{d}": [] for d in range(max_dim + 1)}
    for ns in null_stats:
        for key, val in ns.items():
            null_distributions[key].append(val)

    p_values = {}
    for key in observed:
        null_arr = np.array(null_distributions[key])
        # One-sided p-value: fraction of nulls >= observed
        p_values[key] = float(np.mean(null_arr >= observed[key]))

    logger.info(f"Phase-order shuffle p-values: {p_values}")

    return {
        "observed": observed,
        "null_distributions": {k: v for k, v in null_distributions.items()},
        "p_values": p_values,
        "n_permutations": n_permutations,
    }


# ─────────────────────────────────────────────────────────────────────
# Core permutation test
# ─────────────────────────────────────────────────────────────────────


def _single_permutation(
    null_type: str,
    embeddings: np.ndarray,
    trajectories: list[list[str]] | None,
    metadata: dict | None,
    seed: int,
    max_dim: int,
    n_landmarks: int,
    statistic: str,
    markov_order: int,
    embed_kwargs: dict | None,
) -> dict[str, float]:
    """Execute one permutation and return statistic values."""
    rng = np.random.RandomState(seed)

    if null_type == "label_shuffle":
        X_perm = _label_shuffle(embeddings, rng)
    elif null_type == "cohort_shuffle":
        X_perm = _cohort_shuffle(embeddings, metadata or {}, rng)
    elif null_type == "order_shuffle":
        X_perm = _order_shuffle(trajectories or [], rng, embed_kwargs)
    elif null_type == "markov":
        X_perm = _markov_shuffle(trajectories or [], rng, markov_order, embed_kwargs)
    else:
        raise ValueError(f"Unknown null_type: {null_type}")

    # Subsample if needed
    n = X_perm.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, landmarks = maxmin_landmarks(X_perm, actual_lm, seed=seed)
    else:
        landmarks = X_perm

    ph = compute_rips_ph(landmarks, max_dim=max_dim)
    summary = persistence_summary(ph)

    result = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        result[key] = summary.get(key, {}).get(statistic, 0.0)

    return result


def permutation_test_trajectories(
    embeddings: np.ndarray,
    trajectories: list[list[str]] | None = None,
    metadata: dict | None = None,
    null_type: Literal["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"] = "label_shuffle",
    n_permutations: int = 1000,
    max_dim: int = 1,
    n_landmarks: int = 5000,
    statistic: str = "total_persistence",
    markov_order: int = 1,
    n_jobs: int = -1,
    seed: int = 42,
    embed_kwargs: dict | None = None,
) -> dict:
    """Trajectory-aware permutation test for topological significance.

    Args:
        embeddings: (N, K) observed embedded point cloud
        trajectories: Raw state sequences (needed for order_shuffle, markov)
        metadata: Dict with 'cohort' array (needed for cohort_shuffle)
        null_type: Type of null model
        n_permutations: Number of permutations
        max_dim: Maximum homology dimension to test
        n_landmarks: Landmarks for subsampling
        statistic: 'total_persistence' or 'max_persistence'
        markov_order: Order for Markov null (1 or 2)
        n_jobs: Number of parallel jobs (-1 = all cores)
        seed: Random seed base
        embed_kwargs: Kwargs passed to ngram_embed for re-embedding nulls

    Returns:
        Dict with per-dimension results:
            {f'H{dim}': {observed, null_mean, null_std, null_p95, p_value,
                         significant_at_005}}
    """
    # Validate inputs
    if null_type in ("order_shuffle", "markov") and trajectories is None:
        raise ValueError(f"null_type='{null_type}' requires trajectories argument")

    logger.info(f"Permutation test: {null_type}, {n_permutations} perms, H0-H{max_dim}, statistic={statistic}")

    # Observed statistic
    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_landmarks = embeddings

    ph_obs = compute_rips_ph(obs_landmarks, max_dim=max_dim)
    obs_summary = persistence_summary(ph_obs)
    observed = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        observed[key] = obs_summary.get(key, {}).get(statistic, 0.0)
    logger.info(f"  Observed {statistic}: {observed}")

    # Run permutations in parallel
    seeds = [seed + i + 1 for i in range(n_permutations)]

    null_results = Parallel(n_jobs=n_jobs, verbose=0)(
        delayed(_single_permutation)(
            null_type,
            embeddings,
            trajectories,
            metadata,
            s,
            max_dim,
            actual_lm,
            statistic,
            markov_order,
            embed_kwargs,
        )
        for s in seeds
    )

    # Aggregate results
    results = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        null_vals = np.array([r[key] for r in null_results])
        obs_val = observed[key]
        p_value = float(np.mean(null_vals >= obs_val))

        results[key] = {
            "observed": obs_val,
            "null_mean": float(null_vals.mean()),
            "null_std": float(null_vals.std()),
            "null_p95": float(np.percentile(null_vals, 95)),
            "p_value": p_value,
            "significant_at_005": p_value < 0.05,
            "null_distribution": null_vals.tolist(),
        }
        logger.info(
            f"  {key}: observed={obs_val:.4f}, null={null_vals.mean():.4f}±{null_vals.std():.4f}, p={p_value:.4f}"
        )

    results["null_type"] = null_type
    results["n_permutations"] = n_permutations
    results["statistic"] = statistic

    return results
