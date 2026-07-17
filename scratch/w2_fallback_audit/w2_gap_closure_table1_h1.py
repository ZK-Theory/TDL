"""Rebuild the valid T1.38 Table 1 H1 exact-W2 cells.

Each invocation owns one disjoint ``dataset:null`` checkpoint. It is deliberately
serial within that process: exact EMD and the 5,000-landmark PH step are both
memory-bandwidth intensive on this Windows host. The preflight selects the
fastest safe process count from measured candidates; the selected processes then
run separate cells, never joblib/loky within a cell.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gudhi
import numpy as np
import ot

if __package__:
    from . import audit_lib
else:  # pragma: no cover - direct executable path
    import audit_lib
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint, load_regime_labels
from trajectory_tda.topology.permutation_nulls import (
    _markov_shuffle,
    _order_shuffle,
    _stratified_markov_shuffle,
)
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks
from poverty_tda.topology.multidim_ph import compute_rips_ph


WORKTREE_ROOT = Path(__file__).resolve().parents[2]
PROJ_ROOT = audit_lib.project_root(WORKTREE_ROOT)
OUTPUT_ROOT = WORKTREE_ROOT / "results/trajectory_tda_integration/stage1"
CHECKPOINT_ROOT = Path(__file__).resolve().parent / "phase2_checkpoints"
DATE_DEFAULT = "2026-07-16"
B = 100
L = 5000
SEED = 42
VALID_NULLS = ("order_shuffle", "markov1", "markov2", "stratified_markov1")
DATASETS = {
    "usoc": PROJ_ROOT / "results/trajectory_tda_integration",
    "bhps": PROJ_ROOT / "results/trajectory_tda_bhps",
}


def _available_memory_gb() -> float:
    """Return currently available physical memory using the Windows system API."""
    if sys.platform != "win32":
        raise RuntimeError("This production runner records RAM preflight data on Windows only")

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    global_memory_status = kernel32.GlobalMemoryStatusEx
    global_memory_status.argtypes = [ctypes.POINTER(MemoryStatusEx)]
    global_memory_status.restype = ctypes.c_bool
    if not global_memory_status(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return float(status.ullAvailPhys) / (1024.0**3)


def _peak_working_set_gb() -> float:
    """Return this process's peak resident working set, including the PH stage."""
    if sys.platform != "win32":
        raise RuntimeError("This production runner records RAM preflight data on Windows only")

    class ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCountersEx()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    get_process_memory_info = psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemoryCountersEx), ctypes.c_ulong]
    get_process_memory_info.restype = ctypes.c_bool
    handle = get_current_process()
    if not get_process_memory_info(handle, ctypes.byref(counters), counters.cb):
        raise OSError("GetProcessMemoryInfo failed")
    return float(counters.PeakWorkingSetSize) / (1024.0**3)


def invalid_null_classifications() -> dict[str, dict[str, str]]:
    """Return permanent classifications for set-invariant pseudo-null rows."""
    reason = (
        "INVALID-BY-CONSTRUCTION: this operation only permutes rows of the already embedded "
        "point cloud. Rips PH is set-valued; any L=5000 difference can arise only from the "
        "order-dependent maxmin landmark start, not from a null-generating operation."
    )
    return {
        "label_shuffle": {"classification": "INVALID-BY-CONSTRUCTION", "reason": reason},
        "cohort_shuffle": {"classification": "INVALID-BY-CONSTRUCTION", "reason": reason},
    }


def _exact_solver_metadata() -> dict[str, object]:
    from gudhi.wasserstein import wasserstein_distance

    probe = wasserstein_distance(np.array([[0.0, 2.0]]), np.array([[1.0, 3.0]]), order=2, internal_p=2)
    if not np.isfinite(probe):
        raise RuntimeError("POT/Gudhi exact W2 probe returned a non-finite value")
    return {
        "name": "gudhi.wasserstein.wasserstein_distance",
        "exact": True,
        "pot_available": True,
        "backend_version": {"gudhi": gudhi.__version__, "pot": ot.__version__},
        "order": 2,
        "internal_p": 2,
        "actual_call_path_probe_w2": float(probe),
    }


