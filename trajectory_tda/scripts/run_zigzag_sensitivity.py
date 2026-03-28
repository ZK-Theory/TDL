"""Zigzag ε × landmark 2D sensitivity analysis.

Paper 3 robustness: Runs zigzag persistence across a grid of filtration
thresholds (ε) and landmark counts (L) to characterise which topological
features are stable across parameter choices.

**Methodological rationale:**  Fixed-threshold zigzag persistence requires
choosing ε *a priori*.  We derive a data-driven ε from the per-year
independent VR persistence diagrams: for each year's H₀ diagram, we
compute β₀(ε) and locate the *knee* (point of maximum curvature in the
descent from many components to few).  The median knee across 32 years
gives our recommended ε; the grid sweeps a range from well below to well
above the knee to demonstrate feature stability.

Run::

    python -m trajectory_tda.scripts.run_zigzag_sensitivity \\
        --checkpoint-dir results/trajectory_tda_full \\
        --output-dir results/trajectory_tda_zigzag/sensitivity_2d \\
        --per-year-diagrams results/trajectory_tda_zigzag/02_annual_diagrams.json
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _convert(obj: object) -> object:
    """Recursively convert numpy types to JSON-serialisable equivalents."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Knee detection from per-year VR diagrams
# ---------------------------------------------------------------------------


def compute_per_year_knee(
    per_year_diagrams_path: Path,
    eps_grid: NDArray[np.float64] | None = None,
) -> dict:
    """Derive data-driven ε from per-year H₀ persistence diagrams.

    For each year, computes β₀(ε) and locates the knee via maximum
    curvature in the descent region (β₀ > 5).  Returns summary
    statistics across all years plus per-year detail.

    Args:
        per_year_diagrams_path: Path to ``02_annual_diagrams.json``.
        eps_grid: Optional fine-grained ε grid.  Defaults to
            ``np.arange(0.05, 2.01, 0.01)``.

    Returns:
        Dict with ``median_knee_eps``, ``per_year_knees``,
        ``beta0_summary``, and ``knee_diagnostics``.
    """
    with open(per_year_diagrams_path) as f:
        data = json.load(f)

    if eps_grid is None:
        eps_grid = np.arange(0.05, 2.01, 0.01)

    years = sorted(data["diagrams"].keys(), key=int)

    # β₀(ε) per year
    beta0_matrix = np.zeros((len(years), len(eps_grid)))
    year_knees: dict[str, float] = {}
    max_h0_deaths: dict[str, float] = {}

    x_norm = (eps_grid - eps_grid.min()) / (eps_grid.max() - eps_grid.min())

    for i, yr in enumerate(years):
        h0 = np.array(data["diagrams"][yr]["diagram_h0"])
        births = h0[:, 0]
        deaths = h0[:, 1]
        finite_deaths = deaths[np.isfinite(deaths)]

        max_h0_deaths[yr] = float(finite_deaths.max()) if len(finite_deaths) > 0 else 0.0

        for j, eps in enumerate(eps_grid):
            alive = np.sum((births <= eps) & ((deaths > eps) | np.isinf(deaths)))
            beta0_matrix[i, j] = alive

        # Knee via maximum curvature in descent region
        curve = beta0_matrix[i].astype(np.float64)
        y_range = curve.max() - curve.min()
        if y_range < 1e-12:
            year_knees[yr] = float(eps_grid[0])
            continue

        y_n = (curve - curve.min()) / y_range
        dy = np.gradient(y_n, x_norm)
        d2y = np.gradient(dy, x_norm)
        curvature = np.abs(d2y) / (1 + dy**2) ** 1.5

        descent_mask = curve > 5
        if descent_mask.any():
            valid_idx = np.where(descent_mask)[0]
            knee_idx = valid_idx[np.argmax(curvature[valid_idx])]
        else:
            knee_idx = int(np.argmax(curvature))

        year_knees[yr] = float(eps_grid[knee_idx])

    # Aggregate
    knee_values = np.array(list(year_knees.values()))
    median_beta0 = np.median(beta0_matrix, axis=0)

    # β₀ at key ε thresholds
    beta0_at_eps = {}
    for eps_val in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        idx = np.argmin(np.abs(eps_grid - eps_val))
        beta0_at_eps[f"{eps_val:.1f}"] = {
            "median": float(median_beta0[idx]),
            "q25": float(np.percentile(beta0_matrix[:, idx], 25)),
            "q75": float(np.percentile(beta0_matrix[:, idx], 75)),
        }

    return {
        "median_knee_eps": float(np.median(knee_values)),
        "mean_knee_eps": float(np.mean(knee_values)),
        "std_knee_eps": float(np.std(knee_values)),
        "q25_knee_eps": float(np.percentile(knee_values, 25)),
        "q75_knee_eps": float(np.percentile(knee_values, 75)),
        "min_knee_eps": float(knee_values.min()),
        "max_knee_eps": float(knee_values.max()),
        "per_year_knees": year_knees,
        "max_h0_deaths": max_h0_deaths,
        "beta0_at_eps": beta0_at_eps,
        "n_landmarks_per_year": data.get("n_landmarks", "unknown"),
    }


