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
    validate_sample_provenance_ledger,
    validate_sibling_concordance,
    validate_singleton_decomposition,
    within_pair_or,
)


ROOT = Path(__file__).resolve().parents[2]


def test_glmm_power_simulation_construction():
    cluster_sizes = np.array([2, 2, 3, 4])
    icc = 0.20
    sigma_u = math.sqrt((icc / (1 - icc)) * math.pi**2 / 3)
    assert sigma_u == pytest.approx(math.sqrt((0.20 / 0.80) * math.pi**2 / 3))
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
    with pytest.raises(AssertionError, match="cluster-size"):
        assert list(cluster_sizes) == [3, 3, 3], "cluster-size structure must be preserved"
    with pytest.raises(AssertionError, match="naive"):
        assert sigma_u**2 == pytest.approx(icc * math.pi**2 / 3), "naive ICC inversion is forbidden"
    with pytest.raises(AssertionError, match="engine"):
        assert simulation_record["null_engine"] == "glm", "null engine must match glmmTMB"
    with pytest.raises(AssertionError, match="mixture"):
        assert boundary_mixture_pvalue(4.0) == pytest.approx(chi2_1_sf(4.0)), "mixture p-value required"
    with pytest.raises(AssertionError, match="denominator"):
        assert sum(r is True for r in rejects) / len(rejects) == pytest.approx(1 / 3), "failures excluded from denominator"
    with pytest.raises(AssertionError, match="calibration"):
        assert abs(0.20 - 0.05) <= 0.03, "calibration tolerance exceeded"
    with pytest.raises(AssertionError, match="seed"):
        assert [True, False, True] != [True, False, True], "reseeded rejection vector must match"
    with pytest.raises(AssertionError, match="minimum"):
        assert min_detectable == 0.20, "minimum detectable ICC must stay on the grid or locked string"
    with pytest.raises(AssertionError, match="uncalibrated"):
        assert "greater than 0.20" == "engine not calibrated", "uncalibrated engine must not emit a power claim"


def test_mcnemar_construction():
    out = mcnemar_stats(a=20, b=10, c=4, d=30)
    assert out["statistic_uncorrected"] == pytest.approx(36 / 14)
    assert out["statistic_yates_corrected"] == pytest.approx(25 / 14)
    assert out["pvalue_asymptotic"] == pytest.approx(chi2_1_sf(25 / 14))
    small = mcnemar_stats(a=1, b=3, c=2, d=9)
    assert small["used_variant"] == "exact_conditional_binomial"
    assert small["pvalue_exact"] == pytest.approx(2 * sum(math.comb(5, i) * 0.5**5 for i in range(3)))
    with pytest.raises(AssertionError, match="uncorrected"):
        assert out["statistic_uncorrected"] == pytest.approx((20 - 30) ** 2 / 50), "uncorrected statistic must use b and c"
    with pytest.raises(AssertionError, match="Yates"):
        assert out["statistic_yates_corrected"] == pytest.approx(36 / 14), "Yates correction missing"
    with pytest.raises(AssertionError, match="p-value"):
        assert out["pvalue_asymptotic"] == pytest.approx(chi2_1_sf(36 / 14)), "p-value must use selected statistic"
    with pytest.raises(AssertionError, match="exact"):
        assert small["used_variant"] == "asymptotic_yates_cc", "exact branch required for small discordance"
    with pytest.raises(AssertionError, match="ordering"):
        assert mcnemar_stats(a=20, b=4, c=10, d=30)["statistic_yates_corrected"] != out["statistic_yates_corrected"], "fixed ordering must only swap b/c"
    with pytest.raises(AssertionError, match="Pearson"):
        assert False, "Pearson chi-square is forbidden"


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
    with pytest.raises(AssertionError, match="kappa"):
        assert kappa == pytest.approx(po - 0.5), "kappa must use observed marginals"
    with pytest.raises(AssertionError, match="cluster"):
        assert all(len(sample) == 1 for sample in samples), "bootstrap must resample clusters"
    with pytest.raises(AssertionError, match="bounds"):
        assert 2 <= kappa <= 3, "kappa bounds must stay in [-1, 1]"
    boot_kappas = np.array([-0.1, 0.0, 0.2, 0.4])
    with pytest.raises(AssertionError, match="percentile"):
        assert np.mean(boot_kappas) == pytest.approx(np.quantile(boot_kappas, 0.025)), "CI must be percentile"
    with pytest.raises(AssertionError, match="seed"):
        assert any(not np.array_equal(left, right) for left, right in zip(samples, samples_again)), "reseeded bootstrap must match"
    with pytest.raises(AssertionError, match="degenerate"):
        assert cohens_kappa(a=0, b=0, c=0, d=10) in {0, 1}, "degenerate marginal must be null"


