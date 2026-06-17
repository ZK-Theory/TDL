# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: STRAND (persistence-survival Kaplan-Meier + log-rank) two-sample testing
#   on persistence diagrams, with calibration gate and comparison against W2 /
#   landscape-L2 baselines.  Governs T-STRAND-1 decision (PROMOTE/PARK/KILL).
"""STRAND persistence-survival two-sample test for persistence diagrams.

Implements STRAND (arXiv:2606.11911) on pre-computed persistence diagrams:
  - persistence value p = d - b (finite lifetimes only)
  - per-group Kaplan-Meier survival S(t) = P(p > t)
  - log-rank two-sample statistic
  - label-permutation null (pool lifetimes, relabel to original sizes)
  - STRAND-F variant (appends birth-time survival curve)
  - KS calibration gate

Public API:
  compute_km_survival(lifetimes, t_grid)   -> ndarray  S(t) on grid
  log_rank_statistic(lts_a, lts_b)         -> float    observed statistic
  strand_pvalue(lts_a, lts_b, B, seed, two_sided) -> dict
  strand_f_augment(dgm)                    -> ndarray  concatenated lts + births
  calibrate_strand(lts_pool, n_a, n_b, ...)-> dict     KS calibration result
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats


# ---------------------------------------------------------------------------
# Core STRAND helpers
# ---------------------------------------------------------------------------


def finite_lifetimes(dgm: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return persistence lifetimes p = d - b for finite rows.

    Args:
        dgm: Persistence diagram, shape (n, 2), columns [birth, death].

    Returns:
        1-D array of lifetimes for rows where both birth and death are finite.
    """
    if dgm.shape[0] == 0:
        return np.empty(0, dtype=np.float64)
    mask = np.isfinite(dgm).all(axis=1)
    finite = dgm[mask]
    if finite.shape[0] == 0:
        return np.empty(0, dtype=np.float64)
    return (finite[:, 1] - finite[:, 0]).astype(np.float64)


