from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.research_system.contracts import wp6_2_t2_authority_validation as validation
from tests.research_system.contracts.wp6_2_t2_authority_validation import (
    T2ContractError,
    rebuild_idempotency_index,
    validate_canonical_id,
    validate_catalogue_semantics,
    validate_command_relations,
    validate_concurrency_observation,
    validate_cost_evidence_relations,
    validate_event_observation,
    validate_protected_snapshot,
    validate_provider_receipt_gates,
    validate_reconciliation,
    validate_receipt_v2,
    validate_replay_observation,
)
from tests.research_system.contracts.wp6_2_t2_expectations import (
    CATALOGUE_PATH,
    CROSSWALK_PATH,
    NEGATIVE_CASES,
    PROTECTED_MEMBERSHIP_PATH,
    PROTECTED_PROVIDER_BLOBS,
    PROTECTED_TREE_IDENTITIES,
    SCHEMA_IDENTITIES,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _catalogue() -> dict[str, object]:
    return yaml.safe_load((REPO_ROOT / CATALOGUE_PATH).read_text(encoding="utf-8"))


@pytest.mark.parametrize("test_id", NEGATIVE_CASES)
def test_each_negative_control_is_independently_required(test_id: str) -> None:
    mutated = copy.deepcopy(_catalogue())
    mutated["negative_controls"].pop(test_id)
    with pytest.raises(T2ContractError, match="negative-control set mismatch"):
        validate_catalogue_semantics(mutated, REPO_ROOT)


@pytest.mark.parametrize(
    ("command_type", "events", "message"),
    [
        ("AuthorizeProviderIssue", ["ProviderCommandIssued", "CostGrantReserved"], "event_batch_order_invalid"),
        ("AuthorizeProviderIssue", ["CostGrantReserved"], "event_batch_incomplete"),
        ("RecordProviderReceipt", ["CostGrantReconciled", "ProviderReceiptRecorded"], "event_batch_order_invalid"),
        ("RecordProviderReceipt", ["ProviderReceiptRecorded"], "event_batch_incomplete"),
    ],
)
def test_atomic_batch_order_and_completeness_negative_controls(
    command_type: str, events: list[str], message: str
) -> None:
    with pytest.raises(T2ContractError, match=message):
        validate_event_observation(command_type, events)


@pytest.mark.parametrize("field", ["reducers", "projections"])
def test_missing_reducer_or_projection_rejects(field: str) -> None:
    mutated = copy.deepcopy(_catalogue())
    mutated["rows"][1][field] = []
    with pytest.raises(T2ContractError, match=f"authority row mismatch: provider_issue.authorize/{field}"):
        validate_catalogue_semantics(mutated, REPO_ROOT)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("schema_id", "ars://wp6-2/t2/command/IssueCostGrantAlias", "command identity mismatch"),
        ("schema_version", "1.1.0", "command identity mismatch"),
        ("raw_utf8_lf_sha256", "0" * 64, "command identity mismatch"),
    ],
)
def test_schema_alias_version_and_hash_substitution_reject(field: str, replacement: str, message: str) -> None:
    mutated = copy.deepcopy(_catalogue())
    mutated["rows"][0]["command_schema_identity"][field] = replacement
    with pytest.raises(T2ContractError, match=message):
        validate_catalogue_semantics(mutated, REPO_ROOT)


def test_two_command_over_reservation_has_exactly_one_winner() -> None:
    observation = {
        "command_count": 2,
        "accepted_count": 1,
        "rejected_count": 1,
        "reservation_count": 1,
        "invocation_count": 1,
        "loser_rejection_code": "cost_grant_exhausted",
        "total_reserved_microunits": 800,
        "grant_ceiling_microunits": 1000,
    }
    validate_concurrency_observation(observation)
    for field, wrong_value in (
        ("accepted_count", 2),
        ("reservation_count", 2),
        ("invocation_count", 2),
        ("total_reserved_microunits", 1200),
    ):
        mutated = {**observation, field: wrong_value}
        with pytest.raises(T2ContractError):
            validate_concurrency_observation(mutated)


def _accepted_replay() -> dict[str, object]:
    return {
        "original_payload_hash": "a" * 64,
        "replay_payload_hash": "a" * 64,
        "status": "duplicate",
        "original_receipt_hash": "b" * 64,
        "receipt_hash": "b" * 64,
        "new_grant_count": 0,
        "new_reservation_count": 0,
        "new_issue_count": 0,
        "new_invocation_count": 0,
        "new_provider_receipt_count": 0,
        "new_reconciliation_count": 0,
        "new_refund_count": 0,
    }


@pytest.mark.parametrize(
    "field",
    [
        "new_grant_count",
        "new_reservation_count",
        "new_issue_count",
        "new_invocation_count",
        "new_provider_receipt_count",
        "new_reconciliation_count",
        "new_refund_count",
    ],
)
def test_replay_has_no_second_side_effect(field: str) -> None:
    observation = _accepted_replay()
    validate_replay_observation(observation)
    observation[field] = 1
    with pytest.raises(T2ContractError, match="replay side effect"):
        validate_replay_observation(observation)


