"""Mechanics-only synthetic tests for the later WP6.4 real-A8 proof.

These tests never materialize or accept owner foundation values and never claim
that a real A8 operation occurred.  Temporary values are fixtures for harness
mechanics only; the repository foundation remains null and owner-blocked.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

import research_system.config as config_module
import research_system.evidence.wp64_real_a8 as harness_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evidence import (
    A8ProofRequest,
    ContentAddressedEvidenceStore,
    EvidenceConflictError,
    EvidenceHarnessError,
    capture_real_a8_candidate,
    validate_real_a8_candidate,
)
from research_system.store.identity import load_restore_binding_transaction
from tests.research_system.factories import PROJECT_ID, REPO_ROOT
from tests.research_system.integration.test_restore_recovery_origin_witness import _restored_fixture


def test_public_harness_capture_surface_exists() -> None:
    assert callable(capture_real_a8_candidate)


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _snapshot(path: Path) -> dict[str, str]:
    digest = _file_sha256(path)
    return {"path": str(path.resolve()), "before_raw_sha256": digest, "after_raw_sha256": digest}


def _synthetic_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, remove_source: bool = True):
    initialized, witness, target_root, rebound = _restored_fixture(tmp_path)
    source_root = tmp_path / "source"
    code_root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "research_system", code_root / "research_system", dirs_exist_ok=True)
    shutil.copytree(
        REPO_ROOT / ".research-system" / "config",
        code_root / ".research-system" / "config",
        dirs_exist_ok=True,
    )

    foundation = {
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "control_root": str(target_root.resolve()),
        "control_root_required": True,
        "store_identity": str(initialized),
        "endpoint_scheme": rebound["endpoint_scheme"],
        "canonical_hash": "sha256",
        "canonical_uri": f"{rebound['endpoint_scheme']}://restored-control",
        "canonical_tail_position": 0,
        "canonical_tail_hash": "0" * 64,
        "code_roots": [str(code_root.resolve())],
        "schema_root": str((code_root / ".research-system" / "schemas").resolve()),
        "origin_authority_root": str((tmp_path / "origin-authority").resolve()),
        "origin_witness_path": str(initialized.witness_path.resolve()),
        "origin_witness_sha256": witness.raw_sha256,
    }
    foundation["foundation_sha256"] = sha256_hex(canonical_bytes(foundation))
    foundation_path = code_root / ".research-system" / "config" / "foundation.yaml"
    foundation_path.parent.mkdir(parents=True, exist_ok=True)
    foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8", newline="\n")
    binding_path = foundation_path.parent / "binding.yaml"
    binding_path.write_text(
        yaml.safe_dump(
            {
                "code_roots": foundation["code_roots"],
                "control_root": foundation["control_root"],
                "project_id": PROJECT_ID,
                "schema_root": foundation["schema_root"],
                "store_identity": str(initialized),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
        newline="\n",
    )

    manifest_path = target_root / "manifests" / "store-identity.json"
    operation_path = target_root / "manifests" / "restore-binding-evidence.json"
    transaction_path = target_root / "manifests" / ".restore-binding-transaction.json"
    operation = json_load(operation_path)
    transaction = load_restore_binding_transaction(target_root)
    assert transaction is not None
    registry_path = tmp_path / "operator-evidence" / "registry.json"
    _write_json(registry_path, {"registry": "synthetic-mechanics-only", "revision": 1})
    output_path = target_root / Path(operation["output_object_path"])
    assert output_path.is_file()

    locked_digest = sha256_hex(
        canonical_bytes(
            {
                "manifest_sha256": _file_sha256(manifest_path),
                "transaction_sha256": _file_sha256(transaction_path),
                "evidence_sha256": _file_sha256(operation_path),
            }
        )
    )
    admission_path = tmp_path / "operator-evidence" / "admission.json"
    _write_json(
        admission_path,
        {
            "schema_id": "ars://wp6-4/real-a8/admission-evidence",
            "schema_version": "1.0.0",
            "pre_writer": {"status": "verified", "result_hash": operation["restore_preflight_result_hash"]},
            "locked_revalidation": {"status": "verified", "revalidation_sha256": locked_digest},
            "registry_path": str(registry_path.resolve()),
            "registry_sha256": _file_sha256(registry_path),
            "bound_artifacts": [
                {
                    "path": str(output_path.resolve()),
                    "raw_sha256": _file_sha256(output_path),
                    "git_blob_sha1": git_blob_sha1(output_path.read_bytes()),
                }
            ],
        },
    )

    states = ("prepared", "prepared", "prepared", "prepared", "published", "final_validated", "committed", "cleared")
    lineage_digest = sha256_hex(
        canonical_bytes(
            {
                "source_root": str(source_root.resolve()),
                "source_root_identity": dict(witness.initial_physical_root_identity),
                "origin_witness_sha256": witness.raw_sha256,
            }
        )
    )
    recovery_path = tmp_path / "operator-evidence" / "interruption-retry.json"
    _write_json(
        recovery_path,
        {
            "schema_id": "ars://wp6-4/real-a8/interruption-retry-evidence",
            "schema_version": "1.0.0",
            "transaction_generations": [
                {
                    "generation": index,
                    "state": state,
                    "record_sha256": sha256_hex(canonical_bytes({"generation": index, "state": state})),
                }
                for index, state in enumerate(states)
            ],
            "exact_retry": {
                "before_generation": transaction["generation"],
                "after_generation": transaction["generation"],
                "before_transaction_sha256": _file_sha256(transaction_path),
                "after_transaction_sha256": _file_sha256(transaction_path),
                "request_sha256": sha256_hex(b"synthetic-exact-retry-request"),
            },
            "conflicting_retry": {
                "exit_code": 1,
                "failure_code": "conflict",
                "snapshots": [_snapshot(manifest_path), _snapshot(transaction_path)],
            },
            "rollback_recovery": {
                "recovered_state": "cleared",
                "transaction_generation": transaction["generation"],
                "transaction_sha256": _file_sha256(transaction_path),
                "source_lineage_sha256": lineage_digest,
            },
        },
    )

    rejected_path = tmp_path / "operator-evidence" / "rejected-admission.json"
    _write_json(
        rejected_path,
        {
            "schema_id": "ars://wp6-4/real-a8/rejected-admission-probe",
            "schema_version": "1.0.0",
            "exit_code": 1,
            "failure_code": "admission_rejected",
            "snapshots": [_snapshot(registry_path), _snapshot(output_path)],
        },
    )
    if remove_source:
        shutil.rmtree(source_root)

    monkeypatch.setattr(config_module, "canonical_foundation_path", lambda: foundation_path)
    monkeypatch.setattr(harness_module, "canonical_foundation_path", lambda: foundation_path)
    expected_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    ).strip()
    request = A8ProofRequest(
        foundation_path=foundation_path,
        binding_path=binding_path,
        admission_evidence_path=admission_path,
        interruption_evidence_path=recovery_path,
        rejected_admission_path=rejected_path,
        output_root=tmp_path / "candidate-output",
        expected_git_commit=expected_commit,
        git_paths=("research_system/config.py", "research_system/operations/backups.py"),
    )
    return request, foundation_path, source_root, target_root


def json_load(path: Path) -> dict[str, object]:
    return (
        yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.suffix == ".yaml"
        else json.loads(path.read_text(encoding="utf-8"))
    )


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw, usedforsecurity=False).hexdigest()


def test_mechanics_only_positive_capture_covers_restart_and_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _foundation, source_root, _target = _synthetic_request(tmp_path, monkeypatch)
    capture = capture_real_a8_candidate(request=request)

    assert not source_root.exists()
    assert capture.path.is_file()
    assert capture.raw_sha256 == _file_sha256(capture.path)
    assert capture.candidate["candidate_lifecycle"]["candidate_status"] == "produced_unreviewed"
    assert capture.candidate["restart"]["binding_load"] == "successful"
    assert capture.candidate["restart"]["original_root_state"] == "unavailable"
    assert capture.candidate["retry_recovery"]["transaction_generations"][-1]["generation"] == 7
    assert capture.candidate["rejected_admission"]["mutation_result"] == "no_mutation"
    validate_real_a8_candidate(capture.candidate)


def test_mechanics_only_null_foundation_fails_before_output(tmp_path: Path) -> None:
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    output = tmp_path / "candidate-output"
    request = A8ProofRequest(
        foundation_path=REPO_ROOT / ".research-system" / "config" / "foundation.yaml",
        binding_path=tmp_path / "unused-binding.yaml",
        admission_evidence_path=tmp_path / "unused-admission.json",
        interruption_evidence_path=tmp_path / "unused-recovery.json",
        rejected_admission_path=tmp_path / "unused-rejection.json",
        output_root=output,
        expected_git_commit=expected_commit,
        git_paths=("research_system/config.py",),
    )
    with pytest.raises(EvidenceHarnessError, match="owner-materialized canonical foundation"):
        capture_real_a8_candidate(request=request)
    assert not output.exists()


def test_mechanics_only_witness_digest_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, foundation_path, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    value = yaml.safe_load(foundation_path.read_text(encoding="utf-8"))
    value["origin_witness_sha256"] = "0" * 64
    unsigned = {key: item for key, item in value.items() if key != "foundation_sha256"}
    value["foundation_sha256"] = sha256_hex(canonical_bytes(unsigned))
    foundation_path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8", newline="\n")
    with pytest.raises(EvidenceHarnessError, match="owner-materialized canonical foundation"):
        capture_real_a8_candidate(request=request)


def test_mechanics_only_still_available_original_root_is_a_hard_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _foundation, source_root, _target = _synthetic_request(tmp_path, monkeypatch, remove_source=False)
    with pytest.raises(EvidenceHarnessError, match="original root is still available"):
        capture_real_a8_candidate(request=request)
    assert source_root.is_dir()
    assert not request.output_root.exists()


def test_mechanics_only_rejected_probe_mutation_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    value = json_load(request.rejected_admission_path)
    value["snapshots"][0]["after_raw_sha256"] = "0" * 64
    request.rejected_admission_path.write_bytes(canonical_bytes(value))
    with pytest.raises(EvidenceHarnessError, match="rejected admission probe mutated"):
        capture_real_a8_candidate(request=request)
    assert not request.output_root.exists()


def test_mechanics_only_lifecycle_hard_stop_rejects_claims(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    candidate = capture_real_a8_candidate(request=request).candidate
    invalid = copy.deepcopy(candidate)
    invalid["candidate_lifecycle"]["a8_status"] = "claimed"
    with pytest.raises(EvidenceHarnessError, match="schema violation|lifecycle"):
        validate_real_a8_candidate(invalid)


def test_mechanics_only_exact_retry_converges(tmp_path: Path) -> None:
    store = ContentAddressedEvidenceStore(tmp_path / "objects")
    first = store.write_once("same-key", b"same-bytes")
    second = store.write_once("same-key", b"same-bytes")
    assert second == first


def test_mechanics_only_conflicting_retry_is_rejected(tmp_path: Path) -> None:
    store = ContentAddressedEvidenceStore(tmp_path / "objects")
    store.write_once("same-key", b"first-bytes")
    with pytest.raises(EvidenceConflictError, match="conflicts"):
        store.write_once("same-key", b"different-bytes")
