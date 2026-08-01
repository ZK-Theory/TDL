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
from research_system.store.lock import CompositeWriterLock, WriterLock
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


def test_composite_writer_lock_rejects_absent_root_without_state(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(ConflictError, match="existing directory"):
        CompositeWriterLock(
            (missing,),
            {"command_id": "cmd_composite-missing-root"},
        )

    assert not missing.exists()
    assert not (missing / "runtime").exists()
    assert not (missing / "runtime" / "writer.lock").exists()


def test_composite_writer_lock_exposes_only_a_live_lease(tmp_path):
    root = tmp_path / "control"
    (root / "runtime").mkdir(parents=True)
    candidate = CompositeWriterLock(
        (root,),
        {"command_id": "cmd_composite-live-lease"},
    )

    with pytest.raises(ConflictError, match="lease is not live"):
        candidate.locked_root(root)

    with candidate as entered:
        locked = entered.locked_root(root)
        assert locked.identity.scheme in {"windows-file-id-v1", "posix-dev-inode-v1"}
        assert locked.aliases == (root,)
        assert entered.paths == (locked.runtime_final_path / "writer.lock",)

    assert candidate.paths == ()
    with pytest.raises(ConflictError, match="lease is not live"):
        candidate.locked_root(root)


def test_locked_root_capability_is_private_shared_and_retry_scoped(tmp_path):
    from copy import copy

    from research_system.store.lock import LockedRoot

    root = tmp_path / "capability-root"
    foreign_root = tmp_path / "foreign-root"
    (root / "runtime").mkdir(parents=True)
    (foreign_root / "runtime").mkdir(parents=True)
    candidate = CompositeWriterLock(
        (root,),
        {"command_id": "cmd_composite-capability"},
    )
    foreign_candidate = CompositeWriterLock(
        (foreign_root,),
        {"command_id": "cmd_composite-foreign-capability"},
    )

    with candidate as entered:
        live = entered.locked_root(root)
        shallow_copy = copy(live)
        assert entered._validate_locked_root(shallow_copy) is shallow_copy
        with pytest.raises(TypeError, match="lock-created"):
            LockedRoot(
                identity=live.identity,
                final_path=live.final_path,
                runtime_identity=live.runtime_identity,
                runtime_final_path=live.runtime_final_path,
                aliases=live.aliases,
                _lease_token=object(),
            )
        with foreign_candidate as foreign_entered:
            with pytest.raises(ConflictError, match="lease|member"):
                entered._validate_locked_root(foreign_entered.locked_root(foreign_root))

    with pytest.raises(ConflictError, match="lease|member"):
        candidate._validate_locked_root(live)
    with pytest.raises(ConflictError, match="lease|member"):
        candidate._validate_locked_root(shallow_copy)

    first_token = live._lease_token
    with candidate as retried:
        retried_live = retried.locked_root(root)
        assert retried_live._lease_token is not first_token
        with pytest.raises(ConflictError, match="lease|member"):
            retried._validate_locked_root(live)


@pytest.mark.parametrize("runtime_kind", ["missing", "file", "reparse"])
def test_composite_writer_lock_rejects_invalid_runtime_without_state(tmp_path, runtime_kind):
    root = tmp_path / f"control-{runtime_kind}"
    root.mkdir()
    runtime = root / "runtime"
    if runtime_kind == "file":
        runtime.write_text("not a directory", encoding="utf-8")
    elif runtime_kind == "reparse":
        target = tmp_path / f"runtime-target-{runtime_kind}"
        target.mkdir()
        try:
            runtime.symlink_to(target, target_is_directory=True)
        except OSError:
            pytest.skip("directory reparse creation unavailable on this host")

    with pytest.raises(ConflictError, match="directory|reparse"):
        CompositeWriterLock(
            (root,),
            {"command_id": f"cmd_composite-runtime-{runtime_kind}"},
        )

    assert not (root / "runtime" / "writer.lock").exists()


def test_composite_writer_lock_fails_closed_when_windows_identity_is_unavailable(
    tmp_path,
    monkeypatch,
):
    if os.name != "nt":
        pytest.skip("Windows identity backend control")
    import research_system.store.lock as lock_module

    root = tmp_path / "control-identity"
    (root / "runtime").mkdir(parents=True)

    def unavailable(_handle):
        raise OSError("identity unavailable")

    monkeypatch.setattr(lock_module, "_windows_file_id", unavailable)
    with pytest.raises(ConflictError):
        CompositeWriterLock(
            (root,),
            {"command_id": "cmd_composite-identity-unavailable"},
        )
    assert not (root / "runtime" / "writer.lock").exists()


def test_windows_runtime_anchor_rejects_inside_open_identity_swap_without_publication(
    tmp_path,
    monkeypatch,
):
    if os.name != "nt":
        pytest.skip("Windows directory-anchor race control")
    import research_system.store.lock as lock_module

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    ordinary_identity = lock_module.DirectoryIdentity(
        "windows-file-id-v1",
        1,
        b"ordinary-runtime".ljust(16, b"\0"),
    )
    followed_identity = lock_module.DirectoryIdentity(
        "windows-file-id-v1",
        1,
        b"junction-target".ljust(16, b"\0"),
    )
    directory_attribute = lock_module._FILE_ATTRIBUTE_DIRECTORY
    phase = 0
    handles = []

    class FakeHandle:
        def __init__(self, name, identity, final_path):
            self.name = name
            self.identity = identity
            self.final_path = final_path
            self.closed = False

    def fake_open(path, *, open_reparse_point, delete_protect=False):
        nonlocal phase
        assert path == runtime
        assert not delete_protect
        if open_reparse_point:
            if phase == 0:
                phase = 1
                handle = FakeHandle("probe-before", ordinary_identity, runtime)
            elif phase == 2:
                phase = 3
                handle = FakeHandle("probe-after", ordinary_identity, runtime)
            else:  # pragma: no cover - the phase assertions are the control
                raise AssertionError(f"unexpected no-follow phase: {phase}")
        else:
            assert phase == 1
            phase = 2
            handle = FakeHandle("followed", followed_identity, tmp_path / "junction-target")
        handles.append(handle)
        return handle

    def fake_attributes(handle):
        assert not handle.closed
        return directory_attribute, 0

    def fake_close(handle):
        assert not handle.closed
        handle.closed = True

    monkeypatch.setattr(lock_module, "_windows_open_handle", fake_open)
    monkeypatch.setattr(lock_module, "_windows_file_attribute_tag", fake_attributes)
    monkeypatch.setattr(lock_module, "_windows_file_id", lambda handle: handle.identity)
    monkeypatch.setattr(lock_module, "_windows_final_path", lambda handle: handle.final_path)
    monkeypatch.setattr(lock_module, "_windows_close_handle", fake_close)

    published = []
    with pytest.raises(ConflictError, match="identity"):
        published.append(lock_module._open_windows_anchor(runtime, reject_reparse=True))

    assert published == []
    assert phase == 2
    assert all(handle.closed for handle in handles)


def test_windows_anchor_close_failure_attempts_both_handles_and_preserves_primary_error(
    tmp_path,
    monkeypatch,
):
    if os.name != "nt":
        pytest.skip("Windows directory-anchor cleanup control")
    import research_system.store.lock as lock_module

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    identity = lock_module.DirectoryIdentity(
        "windows-file-id-v1",
        1,
        b"ordinary-runtime".ljust(16, b"\0"),
    )
    followed_identity = lock_module.DirectoryIdentity(
        "windows-file-id-v1",
        1,
        b"changed-runtime".ljust(16, b"\0"),
    )
    handles = []
    close_attempts = []

    class FakeHandle:
        def __init__(self, name):
            self.name = name
            self.closed = False

    def fake_open(path, *, open_reparse_point, delete_protect=False):
        assert path == runtime
        if open_reparse_point:
            assert not delete_protect
            handle = FakeHandle("probe")
        else:
            assert not delete_protect
            handle = FakeHandle("followed")
        handles.append(handle)
        return handle

    def fake_attributes(handle):
        assert not handle.closed
        return lock_module._FILE_ATTRIBUTE_DIRECTORY, 0

    def fake_close(handle):
        close_attempts.append(handle.name)
        if handle.name == "followed":
            raise RuntimeError("close failure")
        handle.closed = True

    monkeypatch.setattr(lock_module, "_windows_open_handle", fake_open)
    monkeypatch.setattr(lock_module, "_windows_file_attribute_tag", fake_attributes)
    monkeypatch.setattr(
        lock_module,
        "_windows_file_id",
        lambda handle: identity if handle.name == "probe" else followed_identity,
    )
    monkeypatch.setattr(lock_module, "_windows_final_path", lambda _handle: runtime)
    monkeypatch.setattr(lock_module, "_windows_close_handle", fake_close)

    with pytest.raises(ConflictError, match="identity") as raised:
        lock_module._open_windows_anchor(runtime, reject_reparse=True)

    assert isinstance(raised.value.__cause__, RuntimeError)
    assert str(raised.value.__cause__) == "close failure"
    assert close_attempts == ["probe", "followed"]
    assert handles[0].closed is True
    assert handles[1].closed is False


def test_windows_anchor_close_failure_without_primary_surfaces_first_error(
    tmp_path,
    monkeypatch,
):
    if os.name != "nt":
        pytest.skip("Windows directory-anchor cleanup control")
    import research_system.store.lock as lock_module

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    identity = lock_module.DirectoryIdentity(
        "windows-file-id-v1",
        1,
        b"ordinary-runtime".ljust(16, b"\0"),
    )
    handles = []
    close_attempts = []

    class FakeHandle:
        def __init__(self, name):
            self.name = name
            self.closed = False

    def fake_open(path, *, open_reparse_point, delete_protect=False):
        assert path == runtime
        if open_reparse_point:
            assert not delete_protect
            handle = FakeHandle("probe")
        else:
            assert not delete_protect
            handle = FakeHandle("followed")
        handles.append(handle)
        return handle

    def fake_attributes(handle):
        assert not handle.closed
        return lock_module._FILE_ATTRIBUTE_DIRECTORY, 0

    def fake_close(handle):
        close_attempts.append(handle.name)
        if handle.name == "probe" and close_attempts.count("probe") == 1:
            raise RuntimeError("first close failure")
        if handle.name == "followed":
            raise ValueError("second close failure")
        handle.closed = True

    monkeypatch.setattr(lock_module, "_windows_open_handle", fake_open)
    monkeypatch.setattr(lock_module, "_windows_file_attribute_tag", fake_attributes)
    monkeypatch.setattr(lock_module, "_windows_file_id", lambda _handle: identity)
    monkeypatch.setattr(lock_module, "_windows_final_path", lambda _handle: runtime)
    monkeypatch.setattr(lock_module, "_windows_close_handle", fake_close)

    with pytest.raises(RuntimeError, match="first close failure"):
        lock_module._open_windows_anchor(runtime, reject_reparse=True)

    assert close_attempts == ["probe", "probe", "followed"]
    assert handles[0].closed is True
    assert handles[1].closed is False


def test_directory_anchor_close_failure_retains_live_handle_for_retry(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows directory-handle cleanup control")
    import research_system.store.lock as lock_module

    identity = lock_module.DirectoryIdentity(
        "windows-file-id-v1",
        1,
        b"retryable-runtime".ljust(16, b"\0"),
    )
    handle = object()
    close_attempts = []

    def close(_handle):
        close_attempts.append(True)
        if len(close_attempts) == 1:
            raise RuntimeError("close failure")

    anchor = lock_module._DirectoryAnchor(
        identity,
        tmp_path,
        handle,
        lambda _handle: (identity, tmp_path),
        close,
    )

    with pytest.raises(RuntimeError, match="close failure"):
        anchor.close()

    assert anchor._closed is False
    anchor.close()
    assert anchor._closed is True
    assert len(close_attempts) == 2


def test_writer_lock_removes_new_file_when_identity_write_fails(tmp_path, monkeypatch):
    path = tmp_path / "writer.lock"

    def fail_dump(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(json, "dump", fail_dump)
    with pytest.raises(OSError, match="disk full"):
        with WriterLock(path, {"writer_id": "w1"}):
            raise AssertionError("lock should not be entered")
    assert not path.exists()


def test_composite_writer_lock_cleans_all_acquired_siblings_after_release_failure(tmp_path, monkeypatch):
    import research_system.store.lock as lock_module

    roots = tuple(tmp_path / name for name in ("a", "b", "c"))
    for root in roots:
        (root / "runtime").mkdir(parents=True)
    candidate = CompositeWriterLock(
        roots,
        {"command_id": "cmd_composite-cleanup"},
    )
    ordered_members = tuple(candidate._members)
    ordered_labels = tuple(member.representative.final_path.name for member in ordered_members)
    failure_label = ordered_labels[-1]
    release_error_label = ordered_labels[-2]
    entered: list[str] = []
    exited: list[str] = []
    closed_anchors = []

    original_close_anchor = lock_module._close_anchor

    def observed_close_anchor(anchor):
        if anchor is not None:
            closed_anchors.append(anchor.final_path)
        return original_close_anchor(anchor)

    monkeypatch.setattr(lock_module, "_close_anchor", observed_close_anchor)

    class FakeLock:
        def __init__(self, path: Path, _identity: dict[str, str]) -> None:
            self.label = path.parent.parent.name

        def __enter__(self):
            entered.append(self.label)
            if self.label == failure_label:
                raise RuntimeError("third lock acquisition failed")
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            exited.append(self.label)
            if self.label == release_error_label:
                raise ValueError("second lock release failed")
            return False

    candidate = CompositeWriterLock(
        roots,
        {"command_id": "cmd_composite-cleanup"},
        lock_factory=FakeLock,
    )
    closed_anchors.clear()
    with pytest.raises(RuntimeError, match="third lock acquisition failed") as raised:
        candidate.__enter__()

    assert entered == list(ordered_labels)
    assert exited == list(reversed(ordered_labels[:-1]))
    assert isinstance(raised.value.__cause__, ValueError)
    assert candidate._acquired == []
    expected_anchor_cleanup = []
    for member in reversed(ordered_members):
        expected_anchor_cleanup.extend([member.representative.runtime_final_path, member.representative.final_path])
    assert closed_anchors == expected_anchor_cleanup
    candidate.__exit__(None, None, None)
    assert exited == list(reversed(ordered_labels[:-1]))


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
