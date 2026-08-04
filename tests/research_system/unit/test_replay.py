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
from research_system.errors import ArsError, ConfigurationError, IntegrityError
from research_system.projection.replay import apply_event, rebuild_projection, replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import (
    initialize_control_store,
    verify_store_identity,
)
from tests.research_system.factories import (
    PROJECT_ID,
    REPO_ROOT,
    control_plane,
    create_task_command,
    write_authority_bootstrap_input,
)

COMMAND_ID = "cmd_01978abc-4001-7000-8000-000000004001"
TASK_ID = "tsk_01978abc-4002-7000-8000-000000004002"
DISPATCH_ID = "dsp_01978abc-4004-7000-8000-000000004004"
LEASE_ID = "els_01978abc-4005-7000-8000-000000004005"
ATTEMPT_ID = "att_01978abc-4006-7000-8000-000000004006"
RESOURCE_GRANT_ID = "rgr_01978abc-4007-7000-8000-000000004007"


def _events(tmp_path):
    harness = control_plane(tmp_path)
    harness.service.submit(create_task_command(COMMAND_ID, "replay", TASK_ID, {"title": "Replay"}))
    return list(harness.ledger.iter_events()), harness


def _rehash(event):
    changed = dict(event)
    changed.pop("event_hash", None)
    changed["event_hash"] = sha256_hex(canonical_bytes(changed))
    return changed


def _generic_lease_granted_event(template, harness):
    event = deepcopy(template)
    binding = harness.schemas.command_binding("ClaimExecutionLease")
    assert binding is not None
    identity = harness.schemas.resolve_identity(binding.schema_id, binding.schema_version)
    payload = {
        "new_lease_id": LEASE_ID,
        "task_id": TASK_ID,
        "task_revision": 1,
        "dispatch_id": DISPATCH_ID,
        "attempt_id": ATTEMPT_ID,
        "resource_grant_id": RESOURCE_GRANT_ID,
        "holder_actor_id": "actor-a",
        "expires_at": "2026-08-01T13:00:00Z",
        "renewal_policy_ref": "policy:lease:v1",
    }
    event.update(
        {
            "event_type": "LeaseGranted",
            "stream_id": LEASE_ID,
            "stream_version": 1,
            "schema_id": "ars://core/event",
            "schema_version": "1.0.0",
            "command_type": "ClaimExecutionLease",
            "command_schema_id": identity.schema_id,
            "command_schema_version": identity.schema_version,
            "command_schema_sha256": identity.sha256,
            "command_payload_hash": sha256_hex(canonical_bytes(payload)),
            "payload": payload,
            "global_position": 1,
            "previous_event_hash": "0" * 64,
            "transaction_count": 1,
            "transaction_index": 1,
        }
    )
    return _rehash(event)


