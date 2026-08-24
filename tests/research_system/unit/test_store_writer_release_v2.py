from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError
from research_system.store.lock import CompositeWriterLock, WriterLock


class _SyntheticMemberLock:
    """A deterministic composite member with an explicit release plan."""

    def __init__(
        self,
        path: Path,
        identity: dict[str, object],
        events: list[str],
        *,
        enter_error: BaseException | None = None,
        release_plan: list[tuple[BaseException | None, bool]] | None = None,
    ) -> None:
        self.path = Path(path)
        self.identity = dict(identity)
        self.events = events
        self.enter_error = enter_error
        self.release_plan = list(release_plan or [])
        self.release_pending = False
        self.release_calls = 0
        self._entered = False
        self._composite_owner: object | None = None

    def __enter__(self) -> _SyntheticMemberLock:
        if self.enter_error is not None:
            error, self.enter_error = self.enter_error, None
            raise error
        self.path.write_bytes(canonical_bytes(self.identity))
        self._entered = True
        self.events.append(f"enter:{self.path}")
        return self

    def _transfer_to_composite(self, owner: object) -> None:
        if not self._entered:
            raise ConflictError("synthetic member was not entered")
        self._composite_owner = owner

    def _release_from_composite(
        self,
        owner: object,
        _exc_type=None,
        _exc=None,
        _traceback=None,
    ) -> bool:
        if self._composite_owner is not owner:
            raise ConflictError("synthetic member composite owner is not live")
        self.release_calls += 1
        self.events.append(f"release:{self.path}")
        error, self.release_pending = self.release_plan.pop(0) if self.release_plan else (None, False)
        if error is not None:
            raise error
        self.path.unlink()
        self._entered = False
        self._composite_owner = None
        return False

    def verify_live(self, _expected_runtime_path: Path) -> None:
        if not self._entered:
            raise ConflictError("synthetic member is not live")


def _roots(base: Path, count: int) -> tuple[Path, ...]:
    roots = tuple(base / f"root-{index}" for index in range(count))
    for root in roots:
        (root / "runtime").mkdir(parents=True)
    return roots


def _causal_text(error: BaseException | None) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        parts.append(repr(error))
        error = error.__cause__ or error.__context__
    return "\n".join(parts)


def test_lock_facade_exports_exact_writer_public_types() -> None:
    import research_system.store.anchor as anchor
    import research_system.store.lock as lock_facade
    import research_system.store.writer as writer

    for name in (
        "CompositeWriterLock",
        "LockedRoot",
        "WriterLock",
        "WriterLockContentionError",
        "inspect_lock",
        "remove_stale_lock",
    ):
        assert getattr(lock_facade, name) is getattr(writer, name)
    for name in ("DirectoryAnchor", "DirectoryIdentity", "DirectoryMutationGuard"):
        assert getattr(lock_facade, name) is getattr(anchor, name)
    for name in ("DirectoryAnchor", "DirectoryIdentity"):
        assert getattr(writer, name) is getattr(anchor, name)
    assert inspect.signature(lock_facade.WriterLock) == inspect.signature(writer.WriterLock)
    assert not hasattr(lock_facade, "_DirectoryAnchor")


def test_writer_posix_staging_capability_remains_on_the_physical_anchor(tmp_path: Path) -> None:
    """The Linux writer's private stage is owned by the extracted anchor module."""

    import research_system.store.anchor as anchor

    physical = anchor.open_registered_root_anchor(tmp_path, delete_protect=True)
    try:
        data = b"writer-stage"
        name, identity = physical.stage_private_file("writer.lock", data)
        observed, observed_identity = physical.read_regular_file_with_identity(name)

        assert observed == data
        assert name.startswith(".writer.lock.") and name.endswith(".tmp")
        assert os.path.samestat(identity, observed_identity)

        with physical.acquire_mutation_guard(anchor.TRANSACTION_GUARD_NAME) as guard:
            physical.remove_exact_generation(name, identity, data, guard=guard)
        assert name not in physical.list_names()
    finally:
        physical.close()


def test_writer_lock_treats_an_unfinished_posix_release_as_retainable() -> None:
    """remediation-red: composite cleanup retries live POSIX release authority."""

    writer = WriterLock(Path("posix-writer.lock"), {"writer_id": "posix-release-state"})
    writer._posix_backend_entered = True
    writer._posix_release_complete = False

    assert writer._has_retained_release()

    writer._posix_release_complete = True
    assert not writer._has_retained_release()


