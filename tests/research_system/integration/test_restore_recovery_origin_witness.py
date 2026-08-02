from __future__ import annotations

import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from research_system.authority import authority_bootstrap_sha256, initialize_authority_control_store
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.operations.backups import RestorePreflightResult, seal_restore_preflight_result
from research_system.store.identity import (
    canonical_restore_binding_output,
    load_store_manifest,
    load_store_origin_witness,
    rebind_restored_store,
    restore_binding_transaction_path,
)
from tests.research_system.factories import PROJECT_ID, REPO_ROOT, authority_bootstrap


ACTOR_ID = "act_01978abc-1002-7000-8000-000000001002"
AUTHORITY_GRANT_ID = "agr_01978abc-1001-7000-8000-000000001001"


def _restored_fixture(tmp_path: Path):
    code_root = tmp_path / "repo"
    schema_root = code_root / ".research-system" / "schemas"
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas", schema_root)
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    origin_root = tmp_path / "origin-authority"
    origin_root.mkdir()
    bootstrap = authority_bootstrap()
    initialized = initialize_authority_control_store(
        [code_root],
        source_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=schema_root,
        origin_authority_root=origin_root,
    )
    shutil.copytree(source_root, target_root)
    witness = load_store_origin_witness(
        initialized.witness_path,
        expected_sha256=initialized.witness.raw_sha256,
    )
    snapshot = {"snapshot_id": "snp_01978abc-1005-7000-8000-000000001005"}
    output = canonical_restore_binding_output(
        target_root,
        PROJECT_ID,
        str(initialized),
        [code_root],
        schema_root,
    )
    manifest_bytes = (target_root / "manifests" / "store-identity.json").read_bytes()
    preflight = seal_restore_preflight_result(
        RestorePreflightResult(
            status="verified",
            failed_predicates=(),
            receipt_hash="a" * 64,
            ledger_hash="b" * 64,
            snapshot_hash="c" * 64,
            target_endpoint_ownership_hash="d" * 64,
            artefact_manifest_hash="e" * 64,
            availability_observations_hash="f" * 64,
            registry_hash="0" * 64,
            target_root=str(target_root.resolve()),
            project_id=PROJECT_ID,
            store_identity=str(initialized),
            tail_position=0,
            tail_hash="0" * 64,
            snapshot_id=snapshot["snapshot_id"],
            actor_id=ACTOR_ID,
            authority_grant_id=AUTHORITY_GRANT_ID,
            result_hash="",
            source_root=str(source_root.resolve()),
            code_roots=[str(code_root.resolve())],
            schema_root=str(schema_root.resolve()),
            source_snapshot_hash=sha256_hex(canonical_bytes(snapshot)),
            target_manifest_bytes_sha256=sha256_hex(manifest_bytes),
            expected_output_sha256=sha256_hex(output),
            origin_witness_path=str(initialized.witness_path.resolve()),
            origin_witness_sha256=witness.raw_sha256,
            origin_initial_control_root=witness.initial_control_root,
            origin_initial_physical_root_identity=dict(witness.initial_physical_root_identity),
        )
    )
    rebound = rebind_restored_store(
        target_root,
        source_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=str(initialized),
        expected_code_roots=[code_root],
        expected_schema_root=schema_root,
        expected_restore_receipt_hash=preflight.receipt_hash,
        actor_id=ACTOR_ID,
        authority_grant_id=AUTHORITY_GRANT_ID,
        source_snapshot=snapshot,
        expected_source_snapshot_hash=preflight.source_snapshot_hash,
        expected_target_manifest_bytes_sha256=preflight.target_manifest_bytes_sha256,
        expected_output=output,
        expected_restore_preflight=asdict(preflight),
        approved_witness=witness,
        approved_witness_path=initialized.witness_path,
        origin_witness_path=str(initialized.witness_path.resolve()),
    )
    return initialized, witness, target_root, rebound


def test_cleared_restore_requires_witness_join_and_transaction_presence(tmp_path: Path):
    initialized, witness, target_root, rebound = _restored_fixture(tmp_path)

    assert rebound["origin_witness_sha256"] == witness.raw_sha256
    assert load_store_manifest(target_root, approved_witness=witness)["control_root"] == str(target_root.resolve())

    restore_binding_transaction_path(target_root).unlink()
    with pytest.raises(IntegrityError):
        load_store_manifest(target_root, approved_witness=witness)
    assert initialized.witness_path.is_file()


def test_third_root_copy_and_changed_external_witness_fail_closed(tmp_path: Path):
    initialized, witness, target_root, _ = _restored_fixture(tmp_path)
    third_root = tmp_path / "third-root"
    shutil.copytree(target_root, third_root)
    with pytest.raises(IntegrityError):
        load_store_manifest(third_root, approved_witness=witness)

    initialized.witness_path.write_bytes(b"changed witness")
    with pytest.raises(IntegrityError):
        load_store_origin_witness(
            initialized.witness_path,
            expected_sha256=witness.raw_sha256,
        )
