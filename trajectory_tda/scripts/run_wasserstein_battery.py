"""
Run Wasserstein-distance null tests on any pipeline checkpoint directory.

Loads embeddings + trajectories from a checkpoint, runs specified null types
with Wasserstein statistic, and writes results to a configurable JSON path.

Usage:
    # BHPS-era Wasserstein (order_shuffle + markov)
    python -m trajectory_tda.scripts.run_wasserstein_battery \
        --checkpoint-dir results/trajectory_tda_bhps \
        --null-types order_shuffle markov \
        --n-perms 100 --landmarks 2000

    # Integration: remaining battery (label_shuffle + markov order-2)
    python -m trajectory_tda.scripts.run_wasserstein_battery \
        --checkpoint-dir results/trajectory_tda_integration \
        --null-types label_shuffle markov \
        --markov-order 2 \
        --n-perms 100 --landmarks 2000

    # Full 5-model battery from scratch
    python -m trajectory_tda.scripts.run_wasserstein_battery \
        --checkpoint-dir results/trajectory_tda_integration \
        --null-types label_shuffle cohort_shuffle order_shuffle markov \
        --n-perms 100 --landmarks 2000

    # Post-audit archival run without touching the legacy JSON
    python -m trajectory_tda.scripts.run_wasserstein_battery \
        --checkpoint-dir results/trajectory_tda_integration \
        --output-name post_audit/04_nulls_wasserstein_w2_20260407.json \
        --null-types label_shuffle cohort_shuffle order_shuffle markov \
        --n-perms 100 --landmarks 2000
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


def _normalise_cohort_label(value: object) -> str:
    """Map missing cohort labels to a stable string bucket."""
    if value is None:
        return "unknown"
    try:
        if value != value:
            return "unknown"
    except Exception:
        pass
    return str(value)


def _convert_numpy(obj: object) -> object:
    """Recursively convert numpy types for JSON serialisation."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    return obj


def load_checkpoint(
    checkpoint_dir: Path,
) -> tuple[np.ndarray, list[list[str]], dict]:
    """Load embeddings and trajectories from a pipeline checkpoint.

    Args:
        checkpoint_dir: Path to results directory with embeddings.npy
            and 01_trajectories_sequences.json.

    Returns:
        Tuple of (embeddings, trajectories, embed_kwargs).
    """
    emb_path = checkpoint_dir / "embeddings.npy"
    seq_path = checkpoint_dir / "01_trajectories_sequences.json"
    info_path = checkpoint_dir / "02_embedding.json"

    if not emb_path.exists():
        raise FileNotFoundError(f"Embeddings not found: {emb_path}")
    if not seq_path.exists():
        raise FileNotFoundError(f"Sequences not found: {seq_path}")

    embeddings = np.load(emb_path)
    with open(seq_path) as f:
        trajectories = json.load(f)

    # Read embed kwargs from checkpoint metadata
    embed_kwargs: dict = {"pca_dim": 20, "include_bigrams": True, "tfidf": False}
    if info_path.exists():
        with open(info_path) as f:
            info = json.load(f)
        embed_info = info.get("info", {})
        embed_kwargs["pca_dim"] = embed_info.get("final_dims", 20)
        embed_kwargs["tfidf"] = embed_info.get("tfidf", False)
        if embed_info.get("n_bigram_dims", 0) > 0:
            embed_kwargs["include_bigrams"] = True

    logger.info(f"Loaded checkpoint: {embeddings.shape[0]} trajectories, " f"{embeddings.shape[1]}D embeddings")
    return embeddings, trajectories, embed_kwargs


def load_cohort_metadata(
    checkpoint_dir: Path,
) -> dict | None:
    """Try to load birth cohort metadata for cohort_shuffle null.

    Returns:
        Dict with 'cohort' key, or None if unavailable.
    """
    traj_path = checkpoint_dir / "01_trajectories.json"
    if not traj_path.exists():
        return None

    with open(traj_path) as f:
        traj_data = json.load(f)

    # Check if metadata contains birth_cohort info
    meta = traj_data.get("metadata", {})
    cohort = meta.get("birth_cohort", {})
    if not cohort:
        cohort = meta.get("cohort", {})
    if not cohort and meta.get("pidp"):
        try:
            from trajectory_tda.data.covariate_extractor import attach_birth_cohort_metadata

            n = traj_data.get("n")
            checkpoint_meta: dict[str, list] = {}
            for key, values in meta.items():
                if isinstance(values, dict):
                    if n is None:
                        ordered_keys = sorted(values, key=int)
                        checkpoint_meta[key] = [values[idx] for idx in ordered_keys]
                    else:
                        checkpoint_meta[key] = [values.get(str(i)) for i in range(n)]
                else:
                    checkpoint_meta[key] = list(values)

            metadata_df = pd.DataFrame(checkpoint_meta)
            metadata_df = attach_birth_cohort_metadata(
                metadata_df,
                data_dir=Path(__file__).resolve().parents[1] / "data",
            )
            if "birth_cohort" in metadata_df.columns and metadata_df["birth_cohort"].notna().any():
                cohort = metadata_df["birth_cohort"].tolist()
                logger.info("Recovered birth_cohort metadata from raw covariates for cohort_shuffle")
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning("Could not backfill birth_cohort metadata: %s", exc)
    if not cohort:
        logger.warning("No birth_cohort metadata found — cohort_shuffle will fall " "back to label_shuffle")
        return None

    # Convert to array aligned with trajectory indices
    if isinstance(cohort, dict):
        n = traj_data.get("n", len(cohort))
        cohort_arr = [_normalise_cohort_label(cohort.get(str(i), "unknown")) for i in range(n)]
    else:
        cohort_arr = [_normalise_cohort_label(value) for value in cohort]

    return {"cohort": np.array(cohort_arr, dtype=object)}