def test_partial_composite_acquisition_retains_one_owner_until_safe_point(tmp_path: Path) -> None:
    roots = _roots(tmp_path, 2)
    drain_root = _roots(tmp_path / "drain", 1)[0]
    events: list[str] = []
    created: list[_SyntheticMemberLock] = []
    first_attempt = True

    def factory(path: Path, identity: dict[str, object]) -> _SyntheticMemberLock:
        nonlocal first_attempt
        index = len(created)
        enter_error = ConflictError("injected partial member enter") if first_attempt and index == 1 else None
        release_plan = (
            [(ConflictError("injected pending member release"), True)] * 3 + [(None, False)]
            if first_attempt and index == 0
            else []
        )
        member = _SyntheticMemberLock(
            path,
            identity,
            events,
            enter_error=enter_error,
            release_plan=release_plan,
        )
        created.append(member)
        if enter_error is not None:
            first_attempt = False
        return member

    candidate = CompositeWriterLock(roots, {"command_id": "partial-retained-owner"}, lock_factory=factory)
    with pytest.raises(ConflictError, match="partial member enter"):
        candidate.__enter__()
    assert created[0].release_pending and created[0].release_calls == 3

    with CompositeWriterLock(
        (drain_root,),
        {"command_id": "partial-retained-owner-drain"},
        lock_factory=lambda path, identity: _SyntheticMemberLock(path, identity, events),
    ):
        pass

    assert created[0].release_calls == 4
    assert not created[0].release_pending


def test_failed_composite_release_is_retried_at_next_public_safe_point(tmp_path: Path) -> None:
    root = _roots(tmp_path, 1)[0]
    drain_root = _roots(tmp_path / "drain", 1)[0]
    events: list[str] = []
    created: list[_SyntheticMemberLock] = []

    def factory(path: Path, identity: dict[str, object]) -> _SyntheticMemberLock:
        member = _SyntheticMemberLock(
            path,
            identity,
            events,
            release_plan=[(ConflictError("injected pending release"), True)] * 3 + [(None, False)],
        )
        created.append(member)
        return member

    owner = CompositeWriterLock((root,), {"command_id": "pending-release"}, lock_factory=factory)
    owner.__enter__()
    with pytest.raises(ConflictError, match="pending release"):
        owner.__exit__(None, None, None)
    assert created[0].release_pending and created[0].release_calls == 3

    with CompositeWriterLock(
        (drain_root,),
        {"command_id": "pending-release-drain"},
        lock_factory=lambda path, identity: _SyntheticMemberLock(path, identity, events),
    ):
        pass

    assert created[0].release_calls == 4
    assert not created[0].release_pending


def test_composite_discards_a_transient_member_release_error_after_its_retry_succeeds(tmp_path: Path) -> None:
    """remediation-red: a recovered release error is not a terminal composite failure."""

    root = _roots(tmp_path, 1)[0]
    events: list[str] = []
    created: list[_SyntheticMemberLock] = []

    def factory(path: Path, identity: dict[str, object]) -> _SyntheticMemberLock:
        member = _SyntheticMemberLock(
            path,
            identity,
            events,
            release_plan=[(ConflictError("injected transient release"), True), (None, False)],
        )
        created.append(member)
        return member

    candidate = CompositeWriterLock((root,), {"command_id": "transient-release"}, lock_factory=factory)
    candidate.__enter__()
    candidate.__exit__(None, None, None)

    assert created[0].release_calls == 2
    assert not created[0].release_pending
    assert not candidate._active_members


def test_locked_root_preserves_directory_open_failure(tmp_path: Path, monkeypatch) -> None:
    """remediation-red: a failed observer open is not replaced by a None close."""

    import research_system.store.writer as writer_module

    root = _roots(tmp_path, 1)[0]
    candidate = CompositeWriterLock((root,), {"command_id": "locked-root-open-failure"})
    candidate.__enter__()

    real_open = writer_module._open_directory_anchor

    def reject_observer(path: Path, *args, **kwargs):
        if Path(path) == root:
            raise RuntimeError("injected observer open failure")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(writer_module, "_open_directory_anchor", reject_observer)
    try:
        with pytest.raises(RuntimeError, match="injected observer open failure"):
            candidate.locked_root(root)
    finally:
        candidate.__exit__(None, None, None)


