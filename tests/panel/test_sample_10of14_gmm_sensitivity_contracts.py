"""Contract bindings for gap-tolerant 10-of-14 GMM sensitivity results."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.analysis.panel.t127_sample_10of14_gmm_sensitivity import (
    SCHEMA_VERSION,
    TASK_NAME,
    validate_sample_10of14_gmm_output,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
SCHEMA_REL = "panel-output-schemas/sample-10of14-gmm-sensitivity-output.yaml"
OUTPUT_VALIDATION_REL = "panel-output-schemas/sample-10of14-gmm-sensitivity-output-json-validation.yaml"
OUTPUT_GLOB = "results/panel_methodology/selection_sensitivity/gmm_10of14_*.json"


def _load_contract(rel_path: str) -> dict[str, Any]:
    with (CONTRACTS_DIR / rel_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    return [path for path in REPO_ROOT.rglob("*.json") if path.relative_to(REPO_ROOT).full_match(glob_pattern)]


def _valid_payload() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-06-07T00:00:00+00:00",
        "task": TASK_NAME,
        "pre_registration": "2026-06-07 T1.27 pre-registration",
        "inputs": {
            "eligible_population_source": "UKHLS waves a-n valid employment-income states",
            "original_gmm_labels_source": "results/trajectory_tda_integration/05_analysis.json[gmm_labels]",
            "n_eligible": 100,
            "git_head": "abc123",
        },
        "params": {
            "presence_rule": "10-of-14",
            "length_variance_standardisation": True,
            "pca_dim": 20,
            "pca_svd_solver": "full",
            "frozen_loadings": True,
            "gmm_k": 7,
            "gmm_covariance_type": "full",
            "seed": 42,
        },
        "results": {
            "n_sample": 50,
            "sample_fraction_of_eligible": 0.5,
            "gmm_converged": True,
            "ari_vs_original": 0.91,
        },
        "baseline_comparison": [
            {
                "characteristic": name,
                "included": {"n_nonmissing": 50},
                "excluded": {"n_nonmissing": 50},
            }
            for name in [
                "age_at_entry",
                "sex",
                "initial_hiqual_dv",
                "initial_employment_status",
                "initial_income_band",
            ]
        ],
    }


def _assert_valid(payload: dict[str, Any]) -> None:
    try:
        validate_sample_10of14_gmm_output(payload)
    except ValueError as exc:
        raise AssertionError(str(exc)) from exc


def test_sample_10of14_gmm_sensitivity_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_valid(_valid_payload())

    # (a) pinned parameter violations reject.
    bad = _valid_payload()
    bad["params"]["presence_rule"] = "14-of-14"
    bad["params"]["pca_svd_solver"] = "randomized"
    bad["params"]["frozen_loadings"] = False
    bad["params"]["gmm_k"] = 6
    bad["params"]["seed"] = 99
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    # (b) sample fraction outside [0, 1] rejects.
    bad = _valid_payload()
    bad["results"]["sample_fraction_of_eligible"] = 1.1
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    # (c) ARI outside [-1, 1] rejects.
    bad = _valid_payload()
    bad["results"]["ari_vs_original"] = -1.2
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    # (d) fewer than five baseline comparison entries rejects.
    bad = _valid_payload()
    bad["baseline_comparison"] = bad["baseline_comparison"][:4]
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    # (e) forbidden keys reject.
    for forbidden_key in ("full_tda_rerun", "per_call_pca"):
        bad = _valid_payload()
        bad[forbidden_key] = True
        with pytest.raises(AssertionError):
            _assert_valid(bad)


def test_sample_10of14_gmm_sensitivity_json_validation_dispatch() -> None:
    output_validation = _load_contract(OUTPUT_VALIDATION_REL)
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == OUTPUT_GLOB
    assert ov["schema_contracts"] == ["sample-10of14-gmm-sensitivity-output"]
    assert Path("results/panel_methodology/selection_sensitivity/gmm_10of14_2026-06-07.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path(
        "results/panel_methodology/selection_sensitivity/gmm_multistart_checkpoint_2026-06-07.json"
    ).full_match(ov["applies_to_glob"])
    assert _load_contract(SCHEMA_REL)["binding"]["test_function"] == (
        "test_sample_10of14_gmm_sensitivity_output_schema"
    )

    matched = _matched_jsons(ov["applies_to_glob"])
    assert matched, f"no result JSON matched dispatch glob {ov['applies_to_glob']}"
    for json_path in matched:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        validate_sample_10of14_gmm_output(payload)


def test_sample_10of14_validator_is_pure_for_valid_payload() -> None:
    payload = _valid_payload()
    before = copy.deepcopy(payload)
    _assert_valid(payload)
    assert payload == before
