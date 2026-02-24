"""
Hybrid persistent homology computation for trajectory point clouds.

Two complementary methods:
1. **Maxmin VR** (good for H₀ / global components): Greedy maxmin landmark
   selection → Vietoris-Rips on landmarks via ripser.
2. **Witness complex** (better for H₁ / local cycles): Same landmarks, full
   data as witnesses → gudhi strong_witness_persistence.

Multi-subsample validation: average Betti curves over multiple random
maxmin subsamples.

Reuses PHResult and compute_rips_ph from poverty_tda.topology.multidim_ph.
"""

from __future__ import annotations

import logging
import time
from typing import Literal

import numpy as np

from poverty_tda.topology.multidim_ph import (
    PHResult,
    betti_curve,
    compute_rips_ph,
    persistence_summary,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Landmark selection
# ─────────────────────────────────────────────────────────────────────


def maxmin_landmarks(
    X: np.ndarray,
    n_landmarks: int,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Greedy maxmin landmark selection.

    Starting from a random point, iteratively select the point farthest
    from the existing landmark set.

    Args:
        X: (N, D) point cloud
        n_landmarks: Number of landmarks to select
        seed: Random seed for initial point

    Returns:
        indices: (n_landmarks,) indices into X
        landmarks: (n_landmarks, D) selected points
    """
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    n_landmarks = min(n_landmarks, n)

    indices = np.zeros(n_landmarks, dtype=int)
    indices[0] = rng.randint(n)

    # Distance from each point to nearest landmark
    min_dists = np.full(n, np.inf)

    for k in range(1, n_landmarks):
        # Update distances to nearest landmark
        dists_to_last = np.linalg.norm(X - X[indices[k - 1]], axis=1)
        min_dists = np.minimum(min_dists, dists_to_last)

        # Select farthest point
        indices[k] = np.argmax(min_dists)

    return indices, X[indices]


# ─────────────────────────────────────────────────────────────────────
# Method 1: Maxmin VR (via ripser)
# ─────────────────────────────────────────────────────────────────────


def _compute_maxmin_vr(
    X: np.ndarray,
    max_dim: int = 1,
    n_landmarks: int = 5000,
    seed: int = 42,
) -> PHResult:
    """Compute VR persistence on maxmin landmarks.

    Args:
        X: (N, D) full point cloud
        max_dim: Maximum homology dimension
        n_landmarks: Number of landmarks
        seed: Random seed

    Returns:
        PHResult from ripser on landmark subset
    """
    n = X.shape[0]
    n_lm = min(n_landmarks, n)

    if n_lm < n:
        logger.info(f"Maxmin VR: selecting {n_lm} landmarks from {n} points")
        _, landmarks = maxmin_landmarks(X, n_lm, seed=seed)
    else:
        landmarks = X
        logger.info(f"Maxmin VR: using all {n} points (no subsampling needed)")

    return compute_rips_ph(landmarks, max_dim=max_dim)


# ─────────────────────────────────────────────────────────────────────
# Method 2: Witness complex (via gudhi)
# ─────────────────────────────────────────────────────────────────────


def _compute_witness(
    X: np.ndarray,
    max_dim: int = 1,
    n_landmarks: int = 5000,
    seed: int = 42,
    max_alpha_square: float = 10.0,
) -> PHResult:
    """Compute strong witness complex persistence.

    Uses gudhi's EuclideanStrongWitnessComplex: landmarks define the
    simplex vertices, full data serves as witnesses that certify simplex
    inclusion.

    Args:
        X: (N, D) full point cloud (witnesses)
        max_dim: Maximum homology dimension
        n_landmarks: Number of landmarks
        seed: Random seed
        max_alpha_square: Maximum filtration value

    Returns:
        PHResult with persistence diagrams
    """
    try:
        import gudhi
    except ImportError:
        logger.warning("gudhi not available, falling back to maxmin VR")
        return _compute_maxmin_vr(X, max_dim, n_landmarks, seed)

    n = X.shape[0]
    n_lm = min(n_landmarks, n)

    logger.info(f"Witness complex: {n_lm} landmarks, {n} witnesses")

    # Select landmarks
    lm_indices, landmarks = maxmin_landmarks(X, n_lm, seed=seed)

    # Build witness complex
    witness_complex = gudhi.EuclideanStrongWitnessComplex(
        witnesses=X.tolist(),
        landmarks=landmarks.tolist(),
    )

    simplex_tree = witness_complex.create_simplex_tree(
        max_alpha_square=max_alpha_square,
        limit_dimension=max_dim + 1,
    )

    # Compute persistence
    simplex_tree.compute_persistence()

    # Extract persistence diagrams into PHResult format
    dgms = {}
    for dim in range(max_dim + 1):
        pairs = simplex_tree.persistence_intervals_in_dimension(dim)
        if len(pairs) > 0:
            dgms[dim] = np.array(pairs)
        else:
            dgms[dim] = np.empty((0, 2))

    ph = PHResult(
        dgms=dgms,
        n_points=n_lm,
        n_dimensions=X.shape[1],
    )

    return ph


# ─────────────────────────────────────────────────────────────────────
# Multi-subsample validation
# ─────────────────────────────────────────────────────────────────────


def _multi_subsample_betti(
    X: np.ndarray,
    n_subsamples: int = 20,
    subsample_size: int = 2000,
    max_dim: int = 1,
    n_betti_points: int = 200,
    seed: int = 42,
) -> dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Compute averaged Betti curves over multiple random subsamples.

    Args:
        X: (N, D) point cloud
        n_subsamples: Number of subsamples to draw
        subsample_size: Size of each subsample
        max_dim: Maximum homology dimension
        n_betti_points: Resolution of Betti curve
        seed: Random seed

    Returns:
        {dim: (epsilon_values, mean_betti, std_betti)}
    """
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    ss = min(subsample_size, n)

    all_bettis: dict[int, list[np.ndarray]] = {d: [] for d in range(max_dim + 1)}
    epsilon_vals = None

    for i in range(n_subsamples):
        idx = rng.choice(n, size=ss, replace=False)
        ph = compute_rips_ph(X[idx], max_dim=max_dim)
        curves = betti_curve(ph, n_points=n_betti_points)

        for dim in range(max_dim + 1):
            if dim in curves:
                eps, betti = curves[dim]
                if epsilon_vals is None:
                    epsilon_vals = eps
                all_bettis[dim].append(betti)

    result = {}
    for dim in range(max_dim + 1):
        if all_bettis[dim]:
            arr = np.array(all_bettis[dim])
            result[dim] = (
                epsilon_vals,
                np.mean(arr, axis=0),
                np.std(arr, axis=0),
            )

    return result


# ─────────────────────────────────────────────────────────────────────
# Main interface
# ─────────────────────────────────────────────────────────────────────


def compute_trajectory_ph(
    embeddings: np.ndarray,
    max_dim: int = 1,
    n_landmarks: int | None = None,
    method: Literal["witness", "maxmin_vr", "both"] = "both",
    validate: bool = True,
    n_validation_subsamples: int = 20,
    validation_subsample_size: int = 2000,
    seed: int = 42,
) -> dict:
    """Compute persistent homology on trajectory embeddings.

    Args:
        embeddings: (N, K) point cloud from ngram_embed
        max_dim: Maximum homology dimension (1 = H₀ + H₁)
        n_landmarks: Number of landmarks (default: min(5000, N//4))
        method: 'witness' (primary), 'maxmin_vr' (fallback), or 'both'
        validate: Whether to compute multi-subsample Betti curves
        n_validation_subsamples: Number of validation subsamples
        validation_subsample_size: Size of each validation subsample
        seed: Random seed

    Returns:
        dict with keys:
            - 'witness': PHResult (if method includes witness)
            - 'maxmin_vr': PHResult (if method includes maxmin_vr)
            - 'summaries': {method_name: persistence_summary}
            - 'validation_betti': averaged Betti curves (if validate=True)
            - 'n_landmarks': actual number of landmarks used
            - 'elapsed_seconds': computation time
    """
    t0 = time.time()
    n = embeddings.shape[0]

    # Adaptive landmark count
    if n_landmarks is None:
        n_landmarks = min(5000, n // 4) if n > 5000 else n
    n_landmarks = min(n_landmarks, n)

    logger.info(
        f"Computing trajectory PH: {n} points × {embeddings.shape[1]} dims, {n_landmarks} landmarks, method={method}"
    )

    results: dict = {
        "n_points": n,
        "n_dims": embeddings.shape[1],
        "n_landmarks": n_landmarks,
        "method": method,
    }
    summaries = {}

    # Witness complex (primary)
    if method in ("witness", "both"):
        logger.info("─── Witness Complex ───")
        ph_witness = _compute_witness(embeddings, max_dim, n_landmarks, seed)
        results["witness"] = ph_witness
        s = persistence_summary(ph_witness)
        summaries["witness"] = s
        for dim_key in ["H0", "H1"]:
            d = s.get(dim_key, {})
            logger.info(f"  {dim_key}: {d.get('n_finite', 0)} features, max={d.get('max_persistence', 0):.4f}")

    # Maxmin VR (fallback / secondary)
    if method in ("maxmin_vr", "both"):
        logger.info("─── Maxmin VR ───")
        ph_vr = _compute_maxmin_vr(embeddings, max_dim, n_landmarks, seed)
        results["maxmin_vr"] = ph_vr
        s = persistence_summary(ph_vr)
        summaries["maxmin_vr"] = s
        for dim_key in ["H0", "H1"]:
            d = s.get(dim_key, {})
            logger.info(f"  {dim_key}: {d.get('n_finite', 0)} features, max={d.get('max_persistence', 0):.4f}")

    results["summaries"] = summaries

    # Multi-subsample validation
    if validate and n > validation_subsample_size:
        logger.info("─── Multi-subsample Betti validation ───")
        results["validation_betti"] = _multi_subsample_betti(
            embeddings,
            n_subsamples=n_validation_subsamples,
            subsample_size=validation_subsample_size,
            max_dim=max_dim,
            seed=seed,
        )
    else:
        results["validation_betti"] = None

    results["elapsed_seconds"] = time.time() - t0
    logger.info(f"PH computation complete in {results['elapsed_seconds']:.1f}s")

    return results
