from copy import deepcopy

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.replay.transactions import (
    TRANSACTION_CONTRACTS,
    validate_transaction_contract,
)
from research_system.discovery.routes import DISCOVERY_ROW_ROUTES
from research_system.errors import IntegrityError


_SATISFIED_REVIEW_WRITE_SETS = {
    "OR-006": ("ReviewVerdictRecorded", "AssayReviewed"),
    "OR-007": ("ReviewVerdictRecorded", "AssayPartialReviewed", "CandidateAssayPartialReviewed"),
    "OR-020": ("ReviewVerdictRecorded", "SpikeReviewed"),
    "OR-021": ("ReviewVerdictRecorded", "SpikePartialReviewed", "CandidateSpikePartialReviewed"),
    "OR-039": ("ReviewVerdictRecorded", "AssayCancellationReviewed", "CandidateAssayCancellationReviewed"),
    "OR-041": ("ReviewVerdictRecorded", "SpikeCancellationReviewed", "CandidateSpikeCancellationReviewed"),
}


def _event(event_type: str, stream_id: str, payload: dict[str, object], command_type: str) -> dict[str, object]:
    return {
        "event_type": event_type,
        "stream_id": stream_id,
        "command_type": command_type,
        "command_payload_hash": sha256_hex(canonical_bytes(payload)),
        "payload": deepcopy(payload),
    }


def _review_stream(event_type: str, payload: dict[str, object]) -> str:
    if event_type == "ReviewVerdictRecorded":
        return str(payload["review_id"])
    if event_type.startswith("Candidate"):
        return str(payload["candidate_id"])
    if event_type.startswith("Assay"):
        return str(payload["assay_id"])
    if event_type.startswith("Spike"):
        return str(payload["spike_id"])
    raise AssertionError(f"unexpected conditional review event: {event_type}")


def test_transaction_registry_covers_every_executable_route() -> None:
    assert set(TRANSACTION_CONTRACTS) == set(DISCOVERY_ROW_ROUTES)
    assert all(
        TRANSACTION_CONTRACTS[row_id].command_type == route.command_type
        for row_id, route in DISCOVERY_ROW_ROUTES.items()
    )
    assert {
        variant.command_payload_binding for contract in TRANSACTION_CONTRACTS.values() for variant in contract.variants
    } == {
        "durable",
        "stateful",
    }


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


@pytest.mark.parametrize("row_id", ["OR-006", "OR-007", "OR-020", "OR-021", "OR-039", "OR-041"])
def test_satisfied_review_variants_bind_the_exact_command_digest(row_id: str) -> None:
    route = DISCOVERY_ROW_ROUTES[row_id]
    subject_key = "assay_id" if row_id in {"OR-006", "OR-007", "OR-039"} else "spike_id"
    original_payload: dict[str, object] = {
        "row_id": row_id,
        "candidate_id": "candidate",
        subject_key: "subject",
        "review_id": "review",
        "subject_sha256": "1" * 64,
        "verdict": "changes_requested",
        "review_verdict": {
            "review_id": "review",
            "verdict": "changes_requested",
        },
    }
    rewritten_payload = deepcopy(original_payload)
    rewritten_payload["verdict"] = "approve"
    rewritten_payload["review_verdict"] = {"review_id": "review", "verdict": "approve"}
    original_digest = sha256_hex(canonical_bytes(original_payload))
    satisfied_variant = _SATISFIED_REVIEW_WRITE_SETS[row_id]
    assert satisfied_variant in {variant.event_types for variant in TRANSACTION_CONTRACTS[row_id].variants}
    events = []
    for event_type in satisfied_variant:
        payload = (
            deepcopy(rewritten_payload["review_verdict"])
            if event_type == "ReviewVerdictRecorded"
            else deepcopy(rewritten_payload)
        )
        event = _event(event_type, _review_stream(event_type, payload), payload, route.command_type)
        event["command_payload_hash"] = original_digest
        events.append(event)

    with pytest.raises(IntegrityError, match=f"command payload mismatch for {row_id}"):
        validate_transaction_contract(tuple(events))
