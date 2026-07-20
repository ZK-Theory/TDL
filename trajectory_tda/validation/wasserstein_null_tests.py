"""Diagram-level Wasserstein null tests for trajectory topology.

Stage 0 upgrade to Paper 1: replace the scalar total-persistence test
statistic with exact Wasserstein distances between persistence diagrams.
This addresses the core validity concern — total persistence is a scalar
that can mask substantive differences in diagram shape.

Two tests:
    1. diagram_wasserstein_pvalue: Overall test — Wasserstein distance
       between observed diagram and each null diagram, replacing the
       total-persistence comparison in the Markov memory ladder.

    2. stratified_wasserstein_test: Subgroup comparative test (§4.6
       upgrade) — Wasserstein distance between persistence diagrams of
       demographically-stratified trajectory subgroups, replacing the
       current bootstrap-p approach.

Primary backend is gudhi.hera.wasserstein_distance (Kerber-Morozov-Nigmetov
geometric matching; no POT dependency), called with delta=1e-8 so the
(1+delta) relative-error bound is exact to well below numerical precision.
Falls back to an exact scipy linear_sum_assignment solve of the canonical
augmented assignment if hera is unavailable (same estimand; O((n+m)^3), so
slower on large diagrams). The backend that actually ran is stamped in
WassersteinNullResult.method.

References:
    Robinson, A., & Turner, K. (2017). Hypothesis testing for topological
    data analysis. Journal of Applied and Computational Topology.

    Kerber, M., Morozov, D., & Nigmetjanow, A. (2017). Geometry helps
    to compare persistence diagrams. J. Exp. Algorithmics.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Relative-error tolerance passed to hera: the returned value is within a
# (1 + _HERA_DELTA) factor of the true distance, i.e. exact to ~1e-8.
_HERA_DELTA = 1e-8


def _resolve_backend() -> str:
    """Return the Wasserstein backend that _compute_wasserstein_distance will use.

    Returns:
        'hera' if gudhi's hera bindings import cleanly, else 'scipy'.
    """
    try:
        import gudhi.hera  # noqa: F401

        return "hera"
    except ImportError:
        return "scipy"


def _compute_wasserstein_distance(
    diagram_a: NDArray[np.float64],
    diagram_b: NDArray[np.float64],
    order: int = 2,
) -> float:
    """Compute Wasserstein distance between two persistence diagrams.

    Primary path is gudhi.hera.wasserstein_distance (exact up to a 1e-8
    relative delta; no POT dependency — the POT-backed gudhi.wasserstein
    module is deliberately not used, see APM Failure Inventory Class 1).
    Falls back to a scipy linear_sum_assignment solve if hera is
    unavailable.

    Args:
        diagram_a: Persistence diagram, shape (n_pairs, 2) with (birth, death).
            Infinite death values should be filtered before passing.
        diagram_b: Second persistence diagram, same format.
        order: Wasserstein order. 2 is standard (matches Perslay literature).

    Returns:
        Wasserstein-`order` distance between the two diagrams.
    """
    # Filter infinite deaths
    finite_a = diagram_a[np.isfinite(diagram_a).all(axis=1)]
    finite_b = diagram_b[np.isfinite(diagram_b).all(axis=1)]

    try:
        import gudhi.hera

        dist = gudhi.hera.wasserstein_distance(finite_a, finite_b, order=order, internal_p=2, delta=_HERA_DELTA)
        return float(dist)

    except ImportError:
        warnings.warn(
            "gudhi.hera not available; falling back to the exact scipy "
            "Hungarian solve (same estimand, O((n+m)^3) — slow on large diagrams). "
            "Install gudhi with hera support for fast exact distances: pip install gudhi",
            stacklevel=2,
        )
        return _scipy_wasserstein_exact(finite_a, finite_b, order)


def _scipy_wasserstein_exact(
    diagram_a: NDArray[np.float64],
    diagram_b: NDArray[np.float64],
    order: int = 2,
) -> float:
    """Exact Wasserstein distance via the canonical augmented assignment.

    Rows are A's n points plus m diagonal slots; columns are B's m points
    plus n diagonal slots. Real-real cost is the Euclidean (internal_p=2)
    ground distance to the ``order``-th power, real-diagonal cost is the
    point's distance to the diagonal (persistence / sqrt(2)) to the
    ``order``-th power (uniform across slots), and the diagonal-diagonal
    block is zero — the zero block is what makes the reduction exact (both
    slots "unused"). Matches shared/math_invariants.py::wasserstein_exact_small
    and gudhi with internal_p=2; the Hungarian solve is O((n+m)^3), so prefer
    gudhi on large diagrams.

    Args:
        diagram_a: Finite persistence pairs, shape (n, 2).
        diagram_b: Finite persistence pairs, shape (m, 2).
        order: Wasserstein order.

    Returns:
        Exact Wasserstein-`order` distance.
    """
    from scipy.optimize import linear_sum_assignment

    n, m = len(diagram_a), len(diagram_b)
    if n == 0 and m == 0:
        return 0.0

    cost = np.zeros((n + m, m + n))
    if n and m:
        diff = diagram_a[:, None, :] - diagram_b[None, :, :]
        cost[:n, :m] = np.linalg.norm(diff, axis=2) ** order
    if n:
        diag_dist_a = (diagram_a[:, 1] - diagram_a[:, 0]) / np.sqrt(2.0)
        cost[:n, m:] = (diag_dist_a**order)[:, None]
    if m:
        diag_dist_b = (diagram_b[:, 1] - diagram_b[:, 0]) / np.sqrt(2.0)
        cost[n:, :m] = (diag_dist_b**order)[None, :]

    row_ind, col_ind = linear_sum_assignment(cost)
    total_cost = cost[row_ind, col_ind].sum()
    return float(total_cost ** (1.0 / order))


@dataclass
class WassersteinNullResult:
    """Result from a diagram-level Wasserstein null test.

    Attributes:
        observed_distance: Wasserstein distance of observed diagram from
            the centroid/expected null.
        null_distances: Wasserstein distances from each null diagram.
        p_value: Fraction of null distances exceeding observed (one-sided).
        z_score: Standardised effect size vs. null distribution.
        wasserstein_order: The Wasserstein order used.
        n_null_simulations: Number of null diagrams tested.
        method: 'hera' (exact, fast) or 'scipy' (exact Hungarian solve, slow
            on large diagrams).
    """

    observed_distance: float
    null_distances: NDArray[np.float64]
    p_value: float
    z_score: float
    wasserstein_order: int
    n_null_simulations: int
    method: str


def diagram_wasserstein_pvalue(
    observed_diagram: NDArray[np.float64],
    null_diagrams: list[NDArray[np.float64]],
    wasserstein_order: int = 2,
) -> WassersteinNullResult:
    """Test observed persistence diagram against a null distribution of diagrams.

    Replaces the total-persistence test statistic in the Markov memory ladder
    (Stage 0 upgrade). For each null simulation, compute the Wasserstein
    distance between the null diagram and the Fréchet mean of the null
    distribution; then compare the observed diagram's distance from that mean.

    In practice (following Robinson-Turner 2017), we compute the Wasserstein
    distance between the observed diagram and each null diagram directly,
    treating the distribution of these distances as the null.

    Args:
        observed_diagram: Persistence diagram from observed trajectories,
            shape (n_pairs, 2) with (birth, death) columns.
        null_diagrams: List of persistence diagrams from null simulations.
        wasserstein_order: Wasserstein order p (2 is standard).

    Returns:
        WassersteinNullResult with p-value and z-score.
    """
    method = _resolve_backend()

    # Observed test statistic: mean Wasserstein distance from the observed
    # diagram to each null diagram.
    obs_to_null = np.array(
        [_compute_wasserstein_distance(observed_diagram, nd, order=wasserstein_order) for nd in null_diagrams]
    )
    observed_distance = float(obs_to_null.mean())

    # Null reference distribution: for each null diagram, compute its mean
    # pairwise distance to all other null diagrams (leave-one-out estimator).
    # This measures how far a typical null is from the null cloud, providing
    # the correct reference for comparison (Robinson-Turner 2017, §3.1).
    n_null = len(null_diagrams)
    null_test_stats = np.zeros(n_null)
    for i in range(n_null):
        dists_i = [
            _compute_wasserstein_distance(null_diagrams[i], null_diagrams[j], order=wasserstein_order)
            for j in range(n_null)
            if j != i
        ]
        null_test_stats[i] = float(np.mean(dists_i)) if dists_i else 0.0

    null_mean = float(null_test_stats.mean())
    null_std = float(null_test_stats.std())
    z_score = (observed_distance - null_mean) / (null_std + 1e-10)
    p_value = float((null_test_stats >= observed_distance).mean())

    logger.info(
        "Wasserstein null test: observed distance=%.4f, null mean=%.4f, z=%.3f, p=%.4f (%s)",
        observed_distance,
        null_mean,
        z_score,
        p_value,
        method,
    )

    return WassersteinNullResult(
        observed_distance=observed_distance,
        null_distances=obs_to_null,
        p_value=p_value,
        z_score=z_score,
        wasserstein_order=wasserstein_order,
        n_null_simulations=len(null_diagrams),
        method=method,
    )


@dataclass
class StratifiedWassersteinResult:
    """Result from a stratified (subgroup) Wasserstein comparison.

    Attributes:
        group_labels: Labels for each subgroup.
        pairwise_distances: Wasserstein distance matrix between subgroup diagrams.
        permutation_p_values: P-values from permutation test for each pair.
        n_permutations: Number of permutations used.
    """

    group_labels: list[str]
    pairwise_distances: NDArray[np.float64]
    permutation_p_values: NDArray[np.float64]
    n_permutations: int


def stratified_wasserstein_test(
    diagrams_by_group: dict[str, NDArray[np.float64]],
    group_memberships: NDArray[np.int64],
    all_points: NDArray[np.float64],
    n_permutations: int = 1000,
    wasserstein_order: int = 2,
    random_seed: int = 42,
) -> StratifiedWassersteinResult:
    """Permutation test for Wasserstein distance between subgroup diagrams.

    Replaces the bootstrap-p approach in §4.6 of Paper 1 (Stage 0 upgrade).
    For each pair of demographic subgroups, tests whether the Wasserstein
    distance between their persistence diagrams exceeds what is expected
    under random reassignment of group membership.

    This follows the Robinson-Turner (2017) permutation framework directly,
    using exact Wasserstein distances rather than scalar summaries.

    Args:
        diagrams_by_group: Dict mapping group label → persistence diagram
            (shape (n_pairs, 2)) for each subgroup.
        group_memberships: Integer array of group assignment for each
            individual in the full sample, shape (n_individuals,).
        all_points: The full embedded point cloud from which subgroup
            diagrams were computed, shape (n_individuals, n_dims).
            Used to simulate null diagrams via permutation.
        n_permutations: Number of permutation replicates.
        wasserstein_order: Wasserstein order p.
        random_seed: RNG seed for reproducibility.

    Returns:
        StratifiedWassersteinResult with pairwise p-values.
    """
    rng = np.random.default_rng(random_seed)
    labels = list(diagrams_by_group.keys())
    n_groups = len(labels)

    observed_dists = np.zeros((n_groups, n_groups))
    for i, label_i in enumerate(labels):
        for j, label_j in enumerate(labels):
            if i >= j:
                continue
            d = _compute_wasserstein_distance(
                diagrams_by_group[label_i],
                diagrams_by_group[label_j],
                order=wasserstein_order,
            )
            observed_dists[i, j] = observed_dists[j, i] = d

    logger.info("Running %d permutations for %d groups...", n_permutations, n_groups)
    perm_counts = np.zeros((n_groups, n_groups))

    # Import ripser once here for efficiency
    try:
        import ripser

        _has_ripser = True
    except ImportError as exc:
        logger.error(
            "ripser not available; stratified Wasserstein test cannot compute null "
            "diagrams. Install ripser to run this test."
        )
        raise ImportError("ripser is required to compute null diagrams for the stratified Wasserstein test.") from exc

    for perm_idx in range(n_permutations):
        shuffled = rng.permutation(group_memberships)
        perm_dists = np.zeros((n_groups, n_groups))

        # Precompute permuted group points and diagrams once per permutation
        group_points = []
        group_valid = []
        for i in range(n_groups):
            mask_i = shuffled == i
            pts_i = all_points[mask_i]
            group_points.append(pts_i)
            group_valid.append(len(pts_i) >= 5)  # noqa: PLR2004

        group_diagrams: list[NDArray[np.float64] | None] = [None] * n_groups
        if _has_ripser:
            for i in range(n_groups):
                if not group_valid[i]:
                    continue
                dgms_i = ripser.ripser(group_points[i], maxdim=1)["dgms"][1]
                group_diagrams[i] = np.array([[b, d] for b, d in dgms_i if np.isfinite(d)])

        for i, label_i in enumerate(labels):
            for j, label_j in enumerate(labels):
                if i >= j:
                    continue

                # Skip pairs where either group has too few points
                if not (group_valid[i] and group_valid[j]):
                    continue

                if _has_ripser:
                    diag_i = group_diagrams[i]
                    diag_j = group_diagrams[j]
                    if diag_i is None or diag_j is None:
                        continue
                    perm_d = _compute_wasserstein_distance(diag_i, diag_j, wasserstein_order)
                else:
                    perm_d = 0.0

                perm_dists[i, j] = perm_dists[j, i] = perm_d

        perm_counts += perm_dists >= observed_dists

        if (perm_idx + 1) % 100 == 0:
            logger.info("  Permutation %d/%d complete", perm_idx + 1, n_permutations)

    p_values = perm_counts / n_permutations

    return StratifiedWassersteinResult(
        group_labels=labels,
        pairwise_distances=observed_dists,
        permutation_p_values=p_values,
        n_permutations=n_permutations,
    )
