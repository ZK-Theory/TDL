"""Era-specific zigzag robustness grid.

Paper 3 robustness: runs zigzag separately on BHPS-only (1991–2008)
and USoc-only (2009–2022) at multiple ε values from the data-driven
knee analysis (sensitivity_2d/knee_analysis.json), testing whether
the full-panel's topological features survive *within* each survey era.

This adjudicates between two competing explanations for the dominant
2008.5 feature:
  (a) Genuine GFC structural break in the trajectory manifold.
  (b) Artefact from the BHPS → USoc survey instrument transition.

If feature (a), the BHPS era should show internal sub-structure
(ERM fragment 1991–1996.5, early-BHPS cluster 1991–2003) at moderate ε,
and the USoc era may show its own sub-structure (austerity, COVID).
If feature (b), era-specific runs should each collapse to a single
connected component at ε ≥ 0.7.

Run::

    python -m trajectory_tda.scripts.run_zigzag_era_robustness \\
        --checkpoint-dir results/trajectory_tda_full \\
        --output-dir results/trajectory_tda_zigzag/era_robustness \\
        --knee-json results/trajectory_tda_zigzag/sensitivity_2d/knee_analysis.json \\
        --landmark-counts 100 150 \\
        --max-dim 1 \\
        --wsl-python /tmp/dionysus_env/bin/python
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


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


def _era_knee(
    per_year_knees: dict[str, float],
    year_start: int,
    year_end: int,
) -> float:
    """Compute the median knee ε for a sub-range of years.

    Args:
        per_year_knees: Year (str) → knee ε from knee_analysis.json.
        year_start: First year (inclusive).
        year_end: Last year (inclusive).

    Returns:
        Median knee ε over the specified years.
    """
    knees = [
        v
        for k, v in per_year_knees.items()
        if year_start <= int(k) <= year_end and v > 0.1  # exclude degenerate knees
    ]
    if not knees:
        return 0.54  # fallback to global median
    return float(np.median(knees))


def _build_eps_grid(
    era_knee: float,
    global_knee: float,
) -> list[float]:
    """Build ε grid centred on era-specific and global knees.

    Includes: era knee, global knee, 0.70, 1.00 (plus the midpoint
    between era knee and 0.70 if there's a big gap).

    Args:
        era_knee: Median knee for this era.
        global_knee: Median knee across all years.

    Returns:
        Sorted, deduplicated ε values.
    """
    eps_set = {
        round(era_knee, 2),
        round(global_knee, 2),
        0.70,
        1.00,
    }
    # Add midpoint between era knee and 0.70 if gap > 0.15
    mid = round((era_knee + 0.70) / 2, 2)
    if abs(mid - era_knee) > 0.07 and abs(mid - 0.70) > 0.07:
        eps_set.add(mid)

    return sorted(eps_set)


def run_era_robustness(
    checkpoint_dir: Path,
    output_dir: Path,
    knee_json: Path,
    landmark_counts: list[int],
    max_dim: int,
    wsl_python: str,
) -> dict:
    """Run era-specific zigzag grid and compare against full-panel features.

    Args:
        checkpoint_dir: Path with ``01_trajectories.json``, ``embeddings.npy``.
        output_dir: Output directory for results.
        knee_json: Path to knee_analysis.json from the sensitivity grid.
        landmark_counts: List of landmark counts to test.
        max_dim: Max homology dimension for zigzag.
        wsl_python: WSL Python path for dionysus bridge.

    Returns:
        Dict with per-era, per-cell results and cross-era comparison.
    """
    from trajectory_tda.data.annual_partition import build_embeddings_by_year
    from trajectory_tda.topology.zigzag import level_to_year, run_gudhi_zigzag

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load knee analysis
    with open(knee_json) as f:
        knee_data = json.load(f)
    per_year_knees = knee_data["per_year_knees"]
    global_knee = knee_data["median_knee_eps"]

    # Load full-panel reference features from sensitivity grid
    # (ε=1.0, L=150 is the canonical reference)
    ref_path = output_dir.parent / "sensitivity_2d" / "eps1.00_L150.json"
    ref_features = None
    if ref_path.exists():
        with open(ref_path) as f:
            ref_features = json.load(f)
        logger.info(
            "Loaded full-panel reference: %d H₀ bars at ε=1.0, L=150",
            ref_features["n_h0_bars"],
        )

    eras = {
        "bhps": (1991, 2008),
        "usoc": (2009, 2022),
    }

    all_results: dict = {"eras": {}, "reference": None}

    if ref_features:
        all_results["reference"] = {
            "eps": 1.0,
            "landmarks": 150,
            "n_h0_bars": ref_features["n_h0_bars"],
            "h0_bars": ref_features["h0_bars"],
        }

    for era_name, (y_start, y_end) in eras.items():
        era_knee = _era_knee(per_year_knees, y_start, y_end)
        eps_grid = _build_eps_grid(era_knee, global_knee)

        logger.info("=" * 70)
        logger.info(
            "ERA: %s (%d–%d), knee ε = %.2f",
            era_name.upper(),
            y_start,
            y_end,
            era_knee,
        )
        logger.info("ε grid: %s", eps_grid)
        logger.info("L grid: %s", landmark_counts)
        n_cells = len(eps_grid) * len(landmark_counts)
        logger.info("Total cells: %d", n_cells)
        logger.info("=" * 70)

        # Build embeddings for this era
        embeddings_by_year = build_embeddings_by_year(
            trajectories_json_path=checkpoint_dir / "01_trajectories.json",
            embeddings_npy_path=checkpoint_dir / "embeddings.npy",
            year_start=y_start,
            year_end=y_end,
            min_individuals=50,
        )

        years_available = sorted(embeddings_by_year.keys())
        n_years = len(years_available)
        y0 = years_available[0]

        logger.info(
            "%d years available (%d–%d)",
            n_years,
            years_available[0],
            years_available[-1],
        )

        era_results: dict = {
            "era": era_name,
            "year_range": [y_start, y_end],
            "n_years": n_years,
            "era_knee_eps": era_knee,
            "eps_grid": eps_grid,
            "landmark_grid": landmark_counts,
            "cells": {},
        }

        cell_idx = 0
        for eps in eps_grid:
            for n_lm in landmark_counts:
                cell_idx += 1
                cell_key = f"eps{eps:.2f}_L{n_lm}"

                # Skip if already computed
                cell_path = output_dir / f"{era_name}_{cell_key}.json"
                if cell_path.exists():
                    with open(cell_path) as f:
                        existing = json.load(f)
                    if "error" not in existing:
                        logger.info(
                            "[%d/%d] %s: loaded from cache (%d H₀, %d H₁)",
                            cell_idx,
                            n_cells,
                            cell_key,
                            existing["n_h0_bars"],
                            existing["n_h1_bars"],
                        )
                        era_results["cells"][cell_key] = existing
                        continue

                logger.info(
                    "[%d/%d] %s ε=%.2f, L=%d",
                    cell_idx,
                    n_cells,
                    era_name.upper(),
                    eps,
                    n_lm,
                )

                t0 = time.time()
                try:
                    h0, h1 = run_gudhi_zigzag(
                        embeddings_by_year=embeddings_by_year,
                        max_filtration=eps,
                        n_landmarks=n_lm,
                        max_dim=max_dim,
                        wsl_python=wsl_python,
                    )
                except Exception as exc:
                    elapsed = time.time() - t0
                    logger.error(
                        "Zigzag failed at %s ε=%.2f, L=%d: %s",
                        era_name,
                        eps,
                        n_lm,
                        exc,
                    )
                    cell_result = {
                        "error": str(exc),
                        "eps": eps,
                        "n_landmarks": n_lm,
                        "elapsed_seconds": elapsed,
                    }
                    era_results["cells"][cell_key] = cell_result
                    with open(cell_path, "w") as f:
                        json.dump(_convert(cell_result), f, indent=2)
                    continue

                elapsed = time.time() - t0

                # Convert H₀ bars to year coordinates
                h0_bars = []
                for birth, death in h0:
                    by = float(level_to_year(birth, y0))
                    dy = float(level_to_year(death, y0)) if np.isfinite(death) else None
                    lt = float((death - birth) / 2.0) if np.isfinite(death) else None
                    h0_bars.append(
                        {
                            "birth_year": by,
                            "death_year": dy,
                            "lifetime_years": lt,
                        }
                    )

                # H₁ summary (don't store all bars — too many)
                h1_finite = h1[np.isfinite(h1[:, 1])] if len(h1) > 0 else np.zeros((0, 2))
                h1_lifetimes = (h1_finite[:, 1] - h1_finite[:, 0]) / 2.0 if len(h1_finite) > 0 else np.array([])

                # Long-lived H₀ bars (≥ 3 years)
                long_h0 = [b for b in h0_bars if b["lifetime_years"] is not None and b["lifetime_years"] >= 3.0]

                cell_result = {
                    "eps": eps,
                    "n_landmarks": n_lm,
                    "n_h0_bars": len(h0),
                    "n_h1_bars": len(h1),
                    "n_h0_long": len(long_h0),
                    "elapsed_seconds": elapsed,
                    "h0_bars": h0_bars,
                    "h0_long_bars": long_h0,
                    "h1_summary": {
                        "n_finite": len(h1_lifetimes),
                        "mean_lifetime": float(h1_lifetimes.mean()) if len(h1_lifetimes) > 0 else 0.0,
                        "median_lifetime": float(np.median(h1_lifetimes)) if len(h1_lifetimes) > 0 else 0.0,
                        "max_lifetime": float(h1_lifetimes.max()) if len(h1_lifetimes) > 0 else 0.0,
                    },
                }

                era_results["cells"][cell_key] = cell_result

                with open(cell_path, "w") as f:
                    json.dump(_convert(cell_result), f, indent=2)

                logger.info(
                    "%s ε=%.2f, L=%d: %d H₀ (%d long-lived), %d H₁ (%.1f s)",
                    era_name.upper(),
                    eps,
                    n_lm,
                    len(h0),
                    len(long_h0),
                    len(h1),
                    elapsed,
                )

                # Log long-lived bars
                for b in sorted(long_h0, key=lambda x: -(x["lifetime_years"] or 0))[:5]:
                    dy_str = f"{b['death_year']:.1f}" if b["death_year"] else "∞"
                    lt_str = f"{b['lifetime_years']:.1f}" if b["lifetime_years"] else "∞"
                    logger.info(
                        "  H₀: %s → %s (%s yr)",
                        f"{b['birth_year']:.1f}",
                        dy_str,
                        lt_str,
                    )

        # Save era results
        era_path = output_dir / f"{era_name}_grid.json"
        with open(era_path, "w") as f:
            json.dump(_convert(era_results), f, indent=2)
        logger.info("Saved era grid: %s", era_path)

        all_results["eras"][era_name] = era_results

    # ── Cross-era comparison ─────────────────────────────────────────────
    _compare_eras(all_results, output_dir)

    return all_results


def _compare_eras(results: dict, output_dir: Path) -> None:
    """Compare era-specific features against the full-panel reference.

    For each ε in common between era grids and the full-panel grid,
    checks whether full-panel features appear within their expected era.
    """
    comparison: dict = {
        "full_panel_h0_at_eps1": results.get("reference", {}),
        "bhps_features": {},
        "usoc_features": {},
        "adjudication": [],
    }

    # Extract features at ε=1.0 for each era (the harshest threshold)
    for era_name in ("bhps", "usoc"):
        era = results["eras"].get(era_name, {})
        cells = era.get("cells", {})

        # Find ε=1.0 cells
        eps1_cells = {k: v for k, v in cells.items() if v.get("eps") == 1.0 and "error" not in v}

        if not eps1_cells:
            logger.warning("No ε=1.0 cells for %s", era_name)
            continue

        # Use the higher-landmark cell
        best_key = max(eps1_cells.keys(), key=lambda k: eps1_cells[k]["n_landmarks"])
        best = eps1_cells[best_key]

        comparison[f"{era_name}_features"] = {
            "eps": 1.0,
            "landmarks": best["n_landmarks"],
            "n_h0_bars": best["n_h0_bars"],
            "h0_bars": best.get("h0_bars", []),
        }

        if best["n_h0_bars"] == 1:
            comparison["adjudication"].append(
                f"{era_name.upper()} at ε=1.0: single component (fully connected). "
                f"No internal topological sub-structure at this scale."
            )
        else:
            bars_desc = []
            for b in best.get("h0_bars", []):
                dy = f"{b['death_year']:.1f}" if b["death_year"] else "∞"
                lt = f"{b['lifetime_years']:.1f}" if b["lifetime_years"] else "∞"
                bars_desc.append(f"{b['birth_year']:.1f}→{dy} ({lt}yr)")
            comparison["adjudication"].append(
                f"{era_name.upper()} at ε=1.0: {best['n_h0_bars']} components — " + ", ".join(bars_desc) + ". "
                "Internal sub-structure present; features not artefactual."
            )

    # Check if full-panel features #3 (1991→2003) and #4 (1991→1996.5)
    # survive in BHPS-only
    ref = results.get("reference", {})
    if ref and "h0_bars" in ref:
        bhps_cells = results["eras"].get("bhps", {}).get("cells", {})

        # Find longest-lived BHPS bars at moderate ε
        for cell_key, cell in bhps_cells.items():
            if "error" in cell or cell.get("eps", 0) > 0.75:
                continue
            long = cell.get("h0_long_bars", [])
            if len(long) >= 2:
                comparison["adjudication"].append(
                    f"BHPS at ε={cell['eps']:.2f}, L={cell['n_landmarks']}: "
                    f"{len(long)} long-lived H₀ bars present. "
                    f"Feature sub-structure survives within BHPS era."
                )
                break

    # Final verdict
    bhps_eps1 = comparison.get("bhps_features", {}).get("n_h0_bars", 0)
    usoc_eps1 = comparison.get("usoc_features", {}).get("n_h0_bars", 0)

    if bhps_eps1 > 1 and usoc_eps1 > 1:
        verdict = (
            "BOTH eras show internal topological sub-structure at ε=1.0. "
            "Full-panel features are genuine, not merge artefacts."
        )
    elif bhps_eps1 > 1 and usoc_eps1 == 1:
        verdict = (
            "BHPS era has internal sub-structure; USoc does not. "
            "The full-panel 2008.5 feature may reflect BHPS-era clusters "
            "merging with the USoc-era connected mass, rather than a GFC "
            "structural break. Requires careful interpretation in the paper."
        )
    elif bhps_eps1 == 1 and usoc_eps1 == 1:
        verdict = (
            "Neither era shows sub-structure at ε=1.0. The full-panel's "
            "multi-component structure arises entirely from the BHPS→USoc "
            "junction. This is a survey-transition artefact; the paper "
            "must not claim GFC causation without further evidence."
        )
    else:
        verdict = "Insufficient data for a definitive verdict."

    comparison["verdict"] = verdict
    comparison["adjudication"].append(f"VERDICT: {verdict}")

    logger.info("=" * 70)
    logger.info("ERA ROBUSTNESS VERDICT")
    logger.info("=" * 70)
    for note in comparison["adjudication"]:
        logger.info("  %s", note)

    comp_path = output_dir / "era_comparison.json"
    with open(comp_path, "w") as f:
        json.dump(_convert(comparison), f, indent=2)
    logger.info("Saved comparison: %s", comp_path)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Era-specific zigzag robustness grid.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint-dir", default="results/trajectory_tda_full")
    parser.add_argument("--output-dir", default="results/trajectory_tda_zigzag/era_robustness")
    parser.add_argument(
        "--knee-json",
        default="results/trajectory_tda_zigzag/sensitivity_2d/knee_analysis.json",
    )
    parser.add_argument("--landmark-counts", nargs="+", type=int, default=[100, 150])
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument("--wsl-python", default="/tmp/dionysus_env/bin/python")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_era_robustness(
        checkpoint_dir=Path(args.checkpoint_dir),
        output_dir=Path(args.output_dir),
        knee_json=Path(args.knee_json),
        landmark_counts=args.landmark_counts,
        max_dim=args.max_dim,
        wsl_python=args.wsl_python,
    )


if __name__ == "__main__":
    main()
