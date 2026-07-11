import json
from dataclasses import replace
from pathlib import Path

import pytest

from research_system.command import service as service_module
from research_system.errors import ArsError
from research_system.evals.retention import EvidenceStoreRegistry
from tests.research_system.factories import control_plane, create_task_command


CMD_RESTORE = "cmd_01978abc-5101-7000-8000-000000005101"
TASK_RESTORE = "tsk_01978abc-5102-7000-8000-000000005102"


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
    roots = [tmp_path / name for name in (
        "primary", "runtime", "staging", "temp", "replica", "backup", "restore"
    )]
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


def test_moved_restore_is_rechecked_before_writer_lock(tmp_path, monkeypatch):
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

    class LockMustNotBeEntered:
        def __init__(self, *args, **kwargs):
            raise AssertionError("writer lock entered before restore recheck")

    monkeypatch.setattr(service_module, "WriterLock", LockMustNotBeEntered)
    command = create_task_command(CMD_RESTORE, "restore-recheck", TASK_RESTORE, {"title": "moved"})
    with pytest.raises(ArsError, match="restore preflight"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()
    assert harness.receipts.load(CMD_RESTORE) is None
    assert not list((harness.service.control_root / "objects").rglob("*.json"))

def _build_restore_case(tmp_path):
    import shutil

    from research_system.canonical import canonical_bytes, sha256_hex
    from research_system.operations.backups import (
        ArtefactBinding,
        BackupReceipt,
        seal_backup_receipt,
    )
    from research_system.projection.replay import replay
    from research_system.store.identity import initialize_control_store

    code_root = tmp_path / "code"
    code_root.mkdir()
    source = tmp_path / "source"
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    store_identity = initialize_control_store([code_root], source, project_id)
    target = tmp_path / "target"
    shutil.copytree(source, target)

    state = replay(())
    snapshot = {
        "snapshot_id": "snapshot-synthetic-r1",
        "source_position": 0,
        "source_hash": "0" * 64,
        "state_hash": sha256_hex(canonical_bytes(state)),
        "replay_start_position": 1,
        "replay_end_position": 0,
        "schema_versions": ["core-v1"],
        "tool_versions": ["restore-tool-v1"],
    }
    snapshot_path = target / "snapshots" / "accepted.json"
    snapshot_path.write_bytes(canonical_bytes(snapshot))

    actor_id = "act_01978abc-1002-7000-8000-000000001002"
    authority_grant_id = "agr_01978abc-1001-7000-8000-000000001001"
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
        canonical_tail_position=0,
        canonical_tail_hash="0" * 64,
        snapshot_id=snapshot["snapshot_id"],
        snapshot_hash=sha256_hex(snapshot_path.read_bytes()),
        snapshot_source_position=0,
        snapshot_source_hash="0" * 64,
        snapshot_state_hash=snapshot["state_hash"],
        replay_start_position=1,
        replay_end_position=0,
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
    }
    values.update(changes)
    return verify_restore_before_writer_lease(**values)


def test_restore_preflight_independently_verifies_moved_store_and_artifacts(tmp_path):
    case = _build_restore_case(tmp_path)
    result = _verify_restore(case)
    assert result.status == "verified"
    assert result.failed_predicates == ()
    assert result.target_root == str(case["target"].resolve(strict=False))
    assert result.receipt_hash == case["receipt"].receipt_hash
    assert result.registry_hash == case["registry"].registry_hash


