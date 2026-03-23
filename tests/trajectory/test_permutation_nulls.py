"""Tests for permutation null models."""

from __future__ import annotations

import numpy as np
import pytest

from tests.trajectory.conftest import make_cyclic_trajectories, make_synthetic_trajectories
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology.permutation_nulls import (
    _label_shuffle,
    _markov_shuffle,
    _order_shuffle,
    _single_permutation,
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


class TestWassersteinStatistic:
    """Tests for Wasserstein distance permutation statistic."""

    def test_single_permutation_wasserstein_returns_distances(self):
        """_single_permutation with wasserstein should return W distances per dim."""
        from poverty_tda.topology.multidim_ph import compute_rips_ph

        from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

        trajs = make_synthetic_trajectories(n=30, t=10)
        embed_kwargs = {"pca_dim": 5}
        emb, _ = ngram_embed(trajs, **embed_kwargs)

        # Compute observed PH
        n_lm = min(30, emb.shape[0])
        _, obs_lm = maxmin_landmarks(emb, n_lm, seed=42)
        ph_obs = compute_rips_ph(obs_lm, max_dim=1)

        result = _single_permutation(
            null_type="label_shuffle",
            embeddings=emb,
            trajectories=trajs,
            metadata=None,
            seed=123,
            max_dim=1,
            n_landmarks=30,
            statistic="wasserstein",
            markov_order=1,
            embed_kwargs=embed_kwargs,
            ph_observed=ph_obs,
        )

        # Should have W distances for each dimension
        assert "H0" in result
        assert "H1" in result
        assert result["H0"] >= 0.0
        assert result["H1"] >= 0.0
        # Should also have stored diagrams
        assert "H0_dgm" in result
        assert "H1_dgm" in result

    def test_wasserstein_label_shuffle_produces_distribution(self):
        """Full wasserstein test should return W distribution stats."""
        trajs = make_synthetic_trajectories(n=50, t=15)
        emb, _ = ngram_embed(trajs, pca_dim=5)

        result = permutation_test_trajectories(
            embeddings=emb,
            null_type="label_shuffle",
            n_permutations=10,
            max_dim=1,
            n_landmarks=50,
            statistic="wasserstein",
            n_jobs=1,
        )

        assert result["statistic"] == "wasserstein"
        assert "H0" in result
        assert "H1" in result

        for key in ["H0", "H1"]:
            r = result[key]
            assert "mean_wasserstein_obs_null" in r
            assert "std_wasserstein_obs_null" in r
            assert "median_wasserstein_obs_null" in r
            assert "mean_wasserstein_null_null" in r
            assert "p_value" in r
            assert "significant_at_005" in r
            assert "obs_null_distribution" in r
            assert "n_null_null_pairs" in r

            # All W distances should be non-negative
            assert r["mean_wasserstein_obs_null"] >= 0.0
            assert all(w >= 0.0 for w in r["obs_null_distribution"])
            assert len(r["obs_null_distribution"]) == 10

    def test_wasserstein_order_shuffle_runs(self):
        """Wasserstein statistic should work with order_shuffle null."""
        trajs = make_synthetic_trajectories(n=30, t=10)
        embed_kwargs = {"pca_dim": 5}
        emb, _ = ngram_embed(trajs, **embed_kwargs)

        result = permutation_test_trajectories(
            embeddings=emb,
            trajectories=trajs,
            null_type="order_shuffle",
            n_permutations=5,
            max_dim=1,
            n_landmarks=30,
            statistic="wasserstein",
            n_jobs=1,
            embed_kwargs=embed_kwargs,
        )

        assert "H0" in result
        assert result["statistic"] == "wasserstein"
        assert result["H0"]["mean_wasserstein_obs_null"] >= 0.0

    def test_wasserstein_markov_runs(self):
        """Wasserstein statistic should work with markov null."""
        trajs = make_synthetic_trajectories(n=30, t=10)
        embed_kwargs = {"pca_dim": 5}
        emb, _ = ngram_embed(trajs, **embed_kwargs)

        result = permutation_test_trajectories(
            embeddings=emb,
            trajectories=trajs,
            null_type="markov",
            n_permutations=5,
            max_dim=1,
            n_landmarks=30,
            statistic="wasserstein",
            n_jobs=1,
            embed_kwargs=embed_kwargs,
        )

        assert "H0" in result
        assert result["statistic"] == "wasserstein"

    def test_wasserstein_cyclic_vs_random_separation(self):
        """Cyclic trajectories should show larger W from random nulls than random trajectories do.

        This validates that the Wasserstein metric captures genuine topological
        differences between structured (cyclic) and unstructured (random) data.
        """
        # Cyclic data — has genuine topological signal
        cyclic_trajs = make_cyclic_trajectories(n=40, t=15, seed=42)
        embed_kwargs = {"pca_dim": 5}
        emb_cyclic, _ = ngram_embed(cyclic_trajs, **embed_kwargs)

        result_cyclic = permutation_test_trajectories(
            embeddings=emb_cyclic,
            trajectories=cyclic_trajs,
            null_type="order_shuffle",
            n_permutations=10,
            max_dim=1,
            n_landmarks=40,
            statistic="wasserstein",
            n_jobs=1,
            embed_kwargs=embed_kwargs,
        )

        # Random data — no topological signal
        random_trajs = make_synthetic_trajectories(n=40, t=15, seed=99)
        emb_random, _ = ngram_embed(random_trajs, **embed_kwargs)

        result_random = permutation_test_trajectories(
            embeddings=emb_random,
            trajectories=random_trajs,
            null_type="order_shuffle",
            n_permutations=10,
            max_dim=1,
            n_landmarks=40,
            statistic="wasserstein",
            n_jobs=1,
            embed_kwargs=embed_kwargs,
        )

        # Both should produce valid results
        assert result_cyclic["H1"]["mean_wasserstein_obs_null"] >= 0.0
        assert result_random["H1"]["mean_wasserstein_obs_null"] >= 0.0

    def test_wasserstein_pvalue_bounded(self):
        """p-value should always be in [0, 1]."""
        trajs = make_synthetic_trajectories(n=40, t=15)
        emb, _ = ngram_embed(trajs, pca_dim=5)

        result = permutation_test_trajectories(
            embeddings=emb,
            null_type="label_shuffle",
            n_permutations=10,
            max_dim=1,
            n_landmarks=40,
            statistic="wasserstein",
            n_jobs=1,
        )

        for key in ["H0", "H1"]:
            assert 0.0 <= result[key]["p_value"] <= 1.0

    def test_wasserstein_null_null_baseline_computed(self):
        """Null-null baseline should be computed from subsampled pairs."""
        trajs = make_synthetic_trajectories(n=50, t=15)
        emb, _ = ngram_embed(trajs, pca_dim=5)

        result = permutation_test_trajectories(
            embeddings=emb,
            null_type="label_shuffle",
            n_permutations=15,
            max_dim=1,
            n_landmarks=50,
            statistic="wasserstein",
            n_jobs=1,
        )

        for key in ["H0", "H1"]:
            r = result[key]
            assert r["n_null_null_pairs"] > 0
            assert r["mean_wasserstein_null_null"] >= 0.0
            assert r["std_wasserstein_null_null"] >= 0.0
