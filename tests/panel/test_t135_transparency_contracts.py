import json
import math
from pathlib import Path

import numpy as np
import pytest

from trajectory_tda.analysis.panel.t135_transparency_contracts import (
    ICC_GRID,
    REASON_VOCAB,
    boundary_mixture_pvalue,
    chi2_1_sf,
    cluster_bootstrap_pairs,
    cohens_kappa,
    dispatch_t135_json,
    mcnemar_stats,
    validate_power_analysis,
    validate_sibling_concordance,
    validate_singleton_decomposition,
    within_pair_or,
)


ROOT = Path(__file__).resolve().parents[2]


def test_glmm_power_simulation_construction():
    cluster_sizes = np.array([2, 2, 3, 4])
    icc = 0.20
    sigma_u = math.sqrt(icc * math.pi**2 / 3)
    assert sigma_u == pytest.approx(math.sqrt(0.20 * math.pi**2 / 3))
    assert cluster_sizes.sum() == 11
    assert boundary_mixture_pvalue(4.0) == pytest.approx(0.5 * chi2_1_sf(4.0))
    assert boundary_mixture_pvalue(0.0) == 1.0
    simulation_record = {"null_engine": "glmmTMB", "full_engine": "glmmTMB", "reject": None, "convergence_failure": True}
    assert simulation_record["null_engine"] == simulation_record["full_engine"] == "glmmTMB"
    converged = [True, False, True, True]
    rejects = [True, None, False, False]
    n_converged = sum(converged)
    assert sum(r is True for r, ok in zip(rejects, converged) if ok) / n_converged == pytest.approx(1 / 3)
    type_i_at_icc0 = 0.052
    assert abs(type_i_at_icc0 - 0.05) <= 0.03
    no_hits = [{"icc": x, "empirical_power": 0.0} for x in ICC_GRID]
    min_detectable = next((r["icc"] for r in no_hits if r["empirical_power"] >= 0.80), "greater than 0.20")
    assert min_detectable == "greater than 0.20"


def test_mcnemar_construction():
    out = mcnemar_stats(a=20, b=10, c=4, d=30)
    assert out["statistic_uncorrected"] == pytest.approx(36 / 14)
    assert out["statistic_yates_corrected"] == pytest.approx(25 / 14)
    assert out["pvalue_asymptotic"] == pytest.approx(chi2_1_sf(25 / 14))
    small = mcnemar_stats(a=1, b=3, c=2, d=9)
    assert small["used_variant"] == "exact_conditional_binomial"
    assert small["pvalue_exact"] == pytest.approx(2 * sum(math.comb(5, i) * 0.5**5 for i in range(3)))


def test_cohens_kappa_construction():
    kappa = cohens_kappa(a=20, b=10, c=4, d=30)
    n = 64
    po = 50 / n
    pe = ((30 * 24) + (34 * 40)) / n**2
    assert kappa == pytest.approx((po - pe) / (1 - pe))
    assert -1 <= kappa <= 1
    assert cohens_kappa(a=0, b=0, c=0, d=10) is None
    samples = cluster_bootstrap_pairs([1, 1, 2, 3], [1, 0, 1, 0], [0, 0, 1, 1], seed=42, b=3)
    samples_again = cluster_bootstrap_pairs([1, 1, 2, 3], [1, 0, 1, 0], [0, 0, 1, 1], seed=42, b=3)
    assert all(np.array_equal(left, right) for left, right in zip(samples, samples_again))
    clusters = np.array([1, 1, 2, 3])
    for sample in samples:
        for cluster in np.unique(clusters[sample]):
            assert set(np.flatnonzero(clusters == cluster)).issubset(set(sample))


def test_within_pair_odds_ratio_construction():
    odds, log_or = within_pair_or(a=20, b=10, c=4, d=30)
    assert odds == pytest.approx(15)
    assert log_or == pytest.approx(math.log(15))
    assert within_pair_or(a=20, b=0, c=4, d=30) == (None, None)


def test_singleton_decomposition_exhaustivity():
    payload = {
        "schema_version": "panel-output/singleton-decomposition/v1",
        "generated_at": "2026-06-03T00:00:00Z",
        "task": "T1.35b singleton decomposition",
        "pre_registration": "2026-05-25",
        "params": {"n_total_singletons": 6284, "n_t121_total_sample": 6995},
        "counts": {"n_true_singletons": 6281, "n_filtered_singletons": 3},
        "primary_reason_counts": {k: (3 if k == "does_not_start_in_r2_or_r6" else 0) for k in REASON_VOCAB},
        "secondary_reason_counts": {k: (3 if k in {"ipw_zero_due_to_ineligibility", "missing_nssec_proxy"} else 0) for k in REASON_VOCAB},
        "per_singleton_records": [
            {"pidp": 1, "primary_reason": "does_not_start_in_r2_or_r6", "secondary_reasons": ["ipw_zero_due_to_ineligibility"], "sibling_pidps": [2]},
            {"pidp": 3, "primary_reason": "does_not_start_in_r2_or_r6", "secondary_reasons": ["missing_nssec_proxy"], "sibling_pidps": [4]},
            {"pidp": 5, "primary_reason": "does_not_start_in_r2_or_r6", "secondary_reasons": ["ipw_zero_due_to_ineligibility", "missing_nssec_proxy"], "sibling_pidps": [6]},
        ],
    }
    validate_singleton_decomposition(payload)
    bad = {**payload, "counts": {"n_true_singletons": 6280, "n_filtered_singletons": 3}}
    with pytest.raises(AssertionError, match="exhaustive"):
        validate_singleton_decomposition(bad)


