# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Canary test for RNG determinism — confirms bit-identical outputs
# across two runs of the Markov-1 W_2 pipeline under a fixed master seed.
#
# Usage:
#   uv run --env-file .env python trajectory_tda/scripts/canary_rng.py run1.json
#   uv run --env-file .env python trajectory_tda/scripts/canary_rng.py run2.json
#   diff run1.json run2.json   # must be empty

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from trajectory_tda.embedding.ngram_embed import STATES, ngram_embed
from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

MASTER_SEED = 42
N_PERMS = 20
N_LANDMARKS = 500
N_TRAJECTORIES = 200
TRAJ_LENGTH = 15
MARKOV_ORDER = 1


def _generate_synthetic_trajectories(seed: int, n: int, length: int) -> list[list[str]]:
    """Generate synthetic trajectories from a seeded Markov chain.

    Uses a randomly-drawn (but seeded) transition matrix so the test
    data is not trivially uniform — it exercises real n-gram variation.
    """
    rng = np.random.default_rng(seed)
    n_states = len(STATES)
    # Draw a random row-stochastic transition matrix
    tm = rng.dirichlet(np.ones(n_states), size=n_states)
    init = np.ones(n_states) / n_states

    trajectories = []
    for _ in range(n):
        current = int(rng.choice(n_states, p=init))
        traj = [STATES[current]]
        for _ in range(length - 1):
            current = int(rng.choice(n_states, p=tm[current]))
            traj.append(STATES[current])
        trajectories.append(traj)
    return trajectories


def run_canary(output_path: Path) -> None:
    """Run the canary and write key outputs to output_path."""
    trajectories = _generate_synthetic_trajectories(seed=MASTER_SEED, n=N_TRAJECTORIES, length=TRAJ_LENGTH)

    embed_kwargs = {
        "include_bigrams": True,
        "tfidf": False,
        "pca_dim": 20,
        "random_state": MASTER_SEED,
    }
    embeddings, _ = ngram_embed(trajectories, **embed_kwargs)

    result = permutation_test_trajectories(
        embeddings=embeddings,
        trajectories=trajectories,
        null_type="markov",
        n_permutations=N_PERMS,
        n_landmarks=N_LANDMARKS,
        statistic="total_persistence",
        markov_order=MARKOV_ORDER,
        seed=MASTER_SEED,
        embed_kwargs=embed_kwargs,
        n_jobs=1,
    )

    output: dict = {}
    for dim in range(2):
        key = f"H{dim}"
        if key in result:
            r = result[key]
            output[key] = {
                "observed": r["observed"],
                "null_mean": r["null_mean"],
                "null_std": r["null_std"],
                "null_p95": r["null_p95"],
                "p_value": r["p_value"],
            }

    output["meta"] = {
        "master_seed": MASTER_SEED,
        "n_perms": N_PERMS,
        "n_landmarks": N_LANDMARKS,
        "markov_order": MARKOV_ORDER,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Canary written to {output_path}")
    for dim in range(2):
        key = f"H{dim}"
        if key in output:
            o = output[key]
            print(f"  {key}: observed={o['observed']:.8f}, null_mean={o['null_mean']:.8f}, p={o['p_value']:.4f}")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("canary_output.json")
    run_canary(out)
