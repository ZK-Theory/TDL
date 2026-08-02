from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.store.identity import (
    initialize_control_store,
    load_store_manifest,
    load_store_origin_witness,
    persist_store_origin_witness,
)


PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"


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
