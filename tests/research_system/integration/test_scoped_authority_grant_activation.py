from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import threading

import pytest

from research_system.authority import (
    GrantedPolicyActionIdentity,
    LedgerAuthorityGrantResolver,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import REPO_ROOT
from tests.research_system.integration.test_authority_grant_source import (
    ACTOR_ID,
    PROJECT_ID,
    PUBLICATION_ID,
    ROOT_ID,
    _initialized,
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


def _runtime_registry():
    return runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")


def _scoped_grant(schemas) -> dict[str, object]:
    policy = schemas.resolve_identity(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
    )
    return {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.0.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": GRANTEE_ID,
        "allowed_actor_classes": ["human"],
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
        "2.0.0",
    )
    return {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": "1.0.0",
        "record_id": record_id,
        "revision": 1,
        "project_id": context.project_id,
        "store_identity": context.store_identity,
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
        "2.0.0",
    )
    return {
        "command_id": command_id,
        "command_type": "ActivateAuthorityGrant",
        "schema_id": "ars://core/command/ActivateAuthorityGrant",
        "schema_version": "1.0.0",
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


def _system(tmp_path):
    control_root, _, identity = _initialized(tmp_path)
    schemas = _runtime_registry()
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        identity,
        schemas,
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
            command_id=ACTIVATE_RETRY_ID,
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
        GRANTEE_ID,
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
            GRANTEE_ID,
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
    with pytest.raises(ArsError, match="actor class"):
        resolver.resolve_policy_action(
            GRANT_ID,
            GRANTEE_ID,
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
            GRANTEE_ID,
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
            GRANTEE_ID,
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
            GRANTEE_ID,
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
            GRANTEE_ID,
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
            GRANTEE_ID,
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
    _, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _scoped_grant(schemas)
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    command = _activation_command(resolver, schemas, grant, decision)
    real_append = ledger.append

    monkeypatch.setattr(
        ledger,
        "append",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic append stop")),
    )
    with pytest.raises(RuntimeError, match="synthetic append stop"):
        service.submit(command)
    assert objects.read("authority_grant", GRANT_ID, 1) == grant
    with pytest.raises(ArsError, match="not activated"):
        resolver.scoped_grant_identity(GRANT_ID)

    monkeypatch.setattr(ledger, "append", real_append)
    assert service.submit(command).status == "accepted"


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
    with pytest.raises(IntegrityError):
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
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(service.submit, activate)
        assert entered.wait(timeout=10)
        try:
            with pytest.raises(ConflictError):
                service.submit(revoke)
        finally:
            release.set()
        assert future.result(timeout=20).status == "accepted"

    monkeypatch.setattr(
        service,
        "_prepare_scoped_authority_activation",
        real_prepare,
    )
    assert service.submit(revoke).status == "accepted"
    assert resolver.scoped_grant_identity(GRANT_ID).status == "revoked"
