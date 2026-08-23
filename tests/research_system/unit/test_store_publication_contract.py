from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat
import sys

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.store.lock import CompositeWriterLock, LockedRoot, WriterLock, WriterLockContentionError
from research_system.store.objects import ObjectStore, write_object


TASK_ID = "tsk_00000000-0000-7000-8000-000000000301"


def _object_directory(root: Path) -> Path:
    return root / "objects" / "task" / TASK_ID


def _object_target(root: Path, value: object) -> Path:
    data = canonical_bytes(value)
    return _object_directory(root) / f"00000001-{sha256_hex(data)}.json"


@contextmanager
def _locked_root(root: Path):
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    with CompositeWriterLock((root,), {"command_id": "cmd_store-publication-contract"}) as lock:
        yield lock.locked_root(root)


def _assert_generation_preserved_after_posix_quarantine(path: Path, expected: bytes) -> None:
    """A refused deletion must leave the substituted owner at its canonical name."""

    assert path.read_bytes() == expected


def test_writer_lock_reports_only_existing_lock_as_typed_contention(tmp_path: Path) -> None:
    path = tmp_path / "writer.lock"

    with WriterLock(path, {"writer_id": "first"}):
        with pytest.raises(WriterLockContentionError, match="writer lock exists"):
            with WriterLock(path, {"writer_id": "second"}):
                raise AssertionError("second writer entered lock")

    assert issubclass(WriterLockContentionError, ConflictError)


def test_writer_lock_fails_closed_before_publication_without_windows_exact_deletion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """preservation-green: unsupported POSIX cannot publish an unreleasable lease."""

    import research_system.store.lock as lock_module

    path = tmp_path / "uncreated" / "writer.lock"
    writer = WriterLock(path, {"writer_id": "unsupported-platform"})
    monkeypatch.setattr(lock_module, "_supports_exact_writer_lock_deletion", lambda: False)

    with pytest.raises(ConflictError, match="require Windows or Linux inode-safe locking"):
        writer.__enter__()

    assert not path.parent.exists()


@pytest.mark.skipif(os.name != "posix" or sys.platform != "linux", reason="Linux flock backend")
@pytest.mark.parametrize("failure", ["fsync", "verification"])
def test_linux_writer_rolls_back_an_exact_canonical_after_post_link_failure(
    tmp_path: Path,
    monkeypatch,
    failure: str,
) -> None:
    """A failed acquisition cannot strand the current process as canonical owner."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    failed = False
    method_name = "fsync" if failure == "fsync" else "read_regular_file_with_identity"
    original = getattr(lock_module._DirectoryAnchor, method_name)

    def fail_once(anchor, *args, **kwargs):
        nonlocal failed
        targets_canonical = failure == "fsync" or args == (path.name,)
        if targets_canonical and not failed:
            failed = True
            raise ConflictError(f"post-link {failure} failed")
        return original(anchor, *args, **kwargs)

    monkeypatch.setattr(lock_module._DirectoryAnchor, method_name, fail_once)
    with pytest.raises(ConflictError, match=f"post-link {failure} failed"):
        WriterLock(path, {"writer_id": "rejected-owner"}).__enter__()

    assert failed
    assert not path.exists()
    with WriterLock(path, {"writer_id": "next-owner"}):
        assert path.is_file()


@pytest.mark.skipif(os.name != "posix" or sys.platform != "linux", reason="Linux flock backend")
def test_linux_writer_retains_release_state_for_an_exact_retry(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "release-owner"})
    writer.__enter__()
    original = lock_module._posix_guarded_delete_lock
    failed = False

    def fail_once(candidate, *args, **kwargs):
        nonlocal failed
        if candidate == path and not failed:
            failed = True
            raise OSError("transient pre-delete failure")
        return original(candidate, *args, **kwargs)

    monkeypatch.setattr(lock_module, "_posix_guarded_delete_lock", fail_once)
    with pytest.raises(OSError, match="transient pre-delete failure"):
        writer.__exit__(None, None, None)
    assert path.is_file()

    assert writer.__exit__(None, None, None) is False
    assert not path.exists()
    assert writer.__exit__(None, None, None) is False


@pytest.mark.skipif(os.name != "posix" or sys.platform != "linux", reason="Linux flock backend")
def test_linux_writer_rejects_active_reentry_and_supports_sequential_reuse(tmp_path: Path) -> None:
    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "reusable-owner"})

    writer.__enter__()
    with pytest.raises(ConflictError, match="already active"):
        writer.__enter__()
    writer.__exit__(None, None, None)

    writer.__enter__()
    writer.__exit__(None, None, None)
    assert not path.exists()


@pytest.mark.skipif(os.name != "posix" or sys.platform != "linux", reason="Linux flock backend")
@pytest.mark.parametrize("during_enter_rollback", [False, True])
def test_linux_composite_retries_a_transient_member_release(
    tmp_path: Path, monkeypatch, during_enter_rollback: bool
) -> None:
    import research_system.store.lock as lock_module

    roots = tuple(tmp_path / name for name in (("a", "b") if during_enter_rollback else ("a",)))
    for root in roots:
        (root / "runtime").mkdir(parents=True)
    enabled = not during_enter_rollback
    failed = False
    original_delete = lock_module._posix_guarded_delete_lock

    def fail_release_once(candidate, *args, **kwargs):
        nonlocal failed
        if enabled and candidate.name == "writer.lock" and not failed:
            failed = True
            raise OSError("transient composite release")
        return original_delete(candidate, *args, **kwargs)

    monkeypatch.setattr(lock_module, "_posix_guarded_delete_lock", fail_release_once)
    if during_enter_rollback:
        created = 0

        def factory(path, identity):
            nonlocal created, enabled
            created += 1
            if created == 2:
                enabled = True
                raise RuntimeError("later member acquisition failed")
            return WriterLock(path, identity)

        candidate = CompositeWriterLock(roots, {"command_id": "cmd_enter-rollback"}, lock_factory=factory)
        with pytest.raises(RuntimeError, match="later member acquisition failed"):
            candidate.__enter__()
    else:
        candidate = CompositeWriterLock(roots, {"command_id": "cmd_normal-release"})
        candidate.__enter__()
        candidate.__exit__(None, None, None)
    assert failed and not candidate._active_members
    assert all(not (root / "runtime" / "writer.lock").exists() for root in roots)


def test_writer_lock_does_not_retype_identity_or_link_failures_as_contention(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    with pytest.raises(ConflictError) as identity_error:
        WriterLock(tmp_path / "writer.lock", {"process_id": "999999", "writer_id": "foreign"})
    assert type(identity_error.value) is ConflictError

    def deny_link(*_args, **_kwargs):
        raise PermissionError("link publication denied")

    monkeypatch.setattr(lock_module.os, "link", deny_link)
    with pytest.raises(PermissionError, match="publication denied"):
        with WriterLock(tmp_path / "denied.lock", {"writer_id": "denied"}):
            raise AssertionError("denied writer entered")
    assert not list(tmp_path.glob(".denied.lock.*.tmp"))


def test_windows_exact_generation_cleanup_retries_sharing_violation_without_winerror(
    tmp_path: Path, monkeypatch
) -> None:
    """remediation-red: a native sharing violation reaches the retryable cleanup seam."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    path.write_bytes(b"owned")

    def sharing_violation(*_args, **_kwargs):
        error = OSError(32, "sharing violation")
        error.winerror = None
        raise error

    monkeypatch.setattr(lock_module.os, "name", "nt")
    monkeypatch.setattr(lock_module, "_windows_open_handle", sharing_violation)

    with pytest.raises(lock_module._ExactGenerationBusyError, match="temporarily busy"):
        lock_module._delete_exact_regular_file(
            path,
            path.stat(),
            expected_bytes=b"owned",
            label="writer lock test",
        )


