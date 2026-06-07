from pathlib import Path

import pytest

from trajectory_tda.analysis.panel.t123_ari_normalisation import (
    DEFAULT_BOOT_B,
    DEFAULT_EPS_STAR,
    DEFAULT_NULL_B,
    DEFAULT_SEED,
    EXPECTED_N,
    dispatch_t123_json,
    validate_ari_normalisation_output,
)


def test_ari_normalisation_output_schema():
    payload = _ari_payload()
    validate_ari_normalisation_output(payload)

    bad_schema = _mutated("schema_version", "wrong")
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_schema)

    bad_paths = _ari_payload()
    bad_paths["input_paths"]["embeddings"] = "results/trajectory_tda_integration/stale.npy"
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_paths)
    bad_key = _ari_payload()
    bad_key["input_paths"]["gmm_labels_key"] = "pickle_labels"
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_key)

    bad_representation = _ari_payload()
    bad_representation["representation"]["uses_pickle_or_joblib_labels"] = True
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_representation)
    bad_alignment = _ari_payload()
    bad_alignment["representation"]["row_alignment"] = "reordered by pidp"
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_alignment)

    bad_eps = _ari_payload()
    bad_eps["parameters"]["eps_star"] = 0.55
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_eps)
    bad_n = _ari_payload()
    bad_n["label_counts"]["h0_label_length"] = EXPECTED_N - 1
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_n)

    bad_observed = _ari_payload()
    bad_observed["observed_ari"] = 1.5
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_observed)
    bad_max = _ari_payload()
    bad_max["max_achievable_ari"]["value"] = float("inf")
    with pytest.raises(AssertionError, match="max_ari"):
        validate_ari_normalisation_output(bad_max)

    bad_null = _ari_payload()
    bad_null["null_distribution"]["se"] = -0.1
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_null)
    bad_ci = _ari_payload()
    bad_ci["bootstrap_ci"]["percentile_95"] = [0.2, 0.1]
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_ci)

    bad_status = _ari_payload()
    bad_status["max_achievable_ari"]["status"] = "upper_bound"
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_status)
    bad_upper_key = _ari_payload()
    del bad_upper_key["max_achievable_ari"]["normalised_observed_ari"]
    bad_upper_key["max_achievable_ari"]["exact"] = False
    bad_upper_key["max_achievable_ari"]["status"] = "upper_bound"
    with pytest.raises(AssertionError):
        validate_ari_normalisation_output(bad_upper_key)

    bad_forbidden = _ari_payload()
    bad_forbidden["pickle_labels_path"] = "old.pkl"
    with pytest.raises(AssertionError, match="forbidden"):
        validate_ari_normalisation_output(bad_forbidden)


def test_ari_normalisation_json_validation_dispatch():
    payload = _ari_payload()
    assert dispatch_t123_json(
        Path("results/panel_methodology/ari/ari_normalised_2026-06-06.json"),
        payload,
    )
    with pytest.raises(AssertionError):
        dispatch_t123_json(
            Path("results/panel_methodology/ari/ari_normalised_2026-06-06.json"),
            _mutated("schema_version", "wrong"),
        )
    assert not dispatch_t123_json(
        Path("results/panel_methodology/regression/tier2_svyglm_headline_2026-06-03.json"),
        {"schema_version": "unrelated"},
    )


def _mutated(key, value):
    payload = _ari_payload()
    payload[key] = value
    return payload


def _ari_payload():
    return {
        "schema_version": "ari-normalisation-v1",
        "created_at": "2026-06-06",
        "git_head": "abc123",
        "input_paths": {
            "embeddings": "C:/Users/steph/TDL/results/trajectory_tda_integration/embeddings.npy",
            "analysis_json": "C:/Users/steph/TDL/results/trajectory_tda_integration/05_analysis.json",
            "gmm_labels_key": "gmm_labels",
        },
        "representation": {
            "embedding_source": "canonical embeddings.npy",
            "gmm_label_source": "canonical 05_analysis.json['gmm_labels']",
            "checkpoint_directory": "C:/Users/steph/TDL/results/trajectory_tda_integration",
            "row_alignment": "same checkpoint directory and row order",
            "row_alignment_justification": "same checkpoint directory and length checks",
            "uses_pickle_or_joblib_labels": False,
        },
        "parameters": {
            "eps_star": DEFAULT_EPS_STAR,
            "h0_label_method": "radius graph connected components",
            "seed": DEFAULT_SEED,
            "null_B_requested": DEFAULT_NULL_B,
            "bootstrap_B_requested": DEFAULT_BOOT_B,
            "n_jobs": 4,
        },
        "label_counts": {
            "n": EXPECTED_N,
            "h0_label_length": EXPECTED_N,
            "gmm_label_length": EXPECTED_N,
            "h0_components": {
                "n_components": 2,
                "graph_nnz": 10,
                "largest_component_sizes": [EXPECTED_N - 1, 1],
                "component_size_histogram": {"1": 1, str(EXPECTED_N - 1): 1},
                "n_singleton_components": 1,
                "n_non_singleton_components": 1,
            },
            "h0_component_counts": {"0": EXPECTED_N - 1, "1": 1},
            "gmm_regime_count": 2,
            "gmm_regime_counts": {"0": 10000, "1": EXPECTED_N - 10000},
        },
        "observed_ari": 0.1,
        "null_distribution": {
            "procedure": "permute GMM labels relative to fixed H0 labels",
            "B": 5000,
            "seed": DEFAULT_SEED,
            "finite_count": 5000,
            "failures_non_finite": 0,
            "mean": 0.0,
            "se": 0.01,
            "pvalue_upper_tail_bias_corrected": 0.001,
            "exceedances_observed_or_larger": 0,
            "quantiles": {"0.025": -0.01, "0.5": 0.0, "0.975": 0.01},
        },
        "max_achievable_ari": {
            "value": 0.5,
            "normalised_observed_ari": 0.2,
            "exact": True,
            "status": "exact",
            "method": "exact whole-row packing certificate",
            "pair_overlap_sum": 10,
            "unsplit_non_singleton_components": 1,
            "split_non_singleton_components": 0,
        },
        "bootstrap_ci": {
            "procedure": "resample paired individual rows",
            "resampling_unit": "individual",
            "B": 1000,
            "seed": DEFAULT_SEED,
            "finite_count": 1000,
            "failures_non_finite": 0,
            "mean": 0.1,
            "se": 0.02,
            "percentile_95": [0.08, 0.12],
        },
        "interpretation": {
            "statistic_role": "descriptive agreement statistic",
            "causal_claim": "none",
            "topological_distinctiveness_claim": "none",
            "normalisation_basis": "exact",
            "paper_claim_guardrail": "report only as exact normalised ARI when exact is true",
        },
        "runtime": {"wall_seconds": 1.0},
    }
