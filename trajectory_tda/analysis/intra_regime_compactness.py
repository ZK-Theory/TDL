"""
Intra-regime compactness test: order-dependence of GMM regime assignments.

Compares within-regime compactness on observed embeddings vs order-shuffled
embeddings using frozen PCA loadings and original regime assignments.

If compactness is indistinguishable under order-shuffle, GMM regimes are not
order-dependent (supporting the "parallel analyses" framing). If compactness
changes significantly, regime structure is partially order-dependent.

Phase 3, Concern #2.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from scipy.spatial.distance import pdist

from trajectory_tda.embedding.ngram_embed import (
    N_STATES,
    STATE_TO_IDX,
    ngram_embed,
)

logger = logging.getLogger(__name__)


def _trajectories_to_idx_arrays(
    trajectories: list[list[str]],
) -> list[np.ndarray]:
    """Convert list of state-label trajectories to integer index arrays."""
    result = []
    for traj in trajectories:
        arr = np.array([STATE_TO_IDX[s] for s in traj], dtype=np.int32)
        result.append(arr)
    return result


def _bigrams_from_idx(idx_arr: np.ndarray, n_states: int = N_STATES) -> np.ndarray:
    """Compute bigram vector from integer index array (vectorised)."""
    n = len(idx_arr)
    if n <= 1:
        return np.zeros(n_states * n_states, dtype=np.float64)
    pairs = idx_arr[:-1] * n_states + idx_arr[1:]
    vec = np.bincount(pairs, minlength=n_states * n_states).astype(np.float64)
    vec /= n - 1
    return vec


def _compute_unigrams_from_idx(
    idx_arr: np.ndarray, n_states: int = N_STATES
) -> np.ndarray:
    """Compute unigram vector from integer index array."""
    vec = np.bincount(idx_arr, minlength=n_states).astype(np.float64)
    vec /= len(idx_arr)
    return vec


def _within_regime_compactness(
    embeddings: np.ndarray,
    labels: np.ndarray,
) -> dict[int, float]:
    """Compute mean within-regime pairwise Euclidean distance.

    Args:
        embeddings: (N, D) point cloud in PCA space.
        labels: (N,) regime assignments.

    Returns:
        Dict mapping regime label → mean pairwise distance.
    """
    unique_labels = np.unique(labels)
    compactness = {}
    for k in unique_labels:
        mask = labels == int(k)
        points = embeddings[mask]
        if len(points) < 2:
            compactness[int(k)] = 0.0
            continue
        # For large regimes, subsample to avoid O(n^2) blowup
        if len(points) > 2000:
            rng = np.random.RandomState(42)
            idx = rng.choice(len(points), size=2000, replace=False)
            points = points[idx]
        dists = pdist(points, metric="euclidean")
        compactness[int(k)] = float(np.mean(dists))
    return compactness


def _order_shuffle_trajectories(
    trajectories: list[list[str]],
    rng: np.random.RandomState,
) -> list[list[str]]:
    """Shuffle temporal order within each trajectory, preserving state frequencies."""
    shuffled = []
    for traj in trajectories:
        perm = rng.permutation(len(traj))
        shuffled.append([traj[i] for i in perm])
    return shuffled


def intra_regime_compactness_test(
    trajectories: list[list[str]],
    regime_labels: np.ndarray,
    n_permutations: int = 500,
    pca_dim: int = 20,
    seed: int = 42,
    n_jobs: int = 1,
) -> dict:
    """Test whether GMM regime assignments are order-dependent.

    Algorithm:
    1. Compute observed n-gram embedding with PCA
    2. Freeze PCA loadings from observed data
    3. For each regime, compute within-regime mean pairwise distance
    4. For each permutation:
       a. Order-shuffle trajectories
       b. Compute raw n-gram features
       c. Apply FROZEN PCA transform (no refit)
       d. Compute within-regime distances using ORIGINAL regime labels
    5. Compare observed compactness vs null distribution

    Args:
        trajectories: List of state sequences.
        regime_labels: (N,) GMM regime assignments from observed data.
        n_permutations: Number of order-shuffle permutations (default: 500).
        pca_dim: PCA dimensionality (default: 20).
        seed: Random seed.
        n_jobs: Not used (kept for interface consistency).

    Returns:
        Dict with per-regime compactness comparison and overall summary.
    """
    n = len(trajectories)
    regime_labels = np.asarray(regime_labels)
    assert len(regime_labels) == n, (
        f"Mismatch: {n} trajectories vs {len(regime_labels)} labels"
    )

    logger.info(
        f"Intra-regime compactness test: {n} trajectories, "
        f"{n_permutations} permutations, PCA-{pca_dim}D"
    )

    # Step 1-2: Compute observed embedding and freeze PCA/scaler
    obs_embeddings, obs_info = ngram_embed(
        trajectories,
        include_bigrams=True,
        pca_dim=pca_dim,
        standardize=True,
        random_state=seed,
    )
    fitted_scaler = obs_info["fitted_models"]["scaler"]
    fitted_pca = obs_info["fitted_models"]["reducer"]
    observed_explained_var = obs_info.get("explained_variance")

    logger.info(
        f"  Observed embedding: {obs_embeddings.shape}, "
        f"explained variance: {observed_explained_var}"
    )

    # Step 3: Observed compactness
    obs_compactness = _within_regime_compactness(obs_embeddings, regime_labels)
    logger.info(f"  Observed compactness: {obs_compactness}")

    # Step 4: Null distribution
    # Pre-compute integer index arrays and observed unigrams (invariant under order-shuffle)
    idx_arrays = _trajectories_to_idx_arrays(trajectories)
    obs_unigrams = np.array([_compute_unigrams_from_idx(a) for a in idx_arrays])

    unique_regimes = sorted(obs_compactness.keys())
    null_compactness = {k: [] for k in unique_regimes}
    rng = np.random.RandomState(seed)

    # Pre-allocate bigram buffer
    shuffled_bigrams = np.empty((n, N_STATES * N_STATES), dtype=np.float64)

    # Pre-allocate combined raw features buffer (reused each iteration)
    shuffled_raw = np.empty((n, N_STATES + N_STATES * N_STATES), dtype=np.float64)
    shuffled_raw[:, :N_STATES] = obs_unigrams  # unigrams are invariant

    for i in range(n_permutations):
        # a+b. For each trajectory, shuffle its index array and recompute bigrams
        for j in range(n):
            shuffled_idx = rng.permutation(idx_arrays[j])
            shuffled_raw[j, N_STATES:] = _bigrams_from_idx(shuffled_idx)

        # c. Apply FROZEN scaler + PCA (in-place where possible)
        shuffled_scaled = fitted_scaler.transform(shuffled_raw)
        shuffled_pca = fitted_pca.transform(shuffled_scaled)
        del shuffled_scaled  # free intermediate array immediately

        # d. Compute compactness with ORIGINAL regime labels
        perm_compactness = _within_regime_compactness(shuffled_pca, regime_labels)
        for k in unique_regimes:
            null_compactness[k].append(perm_compactness.get(k, 0.0))

        if (i + 1) % 50 == 0:
            logger.info(f"  Permutation {i + 1}/{n_permutations}")

    # Step 5: Compare observed vs null
    results_per_regime = {}
    for k in unique_regimes:
        null_arr = np.array(null_compactness[k])
        obs_val = obs_compactness[k]
        null_mean = float(null_arr.mean())
        null_std = float(null_arr.std())
        z_score = (obs_val - null_mean) / null_std if null_std > 0 else 0.0
        # Two-sided p-value: is observed compactness different from null?
        p_value = float(
            np.mean(np.abs(null_arr - null_mean) >= abs(obs_val - null_mean))
        )

        results_per_regime[k] = {
            "observed_compactness": obs_val,
            "null_mean": null_mean,
            "null_std": null_std,
            "z_score": float(z_score),
            "p_value": p_value,
            "n_members": int(np.sum(regime_labels == k)),
        }

        logger.info(
            f"  Regime {k}: obs={obs_val:.4f}, "
            f"null={null_mean:.4f}±{null_std:.4f}, "
            f"z={z_score:.2f}, p={p_value:.4f}"
        )

    # Overall summary
    any_significant = any(r["p_value"] < 0.05 for r in results_per_regime.values())
    n_significant = sum(1 for r in results_per_regime.values() if r["p_value"] < 0.05)

    result = {
        "per_regime": results_per_regime,
        "n_regimes": len(unique_regimes),
        "n_permutations": n_permutations,
        "pca_dim": pca_dim,
        "observed_explained_variance": observed_explained_var,
        "any_regime_order_dependent": any_significant,
        "n_significant_regimes": n_significant,
        "conclusion": (
            "Regime structure is partially order-dependent"
            if any_significant
            else "Regime assignments are NOT order-dependent (supports parallel analyses framing)"
        ),
    }

    logger.info(
        f"Compactness test: {n_significant}/{len(unique_regimes)} regimes "
        f"show significant order-dependence"
    )

    return result


def run_compactness_test(
    results_dir: str | Path,
    data_dir: str | Path | None = None,
    n_permutations: int = 500,
    output_path: str | Path | None = None,
) -> dict:
    """Load pipeline outputs and run the compactness test.

    Args:
        results_dir: Directory containing pipeline checkpoints.
        data_dir: Data directory (unused, kept for CLI consistency).
        n_permutations: Number of order-shuffle permutations.
        output_path: Path to save results JSON.

    Returns:
        Compactness test results dict.
    """

    results_dir = Path(results_dir)

    # Load trajectories
    seq_path = results_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)

    # Load regime labels
    analysis_path = results_dir / "05_analysis.json"
    with open(analysis_path) as f:
        analysis = json.load(f)
    regime_labels = np.array(analysis["gmm_labels"])

    logger.info(
        f"Loaded {len(trajectories)} trajectories, {len(regime_labels)} regime labels"
    )

    result = intra_regime_compactness_test(
        trajectories=trajectories,
        regime_labels=regime_labels,
        n_permutations=n_permutations,
    )

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved: {output_path}")

    return result


if __name__ == "__main__":
    import argparse

    setup_msg = "Run intra-regime compactness test"
    parser = argparse.ArgumentParser(description=setup_msg)
    parser.add_argument(
        "--results-dir",
        default="results/trajectory_tda_integration",
        help="Pipeline results directory",
    )
    parser.add_argument(
        "--n-perms", type=int, default=500, help="Number of permutations"
    )
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    run_compactness_test(
        results_dir=args.results_dir,
        n_permutations=args.n_perms,
        output_path=args.output or f"{args.results_dir}/intra_regime_compactness.json",
    )
