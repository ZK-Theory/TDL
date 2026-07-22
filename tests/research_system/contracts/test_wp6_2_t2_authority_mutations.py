from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tests.research_system.contracts.wp6_2_t2_authority_validation import (
    T2ContractError,
    rebuild_idempotency_index,
    validate_canonical_id,
    validate_catalogue_semantics,
    validate_command_relations,
    validate_concurrency_observation,
    validate_cost_evidence_relations,
    validate_event_observation,
    validate_pre_issue_evidence,
    validate_pre_issue_rejection,
    validate_protected_snapshot,
    validate_provider_receipt_gates,
    validate_reconciliation,
    validate_receipt_v2,
    validate_replay_observation,
)
from tests.research_system.contracts.wp6_2_t2_expectations import (
    CATALOGUE_PATH,
    NEGATIVE_CASES,
    PRE_ISSUE_SENTINEL_SEAMS,
    PROTECTED_PROVIDER_BLOBS,
    PROTECTED_TREE_IDENTITIES,
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


@pytest.mark.parametrize("seam", PRE_ISSUE_SENTINEL_SEAMS)
@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("reservation_count", 1),
        ("invocation_count", 1),
        ("canonical_publication_count", 1),
    ],
)
def test_secret_sentinel_negative_control_detects_every_side_effect(seam: str, field: str, wrong_value: int) -> None:
    observation = {
        "seam": seam,
        "rejection_code": "secret_material_detected",
        "reservation_count": 0,
        "invocation_count": 0,
        "canonical_publication_count": 0,
    }
    validate_pre_issue_rejection(observation)
    observation[field] = wrong_value
    with pytest.raises(T2ContractError):
        validate_pre_issue_rejection(observation)


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
    return {
        "command_id": "cmd_018f47a2-9b3c-7def-8abc-0123456789ab",
        "idempotency_key_hash": "a" * 64,
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
        events[0]["command_id"]: ("a" * 64, "b" * 64)
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


def _pre_issue_fixture() -> tuple[dict[str, object], dict[str, object], str]:
    sentinel = "SAFE_SYNTHETIC_SENTINEL_T2"
    payloads = {seam: {"nested": {"seam": seam, "value": "clean"}} for seam in PRE_ISSUE_SENTINEL_SEAMS}
    hashes = [hashlib.sha256(_canonical_bytes(payloads[seam])).hexdigest() for seam in PRE_ISSUE_SENTINEL_SEAMS]
    digest = "a" * 64
    manifest = {
        "safe_synthetic_sentinel_hash": hashlib.sha256(sentinel.encode()).hexdigest(),
        "seams": [
            {
                "seam_id": seam,
                "producer": {"subject_id": f"producer-{index}", "subject_revision": 1, "subject_hash": digest},
                "source_evidence": [{"subject_id": f"evidence-{index}", "subject_revision": 1, "subject_hash": digest}],
                "serialized_payload_hash": payload_hash,
                "outcome": "no_prohibited_material_or_sentinel",
            }
            for index, (seam, payload_hash) in enumerate(zip(PRE_ISSUE_SENTINEL_SEAMS, hashes, strict=True))
        ],
        "aggregate_content_hash": hashlib.sha256("\n".join(hashes).encode("ascii")).hexdigest(),
    }
    return manifest, payloads, sentinel


def test_recursive_pre_issue_scan_accepts_clean_eight_seams() -> None:
    manifest, payloads, sentinel = _pre_issue_fixture()
    validate_pre_issue_evidence(manifest, payloads, safe_sentinel=sentinel, prohibited_material=["REAL_SECRET"])


@pytest.mark.parametrize("seam", PRE_ISSUE_SENTINEL_SEAMS)
@pytest.mark.parametrize("material", ["SAFE_SYNTHETIC_SENTINEL_T2", "REAL_SECRET"])
def test_recursive_pre_issue_scan_rejects_actual_serialized_seam(seam: str, material: str) -> None:
    manifest, payloads, sentinel = _pre_issue_fixture()
    payloads[seam] = {"recursive": {"list": ["clean", {"material": material}]}}
    with pytest.raises(T2ContractError, match="secret_material_detected"):
        validate_pre_issue_evidence(manifest, payloads, safe_sentinel=sentinel, prohibited_material=["REAL_SECRET"])


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
    original = {
        "outcome": "accepted",
        "command_id": "cmd_018f47a2-9b3c-7def-8abc-0123456789ab",
        "idempotency_key_hash": "a" * 64,
        "payload_hash": "b" * 64,
        "event_batch_id": "txb_018f47a2-9b3c-7def-8abc-0123456789ab",
        "events": [{"event_id": "evt_018f47a2-9b3c-7def-8abc-0123456789ab"}],
        "outcome_binding_hash": "c" * 64,
        "stable_reason": None,
        "unmet_preconditions": [],
    }
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
        "delivery_proof": {"disposition": "unable_to_prove"},
        "completeness": {
            "complete": False,
            "dispatch_gate_satisfied": False,
            "delivery_gate_satisfied": False,
            "reconciliation_gate_satisfied": False,
            "review_gate_satisfied": False,
            "diagnostic_only": True,
        },
    }
    validate_provider_receipt_gates(receipt)
    receipt["completeness"]["review_gate_satisfied"] = True
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
