import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.command import service as service_module
from research_system.command.models import Command
from research_system.command.service import CommandService
from research_system.errors import ArsError, SchemaError
from research_system.evals.retention import EvidenceStoreRegistry
from research_system.schema_registry import cached_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    AUTHORITY_GRANT_ID,
    PROJECT_ID,
    REPO_ROOT,
    control_plane,
    create_task_command,
)


CMD_RESTORE = "cmd_01978abc-5101-7000-8000-000000005101"
TASK_RESTORE = "tsk_01978abc-5102-7000-8000-000000005102"
RESTORE_GRANT = "agr_01978abc-5103-7000-8000-000000005103"
RESTORE_DECISION = "arec_01978abc-5104-7000-8000-000000005104"
RESTORE_ACTIVATION = "cmd_01978abc-5105-7000-8000-000000005105"
RESTORE_REVOKE_DECISION = "arec_01978abc-5106-7000-8000-000000005106"
RESTORE_REVOKE_COMMAND = "cmd_01978abc-5107-7000-8000-000000005107"
RESTORE_ACTOR = ACTORS["actor-a"]
RESTORE_NOW = datetime(2026, 7, 12, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _restore_tests_have_durable_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    import research_system.store.identity as identity_module

    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: True)


def test_restore_preflight_status_is_biconditional_with_failed_predicates():
    from research_system.operations.backups import RestorePreflightResult

    common = {
        "receipt_hash": "a" * 64,
        "ledger_hash": "b" * 64,
        "snapshot_hash": "c" * 64,
        "target_endpoint_ownership_hash": "d" * 64,
        "artefact_manifest_hash": "e" * 64,
        "availability_observations_hash": "f" * 64,
        "registry_hash": "1" * 64,
        "target_root": "C:/synthetic/moved-control",
        "project_id": "prj_01978abc-1000-7000-8000-000000001000",
        "store_identity": "2" * 64,
        "tail_position": 0,
        "tail_hash": "0" * 64,
        "snapshot_id": "snapshot-synthetic-r1",
        "actor_id": "act_01978abc-1002-7000-8000-000000001002",
        "authority_grant_id": "agr_01978abc-1001-7000-8000-000000001001",
        "result_hash": "3" * 64,
    }
    with pytest.raises(ValueError, match="status.*failed predicates"):
        RestorePreflightResult(status="verified", failed_predicates=("tail_mismatch",), **common)
    with pytest.raises(ValueError, match="status.*failed predicates"):
        RestorePreflightResult(status="diagnostic_only", failed_predicates=(), **common)


def test_registered_deletion_topology_includes_backup_and_restore_roots(tmp_path):
    roots = [tmp_path / name for name in ("primary", "runtime", "staging", "temp", "replica", "backup", "restore")]
    registry = EvidenceStoreRegistry(
        store_id="evidence-store",
        registry_hash="a" * 64,
        policy_revision="p0-retention-v1",
        primary_root=roots[0],
        runtime_root=roots[1],
        staging_root=roots[2],
        temp_root=roots[3],
        replicas=(roots[4],),
        backup_roots=(roots[5],),
        restore_roots=(roots[6],),
        permitted_consumers=("eval",),
        retention_policy_ids=("R2:minimized_sensitive_excerpt",),
        verifier_authority_bindings=(("actor", "grant"),),
        unregistered_replicas_prohibited=True,
    )
    assert registry.checked_locations() == tuple(path.resolve(strict=False) for path in roots)

    with pytest.raises(ValueError, match="duplicate locations"):
        replace(registry, restore_roots=(roots[5],)).checked_locations()


def test_moved_restore_is_rechecked_under_writer_lock(tmp_path, monkeypatch):
    from research_system.operations.backups import (
        RestorePreflightResult,
        seal_restore_preflight_result,
    )

    harness = control_plane(tmp_path)
    target_root = harness.service.control_root.resolve(strict=False)
    source_root = tmp_path / "source-control"
    base = RestorePreflightResult(
        status="verified",
        failed_predicates=(),
        receipt_hash="a" * 64,
        ledger_hash="b" * 64,
        snapshot_hash="c" * 64,
        target_endpoint_ownership_hash="d" * 64,
        artefact_manifest_hash="e" * 64,
        availability_observations_hash="f" * 64,
        registry_hash="1" * 64,
        target_root=str(target_root),
        project_id="prj_01978abc-1000-7000-8000-000000001000",
        store_identity="2" * 64,
        tail_position=0,
        tail_hash="0" * 64,
        snapshot_id="snapshot-synthetic-r1",
        actor_id="act_01978abc-1002-7000-8000-000000001002",
        authority_grant_id="agr_01978abc-1001-7000-8000-000000001001",
        result_hash="",
    )
    supplied = seal_restore_preflight_result(base)
    stale = seal_restore_preflight_result(
        replace(
            supplied,
            status="diagnostic_only",
            failed_predicates=("artefact_unavailable",),
            result_hash="",
        )
    )
    harness.service.configure_moved_restore(
        source_root=source_root,
        preflight_result=supplied,
        rechecker=lambda: stale,
    )

    entered = []

    class RecordingLock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            entered.append(True)
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(service_module, "WriterLock", RecordingLock)
    command = create_task_command(CMD_RESTORE, "restore-recheck", TASK_RESTORE, {"title": "moved"})
    with pytest.raises(ArsError, match="restore preflight"):
        harness.service.submit(command)
    assert entered == [True, True]
    assert tuple(harness.ledger.iter_batches()) == ()
    assert harness.receipts.load(CMD_RESTORE) is None
    assert not list((harness.service.control_root / "objects").rglob("*.json"))


