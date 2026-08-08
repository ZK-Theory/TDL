from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

import research_system.operations.backups as backups_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.evals.retention import EvidenceStoreRegistry
from research_system.operations.backups import (
    BackupArtefactInput,
    BackupMaterializer,
)
from research_system.projection.replay import replay
from research_system.schema_registry import bundled_runtime_schema_registry
from research_system.store.identity import initialize_control_store
from research_system.store.ledger import EventLedger


PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
COMMAND_ID = "cmd_019fcdfa-7700-7000-8000-000000000001"
ACTOR_ID = "act_01978abc-1002-7000-8000-000000001002"
GRANT_ID = "agr_019fcdfa-7825-7248-837d-247d023751b3"
RECEIPT_ID = "bkr_019fcdfa-7700-7000-8000-000000000001"
SNAPSHOT_ID = "snp_019fcdfa-7700-7000-8000-000000000001"
ARTEFACT_ID = "art_019fcdfa-7700-7000-8000-000000000001"


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _case(tmp_path: Path) -> dict[str, object]:
    code_root = tmp_path / "code"
    origin_root = tmp_path / "origin"
    source_root = tmp_path / "Source"
    destination_root = tmp_path / "Backup"
    stage_root = tmp_path / f".{destination_root.name}.{COMMAND_ID}.stage"
    for path in (code_root, origin_root):
        path.mkdir()
    store = initialize_control_store(
        [code_root],
        source_root,
        PROJECT_ID,
        origin_authority_root=origin_root,
    )
    (source_root / "objects" / "stable.bin").write_bytes(b"stable object\n")
    (source_root / "runtime" / "writer.lock").write_bytes(b"live writer residue\n")
    (source_root / "runtime" / "pending.tmp").write_bytes(b"mutable temporary\n")

    artefact_path = tmp_path / "external" / "result.bin"
    artefact_path.parent.mkdir()
    artefact_path.write_bytes(b"external result\n")
    artefact_hash = sha256_hex(artefact_path.read_bytes())
    registry = EvidenceStoreRegistry(
        store_id="wp64-evidence-store",
        registry_hash="9" * 64,
        policy_revision="wp64-r1",
        primary_root=source_root,
        runtime_root=tmp_path / "registry-runtime",
        staging_root=stage_root,
        temp_root=tmp_path / "registry-temp",
        replicas=(),
        permitted_consumers=("restore-verifier",),
        retention_policy_ids=("wp64-retention",),
        verifier_authority_bindings=((ACTOR_ID, GRANT_ID),),
        unregistered_replicas_prohibited=True,
        backup_roots=(destination_root,),
    )
    materializer = BackupMaterializer(
        command_id=COMMAND_ID,
        source_root=source_root,
        destination_root=destination_root,
        stage_root=stage_root,
        receipt_id=RECEIPT_ID,
        receipt_revision=1,
        registry=registry,
        artefacts=(
            BackupArtefactInput(
                artefact_id=ARTEFACT_ID,
                source_path=artefact_path,
                content_sha256=artefact_hash,
                availability="available",
                availability_evidence_refs=("owner-observation:wp64-a8",),
                observed_at="2026-08-05T10:00:00Z",
            ),
        ),
        verified_at="2026-08-05T10:01:00Z",
        verified_by_actor_id=ACTOR_ID,
        verification_authority_grant_id=GRANT_ID,
        approved_witness=store.witness,
        approved_witness_path=store.witness_path,
    )
    schemas = bundled_runtime_schema_registry()
    ledger = EventLedger(source_root, PROJECT_ID, schemas)
    before = ledger.snapshot()
    payload = materializer.derive_event_payload(
        snapshot_id=SNAPSHOT_ID,
        destination_class="offline-local-copy",
        schema_versions=("core-1.0.0",),
        tool_versions=("tdl-backup-1.0.0",),
        encryption_class="owner-approved-none",
        redaction_class="owner-approved-complete",
        ledger_snapshot=before,
    )
    envelope = {
        "command_id": COMMAND_ID,
        "command_type": "CreateBackup",
        "schema_id": "ars://core/command/CreateBackup",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-05T10:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": GRANT_ID,
        "target_stream_id": PROJECT_ID,
        "expected_stream_version": 0,
        "idempotency_key": "wp64-backup-1",
        "correlation_id": "wp64-backup-1",
        "causation_id": None,
        "reason": "Create the owner-authorized WP6.4 backup.",
        "evidence_refs": ["owner-observation:wp64-a8"],
        "payload": payload,
        "project_id": PROJECT_ID,
    }
    return {
        "source": source_root,
        "destination": destination_root,
        "stage": stage_root,
        "materializer": materializer,
        "ledger": ledger,
        "before": before,
        "command": Command(envelope),
        "schemas": schemas,
    }


