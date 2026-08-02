from __future__ import annotations

from copy import deepcopy
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.cli import main
from research_system.errors import ArsError, ConfigurationError, IntegrityError
from research_system.projection.replay import apply_event, rebuild_projection, replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import (
    _fsync_directory,
    initialize_control_store,
    rebind_restored_store,
    verify_store_identity,
)
from tests.research_system.factories import (
    PROJECT_ID,
    REPO_ROOT,
    claim_dispatch_command,
    control_plane,
    create_task_command,
    write_authority_bootstrap_input,
)

COMMAND_ID = "cmd_01978abc-4001-7000-8000-000000004001"
TASK_ID = "tsk_01978abc-4002-7000-8000-000000004002"


def _events(tmp_path):
    harness = control_plane(tmp_path)
    harness.service.submit(create_task_command(COMMAND_ID, "replay", TASK_ID, {"title": "Replay"}))
    return list(harness.ledger.iter_events()), harness


def _rehash(event):
    changed = dict(event)
    changed.pop("event_hash", None)
    changed["event_hash"] = sha256_hex(canonical_bytes(changed))
    return changed


def test_emitted_event_matches_frozen_schema(tmp_path):
    events, _ = _events(tmp_path)
    SchemaRegistry(Path(".research-system/schemas")).validate("ars://core/event", events[0])


def test_s008_incomplete_scope_completion_is_rejected():
    initial = {"streams": {}, "last_position": 0, "last_hash": "0" * 64}
    event = {
        "event_type": "ScopeCompleted",
        "stream_id": "prj_01978abc-4003-7000-8000-000000004003",
        "stream_version": 1,
        "payload": {
            "scope_definition_ref": {"object_id": "scope-1", "revision": 1},
            "required_member_ids": ["T2.1", "T2.2"],
            "member_dispositions": {"T2.1": "accepted"},
        },
    }
    with pytest.raises(IntegrityError, match="missing dispositions: T2.2"):
        apply_event(initial, event)
    assert initial == {"streams": {}, "last_position": 0, "last_hash": "0" * 64}


def test_s009_projection_rebuild_is_deterministic_and_disposable(tmp_path):
    events, harness = _events(tmp_path)
    output = tmp_path / "projection.json"
    canonical_before = tuple(path.read_bytes() for path in sorted(harness.ledger.events_root.rglob("*.jsonl")))
    first = rebuild_projection(
        events,
        output,
        schema_registry=harness.service.schemas,
    )
    first_bytes = output.read_bytes()
    output.unlink()
    second = rebuild_projection(
        events,
        output,
        schema_registry=harness.service.schemas,
    )
    assert first == second
    assert output.read_bytes() == first_bytes
    assert tuple(path.read_bytes() for path in sorted(harness.ledger.events_root.rglob("*.jsonl"))) == canonical_before


def test_s010_unknown_major_fails_before_projection_publication(tmp_path):
    events, _ = _events(tmp_path)
    unknown = deepcopy(events)
    unknown[0]["schema_version"] = "2.0.0"
    unknown[0] = _rehash(unknown[0])
    output = tmp_path / "projection.json"
    output.write_bytes(b"previous-projection\n")
    with pytest.raises(IntegrityError, match="unsupported major at 1"):
        rebuild_projection(unknown, output)
    assert output.read_bytes() == b"previous-projection\n"


def test_broken_event_hash_fails_closed(tmp_path):
    events, _ = _events(tmp_path)
    events[0]["payload"]["title"] = "tampered"
    with pytest.raises(IntegrityError, match="event hash mismatch at 1"):
        replay(events)


def test_replay_rejects_wrong_recorded_command_schema_hash(tmp_path):
    events, harness = _events(tmp_path)
    events[0]["command_schema_sha256"] = "0" * 64
    events[0] = _rehash(events[0])

    with pytest.raises(IntegrityError, match="command schema identity"):
        replay(events, schema_registry=harness.service.schemas)


def test_replay_rejects_wrong_recorded_command_schema_version(tmp_path):
    events, harness = _events(tmp_path)
    events[0]["command_schema_version"] = "2.0.0"
    events[0] = _rehash(events[0])

    with pytest.raises(IntegrityError, match="command schema identity"):
        replay(events, schema_registry=harness.service.schemas)


