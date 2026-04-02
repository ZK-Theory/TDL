"""Multi-parameter persistent homology for income-stratified trajectory topology.

Constructs Rips × income lower-star bifiltrations on the P01 PCA embedding
and computes signed measures, Hilbert functions, and rank invariants via
the ``multipers`` library.

Paper 4: Multi-Parameter PH for Poverty Trap Detection.

Usage:
    from trajectory_tda.topology.multipers_bifiltration import (
        BifiltrationResult,
        build_bifiltration,
        compute_signed_measure,
        analyse_income_stratification,
        run_permutation_null,
    )
"""

from __future__ import annotations

import json
import logging
import time
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from numpy.typing import NDArray
from scipy.spatial.distance import pdist

logger = logging.getLogger(__name__)

# Suppress KeOps warnings on Windows
warnings.filterwarnings("ignore", message=".*KeOps.*")
warnings.filterwarnings("ignore", message=".*pykeops.*")

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_DIR = ROOT / "results" / "trajectory_tda_integration"
RESULTS_DIR = ROOT / "results" / "p04_multipers"
FIGURE_DIR = ROOT / "figures" / "trajectory_tda" / "p04"


# ──────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────


@dataclass
class StratificationResult:
    """Income stratification of signed measure mass."""

    low_income_mass: float
    high_income_mass: float
    total_mass: float
    low_income_fraction: float
    n_points: int
    n_low: int
    n_high: int


@dataclass
class QuartileDecomposition:
    """Signed measure mass decomposed by income quartile."""

    masses: list[float]
    boundaries: list[float]
    ratio_q1_q3: float


@dataclass
class SignedMeasureResult:
    """Complete signed measure analysis for one homology degree."""

    degree: int
    points: list[list[float]]
    weights: list[float]
    stratification: StratificationResult
    quartile_decomposition: QuartileDecomposition
    compute_time_s: float


@dataclass
class BifiltrationResult:
    """Full result from a bifiltration computation."""

    n_landmarks: int
    n_simplices: int
    threshold_radius: float
    income_median: float
    income_mean: float
    income_std: float
    grid_strategy: str
    n_income_steps: int
    n_rips_steps: int
    bifiltration_time_s: float
    h0: SignedMeasureResult
    h1: SignedMeasureResult
    income_grid: list[float] = field(default_factory=list)
    rips_grid: list[float] = field(default_factory=list)


@dataclass
class PermutationNullResult:
    """Result from permutation null testing."""

    observed_h1_low_fraction: float
    null_h1_low_fractions: list[float]
    p_value: float
    observed_q1_q3_ratio: float
    null_q1_q3_ratios: list[float]
    p_value_q1_q3: float
    n_permutations: int
    total_time_s: float


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────