def _build_restore_case(tmp_path, *, with_exact_task: bool = False):
    import shutil

    from research_system.canonical import canonical_bytes, sha256_hex
    from research_system.operations.backups import (
        ArtefactBinding,
        BackupReceipt,
        seal_backup_receipt,
    )
    from research_system.projection.replay import replay
    from research_system.schema_registry import runtime_schema_registry

    code_root = tmp_path / "code"
    code_root.mkdir()
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas", code_root / ".research-system" / "schemas")
    shutil.copytree(REPO_ROOT / ".research-system" / "contracts", code_root / ".research-system" / "contracts")
    source = tmp_path / "source"
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    from tests.research_system.factories import authority_bootstrap

    bootstrap = authority_bootstrap(publication_expires_at="2099-07-13T00:00:00Z")
    store_identity = initialize_authority_control_store(
        [code_root],
        source,
        project_id,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=code_root / ".research-system" / "schemas",
    )
    authority = LedgerAuthorityGrantResolver(source, project_id, store_identity, schemas)
    policy_identity = schemas.resolve_identity(
        "ars://core/policy-action/BindRestoredControlStore",
        "1.0.0",
    )
    restore_grant = {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.0.0",
        "authority_grant_id": RESTORE_GRANT,
        "actor_id": RESTORE_ACTOR,
        "allowed_actor_classes": ["human"],
        "allowed_commands": [],
        "allowed_policy_actions": [
            {
                "policy_action_type": "bind_restored_control_store",
                "schema_id": policy_identity.schema_id,
                "schema_version": policy_identity.schema_version,
                "schema_sha256": policy_identity.sha256,
            }
        ],
        "subject_scope": {
            "project_id": project_id,
            "subject": {"kind": "project_store", "id": project_id},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2099-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    context = authority.administration_context()
    grant_schema = schemas.resolve_identity("ars://core/scoped-authority-grant", "2.0.0")
    decision = {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": "1.0.0",
        "record_id": RESTORE_DECISION,
        "revision": 1,
        "project_id": project_id,
        "store_identity": context.store_identity,
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "owner_actor_id": context.owner_actor_id,
        "action": "activate_authority_grant",
        "target_grant_id": RESTORE_GRANT,
        "target_grant_sha256": sha256_hex(canonical_bytes(restore_grant)),
        "target_grant_schema_id": grant_schema.schema_id,
        "target_grant_schema_version": grant_schema.schema_version,
        "target_grant_schema_sha256": grant_schema.sha256,
        "subject_scope": restore_grant["subject_scope"],
        "effective_at": restore_grant["effective_at"],
        "expires_at": restore_grant["expires_at"],
        "one_time_use": True,
        "state": "active",
        "decided_at": "2026-07-12T11:00:00Z",
    }
    objects = ObjectStore(source)
    objects.write("assurance_record", RESTORE_DECISION, 1, decision)
    activation = {
        "command_id": RESTORE_ACTIVATION,
        "command_type": "ActivateAuthorityGrant",
        "schema_id": "ars://core/command/ActivateAuthorityGrant",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": RESTORE_ACTOR,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": context.root_grant_id,
        "target_stream_id": RESTORE_GRANT,
        "expected_stream_version": 0,
        "idempotency_key": "activate-restore-grant",
        "correlation_id": "synthetic-restore-authority",
        "causation_id": None,
        "reason": "activate exact restore verification authority",
        "evidence_refs": [RESTORE_DECISION],
        "project_id": project_id,
        "payload": {
            "project_id": project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": RESTORE_DECISION,
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "new_grant": restore_grant,
            "new_grant_sha256": sha256_hex(canonical_bytes(restore_grant)),
            "new_grant_schema_sha256": grant_schema.sha256,
        },
    }
    service = CommandService(
        source,
        EventLedger(source, project_id, schemas),
        objects,
        ReceiptStore(source),
        schemas,
        authority_resolver=authority,
        clock=lambda: RESTORE_NOW,
    )
    activation_result = service.submit(activation)
    assert activation_result.status == "accepted", activation_result

    target = tmp_path / "target"
    shutil.copytree(source, target)

    ledger = EventLedger(target, project_id, schemas)
    if with_exact_task:
        command = create_task_command(
            CMD_RESTORE,
            "restore-exact-lifecycle",
            TASK_RESTORE,
            {"title": "Exact lifecycle restore history"},
        )
        command_identity = schemas.resolve_identity(
            command["schema_id"],
            command["schema_version"],
        )
        event_identity = schemas.resolve_identity(
            "ars://core/event/TaskCreated",
            "1.0.0",
        )
        ledger.append(
            [
                {
                    "event_type": "TaskCreated",
                    "stream_id": TASK_RESTORE,
                    "command_id": command["command_id"],
                    "command_type": command["command_type"],
                    "command_schema_id": command_identity.schema_id,
                    "command_schema_version": command_identity.schema_version,
                    "command_schema_sha256": command_identity.sha256,
                    "actor_id": command["actor_id"],
                    "authority_grant_id": command["authority_grant_id"],
                    "idempotency_key": command["idempotency_key"],
                    "command_payload_hash": sha256_hex(canonical_bytes(command["payload"])),
                    "correlation_id": command["correlation_id"],
                    "causation_id": command["causation_id"],
                    "schema_id": event_identity.schema_id,
                    "schema_version": event_identity.schema_version,
                    "occurred_at": None,
                    "payload": command["payload"],
                }
            ]
        )
    ledger_snapshot = ledger.snapshot()
    state = replay(
        ledger_snapshot.events,
        schema_registry=schemas,
        authority_state_validator=authority.validate_replayed_administration_state,
    )
    snapshot = {
        "snapshot_id": "snapshot-synthetic-r1",
        "source_position": ledger_snapshot.global_position,
        "source_hash": ledger_snapshot.event_hash,
        "state_hash": sha256_hex(canonical_bytes(state)),
        "replay_start_position": 1,
        "replay_end_position": ledger_snapshot.global_position,
        "schema_versions": ["core-v1"],
        "tool_versions": ["restore-tool-v1"],
    }
    snapshot_path = target / "snapshots" / "accepted.json"
    snapshot_path.write_bytes(canonical_bytes(snapshot))

    actor_id = RESTORE_ACTOR
    authority_grant_id = RESTORE_GRANT
    endpoint = {
        "target_root": str(target.resolve(strict=False)),
        "endpoint_scheme": "local-cli",
        "owner_actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
        "observed_at": "2026-07-11T00:00:00Z",
    }
    endpoint_path = target / "manifests" / "endpoint-ownership.json"
    endpoint_path.write_bytes(canonical_bytes(endpoint))

    artefact_path = target / "external" / "artifact.bin"
    artefact_path.parent.mkdir()
    artefact_path.write_bytes(b"synthetic external artefact\n")
    artefact_hash = sha256_hex(artefact_path.read_bytes())
    observation = {
        "artefact_id": "artifact-synthetic-1",
        "artefact_hash": artefact_hash,
        "availability_status": "available",
        "observed_at": "2026-07-11T00:00:00Z",
        "authority_grant_id": authority_grant_id,
    }
    artefact_manifest = {
        "artefacts": [
            {
                **observation,
                "relative_path": "external/artifact.bin",
            }
        ]
    }
    artefact_manifest_path = target / "manifests" / "external-artifacts.json"
    artefact_manifest_path.write_bytes(canonical_bytes(artefact_manifest))

    registry = EvidenceStoreRegistry(
        store_id="evidence-store",
        registry_hash="9" * 64,
        policy_revision="p0-retention-v1",
        primary_root=target / "evidence-primary",
        runtime_root=target / "evidence-runtime",
        staging_root=target / "evidence-staging",
        temp_root=target / "evidence-temp",
        replicas=(),
        backup_roots=(source,),
        restore_roots=(target,),
        permitted_consumers=("eval",),
        retention_policy_ids=("R2:minimized_sensitive_excerpt",),
        verifier_authority_bindings=((actor_id, authority_grant_id),),
        unregistered_replicas_prohibited=True,
    )
    receipt = BackupReceipt(
        receipt_id="backup-receipt-synthetic-r1",
        receipt_revision=1,
        receipt_hash="",
        project_id=project_id,
        store_identity=store_identity,
        canonical_tail_position=ledger_snapshot.global_position,
        canonical_tail_hash=ledger_snapshot.event_hash,
        snapshot_id=snapshot["snapshot_id"],
        snapshot_hash=sha256_hex(snapshot_path.read_bytes()),
        snapshot_source_position=ledger_snapshot.global_position,
        snapshot_source_hash=ledger_snapshot.event_hash,
        snapshot_state_hash=snapshot["state_hash"],
        replay_start_position=1,
        replay_end_position=ledger_snapshot.global_position,
        schema_versions=("core-v1",),
        tool_versions=("restore-tool-v1",),
        encryption_class="synthetic-none",
        redaction_class="synthetic",
        external_artefact_manifest_hash=sha256_hex(artefact_manifest_path.read_bytes()),
        artefact_bindings=(ArtefactBinding("artifact-synthetic-1", artefact_hash),),
        availability_status="available",
        availability_observation_hash=sha256_hex(canonical_bytes([observation])),
        created_at="2026-07-11T00:00:00Z",
        created_by_actor_id=actor_id,
        verified_at="2026-07-11T00:00:00Z",
        verified_by_actor_id=actor_id,
        verification_authority_grant_id=authority_grant_id,
        destination_class="synthetic-machine-move",
        source_endpoint_scheme="local-cli",
        evidence_registry_hash=registry.registry_hash,
    )
    return {
        "code_root": code_root,
        "source": source,
        "target": target,
        "snapshot_path": snapshot_path,
        "endpoint_path": endpoint_path,
        "artefact_manifest_path": artefact_manifest_path,
        "artefact_path": artefact_path,
        "registry": registry,
        "receipt": seal_backup_receipt(receipt),
        "actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
    }


def _revoke_restore_grant(case) -> None:
    """Exercise governed v2 revocation for the public restore-bind negative."""
    from research_system.schema_registry import runtime_schema_registry

    source = case["source"]
    project_id = case["receipt"].project_id
    store_identity = case["receipt"].store_identity
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    authority = LedgerAuthorityGrantResolver(source, project_id, store_identity, schemas)
    context = authority.administration_context()
    target = authority.scoped_grant_identity(case["authority_grant_id"])
    effective_at = target.effective_at.isoformat().replace("+00:00", "Z")
    expires_at = target.expires_at.isoformat().replace("+00:00", "Z")
    decision = {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": "1.0.0",
        "record_id": RESTORE_REVOKE_DECISION,
        "revision": 1,
        "project_id": project_id,
        "store_identity": context.store_identity,
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "owner_actor_id": context.owner_actor_id,
        "action": "revoke_issued_authority_grant",
        "target_grant_id": target.authority_grant_id,
        "target_grant_sha256": target.authority_grant_sha256,
        "target_grant_schema_id": target.schema_id,
        "target_grant_schema_version": target.schema_version,
        "target_grant_schema_sha256": target.schema_sha256,
        "subject_scope": target.subject_scope.to_dict(),
        "effective_at": effective_at,
        "expires_at": expires_at,
        "one_time_use": True,
        "state": "active",
        "decided_at": RESTORE_NOW.isoformat().replace("+00:00", "Z"),
    }
    reason = "revoke governed restore binding authority"
    ObjectStore(source).write("assurance_record", RESTORE_REVOKE_DECISION, 1, decision)
    command = {
        "command_id": RESTORE_REVOKE_COMMAND,
        "command_type": "RevokeIssuedAuthorityGrant",
        "schema_id": "ars://core/command/RevokeIssuedAuthorityGrant",
        "schema_version": "1.0.0",
        "submitted_at": RESTORE_NOW.isoformat().replace("+00:00", "Z"),
        "actor_id": context.owner_actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": context.root_grant_id,
        "target_stream_id": target.authority_grant_id,
        "expected_stream_version": 1,
        "idempotency_key": "revoke-restore-binding-grant",
        "correlation_id": "revoke-restore-binding-grant",
        "causation_id": None,
        "reason": reason,
        "evidence_refs": [RESTORE_REVOKE_DECISION],
        "project_id": project_id,
        "payload": {
            "project_id": project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": RESTORE_REVOKE_DECISION,
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "target_grant_id": target.authority_grant_id,
            "target_grant_sha256": target.authority_grant_sha256,
            "target_grant_schema_sha256": target.schema_sha256,
            "reason": reason,
        },
    }
    service = CommandService(
        source,
        EventLedger(source, project_id, schemas),
        ObjectStore(source),
        ReceiptStore(source),
        schemas,
        authority_resolver=authority,
        clock=lambda: RESTORE_NOW,
    )
    result = service.submit(command)
    assert result.status == "accepted", result
    assert authority.scoped_grant_identity(target.authority_grant_id).status == "revoked"


def _verify_restore(case, **changes):
    from research_system.operations.backups import verify_restore_before_writer_lease

    values = {
        "target_root": case["target"],
        "receipt": case["receipt"],
        "snapshot_path": case["snapshot_path"],
        "endpoint_ownership_path": case["endpoint_path"],
        "artefact_manifest_path": case["artefact_manifest_path"],
        "registry": case["registry"],
        "actor_id": case["actor_id"],
        "authority_grant_id": case["authority_grant_id"],
        "source_root": case["source"],
        "expected_project_id": case["receipt"].project_id,
        "expected_code_roots": [case["code_root"]],
        "expected_schema_root": case["code_root"] / ".research-system" / "schemas",
    }
    values.update(changes)
    return verify_restore_before_writer_lease(**values)


@pytest.mark.parametrize(
    "mutation",
    [
        "code_roots",
        "schema_root",
        "code_root_file",
        "schema_root_file",
        "target_code_root_file",
        "target_schema_root_file",
        "bootstrap",
        "authority_grant",
        "ledger",
        "target_manifest",
        "target_bootstrap",
        "target_grant",
        "target_ledger",
    ],
)
def test_restore_finalization_rechecks_source_snapshot_before_manifest_replace(tmp_path, monkeypatch, mutation):
    import research_system.store.identity as identity_module
    from research_system.operations.backups import finalize_verified_restore_binding
    from research_system.schema_registry import runtime_schema_registry

    case = _build_restore_case(tmp_path)
    supplied = _verify_restore(case)

    def mutate_source() -> None:
        if mutation == "target_manifest":
            target_manifest_path = case["target"] / "manifests" / "store-identity.json"
            target_manifest = json.loads(target_manifest_path.read_text(encoding="utf-8"))
            target_manifest["endpoint_scheme"] = "foreign"
            target_manifest["manifest_hash"] = sha256_hex(
                canonical_bytes({key: value for key, value in target_manifest.items() if key != "manifest_hash"})
            )
            target_manifest_path.write_bytes(canonical_bytes(target_manifest))
            return
        if mutation.startswith("target_"):
            target = case["target"]
            mutation_kind = mutation.removeprefix("target_")
        else:
            target = case["source"]
            mutation_kind = mutation
        if mutation_kind == "code_root_file":
            (case["code_root"] / "restore-binding-code-mutation.py").write_bytes(b"mutated code root\n")
        elif mutation_kind == "schema_root_file":
            (case["code_root"] / ".research-system" / "schemas" / "restore-binding-schema-mutation.json").write_bytes(
                b'{"mutated":true}'
            )
        elif mutation_kind in {"code_roots", "schema_root"}:
            manifest = json.loads((target / "manifests" / "store-identity.json").read_text(encoding="utf-8"))
            if mutation_kind == "code_roots":
                foreign_root = tmp_path / "foreign-code"
                foreign_root.mkdir(exist_ok=True)
                manifest["code_roots"] = [str(foreign_root.resolve())]
            else:
                manifest["schema_root"] = str((tmp_path / "foreign-schema").resolve())
            manifest["manifest_hash"] = sha256_hex(
                canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
            )
            (target / "manifests" / "store-identity.json").write_bytes(canonical_bytes(manifest))
        elif mutation_kind == "bootstrap":
            bootstrap_path = target / "manifests" / "authority-bootstrap.json"
            bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
            bootstrap["owner_actor_id"] = ACTORS["actor-b"]
            bootstrap_path.write_bytes(canonical_bytes(bootstrap))
        elif mutation_kind in {"authority_grant", "grant"}:
            grant_path = next((target / "objects" / "authority_grant" / RESTORE_GRANT).glob("*.json"))
            grant = json.loads(grant_path.read_text(encoding="utf-8"))
            grant["actor_id"] = ACTORS["actor-b"]
            grant_path.write_bytes(canonical_bytes(grant))
        else:
            event_path = next((target / "events").rglob("*.jsonl"))
            event_path.write_bytes(
                event_path.read_bytes().replace(
                    b'"occurred_at":null',
                    b'"occurred_at":"2026-07-12T12:00:01Z"',
                    1,
                )
            )

    monkeypatch.setattr(identity_module, "_before_restore_manifest_replace", mutate_source, raising=False)
    with pytest.raises(ArsError, match="snapshot"):
        finalize_verified_restore_binding(
            target_root=case["target"],
            source_root=case["source"],
            supplied=supplied,
            current=supplied,
            project_id=case["receipt"].project_id,
            actor_id=case["actor_id"],
            authority_grant_id=case["authority_grant_id"],
            schema_registry=runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas"),
            now=RESTORE_NOW,
            expected_project_id=case["receipt"].project_id,
            expected_code_roots=[case["code_root"]],
            expected_schema_root=case["code_root"] / ".research-system" / "schemas",
        )
    assert json.loads((case["target"] / "manifests" / "store-identity.json").read_text(encoding="utf-8"))[
        "control_root"
    ] == str(case["source"].resolve())


def test_proposed_verify_restore_is_not_an_active_scoped_authority_identity():
    from research_system.authority import ScopedAuthorityGrant, validate_scoped_grant_activation
    from research_system.schema_registry import runtime_schema_registry

    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    command = schemas.resolve_identity("ars://core/command/VerifyRestore", "1.0.0")
    grant = ScopedAuthorityGrant.from_dict(
        {
            "schema_id": "ars://core/scoped-authority-grant",
            "schema_version": "2.0.0",
            "authority_grant_id": "agr_01978abc-1005-7000-8000-000000001005",
            "actor_id": ACTORS["actor-a"],
            "allowed_actor_classes": ["human"],
            "allowed_commands": [
                {
                    "command_type": "VerifyRestore",
                    "schema_id": command.schema_id,
                    "schema_version": command.schema_version,
                    "schema_sha256": command.sha256,
                }
            ],
            "allowed_policy_actions": [],
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": "project_store", "id": PROJECT_ID},
            },
            "risk_ceiling": "R2",
            "effective_at": "2026-07-12T00:00:00Z",
            "expires_at": "2099-07-13T00:00:00Z",
            "delegable": False,
            "revoked": False,
        }
    )
    with pytest.raises(ArsError, match="inactive"):
        validate_scoped_grant_activation(grant, schemas, owner_actor_id=ACTORS["actor-a"])


def test_restore_preflight_independently_verifies_moved_store_and_artifacts(tmp_path):
    case = _build_restore_case(tmp_path)
    result = _verify_restore(case)
    assert result.status == "verified", result.failed_predicates
    assert result.failed_predicates == ()
    assert result.target_root == str(case["target"].resolve(strict=False))
    assert result.receipt_hash == case["receipt"].receipt_hash
    assert result.registry_hash == case["registry"].registry_hash


def test_restore_preflight_replays_exact_lifecycle_history(tmp_path):
    case = _build_restore_case(tmp_path, with_exact_task=True)

    result = _verify_restore(case)

    assert result.status == "verified"
    assert result.failed_predicates == ()
    assert result.tail_position == 4


@pytest.mark.parametrize("mutation", ["forged", "revoked", "wrong_scope"])
def test_restore_preflight_requires_current_replayed_restore_grant(tmp_path, mutation):
    case = _build_restore_case(tmp_path)
    grant_directory = case["source"] / "objects" / "authority_grant" / case["authority_grant_id"]
    grant_path = next(grant_directory.glob("*.json"))
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    if mutation == "forged":
        grant["actor_id"] = "act_01978abc-1010-7000-8000-000000001010"
    elif mutation == "revoked":
        grant["revoked"] = True
    else:
        grant["subject_scope"]["project_id"] = "prj_01978abc-1000-7000-8000-000000001099"
    grant_path.unlink()
    digest = sha256_hex(canonical_bytes(grant))
    (grant_directory / f"00000001-{digest}.json").write_bytes(canonical_bytes(grant))

    result = _verify_restore(case)

    assert result.status == "diagnostic_only"
    assert "source_snapshot_mismatch" in result.failed_predicates


@pytest.mark.parametrize(
    ("mutation", "predicate"),
    [
        ("wrong_store", "store_identity_mismatch"),
        ("wrong_project", "project_identity_mismatch"),
        ("wrong_tail", "ledger_tail_mismatch"),
        ("wrong_snapshot", "snapshot_binding_mismatch"),
        ("wrong_schema", "schema_version_unsupported"),
        ("wrong_endpoint", "endpoint_authority_mismatch"),
        ("wrong_actor", "verification_authority_mismatch"),
        ("wrong_grant", "verification_authority_mismatch"),
        ("artefact_absent", "artefact_unavailable"),
        ("artefact_changed", "artefact_unavailable"),
        ("stale_availability", "availability_observation_mismatch"),
        ("wrong_registry", "registry_hash_mismatch"),
    ],
)
def test_restore_preflight_fails_closed_on_bound_evidence_drift(tmp_path, mutation, predicate):
    from research_system.operations.backups import seal_backup_receipt

    case = _build_restore_case(tmp_path)
    receipt = case["receipt"]
    registry = case["registry"]
    actor_id = case["actor_id"]
    authority_grant_id = case["authority_grant_id"]
    if mutation == "wrong_store":
        receipt = seal_backup_receipt(replace(receipt, store_identity="8" * 64, receipt_hash=""))
    elif mutation == "wrong_project":
        receipt = seal_backup_receipt(
            replace(
                receipt,
                project_id="prj_01978abc-1000-7000-8000-000000001099",
                receipt_hash="",
            )
        )
    elif mutation == "wrong_tail":
        receipt = seal_backup_receipt(replace(receipt, canonical_tail_position=1, receipt_hash=""))
    elif mutation == "wrong_snapshot":
        receipt = seal_backup_receipt(replace(receipt, snapshot_hash="7" * 64, receipt_hash=""))
    elif mutation == "wrong_schema":
        receipt = seal_backup_receipt(replace(receipt, schema_versions=("core-v2",), receipt_hash=""))
    elif mutation == "wrong_endpoint":
        case["endpoint_path"].write_text("{}", encoding="utf-8")
    elif mutation == "wrong_actor":
        actor_id = "act_01978abc-1002-7000-8000-000000001003"
    elif mutation == "wrong_grant":
        authority_grant_id = "agr_01978abc-1001-7000-8000-000000001003"
    elif mutation == "artefact_absent":
        case["artefact_path"].unlink()
    elif mutation == "artefact_changed":
        case["artefact_path"].write_bytes(b"changed")
    elif mutation == "stale_availability":
        manifest = json.loads(case["artefact_manifest_path"].read_text(encoding="utf-8"))
        manifest["artefacts"][0]["observed_at"] = "2026-07-10T00:00:00Z"
        from research_system.canonical import canonical_bytes

        case["artefact_manifest_path"].write_bytes(canonical_bytes(manifest))
    elif mutation == "wrong_registry":
        registry = replace(registry, registry_hash="6" * 64)

    result = _verify_restore(
        case,
        receipt=receipt,
        registry=registry,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
    )
    assert result.status == "diagnostic_only"
    assert predicate in result.failed_predicates


def _moved_service(case):
    from research_system.command.service import CommandService
    from research_system.authority import LedgerAuthorityGrantResolver
    from research_system.schema_registry import runtime_schema_registry
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore
    from research_system.store.receipts import ReceiptStore

    root = case["target"]
    schemas = runtime_schema_registry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas")
    return CommandService(
        root,
        EventLedger(root, case["receipt"].project_id, schemas),
        ObjectStore(root),
        ReceiptStore(root),
        schemas,
        authority_resolver=LedgerAuthorityGrantResolver(
            case["source"],
            case["receipt"].project_id,
            case["receipt"].store_identity,
            schemas,
        ),
    )


def test_real_command_service_accepts_only_current_verified_moved_restore(tmp_path):
    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
        expected_project_id=case["receipt"].project_id,
        expected_code_roots=[case["code_root"]],
        expected_schema_root=case["code_root"] / ".research-system" / "schemas",
    )
    before_batches = tuple(service.ledger.iter_batches())
    command = create_task_command(
        CMD_RESTORE,
        "verified-move",
        TASK_RESTORE,
        {"title": "verified moved store"},
    )
    command["authority_grant_id"] = case["authority_grant_id"]
    receipt = service.submit(command)
    assert receipt.status == "accepted"
    assert len(tuple(service.ledger.iter_batches())) == len(before_batches) + 1

    from research_system.config import ControlBinding
    from research_system.command.service import CommandService
    from research_system.store.objects import ObjectStore
    from research_system.store.receipts import ReceiptStore
    from research_system.store.identity import load_store_manifest

    manifest = load_store_manifest(case["target"])
    assert manifest["control_root"] == str(case["target"].resolve())
    config = tmp_path / "binding.json"
    config.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(case["code_root"].resolve())],
                "control_root": str(case["target"].resolve()),
                "project_id": case["receipt"].project_id,
                "schema_root": str((case["code_root"] / ".research-system" / "schemas").resolve()),
                "store_identity": case["receipt"].store_identity,
            }
        )
    )
    binding = ControlBinding.load(config)
    restarted = CommandService(
        binding.control_root,
        EventLedger(binding.control_root, binding.project_id, service.schemas),
        ObjectStore(binding.control_root),
        ReceiptStore(binding.control_root),
        service.schemas,
        authority_resolver=LedgerAuthorityGrantResolver(
            binding.control_root,
            binding.project_id,
            binding.store_identity,
            service.schemas,
        ),
    )
    assert restarted.submit(command).status == "accepted"


