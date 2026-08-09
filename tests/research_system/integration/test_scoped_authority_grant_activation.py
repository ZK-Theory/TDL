from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import threading
from types import SimpleNamespace

import pytest

from research_system.authority import (
    GrantedCommandIdentity,
    GrantedPolicyActionIdentity,
    LedgerAuthorityGrantResolver,
    OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
    SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.cli import _replay_verify
from research_system.command.service import CommandService
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.projection.replay import apply_event, replay
from research_system.schema_registry import (
    SchemaBinding,
    SchemaRegistry,
    runtime_schema_registry,
)
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import REPO_ROOT
from tests.research_system.integration.test_authority_grant_source import (
    ACTOR_ID,
    CMD_RETRY,
    CMD_REVOKE,
    PROJECT_ID,
    PUBLICATION_ID,
    ROOT_ID,
    _initialized,
    _revoke_command,
)


GRANTEE_ID = "act_01978abc-6200-7000-8000-000000006200"
GRANT_ID = "agr_01978abc-6201-7000-8000-000000006201"
REQUIREMENT_ID = "asr_01978abc-6202-7000-8000-000000006202"
ACTIVATE_DECISION_ID = "arec_01978abc-6203-7000-8000-000000006203"
REVOKE_DECISION_ID = "arec_01978abc-6204-7000-8000-000000006204"
ACTIVATE_COMMAND_ID = "cmd_01978abc-6205-7000-8000-000000006205"
ACTIVATE_RETRY_ID = "cmd_01978abc-6206-7000-8000-000000006206"
REVOKE_COMMAND_ID = "cmd_01978abc-6207-7000-8000-000000006207"
FOREIGN_ACTOR_ID = "act_01978abc-6210-7000-8000-000000006210"
FOREIGN_ROOT_ID = "agr_01978abc-6211-7000-8000-000000006211"
FOREIGN_PROJECT_ID = "prj_01978abc-6212-7000-8000-000000006212"
NOW = datetime(2026, 7, 12, 12, tzinfo=UTC)

pytestmark = pytest.mark.integration


def _runtime_registry():
    return runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")


def _scoped_grant(
    schemas,
    *,
    actor_id: str = ACTOR_ID,
    actor_classes: list[str] | None = None,
) -> dict[str, object]:
    policy = schemas.resolve_identity(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
    )
    return {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
        "authority_grant_id": GRANT_ID,
        "actor_id": actor_id,
        "allowed_actor_classes": actor_classes or ["human"],
        "allowed_commands": [],
        "allowed_policy_actions": [
            {
                "policy_action_type": "accept_r3_assurance_requirement",
                "schema_id": policy.schema_id,
                "schema_version": policy.schema_version,
                "schema_sha256": policy.sha256,
            }
        ],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {
                "kind": "assurance_requirement",
                "id": REQUIREMENT_ID,
            },
        },
        "risk_ceiling": "R3",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }


def _decision(
    resolver: LedgerAuthorityGrantResolver,
    schemas,
    grant: dict[str, object],
    *,
    record_id: str,
    action: str,
) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        str(grant["schema_version"]),
    )
    return {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
        "record_id": record_id,
        "revision": 1,
        "project_id": context.project_id,
        "store_identity": str(context.store_identity),
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "owner_actor_id": context.owner_actor_id,
        "action": action,
        "target_grant_id": grant["authority_grant_id"],
        "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
        "target_grant_schema_id": grant_schema.schema_id,
        "target_grant_schema_version": grant_schema.schema_version,
        "target_grant_schema_sha256": grant_schema.sha256,
        "subject_scope": grant["subject_scope"],
        "effective_at": grant["effective_at"],
        "expires_at": grant["expires_at"],
        "one_time_use": True,
        "state": "active",
        "decided_at": "2026-07-12T11:00:00Z",
    }


def _activation_command(
    resolver: LedgerAuthorityGrantResolver,
    schemas,
    grant: dict[str, object],
    decision: dict[str, object],
    *,
    command_id: str = ACTIVATE_COMMAND_ID,
) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        str(grant["schema_version"]),
    )
    command_binding = schemas.command_binding("ActivateAuthorityGrant")
    assert command_binding is not None
    return {
        "command_id": command_id,
        "command_type": "ActivateAuthorityGrant",
        "schema_id": "ars://core/command/ActivateAuthorityGrant",
        "schema_version": command_binding.schema_version,
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": GRANT_ID,
        "expected_stream_version": 0,
        "idempotency_key": "activate-scoped-authority-grant",
        "correlation_id": "synthetic-scoped-authority-test",
        "causation_id": None,
        "reason": "activate one synthetic scoped authority grant",
        "evidence_refs": [decision["record_id"]],
        "project_id": PROJECT_ID,
        "payload": {
            "project_id": PROJECT_ID,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision["record_id"],
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "new_grant": grant,
            "new_grant_sha256": sha256_hex(canonical_bytes(grant)),
            "new_grant_schema_sha256": grant_schema.sha256,
        },
    }


def _revocation_command(
    resolver: LedgerAuthorityGrantResolver,
    grant: dict[str, object],
    decision: dict[str, object],
) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema_sha256 = decision["target_grant_schema_sha256"]
    return {
        "command_id": REVOKE_COMMAND_ID,
        "command_type": "RevokeIssuedAuthorityGrant",
        "schema_id": "ars://core/command/RevokeIssuedAuthorityGrant",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": GRANT_ID,
        "expected_stream_version": 1,
        "idempotency_key": "revoke-scoped-authority-grant",
        "correlation_id": "synthetic-scoped-authority-test",
        "causation_id": None,
        "reason": "revoke one synthetic scoped authority grant",
        "evidence_refs": [decision["record_id"]],
        "project_id": PROJECT_ID,
        "payload": {
            "project_id": PROJECT_ID,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision["record_id"],
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "target_grant_id": GRANT_ID,
            "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
            "target_grant_schema_sha256": grant_schema_sha256,
            "reason": "revoke one synthetic scoped authority grant",
        },
    }


