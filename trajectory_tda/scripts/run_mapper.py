"""Run the full Mapper pipeline for Paper 2.

Loads pre-computed PCA-20D embeddings from Paper 1, builds KeplerMapper
graphs with multiple parameter configurations, colors nodes by trajectory
outcomes, and validates the Mapper decomposition against GMM regimes.

Usage:
    python -m trajectory_tda.scripts.run_mapper \\
        --results-dir results/trajectory_tda_integration \\
        --output-dir results/trajectory_tda_mapper

    # Synthetic mode (no real data needed):
    python -m trajectory_tda.scripts.run_mapper --synthetic
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the Mapper pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


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
            return list(obj)
        return obj

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=convert)
    logger.info("Saved %s", path)


def _generate_synthetic_data(
    n: int = 300,
    d: int = 20,
    k: int = 5,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic clustered embeddings and regime labels.

    Creates *k* Gaussian clusters in *d* dimensions so that the Mapper
    pipeline can be exercised without access to real UKDS data.

    Args:
        n: Total number of points (distributed evenly across clusters).
        d: Embedding dimensionality.
        k: Number of clusters / regimes.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (embeddings, regime_labels) where embeddings is (n, d)
        and regime_labels is (n,) with integer labels in [0, k).
    """
    rng = np.random.RandomState(seed)
    centers = rng.randn(k, d) * 4
    per_cluster = n // k
    points = []
    labels = []
    for i, c in enumerate(centers):
        count = per_cluster if i < k - 1 else n - per_cluster * (k - 1)
        points.append(c + rng.randn(count, d) * 0.8)
        labels.extend([i] * count)
    return np.vstack(points), np.array(labels, dtype=np.int64)


def run_synthetic_pipeline(output_dir: str, skip_grid_search: bool = False) -> dict:
    """Run the Mapper pipeline on synthetic data.

    This mode generates random clustered embeddings and regime labels,
    then runs the full pipeline for testing and development purposes.

    Args:
        output_dir: Path to output directory for results.
        skip_grid_search: If True, skip the parameter grid search step.

    Returns:
        Dict with all pipeline results.
    """
    from trajectory_tda.mapper.mapper_pipeline import (
        build_mapper_graph,
        mapper_graph_summary,
        save_mapper_graph,
    )
    from trajectory_tda.mapper.node_coloring import (
        color_nodes_by_outcome,
        compute_node_regime_distribution,
    )
    from trajectory_tda.mapper.parameter_search import mapper_parameter_search
    from trajectory_tda.mapper.validation import (
        compute_node_membership_labels,
        validate_against_regimes,
    )

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(exist_ok=True)

    all_results: dict = {}
    t0 = time.time()

    # Step 1: Generate synthetic data
    logger.info("=" * 60)
    logger.info("Step 1: Generating synthetic data (300 pts, 20D, 5 clusters)")
    logger.info("=" * 60)
    embeddings, regime_labels = _generate_synthetic_data(n=300, d=20, k=5)
    n_regimes = int(regime_labels.max()) + 1
    logger.info("  Embeddings: %s, Regimes: %d", embeddings.shape, n_regimes)

    # Step 2: Build Mapper graph
    logger.info("=" * 60)
    logger.info("Step 2: Building Mapper graph (default parameters)")
    logger.info("=" * 60)
    graph, mapper_obj = build_mapper_graph(
        embeddings,
        projection="pca_2d",
        n_cubes=15,
        overlap_frac=0.3,
        verbose=1,
    )
    summary = mapper_graph_summary(graph)
    all_results["01_mapper_graph"] = summary
    _save_json(summary, outdir / "01_mapper_graph.json")

    # Step 3: Color nodes by regime membership
    logger.info("=" * 60)
    logger.info("Step 3: Coloring nodes by regime membership")
    logger.info("=" * 60)
    regime_coloring = color_nodes_by_outcome(
        graph,
        regime_labels.astype(np.float64),
        outcome_name="regime_label",
    )
    regime_dist = compute_node_regime_distribution(graph, regime_labels, n_regimes=n_regimes)

    colorings_save = {
        "regime_label": {
            nid: {k: v for k, v in stats.items() if k != "members"}
            for nid, stats in regime_coloring.items()
        },
        "regime_distribution": regime_dist,
    }
    all_results["02_node_coloring"] = colorings_save
    _save_json(colorings_save, outdir / "02_node_coloring.json")

    # Step 4: Parameter search (optional)
    if not skip_grid_search:
        logger.info("=" * 60)
        logger.info("Step 4: Parameter grid search")
        logger.info("=" * 60)
        grid_results = mapper_parameter_search(
            embeddings,
            n_cubes_range=[10, 15, 20, 25],
            overlap_range=[0.2, 0.3, 0.4, 0.5],
        )
        all_results["03_parameter_search"] = grid_results
        _save_json(grid_results, outdir / "03_parameter_search.json")
    else:
        logger.info("Step 4: Skipped (--skip-grid-search)")

    # Step 5: Validate against regimes
    logger.info("=" * 60)
    logger.info("Step 5: Validating against regime labels")
    logger.info("=" * 60)
    validation = validate_against_regimes(graph, regime_labels, n_regimes=n_regimes)
    membership_labels = compute_node_membership_labels(graph, len(embeddings))

    validation_save = {k: v for k, v in validation.items() if k != "per_node_regime_distribution"}
    validation_save["membership_label_counts"] = {
        "assigned": int(np.sum(membership_labels >= 0)),
        "unassigned": int(np.sum(membership_labels == -1)),
    }
    all_results["04_validation"] = validation_save
    _save_json(validation_save, outdir / "04_validation.json")

    # Step 6: Save graph
    logger.info("=" * 60)
    logger.info("Step 6: Saving Mapper graph and HTML visualization")
    logger.info("=" * 60)
    save_mapper_graph(
        graph,
        str(outdir / "05_mapper_graph.json"),
        mapper_obj=mapper_obj,
        color_values=regime_labels.astype(np.float64),
    )

    elapsed = time.time() - t0
    all_results["elapsed_seconds"] = elapsed
    _save_json(all_results, outdir / "06_pipeline_results.json")

    logger.info("=" * 60)
    logger.info("Synthetic pipeline complete in %.1f seconds", elapsed)
    logger.info("Results saved to %s", outdir)
    logger.info("=" * 60)

    return all_results