def test_same_idempotency_tuple_with_different_payload_conflicts() -> None:
    observation = {
        **_accepted_replay(),
        "replay_payload_hash": "c" * 64,
        "status": "conflict",
        "rejection_code": "idempotency_conflict",
    }
    validate_replay_observation(observation)
    observation["status"] = "duplicate"
    with pytest.raises(T2ContractError, match="different replay payload must conflict"):
        validate_replay_observation(observation)


def _valid_reconciliation() -> dict[str, object]:
    return {
        "actual_input_tokens": 100,
        "actual_output_tokens": 50,
        "actual_total_tokens": 150,
        "reserved_input_tokens": 100,
        "reserved_output_tokens": 50,
        "reserved_total_tokens": 150,
        "reserved_cost_microunits": 1000,
        "consumed_cost_microunits": 2,
        "refund_cost_microunits": 998,
        "refund_disposition": "refunded",
        "input_microunits_per_million_tokens": 10000,
        "output_microunits_per_million_tokens": 20000,
        "rate_mode": "metered",
        "zero_cost_authority": None,
    }


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("actual_total_tokens", 151),
        ("consumed_cost_microunits", 3),
        ("refund_cost_microunits", 997),
        ("refund_disposition", "fully_consumed"),
        ("actual_input_tokens", True),
        ("reserved_input_tokens", 99),
        ("rate_mode", "open"),
    ],
)
def test_reconciliation_actuals_and_refund_relations_reject(field: str, wrong_value: object) -> None:
    payload = _valid_reconciliation()
    validate_reconciliation(payload)
    payload[field] = wrong_value
    with pytest.raises(T2ContractError, match="reconciliation_actuals_invalid"):
        validate_reconciliation(payload)


@pytest.mark.parametrize("protected_path", PROTECTED_TREE_IDENTITIES)
def test_wp6_1_tree_mutation_negative_control(protected_path: str) -> None:
    mutated = dict(PROTECTED_TREE_IDENTITIES)
    mutated[protected_path] = "0" * 40
    with pytest.raises(T2ContractError, match="protected WP6.1 tree"):
        validate_protected_snapshot(mutated, PROTECTED_PROVIDER_BLOBS)


@pytest.mark.parametrize("protected_path", PROTECTED_PROVIDER_BLOBS)
def test_provider_v1_schema_mutation_negative_control(protected_path: str) -> None:
    mutated = dict(PROTECTED_PROVIDER_BLOBS)
    mutated[protected_path] = "0" * 40
    with pytest.raises(T2ContractError, match="protected provider 1.0.0"):
        validate_protected_snapshot(PROTECTED_TREE_IDENTITIES, mutated)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _event(event_type: str, effect_field: str, effect_id: str) -> dict[str, object]:
    idempotency_key = "wp6-2-t2-replay-key"
    return {
        "command_id": "cmd_018f47a2-9b3c-7def-8abc-0123456789ab",
        "actor_id": "actor-a",
        "authority_scope": "wp6.2.t2.provider.issue",
        "command_type": "AuthorizeProviderIssue",
        "idempotency_key": idempotency_key,
        "idempotency_key_hash": hashlib.sha256(idempotency_key.encode()).hexdigest(),
        "payload_hash": "b" * 64,
        "event_type": event_type,
        "payload": {effect_field: effect_id},
    }


def test_rebuild_idempotency_index_from_canonical_event_bytes() -> None:
    events = [
        _event("CostGrantReserved", "reservation_id", "crs_018f47a2-9b3c-7def-8abc-0123456789ab"),
        _event("ProviderCommandIssued", "provider_command_id", "pcmd_018f47a2-9b3c-7def-8abc-0123456789ab"),
    ]
    assert rebuild_idempotency_index([_canonical_bytes(event) for event in events]) == {
        ("actor-a", "wp6.2.t2.provider.issue", "AuthorizeProviderIssue", "wp6-2-t2-replay-key"): (
            events[0]["command_id"],
            "b" * 64,
        )
    }


def test_rebuilt_index_rejects_duplicate_effect() -> None:
    event = _event("CostGrantReserved", "reservation_id", "crs_018f47a2-9b3c-7def-8abc-0123456789ab")
    raw = _canonical_bytes(event)
    with pytest.raises(T2ContractError, match="duplicate replay effect"):
        rebuild_idempotency_index([raw, raw])


def test_rebuilt_index_rejects_conflicting_payload_binding() -> None:
    first = _event("CostGrantReserved", "reservation_id", "crs_018f47a2-9b3c-7def-8abc-0123456789ab")
    second = _event(
        "ProviderCommandIssued",
        "provider_command_id",
        "pcmd_018f47a2-9b3c-7def-8abc-0123456789ab",
    )
    second["payload_hash"] = "c" * 64
    with pytest.raises(T2ContractError, match="idempotency_conflict"):
        rebuild_idempotency_index([_canonical_bytes(first), _canonical_bytes(second)])