def _raw_scoped_administration_event(
    schemas,
    *,
    event_type: str,
    command_type: str,
    stream_id: str,
    payload: dict[str, object],
    suffix: str,
) -> dict[str, object]:
    command_binding = schemas.command_binding(command_type)
    event_binding = schemas.event_binding(event_type, command_type)
    assert command_binding is not None
    assert event_binding is not None
    command_schema = schemas.resolve_identity(
        command_binding.schema_id,
        command_binding.schema_version,
    )
    return {
        "event_type": event_type,
        "stream_id": stream_id,
        "schema_id": event_binding.schema_id,
        "schema_version": event_binding.schema_version,
        "command_id": f"cmd_01978abc-626{suffix}-7000-8000-00000000626{suffix}",
        "command_type": command_type,
        "command_schema_id": command_schema.schema_id,
        "command_schema_version": command_schema.schema_version,
        "command_schema_sha256": command_schema.sha256,
        "idempotency_key": f"raw-scoped-administration-{suffix}",
        "command_payload_hash": sha256_hex(canonical_bytes(payload)),
        "correlation_id": "synthetic-raw-scoped-administration",
        "causation_id": None,
        "actor_id": ACTOR_ID,
        "authority_grant_id": ROOT_ID,
        "occurred_at": None,
        "payload": payload,
    }


def _raw_legacy_revocation_event(
    schemas,
    resolver: LedgerAuthorityGrantResolver,
    grant: dict[str, object],
) -> dict[str, object]:
    command_schema = schemas.resolve_identity("ars://core/command", "1.0.0")
    context = resolver.administration_context()
    payload = {
        "project_id": PROJECT_ID,
        "target_grant_id": grant["authority_grant_id"],
        "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
        "authorizing_grant_id": context.root_grant_id,
        "authorizing_grant_sha256": context.root_grant_sha256,
        "reason": "attempt generic revocation of a typed scoped grant",
    }
    return {
        "event_type": "AuthorityGrantRevoked",
        "stream_id": grant["authority_grant_id"],
        "schema_id": "ars://core/event",
        "schema_version": "1.0.0",
        "command_id": "cmd_01978abc-6295-7000-8000-000000006295",
        "command_type": "RevokeAuthorityGrant",
        "command_schema_id": command_schema.schema_id,
        "command_schema_version": command_schema.schema_version,
        "command_schema_sha256": command_schema.sha256,
        "idempotency_key": "raw-legacy-revocation-of-scoped-grant",
        "command_payload_hash": sha256_hex(canonical_bytes(payload)),
        "correlation_id": "synthetic-cross-family-revocation",
        "causation_id": None,
        "actor_id": ACTOR_ID,
        "authority_grant_id": ROOT_ID,
        "occurred_at": None,
        "payload": payload,
    }


def _rehash_event(event: dict[str, object]) -> dict[str, object]:
    rehashed = deepcopy(event)
    rehashed.pop("event_hash", None)
    rehashed["event_hash"] = sha256_hex(canonical_bytes(rehashed))
    return rehashed


def _positioned_legacy_revocation_event(
    schemas,
    resolver: LedgerAuthorityGrantResolver,
    grant: dict[str, object],
    events: list[dict[str, object]],
) -> dict[str, object]:
    event = _raw_legacy_revocation_event(schemas, resolver, grant)
    event.update(
        {
            "event_id": "evt_01978abc-6296-7000-8000-000000006296",
            "project_id": PROJECT_ID,
            "stream_version": 2,
            "global_position": events[-1]["global_position"] + 1,
            "transaction_id": "txb_01978abc-6297-7000-8000-000000006297",
            "transaction_index": 1,
            "transaction_count": 1,
            "recorded_at": "2026-07-12T12:00:00Z",
            "previous_event_hash": events[-1]["event_hash"],
        }
    )
    return _rehash_event(event)


def _activation_event_payload(
    resolver: LedgerAuthorityGrantResolver,
    schemas,
    grant: dict[str, object],
    *,
    decision_id: str,
    decision_sha256: str,
) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        str(grant["schema_version"]),
    )
    return {
        "authority_admission_version": "owner-bound-v1",
        "project_id": PROJECT_ID,
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "administration_decision_id": decision_id,
        "administration_decision_sha256": decision_sha256,
        "activated_grant_id": grant["authority_grant_id"],
        "activated_grant_sha256": sha256_hex(canonical_bytes(grant)),
        "activated_grant_schema_id": grant_schema.schema_id,
        "activated_grant_schema_version": grant_schema.schema_version,
        "activated_grant_schema_sha256": grant_schema.sha256,
        "subject_scope": grant["subject_scope"],
        "effective_at": grant["effective_at"],
        "expires_at": grant["expires_at"],
    }


def _revocation_event_payload(
    resolver: LedgerAuthorityGrantResolver,
    schemas,
    grant: dict[str, object],
    *,
    decision_id: str,
    decision_sha256: str,
) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        str(grant["schema_version"]),
    )
    return {
        "authority_admission_version": "owner-bound-v1",
        "project_id": PROJECT_ID,
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "administration_decision_id": decision_id,
        "administration_decision_sha256": decision_sha256,
        "target_grant_id": grant["authority_grant_id"],
        "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
        "target_grant_schema_id": grant_schema.schema_id,
        "target_grant_schema_version": grant_schema.schema_version,
        "target_grant_schema_sha256": grant_schema.sha256,
        "reason": "fabricated direct revocation",
    }


def _system(tmp_path):
    control_root, _, identity = _initialized(tmp_path)
    schemas = _runtime_registry()
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        identity,
        schemas,
        approved_witness=identity.witness,
        approved_witness_path=identity.witness_path,
    )
    ledger = EventLedger(control_root, PROJECT_ID, schemas)
    objects = ObjectStore(control_root)
    service = CommandService(
        control_root,
        ledger,
        objects,
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: NOW,
    )
    return control_root, schemas, resolver, ledger, objects, service


def _schema_owner_decision() -> dict[str, object]:
    return {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
        "record_id": ACTIVATE_DECISION_ID,
        "revision": 1,
        "project_id": PROJECT_ID,
        "store_identity": "a" * 64,
        "bootstrap_manifest_sha256": "b" * 64,
        "root_grant_id": ROOT_ID,
        "root_grant_sha256": "c" * 64,
        "owner_actor_id": ACTOR_ID,
        "action": "activate_authority_grant",
        "target_grant_id": GRANT_ID,
        "target_grant_sha256": "d" * 64,
        "target_grant_schema_id": "ars://core/scoped-authority-grant",
        "target_grant_schema_version": SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
        "target_grant_schema_sha256": "e" * 64,
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {
                "kind": "assurance_requirement",
                "id": REQUIREMENT_ID,
            },
        },
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "one_time_use": True,
        "state": "active",
        "decided_at": "2026-07-12T11:00:00Z",
    }


