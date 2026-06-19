# ruff: noqa: E402
# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: H2 dispersion-control and residual-characterization diagnostics.
"""Run H2 dispersion-control dual-metric diagnostics.

The decision-bearing statistic is H2 only: W2 and landscape-L2 between the
observed diagram and Markov-1 null diagrams after each landmark cloud is scaled
by its own pairwise-distance normalizer. The raw condition is retained for the
earlier dispersion-control exhibit.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from joblib import Parallel, delayed

PROJ_ROOT = Path(r"C:\Users\steph\TDL")
WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from poverty_tda.topology.multidim_ph import (  # noqa: E402
    H2_CANDIDATE_TETRA_BUDGET,
    PHResult,
    compute_rips_ph,
    persistence_summary,
)
from trajectory_tda.embedding.ngram_embed import ngram_embed  # noqa: E402
from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint  # noqa: E402
from trajectory_tda.scripts.stage1._battery_core import (  # noqa: E402
    landscape_l2_distance,
    landscape_on_grid,
)
from trajectory_tda.topology.permutation_nulls import (  # noqa: E402
    LandmarkNormalizer,
    _median_pairwise_distance,
    _pairwise_distance_scale,
    _single_permutation,
)
from trajectory_tda.topology.trajectory_ph import maxmin_landmarks  # noqa: E402
from trajectory_tda.topology.vectorisation import (  # noqa: E402
    compute_w2_ratio_bca_ci,
    wasserstein_distance as compute_wasserstein,
)

LOGGER = logging.getLogger(__name__)

USOC_REL = Path("results/trajectory_tda_integration")
H2_REL = USOC_REL / "h2_check"
SCHEMA_VERSION = "stage1/t1-5d-h2-dispersion-dualmetric/v1"
TASK_LABEL = "T1.5d H2 dispersion-control dual-metric diagnostic"
PREREG_REL = USOC_REL / "stage1" / "pre_registrations_h2_dispersion_2026-06-18.json"
CONDITIONS: tuple[Literal["raw", "normalized"], ...] = ("raw", "normalized")
CHARACTERIZATION_SCHEMA_VERSION = "stage1/t1-5e-h2-characterization/v1"
CHARACTERIZATION_TASK_LABEL = "H2 residual characterization diagnostic"
CHARACTERIZATION_PREREG_REL = USOC_REL / "stage1" / "pre_registrations_h2_characterization_2026-06-19.json"
NORMALIZERS: tuple[LandmarkNormalizer, ...] = ("median-pdist", "max-pdist", "mean-pdist")
ROBUSTNESS_NORMALIZERS: tuple[LandmarkNormalizer, ...] = ("max-pdist", "mean-pdist")
PERSISTENCE_BANDS: tuple[dict[str, float | str | None], ...] = (
    {"name": "near_diagonal", "lo": 0.0, "hi": 0.01},
    {"name": "low_persistence", "lo": 0.01, "hi": 0.025},
    {"name": "moderate_persistence", "lo": 0.025, "hi": 0.05},
    {"name": "large_persistence", "lo": 0.05, "hi": None},
)

SCALE_LABELS: dict[LandmarkNormalizer, str] = {
    "none": "median_pairwise_distance",
    "median-pdist": "median_pairwise_distance",
    "max-pdist": "max_pairwise_distance",
    "mean-pdist": "mean_pairwise_distance",
}


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


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")
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


def _raise_if_max_hours_exceeded(args: argparse.Namespace) -> None:
    max_hours = float(getattr(args, "max_hours", 0.0) or 0.0)
    started_at = getattr(args, "_started_at", None)
    if max_hours <= 0.0 or started_at is None:
        return
    elapsed_hours = (time.time() - float(started_at)) / 3600.0
    if elapsed_hours > max_hours:
        raise TimeoutError(f"max_hours={max_hours} exceeded after {elapsed_hours:.3f}h; checkpoints are saved")


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


def _normalize_landmarks(
    landmarks: np.ndarray,
    normalizer: LandmarkNormalizer,
) -> tuple[np.ndarray, float]:
    if normalizer == "none":
        raise ValueError("normalizer='none' cannot be used to normalize landmarks")
    scale = _pairwise_distance_scale(landmarks, normalizer)
    return np.asarray(landmarks, dtype=np.float64) / scale, float(scale)


def _normalize_landmarks_by_median_pdist(landmarks: np.ndarray) -> tuple[np.ndarray, float]:
    return _normalize_landmarks(landmarks, "median-pdist")


def _normalization_payload(
    enabled: bool,
    scale: float,
    n_landmarks: int,
    normalizer: LandmarkNormalizer,
) -> dict[str, Any]:
    return {
        "enabled": bool(enabled),
        "normalizer": normalizer,
        "scale": SCALE_LABELS[normalizer],
        "scale_value": float(scale),
        "landmark_count_for_scale": int(n_landmarks),
    }


def _compute_observed_ph(
    landmarks: np.ndarray,
    *,
    normalize: bool,
    normalizer: LandmarkNormalizer,
    args: argparse.Namespace,
) -> tuple[PHResult, dict[str, Any], float, float]:
    if normalize:
        landmarks_for_ph, scale = _normalize_landmarks(landmarks, normalizer)
    else:
        scale = _pairwise_distance_scale(landmarks, normalizer)
        landmarks_for_ph = np.asarray(landmarks, dtype=np.float64)

    started = time.time()
    ph = compute_rips_ph(
        landmarks_for_ph,
        timeout_seconds=float(args.ph_timeout_seconds),
        **_base_ph_kwargs(args),
    )
    elapsed = time.time() - started
    provenance = _ph_provenance(ph)
    provenance["normalization"] = _normalization_payload(normalize, scale, landmarks_for_ph.shape[0], normalizer)
    return ph, provenance, float(scale), float(elapsed)


def _finite_dgm_from_ph(ph: PHResult, dim: int) -> np.ndarray:
    dgm = ph.dgms.get(dim, np.empty((0, 2)))
    arr = np.asarray(dgm, dtype=np.float64).reshape(-1, 2) if len(dgm) else np.empty((0, 2))
    if arr.shape[0] > 0:
        arr = arr[np.isfinite(arr).all(axis=1)]
    return arr


def _diagram_from_result(result: dict[str, Any], key: str) -> np.ndarray:
    dgm = result.get(f"{key}_dgm", [])
    arr = np.asarray(dgm, dtype=np.float64).reshape(-1, 2) if dgm else np.empty((0, 2))
    if arr.shape[0] > 0:
        arr = arr[np.isfinite(arr).all(axis=1)]
    return arr


def _wasserstein_between_diagrams(dgm_a: np.ndarray, dgm_b: np.ndarray, dim: int) -> float:
    return float(compute_wasserstein(PHResult(dgms={dim: dgm_a}), PHResult(dgms={dim: dgm_b}), dim=dim))


def _landscape_l2_between_diagrams(
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


def _draw_null_pairs(n_permutations: int, seed: int, cap: int) -> list[tuple[int, int]]:
    n_pairs = min(cap, n_permutations * (n_permutations - 1) // 2)
    rng = np.random.RandomState(seed)
    pairs: list[tuple[int, int]] = []
    for _ in range(n_pairs):
        i, j = rng.choice(n_permutations, size=2, replace=False)
        pairs.append((int(i), int(j)))
    return pairs


def _summary_stats(values: list[float | None]) -> dict[str, float | int | None]:
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


def _diagram_location_summary(dgm: np.ndarray) -> dict[str, Any]:
    if dgm.shape[0] == 0:
        return {
            "n_finite": 0,
            "birth_median": None,
            "death_median": None,
            "persistence_median": None,
            "birth_mean": None,
            "death_mean": None,
            "persistence_mean": None,
        }
    persistence = dgm[:, 1] - dgm[:, 0]
    return {
        "n_finite": int(dgm.shape[0]),
        "birth_median": float(np.median(dgm[:, 0])),
        "death_median": float(np.median(dgm[:, 1])),
        "persistence_median": float(np.median(persistence)),
        "birth_mean": float(np.mean(dgm[:, 0])),
        "death_mean": float(np.mean(dgm[:, 1])),
        "persistence_mean": float(np.mean(persistence)),
    }


def _summarise_null_h2_locations(null_results: list[dict[str, Any]]) -> dict[str, Any]:
    per_null = [_diagram_location_summary(_diagram_from_result(result, "H2")) for result in null_results]
    non_empty = [
        _diagram_from_result(result, "H2") for result in null_results if _diagram_from_result(result, "H2").shape[0]
    ]
    pooled = np.vstack(non_empty) if non_empty else np.empty((0, 2))
    return {
        "per_null_h2_medians": per_null,
        "birth_median_summary": _summary_stats([entry["birth_median"] for entry in per_null]),
        "death_median_summary": _summary_stats([entry["death_median"] for entry in per_null]),
        "persistence_median_summary": _summary_stats([entry["persistence_median"] for entry in per_null]),
        "pooled_h2_features": _diagram_location_summary(pooled),
    }


def _metric_stats(
    obs_null: np.ndarray,
    null_null_all: list[float],
    *,
    n_effect_pairs: int,
    n_pvalue_pairs: int,
    seed: int,
) -> dict[str, Any]:
    null_null_effect = np.asarray(null_null_all[:n_effect_pairs], dtype=np.float64)
    null_null_pvalue = np.asarray(null_null_all[:n_pvalue_pairs], dtype=np.float64)
    mean_obs_null = float(np.mean(obs_null))
    mean_null_null = float(np.mean(null_null_effect)) if len(null_null_effect) else float("nan")
    t_ratio = mean_obs_null / mean_null_null if mean_null_null > 0 else float("nan")
    exceedance_count = int(np.sum(null_null_pvalue >= mean_obs_null))
    n_draws = int(len(null_null_pvalue))
    p_value = float((exceedance_count + 1) / (n_draws + 1)) if n_draws else float("nan")
    null_std = float(np.std(null_null_effect)) if len(null_null_effect) > 1 else float("nan")
    d_perm = (mean_obs_null - mean_null_null) / null_std if null_std > 0 else float("nan")

    bca_ci_lower: float | None = None
    bca_ci_upper: float | None = None
    if len(obs_null) >= 2 and len(null_null_effect) >= 2:
        try:
            _, bca_ci_lower, bca_ci_upper = compute_w2_ratio_bca_ci(obs_null, null_null_effect, seed=seed)
        except Exception as exc:
            LOGGER.warning("BCa CI failed: %s", exc)

    return {
        "mean_obs_null": mean_obs_null,
        "std_obs_null": float(np.std(obs_null)),
        "median_obs_null": float(np.median(obs_null)),
        "mean_null_null": mean_null_null,
        "std_null_null": None if not np.isfinite(null_std) else null_std,
        "t_ratio": t_ratio,
        "bca_ci_lower": bca_ci_lower,
        "bca_ci_upper": bca_ci_upper,
        "d_perm": d_perm,
        "p_value": p_value,
        "exceedance_count": exceedance_count,
        "pvalue_null_draws": n_draws,
        "effect_null_pairs": int(len(null_null_effect)),
        "significant_at_005": bool(p_value < 0.05),
        "obs_null_distribution": obs_null.tolist(),
        "null_null_distribution": null_null_effect.tolist(),
    }


def _aggregate_h2_dual_metric(
    null_results: list[dict[str, Any]],
    ph_obs: PHResult,
    *,
    seed: int,
    n_null_pairs_cap: int,
    k_max: int,
    n_points: int,
) -> dict[str, Any]:
    n_permutations = len(null_results)
    total_pairs = n_permutations * (n_permutations - 1) // 2
    n_effect_pairs = min(int(n_null_pairs_cap), total_pairs)
    n_pvalue_pairs = min(n_permutations, total_pairs)
    pair_indices = _draw_null_pairs(n_permutations, seed=seed, cap=max(n_effect_pairs, n_pvalue_pairs))

    obs_h2 = _finite_dgm_from_ph(ph_obs, 2)
    null_h2 = [_diagram_from_result(result, "H2") for result in null_results]
    obs_null_w2 = np.asarray([float(result["H2"]) for result in null_results], dtype=np.float64)
    null_null_w2 = [_wasserstein_between_diagrams(null_h2[i], null_h2[j], 2) for i, j in pair_indices]

    obs_null_land = np.asarray(
        [_landscape_l2_between_diagrams(obs_h2, dgm, k_max=k_max, n_points=n_points) for dgm in null_h2],
        dtype=np.float64,
    )
    null_null_land = [
        _landscape_l2_between_diagrams(null_h2[i], null_h2[j], k_max=k_max, n_points=n_points) for i, j in pair_indices
    ]

    return {
        "dim": "H2",
        "pair_draw_seed": int(seed),
        "pair_indices": [[int(i), int(j)] for i, j in pair_indices[:n_effect_pairs]],
        "pvalue_pair_indices": [[int(i), int(j)] for i, j in pair_indices[:n_pvalue_pairs]],
        "w2": _metric_stats(
            obs_null_w2,
            null_null_w2,
            n_effect_pairs=n_effect_pairs,
            n_pvalue_pairs=n_pvalue_pairs,
            seed=seed,
        ),
        "landscape_l2": _metric_stats(
            obs_null_land,
            null_null_land,
            n_effect_pairs=n_effect_pairs,
            n_pvalue_pairs=n_pvalue_pairs,
            seed=seed,
        ),
    }


def _checkpoint_params(
    *,
    condition: str,
    L: int,
    B: int,
    seed: int,
    normalize: bool,
    normalizer: LandmarkNormalizer,
    ph_kwargs: dict[str, Any],
    k_max: int,
    n_points: int,
) -> dict[str, Any]:
    return {
        "schema_version": "stage1/t1-5d-condition-checkpoint/v1",
        "condition": condition,
        "L": int(L),
        "B": int(B),
        "seed": int(seed),
        "null": "markov-1",
        "markov_order": 1,
        "normalize_landmarks_by_median_pdist": bool(normalize and normalizer == "median-pdist"),
        "normalize_landmarks_by_pairwise_scale": bool(normalize),
        "landmark_normalizer": normalizer,
        "statistic": "wasserstein-plus-landscape-l2",
        "landscape_k_max": int(k_max),
        "landscape_n_points": int(n_points),
        "ph_kwargs": _jsonable(ph_kwargs),
    }


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
        "schema_version": "stage1/t1-5d-condition-checkpoint/v1",
        "updated_at": _now_iso(),
        "params": _jsonable(params),
        "completed_count": len(completed),
        "total": int(params["B"]),
        "results_by_index": completed,
    }
    _write_json_atomic(path, payload)


def _run_condition_permutation(
    index: int,
    *,
    condition: str,
    normalize: bool,
    normalizer: LandmarkNormalizer,
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    seed: int,
    n_landmarks: int,
    embed_kwargs: dict[str, Any],
    frozen_models: dict[str, Any],
    ph_observed: PHResult,
    ph_kwargs: dict[str, Any],
) -> tuple[int, dict[str, Any], float]:
    started = time.time()
    result = _single_permutation(
        "markov",
        embeddings,
        trajectories,
        None,
        seed,
        2,
        n_landmarks,
        "wasserstein",
        1,
        embed_kwargs,
        frozen_models=frozen_models,
        ph_observed=ph_observed,
        dedup=False,
        ph_kwargs=ph_kwargs,
        normalize_landmarks_by_median_pdist=normalize,
        landmark_normalizer=normalizer if normalize else "none",
    )
    elapsed = time.time() - started
    result["_condition"] = condition
    result["_permutation_index"] = int(index)
    result["_wall_time_seconds"] = float(elapsed)
    return index, result, elapsed


def _summarise_null_ph_provenance(null_results: list[dict[str, Any]]) -> dict[str, Any]:
    provenance = [result.get("_ph_provenance", {}) for result in null_results]
    normalizations = [p.get("normalization", {}) for p in provenance]
    return {
        "threshold_value": _summary_stats([p.get("threshold_value") for p in provenance]),
        "edge_prop_at_thresh": _summary_stats([p.get("edge_prop_at_thresh") for p in provenance]),
        "candidate_tetrahedra_burden": _summary_stats([p.get("candidate_tetrahedra_burden") for p in provenance]),
        "wall_time_seconds": _summary_stats([p.get("wall_time_seconds") for p in provenance]),
        "pairwise_scale": _summary_stats([n.get("scale_value") for n in normalizations]),
        "normalizers": sorted({str(n.get("normalizer", "unknown")) for n in normalizations}),
    }


def _filter_by_persistence_band(dgm: np.ndarray, lo: float, hi: float | None) -> np.ndarray:
    if dgm.shape[0] == 0:
        return dgm
    persistence = dgm[:, 1] - dgm[:, 0]
    mask = persistence >= lo
    if hi is not None:
        mask &= persistence < hi
    return dgm[mask]


def _feature_count_summary_by_band(diagrams: list[np.ndarray]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for band in PERSISTENCE_BANDS:
        name = str(band["name"])
        lo = float(band["lo"])
        hi = None if band["hi"] is None else float(band["hi"])
        counts = [int(_filter_by_persistence_band(dgm, lo, hi).shape[0]) for dgm in diagrams]
        summary[name] = {
            "lo_inclusive": lo,
            "hi_exclusive": hi,
            "count_summary": _summary_stats(counts),
        }
    return summary


def _stratify_h2_residual(
    obs_h2: np.ndarray,
    null_h2: list[np.ndarray],
    *,
    total_mean_obs_null_w2: float,
) -> dict[str, Any]:
    bands: dict[str, Any] = {}
    for band in PERSISTENCE_BANDS:
        name = str(band["name"])
        lo = float(band["lo"])
        hi = None if band["hi"] is None else float(band["hi"])
        obs_band = _filter_by_persistence_band(obs_h2, lo, hi)
        null_bands = [_filter_by_persistence_band(dgm, lo, hi) for dgm in null_h2]
        band_w2 = [_wasserstein_between_diagrams(obs_band, null_band, 2) for null_band in null_bands]
        band_mean = float(np.mean(band_w2)) if band_w2 else 0.0
        bands[name] = {
            "lo_inclusive": lo,
            "hi_exclusive": hi,
            "observed_feature_count": int(obs_band.shape[0]),
            "null_feature_count_summary": _summary_stats([dgm.shape[0] for dgm in null_bands]),
            "mean_obs_null_band_restricted_w2": band_mean,
            "share_of_total_mean_obs_null_w2": (
                float(band_mean / total_mean_obs_null_w2) if total_mean_obs_null_w2 > 0 else None
            ),
        }

    ranked = sorted(
        bands.items(),
        key=lambda item: -1.0
        if item[1]["share_of_total_mean_obs_null_w2"] is None
        else -float(item[1]["share_of_total_mean_obs_null_w2"]),
    )
    top_band = ranked[0][0] if ranked else None
    return {
        "method": (
            "Band-restricted W2 diagnostic: recompute H2 W2 after filtering both diagrams by persistence band; "
            "shares are descriptive and not an exact optimal-transport cost decomposition."
        ),
        "feature_counts_by_band": {
            "observed": _feature_count_summary_by_band([obs_h2]),
            "null": _feature_count_summary_by_band(null_h2),
        },
        "w2_band_diagnostics": bands,
        "top_band_by_w2_share": top_band,
    }


def _run_condition(
    *,
    args: argparse.Namespace,
    condition: str,
    B: int,
    normalizer: LandmarkNormalizer,
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    embed_kwargs: dict[str, Any],
    frozen_models: dict[str, Any],
    obs_landmarks: np.ndarray,
    checkpoint_dir: Path,
) -> dict[str, Any]:
    normalize = normalizer != "none"
    LOGGER.info("Running L=%d condition=%s normalizer=%s B=%d", obs_landmarks.shape[0], condition, normalizer, B)
    ph_obs, obs_provenance, obs_scale, observed_seconds = _compute_observed_ph(
        obs_landmarks,
        normalize=normalize,
        normalizer=normalizer,
        args=args,
    )

    worker_ph_kwargs = _base_ph_kwargs(args)
    if int(args.n_jobs) == 1:
        worker_ph_kwargs["timeout_seconds"] = float(args.ph_timeout_seconds)
    else:
        LOGGER.info(
            "Parallel null PH uses joblib worker timeout instead of nested compute_rips_ph child timeout "
            "(avoids Windows loky/spawn start-method collision)."
        )

    checkpoint_path = checkpoint_dir / f"L{obs_landmarks.shape[0]}_{condition}_B{B}_seed{args.seed}.json"
    params = _checkpoint_params(
        condition=condition,
        L=obs_landmarks.shape[0],
        B=B,
        seed=args.seed,
        normalize=normalize,
        normalizer=normalizer,
        ph_kwargs=worker_ph_kwargs,
        k_max=args.landscape_k_max,
        n_points=args.landscape_n_points,
    )
    completed = _load_condition_checkpoint(checkpoint_path, params, args.resume)

    missing = [idx for idx in range(B) if str(idx) not in completed]
    if missing:
        seeds = [int(args.seed) + idx + 1 for idx in range(B)]
        joblib_timeout = None if int(args.n_jobs) == 1 else float(args.ph_timeout_seconds) * 2.0
        chunk_size = max(1, int(args.n_jobs) if int(args.n_jobs) > 0 else 4)
        for offset in range(0, len(missing), chunk_size):
            _raise_if_max_hours_exceeded(args)
            chunk = missing[offset : offset + chunk_size]
            generated = Parallel(
                n_jobs=int(args.n_jobs),
                verbose=10 if args.verbose_joblib else 0,
                return_as="generator_unordered",
                timeout=joblib_timeout,
            )(
                delayed(_run_condition_permutation)(
                    idx,
                    condition=condition,
                    normalize=normalize,
                    normalizer=normalizer,
                    embeddings=embeddings,
                    trajectories=trajectories,
                    seed=seeds[idx],
                    n_landmarks=obs_landmarks.shape[0],
                    embed_kwargs=embed_kwargs,
                    frozen_models=frozen_models,
                    ph_observed=ph_obs,
                    ph_kwargs=worker_ph_kwargs,
                )
                for idx in chunk
            )
            try:
                for idx, result, _elapsed in generated:
                    completed[str(idx)] = _jsonable(result)
                    _save_condition_checkpoint(checkpoint_path, params, completed)
                    LOGGER.info(
                        "  %s L=%d permutation %d/%d complete",
                        condition,
                        obs_landmarks.shape[0],
                        len(completed),
                        B,
                    )
            except BaseException:
                _save_condition_checkpoint(checkpoint_path, params, completed)
                raise
            _raise_if_max_hours_exceeded(args)

    null_results = [completed[str(idx)] for idx in range(B)]
    metrics = _aggregate_h2_dual_metric(
        null_results,
        ph_obs,
        seed=int(args.seed),
        n_null_pairs_cap=int(args.n_null_pairs_cap),
        k_max=int(args.landscape_k_max),
        n_points=int(args.landscape_n_points),
    )
    obs_h2 = _finite_dgm_from_ph(ph_obs, 2)
    null_h2 = [_diagram_from_result(result, "H2") for result in null_results]
    mean_total_w2 = float(metrics["w2"]["mean_obs_null"])
    return {
        "condition": condition,
        "L": int(obs_landmarks.shape[0]),
        "B": int(B),
        "n_jobs": int(args.n_jobs),
        "seed": int(args.seed),
        "null": "markov-1",
        "markov_order": 1,
        "ph_method": "ripser",
        "maxdim": 2,
        "do_cocycles": False,
        "threshold_rule": (
            f"per-cloud-auto-p75-on-{normalizer}-normalized-distances" if normalize else "per-cloud-auto-p75-raw"
        ),
        "normalization": _normalization_payload(normalize, obs_scale, obs_landmarks.shape[0], normalizer),
        "landscape": {
            "k_max": int(args.landscape_k_max),
            "n_points": int(args.landscape_n_points),
        },
        "wasserstein": {
            "order": 2,
            "internal_p": 2,
        },
        "null_worker_timeout_mode": "compute_rips_ph_child" if int(args.n_jobs) == 1 else "joblib_worker_timeout",
        "observed": {
            "vertex_count": int(obs_landmarks.shape[0]),
            "scale_value": float(obs_scale),
            "h2_birth_death": _diagram_location_summary(obs_h2),
            "ph_summary": persistence_summary(ph_obs),
            "ph_provenance": obs_provenance,
            "wall_time_seconds": float(observed_seconds),
        },
        "null_h2_birth_death": _summarise_null_h2_locations(null_results),
        "null_ph_provenance_summary": _summarise_null_ph_provenance(null_results),
        "null_ph_provenance": [result.get("_ph_provenance", {}) for result in null_results],
        "permutation_wall_times_seconds": [float(result.get("_wall_time_seconds", 0.0)) for result in null_results],
        "checkpoint_path": str(checkpoint_path),
        "stratification": _stratify_h2_residual(obs_h2, null_h2, total_mean_obs_null_w2=mean_total_w2),
        "metrics": {"H2": metrics},
    }


def _decision_branch(results: dict[str, Any], alpha: float) -> dict[str, Any]:
    rejecting_cells: list[dict[str, Any]] = []
    for l_key, payload in results.items():
        h2 = payload["normalized"]["metrics"]["H2"]
        w2_p = float(h2["w2"]["p_value"])
        landscape_p = float(h2["landscape_l2"]["p_value"])
        if w2_p < alpha or landscape_p < alpha:
            rejecting_cells.append(
                {
                    "L": int(payload["normalized"]["L"]),
                    "w2_p_value": w2_p,
                    "landscape_l2_p_value": landscape_p,
                    "w2_rejects": bool(w2_p < alpha),
                    "landscape_l2_rejects": bool(landscape_p < alpha),
                }
            )
    return {
        "alpha": float(alpha),
        "branch": "stop_and_escalate" if rejecting_cells else "restriction_stands",
        "restriction_stands": not rejecting_cells,
        "rejecting_normalized_cells": rejecting_cells,
        "rule": (
            "Restriction stands only if normalized H2 W2 p>=0.05 and normalized H2 "
            "landscape-L2 p>=0.05 at both L=200 and L=300."
        ),
    }


def _sign(value: float | None, *, eps: float = 1e-12) -> str:
    if value is None or not np.isfinite(value):
        return "missing"
    if value > eps:
        return "positive"
    if value < -eps:
        return "negative"
    return "zero"


def _normalizer_direction(payload: dict[str, Any]) -> dict[str, Any]:
    observed = payload["observed"]["h2_birth_death"]
    null_summary = payload["null_h2_birth_death"]
    null_birth = null_summary["birth_median_summary"]["median"]
    null_death = null_summary["death_median_summary"]["median"]
    obs_birth = observed["birth_median"]
    obs_death = observed["death_median"]
    birth_delta = None if obs_birth is None or null_birth is None else float(obs_birth) - float(null_birth)
    death_delta = None if obs_death is None or null_death is None else float(obs_death) - float(null_death)
    return {
        "observed_birth_median": obs_birth,
        "null_birth_median_of_medians": null_birth,
        "birth_delta_observed_minus_null": birth_delta,
        "birth_direction": _sign(birth_delta),
        "observed_death_median": obs_death,
        "null_death_median_of_medians": null_death,
        "death_delta_observed_minus_null": death_delta,
        "death_direction": _sign(death_delta),
    }


def _dual_metric_flags(payload: dict[str, Any], alpha: float) -> dict[str, Any]:
    h2 = payload["metrics"]["H2"]
    w2_p = float(h2["w2"]["p_value"])
    landscape_p = float(h2["landscape_l2"]["p_value"])
    return {
        "w2_p_value": w2_p,
        "landscape_l2_p_value": landscape_p,
        "w2_rejects": bool(w2_p < alpha),
        "landscape_l2_rejects": bool(landscape_p < alpha),
        "dual_metric_rejects": bool(w2_p < alpha and landscape_p < alpha),
        "w2_t_ratio": float(h2["w2"]["t_ratio"]),
        "landscape_l2_t_ratio": float(h2["landscape_l2"]["t_ratio"]),
    }


def _characterization_decision(
    results: dict[str, Any],
    *,
    alpha: float,
    power_alpha: float,
) -> dict[str, Any]:
    per_l: list[dict[str, Any]] = []
    robust_l: list[int] = []
    for l_key, normalizer_payloads in results.items():
        median_payload = normalizer_payloads["median-pdist"]
        median_direction = _normalizer_direction(median_payload)
        median_power = _dual_metric_flags(median_payload, power_alpha)
        normalizer_rows: list[dict[str, Any]] = []
        support_count = 0
        sign_flip_count = 0
        for normalizer in NORMALIZERS:
            payload = normalizer_payloads[normalizer]
            direction = _normalizer_direction(payload)
            flags = _dual_metric_flags(payload, power_alpha if normalizer == "median-pdist" else alpha)
            same_direction = (
                direction["birth_direction"] == median_direction["birth_direction"]
                and direction["death_direction"] == median_direction["death_direction"]
                and direction["birth_direction"] not in {"missing", "zero"}
                and direction["death_direction"] not in {"missing", "zero"}
            )
            sign_flip = (
                direction["birth_direction"] not in {"missing", "zero"}
                and median_direction["birth_direction"] not in {"missing", "zero"}
                and direction["birth_direction"] != median_direction["birth_direction"]
            ) or (
                direction["death_direction"] not in {"missing", "zero"}
                and median_direction["death_direction"] not in {"missing", "zero"}
                and direction["death_direction"] != median_direction["death_direction"]
            )
            supports = bool(flags["dual_metric_rejects"] and same_direction)
            if supports:
                support_count += 1
            if sign_flip:
                sign_flip_count += 1
            normalizer_rows.append(
                {
                    "normalizer": normalizer,
                    "direction": direction,
                    "metrics": flags,
                    "same_direction_as_median": bool(same_direction),
                    "sign_flip_vs_median": bool(sign_flip),
                    "supports_residual": supports,
                }
            )

        l_value = int(normalizer_payloads["median-pdist"]["L"])
        power_confirmed = bool(median_power["dual_metric_rejects"])
        robust = bool(power_confirmed and support_count >= 2 and sign_flip_count == 0)
        if robust:
            robust_l.append(l_value)
        per_l.append(
            {
                "L": l_value,
                "median_power_confirmed_at_001": power_confirmed,
                "supporting_normalizer_count": int(support_count),
                "sign_flip_count": int(sign_flip_count),
                "robust_by_pre_registered_rule": robust,
                "normalizers": normalizer_rows,
            }
        )

    branch = "stop_and_escalate" if len(robust_l) == len(results) else "restriction_stands"
    return {
        "alpha": float(alpha),
        "power_alpha": float(power_alpha),
        "branch": branch,
        "restriction_stands": branch == "restriction_stands",
        "robust_L_values": robust_l,
        "per_L": per_l,
        "rule": (
            "Residual is robust only if the median-pdist B=1000 dual-metric cell rejects at p<0.01 "
            "and at least two of median/max/mean-pdist have same-direction birth/death shifts with "
            "dual-metric rejection; sign flips trigger non-robust classification."
        ),
    }


def _embedding_dependence_assessment(args: argparse.Namespace) -> dict[str, Any]:
    integration_root = args.proj_root / USOC_REL
    legacy_embedding = integration_root / "embeddings.npy"
    legacy_metadata = integration_root / "02_embedding.json"
    legacy_h2_result = integration_root / "h2_check" / "04_nulls_wasserstein_h2_L1000_20260502.json"
    model_candidates = [
        integration_root / "02_scaler.joblib",
        integration_root / "02_pca.joblib",
        integration_root / "embedding_scaler.joblib",
        integration_root / "embedding_pca.joblib",
    ]
    found_models = [path for path in model_candidates if path.exists()]
    status = "not_rerun"
    reason = (
        "Legacy embeddings and the 2026-05-02 L=1000 H2 result are present, but no serialized "
        "pre-refreeze scaler/PCA model was found. A fair Markov-null rerun would need that model "
        "to transform synthetic trajectories through the same coordinate system; refitting PCA per "
        "draw would reproduce the old unfrozen bug rather than a representation-robustness cell."
    )
    if found_models:
        status = "recoverable_not_run"
        reason = (
            "Potential legacy model files were found, but this driver only records the feasibility "
            "assessment until a Manager-approved exact pre-refreeze rerun shape is specified."
        )
    return {
        "status": status,
        "reason": reason,
        "checked_paths": {
            "legacy_embedding": str(legacy_embedding),
            "legacy_embedding_exists": legacy_embedding.exists(),
            "legacy_metadata": str(legacy_metadata),
            "legacy_metadata_exists": legacy_metadata.exists(),
            "legacy_h2_result": str(legacy_h2_result),
            "legacy_h2_result_exists": legacy_h2_result.exists(),
            "model_candidates": [str(path) for path in model_candidates],
            "found_model_candidates": [str(path) for path in found_models],
        },
        "caveat": (
            "The committed characterization result should be read as current frozen-representation evidence; "
            "the pre-refreeze discrepancy remains a representation-robustness caveat."
        ),
    }


def _save_run_progress(path: Path, payload: dict[str, Any]) -> None:
    progress = {
        "schema_version": "stage1/h2-characterization-progress/v1",
        "updated_at": _now_iso(),
        **payload,
    }
    _write_json_atomic(path, progress)


def _characterization_estimate(args: argparse.Namespace, n_l: int) -> dict[str, Any]:
    observed_calls = n_l * (1 + len(ROBUSTNESS_NORMALIZERS))
    null_calls = n_l * (int(args.primary_B) + len(ROBUSTNESS_NORMALIZERS) * int(args.robustness_B))
    estimated_wall_seconds = observed_calls * float(args.estimate_seconds_per_observed) + null_calls * float(
        args.estimate_seconds_per_null
    ) / max(1, int(args.n_jobs))
    return {
        "estimated_ph_calls": int(observed_calls + null_calls),
        "estimated_observed_calls": int(observed_calls),
        "estimated_null_calls": int(null_calls),
        "estimate_seconds_per_observed": float(args.estimate_seconds_per_observed),
        "estimate_seconds_per_null": float(args.estimate_seconds_per_null),
        "estimated_wall_seconds": float(estimated_wall_seconds),
        "estimated_wall_minutes": float(estimated_wall_seconds / 60.0),
        "estimated_wall_hours": float(estimated_wall_seconds / 3600.0),
        "available_memory_gb_at_start": _available_physical_memory_gb(),
        "note": "Primary median-pdist B=1000 cells dominate; max/mean B=50 cells add robustness coverage.",
    }


def run_characterization(args: argparse.Namespace) -> Path:
    started = time.time()
    setattr(args, "_started_at", started)
    checkpoint_root = args.proj_root / USOC_REL
    embeddings, trajectories, embed_kwargs, frozen_models = _load_frozen_usoc(checkpoint_root)
    checkpoint_dir = args.checkpoint_dir or (
        args.proj_root / H2_REL / "intermediates" / f"h2_characterization_{args.run_date}"
    )
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    progress_path = checkpoint_dir / "progress.json"
    output_path = args.output_path or (args.worktree_root / H2_REL / f"h2_characterization_{args.run_date}.json")
    estimate = _characterization_estimate(args, len(args.Ls))
    LOGGER.info(
        "Pre-launch characterization estimate: %d PH calls; %.2f hours at n_jobs=%d using %.1fs/null",
        estimate["estimated_ph_calls"],
        estimate["estimated_wall_hours"],
        args.n_jobs,
        estimate["estimate_seconds_per_null"],
    )

    results: dict[str, Any] = {}
    completed_cells: list[dict[str, Any]] = []
    _save_run_progress(
        progress_path,
        {
            "status": "running",
            "run_date": args.run_date,
            "estimate": estimate,
            "completed_cells": completed_cells,
        },
    )
    for L in args.Ls:
        actual_l = min(int(L), embeddings.shape[0])
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_l, seed=int(args.seed))
        LOGGER.info("L=%d observed median-pdist scale=%.6f", actual_l, _median_pairwise_distance(obs_landmarks))
        l_checkpoint_dir = checkpoint_dir / f"L{actual_l}"
        l_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        normalizer_payloads: dict[str, Any] = {}
        for normalizer, B, role in [
            ("median-pdist", int(args.primary_B), "power"),
            ("max-pdist", int(args.robustness_B), "normalizer_robustness"),
            ("mean-pdist", int(args.robustness_B), "normalizer_robustness"),
        ]:
            condition = f"{role}_{normalizer}"
            normalizer_payloads[normalizer] = _run_condition(
                args=args,
                condition=condition,
                B=B,
                normalizer=normalizer,
                embeddings=embeddings,
                trajectories=trajectories,
                embed_kwargs=embed_kwargs,
                frozen_models=frozen_models,
                obs_landmarks=obs_landmarks,
                checkpoint_dir=l_checkpoint_dir,
            )
            completed_cells.append({"L": actual_l, "normalizer": normalizer, "B": B, "role": role})
            _save_run_progress(
                progress_path,
                {
                    "status": "running",
                    "run_date": args.run_date,
                    "estimate": estimate,
                    "completed_cells": completed_cells,
                },
            )
        results[f"L{actual_l}"] = normalizer_payloads

    decision = _characterization_decision(results, alpha=float(args.alpha), power_alpha=float(args.power_alpha))
    payload = {
        "schema_version": CHARACTERIZATION_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "task": CHARACTERIZATION_TASK_LABEL,
        "pre_registration": str(args.proj_root / CHARACTERIZATION_PREREG_REL),
        "phase": "Residual characterization; no vault result claim by Worker.",
        "inputs": {
            "canonical_embedding_source": str(checkpoint_root / "embeddings.npy"),
            "trajectory_source": str(checkpoint_root / "01_trajectories_sequences.json"),
            "embedding_metadata_source": str(checkpoint_root / "02_embedding.json"),
            "git_head": _git_head(args.worktree_root),
        },
        "params": {
            "Ls": [int(L) for L in args.Ls],
            "primary_B": int(args.primary_B),
            "robustness_B": int(args.robustness_B),
            "seed": int(args.seed),
            "maxdim": 2,
            "null": "markov-1",
            "markov_order": 1,
            "normalizers": list(NORMALIZERS),
            "metrics": ["wasserstein-2", "landscape-l2"],
            "landscape_k_max": int(args.landscape_k_max),
            "landscape_n_points": int(args.landscape_n_points),
            "p_value_formula": "(r + 1) / (n + 1), with n recorded as pvalue_null_draws per cell",
            "alpha": float(args.alpha),
            "power_alpha": float(args.power_alpha),
            "ph_method": "ripser",
            "do_cocycles": False,
            "h2_tetra_budget": float(args.h2_tetra_budget),
            "ph_timeout_seconds": float(args.ph_timeout_seconds),
            "n_jobs": int(args.n_jobs),
            "max_hours": float(args.max_hours),
            "n_null_pairs_cap": int(args.n_null_pairs_cap),
            "checkpoint_dir": str(checkpoint_dir),
            "progress_path": str(progress_path),
            "regeneration_command": " ".join(sys.argv),
        },
        "pre_launch_estimate": estimate,
        "elapsed_seconds": float(time.time() - started),
        "decision_branch": decision,
        "embedding_dependence": _embedding_dependence_assessment(args),
        "results": results,
        "manager_gate": "Manager reviews this JSON and files any vault decision claim.",
    }
    _write_json_no_overwrite(output_path, payload)
    _save_run_progress(
        progress_path,
        {
            "status": "complete",
            "run_date": args.run_date,
            "estimate": estimate,
            "completed_cells": completed_cells,
            "output_path": str(output_path),
            "decision_branch": decision["branch"],
            "elapsed_seconds": float(time.time() - started),
        },
    )
    LOGGER.info("Wrote H2 characterization JSON: %s", output_path)
    return output_path


def run_diagnostic(args: argparse.Namespace) -> Path:
    started = time.time()
    setattr(args, "_started_at", started)
    checkpoint_root = args.proj_root / USOC_REL
    embeddings, trajectories, embed_kwargs, frozen_models = _load_frozen_usoc(checkpoint_root)
    checkpoint_dir = args.checkpoint_dir or (
        args.proj_root / H2_REL / "intermediates" / f"h2_dispersion_dualmetric_{args.run_date}"
    )
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_path or (args.worktree_root / H2_REL / f"h2_dispersion_dualmetric_{args.run_date}.json")

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
        "available_memory_gb_at_start": _available_physical_memory_gb(),
        "note": "H2 PH calls dominate; H2-only dual-metric aggregation adds 500 null-null W2/L2 pairs per cell.",
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
        LOGGER.info("L=%d observed median-pdist scale=%.6f", actual_l, _median_pairwise_distance(obs_landmarks))
        l_checkpoint_dir = checkpoint_dir / f"L{actual_l}"
        l_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        condition_payloads: dict[str, Any] = {}
        for condition in CONDITIONS:
            condition_payloads[condition] = _run_condition(
                args=args,
                condition=condition,
                B=int(args.B),
                normalizer="median-pdist" if condition == "normalized" else "none",
                embeddings=embeddings,
                trajectories=trajectories,
                embed_kwargs=embed_kwargs,
                frozen_models=frozen_models,
                obs_landmarks=obs_landmarks,
                checkpoint_dir=l_checkpoint_dir,
            )
        results[f"L{actual_l}"] = condition_payloads

    decision = _decision_branch(results, alpha=float(args.alpha))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "task": TASK_LABEL,
        "pre_registration": str(args.proj_root / PREREG_REL),
        "phase": "Confirmatory dispersion-control diagnostic; no vault result claim by Worker.",
        "inputs": {
            "canonical_embedding_source": str(checkpoint_root / "embeddings.npy"),
            "trajectory_source": str(checkpoint_root / "01_trajectories_sequences.json"),
            "embedding_metadata_source": str(checkpoint_root / "02_embedding.json"),
            "git_head": _git_head(args.worktree_root),
        },
        "params": {
            "Ls": [int(L) for L in args.Ls],
            "B": int(args.B),
            "seed": int(args.seed),
            "maxdim": 2,
            "null": "markov-1",
            "markov_order": 1,
            "conditions": list(CONDITIONS),
            "decision_dim": "H2",
            "normalizer": "median pairwise distance of each L-landmark cloud",
            "metrics": ["wasserstein-2", "landscape-l2"],
            "landscape_k_max": int(args.landscape_k_max),
            "landscape_n_points": int(args.landscape_n_points),
            "p_value_formula": "(r + 1) / (B + 1), with B p-value null-null pair draws",
            "alpha": float(args.alpha),
            "ph_method": "ripser",
            "do_cocycles": False,
            "h2_tetra_budget": float(args.h2_tetra_budget),
            "ph_timeout_seconds": float(args.ph_timeout_seconds),
            "n_jobs": int(args.n_jobs),
            "n_null_pairs_cap": int(args.n_null_pairs_cap),
            "checkpoint_dir": str(checkpoint_dir),
            "regeneration_command": " ".join(sys.argv),
        },
        "pre_launch_estimate": estimate,
        "elapsed_seconds": float(time.time() - started),
        "decision_branch": decision,
        "results": results,
        "manager_gate": "Manager reviews this JSON and files any vault decision claim.",
    }
    _write_json_no_overwrite(output_path, payload)
    LOGGER.info("Wrote H2 dispersion-control diagnostic JSON: %s", output_path)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the H2 dispersion-control dual-metric diagnostic.")
    parser.add_argument("--suite", choices=["dispersion", "characterization"], default="dispersion")
    parser.add_argument("--proj-root", type=Path, default=PROJ_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=WORKTREE_ROOT)
    parser.add_argument("--run-date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--Ls", type=int, nargs="+", default=[200, 300])
    parser.add_argument("--B", type=int, default=50)
    parser.add_argument("--primary-B", type=int, default=1000)
    parser.add_argument("--robustness-B", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-jobs", type=int, default=4)
    parser.add_argument("--n-null-pairs-cap", type=int, default=500)
    parser.add_argument("--landscape-k-max", type=int, default=5)
    parser.add_argument("--landscape-n-points", type=int, default=200)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--power-alpha", type=float, default=0.01)
    parser.add_argument("--ph-timeout-seconds", type=float, default=300.0)
    parser.add_argument("--h2-tetra-budget", type=float, default=H2_CANDIDATE_TETRA_BUDGET)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--output-path", type=Path)
    parser.add_argument("--estimate-seconds-per-observed", type=float, default=20.0)
    parser.add_argument("--estimate-seconds-per-null", type=float, default=25.0)
    parser.add_argument("--max-hours", type=float, default=0.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verbose-joblib", action="store_true")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    if args.suite == "characterization":
        run_characterization(args)
    else:
        run_diagnostic(args)


if __name__ == "__main__":
    main()