def _generic_claim_dispatch_events(
    template,
    harness,
    *,
    malformed_field: str | None = None,
    claim_schema_command_type: str = "ClaimDispatch",
    claim_event_schema_ids: tuple[str, str] = ("ars://core/event", "ars://core/event"),
):
    events = []
    previous_event_hash = "0" * 64

    def append(event_type, stream_id, stream_version, payload, *, command_type, **overrides):
        nonlocal previous_event_hash
        binding = harness.schemas.command_binding(command_type)
        assert binding is not None
        command_identity = harness.schemas.resolve_identity(binding.schema_id, binding.schema_version)
        event = _rehash(
            {
                **template,
                "event_type": event_type,
                "stream_id": stream_id,
                "stream_version": stream_version,
                "schema_id": "ars://core/event",
                "command_type": command_type,
                "command_schema_id": command_identity.schema_id,
                "command_schema_version": command_identity.schema_version,
                "command_schema_sha256": command_identity.sha256,
                "command_payload_hash": sha256_hex(canonical_bytes(payload)),
                "payload": payload,
                "global_position": len(events) + 1,
                "previous_event_hash": previous_event_hash,
                "transaction_id": f"txb_01978abc-{4001 + len(events):04d}-7000-8000-{4001 + len(events):012d}",
                "transaction_count": 1,
                "transaction_index": 1,
                **overrides,
            }
        )
        events.append(event)
        previous_event_hash = event["event_hash"]

    append(
        "TaskCreated",
        TASK_ID,
        1,
        {"title": "Generic historical ClaimDispatch Task"},
        command_type="CreateTask",
    )
    append(
        "ReadinessRequested",
        TASK_ID,
        2,
        {
            "task_id": TASK_ID,
            "task_revision": 1,
            "readiness_evidence_refs": ["evidence:generic-readiness"],
        },
        command_type="RequestReadiness",
    )
    append(
        "ReadinessApproved",
        TASK_ID,
        3,
        {
            "task_id": TASK_ID,
            "task_revision": 1,
            "readiness_evidence_refs": ["evidence:generic-readiness"],
            "passed_check_ids": ["check:generic-readiness"],
        },
        command_type="ApproveReadiness",
    )
    append(
        "DispatchIssued",
        DISPATCH_ID,
        1,
        {
            "dispatch_id": DISPATCH_ID,
            "definition": {"dispatch_id": DISPATCH_ID, "task_id": TASK_ID, "task_revision": 1},
        },
        command_type="IssueDispatch",
    )
    append(
        "DispatchDelivered",
        DISPATCH_ID,
        2,
        {
            "dispatch_id": DISPATCH_ID,
            "recipient_actor_id": "actor-a",
            "delivery_evidence_refs": ["evidence:generic-delivery"],
        },
        command_type="RecordDispatchDelivery",
    )
    append(
        "DispatchAcknowledged",
        DISPATCH_ID,
        3,
        {"dispatch_id": DISPATCH_ID, "recipient_actor_id": "actor-a"},
        command_type="AcknowledgeDispatch",
    )
    dispatch_payload = {
        "dispatch_id": DISPATCH_ID,
        "task_id": TASK_ID,
        "task_revision": 1,
        "lease_id": LEASE_ID,
        "expected_dispatch_stream_version": 3,
        "expected_task_stream_version": 3,
        "declared_write_set": ["dispatch", "task"],
        "expected_global_position": 6,
        "expected_tail_hash": previous_event_hash,
    }
    if malformed_field is not None:
        dispatch_payload[malformed_field] = "not-an-integer"
    transaction_id = "txb_01978abc-4007-7000-8000-000000004007"
    command_payload_hash = sha256_hex(canonical_bytes(dispatch_payload))
    append(
        "DispatchClaimed",
        DISPATCH_ID,
        4,
        dispatch_payload,
        command_type="ClaimDispatch",
        schema_id=claim_event_schema_ids[0],
        transaction_id=transaction_id,
        transaction_count=2,
        transaction_index=1,
        command_schema_id=harness.schemas.resolve_identity(
            harness.schemas.command_binding(claim_schema_command_type).schema_id,
            harness.schemas.command_binding(claim_schema_command_type).schema_version,
        ).schema_id,
        command_schema_version=harness.schemas.resolve_identity(
            harness.schemas.command_binding(claim_schema_command_type).schema_id,
            harness.schemas.command_binding(claim_schema_command_type).schema_version,
        ).schema_version,
        command_schema_sha256=harness.schemas.resolve_identity(
            harness.schemas.command_binding(claim_schema_command_type).schema_id,
            harness.schemas.command_binding(claim_schema_command_type).schema_version,
        ).sha256,
        command_payload_hash=command_payload_hash,
    )
    append(
        "TaskClaimStarted",
        TASK_ID,
        4,
        {"task_id": TASK_ID, "task_revision": 1},
        command_type="ClaimDispatch",
        schema_id=claim_event_schema_ids[1],
        transaction_id=transaction_id,
        transaction_count=2,
        transaction_index=2,
        command_schema_id=harness.schemas.resolve_identity(
            harness.schemas.command_binding(claim_schema_command_type).schema_id,
            harness.schemas.command_binding(claim_schema_command_type).schema_version,
        ).schema_id,
        command_schema_version=harness.schemas.resolve_identity(
            harness.schemas.command_binding(claim_schema_command_type).schema_id,
            harness.schemas.command_binding(claim_schema_command_type).schema_version,
        ).schema_version,
        command_schema_sha256=harness.schemas.resolve_identity(
            harness.schemas.command_binding(claim_schema_command_type).schema_id,
            harness.schemas.command_binding(claim_schema_command_type).schema_version,
        ).sha256,
        command_payload_hash=command_payload_hash,
    )
    return events


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


def test_replay_keeps_valid_generic_lease_granted_history_readable(tmp_path):
    events, harness = _events(tmp_path)

    projection = replay([_generic_lease_granted_event(events[0], harness)], schema_registry=harness.service.schemas)

    assert projection["streams"][LEASE_ID]["status"] == "active"


def test_replay_maps_malformed_generic_lease_granted_shapes_to_integrity_error(tmp_path):
    events, harness = _events(tmp_path)
    valid = _generic_lease_granted_event(events[0], harness)
    malformed_payloads = []

    missing = deepcopy(valid)
    missing["payload"].pop("new_lease_id")
    malformed_payloads.append(_rehash(missing))

    wrong_type = deepcopy(valid)
    wrong_type["payload"]["task_revision"] = None
    malformed_payloads.append(_rehash(wrong_type))

    wrong_value = deepcopy(valid)
    wrong_value["payload"]["task_revision"] = "not-an-integer"
    malformed_payloads.append(_rehash(wrong_value))

    for malformed in malformed_payloads:
        with pytest.raises(IntegrityError):
            replay([malformed], schema_registry=harness.service.schemas)


