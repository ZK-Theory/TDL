# Research context: TDA-Research/00-Meta/Discovery/mcbif-weighted-nerve-employment-dispatch-prereg-2026-07-10.md
# Purpose: Determinism and correctness tests for the confirmatory weighted-nerve
#   battery script (trajectory_tda/scripts/run_mcbif_weighted_nerve_battery.py):
#   same seed -> same statistic vector on a toy object; tau=1 battery grids
#   equal the merged hilbert_grid_h0_h1 module; the two-sided p, BH-FDR, and
#   locked decision rule behave per the pre-registration.
"""Tests for the confirmatory weighted-nerve MCbiF battery core."""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from trajectory_tda.scripts.run_mcbif_weighted_nerve_battery import (
    SEED,
    W,
    _init_worker,
    bh_adjust,
    build_global_nerve,
    buckets_for_tau,
    complete_adjacent_fraction,
    decide_verdict,
    eval_subset,
    grid_from_cache,
    needed_subsets,
    null_orderings,
    two_sided_p,
)
from trajectory_tda.topology.mcbif_nerve import hf_statistics, hilbert_grid_h0_h1


def _toy_partitions(seed: int = 0, n_units: int = 30, n_labels: int = 3) -> list[NDArray[np.int64]]:
    """A small synthetic W-wave labelling with enough overlap to form cycles."""
    rng = np.random.default_rng(seed)
    return [rng.integers(0, n_labels, size=n_units).astype(np.int64) for _ in range(W)]


def _statistic_vector(partitions: list[NDArray[np.int64]], orderings: list[tuple[int, ...]], tau: int) -> list[dict]:
    """Statistic rows for the given orderings via the battery's subset cache path."""
    nerve = build_global_nerve(partitions)
    eb, tb = buckets_for_tau(nerve, tau)
    _init_worker(eb, tb, nerve["wave_start"], nerve["n_labels"])
    cache: dict[frozenset[int], tuple[int, int]] = {}
    for sub in needed_subsets(orderings):
        _, b0, b1 = eval_subset(sub)
        cache[frozenset(sub)] = (b0, b1)
    rows = []
    for seq in orderings:
        hf0, hf1 = grid_from_cache(seq, cache)
        rows.append(hf_statistics(hf0, hf1))
    return rows


def test_same_seed_same_statistic_vector() -> None:
    """Determinism gate: two fresh runs with the same seed agree exactly."""
    partitions = _toy_partitions()
    observed = tuple(range(W))
    draws = null_orderings()[:5]
    first = _statistic_vector(partitions, [observed, *draws], tau=2)
    second = _statistic_vector(partitions, [observed, *draws], tau=2)
    assert first == second


def test_null_orderings_are_the_preregistered_draws() -> None:
    """Per-draw seeds are 42+b: the first draws match default_rng directly."""
    draws = null_orderings()
    assert len(draws) == 1000
    for b in (0, 1, 999):
        expected = tuple(int(x) for x in np.random.default_rng(SEED + b).permutation(W))
        assert draws[b] == expected
    assert len({d for d in draws}) > 900  # collisions in 13! space are vanishingly rare


def test_tau1_grid_matches_module() -> None:
    """At tau=1 the battery's cached grids equal hilbert_grid_h0_h1 exactly."""
    partitions = _toy_partitions(seed=7)
    observed = tuple(range(W))
    nerve = build_global_nerve(partitions)
    eb, tb = buckets_for_tau(nerve, 1)
    _init_worker(eb, tb, nerve["wave_start"], nerve["n_labels"])
    cache: dict[frozenset[int], tuple[int, int]] = {}
    for sub in needed_subsets([observed]):
        _, b0, b1 = eval_subset(sub)
        cache[frozenset(sub)] = (b0, b1)
    hf0, hf1 = grid_from_cache(observed, cache)
    ref = hilbert_grid_h0_h1(partitions)
    np.testing.assert_array_equal(hf0, ref["HF0"])
    np.testing.assert_array_equal(hf1, ref["HF1"])