def _command_fixture(
    command_type: str,
) -> tuple[dict[str, object], dict[str, dict[str, object]], list[dict[str, object]]]:
    suffix = "018f47a2-9b3c-7def-8abc-0123456789ab"
    digest = "a" * 64
    identities = {
        "cost_grant": {"id": f"cgr_{suffix}", "revision": 2, "content_hash": digest},
        "provider_command": {"id": f"pcmd_{suffix}", "revision": 1, "content_hash": digest},
        "provider_receipt": {"id": f"prcp_{suffix}", "revision": 1, "content_hash": digest},
        "reservation": {"id": f"crs_{suffix}", "revision": 1, "content_hash": digest},
        "resource_grant": {"id": f"rgr_{suffix}", "revision": 1, "content_hash": digest},
        "secret_reference": {"id": f"srf_{suffix}", "revision": 1, "content_hash": digest},
        "task": {"id": f"tsk_{suffix}", "revision": 1, "content_hash": digest},
        "dispatch": {"id": f"dsp_{suffix}", "revision": 1, "content_hash": digest},
        "attempt": {"id": f"att_{suffix}", "revision": 1, "content_hash": digest},
    }
    common = {"command_id": f"cmd_{suffix}"}
    if command_type == "IssueCostGrant":
        command = {
            **common,
            "command_type": command_type,
            "target_stream_id": identities["cost_grant"]["id"],
            "write_set": [
                {"stream_role": "cost_grant", "stream_id": identities["cost_grant"]["id"], "expected_stream_version": 0}
            ],
            "payload": {
                "cost_grant_id": identities["cost_grant"]["id"],
                "resource_grant_id": identities["resource_grant"]["id"],
                "resource_grant_revision": 1,
                "resource_grant_hash": digest,
                "task_id": identities["task"]["id"],
                "dispatch_id": identities["dispatch"]["id"],
                "attempt_id": identities["attempt"]["id"],
            },
        }
        events = [
            {
                "event_type": "CostGrantIssued",
                "stream_id": identities["cost_grant"]["id"],
                "resulting_stream_version": 1,
            }
        ]
    elif command_type == "AuthorizeProviderIssue":
        command = {
            **common,
            "command_type": command_type,
            "target_stream_id": identities["cost_grant"]["id"],
            "write_set": [
                {
                    "stream_role": "cost_grant",
                    "stream_id": identities["cost_grant"]["id"],
                    "expected_stream_version": 2,
                },
                {
                    "stream_role": "provider_command",
                    "stream_id": identities["provider_command"]["id"],
                    "expected_stream_version": 0,
                },
            ],
            "payload": {
                "cost_grant_id": identities["cost_grant"]["id"],
                "cost_grant_revision": 2,
                "cost_grant_hash": digest,
                "provider_command_id": identities["provider_command"]["id"],
                "provider_command_revision": 1,
                "provider_command_hash": digest,
                "secret_reference_id": identities["secret_reference"]["id"],
                "secret_reference_revision": 1,
                "secret_reference_hash": digest,
                "reservation_id": identities["reservation"]["id"],
            },
        }
        events = [
            {
                "event_type": "CostGrantReserved",
                "stream_id": identities["cost_grant"]["id"],
                "resulting_stream_version": 3,
            },
            {
                "event_type": "ProviderCommandIssued",
                "stream_id": identities["provider_command"]["id"],
                "resulting_stream_version": 1,
            },
        ]
    else:
        command = {
            **common,
            "command_type": command_type,
            "target_stream_id": identities["provider_command"]["id"],
            "write_set": [
                {
                    "stream_role": "provider_command",
                    "stream_id": identities["provider_command"]["id"],
                    "expected_stream_version": 1,
                },
                {
                    "stream_role": "cost_grant",
                    "stream_id": identities["cost_grant"]["id"],
                    "expected_stream_version": 2,
                },
            ],
            "payload": {
                "provider_command_id": identities["provider_command"]["id"],
                "provider_command_revision": 1,
                "provider_command_hash": digest,
                "provider_receipt_id": identities["provider_receipt"]["id"],
                "provider_receipt_revision": 1,
                "provider_receipt_hash": digest,
                "cost_grant_id": identities["cost_grant"]["id"],
                "cost_grant_revision": 2,
                "cost_grant_hash": digest,
                "reservation_id": identities["reservation"]["id"],
                "reservation_revision": 1,
                "reservation_hash": digest,
            },
        }
        events = [
            {
                "event_type": "ProviderReceiptRecorded",
                "stream_id": identities["provider_command"]["id"],
                "resulting_stream_version": 2,
            },
            {
                "event_type": "CostGrantReconciled",
                "stream_id": identities["cost_grant"]["id"],
                "resulting_stream_version": 3,
            },
        ]
    required_stems = {
        "IssueCostGrant": {
            "cost_grant",
            "resource_grant",
            "task",
            "dispatch",
            "attempt",
            "provider_command",
            "secret_reference",
        },
        "AuthorizeProviderIssue": {
            "cost_grant",
            "resource_grant",
            "task",
            "dispatch",
            "attempt",
            "provider_command",
            "secret_reference",
            "reservation",
        },
        "RecordProviderReceipt": {
            "cost_grant",
            "resource_grant",
            "task",
            "dispatch",
            "attempt",
            "provider_command",
            "provider_receipt",
            "secret_reference",
            "reservation",
        },
    }[command_type]
    for stem in required_stems:
        identity = identities[stem]
        command["payload"].update(
            {
                f"{stem}_id": identity["id"],
                f"{stem}_revision": identity["revision"],
                f"{stem}_hash": identity["content_hash"],
            }
        )
    return command, identities, events


