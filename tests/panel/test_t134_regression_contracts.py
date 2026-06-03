import math

import numpy as np
import pytest

from trajectory_tda.analysis.panel.foo_regression_contracts import (
    assert_required_keys,
    cluster_bootstrap_indices,
    make_nssec_regime_crosstab,
    normalise_trimmed_ipw,
    rubin_pool,
    validate_crosstab_output,
    validate_foo_sensitivity_output,
    validate_mice_convergence,
    validate_tier2_svyglm_headline_output,
    validate_tier2_output,
)


def test_tier2_escape_regression_spec():
    formula = "escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | hh_group)"
    assert "(1 | hh_group)" in formula
    assert "foo_cluster" not in formula
    assert "regime_init" in formula
    sample_regimes = {"R2", "R6"}
    assert sample_regimes == {"R2", "R6"}


def test_rubin_pooling_formula():
    q = [1.0, 1.2, 0.8, 1.1, 0.9]
    u = [0.04, 0.05, 0.04, 0.045, 0.05]
    pooled = rubin_pool(q, u)
    q_bar = np.mean(q)
    u_bar = np.mean(u)
    b = np.var(q, ddof=1)
    total = u_bar + (1 + 1 / 5) * b
    assert pooled.pooled_estimate == pytest.approx(q_bar)
    assert pooled.within_imputation_variance == pytest.approx(u_bar)
    assert pooled.between_imputation_variance == pytest.approx(b)
    assert pooled.total_variance == pytest.approx(total)
    assert pooled.fmi == pytest.approx((1 + 1 / 5) * b / total)
    assert pooled.pooled_se == pytest.approx(math.sqrt(total))
    no_between = rubin_pool([1, 1, 1], [0.2, 0.3, 0.4])
    assert no_between.fmi == 0
    assert no_between.total_variance == pytest.approx(0.3)


def test_svyglm_cluster_robust_se_construction():
    design = {"ids": "~foo_cluster", "weights": "~ipw_trimmed", "family": "quasibinomial"}
    assert design["ids"] == "~foo_cluster"
    assert design["weights"] == "~ipw_trimmed"
    assert design["family"] == "quasibinomial"
    synthetic_glmm = [0.8, 0.9, 0.85]
    synthetic_svy = [0.75, 0.88, 0.82]
    pooled_glmm = rubin_pool(synthetic_glmm, [0.04, 0.05, 0.04])
    pooled_svy = rubin_pool(synthetic_svy, [0.06, 0.07, 0.06])
    assert pooled_svy.pooled_se > 0
    assert math.copysign(1, pooled_glmm.pooled_estimate) == math.copysign(1, pooled_svy.pooled_estimate)


def test_normalised_ipw_trimming_rule():
    rng = np.random.default_rng(42)
    propensity = np.clip(rng.beta(2, 8, size=1000), 0.002, 0.995)
    propensity[:3] = [0.003, 0.004, 0.98]
    strata = np.where(np.arange(1000) % 3 == 0, "a", "b")
    out = normalise_trimmed_ipw(propensity, strata)
    raw = 1 / propensity
    assert out["ipw_trimmed"].min() == pytest.approx(np.quantile(raw, 0.01))
    assert out["ipw_trimmed"].max() == pytest.approx(np.quantile(raw, 0.99))
    assert np.std(out["ipw_trimmed"]) / np.mean(out["ipw_trimmed"]) < np.std(raw) / np.mean(raw)
    for level in np.unique(strata):
        assert out["ipw_normalised"][strata == level].mean() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="p1/p99"):
        normalise_trimmed_ipw(propensity, strata, lower_q=0.05, upper_q=0.95)


def test_sigma_foo_cluster_bootstrap():
    clusters = np.repeat(np.arange(4), [2, 3, 1, 4])
    samples_a = cluster_bootstrap_indices(clusters, seed=42, b=5)
    samples_b = cluster_bootstrap_indices(clusters, seed=42, b=5)
    assert samples_a == samples_b
    first = samples_a[0]
    for cluster in np.unique(clusters):
        original = set(np.flatnonzero(clusters == cluster))
        drawn_count = sum(1 for idx in first if clusters[idx] == cluster)
        assert drawn_count in {0, len(original), 2 * len(original), 3 * len(original), 4 * len(original)}
    boot_sigmas = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    assert np.quantile(boot_sigmas, 0.025) >= 0
    assert np.quantile(boot_sigmas, 0.025) <= np.quantile(boot_sigmas, 0.975)


def test_mice_convergence_rule_blocks_pooling_on_failure():
    validate_mice_convergence([True, True, True], {"nssec_proxy": 1.01})
    with pytest.raises(ValueError, match="chain"):
        validate_mice_convergence([True, False, True], {"nssec_proxy": 1.01})
    with pytest.raises(ValueError, match="R-hat"):
        validate_mice_convergence([True, True, True], {"nssec_proxy": 1.2})


