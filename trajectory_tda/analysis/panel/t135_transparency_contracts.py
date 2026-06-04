"""Deterministic helpers for T1.35 transparency supplement contracts."""

from __future__ import annotations

from math import comb, erfc, exp, isfinite, log, sqrt
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

REASON_VOCAB = {
    "does_not_start_in_r2_or_r6",
    "ipw_zero_due_to_ineligibility",
    "dropped_by_10_of_14_rule",
    "missing_nssec_proxy",
    "other_filter_chain",
}
ICC_GRID = [0.01, 0.025, 0.05, 0.10, 0.20]


def chi2_1_sf(x: float) -> float:
    return erfc(sqrt(max(0.0, x) / 2.0))


def boundary_mixture_pvalue(lrt: float) -> float:
    return 1.0 if lrt <= 0 else 0.5 * chi2_1_sf(lrt)


def binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def mcnemar_stats(a: int, b: int, c: int, d: int) -> dict[str, float | str | None]:
    discordant = b + c
    if discordant == 0:
        unc = cc = 0.0
    else:
        unc = (b - c) ** 2 / discordant
        cc = (abs(b - c) - 1) ** 2 / discordant
    exact = min(1.0, 2 * binom_cdf(min(b, c), discordant)) if discordant < 25 else None
    return {
        "statistic_uncorrected": unc,
        "statistic_yates_corrected": cc,
        "pvalue_asymptotic": chi2_1_sf(cc),
        "pvalue_exact": exact,
        "used_variant": "exact_conditional_binomial" if discordant < 25 else "asymptotic_yates_cc",
    }


def cohens_kappa(a: int, b: int, c: int, d: int) -> float | None:
    n = a + b + c + d
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n**2
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def within_pair_or(a: int, b: int, c: int, d: int) -> tuple[float | None, float | None]:
    if b * c == 0:
        return None, None
    odds = (a * d) / (b * c)
    return odds, log(odds)


def cluster_bootstrap_pairs(
    cluster_ids: Sequence[object],
    outcomes_1: Sequence[int],
    outcomes_2: Sequence[int],
    seed: int,
    b: int,
) -> list[np.ndarray]:
    clusters = np.asarray(cluster_ids)
    unique = np.unique(clusters)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(b):
        drawn = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([np.flatnonzero(clusters == cluster) for cluster in drawn])
        samples.append(idx)
    return samples