@pytest.mark.parametrize("command_type", ["IssueCostGrant", "AuthorizeProviderIssue", "RecordProviderReceipt"])
def test_command_relations_positive_fixtures(command_type: str) -> None:
    command, subjects, events = _command_fixture(command_type)
    validate_command_relations(command, subjects, events)


@pytest.mark.parametrize("mutation", ["target", "version", "subject", "event_order"])
def test_command_relations_counterexamples(mutation: str) -> None:
    command, subjects, events = _command_fixture("RecordProviderReceipt")
    if mutation == "target":
        command["target_stream_id"] = "pcmd_018f47a2-9b3c-7def-8abc-ffffffffffff"
    elif mutation == "version":
        command["write_set"][0]["expected_stream_version"] = 2
    elif mutation == "subject":
        command["payload"]["reservation_hash"] = "b" * 64
    else:
        events.reverse()
    with pytest.raises(T2ContractError):
        validate_command_relations(command, subjects, events)


def test_command_relations_require_every_authority_subject_id() -> None:
    command, subjects, events = _command_fixture("IssueCostGrant")
    subjects.pop("task")
    with pytest.raises(T2ContractError, match="authority subject missing:task"):
        validate_command_relations(command, subjects, events)


def test_integer_ceil_div_reconciliation() -> None:
    validate_reconciliation(_valid_reconciliation())


def test_zero_cost_mode_requires_explicit_authority_and_zero_rates() -> None:
    payload = {
        **_valid_reconciliation(),
        "consumed_cost_microunits": 0,
        "refund_cost_microunits": 1000,
        "input_microunits_per_million_tokens": 0,
        "output_microunits_per_million_tokens": 0,
        "rate_mode": "zero_cost_authorized",
        "zero_cost_authority": {
            "subject_id": "zca_018f47a2-9b3c-7def-8abc-0123456789ab",
            "subject_revision": 1,
            "subject_hash": "a" * 64,
        },
    }
    validate_reconciliation(payload)
    payload["zero_cost_authority"] = None
    with pytest.raises(T2ContractError, match="reconciliation_actuals_invalid"):
        validate_reconciliation(payload)


def test_cost_evidence_identity_relations() -> None:
    binding = {
        "currency": "USD",
        "rate_evidence_id": "rate-1",
        "rate_evidence_revision": 1,
        "rate_evidence_hash": "a" * 64,
    }
    validate_cost_evidence_relations(binding, dict(binding), dict(binding), dict(binding))
    with pytest.raises(T2ContractError, match="cost evidence identity mismatch"):
        validate_cost_evidence_relations(binding, {**binding, "currency": "GBP"})


def test_receipt_v2_outcome_relations_reject() -> None:
    receipt = {
        "outcome": "rejected",
        "events": [{"event_id": "evt"}],
        "event_batch_id": "txb",
        "stable_reason": "blocked",
        "unmet_preconditions": ["authority"],
    }
    with pytest.raises(T2ContractError, match="rejected_receipt_has_events"):
        validate_receipt_v2(receipt)


def test_duplicate_receipt_binds_original_outcome_without_new_effects() -> None:
    original = _accepted_receipt_v2()
    duplicate = {
        **original,
        "outcome": "duplicate",
        "original_accepted_receipt_hash": hashlib.sha256(_canonical_bytes(original)).hexdigest(),
        "new_event_count": 0,
        "new_invocation_count": 0,
    }
    validate_receipt_v2(duplicate, original)
    duplicate["events"] = []
    with pytest.raises(T2ContractError, match="duplicate_receipt_mismatch:events"):
        validate_receipt_v2(duplicate, original)


def test_incomplete_provider_receipt_is_diagnostic_only() -> None:
    receipt = {
        "delivery_binding": {"disposition": "unable_to_prove"},
        "completeness": {
            "complete": False,
            "reconciliation_gate_satisfied": False,
            "diagnostic_only": True,
        },
    }
    validate_provider_receipt_gates(receipt)
    receipt["completeness"]["reconciliation_gate_satisfied"] = True
    with pytest.raises(T2ContractError, match="incomplete provider receipt satisfied gate"):
        validate_provider_receipt_gates(receipt)


@pytest.mark.parametrize(
    "value",
    [
        "srf_abc",
        "srf_018f47a2-9b3c-6def-8abc-0123456789ab",
        "srf_018f47a2-9b3c-7def-7abc-0123456789ab",
        "SRF_018f47a2-9b3c-7def-8abc-0123456789ab",
        "sref_018f47a2-9b3c-7def-8abc-0123456789ab",
    ],
)
def test_uuidv7_prefix_and_case_counterexamples(value: str) -> None:
    with pytest.raises(T2ContractError, match="canonical_id_invalid"):
        validate_canonical_id(value, "srf")


