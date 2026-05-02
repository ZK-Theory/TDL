# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Persistence landscape L² null battery (ISSUE M2).
#   Companion to run_wasserstein_battery.py. Computes L² distances between
#   persistence landscapes of the observed diagram and each null draw, using
#   the same null models as the W₂ battery. Satisfies the CONVENTIONS mandate
#   that landscape L² is always reported alongside Wasserstein-2.
#
# Design notes:
#   - All landscapes are evaluated on the OBSERVED diagram's filtration grid
#     (t_min/t_max from observed features, n_points=200). This ensures null and
#     observed landscapes live in the same function space.
#   - k_max=5 landscape functions per dimension (Bubenik 2015 default).
#   - p-value computation mirrors the W₂ battery: mean obs-null L² is compared
#     against the empirical CDF of null-null L² distances (500 random pairs).
#   - Results JSON format mirrors run_wasserstein_battery.py output.

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
from joblib import Parallel, delayed

from trajectory_tda.scripts.run_wasserstein_battery import (
    _convert_numpy,
    load_checkpoint,
    load_cohort_metadata,
    load_regime_labels,
)
from trajectory_tda.topology.permutation_nulls import (
    _cohort_shuffle,
    _label_shuffle,
    _markov_shuffle,
    _order_shuffle,
    _stratified_markov_shuffle,
    maxmin_landmarks,
)
from poverty_tda.topology.multidim_ph import PHResult, compute_rips_ph

logger = logging.getLogger(__name__)

K_MAX: int = 5
N_POINTS: int = 200


# ---------------------------------------------------------------------------
# Landscape computation helpers
# ---------------------------------------------------------------------------


def _landscape_on_grid(
    ph: PHResult,
    dim: int,
    t_values: np.ndarray,
    k_max: int = K_MAX,
) -> np.ndarray:
    """Persistence landscape evaluated on a fixed grid.

    Returns array of shape (k_max, n_points).  When the diagram has fewer
    than k_max features the remaining rows are zero.  Uses vectorised tent
    computation (avoids a Python loop over features).
    """
    features = ph.h_features(dim, min_persistence=0.0)
    n_pts = len(t_values)
    if len(features) == 0:
        return np.zeros((k_max, n_pts))

    arr = np.array(features)
    births, deaths = arr[:, 0], arr[:, 1]
    finite = np.isfinite(deaths)
    births, deaths = births[finite], deaths[finite]
    if len(births) == 0:
        return np.zeros((k_max, n_pts))

    # Tent functions: shape (n_pairs, n_points)
    tents = np.maximum(
        0.0,
        np.minimum(
            t_values[np.newaxis, :] - births[:, np.newaxis],
            deaths[:, np.newaxis] - t_values[np.newaxis, :],
        ),
    )

    # k-th landscape = k-th largest tent value at each filtration parameter
    n_pairs = tents.shape[0]
    sorted_desc = np.sort(tents, axis=0)[::-1]
    landscapes = np.zeros((k_max, n_pts))
    landscapes[: min(n_pairs, k_max)] = sorted_desc[: min(n_pairs, k_max)]
    return landscapes


def _l2_distance(lscape1: np.ndarray, lscape2: np.ndarray, delta_t: float) -> float:
    """Discrete L² distance between two landscape arrays.

    Both arrays have shape (k_max, n_points).  The integral is approximated
    by the rectangle rule with step delta_t.
    """
    return float(np.sqrt(np.sum((lscape1 - lscape2) ** 2) * delta_t))


def _obs_t_grids(
    ph: PHResult,
    max_dim: int,
    n_points: int = N_POINTS,
) -> dict[int, np.ndarray]:
    """Build per-dimension filtration grids from the observed PH diagram."""
    grids: dict[int, np.ndarray] = {}
    for dim in range(max_dim + 1):
        features = ph.h_features(dim, min_persistence=0.0)
        if len(features) == 0:
            grids[dim] = np.linspace(0.0, 1.0, n_points)
            continue
        arr = np.array(features)
        finite = np.isfinite(arr[:, 1])
        if not finite.any():
            grids[dim] = np.linspace(0.0, 1.0, n_points)
            continue
        t_min = float(arr[finite, 0].min())
        t_max = float(arr[finite, 1].max())
        grids[dim] = np.linspace(t_min, t_max, n_points)
    return grids


# ---------------------------------------------------------------------------
# Single permutation
# ---------------------------------------------------------------------------


