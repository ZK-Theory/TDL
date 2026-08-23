from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.store.anchor import (
    DirectoryIdentity,
    DirectoryMutationGuard,
    DirectoryTransaction,
    TRANSACTION_GUARD_NAME,
    drain_close_quarantine,
    open_registered_root_anchor,
)
from research_system.store.objects import ObjectStore


TASK_ID = "tsk_00000000-0000-7000-8000-000000000901"


def _object_directory(root: Path) -> Path:
    return root / "objects" / "task" / TASK_ID


def _object_target(root: Path, value: object) -> Path:
    data = canonical_bytes(value)
    return _object_directory(root) / f"00000001-{sha256_hex(data)}.json"


def _partial_stage_injection(monkeypatch, *, trigger: str):
    """Fail after O_EXCL ownership is recorded, before fstat/write."""

    import research_system.store.anchor as anchor_module

    stage_hook = anchor_module._after_stage_opened
    injected = False

    def fail_after_stage(_name, descriptor, *args, **kwargs):
        nonlocal injected
        if not injected:
            injected = True
            os.write(descriptor, b"partial-stage")
            raise ConflictError(trigger)
        return stage_hook(_name, descriptor, *args, **kwargs)

    monkeypatch.setattr(anchor_module, "_after_stage_opened", fail_after_stage)
    return lambda: injected


def test_object_final_link_receipt_precedes_failure_and_retry_adopts(tmp_path: Path, monkeypatch) -> None:
    """A successful link is committed even when its later identity read fails."""

    import research_system.store.anchor as anchor_module

    value = {"value": "final-link-retry"}
    data = canonical_bytes(value)
    target = _object_target(tmp_path, value)
    original_identity = anchor_module._DirectoryAnchor._member_identity
    original_link = DirectoryTransaction._link_with_immediate_receipt
    active_transaction: DirectoryTransaction | None = None
    failed = False
    receipt_seen = False

    def observe_link(transaction, stage, final_name, guard):
        nonlocal active_transaction
        active_transaction = transaction
        return original_link(transaction, stage, final_name, guard)

    def fail_destination_identity(anchor, name, final_path):
        nonlocal failed, receipt_seen
        if name == target.name and target.exists() and active_transaction is not None and not failed:
            failed = True
            receipt_seen = any(
                effect.disposition == "linked" and effect.name == target.name for effect in active_transaction.effects
            )
            assert receipt_seen, "link receipt must precede destination identity read"
            raise OSError("injected destination identity-read failure")
        return original_identity(anchor, name, final_path)

    monkeypatch.setattr(anchor_module._DirectoryAnchor, "_member_identity", fail_destination_identity)
    monkeypatch.setattr(DirectoryTransaction, "_link_with_immediate_receipt", observe_link)
    with pytest.raises((ConflictError, OSError), match="destination identity-read failure|final"):
        ObjectStore(tmp_path).write("task", TASK_ID, 1, value)

    assert failed and receipt_seen
    assert target.read_bytes() == data
    assert ObjectStore(tmp_path).write("task", TASK_ID, 1, value) == target
    assert target.read_bytes() == data


def test_partial_owned_stage_is_retained_and_exact_retry_drains_only_it(tmp_path: Path, monkeypatch) -> None:
    """A post-create failure leaves exact recovery state, not guessed cleanup."""

    value = {"value": "partial-stage-retry"}
    data = canonical_bytes(value)
    target = _object_target(tmp_path, value)
    store = ObjectStore(tmp_path)
    injected = _partial_stage_injection(monkeypatch, trigger="injected stage failure after create")

    with pytest.raises(ConflictError, match="stage failure after create"):
        store.write("task", TASK_ID, 1, value)
    assert injected()

    reserved = list(target.parent.glob(f".{target.name}.*.tmp"))
    assert len(reserved) == 1
    reserved_path = reserved[0]
    assert reserved_path.read_bytes() == b"partial-stage"
    foreign = target.parent / f".{target.name}.zzzz-foreign.tmp"
    foreign.write_bytes(b"foreign-stage")

    assert store.write("task", TASK_ID, 1, value) == target
    assert target.read_bytes() == data
    assert not reserved_path.exists()
    assert foreign.read_bytes() == b"foreign-stage"


def test_object_front_door_does_not_retry_terminal_uncertain_descriptor(tmp_path: Path, monkeypatch) -> None:
    """An ambiguous POSIX descriptor release is terminal, never a retry ticket."""

    value = {"value": "terminal-uncertain-guard-front-door"}
    target = _object_target(tmp_path, value)
    original_release = DirectoryMutationGuard._release_resource
    original_retry = DirectoryMutationGuard.retry_release
    injected_guard: DirectoryMutationGuard | None = None
    injected = False
    retry_called = False

    def fail_once(guard, resource, unlocker, closer):
        nonlocal injected, injected_guard
        if not injected:
            injected = True
            injected_guard = guard

            def fail_unlock(released_resource: object) -> None:
                try:
                    unlocker(released_resource)
                finally:
                    raise OSError("injected unlock failure")

            def fail_close(released_resource: object) -> None:
                try:
                    closer(released_resource)
                finally:
                    raise OSError("injected close failure")

            # Both operations touch the real guard descriptor. The close has
            # already consumed it when the terminal uncertainty is reported.
            return original_release(guard, resource, fail_unlock, fail_close)
        return original_release(guard, resource, unlocker, closer)

    def observe_retry(guard):
        nonlocal retry_called
        if guard is injected_guard:
            retry_called = True
        return original_retry(guard)

    monkeypatch.setattr(DirectoryMutationGuard, "_release_resource", fail_once)
    monkeypatch.setattr(DirectoryMutationGuard, "retry_release", observe_retry)

    with pytest.raises((ConflictError, OSError), match="unlock|close|descriptor"):
        ObjectStore(tmp_path).write("task", TASK_ID, 1, value)
    assert injected_guard is not None
    assert injected_guard._release_state == "terminal_uncertain"
    assert injected_guard._retained_release is None
    assert not injected_guard._close_only_transferred
    assert target.exists()

    assert ObjectStore(tmp_path).write("task", TASK_ID, 1, value) == target
    assert not retry_called


def test_object_namespace_uses_one_fixed_persistent_guard(tmp_path: Path, monkeypatch) -> None:
    """Object effects never derive a temporary or publication claim guard."""

    import research_system.store.anchor as anchor_module

    calls: list[tuple[Path, str]] = []
    original = anchor_module._DirectoryAnchor.acquire_mutation_guard

    def observe(anchor, name):
        calls.append((anchor.final_path, name))
        return original(anchor, name)

    monkeypatch.setattr(anchor_module._DirectoryAnchor, "acquire_mutation_guard", observe)
    store = ObjectStore(tmp_path)
    value = {"value": "fixed-guard"}
    store.write("task", TASK_ID, 1, value)
    store.write("task", TASK_ID, 1, value)

    assert calls
    assert [name for _path, name in calls] == [
        ".store-transaction-v2.guard",
        ".store-transaction-v2.guard",
    ]
    assert all(".tmp" not in name and "publication-claim" not in name for _path, name in calls)
    assert len({path for path, _name in calls}) == 1