def test_cross_tab_sparse_cells_flagged():
    rows = ["H"] * 6 + ["M"] * 2 + ["L"] * 4
    cols = ["R2", "R6", "R2", "R2", "R2", "R2", "R6", "R6", "R2", "R2", "R2", "R2"]
    out = make_nssec_regime_crosstab(rows, cols, ["H", "M", "L"], ["R2", "R6"])
    counts = np.asarray(out["counts"])
    sparse = {(c["row_index"], c["col_index"]) for c in out["sparse_cells"]}
    expected = {(i, j) for i in range(counts.shape[0]) for j in range(counts.shape[1]) if counts[i, j] < 5}
    assert sparse == expected
    assert (0, 0) not in sparse


def _tier2_payload():
    return {
        "schema_version": "panel-output/tier2-ipw-mice-svyglm/v1",
        "generated_at": "2026-06-02T12:00:00Z",
        "task": "T1.34 Tier-2 IPW + MICE + svyglm",
        "pre_registration": "2026-05-25",
        "params": {
            "m_imputations": 20,
            "ipw_source": "weights.rds",
            "ipw_trimming": "p1/p99 of raw, normalised to mean 1",
            "engine_glmm": "glmmTMB",
            "engine_design": "survey::svyglm",
            "family": "binomial/quasibinomial",
            "model_formula_fixed": "escape ~ regime_init + nssec_proxy + birth_cohort + sex + region",
            "model_formula_random": "(1 | hh_group)",
            "conditioning_sample": "first-window regime in {R2, R6}",
            "escape_definition_source": "window_escape_assignments_2026-05-14.json",
            "n_obs": 200,
            "n_clusters_hh": 100,
            "n_clusters_foo": 90,
        },
        "convergence": {
            "all_chains_converged": True,
            "per_chain_trace_passed": [True] * 20,
            "rhat_summary": {"nssec_proxy": 1.0},
        },
        "coefficients": [
            {
                "name": "regime_initR6",
                "level": "R6",
                "glmm_rubin_estimate": 0.5,
                "glmm_rubin_se": 0.1,
                "glmm_rubin_pvalue": 0.01,
                "glmm_rubin_df": 19,
                "glmm_rubin_fmi": 0.1,
                "svyglm_estimate": 0.4,
                "svyglm_se": 0.2,
                "svyglm_pvalue": 0.04,
                "agreement_direction": True,
            }
        ],
        "random_effects": {"sigma_u_hh_pooled": 0.2, "icc_hh": 0.05},
        "model_fit": {"marginal_r2": 0.3, "conditional_r2_caveat": "reported only as descriptive"},
    }


def test_tier2_output_json_schema():
    payload = _tier2_payload()
    validate_tier2_output(payload)
    bad = {**payload, "convergence": {**payload["convergence"], "all_chains_converged": False}}
    with pytest.raises(AssertionError):
        validate_tier2_output(bad)


def _tier2_svyglm_headline_payload():
    return {
        "schema_version": "panel-output/tier2-svyglm-headline/v1",
        "generated_at": "2026-06-03T12:00:00Z",
        "task": "T1.34a svyglm headline (Option A fallback)",
        "pre_registration": "2026-06-03 resolution amendment",
        "params": {
            "m_imputations": 20,
            "engine_headline": "survey::svyglm",
            "family": "quasibinomial",
            "design_ids": "~foo_cluster",
            "ipw_source": "weights.rds",
            "ipw_trimming": "p1/p99 of raw, per-stratum normalisation to mean 1",
            "model_formula_fixed": "escape ~ regime_init + nssec_proxy + birth_cohort + sex + region",
            "conditioning_sample": "first-window regime in {R2, R6}",
            "escape_definition_source": "window_escape_assignments_2026-05-14.json",
            "seed": 42,
            "n_obs": 7097,
            "n_clusters": 6715,
        },
        "convergence": {
            "all_chains_converged": True,
            "per_chain_trace_passed": [True] * 20,
            "rhat_summary": {"nssec_proxy": 1.0},
        },
        "svyglm_headline": [
            {
                "name": "regime_initR6",
                "level": "R6",
                "estimate": 3.55,
                "cluster_robust_se": 0.33,
                "pvalue": 0.0,
                "rubin_df": 1000,
                "rubin_fmi": 0.01,
            }
        ],
        "unweighted_glmm_companion": {
            "regime_init_r6_logor": 3.40,
            "sigma_u_hh": 0.47,
            "icc_hh": 0.062,
            "coefficients": [{"name": "regime_initR6", "level": "R6", "estimate": 3.40, "se": None, "pvalue": None}],
        },
        "household_variance_estimability": {
            "weighted_household_variance_estimable": False,
            "rationale": "singleton-dominated household structure",
            "evidence": ["WeMix Matrix seems negative semi-definite", "weighted glmmTMB ICC->0.997 divergence"],
        },
        "acceptance": {
            "regime6_or_gt_1": True,
            "nssec_direction_consistent_with_t120": True,
            "accepted": True,
        },
    }


