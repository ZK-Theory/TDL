import json
import shutil
import threading

import pytest

from research_system.canonical import canonical_bytes
from research_system.command.models import Command
from research_system.command.reducers import reduce_task
from research_system.command.service import CommandService
from research_system.errors import ConflictError, IntegrityError, SchemaError
from research_system.schema_registry import (
    SchemaBinding,
    SchemaRegistry,
    runtime_schema_registry,
)
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    AUTHORITY_GRANT_ID,
    PROJECT_ID,
    REPO_ROOT,
    claim_dispatch_command,
    control_plane,
    create_task_command,
)

CMD_CREATE = "cmd_01978abc-2001-7000-8000-000000002001"
CMD_CLAIM_A = "cmd_01978abc-2002-7000-8000-000000002002"
CMD_CLAIM_B = "cmd_01978abc-2003-7000-8000-000000002003"
TASK_ID = "tsk_01978abc-2004-7000-8000-000000002004"
DISPATCH_ID = "dsp_01978abc-2005-7000-8000-000000002005"
ARTEFACT_ID = "art_01978abc-2006-7000-8000-000000002006"
TASK_ID_B = "tsk_01978abc-2007-7000-8000-000000002007"


def _registry_with_create_task_successor(tmp_path, version):
    schema_root = tmp_path / "successor-schemas"
    schema_root.mkdir()
    source_root = REPO_ROOT / ".research-system" / "schemas"
    for source in (
        source_root / "core" / "command.schema.json",
        source_root / "core" / "event.schema.json",
        source_root / "core" / "commands" / "create_task.schema.json",
        source_root / "core" / "events" / "task_created.schema.json",
    ):
        shutil.copy2(source, schema_root / source.name)

    successor = json.loads(
        (source_root / "core" / "commands" / "create_task.schema.json").read_text(
            encoding="utf-8",
        )
    )
    successor["properties"]["schema_version"]["const"] = version
    (schema_root / "create_task_successor.schema.json").write_bytes(canonical_bytes(successor))
    return SchemaRegistry(
        schema_root,
        active_bindings=(
            SchemaBinding(
                "ars://core/command/CreateTask",
                version,
                command_type="CreateTask",
            ),
            SchemaBinding(
                "ars://core/event/TaskCreated",
                "1.0.0",
                event_type="TaskCreated",
            ),
        ),
    )


