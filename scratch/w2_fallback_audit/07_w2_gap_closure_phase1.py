"""Produce the cache-backed T1.38 Phase 1 W2 gap-closure result.

This runner deliberately delegates distance calculation and aggregation to the
audited ``audit_lib`` reference implementation.  It never invokes the legacy
pipeline fallback: ``audit_lib.exact_w2`` imports Gudhi's POT/EMD backend.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import gudhi
import numpy as np
import ot
from scipy.stats import bootstrap

import audit_lib


PROJ_ROOT = Path("C:/Users/steph/TDL")
WORKTREE_ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = (
    PROJ_ROOT / "results/trajectory_tda_integration/stage1/cache/"
    "null_diagrams_bhps_nonoverlap_frozen_B1000_L5000_seed42_2026-06-09.npz"
)
CORRECTED_BHPS = PROJ_ROOT / "results/trajectory_tda_bhps/stage1/" "bhps_headline_frozen_corrected_2026-07-14.json"
COMMITTED_NONOVERLAP = (
    PROJ_ROOT / "results/panel_methodology/bhps_nonoverlap/" "bhps_nonoverlap_reanalysis_2026-06-09.json"
)


def _exact_solver_metadata() -> dict[str, object]:
    """Fail before computation unless the actual Gudhi/POT path is available."""
    try:
        from gudhi.wasserstein import wasserstein_distance
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("POT/Gudhi exact W2 backend is unavailable; aborting") from exc
    probe = wasserstein_distance(np.array([[0.0, 2.0]]), np.array([[1.0, 3.0]]), order=2, internal_p=2)
    if not np.isfinite(probe):  # pragma: no cover - defensive backend guard
        raise RuntimeError("POT/Gudhi exact W2 probe returned a non-finite value")
    return {
        "name": "gudhi.wasserstein.wasserstein_distance",
        "exact": True,
        "pot_available": True,
        "backend_version": {"gudhi": gudhi.__version__, "pot": ot.__version__},
        "order": 2,
        "internal_p": 2,
        "actual_call_path_probe_w2": float(probe),
    }


def _bca_t_ratio(obs_null: np.ndarray, null_null: np.ndarray) -> dict[str, float]:
    """Return the pre-registered deterministic BCa interval for the T ratio."""

    def statistic(obs: np.ndarray, null: np.ndarray, axis: int = -1) -> np.ndarray:
        return np.mean(obs, axis=axis) / np.mean(null, axis=axis)

    result = bootstrap(
        (obs_null, null_null),
        statistic,
        paired=False,
        n_resamples=2000,
        confidence_level=0.95,
        method="BCa",
        rng=np.random.default_rng(42),
    )
    return {
        "t_ratio": float(statistic(obs_null, null_null)),
        "ci_95_bca_lower": float(result.confidence_interval.low),
        "ci_95_bca_upper": float(result.confidence_interval.high),
        "n_bootstrap": 2000,
        "seed": 42,
    }


def _screen_distances(
    diagrams_a: list[np.ndarray], diagrams_b: list[np.ndarray], distances: np.ndarray
) -> dict[str, float | int]:
    bounds = np.array([audit_lib.diagonal_bound(a, b) for a, b in zip(diagrams_a, diagrams_b, strict=True)])
    ratios = np.divide(distances, bounds, out=np.zeros_like(distances), where=bounds > 0)
    violations = distances > bounds + 1e-10
    if np.any(violations):
        raise RuntimeError("Exact-W2 diagonal-bound screen failed; refusing to write result")
    return {
        "n_values_screened": int(len(distances)),
        "n_violations": int(np.sum(violations)),
        "max_ratio_to_bound": float(np.max(ratios, initial=0.0)),
        "tol": 1e-10,
    }


def _benchmark(cache: dict[str, object]) -> dict[str, object]:
    h1 = cache["h1_diagrams"]
    obs_h1 = cache["obs_h1_diagram"]
    pair_indices = audit_lib.reproduce_pair_indices(len(h1), 4, 42)
    units: list[tuple[np.ndarray, np.ndarray]] = [(obs_h1, h1[index]) for index in range(4)]
    units.extend((h1[left], h1[right]) for left, right in pair_indices)
    seconds: list[float] = []
    for index, (left, right) in enumerate(units, start=1):
        start = time.perf_counter()
        audit_lib.exact_w2(left, right)
        elapsed = time.perf_counter() - start
        seconds.append(elapsed)
        print(f"benchmark {index}/{len(units)}: {elapsed:.3f} s", flush=True)
    p75 = float(np.percentile(seconds, 75))
    # Phase 2 has 6 nulls x 2 datasets x (100 obs-null + 100 null-null) units.
    phase2_units = 6 * 2 * (100 + 100)
    return {
        "n_units_benchmarked": len(seconds),
        "median_seconds_per_unit": float(np.median(seconds)),
        "min_seconds_per_unit": float(np.min(seconds)),
        "max_seconds_per_unit": float(np.max(seconds)),
        "p75_seconds_per_unit": p75,
        "worker_count": 1,
        "per_pair_cost_matrix_gb": None,
        "phase2_projected_units": phase2_units,
        "projected_wall_hours": phase2_units * p75 / 3600,
        "projection_basis": "p75 from 8 serial exact W2 units drawn from the retained non-overlap cache",
    }


def build_result() -> dict[str, object]:
    solver = _exact_solver_metadata()
    cache = audit_lib.load_cache(CACHE_PATH)
    benchmark = _benchmark(cache)
    h1 = cache["h1_diagrams"]
    obs_h1 = cache["obs_h1_diagram"]
    pair_indices = audit_lib.reproduce_pair_indices(len(h1), 1000, 42)

    greedy_obs_null = audit_lib.obs_null_distances(obs_h1, h1, "greedy")
    greedy_null_null = audit_lib.null_null_distances(h1, pair_indices, "greedy")
    greedy_stats = audit_lib.headline_stats_from_distances(greedy_obs_null, greedy_null_null)
    committed = json.loads(COMMITTED_NONOVERLAP.read_text(encoding="utf-8"))
    committed_d_perm = committed["arm_b"]["remainder_h1_w2_d_perm"]
    absdiff = abs(greedy_stats["d_perm"] - committed_d_perm)
    tol = 1e-9
    if absdiff > tol:
        raise RuntimeError("Fresh greedy convention gate did not reproduce the committed remainder")

    exact_obs_null: list[float] = []
    exact_obs_diagrams: list[np.ndarray] = []
    exact_null_diagrams: list[np.ndarray] = []
    for index, null_dgm in enumerate(h1, start=1):
        exact_obs_null.append(audit_lib.exact_w2(obs_h1, null_dgm))
        exact_obs_diagrams.append(obs_h1)
        exact_null_diagrams.append(null_dgm)
        if index == 1 or index % 25 == 0:
            print(f"exact obs-null {index}/{len(h1)}", flush=True)
    exact_null_null: list[float] = []
    nn_left: list[np.ndarray] = []
    nn_right: list[np.ndarray] = []
    for index, (left_index, right_index) in enumerate(pair_indices, start=1):
        left, right = h1[left_index], h1[right_index]
        exact_null_null.append(audit_lib.exact_w2(left, right))
        nn_left.append(left)
        nn_right.append(right)
        if index == 1 or index % 25 == 0:
            print(f"exact null-null {index}/{len(pair_indices)}", flush=True)
    exact_obs_array = np.array(exact_obs_null)
    exact_nn_array = np.array(exact_null_null)
    obs_screen = _screen_distances(exact_obs_diagrams, exact_null_diagrams, exact_obs_array)
    nn_screen = _screen_distances(nn_left, nn_right, exact_nn_array)
    exact_stats = audit_lib.headline_stats_from_distances(exact_obs_array, exact_nn_array)

    corrected = json.loads(CORRECTED_BHPS.read_text(encoding="utf-8"))
    bca = _bca_t_ratio(
        np.array(corrected["h1"]["per_pair"]["obs_null_exact"]),
        np.array(corrected["h1"]["per_pair"]["null_null_exact"]),
    )
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKTREE_ROOT, text=True).strip()
    return {
        "schema_version": "stage1/w2-gap-closure/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "task": "T1.38 W2 gap closure phase 1",
        "phase": "phase1",
        "pre_registration": "results/trajectory_tda_integration/stage1/pre_registrations_w2_gap_closure_2026-07-15.json",
        "solver": solver,
        "params": {"seed": 42, "frozen_loadings": True, "p_value_formula": "(r+1)/(B+1)"},
        "inputs": {
            "git_head": git_head,
            "cache": {"absolute_path": str(CACHE_PATH), "sha256": audit_lib.sha256_file(CACHE_PATH)},
            "bhps_corrected_headline": str(CORRECTED_BHPS),
            "committed_nonoverlap": str(COMMITTED_NONOVERLAP),
        },
        "convention_gate": {
            "reference_freshly_recomputed": True,
            "reference_source": "fresh greedy replica over retained cache",
            "artifact_under_test": str(COMMITTED_NONOVERLAP),
            "greedy_replica_reproduces_committed": True,
            "absdiff": absdiff,
            "tol": tol,
            "reproduced_field": "arm_b.remainder_h1_w2_d_perm",
            "fresh_greedy": greedy_stats,
        },
        "diagonal_bound_screen": {
            "n_values_screened": obs_screen["n_values_screened"] + nn_screen["n_values_screened"],
            "n_violations": 0,
            "max_ratio_to_bound": max(obs_screen["max_ratio_to_bound"], nn_screen["max_ratio_to_bound"]),
            "tol": 1e-10,
            "obs_null": obs_screen,
            "null_null": nn_screen,
        },
        "cost_model": benchmark,
        "phase1": {
            "bhps_markov1_h1_t_ratio_bca": bca,
            "nonoverlap_h1_exact": exact_stats,
            "markov2_alpha_sweep": {
                "classification": "UNVERIFIABLE",
                "reason": "No retained diagram cache or other solver-identifying artifact was found; date and dependency pin are not evidence.",
            },
            "legacy_04_nulls": {
                "classification": "SUSPECT-UNVERIFIABLE",
                "reason": "No cache exists for the 2026-04-07 object; the earliest retained cache is 2026-05-24.",
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    output = WORKTREE_ROOT / "results/trajectory_tda_integration/stage1" / f"w2_gap_closure_phase1_{args.date}.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing result: {output}")
    result = build_result()
    output.write_text(json.dumps(audit_lib.convert_numpy(result), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}", flush=True)


if __name__ == "__main__":
    main()
