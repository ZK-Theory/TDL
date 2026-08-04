import json
import threading
from copy import deepcopy

import pytest

from research_system.canonical import canonical_bytes
from research_system.command.models import Command
from research_system.command.reducers import reduce_task
from research_system.command.service import CommandService
from research_system.errors import ConflictError, IntegrityError, SchemaError
from research_system.schema_registry import (
    SchemaRegistry,
)
from research_system.store.ledger import EventLedger, LedgerSnapshot
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    REPO_ROOT,
    activate_lifecycle_grant,
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


def test_create_task_rejects_unbound_schema_version_without_writes(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(
        CMD_CREATE,
        "successor-create",
        TASK_ID,
        {"title": "Successor task"},
    )
    command["schema_version"] = "2.0.0"

    with pytest.raises(SchemaError, match="CreateTask"):
        harness.service.submit(command)

    assert tuple(harness.ledger.iter_batches()) == ()
    assert harness.receipts.load(command["command_id"]) is None
    assert not list((harness.service.control_root / "objects").rglob("*.json"))


@pytest.mark.parametrize("payload", [None, [], "not-a-mapping"])
def test_revision_graph_rejects_non_mapping_legacy_task_payload(payload):
    snapshot = LedgerSnapshot(
        events=(
            {
                "event_type": "TaskCreated",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
                "payload": payload,
            },
        ),
        global_position=1,
        event_hash="0" * 64,
        stream_versions={TASK_ID: 1},
        fingerprint=(),
    )

    with pytest.raises(IntegrityError, match="TaskCreated payload must be a mapping"):
        CommandService._revision_graph(snapshot)


def test_active_dispatch_schema_rejects_generic_bypass_without_writes(tmp_path):
    harness = control_plane(tmp_path)
    command = claim_dispatch_command(
        CMD_CLAIM_A,
        "actor-a",
        DISPATCH_ID,
        expected_version=0,
    )

    assert harness.service.schemas.contains("ars://core/event/DispatchClaimed")
    assert harness.service.schemas.is_active(
        "ars://core/event/DispatchClaimed",
        "1.0.0",
    )
    with pytest.raises(SchemaError, match="ClaimDispatch"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()


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


def test_active_claim_dispatch_requires_its_exact_command_envelope(tmp_path):
    harness = control_plane(tmp_path)
    command = claim_dispatch_command(
        CMD_CLAIM_A,
        "actor-a",
        DISPATCH_ID,
        expected_version=0,
    )

    with pytest.raises(SchemaError, match="ClaimDispatch"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_events()) == ()


@pytest.mark.parametrize(
    ("actor_id", "command_types"),
    (
        (ACTORS["actor-b"], ("CreateTask",)),
        (ACTORS["actor-a"], ("AmendTask",)),
    ),
    ids=["actor-mismatch", "command-mismatch"],
)
def test_activate_lifecycle_grant_rejects_mismatched_existing_scope(tmp_path, actor_id, command_types):
    harness = control_plane(tmp_path)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_ID,
        command_types=("CreateTask",),
    )

    with pytest.raises(AssertionError, match="existing lifecycle grant does not match requested scope"):
        activate_lifecycle_grant(
            harness,
            subject_kind="task",
            subject_id=TASK_ID,
            actor_id=actor_id,
            command_types=command_types,
            grant_id=grant_id,
        )


def test_generic_command_history_is_not_idempotent_with_exact_create_task(tmp_path):
    harness = control_plane(tmp_path)
    root = harness.service.control_root
    schema_root = REPO_ROOT / ".research-system" / "schemas"
    inert = SchemaRegistry(schema_root)
    runtime = harness.schemas
    command = create_task_command(
        CMD_CREATE,
        "schema-aware-idempotency",
        TASK_ID,
        {"title": "Schema-aware idempotency"},
    )
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_ID,
    )
    command["authority_grant_id"] = grant_id
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
                "authority_grant_id": grant_id,
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
    service = harness.service

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


def test_active_c1_command_validates_before_cross_type_idempotency(tmp_path):
    harness = control_plane(tmp_path)
    create = create_task_command(CMD_CREATE, "shared", TASK_ID, {"title": "A"})
    claim = claim_dispatch_command(CMD_CLAIM_A, "actor-a", DISPATCH_ID, expected_version=0)
    claim["idempotency_key"] = "shared"
    assert harness.service.submit(create).status == "accepted"
    with pytest.raises(SchemaError, match="ClaimDispatch"):
        harness.service.submit(claim)
    assert len(tuple(harness.ledger.iter_batches())) == 1


def test_malformed_active_c1_command_does_not_consume_reused_command_id(tmp_path):
    harness = control_plane(tmp_path)
    first = create_task_command(CMD_CREATE, "first-command", TASK_ID, {"title": "A"})
    reused = claim_dispatch_command(CMD_CREATE, "actor-b", DISPATCH_ID, expected_version=0)
    original = harness.service.submit(first)
    with pytest.raises(SchemaError, match="ClaimDispatch"):
        harness.service.submit(reused)
    assert len(tuple(harness.ledger.iter_batches())) == 1
    assert harness.receipts.load(CMD_CREATE) == original


def test_conflict_receipt_is_persisted_and_reused_after_stream_changes(tmp_path):
    harness = control_plane(tmp_path)
    blocked = create_task_command(CMD_CLAIM_A, "blocked", TASK_ID, {"title": "Blocked"})
    blocked["expected_stream_version"] = 1
    original = harness.service.submit(blocked)
    assert original.status == "conflict"
    assert original.observed_stream_version == 0
    assert harness.receipts.load(CMD_CLAIM_A) == original

    advancing = create_task_command(CMD_CLAIM_B, "advancing", TASK_ID, {"title": "Advancing"})
    assert harness.service.submit(advancing).status == "accepted"
    assert harness.service.submit(blocked) == original


def test_conflict_receipt_rejects_command_id_reuse_with_changed_payload(tmp_path):
    harness = control_plane(tmp_path)
    blocked = create_task_command(CMD_CLAIM_A, "blocked", TASK_ID, {"title": "Blocked"})
    blocked["expected_stream_version"] = 1
    harness.service.submit(blocked)
    changed = deepcopy(blocked)
    changed["payload"]["definition"]["title"] = "Changed payload"
    with pytest.raises(ConflictError, match="idempotency key conflicts"):
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