def test_same_byte_different_inode_final_is_preserved_for_retry(tmp_path: Path, monkeypatch) -> None:
    """Equal bytes do not permit deleting a substituted immutable generation."""

    import research_system.store.anchor as anchor_module

    value = {"value": "same-byte-substitution"}
    data = canonical_bytes(value)
    target = _object_target(tmp_path, value)
    original_fsync = anchor_module._DirectoryAnchor.fsync
    replaced = False
    replacement_identity = None

    def replace_final_after_link(anchor, *args, **kwargs):
        nonlocal replaced, replacement_identity
        if target.exists() and not replaced:
            replaced = True
            target.unlink()
            target.write_bytes(data)
            replacement_identity = target.stat(follow_symlinks=False)
        return original_fsync(anchor, *args, **kwargs)

    monkeypatch.setattr(anchor_module._DirectoryAnchor, "fsync", replace_final_after_link)
    with pytest.raises(ConflictError, match="generation changed|final"):
        ObjectStore(tmp_path).write("task", TASK_ID, 1, value)

    assert replaced and replacement_identity is not None
    assert target.read_bytes() == data
    assert ObjectStore(tmp_path).write("task", TASK_ID, 1, value) == target
    assert os.path.samestat(target.stat(follow_symlinks=False), replacement_identity)


def test_successful_retry_survives_public_close_safe_point_without_final_delete(tmp_path: Path, monkeypatch) -> None:
    """A post-link ambiguity never authorizes delayed final deletion."""

    import research_system.store.anchor as anchor_module

    value = {"value": "no-delayed-final-delete"}
    target = _object_target(tmp_path, value)
    original_fsync = anchor_module._DirectoryAnchor.fsync
    failed = False

    def fail_once_after_final_link(anchor, *args, **kwargs):
        nonlocal failed
        if target.exists() and not failed:
            failed = True
            raise ConflictError("injected post-link durability failure")
        return original_fsync(anchor, *args, **kwargs)

    monkeypatch.setattr(anchor_module._DirectoryAnchor, "fsync", fail_once_after_final_link)
    with pytest.raises(ConflictError, match="post-link durability failure"):
        ObjectStore(tmp_path).write("task", TASK_ID, 1, value)
    assert target.exists()

    assert ObjectStore(tmp_path).write("task", TASK_ID, 1, value) == target
    drain_close_quarantine()
    assert ObjectStore(tmp_path).write("task", TASK_ID, 1, value) == target
    assert target.exists()


def test_close_only_registry_rejects_untyped_tickets_and_preserves_marker(tmp_path: Path) -> None:
    """The close-only registry accepts only typed internal tickets."""

    import research_system.store.anchor as anchor_module

    marker = tmp_path / "close-only-marker"
    marker.write_bytes(b"preserve")

    with pytest.raises(TypeError):
        anchor_module._retain_close_ticket(object())
    assert marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows close-ticket resource validation")
def test_windows_close_only_ticket_rejects_callbacks_and_descriptors(tmp_path: Path) -> None:
    """The Windows close-only seam rejects callback-shaped and CRT resources."""

    import research_system.store.anchor as anchor_module

    marker = tmp_path / "close-only-marker"
    marker.write_bytes(b"preserve")

    with pytest.raises(TypeError):
        anchor_module._close_only_ticket("arbitrary-callback", "arbitrary-callback", lambda: None)
    descriptor = os.open(marker, os.O_RDONLY)
    try:
        with pytest.raises(TypeError):
            anchor_module._close_only_ticket("wrapped-os-close", "native-windows-handle", descriptor)
    finally:
        os.close(descriptor)
    assert marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows typed close-ticket retry control")
def test_windows_close_only_tickets_retry_only_native_handles_and_anchors(tmp_path: Path, monkeypatch) -> None:
    """Native HANDLE and anchor tickets retry; no caller closer is involved."""

    import research_system.store.anchor as anchor_module

    root = tmp_path / "typed-close-root"
    root.mkdir()
    anchor = open_registered_root_anchor(root, delete_protect=False)
    target = root / "typed-close-target"
    target.write_bytes(b"native-handle")
    handle = anchor_module._windows_open_handle(
        target,
        open_reparse_point=True,
        delete_protect=False,
        read_contents=True,
        share_mode=(
            anchor_module._FILE_SHARE_READ | anchor_module._FILE_SHARE_WRITE | anchor_module._FILE_SHARE_DELETE
        ),
    )
    native_attempts = 0
    native_closed = False
    anchor_attempts = 0
    real_close_handle = anchor_module._windows_close_handle
    real_anchor_close = anchor_module._DirectoryAnchor._close_without_quarantine

    def fail_native_once(resource):
        nonlocal native_attempts, native_closed
        native_attempts += 1
        if native_attempts == 1:
            raise OSError("injected native HANDLE close failure")
        result = real_close_handle(resource)
        native_closed = True
        return result

    def fail_anchor_once(current_anchor):
        nonlocal anchor_attempts
        if current_anchor is anchor:
            anchor_attempts += 1
        if current_anchor is anchor and anchor_attempts == 1:
            raise OSError("injected anchor close failure")
        return real_anchor_close(current_anchor)

    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_native_once)
    monkeypatch.setattr(anchor_module._DirectoryAnchor, "_close_without_quarantine", fail_anchor_once)
    try:
        native_ticket = anchor_module._close_only_ticket("native-handle", "native-windows-handle", handle)
        anchor_ticket = anchor_module._close_only_ticket("directory-anchor", "directory-anchor", anchor)
        anchor_module._retain_close_ticket(native_ticket)
        anchor_module._retain_close_ticket(anchor_ticket)
        with pytest.raises(ConflictError, match="close remains pending"):
            drain_close_quarantine()
        assert native_attempts == 1 and anchor_attempts == 1

        drain_close_quarantine()
        assert native_attempts == 2 and anchor_attempts == 2
        assert anchor._closed
        assert target.read_bytes() == b"native-handle"
    finally:
        if not native_closed:
            try:
                real_close_handle(handle)
            except BaseException:
                pass
        if not anchor._closed:
            try:
                real_anchor_close(anchor)
            except BaseException:
                pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX close-ticket descriptor-reuse control")
