# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Unit tests for compute_w2_ratio_bca_ci and compute_w2_ratio_delta_ci —
#          mean-vs-mean W₂ test construction for the permutation null battery.
"""Tests for W₂ ratio test construction with BCa and delta-method CIs."""

from __future__ import annotations

import numpy as np
import pytest

from trajectory_tda.topology.vectorisation import (
    compute_w2_ratio_bca_ci,
    compute_w2_ratio_delta_ci,
)

_RNG = np.random.default_rng(0)


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_arrays(
    n_obs: int = 100,
    n_null: int = 500,
    mean_obs: float = 11.0,
    mean_null: float = 6.0,
    seed: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    w_obs = rng.exponential(mean_obs, size=n_obs)
    w_null = rng.exponential(mean_null, size=n_null)
    return w_obs, w_null


# ── Test 1: T_ratio recovers analytical value ─────────────────────────────────


class TestTRatioRecovery:
    def test_t_ratio_close_to_analytical(self):
        """T_ratio = mean(w_obs)/mean(w_null) recovers mean_obs/mean_null within 10%."""
        mean_obs, mean_null = 11.0, 6.0
        w_obs, w_null = _make_arrays(n_obs=100, n_null=500, mean_obs=mean_obs, mean_null=mean_null)
        t_ratio, _, _ = compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=999, seed=42)
        expected = w_obs.mean() / w_null.mean()
        assert abs(t_ratio - expected) < 1e-10, "T_ratio must equal mean_obs/mean_null exactly"
        assert abs(t_ratio - mean_obs / mean_null) / (mean_obs / mean_null) < 0.10

    def test_t_ratio_greater_than_1_when_obs_larger(self):
        """T_ratio > 1 when observed W₂ is systematically larger than null-null."""
        w_obs, w_null = _make_arrays(mean_obs=15.0, mean_null=5.0)
        t_ratio, _, _ = compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=999, seed=42)
        assert t_ratio > 1.0

    def test_t_ratio_less_than_1_when_obs_smaller(self):
        """T_ratio < 1 when observed W₂ is systematically smaller than null-null."""
        w_obs, w_null = _make_arrays(mean_obs=3.0, mean_null=10.0)
        t_ratio, _, _ = compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=999, seed=42)
        assert t_ratio < 1.0


# ── Test 2: BCa CI validity ───────────────────────────────────────────────────


class TestBCaCI:
    def test_bca_ci_runs_without_error(self):
        """BCa CI computation completes on standard inputs."""
        w_obs, w_null = _make_arrays()
        t_ratio, ci_lo, ci_hi = compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=999, seed=42)
        assert np.isfinite(t_ratio)
        assert np.isfinite(ci_lo)
        assert np.isfinite(ci_hi)

    def test_bca_ci_lower_less_than_upper(self):
        """CI must be a valid interval: lower < T_ratio < upper."""
        w_obs, w_null = _make_arrays()
        t_ratio, ci_lo, ci_hi = compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=999, seed=42)
        assert ci_lo < t_ratio < ci_hi

    def test_bca_ci_width_reasonable_vs_delta_ci(self):
        """BCa CI width should be at least 50% of delta-method CI width."""
        w_obs, w_null = _make_arrays(n_obs=50, n_null=200)
        t_ratio, bca_lo, bca_hi = compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=999, seed=42)

        n_o, n_n = len(w_obs), len(w_null)
        cv_obs = w_obs.std() / (np.sqrt(n_o) * w_obs.mean())
        cv_null = w_null.std() / (np.sqrt(n_n) * w_null.mean())
        delta_lo, delta_hi = compute_w2_ratio_delta_ci(t_ratio, cv_obs, cv_null)

        bca_width = bca_hi - bca_lo
        delta_width = delta_hi - delta_lo
        assert bca_width >= delta_width * 0.5, (
            f"BCa width={bca_width:.4f} should be ≥ 50% of delta width={delta_width:.4f}"
        )

# ── Test 3: Case A (2D) and Case B (1D) consistency ─────────────────────────


