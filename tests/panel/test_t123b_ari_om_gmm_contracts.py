from pathlib import Path

import pytest

from trajectory_tda.analysis.panel.t123b_ari_om_gmm import (
    CANARY_OBSERVED_ARI,
    EXPECTED_N,
    GMM_K,
    OM_K,
    dispatch_t123b_json,
    validate_ari_om_gmm_output,
)


def test_ari_om_gmm_normalisation_output_schema():
    payload = _om_payload()
    validate_ari_om_gmm_output(payload)

    # (a) schema_version must be the OM-vs-GMM tag.
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(_mutated("schema_version", "ari-normalisation-v1"))

    # (b) referent must name optimal-matching k=7 vs GMM k=7.
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(_mutated("referent", "H0 tree-cut vs GMM"))

    # (c) input paths and gmm_labels_key must be canonical.
    bad_paths = _om_payload()
    bad_paths["input_paths"]["trajectories"] = "results/other/stale_sequences.json"
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_paths)
    bad_key = _om_payload()
    bad_key["input_paths"]["gmm_labels_key"] = "pickle_labels"
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_key)

    # (d) representation must not use pickle/joblib labels.
    bad_repr = _om_payload()
    bad_repr["representation"]["uses_pickle_or_joblib_labels"] = True
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_repr)

    # (e) locked parameters and label counts.
    bad_om_k = _om_payload()
    bad_om_k["parameters"]["om_k"] = 6
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_om_k)
    bad_gmm_k = _om_payload()
    bad_gmm_k["parameters"]["gmm_k"] = 8
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_gmm_k)
    bad_seed = _om_payload()
    bad_seed["parameters"]["seed"] = 7
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_seed)
    bad_n = _om_payload()
    bad_n["label_counts"]["om_label_length"] = EXPECTED_N - 1
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_n)
    bad_cluster_count = _om_payload()
    bad_cluster_count["label_counts"]["om_cluster_count"] = 6
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_cluster_count)

    # (f) observed_ari must be in range and reproduce the canary.
    bad_range = _om_payload()
    bad_range["observed_ari"] = 1.5
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_range)
    bad_canary = _om_payload()
    bad_canary["observed_ari"] = 0.40
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_canary)

    # (g) null se sign and bootstrap CI ordering.
    bad_null = _om_payload()
    bad_null["null_distribution"]["se"] = -0.1
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_null)
    bad_ci = _om_payload()
    bad_ci["bootstrap_ci"]["percentile_95"] = [0.30, 0.10]
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_ci)

    # (h) exact / status / normalised-key logic must be consistent.
    bad_status = _om_payload()
    bad_status["max_achievable_ari"]["status"] = "upper_bound"
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_status)

    # (i) forbidden keys (object-confusion guard versus T1.23).
    bad_eps = _om_payload()
    bad_eps["eps_star"] = 0.54
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_eps)
    bad_h0 = _om_payload()
    bad_h0["h0_components"] = {"n_components": 2}
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_h0)
    bad_pickle = _om_payload()
    bad_pickle["pickle_labels_path"] = "old.pkl"
    with pytest.raises(AssertionError):
        validate_ari_om_gmm_output(bad_pickle)


def test_ari_om_gmm_normalisation_json_validation_dispatch():
    payload = _om_payload()
    # OM-vs-GMM files are routed to the schema validator.
    assert dispatch_t123b_json(
        Path("results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-22.json"),
        payload,
    )
    with pytest.raises(AssertionError):
        dispatch_t123b_json(
            Path("results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-22.json"),
            _mutated("schema_version", "wrong"),
        )
    # (b) The H0-tree-cut ari_normalised_*.json file is NOT captured.
    assert not dispatch_t123b_json(
        Path("results/panel_methodology/ari/ari_normalised_2026-06-06.json"),
        {"schema_version": "ari-normalisation-v1"},
    )
    # Other panel methodology JSONs are NOT captured.
    assert not dispatch_t123b_json(
        Path("results/panel_methodology/regression/tier2_svyglm_headline_2026-06-03.json"),
        {"schema_version": "unrelated"},
    )