def test_posix_close_ticket_cannot_close_a_reused_descriptor(tmp_path: Path, monkeypatch) -> None:
    """A mutation-guard close error must not later close a reused fd."""

    import research_system.store.anchor as anchor_module

    reuse_path = tmp_path / "reused-descriptor"
    real_close = os.close
    real_open = os.open
    injected = False
    target_fd: int | None = None
    reused_fd: int | None = None
    original_release = DirectoryMutationGuard._release_resource

    def close_after_real_close(fd: int) -> None:
        nonlocal injected, target_fd, reused_fd
        if fd == target_fd and not injected:
            injected = True
            target_fd = fd
            # The underlying descriptor is already closed when the injected
            # exception is raised. Force the next live file onto its number.
            real_close(fd)
            candidate = real_open(reuse_path, os.O_CREAT | os.O_RDWR, 0o600)
            os.write(candidate, b"fd-reuse-sentinel")
            if candidate != fd:
                os.dup2(candidate, fd)
                real_close(candidate)
            reused_fd = fd
            raise OSError("injected close error after descriptor close")
        real_close(fd)

    def capture_guard_release(guard, resource, unlocker, closer):
        nonlocal target_fd
        target_fd = int(resource)
        return original_release(guard, resource, unlocker, closer)

    monkeypatch.setattr(DirectoryMutationGuard, "_release_resource", capture_guard_release)
    monkeypatch.setattr(anchor_module.os, "close", close_after_real_close)

    try:
        with pytest.raises(OSError, match="after descriptor close"):
            ObjectStore(tmp_path).write("task", TASK_ID, 1, {"value": "fd-reuse"})
        assert injected and target_fd is not None and reused_fd == target_fd
        os.lseek(reused_fd, 0, os.SEEK_SET)
        assert os.read(reused_fd, 64) == b"fd-reuse-sentinel"

        drain_close_quarantine()
        # A stale integer close ticket would close the reused descriptor here.
        os.fstat(reused_fd)
        os.lseek(reused_fd, 0, os.SEEK_SET)
        assert os.read(reused_fd, 64) == b"fd-reuse-sentinel"
    finally:
        if reused_fd is not None:
            try:
                real_close(reused_fd)
            except OSError:
                pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX regular-file descriptor close precedence control")