def test_moved_restore_command_conflict_does_not_bind_store(tmp_path):
    from research_system.store.identity import load_restore_binding_evidence

    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
        expected_project_id=case["receipt"].project_id,
        expected_code_roots=[case["code_root"]],
        expected_schema_root=case["code_root"] / ".research-system" / "schemas",
    )
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    before_batches = tuple(service.ledger.iter_batches())
    command = create_task_command(CMD_RESTORE, "conflict-before-restore-bind", TASK_RESTORE, {"title": "conflict"})
    command["authority_grant_id"] = case["authority_grant_id"]
    command["expected_stream_version"] = 1

    receipt = service.submit(command)

    assert receipt.status == "conflict"
    assert manifest_path.read_bytes() == before_manifest
    assert tuple(service.ledger.iter_batches()) == before_batches
    assert load_restore_binding_evidence(case["target"]) is None


def test_moved_restore_command_specific_rejection_does_not_bind_store(tmp_path):
    from research_system.store.identity import load_restore_binding_evidence

    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
        expected_project_id=case["receipt"].project_id,
        expected_code_roots=[case["code_root"]],
        expected_schema_root=case["code_root"] / ".research-system" / "schemas",
    )
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    before_batches = tuple(service.ledger.iter_batches())
    command = create_task_command(CMD_RESTORE, "rejected-before-restore-bind", TASK_RESTORE, {"title": "rejected"})
    command["authority_grant_id"] = case["authority_grant_id"]
    command["payload"]["definition"]["revision"] = 2

    receipt = service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "invalid_task_revision"
    assert manifest_path.read_bytes() == before_manifest
    assert tuple(service.ledger.iter_batches()) == before_batches
    assert load_restore_binding_evidence(case["target"]) is None


