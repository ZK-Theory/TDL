"""Small deterministic helpers for FOO regression transparency contracts."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean
from typing import Iterable, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class RubinResult:
    pooled_estimate: float
    within_imputation_variance: float
    between_imputation_variance: float
    total_variance: float
    df_rubin: float
    fmi: float
    pooled_se: float


def rubin_pool(estimates: Sequence[float], variances: Sequence[float]) -> RubinResult:
    """Pool scalar estimates with Rubin's rules."""
    if len(estimates) != len(variances):
        raise ValueError("estimates and variances must have the same length")
    if len(estimates) < 2:
        raise ValueError("at least two imputations are required")
    if any(v < 0 for v in variances):
        raise ValueError("within-imputation variances must be non-negative")

    m = len(estimates)
    q_bar = float(mean(estimates))
    u_bar = float(mean(variances))
    b = float(sum((q - q_bar) ** 2 for q in estimates) / (m - 1))
    total = u_bar + (1 + 1 / m) * b
    if total <= 0:
        df = float("inf")
        fmi = 0.0
        pooled_se = 0.0
    elif b == 0:
        df = float("inf")
        fmi = 0.0
        pooled_se = sqrt(total)
    else:
        df = (m - 1) * (1 + u_bar / ((1 + 1 / m) * b)) ** 2
        fmi = ((1 + 1 / m) * b) / total
        pooled_se = sqrt(total)
    return RubinResult(q_bar, u_bar, b, total, df, fmi, pooled_se)


def normalise_trimmed_ipw(
    propensity: Sequence[float],
    strata: Sequence[object],
    lower_q: float = 0.01,
    upper_q: float = 0.99,
) -> dict[str, np.ndarray]:
    """Compute raw, p1/p99-trimmed, and within-stratum mean-1 IPW."""
    p = np.asarray(propensity, dtype=float)
    s = np.asarray(strata)
    if p.ndim != 1 or s.ndim != 1 or len(p) != len(s):
        raise ValueError("propensity and strata must be aligned one-dimensional arrays")
    if np.any((p <= 0) | (p >= 1)):
        raise ValueError("propensities must lie strictly between zero and one")
    if (lower_q, upper_q) != (0.01, 0.99):
        raise ValueError("T1.34 requires p1/p99 trimming")

    raw = 1.0 / p
    lo, hi = np.quantile(raw, [lower_q, upper_q])
    trimmed = np.clip(raw, lo, hi)
    normalised = np.empty_like(trimmed)
    for level in np.unique(s):
        mask = s == level
        normalised[mask] = trimmed[mask] * mask.sum() / trimmed[mask].sum()
    return {"ipw_raw": raw, "ipw_trimmed": trimmed, "ipw_normalised": normalised}


def make_nssec_regime_crosstab(
    rows: Sequence[object],
    cols: Sequence[object],
    row_levels: Sequence[object],
    col_levels: Sequence[object],
    sparse_threshold: int = 5,
) -> dict[str, object]:
    """Build counts, row/column proportions, and explicit sparse-cell records."""
    row_index = {v: i for i, v in enumerate(row_levels)}
    col_index = {v: j for j, v in enumerate(col_levels)}
    counts = np.zeros((len(row_levels), len(col_levels)), dtype=int)
    for r, c in zip(rows, cols):
        if r in row_index and c in col_index:
            counts[row_index[r], col_index[c]] += 1

    row_totals = counts.sum(axis=1, keepdims=True)
    col_totals = counts.sum(axis=0, keepdims=True)
    row_props = np.divide(counts, row_totals, out=np.zeros_like(counts, dtype=float), where=row_totals != 0)
    col_props = np.divide(counts, col_totals, out=np.zeros_like(counts, dtype=float), where=col_totals != 0)
    sparse_cells = []
    for i, r in enumerate(row_levels):
        for j, c in enumerate(col_levels):
            count = int(counts[i, j])
            if count < sparse_threshold:
                sparse_cells.append(
                    {"nssec_level": str(r), "regime_level": str(c), "count": count, "row_index": i, "col_index": j}
                )
    return {
        "counts": counts.tolist(),
        "row_proportions": row_props.tolist(),
        "col_proportions": col_props.tolist(),
        "sparse_cells": sparse_cells,
    }


def cluster_bootstrap_indices(
    cluster_ids: Sequence[object],
    seed: int,
    b: int,
) -> list[list[int]]:
    """Return row indices for cluster-level bootstrap resamples."""
    clusters = np.asarray(cluster_ids)
    unique_clusters = np.unique(clusters)
    rng = np.random.default_rng(seed)
    samples: list[list[int]] = []
    for _ in range(b):
        drawn = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)
        idx: list[int] = []
        for cluster in drawn:
            idx.extend(np.flatnonzero(clusters == cluster).tolist())
        samples.append(idx)
    return samples