def test_posix_read_validation_primary_survives_one_shot_descriptor_close(tmp_path: Path, monkeypatch) -> None:
    """A read validation error remains primary after its consumed descriptor close fails."""

    import research_system.store.anchor as anchor_module

    value = {"value": "posix-read-primary-over-close"}
    target = ObjectStore(tmp_path).write("task", TASK_ID, 1, value)
    anchor = open_registered_root_anchor(target.parent, delete_protect=False)
    sentinel_path = tmp_path / "reused-posix-read-descriptor"
    real_open = os.open
    real_close = os.close
    real_fstat = os.fstat
    target_descriptor: int | None = None
    reused_descriptor: int | None = None
    primary_injected = False
    close_injected = False

    def capture_target_open(path, *args, **kwargs):
        nonlocal target_descriptor
        descriptor = real_open(path, *args, **kwargs)
        if str(path) == target.name:
            target_descriptor = descriptor
        return descriptor

    def inject_reused_descriptor(descriptor: int) -> None:
        nonlocal close_injected, reused_descriptor
        if descriptor != target_descriptor or close_injected:
            return
        close_injected = True
        candidate = real_open(sentinel_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.write(candidate, b"posix-read-descriptor-sentinel")
        if candidate != descriptor:
            os.dup2(candidate, descriptor)
            real_close(candidate)
        reused_descriptor = descriptor
        raise OSError("injected POSIX read descriptor close after consumption")

    def close_after_real_close(descriptor: int) -> None:
        if descriptor == target_descriptor and not close_injected:
            real_close(descriptor)
            inject_reused_descriptor(descriptor)
            return
        real_close(descriptor)

    def fail_target_validation(descriptor: int):
        nonlocal primary_injected
        if descriptor == target_descriptor and not primary_injected:
            primary_injected = True
            raise ConflictError("injected POSIX read validation primary")
        return real_fstat(descriptor)

    supported_dir_fd = anchor_module.os.supports_dir_fd
    if isinstance(supported_dir_fd, tuple):
        patched_supports_dir_fd = tuple(
            capture_target_open if candidate is real_open else candidate for candidate in supported_dir_fd
        )
        if capture_target_open not in patched_supports_dir_fd:
            patched_supports_dir_fd += (capture_target_open,)
    else:
        patched_supports_dir_fd = set(supported_dir_fd)
        patched_supports_dir_fd.discard(real_open)
        patched_supports_dir_fd.add(capture_target_open)
    monkeypatch.setattr(anchor_module.os, "supports_dir_fd", patched_supports_dir_fd)
    monkeypatch.setattr(anchor_module.os, "open", capture_target_open)
    monkeypatch.setattr(anchor_module.os, "close", close_after_real_close)
    monkeypatch.setattr(anchor_module.os, "fstat", fail_target_validation)

    try:
        with pytest.raises(ConflictError, match="injected POSIX read validation primary") as raised:
            anchor.read_regular_file_with_identity(target.name)
        assert raised.value.__cause__ is not None
        assert "POSIX read descriptor close after consumption" in repr(raised.value.__cause__)
        assert primary_injected and close_injected and reused_descriptor == target_descriptor

        drain_close_quarantine()
        os.fstat(reused_descriptor)
        os.lseek(reused_descriptor, 0, os.SEEK_SET)
        assert os.read(reused_descriptor, 128) == b"posix-read-descriptor-sentinel"
    finally:
        if reused_descriptor is not None:
            try:
                real_close(reused_descriptor)
            except OSError:
                pass
        anchor.close()


@pytest.mark.skipif(os.name != "posix", reason="POSIX stage descriptor-reuse control")
def test_posix_stage_close_error_marks_descriptor_terminal_before_cleanup(tmp_path: Path, monkeypatch) -> None:
    """A failed stage close cannot let exception cleanup close a recycled fd."""

    import research_system.store.anchor as anchor_module

    sentinel_path = tmp_path / "stage-reused-descriptor"
    real_close = os.close
    real_open = os.open
    stage_fd: int | None = None
    reused_fd: int | None = None
    injected = False

    def observe_stage(_name, descriptor, *args, **kwargs):
        nonlocal stage_fd
        stage_fd = descriptor

    def close_after_real_close(fd: int) -> None:
        nonlocal injected, reused_fd
        if stage_fd == fd and not injected:
            injected = True
            real_close(fd)
            candidate = real_open(sentinel_path, os.O_CREAT | os.O_RDWR, 0o600)
            os.write(candidate, b"stage-fd-reuse-sentinel")
            if candidate != fd:
                os.dup2(candidate, fd)
                real_close(candidate)
            reused_fd = fd
            raise OSError("injected stage close error after descriptor close")
        real_close(fd)

    monkeypatch.setattr(anchor_module, "_after_stage_opened", observe_stage)
    monkeypatch.setattr(anchor_module.os, "close", close_after_real_close)

    try:
        with pytest.raises(OSError, match="stage close error"):
            ObjectStore(tmp_path).write("task", TASK_ID, 1, {"value": "stage-fd-reuse"})
        assert injected and stage_fd is not None and reused_fd == stage_fd
        os.lseek(reused_fd, 0, os.SEEK_SET)
        assert os.read(reused_fd, 128) == b"stage-fd-reuse-sentinel"

        drain_close_quarantine()
        os.fstat(reused_fd)
        os.lseek(reused_fd, 0, os.SEEK_SET)
        assert os.read(reused_fd, 128) == b"stage-fd-reuse-sentinel"
    finally:
        if reused_fd is not None:
            try:
                real_close(reused_fd)
            except OSError:
                pass


def test_prelock_guard_close_error_never_retries_reused_descriptor(tmp_path: Path, monkeypatch) -> None:
    """A pre-lock descriptor is terminal on both platforms after close ambiguity."""

    import research_system.store.anchor as anchor_module

    root = tmp_path / "prelock-guard-root"
    root.mkdir()
    anchor = open_registered_root_anchor(root, delete_protect=False)
    sentinel_path = tmp_path / "prelock-reused-descriptor"
    real_open = os.open
    real_close = os.close
    guard_fd: int | None = None
    reused_fd: int | None = None
    injected = False
    fsync_failed = False
    real_fsync_directory = anchor_module._DirectoryAnchor._fsync_directory
    real_fsync = os.fsync

    def observe_open(path, *args, **kwargs):
        nonlocal guard_fd
        descriptor = real_open(path, *args, **kwargs)
        try:
            is_guard = Path(path).name == TRANSACTION_GUARD_NAME
        except TypeError:
            is_guard = False
        if is_guard:
            guard_fd = descriptor
        return descriptor

    def fail_before_lock(current_anchor, path):
        nonlocal fsync_failed
        if guard_fd is not None and not fsync_failed:
            fsync_failed = True
            raise ConflictError("injected pre-lock guard failure")
        return real_fsync_directory(current_anchor, path)

    def fail_fsync(fd: int) -> None:
        nonlocal fsync_failed
        if guard_fd is not None and not fsync_failed:
            fsync_failed = True
            raise ConflictError("injected pre-lock guard failure")
        return real_fsync(fd)

    def close_after_real_close(fd: int) -> None:
        nonlocal injected, reused_fd
        if guard_fd == fd and not injected:
            injected = True
            real_close(fd)
            candidate = real_open(sentinel_path, os.O_CREAT | os.O_RDWR, 0o600)
            os.write(candidate, b"prelock-fd-reuse-sentinel")
            if candidate != fd:
                os.dup2(candidate, fd)
                real_close(candidate)
            reused_fd = fd
            raise OSError("injected pre-lock close error after descriptor close")
        real_close(fd)

    # ``acquire_mutation_guard`` deliberately checks the exact ``os.open``
    # callable before using its dir_fd path. Replacing that callable for
    # instrumentation must preserve the platform capability declaration.
    supported_dir_fd = anchor_module.os.supports_dir_fd
    if isinstance(supported_dir_fd, tuple):
        patched_supports_dir_fd = tuple(
            observe_open if candidate is real_open else candidate for candidate in supported_dir_fd
        )
        if observe_open not in patched_supports_dir_fd:
            patched_supports_dir_fd += (observe_open,)
    else:
        patched_supports_dir_fd = set(supported_dir_fd)
        patched_supports_dir_fd.discard(real_open)
        patched_supports_dir_fd.add(observe_open)
    monkeypatch.setattr(anchor_module.os, "supports_dir_fd", patched_supports_dir_fd)
    monkeypatch.setattr(anchor_module.os, "open", observe_open)
    monkeypatch.setattr(anchor_module.os, "close", close_after_real_close)
    monkeypatch.setattr(anchor_module.os, "fsync", fail_fsync)
    monkeypatch.setattr(anchor_module._DirectoryAnchor, "_fsync_directory", fail_before_lock)

    try:
        with pytest.raises(ConflictError, match="pre-lock guard failure"):
            with anchor.acquire_mutation_guard(TRANSACTION_GUARD_NAME):
                pass
        assert fsync_failed and injected and guard_fd is not None and reused_fd == guard_fd
        os.lseek(reused_fd, 0, os.SEEK_SET)
        assert os.read(reused_fd, 128) == b"prelock-fd-reuse-sentinel"

        drain_close_quarantine()
        os.fstat(reused_fd)
        os.lseek(reused_fd, 0, os.SEEK_SET)
        assert os.read(reused_fd, 128) == b"prelock-fd-reuse-sentinel"
    finally:
        if reused_fd is not None:
            try:
                real_close(reused_fd)
            except OSError:
                pass
        anchor.close()


@pytest.mark.skipif(os.name != "posix", reason="POSIX bounded flock control")
def test_occupied_guard_flock_fails_bounded_and_nonblocking(tmp_path: Path, monkeypatch) -> None:
    """An occupied guard retries nonblocking and returns a bounded conflict."""

    import fcntl

    root = tmp_path / "occupied-guard-root"
    root.mkdir()
    anchor = open_registered_root_anchor(root, delete_protect=False)
    real_flock = fcntl.flock
    operations: list[int] = []

    def report_occupied(descriptor: int, operation: int) -> None:
        operations.append(operation)
        if operation & fcntl.LOCK_EX:
            raise BlockingIOError("injected occupied guard")
        return real_flock(descriptor, operation)

    monkeypatch.setattr(fcntl, "flock", report_occupied)
    try:
        with pytest.raises(ConflictError, match="guard is unavailable"):
            with anchor.acquire_mutation_guard(TRANSACTION_GUARD_NAME):
                pass
        assert len(operations) == 64
        assert all(operation & fcntl.LOCK_NB for operation in operations)
    finally:
        anchor.close()


def test_body_exception_remains_primary_when_terminal_release_fails(tmp_path: Path, monkeypatch) -> None:
    """Anchor and admission cleanup errors stay visible without replacing body failure."""

    import research_system.store.anchor as anchor_module

    admission_failed = False
    real_release_admission = anchor_module._release_directory_admission

    def fail_admission_release(admission):
        nonlocal admission_failed
        result = real_release_admission(admission)
        if not admission_failed:
            admission_failed = True
            raise OSError("injected terminal admission release failure")
        return result

    monkeypatch.setattr(anchor_module, "_release_directory_admission", fail_admission_release)

    class _Guard:
        _release_state = "active"
        _close_only_transferred = False

    class _Context:
        def __init__(self) -> None:
            self.guard = _Guard()

        def __enter__(self):
            return self.guard

        def __exit__(self, _exc_type, _exc, _traceback):
            self.guard._release_state = "released"
            return False

    class _Anchor:
        identity = DirectoryIdentity("posix-dev-inode-v1", 9101, b"terminal-release")
        final_path = tmp_path

        def __init__(self) -> None:
            self.transaction_holds = 0
            self.fail_anchor_release = True

        def _retain_transaction_hold(self) -> None:
            self.transaction_holds += 1

        def _release_transaction_hold(self) -> None:
            self.transaction_holds -= 1
            if self.fail_anchor_release:
                self.fail_anchor_release = False
                raise OSError("injected terminal anchor release failure")

        def acquire_mutation_guard(self, _name: str):
            return _Context()

    anchor = _Anchor()
    body_error: ValueError
    with pytest.raises(ValueError, match="body remains primary") as raised:
        with DirectoryTransaction(anchor) as transaction:
            raise ValueError("body remains primary")
    body_error = raised.value
    assert body_error.__cause__ is not None
    assert "terminal anchor release failure" in repr(body_error.__cause__)
    notes = getattr(body_error.__cause__, "__notes__", ())
    assert any("admission release failed" in note for note in notes)
    assert admission_failed and anchor.transaction_holds == 0
    assert transaction._reservation is None and transaction._admission is None

    successor = DirectoryTransaction(anchor)
    successor.__enter__()
    successor.__exit__(None, None, None)
    assert anchor.transaction_holds == 0
    assert successor._reservation is None and successor._admission is None


def test_full_owner_reservation_capacity_rejects_before_any_effect(tmp_path: Path) -> None:
    """Full-owner backpressure has no eviction and no pre-admission effect."""

    class _Guard:
        _release_state = "active"
        _close_only_transferred = False

    class _Context:
        def __init__(self) -> None:
            self.guard = _Guard()

        def __enter__(self):
            return self.guard

        def __exit__(self, _exc_type, _exc, _traceback):
            self.guard._release_state = "released"
            return False

    class _Anchor:
        def __init__(self, index: int) -> None:
            self.identity = DirectoryIdentity("posix-dev-inode-v1", index, index.to_bytes(8, "big"))
            self.final_path = tmp_path / f"anchor-{index}"

        def acquire_mutation_guard(self, _name: str):
            return _Context()

    transactions: list[DirectoryTransaction] = []
    try:
        for index in range(64):
            transaction = DirectoryTransaction(_Anchor(index))
            transaction.__enter__()
            transactions.append(transaction)

        blocked = DirectoryTransaction(_Anchor(64))
        with pytest.raises(ConflictError, match="capacity"):
            blocked.__enter__()
        assert blocked.effects == []

        transactions[0].__exit__(None, None, None)
        replacement = DirectoryTransaction(_Anchor(1000))
        replacement.__enter__()
        transactions.append(replacement)
    finally:
        for transaction in reversed(transactions):
            try:
                transaction.__exit__(None, None, None)
            except BaseException:
                pass


def test_terminal_uncertain_guard_release_does_not_block_next_transaction(tmp_path: Path, monkeypatch) -> None:
    """A failed POSIX guard release is terminal and leaves capacity usable."""

    retry_called = False

    class _GuardContext:
        def __init__(self, guard: DirectoryMutationGuard, *, fail_on_exit: bool) -> None:
            self.guard = guard
            self.fail_on_exit = fail_on_exit

        def __enter__(self):
            return self.guard

        def __exit__(self, _exc_type, _exc, _traceback):
            if self.fail_on_exit:
                self.guard._release_state = "terminal_uncertain"
                raise OSError("injected terminal-uncertain descriptor release")
            self.guard._release_state = "released"
            return False

    class _Anchor:
        final_path = tmp_path
        identity = DirectoryIdentity("posix-dev-inode-v1", 7001, b"terminal-guard")

        def __init__(self) -> None:
            self.calls: list[str] = []

        def acquire_mutation_guard(self, name: str):
            self.calls.append(name)
            guard = DirectoryMutationGuard(self, name)
            return _GuardContext(guard, fail_on_exit=len(self.calls) == 1)

    def observe_retry(_guard: DirectoryMutationGuard) -> None:
        nonlocal retry_called
        retry_called = True

    monkeypatch.setattr(DirectoryMutationGuard, "retry_release", observe_retry)
    anchor = _Anchor()
    transaction = DirectoryTransaction(anchor)
    transaction.__enter__()
    with pytest.raises(OSError, match="terminal-uncertain descriptor release"):
        transaction.__exit__(None, None, None)
    assert transaction.exit_status.guard_state == "terminal_uncertain"
    assert transaction._retained_guard is None
    transaction.retry_guard_release()
    assert not retry_called

    next_transaction = DirectoryTransaction(anchor)
    next_transaction.__enter__()
    next_transaction.__exit__(None, None, None)
    assert not retry_called
    assert anchor.calls == [TRANSACTION_GUARD_NAME, TRANSACTION_GUARD_NAME]


def test_concurrent_same_object_writers_serialize_one_revision(tmp_path: Path, monkeypatch) -> None:
    """Two same-object writers never execute staging concurrently."""

    first_stage = threading.Event()
    second_started = threading.Event()
    second_attempted = threading.Event()
    release_first = threading.Event()
    guard_entries_before_release: list[bool] = []
    original_stage = DirectoryTransaction._stage_owned_private
    import research_system.store.anchor as anchor_module

    original_admission = anchor_module._acquire_directory_admission
    original_guard = anchor_module._DirectoryAnchor.acquire_mutation_guard

    def observe_admission(identity):
        if first_stage.is_set():
            second_attempted.set()
        return original_admission(identity)

    class _ObservedGuardContext:
        def __init__(self, inner) -> None:
            self.inner = inner

        def __enter__(self):
            guard = self.inner.__enter__()
            guard_entries_before_release.append(not release_first.is_set())
            return guard

        def __exit__(self, exc_type, exc, traceback):
            return self.inner.__exit__(exc_type, exc, traceback)

    def observe_guard(anchor, name):
        return _ObservedGuardContext(original_guard(anchor, name))

    monkeypatch.setattr(anchor_module, "_acquire_directory_admission", observe_admission)
    monkeypatch.setattr(anchor_module._DirectoryAnchor, "acquire_mutation_guard", observe_guard)
    results: list[Path] = []
    errors: list[BaseException] = []

    def observe_stage(transaction, target_name, data):
        first_stage.set()
        if not release_first.wait(5):
            raise AssertionError("first writer was not released")
        return original_stage(transaction, target_name, data)

    monkeypatch.setattr(DirectoryTransaction, "_stage_owned_private", observe_stage)

    def write(second: bool) -> None:
        try:
            if second:
                second_started.set()
            results.append(ObjectStore(tmp_path).write("task", TASK_ID, 1, {"x": 1}))
        except BaseException as error:  # pragma: no cover - asserted below
            errors.append(error)

    first_writer = threading.Thread(target=write, args=(False,))
    second_writer = threading.Thread(target=write, args=(True,))
    first_writer.start()
    assert first_stage.wait(5)
    second_writer.start()
    assert second_started.wait(5)
    assert second_attempted.wait(5), "second writer never attempted the guard"
    release_first.set()
    first_writer.join(timeout=5)
    second_writer.join(timeout=5)

    assert not first_writer.is_alive() and not second_writer.is_alive()
    assert errors == []
    assert guard_entries_before_release == [True, False]
    assert len(set(results)) == 1
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) == {"x": 1}
    assert not list(_object_directory(tmp_path).glob(".*.tmp"))


