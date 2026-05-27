# Research context: contracts/stage1-output-schemas/stage1-pvalue-denominator-cleanup.yaml
# Purpose: Build the T1.37 cache-based p-value denominator cleanup artifact.
"""Build Stage-1 p-value denominator cleanup JSON from preserved caches."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from joblib import Parallel, delayed

from poverty_tda.topology.multidim_ph import PHResult
from trajectory_tda.scripts.stage1 import _battery_core as core
from trajectory_tda.topology.vectorisation import wasserstein_distance


PROJ_ROOT = Path("C:/Users/steph/TDL")


RECOVERABLE_ANALYSES = [
    {
        "analysis_id": "usoc_headline",
        "dataset": "usoc",
        "source_result_path": PROJ_ROOT / "results/trajectory_tda_integration/stage1/usoc_headline_2026-05-24.json",
        "source_cache_path": PROJ_ROOT
        / "results/trajectory_tda_integration/stage1/cache/null_diagrams_usoc_B1000_L5000_seed42_2026-05-24.npz",
    },
    {
        "analysis_id": "bhps_headline",
        "dataset": "bhps",
        "source_result_path": PROJ_ROOT / "results/trajectory_tda_integration/stage1/bhps_headline_2026-05-24.json",
        "source_cache_path": PROJ_ROOT
        / "results/trajectory_tda_integration/stage1/cache/null_diagrams_bhps_B1000_L5000_seed42_2026-05-24.npz",
    },
    {
        "analysis_id": "bhps_length_matched_truncate",
        "dataset": "bhps",
        "source_result_path": PROJ_ROOT
        / "results/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_2026-05-25.json",
        "source_cache_path": PROJ_ROOT
        / "results/trajectory_tda_integration/stage1/cache/"
        "null_diagrams_bhps_length_matched_truncate_B1000_L5000_seed42_2026-05-25.npz",
    },
]

UNRECOVERABLE_ANALYSES = [
    {
        "analysis_id": "lm_sensitivity_L2500",
        "dataset": "usoc",
        "source_result_path": PROJ_ROOT / "results/trajectory_tda_integration/stage1/lm_sensitivity_L2500_2026-05-24.json",
        "wrapper_key": "L2500",
    },
    {
        "analysis_id": "lm_sensitivity_L8000",
        "dataset": "usoc",
        "source_result_path": PROJ_ROOT / "results/trajectory_tda_integration/stage1/lm_sensitivity_L8000_2026-05-25.json",
        "wrapper_key": "L8000",
    },
]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _cache_file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def _ph(dim: int, dgm: np.ndarray) -> PHResult:
    return PHResult(dgms={dim: np.array(dgm, dtype=np.float64).reshape(-1, 2)})


def _w2_distance(dgm_a: np.ndarray, dgm_b: np.ndarray, dim: int) -> float:
    return float(wasserstein_distance(_ph(dim, dgm_a), _ph(dim, dgm_b), dim=dim))


def _pair_indices(B: int, seed: int, n_pair_draws: int) -> list[tuple[int, int]]:
    rng = np.random.RandomState(seed)
    return [tuple(int(x) for x in rng.choice(B, size=2, replace=False)) for _ in range(n_pair_draws)]


def _landscape_distribution(
    obs_dgm: np.ndarray,
    null_dgms: list[np.ndarray],
    pair_indices: list[tuple[int, int]],
    k_max: int,
    n_points: int,
) -> tuple[float, list[float]]:
    if obs_dgm.shape[0] > 0:
        t_min = float(obs_dgm[:, 0].min())
        t_max = float(obs_dgm[:, 1].max())
    else:
        t_min, t_max = 0.0, 1.0
    t_vals = np.linspace(t_min, t_max, n_points)
    dx = (t_vals[-1] - t_vals[0]) / n_points if n_points > 1 else 1.0
    obs_land = core.landscape_on_grid(obs_dgm, t_vals, k_max)
    null_lands = [core.landscape_on_grid(dgm, t_vals, k_max) for dgm in null_dgms]
    obs_null = [core.landscape_l2_distance(obs_land, land, dx) for land in null_lands]
    null_null = [core.landscape_l2_distance(null_lands[i], null_lands[j], dx) for i, j in pair_indices]
    return float(np.mean(obs_null)), null_null


def _metric_rows_for_dim(
    analysis: dict[str, Any],
    source: dict[str, Any],
    cache_data: dict[str, Any],
    dim: int,
) -> list[dict[str, Any]]:
    dim_key = f"h{dim}"
    source_cell = source["result"][dim_key]
    B = int(source["run_params"]["B"])
    seed = int(source["run_params"]["seed"])
    k_max = int(source["run_params"].get("landscape_k_max", core.DEFAULT_K_MAX))
    n_points = int(source["run_params"].get("landscape_n_points", core.DEFAULT_N_POINTS))
    n_null_pairs_cap = int(source["run_params"].get("n_null_pairs_cap", core.DEFAULT_N_NULL_PAIRS))
    total_pairs = B * (B - 1) // 2
    old_pair_count = min(n_null_pairs_cap, total_pairs)
    corrected_pair_count = min(B, total_pairs)
    n_pair_draws = max(old_pair_count, corrected_pair_count)
    pairs = _pair_indices(B, seed, n_pair_draws)

    obs_dgm = cache_data[f"obs_{dim_key}_diagram"]
    null_dgms = cache_data[f"{dim_key}_diagrams"]

    obs_null_w2 = Parallel(n_jobs=-1, verbose=0)(
        delayed(_w2_distance)(dgm, obs_dgm, dim) for dgm in null_dgms
    )
    mean_obs_null_w2 = float(np.mean(obs_null_w2))
    null_null_w2 = Parallel(n_jobs=-1, verbose=0)(
        delayed(_w2_distance)(null_dgms[i], null_dgms[j], dim) for i, j in pairs
    )

    mean_obs_null_landscape, null_null_landscape = _landscape_distribution(
        obs_dgm=obs_dgm,
        null_dgms=null_dgms,
        pair_indices=pairs,
        k_max=k_max,
        n_points=n_points,
    )

    rows = []
    metric_specs = [
        ("w2", "w2_pvalue", mean_obs_null_w2, null_null_w2),
        ("landscape_l2", "landscape_l2_pvalue", mean_obs_null_landscape, null_null_landscape),
    ]
    for metric, source_key, mean_obs_null, null_null_values in metric_specs:
        old_values = np.array(null_null_values[:old_pair_count], dtype=np.float64)
        corrected_values = np.array(null_null_values[:corrected_pair_count], dtype=np.float64)
        old_rank_count = int(np.sum(old_values >= mean_obs_null))
        corrected_rank_count = int(np.sum(corrected_values >= mean_obs_null))
        old_denominator = old_pair_count + 1
        corrected_denominator = corrected_pair_count + 1
        old_reported = float(source_cell[source_key])
        corrected = float((corrected_rank_count + 1) / corrected_denominator)
        rows.append(
            {
                "cell_id": f"{analysis['analysis_id']}_{dim_key}_{metric}",
                "analysis_id": analysis["analysis_id"],
                "dataset": analysis["dataset"],
                "homology_dim": dim_key,
                "metric": metric,
                "old_reported_pvalue": old_reported,
                "corrected_pvalue": corrected,
                "old_denominator": old_denominator,
                "corrected_denominator": corrected_denominator,
                "old_pvalue_floor": float(1 / old_denominator),
                "corrected_pvalue_floor": float(1 / corrected_denominator),
                "old_rank_count": old_rank_count,
                "rank_count": corrected_rank_count,
                "B": B,
                "mean_obs_null": mean_obs_null,
                "source_cache_path": str(analysis["source_cache_path"]),
                "source_result_path": str(analysis["source_result_path"]),
                "rejection_changed_at_0_05": (old_reported < 0.05) != (corrected < 0.05),
            }
        )
    return rows


def _recoverable_rows(analysis: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    source = _load_json(analysis["source_result_path"])
    cache_data = core.read_null_diagram_cache(analysis["source_cache_path"])
    rows: list[dict[str, Any]] = []
    for dim in (0, 1):
        rows.extend(_metric_rows_for_dim(analysis, source, cache_data, dim))
    return rows, _cache_file_record(analysis["source_cache_path"]), {"path": str(analysis["source_result_path"])}


def _unrecoverable_rows(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    source = _load_json(analysis["source_result_path"])
    scope = source["result"][analysis["wrapper_key"]]
    rows = []
    reason = (
        "No preserved null-diagram cache was available for this LM sensitivity run; "
        "the historical final JSON contains p-values only."
    )
    for dim_key in ("h0", "h1"):
        for metric, source_key in (("w2", "w2_pvalue"), ("landscape_l2", "landscape_l2_pvalue")):
            rows.append(
                {
                    "cell_id": f"{analysis['analysis_id']}_{dim_key}_{metric}",
                    "analysis_id": analysis["analysis_id"],
                    "dataset": analysis["dataset"],
                    "homology_dim": dim_key,
                    "metric": metric,
                    "old_reported_pvalue": float(scope[dim_key][source_key]),
                    "source_result_path": str(analysis["source_result_path"]),
                    "reason": reason,
                }
            )
    return rows


def build_payload() -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    source_caches: dict[str, Any] = {}
    source_results: dict[str, Any] = {}
    for analysis in RECOVERABLE_ANALYSES:
        rows, cache_record, result_record = _recoverable_rows(analysis)
        cells.extend(rows)
        source_caches[analysis["analysis_id"]] = cache_record
        source_results[analysis["analysis_id"]] = result_record

    unrecoverable: list[dict[str, Any]] = []
    for analysis in UNRECOVERABLE_ANALYSES:
        unrecoverable.extend(_unrecoverable_rows(analysis))
        source_results[analysis["analysis_id"]] = {"path": str(analysis["source_result_path"])}

    return {
        "schema_version": "stage1-pvalue-denominator-cleanup/v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "formula": "(r + 1) / (B + 1)",
        "source_caches": source_caches,
        "source_results": source_results,
        "cells": cells,
        "unrecoverable_cells": unrecoverable,
        "summary": {
            "n_recomputed": len(cells),
            "n_unrecoverable": len(unrecoverable),
            "rejection_direction_changes": sum(1 for row in cells if row["rejection_changed_at_0_05"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            f"results/trajectory_tda_integration/stage1/pvalue_denominator_cleanup_{datetime.now().date()}.json"
        ),
    )
    args = parser.parse_args()
    payload = build_payload()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(core.convert_numpy(payload), indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
