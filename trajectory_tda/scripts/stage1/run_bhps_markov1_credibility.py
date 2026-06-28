# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: T1.6 BHPS Markov-1 credibility diagnostics under frozen-loadings nulls.
"""Run BHPS Markov-1 W2 credibility diagnostics from frozen null caches.

This script reuses the post-refreeze T1.37 null diagram banks. It does not
regenerate PH by default: calibration uses a disjoint cached split, and the
variance diagnostic samples null-null W2 distances from cached diagrams.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from joblib import Parallel, delayed
from scipy.stats import chisquare, kstest

from poverty_tda.topology.multidim_ph import PHResult
from trajectory_tda.scripts.stage1._battery_core import convert_numpy, read_null_diagram_cache
from trajectory_tda.topology.vectorisation import wasserstein_distance

SCHEMA_VERSION = "stage1/bhps-markov1-credibility/v1"
TASK_LABEL = "T1.6 BHPS Markov-1 rejection credibility under valid frozen-loadings nulls"
PRE_REGISTRATION_REF = (
    "2026-06-13 T1.6 amendment at " "results/trajectory_tda_bhps/diagnostics/pre_registrations_2026-06-13.json"
)
CALIBRATION_OUTPUT_GLOB = "results/trajectory_tda_bhps/diagnostics/markov1_calibration_*.json"

PROJ_ROOT = Path("C:/Users/steph/TDL")
WORKTREE_ROOT = Path.cwd
BHPS_CACHE_REL = Path(
    "results/trajectory_tda_integration/stage1/cache/" "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz"
)
USOC_CACHE_REL = Path(
    "results/trajectory_tda_integration/stage1/cache/" "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"
)
BHPS_HEADLINE_REL = Path("results/trajectory_tda_bhps/stage1/bhps_headline_frozen_2026-05-28.json")
DIAGNOSTICS_REL = Path("results/trajectory_tda_bhps/diagnostics")
CHECKPOINT_REL = Path("results/trajectory_tda_bhps/diagnostics/checkpoints")

TARGET_DIM = 0
TARGET_DIM_LABEL = "h0"
DEFAULT_SEED = 42
DEFAULT_L = 5000
DEFAULT_N_TRIALS = 100
DEFAULT_CALIBRATION_BANK_B = 200
DEFAULT_VARIANCE_NULL_PAIRS = 1000
P_VALUE_FORMULA = "(r+1)/(B+1)"
# Exact W2 on ~5000-point H0 diagrams is memory-bandwidth bound and does NOT
# parallelise on this hardware: T1.6 measured a flat ~15-18 s/distance from 1 to 6
# loky workers, and `threading` gives ~no parallelism (gudhi's exact-W2 holds the
# GIL) plus a shared-heap OOM. `serial` (plain in-process loop, no joblib) is both
# the fastest path here (~9.88 s/distance vs loky's per-task pickling overhead) and
# the default; `loky`/`threading` remain available for other (smaller-diagram) uses.
DEFAULT_BACKEND = "serial"
# Worker count for the parallel backends only (ignored by `serial`). Static
# memory-safe default mirroring run_landmark_sensitivity.py:96-102.
DEFAULT_WORKERS = 6
# Measured serial exact-W2 throughput at L=5000 (T1.6 attempt #2, 100-sample
# null-pair phase: 987.8 s / 100). Used only for the up-front runtime estimate.
MEASURED_SERIAL_SECONDS_PER_DISTANCE = 9.88


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(float(value))


def _contains_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        return key in obj or any(_contains_key(value, key) for value in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(value, key) for value in obj)
    return False


def validate_bhps_markov1_credibility_payload(payload: dict[str, Any]) -> list[str]:
    """Validate the T1.6 calibration payload against the active schema contract."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a dict"]

    required_root = [
        "schema_version",
        "generated_at",
        "task",
        "pre_registration",
        "inputs",
        "params",
        "calibration",
        "variance",
        "decision",
    ]
    for key in required_root:
        if key not in payload:
            errors.append(f"missing root key {key}")

    if _contains_key(payload, "per_call_pca"):
        errors.append("forbidden key per_call_pca is present")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if not isinstance(payload.get("generated_at"), str):
        errors.append("generated_at must be str")
    task = payload.get("task")
    if not isinstance(task, str) or not task.startswith("T1.6"):
        errors.append("task must be a string beginning with 'T1.6'")
    pre_registration = payload.get("pre_registration")
    if not isinstance(pre_registration, str) or "2026-06-13" not in pre_registration:
        errors.append("pre_registration must reference the 2026-06-13 amendment")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs must be dict")
    else:
        for key in ("git_head", "bhps_null_cache", "usoc_null_cache"):
            if key not in inputs:
                errors.append(f"inputs.{key} is required")
        for label, expected_dataset in (("bhps_null_cache", "bhps"), ("usoc_null_cache", "usoc")):
            ref = inputs.get(label)
            if isinstance(ref, dict):
                metadata = ref.get("metadata", {})
                if metadata:
                    if metadata.get("B") != 1000:
                        errors.append(f"inputs.{label}.metadata.B must be 1000")
                    if metadata.get("L") != DEFAULT_L:
                        errors.append(f"inputs.{label}.metadata.L must be {DEFAULT_L}")
                    if metadata.get("seed") != DEFAULT_SEED:
                        errors.append(f"inputs.{label}.metadata.seed must be {DEFAULT_SEED}")
                    if metadata.get("frozen_loadings") is not True:
                        errors.append(f"inputs.{label}.metadata.frozen_loadings must be true")
                    if metadata.get("dataset") not in (None, expected_dataset):
                        errors.append(f"inputs.{label}.metadata.dataset must be {expected_dataset!r}")
            elif not isinstance(ref, str):
                errors.append(f"inputs.{label} must be a dict or string cache reference")

    params = payload.get("params")
    if not isinstance(params, dict):
        errors.append("params must be dict")
    else:
        if params.get("null_model") != "markov-1":
            errors.append("params.null_model must equal 'markov-1'")
        if params.get("frozen_loadings") is not True:
            errors.append("params.frozen_loadings must be true")
        if params.get("L") != DEFAULT_L:
            errors.append(f"params.L must equal {DEFAULT_L}")
        if params.get("seed") != DEFAULT_SEED:
            errors.append(f"params.seed must equal {DEFAULT_SEED}")
        if params.get("n_calibration_trials") != DEFAULT_N_TRIALS:
            errors.append(f"params.n_calibration_trials must equal {DEFAULT_N_TRIALS}")
        bank_b = params.get("calibration_null_bank_B")
        if not isinstance(bank_b, int) or isinstance(bank_b, bool) or bank_b < 100:
            errors.append("params.calibration_null_bank_B must be an int >= 100")
        if params.get("p_value_formula") != P_VALUE_FORMULA:
            errors.append(f"params.p_value_formula must equal {P_VALUE_FORMULA!r}")

    calibration = payload.get("calibration")
    calibrated_expected: bool | None = None
    if not isinstance(calibration, dict):
        errors.append("calibration must be dict")
    else:
        ks_statistic = calibration.get("ks_statistic")
        ks_p = calibration.get("ks_p")
        mean_pvalue = calibration.get("mean_pvalue")
        calibrated = calibration.get("calibrated")
        if not _is_number(ks_statistic) or float(ks_statistic) < 0:
            errors.append("calibration.ks_statistic must be a float >= 0")
        if not _is_number(ks_p) or not 0 <= float(ks_p) <= 1:
            errors.append("calibration.ks_p must be in [0, 1]")
        else:
            calibrated_expected = float(ks_p) >= 0.05
        if not _is_number(mean_pvalue) or not 0 <= float(mean_pvalue) <= 1:
            errors.append("calibration.mean_pvalue must be in [0, 1]")
        if not isinstance(calibrated, bool):
            errors.append("calibration.calibrated must be bool")
        elif calibrated_expected is not None and calibrated is not calibrated_expected:
            errors.append("calibration.calibrated must equal (ks_p >= 0.05)")

    variance = payload.get("variance")
    variance_expected: bool | None = None
    if not isinstance(variance, dict):
        errors.append("variance must be dict")
    else:
        bhps_cv = variance.get("bhps_nullnull_cv")
        usoc_cv = variance.get("usoc_nullnull_cv")
        variance_flag = variance.get("variance_flag")
        if not _is_number(bhps_cv) or float(bhps_cv) <= 0:
            errors.append("variance.bhps_nullnull_cv must be a float > 0")
        if not _is_number(usoc_cv) or float(usoc_cv) <= 0:
            errors.append("variance.usoc_nullnull_cv must be a float > 0")
        if _is_number(bhps_cv) and _is_number(usoc_cv) and float(bhps_cv) > 0 and float(usoc_cv) > 0:
            variance_expected = float(bhps_cv) < 0.5 * float(usoc_cv)
        if not isinstance(variance_flag, bool):
            errors.append("variance.variance_flag must be bool")
        elif variance_expected is not None and variance_flag is not variance_expected:
            errors.append("variance.variance_flag must equal (bhps_nullnull_cv < 0.5 * usoc_nullnull_cv)")

    decision = payload.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be dict")
    else:
        verdict = decision.get("verdict")
        if verdict not in {"credible", "conditionally_credible", "suspect"}:
            errors.append("decision.verdict must be credible, conditionally_credible, or suspect")
        if calibrated_expected is not None and variance_expected is not None and isinstance(verdict, str):
            if not calibrated_expected:
                expected_verdict = "suspect"
            elif variance_expected:
                expected_verdict = "conditionally_credible"
            else:
                expected_verdict = "credible"
            if verdict != expected_verdict:
                errors.append(f"decision.verdict must be {expected_verdict!r} for the calibration/variance flags")

    return errors