def compute_km_survival(
    lifetimes: NDArray[np.float64],
    t_grid: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Kaplan-Meier survival S(t) = P(lifetime > t) evaluated on a grid.

    All lifetimes are fully observed (no censoring) so KM reduces to the
    empirical survival function.

    Args:
        lifetimes: 1-D array of non-negative persistence values.
        t_grid: Sorted evaluation points.

    Returns:
        1-D array of survival probabilities on t_grid; all 1.0 if empty.
    """
    if len(lifetimes) == 0:
        return np.ones(len(t_grid), dtype=np.float64)
    sorted_lts = np.sort(lifetimes)
    n = len(sorted_lts)
    surv = np.empty(len(t_grid), dtype=np.float64)
    for i, t in enumerate(t_grid):
        # S(t) = proportion of lifetimes > t
        surv[i] = float(np.sum(sorted_lts > t)) / n
    return surv


def _log_rank_statistic_loop(
    lts_a: NDArray[np.float64],
    lts_b: NDArray[np.float64],
) -> float:
    """Reference O(n^2) log-rank statistic (ground truth for tests).

    Retained as the readable reference implementation; the public
    ``log_rank_statistic`` is a vectorised O(n log n) computation of the
    identical statistic, verified against this loop by the unit tests.
    """
    if len(lts_a) == 0 or len(lts_b) == 0:
        return 0.0

    all_events = np.concatenate([lts_a, lts_b])
    event_times = np.sort(np.unique(all_events))

    o_minus_e = 0.0
    var_sum = 0.0

    for t in event_times:
        at_risk_a = float(np.sum(lts_a >= t))
        at_risk_b = float(np.sum(lts_b >= t))
        at_risk = at_risk_a + at_risk_b
        if at_risk < 1.0:
            continue

        d_a = float(np.sum(lts_a == t))
        d_b = float(np.sum(lts_b == t))
        d = d_a + d_b

        e_a = d * at_risk_a / at_risk
        o_minus_e += d_a - e_a

        if at_risk > 1.0:
            var_contrib = d * at_risk_a * at_risk_b * (at_risk - d) / (at_risk**2 * (at_risk - 1.0))
            var_sum += var_contrib

    if var_sum <= 0.0:
        return 0.0
    return float(o_minus_e / np.sqrt(var_sum))


def log_rank_statistic(
    lts_a: NDArray[np.float64],
    lts_b: NDArray[np.float64],
) -> float:
    """Log-rank test statistic for two groups of fully-observed lifetimes.

    Signed log-rank statistic ``(O_A - E_A) / sqrt(Var)`` summed over unique
    event times, with hypergeometric variance.  Vectorised O(n log n)
    implementation (sort + ``searchsorted`` cumulative at-risk counts);
    mathematically identical to :func:`_log_rank_statistic_loop` to floating
    tolerance (enforced by the unit tests).  Signed so the permutation
    distribution is symmetric.

    Args:
        lts_a: Group A lifetimes (non-negative floats).
        lts_b: Group B lifetimes (non-negative floats).

    Returns:
        Log-rank statistic (float).  0.0 if either group is empty.
    """
    n_a = len(lts_a)
    n_b = len(lts_b)
    if n_a == 0 or n_b == 0:
        return 0.0

    a_sorted = np.sort(np.asarray(lts_a, dtype=np.float64))
    b_sorted = np.sort(np.asarray(lts_b, dtype=np.float64))
    times = np.unique(np.concatenate([a_sorted, b_sorted]))

    # At-risk just before each event time t: count(x >= t) = n - count(x < t).
    at_risk_a = (n_a - np.searchsorted(a_sorted, times, side="left")).astype(np.float64)
    at_risk_b = (n_b - np.searchsorted(b_sorted, times, side="left")).astype(np.float64)
    at_risk = at_risk_a + at_risk_b

    # Events at t: count(x == t) = right - left insertion points.
    d_a = (np.searchsorted(a_sorted, times, side="right") - np.searchsorted(a_sorted, times, side="left")).astype(
        np.float64
    )
    d_b = (np.searchsorted(b_sorted, times, side="right") - np.searchsorted(b_sorted, times, side="left")).astype(
        np.float64
    )
    d = d_a + d_b

    # O_A - E_A over all event times (at_risk >= 1 holds at every event time).
    e_a = d * at_risk_a / at_risk
    o_minus_e = float(np.sum(d_a - e_a))

    # Hypergeometric variance, only where at_risk > 1.
    mask = at_risk > 1.0
    var_terms = np.zeros_like(at_risk)
    ar = at_risk[mask]
    var_terms[mask] = d[mask] * at_risk_a[mask] * at_risk_b[mask] * (ar - d[mask]) / (ar**2 * (ar - 1.0))
    var_sum = float(np.sum(var_terms))

    if var_sum <= 0.0:
        return 0.0
    return float(o_minus_e / np.sqrt(var_sum))


def strand_f_augment(
    dgm: NDArray[np.float64],
) -> NDArray[np.float64]:
    """STRAND-F: augment finite lifetimes with birth times.

    Concatenates [lifetimes, births] for all finite rows, creating the
    STRAND-F feature vector as described in arXiv:2606.11911.

    Args:
        dgm: Persistence diagram, shape (n, 2).

    Returns:
        1-D array: [lifetime_1, ..., lifetime_n, birth_1, ..., birth_n]
        for all finite rows.
    """
    if dgm.shape[0] == 0:
        return np.empty(0, dtype=np.float64)
    mask = np.isfinite(dgm).all(axis=1)
    finite = dgm[mask]
    if finite.shape[0] == 0:
        return np.empty(0, dtype=np.float64)
    lts = finite[:, 1] - finite[:, 0]
    births = finite[:, 0]
    return np.concatenate([lts, births]).astype(np.float64)


def strand_pvalue(
    lts_a: NDArray[np.float64],
    lts_b: NDArray[np.float64],
    B: int = 1000,
    seed: int = 42,
    two_sided: bool = True,
) -> dict[str, Any]:
    """STRAND label-permutation p-value.

    Pool lifetimes from both groups, repeatedly relabel to original sizes,
    recompute log-rank statistic, compare to observed.

    Args:
        lts_a: Group A lifetimes.
        lts_b: Group B lifetimes.
        B: Number of permutations.
        seed: RNG seed.
        two_sided: If True use |statistic| for comparison (two-sided p).

    Returns:
        Dict with keys: observed_stat, perm_stats (list[float]), pvalue,
        n_a, n_b, B, seed, two_sided.
    """
    n_a = len(lts_a)
    n_b = len(lts_b)
    observed_stat = log_rank_statistic(lts_a, lts_b)
    pooled = np.concatenate([lts_a, lts_b])

    rng = np.random.RandomState(seed)
    perm_stats: list[float] = []
    for _ in range(B):
        perm = rng.permutation(pooled)
        perm_a = perm[:n_a]
        perm_b = perm[n_a:]
        perm_stats.append(log_rank_statistic(perm_a, perm_b))

    perm_arr = np.array(perm_stats)
    if two_sided:
        r = int(np.sum(np.abs(perm_arr) >= np.abs(observed_stat)))
    else:
        r = int(np.sum(perm_arr >= observed_stat))
    pvalue = (r + 1) / (B + 1)

    return {
        "observed_stat": float(observed_stat),
        "perm_stats": perm_arr.tolist(),
        "pvalue": float(pvalue),
        "n_a": n_a,
        "n_b": n_b,
        "B": B,
        "seed": seed,
        "two_sided": two_sided,
    }


# ---------------------------------------------------------------------------
# Non-invariance assertion
# ---------------------------------------------------------------------------


def assert_null_non_invariance(
    lts_a: NDArray[np.float64],
    lts_b: NDArray[np.float64],
    seed: int = 42,
    n_checks: int = 5,
) -> dict[str, Any]:
    """Assert that label permutation changes the log-rank statistic.

    Confirms the null operation is not invariant to its input — a requirement
    before any STRAND p-value can be trusted.

    Args:
        lts_a: Group A lifetimes.
        lts_b: Group B lifetimes.
        seed: RNG seed.
        n_checks: Number of permutations to check.

    Returns:
        Dict with observed_stat, perm_stats_sample, non_invariant (bool).

    Raises:
        AssertionError: If all permutations produce the same statistic as observed.
    """
    observed = log_rank_statistic(lts_a, lts_b)
    pooled = np.concatenate([lts_a, lts_b])
    n_a = len(lts_a)
    rng = np.random.RandomState(seed)

    perm_stats: list[float] = []
    for _ in range(n_checks):
        perm = rng.permutation(pooled)
        perm_a = perm[:n_a]
        perm_b = perm[n_a:]
        perm_stats.append(log_rank_statistic(perm_a, perm_b))

    perm_arr = np.array(perm_stats)
    any_different = bool(np.any(perm_arr != observed))

    # Raise explicitly rather than `assert` (which `python -O` strips) while
    # preserving the documented AssertionError contract — this is a
    # research-assurance gate that must always fire.
    if not any_different:
        raise AssertionError(
            "STRAND null is INVARIANT: all label permutations reproduced the observed "
            "log-rank statistic, so permutation p-values would not be trustworthy."
        )

    return {
        "observed_stat": float(observed),
        "perm_stats_sample": perm_arr.tolist(),
        "non_invariant": any_different,
    }


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def calibrate_strand(
    lts_pool: NDArray[np.float64],
    n_a: int,
    n_b: int,
    n_calibration_trials: int = 100,
    B: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Type-I error calibration for STRAND on matched groups.

    Draws two samples of sizes n_a and n_b from a common pool, computes the
    STRAND permutation p-value for each trial, then KS-tests the collection
    of p-values against Uniform(0,1).

    Args:
        lts_pool: Common pool of lifetimes (both groups combined).
        n_a: Size of group A.
        n_b: Size of group B.
        n_calibration_trials: Number of calibration trials.
        B: Permutations per trial.
        seed: Master RNG seed; per-trial seeds derive as seed + trial_idx + 1.

    Returns:
        Dict with ks_statistic, ks_p, mean_pvalue, calibrated (bool),
        trial_pvalues (list), n_calibration_trials, B, seed.
    """
    n_total = n_a + n_b
    rng = np.random.RandomState(seed)

    trial_pvalues: list[float] = []
    t0 = time.time()
    for i in range(n_calibration_trials):
        trial_seed = seed + i + 1
        trial_pool = rng.choice(lts_pool, size=n_total, replace=True)
        trial_a = trial_pool[:n_a]
        trial_b = trial_pool[n_a:]
        result = strand_pvalue(trial_a, trial_b, B=B, seed=trial_seed, two_sided=True)
        trial_pvalues.append(result["pvalue"])
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (n_calibration_trials - i - 1)
            print(f"  calibration trial {i + 1}/{n_calibration_trials} (elapsed={elapsed:.1f}s, ETA={eta:.1f}s)")

    pvals_arr = np.array(trial_pvalues)
    ks_stat, ks_p = stats.kstest(pvals_arr, "uniform")

    return {
        "ks_statistic": float(ks_stat),
        "ks_p": float(ks_p),
        "mean_pvalue": float(pvals_arr.mean()),
        "calibrated": bool(ks_p >= 0.05),
        "trial_pvalues": pvals_arr.tolist(),
        "n_calibration_trials": n_calibration_trials,
        "B": B,
        "seed": seed,
    }


# ---------------------------------------------------------------------------
# Baseline: W2 and landscape-L2 cross null-null
# ---------------------------------------------------------------------------


def _hera_w2_pair(d_b: NDArray[np.float64], d_u: NDArray[np.float64]) -> float:
    """Exact Wasserstein-2 between two diagrams (module-level for joblib pickling).

    Defined at module scope so joblib's loky backend can pickle the task on
    Windows; nested closures are not picklable.
    """
    from gudhi.hera import wasserstein_distance as hera_w2

    a = np.asarray(d_b, dtype=np.float64).reshape(-1, 2)
    b = np.asarray(d_u, dtype=np.float64).reshape(-1, 2)
    a = a[np.isfinite(a).all(axis=1)]
    b = b[np.isfinite(b).all(axis=1)]
    return float(hera_w2(a, b, order=2, internal_p=2))


def cross_null_null_baselines(
    bhps_null_h0: list[NDArray[np.float64]],
    bhps_null_h1: list[NDArray[np.float64]],
    usoc_null_h0: list[NDArray[np.float64]],
    usoc_null_h1: list[NDArray[np.float64]],
    bhps_obs_h0: NDArray[np.float64],
    bhps_obs_h1: NDArray[np.float64],
    usoc_obs_h0: NDArray[np.float64],
    usoc_obs_h1: NDArray[np.float64],
    B_baseline: int = 200,
    seed: int = 42,
    k_max: int = 5,
    n_points: int = 200,
    n_jobs: int = 4,
) -> dict[str, Any]:
    """W2 and landscape-L2 cross null-null two-sample tests.

    Observed statistic = distance(bhps_obs, usoc_obs).
    Null = distance(bhps_null_i, usoc_null_j) for B_baseline random pairs
    (i, j) subsampled from the 1000x1000 null pool with seed=42.

    p-value: one-sided (r+1)/(B+1) where r = sum(null >= observed).

    Args:
        bhps_null_h{0,1}: BHPS null diagram lists (1000 each).
        usoc_null_h{0,1}: USoc null diagram lists (1000 each).
        bhps_obs_h{0,1}: BHPS observed diagrams (finite rows only).
        usoc_obs_h{0,1}: USoc observed diagrams (finite rows only).
        B_baseline: Number of null-null cross pairs to sample.
        seed: RNG seed for pair sampling.
        k_max: Landscape function count.
        n_points: Landscape grid points.
        n_jobs: Parallel workers for W2.

    Returns:
        Dict with h0/h1 sub-dicts each containing w2_p, landscape_l2_p,
        obs_w2, obs_land_l2, null_w2_dist, null_land_dist.
    """
    from gudhi.hera import wasserstein_distance as hera_w2
    from joblib import Parallel, delayed

    from trajectory_tda.scripts.stage1._battery_core import (
        landscape_l2_distance,
        landscape_on_grid,
    )

    rng = np.random.RandomState(seed)
    n_bhps = len(bhps_null_h0)
    n_usoc = len(usoc_null_h0)

    # The same sampled (i, j) index pairs are reused for the H0 and H1 null
    # pools, so each pool must share its length with the H0 pool the indices are
    # drawn against; otherwise H1 indexing could run out of range or silently
    # distort the sample.  The frozen null pools are equal-length by
    # construction (same B); guard it loudly rather than trust that invariant.
    if len(bhps_null_h1) != n_bhps or len(usoc_null_h1) != n_usoc:
        raise ValueError(
            "Null pool lengths differ across homology dimensions "
            f"(bhps H0={n_bhps}, H1={len(bhps_null_h1)}; "
            f"usoc H0={n_usoc}, H1={len(usoc_null_h1)}); "
            "shared index sampling requires equal-length H0/H1 pools."
        )

    # Sample B_baseline (i,j) index pairs (valid for both H0 and H1 pools).
    bhps_indices = rng.randint(0, n_bhps, size=B_baseline)
    usoc_indices = rng.randint(0, n_usoc, size=B_baseline)

    results: dict[str, Any] = {}

    for dim_label, bhps_obs, usoc_obs, bhps_null_list, usoc_null_list in [
        ("h0", bhps_obs_h0, usoc_obs_h0, bhps_null_h0, usoc_null_h0),
        ("h1", bhps_obs_h1, usoc_obs_h1, bhps_null_h1, usoc_null_h1),
    ]:
        print(f"  [baseline] {dim_label}: computing observed W2...")
        t0 = time.time()
        obs_w2 = float(hera_w2(bhps_obs, usoc_obs, order=2, internal_p=2))
        print(f"  [baseline] {dim_label}: observed W2={obs_w2:.4f} ({time.time() - t0:.1f}s)")

        # Landscape grid from obs diagrams pooled
        all_obs = np.concatenate([bhps_obs, usoc_obs], axis=0)
        if all_obs.shape[0] > 0:
            t_min = float(all_obs[:, 0].min())
            t_max = float(all_obs[:, 1].max())
        else:
            t_min, t_max = 0.0, 1.0
        t_vals = np.linspace(t_min, t_max, n_points)
        # Spacing of an n_points linspace grid is (max - min) / (n_points - 1).
        dx = (t_vals[-1] - t_vals[0]) / (n_points - 1) if n_points > 1 else 1.0

        bhps_obs_land = landscape_on_grid(bhps_obs, t_vals, k_max)
        usoc_obs_land = landscape_on_grid(usoc_obs, t_vals, k_max)
        obs_land = float(landscape_l2_distance(bhps_obs_land, usoc_obs_land, dx))
        print(f"  [baseline] {dim_label}: observed landscape L2={obs_land:.4f}")

        # Null W2 in parallel (module-level worker so loky can pickle the task)
        print(f"  [baseline] {dim_label}: computing {B_baseline} null-null W2 pairs...")
        t1 = time.time()
        null_w2_list = Parallel(n_jobs=n_jobs, verbose=0)(
            delayed(_hera_w2_pair)(bhps_null_list[int(bi)], usoc_null_list[int(ui)])
            for bi, ui in zip(bhps_indices, usoc_indices)
        )
        print(f"  [baseline] {dim_label}: null-null W2 done in {time.time() - t1:.1f}s")
        null_w2_arr = np.array(null_w2_list, dtype=np.float64)

        # Null landscape L2 (fast — no PH)
        null_land_list: list[float] = []
        for bi, ui in zip(bhps_indices, usoc_indices):
            d_b = np.array(bhps_null_list[bi], dtype=np.float64).reshape(-1, 2)
            d_u = np.array(usoc_null_list[ui], dtype=np.float64).reshape(-1, 2)
            d_b = d_b[np.isfinite(d_b).all(axis=1)]
            d_u = d_u[np.isfinite(d_u).all(axis=1)]
            lb = landscape_on_grid(d_b, t_vals, k_max)
            lu = landscape_on_grid(d_u, t_vals, k_max)
            null_land_list.append(landscape_l2_distance(lb, lu, dx))
        null_land_arr = np.array(null_land_list, dtype=np.float64)

        # One-sided p-values: r = count(null >= observed)
        r_w2 = int(np.sum(null_w2_arr >= obs_w2))
        r_land = int(np.sum(null_land_arr >= obs_land))
        B = len(null_w2_list)
        w2_p = (r_w2 + 1) / (B + 1)
        land_p = (r_land + 1) / (B + 1)

        print(f"  [baseline] {dim_label}: W2 p={w2_p:.4f}, land L2 p={land_p:.4f}")

        results[dim_label] = {
            "obs_w2": obs_w2,
            "obs_land_l2": obs_land,
            "w2_p": w2_p,
            "landscape_l2_p": land_p,
            "null_w2_dist": null_w2_arr.tolist(),
            "null_land_dist": null_land_arr.tolist(),
            "B_pairs": B,
            "pair_bhps_indices": bhps_indices.tolist(),
            "pair_usoc_indices": usoc_indices.tolist(),
        }

    return results


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------


def validate_strand_comparison_output(payload: dict[str, Any]) -> None:
    """Validate a strand_vs_baseline JSON payload against the contract.

    Uses explicit ``raise ValueError`` rather than ``assert`` so the contract
    is still enforced when Python runs under ``-O`` (which strips assertions).

    Raises:
        ValueError: On any contract violation.
    """
    required_top = {
        "schema_version",
        "generated_at",
        "task",
        "pre_registration",
        "inputs",
        "params",
        "calibration",
        "comparison",
        "decision",
        "null_non_invariance",
    }
    missing = sorted(required_top - set(payload))
    if missing:
        raise ValueError(f"Missing required keys: {missing}")

    forbidden = {"refit_pca", "per_call_loadings"}
    present_forbidden = sorted(forbidden & set(payload))
    if present_forbidden:
        raise ValueError(f"Forbidden keys present: {present_forbidden}")

    # Params
    p = payload["params"]
    if p.get("finite_lifetimes_only") is not True:
        raise ValueError("params.finite_lifetimes_only must be true")
    if p.get("grid_size_g") != 25:
        raise ValueError("params.grid_size_g must be 25")
    if p.get("null_model") != "label-permutation":
        raise ValueError("params.null_model must be 'label-permutation'")
    if not (isinstance(p.get("B"), int) and p["B"] >= 1000):
        raise ValueError("params.B must be >= 1000")
    if not (isinstance(p.get("B_baseline_pairs"), int) and p["B_baseline_pairs"] >= 1):
        raise ValueError("params.B_baseline_pairs must be >= 1")
    if p.get("p_value_formula") != "(r+1)/(B+1)":
        raise ValueError("params.p_value_formula must be '(r+1)/(B+1)'")
    if p.get("frozen_loadings") is not True:
        raise ValueError("params.frozen_loadings must be true")
    if p.get("L") != 5000:
        raise ValueError("params.L must be 5000")
    if p.get("seed") != 42:
        raise ValueError("params.seed must be 42")
    if p.get("alpha_level") != 0.05:
        raise ValueError("params.alpha_level must be 0.05")

    # Calibration
    cal = payload["calibration"]
    ks_stat = cal.get("ks_statistic")
    ks_p = cal.get("ks_p")
    mean_p = cal.get("mean_pvalue")
    calibrated = cal.get("calibrated")
    if not (isinstance(ks_stat, float) and ks_stat >= 0.0):
        raise ValueError("calibration.ks_statistic must be float >= 0")
    if not (isinstance(ks_p, float) and 0.0 <= ks_p <= 1.0):
        raise ValueError("calibration.ks_p must be in [0, 1]")
    if not (isinstance(mean_p, float) and 0.0 <= mean_p <= 1.0):
        raise ValueError("calibration.mean_pvalue must be in [0, 1]")
    if not isinstance(calibrated, bool):
        raise ValueError("calibration.calibrated must be bool")
    # Critical: calibrated must equal ks_p >= 0.05
    expected_calibrated = ks_p >= 0.05
    if calibrated != expected_calibrated:
        raise ValueError(f"calibration.calibrated ({calibrated}) disagrees with ks_p >= 0.05 ({expected_calibrated})")

    # Comparison
    comp = payload["comparison"]
    for dim in ("h0", "h1"):
        if dim not in comp:
            raise ValueError(f"comparison must contain '{dim}'")
        cell = comp[dim]
        for key in ("strand_logrank_p", "w2_p", "landscape_l2_p"):
            val = cell.get(key)
            if not (isinstance(val, float) and 0.0 <= val <= 1.0):
                raise ValueError(f"comparison.{dim}.{key} must be float in [0, 1]")

    # Null non-invariance: the label-permutation null must perturb the STRAND
    # statistic on each dimension (schema requires non_invariant == true).  The
    # canonical gate-4 only checks top-level keys, so this per-cell requirement
    # is enforceable only here.
    nni = payload["null_non_invariance"]
    for dim in ("h0", "h1"):
        if dim not in nni:
            raise ValueError(f"null_non_invariance must contain '{dim}'")
        if nni[dim].get("non_invariant") is not True:
            raise ValueError(
                f"null_non_invariance.{dim}.non_invariant must be true "
                "(the permutation null must change the STRAND statistic)"
            )

    # Decision
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        raise ValueError("decision must be a dict")
    verdict = decision.get("verdict")
    if verdict not in {"additive", "redundant", "miscalibrated"}:
        raise ValueError(f"decision.verdict must be one of additive/redundant/miscalibrated, got {verdict!r}")
    # Verdict-calibration coupling
    if not calibrated:
        if verdict != "miscalibrated":
            raise ValueError("decision.verdict must be 'miscalibrated' when calibration fails")
    elif verdict not in {"additive", "redundant"}:
        raise ValueError(f"calibrated result must have verdict additive or redundant, got {verdict!r}")
