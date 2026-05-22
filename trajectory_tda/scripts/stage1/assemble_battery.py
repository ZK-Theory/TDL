# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Assemble the combined matched_w2_battery_<date>.json from per-phase JSONs
#   written by the four upstream phase scripts. Produces the same top-level schema
#   as the legacy monolith's combined output so downstream consumers
#   (paper draft, supplement, Computational-Log) are unchanged.
"""Stage 1 — battery assembly.

Reads:
    * ``usoc_headline_<date>.json`` and ``bhps_headline_<date>.json``
      (committed deliverables of the headline phases)
    * Zero or more ``lm_sensitivity_L<L>_<date>.json``
    * Optional ``landscape_sensitivity_<date>.json``

Writes:
    ``matched_w2_battery_<date>.json`` with the same top-level schema as
    the legacy monolith's combined JSON.

Usage::

    uv run --env-file .env python trajectory_tda/scripts/stage1/assemble_battery.py \\
        --usoc results/trajectory_tda_integration/stage1/usoc_headline_<date>.json \\
        --bhps results/trajectory_tda_integration/stage1/bhps_headline_<date>.json \\
        --lm results/trajectory_tda_integration/stage1/lm_sensitivity_L2500_<date>.json \\
        --lm results/trajectory_tda_integration/stage1/lm_sensitivity_L5000_<date>.json \\
        --lm results/trajectory_tda_integration/stage1/lm_sensitivity_L8000_<date>.json \\
        --landscape results/trajectory_tda_integration/stage1/landscape_sensitivity_<date>.json
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from trajectory_tda.scripts.stage1 import _battery_core as core


def _load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble combined Stage 1 battery JSON")
    parser.add_argument("--usoc", type=str, required=True, help="USoc headline JSON")
    parser.add_argument("--bhps", type=str, default=None, help="BHPS headline JSON (optional)")
    parser.add_argument(
        "--lm",
        type=str,
        action="append",
        default=[],
        help="LM sensitivity JSON for one L (repeatable).",
    )
    parser.add_argument(
        "--landscape",
        type=str,
        default=None,
        help="Landscape sensitivity JSON.",
    )
    parser.add_argument("--output", type=str, default=None, help="Override output path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    usoc = _load_json(Path(args.usoc))
    bhps = _load_json(Path(args.bhps)) if args.bhps else {"result": {}}

    sensitivity_landmark: dict[str, Any] = {}
    for lm_path in args.lm:
        lm = _load_json(Path(lm_path))
        for k, v in lm.get("result", {}).items():
            sensitivity_landmark[k] = v

    sensitivity_landscape: dict[str, Any] = {}
    if args.landscape:
        ls = _load_json(Path(args.landscape))
        sensitivity_landscape = ls.get("result", {})

    # The headline run_params are the authoritative ones for the combined JSON
    run_params = usoc.get("run_params", {})

    combined: dict[str, Any] = {
        "run_params": run_params,
        "usoc": usoc.get("result", {}),
        "bhps": bhps.get("result", {}),
        "sensitivity_landmark": sensitivity_landmark,
        "sensitivity_landscape": sensitivity_landscape,
    }

    today = date.today().isoformat()
    out_path = (
        Path(args.output)
        if args.output
        else core.worktree_root() / f"results/trajectory_tda_integration/stage1/matched_w2_battery_{today}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(core.convert_numpy(combined), f, indent=2)
    print(f"Combined battery JSON: {out_path}")


if __name__ == "__main__":
    main()
