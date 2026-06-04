# Contract Hardening Register - 2026-06-04

Generated from `uv run python .claude/hooks/contract_binding_check.py --no-pytest --all-jsons` in warn mode after adding the hardening gates.

Hardening warnings: 112 (74 gate 1c + 34 gate 2b + 4 pending-debt)
Existing hard Gate 4 all-JSON findings observed during the same run: 6

> Updated after the PR #33 CodeRabbit review: the gate 1b qualitative-language
> lint was tuned (bare "about" narrowed to numeric-quantifier contexts;
> nearby-number radius 50 → 200), which removed the two prior gate 1b findings
> (`svyglm-cluster-robust-se` "warning about …"; `icc-cluster-bootstrap` "within
> Monte Carlo tolerance" — a soft statistical tolerance to be retrofitted via
> `enforced_by`, not a pinned expression). Gate 1b is now 0.

The warnings below are grouped by contract topic directory for TDA/panel retrofit assignment. They are warn-mode findings; the original hard gates remain blocking.

## Existing Hard Gate 4 Findings

- [gate 4] results\trajectory_tda_bhps\stage1\bhps_length_matched_truncate_frozen_2026-05-29.json:<root>: missing required key 'n_perm_used_observed' (schema: length-matched-run-params)
- [gate 4] results\trajectory_tda_bhps\stage1\bhps_length_matched_truncate_frozen_2026-05-29.json:<root>: missing required key 'covering_radius_at_n_perm_observed' (schema: length-matched-run-params)
- [gate 4] results\trajectory_tda_bhps\stage1\bhps_length_matched_truncate_frozen_2026-05-29.json:<root>: missing required key 'n_perm_used_null_summary' (schema: length-matched-run-params)
- [gate 4] results\trajectory_tda_bhps\stage1\bhps_length_matched_truncate_frozen_2026-05-29.json:<root>: missing required key 'covering_radius_at_n_perm_null_summary' (schema: length-matched-run-params)
- [gate 4] results\trajectory_tda_bhps\stage1\bhps_length_matched_truncate_frozen_2026-05-29.json:<root>: missing required key 'dedup_tolerance' (schema: length-matched-run-params)
- [gate 4] results\trajectory_tda_bhps\stage1\bhps_length_matched_truncate_frozen_2026-05-29.json:<root>: missing required key 'dedup_strategy' (schema: length-matched-run-params)

## foo-topology-schemas

- [gate 1c] comparator-feature-definitions: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] comparator-feature-definitions: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] comparator-feature-definitions: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] comparator-feature-definitions: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 2b] comparator-feature-definitions: binding.must_assert has 5 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_comparator_feature_definitions_construction plus called validators expose 0 negative assertion case(s)
- [gate 2b] per-individual-local-features-output: binding.must_assert has 6 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_per_individual_local_features_json_schema plus called validators expose 2 negative assertion case(s)
- [gate 2b] sibling-pair-permutation-output: binding.must_assert has 6 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_sibling_pair_permutation_json_schema plus called validators expose 3 negative assertion case(s)
- [gate 2b] topology-distinctiveness-comparison-output: binding.must_assert has 6 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_topology_distinctiveness_comparison_json_schema plus called validators expose 3 negative assertion case(s)

## panel-output-schemas

- [gate 2b] foo-sensitivity-fullsample-output: binding.must_assert has 5 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_foo_sensitivity_fullsample_json_schema plus called validators expose 1 negative assertion case(s)
- [gate 2b] nssec-regime-crosstab-output: binding.must_assert has 5 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_nssec_regime_crosstab_json_schema plus called validators expose 1 negative assertion case(s)
- [gate 2b] nssec-regime-crosstab-output: schema required key 'row_proportions' is not referenced as a string literal in tests/panel/test_t134_regression_contracts.py
- [gate 2b] nssec-regime-crosstab-output: schema required key 'col_proportions' is not referenced as a string literal in tests/panel/test_t134_regression_contracts.py
- [gate 2b] power-analysis-output: binding.must_assert has 9 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_power_analysis_json_schema plus called validators expose 3 negative assertion case(s)
- [gate 2b] sibling-concordance-output: binding.must_assert has 5 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_sibling_concordance_json_schema plus called validators expose 1 negative assertion case(s)
- [gate 2b] singleton-decomposition-output: binding.must_assert has 5 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_singleton_decomposition_json_schema plus called validators expose 1 negative assertion case(s)
- [gate 2b] tier2-ipw-mice-svyglm-output: binding.must_assert has 6 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_tier2_output_json_schema plus called validators expose 1 negative assertion case(s)

