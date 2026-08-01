import json
import os
from pathlib import Path
import threading

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.layout import require_external_control_root
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore, write_object
from research_system.store.receipts import ReceiptStore


PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"
TASK_ID = "tsk_01978abc-0002-7000-8000-000000000002"
SCHEMAS = Path(".research-system/schemas")


def _catalogue_only_ledger(tmp_path):
    return EventLedger(
        tmp_path,
        project_id=PROJECT_ID,
        schemas=SchemaRegistry(SCHEMAS),
    )


def test_control_root_requires_registered_code_roots(tmp_path):
    with pytest.raises(ArsError, match="registered code roots required"):
        require_external_control_root([], tmp_path / "control")


def test_control_root_overlapping_any_registered_worktree_is_rejected(tmp_path):
    main = tmp_path / "main"
    worktree = tmp_path / "worktree"
    main.mkdir()
    worktree.mkdir()
    with pytest.raises(ArsError, match="disjoint from every code root"):
        require_external_control_root([main, worktree], worktree / "control")
    with pytest.raises(ArsError, match="disjoint from every code root"):
        require_external_control_root([main, worktree], tmp_path)


def test_sibling_external_control_root_is_accepted(tmp_path):
    code_root = tmp_path / "repo"
    control_root = tmp_path / "control"
    code_root.mkdir()
    assert require_external_control_root([code_root], control_root) == control_root.resolve()


def test_resolved_reparse_parent_overlapping_code_root_is_rejected(tmp_path):
    code_root = tmp_path / "repo"
    linked_parent = tmp_path / "linked-parent"
    code_root.mkdir()
    try:
        linked_parent.symlink_to(code_root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink/reparse creation unavailable on this host")
    with pytest.raises(ArsError, match="disjoint from every code root"):
        require_external_control_root([code_root], linked_parent / "control")


def test_second_writer_lock_is_rejected(tmp_path):
    path = tmp_path / "writer.lock"
    with WriterLock(path, {"writer_id": "w1"}):
        with pytest.raises(ConflictError, match="writer lock exists"):
            with WriterLock(path, {"writer_id": "w2"}):
                raise AssertionError("second writer entered lock")


def test_writer_lock_removes_new_file_when_identity_write_fails(tmp_path, monkeypatch):
    path = tmp_path / "writer.lock"

    def fail_dump(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(json, "dump", fail_dump)
    with pytest.raises(OSError, match="disk full"):
        with WriterLock(path, {"writer_id": "w1"}):
            raise AssertionError("lock should not be entered")
    assert not path.exists()


def test_object_write_is_content_addressed_and_non_overwriting(tmp_path):
    first = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    second = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    assert first == second
    with pytest.raises(ConflictError, match="object revision already exists"):
        write_object(tmp_path, "task", TASK_ID, 1, {"x": 2})


def test_object_write_rejects_matching_bytes_under_wrong_digest_name(tmp_path):
    data = canonical_bytes({"x": 1})
    directory = tmp_path / "objects" / "task" / TASK_ID
    directory.mkdir(parents=True)
    wrong = directory / f"00000001-{'0' * 64}.json"
    wrong.write_bytes(data)

    with pytest.raises(ConflictError, match="object revision already exists"):
        write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})

    canonical = directory / f"00000001-{sha256_hex(data)}.json"
    assert not canonical.exists()
    assert list(directory.glob(".*.publication-claim")) == []
    with pytest.raises(IntegrityError, match="filename hash mismatch"):
        ObjectStore(tmp_path).read("task", TASK_ID, 1)


def test_abandoned_object_claim_is_completed_by_later_writer(tmp_path):
    data = canonical_bytes({"x": 1})
    directory = tmp_path / "objects" / "task" / TASK_ID
    directory.mkdir(parents=True)
    claim = directory / ".00000001.publication-claim"
    claim.write_bytes(data)

    path = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})

    assert path.name == f"00000001-{sha256_hex(data)}.json"
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) == {"x": 1}
    assert not claim.exists()
    assert list(directory.glob(".*.tmp")) == []


