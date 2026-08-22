from __future__ import annotations

import multiprocessing
import os
import threading
from pathlib import Path

import pytest

from research_system.command.service import CommandService
from research_system.errors import ConflictError
from research_system.store.lock import WriterLock, inspect_lock
from research_system.store.spec_preparation_fence import SpecPreparationFence
from tests.research_system.factories import control_plane


def _contend_from_another_process(control_root: str, result_queue: multiprocessing.queues.Queue[str]) -> None:
    try:
        with SpecPreparationFence(Path(control_root)):
            result_queue.put("acquired")
    except ConflictError:
        result_queue.put("conflict")


def _acquire_fence_then_crash(control_root: str, acquired: object) -> None:
    fence = SpecPreparationFence(Path(control_root))
    fence.__enter__()
    acquired.set()  # type: ignore[attr-defined]
    os._exit(23)


def _hold_fence_until_released(control_root: str, acquired: object, release: object) -> None:
    with SpecPreparationFence(Path(control_root)):
        acquired.set()  # type: ignore[attr-defined]
        release.wait(timeout=15)  # type: ignore[attr-defined]


def test_spec_preparation_fence_is_reentrant_but_rejects_a_competing_writer(tmp_path: Path) -> None:
    """Nested public writers share the saga fence; another writer cannot."""

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    result: list[BaseException | None] = []

    def contend() -> None:
        try:
            with SpecPreparationFence(tmp_path):
                result.append(None)
        except BaseException as error:  # the result is asserted by the owning thread
            result.append(error)

    with SpecPreparationFence(tmp_path):
        with SpecPreparationFence(tmp_path):
            assert (runtime / "spec-preparation.lock").is_file()
        contender = threading.Thread(target=contend)
        contender.start()
        contender.join(timeout=5)
        assert not contender.is_alive()
        assert len(result) == 1
        assert isinstance(result[0], ConflictError)

    assert not (runtime / "spec-preparation.lock").exists()
    with SpecPreparationFence(tmp_path):
        assert (runtime / "spec-preparation.lock").is_file()


def test_windows_spec_preparation_fence_physically_anchors_runtime(tmp_path: Path) -> None:
    """The lock namespace cannot be replaced while the saga fence is live."""

    if os.name != "nt":
        pytest.skip("Windows delete-protected directory anchor")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    displaced = tmp_path / "runtime-displaced"
    moved = False

    with SpecPreparationFence(tmp_path):
        try:
            runtime.rename(displaced)
            moved = True
            displaced.rename(runtime)
        except PermissionError:
            pass
        assert not moved


def test_spec_preparation_fence_rejects_same_instance_reentry_and_out_of_order_exit(tmp_path: Path) -> None:
    """Only independently entered instances can nest, and they exit LIFO."""

    (tmp_path / "runtime").mkdir()
    outer = SpecPreparationFence(tmp_path)
    inner = SpecPreparationFence(tmp_path)
    outer.__enter__()
    try:
        with pytest.raises(RuntimeError, match="already entered"):
            outer.__enter__()
        inner.__enter__()
        try:
            with pytest.raises(RuntimeError, match="reverse entry order"):
                outer.__exit__(None, None, None)
            assert (tmp_path / "runtime" / "spec-preparation.lock").is_file()
        finally:
            inner.__exit__(None, None, None)
    finally:
        outer.__exit__(None, None, None)
    assert not (tmp_path / "runtime" / "spec-preparation.lock").exists()
    with pytest.raises(RuntimeError, match="without matching entry"):
        outer.__exit__(None, None, None)


def test_spec_preparation_fence_rolls_back_a_publication_when_acquire_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exception after WriterLock publication cannot orphan the fence lock."""

    (tmp_path / "runtime").mkdir()
    original_enter = WriterLock.__enter__

    def publish_then_fail(lock: WriterLock) -> WriterLock:
        original_enter(lock)
        raise RuntimeError("injected acquire failure after publication")

    monkeypatch.setattr(WriterLock, "__enter__", publish_then_fail)
    with pytest.raises(RuntimeError, match="injected acquire failure"):
        SpecPreparationFence(tmp_path).__enter__()
    assert not (tmp_path / "runtime" / "spec-preparation.lock").exists()


def test_spec_preparation_fence_rejects_wrong_thread_exit_without_releasing_lock(tmp_path: Path) -> None:
    """Only the thread that entered an instance may release its durable lock."""

    (tmp_path / "runtime").mkdir()
    fence = SpecPreparationFence(tmp_path)
    errors: list[BaseException] = []
    fence.__enter__()
    try:
        contender = threading.Thread(
            target=lambda: _attempt_exit_from_another_thread(fence, errors),
        )
        contender.start()
        contender.join(timeout=5)
        assert not contender.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)
        assert "non-owning thread" in str(errors[0])
        assert (tmp_path / "runtime" / "spec-preparation.lock").is_file()
    finally:
        fence.__exit__(None, None, None)


def test_spec_preparation_fence_keeps_owner_state_when_release_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A release failure is fail-safe and the owning instance remains recoverable."""

    (tmp_path / "runtime").mkdir()
    fence = SpecPreparationFence(tmp_path)
    original_exit = WriterLock.__exit__

    def fail_release(_lock: WriterLock, *_args: object) -> bool:
        raise RuntimeError("injected release failure")

    fence.__enter__()
    monkeypatch.setattr(WriterLock, "__exit__", fail_release)
    with pytest.raises(RuntimeError, match="injected release failure"):
        fence.__exit__(None, None, None)
    assert (tmp_path / "runtime" / "spec-preparation.lock").is_file()
    monkeypatch.setattr(WriterLock, "__exit__", original_exit)
    fence.__exit__(None, None, None)
    assert not (tmp_path / "runtime" / "spec-preparation.lock").exists()


