# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Theorem-derived mathematical invariant checks ("canaries") giving the ARS
#          invariants I1a/I1b/I1c/I2b/I2d/I8c their mathematical content. Spec:
#          docs/plans/strategy/Theorem-Derived-Invariant-Battery-2026-07-18.md
"""Theorem-derived invariant battery for persistence-diagram statistics.

Every check in this module asserts a mathematical fact about the estimand —
a closed-form identity, a feasibility bound, or a stability theorem — computed
through a code path independent of the solver under test (closed forms, scipy's
Hungarian algorithm, or an externally supplied bottleneck distance). A failed
verdict therefore implies an implementation error, not a statistical
fluctuation; the sole statistical member is :func:`double_null_calibration`,
which says so in its docstring.

Conventions: the production Wasserstein distance is exact optimal transport at
``order=2, internal_p=2`` (L2 ground metric on the plane). All functions here
are parameterised by ``(order, internal_p)`` with those defaults; under ground
metric L^p the distance from a point ``(b, d)`` to the diagonal is
``(d - b)/2 * 2**(1/p)`` (``pers/sqrt(2)`` for p=2, ``pers/2`` for p=inf).
Mixing conventions between a value and its check is itself the I1a failure
class this module exists to catch.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

Diagram = NDArray[np.float64]


@dataclass
class InvariantVerdict:
    """Outcome of one invariant check.

    Attributes:
        name: Battery identifier of the check (e.g. ``"W2.diagonal_bound"``).
        passed: True when the mathematical invariant holds for the input.
        detail: Numeric evidence (values, bounds, tolerances) for the verdict.
    """

    name: str
    passed: bool
    detail: dict[str, float | int | bool | str] = field(default_factory=dict)


def _as_diagram(diagram: Diagram) -> Diagram:
    arr = np.asarray(diagram, dtype=np.float64)
    if arr.size == 0:
        return arr.reshape(0, 2)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"diagram must have shape (n, 2); got {arr.shape}")
    return arr


def _persistences(diagram: Diagram) -> NDArray[np.float64]:
    dgm = _as_diagram(diagram)
    return dgm[:, 1] - dgm[:, 0]


def _diagonal_distance(pers: NDArray[np.float64], internal_p: float) -> NDArray[np.float64]:
    """L^p ground-metric distance from points with the given persistences to the diagonal."""
    if math.isinf(internal_p):
        return pers / 2.0
    return (pers / 2.0) * 2.0 ** (1.0 / internal_p)


def _ground_distances(a: Diagram, b: Diagram, internal_p: float) -> NDArray[np.float64]:
    diff = np.abs(a[:, None, :] - b[None, :, :])
    if math.isinf(internal_p):
        return diff.max(axis=-1)
    return (diff**internal_p).sum(axis=-1) ** (1.0 / internal_p)


# ---------------------------------------------------------------------------
# D1 — diagram well-formedness
# ---------------------------------------------------------------------------


def check_diagram_wellformed(diagram: Diagram) -> InvariantVerdict:
    """D1: shape (n, 2), no NaN, and birth <= death for every finite pair.

    Infinite-death pairs are admissible (they must be filtered or declared by
    the consumer) but NaN and death < birth are hard violations.

    Args:
        diagram: Persistence diagram, shape (n, 2) birth/death rows.

    Returns:
        Verdict with counts of violating rows in ``detail``.
    """
    dgm = _as_diagram(diagram)
    n_nan = int(np.isnan(dgm).any(axis=1).sum()) if dgm.size else 0
    finite = dgm[np.isfinite(dgm).all(axis=1)] if dgm.size else dgm
    n_inverted = int((finite[:, 1] < finite[:, 0]).sum()) if finite.size else 0
    n_infinite = int((~np.isfinite(dgm).all(axis=1)).sum() - n_nan) if dgm.size else 0
    return InvariantVerdict(
        name="D1.wellformed",
        passed=(n_nan == 0 and n_inverted == 0),
        detail={"n_points": int(dgm.shape[0]), "n_nan": n_nan, "n_inverted": n_inverted, "n_infinite": n_infinite},
    )


# ---------------------------------------------------------------------------
# W1 — closed-form distance to the empty diagram
# ---------------------------------------------------------------------------


def wasserstein_to_empty(diagram: Diagram, order: float = 2.0, internal_p: float = 2.0) -> float:
    """W1: exact ``W_q(D, empty)`` — every point transported to the diagonal.

    ``W_q(D, empty) = (sum_i diag_dist(pers_i)**q)**(1/q)`` with
    ``diag_dist(pers) = pers/2 * 2**(1/internal_p)``. No solver involved; any
    Wasserstein implementation must reproduce this value on ``(D, empty)``
    inputs to machine precision. Note the greedy rank-matcher *passes* this
    check (against the empty diagram it also sends everything to the
    diagonal) — W1 catches convention drift, W3–W5 catch matching errors.

    Args:
        diagram: Persistence diagram, shape (n, 2), finite pairs only.
        order: Wasserstein order q.
        internal_p: Ground-metric exponent p on the plane.

    Returns:
        The exact distance to the empty diagram.
    """
    pers = _persistences(diagram)
    if pers.size == 0:
        return 0.0
    costs = _diagonal_distance(pers, internal_p)
    return float((costs**order).sum() ** (1.0 / order))


# ---------------------------------------------------------------------------
# W2 — diagonal-transport upper bound (the I1b impossibility screen)
# ---------------------------------------------------------------------------


def diagonal_transport_bound(a: Diagram, b: Diagram, order: float = 2.0, internal_p: float = 2.0) -> float:
    """W2: upper bound ``W_q(A, B)^q <= W_q(A, empty)^q + W_q(B, empty)^q``.

    Sending every point of both diagrams to the diagonal is a feasible
    transport plan, so its cost bounds the optimum. For the production
    convention this is ``sqrt(0.5*sum pers_A**2 + 0.5*sum pers_B**2)`` —
    the I1b screen. A reported value above this bound is impossible, not
    merely suspicious.

    Args:
        a: First diagram, shape (n, 2).
        b: Second diagram, shape (m, 2).
        order: Wasserstein order q.
        internal_p: Ground-metric exponent p.

    Returns:
        The diagonal-transport bound.
    """
    ea = wasserstein_to_empty(a, order=order, internal_p=internal_p)
    eb = wasserstein_to_empty(b, order=order, internal_p=internal_p)
    return float((ea**order + eb**order) ** (1.0 / order))


def check_diagonal_bound(
    value: float,
    a: Diagram,
    b: Diagram,
    order: float = 2.0,
    internal_p: float = 2.0,
    rtol: float = 1e-9,
) -> InvariantVerdict:
    """W2: verdict on a reported distance against the diagonal-transport bound.

    Args:
        value: The reported ``W_q(A, B)`` under scrutiny.
        a: First diagram.
        b: Second diagram.
        order: Wasserstein order q the value claims.
        internal_p: Ground-metric exponent p the value claims.
        rtol: Relative floating-point slack on the bound.

    Returns:
        Verdict; ``passed`` is False when ``value`` exceeds the bound.
    """
    bound = diagonal_transport_bound(a, b, order=order, internal_p=internal_p)
    passed = value <= bound * (1.0 + rtol) + 1e-15
    return InvariantVerdict(
        name="W2.diagonal_bound",
        passed=bool(passed),
        detail={"value": float(value), "bound": bound, "rtol": rtol},
    )


# ---------------------------------------------------------------------------
# W3 — independent exact mini-oracle (scipy Hungarian, canonical reduction)
# ---------------------------------------------------------------------------


def wasserstein_exact_small(
    a: Diagram,
    b: Diagram,
    order: float = 2.0,
    internal_p: float = 2.0,
    max_points: int = 64,
) -> float:
    """W3: exact ``W_q`` for small diagrams via the canonical augmented matching.

    Rows are A's n points plus m diagonal slots; columns are B's m points plus
    n diagonal slots. Real–real cost is the L^p ground distance to the q-th
    power, real–diagonal cost is the point's diagonal distance to the q-th
    power (uniform across slots), and the diagonal–diagonal block is **zero**
    — the zero block is what makes this reduction exact (both slots unused).
    scipy's Hungarian algorithm then yields the optimum. This shares no code
    with the POT/EMD production path and is the decisive oracle against which
    any solver must agree on small randomized pairs.

    Args:
        a: First diagram, shape (n, 2), finite pairs only.
        b: Second diagram, shape (m, 2), finite pairs only.
        order: Wasserstein order q.
        internal_p: Ground-metric exponent p.
        max_points: Per-diagram size cap (Hungarian is O((n+m)^3)).

    Returns:
        The exact Wasserstein distance.

    Raises:
        ValueError: If either diagram exceeds ``max_points`` points.
    """
    da, db = _as_diagram(a), _as_diagram(b)
    n, m = da.shape[0], db.shape[0]
    if n > max_points or m > max_points:
        raise ValueError(f"diagram sizes ({n}, {m}) exceed max_points={max_points}")
    if n == 0 and m == 0:
        return 0.0
    cost = np.zeros((n + m, m + n))
    if n and m:
        cost[:n, :m] = _ground_distances(da, db, internal_p) ** order
    if n:
        cost[:n, m:] = (_diagonal_distance(_persistences(da), internal_p) ** order)[:, None]
    if m:
        cost[n:, :m] = (_diagonal_distance(_persistences(db), internal_p) ** order)[None, :]
    row_ind, col_ind = linear_sum_assignment(cost)
    return float(cost[row_ind, col_ind].sum() ** (1.0 / order))


def check_solver_agreement(
    dist_fn: Callable[[Diagram, Diagram], float],
    pairs: Sequence[tuple[Diagram, Diagram]],
    order: float = 2.0,
    internal_p: float = 2.0,
    rtol: float = 1e-6,
) -> InvariantVerdict:
    """W3: a solver under test must agree with the Hungarian oracle on small pairs.

    Args:
        dist_fn: The distance callable under test, ``(A, B) -> float``.
        pairs: Small diagram pairs to test on.
        order: Wasserstein order q the solver claims to compute.
        internal_p: Ground-metric exponent p the solver claims.
        rtol: Maximum tolerated relative disagreement.

    Returns:
        Verdict with the worst relative disagreement in ``detail``.
    """
    worst = 0.0
    for a, b in pairs:
        oracle = wasserstein_exact_small(a, b, order=order, internal_p=internal_p)
        tested = float(dist_fn(a, b))
        denom = max(oracle, 1e-12)
        worst = max(worst, abs(tested - oracle) / denom)
    return InvariantVerdict(
        name="W3.solver_agreement",
        passed=worst <= rtol,
        detail={"max_relative_disagreement": worst, "rtol": rtol, "n_pairs": len(pairs)},
    )


# ---------------------------------------------------------------------------
# W4 — metric axioms
# ---------------------------------------------------------------------------


def check_metric_axioms(
    dist_fn: Callable[[Diagram, Diagram], float],
    diagrams: Sequence[Diagram],
    rtol: float = 1e-9,
) -> InvariantVerdict:
    """W4: identity, symmetry, and triangle inequality for a distance callable.

    Checks ``d(D, D) = 0`` and ``d(A, B) = d(B, A)`` for every diagram/pair and
    ``d(A, C) <= d(A, B) + d(B, C)`` for every ordered triple drawn from
    ``diagrams``. Wasserstein distances are metrics; approximate matchers
    typically break the triangle inequality even when symmetric.

    Args:
        dist_fn: The distance callable under test.
        diagrams: Diagrams to draw pairs and triples from (>= 3 recommended).
        rtol: Relative slack on each axiom.

    Returns:
        Verdict with per-axiom worst violations in ``detail``.
    """
    n = len(diagrams)
    d = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            d[i, j] = float(dist_fn(diagrams[i], diagrams[j]))
    scale = max(float(d.max()), 1e-12)
    worst_identity = float(np.abs(np.diag(d)).max()) if n else 0.0
    worst_symmetry = float(np.abs(d - d.T).max()) if n else 0.0
    worst_triangle = 0.0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                worst_triangle = max(worst_triangle, d[i, k] - (d[i, j] + d[j, k]))
    passed = worst_identity <= rtol * scale and worst_symmetry <= rtol * scale and worst_triangle <= rtol * scale
    return InvariantVerdict(
        name="W4.metric_axioms",
        passed=bool(passed),
        detail={
            "worst_identity": worst_identity,
            "worst_symmetry": worst_symmetry,
            "worst_triangle_excess": worst_triangle,
            "scale": scale,
            "rtol": rtol,
        },
    )


# ---------------------------------------------------------------------------
# W5 — order-interleaving sandwich against an independent bottleneck
# ---------------------------------------------------------------------------


def bottleneck_sandwich(
    a: Diagram,
    b: Diagram,
    bottleneck: float,
    order: float = 2.0,
    internal_p: float = 2.0,
) -> tuple[float, float]:
    """W5: bounds ``bottleneck <= W_q(A, B) <= (n+m)^(1/q) * 2^(1/p) * bottleneck``.

    Lower: for any matching ``(sum c**q)**(1/q) >= max c`` and the L^p ground
    metric dominates L^inf, so every W_q dominates the (L^inf) bottleneck
    distance. Upper: the bottleneck-optimal matching is a feasible plan whose
    per-pair L^p cost is at most ``2**(1/p)`` times its L^inf cost.

    Args:
        a: First diagram.
        b: Second diagram.
        bottleneck: Independently computed bottleneck distance (e.g. gudhi's
            hera-based C++ path, which shares nothing with POT/EMD).
        order: Wasserstein order q.
        internal_p: Ground-metric exponent p.

    Returns:
        ``(lower, upper)`` bounds on ``W_q(A, B)``.
    """
    n_total = _as_diagram(a).shape[0] + _as_diagram(b).shape[0]
    if n_total == 0:
        return 0.0, 0.0
    lp_factor = 1.0 if math.isinf(internal_p) else 2.0 ** (1.0 / internal_p)
    upper = float(n_total ** (1.0 / order) * lp_factor * bottleneck)
    return float(bottleneck), upper


def check_bottleneck_sandwich(
    value: float,
    a: Diagram,
    b: Diagram,
    bottleneck: float,
    order: float = 2.0,
    internal_p: float = 2.0,
    rtol: float = 1e-9,
) -> InvariantVerdict:
    """W5: verdict on a reported ``W_q`` against the bottleneck sandwich.

    Args:
        value: The reported distance under scrutiny.
        a: First diagram.
        b: Second diagram.
        bottleneck: Independently computed bottleneck distance.
        order: Wasserstein order q the value claims.
        internal_p: Ground-metric exponent p the value claims.
        rtol: Relative floating-point slack on both bounds.

    Returns:
        Verdict; fails when the value escapes ``[lower, upper]``.
    """
    lower, upper = bottleneck_sandwich(a, b, bottleneck, order=order, internal_p=internal_p)
    passed = value >= lower * (1.0 - rtol) - 1e-15 and value <= upper * (1.0 + rtol) + 1e-15
    return InvariantVerdict(
        name="W5.bottleneck_sandwich",
        passed=bool(passed),
        detail={"value": float(value), "lower": lower, "upper": upper, "rtol": rtol},
    )


# ---------------------------------------------------------------------------
# L — persistence-landscape checks
# ---------------------------------------------------------------------------


def landscape_levels(diagram: Diagram, ts: NDArray[np.float64], k_max: int | None = None) -> NDArray[np.float64]:
    """Reference landscape: k-th largest tent value at each grid point.

    ``lambda_k(t)`` is the k-th largest value among the tent functions
    ``tent_i(t) = max(0, min(t - b_i, d_i - t))``. This pointwise
    descending-rearrangement characterisation is exact (up to the grid) and
    independent of any production landscape code, so it doubles as the
    reference side of the L-checks.

    Args:
        diagram: Persistence diagram, shape (n, 2), finite pairs only.
        ts: Evaluation grid, shape (T,).
        k_max: Number of levels to return; default n (all — no truncation).

    Returns:
        Array of shape (k_max, T): rows are lambda_1, lambda_2, ...
    """
    dgm = _as_diagram(diagram)
    t = np.asarray(ts, dtype=np.float64)
    n = dgm.shape[0]
    k = n if k_max is None else k_max
    if n == 0:
        return np.zeros((max(k, 1), t.shape[0]))
    tents = np.minimum(t[None, :] - dgm[:, 0:1], dgm[:, 1:2] - t[None, :])
    tents = np.maximum(tents, 0.0)
    levels = -np.sort(-tents, axis=0)
    if k <= n:
        return levels[:k]
    return np.vstack([levels, np.zeros((k - n, t.shape[0]))])


def landscape_norm_closed_form(diagram: Diagram, p: float = 2.0) -> float:
    """L2: exact total L^p content of the full landscape, from the diagram alone.

    Because ``{lambda_k(t)}_k`` is the descending rearrangement of the tent
    values at every t, ``sum_k lambda_k(t)**p = sum_i tent_i(t)**p`` pointwise
    and exactly, so ``sum_k ||lambda_k||_p^p = sum_i 2*h_i**(p+1)/(p+1)`` with
    ``h_i = pers_i/2``. For p=2 this is ``(2/3) * sum_i (pers_i/2)**3`` — an
    O(n) closed form for the entire landscape's squared L2 norm, and the
    landscape lane's impossibility screen.

    Args:
        diagram: Persistence diagram, shape (n, 2), finite pairs only.
        p: Integral exponent (finite).

    Returns:
        ``sum_k ||lambda_k||_p^p`` (note: the p-th power, not the norm).
    """
    h = _persistences(diagram) / 2.0
    if h.size == 0:
        return 0.0
    return float((2.0 * h ** (p + 1.0) / (p + 1.0)).sum())


def check_landscape_norm(
    levels: NDArray[np.float64],
    ts: NDArray[np.float64],
    diagram: Diagram,
    p: float = 2.0,
    rtol: float = 1e-3,
) -> InvariantVerdict:
    """L2: a computed landscape's total L^p content against the closed form.

    Truncation at K levels drops the *smallest* rearranged values, so the
    computed total is <= the closed form always; when K >= n (no truncation
    possible) the two must agree to grid tolerance. The grid must cover the
    diagram's support for the comparison to be meaningful (checked).

    Args:
        levels: Landscape under test, shape (K, T), rows lambda_1..lambda_K.
        ts: Evaluation grid, shape (T,), covering [min birth, max death].
        diagram: The source diagram.
        p: Integral exponent.
        rtol: Relative tolerance absorbing grid discretisation error.

    Returns:
        Verdict; fails on computed > closed form (impossible) or on a deficit
        beyond tolerance when no truncation can explain it.
    """
    t = np.asarray(ts, dtype=np.float64)
    lv = np.asarray(levels, dtype=np.float64)
    dgm = _as_diagram(diagram)
    closed = landscape_norm_closed_form(diagram, p=p)
    computed = float(np.trapezoid(lv**p, t, axis=1).sum()) if lv.size else 0.0
    covers = bool(dgm.size == 0 or (t.min() <= dgm[:, 0].min() and t.max() >= dgm[:, 1].max()))
    atol = 1e-12
    no_truncation = lv.shape[0] >= dgm.shape[0]
    upper_ok = computed <= closed * (1.0 + rtol) + atol
    lower_ok = (not no_truncation) or computed >= closed * (1.0 - rtol) - atol
    return InvariantVerdict(
        name="L2.norm_identity",
        passed=bool(covers and upper_ok and lower_ok),
        detail={
            "computed": computed,
            "closed_form": closed,
            "grid_covers_support": covers,
            "truncation_possible": not no_truncation,
            "rtol": rtol,
        },
    )


def check_landscape_structure(
    levels: NDArray[np.float64],
    ts: NDArray[np.float64],
    diagram: Diagram,
    rtol: float = 1e-9,
) -> InvariantVerdict:
    """L1: ordering, non-negativity, 1-Lipschitz continuity, support, peak bound.

    For all grid points: ``lambda_1 >= lambda_2 >= ... >= 0``; each level is
    1-Lipschitz (checked with grid slack); every level vanishes outside
    ``[min birth, max death]``; and ``sup lambda_k <= (k-th largest
    persistence)/2``. Violations indicate silent resampling, smoothing, or
    normalisation — the landscape analogue of an undeclared convention change.

    Args:
        levels: Landscape under test, shape (K, T).
        ts: Evaluation grid, shape (T,).
        diagram: The source diagram.
        rtol: Relative slack scaled by the landscape's peak value.

    Returns:
        Verdict with per-property worst violations in ``detail``.
    """
    lv = np.asarray(levels, dtype=np.float64)
    t = np.asarray(ts, dtype=np.float64)
    dgm = _as_diagram(diagram)
    scale = max(float(lv.max()) if lv.size else 0.0, 1e-12)
    tol = rtol * scale
    worst_neg = float(np.maximum(-lv, 0.0).max()) if lv.size else 0.0
    worst_order = float(np.maximum(np.diff(lv, axis=0), 0.0).max()) if lv.shape[0] > 1 else 0.0
    dt = np.diff(t)
    worst_lipschitz = float(np.maximum(np.abs(np.diff(lv, axis=1)) - dt[None, :], 0.0).max()) if lv.size else 0.0
    if dgm.size:
        outside = (t < dgm[:, 0].min()) | (t > dgm[:, 1].max())
        worst_support = float(np.abs(lv[:, outside]).max()) if outside.any() and lv.size else 0.0
        pers_sorted = np.sort(_persistences(dgm))[::-1]
        k = lv.shape[0]
        caps = np.zeros(k)
        caps[: min(k, pers_sorted.size)] = pers_sorted[: min(k, pers_sorted.size)] / 2.0
        worst_peak = float(np.maximum(lv.max(axis=1) - caps, 0.0).max()) if lv.size else 0.0
    else:
        worst_support = float(np.abs(lv).max()) if lv.size else 0.0
        worst_peak = worst_support
    passed = all(w <= tol for w in (worst_neg, worst_order, worst_lipschitz, worst_support, worst_peak))
    return InvariantVerdict(
        name="L1.structure",
        passed=bool(passed),
        detail={
            "worst_negativity": worst_neg,
            "worst_order_violation": worst_order,
            "worst_lipschitz_excess": worst_lipschitz,
            "worst_support_leak": worst_support,
            "worst_peak_excess": worst_peak,
            "tol": tol,
        },
    )


def check_landscape_stability(
    levels_a: NDArray[np.float64],
    levels_b: NDArray[np.float64],
    bottleneck: float,
    rtol: float = 1e-9,
) -> InvariantVerdict:
    """L3: landscape infinity-stability against an independent bottleneck.

    Bubenik (2015): ``sup_k ||lambda_k(A) - lambda_k(B)||_inf <=
    bottleneck(A, B)``. The left side comes from the landscape pipeline, the
    right from the diagram-metric pipeline; a violation proves one of the two
    independent implementations wrong. The grid supremum underestimates the
    true supremum, so no grid slack is needed on the passing side.

    Args:
        levels_a: Landscape of A, shape (K_a, T), same grid as ``levels_b``.
        levels_b: Landscape of B, shape (K_b, T); level counts may differ
            (missing levels are zero).
        bottleneck: Independently computed bottleneck distance.
        rtol: Relative floating-point slack.

    Returns:
        Verdict with the observed supremum and the bound in ``detail``.
    """
    la = np.asarray(levels_a, dtype=np.float64)
    lb = np.asarray(levels_b, dtype=np.float64)
    k = max(la.shape[0], lb.shape[0])
    t_len = la.shape[1] if la.size else lb.shape[1]
    pa = np.zeros((k, t_len))
    pb = np.zeros((k, t_len))
    if la.size:
        pa[: la.shape[0]] = la
    if lb.size:
        pb[: lb.shape[0]] = lb
    sup = float(np.abs(pa - pb).max()) if k else 0.0
    passed = sup <= bottleneck * (1.0 + rtol) + 1e-15
    return InvariantVerdict(
        name="L3.stability",
        passed=bool(passed),
        detail={"landscape_sup_distance": sup, "bottleneck_bound": float(bottleneck), "rtol": rtol},
    )


# ---------------------------------------------------------------------------
# P — permutation-test and null-model checks
# ---------------------------------------------------------------------------


def check_pvalue_grid(p_value: float, n_draws: int, atol: float = 1e-6) -> InvariantVerdict:
    """P1: a Monte-Carlo permutation p-value must equal (b+1)/(B+1), b in [0, B].

    The add-one estimator is the contract-locked form; a reported p-value off
    this grid means a different denominator or estimator was used (the Class-10
    ``1 + N_pairs`` contradiction is caught here mechanically).

    Args:
        p_value: The reported p-value.
        n_draws: The number of null draws B recorded in the artifact.
        atol: Absolute tolerance on the implied count b.

    Returns:
        Verdict with the implied (possibly fractional) count in ``detail``.
    """
    implied = p_value * (n_draws + 1) - 1.0
    nearest = round(implied)
    on_grid = abs(implied - nearest) <= atol and -atol <= implied <= n_draws + atol
    return InvariantVerdict(
        name="P1.pvalue_grid",
        passed=bool(on_grid),
        detail={"p_value": float(p_value), "n_draws": int(n_draws), "implied_count": float(implied)},
    )


def null_sensitivity_probe(
    statistic_fn: Callable[[object], float],
    null_draw_fn: Callable[[object, np.random.Generator], object],
    observed_data: object,
    n_probes: int = 5,
    seed: int = 0,
    atol: float = 0.0,
) -> InvariantVerdict:
    """P3: a permutation null must perturb the object the statistic consumes.

    Draws probe transforms of the observed data and recomputes the statistic;
    fails when every probe statistic is identical to the observed one (within
    ``atol``) — the vacuous-null signature (label/cohort shuffles permuting
    rows of an already-embedded cloud left VR persistence bit-identical, so
    the "null distribution" was noise and the negative controls could neither
    pass nor fail).

    Args:
        statistic_fn: Maps data to the scalar test statistic.
        null_draw_fn: Maps (data, rng) to one null-transformed dataset.
        observed_data: The observed dataset.
        n_probes: Number of probe draws.
        seed: Seed for the probe generator (recorded in the verdict).
        atol: Spread below which values count as identical.

    Returns:
        Verdict with the observed statistic spread in ``detail``.
    """
    rng = np.random.default_rng(seed)
    observed = float(statistic_fn(observed_data))
    probes = [float(statistic_fn(null_draw_fn(observed_data, rng))) for _ in range(n_probes)]
    spread = max(abs(v - observed) for v in probes) if probes else 0.0
    return InvariantVerdict(
        name="P3.null_sensitivity",
        passed=spread > atol,
        detail={"observed": observed, "max_probe_deviation": spread, "n_probes": n_probes, "seed": seed},
    )


def double_null_calibration(
    pvalue_fn: Callable[[np.random.Generator], float],
    n_runs: int = 200,
    alphas: Sequence[float] = (0.01, 0.05, 0.1),
    delta: float = 1e-3,
    seed: int = 0,
) -> InvariantVerdict:
    """P2: p-values of a test run on its own null must be (super)uniform.

    This is the battery's one *statistical* check: a valid permutation test
    satisfies ``P(p <= alpha) <= alpha`` when the data are drawn from the
    null. The check rejects when the empirical rejection rate at any alpha
    exceeds ``alpha + sqrt(ln(1/delta)/(2*n_runs))`` (one-sided DKW band) —
    anti-conservatism implies broken exchangeability, leaky conditioning, or
    seed reuse. Generalises the T1.41 double-null panel into a standing
    harness.

    Args:
        pvalue_fn: Runs the full test once on freshly drawn null data using
            the supplied generator and returns its p-value.
        n_runs: Number of independent null runs M.
        alphas: Rejection thresholds to audit.
        delta: DKW band confidence parameter (failure probability under a
            valid test is at most ``len(alphas) * delta``).
        seed: Seed for the run generator (recorded in the verdict).

    Returns:
        Verdict with per-alpha empirical rejection rates in ``detail``.
    """
    rng = np.random.default_rng(seed)
    ps = np.array([float(pvalue_fn(rng)) for _ in range(n_runs)])
    eps = math.sqrt(math.log(1.0 / delta) / (2.0 * n_runs))
    detail: dict[str, float | int | bool | str] = {"n_runs": n_runs, "dkw_eps": eps, "seed": seed}
    passed = True
    for alpha in alphas:
        rate = float((ps <= alpha + 1e-12).mean())
        detail[f"rate_at_{alpha}"] = rate
        if rate > alpha + eps:
            passed = False
    return InvariantVerdict(name="P2.double_null", passed=passed, detail=detail)
