from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError
from research_system.store.lock import CompositeWriterLock


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