def _defer_private_staging_cleanup(monkeypatch, writer: WriterLock, before_failure=None):
    import research_system.store.lock as lock_module

    real_delete = lock_module._delete_exact_regular_file
    failures: list[bool] = []

    def fail_once(candidate: Path, *args, **kwargs) -> None:
        if candidate != writer.path and candidate.suffix == ".tmp" and not failures:
            failures.append(True)
            if before_failure is not None:
                before_failure()
            raise OSError("injected private staging cleanup failure")
        return real_delete(candidate, *args, **kwargs)

    monkeypatch.setattr(lock_module, "_delete_exact_regular_file", fail_once)
    return lock_module, failures


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-protected temporary cleanup")
@pytest.mark.parametrize("exit_state", [None, "missing", "foreign", "anchor-close"])
def test_writer_lock_durable_temporary_cleanup_failure_defers_under_a_tracked_lease(
    tmp_path: Path,
    monkeypatch,
    exit_state: str | None,
) -> None:
    """remediation-red: durable publication retains lock ownership until exit cleanup."""

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "failed-owner"})
    lock_module, cleanup_failures = _defer_private_staging_cleanup(monkeypatch, writer)
    if exit_state == "anchor-close":
        real_close = lock_module._DirectoryAnchor.close

        def fail_after_proof(anchor) -> None:
            real_close(anchor)
            raise OSError("injected parent anchor close failure")

        monkeypatch.setattr(lock_module._DirectoryAnchor, "close", fail_after_proof)

    assert writer.__enter__() is writer
    assert cleanup_failures
    assert path.read_bytes() == writer._data
    with pytest.raises(WriterLockContentionError, match="writer lock exists"):
        WriterLock(path, {"writer_id": "blocked-owner"}).__enter__()

    foreign = WriterLock(path, {"writer_id": "foreign-owner"})._data
    if exit_state in {"missing", "foreign"}:
        path.unlink()
    if exit_state == "foreign":
        path.write_bytes(foreign)
    if exit_state == "anchor-close":
        with pytest.raises(OSError, match="parent anchor close failure"):
            writer.__exit__(None, None, None)
    elif exit_state is not None:
        with pytest.raises(ConflictError):
            writer.__exit__(None, None, None)
    else:
        assert writer.__exit__(None, None, None) is False

    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
    if exit_state == "foreign":
        assert path.read_bytes() == foreign
        with pytest.raises(WriterLockContentionError, match="writer lock exists"):
            WriterLock(path, {"writer_id": "next-owner"}).__enter__()
        return
    assert not path.exists()
    with WriterLock(path, {"writer_id": "next-owner"}):
        assert path.is_file()
    assert not path.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-protected temporary cleanup")
