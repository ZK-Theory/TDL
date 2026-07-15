# Research context: TDA-Research/00-Meta/Discovery/sheaf-laplacian-employment-dispatch-prereg-2026-07-10.md
# Purpose: Cellular-sheaf Laplacian with identity restrictions over subgroup
#   occupancy stalks on the employment transition graph. Promotes the Spike 7
#   reference driver (scratch/discovery_spikes/spike-07-sheaf-cellular-laplacian-
#   employment/run_spike07.py, PASS 2026-07-10) into a tested production module
#   for the LOCKED confirmatory battery. Energy is the tested statistic; the
#   spectrum is exploratory-descriptive only (see module docstring for why).
"""Cellular-sheaf Laplacian on a weighted graph with identity restriction maps.

The sheaf here is the simplest non-trivial one the pre-registration locks: a
weighted graph ``G = (V, E, w)`` whose vertex stalks all carry the same space
``R^G`` (one coordinate per group), with **identity restriction maps** on every
edge. For a signal ``x`` assigning a vector ``x(v) in R^G`` to each vertex, the
sheaf Dirichlet energy is

    E_sheaf(x) = sum_{e = (u, v) in E} w_e * ||x(u) - x(v)||^2 .

Mathematical note (why energy is tested and the spectrum is not)
---------------------------------------------------------------
With identity restrictions the sheaf Laplacian factorises exactly as

    L_F = L_G (x) I_G

(Kronecker product), where ``L_G`` is the ordinary weighted graph Laplacian.
Its spectrum is therefore the spectrum of ``L_G`` with every eigenvalue repeated
``G`` times — it carries **no information beyond the scalar graph Laplacian**,
and in particular no information about the signals ``x``. The energy, by
contrast, is a genuine function of ``x`` (it is ``vec(x)^T L_F vec(x)``), which
is why the locked pre-registration tests energy only and reports the spectrum as
an exploratory descriptive with no p-value attached. ``sheaf_spectrum`` exposes
that degeneracy explicitly rather than hiding it.

This is not a learned model: the restriction maps are identities, fixed by the
pre-registration, never fitted.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "build_transition_graph",
    "occupancy_from_counts",
    "occupancy_signal",
    "per_trajectory_state_counts",
    "sheaf_energy",
    "sheaf_laplacian_matrix",
    "sheaf_spectrum",
    "stalk_signals",
]


def build_transition_graph(
    seqs_idx: list[NDArray[np.int64]],
    n_states: int,
) -> tuple[NDArray[np.int64], list[tuple[int, int]]]:
    """Build the symmetrised employment transition graph from index sequences.

    Edge weights are ``w_ij = count_ij + count_ji`` and support edges run between
    distinct states only (the diagonal is zeroed), exactly as C1 and Spike 7
    construct them.

    Args:
        seqs_idx: Per-trajectory integer state-index arrays.
        n_states: Number of states (vertices) in the graph.

    Returns:
        Tuple ``(W, edges)`` where ``W`` is the ``(n_states, n_states)``
        symmetric integer weight matrix with a zero diagonal, and ``edges`` lists
        the ``(i, j)`` pairs with ``i < j`` and ``W[i, j] > 0``.
    """
    counts = np.zeros((n_states, n_states), dtype=np.int64)
    for seq in seqs_idx:
        if len(seq) >= 2:
            np.add.at(counts, (seq[:-1], seq[1:]), 1)
    weights = counts + counts.T
    np.fill_diagonal(weights, 0)
    edges = [(i, j) for i in range(n_states) for j in range(i + 1, n_states) if weights[i, j] > 0]
    return weights, edges


def occupancy_signal(
    seqs_idx: list[NDArray[np.int64]],
    member: NDArray[np.bool_],
    n_states: int,
) -> NDArray[np.float64]:
    """State-occupancy distribution over all wave positions of the member rows.

    Args:
        seqs_idx: Per-trajectory integer state-index arrays.
        member: Boolean mask over trajectories selecting the group.
        n_states: Number of states.

    Returns:
        Length ``n_states`` array summing to 1.0, or all zeros when the group
        occupies no wave positions at all.
    """
    counts = np.zeros(n_states, dtype=np.float64)
    for i in np.flatnonzero(member):
        counts += np.bincount(seqs_idx[i], minlength=n_states)
    total = counts.sum()
    return counts / total if total > 0 else counts


def per_trajectory_state_counts(
    seqs_idx: list[NDArray[np.int64]],
    n_states: int,
) -> NDArray[np.int64]:
    """Per-trajectory state-occupancy counts, computed once and reused per draw.

    Occupancy is additive over trajectories, so a permutation battery can build
    this matrix once from the (never-permuted) sequences and then obtain any
    group's occupancy by summing the member rows. Only the *labels* move under a
    label-permutation null, never the sequences.

    Args:
        seqs_idx: Per-trajectory integer state-index arrays.
        n_states: Number of states.

    Returns:
        Array of shape ``(len(seqs_idx), n_states)``; entry ``(i, s)`` counts
        wave positions trajectory ``i`` spends in state ``s``.
    """
    counts = np.zeros((len(seqs_idx), n_states), dtype=np.int64)
    for i, seq in enumerate(seqs_idx):
        counts[i] = np.bincount(seq, minlength=n_states)
    return counts


def occupancy_from_counts(
    per_traj_counts: NDArray[np.int64],
    member: NDArray[np.bool_],
) -> NDArray[np.float64]:
    """Group occupancy distribution from precomputed per-trajectory counts.

    Vectorised equivalent of ``occupancy_signal``; see
    ``test_occupancy_from_counts_matches_occupancy_signal`` for the binding
    equivalence check.

    Args:
        per_traj_counts: ``(n_trajectories, n_states)`` from ``per_trajectory_state_counts``.
        member: Boolean mask over trajectories selecting the group.

    Returns:
        Length ``n_states`` array summing to 1.0, or all zeros for an empty group.
    """
    counts = per_traj_counts[member].sum(axis=0).astype(np.float64)
    total = counts.sum()
    return counts / total if total > 0 else counts


def stalk_signals(
    seqs_idx: list[NDArray[np.int64]],
    members: dict[str, NDArray[np.bool_]],
    group_names: list[str],
    n_states: int,
) -> NDArray[np.float64]:
    """Assemble the per-vertex stalk signal matrix.

    Args:
        seqs_idx: Per-trajectory integer state-index arrays.
        members: Group name -> boolean membership mask.
        group_names: Ordered group names; defines the stalk coordinate order.
        n_states: Number of states.

    Returns:
        Array of shape ``(n_states, n_groups)``; row ``v`` is the stalk vector
        ``x(v)`` and column ``g`` is group ``g``'s occupancy distribution.
    """
    return np.vstack([occupancy_signal(seqs_idx, members[g], n_states) for g in group_names]).T


def sheaf_energy(
    signals: NDArray[np.float64],
    weights: NDArray[np.int64],
    edges: list[tuple[int, int]],
) -> float:
    """Cellular-sheaf Dirichlet energy with identity restrictions.

    Computes ``sum_e w_e * ||x(u) - x(v)||^2`` over the support edges.

    Args:
        signals: ``(n_states, n_groups)`` stalk signal matrix from ``stalk_signals``.
        weights: Symmetric edge-weight matrix from ``build_transition_graph``.
        edges: Support edge list ``(i, j)`` with ``i < j``.

    Returns:
        The scalar sheaf energy.
    """
    return float(sum(weights[i, j] * np.sum((signals[i] - signals[j]) ** 2) for i, j in edges))


def sheaf_laplacian_matrix(
    weights: NDArray[np.int64],
    edges: list[tuple[int, int]],
    n_states: int,
    n_groups: int,
) -> NDArray[np.float64]:
    """Dense sheaf Laplacian ``L_F = L_G (x) I_G`` for identity restrictions.

    Provided so the energy identity ``E_sheaf(x) == vec(x)^T L_F vec(x)`` is
    directly checkable, and so the spectrum's structural degeneracy is explicit.

    Args:
        weights: Symmetric edge-weight matrix.
        edges: Support edge list ``(i, j)`` with ``i < j``.
        n_states: Number of vertices.
        n_groups: Stalk dimension (number of groups).

    Returns:
        Array of shape ``(n_states * n_groups, n_states * n_groups)``. Index
        ``v * n_groups + g`` is vertex ``v``'s coordinate ``g``, i.e. the
        row-major flattening of the ``(n_states, n_groups)`` signal matrix.
    """
    graph_laplacian = np.zeros((n_states, n_states), dtype=np.float64)
    for i, j in edges:
        w = float(weights[i, j])
        graph_laplacian[i, i] += w
        graph_laplacian[j, j] += w
        graph_laplacian[i, j] -= w
        graph_laplacian[j, i] -= w
    return np.kron(graph_laplacian, np.eye(n_groups, dtype=np.float64))


def sheaf_spectrum(
    weights: NDArray[np.int64],
    edges: list[tuple[int, int]],
    n_states: int,
    n_groups: int,
) -> NDArray[np.float64]:
    """Ascending eigenvalues of the sheaf Laplacian (exploratory descriptive only).

    Under identity restrictions this equals the weighted graph Laplacian spectrum
    with each eigenvalue repeated ``n_groups`` times, and is independent of the
    stalk signals. The locked pre-registration attaches **no p-value** to it.

    Args:
        weights: Symmetric edge-weight matrix.
        edges: Support edge list ``(i, j)`` with ``i < j``.
        n_states: Number of vertices.
        n_groups: Stalk dimension.

    Returns:
        Ascending eigenvalues, length ``n_states * n_groups``.
    """
    laplacian = sheaf_laplacian_matrix(weights, edges, n_states, n_groups)
    return np.sort(np.linalg.eigvalsh(laplacian))
