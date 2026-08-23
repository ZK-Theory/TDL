import json
import os
from pathlib import Path
import stat
import threading

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.command.models import Receipt
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.layout import require_external_control_root
from research_system.store.ledger import EventLedger
from research_system.store import lock as lock_module
from research_system.store import durability as durability_module
from research_system.store.lock import (
    CompositeWriterLock,
    LockObservation,
    WriterLock,
    WriterLockContentionError,
    inspect_lock,
    process_instance_id,
    remove_stale_lock,
)
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


def test_second_composite_writer_lock_reports_existing_writer(tmp_path):
    root = tmp_path / "control"
    (root / "runtime").mkdir(parents=True)
    first = CompositeWriterLock(
        (root,),
        {"command_id": "cmd_composite-first-writer"},
    )
    second = CompositeWriterLock(
        (root,),
        {"command_id": "cmd_composite-second-writer"},
    )

    with first:
        with pytest.raises(ConflictError, match="writer lock exists"):
            with second:
                raise AssertionError("second composite writer entered lock")


def test_composite_writer_lock_maps_verified_windows_sharing_denial_to_writer_contention(tmp_path, monkeypatch):
    if os.name != "nt":
        pytest.skip("Windows sharing-denial classification control")
    root = tmp_path / "control"
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    candidate = CompositeWriterLock((root,), {"command_id": "cmd_composite-sharing-denial"})

    class SharingViolation(OSError):
        winerror = 32

    def deny_delete_share(*_args, **_kwargs):
        raise ConflictError("root delete protection denied") from SharingViolation("sharing violation")

    monkeypatch.setattr(lock_module, "_open_directory_anchor", deny_delete_share)
    acquired = lock_module._AcquiredMember(candidate._members[0])

    with WriterLock(runtime / "writer.lock", {"command_id": "cmd_live-contender"}):
        with pytest.raises(ConflictError, match="writer lock exists"):
            candidate._prepare_member(acquired)


@pytest.mark.parametrize("message", ["missing root", "reparse root", "identity changed"])
def test_composite_writer_lock_preserves_nonsharing_anchor_conflict_with_lock_residue(tmp_path, monkeypatch, message):
    root = tmp_path / "control"
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "writer.lock").write_text("residue", encoding="utf-8")
    candidate = CompositeWriterLock((root,), {"command_id": "cmd_composite-anchor-conflict"})

    def reject_anchor(*_args, **_kwargs):
        raise ConflictError(message)

    monkeypatch.setattr(lock_module, "_open_directory_anchor", reject_anchor)
    acquired = lock_module._AcquiredMember(candidate._members[0])

    with pytest.raises(ConflictError, match=message):
        candidate._prepare_member(acquired)


def test_fsync_directory_reraises_unexpected_open_error(tmp_path, monkeypatch):
    def fail_open(*_args, **_kwargs):
        raise OSError(5, "unexpected I/O failure")

    monkeypatch.setattr(durability_module.os, "open", fail_open)

    with pytest.raises(OSError, match="unexpected I/O failure"):
        durability_module.fsync_directory(tmp_path)


def test_fsync_directory_tolerates_documented_open_denial(tmp_path, monkeypatch):
    def deny_open(*_args, **_kwargs):
        raise OSError(13, "permission denied")

    monkeypatch.setattr(durability_module.os, "open", deny_open)
    durability_module.fsync_directory(tmp_path)


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
    followed_failed = False

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
        nonlocal followed_failed
        close_attempts.append(handle.name)
        if handle.name == "followed" and not followed_failed:
            followed_failed = True
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
    assert len(lock_module._WINDOWS_CLOSE_QUARANTINE) == 1
    lock_module._drain_windows_close_quarantine()
    assert handles[1].closed is True and not lock_module._WINDOWS_CLOSE_QUARANTINE


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
    followed_failed = False

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
        nonlocal followed_failed
        close_attempts.append(handle.name)
        if handle.name == "probe" and close_attempts.count("probe") == 1:
            raise RuntimeError("first close failure")
        if handle.name == "followed" and not followed_failed:
            followed_failed = True
            raise ValueError("second close failure")
        handle.closed = True

    monkeypatch.setattr(lock_module, "_windows_open_handle", fake_open)
    monkeypatch.setattr(lock_module, "_windows_file_attribute_tag", fake_attributes)
    monkeypatch.setattr(lock_module, "_windows_file_id", lambda _handle: identity)
    monkeypatch.setattr(lock_module, "_windows_final_path", lambda _handle: runtime)
    monkeypatch.setattr(lock_module, "_windows_close_handle", fake_close)

    with pytest.raises(RuntimeError, match="first close failure"):
        lock_module._open_windows_anchor(runtime, reject_reparse=True)

    assert close_attempts == ["probe", "followed"]
    assert handles[0].closed is False
    assert handles[1].closed is False
    assert len(lock_module._WINDOWS_CLOSE_QUARANTINE) == 2
    lock_module._drain_windows_close_quarantine()
    assert all(handle.closed for handle in handles)
    assert not lock_module._WINDOWS_CLOSE_QUARANTINE


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

    assert anchor._closed is False and len(lock_module._WINDOWS_CLOSE_QUARANTINE) == 1
    anchor.close()
    assert anchor._closed is True and not lock_module._WINDOWS_CLOSE_QUARANTINE
    assert len(close_attempts) == 2