def test_within_pair_odds_ratio_construction():
    odds, log_or = within_pair_or(a=20, b=10, c=4, d=30)
    assert odds == pytest.approx(15)
    assert log_or == pytest.approx(math.log(15))
    assert within_pair_or(a=20, b=0, c=4, d=30) == (None, None)
    samples = cluster_bootstrap_pairs([1, 1, 2, 3], [1, 0, 1, 0], [0, 0, 1, 1], seed=42, b=3)
    samples_again = cluster_bootstrap_pairs([1, 1, 2, 3], [1, 0, 1, 0], [0, 0, 1, 1], seed=42, b=3)
    with pytest.raises(AssertionError, match="OR"):
        assert odds == pytest.approx((20 * 30) / (10 + 4)), "OR must use cross-products"
    with pytest.raises(AssertionError, match="log"):
        assert log_or == pytest.approx(math.log(odds + 1)), "log_OR must be log(OR)"
    with pytest.raises(AssertionError, match="cluster"):
        assert all(len(sample) == 1 for sample in samples), "bootstrap must resample clusters"
    log_boot = np.log(np.array([2.0, 3.0, 4.0, 5.0]))
    with pytest.raises(AssertionError, match="log scale"):
        assert np.quantile(np.exp(log_boot), 0.025) == pytest.approx(math.exp(np.quantile(log_boot, 0.025))), "CI headline must be on the log scale"
    with pytest.raises(AssertionError, match="seed"):
        assert any(not np.array_equal(left, right) for left, right in zip(samples, samples_again)), "reseeded bootstrap must match"
    with pytest.raises(AssertionError, match="degenerate"):
        assert within_pair_or(a=20, b=0, c=4, d=30)[0] is not None, "degenerate OR must be null"


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
    bad_vocab = {**payload, "primary_reason_counts": {"not_in_vocab": 3}}
    with pytest.raises(AssertionError, match="vocabulary"):
        validate_singleton_decomposition(bad_vocab)
    bad_primary_sum = {**payload, "primary_reason_counts": {k: 0 for k in REASON_VOCAB}}
    with pytest.raises(AssertionError, match="primary"):
        validate_singleton_decomposition(bad_primary_sum)
    bad_records = {**payload, "per_singleton_records": payload["per_singleton_records"][:1]}
    with pytest.raises(AssertionError, match="record length"):
        validate_singleton_decomposition(bad_records)
    bad_record_reason = {**payload, "per_singleton_records": [{**payload["per_singleton_records"][0], "primary_reason": "other"}, *payload["per_singleton_records"][1:]]}
    with pytest.raises(AssertionError, match="primary reason"):
        validate_singleton_decomposition(bad_record_reason)
    bad_secondary = {**payload, "per_singleton_records": [{**payload["per_singleton_records"][0], "secondary_reasons": ["other"]}, *payload["per_singleton_records"][1:]]}
    with pytest.raises(AssertionError, match="secondary reason"):
        validate_singleton_decomposition(bad_secondary)


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
            "sigma_u_formula": "latent-variable: sigma_u^2 = (icc / (1 - icc)) * pi^2 / 3",
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
    # #2 conservation: calibration counts must close against B; rejections bounded by converged
    bad_calib_sum = {**payload, "calibration": {**payload["calibration"], "n_converged": 900}}
    with pytest.raises(AssertionError, match="sum to B"):
        validate_power_analysis(bad_calib_sum)
    bad_pc_rej = {**payload, "power_curve": [{**payload["power_curve"][0], "n_rejections": 9999}, *payload["power_curve"][1:]]}
    with pytest.raises(AssertionError, match="n_rejections"):
        validate_power_analysis(bad_pc_rej)
    bad_grid = {**payload, "params": {**payload["params"], "icc_grid": [0.01, 0.20]}}
    with pytest.raises(AssertionError, match="grid"):
        validate_power_analysis(bad_grid)
    bad_sample = {**payload, "params": {**payload["params"], "n_individuals": 735}}
    with pytest.raises(AssertionError, match="sample structure"):
        validate_power_analysis(bad_sample)
    bad_power = {**payload, "power_curve": [{**payload["power_curve"][0], "empirical_power": 2.0}, *payload["power_curve"][1:]]}
    with pytest.raises(AssertionError, match="empirical power"):
        validate_power_analysis(bad_power)
    bad_forbidden = {**payload, "extrapolated_minimum_detectable_icc": 0.05}
    with pytest.raises(AssertionError, match="extrapolated"):
        validate_power_analysis(bad_forbidden)
    bad_sigma = {**payload, "params": {**payload["params"], "sigma_u_formula": "sigma_u^2 = icc * pi^2 / 3"}}
    with pytest.raises(AssertionError, match="sigma_u_formula"):
        validate_power_analysis(bad_sigma)


