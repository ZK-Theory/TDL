"""
End-to-end pipeline orchestrator for trajectory TDA.

Run from command line:
    python -m trajectory_tda.scripts.run_pipeline \\
        --data-dir data --min-years 10 --n-perms 100 \\
        --landmarks 5000 --embed pca20 --nulls all \\
        --checkpoint results/trajectory_tda/
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
    """Configure logging for the pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_checkpoint(data: dict, path: Path, name: str) -> None:
    """Save checkpoint data to JSON."""
    path.mkdir(parents=True, exist_ok=True)
    fpath = path / f"{name}.json"

    # Convert numpy arrays to lists for JSON
    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    with open(fpath, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Checkpoint saved: {fpath}")


def run_pipeline(args: argparse.Namespace) -> dict:
    """Execute the full trajectory TDA pipeline.

    Steps:
        1. Extract employment status + income bands
        2. Build trajectories
        3. Embed (n-grams + PCA/UMAP)
        4. Compute PH (witness + maxmin VR)
        5. Permutation tests
        6. Analysis (regimes, cycles, groups)
    """
    from trajectory_tda.analysis.cycle_detection import detect_cycles
    from trajectory_tda.analysis.regime_discovery import discover_regimes
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.topology.permutation_nulls import (
        permutation_test_trajectories,
    )
    from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

    t0 = time.time()
    checkpoint_dir = Path(args.checkpoint) if args.checkpoint else None
    results = {"args": vars(args)}

    # ─── Step 1–2: Build trajectories ───
    logger.info("=" * 60)
    logger.info("Step 1-2: Building trajectories from BHPS/USoc")
    logger.info("=" * 60)

    trajectories, metadata = build_trajectories_from_raw(
        data_dir=args.data_dir,
        min_years=args.min_years,
        max_gap=args.max_gap,
        income_threshold=args.income_threshold,
    )

    results["n_trajectories"] = len(trajectories)
    results["trajectory_lengths"] = {
        "mean": float(metadata["n_years"].mean()),
        "min": int(metadata["n_years"].min()),
        "max": int(metadata["n_years"].max()),
    }

    if checkpoint_dir:
        _save_checkpoint(
            {"metadata": metadata.to_dict(), "n": len(trajectories)},
            checkpoint_dir,
            "01_trajectories",
        )

    # ─── Step 3: Embed ───
    logger.info("=" * 60)
    logger.info("Step 3: Embedding trajectories")
    logger.info("=" * 60)

    pca_dim = None
    umap_dim = None
    if args.embed.startswith("pca"):
        pca_dim = int(args.embed[3:])
    elif args.embed.startswith("umap"):
        umap_dim = int(args.embed[4:])
    elif args.embed == "raw":
        pass

    embeddings, embed_info = ngram_embed(
        trajectories,
        include_bigrams=True,
        tfidf=args.tfidf,
        pca_dim=pca_dim,
        umap_dim=umap_dim,
    )

    results["embedding"] = embed_info

    if checkpoint_dir:
        _save_checkpoint(
            {"shape": list(embeddings.shape), "info": embed_info},
            checkpoint_dir,
            "02_embedding",
        )
        np.save(checkpoint_dir / "embeddings.npy", embeddings)

    # ─── Step 4: Compute PH ───
    logger.info("=" * 60)
    logger.info("Step 4: Computing persistent homology")
    logger.info("=" * 60)

    ph_result = compute_trajectory_ph(
        embeddings,
        max_dim=1,
        n_landmarks=args.landmarks,
        method="maxmin_vr",
        validate=True,
    )

    results["ph"] = {
        "n_landmarks": ph_result["n_landmarks"],
        "elapsed": ph_result["elapsed_seconds"],
        "summaries": {
            k: {dk: {kk: vv for kk, vv in dv.items() if kk != "features"} for dk, dv in v.items()}
            for k, v in ph_result.get("summaries", {}).items()
        },
    }

    if checkpoint_dir:
        _save_checkpoint(results["ph"], checkpoint_dir, "03_ph")
        # Save raw persistence diagrams for plotting
        raw_diagrams = {}
        for method_key in ["witness", "maxmin_vr"]:
            if method_key in ph_result:
                ph_obj = ph_result[method_key]
                raw_diagrams[method_key] = {str(dim): dgm.tolist() for dim, dgm in ph_obj.dgms.items()}
        _save_checkpoint(raw_diagrams, checkpoint_dir, "03_ph_diagrams")

    # ─── Step 5: Permutation tests ───
    logger.info("=" * 60)
    logger.info("Step 5: Permutation tests")
    logger.info("=" * 60)

    null_types = ["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"] if args.nulls == "all" else [args.nulls]

    embed_kwargs = {
        "include_bigrams": True,
        "tfidf": args.tfidf,
        "pca_dim": pca_dim,
        "umap_dim": umap_dim,
    }

    null_results = {}
    for null_type in null_types:
        logger.info(f"  Running {null_type} null...")
        try:
            nr = permutation_test_trajectories(
                embeddings=embeddings,
                trajectories=trajectories,
                null_type=null_type,
                n_permutations=args.n_perms,
                max_dim=1,
                n_landmarks=args.landmarks,
                statistic="total_persistence",
                markov_order=args.markov_order,
                embed_kwargs=embed_kwargs,
            )
            null_results[null_type] = nr
        except Exception as e:
            logger.warning(f"  {null_type} failed: {e}")
            null_results[null_type] = {"error": str(e)}

    results["null_tests"] = null_results

    if checkpoint_dir:
        _save_checkpoint(null_results, checkpoint_dir, "04_nulls")

    # ─── Step 6: Analysis ───
    logger.info("=" * 60)
    logger.info("Step 6: Analysis")
    logger.info("=" * 60)

    # Regime discovery
    regimes = discover_regimes(embeddings, trajectories, ph_result=ph_result)
    results["regimes"] = {
        "k_optimal": regimes["k_optimal"],
        "profiles": {
            str(k): {kk: vv for kk, vv in v.items() if kk != "composition"}
            for k, v in regimes["regime_profiles"].items()
        },
    }

    # Extract regime exemplars (5 closest to centroid per regime)
    regime_exemplars = {}
    gmm_labels = regimes["gmm_labels"]
    for label in np.unique(gmm_labels):
        mask = gmm_labels == label
        cluster_embeddings = embeddings[mask]
        cluster_indices = np.where(mask)[0]
        centroid = cluster_embeddings.mean(axis=0)
        dists = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        top5 = np.argsort(dists)[:5]
        exemplar_indices = cluster_indices[top5].tolist()
        regime_exemplars[str(label)] = {
            "indices": exemplar_indices,
            "trajectories": [trajectories[i] for i in exemplar_indices],
        }

    # Cycle detection
    cycles = detect_cycles(ph_result, embeddings, trajectories)
    results["cycles"] = {
        "n_persistent_loops": cycles["n_persistent_loops"],
        "h1_summary": cycles.get("h1_summary", {}),
    }

    if checkpoint_dir:
        _save_checkpoint(
            {
                "regimes": results["regimes"],
                "cycles": results["cycles"],
                "regime_exemplars": regime_exemplars,
                "gmm_labels": gmm_labels.tolist(),
            },
            checkpoint_dir,
            "05_analysis",
        )

    # ─── Summary ───
    elapsed = time.time() - t0
    results["elapsed_total"] = elapsed
    logger.info("=" * 60)
    logger.info(f"Pipeline complete in {elapsed:.1f}s")
    logger.info(
        f"  Trajectories: {len(trajectories)}, "
        f"Regimes: {regimes['k_optimal']}, "
        f"H₁ loops: {cycles['n_persistent_loops']}"
    )
    logger.info("=" * 60)

    if checkpoint_dir:
        _save_checkpoint(results, checkpoint_dir, "results_full")

    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Trajectory TDA: Employment × Income state-space analysis")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Root data directory (default: data/)",
    )
    parser.add_argument(
        "--min-years",
        type=int,
        default=10,
        help="Minimum trajectory length (default: 10)",
    )
    parser.add_argument(
        "--max-gap",
        type=int,
        default=2,
        help="Maximum gap for interpolation (default: 2)",
    )
    parser.add_argument(
        "--income-threshold",
        type=float,
        default=0.6,
        help="HBAI poverty threshold (default: 0.6)",
    )
    parser.add_argument(
        "--embed",
        type=str,
        default="pca20",
        help="Embedding: 'raw', 'pca20', 'umap16' etc. (default: pca20)",
    )
    parser.add_argument(
        "--tfidf",
        action="store_true",
        help="Apply TF-IDF weighting",
    )
    parser.add_argument(
        "--landmarks",
        type=int,
        default=5000,
        help="Number of landmarks for PH (default: 5000)",
    )
    parser.add_argument(
        "--n-perms",
        type=int,
        default=100,
        help="Number of permutations per null (default: 100)",
    )
    parser.add_argument(
        "--nulls",
        type=str,
        default="all",
        choices=[
            "all",
            "label_shuffle",
            "cohort_shuffle",
            "order_shuffle",
            "markov",
        ],
        help="Null model(s) to run (default: all)",
    )
    parser.add_argument(
        "--markov-order",
        type=int,
        default=1,
        choices=[1, 2],
        help="Markov null model order (default: 1)",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Directory for checkpoint saves",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    run_pipeline(args)


if __name__ == "__main__":
    main()