def test_windows_anchor_deferred_effect_and_guard_closes_preserve_the_primary(tmp_path, monkeypatch):
    """remediation-red: a failed fence or guard close neither masks nor loses the operation."""
    if os.name != "nt":
        pytest.skip("Windows deferred anchor-close control")
    import research_system.store.lock as lock_module

    identity = lock_module.DirectoryIdentity("windows-file-id-v1", 1, b"cleanup".ljust(16, b"\0"))
    anchor = lock_module._DirectoryAnchor(
        identity, tmp_path, object(), lambda _handle: (identity, tmp_path), lambda _handle: None
    )
    fence = object()
    fence_closes = 0

    def close_fence(_handle):
        nonlocal fence_closes
        fence_closes += 1
        if fence_closes == 1:
            raise RuntimeError("fence close failure")

    monkeypatch.setattr(lock_module, "_windows_open_handle", lambda *_args, **_kwargs: fence)
    monkeypatch.setattr(lock_module, "_windows_anchor_refresh", lambda _handle: (identity, tmp_path))
    monkeypatch.setattr(lock_module, "_windows_close_handle", close_fence)
    with pytest.raises(ValueError, match="effect primary") as raised:
        with anchor._effect_final_path(tmp_path):
            raise ValueError("effect primary")
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert anchor.refresh() == (identity, tmp_path)
    assert fence_closes == 2

    real_close = os.close
    guard_closes = 0

    def close_guard(descriptor):
        nonlocal guard_closes
        guard_closes += 1
        if guard_closes == 1:
            raise RuntimeError("guard close failure")
        real_close(descriptor)

    monkeypatch.setattr(lock_module.os, "close", close_guard)
    with pytest.raises(ValueError, match="guard primary") as raised:
        with anchor.acquire_mutation_guard(".object-publication.guard"):
            raise ValueError("guard primary")
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert anchor.refresh() == (identity, tmp_path)
    assert guard_closes == 2


def test_posix_directory_anchor_propagates_delete_protection(tmp_path, monkeypatch):
    import research_system.store.lock as lock_module

    path = tmp_path / "control"
    sentinel = object()
    calls = []

    def open_posix(path_value, *, reject_reparse, delete_protect):
        calls.append((path_value, reject_reparse, delete_protect))
        return sentinel

    monkeypatch.setattr(lock_module, "_open_posix_anchor", open_posix)
    monkeypatch.setattr(lock_module.os, "name", "posix")

    assert lock_module._open_directory_anchor(path, delete_protect=True) is sentinel
    assert calls == [(path, False, True)]


@pytest.mark.parametrize("deleted_signal", ["link-count", "final-path"])
def test_posix_delete_protected_refresh_rejects_unlinked_anchor(monkeypatch, deleted_signal):
    import research_system.store.lock as lock_module

    observed = type(
        "Observed",
        (),
        {
            "st_mode": stat.S_IFDIR | 0o700,
            "st_dev": 1,
            "st_ino": 2,
            "st_nlink": 0 if deleted_signal == "link-count" else 1,
        },
    )()
    monkeypatch.setattr(lock_module.os, "fstat", lambda _descriptor: observed)
    monkeypatch.setattr(
        lock_module.os,
        "readlink",
        lambda _path: "/tmp/control (deleted)" if deleted_signal == "final-path" else "/tmp/control",
    )
    refresh = lock_module._posix_anchor_refresh_factory(
        Path("/tmp/control"),
        delete_protect=True,
    )

    with pytest.raises(ConflictError, match="unlinked|deleted"):
        refresh(17)


