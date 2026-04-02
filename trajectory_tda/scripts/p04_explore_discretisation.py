"""P04 Exploratory Computation: Income Discretisation & Invariant Comparison.

Compares two discretisation strategies for the income filtration parameter:
  A) Quantile thresholds — equal vertex counts per step
  B) Fixed thresholds — uniform spacing on the income score (0, 1, 2)

Tests three multipers invariants for interpretability:
  1) Hilbert function — feature count heatmap across (ε, τ) grid
  2) Signed measure — signed barcode decomposition
  3) Euler surface — quick summary statistic

Runs on 2,000 maxmin landmarks from the P01 checkpoint.

Usage:
    uv run python trajectory_tda/scripts/p04_explore_discretisation.py

Output:
    results/p04_exploration/  — JSON results + PNG figures
"""

from __future__ import annotations

import json
import logging
import time
import warnings
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.distance import pdist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Suppress KeOps warnings on Windows
warnings.filterwarnings("ignore", message=".*KeOps.*")
warnings.filterwarnings("ignore", message=".*pykeops.*")

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_DIR = ROOT / "results" / "trajectory_tda_integration"
OUTPUT_DIR = ROOT / "results" / "p04_exploration"
FIGURE_DIR = ROOT / "figures" / "trajectory_tda" / "p04_exploration"


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────


