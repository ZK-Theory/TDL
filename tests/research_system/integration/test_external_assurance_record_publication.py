"""Exercise the additive external-record scoped grant through real authority replay."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from research_system.assurance.external_records import (
    ExternalAssuranceRecordStore,
    ExternalRecordPublicationContext,
)
from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.authority import (
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    LedgerAuthorityGrantResolver,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError
from research_system.projection.replay import replay
from research_system.store.identity import load_store_manifest
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.integration.test_scoped_authority_grant_activation import (
    ACTIVATE_COMMAND_ID,
    ACTIVATE_DECISION_ID,
    ACTOR_ID,
    GRANT_ID,
    PROJECT_ID,
    REVOKE_COMMAND_ID,
    REVOKE_DECISION_ID,
    ROOT_ID,
    NOW,
    _system,
)
from tests.research_system.factories import REPO_ROOT


RECORD_ID = ACTOR_ID
TASK_ID = "tsk_01978abc-6300-7000-8000-000000006300"
SESSION_ID = "ctx_01978abc-6300-7000-8000-000000006301"


def _external_grant(schemas: object) -> dict[str, object]:
    policy = schemas.resolve_identity(
        "ars://core/policy-action/PublishExternalAssuranceRecord",
        "1.0.0",
    )
    return {
        "schema_id": EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
        "schema_version": EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_actor_classes": ["human"],
        "allowed_commands": [],
        "allowed_policy_actions": [
            {
                "policy_action_type": "publish_external_assurance_record",
                "schema_id": policy.schema_id,
                "schema_version": policy.schema_version,
                "schema_sha256": policy.sha256,
            }
        ],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "external_assurance_record", "id": RECORD_ID},
        },
        "risk_ceiling": "R1",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }


def _owner_decision(resolver, schemas, grant: dict[str, object], *, record_id: str, action: str) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
        EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    )
    return {
        "schema_id": "ars://core/external-assurance-record-owner-authority-administration-decision",
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


def _activation_command(resolver, schemas, grant: dict[str, object], decision: dict[str, object]) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
        EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    )
    command_schema = schemas.resolve_identity(
        "ars://core/command/ActivateExternalAssuranceRecordGrant",
        "1.0.0",
    )
    return {
        "command_id": ACTIVATE_COMMAND_ID,
        "command_type": "ActivateExternalAssuranceRecordGrant",
        "schema_id": command_schema.schema_id,
        "schema_version": command_schema.schema_version,
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": GRANT_ID,
        "expected_stream_version": 0,
        "idempotency_key": "activate-external-assurance-record-grant",
        "correlation_id": "synthetic-external-record-authority-test",
        "causation_id": None,
        "reason": "activate one synthetic external-record scoped authority grant",
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


def _revocation_command(resolver, schemas, grant: dict[str, object], decision: dict[str, object]) -> dict[str, object]:
    context = resolver.administration_context()
    grant_schema = schemas.resolve_identity(
        EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
        EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    )
    command_schema = schemas.resolve_identity(
        "ars://core/command/RevokeExternalAssuranceRecordGrant",
        "1.0.0",
    )
    return {
        "command_id": REVOKE_COMMAND_ID,
        "command_type": "RevokeExternalAssuranceRecordGrant",
        "schema_id": command_schema.schema_id,
        "schema_version": command_schema.schema_version,
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": GRANT_ID,
        "expected_stream_version": 1,
        "idempotency_key": "revoke-external-assurance-record-grant",
        "correlation_id": "synthetic-external-record-authority-test",
        "causation_id": None,
        "reason": "revoke one synthetic external-record scoped authority grant",
        "evidence_refs": [decision["record_id"]],
        "project_id": PROJECT_ID,
        "payload": {
            "project_id": PROJECT_ID,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision["record_id"],
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "target_grant_id": grant["authority_grant_id"],
            "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
            "target_grant_schema_sha256": grant_schema.sha256,
            "reason": "revoke one synthetic external-record scoped authority grant",
        },
    }


def _body(name: str = "Ada") -> dict[str, str]:
    return {
        "record_type": "canonical_actor",
        "actor_id": RECORD_ID,
        "actor_kind": "human",
        "canonical_name": name,
        "status": "active",
    }


def _context(
    binding: ControlBinding, body: dict[str, str], *, revision: int = 1, previous: int = 0
) -> ExternalRecordPublicationContext:
    return ExternalRecordPublicationContext(
        caller_actor_id=ACTOR_ID,
        caller_actor_class="human",
        authority_grant_id=GRANT_ID,
        record_action="create" if revision == 1 else "revise",
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=revision,
        expected_previous_revision=previous,
        project_id=PROJECT_ID,
        store_identity=binding.store_identity,
        authority_root=ROOT_ID,
        canonical_sha256=sha256_hex(canonical_bytes(body)),
        task_id=TASK_ID,
        session_id=SESSION_ID,
        relationship_record_id=None,
        required_risk="R1",
        occurred_at="2026-07-12T12:00:00Z",
    )


def _fixture(tmp_path: Path):
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _external_grant(schemas)
    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    accepted = service.submit(_activation_command(resolver, schemas, grant, decision))
    assert accepted.status == "accepted"
    manifest = load_store_manifest(control_root)
    code_root = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / ".research-system" / "contracts",
        code_root / ".research-system" / "contracts",
    )
    binding = ControlBinding(
        code_roots=(code_root.resolve(),),
        control_root=control_root.resolve(),
        project_id=PROJECT_ID,
        schema_root=(code_root / ".research-system" / "schemas").resolve(),
        store_identity=manifest["store_identity"],
    )
    return binding, schemas, resolver, objects, service, grant


def _durable_files(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _restart_system(control_root: Path, schemas: object):
    manifest = load_store_manifest(control_root)
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        manifest["store_identity"],
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
    return resolver, ledger, objects, service


@pytest.mark.integration
def test_external_grant_activation_append_failure_rolls_back_and_retry_is_single(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _external_grant(schemas)
    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    command = _activation_command(resolver, schemas, grant, decision)
    before_files = _durable_files(control_root)
    before_snapshot = ledger.snapshot()
    before_projection = replay(
        before_snapshot.events,
        schema_registry=schemas,
        authority_state_validator=resolver.validate_replayed_administration_state,
    )

    def fail_scoped_append(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected scoped-authority append failure")

    monkeypatch.setattr(
        ledger,
        "_append_scoped_authority_from_validated_submit",
        fail_scoped_append,
    )
    with pytest.raises(RuntimeError, match="injected scoped-authority append failure"):
        service.submit(command)

    assert _durable_files(control_root) == before_files
    assert ledger.snapshot() == before_snapshot
    assert canonical_bytes(
        replay(
            ledger.snapshot().events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
    ) == canonical_bytes(before_projection)
    assert objects.latest_revision("authority_grant", GRANT_ID) is None

    restarted_resolver, restarted_ledger, restarted_objects, restarted_service = _restart_system(
        control_root,
        schemas,
    )
    restarted_projection = replay(
        restarted_ledger.snapshot().events,
        schema_registry=schemas,
        authority_state_validator=restarted_resolver.validate_replayed_administration_state,
    )
    assert GRANT_ID not in restarted_projection["authority_grants"]
    assert restarted_objects.latest_revision("authority_grant", GRANT_ID) is None

    retry = restarted_service.submit(command)
    assert retry.status == "accepted"
    accepted_snapshot = restarted_ledger.snapshot()
    assert len(accepted_snapshot.events) == len(before_snapshot.events) + 1
    assert sum(event.get("command_id") == ACTIVATE_COMMAND_ID for event in accepted_snapshot.events) == 1
    assert restarted_objects.latest_revision("authority_grant", GRANT_ID) == 1
    assert restarted_service.submit(command) == retry
    assert len(restarted_ledger.snapshot().events) == len(accepted_snapshot.events)
    assert restarted_resolver.scoped_grant_identity(GRANT_ID).status == "active"


@pytest.mark.integration
def test_restart_recovers_uncommitted_external_grant_activation_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _external_grant(schemas)
    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    command = _activation_command(resolver, schemas, grant, decision)
    before_files = _durable_files(control_root)
    real_prepare = service._prepare_scoped_authority_activation

    def terminate_after_object_publication(command, observed_version):
        real_prepare(command, observed_version)
        raise RuntimeError("simulated termination after object publication")

    monkeypatch.setattr(
        service,
        "_prepare_scoped_authority_activation",
        terminate_after_object_publication,
    )
    with pytest.raises(RuntimeError, match="simulated termination after object publication"):
        service.submit(command)

    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    assert len(list(marker_root.glob("*.json"))) == 1
    assert objects.latest_revision("authority_grant", GRANT_ID) == 1
    assert not any(event.get("command_id") == ACTIVATE_COMMAND_ID for event in ledger.snapshot().events)

    restarted_resolver, restarted_ledger, restarted_objects, restarted_service = _restart_system(
        control_root,
        schemas,
    )
    assert _durable_files(control_root) == before_files
    assert not list(marker_root.glob("*.json"))
    assert restarted_objects.latest_revision("authority_grant", GRANT_ID) is None
    projection = replay(
        restarted_ledger.snapshot().events,
        schema_registry=schemas,
        authority_state_validator=restarted_resolver.validate_replayed_administration_state,
    )
    assert GRANT_ID not in projection["authority_grants"]
    assert restarted_service.submit(command).status == "accepted"


@pytest.mark.integration
def test_failed_external_grant_activation_never_removes_preexisting_matching_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    grant = _external_grant(schemas)
    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    preexisting_path = objects.write("authority_grant", GRANT_ID, 1, grant)
    preexisting_bytes = preexisting_path.read_bytes()
    command = _activation_command(resolver, schemas, grant, decision)
    before_files = _durable_files(control_root)
    before_snapshot = ledger.snapshot()

    def fail_scoped_append(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected scoped-authority append failure")

    monkeypatch.setattr(
        ledger,
        "_append_scoped_authority_from_validated_submit",
        fail_scoped_append,
    )
    with pytest.raises(RuntimeError, match="injected scoped-authority append failure"):
        service.submit(command)

    assert _durable_files(control_root) == before_files
    assert ledger.snapshot() == before_snapshot
    assert preexisting_path.read_bytes() == preexisting_bytes
    assert objects.read("authority_grant", GRANT_ID, 1) == grant
    projection = replay(
        ledger.snapshot().events,
        schema_registry=schemas,
        authority_state_validator=resolver.validate_replayed_administration_state,
    )
    assert GRANT_ID not in projection["authority_grants"]


@pytest.mark.integration
def test_governed_external_grant_activates_writer_and_exact_retry(tmp_path: Path) -> None:
    binding, _, resolver, _, _, _ = _fixture(tmp_path)
    store = ExternalAssuranceRecordStore(binding)
    body = _body()

    receipt = store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=_context(binding, body),
    )
    restarted_store = ExternalAssuranceRecordStore(binding)
    retry = restarted_store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=_context(binding, body),
    )

    assert retry == receipt
    assert resolver.scoped_grant_identity(GRANT_ID).schema_id == EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID
    resolved = ControlStoreAuthorityResolver(binding).resolve_with_receipt(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=binding.store_identity,
        phase="load",
    )
    assert resolved.revision == receipt.revision
    assert resolved.canonical_sha256 == receipt.canonical_sha256


@pytest.mark.integration
def test_governed_external_grant_revocation_blocks_revision_retry(tmp_path: Path) -> None:
    binding, schemas, resolver, objects, service, grant = _fixture(tmp_path)
    store = ExternalAssuranceRecordStore(binding)
    body = _body()
    store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=_context(binding, body),
    )

    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=REVOKE_DECISION_ID,
        action="revoke_issued_authority_grant",
    )
    objects.write("assurance_record", REVOKE_DECISION_ID, 1, decision)
    assert service.submit(_revocation_command(resolver, schemas, grant, decision)).status == "accepted"

    revised = _body("Grace")
    with pytest.raises(ArsError, match="revoked"):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=2,
            expected_previous_revision=1,
            record=revised,
            publication_context=_context(binding, revised, revision=2, previous=1),
        )
    assert not list((binding.control_root / "objects" / "canonical_actor" / RECORD_ID).glob("00000002-*.json"))


@pytest.mark.integration
def test_governed_external_grant_rejects_changed_retry_without_replacing_revision(tmp_path: Path) -> None:
    binding, _, _, _, _, _ = _fixture(tmp_path)
    store = ExternalAssuranceRecordStore(binding)
    body = _body()
    store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=_context(binding, body),
    )
    changed = _body("Grace")
    with pytest.raises(ConflictError, match="different content"):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=changed,
            publication_context=_context(binding, changed),
        )
