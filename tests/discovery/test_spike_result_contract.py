"""Contract bindings for Discovery Harness Spike result summaries."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.discovery.spike_result import validate_spike_result

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
DISCOVERY_CONTRACT = "discovery-harness/spike-result-summary.yaml"


def _load_contract(rel_path: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _valid_result() -> dict[str, Any]:
    return {
        "schema_version": "discovery/spike-result-summary/v1",
        "candidate_slug": "strand-persistence-survival-testing",
        "source_preregistration": "vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.md",
        "completed_at": "2026-06-16",
        "outcome": "success",
        "time_box_hours_used": 3,
        "metric_space_confirmed": True,
        "toy_signal_status": "detected",
        "null_model_status": {
            "defined": True,
            "perturbs_input": True,
            "evidence": "Toy permutation changes the STRAND input summaries.",
        },
        "baseline_comparison": {
            "baselines": ["W2 permutation test", "landscape L2 permutation test"],
            "result": "STRAND produced an interpretable toy contrast.",
        },
        "research_assurance_evidence": {
            "topology": "Persistence-diagram summaries consumed directly.",
            "null_model": "Permutation operation perturbed the evaluated summaries.",
            "representation": "Existing frozen P01-B diagrams were reused.",
            "provenance": "Toy subset and source paths recorded.",
        },
        "artifacts": ["results/discovery/strand/toy_summary.json"],
        "decision": "dispatch",
        "next": "/pre-reg-to-dispatch",
    }


def _mutated(path: tuple[str, ...], value: object) -> dict[str, Any]:
    payload = copy.deepcopy(_valid_result())
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return payload


def test_spike_result_summary_rejects_invalid_success_logic() -> None:
    """Representative result passes; success-breaking variants reject."""
    validate_spike_result(_valid_result())

    # (a) Success requires metric-space confirmation.
    bad = _mutated(("metric_space_confirmed",), False)
    with pytest.raises(AssertionError, match="metric_space_confirmed"):
        validate_spike_result(bad)

    # (b) Success requires a defined null that perturbs the actual input.
    bad = _mutated(("null_model_status", "defined"), False)
    with pytest.raises(AssertionError, match="null_model_status.defined"):
        validate_spike_result(bad)

    bad = _mutated(("null_model_status", "perturbs_input"), False)
    with pytest.raises(AssertionError, match="perturbs_input"):
        validate_spike_result(bad)

    # (c) Success must hand off through pre-reg-to-dispatch.
    bad = _mutated(("next",), "open APM task directly")
    with pytest.raises(AssertionError, match="pre-reg-to-dispatch"):
        validate_spike_result(bad)

    # (d) Partial/failure outcomes must not pretend to dispatch.
    bad = _mutated(("outcome",), "partial")
    bad["decision"] = "dispatch"
    with pytest.raises(AssertionError, match="partial"):
        validate_spike_result(bad)

    # (e) Research assurance lanes are required for result review.
    bad = _valid_result()
    del bad["research_assurance_evidence"]["null_model"]
    with pytest.raises(AssertionError, match="research_assurance_evidence"):
        validate_spike_result(bad)


def test_spike_result_summary_contract_binding() -> None:
    contract = _load_contract(DISCOVERY_CONTRACT)
    assert contract["id"] == "spike-result-summary"
    assert contract["kind"] == "schema"
    assert contract["binding"]["test_file"] == "tests/discovery/test_spike_result_contract.py"
    assert contract["binding"]["test_function"] == "test_spike_result_summary_rejects_invalid_success_logic"

    required = [entry["name"] for entry in contract["schema_def"]["required_keys"]]
    assert required == [
        "schema_version",
        "candidate_slug",
        "source_preregistration",
        "completed_at",
        "outcome",
        "time_box_hours_used",
        "metric_space_confirmed",
        "toy_signal_status",
        "null_model_status",
        "baseline_comparison",
        "research_assurance_evidence",
        "artifacts",
        "decision",
        "next",
    ]