def run_battery(
    checkpoint_dir: Path,
    null_types: list[str],
    n_permutations: int = 100,
    n_landmarks: int = 2000,
    max_dim: int = 1,
    markov_order: int = 1,
    n_jobs: int = 1,
    seed: int = 42,
    output_name: str = "04_nulls_wasserstein.json",
    overwrite_output: bool = False,
) -> dict:
    """Run Wasserstein null tests and merge with existing results.

    Args:
        checkpoint_dir: Path to results checkpoint directory.
        null_types: List of null types to run.
        n_permutations: Number of permutations per null type.
        n_landmarks: Landmark count for VR persistence.
        max_dim: Maximum homology dimension.
        markov_order: Markov chain order (1 or 2).
        n_jobs: Parallelism (-1 = all cores, 1 = serial).
        seed: Random seed.
        output_name: Output JSON path, relative to checkpoint_dir unless absolute.
        overwrite_output: If true, ignore any existing output file and rerun all keys.

    Returns:
        Merged results dict.
    """
    from trajectory_tda.topology.permutation_nulls import (
        permutation_test_trajectories,
    )

    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    metadata = load_cohort_metadata(checkpoint_dir)

    out_path = Path(output_name)
    if not out_path.is_absolute():
        out_path = checkpoint_dir / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results to merge
    existing: dict = {}
    if out_path.exists() and not overwrite_output:
        with open(out_path) as f:
            existing = json.load(f)
        logger.info(f"Loaded existing results with keys: {list(existing.keys())}")
    elif out_path.exists() and overwrite_output:
        logger.info(f"Overwriting existing output: {out_path}")
        out_path.unlink()

    for null_type in null_types:
        # Determine result key (markov order-2 stored under "markov2")
        result_key = null_type
        current_markov_order = 1
        if null_type == "markov" and markov_order == 2:
            result_key = "markov2"
            current_markov_order = 2
        elif null_type == "markov":
            current_markov_order = 1

        if result_key in existing:
            logger.info(f"Skipping {result_key} — already in results")
            continue

        logger.info(f"\n{'=' * 60}")
        logger.info(
            f"Wasserstein null: {null_type} "
            f"(markov_order={current_markov_order if null_type == 'markov' else 'n/a'})"
        )
        logger.info(f"{'=' * 60}")

        t0 = time.time()
        try:
            result = permutation_test_trajectories(
                embeddings=embeddings,
                trajectories=trajectories,
                metadata=metadata,
                null_type=null_type,
                n_permutations=n_permutations,
                max_dim=max_dim,
                n_landmarks=n_landmarks,
                statistic="wasserstein",
                markov_order=current_markov_order,
                n_jobs=n_jobs,
                seed=seed,
                embed_kwargs=embed_kwargs,
            )
            elapsed = time.time() - t0
            result["elapsed_seconds"] = elapsed
            existing[result_key] = result

            logger.info(f"  Completed in {elapsed:.1f}s")
            for dim in range(max_dim + 1):
                key = f"H{dim}"
                if key in result:
                    r = result[key]
                    logger.info(
                        f"  {key}: W(obs,null)={r['mean_wasserstein_obs_null']:.3f}, "
                        f"W(null,null)={r['mean_wasserstein_null_null']:.3f}, "
                        f"p={r['p_value']:.4f}"
                    )

            # Save after each null type (incremental)
            with open(out_path, "w") as f:
                json.dump(_convert_numpy(existing), f, indent=2)
            logger.info(f"  Saved incremental results to {out_path}")

        except Exception:
            logger.exception(f"  Failed: {null_type}")
            existing[result_key] = {"error": "failed", "null_type": null_type}

    return existing


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Wasserstein null battery on pipeline checkpoint")
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        required=True,
        help="Path to results checkpoint directory",
    )
    parser.add_argument(
        "--null-types",
        nargs="+",
        default=["order_shuffle", "markov"],
        help="Null types: label_shuffle, cohort_shuffle, order_shuffle, markov",
    )
    parser.add_argument("--n-perms", type=int, default=100)
    parser.add_argument("--landmarks", type=int, default=2000)
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument("--markov-order", type=int, default=1)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-name",
        type=str,
        default="04_nulls_wasserstein.json",
        help="Output JSON path, relative to checkpoint-dir unless absolute.",
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Rerun all requested keys even if the output file already exists.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    results = run_battery(
        checkpoint_dir=Path(args.checkpoint_dir),
        null_types=args.null_types,
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
        max_dim=args.max_dim,
        markov_order=args.markov_order,
        n_jobs=args.n_jobs,
        seed=args.seed,
        output_name=args.output_name,
        overwrite_output=args.overwrite_output,
    )

    logger.info(f"\nComplete. Result keys: {list(results.keys())}")
    for key, val in results.items():
        if isinstance(val, dict) and "H0" in val:
            h0 = val["H0"]
            logger.info(f"  {key}: H0 p={h0['p_value']:.4f} " f"({'*' if h0.get('significant_at_005') else 'ns'})")


if __name__ == "__main__":
    main()
