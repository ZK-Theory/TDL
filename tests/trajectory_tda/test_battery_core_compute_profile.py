# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Binding test for WT-5 (amendment B7) — compute_profile adoption into
#   the Stage-1 production battery. Verifies the additive `compute_profile`
#   key appears per (dataset, dim) cell in `run_headline_from_embeddings`'
#   output with all required fields populated, and that every pre-existing
#   h0/h1 key and value is bit-for-bit unchanged relative to the same inputs
#   aggregated without `profile_context`.
"""Deterministic toy-scale test for compute_profile adoption in _battery_core."""

from __future__ import annotations

import uuid

import numpy as np
import pytest
from poverty_tda.topology.multidim_ph import PHResult

from trajectory_tda.embedding.ngram_embed import STATES, ngram_embed
from trajectory_tda.scripts.stage1._battery_core import (
    aggregate_combined,
    run_headline_from_embeddings,
    worktree_root,
)

REQUIRED_PROFILE_FIELDS = (
    "complex_construction_wall_s",
    "ph_wall_s",
    "w2_pair_count",
    "w2_total_wall_s",
    "peak_rss_bytes",
    "simplex_counts",
    "diagram_cardinality",
    "backend",
    "backend_version",
)

SEED = 42
B = 4
L = 40
K_MAX = 3
N_POINTS = 20


@pytest.fixture
def _toy_battery_inputs():
    rng = np.random.RandomState(11)
    trajectories = [[rng.choice(STATES) for _ in range(6)] for _ in range(60)]
    embed_kwargs = {"pca_dim": 5}
    embeddings, _ = ngram_embed(trajectories, **embed_kwargs)
    return embeddings, trajectories, embed_kwargs


def _run_headline(embeddings, trajectories, embed_kwargs, phase_tag: str):
    partial_dir = worktree_root() / "results/trajectory_tda_integration/stage1/.partial"
    try:
        return run_headline_from_embeddings(
            embeddings=embeddings,
            trajectories=trajectories,
            embed_kwargs=embed_kwargs,
            n_permutations=B,
            n_landmarks=L,
            k_max=K_MAX,
            n_points=N_POINTS,
            seed=SEED,
            label="test/compute_profile/tiny",
            phase_tag=phase_tag,
            n_jobs=2,
        )
    finally:
        for f in partial_dir.glob(f"{phase_tag}*"):
            f.unlink(missing_ok=True)


def test_compute_profile_attached_per_cell_with_required_fields(_toy_battery_inputs) -> None:
    """compute_profile appears per (dataset, dim) cell with every required field."""
    embeddings, trajectories, embed_kwargs = _toy_battery_inputs
    phase_tag = f"test_compute_profile_tiny_{uuid.uuid4().hex[:8]}"
    result, null_results, ph_obs = _run_headline(embeddings, trajectories, embed_kwargs, phase_tag)

    assert len(null_results) == B
    assert isinstance(ph_obs, PHResult)
    assert "compute_profile" in result
    profile_block = result["compute_profile"]
    assert set(profile_block.keys()) == {"h0", "h1"}

    for dim_key in ("h0", "h1"):
        profile = profile_block[dim_key]
        for field in REQUIRED_PROFILE_FIELDS:
            assert field in profile, f"{dim_key} compute_profile missing field: {field}"

        assert profile["complex_construction_wall_s"] >= 0.0
        assert profile["ph_wall_s"] >= 0.0
        assert profile["w2_pair_count"] > 0
        assert profile["w2_total_wall_s"] >= 0.0
        assert profile["peak_rss_bytes"] is None or profile["peak_rss_bytes"] > 0
        assert isinstance(profile["simplex_counts"], dict)
        assert isinstance(profile["diagram_cardinality"], dict)
        assert profile["backend"] == "ripser"
        assert isinstance(profile["backend_version"], str) and profile["backend_version"] != ""


def test_compute_profile_is_additive_no_preexisting_key_or_value_change(_toy_battery_inputs) -> None:
    """h0/h1 cells are bit-for-bit identical whether or not profile_context is set."""
    embeddings, trajectories, embed_kwargs = _toy_battery_inputs
    phase_tag = f"test_compute_profile_additive_{uuid.uuid4().hex[:8]}"
    with_profile, null_results, ph_obs = _run_headline(embeddings, trajectories, embed_kwargs, phase_tag)

    without_profile = aggregate_combined(
        null_results,
        ph_obs,
        B,
        max_dim=1,
        k_max=K_MAX,
        n_points=N_POINTS,
        seed=SEED,
        phase_label="test/compute_profile/additive-check",
        n_jobs=1,
    )

    assert "compute_profile" not in without_profile
    assert "compute_profile" in with_profile
    assert set(with_profile.keys()) - {"compute_profile"} == set(without_profile.keys())
    assert with_profile["h0"] == without_profile["h0"]
    assert with_profile["h1"] == without_profile["h1"]
