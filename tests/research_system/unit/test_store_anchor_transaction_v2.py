from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError
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


def test_object_front_door_retries_unknown_guard_owner(tmp_path: Path, monkeypatch) -> None:
    """An unknown unlock/close owner remains reachable at the next public write."""

    value = {"value": "unknown-guard-front-door"}
    target = _object_target(tmp_path, value)
    original_release = DirectoryMutationGuard._release_resource
    original_retry = DirectoryMutationGuard.retry_release
    injected_guard: DirectoryMutationGuard | None = None
    injected = False
    retry_ready = False
    retry_called = False

    def fail_unlock(_resource: object) -> None:
        if not retry_ready:
            raise OSError("injected unlock failure")

    def fail_close(_resource: object) -> None:
        if not retry_ready:
            raise OSError("injected close failure")

    def fail_once(guard, resource, unlocker, closer):
        nonlocal injected, injected_guard
        if not injected:
            injected = True
            injected_guard = guard
            # Close the real descriptor before substituting inert retry state.
            try:
                unlocker(resource)
            finally:
                closer(resource)
            return original_release(guard, object(), fail_unlock, fail_close)
        return original_release(guard, resource, unlocker, closer)

    def observe_retry(guard):
        nonlocal retry_called
        if guard is injected_guard:
            retry_called = True
        return original_retry(guard)

    monkeypatch.setattr(DirectoryMutationGuard, "_release_resource", fail_once)
    monkeypatch.setattr(DirectoryMutationGuard, "retry_release", observe_retry)

    with pytest.raises(BaseException, match="unlock|close|unknown"):
        ObjectStore(tmp_path).write("task", TASK_ID, 1, value)
    assert injected_guard is not None
    assert target.exists()

    retry_ready = True
    assert ObjectStore(tmp_path).write("task", TASK_ID, 1, value) == target
    assert retry_called


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
    assert [name for _path, name in calls] == [TRANSACTION_GUARD_NAME, TRANSACTION_GUARD_NAME]
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


def test_close_only_ticket_is_typed_and_never_mutates_namespace(tmp_path: Path) -> None:
    """Resource-only close retries cannot carry a namespace callback."""

    import research_system.store.anchor as anchor_module

    marker = tmp_path / "close-only-marker"
    marker.write_bytes(b"preserve")
    attempts = 0

    def close_only(_resource):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("injected close-only failure")

    ticket = anchor_module._close_only_ticket("anchor-v2-test", object(), close_only)
    anchor_module._retain_close_ticket(ticket)
    with pytest.raises(ConflictError, match="close remains pending"):
        drain_close_quarantine()
    assert attempts == 1
    assert marker.exists()
    drain_close_quarantine()
    assert attempts == 2
    assert marker.exists()
    with pytest.raises(TypeError):
        anchor_module._retain_close_ticket(object())


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


def test_unknown_guard_owner_is_retained_and_drained_before_next_transaction(tmp_path: Path, monkeypatch) -> None:
    """A failed guard release is a reachable full owner, not lost state."""

    first_guard: DirectoryMutationGuard | None = None
    retry_called = False
    original_retry = DirectoryMutationGuard.retry_release

    class _GuardContext:
        def __init__(self, guard: DirectoryMutationGuard, *, fail_on_exit: bool) -> None:
            self.guard = guard
            self.fail_on_exit = fail_on_exit

        def __enter__(self):
            return self.guard

        def __exit__(self, _exc_type, _exc, _traceback):
            if self.fail_on_exit:
                self.guard._release_state = "unknown"
                raise OSError("injected unknown guard release")
            self.guard._release_state = "released"
            return False

    class _Anchor:
        final_path = tmp_path
        identity = DirectoryIdentity("posix-dev-inode-v1", 7001, b"unknown-guard")

        def __init__(self) -> None:
            self.calls: list[str] = []

        def acquire_mutation_guard(self, name: str):
            self.calls.append(name)
            guard = DirectoryMutationGuard(self, name)
            if len(self.calls) == 1:
                guard._retained_release = (object(), lambda _resource: None, lambda _resource: None)
            return _GuardContext(guard, fail_on_exit=len(self.calls) == 1)

    def observe_retry(guard: DirectoryMutationGuard) -> None:
        nonlocal retry_called
        if guard is first_guard:
            retry_called = True
        return original_retry(guard)

    monkeypatch.setattr(DirectoryMutationGuard, "retry_release", observe_retry)
    anchor = _Anchor()
    transaction = DirectoryTransaction(anchor)
    transaction.__enter__()
    with pytest.raises(OSError, match="unknown guard release"):
        transaction.__exit__(None, None, None)
    assert transaction.exit_status.guard_state == "unknown"
    first_guard = transaction._retained_guard
    assert first_guard is not None

    next_transaction = DirectoryTransaction(anchor)
    next_transaction.__enter__()
    next_transaction.__exit__(None, None, None)
    assert retry_called
    assert transaction.exit_status.guard_state == "released"
    assert anchor.calls == [TRANSACTION_GUARD_NAME, TRANSACTION_GUARD_NAME]


def test_concurrent_same_object_writers_serialize_one_revision(tmp_path: Path, monkeypatch) -> None:
    """Two same-object writers never execute staging concurrently."""

    first_stage = threading.Event()
    second_started = threading.Event()
    release_first = threading.Event()
    guard_entries_before_release: list[bool] = []
    original_stage = DirectoryTransaction._stage_owned_private
    import research_system.store.anchor as anchor_module

    original_guard = anchor_module._DirectoryAnchor.acquire_mutation_guard

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
            if close_attempts <= 2:
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
        # the retained-owner registry for the successor entry to drain.
        with pytest.raises(ConflictError, match="stage cleanup|close|pending"):
            with DirectoryTransaction(anchor) as transaction:
                stage = transaction.stage("owned-stage", b"owned-stage")
                stage_name = stage.name
                with pytest.raises(ConflictError, match="stage cleanup|close|pending"):
                    transaction.discard_stage(stage)

        with DirectoryTransaction(anchor):
            pass
        assert close_attempts >= 3
        assert not (root / stage_name).exists()
    finally:
        anchor.close()
