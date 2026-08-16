from __future__ import annotations

from pathlib import Path

import pytest

import research_system.discovery.path_safety as path_safety
from research_system.discovery.path_safety import contained_regular_file, read_contained_regular_file
from research_system.errors import ConfigurationError, IntegrityError
from research_system.methods.registration import CandidateDocumentStore


def test_contained_regular_file_rejects_traversal_absolute_and_redirected_paths(tmp_path: Path) -> None:
    root = tmp_path / "control"
    root.mkdir()
    accepted = root / "methods" / "documents" / "result.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("{}", encoding="utf-8")
    assert contained_regular_file(root, "methods/documents/result.json", label="registered result") == accepted
    assert read_contained_regular_file(root, "methods/documents/result.json", label="registered result") == b"{}"

    for invalid in (None, ""):
        with pytest.raises(IntegrityError, match="path is invalid"):
            contained_regular_file(root, invalid, label="registered result")

    with pytest.raises(IntegrityError, match="is not a regular file"):
        contained_regular_file(root, "methods/documents", label="registered result")

    for relative in ("../outside.json", str((tmp_path / "outside.json").resolve())):
        with pytest.raises(IntegrityError, match="canonical and relative"):
            contained_regular_file(root, relative, label="registered result")

    external = tmp_path / "external.json"
    external.write_text("{}", encoding="utf-8")
    redirected = root / "methods" / "documents" / "redirected.json"
    try:
        redirected.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(IntegrityError, match="reparse component"):
        contained_regular_file(root, "methods/documents/redirected.json", label="registered result")
    assert external.read_text(encoding="utf-8") == "{}"


@pytest.mark.skipif(path_safety.os.name != "nt", reason="Windows final-handle containment fallback")
def test_read_rejects_parent_redirect_restored_after_the_leaf_is_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "control"
    parent = root / "methods" / "documents"
    parent.mkdir(parents=True)
    (parent / "result.json").write_bytes(b"inside")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.json").write_bytes(b"outside")
    probe = tmp_path / "symlink-probe"
    try:
        probe.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("symlink creation is not permitted on this Windows runner")
        raise
    probe.unlink()
    held_parent = root / "methods" / "documents-held"
    original_contained = path_safety.contained_regular_file
    original_final_path = path_safety._descriptor_final_path

    def redirect_after_validation(*args, **kwargs):
        result = original_contained(*args, **kwargs)
        parent.rename(held_parent)
        parent.symlink_to(outside, target_is_directory=True)
        return result

    def restore_before_final_path_check(descriptor: int):
        parent.unlink()
        held_parent.rename(parent)
        return original_final_path(descriptor)

    monkeypatch.setattr(path_safety, "contained_regular_file", redirect_after_validation)
    monkeypatch.setattr(path_safety, "_descriptor_final_path", restore_before_final_path_check)

    with pytest.raises(IntegrityError, match="escapes its configured root"):
        path_safety.read_contained_regular_file(root, "methods/documents/result.json", label="registered result")

    assert (parent / "result.json").read_bytes() == b"inside"


@pytest.mark.skipif(path_safety.os.name == "nt", reason="POSIX parent-descriptor containment")
def test_read_retains_open_parent_when_its_name_is_redirected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "control"
    parent = root / "methods" / "documents"
    parent.mkdir(parents=True)
    (parent / "result.json").write_bytes(b"inside")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.json").write_bytes(b"outside")
    held_parent = root / "methods" / "documents-held"
    original_open = path_safety.os.open
    redirected = False

    def redirect_open(path, flags, *args, **kwargs):
        nonlocal redirected
        descriptor = original_open(path, flags, *args, **kwargs)
        if path == "documents" and kwargs.get("dir_fd") is not None and not redirected:
            redirected = True
            parent.rename(held_parent)
            parent.symlink_to(outside, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(path_safety.os, "open", redirect_open)
    try:
        with pytest.raises(IntegrityError, match="changed during read"):
            path_safety.read_contained_regular_file(
                root,
                "methods/documents/result.json",
                label="registered result",
            )
    finally:
        if parent.is_symlink():
            parent.unlink()
        if held_parent.exists():
            held_parent.rename(parent)

    assert redirected is True


def test_candidate_document_store_rejects_redirected_parent_before_write(tmp_path: Path) -> None:
    root = tmp_path / "control"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    methods = root / "methods"
    methods.mkdir()
    try:
        (methods / "documents").symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(ConfigurationError, match="physical directory"):
        CandidateDocumentStore(root).write("art_example", b"{}")
    assert not list(external.iterdir())