def _schema_revoke_command() -> dict[str, object]:
    digest = "a" * 64
    return {
        "command_id": REVOKE_COMMAND_ID,
        "command_type": "RevokeIssuedAuthorityGrant",
        "schema_id": "ars://core/command/RevokeIssuedAuthorityGrant",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": GRANT_ID,
        "expected_stream_version": 1,
        "idempotency_key": "schema-revoke-command",
        "correlation_id": "schema-revoke-command",
        "causation_id": None,
        "reason": "schema validation fixture",
        "evidence_refs": [REVOKE_DECISION_ID],
        "project_id": PROJECT_ID,
        "payload": {
            "project_id": PROJECT_ID,
            "bootstrap_manifest_sha256": digest,
            "root_grant_id": ROOT_ID,
            "root_grant_sha256": digest,
            "administration_decision_id": REVOKE_DECISION_ID,
            "administration_decision_sha256": digest,
            "target_grant_id": GRANT_ID,
            "target_grant_sha256": digest,
            "target_grant_schema_sha256": digest,
            "reason": "schema validation fixture",
        },
    }


@pytest.mark.parametrize(
    "store_identity",
    ["a" * 63, "A" * 64, "g" * 64],
    ids=["short", "uppercase", "nonhex"],
)
def test_owner_administration_schema_requires_lowercase_sha256_store_identity(
    store_identity,
) -> None:
    schemas = _runtime_registry()
    decision = _schema_owner_decision()
    schemas.validate_active(
        "ars://core/owner-authority-administration-decision",
        decision,
        schema_version=OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
    )
    decision["store_identity"] = store_identity
    with pytest.raises(SchemaError):
        schemas.validate_active(
            "ars://core/owner-authority-administration-decision",
            decision,
            schema_version=OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
        )


@pytest.mark.parametrize(
    ("field", "prefix"),
    [
        ("command_id", "cmd"),
        ("actor_id", "act"),
        ("authority_grant_id", "agr"),
        ("target_stream_id", "agr"),
        ("project_id", "prj"),
        ("payload.project_id", "prj"),
        ("payload.root_grant_id", "agr"),
        ("payload.administration_decision_id", "arec"),
        ("payload.target_grant_id", "agr"),
    ],
)
@pytest.mark.parametrize(
    "malformed_uuid",
    [
        "01978abc-6207-7000-8000-00000000620",
        "01978abc-6207-7000-8000-00000000620G",
    ],
    ids=["truncated", "nonhex"],
)
def test_revoke_command_schema_requires_prefixed_lowercase_uuidv7_ids(
    field,
    prefix,
    malformed_uuid,
) -> None:
    schemas = _runtime_registry()
    command = _schema_revoke_command()
    schemas.validate_active(
        "ars://core/command/RevokeIssuedAuthorityGrant",
        command,
        schema_version="1.0.0",
    )
    invalid = deepcopy(command)
    if field.startswith("payload."):
        target = invalid["payload"]
        key = field.removeprefix("payload.")
    else:
        target = invalid
        key = field
    target[key] = f"{prefix}_{malformed_uuid}"
    with pytest.raises(SchemaError):
        schemas.validate_active(
            "ars://core/command/RevokeIssuedAuthorityGrant",
            invalid,
            schema_version="1.0.0",
        )


def test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant(
    tmp_path,
) -> None:
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write(
        "assurance_record",
        ACTIVATE_DECISION_ID,
        1,
        activation_decision,
    )
    command = _activation_command(resolver, schemas, grant, activation_decision)

    accepted = service.submit(command)
    assert accepted.status == "accepted"
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, schemas),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: NOW,
    )
    retry = service.submit(
        _activation_command(
            resolver,
            schemas,
            grant,
            activation_decision,
            command_id=ACTIVATE_COMMAND_ID,
        )
    )
    assert retry == accepted

    changed = deepcopy(command)
    changed["payload"]["new_grant"]["risk_ceiling"] = "R2"
    changed["payload"]["new_grant_sha256"] = sha256_hex(canonical_bytes(changed["payload"]["new_grant"]))
    with pytest.raises(ConflictError):
        service.submit(changed)

    policy = schemas.resolve_identity(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
    )
    resolved = resolver.resolve_policy_action(
        GRANT_ID,
        ACTOR_ID,
        "human",
        GrantedPolicyActionIdentity(
            "accept_r3_assurance_requirement",
            policy.schema_id,
            str(policy.schema_version),
            policy.sha256,
        ),
        "R3",
        PROJECT_ID,
        "assurance_requirement",
        REQUIREMENT_ID,
        NOW,
    )
    assert resolved.status == "active"
    exact_policy = GrantedPolicyActionIdentity(
        "accept_r3_assurance_requirement",
        policy.schema_id,
        str(policy.schema_version),
        policy.sha256,
    )
    with pytest.raises(ArsError, match="policy-action schema is not active"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "human",
            GrantedPolicyActionIdentity(
                "wrong_policy_action",
                policy.schema_id,
                str(policy.schema_version),
                policy.sha256,
            ),
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            REQUIREMENT_ID,
            NOW,
        )
    with pytest.raises(ArsError, match="bound human owner"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "importer",
            exact_policy,
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            REQUIREMENT_ID,
            NOW,
        )
    with pytest.raises(ArsError, match="subject scope"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "human",
            exact_policy,
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            "asr_01978abc-6290-7000-8000-000000006290",
            NOW,
        )
    with pytest.raises(ArsError, match="expired"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "human",
            exact_policy,
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            REQUIREMENT_ID,
            datetime(2026, 7, 13, tzinfo=UTC),
        )
    with pytest.raises(ArsError, match="schema identity"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "human",
            GrantedPolicyActionIdentity(
                "accept_r3_assurance_requirement",
                policy.schema_id,
                str(policy.schema_version),
                "0" * 64,
            ),
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            REQUIREMENT_ID,
            NOW,
        )

    revocation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    objects.write(
        "assurance_record",
        REVOKE_DECISION_ID,
        1,
        revocation_decision,
    )
    revoked = service.submit(_revocation_command(resolver, grant, revocation_decision))
    assert revoked.status == "accepted"
    with pytest.raises(ArsError, match="revoked"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "human",
            GrantedPolicyActionIdentity(
                "accept_r3_assurance_requirement",
                policy.schema_id,
                str(policy.schema_version),
                policy.sha256,
            ),
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            REQUIREMENT_ID,
            NOW,
        )