def _worktree_root() -> Path:
    return WORKTREE_ROOT()


def _proj_root() -> Path:
    override = os.environ.get("STAGE1_PROJ_ROOT")
    return Path(override) if override else PROJ_ROOT


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_worktree_root(), text=True).strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict[str, Any], *, overwrite: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(convert_numpy(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(5):
        try:
            if path.exists() and not overwrite:
                tmp.unlink(missing_ok=True)
                raise FileExistsError(f"refusing to overwrite existing output: {path}")
            os.replace(tmp, path)
            return path
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.25 * (attempt + 1))
    return path


def _cache_ref(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "metadata": convert_numpy(metadata),
        "size_bytes": int(stat.st_size),
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        "sha256": _sha256(path),
    }


def _validate_cache(label: str, path: Path, cache: dict[str, Any]) -> None:
    metadata = cache.get("metadata", {})
    expected = {
        "B": 1000,
        "L": DEFAULT_L,
        "seed": DEFAULT_SEED,
        "dataset": label,
        "frozen_loadings": True,
    }
    mismatches = {key: (metadata.get(key), value) for key, value in expected.items() if metadata.get(key) != value}
    if mismatches:
        raise ValueError(f"{label} cache metadata mismatch for {path}: {mismatches}")


def _finite_diagram(diagram: Any) -> np.ndarray:
    arr = np.asarray(diagram, dtype=np.float64).reshape(-1, 2)
    if len(arr) == 0:
        return np.empty((0, 2), dtype=np.float64)
    return arr[np.isfinite(arr).all(axis=1)]


def _ph(diagram: Any, dim: int) -> PHResult:
    return PHResult(dgms={dim: _finite_diagram(diagram)})


def _w2(diagram_a: Any, diagram_b: Any, dim: int) -> float:
    return float(wasserstein_distance(_ph(diagram_a, dim), _ph(diagram_b, dim), dim=dim, p=2))


def _sample_pairs(n_items: int, n_pairs: int, seed: int) -> list[tuple[int, int]]:
    rng = np.random.RandomState(seed)
    return [tuple(int(x) for x in rng.choice(n_items, size=2, replace=False)) for _ in range(n_pairs)]


def _load_progress(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"trials": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _distance_batch(
    parallel: Parallel,
    pairs: list[tuple[int, int]],
    diagrams: list[np.ndarray],
    dim: int,
) -> list[float]:
    return list(parallel(delayed(_w2)(diagrams[i], diagrams[j], dim) for i, j in pairs))


def _obs_to_bank_distances(
    parallel: Parallel,
    observed: np.ndarray,
    bank: list[np.ndarray],
    dim: int,
) -> list[float]:
    return list(parallel(delayed(_w2)(observed, candidate, dim) for candidate in bank))


def _peak_working_set_bytes() -> int | None:
    """Best-effort peak working set of the current process, in bytes.

    Pure-stdlib (Windows ``ctypes``/``GetProcessMemoryInfo``); returns ``None`` on
    platforms or runtimes where the query is unavailable. No ``psutil`` dependency.
    """
    try:
        import ctypes
        from ctypes import wintypes

        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        # Set the pseudo-handle return type to a full-width HANDLE; the default
        # c_int restype truncates it to -1 (32-bit) and corrupts the call.
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        if not ok:
            return None
        return int(counters.PeakWorkingSetSize)
    except (OSError, AttributeError, ValueError):
        return None


def _available_physical_memory_bytes() -> int | None:
    """Best-effort available physical memory, in bytes (Windows ``ctypes``).

    Returns ``None`` where unavailable. Pure-stdlib; no ``psutil`` dependency.
    """
    try:
        import ctypes
        from ctypes import wintypes

        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        if not ok:
            return None
        return int(status.ullAvailPhys)
    except (OSError, AttributeError, ValueError):
        return None


class _SerialExecutor:
    """In-process drop-in for ``joblib.Parallel`` that runs ``delayed`` tasks serially.

    Exact W2 on ~5000-point H0 diagrams is memory-bandwidth bound and does not
    parallelise on this hardware (T1.6: flat per-distance 1->6 workers), and joblib
    carries per-task pickling overhead, so a plain in-process loop is the fastest and
    simplest path. Accepts the same ``(func, args, kwargs)`` tuples ``delayed`` emits.
    """

    def __enter__(self) -> _SerialExecutor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def __call__(self, tasks: Any) -> list[Any]:
        return [func(*args, **kwargs) for func, args, kwargs in tasks]


def _make_executor(workers: int, backend: str) -> Any:
    """Return a context-manager executor: serial in-process or joblib ``Parallel``."""
    if backend == "serial":
        return _SerialExecutor()
    return Parallel(n_jobs=workers, backend=backend)


def _w2_with_peak_rss(diagram_a: Any, diagram_b: Any, dim: int) -> tuple[float, int | None]:
    """Compute the W2 distance and report the worker's peak working set (bytes)."""
    return _w2(diagram_a, diagram_b, dim), _peak_working_set_bytes()


def _obs_to_bank_with_rss(
    parallel: Parallel,
    observed: np.ndarray,
    bank: list[np.ndarray],
    dim: int,
) -> tuple[list[float], int | None]:
    """Benchmark obs-to-bank distances plus the max per-process peak RSS observed.

    Falls back to plain distances (RSS ``None``) when ``parallel`` is not callable
    (e.g. a test double), so the benchmark path stays unit-testable.
    """
    try:
        results = list(parallel(delayed(_w2_with_peak_rss)(observed, candidate, dim) for candidate in bank))
    except TypeError:
        return _obs_to_bank_distances(parallel, observed, bank, dim), None
    distances = [float(distance) for distance, _ in results]
    rss_samples = [rss for _, rss in results if rss is not None]
    return distances, (max(rss_samples) if rss_samples else None)


def compute_calibration(
    bhps_cache: dict[str, Any],
    *,
    n_trials: int,
    bank_b: int,
    seed: int,
    workers: int,
    backend: str,
    checkpoint_path: Path,
    benchmark_only: bool = False,
    benchmark_trials: int = 1,
    benchmark_null_pairs: int = 4,
    benchmark_bank_B: int = 4,
) -> dict[str, Any]:
    diagrams = [_finite_diagram(dgm) for dgm in bhps_cache["h0_diagrams"]]
    if len(diagrams) < n_trials + bank_b:
        raise ValueError(f"need at least {n_trials + bank_b} BHPS diagrams for disjoint calibration split")

    observed = diagrams[:n_trials]
    bank = diagrams[n_trials : n_trials + bank_b]
    active_bank = bank
    active_bank_b = bank_b
    active_null_pairs = bank_b
    if benchmark_only:
        # Time strictly more distances than the worker pool so elapsed/count
        # reflects steady-state per-distance throughput under genuine parallel
        # saturation, not a sub-pool burst. (The attempt-#2 probe was 4.7x
        # optimistic because it timed 4 distances against 8 workers.)
        saturated_bank_b = max(benchmark_bank_B, 2 * workers)
        active_bank_b = max(2, min(bank_b, saturated_bank_b))
        active_bank = bank[:active_bank_b]
        active_null_pairs = max(1, min(benchmark_null_pairs, active_bank_b))
        if active_bank_b <= workers:
            raise ValueError(
                "benchmark must time more distances than workers to measure "
                f"saturated throughput: active_bank_b={active_bank_b} <= workers={workers}; "
                "increase --calibration-null-bank-B or reduce --workers"
            )
    pair_indices = _sample_pairs(active_bank_b, active_null_pairs, seed)
    progress = _load_progress(checkpoint_path)
    expected_observed_indices = list(range(n_trials))
    expected_bank_indices = list(range(n_trials, n_trials + bank_b))
    expected_active_indices = list(range(n_trials, n_trials + active_bank_b))
    compatible_progress = (
        progress.get("benchmark_only") == bool(benchmark_only)
        and progress.get("observed_cache_indices") == expected_observed_indices
        and progress.get("bank_cache_indices") == expected_bank_indices
        and progress.get("active_bank_cache_indices") == expected_active_indices
        and int(progress.get("benchmark_null_pairs", -1)) == int(active_null_pairs)
        and int(progress.get("pair_seed", -1)) == int(seed)
    )
    if not compatible_progress:
        progress = {"trials": []}
    progress.setdefault("trials", [])
    progress.update(
        {
            "schema_version": "stage1/bhps-markov1-credibility-progress/v1",
            "updated_at": _utc_now(),
            "design": "cached_disjoint_split",
            "homology_dim": TARGET_DIM_LABEL,
            "observed_cache_indices": expected_observed_indices,
            "bank_cache_indices": expected_bank_indices,
            "active_bank_cache_indices": expected_active_indices,
            "benchmark_only": bool(benchmark_only),
            "benchmark_null_pairs": int(active_null_pairs),
            "pair_seed": seed,
            "p_value_formula": P_VALUE_FORMULA,
        }
    )

    _write_json(checkpoint_path, progress, overwrite=True)

    benchmark_peak_rss_bytes: int | None = None
    with _make_executor(workers, backend) as parallel:
        if len(progress.get("calibration_null_pair_distances", [])) == active_null_pairs:
            null_pair_distances = [float(x) for x in progress["calibration_null_pair_distances"]]
        else:
            t0 = time.time()
            null_pair_distances = _distance_batch(parallel, pair_indices, active_bank, TARGET_DIM)
            progress["calibration_null_pair_distances"] = null_pair_distances
            progress["calibration_null_pair_elapsed_s"] = time.time() - t0
            _write_json(checkpoint_path, progress, overwrite=True)

        completed = {int(row["trial_index"]): row for row in progress["trials"]}
        limit = min(n_trials, benchmark_trials) if benchmark_only else n_trials
        for trial_index in range(limit):
            if trial_index in completed:
                continue
            t0 = time.time()
            if benchmark_only:
                obs_null_distances, trial_peak_rss = _obs_to_bank_with_rss(
                    parallel, observed[trial_index], active_bank, TARGET_DIM
                )
                if trial_peak_rss is not None:
                    benchmark_peak_rss_bytes = max(benchmark_peak_rss_bytes or 0, trial_peak_rss)
            else:
                obs_null_distances = _obs_to_bank_distances(parallel, observed[trial_index], active_bank, TARGET_DIM)
            mean_obs_null = float(np.mean(obs_null_distances))
            mean_null_null = float(np.mean(null_pair_distances))
            rank_count = int(np.sum(np.asarray(null_pair_distances, dtype=np.float64) >= mean_obs_null))
            pvalue_denominator = len(null_pair_distances)
            p_value = float((rank_count + 1) / (pvalue_denominator + 1))
            row = {
                "trial_index": trial_index,
                "observed_cache_index": trial_index,
                "bank_cache_indices_start": n_trials,
                "bank_cache_indices_stop_exclusive": n_trials + active_bank_b,
                "mean_obs_null_w2": mean_obs_null,
                "mean_null_null_w2": mean_null_null,
                "t_ratio": float(mean_obs_null / mean_null_null) if mean_null_null > 0 else None,
                "rank_count": rank_count,
                "p_value": p_value,
                "pvalue_null_draws": pvalue_denominator,
                "obs_null_distances": [float(x) for x in obs_null_distances],
                "elapsed_s": time.time() - t0,
            }
            progress["trials"].append(row)
            progress["updated_at"] = _utc_now()
            _write_json(checkpoint_path, progress, overwrite=True)

    trials = sorted(progress["trials"], key=lambda row: int(row["trial_index"]))
    if benchmark_only and len(trials) < n_trials:
        elapsed_trials = [float(row["elapsed_s"]) for row in trials[:limit] if "elapsed_s" in row]
        mean_elapsed = float(np.mean(elapsed_trials)) if elapsed_trials else float("nan")
        null_pair_elapsed = float(progress.get("calibration_null_pair_elapsed_s", float("nan")))
        trial_seconds_per_distance = mean_elapsed / active_bank_b if np.isfinite(mean_elapsed) else float("nan")
        null_seconds_per_distance = (
            null_pair_elapsed / active_null_pairs
            if np.isfinite(null_pair_elapsed) and active_null_pairs
            else float("nan")
        )
        projected_calibration_s = None
        if np.isfinite(trial_seconds_per_distance) and np.isfinite(null_seconds_per_distance):
            projected_calibration_s = (
                null_seconds_per_distance * bank_b + trial_seconds_per_distance * n_trials * bank_b
            )
        available_bytes = _available_physical_memory_bytes()
        available_ram_gb = (available_bytes / 1e9) if available_bytes is not None else None
        per_process_rss_gb = (benchmark_peak_rss_bytes / 1e9) if benchmark_peak_rss_bytes else None
        projected_peak_memory_gb = per_process_rss_gb * workers if per_process_rss_gb is not None else None
        return {
            "benchmark_only": True,
            "backend": backend,
            "workers": workers,
            "completed_trials": len(trials),
            "mean_trial_elapsed_s": mean_elapsed,
            "projected_full_trials_s": mean_elapsed * n_trials if np.isfinite(mean_elapsed) else None,
            "projected_calibration_full_design_s": projected_calibration_s,
            "trial_seconds_per_distance": trial_seconds_per_distance
            if np.isfinite(trial_seconds_per_distance)
            else None,
            "null_pair_seconds_per_distance": null_seconds_per_distance
            if np.isfinite(null_seconds_per_distance)
            else None,
            "benchmark_bank_B": active_bank_b,
            "benchmark_null_pairs": active_null_pairs,
            "benchmark_distances_timed": active_bank_b,
            "per_process_peak_rss_bytes": benchmark_peak_rss_bytes,
            "per_process_peak_rss_gb": per_process_rss_gb,
            "available_ram_gb": available_ram_gb,
            "projected_peak_memory_gb": projected_peak_memory_gb,
            "full_design_distances_projected": bank_b + n_trials * bank_b,
            "checkpoint_path": str(checkpoint_path),
        }

    if len(trials) != n_trials:
        raise RuntimeError(f"calibration incomplete: {len(trials)} of {n_trials} trials")

    pvalues = np.asarray([float(row["p_value"]) for row in trials], dtype=np.float64)
    ks = kstest(pvalues, "uniform")
    bins = np.linspace(0, 1, 11)
    counts, edges = np.histogram(pvalues, bins=bins)
    chi = chisquare(counts, f_exp=np.full(10, len(pvalues) / 10))
    return {
        "design": "cached_disjoint_split",
        "homology_dim": TARGET_DIM_LABEL,
        "n_trials": n_trials,
        "observed_cache_indices": list(range(n_trials)),
        "calibration_null_bank_indices": list(range(n_trials, n_trials + bank_b)),
        "calibration_null_bank_B": bank_b,
        "ks_statistic": float(ks.statistic),
        "ks_p": float(ks.pvalue),
        "mean_pvalue": float(np.mean(pvalues)),
        "calibrated": bool(float(ks.pvalue) >= 0.05),
        "chi_square_statistic": float(chi.statistic),
        "chi_square_p": float(chi.pvalue),
        "chi_square_bins": [float(x) for x in edges.tolist()],
        "chi_square_counts": [int(x) for x in counts.tolist()],
        "trial_pvalues": [float(x) for x in pvalues.tolist()],
        "trial_details": trials,
        "null_pair_summary": {
            "n_pairs": len(null_pair_distances),
            "mean_w2": float(np.mean(null_pair_distances)),
            "sd_w2": float(np.std(null_pair_distances, ddof=1)),
        },
        "checkpoint_path": str(checkpoint_path),
        "discreteness_note": f"Trial p-values have resolution 1/(B+1) from the shared B={bank_b} null bank.",
    }


def compute_variance(
    cache: dict[str, Any],
    *,
    n_pairs: int,
    seed: int,
    workers: int,
    backend: str,
) -> dict[str, Any]:
    diagrams = [_finite_diagram(dgm) for dgm in cache["h0_diagrams"]]
    pairs = _sample_pairs(len(diagrams), n_pairs, seed)
    t0 = time.time()
    with _make_executor(workers, backend) as parallel:
        distances = _distance_batch(parallel, pairs, diagrams, TARGET_DIM)
    arr = np.asarray(distances, dtype=np.float64)
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1))
    return {
        "homology_dim": TARGET_DIM_LABEL,
        "n_pairs": int(n_pairs),
        "pair_seed": int(seed),
        "mean_w2": mean,
        "sd_w2": sd,
        "sd_ddof": 1,
        "cv": float(sd / mean) if mean > 0 else float("nan"),
        "elapsed_s": time.time() - t0,
        "pair_indices": [[int(i), int(j)] for i, j in pairs],
        "distances": [float(x) for x in arr.tolist()],
    }