def _mutated(key, value):
    payload = _om_payload()
    payload[key] = value
    return payload


def _om_payload():
    return {
        "schema_version": "ari-om-gmm-normalisation-v1",
        "created_at": "2026-06-22",
        "git_head": "abc123",
        "referent": ("optimal-matching (dynamic Hamming, Lesnard 2010) k=7 vs GMM k=7"),
        "input_paths": {
            "trajectories": ("C:/Users/steph/TDL/results/trajectory_tda_integration/01_trajectories_sequences.json"),
            "analysis_json": ("C:/Users/steph/TDL/results/trajectory_tda_integration/05_analysis.json"),
            "gmm_labels_key": "gmm_labels",
        },
        "representation": {
            "om_label_source": "fcluster(k=7) of Ward linkage (dynamic Hamming)",
            "gmm_label_source": "canonical 05_analysis.json['gmm_labels']",
            "om_baseline_directory": ("C:/Users/steph/TDL/results/trajectory_tda_robustness/om_baseline"),
            "row_alignment": "same trajectory/GMM row order, both length 27,280",
            "uses_pickle_or_joblib_labels": False,
            "regenerated_linkage": True,
        },
        "parameters": {
            "om_k": OM_K,
            "gmm_k": GMM_K,
            "om_distance": "dynamic Hamming distance (Lesnard 2010), Ward linkage",
            "seed": 42,
            "null_B_requested": 5000,
            "bootstrap_B_requested": 1000,
            "n_jobs": 8,
        },
        "label_counts": {
            "n": EXPECTED_N,
            "om_label_length": EXPECTED_N,
            "gmm_label_length": EXPECTED_N,
            "om_cluster_count": OM_K,
            "om_cluster_counts": {str(i): EXPECTED_N // OM_K for i in range(OM_K)},
            "gmm_regime_count": GMM_K,
            "gmm_regime_counts": {str(i): EXPECTED_N // GMM_K for i in range(GMM_K)},
        },
        "observed_ari": CANARY_OBSERVED_ARI,
        "null_distribution": {
            "procedure": "Permute GMM labels relative to fixed OM k=7 labels.",
            "B": 5000,
            "seed": 42,
            "finite_count": 5000,
            "failures_non_finite": 0,
            "mean": 0.0,
            "se": 0.0009,
            "pvalue": 0.0002,
            "pvalue_definition": "(r + 1) / (B + 1)",
            "exceedances_observed_or_larger": 0,
            "quantiles": {"0.025": -0.001, "0.5": 0.0, "0.975": 0.001},
        },
        "max_achievable_ari": {
            "value": 0.62,
            "exact": True,
            "status": "exact",
            "method": "exact whole-cluster packing certificate",
            "pair_overlap_sum": 100,
            "unsplit_non_singleton_components": 7,
            "split_non_singleton_components": 0,
            "normalised_observed_ari": 0.42,
        },
        "bootstrap_ci": {
            "procedure": "Resample paired individual rows (OM label, GMM label).",
            "resampling_unit": "individual",
            "B": 1000,
            "seed": 42,
            "finite_count": 1000,
            "failures_non_finite": 0,
            "mean": 0.261,
            "se": 0.004,
            "percentile_95": [0.253, 0.269],
        },
        "interpretation": {
            "statistic_role": "descriptive clustering-agreement statistic",
            "closes_b9": True,
            "claim": "OM k=7 and GMM k=7 agree at ARI = 0.26 (closes B9).",
            "causal_claim": "none",
            "topological_distinctiveness_claim": "none",
            "normalisation_basis": "exact",
            "paper_claim_guardrail": "Report only as OM-vs-GMM agreement.",
        },
        "runtime": {"wall_seconds": 12.0},
    }