def load_embeddings_and_income(
    checkpoint_dir: Path | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Load P01 embeddings and compute per-person income score from sequences.

    Income score: proportion-weighted mean of income bands.
        L=0, M=1, H=2 → score in [0, 2].

    Args:
        checkpoint_dir: Path to P01 checkpoint directory.

    Returns:
        embeddings: (N, 20) PCA embedding.
        income_scores: (N,) continuous income score per person.
    """
    cdir = checkpoint_dir or CHECKPOINT_DIR
    embeddings = np.load(cdir / "embeddings.npy")
    with open(cdir / "01_trajectories_sequences.json") as f:
        sequences = json.load(f)

    if len(sequences) != embeddings.shape[0]:
        msg = (
            f"Sequence count ({len(sequences)}) != embedding rows "
            f"({embeddings.shape[0]})"
        )
        raise ValueError(msg)

    income_map = {"L": 0.0, "M": 1.0, "H": 2.0}
    income_scores = np.array(
        [np.mean([income_map[state[-1]] for state in seq]) for seq in sequences]
    )

    logger.info(
        "Loaded %d embeddings (%s), income: mean=%.2f, std=%.2f",
        len(embeddings),
        embeddings.shape,
        income_scores.mean(),
        income_scores.std(),
    )
    return embeddings, income_scores


# ──────────────────────────────────────────────────────────────────────
# Landmarking
# ──────────────────────────────────────────────────────────────────────


def maxmin_landmarks(
    points: NDArray[np.float64],
    n_landmarks: int,
    seed: int = 42,
) -> NDArray[np.intp]:
    """Select landmarks via greedy maxmin subsampling.

    Args:
        points: (N, D) point cloud.
        n_landmarks: Number of landmarks to select.
        seed: Seed for initial point selection.

    Returns:
        (n_landmarks,) indices into points.
    """
    rng = np.random.RandomState(seed)
    n = points.shape[0]
    indices = np.zeros(n_landmarks, dtype=np.intp)
    indices[0] = rng.randint(n)

    min_dist = np.full(n, np.inf)
    for i in range(1, n_landmarks):
        new_dists = np.linalg.norm(points - points[indices[i - 1]], axis=1)
        min_dist = np.minimum(min_dist, new_dists)
        indices[i] = np.argmax(min_dist)

    return indices


# ──────────────────────────────────────────────────────────────────────
# Grid construction
# ──────────────────────────────────────────────────────────────────────


def build_grid(
    rips_radius: float,
    income: NDArray[np.float64],
    strategy: str = "quantile",
    n_income_steps: int = 20,
    n_rips_steps: int = 20,
) -> list[NDArray[np.float64]]:
    """Build a 2-parameter custom grid for signed measure evaluation.

    Args:
        rips_radius: Maximum Rips distance (first parameter range).
        income: Per-vertex income scores.
        strategy: 'quantile' or 'fixed'.
        n_income_steps: Grid resolution on the income (τ) axis.
        n_rips_steps: Grid resolution on the Rips (ε) axis.

    Returns:
        [rips_grid, income_grid] — two 1D arrays.
    """
    rips_grid = np.linspace(0, rips_radius, n_rips_steps)

    if strategy == "quantile":
        quantiles = np.linspace(0, 100, n_income_steps)
        income_grid = np.unique(np.percentile(income, quantiles))
    elif strategy == "fixed":
        income_grid = np.linspace(income.min(), income.max(), n_income_steps)
    else:
        msg = f"Unknown strategy: {strategy}"
        raise ValueError(msg)

    return [rips_grid, income_grid]


# ──────────────────────────────────────────────────────────────────────
# Bifiltration
# ──────────────────────────────────────────────────────────────────────


def build_bifiltration(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
):
    """Construct Rips × income lower-star bifiltration.

    Args:
        points: (n, D) point cloud (PCA embedding).
        income: (n,) per-vertex income score.
        threshold_radius: Maximum Rips radius.

    Returns:
        SimplexTreeMulti from multipers.
    """
    from multipers.filtrations import RipsLowerstar

    return RipsLowerstar(
        points=points,
        function=income.reshape(-1, 1),
        threshold_radius=threshold_radius,
    )


def auto_rips_radius(
    points: NDArray[np.float64],
    percentile: float = 10.0,
    sample_size: int = 500,
    seed: int = 42,
) -> float:
    """Compute Rips radius from pairwise distance percentile.

    Args:
        points: (n, D) point cloud.
        percentile: Percentile of pairwise distances to use.
        sample_size: Number of points to subsample for distance computation.
        seed: Random seed.

    Returns:
        Threshold radius.
    """
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(points), size=min(sample_size, len(points)), replace=False)
    dists = pdist(points[idx])
    radius = float(np.percentile(dists, percentile))
    logger.info("Auto Rips radius (%gth pctl): %.3f", percentile, radius)
    return radius


# ──────────────────────────────────────────────────────────────────────
# Signed measure computation
# ──────────────────────────────────────────────────────────────────────


def compute_signed_measure(
    st,
    degree: int,
    grid: list[NDArray[np.float64]] | None = None,
    resolution: int = 20,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute signed measure for a homology degree.

    Args:
        st: SimplexTreeMulti from multipers.
        degree: Homology degree (0 or 1).
        grid: Custom [rips_grid, income_grid] arrays.
        resolution: Default resolution if no custom grid.

    Returns:
        (points, weights) arrays.
    """
    import multipers as mp

    kwargs: dict = {"degree": degree}
    if grid is not None:
        kwargs["grid"] = grid
    else:
        kwargs["grid_strategy"] = "regular"
        kwargs["resolution"] = resolution

    sm = mp.signed_measure(st, **kwargs)
    return sm[0]  # (points_array, weights_array)


# ──────────────────────────────────────────────────────────────────────
# Analysis
# ──────────────────────────────────────────────────────────────────────


def analyse_income_stratification(
    pts: NDArray[np.float64],
    weights: NDArray[np.float64],
    income_median: float,
) -> StratificationResult:
    """Analyse how signed measure mass distributes across income levels.

    Args:
        pts: (n, 2) signed measure support points (ε, τ).
        weights: (n,) signed weights.
        income_median: Median income for split.

    Returns:
        StratificationResult with low/high mass breakdown.
    """
    if len(pts) == 0:
        return StratificationResult(
            low_income_mass=0.0,
            high_income_mass=0.0,
            total_mass=0.0,
            low_income_fraction=0.0,
            n_points=0,
            n_low=0,
            n_high=0,
        )

    income_vals = pts[:, 1]
    low_mask = income_vals <= income_median
    abs_weights = np.abs(weights)
    low_mass = float(np.sum(abs_weights[low_mask]))
    high_mass = float(np.sum(abs_weights[~low_mask]))
    total = low_mass + high_mass

    return StratificationResult(
        low_income_mass=low_mass,
        high_income_mass=high_mass,
        total_mass=total,
        low_income_fraction=low_mass / total if total > 0 else 0.0,
        n_points=len(pts),
        n_low=int(np.sum(low_mask)),
        n_high=int(np.sum(~low_mask)),
    )


def quartile_mass(
    pts: NDArray[np.float64],
    weights: NDArray[np.float64],
    income: NDArray[np.float64],
    n_quartiles: int = 4,
) -> QuartileDecomposition:
    """Compute absolute signed measure mass in each income quartile.

    Args:
        pts: (n, 2) signed measure support points.
        weights: (n,) signed weights.
        income: Full income array (for quartile boundaries).
        n_quartiles: Number of quantile bins.

    Returns:
        QuartileDecomposition with per-quartile masses.
    """
    if len(pts) == 0:
        return QuartileDecomposition(
            masses=[0.0] * n_quartiles,
            boundaries=[0.0] * (n_quartiles + 1),
            ratio_q1_q3=0.0,
        )

    boundaries = np.percentile(income, np.linspace(0, 100, n_quartiles + 1))
    masses = []
    income_vals = pts[:, 1]
    abs_w = np.abs(weights)

    for i in range(n_quartiles):
        lo, hi = boundaries[i], boundaries[i + 1]
        if i == n_quartiles - 1:
            mask = (income_vals >= lo) & (income_vals <= hi)
        else:
            mask = (income_vals >= lo) & (income_vals < hi)
        masses.append(float(np.sum(abs_w[mask])))

    q1 = masses[0] if masses[0] > 0 else 1e-10
    q3 = masses[2] if len(masses) > 2 and masses[2] > 0 else 1e-10
    ratio = q1 / q3

    return QuartileDecomposition(
        masses=masses,
        boundaries=boundaries.tolist(),
        ratio_q1_q3=ratio,
    )


# ──────────────────────────────────────────────────────────────────────
# Full pipeline
# ──────────────────────────────────────────────────────────────────────


def run_bifiltration(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
    grid_strategy: str = "quantile",
    n_income_steps: int = 20,
    n_rips_steps: int = 20,
) -> BifiltrationResult:
    """Run full signed measure computation on a bifiltration.

    Args:
        points: (n, D) landmark point cloud.
        income: (n,) per-landmark income scores.
        threshold_radius: Rips radius.
        grid_strategy: 'quantile' or 'fixed'.
        n_income_steps: Income grid resolution.
        n_rips_steps: Rips grid resolution.

    Returns:
        BifiltrationResult containing H0 and H1 signed measure analyses.
    """
    income_median = float(np.median(income))

    t0 = time.time()
    st = build_bifiltration(points, income, threshold_radius)
    t_bif = time.time() - t0
    logger.info("Bifiltration: %d simplices, %.1fs", st.num_simplices, t_bif)

    grid = build_grid(
        threshold_radius, income, grid_strategy, n_income_steps, n_rips_steps
    )

    results = {}
    for degree in [0, 1]:
        t0 = time.time()
        pts_sm, w_sm = compute_signed_measure(st, degree=degree, grid=grid)
        t_sm = time.time() - t0

        strat = analyse_income_stratification(pts_sm, w_sm, income_median)
        qm = quartile_mass(pts_sm, w_sm, income)

        results[degree] = SignedMeasureResult(
            degree=degree,
            points=pts_sm.tolist() if len(pts_sm) > 0 else [],
            weights=w_sm.tolist() if len(w_sm) > 0 else [],
            stratification=strat,
            quartile_decomposition=qm,
            compute_time_s=t_sm,
        )
        logger.info(
            "H%d: %d pts, low_frac=%.3f, quartiles=%s (%.1fs)",
            degree,
            strat.n_points,
            strat.low_income_fraction,
            [f"{m:.0f}" for m in qm.masses],
            t_sm,
        )

    return BifiltrationResult(
        n_landmarks=len(points),
        n_simplices=st.num_simplices,
        threshold_radius=threshold_radius,
        income_median=income_median,
        income_mean=float(income.mean()),
        income_std=float(income.std()),
        grid_strategy=grid_strategy,
        n_income_steps=n_income_steps,
        n_rips_steps=n_rips_steps,
        bifiltration_time_s=t_bif,
        h0=results[0],
        h1=results[1],
        income_grid=grid[1].tolist(),
        rips_grid=grid[0].tolist(),
    )


# ──────────────────────────────────────────────────────────────────────
# Permutation null testing
# ──────────────────────────────────────────────────────────────────────


def _single_permutation(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
    grid: list[NDArray[np.float64]],
    income_median: float,
    seed: int,
) -> tuple[float, float]:
    """Run one income-shuffle permutation.

    Returns:
        (h1_low_fraction, q1_q3_ratio) under shuffled income.
    """
    rng = np.random.RandomState(seed)
    shuffled_income = income.copy()
    rng.shuffle(shuffled_income)

    st = build_bifiltration(points, shuffled_income, threshold_radius)
    pts_h1, w_h1 = compute_signed_measure(st, degree=1, grid=grid)

    strat = analyse_income_stratification(pts_h1, w_h1, income_median)
    qm = quartile_mass(pts_h1, w_h1, income)

    return strat.low_income_fraction, qm.ratio_q1_q3


def run_permutation_null(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
    grid_strategy: str = "quantile",
    n_income_steps: int = 20,
    n_rips_steps: int = 20,
    n_permutations: int = 999,
    n_jobs: int = -1,
    seed: int = 42,
) -> tuple[BifiltrationResult, PermutationNullResult]:
    """Run observed bifiltration + permutation null test.

    Args:
        points: (n, D) landmark point cloud.
        income: (n,) per-landmark income scores.
        threshold_radius: Rips radius.
        grid_strategy: Grid type ('quantile' or 'fixed').
        n_income_steps: Income grid resolution.
        n_rips_steps: Rips grid resolution.
        n_permutations: Number of income-shuffle permutations.
        n_jobs: Parallelism for joblib (-1 = all cores).
        seed: Base random seed.

    Returns:
        (observed_result, null_result) tuple.
    """
    t_total = time.time()

    # Observed
    logger.info("Computing observed bifiltration...")
    observed = run_bifiltration(
        points,
        income,
        threshold_radius,
        grid_strategy,
        n_income_steps,
        n_rips_steps,
    )

    # Build grid once (same grid for all permutations)
    grid = build_grid(
        threshold_radius, income, grid_strategy, n_income_steps, n_rips_steps
    )
    income_median = float(np.median(income))

    # Permutations
    logger.info("Running %d income-label permutations...", n_permutations)
    rng = np.random.RandomState(seed)
    perm_seeds = rng.randint(0, 2**31, size=n_permutations).tolist()

    null_results = Parallel(n_jobs=n_jobs, verbose=10)(
        delayed(_single_permutation)(
            points, income, threshold_radius, grid, income_median, s
        )
        for s in perm_seeds
    )

    null_fracs = [r[0] for r in null_results]
    null_ratios = [r[1] for r in null_results]

    obs_frac = observed.h1.stratification.low_income_fraction
    obs_ratio = observed.h1.quartile_decomposition.ratio_q1_q3

    null_fracs_arr = np.array(null_fracs)
    null_ratios_arr = np.array(null_ratios)

    # Two-sided p-value: how extreme is observed relative to null distribution?
    null_mean_frac = float(np.mean(null_fracs_arr))
    p_frac = float(
        np.sum(
            np.abs(null_fracs_arr - null_mean_frac) >= abs(obs_frac - null_mean_frac)
        )
        / n_permutations
    )
    null_mean_ratio = float(np.mean(null_ratios_arr))
    p_ratio = float(
        np.sum(
            np.abs(null_ratios_arr - null_mean_ratio)
            >= abs(obs_ratio - null_mean_ratio)
        )
        / n_permutations
    )

    t_elapsed = time.time() - t_total
    logger.info(
        "Permutation test complete (%.0fs). "
        "H1 low_frac: observed=%.3f, null_mean=%.3f, p=%.4f",
        t_elapsed,
        obs_frac,
        float(np.mean(null_fracs)),
        p_frac,
    )
    logger.info(
        "Q1/Q3 ratio: observed=%.3f, null_mean=%.3f, p=%.4f",
        obs_ratio,
        float(np.mean(null_ratios)),
        p_ratio,
    )

    null = PermutationNullResult(
        observed_h1_low_fraction=obs_frac,
        null_h1_low_fractions=null_fracs,
        p_value=p_frac,
        observed_q1_q3_ratio=obs_ratio,
        null_q1_q3_ratios=null_ratios,
        p_value_q1_q3=p_ratio,
        n_permutations=n_permutations,
        total_time_s=t_elapsed,
    )

    return observed, null


# ──────────────────────────────────────────────────────────────────────
# P01 baseline comparison
# ──────────────────────────────────────────────────────────────────────


def run_p01_baseline_comparison(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
) -> dict:
    """Compare bifiltration PH to standard single-parameter Rips PH.

    Computes VR PH on all landmarks (ignoring income) and on low-income
    subset (τ <= Q1), then compares to the bifiltration signed measure.

    Uses ripser for efficiency on large point clouds (>2,000 points).

    Args:
        points: (n, D) landmark point cloud.
        income: (n,) per-landmark income scores.
        threshold_radius: Rips radius for comparison.

    Returns:
        Dict with PH summary for full, low-income, and high-income subsets.
    """
    from ripser import ripser as ripser_fn

    def _rips_ph(pts: NDArray[np.float64], label: str) -> dict:
        if len(pts) < 3:
            return {"label": label, "n_points": len(pts), "h0_count": 0, "h1_count": 0}

        logger.info(
            "Ripser PH on %s: %d points, radius=%.3f", label, len(pts), threshold_radius
        )
        result = ripser_fn(pts, maxdim=1, thresh=threshold_radius, do_cocycles=False)

        h0_dgm = result["dgms"][0]
        h1_dgm = result["dgms"][1]

        # H0: exclude infinite bar (one component persists forever)
        h0_finite = h0_dgm[np.isfinite(h0_dgm[:, 1])]
        h0_persist = (
            (h0_finite[:, 1] - h0_finite[:, 0]).tolist() if len(h0_finite) > 0 else []
        )
        h1_persist = (h1_dgm[:, 1] - h1_dgm[:, 0]).tolist() if len(h1_dgm) > 0 else []

        return {
            "label": label,
            "n_points": len(pts),
            "h0_count": len(h0_persist),
            "h1_count": len(h1_dgm),
            "h0_total_persistence": float(sum(h0_persist)) if h0_persist else 0.0,
            "h1_total_persistence": float(sum(h1_persist)) if h1_persist else 0.0,
            "h0_max_persistence": float(max(h0_persist)) if h0_persist else 0.0,
            "h1_max_persistence": float(max(h1_persist)) if h1_persist else 0.0,
        }

    q1 = float(np.percentile(income, 25))
    q3 = float(np.percentile(income, 75))

    low_mask = income <= q1
    high_mask = income >= q3

    full_ph = _rips_ph(points, "full")
    low_ph = _rips_ph(points[low_mask], "low_income_q1")
    high_ph = _rips_ph(points[high_mask], "high_income_q4")

    # Key comparison: H1 features per point
    n_full = full_ph["n_points"]
    n_low = low_ph["n_points"]
    n_high = high_ph["n_points"]

    result = {
        "full": full_ph,
        "low_income_q1": low_ph,
        "high_income_q4": high_ph,
        "h1_density_full": full_ph["h1_count"] / n_full if n_full > 0 else 0,
        "h1_density_low": low_ph["h1_count"] / n_low if n_low > 0 else 0,
        "h1_density_high": high_ph["h1_count"] / n_high if n_high > 0 else 0,
    }

    logger.info(
        "P01 baseline: full H1=%d (%d pts), low H1=%d (%d pts), high H1=%d (%d pts)",
        full_ph["h1_count"],
        n_full,
        low_ph["h1_count"],
        n_low,
        high_ph["h1_count"],
        n_high,
    )
    return result


# ──────────────────────────────────────────────────────────────────────
# GMM regime overlay
# ──────────────────────────────────────────────────────────────────────


def compute_regime_overlay(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    landmark_indices: NDArray[np.intp],
    gmm_path: Path | None = None,
    embeddings_full: NDArray[np.float64] | None = None,
) -> dict:
    """Overlay P01's GMM regime labels on signed measure support.

    Assigns each landmark to a GMM regime, then computes signed measure
    mass conditional on regime label.

    Args:
        points: (n_landmarks, D) landmark points.
        income: (n_landmarks,) income scores.
        landmark_indices: Indices into the full embedding.
        gmm_path: Path to fitted GMM joblib file.
        embeddings_full: Full embedding for GMM prediction.

    Returns:
        Dict with per-regime signed measure statistics.
    """
    import joblib

    gpath = gmm_path or (CHECKPOINT_DIR / "05_gmm.joblib")
    gmm = joblib.load(gpath)

    # Predict regime labels for landmarks
    if embeddings_full is not None:
        all_labels = gmm.predict(embeddings_full)
        regime_labels = all_labels[landmark_indices]
    else:
        regime_labels = gmm.predict(points)

    unique_regimes = np.unique(regime_labels)
    logger.info(
        "GMM regimes for landmarks: %s",
        {int(r): int(np.sum(regime_labels == r)) for r in unique_regimes},
    )

    # Compute income statistics per regime
    regime_income = {}
    for r in unique_regimes:
        mask = regime_labels == r
        r_income = income[mask]
        regime_income[int(r)] = {
            "count": int(np.sum(mask)),
            "mean_income": float(r_income.mean()),
            "std_income": float(r_income.std()),
            "low_income_pct": float(np.mean(r_income <= np.median(income))),
        }

    return {
        "regime_labels": regime_labels.tolist(),
        "regime_income_stats": regime_income,
        "n_regimes": len(unique_regimes),
    }


# ──────────────────────────────────────────────────────────────────────
# Serialisation
# ──────────────────────────────────────────────────────────────────────


@dataclass
class HilbertResult:
    """Hilbert function analysis for one homology degree."""

    degree: int
    resolution: tuple[int, int]
    grid_rips: list[float]
    grid_income: list[float]
    heatmap: list[list[float]]
    total_mass: float
    low_income_fraction: float
    quartile_masses: list[float]
    compute_time_s: float


@dataclass
class RankInvariantResult:
    """Rank invariant analysis for one homology degree."""

    degree: int
    n_features: int
    birth_rips: list[float]
    birth_income: list[float]
    death_rips: list[float]
    death_income: list[float]
    weights: list[float]
    total_weight: float
    income_persistence_stats: dict
    compute_time_s: float


def compute_hilbert_function(
    st,
    degree: int,
    grid: list[NDArray[np.float64]],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute Hilbert function signed measure for a homology degree.

    The Hilbert function H_k(eps, tau) = dim H_k(K_{eps,tau}) counts
    features *alive* at each grid point (state view, not differential).

    Args:
        st: SimplexTreeMulti from multipers.
        degree: Homology degree (0 or 1).
        grid: [rips_grid, income_grid] arrays.

    Returns:
        (points, weights) from Hilbert-based signed measure.
    """
    import multipers as mp

    sm = mp.signed_measure(st, degree=degree, invariant="hilbert", grid=grid)
    return sm[0]


def compute_rank_invariant(
    st,
    degree: int,
    grid: list[NDArray[np.float64]],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute rank invariant signed measure for a homology degree.

    The rank invariant captures (birth_eps, birth_tau, death_eps, death_tau)
    for features — which features persist across parameter ranges.

    Args:
        st: SimplexTreeMulti from multipers.
        degree: Homology degree (0 or 1).
        grid: [rips_grid, income_grid] arrays.

    Returns:
        (points, weights) where points is (n, 4) with columns
        [birth_eps, birth_tau, death_eps, death_tau].
    """
    import multipers as mp

    sm = mp.signed_measure(st, degree=degree, invariant="rank", grid=grid)
    return sm[0]


def analyse_hilbert_function(
    pts: NDArray[np.float64],
    weights: NDArray[np.float64],
    rips_grid: NDArray[np.float64],
    income_grid: NDArray[np.float64],
    income: NDArray[np.float64],
    degree: int,
    compute_time: float,
) -> HilbertResult:
    """Build a 2D heatmap from Hilbert function signed measure.

    Args:
        pts: (n, 2) support points (eps, tau).
        weights: (n,) weights.
        rips_grid: Rips axis values.
        income_grid: Income axis values.
        income: Full income array for quartile boundaries.
        degree: Homology degree.
        compute_time: Computation time in seconds.

    Returns:
        HilbertResult with heatmap and income stratification.
    """
    n_rips = len(rips_grid)
    n_income = len(income_grid)
    heatmap = np.zeros((n_rips, n_income))

    if len(pts) > 0:
        for i in range(len(pts)):
            eps_val, tau_val = pts[i, 0], pts[i, 1]
            ri = int(np.argmin(np.abs(rips_grid - eps_val)))
            ci = int(np.argmin(np.abs(income_grid - tau_val)))
            heatmap[ri, ci] += weights[i]

    income_median = float(np.median(income))
    abs_w = np.abs(weights) if len(weights) > 0 else np.array([])
    total_mass = float(np.sum(abs_w))

    if len(pts) > 0:
        income_vals = pts[:, 1]
        low_mask = income_vals <= income_median
        low_frac = float(np.sum(abs_w[low_mask])) / total_mass if total_mass > 0 else 0
    else:
        low_frac = 0.0

    boundaries = np.percentile(income, [0, 25, 50, 75, 100])
    quartile_masses = []
    if len(pts) > 0:
        income_vals = pts[:, 1]
        for i in range(4):
            lo, hi = boundaries[i], boundaries[i + 1]
            if i == 3:
                mask = (income_vals >= lo) & (income_vals <= hi)
            else:
                mask = (income_vals >= lo) & (income_vals < hi)
            quartile_masses.append(float(np.sum(abs_w[mask])))
    else:
        quartile_masses = [0.0] * 4

    return HilbertResult(
        degree=degree,
        resolution=(n_rips, n_income),
        grid_rips=rips_grid.tolist(),
        grid_income=income_grid.tolist(),
        heatmap=heatmap.tolist(),
        total_mass=total_mass,
        low_income_fraction=low_frac,
        quartile_masses=quartile_masses,
        compute_time_s=compute_time,
    )


def analyse_rank_invariant(
    pts: NDArray[np.float64],
    weights: NDArray[np.float64],
    income: NDArray[np.float64],
    degree: int,
    compute_time: float,
) -> RankInvariantResult:
    """Analyse rank invariant: which features persist across income levels?

    Args:
        pts: (n, 4) with columns [birth_eps, birth_tau, death_eps, death_tau].
        weights: (n,) weights.
        income: Full income array for quartile boundaries.
        degree: Homology degree.
        compute_time: Computation time in seconds.

    Returns:
        RankInvariantResult with persistence-across-income statistics.
    """
    if len(pts) == 0:
        return RankInvariantResult(
            degree=degree,
            n_features=0,
            birth_rips=[],
            birth_income=[],
            death_rips=[],
            death_income=[],
            weights=[],
            total_weight=0.0,
            income_persistence_stats={},
            compute_time_s=compute_time,
        )

    birth_income = pts[:, 1]
    death_income = pts[:, 3]
    abs_w = np.abs(weights)

    # Income persistence: how far does each feature persist along the income axis?
    income_persistence = death_income - birth_income
    # Handle inf values (features that persist to infinity)
    finite_mask = np.isfinite(income_persistence)

    income_median = float(np.median(income))
    q1 = float(np.percentile(income, 25))
    q3 = float(np.percentile(income, 75))

    # Features born at LOW income (below median)
    born_low = birth_income <= income_median
    # Of those, how many survive to HIGH income?
    survive_to_high = born_low & (death_income > income_median)
    # Features born at low income that die before reaching high income
    confined_to_low = born_low & (death_income <= income_median) & finite_mask

    # Features born at Q1 that survive to Q3
    born_q1 = birth_income <= q1
    survive_to_q3 = born_q1 & (death_income >= q3)

    # Weighted versions
    total_w = float(np.sum(abs_w))
    born_low_w = float(np.sum(abs_w[born_low]))
    survive_high_w = float(np.sum(abs_w[survive_to_high]))
    confined_low_w = float(np.sum(abs_w[confined_to_low]))
    born_q1_w = float(np.sum(abs_w[born_q1]))
    survive_q3_w = float(np.sum(abs_w[survive_to_q3]))

    # Features that persist to infinity (never die in the bifiltration)
    inf_mask = ~np.isfinite(death_income)
    inf_w = float(np.sum(abs_w[inf_mask]))

    stats = {
        "n_total": int(len(pts)),
        "total_weight": total_w,
        "n_born_low": int(np.sum(born_low)),
        "w_born_low": born_low_w,
        "frac_born_low": born_low_w / total_w if total_w > 0 else 0,
        "n_survive_to_high": int(np.sum(survive_to_high)),
        "w_survive_to_high": survive_high_w,
        "frac_survive_to_high": survive_high_w / born_low_w if born_low_w > 0 else 0,
        "n_confined_to_low": int(np.sum(confined_to_low)),
        "w_confined_to_low": confined_low_w,
        "frac_confined_to_low": confined_low_w / born_low_w if born_low_w > 0 else 0,
        "n_born_q1": int(np.sum(born_q1)),
        "w_born_q1": born_q1_w,
        "n_survive_q1_to_q3": int(np.sum(survive_to_q3)),
        "w_survive_q1_to_q3": survive_q3_w,
        "frac_q1_surviving_to_q3": survive_q3_w / born_q1_w if born_q1_w > 0 else 0,
        "n_persist_to_inf": int(np.sum(inf_mask)),
        "w_persist_to_inf": inf_w,
        "frac_persist_to_inf": inf_w / total_w if total_w > 0 else 0,
    }

    # Mean income persistence for finite features
    if np.sum(finite_mask) > 0:
        finite_ip = income_persistence[finite_mask]
        finite_w = abs_w[finite_mask]
        stats["mean_income_persistence"] = float(
            np.average(finite_ip, weights=finite_w)
        )
        stats["median_income_persistence"] = float(np.median(finite_ip))
    else:
        stats["mean_income_persistence"] = float("inf")
        stats["median_income_persistence"] = float("inf")

    return RankInvariantResult(
        degree=degree,
        n_features=len(pts),
        birth_rips=pts[:, 0].tolist(),
        birth_income=pts[:, 1].tolist(),
        death_rips=pts[:, 2].tolist(),
        death_income=pts[:, 3].tolist(),
        weights=weights.tolist(),
        total_weight=total_w,
        income_persistence_stats=stats,
        compute_time_s=compute_time,
    )


def run_appendix_b(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
    resolutions: list[int] | None = None,
) -> dict:
    """Run Appendix B analyses: Hilbert function + rank invariant.

    Args:
        points: (n, D) landmark point cloud.
        income: (n,) per-landmark income scores.
        threshold_radius: Rips radius.
        resolutions: List of grid resolutions to compute (default [10, 20]).

    Returns:
        Dict with results keyed by invariant and resolution.
    """
    if resolutions is None:
        resolutions = [10, 20]

    st = build_bifiltration(points, income, threshold_radius)

    results = {}

    for res in resolutions:
        grid = build_grid(threshold_radius, income, "quantile", res, res)
        key = f"{res}x{res}"

        # Hilbert function — H0 and H1
        for degree in [0, 1]:
            t0 = time.time()
            pts_h, w_h = compute_hilbert_function(st, degree=degree, grid=grid)
            t_hf = time.time() - t0

            hf_result = analyse_hilbert_function(
                pts_h, w_h, grid[0], grid[1], income, degree, t_hf
            )
            results[f"hilbert_H{degree}_{key}"] = hf_result
            logger.info(
                "Hilbert H%d (%s): %d pts, low_frac=%.3f, total=%.0f (%.1fs)",
                degree,
                key,
                len(pts_h),
                hf_result.low_income_fraction,
                hf_result.total_mass,
                t_hf,
            )

        # Rank invariant — H1 only (H0 rank invariant less informative)
        t0 = time.time()
        pts_r, w_r = compute_rank_invariant(st, degree=1, grid=grid)
        t_ri = time.time() - t0

        ri_result = analyse_rank_invariant(pts_r, w_r, income, 1, t_ri)
        results[f"rank_H1_{key}"] = ri_result
        logger.info(
            "Rank H1 (%s): %d features, born_low=%.3f, "
            "survive_to_high=%.3f, confined=%.3f (%.1fs)",
            key,
            ri_result.n_features,
            ri_result.income_persistence_stats.get("frac_born_low", 0),
            ri_result.income_persistence_stats.get("frac_survive_to_high", 0),
            ri_result.income_persistence_stats.get("frac_confined_to_low", 0),
            t_ri,
        )

    return results


def save_results(
    bifiltration: BifiltrationResult,
    null: PermutationNullResult | None,
    baseline: dict | None,
    regime: dict | None,
    appendix_b: dict | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Save all results to JSON.

    Args:
        bifiltration: Observed bifiltration result.
        null: Permutation null result (if computed).
        baseline: P01 baseline comparison (if computed).
        regime: GMM regime overlay (if computed).
        appendix_b: Hilbert function and rank invariant results.
        output_dir: Output directory.

    Returns:
        Path to saved JSON file.
    """
    odir = output_dir or RESULTS_DIR
    odir.mkdir(parents=True, exist_ok=True)

    data = {"bifiltration": asdict(bifiltration)}
    if null is not None:
        data["permutation_null"] = asdict(null)
    if baseline is not None:
        data["p01_baseline"] = baseline
    if regime is not None:
        data["gmm_regime_overlay"] = regime
    if appendix_b is not None:
        data["appendix_b"] = {k: asdict(v) for k, v in appendix_b.items()}

    path = odir / "p04_results.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Results saved to %s", path)
    return path
