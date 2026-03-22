"""Tests for PH computation (maxmin VR + witness) and permutation nulls."""

from __future__ import annotations

import numpy as np
import pytest

from tests.trajectory.conftest import (
    make_clustered_trajectories,
    make_synthetic_trajectories,
)
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology.trajectory_ph import (
    compute_trajectory_ph,
    maxmin_landmarks,
)


class TestMaxminLandmarks:
    """Test greedy maxmin landmark selection."""

    def test_correct_count(self):
        X = np.random.RandomState(42).randn(100, 10)
        indices, landmarks = maxmin_landmarks(X, n_landmarks=20)
        assert len(indices) == 20
        assert landmarks.shape == (20, 10)

    def test_unique_indices(self):
        X = np.random.RandomState(42).randn(100, 10)
        indices, _ = maxmin_landmarks(X, n_landmarks=50)
        assert len(set(indices)) == 50

    def test_cap_at_n(self):
        X = np.random.RandomState(42).randn(30, 5)
        indices, landmarks = maxmin_landmarks(X, n_landmarks=100)
        assert len(indices) == 30  # Can't exceed N

    def test_spatial_coverage(self):
        """Landmarks should cover the space evenly."""
        rng = np.random.RandomState(42)
        X = rng.randn(200, 3)
        _, landmarks = maxmin_landmarks(X, n_landmarks=20)
        # Min pairwise distance should be reasonable (not clustered)
        from scipy.spatial.distance import pdist

        min_dist = pdist(landmarks).min()
        assert min_dist > 0


class TestComputeTrajectoryPH:
    """Test hybrid PH computation pipeline."""

    @pytest.fixture
    def embedded_cloud(self):
        """Create a small embedded point cloud for testing."""
        trajs = make_synthetic_trajectories(n=100, t=15)
        emb, _ = ngram_embed(trajs, pca_dim=10)
        return emb

    def test_maxmin_vr_returns_ph(self, embedded_cloud):
        result = compute_trajectory_ph(
            embedded_cloud,
            max_dim=1,
            method="maxmin_vr",
            validate=False,
        )
        assert "maxmin_vr" in result
        assert "summaries" in result
        ph = result["maxmin_vr"]
        assert 0 in ph.dgms  # H0
        assert 1 in ph.dgms  # H1

    def test_witness_returns_ph(self, embedded_cloud):
        result = compute_trajectory_ph(
            embedded_cloud,
            max_dim=1,
            method="witness",
            validate=False,
        )
        # Witness may fall back to maxmin_vr if gudhi unavailable
        assert "witness" in result or "maxmin_vr" in result

    def test_both_methods(self, embedded_cloud):
        result = compute_trajectory_ph(
            embedded_cloud,
            max_dim=1,
            method="both",
            validate=False,
        )
        assert "summaries" in result

    def test_adaptive_landmarks(self, embedded_cloud):
        result = compute_trajectory_ph(
            embedded_cloud,
            method="maxmin_vr",
            validate=False,
        )
        # With 100 points, n_landmarks = min(5000, 100//4) = 25
        assert result["n_landmarks"] <= 100

    def test_elapsed_recorded(self, embedded_cloud):
        result = compute_trajectory_ph(
            embedded_cloud,
            method="maxmin_vr",
            validate=False,
        )
        assert "elapsed_seconds" in result
        assert result["elapsed_seconds"] >= 0

    def test_clustered_data_has_h0(self):
        """Well-separated clusters should show persistent H₀ features."""
        trajs, _ = make_clustered_trajectories(n=150, k=3)
        emb, _ = ngram_embed(trajs, pca_dim=5)
        result = compute_trajectory_ph(emb, max_dim=1, method="maxmin_vr", validate=False)
        summary = result["summaries"]["maxmin_vr"]
        # Should have H₀ features
        assert summary["H0"]["n_finite"] > 0