def test_composite_acquisition_fence_preserves_directory_open_failure(tmp_path: Path, monkeypatch) -> None:
    """remediation-red: a failed final fence open is not replaced by a None close."""

    import research_system.store.writer as writer_module

    root = _roots(tmp_path, 1)[0]
    candidate = CompositeWriterLock((root,), {"command_id": "acquisition-fence-open-failure"})
    real_open = writer_module._open_directory_anchor
    root_open_count = 0

    def reject_second_root_open(path: Path, *args, **kwargs):
        nonlocal root_open_count
        if Path(path) == root:
            root_open_count += 1
            if root_open_count == 2:
                raise RuntimeError("injected final fence open failure")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(writer_module, "_open_directory_anchor", reject_second_root_open)

    with pytest.raises(RuntimeError, match="injected final fence open failure"):
        candidate.__enter__()

    assert root_open_count == 2
    assert not (root / "runtime" / "writer.lock").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows stateless Delete=True owner control")
def test_windows_stale_lock_removal_retains_delete_true_owner_until_the_next_safe_point(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: a release-less deletion keeps full transaction ownership."""

    import research_system.store.anchor as anchor_module
    import research_system.store.writer as writer_module

    path = tmp_path / "writer.lock"
    stale = {
        "process_id": "919191",
        "process_instance_id": "dead-process-instance",
        "writer_id": "stale-owner",
    }
    path.write_bytes(canonical_bytes(stale))
    real_process_instance_id = writer_module.process_instance_id
    monkeypatch.setattr(writer_module, "process_instance_id", lambda _pid: None)
    monkeypatch.setattr(
        writer_module.os,
        "kill",
        lambda _pid, _signal: (_ for _ in ()).throw(ProcessLookupError()),
    )
    state, observed, _record = writer_module.inspect_lock(path)
    assert state == "stale" and observed is not None

    real_open = anchor_module._windows_open_handle
    real_close = anchor_module._windows_close_handle
    target_handles: set[int] = set()
    close_attempts = 0

    def capture_delete_handle(candidate, *args, **kwargs):
        handle = real_open(candidate, *args, **kwargs)
        if Path(candidate).name == path.name and kwargs.get("delete_access"):
            target_handles.add(int(getattr(handle, "value", handle)))
        return handle

    def fail_delete_close_until_safe_point(handle):
        nonlocal close_attempts
        value = int(getattr(handle, "value", handle))
        if value in target_handles:
            close_attempts += 1
            if close_attempts <= 2:
                raise OSError("injected stateless Delete=True CloseHandle failure")
        return real_close(handle)

    def reject_close_only(*_args, **_kwargs):
        raise AssertionError("Delete=True stale-lock owner was downgraded to close-only state")

    monkeypatch.setattr(anchor_module, "_windows_open_handle", capture_delete_handle)
    monkeypatch.setattr(anchor_module, "_windows_close_handle", fail_delete_close_until_safe_point)
    monkeypatch.setattr(anchor_module, "_retain_close_ticket", reject_close_only)

    assert not writer_module.remove_stale_lock(path, observed)
    assert close_attempts == 2

    monkeypatch.setattr(writer_module, "process_instance_id", real_process_instance_id)
    with writer_module.WriterLock(path, {"writer_id": "successor"}):
        assert path.exists()

    assert close_attempts >= 3
    assert not path.exists()


def test_body_error_remains_primary_when_all_member_releases_fail(tmp_path: Path) -> None:
    roots = _roots(tmp_path, 2)
    events: list[str] = []
    release_errors = [RuntimeError("release root-0"), RuntimeError("release root-1")]
    created: list[_SyntheticMemberLock] = []

    def factory(path: Path, identity: dict[str, object]) -> _SyntheticMemberLock:
        member = _SyntheticMemberLock(path, identity, events, release_plan=[(release_errors[len(created)], False)])
        created.append(member)
        return member

    owner = CompositeWriterLock(roots, {"command_id": "body-error-priority"}, lock_factory=factory)
    primary = RuntimeError("exact body error")
    with pytest.raises(RuntimeError) as caught:
        with owner:
            raise primary

    assert caught.value is primary
    assert [member.release_calls for member in created] == [1, 1]
    causal = _causal_text(caught.value.__cause__)
    assert "release root-0" in causal
    assert "release root-1" in causal