def test_replay_keeps_legacy_event_without_schema_provenance_readable(tmp_path):
    events, harness = _events(tmp_path)
    legacy = events[0]
    for field in (
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    ):
        legacy.pop(field)
    legacy["schema_id"] = "ars://core/event"
    legacy["payload"] = {"title": "Legacy task"}
    events[0] = _rehash(legacy)

    projection = replay(
        events,
        schema_registry=harness.service.schemas,
        legacy_command_provenance_through_position=1,
    )

    assert projection["streams"][TASK_ID]["status"] == "draft"


def test_replay_rejects_absent_command_provenance_after_default_cutover(tmp_path):
    events, harness = _events(tmp_path)
    for field in (
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    ):
        events[0].pop(field)
    events[0]["schema_id"] = "ars://core/event"
    events[0] = _rehash(events[0])

    with pytest.raises(IntegrityError, match="missing command schema identity at 1"):
        replay(events, schema_registry=harness.service.schemas)


def test_replay_validates_recorded_specific_event_with_inert_registry(tmp_path):
    events, _ = _events(tmp_path)
    events[0]["payload"] = {"title": "Only the generic envelope accepts this"}
    events[0] = _rehash(events[0])

    with pytest.raises(IntegrityError, match="event schema validation failed at 1"):
        replay(
            events,
            schema_registry=SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        )


def test_future_activation_does_not_reinterpret_generic_event_history(tmp_path):
    events, harness = _events(tmp_path)
    events[0]["schema_id"] = "ars://core/event"
    events[0]["payload"] = {"title": "Historically generic event"}
    events[0] = _rehash(events[0])

    projection = replay(events, schema_registry=harness.service.schemas)

    assert projection["streams"][TASK_ID]["status"] == "draft"


def test_replay_rejects_unbound_full_only_event_with_runtime_registry(tmp_path):
    harness = control_plane(tmp_path)
    command = claim_dispatch_command(
        "cmd_01978abc-4004-7000-8000-000000004004",
        "actor-a",
        "dsp_01978abc-4005-7000-8000-000000004005",
        expected_version=0,
    )
    assert harness.service.submit(command).status == "accepted"
    events = list(harness.ledger.iter_events())
    events[0]["schema_id"] = "ars://core/event/DispatchClaimed"
    events[0] = _rehash(events[0])

    with pytest.raises(IntegrityError, match="event schema validation failed at 1"):
        replay(events, schema_registry=harness.service.schemas)


def test_s012_store_identity_mismatch_and_worktree_local_store_are_rejected(
    tmp_path,
):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    control_root = tmp_path / "control"
    identity = initialize_control_store([code_root], control_root, PROJECT_ID)
    assert verify_store_identity(control_root, PROJECT_ID, identity) == identity
    with pytest.raises(ArsError, match="store identity mismatch"):
        verify_store_identity(control_root, PROJECT_ID, "0" * 64)
    rogue_root = tmp_path / "rogue-repo"
    rogue_root.mkdir()
    with pytest.raises(ArsError, match="code root binding mismatch"):
        verify_store_identity(control_root, PROJECT_ID, identity, [rogue_root])
    with pytest.raises(ArsError, match="disjoint from every code root"):
        initialize_control_store([code_root], code_root / "worktree-local-control", PROJECT_ID)


def test_verify_store_identity_reports_missing_code_roots_as_binding_mismatch(tmp_path):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    control_root = tmp_path / "control"
    identity = initialize_control_store([code_root], control_root, PROJECT_ID)
    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("code_roots")
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))

    with pytest.raises(ArsError, match="code root binding mismatch"):
        verify_store_identity(control_root, PROJECT_ID, identity, [code_root])