@pytest.mark.parametrize("binding_field", ["code_roots", "schema_root"])
def test_moved_restore_rejects_binding_changes_under_writer_lock(tmp_path, binding_field):
    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
        expected_project_id=case["receipt"].project_id,
        expected_code_roots=[case["code_root"]],
        expected_schema_root=case["code_root"] / ".research-system" / "schemas",
    )
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if binding_field == "code_roots":
        foreign = tmp_path / "foreign-code"
        foreign.mkdir()
        manifest["code_roots"] = [str(foreign.resolve())]
    else:
        manifest["schema_binding_version"] = "1.0.0"
        manifest["schema_root"] = str((tmp_path / "foreign-schema").resolve())
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    attempted_bytes = manifest_path.read_bytes()
    before_batches = tuple(service.ledger.iter_batches())
    before_objects = sorted(
        (path.relative_to(case["target"]).as_posix(), path.read_bytes())
        for path in (case["target"] / "objects").rglob("*.json")
    )

    command = create_task_command(
        CMD_RESTORE,
        f"changed-{binding_field}",
        TASK_RESTORE,
        {"title": f"changed {binding_field}"},
    )
    command["authority_grant_id"] = case["authority_grant_id"]
    with pytest.raises(ArsError, match="restore preflight"):
        service.submit(command)
    assert manifest_path.read_bytes() == attempted_bytes
    assert tuple(service.ledger.iter_batches()) == before_batches
    assert service.receipts.load(CMD_RESTORE) is None
    assert (
        sorted(
            (path.relative_to(case["target"]).as_posix(), path.read_bytes())
            for path in (case["target"] / "objects").rglob("*.json")
        )
        == before_objects
    )