def _append_backup_created(case: dict[str, object]) -> dict[str, object]:
    command = case["command"]
    ledger = case["ledger"]
    schemas = case["schemas"]
    before = case["before"]
    assert isinstance(command, Command)
    assert isinstance(ledger, EventLedger)
    command_identity = schemas.resolve_identity(
        "ars://core/command/CreateBackup",
        "1.0.0",
    )
    event_identity = schemas.resolve_identity(
        "ars://core/event/BackupCreated",
        "1.0.0",
    )
    ledger.append(
        [
            {
                "event_type": "BackupCreated",
                "stream_id": PROJECT_ID,
                "command_id": command.command_id,
                "command_type": "CreateBackup",
                "command_schema_id": command_identity.schema_id,
                "command_schema_version": command_identity.schema_version,
                "command_schema_sha256": command_identity.sha256,
                "actor_id": ACTOR_ID,
                "authority_grant_id": GRANT_ID,
                "idempotency_key": command.idempotency_key,
                "command_payload_hash": command.payload_hash,
                "correlation_id": command.envelope["correlation_id"],
                "causation_id": None,
                "schema_id": event_identity.schema_id,
                "schema_version": event_identity.schema_version,
                "occurred_at": None,
                "payload": command.envelope["payload"],
            }
        ],
        snapshot=before,
    )
    return ledger.snapshot().events[-1]


