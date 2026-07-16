"""Tests for the promoted deprivation scale-coherence statistic and null."""

from __future__ import annotations

import numpy as np

from poverty_tda.topology import deprivation_scale_coherence as coherence


def test_spatialised_null_permutes_raw_vectors_then_uses_observed_pipeline(monkeypatch) -> None:
    raw = np.arange(28, dtype=np.float64).reshape(4, 7)
    closed_neighbours = [np.array([i], dtype=np.intp) for i in range(4)]
    seen: list[np.ndarray] = []

    def fake_statistic(values: np.ndarray, neighbours: list[np.ndarray]) -> dict[str, object]:
        seen.append(values.copy())
        assert neighbours is closed_neighbours
        return {"h1_total_area": 3.0}

    monkeypatch.setattr(coherence, "scale_coherence_statistic", fake_statistic)

    result = coherence.spatialised_null_draw(raw, closed_neighbours, draw_index=0)

    expected_order = np.random.default_rng(42).permutation(len(raw))
    assert len(seen) == 1
    np.testing.assert_array_equal(seen[0], raw[expected_order])
    assert result == {"h1_total_area": 3.0}


def test_empirical_tail_pvalues_are_inclusive_and_plus_one_corrected() -> None:
    null = np.array([1.0, 2.0, 3.0])

    p_lower, p_upper, percentile = coherence.empirical_tail_pvalues(null, observed=1.0)

    assert p_lower == 0.5
    assert p_upper == 1.0
    assert np.isclose(percentile, 100.0 / 3.0)


def test_benjamini_hochberg_adjustment_is_monotone_in_rank_order() -> None:
    adjusted = coherence.benjamini_hochberg(np.array([0.01, 0.04, 0.03, 0.002]))

    np.testing.assert_allclose(adjusted, np.array([0.02, 0.04, 0.04, 0.008]))


def test_null_validity_requires_partition_perturbation_and_positive_variance() -> None:
    observed = [np.zeros(4, dtype=np.int64), np.array([0, 0, 1, 1], dtype=np.int64)]
    perturbed = [np.array([0, 1, 0, 1], dtype=np.int64), observed[1].copy()]

    valid = coherence.null_validity_record(observed, perturbed, np.array([1.0, 2.0]))
    invariant = coherence.null_validity_record(observed, observed, np.array([1.0, 2.0]))
    degenerate = coherence.null_validity_record(observed, perturbed, np.array([1.0, 1.0]))

    assert valid["valid"] is True
    assert invariant["valid"] is False
    assert "partition_invariant" in invariant["reasons"]
    assert degenerate["valid"] is False
    assert "zero_null_variance" in degenerate["reasons"]


def test_redundancy_requires_both_locked_correlations_to_fail() -> None:
    h1 = np.array([1.0, 2.0, 3.0, 4.0])

    both_fail = coherence.redundancy_record(h1, h1.copy(), h1[::-1])
    one_passes = coherence.redundancy_record(h1, h1.copy(), np.array([1.0, 3.0, 2.0, 4.0]))

    assert both_fail["redundant"] is True
    assert one_passes["redundant"] is False