def load_embeddings_and_income() -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Load P01 embeddings and compute per-person income score from sequences.

    Income score: proportion-weighted mean of income bands.
        L=0, M=1, H=2 → score in [0, 2].

    Returns:
        embeddings: (N, 20) PCA embedding.
        income_scores: (N,) continuous income score per person.
    """
    embeddings = np.load(CHECKPOINT_DIR / "embeddings.npy")
    with open(CHECKPOINT_DIR / "01_trajectories_sequences.json") as f:
        sequences = json.load(f)

    assert len(sequences) == embeddings.shape[0]

    income_map = {"L": 0.0, "M": 1.0, "H": 2.0}
    income_scores = np.array(
        [np.mean([income_map[state[-1]] for state in seq]) for seq in sequences]
    )

    logger.info(
        "Loaded %d embeddings (shape %s), income scores: "
        "mean=%.2f, std=%.2f, min=%.2f, max=%.2f",
        len(embeddings),
        embeddings.shape,
        income_scores.mean(),
        income_scores.std(),
        income_scores.min(),
        income_scores.max(),
    )
    return embeddings, income_scores


# ──────────────────────────────────────────────────────────────────────
# Maxmin landmarking
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

    # Distance from each point to nearest selected landmark
    min_dist = np.full(n, np.inf)

    for i in range(1, n_landmarks):
        # Update distances to include the just-added landmark
        new_dists = np.linalg.norm(points - points[indices[i - 1]], axis=1)
        min_dist = np.minimum(min_dist, new_dists)
        indices[i] = np.argmax(min_dist)

    return indices


# ──────────────────────────────────────────────────────────────────────
# Discretisation strategies
# ──────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────
# Bifiltration computation
# ──────────────────────────────────────────────────────────────────────


def compute_points_per_threshold(
    income: NDArray[np.float64],
    thresholds: NDArray[np.float64],
) -> list[int]:
    """Count cumulative vertices at each threshold (for balance diagnostics)."""
    return [int(np.sum(income <= t)) for t in thresholds]


def compute_bifiltration(
    points: NDArray[np.float64],
    income: NDArray[np.float64],
    threshold_radius: float,
):
    """Construct Rips × income lower-star bifiltration.

    Returns:
        SimplexTreeMulti with 2 filtration parameters.
    """
    from multipers.filtrations import RipsLowerstar

    return RipsLowerstar(
        points=points,
        function=income.reshape(-1, 1),
        threshold_radius=threshold_radius,
    )


def compute_signed_measure(
    st,
    degree: int,
    resolution: int = 20,
    custom_grid: list[NDArray[np.float64]] | None = None,
):
    """Compute signed measure for a given homology degree.

    Args:
        st: SimplexTreeMulti.
        degree: Homology degree (0, 1, ...).
        resolution: Grid resolution (used if custom_grid is None).
        custom_grid: Optional list of 1D arrays [rips_values, income_values].

    Returns:
        (points, weights) — grid coordinates and signed integer weights.
    """
    import multipers as mp

    kwargs: dict = {"degree": degree}
    if custom_grid is not None:
        kwargs["grid"] = custom_grid
    else:
        kwargs["grid_strategy"] = "regular"
        kwargs["resolution"] = resolution

    sm = mp.signed_measure(st, **kwargs)
    return sm[0]  # (points_array, weights_array)


# ──────────────────────────────────────────────────────────────────────
# Analysis: income-stratified mass
# ──────────────────────────────────────────────────────────────────────


def analyse_income_stratification(
    pts: NDArray[np.float64],
    weights: NDArray[np.float64],
    income_median: float,
) -> dict:
    """Analyse how signed measure mass distributes across income levels.

    Splits at income_median (the second filtration parameter axis).

    Returns:
        Dict with low/high income mass, ratio, and concentration metrics.
    """
    if len(pts) == 0:
        return {
            "low_income_mass": 0.0,
            "high_income_mass": 0.0,
            "ratio": 0.0,
            "n_points": 0,
        }

    # Second column of pts is the income filtration parameter
    income_vals = pts[:, 1]
    low_mask = income_vals <= income_median
    high_mask = ~low_mask

    abs_weights = np.abs(weights)
    low_mass = float(np.sum(abs_weights[low_mask]))
    high_mass = float(np.sum(abs_weights[high_mask]))
    total = low_mass + high_mass

    return {
        "low_income_mass": low_mass,
        "high_income_mass": high_mass,
        "total_mass": total,
        "low_income_fraction": low_mass / total if total > 0 else 0.0,
        "n_points": len(pts),
        "n_low": int(np.sum(low_mask)),
        "n_high": int(np.sum(high_mask)),
    }


# ──────────────────────────────────────────────────────────────────────
# Visualisation
# ──────────────────────────────────────────────────────────────────────


def plot_discretisation_comparison(results: dict, output_path: Path) -> None:
    """Plot side-by-side comparison of discretisation strategies."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("P04 Discretisation Strategy Comparison (Custom Grids)", fontsize=14)

    for row, strategy in enumerate(["quantile", "fixed"]):
        data = results[strategy]

        # 1) Points per threshold (balance diagnostic)
        ax = axes[row, 0]
        pts_per = data["points_per_threshold"]
        ax.bar(
            range(len(pts_per)),
            pts_per,
            color="steelblue" if strategy == "quantile" else "coral",
        )
        ax.set_title(f"{strategy.title()}: Cumulative pts per τ")
        ax.set_xlabel("Threshold index")
        ax.set_ylabel("Cumulative count")

        # 2) H0 income stratification
        ax = axes[row, 1]
        h0 = data["h0_stratification"]
        ax.bar(
            ["Low income", "High income"],
            [h0["low_income_mass"], h0["high_income_mass"]],
            color=["#d62728", "#2ca02c"],
        )
        ax.set_title(f"{strategy.title()}: H0 signed measure mass")
        ax.set_ylabel("|weight| sum")

        # 3) H1 income stratification
        ax = axes[row, 2]
        h1 = data["h1_stratification"]
        ax.bar(
            ["Low income", "High income"],
            [h1["low_income_mass"], h1["high_income_mass"]],
            color=["#d62728", "#2ca02c"],
        )
        ax.set_title(f"{strategy.title()}: H1 signed measure mass")
        ax.set_ylabel("|weight| sum")

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved discretisation comparison figure: %s", output_path)