def test_real_command_service_rejects_changed_artifact_under_writer_lock(tmp_path, monkeypatch):
    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
        expected_project_id=case["receipt"].project_id,
        expected_code_roots=[case["code_root"]],
        expected_schema_root=case["code_root"] / ".research-system" / "schemas",
    )
    before_batches = tuple(service.ledger.iter_batches())
    before_objects = sorted(
        (path.relative_to(case["target"]).as_posix(), path.read_bytes())
        for path in (case["target"] / "objects").rglob("*.json")
    )
    case["artefact_path"].unlink()

    entered = []

    class RecordingLock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            entered.append(True)
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(service_module, "WriterLock", RecordingLock)
    command = create_task_command(
        CMD_RESTORE,
        "changed-artifact",
        TASK_RESTORE,
        {"title": "changed artefact"},
    )
    command["authority_grant_id"] = case["authority_grant_id"]
    with pytest.raises(ArsError, match="restore preflight"):
        service.submit(command)
    assert entered == [True, True]
    assert tuple(service.ledger.iter_batches()) == before_batches
    assert service.receipts.load(CMD_RESTORE) is None
    assert (
        sorted(
            (path.relative_to(case["target"]).as_posix(), path.read_bytes())
            for path in (case["target"] / "objects").rglob("*.json")
        )
        == before_objects
    )


