# Research context: Stage-1 T1.5c H2 threshold-comparability diagnostic.
# Purpose: Bind pinned-threshold provenance and W2 aggregation helpers.
"""Tests for the T1.5c H2 pinned-threshold diagnostic driver."""

from __future__ import annotations

import numpy as np

import trajectory_tda.scripts.run_h2_pinned_threshold_diagnostic as diagnostic


def _null_result(index: int, distance: float, threshold: float) -> dict:
    dgm = [[float(index), float(index + 1)]]
    return {
        "H0": distance,
        "H1": distance + 1.0,
        "H2": distance + 2.0,
        "H0_dgm": dgm,
        "H1_dgm": dgm,
        "H2_dgm": dgm,
        "_ph_provenance": {
            "threshold_value": threshold,
            "edge_prop_at_thresh": 1.0,
            "candidate_tetrahedra_burden": 10.0,
            "wall_time_seconds": 0.2,
        },
        "_wall_time_seconds": 0.3,
    }


def test_condition_ph_kwargs_pins_only_pinned_condition() -> None:
    base = {"max_dim": 2, "do_cocycles": False}

    auto = diagnostic._condition_ph_kwargs(base, "auto", 12.5)
    pinned = diagnostic._condition_ph_kwargs(base, "pinned", 12.5)

    assert "thresh" not in auto
    assert pinned["thresh"] == 12.5
    assert "thresh" not in base


def test_verify_pinned_thresholds_requires_observed_and_all_nulls() -> None:
    obs_provenance = {"threshold_value": 3.5}
    null_results = [_null_result(0, 1.0, 3.5), _null_result(1, 2.0, 3.5)]
    assert diagnostic._verify_pinned_thresholds(3.5, obs_provenance, null_results)

    null_results[1]["_ph_provenance"]["threshold_value"] = 3.6
    assert not diagnostic._verify_pinned_thresholds(3.5, obs_provenance, null_results)


def test_aggregate_condition_stats_reports_all_homology_dimensions(monkeypatch) -> None:
    null_results = [_null_result(i, float(i + 1), 2.0) for i in range(4)]

    monkeypatch.setattr(
        diagnostic,
        "_draw_null_pairs",
        lambda n_permutations, seed, cap=500: [(0, 1), (1, 2), (2, 3)],
    )
    monkeypatch.setattr(
        diagnostic,
        "_wasserstein_from_diagrams",
        lambda dgm_a, dgm_b, dim: float(dim + 1),
    )

    stats = diagnostic._aggregate_condition_stats(null_results, seed=42, max_dim=2)

    assert stats["pair_draw_seed"] == 42
    assert stats["pair_indices"] == [[0, 1], [1, 2], [2, 3]]
    for dim, expected_null_null in [("H0", 1.0), ("H1", 2.0), ("H2", 3.0)]:
        assert np.isfinite(stats[dim]["mean_wasserstein_obs_null"])
        assert stats[dim]["mean_wasserstein_null_null"] == expected_null_null
        assert stats[dim]["n_null_null_pairs"] == 3
        assert stats[dim]["pvalue_null_draws"] == 3
        assert len(stats[dim]["obs_null_distribution"]) == 4
        assert len(stats[dim]["null_null_distribution"]) == 3