def plot_signed_measure_heatmaps(results: dict, output_path: Path) -> None:
    """Plot H1 signed measure as heatmaps for both grid strategies."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("H1 Signed Measure Heatmap: Quantile vs Fixed Grid", fontsize=14)

    for ax, strategy in zip(axes, ["quantile", "fixed"]):
        data = results[strategy]
        pts = np.array(data["h1_sm_points"])
        weights = np.array(data["h1_sm_weights"])

        if len(pts) == 0:
            ax.set_title(f"{strategy.title()}: No H1 features")
            continue

        # Bin into heatmap
        eps_vals = np.unique(pts[:, 0])
        tau_vals = np.unique(pts[:, 1])

        heatmap = np.zeros((len(tau_vals), len(eps_vals)))
        eps_idx = {v: i for i, v in enumerate(eps_vals)}
        tau_idx = {v: i for i, v in enumerate(tau_vals)}

        for (e, t), w in zip(pts, weights):
            heatmap[tau_idx[t], eps_idx[e]] = w

        # Two-slope colormap: negative=blue, zero=white, positive=red
        vmax = max(abs(heatmap.max()), abs(heatmap.min()), 1)
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

        im = ax.imshow(
            heatmap,
            aspect="auto",
            origin="lower",
            norm=norm,
            cmap="RdBu_r",
            extent=[eps_vals[0], eps_vals[-1], tau_vals[0], tau_vals[-1]],
        )
        ax.set_xlabel("Rips radius ε")
        ax.set_ylabel("Income threshold τ")
        ax.set_title(f"{strategy.title()} grid")
        fig.colorbar(im, ax=ax, label="Signed weight", shrink=0.8)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved H1 heatmap figure: %s", output_path)


def plot_resolution_sensitivity(results: dict, output_path: Path) -> None:
    """Plot how invariants change across discretisation resolutions."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Resolution Sensitivity: H1 Low-Income Fraction", fontsize=14)

    for ax, strategy in zip(axes, ["quantile", "fixed"]):
        data = results[strategy]["resolution_sweep"]
        resolutions = sorted(data.keys(), key=int)
        fracs = [data[r]["h1_low_fraction"] for r in resolutions]
        ax.plot([int(r) for r in resolutions], fracs, "o-", linewidth=2)
        ax.set_xlabel("Grid resolution (income axis)")
        ax.set_ylabel("H1 low-income fraction")
        ax.set_title(f"{strategy.title()} grid")
        ax.set_ylim(0, 1)
        ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved resolution sensitivity figure: %s", output_path)


def plot_invariant_comparison(results: dict, output_path: Path) -> None:
    """Compare signed measure vs Euler surface for interpretability."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Invariant Comparison: Signed Measure vs Euler Surface", fontsize=14)

    for col, strategy in enumerate(["quantile", "fixed"]):
        data = results[strategy]

        # Row 0: H1 signed measure mass by income quartile
        ax = axes[0, col]
        quartile_mass = data.get("h1_quartile_mass", [])
        if quartile_mass:
            labels = [f"Q{i + 1}" for i in range(len(quartile_mass))]
            colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(quartile_mass)))
            ax.bar(labels, quartile_mass, color=colors)
            ax.set_ylabel("|weight| sum")
        ax.set_title(f"{strategy.title()}: H1 mass by income quartile")

        # Row 1: Euler surface (H0 - H1 mass) by income quartile
        ax = axes[1, col]
        h0_qm = data.get("h0_quartile_mass", [])
        h1_qm = data.get("h1_quartile_mass", [])
        if h0_qm and h1_qm:
            euler_qm = [h0 - h1 for h0, h1 in zip(h0_qm, h1_qm)]
            labels = [f"Q{i + 1}" for i in range(len(euler_qm))]
            colors_eu = ["#d62728" if v < 0 else "#2ca02c" for v in euler_qm]
            ax.bar(labels, euler_qm, color=colors_eu)
            ax.axhline(0, color="black", linewidth=0.5)
            ax.set_ylabel("Euler mass (H0 − H1)")
        ax.set_title(f"{strategy.title()}: Euler surface by income quartile")

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved invariant comparison figure: %s", output_path)


# ──────────────────────────────────────────────────────────────────────
# Grid construction
# ──────────────────────────────────────────────────────────────────────


def _build_custom_grid(
    rips_radius: float,
    income: NDArray[np.float64],
    strategy: str,
    n_income_steps: int,
    n_rips_steps: int = 20,
) -> list[NDArray[np.float64]]:
    """Build a 2-parameter custom grid for signed measure evaluation.

    Args:
        rips_radius: Maximum Rips distance (first parameter range).
        income: Per-vertex income scores (to compute quantile grid).
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


def _quartile_mass(
    pts: NDArray[np.float64],
    weights: NDArray[np.float64],
    income: NDArray[np.float64],
    n_quartiles: int = 4,
) -> list[float]:
    """Compute absolute signed measure mass in each income quartile."""
    if len(pts) == 0:
        return [0.0] * n_quartiles

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

    return masses


# ──────────────────────────────────────────────────────────────────────
# Main exploration
# ──────────────────────────────────────────────────────────────────────


