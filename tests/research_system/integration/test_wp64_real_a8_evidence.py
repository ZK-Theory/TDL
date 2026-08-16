"""Mechanics-only synthetic tests for the later WP6.4 real-A8 proof.

These tests never accept their temporary foundation values as owner evidence and
never claim that a real A8 operation occurred. Temporary values remain fixtures
for harness mechanics only.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import py_compile
import shutil
import subprocess
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

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
from tests.research_system.factories import PROJECT_ID, REPO_ROOT
from tests.research_system.integration.test_gate5_release_tranche import (
    _build_restore_case,
    _prepare_restore_admission,
    _rebind_restore_case,
)


pytestmark = pytest.mark.integration


def test_public_harness_capture_surface_exists() -> None:
    assert callable(capture_real_a8_candidate)


def test_fresh_process_records_the_interpreter_it_executed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_path = tmp_path / "binding.yaml"
    binding_path.write_text("binding", encoding="utf-8")
    code_root = tmp_path / "code"
    code_root.mkdir()
    expected = SimpleNamespace(
        control_root=(tmp_path / "control").resolve(),
        project_id=PROJECT_ID,
        store_identity="store-identity",
    )
    executed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        executed["interpreter"] = argv[0]
        executed["timeout"] = kwargs.get("timeout")
        monkeypatch.setattr(harness_module.sys, "executable", str(tmp_path / "different-python"))
        stdout = json.dumps(
            {
                "control_root": str(expected.control_root),
                "project_id": expected.project_id,
                "store_identity": expected.store_identity,
            }
        ).encode("utf-8")
        return SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(harness_module.subprocess, "run", fake_run)

    restart = harness_module._fresh_process_binding_load(
        binding_path=binding_path,
        code_root=code_root,
        expected=expected,
    )

    assert restart["interpreter"] == executed["interpreter"]
    assert restart["interpreter"] != str(Path(harness_module.sys.executable).resolve(strict=False))
    assert executed["timeout"] == 30


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _jsonable(value):
    if isinstance(value, Path):
        return str(value.resolve(strict=False))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _snapshot(path: Path) -> dict[str, str]:
    digest = _file_sha256(path)
    return {"path": str(path.resolve()), "before_raw_sha256": digest, "after_raw_sha256": digest}


def _synthetic_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, remove_source: bool = True):
    case = _build_restore_case(tmp_path, rebindable=True)
    prepared = _prepare_restore_admission(case)
    _rebind_restore_case(case, prepared.result)
    initialized_witness = case["witness"]
    witness_path = case["witness_path"]
    target_root = case["target"]
    source_root = tmp_path / "source"
    code_root = tmp_path / "code"
    foundation_root = code_root
    shutil.copytree(
        REPO_ROOT / ".research-system" / "schemas", code_root / ".research-system" / "schemas", dirs_exist_ok=True
    )
    shutil.copytree(REPO_ROOT / "research_system", code_root / "research_system", dirs_exist_ok=True)
    shutil.copytree(
        REPO_ROOT / ".research-system" / "config",
        foundation_root / ".research-system" / "config",
        dirs_exist_ok=True,
    )

    foundation = {
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "control_root": str(target_root.resolve()),
        "control_root_required": True,
        "store_identity": case["receipt"].store_identity,
        "endpoint_scheme": case["receipt"].source_endpoint_scheme,
        "canonical_hash": "sha256",
        "canonical_uri": config_module._canonical_local_cli_uri(target_root.resolve()),
        "canonical_tail_position": 0,
        "canonical_tail_hash": "0" * 64,
        "code_roots": [str(code_root.resolve())],
        "schema_root": str((code_root / ".research-system" / "schemas").resolve()),
        "origin_authority_root": str((tmp_path / "origin-authority").resolve()),
        "origin_witness_path": str(witness_path.resolve()),
        "origin_witness_sha256": initialized_witness.raw_sha256,
    }
    foundation["foundation_sha256"] = sha256_hex(canonical_bytes(foundation))
    foundation_path = foundation_root / ".research-system" / "config" / "foundation.yaml"
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
                "store_identity": case["receipt"].store_identity,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
        newline="\n",
    )

    receipt_path = tmp_path / "operator-evidence" / "backup-receipt.json"
    _write_json(receipt_path, _jsonable(asdict(case["receipt"])))
    registry_path = tmp_path / "operator-evidence" / "registry.json"
    registry_value = _jsonable(asdict(case["registry"]))
    registry_value.update({"schema_id": "ars://evals/evidence-store-registry", "schema_version": "1.0.0"})
    _write_json(registry_path, registry_value)
    runtime_inputs_path = tmp_path / "operator-evidence" / "runtime-inputs.json"
    admission_bundle = _jsonable(asdict(prepared))
    admission_bundle.update(
        {
            "schema_id": "ars://wp6-4/real-a8/runtime-admission",
            "schema_version": "1.0.0",
        }
    )
    admission_bundle["closure"]["registry"].update(
        {
            "schema_id": "ars://evals/evidence-store-registry",
            "schema_version": "1.0.0",
        }
    )
    _write_json(
        runtime_inputs_path,
        {
            "schema_id": "ars://wp6-4/real-a8/runtime-inputs",
            "schema_version": "1.0.0",
            "receipt_path": str(receipt_path.resolve()),
            "registry_path": str(registry_path.resolve()),
            "snapshot_path": str(case["snapshot_path"].resolve()),
            "endpoint_ownership_path": str(case["endpoint_path"].resolve()),
            "artefact_manifest_path": str(case["artefact_manifest_path"].resolve()),
            "admission_bundle": admission_bundle,
        },
    )
    if remove_source:
        shutil.rmtree(source_root)

    monkeypatch.setattr(config_module, "canonical_foundation_path", lambda: foundation_path)
    monkeypatch.setattr(harness_module, "canonical_foundation_path", lambda: foundation_path)
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    request = A8ProofRequest(
        foundation_path=foundation_path,
        binding_path=binding_path,
        runtime_inputs_path=runtime_inputs_path,
        output_root=tmp_path / "candidate-output",
        expected_git_commit=expected_commit,
        git_paths=harness_module.governed_repository_paths(),
    )
    return request, foundation_path, source_root, target_root


def json_load(path: Path) -> dict[str, object]:
    return (
        yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.suffix == ".yaml"
        else json.loads(path.read_text(encoding="utf-8"))
    )


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(  # nosemgrep: insecure-hash-algorithm-sha1  # nosec B324
        f"blob {len(raw)}\0".encode() + raw,
        usedforsecurity=False,
    ).hexdigest()


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
        runtime_inputs_path=tmp_path / "unused-runtime-inputs.json",
        output_root=output,
        expected_git_commit=expected_commit,
        git_paths=harness_module.governed_repository_paths(),
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
    value = json_load(request.runtime_inputs_path)
    value["receipt_path"] = str((tmp_path / "operator-evidence" / "missing-receipt.json").resolve())
    request.runtime_inputs_path.write_bytes(canonical_bytes(value))
    with pytest.raises(EvidenceHarnessError, match="runtime backup receipt|runtime receipt"):
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


def test_red_caller_attestation_positive_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The old positive fixture must stop being accepted as runtime proof."""

    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    narrative = json_load(request.runtime_inputs_path)
    narrative["admission_bundle"]["schema_id"] = "ars://wp6-4/real-a8/admission-evidence"
    request.runtime_inputs_path.write_bytes(canonical_bytes(narrative))
    with pytest.raises(EvidenceHarnessError, match="canonical runtime|public runtime"):
        capture_real_a8_candidate(request=request)