class TestCaseAandB:
    def test_1d_and_2d_produce_same_t_ratio(self):
        """Case A (2D matrix input) and Case B (1D array) give identical T_ratio."""
        rng = np.random.default_rng(7)
        n_obs, n_null = 20, 30
        # Case B: 1D arrays
        w_obs_1d = rng.exponential(10.0, size=n_obs)
        w_null_1d = rng.exponential(5.0, size=n_null)
        t_b, _, _ = compute_w2_ratio_bca_ci(w_obs_1d, w_null_1d, n_boot=99, seed=0)

        # Case A: 2D matrix (n_obs × n_null) — each element is a pairwise distance
        # Flattening should produce the same mean
        w_obs_2d = w_obs_1d.reshape(4, 5)   # 4×5 = 20 elements
        w_null_2d = w_null_1d.reshape(5, 6)  # 5×6 = 30 elements
        t_a, _, _ = compute_w2_ratio_bca_ci(w_obs_2d, w_null_2d, n_boot=99, seed=0)

        assert abs(t_a - t_b) < 1e-10, "Case A and Case B must produce identical T_ratio"

    def test_2d_matrix_flattened_correctly(self):
        """2D input is flattened: T_ratio equals mean of all elements / mean of all elements."""
        rng = np.random.default_rng(5)
        mat_obs = rng.exponential(8.0, size=(10, 15))
        mat_null = rng.exponential(4.0, size=(12, 20))
        t_ratio, _, _ = compute_w2_ratio_bca_ci(mat_obs, mat_null, n_boot=99, seed=0)
        expected = mat_obs.mean() / mat_null.mean()
        assert abs(t_ratio - expected) < 1e-10


# ── Test 4: Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    def test_n_obs_1_raises_informative(self):
        """n_obs=1 raises ValueError with an informative message."""
        w_obs = np.array([5.0])
        w_null = np.array([3.0, 4.0, 5.0])
        with pytest.raises(ValueError, match="at least 2"):
            compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=99)

    def test_n_null_1_raises_informative(self):
        """n_null=1 raises ValueError with an informative message."""
        w_obs = np.array([5.0, 6.0, 7.0])
        w_null = np.array([3.0])
        with pytest.raises(ValueError, match="at least 2"):
            compute_w2_ratio_bca_ci(w_obs, w_null, n_boot=99)

    def test_empty_obs_raises(self):
        """Empty w_obs raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            compute_w2_ratio_bca_ci(np.array([]), np.array([1.0, 2.0]))

    def test_empty_null_raises(self):
        """Empty w_null_null raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            compute_w2_ratio_bca_ci(np.array([1.0, 2.0]), np.array([]))


# ── Test 5: Delta-method CI ───────────────────────────────────────────────────


class TestDeltaMethodCI:
    def test_delta_ci_symmetric_around_t_ratio_on_log_scale(self):
        """Delta CI is symmetric on log scale: log(ci_hi/t) == log(t/ci_lo)."""
        t = 2.5
        ci_lo, ci_hi = compute_w2_ratio_delta_ci(t, se_obs=0.05, se_null=0.03)
        assert abs(np.log(ci_hi / t) - np.log(t / ci_lo)) < 1e-10

    def test_delta_ci_lower_less_than_t_ratio(self):
        ci_lo, ci_hi = compute_w2_ratio_delta_ci(2.0, se_obs=0.1, se_null=0.05)
        assert ci_lo < 2.0 < ci_hi

    def test_larger_se_gives_wider_ci(self):
        """Larger coefficient of variation → wider CI."""
        ci_lo_narrow, ci_hi_narrow = compute_w2_ratio_delta_ci(2.0, se_obs=0.02, se_null=0.01)
        ci_lo_wide, ci_hi_wide = compute_w2_ratio_delta_ci(2.0, se_obs=0.20, se_null=0.10)
        assert (ci_hi_wide - ci_lo_wide) > (ci_hi_narrow - ci_lo_narrow)

    def test_zero_se_gives_point_ci(self):
        """Zero uncertainty → CI collapses to (t_ratio, t_ratio)."""
        t = 1.8
        ci_lo, ci_hi = compute_w2_ratio_delta_ci(t, se_obs=0.0, se_null=0.0)
        assert abs(ci_lo - t) < 1e-10
        assert abs(ci_hi - t) < 1e-10