def _accepted_receipt_v2() -> dict[str, object]:
    suffix = "018f47a2-9b3c-7def-8abc-0123456789ab"
    return {
        "schema_id": "ars://core/receipt/v2",
        "schema_version": "2.0.0",
        "receipt_id": f"rcp_{suffix}",
        "outcome": "accepted",
        "command_type": "AuthorizeProviderIssue",
        "command_id": f"cmd_{suffix}",
        "idempotency_key_hash": "a" * 64,
        "payload_hash": "b" * 64,
        "event_batch_id": f"txb_{suffix}",
        "events": [
            {
                "event_id": f"evt_{suffix}",
                "event_type": "CostGrantReserved",
                "transaction_position": 0,
                "stream_id": f"cgr_{suffix}",
                "prior_stream_version": 2,
                "resulting_stream_version": 3,
            },
            {
                "event_id": "evt_018f47a2-9b3c-7def-8abc-0123456789ac",
                "event_type": "ProviderCommandIssued",
                "transaction_position": 1,
                "stream_id": f"pcmd_{suffix}",
                "prior_stream_version": 0,
                "resulting_stream_version": 1,
            },
        ],
        "stable_reason": None,
        "unmet_preconditions": [],
        "original_accepted_receipt_hash": None,
        "outcome_binding_hash": "c" * 64,
        "new_event_count": 2,
        "new_invocation_count": 0,
    }


@pytest.mark.parametrize(
    "mutation",
    ["count", "position", "order", "event_id", "stream_version"],
)
def test_r3_red_c1_receipt_v2_rejects_internally_inconsistent_proof(mutation: str) -> None:
    receipt = _accepted_receipt_v2()
    if mutation == "count":
        receipt["new_event_count"] = 1
    elif mutation == "position":
        receipt["events"][1]["transaction_position"] = 0
    elif mutation == "order":
        receipt["events"].reverse()
    elif mutation == "event_id":
        receipt["events"][1]["event_id"] = receipt["events"][0]["event_id"]
    else:
        receipt["events"][0]["resulting_stream_version"] = 4
    with pytest.raises(T2ContractError):
        validate_receipt_v2(receipt)


def test_r3_red_c2_logical_tuple_collision_is_command_id_independent() -> None:
    first = _event("CostGrantReserved", "reservation_id", "crs_018f47a2-9b3c-7def-8abc-0123456789ab")
    second = _event(
        "ProviderCommandIssued",
        "provider_command_id",
        "pcmd_018f47a2-9b3c-7def-8abc-0123456789ab",
    )
    for event in (first, second):
        idempotency_key = "provider-issue-01"
        event.update(
            {
                "actor_id": "act_018f47a2-9b3c-7def-8abc-0123456789ab",
                "authority_scope": "wp6.2.t2.provider.issue",
                "command_type": "AuthorizeProviderIssue",
                "idempotency_key": idempotency_key,
                "idempotency_key_hash": hashlib.sha256(idempotency_key.encode()).hexdigest(),
            }
        )
    second["command_id"] = "cmd_018f47a2-9b3c-7def-8abc-0123456789ac"
    with pytest.raises(T2ContractError, match="idempotency_conflict"):
        rebuild_idempotency_index([_canonical_bytes(first), _canonical_bytes(second)])


def test_r3_red_c4_every_applicable_authority_subject_is_a_complete_triple() -> None:
    required_stems = {
        "IssueCostGrant": {
            "cost_grant",
            "resource_grant",
            "task",
            "dispatch",
            "attempt",
            "provider_command",
            "secret_reference",
        },
        "AuthorizeProviderIssue": {
            "cost_grant",
            "resource_grant",
            "task",
            "dispatch",
            "attempt",
            "provider_command",
            "secret_reference",
            "reservation",
        },
        "RecordProviderReceipt": {
            "cost_grant",
            "resource_grant",
            "task",
            "dispatch",
            "attempt",
            "provider_command",
            "provider_receipt",
            "secret_reference",
            "reservation",
        },
    }
    for command_type, stems in required_stems.items():
        schema = json.loads((REPO_ROOT / SCHEMA_IDENTITIES[command_type]["path"]).read_text(encoding="utf-8"))
        payload_required = set(schema["properties"]["payload"]["required"])
        for stem in stems:
            assert {f"{stem}_id", f"{stem}_revision", f"{stem}_hash"} <= payload_required


def test_r3_red_m1_one_composed_gate_includes_schema_arithmetic_and_evidence() -> None:
    assert callable(getattr(validation, "validate_t2_authority_cost_gate", None))