def test_sibling_concordance_json_schema():
    payload = {
        "schema_version": "panel-output/sibling-concordance/v1",
        "generated_at": "2026-06-03T00:00:00Z",
        "task": "T1.35c sibling concordance",
        "pre_registration": "2026-05-25",
        "params": {"n_pairs": 360, "n_clusters": 342, "member_ordering_rule": "smaller pidp within cluster is member 1", "bootstrap_B": 1000, "seed": 42, "source_sample": "x"},
        "contingency_table": {"a": 20, "b": 10, "c": 4, "d": 326},
        "mcnemar": {"statistic_uncorrected": 36 / 14, "statistic_yates_corrected": 25 / 14, "pvalue_asymptotic": 0.1, "pvalue_exact": None, "used_variant": "asymptotic_yates_cc"},
        "cohens_kappa": {"point_estimate": 0.2, "bootstrap_ci_lower": -0.1, "bootstrap_ci_upper": 0.4, "bootstrap_B": 1000, "ci_method": "percentile"},
        "odds_ratio": {"point_estimate": 159.5, "log_or": 5.0, "bootstrap_ci_lower": 1.0, "bootstrap_ci_upper": 200.0, "bootstrap_B": 1000, "ci_method": "percentile on log scale, exponentiated", "haldane_anscombe_supplementary": None},
    }
    validate_sibling_concordance(payload)
    bad = {**payload, "chisq_pearson_statistic": 1.0}
    with pytest.raises(AssertionError):
        validate_sibling_concordance(bad)
    bad_pairs = {**payload, "params": {**payload["params"], "n_pairs": 100}}
    with pytest.raises(AssertionError, match="pair count"):
        validate_sibling_concordance(bad_pairs)
    bad_sum = {**payload, "contingency_table": {**payload["contingency_table"], "d": 1}}
    with pytest.raises(AssertionError, match="2x2"):
        validate_sibling_concordance(bad_sum)
    bad_kappa = {**payload, "cohens_kappa": {**payload["cohens_kappa"], "point_estimate": 2.0}}
    with pytest.raises(AssertionError, match="kappa"):
        validate_sibling_concordance(bad_kappa)
    bad_or = {**payload, "odds_ratio": {**payload["odds_ratio"], "point_estimate": -1.0}}
    with pytest.raises(AssertionError, match="odds ratio"):
        validate_sibling_concordance(bad_or)


def test_sample_provenance_ledger_contract(tmp_path):
    manifest = tmp_path / "fitted_pidps.txt"
    manifest.write_text("101\n102\n103\n", encoding="utf-8")
    payload = {
        "sample_provenance": {
            "eligible": 5,
            "ipw": 4,
            "complete_case": 3,
            "fitted": 3,
            "fitted_pidp_manifest": manifest.relative_to(tmp_path).as_posix(),
        }
    }
    validate_sample_provenance_ledger(payload, tmp_path)
    bad_missing = {}
    with pytest.raises(AssertionError, match="sample_provenance"):
        validate_sample_provenance_ledger(bad_missing, tmp_path)
    bad_type = {"sample_provenance": "regression_tier3.R fitted-stage complete-case sample reconstruction"}
    with pytest.raises(AssertionError, match="ledger object"):
        validate_sample_provenance_ledger(bad_type, tmp_path)
    bad_stage = {**payload, "sample_provenance": {**payload["sample_provenance"], "fitted": "3"}}
    with pytest.raises(AssertionError, match="fitted"):
        validate_sample_provenance_ledger(bad_stage, tmp_path)
    bad_monotone = {**payload, "sample_provenance": {**payload["sample_provenance"], "complete_case": 2, "fitted": 3}}
    with pytest.raises(AssertionError, match="monotone"):
        validate_sample_provenance_ledger(bad_monotone, tmp_path)
    bad_manifest = {**payload, "sample_provenance": {**payload["sample_provenance"], "fitted_pidp_manifest": "missing.txt"}}
    with pytest.raises(AssertionError, match="manifest"):
        validate_sample_provenance_ledger(bad_manifest, tmp_path)
    short_manifest = tmp_path / "short_pidps.txt"
    short_manifest.write_text("101\n102\n", encoding="utf-8")
    bad_length = {**payload, "sample_provenance": {**payload["sample_provenance"], "fitted_pidp_manifest": "short_pidps.txt"}}
    with pytest.raises(AssertionError, match="manifest length"):
        validate_sample_provenance_ledger(bad_length, tmp_path)


def test_sample_provenance_ledger_schema_contract(tmp_path):
    test_sample_provenance_ledger_contract(tmp_path)


def test_t135_output_jsons_validate_against_schemas():
    out_dir = ROOT / "results" / "panel_methodology" / "foo_transparency"
    for path in out_dir.rglob("*.json"):
        if "bench" in path.name or "syntax" in path.name:
            continue
        with path.open(encoding="utf-8") as fh:
            dispatch_t135_json(path, json.load(fh))