def _unit_restore_transaction_case(tmp_path: Path) -> dict[str, object]:
    from research_system.store.identity import canonical_restore_binding_output

    code_root = tmp_path / "repo"
    schema_root = code_root / ".research-system" / "schemas"
    schema_root.mkdir(parents=True)
    source_root = tmp_path / "source"
    identity = initialize_control_store([code_root], source_root, PROJECT_ID)
    manifest_path = source_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_binding_version"] = "1.0.0"
    manifest["schema_root"] = str(schema_root.resolve())
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    target_root = tmp_path / "target"
    shutil.copytree(source_root, target_root)
    snapshot = {
        "source_root": str(source_root.resolve()),
        "target_root": str(target_root.resolve()),
        "project_id": PROJECT_ID,
        "store_identity": identity,
    }
    snapshot_hash = sha256_hex(canonical_bytes(snapshot))
    output = canonical_restore_binding_output(
        target_root,
        PROJECT_ID,
        identity,
        [code_root],
        schema_root,
    )
    preflight = {
        "status": "verified",
        "failed_predicates": [],
        "receipt_hash": "a" * 64,
        "ledger_hash": "b" * 64,
        "snapshot_hash": "c" * 64,
        "target_endpoint_ownership_hash": "d" * 64,
        "artefact_manifest_hash": "e" * 64,
        "availability_observations_hash": "f" * 64,
        "registry_hash": "1" * 64,
        "target_root": str(target_root.resolve()),
        "project_id": PROJECT_ID,
        "store_identity": identity,
        "tail_position": 0,
        "tail_hash": "2" * 64,
        "snapshot_id": "snp_01978abc-1000-7000-8000-000000001003",
        "actor_id": "act_01978abc-1000-7000-8000-000000001001",
        "authority_grant_id": "agr_01978abc-1000-7000-8000-000000001002",
        "result_hash": "",
        "source_root": str(source_root.resolve()),
        "code_roots": [str(code_root.resolve())],
        "schema_root": str(schema_root.resolve()),
        "source_snapshot_hash": snapshot_hash,
        "target_manifest_bytes_sha256": sha256_hex(manifest_path.read_bytes()),
        "expected_output_sha256": sha256_hex(output),
    }
    preflight["result_hash"] = sha256_hex(canonical_bytes(preflight))
    return {
        "code_root": code_root,
        "schema_root": schema_root,
        "source": source_root,
        "target": target_root,
        "identity": identity,
        "snapshot": snapshot,
        "snapshot_hash": snapshot_hash,
        "output": output,
        "kwargs": {
            "expected_project_id": PROJECT_ID,
            "expected_store_identity": identity,
            "expected_code_roots": [code_root],
            "expected_schema_root": schema_root,
            "expected_restore_receipt_hash": "a" * 64,
            "actor_id": "act_01978abc-1000-7000-8000-000000001001",
            "authority_grant_id": "agr_01978abc-1000-7000-8000-000000001002",
            "source_snapshot": snapshot,
            "expected_source_snapshot_hash": snapshot_hash,
            "expected_output": output,
            "expected_restore_preflight": preflight,
        },
    }


def test_restored_store_transaction_is_canonical_monotone_and_idempotent(tmp_path, monkeypatch):
    from research_system.store.identity import (
        load_restore_binding_transaction,
        restore_binding_output_object_path,
        verify_restore_binding_admission,
    )

    monkeypatch.setattr("research_system.store.identity._fsync_directory", lambda _path: True)
    case = _unit_restore_transaction_case(tmp_path)
    rebound = rebind_restored_store(
        case["target"],
        case["source"],
        **case["kwargs"],
    )
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    transaction_raw = transaction_path.read_bytes()
    transaction = load_restore_binding_transaction(case["target"])
    assert transaction is not None
    assert transaction_raw == canonical_bytes(transaction)
    assert transaction["state"] == "cleared"
    assert transaction["generation"] == 7
    assert len(transaction["prior_record_sha256"]) == 64
    assert transaction["last_completed_durability_step"] == "clear-durable"
    assert rebound["control_root"] == str(case["target"].resolve())
    output = restore_binding_output_object_path(case["target"], transaction["output_object_sha256"])
    assert output.read_bytes() == case["output"]
    assert verify_restore_binding_admission(case["target"]) == transaction

    assert (
        rebind_restored_store(
            case["target"],
            case["source"],
            **case["kwargs"],
        )
        == rebound
    )
    assert transaction_path.read_bytes() == transaction_raw


def test_restored_store_rebind_has_no_journal_less_mode(tmp_path, monkeypatch):
    monkeypatch.setattr("research_system.store.identity._fsync_directory", lambda _path: True)
    case = _unit_restore_transaction_case(tmp_path)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before = manifest_path.read_bytes()

    with pytest.raises(ArsError, match="complete approved restore transaction inputs"):
        rebind_restored_store(
            case["target"],
            case["source"],
            expected_project_id=PROJECT_ID,
            expected_store_identity=case["identity"],
            expected_code_roots=[case["code_root"]],
        )

    assert manifest_path.read_bytes() == before
    assert not (case["target"] / "manifests" / ".restore-binding-transaction.json").exists()


