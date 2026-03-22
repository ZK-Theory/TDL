"""
Targeted null model runner for individual nulls at L=5000.

Run one null at a time so progress is saved immediately and
terminals can be killed without losing completed work.

Usage:
    python -m trajectory_tda.scripts.run_missing_nulls_L5000 --null-type label_shuffle
    python -m trajectory_tda.scripts.run_missing_nulls_L5000 --null-type cohort_shuffle
    python -m trajectory_tda.scripts.run_missing_nulls_L5000 --null-type markov2
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

RESULTS_DIR = Path("results/trajectory_tda_integration")
ROBUSTNESS_DIR = Path("results/trajectory_tda_robustness/landmark_sensitivity")
DATA_DIR = "trajectory_tda/data"
N_LANDMARKS = 5000
N_PERMS = 200


def _save(data: dict, path: Path, name: str) -> None:
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
    logger.info(f"Saved: {fpath}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--null-type",
        required=True,
        choices=["label_shuffle", "cohort_shuffle", "markov2"],
    )
    parser.add_argument("--n-perms", type=int, default=N_PERMS)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    t0 = time.time()

    # ─── Load existing embeddings ───
    embeddings = np.load(RESULTS_DIR / "embeddings.npy")
    logger.info(f"Embeddings: {embeddings.shape}")

    trajectories = None
    metadata = {}

    # Load saved trajectories and metadata (matches the 27,280 embeddings)
    if args.null_type in ("markov2", "cohort_shuffle"):
        import json as _json

        seq_path = RESULTS_DIR / "01_trajectories_sequences.json"
        meta_path = RESULTS_DIR / "01_trajectories.json"
        logger.info(f"Loading saved trajectories from {seq_path}")
        with open(seq_path) as f:
            trajectories = _json.load(f)
        with open(meta_path) as f:
            saved = _json.load(f)
        metadata = saved["metadata"]
        logger.info(
            f"Loaded {len(trajectories)} trajectories, metadata keys: {list(metadata.keys())}"
        )
        if len(trajectories) != embeddings.shape[0]:
            raise ValueError(
                f"Trajectory count ({len(trajectories)}) != embedding count ({embeddings.shape[0]})"
            )

    embed_kwargs = {
        "include_bigrams": True,
        "tfidf": False,
        "pca_dim": 20,
        "umap_dim": None,
    }

    from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

    null_type = args.null_type
    n_perms = args.n_perms

    if null_type == "label_shuffle":
        logger.info(f"=== label_shuffle at n={n_perms} ===")
        result = permutation_test_trajectories(
            embeddings=embeddings,
            null_type="label_shuffle",
            n_permutations=n_perms,
            max_dim=1,
            n_landmarks=N_LANDMARKS,
            statistic="total_persistence",
            n_jobs=1,
        )
        _save(result, ROBUSTNESS_DIR, "nulls_label_shuffle_L5000")

    elif null_type == "cohort_shuffle":
        cohort_raw = metadata.get("start_year")
        if cohort_raw is None:
            raise ValueError("No start_year in saved metadata")
        # Saved metadata is a dict (from pandas to_dict); extract values in order
        if isinstance(cohort_raw, dict):
            cohort_arr = np.array([cohort_raw[str(i)] for i in range(len(cohort_raw))])
        else:
            cohort_arr = np.array(cohort_raw)
        logger.info(
            f"Cohort array: {len(cohort_arr)} entries, {len(np.unique(cohort_arr))} unique cohorts"
        )
        logger.info(f"=== cohort_shuffle at n={n_perms} ===")
        result = permutation_test_trajectories(
            embeddings=embeddings,
            metadata={"cohort": cohort_arr},
            null_type="cohort_shuffle",
            n_permutations=n_perms,
            max_dim=1,
            n_landmarks=N_LANDMARKS,
            statistic="total_persistence",
            n_jobs=1,
        )
        _save(result, ROBUSTNESS_DIR, "nulls_cohort_shuffle_L5000")

    elif null_type == "markov2":
        logger.info(f"=== markov(order=2) at n={n_perms} ===")
        result = permutation_test_trajectories(
            embeddings=embeddings,
            trajectories=trajectories,
            null_type="markov",
            n_permutations=n_perms,
            max_dim=1,
            n_landmarks=N_LANDMARKS,
            statistic="total_persistence",
            markov_order=2,
            embed_kwargs=embed_kwargs,
            n_jobs=1,
        )
        _save(result, ROBUSTNESS_DIR, "nulls_markov2_L5000")

    elapsed = time.time() - t0

    h0 = result["H0"]
    h1 = result["H1"]
    logger.info("=" * 60)
    logger.info(
        f"{null_type}: "
        f"H0 obs={h0['observed']:.1f} null={h0['null_mean']:.1f}±{h0['null_std']:.1f} p={h0['p_value']:.4f} | "
        f"H1 obs={h1['observed']:.1f} null={h1['null_mean']:.1f}±{h1['null_std']:.1f} p={h1['p_value']:.4f}"
    )
    logger.info(f"Completed in {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
