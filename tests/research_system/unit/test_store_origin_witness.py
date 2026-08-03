from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from research_system.errors import ArsError, ConflictError, IntegrityError
import research_system.store.identity as identity_module
from research_system.store.identity import (
    initialize_control_store,
    load_store_manifest,
    load_store_origin_witness,
    persist_store_origin_witness,
)


PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"


def _simulate_posix_cleanup(monkeypatch):
    monkeypatch.setattr(identity_module.os, "name", "posix")
    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: True)


def _initialized(tmp_path: Path):
    code_root = tmp_path / "code"
    control_root = tmp_path / "control"
    origin_root = tmp_path / "origin-authority"
    code_root.mkdir()
    origin_root.mkdir()
    result = initialize_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        origin_authority_root=origin_root,
    )
    witness = load_store_origin_witness(result.witness_path, expected_sha256=result.witness.raw_sha256)
    return code_root, control_root, origin_root, result, witness


def test_initialization_persists_external_witness_and_ignores_local_mirror(tmp_path: Path):
    _, control_root, _, result, witness = _initialized(tmp_path)

    assert result.witness_path.name == f"sha256-{witness.slot}.json"
    assert result.witness_path.parent.name == "store-origins"
    assert load_store_manifest(
        control_root,
        approved_witness=witness,
        approved_witness_path=result.witness_path,
    )["store_identity"] == str(result)

    (control_root / "manifests" / "store-origin.json").write_bytes(b"{}")
    assert load_store_manifest(
        control_root,
        approved_witness=witness,
        approved_witness_path=result.witness_path,
    )["store_identity"] == str(result)


def test_normal_loader_requires_explicit_witness_and_rejects_a_copied_store(tmp_path: Path):
    _, control_root, _, result, witness = _initialized(tmp_path)
    copied_root = tmp_path / "copied"
    shutil.copytree(control_root, copied_root)

    with pytest.raises(IntegrityError, match="approved origin witness"):
        load_store_manifest(control_root)
    with pytest.raises(IntegrityError, match="control-root binding|origin witness"):
        load_store_manifest(copied_root, approved_witness=witness, approved_witness_path=result.witness_path)

    with pytest.raises(IntegrityError):
        load_store_origin_witness(result.witness_path, expected_sha256="0" * 64)


def test_existing_store_without_external_witness_is_not_backfilled(tmp_path: Path):
    code_root, control_root, origin_root, result, _ = _initialized(tmp_path)
    result.witness_path.unlink()

    with pytest.raises(ConflictError, match="independent origin witness"):
        initialize_control_store(
            [code_root],
            control_root,
            PROJECT_ID,
            origin_authority_root=origin_root,
        )
    assert not result.witness_path.exists()


def test_origin_authority_root_must_preexist_and_be_disjoint(tmp_path: Path):
    code_root = tmp_path / "code"
    code_root.mkdir()
    control_root = tmp_path / "control"

    with pytest.raises(ArsError, match="existing directory"):
        initialize_control_store(
            [code_root],
            control_root,
            PROJECT_ID,
            origin_authority_root=tmp_path / "missing-origin",
        )
    overlapping_origin = code_root / "origin"
    overlapping_origin.mkdir()
    with pytest.raises(ArsError, match="physically disjoint"):
        initialize_control_store(
            [code_root],
            control_root,
            PROJECT_ID,
            origin_authority_root=overlapping_origin,
        )
    assert not control_root.exists()


def test_witness_is_write_once_and_exact_retry_is_idempotent(tmp_path: Path):
    _, control_root, origin_root, first, witness = _initialized(tmp_path)
    retry = initialize_control_store(
        [tmp_path / "code"],
        control_root,
        PROJECT_ID,
        origin_authority_root=origin_root,
        approved_origin_witness_sha256=witness.raw_sha256,
    )
    assert retry == first
    assert retry.witness.raw_bytes == first.witness.raw_bytes

    first.witness_path.write_bytes(b"foreign witness")
    with pytest.raises(ConflictError, match="conflicts"):
        persist_store_origin_witness(witness, origin_root)
    assert first.witness_path.read_bytes() == b"foreign witness"


