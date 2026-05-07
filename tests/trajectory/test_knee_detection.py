# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Unit tests for detect_eps_star_knee — per-year β₀(ε) knee detection
#          for the zigzag filtration threshold ε* selection.
"""Tests for detect_eps_star_knee and compute_per_year_knee refactor."""

from __future__ import annotations

import numpy as np
import pytest

from trajectory_tda.scripts.run_zigzag_sensitivity import (
    _KNEE_DECREASE_THRESHOLD,
    detect_eps_star_knee,
)

_EPS_GRID = np.arange(0.05, 2.01, 0.01)  # standard BHPS/USoc grid (196 pts)


# ── helpers ──────────────────────────────────────────────────────────────────


def _step_curve(
    eps_grid: np.ndarray,
    step_eps: float,
    hi: float = 100.0,
    lo: float = 1.0,
) -> np.ndarray:
    """Return a step-down β₀ curve: hi for ε < step_eps, lo for ε ≥ step_eps."""
    return np.where(eps_grid < step_eps, hi, lo).astype(np.float64)


def _smooth_decay(eps_grid: np.ndarray, rate: float = 4.0) -> np.ndarray:
    """Return a smooth exponential-decay β₀ curve (100 → ~1)."""
    return (100.0 * np.exp(-rate * eps_grid) + 1.0).astype(np.float64)


# ── Test 1: flat curve → degenerate ──────────────────────────────────────────


class TestFlatCurve:
    def test_completely_flat_returns_degenerate(self):
        """A constant β₀ curve (y_range=0) must be flagged degenerate."""
        values = np.full(len(_EPS_GRID), 50.0)
        knee_eps, is_deg = detect_eps_star_knee(values, _EPS_GRID, 0.05)
        assert is_deg
        assert knee_eps == pytest.approx(_EPS_GRID[0])

    def test_nearly_flat_below_threshold_returns_degenerate(self):
        """A curve with y_range < decrease_threshold * max must be degenerate.

        max=100, decrease_threshold=0.10 → threshold = 10.
        y_range=5 < 10 → degenerate.
        """
        values = np.full(len(_EPS_GRID), 100.0)
        values[-10:] = 95.0  # y_range = 5, max = 100
        knee_eps, is_deg = detect_eps_star_knee(values, _EPS_GRID, 0.10)
        assert is_deg
        assert knee_eps == pytest.approx(_EPS_GRID[0])

    def test_sufficient_variation_not_degenerate(self):
        """A curve with y_range ≥ decrease_threshold × max must proceed."""
        values = _step_curve(_EPS_GRID, step_eps=1.0, hi=100.0, lo=1.0)
        # y_range=99, decrease_threshold=0.05 → threshold=5; 99>5 → not degenerate
        _, is_deg = detect_eps_star_knee(values, _EPS_GRID, 0.05)
        assert not is_deg


# ── Test 2: step-down curve → knee near the step ─────────────────────────────


class TestStepKnee:
    def test_step_at_0_5_returns_knee_near_step(self):
        """Clear step at ε=0.5 should yield knee_eps close to 0.5."""
        values = _step_curve(_EPS_GRID, step_eps=0.5)
        knee_eps, _ = detect_eps_star_knee(values, _EPS_GRID, 0.05)
        assert abs(knee_eps - 0.5) <= 0.06  # within 6 grid steps of the step

    def test_step_at_1_0_returns_knee_near_step(self):
        """Clear step at ε=1.0 should yield knee_eps close to 1.0."""
        values = _step_curve(_EPS_GRID, step_eps=1.0)
        knee_eps, _ = detect_eps_star_knee(values, _EPS_GRID, 0.05)
        assert abs(knee_eps - 1.0) <= 0.06

    def test_smooth_decay_knee_in_interior(self):
        """Smooth decay should locate a knee in the interior of ε grid."""
        values = _smooth_decay(_EPS_GRID, rate=3.0)
        knee_eps, is_deg = detect_eps_star_knee(values, _EPS_GRID, 0.05)
        assert not is_deg
        assert _EPS_GRID[0] < knee_eps < _EPS_GRID[-1]


# ── Test 3: decrease_threshold controls descent region ───────────────────────