def _decision(calibrated: bool, variance_flag: bool) -> str:
    if not calibrated:
        return "suspect"
    if variance_flag:
        return "conditionally_credible"
    return "credible"


def build_outputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    proj_root = _proj_root()
    bhps_cache_path = proj_root / BHPS_CACHE_REL
    usoc_cache_path = proj_root / USOC_CACHE_REL
    bhps_cache = read_null_diagram_cache(bhps_cache_path)
    usoc_cache = read_null_diagram_cache(usoc_cache_path)
    _validate_cache("bhps", bhps_cache_path, bhps_cache)
    _validate_cache("usoc", usoc_cache_path, usoc_cache)

    output_date = args.output_date
    checkpoint_path = proj_root / CHECKPOINT_REL / f"markov1_calibration_{output_date}_progress.json"
    calibration = compute_calibration(
        bhps_cache,
        n_trials=args.n_calibration_trials,
        bank_b=args.calibration_null_bank_B,
        seed=args.seed,
        workers=args.workers,
        backend=args.backend,
        checkpoint_path=checkpoint_path,
        benchmark_only=args.benchmark_only,
        benchmark_trials=args.benchmark_trials,
        benchmark_null_pairs=args.benchmark_null_pairs,
        benchmark_bank_B=args.benchmark_bank_B,
    )
    if args.benchmark_only:
        return calibration, {}

    bhps_var = compute_variance(
        bhps_cache,
        n_pairs=args.variance_null_pairs,
        seed=args.seed,
        workers=args.workers,
        backend=args.backend,
    )
    usoc_var = compute_variance(
        usoc_cache,
        n_pairs=args.variance_null_pairs,
        seed=args.seed,
        workers=args.workers,
        backend=args.backend,
    )
    variance_flag = bool(bhps_var["cv"] < 0.5 * usoc_var["cv"])
    verdict = _decision(bool(calibration["calibrated"]), variance_flag)

    generated_at = _utc_now()
    git_head = _git_head()
    available_bytes = _available_physical_memory_bytes()
    available_ram_gb = (available_bytes / 1e9) if available_bytes is not None else None
    cache_inputs = {
        "git_head": git_head,
        "bhps_null_cache": _cache_ref(bhps_cache_path, bhps_cache["metadata"]),
        "usoc_null_cache": _cache_ref(usoc_cache_path, usoc_cache["metadata"]),
        "bhps_headline_source": str(proj_root / BHPS_HEADLINE_REL),
    }
    params = {
        "null_model": "markov-1",
        "markov_order": 1,
        "frozen_loadings": True,
        "L": DEFAULT_L,
        "seed": args.seed,
        "homology_dim": TARGET_DIM_LABEL,
        "n_calibration_trials": args.n_calibration_trials,
        "calibration_null_bank_B": args.calibration_null_bank_B,
        "calibration_null_bank_B_floor": 100,
        "variance_null_pairs": args.variance_null_pairs,
        "p_value_formula": P_VALUE_FORMULA,
        "wasserstein_order": 2,
        "wasserstein_internal_p": 2,
        "wasserstein_function": "trajectory_tda.topology.vectorisation.wasserstein_distance",
        "fresh_ph_generated": False,
        "calibration_design": "cached_disjoint_split",
        "backend": args.backend,
        "workers": args.workers,
        "worker_cap_basis": (
            "static memory-safe default; ~0.2-0.8 GB per in-flight exact-W2 solve x "
            "workers << free RAM under loky per-process heaps"
        ),
        "preflight": {
            "backend": args.backend,
            "workers": args.workers,
            "available_ram_gb": available_ram_gb,
            "benchmark_seconds_per_distance": args.preflight_seconds_per_distance,
            "benchmark_per_process_peak_rss_gb": args.preflight_peak_rss_gb,
            "benchmark_projected_calibration_s": args.preflight_projection_s,
        },
    }
    variance_summary = {
        "homology_dim": TARGET_DIM_LABEL,
        "bhps_nullnull_cv": float(bhps_var["cv"]),
        "usoc_nullnull_cv": float(usoc_var["cv"]),
        "variance_flag": variance_flag,
        "variance_flag_rule": "bhps_nullnull_cv < 0.5 * usoc_nullnull_cv",
        "n_pairs_per_dataset": args.variance_null_pairs,
        "sd_ddof": 1,
    }
    calibration_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "task": TASK_LABEL,
        "pre_registration": PRE_REGISTRATION_REF,
        "inputs": cache_inputs,
        "params": params,
        "calibration": calibration,
        "variance": variance_summary,
        "decision": {
            "verdict": verdict,
            "rule": "credible if calibrated and not variance_flag; conditionally_credible if calibrated and variance_flag; suspect otherwise",
            "manager_locks_prose": True,
            "suspect_direction": "anti-conservative"
            if verdict == "suspect" and calibration["mean_pvalue"] < 0.5
            else None,
        },
    }
    validation_errors = validate_bhps_markov1_credibility_payload(calibration_payload)
    if validation_errors:
        raise ValueError("calibration payload failed contract validation: " + "; ".join(validation_errors))

    variance_payload = {
        "schema_version": "stage1/bhps-markov1-nullnull-variance/v1",
        "generated_at": generated_at,
        "task": TASK_LABEL,
        "pre_registration": PRE_REGISTRATION_REF,
        "inputs": cache_inputs,
        "params": params,
        "variance": variance_summary,
        "per_dataset": {
            "bhps": bhps_var,
            "usoc": usoc_var,
        },
    }
    return calibration_payload, variance_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--backend", default=DEFAULT_BACKEND, choices=["serial", "threading", "loky"])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-calibration-trials", type=int, default=DEFAULT_N_TRIALS)
    parser.add_argument("--calibration-null-bank-B", type=int, default=DEFAULT_CALIBRATION_BANK_B)
    parser.add_argument("--variance-null-pairs", type=int, default=DEFAULT_VARIANCE_NULL_PAIRS)
    parser.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--benchmark-trials", type=int, default=1)
    parser.add_argument("--benchmark-null-pairs", type=int, default=4)
    parser.add_argument("--benchmark-bank-B", type=int, default=4)
    # Provenance: carry the corrected --benchmark-only probe figures into the full
    # run's result JSON params (the confirm-then-launch gate reads them).
    parser.add_argument("--preflight-seconds-per-distance", type=float, default=None)
    parser.add_argument("--preflight-peak-rss-gb", type=float, default=None)
    parser.add_argument("--preflight-projection-s", type=float, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.backend != "serial" and args.workers < 4:
        raise ValueError("workers must be >= 4 for the parallel backends")
    if args.n_calibration_trials != DEFAULT_N_TRIALS:
        raise ValueError(f"n_calibration_trials is locked at {DEFAULT_N_TRIALS}")
    if args.calibration_null_bank_B < 100:
        raise ValueError("calibration_null_bank_B floor is 100")

    if not args.benchmark_only:
        est_distances = args.n_calibration_trials * args.calibration_null_bank_B + 2 * args.variance_null_pairs
        est_hours = est_distances * MEASURED_SERIAL_SECONDS_PER_DISTANCE / 3600
        print(
            f"[T1.6] backend={args.backend}: <= {est_distances} distances at "
            f"~{MEASURED_SERIAL_SECONDS_PER_DISTANCE}s -> ~{est_hours:.1f}h "
            "(cached null-pair bank reused; completed trials skipped on resume)",
            file=sys.stderr,
            flush=True,
        )

    calibration_payload, variance_payload = build_outputs(args)
    if args.benchmark_only:
        print(json.dumps(convert_numpy(calibration_payload), indent=2, sort_keys=True))
        return

    out_dir = _worktree_root() / DIAGNOSTICS_REL
    calibration_path = out_dir / f"markov1_calibration_{args.output_date}.json"
    variance_path = out_dir / f"markov1_nullnull_variance_{args.output_date}.json"
    for output_path in (variance_path, calibration_path):
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    _write_json(variance_path, variance_payload, overwrite=False)
    _write_json(calibration_path, calibration_payload, overwrite=False)
    print(
        json.dumps(
            {
                "calibration_path": str(calibration_path),
                "variance_path": str(variance_path),
                "ks_p": calibration_payload["calibration"]["ks_p"],
                "mean_pvalue": calibration_payload["calibration"]["mean_pvalue"],
                "calibrated": calibration_payload["calibration"]["calibrated"],
                "bhps_nullnull_cv": calibration_payload["variance"]["bhps_nullnull_cv"],
                "usoc_nullnull_cv": calibration_payload["variance"]["usoc_nullnull_cv"],
                "variance_flag": calibration_payload["variance"]["variance_flag"],
                "verdict": calibration_payload["decision"]["verdict"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
