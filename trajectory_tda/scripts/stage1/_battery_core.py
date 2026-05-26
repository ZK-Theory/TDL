# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Shared core utilities for the Stage 1 matched-L W2 + landscape L2 battery,
#   phase-split package. Houses the W2 + landscape L2 aggregator (identical numerical
#   behaviour to the legacy monolith), the launch-PID marker writer, the
#   partial-JSON writer, the null-diagram cache I/O, and the two-path output roots.
"""Stage 1 battery — shared core utilities.

The phase scripts under ``trajectory_tda/scripts/stage1/`` are intentionally
thin wrappers around the helpers in this module. The numerical core
(``aggregate_combined``) is bit-for-bit equivalent to the legacy monolith
``trajectory_tda/scripts/run_stage1_battery.py`` at the same seed/parameters
— verified by ``tests/trajectory_tda/test_stage1_phase_equivalence.py``.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# --- Pre-registered defaults (locked 2026-05-13) -----------------------------

DEFAULT_L = 5000
DEFAULT_B = 1000
DEFAULT_SEED = 42
DEFAULT_K_MAX = 5
DEFAULT_N_POINTS = 200
DEFAULT_MARKOV_ORDER = 1
DEFAULT_N_NULL_PAIRS = 500

# --- Two-path output roots ---------------------------------------------------
# Strict separation per APM_RULES "Two-path rule":
#   WORKTREE — committed deliverables (phase JSONs, scripts, smoke-test outputs)
#   PROJ_ROOT — gitignored intermediates that must survive worktree removal
#   (null-diagram cache .npz, launch-PID markers, partial-JSON files)

PROJ_ROOT_DEFAULT = Path("C:/Users/steph/TDL")


def proj_root() -> Path:
    """Absolute path to the main working tree.

    Overridable via ``STAGE1_PROJ_ROOT`` env var (used by the smoke test).
    """
    override = os.environ.get("STAGE1_PROJ_ROOT")
    return Path(override) if override else PROJ_ROOT_DEFAULT


def worktree_root() -> Path:
    """Absolute path to the current worktree (where the script is invoked)."""
    return Path.cwd()


# --- Live phase-status (carried over from legacy for parity) ----------------

_PHASE_STATUS_FILE = os.environ.get("STAGE1_STATUS_FILE")


def write_status(phase: str, detail: str = "") -> None:
    """Append a phase-transition line to ``STAGE1_STATUS_FILE`` if set.

    Best-effort observability; failures are silent.
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


# --- Launch-PID marker -------------------------------------------------------


def write_launch_marker(phase_tag: str, params: dict[str, Any]) -> Path:
    """Write a launch-PID marker before any heavy work begins.

    Ground truth that the launch succeeded — a session interruption between
    ``Start-Process`` and the first compute step is detectable from the
    presence (or absence) of this file. Returns the marker path so the caller
    can log it.

    Args:
        phase_tag: Short identifier for the phase (e.g. ``"usoc_headline"``).
        params: Run parameters to record in the marker (L, B, seed, ...).
    """
    launches_dir = proj_root() / "results/trajectory_tda_integration/stage1/launches"
    launches_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    marker = launches_dir / f"launch_{phase_tag}_{stamp}.pid"
    payload = {
        "pid": os.getpid(),
        "phase_tag": phase_tag,
        "started_utc": stamp,
        "params": params,
    }
    marker.write_text(json.dumps(payload, indent=2))
    logger.info("Launch marker: %s (pid=%d)", marker, os.getpid())
    return marker


# --- Partial-JSON writer -----------------------------------------------------


def write_partial(phase_tag: str, suffix: str, payload: dict[str, Any]) -> Path:
    """Write a defensive partial JSON for forensic recovery after a halt.

    Files live under ``WORKTREE/results/trajectory_tda_integration/stage1/.partial/``
    (gitignored). The committed deliverable is the non-partial JSON written
    by the phase script on graceful completion.
    """
    partial_dir = worktree_root() / "results/trajectory_tda_integration/stage1/.partial"
    partial_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().date().isoformat()
    path = partial_dir / f"{phase_tag}_{today}_{suffix}.json"
    with open(path, "w") as f:
        json.dump(convert_numpy(payload), f, indent=2)
    logger.info("Partial JSON: %s", path)
    return path


# --- Numpy → JSON conversion -------------------------------------------------


