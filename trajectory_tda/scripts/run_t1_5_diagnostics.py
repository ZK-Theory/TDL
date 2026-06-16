#!/usr/bin/env python3
# ruff: noqa: E402
# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.5 H2, positive-control, and doubled-n W2 diagnostic runner.
"""Run and assemble T1.5 auxiliary diagnostics.

The runner keeps committed JSONs under the active worktree and reads reusable
inputs/caches from the canonical project root. Long phases write date-suffixed
outputs and refuse to overwrite existing deliverables.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from joblib import Parallel, delayed

PROJ_ROOT = Path(r"C:\Users\steph\TDL")
WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from poverty_tda.topology.multidim_ph import PHResult, compute_rips_ph, persistence_summary
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts.run_positive_control import run_positive_control
from trajectory_tda.scripts.run_stage1_aux_diagnostics import validate_h2_positive_control_diagnostics_payload
from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint
from trajectory_tda.scripts.stage1 import _battery_core as core
from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks
from trajectory_tda.topology.vectorisation import compute_w2_ratio_bca_ci

LOGGER = logging.getLogger(__name__)
USOC_REL = Path("results/trajectory_tda_integration")
H2_REL = USOC_REL / "h2_check"
POSITIVE_REL = USOC_REL / "positive_control"
POST_AUDIT_REL = USOC_REL / "post_audit"
SUMMARY_SCHEMA = "stage1/h2-positive-control-diagnostics/v1"
TASK_LABEL = "T1.5 H2 + positive control + doubled-n W2"
PREREG = "2026-05-13 H2-Check pre-registration"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result JSON: {path}")
    path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")
    return path


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
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


def _elapsed_hours(start: float) -> float:
    return (time.time() - start) / 3600.0


def _check_hours(start: float, max_hours: float, phase: str) -> None:
    if max_hours > 0 and _elapsed_hours(start) > max_hours:
        raise TimeoutError(f"max-hours={max_hours} exceeded before {phase}")


def _load_frozen_usoc(checkpoint_dir: Path) -> tuple[np.ndarray, list[list[str]], dict[str, Any], dict[str, Any]]:
    _, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    embeddings, embedding_info = ngram_embed(trajectories, **embed_kwargs)
    return embeddings, trajectories, embed_kwargs, embedding_info["fitted_models"]


def _w2(dgm_a: np.ndarray, dgm_b: np.ndarray, dim: int) -> float:
    return float(core.wasserstein_distance_between_diagrams(dgm_a, dgm_b, dim))


def _timed_w2(dgm_a: np.ndarray, dgm_b: np.ndarray, dim: int) -> tuple[float, float]:
    started = time.time()
    value = _w2(dgm_a, dgm_b, dim)
    return value, time.time() - started


def _obs_null_w2_worker(
    idx: int,
    obs_h0: np.ndarray,
    obs_h1: np.ndarray,
    null_h0: np.ndarray,
    null_h1: np.ndarray,
) -> dict[str, Any]:
    h0_value, h0_seconds = _timed_w2(obs_h0, null_h0, 0)
    h1_value, h1_seconds = _timed_w2(obs_h1, null_h1, 1)
    return {
        "index": int(idx),
        "H0": h0_value,
        "H1": h1_value,
        "timings": {"H0_seconds": h0_seconds, "H1_seconds": h1_seconds},
    }


def _null_null_w2_worker_timed(
    position: int,
    i: int,
    j: int,
    dim: int,
    d_i: np.ndarray,
    d_j: np.ndarray,
) -> dict[str, Any]:
    value, seconds = _timed_w2(d_i, d_j, dim)
    return {
        "position": int(position),
        "i": int(i),
        "j": int(j),
        "value": value,
        "elapsed_seconds": seconds,
    }


def _fill_doubled_monitoring_paths(args: argparse.Namespace) -> None:
    if args.command != "doubled-n":
        return
    stem = f"04_nulls_wasserstein_w2_L5000_doublen_{args.run_date}"
    out_dir = args.proj_root / POST_AUDIT_REL / "intermediates" / stem
    if args.log_path is None:
        args.log_path = out_dir / f"{stem}.log"
    if args.progress_path is None:
        args.progress_path = out_dir / f"{stem}.progress.json"
    if args.checkpoint_dir is None:
        args.checkpoint_dir = out_dir / "checkpoint"


def _configure_file_logging(args: argparse.Namespace) -> None:
    log_path = getattr(args, "log_path", None)
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    LOGGER.info("Log file: %s", log_path)


def _write_progress(args: argparse.Namespace, started: float, phase: str, **fields: Any) -> None:
    progress_path = getattr(args, "progress_path", None)
    if progress_path is None:
        return
    payload = {
        "schema_version": "stage1/t1-5-doubled-n-progress/v1",
        "task": TASK_LABEL,
        "phase": phase,
        "heartbeat_at": _now_iso(),
        "elapsed_seconds": time.time() - started,
        "pid": os.getpid(),
        "run_date": args.run_date,
        "output_path": str(args.worktree_root / POST_AUDIT_REL / f"04_nulls_wasserstein_w2_L5000_doublen_{args.run_date}.json"),
        "log_path": str(args.log_path) if getattr(args, "log_path", None) else None,
        "checkpoint_dir": str(args.checkpoint_dir) if getattr(args, "checkpoint_dir", None) else None,
        "params": {
            "n_perms": int(args.n_perms),
            "n_nullnull": int(args.n_nullnull),
            "L": int(args.L),
            "seed": int(args.seed),
            "aggregate_jobs": int(args.aggregate_jobs),
            "checkpoint_every": int(args.checkpoint_every),
            "resume": bool(args.resume),
            "estimate_h0_seconds": float(args.estimate_h0_seconds),
            "estimate_h1_seconds": float(args.estimate_h1_seconds),
        },
        **fields,
    }
    _write_json_atomic(progress_path, payload)


def _checkpoint_matches(payload: dict[str, Any], args: argparse.Namespace, kind: str) -> bool:
    params = payload.get("params", {})
    return (
        payload.get("kind") == kind
        and int(params.get("n_perms", -1)) == int(args.n_perms)
        and int(params.get("n_nullnull", -1)) == int(args.n_nullnull)
        and int(params.get("L", -1)) == int(args.L)
        and int(params.get("seed", -1)) == int(args.seed)
        and int(params.get("aggregate_jobs", -1)) == int(args.aggregate_jobs)
        and str(params.get("cache_path", "")) == str(args.cache_path)
    )


def _checkpoint_params(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "n_perms": int(args.n_perms),
        "n_nullnull": int(args.n_nullnull),
        "L": int(args.L),
        "seed": int(args.seed),
        "cache_path": str(args.cache_path),
        "k_max": int(args.k_max),
        "n_points": int(args.n_points),
        "aggregate_jobs": int(args.aggregate_jobs),
        "checkpoint_every": int(args.checkpoint_every),
        "estimate_h0_seconds": float(args.estimate_h0_seconds),
        "estimate_h1_seconds": float(args.estimate_h1_seconds),
    }


def _load_checkpoint(path: Path, args: argparse.Namespace, kind: str) -> dict[str, Any] | None:
    if not args.resume or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not _checkpoint_matches(payload, args, kind):
        LOGGER.warning("Ignoring incompatible checkpoint: %s", path)
        return None
    LOGGER.info("Loaded checkpoint: %s", path)
    return payload


def run_h2(args: argparse.Namespace) -> None:
    started = time.time()
    checkpoint_dir = args.proj_root / USOC_REL
    embeddings, trajectories, embed_kwargs, frozen_models = _load_frozen_usoc(checkpoint_dir)
    actual_l = min(args.L, embeddings.shape[0])
    fallback_reason = args.fallback_reason
    if args.requested_L != args.L and not fallback_reason:
        raise ValueError("fallback_reason is required when requested_L differs from L")

    LOGGER.info("H2 observed PH: L=%d requested_L=%d maxdim=2", actual_l, args.requested_L)
    _, obs_landmarks = maxmin_landmarks(embeddings, actual_l, seed=args.seed)
    ph_obs = compute_rips_ph(obs_landmarks, max_dim=2)
    summary = persistence_summary(ph_obs)
    h2_summary = summary.get("H2", {})

    observed_payload = {
        "schema_version": "stage1/t1-5-h2-observed/v1",
        "generated_at": _now_iso(),
        "task": TASK_LABEL,
        "pre_registration": PREREG,
        "inputs": {
            "canonical_embedding_source": str(checkpoint_dir / "embeddings.npy"),
            "trajectory_source": str(checkpoint_dir / "01_trajectories_sequences.json"),
            "git_head": _git_head(args.worktree_root),
        },
        "params": {
            "requested_L": int(args.requested_L),
            "L": int(actual_l),
            "maxdim": 2,
            "seed": int(args.seed),
            "frozen_loadings": True,
            "fallback_reason": fallback_reason,
            "max_hours": float(args.max_hours),
        },
        "observed": {
            "H0": summary.get("H0", {}),
            "H1": summary.get("H1", {}),
            "H2": h2_summary,
            "n_h2_features": int(h2_summary.get("n_finite", 0)),
            "total_persistence_h2": float(h2_summary.get("total_persistence", 0.0)),
        },
    }
    observed_path = args.worktree_root / H2_REL / f"ph_H2_L{actual_l}_{args.run_date}.json"
    _write_json_no_overwrite(observed_path, observed_payload)
    LOGGER.info("H2 observed JSON: %s", observed_path)

    _check_hours(started, args.max_hours, "H2 Markov-1 null")
    LOGGER.info("H2 Markov-1 null: B=%d L=%d n_jobs=%d", args.B, actual_l, args.n_jobs)
    null_started = time.time()
    null_result = permutation_test_trajectories(
        embeddings=embeddings,
        trajectories=trajectories,
        null_type="markov",
        n_permutations=args.B,
        max_dim=2,
        n_landmarks=actual_l,
        statistic="wasserstein",
        markov_order=1,
        n_jobs=args.n_jobs,
        seed=args.seed,
        embed_kwargs=embed_kwargs,
        frozen_models=frozen_models,
    )
    null_result["elapsed_seconds"] = time.time() - null_started
    null_result["params"] = {
        "requested_L": int(args.requested_L),
        "L": int(actual_l),
        "B": int(args.B),
        "maxdim": 2,
        "seed": int(args.seed),
        "markov_order": 1,
        "null": "markov-1",
        "statistic": "wasserstein",
        "wasserstein_order": 2,
        "wasserstein_internal_p": 2,
        "frozen_loadings": True,
        "fallback_reason": fallback_reason,
        "max_hours": float(args.max_hours),
        "n_jobs": int(args.n_jobs),
    }
    null_result["inputs"] = observed_payload["inputs"]
    null_path = args.worktree_root / H2_REL / f"04_nulls_wasserstein_h2_L{actual_l}_{args.run_date}.json"
    _write_json_no_overwrite(null_path, {"markov": null_result})
    LOGGER.info("H2 null JSON: %s", null_path)


def run_positive(args: argparse.Namespace) -> None:
    out_path = args.worktree_root / POSITIVE_REL / f"markov1_simulation_{args.run_date}.json"
    result = run_positive_control(
        checkpoint_dir=args.proj_root / USOC_REL,
        n_permutations=args.B,
        n_landmarks=args.L,
        seed=args.seed,
        output_path=None,
        frozen_loadings=True,
        n_jobs=args.n_jobs,
    )
    result["schema_version"] = "stage1/t1-5-positive-control/v1"
    result["generated_at"] = _now_iso()
    result["task"] = TASK_LABEL
    result["pre_registration"] = PREREG
    result["params"] = {
        "null": "markov-1",
        "markov_order": 1,
        "seed": int(args.seed),
        "n_permutations": int(args.B),
        "L": int(args.L),
        "frozen_loadings": True,
        "tolerance_band": [0.3, 0.7],
        "n_jobs": int(args.n_jobs),
        "max_hours": float(args.max_hours),
    }
    result["calibration"] = {
        "p_h0": float(result["H0"]["p_value"]),
        "p_h1": float(result["H1"]["p_value"]),
        "tolerance_band": [0.3, 0.7],
        "calibrated": 0.3 <= float(result["H0"]["p_value"]) <= 0.7
        and 0.3 <= float(result["H1"]["p_value"]) <= 0.7,
    }
    _write_json_no_overwrite(out_path, result)
    LOGGER.info("Positive-control JSON: %s", out_path)


def _compute_obs_null_w2_checkpointed(
    cache: dict[str, Any],
    obs_h0: np.ndarray,
    obs_h1: np.ndarray,
    args: argparse.Namespace,
    started: float,
    parallel: Parallel,
) -> dict[str, Any]:
    path = args.checkpoint_dir / "obs_null_w2.json"
    payload = _load_checkpoint(path, args, "obs_null_w2")
    h0_values: list[float | None]
    h1_values: list[float | None]
    timings: list[dict[str, float] | None]
    if payload is not None:
        h0_values = list(payload.get("H0", []))
        h1_values = list(payload.get("H1", []))
        timings = list(payload.get("timings", []))
        if len(h0_values) != args.n_perms or len(h1_values) != args.n_perms:
            h0_values = [None] * args.n_perms
            h1_values = [None] * args.n_perms
            timings = [None] * args.n_perms
        if len(timings) != args.n_perms:
            timings = [None] * args.n_perms
    else:
        h0_values = [None] * args.n_perms
        h1_values = [None] * args.n_perms
        timings = [None] * args.n_perms

    while True:
        pending = [idx for idx in range(args.n_perms) if h0_values[idx] is None or h1_values[idx] is None]
        if not pending:
            break
        chunk_indices = pending[: args.checkpoint_every]
        LOGGER.info(
            "Doubled-n obs-null W2 chunk: permutations %d-%d of %d",
            chunk_indices[0] + 1,
            chunk_indices[-1] + 1,
            args.n_perms,
        )
        chunk_results = parallel(
            delayed(_obs_null_w2_worker)(
                idx,
                obs_h0,
                obs_h1,
                np.asarray(cache["h0_diagrams"][idx], dtype=np.float64).reshape(-1, 2),
                np.asarray(cache["h1_diagrams"][idx], dtype=np.float64).reshape(-1, 2),
            )
            for idx in chunk_indices
        )
        for result in chunk_results:
            idx = int(result["index"])
            h0_values[idx] = float(result["H0"])
            h1_values[idx] = float(result["H1"])
            timings[idx] = {
                "H0_seconds": float(result["timings"]["H0_seconds"]),
                "H1_seconds": float(result["timings"]["H1_seconds"]),
            }
            LOGGER.info(
                "Doubled-n obs-null W2 idx=%d H0=%.6f (%.2fs) H1=%.6f (%.2fs)",
                idx,
                h0_values[idx],
                timings[idx]["H0_seconds"],
                h1_values[idx],
                timings[idx]["H1_seconds"],
            )
            completed = sum(v is not None for v in h0_values)
            _write_progress(
                args,
                started,
                "obs_null_w2_call",
                completed=completed,
                total=int(args.n_perms),
                percent=completed / args.n_perms,
                latest_timing=result,
            )
        completed = sum(v is not None for v in h0_values)
        LOGGER.info("Doubled-n obs-null W2 checkpoint: %d/%d", completed, args.n_perms)
        _write_json_atomic(
            path,
            {
                "kind": "obs_null_w2",
                "generated_at": _now_iso(),
                "params": _checkpoint_params(args),
                "completed": completed,
                "total": int(args.n_perms),
                "H0": h0_values,
                "H1": h1_values,
                "timings": timings,
            },
        )
        _write_progress(args, started, "obs_null_w2", completed=completed, total=int(args.n_perms), percent=completed / args.n_perms)

    return {
        "H0": [float(v) for v in h0_values if v is not None],
        "H1": [float(v) for v in h1_values if v is not None],
        "timings": [t for t in timings if t is not None],
    }


def _doubled_pair_indices(args: argparse.Namespace) -> list[tuple[int, int]]:
    rng_pairs = np.random.RandomState(args.seed)
    n_total_pairs = args.n_perms * (args.n_perms - 1) // 2
    n_null_pairs = min(args.n_nullnull, n_total_pairs)
    n_pvalue_pairs = min(args.n_perms, n_total_pairs)
    n_pair_draws = max(n_null_pairs, n_pvalue_pairs)
    return [tuple(int(x) for x in rng_pairs.choice(args.n_perms, size=2, replace=False)) for _ in range(n_pair_draws)]


def _compute_null_null_w2_checkpointed(
    dim: int,
    null_dgms: list[np.ndarray],
    pair_indices: list[tuple[int, int]],
    args: argparse.Namespace,
    started: float,
    parallel: Parallel,
) -> dict[str, Any]:
    kind = f"h{dim}_null_null_w2"
    path = args.checkpoint_dir / f"{kind}.json"
    payload = _load_checkpoint(path, args, kind)
    if payload is not None and len(payload.get("values", [])) == len(pair_indices):
        values: list[float | None] = list(payload["values"])
        timings: list[float | None] = list(payload.get("timings", []))
    else:
        values = [None] * len(pair_indices)
        timings = [None] * len(pair_indices)
    if len(timings) != len(pair_indices):
        timings = [None] * len(pair_indices)

    while True:
        pending = [idx for idx, value in enumerate(values) if value is None]
        if not pending:
            break
        positions_by_pair: dict[tuple[int, int], list[int]] = {}
        for pos in pending:
            i, j = pair_indices[pos]
            key = (i, j) if i <= j else (j, i)
            positions_by_pair.setdefault(key, []).append(pos)
        chunk_keys = list(positions_by_pair)[: args.checkpoint_every]
        LOGGER.info(
            "Doubled-n H%d null-null W2 chunk: %d unique pairs covering %d sampled positions (%d/%d complete)",
            dim,
            len(chunk_keys),
            sum(len(positions_by_pair[key]) for key in chunk_keys),
            len(values) - len(pending),
            len(pair_indices),
        )
        chunk_results = parallel(
            delayed(_null_null_w2_worker_timed)(positions_by_pair[key][0], key[0], key[1], dim, null_dgms[key[0]], null_dgms[key[1]])
            for key in chunk_keys
        )
        for result in chunk_results:
            pos = int(result["position"])
            key = (int(result["i"]), int(result["j"]))
            for sampled_pos in positions_by_pair[key]:
                values[sampled_pos] = float(result["value"])
                timings[sampled_pos] = float(result["elapsed_seconds"])
            LOGGER.info(
                "Doubled-n H%d null-null W2 pair=(%d,%d) reused_for=%d value=%.6f elapsed=%.2fs",
                dim,
                int(result["i"]),
                int(result["j"]),
                len(positions_by_pair[key]),
                float(result["value"]),
                float(result["elapsed_seconds"]),
            )
            completed = len(values) - sum(value is None for value in values)
            _write_progress(
                args,
                started,
                f"{kind}_call",
                dim=dim,
                completed=completed,
                total=len(pair_indices),
                percent=completed / len(pair_indices) if pair_indices else 1.0,
                latest_timing=result,
            )
        completed = len(values) - sum(value is None for value in values)
        _write_json_atomic(
            path,
            {
                "kind": kind,
                "generated_at": _now_iso(),
                "params": _checkpoint_params(args),
                "completed": completed,
                "total": len(pair_indices),
                "pair_indices": [[int(i), int(j)] for i, j in pair_indices],
                "pair_draw_seed": int(args.seed),
                "values": values,
                "timings": timings,
            },
        )
        _write_progress(
            args,
            started,
            kind,
            dim=dim,
            completed=completed,
            total=len(pair_indices),
            percent=completed / len(pair_indices) if pair_indices else 1.0,
        )
    return {
        "values": [float(value) for value in values if value is not None],
        "timings": [float(value) for value in timings if value is not None],
        "pair_indices": [[int(i), int(j)] for i, j in pair_indices],
        "pair_draw_seed": int(args.seed),
    }


def _aggregate_doubled_dim_checkpointed(
    dim: int,
    obs_dgm: np.ndarray,
    null_dgms: list[np.ndarray],
    obs_null_w2: list[float],
    obs_null_timings: list[dict[str, float]],
    args: argparse.Namespace,
    started: float,
    parallel: Parallel,
) -> dict[str, Any]:
    cell_key = f"h{dim}"
    kind = f"{cell_key}_aggregate"
    path = args.checkpoint_dir / f"{kind}.json"
    payload = _load_checkpoint(path, args, kind)
    if payload is not None and "cell" in payload:
        return payload["cell"]

    LOGGER.info("Doubled-n %s aggregation starting", cell_key)
    ph_obs = PHResult(dgms={dim: obs_dgm})
    obs_null_w2_arr = np.array(obs_null_w2, dtype=np.float64)
    mean_obs_null_w2 = float(obs_null_w2_arr.mean())

    finite_obs = core._obs_finite_dgm(ph_obs, dim)
    if finite_obs.shape[0] > 0:
        t_min = float(finite_obs[:, 0].min())
        t_max = float(finite_obs[:, 1].max())
    else:
        t_min, t_max = 0.0, 1.0
    t_vals = np.linspace(t_min, t_max, args.n_points)
    dx = (t_vals[-1] - t_vals[0]) / args.n_points if args.n_points > 1 else 1.0
    obs_land = core.landscape_on_grid(core._obs_finite_dgm_for_landscape(ph_obs, dim), t_vals, args.k_max)

    null_lands: list[np.ndarray] = []
    obs_null_l2: list[float] = []
    for idx, dgm in enumerate(null_dgms):
        land_j = core.landscape_on_grid(dgm, t_vals, args.k_max)
        null_lands.append(land_j)
        obs_null_l2.append(core.landscape_l2_distance(obs_land, land_j, dx))
        if (idx + 1) % max(args.checkpoint_every, 1) == 0 or idx + 1 == len(null_dgms):
            _write_progress(
                args,
                started,
                f"{cell_key}_landscapes",
                dim=dim,
                completed=idx + 1,
                total=len(null_dgms),
                percent=(idx + 1) / len(null_dgms),
            )
    obs_null_land = np.array(obs_null_l2, dtype=np.float64)
    mean_obs_null_land = float(obs_null_land.mean())

    pair_indices_all = _doubled_pair_indices(args)
    n_total_pairs = args.n_perms * (args.n_perms - 1) // 2
    n_null_pairs = min(args.n_nullnull, n_total_pairs)
    n_pvalue_pairs = min(args.n_perms, n_total_pairs)
    null_null_bundle = _compute_null_null_w2_checkpointed(dim, null_dgms, pair_indices_all, args, started, parallel)
    null_null_w2_all = null_null_bundle["values"]
    null_null_l2_all = [
        core.landscape_l2_distance(null_lands[i], null_lands[j], dx) for (i, j) in pair_indices_all
    ]

    null_null_w2 = null_null_w2_all[:n_null_pairs]
    pvalue_null_null_w2 = null_null_w2_all[:n_pvalue_pairs]
    null_null_l2_list = null_null_l2_all[:n_null_pairs]
    pvalue_null_null_l2_list = null_null_l2_all[:n_pvalue_pairs]

    null_null_w2_arr = np.array(null_null_w2, dtype=np.float64) if null_null_w2 else np.array([0.0])
    null_null_l2_arr = np.array(null_null_l2_list, dtype=np.float64) if null_null_l2_list else np.array([0.0])
    mean_null_null_w2 = float(null_null_w2_arr.mean())
    mean_null_null_land = float(null_null_l2_arr.mean())

    t_ratio_w2 = mean_obs_null_w2 / mean_null_null_w2 if mean_null_null_w2 > 0 else float("nan")
    bca_ci_lower: float | None = None
    bca_ci_upper: float | None = None
    if len(obs_null_w2_arr) >= 2 and len(null_null_w2_arr) >= 2:
        try:
            _, bca_ci_lower, bca_ci_upper = compute_w2_ratio_bca_ci(obs_null_w2_arr, null_null_w2_arr, seed=args.seed)
        except Exception as exc:
            LOGGER.warning("BCa CI failed for W2 H%d: %s", dim, exc)

    pvalue_null_null_w2_arr = np.array(pvalue_null_null_w2, dtype=np.float64) if pvalue_null_null_w2 else np.array([0.0])
    r_w2 = int(np.sum(pvalue_null_null_w2_arr >= mean_obs_null_w2))
    n_w2 = len(pvalue_null_null_w2_arr)
    w2_pvalue = (r_w2 + 1) / (n_w2 + 1)
    r_lower = int(np.sum(pvalue_null_null_w2_arr <= mean_obs_null_w2))
    lower_tail_pvalue = (r_lower + 1) / (n_w2 + 1)
    std_w2 = float(null_null_w2_arr.std()) if len(null_null_w2) > 1 else float("nan")
    d_perm_w2 = (mean_obs_null_w2 - mean_null_null_w2) / std_w2 if std_w2 > 0 else float("nan")

    t_ratio_land = mean_obs_null_land / mean_null_null_land if mean_null_null_land > 0 else float("nan")
    bca_ci_lower_land: float | None = None
    bca_ci_upper_land: float | None = None
    if len(obs_null_land) >= 2 and len(null_null_l2_arr) >= 2:
        try:
            _, bca_ci_lower_land, bca_ci_upper_land = compute_w2_ratio_bca_ci(
                obs_null_land, null_null_l2_arr, seed=args.seed
            )
        except Exception as exc:
            LOGGER.warning("BCa CI failed for landscape L2 H%d: %s", dim, exc)

    pvalue_null_null_l2_arr = (
        np.array(pvalue_null_null_l2_list, dtype=np.float64) if pvalue_null_null_l2_list else np.array([0.0])
    )
    r_land = int(np.sum(pvalue_null_null_l2_arr >= mean_obs_null_land))
    n_land = len(pvalue_null_null_l2_arr)
    land_pvalue = (r_land + 1) / (n_land + 1)
    std_land = float(null_null_l2_arr.std()) if len(null_null_l2_list) > 1 else float("nan")
    d_perm_land = (mean_obs_null_land - mean_null_null_land) / std_land if std_land > 0 else float("nan")

    cell: dict[str, Any] = {
        "w2_pvalue": w2_pvalue,
        "pvalue_null_draws": n_w2,
        "effect_null_pairs": len(null_null_w2_arr),
        "landscape_l2_pvalue": land_pvalue,
        "t_ratio": t_ratio_w2,
        "bca_ci_lower": bca_ci_lower,
        "bca_ci_upper": bca_ci_upper,
        "d_perm": d_perm_w2,
        "mean_obs_null": mean_obs_null_w2,
        "mean_null_null": mean_null_null_w2,
        "obs_null_w2_values": [float(v) for v in obs_null_w2],
        "obs_null_w2_timings": obs_null_timings,
        "null_null_w2_values": [float(v) for v in null_null_w2_all],
        "null_null_w2_timings": null_null_bundle["timings"],
        "null_null_pair_indices": null_null_bundle["pair_indices"],
        "pair_draw_seed": null_null_bundle["pair_draw_seed"],
        "landscape_t_ratio": t_ratio_land,
        "landscape_bca_ci_lower": bca_ci_lower_land,
        "landscape_bca_ci_upper": bca_ci_upper_land,
        "landscape_d_perm": d_perm_land,
    }
    if dim == 0:
        cell["lower_tail_pvalue"] = lower_tail_pvalue

    _write_json_atomic(
        path,
        {
            "kind": kind,
            "generated_at": _now_iso(),
            "params": _checkpoint_params(args),
            "cell": cell,
            "diagnostics": {
                "obs_null_count": len(obs_null_w2_arr),
                "null_null_pair_draws": len(pair_indices_all),
                "effect_null_pairs": n_null_pairs,
                "pvalue_null_pairs": n_pvalue_pairs,
            },
        },
    )
    _write_progress(args, started, kind, dim=dim, completed=1, total=1, percent=1.0, cell=cell)
    LOGGER.info("Doubled-n %s aggregation complete: W2 p=%.6f", cell_key, w2_pvalue)
    return cell


def _aggregate_doubled_checkpointed(
    cache: dict[str, Any],
    obs_h0: np.ndarray,
    obs_h1: np.ndarray,
    obs_null: dict[str, Any],
    args: argparse.Namespace,
    started: float,
    parallel: Parallel,
) -> dict[str, Any]:
    result = {
        "h0": _aggregate_doubled_dim_checkpointed(
            0,
            obs_h0,
            [np.asarray(dgm, dtype=np.float64).reshape(-1, 2) for dgm in cache["h0_diagrams"][: args.n_perms]],
            obs_null["H0"],
            [dict(t) for t in obs_null["timings"]],
            args,
            started,
            parallel,
        )
    }
    result["h1"] = _aggregate_doubled_dim_checkpointed(
        1,
        obs_h1,
        [np.asarray(dgm, dtype=np.float64).reshape(-1, 2) for dgm in cache["h1_diagrams"][: args.n_perms]],
        obs_null["H1"],
        [dict(t) for t in obs_null["timings"]],
        args,
        started,
        parallel,
    )
    return result


def run_doubled(args: argparse.Namespace) -> None:
    started = time.time()
    if not 1 <= args.aggregate_jobs <= 6:
        raise ValueError("aggregate_jobs must be between 1 and 6 for this shared machine")
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    _write_progress(args, started, "starting", completed=0, total=1, percent=0.0)
    cache_started = time.time()
    cache = core.read_null_diagram_cache(args.cache_path)
    cache_elapsed = time.time() - cache_started
    LOGGER.info("Doubled-n cache loaded in %.2fs: %s", cache_elapsed, args.cache_path)
    if cache["metadata"].get("B", 0) < args.n_perms:
        raise ValueError(f"cache has B={cache['metadata'].get('B')} but n_perms={args.n_perms} requested")
    if cache["metadata"].get("L") != args.L or cache["metadata"].get("seed") != args.seed:
        raise ValueError("cache L/seed does not match requested doubled-n parameters")
    if cache["metadata"].get("frozen_loadings") is not True:
        raise ValueError("doubled-n requires a frozen-loadings cache")

    obs_h0 = np.asarray(cache["obs_h0_diagram"], dtype=np.float64).reshape(-1, 2)
    obs_h1 = np.asarray(cache["obs_h1_diagram"], dtype=np.float64).reshape(-1, 2)
    n_pair_draws = len(_doubled_pair_indices(args))
    estimated_seconds = (
        (float(args.estimate_h0_seconds) + float(args.estimate_h1_seconds))
        * (int(args.n_perms) + n_pair_draws)
        / int(args.aggregate_jobs)
    )
    estimate = {
        "h0_seconds_per_call": float(args.estimate_h0_seconds),
        "h1_seconds_per_call": float(args.estimate_h1_seconds),
        "h0_calls": int(args.n_perms) + n_pair_draws,
        "h1_calls": int(args.n_perms) + n_pair_draws,
        "total_w2_calls": 2 * (int(args.n_perms) + n_pair_draws),
        "aggregate_jobs": int(args.aggregate_jobs),
        "estimated_seconds": estimated_seconds,
        "estimated_hours": estimated_seconds / 3600.0,
    }
    LOGGER.info("Doubled-n wall-time estimate before launch: %s", estimate)
    _write_progress(
        args,
        started,
        "wall_time_estimate",
        completed=0,
        total=int(args.n_perms),
        percent=0.0,
        cache_metadata=cache["metadata"],
        cache_elapsed_seconds=cache_elapsed,
        wall_time_estimate=estimate,
    )
    with Parallel(n_jobs=args.aggregate_jobs, return_as="generator_unordered", verbose=0) as parallel:
        obs_null = _compute_obs_null_w2_checkpointed(cache, obs_h0, obs_h1, args, started, parallel)
        result = _aggregate_doubled_checkpointed(cache, obs_h0, obs_h1, obs_null, args, started, parallel)
    baseline = json.loads(args.baseline_path.read_text(encoding="utf-8"))
    baseline_h0 = float(baseline["result"]["h0"]["w2_pvalue"])
    baseline_h1 = float(baseline["result"]["h1"]["w2_pvalue"])
    h0_p = float(result["h0"]["w2_pvalue"])
    h1_p = float(result["h1"]["w2_pvalue"])
    mc_tolerance = max(0.01, 2 * (1 / (args.n_perms + 1) + 1 / (1000 + 1)))
    stable = (h0_p < 0.05) == (baseline_h0 < 0.05) and (h1_p < 0.05) == (baseline_h1 < 0.05)
    stable = stable and abs(h0_p - baseline_h0) <= mc_tolerance and abs(h1_p - baseline_h1) <= mc_tolerance
    per_pair_w2 = {
        "obs_null": {
            "H0": result["h0"]["obs_null_w2_values"],
            "H1": result["h1"]["obs_null_w2_values"],
            "timings": {
                "H0_seconds": [float(t["H0_seconds"]) for t in result["h0"]["obs_null_w2_timings"]],
                "H1_seconds": [float(t["H1_seconds"]) for t in result["h1"]["obs_null_w2_timings"]],
            },
        },
        "null_null": {
            "pair_draw_seed": int(result["h0"]["pair_draw_seed"]),
            "pair_indices": result["h0"]["null_null_pair_indices"],
            "H0": result["h0"]["null_null_w2_values"],
            "H1": result["h1"]["null_null_w2_values"],
            "timings": {
                "H0_seconds": result["h0"]["null_null_w2_timings"],
                "H1_seconds": result["h1"]["null_null_w2_timings"],
            },
        },
    }
    per_pair_keys = {
        "obs_null_w2_values",
        "obs_null_w2_timings",
        "null_null_w2_values",
        "null_null_w2_timings",
        "null_null_pair_indices",
        "pair_draw_seed",
    }
    result_for_payload = {
        dim: {key: value for key, value in cell.items() if key not in per_pair_keys} for dim, cell in result.items()
    }
    payload = {
        "schema_version": "stage1/t1-5-doubled-n-w2/v1",
        "generated_at": _now_iso(),
        "task": TASK_LABEL,
        "pre_registration": PREREG,
        "inputs": {
            "null_diagram_cache": str(args.cache_path),
            "baseline_t1_2_result": str(args.baseline_path),
            "git_head": _git_head(args.worktree_root),
            "checkpoint_dir": str(args.checkpoint_dir),
            "log_path": str(args.log_path),
            "progress_path": str(args.progress_path),
        },
        "params": {
            "n_perms": int(args.n_perms),
            "n_nullnull": int(args.n_nullnull),
            "L": int(args.L),
            "seed": int(args.seed),
            "markov_order": 1,
            "null": "markov-1",
            "frozen_loadings": True,
            "wasserstein_order": 2,
            "wasserstein_internal_p": 2,
            "landscape_k_max": int(args.k_max),
            "landscape_n_points": int(args.n_points),
            "pvalue_formula": "(r+1)/(B+1)",
            "aggregate_jobs": int(args.aggregate_jobs),
            "checkpoint_every": int(args.checkpoint_every),
            "resume": bool(args.resume),
            "wall_time_estimate": estimate,
        },
        "result": result_for_payload,
        "per_pair_w2": per_pair_w2,
        "stability": {
            "baseline_h0_w2_pvalue": baseline_h0,
            "baseline_h1_w2_pvalue": baseline_h1,
            "h0_w2_pvalue": h0_p,
            "h1_w2_pvalue": h1_p,
            "mc_tolerance": mc_tolerance,
            "stable_vs_t1_2": bool(stable),
        },
    }
    out_path = args.worktree_root / POST_AUDIT_REL / f"04_nulls_wasserstein_w2_L5000_doublen_{args.run_date}.json"
    _write_json_no_overwrite(out_path, payload)
    _write_progress(args, started, "complete", completed=1, total=1, percent=1.0, final_output=str(out_path))
    LOGGER.info("Doubled-n JSON: %s", out_path)


def build_summary(args: argparse.Namespace) -> None:
    h2_ph = json.loads(args.h2_ph.read_text(encoding="utf-8"))
    h2_null_all = json.loads(args.h2_null.read_text(encoding="utf-8"))
    h2_null = h2_null_all["markov"]
    positive = json.loads(args.positive_control.read_text(encoding="utf-8"))
    doubled = json.loads(args.doubled_n.read_text(encoding="utf-8"))
    p_h0 = float(positive["H0"]["p_value"])
    p_h1 = float(positive["H1"]["p_value"])
    payload = {
        "schema_version": SUMMARY_SCHEMA,
        "generated_at": _now_iso(),
        "task": TASK_LABEL,
        "pre_registration": PREREG,
        "inputs": {
            "canonical_embedding_source": h2_ph["inputs"]["canonical_embedding_source"],
            "fitted_markov1_source": h2_ph["inputs"]["trajectory_source"],
            "git_head": _git_head(args.worktree_root),
            "h2_observed_path": str(args.h2_ph),
            "h2_null_path": str(args.h2_null),
            "positive_control_path": str(args.positive_control),
            "doubled_n_path": str(args.doubled_n),
        },
        "h2_check": {
            "maxdim": 2,
            "requested_L": int(h2_ph["params"]["requested_L"]),
            "L": int(h2_ph["params"]["L"]),
            "fallback_reason": h2_ph["params"].get("fallback_reason"),
            "seed": int(h2_null["params"]["seed"]),
            "B": int(h2_null["params"]["B"]),
            "markov_order": 1,
            "null": "markov-1",
            "wasserstein_order": 2,
            "wasserstein_internal_p": 2,
            "n_h2_features": int(h2_ph["observed"]["n_h2_features"]),
            "total_persistence_h2": float(h2_ph["observed"]["total_persistence_h2"]),
            "markov1_null_p": float(h2_null["H2"]["p_value"]),
        },
        "positive_control": {
            "null": "markov-1",
            "seed": int(positive["params"]["seed"]),
            "frozen_loadings": True,
            "p_h0": p_h0,
            "p_h1": p_h1,
            "tolerance_band": [0.3, 0.7],
            "calibrated": 0.3 <= p_h0 <= 0.7 and 0.3 <= p_h1 <= 0.7,
        },
        "doubled_n_w2": {
            "n_perms": int(doubled["params"]["n_perms"]),
            "n_nullnull": int(doubled["params"]["n_nullnull"]),
            "L": int(doubled["params"]["L"]),
            "seed": int(doubled["params"]["seed"]),
            "markov_order": 1,
            "wasserstein_order": 2,
            "wasserstein_internal_p": 2,
            "p_value": float(doubled["result"]["h0"]["w2_pvalue"]),
            "h1_p_value": float(doubled["result"]["h1"]["w2_pvalue"]),
            "stable_vs_t1_2": bool(doubled["stability"]["stable_vs_t1_2"]),
            "per_pair_w2": doubled["per_pair_w2"],
        },
    }
    errors = validate_h2_positive_control_diagnostics_payload(payload)
    if errors:
        raise ValueError("diagnostics summary payload invalid: " + "; ".join(errors))
    out_path = args.worktree_root / H2_REL / f"diagnostics_summary_{args.run_date}.json"
    _write_json_no_overwrite(out_path, payload)
    LOGGER.info("Diagnostics summary JSON: %s", out_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run T1.5 auxiliary diagnostics.")
    parser.add_argument("command", choices=["h2", "positive-control", "doubled-n", "summary"])
    parser.add_argument("--proj-root", type=Path, default=PROJ_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=WORKTREE_ROOT)
    parser.add_argument("--run-date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-hours", type=float, default=24.0)
    parser.add_argument("--n-jobs", type=int, default=4)
    parser.add_argument("--L", type=int, default=5000)
    parser.add_argument("--B", type=int, default=100)
    parser.add_argument("--requested-L", type=int, default=2000)
    parser.add_argument("--fallback-reason", default=None)
    parser.add_argument("--n-perms", type=int, default=200)
    parser.add_argument("--n-nullnull", type=int, default=2000)
    parser.add_argument("--k-max", type=int, default=5)
    parser.add_argument("--n-points", type=int, default=200)
    parser.add_argument("--aggregate-jobs", type=int, default=4)
    parser.add_argument("--checkpoint-every", type=int, default=50)
    parser.add_argument("--estimate-h0-seconds", type=float, default=5.0)
    parser.add_argument("--estimate-h1-seconds", type=float, default=9.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--progress-path", type=Path)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument(
        "--cache-path",
        type=Path,
        default=PROJ_ROOT / "results/trajectory_tda_integration/stage1/cache/null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=PROJ_ROOT / "results/trajectory_tda_integration/stage1/usoc_headline_frozen_2026-05-28.json",
    )
    parser.add_argument("--h2-ph", type=Path)
    parser.add_argument("--h2-null", type=Path)
    parser.add_argument("--positive-control", type=Path)
    parser.add_argument("--doubled-n", type=Path)
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    _fill_doubled_monitoring_paths(args)
    _configure_file_logging(args)
    if args.command == "h2":
        run_h2(args)
    elif args.command == "positive-control":
        run_positive(args)
    elif args.command == "doubled-n":
        run_doubled(args)
    elif args.command == "summary":
        missing = [name for name in ("h2_ph", "h2_null", "positive_control", "doubled_n") if getattr(args, name) is None]
        if missing:
            raise ValueError(f"summary requires paths for: {', '.join(missing)}")
        build_summary(args)


if __name__ == "__main__":
    main()
