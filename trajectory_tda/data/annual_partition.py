"""Annual partition of trajectory embeddings by calendar year.

Builds the ``embeddings_by_year`` dict required by
:func:`~trajectory_tda.topology.zigzag.create_annual_snapshots`. For each
calendar year, selects the rows from the pre-computed full-sample PCA
embedding whose trajectories were active in that year (i.e. the
individual's career span ``[start_year, end_year]`` covers the year).

Because the embeddings are derived from frozen full-sample PCA loadings,
filtering rows is sufficient to satisfy the "same coordinate system per
year" requirement — no per-year re-fitting is needed.

References:
    Results/trajectories metadata expected at
    ``<checkpoint_dir>/01_trajectories.json`` (key ``metadata``) and
    embeddings at ``<checkpoint_dir>/embeddings.npy``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def build_embeddings_by_year(
    trajectories_json_path: Path,
    embeddings_npy_path: Path,
    year_start: int = 1991,
    year_end: int = 2023,
    min_individuals: int = 50,
) -> dict[int, NDArray[np.float64]]:
    """Partition frozen PCA embeddings by calendar year of activity.

    For each year Y in ``[year_start, year_end]``, return the rows from
    ``embeddings_npy_path`` corresponding to individuals whose recorded
    career span covers Y (i.e. ``start_year <= Y <= end_year``).

    The embeddings must already be computed from frozen full-sample PCA
    loadings so that all annual sub-clouds share the same coordinate
    system. Years with fewer than ``min_individuals`` active individuals
    are included but trigger a warning; the caller may choose to exclude
    them.

    Args:
        trajectories_json_path: Path to ``01_trajectories.json`` as
            written by ``run_pipeline.py``. Must contain a ``metadata``
            key with per-trajectory ``start_year`` and ``end_year`` fields
            and row order matching ``embeddings_npy_path``.
        embeddings_npy_path: Path to ``embeddings.npy`` (shape
            ``(n_trajectories, n_dims)``), row-aligned with the metadata.
        year_start: First calendar year to include (inclusive).
        year_end: Last calendar year to include (inclusive).
        min_individuals: Minimum active individuals required before a
            warning is logged. The year is still included in the output.

    Returns:
        Dict mapping calendar year → embedding sub-matrix of shape
        ``(n_active, n_dims)`` as a contiguous ``float64`` array.

    Raises:
        FileNotFoundError: If either input file does not exist.
        ValueError: If the metadata row count does not match the
            embedding row count, or if required metadata columns are
            missing.
    """
    trajectories_json_path = Path(trajectories_json_path)
    embeddings_npy_path = Path(embeddings_npy_path)

    if not trajectories_json_path.exists():
        raise FileNotFoundError(f"Trajectories JSON not found: {trajectories_json_path}")
    if not embeddings_npy_path.exists():
        raise FileNotFoundError(f"Embeddings not found: {embeddings_npy_path}")

    logger.info("Loading metadata from %s", trajectories_json_path)
    with open(trajectories_json_path) as f:
        cp = json.load(f)

    raw_meta = cp.get("metadata")
    if raw_meta is None:
        raise ValueError("'metadata' key missing from trajectories JSON")

    metadata = pd.DataFrame(raw_meta)

    required_cols = {"start_year", "end_year"}
    missing = required_cols - set(metadata.columns)
    if missing:
        raise ValueError(f"Metadata missing required columns: {missing}")

    logger.info("Loading embeddings from %s", embeddings_npy_path)
    embeddings = np.load(embeddings_npy_path).astype(np.float64)

    if len(metadata) != len(embeddings):
        raise ValueError(
            f"Metadata row count ({len(metadata)}) does not match " f"embedding row count ({len(embeddings)})"
        )

    start_years = metadata["start_year"].to_numpy()
    end_years = metadata["end_year"].to_numpy()

    embeddings_by_year: dict[int, NDArray[np.float64]] = {}
    for year in range(year_start, year_end + 1):
        mask = (start_years <= year) & (year <= end_years)
        n_active = int(mask.sum())

        if n_active == 0:
            logger.warning("Year %d: 0 active individuals — skipping", year)
            continue

        if n_active < min_individuals:
            logger.warning(
                "Year %d: only %d active individuals (< min_individuals=%d). " "PH results may be noise-dominated.",
                year,
                n_active,
                min_individuals,
            )

        embeddings_by_year[year] = np.ascontiguousarray(embeddings[mask])
        logger.debug("Year %d: %d active individuals", year, n_active)

    years_found = sorted(embeddings_by_year)
    if years_found:
        counts = [len(v) for v in embeddings_by_year.values()]
        logger.info(
            "Annual partition complete: %d years (%d–%d), median n=%d, min n=%d, max n=%d",
            len(years_found),
            years_found[0],
            years_found[-1],
            int(np.median(counts)),
            min(counts),
            max(counts),
        )
    else:
        logger.warning(
            "Annual partition complete: 0 years found in range %d–%d",
            year_start,
            year_end,
        )

    return embeddings_by_year


def annual_counts(embeddings_by_year: dict[int, NDArray[np.float64]]) -> dict[str, int]:
    """Return a year → n_individuals mapping for logging / checkpointing.

    Args:
        embeddings_by_year: Dict as returned by :func:`build_embeddings_by_year`.

    Returns:
        Dict mapping str(year) → n_individuals (JSON-serialisable).
    """
    return {str(year): len(arr) for year, arr in sorted(embeddings_by_year.items())}