def validate_mice_convergence(
    per_chain_trace_passed: Sequence[bool],
    rhat_summary: Mapping[str, float],
    max_rhat: float = 1.1,
) -> None:
    """Raise if any MICE convergence diagnostic fails."""
    failed = [i + 1 for i, ok in enumerate(per_chain_trace_passed) if not ok]
    high_rhat = {k: v for k, v in rhat_summary.items() if isfinite(v) and v > max_rhat}
    if failed or high_rhat:
        detail = []
        if failed:
            detail.append(f"trace drift failed chains: {failed}")
        if high_rhat:
            detail.append(f"R-hat above {max_rhat}: {high_rhat}")
        raise ValueError("; ".join(detail))


def assert_required_keys(payload: Mapping[str, object], keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise AssertionError(f"missing required keys: {missing}")


def validate_tier2_output(payload: Mapping[str, object]) -> None:
    assert_required_keys(
        payload,
        ["schema_version", "generated_at", "task", "pre_registration", "params", "convergence", "coefficients", "random_effects", "model_fit"],
    )
    if payload.get("schema_version") != "panel-output/tier2-ipw-mice-svyglm/v1":
        raise AssertionError("unexpected schema_version")
    if "stargazer_table" in payload:
        raise AssertionError("stargazer_table is forbidden")
    params = payload["params"]  # type: ignore[index]
    if params["m_imputations"] != 20:  # type: ignore[index]
        raise AssertionError("m_imputations must be 20")
    if not payload["convergence"]["all_chains_converged"]:  # type: ignore[index]
        raise AssertionError("all MICE chains must converge")
    icc = payload["random_effects"]["icc_hh"]  # type: ignore[index]
    if icc < 0 or icc > 1:
        raise AssertionError("icc_hh must be in [0, 1]")
    for row in payload["coefficients"]:  # type: ignore[index]
        assert_required_keys(
            row,
            [
                "name",
                "level",
                "glmm_rubin_estimate",
                "glmm_rubin_se",
                "glmm_rubin_pvalue",
                "glmm_rubin_df",
                "glmm_rubin_fmi",
                "svyglm_estimate",
                "svyglm_se",
                "svyglm_pvalue",
                "agreement_direction",
            ],
        )
        if not 0 <= row["glmm_rubin_pvalue"] <= 1 or not 0 <= row["svyglm_pvalue"] <= 1:
            raise AssertionError("p-values must be in [0, 1]")


def validate_crosstab_output(payload: Mapping[str, object]) -> None:
    assert_required_keys(
        payload,
        ["schema_version", "generated_at", "task", "params", "counts", "row_proportions", "col_proportions", "sparse_cells", "column_independence_test"],
    )
    if "aggregated_other_row" in payload:
        raise AssertionError("aggregated_other_row is forbidden")
    counts = np.asarray(payload["counts"])
    if not np.issubdtype(counts.dtype, np.integer) or np.any(counts < 0):
        raise AssertionError("counts must be non-negative integers")
    sparse = {(c["row_index"], c["col_index"]) for c in payload["sparse_cells"]}  # type: ignore[index]
    expected = {(i, j) for i in range(counts.shape[0]) for j in range(counts.shape[1]) if counts[i, j] < 5}
    if sparse != expected:
        raise AssertionError("sparse_cells must exactly match cells with count < 5")


def validate_foo_sensitivity_output(payload: Mapping[str, object]) -> None:
    assert_required_keys(
        payload,
        ["schema_version", "generated_at", "task", "pre_registration", "params", "n_full_sample", "n_foo_clusters", "sigma_foo", "ci_includes_zero", "narrative_sentence"],
    )
    if "sigma_foo_p_value" in payload:
        raise AssertionError("sigma_foo_p_value is forbidden")
    if payload["n_full_sample"] <= 10_000:
        raise AssertionError("full-sample fit appears to use a restricted sample")
    sigma = payload["sigma_foo"]  # type: ignore[index]
    if sigma["bootstrap_B"] != 1000:
        raise AssertionError("bootstrap_B must be 1000")
    if sigma["bootstrap_ci_lower"] > sigma["bootstrap_ci_upper"]:
        raise AssertionError("CI lower bound exceeds upper bound")
    if payload["ci_includes_zero"] and "significant" in payload["narrative_sentence"].lower():
        raise AssertionError("null-evidence narrative must not call the FOO variance significant")