def test_posix_unprotected_refresh_preserves_deleted_path_compatibility(monkeypatch):
    import research_system.store.lock as lock_module

    observed = type(
        "Observed",
        (),
        {
            "st_mode": stat.S_IFDIR | 0o700,
            "st_dev": 1,
            "st_ino": 2,
            "st_nlink": 0,
        },
    )()
    monkeypatch.setattr(lock_module.os, "fstat", lambda _descriptor: observed)
    monkeypatch.setattr(lock_module.os, "readlink", lambda _path: "/tmp/control (deleted)")
    refresh = lock_module._posix_anchor_refresh_factory(
        Path("/tmp/control"),
        delete_protect=False,
    )

    identity, final_path = refresh(17)

    assert identity.scheme == "posix-dev-inode-v1"
    assert final_path == Path("/tmp/control")


def test_writer_lock_removes_new_file_when_identity_write_fails(tmp_path, monkeypatch):
    path = tmp_path / "writer.lock"

    def fail_link(*args, **kwargs):
        raise OSError("link failed")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(OSError, match="link failed"):
        with WriterLock(path, {"writer_id": "w1"}):
            raise AssertionError("lock should not be entered")
    assert not path.exists()
    assert not list(path.parent.glob(".writer.lock.*.tmp"))


def test_writer_lock_publishes_complete_process_instance_metadata(tmp_path):
    path = tmp_path / "writer.lock"
    with WriterLock(path, {"writer_id": "w1"}):
        raw = path.read_bytes()
        record = json.loads(raw)
        assert record["process_id"] == str(os.getpid())
        assert isinstance(record["process_instance_id"], str)
        assert canonical_bytes(record) == raw
        state, observed, inspected = inspect_lock(path)
        assert state == "live"
        assert isinstance(observed, LockObservation)
        assert observed.data == raw
        assert os.path.samestat(observed.identity, path.stat())
        assert inspected == record
    assert not path.exists()


def test_malformed_lock_is_bounded_and_never_reclaimed_without_identity(tmp_path):
    path = tmp_path / "writer.lock"
    path.write_bytes(b'{"process_id":"1"')

    state, observed, _ = inspect_lock(path)
    assert state == "malformed"
    assert isinstance(observed, LockObservation)
    assert observed.data == b'{"process_id":"1"'
    assert not remove_stale_lock(path, observed)
    assert path.exists()


def test_recycled_pid_is_stale_only_when_process_instance_differs(tmp_path):
    path = tmp_path / "writer.lock"
    current = process_instance_id(os.getpid())
    assert current is not None
    path.write_bytes(
        canonical_bytes(
            {
                "process_id": str(os.getpid()),
                "process_instance_id": "different-process-instance",
            }
        )
    )

    state, observed, _ = inspect_lock(path)
    assert state == "stale"
    assert observed is not None
    assert remove_stale_lock(path, observed)
    assert not path.exists()


def test_genuine_live_process_instance_is_not_reclaimed(tmp_path):
    path = tmp_path / "writer.lock"
    current = process_instance_id(os.getpid())
    assert current is not None
    path.write_bytes(
        canonical_bytes(
            {
                "process_id": str(os.getpid()),
                "process_instance_id": current,
                "operation": "other-owner",
            }
        )
    )

    state, observed, _ = inspect_lock(path)
    assert state == "live"
    assert observed is not None
    assert not remove_stale_lock(path, observed)
    assert path.exists()


def test_stale_dead_owner_is_reclaimed_after_process_revalidation(tmp_path, monkeypatch):
    path = tmp_path / "writer.lock"
    path.write_bytes(
        canonical_bytes(
            {
                "process_id": "919191",
                "process_instance_id": "dead-process-instance",
            }
        )
    )

    def no_process(_pid):
        return None

    def dead_process(_pid, _signal):
        raise ProcessLookupError

    monkeypatch.setattr(lock_module, "process_instance_id", no_process)
    monkeypatch.setattr(lock_module.os, "kill", dead_process)
    state, observed, _ = inspect_lock(path)
    assert state == "stale"
    assert observed is not None
    assert remove_stale_lock(path, observed)
    assert not path.exists()