# ---------------------------------------------------------------------------
# 2D grid sweep
# ---------------------------------------------------------------------------


def run_sensitivity_2d(
    checkpoint_dir: Path,
    output_dir: Path,
    eps_values: list[float],
    landmark_counts: list[int],
    year_start: int,
    year_end: int,
    max_dim: int,
    wsl_python: str,
) -> dict:
    """Run zigzag across a 2D grid of (ε, L) and collect results.

    Args:
        checkpoint_dir: Directory with ``01_trajectories.json`` and
            ``embeddings.npy``.
        output_dir: Directory for sensitivity outputs.
        eps_values: Filtration thresholds to sweep.
        landmark_counts: Landmark counts to sweep.
        year_start: First calendar year.
        year_end: Last calendar year.
        max_dim: Maximum homology dimension.
        wsl_python: WSL Python path for dionysus bridge.

    Returns:
        Summary dict with the full grid of results.
    """
    import pandas as pd

    from trajectory_tda.data.annual_partition import build_embeddings_by_year
    from trajectory_tda.topology.zigzag import level_to_year, run_gudhi_zigzag

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data once
    logger.info("Loading embeddings and metadata...")
    embeddings_by_year = build_embeddings_by_year(
        trajectories_json_path=checkpoint_dir / "01_trajectories.json",
        embeddings_npy_path=checkpoint_dir / "embeddings.npy",
        year_start=year_start,
        year_end=year_end,
        min_individuals=50,
    )
    with open(checkpoint_dir / "01_trajectories.json") as f:
        cp = json.load(f)
    metadata = pd.DataFrame(cp["metadata"])

    years = sorted(embeddings_by_year.keys())
    y0 = years[0]

    grid_results: dict = {
        "eps_values": eps_values,
        "landmark_counts": landmark_counts,
        "max_dim": max_dim,
        "year_range": [year_start, year_end],
        "cells": {},
    }

    total_cells = len(eps_values) * len(landmark_counts)
    cell_num = 0

    for eps in eps_values:
        for n_land in landmark_counts:
            cell_num += 1
            cell_key = f"eps{eps:.2f}_L{n_land}"
            logger.info(
                "=" * 60 + "\n[%d/%d] ε=%.2f, L=%d\n" + "=" * 60,
                cell_num,
                total_cells,
                eps,
                n_land,
            )

            t0 = time.time()
            try:
                h0, h1 = run_gudhi_zigzag(
                    embeddings_by_year=embeddings_by_year,
                    max_filtration=eps,
                    n_landmarks=n_land,
                    sparse=0.5,
                    metadata=metadata,
                    max_dim=max_dim,
                    wsl_python=wsl_python,
                )
            except Exception as exc:
                logger.error("Zigzag failed at ε=%.2f, L=%d: %s", eps, n_land, exc)
                grid_results["cells"][cell_key] = {
                    "eps": eps,
                    "n_landmarks": n_land,
                    "error": str(exc),
                }
                continue

            elapsed = time.time() - t0

            # H₀ bar details (birth/death in calendar years)
            h0_bars = []
            for birth, death in h0:
                lt = float((death - birth) / 2.0) if np.isfinite(death) else None
                h0_bars.append(
                    {
                        "birth_level": float(birth),
                        "death_level": float(death) if np.isfinite(death) else None,
                        "birth_year": float(level_to_year(birth, y0)),
                        "death_year": (float(level_to_year(death, y0)) if np.isfinite(death) else None),
                        "lifetime_years": lt,
                    }
                )

            # H₁ summary
            h1_finite = h1[np.isfinite(h1[:, 1])] if len(h1) > 0 else np.zeros((0, 2))
            h1_lifetimes = (h1_finite[:, 1] - h1_finite[:, 0]) / 2.0 if len(h1_finite) > 0 else np.array([])

            cell_result = {
                "eps": eps,
                "n_landmarks": n_land,
                "n_h0_bars": len(h0),
                "n_h1_bars": len(h1),
                "elapsed_seconds": round(elapsed, 1),
                "h0_bars": h0_bars,
                "h1_summary": {
                    "n_finite": len(h1_lifetimes),
                    "mean_lifetime_years": (round(float(h1_lifetimes.mean()), 3) if len(h1_lifetimes) > 0 else 0.0),
                    "median_lifetime_years": (
                        round(float(np.median(h1_lifetimes)), 3) if len(h1_lifetimes) > 0 else 0.0
                    ),
                    "max_lifetime_years": (round(float(h1_lifetimes.max()), 3) if len(h1_lifetimes) > 0 else 0.0),
                    "n_above_1yr": (int((h1_lifetimes > 1).sum()) if len(h1_lifetimes) > 0 else 0),
                    "n_above_5yr": (int((h1_lifetimes > 5).sum()) if len(h1_lifetimes) > 0 else 0),
                    "n_above_10yr": (int((h1_lifetimes > 10).sum()) if len(h1_lifetimes) > 0 else 0),
                },
            }

            grid_results["cells"][cell_key] = cell_result
            logger.info(
                "ε=%.2f, L=%d: %d H₀ bars, %d H₁ bars (%.1f s)",
                eps,
                n_land,
                len(h0),
                len(h1),
                elapsed,
            )

            # Save individual cell
            cell_path = output_dir / f"{cell_key}.json"
            with open(cell_path, "w") as f:
                json.dump(_convert(cell_result), f, indent=2)

            # Flush grid after each cell (long-running)
            with open(output_dir / "grid_results.json", "w") as f:
                json.dump(_convert(grid_results), f, indent=2)

    # Print summary table
    _print_grid_summary(grid_results)

    return grid_results


