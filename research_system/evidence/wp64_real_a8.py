"""Fail-closed, operator-only preparation for a later WP6.4 real-A8 proof.

The harness consumes an owner-materialized foundation, canonical runtime input
files, and an already completed moved-store operation.  It never initializes a
store, chooses owner values, executes a restore, or turns caller prose into
evidence.  The only durable writes are the final candidate object and claim,
published after all physical and runtime checks have completed.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed interpreter and Git metadata probes
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ApprovedProjectBinding, ControlBinding, canonical_foundation_path
from research_system.errors import ArsError, ConflictError
from research_system.evals.retention import EvidenceStoreRegistry
from research_system.operations.backups import (
    ArtefactBinding,
    BackupReceipt,
    RestoreAdmissionBundle,
    RestoreAdmissionClosure,
    RestoreBoundArtefact,
    RestoreBoundFile,
    RestorePreflightResult,
    revalidate_restore_admission_closure,
    seal_backup_receipt,
    validate_restore_preflight_result,
    verify_restore_before_writer_lease,
)
from research_system.schema_registry import bundled_runtime_schema_registry
from research_system.store.durability import fsync_directory
from research_system.store.identity import (
    _RESTORE_STEPS,
    load_canonical_restore_binding_evidence,
    load_restore_binding_transaction,
    load_store_manifest,
    load_store_origin_witness,
    physical_root_identity,
    restore_binding_transaction_path,
    validate_approved_origin_witness_path,
    verify_restore_binding_admission,
)
from research_system.store.lock import CompositeWriterLock


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SCHEMA_ID = "ars://wp6-4/real-a8-proof-candidate"
_RUNTIME_INPUTS_SCHEMA_ID = "ars://wp6-4/real-a8/runtime-inputs"
_RUNTIME_ADMISSION_SCHEMA_ID = "ars://wp6-4/real-a8/runtime-admission"
_RUNTIME_INPUTS_SCHEMA_VERSION = "1.0.0"
_TRANSACTION_STEPS = tuple(_RESTORE_STEPS)
_TRANSACTION_STATE_BY_STEP = (
    "prepared",
    "prepared",
    "prepared",
    "prepared",
    "published",
    "final_validated",
    "committed",
    "cleared",
)


class EvidenceHarnessError(ArsError):
    """Raised when the operator proof cannot be captured without inference."""


class EvidenceConflictError(ConflictError):
    """Raised when one immutable evidence key is reused with different bytes."""


@dataclass(frozen=True, slots=True)
class A8ProofRequest:
    """Paths and exact subject supplied by the operator for one capture."""

    foundation_path: Path
    binding_path: Path
    runtime_inputs_path: Path
    output_root: Path
    expected_git_commit: str
    git_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateCapture:
    """The validated candidate and the immutable object written for it."""

    candidate: dict[str, Any]
    path: Path
    raw_sha256: str
    git_blob_sha1: str


@dataclass(frozen=True, slots=True)
class _PhysicalFileSnapshot:
    path: Path
    raw: bytes
    record: dict[str, Any]
    value: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class _RuntimeInputs:
    bundle_record: dict[str, Any]
    receipt_record: dict[str, Any]
    registry_record: dict[str, Any]
    snapshot_record: dict[str, Any]
    endpoint_record: dict[str, Any]
    artefact_manifest_record: dict[str, Any]
    receipt: BackupReceipt
    registry: EvidenceStoreRegistry
    snapshot_path: Path
    endpoint_ownership_path: Path
    artefact_manifest_path: Path
    actor_id: str
    authority_grant_id: str
    admission_bundle: RestoreAdmissionBundle


class ContentAddressedEvidenceStore:
    """Write one logical evidence key with durable, crash-convergent objects."""

    def __init__(
        self,
        root: Path,
        *,
        forbidden_physical_root_identity: Mapping[str, str] | None = None,
        forbidden_physical_roots: Sequence[Path] = (),
    ) -> None:
        self.root = Path(root)
        self.forbidden_physical_root_identity = (
            dict(forbidden_physical_root_identity) if forbidden_physical_root_identity is not None else None
        )
        self.forbidden_physical_roots = tuple(Path(root) for root in forbidden_physical_roots)

    def write_once(self, key: str, raw: bytes) -> tuple[Path, str, str]:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", key):
            raise EvidenceHarnessError("evidence object key is invalid")
        digest = sha256_hex(raw)
        blob_sha1 = _git_blob_sha1(raw)
        claim_path = self.root / "claims" / f"{key}.json"
        object_path = self.root / "objects" / f"sha256-{digest}.json"
        root_was_absent = not self.root.exists()
        self.root.mkdir(parents=True, exist_ok=True)
        if root_was_absent:
            fsync_directory(self.root.parent)
        _validate_no_follow_directory(self.root, "candidate output root")
        if (
            self.forbidden_physical_root_identity is not None
            and physical_root_identity(self.root) == self.forbidden_physical_root_identity
        ):
            raise EvidenceHarnessError("candidate output root retains the original source physical identity")
        for protected_root in self.forbidden_physical_roots:
            _require_physical_root_disjoint_if_available(
                self.root,
                protected_root,
                "candidate output root is a physical alias of a protected root",
            )
        claims = self.root / "claims"
        objects = self.root / "objects"
        claims.mkdir(parents=True, exist_ok=True)
        objects.mkdir(parents=True, exist_ok=True)
        fsync_directory(self.root)
        fsync_directory(claims)
        fsync_directory(objects)

        if claim_path.exists():
            claim = _read_canonical_json(claim_path, "evidence claim")
            _validate_claim(claim, key, digest, blob_sha1, object_path, self.root)
            _atomic_write(object_path, raw)
            return object_path, digest, blob_sha1

        _atomic_write(object_path, raw)
        claim = canonical_bytes(
            {
                "key": key,
                "raw_sha256": digest,
                "git_blob_sha1": blob_sha1,
                "object_path": object_path.relative_to(self.root).as_posix(),
            }
        )
        try:
            _atomic_write(claim_path, claim)
        except EvidenceConflictError:
            if not claim_path.exists():
                raise
            existing = _read_canonical_json(claim_path, "evidence claim")
            _validate_claim(existing, key, digest, blob_sha1, object_path, self.root)
        return object_path, digest, blob_sha1


def capture_real_a8_candidate(*, request: A8ProofRequest) -> CandidateCapture:
    """Capture a produced-unreviewed candidate from physical/runtime evidence."""

    approved, foundation_record = _load_approved_foundation(request.foundation_path)
    _load_canonical_binding(request.binding_path, approved)
    source_root = Path(approved.origin_witness.initial_control_root).resolve(strict=False)
    target_root = approved.control_root.resolve(strict=True)
    origin_root = approved.origin_authority_root.resolve(strict=True)
    output_root = _validate_output_root(
        request.output_root,
        source_root=source_root,
        code_roots=approved.code_roots,
        target_root=target_root,
        origin_root=origin_root,
    )
    _validate_root_relationships(approved, source_root, target_root, origin_root, output_root)

    witness_path, witness_origin_root = validate_approved_origin_witness_path(
        approved.origin_witness_path,
        approved.origin_witness,
    )
    if witness_origin_root != origin_root:
        raise EvidenceHarnessError("origin witness authority root differs from foundation")
    witness = load_store_origin_witness(witness_path, expected_sha256=approved.origin_witness_sha256)
    witness_snapshot = _read_physical_file_snapshot(witness_path, "origin witness")
    if witness_snapshot.raw != witness.raw_bytes or witness.raw_sha256 != approved.origin_witness_sha256:
        raise EvidenceHarnessError("origin witness bytes changed during capture")

    runtime = _load_runtime_inputs(request.runtime_inputs_path)
    manifest_path = target_root / "manifests" / "store-identity.json"
    transaction_path = restore_binding_transaction_path(target_root)
    evidence_path = target_root / "manifests" / "restore-binding-evidence.json"
    manifest_snapshot = _read_canonical_snapshot(manifest_path, "destination store manifest")
    evidence_snapshot = _read_canonical_snapshot(evidence_path, "restore operation evidence")
    transaction_snapshot = _read_canonical_snapshot(transaction_path, "restore transaction")
    manifest = _load_store_manifest(target_root, approved)
    operation_evidence = load_canonical_restore_binding_evidence(target_root)
    transaction = load_restore_binding_transaction(target_root)
    if operation_evidence is None or transaction is None:
        raise EvidenceHarnessError("moved-store operation evidence is incomplete")
    if (
        manifest_snapshot.value != manifest
        or evidence_snapshot.value != operation_evidence
        or transaction_snapshot.value != transaction
    ):
        raise EvidenceHarnessError("store evidence changed between one physical snapshot and public loading")
    _validate_operation_join(
        approved=approved,
        source_root=source_root,
        target_root=target_root,
        manifest=manifest,
        operation_evidence=operation_evidence,
        transaction=transaction,
    )

    source_state = _path_state(source_root)
    if source_state != "unavailable":
        raise EvidenceHarnessError("original root is still available at the restart checkpoint")
    destination_identity = physical_root_identity(target_root)
    execution_root = _approved_execution_root(approved)
    git_identity = _capture_git_identity(
        request.expected_git_commit,
        request.git_paths,
        execution_root=execution_root,
    )
    checked_execution_root = Path(git_identity["execution_root"])
    restart = _fresh_process_binding_load(
        binding_path=request.binding_path,
        code_root=checked_execution_root,
        expected=approved,
    )

    runtime_result, locked_revalidation, rejection, conflicting_retry = _capture_runtime_evidence(
        runtime=runtime,
        transaction=transaction,
        transaction_record=transaction_snapshot.record,
        target_root=target_root,
        manifest_path=manifest_path,
        evidence_path=evidence_path,
        transaction_path=transaction_path,
        operation_evidence=operation_evidence,
        witness=witness,
        witness_path=witness_path,
        approved=approved,
    )
    exact_retry = _capture_exact_retry(transaction_path, transaction, runtime_result)
    rollback_recovery = _capture_rollback_recovery(
        target_root=target_root,
        witness=witness,
        witness_path=witness_path,
        transaction=transaction,
        transaction_record=transaction_snapshot.record,
        source_root=source_root,
    )

    bound_artifact_paths = _bound_artifact_paths(
        target_root,
        runtime,
        target_root / Path(str(operation_evidence["output_object_path"])),
    )
    bound_artifact_records = tuple(_file_record(path, "bound_artifact") for path in bound_artifact_paths)
    produced_files = _unique_file_records(
        (
            foundation_record,
            _file_record(request.binding_path, "binding_config"),
            witness_snapshot.record,
            manifest_snapshot.record,
            evidence_snapshot.record,
            transaction_snapshot.record,
            runtime.bundle_record,
            runtime.receipt_record,
            runtime.registry_record,
            runtime.snapshot_record,
            runtime.endpoint_record,
            runtime.artefact_manifest_record,
            *bound_artifact_records,
        )
    )
    _revalidate_publication_inputs(
        produced_files,
        source_root=source_root,
        output_root=output_root,
        protected_roots=(*approved.code_roots, target_root, origin_root),
    )

    candidate_without_id: dict[str, Any] = {
        "schema_id": _SCHEMA_ID,
        "schema_version": "1.0.0",
        "workflow_system": "standalone",
        "lifecycle_phase": "WP6.4",
        "proof_scope": "real_external_store_moved_store",
        "candidate_lifecycle": {
            "candidate_status": "produced_unreviewed",
            "a8_status": "open",
            "independent_review": "pending",
            "owner_acceptance": "pending",
            "dispatch_claim": "none",
            "research_claim": "none",
        },
        "foundation": {
            "file": foundation_record,
            "project_id": approved.project_id,
            "store_identity": approved.store_identity,
            "control_root": str(target_root),
            "origin_authority_root": str(origin_root),
            "origin_witness_path": str(witness_path),
            "origin_witness_slot": witness.slot,
            "origin_witness_sha256": witness.raw_sha256,
            "foundation_sha256": approved.foundation_sha256,
        },
        "external_operation": {
            "operation_status": "moved_store_verified",
            "source_root": str(source_root),
            "source_root_state_at_restart": source_state,
            "source_physical_identity": dict(witness.initial_physical_root_identity),
            "destination_root": str(target_root),
            "destination_physical_identity": destination_identity,
            "destination_manifest": manifest_snapshot.record,
            "operation_evidence": evidence_snapshot.record,
            "transaction": transaction_snapshot.record,
            "transaction_id": transaction["transaction_id"],
            "final_transaction_generation": transaction["generation"],
            "source_lineage": {
                "source_root": operation_evidence["source_root"],
                "source_root_identity": dict(operation_evidence["source_root_identity"]),
                "origin_witness_path": operation_evidence["origin_witness_path"],
                "origin_witness_sha256": operation_evidence["origin_witness_sha256"],
            },
        },
        "restart": restart | {"original_root_state": source_state},
        "admission": {
            "pre_writer": runtime_result["pre_writer"],
            "locked_revalidation": locked_revalidation,
            "runtime_inputs_file": runtime.bundle_record,
        },
        "registry": {
            "file": runtime.registry_record,
            "raw_sha256": runtime.registry_record["raw_sha256"],
        },
        "bound_artifacts": [{"file": record, "raw_sha256": record["raw_sha256"]} for record in bound_artifact_records],
        "retry_recovery": {
            "transaction_generations": _transaction_generations(transaction),
            "exact_retry": exact_retry,
            "conflicting_retry": conflicting_retry,
            "rollback_recovery": rollback_recovery,
            "runtime_inputs_file": runtime.bundle_record,
        },
        "rejected_admission": rejection,
        "git": git_identity,
        "environment": _environment(),
        "produced_files": list(produced_files),
    }
    _revalidate_publication_inputs(
        produced_files,
        source_root=source_root,
        output_root=output_root,
        protected_roots=(*approved.code_roots, target_root, origin_root),
    )
    candidate = dict(candidate_without_id)
    candidate["candidate_id"] = _candidate_id(candidate_without_id)
    validate_real_a8_candidate(candidate)
    raw = canonical_bytes(candidate)
    path, raw_sha256, blob_sha1 = ContentAddressedEvidenceStore(
        output_root,
        forbidden_physical_root_identity=witness.initial_physical_root_identity,
        forbidden_physical_roots=(*approved.code_roots, target_root, origin_root),
    ).write_once(
        candidate["candidate_id"],
        raw,
    )
    return CandidateCapture(candidate, path, raw_sha256, blob_sha1)


def validate_real_a8_candidate(candidate: Mapping[str, Any]) -> None:
    """Validate schema, candidate preimage, immutable file records, and joins."""

    if not isinstance(candidate, Mapping):
        raise EvidenceHarnessError("A8 candidate must be an object")
    schema_path = (
        Path(__file__).resolve().parents[2]
        / ".research-system"
        / "schemas"
        / "wp6-4"
        / "real-a8-proof-candidate.schema.json"
    )
    try:
        schema_snapshot = _read_json_snapshot(schema_path, "real-A8 candidate schema")
        schema = schema_snapshot.value
    except EvidenceHarnessError:
        raise
    if not isinstance(schema, dict):
        raise EvidenceHarnessError("real-A8 candidate schema is unavailable")
    errors = sorted(Draft202012Validator(schema).iter_errors(dict(candidate)), key=lambda item: list(item.path))
    if errors:
        location = "/".join(str(item) for item in errors[0].path) or "$"
        raise EvidenceHarnessError(f"real-A8 candidate schema violation at {location}: {errors[0].message}")
    lifecycle = candidate["candidate_lifecycle"]
    if lifecycle != {
        "candidate_status": "produced_unreviewed",
        "a8_status": "open",
        "independent_review": "pending",
        "owner_acceptance": "pending",
        "dispatch_claim": "none",
        "research_claim": "none",
    }:
        raise EvidenceHarnessError("real-A8 candidate lifecycle is not fail-closed")
    without_id = dict(candidate)
    supplied_id = without_id.pop("candidate_id")
    expected_id = _candidate_id(without_id)
    if supplied_id != expected_id:
        raise EvidenceHarnessError("candidate_id does not match canonical candidate bytes")
    _validate_candidate_joins(candidate)


def governed_repository_paths(repo_root: Path | None = None) -> tuple[str, ...]:
    """Enumerate the loaded repository Python dependencies plus governed schemas."""

    root = (repo_root or Path(__file__).resolve().parents[2]).resolve(strict=True)
    paths = {
        ".research-system/schemas/wp6-4/real-a8-proof-candidate.schema.json",
        ".research-system/schemas/evals/evidence-store-registry.schema.json",
    }
    research_root = root / "research_system"
    for module in tuple(sys.modules.values()):
        module_path = getattr(module, "__file__", None)
        if not module_path:
            continue
        path = Path(module_path)
        if path.suffix == ".pyc":
            path = path.with_suffix("").with_suffix(".py")
        try:
            relative = path.resolve(strict=False).relative_to(research_root)
        except ValueError:
            continue
        if path.suffix == ".py":
            paths.add((Path("research_system") / relative).as_posix())
    module_path = Path(__file__).resolve(strict=True).relative_to(root)
    paths.add(module_path.as_posix())
    return tuple(sorted(paths))


def _load_approved_foundation(path: Path) -> tuple[ApprovedProjectBinding, dict[str, Any]]:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise EvidenceHarnessError("canonical foundation path must be absolute")
    expected = canonical_foundation_path().resolve(strict=False)
    resolved = candidate.resolve(strict=False)
    if resolved != expected:
        raise EvidenceHarnessError("foundation path is not the canonical materialized foundation")
    snapshot = _read_physical_file_snapshot(resolved, "foundation")
    try:
        approved = ApprovedProjectBinding.from_raw(snapshot.raw)
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("owner-materialized canonical foundation is required") from exc
    _revalidate_file_snapshot(resolved, snapshot, "foundation")
    return approved, snapshot.record


def _load_canonical_binding(path: Path, approved: ApprovedProjectBinding) -> ControlBinding:
    binding_path = Path(path)
    before = _read_physical_file_snapshot(binding_path, "ControlBinding")
    try:
        binding = ControlBinding.from_raw(before.raw, approved=approved)
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("canonical ControlBinding could not be loaded") from exc
    _revalidate_file_snapshot(binding_path, before, "ControlBinding")
    if binding.control_root != approved.control_root or binding.project_id != approved.project_id:
        raise EvidenceHarnessError("ControlBinding identity differs from foundation")
    if binding.store_identity != approved.store_identity:
        raise EvidenceHarnessError("ControlBinding store identity differs from foundation")
    return binding


def _validate_root_relationships(
    approved: ApprovedProjectBinding,
    source_root: Path,
    target_root: Path,
    origin_root: Path,
    output_root: Path,
) -> None:
    for label, path in (
        ("source root", source_root),
        ("destination root", target_root),
        ("origin authority root", origin_root),
        ("output root", Path(output_root)),
    ):
        if not path.is_absolute():
            raise EvidenceHarnessError(f"{label} must be absolute")
    if source_root == target_root:
        raise EvidenceHarnessError("source and destination roots must differ")
    _require_lexically_disjoint(source_root, target_root, "source and destination roots must be disjoint")
    _require_lexically_disjoint(source_root, output_root, "source and output roots must be disjoint")
    _require_lexically_disjoint(source_root, origin_root, "source root overlaps origin authority root")
    _require_lexically_disjoint(target_root, origin_root, "destination root overlaps origin authority root")
    _require_lexically_disjoint(output_root, origin_root, "output root overlaps origin authority root")
    if not approved.code_roots:
        raise EvidenceHarnessError("foundation code roots are required")
    for root in approved.code_roots:
        _require_lexically_disjoint(root, source_root, "source root overlaps an approved code root")
        _require_lexically_disjoint(root, target_root, "destination root overlaps an approved code root")
        _require_lexically_disjoint(root, output_root, "output root overlaps an approved code root")
    _require_physical_root_disjoint_if_available(source_root, output_root, "source and output roots are aliases")


def _validate_output_root(
    path: Path,
    *,
    source_root: Path,
    code_roots: Sequence[Path],
    target_root: Path,
    origin_root: Path,
) -> Path:
    output = Path(path)
    if not output.is_absolute():
        raise EvidenceHarnessError("candidate output root must be absolute")
    _require_lexically_disjoint(output, source_root, "source and output roots must be disjoint")
    for root in (*code_roots, target_root, origin_root):
        _require_lexically_disjoint(output, Path(root), "candidate output root overlaps a protected root")
    if output.exists():
        _validate_no_follow_directory(output, "candidate output root")
        for root in (*code_roots, target_root, origin_root):
            _require_physical_root_disjoint_if_available(
                output,
                Path(root),
                "candidate output root is a physical alias of a protected root",
            )
    return output


def _load_store_manifest(target_root: Path, approved: ApprovedProjectBinding) -> dict[str, Any]:
    try:
        value = load_store_manifest(
            target_root,
            approved_witness=approved.origin_witness,
            approved_witness_path=approved.origin_witness_path,
        )
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("destination store manifest is not bound to the foundation") from exc
    if value.get("project_id") != approved.project_id or value.get("store_identity") != approved.store_identity:
        raise EvidenceHarnessError("destination store/project join is invalid")
    if value.get("control_root") != str(target_root):
        raise EvidenceHarnessError("destination store root join is invalid")
    return value


def _validate_operation_join(
    *,
    approved: ApprovedProjectBinding,
    source_root: Path,
    target_root: Path,
    manifest: Mapping[str, Any],
    operation_evidence: Mapping[str, Any],
    transaction: Mapping[str, Any],
) -> None:
    if operation_evidence.get("source_root") != str(source_root):
        raise EvidenceHarnessError("operation source root differs from origin witness")
    if operation_evidence.get("target_root") != str(target_root):
        raise EvidenceHarnessError("operation destination root differs from foundation")
    if operation_evidence.get("project_id") != approved.project_id:
        raise EvidenceHarnessError("operation project join is invalid")
    if operation_evidence.get("store_identity") != approved.store_identity:
        raise EvidenceHarnessError("operation store join is invalid")
    if operation_evidence.get("manifest_hash") != manifest.get("manifest_hash"):
        raise EvidenceHarnessError("operation manifest join is invalid")
    if operation_evidence.get("origin_witness_path") != str(approved.origin_witness_path):
        raise EvidenceHarnessError("operation witness path join is invalid")
    if operation_evidence.get("origin_witness_sha256") != approved.origin_witness_sha256:
        raise EvidenceHarnessError("operation witness digest join is invalid")
    if operation_evidence.get("source_root_identity") != approved.origin_witness.initial_physical_root_identity:
        raise EvidenceHarnessError("operation source physical identity join is invalid")
    if operation_evidence.get("operation_status") != "bound-and-config-published":
        raise EvidenceHarnessError("operation is not a completed moved-store bind")
    if operation_evidence.get("durability_status") != "durable":
        raise EvidenceHarnessError("operation durability evidence is missing")
    for field, expected in (
        ("source_root", str(source_root)),
        ("target_root", str(target_root)),
        ("project_id", approved.project_id),
        ("store_identity", approved.store_identity),
        ("origin_witness_path", str(approved.origin_witness_path)),
        ("origin_witness_sha256", approved.origin_witness_sha256),
        ("origin_initial_control_root", str(source_root)),
    ):
        if transaction.get(field) != expected:
            raise EvidenceHarnessError(f"restore transaction join is invalid: {field}")
    if transaction.get("source_root_identity") != approved.origin_witness.initial_physical_root_identity:
        raise EvidenceHarnessError("restore transaction source physical identity is invalid")
    if transaction.get("target_root_identity") != physical_root_identity(target_root):
        raise EvidenceHarnessError("restore transaction destination physical identity is stale")
    if transaction.get("state") != "cleared" or transaction.get("last_completed_durability_step") != "clear-durable":
        raise EvidenceHarnessError("restore transaction has not completed recovery")
    if not isinstance(transaction.get("generation"), int) or transaction["generation"] != len(_TRANSACTION_STEPS) - 1:
        raise EvidenceHarnessError("restore transaction final generation is not exact")


def _load_runtime_inputs(path: Path) -> _RuntimeInputs:
    value, bundle_snapshot = _load_canonical_evidence(path, _RUNTIME_INPUTS_SCHEMA_ID)
    required = {
        "schema_id",
        "schema_version",
        "receipt_path",
        "registry_path",
        "snapshot_path",
        "endpoint_ownership_path",
        "artefact_manifest_path",
        "admission_bundle",
    }
    if set(value) != required or value["schema_version"] != _RUNTIME_INPUTS_SCHEMA_VERSION:
        raise EvidenceHarnessError("canonical runtime-input bundle fields are incomplete")
    receipt_path = _absolute_evidence_path(value["receipt_path"], "runtime receipt path")
    registry_path = _absolute_evidence_path(value["registry_path"], "runtime registry path")
    snapshot_path = _absolute_evidence_path(value["snapshot_path"], "runtime snapshot path")
    endpoint_path = _absolute_evidence_path(value["endpoint_ownership_path"], "runtime endpoint path")
    artefact_manifest_path = _absolute_evidence_path(value["artefact_manifest_path"], "runtime artefact manifest path")
    admission_bundle = _restore_admission_bundle_from_json(value["admission_bundle"])
    receipt_snapshot = _read_canonical_snapshot(receipt_path, "runtime backup receipt")
    registry_snapshot = _read_canonical_snapshot(registry_path, "runtime evidence registry")
    snapshot_record = _read_canonical_snapshot(snapshot_path, "runtime accepted snapshot")
    endpoint_snapshot = _read_canonical_snapshot(endpoint_path, "runtime endpoint ownership")
    artefact_manifest_snapshot = _read_canonical_snapshot(artefact_manifest_path, "runtime artefact manifest")
    receipt = _backup_receipt_from_json(receipt_snapshot.value or {})
    registry = _evidence_registry_from_json(registry_snapshot.value or {})
    endpoint = endpoint_snapshot.value or {}
    if set(endpoint) != {"target_root", "endpoint_scheme", "owner_actor_id", "authority_grant_id", "observed_at"}:
        raise EvidenceHarnessError("runtime endpoint ownership is not canonical")
    actor_id = endpoint.get("owner_actor_id")
    authority_grant_id = endpoint.get("authority_grant_id")
    if (
        not isinstance(actor_id, str)
        or not actor_id
        or not isinstance(authority_grant_id, str)
        or not authority_grant_id
    ):
        raise EvidenceHarnessError("runtime endpoint authority is incomplete")
    if receipt.verified_by_actor_id != actor_id or receipt.verification_authority_grant_id != authority_grant_id:
        raise EvidenceHarnessError("runtime receipt and endpoint authority differ")
    if (actor_id, authority_grant_id) not in registry.verifier_authority_bindings:
        raise EvidenceHarnessError("runtime registry and endpoint authority differ")
    return _RuntimeInputs(
        bundle_record=bundle_snapshot,
        receipt_record=receipt_snapshot.record,
        registry_record=registry_snapshot.record,
        snapshot_record=snapshot_record.record,
        endpoint_record=endpoint_snapshot.record,
        artefact_manifest_record=artefact_manifest_snapshot.record,
        receipt=receipt,
        registry=registry,
        snapshot_path=snapshot_path,
        endpoint_ownership_path=endpoint_path,
        artefact_manifest_path=artefact_manifest_path,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        admission_bundle=admission_bundle,
    )


def _backup_receipt_from_json(value: Mapping[str, Any]) -> BackupReceipt:
    expected = {field.name for field in fields(BackupReceipt)}
    if set(value) != expected:
        raise EvidenceHarnessError("runtime backup receipt fields are incomplete")
    payload = dict(value)
    try:
        payload["schema_versions"] = tuple(payload["schema_versions"])
        payload["tool_versions"] = tuple(payload["tool_versions"])
        payload["artefact_bindings"] = tuple(ArtefactBinding(**item) for item in payload["artefact_bindings"])
        receipt = BackupReceipt(**payload)
        if seal_backup_receipt(receipt) != receipt:
            raise EvidenceHarnessError("runtime backup receipt seal does not match its canonical payload")
        return receipt
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceHarnessError("runtime backup receipt is invalid") from exc


def _evidence_registry_from_json(value: Mapping[str, Any]) -> EvidenceStoreRegistry:
    required = {
        "schema_id",
        "schema_version",
        "store_id",
        "registry_hash",
        "policy_revision",
        "primary_root",
        "runtime_root",
        "staging_root",
        "temp_root",
        "replicas",
        "backup_roots",
        "restore_roots",
        "permitted_consumers",
        "retention_policy_ids",
        "verifier_authority_bindings",
        "unregistered_replicas_prohibited",
    }
    if (
        set(value) != required
        or value["schema_id"] != "ars://evals/evidence-store-registry"
        or value["schema_version"] != "1.0.0"
    ):
        raise EvidenceHarnessError("runtime evidence registry fields are incomplete")
    try:
        bundled_runtime_schema_registry().validate("ars://evals/evidence-store-registry", dict(value))
        return EvidenceStoreRegistry(
            store_id=value["store_id"],
            registry_hash=value["registry_hash"],
            policy_revision=value["policy_revision"],
            primary_root=Path(value["primary_root"]),
            runtime_root=Path(value["runtime_root"]),
            staging_root=Path(value["staging_root"]),
            temp_root=Path(value["temp_root"]),
            replicas=tuple(Path(item) for item in value["replicas"]),
            backup_roots=tuple(Path(item) for item in value["backup_roots"]),
            restore_roots=tuple(Path(item) for item in value["restore_roots"]),
            permitted_consumers=tuple(value["permitted_consumers"]),
            retention_policy_ids=tuple(value["retention_policy_ids"]),
            verifier_authority_bindings=tuple(tuple(item) for item in value["verifier_authority_bindings"]),
            unregistered_replicas_prohibited=value["unregistered_replicas_prohibited"],
        )
    except (ArsError, OSError, TypeError, ValueError) as exc:
        raise EvidenceHarnessError("runtime evidence registry is invalid") from exc


def _registry_state_sha256(registry: EvidenceStoreRegistry) -> str:
    try:
        state = {field.name: _jsonable(getattr(registry, field.name)) for field in fields(registry)}
    except (AttributeError, TypeError, ValueError) as exc:
        raise EvidenceHarnessError("runtime evidence registry state is unavailable") from exc
    return sha256_hex(canonical_bytes(state))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value.resolve(strict=False))
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _restore_admission_bundle_from_json(value: Any) -> RestoreAdmissionBundle:
    if not isinstance(value, Mapping) or set(value) != {"schema_id", "schema_version", "result", "closure"}:
        raise EvidenceHarnessError("canonical runtime admission bundle fields are incomplete")
    if value["schema_id"] != _RUNTIME_ADMISSION_SCHEMA_ID or value["schema_version"] != _RUNTIME_INPUTS_SCHEMA_VERSION:
        raise EvidenceHarnessError("unsupported canonical runtime admission bundle schema")
    result_value = value["result"]
    closure_value = value["closure"]
    if not isinstance(result_value, Mapping) or not isinstance(closure_value, Mapping):
        raise EvidenceHarnessError("canonical runtime admission bundle is incomplete")
    result_fields = {field.name for field in fields(RestorePreflightResult)}
    if set(result_value) != result_fields:
        raise EvidenceHarnessError("canonical runtime preflight result fields are incomplete")
    result_payload = dict(result_value)
    try:
        result_payload["failed_predicates"] = tuple(result_payload["failed_predicates"])
        result_payload["code_roots"] = list(result_payload["code_roots"])
        result_payload["origin_initial_physical_root_identity"] = dict(
            result_payload["origin_initial_physical_root_identity"]
        )
        result = RestorePreflightResult(**result_payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceHarnessError("canonical runtime preflight result is invalid") from exc
    if set(closure_value) != {
        "target_root",
        "snapshot",
        "endpoint_ownership",
        "artefact_manifest",
        "artefacts",
        "registry",
        "registry_state_sha256",
    }:
        raise EvidenceHarnessError("canonical runtime admission closure fields are incomplete")
    try:
        closure = RestoreAdmissionClosure(
            target_root=closure_value["target_root"],
            snapshot=_restore_bound_file(closure_value["snapshot"]),
            endpoint_ownership=_restore_bound_file(closure_value["endpoint_ownership"]),
            artefact_manifest=_restore_bound_file(closure_value["artefact_manifest"]),
            artefacts=tuple(_restore_bound_artefact(item) for item in closure_value["artefacts"]),
            registry=_evidence_registry_from_json(closure_value["registry"]),
            registry_state_sha256=closure_value["registry_state_sha256"],
        )
    except (KeyError, TypeError, ValueError, EvidenceHarnessError) as exc:
        raise EvidenceHarnessError("canonical runtime admission closure is invalid") from exc
    if closure.registry_state_sha256 != _registry_state_sha256(closure.registry):
        raise EvidenceHarnessError("canonical runtime admission registry state hash is invalid")
    return RestoreAdmissionBundle(result=result, closure=closure)


def _restore_bound_file(value: Any) -> RestoreBoundFile:
    if not isinstance(value, Mapping) or set(value) != {"relative_path", "raw_sha256", "canonical_sha256"}:
        raise EvidenceHarnessError("canonical runtime bound-file fields are incomplete")
    return RestoreBoundFile(**dict(value))


def _restore_bound_artefact(value: Any) -> RestoreBoundArtefact:
    if not isinstance(value, Mapping) or set(value) != {
        "artefact_id",
        "relative_path",
        "artefact_sha256",
        "observation_sha256",
    }:
        raise EvidenceHarnessError("canonical runtime bound-artefact fields are incomplete")
    return RestoreBoundArtefact(**dict(value))


def _capture_runtime_evidence(
    *,
    runtime: _RuntimeInputs,
    transaction: Mapping[str, Any],
    transaction_record: Mapping[str, Any],
    target_root: Path,
    manifest_path: Path,
    evidence_path: Path,
    transaction_path: Path,
    operation_evidence: Mapping[str, Any],
    witness: Any,
    witness_path: Path,
    approved: ApprovedProjectBinding,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    bundle = runtime.admission_bundle
    if not isinstance(bundle, RestoreAdmissionBundle) or not isinstance(bundle.result, RestorePreflightResult):
        raise EvidenceHarnessError("canonical runtime pre-writer admission bundle is unavailable")
    result = bundle.result
    if bundle.closure is None:
        raise EvidenceHarnessError("canonical runtime pre-writer admission closure is unavailable")
    try:
        validate_restore_preflight_result(
            result,
            current_root=target_root,
            project_id=approved.project_id,
            actor_id=runtime.actor_id,
            authority_grant_id=runtime.authority_grant_id,
            approved_witness=witness,
        )
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("canonical runtime pre-writer admission is not valid") from exc
    if (
        result.status != "verified"
        or result.failed_predicates
        or result.result_hash != transaction.get("restore_preflight_result_hash")
        or result.receipt_hash != runtime.receipt.receipt_hash
        or result.snapshot_hash != runtime.snapshot_record["raw_sha256"]
        or result.target_endpoint_ownership_hash != runtime.endpoint_record["raw_sha256"]
        or result.artefact_manifest_hash != runtime.artefact_manifest_record["raw_sha256"]
        or result.registry_hash != runtime.registry.registry_hash
        or bundle.closure.target_root != str(target_root)
        or bundle.closure.registry != runtime.registry
        or bundle.closure.registry_state_sha256 != _registry_state_sha256(runtime.registry)
        or bundle.closure.snapshot.relative_path != _target_relative_path(target_root, runtime.snapshot_path)
        or bundle.closure.snapshot.raw_sha256 != runtime.snapshot_record["raw_sha256"]
        or bundle.closure.endpoint_ownership.relative_path
        != _target_relative_path(target_root, runtime.endpoint_ownership_path)
        or bundle.closure.endpoint_ownership.raw_sha256 != runtime.endpoint_record["raw_sha256"]
        or bundle.closure.artefact_manifest.relative_path
        != _target_relative_path(target_root, runtime.artefact_manifest_path)
        or bundle.closure.artefact_manifest.raw_sha256 != runtime.artefact_manifest_record["raw_sha256"]
    ):
        raise EvidenceHarnessError(
            "canonical runtime pre-writer admission is not bound to the cleared transaction: "
            f"result_hash={result.result_hash!r}, "
            f"transaction_hash={transaction.get('restore_preflight_result_hash')!r}, "
            f"failed_predicates={result.failed_predicates!r}"
        )
    request_identity = _request_identity(transaction, result, runtime.actor_id, runtime.authority_grant_id)
    pre_writer = {
        "status": "verified",
        "result_hash": result.result_hash,
        "receipt_hash": result.receipt_hash,
        "transaction_id": transaction["transaction_id"],
        "request_identity_sha256": request_identity,
    }
    protected_paths = _protected_surface_paths(
        target_root=target_root,
        manifest_path=manifest_path,
        evidence_path=evidence_path,
        transaction_path=transaction_path,
        operation_evidence=operation_evidence,
        runtime=runtime,
        result=result,
    )
    lock_identity = {
        "transaction_id": str(transaction["transaction_id"]),
        "purpose": "wp64-real-a8-locked-revalidation",
    }
    try:
        with CompositeWriterLock((target_root,), lock_identity) as lease:
            before = _capture_surface(protected_paths)
            revalidate_restore_admission_closure(bundle)
            after = _capture_surface(protected_paths)
            _assert_surface_unchanged(before, after, "locked revalidation")
            if len(lease.paths) != 1:
                raise EvidenceHarnessError("locked revalidation did not expose one writer lock")
            lock_record = _read_canonical_json(lease.paths[0], "writer lock identity")
            surface_before_hash = _surface_hash(before)
            surface_after_hash = _surface_hash(after)
            revalidation_hash = sha256_hex(
                canonical_bytes(
                    {
                        "result_hash": result.result_hash,
                        "transaction_sha256": transaction_record["raw_sha256"],
                        "lock_identity": lock_record,
                        "surface_before_sha256": surface_before_hash,
                        "surface_after_sha256": surface_after_hash,
                    }
                )
            )
            rejected = _run_rejected_probe(
                runtime=runtime,
                target_root=target_root,
                witness=witness,
                witness_path=witness_path,
                protected_paths=protected_paths,
                expected_transaction_id=str(transaction["transaction_id"]),
            )
            conflicting = _run_conflicting_retry_probe(
                runtime=runtime,
                target_root=target_root,
                witness=witness,
                witness_path=witness_path,
                protected_paths=protected_paths,
                expected_transaction_id=str(transaction["transaction_id"]),
            )
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("locked runtime admission revalidation could not be captured") from exc
    locked = {
        "status": "verified",
        "result_hash": result.result_hash,
        "transaction_id": transaction["transaction_id"],
        "lock_identity": lock_record,
        "surface_before_sha256": surface_before_hash,
        "surface_after_sha256": surface_after_hash,
        "revalidation_sha256": revalidation_hash,
    }
    return {"pre_writer": pre_writer}, locked, rejected, conflicting


def _run_rejected_probe(
    *,
    runtime: _RuntimeInputs,
    target_root: Path,
    witness: Any,
    witness_path: Path,
    protected_paths: Sequence[Path],
    expected_transaction_id: str,
) -> dict[str, Any]:
    probe_actor = "rejected-probe-" + sha256_hex(runtime.actor_id.encode("utf-8"))[:24]
    before = _capture_surface(protected_paths)
    try:
        result = verify_restore_before_writer_lease(
            target_root=target_root,
            receipt=runtime.receipt,
            snapshot_path=runtime.snapshot_path,
            endpoint_ownership_path=runtime.endpoint_ownership_path,
            artefact_manifest_path=runtime.artefact_manifest_path,
            registry=runtime.registry,
            actor_id=probe_actor,
            authority_grant_id=runtime.authority_grant_id,
            approved_witness=witness,
            approved_witness_path=witness_path,
        )
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("rejected-admission public probe could not be executed") from exc
    after = _capture_surface(protected_paths)
    _assert_surface_unchanged(before, after, "rejected admission")
    if (
        not isinstance(result, RestorePreflightResult)
        or result.status != "diagnostic_only"
        or not result.failed_predicates
    ):
        raise EvidenceHarnessError("rejected-admission public probe did not reject")
    return {
        "result_hash": result.result_hash,
        "status": result.status,
        "failed_predicates": list(result.failed_predicates),
        "transaction_id": expected_transaction_id,
        "probe_actor_id": probe_actor,
        "surface_before_sha256": _surface_hash(before),
        "surface_after_sha256": _surface_hash(after),
        "snapshots": _surface_snapshots(before, after),
        "mutation_result": "no_mutation",
    }


def _run_conflicting_retry_probe(
    *,
    runtime: _RuntimeInputs,
    target_root: Path,
    witness: Any,
    witness_path: Path,
    protected_paths: Sequence[Path],
    expected_transaction_id: str,
) -> dict[str, Any]:
    bad_grant = "conflicting-retry-" + sha256_hex(runtime.authority_grant_id.encode("utf-8"))[:24]
    before = _capture_surface(protected_paths)
    try:
        result = verify_restore_before_writer_lease(
            target_root=target_root,
            receipt=runtime.receipt,
            snapshot_path=runtime.snapshot_path,
            endpoint_ownership_path=runtime.endpoint_ownership_path,
            artefact_manifest_path=runtime.artefact_manifest_path,
            registry=runtime.registry,
            actor_id=runtime.actor_id,
            authority_grant_id=bad_grant,
            approved_witness=witness,
            approved_witness_path=witness_path,
        )
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("conflicting retry public probe could not be executed") from exc
    after = _capture_surface(protected_paths)
    _assert_surface_unchanged(before, after, "conflicting retry")
    if (
        not isinstance(result, RestorePreflightResult)
        or result.status != "diagnostic_only"
        or not result.failed_predicates
    ):
        raise EvidenceHarnessError("conflicting retry public probe did not reject")
    return {
        "result_hash": result.result_hash,
        "transaction_id": expected_transaction_id,
        "failed_predicates": list(result.failed_predicates),
        "surface_before_sha256": _surface_hash(before),
        "surface_after_sha256": _surface_hash(after),
        "snapshots": _surface_snapshots(before, after),
        "mutation_result": "no_mutation",
    }


def _capture_exact_retry(
    transaction_path: Path,
    transaction: Mapping[str, Any],
    result_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    before = _file_record(transaction_path, "restore_transaction")
    first = load_restore_binding_transaction(transaction_path.parent.parent)
    second = load_restore_binding_transaction(transaction_path.parent.parent)
    after = _file_record(transaction_path, "restore_transaction")
    if first != second or first != dict(transaction) or before["raw_sha256"] != after["raw_sha256"]:
        raise EvidenceHarnessError("exact retry did not converge to one transaction record")
    return {
        "before_generation": transaction["generation"],
        "after_generation": transaction["generation"],
        "before_transaction_sha256": before["raw_sha256"],
        "after_transaction_sha256": after["raw_sha256"],
        "request_identity_sha256": result_bundle["pre_writer"]["request_identity_sha256"],
        "result": "converged",
    }


def _capture_rollback_recovery(
    *,
    target_root: Path,
    witness: Any,
    witness_path: Path,
    transaction: Mapping[str, Any],
    transaction_record: Mapping[str, Any],
    source_root: Path,
) -> dict[str, Any]:
    try:
        verify_restore_binding_admission(
            target_root,
            approved_witness=witness,
            approved_witness_path=witness_path,
        )
    except (ArsError, OSError, ValueError, TypeError) as exc:
        raise EvidenceHarnessError("cleared restore recovery could not be verified") from exc
    lineage_hash = sha256_hex(
        canonical_bytes(
            {
                "source_root": str(source_root),
                "source_root_identity": dict(witness.initial_physical_root_identity),
                "origin_witness_sha256": witness.raw_sha256,
            }
        )
    )
    return {
        "recovered_state": "cleared",
        "transaction_generation": transaction["generation"],
        "transaction_sha256": transaction_record["raw_sha256"],
        "source_lineage_sha256": lineage_hash,
    }


def _transaction_generations(transaction: Mapping[str, Any]) -> list[dict[str, Any]]:
    if transaction.get("generation") != len(_TRANSACTION_STEPS) - 1 or transaction.get("state") != "cleared":
        raise EvidenceHarnessError("transaction generation sequence is not complete")
    return [
        {"generation": index, "state": state, "durability_step": step}
        for index, (state, step) in enumerate(zip(_TRANSACTION_STATE_BY_STEP, _TRANSACTION_STEPS, strict=True))
    ]


def _target_relative_path(target_root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(target_root.resolve(strict=False)).as_posix()
    except ValueError as exc:
        raise EvidenceHarnessError("runtime admission input escapes the destination root") from exc


def _bound_artifact_paths(
    target_root: Path,
    runtime: _RuntimeInputs,
    output_object_path: Path,
) -> tuple[Path, ...]:
    manifest = _read_canonical_json(runtime.artefact_manifest_path, "runtime artefact manifest")
    paths: list[Path] = []
    for row in manifest.get("artefacts", []):
        relative = row.get("relative_path") if isinstance(row, dict) else None
        if isinstance(relative, str) and relative:
            paths.append(target_root / Path(relative))
    paths.append(output_object_path)
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = str(path.resolve(strict=False))
        if resolved not in seen:
            seen.add(resolved)
            result.append(path)
    return tuple(result)


def _fresh_process_binding_load(
    *, binding_path: Path, code_root: Path, expected: ApprovedProjectBinding
) -> dict[str, Any]:
    code = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(sys.argv[2]).resolve(strict=True)))\n"
        "from research_system.config import ControlBinding\n"
        "binding = ControlBinding.load(Path(sys.argv[1]))\n"
        "print(json.dumps({'control_root': str(binding.control_root), 'project_id': binding.project_id, "
        "'store_identity': binding.store_identity}, sort_keys=True, separators=(',', ':')))\n"
    )
    try:
        interpreter = Path(sys.executable).resolve(strict=True)
        if not interpreter.is_file():
            raise EvidenceHarnessError("fresh-process interpreter is not a physical file")
        resolved_code_root = code_root.resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="wp64-a8-pycache-") as pycache_root:
            result = subprocess.run(  # nosemgrep: dangerous-subprocess-use-audit  # nosec B603
                [
                    str(interpreter),
                    "-I",
                    "-B",
                    "-X",
                    f"pycache_prefix={pycache_root}",
                    "-c",
                    code,
                    str(Path(binding_path).resolve(strict=True)),
                    str(resolved_code_root),
                ],
                cwd=str(resolved_code_root),
                capture_output=True,
                check=False,
            )
    except OSError as exc:
        raise EvidenceHarnessError("fresh-process ControlBinding probe could not start") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip().replace("\r", " ").replace("\n", " ")
        raise EvidenceHarnessError(f"fresh-process ControlBinding load failed: {detail[-400:]}")
    try:
        value = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceHarnessError("fresh-process ControlBinding output is invalid") from exc
    if value != {
        "control_root": str(expected.control_root),
        "project_id": expected.project_id,
        "store_identity": expected.store_identity,
    }:
        raise EvidenceHarnessError("fresh-process ControlBinding identity differs from foundation")
    return {
        "process": "fresh",
        "exit_code": result.returncode,
        "binding_load": "successful",
        "control_root": value["control_root"],
        "project_id": value["project_id"],
        "store_identity": value["store_identity"],
        "stdout_sha256": sha256_hex(result.stdout),
        "stderr_sha256": sha256_hex(result.stderr),
        "interpreter": str(Path(sys.executable).resolve(strict=False)),
    }


def _capture_git_identity(
    expected_commit: str,
    paths: Sequence[str],
    *,
    execution_root: Path | None = None,
) -> dict[str, Any]:
    if not _COMMIT.fullmatch(expected_commit):
        raise EvidenceHarnessError("exact Git subject must be a full commit SHA")
    repo_root = Path(__file__).resolve().parents[2]
    execution_candidate = repo_root if execution_root is None else Path(execution_root)
    if not execution_candidate.is_absolute():
        raise EvidenceHarnessError("execution root must be an absolute approved code root")
    try:
        checked_execution_root = execution_candidate.resolve(strict=True)
    except OSError as exc:
        raise EvidenceHarnessError("execution root is unavailable") from exc
    if not checked_execution_root.is_dir():
        raise EvidenceHarnessError("execution root must be a physical directory")
    _validate_no_follow_directory(checked_execution_root, "execution root")
    expected_paths = governed_repository_paths(repo_root)
    supplied_paths = tuple(paths)
    if supplied_paths != expected_paths or len(set(supplied_paths)) != len(supplied_paths):
        raise EvidenceHarnessError("Git identity must contain the complete governed path set exactly once")
    commit = _git(repo_root, "rev-parse", "HEAD")
    if commit != expected_commit:
        raise EvidenceHarnessError("exact Git subject differs from HEAD")
    parent_line = _git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    path_records: list[dict[str, Any]] = []
    for raw_path in supplied_paths:
        if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute() or "\\" in raw_path:
            raise EvidenceHarnessError("Git identity path must be a non-empty relative POSIX path")
        if any(part in {"", ".", ".."} for part in Path(raw_path).parts):
            raise EvidenceHarnessError("Git identity path is not canonical")
        rows = _git(repo_root, "ls-tree", "-r", "--full-tree", "HEAD", "--", raw_path).splitlines()
        matches = [row.split("\t", 1) for row in rows if row]
        if len(matches) != 1 or len(matches[0]) != 2:
            raise EvidenceHarnessError(f"Git identity path is not exactly tracked at HEAD: {raw_path}")
        left, path_value = matches[0]
        fields_value = left.split()
        if len(fields_value) != 3:
            raise EvidenceHarnessError(f"Git identity tree row is invalid: {raw_path}")
        mode, object_type, blob = fields_value
        if object_type != "blob" or not _SHA1.fullmatch(blob) or path_value != raw_path:
            raise EvidenceHarnessError(f"Git identity blob is invalid: {raw_path}")
        working = _read_physical_file_snapshot(repo_root / Path(raw_path), f"governed Git path {raw_path}")
        committed = _git_bytes(repo_root, "show", f"HEAD:{raw_path}")
        if working.raw != committed or working.record["git_blob_sha1"] != blob:
            raise EvidenceHarnessError(f"governed Git path bytes differ from HEAD: {raw_path}")
        executed = _read_physical_file_snapshot(
            checked_execution_root / Path(raw_path),
            f"governed execution path {raw_path}",
        )
        if executed.raw != committed or executed.record["git_blob_sha1"] != blob:
            raise EvidenceHarnessError(f"execution root bytes differ from Git HEAD: {raw_path}")
        path_records.append({"path": raw_path, "mode": mode, "blob_sha1": blob})
    path_set_hash = sha256_hex(canonical_bytes(list(supplied_paths)))
    return {
        "repository_root": str(repo_root),
        "execution_root": str(checked_execution_root),
        "commit": commit,
        "parent_commits": parent_line[1:],
        "tree": tree,
        "subject_resolution": "exact_head_match",
        "paths": path_records,
        "path_set_sha256": path_set_hash,
        "working_bytes_match_head": True,
        "execution_bytes_match_head": True,
    }


def _approved_execution_root(approved: ApprovedProjectBinding) -> Path:
    try:
        execution_root = canonical_foundation_path().parents[2].resolve(strict=True)
    except (IndexError, OSError) as exc:
        raise EvidenceHarnessError("executing repository root is unavailable") from exc
    if execution_root not in approved.code_roots:
        raise EvidenceHarnessError("executing repository root is not an approved code root")
    return execution_root


def _git(repo_root: Path, *args: str) -> str:
    return _git_bytes(repo_root, *args).decode("utf-8").strip()


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    try:
        git_executable = shutil.which("git")
        if git_executable is None:
            raise EvidenceHarnessError("Git executable is unavailable")
        resolved_git = Path(git_executable).resolve(strict=True)
        if not resolved_git.is_file():
            raise EvidenceHarnessError("Git executable is not a physical file")
        result = subprocess.run(  # nosemgrep: dangerous-subprocess-use-audit  # nosec B603
            [str(resolved_git), "-C", str(repo_root), *args],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceHarnessError("exact Git identity could not be captured") from exc
    return result.stdout


def _environment() -> dict[str, str]:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "interpreter": str(Path(sys.executable).resolve(strict=False)),
        "platform_system": platform.system(),
        "platform_release": platform.release() or "unavailable",
        "platform_machine": platform.machine() or "unavailable",
        "cwd": str(Path.cwd().resolve(strict=False)),
    }


def _load_canonical_evidence(path: Path, schema_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = _read_canonical_snapshot(path, "operator runtime evidence")
    value = snapshot.value
    if value is None or value.get("schema_id") != schema_id or value.get("schema_version") != "1.0.0":
        raise EvidenceHarnessError(f"unsupported operator evidence schema: {schema_id}")
    return value, snapshot.record


def _read_canonical_json(path: Path, label: str) -> dict[str, Any]:
    snapshot = _read_canonical_snapshot(path, label)
    if snapshot.value is None:
        raise EvidenceHarnessError(f"{label} is not a JSON object")
    return snapshot.value


def _read_canonical_snapshot(path: Path, label: str) -> _PhysicalFileSnapshot:
    snapshot = _read_physical_file_snapshot(path, label)
    value = _parse_canonical_json(snapshot.raw, label)
    return _PhysicalFileSnapshot(snapshot.path, snapshot.raw, snapshot.record, value)


def _read_json_snapshot(path: Path, label: str) -> _PhysicalFileSnapshot:
    snapshot = _read_physical_file_snapshot(path, label)
    try:
        value = json.loads(snapshot.raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceHarnessError(f"{label} is unavailable or invalid") from exc
    if not isinstance(value, dict):
        raise EvidenceHarnessError(f"{label} is not an object")
    return _PhysicalFileSnapshot(snapshot.path, snapshot.raw, snapshot.record, value)


def _parse_canonical_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceHarnessError(f"{label} is unavailable or invalid") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise EvidenceHarnessError(f"{label} is not canonical JSON")
    return value


def _absolute_evidence_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise EvidenceHarnessError(f"{label} is required")
    path = Path(value)
    if not path.is_absolute():
        raise EvidenceHarnessError(f"{label} must be absolute")
    return path


def _file_record(path: Path, role: str) -> dict[str, Any]:
    return _read_physical_file_snapshot(path, role).record


def _read_physical_file_snapshot(path: Path, role: str) -> _PhysicalFileSnapshot:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise EvidenceHarnessError(f"{role} path must be absolute")
    absolute = Path(os.path.abspath(str(candidate)))
    _validate_no_follow_file(absolute, role)
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(str(absolute), flags)
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except (OSError, FileNotFoundError) as exc:
        raise EvidenceHarnessError(f"{role} file is unavailable") from exc
    finally:
        if descriptor != -1:
            os.close(descriptor)
    before_identity = _file_physical_identity(before)
    after_identity = _file_physical_identity(after)
    if before_identity != after_identity:
        raise EvidenceHarnessError(f"{role} changed during one physical snapshot read")
    try:
        current = absolute.lstat()
    except OSError as exc:
        raise EvidenceHarnessError(f"{role} disappeared after snapshot read") from exc
    if _file_physical_identity(current) != before_identity or _is_reparse(current):
        raise EvidenceHarnessError(f"{role} changed after snapshot read")
    raw = b"".join(chunks)
    resolved = absolute.resolve(strict=True)
    if resolved != absolute:
        raise EvidenceHarnessError(f"{role} path is not physical")
    record = {
        "path": str(resolved),
        "role": role,
        "size": len(raw),
        "raw_sha256": sha256_hex(raw),
        "git_blob_sha1": _git_blob_sha1(raw),
        "physical_identity": before_identity,
    }
    return _PhysicalFileSnapshot(resolved, raw, record)


def _validate_no_follow_file(path: Path, role: str) -> None:
    _validate_no_follow_components(path, role, require_file=True)


def _validate_no_follow_directory(path: Path, role: str) -> None:
    _validate_no_follow_components(path, role, require_file=False)


def _validate_no_follow_components(path: Path, role: str, *, require_file: bool) -> None:
    absolute = Path(os.path.abspath(str(path)))
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise EvidenceHarnessError(f"{role} is unavailable") from exc
        if _is_reparse(metadata):
            raise EvidenceHarnessError(f"{role} crosses a symlink or reparse point")
        if index == len(parts) - 1:
            if require_file and not stat.S_ISREG(metadata.st_mode):
                raise EvidenceHarnessError(f"{role} must be a regular physical file")
            if not require_file and not stat.S_ISDIR(metadata.st_mode):
                raise EvidenceHarnessError(f"{role} must be a physical directory")


def _is_reparse(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(getattr(metadata, "st_file_attributes", 0) & 0x400)


def _file_physical_identity(metadata: os.stat_result) -> dict[str, str]:
    return {
        "device": str(int(metadata.st_dev)),
        "inode": str(int(metadata.st_ino)),
        "size": str(int(metadata.st_size)),
        "mtime_ns": str(int(metadata.st_mtime_ns)),
    }


def _revalidate_file_snapshot(path: Path, snapshot: _PhysicalFileSnapshot, role: str) -> None:
    current = _read_physical_file_snapshot(path, role)
    if current.raw != snapshot.raw or current.record["physical_identity"] != snapshot.record["physical_identity"]:
        raise EvidenceHarnessError(f"{role} changed after its immutable snapshot")


def _unique_file_records(records: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        path = record["path"]
        existing = by_path.get(path)
        if existing is not None:
            if (
                existing["raw_sha256"] != record["raw_sha256"]
                or existing["physical_identity"] != record["physical_identity"]
            ):
                raise EvidenceHarnessError("one produced path has conflicting physical snapshots")
            continue
        by_path[path] = record
        result.append(record)
    return tuple(result)


def _path_state(path: Path) -> str:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return "unavailable"
    except OSError as exc:
        raise EvidenceHarnessError("original root availability could not be established") from exc
    if _is_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise EvidenceHarnessError("original root is not a physical directory")
    return "available"


def _require_lexically_disjoint(left: Path, right: Path, message: str) -> None:
    left_value = left.resolve(strict=False)
    right_value = right.resolve(strict=False)
    if left_value == right_value or left_value in right_value.parents or right_value in left_value.parents:
        raise EvidenceHarnessError(message)


def _require_physical_root_disjoint_if_available(left: Path, right: Path, message: str) -> None:
    if not left.exists() or not right.exists():
        return
    try:
        left_identity = physical_root_identity(left)
        right_identity = physical_root_identity(right)
    except (ArsError, OSError, ValueError) as exc:
        raise EvidenceHarnessError("physical root identity could not be captured") from exc
    if left_identity == right_identity:
        raise EvidenceHarnessError(message)


def _revalidate_publication_inputs(
    records: Sequence[Mapping[str, Any]],
    *,
    source_root: Path,
    output_root: Path,
    protected_roots: Sequence[Path],
) -> None:
    if _path_state(source_root) != "unavailable":
        raise EvidenceHarnessError("original root became available before publication")
    _require_lexically_disjoint(source_root, output_root, "source and output roots must be disjoint")
    if output_root.exists():
        _validate_no_follow_directory(output_root, "candidate output root")
        _require_physical_root_disjoint_if_available(source_root, output_root, "source and output roots are aliases")
        for protected_root in protected_roots:
            _require_physical_root_disjoint_if_available(
                output_root,
                protected_root,
                "candidate output root is a physical alias of a protected root",
            )
    for record in records:
        current = _file_record(Path(record["path"]), str(record["role"]))
        if current != dict(record):
            raise EvidenceHarnessError(f"published input changed before candidate publication: {record['path']}")


def _capture_surface(paths: Sequence[Path]) -> tuple[dict[str, Any], ...]:
    records = [_file_record(path, "protected_surface") for path in paths]
    return tuple(
        sorted(
            (
                {"path": item["path"], "raw_sha256": item["raw_sha256"], "physical_identity": item["physical_identity"]}
                for item in records
            ),
            key=lambda item: item["path"],
        )
    )


def _surface_hash(surface: Sequence[Mapping[str, Any]]) -> str:
    return sha256_hex(canonical_bytes(list(surface)))


def _surface_snapshots(before: Sequence[Mapping[str, Any]], after: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if tuple(item["path"] for item in before) != tuple(item["path"] for item in after):
        raise EvidenceHarnessError("protected surface path set changed")
    return [
        {
            "path": left["path"],
            "before_raw_sha256": left["raw_sha256"],
            "after_raw_sha256": right["raw_sha256"],
        }
        for left, right in zip(before, after, strict=True)
    ]


def _assert_surface_unchanged(
    before: Sequence[Mapping[str, Any]], after: Sequence[Mapping[str, Any]], label: str
) -> None:
    if tuple(before) != tuple(after):
        raise EvidenceHarnessError(f"{label} mutated the protected surface")


def _protected_surface_paths(
    *,
    target_root: Path,
    manifest_path: Path,
    evidence_path: Path,
    transaction_path: Path,
    operation_evidence: Mapping[str, Any],
    runtime: _RuntimeInputs,
    result: RestorePreflightResult,
) -> tuple[Path, ...]:
    del result
    paths = [
        manifest_path,
        evidence_path,
        transaction_path,
        runtime.bundle_record["path"],
        runtime.receipt_record["path"],
        runtime.registry_record["path"],
        runtime.snapshot_record["path"],
        runtime.endpoint_record["path"],
        runtime.artefact_manifest_record["path"],
    ]
    output_path = target_root / Path(str(operation_evidence["output_object_path"]))
    paths.append(output_path)
    manifest_value = _read_canonical_json(runtime.artefact_manifest_path, "runtime artefact manifest")
    for row in manifest_value.get("artefacts", []):
        relative = row.get("relative_path")
        if isinstance(relative, str) and relative:
            paths.append(target_root / Path(relative))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        value = str(Path(path).resolve(strict=False))
        if value not in seen:
            seen.add(value)
            unique.append(Path(path))
    return tuple(unique)


def _request_identity(
    transaction: Mapping[str, Any],
    result: RestorePreflightResult,
    actor_id: str,
    authority_grant_id: str,
) -> str:
    fields_value = {
        field: transaction.get(field)
        for field in (
            "transaction_id",
            "approval_sha256",
            "restore_preflight_result_hash",
            "source_root",
            "target_root",
            "project_id",
            "store_identity",
            "receipt_hash",
            "source_snapshot_hash",
        )
    }
    fields_value.update(
        {
            "result_hash": result.result_hash,
            "actor_id": actor_id,
            "authority_grant_id": authority_grant_id,
        }
    )
    return sha256_hex(canonical_bytes(fields_value))


def _candidate_id(candidate_without_id: Mapping[str, Any]) -> str:
    return f"a8c_{sha256_hex(canonical_bytes(dict(candidate_without_id)))}"


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(  # nosemgrep: insecure-hash-algorithm-sha1  # nosec B324
        header + raw,
        usedforsecurity=False,
    ).hexdigest()


def _validate_claim(
    claim: Mapping[str, Any],
    key: str,
    digest: str,
    blob_sha1: str,
    object_path: Path,
    root: Path,
) -> None:
    expected = {
        "key": key,
        "raw_sha256": digest,
        "git_blob_sha1": blob_sha1,
        "object_path": object_path.relative_to(root).as_posix(),
    }
    if dict(claim) != expected:
        raise EvidenceConflictError("immutable evidence key conflicts with existing bytes")


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _read_physical_file_snapshot(path, "immutable evidence object")
        if existing.raw != raw:
            raise EvidenceConflictError("immutable evidence path conflicts with existing bytes")
        return
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        existing_temporary = _read_physical_file_snapshot(temporary, "evidence publication temporary")
        if existing_temporary.raw != raw:
            temporary.unlink()
            fsync_directory(path.parent)
    if not temporary.exists():
        _write_exclusive(temporary, raw)
    verified_temporary = _read_physical_file_snapshot(temporary, "evidence publication temporary")
    if verified_temporary.raw != raw:
        raise EvidenceHarnessError("evidence publication temporary is incomplete")
    if path.exists():
        existing = _read_physical_file_snapshot(path, "immutable evidence object")
        if existing.raw != raw:
            raise EvidenceConflictError("immutable evidence path conflicts with existing bytes")
        temporary.unlink(missing_ok=True)
        fsync_directory(path.parent)
        return
    try:
        os.replace(str(temporary), str(path))
    except OSError as exc:
        raise EvidenceHarnessError("durable evidence publication failed") from exc
    fsync_directory(path.parent)
    published = _read_physical_file_snapshot(path, "published evidence object")
    if published.raw != raw:
        raise EvidenceHarnessError("published evidence bytes differ from the immutable preimage")


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _validate_candidate_joins(candidate: Mapping[str, Any]) -> None:
    foundation = candidate["foundation"]
    operation = candidate["external_operation"]
    restart = candidate["restart"]
    admission = candidate["admission"]
    retry = candidate["retry_recovery"]
    rejection = candidate["rejected_admission"]
    if (
        operation["destination_root"] != foundation["control_root"]
        or restart["control_root"] != operation["destination_root"]
    ):
        raise EvidenceHarnessError("candidate destination/control-root join is invalid")
    if operation["source_root"] != operation["source_lineage"]["source_root"]:
        raise EvidenceHarnessError("candidate source lineage join is invalid")
    if operation["source_lineage"]["origin_witness_path"] != foundation["origin_witness_path"]:
        raise EvidenceHarnessError("candidate witness path join is invalid")
    if operation["source_lineage"]["origin_witness_sha256"] != foundation["origin_witness_sha256"]:
        raise EvidenceHarnessError("candidate witness digest join is invalid")
    if restart["project_id"] != foundation["project_id"] or restart["store_identity"] != foundation["store_identity"]:
        raise EvidenceHarnessError("candidate restart identity join is invalid")
    transaction_records = (
        admission["pre_writer"],
        admission["locked_revalidation"],
        admission["locked_revalidation"]["lock_identity"],
        rejection,
        retry["conflicting_retry"],
    )
    if any(record["transaction_id"] != operation["transaction_id"] for record in transaction_records):
        raise EvidenceHarnessError("candidate probe/transaction join is invalid")
    if retry["exact_retry"]["before_generation"] != operation["final_transaction_generation"]:
        raise EvidenceHarnessError("candidate retry generation join is invalid")
    if retry["rollback_recovery"]["transaction_generation"] != operation["final_transaction_generation"]:
        raise EvidenceHarnessError("candidate rollback generation join is invalid")
    expected_generations = _transaction_generations({"generation": len(_TRANSACTION_STEPS) - 1, "state": "cleared"})
    if retry["transaction_generations"] != expected_generations:
        raise EvidenceHarnessError("candidate transaction generation sequence is not exact")
    if rejection["status"] != "diagnostic_only" or not rejection["failed_predicates"]:
        raise EvidenceHarnessError("candidate rejection result is not a diagnostic runtime result")
    if rejection["mutation_result"] != "no_mutation":
        raise EvidenceHarnessError("candidate rejection does not prove no mutation")
    for probe in (rejection, retry["conflicting_retry"]):
        if probe["surface_before_sha256"] != probe["surface_after_sha256"]:
            raise EvidenceHarnessError("candidate protected surface changed during a rejected probe")
        for item in probe["snapshots"]:
            if item["before_raw_sha256"] != item["after_raw_sha256"]:
                raise EvidenceHarnessError("candidate no-mutation snapshot changed")
    paths = candidate["git"]["paths"]
    path_values = [item["path"] for item in paths]
    if path_values != sorted(set(path_values)):
        raise EvidenceHarnessError("candidate Git path set is not sorted and unique")
    if candidate["git"]["path_set_sha256"] != sha256_hex(canonical_bytes(path_values)):
        raise EvidenceHarnessError("candidate Git path-set digest is invalid")
    if not candidate["git"]["working_bytes_match_head"]:
        raise EvidenceHarnessError("candidate Git proof does not bind working bytes")
    if not candidate["git"]["execution_bytes_match_head"]:
        raise EvidenceHarnessError("candidate Git proof does not bind execution-root bytes")
    if candidate["registry"]["raw_sha256"] != candidate["registry"]["file"]["raw_sha256"]:
        raise EvidenceHarnessError("candidate registry raw_sha256 does not join its file digest")
    file_records: dict[str, Mapping[str, Any]] = {}
    for record in candidate["produced_files"]:
        path = record["path"]
        if path in file_records:
            raise EvidenceHarnessError("candidate produced file path is duplicated")
        file_records[path] = record
        current = _file_record(Path(path), str(record["role"]))
        if current != dict(record):
            raise EvidenceHarnessError(f"candidate produced file changed: {path}")
    nested_records = [
        foundation["file"],
        operation["destination_manifest"],
        operation["operation_evidence"],
        operation["transaction"],
        admission["runtime_inputs_file"],
        candidate["registry"]["file"],
        *(item["file"] for item in candidate["bound_artifacts"]),
        *(item for item in (candidate["retry_recovery"].get("runtime_inputs_file"),) if item is not None),
    ]
    for record in nested_records:
        if record["path"] not in file_records or file_records[record["path"]] != record:
            raise EvidenceHarnessError("candidate nested file record is not in the produced-file closure")
    transaction_value = _read_canonical_json(Path(operation["transaction"]["path"]), "candidate transaction")
    if (
        transaction_value.get("transaction_id") != operation["transaction_id"]
        or transaction_value.get("generation") != operation["final_transaction_generation"]
    ):
        raise EvidenceHarnessError("candidate transaction identity is not joined to its bytes")
    if transaction_value.get("restore_preflight_result_hash") != admission["pre_writer"]["result_hash"]:
        raise EvidenceHarnessError("candidate preflight result is not joined to transaction bytes")
    operation_value = _read_canonical_json(
        Path(operation["operation_evidence"]["path"]), "candidate operation evidence"
    )
    if operation_value.get("transaction_id") not in {None, operation["transaction_id"]}:
        raise EvidenceHarnessError("candidate operation evidence transaction join is invalid")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))