def test_two_reclaimers_cannot_remove_a_fresh_winner(tmp_path, monkeypatch):
    path = tmp_path / "writer.lock"
    stale_pid = 919191
    path.write_bytes(
        canonical_bytes(
            {
                "process_id": str(stale_pid),
                "process_instance_id": "dead-process-instance",
            }
        )
    )
    real_instance_id = lock_module.process_instance_id
    real_kill = lock_module.os.kill

    def instance_id(pid):
        return None if pid == stale_pid else real_instance_id(pid)

    def kill(pid, signal):
        if pid == stale_pid:
            raise ProcessLookupError
        return real_kill(pid, signal)

    monkeypatch.setattr(lock_module, "process_instance_id", instance_id)
    monkeypatch.setattr(lock_module.os, "kill", kill)
    state, observed, _ = inspect_lock(path)
    assert state == "stale"
    assert observed is not None

    ready = threading.Event()
    release = threading.Event()
    gate_used = False
    gate_guard = threading.Lock()

    def pause_once() -> None:
        nonlocal gate_used
        with gate_guard:
            if gate_used:
                return
            gate_used = True
        ready.set()
        assert release.wait(2)

    def before_exact_delete(candidate):
        if Path(candidate) == path:
            pause_once()

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", before_exact_delete)
    results = []
    errors = []

    def reclaim():
        try:
            results.append(remove_stale_lock(path, observed))
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    first = threading.Thread(target=reclaim)
    first.start()
    assert ready.wait(2)

    assert remove_stale_lock(path, observed)
    fresh = WriterLock(path, {"writer_id": "fresh-winner"})
    fresh.__enter__()
    try:
        assert path.exists()
        release.set()
        first.join(timeout=2)
        assert not first.is_alive()
        assert errors == []
        assert results == [False]
        with pytest.raises(WriterLockContentionError, match="writer lock exists"):
            WriterLock(path, {"writer_id": "third-contender"}).__enter__()
    finally:
        fresh.__exit__(None, None, None)
    assert not path.exists()


def _recovery_service(root):
    service = object.__new__(CommandService)
    service.control_root = root
    service.recovery_lock_timeout_seconds = 0.05
    now = [0.0]
    service._monotonic = lambda: now[0]
    service._lock_wait = lambda seconds: now.__setitem__(0, now[0] + seconds)
    return service, now


def test_recovery_lock_revalidation_is_bounded_for_malformed_metadata(tmp_path):
    path = tmp_path / "runtime" / "writer.lock"
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"truncated"')
    service, now = _recovery_service(tmp_path)

    assert service._take_scoped_activation_recovery_lock({"command_id": "cmd_recovery"}) is None
    assert 0.05 <= now[0] < 0.06
    assert path.read_bytes() == b'{"truncated"'


def test_recovery_lock_does_not_steal_a_live_mismatched_owner(tmp_path):
    path = tmp_path / "runtime" / "writer.lock"
    path.parent.mkdir(parents=True)
    held = WriterLock(path, {"operation": "other-owner", "command_id": "cmd_other"})
    held.__enter__()
    try:
        service, now = _recovery_service(tmp_path)
        assert service._take_scoped_activation_recovery_lock({"command_id": "cmd_recovery"}) is None
        assert 0.05 <= now[0] < 0.06
        assert path.exists()
    finally:
        held.__exit__(None, None, None)


