import json
from pathlib import Path

import pytest
import research_system

from research_system.authority import (
    SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES,
    _SCOPED_COMMAND_SUBJECT_KINDS,
)
from research_system.errors import SchemaError
from research_system.discovery.routes import (
    DISCOVERY_DEFERRED_ROWS as _DISCOVERY_DEFERRED_ROWS,
    DISCOVERY_EXCLUDED_ROWS as _DISCOVERY_EXCLUDED_ROWS,
    DISCOVERY_ROW_ROUTES as _DISCOVERY_ROW_ROUTES,
    validate_discovery_route_registry as _validate_discovery_route_registry,
)
from research_system.discovery.replay.transactions import TRANSACTION_CONTRACTS
from research_system.discovery.runtime import _DISCOVERY_COMMAND_TYPES
from research_system.discovery.commands import discovery_resolve_transaction_ids
from research_system.schema_registry import runtime_schema_registry


REPOSITORY_ROOT = Path(research_system.__file__).resolve().parent.parent


def test_candidate_supersession_uses_candidate_compatible_scoped_authority():
    assert "SupersedeDiscoveryRecord" in SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES
    assert _SCOPED_COMMAND_SUBJECT_KINDS["SupersedeDiscoveryRecord"] == "scope_definition"
    assert (
        _SCOPED_COMMAND_SUBJECT_KINDS["SupersedeDiscoveryRecord"] == _SCOPED_COMMAND_SUBJECT_KINDS["RegisterCandidate"]
    )


def test_spec_brief_non_owner_commands_require_proven_scoped_actor_classes():
    assert {
        "RegisterArtefact",
        "RecordScientificReview",
        "RequestContextPacket",
        "BeginContextCompilation",
        "CompleteContextCompilation",
        "PrepareOwnerOperatedContextHandoff",
        "ValidateOwnerOperatedContextHandoff",
        "IssueOwnerOperatedContextHandoff",
        "RecordOwnerOperatedContextDelivery",
    }.issubset(SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES)


def test_spec_execution_non_owner_commands_require_proven_scoped_actor_classes():
    assert {
        "CreateTask",
        "RequestReadiness",
        "ApproveReadiness",
        "IssueDispatch",
        "RecordDispatchDelivery",
        "AcknowledgeDispatch",
        "ClaimDispatch",
        "RequestResourceGrant",
        "ClaimExecutionLease",
        "CreateAttempt",
        "ClaimAttempt",
        "StartAttempt",
    }.issubset(SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES)


def test_discovery_initiating_commands_use_candidate_scoped_authority():
    for command_type in (
        "ProposeRevisitDecision",
        "RequestDiscoveryOutcomeReview",
        "ProposePromotionDecision",
        "ProposeSpikeExecutionDecision",
    ):
        assert _SCOPED_COMMAND_SUBJECT_KINDS[command_type] == "scope_definition"


def test_generic_resolve_decision_cannot_spoof_a_discovery_row_binding():
    schemas = runtime_schema_registry(REPOSITORY_ROOT / ".research-system/schemas")
    binding = schemas.command_binding("ResolveDecision")
    assert binding is not None
    assert binding.schema_id == "ars://core/command/ResolveDecision"
    assert binding.schema_version == "1.0.0"
    payload = {
        "decision_id": "dec_019fed25-b33e-7740-b280-000000000001",
        "selected_option": "approve",
        "effective_scope": "generic decision",
        "decision_revision": 1,
        "deciding_actor_id": "act_019fed25-b33e-7740-b280-000000000001",
        "decision_authority_grant_id": "agr_019fed25-b33e-7740-b280-000000000001",
        "governing_evidence_refs": ["evidence:generic"],
        "considered_review_ids": [],
        "effective_at": "2026-08-12T00:00:00Z",
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    schema = json.loads(
        (REPOSITORY_ROOT / ".research-system/schemas/core/commands/resolve_decision.schema.json").read_bytes()
    )
    generic_payload_contracts = [
        contract
        for contract in schema["$defs"]["payload"]["oneOf"]
        if set(contract.get("required", ())) == set(payload)
    ]
    assert len(generic_payload_contracts) == 1
    generic_payload_contract = generic_payload_contracts[0]
    assert generic_payload_contract["additionalProperties"] is False
    assert {"row_id", "owner_row_id"}.isdisjoint(generic_payload_contract["properties"])

    command = {
        "command_id": "cmd_019fed25-b33e-7740-b280-000000000001",
        "command_type": "ResolveDecision",
        "schema_id": binding.schema_id,
        "schema_version": binding.schema_version,
        "submitted_at": "2026-08-12T00:00:00Z",
        "actor_id": "act_019fed25-b33e-7740-b280-000000000001",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": "agr_019fed25-b33e-7740-b280-000000000001",
        "target_stream_id": payload["decision_id"],
        "expected_stream_version": 0,
        "idempotency_key": "generic-resolve-decision",
        "correlation_id": "generic-resolve-decision",
        "causation_id": None,
        "reason": "verify closed generic ResolveDecision payload",
        "evidence_refs": [],
        "payload": payload,
        "project_id": "prj_019fed25-b33e-7740-b280-000000000001",
    }
    schemas.validate(binding.schema_id, command, schema_version=binding.schema_version)
    for extra_key in ("row_id", "owner_row_id"):
        spoofed = {**command, "payload": {**payload, extra_key: "OR-013"}}
        with pytest.raises(SchemaError) as exc_info:
            schemas.validate(binding.schema_id, spoofed, schema_version=binding.schema_version)
        assert extra_key in str(exc_info.value)

    assert (
        discovery_resolve_transaction_ids(
            ({"command_type": "ResolveDecision", "transaction_id": "txn:generic", "payload": payload},)
        )
        == frozenset()
    )


def test_executable_route_registry_exactly_partitions_the_accepted_w11_catalogue():
    catalogue = json.loads(
        (REPOSITORY_ROOT / ".research-system/evals/expected/w11-portfolio-discovery-v1.json").read_bytes()
    )
    schemas = runtime_schema_registry(REPOSITORY_ROOT / ".research-system/schemas")

    _validate_discovery_route_registry(catalogue)
    assert len(_DISCOVERY_ROW_ROUTES) == 59
    assert set(TRANSACTION_CONTRACTS) == set(_DISCOVERY_ROW_ROUTES)
    assert len(_DISCOVERY_EXCLUDED_ROWS) == 21
    assert _DISCOVERY_DEFERRED_ROWS == {"OR-030": "WP6.7 annotation-epoch contract and initial authority activation"}
    assert set(_DISCOVERY_ROW_ROUTES).isdisjoint(_DISCOVERY_EXCLUDED_ROWS)
    assert {route.command_type for route in _DISCOVERY_ROW_ROUTES.values()} == _DISCOVERY_COMMAND_TYPES
    assert {route.family for route in _DISCOVERY_ROW_ROUTES.values()} == {
        "assay",
        "assay_authority",
        "authority",
        "candidate",
        "dossier",
        "genesis",
        "scout",
        "spike",
        "supersede",
    }
    for route in _DISCOVERY_ROW_ROUTES.values():
        assert schemas.command_binding(route.command_type) is not None
        assert _SCOPED_COMMAND_SUBJECT_KINDS[route.command_type] in {"decision", "review", "scope_definition"}