def test_s014_executor_crosses_real_command_service_seam(monkeypatch):
    from research_system.command.service import CommandService
    from research_system.evals.executors.release_tranche import execute_s014

    original = CommandService.submit
    calls = []

    def counted(self, envelope):
        calls.append(envelope)
        return original(self, envelope)

    monkeypatch.setattr(CommandService, "submit", counted)
    payload = {
        "contract": "restore_preflight_registered_topology",
        "action": {"operation": "verify_restore_machine_move"},
    }
    assert execute_s014("known_bad", payload)["restore_preflight_status"] == "diagnostic_only"
    assert execute_s014("known_good", payload)["restore_preflight_status"] == "verified"
    assert len(calls) == 2
    assert all(command["schema_id"] == "ars://core/command/CreateTask" for command in calls)
    assert all(command["payload"]["new_task_id"] == command["target_stream_id"] for command in calls)


def test_backup_receipt_schema_binds_complete_w8_record(tmp_path):
    from dataclasses import asdict

    from research_system.schema_registry import SchemaRegistry

    case = _build_restore_case(tmp_path)
    schemas = SchemaRegistry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas")
    schemas.validate(
        "ars://operations/backup-receipt",
        json.loads(json.dumps(asdict(case["receipt"]))),
    )


TASK_A = "tsk_01978abc-5201-7000-8000-000000005201"
TASK_B = "tsk_01978abc-5202-7000-8000-000000005202"
TASK_C = "tsk_01978abc-5203-7000-8000-000000005203"
TASK_D = "tsk_01978abc-5204-7000-8000-000000005204"
CMD_A = "cmd_01978abc-5211-7000-8000-000000005211"
CMD_B = "cmd_01978abc-5212-7000-8000-000000005212"
CMD_C = "cmd_01978abc-5213-7000-8000-000000005213"
CMD_D = "cmd_01978abc-5214-7000-8000-000000005214"
CMD_AB = "cmd_01978abc-5221-7000-8000-000000005221"
CMD_BC = "cmd_01978abc-5222-7000-8000-000000005222"
CMD_CA = "cmd_01978abc-5223-7000-8000-000000005223"
CMD_DA = "cmd_01978abc-5224-7000-8000-000000005224"


def _create_revision(
    harness,
    command_id,
    task_id,
    title,
    *,
    task_type="research_task",
    continuing_consumers=("audit",),
):
    """Seed one authentic pre-cutover generic Task revision.

    These supersession fixtures predate the accepted rich ``TaskDefinition``.
    Keep their legacy type and consumer contract in generic history instead of
    adding those retired fields to the current exact CreateTask payload.
    """
    payload = {
        "title": title,
        "task_type": task_type,
        "continuing_consumers": list(continuing_consumers),
    }
    command = create_task_command(
        command_id,
        f"create-{title}",
        task_id,
        payload,
    )
    command["schema_id"] = "ars://core/command"
    command["payload"] = payload
    command.pop("project_id")
    inert_schemas = cached_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    command_schema = inert_schemas.resolve_identity(
        "ars://core/command",
        "1.0.0",
    )
    harness.objects.write("task", task_id, 1, payload)
    return EventLedger(
        harness.service.control_root,
        PROJECT_ID,
        inert_schemas,
    ).append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": task_id,
                "command_id": command_id,
                "command_type": "CreateTask",
                "command_schema_id": command_schema.schema_id,
                "command_schema_version": command_schema.schema_version,
                "command_schema_sha256": command_schema.sha256,
                "actor_id": ACTORS["actor-a"],
                "authority_grant_id": AUTHORITY_GRANT_ID,
                "idempotency_key": command["idempotency_key"],
                "command_payload_hash": Command(command).payload_hash,
                "correlation_id": command["correlation_id"],
                "causation_id": command["causation_id"],
                "schema_id": "ars://core/event",
                "schema_version": "1.0.0",
                "occurred_at": None,
                "payload": payload,
            }
        ]
    )


def _supersede_command(command_id, source_id, replacement_id, replacement_revision=1):
    payload = {
        "task_id": source_id,
        "replacement_task_id": replacement_id,
        "replacement_task_revision": replacement_revision,
        "continuing_consumer_dispositions": ["audit"],
        "lineage_reason": "Replace the exact source Task revision.",
    }
    command = create_task_command(
        command_id,
        f"supersede-{command_id}",
        source_id,
        payload,
    )
    command["command_type"] = "SupersedeTask"
    command["schema_id"] = "ars://core/command/SupersedeTask"
    command["expected_stream_version"] = 1
    command["payload"] = payload
    return command


def _store_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "receipts" not in path.parts and "runtime" not in path.parts
    }


