# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Unit tests for _stratified_markov_shuffle regime-label input validation
#          and correct multi-regime generation. Guards against the collapse-to-2-regimes
#          bug that occurred when a GMM pkl was loaded under a mismatched sklearn version.
"""Tests for _stratified_markov_shuffle regime-label handling."""

from __future__ import annotations

import numpy as np
import pytest

from tests.trajectory.conftest import STATES, make_synthetic_trajectories
from trajectory_tda.topology.permutation_nulls import _stratified_markov_shuffle

N_STATES = len(STATES)
_RNG = np.random.RandomState(42)


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_regime_labels(n: int, k: int, seed: int = 0) -> np.ndarray:
    """Return n integer regime labels drawn uniformly from 0..k-1."""
    rng = np.random.RandomState(seed)
    # Force at least min_regime_n (30) per regime for reliable estimation
    # by constructing balanced blocks then shuffling.
    per_regime = max(30, n // k)
    labels = np.concatenate([np.full(per_regime, r) for r in range(k)])
    labels = labels[:n]
    rng.shuffle(labels)
    return labels.astype(int)


# ── Test 1: input validation — scalar regime_labels raises ───────────────────


class TestInputValidation:
    def test_scalar_regime_labels_raises(self):
        """Passing k (integer) instead of a label array must raise ValueError.

        This is the most common collapse cause: metadata['regime_labels'] = 7
        (the cluster count) instead of the (N,) per-trajectory label array.
        """
        trajs = make_synthetic_trajectories(n=50, t=10, seed=0)
        rng = np.random.RandomState(0)
        with pytest.raises(ValueError, match="1-D array"):
            _stratified_markov_shuffle(trajs, np.array(7), rng)

    def test_2d_regime_labels_raises(self):
        """A 2-D label array (e.g., one-hot or column vector) must raise."""
        trajs = make_synthetic_trajectories(n=50, t=10, seed=0)
        rng = np.random.RandomState(0)
        labels_2d = np.zeros((50, 1), dtype=int)
        with pytest.raises(ValueError, match="1-D array"):
            _stratified_markov_shuffle(trajs, labels_2d, rng)

    def test_misaligned_length_raises(self):
        """Labels shorter than trajectories must raise (row-alignment check)."""
        trajs = make_synthetic_trajectories(n=50, t=10, seed=0)
        rng = np.random.RandomState(0)
        short_labels = np.zeros(30, dtype=int)  # 30 != 50
        with pytest.raises(ValueError, match="does not match"):
            _stratified_markov_shuffle(trajs, short_labels, rng)

    def test_misaligned_too_long_raises(self):
        """Labels longer than trajectories must also raise."""
        trajs = make_synthetic_trajectories(n=50, t=10, seed=0)
        rng = np.random.RandomState(0)
        long_labels = np.zeros(100, dtype=int)  # 100 != 50
        with pytest.raises(ValueError, match="does not match"):
            _stratified_markov_shuffle(trajs, long_labels, rng)


# ── Test 2: regime coverage ───────────────────────────────────────────────────


class TestRegimeCoverage:
    """Surrogates must draw from all regimes, not collapse to fewer."""

    def test_all_7_regimes_used(self):
        """With 7 balanced regimes (≥30 trajectories each), surrogates work."""
        n = 7 * 50  # 50 per regime
        trajs = make_synthetic_trajectories(n=n, t=15, seed=1)
        labels = _make_regime_labels(n, k=7, seed=1)
        assert len(np.unique(labels)) == 7, "Test setup: should have 7 regimes"
        rng = np.random.RandomState(1)
        result = _stratified_markov_shuffle(trajs, labels, rng)
        assert not np.any(np.isnan(result))
        assert result.shape[0] == n

    def test_no_regime_collapse_in_output(self):
        """Result has correct number of rows — no trajectories silently dropped."""
        n = 210  # 30 per regime for 7 regimes
        trajs = make_synthetic_trajectories(n=n, t=12, seed=2)
        labels = _make_regime_labels(n, k=7, seed=2)
        rng = np.random.RandomState(2)
        result = _stratified_markov_shuffle(trajs, labels, rng)
        assert result.shape[0] == n, (
            "Output must have exactly N rows — no regime collapse or trajectory drop"
        )

    def test_single_regime_falls_back_to_global(self):
        """A regime with < min_regime_n trajectories uses the global matrix."""
        # 200 trajectories: 195 in regime 0, 5 in regime 1 (below min_regime_n=30)
        trajs = make_synthetic_trajectories(n=200, t=10, seed=3)
        labels = np.zeros(200, dtype=int)
        labels[:5] = 1  # 5 in regime 1
        rng = np.random.RandomState(3)
        # Should NOT raise — small regime falls back to global matrix
        result = _stratified_markov_shuffle(trajs, labels, rng)
        assert result.shape[0] == 200
        assert not np.any(np.isnan(result))


# ── Test 3: list-style labels are coerced to array ────────────────────────────


class TestLabelCoercion:
    def test_list_labels_accepted(self):
        """Python list of regime labels should be accepted (coerced to array)."""
        n = 60
        trajs = make_synthetic_trajectories(n=n, t=10, seed=4)
        labels_list = [0] * 30 + [1] * 30  # plain Python list
        rng = np.random.RandomState(4)
        result = _stratified_markov_shuffle(trajs, labels_list, rng)
        assert result.shape[0] == n
        assert not np.any(np.isnan(result))
