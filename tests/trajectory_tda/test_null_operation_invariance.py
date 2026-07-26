"""Binding test for null operations that must perturb the PH input."""

from __future__ import annotations

import numpy as np
import pytest

from poverty_tda.topology.multidim_ph import compute_rips_ph
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology.permutation_nulls import _order_shuffle
from trajectory_tda.topology.vectorisation import wasserstein_distance


def test_null_shuffle_perturbs_persistence_diagram() -> None:
    """Pre-embedding order shuffling changes PH; row shuffling remains a no-op."""
    trajectories = [
        ["EL", "EM", "EH", "EL", "EM", "EH"],
        ["UL", "UM", "UH", "UL", "UM", "UH"],
        ["IL", "IM", "IH", "IL", "IM", "IH"],
        ["EL", "UL", "IL", "EM", "UM", "IM"],
        ["EH", "UH", "IH", "EM", "UM", "IM"],
        ["EL", "UM", "IH", "EL", "UM", "IH"],
    ]
    embed_kwargs = {"pca_dim": 3, "include_bigrams": True}
    observed, embedding_info = ngram_embed(trajectories, **embed_kwargs)

    reembedded_null = _order_shuffle(
        trajectories,
        np.random.RandomState(42),
        embed_kwargs,
        embedding_info["fitted_models"],
    )
    row_shuffled_null = observed[np.random.RandomState(42).permutation(len(observed))]

    observed_ph = compute_rips_ph(observed, max_dim=1)
    reembedded_ph = compute_rips_ph(reembedded_null, max_dim=1)
    row_shuffled_ph = compute_rips_ph(row_shuffled_null, max_dim=1)

    reembedded_w2 = wasserstein_distance(observed_ph, reembedded_ph, dim=0)
    row_shuffled_w2 = wasserstein_distance(observed_ph, row_shuffled_ph, dim=0)

    assert reembedded_w2 > 0.0
    assert row_shuffled_w2 == pytest.approx(0.0, abs=1e-12)
