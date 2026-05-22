# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Landscape sensitivity sweep — reads the headline null-diagram cache
#   (one or more datasets) and sweeps (k_max, n_points). No Rips PH, no Markov
#   simulation; the cache supplies all diagrams. Replaces the redundant
#   permutation re-runs in the legacy monolith's _run_landscape_sensitivity.
"""Stage 1 — landscape sensitivity (cache-driven).

Usage::

    uv run --env-file .env python trajectory_tda/scripts/stage1/run_landscape_sensitivity.py \\
        --cache PROJ_ROOT/results/.../null_diagrams_usoc_B1000_L5000_seed42_<date>.npz \\
        --k-max 3 5 10 --n-points 100 200 500
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from trajectory_tda.scripts.stage1 import _battery_core as core


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 landscape sensitivity (cache-driven)")
    parser.add_argument(
        "--cache",
        type=str,
        required=True,
        help="Path to a null-diagram cache .npz written by a headline phase script.",
    )
    parser.add_argument(
        "--k-max",
        type=int,
        nargs="+",
        default=[3, 5, 10],
        help="k_max values to sweep.",
    )
    parser.add_argument(
        "--n-points",
        type=int,
        nargs="+",
        default=[100, 200, 500],
        help="n_points values to sweep.",
    )
    parser.add_argument("--seed", type=int, default=core.DEFAULT_SEED)
    parser.add_argument("--n-null-pairs", type=int, default=core.DEFAULT_N_NULL_PAIRS)
    parser.add_argument(
        "--label",
        type=str,
        default="USoc_land_sens",
        help="Phase label for logging and JSON.",
    )
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    phase_tag = "landscape_sensitivity"
    cache_path = Path(args.cache)
    if not cache_path.is_absolute():
        cache_path = core.proj_root() / cache_path
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache not found: {cache_path}")

    core.write_launch_marker(
        phase_tag,
        {"cache": str(cache_path), "seed": args.seed, "smoke": args.smoke},
    )

    cache_data = core.read_null_diagram_cache(cache_path)
    meta = cache_data["metadata"]
    logging.info(
        "Loaded cache: dataset=%s B=%s L=%s seed=%s",
        meta.get("dataset"),
        meta.get("B"),
        meta.get("L"),
        meta.get("seed"),
    )

    out = core.sweep_landscape_from_cache(
        cache_data=cache_data,
        k_max_values=args.k_max,
        n_points_values=args.n_points,
        seed=args.seed,
        label=args.label,
        n_null_pairs_cap=args.n_null_pairs,
    )

    today = date.today().isoformat()
    smoke_tag = "_smoke" if args.smoke else ""
    out_dir = core.worktree_root() / "results/trajectory_tda_integration/stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"landscape_sensitivity{smoke_tag}_{today}.json"
    payload = {
        "phase": phase_tag,
        "run_params": {
            "cache": str(cache_path),
            "k_max_values": args.k_max,
            "n_points_values": args.n_points,
            "seed": args.seed,
            "n_null_pairs_cap": args.n_null_pairs,
            "pvalue_formula": "(r+1)/(B+1)",
            "B_from_cache": meta.get("B"),
            "L_from_cache": meta.get("L"),
            "dataset_from_cache": meta.get("dataset"),
        },
        "result": out,
    }
    with open(out_path, "w") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
    print(f"Landscape sensitivity JSON: {out_path}")


if __name__ == "__main__":
    main()
