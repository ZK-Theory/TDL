"""
Rerun permutation tests at n=500 for BHPS and spanning results.
Uses pre-computed embeddings. Only reruns the null permutations.

Run: python trajectory_tda/scripts/bhps_rerun_nulls.py
"""

import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json
import logging
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

N_PERMS = 500
EMBED_KWARGS = {"include_bigrams": True, "tfidf": False, "pca_dim": 20}


def convert(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert(v) for v in obj]
    return obj


def run_nulls(name, embeddings, trajectories, checkpoint_dir, n_landmarks, null_types):
    """Run permutation tests and save results."""
    logger.info(f"{'=' * 60}")
    logger.info(f"Running {name} nulls: {null_types}, n={N_PERMS}, L={n_landmarks}")
    logger.info(f"{'=' * 60}")

    null_results = {}
    for null_type in null_types:
        logger.info(f"  {null_type}...")
        t1 = time.time()
        try:
            nr = permutation_test_trajectories(
                embeddings=embeddings,
                trajectories=trajectories,
                null_type=null_type,
                n_permutations=N_PERMS,
                max_dim=1,
                n_landmarks=n_landmarks,
                statistic="total_persistence",
                markov_order=1,
                embed_kwargs=EMBED_KWARGS,
            )
            null_results[null_type] = nr
            elapsed = time.time() - t1
            for dim in ["H0", "H1"]:
                if dim in nr:
                    logger.info(
                        f"    {null_type} {dim}: p={nr[dim]['p_value']:.4f} "
                        f"(obs={nr[dim]['observed']:.1f}, null_mean={nr[dim]['null_mean']:.1f})"
                    )
            logger.info(f"    Elapsed: {elapsed:.1f}s")
        except Exception as e:
            logger.warning(f"    {null_type} FAILED: {e}")
            null_results[null_type] = {"error": str(e)}

    # Save
    with open(checkpoint_dir / "04_nulls.json", "w") as f:
        json.dump(convert(null_results), f, indent=2)

    # Update results_full.json
    results_path = checkpoint_dir / "results_full.json"
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        pvals = {}
        for nt, r in null_results.items():
            if "error" not in r:
                for dim in ["H0", "H1"]:
                    if dim in r:
                        pvals[f"{nt}_{dim}"] = r[dim].get("p_value")
        results["null_p_values"] = pvals
        results["n_permutations"] = N_PERMS
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

    return null_results


if __name__ == "__main__":
    t0 = time.time()

    # ─── BHPS nulls ───
    bhps_dir = Path("results/trajectory_tda_bhps")
    if (bhps_dir / "embeddings.npy").exists():
        logger.info("Loading BHPS embeddings and trajectories...")
        bhps_emb = np.load(bhps_dir / "embeddings.npy")
        with open(bhps_dir / "01_trajectories_sequences.json") as f:
            bhps_trajs = json.load(f)
        logger.info(f"  BHPS: {len(bhps_trajs)} trajectories, {bhps_emb.shape}")

        run_nulls(
            "BHPS",
            bhps_emb,
            bhps_trajs,
            bhps_dir,
            n_landmarks=5000,
            null_types=["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"],
        )

    # ─── Spanning nulls ───
    span_dir = Path("results/trajectory_tda_spanning")
    if (span_dir / "embeddings.npy").exists():
        logger.info("\nLoading spanning embeddings and trajectories...")
        span_emb = np.load(span_dir / "embeddings.npy")
        with open(span_dir / "01_trajectories_sequences.json") as f:
            span_trajs = json.load(f)
        logger.info(f"  Spanning: {len(span_trajs)} trajectories, {span_emb.shape}")

        run_nulls(
            "Spanning",
            span_emb,
            span_trajs,
            span_dir,
            n_landmarks=5000,
            null_types=["label_shuffle", "order_shuffle", "markov"],
        )

    elapsed = time.time() - t0
    logger.info(f"\nAll nulls complete in {elapsed:.1f}s ({elapsed / 60:.1f} min)")
