# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Single-L landmark sensitivity phase — runs USoc battery at a single L
#   (variable via --L). Designed for independent dispatch per L value so a halt
#   on one sub-phase never costs a completed sub-phase.
"""Stage 1 — landmark sensitivity at a single L value.

One invocation = one sub-phase. Run once per L in the sensitivity sweep.

Usage::

    uv run --env-file .env python trajectory_tda/scripts/stage1/run_lm_sensitivity.py \\
        --usoc-dir results/trajectory_tda_integration --L 2500 --B 1000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from trajectory_tda.scripts.stage1 import _battery_core as core


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 USoc landmark sensitivity (single L)")
    parser.add_argument("--usoc-dir", type=str, default="results/trajectory_tda_integration")
    parser.add_argument("--L", type=int, required=True, help="Landmark count for this sub-phase")
    parser.add_argument("--B", type=int, default=core.DEFAULT_B)
    parser.add_argument("--seed", type=int, default=core.DEFAULT_SEED)
    parser.add_argument("--k-max", type=int, default=core.DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=core.DEFAULT_N_POINTS)
    parser.add_argument("--n-null-pairs", type=int, default=core.DEFAULT_N_NULL_PAIRS)
    parser.add_argument("--n-jobs", type=int, default=4)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cell = core.run_lm_sensitivity_single_L(
        checkpoint_dir=Path(args.usoc_dir),
        L=args.L,
        n_permutations=args.B,
        seed=args.seed,
        label="USoc_lm_sens",
        n_jobs=args.n_jobs,
        n_null_pairs_cap=args.n_null_pairs,
        k_max=args.k_max,
        n_points=args.n_points,
    )

    today = date.today().isoformat()
    out_dir = core.worktree_root() / "results/trajectory_tda_integration/stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"lm_sensitivity_L{args.L}_{today}.json"
    payload = {
        "phase": f"lm_sens_L{args.L}",
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
        "result": {f"L{args.L}": cell},
    }
    with open(out_path, "w") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
    print(f"LM sensitivity (L={args.L}) JSON: {out_path}")


if __name__ == "__main__":
    main()
