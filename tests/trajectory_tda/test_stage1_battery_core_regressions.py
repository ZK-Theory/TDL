# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Regression tests for Stage 1 W2/landscape aggregation statistics.
"""Regression tests for Stage 1 battery aggregation edge cases."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import trajectory_tda.scripts.run_stage1_battery as legacy_battery
import trajectory_tda.scripts.stage1._battery_core as battery_core


class InlineParallel:
    """Small joblib.Parallel stand-in that executes delayed tasks inline."""

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, tasks):
        out = []
        for task in tasks:
            func, args, kwargs = task
            out.append(func(*args, **kwargs))
        return out


def test_aggregate_combined_pvalue_uses_b_draws_not_effect_pair_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """P-values use (r + 1) / (B + 1), while T/d may use the pair cap."""
    import joblib

    monkeypatch.setattr(joblib, "Parallel", InlineParallel)
    monkeypatch.setattr(battery_core, "_null_null_w2_worker", lambda dgm_i, dgm_j, dim: 0.0)

    n_permutations = 10
    null_results = [
        {
            "H0": 1.0,
            "H1": 1.0,
            "H0_dgm": [[0.0, 0.1]],
            "H1_dgm": [[0.0, 0.1]],
        }
        for _ in range(n_permutations)
    ]
    ph_obs = SimpleNamespace(dgms={0: np.array([[0.0, 2.0]]), 1: np.array([[0.0, 2.0]])})

    result = battery_core.aggregate_combined(
        null_results=null_results,
        ph_obs=ph_obs,
        n_permutations=n_permutations,
        max_dim=1,
        k_max=1,
        n_points=32,
        seed=42,
        n_null_pairs_cap=3,
    )

    for dim_key in ("h0", "h1"):
        cell = result[dim_key]
        assert cell["pvalue_null_draws"] == n_permutations
        assert cell["effect_null_pairs"] == 3
        assert cell["w2_pvalue"] == pytest.approx(1 / (n_permutations + 1))
        assert cell["landscape_l2_pvalue"] == pytest.approx(1 / (n_permutations + 1))

    assert result["h0"]["lower_tail_pvalue"] == pytest.approx(1.0)


def test_legacy_stage1_pvalue_uses_b_draws_not_pair_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy reference path must use the same (r + 1) / (B + 1) test."""
    import joblib

    monkeypatch.setattr(joblib, "Parallel", InlineParallel)
    monkeypatch.setattr(legacy_battery, "_null_null_w2_worker", lambda dgm_i, dgm_j, dim: 0.0)

    n_permutations = 12
    null_results = [
        {
            "H0": 1.0,
            "H1": 1.0,
            "H0_dgm": [[0.0, 0.1]],
            "H1_dgm": [[0.0, 0.1]],
        }
        for _ in range(n_permutations)
    ]
    ph_obs = SimpleNamespace(dgms={0: np.array([[0.0, 2.0]]), 1: np.array([[0.0, 2.0]])})

    result = legacy_battery._aggregate_combined(
        null_results=null_results,
        ph_obs=ph_obs,
        n_permutations=n_permutations,
        max_dim=1,
        k_max=1,
        n_points=32,
        seed=42,
    )

    for dim_key in ("h0", "h1"):
        cell = result[dim_key]
        assert cell["pvalue_null_draws"] == n_permutations
        assert cell["effect_null_pairs"] == n_permutations * (n_permutations - 1) // 2
        assert cell["w2_pvalue"] == pytest.approx(1 / (n_permutations + 1))
        assert cell["landscape_l2_pvalue"] == pytest.approx(1 / (n_permutations + 1))


def test_lm_sensitivity_single_L_returns_full_aggregate_schema(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """The LM path must preserve T/d/mean fields needed by comparison tables."""
    import joblib
    import poverty_tda.topology.multidim_ph as multidim_ph
    import trajectory_tda.scripts.run_wasserstein_battery as battery_script
    import trajectory_tda.topology.permutation_nulls as permutation_nulls

    monkeypatch.setattr(joblib, "Parallel", InlineParallel)
    monkeypatch.setattr(battery_core, "write_status", lambda phase, detail="": None)
    monkeypatch.setattr(battery_core, "write_partial", lambda phase_tag, suffix, payload: tmp_path / "partial.json")
    monkeypatch.setattr(
        battery_script,
        "load_checkpoint",
        lambda checkpoint_dir: (np.zeros((3, 2)), [["EL", "EM"], ["EM", "EH"], ["EH", "EL"]], {"pca_dim": 2}),
    )
    monkeypatch.setattr(multidim_ph, "compute_rips_ph", lambda landmarks, max_dim: SimpleNamespace(dgms={}))
    monkeypatch.setattr(permutation_nulls, "_single_permutation", lambda *args, **kwargs: {"ok": True})

    full_payload = {
        "h0": {
            "w2_pvalue": 0.25,
            "landscape_l2_pvalue": 0.5,
            "t_ratio": 1.25,
            "d_perm": 0.75,
            "mean_obs_null": 2.0,
            "mean_null_null": 1.6,
        },
        "h1": {
            "w2_pvalue": 0.75,
            "landscape_l2_pvalue": 0.8,
            "t_ratio": 0.9,
            "d_perm": -0.1,
            "mean_obs_null": 1.8,
            "mean_null_null": 2.0,
        },
    }
    monkeypatch.setattr(battery_core, "aggregate_combined", lambda *args, **kwargs: full_payload)

    result = battery_core.run_lm_sensitivity_single_L(
        checkpoint_dir=tmp_path,
        L=3,
        n_permutations=2,
        seed=42,
        label="regression",
        phase_tag="regression",
        n_jobs=1,
    )

    assert result == full_payload
    assert {"t_ratio", "d_perm", "mean_obs_null", "mean_null_null"} <= set(result["h0"])