def run_pipeline(
    results_dir: str,
    output_dir: str,
    skip_grid_search: bool = False,
) -> dict:
    """Run the full Mapper pipeline.

    Args:
        results_dir: Path to P01 results directory.
        output_dir: Path to output directory for Mapper results.
        skip_grid_search: If True, skip the parameter grid search step.

    Returns:
        Dict with all pipeline results.
    """
    from trajectory_tda.mapper.mapper_pipeline import (
        build_mapper_graph,
        load_embeddings,
        mapper_graph_summary,
        save_mapper_graph,
    )
    from trajectory_tda.mapper.node_coloring import (
        compute_all_colorings,
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

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(exist_ok=True)

    all_results: dict = {}
    t0 = time.time()

    # Step 1: Load embeddings + trajectories + metadata
    logger.info("=" * 60)
    logger.info("Step 1: Loading embeddings and metadata from P01")
    logger.info("=" * 60)
    embeddings, trajectories, metadata = load_embeddings(results_dir)
    logger.info("  Embeddings: %s", embeddings.shape)
    logger.info("  Trajectories: %d", len(trajectories))

    # Step 2: Build Mapper graph with default parameters
    logger.info("=" * 60)
    logger.info("Step 2: Building Mapper graph (default parameters)")
    logger.info("=" * 60)
    graph, mapper_obj = build_mapper_graph(
        embeddings,
        projection="pca_2d",
        n_cubes=15,
        overlap_frac=0.3,
        verbose=1,
    )
    summary = mapper_graph_summary(graph)
    all_results["01_mapper_graph"] = summary
    _save_json(summary, outdir / "01_mapper_graph.json")

    # Step 3: Color nodes by regime membership and outcomes
    logger.info("=" * 60)
    logger.info("Step 3: Coloring nodes by outcome variables")
    logger.info("=" * 60)
    colorings = compute_all_colorings(graph, embeddings, trajectories, metadata)

    # Also compute regime distribution
    analysis = metadata.get("analysis", {})
    gmm_labels = np.array(analysis.get("gmm_labels", []), dtype=np.int64)
    n_regimes = analysis.get("regimes", {}).get("k_optimal", 7)
    regime_dist = {}
    if len(gmm_labels) > 0:
        regime_dist = compute_node_regime_distribution(graph, gmm_labels, n_regimes=n_regimes)

    colorings_summary = {}
    for cname, cdata in colorings.items():
        colorings_summary[cname] = {
            node_id: {k: v for k, v in stats.items() if k != "members"}
            for node_id, stats in cdata.items()
        }
    colorings_summary["regime_distribution"] = regime_dist
    all_results["02_node_coloring"] = colorings_summary
    _save_json(colorings_summary, outdir / "02_node_coloring.json")

    # Step 4: Parameter grid search
    if not skip_grid_search:
        logger.info("=" * 60)
        logger.info("Step 4: Parameter grid search")
        logger.info("=" * 60)
        grid_results = mapper_parameter_search(
            embeddings,
            n_cubes_range=[10, 15, 20, 25],
            overlap_range=[0.2, 0.3, 0.4, 0.5],
        )
        all_results["03_parameter_search"] = grid_results
        _save_json(grid_results, outdir / "03_parameter_search.json")

        # Also run the broader multi-projection search
        broad_results = parameter_grid_search(
            embeddings,
            n_cubes_range=[10, 15, 20, 25, 30],
            overlap_range=[0.2, 0.3, 0.4, 0.5],
            projections=["pca_2d", "l2norm"],
        )
        all_results["03b_broad_grid_search"] = {
            "best": broad_results["best"],
            "n_evaluated": broad_results["n_evaluated"],
            "results": [
                {
                    "params": r["params"],
                    "n_nodes": r["summary"]["n_nodes"] if r["summary"] else None,
                    "n_edges": r["summary"]["n_edges"] if r["summary"] else None,
                    "coverage": r["summary"]["coverage"] if r["summary"] else None,
                    "n_components": (
                        r["summary"]["n_connected_components"] if r["summary"] else None
                    ),
                }
                for r in broad_results["results"]
            ],
        }

        # Rebuild with best parameters if different from default
        best = broad_results["best"]
        if best and (best.get("n_cubes") != 15 or best.get("overlap_frac") != 0.3):
            logger.info("Rebuilding graph with best parameters: %s", best)
            graph, mapper_obj = build_mapper_graph(
                embeddings,
                projection=best.get("projection", "pca_2d"),
                n_cubes=best.get("n_cubes", 15),
                overlap_frac=best.get("overlap_frac", 0.3),
                verbose=1,
            )
    else:
        logger.info("Step 4: Skipped (--skip-grid-search)")

    # Step 5: Validate against GMM regimes
    logger.info("=" * 60)
    logger.info("Step 5: Validating against GMM regimes")
    logger.info("=" * 60)

    if len(gmm_labels) > 0:
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
        _save_json(validation_save, outdir / "04_validation.json")
    else:
        logger.warning("No GMM labels found; skipping validation")

    # Step 6: Identify sub-regime structure
    logger.info("=" * 60)
    logger.info("Step 6: Identifying sub-regime structure")
    logger.info("=" * 60)
    if len(gmm_labels) > 0:
        from trajectory_tda.mapper.node_coloring import compute_employment_rate

        emp_rate = compute_employment_rate(trajectories)
        subregime = identify_subregime_structure(graph, gmm_labels, emp_rate)
        all_results["05_subregime"] = subregime
        _save_json(subregime, outdir / "05_subregime_structure.json")
    else:
        logger.warning("No GMM labels found; skipping sub-regime analysis")

    # Step 7: Save graph and generate HTML visualisation
    logger.info("=" * 60)
    logger.info("Step 7: Saving graph and generating HTML visualisations")
    logger.info("=" * 60)
    color_values = (
        gmm_labels.astype(np.float64) if len(gmm_labels) > 0 else embeddings[:, 0]
    )
    save_mapper_graph(
        graph,
        str(outdir / "06_mapper_graph.json"),
        mapper_obj=mapper_obj,
        color_values=color_values,
    )

    try:
        # Additional HTML with employment rate coloring
        from trajectory_tda.mapper.node_coloring import compute_employment_rate

        emp_rate = compute_employment_rate(trajectories)
        mapper_obj.visualize(
            graph,
            path_html=str(outdir / "figures" / "mapper_graph_employment.html"),
            title="Trajectory Mapper - colored by Employment Rate",
            color_values=emp_rate,
        )
        logger.info("Saved employment-rate HTML to figures/mapper_graph_employment.html")
    except Exception:
        logger.warning("Employment-rate HTML visualisation failed", exc_info=True)

    elapsed = time.time() - t0
    all_results["elapsed_seconds"] = elapsed
    _save_json(all_results, outdir / "07_pipeline_results.json")

    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds", elapsed)
    logger.info("Results saved to %s", outdir)
    logger.info("=" * 60)

    return all_results


def main() -> None:
    """CLI entry point for the Mapper pipeline."""
    parser = argparse.ArgumentParser(description="Run KeplerMapper pipeline for Paper 2")
    parser.add_argument(
        "--results-dir",
        default="results/trajectory_tda_integration",
        help="Path to P01 results directory",
    )
    parser.add_argument(
        "--output-dir",
        default="results/trajectory_tda_mapper",
        help="Output directory for Mapper results",
    )
    parser.add_argument(
        "--skip-grid-search",
        action="store_true",
        help="Skip parameter grid search (faster)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic data instead of loading real embeddings (for testing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if args.synthetic:
        run_synthetic_pipeline(
            output_dir=args.output_dir,
            skip_grid_search=args.skip_grid_search,
        )
    else:
        run_pipeline(
            results_dir=args.results_dir,
            output_dir=args.output_dir,
            skip_grid_search=args.skip_grid_search,
        )


if __name__ == "__main__":
    main()
