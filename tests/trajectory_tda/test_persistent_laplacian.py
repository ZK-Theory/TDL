# Research context: TDA-Research/00-Meta/Discovery/c1-persistent-laplacian-gate-check-result-2026-07-03.md
# Purpose: Binding tests for the extracted persistent-Laplacian module — pins the
#   Gate 2 property (ker(L1) == ripser beta_1 bit-for-bit under the float32
#   convention) and cross-validates the PETLS backend against the validated numpy
#   fallback (both must agree; neither is trusted without the other).
"""Tests for trajectory_tda.topology.persistent_laplacian."""

from __future__ import annotations

import os

import numpy as np
import pytest

from trajectory_tda.topology.persistent_laplacian import (
    PETLS_AVAILABLE,
    PETLS_BACKEND_NAME,
    betti_1_at_threshold,
    build_boundary_1,
    build_boundary_2,
    build_complex_at_threshold,
    build_undirected_graph,
    compute_fiedler_curve,
    compute_laplacian_1,
    compute_ph_barcodes,
    eigen_analysis,
)

# Deterministic 5-node substrate (independent of any BHPS data load) used for
# fast unit tests of the boundary/complex machinery.
_SMALL_COUNTS = np.array(
    [
        [0, 5, 0, 5, 0],
        [5, 0, 5, 0, 0],
        [0, 5, 0, 5, 0],
        [5, 0, 5, 0, 5],
        [0, 0, 0, 5, 0],
    ],
    dtype=np.int64,
)


def test_build_undirected_graph_is_float32() -> None:
    D = build_undirected_graph(_SMALL_COUNTS)
    assert D.dtype == np.float32


def test_build_undirected_graph_symmetric_weight_formula() -> None:
    D = build_undirected_graph(_SMALL_COUNTS)
    # weight = 1 / (count_ij + count_ji + 1); counts here are already symmetric
    expected = np.float32(1.0 / (5 + 5 + 1))
    assert D[0, 1] == expected
    assert D[1, 0] == expected


def test_kernel_dim_matches_ripser_betti1_bit_for_bit() -> None:
    """Pins the Gate 2 invariant on a small deterministic substrate.

    Exact (epsilon-free) comparison is valid only because both D and ripser's
    internal representation are float32 — see gate-check note: do not add
    epsilon "for safety".
    """
    D = build_undirected_graph(_SMALL_COUNTS)
    dgms = compute_ph_barcodes(D, max_dim=1)
    thresholds = sorted(
        {float(D[i, j]) for i in range(D.shape[0]) for j in range(i + 1, D.shape[0]) if np.isfinite(D[i, j])}
    )
    for t in thresholds:
        edges, triangles = build_complex_at_threshold(D, t)
        d1 = build_boundary_1(D.shape[0], edges)
        d2 = build_boundary_2(edges, triangles)
        L1 = compute_laplacian_1(d1, d2)
        ker_dim, _ = eigen_analysis(L1)
        beta1 = betti_1_at_threshold(dgms, t)
        assert ker_dim == beta1, f"mismatch at t={t}: ker={ker_dim} beta1={beta1}"


def test_eigen_analysis_empty_matrix() -> None:
    ker_dim, lam1 = eigen_analysis(np.zeros((0, 0)))
    assert ker_dim == 0
    assert lam1 is None


@pytest.mark.skipif(
    os.environ.get("TDL_REQUIRE_PETLS") != "1",
    reason="petls is an optional dependency group; set TDL_REQUIRE_PETLS=1 to pin its availability",
)
def test_petls_is_importable_in_this_environment() -> None:
    """Pin PETLS availability where the environment is supposed to provide it.

    Was an unconditional assertion, pinning the 2026-07-07 fact that PETLS built and
    imported in this repo's .venv. Demoted to opt-in on 2026-07-29 when petls moved to a
    dependency group: petls ships no Windows wheel, so on Windows the default environment
    legitimately lacks it and an unconditional assertion would fail for the expected
    reason rather than a regression.

    The risk that motivated it — a silent fallback to numpy — is guarded independently and
    unconditionally by ``test_forced_petls_backend_raises_rather_than_falling_back``. Set
    ``TDL_REQUIRE_PETLS=1`` (Linux, or a Windows venv seeded per the worktree skill) to
    assert availability rather than merely tolerate it.
    """
    assert PETLS_AVAILABLE is True


def test_forced_petls_backend_raises_rather_than_falling_back() -> None:
    """An explicitly requested backend must never be silently substituted.

    This is the control the availability pin actually existed for, and unlike that pin it
    holds in both environments: where PETLS is present the call must use it, and where it
    is absent the call must fail loudly instead of returning a numpy result under the
    ``petls`` label. A silent substitution swaps the statistic, not the precision.
    """
    D = build_undirected_graph(_SMALL_COUNTS)
    if PETLS_AVAILABLE:
        assert compute_fiedler_curve(D, backend="petls")["backend"] == PETLS_BACKEND_NAME
        return
    with pytest.raises(ImportError, match="backend='petls' requested"):
        compute_fiedler_curve(D, backend="petls")


