# ruff: noqa: E402
# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.5f cached-diagram landscape-L2 grid correction check.
"""Compare old and corrected landscape-L2 grids from cached H2 diagrams.

This runner intentionally does not compute persistent homology. It reads the
T1.5e characterization JSON plus its cached per-null diagrams, then reports
whether a cached-only old-grid versus corrected-grid comparison can be made.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", WORKTREE_ROOT)).resolve()
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from trajectory_tda.scripts.run_h2_dispersion_dualmetric import (  # noqa: E402
    _landscape_l2_between_diagrams as _corrected_landscape_l2_between_diagrams,
)
from trajectory_tda.scripts.stage1._battery_core import (  # noqa: E402
    landscape_l2_distance,
    landscape_on_grid,
)

USOC_REL = Path("results/trajectory_tda_integration")
H2_REL = USOC_REL / "h2_check"
SCHEMA_VERSION = "stage1/t1-5f-h2-landscape-grid-correction/v1"
TASK_LABEL = "T1.5f H2 landscape-L2 grid correction check"
PREREG_CHAIN = [
    "results/trajectory_tda_integration/stage1/pre_registrations_2026-06-17.json",
    "results/trajectory_tda_integration/stage1/pre_registrations_2026-06-18.json",
    "results/trajectory_tda_integration/stage1/pre_registrations_h2_dispersion_2026-06-18.json",
    "results/trajectory_tda_integration/stage1/pre_registrations_h2_characterization_2026-06-19.json",
]
CELL_SPECS = {
    "median-pdist": {"condition": "power_median-pdist", "B": 1000},
    "max-pdist": {"condition": "normalizer_robustness_max-pdist", "B": 50},
    "mean-pdist": {"condition": "normalizer_robustness_mean-pdist", "B": 50},
}


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _repo_relpath(path: Path | str, root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _portable_arg(arg: str, *, proj_root: Path, worktree_root: Path) -> str:
    value = str(arg)
    roots = ((worktree_root, "<WORKTREE_ROOT>"), (proj_root, "<PROJ_ROOT>"))
    for root, label in roots:
        root_text = str(root)
        if value.lower().startswith(root_text.lower()):
            suffix = value[len(root_text) :].lstrip("\\/")
            return f"{label}/{Path(suffix).as_posix()}" if suffix else label
    return value


def _portable_command(argv: list[str], *, proj_root: Path, worktree_root: Path) -> str:
    return " ".join(_portable_arg(arg, proj_root=proj_root, worktree_root=worktree_root) for arg in argv)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result JSON: {path}")
    path.write_text(json.dumps(_jsonable(payload), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path


def _git_head(worktree_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _diagram_from_result(result: dict[str, Any], key: str = "H2") -> np.ndarray:
    dgm = result.get(f"{key}_dgm", [])
    arr = np.asarray(dgm, dtype=np.float64).reshape(-1, 2) if dgm else np.empty((0, 2))
    if arr.shape[0] > 0:
        arr = arr[np.isfinite(arr).all(axis=1)]
    return arr


def _observed_h2_diagram(cell: dict[str, Any]) -> np.ndarray | None:
    observed = cell.get("observed", {})
    for key in ("H2_dgm", "h2_dgm", "observed_h2_dgm"):
        if key in observed:
            return _diagram_from_result({"H2_dgm": observed[key]})
    return None


def _old_landscape_l2_between_diagrams(
    observed_dgm: np.ndarray,
    comparison_dgm: np.ndarray,
    *,
    k_max: int,
    n_points: int,
) -> float:
    if observed_dgm.shape[0] > 0:
        t_min = float(observed_dgm[:, 0].min())
        t_max = float(observed_dgm[:, 1].max())
    else:
        t_min, t_max = 0.0, 1.0
    t_values = np.linspace(t_min, t_max, n_points)
    dx = (t_values[-1] - t_values[0]) / n_points if n_points > 1 else 1.0
    obs_land = landscape_on_grid(observed_dgm, t_values, k_max)
    comp_land = landscape_on_grid(comparison_dgm, t_values, k_max)
    return landscape_l2_distance(obs_land, comp_land, dx)


def _metric_stats(
    obs_null: list[float],
    null_null_all: list[float],
    *,
    n_effect_pairs: int,
    n_pvalue_pairs: int,
) -> dict[str, Any]:
    obs_arr = np.asarray(obs_null, dtype=np.float64)
    effect = np.asarray(null_null_all[:n_effect_pairs], dtype=np.float64)
    pvalue = np.asarray(null_null_all[:n_pvalue_pairs], dtype=np.float64)
    mean_obs = float(np.mean(obs_arr))
    mean_null = float(np.mean(effect)) if len(effect) else float("nan")
    exceedance_count = int(np.sum(pvalue >= mean_obs))
    p_draws = int(len(pvalue))
    p_value = float((exceedance_count + 1) / (p_draws + 1)) if p_draws else float("nan")
    return {
        "mean_obs_null": mean_obs,
        "mean_null_null": mean_null,
        "t_ratio": mean_obs / mean_null if mean_null > 0 else None,
        "p_value": p_value,
        "exceedance_count": exceedance_count,
        "pvalue_null_draws": p_draws,
        "effect_null_pairs": int(len(effect)),
        "significant_at_005": bool(p_value < 0.05),
    }


def _distribution_delta(old_values: list[float], corrected_values: list[float]) -> dict[str, Any]:
    old_arr = np.asarray(old_values, dtype=np.float64)
    new_arr = np.asarray(corrected_values, dtype=np.float64)
    delta = new_arr - old_arr
    return {
        "n": int(len(delta)),
        "old_mean": float(np.mean(old_arr)) if len(old_arr) else None,
        "corrected_mean": float(np.mean(new_arr)) if len(new_arr) else None,
        "mean_delta": float(np.mean(delta)) if len(delta) else None,
        "mean_relative_delta": float(np.mean(delta) / np.mean(old_arr)) if len(delta) and np.mean(old_arr) else None,
        "max_abs_delta": float(np.max(np.abs(delta))) if len(delta) else None,
    }


def _full_pair_indices(original_metric: dict[str, Any]) -> list[tuple[int, int]]:
    effect = [tuple(int(v) for v in pair) for pair in original_metric.get("pair_indices", [])]
    pvalue = [tuple(int(v) for v in pair) for pair in original_metric.get("pvalue_pair_indices", [])]
    return effect if len(effect) >= len(pvalue) else pvalue


def _cell_checkpoint(checkpoint_root: Path, L: int, normalizer: str) -> Path:
    spec = CELL_SPECS[normalizer]
    return checkpoint_root / f"L{L}" / f"L{L}_{spec['condition']}_B{spec['B']}_seed42.json"


def _summarize_cell(
    *,
    L: int,
    normalizer: str,
    original_cell: dict[str, Any],
    checkpoint_path: Path,
    proj_root: Path,
    k_max: int,
    n_points: int,
) -> dict[str, Any]:
    spec = CELL_SPECS[normalizer]
    original_metric = original_cell["metrics"]["H2"]
    original_landscape = original_metric["landscape_l2"]
    cell_payload: dict[str, Any] = {
        "L": int(L),
        "normalizer": normalizer,
        "B": int(spec["B"]),
        "checkpoint_path": _repo_relpath(checkpoint_path, proj_root),
        "checkpoint_exists": checkpoint_path.exists(),
        "original_landscape_l2": {
            "p_value": float(original_landscape["p_value"]),
            "t_ratio": float(original_landscape["t_ratio"]),
            "mean_obs_null": float(original_landscape["mean_obs_null"]),
            "mean_null_null": float(original_landscape["mean_null_null"]),
            "significant_at_005": bool(original_landscape["significant_at_005"]),
            "pvalue_null_draws": int(original_landscape["pvalue_null_draws"]),
            "effect_null_pairs": int(original_landscape["effect_null_pairs"]),
        },
    }
    if not checkpoint_path.exists():
        cell_payload["recompute_status"] = "blocked_missing_checkpoint"
        return cell_payload

    checkpoint = _read_json(checkpoint_path)
    completed = checkpoint.get("results_by_index", {})
    cell_payload["checkpoint_completed_count"] = len(completed)
    cell_payload["checkpoint_total"] = int(checkpoint.get("total", spec["B"]))
    if len(completed) != spec["B"]:
        cell_payload["recompute_status"] = "blocked_incomplete_checkpoint"
        return cell_payload

    null_h2 = [_diagram_from_result(completed[str(idx)], "H2") for idx in range(spec["B"])]
    obs_h2 = _observed_h2_diagram(original_cell)
    cell_payload["observed_h2_diagram_cached"] = obs_h2 is not None
    cell_payload["observed_h2_features_in_summary"] = int(
        original_cell.get("observed", {}).get("ph_summary", {}).get("H2", {}).get("n_features", -1)
    )
    cell_payload["observed_h2_features_stored_in_summary"] = len(
        original_cell.get("observed", {}).get("ph_summary", {}).get("H2", {}).get("features", [])
    )

    full_pairs = _full_pair_indices(original_metric)
    null_null_old = [
        _old_landscape_l2_between_diagrams(null_h2[i], null_h2[j], k_max=k_max, n_points=n_points)
        for i, j in full_pairs
    ]
    null_null_corrected = [
        _corrected_landscape_l2_between_diagrams(null_h2[i], null_h2[j], k_max=k_max, n_points=n_points)
        for i, j in full_pairs
    ]
    cell_payload["null_null_grid_delta"] = _distribution_delta(null_null_old, null_null_corrected)

    if obs_h2 is None:
        cell_payload["recompute_status"] = "blocked_missing_observed_h2_diagram"
        cell_payload["blocking_reason"] = (
            "Cached null H2 diagrams are present, but the T1.5e result JSON stores only truncated observed "
            "H2 summaries (top-20 features), not the full observed H2 diagram required for obs-null "
            "landscape-L2 recomputation. No PH recompute was performed."
        )
        return cell_payload

    obs_null_old = [_old_landscape_l2_between_diagrams(obs_h2, dgm, k_max=k_max, n_points=n_points) for dgm in null_h2]
    obs_null_corrected = [
        _corrected_landscape_l2_between_diagrams(obs_h2, dgm, k_max=k_max, n_points=n_points) for dgm in null_h2
    ]
    n_effect_pairs = int(original_metric["landscape_l2"]["effect_null_pairs"])
    n_pvalue_pairs = int(original_metric["landscape_l2"]["pvalue_null_draws"])
    old_stats = _metric_stats(
        obs_null_old,
        null_null_old,
        n_effect_pairs=n_effect_pairs,
        n_pvalue_pairs=n_pvalue_pairs,
    )
    corrected_stats = _metric_stats(
        obs_null_corrected,
        null_null_corrected,
        n_effect_pairs=n_effect_pairs,
        n_pvalue_pairs=n_pvalue_pairs,
    )
    cell_payload["obs_null_grid_delta"] = _distribution_delta(obs_null_old, obs_null_corrected)
    cell_payload["old_grid_recomputed"] = old_stats
    cell_payload["corrected_grid"] = corrected_stats
    cell_payload["verdict_preserved"] = old_stats["significant_at_005"] == corrected_stats["significant_at_005"]
    cell_payload["recompute_status"] = "complete"
    return cell_payload


def run(args: argparse.Namespace) -> Path:
    original_path = args.original_json
    checkpoint_root = args.checkpoint_root
    original = _read_json(original_path)

    results: dict[str, dict[str, Any]] = {}
    blocked_cells: list[dict[str, Any]] = []
    changed_verdict_cells: list[dict[str, Any]] = []
    for L in args.Ls:
        l_key = f"L{int(L)}"
        results[l_key] = {}
        for normalizer in ("median-pdist", "max-pdist", "mean-pdist"):
            cell = _summarize_cell(
                L=int(L),
                normalizer=normalizer,
                original_cell=original["results"][l_key][normalizer],
                checkpoint_path=_cell_checkpoint(checkpoint_root, int(L), normalizer),
                proj_root=args.proj_root,
                k_max=int(args.landscape_k_max),
                n_points=int(args.landscape_n_points),
            )
            results[l_key][normalizer] = cell
            if cell.get("recompute_status") != "complete":
                blocked_cells.append({"L": int(L), "normalizer": normalizer, "status": cell.get("recompute_status")})
            elif not cell.get("verdict_preserved", False):
                changed_verdict_cells.append({"L": int(L), "normalizer": normalizer})

    if blocked_cells:
        status = "partial_escalate_missing_cached_observed_diagrams"
        restriction_stands_confirmed = False
    elif changed_verdict_cells:
        status = "partial_escalate_verdict_changed"
        restriction_stands_confirmed = False
    else:
        status = "complete_restriction_stands_confirmed"
        restriction_stands_confirmed = True

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "task": TASK_LABEL,
        "status": status,
        "restriction_stands_confirmed": restriction_stands_confirmed,
        "no_ph_recompute": True,
        "pre_registration_chain": PREREG_CHAIN,
        "inputs": {
            "original_characterization_json": _repo_relpath(original_path, args.worktree_root),
            "checkpoint_root": _repo_relpath(checkpoint_root, args.proj_root),
            "git_head": _git_head(args.worktree_root),
        },
        "params": {
            "Ls": [int(L) for L in args.Ls],
            "seed": 42,
            "normalizer_B": {normalizer: int(spec["B"]) for normalizer, spec in CELL_SPECS.items()},
            "landscape_k_max": int(args.landscape_k_max),
            "landscape_n_points": int(args.landscape_n_points),
            "old_grid": "support from first diagram only; dx=(t[-1]-t[0])/n_points",
            "corrected_grid": "union support from both diagrams; dx=(t[-1]-t[0])/(n_points-1)",
            "regeneration_command": _portable_command(
                sys.argv, proj_root=args.proj_root, worktree_root=args.worktree_root
            ),
        },
        "blocked_cells": blocked_cells,
        "changed_verdict_cells": changed_verdict_cells,
        "results": results,
    }
    return _write_json_no_overwrite(args.output_path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare old and corrected H2 landscape-L2 grids from cached diagrams."
    )
    parser.add_argument("--proj-root", type=Path, default=PROJ_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=WORKTREE_ROOT)
    parser.add_argument(
        "--original-json",
        type=Path,
        default=WORKTREE_ROOT / H2_REL / "h2_characterization_2026-06-19.json",
    )
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=PROJ_ROOT / H2_REL / "intermediates" / "h2_characterization_2026-06-19",
    )
    parser.add_argument("--output-path", type=Path)
    parser.add_argument("--run-date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--Ls", type=int, nargs="+", default=[200, 300])
    parser.add_argument("--landscape-k-max", type=int, default=5)
    parser.add_argument("--landscape-n-points", type=int, default=200)
    args = parser.parse_args()
    if args.output_path is None:
        args.output_path = args.worktree_root / H2_REL / f"h2_landscape_grid_correction_{args.run_date}.json"
    return args


def main() -> None:
    output_path = run(parse_args())
    print(output_path)


if __name__ == "__main__":
    main()
