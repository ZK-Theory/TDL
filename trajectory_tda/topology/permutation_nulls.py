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

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from joblib import Parallel, delayed

from poverty_tda.topology.multidim_ph import (
    PHResult,
    compute_rips_ph,
    persistence_summary,
)
from trajectory_tda.embedding.ngram_embed import STATES, ngram_embed
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks
from trajectory_tda.topology.vectorisation import (
    compute_w2_ratio_bca_ci,
    wasserstein_distance as compute_wasserstein,
)

logger = logging.getLogger(__name__)

LandmarkNormalizer = Literal["none", "median-pdist", "max-pdist", "mean-pdist"]
_NORMALIZER_SCALE_LABELS: dict[LandmarkNormalizer, str] = {
    "none": "median_pairwise_distance",
    "median-pdist": "median_pairwise_distance",
    "max-pdist": "max_pairwise_distance",
    "mean-pdist": "mean_pairwise_distance",
}


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")
    for attempt in range(10):
        try:
            tmp_path.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.2 * (attempt + 1))


def _pairwise_distance_scale(X: np.ndarray, normalizer: LandmarkNormalizer) -> float:
    """Characteristic cloud scale for H2 dispersion-control diagnostics."""
    from scipy.spatial.distance import pdist

    if X.shape[0] < 2:
        raise ValueError("pairwise-distance scale is undefined for fewer than two points")
    distances = pdist(np.asarray(X, dtype=np.float64))
    if normalizer in ("none", "median-pdist"):
        scale = float(np.median(distances))
    elif normalizer == "max-pdist":
        scale = float(np.max(distances))
    elif normalizer == "mean-pdist":
        scale = float(np.mean(distances))
    else:
        raise ValueError(f"unknown landmark normalizer: {normalizer!r}")
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError(f"pairwise-distance scale must be positive and finite; got {scale!r}")
    return scale


def _median_pairwise_distance(X: np.ndarray) -> float:
    """Median pairwise cloud scale used by earlier H2 dispersion diagnostics."""
    return _pairwise_distance_scale(X, "median-pdist")


def _resolve_landmark_normalizer(
    normalize_landmarks_by_median_pdist: bool,
    landmark_normalizer: LandmarkNormalizer | None,
) -> LandmarkNormalizer:
    if landmark_normalizer is None:
        return "median-pdist" if normalize_landmarks_by_median_pdist else "none"
    if landmark_normalizer not in _NORMALIZER_SCALE_LABELS:
        raise ValueError(f"unknown landmark normalizer: {landmark_normalizer!r}")
    return landmark_normalizer


def _ph_provenance(ph: PHResult) -> dict[str, Any]:
    return {
        "ph_method": getattr(ph, "ph_method", "unknown"),
        "do_cocycles": bool(getattr(ph, "do_cocycles", False)),
        "threshold_rule": getattr(ph, "threshold_rule", None),
        "threshold_value": getattr(ph, "threshold_value", None),
        "edge_prop_at_thresh": getattr(ph, "edge_prop_at_thresh", None),
        "candidate_tetrahedra_burden": getattr(ph, "candidate_tetrahedra_burden", None),
        "wall_time_seconds": float(getattr(ph, "elapsed_seconds", 0.0)),
        "backend_versions": dict(getattr(ph, "backend_versions", {})),
        "preflight": dict(getattr(ph, "preflight", {})),
    }

def _normalise_cohort_label(value: object) -> str:
    """Map missing cohort labels to a stable string bucket."""
    if value is None:
        return "unknown"
    try:
        if value != value:
            return "unknown"
    except Exception:
        pass
    return str(value)


def _ngram_kwargs_with_frozen_models(
    embed_kwargs: dict | None,
    frozen_models: dict | None,
) -> dict:
    """Merge frozen fitted models into kwargs for ngram_embed()."""
    kwargs = dict(embed_kwargs or {})
    if not frozen_models:
        return kwargs

    scaler = frozen_models.get("scaler")
    reducer = frozen_models.get("reducer")
    if scaler is not None:
        kwargs["frozen_scaler"] = scaler
    if reducer is not None:
        if hasattr(reducer, "components_"):
            kwargs["frozen_pca"] = reducer
        else:
            kwargs["frozen_umap"] = reducer
    return kwargs