def test_replay_selects_revoked_grant_version_from_exact_event_identity(
    tmp_path,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, activation_decision)
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    revocation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    objects.write("assurance_record", REVOKE_DECISION_ID, 1, revocation_decision)
    assert service.submit(_revocation_command(resolver, grant, revocation_decision)).status == "accepted"

    current_events = list(ledger.iter_events())
    current = replay(
        current_events,
        schema_registry=schemas,
        authority_state_validator=lambda state: None,
    )
    assert current["authority_grants"][GRANT_ID]["schema_version"] == "2.1.0"
    assert current["authority_grants"][GRANT_ID]["status"] == "revoked"

    legacy_events = deepcopy(current_events)
    activation = next(event for event in legacy_events if event["command_type"] == "ActivateAuthorityGrant")
    activation["schema_version"] = "1.0.0"
    activation["command_schema_version"] = "1.0.0"
    activation["command_schema_sha256"] = schemas.resolve_identity(
        "ars://core/command/ActivateAuthorityGrant",
        "1.0.0",
    ).sha256
    activation["payload"]["activated_grant_schema_version"] = "2.0.0"
    activation["payload"]["activated_grant_schema_sha256"] = schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        "2.0.0",
    ).sha256
    activation.pop("event_hash")
    activation["event_hash"] = sha256_hex(canonical_bytes(activation))

    revocation = next(event for event in legacy_events if event["command_type"] == "RevokeIssuedAuthorityGrant")
    revocation["schema_version"] = "1.0.0"
    revocation["previous_event_hash"] = activation["event_hash"]
    revocation["payload"]["target_grant_schema_version"] = "2.0.0"
    revocation["payload"]["target_grant_schema_sha256"] = schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        "2.0.0",
    ).sha256
    revocation.pop("event_hash")
    revocation["event_hash"] = sha256_hex(canonical_bytes(revocation))

    historical = replay(
        legacy_events,
        schema_registry=schemas,
        authority_state_validator=lambda state: None,
    )
    assert historical["authority_grants"][GRANT_ID]["schema_version"] == "2.0.0"
    assert historical["authority_grants"][GRANT_ID]["status"] == "revoked"

    mixed = deepcopy(legacy_events)
    mixed[-1]["schema_version"] = "1.1.0"
    mixed[-1].pop("event_hash")
    mixed[-1]["event_hash"] = sha256_hex(canonical_bytes(mixed[-1]))
    with pytest.raises((IntegrityError, SchemaError), match="schema|binding"):
        replay(
            mixed,
            schema_registry=schemas,
            authority_state_validator=lambda state: None,
        )

    reverse_mixed = deepcopy(current_events)
    reverse_mixed[-1]["schema_version"] = "1.0.0"
    reverse_mixed[-1].pop("event_hash")
    reverse_mixed[-1]["event_hash"] = sha256_hex(canonical_bytes(reverse_mixed[-1]))
    with pytest.raises((IntegrityError, SchemaError), match="schema|binding"):
        replay(
            reverse_mixed,
            schema_registry=schemas,
            authority_state_validator=lambda state: None,
        )


def test_policy_resolution_uses_one_projection_snapshot_and_checks_owner_first(
    tmp_path,
    monkeypatch,
) -> None:
    _, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"
    policy = schemas.resolve_identity(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
    )

    cached_projection = resolver._projection()
    calls: list[str] = []
    monkeypatch.setattr(
        resolver,
        "_projection",
        lambda: calls.append("projection") or cached_projection,
    )
    real_context = resolver._administration_context_from_projection

    def tracked_context(projection):
        calls.append("owner-check")
        return real_context(projection)

    monkeypatch.setattr(
        resolver,
        "_administration_context_from_projection",
        tracked_context,
    )
    real_binding = schemas.policy_action_binding

    def tracked_binding(policy_action_type):
        calls.append("binding")
        return real_binding(policy_action_type)

    monkeypatch.setattr(schemas, "policy_action_binding", tracked_binding)

    resolved = resolver.resolve_policy_action(
        GRANT_ID,
        ACTOR_ID,
        "human",
        GrantedPolicyActionIdentity(
            "accept_r3_assurance_requirement",
            policy.schema_id,
            str(policy.schema_version),
            policy.sha256,
        ),
        "R3",
        PROJECT_ID,
        "assurance_requirement",
        REQUIREMENT_ID,
        NOW,
    )

    assert resolved.status == "active"
    assert calls.count("projection") == 1
    assert calls.index("owner-check") < calls.index("binding")


def test_scoped_resolver_enforces_risk_ceiling(tmp_path) -> None:
    _, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    grant["risk_ceiling"] = "R2"
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"
    policy = schemas.resolve_identity(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
    )
    with pytest.raises(ArsError, match="risk ceiling"):
        resolver.resolve_policy_action(
            GRANT_ID,
            ACTOR_ID,
            "human",
            GrantedPolicyActionIdentity(
                "accept_r3_assurance_requirement",
                policy.schema_id,
                str(policy.schema_version),
                policy.sha256,
            ),
            "R3",
            PROJECT_ID,
            "assurance_requirement",
            REQUIREMENT_ID,
            NOW,
        )