def test_red_output_root_equal_source_is_rejected_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The old harness recreated an unavailable source at its output path."""

    request, _foundation, source_root, _target = _synthetic_request(tmp_path, monkeypatch)
    collided = replace(request, output_root=source_root)
    with pytest.raises(EvidenceHarnessError, match="source.*output|output.*source"):
        capture_real_a8_candidate(request=collided)
    assert not source_root.exists()


@pytest.mark.parametrize(
    "case",
    ("output_parent", "output_absolute", "artefact_parent", "artefact_malformed"),
)
def test_bound_artifact_paths_reject_operator_path_escape(
    tmp_path: Path,
    case: str,
) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir()
    output_path = "objects/result.json"
    artefacts: list[dict[str, str]] = []
    if case == "output_parent":
        output_path = "../outside.json"
    elif case == "output_absolute":
        output_path = str((tmp_path / "outside.json").resolve())
    elif case == "artefact_parent":
        artefacts = [{"relative_path": "../outside.json"}]
    else:
        artefacts = [{}]
    manifest_path = tmp_path / "artefact-manifest.json"
    _write_json(manifest_path, {"artefacts": artefacts})
    runtime = SimpleNamespace(artefact_manifest_path=manifest_path)

    with pytest.raises(EvidenceHarnessError, match="escapes|lacks a relative path"):
        harness_module._bound_artifact_paths(target_root, runtime, output_path)


def test_exact_retry_uses_the_explicit_target_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _foundation, _source, target_root = _synthetic_request(tmp_path, monkeypatch)
    transaction_path = harness_module.restore_binding_transaction_path(target_root)
    detached_transaction_path = tmp_path / "detached-transaction.json"
    shutil.copyfile(transaction_path, detached_transaction_path)
    transaction = harness_module.load_restore_binding_transaction(target_root)
    assert transaction is not None

    retry = harness_module._capture_exact_retry(
        target_root=target_root,
        transaction_path=detached_transaction_path,
        transaction=transaction,
        result_bundle={"pre_writer": {"request_identity_sha256": "request-identity"}},
    )

    assert retry["result"] == "converged"


def test_red_single_snapshot_rejects_replacement_between_parse_and_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The old loader parsed a replacement after recording the old file hash."""

    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    alternate_registry = tmp_path / "operator-evidence" / "registry-alternate.json"
    alternate_registry.write_bytes(request.runtime_inputs_path.parent.joinpath("registry.json").read_bytes())
    replacement = json_load(request.runtime_inputs_path)
    replacement["registry_path"] = str(alternate_registry.resolve())
    original_snapshot = harness_module._read_physical_file_snapshot
    replaced = False

    def race(path: Path, role: str):
        nonlocal replaced
        snapshot = original_snapshot(path, role)
        if not replaced and Path(path).resolve() == request.runtime_inputs_path.resolve():
            replaced = True
            request.runtime_inputs_path.write_bytes(canonical_bytes(replacement))
        return snapshot

    monkeypatch.setattr(harness_module, "_read_physical_file_snapshot", race)
    with pytest.raises(EvidenceHarnessError, match="snapshot|changed|replacement"):
        capture_real_a8_candidate(request=request)


