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
        from gudhi.wasserstein import wasserstein_distance as _gudhi_wd

        dgm1 = np.column_stack([f1[:, 0], f1[:, 1]])
        dgm2 = np.column_stack([f2[:, 0], f2[:, 1]])
        return float(_gudhi_wd(dgm1, dgm2, order=p, internal_p=2))
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
# W₂ test construction: mean-vs-mean T_ratio with BCa and delta-method CI
# ─────────────────────────────────────────────────────────────────────


def compute_w2_ratio_bca_ci(
    w_obs: np.ndarray,
    w_null_null: np.ndarray,
    n_boot: int = 9999,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """BCa bootstrap CI for T_ratio = mean(W_obs_null) / mean(W_null_null).

    Supports Case A (2D matrix input: rows are obs/null diagrams, columns are
    null draws) and Case B (1D array of pre-computed pairwise distances).
    2D inputs are flattened before computing the ratio.

    BCa corrects for bias and skewness in the bootstrap distribution using the
    bias-correction constant z0 and jackknife-estimated acceleration a.

    Args:
        w_obs: W₂ distances between observed and null draws. Shape (n_obs,) or
            (n_obs, n_null) for Case A matrix input.
        w_null_null: W₂ distances between pairs of null draws. Shape (n_null,)
            or (n_null, n_null) for Case A matrix input.
        n_boot: Number of bootstrap replicates (default 9999).
        alpha: Two-sided significance level (default 0.05 → 95% CI).
        seed: Random seed for reproducibility.

    Returns:
        Tuple (T_ratio, ci_lower, ci_upper).

    Raises:
        ValueError: If either array is empty or contains non-positive values
            that would make the ratio undefined.
    """
    from scipy.stats import norm

    w_obs_1d = np.asarray(w_obs, dtype=np.float64).ravel()
    w_nn_1d = np.asarray(w_null_null, dtype=np.float64).ravel()

    if len(w_obs_1d) == 0 or len(w_nn_1d) == 0:
        raise ValueError("w_obs and w_null_null must be non-empty arrays.")
    if len(w_obs_1d) == 1 or len(w_nn_1d) == 1:
        raise ValueError(
            "BCa CI requires at least 2 observations in each array; "
            f"got n_obs={len(w_obs_1d)}, n_null={len(w_nn_1d)}."
        )

    mean_obs = w_obs_1d.mean()
    mean_nn = w_nn_1d.mean()
    if mean_nn == 0.0:
        raise ValueError("mean(w_null_null) is zero; T_ratio is undefined.")

    t_obs = mean_obs / mean_nn

    # Bootstrap distribution
    rng = np.random.default_rng(seed)
    n_o, n_n = len(w_obs_1d), len(w_nn_1d)
    boot_ratios = np.empty(n_boot)
    for b in range(n_boot):
        b_obs = rng.choice(w_obs_1d, size=n_o, replace=True)
        b_nn = rng.choice(w_nn_1d, size=n_n, replace=True)
        denom = b_nn.mean()
        boot_ratios[b] = b_obs.mean() / denom if denom > 0 else np.nan

    valid = boot_ratios[~np.isnan(boot_ratios)]
    if len(valid) < n_boot // 2:
        raise ValueError("Too many degenerate bootstrap replicates (mean_null≈0).")

    # Bias-correction constant z0
    z0 = float(norm.ppf(np.mean(valid < t_obs) or 1e-10))

    # Jackknife acceleration constant a (combined over both samples)
    jack_obs = np.array(
        [(np.delete(w_obs_1d, i).mean() / mean_nn) for i in range(n_o)]
    )
    jack_nn = np.array(
        [(mean_obs / np.delete(w_nn_1d, j).mean()) for j in range(n_n)]
    )
    deltas = np.concatenate([jack_obs, jack_nn])
    delta_mean = deltas.mean()
    d = delta_mean - deltas
    denom_a = 6.0 * (np.sum(d**2) ** 1.5)
    a = float(np.sum(d**3) / denom_a) if denom_a > 0 else 0.0

    # BCa-adjusted percentiles
    z_alpha_lo = norm.ppf(alpha / 2)
    z_alpha_hi = norm.ppf(1 - alpha / 2)

    def _bca_pct(z_a: float) -> float:
        num = z0 + z_a
        adj = z0 + num / (1.0 - a * num)
        return float(norm.cdf(adj))

    p_lo = _bca_pct(z_alpha_lo)
    p_hi = _bca_pct(z_alpha_hi)
    p_lo = np.clip(p_lo, 0.001, 0.999)
    p_hi = np.clip(p_hi, 0.001, 0.999)

    sorted_boot = np.sort(valid)
    n_v = len(sorted_boot)
    ci_lower = float(sorted_boot[int(p_lo * n_v)])
    ci_upper = float(sorted_boot[min(int(p_hi * n_v), n_v - 1)])

    return t_obs, ci_lower, ci_upper


def compute_w2_ratio_delta_ci(
    t_ratio: float,
    se_obs: float,
    se_null: float,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Delta-method CI for T_ratio using log-normal approximation.

    Fallback for when only summary statistics (not the full null matrix) are
    stored. Uses a first-order delta-method log-normal approximation:
    SE(log T) ≈ sqrt(cv_obs² + cv_null²), where cv = SE/mean.

    Args:
        t_ratio: T_ratio = mean(W_obs_null) / mean(W_null_null).
        se_obs: Relative SE of mean(W_obs_null): std_obs / (sqrt(n) * mean_obs).
            This is the coefficient of variation of the numerator estimator.
        se_null: Relative SE of mean(W_null_null): std_null / (sqrt(n) * mean_null).
            This is the coefficient of variation of the denominator estimator.
        alpha: Two-sided significance level (default 0.05 → 95% CI).

    Returns:
        Tuple (ci_lower, ci_upper).
    """
    from scipy.stats import norm

    z = float(norm.ppf(1 - alpha / 2))
    se_log_t = float(np.sqrt(se_obs**2 + se_null**2))
    ci_lower = float(t_ratio * np.exp(-z * se_log_t))
    ci_upper = float(t_ratio * np.exp(z * se_log_t))
    return ci_lower, ci_upper


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
