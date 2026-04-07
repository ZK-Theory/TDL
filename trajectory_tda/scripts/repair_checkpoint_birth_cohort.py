# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Persist birth-year cohort metadata into legacy trajectory checkpoints.

"""Repair trajectory checkpoints by persisting birth-year cohort metadata.

This utility updates an existing ``01_trajectories.json`` file in place by
backfilling ``birth_year`` and ``birth_cohort`` from raw covariates. It is
intended for legacy checkpoints created before cohort metadata was added to the
checkpoint builders.

Usage:
    python -m trajectory_tda.scripts.repair_checkpoint_birth_cohort \
        --checkpoint results/trajectory_tda_integration

    python -m trajectory_tda.scripts.repair_checkpoint_birth_cohort \
        --checkpoint results/trajectory_tda_integration \
        --checkpoint results/trajectory_tda_bhps
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, cast

import pandas as pd

from trajectory_tda.data.covariate_extractor import attach_birth_cohort_metadata

logger = logging.getLogger(__name__)


def _metadata_dict_to_frame(raw_metadata: dict[str, Any], n_rows: int | None) -> pd.DataFrame:
    """Convert JSON checkpoint metadata back to a DataFrame."""
    columns: dict[str, list[Any]] = {}
    for key, values in raw_metadata.items():
        if isinstance(values, dict):
            values_dict = cast(dict[str, Any], values)
            if n_rows is None:
                ordered_keys = sorted(values_dict, key=int)
                columns[key] = [values_dict[index] for index in ordered_keys]
            else:
                columns[key] = [values_dict.get(str(index)) for index in range(n_rows)]
        else:
            columns[key] = list(values)
    return pd.DataFrame(columns)


def repair_checkpoint(checkpoint_dir: Path, data_dir: Path) -> tuple[int, int]:
    """Repair one checkpoint and return birth-year/cohort coverage counts."""
    checkpoint_file = checkpoint_dir / "01_trajectories.json"
    if not checkpoint_file.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")

    with open(checkpoint_file) as handle:
        payload = json.load(handle)

    metadata = _metadata_dict_to_frame(payload.get("metadata", {}), payload.get("n"))
    repaired = attach_birth_cohort_metadata(metadata, data_dir=data_dir)

    payload["metadata"] = repaired.to_dict()
    with open(checkpoint_file, "w") as handle:
        json.dump(payload, handle, indent=2, default=str)

    birth_year_count = 0
    if "birth_year" in repaired.columns:
        birth_year_count = int(repaired["birth_year"].notna().sum())

    birth_cohort_count = 0
    if "birth_cohort" in repaired.columns:
        birth_cohort_count = int(repaired["birth_cohort"].notna().sum())
    logger.info(
        "Updated %s: birth_year=%d/%d, birth_cohort=%d/%d",
        checkpoint_file,
        birth_year_count,
        len(repaired),
        birth_cohort_count,
        len(repaired),
    )
    return birth_year_count, birth_cohort_count


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint",
        action="append",
        required=True,
        help="Checkpoint directory to repair. Can be passed multiple times.",
    )
    parser.add_argument(
        "--data-dir",
        default="trajectory_tda/data",
        help="Root data directory containing BHPS/USoc raw files (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    data_dir = Path(args.data_dir)
    for checkpoint in args.checkpoint:
        repair_checkpoint(Path(checkpoint), data_dir)


if __name__ == "__main__":
    main()