def convert_numpy(obj: object) -> object:
    """Recursively convert numpy types for JSON serialisation.

    Mirrors ``trajectory_tda.scripts.run_wasserstein_battery._convert_numpy``
    so phase JSONs are interchangeable with the legacy schema.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_numpy(v) for v in obj]
    return obj


# --- Landscape primitives ----------------------------------------------------


def landscape_on_grid(
    dgm: NDArray[np.float64],
    t_values: NDArray[np.float64],
    k_max: int = DEFAULT_K_MAX,
) -> NDArray[np.float64]:
    """Persistence landscape evaluated on a fixed filtration grid.

    Args:
        dgm: Persistence diagram, shape ``(n_pairs, 2)`` with finite features only.
        t_values: 1-D array of filtration parameter values.
        k_max: Number of landscape functions to return.

    Returns:
        Array of shape ``(k_max, n_points)``.
    """
    n_pts = len(t_values)
    if dgm.shape[0] == 0:
        return np.zeros((k_max, n_pts))

    births = dgm[:, 0][:, None]
    deaths = dgm[:, 1][:, None]
    t = t_values[None, :]
    tent = np.minimum(t - births, deaths - t)
    tent = np.maximum(tent, 0.0)

    n_pairs = tent.shape[0]
    if n_pairs == 0:
        return np.zeros((k_max, n_pts))

    sorted_desc = np.sort(tent, axis=0)[::-1]
    landscapes = np.zeros((k_max, n_pts))
    landscapes[: min(n_pairs, k_max)] = sorted_desc[: min(n_pairs, k_max)]
    return landscapes


def landscape_l2_distance(L1: NDArray[np.float64], L2: NDArray[np.float64], dx: float) -> float:
    """Discrete L² distance between two landscape arrays (shape ``(k_max, n_points)``)."""
    return float(np.sqrt(np.sum((L1 - L2) ** 2) * dx))


def _null_null_w2_worker(d_i: NDArray[np.float64], d_j: NDArray[np.float64], dim: int) -> float:
    """Worker for parallel null-null W2 computation.

    Module-level so joblib can pickle it. Reconstructs ``PHResult`` objects
    from raw ``(birth, death)`` arrays and returns the Wasserstein-2 distance
    at the given homology dimension.
    """
    from poverty_tda.topology.multidim_ph import PHResult
    from trajectory_tda.topology.vectorisation import wasserstein_distance

    ph_i = PHResult(dgms={dim: d_i})
    ph_j = PHResult(dgms={dim: d_j})
    return float(wasserstein_distance(ph_i, ph_j, dim=dim))


# --- Diagram extraction from PHResult ----------------------------------------


def _obs_finite_dgm(ph_obs: Any, dim: int) -> NDArray[np.float64]:
    """Extract the observed PH diagram at ``dim``, filtering infinite bars."""
    dgm = ph_obs.dgms.get(dim, np.empty((0, 2)))
    dgm_arr: NDArray[np.float64] = np.array(dgm, dtype=np.float64) if len(dgm) > 0 else np.empty((0, 2))
    if dgm_arr.shape[0] > 0:
        dgm_arr = dgm_arr[np.isfinite(dgm_arr).all(axis=1)]
    return dgm_arr


# --- The numerical core (W2 + landscape L2 aggregation) ---------------------


def aggregate_combined(
    null_results: list[dict],
    ph_obs: Any,
    n_permutations: int,
    max_dim: int,
    k_max: int,
    n_points: int,
    seed: int,
    n_null_pairs_cap: int = DEFAULT_N_NULL_PAIRS,
    phase_label: str = "",
) -> dict[str, Any]:
    """Aggregate W2 + landscape L2 from a shared set of null permutation results.

    Bit-for-bit equivalent to ``run_stage1_battery._aggregate_combined`` at
    the same inputs — same seed propagation, same pair-sampling, same
    p-value formula. The smoke test pins this equivalence to 1e-10.

    Args:
        null_results: Output list from ``Parallel(_single_permutation(...))``
            calls in ``"wasserstein"`` mode with ``ph_observed`` provided.
        ph_obs: Observed PHResult.
        n_permutations: Number of permutations (= ``len(null_results)``).
        max_dim: Maximum homology dimension.
        k_max: Landscape functions per dim.
        n_points: Grid points for landscape evaluation.
        seed: Random seed for null-null pair sampling.
        n_null_pairs_cap: Cap on number of null-null pairs to sample.
        phase_label: Label used in log messages.

    Returns:
        Dict keyed ``h0``/``h1``/... with W2 + landscape fields per dimension.
    """
    from joblib import Parallel, delayed

    from trajectory_tda.topology.vectorisation import compute_w2_ratio_bca_ci

    rng_pairs = np.random.RandomState(seed)
    n_null_pairs = min(n_null_pairs_cap, n_permutations * (n_permutations - 1) // 2)

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

        obs_null_w2 = np.array([r[key] for r in null_results])
        mean_obs_null_w2 = float(obs_null_w2.mean())

        finite_obs = _obs_finite_dgm(ph_obs, dim)
        if finite_obs.shape[0] > 0:
            t_min = float(finite_obs[:, 0].min())
            t_max = float(finite_obs[:, 1].max())
        else:
            t_min, t_max = 0.0, 1.0
        t_vals = np.linspace(t_min, t_max, n_points)
        dx = (t_vals[-1] - t_vals[0]) / n_points if n_points > 1 else 1.0
        obs_land = landscape_on_grid(_obs_finite_dgm_for_landscape(ph_obs, dim), t_vals, k_max)

        null_lands: list[NDArray[np.float64]] = []
        obs_null_l2: list[float] = []
        null_dgms: list[NDArray[np.float64]] = []
        for r in null_results:
            dgm_j = r.get(f"{key}_dgm", [])
            d_j: NDArray[np.float64] = np.array(dgm_j, dtype=np.float64) if len(dgm_j) > 0 else np.empty((0, 2))
            null_dgms.append(d_j)
            land_j = landscape_on_grid(d_j, t_vals, k_max)
            null_lands.append(land_j)
            obs_null_l2.append(landscape_l2_distance(obs_land, land_j, dx))
        obs_null_land = np.array(obs_null_l2)
        mean_obs_null_land = float(obs_null_land.mean())

        # Pair sampling — re-seed deterministically per dim (matches legacy)
        rng_pairs.seed(seed)
        pair_indices = [
            tuple(int(x) for x in rng_pairs.choice(n_permutations, size=2, replace=False)) for _ in range(n_null_pairs)
        ]

        # Null-null W2 — parallel n_jobs=-1 (parallelism note, see vault)
        t_w2 = time.time()
        logger.info("%s   dim=%d null-null W2 n_pairs=%d...", tag, dim, n_null_pairs)
        null_null_w2 = list(
            Parallel(n_jobs=-1, verbose=10)(
                delayed(_null_null_w2_worker)(null_dgms[i], null_dgms[j], dim) for (i, j) in pair_indices
            )
        )
        logger.info("%s   dim=%d null-null W2 done in %.1fs", tag, dim, time.time() - t_w2)

        null_null_l2_list = [landscape_l2_distance(null_lands[i], null_lands[j], dx) for (i, j) in pair_indices]

        null_null_w2_arr = np.array(null_null_w2) if null_null_w2 else np.array([0.0])
        null_null_l2_arr = np.array(null_null_l2_list) if null_null_l2_list else np.array([0.0])
        mean_null_null_w2 = float(null_null_w2_arr.mean())
        mean_null_null_land = float(null_null_l2_arr.mean())

        t_ratio_w2 = mean_obs_null_w2 / mean_null_null_w2 if mean_null_null_w2 > 0 else float("nan")
        bca_ci_lower: float | None = None
        bca_ci_upper: float | None = None
        if len(obs_null_w2) >= 2 and len(null_null_w2_arr) >= 2:
            try:
                _, bca_ci_lower, bca_ci_upper = compute_w2_ratio_bca_ci(obs_null_w2, null_null_w2_arr, seed=seed)
            except Exception as exc:
                logger.warning("BCa CI failed for W2 %s: %s", key, exc)

        _r_w2 = int(np.sum(null_null_w2_arr >= mean_obs_null_w2))
        _n_w2 = len(null_null_w2_arr)
        w2_pvalue = (_r_w2 + 1) / (_n_w2 + 1)
        _r_lower = int(np.sum(null_null_w2_arr <= mean_obs_null_w2))
        lower_tail_pvalue = (_r_lower + 1) / (_n_w2 + 1)
        _std_w2 = float(null_null_w2_arr.std()) if len(null_null_w2) > 1 else float("nan")
        d_perm_w2 = (mean_obs_null_w2 - mean_null_null_w2) / _std_w2 if _std_w2 > 0 else float("nan")

        t_ratio_land = mean_obs_null_land / mean_null_null_land if mean_null_null_land > 0 else float("nan")
        bca_ci_lower_land: float | None = None
        bca_ci_upper_land: float | None = None
        if len(obs_null_land) >= 2 and len(null_null_l2_arr) >= 2:
            try:
                _, bca_ci_lower_land, bca_ci_upper_land = compute_w2_ratio_bca_ci(
                    obs_null_land, null_null_l2_arr, seed=seed
                )
            except Exception as exc:
                logger.warning("BCa CI failed for landscape L2 %s: %s", key, exc)

        _r_land = int(np.sum(null_null_l2_arr >= mean_obs_null_land))
        _n_land = len(null_null_l2_arr)
        land_pvalue = (_r_land + 1) / (_n_land + 1)
        _std_land = float(null_null_l2_arr.std()) if len(null_null_l2_list) > 1 else float("nan")
        d_perm_land = (mean_obs_null_land - mean_null_null_land) / _std_land if _std_land > 0 else float("nan")

        logger.info(
            "  %s: W2 p=%.4f T=%.4f d=%.4f | land L2 p=%.4f T=%.4f d=%.4f",
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


def _obs_finite_dgm_for_landscape(ph_obs: Any, dim: int) -> NDArray[np.float64]:
    """Diagram for landscape evaluation — same finite-filter as the legacy path."""
    return _obs_finite_dgm(ph_obs, dim)


# --- Run a single headline dataset (USoc or BHPS) ----------------------------


def run_headline_from_embeddings(
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
    n_jobs: int = 4,
    n_null_pairs_cap: int = DEFAULT_N_NULL_PAIRS,
    markov_order: int = DEFAULT_MARKOV_ORDER,
    frozen_models: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict], Any]:
    """Headline W2 + landscape L2 battery from pre-loaded embeddings/trajectories.

    Behaviourally identical to ``run_headline`` from the maxmin-landmarks step
    onward; the only difference is that the caller supplies the embeddings,
    trajectories, and ``embed_kwargs`` directly instead of loading them from a
    checkpoint directory. Length-matched and other re-embedding sub-tasks call
    this helper after applying their length-control strategy and re-embedding.

    Args:
        embeddings: (n_trajectories, n_dims) embedding array.
        trajectories: List of state sequences (one per row of ``embeddings``).
        embed_kwargs: Dict matching the ``ngram_embed`` signature used to produce
            ``embeddings`` (carried through the Markov-k permutation null because
            each permuted trajectory is re-embedded with the same kwargs).
        n_permutations: Number of Markov-k null permutations (``B``).
        n_landmarks: Maxmin-landmark count (``L``).
        k_max, n_points: Persistence-landscape vectorisation parameters.
        seed: Master RNG seed; per-permutation seeds derive as ``seed + i + 1``.
        label: Short dataset label for log lines (e.g. ``"BHPS LM-truncate"``).
        phase_tag: Phase tag for status files and partial-JSON writes.
        n_jobs: Permutation parallelism (locked to 4 at L >= 2000 per OOM finding).
        n_null_pairs_cap: Cap on null-null symmetric pairs (default 500).
        markov_order: Markov order ``k`` of the permutation null (default 1).
        frozen_models: Optional fitted-model bundle forwarded into trajectory-level null embeddings.

    Returns:
        Tuple of (result dict ready for JSON dump, per-permutation null_results
        list, observed PHResult for cache writing) — same return shape as
        ``run_headline``.
    """
    from joblib import Parallel, delayed

    from poverty_tda.topology.multidim_ph import compute_rips_ph
    from trajectory_tda.topology.permutation_nulls import (
        _single_permutation,
        maxmin_landmarks,
    )

    t_phase = time.time()
    write_status(f"PHASE {label} START", f"L={n_landmarks} B={n_permutations} n_jobs={n_jobs}")
    logger.info("=" * 70)
    logger.info("[PHASE %s] start (L=%d, B=%d, n_jobs=%d)", label, n_landmarks, n_permutations, n_jobs)
    logger.info("=" * 70)

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

    write_status(f"PHASE {label} PERMUTATIONS", f"B={n_permutations} n_jobs={n_jobs}")
    logger.info(
        "[PHASE %s] running %d Markov-%d permutations (n_jobs=%d)...",
        label,
        n_permutations,
        markov_order,
        n_jobs,
    )
    t0 = time.time()
    seeds_list = [seed + i + 1 for i in range(n_permutations)]
    null_results = list(
        Parallel(n_jobs=n_jobs, verbose=10)(
            delayed(_single_permutation)(
                "markov",
                embeddings,
                trajectories,
                None,
                s,
                1,
                actual_lm,
                "wasserstein",
                markov_order,
                embed_kwargs,
                frozen_models=frozen_models,
                ph_observed=ph_obs,
            )
            for s in seeds_list
        )
    )
    logger.info("[PHASE %s] %d permutations done in %.1fs", label, n_permutations, time.time() - t0)

    write_partial(
        phase_tag,
        "after_perms",
        {
            "phase": phase_tag,
            "n_permutations": n_permutations,
            "L": actual_lm,
            "seed": seed,
            "elapsed_perms_s": time.time() - t0,
        },
    )

    write_status(f"PHASE {label} AGGREGATION", f"perms done in {time.time() - t0:.0f}s")
    out = aggregate_combined(
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

    write_partial(phase_tag, "after_agg", {"phase": phase_tag, "result": out})

    logger.info("[PHASE %s] TOTAL elapsed %.1fs", label, time.time() - t_phase)
    logger.info("=" * 70)
    write_status(f"PHASE {label} DONE", f"total {time.time() - t_phase:.0f}s")
    return out, null_results, ph_obs


def run_headline(
    checkpoint_dir: Path,
    n_permutations: int,
    n_landmarks: int,
    k_max: int,
    n_points: int,
    seed: int,
    label: str,
    phase_tag: str,
    n_jobs: int = 4,
    n_null_pairs_cap: int = DEFAULT_N_NULL_PAIRS,
    markov_order: int = DEFAULT_MARKOV_ORDER,
    frozen_loadings: bool = False,
) -> tuple[dict[str, Any], list[dict], Any]:
    """Run a headline dataset W2 + landscape L2 battery.

    Thin wrapper: loads ``embeddings``/``trajectories``/``embed_kwargs`` from
    ``checkpoint_dir`` via the canonical checkpoint loader, then delegates the
    full battery (maxmin landmarks → PH → permutations → aggregation) to
    ``run_headline_from_embeddings``.

    Returns:
        Tuple of:
          - result dict (h0/h1 cells, ready for JSON dump)
          - null_results list (per-permutation dict with H{dim} and H{dim}_dgm)
          - observed PHResult (for cache writing)
    """
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint

    t_load = time.time()
    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    logger.info(
        "[PHASE %s] checkpoint loaded in %.1fs: %d trajectories, %dD embeddings",
        label,
        time.time() - t_load,
        embeddings.shape[0],
        embeddings.shape[1],
    )
    frozen_models = None
    if frozen_loadings:
        embeddings, embedding_info = ngram_embed(trajectories, **embed_kwargs)
        frozen_models = embedding_info["fitted_models"]
        logger.info(
            "[PHASE %s] recomputed observed embedding for frozen loadings: %d trajectories, %dD",
            label,
            embeddings.shape[0],
            embeddings.shape[1],
        )
    return run_headline_from_embeddings(
        embeddings=embeddings,
        trajectories=trajectories,
        embed_kwargs=embed_kwargs,
        n_permutations=n_permutations,
        n_landmarks=n_landmarks,
        k_max=k_max,
        n_points=n_points,
        seed=seed,
        label=label,
        phase_tag=phase_tag,
        n_jobs=n_jobs,
        n_null_pairs_cap=n_null_pairs_cap,
        markov_order=markov_order,
        frozen_models=frozen_models,
    )


# --- Cache I/O (.npz) for landscape sensitivity reuse -----------------------

CACHE_DTYPE_OBJECT = np.dtype("O")


def write_null_diagram_cache(
    cache_path: Path,
    null_results: list[dict],
    ph_obs: Any,
    metadata: dict[str, Any],
) -> Path:
    """Persist null + observed diagrams to a gitignored ``.npz`` for downstream reuse.

    Schema:
        h0_diagrams: ragged ``(B,)`` object array of ``(n_i, 2)`` float64
        h1_diagrams: ragged ``(B,)`` object array of ``(m_i, 2)`` float64
        obs_h0_diagram: ``(n_obs, 2)`` float64
        obs_h1_diagram: ``(m_obs, 2)`` float64
        metadata: 0-D object array carrying a dict ``{B, L, seed, dataset, ...}``

    ``run_landscape_sensitivity.py`` is the sole consumer.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    B = len(null_results)
    h0_arr = np.empty(B, dtype=CACHE_DTYPE_OBJECT)
    h1_arr = np.empty(B, dtype=CACHE_DTYPE_OBJECT)
    for i, r in enumerate(null_results):
        h0_arr[i] = np.array(r.get("H0_dgm", []), dtype=np.float64).reshape(-1, 2)
        h1_arr[i] = np.array(r.get("H1_dgm", []), dtype=np.float64).reshape(-1, 2)

    obs_h0 = _obs_finite_dgm(ph_obs, 0)
    obs_h1 = _obs_finite_dgm(ph_obs, 1)

    np.savez_compressed(
        cache_path,
        h0_diagrams=h0_arr,
        h1_diagrams=h1_arr,
        obs_h0_diagram=obs_h0,
        obs_h1_diagram=obs_h1,
        metadata=np.array(metadata, dtype=CACHE_DTYPE_OBJECT),
    )
    logger.info("Null-diagram cache: %s (B=%d)", cache_path, B)
    return cache_path