@pytest.mark.parametrize(
    "malformed_field",
    (
        "expected_dispatch_stream_version",
        "expected_task_stream_version",
        "expected_global_position",
    ),
)
def test_replay_rejects_non_integer_generic_claim_dispatch_expected_positions(tmp_path, malformed_field):
    events, harness = _events(tmp_path)

    with pytest.raises(IntegrityError, match="ClaimDispatch expected positions must be integers"):
        replay(
            _generic_claim_dispatch_events(events[0], harness, malformed_field=malformed_field),
            schema_registry=harness.service.schemas,
        )


def test_replay_keeps_valid_generic_claim_dispatch_history_readable(tmp_path):
    events, harness = _events(tmp_path)

    projection = replay(
        _generic_claim_dispatch_events(events[0], harness),
        schema_registry=harness.service.schemas,
    )

    assert projection["streams"][DISPATCH_ID]["status"] == "claimed"
    assert projection["streams"][TASK_ID]["status"] == "in_progress"


def test_replay_rejects_generic_claim_dispatch_with_another_registered_command_identity(tmp_path):
    events, harness = _events(tmp_path)

    with pytest.raises(IntegrityError, match="ClaimDispatch command schema binding mismatch"):
        replay(
            _generic_claim_dispatch_events(
                events[0],
                harness,
                claim_schema_command_type="IssueDispatch",
            ),
            schema_registry=harness.service.schemas,
        )


def test_invalid_claim_dispatch_batch_cannot_replace_an_existing_projection(tmp_path):
    events, harness = _events(tmp_path)
    output = tmp_path / "projection.json"
    output.write_bytes(b"previous-projection\n")

    with pytest.raises(IntegrityError, match="ClaimDispatch command schema binding mismatch"):
        rebuild_projection(
            _generic_claim_dispatch_events(
                events[0],
                harness,
                claim_schema_command_type="IssueDispatch",
            ),
            output,
            schema_registry=harness.service.schemas,
        )

    assert output.read_bytes() == b"previous-projection\n"


def test_replay_rejects_mixed_generic_and_exact_claim_dispatch_event_schemas(tmp_path):
    events, harness = _events(tmp_path)

    with pytest.raises(IntegrityError, match="ClaimDispatch event schema representation mismatch"):
        replay(
            _generic_claim_dispatch_events(
                events[0],
                harness,
                claim_event_schema_ids=("ars://core/event", "ars://core/event/TaskClaimStarted"),
            ),
            schema_registry=harness.service.schemas,
        )


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
    events, harness = _events(tmp_path)
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
    origin_authority_root = tmp_path / "origin-authority"
    origin_authority_root.mkdir()
    identity = initialize_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        origin_authority_root=origin_authority_root,
    )
    assert (
        verify_store_identity(
            control_root,
            PROJECT_ID,
            identity,
            approved_witness=identity.witness,
        )
        == identity
    )
    with pytest.raises(ArsError, match="store identity mismatch"):
        verify_store_identity(
            control_root,
            PROJECT_ID,
            "0" * 64,
            approved_witness=identity.witness,
        )
    rogue_root = tmp_path / "rogue-repo"
    rogue_root.mkdir()
    with pytest.raises(ArsError, match="code root binding mismatch"):
        verify_store_identity(
            control_root,
            PROJECT_ID,
            identity,
            [rogue_root],
            approved_witness=identity.witness,
        )
    with pytest.raises(ArsError, match="disjoint from every code root"):
        initialize_control_store(
            [code_root],
            code_root / "worktree-local-control",
            PROJECT_ID,
            origin_authority_root=origin_authority_root,
        )


def test_verify_store_identity_reports_missing_code_roots_as_binding_mismatch(tmp_path):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    control_root = tmp_path / "control"
    origin_authority_root = tmp_path / "origin-authority"
    origin_authority_root.mkdir()
    identity = initialize_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        origin_authority_root=origin_authority_root,
    )
    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("code_roots")
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))

    with pytest.raises(ArsError, match="initial store manifest differs from approved origin witness"):
        verify_store_identity(
            control_root,
            PROJECT_ID,
            identity,
            [code_root],
            approved_witness=identity.witness,
        )


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


def test_s006_cli_requires_materialized_canonical_origin_pins(tmp_path, monkeypatch):
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
    with pytest.raises(ConfigurationError, match="approved origin_authority_root must be a materialized value"):
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
    assert not control_root.exists()
