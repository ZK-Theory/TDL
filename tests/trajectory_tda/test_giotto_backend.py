# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Verify the giotto-tda Rips-PH backend (poverty_tda.topology.
#   giotto_backend) is numerically consistent with ripser and that
#   run_headline_from_embeddings' rips_backend="giotto" path runs correctly
#   end-to-end. Requires .venv-giotto312 (uv venv --python 3.12
#   .venv-giotto312 && uv pip install --python
#   .venv-giotto312/Scripts/python.exe giotto-tda) — skipped if absent.
"""Tests for the giotto-tda Rips-PH backend bridge."""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pytest

from poverty_tda.topology.multidim_ph import PHResult, compute_rips_ph

_GIOTTO_VENV = Path.cwd() / ".venv-giotto312" / "Scripts" / "python.exe"
requires_giotto_venv = pytest.mark.skipif(
    not _GIOTTO_VENV.exists(),
    reason=(
        "giotto-tda venv not found; create with "
        "'uv venv --python 3.12 .venv-giotto312 && "
        "uv pip install --python .venv-giotto312/Scripts/python.exe giotto-tda'"
    ),
)


def _finite(dgm: np.ndarray) -> np.ndarray:
    if len(dgm) == 0:
        return np.empty((0, 2))
    return dgm[np.isfinite(dgm[:, 1])]


@pytest.mark.integration
@requires_giotto_venv
def test_giotto_matches_ripser_on_finite_pairs() -> None:
    """Finite persistence pairs must match ripser bit-for-bit (2026-07-01
    verification: confirmed on real USoc/BHPS production data at L=5000;
    this test re-checks the same property at a fast, synthetic scale so it
    can run in CI)."""
    from poverty_tda.topology.giotto_backend import GiottoPool, compute_rips_ph_giotto

    rng = np.random.RandomState(7)
    X = rng.standard_normal((300, 10)).astype(np.float64)

    ph_ripser = compute_rips_ph(X, max_dim=1, do_cocycles=False)

    pool = GiottoPool(n_workers=1, worktree_root=Path.cwd())
    try:
        ph_giotto = compute_rips_ph_giotto(X, pool, max_dim=1, thresh=ph_ripser.threshold_value)
    finally:
        pool.close()

    for dim in (0, 1):
        r = _finite(ph_ripser.dgms[dim])
        g = _finite(ph_giotto.dgms[dim])
        assert r.shape[0] == g.shape[0], f"H{dim} finite count mismatch: ripser={r.shape[0]} giotto={g.shape[0]}"
        r_sorted = r[np.lexsort((r[:, 1], r[:, 0]))]
        g_sorted = g[np.lexsort((g[:, 1], g[:, 0]))]
        assert np.allclose(r_sorted, g_sorted, atol=1e-6), f"H{dim} finite pairs diverge beyond tolerance"


@pytest.mark.integration
@requires_giotto_venv
def test_run_headline_from_embeddings_giotto_backend_runs_end_to_end() -> None:
    """rips_backend="giotto" must run through the full permutation loop
    (pool lifecycle, ThreadPoolExecutor dispatch, ph_obs + null diagrams
    all on giotto) without error, at a tiny scale."""
    from trajectory_tda.embedding.ngram_embed import STATES, ngram_embed
    from trajectory_tda.scripts.stage1._battery_core import (
        run_headline_from_embeddings,
        worktree_root,
    )

    rng = np.random.RandomState(11)
    trajectories = [[rng.choice(STATES) for _ in range(6)] for _ in range(60)]
    embed_kwargs = {"pca_dim": 5}
    embeddings, _ = ngram_embed(trajectories, **embed_kwargs)

    # Unique phase_tag per run: on branches with the perm-cache-recovery
    # feature, a stale cache from an earlier run of this test would
    # otherwise trigger the (correct, backend-agnostic) cache-recovery
    # path, which reconstructs ph_obs without ph_method set to
    # "giotto-tda" — a false failure, not a real backend-routing bug.
    phase_tag = f"test_giotto_tiny_{uuid.uuid4().hex[:8]}"
    partial_dir = worktree_root() / "results/trajectory_tda_integration/stage1/.partial"
    try:
        result, null_results, ph_obs = run_headline_from_embeddings(
            embeddings=embeddings,
            trajectories=trajectories,
            embed_kwargs=embed_kwargs,
            n_permutations=4,
            n_landmarks=40,
            k_max=3,
            n_points=20,
            seed=42,
            label="test/giotto/tiny",
            phase_tag=phase_tag,
            n_jobs=2,
            rips_backend="giotto",
        )

        assert len(null_results) == 4
        assert isinstance(ph_obs, PHResult)
        assert ph_obs.ph_method == "giotto-tda"
        assert "h0" in result and "h1" in result
        assert "w2_pvalue" in result["h0"]
    finally:
        for f in partial_dir.glob(f"{phase_tag}*"):
            f.unlink(missing_ok=True)