def read_null_diagram_cache(cache_path: Path) -> dict[str, Any]:
    """Load a null-diagram cache ``.npz`` written by ``write_null_diagram_cache``.

    Returns a dict with the same keys as the cache schema, with ragged arrays
    materialised as Python lists of float64 arrays.
    """
    with np.load(cache_path, allow_pickle=True) as data:
        h0_arr = data["h0_diagrams"]
        h1_arr = data["h1_diagrams"]
        obs_h0 = np.array(data["obs_h0_diagram"], dtype=np.float64)
        obs_h1 = np.array(data["obs_h1_diagram"], dtype=np.float64)
        metadata = data["metadata"].item()
        h0_list = [np.array(x, dtype=np.float64).reshape(-1, 2) for x in h0_arr]
        h1_list = [np.array(x, dtype=np.float64).reshape(-1, 2) for x in h1_arr]
    return {
        "h0_diagrams": h0_list,
        "h1_diagrams": h1_list,
        "obs_h0_diagram": obs_h0,
        "obs_h1_diagram": obs_h1,
        "metadata": metadata,
    }


# --- Landmark sensitivity (single L per invocation) -------------------------


def run_lm_sensitivity_single_L(
    checkpoint_dir: Path,
    L: int,
    n_permutations: int,
    seed: int,
    label: str,
    phase_tag: str,
    n_jobs: int = 4,
    n_null_pairs_cap: int = DEFAULT_N_NULL_PAIRS,
    markov_order: int = DEFAULT_MARKOV_ORDER,
    k_max: int = DEFAULT_K_MAX,
    n_points: int = DEFAULT_N_POINTS,
    frozen_loadings: bool = False,
) -> dict[str, Any]:
    """Cross-landmark sensitivity at a single L (one invocation = one sub-phase).

    Returns the h0/h1 cells in the legacy ``L<L>`` schema.
    """
    from joblib import Parallel, delayed

    from poverty_tda.topology.multidim_ph import compute_rips_ph
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint
    from trajectory_tda.topology.permutation_nulls import (
        _single_permutation,
        maxmin_landmarks,
    )

    write_status(f"LM {label} L={L} START", f"B={n_permutations}")
    logger.info("[LM %s L=%d] starting (B=%d)", label, L, n_permutations)
    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    frozen_models = None
    if frozen_loadings:
        embeddings, embedding_info = ngram_embed(trajectories, **embed_kwargs)
        frozen_models = embedding_info["fitted_models"]
    n = embeddings.shape[0]
    actual_lm = min(L, n)
    if actual_lm < n:
        _, obs_lm = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_lm = embeddings
    ph_obs = compute_rips_ph(obs_lm, max_dim=1)

    seeds_list = [seed + i + 1 for i in range(n_permutations)]
    t_perm = time.time()
    null_res = list(
        Parallel(n_jobs=n_jobs, verbose=10)(
            delayed(_single_permutation)(
                "markov",
                embeddings,
                trajectories,
                None,
                s,
                1,
                actual_lm,
                "wasserstein",
                markov_order,
                embed_kwargs,
                frozen_models=frozen_models,
                ph_observed=ph_obs,
            )
            for s in seeds_list
        )
    )
    logger.info("[LM %s L=%d] %d perms in %.1fs", label, L, n_permutations, time.time() - t_perm)
    write_partial(
        phase_tag,
        f"L{L}_after_perms",
        {"phase": phase_tag, "L": L, "elapsed_s": time.time() - t_perm},
    )

    combined = aggregate_combined(
        null_res,
        ph_obs,
        n_permutations,
        max_dim=1,
        k_max=k_max,
        n_points=n_points,
        seed=seed,
        n_null_pairs_cap=n_null_pairs_cap,
        phase_label=f"{label}_L{L}",
    )
    out = {
        "h0": {
            "w2_pvalue": combined["h0"]["w2_pvalue"],
            "landscape_l2_pvalue": combined["h0"]["landscape_l2_pvalue"],
        },
        "h1": {
            "w2_pvalue": combined["h1"]["w2_pvalue"],
            "landscape_l2_pvalue": combined["h1"]["landscape_l2_pvalue"],
        },
    }
    write_status(f"LM {label} L={L} DONE", "")
    return out


