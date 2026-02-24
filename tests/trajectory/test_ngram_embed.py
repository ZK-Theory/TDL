"""Tests for n-gram embedding: dimensions, normalisation, known vectors."""

from __future__ import annotations

import numpy as np
import pytest

from tests.trajectory.conftest import (
    STATES,
    make_clustered_trajectories,
    make_synthetic_trajectories,
)
from trajectory_tda.embedding.ngram_embed import (
    N_STATES,
    STATE_TO_IDX,
    _compute_bigrams,
    _compute_unigrams,
    ngram_embed,
)


class TestUnigrams:
    """Test unigram frequency computation."""

    def test_uniform_trajectory(self):
        """All same state → one dimension = 1.0, rest = 0."""
        traj = ["EH"] * 20
        vec = _compute_unigrams(traj)
        assert vec[STATE_TO_IDX["EH"]] == 1.0
        assert vec.sum() == pytest.approx(1.0)

    def test_two_states(self):
        traj = ["EH"] * 10 + ["UL"] * 10
        vec = _compute_unigrams(traj)
        assert vec[STATE_TO_IDX["EH"]] == pytest.approx(0.5)
        assert vec[STATE_TO_IDX["UL"]] == pytest.approx(0.5)

    def test_all_states(self):
        traj = STATES * 2  # Each state appears twice
        vec = _compute_unigrams(traj)
        for s in STATES:
            assert vec[STATE_TO_IDX[s]] == pytest.approx(1 / N_STATES, abs=0.01)

    def test_dimension(self):
        vec = _compute_unigrams(["EH", "UL", "IM"])
        assert vec.shape == (N_STATES,)


class TestBigrams:
    """Test bigram (transition frequency) computation."""

    def test_single_transition(self):
        traj = ["EH", "EM"]
        vec = _compute_bigrams(traj)
        idx = STATE_TO_IDX["EH"] * N_STATES + STATE_TO_IDX["EM"]
        assert vec[idx] == pytest.approx(1.0)

    def test_self_loop(self):
        traj = ["EH", "EH", "EH"]
        vec = _compute_bigrams(traj)
        idx = STATE_TO_IDX["EH"] * N_STATES + STATE_TO_IDX["EH"]
        assert vec[idx] == pytest.approx(1.0)

    def test_dimension(self):
        vec = _compute_bigrams(["EH", "UL"])
        assert vec.shape == (N_STATES * N_STATES,)

    def test_normalisation(self):
        traj = ["EH", "EM", "UL", "IL", "EH"]
        vec = _compute_bigrams(traj)
        assert vec.sum() == pytest.approx(1.0, abs=0.01)


class TestNgramEmbed:
    """Test full embedding pipeline."""

    def test_unigram_only_shape(self):
        trajs = make_synthetic_trajectories(n=50, t=15)
        emb, info = ngram_embed(trajs, include_bigrams=False, pca_dim=None)
        assert emb.shape == (50, 9)
        assert info["n_unigram_dims"] == 9
        assert info["n_bigram_dims"] == 0

    def test_bigram_shape(self):
        trajs = make_synthetic_trajectories(n=50, t=15)
        emb, info = ngram_embed(trajs, include_bigrams=True, pca_dim=None)
        assert emb.shape == (50, 90)
        assert info["raw_dims"] == 90

    def test_pca_reduction(self):
        trajs = make_synthetic_trajectories(n=50, t=15)
        emb, info = ngram_embed(trajs, pca_dim=10)
        assert emb.shape == (50, 10)
        assert info["method"] == "pca"
        assert info["explained_variance"] is not None
        assert 0 < info["explained_variance"] <= 1

    def test_tfidf(self):
        trajs = make_synthetic_trajectories(n=50, t=15)
        # Default standardise=True will now use with_std=False when tfidf=True
        emb_raw, _ = ngram_embed(trajs, tfidf=False, pca_dim=None)
        emb_tfidf, info = ngram_embed(trajs, tfidf=True, pca_dim=None)
        assert info["tfidf"] is True
        # TF-IDF should change the embeddings (not cancelled by standardisation)
        assert not np.allclose(emb_raw, emb_tfidf)

    def test_state_to_idx_exported(self):
        trajs = make_synthetic_trajectories(n=10, t=5)
        _, info = ngram_embed(trajs, pca_dim=None)
        assert "state_to_idx" in info
        assert len(info["state_to_idx"]) == 9

    def test_clustered_trajectories_separable(self):
        """Clustered trajectories should have clearly different embeddings."""
        trajs, labels = make_clustered_trajectories(n=150, k=3)
        emb, _ = ngram_embed(trajs, pca_dim=None)

        # Compute between-cluster vs within-cluster distances
        from sklearn.metrics import silhouette_score

        sil = silhouette_score(emb, labels)
        # Well-separated regimes should have positive silhouette
        assert sil > 0.0

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="No trajectories"):
            ngram_embed([], pca_dim=None)