def test_recovery_lock_reclaims_a_recycled_pid_and_a_revalidated_dead_owner(tmp_path, monkeypatch):
    path = tmp_path / "runtime" / "writer.lock"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        canonical_bytes(
            {
                "operation": "other-owner",
                "command_id": "cmd_other",
                "process_id": str(os.getpid()),
                "process_instance_id": "recycled-instance",
            }
        )
    )
    service, _ = _recovery_service(tmp_path)
    recovered = service._take_scoped_activation_recovery_lock({"command_id": "cmd_recovery"})
    assert recovered is not None
    recovered.__exit__(None, None, None)
    assert not path.exists()

    dead_pid = 919191
    path.write_bytes(
        canonical_bytes(
            {
                "operation": "dead-owner",
                "command_id": "cmd_dead",
                "process_id": str(dead_pid),
                "process_instance_id": "dead-instance",
            }
        )
    )
    real_instance_id = lock_module.process_instance_id

    def instance_id(pid):
        return None if pid == dead_pid else real_instance_id(pid)

    real_kill = lock_module.os.kill

    def kill(pid, signal):
        if pid == dead_pid:
            raise ProcessLookupError
        return real_kill(pid, signal)

    monkeypatch.setattr(lock_module, "process_instance_id", instance_id)
    monkeypatch.setattr(lock_module.os, "kill", kill)
    recovered = service._take_scoped_activation_recovery_lock({"command_id": "cmd_recovery"})
    assert recovered is not None
    recovered.__exit__(None, None, None)
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
            self._posix_backend_entered = self.label == release_error_label
            self._posix_release_complete = False
            self.release_attempts = 0

        def __enter__(self):
            entered.append(self.label)
            if self.label == failure_label:
                raise RuntimeError("third lock acquisition failed")
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            exited.append(self.label)
            if self.label == release_error_label:
                self.release_attempts += 1
                if self.release_attempts <= 3:
                    raise ValueError("second lock release failed")
                self._posix_release_complete = True
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
    assert exited.count(release_error_label) == 3
    assert isinstance(raised.value.__cause__, ValueError)
    assert len(candidate._active_members) == len(candidate._acquired) == 1
    candidate.__exit__(None, None, None)
    assert exited.count(release_error_label) == 4
    assert candidate._active_members == candidate._acquired == []
    assert len(closed_anchors) == 2 * len(ordered_members)


def test_object_write_is_content_addressed_and_non_overwriting(tmp_path):
    first = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    second = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})
    assert first == second
    with pytest.raises(ConflictError, match="object revision already exists"):
        write_object(tmp_path, "task", TASK_ID, 1, {"x": 2})


@pytest.mark.parametrize("operation", ("revision_exists", "latest_revision", "read", "rollback_new_revision"))
def test_object_public_operations_never_preflight_the_lexical_object_directory(tmp_path, monkeypatch, operation):
    """remediation-red: reads and rollback start from an anchored generation, not ``Path.exists``."""
    store = ObjectStore(tmp_path)
    value = {"x": 1}
    store.write("task", TASK_ID, 1, value)
    directory = tmp_path / "objects" / "task" / TASK_ID
    real_exists = Path.exists

    def reject_lexical_object_preflight(candidate):
        if candidate == directory:
            raise AssertionError("object operation used the lexical directory before anchoring it")
        return real_exists(candidate)

    monkeypatch.setattr(Path, "exists", reject_lexical_object_preflight)

    if operation == "revision_exists":
        assert store.revision_exists("task", TASK_ID, 1)
    elif operation == "latest_revision":
        assert store.latest_revision("task", TASK_ID) == 1
    elif operation == "read":
        assert store.read("task", TASK_ID, 1) == value
    else:
        store.rollback_new_revision("task", TASK_ID, 1, value, existed_before=False)
        assert not list(directory.glob("00000001-*.json"))


@pytest.mark.parametrize("shape", ("missing-root", "root-only", "objects-only", "kind-only"))
def test_object_public_operations_preserve_missing_object_contracts(tmp_path, shape):
    """remediation-red: anchored traversal preserves the preflight absence contracts."""
    root = tmp_path / "control"
    if shape != "missing-root":
        root.mkdir()
    if shape in {"objects-only", "kind-only"}:
        (root / "objects").mkdir()
    if shape == "kind-only":
        (root / "objects" / "task").mkdir()
    store = ObjectStore(root)

    assert not store.revision_exists("task", TASK_ID, 1)
    assert store.latest_revision("task", TASK_ID) is None
    store.rollback_new_revision("task", TASK_ID, 1, {"x": 1}, existed_before=False)
    with pytest.raises(IntegrityError, match="object revision must resolve exactly once"):
        store.read("task", TASK_ID, 1)