def test_object_write_interruption_leaves_no_partial_revision_and_retry_recovers(tmp_path, monkeypatch):
    import research_system.store.objects as object_module

    def interrupt(_temporary):
        raise OSError("injected object publication interruption")

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", interrupt)
    with pytest.raises(OSError, match="publication interruption"):
        write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    directory = tmp_path / "objects" / "task" / TASK_ID
    assert list(directory.glob("00000001-*.json")) == []
    assert list(directory.glob(".*.tmp")) == []

    monkeypatch.setattr(
        object_module,
        "_after_object_temp_fsync",
        lambda _temporary: None,
    )
    path = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) == {"x": 1}
    assert path.is_file()


def test_object_target_link_interruption_is_recovered_on_retry(tmp_path, monkeypatch):
    import research_system.store.objects as object_module

    real_link = os.link
    interrupted = False

    def interrupt_target_link(source, target):
        nonlocal interrupted
        if Path(target).suffix == ".json" and not interrupted:
            interrupted = True
            raise OSError("injected target link interruption")
        return real_link(source, target)

    monkeypatch.setattr(object_module.os, "link", interrupt_target_link)
    with pytest.raises(OSError, match="target link interruption"):
        write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    directory = tmp_path / "objects" / "task" / TASK_ID
    claim = directory / ".00000001.publication-claim"
    assert claim.read_bytes() == canonical_bytes({"x": 1})
    assert list(directory.glob("00000001-*.json")) == []
    assert list(directory.glob(".*.tmp")) == []

    monkeypatch.setattr(object_module.os, "link", real_link)
    write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) == {"x": 1}
    assert len(list(directory.glob("00000001-*.json"))) == 1
    assert list(directory.glob(".*.tmp")) == []
    assert list(directory.glob(".*.publication-claim")) == []


def test_object_publication_fsyncs_directory_after_target_link(tmp_path, monkeypatch):
    import research_system.store.objects as object_module

    observations = []

    def observe(directory):
        target_exists = bool(list(directory.glob("00000001-*.json")))
        claim_exists = bool(list(directory.glob(".*.publication-claim")))
        observations.append((directory, target_exists, claim_exists))

    monkeypatch.setattr(object_module, "_fsync_directory", observe)
    path = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})

    assert (path.parent, True, True) in observations
    assert list(path.parent.glob(".*.tmp")) == []
    assert list(path.parent.glob(".*.publication-claim")) == []


def test_two_concurrent_identical_object_writers_publish_one_complete_revision(tmp_path, monkeypatch):
    import research_system.store.objects as object_module

    entered = threading.Barrier(3)
    release = threading.Event()

    def pause(_temporary):
        entered.wait(timeout=2)
        assert release.wait(2)

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", pause)
    results = []
    errors = []

    def write():
        try:
            results.append(write_object(tmp_path, "task", TASK_ID, 1, {"x": 1}))
        except Exception as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    writers = [threading.Thread(target=write) for _ in range(2)]
    for writer in writers:
        writer.start()
    entered.wait(timeout=2)
    release.set()
    for writer in writers:
        writer.join(timeout=2)
        assert not writer.is_alive()
    assert errors == []
    assert len(set(results)) == 1
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) == {"x": 1}
    directory = tmp_path / "objects" / "task" / TASK_ID
    assert list(directory.glob(".*.tmp")) == []
    assert list(directory.glob(".*.publication-claim")) == []


