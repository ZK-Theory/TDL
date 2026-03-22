"""Tests for permutation null models."""

from __future__ import annotations

import numpy as np
import pytest

from tests.trajectory.conftest import make_synthetic_trajectories
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology.permutation_nulls import (
    _label_shuffle,
    _markov_shuffle,
    _order_shuffle,
    permutation_test_trajectories,
)


class TestLabelShuffle:
    """Test label shuffle null."""

    def test_preserves_shape(self):
        emb = np.random.RandomState(42).randn(50, 10)
        rng = np.random.RandomState(0)
        shuffled = _label_shuffle(emb, rng)
        assert shuffled.shape == emb.shape

    def test_preserves_rows(self):
        """Should contain same rows, just reordered."""
        emb = np.random.RandomState(42).randn(50, 10)
        rng = np.random.RandomState(0)
        shuffled = _label_shuffle(emb, rng)
        # Sort and compare
        assert np.allclose(np.sort(emb, axis=0), np.sort(shuffled, axis=0))


class TestOrderShuffle:
    """Test order-preserving shuffle."""

    def test_preserves_unigrams(self):
        """Order shuffle should preserve state frequencies (unigrams).

        Shuffling state order within each trajectory doesn't change
        which states appear — only their order. So unigram vectors
        should be identical.
        """
        trajs = make_synthetic_trajectories(n=20, t=15)
        rng = np.random.RandomState(42)

        embed_kwargs = {
            "include_bigrams": False,
            "pca_dim": None,
            "standardize": False,
        }
        # Original unigram embeddings (9D, no bigrams, no standardization)
        emb_orig, _ = ngram_embed(trajs, **embed_kwargs)
        # Shuffled: each trajectory's states permuted internally
        emb_shuffled = _order_shuffle(trajs, rng, embed_kwargs)

        # Each row should have same unigram frequencies as original
        # (same set of rows, order preserved since trajectories stay matched)
        np.testing.assert_allclose(emb_orig, emb_shuffled, atol=1e-10)


class TestMarkovShuffle:
    """Test Markov chain null model."""

    def test_preserves_trajectory_lengths(self):
        trajs = make_synthetic_trajectories(n=20, t=15)
        rng = np.random.RandomState(42)
        embed_kwargs = {"pca_dim": None, "standardize": False}
        emb = _markov_shuffle(trajs, rng, markov_order=1, embed_kwargs=embed_kwargs)
        assert emb.shape[0] == 20  # Same number of trajectories

    def test_markov_order_2(self):
        trajs = make_synthetic_trajectories(n=20, t=15)
        rng = np.random.RandomState(42)
        embed_kwargs = {"pca_dim": None, "standardize": False}
        emb = _markov_shuffle(trajs, rng, markov_order=2, embed_kwargs=embed_kwargs)
        assert emb.shape[0] == 20

    def test_invalid_order_raises(self):
        trajs = make_synthetic_trajectories(n=5, t=5)
        rng = np.random.RandomState(42)
        with pytest.raises(ValueError, match="Unsupported Markov order"):
            _markov_shuffle(trajs, rng, markov_order=3)


class TestPermutationTestTrajectories:
    """Integration test for full permutation test."""

    def test_label_shuffle_produces_pvalue(self):
        trajs = make_synthetic_trajectories(n=50, t=15)
        emb, _ = ngram_embed(trajs, pca_dim=5)

        result = permutation_test_trajectories(
            embeddings=emb,
            null_type="label_shuffle",
            n_permutations=10,  # Small for speed
            max_dim=1,
            n_landmarks=50,
            n_jobs=1,
        )

        assert "H0" in result
        assert "H1" in result
        assert 0 <= result["H0"]["p_value"] <= 1
        assert 0 <= result["H1"]["p_value"] <= 1

    def test_order_shuffle_requires_trajectories(self):
        emb = np.random.RandomState(42).randn(50, 10)
        with pytest.raises(ValueError, match="requires trajectories"):
            permutation_test_trajectories(
                embeddings=emb,
                null_type="order_shuffle",
                n_permutations=5,
                n_jobs=1,
            )

    def test_markov_requires_trajectories(self):
        emb = np.random.RandomState(42).randn(50, 10)
        with pytest.raises(ValueError, match="requires trajectories"):
            permutation_test_trajectories(
                embeddings=emb,
                null_type="markov",
                n_permutations=5,
                n_jobs=1,
            )

    def test_order_shuffle_runs(self):
        trajs = make_synthetic_trajectories(n=30, t=10)
        embed_kwargs = {"pca_dim": 5}
        emb, _ = ngram_embed(trajs, **embed_kwargs)

        result = permutation_test_trajectories(
            embeddings=emb,
            trajectories=trajs,
            null_type="order_shuffle",
            n_permutations=5,
            n_landmarks=30,
            n_jobs=1,
            embed_kwargs=embed_kwargs,
        )
        assert "H0" in result