def test_thresholding_reduces_or_keeps_edges() -> None:
    """tau=2 buckets are a subset of tau=1 buckets (support thresholding)."""
    partitions = _toy_partitions(seed=3)
    nerve = build_global_nerve(partitions)
    eb1, tb1 = buckets_for_tau(nerve, 1)
    eb2, tb2 = buckets_for_tau(nerve, 2)
    n1 = sum(len(v) for v in eb1.values())
    n2 = sum(len(v) for v in eb2.values())
    assert n2 <= n1
    t1 = sum(len(v) for v in tb1.values())
    t2 = sum(len(v) for v in tb2.values())
    assert t2 <= t1
    frac1, _ = complete_adjacent_fraction(nerve, 1)
    frac2, _ = complete_adjacent_fraction(nerve, 2)
    assert frac2 <= frac1


def test_two_sided_p_convention() -> None:
    """p_two = min(1, 2*min(p_lower, p_upper)) with the (r+1)/(n+1) floor."""
    nulls = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    res = two_sided_p(nulls, 10.0)  # above every null
    assert res["p_upper"] == pytest.approx(1 / 10)
    assert res["p_lower"] == pytest.approx(1.0)
    assert res["p_two"] == pytest.approx(2 / 10)
    res = two_sided_p(nulls, 5.0)  # dead centre
    assert res["p_two"] == pytest.approx(1.0)
    for value in (res["p_lower"], res["p_upper"], res["p_two"]):
        assert 1 / 10 <= value <= 1.0


def test_bh_adjust_two_hypotheses() -> None:
    """BH across two substrates: adj_(2) = p_(2), adj_(1) = min(2 p_(1), adj_(2))."""
    assert bh_adjust([0.01, 0.04]) == pytest.approx([0.02, 0.04])
    assert bh_adjust([0.03, 0.03]) == pytest.approx([0.03, 0.03])
    assert bh_adjust([0.6, 0.9]) == pytest.approx([0.9, 0.9])
    single = bh_adjust([0.02])
    assert single == pytest.approx([0.02])


def test_decide_verdict_locked_rule() -> None:
    """The four locked outcomes, plus the both-reject-one-gated cell."""

    def arm(p_fdr: float, rho: float = 0.3) -> dict[str, float]:
        return {"p_fdr": p_fdr, "rho_ari": rho, "rho_ce": -rho}

    additive = decide_verdict({"integration": arm(0.002), "bhps": arm(0.01)})
    assert additive["verdict"] == "additive"

    negative = decide_verdict({"integration": arm(0.4), "bhps": arm(0.8)})
    assert negative["verdict"] == "negative"

    partial = decide_verdict({"integration": arm(0.002), "bhps": arm(0.4)})
    assert partial["verdict"] == "partial-signal"

    redundant = decide_verdict({"integration": arm(0.002, rho=0.99), "bhps": arm(0.4)})
    assert redundant["verdict"] == "redundant"

    # Both reject, gates pass on exactly one: one effective rejection -> partial-signal.
    mixed = decide_verdict({"integration": arm(0.002), "bhps": arm(0.01, rho=0.99)})
    assert mixed["verdict"] == "partial-signal"
    assert mixed["per_arm"]["bhps"]["rejected"] and not mixed["per_arm"]["bhps"]["gates_pass"]

    # A Gate-0 infeasible arm has no defined verdict: BLOCKED arms escalate.
    blocked = {"integration": arm(0.002), "bhps": {**arm(0.01), "infeasible": True}}
    with pytest.raises(ValueError, match="BLOCKED arms escalate"):
        decide_verdict(blocked)


def test_p_floor_respected_at_full_b() -> None:
    """At B=1000 no p can fall below 1/1001 (the permutation floor)."""
    nulls = np.arange(1000, dtype=float)
    res = two_sided_p(nulls, 1e12)
    assert res["p_upper"] == pytest.approx(1 / 1001)
    assert res["p_two"] == pytest.approx(2 / 1001)
    assert not math.isclose(res["p_two"], 0.0)