def test_scoped_administration_events_require_owner_bound_admission_version(
    tmp_path,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write(
        "assurance_record",
        ACTIVATE_DECISION_ID,
        1,
        activation_decision,
    )
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    revocation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    objects.write(
        "assurance_record",
        REVOKE_DECISION_ID,
        1,
        revocation_decision,
    )
    assert service.submit(_revocation_command(resolver, grant, revocation_decision)).status == "accepted"

    administration_events = [
        event
        for event in ledger.iter_events()
        if event["command_type"] in {"ActivateAuthorityGrant", "RevokeIssuedAuthorityGrant"}
    ]
    assert len(administration_events) == 2
    for event in administration_events:
        assert event["payload"].get("authority_admission_version") == "owner-bound-v1"
        pre_remediation_event = deepcopy(event)
        del pre_remediation_event["payload"]["authority_admission_version"]
        with pytest.raises(SchemaError):
            schemas.validate_active(
                pre_remediation_event["schema_id"],
                pre_remediation_event,
                schema_version=pre_remediation_event["schema_version"],
            )


def test_unactivated_grant_object_is_inert(tmp_path) -> None:
    _, schemas, resolver, _, objects, _ = _system(tmp_path)
    grant = _scoped_grant(schemas)
    objects.write("authority_grant", GRANT_ID, 1, grant)

    with pytest.raises(ArsError, match="not activated"):
        resolver.scoped_grant_identity(GRANT_ID)


def test_create_before_failed_append_remains_inert_and_exact_retry_recovers(
    tmp_path,
    monkeypatch,
) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    changed_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id="arec_01978abc-6260-7000-8000-000000006260",
        action="activate_authority_grant",
    )
    objects.write("assurance_record", changed_decision["record_id"], 1, changed_decision)
    command = _activation_command(resolver, schemas, grant, decision)
    before_events = ledger.snapshot().events
    real_append = ledger.append

    monkeypatch.setattr(
        ledger,
        "append",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic append stop")),
    )
    with pytest.raises(RuntimeError, match="synthetic append stop"):
        service.submit(command)
    assert objects.latest_revision("authority_grant", GRANT_ID) is None
    assert not list((control_root / "objects" / "authority_grant" / GRANT_ID).glob("00000001-*.json"))
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    assert len(list(marker_root.glob("*.json"))) == 1
    with pytest.raises(ArsError, match="not activated"):
        resolver.scoped_grant_identity(GRANT_ID)

    restarted_ledger = EventLedger(control_root, PROJECT_ID, schemas)
    restarted_service = CommandService(
        control_root,
        restarted_ledger,
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: NOW,
    )
    changed_command = _activation_command(resolver, schemas, grant, changed_decision)
    with pytest.raises(ConflictError, match="recovery marker conflicts"):
        restarted_service.submit(changed_command)
    assert restarted_ledger.snapshot().events == before_events
    assert objects.latest_revision("authority_grant", GRANT_ID) is None
    assert len(list(marker_root.glob("*.json"))) == 1

    monkeypatch.setattr(ledger, "append", real_append)
    assert restarted_service.submit(command).status == "accepted"
    assert not list(marker_root.glob("*.json"))


def test_authority_event_producer_cannot_downgrade_to_legacy_schema(
    tmp_path,
) -> None:
    control_root, schemas, _, ledger, _, _ = _system(tmp_path)
    command_schema = schemas.resolve_identity("ars://core/command", "1.0.0")
    forged = {
        "event_type": "AuthorityGrantRevoked",
        "stream_id": PUBLICATION_ID,
        "schema_id": "ars://core/event",
        "schema_version": "1.0.0",
        "command_id": "cmd_01978abc-6250-7000-8000-000000006250",
        "command_type": "ForgedAuthorityProducer",
        "command_schema_id": command_schema.schema_id,
        "command_schema_version": command_schema.schema_version,
        "command_schema_sha256": command_schema.sha256,
        "idempotency_key": "forged-authority-producer",
        "command_payload_hash": "0" * 64,
        "correlation_id": "synthetic-scoped-authority-test",
        "causation_id": None,
        "actor_id": ACTOR_ID,
        "authority_grant_id": ROOT_ID,
        "occurred_at": None,
        "payload": {
            "project_id": PROJECT_ID,
            "target_grant_id": PUBLICATION_ID,
            "target_grant_sha256": "1" * 64,
            "authorizing_grant_id": ROOT_ID,
            "authorizing_grant_sha256": "2" * 64,
            "reason": "forged producer",
        },
    }
    before = ledger.snapshot().events
    with pytest.raises(ArsError, match="unbound event producer"):
        ledger.append([forged])
    assert ledger.snapshot().events == before

    inert_schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    EventLedger(control_root, PROJECT_ID, inert_schemas).append([forged])
    with pytest.raises(IntegrityError, match="unbound authority revocation producer"):
        replay(
            tuple(EventLedger(control_root, PROJECT_ID, inert_schemas).iter_events()),
            schema_registry=schemas,
        )


def test_direct_activation_append_hits_scoped_authority_admission_gate(
    tmp_path,
) -> None:
    control_root, schemas, resolver, ledger, objects, _ = _system(tmp_path)
    grant = _scoped_grant(schemas)
    objects.write("authority_grant", GRANT_ID, 1, grant)
    variants: list[tuple[str, str]] = [
        ("arec_01978abc-6280-7000-8000-000000006280", "0" * 64),
    ]
    for index, mutation in enumerate(
        ["foreign_owner", "wrong_target", "wrong_hash"],
        start=1,
    ):
        decision_id = f"arec_01978abc-628{index}-7000-8000-00000000628{index}"
        decision = _decision(
            resolver,
            schemas,
            grant,
            record_id=decision_id,
            action="activate_authority_grant",
        )
        if mutation == "foreign_owner":
            decision["owner_actor_id"] = FOREIGN_ACTOR_ID
        elif mutation == "wrong_target":
            decision["target_grant_id"] = FOREIGN_ROOT_ID
        objects.write("assurance_record", decision_id, 1, decision)
        decision_sha256 = sha256_hex(canonical_bytes(decision))
        if mutation == "wrong_hash":
            decision_sha256 = "f" * 64
        variants.append((decision_id, decision_sha256))
    before = ledger.snapshot()

    for suffix, (decision_id, decision_sha256) in enumerate(variants):
        payload = _activation_event_payload(
            resolver,
            schemas,
            grant,
            decision_id=decision_id,
            decision_sha256=decision_sha256,
        )
        event = _raw_scoped_administration_event(
            schemas,
            event_type="AuthorityGrantActivated",
            command_type="ActivateAuthorityGrant",
            stream_id=GRANT_ID,
            payload=payload,
            suffix=str(suffix),
        )
        with pytest.raises(
            ArsError,
            match="validated CommandService scoped-authority continuation",
        ):
            ledger.append([event], snapshot=before)
        assert ledger.snapshot() == before
        assert ReceiptStore(control_root).load(event["command_id"]) is None
    with pytest.raises(ArsError, match="not activated"):
        resolver.scoped_grant_identity(GRANT_ID)
    assert objects.read("authority_grant", GRANT_ID, 1) == grant