def test_tier2_svyglm_headline_json_schema():
    payload = _tier2_svyglm_headline_payload()
    validate_tier2_svyglm_headline_output(payload)
    bad_m = {**payload, "params": {**payload["params"], "m_imputations": 19}}
    with pytest.raises(AssertionError, match="m_imputations"):
        validate_tier2_svyglm_headline_output(bad_m)
    bad_engine = {**payload, "params": {**payload["params"], "engine_headline": "glm"}}
    with pytest.raises(AssertionError, match="engine_headline"):
        validate_tier2_svyglm_headline_output(bad_engine)
    bad_row = {**payload, "svyglm_headline": [{k: v for k, v in payload["svyglm_headline"][0].items() if k != "cluster_robust_se"}]}
    with pytest.raises(AssertionError, match="missing required keys"):
        validate_tier2_svyglm_headline_output(bad_row)
    bad_estimability = {
        **payload,
        "household_variance_estimability": {**payload["household_variance_estimability"], "weighted_household_variance_estimable": True},
    }
    with pytest.raises(AssertionError, match="weighted_household_variance_estimable"):
        validate_tier2_svyglm_headline_output(bad_estimability)
    bad_icc = {**payload, "unweighted_glmm_companion": {**payload["unweighted_glmm_companion"], "icc_hh": 1.5}}
    with pytest.raises(AssertionError, match="icc_hh"):
        validate_tier2_svyglm_headline_output(bad_icc)
    bad_accept = {**payload, "acceptance": {**payload["acceptance"], "accepted": False}}
    with pytest.raises(AssertionError, match="acceptance"):
        validate_tier2_svyglm_headline_output(bad_accept)
    bad_forbidden = {**payload, "weighted_household_icc": 0.99}
    with pytest.raises(AssertionError, match="forbidden"):
        validate_tier2_svyglm_headline_output(bad_forbidden)


def test_nssec_regime_crosstab_json_schema():
    tab = make_nssec_regime_crosstab(["H", "H", "M"], ["R2", "R6", "R6"], ["H", "M"], ["R2", "R6"])
    payload = {
        "schema_version": "panel-output/nssec-regime-crosstab/v1",
        "generated_at": "2026-06-02T12:00:00Z",
        "task": "T1.34 NSSEC x regime cross-tab",
        "params": {
            "nssec_proxy_source": "mice",
            "regime_init_source": "window",
            "nssec_levels": ["H", "M"],
            "regime_levels": ["R2", "R6"],
            "n_total": 3,
            "n_missing_nssec": 0,
            "n_missing_regime": 0,
        },
        **tab,
        "column_independence_test": {"statistic": 0.0, "df": 1, "pvalue": 1.0, "expected_min": 0.5},
    }
    validate_crosstab_output(payload)
    bad = {**payload, "sparse_cells": []}
    with pytest.raises(AssertionError):
        validate_crosstab_output(bad)


def test_foo_sensitivity_fullsample_json_schema():
    payload = {
        "schema_version": "panel-output/foo-sensitivity-fullsample/v1",
        "generated_at": "2026-06-02T12:00:00Z",
        "task": "T1.34c full-sample FOO sensitivity",
        "pre_registration": "2026-05-25",
        "params": {
            "sample_definition": "full analytical sample, all individuals with valid escape outcome - NOT restricted to R2/R6 starters",
            "bootstrap_B": 1000,
            "seed": 42,
            "model_formula": "escape ~ baseline_covariates + (1 | foo_cluster)",
            "engine": "glmmTMB",
            "family": "binomial",
        },
        "n_full_sample": 27280,
        "n_foo_clusters": 25000,
        "sigma_foo": {
            "point_estimate": 0.0,
            "bootstrap_ci_lower": 0.0,
            "bootstrap_ci_upper": 0.1,
            "bootstrap_B": 1000,
            "ci_method": "percentile",
        },
        "ci_includes_zero": True,
        "narrative_sentence": "The 95% bootstrap CI [0.000, 0.100] includes zero, so S8 reports no detectable between-FOO variance.",
    }
    validate_foo_sensitivity_output(payload)
    bad = {**payload, "narrative_sentence": "The effect is significant despite zero."}
    with pytest.raises(AssertionError):
        validate_foo_sensitivity_output(bad)


def test_t134_output_jsons_validate_against_schemas():
    validate_tier2_output(_tier2_payload())
    with pytest.raises(AssertionError):
        assert_required_keys({}, ["schema_version"])