## regression-specs

- [gate 1c] normalised-ipw-trimming: formula.invariants[0] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] normalised-ipw-trimming: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] normalised-ipw-trimming: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] normalised-ipw-trimming: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] normalised-ipw-trimming: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] normalised-ipw-trimming: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] rubin-pooling: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] rubin-pooling: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] rubin-pooling: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] rubin-pooling: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[0] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] svyglm-cluster-robust-se: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[0] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] tier2-escape-regression-spec: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 2b] normalised-ipw-trimming: binding.must_assert has 7 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_normalised_ipw_trimming_rule plus called validators expose 1 negative assertion case(s)
- [gate 2b] rubin-pooling: binding.must_assert has 8 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_rubin_pooling_formula plus called validators expose 0 negative assertion case(s)
- [gate 2b] singleton-decomposition-exhaustivity: binding.must_assert has 6 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_singleton_decomposition_exhaustivity plus called validators expose 1 negative assertion case(s)
- [gate 2b] svyglm-cluster-robust-se: binding.must_assert has 5 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_svyglm_cluster_robust_se_construction plus called validators expose 0 negative assertion case(s)
- [gate 2b] tier2-escape-regression-spec: binding.must_assert has 7 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_tier2_escape_regression_spec plus called validators expose 1 negative assertion case(s)

## stage1-output-schemas

- [gate 2b] stage1-aggregate-output-cell: schema required key 'bca_ci_lower' is not referenced as a string literal in tests/trajectory_tda/test_stage1_battery_core_regressions.py
- [gate 2b] stage1-aggregate-output-cell: schema required key 'bca_ci_upper' is not referenced as a string literal in tests/trajectory_tda/test_stage1_battery_core_regressions.py
- [gate 2b] stage1-aggregate-output-cell: schema required key 'landscape_t_ratio' is not referenced as a string literal in tests/trajectory_tda/test_stage1_battery_core_regressions.py
- [gate 2b] stage1-aggregate-output-cell: schema required key 'landscape_bca_ci_lower' is not referenced as a string literal in tests/trajectory_tda/test_stage1_battery_core_regressions.py
- [gate 2b] stage1-aggregate-output-cell: schema required key 'landscape_bca_ci_upper' is not referenced as a string literal in tests/trajectory_tda/test_stage1_battery_core_regressions.py
- [gate 2b] stage1-aggregate-output-cell: schema required key 'landscape_d_perm' is not referenced as a string literal in tests/trajectory_tda/test_stage1_battery_core_regressions.py
- [gate 2b] stratified-markov1-output: schema required key 'pre_registration' is not referenced as a string literal in tests/trajectory_tda/test_stratified_markov_contracts.py
- [gate 2b] stratified-markov1-output: schema required key 'outcome_rule' is not referenced as a string literal in tests/trajectory_tda/test_stratified_markov_contracts.py
- [gate 2b] stratified-markov1-output: schema required key 'date' is not referenced as a string literal in tests/trajectory_tda/test_stratified_markov_contracts.py
- [pending-debt] length-matched-run-params-validation: pending:true but tests/trajectory_tda/test_length_matched_dedup_contracts.py::test_length_matched_run_params_jsons_validate_against_schema exists on this branch
- [pending-debt] length-matched-run-params: pending:true but tests/trajectory_tda/test_length_matched_dedup_contracts.py::test_length_matched_run_params_schema exists on this branch

## statistical-tests