def assert_required_keys(payload: Mapping[str, object], keys: Sequence[str]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise AssertionError(f"missing required keys: {missing}")


def validate_power_analysis(payload: Mapping[str, object]) -> None:
    assert_required_keys(payload, ["schema_version", "generated_at", "task", "pre_registration", "params", "calibration", "power_curve", "minimum_detectable_icc", "multi_member_only_fit"])
    if payload["schema_version"] != "panel-output/power-analysis/v1":
        raise AssertionError("unexpected power schema version")
    if "extrapolated_minimum_detectable_icc" in payload:
        raise AssertionError("extrapolated minimum detectable ICC is forbidden")
    params = payload["params"]  # type: ignore[index]
    if list(params["icc_grid"]) != ICC_GRID or params["B"] != 1000:  # type: ignore[index]
        raise AssertionError("power grid and B must match the pre-registration")
    if params["n_individuals"] != 711 or params["n_clusters"] != 342:  # type: ignore[index]
        raise AssertionError("power sample structure must be n_individuals=711 and n_clusters=342")
    if params.get("sigma_u_formula") != "latent-variable: sigma_u^2 = (icc / (1 - icc)) * pi^2 / 3":  # type: ignore[attr-defined]
        raise AssertionError("sigma_u_formula must use the latent-variable ICC inversion")
    if params.get("lrt_df_reference") != "chisq_0_1_mixture":  # type: ignore[attr-defined]
        raise AssertionError("lrt_df_reference must be chisq_0_1_mixture")
    if params.get("null_engine") != "glmmTMB" or params.get("full_engine") != "glmmTMB":  # type: ignore[attr-defined]
        raise AssertionError("null and full engines must both be glmmTMB")
    calibration = payload["calibration"]  # type: ignore[index]
    assert_required_keys(calibration, ["type_i_at_icc0", "calibrated", "n_rejections", "n_converged", "convergence_failures"])
    if not 0 <= calibration["type_i_at_icc0"] <= 1:
        raise AssertionError("type_i_at_icc0 must be in [0, 1]")
    # Conservation on the calibration block (same simulate-fit-reject machinery as
    # the power grid; counts must close against B and bound the rejection tally).
    if calibration["n_converged"] + calibration["convergence_failures"] != params["B"]:  # type: ignore[index]
        raise AssertionError("calibration convergence counts must sum to B")
    if not 0 <= calibration["n_rejections"] <= calibration["n_converged"]:
        raise AssertionError("calibration n_rejections must be in [0, n_converged]")
    if calibration["n_converged"] > 0 and calibration["n_rejections"] != round(calibration["type_i_at_icc0"] * calibration["n_converged"]):
        raise AssertionError("calibration n_rejections must align with type_i_at_icc0")
    seen = []
    for row in payload["power_curve"]:  # type: ignore[index]
        seen.append(row["icc"])
        if not 0 <= row["empirical_power"] <= 1:
            raise AssertionError("empirical power must be in [0, 1]")
        assert_required_keys(row, ["n_rejections", "n_converged", "convergence_failures"])
        if row["n_converged"] + row["convergence_failures"] != params["B"]:  # type: ignore[index]
            raise AssertionError("convergence counts must sum to B")
        if not 0 <= row["n_rejections"] <= row["n_converged"]:
            raise AssertionError("n_rejections must be in [0, n_converged]")
        if row["n_converged"] > 0 and row["n_rejections"] != round(row["empirical_power"] * row["n_converged"]):
            raise AssertionError("n_rejections must align with n_converged")
    if seen != ICC_GRID:
        raise AssertionError("power curve grid mismatch")
    mdi = payload["minimum_detectable_icc"]
    if mdi not in {"greater than 0.20", "engine not calibrated"} and mdi not in ICC_GRID:
        raise AssertionError("minimum detectable ICC must be a grid value or the locked string")
    if calibration["calibrated"] is False and mdi != "engine not calibrated":
        raise AssertionError("uncalibrated engine must not report a numeric minimum detectable ICC")
    fit = payload["multi_member_only_fit"]  # type: ignore[index]
    if fit["bootstrap_B"] != 1000 or fit["sigma_foo_bootstrap_ci_lower"] > fit["sigma_foo_bootstrap_ci_upper"]:
        raise AssertionError("invalid sigma bootstrap summary")
    if not 0 <= fit["lrt_pvalue_against_icc_zero"] <= 1:
        raise AssertionError("LRT p-value must be in [0, 1]")


def validate_singleton_decomposition(payload: Mapping[str, object]) -> None:
    assert_required_keys(payload, ["schema_version", "generated_at", "task", "pre_registration", "params", "counts", "primary_reason_counts", "secondary_reason_counts", "per_singleton_records"])
    if payload["schema_version"] != "panel-output/singleton-decomposition/v1":
        raise AssertionError("unexpected singleton schema version")
    params = payload["params"]  # type: ignore[index]
    counts = payload["counts"]  # type: ignore[index]
    if params["n_total_singletons"] <= 0 or params["n_t121_total_sample"] <= 0:
        raise AssertionError("singleton sample counts must be positive")
    if counts["n_true_singletons"] + counts["n_filtered_singletons"] != params["n_total_singletons"]:
        raise AssertionError("singleton decomposition is not exhaustive")
    primary = payload["primary_reason_counts"]  # type: ignore[index]
    secondary = payload["secondary_reason_counts"]  # type: ignore[index]
    if set(primary) != REASON_VOCAB or set(secondary) != REASON_VOCAB:
        raise AssertionError("reason vocabulary mismatch")
    if sum(primary.values()) != counts["n_filtered_singletons"]:
        raise AssertionError("primary reasons must sum to filtered singleton count")
    records = payload["per_singleton_records"]  # type: ignore[index]
    if len(records) != counts["n_filtered_singletons"]:
        raise AssertionError("per-singleton record length mismatch")
    for rec in records:
        if rec["primary_reason"] not in REASON_VOCAB:
            raise AssertionError("record primary reason outside vocabulary")
        if not set(rec["secondary_reasons"]).issubset(REASON_VOCAB):
            raise AssertionError("record secondary reason outside vocabulary")


def validate_sibling_concordance(payload: Mapping[str, object]) -> None:
    assert_required_keys(payload, ["schema_version", "generated_at", "task", "pre_registration", "params", "contingency_table", "mcnemar", "cohens_kappa", "odds_ratio"])
    if payload["schema_version"] != "panel-output/sibling-concordance/v1":
        raise AssertionError("unexpected sibling concordance schema version")
    if "chisq_pearson_statistic" in payload:
        raise AssertionError("Pearson chi-square is forbidden")
    params = payload["params"]  # type: ignore[index]
    tab = payload["contingency_table"]  # type: ignore[index]
    if params["n_pairs"] < 342 or params.get("n_clusters") != 342 or params["bootstrap_B"] != 1000:
        raise AssertionError("pair count or bootstrap B mismatch")
    if sum(tab[k] for k in ["a", "b", "c", "d"]) != params["n_pairs"]:
        raise AssertionError("2x2 table does not sum to n_pairs")
    mc = payload["mcnemar"]  # type: ignore[index]
    if mc["used_variant"] not in {"asymptotic_uncorrected", "asymptotic_yates_cc", "exact_conditional_binomial"}:
        raise AssertionError("unknown McNemar variant")
    if not 0 <= mc["pvalue_asymptotic"] <= 1:
        raise AssertionError("McNemar p-value must be in [0, 1]")
    kappa = payload["cohens_kappa"]  # type: ignore[index]
    if kappa["bootstrap_B"] != 1000 or kappa["bootstrap_ci_lower"] > kappa["bootstrap_ci_upper"]:
        raise AssertionError("invalid kappa CI")
    if kappa["point_estimate"] is not None and not -1 <= kappa["point_estimate"] <= 1:
        raise AssertionError("kappa point estimate outside [-1, 1]")
    odds = payload["odds_ratio"]  # type: ignore[index]
    if odds["bootstrap_B"] != 1000 or odds["bootstrap_ci_lower"] > odds["bootstrap_ci_upper"]:
        raise AssertionError("invalid odds-ratio CI")
    if odds["point_estimate"] is not None and odds["point_estimate"] <= 0:
        raise AssertionError("odds ratio must be positive when defined")


def dispatch_t135_json(path: Path, payload: Mapping[str, object]) -> None:
    name = path.name
    if name.startswith("power_analysis_"):
        validate_power_analysis(payload)
    elif name.startswith("singleton_decomposition_"):
        validate_singleton_decomposition(payload)
    elif name.startswith("sibling_concordance_"):
        validate_sibling_concordance(payload)
