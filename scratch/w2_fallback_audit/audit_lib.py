# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6)
# Purpose: Self-contained audit library for the systemic greedy-fallback W2 audit.
#   Loads null-diagram caches, replicates the exact battery obs-null / null-null
#   aggregation (both the greedy fallback convention and exact optimal-transport),
#   computes the diagonal-bound impossibility screen, and re-derives corrected
#   exact-W2 headline statistics. Pure numpy + gudhi (POT/EMD) — no trajectory_tda
#   import, so it runs on any venv with gudhi+POT. Reference implementation:
#   scratch/vintage_audit/_auditlib.py on branch run/headline-vintage-materiality.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

PROJ_ROOT = Path("C:/Users/steph/TDL")
STAGE1_DIR = PROJ_ROOT / "results/trajectory_tda_integration/stage1"
CACHE_DIR = STAGE1_DIR / "cache"

# Battery pair-sampling defaults (trajectory_tda/scripts/stage1/_battery_core.py).
DEFAULT_N_NULL_PAIRS = 500  # effect-statistic cap; p-value uses all B pairs.


def sha256_file(path: Path) -> str:
    """Return the sha256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_pairs(dgm: Any) -> NDArray[np.float64]:
    """Reshape to (n, 2) and drop non-finite (birth, death) pairs."""
    arr = np.asarray(dgm, dtype=np.float64).reshape(-1, 2)
    if arr.shape[0] == 0:
        return arr
    return arr[np.isfinite(arr).all(axis=1)]


def load_cache(cache_path: Path) -> dict[str, Any]:
    """Load a null-diagram cache .npz (obs + B null diagrams per dim + metadata).

    Security:
        ``allow_pickle=True`` is required because the battery stores its metadata
        dict as a pickled object array. Unpickling executes arbitrary code, so
        ``cache_path`` must only ever reference a trusted pipeline-generated cache
        under ``CACHE_DIR`` — never an untrusted or externally-supplied .npz.
    """
    with np.load(cache_path, allow_pickle=True) as data:
        h0_arr = data["h0_diagrams"]
        h1_arr = data["h1_diagrams"]
        obs_h0 = np.array(data["obs_h0_diagram"], dtype=np.float64)
        obs_h1 = np.array(data["obs_h1_diagram"], dtype=np.float64)
        metadata = data["metadata"].item() if "metadata" in data else {}
        h0_list = [finite_pairs(x) for x in h0_arr]
        h1_list = [finite_pairs(x) for x in h1_arr]
    return {
        "h0_diagrams": h0_list,
        "h1_diagrams": h1_list,
        "obs_h0_diagram": finite_pairs(obs_h0),
        "obs_h1_diagram": finite_pairs(obs_h1),
        "metadata": metadata,
    }


def exact_w2(dgm_a: Any, dgm_b: Any, p: int = 2) -> float:
    """Exact Wasserstein-p via gudhi's POT/EMD solver (order=p, internal_p=2)."""
    from gudhi.wasserstein import wasserstein_distance

    return float(wasserstein_distance(finite_pairs(dgm_a), finite_pairs(dgm_b), order=p, internal_p=2))


def greedy_w2(dgm_a: Any, dgm_b: Any, p: int = 2) -> float:
    """Faithful replica of the greedy persistence-rank fallback that ran when POT
    was absent (original trajectory_tda.topology.vectorisation.wasserstein_distance,
    lines 236-254). NOT optimal transport; used only for the convention gate."""
    f1 = finite_pairs(dgm_a)
    f2 = finite_pairs(dgm_b)
    if len(f1) == 0 and len(f2) == 0:
        return 0.0
    if len(f1) == 0:
        pers2 = f2[:, 1] - f2[:, 0]
        return float(np.sum((pers2 / 2) ** p) ** (1 / p))
    if len(f2) == 0:
        pers1 = f1[:, 1] - f1[:, 0]
        return float(np.sum((pers1 / 2) ** p) ** (1 / p))

    pers1 = f1[:, 1] - f1[:, 0]
    pers2 = f2[:, 1] - f2[:, 0]
    idx1 = np.argsort(-pers1)
    idx2 = np.argsort(-pers2)

    total_cost = 0.0
    n_matched = min(len(idx1), len(idx2))
    for i in range(n_matched):
        diff = np.abs(f1[idx1[i]] - f2[idx2[i]])
        total_cost += np.sum(diff**p)
    for i in range(n_matched, len(idx1)):
        total_cost += (pers1[idx1[i]] / 2) ** p * 2
    for i in range(n_matched, len(idx2)):
        total_cost += (pers2[idx2[i]] / 2) ** p * 2
    return float(total_cost ** (1 / p))