def test_compute_fiedler_curve_auto_uses_petls_when_available() -> None:
    D = build_undirected_graph(_SMALL_COUNTS)
    result = compute_fiedler_curve(D, backend="auto")
    assert result["backend"] == ("petls" if PETLS_AVAILABLE else "numpy-schur-scratch")


def test_compute_fiedler_curve_numpy_backend_forced() -> None:
    D = build_undirected_graph(_SMALL_COUNTS)
    result = compute_fiedler_curve(D, backend="numpy")
    assert result["backend"] == "numpy-schur-scratch"
    assert len(result["thresholds"]) == len(result["lambda1"])
    assert all(isinstance(v, float) for v in result["lambda1"])


@pytest.mark.skipif(not PETLS_AVAILABLE, reason="petls not importable in this environment")
def test_compute_fiedler_curve_petls_backend_forced() -> None:
    D = build_undirected_graph(_SMALL_COUNTS)
    result = compute_fiedler_curve(D, backend="petls")
    assert result["backend"] == "petls"
    assert len(result["thresholds"]) == len(result["lambda1"])


def test_compute_fiedler_curve_backend_agreement_on_deterministic_substrate() -> None:
    """PETLS and numpy must agree exactly (within numerical tolerance) on lambda1
    and ker_dim at every active threshold — neither backend is trusted alone.
    """
    D = build_undirected_graph(_SMALL_COUNTS)
    numpy_result = compute_fiedler_curve(D, backend="numpy")
    if not PETLS_AVAILABLE:
        pytest.skip("petls not importable in this environment")
    petls_result = compute_fiedler_curve(D, backend="petls")

    assert numpy_result["thresholds"] == petls_result["thresholds"]
    assert numpy_result["ker_dim"] == petls_result["ker_dim"]
    np.testing.assert_allclose(numpy_result["lambda1"], petls_result["lambda1"], atol=1e-4)


def test_compute_fiedler_curve_include_inactive_aligns_to_grid() -> None:
    """include_inactive=True returns a curve aligned 1:1 with the input grid.

    The null-battery use case requires every threshold retained with lambda1=0.0
    at inactive steps, so observed and null curves share a common fixed abscissa
    (distinct distance matrices otherwise yield different active-step counts and
    a length mismatch — the defect this option closes).
    """
    D = build_undirected_graph(_SMALL_COUNTS)
    weights = sorted(
        {float(D[i, j]) for i in range(D.shape[0]) for j in range(i + 1, D.shape[0]) if np.isfinite(D[i, j])}
    )
    # Prepend a threshold below the smallest edge weight: that step has no edges
    # (inactive) and is dropped by the default filter but padded by include_inactive.
    grid = [weights[0] / 2.0] + weights
    filtered = compute_fiedler_curve(D, thresholds=grid, backend="auto")
    full = compute_fiedler_curve(D, thresholds=grid, backend="auto", include_inactive=True)

    assert len(full["thresholds"]) == len(grid)
    assert len(full["lambda1"]) == len(grid)
    assert len(full["ker_dim"]) == len(grid)
    assert full["n_active_steps"] == len(grid)
    # The sub-minimum threshold has no edges -> lambda1 padded to 0.0.
    assert full["thresholds"][0] == grid[0]
    assert full["lambda1"][0] == 0.0
    # The default filter drops the inactive leading step.
    assert len(filtered["thresholds"]) < len(grid)
    # On the shared active thresholds the two runs agree exactly.
    for t, lam in zip(filtered["thresholds"], filtered["lambda1"]):
        idx = full["thresholds"].index(t)
        assert full["lambda1"][idx] == pytest.approx(lam, abs=1e-9)


def test_compute_fiedler_curve_backend_agreement_on_real_bhps_substrate() -> None:
    """Re-runs the cross-backend agreement check on the real 9-node BHPS
    transition graph (35 thresholds) — the exact substrate the gate check and
    the dispatch pre-registration specify. Skips if the frozen sequences file
    is not present at PROJ_ROOT (per the two-path rule; not regenerated here).
    """
    import json
    from pathlib import Path

    seq_path = Path(r"C:\Users\steph\TDL\results\trajectory_tda_bhps\01_trajectories_sequences.json")
    if not seq_path.exists():
        pytest.skip(f"frozen sequences file not present at {seq_path}")
    if not PETLS_AVAILABLE:
        pytest.skip("petls not importable in this environment")

    states = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
    state_to_idx = {s: i for i, s in enumerate(states)}
    n_states = len(states)

    sequences = json.loads(seq_path.read_text(encoding="utf-8"))
    counts = np.zeros((n_states, n_states), dtype=np.int64)
    for seq in sequences:
        for a, b in zip(seq[:-1], seq[1:]):
            if a in state_to_idx and b in state_to_idx:
                counts[state_to_idx[a], state_to_idx[b]] += 1

    D = build_undirected_graph(counts)
    numpy_result = compute_fiedler_curve(D, backend="numpy")
    petls_result = compute_fiedler_curve(D, backend="petls")

    assert numpy_result["n_active_steps"] == 35
    assert numpy_result["thresholds"] == petls_result["thresholds"]
    assert numpy_result["ker_dim"] == petls_result["ker_dim"]
    np.testing.assert_allclose(numpy_result["lambda1"], petls_result["lambda1"], atol=1e-4)