def test_create_task_vertical_uses_exact_activated_schema_identity(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(
        CMD_CREATE,
        "activated-create",
        TASK_ID,
        {"title": "Activated task"},
    )

    receipt = harness.service.submit(command)
    event = tuple(harness.ledger.iter_events())[0]
    command_identity = harness.service.schemas.validate_active(
        command["schema_id"],
        command,
        schema_version=command["schema_version"],
    )
    event_identity = harness.service.schemas.validate_active(
        event["schema_id"],
        event,
        schema_version=event["schema_version"],
    )

    assert receipt.status == "accepted"
    assert event["payload"] == command["payload"]
    assert event["command_schema_id"] == command_identity.schema_id
    assert event["command_schema_version"] == command_identity.schema_version
    assert event["command_schema_sha256"] == command_identity.sha256
    assert event_identity.schema_id == "ars://core/event/TaskCreated"


def test_create_task_object_shape_follows_resolved_successor_binding(tmp_path):
    schemas = _registry_with_create_task_successor(tmp_path, "2.0.0")
    root = tmp_path / "control"
    root.mkdir()
    objects = ObjectStore(root)
    service = CommandService(
        root,
        EventLedger(root, PROJECT_ID, schemas),
        objects,
        ReceiptStore(root),
        schemas,
    )
    command = create_task_command(
        CMD_CREATE,
        "successor-create",
        TASK_ID,
        {"title": "Successor task"},
    )
    command["schema_version"] = "2.0.0"

    assert service.submit(command).status == "accepted"
    assert objects.read("task", TASK_ID, 1) == command["payload"]["definition"]


def test_inactive_dispatch_schema_materialization_is_inert(tmp_path):
    harness = control_plane(tmp_path)
    command = claim_dispatch_command(
        CMD_CLAIM_A,
        "actor-a",
        DISPATCH_ID,
        expected_version=0,
    )

    assert harness.service.schemas.contains("ars://core/event/DispatchClaimed")
    assert not harness.service.schemas.is_active(
        "ars://core/event/DispatchClaimed",
        "1.0.0",
    )
    assert harness.service.submit(command).status == "accepted"


def test_caller_supplied_command_schema_provenance_is_ignored(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(
        CMD_CREATE,
        "caller-provenance",
        TASK_ID,
        {"title": "Caller provenance"},
    )
    command.update(
        {
            "command_schema_id": "ars://caller/forged",
            "command_schema_version": "9.0.0",
            "command_schema_sha256": "0" * 64,
        }
    )

    assert harness.service.submit(command).status == "accepted"
    event = tuple(harness.ledger.iter_events())[0]
    identity = harness.service.schemas.resolve_identity(
        "ars://core/command/CreateTask",
        "1.0.0",
    )
    assert event["command_schema_id"] == identity.schema_id
    assert event["command_schema_version"] == identity.schema_version
    assert event["command_schema_sha256"] == identity.sha256


def test_active_command_avoids_unsatisfiable_generic_specific_intersection(
    tmp_path,
):
    harness = control_plane(tmp_path)
    command = create_task_command(
        CMD_CREATE,
        "specific-command",
        TASK_ID,
        {"title": "Specific command"},
    )

    with pytest.raises(SchemaError, match="ars://core/command"):
        harness.service.schemas.validate("ars://core/command", command)
    harness.service.schemas.validate_active(
        command["schema_id"],
        command,
        schema_version=command["schema_version"],
    )
    assert harness.service.submit(command).status == "accepted"


def test_generic_schema_cannot_bypass_active_create_task_binding(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(
        CMD_CREATE,
        "generic-create-bypass",
        TASK_ID,
        {"title": "Generic bypass"},
    )
    command["schema_id"] = "ars://core/command"
    command.pop("project_id")
    command["payload"] = {"title": "Generic bypass"}

    with pytest.raises(SchemaError, match="CreateTask"):
        harness.service.submit(command)

    assert tuple(harness.ledger.iter_batches()) == ()
    assert harness.receipts.load(CMD_CREATE) is None
    assert not list((harness.objects.control_root / "objects").rglob("*.json"))


def test_inactive_event_records_generic_schema_identity(tmp_path):
    harness = control_plane(tmp_path)
    command = claim_dispatch_command(
        CMD_CLAIM_A,
        "actor-a",
        DISPATCH_ID,
        expected_version=0,
    )

    assert harness.service.submit(command).status == "accepted"
    event = tuple(harness.ledger.iter_events())[0]

    assert event["event_type"] == "DispatchClaimed"
    assert event["schema_id"] == "ars://core/event"
    assert event["schema_version"] == "1.0.0"


def test_generic_command_history_is_not_idempotent_with_exact_create_task(tmp_path):
    root = tmp_path / "control"
    root.mkdir()
    schema_root = REPO_ROOT / ".research-system" / "schemas"
    inert = SchemaRegistry(schema_root)
    runtime = runtime_schema_registry(schema_root)
    command = create_task_command(
        CMD_CREATE,
        "schema-aware-idempotency",
        TASK_ID,
        {"title": "Schema-aware idempotency"},
    )
    generic_identity = runtime.resolve_identity("ars://core/command", "1.0.0")
    command_model = Command(command)
    EventLedger(root, PROJECT_ID, inert).append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": TASK_ID,
                "command_id": command["command_id"],
                "command_type": command["command_type"],
                "command_schema_id": generic_identity.schema_id,
                "command_schema_version": generic_identity.schema_version,
                "command_schema_sha256": generic_identity.sha256,
                "actor_id": ACTORS["actor-a"],
                "authority_grant_id": AUTHORITY_GRANT_ID,
                "idempotency_key": command["idempotency_key"],
                "command_payload_hash": command_model.payload_hash,
                "correlation_id": command["correlation_id"],
                "causation_id": command["causation_id"],
                "schema_id": "ars://core/event",
                "schema_version": "1.0.0",
                "occurred_at": None,
                "payload": command["payload"],
            }
        ]
    )
    service = CommandService(
        root,
        EventLedger(root, PROJECT_ID, runtime),
        ObjectStore(root),
        ReceiptStore(root),
        runtime,
    )

    with pytest.raises(ConflictError, match="idempotency"):
        service.submit(command)

    assert len(tuple(service.ledger.iter_batches())) == 1
    assert service.receipts.load(CMD_CREATE) is None