# --- Landscape sensitivity (cache-driven) -----------------------------------


def sweep_landscape_from_cache(
    cache_data: dict[str, Any],
    k_max_values: list[int],
    n_points_values: list[int],
    seed: int,
    label: str,
    n_null_pairs_cap: int = DEFAULT_N_NULL_PAIRS,
) -> dict[str, Any]:
    """Sweep ``(k_max, n_points)`` against a cached set of null + obs diagrams.

    No Rips PH, no Markov simulation. Loads diagrams from the cache and
    evaluates landscapes per (k_max, n_points), producing the same
    ``h0_landscape_l2_pvalue`` / ``h1_landscape_l2_pvalue`` schema as legacy.
    """
    h0_list = cache_data["h0_diagrams"]
    h1_list = cache_data["h1_diagrams"]
    obs_h0 = cache_data["obs_h0_diagram"]
    obs_h1 = cache_data["obs_h1_diagram"]
    B = len(h0_list)
    n_null_pairs = min(n_null_pairs_cap, B * (B - 1) // 2)

    out: dict[str, Any] = {}
    rng_pairs = np.random.RandomState(seed)

    for k_max in k_max_values:
        for n_pts in n_points_values:
            run_key = f"k{k_max}_np{n_pts}"
            write_status(f"LAND-SENS {label} {run_key}", f"k_max={k_max} n_points={n_pts}")
            logger.info("[LAND-SENS %s %s] k_max=%d n_points=%d", label, run_key, k_max, n_pts)

            cell: dict[str, Any] = {"k_max": k_max, "n_points": n_pts}
            for dim, obs_dgm, null_dgms in (
                (0, obs_h0, h0_list),
                (1, obs_h1, h1_list),
            ):
                if obs_dgm.shape[0] > 0:
                    t_min = float(obs_dgm[:, 0].min())
                    t_max = float(obs_dgm[:, 1].max())
                else:
                    t_min, t_max = 0.0, 1.0
                t_vals = np.linspace(t_min, t_max, n_pts)
                dx = (t_vals[-1] - t_vals[0]) / n_pts if n_pts > 1 else 1.0

                obs_land = landscape_on_grid(obs_dgm, t_vals, k_max)
                null_lands = [landscape_on_grid(d, t_vals, k_max) for d in null_dgms]
                obs_null_l2 = np.array([landscape_l2_distance(obs_land, lnd, dx) for lnd in null_lands])

                rng_pairs.seed(seed)
                pair_indices = [
                    tuple(int(x) for x in rng_pairs.choice(B, size=2, replace=False)) for _ in range(n_null_pairs)
                ]
                null_null_l2 = np.array(
                    [landscape_l2_distance(null_lands[i], null_lands[j], dx) for (i, j) in pair_indices]
                )

                mean_obs_null = float(obs_null_l2.mean())
                _r = int(np.sum(null_null_l2 >= mean_obs_null))
                _n = len(null_null_l2)
                p_value = (_r + 1) / (_n + 1)
                cell[f"h{dim}_landscape_l2_pvalue"] = p_value

            out[run_key] = cell

    return out