@pytest.mark.parametrize("foreign_canonical", [True, False], ids=["foreign", "proof-unavailable"])
def test_writer_lock_cleanup_failure_preserves_foreign_or_rolls_back_owned_canonical(
    tmp_path: Path,
    monkeypatch,
    foreign_canonical: bool,
) -> None:
    """A failed proof keeps a foreign lock but rolls back the exact owned generation."""

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "failed-owner"})
    foreign = WriterLock(path, {"writer_id": "foreign-owner"})._data

    def substitute_foreign() -> None:
        assert path.read_bytes() == writer._data
        path.unlink()
        path.write_bytes(foreign)

    lock_module, cleanup_failures = _defer_private_staging_cleanup(
        monkeypatch,
        writer,
        substitute_foreign if foreign_canonical else None,
    )
    if not foreign_canonical:
        monkeypatch.setattr(
            lock_module,
            "_open_directory_anchor",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected ownership proof failure")),
        )

    with pytest.raises(ConflictError, match="canonical ownership cannot be verified"):
        writer.__enter__()

    assert cleanup_failures
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
    if foreign_canonical:
        assert path.read_bytes() == foreign
        with pytest.raises(WriterLockContentionError, match="writer lock exists"):
            WriterLock(path, {"writer_id": "next-owner"}).__enter__()
    else:
        assert not path.exists()
        with WriterLock(path, {"writer_id": "next-owner"}):
            assert path.is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-protected temporary cleanup")
