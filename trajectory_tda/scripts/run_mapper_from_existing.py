"""Run Mapper pipeline using existing P01 embeddings and GMM labels.

Bypasses the full load_embeddings() call since trajectory sequences
are not available in the integration results directory. Uses embeddings.npy
and gmm_labels from 05_analysis.json directly.

Usage:
    python -m trajectory_tda.scripts.run_mapper_from_existing
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

RESULTS_DIR = Path("results/trajectory_tda_integration")
OUTPUT_DIR = Path("results/trajectory_tda_mapper")


def _save_json(data: dict, path: Path) -> None:
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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from trajectory_tda.mapper.mapper_pipeline import (
        build_mapper_graph,
        mapper_graph_summary,
        save_mapper_graph,
    )
    from trajectory_tda.mapper.node_coloring import (
        color_nodes_by_outcome,
        compute_escape_probability,
        compute_node_regime_distribution,
    )
    from trajectory_tda.mapper.parameter_search import (
        mapper_parameter_search,
        parameter_grid_search,
    )
    from trajectory_tda.mapper.validation import (
        compute_node_membership_labels,
        identify_subregime_structure,
        validate_against_regimes,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "figures").mkdir(exist_ok=True)

    all_results: dict = {}
    t0 = time.time()

    # Step 1: Load existing data
    logger.info("=" * 60)
    logger.info("Step 1: Loading embeddings and GMM labels from P01")
    logger.info("=" * 60)

    embeddings = np.load(RESULTS_DIR / "embeddings.npy")
    logger.info("Embeddings: %s", embeddings.shape)

    with open(RESULTS_DIR / "05_analysis.json") as f:
        analysis = json.load(f)

    gmm_labels = np.array(analysis["gmm_labels"], dtype=np.int64)
    n_regimes = analysis["regimes"]["k_optimal"]
    logger.info("GMM labels: %d, k_optimal: %d", len(gmm_labels), n_regimes)

    # Validate alignment between embeddings and GMM labels before running Mapper/validation
    n_embeddings = embeddings.shape[0]
    n_labels = len(gmm_labels)
    if n_embeddings != n_labels:
        msg = (
            "Mismatch between embeddings and GMM labels: "
            f"{n_embeddings} embeddings loaded from '{RESULTS_DIR / 'embeddings.npy'}' "
            f"but {n_labels} GMM labels loaded from '{RESULTS_DIR / '05_analysis.json'}'. "
            "These must have the same length for Mapper and validation; "
            "please regenerate the inputs so they are aligned."
        )
        logger.error(msg)
        raise ValueError(msg)
    # Identify disadvantaged regimes from P01: Regime 2 (Inactive Low) and Regime 6 (Low-Income Churn)
    disadvantaged_regimes = [2, 6]

    # Step 2: Parameter grid search
    logger.info("=" * 60)
    logger.info("Step 2: Parameter grid search")
    logger.info("=" * 60)

    grid_results = mapper_parameter_search(
        embeddings,
        n_cubes_range=[10, 15, 20, 25],
        overlap_range=[0.2, 0.3, 0.4, 0.5],
    )
    all_results["01_parameter_search"] = grid_results
    _save_json(grid_results, OUTPUT_DIR / "01_parameter_search.json")

    # Broader multi-projection search
    broad_results = parameter_grid_search(
        embeddings,
        n_cubes_range=[10, 15, 20, 25, 30],
        overlap_range=[0.2, 0.3, 0.4, 0.5],
        projections=["pca_2d", "l2norm"],
    )
    best = broad_results["best"]
    broad_save = {
        "best": best,
        "n_evaluated": broad_results["n_evaluated"],
        "results": [
            {
                "params": r["params"],
                "n_nodes": r["summary"]["n_nodes"] if r["summary"] else None,
                "n_edges": r["summary"]["n_edges"] if r["summary"] else None,
                "coverage": r["summary"]["coverage"] if r["summary"] else None,
                "n_components": (r["summary"]["n_connected_components"] if r["summary"] else None),
            }
            for r in broad_results["results"]
        ],
    }
    all_results["01b_broad_grid_search"] = broad_save
    _save_json(broad_save, OUTPUT_DIR / "01b_broad_grid_search.json")

    # Step 3: Build Mapper graph with best parameters
    logger.info("=" * 60)
    logger.info("Step 3: Building Mapper graph with best parameters: %s", best)
    logger.info("=" * 60)

    proj = best.get("projection", "pca_2d") if best else "pca_2d"
    nc = best.get("n_cubes", 15) if best else 15
    ov = best.get("overlap_frac", 0.3) if best else 0.3

    graph, mapper_obj = build_mapper_graph(
        embeddings,
        projection=proj,
        n_cubes=nc,
        overlap_frac=ov,
        verbose=1,
    )
    summary = mapper_graph_summary(graph)
    all_results["02_mapper_graph"] = summary
    all_results["02_mapper_graph"]["params"] = {"projection": proj, "n_cubes": nc, "overlap_frac": ov}
    _save_json(all_results["02_mapper_graph"], OUTPUT_DIR / "02_mapper_graph.json")

    # Also build with default params for comparison
    logger.info("Building default-params graph (pca_2d, 15, 0.3) for comparison")
    graph_default, mapper_default = build_mapper_graph(
        embeddings,
        projection="pca_2d",
        n_cubes=15,
        overlap_frac=0.3,
        verbose=0,
    )
    summary_default = mapper_graph_summary(graph_default)
    all_results["02b_mapper_graph_default"] = summary_default
    _save_json(summary_default, OUTPUT_DIR / "02b_mapper_graph_default.json")

    # Step 4: Node colouring
    logger.info("=" * 60)
    logger.info("Step 4: Node colouring (escape probability, regime distribution)")
    logger.info("=" * 60)

    escape_prob = compute_escape_probability(gmm_labels, disadvantaged_regimes)
    escape_coloring = color_nodes_by_outcome(graph, escape_prob, "escape_probability")
    regime_dist = compute_node_regime_distribution(graph, gmm_labels, n_regimes=n_regimes)

    # Regime label coloring
    regime_coloring = color_nodes_by_outcome(graph, gmm_labels.astype(np.float64), "regime_label")

    colorings_save = {
        "escape_probability": {
            nid: {k: v for k, v in stats.items() if k != "members"} for nid, stats in escape_coloring.items()
        },
        "regime_label": {
            nid: {k: v for k, v in stats.items() if k != "members"} for nid, stats in regime_coloring.items()
        },
        "regime_distribution": regime_dist,
    }
    all_results["03_node_coloring"] = colorings_save
    _save_json(colorings_save, OUTPUT_DIR / "03_node_coloring.json")

    # Step 5: Validate against GMM regimes
    logger.info("=" * 60)
    logger.info("Step 5: Validating against GMM regimes")
    logger.info("=" * 60)

    validation = validate_against_regimes(graph, gmm_labels, n_regimes=n_regimes)
    membership_labels = compute_node_membership_labels(graph, len(embeddings))

    validation_save = {k: v for k, v in validation.items() if k != "per_node_regime_distribution"}
    validation_save["per_node_regime_distribution_sample"] = dict(
        list(validation["per_node_regime_distribution"].items())[:10]
    )
    validation_save["membership_label_counts"] = {
        "assigned": int(np.sum(membership_labels >= 0)),
        "unassigned": int(np.sum(membership_labels == -1)),
    }
    all_results["04_validation"] = validation_save
    _save_json(validation_save, OUTPUT_DIR / "04_validation.json")

    # Step 6: Sub-regime structure
    logger.info("=" * 60)
    logger.info("Step 6: Identifying sub-regime structure")
    logger.info("=" * 60)

    subregime = identify_subregime_structure(graph, gmm_labels, escape_prob)
    all_results["05_subregime"] = subregime
    _save_json(subregime, OUTPUT_DIR / "05_subregime_structure.json")

    # Step 7: Save graph + HTML
    logger.info("=" * 60)
    logger.info("Step 7: Saving graph and HTML visualisation")
    logger.info("=" * 60)

    save_mapper_graph(
        graph,
        str(OUTPUT_DIR / "06_mapper_graph.json"),
        mapper_obj=mapper_obj,
        color_values=escape_prob,
    )

    # Additional HTML coloured by regime labels
    try:
        mapper_obj.visualize(
            graph,
            path_html=str(OUTPUT_DIR / "figures" / "mapper_escape_prob.html"),
            title="Trajectory Mapper - Escape Probability",
            color_values=escape_prob,
        )
        mapper_obj.visualize(
            graph,
            path_html=str(OUTPUT_DIR / "figures" / "mapper_regime_labels.html"),
            title="Trajectory Mapper - GMM Regime Labels",
            color_values=gmm_labels.astype(np.float64),
        )
        logger.info("Saved HTML visualisations to figures/")
    except Exception:
        logger.warning("HTML visualisation failed", exc_info=True)

    elapsed = time.time() - t0
    all_results["elapsed_seconds"] = elapsed
    _save_json(all_results, OUTPUT_DIR / "07_pipeline_results.json")

    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds", elapsed)
    logger.info("Results saved to %s", OUTPUT_DIR)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
