# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.26b BHPS non-overlap re-analysis. Re-test the BHPS-only
#   remainder at matched landmark fraction and compare its W2 statistic against
#   same-size random full-BHPS controls under frozen full-BHPS loadings.
"""BHPS non-overlap re-analysis for the P01-A replication framing."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import time
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from trajectory_tda.analysis.panel.t126_bhps_nonoverlap import (
    ALPHA_LEVEL,
    BASELINE_HEADLINE_REL,
    BHPS_DIR_REL,
    OUT_DIR_REL,
    P_VALUE_FORMULA,
    PCA_DIM,
    PCA_SVD_SOLVER,
    PROJ_ROOT,
    SEED,
    SPANNING_DIR_REL,
    WORKTREE,
    _fit_full_bhps_reference,
    _git_head,
    _load_checkpoint,
)
from trajectory_tda.scripts.stage1 import _battery_core as core

LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION = "stage1/bhps-nonoverlap-reanalysis/v1"
TASK_NAME = "T1.26b BHPS non-overlap re-analysis"
PRE_REGISTRATION_REF = (
    "2026-06-09 T1.26b pre-registration amendment: "
    "results/panel_methodology/bhps_nonoverlap/pre_registrations_2026-06-09.json"
)
T126_RESULT_REL = OUT_DIR_REL / "bhps_only_gmm_ph_2026-06-09.json"

MATCHED_LANDMARK_FRACTION_ROUNDED = 0.588
K_SUBSAMPLES = 20
SUBSAMPLE_N = 3202
DUAL_METRIC = True


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _range_check_number(value: Any, lo: float, hi: float, name: str, errors: list[str]) -> None:
    if not _is_number(value):
        errors.append(f"{name} must be a finite number")
        return
    if not lo <= float(value) <= hi:
        errors.append(f"{name} must be in [{lo}, {hi}]")


def _positive_int(value: Any, name: str, errors: list[str], *, allow_zero: bool = False) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{name} must be an int")
        return
    if allow_zero:
        if value < 0:
            errors.append(f"{name} must be >= 0")
    elif value <= 0:
        errors.append(f"{name} must be > 0")


def _p_rejects(p_value: Any) -> bool | None:
    if not _is_number(p_value):
        return None
    return bool(float(p_value) < ALPHA_LEVEL)


def _hash_int_array(values: NDArray[np.integer[Any]]) -> str:
    arr = np.asarray(values, dtype=np.int64)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing JSON: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(core.convert_numpy(payload), indent=2), encoding="utf-8")


def _configure_core_output_roots(proj_root: Path) -> None:
    """Route canonical core launch markers and partials to PROJ_ROOT."""
    os.environ["STAGE1_PROJ_ROOT"] = str(proj_root)
    core.worktree_root = lambda: proj_root  # type: ignore[assignment]


def _metric_cell(cell: dict[str, Any]) -> dict[str, Any]:
    w2_p = float(cell["w2_pvalue"])
    landscape_p = float(cell["landscape_l2_pvalue"])
    return {
        "w2_p": w2_p,
        "w2_rejects": bool(w2_p < ALPHA_LEVEL),
        "w2_d_perm": float(cell["d_perm"]),
        "w2_t_ratio": float(cell["t_ratio"]),
        "w2_mean_obs_null": float(cell["mean_obs_null"]),
        "w2_mean_null_null": float(cell["mean_null_null"]),
        "landscape_l2_p": landscape_p,
        "landscape_l2_rejects": bool(landscape_p < ALPHA_LEVEL),
        "landscape_l2_d_perm": float(cell["landscape_d_perm"]),
        "landscape_l2_t_ratio": float(cell["landscape_t_ratio"]),
        "pvalue_null_draws": int(cell["pvalue_null_draws"]),
        "effect_null_pairs": int(cell["effect_null_pairs"]),
    }


def _flatten_arm_a(out: dict[str, Any], L: int, n: int, cache_path: Path, checkpoint_path: Path, runtime: float) -> dict[str, Any]:
    h0 = _metric_cell(out["h0"])
    h1 = _metric_cell(out["h1"])
    return {
        "L": int(L),
        "actual_landmarks": int(min(L, n)),
        "h1_w2_p": h1["w2_p"],
        "h1_w2_rejects": h1["w2_rejects"],
        "h1_w2_d_perm": h1["w2_d_perm"],
        "h1_landscape_l2_p": h1["landscape_l2_p"],
        "h1_landscape_l2_rejects": h1["landscape_l2_rejects"],
        "h1_landscape_l2_d_perm": h1["landscape_l2_d_perm"],
        "h0_w2_p": h0["w2_p"],
        "h0_w2_rejects": h0["w2_rejects"],
        "h0_w2_d_perm": h0["w2_d_perm"],
        "h0_landscape_l2_p": h0["landscape_l2_p"],
        "h0_landscape_l2_rejects": h0["landscape_l2_rejects"],
        "h0_landscape_l2_d_perm": h0["landscape_l2_d_perm"],
        "metrics": {"h0": h0, "h1": h1},
        "runtime_seconds": float(runtime),
        "null_diagram_cache": str(cache_path),
        "checkpoint": str(checkpoint_path),
    }


def _flatten_subsample(
    out: dict[str, Any],
    subsample_index: int,
    draw_seed: int,
    selected_indices: NDArray[np.integer[Any]],
    L: int,
    cache_path: Path,
    checkpoint_path: Path,
    runtime: float,
) -> dict[str, Any]:
    h0 = _metric_cell(out["h0"])
    h1 = _metric_cell(out["h1"])
    return {
        "subsample_index": int(subsample_index),
        "draw_seed": int(draw_seed),
        "permutation_seed": int(draw_seed),
        "n": int(len(selected_indices)),
        "L": int(L),
        "actual_landmarks": int(min(L, len(selected_indices))),
        "selected_index_sha256": _hash_int_array(selected_indices),
        "h1_w2_p": h1["w2_p"],
        "h1_w2_rejects": h1["w2_rejects"],
        "h1_w2_d_perm": h1["w2_d_perm"],
        "h1_landscape_l2_p": h1["landscape_l2_p"],
        "h1_landscape_l2_rejects": h1["landscape_l2_rejects"],
        "h1_landscape_l2_d_perm": h1["landscape_l2_d_perm"],
        "h0_w2_p": h0["w2_p"],
        "h0_landscape_l2_p": h0["landscape_l2_p"],
        "metrics": {"h0": h0, "h1": h1},
        "runtime_seconds": float(runtime),
        "null_diagram_cache": str(cache_path),
        "checkpoint": str(checkpoint_path),
    }


def validate_bhps_nonoverlap_reanalysis_payload(payload: dict[str, Any]) -> None:
    """Validate a T1.26b BHPS non-overlap re-analysis payload."""
    errors: list[str] = []
    required = ["schema_version", "generated_at", "task", "pre_registration", "inputs", "params", "arm_a", "arm_b", "decision"]
    for key in required:
        if key not in payload:
            errors.append(f"missing required key: {key}")
    if "per_call_pca" in payload:
        errors.append("forbidden key present: per_call_pca")
    if errors:
        raise ValueError("; ".join(errors))

    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION!r}")
    if payload["task"] != TASK_NAME:
        errors.append(f"task must equal {TASK_NAME!r}")
    if "2026-06-09" not in str(payload["pre_registration"]):
        errors.append("pre_registration must reference the 2026-06-09 T1.26b pre-registration amendment")

    inputs = payload["inputs"]
    for key in ("full_bhps_source", "spanning_ids_source", "t126_result_source", "baseline_bhps_headline_source", "git_head"):
        if key not in inputs:
            errors.append(f"inputs missing {key}")
    if "trajectory_tda_bhps" not in str(inputs.get("full_bhps_source", "")):
        errors.append("inputs.full_bhps_source must reference the BHPS checkpoint")
    if "trajectory_tda_spanning" not in str(inputs.get("spanning_ids_source", "")):
        errors.append("inputs.spanning_ids_source must reference the spanning checkpoint")
    if "bhps_only_gmm_ph_2026-06-09.json" not in str(inputs.get("t126_result_source", "")):
        errors.append("inputs.t126_result_source must reference the T1.26 result JSON")

    params = payload["params"]
    expected = {
        "matched_landmark_fraction": MATCHED_LANDMARK_FRACTION_ROUNDED,
        "K_subsamples": K_SUBSAMPLES,
        "subsample_n": SUBSAMPLE_N,
        "seed": SEED,
        "frozen_loadings": True,
        "dual_metric": True,
        "p_value_formula": P_VALUE_FORMULA,
        "alpha_level": ALPHA_LEVEL,
        "pca_dim": PCA_DIM,
        "pca_svd_solver": PCA_SVD_SOLVER,
        "null_model": f"markov-{core.DEFAULT_MARKOV_ORDER}",
    }
    for key, expected_value in expected.items():
        if params.get(key) != expected_value:
            errors.append(f"params.{key} must equal {expected_value!r}")
    _positive_int(params.get("B"), "params.B", errors)
    if isinstance(params.get("B"), int) and params["B"] < 1000:
        errors.append("params.B must be >= 1000")
    _positive_int(params.get("arm_a_L"), "params.arm_a_L", errors)
    if isinstance(params.get("arm_a_L"), int) and params["arm_a_L"] >= SUBSAMPLE_N:
        errors.append("params.arm_a_L must be < 3202")
    _positive_int(params.get("arm_b_L"), "params.arm_b_L", errors)

    arm_a = payload["arm_a"]
    _positive_int(arm_a.get("L"), "arm_a.L", errors)
    if isinstance(arm_a.get("L"), int) and arm_a["L"] >= SUBSAMPLE_N:
        errors.append("arm_a.L must be < 3202")
    for key in ("h1_w2_p", "h1_landscape_l2_p", "h0_w2_p", "h0_landscape_l2_p"):
        _range_check_number(arm_a.get(key), 0.0, 1.0, f"arm_a.{key}", errors)
    if not isinstance(arm_a.get("h1_w2_rejects"), bool):
        errors.append("arm_a.h1_w2_rejects must be bool")
    elif _p_rejects(arm_a.get("h1_w2_p")) is not None and arm_a["h1_w2_rejects"] != _p_rejects(arm_a["h1_w2_p"]):
        errors.append("arm_a.h1_w2_rejects must equal h1_w2_p < 0.05")

    arm_b = payload["arm_b"]
    if arm_b.get("K") != K_SUBSAMPLES:
        errors.append(f"arm_b.K must equal {K_SUBSAMPLES}")
    if arm_b.get("subsample_n") != SUBSAMPLE_N:
        errors.append(f"arm_b.subsample_n must equal {SUBSAMPLE_N}")
    seeds = arm_b.get("per_subsample_seeds")
    if not isinstance(seeds, list) or len(seeds) != K_SUBSAMPLES or not all(isinstance(seed, int) for seed in seeds):
        errors.append("arm_b.per_subsample_seeds must be a list of 20 ints")
    _range_check_number(arm_b.get("remainder_h1_w2_d_perm"), -math.inf, math.inf, "arm_b.remainder_h1_w2_d_perm", errors)
    null_band = arm_b.get("null_band", {})
    if not isinstance(null_band, dict):
        errors.append("arm_b.null_band must be a dict")
        null_band = {}
    for key in ("d_perm_mean", "d_perm_sd", "d_perm_q025", "d_perm_q975"):
        _range_check_number(null_band.get(key), -math.inf, math.inf, f"arm_b.null_band.{key}", errors)
    if _is_number(null_band.get("d_perm_q025")) and _is_number(null_band.get("d_perm_q975")):
        if float(null_band["d_perm_q025"]) > float(null_band["d_perm_q975"]):
            errors.append("arm_b.null_band.d_perm_q025 must be <= d_perm_q975")
    if not isinstance(arm_b.get("remainder_within_band"), bool):
        errors.append("arm_b.remainder_within_band must be bool")
    elif all(_is_number(value) for value in (arm_b.get("remainder_h1_w2_d_perm"), null_band.get("d_perm_q025"), null_band.get("d_perm_q975"))):
        d_perm = float(arm_b["remainder_h1_w2_d_perm"])
        q025 = float(null_band["d_perm_q025"])
        q975 = float(null_band["d_perm_q975"])
        if arm_b["remainder_within_band"] != (q025 <= d_perm <= q975):
            errors.append("arm_b.remainder_within_band must equal d_perm in [q025, q975]")
    n_reject = arm_b.get("n_subsamples_h1_w2_reject")
    if not isinstance(n_reject, int) or isinstance(n_reject, bool) or not 0 <= n_reject <= K_SUBSAMPLES:
        errors.append("arm_b.n_subsamples_h1_w2_reject must be an int in [0, 20]")
    subsamples = arm_b.get("subsamples")
    if subsamples is not None:
        if not isinstance(subsamples, list) or len(subsamples) != K_SUBSAMPLES:
            errors.append("arm_b.subsamples must contain 20 entries when present")
        else:
            rejects = sum(1 for sample in subsamples if isinstance(sample, dict) and sample.get("h1_w2_rejects") is True)
            if isinstance(n_reject, int) and n_reject != rejects:
                errors.append("arm_b.n_subsamples_h1_w2_reject must match subsample rejection count")

    decision = payload["decision"]
    if decision.get("outcome") not in {"size_or_fraction_artefact", "overlap_dependent"}:
        errors.append("decision.outcome must be 'size_or_fraction_artefact' or 'overlap_dependent'")
    if not isinstance(decision.get("overlap_specific"), bool):
        errors.append("decision.overlap_specific must be bool")
    if isinstance(arm_a.get("h1_w2_rejects"), bool) and isinstance(arm_b.get("remainder_within_band"), bool):
        artefact = bool(arm_a["h1_w2_rejects"] or arm_b["remainder_within_band"])
        expected_outcome = "size_or_fraction_artefact" if artefact else "overlap_dependent"
        expected_overlap_specific = not artefact
        if decision.get("outcome") != expected_outcome:
            errors.append("decision.outcome must follow the pre-registered artefact rule")
        if decision.get("overlap_specific") != expected_overlap_specific:
            errors.append("decision.overlap_specific must be false iff artefact rule is met")

    if errors:
        raise ValueError("; ".join(errors))


def _run_headline_and_cache(
    *,
    embeddings: NDArray[np.float64],
    trajectories: list[list[str]],
    frozen_models: dict[str, Any],
    B: int,
    L: int,
    seed: int,
    label: str,
    phase_tag: str,
    n_jobs: int,
    n_null_pairs: int,
    k_max: int,
    n_points: int,
    cache_path: Path,
    cache_metadata: dict[str, Any],
    joblib_backend: str | None,
    permutation_chunk_size: int,
) -> dict[str, Any]:
    if cache_path.exists():
        raise FileExistsError(f"Null-diagram cache exists without a checkpoint to resume: {cache_path}")
    embed_kwargs = {"include_bigrams": True, "tfidf": False, "pca_dim": PCA_DIM}
    if permutation_chunk_size > 0:
        out, null_results, ph_obs = _run_headline_from_embeddings_chunked(
            embeddings=embeddings,
            trajectories=trajectories,
            embed_kwargs=embed_kwargs,
            n_permutations=B,
            n_landmarks=L,
            k_max=k_max,
            n_points=n_points,
            seed=seed,
            label=label,
            phase_tag=phase_tag,
            n_jobs=n_jobs,
            n_null_pairs_cap=n_null_pairs,
            markov_order=core.DEFAULT_MARKOV_ORDER,
            frozen_models=frozen_models,
            joblib_backend=joblib_backend,
            permutation_chunk_size=permutation_chunk_size,
        )
    else:
        if joblib_backend is None:
            parallel_context = nullcontext()
        else:
            from joblib import parallel_config

            parallel_context = parallel_config(backend=joblib_backend)
        with parallel_context:
            out, null_results, ph_obs = core.run_headline_from_embeddings(
                embeddings=embeddings,
                trajectories=trajectories,
                embed_kwargs=embed_kwargs,
                n_permutations=B,
                n_landmarks=L,
                k_max=k_max,
                n_points=n_points,
                seed=seed,
                label=label,
                phase_tag=phase_tag,
                n_jobs=n_jobs,
                n_null_pairs_cap=n_null_pairs,
                markov_order=core.DEFAULT_MARKOV_ORDER,
                frozen_models=frozen_models,
            )
    core.write_null_diagram_cache(cache_path, null_results, ph_obs, cache_metadata)
    return out


def _subsample_seeds(seed: int, K: int) -> list[int]:
    rng = np.random.default_rng(seed)
    seeds = [int(value) for value in rng.integers(1, np.iinfo(np.int32).max, size=K, dtype=np.int64)]
    if len(set(seeds)) != K:
        raise ValueError("Derived duplicate subsample seeds")
    return seeds


def _draw_subsample_indices(n_full: int, subsample_n: int, seed: int) -> NDArray[np.int64]:
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n_full, size=subsample_n, replace=False)).astype(np.int64)


def _run_headline_from_embeddings_chunked(
    *,
    embeddings: NDArray[np.float64],
    trajectories: list[list[str]],
    embed_kwargs: dict[str, Any],
    n_permutations: int,
    n_landmarks: int,
    k_max: int,
    n_points: int,
    seed: int,
    label: str,
    phase_tag: str,
    n_jobs: int,
    n_null_pairs_cap: int,
    markov_order: int,
    frozen_models: dict[str, Any],
    joblib_backend: str | None,
    permutation_chunk_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
    """Canonical headline computation with recycled permutation workers."""
    from joblib import Parallel, delayed, parallel_config
    from poverty_tda.topology.multidim_ph import compute_rips_ph
    from trajectory_tda.topology.permutation_nulls import _single_permutation, maxmin_landmarks

    t_phase = time.time()
    core.write_status(f"PHASE {label} START", f"L={n_landmarks} B={n_permutations} n_jobs={n_jobs}")
    LOGGER.info("=" * 70)
    LOGGER.info(
        "[PHASE %s] chunked start (L=%d, B=%d, n_jobs=%d, chunk_size=%d)",
        label,
        n_landmarks,
        n_permutations,
        n_jobs,
        permutation_chunk_size,
    )
    LOGGER.info("=" * 70)

    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    t_lm = time.time()
    if actual_lm < n:
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_landmarks = embeddings
    ph_obs = compute_rips_ph(obs_landmarks, max_dim=1)
    LOGGER.info("[PHASE %s] obs landmarks + PH built in %.1fs (L=%d)", label, time.time() - t_lm, actual_lm)

    core.write_status(f"PHASE {label} PERMUTATIONS", f"B={n_permutations} n_jobs={n_jobs}")
    seeds_list = [seed + i + 1 for i in range(n_permutations)]
    null_results: list[dict[str, Any]] = []
    t0 = time.time()
    for chunk_start in range(0, n_permutations, permutation_chunk_size):
        chunk_end = min(chunk_start + permutation_chunk_size, n_permutations)
        chunk_seeds = seeds_list[chunk_start:chunk_end]
        LOGGER.info(
            "[PHASE %s] chunk %d-%d/%d running with backend=%s",
            label,
            chunk_start + 1,
            chunk_end,
            n_permutations,
            joblib_backend or "default",
        )
        if joblib_backend is None:
            parallel_context = nullcontext()
        else:
            parallel_context = parallel_config(backend=joblib_backend)
        with parallel_context:
            chunk_results = list(
                Parallel(n_jobs=n_jobs, verbose=10)(
                    delayed(_single_permutation)(
                        "markov",
                        embeddings,
                        trajectories,
                        None,
                        chunk_seed,
                        1,
                        actual_lm,
                        "wasserstein",
                        markov_order,
                        embed_kwargs,
                        frozen_models=frozen_models,
                        ph_observed=ph_obs,
                    )
                    for chunk_seed in chunk_seeds
                )
            )
        null_results.extend(chunk_results)
        core.write_partial(
            phase_tag,
            f"chunk_{chunk_end:04d}",
            {
                "phase": phase_tag,
                "chunk_start": chunk_start,
                "chunk_end": chunk_end,
                "n_permutations_completed": len(null_results),
                "L": actual_lm,
                "seed": seed,
                "elapsed_perms_s": time.time() - t0,
            },
        )

    LOGGER.info("[PHASE %s] %d permutations done in %.1fs", label, n_permutations, time.time() - t0)
    core.write_status(f"PHASE {label} AGGREGATION", f"perms done in {time.time() - t0:.0f}s")
    out = core.aggregate_combined(
        null_results,
        ph_obs,
        n_permutations,
        max_dim=1,
        k_max=k_max,
        n_points=n_points,
        seed=seed,
        n_null_pairs_cap=n_null_pairs_cap,
        phase_label=label,
    )
    core.write_partial(phase_tag, "after_agg", {"phase": phase_tag, "result": out})
    LOGGER.info("[PHASE %s] TOTAL elapsed %.1fs", label, time.time() - t_phase)
    core.write_status(f"PHASE {label} DONE", f"total {time.time() - t_phase:.0f}s")
    return out, null_results, ph_obs


def _write_progress(checkpoint_dir: Path, completed: int, total: int, date: str) -> None:
    progress_path = checkpoint_dir / f"progress_{date}.json"
    progress = {
        "task": TASK_NAME,
        "generated_at": datetime.now(UTC).isoformat(),
        "completed_subsamples": completed,
        "total_subsamples": total,
        "checkpoint_dir": str(checkpoint_dir),
    }
    progress_path.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute both T1.26b re-analysis arms and write the result JSON."""
    started = time.perf_counter()
    worktree = Path(args.worktree)
    proj_root = Path(args.proj_root)
    _configure_core_output_roots(proj_root)

    output_dir = worktree / OUT_DIR_REL
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"bhps_nonoverlap_reanalysis_{args.date}.json"
    if output_path.exists():
        raise FileExistsError(f"Result already exists: {output_path}")

    checkpoint_dir = proj_root / "results/trajectory_tda_integration/stage1/bhps_nonoverlap_reanalysis" / args.date
    cache_dir = proj_root / "results/trajectory_tda_integration/stage1/cache/bhps_nonoverlap_reanalysis"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + args.max_hours * 3600 if args.max_hours else None

    marker_path = core.write_launch_marker(
        "bhps_nonoverlap_reanalysis",
        {"B": args.B, "seed": args.seed, "K_subsamples": K_SUBSAMPLES, "subsample_n": SUBSAMPLE_N},
    )

    bhps_dir = proj_root / BHPS_DIR_REL
    spanning_dir = proj_root / SPANNING_DIR_REL
    full_sequences, full_pidps = _load_checkpoint(bhps_dir)
    spanning_sequences, spanning_pidps = _load_checkpoint(spanning_dir)
    del spanning_sequences
    full_embedding, frozen_models, representation_info = _fit_full_bhps_reference(full_sequences)

    spanning_pidp_set = set(spanning_pidps)
    remainder_indices = np.asarray([idx for idx, pidp in enumerate(full_pidps) if pidp not in spanning_pidp_set], dtype=np.int64)
    excluded_indices = np.asarray([idx for idx, pidp in enumerate(full_pidps) if pidp in spanning_pidp_set], dtype=np.int64)
    if len(remainder_indices) != SUBSAMPLE_N:
        raise ValueError(f"Expected BHPS-only remainder n={SUBSAMPLE_N}, got {len(remainder_indices)}")
    remainder_sequences = [full_sequences[int(idx)] for idx in remainder_indices]
    remainder_embedding = full_embedding[remainder_indices]

    t126_payload = _load_json(worktree / T126_RESULT_REL)
    t126_remainder_h1_w2_d_perm = float(t126_payload["headline_result"]["h1"]["d_perm"])
    t126_remainder_h1_w2_p = float(t126_payload["headline_result"]["h1"]["w2_pvalue"])
    t126_remainder_h1_landscape_l2_p = float(t126_payload["headline_result"]["h1"]["landscape_l2_pvalue"])

    matched_landmark_fraction_exact = core.DEFAULT_L / len(full_sequences)
    arm_a_L = int(round(matched_landmark_fraction_exact * len(remainder_sequences)))
    if arm_a_L <= 0 or arm_a_L >= len(remainder_sequences):
        raise ValueError(f"Computed invalid Arm A L={arm_a_L}")

    arm_a_checkpoint = checkpoint_dir / f"arm_a_L{arm_a_L}_B{args.B}_seed{args.seed}.json"
    if arm_a_checkpoint.exists():
        arm_a = _load_json(arm_a_checkpoint)
        arm_a.setdefault("joblib_backend", "loky")
        arm_a.setdefault("permutation_chunk_size", 0)
        LOGGER.info("Loaded Arm A checkpoint: %s", arm_a_checkpoint)
    else:
        arm_a_started = time.perf_counter()
        arm_a_cache = cache_dir / f"null_diagrams_bhps_nonoverlap_reanalysis_arm_a_B{args.B}_L{arm_a_L}_seed{args.seed}_{args.date}.npz"
        arm_a_out = _run_headline_and_cache(
            embeddings=remainder_embedding,
            trajectories=remainder_sequences,
            frozen_models=frozen_models,
            B=args.B,
            L=arm_a_L,
            seed=args.seed,
            label="BHPS non-overlap matched-fraction",
            phase_tag="bhps_nonoverlap_reanalysis_arm_a",
            n_jobs=args.n_jobs,
            n_null_pairs=args.n_null_pairs,
            k_max=args.k_max,
            n_points=args.n_points,
            cache_path=arm_a_cache,
            cache_metadata={
                "arm": "A",
                "B": args.B,
                "L": arm_a_L,
                "actual_landmarks": min(arm_a_L, len(remainder_sequences)),
                "seed": args.seed,
                "dataset": "bhps_nonoverlap_reanalysis_arm_a",
                "timestamp": args.date,
                "frozen_loadings": True,
                "n_bhps_only": len(remainder_sequences),
            },
            joblib_backend=args.joblib_backend,
            permutation_chunk_size=args.permutation_chunk_size,
        )
        arm_a = _flatten_arm_a(
            arm_a_out,
            arm_a_L,
            len(remainder_sequences),
            arm_a_cache,
            arm_a_checkpoint,
            time.perf_counter() - arm_a_started,
        )
        arm_a["joblib_backend"] = args.joblib_backend or "loky"
        arm_a["permutation_chunk_size"] = args.permutation_chunk_size
        _write_json_no_overwrite(arm_a_checkpoint, arm_a)

    subsample_seeds = _subsample_seeds(args.seed, K_SUBSAMPLES)
    subsamples: list[dict[str, Any]] = []
    for idx, subsample_seed in enumerate(subsample_seeds):
        checkpoint_path = checkpoint_dir / f"arm_b_subsample_{idx:02d}_seed{subsample_seed}_B{args.B}.json"
        if checkpoint_path.exists():
            subsample = _load_json(checkpoint_path)
            subsample.setdefault("joblib_backend", "loky")
            subsample.setdefault("permutation_chunk_size", 0)
            LOGGER.info("Loaded Arm B checkpoint %02d/%02d: %s", idx + 1, K_SUBSAMPLES, checkpoint_path)
            subsamples.append(subsample)
            continue
        if deadline is not None and time.perf_counter() >= deadline:
            _write_progress(checkpoint_dir, len(subsamples), K_SUBSAMPLES, args.date)
            raise TimeoutError(
                f"--max-hours reached after {len(subsamples)} of {K_SUBSAMPLES} Arm B subsamples; rerun to resume"
            )
        selected_indices = _draw_subsample_indices(len(full_sequences), SUBSAMPLE_N, subsample_seed)
        selected_sequences = [full_sequences[int(row)] for row in selected_indices]
        selected_embedding = full_embedding[selected_indices]
        cache_path = cache_dir / (
            f"null_diagrams_bhps_nonoverlap_reanalysis_arm_b_sub{idx:02d}_"
            f"B{args.B}_L{core.DEFAULT_L}_seed{subsample_seed}_{args.date}.npz"
        )
        sub_started = time.perf_counter()
        out = _run_headline_and_cache(
            embeddings=selected_embedding,
            trajectories=selected_sequences,
            frozen_models=frozen_models,
            B=args.B,
            L=core.DEFAULT_L,
            seed=subsample_seed,
            label=f"BHPS same-size control {idx:02d}",
            phase_tag=f"bhps_nonoverlap_reanalysis_arm_b_sub{idx:02d}",
            n_jobs=args.n_jobs,
            n_null_pairs=args.n_null_pairs,
            k_max=args.k_max,
            n_points=args.n_points,
            cache_path=cache_path,
            cache_metadata={
                "arm": "B",
                "subsample_index": idx,
                "B": args.B,
                "L": core.DEFAULT_L,
                "actual_landmarks": min(core.DEFAULT_L, SUBSAMPLE_N),
                "seed": subsample_seed,
                "dataset": "bhps_nonoverlap_reanalysis_arm_b",
                "timestamp": args.date,
                "frozen_loadings": True,
                "subsample_n": SUBSAMPLE_N,
                "selected_index_sha256": _hash_int_array(selected_indices),
            },
            joblib_backend=args.joblib_backend,
            permutation_chunk_size=args.permutation_chunk_size,
        )
        subsample = _flatten_subsample(
            out,
            idx,
            subsample_seed,
            selected_indices,
            core.DEFAULT_L,
            cache_path,
            checkpoint_path,
            time.perf_counter() - sub_started,
        )
        subsample["joblib_backend"] = args.joblib_backend or "loky"
        subsample["permutation_chunk_size"] = args.permutation_chunk_size
        _write_json_no_overwrite(checkpoint_path, subsample)
        subsamples.append(subsample)
        _write_progress(checkpoint_dir, len(subsamples), K_SUBSAMPLES, args.date)

    d_perm_values = np.asarray([float(sample["h1_w2_d_perm"]) for sample in subsamples], dtype=np.float64)
    q025, q975 = np.quantile(d_perm_values, [0.025, 0.975])
    remainder_within_band = bool(float(q025) <= t126_remainder_h1_w2_d_perm <= float(q975))
    arm_b = {
        "K": K_SUBSAMPLES,
        "subsample_n": SUBSAMPLE_N,
        "L": core.DEFAULT_L,
        "actual_landmarks": SUBSAMPLE_N,
        "per_subsample_seeds": subsample_seeds,
        "remainder_h1_w2_d_perm": t126_remainder_h1_w2_d_perm,
        "remainder_h1_w2_p": t126_remainder_h1_w2_p,
        "remainder_h1_landscape_l2_p": t126_remainder_h1_landscape_l2_p,
        "null_band": {
            "d_perm_mean": float(d_perm_values.mean()),
            "d_perm_sd": float(d_perm_values.std(ddof=1)),
            "d_perm_q025": float(q025),
            "d_perm_q975": float(q975),
            "d_perm_min": float(d_perm_values.min()),
            "d_perm_max": float(d_perm_values.max()),
        },
        "remainder_within_band": remainder_within_band,
        "remainder_on_band_boundary": bool(t126_remainder_h1_w2_d_perm == float(q025) or t126_remainder_h1_w2_d_perm == float(q975)),
        "n_subsamples_h1_w2_reject": int(sum(sample["h1_w2_rejects"] for sample in subsamples)),
        "n_subsamples_h1_landscape_l2_reject": int(sum(sample["h1_landscape_l2_rejects"] for sample in subsamples)),
        "subsamples": subsamples,
    }

    artefact = bool(arm_a["h1_w2_rejects"] or arm_b["remainder_within_band"])
    decision = {
        "overlap_specific": not artefact,
        "outcome": "size_or_fraction_artefact" if artefact else "overlap_dependent",
        "rule": "size_or_fraction_artefact iff Arm A H1 W2 rejects or T1.26 remainder H1 W2 d_perm lies within Arm B same-size band",
        "dual_metric_note": "Landscape L2 is reported for H0 and H1 throughout; no H1 conclusion rests on W2 alone.",
        "manager_review_required": bool(arm_b["remainder_on_band_boundary"]),
        "paper_section": "P01-A section 6.2",
    }

    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION_REF,
        "inputs": {
            "full_bhps_source": str(BHPS_DIR_REL / "01_trajectories.json"),
            "full_bhps_sequences_source": str(BHPS_DIR_REL / "01_trajectories_sequences.json"),
            "spanning_ids_source": str(SPANNING_DIR_REL / "01_trajectories.json") + "[metadata.pidp]",
            "t126_result_source": str(T126_RESULT_REL),
            "baseline_bhps_headline_source": str(BASELINE_HEADLINE_REL),
            "git_head": _git_head(),
        },
        "params": {
            "matched_landmark_fraction": MATCHED_LANDMARK_FRACTION_ROUNDED,
            "matched_landmark_fraction_exact": float(matched_landmark_fraction_exact),
            "K_subsamples": K_SUBSAMPLES,
            "subsample_n": SUBSAMPLE_N,
            "B": args.B,
            "seed": args.seed,
            "frozen_loadings": True,
            "dual_metric": DUAL_METRIC,
            "pca_dim": PCA_DIM,
            "pca_svd_solver": PCA_SVD_SOLVER,
            "arm_a_L": arm_a_L,
            "arm_b_L": core.DEFAULT_L,
            "n_null_pairs_cap": args.n_null_pairs,
            "landscape_k_max": args.k_max,
            "landscape_n_points": args.n_points,
            "null_model": f"markov-{core.DEFAULT_MARKOV_ORDER}",
            "p_value_formula": P_VALUE_FORMULA,
            "alpha_level": ALPHA_LEVEL,
            "n_jobs": args.n_jobs,
            "joblib_backend": args.joblib_backend or "loky",
            "permutation_chunk_size": args.permutation_chunk_size,
        },
        "arm_a": arm_a,
        "arm_b": arm_b,
        "decision": decision,
        "sample_counts": {
            "n_bhps_full": int(len(full_sequences)),
            "n_spanning_source": int(len(spanning_pidps)),
            "n_spanning_excluded": int(len(excluded_indices)),
            "n_bhps_only": int(len(remainder_sequences)),
        },
        "representation_provenance": representation_info,
        "output_provenance": {
            "result_path": str(output_path.relative_to(worktree)),
            "checkpoint_dir": str(checkpoint_dir),
            "cache_dir": str(cache_dir),
            "launch_marker": str(marker_path),
            "progress_path": str(checkpoint_dir / f"progress_{args.date}.json"),
            "partial_json_glob": str(proj_root / "results/trajectory_tda_integration/stage1/.partial/bhps_nonoverlap_reanalysis_*"),
            "regeneration_command": (
                ".\\.venv\\Scripts\\python.exe -m trajectory_tda.analysis.panel.t126b_bhps_nonoverlap_reanalysis "
                f"--date {args.date} --B {args.B} --seed {args.seed} --n-jobs {args.n_jobs}"
                f" --joblib-backend {args.joblib_backend or 'loky'}"
                f" --permutation-chunk-size {args.permutation_chunk_size}"
            ),
            "no_overwrite": True,
            "runtime_seconds": float(time.perf_counter() - started),
        },
    }
    validate_bhps_nonoverlap_reanalysis_payload(result)
    _write_json_no_overwrite(output_path, result)
    LOGGER.info("Saved result: %s", output_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--proj-root", default=str(PROJ_ROOT))
    parser.add_argument("--worktree", default=str(WORKTREE))
    parser.add_argument("--B", type=int, default=core.DEFAULT_B)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--k-max", type=int, default=core.DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=core.DEFAULT_N_POINTS)
    parser.add_argument("--n-null-pairs", type=int, default=core.DEFAULT_N_NULL_PAIRS)
    parser.add_argument("--n-jobs", type=int, default=4)
    parser.add_argument("--joblib-backend", choices=("loky", "threading"), default="loky")
    parser.add_argument("--permutation-chunk-size", type=int, default=0)
    parser.add_argument("--max-hours", type=float, default=0.0, help="Stop before a new subsample once this wall-time budget is reached; 0 means no limit.")
    args = parser.parse_args()
    if args.seed != SEED:
        raise ValueError(f"--seed must remain locked to {SEED}")
    if args.B < 1000:
        raise ValueError("--B must be >= 1000")
    if args.n_jobs < 4:
        raise ValueError("--n-jobs must be >= 4")
    if args.max_hours < 0:
        raise ValueError("--max-hours must be >= 0")
    if args.permutation_chunk_size < 0:
        raise ValueError("--permutation-chunk-size must be >= 0")
    return args


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    run(parse_args())


if __name__ == "__main__":
    main()
