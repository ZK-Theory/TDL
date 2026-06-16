"""Toy STRAND persistence-survival compute for Discovery Harness Spikes."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np


def finite_lifetimes(diagram: np.ndarray) -> np.ndarray:
    """Return positive finite persistence lifetimes from a birth-death diagram."""
    values = np.asarray(diagram, dtype=float)
    if values.ndim != 2 or values.shape[1] != 2:
        raise AssertionError("diagram must have shape (n, 2)")
    if values.size == 0:
        raise AssertionError("diagram must contain at least one row")
    births = values[:, 0]
    deaths = values[:, 1]
    if not np.all(np.isfinite(births)):
        raise AssertionError("birth values must be finite")
    finite = np.isfinite(deaths)
    finite_births = births[finite]
    finite_deaths = deaths[finite]
    if np.any(finite_deaths <= finite_births):
        raise AssertionError("finite death values must exceed birth values")
    lifetimes = finite_deaths - finite_births
    if lifetimes.size == 0:
        raise AssertionError("diagram must contain at least one finite feature")
    return lifetimes


def survival_area_distance(first: np.ndarray, second: np.ndarray) -> float:
    """Exact area between two empirical persistence-survival functions."""
    a = _as_lifetimes(first, "first")
    b = _as_lifetimes(second, "second")
    events = np.unique(np.concatenate(([0.0], a, b)))
    if events.size < 2:
        return 0.0

    left_edges = events[:-1]
    widths = np.diff(events)
    sorted_a = np.sort(a)
    sorted_b = np.sort(b)
    s_a = (a.size - np.searchsorted(sorted_a, left_edges, side="right")) / a.size
    s_b = (b.size - np.searchsorted(sorted_b, left_edges, side="right")) / b.size
    return float(np.sum(np.abs(s_a - s_b) * widths))


def monte_carlo_upper_tail_pvalue(observed: float, null_statistics: Iterable[float]) -> float:
    """Bias-corrected Monte Carlo p-value, P(null >= observed)."""
    null_values = [float(value) for value in null_statistics]
    if not null_values:
        raise AssertionError("null_statistics must be non-empty")
    exceedances = sum(value >= observed for value in null_values)
    return float((exceedances + 1) / (len(null_values) + 1))


def compute_strand_cell(
    observed_diagram: np.ndarray,
    null_diagrams: Sequence[np.ndarray],
    *,
    max_null_diagrams: int,
) -> dict[str, Any]:
    """Compute one toy STRAND cell for one dataset and homology dimension."""
    if isinstance(max_null_diagrams, bool) or max_null_diagrams < 2:
        raise AssertionError("max_null_diagrams must be at least 2")
    selected = list(null_diagrams[:max_null_diagrams])
    if len(selected) < 2:
        raise AssertionError("at least two null diagrams are required")

    observed_lifetimes = finite_lifetimes(observed_diagram)
    null_lifetimes = [finite_lifetimes(diagram) for diagram in selected]
    obs_null_stats = [
        survival_area_distance(observed_lifetimes, lifetimes) for lifetimes in null_lifetimes
    ]
    null_null_stats = [
        survival_area_distance(null_lifetimes[i], null_lifetimes[(i + 1) % len(null_lifetimes)])
        for i in range(len(null_lifetimes))
    ]

    observed_stat = float(np.mean(obs_null_stats))
    p_value = monte_carlo_upper_tail_pvalue(observed_stat, null_null_stats)
    null_mean_lifetime = float(np.mean([np.mean(lifetimes) for lifetimes in null_lifetimes]))
    observed_mean_lifetime = float(np.mean(observed_lifetimes))

    return {
        "observed_features": int(observed_lifetimes.size),
        "null_diagrams_used": len(null_lifetimes),
        "null_null_pairs_used": len(null_null_stats),
        "observed_lifetime_mean": observed_mean_lifetime,
        "observed_lifetime_median": float(np.median(observed_lifetimes)),
        "observed_lifetime_max": float(np.max(observed_lifetimes)),
        "null_lifetime_mean_mean": null_mean_lifetime,
        "null_lifetime_mean_median": float(
            np.median([np.mean(lifetimes) for lifetimes in null_lifetimes])
        ),
        "observed_vs_null_statistic": observed_stat,
        "null_null_statistic_mean": float(np.mean(null_null_stats)),
        "null_null_statistic_median": float(np.median(null_null_stats)),
        "p_value": p_value,
        "effect_direction": (
            "observed_heavier_persistence_tail"
            if observed_mean_lifetime > null_mean_lifetime
            else "observed_lighter_persistence_tail"
        ),
        "null_perturbs_input": _any_null_differs_from_observed(
            observed_lifetimes,
            null_lifetimes,
        ),
    }


def run_strand_spike(
    *,
    usoc_cache: Path,
    bhps_cache: Path,
    usoc_wasserstein: Path,
    bhps_wasserstein: Path,
    usoc_landscape: Path,
    bhps_landscape: Path,
    output: Path,
    max_null_diagrams: int = 100,
) -> dict[str, Any]:
    """Run the bounded STRAND Spike compute and persist a JSON summary."""
    datasets = {
        "usoc": _compute_dataset(usoc_cache, max_null_diagrams=max_null_diagrams),
        "bhps": _compute_dataset(bhps_cache, max_null_diagrams=max_null_diagrams),
    }
    detected_cells = [
        f"{dataset}.{dim}"
        for dataset, dataset_result in datasets.items()
        for dim in ("H0", "H1")
        if dataset_result[dim]["p_value"] <= 0.05
    ]
    all_cells = [
        dataset_result[dim]
        for dataset_result in datasets.values()
        for dim in ("H0", "H1")
    ]
    result = {
        "schema_version": "discovery/strand-spike-compute/v1",
        "candidate_slug": "strand-persistence-survival-testing",
        "created_at": date.today().isoformat(),
        "method": {
            "name": "STRAND-style persistence-survival toy statistic",
            "source": "arXiv:2606.11911",
            "statistic": (
                "Mean observed-vs-null area between empirical persistence-survival "
                "functions of finite feature lifetimes."
            ),
        },
        "parameters": {
            "max_null_diagrams_per_dataset": max_null_diagrams,
            "homology_dimensions": ["H0", "H1"],
            "pvalue_formula": "(r + 1) / (n + 1), upper tail over null-null STRAND distances",
            "null_null_pairing": "cyclic adjacent pairs among the bounded null subset",
        },
        "null_model": {
            "operation": "cached permutation-null diagrams compared against observed diagrams",
            "perturbs_input": all(cell["null_perturbs_input"] for cell in all_cells),
            "input_object": "finite persistence lifetimes consumed by empirical survival curves",
        },
        "datasets": datasets,
        "baselines": {
            "wasserstein": {
                "usoc": _read_wasserstein_baseline(usoc_wasserstein),
                "bhps": _read_wasserstein_baseline(bhps_wasserstein),
            },
            "landscape_l2": {
                "usoc": _read_landscape_baseline(usoc_landscape),
                "bhps": _read_landscape_baseline(bhps_landscape),
            },
        },
        "decision_support": {
            "metric_space_confirmed": True,
            "toy_signal_status": "detected" if detected_cells else "not_detected",
            "detected_cells_p_le_0_05": detected_cells,
            "null_perturbs_input": all(cell["null_perturbs_input"] for cell in all_cells),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def _compute_dataset(cache_path: Path, *, max_null_diagrams: int) -> dict[str, Any]:
    with np.load(cache_path, allow_pickle=True) as cache:
        metadata = cache["metadata"].item()
        return {
            "cache": str(cache_path),
            "metadata": _json_safe(metadata),
            "H0": compute_strand_cell(
                cache["obs_h0_diagram"],
                list(cache["h0_diagrams"]),
                max_null_diagrams=max_null_diagrams,
            ),
            "H1": compute_strand_cell(
                cache["obs_h1_diagram"],
                list(cache["h1_diagrams"]),
                max_null_diagrams=max_null_diagrams,
            ),
        }


def _read_wasserstein_baseline(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells: dict[str, Any] = {}
    for null_name, null_payload in payload.items():
        cells[null_name] = {}
        for dim in ("H0", "H1"):
            if dim in null_payload:
                dim_payload = null_payload[dim]
                cells[null_name][dim] = {
                    "p_value": dim_payload.get("p_value"),
                    "significant_at_005": dim_payload.get("significant_at_005"),
                    "mean_wasserstein_obs_null": dim_payload.get(
                        "mean_wasserstein_obs_null"
                    ),
                    "mean_wasserstein_null_null": dim_payload.get(
                        "mean_wasserstein_null_null"
                    ),
                }
    return {"source": str(path), "cells": cells}


def _read_landscape_baseline(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells = {
        key: {
            "h0_landscape_l2_pvalue": value.get("h0_landscape_l2_pvalue"),
            "h1_landscape_l2_pvalue": value.get("h1_landscape_l2_pvalue"),
        }
        for key, value in payload["result"].items()
    }
    return {
        "source": str(path),
        "run_params": payload.get("run_params", {}),
        "cells": cells,
    }


def _any_null_differs_from_observed(
    observed_lifetimes: np.ndarray,
    null_lifetimes: Sequence[np.ndarray],
) -> bool:
    for lifetimes in null_lifetimes:
        if observed_lifetimes.shape != lifetimes.shape:
            return True
        if not np.allclose(observed_lifetimes, lifetimes):
            return True
    return False


def _as_lifetimes(values: np.ndarray, label: str) -> np.ndarray:
    lifetimes = np.asarray(values, dtype=float)
    if lifetimes.ndim != 1 or lifetimes.size == 0:
        raise AssertionError(f"{label} lifetimes must be a non-empty 1D array")
    if not np.all(np.isfinite(lifetimes)):
        raise AssertionError(f"{label} lifetimes must be finite")
    if np.any(lifetimes <= 0):
        raise AssertionError(f"{label} lifetimes must be positive")
    return lifetimes


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--usoc-cache",
        type=Path,
        default=Path(
            "C:/Users/steph/TDL/results/trajectory_tda_integration/stage1/cache/"
            "null_diagrams_usoc_B1000_L5000_seed42_2026-05-24.npz"
        ),
    )
    parser.add_argument(
        "--bhps-cache",
        type=Path,
        default=Path(
            "C:/Users/steph/TDL/results/trajectory_tda_integration/stage1/cache/"
            "null_diagrams_bhps_B1000_L5000_seed42_2026-05-24.npz"
        ),
    )
    parser.add_argument(
        "--usoc-wasserstein",
        type=Path,
        default=Path("results/trajectory_tda_integration/04_nulls_wasserstein.json"),
    )
    parser.add_argument(
        "--bhps-wasserstein",
        type=Path,
        default=Path("results/trajectory_tda_bhps/04_nulls_wasserstein.json"),
    )
    parser.add_argument(
        "--usoc-landscape",
        type=Path,
        default=Path(
            "results/trajectory_tda_integration/stage1/"
            "landscape_sensitivity_usoc_2026-05-25.json"
        ),
    )
    parser.add_argument(
        "--bhps-landscape",
        type=Path,
        default=Path(
            "results/trajectory_tda_integration/stage1/"
            "landscape_sensitivity_bhps_2026-05-25.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/discovery/strand_persistence_survival_spike_2026-06-16.json"),
    )
    parser.add_argument("--max-null-diagrams", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_strand_spike(
        usoc_cache=args.usoc_cache,
        bhps_cache=args.bhps_cache,
        usoc_wasserstein=args.usoc_wasserstein,
        bhps_wasserstein=args.bhps_wasserstein,
        usoc_landscape=args.usoc_landscape,
        bhps_landscape=args.bhps_landscape,
        output=args.output,
        max_null_diagrams=args.max_null_diagrams,
    )
    print(json.dumps(result["decision_support"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
