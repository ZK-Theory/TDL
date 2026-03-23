"""Build a combined BHPS + USoc trajectory checkpoint for zigzag persistence.

Runs only pipeline steps 1–3 (data loading, trajectory building, PCA embedding).
No permutation tests. Produces the ``01_trajectories.json`` and ``embeddings.npy``
artefacts required by :mod:`trajectory_tda.data.annual_partition`.

All three survey eras are included so the annual partition covers 1991–2022:
  - ``bhps_only``  :  individuals active 1991–2008 only
  - ``spanning``   :  individuals active in both BHPS and USoc (1991–2022)
  - ``usoc_only``  :  individuals active 2009–2022 only

Usage::

    python trajectory_tda/scripts/build_full_checkpoint.py \\
        --data-dir trajectory_tda/data \\
        --checkpoint results/trajectory_tda_full \\
        --min-years 10 \\
        --pca-dim 20

"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _save_json(data: object, path: Path) -> None:
    """Serialise ``data`` to JSON, converting numpy scalars."""

    def _convert(obj: object) -> object:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): _convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_convert(v) for v in obj]
        return obj

    with open(path, "w") as f:
        json.dump(_convert(data), f, indent=2)
    logger.info("Saved: %s", path)


def build_full_checkpoint(
    data_dir: str | Path,
    checkpoint_dir: str | Path,
    min_years: int,
    max_gap: int,
    pca_dim: int,
    tfidf: bool,
    income_threshold: float = 0.6,
) -> None:
    """Extract, build, embed, and checkpoint all BHPS + USoc trajectories.

    Args:
        data_dir: Root directory containing ``UKDA-5151-tab`` and
            ``UKDA-6614-tab`` subdirectories.
        checkpoint_dir: Output directory.  Created if absent.
        min_years: Minimum trajectory length to retain.
        max_gap: Maximum gap allowed in a trajectory (years).
        pca_dim: Number of PCA dimensions for the embedding.
        tfidf: Whether to apply TF-IDF weighting before PCA.
    """
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.utils.model_io import save_model

    data_dir = Path(data_dir)
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()

    # ── Step 1–2: Extract + build trajectories ──────────────────────────────
    logger.info("=" * 60)
    logger.info("Step 1-2: Building trajectories from BHPS + USoc")
    logger.info("data_dir: %s", data_dir)
    logger.info("=" * 60)

    trajectories, metadata = build_trajectories_from_raw(
        data_dir=data_dir,
        min_years=min_years,
        max_gap=max_gap,
        income_threshold=income_threshold,
    )

    logger.info("Total trajectories: %d", len(trajectories))

    if "survey_era" in metadata.columns:
        era_counts = metadata["survey_era"].value_counts()
        for era, count in era_counts.items():
            sub = metadata[metadata["survey_era"] == era]
            logger.info(
                "  %s: n=%d, mean_len=%.1f, range=%d–%d",
                era,
                count,
                sub["n_years"].mean(),
                sub["start_year"].min(),
                sub["end_year"].max(),
            )
    else:
        logger.info(
            "  start_year %d–%d, end_year %d–%d",
            metadata["start_year"].min(),
            metadata["start_year"].max(),
            metadata["end_year"].min(),
            metadata["end_year"].max(),
        )

    # Save trajectories checkpoint
    _save_json(
        {"metadata": metadata.to_dict(), "n": len(trajectories)},
        checkpoint_dir / "01_trajectories.json",
    )
    seq_path = checkpoint_dir / "01_trajectories_sequences.json"
    with open(seq_path, "w") as f:
        json.dump(trajectories, f)
    logger.info("Trajectory sequences saved: %s", seq_path)

    # ── Step 3: Embed ────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(
        "Step 3: Embedding %d trajectories (pca%d, tfidf=%s)",
        len(trajectories),
        pca_dim,
        tfidf,
    )
    logger.info("=" * 60)

    embeddings, embed_info = ngram_embed(
        trajectories,
        include_bigrams=True,
        tfidf=tfidf,
        pca_dim=pca_dim,
        umap_dim=None,
    )

    logger.info("Embeddings shape: %s", embeddings.shape)

    np.save(checkpoint_dir / "embeddings.npy", embeddings)
    logger.info("Saved embeddings.npy")

    _save_json(
        {
            "shape": list(embeddings.shape),
            "info": {k: v for k, v in embed_info.items() if k != "fitted_models"},
        },
        checkpoint_dir / "02_embedding.json",
    )

    fitted_models = embed_info.get("fitted_models", {})
    if fitted_models.get("scaler") is not None:
        save_model(fitted_models["scaler"], checkpoint_dir / "02_scaler.joblib")
    if fitted_models.get("reducer") is not None:
        save_model(fitted_models["reducer"], checkpoint_dir / "02_pca.joblib")

    # ── Summary ─────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info(
        "Checkpoint complete in %.1fs — %d trajectories, embeddings %s",
        elapsed,
        len(trajectories),
        embeddings.shape,
    )
    logger.info("Output: %s", checkpoint_dir)
    logger.info("=" * 60)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--data-dir",
        default="trajectory_tda/data",
        help="Root data directory containing UKDA-5151-tab and UKDA-6614-tab (default: %(default)s)",
    )
    p.add_argument(
        "--checkpoint",
        default="results/trajectory_tda_full",
        help="Output checkpoint directory (default: %(default)s)",
    )
    p.add_argument(
        "--min-years",
        type=int,
        default=10,
        help="Minimum trajectory length to retain (default: %(default)s)",
    )
    p.add_argument(
        "--max-gap",
        type=int,
        default=2,
        help="Maximum within-trajectory gap allowed in years (default: %(default)s)",
    )
    p.add_argument(
        "--pca-dim",
        type=int,
        default=20,
        help="PCA dimensionality for the embedding (default: %(default)s)",
    )
    p.add_argument(
        "--income-threshold",
        type=float,
        default=0.6,
        help="Low/mid income threshold as fraction of median (default: %(default)s)",
    )
    p.add_argument(
        "--no-tfidf",
        action="store_true",
        help="Disable TF-IDF weighting before PCA",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    build_full_checkpoint(
        data_dir=args.data_dir,
        checkpoint_dir=args.checkpoint,
        min_years=args.min_years,
        max_gap=args.max_gap,
        pca_dim=args.pca_dim,
        tfidf=not args.no_tfidf,
        income_threshold=args.income_threshold,
    )