def test_object_write_preserves_primary_error_when_anchor_close_also_fails(tmp_path, monkeypatch):
    """remediation-red: directory cleanup cannot replace the write outcome."""
    import research_system.store.objects as object_module

    def fail_write(*_args, **_kwargs):
        raise ConflictError("injected primary object write failure")

    class Anchor:
        def __init__(self, final_path, child=None, *, fail_close=False):
            self.final_path = final_path
            self.child = child
            self.fail_close = fail_close
            self.closed = False

        def open_member_directory(self, _name, **_kwargs):
            assert self.child is not None
            return self.child

        def acquire_mutation_guard(self, _name):
            class Guard:
                def __enter__(self):
                    return object()

                def __exit__(self, *_args):
                    return False

            return Guard()

        def close(self):
            self.closed = True
            if self.fail_close:
                raise OSError("injected object anchor close failure")

    object_anchor = Anchor(tmp_path / "objects" / "task" / TASK_ID, fail_close=True)
    kind_anchor = Anchor(tmp_path / "objects" / "task", object_anchor)
    objects_anchor = Anchor(tmp_path / "objects", kind_anchor)
    root_anchor = Anchor(tmp_path, objects_anchor)

    monkeypatch.setattr(object_module, "_write_object_in_directory", fail_write)
    monkeypatch.setattr(object_module, "open_registered_root_anchor", lambda *_args, **_kwargs: root_anchor)

    with pytest.raises(ConflictError, match="primary object write failure") as raised:
        write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})

    assert all(anchor.closed for anchor in (object_anchor, kind_anchor, objects_anchor, root_anchor))
    assert isinstance(raised.value.__cause__, OSError)
    assert "anchor close failure" in str(raised.value.__cause__)


def test_object_write_creates_staging_file_with_least_privilege_mode(tmp_path, monkeypatch):
    """remediation-red: private staged content is never created with process defaults."""
    import research_system.store.objects as object_module

    original_open = object_module.os.open
    staging_modes: list[int | None] = []
    target_name = f"00000001-{sha256_hex(canonical_bytes({'x': 1}))}.json"

    def record_staging_mode(path, flags, *args, **kwargs):
        candidate = Path(path)
        if (
            candidate.name.startswith(f".{target_name}.")
            and candidate.name.endswith(".tmp")
            and flags & os.O_CREAT
            and flags & os.O_EXCL
        ):
            staging_modes.append(args[0] if args else kwargs.get("mode"))
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(object_module.os, "open", record_staging_mode)

    write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})

    assert staging_modes == [0o600]


def test_object_rollback_reports_concurrently_removed_revision_as_changed(tmp_path, monkeypatch):
    """remediation-red: a listed revision removed before proof is not unreadable."""
    store = ObjectStore(tmp_path)
    value = {"x": 1}
    path = store.write("task", TASK_ID, 1, value)
    removed = False

    def remove_after_ownership_proof(candidate):
        nonlocal removed
        if str(candidate).endswith(path.name) and not removed:
            removed = True
            candidate.unlink()

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", remove_after_ownership_proof)

    with pytest.raises(IntegrityError, match="cannot roll back a changed object revision"):
        store.rollback_new_revision("task", TASK_ID, 1, value, existed_before=False)

    assert removed


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


def test_persisted_final_claim_and_temp_crash_recovers_before_a_later_conflicting_write(tmp_path):
    """remediation-red: an idempotent restart drains aliases from a post-final crash."""
    data = canonical_bytes({"x": 1})
    directory = tmp_path / "objects" / "task" / TASK_ID
    directory.mkdir(parents=True)
    target = f"00000001-{sha256_hex(data)}.json"
    temporary = directory / f".{target}.crashed.tmp"
    claim = directory / ".00000001.publication-claim"
    final = directory / target
    temporary.write_bytes(data)
    os.link(temporary, claim, follow_symlinks=False)
    os.link(claim, final, follow_symlinks=False)

    store = ObjectStore(tmp_path)
    store.write("task", TASK_ID, 1, {"x": 1})
    assert not list(directory.glob(".*.tmp"))
    assert not claim.exists()
    store.rollback_new_revision("task", TASK_ID, 1, {"x": 1}, existed_before=False)
    assert not store.revision_exists("task", TASK_ID, 1)
    assert store.write("task", TASK_ID, 1, {"x": 2}).is_file()


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

    def interrupt_target_link(source, target, *args, **kwargs):
        nonlocal interrupted
        if Path(target).suffix == ".json" and not interrupted:
            interrupted = True
            raise OSError("injected target link interruption")
        return real_link(source, target, *args, **kwargs)

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
    import research_system.store.lock as lock_module

    observations = []
    real_fsync = lock_module._DirectoryAnchor._fsync_directory

    def observe(anchor, directory):
        target_exists = bool(list(directory.glob("00000001-*.json")))
        claim_exists = bool(list(directory.glob(".*.publication-claim")))
        observations.append((directory, target_exists, claim_exists))
        return real_fsync(anchor, directory)

    monkeypatch.setattr(lock_module._DirectoryAnchor, "_fsync_directory", observe)
    path = write_object(tmp_path, "task", TASK_ID, 1, {"x": 1})

    def normalise_path(candidate):
        value = os.path.normcase(os.fspath(candidate))
        return value.removeprefix("\\\\?\\")

    assert any(
        normalise_path(directory) == normalise_path(path.parent) and target_exists
        for directory, target_exists, _claim_exists in observations
    )
    assert list(path.parent.glob(".*.tmp")) == []
    assert list(path.parent.glob(".*.publication-claim")) == []


