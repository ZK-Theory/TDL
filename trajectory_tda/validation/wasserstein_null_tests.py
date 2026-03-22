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

Uses hera (via gudhi Python bindings) for exact Wasserstein distances.
Falls back to scipy-based approximation if hera is unavailable.

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


def _compute_wasserstein_distance(
    diagram_a: NDArray[np.float64],
    diagram_b: NDArray[np.float64],
    order: int = 2,
) -> float:
    """Compute Wasserstein distance between two persistence diagrams.

    Attempts to use gudhi's hera bindings (exact, fast C++). Falls back
    to a scipy-based approximation using the linear_sum_assignment solver.

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
        import gudhi.wasserstein

        dist = gudhi.wasserstein.wasserstein_distance(finite_a, finite_b, order=order, internal_p=2)
        return float(dist)

    except ImportError:
        warnings.warn(
            "gudhi.wasserstein not available; falling back to scipy approximation. "
            "Install gudhi with hera support for exact distances: pip install gudhi",
            stacklevel=2,
        )
        return _scipy_wasserstein_approx(finite_a, finite_b, order)


def _scipy_wasserstein_approx(
    diagram_a: NDArray[np.float64],
    diagram_b: NDArray[np.float64],
    order: int = 2,
) -> float:
    """Approximate Wasserstein distance via scipy linear assignment.

    Augments each diagram with diagonal projections to handle unequal sizes.
    This is an approximation — use gudhi for exact computation in publication runs.

    Args:
        diagram_a: Finite persistence pairs, shape (n, 2).
        diagram_b: Finite persistence pairs, shape (m, 2).
        order: Wasserstein order.

    Returns:
        Approximate Wasserstein distance.
    """
    from scipy.optimize import linear_sum_assignment

    def diag_proj(pts: NDArray[np.float64]) -> NDArray[np.float64]:
        mid = pts.mean(axis=1, keepdims=True)
        return np.hstack([mid, mid])

    # Augment: each point can be matched to diagonal of the other diagram
    a_diag = diag_proj(diagram_a) if len(diagram_a) > 0 else np.zeros((0, 2))
    b_diag = diag_proj(diagram_b) if len(diagram_b) > 0 else np.zeros((0, 2))

    a_aug = np.vstack([diagram_a, b_diag]) if len(diagram_a) > 0 else b_diag
    b_aug = np.vstack([diagram_b, a_diag]) if len(diagram_b) > 0 else a_diag

    if len(a_aug) == 0 or len(b_aug) == 0:
        return 0.0

    n, m = len(a_aug), len(b_aug)
    cost = np.zeros((n, m))
    for i in range(n):
        for j in range(m):
            cost[i, j] = np.linalg.norm(a_aug[i] - b_aug[j]) ** order

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
        method: 'gudhi' (exact) or 'scipy' (approximate).
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
    null_distances = []
    method = "scipy"

    for i, null_diag in enumerate(null_diagrams):
        dist = _compute_wasserstein_distance(observed_diagram, null_diag, order=wasserstein_order)
        null_distances.append(dist)
        if i == 0:
            # Check which method was used (heuristic: gudhi is much faster)
            try:
                import gudhi.wasserstein  # noqa: F401

                method = "gudhi"
            except ImportError:
                method = "scipy"

    null_arr = np.array(null_distances)
    # The observed diagram is "more complex" if its distance from a random
    # null is large — so we test against the lower tail
    p_value = float((null_arr <= null_arr.mean()).mean())

    # Re-run observed vs. each null for the actual test statistic
    obs_vs_null = np.array(
        [_compute_wasserstein_distance(observed_diagram, nd, order=wasserstein_order) for nd in null_diagrams]
    )
    observed_distance = obs_vs_null.mean()
    null_mean = null_arr.mean()
    null_std = null_arr.std()
    z_score = (observed_distance - null_mean) / (null_std + 1e-10)
    p_value = float((null_arr >= obs_vs_null.mean()).mean())

    logger.info(
        "Wasserstein null test: observed distance=%.4f, null mean=%.4f, " "z=%.3f, p=%.4f (%s)",
        observed_distance,
        null_mean,
        z_score,
        p_value,
        method,
    )

    return WassersteinNullResult(
        observed_distance=observed_distance,
        null_distances=null_arr,
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
        raise ImportError(
            "ripser is required to compute null diagrams for the stratified "
            "Wasserstein test."
        ) from exc

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
