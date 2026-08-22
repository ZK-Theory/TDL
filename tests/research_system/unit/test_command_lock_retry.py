from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

import research_system.command.service as service_module
from research_system.command.models import Command
from research_system.command.service import CommandService
from research_system.errors import ConflictError
from research_system.store.lock import WriterLockContentionError


def _recovery_service(tmp_path) -> CommandService:
    service = object.__new__(CommandService)
    service.control_root = tmp_path
    service.recovery_lock_timeout_seconds = 1.0
    service._monotonic = lambda: 0.0
    service._lock_wait = lambda _seconds: None
    return service


def _submission_service(tmp_path) -> CommandService:
    service = object.__new__(CommandService)
    service.control_root = tmp_path
    service._restore_admission_sequence_lock = threading.Lock()
    service._prepare_moved_restore = lambda _command: None
    service._canonical_authority_resolver = lambda: None
    service._monotonic = lambda: 0.0
    service._lock_wait = lambda _seconds: None
    service.release_lock_timeout_seconds = 1.0
    service.ledger = SimpleNamespace(snapshot=lambda: "one-verified-snapshot")
    service._revalidate_prepared_moved_restore = lambda _command, _prepared, _snapshot: None
    return service


def _lifecycle_command() -> Command:
    return Command(
        {
            "command_id": "cmd_01978abc-0001-7000-8000-000000003001",
            "command_type": "CreateTask",
            "payload": {},
        }
    )


def test_scoped_activation_recovery_propagates_non_contention_conflict_without_retry(tmp_path, monkeypatch):
    """remediation-red: only the dedicated lock-contention error may retry."""

    service = _recovery_service(tmp_path)
    attempts = 0

    class GenericConflictLock:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            nonlocal attempts
            attempts += 1
            raise ConflictError("writer root identity changed")

    monkeypatch.setattr(service_module, "WriterLock", GenericConflictLock)
    monkeypatch.setattr(
        service_module,
        "inspect_lock",
        lambda _path: pytest.fail("a non-contention conflict must not inspect or reclaim a lock"),
    )
    monkeypatch.setattr(
        service,
        "_lock_wait",
        lambda _seconds: pytest.fail("a non-contention conflict must not wait and retry"),
    )

    with pytest.raises(ConflictError, match="writer root identity changed"):
        service._take_scoped_activation_recovery_lock({"command_id": "cmd_recovery"})

    assert attempts == 1


def test_scoped_activation_recovery_retries_writer_lock_contention(tmp_path, monkeypatch):
    """preservation-green: the dedicated contention signal still retries."""

    service = _recovery_service(tmp_path)
    waits: list[float] = []
    attempts = 0

    class ContendedThenAcquiredLock:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise WriterLockContentionError("writer lock exists")
            return self

    monkeypatch.setattr(service_module, "WriterLock", ContendedThenAcquiredLock)
    monkeypatch.setattr(service_module, "inspect_lock", lambda _path: ("live", None, None))
    monkeypatch.setattr(service, "_lock_wait", waits.append)

    lock = service._take_scoped_activation_recovery_lock({"command_id": "cmd_recovery"})

    assert lock is not None
    assert attempts == 2
    assert waits == [0.01]


def test_submission_lock_propagates_non_contention_conflict_without_retry(tmp_path, monkeypatch):
    """remediation-red: a composite-lock integrity conflict must not be retried."""

    service = _submission_service(tmp_path)
    attempts = 0
    waits: list[float] = []
    now = [0.0]

    class GenericConflictCompositeLock:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            nonlocal attempts
            attempts += 1
            raise ConflictError("composite root identity changed")

    service._monotonic = lambda: now[0]
    service._lock_wait = lambda seconds: (waits.append(seconds), now.__setitem__(0, 1.0))
    monkeypatch.setattr(service_module, "CompositeWriterLock", GenericConflictCompositeLock)

    with pytest.raises(ConflictError, match="composite root identity changed"):
        with service._submission_lock(_lifecycle_command()):
            pytest.fail("a failed lock acquisition must not yield a submission lease")

    assert attempts == 1
    assert waits == []


def test_submission_lock_retries_writer_lock_contention(tmp_path, monkeypatch):
    """preservation-green: coordinated submits keep bounded contention retry."""

    service = _submission_service(tmp_path)
    attempts = 0
    waits: list[float] = []

    class ContendedThenAcquiredCompositeLock:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise WriterLockContentionError("writer lock exists")
            return self

        def __exit__(self, *_args) -> bool:
            return False

    service._lock_wait = waits.append
    monkeypatch.setattr(service_module, "CompositeWriterLock", ContendedThenAcquiredCompositeLock)

    with service._submission_lock(_lifecycle_command()) as lease:
        assert lease.snapshot == "one-verified-snapshot"

    assert attempts == 2
    assert waits == [0.01]