def test_cleared_loader_rejects_coordinated_manifest_evidence_rewrite(tmp_path, monkeypatch):
    from research_system.store.identity import verify_restore_binding_admission

    monkeypatch.setattr("research_system.store.identity._fsync_directory", lambda _path: True)
    case = _unit_restore_transaction_case(tmp_path)
    rebind_restored_store(case["target"], case["source"], **case["kwargs"])
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    evidence_path = case["target"] / "manifests" / "restore-binding-evidence.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["endpoint_scheme"] = "coordinated-foreign"
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_bytes = canonical_bytes(manifest)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["manifest_hash"] = manifest["manifest_hash"]
    evidence["target_manifest_bytes_sha256"] = sha256_hex(manifest_bytes)
    manifest_path.write_bytes(manifest_bytes)
    evidence_path.write_bytes(canonical_bytes(evidence))

    with pytest.raises(IntegrityError, match="transaction"):
        verify_restore_binding_admission(case["target"])


def test_cleared_loader_rejects_coordinated_record_evidence_and_output_rewrite(tmp_path, monkeypatch):
    """Cleared admission needs an expected side outside the mutable current tuple."""
    from research_system.store.identity import verify_restore_binding_admission

    monkeypatch.setattr("research_system.store.identity._fsync_directory", lambda _path: True)
    case = _unit_restore_transaction_case(tmp_path)
    rebind_restored_store(case["target"], case["source"], **case["kwargs"])
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    evidence_path = case["target"] / "manifests" / "restore-binding-evidence.json"
    record = json.loads(transaction_path.read_text(encoding="utf-8"))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    foreign_snapshot = {"coordinated": "foreign-approved-source"}
    foreign_snapshot_hash = sha256_hex(canonical_bytes(foreign_snapshot))
    foreign_output = canonical_bytes({"coordinated": "foreign-output"})
    foreign_output_hash = sha256_hex(foreign_output)
    foreign_output_relative = f"manifests/restore-bindings/sha256-{foreign_output_hash}.json"
    foreign_output_path = case["target"] / Path(foreign_output_relative)
    foreign_output_path.write_bytes(foreign_output)

    record.update(
        {
            "actor_id": "act_01978abc-1000-7000-8000-000000009991",
            "authority_grant_id": "agr_01978abc-1000-7000-8000-000000009992",
            "receipt_hash": "b" * 64,
            "source_snapshot": foreign_snapshot,
            "source_snapshot_hash": foreign_snapshot_hash,
            "output_object_path": foreign_output_relative,
            "output_object_sha256": foreign_output_hash,
            "output_object_bytes": foreign_output.hex(),
        }
    )
    record["temporaries"]["output"] = {
        "relative_path": f"manifests/restore-bindings/.sha256-{foreign_output_hash}.json.{record['transaction_id']}.tmp",
        "sha256": foreign_output_hash,
    }
    evidence.update(
        {
            "actor_id": record["actor_id"],
            "authority_grant_id": record["authority_grant_id"],
            "receipt_hash": record["receipt_hash"],
            "source_snapshot": foreign_snapshot,
            "source_snapshot_hash": foreign_snapshot_hash,
            "expected_output_bytes": foreign_output.decode("utf-8"),
            "expected_output_sha256": foreign_output_hash,
            "output_object_path": foreign_output_relative,
            "output_object_sha256": foreign_output_hash,
        }
    )
    intended_evidence = canonical_bytes(evidence)
    record["intended_evidence_bytes"] = intended_evidence.hex()
    record["intended_evidence_sha256"] = sha256_hex(intended_evidence)
    record["temporaries"]["evidence"]["sha256"] = sha256_hex(intended_evidence)
    evidence_path.write_bytes(intended_evidence)
    transaction_path.write_bytes(canonical_bytes(record))

    with pytest.raises(IntegrityError, match="approval|expected|transaction"):
        verify_restore_binding_admission(case["target"])


def test_recordless_rebound_manifest_cannot_downgrade_to_initialized_store(tmp_path):
    from research_system.config import ControlBinding

    case = _unit_restore_transaction_case(tmp_path)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["control_root"] = str(case["target"].resolve())
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    binding_path = tmp_path / "recordless-rebound-binding.json"
    binding_path.write_bytes(case["output"])

    with pytest.raises((ConfigurationError, IntegrityError), match="origin|restore|materialized"):
        ControlBinding.load(binding_path)