@pytest.mark.skipif(os.name != "nt", reason="Windows Delete=True stage control")
def test_windows_delete_true_stage_close_failure_retains_full_owner(tmp_path: Path, monkeypatch) -> None:
    """A failed Delete=True stage close remains a transaction owner."""

    import research_system.store.anchor as anchor_module

    root = tmp_path / "stage-owner-root"
    root.mkdir()
    anchor = open_registered_root_anchor(root, delete_protect=False)
    original_open = anchor_module._windows_open_handle
    original_close = anchor_module._windows_close_handle
    target_values: set[int] = set()
    close_attempts = 0
    stage_name: str | None = None

    def capture_open(path, *args, **kwargs):
        handle = original_open(path, *args, **kwargs)
        if stage_name is not None and Path(path).name == stage_name:
            value = getattr(handle, "value", handle)
            target_values.add(int(value))
        return handle

    def fail_target_close(handle):
        nonlocal close_attempts
        value = getattr(handle, "value", handle)
        if int(value) in target_values:
            close_attempts += 1
            if close_attempts <= 3:
                raise OSError("injected Delete=True stage CloseHandle failure")
        return original_close(handle)

    def reject_close_only(*_args, **_kwargs):
        raise AssertionError("Delete=True stage owner entered close-only quarantine")

    monkeypatch.setattr(anchor_module, "_windows_open_handle", capture_open)
    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_target_close)
    monkeypatch.setattr(anchor_module, "_retain_close_ticket", reject_close_only)

    try:
        # The first failure is caught locally so the transaction's own
        # context-manager exit still runs.  Its immediate retry is the second
        # injected close failure; that exit then transfers the whole owner to
        # the retained-owner registry. During the successor drain, the first
        # close attempt also fails and the retry in __exit__ completes it.
        with pytest.raises(ConflictError, match="stage cleanup|close|pending"):
            with DirectoryTransaction(anchor) as transaction:
                stage = transaction.stage("owned-stage", b"owned-stage")
                stage_name = stage.name
                with pytest.raises(ConflictError, match="stage cleanup|close|pending"):
                    transaction.discard_stage(stage)

        with DirectoryTransaction(anchor):
            pass
        assert close_attempts >= 4
        assert not (root / stage_name).exists()
    finally:
        anchor.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows retained-owner terminal conflict control")