@pytest.mark.parametrize(
    ("mutation", "predicate"),
    [
        ("wrong_store", "store_identity_mismatch"),
        ("wrong_project", "project_identity_mismatch"),
        ("wrong_tail", "ledger_tail_mismatch"),
        ("wrong_snapshot", "snapshot_binding_mismatch"),
        ("wrong_schema", "schema_version_unsupported"),
        ("wrong_endpoint", "endpoint_authority_mismatch"),
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
    if mutation == "wrong_store":
        receipt = seal_backup_receipt(replace(receipt, store_identity="8" * 64, receipt_hash=""))
    elif mutation == "wrong_project":
        receipt = seal_backup_receipt(replace(
            receipt,
            project_id="prj_01978abc-1000-7000-8000-000000001099",
            receipt_hash="",
        ))
    elif mutation == "wrong_tail":
        receipt = seal_backup_receipt(replace(receipt, canonical_tail_position=1, receipt_hash=""))
    elif mutation == "wrong_snapshot":
        receipt = seal_backup_receipt(replace(receipt, snapshot_hash="7" * 64, receipt_hash=""))
    elif mutation == "wrong_schema":
        receipt = seal_backup_receipt(replace(receipt, schema_versions=("core-v2",), receipt_hash=""))
    elif mutation == "wrong_endpoint":
        case["endpoint_path"].write_text("{}", encoding="utf-8")
    elif mutation == "artefact_absent":
        case["artefact_path"].unlink()
    elif mutation == "artefact_changed":
        case["artefact_path"].write_bytes(b"changed")
    elif mutation == "stale_availability":
        manifest = json.loads(
            case["artefact_manifest_path"].read_text(encoding="utf-8")
        )
        manifest["artefacts"][0]["observed_at"] = "2026-07-10T00:00:00Z"
        from research_system.canonical import canonical_bytes

        case["artefact_manifest_path"].write_bytes(canonical_bytes(manifest))
    elif mutation == "wrong_registry":
        registry = replace(registry, registry_hash="6" * 64)

    result = _verify_restore(case, receipt=receipt, registry=registry)
    assert result.status == "diagnostic_only"
    assert predicate in result.failed_predicates

def _moved_service(case):
    from research_system.command.service import CommandService
    from research_system.schema_registry import SchemaRegistry
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore
    from research_system.store.receipts import ReceiptStore

    root = case["target"]
    schemas = SchemaRegistry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas")
    return CommandService(
        root,
        EventLedger(root, case["receipt"].project_id),
        ObjectStore(root),
        ReceiptStore(root),
        schemas,
    )


def test_real_command_service_accepts_only_current_verified_moved_restore(tmp_path):
    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
    )
    command = create_task_command(
        CMD_RESTORE,
        "verified-move",
        TASK_RESTORE,
        {"title": "verified moved store"},
    )
    receipt = service.submit(command)
    assert receipt.status == "accepted"
    assert len(tuple(service.ledger.iter_batches())) == 1


def test_real_command_service_rejects_changed_artifact_before_writer_lock(
    tmp_path, monkeypatch
):
    case = _build_restore_case(tmp_path)
    service = _moved_service(case)
    supplied = _verify_restore(case)
    service.configure_moved_restore(
        source_root=case["source"],
        preflight_result=supplied,
        rechecker=lambda: _verify_restore(case),
    )
    case["artefact_path"].unlink()

    class LockMustNotBeEntered:
        def __init__(self, *args, **kwargs):
            raise AssertionError("writer lock entered after artefact drift")

    monkeypatch.setattr(service_module, "WriterLock", LockMustNotBeEntered)
    command = create_task_command(
        CMD_RESTORE,
        "changed-artifact",
        TASK_RESTORE,
        {"title": "changed artefact"},
    )
    with pytest.raises(ArsError, match="restore preflight"):
        service.submit(command)
    assert tuple(service.ledger.iter_batches()) == ()
    assert service.receipts.load(CMD_RESTORE) is None
    assert not list((case["target"] / "objects").rglob("*.json"))

def test_s014_executor_crosses_real_command_service_seam(monkeypatch):
    from research_system.command.service import CommandService
    from research_system.evals.executors.release_tranche import execute_s014

    original = CommandService.submit
    calls = 0

    def counted(self, envelope):
        nonlocal calls
        calls += 1
        return original(self, envelope)

    monkeypatch.setattr(CommandService, "submit", counted)
    payload = {
        "contract": "restore_preflight_registered_topology",
        "action": {"operation": "verify_restore_machine_move"},
    }
    assert execute_s014("known_bad", payload)["restore_preflight_status"] == "diagnostic_only"
    assert execute_s014("known_good", payload)["restore_preflight_status"] == "verified"
    assert calls == 2

def test_backup_receipt_schema_binds_complete_w8_record(tmp_path):
    from dataclasses import asdict

    from research_system.schema_registry import SchemaRegistry

    case = _build_restore_case(tmp_path)
    schemas = SchemaRegistry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas")
    schemas.validate(
        "ars://operations/backup-receipt",
        json.loads(json.dumps(asdict(case["receipt"]))),
    )