def test_repeated_directory_durability_failure_never_advances_observed_generation(tmp_path, monkeypatch):
    import research_system.store.identity as identity_module

    case = _unit_restore_transaction_case(tmp_path)
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: False)

    for _attempt in range(24):
        with pytest.raises(ArsError, match="durab"):
            rebind_restored_store(case["target"], case["source"], **case["kwargs"])
        if transaction_path.exists():
            record = json.loads(transaction_path.read_text(encoding="utf-8"))
            assert record["generation"] == 0
            assert record["last_completed_durability_step"] == "prepared-record-durable"


def test_restored_store_recovers_one_record_after_transition_directory_fsync_failure(tmp_path, monkeypatch):
    import research_system.store.identity as identity_module

    case = _unit_restore_transaction_case(tmp_path)
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    original_replace = identity_module.os.replace
    transition_replaced = False
    failed = False

    def observe_replace(source: object, destination: object) -> None:
        nonlocal transition_replaced
        original_replace(source, destination)
        if Path(destination).resolve(strict=False) == transaction_path.resolve(strict=False):
            transition_replaced = True

    def fail_transition_directory_fsync(_path: Path) -> bool:
        nonlocal failed
        if transition_replaced and not failed:
            failed = True
            return False
        return True

    monkeypatch.setattr(identity_module.os, "replace", observe_replace)
    monkeypatch.setattr(identity_module, "_fsync_directory", fail_transition_directory_fsync)
    with pytest.raises(ArsError, match="durable transaction transition"):
        rebind_restored_store(case["target"], case["source"], **case["kwargs"])

    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert failed
    assert transaction["state"] == "prepared"
    assert transaction["last_completed_durability_step"] == "output-object-durable"
    assert not (case["target"] / "manifests" / ".restore-binding-recovery.json").exists()

    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: True)
    rebound = rebind_restored_store(case["target"], case["source"], **case["kwargs"])
    assert rebound["control_root"] == str(case["target"].resolve())
    assert json.loads(transaction_path.read_text(encoding="utf-8"))["state"] == "cleared"


@pytest.mark.parametrize("drift_root", ("source", "target"))
def test_restored_store_rejects_physical_root_identity_drift_after_prepared(
    tmp_path,
    monkeypatch,
    drift_root,
):
    import research_system.store.identity as identity_module

    case = _unit_restore_transaction_case(tmp_path)
    original_identity = identity_module._physical_root_identity
    drifted = False

    def arm_drift(_path: Path, state: str, generation: int) -> None:
        nonlocal drifted
        if state == "prepared" and generation == 0:
            drifted = True

    def physical_identity(path: Path) -> dict[str, str]:
        identity = original_identity(path)
        if drifted and path.resolve(strict=False) == case[drift_root].resolve(strict=False):
            return {**identity, "inode": str(int(identity["inode"]) + 1)}
        return identity

    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: True)
    monkeypatch.setattr(identity_module, "_after_restore_transaction_state_written", arm_drift)
    monkeypatch.setattr(identity_module, "_physical_root_identity", physical_identity)
    with pytest.raises(ArsError, match="physical root identity changed"):
        rebind_restored_store(case["target"], case["source"], **case["kwargs"])

    transaction = json.loads(
        (case["target"] / "manifests" / ".restore-binding-transaction.json").read_text(encoding="utf-8")
    )
    assert transaction["state"] == "prepared"
    assert transaction["last_completed_durability_step"] == "prepared-record-durable"


def test_directory_fsync_unsupported_is_explicitly_non_durable(tmp_path, monkeypatch):
    import research_system.store.identity as identity_module

    def unsupported(*_args, **_kwargs):
        raise OSError(22, "directory handles are unsupported")

    monkeypatch.setattr(identity_module.os, "name", "posix")
    monkeypatch.setattr("research_system.store.identity.os.open", unsupported)
    assert _fsync_directory(tmp_path) is False


@pytest.mark.skipif(os.name != "nt", reason="native Win32 directory durability contract")
def test_directory_fsync_uses_native_windows_directory_handle(tmp_path):
    assert _fsync_directory(tmp_path) is True


def test_cli_requires_explicit_control_and_code_paths():
    with pytest.raises(SystemExit) as exc_info:
        main(["store", "init", "--project-id", PROJECT_ID])
    assert exc_info.value.code == 2