def test_two_concurrent_different_object_writers_publish_one_revision(tmp_path, monkeypatch):
    import research_system.store.objects as object_module

    entered = threading.Barrier(3)
    release = threading.Event()

    def pause(_temporary):
        entered.wait(timeout=2)
        assert release.wait(2)

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", pause)
    results = []
    errors = []

    def write(value):
        try:
            results.append(write_object(tmp_path, "task", TASK_ID, 1, value))
        except Exception as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    writers = [
        threading.Thread(target=write, args=({"x": 1},)),
        threading.Thread(target=write, args=({"x": 2},)),
    ]
    for writer in writers:
        writer.start()
    entered.wait(timeout=2)
    release.set()
    for writer in writers:
        writer.join(timeout=2)
        assert not writer.is_alive()
    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ConflictError)
    revisions = list((tmp_path / "objects" / "task" / TASK_ID).glob("00000001-*.json"))
    assert len(revisions) == 1
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) in ({"x": 1}, {"x": 2})
    directory = tmp_path / "objects" / "task" / TASK_ID
    assert list(directory.glob(".*.tmp")) == []
    assert list(directory.glob(".*.publication-claim")) == []


def test_object_read_normalizes_io_and_canonicalization_failures(tmp_path, monkeypatch):
    store = ObjectStore(tmp_path)
    path = store.write("task", TASK_ID, 1, {"x": 1})
    original_read_bytes = Path.read_bytes

    def fail_read(candidate):
        if candidate == path:
            raise OSError("unreadable")
        return original_read_bytes(candidate)

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    with pytest.raises(IntegrityError, match="unreadable"):
        store.read("task", TASK_ID, 1)

    monkeypatch.setattr(Path, "read_bytes", original_read_bytes)
    path.unlink()
    float_bytes = b'{"x":1.5}'
    from research_system.canonical import sha256_hex

    float_path = path.with_name(f"00000001-{sha256_hex(float_bytes)}.json")
    float_path.write_bytes(float_bytes)
    with pytest.raises(IntegrityError, match="canonical JSON"):
        store.read("task", TASK_ID, 1)


def test_batch_is_invisible_until_atomic_replace(tmp_path, monkeypatch):
    ledger = _catalogue_only_ledger(tmp_path)
    monkeypatch.setattr(
        ledger,
        "_publish",
        lambda source, target: (_ for _ in ()).throw(OSError("crash")),
    )
    with pytest.raises(OSError, match="crash"):
        ledger.append(
            [
                {
                    "event_type": "TaskCreated",
                    "stream_id": TASK_ID,
                    "schema_id": "ars://core/event",
                }
            ]
        )
    assert list((tmp_path / "events").rglob("*.jsonl")) == []


def test_batch_positions_and_hash_chain_are_contiguous(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    receipt = ledger.append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            }
        ]
    )
    events = list(ledger.iter_events())
    assert [item["global_position"] for item in events] == [1]
    assert events[0]["previous_event_hash"] == "0" * 64
    assert receipt["event_batch_id"] == events[0]["transaction_id"]


def test_default_ledger_rejects_append_without_explicit_schema_registry(tmp_path):
    ledger = EventLedger(tmp_path, project_id=PROJECT_ID)

    with pytest.raises(ArsError, match="explicit SchemaRegistry"):
        ledger.append([{"event_type": "TaskCreated", "stream_id": TASK_ID}])

    assert tuple(ledger.iter_batches()) == ()


def test_unbound_payload_backed_event_prefers_registered_full_schema(tmp_path):
    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    event_schema_id = "ars://test/event/StrictPayload"
    schemas = {
        "core_event.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "ars://core/event",
            "type": "object",
        },
        "strict_event.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": event_schema_id,
            "type": "object",
            "properties": {
                "schema_version": {"const": "1.0.0"},
                "payload": {
                    "type": "object",
                    "required": ["must_exist"],
                    "properties": {"must_exist": {"type": "string"}},
                },
            },
            "required": ["schema_version", "payload"],
        },
        "strict_payload.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{event_schema_id}/payload",
            "type": "object",
        },
    }
    for name, schema in schemas.items():
        (schema_root / name).write_bytes(canonical_bytes(schema))

    ledger = EventLedger(
        tmp_path / "control",
        project_id=PROJECT_ID,
        schemas=SchemaRegistry(schema_root),
    )
    incomplete = {
        "event_type": "StrictPayloadRecorded",
        "stream_id": TASK_ID,
        "schema_id": event_schema_id,
        "schema_version": "1.0.0",
        "payload": {},
    }

    with pytest.raises(SchemaError, match="must_exist"):
        ledger.append([incomplete])
    assert tuple(ledger.iter_batches()) == ()

    ledger.append(
        [
            {
                **incomplete,
                "payload": {"must_exist": "validated by the full event schema"},
            }
        ]
    )
    assert tuple(ledger.iter_events())[0]["payload"]["must_exist"] == ("validated by the full event schema")


