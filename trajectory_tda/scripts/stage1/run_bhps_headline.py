# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: BHPS headline phase — matched-L W2 + landscape L2 with B Markov-1 perms.
#   Writes the phase result JSON to WORKTREE on completion and the null-diagram
#   cache .npz to PROJ_ROOT for downstream landscape sensitivity reuse.
"""Stage 1 — BHPS headline phase.

Usage::

    uv run --env-file .env python trajectory_tda/scripts/stage1/run_bhps_headline.py \\
        --L 5000 --B 1000 --seed 42

``--bhps-dir`` defaults to the absolute canonical PROJ_ROOT path
(``<PROJ_ROOT>/results/trajectory_tda_bhps``) via
``_battery_core.proj_root()``, so the script resolves the upstream
trajectory checkpoint correctly regardless of CWD — including when launched
from a ``git worktree`` directory. Override with ``--bhps-dir`` only for
explicit cross-machine or non-standard layouts.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from trajectory_tda.scripts.stage1 import _battery_core as core


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 BHPS headline phase")
    parser.add_argument(
        "--bhps-dir",
        type=str,
        default=str(core.proj_root() / "results/trajectory_tda_bhps"),
        help=(
            "Upstream BHPS trajectory checkpoint directory. Defaults to the "
            "canonical PROJ_ROOT path so worktree execution works without an "
            "override (default: %(default)s)."
        ),
    )
    parser.add_argument("--L", type=int, default=core.DEFAULT_L, help="Landmarks (default 5000)")
    parser.add_argument("--B", type=int, default=core.DEFAULT_B, help="Permutations (default 1000)")
    parser.add_argument("--seed", type=int, default=core.DEFAULT_SEED)
    parser.add_argument("--k-max", type=int, default=core.DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=core.DEFAULT_N_POINTS)
    parser.add_argument(
        "--n-null-pairs",
        type=int,
        default=core.DEFAULT_N_NULL_PAIRS,
        help="Cap on null-null pairs (default 500)",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=4,
        help="Permutation parallelism (locked to 4 at L>=2000 per OOM finding)",
    )
    parser.add_argument("--smoke", action="store_true", help="Smoke-test mode.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    phase_tag = "bhps_headline"
    core.write_launch_marker(
        phase_tag,
        {"L": args.L, "B": args.B, "seed": args.seed, "smoke": args.smoke},
    )

    out, null_results, ph_obs = core.run_headline(
        checkpoint_dir=Path(args.bhps_dir),
        n_permutations=args.B,
        n_landmarks=args.L,
        k_max=args.k_max,
        n_points=args.n_points,
        seed=args.seed,
        label="BHPS",
        phase_tag=phase_tag,
        n_jobs=args.n_jobs,
        n_null_pairs_cap=args.n_null_pairs,
    )

    today = date.today().isoformat()
    smoke_tag = "_smoke" if args.smoke else ""

    cache_dir = core.proj_root() / "results/trajectory_tda_integration/stage1/cache"
    cache_name = f"null_diagrams_bhps_B{args.B}_L{args.L}_seed{args.seed}{smoke_tag}_{today}.npz"
    cache_path = core.write_null_diagram_cache(
        cache_dir / cache_name,
        null_results,
        ph_obs,
        {
            "B": args.B,
            "L": args.L,
            "seed": args.seed,
            "dataset": "bhps",
            "timestamp": today,
            "smoke": args.smoke,
        },
    )

    out_dir = core.worktree_root() / "results/trajectory_tda_integration/stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"bhps_headline{smoke_tag}_{today}.json"
    payload = {
        "phase": phase_tag,
        "run_params": {
            "L": args.L,
            "B": args.B,
            "null_model": f"markov-{core.DEFAULT_MARKOV_ORDER}",
            "seed": args.seed,
            "landscape_k_max": args.k_max,
            "landscape_n_points": args.n_points,
            "pvalue_formula": "(r+1)/(B+1)",
            "null_diagram_cache": str(cache_path),
        },
        "dataset": "bhps",
        "result": out,
    }
    with open(out_path, "w") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
    print(f"BHPS headline JSON: {out_path}")
    print(f"Null-diagram cache: {cache_path}")


if __name__ == "__main__":
    main()
