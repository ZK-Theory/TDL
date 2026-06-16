"""Toy STRAND persistence-survival compute checks."""

from __future__ import annotations

import math

import numpy as np
import pytest

from trajectory_tda.discovery.strand_spike import (
    compute_strand_cell,
    finite_lifetimes,
    monte_carlo_upper_tail_pvalue,
    survival_area_distance,
)


def test_finite_lifetimes_rejects_invalid_diagram_rows() -> None:
    diagram = np.array([[0.0, 2.0], [1.0, 4.5], [0.0, math.inf]])

    lifetimes = finite_lifetimes(diagram)

    assert lifetimes.tolist() == [2.0, 3.5]

    with pytest.raises(AssertionError, match="death values must exceed birth"):
        finite_lifetimes(np.array([[1.0, 1.0]]))


def test_survival_area_distance_is_exact_and_symmetric() -> None:
    first = np.array([1.0, 3.0])
    second = np.array([2.0, 4.0])

    assert survival_area_distance(first, second) == pytest.approx(1.0)
    assert survival_area_distance(second, first) == pytest.approx(1.0)
    assert survival_area_distance(first, first) == pytest.approx(0.0)


def test_monte_carlo_upper_tail_pvalue_uses_bias_corrected_denominator() -> None:
    pvalue = monte_carlo_upper_tail_pvalue(2.5, [0.5, 1.0, 3.0])

    assert pvalue == pytest.approx(0.5)


def test_compute_strand_cell_uses_null_null_reference_distribution() -> None:
    observed = np.array([[0.0, 5.0], [0.0, 6.0]])
    nulls = [
        np.array([[0.0, 1.0], [0.0, 2.0]]),
        np.array([[0.0, 1.5], [0.0, 2.5]]),
        np.array([[0.0, 2.0], [0.0, 3.0]]),
    ]

    cell = compute_strand_cell(observed, nulls, max_null_diagrams=3)

    assert cell["null_diagrams_used"] == 3
    assert cell["observed_features"] == 2
    assert cell["null_null_pairs_used"] == 3
    assert cell["null_perturbs_input"] is True
    assert cell["observed_vs_null_statistic"] > cell["null_null_statistic_mean"]
    assert cell["p_value"] == pytest.approx(0.25)