def test_posix_cleanup_preserves_foreign_temporary_inode(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    anchor.write_bytes(expected)
    temporary.write_bytes(b"foreign")
    _simulate_posix_cleanup(monkeypatch)

    with pytest.raises(ConflictError, match="temporary physical identity changed"):
        identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert temporary.read_bytes() == b"foreign"


def test_posix_cleanup_removes_owned_temporary_hardlink(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    anchor.write_bytes(expected)
    os.link(anchor, temporary)
    _simulate_posix_cleanup(monkeypatch)

    identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert not temporary.exists()
    assert anchor.read_bytes() == expected
    quarantine_directories = list(tmp_path.glob(".temporary.restore-cleanup-quarantine-*"))
    assert len(quarantine_directories) == 1
    quarantined = quarantine_directories[0] / temporary.name
    assert quarantined.read_bytes() == expected
    assert os.path.samefile(quarantined, anchor)


def test_posix_cleanup_preserves_replaced_temporary_path(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    anchor.write_bytes(expected)
    os.link(anchor, temporary)
    _simulate_posix_cleanup(monkeypatch)

    def replace_temporary(path: Path):
        path.unlink()
        path.write_bytes(b"foreign replacement")

    monkeypatch.setattr(identity_module, "_after_restore_owned_temporary_compared", replace_temporary)
    with pytest.raises(ConflictError, match="temporary physical identity changed"):
        identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert temporary.read_bytes() == b"foreign replacement"
    assert anchor.read_bytes() == expected


def test_posix_cleanup_preserves_post_final_compare_replacement(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    foreign = b"foreign after final comparison"
    anchor.write_bytes(expected)
    os.link(anchor, temporary)
    _simulate_posix_cleanup(monkeypatch)
    original_compare = identity_module._posix_compare_owned_temporary
    completed_comparisons = []

    def replace_after_second_compare(path: Path, compared_anchor: Path, compared_expected: bytes):
        original_compare(path, compared_anchor, compared_expected)
        completed_comparisons.append(path)
        if len(completed_comparisons) == 2:
            path.unlink()
            path.write_bytes(foreign)

    monkeypatch.setattr(identity_module, "_posix_compare_owned_temporary", replace_after_second_compare)
    with pytest.raises(ConflictError, match="temporary physical identity changed"):
        identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert len(completed_comparisons) == 2
    assert temporary.read_bytes() == foreign
    assert anchor.read_bytes() == expected
    quarantine_directories = list(tmp_path.glob(".temporary.restore-cleanup-quarantine-*"))
    assert len(quarantine_directories) == 1
    quarantined = quarantine_directories[0] / temporary.name
    assert quarantined.read_bytes() == foreign
    assert os.path.samefile(temporary, quarantined)


def test_posix_cleanup_retains_quarantine_if_replaced_after_final_compare(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    foreign = b"foreign after quarantine comparison"
    anchor.write_bytes(expected)
    os.link(anchor, temporary)
    _simulate_posix_cleanup(monkeypatch)
    original_compare = identity_module._posix_compare_owned_temporary
    completed_comparisons = []

    def replace_after_third_compare(path: Path, compared_anchor: Path, compared_expected: bytes):
        original_compare(path, compared_anchor, compared_expected)
        completed_comparisons.append(path)
        if len(completed_comparisons) == 3:
            path.unlink()
            path.write_bytes(foreign)

    monkeypatch.setattr(identity_module, "_posix_compare_owned_temporary", replace_after_third_compare)
    identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert len(completed_comparisons) == 3
    assert not temporary.exists()
    assert anchor.read_bytes() == expected
    quarantine_directories = list(tmp_path.glob(".temporary.restore-cleanup-quarantine-*"))
    assert len(quarantine_directories) == 1
    quarantined = quarantine_directories[0] / temporary.name
    assert quarantined.read_bytes() == foreign


def test_posix_cleanup_preserves_quarantine_without_overwriting_concurrent_path(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    foreign = b"foreign after final comparison"
    concurrent = b"concurrently created path"
    anchor.write_bytes(expected)
    os.link(anchor, temporary)
    _simulate_posix_cleanup(monkeypatch)
    original_compare = identity_module._posix_compare_owned_temporary
    compare_paths = []

    def replace_then_collide(path: Path, compared_anchor: Path, compared_expected: bytes):
        compare_paths.append(path)
        if len(compare_paths) == 3:
            temporary.write_bytes(concurrent)
        original_compare(path, compared_anchor, compared_expected)
        if len(compare_paths) == 2:
            path.unlink()
            path.write_bytes(foreign)

    monkeypatch.setattr(identity_module, "_posix_compare_owned_temporary", replace_then_collide)
    with pytest.raises(ConflictError, match="without overwriting current path"):
        identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert len(compare_paths) == 3
    assert temporary.read_bytes() == concurrent
    assert anchor.read_bytes() == expected
    quarantine_directories = list(tmp_path.glob(".temporary.restore-cleanup-quarantine-*"))
    assert len(quarantine_directories) == 1
    assert (quarantine_directories[0] / temporary.name).read_bytes() == foreign


def test_posix_cleanup_preserves_same_inode_content_mismatch(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    changed = b"changed through the shared inode"
    anchor.write_bytes(expected)
    os.link(anchor, temporary)
    temporary.write_bytes(changed)
    _simulate_posix_cleanup(monkeypatch)

    with pytest.raises(ConflictError, match="temporary ownership changed"):
        identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert os.path.samefile(temporary, anchor)
    assert temporary.read_bytes() == changed
    assert anchor.read_bytes() == changed


def test_posix_cleanup_rejects_temporary_symlink_without_following(tmp_path: Path, monkeypatch):
    anchor = tmp_path / "anchor"
    foreign = tmp_path / "foreign"
    temporary = tmp_path / "temporary"
    expected = b"owned"
    anchor.write_bytes(expected)
    foreign.write_bytes(b"foreign")
    try:
        temporary.symlink_to(foreign)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")
    _simulate_posix_cleanup(monkeypatch)

    with pytest.raises(ConflictError, match="not a regular file"):
        identity_module._cleanup_owned_temporary(temporary, expected, anchor=anchor)

    assert temporary.is_symlink()
    assert foreign.read_bytes() == b"foreign"


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse controls are platform-specific")
def test_origin_store_locator_rejects_directory_reparse_escape(tmp_path: Path):
    code_root = tmp_path / "code"
    code_root.mkdir()
    origin_root = tmp_path / "origin-authority"
    origin_root.mkdir()
    outside = tmp_path / "outside-store-origins"
    outside.mkdir()
    try:
        os.symlink(outside, origin_root / "store-origins", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(IntegrityError, match="reparse|locator"):
        initialize_control_store(
            [code_root],
            tmp_path / "control",
            PROJECT_ID,
            origin_authority_root=origin_root,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse controls are platform-specific")
def test_origin_witness_rejects_file_symlink_escape(tmp_path: Path):
    _, _, _, result, witness = _initialized(tmp_path)
    foreign = tmp_path / "foreign-witness.json"
    foreign.write_bytes(witness.raw_bytes)
    result.witness_path.unlink()
    try:
        os.symlink(foreign, result.witness_path)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    with pytest.raises(IntegrityError, match="reparse|locator"):
        load_store_origin_witness(result.witness_path, expected_sha256=witness.raw_sha256)