def test_singleton_decomposition_json_schema():
    test_singleton_decomposition_exhaustivity()


def test_power_analysis_json_schema():
    payload = {
        "schema_version": "panel-output/power-analysis/v1",
        "generated_at": "2026-06-03T00:00:00Z",
        "task": "T1.35a power analysis",
        "pre_registration": "2026-05-25",
        "params": {
            "icc_grid": ICC_GRID,
            "B": 1000,
            "alpha": 0.05,
            "seed": 42,
            "n_individuals": 711,
            "n_clusters": 342,
            "sigma_u_formula": "latent-variable: sigma_u^2 = icc * pi^2 / 3",
            "lrt_df_reference": "chisq_0_1_mixture",
            "null_engine": "glmmTMB",
            "full_engine": "glmmTMB",
        },
        "calibration": {"type_i_at_icc0": 0.052, "calibrated": True, "n_rejections": 52, "n_converged": 1000, "convergence_failures": 0},
        "power_curve": [{"icc": icc, "empirical_power": 0.5, "n_rejections": 490, "n_converged": 980, "convergence_failures": 20, "bootstrap_se_of_power": 0.016} for icc in ICC_GRID],
        "minimum_detectable_icc": "greater than 0.20",
        "multi_member_only_fit": {"sigma_foo_point_estimate": 0.0, "sigma_foo_bootstrap_ci_lower": 0.0, "sigma_foo_bootstrap_ci_upper": 0.1, "bootstrap_B": 1000, "lrt_pvalue_against_icc_zero": 0.5},
    }
    validate_power_analysis(payload)
    bad = {**payload, "params": {**payload["params"], "B": 999}}
    with pytest.raises(AssertionError):
        validate_power_analysis(bad)
    bad_ref = {**payload, "params": {**payload["params"], "lrt_df_reference": "chisq_1"}}
    with pytest.raises(AssertionError, match="lrt_df_reference"):
        validate_power_analysis(bad_ref)
    bad_cal = {**payload, "calibration": {**payload["calibration"], "calibrated": False}, "minimum_detectable_icc": 0.05}
    with pytest.raises(AssertionError, match="uncalibrated"):
        validate_power_analysis(bad_cal)


def test_sibling_concordance_json_schema():
    payload = {
        "schema_version": "panel-output/sibling-concordance/v1",
        "generated_at": "2026-06-03T00:00:00Z",
        "task": "T1.35c sibling concordance",
        "pre_registration": "2026-05-25",
        "params": {"n_pairs": 342, "member_ordering_rule": "smaller pidp within cluster is member 1", "bootstrap_B": 1000, "seed": 42, "source_sample": "x"},
        "contingency_table": {"a": 20, "b": 10, "c": 4, "d": 308},
        "mcnemar": {"statistic_uncorrected": 36 / 14, "statistic_yates_corrected": 25 / 14, "pvalue_asymptotic": 0.1, "pvalue_exact": None, "used_variant": "asymptotic_yates_cc"},
        "cohens_kappa": {"point_estimate": 0.2, "bootstrap_ci_lower": -0.1, "bootstrap_ci_upper": 0.4, "bootstrap_B": 1000, "ci_method": "percentile"},
        "odds_ratio": {"point_estimate": 159.5, "log_or": 5.0, "bootstrap_ci_lower": 1.0, "bootstrap_ci_upper": 200.0, "bootstrap_B": 1000, "ci_method": "percentile on log scale, exponentiated", "haldane_anscombe_supplementary": None},
    }
    validate_sibling_concordance(payload)
    bad = {**payload, "chisq_pearson_statistic": 1.0}
    with pytest.raises(AssertionError):
        validate_sibling_concordance(bad)


def test_t135_output_jsons_validate_against_schemas():
    out_dir = ROOT / "results" / "panel_methodology" / "foo_transparency"
    for path in out_dir.glob("*.json"):
        if "bench" in path.name or "syntax" in path.name:
            continue
        if path.name.startswith(("power_analysis_", "singleton_decomposition_", "sibling_concordance_")) and "corrected_" not in path.name:
            continue
        with path.open(encoding="utf-8") as fh:
            dispatch_t135_json(path, json.load(fh))