def _null_embedding(
    null_type: str,
    embeddings: np.ndarray,
    trajectories: list[list[str]] | None,
    metadata: dict | None,
    rng: np.random.RandomState,
    markov_order: int,
    embed_kwargs: dict,
) -> np.ndarray:
    if null_type == "label_shuffle":
        return _label_shuffle(embeddings, rng, embed_kwargs=embed_kwargs)
    if null_type == "cohort_shuffle":
        return _cohort_shuffle(embeddings, metadata, rng)
    if null_type == "order_shuffle":
        return _order_shuffle(trajectories, rng, embed_kwargs=embed_kwargs)
    if null_type == "markov":
        return _markov_shuffle(trajectories, rng, markov_order=markov_order, embed_kwargs=embed_kwargs)
    if null_type == "stratified_markov1":
        regime_labels = (metadata or {}).get("regime_labels")
        return _stratified_markov_shuffle(trajectories, regime_labels, rng, embed_kwargs=embed_kwargs)
    raise ValueError(f"Unknown null_type: {null_type}")


def _single_landscape_perm(
    null_type: str,
    embeddings: np.ndarray,
    trajectories: list[list[str]] | None,
    metadata: dict | None,
    seed: int,
    n_landmarks: int,
    obs_t_grids: dict[int, np.ndarray],
    markov_order: int,
    embed_kwargs: dict,
) -> dict[str, np.ndarray]:
    """One permutation: null embedding → PH → landscape on observed grid.

    Returns dict mapping 'H{dim}' → landscape array (k_max, n_points).
    """
    rng = np.random.RandomState(seed)
    X_null = _null_embedding(
        null_type, embeddings, trajectories, metadata, rng, markov_order, embed_kwargs
    )
    n = X_null.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, lm = maxmin_landmarks(X_null, actual_lm, seed=seed)
    else:
        lm = X_null
    max_dim = max(obs_t_grids.keys())
    ph = compute_rips_ph(lm, max_dim=max_dim)
    return {
        f"H{dim}": _landscape_on_grid(ph, dim, t_values)
        for dim, t_values in obs_t_grids.items()
    }


# ---------------------------------------------------------------------------
# Main battery function
# ---------------------------------------------------------------------------


