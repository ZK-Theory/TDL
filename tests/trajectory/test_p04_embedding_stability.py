"""Tests that the P01 embedding pipeline is stable for P04 consumption.

P04 (multi-parameter PH) depends on:
1. Deterministic embedding: same trajectories → same point cloud
2. Cached checkpoint consistency: on-disk .npy matches re-computation
3. Fitted PCA transform: landmarks subset through saved PCA matches row-slice
4. Income alignment: income bands can be joined to embedding rows by pidp

These tests run on synthetic data (no UKDS access required) plus checkpoint
validation when the integration results directory exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.trajectory.conftest import (
    make_clustered_trajectories,
    make_synthetic_trajectories,
)
from trajectory_tda.embedding.ngram_embed import (
    STATE_TO_IDX,
    ngram_embed,
)

# Path to cached P01 results (may not exist in CI)
CHECKPOINT_DIR = (
    Path(__file__).parent.parent.parent / "results" / "trajectory_tda_integration"
)


# ──────────────────────────────────────────────────────────────────────
# 1. Determinism: same input → same output
# ──────────────────────────────────────────────────────────────────────


class TestEmbeddingDeterminism:
    """Verify ngram_embed is fully deterministic across calls."""

    def test_pca_determinism(self):
        """Two calls with identical data and seed produce identical output."""
        trajs = make_synthetic_trajectories(n=200, t=15, seed=99)
        emb1, info1 = ngram_embed(trajs, pca_dim=20, random_state=42)
        emb2, info2 = ngram_embed(trajs, pca_dim=20, random_state=42)
        np.testing.assert_array_equal(emb1, emb2)
        assert info1["explained_variance"] == info2["explained_variance"]

    def test_raw_determinism(self):
        """Raw embedding (no reduction) is deterministic."""
        trajs = make_synthetic_trajectories(n=100, t=15, seed=99)
        emb1, _ = ngram_embed(trajs, pca_dim=None, standardize=True)
        emb2, _ = ngram_embed(trajs, pca_dim=None, standardize=True)
        np.testing.assert_array_equal(emb1, emb2)

    def test_pca_seed_invariant_for_full_svd(self):
        """sklearn PCA uses full SVD for small dims — result is seed-independent.

        This is a *positive* finding for P04: the embedding is fully
        deterministic regardless of random_state when n_components < min(n, d)
        and the full LAPACK solver is used.
        """
        trajs = make_synthetic_trajectories(n=200, t=15, seed=99)
        emb1, _ = ngram_embed(trajs, pca_dim=10, random_state=42)
        emb2, _ = ngram_embed(trajs, pca_dim=10, random_state=7)
        np.testing.assert_allclose(emb1, emb2, atol=1e-12)

    def test_state_to_idx_stable(self):
        """STATE_TO_IDX is consistent across calls and matches canonical order."""
        trajs = make_synthetic_trajectories(n=10, t=5)
        _, info = ngram_embed(trajs, pca_dim=None)
        assert info["state_to_idx"] == STATE_TO_IDX
        # Canonical order
        expected = {
            "EL": 0,
            "EM": 1,
            "EH": 2,
            "UL": 3,
            "UM": 4,
            "UH": 5,
            "IL": 6,
            "IM": 7,
            "IH": 8,
        }
        assert info["state_to_idx"] == expected


# ──────────────────────────────────────────────────────────────────────
# 2. Fitted model reuse: PCA transform on subsets
# ──────────────────────────────────────────────────────────────────────


class TestFittedPCAReuse:
    """Verify that the fitted PCA from ngram_embed can transform subsets."""

    def test_transform_subset_matches_slice(self):
        """Transforming a subset via fitted PCA matches the corresponding rows."""
        trajs = make_clustered_trajectories(n=300, k=3, t=15)[0]
        emb_full, info = ngram_embed(trajs, pca_dim=20, random_state=42)

        scaler = info["fitted_models"]["scaler"]
        reducer = info["fitted_models"]["reducer"]

        # Re-embed a subset of raw trajectories through the fitted pipeline
        subset_idx = [0, 50, 100, 150, 200, 250]
        subset_trajs = [trajs[i] for i in subset_idx]
        emb_subset_raw, _ = ngram_embed(subset_trajs, pca_dim=None, standardize=False)

        # Apply fitted scaler + PCA
        scaled = scaler.transform(emb_subset_raw)
        emb_subset_transformed = reducer.transform(scaled)

        # Should match the corresponding rows from the full embedding
        emb_subset_expected = emb_full[subset_idx]
        np.testing.assert_allclose(
            emb_subset_transformed, emb_subset_expected, atol=1e-10
        )

    def test_fitted_models_present(self):
        """Info dict contains fitted scaler and reducer."""
        trajs = make_synthetic_trajectories(n=50, t=10)
        _, info = ngram_embed(trajs, pca_dim=10)
        assert "fitted_models" in info
        assert info["fitted_models"]["scaler"] is not None
        assert info["fitted_models"]["reducer"] is not None


# ──────────────────────────────────────────────────────────────────────
# 3. Checkpoint consistency (integration test — requires P01 results)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCheckpointConsistency:
    """Validate cached P01 embeddings match expected properties."""

    @pytest.fixture(autouse=True)
    def _check_checkpoint(self):
        if not (CHECKPOINT_DIR / "embeddings.npy").exists():
            pytest.skip("P01 checkpoint not available")

    def test_embedding_shape(self):
        """Cached embedding has expected shape (27280, 20)."""
        emb = np.load(CHECKPOINT_DIR / "embeddings.npy")
        assert emb.shape == (27280, 20)

    def test_embedding_finite(self):
        """No NaN or Inf values in cached embedding."""
        emb = np.load(CHECKPOINT_DIR / "embeddings.npy")
        assert np.all(np.isfinite(emb))

    def test_metadata_consistent(self):
        """Metadata JSON matches embedding shape and configuration."""
        emb = np.load(CHECKPOINT_DIR / "embeddings.npy")
        with open(CHECKPOINT_DIR / "02_embedding.json") as f:
            meta = json.load(f)
        assert meta["shape"] == list(emb.shape)
        assert meta["info"]["method"] == "pca"
        assert meta["info"]["final_dims"] == 20
        assert meta["info"]["raw_dims"] == 90
        assert meta["info"]["n_trajectories"] == 27280

    def test_pca_explained_variance_reasonable(self):
        """PCA explained variance is in a sensible range."""
        with open(CHECKPOINT_DIR / "02_embedding.json") as f:
            meta = json.load(f)
        ev = meta["info"]["explained_variance"]
        # 20 PCs from 90D; expect 30-70% explained variance
        assert 0.3 < ev < 0.7, f"Explained variance {ev} outside expected range"

    def test_trajectory_count_matches_metadata(self):
        """Trajectory metadata has the same number of individuals as embedding."""
        emb = np.load(CHECKPOINT_DIR / "embeddings.npy")
        with open(CHECKPOINT_DIR / "01_trajectories.json") as f:
            traj_meta = json.load(f)

        # Metadata may store 'n' directly, or we count from pidp column
        if "n" in traj_meta:
            n_meta = traj_meta["n"]
        else:
            # Column-oriented dict: metadata["pidp"] is {str_idx: pidp_value}
            n_meta = len(traj_meta.get("metadata", {}).get("pidp", {}))

        assert n_meta == emb.shape[0], (
            f"Metadata has {n_meta} individuals but embedding has {emb.shape[0]} rows"
        )

    def test_fitted_pca_loadable(self):
        """Saved PCA joblib can be loaded and has correct shape."""
        import joblib

        pca = joblib.load(CHECKPOINT_DIR / "02_pca.joblib")
        assert hasattr(pca, "components_")
        assert pca.components_.shape == (20, 90)

    def test_fitted_scaler_loadable(self):
        """Saved scaler joblib can be loaded."""
        import joblib

        scaler = joblib.load(CHECKPOINT_DIR / "02_scaler.joblib")
        assert hasattr(scaler, "mean_")
        assert scaler.mean_.shape == (90,)


# ──────────────────────────────────────────────────────────────────────
# 4. Income alignment readiness
# ──────────────────────────────────────────────────────────────────────


class TestIncomeAlignmentReadiness:
    """Verify embedding pipeline produces data P04 can join with income."""

    def test_synthetic_trajectories_have_income_states(self):
        """Synthetic trajectories include income band in state labels."""
        trajs = make_clustered_trajectories(n=100, k=3)[0]
        for traj in trajs:
            for state in traj:
                # Every state should end with L, M, or H (income band)
                assert state[-1] in ("L", "M", "H"), (
                    f"State {state} lacks income band suffix"
                )

    def test_income_extractable_from_state_label(self):
        """Income band can be extracted from state labels for per-person stats."""
        trajs = make_clustered_trajectories(n=100, k=3)[0]
        income_map = {"L": 0, "M": 1, "H": 2}

        for traj in trajs:
            bands = [income_map[s[-1]] for s in traj]
            mean_band = np.mean(bands)
            # Mean should be between 0 and 2
            assert 0 <= mean_band <= 2

    def test_mean_income_band_distinguishes_regimes(self):
        """Mean income band should distinguish clustered regime trajectories."""
        trajs, labels = make_clustered_trajectories(n=300, k=3, t=20)
        income_map = {"L": 0, "M": 1, "H": 2}

        regime_means = {}
        for regime in range(3):
            regime_trajs = [trajs[i] for i, l in enumerate(labels) if l == regime]
            means = [np.mean([income_map[s[-1]] for s in t]) for t in regime_trajs]
            regime_means[regime] = np.mean(means)

        # Regime 0 (EH-dominant) should have highest mean income band
        # Regime 2 (UL/IL-dominant) should have lowest
        assert regime_means[0] > regime_means[2]