def test_pre_cutover_generic_task_history_remains_replayable_and_resolvable(
    tmp_path,
):
    from research_system.projection.replay import replay

    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    events = tuple(harness.ledger.iter_events())

    assert len(events) == 1
    assert events[0]["schema_id"] == "ars://core/event"
    assert events[0]["command_schema_id"] == "ars://core/command"
    assert harness.objects.read("task", TASK_A, 1) == {
        "title": "A",
        "task_type": "research_task",
        "continuing_consumers": ["audit"],
    }
    state = replay(
        events,
        schema_registry=harness.service.schemas,
    )["streams"][TASK_A]
    assert state["status"] == "draft"


def test_exact_task_amendment_rejects_pre_cutover_generic_source(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    definition = create_task_command(
        "cmd_01978abc-5298-7000-8000-000000005298",
        "replacement-definition",
        TASK_A,
        {"title": "Modern replacement"},
    )["payload"]["definition"]
    definition["revision"] = 2
    definition["title"] = "Modern replacement"
    definition["objective"] = "Complete Modern replacement"
    definition.pop("content_sha256")
    definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
    command = create_task_command(
        "cmd_01978abc-5299-7000-8000-000000005299",
        "reject-legacy-amendment",
        TASK_A,
        {"title": "Modern replacement"},
    )
    command.update(
        {
            "command_type": "AmendTask",
            "schema_id": "ars://core/command/AmendTask",
            "expected_stream_version": 1,
            "payload": {
                "task_id": TASK_A,
                "prior_revision": 1,
                "new_revision": 2,
                "replacement_definition": definition,
                "changed_fields": ["title", "objective"],
                "rationale": "Do not silently convert a generic legacy Task.",
                "effective_boundary": "before redispatch",
                "authority_evidence_refs": [AUTHORITY_GRANT_ID],
            },
        }
    )

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "source_task_definition_incompatible"
    assert len(tuple(harness.ledger.iter_events())) == 1
    assert harness.objects.latest_revision("task", TASK_A) == 1


def test_s015_nonterminal_source_cycle_rejected_atomically_and_idempotently(tmp_path):
    from research_system.projection.replay import replay

    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(harness, CMD_B, TASK_B, "B")
    _create_revision(harness, CMD_C, TASK_C, "C")
    assert harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_B)).status == "accepted"
    assert harness.service.submit(_supersede_command(CMD_BC, TASK_B, TASK_C)).status == "accepted"

    before_bytes = _store_bytes(harness.service.control_root)
    before_projection = replay(
        harness.ledger.iter_events(),
        schema_registry=harness.service.schemas,
    )
    before_snapshot = harness.ledger.snapshot()
    command = _supersede_command(CMD_CA, TASK_C, TASK_A)
    first = harness.service.submit(command)
    second = harness.service.submit(command)

    assert first == second
    assert first.status == "rejected"
    assert first.reason_code == "supersession_cycle"
    assert first.explanation
    assert first.unmet_preconditions == ("supersession_cycle",)
    assert first.observed_stream_version == 1
    assert _store_bytes(harness.service.control_root) == before_bytes
    assert (
        replay(
            harness.ledger.iter_events(),
            schema_registry=harness.service.schemas,
        )
        == before_projection
    )
    after_snapshot = harness.ledger.snapshot()
    assert (after_snapshot.global_position, after_snapshot.event_hash) == (
        before_snapshot.global_position,
        before_snapshot.event_hash,
    )
    assert len(list(harness.receipts.receipts_root.glob(f"{CMD_CA}.json"))) == 1
    assert before_projection["streams"][TASK_C]["status"] != "superseded"


def test_supersession_rejects_terminal_replacement_after_cycle_check(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(harness, CMD_B, TASK_B, "B")
    _create_revision(harness, CMD_D, TASK_D, "D")
    assert harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_B)).status == "accepted"

    before = tuple(event.copy() for event in harness.ledger.iter_events())
    rejected = harness.service.submit(_supersede_command(CMD_DA, TASK_D, TASK_A))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "replacement_revision_terminal"
    assert rejected.unmet_preconditions == ("replacement_revision_terminal",)
    assert tuple(event.copy() for event in harness.ledger.iter_events()) == before
    assert len(list(harness.receipts.receipts_root.glob(f"{CMD_DA}.json"))) == 1


def test_legacy_supersession_accepts_same_task_higher_revision_and_preserves_history(
    tmp_path,
):
    from research_system.projection.replay import replay

    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    harness.objects.write(
        "task",
        TASK_A,
        2,
        {
            "title": "A revision 2",
            "task_type": "research_task",
            "continuing_consumers": ["audit"],
        },
    )
    command = _supersede_command(CMD_AB, TASK_A, TASK_A, 2)
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted"
    events = tuple(harness.ledger.iter_events())
    assert events[0]["schema_id"] == "ars://core/event"
    state = replay(
        events,
        schema_registry=harness.service.schemas,
    )["streams"][TASK_A]
    assert state["status"] == "draft"
    assert state["current_revision"] == 2
    assert state["revision_history"]["1"]["status"] == "superseded"
    event = events[-1]
    assert event["event_type"] == "TaskSuperseded"
    assert event["schema_id"] == "ars://core/event/TaskSuperseded"
    assert event["payload"]["task_id"] == TASK_A
    assert event["payload"]["replacement_task_revision"] == 2
    assert event["payload"]["continuing_consumer_dispositions"] == ["audit"]
    assert event["payload"]["lineage_reason"]


def test_supersession_rejects_identical_node_and_terminal_source(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(harness, CMD_B, TASK_B, "B")
    _create_revision(harness, CMD_C, TASK_C, "C")
    self_cycle = harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_A))
    assert self_cycle.status == "rejected"
    assert self_cycle.reason_code == "supersession_cycle"

    accepted = harness.service.submit(_supersede_command(CMD_BC, TASK_B, TASK_C))
    assert accepted.status == "accepted"
    terminal = _supersede_command(CMD_CA, TASK_B, TASK_A)
    terminal["expected_stream_version"] = 2
    rejected = harness.service.submit(terminal)
    assert rejected.status == "rejected"
    assert rejected.reason_code == "source_revision_terminal"


def test_supersession_rejects_missing_replacement_revision(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    missing = harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_B))
    assert missing.reason_code == "replacement_revision_missing"


def test_legacy_supersession_rejects_stale_replacement_revision(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(harness, CMD_B, TASK_B, "B")
    harness.objects.write(
        "task",
        TASK_B,
        2,
        {
            "title": "B revision 2",
            "task_type": "research_task",
            "continuing_consumers": ["audit"],
        },
    )
    stale = harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_B, 2))
    assert stale.reason_code == "replacement_revision_stale"


def test_legacy_supersession_rejects_type_incompatible_replacement(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(
        harness,
        CMD_B,
        TASK_B,
        "B",
        task_type="review_task",
    )
    incompatible = harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_B))
    assert incompatible.reason_code == "replacement_revision_incompatible"