def test_windows_path_fence_loss_after_delete_close_does_not_poison_later_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A handleless path conflict is terminal, not a permanently pending owner."""

    import research_system.store.anchor as anchor_module

    value = {"value": "terminal-path-conflict"}
    target = _object_target(tmp_path, value)
    stage_name: str | None = None
    target_handles: set[int] = set()
    close_attempts = 0
    target_closed = False
    fence_failed = False
    real_stage_hook = anchor_module._after_stage_opened
    real_open_handle = anchor_module._windows_open_handle
    real_close_handle = anchor_module._windows_close_handle
    real_verify = anchor_module._DirectoryAnchor.verify_unchanged

    def capture_stage(name, descriptor, *args, **kwargs):
        nonlocal stage_name
        stage_name = name
        return real_stage_hook(name, descriptor, *args, **kwargs)

    def capture_stage_handle(path, *args, **kwargs):
        handle = real_open_handle(path, *args, **kwargs)
        if stage_name is not None and Path(path).name == stage_name:
            target_handles.add(int(getattr(handle, "value", handle)))
        return handle

    def fail_then_close_stage(handle):
        nonlocal close_attempts, target_closed
        value_handle = int(getattr(handle, "value", handle))
        if value_handle in target_handles:
            close_attempts += 1
            if close_attempts <= 2:
                raise OSError("injected retained-stage CloseHandle failure")
            result = real_close_handle(handle)
            target_closed = True
            return result
        return real_close_handle(handle)

    def fail_once_after_stage_close(anchor):
        nonlocal fence_failed
        if target_closed and not fence_failed:
            fence_failed = True
            raise ConflictError("injected retained-owner path-fence loss")
        return real_verify(anchor)

    monkeypatch.setattr(anchor_module, "_after_stage_opened", capture_stage)
    monkeypatch.setattr(anchor_module, "_windows_open_handle", capture_stage_handle)
    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_then_close_stage)

    store = ObjectStore(tmp_path)
    with pytest.raises(ConflictError, match="stage cleanup|close|pending|deletion"):
        store.write("task", TASK_ID, 1, value)
    assert close_attempts == 2 and stage_name is not None

    monkeypatch.setattr(anchor_module._DirectoryAnchor, "verify_unchanged", fail_once_after_stage_close)
    with pytest.raises(ConflictError, match="retained store owner drain remains pending"):
        store.write("task", TASK_ID, 1, value)

    assert target_closed and fence_failed
    assert target.read_bytes() == canonical_bytes(value)
    assert store.write("task", TASK_ID, 1, value) == target


@pytest.mark.skipif(os.name != "nt", reason="Windows ordinary ObjectStore owner-retry control")
def test_windows_object_store_retry_drains_stage_owner_and_anchor_chain(tmp_path: Path, monkeypatch) -> None:
    """An ordinary ObjectStore retry keeps the complete anchor chain reachable."""

    import research_system.store.anchor as anchor_module
    import research_system.store.objects as object_module

    value = {"value": "ordinary-store-owner-retry"}
    target = _object_target(tmp_path, value)
    root_anchor: list[object] = []
    first_chain: list[object] = []
    real_open_root = object_module.open_registered_root_anchor
    real_open_member = anchor_module._DirectoryAnchor.open_member_directory

    def capture_root(path, **kwargs):
        anchor = real_open_root(path, **kwargs)
        if not root_anchor:
            root_anchor.append(anchor)
            first_chain.append(anchor)
        return anchor

    def capture_member(anchor, name, **kwargs):
        child = real_open_member(anchor, name, **kwargs)
        if root_anchor and len(first_chain) < 4:
            first_chain.append(child)
        return child

    monkeypatch.setattr(object_module, "open_registered_root_anchor", capture_root)
    monkeypatch.setattr(anchor_module._DirectoryAnchor, "open_member_directory", capture_member)

    real_open_handle = anchor_module._windows_open_handle
    real_close_handle = anchor_module._windows_close_handle
    real_stage_hook = anchor_module._after_stage_opened
    target_handles: set[int] = set()
    close_attempts = 0
    stage_name: str | None = None

    def capture_stage_name(name, descriptor, *args, **kwargs):
        nonlocal stage_name
        stage_name = name
        return real_stage_hook(name, descriptor, *args, **kwargs)

    def capture_stage_handle(path, *args, **kwargs):
        handle = real_open_handle(path, *args, **kwargs)
        if stage_name is not None and Path(path).name == stage_name:
            target_handles.add(int(getattr(handle, "value", handle)))
        return handle

    def fail_stage_close(handle):
        nonlocal close_attempts
        value_handle = int(getattr(handle, "value", handle))
        if value_handle in target_handles:
            close_attempts += 1
            if close_attempts <= 2:
                raise OSError("injected ordinary ObjectStore Delete=True stage close failure")
        return real_close_handle(handle)

    def reject_close_only(*_args, **_kwargs):
        raise AssertionError("Delete=True stage owner was downgraded to close-only state")

    monkeypatch.setattr(anchor_module, "_windows_open_handle", capture_stage_handle)
    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_stage_close)
    monkeypatch.setattr(anchor_module, "_after_stage_opened", capture_stage_name)
    monkeypatch.setattr(anchor_module, "_retain_close_ticket", reject_close_only)

    store = ObjectStore(tmp_path)
    with pytest.raises(ConflictError, match="stage cleanup|close|pending|deletion"):
        # This is deliberately the public production seam. No transaction
        # lifecycle is driven by the control itself.
        store.write("task", TASK_ID, 1, value)

    assert len(first_chain) == 4
    assert close_attempts == 2
    assert stage_name is not None
    reserved_stage = target.parent / stage_name
    assert reserved_stage.exists()
    assert all(not getattr(anchor, "_closed") for anchor in first_chain)

    result: list[Path] = []
    errors: list[BaseException] = []
    completed = threading.Event()

    def retry_public_store_write() -> None:
        try:
            result.append(store.write("task", TASK_ID, 1, value))
        except BaseException as error:  # pragma: no cover - asserted below
            errors.append(error)
        finally:
            completed.set()

    retry = threading.Thread(target=retry_public_store_write, daemon=True)
    retry.start()
    assert completed.wait(5), "next public ObjectStore write did not drain the retained owner"
    retry.join(timeout=1)
    assert errors == []
    assert result == [target]
    assert close_attempts >= 3
    assert not reserved_stage.exists()
    assert all(getattr(anchor, "_closed") for anchor in first_chain)

    # A further public write demonstrates that the retained owner released its
    # admission capacity rather than merely allowing the exact retry through.
    assert store.write("task", TASK_ID, 2, {"value": "after-owner-drain"}).is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows member creation fence control")
def test_windows_object_store_member_creation_never_mutates_recreated_root(tmp_path: Path, monkeypatch) -> None:
    """A root move before lexical mkdir cannot create a replacement-root member."""

    root = tmp_path / "control-root"
    moved_root = tmp_path / "moved-control-root"
    replacement_member = root / "objects"
    original_mkdir = Path.mkdir
    moved = False

    def move_root_before_member_create(path: Path, *args, **kwargs) -> None:
        nonlocal moved
        if path == replacement_member and not moved:
            moved = True
            os.replace(root, moved_root)
            original_mkdir(root)
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", move_root_before_member_create)

    with pytest.raises(ConflictError, match="identity changed|parent directory changed"):
        ObjectStore(root).write("task", TASK_ID, 1, {"value": "recreated-root"})

    assert moved
    assert not replacement_member.exists()
    # The original physical root remains separate evidence; no member is
    # created there because the operation rejected before the requested effect.
    assert not (moved_root / "objects").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows typed validation-close ownership control")
def test_windows_delete_validation_primary_retains_native_handle_until_drain(tmp_path: Path, monkeypatch) -> None:
    """A failed Delete=True validation retains its HANDLE without hiding the primary error."""

    import research_system.store.anchor as anchor_module

    value = {"value": "retain-validation-handle"}
    store = ObjectStore(tmp_path)
    target = store.write("task", TASK_ID, 1, value)
    target_handles: list[object] = []
    close_attempts = 0
    target_closed = False
    real_open_handle = anchor_module._windows_open_handle
    real_read_handle = anchor_module._windows_read_handle
    real_close_handle = anchor_module._windows_close_handle

    def capture_target_handle(path, *args, **kwargs):
        handle = real_open_handle(path, *args, **kwargs)
        if Path(path).name == target.name:
            target_handles.append(handle)
        return handle

    def wrong_target_bytes(handle):
        if handle in target_handles:
            return b"foreign-bytes"
        return real_read_handle(handle)

    def fail_target_close_once(handle):
        nonlocal close_attempts, target_closed
        if handle in target_handles:
            close_attempts += 1
            if close_attempts == 1:
                raise OSError("injected validation-handle CloseHandle failure")
            target_closed = True
        return real_close_handle(handle)

    monkeypatch.setattr(anchor_module, "_windows_open_handle", capture_target_handle)
    monkeypatch.setattr(anchor_module, "_windows_read_handle", wrong_target_bytes)
    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_target_close_once)

    try:
        with pytest.raises(IntegrityError, match="changed object revision") as raised:
            store.rollback_new_revision("task", TASK_ID, 1, value, existed_before=False)
        assert raised.value.__cause__ is not None
        assert "bytes changed before exact deletion" in str(raised.value.__cause__)
        assert target_handles and close_attempts == 1
        assert any(
            ticket.disposition == "native-windows-handle" and ticket.resource in target_handles
            for ticket in anchor_module._WINDOWS_CLOSE_QUARANTINE
        )

        drain_close_quarantine()
        assert close_attempts == 2 and target_closed
        assert target.exists()
    finally:
        if target_handles and not target_closed:
            try:
                real_close_handle(target_handles[-1])
            except OSError:
                pass


@pytest.mark.skipif(os.name != "nt", reason="Windows member traversal cleanup precedence control")
def test_windows_member_close_failure_preserves_parent_revalidation_error(tmp_path: Path, monkeypatch) -> None:
    """A child-close failure stays retained and cannot replace the parent traversal failure."""

    import research_system.store.anchor as anchor_module

    root = tmp_path / "member-revalidation-root"
    child_path = root / "child"
    child_path.mkdir(parents=True)
    root_anchor = open_registered_root_anchor(root, delete_protect=False)
    child_anchors: list[object] = []
    root_verifications = 0
    close_attempts = 0
    real_open_child = anchor_module._open_windows_anchor
    real_verify = anchor_module._DirectoryAnchor.verify_unchanged
    real_close_handle = anchor_module._windows_close_handle

    def capture_child(path, *args, **kwargs):
        child = real_open_child(path, *args, **kwargs)
        if Path(path).name == child_path.name:
            child_anchors.append(child)
        return child

    def fail_second_root_verification(current_anchor):
        nonlocal root_verifications
        if current_anchor is root_anchor:
            root_verifications += 1
            if root_verifications == 2:
                raise ConflictError("injected parent revalidation primary")
        return real_verify(current_anchor)

    def fail_child_close_once(handle):
        nonlocal close_attempts
        if child_anchors and handle is child_anchors[0]._handle:
            close_attempts += 1
            if close_attempts == 1:
                raise OSError("injected child anchor CloseHandle failure")
        return real_close_handle(handle)

    monkeypatch.setattr(anchor_module, "_open_windows_anchor", capture_child)
    monkeypatch.setattr(anchor_module._DirectoryAnchor, "verify_unchanged", fail_second_root_verification)
    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_child_close_once)

    try:
        with pytest.raises(ConflictError, match="injected parent revalidation primary") as raised:
            root_anchor.open_member_directory("child", create=False, delete_protect=False)
        assert raised.value.__cause__ is not None
        assert "child anchor CloseHandle failure" in repr(raised.value.__cause__)
        assert child_anchors and close_attempts == 1
        child = child_anchors[0]
        assert any(ticket.resource is child for ticket in anchor_module._WINDOWS_CLOSE_QUARANTINE)

        drain_close_quarantine()
        assert close_attempts == 2 and child._closed
    finally:
        try:
            root_anchor.close()
        except OSError:
            pass


@pytest.mark.skipif(os.name != "nt", reason="Windows regular-file descriptor close precedence control")
def test_windows_read_validation_primary_survives_one_shot_descriptor_close(tmp_path: Path, monkeypatch) -> None:
    """Read validation remains primary when its consumed CRT descriptor close also fails."""

    import research_system.store.anchor as anchor_module

    value = {"value": "read-primary-over-close"}
    target = ObjectStore(tmp_path).write("task", TASK_ID, 1, value)
    anchor = open_registered_root_anchor(target.parent, delete_protect=False)
    sentinel_path = tmp_path / "reused-read-descriptor"
    real_open = os.open
    real_close = os.close
    real_fdopen = os.fdopen
    real_fstat = os.fstat
    target_descriptor: int | None = None
    reused_descriptor: int | None = None
    primary_injected = False
    close_injected = False

    def capture_target_open(path, *args, **kwargs):
        nonlocal target_descriptor
        descriptor = real_open(path, *args, **kwargs)
        if Path(path).name == target.name:
            target_descriptor = descriptor
        return descriptor

    def inject_reused_descriptor(descriptor: int) -> None:
        nonlocal close_injected, reused_descriptor
        if descriptor != target_descriptor or close_injected:
            return
        close_injected = True
        candidate = real_open(sentinel_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.write(candidate, b"read-descriptor-sentinel")
        if candidate != descriptor:
            os.dup2(candidate, descriptor)
            real_close(candidate)
        reused_descriptor = descriptor
        raise OSError("injected read descriptor close after consumption")

    class _ClosingFile:
        def __init__(self, inner) -> None:
            self._inner = inner
            self._descriptor = inner.fileno()

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            self._inner.close()
            inject_reused_descriptor(self._descriptor)
            return False

        def fileno(self) -> int:
            return self._inner.fileno()

        def read(self, *args, **kwargs):
            return self._inner.read(*args, **kwargs)

    def close_after_real_close(descriptor: int) -> None:
        if descriptor == target_descriptor and not close_injected:
            real_close(descriptor)
            inject_reused_descriptor(descriptor)
            return
        real_close(descriptor)

    def fail_target_validation(descriptor: int):
        nonlocal primary_injected
        if descriptor == target_descriptor and not primary_injected:
            primary_injected = True
            raise ConflictError("injected read validation primary")
        return real_fstat(descriptor)

    def wrapped_fdopen(descriptor: int, *args, **kwargs):
        return _ClosingFile(real_fdopen(descriptor, *args, **kwargs))

    monkeypatch.setattr(anchor_module.os, "open", capture_target_open)
    monkeypatch.setattr(anchor_module.os, "close", close_after_real_close)
    monkeypatch.setattr(anchor_module.os, "fstat", fail_target_validation)
    monkeypatch.setattr(anchor_module.os, "fdopen", wrapped_fdopen)

    try:
        with pytest.raises(ConflictError, match="injected read validation primary") as raised:
            anchor.read_regular_file_with_identity(target.name)
        assert raised.value.__cause__ is not None
        assert "read descriptor close after consumption" in repr(raised.value.__cause__)
        assert primary_injected and close_injected and reused_descriptor == target_descriptor

        drain_close_quarantine()
        os.fstat(reused_descriptor)
        os.lseek(reused_descriptor, 0, os.SEEK_SET)
        assert os.read(reused_descriptor, 128) == b"read-descriptor-sentinel"
    finally:
        if reused_descriptor is not None:
            try:
                real_close(reused_descriptor)
            except OSError:
                pass
        anchor.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows same-byte rollback race control")
def test_windows_rollback_rejects_same_byte_generation_swap_without_deleting_foreign(
    tmp_path: Path, monkeypatch
) -> None:
    """Rollback binds the Delete=True handle before any pathname deletion."""

    import research_system.store.anchor as anchor_module

    value = {"value": "rollback-same-byte-race"}
    data = canonical_bytes(value)
    store = ObjectStore(tmp_path)
    target = store.write("task", TASK_ID, 1, value)
    original_identity = target.stat(follow_symlinks=False)
    saved_a = target.with_name(f".{target.name}.saved-a")
    foreign_b = target.with_name(f".{target.name}.foreign-b")
    real_before_unlink = anchor_module._before_exact_generation_unlink
    real_open_handle = anchor_module._windows_open_handle
    real_regular_identity = anchor_module._regular_file_identity
    swapped = False
    restored = False
    path_lstat_calls = 0

    def swap_after_path_proof(path: Path) -> None:
        nonlocal swapped
        real_before_unlink(path)
        if Path(path).name == target.name and not swapped:
            swapped = True
            # Keep original A's inode aside, publish same-byte B, and retain
            # a second B link so the Delete=True handle cannot erase the
            # foreign generation from the test's evidence namespace.
            os.replace(target, saved_a)
            target.write_bytes(data)
            os.link(target, foreign_b)

    def restore_a_before_path_lstat(path: Path, *, label: str):
        nonlocal path_lstat_calls
        path_lstat_calls += 1
        return real_regular_identity(path, label=label)

    def open_target_then_restore(path: Path, *args, **kwargs):
        nonlocal restored
        handle = real_open_handle(path, *args, **kwargs)
        if Path(path).name == target.name and swapped and not restored:
            restored = True
            # The Delete=True handle has opened B with delete sharing. Remove
            # only B's target name and restore A before the handle-ID binding
            # and subsequent pathname lstat.
            os.unlink(target)
            os.replace(saved_a, target)
        return handle

    monkeypatch.setattr(anchor_module, "_before_exact_generation_unlink", swap_after_path_proof)
    monkeypatch.setattr(anchor_module, "_windows_open_handle", open_target_then_restore)
    monkeypatch.setattr(anchor_module, "_regular_file_identity", restore_a_before_path_lstat)

    try:
        with pytest.raises(IntegrityError, match="changed object revision"):
            store.rollback_new_revision(
                "task",
                TASK_ID,
                1,
                value,
                existed_before=False,
            )

        assert swapped and restored and path_lstat_calls == 0
        assert target.read_bytes() == data
        assert os.path.samestat(target.stat(follow_symlinks=False), original_identity)
        assert foreign_b.exists()
        assert foreign_b.read_bytes() == data
        assert not os.path.samestat(foreign_b.stat(follow_symlinks=False), original_identity)
    finally:
        for residue in (saved_a, foreign_b):
            try:
                residue.unlink()
            except FileNotFoundError:
                pass
