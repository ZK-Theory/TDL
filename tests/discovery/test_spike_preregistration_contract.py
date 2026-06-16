"""Contract bindings for Discovery Harness Spike pre-registrations."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.discovery.spike_preregistration import validate_spike_preregistration

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
DISCOVERY_CONTRACT = "discovery-harness/spike-pre-registration.yaml"


def _load_contract(rel_path: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _valid_prereg() -> dict[str, Any]:
    return {
        "schema_version": "discovery/spike-pre-registration/v1",
        "candidate_slug": "strand-persistence-survival-testing",
        "source_scorecard": "vault/00-Meta/Discovery/strand-persistence-survival-testing.md",
        "registered_at": "2026-06-16",
        "approval": {
            "approved": True,
            "approved_by": "Stephen",
            "approved_at": "2026-06-16",
        },
        "time_box_hours": 4,
        "research_question": "Can STRAND add calibrated persistence-diagram testing power?",
        "metric_space": "Persistence diagrams already produced by P01-B.",
        "toy_scope": {
            "dataset": "existing P01-B diagrams",
            "max_units": 100,
            "compute_budget": "toy subset only",
        },
        "topology_gate": {
            "assay_gate_passed": True,
            "feature_claim_map": "STRAND survival curves localise group differences.",
            "named_baseline": "Existing W2 and landscape L2 permutation tests.",
        },
        "null_model": {
            "operation": "reuse the existing label/permutation null at toy scale",
            "invariance_risk": "STRAND must consume the perturbed diagram summaries, not cached labels.",
        },
        "baselines": ["W2 permutation test", "landscape L2 permutation test"],
        "decision_rule": {
            "success_criteria": [
                "STRAND can be computed on the toy subset",
                "A test statistic and null are explicitly defined",
            ],
            "failure_criteria": [
                "No implementable STRAND summary is available",
                "The null operation does not perturb the STRAND input",
            ],
        },
        "outcome_to_prose": {
            "success": "Open an APM task to compare STRAND against current baselines.",
            "partial": "Record implementation gap and park until method details improve.",
            "failure": "Write a NEGATIVE note and keep current W2/landscape testing.",
        },
        "planned_contracts": ["spike-result-summary"],
        "next_on_success": "/pre-reg-to-dispatch",
        "next_on_failure": "write [NEGATIVE] note and update Discovery backlog",
    }


def _mutated(path: tuple[str, ...], value: object) -> dict[str, Any]:
    payload = copy.deepcopy(_valid_prereg())
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return payload


def test_spike_preregistration_schema_rejects_invalid_seam_logic() -> None:
    """Representative pre-reg passes; seam-breaking variants reject."""
    validate_spike_preregistration(_valid_prereg())

    # (a) User approval is required before a promoted candidate can run a Spike.
    bad = _mutated(("approval", "approved"), False)
    with pytest.raises(AssertionError, match="approval"):
        validate_spike_preregistration(bad)

    # (b) The Spike must be time-boxed to a few hours.
    bad = _mutated(("time_box_hours",), 8)
    with pytest.raises(AssertionError, match="time_box_hours"):
        validate_spike_preregistration(bad)

    # (c) The Assay topology gate remains hard at the Spike seam.
    bad = _mutated(("topology_gate", "assay_gate_passed"), False)
    with pytest.raises(AssertionError, match="topology gate"):
        validate_spike_preregistration(bad)

    # (d) A named baseline, null model, and outcome-to-prose map are mandatory.
    bad = _mutated(("topology_gate", "named_baseline"), "")
    with pytest.raises(AssertionError, match="named_baseline"):
        validate_spike_preregistration(bad)

    bad = _mutated(("null_model", "operation"), "")
    with pytest.raises(AssertionError, match="null_model.operation"):
        validate_spike_preregistration(bad)

    bad = _valid_prereg()
    del bad["outcome_to_prose"]["partial"]
    with pytest.raises(AssertionError, match="outcome_to_prose"):
        validate_spike_preregistration(bad)

    # (e) Successful Spikes must hand off through pre-reg-to-dispatch.
    bad = _mutated(("next_on_success",), "start APM directly")
    with pytest.raises(AssertionError, match="pre-reg-to-dispatch"):
        validate_spike_preregistration(bad)


def test_spike_preregistration_contract_binding() -> None:
    contract = _load_contract(DISCOVERY_CONTRACT)
    assert contract["id"] == "spike-pre-registration"
    assert contract["kind"] == "schema"
    assert contract["binding"]["test_file"] == "tests/discovery/test_spike_preregistration_contract.py"
    assert contract["binding"]["test_function"] == "test_spike_preregistration_schema_rejects_invalid_seam_logic"

    required = [entry["name"] for entry in contract["schema_def"]["required_keys"]]
    assert required == [
        "schema_version",
        "candidate_slug",
        "source_scorecard",
        "registered_at",
        "approval",
        "time_box_hours",
        "research_question",
        "metric_space",
        "toy_scope",
        "topology_gate",
        "null_model",
        "baselines",
        "decision_rule",
        "outcome_to_prose",
        "planned_contracts",
        "next_on_success",
        "next_on_failure",
    ]