def test_writer_lock_cleanup_failure_preserves_canonical_when_anchored_observation_is_unsafe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: an anchored reparse/non-regular rejection cannot trigger canonical rollback."""

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "failed-owner"})
    lock_module, cleanup_failures = _defer_private_staging_cleanup(monkeypatch, writer)
    deferred_delete = lock_module._delete_exact_regular_file
    canonical_deletions: list[Path] = []

    def record_delete(candidate: Path, *args, **kwargs) -> None:
        if candidate == path:
            canonical_deletions.append(candidate)
        return deferred_delete(candidate, *args, **kwargs)

    monkeypatch.setattr(lock_module, "_delete_exact_regular_file", record_delete)
    monkeypatch.setattr(
        lock_module,
        "_open_directory_anchor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ConflictError("injected canonical reparse rejection")),
    )

    with pytest.raises(ConflictError, match="canonical ownership cannot be verified"):
        writer.__enter__()

    assert cleanup_failures
    assert canonical_deletions == []
    assert path.read_bytes() == writer._data
    with pytest.raises(WriterLockContentionError, match="writer lock exists"):
        WriterLock(path, {"writer_id": "next-owner"}).__enter__()


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-protected publication rollback")
def test_writer_lock_post_publication_fsync_failure_rolls_back_and_raises(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: a non-durable canonical link is removed before entry fails."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "fsync-owner"})
    real_fsync_directory = lock_module.fsync_directory
    fsync_failed = False

    def fail_post_publication_fsync(directory: Path) -> None:
        nonlocal fsync_failed
        if Path(directory) == path.parent and not fsync_failed:
            fsync_failed = True
            assert path.read_bytes() == writer._data
            raise OSError("injected post-publication directory fsync failure")
        return real_fsync_directory(directory)

    monkeypatch.setattr(lock_module, "fsync_directory", fail_post_publication_fsync)

    with pytest.raises(OSError, match="post-publication directory fsync failure"):
        writer.__enter__()

    assert fsync_failed
    assert not path.exists()
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
    with WriterLock(path, {"writer_id": "next-owner"}):
        assert path.is_file()
    assert not path.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-protected publication rollback")
def test_writer_lock_post_publication_fsync_and_rollback_failure_leaves_a_fail_closed_poison(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: a failed non-durable rollback cannot enter protected work."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "fsync-owner"})
    real_delete = lock_module._delete_exact_regular_file
    real_fsync_directory = lock_module.fsync_directory
    fsync_failed = False
    rollback_failed = False

    def fail_post_publication_fsync(directory: Path) -> None:
        nonlocal fsync_failed
        if Path(directory) == path.parent and not fsync_failed:
            fsync_failed = True
            raise OSError("injected post-publication directory fsync failure")
        return real_fsync_directory(directory)

    def fail_canonical_rollback(candidate: Path, *args, **kwargs) -> None:
        nonlocal rollback_failed
        if candidate == path and not rollback_failed:
            rollback_failed = True
            raise OSError("injected canonical rollback failure")
        return real_delete(candidate, *args, **kwargs)

    monkeypatch.setattr(lock_module, "fsync_directory", fail_post_publication_fsync)
    monkeypatch.setattr(lock_module, "_delete_exact_regular_file", fail_canonical_rollback)

    with pytest.raises(OSError, match="post-publication directory fsync failure"):
        writer.__enter__()

    assert fsync_failed and rollback_failed
    assert path.read_bytes() == writer._data
    with pytest.raises(WriterLockContentionError, match="writer lock exists"):
        WriterLock(path, {"writer_id": "next-owner"}).__enter__()
    assert path.read_bytes() == writer._data


def test_writer_lock_uses_no_follow_link_publication_on_windows(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    real_link = os.link
    calls: list[tuple[bool, bool, bool]] = []

    def observe(source, destination, *args, follow_symlinks=True, **kwargs):
        calls.append((follow_symlinks, "src_dir_fd" in kwargs, "dst_dir_fd" in kwargs))
        return real_link(source, destination, *args, follow_symlinks=follow_symlinks, **kwargs)

    monkeypatch.setattr(lock_module.os, "link", observe)

    with WriterLock(path, {"writer_id": "no-follow"}):
        assert path.is_file()

    assert calls == [(False, os.name != "nt", os.name != "nt")]


def test_composite_writer_lock_still_enters_and_releases_its_canonical_lock(tmp_path: Path) -> None:
    root = tmp_path / "control"
    (root / "runtime").mkdir(parents=True)

    with CompositeWriterLock((root,), {"command_id": "cmd_store-publication-contract"}) as lease:
        assert lease.locked_root(root).runtime_final_path.name == "runtime"
        assert (root / "runtime" / "writer.lock").is_file()

    assert not (root / "runtime" / "writer.lock").exists()


def test_object_publication_uses_no_follow_hard_links(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.objects as object_module

    real_link = os.link
    calls: list[tuple[bool, bool, bool]] = []

    def observe(source, destination, *args, follow_symlinks=True, **kwargs):
        calls.append((follow_symlinks, "src_dir_fd" in kwargs, "dst_dir_fd" in kwargs))
        return real_link(source, destination, *args, follow_symlinks=follow_symlinks, **kwargs)

    monkeypatch.setattr(object_module.os, "link", observe)

    write_object(tmp_path, "task", TASK_ID, 1, {"value": "no-follow"})

    assert calls == [(False, os.name != "nt", os.name != "nt")] * 2


@pytest.mark.parametrize("swap_level", ("control-root", "objects", "kind", "object"))
def test_object_publication_keeps_every_effect_in_the_opened_object_directory_generation(
    tmp_path: Path,
    monkeypatch,
    swap_level: str,
) -> None:
    """remediation-red: no ancestor swap redirects an object transaction."""

    import research_system.store.objects as object_module

    control_root = tmp_path / "control"
    directory = _object_directory(control_root)
    swap_path, replacement_tail = {
        "control-root": (control_root, ("objects", "task", TASK_ID)),
        "objects": (control_root / "objects", ("task", TASK_ID)),
        "kind": (control_root / "objects" / "task", (TASK_ID,)),
        "object": (directory, ()),
    }[swap_level]
    held_path = swap_path.with_name(f"{swap_path.name}-held-generation")
    held_directory = held_path.joinpath(*replacement_tail)
    real_open = object_module.os.open
    swapped = False
    rename_rejected = False

    def swap_before_private_stage(path, flags, *args, **kwargs):
        nonlocal swapped, rename_rejected
        if not swapped and Path(path).name.endswith(".tmp") and flags & os.O_CREAT:
            try:
                swap_path.rename(held_path)
                directory.mkdir(parents=True)
            except OSError:
                rename_rejected = True
                raise
            swapped = True
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(object_module.os, "open", swap_before_private_stage)

    if os.name == "nt":
        with pytest.raises(OSError):
            write_object(control_root, "task", TASK_ID, 1, {"value": "anchored"})
        assert rename_rejected
        assert not held_path.exists()
        assert not list(directory.glob("00000001-*.json"))
        return

    with pytest.raises(ConflictError, match="final generation is unavailable|directory identity changed"):
        write_object(control_root, "task", TASK_ID, 1, {"value": "anchored"})

    assert swapped
    assert not list(directory.iterdir())
    assert not list(held_directory.glob("00000001-*.json"))
    assert len(list(held_directory.glob(".*.tmp"))) == 1


def test_object_publication_rolls_back_its_owned_final_after_an_ancestor_move(tmp_path: Path, monkeypatch) -> None:
    """remediation-red: parent-chain failure after final publication leaves no final behind."""

    import research_system.store.objects as object_module

    control_root = tmp_path / "control"
    directory = _object_directory(control_root)
    swap_path = directory if os.name == "nt" else control_root
    held_path = swap_path.with_name(f"{swap_path.name}-held-generation")
    held_directory = held_path if os.name == "nt" else _object_directory(held_path)
    real_require = object_module._require_exact_generation
    swapped = False

    def swap_after_final(anchor, name, expected, data, label, **kwargs):
        nonlocal swapped
        if label == "final" and not swapped:
            swap_path.rename(held_path)
            directory.mkdir(parents=True)
            swapped = True
        return real_require(anchor, name, expected, data, label, **kwargs)

    monkeypatch.setattr(object_module, "_require_exact_generation", swap_after_final)

    if os.name == "nt":
        # The held DELETE-capable anchor fences this attempted leaf replacement
        # before it can create a second namespace.  POSIX exercises the later
        # recovery path below, where a moved ancestor remains reachable by fd.
        with pytest.raises(OSError):
            write_object(control_root, "task", TASK_ID, 1, {"value": "anchored"})
        assert not swapped
        assert not held_path.exists()
        assert not list(directory.glob("00000001-*.json"))
        return

    with pytest.raises(ConflictError, match="directory identity changed"):
        write_object(control_root, "task", TASK_ID, 1, {"value": "anchored"})

    assert swapped
    assert not list(directory.glob("00000001-*.json"))
    assert not list(held_directory.glob("00000001-*.json"))
    assert len(list(held_directory.glob(".*.publication-claim"))) == 1


def test_object_publication_rejects_replaced_temporary_without_publishing_foreign_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import research_system.store.objects as object_module

    expected = {"value": "expected"}
    foreign = canonical_bytes({"value": "foreign"})
    directory = _object_directory(tmp_path)

    def replace_temporary(temporary_name: str) -> None:
        temporary = directory / temporary_name
        temporary.unlink()
        temporary.write_bytes(foreign)

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", replace_temporary)

    with pytest.raises(ConflictError, match="temporary.*generation changed"):
        write_object(tmp_path, "task", TASK_ID, 1, expected)

    assert not list(directory.glob("00000001-*.json"))
    assert not list(directory.glob(".*.publication-claim"))
    temporary = list(directory.glob(".*.tmp"))
    assert len(temporary) == 1
    assert temporary[0].read_bytes() == foreign


def test_object_publication_preserves_substituted_final_generation(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.objects as object_module

    expected = {"value": "expected"}
    foreign = canonical_bytes({"value": "foreign"})
    target = _object_target(tmp_path, expected)
    real_link = os.link
    replaced = False

    def link_then_replace(source, destination, *args, **kwargs):
        nonlocal replaced
        result = real_link(source, destination, *args, **kwargs)
        if Path(destination).name == target.name and not replaced:
            replaced = True
            target.unlink()
            target.write_bytes(foreign)
        return result

    monkeypatch.setattr(object_module.os, "link", link_then_replace)

    with pytest.raises(ConflictError, match="final.*changed|object revision already exists"):
        write_object(tmp_path, "task", TASK_ID, 1, expected)

    directory = _object_directory(tmp_path)
    assert target.read_bytes() == foreign
    assert not list(directory.glob(".*.tmp"))
    claim = directory / ".00000001.publication-claim"
    assert claim.read_bytes() == canonical_bytes(expected)


def test_object_publication_preserves_substituted_claim_without_publishing_it(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.objects as object_module

    expected = {"value": "expected"}
    foreign = canonical_bytes({"value": "foreign"})
    real_link = os.link
    replaced = False

    def link_then_replace(source, destination, *args, **kwargs):
        nonlocal replaced
        result = real_link(source, destination, *args, **kwargs)
        if Path(destination).name.endswith(".publication-claim") and not replaced:
            replaced = True
            claim = Path(destination)
            claim.unlink()
            claim.write_bytes(foreign)
        return result

    monkeypatch.setattr(object_module.os, "link", link_then_replace)

    with pytest.raises(ConflictError, match="claim.*changed"):
        write_object(tmp_path, "task", TASK_ID, 1, expected)

    directory = _object_directory(tmp_path)
    assert not list(directory.glob("00000001-*.json"))
    claims = list(directory.glob(".*.publication-claim"))
    assert len(claims) == 1
    assert claims[0].read_bytes() == foreign
    assert not list(directory.glob(".*.tmp"))


def test_object_publication_rejects_foreign_claim_collision_without_cleanup(tmp_path: Path) -> None:
    expected = {"value": "expected"}
    foreign = canonical_bytes({"value": "foreign"})
    directory = _object_directory(tmp_path)
    directory.mkdir(parents=True)
    claim = directory / ".00000001.publication-claim"
    claim.write_bytes(foreign)

    with pytest.raises(ConflictError, match="claim.*changed"):
        write_object(tmp_path, "task", TASK_ID, 1, expected)

    assert not list(directory.glob("00000001-*.json"))
    assert claim.read_bytes() == foreign
    assert not list(directory.glob(".*.tmp"))


def test_locked_root_publishes_and_reads_exact_relative_file_bytes(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    payload = b'{"binding":"exact"}\n'

    with _locked_root(control_root) as locked_root:
        assert isinstance(locked_root, LockedRoot)
        locked_root.write_exact_file("runtime/manifests/spec-current-binding.json", payload)
        assert locked_root.read_exact_file("runtime/manifests/spec-current-binding.json") == payload

    assert (control_root / "runtime" / "manifests" / "spec-current-binding.json").read_bytes() == payload


@pytest.mark.parametrize(
    "relative_path",
    (
        "/runtime/manifests/spec-current-binding.json",
        "runtime//manifests/spec-current-binding.json",
        "runtime/../outside.json",
        "runtime\\manifests\\spec-current-binding.json",
        "runtime/manifests/spec\x00-current-binding.json",
    ),
)
def test_locked_root_rejects_noncanonical_relative_paths_before_any_publication(
    tmp_path: Path,
    relative_path: str,
) -> None:
    control_root = tmp_path / "control"

    with _locked_root(control_root) as locked_root:
        with pytest.raises(ConflictError, match="relative file path is invalid"):
            locked_root.write_exact_file(relative_path, b"expected")

    assert not list(control_root.rglob("*.json"))


def test_locked_root_publication_uses_no_follow_hard_links(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    real_link = os.link
    calls: list[bool] = []

    def observe(source, destination, *args, **kwargs):
        calls.append(kwargs.get("follow_symlinks", True))
        return real_link(source, destination, *args, **kwargs)

    with _locked_root(control_root) as locked_root:
        monkeypatch.setattr(lock_module.os, "link", observe)
        locked_root.write_exact_file("runtime/manifests/spec-current-binding.json", b"expected")

    assert calls and calls == [False, False]


def test_locked_root_rejects_reparse_escape_and_preserves_foreign_directory(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    foreign_root = tmp_path / "foreign"
    foreign_root.mkdir()
    runtime = control_root / "runtime"
    runtime.mkdir(parents=True)
    try:
        (runtime / "manifests").symlink_to(foreign_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory reparse creation unavailable: {exc}")

    with _locked_root(control_root) as locked_root:
        with pytest.raises(ConflictError, match="physical member directory|reparse"):
            locked_root.write_exact_file("runtime/manifests/spec-current-binding.json", b"expected")

    assert list(foreign_root.iterdir()) == []


def test_object_publication_rejects_redirected_namespace_without_writing_outside(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    foreign_root = tmp_path / "foreign"
    foreign_root.mkdir()
    objects = control_root / "objects"
    objects.mkdir(parents=True)
    try:
        (objects / "task").symlink_to(foreign_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory reparse creation unavailable: {exc}")

    with pytest.raises(ConflictError, match="physical member directory|reparse"):
        write_object(control_root, "task", TASK_ID, 1, {"value": "expected"})

    assert list(foreign_root.iterdir()) == []


def test_object_publication_rejects_existing_reparse_final_without_following_it(tmp_path: Path) -> None:
    expected = {"value": "expected"}
    target = _object_target(tmp_path, expected)
    target.parent.mkdir(parents=True)
    foreign = tmp_path / "foreign.json"
    foreign.write_bytes(canonical_bytes({"value": "foreign"}))
    try:
        target.symlink_to(foreign)
    except OSError as exc:
        pytest.skip(f"file reparse creation unavailable: {exc}")

    with pytest.raises(ConflictError, match="object revision already exists"):
        write_object(tmp_path, "task", TASK_ID, 1, expected)

    assert foreign.read_bytes() == canonical_bytes({"value": "foreign"})


def test_locked_root_preserves_foreign_final_collision(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    target = control_root / "runtime" / "manifests" / "spec-current-binding.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"foreign")

    with _locked_root(control_root) as locked_root:
        with pytest.raises(ConflictError, match="already binds different bytes"):
            locked_root.write_exact_file("runtime/manifests/spec-current-binding.json", b"expected")

    assert target.read_bytes() == b"foreign"


def test_locked_root_compare_and_swap_requires_exact_predecessor(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"old")
        locked_root.replace_exact_file(relative_path, b"old", b"new")
        assert locked_root.read_exact_file(relative_path) == b"new"
        with pytest.raises(ConflictError, match="expected bytes differ"):
            locked_root.replace_exact_file(relative_path, b"old", b"later")


def test_locked_root_removal_requires_the_exact_generation(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"expected")
        with pytest.raises(ConflictError, match="expected bytes differ"):
            locked_root.remove_exact_file(relative_path, b"foreign")
        assert locked_root.read_exact_file(relative_path) == b"expected"
        locked_root.remove_exact_file(relative_path, b"expected")
        with pytest.raises(ConflictError, match="cannot be read"):
            locked_root.read_exact_file(relative_path)


def test_locked_root_removal_preserves_a_substituted_final_and_cleans_its_claim(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"
    target = control_root / relative_path.replace("/", os.sep)
    real_link = os.link
    replaced = False

    def link_then_replace(source, destination, *args, **kwargs):
        nonlocal replaced
        result = real_link(source, destination, *args, **kwargs)
        if Path(destination).suffix == ".remove" and not replaced:
            replaced = True
            target.unlink()
            target.write_bytes(b"foreign")
        return result

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"expected")
        monkeypatch.setattr(lock_module.os, "link", link_then_replace)
        with pytest.raises(ConflictError, match="changed before claim source removal"):
            locked_root.remove_exact_file(relative_path, b"expected")

    assert target.read_bytes() == b"foreign"
    assert not list(target.parent.glob(f".{target.name}.*.remove"))


def test_locked_root_compare_and_swap_preserves_substituted_final(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"
    target = control_root / relative_path.replace("/", os.sep)
    real_link = os.link
    replaced = False

    def link_then_replace(source, destination, *args, **kwargs):
        nonlocal replaced
        result = real_link(source, destination, *args, **kwargs)
        if Path(destination).name == target.name and not replaced:
            replaced = True
            target.unlink()
            target.write_bytes(b"foreign")
        return result

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"old")
        monkeypatch.setattr(lock_module.os, "link", link_then_replace)
        with pytest.raises(ConflictError, match="publication did not remain exact|changed"):
            locked_root.replace_exact_file(relative_path, b"old", b"new")

    assert target.read_bytes() == b"foreign"
    predecessor_claim = target.with_name(f".{target.name}.replacement-predecessor-claim")
    assert predecessor_claim.read_bytes() == b"old"
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))
    assert not target.with_name(f".{target.name}.replacement-publication-claim").exists()


def test_locked_root_replacement_finishes_committed_recovery_after_predecessor_cleanup_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: a committed final is retried by draining its exact predecessor claim."""

    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"
    target = control_root / relative_path.replace("/", os.sep)
    predecessor_claim = target.with_name(f".{target.name}.replacement-predecessor-claim")
    real_unlink = lock_module._DirectoryAnchor._unlink_claimed_generation
    failed = False

    def fail_once_for_predecessor(anchor, claim, *args, **kwargs):
        nonlocal failed
        if claim == predecessor_claim.name and not failed:
            failed = True
            raise OSError("injected predecessor cleanup failure")
        return real_unlink(anchor, claim, *args, **kwargs)

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"old")
        monkeypatch.setattr(lock_module._DirectoryAnchor, "_unlink_claimed_generation", fail_once_for_predecessor)
        with pytest.raises(ConflictError, match="cannot be replaced"):
            locked_root.replace_exact_file(relative_path, b"old", b"new")

        assert failed
        assert locked_root.read_exact_file(relative_path) == b"new"
        assert predecessor_claim.read_bytes() == b"old"
        locked_root.replace_exact_file(relative_path, b"old", b"new")
        assert locked_root.read_exact_file(relative_path) == b"new"

    assert not predecessor_claim.exists()
    assert not target.with_name(f".{target.name}.replacement-publication-claim").exists()


