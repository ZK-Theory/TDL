from __future__ import annotations

from contextlib import contextmanager
import inspect
import os
from pathlib import Path
import stat
import threading

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
    """Assert the platform-specific safe outcome of exact-generation refusal."""

    if os.name == "nt":
        assert path.read_bytes() == expected
        return
    quarantines = list(path.parent.glob(f".{path.name}.*.exact-delete-quarantine"))
    assert not path.exists()
    assert len(quarantines) == 1
    assert (quarantines[0] / path.name).read_bytes() == expected
    assert stat.S_IMODE(quarantines[0].lstat().st_mode) == 0o700


def test_writer_lock_reports_only_existing_lock_as_typed_contention(tmp_path: Path) -> None:
    path = tmp_path / "writer.lock"

    with WriterLock(path, {"writer_id": "first"}):
        with pytest.raises(WriterLockContentionError, match="writer lock exists"):
            with WriterLock(path, {"writer_id": "second"}):
                raise AssertionError("second writer entered lock")

    assert issubclass(WriterLockContentionError, ConflictError)


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


def test_writer_lock_uses_no_follow_link_publication_on_windows(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    real_link = os.link
    calls: list[bool] = []

    def observe(source, destination, *, follow_symlinks=True):
        calls.append(follow_symlinks)
        return real_link(source, destination, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(lock_module.os, "link", observe)

    with WriterLock(path, {"writer_id": "no-follow"}):
        assert path.is_file()

    assert calls == [False]


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
    calls: list[bool] = []

    def observe(source, destination, *, follow_symlinks=True):
        calls.append(follow_symlinks)
        return real_link(source, destination, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(object_module.os, "link", observe)

    write_object(tmp_path, "task", TASK_ID, 1, {"value": "no-follow"})

    assert calls == [False, False]


def test_identical_object_writers_share_the_claim_without_cleanup_conflict(tmp_path: Path, monkeypatch) -> None:
    import research_system.store.objects as object_module

    staged = threading.Barrier(3)
    release = threading.Event()
    results: list[Path] = []
    errors: list[BaseException] = []

    def pause_after_stage(_temporary: Path) -> None:
        staged.wait(timeout=2)
        assert release.wait(2)

    def publish() -> None:
        try:
            results.append(write_object(tmp_path, "task", TASK_ID, 1, {"value": "same"}))
        except BaseException as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", pause_after_stage)
    writers = [threading.Thread(target=publish), threading.Thread(target=publish)]
    for writer in writers:
        writer.start()
    staged.wait(timeout=2)
    release.set()
    for writer in writers:
        writer.join(timeout=2)
        assert not writer.is_alive()

    directory = _object_directory(tmp_path)
    assert errors == []
    assert len(set(results)) == 1
    assert ObjectStore(tmp_path).read("task", TASK_ID, 1) == {"value": "same"}
    assert len(list(directory.glob("00000001-*.json"))) == 1
    assert not list(directory.glob(".*.tmp"))
    assert not list(directory.glob(".*.publication-claim"))
    assert not list(directory.glob(".*.cleanup-anchor"))


def test_object_publication_rejects_replaced_temporary_without_publishing_foreign_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import research_system.store.objects as object_module

    expected = {"value": "expected"}
    foreign = canonical_bytes({"value": "foreign"})

    def replace_temporary(temporary: Path) -> None:
        temporary.unlink()
        temporary.write_bytes(foreign)

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", replace_temporary)

    with pytest.raises(ConflictError, match="temporary.*generation changed"):
        write_object(tmp_path, "task", TASK_ID, 1, expected)

    directory = _object_directory(tmp_path)
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


def test_object_rollback_preserves_replaced_final_generation(tmp_path: Path, monkeypatch) -> None:
    store = ObjectStore(tmp_path)
    value = {"value": "expected"}
    path = store.write("task", TASK_ID, 1, value)
    foreign = canonical_bytes({"value": "foreign"})
    import research_system.store.objects as object_module

    real_read_generation = object_module._read_physical_generation
    replaced = False

    def read_then_replace(candidate: Path, expected_generation, label: str) -> bytes:
        nonlocal replaced
        data = real_read_generation(candidate, expected_generation, label)
        if label == "rollback final" and not replaced:
            replaced = True
            candidate.unlink()
            candidate.write_bytes(foreign)
        return data

    monkeypatch.setattr(object_module, "_read_physical_generation", read_then_replace)

    with pytest.raises(IntegrityError, match="changed object revision"):
        store.rollback_new_revision("task", TASK_ID, 1, value, existed_before=False)

    assert path.read_bytes() == foreign


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


def test_writer_lock_release_preserves_a_generation_substituted_after_ownership_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """remediation-red: lock release must not unlink a replacement after verifying its owner."""

    import research_system.store.lock as lock_module

    path = tmp_path / "writer.lock"
    writer = WriterLock(path, {"writer_id": "owner"})
    writer.__enter__()
    foreign = b'{"writer_id":"foreign"}'
    substituted = False

    def replace_after_check(candidate: Path) -> None:
        nonlocal substituted
        if candidate == path and not substituted:
            substituted = True
            candidate.unlink()
            candidate.write_bytes(foreign)

    monkeypatch.setattr(lock_module, "_before_exact_generation_unlink", replace_after_check, raising=False)

    with pytest.raises(ConflictError, match="writer lock.*changed|writer lock.*ownership"):
        writer.__exit__(None, None, None)

    assert substituted
    _assert_generation_preserved_after_posix_quarantine(path, foreign)


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

    real_existing = object_module._existing_revision
    removed = False

    def existing_then_remove_temporary(directory, *args, **kwargs):
        nonlocal removed
        result = real_existing(directory, *args, **kwargs)
        if result is not None and not removed:
            temporary = next(directory.glob(".*.tmp"))
            temporary.unlink()
            removed = True
        return result

    monkeypatch.setattr(object_module, "_existing_revision", existing_then_remove_temporary)

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


def test_posix_exact_generation_deletion_has_a_private_dirfd_quarantine_contract() -> None:
    """The POSIX path must move a name before unlinking it, never stat/unlink it."""

    import research_system.store.lock as lock_module

    source = inspect.getsource(lock_module._posix_delete_exact_regular_file) + inspect.getsource(
        lock_module._posix_private_quarantine
    )

    assert "os.rename(" in source
    assert "src_dir_fd=" in source
    assert "dst_dir_fd=" in source
    assert "os.unlink(" in source
    assert "dir_fd=" in source
    assert "0o700" in source


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory-fd quarantine contract")
def test_posix_object_publication_releases_its_claim_without_quarantine_residue(tmp_path: Path) -> None:
    """Normal immutable publication remains usable on the Ubuntu CI platform."""

    target = write_object(tmp_path, "task", TASK_ID, 1, {"value": "posix"})

    assert target.read_bytes() == canonical_bytes({"value": "posix"})
    assert not list(target.parent.glob(".*.publication-claim"))
    assert not list(target.parent.glob(".*.exact-delete-quarantine"))
    assert not list(target.parent.glob(".*.tmp"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory-fd quarantine contract")
def test_posix_exact_generation_deletion_retains_a_postcheck_foreign_source_in_private_quarantine(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A post-proof foreign source is moved aside, never unlinked or overwritten."""

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
        with pytest.raises(ConflictError, match="quarantined|generation changed|exact generation"):
            locked_root.remove_exact_file(relative_path, b"expected")

    assert substituted
    assert not target.exists()
    quarantines = list(target.parent.glob(f".{target.name}.*.exact-delete-quarantine"))
    assert len(quarantines) == 1
    quarantined = quarantines[0] / target.name
    assert quarantined.read_bytes() == foreign
    assert stat.S_IMODE(quarantines[0].lstat().st_mode) == 0o700
