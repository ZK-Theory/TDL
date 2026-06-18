"""Exact spanning-vs-newcomer H0 inference for the T1.9b amendment.

The runner reuses the T1.9 matched sample and frozen full-checkpoint embedding.
Each stochastic draw recomputes full H0 diagrams for both 8,000-point groups,
then derives the single-epsilon Betti ratio, windowed normalized AUC ratio, and
Wasserstein-2 distance from those diagrams.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from trajectory_tda.scripts.stage1 import _battery_core as core
from trajectory_tda.scripts.stage1.run_spanning_betti_robustness import (
    DEFAULT_MATCHED_N,
    DEFAULT_SEED,
    EPS_STAR_LOCKED,
    EPS_STARS,
    FULL_CHECKPOINT_REL_DIR,
    OUTPUT_REL_DIR,
    _betti0_at_eps,
    _betti0_auc,
    _contains_forbidden_key,
    _finite_deaths,
    _git_head,
    _group_indices,
    _h0_diagram,
    _load_json,
    _load_or_rebuild_full_embedding,
    _sample_indices,
    _sha256_ints,
    _w2_h0,
)


SCHEMA_VERSION = "stage1/spanning-betti-inference/v1"
TASK_NAME = "T1.9b spanning vs newcomer H0 inferential re-analysis"
PRE_REGISTRATION = "2026-06-09 T1.9b pre-registration amendment"
STATISTICS = ["single_eps_ratio", "auc_ratio_windowed", "w2_matched"]
P_VALUE_FORMULA = "(r+1)/(B+1)"
P_VALUE_METHOD = (
    "ratios use abs(log(ratio)) against parity 1; W2 uses upper-tail distance"
)
DECISION_OUTCOMES = {
    "newcomers_robust",
    "spanning_robust",
    "no_robust_difference",
}
DEFAULT_B = 1000
DEFAULT_WORKERS = 4
MAX_WORKERS = 6
DEFAULT_CHUNK_SIZE = 25
DEFAULT_MAX_HOURS = 12.0
DEFAULT_MICRO_DRAWS = 8
OBSERVED_EQUIVALENCE_TOL = 1e-9
EPS_KEYS = [f"{eps:.2f}" for eps in EPS_STARS]

Lane = Literal["permutation", "bootstrap"]

logger = logging.getLogger(__name__)


def _eps_key(eps: float) -> str:
    return f"{eps:.2f}"


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _atomic_write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result: {path}")
    _atomic_write_json(path, payload)


def _load_checkpoint_file(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    draws = payload.get("draws")
    if not isinstance(draws, list):
        raise ValueError(f"Checkpoint missing draws list: {path}")
    return draws


def _windowed_normalized_auc(
    deaths: NDArray[np.float64],
    eps_lo: float,
    eps_hi: float,
    n_points: int,
) -> float:
    if eps_hi <= eps_lo:
        raise ValueError(f"eps_hi must exceed eps_lo, got {eps_hi} <= {eps_lo}")
    capped = np.minimum(deaths, eps_hi)
    contributions = np.maximum(capped - eps_lo, 0.0)
    # The surviving infinite H0 component contributes one component throughout.
    auc = (eps_hi - eps_lo) + float(contributions.sum())
    return float(auc / n_points)


def _compute_eps_lo(
    spanning_deaths: NDArray[np.float64],
    newcomer_deaths: NDArray[np.float64],
    matched_n: int,
) -> float:
    candidates = np.unique(np.concatenate([spanning_deaths, newcomer_deaths]))
    for eps in candidates:
        eps_float = float(eps)
        if eps_float <= 0.0:
            continue
        mean_beta0 = (
            _betti0_at_eps(spanning_deaths, eps_float)
            + _betti0_at_eps(newcomer_deaths, eps_float)
        ) / 2.0
        if mean_beta0 < matched_n / 2.0:
            return eps_float
    raise ValueError("Could not find eps_lo where mean beta0 drops below n/2")


def _stats_from_diagrams(
    spanning_dgm: NDArray[np.float64],
    newcomer_dgm: NDArray[np.float64],
    *,
    eps_lo: float,
    matched_n: int,
) -> dict[str, Any]:
    spanning_deaths = _finite_deaths(spanning_dgm)
    newcomer_deaths = _finite_deaths(newcomer_dgm)

    single_eps_ratio_by_eps: dict[str, float] = {}
    auc_ratio_windowed_by_eps: dict[str, float] = {}
    counts_by_eps: dict[str, dict[str, int]] = {}
    auc_by_eps: dict[str, dict[str, float]] = {}
    full_auc_ratio_by_eps: dict[str, float] = {}

    for eps in EPS_STARS:
        key = _eps_key(eps)
        span_beta = _betti0_at_eps(spanning_deaths, eps)
        new_beta = _betti0_at_eps(newcomer_deaths, eps)
        span_window_auc = _windowed_normalized_auc(
            spanning_deaths,
            eps_lo,
            eps,
            matched_n,
        )
        new_window_auc = _windowed_normalized_auc(
            newcomer_deaths,
            eps_lo,
            eps,
            matched_n,
        )
        span_full_auc = _betti0_auc(spanning_deaths, eps)
        new_full_auc = _betti0_auc(newcomer_deaths, eps)

        single_eps_ratio_by_eps[key] = float(new_beta / span_beta)
        auc_ratio_windowed_by_eps[key] = float(new_window_auc / span_window_auc)
        full_auc_ratio_by_eps[key] = float(new_full_auc / span_full_auc)
        counts_by_eps[key] = {
            "spanning_beta0": int(span_beta),
            "newcomer_beta0": int(new_beta),
        }
        auc_by_eps[key] = {
            "spanning_auc_windowed_normalized": float(span_window_auc),
            "newcomer_auc_windowed_normalized": float(new_window_auc),
            "spanning_auc_full": float(span_full_auc),
            "newcomer_auc_full": float(new_full_auc),
        }

    return {
        "single_eps_ratio_by_eps": single_eps_ratio_by_eps,
        "auc_ratio_windowed_by_eps": auc_ratio_windowed_by_eps,
        "full_auc_ratio_by_eps": full_auc_ratio_by_eps,
        "counts_by_eps": counts_by_eps,
        "auc_by_eps": auc_by_eps,
        "w2_matched": _w2_h0(newcomer_dgm, spanning_dgm),
    }


def _compute_pair_stats(
    embeddings: NDArray[np.float64],
    spanning_idx: NDArray[np.int64],
    newcomer_idx: NDArray[np.int64],
    *,
    eps_lo: float,
    matched_n: int,
) -> dict[str, Any]:
    spanning_points = np.asarray(embeddings[spanning_idx], dtype=np.float64)
    newcomer_points = np.asarray(embeddings[newcomer_idx], dtype=np.float64)
    spanning_dgm = _h0_diagram(spanning_points)
    newcomer_dgm = _h0_diagram(newcomer_points)
    return _stats_from_diagrams(
        spanning_dgm,
        newcomer_dgm,
        eps_lo=eps_lo,
        matched_n=matched_n,
    )


def _seed_sequence_for_draw(master_seed: int, spawn_index: int) -> np.random.SeedSequence:
    return np.random.SeedSequence(master_seed, spawn_key=(spawn_index,))


def _draw_worker(
    *,
    lane: Lane,
    draw_index: int,
    spawn_index: int,
    embedding_cache_path: str,
    spanning_idx: NDArray[np.int64],
    newcomer_idx: NDArray[np.int64],
    eps_lo: float,
    matched_n: int,
    master_seed: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    embeddings = np.load(embedding_cache_path, mmap_mode="r")
    seed_sequence = _seed_sequence_for_draw(master_seed, spawn_index)
    rng = np.random.default_rng(seed_sequence)

    if lane == "permutation":
        pooled = np.concatenate([spanning_idx, newcomer_idx])
        shuffled = rng.permutation(pooled)
        draw_spanning_idx = np.asarray(shuffled[:matched_n], dtype=np.int64)
        draw_newcomer_idx = np.asarray(shuffled[matched_n:], dtype=np.int64)
    elif lane == "bootstrap":
        draw_spanning_idx = rng.choice(spanning_idx, size=matched_n, replace=True)
        draw_newcomer_idx = rng.choice(newcomer_idx, size=matched_n, replace=True)
    else:
        raise ValueError(f"Unknown lane: {lane}")

    stats = _compute_pair_stats(
        embeddings,
        draw_spanning_idx,
        draw_newcomer_idx,
        eps_lo=eps_lo,
        matched_n=matched_n,
    )
    return {
        "lane": lane,
        "draw_index": int(draw_index),
        "seed_entropy": int(master_seed),
        "seed_spawn_key": [int(spawn_index)],
        "single_eps_ratio_by_eps": stats["single_eps_ratio_by_eps"],
        "auc_ratio_windowed_by_eps": stats["auc_ratio_windowed_by_eps"],
        "w2_matched": float(stats["w2_matched"]),
        "elapsed_s": float(time.perf_counter() - started),
    }


def _existing_draws(checkpoint_dir: Path, lane: Lane) -> dict[int, dict[str, Any]]:
    existing: dict[int, dict[str, Any]] = {}
    for path in sorted(checkpoint_dir.glob(f"{lane}_draws_*.json")):
        for draw in _load_checkpoint_file(path):
            idx = int(draw["draw_index"])
            if idx in existing:
                raise ValueError(f"Duplicate {lane} draw index {idx} in checkpoints")
            existing[idx] = draw
    return existing


def _checkpoint_path(
    checkpoint_dir: Path,
    lane: Lane,
    chunk_start: int,
    chunk_end: int,
) -> Path:
    return checkpoint_dir / f"{lane}_draws_{chunk_start:04d}_{chunk_end - 1:04d}.json"


def _write_progress(
    checkpoint_dir: Path,
    *,
    run_id: str,
    progress: dict[str, Any],
) -> Path:
    path = checkpoint_dir / "progress.json"
    payload = {
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **progress,
    }
    _atomic_write_json(path, payload)
    return path


def _load_progress(checkpoint_dir: Path) -> dict[str, Any] | None:
    path = checkpoint_dir / "progress.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _run_lane(
    *,
    lane: Lane,
    b_draws: int,
    checkpoint_dir: Path,
    run_id: str,
    resume: bool,
    workers: int,
    chunk_size: int,
    embedding_cache_path: Path,
    spanning_idx: NDArray[np.int64],
    newcomer_idx: NDArray[np.int64],
    eps_lo: float,
    matched_n: int,
    master_seed: int,
    spawn_offset: int,
) -> list[dict[str, Any]]:
    from joblib import Parallel, delayed

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    existing = _existing_draws(checkpoint_dir, lane) if resume else {}
    if not resume and _existing_draws(checkpoint_dir, lane):
        raise FileExistsError(
            f"{lane} checkpoints already exist in {checkpoint_dir}; use --resume"
        )

    missing = [idx for idx in range(b_draws) if idx not in existing]
    t_lane = time.perf_counter()
    with Parallel(n_jobs=workers, verbose=10 if workers != 1 else 0) as parallel:
        for chunk_start in range(0, len(missing), chunk_size):
            chunk_indices = missing[chunk_start : chunk_start + chunk_size]
            if not chunk_indices:
                continue
            chunk_draws = list(
                parallel(
                    delayed(_draw_worker)(
                        lane=lane,
                        draw_index=idx,
                        spawn_index=spawn_offset + idx,
                        embedding_cache_path=str(embedding_cache_path),
                        spanning_idx=spanning_idx,
                        newcomer_idx=newcomer_idx,
                        eps_lo=eps_lo,
                        matched_n=matched_n,
                        master_seed=master_seed,
                    )
                    for idx in chunk_indices
                )
            )
            first_idx = min(chunk_indices)
            last_idx = max(chunk_indices) + 1
            _atomic_write_json(
                _checkpoint_path(checkpoint_dir, lane, first_idx, last_idx),
                {
                    "lane": lane,
                    "chunk": [first_idx, last_idx],
                    "draws": chunk_draws,
                },
            )
            for draw in chunk_draws:
                existing[int(draw["draw_index"])] = draw
            _write_progress(
                checkpoint_dir,
                run_id=run_id,
                progress={
                    "status": "running",
                    "current_lane": lane,
                    "completed": {
                        "permutation": len(_existing_draws(checkpoint_dir, "permutation")),
                        "bootstrap": len(_existing_draws(checkpoint_dir, "bootstrap")),
                    },
                    "workers": workers,
                    "chunk_size": chunk_size,
                    "elapsed_current_lane_s": time.perf_counter() - t_lane,
                },
            )

    if len(existing) != b_draws:
        raise RuntimeError(f"{lane} lane incomplete: {len(existing)} != {b_draws}")
    return [existing[idx] for idx in sorted(existing)]


def _run_micro_benchmark(
    *,
    checkpoint_dir: Path,
    run_id: str,
    micro_draws: int,
    workers: int,
    embedding_cache_path: Path,
    spanning_idx: NDArray[np.int64],
    newcomer_idx: NDArray[np.int64],
    eps_lo: float,
    matched_n: int,
    master_seed: int,
    b_permutation: int,
    b_bootstrap: int,
) -> dict[str, Any]:
    from joblib import Parallel, delayed

    if micro_draws < 1:
        raise ValueError("micro_draws must be positive")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    n_perm = max(1, micro_draws // 2)
    n_boot = max(1, micro_draws - n_perm)
    jobs = []
    for idx in range(n_perm):
        jobs.append(
            dict(lane="permutation", draw_index=idx, spawn_index=idx)
        )
    for idx in range(n_boot):
        jobs.append(
            dict(
                lane="bootstrap",
                draw_index=idx,
                spawn_index=b_permutation + idx,
            )
        )

    started = time.perf_counter()
    with Parallel(n_jobs=workers, verbose=10 if workers != 1 else 0) as parallel:
        draws = list(
            parallel(
                delayed(_draw_worker)(
                    lane=job["lane"],
                    draw_index=job["draw_index"],
                    spawn_index=job["spawn_index"],
                    embedding_cache_path=str(embedding_cache_path),
                    spanning_idx=spanning_idx,
                    newcomer_idx=newcomer_idx,
                    eps_lo=eps_lo,
                    matched_n=matched_n,
                    master_seed=master_seed,
                )
                for job in jobs
            )
        )
    elapsed_s = time.perf_counter() - started
    total_draws = b_permutation + b_bootstrap
    projected_hours = (elapsed_s / len(draws)) * total_draws / 3600.0
    benchmark = {
        "micro_draws": len(draws),
        "permutation_micro_draws": n_perm,
        "bootstrap_micro_draws": n_boot,
        "workers": workers,
        "elapsed_s": elapsed_s,
        "mean_effective_wall_s_per_draw": elapsed_s / len(draws),
        "projected_total_draws": total_draws,
        "projected_wall_hours_at_workers": projected_hours,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write_json(
        checkpoint_dir / "micro_benchmark.json",
        {"benchmark": benchmark, "draws": draws},
    )
    progress = _load_progress(checkpoint_dir) or {}
    progress["micro_benchmark"] = benchmark
    progress["status"] = "benchmarked"
    _write_progress(checkpoint_dir, run_id=run_id, progress=progress)
    return benchmark


def _load_or_run_micro_benchmark(
    *,
    checkpoint_dir: Path,
    run_id: str,
    micro_draws: int,
    workers: int,
    embedding_cache_path: Path,
    spanning_idx: NDArray[np.int64],
    newcomer_idx: NDArray[np.int64],
    eps_lo: float,
    matched_n: int,
    master_seed: int,
    b_permutation: int,
    b_bootstrap: int,
    resume: bool,
) -> dict[str, Any]:
    progress = _load_progress(checkpoint_dir) if resume else None
    benchmark = (progress or {}).get("micro_benchmark")
    if isinstance(benchmark, dict):
        return benchmark
    return _run_micro_benchmark(
        checkpoint_dir=checkpoint_dir,
        run_id=run_id,
        micro_draws=micro_draws,
        workers=workers,
        embedding_cache_path=embedding_cache_path,
        spanning_idx=spanning_idx,
        newcomer_idx=newcomer_idx,
        eps_lo=eps_lo,
        matched_n=matched_n,
        master_seed=master_seed,
        b_permutation=b_permutation,
        b_bootstrap=b_bootstrap,
    )


def _empirical_p_value(
    observed: float,
    null_values: NDArray[np.float64],
    statistic: str,
) -> tuple[float, int]:
    if null_values.size == 0:
        raise ValueError("null_values must be non-empty")
    if statistic in {"single_eps_ratio", "auc_ratio_windowed"}:
        if observed <= 0.0 or np.any(null_values <= 0.0):
            raise ValueError(f"{statistic} p-value requires positive ratios")
        observed_extreme = abs(math.log(observed))
        null_extreme = np.abs(np.log(null_values))
    elif statistic == "w2_matched":
        observed_extreme = float(observed)
        null_extreme = null_values
    else:
        raise ValueError(f"Unknown statistic: {statistic}")
    r = int(np.sum(null_extreme >= observed_extreme - 1e-15))
    return float((r + 1) / (len(null_values) + 1)), r


def _percentile_ci(values: NDArray[np.float64]) -> list[float]:
    if values.size == 0:
        raise ValueError("Cannot compute a percentile CI from no values")
    lo, hi = np.percentile(values, [2.5, 97.5], method="linear")
    return [float(lo), float(hi)]


def _draw_values(
    draws: list[dict[str, Any]],
    statistic: str,
    eps: float | None = None,
) -> NDArray[np.float64]:
    if statistic == "w2_matched":
        return np.asarray([float(draw["w2_matched"]) for draw in draws], dtype=np.float64)
    if eps is None:
        raise ValueError(f"eps is required for {statistic}")
    key = _eps_key(eps)
    return np.asarray(
        [float(draw[f"{statistic}_by_eps"][key]) for draw in draws],
        dtype=np.float64,
    )


def _ci_excludes_parity(ci: list[float]) -> bool:
    return bool(ci[1] < 1.0 or ci[0] > 1.0)


def summarize_inference(
    *,
    observed: dict[str, Any],
    permutation_draws: list[dict[str, Any]],
    bootstrap_draws: list[dict[str, Any]],
    alpha: float = 0.05,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for eps in EPS_STARS:
        key = _eps_key(eps)
        obs_single = float(observed["single_eps_ratio_by_eps"][key])
        obs_auc = float(observed["auc_ratio_windowed_by_eps"][key])
        obs_w2 = float(observed["w2_matched"])

        single_null = _draw_values(permutation_draws, "single_eps_ratio", eps)
        auc_null = _draw_values(permutation_draws, "auc_ratio_windowed", eps)
        w2_null = _draw_values(permutation_draws, "w2_matched")
        single_boot = _draw_values(bootstrap_draws, "single_eps_ratio", eps)
        auc_boot = _draw_values(bootstrap_draws, "auc_ratio_windowed", eps)

        single_p, single_r = _empirical_p_value(
            obs_single,
            single_null,
            "single_eps_ratio",
        )
        auc_p, auc_r = _empirical_p_value(obs_auc, auc_null, "auc_ratio_windowed")
        w2_p, w2_r = _empirical_p_value(obs_w2, w2_null, "w2_matched")

        row = {
            "eps_star": float(eps),
            "single_eps_ratio": obs_single,
            "single_eps_perm_p": single_p,
            "single_eps_perm_extreme_count": single_r,
            "single_eps_boot_ci": _percentile_ci(single_boot),
            "auc_ratio_windowed": obs_auc,
            "auc_perm_p": auc_p,
            "auc_perm_extreme_count": auc_r,
            "auc_boot_ci": _percentile_ci(auc_boot),
            "w2_matched": obs_w2,
            "w2_perm_p": w2_p,
            "w2_perm_extreme_count": w2_r,
            "pvalue_null_draws": len(permutation_draws),
            "direction_newcomers_gt": bool(obs_auc > 1.0),
        }
        rows.append(row)

    locked = next(row for row in rows if row["eps_star"] == EPS_STAR_LOCKED)
    directions = [float(row["auc_ratio_windowed"]) for row in rows]
    all_newcomer_gt = all(value > 1.0 for value in directions)
    all_spanning_gt = all(value < 1.0 for value in directions)
    direction_consistent = bool(all_newcomer_gt or all_spanning_gt)
    significant_at_locked = bool(locked["auc_perm_p"] < alpha)
    bootstrap_ci_excludes_parity = _ci_excludes_parity(locked["auc_boot_ci"])
    dual_metric_satisfied = bool(locked["w2_perm_p"] < alpha)
    directional_claim_allowed = bool(
        significant_at_locked
        and bootstrap_ci_excludes_parity
        and direction_consistent
        and dual_metric_satisfied
    )

    if directional_claim_allowed and all_newcomer_gt:
        outcome = "newcomers_robust"
    elif directional_claim_allowed and all_spanning_gt:
        outcome = "spanning_robust"
    else:
        outcome = "no_robust_difference"

    decision = {
        "outcome": outcome,
        "significant_at_locked": significant_at_locked,
        "bootstrap_ci_excludes_parity_at_locked": bootstrap_ci_excludes_parity,
        "direction_consistent": direction_consistent,
        "dual_metric_satisfied": dual_metric_satisfied,
        "locked_eps_star": EPS_STAR_LOCKED,
        "alpha": alpha,
        "rule": (
            "A directional outcome requires locked-epsilon windowed AUC "
            "p < alpha, locked-epsilon bootstrap CI excluding parity, AUC "
            "direction consistency across all epsilon-star values, and "
            "significant W2 evidence. Otherwise outcome is no_robust_difference."
        ),
        "headline": (
            "Mechanical T1.9b outcome only; manuscript-facing prose lock is "
            "deferred to Manager review."
        ),
    }
    return rows, decision


def _validate_eps_mapping(
    value: object,
    *,
    path: str,
    positive: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{path} must be a dict"]
    if sorted(value) != sorted(EPS_KEYS):
        errors.append(f"{path} must contain epsilon keys {EPS_KEYS}")
        return errors
    for key in EPS_KEYS:
        if not _is_finite_number(value.get(key)):
            errors.append(f"{path}.{key} must be finite numeric")
        elif positive and float(value[key]) <= 0.0:
            errors.append(f"{path}.{key} must be positive")
    return errors


def _validate_ci(value: object, path: str) -> list[str]:
    if not isinstance(value, list) or len(value) != 2:
        return [f"{path} must be a two-element list"]
    if not all(_is_finite_number(v) for v in value):
        return [f"{path} must contain finite numbers"]
    if float(value[0]) > float(value[1]):
        return [f"{path} lower bound must be <= upper bound"]
    return []


def _validate_per_draw(
    draws: object,
    *,
    lane: Lane,
    expected_len: int,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(draws, list):
        return [f"per_draw.{lane} must be a list"]
    if len(draws) != expected_len:
        errors.append(f"per_draw.{lane} length must equal {expected_len}")
    seen: set[int] = set()
    for i, draw in enumerate(draws):
        if not isinstance(draw, dict):
            errors.append(f"per_draw.{lane}[{i}] must be a dict")
            continue
        if draw.get("lane") != lane:
            errors.append(f"per_draw.{lane}[{i}].lane must be {lane!r}")
        idx = draw.get("draw_index")
        if not isinstance(idx, int):
            errors.append(f"per_draw.{lane}[{i}].draw_index must be int")
        elif idx in seen:
            errors.append(f"per_draw.{lane}[{i}].draw_index is duplicated")
        else:
            seen.add(idx)
        spawn_key = draw.get("seed_spawn_key")
        if (
            not isinstance(spawn_key, list)
            or len(spawn_key) != 1
            or not isinstance(spawn_key[0], int)
        ):
            errors.append(f"per_draw.{lane}[{i}].seed_spawn_key must be [int]")
        errors.extend(
            _validate_eps_mapping(
                draw.get("single_eps_ratio_by_eps"),
                path=f"per_draw.{lane}[{i}].single_eps_ratio_by_eps",
            )
        )
        errors.extend(
            _validate_eps_mapping(
                draw.get("auc_ratio_windowed_by_eps"),
                path=f"per_draw.{lane}[{i}].auc_ratio_windowed_by_eps",
            )
        )
        if not _is_finite_number(draw.get("w2_matched")):
            errors.append(f"per_draw.{lane}[{i}].w2_matched must be finite")
        elif float(draw["w2_matched"]) < 0.0:
            errors.append(f"per_draw.{lane}[{i}].w2_matched must be non-negative")
    return errors


def validate_spanning_betti_inference_payload(payload: dict[str, Any]) -> list[str]:
    """Return schema-contract validation errors for a T1.9b inference payload."""
    errors: list[str] = []
    required = [
        "schema_version",
        "generated_at",
        "task",
        "pre_registration",
        "inputs",
        "params",
        "observed",
        "results",
        "per_draw",
        "decision",
    ]
    for key in required:
        if key not in payload:
            errors.append(f"missing required key: {key}")

    if _contains_forbidden_key(payload, "per_call_pca"):
        errors.append("forbidden key present: per_call_pca")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if payload.get("task") != TASK_NAME:
        errors.append(f"task must be {TASK_NAME!r}")
    if "2026-06-09" not in str(payload.get("pre_registration", "")):
        errors.append("pre_registration must reference 2026-06-09")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs must be a dict")
    else:
        for key in (
            "spanning_source",
            "newcomer_source",
            "t19_result_source",
            "pre_registration_source",
            "git_head",
        ):
            if not inputs.get(key):
                errors.append(f"inputs.{key} is required")

    params = payload.get("params")
    b_perm = b_boot = None
    if not isinstance(params, dict):
        errors.append("params must be a dict")
    else:
        if params.get("matched_sample_size") != DEFAULT_MATCHED_N:
            errors.append(f"params.matched_sample_size must equal {DEFAULT_MATCHED_N}")
        if params.get("eps_stars") != EPS_STARS:
            errors.append(f"params.eps_stars must equal {EPS_STARS}")
        if params.get("eps_star_locked") != EPS_STAR_LOCKED:
            errors.append(f"params.eps_star_locked must equal {EPS_STAR_LOCKED}")
        b_perm = params.get("B_permutation")
        b_boot = params.get("B_bootstrap")
        if not isinstance(b_perm, int) or b_perm < DEFAULT_B:
            errors.append(f"params.B_permutation must be >= {DEFAULT_B}")
        if not isinstance(b_boot, int) or b_boot < DEFAULT_B:
            errors.append(f"params.B_bootstrap must be >= {DEFAULT_B}")
        if params.get("seed") != DEFAULT_SEED:
            errors.append(f"params.seed must equal {DEFAULT_SEED}")
        if params.get("dual_metric") is not True:
            errors.append("params.dual_metric must be true")
        if not _is_finite_number(params.get("eps_lo")) or float(params.get("eps_lo", 0)) <= 0:
            errors.append("params.eps_lo must be a positive finite float")
        if params.get("p_value_formula") != P_VALUE_FORMULA:
            errors.append(f"params.p_value_formula must equal {P_VALUE_FORMULA!r}")
        if params.get("statistics") != STATISTICS:
            errors.append(f"params.statistics must equal {STATISTICS}")

    observed = payload.get("observed")
    if not isinstance(observed, dict):
        errors.append("observed must be a dict")
    else:
        errors.extend(
            _validate_eps_mapping(
                observed.get("single_eps_ratio_by_eps"),
                path="observed.single_eps_ratio_by_eps",
            )
        )
        errors.extend(
            _validate_eps_mapping(
                observed.get("auc_ratio_windowed_by_eps"),
                path="observed.auc_ratio_windowed_by_eps",
            )
        )
        if not _is_finite_number(observed.get("w2_matched")):
            errors.append("observed.w2_matched must be finite")
        elif float(observed["w2_matched"]) < 0.0:
            errors.append("observed.w2_matched must be non-negative")

    per_draw = payload.get("per_draw")
    permutation_draws: list[dict[str, Any]] = []
    bootstrap_draws: list[dict[str, Any]] = []
    if not isinstance(per_draw, dict):
        errors.append("per_draw must be a dict")
    elif isinstance(b_perm, int) and isinstance(b_boot, int):
        permutation_draws = per_draw.get("permutation", [])
        bootstrap_draws = per_draw.get("bootstrap", [])
        errors.extend(
            _validate_per_draw(
                permutation_draws,
                lane="permutation",
                expected_len=b_perm,
            )
        )
        errors.extend(
            _validate_per_draw(
                bootstrap_draws,
                lane="bootstrap",
                expected_len=b_boot,
            )
        )

    results = payload.get("results")
    if not isinstance(results, list):
        errors.append("results must be a list")
        results = []
    if len(results) != len(EPS_STARS):
        errors.append("results must contain exactly one entry per epsilon-star")
    eps_seen: list[float] = []
    for i, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"results[{i}] must be a dict")
            continue
        try:
            eps = float(row["eps_star"])
            eps_seen.append(eps)
        except (KeyError, TypeError, ValueError):
            errors.append(f"results[{i}].eps_star is required and numeric")
            continue
        for key in (
            "single_eps_ratio",
            "single_eps_perm_p",
            "auc_ratio_windowed",
            "auc_perm_p",
            "w2_matched",
            "w2_perm_p",
        ):
            if not _is_finite_number(row.get(key)):
                errors.append(f"results[{i}].{key} must be finite numeric")
        for key in ("single_eps_perm_p", "auc_perm_p", "w2_perm_p"):
            if _is_finite_number(row.get(key)) and not 0.0 <= float(row[key]) <= 1.0:
                errors.append(f"results[{i}].{key} must be in [0, 1]")
        if _is_finite_number(row.get("w2_matched")) and float(row["w2_matched"]) < 0.0:
            errors.append(f"results[{i}].w2_matched must be non-negative")
        errors.extend(_validate_ci(row.get("single_eps_boot_ci"), f"results[{i}].single_eps_boot_ci"))
        errors.extend(_validate_ci(row.get("auc_boot_ci"), f"results[{i}].auc_boot_ci"))
        if not isinstance(row.get("direction_newcomers_gt"), bool):
            errors.append(f"results[{i}].direction_newcomers_gt must be bool")

    if sorted(eps_seen) != sorted(EPS_STARS) or len(eps_seen) != len(set(eps_seen)):
        errors.append("results must contain exactly the locked epsilon-star set")

    decision = payload.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be a dict")
    else:
        outcome = decision.get("outcome")
        if outcome not in DECISION_OUTCOMES:
            errors.append("decision.outcome must be one of the allowed outcomes")
        for key in (
            "significant_at_locked",
            "bootstrap_ci_excludes_parity_at_locked",
            "direction_consistent",
            "dual_metric_satisfied",
        ):
            if not isinstance(decision.get(key), bool):
                errors.append(f"decision.{key} must be bool")
        if not isinstance(decision.get("headline"), str) or not decision.get("headline"):
            errors.append("decision.headline must be a non-empty string")
        if not _is_finite_number(decision.get("alpha")):
            errors.append("decision.alpha must be finite numeric")
        if outcome in {"newcomers_robust", "spanning_robust"}:
            for key in (
                "significant_at_locked",
                "bootstrap_ci_excludes_parity_at_locked",
                "direction_consistent",
                "dual_metric_satisfied",
            ):
                if decision.get(key) is not True:
                    errors.append(f"directional outcome requires decision.{key}")
        if (
            outcome == "no_robust_difference"
            and decision.get("significant_at_locked") is True
            and decision.get("bootstrap_ci_excludes_parity_at_locked") is True
            and decision.get("direction_consistent") is True
            and decision.get("dual_metric_satisfied") is True
        ):
            errors.append("no_robust_difference contradicts satisfied directional gates")

    if not errors and permutation_draws and bootstrap_draws and isinstance(observed, dict):
        recomputed_rows, recomputed_decision = summarize_inference(
            observed=observed,
            permutation_draws=permutation_draws,
            bootstrap_draws=bootstrap_draws,
            alpha=float(payload["decision"]["alpha"]),
        )
        for idx, (actual, expected) in enumerate(zip(results, recomputed_rows, strict=True)):
            for key in (
                "single_eps_perm_p",
                "auc_perm_p",
                "w2_perm_p",
            ):
                if not math.isclose(float(actual[key]), float(expected[key]), abs_tol=1e-12):
                    errors.append(f"results[{idx}].{key} does not match per_draw recomputation")
            for key in ("single_eps_boot_ci", "auc_boot_ci"):
                for j in range(2):
                    if not math.isclose(
                        float(actual[key][j]),
                        float(expected[key][j]),
                        abs_tol=1e-12,
                    ):
                        errors.append(f"results[{idx}].{key} does not match per_draw recomputation")
        if decision.get("outcome") != recomputed_decision["outcome"]:
            errors.append("decision.outcome does not match mechanical recomputation")

    return errors


def dispatches_spanning_betti_inference_json(path: Path) -> bool:
    """Return True for T1.9b inference JSONs covered by the dispatch contract."""
    rel = path.as_posix()
    return (
        rel.startswith(OUTPUT_REL_DIR.as_posix() + "/")
        and path.name.startswith("spanning_betti_inference_")
        and path.suffix == ".json"
    )


def prepare_context(
    *,
    repo_root: Path,
    matched_n: int,
    seed: int,
) -> dict[str, Any]:
    metadata_path = repo_root / FULL_CHECKPOINT_REL_DIR / "01_trajectories.json"
    metadata_payload = _load_json(metadata_path)
    metadata = metadata_payload["metadata"]
    embeddings, cache_info = _load_or_rebuild_full_embedding(
        worktree_checkpoint=repo_root / FULL_CHECKPOINT_REL_DIR,
        proj_checkpoint=core.proj_root() / FULL_CHECKPOINT_REL_DIR,
    )
    embedding_cache_path = Path(cache_info["embedding_cache"])
    if not embedding_cache_path.exists():
        raise FileNotFoundError(f"Embedding cache missing: {embedding_cache_path}")

    spanning_all = _group_indices(metadata, "spanning")
    newcomer_all = _group_indices(metadata, "usoc_only")
    actual_n = min(matched_n, len(spanning_all), len(newcomer_all))
    if actual_n != DEFAULT_MATCHED_N:
        raise ValueError(f"T1.9b requires matched n={DEFAULT_MATCHED_N}; got {actual_n}")
    spanning_idx = _sample_indices(spanning_all, actual_n, seed, offset=101)
    newcomer_idx = _sample_indices(newcomer_all, actual_n, seed, offset=202)
    return {
        "metadata_path": metadata_path,
        "embeddings": embeddings,
        "embedding_cache_path": embedding_cache_path,
        "embedding_cache_info": cache_info,
        "spanning_population_n": int(len(spanning_all)),
        "newcomer_population_n": int(len(newcomer_all)),
        "spanning_idx": spanning_idx,
        "newcomer_idx": newcomer_idx,
        "matched_n": actual_n,
    }


def compute_observed(context: dict[str, Any]) -> dict[str, Any]:
    spanning_idx = context["spanning_idx"]
    newcomer_idx = context["newcomer_idx"]
    embeddings = context["embeddings"]
    matched_n = int(context["matched_n"])
    spanning_dgm = _h0_diagram(embeddings[spanning_idx])
    newcomer_dgm = _h0_diagram(embeddings[newcomer_idx])
    eps_lo = _compute_eps_lo(
        _finite_deaths(spanning_dgm),
        _finite_deaths(newcomer_dgm),
        matched_n,
    )
    observed = _stats_from_diagrams(
        spanning_dgm,
        newcomer_dgm,
        eps_lo=eps_lo,
        matched_n=matched_n,
    )
    observed["eps_lo"] = eps_lo
    observed["spanning_sample_sha256"] = _sha256_ints(spanning_idx)
    observed["newcomer_sample_sha256"] = _sha256_ints(newcomer_idx)
    return observed


def observed_equivalence_gate(observed: dict[str, Any]) -> dict[str, Any]:
    expected_counts = {
        "0.54": {"spanning_beta0": 30, "newcomer_beta0": 48},
        "0.65": {"spanning_beta0": 8, "newcomer_beta0": 12},
        "0.70": {"spanning_beta0": 4, "newcomer_beta0": 5},
        "0.80": {"spanning_beta0": 2, "newcomer_beta0": 3},
    }
    expected_full_auc = {
        "0.54": 0.9378960191104395,
        "0.65": 0.9389603600755404,
        "0.70": 0.9391089908592571,
        "0.80": 0.939175680699411,
    }
    expected_w2 = 2.536260410018281
    errors: list[str] = []
    for key in EPS_KEYS:
        if observed["counts_by_eps"][key] != expected_counts[key]:
            errors.append(
                f"counts at eps {key}: {observed['counts_by_eps'][key]} != "
                f"{expected_counts[key]}"
            )
        if not math.isclose(
            float(observed["full_auc_ratio_by_eps"][key]),
            expected_full_auc[key],
            rel_tol=0.0,
            abs_tol=OBSERVED_EQUIVALENCE_TOL,
        ):
            errors.append(
                f"full AUC ratio at eps {key}: "
                f"{observed['full_auc_ratio_by_eps'][key]} != "
                f"{expected_full_auc[key]}"
            )
    if not math.isclose(
        float(observed["w2_matched"]),
        expected_w2,
        rel_tol=0.0,
        abs_tol=OBSERVED_EQUIVALENCE_TOL,
    ):
        errors.append(f"W2: {observed['w2_matched']} != {expected_w2}")
    return {
        "passed": not errors,
        "errors": errors,
        "tolerance": OBSERVED_EQUIVALENCE_TOL,
        "expected_counts": expected_counts,
        "expected_full_auc_ratio_by_eps": expected_full_auc,
        "expected_w2": expected_w2,
    }


def build_payload(
    *,
    repo_root: Path,
    context: dict[str, Any],
    observed: dict[str, Any],
    equivalence_gate: dict[str, Any],
    permutation_draws: list[dict[str, Any]],
    bootstrap_draws: list[dict[str, Any]],
    run_id: str,
    checkpoint_dir: Path,
    progress_path: Path,
    benchmark: dict[str, Any],
    workers: int,
    chunk_size: int,
    started_at: float,
) -> dict[str, Any]:
    results, decision = summarize_inference(
        observed=observed,
        permutation_draws=permutation_draws,
        bootstrap_draws=bootstrap_draws,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "spanning_source": (
                "results/trajectory_tda_full/01_trajectories.json::"
                "metadata.survey_era == 'spanning'"
            ),
            "newcomer_source": (
                "results/trajectory_tda_full/01_trajectories.json::"
                "metadata.survey_era == 'usoc_only'"
            ),
            "t19_result_source": (
                "results/trajectory_tda_spanning/knee_robustness/"
                "spanning_AUC_W2_2026-06-09.json"
            ),
            "pre_registration_source": (
                "results/trajectory_tda_spanning/knee_robustness/"
                "pre_registrations_2026-06-09.json"
            ),
            "git_head": _git_head(repo_root),
            "full_embedding_cache": context["embedding_cache_info"],
        },
        "params": {
            "matched_sample_size": DEFAULT_MATCHED_N,
            "eps_stars": EPS_STARS,
            "eps_star_locked": EPS_STAR_LOCKED,
            "B_permutation": len(permutation_draws),
            "B_bootstrap": len(bootstrap_draws),
            "seed": DEFAULT_SEED,
            "seed_sequence": {
                "scheme": "np.random.SeedSequence(seed, spawn_key=(spawn_index,))",
                "master_seed": DEFAULT_SEED,
                "permutation_spawn_index_range": [0, len(permutation_draws) - 1],
                "bootstrap_spawn_index_range": [
                    len(permutation_draws),
                    len(permutation_draws) + len(bootstrap_draws) - 1,
                ],
            },
            "statistics": STATISTICS,
            "p_value_formula": P_VALUE_FORMULA,
            "p_value_method": P_VALUE_METHOD,
            "bootstrap_ci": "95% percentile, numpy.percentile method='linear'",
            "alpha": 0.05,
            "dual_metric": True,
            "eps_lo": float(observed["eps_lo"]),
            "homology_dimension": "H0",
            "frozen_loadings": True,
            "pca_scope": "single full-checkpoint PCA basis; no per-draw PCA refit",
            "w2_order": 2,
            "w2_internal_p": 2,
            "workers": workers,
            "chunk_size": chunk_size,
            "run_id": run_id,
            "wall_time_s": time.perf_counter() - started_at,
            "checkpoint_dir": str(checkpoint_dir),
            "progress_path": str(progress_path),
            "regeneration_command": (
                "uv run --extra wasserstein python trajectory_tda/scripts/stage1/"
                "run_spanning_betti_inference.py --run-full --resume "
                f"--run-id {run_id} --workers {workers}"
            ),
            "micro_benchmark": benchmark,
        },
        "observed": {
            **observed,
            "equivalence_gate": equivalence_gate,
        },
        "results": results,
        "per_draw": {
            "permutation": permutation_draws,
            "bootstrap": bootstrap_draws,
        },
        "decision": decision,
    }
    errors = validate_spanning_betti_inference_payload(payload)
    if errors:
        raise ValueError("Inference payload failed validation:\n  " + "\n  ".join(errors))
    return payload


def _validate_args(args: argparse.Namespace) -> None:
    if args.seed != DEFAULT_SEED:
        raise ValueError(f"T1.9b seed is locked to {DEFAULT_SEED}")
    if args.matched_n != DEFAULT_MATCHED_N:
        raise ValueError(f"T1.9b matched_n is locked to {DEFAULT_MATCHED_N}")
    if args.workers < 1 or args.workers > MAX_WORKERS:
        raise ValueError(f"--workers must be in [1, {MAX_WORKERS}]")
    if args.b_permutation < DEFAULT_B or args.b_bootstrap < DEFAULT_B:
        raise ValueError(f"Final T1.9b B values must be >= {DEFAULT_B}")
    if args.chunk_size < 1:
        raise ValueError("--chunk-size must be positive")
    if args.micro_benchmark_draws < 5 or args.micro_benchmark_draws > 10:
        raise ValueError("--micro-benchmark-draws must be between 5 and 10")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matched-n", type=int, default=DEFAULT_MATCHED_N)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--b-permutation", type=int, default=DEFAULT_B)
    parser.add_argument("--b-bootstrap", type=int, default=DEFAULT_B)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--max-hours", type=float, default=DEFAULT_MAX_HOURS)
    parser.add_argument("--micro-benchmark-draws", type=int, default=DEFAULT_MICRO_DRAWS)
    parser.add_argument("--run-id", default=date.today().isoformat())
    parser.add_argument("--output-date", default=date.today().isoformat())
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-full", action="store_true")
    parser.add_argument("--observed-only", action="store_true")
    parser.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--skip-benchmark", action="store_true")
    args = parser.parse_args()
    _validate_args(args)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started_at = time.perf_counter()
    repo_root = Path.cwd()
    checkpoint_dir = (
        core.proj_root()
        / OUTPUT_REL_DIR
        / "inference_checkpoints"
        / f"spanning_betti_inference_{args.run_id}"
    )

    context = prepare_context(repo_root=repo_root, matched_n=args.matched_n, seed=args.seed)
    observed = compute_observed(context)
    equivalence_gate = observed_equivalence_gate(observed)
    if not equivalence_gate["passed"]:
        raise RuntimeError(
            "Observed-equivalence gate failed:\n  "
            + "\n  ".join(equivalence_gate["errors"])
        )
    progress = _load_progress(checkpoint_dir) if args.resume else None
    progress = progress or {}
    progress.update(
        {
            "status": "observed_gate_passed",
            "observed_equivalence_gate": equivalence_gate,
            "workers": args.workers,
            "chunk_size": args.chunk_size,
        }
    )
    progress_path = _write_progress(
        checkpoint_dir,
        run_id=args.run_id,
        progress=progress,
    )
    if args.observed_only:
        print(json.dumps(core.convert_numpy({"observed": observed, "gate": equivalence_gate}), indent=2))
        return

    benchmark: dict[str, Any] = {}
    if not args.skip_benchmark:
        benchmark = _load_or_run_micro_benchmark(
            checkpoint_dir=checkpoint_dir,
            run_id=args.run_id,
            micro_draws=args.micro_benchmark_draws,
            workers=args.workers,
            embedding_cache_path=context["embedding_cache_path"],
            spanning_idx=context["spanning_idx"],
            newcomer_idx=context["newcomer_idx"],
            eps_lo=float(observed["eps_lo"]),
            matched_n=int(context["matched_n"]),
            master_seed=args.seed,
            b_permutation=args.b_permutation,
            b_bootstrap=args.b_bootstrap,
            resume=args.resume,
        )
        projected = float(benchmark["projected_wall_hours_at_workers"])
        if projected > args.max_hours:
            raise RuntimeError(
                f"Projected full run {projected:.2f}h exceeds --max-hours "
                f"{args.max_hours:.2f}; pause for launch direction."
            )

    if args.benchmark_only or not args.run_full:
        launch_command = (
            "uv run --extra wasserstein python trajectory_tda/scripts/stage1/"
            "run_spanning_betti_inference.py --run-full --resume "
            f"--run-id {args.run_id} --workers {args.workers}"
        )
        print(f"Observed-equivalence gate passed. Launch command: {launch_command}")
        return

    permutation_draws = _run_lane(
        lane="permutation",
        b_draws=args.b_permutation,
        checkpoint_dir=checkpoint_dir,
        run_id=args.run_id,
        resume=args.resume,
        workers=args.workers,
        chunk_size=args.chunk_size,
        embedding_cache_path=context["embedding_cache_path"],
        spanning_idx=context["spanning_idx"],
        newcomer_idx=context["newcomer_idx"],
        eps_lo=float(observed["eps_lo"]),
        matched_n=int(context["matched_n"]),
        master_seed=args.seed,
        spawn_offset=0,
    )
    bootstrap_draws = _run_lane(
        lane="bootstrap",
        b_draws=args.b_bootstrap,
        checkpoint_dir=checkpoint_dir,
        run_id=args.run_id,
        resume=args.resume,
        workers=args.workers,
        chunk_size=args.chunk_size,
        embedding_cache_path=context["embedding_cache_path"],
        spanning_idx=context["spanning_idx"],
        newcomer_idx=context["newcomer_idx"],
        eps_lo=float(observed["eps_lo"]),
        matched_n=int(context["matched_n"]),
        master_seed=args.seed,
        spawn_offset=args.b_permutation,
    )
    progress_path = _write_progress(
        checkpoint_dir,
        run_id=args.run_id,
        progress={
            "status": "draws_complete",
            "completed": {
                "permutation": len(permutation_draws),
                "bootstrap": len(bootstrap_draws),
            },
            "micro_benchmark": benchmark,
        },
    )
    payload = build_payload(
        repo_root=repo_root,
        context=context,
        observed=observed,
        equivalence_gate=equivalence_gate,
        permutation_draws=permutation_draws,
        bootstrap_draws=bootstrap_draws,
        run_id=args.run_id,
        checkpoint_dir=checkpoint_dir,
        progress_path=progress_path,
        benchmark=benchmark,
        workers=args.workers,
        chunk_size=args.chunk_size,
        started_at=started_at,
    )
    output_path = repo_root / OUTPUT_REL_DIR / f"spanning_betti_inference_{args.output_date}.json"
    _write_json_no_overwrite(output_path, payload)
    _write_progress(
        checkpoint_dir,
        run_id=args.run_id,
        progress={
            "status": "complete",
            "output_path": str(output_path),
            "completed": {
                "permutation": len(permutation_draws),
                "bootstrap": len(bootstrap_draws),
            },
            "micro_benchmark": benchmark,
        },
    )
    print(f"Inference JSON: {output_path}")


if __name__ == "__main__":
    main()