def _authority_cost_fixtures() -> tuple[dict[str, object], ...]:
    suffix = "018f47a2-9b3c-7def-8abc-0123456789ab"
    digest = "a" * 64
    timestamp = "2026-07-22T12:00:00Z"

    def triple(prefix: str) -> dict[str, object]:
        return {"id": f"{prefix}_{suffix}", "revision": 1, "content_hash": digest}

    def content_ref(prefix: str) -> dict[str, object]:
        return {
            "subject_id": f"{prefix}_{suffix}",
            "subject_revision": 1,
            "subject_hash": digest,
        }

    rate_binding = {
        "currency": "USD",
        "rate_evidence_id": f"rate_{suffix}",
        "rate_evidence_revision": 1,
        "rate_evidence_hash": digest,
    }
    cost_grant = {
        "schema_id": "ars://wp6-2/t2/cost-grant",
        "schema_version": "1.0.0",
        "cost_grant_id": f"cgr_{suffix}",
        "revision": 1,
        "content_hash": digest,
        "resource_grant_id": f"rgr_{suffix}",
        "resource_grant_revision": 1,
        "resource_grant_hash": digest,
        "authority_grant_id": f"agr_{suffix}",
        "scope": {
            "task_id": f"tsk_{suffix}",
            "dispatch_id": f"dsp_{suffix}",
            "attempt_id": f"att_{suffix}",
            "route_id": f"rte_{suffix}",
            "profile_id": f"prf_{suffix}",
            "adapter_revision": "adapter-1",
            "provider_command_id": f"pcmd_{suffix}",
            "provider_command_revision": 1,
            "provider_command_hash": digest,
        },
        "secret_reference_id": f"srf_{suffix}",
        "secret_reference_revision": 1,
        "secret_reference_hash": digest,
        "provider_command_schema_id": "ars://adapters/provider-command/v2",
        "provider_command_schema_version": "2.0.0",
        "token_ceilings": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "cost_ceiling_microunits": 1000,
        "rate_evidence": {
            **rate_binding,
            "effective_at": timestamp,
            "expires_at": "2026-07-23T12:00:00Z",
            "mode": "metered",
            "input_microunits_per_million_tokens": 10000,
            "output_microunits_per_million_tokens": 20000,
            "zero_cost_authority": None,
        },
        "initial_accounting": {
            "reserved_microunits": 0,
            "consumed_microunits": 0,
            "refunded_microunits": 0,
        },
        "expires_at": "2026-07-23T12:00:00Z",
        "idempotency_identity": {
            "actor_id": f"act_{suffix}",
            "authority_scope": "wp6.2.t2.cost-grant.issue",
            "command_type": "IssueCostGrant",
            "idempotency_key": "issue-cost-grant-01",
        },
        "revocation_binding": {
            "authority_grant_id": f"agr_{suffix}",
            "resource_grant_id": f"rgr_{suffix}",
            "new_issue_rule": "require_both_current_projections_active",
            "reconciliation_rule": "reconcile_every_previously_accepted_reservation",
        },
    }
    reservation = {
        "cost_grant_id": f"cgr_{suffix}",
        "reservation_id": f"crs_{suffix}",
        "provider_command_id": f"pcmd_{suffix}",
        "reserved_tokens": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "reserved_cost_microunits": 1000,
        "remaining_cost_microunits": 0,
        **rate_binding,
        "input_microunits_per_million_tokens": 10000,
        "output_microunits_per_million_tokens": 20000,
        "rate_mode": "metered",
        "zero_cost_authority": None,
    }
    provider_receipt = {
        "schema_id": "ars://adapters/provider-receipt/v2",
        "schema_version": "2.0.0",
        "provider_receipt_id": f"prcp_{suffix}",
        "revision": 1,
        "revision_hash": digest,
        "command_binding": {
            "provider_command": triple("pcmd"),
            "w2_command": triple("cmd"),
            "idempotency_key_hash": digest,
            "payload_hash": digest,
        },
        "provider_binding": {
            "provider": "claude",
            "provider_identity": triple("prv"),
            "model": triple("mdl"),
            "profile": triple("prf"),
            "adapter": triple("adp"),
            "policy": triple("pol"),
        },
        "authority_binding": {
            "task": triple("tsk"),
            "dispatch": triple("dsp"),
            "attempt": triple("att"),
            "resource_grant": triple("rgr"),
            "cost_grant": triple("cgr"),
            "reservation": triple("crs"),
            "secret_reference": triple("srf"),
            "provider_receipt": triple("prcp"),
        },
        "delivery_binding": {
            "disposition": "proven",
            "rendered_payload_hash": digest,
            "delivered_context_hash": digest,
        },
        "timestamps": {"issued_at": timestamp, "terminal_at": timestamp},
        "token_accounting": {
            "actual_input_tokens": 100,
            "actual_output_tokens": 50,
            "actual_total_tokens": 150,
            "accounting_method": "provider_receipt_exact",
            "reserved_cost_microunits": 1000,
            "consumed_cost_microunits": 2,
            "refund_cost_microunits": 998,
            **rate_binding,
        },
        "terminal_outcome": {"status": "terminal", "normalized_error": None},
        "outputs": {"references": [], "aggregate_hash": digest},
        "lifecycle_evidence": {
            "retry_count": 0,
            "duplicate_of_receipt": None,
            "reconciliation": content_ref("rec"),
        },
        "evidence_disposition": {
            "redaction": "secret_and_restricted_material_removed",
            "omission_declarations": [],
        },
        "completeness": {
            "complete": True,
            "reconciliation_gate_satisfied": True,
            "diagnostic_only": False,
        },
    }
    reconciliation = {
        **_valid_reconciliation(),
        "cost_grant_id": f"cgr_{suffix}",
        "reservation_id": f"crs_{suffix}",
        "provider_command_id": f"pcmd_{suffix}",
        "provider_receipt_id": f"prcp_{suffix}",
        "remaining_cost_microunits": 0,
        **rate_binding,
    }
    return cost_grant, reservation, provider_receipt, reconciliation


