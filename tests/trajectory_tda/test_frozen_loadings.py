# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Unit tests for frozen scaler/PCA loadings in trajectory null embeddings.
"""Frozen-loadings tests for n-gram embedding and Markov-null threading."""

from __future__ import annotations

import numpy as np

from trajectory_tda.embedding import ngram_embed as embed_module
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology import permutation_nulls


STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]


def _trajectories(n: int = 50, length: int = 14) -> list[list[str]]:
    return [[STATES[(i + 2 * j) % len(STATES)] for j in range(length)] for i in range(n)]


def _raw_features(trajectories: list[list[str]]) -> np.ndarray:
    unigrams = np.array([embed_module._compute_unigrams(t) for t in trajectories])
    bigrams = np.array([embed_module._compute_bigrams(t) for t in trajectories])
    return np.hstack([unigrams, bigrams])


def test_default_behaviour_unchanged() -> None:
    trajectories = _trajectories()

    emb1, info1 = ngram_embed(trajectories, random_state=42)
    emb2, info2 = ngram_embed(trajectories, random_state=42)

    np.testing.assert_array_equal(emb1, emb2)
    assert info1["method"] == info2["method"] == "pca"
    assert info1["final_dims"] == info2["final_dims"]


def test_frozen_scaler_pca_transform_only() -> None:
    train = _trajectories(n=60)
    test = _trajectories(n=30)
    _, info = ngram_embed(train, pca_dim=8, random_state=42)
    scaler = info["fitted_models"]["scaler"]
    pca = info["fitted_models"]["reducer"]

    frozen_embedding, frozen_info = ngram_embed(
        test,
        pca_dim=8,
        random_state=42,
        frozen_scaler=scaler,
        frozen_pca=pca,
    )

    expected = pca.transform(scaler.transform(_raw_features(test)))
    np.testing.assert_allclose(frozen_embedding, expected)
    assert frozen_info["fitted_models"]["scaler"] is scaler
    assert frozen_info["fitted_models"]["reducer"] is pca


def test_null_function_uses_frozen_models(monkeypatch) -> None:
    trajectories = _trajectories(n=12, length=10)
    _, info = ngram_embed(trajectories, pca_dim=4, random_state=42)
    frozen_models = info["fitted_models"]
    calls: list[dict] = []

    def fake_ngram_embed(synthetic, **kwargs):
        calls.append(kwargs)
        return np.zeros((len(synthetic), 4)), {"fitted_models": {"scaler": None, "reducer": None}}

    monkeypatch.setattr(permutation_nulls, "ngram_embed", fake_ngram_embed)
    rng = np.random.RandomState(7)

    permutation_nulls._markov_shuffle(trajectories, rng, markov_order=1, embed_kwargs={"pca_dim": 4})
    permutation_nulls._markov_shuffle(
        trajectories,
        rng,
        markov_order=1,
        embed_kwargs={"pca_dim": 4},
        frozen_models=frozen_models,
    )

    assert calls[0].get("frozen_pca") is None
    assert calls[1]["frozen_scaler"] is frozen_models["scaler"]
    assert calls[1]["frozen_pca"] is frozen_models["reducer"]


def test_single_permutation_threads_frozen(monkeypatch) -> None:
    embeddings = np.zeros((6, 3))
    trajectories = _trajectories(n=6, length=8)
    frozen_models = {"scaler": object(), "reducer": object()}
    seen = {}

    def fake_markov_shuffle(trajectories, rng, markov_order=1, embed_kwargs=None, alpha=1.0, frozen_models=None):
        seen["frozen_models"] = frozen_models
        return embeddings

    class FakePH:
        pass

    monkeypatch.setattr(permutation_nulls, "_markov_shuffle", fake_markov_shuffle)
    monkeypatch.setattr(permutation_nulls, "compute_rips_ph", lambda landmarks, max_dim: FakePH())
    monkeypatch.setattr(permutation_nulls, "persistence_summary", lambda ph: {"H0": {"total_persistence": 1.0}})

    result = permutation_nulls._single_permutation(
        "markov",
        embeddings,
        trajectories,
        None,
        43,
        0,
        6,
        "total_persistence",
        1,
        {"pca_dim": 3},
        frozen_models=frozen_models,
    )

    assert seen["frozen_models"] is frozen_models
    assert result["H0"] == 1.0
