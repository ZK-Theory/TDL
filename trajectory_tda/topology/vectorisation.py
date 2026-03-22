"""
Vectorise persistence diagrams for downstream ML and statistical comparison.

Provides three complementary representations:
1. **Betti curves**: β_k(ε) — reuses existing infrastructure
2. **Persistence landscapes**: Piecewise-linear summary functions L_k
3. **Persistence images**: Resolution-parameterised heatmap representation

Plus Wasserstein distance for diagram comparison.
"""

from __future__ import annotations

import logging

import numpy as np

from poverty_tda.topology.multidim_ph import PHResult, betti_curve

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Persistence Landscapes
# ─────────────────────────────────────────────────────────────────────


def persistence_landscape(
    ph: PHResult,
    dim: int = 1,
    k_max: int = 5,
    n_points: int = 200,
    min_persistence: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute persistence landscape functions L_1, ..., L_k.

    For each persistence pair (b, d), the tent function is:
        f(t) = max(0, min(t - b, d - t))

    The k-th landscape L_k(t) is the k-th largest tent function value at t.

    Args:
        ph: PHResult with persistence diagrams
        dim: Homology dimension to compute landscapes for
        k_max: Number of landscape functions to compute
        n_points: Resolution of the landscape
        min_persistence: Minimum lifetime to include

    Returns:
        t_values: (n_points,) filtration parameter values
        landscapes: (k_max, n_points) landscape function values
    """
    features = ph.h_features(dim, min_persistence=min_persistence)
    if len(features) == 0:
        return np.linspace(0, 1, n_points), np.zeros((k_max, n_points))

    features = np.array(features)
    births = features[:, 0]
    deaths = features[:, 1]

    # Filter out infinite features
    finite_mask = np.isfinite(deaths)
    births = births[finite_mask]
    deaths = deaths[finite_mask]

    if len(births) == 0:
        return np.linspace(0, 1, n_points), np.zeros((k_max, n_points))

    t_min = births.min()
    t_max = deaths.max()
    t_values = np.linspace(t_min, t_max, n_points)

    # Compute tent functions for all pairs
    n_pairs = len(births)
    tents = np.zeros((n_pairs, n_points))
    for i in range(n_pairs):
        tents[i] = np.maximum(0, np.minimum(t_values - births[i], deaths[i] - t_values))

    # k-th landscape = k-th largest tent at each point
    landscapes = np.zeros((k_max, n_points))
    sorted_tents = np.sort(tents, axis=0)[::-1]  # Descending
    for k in range(min(k_max, n_pairs)):
        landscapes[k] = sorted_tents[k]

    return t_values, landscapes


# ─────────────────────────────────────────────────────────────────────
# Persistence Images
# ─────────────────────────────────────────────────────────────────────


def persistence_image(
    ph: PHResult,
    dim: int = 1,
    resolution: int = 20,
    sigma: float | None = None,
    weight_fn: str = "linear",
    min_persistence: float = 0.0,
) -> np.ndarray:
    """Compute persistence image from a persistence diagram.

    Transforms (birth, persistence) pairs into a 2D image via
    Gaussian kernel density estimation with a weighting function.

    Args:
        ph: PHResult with persistence diagrams
        dim: Homology dimension
        resolution: Grid resolution (image will be resolution × resolution)
        sigma: Gaussian bandwidth (default: auto from data range)
        weight_fn: Weighting function: 'linear' (weight by persistence)
                   or 'uniform' (equal weight)
        min_persistence: Minimum lifetime to include

    Returns:
        (resolution, resolution) persistence image
    """
    features = ph.h_features(dim, min_persistence=min_persistence)
    if len(features) == 0:
        return np.zeros((resolution, resolution))

    features = np.array(features)
    births = features[:, 0]
    deaths = features[:, 1]

    finite_mask = np.isfinite(deaths)
    births = births[finite_mask]
    deaths = deaths[finite_mask]

    if len(births) == 0:
        return np.zeros((resolution, resolution))

    # Transform to (birth, persistence) coordinates
    persistence = deaths - births
    points = np.column_stack([births, persistence])

    # Grid bounds
    b_min, b_max = births.min(), births.max()
    p_min, p_max = 0, persistence.max()

    # Add padding
    b_pad = (b_max - b_min) * 0.1 + 1e-6
    p_pad = (p_max - p_min) * 0.1 + 1e-6

    b_grid = np.linspace(b_min - b_pad, b_max + b_pad, resolution)
    p_grid = np.linspace(max(0, p_min - p_pad), p_max + p_pad, resolution)

    if sigma is None:
        sigma = max(
            (b_max - b_min) / resolution,
            (p_max - p_min) / resolution,
            1e-4,
        )

    # Compute image
    image = np.zeros((resolution, resolution))
    for k in range(len(births)):
        # Weight
        if weight_fn == "linear":
            w = persistence[k]
        else:
            w = 1.0

        # Gaussian kernel contribution
        for i in range(resolution):
            for j in range(resolution):
                db = b_grid[i] - points[k, 0]
                dp = p_grid[j] - points[k, 1]
                image[i, j] += w * np.exp(-(db**2 + dp**2) / (2 * sigma**2))

    return image


# ─────────────────────────────────────────────────────────────────────
# Wasserstein Distance
# ─────────────────────────────────────────────────────────────────────


def wasserstein_distance(
    ph1: PHResult,
    ph2: PHResult,
    dim: int = 1,
    p: int = 2,
    min_persistence: float = 0.0,
) -> float:
    """Approximate p-Wasserstein distance between persistence diagrams.

    Uses an optimal transport approximation: matches features by
    persistence value, with unmatched features projected to diagonal.

    Args:
        ph1, ph2: PHResult objects to compare
        dim: Homology dimension
        p: Wasserstein-p (default 2)
        min_persistence: Minimum lifetime to include

    Returns:
        Wasserstein distance (float)
    """
    f1 = ph1.h_features(dim, min_persistence=min_persistence)
    f2 = ph2.h_features(dim, min_persistence=min_persistence)

    f1 = np.array(f1) if len(f1) > 0 else np.empty((0, 2))
    f2 = np.array(f2) if len(f2) > 0 else np.empty((0, 2))

    # Filter infinite features
    if len(f1) > 0:
        f1 = f1[np.isfinite(f1[:, 1])]
    if len(f2) > 0:
        f2 = f2[np.isfinite(f2[:, 1])]

    # If either is empty, distance is sum of persistence / 2 of the other
    if len(f1) == 0 and len(f2) == 0:
        return 0.0
    if len(f1) == 0:
        pers2 = f2[:, 1] - f2[:, 0]
        return float(np.sum((pers2 / 2) ** p) ** (1 / p))
    if len(f2) == 0:
        pers1 = f1[:, 1] - f1[:, 0]
        return float(np.sum((pers1 / 2) ** p) ** (1 / p))

    # Persistence values
    pers1 = f1[:, 1] - f1[:, 0]
    pers2 = f2[:, 1] - f2[:, 0]

    # Use gudhi if available for exact computation
    try:
        import gudhi

        dgm1 = np.column_stack([f1[:, 0], f1[:, 1]])
        dgm2 = np.column_stack([f2[:, 0], f2[:, 1]])
        return float(gudhi.wasserstein.wasserstein_distance(dgm1, dgm2, order=p, internal_p=2))
    except (ImportError, AttributeError):
        pass

    # Fallback: greedy matching by persistence
    # Sort by persistence descending
    idx1 = np.argsort(-pers1)
    idx2 = np.argsort(-pers2)

    total_cost = 0.0
    n_matched = min(len(idx1), len(idx2))

    for i in range(n_matched):
        diff = np.abs(f1[idx1[i]] - f2[idx2[i]])
        total_cost += np.sum(diff**p)

    # Unmatched features: distance to diagonal = persistence / 2
    for i in range(n_matched, len(idx1)):
        total_cost += (pers1[idx1[i]] / 2) ** p * 2
    for i in range(n_matched, len(idx2)):
        total_cost += (pers2[idx2[i]] / 2) ** p * 2

    return float(total_cost ** (1 / p))


# ─────────────────────────────────────────────────────────────────────
# Convenience: vectorise multiple diagrams
# ─────────────────────────────────────────────────────────────────────


def vectorise_diagram(
    ph: PHResult,
    dim: int = 1,
    methods: list[str] | None = None,
    landscape_k: int = 5,
    landscape_points: int = 200,
    image_resolution: int = 20,
    betti_points: int = 200,
    min_persistence: float = 0.0,
) -> dict[str, np.ndarray]:
    """Compute multiple vectorisations of a persistence diagram.

    Args:
        ph: PHResult
        dim: Homology dimension
        methods: List of methods to compute (default: all)
        landscape_k: Number of landscape functions
        landscape_points: Resolution for landscapes
        image_resolution: Resolution for persistence images
        betti_points: Resolution for Betti curves
        min_persistence: Minimum lifetime threshold

    Returns:
        Dict mapping method name to vector/array:
            'betti_curve': (betti_points,)
            'landscape': (landscape_k * landscape_points,) flattened
            'persistence_image': (image_resolution * image_resolution,) flat
    """
    if methods is None:
        methods = ["betti_curve", "landscape", "persistence_image"]

    result = {}

    if "betti_curve" in methods:
        curves = betti_curve(ph, n_points=betti_points)
        if dim in curves:
            _, betti_vals = curves[dim]
            result["betti_curve"] = betti_vals
        else:
            result["betti_curve"] = np.zeros(betti_points)

    if "landscape" in methods:
        _, landscapes = persistence_landscape(
            ph,
            dim=dim,
            k_max=landscape_k,
            n_points=landscape_points,
            min_persistence=min_persistence,
        )
        result["landscape"] = landscapes.flatten()

    if "persistence_image" in methods:
        img = persistence_image(
            ph,
            dim=dim,
            resolution=image_resolution,
            min_persistence=min_persistence,
        )
        result["persistence_image"] = img.flatten()

    return result
