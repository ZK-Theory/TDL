"""Tests for vectorisation, regime discovery, cycle detection, and group comparison."""

from __future__ import annotations

import numpy as np
import pytest

from tests.trajectory.conftest import (
    make_clustered_trajectories,
    make_cyclic_trajectories,
    make_synthetic_trajectories,
)
from trajectory_tda.analysis.regime_discovery import discover_regimes, fit_gmm
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph
from trajectory_tda.topology.vectorisation import (
    persistence_image,
    persistence_landscape,
    vectorise_diagram,
    wasserstein_distance,
)

# ─────────────────────────────────────────────────────────────────────
# Vectorisation tests
# ─────────────────────────────────────────────────────────────────────


class TestPersistenceLandscape:
    """Test persistence landscape computation."""

    def test_empty_diagram(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph = PHResult(dgms={1: np.empty((0, 2))}, n_points=10)
        t_vals, landscapes = persistence_landscape(ph, dim=1)
        assert landscapes.shape[0] == 5  # default k_max
        assert np.all(landscapes == 0)

    def test_single_feature(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph = PHResult(
            dgms={1: np.array([[0.0, 1.0]])},
            n_points=10,
        )
        t_vals, landscapes = persistence_landscape(ph, dim=1, n_points=50)
        assert landscapes.shape == (5, 50)
        # First landscape should have nonzero values
        assert landscapes[0].max() > 0


class TestPersistenceImage:
    """Test persistence image computation."""

    def test_shape(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph = PHResult(
            dgms={1: np.array([[0.0, 1.0], [0.5, 2.0]])},
            n_points=10,
        )
        img = persistence_image(ph, dim=1, resolution=15)
        assert img.shape == (15, 15)
        assert img.sum() > 0

    def test_empty_diagram(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph = PHResult(dgms={1: np.empty((0, 2))}, n_points=10)
        img = persistence_image(ph, dim=1, resolution=10)
        assert img.shape == (10, 10)
        assert img.sum() == 0


class TestWassersteinDistance:
    """Test Wasserstein distance."""

    def test_identical_diagrams(self):
        from poverty_tda.topology.multidim_ph import PHResult

        dgm = np.array([[0.0, 1.0], [0.5, 2.0]])
        ph1 = PHResult(dgms={1: dgm.copy()}, n_points=10)
        ph2 = PHResult(dgms={1: dgm.copy()}, n_points=10)
        dist = wasserstein_distance(ph1, ph2, dim=1)
        assert dist == pytest.approx(0.0, abs=0.01)

    def test_different_diagrams_positive(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph1 = PHResult(dgms={1: np.array([[0.0, 1.0]])}, n_points=10)
        ph2 = PHResult(dgms={1: np.array([[0.0, 5.0]])}, n_points=10)
        dist = wasserstein_distance(ph1, ph2, dim=1)
        assert dist > 0

    def test_empty_vs_nonempty(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph1 = PHResult(dgms={1: np.empty((0, 2))}, n_points=10)
        ph2 = PHResult(dgms={1: np.array([[0.0, 2.0]])}, n_points=10)
        dist = wasserstein_distance(ph1, ph2, dim=1)
        assert dist > 0


class TestVectoriseDiagram:
    """Test convenience vectorisation function."""

    def test_all_methods(self):
        from poverty_tda.topology.multidim_ph import PHResult

        ph = PHResult(
            dgms={1: np.array([[0.0, 1.0], [0.5, 2.0]])},
            n_points=10,
        )
        result = vectorise_diagram(ph, dim=1)
        assert "betti_curve" in result
        assert "landscape" in result
        assert "persistence_image" in result


# ─────────────────────────────────────────────────────────────────────
# Regime discovery tests
# ─────────────────────────────────────────────────────────────────────


class TestFitGMM:
    """Test GMM fitting."""

    def test_finds_clusters(self):
        trajs, labels = make_clustered_trajectories(n=150, k=3)
        emb, _ = ngram_embed(trajs, pca_dim=10)
        gmm, pred_labels, info = fit_gmm(emb)

        assert info["k_optimal"] >= 2
        assert len(pred_labels) == 150

    def test_silhouette_positive(self):
        trajs, _ = make_clustered_trajectories(n=150, k=3)
        emb, _ = ngram_embed(trajs, pca_dim=10)
        _, _, info = fit_gmm(emb)
        assert info["silhouette"] > 0


class TestDiscoverRegimes:
    """Test regime discovery pipeline."""

    def test_basic_run(self):
        trajs, _ = make_clustered_trajectories(n=150, k=3)
        emb, _ = ngram_embed(trajs, pca_dim=10)

        result = discover_regimes(emb, trajs)

        assert "k_optimal" in result
        assert "regime_profiles" in result
        assert result["k_optimal"] >= 2

        # Each profile should have characterisation fields
        for label, profile in result["regime_profiles"].items():
            assert "dominant_state" in profile
            assert "employment_rate" in profile
            assert 0 <= profile["employment_rate"] <= 1


# ─────────────────────────────────────────────────────────────────────
# Cycle detection tests
# ─────────────────────────────────────────────────────────────────────


class TestCycleDetection:
    """Test cycle detection."""

    def test_no_ph_warning(self):
        from trajectory_tda.analysis.cycle_detection import detect_cycles

        result = detect_cycles(
            ph_result={},
            embeddings=np.random.randn(50, 10),
            trajectories=make_synthetic_trajectories(50, 15),
        )
        assert result["n_persistent_loops"] == 0

    def test_with_ph(self):
        from trajectory_tda.analysis.cycle_detection import detect_cycles

        trajs = make_cyclic_trajectories(n=100, t=20)
        emb, _ = ngram_embed(trajs, pca_dim=10)
        ph_result = compute_trajectory_ph(emb, max_dim=1, method="maxmin_vr", validate=False)

        result = detect_cycles(ph_result, emb, trajs)
        assert "n_persistent_loops" in result
        assert "h1_summary" in result


# ─────────────────────────────────────────────────────────────────────
# Group comparison tests
# ─────────────────────────────────────────────────────────────────────


class TestGroupComparison:
    """Test group comparison."""

    def test_two_groups(self):
        from trajectory_tda.analysis.group_comparison import compare_groups

        trajs, labels = make_clustered_trajectories(n=100, k=2)
        emb, _ = ngram_embed(trajs, pca_dim=5)
        group_labels = np.array(labels)

        result = compare_groups(
            emb,
            group_labels,
            n_landmarks=50,
            n_permutations=5,  # Small for speed
        )

        assert result["n_groups"] == 2
        assert len(result["per_group"]) == 2
        assert len(result["pairwise_wasserstein"]) > 0

    def test_wasserstein_positive_for_different_groups(self):
        from trajectory_tda.analysis.group_comparison import compare_groups

        trajs, labels = make_clustered_trajectories(n=100, k=2)
        emb, _ = ngram_embed(trajs, pca_dim=5)

        result = compare_groups(
            emb,
            np.array(labels),
            n_landmarks=50,
            n_permutations=0,  # Skip perm test
        )

        # At least some Wasserstein distance should be > 0
        wass_values = list(result["pairwise_wasserstein"].values())
        assert any(w > 0 for w in wass_values)
