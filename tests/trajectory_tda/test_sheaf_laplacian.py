# Research context: TDA-Research/00-Meta/Discovery/sheaf-laplacian-employment-dispatch-prereg-2026-07-10.md
# Purpose: Deterministic unit tests for the cellular-sheaf Laplacian module used
#   by the LOCKED sheaf-energy confirmatory battery. Every case is hand-checkable
#   on a toy graph — no data files, no RNG, no network.
"""Unit tests for ``trajectory_tda.topology.sheaf_laplacian``."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from trajectory_tda.topology.sheaf_laplacian import (
    build_transition_graph,
    occupancy_from_counts,
    occupancy_signal,
    per_trajectory_state_counts,
    sheaf_energy,
    sheaf_laplacian_matrix,
    sheaf_spectrum,
    stalk_signals,
)

N_STATES = 3


def _toy_sequences() -> list[NDArray[np.int64]]:
    """Three short sequences over a 3-state alphabet."""
    return [
        np.array([0, 1, 0, 1], dtype=np.int64),  # 0->1, 1->0, 0->1
        np.array([1, 2], dtype=np.int64),  # 1->2
        np.array([2], dtype=np.int64),  # no transitions (length 1)
    ]


# ── build_transition_graph ───────────────────────────────────────────────────


def test_build_transition_graph_symmetrises_and_zeroes_diagonal() -> None:
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)

    # Directed counts: 0->1 twice, 1->0 once, 1->2 once. Symmetrised:
    # w_01 = 2 + 1 = 3, w_12 = 1 + 0 = 1, w_02 = 0.
    expected = np.array([[0, 3, 0], [3, 0, 1], [0, 1, 0]], dtype=np.int64)
    np.testing.assert_array_equal(weights, expected)
    assert np.array_equal(weights, weights.T)
    assert np.all(np.diag(weights) == 0)
    assert edges == [(0, 1), (1, 2)]


def test_build_transition_graph_ignores_length_one_sequences() -> None:
    only_singletons = [np.array([0], dtype=np.int64), np.array([2], dtype=np.int64)]
    weights, edges = build_transition_graph(only_singletons, N_STATES)

    assert edges == []
    np.testing.assert_array_equal(weights, np.zeros((N_STATES, N_STATES), dtype=np.int64))


def test_build_transition_graph_self_transitions_do_not_create_edges() -> None:
    # A self-loop lands on the diagonal, which is explicitly zeroed: support
    # edges run between distinct states only.
    weights, edges = build_transition_graph([np.array([1, 1, 1], dtype=np.int64)], N_STATES)

    assert edges == []
    assert weights[1, 1] == 0


# ── occupancy_signal ─────────────────────────────────────────────────────────


def test_occupancy_signal_is_a_distribution_over_member_wave_positions() -> None:
    seqs = _toy_sequences()
    member = np.array([True, False, False])

    signal = occupancy_signal(seqs, member, N_STATES)

    # Sequence 0 is [0,1,0,1]: state 0 twice, state 1 twice, state 2 never.
    np.testing.assert_allclose(signal, [0.5, 0.5, 0.0])
    assert signal.sum() == pytest.approx(1.0)


def test_occupancy_signal_pools_all_member_rows() -> None:
    seqs = _toy_sequences()
    all_rows = np.array([True, True, True])

    signal = occupancy_signal(seqs, all_rows, N_STATES)

    # Pooled positions: 0 twice, 1 three times, 2 twice -> 7 total.
    np.testing.assert_allclose(signal, [2 / 7, 3 / 7, 2 / 7])


def test_occupancy_signal_empty_group_returns_zeros_not_nan() -> None:
    signal = occupancy_signal(_toy_sequences(), np.array([False, False, False]), N_STATES)

    np.testing.assert_array_equal(signal, np.zeros(N_STATES))
    assert not np.isnan(signal).any()


# ── per_trajectory_state_counts / occupancy_from_counts ──────────────────────


def test_per_trajectory_state_counts_rows_match_each_sequence() -> None:
    counts = per_trajectory_state_counts(_toy_sequences(), N_STATES)

    assert counts.shape == (3, N_STATES)
    np.testing.assert_array_equal(counts[0], [2, 2, 0])  # [0,1,0,1]
    np.testing.assert_array_equal(counts[1], [0, 1, 1])  # [1,2]
    np.testing.assert_array_equal(counts[2], [0, 0, 1])  # [2]


@pytest.mark.parametrize(
    "member",
    [
        np.array([True, False, False]),
        np.array([True, True, False]),
        np.array([True, True, True]),
        np.array([False, False, False]),  # empty group
    ],
)
def test_occupancy_from_counts_matches_occupancy_signal(member: NDArray[np.bool_]) -> None:
    """Binding equivalence: the vectorised battery path must equal the reference path."""
    seqs = _toy_sequences()
    counts = per_trajectory_state_counts(seqs, N_STATES)

    np.testing.assert_allclose(
        occupancy_from_counts(counts, member),
        occupancy_signal(seqs, member, N_STATES),
    )


# ── stalk_signals ────────────────────────────────────────────────────────────


def test_stalk_signals_orders_columns_by_group_names() -> None:
    seqs = _toy_sequences()
    members = {
        "a": np.array([True, False, False]),
        "b": np.array([False, True, False]),
    }

    signals = stalk_signals(seqs, members, ["a", "b"], N_STATES)
    swapped = stalk_signals(seqs, members, ["b", "a"], N_STATES)

    assert signals.shape == (N_STATES, 2)
    np.testing.assert_allclose(signals[:, 0], occupancy_signal(seqs, members["a"], N_STATES))
    np.testing.assert_allclose(signals[:, 1], occupancy_signal(seqs, members["b"], N_STATES))
    np.testing.assert_allclose(swapped, signals[:, ::-1])


# ── sheaf_energy ─────────────────────────────────────────────────────────────


def test_sheaf_energy_is_zero_for_a_constant_signal() -> None:
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    constant = np.tile(np.array([0.25, 0.75]), (N_STATES, 1))

    assert sheaf_energy(constant, weights, edges) == pytest.approx(0.0)


def test_sheaf_energy_matches_hand_computed_value() -> None:
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    signals = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])

    # edge (0,1) w=3: ||(1,0)-(0,1)||^2 = 2      -> 6
    # edge (1,2) w=1: ||(0,1)-(0,0)||^2 = 1      -> 1
    assert sheaf_energy(signals, weights, edges) == pytest.approx(7.0)


def test_sheaf_energy_ignores_non_support_edges() -> None:
    # w_02 == 0, so any disagreement between vertices 0 and 2 is unweighted and
    # must not contribute; only edges (0,1) and (1,2) carry energy.
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    signals = np.zeros((N_STATES, 1))
    signals[0, 0] = 1.0
    signals[2, 0] = -1.0

    # edge (0,1) w=3: (1-0)^2 = 1 -> 3 ; edge (1,2) w=1: (0-(-1))^2 = 1 -> 1
    assert sheaf_energy(signals, weights, edges) == pytest.approx(4.0)


def test_sheaf_energy_scales_quadratically_with_signal_amplitude() -> None:
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    signals = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])

    base = sheaf_energy(signals, weights, edges)
    scaled = sheaf_energy(3.0 * signals, weights, edges)

    assert scaled == pytest.approx(9.0 * base)


# ── sheaf_laplacian_matrix / energy identity ─────────────────────────────────


@pytest.mark.validation
def test_sheaf_laplacian_is_symmetric_psd_with_zero_row_sums() -> None:
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    n_groups = 2

    laplacian = sheaf_laplacian_matrix(weights, edges, N_STATES, n_groups)

    assert laplacian.shape == (N_STATES * n_groups, N_STATES * n_groups)
    np.testing.assert_allclose(laplacian, laplacian.T)
    np.testing.assert_allclose(laplacian.sum(axis=1), np.zeros(N_STATES * n_groups), atol=1e-12)
    assert np.linalg.eigvalsh(laplacian).min() > -1e-10


@pytest.mark.validation
def test_energy_equals_quadratic_form_of_the_sheaf_laplacian() -> None:
    """E_sheaf(x) == vec(x)^T L_F vec(x) — the identity that makes it a sheaf energy."""
    rng = np.random.default_rng(42)
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    n_groups = 4
    signals = rng.random((N_STATES, n_groups))

    laplacian = sheaf_laplacian_matrix(weights, edges, N_STATES, n_groups)
    vec = signals.ravel()  # row-major: index v * n_groups + g

    assert float(vec @ laplacian @ vec) == pytest.approx(sheaf_energy(signals, weights, edges))


# ── sheaf_spectrum ───────────────────────────────────────────────────────────


@pytest.mark.validation
def test_spectrum_repeats_each_graph_laplacian_eigenvalue_n_groups_times() -> None:
    """Identity restrictions make L_F = L_G (x) I_G, so the spectrum is degenerate."""
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)
    n_groups = 3

    scalar_spectrum = np.sort(np.linalg.eigvalsh(sheaf_laplacian_matrix(weights, edges, N_STATES, 1)))
    spectrum = sheaf_spectrum(weights, edges, N_STATES, n_groups)

    assert spectrum.shape == (N_STATES * n_groups,)
    np.testing.assert_allclose(spectrum, np.repeat(scalar_spectrum, n_groups), atol=1e-10)


@pytest.mark.validation
def test_spectrum_does_not_depend_on_the_stalk_signals() -> None:
    """The documented reason the pre-registration attaches no p-value to spectra."""
    weights, edges = build_transition_graph(_toy_sequences(), N_STATES)

    # sheaf_spectrum takes no signal argument at all; the connected component
    # count is the only structure it can see. Assert the invariant that follows:
    # a zero eigenvalue per component, per group coordinate.
    spectrum = sheaf_spectrum(weights, edges, N_STATES, 2)

    # The toy graph 0-1-2 is connected -> exactly one zero eigenvalue per group.
    assert int(np.sum(np.isclose(spectrum, 0.0, atol=1e-10))) == 2
