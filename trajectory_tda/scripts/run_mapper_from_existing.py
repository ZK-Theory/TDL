"""Run Mapper pipeline using existing P01 embeddings and GMM labels.

Bypasses the full load_embeddings() call since trajectory sequences
are not available in the integration results directory. Uses embeddings.npy
and gmm_labels from 05_analysis.json directly.

Usage:
    python -m trajectory_tda.scripts.run_mapper_from_existing
    python -m trajectory_tda.scripts.run_mapper_from_existing \\
        --results-dir results/trajectory_tda_integration \\
        --output-dir results/trajectory_tda_mapper \\
        --disadvantaged-regimes 2 6
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


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


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run Mapper pipeline from existing P01 embeddings and GMM labels.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/trajectory_tda_integration"),
        help=("Directory containing P01 integration outputs " "(embeddings.npy, 05_analysis.json)."),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/trajectory_tda_mapper"),
        help="Directory to write Mapper outputs.",
    )
    parser.add_argument(
        "--disadvantaged-regimes",
        type=int,
        nargs="+",
        default=None,
        metavar="REGIME_IDX",
        help=(
            "Regime indices treated as disadvantaged for escape probability. "
            "If omitted, inferred from regime profiles in 05_analysis.json "
            "(dominant_state in {inactive, low_income}), falling back to [2, 6]."
        ),
    )
    return parser.parse_args()


def _infer_disadvantaged_regimes(analysis: dict) -> list[int]:
    """Infer disadvantaged regime indices from 05_analysis.json metadata.

    Looks for regimes whose dominant_state matches known disadvantaged labels.
    Falls back to [2, 6] if no profiles are found.

    Args:
        analysis: Dict loaded from 05_analysis.json.

    Returns:
        Sorted list of disadvantaged regime indices.
    """
    profiles = analysis.get("regimes", {}).get("profiles", {})
    if not profiles:
        logger.warning("No regime profiles in 05_analysis.json; defaulting to [2, 6].")
        return [2, 6]

    disadvantaged_states = {"inactive", "low_income", "low-income", "inactive_low"}
    inferred = [
        int(rid)
        for rid, prof in profiles.items()
        if str(prof.get("dominant_state", "")).lower() in disadvantaged_states
    ]
    if not inferred:
        logger.warning("Could not infer disadvantaged regimes from profiles; defaulting to [2, 6].")
        return [2, 6]

    logger.info("Inferred disadvantaged regimes from metadata: %s", sorted(inferred))
    return sorted(inferred)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _parse_args()
    results_dir = args.results_dir
    output_dir = args.output_dir

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

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)

    all_results: dict = {}
    t0 = time.time()

    # Step 1: Load existing data
    logger.info("=" * 60)
    logger.info("Step 1: Loading embeddings and GMM labels from P01")
    logger.info("=" * 60)

    embeddings = np.load(results_dir / "embeddings.npy")
    logger.info("Embeddings: %s", embeddings.shape)

    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)

    gmm_labels = np.array(analysis["gmm_labels"], dtype=np.int64)
    n_regimes = analysis["regimes"]["k_optimal"]
    logger.info("GMM labels: %d, k_optimal: %d", len(gmm_labels), n_regimes)

    # Validate alignment between embeddings and GMM labels before running
    n_embeddings = embeddings.shape[0]
    n_labels = len(gmm_labels)
    if n_embeddings != n_labels:
        msg = (
            "Mismatch between embeddings and GMM labels: "
            f"{n_embeddings} embeddings loaded from "
            f"'{results_dir / 'embeddings.npy'}' "
            f"but {n_labels} GMM labels loaded from "
            f"'{results_dir / '05_analysis.json'}'. "
            "These must have the same length for Mapper and validation; "
            "please regenerate the inputs so they are aligned."
        )
        logger.error(msg)
        raise ValueError(msg)

    # Derive disadvantaged regimes from CLI override or metadata
    if args.disadvantaged_regimes is not None:
        disadvantaged_regimes = args.disadvantaged_regimes
        logger.info("Disadvantaged regimes (from CLI): %s", disadvantaged_regimes)
    else:
        disadvantaged_regimes = _infer_disadvantaged_regimes(analysis)
        logger.info("Disadvantaged regimes (inferred): %s", disadvantaged_regimes)

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
    _save_json(grid_results, output_dir / "01_parameter_search.json")

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
    _save_json(broad_save, output_dir / "01b_broad_grid_search.json")

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
    all_results["02_mapper_graph"]["params"] = {
        "projection": proj,
        "n_cubes": nc,
        "overlap_frac": ov,
    }
    _save_json(all_results["02_mapper_graph"], output_dir / "02_mapper_graph.json")

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
    _save_json(summary_default, output_dir / "02b_mapper_graph_default.json")

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
    _save_json(colorings_save, output_dir / "03_node_coloring.json")

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
    _save_json(validation_save, output_dir / "04_validation.json")

    # Step 6: Sub-regime structure
    logger.info("=" * 60)
    logger.info("Step 6: Identifying sub-regime structure")
    logger.info("=" * 60)

    # 6a. Sub-regimes using escape probability (original behaviour)
    subregime_escape = identify_subregime_structure(graph, gmm_labels, escape_prob)
    all_results["05_subregime_escape_prob"] = subregime_escape
    # Preserve original filename for backwards compatibility
    _save_json(subregime_escape, output_dir / "05_subregime_structure.json")

    # 6b. Sub-regimes using continuous outcomes from embeddings (PC1 and L2 norm)
    #     These reproduce the manuscript's PC1/L2 sub-regime results; escape_prob
    #     is binary so it rarely yields sub-regimes under the z-score threshold.
    pc1_values = embeddings[:, 0]
    l2_values = np.linalg.norm(embeddings, axis=1)

    subregime_pc1 = identify_subregime_structure(graph, gmm_labels, pc1_values)
    subregime_l2 = identify_subregime_structure(graph, gmm_labels, l2_values)

    all_results["05_subregime_pc1"] = subregime_pc1
    all_results["05_subregime_l2"] = subregime_l2

    _save_json(subregime_pc1, output_dir / "05_subregime_pc1_structure.json")
    _save_json(subregime_l2, output_dir / "05_subregime_l2_structure.json")

    # Step 7: Save graph + HTML
    logger.info("=" * 60)
    logger.info("Step 7: Saving graph and HTML visualisation")
    logger.info("=" * 60)

    save_mapper_graph(
        graph,
        str(output_dir / "06_mapper_graph.json"),
        mapper_obj=mapper_obj,
        color_values=escape_prob,
    )

    # Additional HTML coloured by regime labels
    try:
        mapper_obj.visualize(
            graph,
            path_html=str(output_dir / "figures" / "mapper_escape_prob.html"),
            title="Trajectory Mapper - Escape Probability",
            color_values=escape_prob,
        )
        mapper_obj.visualize(
            graph,
            path_html=str(output_dir / "figures" / "mapper_regime_labels.html"),
            title="Trajectory Mapper - GMM Regime Labels",
            color_values=gmm_labels.astype(np.float64),
        )
        logger.info("Saved HTML visualisations to figures/")
    except Exception:
        logger.warning("HTML visualisation failed", exc_info=True)

    elapsed = time.time() - t0
    all_results["elapsed_seconds"] = elapsed
    _save_json(all_results, output_dir / "07_pipeline_results.json")

    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds", elapsed)
    logger.info("Results saved to %s", output_dir)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