def diagonal_norm_sq(dgm: Any) -> float:
    """Sum of squared L2 distances of each point to the diagonal.

    Under internal_p=2 the distance of (b, d) to the diagonal is (d-b)/sqrt(2),
    so this returns sum_i ((d_i - b_i)/sqrt(2))**2 = 0.5 * sum_i pers_i**2.
    """
    f = finite_pairs(dgm)
    if len(f) == 0:
        return 0.0
    pers = f[:, 1] - f[:, 0]
    return float(0.5 * np.sum(pers**2))


def diagonal_bound(dgm_a: Any, dgm_b: Any) -> float:
    """Max possible exact W2(a, b): project every point of both diagrams to the
    diagonal. sqrt(diag_norm_sq(a) + diag_norm_sq(b)). An exact W2 CANNOT exceed
    this; a stored value above it is mathematically impossible as exact W2."""
    return float(np.sqrt(diagonal_norm_sq(dgm_a) + diagonal_norm_sq(dgm_b)))


def reproduce_pair_indices(n_permutations: int, n_pair_draws: int, seed: int) -> list[tuple[int, int]]:
    """Replicate _battery_core.aggregate_combined null-null pair sampling exactly.

    rng.seed(seed); then n_pair_draws draws of choice(n_permutations, size=2,
    replace=False). Returns the ordered pair list; the effect statistic uses the
    first DEFAULT_N_NULL_PAIRS, the p-value uses all n_pair_draws.
    """
    rng = np.random.RandomState(seed)
    return [tuple(int(x) for x in rng.choice(n_permutations, size=2, replace=False)) for _ in range(n_pair_draws)]


def obs_null_distances(
    obs_dgm: NDArray[np.float64],
    null_dgms: list[NDArray[np.float64]],
    solver: str,
) -> NDArray[np.float64]:
    """W2(obs, null_i) for every null draw. solver in {'greedy', 'exact'}."""
    fn = greedy_w2 if solver == "greedy" else exact_w2
    return np.array([fn(obs_dgm, nd) for nd in null_dgms], dtype=np.float64)


def null_null_distances(
    null_dgms: list[NDArray[np.float64]],
    pair_indices: list[tuple[int, int]],
    solver: str,
) -> NDArray[np.float64]:
    """W2(null_i, null_j) over the sampled pairs. solver in {'greedy', 'exact'}."""
    fn = greedy_w2 if solver == "greedy" else exact_w2
    return np.array([fn(null_dgms[i], null_dgms[j]) for (i, j) in pair_indices], dtype=np.float64)


def headline_stats_from_distances(
    obs_null: NDArray[np.float64],
    null_null_all: NDArray[np.float64],
    n_effect_pairs: int = DEFAULT_N_NULL_PAIRS,
) -> dict[str, float]:
    """Derive the committed headline statistics from obs-null and null-null arrays.

    Mirrors _battery_core.aggregate_combined: mean_null_null / std over the first
    n_effect_pairs; the p-value uses the full null_null_all array.
    """
    mean_obs = float(obs_null.mean())
    nn_effect = null_null_all[:n_effect_pairs]
    mean_nn = float(nn_effect.mean())
    std_nn = float(nn_effect.std()) if len(nn_effect) > 1 else float("nan")
    d_perm = (mean_obs - mean_nn) / std_nn if std_nn and std_nn > 0 else float("nan")
    t_ratio = mean_obs / mean_nn if mean_nn > 0 else float("nan")
    n_pv = len(null_null_all)
    r_upper = int(np.sum(null_null_all >= mean_obs))
    r_lower = int(np.sum(null_null_all <= mean_obs))
    w2_pvalue = (r_upper + 1) / (n_pv + 1)
    lower_tail_pvalue = (r_lower + 1) / (n_pv + 1)
    return {
        "mean_obs_null": mean_obs,
        "mean_null_null": mean_nn,
        "std_null_null": std_nn,
        "d_perm": d_perm,
        "t_ratio": t_ratio,
        "w2_pvalue": w2_pvalue,
        "lower_tail_pvalue": lower_tail_pvalue,
        "n_effect_pairs": len(nn_effect),
        "n_pvalue_pairs": n_pv,
    }


def convert_numpy(obj: Any) -> Any:
    """Convert numpy types to JSON-serialisable Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_numpy(x) for x in obj]
    return obj


def load_result_json(path: Path) -> dict[str, Any]:
    """Load a committed headline/battery result JSON."""
    return json.loads(path.read_text(encoding="utf-8"))
