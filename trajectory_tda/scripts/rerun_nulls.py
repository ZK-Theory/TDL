"""
Standalone null model rerun script.

Loads existing embeddings from checkpoint, rebuilds trajectories from raw data,
then runs null models at higher permutation counts:
  - order_shuffle + markov(1): n=500
  - markov(2): n=500
  - label_shuffle + cohort_shuffle: n=100

Saves results alongside existing checkpoints without overwriting originals.

Usage:
    python -m trajectory_tda.scripts.rerun_nulls \
        --results-dir results/trajectory_tda_integration \
        --data-dir trajectory_tda/data
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _save_checkpoint(data: dict, path: Path, name: str) -> None:
    """Save checkpoint data to JSON."""
    path.mkdir(parents=True, exist_ok=True)
    fpath = path / f"{name}.json"

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


def main():
    parser = argparse.ArgumentParser(description="Rerun null models at higher permutation counts")
    parser.add_argument("--results-dir", type=str, default="results/trajectory_tda_integration")
    parser.add_argument("--data-dir", type=str, default="trajectory_tda/data")
    parser.add_argument("--n-perms-main", type=int, default=500)
    parser.add_argument("--n-perms-confirm", type=int, default=100)
    parser.add_argument("--landmarks", type=int, default=2500)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    results_dir = Path(args.results_dir)

    # ─── Load existing embeddings ───
    logger.info("Loading embeddings from checkpoint")
    embeddings = np.load(results_dir / "embeddings.npy")
    logger.info(f"Embeddings: {embeddings.shape}")

    # ─── Rebuild trajectories ───
    logger.info("Rebuilding trajectories from raw data")
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw

    trajectories, metadata = build_trajectories_from_raw(
        data_dir=args.data_dir,
        min_years=10,
        max_gap=2,
        income_threshold=0.6,
    )
    logger.info(f"Built {len(trajectories)} trajectories")

    if len(trajectories) != embeddings.shape[0]:
        logger.warning(
            f"Trajectory count ({len(trajectories)}) != embedding count ({embeddings.shape[0]}). "
            "Results may not align. Proceeding anyway."
        )

    # ─── Embedding kwargs (must match original) ───
    embed_kwargs = {
        "include_bigrams": True,
        "tfidf": False,
        "pca_dim": 20,
        "umap_dim": None,
    }

    from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

    # ─── Also save raw persistence diagrams if not already saved ───
    diagrams_path = results_dir / "03_ph_diagrams.json"
    if not diagrams_path.exists():
        logger.info("Computing and saving raw persistence diagrams")
        from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

        ph_result = compute_trajectory_ph(
            embeddings,
            max_dim=1,
            n_landmarks=args.landmarks,
            method="maxmin_vr",
            validate=False,
        )
        raw_diagrams = {}
        for method_key in ["witness", "maxmin_vr"]:
            if method_key in ph_result:
                ph_obj = ph_result[method_key]
                raw_diagrams[method_key] = {str(dim): dgm.tolist() for dim, dgm in ph_obj.dgms.items()}
        _save_checkpoint(raw_diagrams, results_dir, "03_ph_diagrams")
    else:
        logger.info("Raw persistence diagrams already exist, skipping")

    # ─── Run main nulls at n=500 ───
    t0 = time.time()

    # Order shuffle (n=500)
    logger.info(f"Running order_shuffle at n={args.n_perms_main}")
    order_result = permutation_test_trajectories(
        embeddings=embeddings,
        trajectories=trajectories,
        null_type="order_shuffle",
        n_permutations=args.n_perms_main,
        max_dim=1,
        n_landmarks=args.landmarks,
        statistic="total_persistence",
        embed_kwargs=embed_kwargs,
    )

    # Markov order 1 (n=500)
    logger.info(f"Running markov(order=1) at n={args.n_perms_main}")
    markov1_result = permutation_test_trajectories(
        embeddings=embeddings,
        trajectories=trajectories,
        null_type="markov",
        n_permutations=args.n_perms_main,
        max_dim=1,
        n_landmarks=args.landmarks,
        statistic="total_persistence",
        markov_order=1,
        embed_kwargs=embed_kwargs,
    )

    # Markov order 2 (n=500)
    logger.info(f"Running markov(order=2) at n={args.n_perms_main}")
    markov2_result = permutation_test_trajectories(
        embeddings=embeddings,
        trajectories=trajectories,
        null_type="markov",
        n_permutations=args.n_perms_main,
        max_dim=1,
        n_landmarks=args.landmarks,
        statistic="total_persistence",
        markov_order=2,
        embed_kwargs=embed_kwargs,
    )

    # ─── Run confirmation nulls at n=100 ───
    logger.info(f"Running label_shuffle at n={args.n_perms_confirm}")
    label_result = permutation_test_trajectories(
        embeddings=embeddings,
        null_type="label_shuffle",
        n_permutations=args.n_perms_confirm,
        max_dim=1,
        n_landmarks=args.landmarks,
        statistic="total_persistence",
    )

    logger.info(f"Running cohort_shuffle at n={args.n_perms_confirm}")
    cohort_result = permutation_test_trajectories(
        embeddings=embeddings,
        metadata={"cohort": metadata.get("start_year", metadata.get("cohort", None))},
        null_type="cohort_shuffle",
        n_permutations=args.n_perms_confirm,
        max_dim=1,
        n_landmarks=args.landmarks,
        statistic="total_persistence",
    )

    elapsed = time.time() - t0
    logger.info(f"All null models complete in {elapsed:.1f}s")

    # ─── Save results ───
    # Main nulls (overwrites 04_nulls.json with n=500 results)
    null_results = {
        "label_shuffle": label_result,
        "cohort_shuffle": cohort_result,
        "order_shuffle": order_result,
        "markov": markov1_result,
    }
    _save_checkpoint(null_results, results_dir, "04_nulls")
    logger.info("Saved 04_nulls.json (updated with n=500)")

    # Markov order-2 (separate file)
    _save_checkpoint({"markov": markov2_result}, results_dir, "04_nulls_markov2")
    logger.info("Saved 04_nulls_markov2.json")

    # ─── Summary ───
    logger.info("=" * 60)
    logger.info("MARKOV MEMORY LADDER")
    logger.info("=" * 60)
    for name, result in [
        ("Order Shuffle", order_result),
        ("Markov (order 1)", markov1_result),
        ("Markov (order 2)", markov2_result),
    ]:
        h0 = result.get("H0", {})
        h1 = result.get("H1", {})
        logger.info(f"  {name:20s}: H0 p={h0.get('p_value', '?'):.4f}  " f"H1 p={h1.get('p_value', '?'):.4f}")
    logger.info(f"  Label Shuffle:       H0 p={label_result.get('H0', {}).get('p_value', '?'):.4f}")
    logger.info(f"  Cohort Shuffle:      H0 p={cohort_result.get('H0', {}).get('p_value', '?'):.4f}")
    logger.info("=" * 60)

    # ─── Also update analysis with exemplars + gmm_labels if missing ───
    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)

    if "regime_exemplars" not in analysis or "gmm_labels" not in analysis:
        logger.info("Adding regime exemplars and GMM labels to analysis checkpoint")
        from trajectory_tda.analysis.regime_discovery import discover_regimes
        from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

        # Re-run regime discovery to get labels
        ph_result_for_regimes = compute_trajectory_ph(
            embeddings,
            max_dim=1,
            n_landmarks=args.landmarks,
            method="maxmin_vr",
            validate=False,
        )
        regimes = discover_regimes(embeddings, trajectories, ph_result=ph_result_for_regimes)

        gmm_labels = regimes["gmm_labels"]
        regime_exemplars = {}
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

        analysis["regime_exemplars"] = regime_exemplars
        analysis["gmm_labels"] = gmm_labels.tolist()
        _save_checkpoint(analysis, results_dir, "05_analysis")
        logger.info("Updated 05_analysis.json with exemplars and labels")


if __name__ == "__main__":
    main()