def _finite_h1(ph: Any) -> np.ndarray:
    return audit_lib.finite_pairs(ph.h_features(1))


def _checkpoint_path(date: str, dataset: str, null_type: str, n_permutations: int) -> Path:
    return CHECKPOINT_ROOT / date / f"{dataset}_{null_type}_B{n_permutations}_L{L}_seed{SEED}.npz"


def _summary_path(date: str, dataset: str, null_type: str, n_permutations: int) -> Path:
    return _checkpoint_path(date, dataset, null_type, n_permutations).with_suffix(".json")


def _load_dataset(dataset: str) -> tuple[np.ndarray, list[list[str]], dict[str, Any], dict[str, Any], np.ndarray]:
    checkpoint_dir = DATASETS[dataset]
    _, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    observed_embeddings, embedding_info = ngram_embed(trajectories, **embed_kwargs)
    labels = load_regime_labels(checkpoint_dir / "05_analysis.json")
    if len(labels) != len(trajectories):
        raise RuntimeError(f"{dataset} regime-label rows do not align with trajectories")
    return observed_embeddings, trajectories, embed_kwargs, embedding_info["fitted_models"], labels


def _observed_h1(embeddings: np.ndarray) -> np.ndarray:
    _, landmarks = maxmin_landmarks(embeddings, min(L, len(embeddings)), seed=SEED)
    return _finite_h1(compute_rips_ph(landmarks, max_dim=1))


def _null_h1(
    null_type: str,
    trajectories: list[list[str]],
    embed_kwargs: dict[str, Any],
    frozen_models: dict[str, Any],
    regime_labels: np.ndarray,
    seed: int,
) -> np.ndarray:
    rng = np.random.RandomState(seed)
    if null_type == "order_shuffle":
        embeddings = _order_shuffle(trajectories, rng, embed_kwargs, frozen_models)
    elif null_type == "markov1":
        embeddings = _markov_shuffle(trajectories, rng, 1, embed_kwargs, frozen_models=frozen_models)
    elif null_type == "markov2":
        embeddings = _markov_shuffle(trajectories, rng, 2, embed_kwargs, alpha=1.0, frozen_models=frozen_models)
    elif null_type == "stratified_markov1":
        embeddings = _stratified_markov_shuffle(
            trajectories, regime_labels, rng, markov_order=1, embed_kwargs=embed_kwargs, frozen_models=frozen_models
        )
    else:
        raise ValueError(f"Invalid requested null type: {null_type}")
    _, landmarks = maxmin_landmarks(embeddings, min(L, len(embeddings)), seed=seed)
    return _finite_h1(compute_rips_ph(landmarks, max_dim=1))


