# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: T0.7 ℓ∞ ground-metric sensitivity check for W₂ null battery.
#          Compares Markov-1 H₀ rejection direction between ℓ² (canonical)
#          and ℓ∞ ground metric using gudhi.wasserstein.wasserstein_distance.
"""W₂ ground-metric sensitivity: ℓ² vs ℓ∞ comparison for Markov-1 null."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import numpy as np

from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint
from trajectory_tda.topology.permutation_nulls import (
    _markov_shuffle,
    compute_rips_ph,
    maxmin_landmarks,
)
from trajectory_tda.topology.vectorisation import PHResult

logger = logging.getLogger(__name__)

# Compute checkpoint directory from environment or project-relative path
_CHECKPOINT_DIR = Path(
    os.getenv(
        "TDA_CHECKPOINT_DIR",
        str(Path(__file__).parent.parent / "results" / "trajectory_tda_integration")
    )
)
_OUTPUT_DIR = _CHECKPOINT_DIR / "post_audit"
_OUTPUT_PATH = _OUTPUT_DIR / "w2_internal_p_sensitivity_2026-05-12.json"
_N_PERMS = 50
_N_LANDMARKS = 2000
_MAX_DIM = 1
_SEED = 42
_MARKOV_ORDER = 1


def _w2_inf(dgm1: np.ndarray, dgm2: np.ndarray) -> float:
    """W₂ distance with ℓ∞ ground metric via gudhi."""
    from gudhi.wasserstein import wasserstein_distance as _gudhi_wd

    d1 = dgm1 if len(dgm1) > 0 else np.empty((0, 2))
    d2 = dgm2 if len(dgm2) > 0 else np.empty((0, 2))
    return float(_gudhi_wd(d1, d2, order=2, internal_p=np.inf))


def _extract_dgm(ph: PHResult, dim: int) -> np.ndarray:
    feats = ph.h_features(dim)
    arr = np.array(feats) if len(feats) > 0 else np.empty((0, 2))
    if len(arr) > 0:
        arr = arr[np.isfinite(arr[:, 1])]
    return arr


def run_sensitivity() -> dict:
    """Run W₂ ground-metric sensitivity audit comparing ℓ² vs ℓ∞.

    Loads checkpoint embeddings/trajectories, computes observed persistence diagram,
    generates Markov-shuffled permutation nulls, and computes W₂ distances with ℓ∞
    ground metric. Compares obs-null and null-null distance distributions to assess
    whether the metric choice affects hypothesis-test conclusions.

    Returns:
        Dictionary containing audit parameters, ℓ² reference results, and per-dimension
        W₂(ℓ∞) statistics including mean obs-null/null-null distances, p-values, and
        significance flags.

    Raises:
        FileNotFoundError: If checkpoint files are not found.
        Exception: If checkpoint loading fails.
    """
    logger.info("Loading checkpoint …")
    try:
        embeddings, trajectories, embed_kwargs = load_checkpoint(_CHECKPOINT_DIR)
    except FileNotFoundError as e:
        logger.error(f"Checkpoint not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        raise
    n = embeddings.shape[0]
    actual_lm = min(_N_LANDMARKS, n)
    logger.info(f"n={n}, landmarks={actual_lm}, n_perms={_N_PERMS}, seed={_SEED}")

    # Observed persistence diagram
    if actual_lm < n:
        _, obs_lm = maxmin_landmarks(embeddings, actual_lm, seed=_SEED)
    else:
        obs_lm = embeddings
    ph_obs = compute_rips_ph(obs_lm, max_dim=_MAX_DIM)
    obs_dgms = {dim: _extract_dgm(ph_obs, dim) for dim in range(_MAX_DIM + 1)}

    # Per-permutation obs-null distances (ℓ∞)
    seeds = [_SEED + i + 1 for i in range(_N_PERMS)]
    null_dgms_store: list[dict[int, np.ndarray]] = []
    obs_null_dists: dict[int, list[float]] = {dim: [] for dim in range(_MAX_DIM + 1)}

    for idx, s in enumerate(seeds):
        if idx % 10 == 0:
            logger.info(f"  Permutation {idx+1}/{_N_PERMS} …")
        rng = np.random.RandomState(s)
        X_perm = _markov_shuffle(trajectories, rng, _MARKOV_ORDER, embed_kwargs)
        n_p = X_perm.shape[0]
        actual_lm_p = min(_N_LANDMARKS, n_p)
        if actual_lm_p < n_p:
            _, lm_p = maxmin_landmarks(X_perm, actual_lm_p, seed=s)
        else:
            lm_p = X_perm
        ph_perm = compute_rips_ph(lm_p, max_dim=_MAX_DIM)
        null_dgm = {dim: _extract_dgm(ph_perm, dim) for dim in range(_MAX_DIM + 1)}
        null_dgms_store.append(null_dgm)
        for dim in range(_MAX_DIM + 1):
            obs_null_dists[dim].append(_w2_inf(obs_dgms[dim], null_dgm[dim]))

    # Null-null baseline
    null_null_dists: dict[int, list[float]] = {dim: [] for dim in range(_MAX_DIM + 1)}
    
    if _N_PERMS < 2:
        logger.warning(
            f"Insufficient permutations for null-null sampling: _N_PERMS={_N_PERMS} < 2. "
            "Skipping null-null baseline computation."
        )
    else:
        n_null_pairs = min(500, _N_PERMS * (_N_PERMS - 1) // 2)
        rng_pairs = np.random.RandomState(_SEED)
        logger.info(f"Computing {n_null_pairs} null-null pairs …")
        for _ in range(n_null_pairs):
            i, j = rng_pairs.choice(_N_PERMS, size=2, replace=False)
            for dim in range(_MAX_DIM + 1):
                null_null_dists[dim].append(
                    _w2_inf(null_dgms_store[i][dim], null_dgms_store[j][dim])
                )

    results: dict = {
        "audit_parameters": {
            "internal_p": "inf",
            "order": 2,
            "n_perms": _N_PERMS,
            "n_landmarks": _N_LANDMARKS,
            "max_dim": _MAX_DIM,
            "seed": _SEED,
            "null_type": "markov",
            "markov_order": _MARKOV_ORDER,
        },
        "l2_reference": {
            "H0": {"mean_obs_null": 11.4224, "mean_null_null": 5.9919, "p_value": 0.002, "significant": True},
        },
    }
    for dim in range(_MAX_DIM + 1):
        key = f"H{dim}"
        on = np.array(obs_null_dists[dim])
        if not null_null_dists[dim]:
            logger.warning(f"{key}: No null-null distances available — result marked invalid")
            results[key] = {
                "mean_wasserstein_obs_null": float(on.mean()),
                "std_wasserstein_obs_null": float(on.std()),
                "mean_wasserstein_null_null": None,
                "p_value": None,
                "significant_at_005": None,
                "n_null_null_pairs": 0,
            }
            continue
        nn = np.array(null_null_dists[dim])
        mean_on = float(on.mean())
        mean_nn = float(nn.mean())
        p_val = float(np.mean(nn >= mean_on))
        results[key] = {
            "mean_wasserstein_obs_null": mean_on,
            "std_wasserstein_obs_null": float(on.std()),
            "mean_wasserstein_null_null": mean_nn,
            "p_value": p_val,
            "significant_at_005": p_val < 0.05,
            "n_null_null_pairs": len(null_null_dists[dim]),
        }
        logger.info(
            f"  ℓ∞ {key}: mean_W(obs,null)={mean_on:.4f}, "
            f"mean_W(null,null)={mean_nn:.4f}, p={p_val:.4f}"
        )

    return results        mean_nn = float(nn.mean())
        p_val = float(np.mean(nn >= mean_on))
        results[key] = {
            "mean_wasserstein_obs_null": mean_on,
            "std_wasserstein_obs_null": float(on.std()),
            "mean_wasserstein_null_null": mean_nn,
            "p_value": p_val,
            "significant_at_005": p_val < 0.05,
            "n_null_null_pairs": len(null_null_dists[dim]),
        }
        logger.info(
            f"  ℓ∞ {key}: mean_W(obs,null)={mean_on:.4f}, "
            f"mean_W(null,null)={mean_nn:.4f}, p={p_val:.4f}"
        )

    return results

def setup_logging() -> None:
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> None:
    setup_logging()
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = run_sensitivity()
    try:
        with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved to {_OUTPUT_PATH}")
    except IOError as e:
        logger.error(f"Failed to write results: {e}")
        raise

if __name__ == "__main__":
    main()