def test_locked_runtime_preserves_specific_harness_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, foundation_path, _source, target_root = _synthetic_request(tmp_path, monkeypatch)
    approved, _foundation_record = harness_module._load_approved_foundation(foundation_path)
    runtime = harness_module._load_runtime_inputs(request.runtime_inputs_path)
    manifest_path = target_root / "manifests" / "store-identity.json"
    evidence_path = target_root / "manifests" / "restore-binding-evidence.json"
    transaction_path = harness_module.restore_binding_transaction_path(target_root)
    operation_evidence = harness_module.load_canonical_restore_binding_evidence(target_root)
    transaction = harness_module.load_restore_binding_transaction(target_root)
    assert operation_evidence is not None
    assert transaction is not None
    witness_path = Path(approved.origin_witness_path)
    witness = harness_module.load_store_origin_witness(
        witness_path,
        expected_sha256=approved.origin_witness_sha256,
    )

    def reject_surface(*_args, **_kwargs) -> None:
        raise EvidenceHarnessError("specific locked-surface failure")

    monkeypatch.setattr(harness_module, "_assert_surface_unchanged", reject_surface)

    with pytest.raises(EvidenceHarnessError, match="specific locked-surface failure"):
        harness_module._capture_runtime_evidence(
            runtime=runtime,
            transaction=transaction,
            transaction_record=harness_module._file_record(transaction_path, "restore_transaction"),
            target_root=target_root,
            manifest_path=manifest_path,
            evidence_path=evidence_path,
            transaction_path=transaction_path,
            operation_evidence=operation_evidence,
            witness=witness,
            witness_path=witness_path,
            approved=approved,
        )


