# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Regression tests for Stage 1 W2/landscape aggregation statistics.
"""Regression tests for Stage 1 battery aggregation edge cases."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

import trajectory_tda.scripts.run_stage1_battery as legacy_battery
import trajectory_tda.scripts.stage1._battery_core as battery_core

STAGE1_AGGREGATE_REQUIRED_KEYS = (
    "w2_pvalue",
    "pvalue_null_draws",
    "effect_null_pairs",
    "landscape_l2_pvalue",
    "t_ratio",
    "bca_ci_lower",
    "bca_ci_upper",
    "d_perm",
    "mean_obs_null",
    "mean_null_null",
    "landscape_t_ratio",
    "landscape_bca_ci_lower",
    "landscape_bca_ci_upper",
    "landscape_d_perm",
)


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
            "pvalue_null_draws": 2,
            "effect_null_pairs": 1,
            "landscape_l2_pvalue": 0.5,
            "t_ratio": 1.25,
            "bca_ci_lower": None,
            "bca_ci_upper": None,
            "d_perm": 0.75,
            "mean_obs_null": 2.0,
            "mean_null_null": 1.6,
            "landscape_t_ratio": 1.15,
            "landscape_bca_ci_lower": None,
            "landscape_bca_ci_upper": None,
            "landscape_d_perm": 0.65,
        },
        "h1": {
            "w2_pvalue": 0.75,
            "pvalue_null_draws": 2,
            "effect_null_pairs": 1,
            "landscape_l2_pvalue": 0.8,
            "t_ratio": 0.9,
            "bca_ci_lower": None,
            "bca_ci_upper": None,
            "d_perm": -0.1,
            "mean_obs_null": 1.8,
            "mean_null_null": 2.0,
            "landscape_t_ratio": 0.8,
            "landscape_bca_ci_lower": None,
            "landscape_bca_ci_upper": None,
            "landscape_d_perm": -0.2,
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
    for dim_key in ("h0", "h1"):
        cell = result[dim_key]
        assert set(STAGE1_AGGREGATE_REQUIRED_KEYS) <= set(cell)
        assert isinstance(cell["w2_pvalue"], float)
        assert isinstance(cell["pvalue_null_draws"], int)
        assert isinstance(cell["effect_null_pairs"], int)
        assert isinstance(cell["landscape_l2_pvalue"], float)
        assert isinstance(cell["t_ratio"], float)
        assert cell["bca_ci_lower"] is None or isinstance(cell["bca_ci_lower"], float)
        assert cell["bca_ci_upper"] is None or isinstance(cell["bca_ci_upper"], float)
        assert isinstance(cell["d_perm"], float)
        assert isinstance(cell["mean_obs_null"], float)
        assert isinstance(cell["mean_null_null"], float)
        assert isinstance(cell["landscape_t_ratio"], float)
        assert cell["landscape_bca_ci_lower"] is None or isinstance(cell["landscape_bca_ci_lower"], float)
        assert cell["landscape_bca_ci_upper"] is None or isinstance(cell["landscape_bca_ci_upper"], float)
        assert isinstance(cell["landscape_d_perm"], float)


def test_lm_sensitivity_cli_writes_aggregate_result_shape(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """The LM CLI JSON must expose h0/h1 directly under result for schema validation."""
    import sys
    from trajectory_tda.scripts.stage1 import run_lm_sensitivity

    full_payload = {
        "h0": {
            "w2_pvalue": 0.25,
            "landscape_l2_pvalue": 0.5,
            "t_ratio": 1.25,
            "bca_ci_lower": None,
            "bca_ci_upper": None,
            "d_perm": 0.75,
            "mean_obs_null": 2.0,
            "mean_null_null": 1.6,
            "landscape_t_ratio": 1.15,
            "landscape_bca_ci_lower": None,
            "landscape_bca_ci_upper": None,
            "landscape_d_perm": 0.65,
            "pvalue_null_draws": 2,
            "effect_null_pairs": 1,
            "lower_tail_pvalue": 0.5,
        },
        "h1": {
            "w2_pvalue": 0.75,
            "landscape_l2_pvalue": 0.8,
            "t_ratio": 0.9,
            "bca_ci_lower": None,
            "bca_ci_upper": None,
            "d_perm": -0.1,
            "mean_obs_null": 1.8,
            "mean_null_null": 2.0,
            "landscape_t_ratio": 0.8,
            "landscape_bca_ci_lower": None,
            "landscape_bca_ci_upper": None,
            "landscape_d_perm": -0.2,
            "pvalue_null_draws": 2,
            "effect_null_pairs": 1,
        },
    }

    monkeypatch.setattr(run_lm_sensitivity.core, "worktree_root", lambda: tmp_path)
    monkeypatch.setattr(run_lm_sensitivity.core, "write_launch_marker", lambda *args, **kwargs: tmp_path / "launch.pid")
    monkeypatch.setattr(run_lm_sensitivity.core, "run_lm_sensitivity_single_L", lambda **kwargs: full_payload)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_lm_sensitivity.py",
            "--usoc-dir",
            str(tmp_path),
            "--L",
            "2500",
            "--B",
            "2",
            "--frozen-loadings",
            "--smoke",
        ],
    )

    run_lm_sensitivity.main()

    out_path = next((tmp_path / "results/trajectory_tda_integration/stage1").glob("lm_sensitivity_L2500_frozen_smoke_*.json"))
    payload = json.loads(out_path.read_text())
    assert payload["result"] == full_payload
    assert "L2500" not in payload["result"]