def test_prepare_is_invisible_and_excludes_mutable_writer_residue(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    preparation = materializer.prepare(case["command"], case["before"])

    destination = case["destination"]
    stage = case["stage"]
    assert isinstance(destination, Path)
    assert isinstance(stage, Path)
    assert not destination.exists()
    assert stage.is_dir()
    assert not (stage / "manifests" / "backup-receipt.json").exists()
    assert list((stage / "runtime").iterdir()) == []
    assert (stage / "objects" / "stable.bin").read_bytes() == b"stable object\n"
    assert preparation.event_payload == case["command"].envelope["payload"]
    assert preparation.preparation_sha256 == sha256_hex((stage / "manifests" / "backup-preparation.json").read_bytes())


def test_materializer_requires_canonical_receipt_and_artefact_ids(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)

    with pytest.raises(ArsError, match="receipt identity must be canonical"):
        replace(materializer, receipt_id="receipt-1")

    escaped = replace(
        materializer.artefacts[0],
        artefact_id="../../outside",
    )
    with pytest.raises(ArsError, match="artefact identity must be canonical"):
        replace(materializer, artefacts=(escaped,))

    assert not (tmp_path / "outside").exists()


def test_materializer_requires_exact_registry_roles_and_closed_replica_policy(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    registry = materializer.registry
    assert isinstance(registry, EvidenceStoreRegistry)
    source = case["source"]
    destination = case["destination"]
    stage = case["stage"]
    assert isinstance(source, Path)
    assert isinstance(destination, Path)
    assert isinstance(stage, Path)

    permuted = replace(
        registry,
        primary_root=destination,
        staging_root=source,
        backup_roots=(stage,),
    )
    with pytest.raises(ArsError, match="registry roles"):
        replace(materializer, registry=permuted)

    open_registry = replace(registry, unregistered_replicas_prohibited=False)
    with pytest.raises(ArsError, match="prohibit unregistered replicas"):
        replace(materializer, registry=open_registry)


def test_prepare_retry_rejects_live_source_drift(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    source = case["source"]
    destination = case["destination"]
    stage = case["stage"]
    assert isinstance(source, Path)
    assert isinstance(destination, Path)
    assert isinstance(stage, Path)

    (source / "objects" / "stable.bin").write_bytes(b"changed after preparation\n")

    with pytest.raises(IntegrityError, match="Source changed"):
        materializer.prepare(case["command"], case["before"])

    assert stage.is_dir()
    assert not destination.exists()


def test_prepare_retry_rejects_coherently_rebound_staged_artefact(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    original_command = case["command"]
    assert isinstance(materializer, BackupMaterializer)
    assert isinstance(original_command, Command)
    materializer.prepare(original_command, case["before"])
    stage = case["stage"]
    destination = case["destination"]
    assert isinstance(stage, Path)
    assert isinstance(destination, Path)

    changed = b"coherently rebound staged artefact\n"
    changed_hash = sha256_hex(changed)
    artefact_path = stage / "external-artefacts" / ARTEFACT_ID
    artefact_path.write_bytes(changed)
    preparation_path = stage / "manifests" / "backup-preparation.json"
    preparation = json.loads(preparation_path.read_bytes())
    for binding in preparation["file_bindings"]:
        if binding["relative_path"] == f"external-artefacts/{ARTEFACT_ID}":
            binding["raw_sha256"] = changed_hash
    preparation["event_payload"]["external_artefacts"][0]["content_sha256"] = changed_hash
    preparation_path.write_bytes(canonical_bytes(preparation))

    rebound_payload = materializer.derive_event_payload(
        snapshot_id=SNAPSHOT_ID,
        destination_class="offline-local-copy",
        schema_versions=("core-1.0.0",),
        tool_versions=("tdl-backup-1.0.0",),
        encryption_class="owner-approved-none",
        redaction_class="owner-approved-complete",
        ledger_snapshot=case["before"],
    )
    rebound_envelope = json.loads(json.dumps(original_command.envelope))
    rebound_envelope["payload"] = rebound_payload
    rebound_command = Command(rebound_envelope)

    with pytest.raises(IntegrityError, match="freshly derived candidate"):
        materializer.prepare(rebound_command, case["before"])

    assert stage.is_dir()
    assert not destination.exists()


def test_durable_exclusive_removes_partial_final_after_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "exclusive.bin"
    original_write = backups_module.os.write
    wrote_partial = False

    def partial_then_fail(descriptor: int, data: object) -> int:
        nonlocal wrote_partial
        if not wrote_partial:
            wrote_partial = True
            return original_write(descriptor, memoryview(data)[:3])
        raise OSError("injected write failure")

    monkeypatch.setattr(backups_module.os, "write", partial_then_fail)
    with pytest.raises(OSError, match="injected write failure"):
        backups_module._write_durable_exclusive(target, b"complete bytes\n", "test file")

    assert not target.exists()
    monkeypatch.setattr(backups_module.os, "write", original_write)
    backups_module._write_durable_exclusive(target, b"complete bytes\n", "test file")
    assert target.read_bytes() == b"complete bytes\n"


def test_durable_exclusive_removes_exact_final_after_file_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "exclusive.bin"
    original_fsync = backups_module.os.fsync
    fail_next = True

    def fail_file_fsync_once(descriptor: int) -> None:
        nonlocal fail_next
        if fail_next:
            fail_next = False
            raise OSError("injected file fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(backups_module.os, "fsync", fail_file_fsync_once)
    with pytest.raises(OSError, match="injected file fsync failure"):
        backups_module._write_durable_exclusive(target, b"complete bytes\n", "test file")

    assert not target.exists()
    backups_module._write_durable_exclusive(target, b"complete bytes\n", "test file")
    assert target.read_bytes() == b"complete bytes\n"


def test_prepare_cleans_owned_stage_after_preparation_file_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    original_writer = backups_module._write_durable_exclusive
    original_fsync = backups_module.os.fsync
    failed = False

    def fail_preparation_once(path: Path, data: bytes, label: str) -> None:
        nonlocal failed
        if label != "preparation record" or failed:
            original_writer(path, data, label)
            return
        failed = True
        fail_next = True

        def fail_file_fsync_once(descriptor: int) -> None:
            nonlocal fail_next
            if fail_next:
                fail_next = False
                raise OSError("injected preparation fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(backups_module.os, "fsync", fail_file_fsync_once)
        try:
            original_writer(path, data, label)
        finally:
            monkeypatch.setattr(backups_module.os, "fsync", original_fsync)

    monkeypatch.setattr(backups_module, "_write_durable_exclusive", fail_preparation_once)
    before = case["ledger"].snapshot()

    with pytest.raises(OSError, match="injected preparation fsync failure"):
        materializer.prepare(case["command"], case["before"])

    assert not case["stage"].exists()
    assert not case["destination"].exists()
    after_failure = case["ledger"].snapshot()
    assert (after_failure.global_position, after_failure.event_hash) == (
        before.global_position,
        before.event_hash,
    )

    materializer.prepare(case["command"], case["before"])
    assert case["stage"].is_dir()


@pytest.mark.parametrize(
    "unsafe_snapshot_id",
    ["../../escaped-snapshot", "foo:bar", "CON", "NUL.txt", "trailing.", "trailing "],
)
def test_prepare_rejects_unsafe_snapshot_id_before_any_write(
    tmp_path: Path,
    unsafe_snapshot_id: str,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    original = case["command"]
    assert isinstance(original, Command)
    payload = json.loads(json.dumps(original.envelope["payload"]))
    payload["snapshot_id"] = unsafe_snapshot_id
    state = replay(case["before"].events, schema_registry=case["schemas"])
    escaped_snapshot = {
        "snapshot_id": payload["snapshot_id"],
        "source_position": payload["canonical_tail_position"],
        "source_hash": payload["canonical_tail_sha256"],
        "state_hash": sha256_hex(canonical_bytes(state)),
        "replay_start_position": payload["replay_start_position"],
        "replay_end_position": payload["replay_end_position"],
        "schema_versions": payload["schema_versions"],
        "tool_versions": payload["tool_versions"],
    }
    payload["snapshot_sha256"] = sha256_hex(canonical_bytes(escaped_snapshot))
    command = Command({**original.envelope, "payload": payload})
    case["schemas"].validate_active(
        command.envelope["schema_id"],
        command.envelope,
        schema_version=command.envelope["schema_version"],
    )

    with pytest.raises(ArsError, match="snapshot identity"):
        materializer.prepare(command, case["before"])

    assert not case["stage"].exists()
    assert not case["destination"].exists()
    assert not (tmp_path / "escaped-snapshot.json").exists()


def test_prepare_flushes_stage_parent_before_event_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    stage = case["stage"]
    assert isinstance(stage, Path)
    calls: list[Path] = []
    original_flush = backups_module._fsync_directory

    def tracked_flush(path: Path) -> bool:
        result = original_flush(path)
        calls.append(path.resolve(strict=True))
        return result

    monkeypatch.setattr(backups_module, "_fsync_directory", tracked_flush)
    before = case["ledger"].snapshot()

    materializer.prepare(case["command"], case["before"])

    after = case["ledger"].snapshot()
    assert stage.resolve(strict=True) in calls
    assert stage.parent.resolve(strict=True) in calls
    assert calls.index(stage.parent.resolve(strict=True)) > calls.index(stage.resolve(strict=True))
    assert (after.global_position, after.event_hash) == (before.global_position, before.event_hash)


def test_materialize_publishes_only_after_exact_committed_event(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)

    receipt = materializer.materialize(case["command"], committed)

    destination = case["destination"]
    stage = case["stage"]
    assert isinstance(destination, Path)
    assert isinstance(stage, Path)
    assert destination.is_dir()
    assert not stage.exists()
    receipt_path = destination / "manifests" / "backup-receipt.json"
    assert receipt_path.read_bytes() == canonical_bytes(json.loads(json.dumps(asdict(receipt))))
    receipt_value = json.loads(receipt_path.read_bytes())
    case["schemas"].validate("ars://operations/backup-receipt", receipt_value)


def test_event_only_retry_recovers_from_receipt_file_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)
    committed_tail = case["ledger"].snapshot()
    original_writer = backups_module._write_durable_exclusive
    original_fsync = backups_module.os.fsync
    failed = False

    def fail_receipt_once(path: Path, data: bytes, label: str) -> None:
        nonlocal failed
        if label != "receipt" or failed:
            original_writer(path, data, label)
            return
        failed = True
        fail_next = True

        def fail_file_fsync_once(descriptor: int) -> None:
            nonlocal fail_next
            if fail_next:
                fail_next = False
                raise OSError("injected receipt fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(backups_module.os, "fsync", fail_file_fsync_once)
        try:
            original_writer(path, data, label)
        finally:
            monkeypatch.setattr(backups_module.os, "fsync", original_fsync)

    monkeypatch.setattr(backups_module, "_write_durable_exclusive", fail_receipt_once)

    with pytest.raises(OSError, match="injected receipt fsync failure"):
        materializer.materialize(case["command"], committed)

    stage = case["stage"]
    destination = case["destination"]
    assert isinstance(stage, Path)
    assert isinstance(destination, Path)
    assert stage.is_dir()
    assert not (stage / "manifests" / "backup-receipt.json").exists()
    assert not destination.exists()

    materializer.materialize(case["command"], committed)

    assert destination.is_dir()
    assert not stage.exists()
    after_retry = case["ledger"].snapshot()
    assert (after_retry.global_position, after_retry.event_hash) == (
        committed_tail.global_position,
        committed_tail.event_hash,
    )


def test_retry_reestablishes_exact_stage_receipt_durability_before_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)
    original_rename = backups_module._rename_directory_no_replace
    monkeypatch.setattr(
        backups_module,
        "_rename_directory_no_replace",
        lambda _source, _destination: (_ for _ in ()).throw(RuntimeError("interrupt before rename")),
    )
    with pytest.raises(RuntimeError, match="interrupt before rename"):
        materializer.materialize(case["command"], committed)
    stage = case["stage"]
    assert isinstance(stage, Path)
    assert (stage / "manifests" / "backup-receipt.json").is_file()

    calls: list[Path] = []
    file_calls: list[Path] = []
    original_flush = backups_module._fsync_directory
    original_file_flush = backups_module._fsync_physical_regular_file

    def tracked_flush(path: Path) -> bool:
        result = original_flush(path)
        calls.append(path.resolve(strict=True))
        return result

    def tracked_file_flush(path: Path, label: str) -> None:
        original_file_flush(path, label)
        file_calls.append(path.resolve(strict=True))

    def checked_rename(source: Path, destination: Path) -> None:
        assert (stage / "manifests" / "backup-receipt.json").resolve(strict=True) in file_calls
        assert (stage / "manifests").resolve(strict=True) in calls
        assert stage.resolve(strict=True) in calls
        assert stage.parent.resolve(strict=True) in calls
        original_rename(source, destination)

    monkeypatch.setattr(backups_module, "_fsync_directory", tracked_flush)
    monkeypatch.setattr(backups_module, "_fsync_physical_regular_file", tracked_file_flush)
    monkeypatch.setattr(backups_module, "_rename_directory_no_replace", checked_rename)

    materializer.materialize(case["command"], committed)

    assert case["destination"].is_dir()


def test_retry_reestablishes_exact_destination_durability_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)
    first = materializer.materialize(case["command"], committed)
    destination = case["destination"]
    assert isinstance(destination, Path)
    calls: list[Path] = []
    file_calls: list[Path] = []
    original_flush = backups_module._fsync_directory
    original_file_flush = backups_module._fsync_physical_regular_file

    def tracked_flush(path: Path) -> bool:
        result = original_flush(path)
        calls.append(path.resolve(strict=True))
        return result

    def tracked_file_flush(path: Path, label: str) -> None:
        original_file_flush(path, label)
        file_calls.append(path.resolve(strict=True))

    monkeypatch.setattr(backups_module, "_fsync_directory", tracked_flush)
    monkeypatch.setattr(backups_module, "_fsync_physical_regular_file", tracked_file_flush)

    retried = materializer.materialize(case["command"], committed)

    assert retried == first
    assert (destination / "manifests" / "backup-receipt.json").resolve(strict=True) in file_calls
    assert destination.resolve(strict=True) in calls
    assert destination.parent.resolve(strict=True) in calls


def test_committed_event_rejects_self_authenticated_snapshot_rewrite(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)
    stage = case["stage"]
    destination = case["destination"]
    assert isinstance(stage, Path)
    assert isinstance(destination, Path)
    snapshot_path = stage / "snapshots" / f"{SNAPSHOT_ID}.json"
    preparation_path = stage / "manifests" / "backup-preparation.json"
    snapshot = json.loads(snapshot_path.read_bytes())
    snapshot["state_hash"] = "f" * 64
    snapshot_raw = canonical_bytes(snapshot)
    snapshot_path.write_bytes(snapshot_raw)
    preparation = json.loads(preparation_path.read_bytes())
    preparation["snapshot"] = snapshot
    preparation["snapshot_sha256"] = sha256_hex(snapshot_raw)
    for binding in preparation["file_bindings"]:
        if binding["relative_path"] == f"snapshots/{SNAPSHOT_ID}.json":
            binding["raw_sha256"] = sha256_hex(snapshot_raw)
            break
    preparation_path.write_bytes(canonical_bytes(preparation))

    with pytest.raises((ConflictError, IntegrityError), match="snapshot"):
        materializer.materialize(case["command"], committed)

    assert stage.is_dir()
    assert not destination.exists()


def test_committed_event_rejects_self_authenticated_source_object_rewrite(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)
    stage = case["stage"]
    destination = case["destination"]
    assert isinstance(stage, Path)
    assert isinstance(destination, Path)
    object_path = stage / "objects" / "stable.bin"
    preparation_path = stage / "manifests" / "backup-preparation.json"
    changed = b"post-event replacement\n"
    object_path.write_bytes(changed)
    preparation = json.loads(preparation_path.read_bytes())
    for binding in preparation["file_bindings"]:
        if binding["relative_path"] == "objects/stable.bin":
            binding["raw_sha256"] = sha256_hex(changed)
            break
    preparation_path.write_bytes(canonical_bytes(preparation))

    with pytest.raises((ConflictError, IntegrityError), match="Source file"):
        materializer.materialize(case["command"], committed)

    assert stage.is_dir()
    assert not (stage / "manifests" / "backup-receipt.json").exists()
    assert not destination.exists()


def test_exact_retry_returns_existing_receipt_without_second_event(tmp_path: Path) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    materializer.prepare(case["command"], case["before"])
    committed = _append_backup_created(case)
    first = materializer.materialize(case["command"], committed)
    destination = case["destination"]
    assert isinstance(destination, Path)
    before_bytes = _tree_bytes(destination)
    before_tail = case["ledger"].snapshot()

    retry_payload = materializer.derive_event_payload(
        snapshot_id=SNAPSHOT_ID,
        destination_class="offline-local-copy",
        schema_versions=("core-1.0.0",),
        tool_versions=("tdl-backup-1.0.0",),
        encryption_class="owner-approved-none",
        redaction_class="owner-approved-complete",
        ledger_snapshot=before_tail,
    )

    retried = materializer.materialize(case["command"], committed)

    assert retry_payload == case["command"].envelope["payload"]
    assert retried == first
    assert _tree_bytes(destination) == before_bytes
    after_tail = case["ledger"].snapshot()
    assert (after_tail.global_position, after_tail.event_hash) == (
        before_tail.global_position,
        before_tail.event_hash,
    )


@pytest.mark.parametrize("collision", ["stage", "destination"])
def test_foreign_stage_or_destination_is_preserved_and_rejected(
    tmp_path: Path,
    collision: str,
) -> None:
    case = _case(tmp_path)
    materializer = case["materializer"]
    assert isinstance(materializer, BackupMaterializer)
    collision_root = case[collision]
    assert isinstance(collision_root, Path)
    if collision == "stage":
        collision_root.mkdir()
        marker = collision_root / "foreign.txt"
        marker.write_text("foreign stage", encoding="utf-8")
        with pytest.raises(ConflictError, match="stage"):
            materializer.prepare(case["command"], case["before"])
    else:
        materializer.prepare(case["command"], case["before"])
        committed = _append_backup_created(case)
        collision_root.mkdir()
        marker = collision_root / "foreign.txt"
        marker.write_text("foreign destination", encoding="utf-8")
        with pytest.raises(ConflictError, match="destination"):
            materializer.materialize(case["command"], committed)
        assert case["stage"].is_dir()
    assert marker.read_text(encoding="utf-8") == f"foreign {collision}"