@pytest.mark.parametrize("same_bytes", [False, True], ids=["different-bytes", "same-bytes-new-inode"])
def test_writer_lock_release_preserves_a_generation_substituted_after_ownership_check(
    tmp_path: Path,
    monkeypatch,
    same_bytes: bool,
) -> None:
    """remediation-red: A's release cannot vacate B or admit C after an ABA substitution."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "owner"})
    writer.__enter__()
    foreign = writer._data if same_bytes else WriterLock(path, {"writer_id": "foreign"})._data
    substituted = False
    contender_blocked = False

    def replace_after_check(candidate: Path) -> None:
        nonlocal substituted, contender_blocked
        if candidate == path and not substituted:
            substituted = True
            candidate.unlink()
            candidate.write_bytes(foreign)
            with pytest.raises(WriterLockContentionError, match="writer lock exists"):
                WriterLock(path, {"writer_id": "contender"}).__enter__()
            contender_blocked = True

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", replace_after_check, raising=False)

    with pytest.raises(ConflictError, match="writer lock.*changed|writer lock.*ownership"):
        writer.__exit__(None, None, None)

    assert substituted
    assert contender_blocked
    _assert_generation_preserved_after_posix_quarantine(path, foreign)
    with pytest.raises(WriterLockContentionError, match="writer lock exists"):
        WriterLock(path, {"writer_id": "contender"}).__enter__()


@pytest.mark.parametrize("same_bytes", [False, True], ids=["different-bytes", "same-bytes-new-inode"])
def test_stale_reclaim_preserves_a_live_generation_substituted_after_inspection(
    tmp_path: Path,
    monkeypatch,
    same_bytes: bool,
) -> None:
    """remediation-red: reclaiming stale A cannot vacate substituted B or admit C."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    stale = canonical_bytes(
        {"process_id": "919191", "process_instance_id": "dead-process-instance", "writer_id": "stale-a"}
    )
    path.write_bytes(stale)
    monkeypatch.setattr(lock_module, "process_instance_id", lambda _pid: None)
    monkeypatch.setattr(
        lock_module.os,
        "kill",
        lambda _pid, _signal: (_ for _ in ()).throw(ProcessLookupError()),
    )
    state, observed, _ = lock_module.inspect_lock(path)
    assert state == "stale"
    assert observed is not None

    live_identity = {
        "process_id": str(os.getpid()),
        "process_instance_id": "test-live-process-instance",
        "writer_id": "live-b",
    }
    contender_identity = {
        "process_id": str(os.getpid()),
        "process_instance_id": "test-contender-process-instance",
        "writer_id": "contender-c",
    }
    live = stale if same_bytes else WriterLock(path, live_identity)._data
    substituted = False
    contender_blocked = False

    def replace_before_delete(candidate: Path) -> None:
        nonlocal substituted, contender_blocked
        if candidate == path and not substituted:
            substituted = True
            candidate.unlink()
            candidate.write_bytes(live)
            with pytest.raises(WriterLockContentionError, match="writer lock exists"):
                WriterLock(path, contender_identity).__enter__()
            contender_blocked = True

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", replace_before_delete)

    assert not lock_module.remove_stale_lock(path, observed)
    assert substituted
    assert contender_blocked
    assert path.read_bytes() == live
    with pytest.raises(WriterLockContentionError, match="writer lock exists"):
        WriterLock(path, contender_identity).__enter__()