def test_direct_issued_revocation_append_hits_scoped_authority_admission_gate(
    tmp_path,
) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, activation_decision)
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"

    variants: list[tuple[str, str]] = [
        ("arec_01978abc-6290-7000-8000-000000006290", "0" * 64),
    ]
    for index, mutation in enumerate(
        ["foreign_owner", "wrong_target", "wrong_hash"],
        start=1,
    ):
        decision_id = f"arec_01978abc-629{index}-7000-8000-00000000629{index}"
        decision = _decision(
            resolver,
            schemas,
            grant,
            record_id=decision_id,
            action="revoke_issued_authority_grant",
        )
        if mutation == "foreign_owner":
            decision["owner_actor_id"] = FOREIGN_ACTOR_ID
        elif mutation == "wrong_target":
            decision["target_grant_id"] = FOREIGN_ROOT_ID
        objects.write("assurance_record", decision_id, 1, decision)
        decision_sha256 = sha256_hex(canonical_bytes(decision))
        if mutation == "wrong_hash":
            decision_sha256 = "f" * 64
        variants.append((decision_id, decision_sha256))
    before = ledger.snapshot()

    for suffix, (decision_id, decision_sha256) in enumerate(variants, start=4):
        payload = _revocation_event_payload(
            resolver,
            schemas,
            grant,
            decision_id=decision_id,
            decision_sha256=decision_sha256,
        )
        event = _raw_scoped_administration_event(
            schemas,
            event_type="AuthorityGrantRevoked",
            command_type="RevokeIssuedAuthorityGrant",
            stream_id=GRANT_ID,
            payload=payload,
            suffix=str(suffix),
        )
        with pytest.raises(
            ArsError,
            match="validated CommandService scoped-authority continuation",
        ):
            ledger.append([event], snapshot=before)
        assert ledger.snapshot() == before
        assert ReceiptStore(control_root).load(event["command_id"]) is None
    assert resolver.scoped_grant_identity(GRANT_ID).status == "active"


def test_direct_legacy_revocation_append_cannot_target_scoped_v2_grant(
    tmp_path,
) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, activation_decision)
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    event = _raw_legacy_revocation_event(schemas, resolver, grant)
    before = ledger.snapshot()
    files_before = {
        path.relative_to(control_root).as_posix(): path.read_bytes()
        for root in (control_root / "events", control_root / "runtime")
        for path in root.rglob("*")
        if path.is_file()
    }

    with pytest.raises(
        ArsError,
        match="validated CommandService scoped-authority continuation",
    ):
        ledger.append([event], snapshot=before)

    assert ledger.snapshot() == before
    assert {
        path.relative_to(control_root).as_posix(): path.read_bytes()
        for root in (control_root / "events", control_root / "runtime")
        for path in root.rglob("*")
        if path.is_file()
    } == files_before
    assert ReceiptStore(control_root).load(event["command_id"]) is None
    assert resolver.scoped_grant_identity(GRANT_ID).status == "active"


def test_replay_rejects_legacy_revocation_of_scoped_v2_grant(
    tmp_path,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, activation_decision)
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    events = list(ledger.snapshot().events)
    legacy_revocation = _positioned_legacy_revocation_event(
        schemas,
        resolver,
        grant,
        events,
    )

    with pytest.raises(
        IntegrityError,
        match="legacy authority revocation cannot target scoped grant",
    ):
        replay(
            (*events, legacy_revocation),
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )


def test_replay_rejects_legacy_revocation_of_unknown_typed_grant_marker(
    tmp_path,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, activation_decision)
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    events = list(ledger.snapshot().events)
    legacy_revocation = _positioned_legacy_revocation_event(
        schemas,
        resolver,
        grant,
        events,
    )
    projection = replay(
        tuple(events),
        schema_registry=schemas,
        authority_state_validator=resolver.validate_replayed_administration_state,
    )
    projection["authority_grants"][GRANT_ID]["schema_id"] = "ars://core/unknown-authority-grant"
    projection["authority_grants"][GRANT_ID]["schema_version"] = "1.0.0"

    with pytest.raises(
        IntegrityError,
        match="legacy authority revocation cannot target typed grant",
    ):
        apply_event(projection, legacy_revocation)
    assert projection["authority_grants"][GRANT_ID]["status"] == "active"


def test_legacy_v1_command_service_revocation_and_retry_remain_accepted(
    tmp_path,
) -> None:
    control_root, schemas, resolver, _, _, service = _system(tmp_path)

    accepted = service.submit(_revoke_command(CMD_REVOKE))
    assert accepted.status == "accepted"
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, schemas),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: NOW,
    )
    assert restarted.submit(_revoke_command(CMD_RETRY)) == accepted
    assert (
        replay(
            EventLedger(control_root, PROJECT_ID, schemas).iter_events(),
            schema_registry=schemas,
        )["authority_grants"][PUBLICATION_ID]["status"]
        == "revoked"
    )


def test_typed_v2_owner_decision_revocation_remains_accepted(tmp_path) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, activation_decision)
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    revocation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    objects.write("assurance_record", REVOKE_DECISION_ID, 1, revocation_decision)

    accepted = service.submit(_revocation_command(resolver, grant, revocation_decision))

    assert accepted.status == "accepted"
    assert resolver.scoped_grant_identity(GRANT_ID).status == "revoked"
    assert (
        replay(
            ledger.iter_events(),
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )["authority_grants"][GRANT_ID]["status"]
        == "revoked"
    )


