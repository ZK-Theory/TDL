from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from tests.research_system.contracts.wp6_2_t2_authority_validation import (
    T2ContractError,
    validate_catalogue_semantics,
    validate_concurrency_observation,
    validate_event_observation,
    validate_pre_issue_rejection,
    validate_protected_snapshot,
    validate_reconciliation,
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
        "reserved_cost_microunits": 1000,
        "consumed_cost_microunits": 750,
        "refund_microunits": 250,
        "refund_disposition": "refunded",
    }


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("actual_total_tokens", 151),
        ("consumed_cost_microunits", 1001),
        ("refund_microunits", 249),
        ("refund_disposition", "fully_consumed"),
        ("actual_input_tokens", True),
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
