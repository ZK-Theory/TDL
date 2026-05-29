# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Assemble split USoc/BHPS T1.3 stratified Markov-1 job outputs into
#   the final frozen stratified Markov-1 contract JSON.
"""Assemble split stratified Markov-1 partial outputs."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from trajectory_tda.scripts import run_stratified_battery


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_partial(data: dict[str, Any], dataset: str) -> None:
    if data.get("schema_version") != "stratified-markov1-partial/v1":
        raise ValueError(f"{dataset} partial has unexpected schema_version")
    if data.get("dataset") != dataset:
        raise ValueError(f"Expected {dataset} partial, found {data.get('dataset')!r}")
    params = data.get("params", {})
    if params.get("frozen_loadings") is not True:
        raise ValueError(f"{dataset} partial does not record frozen_loadings=true")
    if not data.get("results"):
        raise ValueError(f"{dataset} partial has no regime results")


def combine_partials(usoc_partial: Path, bhps_partial: Path, output: Path | None = None) -> Path:
    usoc = _load_json(usoc_partial)
    bhps = _load_json(bhps_partial)
    _validate_partial(usoc, "usoc")
    _validate_partial(bhps, "bhps")

    usoc_params = usoc["params"]
    bhps_params = bhps["params"]
    checked_keys = ["L", "B", "markov_order", "seed", "k_max", "n_points", "fdr_alpha"]
    mismatched = [key for key in checked_keys if usoc_params.get(key) != bhps_params.get(key)]
    if mismatched:
        raise ValueError(f"Partial parameter mismatch: {mismatched}")

    payload = run_stratified_battery._assemble_output(
        usoc_results=usoc["results"],
        bhps_results=bhps["results"],
        n_permutations=int(usoc_params["B"]),
        n_landmarks=int(usoc_params["L"]),
        seed=int(usoc_params["seed"]),
        frozen_loadings=bool(usoc_params["frozen_loadings"]),
        today=date.today().isoformat(),
    )
    output_path = output or Path(
        "results/trajectory_tda_integration/stratified_markov/"
        f"stratified_markov1_W2_L{usoc_params['L']}_frozen_{date.today().isoformat()}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(run_stratified_battery._convert_numpy(payload), f, indent=2)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble split stratified Markov-1 partial JSONs")
    parser.add_argument("--usoc-partial", type=Path, required=True)
    parser.add_argument("--bhps-partial", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    out_path = combine_partials(args.usoc_partial, args.bhps_partial, output=args.output)
    print(f"Stratified Markov-1 frozen JSON: {out_path}")


if __name__ == "__main__":
    main()
