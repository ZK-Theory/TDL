from copy import deepcopy

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.replay.transactions import (
    STATEFUL_COMMAND_BINDINGS,
    TRANSACTION_CONTRACTS,
    validate_transaction_contract,
)
from research_system.discovery.routes import DISCOVERY_ROW_ROUTES
from research_system.errors import IntegrityError


def _event(event_type: str, stream_id: str, payload: dict[str, object], command_type: str) -> dict[str, object]:
    return {
        "event_type": event_type,
        "stream_id": stream_id,
        "command_type": command_type,
        "command_payload_hash": sha256_hex(canonical_bytes(payload)),
        "payload": deepcopy(payload),
    }


def test_transaction_registry_covers_every_executable_route() -> None:
    assert set(TRANSACTION_CONTRACTS) == set(DISCOVERY_ROW_ROUTES)
    assert all(
        TRANSACTION_CONTRACTS[row_id].command_type == route.command_type
        for row_id, route in DISCOVERY_ROW_ROUTES.items()
    )
    assert {contract.command_payload_binding for contract in TRANSACTION_CONTRACTS.values()} == {
        "durable",
        "stateful",
    }
    assert {
        row_id for row_id, contract in TRANSACTION_CONTRACTS.items() if contract.command_payload_binding == "stateful"
    } == set(STATEFUL_COMMAND_BINDINGS)


def test_transaction_rejects_conflicting_owner_rows_and_wrong_command_route() -> None:
    payload = {
        "row_id": "OR-004",
        "candidate_id": "candidate",
        "assay_id": "assay",
        "scorecard_sha256": "1" * 64,
        "scorecard_artifact": {"mechanical_recommendation": "PROMOTE"},
        "producer_relation_sha256": "2" * 64,
    }
    events = (
        _event("AssayScored", "assay", payload, "RecordAssayScore"),
        _event("CandidateAssayLinked", "candidate", payload, "RecordAssayScore"),
    )
    conflicting = deepcopy(events)
    conflicting[1]["payload"]["row_id"] = "OR-005"
    with pytest.raises(IntegrityError, match="conflicting W11 owner rows"):
        validate_transaction_contract(conflicting)

    wrong_command = deepcopy(events)
    for event in wrong_command:
        event["command_type"] = "CancelDiscoveryEvaluation"
    with pytest.raises(IntegrityError, match="route mismatch"):
        validate_transaction_contract(wrong_command)


def test_transaction_binds_assay_score_to_command_digest_and_assay_stream() -> None:
    score_payload = {
        "row_id": "OR-004",
        "candidate_id": "candidate",
        "assay_id": "assay",
        "scorecard_sha256": "1" * 64,
        "scorecard_artifact": {"mechanical_recommendation": "PROMOTE", "value": True},
        "producer_relation_sha256": "2" * 64,
    }
    scored = (
        _event("AssayScored", "assay", score_payload, "RecordAssayScore"),
        _event("CandidateAssayLinked", "candidate", score_payload, "RecordAssayScore"),
    )
    validate_transaction_contract(scored)
    rewritten = deepcopy(scored)
    for event in rewritten:
        event["payload"]["scorecard_artifact"] = {"mechanical_recommendation": "KILL", "value": False}
        event["payload"]["scorecard_sha256"] = "3" * 64
    with pytest.raises(IntegrityError, match="command payload mismatch for OR-004"):
        validate_transaction_contract(rewritten)

    cancellation_payload = {
        "row_id": "OR-008",
        "evaluation_kind": "assay",
        "candidate_id": "candidate",
        "assay_id": "assay",
        "cancellation_sha256": "4" * 64,
        "cancellation_artifact": {"reason": "stop"},
    }
    cancelled = (
        _event("AssayCancelled", "foreign", cancellation_payload, "CancelDiscoveryEvaluation"),
        _event("CandidateEvaluationCancelled", "candidate", cancellation_payload, "CancelDiscoveryEvaluation"),
    )
    with pytest.raises(IntegrityError, match="stream mismatch for OR-008"):
        validate_transaction_contract(cancelled)
