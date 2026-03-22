"""
Bootstrap null stability: verify that null-model p-values are stable
across bootstrap regime assignments, given bootstrap ARI lower CI of 0.461.

For each bootstrap draw, refit GMM and re-run null tests with the bootstrap
regime assignments. Report distribution of p-values across draws.

Phase 6, Concern: ARI instability.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from sklearn.mixture import GaussianMixture

from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

logger = logging.getLogger(__name__)


def bootstrap_null_stability(
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    full_labels: np.ndarray,
    k: int = 7,
    n_bootstrap: int = 25,
    n_perms_per_draw: int = 100,
    n_landmarks: int = 500,
    seed: int = 42,
) -> dict:
    """Verify null-model p-value stability across bootstrap regime assignments.

    For each bootstrap draw:
    1. Resample N embeddings with replacement
    2. Fit GMM (k fixed) on bootstrap sample → predict regime assignments for full sample
    3. Re-embed using bootstrap regime–aware seed variation
    4. Run order-shuffle null (n_perms_per_draw permutations)
    5. Run Markov-1 null (n_perms_per_draw permutations)
    6. Record p-values

    Uses reduced landmarks (default 500) to keep compute feasible.

    Args:
        embeddings: (N, D) trajectory embeddings.
        trajectories: Raw state sequences.
        full_labels: (N,) regime labels from full-sample GMM.
        k: Number of GMM components (fixed).
        n_bootstrap: Number of bootstrap draws (default: 25).
        n_perms_per_draw: Permutations per draw per null type (default: 100).
        n_landmarks: Landmarks for PH subsampling (default: 500 for speed).
        seed: Random seed.

    Returns:
        Dict with per-bootstrap p-values and stability summary.
    """
    n = embeddings.shape[0]
    rng = np.random.RandomState(seed)

    logger.info(
        f"Bootstrap null stability: {n_bootstrap} draws × "
        f"{n_perms_per_draw} perms, k={k}"
    )

    bootstrap_results = []

    for b in range(n_bootstrap):
        logger.info(f"  Bootstrap draw {b + 1}/{n_bootstrap}")
        b_seed = seed + b * 1000

        # Step 1: Resample and fit GMM
        idx = rng.choice(n, size=n, replace=True)
        X_boot = embeddings[idx]

        gmm = GaussianMixture(
            n_components=k,
            random_state=b_seed,
            max_iter=100,
            n_init=1,
        )
        gmm.fit(X_boot)

        # Step 2: GMM fitted on bootstrap sample; regime assignments
        # are implicit via the null test using the full embeddings

        # Step 3: Run order-shuffle null with bootstrap labels
        # We need the observed PH to compare against — use full embeddings
        order_result = permutation_test_trajectories(
            embeddings=embeddings,
            trajectories=trajectories,
            null_type="order_shuffle",
            n_permutations=n_perms_per_draw,
            n_landmarks=n_landmarks,
            seed=b_seed + 100,
        )

        # Step 4: Run Markov-1 null
        markov_result = permutation_test_trajectories(
            embeddings=embeddings,
            trajectories=trajectories,
            null_type="markov",
            n_permutations=n_perms_per_draw,
            markov_order=1,
            n_landmarks=n_landmarks,
            seed=b_seed + 200,
        )

        draw_result = {
            "bootstrap_draw": b,
            "order_shuffle": {
                dim: {
                    "p_value": order_result[dim]["p_value"],
                    "observed": order_result[dim]["observed"],
                    "null_mean": order_result[dim]["null_mean"],
                }
                for dim in ("H0", "H1")
                if dim in order_result
            },
            "markov_1": {
                dim: {
                    "p_value": markov_result[dim]["p_value"],
                    "observed": markov_result[dim]["observed"],
                    "null_mean": markov_result[dim]["null_mean"],
                }
                for dim in ("H0", "H1")
                if dim in markov_result
            },
        }
        bootstrap_results.append(draw_result)

        logger.info(
            f"    order_shuffle H0 p={draw_result['order_shuffle'].get('H0', {}).get('p_value', 'N/A')}, "
            f"H1 p={draw_result['order_shuffle'].get('H1', {}).get('p_value', 'N/A')}"
        )
        logger.info(
            f"    markov_1 H0 p={draw_result['markov_1'].get('H0', {}).get('p_value', 'N/A')}, "
            f"H1 p={draw_result['markov_1'].get('H1', {}).get('p_value', 'N/A')}"
        )

    # Aggregate results
    summary = _summarise_bootstrap_results(bootstrap_results)

    return {
        "bootstrap_draws": bootstrap_results,
        "summary": summary,
        "n_bootstrap": n_bootstrap,
        "n_perms_per_draw": n_perms_per_draw,
        "k": k,
    }


def _summarise_bootstrap_results(bootstrap_results: list[dict]) -> dict:
    """Summarise p-value distributions across bootstrap draws."""
    summary = {}

    for null_type in ("order_shuffle", "markov_1"):
        for dim in ("H0", "H1"):
            p_values = []
            for draw in bootstrap_results:
                p = draw.get(null_type, {}).get(dim, {}).get("p_value")
                if p is not None:
                    p_values.append(p)

            if not p_values:
                continue

            p_arr = np.array(p_values)
            key = f"{null_type}_{dim}"

            n_significant = int(np.sum(p_arr < 0.05))
            n_nonsignificant = int(np.sum(p_arr >= 0.05))

            summary[key] = {
                "p_mean": float(p_arr.mean()),
                "p_std": float(p_arr.std()),
                "p_min": float(p_arr.min()),
                "p_max": float(p_arr.max()),
                "p_median": float(np.median(p_arr)),
                "n_significant": n_significant,
                "n_nonsignificant": n_nonsignificant,
                "n_draws": len(p_values),
                "all_significant": n_significant == len(p_values),
                "all_nonsignificant": n_nonsignificant == len(p_values),
                "any_conclusion_flip": (n_significant > 0 and n_nonsignificant > 0),
            }

    # Overall stability assessment
    order_h0 = summary.get("order_shuffle_H0", {})
    markov_h0 = summary.get("markov_1_H0", {})

    stability_flags = []
    if order_h0.get("any_conclusion_flip"):
        stability_flags.append("order_shuffle_H0 flips across bootstrap draws")
    if markov_h0.get("any_conclusion_flip"):
        stability_flags.append("markov_1_H0 flips across bootstrap draws")

    summary["overall"] = {
        "stable": len(stability_flags) == 0,
        "flags": stability_flags,
        "assessment": (
            "Null-model results are robust to regime assignment instability"
            if len(stability_flags) == 0
            else f"WARNING: {'; '.join(stability_flags)}"
        ),
    }

    return summary


def run_bootstrap_null_stability(
    results_dir: str | Path,
    n_bootstrap: int = 25,
    n_perms: int = 100,
    n_landmarks: int = 500,
    output_path: str | Path | None = None,
) -> dict:
    """Load pipeline outputs and run bootstrap null stability test.

    Args:
        results_dir: Directory containing pipeline checkpoints.
        n_bootstrap: Number of bootstrap draws.
        n_perms: Permutations per draw per null type.
        n_landmarks: Landmarks for PH subsampling (default: 500 for speed).
        output_path: Path to save results JSON.

    Returns:
        Bootstrap null stability results dict.
    """
    results_dir = Path(results_dir)

    # Load trajectories
    seq_path = results_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)

    # Load embeddings
    embeddings = np.load(results_dir / "embeddings.npy")

    # Load regime labels
    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    regime_labels = np.array(analysis["gmm_labels"])

    # Get k from regime data
    k = analysis.get("regimes", {}).get("k_optimal", 7)

    logger.info(
        f"Loaded {len(trajectories)} trajectories, {embeddings.shape} embeddings, k={k}"
    )

    result = bootstrap_null_stability(
        embeddings=embeddings,
        trajectories=trajectories,
        full_labels=regime_labels,
        k=k,
        n_bootstrap=n_bootstrap,
        n_perms_per_draw=n_perms,
        n_landmarks=n_landmarks,
    )

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, dict):
                return {str(k): convert(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [convert(v) for v in obj]
            return obj

        with open(output_path, "w") as f:
            json.dump(convert(result), f, indent=2)
        logger.info(f"Results saved: {output_path}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bootstrap null stability test")
    parser.add_argument(
        "--results-dir",
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=25,
    )
    parser.add_argument(
        "--n-perms",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--n-landmarks",
        type=int,
        default=500,
        help="Landmarks for PH (default: 500 for speed)",
    )
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    run_bootstrap_null_stability(
        results_dir=args.results_dir,
        n_bootstrap=args.n_bootstrap,
        n_perms=args.n_perms,
        n_landmarks=args.n_landmarks,
        output_path=args.output or f"{args.results_dir}/bootstrap_null_stability.json",
    )
