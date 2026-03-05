"""
End-to-end pipeline orchestrator for trajectory TDA.

Run from command line:
    python -m trajectory_tda.scripts.run_pipeline \\
        --data-dir data --min-years 10 --n-perms 100 \\
        --landmarks 5000 --embed pca20 --nulls all \\
        --checkpoint results/trajectory_tda/

Resume from a checkpoint:
    python -m trajectory_tda.scripts.run_pipeline \\
        --checkpoint results/trajectory_tda/ --skip-to 4
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

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


def _load_checkpoint(path: Path, name: str) -> dict:
    """Load checkpoint data from JSON."""
    fpath = path / f"{name}.json"
    if not fpath.exists():
        raise FileNotFoundError(f"Checkpoint not found: {fpath}")
    with open(fpath) as f:
        data = json.load(f)
    logger.info(f"Checkpoint loaded: {fpath}")
    return data


def _load_prior_steps(checkpoint_dir: Path, skip_to: int) -> dict:
    """Load all checkpoints needed to resume from *skip_to*.

    Returns a dict with the loaded artefacts keyed by name.
    """
    from trajectory_tda.utils.model_io import load_model

    loaded: dict = {}

    # Step 1-2 artefacts
    if skip_to > 2:
        cp = _load_checkpoint(checkpoint_dir, "01_trajectories")
        loaded["metadata"] = pd.DataFrame(cp["metadata"])

        seq_path = checkpoint_dir / "01_trajectories_sequences.json"
        if seq_path.exists():
            with open(seq_path) as f:
                loaded["trajectories"] = json.load(f)
            logger.info(f"Loaded {len(loaded['trajectories'])} trajectory sequences")
        else:
            raise FileNotFoundError(
                f"Raw trajectory sequences not found at {seq_path}. "
                "Re-run the pipeline without --skip-to to generate them."
            )

    # Step 3 artefacts
    if skip_to > 3:
        emb_path = checkpoint_dir / "embeddings.npy"
        if not emb_path.exists():
            raise FileNotFoundError(f"Embeddings not found: {emb_path}")
        loaded["embeddings"] = np.load(emb_path)
        loaded["embed_info"] = _load_checkpoint(checkpoint_dir, "02_embedding")
        logger.info(f"Loaded embeddings: {loaded['embeddings'].shape}")

    # Step 4 artefacts
    if skip_to > 4:
        loaded["ph_checkpoint"] = _load_checkpoint(checkpoint_dir, "03_ph")
        diag_path = checkpoint_dir / "03_ph_diagrams.json"
        if diag_path.exists():
            loaded["ph_diagrams"] = _load_checkpoint(checkpoint_dir, "03_ph_diagrams")

    # Step 5 artefacts
    if skip_to > 5:
        loaded["null_results"] = _load_checkpoint(checkpoint_dir, "04_nulls")

    # Model objects (for downstream use / verification)
    for model_file in ["02_scaler.joblib", "02_pca.joblib", "05_gmm.joblib"]:
        model_path = checkpoint_dir / model_file
        if model_path.exists():
            loaded[model_file] = load_model(model_path)

    return loaded


def run_pipeline(args: argparse.Namespace) -> dict:
    """Execute the full trajectory TDA pipeline.

    Steps:
        1. Extract employment status + income bands
        2. Build trajectories
        3. Embed (n-grams + PCA/UMAP)
        4. Compute PH (witness + maxmin VR)
        5. Permutation tests
        6. Analysis (regimes, cycles, groups)

    Supports --skip-to N to resume from step N using saved checkpoints.
    """
    from trajectory_tda.analysis.cycle_detection import detect_cycles
    from trajectory_tda.analysis.regime_discovery import discover_regimes
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.topology.permutation_nulls import (
        permutation_test_trajectories,
    )
    from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph
    from trajectory_tda.utils.model_io import save_model

    t0 = time.time()
    checkpoint_dir = Path(args.checkpoint) if args.checkpoint else None
    skip_to = getattr(args, "skip_to", 1)
    results = {"args": vars(args)}

    # Load prior checkpoints if resuming
    loaded = {}
    if skip_to > 1 and checkpoint_dir:
        logger.info(f"Resuming from step {skip_to}, loading prior checkpoints...")
        loaded = _load_prior_steps(checkpoint_dir, skip_to)

    # Retrieve pre-loaded artefacts for skipped steps
    trajectories = loaded.get("trajectories")
    metadata = loaded.get("metadata")
    embeddings = loaded.get("embeddings")
    embed_info = loaded.get("embed_info")
    ph_result = None
    null_results = loaded.get("null_results", {})

    # ─── Step 1–2: Build trajectories ───
    if skip_to <= 2:
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
            # Save raw trajectory sequences for downstream reuse
            seq_path = checkpoint_dir / "01_trajectories_sequences.json"
            with open(seq_path, "w") as f:
                json.dump(trajectories, f)
            logger.info(f"Trajectory sequences saved: {seq_path}")
    else:
        results["n_trajectories"] = len(trajectories)
        logger.info(f"Step 1-2: Loaded {len(trajectories)} trajectories from checkpoint")

    # ─── Step 3: Embed ───
    if skip_to <= 3:
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

        results["embedding"] = {k: v for k, v in embed_info.items() if k != "fitted_models"}

        if checkpoint_dir:
            _save_checkpoint(
                {
                    "shape": list(embeddings.shape),
                    "info": {k: v for k, v in embed_info.items() if k != "fitted_models"},
                },
                checkpoint_dir,
                "02_embedding",
            )
            np.save(checkpoint_dir / "embeddings.npy", embeddings)

            # Save fitted transform objects for downstream reuse
            fitted_models = embed_info.get("fitted_models", {})
            if fitted_models.get("scaler") is not None:
                save_model(fitted_models["scaler"], checkpoint_dir / "02_scaler.joblib")
            if fitted_models.get("reducer") is not None:
                save_model(fitted_models["reducer"], checkpoint_dir / "02_pca.joblib")
    else:
        logger.info(f"Step 3: Loaded embeddings {embeddings.shape} from checkpoint")

    # ─── Step 4: Compute PH ───
    if skip_to <= 4:
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
                    # Save landmark indices for reproducibility
                    if hasattr(ph_obj, "landmark_indices") and ph_obj.landmark_indices is not None:
                        np.save(
                            checkpoint_dir / f"03_landmark_indices_{method_key}.npy",
                            ph_obj.landmark_indices,
                        )
            _save_checkpoint(raw_diagrams, checkpoint_dir, "03_ph_diagrams")
    else:
        logger.info("Step 4: Loaded PH results from checkpoint")

    # ─── Step 5: Permutation tests ───
    if skip_to <= 5:
        logger.info("=" * 60)
        logger.info("Step 5: Permutation tests")
        logger.info("=" * 60)

        # Parse embed args (needed for null re-embedding)
        pca_dim = None
        umap_dim = None
        if hasattr(args, "embed"):
            if args.embed.startswith("pca"):
                pca_dim = int(args.embed[3:])
            elif args.embed.startswith("umap"):
                umap_dim = int(args.embed[4:])

        null_types = (
            ["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"] if args.nulls == "all" else [args.nulls]
        )

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
    else:
        logger.info("Step 5: Loaded null results from checkpoint")

    # ─── Step 6: Analysis ───
    if skip_to <= 6:
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

        # Save fitted GMM for downstream reuse (Phase 6 etc.)
        if checkpoint_dir:
            gmm_obj = regimes.get("gmm_object")
            if gmm_obj is not None:
                save_model(gmm_obj, checkpoint_dir / "05_gmm.joblib")

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

        # Cycle detection (requires PH result from step 4)
        if ph_result is not None:
            cycles = detect_cycles(ph_result, embeddings, trajectories)
            results["cycles"] = {
                "n_persistent_loops": cycles["n_persistent_loops"],
                "h1_summary": cycles.get("h1_summary", {}),
            }
        else:
            logger.warning("Skipping cycle detection — PH result not available (skipped step 4)")
            results["cycles"] = {"n_persistent_loops": 0, "h1_summary": {}}

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
    if "regimes" in results:
        logger.info(f"  Trajectories: {len(trajectories)}, " f"Regimes: {results['regimes']['k_optimal']}")
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
        default="trajectory_tda/data",
        help="Root data directory (default: trajectory_tda/data/)",
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
        "--skip-to",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5, 6],
        help="Resume from this step, loading prior checkpoints (default: 1)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.skip_to > 1 and not args.checkpoint:
        parser.error("--skip-to requires --checkpoint to load prior results")

    run_pipeline(args)


if __name__ == "__main__":
    main()
