from __future__ import annotations

from copy import deepcopy
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.cli import main
from research_system.errors import ArsError, ConfigurationError, ConflictError, IntegrityError
from research_system.projection.replay import apply_event, rebuild_projection, replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import (
    _fsync_directory,
    initialize_control_store,
    load_store_manifest,
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


def test_restored_store_rebind_is_canonical_atomic_and_identity_stable(tmp_path):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    source_root = tmp_path / "source"
    identity = initialize_control_store([code_root], source_root, PROJECT_ID)
    target_root = tmp_path / "target"
    shutil.copytree(source_root, target_root)
    manifest_path = target_root / "manifests" / "store-identity.json"
    before = json.loads(manifest_path.read_text(encoding="utf-8"))

    rebound = rebind_restored_store(
        target_root,
        source_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=identity,
        expected_code_roots=[code_root],
    )

    after_bytes = manifest_path.read_bytes()
    after = json.loads(after_bytes)
    assert after_bytes == canonical_bytes(after)
    assert after["control_root"] == str(target_root.resolve())
    assert after["manifest_hash"] == sha256_hex(
        canonical_bytes({k: v for k, v in after.items() if k != "manifest_hash"})
    )
    assert after["store_identity"] == identity
    assert {key: value for key, value in after.items() if key not in {"control_root", "manifest_hash"}} == {
        key: value for key, value in before.items() if key not in {"control_root", "manifest_hash"}
    }
    assert rebound == after
    assert load_store_manifest(target_root)["control_root"] == str(target_root.resolve())

    assert (
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )
        == after
    )
    with pytest.raises(ConflictError, match="source binding"):
        rebind_restored_store(
            target_root,
            tmp_path / "different-source",
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )
    with pytest.raises(ConflictError, match="project identity"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id="prj_01978abc-1000-7000-8000-000000001099",
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )
    with pytest.raises(ConflictError, match="store identity"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity="0" * 64,
            expected_code_roots=[code_root],
        )
    with pytest.raises(ConflictError, match="source must differ"):
        rebind_restored_store(
            target_root,
            target_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )
    conflicting_target = tmp_path / "conflicting-target"
    shutil.copytree(source_root, conflicting_target)
    with pytest.raises(ConflictError, match="source binding"):
        rebind_restored_store(
            conflicting_target,
            tmp_path / "other-source",
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )


def test_restored_store_rebind_rejects_noncanonical_and_replace_failure(tmp_path, monkeypatch):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    source_root = tmp_path / "source"
    identity = initialize_control_store([code_root], source_root, PROJECT_ID)
    target_root = tmp_path / "target"
    shutil.copytree(source_root, target_root)
    manifest_path = target_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(IntegrityError, match="noncanonical"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )

    manifest_path.write_bytes(canonical_bytes(manifest))
    manifest["manifest_hash"] = "0" * 64
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(IntegrityError, match="hash mismatch"):
        rebind_restored_store(target_root, source_root)
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest["code_roots"] = [str(target_root.resolve())]
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(ArsError, match="disjoint"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[target_root],
        )
    manifest["code_roots"] = [str(code_root.resolve())]
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    original = manifest_path.read_bytes()

    def interrupted_replace(*_args, **_kwargs):
        raise OSError("replace interrupted")

    monkeypatch.setattr("research_system.store.identity.os.replace", interrupted_replace)
    with pytest.raises(OSError, match="replace interrupted"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )
    assert manifest_path.read_bytes() == original
    assert not list(manifest_path.parent.glob(".*.tmp"))


def test_restored_store_rebind_recovers_after_post_replace_durability_failure(tmp_path, monkeypatch):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    source_root = tmp_path / "source"
    identity = initialize_control_store([code_root], source_root, PROJECT_ID)
    target_root = tmp_path / "target"
    shutil.copytree(source_root, target_root)

    calls = 0

    def fail_after_manifest_replace(_path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("directory durability interrupted")
        return True

    monkeypatch.setattr("research_system.store.identity._fsync_directory", fail_after_manifest_replace)
    with pytest.raises(OSError, match="directory durability interrupted"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=identity,
            expected_code_roots=[code_root],
        )

    monkeypatch.setattr("research_system.store.identity._fsync_directory", lambda _path: True)
    rebound = rebind_restored_store(
        target_root,
        source_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=identity,
        expected_code_roots=[code_root],
    )
    assert rebound["control_root"] == str(target_root.resolve())
    assert load_store_manifest(target_root)["control_root"] == str(target_root.resolve())


def test_directory_fsync_unsupported_is_explicitly_non_durable(tmp_path, monkeypatch):
    def unsupported(*_args, **_kwargs):
        raise OSError(22, "directory handles are unsupported")

    monkeypatch.setattr("research_system.store.identity.os.open", unsupported)
    assert _fsync_directory(tmp_path) is False


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
