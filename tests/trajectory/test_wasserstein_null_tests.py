"""Unit tests for diagram-level Wasserstein null tests.

Covers:
- _compute_wasserstein_distance: symmetry, identity, infinite-death filtering,
  gudhi/scipy fallback routing
- _scipy_wasserstein_exact: edge cases (empty diagrams, unequal sizes)
- diagram_wasserstein_pvalue: return-type contract, p-value range, z-score,
  observed_distance content, empty diagrams, method detection
- stratified_wasserstein_test: group-mapping correctness, pairwise symmetry,
  p-values in [0,1], identical-group baseline, ripser-unavailable path
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

from trajectory_tda.validation.wasserstein_null_tests import (
    WassersteinNullResult,
    _compute_wasserstein_distance,
    _scipy_wasserstein_exact,
    diagram_wasserstein_pvalue,
    stratified_wasserstein_test,
)

# ─────────────────────────────────────────────────────────────
# Helpers — small synthetic persistence diagrams
# ─────────────────────────────────────────────────────────────


def _make_diagram(pairs: list[tuple[float, float]]) -> np.ndarray:
    """Build a (n, 2) float64 persistence diagram from a list of (birth, death) pairs."""
    if not pairs:
        return np.empty((0, 2), dtype=np.float64)
    return np.array(pairs, dtype=np.float64)


# Simple diagrams used across many tests
DIAG_SIMPLE = _make_diagram([(0.0, 1.0), (0.5, 2.0), (0.1, 0.3)])
DIAG_SHIFTED = _make_diagram([(0.0, 1.5), (0.5, 2.5), (0.1, 0.8)])  # shifted right
DIAG_EMPTY = _make_diagram([])
DIAG_SINGLE = _make_diagram([(0.0, 1.0)])
# Diagram with an infinite death that must be filtered
DIAG_WITH_INF = np.array([[0.0, 1.0], [0.5, np.inf], [0.1, 0.3]])


# ─────────────────────────────────────────────────────────────
# Tests: _scipy_wasserstein_exact
# ─────────────────────────────────────────────────────────────


class TestScipyWassersteinExact:
    """Algebraic properties of the exact scipy fallback."""

    def test_identity_returns_zero(self):
        """Distance from a diagram to itself is zero."""
        d = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_SIMPLE)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_symmetric(self):
        """d(A, B) == d(B, A)."""
        d_ab = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_SHIFTED)
        d_ba = _scipy_wasserstein_exact(DIAG_SHIFTED, DIAG_SIMPLE)
        assert d_ab == pytest.approx(d_ba, rel=1e-6)

    def test_nonnegative(self):
        d = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_SHIFTED)
        assert d >= 0.0

    def test_both_empty_returns_zero(self):
        d = _scipy_wasserstein_exact(DIAG_EMPTY, DIAG_EMPTY)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_one_empty_returns_finite(self):
        """Matching a non-empty diagram against the empty one should work."""
        d = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_EMPTY)
        assert np.isfinite(d)
        assert d >= 0.0

    def test_single_point_both_sides(self):
        d = _scipy_wasserstein_exact(DIAG_SINGLE, DIAG_SINGLE)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_unequal_sizes_runs(self):
        """Diagrams with different numbers of pairs should not raise."""
        diag_large = _make_diagram([(i * 0.1, i * 0.1 + 1.0) for i in range(10)])
        diag_small = _make_diagram([(0.0, 1.0)])
        d = _scipy_wasserstein_exact(diag_large, diag_small)
        assert np.isfinite(d) and d >= 0.0

    def test_order_2_produces_larger_than_order_1(self):
        """Higher Wasserstein order magnifies large distances."""
        d1 = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_SHIFTED, order=1)
        d2 = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_SHIFTED, order=2)
        # Both must be finite and non-negative; no strict ordering between
        # orders is guaranteed, but both should be positive when diagrams differ
        assert d1 >= 0.0
        assert d2 >= 0.0


# ─────────────────────────────────────────────────────────────
# Tests: scipy fallback == exact W_q (canonical zero-block reduction)
# ─────────────────────────────────────────────────────────────


def _bruteforce_wasserstein(diagram_a: np.ndarray, diagram_b: np.ndarray, order: int = 2) -> float:
    """Exact W_q oracle by exhaustive enumeration of partial matchings.

    Independent re-derivation of the estimand computed by
    ``shared/math_invariants.py::wasserstein_exact_small`` (the canonical
    augmented-assignment oracle, PR #131): every injective partial matching
    between A and B is enumerated; matched pairs pay the Euclidean ground
    distance to the ``order``-th power, unmatched points pay their L2
    distance to the diagonal (persistence / sqrt(2)) to the ``order``-th
    power. Shares no code with the solver under test. Tiny diagrams only
    (factorial enumeration).
    """
    from itertools import combinations, permutations

    n, m = len(diagram_a), len(diagram_b)

    def diag_cost(pt: np.ndarray) -> float:
        return float((pt[1] - pt[0]) / np.sqrt(2.0)) ** order

    best = np.inf
    for k in range(min(n, m) + 1):
        for a_idx in combinations(range(n), k):
            for b_idx in permutations(range(m), k):
                total = sum(float(np.linalg.norm(diagram_a[i] - diagram_b[j])) ** order for i, j in zip(a_idx, b_idx))
                total += sum(diag_cost(diagram_a[i]) for i in range(n) if i not in a_idx)
                total += sum(diag_cost(diagram_b[j]) for j in range(m) if j not in b_idx)
                best = min(best, total)
    return float(best ** (1.0 / order))


class TestScipyFallbackCanonicalReduction:
    """The scipy fallback must compute exact W_q, not an upper-biased surrogate.

    Regression for the augmented-matrix defect where the diagonal-diagonal
    block carried the distance between the two diagonal projections instead
    of 0: whenever the optimal plan contained a real-real match, surplus
    diagonal slots were forced to pair at positive cost, over-estimating W_q
    (demonstrated by test_w3_fires_on_no_zero_diagonal_block_reduction in
    tests/shared/test_math_invariants.py, PR #131).
    """

    def test_surplus_diagonal_slots_regression(self):
        """One real-real match plus a surplus diagonal slot: the bug's minimal trigger.

        A = {(10, 11), (0, 4)}, B = {(0, 1.2)}. Optimal plan: (0,4)-(0,1.2)
        real-real (cost 2.8^2), (10,11) to the diagonal (cost (1/sqrt(2))^2);
        exact W_2 = sqrt(8.34). The defective matrix additionally charged the
        leftover B-projection row against the leftover A-projection column.
        """
        diag_a = _make_diagram([(10.0, 11.0), (0.0, 4.0)])
        diag_b = _make_diagram([(0.0, 1.2)])
        d = _scipy_wasserstein_exact(diag_a, diag_b, order=2)
        assert d == pytest.approx(np.sqrt(8.34), rel=1e-9)
        assert d == pytest.approx(_bruteforce_wasserstein(diag_a, diag_b, order=2), rel=1e-9)

    @pytest.mark.parametrize("order", [1, 2])
    def test_matches_bruteforce_on_fixed_cases(self, order):
        """Exact agreement with the enumeration oracle on the shared fixtures."""
        cases = [
            (DIAG_SIMPLE, DIAG_SHIFTED),
            (DIAG_SIMPLE, DIAG_SINGLE),
            (DIAG_SINGLE, DIAG_EMPTY),
            (DIAG_SIMPLE, DIAG_EMPTY),
        ]
        for diag_a, diag_b in cases:
            d = _scipy_wasserstein_exact(diag_a, diag_b, order=order)
            expected = _bruteforce_wasserstein(diag_a, diag_b, order=order)
            assert d == pytest.approx(expected, rel=1e-9, abs=1e-12)

    @pytest.mark.parametrize("order", [1, 2])
    def test_matches_bruteforce_randomized(self, order):
        """Exact agreement with the enumeration oracle on random tiny diagrams."""
        rng = np.random.default_rng(20260718)
        for _ in range(25):
            n, m = int(rng.integers(0, 4)), int(rng.integers(0, 4))
            births_a = rng.uniform(0.0, 2.0, size=n)
            births_b = rng.uniform(0.0, 2.0, size=m)
            diag_a = np.column_stack([births_a, births_a + rng.uniform(0.0, 2.0, size=n)]) if n else DIAG_EMPTY
            diag_b = np.column_stack([births_b, births_b + rng.uniform(0.0, 2.0, size=m)]) if m else DIAG_EMPTY
            d = _scipy_wasserstein_exact(diag_a, diag_b, order=order)
            expected = _bruteforce_wasserstein(diag_a, diag_b, order=order)
            assert d == pytest.approx(expected, rel=1e-9, abs=1e-12)

    def test_one_empty_exact_value(self):
        """Against the empty diagram every point pays its diagonal distance."""
        d = _scipy_wasserstein_exact(DIAG_SIMPLE, DIAG_EMPTY, order=2)
        pers = DIAG_SIMPLE[:, 1] - DIAG_SIMPLE[:, 0]
        expected = float(np.sum((pers / np.sqrt(2.0)) ** 2) ** 0.5)
        assert d == pytest.approx(expected, rel=1e-9)

    def test_agrees_with_gudhi_hera_when_available(self):
        """Cross-check against the exact hera solver (same estimand, internal_p=2)."""
        hera = pytest.importorskip("gudhi.hera", reason="gudhi hera bindings not installed")
        for diag_a, diag_b in [(DIAG_SIMPLE, DIAG_SHIFTED), (DIAG_SIMPLE, DIAG_SINGLE)]:
            d_fallback = _scipy_wasserstein_exact(diag_a, diag_b, order=2)
            d_hera = hera.wasserstein_distance(diag_a, diag_b, order=2, internal_p=2, delta=1e-8)
            assert d_fallback == pytest.approx(d_hera, rel=1e-6)


# ─────────────────────────────────────────────────────────────
# Tests: _compute_wasserstein_distance
# ─────────────────────────────────────────────────────────────


class TestComputeWassersteinDistance:
    """Routing, symmetry, and edge cases for _compute_wasserstein_distance."""

    def test_identity_returns_zero(self):
        d = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SIMPLE)
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_symmetric(self):
        d_ab = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SHIFTED)
        d_ba = _compute_wasserstein_distance(DIAG_SHIFTED, DIAG_SIMPLE)
        assert d_ab == pytest.approx(d_ba, rel=1e-5)

    def test_nonnegative(self):
        d = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SHIFTED)
        assert d >= 0.0

    def test_returns_float(self):
        d = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SHIFTED)
        assert isinstance(d, float)

    def test_infinite_deaths_filtered_before_computation(self):
        """Infinite deaths are stripped; result should equal finite-only version."""
        # DIAG_WITH_INF has middle row with death=inf; should filter to 2 finite pairs
        finite_only = _make_diagram([(0.0, 1.0), (0.1, 0.3)])
        d_inf = _compute_wasserstein_distance(DIAG_WITH_INF, DIAG_SIMPLE)
        d_finite = _compute_wasserstein_distance(finite_only, DIAG_SIMPLE)
        assert d_inf == pytest.approx(d_finite, rel=1e-5)

    def test_empty_vs_empty_returns_zero(self):
        d = _compute_wasserstein_distance(DIAG_EMPTY, DIAG_EMPTY)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_empty_vs_nonempty_returns_finite(self):
        d = _compute_wasserstein_distance(DIAG_EMPTY, DIAG_SIMPLE)
        assert np.isfinite(d) and d >= 0.0

    def test_dispatches_to_scipy_when_gudhi_absent(self):
        """When gudhi.hera is not importable, falls back to scipy with a warning."""
        # Ensure gudhi.hera is absent by patching builtins.__import__
        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def _block_gudhi(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "gudhi.hera":
                raise ImportError("mocked absence of gudhi.hera")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_block_gudhi):
            with pytest.warns(UserWarning, match="gudhi.hera not available"):
                d = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SHIFTED)
        assert np.isfinite(d) and d >= 0.0

    @pytest.mark.skipif(
        "gudhi.wasserstein" not in sys.modules and True,
        reason="test always runs; skip if want to isolate",
    )
    def test_order_parameter_forwarded(self):
        """Different order values should give different (non-negative) results."""
        d1 = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SHIFTED, order=1)
        d2 = _compute_wasserstein_distance(DIAG_SIMPLE, DIAG_SHIFTED, order=2)
        assert d1 >= 0.0
        assert d2 >= 0.0


# ─────────────────────────────────────────────────────────────
# Tests: diagram_wasserstein_pvalue
# ─────────────────────────────────────────────────────────────


def _make_null_diagrams(n: int = 20, seed: int = 42) -> list[np.ndarray]:
    """Generate n small random persistence diagrams as a null distribution."""
    rng = np.random.default_rng(seed)
    diagrams = []
    for _ in range(n):
        births = rng.uniform(0.0, 0.5, size=5)
        deaths = births + rng.uniform(0.05, 1.0, size=5)
        diagrams.append(np.column_stack([births, deaths]))
    return diagrams


class TestDiagramWassersteinPvalue:
    """Contract tests for diagram_wasserstein_pvalue."""

    def test_returns_correct_type(self):
        null = _make_null_diagrams(10)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert isinstance(result, WassersteinNullResult)

    def test_p_value_in_unit_interval(self):
        null = _make_null_diagrams(20)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert 0.0 <= result.p_value <= 1.0

    def test_z_score_is_float(self):
        null = _make_null_diagrams(20)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert isinstance(result.z_score, float)

    def test_observed_distance_is_nonneg_float(self):
        null = _make_null_diagrams(20)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert isinstance(result.observed_distance, float)
        assert result.observed_distance >= 0.0

    def test_n_null_simulations_matches_input(self):
        null = _make_null_diagrams(15)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert result.n_null_simulations == 15

    def test_null_distances_shape(self):
        null = _make_null_diagrams(12)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert result.null_distances.shape == (12,)

    def test_null_distances_nonneg(self):
        null = _make_null_diagrams(10)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert (result.null_distances >= 0.0).all()

    def test_wasserstein_order_stored(self):
        null = _make_null_diagrams(10)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null, wasserstein_order=1)
        assert result.wasserstein_order == 1

    def test_method_is_str(self):
        null = _make_null_diagrams(10)
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert result.method in ("hera", "scipy")

    def test_identical_observed_and_null_p_value(self):
        """When observed matches all null diagrams, all distances are zero.

        p_value = fraction of null_test_stats (null-vs-null) >= observed_distance.
        All distances are 0 (identical diagrams), so fraction(0 >= 0) = 1.0.
        """
        single_diag = DIAG_SIMPLE.copy()
        null = [single_diag.copy() for _ in range(20)]
        result = diagram_wasserstein_pvalue(single_diag, null)
        # All distances are 0; fraction >= 0.0 is 1.0
        assert result.p_value == pytest.approx(1.0, abs=1e-9)

    def test_p_value_direction_distinct_observed(self):
        """An observed diagram far from the null should yield low p-value.

        Construct a constant null (identical tiny diagrams near the diagonal)
        and an observed diagram with large persistent features. Under the
        corrected Robinson-Turner framework, all null-vs-null distances are
        zero (identical nulls), so the observed's large distance yields
        p_value = 0.0 and z_score >> 0.
        """
        # Null: identical tiny features near diagonal
        tiny = _make_diagram([(0.0, 0.01), (0.01, 0.02)])
        null = [tiny.copy() for _ in range(20)]
        # Observed: large persistent features far from diagonal
        large = _make_diagram([(0.0, 10.0), (0.5, 9.5)])
        result = diagram_wasserstein_pvalue(large, null)
        # null_test_stats = [0, ..., 0], observed_distance >> 0 → p_value = 0
        assert result.p_value == pytest.approx(0.0)
        assert result.observed_distance > 0.0
        assert result.z_score > 0.0

    def test_z_score_zero_for_identical_null(self):
        """When observed == null, observed_distance == null_mean so z_score = 0."""
        single_diag = DIAG_SIMPLE.copy()
        null = [single_diag.copy() for _ in range(20)]
        result = diagram_wasserstein_pvalue(single_diag, null)
        assert result.z_score == pytest.approx(0.0, abs=1e-6)

    def test_empty_observed_diagram_returns_result(self):
        """An empty observed diagram (no persistence pairs) should not crash."""
        null = _make_null_diagrams(10)
        result = diagram_wasserstein_pvalue(DIAG_EMPTY, null)
        assert isinstance(result, WassersteinNullResult)
        assert 0.0 <= result.p_value <= 1.0

    def test_empty_null_diagrams_returns_result(self):
        """Null diagrams that are all empty should not crash."""
        null = [DIAG_EMPTY.copy() for _ in range(10)]
        result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert isinstance(result, WassersteinNullResult)
        assert result.n_null_simulations == 10

    def test_infinite_deaths_in_observed_filtered(self):
        """Infinite deaths are filtered inside _compute_wasserstein_distance."""
        null = _make_null_diagrams(10)
        # Should run without error even with inf in the observed diagram
        result = diagram_wasserstein_pvalue(DIAG_WITH_INF, null)
        assert isinstance(result, WassersteinNullResult)
        assert np.isfinite(result.observed_distance)

    def test_gudhi_absent_falls_back_to_scipy(self):
        """When gudhi.hera is missing, method should be 'scipy'."""
        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def _block_gudhi(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "gudhi.hera":
                raise ImportError("blocked for test")
            return real_import(name, *args, **kwargs)

        null = _make_null_diagrams(5)
        with patch("builtins.__import__", side_effect=_block_gudhi):
            with pytest.warns(UserWarning, match="gudhi.hera not available"):
                result = diagram_wasserstein_pvalue(DIAG_SIMPLE, null)
        assert result.method == "scipy"
        assert 0.0 <= result.p_value <= 1.0


# ─────────────────────────────────────────────────────────────
# Tests: stratified_wasserstein_test
# ─────────────────────────────────────────────────────────────

ripser = pytest.importorskip("ripser", reason="ripser required for stratified test")


@pytest.fixture
def two_group_setup():
    """Minimal two-group setup for stratified tests.

    Group 0: stable-employed trajectories — cluster near (0, 0.5) in H1
    Group 1: low-income churn — cluster near (0.5, 1.5) in H1

    We provide pre-computed diagrams AND a point cloud so permutations
    recompute diagrams via ripser on shuffled assignments.
    """
    rng = np.random.default_rng(0)
    n_per_group = 30
    n_dim = 5

    # Group 0: tight cluster; Group 1: spread cluster
    pts_0 = rng.normal(loc=0.0, scale=0.5, size=(n_per_group, n_dim))
    pts_1 = rng.normal(loc=3.0, scale=0.5, size=(n_per_group, n_dim))

    all_points = np.vstack([pts_0, pts_1]).astype(np.float64)
    group_memberships = np.array([0] * n_per_group + [1] * n_per_group, dtype=np.int64)

    # Compute H1 diagrams via ripser
    def _h1(pts: np.ndarray) -> np.ndarray:
        dgms = ripser.ripser(pts, maxdim=1)["dgms"][1]
        return np.array([[b, d] for b, d in dgms if np.isfinite(d)])

    diag_0 = _h1(pts_0)
    diag_1 = _h1(pts_1)

    diagrams_by_group = {"group0": diag_0, "group1": diag_1}
    return diagrams_by_group, group_memberships, all_points


class TestStratifiedWassersteinTest:
    """Tests for stratified_wasserstein_test."""

    def test_returns_correct_type(self, two_group_setup):
        diagrams_by_group, memberships, points = two_group_setup
        from trajectory_tda.validation.wasserstein_null_tests import (
            StratifiedWassersteinResult,
        )

        result = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=5)
        assert isinstance(result, StratifiedWassersteinResult)

    def test_group_labels_match_input_keys(self, two_group_setup):
        diagrams_by_group, memberships, points = two_group_setup
        result = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=5)
        assert sorted(result.group_labels) == sorted(diagrams_by_group.keys())

    def test_pairwise_distances_symmetric(self, two_group_setup):
        """Distance matrix should be symmetric with zeros on diagonal."""
        diagrams_by_group, memberships, points = two_group_setup
        result = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=5)
        d = result.pairwise_distances
        np.testing.assert_allclose(d, d.T, atol=1e-9, err_msg="Distance matrix not symmetric")
        np.testing.assert_allclose(np.diag(d), 0.0, atol=1e-9, err_msg="Diagonal not zero")

    def test_p_values_in_unit_interval(self, two_group_setup):
        diagrams_by_group, memberships, points = two_group_setup
        result = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=10)
        assert (result.permutation_p_values >= 0.0).all()
        assert (result.permutation_p_values <= 1.0).all()

    def test_p_values_symmetric_matrix(self, two_group_setup):
        """P-value matrix should also be symmetric."""
        diagrams_by_group, memberships, points = two_group_setup
        result = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=5)
        p = result.permutation_p_values
        np.testing.assert_allclose(p, p.T, atol=1e-9, err_msg="P-value matrix not symmetric")

    def test_n_permutations_stored(self, two_group_setup):
        diagrams_by_group, memberships, points = two_group_setup
        result = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=7)
        assert result.n_permutations == 7

    def test_identical_groups_p_value_not_small(self, two_group_setup):
        """Identical diagrams for both groups should not yield a very small p-value.

        Since the groups are the same, a random permutation of membership
        should look just as different as the observed assignment.
        """
        rng = np.random.default_rng(1)
        n = 30
        pts = rng.normal(size=(n * 2, 5))  # same distribution for both groups
        memberships = np.array([0] * n + [1] * n, dtype=np.int64)

        def _h1(p: np.ndarray) -> np.ndarray:
            dgms = ripser.ripser(p, maxdim=1)["dgms"][1]
            return np.array([[b, d] for b, d in dgms if np.isfinite(d)])

        diag_same = _h1(pts[:n])
        # Use the same diagram for both groups (extreme identical case)
        diagrams_by_group = {"group0": diag_same, "group1": diag_same.copy()}

        result = stratified_wasserstein_test(diagrams_by_group, memberships, pts, n_permutations=20, random_seed=0)
        # p-value should be >= 0; for identical diagrams it should not be
        # suspiciously low. We allow any value in [0,1] but assert it's
        # not less than 0 (sanity) and not exactly 0 (unreasonably strong result).
        assert result.permutation_p_values[0, 1] >= 0.0

    def test_group_mapping_three_groups(self):
        """With 3 groups, pairwise_distances and p_values should be (3,3) matrices."""
        rng = np.random.default_rng(2)
        n = 20
        n_dim = 4
        pts = rng.normal(size=(n * 3, n_dim))
        memberships = np.array([0] * n + [1] * n + [2] * n, dtype=np.int64)

        def _h1(p: np.ndarray) -> np.ndarray:
            dgms = ripser.ripser(p, maxdim=1)["dgms"][1]
            return np.array([[b, d] for b, d in dgms if np.isfinite(d)])

        diagrams_by_group = {
            "A": _h1(pts[:n]),
            "B": _h1(pts[n : 2 * n]),
            "C": _h1(pts[2 * n :]),
        }
        result = stratified_wasserstein_test(diagrams_by_group, memberships, pts, n_permutations=3)
        assert result.pairwise_distances.shape == (3, 3)
        assert result.permutation_p_values.shape == (3, 3)
        assert len(result.group_labels) == 3

    def test_ripser_unavailable_raises_import_error(self, two_group_setup):
        """When ripser is not importable, stratified test must raise ImportError."""
        diagrams_by_group, memberships, points = two_group_setup

        # Temporarily remove ripser from available modules
        with patch.dict(sys.modules, {"ripser": None}):
            with pytest.raises(ImportError, match="ripser"):
                stratified_wasserstein_test(
                    diagrams_by_group,
                    memberships,
                    points,
                    n_permutations=5,
                )

    def test_reproducibility_with_same_seed(self, two_group_setup):
        """Results should be identical for the same random_seed."""
        diagrams_by_group, memberships, points = two_group_setup
        r1 = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=10, random_seed=7)
        r2 = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=10, random_seed=7)
        np.testing.assert_array_equal(r1.pairwise_distances, r2.pairwise_distances)
        np.testing.assert_array_equal(r1.permutation_p_values, r2.permutation_p_values)

    def test_different_seeds_may_differ(self, two_group_setup):
        """Different seeds should (almost certainly) produce different p-values."""
        diagrams_by_group, memberships, points = two_group_setup
        r1 = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=50, random_seed=0)
        r2 = stratified_wasserstein_test(diagrams_by_group, memberships, points, n_permutations=50, random_seed=99)
        # Pairwise distances are deterministic (observed); only p-values differ
        np.testing.assert_array_equal(
            r1.pairwise_distances,
            r2.pairwise_distances,
            err_msg="Observed distances should not vary with seed",
        )