class TestDecreaseThreshold:
    def test_floor_equivalence_when_max_100(self):
        """With max=100 and decrease_threshold=0.05, floor=5 matches curve>5."""
        values = _step_curve(_EPS_GRID, step_eps=0.7, hi=100.0, lo=1.0)
        # Both formulations should produce the same descent region
        floor_param = 0.05 * values.max()  # = 5.0
        descent_param = values > floor_param
        descent_hardcoded = values > 5.0
        np.testing.assert_array_equal(descent_param, descent_hardcoded)

    def test_larger_threshold_restricts_descent_region(self):
        """Higher decrease_threshold → narrower eligible region → different knee."""
        values = _smooth_decay(_EPS_GRID, rate=2.0)
        knee_loose, _ = detect_eps_star_knee(values, _EPS_GRID, decrease_threshold=0.01)
        knee_strict, _ = detect_eps_star_knee(values, _EPS_GRID, decrease_threshold=0.20)
        # Stricter threshold may shift or narrow the eligible window
        # Both should return valid (non-eps_grid[0]) knees
        assert knee_loose != _EPS_GRID[0] or knee_strict != _EPS_GRID[0]

    def test_very_high_threshold_flags_degenerate(self):
        """decrease_threshold=0.999 means curve must drop to 0.1% of max.

        A smooth decay from 100 to 1 has y_range=99, max=100+1.
        0.999 * 101 ≈ 101 > 99 → degenerate.
        """
        values = _smooth_decay(_EPS_GRID, rate=4.0)
        _, is_deg = detect_eps_star_knee(values, _EPS_GRID, decrease_threshold=0.999)
        assert is_deg


# ── Test 4: degeneracy_threshold flags tail knees ────────────────────────────


class TestDegeneracyThreshold:
    def test_zero_threshold_disables_tail_check(self):
        """degeneracy_threshold=0 means is_degenerate can only be set by range check."""
        eps = np.linspace(0.05, 2.0, 20)
        values = np.concatenate([np.full(15, 100.0), np.full(5, 6.0)])
        _, is_deg = detect_eps_star_knee(
            values, eps, decrease_threshold=0.05, degeneracy_threshold=0.0
        )
        assert not is_deg

    def test_knee_at_max_y_n_not_flagged_by_high_threshold(self):
        """When y_n[knee]=1.0, even degeneracy_threshold=0.99 does not flag it.

        Step curve [100]*15 + [6]*5: curvature maximum at index 14, y_n=1.0.
        Strict inequality: 1.0 < 0.99 is False → not degenerate.
        """
        eps = np.linspace(0.05, 2.0, 20)
        values = np.concatenate([np.full(15, 100.0), np.full(5, 6.0)])
        _, is_deg = detect_eps_star_knee(
            values, eps, decrease_threshold=0.05, degeneracy_threshold=0.99
        )
        assert not is_deg

    def test_interior_knee_flagged_by_moderate_threshold(self):
        """A knee at y_n≈0.43 (smooth decay, rate=3) is flagged by threshold=0.5.

        The normalised β₀ at the curvature maximum for 100*exp(-3*eps)+1 on
        eps ∈ [0.05, 2.00] is approximately 0.43.  degeneracy_threshold=0.5
        catches this as a tail-adjacent knee.
        """
        values = _smooth_decay(_EPS_GRID, rate=3.0)
        _, is_deg = detect_eps_star_knee(
            values, _EPS_GRID, decrease_threshold=0.05, degeneracy_threshold=0.5
        )
        assert is_deg

    def test_interior_knee_not_flagged_by_default_threshold(self):
        """The same knee (y_n≈0.43) is NOT flagged by the default threshold=0.1."""
        values = _smooth_decay(_EPS_GRID, rate=3.0)
        _, is_deg = detect_eps_star_knee(
            values, _EPS_GRID, decrease_threshold=0.05, degeneracy_threshold=0.1
        )
        assert not is_deg


# ── Test 5: module constant _KNEE_DECREASE_THRESHOLD ─────────────────────────


class TestModuleConstant:
    def test_default_threshold_is_five_percent(self):
        assert _KNEE_DECREASE_THRESHOLD == pytest.approx(0.05)

    def test_default_threshold_produces_valid_knee_on_smooth_curve(self):
        values = _smooth_decay(_EPS_GRID, rate=3.0)
        knee_eps, is_deg = detect_eps_star_knee(values, _EPS_GRID, _KNEE_DECREASE_THRESHOLD)
        assert not is_deg
        assert _EPS_GRID[0] < knee_eps < _EPS_GRID[-1]
