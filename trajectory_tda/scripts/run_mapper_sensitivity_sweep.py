"""Mapper sensitivity sweep: eps, clustering algorithm, and lens functions.

Runs the Mapper pipeline across a grid of:
  - DBSCAN eps: {0.2, 0.3, 0.5}
  - Clustering algorithm: {DBSCAN, Agglomerative}
  - Lens functions: {pca_2d, l2norm, sum, density}
  - Cover: n_cubes=30, overlap=0.5 (best from prior grid search)

For each configuration, records:
  - Graph summary (nodes, edges, components, coverage)
  - Validation against GMM regimes (NMI, purity, bridge nodes)
  - Sub-regime structure (PC1, L2 norm)

Usage:
    python -m trajectory_tda.scripts.run_mapper_sensitivity_sweep
    python -m trajectory_tda.scripts.run_mapper_sensitivity_sweep \
        --results-dir results/trajectory_tda_integration \
        --output-dir results/trajectory_tda_mapper/sensitivity
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from itertools import product
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _save_json(data: dict | list, path: Path) -> None:
    """Save data to JSON with numpy type conversion."""

    def convert(obj: object) -> object:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, set):
            return sorted(obj)
        return obj

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=convert)
    logger.info("Saved %s", path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mapper sensitivity sweep across eps, clusterer, and lens."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/trajectory_tda_integration"),
        help="Directory containing P01 integration outputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/trajectory_tda_mapper/sensitivity"),
        help="Directory to write sweep outputs.",
    )
    return parser.parse_args()


def run_single_config(
    embeddings: np.ndarray,
    gmm_labels: np.ndarray,
    n_regimes: int,
    projection: str,
    n_cubes: int,
    overlap_frac: float,
    clusterer: str,
    clusterer_params: dict,
) -> dict:
    """Run Mapper + validation + sub-regime for one configuration.

    Returns a dict with graph summary, validation, and sub-regime results,
    or an error entry if the configuration fails.
    """
    from trajectory_tda.mapper.mapper_pipeline import (
        build_mapper_graph,
        mapper_graph_summary,
    )
    from trajectory_tda.mapper.validation import (
        identify_subregime_structure,
        validate_against_regimes,
    )

    config_label = (
        f"proj={projection} n_cubes={n_cubes} overlap={overlap_frac} "
        f"clusterer={clusterer} params={clusterer_params}"
    )

    try:
        graph, _ = build_mapper_graph(
            embeddings,
            projection=projection,
            n_cubes=n_cubes,
            overlap_frac=overlap_frac,
            clusterer=clusterer,
            clusterer_params=clusterer_params,
            verbose=0,
        )
    except Exception as exc:
        logger.warning("Build failed for %s: %s", config_label, exc)
        return {"error": str(exc)}

    summary = mapper_graph_summary(graph, n_points=len(embeddings))

    # Validation
    validation = validate_against_regimes(graph, gmm_labels, n_regimes=n_regimes)

    # Sub-regime on PC1 and L2 norm
    pc1_values = embeddings[:, 0]
    l2_values = np.linalg.norm(embeddings, axis=1)

    subregime_pc1 = identify_subregime_structure(graph, gmm_labels, pc1_values)
    subregime_l2 = identify_subregime_structure(graph, gmm_labels, l2_values)

    return {
        "summary": summary,
        "validation": {
            "nmi": validation["nmi"],
            "purity": validation["purity"],
            "n_bridge_nodes": validation["n_bridge_nodes"],
            "regime_fragmentation": validation["regime_fragmentation"],
        },
        "subregime_pc1": {
            "n_total": subregime_pc1["n_total"],
            "per_regime": subregime_pc1["summary"],
        },
        "subregime_l2": {
            "n_total": subregime_l2["n_total"],
            "per_regime": subregime_l2["summary"],
        },
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _parse_args()
    results_dir = args.results_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()

    # Load data
    logger.info("Loading embeddings and GMM labels from %s", results_dir)
    embeddings = np.load(results_dir / "embeddings.npy")
    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    gmm_labels = np.array(analysis["gmm_labels"], dtype=np.int64)
    n_regimes = analysis["regimes"]["k_optimal"]
    logger.info(
        "Loaded %d embeddings (%dD), %d regimes",
        len(embeddings),
        embeddings.shape[1],
        n_regimes,
    )

    # Fixed cover parameters (best from prior grid search)
    n_cubes = 30
    overlap_frac = 0.5

    # Sweep dimensions
    projections = ["pca_2d", "l2norm", "sum", "density"]
    dbscan_eps_values = [0.2, 0.3, 0.5]
    agglom_thresholds = [1.0, 1.5, 2.0]

    # Build configuration list
    configs: list[dict] = []

    # DBSCAN configs across projections and eps
    for proj, eps in product(projections, dbscan_eps_values):
        configs.append(
            {
                "projection": proj,
                "n_cubes": n_cubes,
                "overlap_frac": overlap_frac,
                "clusterer": "dbscan",
                "clusterer_params": {"eps": eps, "min_samples": 5},
                "label": f"{proj}_dbscan_eps{eps}",
            }
        )

    # Agglomerative configs across projections and thresholds
    for proj, thresh in product(projections, agglom_thresholds):
        configs.append(
            {
                "projection": proj,
                "n_cubes": n_cubes,
                "overlap_frac": overlap_frac,
                "clusterer": "agglomerative",
                "clusterer_params": {"threshold": thresh},
                "label": f"{proj}_agglom_t{thresh}",
            }
        )

    logger.info("Running %d configurations", len(configs))

    # Run sweep
    all_results: list[dict] = []
    for i, cfg in enumerate(configs):
        label = cfg["label"]
        logger.info("[%d/%d] %s", i + 1, len(configs), label)

        result = run_single_config(
            embeddings=embeddings,
            gmm_labels=gmm_labels,
            n_regimes=n_regimes,
            projection=cfg["projection"],
            n_cubes=cfg["n_cubes"],
            overlap_frac=cfg["overlap_frac"],
            clusterer=cfg["clusterer"],
            clusterer_params=cfg["clusterer_params"],
        )

        entry = {
            "config": {
                "projection": cfg["projection"],
                "n_cubes": cfg["n_cubes"],
                "overlap_frac": cfg["overlap_frac"],
                "clusterer": cfg["clusterer"],
                "clusterer_params": cfg["clusterer_params"],
            },
            "label": label,
            **result,
        }
        all_results.append(entry)

        # Log progress
        if "summary" in result:
            s = result["summary"]
            v = result["validation"]
            logger.info(
                "  -> nodes=%d edges=%d coverage=%.1f%% NMI=%.3f purity=%.3f "
                "bridge=%d subregime_pc1=%d subregime_l2=%d",
                s["n_nodes"],
                s["n_edges"],
                s["coverage"] * 100,
                v["nmi"],
                v["purity"],
                v["n_bridge_nodes"],
                result["subregime_pc1"]["n_total"],
                result["subregime_l2"]["n_total"],
            )
        else:
            logger.info("  -> FAILED: %s", result.get("error", "unknown"))

    elapsed = time.time() - t0

    # Save full results
    output = {
        "sweep_params": {
            "n_cubes": n_cubes,
            "overlap_frac": overlap_frac,
            "projections": projections,
            "dbscan_eps_values": dbscan_eps_values,
            "agglom_thresholds": agglom_thresholds,
            "n_configs": len(configs),
        },
        "elapsed_seconds": elapsed,
        "results": all_results,
    }
    _save_json(output, output_dir / "sweep_results.json")

    # Print summary table
    logger.info("=" * 80)
    logger.info("SWEEP SUMMARY (%d configs, %.1fs)", len(configs), elapsed)
    logger.info("=" * 80)
    logger.info(
        "%-30s %6s %6s %6s %7s %6s %6s %5s %5s",
        "Config",
        "Nodes",
        "Edges",
        "Comps",
        "Cover%",
        "NMI",
        "Purity",
        "PC1sr",
        "L2sr",
    )
    logger.info("-" * 80)
    for entry in all_results:
        if "summary" in entry:
            s = entry["summary"]
            v = entry["validation"]
            logger.info(
                "%-30s %6d %6d %6d %6.1f%% %6.3f %6.3f %5d %5d",
                entry["label"],
                s["n_nodes"],
                s["n_edges"],
                s["n_connected_components"],
                s["coverage"] * 100,
                v["nmi"],
                v["purity"],
                entry["subregime_pc1"]["n_total"],
                entry["subregime_l2"]["n_total"],
            )
        else:
            logger.info("%-30s  FAILED: %s", entry["label"], entry.get("error", "?"))

    logger.info("=" * 80)
    logger.info("Results saved to %s", output_dir / "sweep_results.json")


if __name__ == "__main__":
    main()