def test_derived_lineage_fails_closed_on_corrupt_existing_cycle():
    node_a = ("task-a", 1)
    node_b = ("task-b", 1)
    errors = []
    completed = threading.Event()

    def derive() -> None:
        try:
            CommandService._derived_lineage(
                {node_a: node_b, node_b: node_a},
                node_a,
                ("task-c", 1),
            )
        except Exception as exc:  # pragma: no branch - expected fail-closed path
            errors.append(exc)
        finally:
            completed.set()

    worker = threading.Thread(target=derive, daemon=True)
    worker.start()
    assert completed.wait(0.5), "lineage derivation did not terminate"
    assert len(errors) == 1
    assert isinstance(errors[0], IntegrityError)
    assert str(errors[0]) == "supersession lineage cycle"


def test_identical_retry_returns_original_receipt_and_one_batch(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, "same", TASK_ID, {"title": "A"})
    assert harness.service.submit(command) == harness.service.submit(command)
    assert len(tuple(harness.ledger.iter_batches())) == 1


def test_novel_submission_does_not_scan_existing_schema_scopes(tmp_path):
    class IterationForbiddenDict(dict):
        def __iter__(self):
            raise AssertionError("schema-scope index was scanned")

    harness = control_plane(tmp_path)
    first = create_task_command(CMD_CREATE, "first-scope", TASK_ID, {"title": "A"})
    assert harness.service.submit(first).status == "accepted"
    assert harness.service._view is not None
    harness.service._view.batches_by_scope = IterationForbiddenDict(harness.service._view.batches_by_scope)
    second = create_task_command(
        CMD_CLAIM_A,
        "second-scope",
        TASK_ID_B,
        {"title": "B"},
    )

    assert harness.service.submit(second).status == "accepted"


def test_same_idempotency_key_with_changed_payload_conflicts(tmp_path):
    harness = control_plane(tmp_path)
    first = create_task_command(CMD_CREATE, "same", TASK_ID, {"title": "A"})
    changed = create_task_command(CMD_CREATE, "same", TASK_ID, {"title": "B"})
    harness.service.submit(first)
    with pytest.raises(ConflictError, match="idempotency"):
        harness.service.submit(changed)


def test_same_key_is_independent_across_command_types(tmp_path):
    harness = control_plane(tmp_path)
    create = create_task_command(CMD_CREATE, "shared", TASK_ID, {"title": "A"})
    claim = claim_dispatch_command(CMD_CLAIM_A, "actor-a", DISPATCH_ID, expected_version=0)
    claim["idempotency_key"] = "shared"
    assert harness.service.submit(create).status == "accepted"
    assert harness.service.submit(claim).status == "accepted"
    assert len(tuple(harness.ledger.iter_batches())) == 2


def test_reused_command_id_conflicts_before_second_batch(tmp_path):
    harness = control_plane(tmp_path)
    first = create_task_command(CMD_CREATE, "first-command", TASK_ID, {"title": "A"})
    reused = claim_dispatch_command(CMD_CREATE, "actor-b", DISPATCH_ID, expected_version=0)
    original = harness.service.submit(first)
    with pytest.raises(ConflictError, match="command ID conflicts"):
        harness.service.submit(reused)
    assert len(tuple(harness.ledger.iter_batches())) == 1
    assert harness.receipts.load(CMD_CREATE) == original


def test_competing_claims_create_only_one_active_attempt(tmp_path):
    harness = control_plane(tmp_path)
    first = claim_dispatch_command(CMD_CLAIM_A, "actor-a", DISPATCH_ID, expected_version=0)
    second = claim_dispatch_command(CMD_CLAIM_B, "actor-b", DISPATCH_ID, expected_version=0)
    winner = harness.service.submit(first)
    loser = harness.service.submit(second)
    assert {winner.status, loser.status} == {"accepted", "conflict"}
    assert len(harness.replay().active_attempt_ids) == 1


def test_conflict_receipt_is_persisted_and_reused_after_stream_changes(tmp_path):
    harness = control_plane(tmp_path)
    blocked = claim_dispatch_command(CMD_CLAIM_A, "actor-a", DISPATCH_ID, expected_version=1)
    original = harness.service.submit(blocked)
    assert original.status == "conflict"
    assert original.observed_stream_version == 0
    assert harness.receipts.load(CMD_CLAIM_A) == original

    advancing = claim_dispatch_command(CMD_CLAIM_B, "actor-a", DISPATCH_ID, expected_version=0)
    assert harness.service.submit(advancing).status == "accepted"
    restarted = CommandService(
        harness.service.control_root,
        harness.ledger,
        harness.objects,
        harness.receipts,
        harness.service.schemas,
    )
    assert restarted.submit(blocked) == original