def run_exploration(
    n_landmarks: int = 2000,
    threshold_radius: float | None = None,
    n_income_steps: int = 20,
    n_rips_steps: int = 20,
    resolution_sweep: list[int] | None = None,
) -> dict:
    """Run full exploratory computation with custom grids.

    Builds the bifiltration once, then evaluates the signed measure on
    two different grids (quantile vs fixed income spacing) to properly
    compare discretisation strategies.
    """
    if resolution_sweep is None:
        resolution_sweep = [5, 10, 15, 20, 30]

    embeddings, income_scores = load_embeddings_and_income()

    logger.info("Selecting %d maxmin landmarks...", n_landmarks)
    t0 = time.time()
    lm_idx = maxmin_landmarks(embeddings, n_landmarks)
    logger.info("  Landmarking took %.1fs", time.time() - t0)

    pts = embeddings[lm_idx]
    income = income_scores[lm_idx]
    income_median = float(np.median(income))

    logger.info(
        "Landmark income: mean=%.3f, median=%.3f, std=%.3f, min=%.3f, max=%.3f",
        income.mean(),
        income_median,
        income.std(),
        income.min(),
        income.max(),
    )

    if threshold_radius is None:
        sample_idx = np.random.RandomState(42).choice(
            len(pts),
            size=min(500, len(pts)),
            replace=False,
        )
        sample_dists = pdist(pts[sample_idx])
        threshold_radius = float(np.percentile(sample_dists, 10))
        logger.info("Auto Rips radius (10th pctl): %.3f", threshold_radius)

    # Build bifiltration ONCE
    logger.info("Building bifiltration...")
    t0 = time.time()
    st = compute_bifiltration(pts, income, threshold_radius)
    t_bif = time.time() - t0
    logger.info("  Bifiltration: %d simplices, %.1fs", st.num_simplices, t_bif)

    results = {
        "n_landmarks": n_landmarks,
        "threshold_radius": threshold_radius,
        "income_median": income_median,
        "income_mean": float(income.mean()),
        "income_std": float(income.std()),
        "n_income_steps": n_income_steps,
        "n_rips_steps": n_rips_steps,
        "n_simplices": st.num_simplices,
        "bifiltration_time_s": t_bif,
    }

    # Evaluate on quantile and fixed grids
    for strategy in ["quantile", "fixed"]:
        logger.info("=" * 60)
        logger.info(
            "Evaluating on %s grid (income=%d, rips=%d)",
            strategy,
            n_income_steps,
            n_rips_steps,
        )
        logger.info("=" * 60)

        grid = _build_custom_grid(
            threshold_radius,
            income,
            strategy,
            n_income_steps,
            n_rips_steps,
        )
        income_grid = grid[1]

        pts_per = compute_points_per_threshold(income, income_grid)
        logger.info("  Income grid (first 5): %s", income_grid[:5].tolist())
        logger.info("  Pts per τ (first 5): %s", pts_per[:5])
        logger.info("  Balance: min=%d, max=%d", min(pts_per), max(pts_per))

        # H0 signed measure on custom grid
        t0 = time.time()
        pts_h0, w_h0 = compute_signed_measure(st, degree=0, custom_grid=grid)
        t_h0 = time.time() - t0
        logger.info("  H0 SM: %d points, %.1fs", len(pts_h0), t_h0)

        # H1 signed measure on custom grid
        t0 = time.time()
        pts_h1, w_h1 = compute_signed_measure(st, degree=1, custom_grid=grid)
        t_h1 = time.time() - t0
        logger.info("  H1 SM: %d points, %.1fs", len(pts_h1), t_h1)

        # Binary stratification
        h0_strat = analyse_income_stratification(pts_h0, w_h0, income_median)
        h1_strat = analyse_income_stratification(pts_h1, w_h1, income_median)

        logger.info(
            "  H0: low=%.0f, high=%.0f, low_frac=%.3f",
            h0_strat["low_income_mass"],
            h0_strat["high_income_mass"],
            h0_strat["low_income_fraction"],
        )
        logger.info(
            "  H1: low=%.0f, high=%.0f, low_frac=%.3f",
            h1_strat["low_income_mass"],
            h1_strat["high_income_mass"],
            h1_strat["low_income_fraction"],
        )

        # Quartile decomposition
        h0_qm = _quartile_mass(pts_h0, w_h0, income)
        h1_qm = _quartile_mass(pts_h1, w_h1, income)
        logger.info("  H0 quartile mass: %s", [f"{m:.0f}" for m in h0_qm])
        logger.info("  H1 quartile mass: %s", [f"{m:.0f}" for m in h1_qm])

        # Resolution sweep
        sweep_results = {}
        for n_inc in resolution_sweep:
            logger.info("  Resolution sweep: n_income=%d", n_inc)
            g = _build_custom_grid(
                threshold_radius,
                income,
                strategy,
                n_inc,
                n_rips_steps,
            )
            pts_r, w_r = compute_signed_measure(st, degree=1, custom_grid=g)
            h1_r = analyse_income_stratification(pts_r, w_r, income_median)
            sweep_results[str(n_inc)] = {
                "h1_low_fraction": h1_r["low_income_fraction"],
                "h1_total_mass": h1_r["total_mass"],
                "income_grid_size": len(g[1]),
            }

        results[strategy] = {
            "income_grid": income_grid.tolist(),
            "thresholds": income_grid.tolist(),
            "points_per_threshold": pts_per,
            "h0_stratification": h0_strat,
            "h1_stratification": h1_strat,
            "h0_quartile_mass": h0_qm,
            "h1_quartile_mass": h1_qm,
            "h0_sm_time_s": t_h0,
            "h1_sm_time_s": t_h1,
            "h1_sm_points": pts_h1.tolist() if len(pts_h1) > 0 else [],
            "h1_sm_weights": w_h1.tolist() if len(w_h1) > 0 else [],
            "resolution_sweep": sweep_results,
        }

    return results