@pytest.mark.parametrize(
    "decision_mutation",
    ["missing", "foreign_owner", "wrong_hash"],
)
def test_restart_revalidates_immutable_activation_decision(
    tmp_path,
    decision_mutation,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    decision_path = objects.write(
        "assurance_record",
        ACTIVATE_DECISION_ID,
        1,
        decision,
    )
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"
    events = ledger.snapshot().events
    with pytest.raises(
        IntegrityError,
        match="administration decision validator unavailable",
    ):
        replay(events, schema_registry=schemas)

    if decision_mutation == "missing":
        decision_path.unlink()
    else:
        changed = deepcopy(decision)
        if decision_mutation == "foreign_owner":
            changed["owner_actor_id"] = FOREIGN_ACTOR_ID
        else:
            changed["decided_at"] = "2026-07-12T10:59:59Z"
        changed_bytes = canonical_bytes(changed)
        replacement = decision_path.with_name(f"00000001-{sha256_hex(changed_bytes)}.json")
        decision_path.unlink()
        replacement.write_bytes(changed_bytes)

    with pytest.raises(IntegrityError, match="administration decision"):
        replay(
            events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
    with pytest.raises(IntegrityError, match="administration decision"):
        resolver.scoped_grant_identity(GRANT_ID)


def test_restart_revalidates_immutable_revocation_decision(tmp_path) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write(
        "assurance_record",
        ACTIVATE_DECISION_ID,
        1,
        activation_decision,
    )
    assert service.submit(_activation_command(resolver, schemas, grant, activation_decision)).status == "accepted"
    revocation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    decision_path = objects.write(
        "assurance_record",
        REVOKE_DECISION_ID,
        1,
        revocation_decision,
    )
    assert service.submit(_revocation_command(resolver, grant, revocation_decision)).status == "accepted"
    changed = deepcopy(revocation_decision)
    changed["target_grant_id"] = FOREIGN_ROOT_ID
    changed_bytes = canonical_bytes(changed)
    replacement = decision_path.with_name(f"00000001-{sha256_hex(changed_bytes)}.json")
    decision_path.unlink()
    replacement.write_bytes(changed_bytes)

    with pytest.raises(IntegrityError, match="administration decision"):
        replay(
            ledger.snapshot().events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
    with pytest.raises(IntegrityError, match="administration decision"):
        resolver.scoped_grant_identity(GRANT_ID)


def test_cli_replay_uses_bound_owner_decision_validator(
    tmp_path,
    capsys,
) -> None:
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    decision_path = objects.write(
        "assurance_record",
        ACTIVATE_DECISION_ID,
        1,
        decision,
    )
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"

    assert _replay_verify(SimpleNamespace(control_root=control_root)) == 0
    assert GRANT_ID in capsys.readouterr().out
    decision_path.unlink()
    with pytest.raises(IntegrityError, match="administration decision"):
        _replay_verify(SimpleNamespace(control_root=control_root))


@pytest.mark.parametrize(
    "identity_case",
    [
        "inactive_command",
        "unresolved_command",
        "wrong_command_hash",
        "wrong_command_subject",
        "wrong_policy_subject",
    ],
)
def test_activation_rejects_unresolved_inactive_or_wrong_subject_identity(
    tmp_path,
    identity_case,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    grant["allowed_policy_actions"] = []
    grant["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {
            "kind": "task",
            "id": "tsk_01978abc-6270-7000-8000-000000006270",
        },
    }
    if identity_case == "inactive_command":
        identity = schemas.resolve_identity(
            "ars://core/command/CompleteAttempt",
            "1.0.0",
        )
        grant["subject_scope"]["subject"] = {
            "kind": "attempt",
            "id": "att_01978abc-6271-7000-8000-000000006271",
        }
        command_type = "CompleteAttempt"
        schema_id = identity.schema_id
        schema_version = identity.schema_version
        schema_sha256 = identity.sha256
    elif identity_case == "unresolved_command":
        command_type = "MissingCommand"
        schema_id = "ars://core/command/MissingCommand"
        schema_version = "1.0.0"
        schema_sha256 = "1" * 64
    else:
        identity = schemas.resolve_identity(
            "ars://core/command/CreateTask",
            "1.0.0",
        )
        command_type = "CreateTask"
        schema_id = identity.schema_id
        schema_version = identity.schema_version
        schema_sha256 = identity.sha256
        if identity_case == "wrong_command_hash":
            schema_sha256 = "2" * 64
        elif identity_case == "wrong_command_subject":
            grant["subject_scope"]["subject"] = {
                "kind": "assurance_requirement",
                "id": REQUIREMENT_ID,
            }
        elif identity_case == "wrong_policy_subject":
            policy = schemas.resolve_identity(
                "ars://core/policy-action/AcceptR3AssuranceRequirement",
                "1.0.0",
            )
            grant["allowed_commands"] = []
            grant["allowed_policy_actions"] = [
                {
                    "policy_action_type": "accept_r3_assurance_requirement",
                    "schema_id": policy.schema_id,
                    "schema_version": policy.schema_version,
                    "schema_sha256": policy.sha256,
                }
            ]
    if identity_case != "wrong_policy_subject":
        grant["allowed_commands"] = [
            {
                "command_type": command_type,
                "schema_id": schema_id,
                "schema_version": schema_version,
                "schema_sha256": schema_sha256,
            }
        ]
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    before = ledger.snapshot()

    receipt = service.submit(_activation_command(resolver, schemas, grant, decision))

    assert receipt.status == "rejected"
    assert ledger.snapshot() == before
    assert objects.latest_revision("authority_grant", GRANT_ID) is None


def test_later_binding_cannot_wake_rejected_inactive_identity(tmp_path) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    inactive = schemas.resolve_identity(
        "ars://core/command/CompleteAttempt",
        "1.0.0",
    )
    grant["allowed_policy_actions"] = []
    grant["allowed_commands"] = [
        {
            "command_type": "CompleteAttempt",
            "schema_id": inactive.schema_id,
            "schema_version": inactive.schema_version,
            "schema_sha256": inactive.sha256,
        }
    ]
    grant["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {
            "kind": "attempt",
            "id": "att_01978abc-6272-7000-8000-000000006272",
        },
    }
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    before = ledger.snapshot()
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "rejected"
    assert ledger.snapshot() == before

    later_registry = SchemaRegistry(
        REPO_ROOT / ".research-system" / "schemas",
        active_bindings=(
            *schemas._active_bindings,
            SchemaBinding(
                inactive.schema_id,
                inactive.schema_version,
                command_type="CompleteAttempt",
            ),
        ),
    )
    later_resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        resolver.expected_store_identity,
        later_registry,
    )
    with pytest.raises(ArsError, match="not activated"):
        later_resolver.scoped_grant_identity(GRANT_ID)


def test_active_command_identity_uses_its_closed_subject_mapping(tmp_path) -> None:
    _, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas, actor_id=GRANTEE_ID)
    identity = schemas.resolve_identity(
        "ars://core/command/CreateTask",
        "1.0.0",
    )
    task_id = "tsk_01978abc-6273-7000-8000-000000006273"
    grant["allowed_policy_actions"] = []
    grant["allowed_commands"] = [
        {
            "command_type": "CreateTask",
            "schema_id": identity.schema_id,
            "schema_version": identity.schema_version,
            "schema_sha256": identity.sha256,
        }
    ]
    grant["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {
            "kind": "task",
            "id": task_id,
        },
    }
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"

    resolved = resolver.resolve_command(
        GRANT_ID,
        GRANTEE_ID,
        "human",
        GrantedCommandIdentity(
            "CreateTask",
            identity.schema_id,
            str(identity.schema_version),
            identity.sha256,
        ),
        "R3",
        PROJECT_ID,
        "task",
        task_id,
        NOW,
    )
    assert resolved.status == "active"


@pytest.mark.parametrize(
    ("actor_id", "actor_classes"),
    [
        (ACTOR_ID, ["agent"]),
        (ACTOR_ID, ["service"]),
        (GRANTEE_ID, ["human"]),
    ],
)
def test_r3_policy_grant_requires_bound_human_owner(
    tmp_path,
    actor_id,
    actor_classes,
) -> None:
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(
        schemas,
        actor_id=actor_id,
        actor_classes=actor_classes,
    )
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    before = ledger.snapshot()

    receipt = service.submit(_activation_command(resolver, schemas, grant, decision))

    assert receipt.status == "rejected"
    assert ledger.snapshot() == before
    assert objects.latest_revision("authority_grant", GRANT_ID) is None