def test_exact_supersession_rejects_caller_supplied_lineage(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(harness, CMD_B, TASK_B, "B")

    caller_lineage = _supersede_command(CMD_AB, TASK_A, TASK_B)
    caller_lineage["payload"]["lineage"] = [{"task_id": TASK_A, "revision": 1}]
    with pytest.raises(SchemaError, match="lineage"):
        harness.service.submit(caller_lineage)
    assert len(tuple(harness.ledger.iter_events())) == 2


def test_legacy_supersession_rejects_continuing_consumer_drift(tmp_path):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    _create_revision(harness, CMD_B, TASK_B, "B")

    consumers = _supersede_command(CMD_BC, TASK_A, TASK_B)
    consumers["payload"]["continuing_consumer_dispositions"] = ["claim"]
    assert harness.service.submit(consumers).reason_code == "continuing_consumers_mismatch"


def test_s015_executor_crosses_real_command_service_cycle_seam(monkeypatch):
    from research_system.command.service import CommandService
    from research_system.evals.executors.release_tranche import execute_s015

    original = CommandService.submit
    calls = []

    def counted(self, envelope):
        calls.append(envelope)
        return original(self, envelope)

    monkeypatch.setattr(CommandService, "submit", counted)
    payload = {
        "contract": "revision_qualified_supersession_cycle_rejection",
        "action": {"operation": "supersede_task"},
    }
    observed = execute_s015("known_good", payload)
    assert observed["rejection_reason"] == "supersession_cycle"
    assert observed["authority_unchanged"] is True
    assert len(calls) == 6
    creates = [command for command in calls if command["command_type"] == "CreateTask"]
    assert len(creates) == 3
    assert all(command["schema_id"] == "ars://core/command/CreateTask" for command in creates)
    supersedes = [command for command in calls if command["command_type"] == "SupersedeTask"]
    assert all(command["schema_id"] == "ars://core/command/SupersedeTask" for command in supersedes)


def test_supersession_graph_and_rejected_receipt_io_stay_inside_writer_lock(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    _create_revision(harness, CMD_A, TASK_A, "A")
    active = False
    original_lock = service_module.WriterLock
    original_prepare = harness.service._prepare_supersession
    original_load = harness.receipts.load
    original_write = harness.receipts.write

    class TrackingLock:
        def __init__(self, *args, **kwargs):
            self.inner = original_lock(*args, **kwargs)

        def __enter__(self):
            nonlocal active
            value = self.inner.__enter__()
            active = True
            return value

        def __exit__(self, *args):
            nonlocal active
            active = False
            return self.inner.__exit__(*args)

    def prepare(*args, **kwargs):
        assert active is True
        return original_prepare(*args, **kwargs)

    def load(command_id):
        if command_id == CMD_AB:
            assert active is True
        return original_load(command_id)

    def write(receipt):
        if receipt.command_id == CMD_AB:
            assert active is True
        return original_write(receipt)

    monkeypatch.setattr(service_module, "WriterLock", TrackingLock)
    monkeypatch.setattr(harness.service, "_prepare_supersession", prepare)
    monkeypatch.setattr(harness.receipts, "load", load)
    monkeypatch.setattr(harness.receipts, "write", write)
    rejected = harness.service.submit(_supersede_command(CMD_AB, TASK_A, TASK_A))
    assert rejected.reason_code == "supersession_cycle"
    assert active is False


@pytest.mark.parametrize(
    "field",
    [
        "capability",
        "risk_tier",
        "independence_grade",
        "authority_grant_id",
        "root_bindings_hash",
        "tool_permissions_hash",
        "sensitivity_class",
        "policy_revision",
        "evaluation_revision",
    ],
)
def test_s016_route_request_binds_every_hard_requirement(field):
    from research_system.routing.models import RouteRequest

    request = RouteRequest(
        request_id="rrq_" + "1" * 32,
        task_id=TASK_A,
        task_revision=1,
        assurance_requirement_id="asr_" + "2" * 32,
        assurance_requirement_hash="a" * 64,
        context_candidate_id="ctx_" + "3" * 32,
        context_hash="b" * 64,
        capability="independent_r3_review",
        risk_tier="R3",
        independence_grade="I3",
        authority_grant_id="agr_01978abc-1001-7000-8000-000000001001",
        root_bindings_hash="c" * 64,
        tool_permissions_hash="d" * 64,
        sensitivity_class="internal",
        policy_revision="routing-policy-v1",
        evaluation_revision="gate5-eval-v1",
    )
    assert getattr(request, field)


def _s016_payload():
    return {
        "contract": "r3_provider_outage_preserves_requirements",
        "action": {
            "operation": "route_r3_review",
            "required_risk": "R3",
            "required_independence": "I3",
            "required_family_count": 2,
            "provider_status": "unavailable",
        },
    }


def test_s016_executor_proves_distinct_preissue_and_issue_time_outage_flows(
    monkeypatch,
):
    from research_system.evals.executors.release_tranche import execute_s016
    from research_system.operations import coordinator as coordinator_module
    from research_system.routing.engine import PreparedDispatch

    calls = []
    original = coordinator_module.issue_prepared_dispatch

    def counted(prepared, adapter, operations, command_service):
        calls.append(prepared)
        return original(prepared, adapter, operations, command_service)

    monkeypatch.setattr(coordinator_module, "issue_prepared_dispatch", counted)
    observed = execute_s016("known_good", _s016_payload())

    assert len(calls) == 1
    assert isinstance(calls[0], PreparedDispatch)
    assert calls[0].route["kind"] == "selected"
    assert observed["pre_dispatch_failure"] == "no_eligible_route"
    assert observed["candidate_rejection_codes"] == [
        "provider_unavailable",
        "capability_insufficient",
        "independence_unavailable",
    ]
    assert observed["pre_dispatch_prepared_count"] == 0
    assert observed["issue_time_prepared_count"] == 1
    assert observed["pre_dispatch_issued_command_count"] == 0
    assert observed["issue_time_issued_command_count"] == 1
    assert observed["fallback_issued"] is False
    assert observed["provider_receipt_status"] == "incomplete"
    assert observed["provider_failure_code"] == "provider_unavailable"
    assert observed["provider_output_present"] is False
    assert observed["bindings_unchanged"] is True
    assert observed["canonical_dispatch_events"] == 0
    assert observed["canonical_acceptance_events"] == 0
    assert observed["task_accepted"] is False


def test_s016_forbidden_events_change_derived_evidence(monkeypatch):
    from research_system.evals.executors import release_tranche as module

    trace_type = getattr(module, "_S016CommandTrace")
    original = trace_type.submit

    def inject_forbidden(self, command):
        receipt = original(self, command)
        if command.get("event_type") == "ProviderOutageRecorded":
            self.events.append(
                {
                    "event_type": "FallbackDispatchIssued",
                    "profile_id": "same-family-fallback",
                }
            )
            self.events.append({"event_type": "TaskAccepted"})
            self.task_state = "accepted"
        return receipt

    monkeypatch.setattr(trace_type, "submit", inject_forbidden)
    observed = module.execute_s016("known_good", _s016_payload())

    assert observed["fallback_issued"] is True
    assert observed["canonical_dispatch_events"] == 1
    assert observed["canonical_acceptance_events"] == 1
    assert observed["task_accepted"] is True