def main() -> None:
    """Entry point for P04 exploratory computation."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    results = run_exploration(n_landmarks=2000)

    # Save results
    results_path = OUTPUT_DIR / "discretisation_exploration.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results saved to %s", results_path)

    # Generate all figures
    plot_discretisation_comparison(
        results,
        FIGURE_DIR / "discretisation_comparison.png",
    )
    plot_signed_measure_heatmaps(
        results,
        FIGURE_DIR / "h1_signed_measure_heatmap.png",
    )
    plot_resolution_sensitivity(
        results,
        FIGURE_DIR / "resolution_sensitivity.png",
    )
    plot_invariant_comparison(
        results,
        FIGURE_DIR / "invariant_comparison.png",
    )

    # Print summary
    print("\n" + "=" * 70)
    print("P04 DISCRETISATION & INVARIANT EXPLORATION")
    print("=" * 70)
    print(f"Landmarks: {results['n_landmarks']}")
    print(f"Rips radius: {results['threshold_radius']:.3f}")
    print(f"Simplices: {results['n_simplices']}")
    print(
        f"Income: mean={results['income_mean']:.3f}, "
        f"median={results['income_median']:.3f}"
    )
    print()

    for strategy in ["quantile", "fixed"]:
        d = results[strategy]
        print(f"--- {strategy.upper()} GRID ---")
        print(f"  Income grid: {len(d['income_grid'])} steps")
        print(
            f"  Balance (pts/τ): min={min(d['points_per_threshold'])}, "
            f"max={max(d['points_per_threshold'])}"
        )
        print(
            f"  H0: low_frac={d['h0_stratification']['low_income_fraction']:.3f}, "
            f"total_mass={d['h0_stratification']['total_mass']:.0f}"
        )
        print(
            f"  H1: low_frac={d['h1_stratification']['low_income_fraction']:.3f}, "
            f"total_mass={d['h1_stratification']['total_mass']:.0f}"
        )
        print(f"  H0 quartile mass: {[f'{m:.0f}' for m in d['h0_quartile_mass']]}")
        print(f"  H1 quartile mass: {[f'{m:.0f}' for m in d['h1_quartile_mass']]}")
        print(f"  Time: H0_SM={d['h0_sm_time_s']:.1f}s, H1_SM={d['h1_sm_time_s']:.1f}s")

        sweep = d["resolution_sweep"]
        fracs = [sweep[r]["h1_low_fraction"] for r in sorted(sweep, key=int)]
        print(f"  H1 low-frac stability: {[f'{f:.3f}' for f in fracs]}")
        print()


if __name__ == "__main__":
    main()
