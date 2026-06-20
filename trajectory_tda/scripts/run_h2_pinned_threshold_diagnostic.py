# ruff: noqa: E402
# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.5c small-L H2 threshold-comparability diagnostic.
"""Run the T1.5c H2 auto-threshold vs pinned-threshold diagnostic.

This Phase A driver compares the historical per-cloud auto threshold with a
common threshold pinned to the observed landmark enclosing radius. It is a
calibration diagnostic only; it does not apply the H2 decision rule or write a
vault result claim.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import math
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from joblib import Parallel, delayed
from scipy.spatial.distance import pdist

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", WORKTREE_ROOT)).resolve()
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from poverty_tda.topology.multidim_ph import (
    H2_CANDIDATE_TETRA_BUDGET,
    PHResult,
    compute_rips_ph,
    persistence_summary,
)
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint
from trajectory_tda.topology.permutation_nulls import _single_permutation
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks
from trajectory_tda.topology.vectorisation import wasserstein_distance as compute_wasserstein

LOGGER = logging.getLogger(__name__)

USOC_REL = Path("results/trajectory_tda_integration")
H2_REL = USOC_REL / "h2_check"
SCHEMA_VERSION = "stage1/t1-5c-h2-pinned-threshold-smallL/v1"
TASK_LABEL = "T1.5c H2 pinned-threshold matched-scale diagnostic"
PREREG = "2026-06-18 H2 threshold-comparability fix"
CONDITIONS: tuple[Literal["auto", "pinned"], ...] = ("auto", "pinned")


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


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(_jsonable(payload), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _git_head(worktree_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _available_physical_memory_gb() -> float | None:
    if sys.platform != "win32":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
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

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return float(status.ullAvailPhys) / (1024.0**3)


def _load_frozen_usoc(checkpoint_dir: Path) -> tuple[np.ndarray, list[list[str]], dict[str, Any], dict[str, Any]]:
    _, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    embeddings, embedding_info = ngram_embed(trajectories, **embed_kwargs)
    return embeddings, trajectories, embed_kwargs, embedding_info["fitted_models"]


def _ph_provenance(ph: PHResult) -> dict[str, Any]:
    return {
        "ph_method": ph.ph_method,
        "do_cocycles": bool(ph.do_cocycles),
        "threshold_rule": ph.threshold_rule,
        "threshold_value": ph.threshold_value,
        "edge_prop_at_thresh": ph.edge_prop_at_thresh,
        "candidate_tetrahedra_burden": ph.candidate_tetrahedra_burden,
        "wall_time_seconds": float(ph.elapsed_seconds),
        "backend_versions": dict(ph.backend_versions),
        "preflight": dict(ph.preflight),
    }


def _base_ph_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "max_dim": 2,
        "do_cocycles": False,
        "method": "ripser",
        "feasibility_tetra_budget": float(args.h2_tetra_budget),
    }


def _condition_ph_kwargs(base_kwargs: dict[str, Any], condition: str, tau: float) -> dict[str, Any]:
    kwargs = dict(base_kwargs)
    if condition == "pinned":
        kwargs["thresh"] = float(tau)
    elif condition != "auto":
        raise ValueError("condition must be 'auto' or 'pinned'")
    return kwargs


def _diagram_from_result(result: dict[str, Any], key: str) -> np.ndarray:
    dgm = result.get(f"{key}_dgm", [])
    return np.asarray(dgm, dtype=np.float64).reshape(-1, 2) if dgm else np.empty((0, 2))


def _wasserstein_from_diagrams(dgm_a: np.ndarray, dgm_b: np.ndarray, dim: int) -> float:
    return float(compute_wasserstein(PHResult(dgms={dim: dgm_a}), PHResult(dgms={dim: dgm_b}), dim=dim))


def _draw_null_pairs(n_permutations: int, seed: int, cap: int = 500) -> list[tuple[int, int]]:
    n_pairs = min(cap, n_permutations * (n_permutations - 1) // 2)
    all_pairs = [(i, j) for i in range(n_permutations) for j in range(i + 1, n_permutations)]
    rng = np.random.RandomState(seed)
    rng.shuffle(all_pairs)
    return [(int(i), int(j)) for i, j in all_pairs[:n_pairs]]


def _summary_stats(values: list[float]) -> dict[str, float | int | None]:
    finite = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not finite:
        return {"min": None, "median": None, "max": None, "mean": None, "n": 0}
    arr = np.asarray(finite, dtype=np.float64)
    return {
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "n": int(len(arr)),
    }


def _summarise_null_ph_provenance(null_results: list[dict[str, Any]]) -> dict[str, Any]:
    provenance = [r.get("_ph_provenance", {}) for r in null_results]
    return {
        "threshold_value": _summary_stats([p.get("threshold_value") for p in provenance]),
        "edge_prop_at_thresh": _summary_stats([p.get("edge_prop_at_thresh") for p in provenance]),
        "candidate_tetrahedra_burden": _summary_stats([p.get("candidate_tetrahedra_burden") for p in provenance]),
        "wall_time_seconds": _summary_stats([p.get("wall_time_seconds") for p in provenance]),
    }


def _verify_pinned_thresholds(tau: float, obs_provenance: dict[str, Any], null_results: list[dict[str, Any]]) -> bool:
    values = [obs_provenance.get("threshold_value")]
    values.extend(r.get("_ph_provenance", {}).get("threshold_value") for r in null_results)
    return all(value is not None and np.isclose(float(value), float(tau), rtol=0.0, atol=1e-9) for value in values)


def _aggregate_condition_stats(
    null_results: list[dict[str, Any]],
    *,
    seed: int,
    max_dim: int = 2,
    n_null_pairs_cap: int = 500,
) -> dict[str, Any]:
    pair_indices = _draw_null_pairs(len(null_results), seed=seed, cap=n_null_pairs_cap)
    output: dict[str, Any] = {
        "pair_draw_seed": int(seed),
        "pair_indices": [[int(i), int(j)] for i, j in pair_indices],
    }

    for dim in range(max_dim + 1):
        key = f"H{dim}"
        obs_null = np.asarray([float(r[key]) for r in null_results], dtype=np.float64)
        null_null: list[float] = []
        for i, j in pair_indices:
            d_i = _diagram_from_result(null_results[i], key)
            d_j = _diagram_from_result(null_results[j], key)
            null_null.append(_wasserstein_from_diagrams(d_i, d_j, dim))

        null_null_arr = np.asarray(null_null, dtype=np.float64)
        mean_obs_null = float(np.mean(obs_null))
        mean_null_null = float(np.mean(null_null_arr)) if len(null_null_arr) else float("nan")
        t_ratio = mean_obs_null / mean_null_null if mean_null_null > 0 else float("nan")
        exceedance_count = int(np.sum(null_null_arr >= mean_obs_null))
        n_draws = int(len(null_null_arr))
        p_value = float(exceedance_count / n_draws) if n_draws else float("nan")
        p_value_plus_one = float((exceedance_count + 1) / (n_draws + 1)) if n_draws else float("nan")

        output[key] = {
            "mean_wasserstein_obs_null": mean_obs_null,
            "std_wasserstein_obs_null": float(np.std(obs_null)),
            "median_wasserstein_obs_null": float(np.median(obs_null)),
            "mean_wasserstein_null_null": mean_null_null,
            "std_wasserstein_null_null": float(np.std(null_null_arr)) if n_draws else None,
            "t_ratio": t_ratio,
            "p_value": p_value,
            "p_value_plus_one": p_value_plus_one,
            "exceedance_count": exceedance_count,
            "pvalue_null_draws": n_draws,
            "significant_at_005": bool(p_value < 0.05),
            "obs_null_distribution": obs_null.tolist(),
            "null_null_distribution": null_null,
            "n_null_null_pairs": n_draws,
        }
        LOGGER.info(
            "  %s: mean_W(obs,null)=%.4f mean_W(null,null)=%.4f T=%.4f p=%.4f",
            key,
            mean_obs_null,
            mean_null_null,
            t_ratio,
            p_value,
        )
    return output


def _checkpoint_params(
    *,
    condition: str,
    L: int,
    B: int,
    seed: int,
    tau: float,
    ph_kwargs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "stage1/t1-5c-condition-checkpoint/v1",
        "condition": condition,
        "L": int(L),
        "B": int(B),
        "seed": int(seed),
        "tau": float(tau),
        "null": "markov-1",
        "statistic": "wasserstein",
        "ph_kwargs": _jsonable(ph_kwargs),
    }


def _run_condition_permutation(
    index: int,
    *,
    condition: str,
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    seed: int,
    max_dim: int,
    n_landmarks: int,
    markov_order: int,
    embed_kwargs: dict[str, Any],
    frozen_models: dict[str, Any],
    ph_observed: PHResult,
    ph_kwargs: dict[str, Any],
    pinned_thresh: float | None,
) -> tuple[int, dict[str, Any], float]:
    started = time.time()
    result = _single_permutation(
        "markov",
        embeddings,
        trajectories,
        None,
        seed,
        max_dim,
        n_landmarks,
        "wasserstein",
        markov_order,
        embed_kwargs,
        frozen_models=frozen_models,
        ph_observed=ph_observed,
        dedup=False,
        pinned_thresh=pinned_thresh,
        ph_kwargs=ph_kwargs,
    )
    elapsed = time.time() - started
    result["_condition"] = condition
    result["_permutation_index"] = int(index)
    result["_wall_time_seconds"] = float(elapsed)
    return index, result, elapsed


def _load_condition_checkpoint(path: Path, params: dict[str, Any], resume: bool) -> dict[str, dict[str, Any]]:
    if not resume or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("params") != _jsonable(params):
        LOGGER.warning("Ignoring incompatible checkpoint: %s", path)
        return {}
    results = {str(k): v for k, v in payload.get("results_by_index", {}).items()}
    LOGGER.info("Loaded checkpoint %s (%d/%d)", path, len(results), params["B"])
    return results


def _save_condition_checkpoint(path: Path, params: dict[str, Any], completed: dict[str, dict[str, Any]]) -> None:
    payload = {
        "schema_version": "stage1/t1-5c-condition-checkpoint/v1",
        "updated_at": _now_iso(),
        "params": _jsonable(params),
        "completed_count": len(completed),
        "total": int(params["B"]),
        "results_by_index": completed,
    }
    _write_json_atomic(path, payload)


def _run_condition(
    *,
    args: argparse.Namespace,
    condition: Literal["auto", "pinned"],
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    embed_kwargs: dict[str, Any],
    frozen_models: dict[str, Any],
    obs_landmarks: np.ndarray,
    tau: float,
    checkpoint_dir: Path,
) -> dict[str, Any]:
    LOGGER.info("Running L=%d condition=%s B=%d", obs_landmarks.shape[0], condition, args.B)
    base_kwargs = _base_ph_kwargs(args)
    observed_kwargs = _condition_ph_kwargs(base_kwargs, condition, tau)
    observed_started = time.time()
    ph_obs = compute_rips_ph(
        obs_landmarks,
        timeout_seconds=float(args.ph_timeout_seconds),
        **observed_kwargs,
    )
    observed_seconds = time.time() - observed_started
    obs_provenance = _ph_provenance(ph_obs)
    ph_summary = persistence_summary(ph_obs)

    worker_ph_kwargs = dict(base_kwargs)
    if int(args.n_jobs) == 1:
        worker_ph_kwargs["timeout_seconds"] = float(args.ph_timeout_seconds)
    else:
        LOGGER.info(
            "Parallel null PH uses joblib worker timeout instead of nested compute_rips_ph child timeout "
            "(avoids Windows loky/spawn start-method collision)."
        )
    pinned_thresh = float(tau) if condition == "pinned" else None
    checkpoint_path = checkpoint_dir / f"L{obs_landmarks.shape[0]}_{condition}_B{args.B}_seed{args.seed}.json"
    params = _checkpoint_params(
        condition=condition,
        L=obs_landmarks.shape[0],
        B=args.B,
        seed=args.seed,
        tau=tau,
        ph_kwargs=worker_ph_kwargs if pinned_thresh is None else {**worker_ph_kwargs, "thresh": tau},
    )
    completed = _load_condition_checkpoint(checkpoint_path, params, args.resume)

    missing = [idx for idx in range(args.B) if str(idx) not in completed]
    if missing:
        seeds = [int(args.seed) + idx + 1 for idx in range(args.B)]
        joblib_timeout = None if args.n_jobs == 1 else float(args.ph_timeout_seconds) * 2.0
        generated = Parallel(
            n_jobs=int(args.n_jobs),
            verbose=10 if args.verbose_joblib else 0,
            return_as="generator_unordered",
            timeout=joblib_timeout,
        )(
            delayed(_run_condition_permutation)(
                idx,
                condition=condition,
                embeddings=embeddings,
                trajectories=trajectories,
                seed=seeds[idx],
                max_dim=2,
                n_landmarks=obs_landmarks.shape[0],
                markov_order=1,
                embed_kwargs=embed_kwargs,
                frozen_models=frozen_models,
                ph_observed=ph_obs,
                ph_kwargs=worker_ph_kwargs,
                pinned_thresh=pinned_thresh,
            )
            for idx in missing
        )
        try:
            for idx, result, _elapsed in generated:
                completed[str(idx)] = _jsonable(result)
                _save_condition_checkpoint(checkpoint_path, params, completed)
                LOGGER.info(
                    "  %s L=%d permutation %d/%d complete", condition, obs_landmarks.shape[0], len(completed), args.B
                )
        except BaseException:
            _save_condition_checkpoint(checkpoint_path, params, completed)
            raise

    null_results = [completed[str(idx)] for idx in range(args.B)]
    if condition == "pinned" and not _verify_pinned_thresholds(tau, obs_provenance, null_results):
        raise RuntimeError("Pinned-threshold condition did not use identical tau for observed and all null PH calls")

    stats = _aggregate_condition_stats(
        null_results,
        seed=int(args.seed),
        max_dim=2,
        n_null_pairs_cap=int(args.n_null_pairs_cap),
    )
    null_provenance = [r.get("_ph_provenance", {}) for r in null_results]
    return {
        "condition": condition,
        "threshold_rule": "per-cloud-auto-p75" if condition == "auto" else "pinned-common-observed-enclosing-radius",
        "tau": float(tau),
        "L": int(obs_landmarks.shape[0]),
        "B": int(args.B),
        "n_jobs": int(args.n_jobs),
        "seed": int(args.seed),
        "null": "markov-1",
        "markov_order": 1,
        "statistic": "wasserstein",
        "wasserstein_order": 2,
        "wasserstein_internal_p": 2,
        "ph_kwargs": _jsonable(observed_kwargs),
        "null_worker_timeout_mode": "compute_rips_ph_child" if int(args.n_jobs) == 1 else "joblib_worker_timeout",
        "observed": {
            "vertex_count": int(obs_landmarks.shape[0]),
            "ph_summary": ph_summary,
            "ph_provenance": obs_provenance,
            "wall_time_seconds": float(observed_seconds),
        },
        "null_ph_provenance_summary": _summarise_null_ph_provenance(null_results),
        "null_ph_provenance": null_provenance,
        "permutation_wall_times_seconds": [float(r.get("_wall_time_seconds", 0.0)) for r in null_results],
        "checkpoint_path": str(checkpoint_path),
        "pinned_threshold_verified": (
            _verify_pinned_thresholds(tau, obs_provenance, null_results) if condition == "pinned" else None
        ),
        "stats": stats,
    }


def _compare_conditions(auto_result: dict[str, Any], pinned_result: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for dim in ("H0", "H1", "H2"):
        auto_stats = auto_result["stats"][dim]
        pinned_stats = pinned_result["stats"][dim]
        auto_t = float(auto_stats["t_ratio"])
        pinned_t = float(pinned_stats["t_ratio"])
        comparison[dim] = {
            "auto_t_ratio": auto_t,
            "pinned_t_ratio": pinned_t,
            "t_ratio_delta": float(pinned_t - auto_t),
            "t_ratio_collapse_factor": float(pinned_t / auto_t) if auto_t else None,
            "auto_p_value": float(auto_stats["p_value"]),
            "pinned_p_value": float(pinned_stats["p_value"]),
            "pinned_significant_at_005": bool(pinned_stats["significant_at_005"]),
        }
    return comparison


def run_diagnostic(args: argparse.Namespace) -> Path:
    """Run the pinned-threshold diagnostic and write one no-overwrite JSON.

    Args:
        args: Parsed CLI arguments controlling frozen inputs, checkpointing, and PH parameters.

    Returns:
        Path to the freshly written pinned-threshold result JSON.
    """
    started = time.time()
    checkpoint_root = args.proj_root / USOC_REL
    embeddings, trajectories, embed_kwargs, frozen_models = _load_frozen_usoc(checkpoint_root)
    checkpoint_dir = args.checkpoint_dir or (
        args.proj_root / H2_REL / "intermediates" / f"h2_pinned_vs_auto_smallL_{args.run_date}"
    )
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_path or (args.worktree_root / H2_REL / f"h2_pinned_vs_auto_smallL_{args.run_date}.json")

    estimated_observed_calls = len(args.Ls) * len(CONDITIONS)
    estimated_null_calls = len(args.Ls) * len(CONDITIONS) * int(args.B)
    estimated_ph_calls = estimated_observed_calls + estimated_null_calls
    estimated_wall_seconds = estimated_observed_calls * float(
        args.estimate_seconds_per_observed
    ) + estimated_null_calls * float(args.estimate_seconds_per_null) / max(1, int(args.n_jobs))
    estimate = {
        "estimated_ph_calls": int(estimated_ph_calls),
        "estimated_observed_calls": int(estimated_observed_calls),
        "estimated_null_calls": int(estimated_null_calls),
        "estimate_seconds_per_observed": float(args.estimate_seconds_per_observed),
        "estimate_seconds_per_null": float(args.estimate_seconds_per_null),
        "estimated_wall_seconds": float(estimated_wall_seconds),
        "estimated_wall_minutes": float(estimated_wall_seconds / 60.0),
        "note": "Estimate includes smoke-observed Markov re-embedding overhead; PH-only floor is much lower.",
    }
    LOGGER.info(
        "Pre-launch estimate: %d PH calls; %.1f minutes at n_jobs=%d using %.1fs/null",
        estimate["estimated_ph_calls"],
        estimate["estimated_wall_minutes"],
        args.n_jobs,
        estimate["estimate_seconds_per_null"],
    )

    results: dict[str, Any] = {}
    for L in args.Ls:
        actual_l = min(int(L), embeddings.shape[0])
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_l, seed=int(args.seed))
        tau = float(pdist(obs_landmarks).max())
        LOGGER.info("L=%d observed enclosing radius tau=%.6f", actual_l, tau)
        l_checkpoint_dir = checkpoint_dir / f"L{actual_l}"
        l_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        condition_payloads: dict[str, Any] = {}
        for condition in CONDITIONS:
            condition_payloads[condition] = _run_condition(
                args=args,
                condition=condition,
                embeddings=embeddings,
                trajectories=trajectories,
                embed_kwargs=embed_kwargs,
                frozen_models=frozen_models,
                obs_landmarks=obs_landmarks,
                tau=tau,
                checkpoint_dir=l_checkpoint_dir,
            )

        condition_payloads["comparison"] = _compare_conditions(
            condition_payloads["auto"],
            condition_payloads["pinned"],
        )
        results[f"L{actual_l}"] = condition_payloads

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "task": TASK_LABEL,
        "pre_registration": PREREG,
        "phase": "Phase A small-L diagnostic only; Phase B is manager-gated.",
        "inputs": {
            "canonical_embedding_source": _repo_relpath(checkpoint_root / "embeddings.npy", args.proj_root),
            "trajectory_source": _repo_relpath(checkpoint_root / "01_trajectories_sequences.json", args.proj_root),
            "embedding_metadata_source": _repo_relpath(checkpoint_root / "02_embedding.json", args.proj_root),
            "git_head": _git_head(args.worktree_root),
        },
        "params": {
            "Ls": [int(L) for L in args.Ls],
            "B": int(args.B),
            "seed": int(args.seed),
            "maxdim": 2,
            "null": "markov-1",
            "markov_order": 1,
            "statistic": "wasserstein",
            "conditions": list(CONDITIONS),
            "ph_method": "ripser",
            "do_cocycles": False,
            "h2_tetra_budget": float(args.h2_tetra_budget),
            "ph_timeout_seconds": float(args.ph_timeout_seconds),
            "n_jobs": int(args.n_jobs),
            "n_null_pairs_cap": int(args.n_null_pairs_cap),
            "available_memory_gb_at_start": _available_physical_memory_gb(),
            "checkpoint_dir": _repo_relpath(checkpoint_dir, args.proj_root),
            "regeneration_command": " ".join(sys.argv),
        },
        "pre_launch_estimate": estimate,
        "elapsed_seconds": float(time.time() - started),
        "results": results,
        "manager_gate": "Report Phase A numbers to Manager before any Phase B decision run or vault claim.",
    }
    _write_json_no_overwrite(output_path, payload)
    LOGGER.info("Wrote Phase A diagnostic JSON: %s", output_path)
    return output_path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the pinned-threshold diagnostic."""
    parser = argparse.ArgumentParser(description="Run T1.5c H2 pinned-vs-auto small-L diagnostic.")
    parser.add_argument("--proj-root", type=Path, default=PROJ_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=WORKTREE_ROOT)
    parser.add_argument("--run-date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--Ls", type=int, nargs="+", default=[200, 300])
    parser.add_argument("--B", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-jobs", type=int, default=4)
    parser.add_argument("--n-null-pairs-cap", type=int, default=500)
    parser.add_argument("--ph-timeout-seconds", type=float, default=300.0)
    parser.add_argument("--h2-tetra-budget", type=float, default=H2_CANDIDATE_TETRA_BUDGET)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--output-path", type=Path)
    parser.add_argument("--estimate-seconds-per-observed", type=float, default=20.0)
    parser.add_argument("--estimate-seconds-per-null", type=float, default=25.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verbose-joblib", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run the pinned-threshold diagnostic from the command line."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_diagnostic(parse_args())


if __name__ == "__main__":
    main()