def run_landscape_battery(
    checkpoint_dir: Path,
    null_types: list[str],
    n_permutations: int = 100,
    n_landmarks: int = 5000,
    max_dim: int = 1,
    markov_order: int = 1,
    n_jobs: int = 1,
    seed: int = 42,
    output_name: str = "04_nulls_landscape_L2.json",
    overwrite_output: bool = False,
    regime_labels_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run persistence landscape L² null battery on a pipeline checkpoint.

    Args:
        checkpoint_dir: Path to results checkpoint.
        null_types: Null types to run (same set as run_wasserstein_battery).
        n_permutations: Obs-null permutations per null.
        n_landmarks: Landmark count for VR filtration.
        max_dim: Maximum homology dimension (landscapes computed for H0..H{max_dim}).
        markov_order: Markov chain order for 'markov' null.
        n_jobs: Joblib parallelism (1 = serial).
        seed: RNG seed for observed landmarks + permutation sequence.
        output_name: Output path, relative to checkpoint_dir unless absolute.
        overwrite_output: Rerun all keys even if output already exists.
        regime_labels_path: Path to 05_analysis.json (required for stratified_markov1).

    Returns:
        Results dict keyed by null type.
    """
    embeddings, trajectories, embed_kwargs = load_checkpoint(checkpoint_dir)
    metadata = load_cohort_metadata(checkpoint_dir)

    _regime_labels: np.ndarray | None = None
    if "stratified_markov1" in null_types:
        if regime_labels_path is None:
            raise ValueError(
                "null_type='stratified_markov1' requires --regime-labels-path. "
                "USoc: results/trajectory_tda_integration/05_analysis.json. "
                "BHPS: results/trajectory_tda_bhps/05_analysis.json."
            )
        _regime_labels = load_regime_labels(Path(regime_labels_path))

    out_path = Path(output_name)
    if not out_path.is_absolute():
        out_path = checkpoint_dir / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if out_path.exists() and not overwrite_output:
        with open(out_path) as f:
            existing = json.load(f)
        logger.info("Loaded existing results: %s", list(existing.keys()))
    elif out_path.exists() and overwrite_output:
        out_path.unlink()

    # Compute observed PH and grids once (shared across all null types)
    n = embeddings.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, obs_lm = maxmin_landmarks(embeddings, actual_lm, seed=seed)
    else:
        obs_lm = embeddings
    ph_obs = compute_rips_ph(obs_lm, max_dim=max_dim)
    t_grids = _obs_t_grids(ph_obs, max_dim)

    # Pre-compute observed landscapes
    obs_landscapes: dict[str, np.ndarray] = {}
    for dim, t_vals in t_grids.items():
        obs_landscapes[f"H{dim}"] = _landscape_on_grid(ph_obs, dim, t_vals)
        logger.info(
            "Observed H%d landscape: grid [%.4f, %.4f], k_max=%d",
            dim,
            t_vals[0],
            t_vals[-1],
            K_MAX,
        )

    for null_type in null_types:
        if null_type == "markov":
            result_key = f"markov{markov_order}"
            current_markov_order = markov_order
        else:
            result_key = null_type
            current_markov_order = 1

        if result_key in existing:
            logger.info("Skipping %s — already in results", result_key)
            continue

        logger.info("=" * 60)
        logger.info("Landscape L² null: %s", null_type)
        logger.info("=" * 60)
        t0 = time.time()

        call_metadata: dict[str, Any] | None = metadata
        if null_type == "stratified_markov1" and _regime_labels is not None:
            call_metadata = dict(metadata) if metadata else {}
            call_metadata["regime_labels"] = _regime_labels

        seeds = [seed + i + 1 for i in range(n_permutations)]

        null_landscapes_per_perm: list[dict[str, np.ndarray]] = Parallel(
            n_jobs=n_jobs, verbose=0
        )(
            delayed(_single_landscape_perm)(
                null_type,
                embeddings,
                trajectories,
                call_metadata,
                s,
                actual_lm,
                t_grids,
                current_markov_order,
                embed_kwargs,
            )
            for s in seeds
        )

        # Aggregate per dimension
        null_result: dict[str, Any] = {}
        for dim, t_vals in t_grids.items():
            key = f"H{dim}"
            delta_t = float(t_vals[1] - t_vals[0]) if len(t_vals) > 1 else 1.0
            obs_lscape = obs_landscapes[key]

            obs_null_dists = np.array(
                [_l2_distance(obs_lscape, p[key], delta_t) for p in null_landscapes_per_perm]
            )

            # Null-null L² distances (500 random pairs)
            n_null_pairs = min(500, n_permutations * (n_permutations - 1) // 2)
            rng_pairs = np.random.RandomState(seed)
            null_null_dists = []
            for _ in range(n_null_pairs):
                i, j = rng_pairs.choice(n_permutations, size=2, replace=False)
                null_null_dists.append(
                    _l2_distance(
                        null_landscapes_per_perm[i][key],
                        null_landscapes_per_perm[j][key],
                        delta_t,
                    )
                )

            null_null_arr = np.array(null_null_dists) if null_null_dists else np.array([0.0])
            mean_obs_null = float(obs_null_dists.mean())
            p_value = float(np.mean(null_null_arr >= mean_obs_null))

            null_result[key] = {
                "mean_l2_obs_null": mean_obs_null,
                "std_l2_obs_null": float(obs_null_dists.std()),
                "median_l2_obs_null": float(np.median(obs_null_dists)),
                "mean_l2_null_null": float(null_null_arr.mean()),
                "std_l2_null_null": float(null_null_arr.std()),
                "p_value": p_value,
                "significant_at_005": p_value < 0.05,
                "obs_null_distribution": obs_null_dists.tolist(),
                "n_null_null_pairs": len(null_null_dists),
            }
            logger.info(
                "  %s: L²(obs,null)=%.4f, L²(null,null)=%.4f, p=%.4f",
                key,
                mean_obs_null,
                float(null_null_arr.mean()),
                p_value,
            )

        null_result["null_type"] = null_type
        null_result["n_permutations"] = n_permutations
        null_result["k_max"] = K_MAX
        null_result["n_points"] = N_POINTS
        null_result["statistic"] = "landscape_l2"
        null_result["elapsed_seconds"] = time.time() - t0
        existing[result_key] = null_result

        with open(out_path, "w") as f:
            json.dump(_convert_numpy(existing), f, indent=2)
        logger.info("  Saved incremental results to %s", out_path)

    return existing


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Persistence landscape L² null battery on pipeline checkpoint (ISSUE M2)"
    )
    parser.add_argument("--checkpoint-dir", type=str, required=True)
    parser.add_argument(
        "--null-types",
        nargs="+",
        default=["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"],
    )
    parser.add_argument("--n-perms", type=int, default=100)
    parser.add_argument("--landmarks", type=int, default=5000)
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument("--markov-order", type=int, default=1)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-name",
        type=str,
        default="04_nulls_landscape_L2.json",
    )
    parser.add_argument("--overwrite-output", action="store_true")
    parser.add_argument(
        "--regime-labels-path",
        type=str,
        default=None,
        help=(
            "Path to 05_analysis.json with 'gmm_labels'. "
            "Required when --null-types includes stratified_markov1."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    run_landscape_battery(
        checkpoint_dir=Path(args.checkpoint_dir),
        null_types=args.null_types,
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
        max_dim=args.max_dim,
        markov_order=args.markov_order,
        n_jobs=args.n_jobs,
        seed=args.seed,
        output_name=args.output_name,
        overwrite_output=args.overwrite_output,
        regime_labels_path=args.regime_labels_path,
    )


if __name__ == "__main__":
    main()