@pytest.mark.parametrize(
    "provenance",
    [
        {},
        {"command_schema_id": "ars://core/command"},
    ],
)
def test_runtime_ledger_rejects_absent_or_partial_command_schema_provenance(
    tmp_path,
    provenance,
):
    ledger = EventLedger(
        tmp_path,
        project_id=PROJECT_ID,
        schemas=runtime_schema_registry(SCHEMAS),
    )

    with pytest.raises(ArsError, match="command schema"):
        ledger.append(
            [
                {
                    "event_type": "DispatchClaimed",
                    "stream_id": "dsp_01978abc-0003-7000-8000-000000000003",
                    "schema_id": "ars://core/event",
                    **provenance,
                }
            ]
        )

    assert tuple(ledger.iter_batches()) == ()


def test_runtime_ledger_rejects_unbound_full_only_event_schema(tmp_path):
    schemas = runtime_schema_registry(SCHEMAS)
    command_identity = schemas.resolve_identity("ars://core/command", "1.0.0")
    ledger = EventLedger(
        tmp_path,
        project_id=PROJECT_ID,
        schemas=schemas,
    )

    with pytest.raises(ArsError, match="inactive event schema"):
        ledger.append(
            [
                {
                    "event_type": "DispatchClaimed",
                    "stream_id": "dsp_01978abc-0003-7000-8000-000000000003",
                    "schema_id": "ars://core/event/DispatchClaimed",
                    "schema_version": "1.0.0",
                    "command_schema_id": command_identity.schema_id,
                    "command_schema_version": command_identity.schema_version,
                    "command_schema_sha256": command_identity.sha256,
                    "payload": {},
                }
            ]
        )

    assert tuple(ledger.iter_batches()) == ()


def test_replay_and_tail_follow_global_position_across_date_rollback(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    ledger.append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            }
        ]
    )
    ledger.append(
        [
            {
                "event_type": "ReadinessRequested",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            }
        ]
    )
    batches = sorted(ledger.events_root.rglob("*.jsonl"), key=lambda path: path.name)

    later_date = ledger.events_root / "2027" / "01"
    earlier_date = ledger.events_root / "2026" / "01"
    later_date.mkdir(parents=True, exist_ok=True)
    earlier_date.mkdir(parents=True, exist_ok=True)
    batches[0].replace(later_date / batches[0].name)
    batches[1].replace(earlier_date / batches[1].name)

    events = tuple(ledger.iter_events())
    assert [event["global_position"] for event in events] == [1, 2]
    assert [batch[0]["global_position"] for batch in ledger.iter_batches()] == [1, 2]
    assert ledger._persisted_tail() == (2, events[-1]["event_hash"])


def test_caller_cannot_override_recorded_at(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    with pytest.raises(ArsError, match="protected event fields"):
        ledger.append(
            [
                {
                    "event_type": "TaskCreated",
                    "stream_id": TASK_ID,
                    "recorded_at": "2000-01-01T00:00:00Z",
                }
            ]
        )


def test_receipt_write_repairs_partial_temporary_file(tmp_path):
    store = ReceiptStore(tmp_path)
    receipt = Receipt(
        status="accepted",
        command_id="cmd_01978abc-2001-7000-8000-000000002001",
        payload_hash="a" * 64,
        event_batch_id="txb_01978abc-2002-7000-8000-000000002002",
        observed_stream_version=1,
    )
    temporary = store.runtime_root / f"{receipt.command_id}.receipt.tmp"
    temporary.write_bytes(b"partial")
    assert store.write(receipt) == receipt
    assert not temporary.exists()
    assert store.load(receipt.command_id) == receipt