def test_two_concurrent_identical_object_writers_publish_one_complete_revision(tmp_path, monkeypatch):
    import research_system.store.objects as object_module

    first_staged = threading.Event()
    second_entered = threading.Event()
    second_staged = threading.Event()
    stage_count = 0
    stage_lock = threading.Lock()

    def pause(_temporary):
        nonlocal stage_count
        if os.name == "nt":
            with stage_lock:
                stage_count += 1
                first = stage_count == 1
            if first:
                first_staged.set()
                assert second_entered.wait(2)
                assert not second_staged.wait(0.05)
            else:
                second_staged.set()

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", pause)
    results = []
    errors = []

    def write(second=False):
        try:
            if second:
                second_entered.set()
            results.append(write_object(tmp_path, "task", TASK_ID, 1, {"x": 1}))
        except Exception as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    first_writer = threading.Thread(target=write)
    second_writer = threading.Thread(target=write, args=(True,))
    first_writer.start()
    if os.name == "nt":
        assert first_staged.wait(2)
    second_writer.start()
    for writer in (first_writer, second_writer):
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

    entered = threading.Barrier(2)
    release = threading.Event()

    def pause(_temporary):
        if os.name == "nt":
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
    if os.name == "nt":
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
    import research_system.store.objects as object_module

    store = ObjectStore(tmp_path)
    path = store.write("task", TASK_ID, 1, {"x": 1})
    original_open = object_module.os.open

    def normalise_path(candidate):
        value = object_module.os.path.normcase(object_module.os.fspath(candidate))
        return value.removeprefix("\\\\?\\")

    def fail_open(candidate, *args, **kwargs):
        if candidate == path.name and kwargs.get("dir_fd") is not None:
            raise OSError("unreadable")
        if normalise_path(candidate) == normalise_path(path):
            raise OSError("unreadable")
        return original_open(candidate, *args, **kwargs)

    monkeypatch.setattr(object_module.os, "open", fail_open)
    with pytest.raises(IntegrityError, match="unreadable"):
        store.read("task", TASK_ID, 1)

    monkeypatch.setattr(object_module.os, "open", original_open)
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


def test_raw_prefix_sha256_stops_after_first_batch_beyond_cut(tmp_path, monkeypatch):
    ledger = _catalogue_only_ledger(tmp_path)
    for index in range(3):
        ledger.append(
            [
                {
                    "event_type": "TaskCreated",
                    "stream_id": TASK_ID,
                    "schema_id": "ars://core/event",
                    "payload": {"index": index},
                }
            ]
        )
    paths = ledger._batch_paths()
    expected = sha256_hex(paths[0].read_bytes())
    ledger.snapshot()
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path):
        if path == paths[2]:
            raise AssertionError("raw prefix read a batch after the cut")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert ledger.raw_prefix_sha256(1) == expected


def test_raw_prefix_sha256_rejects_a_cut_inside_atomic_batch(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    ledger.append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            },
            {
                "event_type": "TaskAmended",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            },
        ]
    )

    with pytest.raises(ConflictError, match="splits one atomic event batch"):
        ledger.raw_prefix_sha256(1)


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

    with pytest.raises(ArsError, match="unbound event producer: DispatchClaimed from LedgerInternalAppend"):
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