def test_conflict_receipt_rejects_command_id_reuse_with_changed_payload(tmp_path):
    harness = control_plane(tmp_path)
    blocked = claim_dispatch_command(CMD_CLAIM_A, "actor-a", DISPATCH_ID, expected_version=1)
    harness.service.submit(blocked)
    changed = {**blocked, "payload": {"changed": True}}
    with pytest.raises(ConflictError, match="stored receipt"):
        harness.service.submit(changed)


def test_distinct_task_and_artefact_objects_cannot_overwrite(tmp_path):
    harness = control_plane(tmp_path)
    task = harness.objects.write("task", TASK_ID, 1, {"kind": "task"})
    artefact = harness.objects.write("artefact", ARTEFACT_ID, 1, {"kind": "artefact"})
    assert task != artefact
    assert task.read_bytes() != artefact.read_bytes()


def test_committed_batch_reconstructs_missing_receipt_on_retry(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, "recover", TASK_ID, {"title": "A"})
    original_write = harness.receipts.write
    monkeypatch.setattr(
        harness.receipts,
        "write",
        lambda receipt: (_ for _ in ()).throw(OSError("receipt crash")),
    )
    with pytest.raises(OSError, match="receipt crash"):
        harness.service.submit(command)
    assert len(tuple(harness.ledger.iter_batches())) == 1
    monkeypatch.setattr(harness.receipts, "write", original_write)
    recovered = harness.service.submit(command)
    assert recovered.status == "accepted"
    assert len(tuple(harness.ledger.iter_batches())) == 1
    assert harness.receipts.load(CMD_CREATE) == recovered


def test_reconstructed_receipt_uses_target_stream_version_not_batch_max(tmp_path):
    harness = control_plane(tmp_path)
    transaction_id = "txb_01978abc-2011-7000-8000-000000002011"
    shared = {
        "command_id": CMD_CREATE,
        "command_payload_hash": "a" * 64,
        "transaction_id": transaction_id,
    }
    reconstructed = harness.service._return_or_reconstruct(
        [
            {**shared, "stream_id": TASK_ID, "stream_version": 1},
            {**shared, "stream_id": DISPATCH_ID, "stream_version": 4},
        ]
    )
    assert reconstructed.observed_stream_version == 1


def test_retry_rejects_receipt_that_does_not_match_committed_batch(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, "receipt-match", TASK_ID, {"title": "A"})
    harness.service.submit(command)
    path = harness.receipts.receipts_root / f"{CMD_CREATE}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["outcome"]["event_batch_id"] = "txb_01978abc-2010-7000-8000-000000002010"
    path.write_bytes(canonical_bytes(record))
    with pytest.raises(IntegrityError, match="receipt does not match"):
        harness.service.submit(command)


def test_invalid_command_is_rejected_before_lifecycle_event(tmp_path):
    harness = control_plane(tmp_path)
    invalid = create_task_command(CMD_CREATE, "invalid", TASK_ID, {"title": "A"})
    invalid.pop("reason")
    with pytest.raises(SchemaError, match="reason"):
        harness.service.submit(invalid)
    assert tuple(harness.ledger.iter_batches()) == ()


def test_task_reducer_is_pure_and_fails_closed():
    created = reduce_task(
        {},
        {"event_type": "TaskCreated", "stream_id": TASK_ID},
    )
    assert created == {"task_id": TASK_ID, "status": "draft", "version": 1}
    with pytest.raises(ValueError, match="TaskCreated requires empty stream"):
        reduce_task(created, {"event_type": "TaskCreated", "stream_id": TASK_ID})


def test_unknown_task_stream_readiness_fails_as_illegal_transition():
    with pytest.raises(ValueError, match="illegal task transition: None"):
        reduce_task(
            {},
            {"event_type": "ReadinessRequested", "stream_id": TASK_ID},
        )


def test_submission_materializes_ledger_once(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, "one-scan", TASK_ID, {"title": "A"})
    original = harness.ledger.iter_events
    calls = 0

    def counted_events():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(harness.ledger, "iter_events", counted_events)
    assert harness.service.submit(command).status == "accepted"
    assert calls == 1


def test_persisted_receipt_matches_frozen_schema(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, "receipt-schema", TASK_ID, {"title": "A"})
    harness.service.submit(command)
    record = json.loads((harness.receipts.receipts_root / f"{CMD_CREATE}.json").read_text(encoding="utf-8"))
    harness.service.schemas.validate("ars://core/receipt", record)