def _attempt_exit_from_another_thread(fence: SpecPreparationFence, errors: list[BaseException]) -> None:
    try:
        fence.__exit__(None, None, None)
    except BaseException as error:  # asserted by the owning thread
        errors.append(error)


def test_spec_preparation_fence_rejects_a_contending_process_and_releases_after_exit(tmp_path: Path) -> None:
    """The durable WriterLock also excludes a separate process."""

    (tmp_path / "runtime").mkdir()
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    with SpecPreparationFence(tmp_path):
        contender = context.Process(target=_contend_from_another_process, args=(str(tmp_path), result_queue))
        contender.start()
        contender.join(timeout=15)
        assert not contender.is_alive()
        assert contender.exitcode == 0
        assert result_queue.get(timeout=5) == "conflict"
    successor = context.Process(target=_contend_from_another_process, args=(str(tmp_path), result_queue))
    successor.start()
    successor.join(timeout=15)
    assert not successor.is_alive()
    assert successor.exitcode == 0
    assert result_queue.get(timeout=5) == "acquired"


def test_command_service_startup_recovery_reclaims_a_stale_fence_after_owner_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dead SPEC owner cannot wedge startup marker recovery indefinitely."""

    harness = control_plane(tmp_path, auto_authority=False)
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    crashed_owner = context.Process(
        target=_acquire_fence_then_crash,
        args=(str(harness.service.control_root), acquired),
    )
    crashed_owner.start()
    assert acquired.wait(timeout=10)
    crashed_owner.join(timeout=15)
    assert not crashed_owner.is_alive()
    assert crashed_owner.exitcode == 23
    lock_path = harness.service.control_root / "runtime" / "spec-preparation.lock"
    assert inspect_lock(lock_path)[0] == "stale"
    calls: list[str] = []
    monkeypatch.setattr(CommandService, "_recover_scoped_activation_markers", lambda _self: calls.append("scoped"))
    monkeypatch.setattr(CommandService, "_recover_owner_publication_markers", lambda _self: calls.append("owner"))

    CommandService(
        harness.service.control_root,
        harness.ledger,
        harness.objects,
        harness.receipts,
        harness.schemas,
        authority_resolver=harness.authority_resolver,
        clock=harness.service.clock,
    )

    assert calls == ["scoped", "owner"]
    assert not lock_path.exists()


def test_spec_preparation_fence_never_reclaims_a_live_process_owner(tmp_path: Path) -> None:
    """Process-instance revalidation refuses to steal the active saga fence."""

    (tmp_path / "runtime").mkdir()
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    release = context.Event()
    owner = context.Process(target=_hold_fence_until_released, args=(str(tmp_path), acquired, release))
    owner.start()
    try:
        assert acquired.wait(timeout=10)
        lock_path = tmp_path / "runtime" / "spec-preparation.lock"
        observed = lock_path.read_bytes()
        assert inspect_lock(lock_path)[0] == "live"
        with pytest.raises(ConflictError, match="writer lock exists"):
            with SpecPreparationFence(tmp_path):
                pass
        assert lock_path.read_bytes() == observed
    finally:
        release.set()
        owner.join(timeout=15)
        if owner.is_alive():
            owner.terminate()
            owner.join(timeout=5)
    assert owner.exitcode == 0
    assert not (tmp_path / "runtime" / "spec-preparation.lock").exists()


def test_command_service_startup_recovery_cannot_bypass_an_active_spec_saga(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Startup marker recovery enters the same fence before any recovery write."""

    harness = control_plane(tmp_path, auto_authority=False)
    calls: list[str] = []

    def recover_scoped(_service: CommandService) -> None:
        calls.append("scoped")

    def recover_owner(_service: CommandService) -> None:
        calls.append("owner")

    monkeypatch.setattr(CommandService, "_recover_scoped_activation_markers", recover_scoped)
    monkeypatch.setattr(CommandService, "_recover_owner_publication_markers", recover_owner)
    result: list[BaseException | None] = []

    def construct_contender() -> None:
        try:
            CommandService(
                harness.service.control_root,
                harness.ledger,
                harness.objects,
                harness.receipts,
                harness.schemas,
                authority_resolver=harness.authority_resolver,
                clock=harness.service.clock,
            )
            result.append(None)
        except BaseException as error:  # asserted by the owning thread
            result.append(error)

    with SpecPreparationFence(harness.service.control_root):
        contender = threading.Thread(target=construct_contender)
        contender.start()
        contender.join(timeout=5)
        assert not contender.is_alive()
        assert len(result) == 1
        assert isinstance(result[0], ConflictError)
        assert calls == []

    CommandService(
        harness.service.control_root,
        harness.ledger,
        harness.objects,
        harness.receipts,
        harness.schemas,
        authority_resolver=harness.authority_resolver,
        clock=harness.service.clock,
    )
    assert calls == ["scoped", "owner"]