def test_runtime_ledger_rejects_wrong_producer_for_active_full_only_event_schema(tmp_path):
    schemas = runtime_schema_registry(SCHEMAS)
    command_identity = schemas.resolve_identity("ars://core/command", "1.0.0")
    ledger = EventLedger(
        tmp_path,
        project_id=PROJECT_ID,
        schemas=schemas,
    )

    with pytest.raises(ArsError, match="unbound event producer"):
        ledger.append(
            [
                {
                    "event_type": "DispatchClaimed",
                    "stream_id": "dsp_01978abc-0003-7000-8000-000000000003",
                    "schema_id": "ars://core/event/DispatchClaimed",
                    "schema_version": "1.0.0",
                    "command_type": "WrongDispatchProducer",
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


def test_replay_rejects_split_multi_event_batch_across_files(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    ledger.append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            },
            {
                "event_type": "ReadinessRequested",
                "stream_id": TASK_ID,
                "schema_id": "ars://core/event",
            },
        ]
    )

    batch = next(ledger.events_root.rglob("*.jsonl"))
    lines = [line for line in batch.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2

    batch.unlink()
    left = batch.with_name(batch.name.replace(".jsonl", "-left.jsonl"))
    right = batch.with_name(batch.name.replace(".jsonl", "-right.jsonl"))
    left.write_text(lines[0] + "\n", encoding="utf-8")
    right.write_text(lines[1] + "\n", encoding="utf-8")

    with pytest.raises(ArsError, match="transaction_count does not match physical line count"):
        list(ledger.iter_events())


def test_iter_batches_rejects_reordered_physical_transaction_indexes(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    ledger.append(
        [
            {"event_type": "TaskCreated", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
            {"event_type": "ReadinessRequested", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
        ]
    )
    batch = next(ledger.events_root.rglob("*.jsonl"))
    lines = [line for line in batch.read_text(encoding="utf-8").splitlines() if line.strip()]
    batch.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")

    with pytest.raises(ArsError, match="invalid transaction_index sequence"):
        next(ledger.iter_batches())


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    (
        ("transaction_index", True, "invalid transaction_index sequence"),
        ("transaction_index", 1.0, "invalid transaction_index sequence"),
        ("transaction_count", 2.0, "transaction_count does not match physical line count"),
    ),
    ids=["boolean-index", "float-index", "float-count"],
)
def test_iter_batches_rejects_non_integer_transaction_envelope_values(tmp_path, field, value, expected_error):
    ledger = _catalogue_only_ledger(tmp_path)
    ledger.append(
        [
            {"event_type": "TaskCreated", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
            {"event_type": "ReadinessRequested", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
        ]
    )
    batch = next(ledger.events_root.rglob("*.jsonl"))
    events = [json.loads(line) for line in batch.read_text(encoding="utf-8").splitlines() if line.strip()]
    events[0][field] = value
    batch.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(ArsError, match=expected_error):
        next(ledger.iter_batches())


def test_iter_batches_rejects_mixed_t2_and_core_transaction_conventions(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)
    ledger.append(
        [
            {"event_type": "TaskCreated", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
            {"event_type": "ReadinessRequested", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
        ]
    )
    batch = next(ledger.events_root.rglob("*.jsonl"))
    events = [json.loads(line) for line in batch.read_text(encoding="utf-8").splitlines() if line.strip()]
    events[0]["schema_id"] = "ars://wp6-2/t2/event/CostGrantIssued"
    batch.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(ArsError, match="mixed transaction_index conventions"):
        next(ledger.iter_batches())


def test_append_rejects_mixed_t2_and_core_transaction_conventions_before_publication(tmp_path):
    ledger = _catalogue_only_ledger(tmp_path)

    with pytest.raises(ArsError, match="must not mix transaction_index conventions"):
        ledger.append(
            [
                {"event_type": "TaskCreated", "stream_id": TASK_ID, "schema_id": "ars://core/event"},
                {
                    "event_type": "CostGrantIssued",
                    "stream_id": TASK_ID,
                    "schema_id": "ars://wp6-2/t2/event/CostGrantIssued",
                },
            ]
        )

    assert tuple(ledger.iter_batches()) == ()


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