def test_activation_rejects_wrong_owner_root_project_bootstrap_decision_and_schema(
    tmp_path,
) -> None:
    _, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    base = _activation_command(resolver, schemas, grant, decision)

    candidates: list[dict[str, object]] = []
    wrong_owner = deepcopy(base)
    wrong_owner["actor_id"] = FOREIGN_ACTOR_ID
    candidates.append(wrong_owner)
    wrong_root = deepcopy(base)
    wrong_root["authority_grant_id"] = FOREIGN_ROOT_ID
    wrong_root["payload"]["root_grant_id"] = FOREIGN_ROOT_ID
    candidates.append(wrong_root)
    wrong_project = deepcopy(base)
    wrong_project["project_id"] = FOREIGN_PROJECT_ID
    wrong_project["payload"]["project_id"] = FOREIGN_PROJECT_ID
    candidates.append(wrong_project)
    wrong_bootstrap = deepcopy(base)
    wrong_bootstrap["payload"]["bootstrap_manifest_sha256"] = "d" * 64
    candidates.append(wrong_bootstrap)
    wrong_decision_hash = deepcopy(base)
    wrong_decision_hash["payload"]["administration_decision_sha256"] = "e" * 64
    candidates.append(wrong_decision_hash)
    wrong_schema = deepcopy(base)
    wrong_schema["payload"]["new_grant_schema_sha256"] = "f" * 64
    candidates.append(wrong_schema)

    for index, candidate in enumerate(candidates, start=1):
        candidate["command_id"] = f"cmd_01978abc-623{index}-7000-8000-00000000623{index}"
        candidate["idempotency_key"] = f"invalid-activation-{index}"
        assert service.submit(candidate).status == "rejected"

    wrong_store_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id="arec_01978abc-6240-7000-8000-000000006240",
        action="activate_authority_grant",
    )
    wrong_store_decision["store_identity"] = "c" * 64
    objects.write(
        "assurance_record",
        wrong_store_decision["record_id"],
        1,
        wrong_store_decision,
    )
    wrong_store = _activation_command(
        resolver,
        schemas,
        grant,
        wrong_store_decision,
        command_id="cmd_01978abc-6241-7000-8000-000000006241",
    )
    wrong_store["idempotency_key"] = "invalid-activation-wrong-store"
    assert service.submit(wrong_store).status == "rejected"

    future_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id="arec_01978abc-6246-7000-8000-000000006246",
        action="activate_authority_grant",
    )
    future_decision["decided_at"] = "2026-07-12T12:30:00Z"
    objects.write(
        "assurance_record",
        future_decision["record_id"],
        1,
        future_decision,
    )
    future_command = _activation_command(
        resolver,
        schemas,
        grant,
        future_decision,
        command_id="cmd_01978abc-6247-7000-8000-000000006247",
    )
    future_command["idempotency_key"] = "invalid-activation-future-decision"
    assert service.submit(future_command).status == "rejected"

    missing_decision = deepcopy(base)
    missing_decision["command_id"] = "cmd_01978abc-6242-7000-8000-000000006242"
    missing_decision["idempotency_key"] = "invalid-activation-missing-decision"
    missing_decision["payload"]["administration_decision_id"] = "arec_01978abc-6243-7000-8000-000000006243"
    with pytest.raises(
        IntegrityError,
        match="owner authority administration decision invalid",
    ):
        service.submit(missing_decision)

    legacy_target = resolver.grant_identity(PUBLICATION_ID)
    unrelated_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id="arec_01978abc-6244-7000-8000-000000006244",
        action="revoke_issued_authority_grant",
    )
    unrelated_decision["target_grant_id"] = PUBLICATION_ID
    unrelated_decision["target_grant_sha256"] = legacy_target.authority_grant_sha256
    objects.write(
        "assurance_record",
        unrelated_decision["record_id"],
        1,
        unrelated_decision,
    )
    unrelated_revoke = _revocation_command(
        resolver,
        grant,
        unrelated_decision,
    )
    unrelated_revoke["command_id"] = "cmd_01978abc-6245-7000-8000-000000006245"
    unrelated_revoke["target_stream_id"] = PUBLICATION_ID
    unrelated_revoke["idempotency_key"] = "invalid-unrelated-revocation"
    unrelated_revoke["payload"]["target_grant_id"] = PUBLICATION_ID
    unrelated_revoke["payload"]["target_grant_sha256"] = legacy_target.authority_grant_sha256
    assert service.submit(unrelated_revoke).status == "rejected"

    assert objects.latest_revision("authority_grant", GRANT_ID) is None


def test_activation_and_revocation_are_serialized_by_the_writer_lock(
    tmp_path,
    monkeypatch,
) -> None:
    _, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    activation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    revocation_decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    objects.write(
        "assurance_record",
        ACTIVATE_DECISION_ID,
        1,
        activation_decision,
    )
    objects.write(
        "assurance_record",
        REVOKE_DECISION_ID,
        1,
        revocation_decision,
    )
    activate = _activation_command(
        resolver,
        schemas,
        grant,
        activation_decision,
    )
    revoke = _revocation_command(resolver, grant, revocation_decision)
    entered = threading.Event()
    release = threading.Event()
    real_prepare = service._prepare_scoped_authority_activation

    def paused_prepare(command, observed_version):
        prepared = real_prepare(command, observed_version)
        entered.set()
        if not release.wait(timeout=10):
            raise AssertionError("synthetic activation pause was not released")
        return prepared

    monkeypatch.setattr(
        service,
        "_prepare_scoped_authority_activation",
        paused_prepare,
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        activation_future = executor.submit(service.submit, activate)
        try:
            assert entered.wait(timeout=10)
            revoke_future = executor.submit(service.submit, revoke)
            with pytest.raises(ConflictError, match="writer lock exists"):
                revoke_future.result(timeout=5)
        finally:
            release.set()
        assert activation_future.result(timeout=20).status == "accepted"

    monkeypatch.setattr(
        service,
        "_prepare_scoped_authority_activation",
        real_prepare,
    )
    assert service.submit(revoke).status == "accepted"
    assert resolver.scoped_grant_identity(GRANT_ID).status == "revoked"
