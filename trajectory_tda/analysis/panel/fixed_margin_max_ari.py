# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Certified maximum-achievable ARI under fixed cluster-size margins for
#          the reviewer-B9 OM-vs-GMM normalisation (T1.23d). Replaces the trivial
#          whole-cluster-packing fallback (which returned a vacuous 1.0 when a row
#          exceeds every column capacity) with a rigorous achievable lower bound
#          and a rigorous upper bound on max Sum C(n_ij, 2) over the fixed-margin
#          integer transportation polytope.
"""Fixed-margin maximum-achievable ARI for two clusterings.

ARI's denominator and expectation term depend only on the cluster-size margins,
so maximising ARI over all contingency tables with fixed row sums (OM k=7 cluster
sizes) and column sums (GMM k=7 regime sizes) reduces to maximising the within-cell
pair count ``Sum_ij C(n_ij, 2) = (Sum_ij n_ij**2 - n) / 2`` over the integer
transportation polytope with those margins.

That objective is *convex*, so its maximum sits at a vertex of the polytope, and the
problem is NP-hard in general (the cell values are large here, so naive value-branch
B&B does not terminate, and no MILP/CP solver is available in this environment). We
therefore certify a **rigorous bracket**:

* **Achievable lower bound** -- a concrete feasible table found by a deterministic
  family of north-west-corner constructions (over sorted row/column orderings) each
  driven to a 2x2-exchange local optimum. The table is returned in the result so its
  margins and pair count can be re-verified independently; its pair count is, by
  construction, a valid lower bound on the true maximum.
* **Rigorous upper bound** -- the per-line *concentration relaxation*: relaxing the
  column-sum equalities to per-cell capacity bounds (or symmetrically the row sums)
  yields ``Sum_i maxsq(r_i; c)`` (resp. ``Sum_j maxsq(c_j; r)``), each a valid upper
  bound on ``Sum n_ij**2``; we take the tighter of the two.

When the two bounds coincide the maximum is certified exact. For the B9 OM-vs-GMM
margins they do not (achievable 0.8397 vs upper bound 0.8607), so the result is a
bracket -- far tighter than the trivial 1.0 and reported honestly as such.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# Deterministic-search budget: enumerate every column ordering when C! is at or
# below this, otherwise fall back to the sorted row/column orderings only. The B9
# 7x7 instance (5040 > 720) uses the nine sorted-order seeds, which reproduce the
# value found by exhaustive column-permutation search and 80,000 randomised
# restarts; small validation instances (C <= 6) are searched exhaustively.
COL_PERM_BUDGET = 720  # 6!


@dataclass(frozen=True)
class CertifiedMaxAri:
    """Certified fixed-margin maximum-achievable ARI (exact or bracketed)."""

    status: str  # "exact" or "bracket"
    ari_max_achievable: float  # ARI of the concrete achievable table (lower bound)
    ari_max_upper_bound: float  # rigorous upper bound on max ARI
    achievable_pair_overlap: int  # Sum_ij C(n_ij, 2) of the achievable table
    upper_bound_pair_overlap: int  # Sum_ij C(n_ij, 2) implied by the upper bound
    achieving_table: NDArray[np.int64]  # the certifying contingency table
    normalised_observed_ari: float  # observed / ari_max_achievable
    normalised_lower_bound: float  # observed / ari_max_upper_bound
    achievable_method: str
    upper_bound_method: str


def comb2(values: NDArray[np.int64] | int) -> NDArray[np.int64] | int:
    """Return n choose 2 for a scalar or an array of non-negative counts."""

    arr = np.asarray(values, dtype=np.int64)
    out = arr * (arr - 1) // 2
    if np.isscalar(values):
        return int(out)
    return out


def pair_overlap(table: NDArray[np.int64]) -> int:
    """Return Sum_ij C(table_ij, 2) -- within-cell co-clustered pair count."""

    return int(comb2(np.asarray(table, dtype=np.int64)).sum())


def ari_from_pair_overlap(
    sum_cells: int,
    row_counts: NDArray[np.int64],
    col_counts: NDArray[np.int64],
) -> float:
    """Adjusted Rand index implied by a within-cell pair count and fixed margins.

    Args:
        sum_cells: ``Sum_ij C(n_ij, 2)`` for some table with the given margins.
        row_counts: Row cluster sizes (OM k=7).
        col_counts: Column cluster sizes (GMM k=7).

    Returns:
        The ARI value; ``row_pairs``/``col_pairs``/expectation are fixed by the
        margins, so ARI is an increasing affine function of ``sum_cells``.
    """

    row_counts = np.asarray(row_counts, dtype=np.int64)
    col_counts = np.asarray(col_counts, dtype=np.int64)
    n = int(row_counts.sum())
    if n != int(col_counts.sum()):
        raise ValueError("row and column margins must sum to the same n")
    if n < 2:
        return 1.0
    row_pairs = int(comb2(row_counts).sum())
    col_pairs = int(comb2(col_counts).sum())
    total_pairs = comb2(n)
    expected = row_pairs * col_pairs / total_pairs
    max_index = 0.5 * (row_pairs + col_pairs)
    denom = max_index - expected
    if denom == 0:
        return 1.0 if sum_cells == max_index else 0.0
    return float((sum_cells - expected) / denom)


def _maxsq_line(total: int, caps_desc: list[int]) -> int:
    """Max Sum of squares placing ``total`` units into bins with the given caps.

    Concentration is optimal for a convex objective, so fill the largest-capacity
    bins first. ``caps_desc`` must be sorted descending.
    """

    s = 0
    rem = int(total)
    for cap in caps_desc:
        if rem <= 0:
            break
        take = cap if cap < rem else rem
        s += take * take
        rem -= take
    return s


def concentration_upper_bound_sumsq(
    row_counts: NDArray[np.int64],
    col_counts: NDArray[np.int64],
) -> int:
    """Rigorous upper bound on ``Sum_ij n_ij**2`` over the fixed-margin polytope.

    Relaxing the column-sum equalities to per-cell capacity bounds lets each row be
    packed independently into the full column capacities, giving
    ``Sum_i maxsq(r_i; col_caps)`` -- an upper bound on ``Sum n_ij**2``. The
    symmetric row relaxation gives ``Sum_j maxsq(c_j; row_caps)``. Both are valid;
    we return the tighter (smaller) one.
    """

    row_counts = np.asarray(row_counts, dtype=np.int64)
    col_counts = np.asarray(col_counts, dtype=np.int64)
    col_desc = sorted((int(c) for c in col_counts if c > 0), reverse=True)
    row_desc = sorted((int(r) for r in row_counts if r > 0), reverse=True)
    ub_rows = sum(_maxsq_line(int(r), col_desc) for r in row_counts)
    ub_cols = sum(_maxsq_line(int(c), row_desc) for c in col_counts)
    return min(ub_rows, ub_cols)


def _north_west(
    row_counts: NDArray[np.int64],
    col_counts: NDArray[np.int64],
    row_order: list[int],
    col_order: list[int],
) -> NDArray[np.int64]:
    """North-west-corner feasible table for the given row/column visit orders."""

    n_rows, n_cols = len(row_counts), len(col_counts)
    table = np.zeros((n_rows, n_cols), dtype=np.int64)
    rem_r = [int(row_counts[i]) for i in row_order]
    rem_c = [int(col_counts[j]) for j in col_order]
    i = j = 0
    while i < n_rows and j < n_cols:
        v = rem_r[i] if rem_r[i] < rem_c[j] else rem_c[j]
        table[row_order[i], col_order[j]] = v
        rem_r[i] -= v
        rem_c[j] -= v
        if rem_r[i] == 0:
            i += 1
        else:
            j += 1
    return table


def _two_opt(table: NDArray[np.int64]) -> NDArray[np.int64]:
    """Drive a feasible table to a 2x2-exchange local maximum of Sum n_ij**2.

    For any two rows and two columns the 2x2 sub-table sum of squares is convex in
    the mass shift t, so the optimum is at an endpoint; we apply every strictly
    improving extreme shift until none remains. Margins are preserved exactly.
    """

    mat = np.array(table, dtype=np.int64, copy=True)
    n_rows, n_cols = mat.shape
    improved = True
    while improved:
        improved = False
        for i1 in range(n_rows):
            for i2 in range(n_rows):
                if i1 == i2:
                    continue
                for j1 in range(n_cols):
                    for j2 in range(n_cols):
                        if j1 == j2:
                            continue
                        a = int(mat[i1, j1])
                        d = int(mat[i2, j2])
                        b = int(mat[i1, j2])
                        c = int(mat[i2, j1])
                        for t in (-min(a, d), min(b, c)):
                            if t == 0:
                                continue
                            if 2 * t * (a + d - b - c) + 4 * t * t > 0:
                                mat[i1, j1] += t
                                mat[i2, j2] += t
                                mat[i1, j2] -= t
                                mat[i2, j1] -= t
                                a = int(mat[i1, j1])
                                d = int(mat[i2, j2])
                                b = int(mat[i1, j2])
                                c = int(mat[i2, j1])
                                improved = True
    return mat


def _candidate_orders(counts: NDArray[np.int64]) -> list[list[int]]:
    """Deterministic visit orders: identity, descending, ascending by size."""

    idx = list(range(len(counts)))
    desc = sorted(idx, key=lambda k: -int(counts[k]))
    return [idx, desc, desc[::-1]]


def achievable_max_table(
    row_counts: NDArray[np.int64],
    col_counts: NDArray[np.int64],
) -> NDArray[np.int64]:
    """Best feasible table found by a deterministic NW + 2-opt search.

    The returned table is a concrete feasible point, so its pair count is a rigorous
    lower bound on the fixed-margin maximum. The search enumerates every column
    ordering when ``len(col_counts)! <= COL_PERM_BUDGET`` (paired with the three
    sorted row orderings), otherwise the three sorted column orderings; each NW seed
    is driven to a 2x2 local optimum and the best is kept. For the B9 7x7 instance
    the sorted-order seeds reproduce the value found by exhaustive column-permutation
    search and by 80,000 randomised restarts.
    """

    row_counts = np.asarray(row_counts, dtype=np.int64)
    col_counts = np.asarray(col_counts, dtype=np.int64)
    n_cols = len(col_counts)
    if math.factorial(n_cols) <= COL_PERM_BUDGET:
        col_orders: list[list[int]] = [list(p) for p in itertools.permutations(range(n_cols))]
    else:
        col_orders = _candidate_orders(col_counts)
    row_orders = _candidate_orders(row_counts)

    best_table: NDArray[np.int64] | None = None
    best_sumsq = -1
    for row_order in row_orders:
        for col_order in col_orders:
            table = _two_opt(_north_west(row_counts, col_counts, row_order, col_order))
            sumsq = int((table.astype(np.int64) ** 2).sum())
            if sumsq > best_sumsq:
                best_sumsq = sumsq
                best_table = table
    if best_table is None:
        raise RuntimeError("no feasible table found for the given fixed margins")
    return best_table


def certify_max_ari(
    row_counts: NDArray[np.int64],
    col_counts: NDArray[np.int64],
    observed_ari: float,
) -> CertifiedMaxAri:
    """Certify the fixed-margin maximum-achievable ARI as exact or a bracket.

    Args:
        row_counts: OM k=7 cluster sizes.
        col_counts: GMM k=7 regime sizes.
        observed_ari: The observed OM-vs-GMM ARI to normalise.

    Returns:
        A :class:`CertifiedMaxAri`. ``status`` is ``"exact"`` when the achievable
        lower bound meets the concentration upper bound, else ``"bracket"``.
    """

    row_counts = np.asarray(row_counts, dtype=np.int64)
    col_counts = np.asarray(col_counts, dtype=np.int64)
    n = int(row_counts.sum())

    table = achievable_max_table(row_counts, col_counts)
    if not (np.array_equal(table.sum(axis=1), row_counts) and np.array_equal(table.sum(axis=0), col_counts)):
        raise ValueError("achievable table violates the fixed margins")
    achievable_cells = pair_overlap(table)
    achievable_sumsq = 2 * achievable_cells + n

    ub_sumsq = concentration_upper_bound_sumsq(row_counts, col_counts)
    if ub_sumsq < achievable_sumsq:
        raise ValueError("upper bound below achievable value -- bound is invalid")
    ub_cells = (ub_sumsq - n) // 2

    ari_achievable = ari_from_pair_overlap(achievable_cells, row_counts, col_counts)
    ari_upper = ari_from_pair_overlap(ub_cells, row_counts, col_counts)
    status = "exact" if ub_sumsq == achievable_sumsq else "bracket"

    return CertifiedMaxAri(
        status=status,
        ari_max_achievable=ari_achievable,
        ari_max_upper_bound=ari_upper,
        achievable_pair_overlap=achievable_cells,
        upper_bound_pair_overlap=int(ub_cells),
        achieving_table=table,
        normalised_observed_ari=observed_ari / ari_achievable,
        normalised_lower_bound=observed_ari / ari_upper,
        achievable_method=(
            "Deterministic north-west-corner constructions over sorted row/column "
            "orderings (all column permutations enumerated for k<=6), each driven to "
            "a 2x2-exchange local maximum of Sum n_ij**2; best table retained. The "
            "table is returned so its margins and pair count are independently "
            "verifiable; its pair count is a rigorous lower bound on the maximum."
        ),
        upper_bound_method=(
            "Per-line concentration relaxation: relax the column-sum (resp. row-sum) "
            "equalities to per-cell capacity bounds and pack each row (resp. column) "
            "into the largest capacities; min of the two is a rigorous upper bound on "
            "Sum n_ij**2."
        ),
    )