def test_writer_lock_release_rejects_an_in_place_byte_mutation_after_ownership_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A matching inode is insufficient when its immutable bytes were altered."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "owner"})
    writer.__enter__()
    foreign = b'{"writer_id":"mutated"}'
    mutated = False

    def mutate_after_check(candidate: Path) -> None:
        nonlocal mutated
        if candidate == path and not mutated:
            mutated = True
            candidate.write_bytes(foreign)

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", mutate_after_check, raising=False)

    with pytest.raises(ConflictError, match="writer lock.*bytes changed|writer lock.*quarantined"):
        writer.__exit__(None, None, None)

    assert mutated
    _assert_generation_preserved_after_posix_quarantine(path, foreign)


def test_locked_root_source_deletion_preserves_a_generation_substituted_after_claim_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: a no-replace claim does not authorize path-based deletion."""

    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"
    target = control_root / relative_path.replace("/", os.sep)
    foreign = b"foreign"
    substituted = False

    def replace_after_check(candidate: Path) -> None:
        nonlocal substituted
        if candidate.name == target.name and not substituted:
            substituted = True
            candidate.unlink()
            candidate.write_bytes(foreign)

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"expected")
        monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", replace_after_check, raising=False)
        with pytest.raises(ConflictError, match="changed|exact generation"):
            locked_root.remove_exact_file(relative_path, b"expected")

    assert substituted
    _assert_generation_preserved_after_posix_quarantine(target, foreign)
    assert not list(target.parent.glob(f".{target.name}.*.remove"))


def test_locked_root_claim_cleanup_preserves_a_claim_substituted_after_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: final publication survives a substituted claim-cleanup name."""

    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"
    target = control_root / relative_path.replace("/", os.sep)
    claim = target.with_name(f".{target.name}.publication-claim")
    foreign = b"foreign-claim"
    substituted = False

    def replace_after_check(candidate: Path) -> None:
        nonlocal substituted
        if candidate.name == claim.name and not substituted:
            substituted = True
            candidate.unlink()
            candidate.write_bytes(foreign)

    with _locked_root(control_root) as locked_root:
        monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", replace_after_check, raising=False)
        with pytest.raises(ConflictError, match="claim.*changed|generation changed"):
            locked_root.write_exact_file(relative_path, b"expected")

    assert substituted
    assert target.read_bytes() == b"expected"
    _assert_generation_preserved_after_posix_quarantine(claim, foreign)
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_object_rollback_preserves_a_generation_substituted_after_ownership_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: object rollback cannot delete a post-proof foreign revision."""

    import research_system.store.lock as lock_module

    store = ObjectStore(tmp_path)
    value = {"value": "expected"}
    path = store.write("task", TASK_ID, 1, value)
    foreign = canonical_bytes({"value": "foreign"})
    substituted = False

    def replace_after_check(candidate: Path) -> None:
        nonlocal substituted
        if candidate.name == path.name and not substituted:
            substituted = True
            candidate.unlink()
            candidate.write_bytes(foreign)

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", replace_after_check, raising=False)

    with pytest.raises(IntegrityError, match="changed object revision"):
        store.rollback_new_revision("task", TASK_ID, 1, value, existed_before=False)

    assert substituted
    _assert_generation_preserved_after_posix_quarantine(path, foreign)
    assert not list(path.parent.glob(".*.tmp"))
    assert not list(path.parent.glob(".*.cleanup-anchor"))


def test_object_temporary_cleanup_treats_a_concurrent_absence_as_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: missing_ok cleanup is not converted to a false conflict."""

    import research_system.store.lock as lock_module

    removed = False

    def remove_after_check(candidate: Path) -> None:
        nonlocal removed
        if candidate.name.endswith(".tmp") and not removed:
            removed = True
            candidate.unlink()

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", remove_after_check, raising=False)

    target = write_object(tmp_path, "task", TASK_ID, 1, {"value": "expected"})

    assert removed
    assert target.read_bytes() == canonical_bytes({"value": "expected"})
    assert not list(target.parent.glob(".*.tmp"))
    assert not list(target.parent.glob(".*.publication-claim"))