def test_red_git_identity_requires_complete_governed_path_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The old capture accepted an arbitrary caller-selected one-file proof."""

    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    incomplete = replace(request, git_paths=("research_system/config.py",))
    with pytest.raises(EvidenceHarnessError, match="governed|Git.*path|complete"):
        capture_real_a8_candidate(request=incomplete)


def test_governed_repository_paths_normalizes_cached_module_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    cached = REPO_ROOT / "research_system" / "example" / "__pycache__" / "cached.cpython-313.pyc"
    monkeypatch.setitem(
        harness_module.sys.modules,
        "research_system._wp64_cached_path_probe",
        SimpleNamespace(__file__=str(cached)),
    )

    assert "research_system/example/cached.py" in harness_module.governed_repository_paths()


def test_red_git_identity_rejects_dirty_schema_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    paths = harness_module.governed_repository_paths()
    target = (REPO_ROOT / ".research-system" / "schemas" / "wp6-4" / "real-a8-proof-candidate.schema.json").resolve()
    original_snapshot = harness_module._read_physical_file_snapshot

    def dirty_snapshot(path: Path, role: str):
        snapshot = original_snapshot(path, role)
        if Path(path).resolve() != target:
            return snapshot
        raw = snapshot.raw + b"\n"
        record = dict(snapshot.record)
        record["size"] = len(raw)
        record["raw_sha256"] = sha256_hex(raw)
        record["git_blob_sha1"] = git_blob_sha1(raw)
        return harness_module._PhysicalFileSnapshot(snapshot.path, raw, record)

    monkeypatch.setattr(harness_module, "_read_physical_file_snapshot", dirty_snapshot)
    with pytest.raises(EvidenceHarnessError, match="bytes differ"):
        harness_module._capture_git_identity(expected_commit, paths)


def test_red_git_identity_rejects_executed_harness_substitution(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    paths = harness_module.governed_repository_paths()
    target = (REPO_ROOT / "research_system" / "evidence" / "wp64_real_a8.py").resolve()
    original_snapshot = harness_module._read_physical_file_snapshot

    def substituted_snapshot(path: Path, role: str):
        snapshot = original_snapshot(path, role)
        if Path(path).resolve() != target:
            return snapshot
        raw = snapshot.raw.replace(b"Fail-closed", b"Substituted", 1)
        assert raw != snapshot.raw, "substitution marker is no longer present in the harness source"
        record = dict(snapshot.record)
        record["size"] = len(raw)
        record["raw_sha256"] = sha256_hex(raw)
        record["git_blob_sha1"] = git_blob_sha1(raw)
        return harness_module._PhysicalFileSnapshot(snapshot.path, raw, record)

    monkeypatch.setattr(harness_module, "_read_physical_file_snapshot", substituted_snapshot)
    with pytest.raises(EvidenceHarnessError, match="bytes differ"):
        harness_module._capture_git_identity(expected_commit, paths)


def test_red_candidate_id_is_recomputed_after_direct_tamper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    candidate = capture_real_a8_candidate(request=request).candidate
    tampered = copy.deepcopy(candidate)
    tampered["candidate_id"] = "a8c_" + "0" * 64
    with pytest.raises(EvidenceHarnessError, match="candidate_id|identity"):
        validate_real_a8_candidate(tampered)
    joined_tamper = copy.deepcopy(candidate)
    joined_tamper["external_operation"]["transaction_id"] = "a" * 64
    joined_tamper_without_id = dict(joined_tamper)
    joined_tamper_without_id.pop("candidate_id")
    joined_tamper["candidate_id"] = harness_module._candidate_id(joined_tamper_without_id)
    with pytest.raises(EvidenceHarnessError, match="join|transaction"):
        validate_real_a8_candidate(joined_tamper)


def test_red_validator_joins_every_probe_transaction_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    candidate = capture_real_a8_candidate(request=request).candidate
    transaction_paths = (
        ("admission", "pre_writer"),
        ("admission", "locked_revalidation"),
        ("admission", "locked_revalidation", "lock_identity"),
        ("rejected_admission",),
        ("retry_recovery", "conflicting_retry"),
    )

    for path in transaction_paths:
        tampered = copy.deepcopy(candidate)
        record = tampered
        for key in path:
            record = record[key]
        record["transaction_id"] = "f" * 64
        without_id = dict(tampered)
        without_id.pop("candidate_id")
        tampered["candidate_id"] = harness_module._candidate_id(without_id)
        try:
            validate_real_a8_candidate(tampered)
        except EvidenceHarnessError as exc:
            assert "transaction" in str(exc)
        else:
            pytest.fail(f"validator accepted a spliced transaction_id at {'.'.join(path)}")


def test_red_interrupted_publication_reconciles_partial_object_on_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentAddressedEvidenceStore(tmp_path / "objects")
    original_write = harness_module._write_exclusive
    interrupted = False

    def leave_partial_then_fail(path: Path, raw: bytes) -> None:
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw[: max(1, len(raw) // 2)])
            raise OSError("injected publication interruption")
        original_write(path, raw)

    monkeypatch.setattr(harness_module, "_write_exclusive", leave_partial_then_fail)
    with pytest.raises(OSError, match="interruption"):
        store.write_once("interrupted-key", b"complete-payload")
    monkeypatch.setattr(harness_module, "_write_exclusive", original_write)

    result = store.write_once("interrupted-key", b"complete-payload")
    assert result[0].read_bytes() == b"complete-payload"


def test_red_capture_rejects_runtime_receipt_with_stale_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    runtime = json_load(request.runtime_inputs_path)
    receipt_path = Path(str(runtime["receipt_path"]))
    receipt = json_load(receipt_path)
    retained_seal = receipt["receipt_hash"]
    receipt["created_at"] = "2026-07-12T00:00:00Z"
    receipt["receipt_hash"] = retained_seal
    receipt_path.write_bytes(canonical_bytes(receipt))

    with pytest.raises(EvidenceHarnessError, match="receipt.*(?:seal|hash)|(?:seal|hash).*receipt"):
        capture_real_a8_candidate(request=request)
    assert not request.output_root.exists()


def test_red_capture_rejects_retained_source_identity_at_output_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _foundation, source_root, _target = _synthetic_request(
        tmp_path,
        monkeypatch,
        remove_source=False,
    )
    source_root.rename(request.output_root)
    before = {
        path.relative_to(request.output_root).as_posix(): _file_sha256(path)
        for path in request.output_root.rglob("*")
        if path.is_file()
    }
    claims_existed = (request.output_root / "claims").exists()
    objects_existed = (request.output_root / "objects").exists()

    with pytest.raises(EvidenceHarnessError, match="source.*(?:identity|output)|output.*(?:identity|source)"):
        capture_real_a8_candidate(request=request)

    after = {
        path.relative_to(request.output_root).as_posix(): _file_sha256(path)
        for path in request.output_root.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert (request.output_root / "claims").exists() is claims_existed
    assert (request.output_root / "objects").exists() is objects_existed


@pytest.mark.parametrize("protected_name", ["code", "target", "origin"])
def test_red_existing_output_root_rejects_physical_alias_of_every_protected_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protected_name: str,
) -> None:
    roots = {name: tmp_path / name for name in ("code", "target", "origin", "output")}
    for root in roots.values():
        root.mkdir()
    resolved = {name: root.resolve() for name, root in roots.items()}
    identities = {path: {"device": "1", "inode": str(index + 10)} for index, path in enumerate(resolved.values())}
    identities[resolved["output"]] = identities[resolved[protected_name]]
    monkeypatch.setattr(
        harness_module,
        "physical_root_identity",
        lambda path: identities[Path(path).resolve(strict=True)],
    )

    with pytest.raises(EvidenceHarnessError, match="physical alias.*protected root"):
        harness_module._validate_output_root(
            roots["output"],
            source_root=tmp_path / "unavailable-source",
            code_roots=(roots["code"],),
            target_root=roots["target"],
            origin_root=roots["origin"],
        )

    assert not (roots["output"] / "claims").exists()
    assert not (roots["output"] / "objects").exists()


@pytest.mark.parametrize("protected_name", ["code", "target", "origin"])
def test_red_publication_rechecks_reject_late_physical_alias_of_every_protected_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protected_name: str,
) -> None:
    roots = {name: tmp_path / name for name in ("code", "target", "origin", "output")}
    for root in roots.values():
        root.mkdir()
    resolved = {name: root.resolve() for name, root in roots.items()}
    identities = {path: {"device": "1", "inode": str(index + 20)} for index, path in enumerate(resolved.values())}
    monkeypatch.setattr(
        harness_module,
        "physical_root_identity",
        lambda path: identities[Path(path).resolve(strict=True)],
    )
    protected_roots = (roots["code"], roots["target"], roots["origin"])

    harness_module._validate_output_root(
        roots["output"],
        source_root=tmp_path / "unavailable-source",
        code_roots=(roots["code"],),
        target_root=roots["target"],
        origin_root=roots["origin"],
    )
    identities[resolved["output"]] = identities[resolved[protected_name]]

    with pytest.raises(EvidenceHarnessError, match="physical alias.*protected root"):
        harness_module._revalidate_publication_inputs(
            (),
            source_root=tmp_path / "unavailable-source",
            output_root=roots["output"],
            protected_roots=protected_roots,
        )
    with pytest.raises(EvidenceHarnessError, match="physical alias.*protected root"):
        ContentAddressedEvidenceStore(
            roots["output"],
            forbidden_physical_roots=protected_roots,
        ).write_once("late-alias", b"must-not-publish")

    assert not (roots["output"] / "claims").exists()
    assert not (roots["output"] / "objects").exists()


def test_execution_root_selection_uses_canonical_checkout_with_multiple_approved_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoy_root = tmp_path / "a-decoy-root"
    executing_root = tmp_path / "z-executing-root"
    decoy_root.mkdir()
    executing_root.mkdir()
    foundation_path = executing_root / ".research-system" / "config" / "foundation.yaml"
    monkeypatch.setattr(harness_module, "canonical_foundation_path", lambda: foundation_path)
    approved = SimpleNamespace(
        code_roots=tuple(sorted((decoy_root.resolve(), executing_root.resolve()), key=str)),
    )

    assert harness_module._approved_execution_root(approved) == executing_root.resolve()


@pytest.mark.parametrize("consumed_loader", ["foundation", "binding"])
def test_red_capture_binds_foundation_and_binding_to_single_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    consumed_loader: str,
) -> None:
    request, foundation_path, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    canonical_path = foundation_path if consumed_loader == "foundation" else request.binding_path
    a_raw = canonical_path.read_bytes()
    a_foundation = json_load(foundation_path)
    if consumed_loader == "foundation":
        b_value = dict(a_foundation)
        b_value["canonical_uri"] = "local-cli://alternate-aba-snapshot"
        b_unsigned = {key: value for key, value in b_value.items() if key != "foundation_sha256"}
        b_value["foundation_sha256"] = sha256_hex(canonical_bytes(b_unsigned))
    else:
        b_value = json_load(request.binding_path)
        b_value.update(
            {
                "origin_authority_root": a_foundation["origin_authority_root"],
                "origin_witness_path": a_foundation["origin_witness_path"],
                "origin_witness_sha256": a_foundation["origin_witness_sha256"],
            }
        )
    b_raw = yaml.safe_dump(b_value, sort_keys=False).encode("utf-8")
    assert b_raw != a_raw
    b_hold = canonical_path.with_name(f".{canonical_path.name}.aba-b")
    b_hold.write_bytes(b_raw)
    original_snapshot = harness_module._read_physical_file_snapshot
    swapped = False

    def swap_after_snapshot(path: Path, role: str):
        nonlocal swapped
        snapshot = original_snapshot(path, role)
        if not swapped and Path(path).resolve(strict=False) == canonical_path.resolve(strict=False):
            os.replace(b_hold, canonical_path)
            swapped = True
        return snapshot

    monkeypatch.setattr(harness_module, "_read_physical_file_snapshot", swap_after_snapshot)
    try:
        with pytest.raises(EvidenceHarnessError, match="snapshot|changed|replacement|foundation|binding"):
            capture_real_a8_candidate(request=request)
    finally:
        canonical_path.write_bytes(a_raw)
        b_hold.unlink(missing_ok=True)

    assert swapped is True
    assert not (request.output_root / "claims").exists()
    assert not (request.output_root / "objects").exists()


def test_red_capture_rejects_fresh_process_code_not_bound_to_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, foundation_path, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    foundation = json_load(foundation_path)
    execution_root = Path(str(foundation["code_roots"][0]))
    executed_config = execution_root / "research_system" / "config.py"
    executed_config.write_bytes(executed_config.read_bytes() + b"\n# harmless F4 execution-root byte perturbation\n")

    with pytest.raises(EvidenceHarnessError, match="execution.*(?:Git|HEAD|bytes)|(?:Git|HEAD).*execution"):
        capture_real_a8_candidate(request=request)
    assert not request.output_root.exists()


def test_red_fresh_process_ignores_unchecked_hash_config_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, foundation_path, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    foundation = json_load(foundation_path)
    execution_root = Path(str(foundation["code_roots"][0]))
    executed_config = execution_root / "research_system" / "config.py"
    tracked_config = REPO_ROOT / "research_system" / "config.py"
    marker = tmp_path / "unchecked-hash-config-cache-consumed.txt"
    cached_source = tmp_path / "cached-config.py"
    cached_source.write_bytes(
        executed_config.read_bytes()
        + (f"\n__import__('pathlib').Path({str(marker)!r}).write_text('consumed', encoding='utf-8')\n").encode("utf-8")
    )
    cache_path = Path(importlib.util.cache_from_source(str(executed_config)))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    py_compile.compile(
        str(cached_source),
        cfile=str(cache_path),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )

    assert executed_config.read_bytes() == tracked_config.read_bytes()
    capture = capture_real_a8_candidate(request=request)
    assert executed_config.read_bytes() == tracked_config.read_bytes()
    assert not marker.exists()
    assert capture.candidate["restart"]["binding_load"] == "successful"


def test_red_validator_rejects_registry_digest_join_with_recomputed_candidate_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _foundation, _source, _target = _synthetic_request(tmp_path, monkeypatch)
    candidate = copy.deepcopy(capture_real_a8_candidate(request=request).candidate)
    candidate["registry"]["raw_sha256"] = "0" * 64
    without_id = dict(candidate)
    without_id.pop("candidate_id")
    candidate["candidate_id"] = harness_module._candidate_id(without_id)

    with pytest.raises(EvidenceHarnessError, match="registry.*(?:digest|raw_sha256)|raw_sha256.*registry"):
        validate_real_a8_candidate(candidate)


def test_red_new_store_root_fsyncs_parent_before_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "new-evidence-root"
    events: list[tuple[str, Path]] = []
    original_fsync = harness_module.fsync_directory
    original_write = harness_module._write_exclusive

    def recording_fsync(path: Path) -> None:
        events.append(("fsync", Path(path).resolve(strict=False)))
        original_fsync(path)

    def recording_write(path: Path, raw: bytes) -> None:
        events.append(("write", Path(path).resolve(strict=False)))
        original_write(path, raw)

    monkeypatch.setattr(harness_module, "fsync_directory", recording_fsync)
    monkeypatch.setattr(harness_module, "_write_exclusive", recording_write)
    ContentAddressedEvidenceStore(root).write_once("new-root", b"durable-payload")

    first_write = next(index for index, event in enumerate(events) if event[0] == "write")
    parent_fsyncs = [
        index for index, event in enumerate(events) if event == ("fsync", root.parent.resolve(strict=False))
    ]
    assert parent_fsyncs
    assert parent_fsyncs[0] < first_write
