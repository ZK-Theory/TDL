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


def _import_exact_wasserstein_solver():  # type: ignore[no-untyped-def]
    """Return gudhi's exact (POT/EMD optimal-transport) Wasserstein callable.

    ``gudhi.wasserstein`` requires POT (``ot``) to be importable; when POT is
    absent the import raises :class:`ImportError`. This helper returns the
    solver callable when available and ``None`` when it is not, so the caller
    can decide — raise (default) or explicit opt-in fallback — rather than
    silently degrading to a different statistic.
    """
    try:
        from gudhi.wasserstein import wasserstein_distance as gudhi_wd
    except ImportError:
        return None
    return gudhi_wd


def wasserstein_distance(
    ph1: PHResult,
    ph2: PHResult,
    dim: int = 1,
    p: int = 2,
    min_persistence: float = 0.0,
    *,
    allow_greedy_fallback: bool = False,
) -> float:
    """Exact p-Wasserstein distance between persistence diagrams.

    Uses gudhi's POT/EMD optimal-transport solver
    (``order=p, internal_p=2``). When POT (``ot``) is not importable the exact
    solver is unavailable; by default this raises :class:`RuntimeError` rather
    than silently substituting the greedy persistence-rank matching below,
    which is **not** optimal transport and inflates H1 distances (~18x on the
    frozen USoc headline; WT-1c, 2026-07-14). The greedy path is reachable only
    by passing ``allow_greedy_fallback=True`` and it emits a loud warning
    marking its output convention as ``greedy_rank``.

    Args:
        ph1, ph2: PHResult objects to compare.
        dim: Homology dimension.
        p: Wasserstein-p (default 2).
        min_persistence: Minimum lifetime to include.
        allow_greedy_fallback: When True *and* POT is unavailable, fall back to
            the greedy persistence-rank matching (convention ``greedy_rank``,
            NOT optimal transport) instead of raising. Default False. Has no
            effect when POT is available — the exact solver is always used then.

    Returns:
        Wasserstein distance (float). Exact optimal transport unless the
        opt-in greedy fallback was taken (see ``allow_greedy_fallback``).

    Raises:
        RuntimeError: If the exact solver (POT) is unavailable and
            ``allow_greedy_fallback`` is False.
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

    # Exact optimal transport via gudhi's POT/EMD solver. Refuse to silently
    # substitute the greedy fallback below when POT is absent — that path is
    # NOT optimal transport (see WT-1c, 2026-07-14). A real error inside the
    # gudhi call is intentionally *not* caught here: it propagates rather than
    # degrading to greedy.
    exact_wd = _import_exact_wasserstein_solver()
    if exact_wd is not None:
        dgm1 = np.column_stack([f1[:, 0], f1[:, 1]])
        dgm2 = np.column_stack([f2[:, 0], f2[:, 1]])
        return float(exact_wd(dgm1, dgm2, order=p, internal_p=2))

    if not allow_greedy_fallback:
        raise RuntimeError(
            "Exact Wasserstein-p requires POT (`ot`), but `gudhi.wasserstein` "
            "is not importable. Refusing to silently fall back to greedy "
            "persistence-rank matching (convention='greedy_rank'), which is not "
            "optimal transport and inflates H1 distances (~18x on the frozen "
            "USoc headline; see WT-1c 2026-07-14). Install POT (bundled in the "
            "project dependencies since 2026-06-16) or pass "
            "allow_greedy_fallback=True to explicitly accept the greedy "
            "approximation."
        )

    logger.warning(
        "wasserstein_distance: POT unavailable and allow_greedy_fallback=True — "
        "using GREEDY persistence-rank matching (convention='greedy_rank'). This "
        "is NOT optimal transport; H1 distances may be inflated (~18x vs exact "
        "W2 on the frozen USoc headline). See WT-1c 2026-07-14."
    )

    # Fallback: greedy matching by persistence (opt-in only; see warning above).
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

    Uses ``scipy.stats.bootstrap`` with ``method='BCa'``, which handles the
    bias-correction constant z0 and jackknife acceleration a correctly.

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
        ValueError: If either array is empty or has fewer than 2 elements,
            or if mean(w_null_null) is zero.
    """
    from scipy.stats import bootstrap

    w_obs_1d = np.asarray(w_obs, dtype=np.float64).ravel()
    w_nn_1d = np.asarray(w_null_null, dtype=np.float64).ravel()

    if len(w_obs_1d) == 0 or len(w_nn_1d) == 0:
        raise ValueError("w_obs and w_null_null must be non-empty arrays.")
    if len(w_obs_1d) == 1 or len(w_nn_1d) == 1:
        raise ValueError(
            f"BCa CI requires at least 2 observations in each array; got n_obs={len(w_obs_1d)}, n_null={len(w_nn_1d)}."
        )

    _EPS = 1e-12
    mean_nn = w_nn_1d.mean()
    if mean_nn < _EPS:
        raise ValueError("mean(w_null_null) is zero; T_ratio is undefined.")

    t_obs = float(w_obs_1d.mean() / mean_nn)

    def _ratio_stat(x: np.ndarray, y: np.ndarray) -> float:
        denom = y.mean()
        if denom < _EPS:
            return np.nan  # NaN is safer; scipy bootstrap handles NaN gracefully
        return float(x.mean() / denom)

    res = bootstrap(
        (w_obs_1d, w_nn_1d),
        statistic=_ratio_stat,
        n_resamples=n_boot,
        method="BCa",
        random_state=seed,
        paired=False,
        confidence_level=1 - alpha,
        vectorized=False,
    )
    return t_obs, float(res.confidence_interval.low), float(res.confidence_interval.high)


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

    if t_ratio <= 0:
        raise ValueError("t_ratio must be positive for log-normal CI.")
    if se_obs < 0 or se_null < 0:
        raise ValueError("se_obs and se_null must be non-negative.")

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
