"""
Run Wasserstein-distance permutation null tests for trajectory TDA.

Computes Wasserstein distances between observed persistence diagrams and
null-model diagrams, plus a null-null baseline for significance assessment.

Supports both synthetic data (for validation) and real BHPS/UKHLS data
(from existing pipeline checkpoints).

Usage:
    # Synthetic validation (no data dependencies)
    python -m trajectory_tda.scripts.run_wasserstein_nulls --synthetic

    # Real data from checkpoint
    python -m trajectory_tda.scripts.run_wasserstein_nulls \\
        --results-dir results/trajectory_tda_integration \\
        --data-dir trajectory_tda/data

    # Custom permutation count and null types
    python -m trajectory_tda.scripts.run_wasserstein_nulls --synthetic \\
        --n-perms 200 --null-types order_shuffle markov
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic data generation (no test-module dependencies)
# ---------------------------------------------------------------------------

_STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
_POVERTY_CYCLE = ["EL", "UL", "IL", "IM", "EM", "EL"]


def _make_cyclic_trajectories(
    n: int = 50,
    cycle: list[str] | None = None,
    noise: float = 0.1,
    t: int = 20,
    seed: int = 42,
) -> list[list[str]]:
    """Generate trajectories following a poverty-churn cycle.

    Default cycle: EL → UL → IL → IM → EM → EL.
    With probability *noise* a random state is substituted instead.
    """
    rng = np.random.RandomState(seed)
    if cycle is None:
        cycle = _POVERTY_CYCLE
    cycle_len = len(cycle)
    trajectories = []
    for _ in range(n):
        traj = []
        start = rng.randint(cycle_len)
        for step in range(t):
            if rng.random() < noise:
                traj.append(_STATES[rng.randint(len(_STATES))])
            else:
                traj.append(cycle[(start + step) % cycle_len])
        trajectories.append(traj)
    return trajectories


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _save_results(data: dict, path: Path, name: str) -> None:
    """Save results to JSON with numpy conversion."""
    path.mkdir(parents=True, exist_ok=True)
    fpath = path / f"{name}.json"

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    with open(fpath, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Results saved: {fpath}")


def _make_synthetic_data(
    n: int = 100,
    t: int = 15,
    seed: int = 42,
) -> tuple[np.ndarray, list[list[str]], dict]:
    """Generate synthetic trajectory data for validation."""
    from trajectory_tda.embedding.ngram_embed import ngram_embed

    trajs = _make_cyclic_trajectories(n=n, t=t, seed=seed)
    embed_kwargs = {"pca_dim": 5}
    emb, _ = ngram_embed(trajs, **embed_kwargs)
    return emb, trajs, embed_kwargs


def _load_checkpoint_data(
    data_dir: Path,
) -> tuple[np.ndarray, list[list[str]], dict]:
    """Load embeddings and trajectories from existing pipeline checkpoint."""
    from trajectory_tda.embedding.ngram_embed import ngram_embed

    # Load raw trajectories
    traj_path = data_dir / "bhps_trajectories.json"
    if not traj_path.exists():
        raise FileNotFoundError(f"Trajectory file not found: {traj_path}")

    with open(traj_path) as f:
        traj_data = json.load(f)

    trajectories = [item["trajectory"] for item in traj_data]

    # Load or recompute embeddings
    embed_kwargs = {"pca_dim": 5}
    emb, _ = ngram_embed(trajectories, **embed_kwargs)

    return emb, trajectories, embed_kwargs


def run_wasserstein_nulls(
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    embed_kwargs: dict,
    null_types: list[str],
    n_permutations: int = 200,
    max_dim: int = 1,
    n_landmarks: int = 2500,
    n_jobs: int = -1,
    seed: int = 42,
) -> dict:
    """Run Wasserstein permutation tests for all specified null types."""
    all_results = {}

    for null_type in null_types:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Wasserstein null test: {null_type}")
        logger.info(f"{'=' * 60}")
        t0 = time.time()

        try:
            result = permutation_test_trajectories(
                embeddings=embeddings,
                trajectories=trajectories,
                null_type=null_type,
                n_permutations=n_permutations,
                max_dim=max_dim,
                n_landmarks=n_landmarks,
                statistic="wasserstein",
                n_jobs=n_jobs,
                seed=seed,
                embed_kwargs=embed_kwargs,
            )
            elapsed = time.time() - t0
            result["elapsed_seconds"] = elapsed
            all_results[null_type] = result
            logger.info(f"  Completed in {elapsed:.1f}s")

            # Summary
            for dim in range(max_dim + 1):
                key = f"H{dim}"
                if key in result:
                    r = result[key]
                    logger.info(
                        f"  {key}: mean_W(obs,null)={r['mean_wasserstein_obs_null']:.4f}, "
                        f"mean_W(null,null)={r['mean_wasserstein_null_null']:.4f}, "
                        f"p={r['p_value']:.4f}"
                    )

        except Exception as e:
            logger.error(f"  Failed: {e}")
            all_results[null_type] = {"error": str(e)}

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Run Wasserstein permutation null tests")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data for validation")
    parser.add_argument("--results-dir", type=str, default="results/trajectory_tda_integration")
    parser.add_argument("--data-dir", type=str, default="trajectory_tda/data")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory (default: results-dir)")
    parser.add_argument("--n-perms", type=int, default=200)
    parser.add_argument("--landmarks", type=int, default=2500)
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--null-types",
        nargs="+",
        default=["order_shuffle", "markov"],
        help="Null types to test (default: order_shuffle markov)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    # Load data
    if args.synthetic:
        logger.info("Using synthetic cyclic trajectories for validation")
        emb, trajs, embed_kwargs = _make_synthetic_data()
    else:
        logger.info(f"Loading data from {args.data_dir}")
        emb, trajs, embed_kwargs = _load_checkpoint_data(
            Path(args.data_dir),
        )

    logger.info(f"Embeddings shape: {emb.shape}, {len(trajs)} trajectories")

    # Run tests
    all_results = run_wasserstein_nulls(
        embeddings=emb,
        trajectories=trajs,
        embed_kwargs=embed_kwargs,
        null_types=args.null_types,
        n_permutations=args.n_perms,
        max_dim=args.max_dim,
        n_landmarks=args.landmarks,
        n_jobs=args.n_jobs,
        seed=args.seed,
    )

    # Save results
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.results_dir)
    _save_results(all_results, output_dir, "wasserstein_null_tests")

    logger.info(f"\nAll Wasserstein null tests complete. Results saved to {output_dir}")


if __name__ == "__main__":
    main()