def _print_grid_summary(grid_results: dict) -> None:
    """Print a formatted summary table of the 2D grid."""
    eps_values = grid_results["eps_values"]
    landmark_counts = grid_results["landmark_counts"]

    logger.info("\n" + "=" * 80)
    logger.info("2D SENSITIVITY GRID SUMMARY")
    logger.info("=" * 80)

    # H₀ bar count table
    col_label = "ε \\ L"
    header = f"{col_label:>8s}" + "".join(f"{L:>8d}" for L in landmark_counts)
    logger.info("\nH₀ bar counts:")
    logger.info(header)
    logger.info("-" * len(header))
    for eps in eps_values:
        row = f"{eps:8.2f}"
        for L in landmark_counts:
            key = f"eps{eps:.2f}_L{L}"
            cell = grid_results["cells"].get(key, {})
            if "error" in cell:
                row += f"{'ERR':>8s}"
            else:
                row += f"{cell.get('n_h0_bars', '?'):>8}"
        logger.info(row)

    # H₁ bar count table
    logger.info("\nH₁ bar counts:")
    logger.info(header)
    logger.info("-" * len(header))
    for eps in eps_values:
        row = f"{eps:8.2f}"
        for L in landmark_counts:
            key = f"eps{eps:.2f}_L{L}"
            cell = grid_results["cells"].get(key, {})
            if "error" in cell:
                row += f"{'ERR':>8s}"
            else:
                row += f"{cell.get('n_h1_bars', '?'):>8}"
        logger.info(row)

    # Runtime table
    logger.info("\nRuntime (seconds):")
    logger.info(header)
    logger.info("-" * len(header))
    for eps in eps_values:
        row = f"{eps:8.2f}"
        for L in landmark_counts:
            key = f"eps{eps:.2f}_L{L}"
            cell = grid_results["cells"].get(key, {})
            if "error" in cell:
                row += f"{'ERR':>8s}"
            else:
                row += f"{cell.get('elapsed_seconds', '?'):>8}"
        logger.info(row)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Zigzag ε × landmark 2D sensitivity analysis.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="results/trajectory_tda_full",
    )
    parser.add_argument(
        "--output-dir",
        default="results/trajectory_tda_zigzag/sensitivity_2d",
    )
    parser.add_argument(
        "--per-year-diagrams",
        default="results/trajectory_tda_zigzag/02_annual_diagrams.json",
        help="Path to per-year VR diagrams for knee detection.",
    )
    parser.add_argument(
        "--eps-values",
        type=float,
        nargs="+",
        default=None,
        help="Filtration thresholds.  If omitted, derived from per-year knee.",
    )
    parser.add_argument(
        "--landmark-counts",
        type=int,
        nargs="+",
        default=[75, 100, 150, 200],
    )
    parser.add_argument("--year-start", type=int, default=1991)
    parser.add_argument("--year-end", type=int, default=2022)
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument(
        "--wsl-python",
        default="/tmp/dionysus_env/bin/python",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    # Step 1: Knee analysis from per-year VR diagrams
    per_year_path = Path(args.per_year_diagrams)
    if per_year_path.exists():
        logger.info("Computing per-year β₀ knee from %s", per_year_path)
        knee_info = compute_per_year_knee(per_year_path)

        knee_eps = knee_info["median_knee_eps"]
        logger.info(
            "Per-year knee: median=%.3f, Q25=%.3f, Q75=%.3f, range=[%.3f, %.3f]",
            knee_eps,
            knee_info["q25_knee_eps"],
            knee_info["q75_knee_eps"],
            knee_info["min_knee_eps"],
            knee_info["max_knee_eps"],
        )

        # Save knee analysis
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "knee_analysis.json", "w") as f:
            json.dump(_convert(knee_info), f, indent=2)
        logger.info("Saved knee analysis: %s", output_dir / "knee_analysis.json")
    else:
        logger.warning("Per-year diagrams not found at %s; using default ε grid", per_year_path)
        knee_eps = 0.6

    # Step 2: Build ε grid centred on knee
    if args.eps_values is not None:
        eps_values = sorted(args.eps_values)
    else:
        # Grid: from well below knee to well above, denser near knee
        eps_values = sorted(
            {
                round(knee_eps - 0.20, 2),
                round(knee_eps - 0.10, 2),
                round(knee_eps - 0.05, 2),
                round(knee_eps, 2),
                round(knee_eps + 0.05, 2),
                round(knee_eps + 0.10, 2),
                round(knee_eps + 0.20, 2),
                0.70,  # original H1 run
                0.80,
                0.90,
                1.00,  # original main run
            }
        )
        # Remove any ε ≤ 0
        eps_values = [e for e in eps_values if e > 0]

    logger.info("ε grid: %s", eps_values)
    logger.info("Landmark grid: %s", args.landmark_counts)
    logger.info("Total cells: %d", len(eps_values) * len(args.landmark_counts))

    # Step 3: Run 2D grid
    grid_results = run_sensitivity_2d(
        checkpoint_dir=Path(args.checkpoint_dir),
        output_dir=Path(args.output_dir),
        eps_values=eps_values,
        landmark_counts=args.landmark_counts,
        year_start=args.year_start,
        year_end=args.year_end,
        max_dim=args.max_dim,
        wsl_python=args.wsl_python,
    )

    # Step 4: Save combined output (knee + grid)
    output_dir = Path(args.output_dir)
    combined = {
        "knee_analysis": knee_info if per_year_path.exists() else None,
        "grid": grid_results,
    }
    with open(output_dir / "full_sensitivity_report.json", "w") as f:
        json.dump(_convert(combined), f, indent=2)
    logger.info("Saved full report: %s", output_dir / "full_sensitivity_report.json")


if __name__ == "__main__":
    main()