def _load_or_init(
    path: Path, n: int
) -> tuple[list[np.ndarray | None], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not path.exists():
        empty = np.full(n, np.nan)
        return [None] * n, empty.copy(), empty.copy(), empty.copy(), empty.copy(), empty.copy()
    with np.load(path, allow_pickle=True) as saved:
        diagrams = [audit_lib.finite_pairs(x) if x is not None else None for x in saved["null_diagrams"]]
        empty = np.full(n, np.nan)
        return (
            diagrams,
            saved["obs_null_w2"],
            saved["generation_seconds"],
            saved["obs_bound"],
            saved["null_null_w2"] if "null_null_w2" in saved else empty.copy(),
            saved["null_null_seconds"] if "null_null_seconds" in saved else empty.copy(),
        )


def _write_checkpoint(
    path: Path,
    diagrams: list[np.ndarray | None],
    obs_w2: np.ndarray,
    gen_seconds: np.ndarray,
    bounds: np.ndarray,
    null_null_w2: np.ndarray,
    null_null_seconds: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = np.empty(len(diagrams), dtype=object)
    for i, diagram in enumerate(diagrams):
        stored[i] = np.empty((0, 2)) if diagram is None else diagram
    np.savez_compressed(
        path,
        null_diagrams=stored,
        obs_null_w2=obs_w2,
        generation_seconds=gen_seconds,
        obs_bound=bounds,
        null_null_w2=null_null_w2,
        null_null_seconds=null_null_seconds,
    )


def _progress(label: str, done: int, total: int, started: float) -> None:
    elapsed = time.perf_counter() - started
    eta = (total - done) * elapsed / done if done else float("nan")
    print(f"[{label}] {done}/{total}; elapsed={elapsed / 60:.1f}m eta={eta / 60:.1f}m", flush=True)


def _screen(left: list[np.ndarray], right: list[np.ndarray], values: np.ndarray) -> dict[str, float | int]:
    bounds = np.asarray([audit_lib.diagonal_bound(a, b) for a, b in zip(left, right, strict=True)])
    if np.any(values > bounds + 1e-10):
        raise RuntimeError("Exact-W2 diagonal-bound screen failed; refusing to write output")
    ratios = np.divide(values, bounds, out=np.zeros_like(values), where=bounds > 0)
    return {
        "n_values_screened": int(len(values)),
        "n_violations": 0,
        "max_ratio_to_bound": float(np.max(ratios, initial=0.0)),
        "tol": 1e-10,
    }


def run_cell(date: str, dataset: str, null_type: str, n_permutations: int, checkpoint_every: int) -> dict[str, Any]:
    if null_type not in VALID_NULLS:
        raise ValueError(f"Only valid nulls may be computed: {VALID_NULLS}")
    _exact_solver_metadata()
    label = f"{dataset}:{null_type}"
    free_gb_at_launch = _available_memory_gb()
    embeddings, trajectories, embed_kwargs, frozen_models, regime_labels = _load_dataset(dataset)
    print(f"[{label}] reconstructing observed frozen-loading H1 diagram", flush=True)
    obs_h1 = _observed_h1(embeddings)
    path = _checkpoint_path(date, dataset, null_type, n_permutations)
    diagrams, obs_w2, generation_seconds, obs_bounds, null_null_w2, null_null_seconds = _load_or_init(
        path, n_permutations
    )
    started = time.perf_counter()
    for index in range(n_permutations):
        if np.isfinite(obs_w2[index]):
            continue
        unit_started = time.perf_counter()
        diagram = _null_h1(null_type, trajectories, embed_kwargs, frozen_models, regime_labels, SEED + index + 1)
        diagrams[index] = diagram
        obs_w2[index] = audit_lib.exact_w2(obs_h1, diagram)
        generation_seconds[index] = time.perf_counter() - unit_started
        obs_bounds[index] = audit_lib.diagonal_bound(obs_h1, diagram)
        done = int(np.sum(np.isfinite(obs_w2)))
        if done % checkpoint_every == 0 or done == n_permutations:
            _write_checkpoint(path, diagrams, obs_w2, generation_seconds, obs_bounds, null_null_w2, null_null_seconds)
            _progress(label, done, n_permutations, started)
    if not np.all(np.isfinite(obs_w2)) or any(d is None for d in diagrams):
        raise RuntimeError(f"{label} checkpoint is incomplete")
    finite_diagrams = [d for d in diagrams if d is not None]
    pair_indices = audit_lib.reproduce_pair_indices(n_permutations, n_permutations, SEED)
    for index, (left, right) in enumerate(pair_indices):
        if np.isfinite(null_null_w2[index]):
            continue
        unit_started = time.perf_counter()
        null_null_w2[index] = audit_lib.exact_w2(finite_diagrams[left], finite_diagrams[right])
        null_null_seconds[index] = time.perf_counter() - unit_started
        done = int(np.sum(np.isfinite(null_null_w2)))
        if done % checkpoint_every == 0 or done == n_permutations:
            _write_checkpoint(path, diagrams, obs_w2, generation_seconds, obs_bounds, null_null_w2, null_null_seconds)
            _progress(f"{label}:null-null", done, n_permutations, started)
    if not np.all(np.isfinite(null_null_w2)):
        raise RuntimeError(f"{label} null-null checkpoint is incomplete")
    obs_screen = _screen([obs_h1] * n_permutations, finite_diagrams, obs_w2)
    nn_screen = _screen(
        [finite_diagrams[i] for i, _ in pair_indices], [finite_diagrams[j] for _, j in pair_indices], null_null_w2
    )
    stats = audit_lib.headline_stats_from_distances(obs_w2, null_null_w2)
    summary = {
        "dataset": dataset,
        "null_type": null_type,
        "B": n_permutations,
        "L": L,
        "seed": SEED,
        "observed_h1_features": int(len(obs_h1)),
        "null_h1_features_median": float(np.median([len(x) for x in finite_diagrams])),
        "statistics": stats,
        "diagonal_bound_screen": {"obs_null": obs_screen, "null_null": nn_screen},
        "cost": {
            "generation_plus_obs_w2_seconds": generation_seconds.tolist(),
            "null_null_w2_total_seconds": float(np.sum(null_null_seconds)),
            "null_null_w2_seconds_per_unit": float(np.mean(null_null_seconds)),
            "per_process_peak_gb": _peak_working_set_gb(),
            "free_gb_at_launch": free_gb_at_launch,
        },
        "checkpoint": str(path),
    }
    summary_path = _summary_path(date, dataset, null_type, n_permutations)
    summary_path.write_text(json.dumps(audit_lib.convert_numpy(summary), indent=2) + "\n", encoding="utf-8")
    print(f"[{label}] complete: {summary_path}", flush=True)
    return summary


def _cost_model(summaries: list[dict[str, Any]], n_permutations: int, worker_count: int = 1) -> dict[str, Any]:
    if worker_count < 1:
        raise ValueError("worker_count must be positive")
    generation_units = np.concatenate([np.asarray(s["cost"]["generation_plus_obs_w2_seconds"]) for s in summaries])
    nn_units = np.asarray([s["cost"]["null_null_w2_seconds_per_unit"] for s in summaries])
    measured = np.concatenate([generation_units, nn_units])
    p75_generation = float(np.percentile(generation_units, 75))
    p75_nn = float(np.percentile(nn_units, 75))
    full_cells = len(DATASETS) * len(VALID_NULLS)
    projected_units = full_cells * B
    telemetry = [
        s["cost"] for s in summaries if "per_process_peak_gb" in s["cost"] and "free_gb_at_launch" in s["cost"]
    ]
    if not telemetry:
        raise RuntimeError("No peak-RSS telemetry is available for the chosen worker-count cost model")
    observed_peak = max(float(cost["per_process_peak_gb"]) for cost in telemetry)
    observed_free = min(float(cost["free_gb_at_launch"]) for cost in telemetry)
    prelaunch_path = OUTPUT_ROOT / f"resource_preflight_t138_phase2_parallel_n{worker_count}_{DATE_DEFAULT}.json"
    if worker_count > 1 and prelaunch_path.exists():
        prelaunch_cost = json.loads(prelaunch_path.read_text(encoding="utf-8"))["cost_model"]
        per_process_peak = float(prelaunch_cost["per_process_peak_gb"])
        free_at_launch = float(prelaunch_cost["free_gb_at_launch"])
        prelaunch_source: str | None = str(prelaunch_path)
    else:
        per_process_peak = observed_peak
        free_at_launch = observed_free
        prelaunch_source = None
    parallel_ram = worker_count * per_process_peak
    headroom = free_at_launch - parallel_ram
    return {
        "n_units_benchmarked": int(len(measured)),
        "median_seconds_per_unit": float(np.median(measured)),
        "min_seconds_per_unit": float(np.min(measured)),
        "max_seconds_per_unit": float(np.max(measured)),
        "p75_generation_plus_obs_w2_seconds": p75_generation,
        "p75_null_null_w2_seconds": p75_nn,
        "projected_wall_hours": (projected_units * (p75_generation + p75_nn)) / (3600 * worker_count),
        "projected_units": projected_units * 2,
        "projection_basis": f"p75 production generation+exact obs-null and p75 exact null-null; B={n_permutations} measured per available cell",
        "worker_count": worker_count,
        "per_process_peak_gb": per_process_peak,
        "free_gb_at_launch": free_at_launch,
        "parallel_ram_required_gb": parallel_ram,
        "ram_headroom_gb": headroom,
        "ram_headroom_rule": "chosen workers require at least 25% of free RAM to remain available",
        "ram_preflight_passed": headroom >= 0.25 * free_at_launch,
        "prelaunch_resource_preflight": prelaunch_source,
        "post_restart_single_process_peak_gb": observed_peak,
        "post_restart_single_process_free_gb": observed_free,
        "parallelism": "serial within each OS process; cells are safe to launch as independent processes",
    }


def _preflight_classification(cost_model: dict[str, Any], wall_time_hours: float) -> str:
    """Classify a selected worker count against its recorded resource budget."""
    if wall_time_hours <= 0:
        raise ValueError("wall_time_hours must be positive")
    return (
        "GO" if cost_model["projected_wall_hours"] <= wall_time_hours and cost_model["ram_preflight_passed"] else "STOP"
    )


def write_preflight(
    date: str,
    summaries: list[dict[str, Any]],
    n_permutations: int,
    worker_count: int,
    wall_time_hours: float,
) -> Path:
    cost_model = _cost_model(summaries, n_permutations, worker_count)
    suffix = "" if worker_count == 1 else f"_parallel_n{worker_count}"
    output = OUTPUT_ROOT / f"resource_preflight_t138_phase2{suffix}_{date}.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing preflight: {output}")
    payload = {
        "task": "T1.38 phase 2 re-scoped valid-null preflight",
        "generated_at": datetime.now(UTC).isoformat(),
        "B_benchmarked": n_permutations,
        "L": L,
        "seed": SEED,
        "wall_time_budget_hours": wall_time_hours,
        "production_cells": [f"{dataset}:{null_type}" for dataset in DATASETS for null_type in VALID_NULLS],
        "cost_model": cost_model,
        "classification": _preflight_classification(cost_model, wall_time_hours),
        "reason": "Projection is based on actual frozen-loading null generation plus exact W2, not a retained cache.",
    }
    output.write_text(json.dumps(audit_lib.convert_numpy(payload), indent=2) + "\n", encoding="utf-8")
    return output


def assemble(date: str, worker_count: int) -> Path:
    summaries: list[dict[str, Any]] = []
    for dataset in DATASETS:
        for null_type in VALID_NULLS:
            path = _summary_path(date, dataset, null_type, B)
            if not path.exists():
                raise FileNotFoundError(f"Cannot assemble: required completed cell missing: {path}")
            summary = json.loads(path.read_text(encoding="utf-8"))
            checkpoint = Path(summary["checkpoint"])
            with np.load(checkpoint, allow_pickle=True) as saved:
                summary["statistics"] = audit_lib.headline_stats_from_distances(
                    saved["obs_null_w2"], saved["null_null_w2"]
                )
            summaries.append(summary)
    screen_rows = [s["diagonal_bound_screen"] for s in summaries]
    all_screen = {
        "n_values_screened": sum(
            r["obs_null"]["n_values_screened"] + r["null_null"]["n_values_screened"] for r in screen_rows
        ),
        "n_violations": 0,
        "max_ratio_to_bound": max(
            max(r["obs_null"]["max_ratio_to_bound"], r["null_null"]["max_ratio_to_bound"]) for r in screen_rows
        ),
        "tol": 1e-10,
        "cells": screen_rows,
    }
    benchmark_summaries = summaries
    cost_model = _cost_model(benchmark_summaries, B, worker_count)
    fresh_source = "fresh frozen-loading observed reconstruction and four valid surrogate generators"
    output = OUTPUT_ROOT / f"w2_gap_closure_table1_h1_{date}.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing result: {output}")
    result = {
        "schema_version": "stage1/w2-gap-closure/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "task": "T1.38 W2 gap closure phase 2 re-scoped valid Table 1 H1 rebuild",
        "phase": "phase2",
        "pre_registration": "results/trajectory_tda_integration/stage1/pre_registrations_w2_gap_closure_2026-07-15.json",
        "pre_registration_amendment": "results/trajectory_tda_integration/stage1/pre_registrations_w2_gap_closure_amendment_2026-07-16.json",
        "solver": _exact_solver_metadata(),
        "params": {"seed": SEED, "frozen_loadings": True, "p_value_formula": "(r+1)/(B+1)"},
        "inputs": {
            "git_head": audit_lib.git_head(WORKTREE_ROOT),
            "datasets": {
                name: {
                    "checkpoint": str(path),
                    "sequence_sha256": audit_lib.sha256_file(path / "01_trajectories_sequences.json"),
                }
                for name, path in DATASETS.items()
            },
        },
        "convention_gate": {
            "reference_freshly_recomputed": True,
            "reference_source": fresh_source,
            "artifact_under_test": "no prior numerical artifact; amended production rebuild",
            "greedy_replica_reproduces_committed": False,
            "absdiff": 0.0,
            "tol": 1e-10,
            "interpretation": "No legacy table value is used as a numerical anchor; all valid cells were generated afresh.",
        },
        "diagonal_bound_screen": all_screen,
        "cost_model": cost_model,
        "phase2": {
            "valid_nulls": list(VALID_NULLS),
            "invalid_nulls": invalid_null_classifications(),
            "h1_cells": summaries,
        },
    }
    output.write_text(json.dumps(audit_lib.convert_numpy(result), indent=2) + "\n", encoding="utf-8")
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DATE_DEFAULT)
    parser.add_argument("--only", help="comma-separated disjoint cells, e.g. usoc:markov1,bhps:markov1")
    parser.add_argument("--n-permutations", type=int, default=B)
    parser.add_argument("--checkpoint-every", type=int, default=5)
    parser.add_argument(
        "--worker-count",
        type=int,
        required=True,
        help="process count selected and recorded by the production-entry-point preflight",
    )
    parser.add_argument("--wall-time-hours", type=float, default=12.0, help="preflight wall-time budget in hours")
    parser.add_argument("--write-preflight", action="store_true")
    parser.add_argument("--assemble", action="store_true")
    args = parser.parse_args(argv)
    if args.n_permutations < 2:
        raise ValueError("n-permutations must be at least 2")
    if args.worker_count < 1:
        raise ValueError("worker-count must be positive")
    if args.wall_time_hours <= 0:
        raise ValueError("wall-time-hours must be positive")
    return args


def main() -> None:
    args = parse_args()
    if args.assemble:
        print(assemble(args.date, args.worker_count), flush=True)
        return
    cells = [(dataset, null_type) for dataset in DATASETS for null_type in VALID_NULLS]
    if args.only:
        requested: list[tuple[str, str]] = []
        for item in args.only.split(","):
            try:
                dataset, null_type = item.split(":", 1)
            except ValueError as exc:
                raise ValueError("--only entries must be dataset:null_type") from exc
            if (dataset, null_type) not in cells:
                raise ValueError(f"--only must name valid cells: {cells}")
            requested.append((dataset, null_type))
        if len(set(requested)) != len(requested):
            raise ValueError("--only cannot contain a duplicate cell")
        cells = requested
    if not args.only:
        raise ValueError(
            "Production cells must be launched as disjoint --only processes at the preflight-selected worker count; "
            "use --assemble after their checkpoints complete."
        )
    summaries = [
        run_cell(args.date, dataset, null_type, args.n_permutations, args.checkpoint_every)
        for dataset, null_type in cells
    ]
    if args.write_preflight:
        print(
            write_preflight(args.date, summaries, args.n_permutations, args.worker_count, args.wall_time_hours),
            flush=True,
        )


if __name__ == "__main__":
    main()