def test_t2_authority_cost_gate_composes_schema_arithmetic_and_evidence() -> None:
    cost_grant, reservation, provider_receipt, reconciliation = _authority_cost_fixtures()
    validation.validate_t2_authority_cost_gate(
        REPO_ROOT,
        cost_grant=cost_grant,
        reservation=reservation,
        provider_receipt=provider_receipt,
        reconciliation=reconciliation,
    )


def test_zero_cost_authorization_accepts_zero_reservation_end_to_end() -> None:
    cost_grant, reservation, provider_receipt, reconciliation = _authority_cost_fixtures()
    suffix = "018f47a2-9b3c-7def-8abc-0123456789ab"
    digest = "a" * 64
    zero_cost_authority = {
        "subject_id": f"zca_{suffix}",
        "subject_revision": 1,
        "subject_hash": digest,
    }
    rate_fields = {
        "input_microunits_per_million_tokens": 0,
        "output_microunits_per_million_tokens": 0,
        "rate_mode": "zero_cost_authorized",
        "zero_cost_authority": zero_cost_authority,
    }

    cost_grant["rate_evidence"].update(
        {
            "mode": "zero_cost_authorized",
            **rate_fields,
        }
    )
    cost_grant["rate_evidence"].pop("rate_mode")
    reservation.update(
        {
            "reserved_cost_microunits": 0,
            **rate_fields,
        }
    )
    provider_receipt["token_accounting"].update(
        {
            "reserved_cost_microunits": 0,
            "consumed_cost_microunits": 0,
            "refund_cost_microunits": 0,
        }
    )
    reconciliation.update(
        {
            "reserved_cost_microunits": 0,
            "consumed_cost_microunits": 0,
            "refund_cost_microunits": 0,
            "refund_disposition": "fully_consumed",
            **rate_fields,
        }
    )
    command_payload = {
        "cost_grant_id": f"cgr_{suffix}",
        "cost_grant_revision": 1,
        "cost_grant_hash": digest,
        "resource_grant_id": f"rgr_{suffix}",
        "resource_grant_revision": 1,
        "resource_grant_hash": digest,
        "task_id": f"tsk_{suffix}",
        "task_revision": 1,
        "task_hash": digest,
        "dispatch_id": f"dsp_{suffix}",
        "dispatch_revision": 1,
        "dispatch_hash": digest,
        "attempt_id": f"att_{suffix}",
        "attempt_revision": 1,
        "attempt_hash": digest,
        "reservation_id": f"crs_{suffix}",
        "reservation_revision": 1,
        "reservation_hash": digest,
        "provider_command_id": f"pcmd_{suffix}",
        "provider_command_revision": 1,
        "provider_command_hash": digest,
        "secret_reference_id": f"srf_{suffix}",
        "secret_reference_revision": 1,
        "secret_reference_hash": digest,
        "requested_tokens": reservation["reserved_tokens"],
        "reserved_cost_microunits": 0,
        "expected_available_microunits": 1000,
        "currency": reservation["currency"],
        "rate_evidence_id": reservation["rate_evidence_id"],
        "rate_evidence_revision": reservation["rate_evidence_revision"],
        "rate_evidence_hash": reservation["rate_evidence_hash"],
        **rate_fields,
        "rendered_payload_hash": digest,
    }

    command_schema = json.loads(
        (REPO_ROOT / SCHEMA_IDENTITIES["AuthorizeProviderIssue"]["path"]).read_text(encoding="utf-8")
    )
    command_validator = Draft202012Validator(command_schema["properties"]["payload"])
    assert not list(command_validator.iter_errors(command_payload))
    validation.validate_t2_authority_cost_gate(
        REPO_ROOT,
        cost_grant=cost_grant,
        reservation=reservation,
        provider_receipt=provider_receipt,
        reconciliation=reconciliation,
    )

    command_payload["reserved_cost_microunits"] = -1
    assert any(error.validator == "minimum" for error in command_validator.iter_errors(command_payload))
    reservation_schema = json.loads(
        (REPO_ROOT / SCHEMA_IDENTITIES["CostGrantReserved"]["path"]).read_text(encoding="utf-8")
    )
    reservation_validator = Draft202012Validator(reservation_schema["properties"]["payload"])
    reservation["reserved_cost_microunits"] = -1
    assert any(error.validator == "minimum" for error in reservation_validator.iter_errors(reservation))