def test_store_init_rejects_multiple_explicit_schema_authorities(tmp_path):
    roots = [tmp_path / "a", tmp_path / "b"]
    for root in roots:
        root.mkdir()
    with pytest.raises(ConfigurationError, match="exactly one explicit code root"):
        main(
            [
                "store",
                "init",
                "--code-root",
                str(roots[0]),
                "--code-root",
                str(roots[1]),
                "--control-root",
                str(tmp_path / "control"),
                "--project-id",
                PROJECT_ID,
                "--authority-bootstrap",
                str(tmp_path / "unread-bootstrap.json"),
            ]
        )
    assert not (tmp_path / "control").exists()
    with pytest.raises(SystemExit) as exc_info:
        main(["replay", "verify"])
    assert exc_info.value.code == 2


def test_store_init_fails_closed_when_worktrees_cannot_be_enumerated(tmp_path, monkeypatch):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    monkeypatch.setattr(
        "research_system.cli.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="git unavailable"),
    )
    with pytest.raises(ConfigurationError, match="cannot enumerate git worktrees"):
        main(
            [
                "store",
                "init",
                "--code-root",
                str(code_root),
                "--control-root",
                str(tmp_path / "control"),
                "--project-id",
                PROJECT_ID,
                "--authority-bootstrap",
                str(tmp_path / "unread-bootstrap.json"),
            ]
        )
    assert not (tmp_path / "control").exists()


def test_store_init_fails_closed_when_worktree_enumeration_times_out(tmp_path, monkeypatch):
    code_root = tmp_path / "repo"
    code_root.mkdir()

    def time_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(  # nosemgrep  # nosec B603 - test exception only
            args[0], kwargs["timeout"]
        )

    monkeypatch.setattr("research_system.cli.subprocess.run", time_out)
    with pytest.raises(ConfigurationError, match="timed out"):
        main(
            [
                "store",
                "init",
                "--code-root",
                str(code_root),
                "--control-root",
                str(tmp_path / "control"),
                "--project-id",
                PROJECT_ID,
                "--authority-bootstrap",
                str(tmp_path / "unread-bootstrap.json"),
            ]
        )
    assert not (tmp_path / "control").exists()


def test_s006_cli_uses_namespaced_projection_and_explicit_binding(tmp_path, capsys, monkeypatch):
    code_root = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / ".research-system" / "schemas",
        code_root / ".research-system" / "schemas",
    )
    monkeypatch.setattr(
        "research_system.cli.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=f"worktree {code_root.resolve()}\n",
            stderr="",
        ),
    )
    control_root = tmp_path / "control"
    bootstrap_path = write_authority_bootstrap_input(tmp_path / "authority-bootstrap.json")
    assert (
        main(
            [
                "store",
                "init",
                "--code-root",
                str(code_root),
                "--control-root",
                str(control_root),
                "--project-id",
                PROJECT_ID,
                "--authority-bootstrap",
                str(bootstrap_path),
            ]
        )
        == 0
    )
    identity = json.loads(capsys.readouterr().out)["store_identity"]
    config_path = tmp_path / "binding.json"
    config_path.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(code_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((code_root / ".research-system" / "schemas").resolve()),
                "store_identity": identity,
            }
        )
    )
    command_path = tmp_path / "command.json"
    command_path.write_bytes(canonical_bytes(create_task_command(COMMAND_ID, "cli-submit", TASK_ID, {"title": "CLI"})))
    assert (
        main(
            [
                "command",
                "submit",
                "--config",
                str(config_path),
                "--command",
                str(command_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["replay", "verify", "--control-root", str(control_root)]) == 0
    capsys.readouterr()
    output = code_root / ".research-system" / "projections" / "state.json"
    assert (
        main(
            [
                "projection",
                "rebuild",
                "--control-root",
                str(control_root),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["last_position"] == 3
    with pytest.raises(ArsError, match="namespaced projection root"):
        main(
            [
                "projection",
                "rebuild",
                "--control-root",
                str(control_root),
                "--output",
                str(code_root / "task.md"),
            ]
        )
    with pytest.raises(ArsError, match="projection output must be external"):
        main(
            [
                "projection",
                "rebuild",
                "--control-root",
                str(control_root),
                "--output",
                str(control_root / "events" / "projection.json"),
            ]
        )