- [gate 1c] cohens-kappa: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] cohens-kappa: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] cohens-kappa: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] cohens-kappa: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] cohens-kappa: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] cohens-kappa: formula.invariants[7] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] glmm-power-simulation: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] glmm-power-simulation: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] glmm-power-simulation: formula.invariants[8] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] mcnemar-test: formula.invariants[0] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] mcnemar-test: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] mcnemar-test: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] mcnemar-test: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] mcnemar-test: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] within-pair-odds-ratio: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] within-pair-odds-ratio: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] within-pair-odds-ratio: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] within-pair-odds-ratio: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] within-pair-odds-ratio: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 2b] cohens-kappa: binding.must_assert has 6 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_cohens_kappa_construction plus called validators expose 0 negative assertion case(s)
- [gate 2b] glmm-power-simulation: binding.must_assert has 9 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_glmm_power_simulation_construction plus called validators expose 0 negative assertion case(s)
- [gate 2b] mcnemar-test: binding.must_assert has 6 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_mcnemar_construction plus called validators expose 0 negative assertion case(s)
- [gate 2b] within-pair-odds-ratio: binding.must_assert has 6 lettered clause(s), but tests/panel/test_t135_transparency_contracts.py::test_within_pair_odds_ratio_construction plus called validators expose 0 negative assertion case(s)

## stochastic-tests

- [gate 1c] constrained-shuffle-null: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] constrained-shuffle-null: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] constrained-shuffle-null: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] constrained-shuffle-null: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] icc-cluster-bootstrap: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] icc-cluster-bootstrap: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] icc-cluster-bootstrap: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] monte-carlo-permutation-p-value-legacy: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] monte-carlo-permutation-p-value-legacy: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] monte-carlo-permutation-p-value-legacy: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] monte-carlo-permutation-p-value: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] monte-carlo-permutation-p-value: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] monte-carlo-permutation-p-value: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] sigma-foo-cluster-bootstrap: formula.invariants[0] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] sigma-foo-cluster-bootstrap: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] sigma-foo-cluster-bootstrap: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] sigma-foo-cluster-bootstrap: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] sigma-foo-cluster-bootstrap: formula.invariants[6] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 2b] constrained-shuffle-null: binding.must_assert has 5 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_constrained_shuffle_preserves_cluster_size_partition plus called validators expose 0 negative assertion case(s)
- [gate 2b] icc-cluster-bootstrap: binding.must_assert has 6 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_icc_cluster_bootstrap_construction plus called validators expose 0 negative assertion case(s)
- [gate 2b] sigma-foo-cluster-bootstrap: binding.must_assert has 6 lettered clause(s), but tests/panel/test_t134_regression_contracts.py::test_sigma_foo_cluster_bootstrap plus called validators expose 0 negative assertion case(s)

## topology-invariants

- [gate 1c] length-matched-dedup-via-n-perm: formula.invariants[0] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] length-matched-dedup-via-n-perm: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] length-matched-dedup-via-n-perm: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] length-matched-dedup-via-n-perm: formula.invariants[4] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] length-matched-dedup-via-n-perm: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] per-individual-knn-local-ph: formula.invariants[1] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] per-individual-knn-local-ph: formula.invariants[2] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] per-individual-knn-local-ph: formula.invariants[3] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 1c] per-individual-knn-local-ph: formula.invariants[5] has neither expression nor enforced_by; exactly one is required by the hardening gate
- [gate 2b] per-individual-knn-local-ph: binding.must_assert has 6 lettered clause(s), but tests/trajectory_tda/test_foo_topology_contracts.py::test_per_individual_knn_local_ph_construction plus called validators expose 0 negative assertion case(s)
- [pending-debt] dedup-equivalence-canary: pending:true but tests/trajectory_tda/test_length_matched_dedup_contracts.py::test_dedup_equivalence_canary_on_t12f_truncate_landmarks exists on this branch
- [pending-debt] length-matched-dedup-via-n-perm: pending:true but tests/trajectory_tda/test_length_matched_dedup_contracts.py::test_length_matched_dedup_via_n_perm_construction exists on this branch