# ───────────────────────────────────────────────────────────────────
# Null model generators
# ───────────────────────────────────────────────────────────────────


def _label_shuffle(
    embeddings: np.ndarray,
    rng: np.random.RandomState,
    embed_kwargs: dict | None = None,
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

    cohort_array = np.asarray([_normalise_cohort_label(value) for value in cohorts], dtype=object)

    result = embeddings.copy()
    unique_cohorts = np.unique(cohort_array)
    for c in unique_cohorts:
        mask = cohort_array == c
        indices = np.where(mask)[0]
        perm = rng.permutation(len(indices))
        result[indices] = embeddings[indices[perm]]

    return result


def _order_shuffle(
    trajectories: list[list[str]],
    rng: np.random.RandomState,
    embed_kwargs: dict | None = None,
    frozen_models: dict | None = None,
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

    kwargs = _ngram_kwargs_with_frozen_models(embed_kwargs, frozen_models)
    embeddings, _ = ngram_embed(shuffled, **kwargs)
    return embeddings


def _markov_shuffle(
    trajectories: list[list[str]],
    rng: np.random.RandomState,
    markov_order: int = 1,
    embed_kwargs: dict | None = None,
    alpha: float = 1.0,
    frozen_models: dict | None = None,
) -> np.ndarray:
    """Generate synthetic trajectories from fitted Markov chain, then embed.

    Estimates the transition matrix (or higher-order) from all trajectories,
    then generates synthetic trajectories of the same lengths. Tests whether
    observed topology exceeds what a memoryless process produces.

    For Markov-2, conditional probabilities are smoothed with Laplace smoothing:
    P(s_t | s_{t-2}, s_{t-1}) = (count(s_{t-2}, s_{t-1}, s_t) + alpha) /
                                  (sum_s count(s_{t-2}, s_{t-1}, s) + alpha * n_states)
    Unobserved bigrams receive uniform probability (alpha / (alpha * n_states) = 1/n_states).

    Args:
        trajectories: Raw state sequences.
        rng: Random state for reproducibility.
        markov_order: Markov chain order (1 or 2).
        embed_kwargs: Kwargs passed to ngram_embed.
        alpha: Laplace smoothing parameter for Markov-2 conditional probabilities.
            Default 1 (add-one smoothing). Use alpha=0 to recover raw MLE.
        frozen_models: Optional fitted-model bundle from ngram_embed()[1]["fitted_models"].

    Raises:
        ValueError: If ``alpha`` is negative (invalid Laplace smoothing).
    """
    if alpha < 0:
        raise ValueError(f"alpha must be non-negative for Markov smoothing, got {alpha}")

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

        # Laplace-smoothed conditional probabilities for all observed bigrams.
        # Unobserved bigrams fall through to uniform (alpha / alpha*n_states).
        bigram_probs = {}
        for key, counts in bigram_counts.items():
            total = counts.sum()
            bigram_probs[key] = (counts + alpha) / (total + alpha * n_states)

        init_sum = initial_counts.sum()
        initial_probs = initial_counts / init_sum if init_sum > 0 else np.ones(n_states) / n_states

        uniform_fallback = np.ones(n_states) / n_states

        synthetic = []
        for traj in trajectories:
            length = len(traj)
            synth = []
            prev = rng.choice(n_states, p=initial_probs)
            synth.append(STATES[prev])
            if length > 1:
                current = rng.choice(n_states, p=uniform_fallback)
                synth.append(STATES[current])
                for _ in range(length - 2):
                    key = (prev, current)
                    probs = bigram_probs.get(key, uniform_fallback)
                    nxt = rng.choice(n_states, p=probs)
                    synth.append(STATES[nxt])
                    prev = current
                    current = nxt
            synthetic.append(synth)

    else:
        raise ValueError(f"Unsupported Markov order: {markov_order}")

    kwargs = _ngram_kwargs_with_frozen_models(embed_kwargs, frozen_models)
    embeddings, _ = ngram_embed(synthetic, **kwargs)
    return embeddings


# ───────────────────────────────────────────────────────────────────
# Stratified Markov null (per-regime transition matrices)
# ───────────────────────────────────────────────────────────────────


def _stratified_markov_shuffle(
    trajectories: list[list[str]],
    regime_labels: np.ndarray,
    rng: np.random.RandomState,
    markov_order: int = 1,
    embed_kwargs: dict | None = None,
    min_regime_n: int = 30,
    frozen_models: dict | None = None,
) -> np.ndarray:
    """Generate synthetic trajectories using per-regime Markov chains.

    For each regime k:
      1. Select trajectories assigned to regime k
      2. Estimate Markov-order transition matrix from those trajectories only
      3. Generate synthetic trajectories of same lengths using regime-specific chain

    Concatenate all regime-specific synthetic trajectories (preserving original order).
    Return re-embedded synthetic point cloud.

    Args:
        trajectories: Raw state sequences.
        regime_labels: (N,) array of integer regime assignments (one per trajectory).
        rng: Random state for reproducibility.
        markov_order: Markov chain order (only 1 supported for stratified).
        embed_kwargs: Kwargs passed to ngram_embed.
        min_regime_n: Minimum trajectories per regime for reliable estimation.
        frozen_models: Optional fitted-model bundle from ngram_embed()[1]["fitted_models"].
                      Regimes below this threshold use the global transition matrix.
    """
    if markov_order != 1:
        raise ValueError("Stratified Markov null only supports order 1")

    # Guard against the two most common collapse causes:
    # 1. regime_labels passed as a scalar (k_optimal int) instead of a label array.
    # 2. regime_labels length not aligned with trajectories (index-reset mismatch).
    regime_labels = np.asarray(regime_labels)
    if regime_labels.ndim != 1:
        raise ValueError(
            f"regime_labels must be a 1-D array of per-trajectory integers, "
            f"got shape {regime_labels.shape}. "
            "Pass gmm_labels from 05_analysis.json, not the cluster count k."
        )
    if len(regime_labels) != len(trajectories):
        raise ValueError(
            f"regime_labels length ({len(regime_labels)}) does not match "
            f"trajectories length ({len(trajectories)}). "
            "Ensure the label array is row-aligned with the trajectory list "
            "(no index resets between embedding and null steps)."
        )

    state_to_idx = {s: i for i, s in enumerate(STATES)}
    n_states = len(STATES)
    n_traj = len(trajectories)

    # Global transition matrix (fallback for small regimes)
    global_tm = np.zeros((n_states, n_states), dtype=np.float64)
    global_init = np.zeros(n_states, dtype=np.float64)
    for traj in trajectories:
        if len(traj) == 0:
            continue
        s0 = state_to_idx.get(traj[0])
        if s0 is not None:
            global_init[s0] += 1
        for t in range(len(traj) - 1):
            i = state_to_idx.get(traj[t])
            j = state_to_idx.get(traj[t + 1])
            if i is not None and j is not None:
                global_tm[i, j] += 1
    row_sums = global_tm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    global_tm /= row_sums
    init_sum = global_init.sum()
    global_init_probs = global_init / init_sum if init_sum > 0 else np.ones(n_states) / n_states

    # Per-regime transition matrices
    unique_regimes = np.unique(regime_labels)
    regime_tm: dict[int, np.ndarray] = {}
    regime_init: dict[int, np.ndarray] = {}

    for k in unique_regimes:
        mask = regime_labels == k
        regime_trajs = [trajectories[i] for i in range(n_traj) if mask[i]]
        n_regime = len(regime_trajs)

        if n_regime < min_regime_n:
            logger.warning(
                "Regime %s: only %d trajectories (< %d), using global transition matrix",
                k,
                n_regime,
                min_regime_n,
            )
            regime_tm[int(k)] = global_tm.copy()
            regime_init[int(k)] = global_init_probs.copy()
            continue

        tm = np.zeros((n_states, n_states), dtype=np.float64)
        init_counts = np.zeros(n_states, dtype=np.float64)
        for traj in regime_trajs:
            if len(traj) == 0:
                continue
            s0 = state_to_idx.get(traj[0])
            if s0 is not None:
                init_counts[s0] += 1
            for t in range(len(traj) - 1):
                i = state_to_idx.get(traj[t])
                j = state_to_idx.get(traj[t + 1])
                if i is not None and j is not None:
                    tm[i, j] += 1

        rs = tm.sum(axis=1, keepdims=True)
        rs[rs == 0] = 1
        tm /= rs
        isum = init_counts.sum()
        init_p = init_counts / isum if isum > 0 else np.ones(n_states) / n_states

        regime_tm[int(k)] = tm
        regime_init[int(k)] = init_p

    # Generate synthetic trajectories per regime, preserving original order
    synthetic = [None] * n_traj
    for i, traj in enumerate(trajectories):
        k = int(regime_labels[i])
        tm = regime_tm[k]
        init_p = regime_init[k]
        length = len(traj)

        synth = []
        current = rng.choice(n_states, p=init_p)
        synth.append(STATES[current])
        for _ in range(length - 1):
            current = rng.choice(n_states, p=tm[current])
            synth.append(STATES[current])
        synthetic[i] = synth

    kwargs = _ngram_kwargs_with_frozen_models(embed_kwargs, frozen_models)
    embeddings, _ = ngram_embed(synthetic, **kwargs)
    return embeddings


# ───────────────────────────────────────────────────────────────────
# Phase-order shuffle (for Phase 6 career-phase analysis)
# ───────────────────────────────────────────────────────────────────


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


# ───────────────────────────────────────────────────────────────────
# Core permutation test
# ───────────────────────────────────────────────────────────────────


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
    alpha: float = 1.0,
    frozen_models: dict | None = None,
    ph_observed: PHResult | None = None,
    dedup: bool = False,
    forced_n_dedup: int | None = None,
    pinned_thresh: float | None = None,
    ph_kwargs: dict[str, Any] | None = None,
    normalize_landmarks_by_median_pdist: bool = False,
    landmark_normalizer: LandmarkNormalizer | None = None,
) -> dict:
    """Execute one permutation and return statistic values.

    When ``dedup`` is True, the Rips PH for the permuted landmark sample is
    computed via ``ripser.ripser(..., n_perm=N)`` where N is determined by
    ``compute_greedy_dedup_count`` so that the covering radius is at or below
    ``DEDUP_TOLERANCE`` — see the length-matched-dedup-via-n-perm formula
    contract. The returned dict additionally carries ``_dedup_info`` with
    the per-permutation ``n_perm_used`` and ``covering_radius_at_n_perm``.

    Probe-mode overrides for Pre-reg #5 redo amendment robustness checks:

    - ``forced_n_dedup``: when set, override the natural dedup count and use
      the first ``forced_n_dedup`` greedy-permutation indices regardless of
      covering-radius termination. Used by the probe-symmetric-dedup probe
      to force null PDs to use n_perm = obs_n_dedup, eliminating the
      observed-vs-null vertex-count asymmetry that emerges naturally on
      length-matched cells.
    - ``pinned_thresh``: when set, pass this threshold to ``compute_rips_ph``
      for the null PD computation, overriding the per-call auto-thresh from
      a random 500-pt subsample. Used by the probe-pinned-thresh probe to
      eliminate observed-vs-null auto-thresh divergence.

    Both probe parameters default to ``None`` (no behaviour change) — they
    do not affect the production pipeline; they exist to support the
    supplementary robustness probes queued in P01-A-JRSSA open items.
    """
    rng = np.random.RandomState(seed)

    if null_type == "label_shuffle":
        X_perm = _label_shuffle(embeddings, rng)
    elif null_type == "cohort_shuffle":
        X_perm = _cohort_shuffle(embeddings, metadata or {}, rng)
    elif null_type == "order_shuffle":
        X_perm = _order_shuffle(trajectories or [], rng, embed_kwargs, frozen_models)
    elif null_type == "markov":
        X_perm = _markov_shuffle(
            trajectories or [],
            rng,
            markov_order,
            embed_kwargs,
            alpha=alpha,
            frozen_models=frozen_models,
        )
    elif null_type == "stratified_markov1":
        regime_labels = (metadata or {}).get("regime_labels")
        if regime_labels is None:
            raise ValueError("null_type='stratified_markov1' requires metadata['regime_labels']")
        X_perm = _stratified_markov_shuffle(
            trajectories or [],
            np.asarray(regime_labels),
            rng,
            markov_order=1,
            embed_kwargs=embed_kwargs,
            frozen_models=frozen_models,
        )
    else:
        raise ValueError(f"Unknown null_type: {null_type}")

    # Subsample if needed
    n = X_perm.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, landmarks = maxmin_landmarks(X_perm, actual_lm, seed=seed)
    else:
        landmarks = X_perm

    # Optional external dedup for length-matched cells per the
    # length-matched-dedup-via-n-perm formula contract. Identical to the
    # exact-ripser path when dedup=False (default) — the compute_rips_ph
    # call shape is bit-for-bit unchanged so existing monkeypatches and
    # call sites are not affected. Probe-mode overrides (forced_n_dedup,
    # pinned_thresh) are documented in the function docstring.
    n_perm_used: int | None = None
    covering_radius_at_n_perm: float | None = None
    landmarks_for_ph = landmarks
    if forced_n_dedup is not None:
        from poverty_tda.topology.multidim_ph import (
            greedy_first_k_indices_with_radius,
        )

        forced_k = int(min(forced_n_dedup, landmarks.shape[0]))
        dedup_idx, eps_at_k = greedy_first_k_indices_with_radius(landmarks, forced_k)
        n_perm_used = forced_k
        covering_radius_at_n_perm = float(eps_at_k)
        landmarks_for_ph = landmarks[dedup_idx]
    elif dedup:
        from poverty_tda.topology.multidim_ph import compute_greedy_dedup_count

        n_perm_used, covering_radius_at_n_perm, dedup_idx = compute_greedy_dedup_count(landmarks)
        landmarks_for_ph = landmarks[dedup_idx]

    resolved_normalizer = _resolve_landmark_normalizer(
        normalize_landmarks_by_median_pdist,
        landmark_normalizer,
    )
    normalization = {
        "enabled": resolved_normalizer != "none",
        "normalizer": resolved_normalizer,
        "scale": _NORMALIZER_SCALE_LABELS[resolved_normalizer],
        "scale_value": None,
        "landmark_count_for_scale": int(landmarks_for_ph.shape[0]),
    }
    if resolved_normalizer != "none":
        scale_value = _pairwise_distance_scale(landmarks_for_ph, resolved_normalizer)
        normalization["scale_value"] = float(scale_value)
        landmarks_for_ph = landmarks_for_ph / scale_value
    runtime_ph_kwargs: dict[str, Any] = dict(ph_kwargs or {})
    runtime_ph_kwargs.setdefault("max_dim", max_dim)
    if pinned_thresh is not None:
        runtime_ph_kwargs["thresh"] = float(pinned_thresh)
    ph = compute_rips_ph(landmarks_for_ph, **runtime_ph_kwargs)
    provenance = _ph_provenance(ph)
    provenance["seed"] = int(seed)
    provenance["n_landmarks"] = int(landmarks_for_ph.shape[0])
    provenance["normalization"] = normalization

    dedup_info: dict | None = None
    if n_perm_used is not None:
        # Populated for both natural dedup (dedup=True) and probe-forced
        # dedup (forced_n_dedup set). Carries forced-vs-natural origin so
        # downstream provenance can distinguish probe results from
        # production runs.
        dedup_info = {
            "n_perm_used": int(n_perm_used),
            "covering_radius_at_n_perm": float(covering_radius_at_n_perm)
            if covering_radius_at_n_perm is not None
            else None,
            "origin": "forced" if forced_n_dedup is not None else "natural",
        }

    # Wasserstein statistic: return W(null, observed) per dimension
    if statistic == "wasserstein" and ph_observed is not None:
        result = {}
        for dim in range(max_dim + 1):
            key = f"H{dim}"
            result[key] = compute_wasserstein(ph, ph_observed, dim=dim)
            # Store raw diagram for null-null baseline computation
            feats = ph.h_features(dim)
            arr = np.array(feats) if len(feats) > 0 else np.empty((0, 2))
            # Filter infinite features
            if len(arr) > 0:
                arr = arr[np.isfinite(arr[:, 1])]
            result[f"{key}_dgm"] = arr.tolist()
        if dedup_info is not None:
            result["_dedup_info"] = dedup_info
        result["_ph_provenance"] = provenance
        return result

    summary = persistence_summary(ph)

    result = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        result[key] = summary.get(key, {}).get(statistic, 0.0)

    if dedup_info is not None:
        result["_dedup_info"] = dedup_info
    result["_ph_provenance"] = provenance
    return result


def _single_permutation_indexed(
    index: int,
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
    *,
    alpha: float = 1.0,
    frozen_models: dict | None = None,
    ph_observed: PHResult | None = None,
    ph_kwargs: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any], float]:
    started = time.time()
    result = _single_permutation(
        null_type,
        embeddings,
        trajectories,
        metadata,
        seed,
        max_dim,
        n_landmarks,
        statistic,
        markov_order,
        embed_kwargs,
        alpha=alpha,
        frozen_models=frozen_models,
        ph_observed=ph_observed,
        ph_kwargs=ph_kwargs,
    )
    elapsed = time.time() - started
    result["_permutation_index"] = int(index)
    result["_wall_time_seconds"] = float(elapsed)
    return index, result, elapsed


