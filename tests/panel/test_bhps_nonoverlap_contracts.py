# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Contract bindings for the T1.26 BHPS non-overlap result schema and
#   JSON-validation dispatch.
"""Contract bindings for BHPS non-overlap sensitivity results."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.analysis.panel.t126_bhps_nonoverlap import (
    SCHEMA_VERSION,
    TASK_NAME,
    validate_bhps_nonoverlap_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
SCHEMA_REL = "panel-output-schemas/bhps-nonoverlap-output.yaml"
OUTPUT_VALIDATION_REL = "panel-output-schemas/bhps-nonoverlap-output-json-validation.yaml"
OUTPUT_GLOB = "results/panel_methodology/bhps_nonoverlap/bhps_only_gmm_ph_*.json"


def _load_contract(rel_path: str) -> dict[str, Any]:
    with (CONTRACTS_DIR / rel_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    return [path for path in REPO_ROOT.rglob("*.json") if path.relative_to(REPO_ROOT).full_match(glob_pattern)]


def _valid_payload() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-06-08T00:00:00+00:00",
        "task": TASK_NAME,
        "pre_registration": "2026-06-08 T1.26 pre-registration",
        "inputs": {
            "full_bhps_source": "results/trajectory_tda_bhps/01_trajectories.json",
            "spanning_ids_source": "results/trajectory_tda_spanning/01_trajectories.json[metadata.pidp]",
            "baseline_bhps_gmm_labels_source": "results/trajectory_tda_bhps/05_analysis.json[gmm_labels]",
            "git_head": "abc123",
        },
        "params": {
            "gmm_k": 8,
            "gmm_covariance_type": "full",
            "gmm_n_init": 5,
            "gmm_max_iter": 200,
            "seed": 42,
            "pca_dim": 20,
            "pca_svd_solver": "full",
            "frozen_loadings": True,
            "L": 5000,
            "B": 1000,
            "p_value_formula": "(r+1)/(B+1)",
            "alpha_level": 0.05,
            "ari_stability_threshold": 0.9,
        },
        "results": {
            "n_bhps_full": 8509,
            "n_spanning_excluded": 5307,
            "n_bhps_only": 3202,
            "ari_vs_full": 0.91,
            "regime_stable": True,
            "persistence": {
                "h0_w2_p": 0.001,
                "h1_w2_p": 0.08,
                "h0_rejects": True,
                "h1_asymmetry_preserved": True,
            },
        },
        "decision": {
            "primary_preserved": True,
            "outcome": "supported",
        },
    }


def _assert_valid(payload: dict[str, Any]) -> None:
    try:
        validate_bhps_nonoverlap_payload(payload)
    except ValueError as exc:
        raise AssertionError(str(exc)) from exc


def test_bhps_nonoverlap_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_valid(_valid_payload())

    bad = _valid_payload()
    bad["params"]["gmm_k"] = 7
    bad["params"]["seed"] = 99
    bad["params"]["ari_stability_threshold"] = 0.8
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["results"]["n_bhps_only"] = 3203
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["results"]["ari_vs_full"] = 0.89
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["results"]["persistence"]["h0_w2_p"] = 0.06
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["results"]["persistence"]["h1_w2_p"] = 1.2
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["decision"]["outcome"] = "overlap_dependent"
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["per_call_pca"] = True
    with pytest.raises(AssertionError):
        _assert_valid(bad)


def test_bhps_nonoverlap_json_validation_dispatch() -> None:
    """Dispatch contract targets the result glob and validates matched JSONs."""
    output_validation = _load_contract(OUTPUT_VALIDATION_REL)
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == OUTPUT_GLOB
    assert ov["schema_contracts"] == ["bhps-nonoverlap-output"]
    assert Path("results/panel_methodology/bhps_nonoverlap/bhps_only_gmm_ph_2026-06-08.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/panel_methodology/bhps_nonoverlap/pre_registrations_2026-06-08.json").full_match(
        ov["applies_to_glob"]
    )
    assert _load_contract(SCHEMA_REL)["binding"]["test_function"] == "test_bhps_nonoverlap_output_schema"

    matched = _matched_jsons(ov["applies_to_glob"])
    for json_path in matched:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        validate_bhps_nonoverlap_payload(payload)


def test_bhps_nonoverlap_validator_is_pure_for_valid_payload() -> None:
    """Validator does not mutate a valid payload."""
    payload = _valid_payload()
    before = copy.deepcopy(payload)
    _assert_valid(payload)
    assert payload == before
