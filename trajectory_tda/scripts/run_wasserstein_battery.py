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
import os
import time
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _metadata_fallback(key: str) -> object:
    """Provide explicit fallbacks for sparse checkpoint metadata."""
    if key in {"cohort", "birth_cohort"}:
        return "unknown"
    return np.nan


def _resolve_trajectory_data_dir(explicit_data_dir: str | Path | None = None) -> Path:
    """Resolve the raw trajectory data directory from CLI, env, or package data."""
    if explicit_data_dir is not None:
        return Path(explicit_data_dir)

    env_data_dir = os.environ.get("TRAJECTORY_TDA_DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir)

    return Path(str(files("trajectory_tda").joinpath("data")))


def _checkpoint_meta_column(key: str, values: object, n_rows: int | None) -> list[object]:
    """Convert checkpoint metadata into a length-safe column for DataFrame rebuild."""
    if isinstance(values, dict):
        values_dict = cast(dict[object, object], values)
        indexed_values: dict[int, object] = {}
        for raw_key, raw_value in values_dict.items():
            try:
                indexed_values[int(raw_key)] = raw_value
            except (TypeError, ValueError):
                logger.warning(
                    "Skipping non-numeric metadata index %r in %s",
                    raw_key,
                    key,
                )

        if not indexed_values:
            logger.warning("Skipping metadata field %s: no integer-indexed entries", key)
            return []

        if n_rows is None:
            return [indexed_values[index] for index in sorted(indexed_values)]

        fallback = _metadata_fallback(key)
        ordered_values = [indexed_values.get(index, fallback) for index in range(n_rows)]
        missing_count = sum(index not in indexed_values for index in range(n_rows))
        if missing_count:
            logger.warning(
                "Metadata field %s missing %d/%d indexed entries; using explicit fallback values",
                key,
                missing_count,
                n_rows,
            )
        return ordered_values

    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        logger.warning(
            "Skipping metadata field %s: unsupported metadata type %s",
            key,
            type(values).__name__,
        )
        return []

    sequence = list(cast(Iterable[Any], values))
    if n_rows is None:
        return sequence

    fallback = _metadata_fallback(key)
    if len(sequence) < n_rows:
        logger.warning(
            "Metadata field %s shorter than checkpoint length (%d < %d); padding with fallback values",
            key,
            len(sequence),
            n_rows,
        )
        return sequence + [fallback] * (n_rows - len(sequence))
    if len(sequence) > n_rows:
        logger.warning(
            "Metadata field %s longer than checkpoint length (%d > %d); truncating extras",
            key,
            len(sequence),
            n_rows,
        )
        return sequence[:n_rows]
    return sequence


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
) -> tuple[np.ndarray, list[list[str]], dict[str, Any]]:
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
    embed_kwargs: dict[str, Any] = {
        "pca_dim": 20,
        "include_bigrams": True,
        "tfidf": False,
    }
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


def load_regime_labels(analysis_json_path: Path) -> np.ndarray:
    """Load per-trajectory regime labels from a pipeline analysis JSON.

    Reads ``gmm_labels`` from the file produced by the main pipeline.  This is
    the authoritative source for regime assignments — it avoids reloading the
    saved GMM object and the sklearn version-mismatch risk that caused the
    original stratified-Markov run to collapse to 2 regimes.

    Args:
        analysis_json_path: Path to ``05_analysis.json`` (or equivalent).

    Returns:
        Integer array of shape (N,) — one regime label per trajectory.

    Raises:
        KeyError: If ``gmm_labels`` is absent from the JSON.
    """
    with open(analysis_json_path) as f:
        analysis = json.load(f)
    labels = analysis.get("gmm_labels")
    if labels is None:
        raise KeyError(f"No 'gmm_labels' key in {analysis_json_path}")
    arr = np.array(labels, dtype=int)
    logger.info(
        "Loaded %d regime labels (%d unique regimes) from %s",
        len(arr),
        len(np.unique(arr)),
        analysis_json_path,
    )
    return arr


def load_cohort_metadata(
    checkpoint_dir: Path,
    data_dir: str | Path | None = None,
) -> dict[str, Any] | None:
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
            from trajectory_tda.data.covariate_extractor import (
                attach_birth_cohort_metadata,
            )

            n = traj_data.get("n")
            checkpoint_meta: dict[str, list[Any]] = {}
            for key, values in meta.items():
                column_values = _checkpoint_meta_column(key, values, n)
                if column_values:
                    checkpoint_meta[key] = column_values

            metadata_df = pd.DataFrame(checkpoint_meta)
            metadata_df = attach_birth_cohort_metadata(
                metadata_df,
                data_dir=_resolve_trajectory_data_dir(data_dir),
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
    data_dir: str | Path | None = None,
    regime_labels_path: str | Path | None = None,
) -> dict[str, Any]:
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
        data_dir: Optional raw data directory override for cohort metadata recovery.
        regime_labels_path: Path to a pipeline ``05_analysis.json`` containing
            ``gmm_labels``.  Required when ``stratified_markov1`` is in
            ``null_types``.

    Returns:
        Merged results dict.
    """
    from trajectory_tda.topology.permutation_nulls import (
        permutation_test_trajectories,
    )

    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    metadata = load_cohort_metadata(checkpoint_dir, data_dir=data_dir)

    # Pre-load regime labels once if needed — avoids repeated JSON reads per null
    _regime_labels: np.ndarray | None = None
    if "stratified_markov1" in null_types:
        if regime_labels_path is None:
            raise ValueError(
                "null_type='stratified_markov1' requires --regime-labels-path "
                "pointing to a pipeline 05_analysis.json with 'gmm_labels'. "
                "For USoc: results/trajectory_tda_integration/05_analysis.json. "
                "For BHPS: results/trajectory_tda_bhps/05_analysis.json."
            )
        _regime_labels = load_regime_labels(Path(regime_labels_path))

    out_path = Path(output_name)
    if not out_path.is_absolute():
        out_path = checkpoint_dir / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results to merge
    existing: dict[str, Any] = {}
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
            # For stratified_markov1, inject regime labels into a fresh metadata dict
            call_metadata: dict[str, Any] | None = metadata
            if null_type == "stratified_markov1" and _regime_labels is not None:
                call_metadata = dict(metadata) if metadata else {}
                call_metadata["regime_labels"] = _regime_labels

            result = permutation_test_trajectories(
                embeddings=embeddings,
                trajectories=trajectories,
                metadata=call_metadata,
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
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help=(
            "Optional raw data directory override for cohort metadata recovery. "
            "Defaults to TRAJECTORY_TDA_DATA_DIR or the packaged trajectory_tda/data directory."
        ),
    )
    parser.add_argument(
        "--regime-labels-path",
        type=str,
        default=None,
        help=(
            "Path to a pipeline 05_analysis.json containing 'gmm_labels'. "
            "Required when --null-types includes stratified_markov1. "
            "USoc: results/trajectory_tda_integration/05_analysis.json. "
            "BHPS: results/trajectory_tda_bhps/05_analysis.json."
        ),
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
        data_dir=args.data_dir,
        regime_labels_path=args.regime_labels_path,
    )

    logger.info(f"\nComplete. Result keys: {list(results.keys())}")
    for key, val in results.items():
        if isinstance(val, dict) and "H0" in val:
            h0 = val["H0"]
            logger.info(f"  {key}: H0 p={h0['p_value']:.4f} " f"({'*' if h0.get('significant_at_005') else 'ns'})")


if __name__ == "__main__":
    main()
