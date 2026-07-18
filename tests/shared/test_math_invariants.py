# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Validation tests for the theorem-derived invariant battery, including the
#          I2b negative controls (each check demonstrated firing on a known-bad input,
#          among them a reimplementation of the historical greedy W2 fallback defect).
"""Tests for shared.math_invariants — the theorem-derived invariant battery.

Positive tests establish each check passes on correct implementations
(hand-computed known answers, the scipy Hungarian oracle, and — when
installed — gudhi's exact solvers). Negative controls establish each check
*fires* on the documented failure modes: greedy rank matching (the Class-1
defect), the no-zero-diagonal augmented reduction (the
wasserstein_null_tests fallback defect), corrupted landscapes, off-grid
p-values, vacuous nulls, and anti-conservative tests.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from shared import math_invariants as mi

pytestmark = pytest.mark.validation

RNG_SEED = 42


# ---------------------------------------------------------------------------
# Helpers: random diagrams and the known-bad implementations (negative controls)
# ---------------------------------------------------------------------------


def _random_diagram(rng: np.random.Generator, n: int, offset: float = 0.0) -> NDArray[np.float64]:
    births = rng.uniform(0.0, 2.0, n) + offset
    pers = rng.uniform(0.1, 1.5, n)
    return np.column_stack([births, births + pers])


def _greedy_rank_distance(a: NDArray[np.float64], b: NDArray[np.float64], internal_p: float = 2.0) -> float:
    """The historical defect: pair points by persistence rank, leftovers to diagonal.

    This is NOT optimal transport — it reproduces the greedy fallback that
    inflated H1 W2 headlines ~18-56x. It exists here solely as the I2b
    negative control the battery must catch.
    """
    da = a[np.argsort(-(a[:, 1] - a[:, 0]))]
    db = b[np.argsort(-(b[:, 1] - b[:, 0]))]
    k = min(len(da), len(db))
    cost = 0.0
    if k:
        matched = mi._ground_distances(da[:k], db[:k], internal_p)
        cost += float((np.diagonal(matched) ** 2).sum())
    for rest in (da[k:], db[k:]):
        if len(rest):
            cost += float((mi._diagonal_distance(rest[:, 1] - rest[:, 0], internal_p) ** 2).sum())
    return cost**0.5


def _augmented_no_zero_block(a: NDArray[np.float64], b: NDArray[np.float64], internal_p: float = 2.0) -> float:
    """The wasserstein_null_tests fallback defect: diagonal-diagonal cost > 0.

    Identical to the canonical reduction except the diagonal-diagonal block
    holds the distance between the two projections instead of 0, forcing
    surplus diagonal slots to pair at positive cost — an upper-biased
    approximation, not the exact estimand.
    """
    proj_a = np.column_stack([a.mean(axis=1), a.mean(axis=1)])
    proj_b = np.column_stack([b.mean(axis=1), b.mean(axis=1)])
    a_aug = np.vstack([a, proj_b])
    b_aug = np.vstack([b, proj_a])
    cost = mi._ground_distances(a_aug, b_aug, internal_p) ** 2
    from scipy.optimize import linear_sum_assignment

    row, col = linear_sum_assignment(cost)
    return float(cost[row, col].sum() ** 0.5)


# ---------------------------------------------------------------------------
# D1 — well-formedness
# ---------------------------------------------------------------------------


def test_d1_wellformed_passes_on_clean_diagram() -> None:
    rng = np.random.default_rng(RNG_SEED)
    assert mi.check_diagram_wellformed(_random_diagram(rng, 20)).passed


def test_d1_fires_on_nan_and_inverted_pairs() -> None:
    assert not mi.check_diagram_wellformed(np.array([[0.0, np.nan]])).passed
    assert not mi.check_diagram_wellformed(np.array([[2.0, 1.0]])).passed


# ---------------------------------------------------------------------------
# W1 — closed-form empty-diagram oracle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("internal_p", [2.0, np.inf])
def test_w1_closed_form_matches_hungarian_oracle(internal_p: float) -> None:
    rng = np.random.default_rng(RNG_SEED)
    empty = np.zeros((0, 2))
    for n in (1, 5, 17):
        dgm = _random_diagram(rng, n)
        closed = mi.wasserstein_to_empty(dgm, order=2.0, internal_p=internal_p)
        oracle = mi.wasserstein_exact_small(dgm, empty, order=2.0, internal_p=internal_p)
        assert closed == pytest.approx(oracle, rel=1e-12)


def test_w1_hand_computed_value() -> None:
    # Single point (0, 4): pers 4, diagonal distance 4/sqrt(2) under L2 ground metric.
    assert mi.wasserstein_to_empty(np.array([[0.0, 4.0]])) == pytest.approx(4.0 / np.sqrt(2.0), rel=1e-12)


# ---------------------------------------------------------------------------
# W2 — diagonal-transport bound
# ---------------------------------------------------------------------------


def test_w2_exact_distances_respect_diagonal_bound() -> None:
    rng = np.random.default_rng(RNG_SEED)
    for _ in range(10):
        a, b = _random_diagram(rng, 8), _random_diagram(rng, 6)
        w2 = mi.wasserstein_exact_small(a, b)
        assert mi.check_diagonal_bound(w2, a, b).passed


def test_w2_fires_on_greedy_inflation() -> None:
    # Two far-apart low-persistence points: greedy pairs them by rank at huge
    # cost; the optimum sends both to the diagonal. Bound = 1, greedy ~ 141.
    a, b = np.array([[0.0, 1.0]]), np.array([[100.0, 101.0]])
    greedy = _greedy_rank_distance(a, b)
    verdict = mi.check_diagonal_bound(greedy, a, b)
    assert not verdict.passed
    assert greedy > 100.0 * verdict.detail["bound"]


# ---------------------------------------------------------------------------
# W3 — Hungarian mini-oracle and solver agreement
# ---------------------------------------------------------------------------


def test_w3_hand_computed_values() -> None:
    # Match beats diagonal: W2({(0,2)}, {(0,2.2)}) = 0.2 (L2 ground metric).
    assert mi.wasserstein_exact_small(np.array([[0.0, 2.0]]), np.array([[0.0, 2.2]])) == pytest.approx(0.2, rel=1e-12)
    # Mixed: big-big matches at 0, small point to diagonal at cost (0.5*sqrt(2))^2 = 0.5.
    a = np.array([[0.0, 10.0], [0.0, 1.0]])
    b = np.array([[0.0, 10.0]])
    assert mi.wasserstein_exact_small(a, b) == pytest.approx(np.sqrt(0.5), rel=1e-12)


def test_w3_oracle_agrees_with_itself_under_symmetry() -> None:
    rng = np.random.default_rng(RNG_SEED)
    a, b = _random_diagram(rng, 7), _random_diagram(rng, 9)
    assert mi.wasserstein_exact_small(a, b) == pytest.approx(mi.wasserstein_exact_small(b, a), rel=1e-12)


def test_w3_agreement_with_gudhi_exact_solver() -> None:
    gw = pytest.importorskip("gudhi.wasserstein", reason="gudhi/POT exact solver not installed")
    rng = np.random.default_rng(RNG_SEED)
    pairs = [(_random_diagram(rng, 6), _random_diagram(rng, 8)) for _ in range(10)]
    verdict = mi.check_solver_agreement(
        lambda a, b: float(gw.wasserstein_distance(a, b, order=2.0, internal_p=2.0)),
        pairs,
    )
    assert verdict.passed, verdict.detail


def test_w3_fires_on_greedy_rank_matching() -> None:
    rng = np.random.default_rng(RNG_SEED)
    pairs = [(_random_diagram(rng, 5), _random_diagram(rng, 5, offset=3.0)) for _ in range(5)]
    verdict = mi.check_solver_agreement(_greedy_rank_distance, pairs)
    assert not verdict.passed


def test_w3_fires_on_no_zero_diagonal_block_reduction() -> None:
    # Optimal plan: real-real match + one point to diagonal; the defective
    # reduction then pairs surplus diagonal slots at positive cost.
    a = np.array([[0.0, 2.0], [10.0, 11.0]])
    b = np.array([[0.1, 2.1]])
    correct = mi.wasserstein_exact_small(a, b)
    naive = _augmented_no_zero_block(a, b)
    assert correct == pytest.approx(np.sqrt(0.52), rel=1e-9)
    assert naive > correct + 1e-3  # upper-biased, as documented in the spec §4


# ---------------------------------------------------------------------------
# W4 — metric axioms
# ---------------------------------------------------------------------------


def test_w4_exact_solver_satisfies_metric_axioms() -> None:
    rng = np.random.default_rng(RNG_SEED)
    diagrams = [_random_diagram(rng, n) for n in (4, 6, 8, 3)]
    assert mi.check_metric_axioms(mi.wasserstein_exact_small, diagrams).passed


def test_w4_fires_on_greedy_triangle_violation() -> None:
    # d(A, empty) + d(empty, B) ~ 1.41 under greedy, but greedy d(A, B) ~ 141.
    diagrams = [np.array([[0.0, 1.0]]), np.zeros((0, 2)), np.array([[100.0, 101.0]])]
    verdict = mi.check_metric_axioms(_greedy_rank_distance, diagrams)
    assert not verdict.passed
    assert verdict.detail["worst_triangle_excess"] > 100.0


# ---------------------------------------------------------------------------
# W5 — bottleneck sandwich
# ---------------------------------------------------------------------------


def test_w5_hand_computed_sandwich_holds_for_exact_value() -> None:
    # bottleneck({(0,2)}, {(0,2.2)}) = 0.2 (match at L-inf cost 0.2 beats diagonals).
    a, b = np.array([[0.0, 2.0]]), np.array([[0.0, 2.2]])
    w2 = mi.wasserstein_exact_small(a, b)
    assert mi.check_bottleneck_sandwich(w2, a, b, bottleneck=0.2).passed


def test_w5_fires_on_greedy_inflation() -> None:
    # bottleneck = 0.5 (both to diagonal); upper bound = sqrt(2)*sqrt(2)*0.5 = 1.
    a, b = np.array([[0.0, 1.0]]), np.array([[100.0, 101.0]])
    greedy = _greedy_rank_distance(a, b)
    assert not mi.check_bottleneck_sandwich(greedy, a, b, bottleneck=0.5).passed


def test_w5_sandwich_against_gudhi_bottleneck() -> None:
    gudhi = pytest.importorskip("gudhi", reason="gudhi not installed")
    rng = np.random.default_rng(RNG_SEED)
    for _ in range(5):
        a, b = _random_diagram(rng, 7), _random_diagram(rng, 5)
        bottleneck = float(gudhi.bottleneck_distance(a, b))
        w2 = mi.wasserstein_exact_small(a, b)
        verdict = mi.check_bottleneck_sandwich(w2, a, b, bottleneck, rtol=1e-6)
        assert verdict.passed, verdict.detail


# ---------------------------------------------------------------------------
# L1/L2 — landscape structure and the exact norm identity
# ---------------------------------------------------------------------------


def _grid_for(diagram: NDArray[np.float64], n_points: int = 4001) -> NDArray[np.float64]:
    lo, hi = diagram[:, 0].min(), diagram[:, 1].max()
    pad = 0.05 * (hi - lo)
    return np.linspace(lo - pad, hi + pad, n_points)


def test_l1_reference_landscape_passes_structure() -> None:
    rng = np.random.default_rng(RNG_SEED)
    dgm = _random_diagram(rng, 12)
    ts = _grid_for(dgm)
    levels = mi.landscape_levels(dgm, ts)
    assert mi.check_landscape_structure(levels, ts, dgm, rtol=1e-9).passed


def test_l1_fires_on_shuffled_levels_and_offset() -> None:
    rng = np.random.default_rng(RNG_SEED)
    dgm = _random_diagram(rng, 8)
    ts = _grid_for(dgm)
    levels = mi.landscape_levels(dgm, ts)
    shuffled = levels[::-1].copy()  # breaks the descending-order invariant
    assert not mi.check_landscape_structure(shuffled, ts, dgm).passed
    offset = levels + 0.1  # leaks outside the support and exceeds peak caps
    assert not mi.check_landscape_structure(offset, ts, dgm).passed


def test_l2_norm_identity_two_sided_at_full_depth() -> None:
    rng = np.random.default_rng(RNG_SEED)
    for n in (1, 5, 15):
        dgm = _random_diagram(rng, n)
        ts = _grid_for(dgm)
        levels = mi.landscape_levels(dgm, ts)
        verdict = mi.check_landscape_norm(levels, ts, dgm, p=2.0, rtol=1e-3)
        assert verdict.passed, verdict.detail
        # And the numbers genuinely agree, not merely within a loose band:
        assert verdict.detail["computed"] == pytest.approx(verdict.detail["closed_form"], rel=1e-4)


def test_l2_truncated_landscape_passes_one_sided_only() -> None:
    rng = np.random.default_rng(RNG_SEED)
    dgm = _random_diagram(rng, 15)
    ts = _grid_for(dgm)
    truncated = mi.landscape_levels(dgm, ts, k_max=2)
    verdict = mi.check_landscape_norm(truncated, ts, dgm, p=2.0)
    assert verdict.passed  # deficit is explainable by truncation
    assert verdict.detail["computed"] < verdict.detail["closed_form"]


def test_l2_fires_on_scaled_landscape() -> None:
    rng = np.random.default_rng(RNG_SEED)
    dgm = _random_diagram(rng, 10)
    ts = _grid_for(dgm)
    inflated = 1.1 * mi.landscape_levels(dgm, ts)  # computed norm > closed form: impossible
    assert not mi.check_landscape_norm(inflated, ts, dgm, p=2.0).passed


def test_l2_closed_form_hand_value() -> None:
    # Single point (0, 2): h = 1, total L2 content = 2/3.
    assert mi.landscape_norm_closed_form(np.array([[0.0, 2.0]]), p=2.0) == pytest.approx(2.0 / 3.0, rel=1e-12)


# ---------------------------------------------------------------------------
# L3 — landscape stability against the bottleneck
# ---------------------------------------------------------------------------


def test_l3_hand_computed_stability_holds() -> None:
    a, b = np.array([[0.0, 2.0]]), np.array([[0.0, 2.2]])
    ts = np.linspace(-0.5, 3.0, 4001)
    la, lb = mi.landscape_levels(a, ts), mi.landscape_levels(b, ts)
    assert mi.check_landscape_stability(la, lb, bottleneck=0.2).passed


def test_l3_fires_on_understated_bottleneck() -> None:
    a, b = np.array([[0.0, 2.0]]), np.array([[0.0, 2.2]])
    ts = np.linspace(-0.5, 3.0, 4001)
    la, lb = mi.landscape_levels(a, ts), mi.landscape_levels(b, ts)
    assert not mi.check_landscape_stability(la, lb, bottleneck=0.05).passed


def test_l3_stability_against_gudhi_bottleneck() -> None:
    gudhi = pytest.importorskip("gudhi", reason="gudhi not installed")
    rng = np.random.default_rng(RNG_SEED)
    for _ in range(5):
        a, b = _random_diagram(rng, 8), _random_diagram(rng, 6)
        both = np.vstack([a, b])
        ts = _grid_for(both)
        la, lb = mi.landscape_levels(a, ts), mi.landscape_levels(b, ts)
        bottleneck = float(gudhi.bottleneck_distance(a, b))
        verdict = mi.check_landscape_stability(la, lb, bottleneck, rtol=1e-6)
        assert verdict.passed, verdict.detail


# ---------------------------------------------------------------------------
# P1 — p-value grid membership
# ---------------------------------------------------------------------------


def test_p1_add_one_grid_passes() -> None:
    for b, n_draws in ((0, 1000), (2, 1000), (999, 1000), (42, 99)):
        p = (b + 1) / (n_draws + 1)
        assert mi.check_pvalue_grid(p, n_draws).passed


def test_p1_fires_on_wrong_denominator() -> None:
    # b/B instead of (b+1)/(B+1): the Class-10 denominator contradiction.
    assert not mi.check_pvalue_grid(25 / 1000, 1000).passed
    assert not mi.check_pvalue_grid(0.0, 1000).passed  # p = 0 is off-grid for add-one


# ---------------------------------------------------------------------------
# P3 — null-sensitivity probe
# ---------------------------------------------------------------------------


def test_p3_fires_on_vacuous_null() -> None:
    # The historical defect: the null permutes rows of a set-valued input, so
    # the statistic (here: a symmetric function of the rows) never changes.
    data = np.arange(20.0).reshape(10, 2)
    verdict = mi.null_sensitivity_probe(
        statistic_fn=lambda d: float(np.sort(d.ravel()).sum()),
        null_draw_fn=lambda d, rng: rng.permutation(d, axis=0),
        observed_data=data,
    )
    assert not verdict.passed
    assert verdict.detail["max_probe_deviation"] == 0.0


def test_p3_passes_on_effective_null() -> None:
    data = np.arange(20.0).reshape(10, 2)
    weights = np.linspace(0.0, 1.0, 10)
    verdict = mi.null_sensitivity_probe(
        statistic_fn=lambda d: float((weights @ d).sum()),
        null_draw_fn=lambda d, rng: rng.permutation(d, axis=0),
        observed_data=data,
    )
    assert verdict.passed


# ---------------------------------------------------------------------------
# P2 — double-null calibration (the battery's one statistical check)
# ---------------------------------------------------------------------------


def _permutation_pvalue(rng: np.random.Generator, n_draws: int = 99) -> float:
    """A valid add-one permutation test on a two-group mean difference, run on null data."""
    x = rng.standard_normal(24)
    labels = np.repeat([0, 1], 12)
    observed = abs(x[labels == 0].mean() - x[labels == 1].mean())
    exceed = 0
    for _ in range(n_draws):
        perm = rng.permutation(labels)
        if abs(x[perm == 0].mean() - x[perm == 1].mean()) >= observed:
            exceed += 1
    return (exceed + 1) / (n_draws + 1)


def test_p2_valid_permutation_test_calibrates() -> None:
    verdict = mi.double_null_calibration(_permutation_pvalue, n_runs=200, seed=RNG_SEED)
    assert verdict.passed, verdict.detail


def test_p2_fires_on_anti_conservative_test() -> None:
    # p**4 of a uniform p-value: P(p <= 0.05) ~ 0.47 — grossly anti-conservative.
    verdict = mi.double_null_calibration(lambda rng: float(rng.uniform()) ** 4, n_runs=200, seed=RNG_SEED)
    assert not verdict.passed
