# DEPRECATED: replaced by trajectory_tda/scripts/stage1/ — kept until smoke-test
# equivalence is locked. Do not invoke for new headline or sensitivity runs; use
# the phase-split scripts (run_usoc_headline.py, run_bhps_headline.py,
# run_lm_sensitivity.py, run_landscape_sensitivity.py, assemble_battery.py).
# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Stage 1 headline battery — matched-L W2 + landscape L2 at L=5000, B=1000,
#   Markov-1 null, for USoc and BHPS independently. Produces the combined results JSON
#   required by T1.2 pre-registration (2026-05-13). Also runs cross-landmark and
#   landscape sensitivity for the supplement.
"""
Stage 1 matched-L W₂ + landscape L² battery.

Runs W₂ and landscape L² Markov-1 permutation tests for USoc and BHPS at the
pre-registered parameters (L=5000, B=1000, seed=42) and saves a combined JSON.
Also runs supplement sensitivity sweeps at B=100.

Usage:
    python -m trajectory_tda.scripts.run_stage1_battery \\
        --usoc-dir results/trajectory_tda_integration \\
        --bhps-dir results/trajectory_tda_bhps \\
        --output results/trajectory_tda_integration/stage1/matched_w2_battery_<date>.json

For a fast smoke test (B=10):
    python -m trajectory_tda.scripts.run_stage1_battery --n-perms 10 --n-perms-sens 5

Pre-registration: 2026-05-13 vault entry PRE-REGISTRATION — Matched-L W2 + Landscape L2 Battery
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Live phase-status file: latest current phase is written here (overwritten each
# transition) so external observers can `cat` or `tail -f` to see real-time state
# without depending on Python's buffered stdout. Set via STAGE1_STATUS_FILE env var.
_PHASE_STATUS_FILE = os.environ.get("STAGE1_STATUS_FILE")


def _write_status(phase: str, detail: str = "") -> None:
    """Write the current phase to STAGE1_STATUS_FILE (env var) if set.

    Appends so we keep a history of phase transitions; the tail of the file is the
    most recent state. Failures are silent — this is observability, not control flow.
    """
    if not _PHASE_STATUS_FILE:
        return
    try:
        line = f"{datetime.now().isoformat(timespec='seconds')} | {phase} | {detail}\n"
        with open(_PHASE_STATUS_FILE, "a") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass


# Pre-registered parameters (locked 2026-05-13)
DEFAULT_L = 5000
DEFAULT_B = 1000
DEFAULT_SEED = 42
DEFAULT_K_MAX = 5
DEFAULT_N_POINTS = 200
DEFAULT_MARKOV_ORDER = 1


def _convert_numpy(obj: object) -> object:
    """Recursively convert numpy types for JSON serialisation."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    return obj


def _w2_result_to_cell(h_result: dict) -> dict:
    """Extract the required fields from a permutation_test_trajectories H-dim result."""
    return {
        "w2_pvalue": h_result["p_value"],
        "lower_tail_pvalue": h_result.get("lower_tail_pvalue"),
        "t_ratio": h_result.get("t_ratio"),
        "bca_ci_lower": h_result.get("bca_ci_lower"),
        "bca_ci_upper": h_result.get("bca_ci_upper"),
        "d_perm": h_result.get("d_perm"),
        "mean_obs_null": h_result["mean_wasserstein_obs_null"],
        "mean_null_null": h_result["mean_wasserstein_null_null"],
    }


def _landscape_l2_distance(L1: np.ndarray, L2: np.ndarray, dx: float) -> float:
    """Discrete L² distance between two landscape arrays of shape (k_max, n_points)."""
    return float(np.sqrt(np.sum((L1 - L2) ** 2) * dx))


def _landscape_on_grid(
    ph_result: Any,
    dim: int,
    t_values: np.ndarray,
    k_max: int = DEFAULT_K_MAX,
) -> np.ndarray:
    """Persistence landscape evaluated on a fixed grid.

    Args:
        ph_result: PHResult with dgms dict.
        dim: Homology dimension.
        t_values: 1-D array of filtration parameter values (the grid).
        k_max: Number of landscape functions.

    Returns:
        Array of shape (k_max, n_points).
    """
    n_pts = len(t_values)
    dgm = ph_result.dgms.get(dim, np.empty((0, 2)))
    dgm = np.array(dgm) if len(dgm) > 0 else np.empty((0, 2))

    # Filter out infinite bars
    finite_mask = np.isfinite(dgm).all(axis=1) if dgm.shape[0] > 0 else np.array([], dtype=bool)
    dgm = dgm[finite_mask] if dgm.shape[0] > 0 else dgm

    if dgm.shape[0] == 0:
        return np.zeros((k_max, n_pts))

    # Tent functions: shape (n_pairs, n_points)
    births = dgm[:, 0][:, None]
    deaths = dgm[:, 1][:, None]
    t = t_values[None, :]
    tent = np.minimum(t - births, deaths - t)
    tent = np.maximum(tent, 0.0)

    n_pairs = tent.shape[0]
    if n_pairs == 0:
        return np.zeros((k_max, n_pts))

    # k-th landscape = k-th largest tent value at each filtration parameter
    sorted_desc = np.sort(tent, axis=0)[::-1]
    landscapes = np.zeros((k_max, n_pts))
    landscapes[: min(n_pairs, k_max)] = sorted_desc[: min(n_pairs, k_max)]
    return landscapes


