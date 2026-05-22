# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: USoc headline phase — matched-L W2 + landscape L2 with B Markov-1 perms.
#   Writes the phase result JSON to WORKTREE on completion.
"""Stage 1 — USoc headline phase.

Usage::

    uv run --env-file .env python trajectory_tda/scripts/stage1/run_usoc_headline.py \\
        --usoc-dir results/trajectory_tda_integration \\
        --L 5000 --B 1000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from trajectory_tda.scripts.stage1 import _battery_core as core


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 USoc headline phase")
    parser.add_argument("--usoc-dir", type=str, default="results/trajectory_tda_integration")
    parser.add_argument("--L", type=int, default=core.DEFAULT_L, help="Landmarks (default 5000)")
    parser.add_argument("--B", type=int, default=core.DEFAULT_B, help="Permutations (default 1000)")
    parser.add_argument("--seed", type=int, default=core.DEFAULT_SEED)
    parser.add_argument("--k-max", type=int, default=core.DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=core.DEFAULT_N_POINTS)
    parser.add_argument(
        "--n-null-pairs", type=int, default=core.DEFAULT_N_NULL_PAIRS,
        help="Cap on null-null pairs (default 500)",
    )
    parser.add_argument(
        "--n-jobs", type=int, default=4,
        help="Permutation parallelism (locked to 4 at L>=2000 per OOM finding)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out, _null_results, _ph_obs = core.run_headline(
        checkpoint_dir=Path(args.usoc_dir),
        n_permutations=args.B,
        n_landmarks=args.L,
        k_max=args.k_max,
        n_points=args.n_points,
        seed=args.seed,
        label="USoc",
        n_jobs=args.n_jobs,
        n_null_pairs_cap=args.n_null_pairs,
    )

    today = date.today().isoformat()
    out_dir = core.worktree_root() / "results/trajectory_tda_integration/stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"usoc_headline_{today}.json"
    payload = {
        "phase": "usoc_headline",
        "run_params": {
            "L": args.L,
            "B": args.B,
            "null_model": f"markov-{core.DEFAULT_MARKOV_ORDER}",
            "seed": args.seed,
            "landscape_k_max": args.k_max,
            "landscape_n_points": args.n_points,
            "pvalue_formula": "(r+1)/(B+1)",
        },
        "dataset": "usoc",
        "result": out,
    }
    with open(out_path, "w") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
    print(f"USoc headline JSON: {out_path}")


if __name__ == "__main__":
    main()