@pytest.mark.parametrize(
    ("record_index", "field", "wrong_value"),
    [
        (0, "currency", "GBP"),
        (1, "rate_evidence_id", "rate_018f47a2-9b3c-7def-8abc-0123456789ac"),
        (2, "rate_evidence_revision", 2),
        (3, "rate_evidence_hash", "b" * 64),
    ],
)
def test_t2_authority_cost_gate_rejects_each_cross_object_evidence_difference(
    record_index: int,
    field: str,
    wrong_value: object,
) -> None:
    cost_grant, reservation, provider_receipt, reconciliation = _authority_cost_fixtures()
    evidence_records = [
        cost_grant["rate_evidence"],
        reservation,
        provider_receipt["token_accounting"],
        reconciliation,
    ]
    evidence_records[record_index][field] = wrong_value
    with pytest.raises(T2ContractError, match="cost evidence identity mismatch"):
        validation.validate_t2_authority_cost_gate(
            REPO_ROOT,
            cost_grant=cost_grant,
            reservation=reservation,
            provider_receipt=provider_receipt,
            reconciliation=reconciliation,
        )


def test_r3_red_m3_receipt_stream_id_uses_canonical_permitted_prefix() -> None:
    receipt = _accepted_receipt_v2()
    receipt["events"][0]["stream_id"] = "CGR_018f47a2-9b3c-7def-8abc-0123456789ab"
    with pytest.raises(T2ContractError, match="canonical_id_invalid"):
        validate_receipt_v2(receipt)


def test_r3_red_i1_protected_membership_is_explicit_and_omission_sensitive() -> None:
    contract_path = REPO_ROOT / PROTECTED_MEMBERSHIP_PATH
    schema_path = REPO_ROOT / ".research-system/schemas/contracts/wp6-2-t2-protected-membership.schema.json"
    assert contract_path.is_file() and schema_path.is_file()
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(contract)
    mutated["members"].pop()
    with pytest.raises(T2ContractError):
        validation.validate_protected_membership_contract(mutated, REPO_ROOT)


def test_protected_membership_recomputes_exact_live_set() -> None:
    contract = yaml.safe_load((REPO_ROOT / PROTECTED_MEMBERSHIP_PATH).read_text(encoding="utf-8"))
    validation.validate_protected_membership_contract(contract, REPO_ROOT)


def test_protected_membership_expected_side_has_no_materializer_dependency() -> None:
    materializer_source = (REPO_ROOT / "tests/research_system/contracts/wp6_2_t2_schema_materializer.py").read_text(
        encoding="utf-8"
    )
    validator_source = (REPO_ROOT / "tests/research_system/contracts/wp6_2_t2_authority_validation.py").read_text(
        encoding="utf-8"
    )
    materializer_imports = {
        node.module for node in ast.walk(ast.parse(materializer_source)) if isinstance(node, ast.ImportFrom)
    }
    validator_imports = {
        node.module for node in ast.walk(ast.parse(validator_source)) if isinstance(node, ast.ImportFrom)
    }
    assert "tests.research_system.contracts.wp6_2_t2_authority_validation" not in materializer_imports
    assert "_derive_protected_paths" not in materializer_source
    assert "tests.research_system.contracts.wp6_2_t2_schema_materializer" not in validator_imports


def test_r3_red_c3_obsolete_evidence_system_is_absent_from_t2_surface() -> None:
    scoped_paths = {
        CROSSWALK_PATH,
        CATALOGUE_PATH,
        "tests/research_system/contracts/wp6_2_t2_expectations.py",
        "tests/research_system/contracts/wp6_2_t2_schema_materializer.py",
        "tests/research_system/contracts/wp6_2_t2_authority_validation.py",
        "tests/research_system/contracts/test_wp6_2_t2_authority_contract.py",
        "tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py",
        "docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md",
    }
    forbidden = (
        "PreIssue" + "EvidenceManifest",
        "pre_issue_evidence_" + "manifest",
        "PRE_ISSUE_" + "SENTINEL_SEAMS",
    )
    offenders = {
        path: token
        for path in scoped_paths
        for token in forbidden
        if token in (REPO_ROOT / path).read_text(encoding="utf-8")
    }
    assert not offenders
    assert "pre_issue_evidence_" + "manifest" not in SCHEMA_IDENTITIES
    removed_schema_path = ".research-system/schemas/wp6-2-t2/" + "pre-issue-evidence-" + "manifest.schema.json"
    assert not (REPO_ROOT / removed_schema_path).exists()


def test_r3_red_m2_provider_successors_are_labeled_exact_t2_subset() -> None:
    command = json.loads((REPO_ROOT / SCHEMA_IDENTITIES["provider_command_v2"]["path"]).read_text(encoding="utf-8"))
    receipt = json.loads((REPO_ROOT / SCHEMA_IDENTITIES["provider_receipt_v2"]["path"]).read_text(encoding="utf-8"))
    assert command["x-t2-validation-scope"] == "t2_authority_cost_subset"
    assert receipt["x-t2-validation-scope"] == "t2_authority_cost_subset"
    assert not (
        {"context_binding", "assurance_binding", "resource_binding", "receipt_expectation"} & set(command["properties"])
    )
    assert not ({"provider_native_ids", "actions", "resource_observations"} & set(receipt["properties"]))