def _run_landscape_permutation_test(
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    embed_kwargs: dict,
    max_dim: int,
    n_landmarks: int,
    n_permutations: int,
    k_max: int,
    n_points: int,
    seed: int,
    null_type: str = "markov",
    markov_order: int = 1,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Run landscape L² permutation test alongside W₂.

    Uses the same null draws as would be used for W₂ — generates null embeddings,
    computes PH, evaluates landscapes on the observed filtration grid.

    Returns:
        Dict with H0/H1 landscape L² p-values, T_ratio, d_perm.
    """
    from joblib import Parallel, delayed

    from trajectory_tda.topology.permutation_nulls import (
        _single_permutation,
        maxmin_landmarks,
    )
    from poverty_tda.topology.multidim_ph import PHResult, compute_rips_ph
    from trajectory_tda.topology.vectorisation import compute_w2_ratio_bca_ci

    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_landmarks = embeddings

    ph_obs = compute_rips_ph(obs_landmarks, max_dim=max_dim)

    # Build observed landscape grids per dimension
    t_grids: dict[int, np.ndarray] = {}
    obs_landscapes: dict[int, np.ndarray] = {}
    for dim in range(max_dim + 1):
        dgm = ph_obs.dgms.get(dim, np.empty((0, 2)))
        dgm = np.array(dgm) if len(dgm) > 0 else np.empty((0, 2))
        finite = dgm[np.isfinite(dgm).all(axis=1)] if dgm.shape[0] > 0 else dgm
        if finite.shape[0] > 0:
            t_min, t_max = float(finite[:, 0].min()), float(finite[:, 1].max())
        else:
            t_min, t_max = 0.0, 1.0
        t_grids[dim] = np.linspace(t_min, t_max, n_points)
        obs_landscapes[dim] = _landscape_on_grid(ph_obs, dim, t_grids[dim], k_max)

    # Run null permutations (wasserstein mode stores null diagrams)
    seeds_list = [seed + i + 1 for i in range(n_permutations)]
    null_results = Parallel(n_jobs=4, verbose=10)(
        delayed(_single_permutation)(
            null_type,
            embeddings,
            trajectories,
            metadata,
            s,
            max_dim,
            actual_lm,
            "wasserstein",
            markov_order,
            embed_kwargs,
            ph_observed=ph_obs,
        )
        for s in seeds_list
    )

    results: dict[str, Any] = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        t_vals = t_grids[dim]
        obs_land = obs_landscapes[dim]
        n_pts = len(t_vals)
        dx = (t_vals[-1] - t_vals[0]) / n_pts if n_pts > 1 else 1.0

        # Compute obs-null landscape L² distances
        obs_null_l2: list[float] = []
        null_lands: list[np.ndarray] = []
        for r in null_results:
            dgm_j = r.get(f"{key}_dgm", [])
            d_j = np.array(dgm_j) if len(dgm_j) > 0 else np.empty((0, 2))
            ph_j = PHResult(dgms={dim: d_j})
            land_j = _landscape_on_grid(ph_j, dim, t_vals, k_max)
            null_lands.append(land_j)
            obs_null_l2.append(_landscape_l2_distance(obs_land, land_j, dx))

        obs_null_arr = np.array(obs_null_l2)
        mean_obs_null = float(obs_null_arr.mean())

        # Null-null landscape L² distances
        n_null_pairs = min(500, n_permutations * (n_permutations - 1) // 2)
        rng_pairs = np.random.RandomState(seed)
        null_null_l2: list[float] = []
        for _ in range(n_null_pairs):
            i, j = rng_pairs.choice(n_permutations, size=2, replace=False)
            null_null_l2.append(_landscape_l2_distance(null_lands[i], null_lands[j], dx))

        null_null_arr = np.array(null_null_l2) if null_null_l2 else np.array([0.0])
        mean_null_null = float(null_null_arr.mean())

        t_ratio = mean_obs_null / mean_null_null if mean_null_null > 0 else float("nan")

        bca_ci_lower: float | None = None
        bca_ci_upper: float | None = None
        if len(obs_null_arr) >= 2 and len(null_null_arr) >= 2:
            try:
                _, bca_ci_lower, bca_ci_upper = compute_w2_ratio_bca_ci(obs_null_arr, null_null_arr, seed=seed)
            except Exception as exc:
                logger.warning("Landscape BCa CI failed for %s: %s", key, exc)

        _r_upper = int(np.sum(null_null_arr >= mean_obs_null))
        _n_null = len(null_null_arr)
        p_value = (_r_upper + 1) / (_n_null + 1)

        _std_null_null = float(null_null_arr.std()) if len(null_null_l2) > 1 else float("nan")
        d_perm = (mean_obs_null - mean_null_null) / _std_null_null if _std_null_null > 0 else float("nan")

        results[key] = {
            "landscape_l2_pvalue": p_value,
            "t_ratio": t_ratio,
            "bca_ci_lower": bca_ci_lower,
            "bca_ci_upper": bca_ci_upper,
            "d_perm": d_perm,
            "mean_obs_null": mean_obs_null,
            "mean_null_null": mean_null_null,
            "k_max": k_max,
            "n_points": n_points,
            "n_null_null_pairs": len(null_null_l2),
        }
        logger.info(
            "  Landscape L² %s: mean_D(obs,null)=%.4f, mean_D(null,null)=%.4f, T_ratio=%.4f, p=%.4f",
            key,
            mean_obs_null,
            mean_null_null,
            t_ratio,
            p_value,
        )

    return results


def _null_null_w2_worker(d_i: np.ndarray, d_j: np.ndarray, dim: int) -> float:
    """Worker for parallel null-null W₂ computation.

    Pickled into joblib workers; must be at module level. Reconstructs PHResult
    objects from raw (birth, death) arrays and returns the Wasserstein-2 distance
    between them at the given homology dimension.
    """
    from poverty_tda.topology.multidim_ph import PHResult
    from trajectory_tda.topology.vectorisation import wasserstein_distance

    ph_i = PHResult(dgms={dim: d_i})
    ph_j = PHResult(dgms={dim: d_j})
    return float(wasserstein_distance(ph_i, ph_j, dim=dim))


def _aggregate_combined(
    null_results: list[dict],
    ph_obs: Any,
    n_permutations: int,
    max_dim: int,
    k_max: int,
    n_points: int,
    seed: int,
    phase_label: str = "",
) -> dict[str, Any]:
    """Aggregate W₂ and landscape L² from a shared set of null permutation results.

    Args:
        null_results: Output list from Parallel(_single_permutation calls).
        ph_obs: Observed PHResult.
        n_permutations: Number of permutations (= len(null_results)).
        max_dim: Maximum homology dimension.
        k_max: Landscape functions per dim.
        n_points: Grid points for landscape evaluation.
        seed: Random seed for null-null pair sampling.

    Returns:
        Dict with h0/h1 keys containing all required output fields.
    """
    from joblib import Parallel, delayed

    from poverty_tda.topology.multidim_ph import PHResult
    from trajectory_tda.topology.vectorisation import compute_w2_ratio_bca_ci

    rng_pairs = np.random.RandomState(seed)
    n_null_pairs = min(500, n_permutations * (n_permutations - 1) // 2)

    t_agg_total = time.time()
    tag = f"[{phase_label} AGG]" if phase_label else "[AGG]"
    logger.info(
        "%s starting: B=%d, n_null_pairs=%d, max_dim=%d, k_max=%d, n_points=%d",
        tag,
        n_permutations,
        n_null_pairs,
        max_dim,
        k_max,
        n_points,
    )

    output: dict[str, Any] = {}
    for dim in range(max_dim + 1):
        key = f"H{dim}"
        cell_key = f"h{dim}"
        t_dim = time.time()
        logger.info("%s   dim=%d (%s) starting", tag, dim, cell_key)

        # W₂ obs-null distances (already computed by _single_permutation)
        obs_null_w2 = np.array([r[key] for r in null_results])
        mean_obs_null_w2 = float(obs_null_w2.mean())

        # Build landscape grids from observed PH
        dgm_obs = ph_obs.dgms.get(dim, np.empty((0, 2)))
        dgm_obs = np.array(dgm_obs) if len(dgm_obs) > 0 else np.empty((0, 2))
        finite_obs = dgm_obs[np.isfinite(dgm_obs).all(axis=1)] if dgm_obs.shape[0] > 0 else dgm_obs
        if finite_obs.shape[0] > 0:
            t_min = float(finite_obs[:, 0].min())
            t_max = float(finite_obs[:, 1].max())
        else:
            t_min, t_max = 0.0, 1.0
        t_vals = np.linspace(t_min, t_max, n_points)
        dx = (t_vals[-1] - t_vals[0]) / n_points if n_points > 1 else 1.0
        obs_land = _landscape_on_grid(ph_obs, dim, t_vals, k_max)

        # Null PH diagrams → landscape arrays (and obs-null L²)
        t_obs_null_land = time.time()
        null_lands: list[np.ndarray] = []
        obs_null_l2: list[float] = []
        null_dgms: list[np.ndarray] = []
        for r in null_results:
            dgm_j = r.get(f"{key}_dgm", [])
            d_j = np.array(dgm_j) if len(dgm_j) > 0 else np.empty((0, 2))
            null_dgms.append(d_j)
            ph_j = PHResult(dgms={dim: d_j})
            land_j = _landscape_on_grid(ph_j, dim, t_vals, k_max)
            null_lands.append(land_j)
            obs_null_l2.append(_landscape_l2_distance(obs_land, land_j, dx))
        obs_null_land = np.array(obs_null_l2)
        mean_obs_null_land = float(obs_null_land.mean())
        logger.info(
            "%s   dim=%d obs-null landscapes built (n=%d) in %.1fs",
            tag,
            dim,
            n_permutations,
            time.time() - t_obs_null_land,
        )

        # Pre-sample pairs deterministically (preserves seeded reproducibility)
        rng_pairs.seed(seed)
        pair_indices = [
            tuple(int(x) for x in rng_pairs.choice(n_permutations, size=2, replace=False)) for _ in range(n_null_pairs)
        ]

        # Null-null W₂ — parallel (was the serial bottleneck; now n_jobs=-1).
        # Per-worker memory is small (~50–100 MB) since we only pass two small diagrams
        # per task; no condensed distance matrices allocated here.
        t_w2 = time.time()
        logger.info(
            "%s   dim=%d null-null W₂ Parallel(n_jobs=-1) n_pairs=%d...",
            tag,
            dim,
            n_null_pairs,
        )
        null_null_w2 = list(
            Parallel(n_jobs=-1, verbose=10)(
                delayed(_null_null_w2_worker)(null_dgms[i], null_dgms[j], dim) for (i, j) in pair_indices
            )
        )
        logger.info(
            "%s   dim=%d null-null W₂ done in %.1fs (mean=%.4f)",
            tag,
            dim,
            time.time() - t_w2,
            float(np.mean(null_null_w2)) if null_null_w2 else 0.0,
        )

        # Null-null landscape L² — serial (cheap, not worth parallelising)
        t_l2 = time.time()
        null_null_l2_list = [_landscape_l2_distance(null_lands[i], null_lands[j], dx) for (i, j) in pair_indices]
        logger.info(
            "%s   dim=%d null-null L² done in %.1fs",
            tag,
            dim,
            time.time() - t_l2,
        )

        null_null_w2_arr = np.array(null_null_w2) if null_null_w2 else np.array([0.0])
        null_null_l2_arr = np.array(null_null_l2_list) if null_null_l2_list else np.array([0.0])
        mean_null_null_w2 = float(null_null_w2_arr.mean())
        mean_null_null_land = float(null_null_l2_arr.mean())

        # W₂ statistics
        t_ratio_w2 = mean_obs_null_w2 / mean_null_null_w2 if mean_null_null_w2 > 0 else float("nan")
        bca_ci_lower: float | None = None
        bca_ci_upper: float | None = None
        if len(obs_null_w2) >= 2 and len(null_null_w2_arr) >= 2:
            try:
                _, bca_ci_lower, bca_ci_upper = compute_w2_ratio_bca_ci(obs_null_w2, null_null_w2_arr, seed=seed)
            except Exception as exc:
                logger.warning("BCa CI failed for W₂ %s: %s", key, exc)

        _r_w2 = int(np.sum(null_null_w2_arr >= mean_obs_null_w2))
        _n_w2 = len(null_null_w2_arr)
        w2_pvalue = (_r_w2 + 1) / (_n_w2 + 1)
        _r_lower = int(np.sum(null_null_w2_arr <= mean_obs_null_w2))
        lower_tail_pvalue = (_r_lower + 1) / (_n_w2 + 1)
        _std_w2 = float(null_null_w2_arr.std()) if len(null_null_w2) > 1 else float("nan")
        d_perm_w2 = (mean_obs_null_w2 - mean_null_null_w2) / _std_w2 if _std_w2 > 0 else float("nan")

        # Landscape L² statistics
        t_ratio_land = mean_obs_null_land / mean_null_null_land if mean_null_null_land > 0 else float("nan")
        bca_ci_lower_land: float | None = None
        bca_ci_upper_land: float | None = None
        if len(obs_null_land) >= 2 and len(null_null_l2_arr) >= 2:
            try:
                _, bca_ci_lower_land, bca_ci_upper_land = compute_w2_ratio_bca_ci(
                    obs_null_land, null_null_l2_arr, seed=seed
                )
            except Exception as exc:
                logger.warning("BCa CI failed for landscape L² %s: %s", key, exc)

        _r_land = int(np.sum(null_null_l2_arr >= mean_obs_null_land))
        _n_land = len(null_null_l2_arr)
        land_pvalue = (_r_land + 1) / (_n_land + 1)
        _std_land = float(null_null_l2_arr.std()) if len(null_null_l2_list) > 1 else float("nan")
        d_perm_land = (mean_obs_null_land - mean_null_null_land) / _std_land if _std_land > 0 else float("nan")

        logger.info(
            "  %s: W₂ p=%.4f T=%.4f d=%.4f | land L² p=%.4f T=%.4f d=%.4f",
            key,
            w2_pvalue,
            t_ratio_w2,
            d_perm_w2,
            land_pvalue,
            t_ratio_land,
            d_perm_land,
        )
        logger.info("%s   dim=%d done in %.1fs", tag, dim, time.time() - t_dim)

        cell: dict[str, Any] = {
            "w2_pvalue": w2_pvalue,
            "landscape_l2_pvalue": land_pvalue,
            "t_ratio": t_ratio_w2,
            "bca_ci_lower": bca_ci_lower,
            "bca_ci_upper": bca_ci_upper,
            "d_perm": d_perm_w2,
            "mean_obs_null": mean_obs_null_w2,
            "mean_null_null": mean_null_null_w2,
            "landscape_t_ratio": t_ratio_land,
            "landscape_bca_ci_lower": bca_ci_lower_land,
            "landscape_bca_ci_upper": bca_ci_upper_land,
            "landscape_d_perm": d_perm_land,
        }
        if dim == 0:
            cell["lower_tail_pvalue"] = lower_tail_pvalue
        output[cell_key] = cell

    logger.info("%s aggregation total elapsed: %.1fs", tag, time.time() - t_agg_total)
    return output


def _run_dataset(
    checkpoint_dir: Path,
    n_permutations: int,
    n_landmarks: int,
    k_max: int,
    n_points: int,
    seed: int,
    label: str,
    n_jobs: int = 4,
) -> dict[str, Any]:
    """Run W₂ + landscape L² battery for one dataset with shared null permutations.

    Returns:
        Dict with h0/h1 keys each containing merged W₂ + landscape fields.
    """
    from joblib import Parallel, delayed

    from poverty_tda.topology.multidim_ph import compute_rips_ph
    from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint
    from trajectory_tda.topology.permutation_nulls import (
        _single_permutation,
        maxmin_landmarks,
    )

    t_phase = time.time()
    _write_status(f"PHASE {label} START", f"L={n_landmarks} B={n_permutations} n_jobs={n_jobs}")
    logger.info("=" * 70)
    logger.info("[PHASE %s] start (L=%d, B=%d, n_jobs=%d)", label, n_landmarks, n_permutations, n_jobs)
    logger.info("=" * 70)

    t_load = time.time()
    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    logger.info(
        "[PHASE %s] checkpoint loaded in %.1fs: %d trajectories, %dD embeddings",
        label,
        time.time() - t_load,
        embeddings.shape[0],
        embeddings.shape[1],
    )

    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    t_lm = time.time()
    if actual_lm < n:
        _, obs_landmarks = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_landmarks = embeddings
    ph_obs = compute_rips_ph(obs_landmarks, max_dim=1)
    logger.info(
        "[PHASE %s] obs landmarks + PH built in %.1fs (L=%d)",
        label,
        time.time() - t_lm,
        actual_lm,
    )

    _write_status(f"PHASE {label} PERMUTATIONS", f"B={n_permutations} n_jobs={n_jobs}")
    logger.info(
        "[PHASE %s] running %d Markov-1 permutations (n_jobs=%d) — W₂ + landscape L² from shared draws...",
        label,
        n_permutations,
        n_jobs,
    )
    t0 = time.time()
    seeds_list = [seed + i + 1 for i in range(n_permutations)]
    null_results = Parallel(n_jobs=n_jobs, verbose=10)(
        delayed(_single_permutation)(
            "markov",
            embeddings,
            trajectories,
            None,
            s,
            1,
            actual_lm,
            "wasserstein",
            DEFAULT_MARKOV_ORDER,
            embed_kwargs,
            ph_observed=ph_obs,
        )
        for s in seeds_list
    )
    logger.info("[PHASE %s] %d permutations done in %.1fs", label, n_permutations, time.time() - t0)
    _write_status(f"PHASE {label} AGGREGATION", f"permutations done in {time.time() - t0:.0f}s")

    out = _aggregate_combined(null_results, ph_obs, n_permutations, 1, k_max, n_points, seed, phase_label=label)
    logger.info("[PHASE %s] TOTAL elapsed %.1fs", label, time.time() - t_phase)
    logger.info("=" * 70)
    _write_status(f"PHASE {label} DONE", f"total {time.time() - t_phase:.0f}s")
    return out


def _run_landmark_sensitivity(
    checkpoint_dir: Path,
    landmark_values: list[int],
    n_permutations: int,
    seed: int,
    label: str,
) -> dict[str, Any]:
    """Cross-landmark sensitivity sweep (supplement) using shared null draws."""
    from joblib import Parallel, delayed

    from poverty_tda.topology.multidim_ph import compute_rips_ph
    from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint
    from trajectory_tda.topology.permutation_nulls import (
        _single_permutation,
        maxmin_landmarks,
    )

    t_sweep = time.time()
    _write_status(f"SWEEP {label} START", f"L={landmark_values} B={n_permutations}")
    logger.info("=" * 70)
    logger.info(
        "[SWEEP %s] start — %d landmark values: %s (B=%d each)",
        label,
        len(landmark_values),
        landmark_values,
        n_permutations,
    )
    logger.info("=" * 70)
    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    out: dict[str, Any] = {}
    seeds_list = [seed + i + 1 for i in range(n_permutations)]
    for idx, L in enumerate(landmark_values, start=1):
        sub_label = f"{label}_L{L}"
        _write_status(
            f"SWEEP {label} {idx}/{len(landmark_values)} L={L}",
            f"sub-phase START B={n_permutations}",
        )
        logger.info(
            "[SWEEP %s %d/%d L=%d] starting (B=%d)",
            label,
            idx,
            len(landmark_values),
            L,
            n_permutations,
        )
        t0 = time.time()
        n = embeddings.shape[0]
        actual_lm = min(L, n)
        if actual_lm < n:
            _, obs_lm = maxmin_landmarks(embeddings, actual_lm, seed=seed)
        else:
            obs_lm = embeddings
        ph_obs = compute_rips_ph(obs_lm, max_dim=1)
        t_perm = time.time()
        null_res = Parallel(n_jobs=4, verbose=10)(
            delayed(_single_permutation)(
                "markov",
                embeddings,
                trajectories,
                None,
                s,
                1,
                actual_lm,
                "wasserstein",
                DEFAULT_MARKOV_ORDER,
                embed_kwargs,
                ph_observed=ph_obs,
            )
            for s in seeds_list
        )
        logger.info(
            "[SWEEP %s %d/%d L=%d] %d permutations done in %.1fs",
            label,
            idx,
            len(landmark_values),
            L,
            n_permutations,
            time.time() - t_perm,
        )
        combined = _aggregate_combined(
            null_res,
            ph_obs,
            n_permutations,
            1,
            DEFAULT_K_MAX,
            DEFAULT_N_POINTS,
            seed,
            phase_label=sub_label,
        )
        out[f"L{L}"] = {
            "h0": {
                "w2_pvalue": combined["h0"]["w2_pvalue"],
                "landscape_l2_pvalue": combined["h0"]["landscape_l2_pvalue"],
            },
            "h1": {
                "w2_pvalue": combined["h1"]["w2_pvalue"],
                "landscape_l2_pvalue": combined["h1"]["landscape_l2_pvalue"],
            },
        }
        logger.info(
            "[SWEEP %s %d/%d L=%d] sub-phase TOTAL %.1fs",
            label,
            idx,
            len(landmark_values),
            L,
            time.time() - t0,
        )
    logger.info("[SWEEP %s] TOTAL elapsed %.1fs", label, time.time() - t_sweep)
    logger.info("=" * 70)
    _write_status(f"SWEEP {label} DONE", f"total {time.time() - t_sweep:.0f}s")
    return out


def _run_landscape_sensitivity(
    checkpoint_dir: Path,
    n_landmarks: int,
    n_permutations: int,
    seed: int,
    label: str,
    k_max_values: list[int],
    n_points_values: list[int],
) -> dict[str, Any]:
    """Landscape sensitivity sweep (supplement)."""
    from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint

    t_sweep = time.time()
    total_runs = len(k_max_values) * len(n_points_values)
    _write_status(
        f"SWEEP {label} START",
        f"{total_runs} combinations k_max={k_max_values} n_points={n_points_values} B={n_permutations}",
    )
    logger.info("=" * 70)
    logger.info(
        "[SWEEP %s] start — %d combinations (k_max=%s × n_points=%s, B=%d each)",
        label,
        total_runs,
        k_max_values,
        n_points_values,
        n_permutations,
    )
    logger.info("=" * 70)
    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    out: dict[str, Any] = {}
    idx = 0
    for k_max in k_max_values:
        for n_pts in n_points_values:
            idx += 1
            run_key = f"k{k_max}_np{n_pts}"
            _write_status(
                f"SWEEP {label} {idx}/{total_runs} {run_key}",
                f"sub-phase START k_max={k_max} n_points={n_pts}",
            )
            logger.info(
                "[SWEEP %s %d/%d %s] starting (k_max=%d, n_points=%d, B=%d)",
                label,
                idx,
                total_runs,
                run_key,
                k_max,
                n_pts,
                n_permutations,
            )
            t0 = time.time()
            land_r = _run_landscape_permutation_test(
                embeddings=embeddings,
                trajectories=trajectories,
                embed_kwargs=embed_kwargs,
                max_dim=1,
                n_landmarks=n_landmarks,
                n_permutations=n_permutations,
                k_max=k_max,
                n_points=n_pts,
                seed=seed,
            )
            out[run_key] = {
                "k_max": k_max,
                "n_points": n_pts,
                "h0_landscape_l2_pvalue": land_r["H0"]["landscape_l2_pvalue"],
                "h1_landscape_l2_pvalue": land_r["H1"]["landscape_l2_pvalue"],
            }
            logger.info(
                "[SWEEP %s %d/%d %s] sub-phase TOTAL %.1fs",
                label,
                idx,
                total_runs,
                run_key,
                time.time() - t0,
            )
    logger.info("[SWEEP %s] TOTAL elapsed %.1fs", label, time.time() - t_sweep)
    logger.info("=" * 70)
    _write_status(f"SWEEP {label} DONE", f"total {time.time() - t_sweep:.0f}s")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 matched-L W2 + landscape L2 battery")
    parser.add_argument("--usoc-dir", type=str, default="results/trajectory_tda_integration")
    parser.add_argument("--bhps-dir", type=str, default="results/trajectory_tda_bhps")
    parser.add_argument("--output", type=str, default=None, help="Override output path")
    parser.add_argument("--n-perms", type=int, default=DEFAULT_B, help="Headline permutations (default 1000)")
    parser.add_argument("--n-perms-sens", type=int, default=100, help="Sensitivity permutations (default 100)")
    parser.add_argument("--landmarks", type=int, default=DEFAULT_L)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--k-max", type=int, default=DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=DEFAULT_N_POINTS)
    parser.add_argument(
        "--n-jobs", type=int, default=4, help="Parallel workers for permutations (default 4; use -1 for all cores)"
    )
    parser.add_argument("--skip-sensitivity", action="store_true", help="Skip supplement sensitivity sweeps (faster)")
    parser.add_argument("--skip-bhps", action="store_true", help="Skip BHPS run (USoc only)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    today = date.today().isoformat()
    out_path = (
        Path(args.output)
        if args.output
        else Path(f"results/trajectory_tda_integration/stage1/matched_w2_battery_{today}.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Phase manifest — used for [X/N] progress markers
    phases = ["USoc HEADLINE"]
    if not args.skip_bhps:
        phases.append("BHPS HEADLINE")
    if not args.skip_sensitivity:
        phases.append("LANDMARK SENSITIVITY (3 sub-phases)")
        phases.append("LANDSCAPE SENSITIVITY (9 sub-phases)")
    total_phases = len(phases)

    t_master = time.time()
    _write_status(
        "BATTERY START",
        f"L={args.landmarks} B={args.n_perms} seed={args.seed} phases={phases}",
    )
    logger.info("=" * 70)
    logger.info("Stage 1 battery: L=%d, B=%d, seed=%d, Markov-1", args.landmarks, args.n_perms, args.seed)
    logger.info("Output: %s", out_path)
    logger.info("Phases (%d): %s", total_phases, " | ".join(phases))
    if _PHASE_STATUS_FILE:
        logger.info("Phase status file: %s", _PHASE_STATUS_FILE)
    logger.info("=" * 70)

    run_params = {
        "L": args.landmarks,
        "B": args.n_perms,
        "null_model": f"markov-{DEFAULT_MARKOV_ORDER}",
        "seed": args.seed,
        "landscape_k_max": args.k_max,
        "landscape_n_points": args.n_points,
        "pvalue_formula": "(r+1)/(B+1)",
    }

    # Headline USoc run
    logger.info("[%d/%d] USoc HEADLINE starting", 1, total_phases)
    usoc_results = _run_dataset(
        checkpoint_dir=Path(args.usoc_dir),
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
        k_max=args.k_max,
        n_points=args.n_points,
        seed=args.seed,
        label="USoc",
        n_jobs=args.n_jobs,
    )
    logger.info("[%d/%d] USoc HEADLINE done | master elapsed %.1fs", 1, total_phases, time.time() - t_master)

    # Headline BHPS run
    bhps_results: dict[str, Any] = {}
    if not args.skip_bhps:
        logger.info("[%d/%d] BHPS HEADLINE starting", 2, total_phases)
        bhps_results = _run_dataset(
            checkpoint_dir=Path(args.bhps_dir),
            n_permutations=args.n_perms,
            n_landmarks=args.landmarks,
            k_max=args.k_max,
            n_points=args.n_points,
            seed=args.seed,
            label="BHPS",
            n_jobs=args.n_jobs,
        )
        logger.info("[%d/%d] BHPS HEADLINE done | master elapsed %.1fs", 2, total_phases, time.time() - t_master)

    # Cross-landmark sensitivity (supplement, B=100)
    sensitivity_landmark: dict[str, Any] = {}
    if not args.skip_sensitivity:
        logger.info(
            "[%d/%d] LANDMARK SENSITIVITY starting (L={2500,5000,8000}, B=%d)",
            3,
            total_phases,
            args.n_perms_sens,
        )
        sensitivity_landmark = _run_landmark_sensitivity(
            checkpoint_dir=Path(args.usoc_dir),
            landmark_values=[2500, 5000, 8000],
            n_permutations=args.n_perms_sens,
            seed=args.seed,
            label="USoc_lm_sens",
        )
        logger.info(
            "[%d/%d] LANDMARK SENSITIVITY done | master elapsed %.1fs",
            3,
            total_phases,
            time.time() - t_master,
        )

    # Landscape sensitivity (supplement, B=100)
    sensitivity_landscape: dict[str, Any] = {}
    if not args.skip_sensitivity:
        logger.info(
            "[%d/%d] LANDSCAPE SENSITIVITY starting (k_max × n_points sweep, B=%d)",
            4,
            total_phases,
            args.n_perms_sens,
        )
        sensitivity_landscape = _run_landscape_sensitivity(
            checkpoint_dir=Path(args.usoc_dir),
            n_landmarks=args.landmarks,
            n_permutations=args.n_perms_sens,
            seed=args.seed,
            label="USoc_land_sens",
            k_max_values=[3, 5, 10],
            n_points_values=[100, 200, 500],
        )
        logger.info(
            "[%d/%d] LANDSCAPE SENSITIVITY done | master elapsed %.1fs",
            4,
            total_phases,
            time.time() - t_master,
        )

    result = {
        "run_params": run_params,
        "usoc": usoc_results,
        "bhps": bhps_results,
        "sensitivity_landmark": sensitivity_landmark,
        "sensitivity_landscape": sensitivity_landscape,
    }

    # Convert numpy types and save
    from trajectory_tda.scripts.run_wasserstein_battery import _convert_numpy

    with open(out_path, "w") as f:
        json.dump(_convert_numpy(result), f, indent=2)
    logger.info("Saved: %s", out_path)

    # Print headline summary
    logger.info("")
    logger.info("HEADLINE RESULTS")
    logger.info("=" * 60)
    for dataset, res in [("USoc", usoc_results), ("BHPS", bhps_results)]:
        if not res:
            continue
        for dim_key in ["h0", "h1"]:
            cell = res.get(dim_key, {})
            logger.info(
                "%s %s: W2 p=%.4f, land_L2 p=%.4f, T_ratio=%.4f, d_perm=%.4f",
                dataset,
                dim_key.upper(),
                cell.get("w2_pvalue", float("nan")),
                cell.get("landscape_l2_pvalue", float("nan")),
                cell.get("t_ratio") or float("nan"),
                cell.get("d_perm") or float("nan"),
            )

    logger.info("=" * 70)
    logger.info("Stage 1 battery COMPLETE | total wall time %.1fs", time.time() - t_master)
    logger.info("=" * 70)
    _write_status("BATTERY DONE", f"total {time.time() - t_master:.0f}s output={out_path}")


if __name__ == "__main__":
    main()
