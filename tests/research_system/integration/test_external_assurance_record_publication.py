"""Exercise the additive external-record scoped grant through real authority replay."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

from research_system.assurance.external_records import (
    ExternalAssuranceRecordStore,
    ExternalRecordPublicationContext,
)
from research_system.assurance.relationship_facts import (
    ProtectedRelationshipReference,
    RelationshipEvidenceFactsStore,
    RelationshipEvidenceParticipant,
)
from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.authority import (
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    LedgerAuthorityGrantResolver,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.command.service import CommandService
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.projection.replay import replay
from research_system.schema_registry import runtime_schema_registry
from research_system.store.identity import (
    load_store_manifest,
    load_store_manifest_unbound,
    load_store_origin_witness,
    origin_witness_path,
)
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.integration.test_scoped_authority_grant_activation import (
    ACTIVATE_COMMAND_ID,
    ACTIVATE_DECISION_ID,
    ACTOR_ID,
    FOREIGN_ACTOR_ID,
    FOREIGN_PROJECT_ID,
    GRANT_ID,
    PROJECT_ID,
    REQUIREMENT_ID,
    REVOKE_COMMAND_ID,
    REVOKE_DECISION_ID,
    ROOT_ID,
    NOW,
    _activation_command as _authority_activation_command,
    _decision as _authority_decision,
    _scoped_grant as _authority_grant,
    _system,
)
from tests.research_system.contracts import test_wp6_3_tdl_private_assurance_pack_contract as frozen
from tests.research_system.factories import REPO_ROOT


RECORD_ID = ACTOR_ID
TASK_ID = "tsk_01978abc-6300-7000-8000-000000006300"
SESSION_ID = "ctx_01978abc-6300-7000-8000-000000006301"


def _external_grant(
    schemas: object,
    *,
    record_id: str = RECORD_ID,
    actor_id: str = ACTOR_ID,
    actor_classes: list[str] | None = None,
    risk_ceiling: str = "R1",
) -> dict[str, object]:
    policy = schemas.resolve_identity(
        "ars://core/policy-action/PublishExternalAssuranceRecord",
        "1.0.0",
    )
    return {
        "schema_id": EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
        "schema_version": EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
        "authority_grant_id": GRANT_ID,
        "actor_id": actor_id,
        "allowed_actor_classes": actor_classes or ["human"],
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
            "subject": {"kind": "external_assurance_record", "id": record_id},
        },
        "risk_ceiling": risk_ceiling,
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


def _activation_command(
    resolver,
    schemas,
    grant: dict[str, object],
    decision: dict[str, object],
    *,
    command_id: str = ACTIVATE_COMMAND_ID,
    idempotency_key: str = "activate-external-assurance-record-grant",
    correlation_id: str = "synthetic-external-record-authority-test",
) -> dict[str, object]:
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
        "command_id": command_id,
        "command_type": "ActivateExternalAssuranceRecordGrant",
        "schema_id": command_schema.schema_id,
        "schema_version": command_schema.schema_version,
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": grant["authority_grant_id"],
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": correlation_id,
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


def _activation_case(tmp_path: Path, activation_kind: str):
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    if activation_kind == "authority":
        grant = _authority_grant(schemas)
        decision = _authority_decision(
            resolver,
            schemas,
            grant,
            record_id=ACTIVATE_DECISION_ID,
            action="activate_authority_grant",
        )
        command = _authority_activation_command(resolver, schemas, grant, decision)
    else:
        grant = _external_grant(schemas)
        decision = _owner_decision(
            resolver,
            schemas,
            grant,
            record_id=ACTIVATE_DECISION_ID,
            action="activate_authority_grant",
        )
        command = _activation_command(resolver, schemas, grant, decision)
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    return control_root, schemas, resolver, objects, service, command


def _foreign_activation_marker_bytes(
    service: CommandService,
    schemas: object,
    command: dict[str, object],
    *,
    identity_suffix: str = "6302",
    command_id: str | None = None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> bytes:
    foreign = deepcopy(command)
    foreign["command_id"] = command_id or f"cmd_01978abc-6300-7000-8000-00000000{identity_suffix}"
    foreign["idempotency_key"] = idempotency_key or f"{command['idempotency_key']}-foreign-{identity_suffix}"
    foreign["correlation_id"] = correlation_id or f"{command['correlation_id']}-foreign-{identity_suffix}"
    foreign_envelope = {
        key: value
        for key, value in foreign.items()
        if key not in {"command_schema_id", "command_schema_version", "command_schema_sha256"}
    }
    foreign_path = service._scoped_activation_marker_path(foreign["command_id"])
    service._write_scoped_activation_marker(
        Command(foreign_envelope),
        command_schema=schemas.resolve_identity(foreign["schema_id"], foreign["schema_version"]),
        existed_before=False,
    )
    foreign_bytes = foreign_path.read_bytes()
    foreign_path.unlink()
    return foreign_bytes


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
    witness = resolver.approved_witness
    manifest = load_store_manifest(control_root, approved_witness=witness)
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
        origin_witness=witness,
    )
    return binding, schemas, resolver, objects, service, grant


FACTS_RELATIONSHIP_ID = "rel_01978abc-6300-7000-8000-0000000063a0"
FACTS_PRODUCER_TASK_ID = "tsk_01978abc-6300-7000-8000-0000000063a1"
FACTS_REVIEW_TASK_ID = "tsk_01978abc-6300-7000-8000-0000000063a2"
FACTS_PRODUCER_SESSION_ID = "ctx_01978abc-6300-7000-8000-0000000063a3"
FACTS_REVIEW_SESSION_ID = "ctx_01978abc-6300-7000-8000-0000000063a4"
FACTS_HANDOFF_ID = "hnd_01978abc-6300-7000-8000-0000000063a5"


def _facts_fixture(tmp_path: Path) -> ControlBinding:
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _external_grant(schemas, record_id=FACTS_RELATIONSHIP_ID)
    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"
    witness = resolver.approved_witness
    manifest = load_store_manifest(control_root, approved_witness=witness)
    code_root = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / ".research-system" / "contracts",
        code_root / ".research-system" / "contracts",
    )
    return ControlBinding(
        code_roots=(code_root.resolve(),),
        control_root=control_root.resolve(),
        project_id=PROJECT_ID,
        schema_root=(code_root / ".research-system" / "schemas").resolve(),
        store_identity=manifest["store_identity"],
        origin_witness=witness,
    )


def _relationship_body() -> dict[str, object]:
    return {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": FACTS_RELATIONSHIP_ID,
        "relationship_context": "requirement_scope_review",
        "subject_actor_id": ACTOR_ID,
        "object_actor_id": FOREIGN_ACTOR_ID,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
    }


def _facts_participants(
    *,
    same_task: bool = False,
    same_session: bool = False,
    same_context_hash: bool = False,
    same_model_family: bool = False,
) -> tuple[RelationshipEvidenceParticipant, RelationshipEvidenceParticipant]:
    producer = RelationshipEvidenceParticipant(
        actor_id=FOREIGN_ACTOR_ID,
        task_id=FACTS_PRODUCER_TASK_ID,
        session_id=FACTS_PRODUCER_SESSION_ID,
        context_hash="1" * 64,
        model_family="codex",
        stable_handoff_or_run_id=FACTS_HANDOFF_ID,
    )
    reviewer = RelationshipEvidenceParticipant(
        actor_id=ACTOR_ID,
        task_id=FACTS_PRODUCER_TASK_ID if same_task else FACTS_REVIEW_TASK_ID,
        session_id=FACTS_PRODUCER_SESSION_ID if same_session else FACTS_REVIEW_SESSION_ID,
        context_hash="1" * 64 if same_context_hash else "2" * 64,
        model_family="codex" if same_model_family else "claude",
        stable_handoff_or_run_id=FACTS_HANDOFF_ID,
    )
    return producer, reviewer


def _facts_publication_context(
    binding: ControlBinding,
    body: Mapping[str, object],
    *,
    revision: int = 1,
    previous: int = 0,
) -> ExternalRecordPublicationContext:
    return ExternalRecordPublicationContext(
        caller_actor_id=ACTOR_ID,
        caller_actor_class="human",
        authority_grant_id=GRANT_ID,
        record_action="create" if revision == 1 else "revise",
        record_class="producer_relationship_evidence",
        record_id=FACTS_RELATIONSHIP_ID,
        revision=revision,
        expected_previous_revision=previous,
        project_id=PROJECT_ID,
        store_identity=binding.store_identity,
        authority_root=ROOT_ID,
        canonical_sha256=sha256_hex(canonical_bytes(body)),
        task_id=FACTS_REVIEW_TASK_ID,
        session_id=FACTS_REVIEW_SESSION_ID,
        relationship_record_id=FACTS_RELATIONSHIP_ID,
        required_risk="R1",
        occurred_at="2026-07-12T12:00:00Z",
    )


def _publish_protected_relationship(binding: ControlBinding) -> ProtectedRelationshipReference:
    relationship = _relationship_body()
    ExternalAssuranceRecordStore(binding, clock=lambda: NOW).write(
        record_class="producer_relationship_evidence",
        record_id=FACTS_RELATIONSHIP_ID,
        revision=1,
        expected_previous_revision=0,
        record=relationship,
        publication_context=_facts_publication_context(binding, relationship),
    )
    return ProtectedRelationshipReference(
        relationship_record_id=FACTS_RELATIONSHIP_ID,
        revision=1,
        canonical_sha256=sha256_hex(canonical_bytes(relationship)),
        relationship_context="requirement_scope_review",
        grade="I2",
        effective_at="2026-07-12T00:00:00Z",
        expires_at="2026-07-13T00:00:00Z",
    )


def _facts_publish_kwargs(
    binding: ControlBinding,
    store: RelationshipEvidenceFactsStore,
    protected: ProtectedRelationshipReference,
    *,
    same_task: bool = False,
    same_session: bool = False,
    same_context_hash: bool = False,
    same_model_family: bool = False,
    visibility: str = "hidden_from_reviewer",
) -> dict[str, object]:
    producer, reviewer = _facts_participants(
        same_task=same_task,
        same_session=same_session,
        same_context_hash=same_context_hash,
        same_model_family=same_model_family,
    )
    base = {
        "relationship_evidence_facts_id": FACTS_RELATIONSHIP_ID,
        "relationship_scope": "requirement_scope",
        "protected_relationship": protected,
        "reviewed_subject": {
            "subject_kind": "assurance_requirement",
            "subject_id": REQUIREMENT_ID,
            "subject_revision": 1,
            "subject_sha256": "3" * 64,
        },
        "producer": producer,
        "reviewer": reviewer,
        "evidence_author_actor_id": ACTOR_ID,
        "producer_conclusions_visibility": visibility,
        "reviewed_at": "2026-07-12T11:55:00Z",
    }
    body = store.derive_record(**base)
    return {
        **base,
        "revision": 1,
        "expected_previous_revision": 0,
        "publication_context": _facts_publication_context(binding, body),
    }


def _record_publication_binding(tmp_path: Path, *, record_id: str, actor_id: str) -> ControlBinding:
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    grant = _external_grant(schemas, record_id=record_id, actor_id=actor_id, risk_ceiling="R3")
    decision = _owner_decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"
    witness = resolver.approved_witness
    manifest = load_store_manifest(control_root, approved_witness=witness)
    code_root = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / ".research-system" / "contracts",
        code_root / ".research-system" / "contracts",
    )
    return ControlBinding(
        code_roots=(code_root.resolve(),),
        control_root=control_root.resolve(),
        project_id=PROJECT_ID,
        schema_root=(code_root / ".research-system" / "schemas").resolve(),
        store_identity=manifest["store_identity"],
        origin_witness=witness,
    )


def _external_record_context(
    binding: ControlBinding,
    *,
    record_class: str,
    record_id: str,
    caller_actor_id: str,
    body: Mapping[str, object],
) -> ExternalRecordPublicationContext:
    return ExternalRecordPublicationContext(
        caller_actor_id=caller_actor_id,
        caller_actor_class="human",
        authority_grant_id=GRANT_ID,
        record_action="create",
        record_class=record_class,
        record_id=record_id,
        revision=1,
        expected_previous_revision=0,
        project_id=PROJECT_ID,
        store_identity=binding.store_identity,
        authority_root=ROOT_ID,
        canonical_sha256=sha256_hex(canonical_bytes(body)),
        task_id=TASK_ID,
        session_id=SESSION_ID,
        relationship_record_id=None,
        required_risk="R3",
        occurred_at="2026-07-12T12:00:00Z",
    )


def _durable_files(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _schema_variant(tmp_path: Path, *, event: bool = False):
    schema_root = tmp_path / "schemas-b"
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas", schema_root)
    schema_path = (
        schema_root / "wp6-3-authority" / "external-assurance-record-grant-activated-event.schema.json"
        if event
        else schema_root / "wp6-3-authority" / "activate-external-assurance-record-grant-command.schema.json"
    )
    schema = json.loads(schema_path.read_bytes())
    schema["$comment"] = "bytes-B"
    schema_path.write_bytes(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return runtime_schema_registry(schema_root)


def _restart_system(control_root: Path, schemas: object):
    unbound = load_store_manifest_unbound(control_root)
    origin_root = control_root.parent / "origin-authority"
    witness_path = origin_witness_path(
        origin_root,
        project_id=PROJECT_ID,
        initial_control_root=Path(str(unbound["control_root"])),
    )
    witness = load_store_origin_witness(witness_path, expected_sha256=sha256_hex(witness_path.read_bytes()))
    manifest = load_store_manifest(control_root, approved_witness=witness)
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        manifest["store_identity"],
        schemas,
        approved_witness=witness,
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

    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker_path = next(marker_root.glob("*.json"))
    marker_files = {marker_path.relative_to(control_root).as_posix(): marker_path.read_bytes()}
    assert _durable_files(control_root) == before_files | marker_files
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
    assert _durable_files(control_root) == before_files | marker_files
    assert len(list(marker_root.glob("*.json"))) == 1
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
    marker_path = next(marker_root.glob("*.json"))
    marker_files = {marker_path.relative_to(control_root).as_posix(): marker_path.read_bytes()}

    restarted_resolver, restarted_ledger, restarted_objects, restarted_service = _restart_system(
        control_root,
        schemas,
    )
    assert _durable_files(control_root) == before_files | marker_files
    assert len(list(marker_root.glob("*.json"))) == 1
    assert restarted_objects.latest_revision("authority_grant", GRANT_ID) is None
    projection = replay(
        restarted_ledger.snapshot().events,
        schema_registry=schemas,
        authority_state_validator=restarted_resolver.validate_replayed_administration_state,
    )
    assert GRANT_ID not in projection["authority_grants"]
    assert restarted_service.submit(command).status == "accepted"


@pytest.mark.integration
def test_recovery_preserves_distinct_later_activation_of_same_target(
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
    first = _activation_command(resolver, schemas, grant, decision)
    second = _activation_command(
        resolver,
        schemas,
        grant,
        decision,
        command_id="cmd_01978abc-6260-7000-8000-000000006260",
        idempotency_key="activate-external-assurance-record-grant-2",
        correlation_id="synthetic-external-record-authority-test-2",
    )
    real_append = ledger._append_scoped_authority_from_validated_submit

    def interrupted(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt("simulated termination before activation append")

    monkeypatch.setattr(ledger, "_append_scoped_authority_from_validated_submit", interrupted)
    with pytest.raises(KeyboardInterrupt, match="before activation append"):
        service.submit(first)
    monkeypatch.setattr(ledger, "_append_scoped_authority_from_validated_submit", real_append)

    second_receipt = service.submit(second)
    assert second_receipt.status == "accepted"
    before_events = ledger.snapshot().events
    before_object_path = next((control_root / "objects" / "authority_grant" / GRANT_ID).glob("00000001-*.json"))
    before_object = before_object_path.read_bytes()
    before_projection = canonical_bytes(
        replay(
            before_events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
    )

    restarted_resolver, restarted_ledger, restarted_objects, restarted_service = _restart_system(
        control_root,
        schemas,
    )
    assert restarted_ledger.snapshot().events == before_events
    assert restarted_objects.read("authority_grant", GRANT_ID, 1) == grant
    restarted_object_path = next((control_root / "objects" / "authority_grant" / GRANT_ID).glob("00000001-*.json"))
    assert restarted_object_path.read_bytes() == before_object
    assert (
        canonical_bytes(
            replay(
                restarted_ledger.snapshot().events,
                schema_registry=schemas,
                authority_state_validator=restarted_resolver.validate_replayed_administration_state,
            )
        )
        == before_projection
    )
    assert restarted_service.submit(second) == second_receipt


@pytest.mark.integration
def test_exact_retry_rejects_same_envelope_against_changed_schema_bytes(
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
    before_events = ledger.snapshot().events

    def interrupted(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt("simulated termination before activation append")

    monkeypatch.setattr(ledger, "_append_scoped_authority_from_validated_submit", interrupted)
    with pytest.raises(KeyboardInterrupt, match="before activation append"):
        service.submit(command)

    schemas_b = _schema_variant(tmp_path)
    witness = resolver.approved_witness
    manifest = load_store_manifest(control_root, approved_witness=witness)
    resolver_b = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        manifest["store_identity"],
        schemas_b,
        approved_witness=witness,
    )
    ledger_b = EventLedger(control_root, PROJECT_ID, schemas_b)
    objects_b = ObjectStore(control_root)
    service_b = CommandService(
        control_root,
        ledger_b,
        objects_b,
        ReceiptStore(control_root),
        schemas_b,
        authority_resolver=resolver_b,
        clock=lambda: NOW,
    )
    before = _durable_files(control_root)
    with pytest.raises(ConflictError, match="recovery marker conflicts"):
        service_b.submit(command)
    assert _durable_files(control_root) == before
    assert ledger_b.snapshot().events == before_events
    assert objects_b.latest_revision("authority_grant", GRANT_ID) is None


@pytest.mark.integration
def test_recovery_rejects_same_command_event_with_different_schema_bytes(
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
    monkeypatch.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
    assert service.submit(command).status == "accepted"

    schemas_b = _schema_variant(tmp_path)
    schema_b = schemas_b.resolve_identity(
        command["schema_id"],
        command["schema_version"],
    )
    event_path = next(
        path
        for path in (control_root / "events").rglob("*.jsonl")
        if command["command_id"] in path.read_text(encoding="utf-8")
    )
    lines = event_path.read_text(encoding="utf-8").splitlines()
    event_index = next(index for index, line in enumerate(lines) if command["command_id"] in line)
    assert event_index == len(lines) - 1
    event = json.loads(lines[event_index])
    event["command_schema_sha256"] = schema_b.sha256
    event.pop("event_hash", None)
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    lines[event_index] = canonical_bytes(event).decode("utf-8")
    event_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    with pytest.raises(IntegrityError, match="schema|identity"):
        _restart_system(control_root, schemas)


@pytest.mark.integration
def test_restart_rejects_marker_after_event_schema_bytes_change_without_mutation(
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

    def interrupted(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt("simulated termination before activation append")

    monkeypatch.setattr(ledger, "_append_scoped_authority_from_validated_submit", interrupted)
    with pytest.raises(KeyboardInterrupt, match="before activation append"):
        service.submit(command)

    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker_path = next(marker_root.glob("*.json"))
    before_files = _durable_files(control_root)
    before_events = ledger.snapshot().events
    assert objects.latest_revision("authority_grant", GRANT_ID) == 1

    schemas_b = _schema_variant(tmp_path, event=True)
    event_binding = schemas.event_binding("AuthorityGrantActivated", command["command_type"])
    assert event_binding is not None
    event_schema = schemas.resolve_identity(event_binding.schema_id, event_binding.schema_version)
    event_schema_b = schemas_b.resolve_identity(event_binding.schema_id, event_binding.schema_version)
    assert event_schema_b.schema_id == event_schema.schema_id
    assert event_schema_b.schema_version == event_schema.schema_version
    assert event_schema_b.sha256 != event_schema.sha256

    with pytest.raises(ConflictError, match="recovery marker conflicts"):
        _restart_system(control_root, schemas_b)

    assert _durable_files(control_root) == before_files
    assert marker_path.exists()
    assert objects.latest_revision("authority_grant", GRANT_ID) == 1
    assert ledger.snapshot().events == before_events

    service.schemas = schemas_b
    with pytest.raises(ConflictError, match="recovery marker conflicts"):
        service.submit(command)
    assert _durable_files(control_root) == before_files


@pytest.mark.integration
def test_truncated_marker_temp_is_quarantined_and_exact_retry_completes(
    tmp_path: Path,
) -> None:
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
    command = _activation_command(resolver, schemas, grant, decision)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker_root.mkdir(parents=True, exist_ok=True)
    (marker_root / f".{command['command_id']}.json.crashed.tmp").write_bytes(b'{"partial":')

    receipt = service.submit(command)
    assert receipt.status == "accepted"
    assert service.submit(command) == receipt
    assert not list(marker_root.glob("*.tmp"))
    assert any(path.name.endswith(".quarantine") for path in marker_root.iterdir())


@pytest.mark.integration
def test_committed_marker_retry_reconstructs_receipt_and_cleans_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    command = _activation_command(resolver, schemas, grant, decision)
    monkeypatch.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
    receipt = service.submit(command)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker_path = next(marker_root.glob("*.json"))
    marker_bytes = marker_path.read_bytes()
    marker_path.with_suffix(".json.tmp").write_bytes(marker_bytes)
    for path in (control_root / "receipts").rglob("*.json"):
        path.unlink()

    restarted_resolver, restarted_ledger, restarted_objects, restarted_service = _restart_system(
        control_root,
        schemas,
    )
    retry = restarted_service.submit(command)
    assert retry == receipt
    assert restarted_ledger.snapshot().events
    assert restarted_objects.read("authority_grant", GRANT_ID, 1) == grant
    assert not list(marker_root.glob("*.json"))
    assert not list(marker_root.glob("*.tmp"))


@pytest.mark.integration
def test_foreign_marker_temp_conflict_preserves_committed_marker_and_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    command = _activation_command(resolver, schemas, grant, decision)
    monkeypatch.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
    receipt = service.submit(command)

    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker_path = next(marker_root.glob("*.json"))
    foreign_bytes = _foreign_activation_marker_bytes(
        service,
        schemas,
        command,
        command_id="cmd_01978abc-6300-7000-8000-000000006302",
        idempotency_key="activate-external-assurance-record-grant-foreign",
        correlation_id="synthetic-external-record-authority-test-foreign",
    )
    foreign_temp = marker_path.with_name(f".{marker_path.name}.foreign.tmp")
    foreign_temp.write_bytes(foreign_bytes)
    for path in (control_root / "receipts").rglob("*.json"):
        path.unlink()
    before = _durable_files(control_root)

    monkeypatch.undo()
    with pytest.raises(ConflictError, match="temporary data conflicts"):
        service.submit(command)

    after_conflict = _durable_files(control_root)
    assert {path: data for path, data in after_conflict.items() if not path.startswith("receipts/")} == {
        path: data for path, data in before.items() if not path.startswith("receipts/")
    }
    assert marker_path.read_bytes() == before[marker_path.relative_to(control_root).as_posix()]
    assert foreign_temp.read_bytes() == foreign_bytes

    foreign_temp.unlink()
    for path in (control_root / "receipts").rglob("*.json"):
        path.unlink()
    assert service.submit(command) == receipt
    assert not marker_path.exists()
    assert not list(marker_root.glob("*.tmp"))


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_cleans_committed_marker_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    assert len(list(marker_root.glob("*.json"))) == 1
    assert service.submit(command) == receipt
    assert not list(marker_root.glob("*.json"))
    assert not list(marker_root.glob("*.tmp"))


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_reconciles_matching_marker_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    marker_path.with_suffix(".json.tmp").write_bytes(marker_path.read_bytes())
    assert service.submit(command) == receipt
    assert not list(marker_root.glob("*.json"))
    assert not list(marker_root.glob("*.tmp"))


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_recovery_activation_payload_equals_the_prepared_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    prepared_payloads: list[dict[str, object]] = []
    real_prepare = service._prepare_scoped_authority_activation

    def capture_prepared_payload(command_value: Command, observed_version: int) -> dict[str, object]:
        prepared = real_prepare(command_value, observed_version)
        prepared_payloads.append(prepared)
        return prepared

    monkeypatch.setattr(service, "_prepare_scoped_authority_activation", capture_prepared_payload)
    monkeypatch.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
    service.submit(command)

    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker = service._load_scoped_activation_marker(next(marker_root.glob("*.json")))
    event = next(event for event in service.ledger.snapshot().events if event["command_id"] == command["command_id"])
    assert prepared_payloads == [service._scoped_activation_event_payload(marker)]
    assert event["payload"] == prepared_payloads[0]


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_classifies_foreign_marker_temp_before_returning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, schemas, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    marker_bytes = marker_path.read_bytes()
    foreign_bytes = _foreign_activation_marker_bytes(service, schemas, command)
    foreign_temp = marker_path.with_name(f".{marker_path.name}.foreign.tmp")
    foreign_temp.write_bytes(foreign_bytes)

    with pytest.raises(ConflictError, match="temporary data conflicts"):
        service.submit(command)
    assert marker_path.read_bytes() == marker_bytes
    assert foreign_temp.read_bytes() == foreign_bytes

    foreign_temp.unlink()
    assert service.submit(command) == receipt
    assert not marker_path.exists()
    assert not list(marker_root.glob("*.tmp"))


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_with_absent_marker_and_no_residue_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    marker_path.unlink()
    assert service.submit(command) == receipt
    assert not marker_path.exists()
    assert not list(marker_root.glob("*.tmp"))


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_with_absent_marker_reconciles_matching_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    marker_bytes = marker_path.read_bytes()
    marker_path.unlink()
    matching_temp = marker_path.with_suffix(".json.tmp")
    matching_temp.write_bytes(marker_bytes)
    assert service.submit(command) == receipt
    assert not marker_path.exists()
    assert not matching_temp.exists()


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_with_absent_marker_preserves_foreign_temp_and_conflicts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, schemas, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    marker_path.unlink()
    foreign_temp = marker_path.with_name(f".{marker_path.name}.foreign.tmp")
    foreign_bytes = _foreign_activation_marker_bytes(service, schemas, command)
    foreign_temp.write_bytes(foreign_bytes)

    with pytest.raises(ConflictError, match="temporary data conflicts"):
        service.submit(command)
    assert not marker_path.exists()
    assert foreign_temp.read_bytes() == foreign_bytes


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
def test_receipt_present_retry_with_absent_marker_classifies_mixed_residue_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
) -> None:
    control_root, schemas, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    marker_bytes = marker_path.read_bytes()
    marker_path.unlink()
    matching_temp = marker_path.with_suffix(".json.tmp")
    matching_temp.write_bytes(marker_bytes)
    foreign_temp = marker_path.with_name(f".{marker_path.name}.foreign.tmp")
    foreign_bytes = _foreign_activation_marker_bytes(service, schemas, command)
    foreign_temp.write_bytes(foreign_bytes)

    with pytest.raises(ConflictError, match="temporary data conflicts"):
        service.submit(command)
    assert not marker_path.exists()
    assert matching_temp.read_bytes() == marker_bytes
    assert foreign_temp.read_bytes() == foreign_bytes


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
@pytest.mark.parametrize("marker_state", ["present", "absent"])
def test_receipt_present_retry_rejects_invalid_marker_temp_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
    marker_state: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    if marker_state == "absent":
        marker_path.unlink()
    invalid_temp = marker_path.with_name(f".{marker_path.name}.invalid.tmp")
    invalid_bytes = b'{"partial":'
    invalid_temp.write_bytes(invalid_bytes)
    before = _durable_files(control_root)

    with pytest.raises(IntegrityError, match="temporary data is invalid"):
        service.submit(command)

    assert _durable_files(control_root) == before
    assert invalid_temp.read_bytes() == invalid_bytes
    assert marker_path.exists() is (marker_state == "present")
    assert service.receipts.load(command["command_id"]) == receipt


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
@pytest.mark.parametrize("marker_state", ["present", "absent"])
def test_receipt_present_retry_revalidates_envelope_project_with_or_without_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
    marker_state: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    if marker_state == "absent":
        marker_path.unlink()
    foreign_project = deepcopy(command)
    foreign_project["project_id"] = FOREIGN_PROJECT_ID
    before = _durable_files(control_root)

    with pytest.raises(ConflictError, match="recovery marker conflicts"):
        service.submit(foreign_project)

    assert _durable_files(control_root) == before
    assert marker_path.exists() is (marker_state == "present")
    assert service.receipts.load(command["command_id"]) == receipt


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
@pytest.mark.parametrize("marker_state", ["present", "absent"])
def test_index_only_retry_rejects_invalid_marker_temp_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
    marker_state: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        receipt = service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    if marker_state == "absent":
        marker_path.unlink()
    invalid_temp = marker_path.with_name(f".{marker_path.name}.invalid.tmp")
    invalid_bytes = b'{"partial":'
    invalid_temp.write_bytes(invalid_bytes)
    receipt_path = control_root / "receipts" / f"{command['command_id']}.json"
    receipt_path.unlink()
    before = _durable_files(control_root)

    with pytest.raises(IntegrityError, match="temporary data is invalid"):
        service.submit(command)

    assert _durable_files(control_root) == before
    assert invalid_temp.read_bytes() == invalid_bytes
    assert marker_path.exists() is (marker_state == "present")
    assert not receipt_path.exists()
    assert receipt.status == "accepted"


@pytest.mark.integration
@pytest.mark.parametrize("activation_kind", ["authority", "external"])
@pytest.mark.parametrize("marker_state", ["present", "absent"])
def test_index_only_retry_revalidates_envelope_project_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    activation_kind: str,
    marker_state: str,
) -> None:
    control_root, _, _, _, service, command = _activation_case(tmp_path, activation_kind)
    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    with monkeypatch.context() as crash:
        crash.setattr(service, "_remove_scoped_activation_marker", lambda _command_id: None)
        service.submit(command)

    marker_path = next(marker_root.glob("*.json"))
    if marker_state == "absent":
        marker_path.unlink()
    receipt_path = control_root / "receipts" / f"{command['command_id']}.json"
    receipt_path.unlink()
    foreign_project = deepcopy(command)
    foreign_project["project_id"] = FOREIGN_PROJECT_ID
    before = _durable_files(control_root)

    with pytest.raises(ConflictError, match="recovery marker conflicts"):
        service.submit(foreign_project)

    assert _durable_files(control_root) == before
    assert marker_path.exists() is (marker_state == "present")
    assert not receipt_path.exists()


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

    marker_root = control_root / "runtime" / "scoped-authority-activation-recovery"
    marker_path = next(marker_root.glob("*.json"))
    marker_files = {marker_path.relative_to(control_root).as_posix(): marker_path.read_bytes()}
    assert _durable_files(control_root) == before_files | marker_files
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
def test_governed_relationship_facts_publish_authorized_round_trip(tmp_path: Path) -> None:
    binding = _facts_fixture(tmp_path)
    protected = _publish_protected_relationship(binding)
    store = RelationshipEvidenceFactsStore(binding, clock=lambda: NOW)
    kwargs = _facts_publish_kwargs(binding, store, protected)

    receipt = store.publish(**kwargs)

    assert receipt.relationship_evidence_facts_id == FACTS_RELATIONSHIP_ID
    path = next(
        (binding.control_root / "runtime" / "relationship-evidence-facts" / FACTS_RELATIONSHIP_ID).glob("*.json")
    )
    body = json.loads(path.read_bytes())
    assert body["relationship_evidence_facts_id"] == FACTS_RELATIONSHIP_ID
    assert path.name == f"00000001-{sha256_hex(canonical_bytes(body))}.json"
    retry = RelationshipEvidenceFactsStore(binding, clock=lambda: NOW).publish(**kwargs)
    assert retry == receipt


@pytest.mark.integration
@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("same_task", "separate task provenance"),
        ("same_session", "independence grade"),
        ("same_context_hash", "independence grade"),
        ("same_model_family", "independence grade"),
        ("visible", "independence grade"),
    ),
)
def test_governed_relationship_facts_rejects_non_independent_or_visible_producer_inputs(
    tmp_path: Path,
    field: str,
    message: str,
) -> None:
    binding = _facts_fixture(tmp_path)
    protected = _publish_protected_relationship(binding)
    store = RelationshipEvidenceFactsStore(binding, clock=lambda: NOW)

    with pytest.raises(SchemaError, match=message):
        _facts_publish_kwargs(
            binding,
            store,
            protected,
            same_task=field == "same_task",
            same_session=field == "same_session",
            same_context_hash=field == "same_context_hash",
            same_model_family=field == "same_model_family",
            visibility="visible_to_reviewer" if field == "visible" else "hidden_from_reviewer",
        )


@pytest.mark.integration
def test_governed_relationship_facts_rejects_protected_actor_mismatch_without_mutation(tmp_path: Path) -> None:
    binding = _facts_fixture(tmp_path)
    protected = _publish_protected_relationship(binding)
    store = RelationshipEvidenceFactsStore(binding, clock=lambda: NOW)
    kwargs = _facts_publish_kwargs(binding, store, protected)
    kwargs["producer"] = replace(kwargs["producer"], actor_id=frozen.ACT_PRODUCER)

    with pytest.raises(SchemaError, match="protected relationship actors"):
        store.publish(**kwargs)

    assert not (binding.control_root / "runtime" / "relationship-evidence-facts" / FACTS_RELATIONSHIP_ID).exists()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("task_id", FACTS_PRODUCER_TASK_ID),
        ("session_id", FACTS_PRODUCER_SESSION_ID),
    ),
)
def test_governed_relationship_facts_rejects_publication_context_reviewer_mismatch_without_mutation(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    binding = _facts_fixture(tmp_path)
    protected = _publish_protected_relationship(binding)
    store = RelationshipEvidenceFactsStore(binding, clock=lambda: NOW)
    kwargs = _facts_publish_kwargs(binding, store, protected)
    kwargs["publication_context"] = replace(kwargs["publication_context"], **{field: value})

    with pytest.raises(SchemaError, match="reviewer provenance"):
        store.publish(**kwargs)

    assert not (binding.control_root / "runtime" / "relationship-evidence-facts" / FACTS_RELATIONSHIP_ID).exists()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("record_class", "record_id"),
    (
        ("active_authority_grant", frozen.OWNER_GRANT_ID),
        ("stephen_owner_acceptance", frozen.OWNER_DECISION_ID),
    ),
)
def test_external_record_writer_keeps_publication_grant_distinct_from_body_r3_grant(
    tmp_path: Path,
    record_class: str,
    record_id: str,
) -> None:
    contract = frozen._load_yaml(frozen.CONTRACT_PATH)
    pack = frozen._proposed_pack(contract)
    _, _, record_store, _ = frozen._external_records(pack, contract)
    body = deepcopy(record_store[record_id])
    binding = _record_publication_binding(tmp_path, record_id=record_id, actor_id=frozen.ACT_OWNER)

    receipt = ExternalAssuranceRecordStore(binding, clock=lambda: NOW).write(
        record_class=record_class,
        record_id=record_id,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=_external_record_context(
            binding,
            record_class=record_class,
            record_id=record_id,
            caller_actor_id=frozen.ACT_OWNER,
            body=body,
        ),
    )

    assert receipt.authority_grant_id == GRANT_ID
    assert body["authority_grant_id"] == frozen.OWNER_GRANT_ID
    assert GRANT_ID != frozen.OWNER_GRANT_ID


@pytest.mark.integration
def test_governed_external_grant_activates_writer_and_exact_retry(tmp_path: Path) -> None:
    binding, _, resolver, _, _, _ = _fixture(tmp_path)
    store = ExternalAssuranceRecordStore(binding, clock=lambda: NOW)
    body = _body()

    receipt = store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=_context(binding, body),
    )
    restarted_store = ExternalAssuranceRecordStore(binding, clock=lambda: NOW)
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
    store = ExternalAssuranceRecordStore(binding, clock=lambda: NOW)
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
    store = ExternalAssuranceRecordStore(binding, clock=lambda: NOW)
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


@pytest.mark.integration
def test_backdated_publication_metadata_cannot_revive_an_expired_grant(tmp_path: Path) -> None:
    binding, _, _, _, _, _ = _fixture(tmp_path)
    store = ExternalAssuranceRecordStore(
        binding,
        clock=lambda: datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    body = _body()

    with pytest.raises(ArsError, match="expired"):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=body,
            publication_context=_context(binding, body),
        )

    assert not (binding.control_root / "objects" / "canonical_actor" / RECORD_ID).exists()


@pytest.mark.integration
def test_future_publication_metadata_cannot_move_authority_evaluation_time(tmp_path: Path) -> None:
    binding, _, _, _, _, _ = _fixture(tmp_path)
    store = ExternalAssuranceRecordStore(binding, clock=lambda: NOW)
    body = _body()
    context = replace(_context(binding, body), occurred_at="2027-07-12T12:00:00Z")

    receipt = store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
        publication_context=context,
    )

    assert receipt.publication_context_sha256 == sha256_hex(canonical_bytes(asdict(context)))