def test_object_temporary_cleanup_allows_an_absence_before_its_generation_recheck(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: ``missing_ok`` reaches the first generation check too."""

    import research_system.store.objects as object_module

    real_remove = object_module._remove_owned_generation
    removed = False

    def remove_then_observe_absence(anchor, name, expected, data, label, guard, *, missing_ok=False, **kwargs):
        nonlocal removed
        if label == "temporary" and not removed:
            anchor.remove_exact_generation(name, expected, data, guard=guard)
            removed = True
        return real_remove(
            anchor,
            name,
            expected,
            data,
            label,
            guard,
            missing_ok=missing_ok,
            **kwargs,
        )

    monkeypatch.setattr(object_module, "_remove_owned_generation", remove_then_observe_absence)

    target = write_object(tmp_path, "task", TASK_ID, 1, {"value": "expected"})

    assert removed
    assert target.read_bytes() == canonical_bytes({"value": "expected"})
    assert not list(target.parent.glob(".*.tmp"))
    assert not list(target.parent.glob(".*.publication-claim"))


def test_locked_root_rejects_a_real_reparse_substituted_after_claim_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: a source turned into a reparse point remains untouched."""

    import research_system.store.lock as lock_module

    control_root = tmp_path / "control"
    relative_path = "runtime/manifests/spec-current-binding.json"
    target = control_root / relative_path.replace("/", os.sep)
    foreign = tmp_path / "foreign.json"
    foreign.write_bytes(b"foreign")
    substituted = False

    def replace_with_reparse_after_check(candidate: Path) -> None:
        nonlocal substituted
        if candidate.name == target.name and not substituted:
            substituted = True
            candidate.unlink()
            try:
                candidate.symlink_to(foreign)
            except OSError as exc:
                pytest.skip(f"file reparse creation unavailable: {exc}")

    with _locked_root(control_root) as locked_root:
        locked_root.write_exact_file(relative_path, b"expected")
        monkeypatch.setattr(
            lock_module,
            "_before_exact_generation_unlink",
            replace_with_reparse_after_check,
            raising=False,
        )
        with pytest.raises(ConflictError, match="physical regular file|generation changed"):
            locked_root.remove_exact_file(relative_path, b"expected")

    assert substituted
    assert foreign.read_bytes() == b"foreign"
    if os.name == "nt":
        assert target.is_symlink()
        assert not list(target.parent.glob(f".{target.name}.*.remove"))
    else:
        quarantines = list(target.parent.glob(f".{target.name}.*.exact-delete-quarantine"))
        assert not target.exists()
        assert len(quarantines) == 1
        assert (quarantines[0] / target.name).is_symlink()
        assert stat.S_IMODE(quarantines[0].lstat().st_mode) == 0o700