def permutation_test_trajectories(
    embeddings: np.ndarray,
    trajectories: list[list[str]] | None = None,
    metadata: dict | None = None,
    null_type: Literal[
        "label_shuffle",
        "cohort_shuffle",
        "order_shuffle",
        "markov",
        "stratified_markov1",
    ] = "label_shuffle",
    n_permutations: int = 1000,
    max_dim: int = 1,
    n_landmarks: int = 5000,
    statistic: str = "total_persistence",
    markov_order: int = 1,
    alpha: float = 1.0,
    n_jobs: int = -1,
    seed: int = 42,
    embed_kwargs: dict | None = None,
    frozen_models: dict | None = None,
    ph_kwargs: dict[str, Any] | None = None,
    ph_observed: PHResult | None = None,
    checkpoint_path: Path | None = None,
    resume: bool = False,
    max_hours: float = 0.0,
    started_at: float | None = None,
    parallel_timeout_seconds: float | None = None,
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
        statistic: 'total_persistence', 'max_persistence', or 'wasserstein'
        markov_order: Order for Markov null (1 or 2)
        alpha: Laplace smoothing parameter for Markov-2 nulls
        n_jobs: Number of parallel jobs (-1 = all cores)
        seed: Random seed base
        embed_kwargs: Kwargs passed to ngram_embed for re-embedding nulls
        frozen_models: Optional fitted-model bundle from ngram_embed()[1]["fitted_models"].

    Returns:
        Dict with per-dimension results. For scalar statistics:
            {f'H{dim}': {observed, null_mean, null_std, null_p95, p_value,
                         significant_at_005}}
        For wasserstein statistic:
            {f'H{dim}': {mean_wasserstein_obs_null, std_wasserstein_obs_null,
                         median_wasserstein_obs_null, mean_wasserstein_null_null,
                         p_value, significant_at_005, obs_null_distribution,
                         n_null_null_pairs}}
    """
    # Validate inputs
    if null_type in ("order_shuffle", "markov", "stratified_markov1") and trajectories is None:
        raise ValueError(f"null_type='{null_type}' requires trajectories argument")

    logger.info(f"Permutation test: {null_type}, {n_permutations} perms, H0-H{max_dim}, statistic={statistic}")

    # Observed statistic
    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_landmarks = embeddings

    runtime_ph_kwargs: dict[str, Any] = dict(ph_kwargs or {})
    runtime_ph_kwargs.setdefault("max_dim", max_dim)
    ph_obs = ph_observed if ph_observed is not None else compute_rips_ph(obs_landmarks, **runtime_ph_kwargs)

    if statistic != "wasserstein":
        obs_summary = persistence_summary(ph_obs)
        observed = {}
        for dim in range(max_dim + 1):
            key = f"H{dim}"
            observed[key] = obs_summary.get(key, {}).get(statistic, 0.0)
        logger.info(f"  Observed {statistic}: {observed}")
    else:
        logger.info("  Wasserstein mode: computing W(null, observed) for each permutation")

    # Run permutations in parallel
    seeds = [seed + i + 1 for i in range(n_permutations)]

    checkpoint_params = {
        "null_type": null_type,
        "n_permutations": int(n_permutations),
        "max_dim": int(max_dim),
        "n_landmarks": int(actual_lm),
        "statistic": statistic,
        "markov_order": int(markov_order),
        "alpha": float(alpha),
        "seed": int(seed),
        "ph_kwargs": _jsonable(runtime_ph_kwargs),
    }
    completed: dict[str, dict[str, Any]] = {}
    if checkpoint_path is not None:
        checkpoint_path = Path(checkpoint_path)
        if resume and checkpoint_path.exists():
            payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if payload.get("params") == _jsonable(checkpoint_params):
                completed = {str(k): v for k, v in payload.get("results_by_index", {}).items()}
                logger.info("Loaded permutation checkpoint %s (%d/%d)", checkpoint_path, len(completed), n_permutations)
            else:
                logger.warning("Ignoring incompatible permutation checkpoint: %s", checkpoint_path)

    def _save_checkpoint() -> None:
        if checkpoint_path is None:
            return
        payload = {
            "schema_version": "trajectory_tda/permutation-null-checkpoint/v1",
            "updated_at": _now_iso(),
            "params": checkpoint_params,
            "completed_count": len(completed),
            "total": int(n_permutations),
            "results_by_index": completed,
        }
        _write_json_atomic(checkpoint_path, payload)

    missing = [i for i in range(n_permutations) if str(i) not in completed]
    if missing:
        joblib_timeout = None if n_jobs == 1 else parallel_timeout_seconds
        chunk_size = max(1, n_jobs if n_jobs > 0 else 4)
        for offset in range(0, len(missing), chunk_size):
            if max_hours > 0 and started_at is not None and (time.time() - started_at) / 3600.0 > max_hours:
                _save_checkpoint()
                raise TimeoutError(f"max_hours={max_hours} exceeded during permutation null")
            chunk = missing[offset : offset + chunk_size]
            parallel = Parallel(
                n_jobs=n_jobs,
                verbose=0,
                return_as="generator_unordered",
                timeout=joblib_timeout,
            )
            generated = parallel(
                delayed(_single_permutation_indexed)(
                    i,
                    null_type,
                    embeddings,
                    trajectories,
                    metadata,
                    seeds[i],
                    max_dim,
                    actual_lm,
                    statistic,
                    markov_order,
                    embed_kwargs,
                    alpha=alpha,
                    frozen_models=frozen_models,
                    ph_observed=ph_obs if statistic == "wasserstein" else None,
                    ph_kwargs=runtime_ph_kwargs,
                )
                for i in chunk
            )
            try:
                for idx, result, _elapsed in generated:
                    completed[str(idx)] = result
                    _save_checkpoint()
                    logger.info("  permutation %d/%d complete", len(completed), n_permutations)
            except BaseException:
                _save_checkpoint()
                raise

    null_results = [completed[str(i)] for i in range(n_permutations)]

    # Aggregate results
    results = {}

    if statistic == "wasserstein":
        # Wasserstein aggregation: obs-null distances + null-null baseline
        for dim in range(max_dim + 1):
            key = f"H{dim}"
            obs_null_dists = np.array([r[key] for r in null_results])

            # Compute null-null baseline from stored diagrams
            n_null_pairs = min(500, n_permutations * (n_permutations - 1) // 2)
            rng_pairs = np.random.RandomState(seed)
            null_null_dists = []
            for _ in range(n_null_pairs):
                i, j = rng_pairs.choice(n_permutations, size=2, replace=False)
                dgm_i = null_results[i].get(f"{key}_dgm", [])
                dgm_j = null_results[j].get(f"{key}_dgm", [])
                d_i = np.array(dgm_i) if len(dgm_i) > 0 else np.empty((0, 2))
                d_j = np.array(dgm_j) if len(dgm_j) > 0 else np.empty((0, 2))
                ph_i = PHResult(dgms={dim: d_i})
                ph_j = PHResult(dgms={dim: d_j})
                null_null_dists.append(compute_wasserstein(ph_i, ph_j, dim=dim))

            null_null_arr = np.array(null_null_dists) if null_null_dists else np.array([0.0])
            mean_obs_null = float(obs_null_dists.mean())
            mean_null_null = float(null_null_arr.mean())

            # T_ratio = mean(W_obs_null) / mean(W_null_null) (mean-vs-mean construction)
            t_ratio = mean_obs_null / mean_null_null if mean_null_null > 0 else float("nan")

            # BCa CI on T_ratio (requires ≥2 obs in each array)
            bca_ci_lower: float | None = None
            bca_ci_upper: float | None = None
            if len(obs_null_dists) >= 2 and len(null_null_arr) >= 2:
                try:
                    _, bca_ci_lower, bca_ci_upper = compute_w2_ratio_bca_ci(obs_null_dists, null_null_arr, seed=seed)
                except Exception as exc:
                    logger.warning(f"  BCa CI failed for {key}: {exc}")

            # p-value: fraction of null-null W distances >= mean(obs-null W)
            # If observed is typical of nulls, obs-null W ~ null-null W, p ~ 0.5
            # If observed is atypical, obs-null W >> null-null W, p ~ 0
            p_value = float(np.mean(null_null_arr >= mean_obs_null))

            results[key] = {
                "mean_wasserstein_obs_null": mean_obs_null,
                "std_wasserstein_obs_null": float(obs_null_dists.std()),
                "median_wasserstein_obs_null": float(np.median(obs_null_dists)),
                "mean_wasserstein_null_null": mean_null_null,
                "std_wasserstein_null_null": None if len(null_null_dists) <= 1 else float(null_null_arr.std()),
                "t_ratio": t_ratio,
                "bca_ci_lower": bca_ci_lower,
                "bca_ci_upper": bca_ci_upper,
                "p_value": p_value,
                "significant_at_005": p_value < 0.05,
                "obs_null_distribution": obs_null_dists.tolist(),
                "n_null_null_pairs": len(null_null_dists),
            }
            logger.info(
                f"  {key}: mean_W(obs,null)={mean_obs_null:.4f}, "
                f"mean_W(null,null)={mean_null_null:.4f}, "
                f"T_ratio={t_ratio:.4f}, p={p_value:.4f}"
            )
    else:
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
    results["ph_call_provenance"] = [
        r.get("_ph_provenance", {"seed": int(seeds[i]), "missing": True}) for i, r in enumerate(null_results)
    ]
    results["permutation_wall_times_seconds"] = [float(r.get("_wall_time_seconds", 0.0)) for r in null_results]
    results["checkpoint_path"] = None if checkpoint_path is None else str(checkpoint_path)
    results["ph_kwargs"] = _jsonable(runtime_ph_kwargs)

    return results
