"""Fail-closed, operator-only preparation for a later WP6.4 real-A8 proof.

The module observes an already materialized foundation and an already completed
moved-store operation.  It never initializes a store, chooses owner values,
executes a restore, or turns an assertion into evidence.  All writes are
limited to the final content-addressed candidate output after read-only checks
have passed.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ApprovedProjectBinding, ControlBinding, canonical_foundation_path
from research_system.errors import ArsError, ConflictError
from research_system.store.identity import (
    load_canonical_restore_binding_evidence,
    load_restore_binding_transaction,
    load_store_manifest,
    load_store_origin_witness,
    physical_root_identity,
    restore_binding_transaction_path,
    validate_approved_origin_witness_path,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SCHEMA_ID = "ars://wp6-4/real-a8-proof-candidate"
_ADMISSION_SCHEMA_ID = "ars://wp6-4/real-a8/admission-evidence"
_RECOVERY_SCHEMA_ID = "ars://wp6-4/real-a8/interruption-retry-evidence"
_REJECTION_SCHEMA_ID = "ars://wp6-4/real-a8/rejected-admission-probe"
_TRANSACTION_STATES = (
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
    admission_evidence_path: Path
    interruption_evidence_path: Path
    rejected_admission_path: Path
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


class ContentAddressedEvidenceStore:
    """Write one logical evidence key once, with a digest-addressed object."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def write_once(self, key: str, raw: bytes) -> tuple[Path, str, str]:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", key):
            raise EvidenceHarnessError("evidence object key is invalid")
        digest = sha256_hex(raw)
        blob_sha1 = _git_blob_sha1(raw)
        claim_path = self.root / "claims" / f"{key}.json"
        object_path = self.root / "objects" / f"sha256-{digest}.json"
        if claim_path.exists():
            claim = _read_canonical_json(claim_path, "evidence claim")
            if claim.get("raw_sha256") != digest:
                raise EvidenceConflictError("immutable evidence key conflicts with existing bytes")
            if not object_path.is_file() or object_path.read_bytes() != raw:
                raise EvidenceHarnessError("immutable evidence claim points to missing or changed bytes")
            return object_path, digest, blob_sha1

        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "claims").mkdir(parents=True, exist_ok=True)
        (self.root / "objects").mkdir(parents=True, exist_ok=True)
        if object_path.exists() and object_path.read_bytes() != raw:
            raise EvidenceConflictError("content-addressed evidence object conflicts with existing bytes")
        if not object_path.exists():
            _write_exclusive(object_path, raw)
        claim = canonical_bytes(
            {
                "key": key,
                "raw_sha256": digest,
                "git_blob_sha1": blob_sha1,
                "object_path": object_path.relative_to(self.root).as_posix(),
            }
        )
        try:
            _write_exclusive(claim_path, claim)
        except FileExistsError:
            existing = _read_canonical_json(claim_path, "evidence claim")
            if existing.get("raw_sha256") != digest:
                raise EvidenceConflictError("immutable evidence key conflicts with existing bytes") from None
        return object_path, digest, blob_sha1


def capture_real_a8_candidate(*, request: A8ProofRequest) -> CandidateCapture:
    """Capture a produced-unreviewed candidate from physical and file evidence.

    The function performs no source/destination mutation.  The only write is a
    candidate object under ``request.output_root`` after all validation has
    completed.
    """

    approved, foundation_record = _load_approved_foundation(request.foundation_path)
    _load_canonical_binding(request.binding_path, approved)
    source_root = Path(approved.origin_witness.initial_control_root).resolve(strict=False)
    target_root = approved.control_root.resolve(strict=True)
    origin_root = approved.origin_authority_root.resolve(strict=True)
    _validate_root_relationships(approved, source_root, target_root, origin_root, request.output_root)

    witness_path, witness_origin_root = validate_approved_origin_witness_path(
        approved.origin_witness_path,
        approved.origin_witness,
    )
    if witness_origin_root != origin_root:
        raise EvidenceHarnessError("origin witness authority root differs from foundation")
    witness = load_store_origin_witness(witness_path, expected_sha256=approved.origin_witness_sha256)
    if witness.raw_sha256 != approved.origin_witness_sha256:
        raise EvidenceHarnessError("origin witness raw digest differs from foundation")

    manifest_path = target_root / "manifests" / "store-identity.json"
    transaction_path = restore_binding_transaction_path(target_root)
    evidence_path = target_root / "manifests" / "restore-binding-evidence.json"
    manifest = _load_store_manifest(target_root, approved)
    operation_evidence = load_canonical_restore_binding_evidence(target_root)
    transaction = load_restore_binding_transaction(target_root)
    if operation_evidence is None or transaction is None:
        raise EvidenceHarnessError("moved-store operation evidence is incomplete")
    _validate_operation_join(
        approved=approved,
        source_root=source_root,
        target_root=target_root,
        manifest=manifest,
        operation_evidence=operation_evidence,
        transaction=transaction,
    )

    admission, admission_record, registry_record, bound_artifact_records = _load_admission_evidence(
        request.admission_evidence_path,
        operation_evidence=operation_evidence,
        manifest_path=manifest_path,
        transaction_path=transaction_path,
        evidence_path=evidence_path,
    )
    recovery, recovery_record = _load_recovery_evidence(
        request.interruption_evidence_path,
        transaction=transaction,
        transaction_path=transaction_path,
        source_root=source_root,
        witness=witness,
    )
    rejection, rejection_record = _load_rejection_evidence(request.rejected_admission_path)

    source_state = _path_state(source_root)
    if source_state != "unavailable":
        raise EvidenceHarnessError("original root is still available at the restart checkpoint")
    destination_identity = physical_root_identity(target_root)
    restart = _fresh_process_binding_load(
        binding_path=request.binding_path,
        code_root=approved.code_roots[0],
        expected=approved,
    )
    git_identity = _capture_git_identity(request.expected_git_commit, request.git_paths)
    output_root = _validate_output_root(
        request.output_root,
        code_roots=approved.code_roots,
        target_root=target_root,
        origin_root=origin_root,
    )

    produced_files = _unique_file_records(
        (
            foundation_record,
            _file_record(request.binding_path, "binding_config"),
            _file_record(witness_path, "origin_witness"),
            _file_record(manifest_path, "destination_store_manifest"),
            _file_record(evidence_path, "restore_operation_evidence"),
            _file_record(transaction_path, "restore_transaction"),
            admission_record,
            recovery_record,
            rejection_record,
            registry_record,
            *bound_artifact_records,
        )
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
            "destination_manifest": _file_record(manifest_path, "destination_store_manifest"),
            "operation_evidence": _file_record(evidence_path, "restore_operation_evidence"),
            "transaction": _file_record(transaction_path, "restore_transaction"),
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
        "admission": admission,
        "registry": {
            "file": registry_record,
            "raw_sha256": registry_record["raw_sha256"],
        },
        "bound_artifacts": [{"file": record, "raw_sha256": record["raw_sha256"]} for record in bound_artifact_records],
        "retry_recovery": recovery,
        "rejected_admission": rejection,
        "git": git_identity,
        "environment": _environment(),
        "produced_files": list(produced_files),
    }
    candidate = dict(candidate_without_id)
    candidate["candidate_id"] = f"a8c_{sha256_hex(canonical_bytes(candidate_without_id))}"
    validate_real_a8_candidate(candidate)
    raw = canonical_bytes(candidate)
    path, raw_sha256, blob_sha1 = ContentAddressedEvidenceStore(output_root).write_once(
        candidate["candidate_id"],
        raw,
    )
    return CandidateCapture(candidate, path, raw_sha256, blob_sha1)


def validate_real_a8_candidate(candidate: Mapping[str, Any]) -> None:
    """Validate the strict candidate schema and lifecycle hard stops."""

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
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceHarnessError("real-A8 candidate schema is unavailable") from exc
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


def _load_approved_foundation(path: Path) -> tuple[ApprovedProjectBinding, dict[str, Any]]:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise EvidenceHarnessError("canonical foundation path must be absolute")
    expected = canonical_foundation_path().resolve(strict=False)
    resolved = candidate.resolve(strict=False)
    if resolved != expected:
        raise EvidenceHarnessError("foundation path is not the canonical materialized foundation")
    record = _file_record(resolved, "foundation")
    try:
        return ApprovedProjectBinding.load(resolved), record
    except (ArsError, OSError, ValueError) as exc:
        raise EvidenceHarnessError("owner-materialized canonical foundation is required") from exc


def _load_canonical_binding(path: Path, approved: ApprovedProjectBinding) -> ControlBinding:
    try:
        binding = ControlBinding.load(Path(path))
    except (ArsError, OSError, ValueError) as exc:
        raise EvidenceHarnessError("canonical ControlBinding could not be loaded") from exc
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
    _require_lexically_disjoint(source_root, origin_root, "source root overlaps origin authority root")
    _require_lexically_disjoint(target_root, origin_root, "destination root overlaps origin authority root")
    if not approved.code_roots:
        raise EvidenceHarnessError("foundation code roots are required")
    for root in approved.code_roots:
        _require_lexically_disjoint(root, source_root, "source root overlaps an approved code root")
        _require_lexically_disjoint(root, target_root, "destination root overlaps an approved code root")


def _validate_output_root(
    path: Path,
    *,
    code_roots: Sequence[Path],
    target_root: Path,
    origin_root: Path,
) -> Path:
    output = Path(path)
    if not output.is_absolute():
        raise EvidenceHarnessError("candidate output root must be absolute")
    if output.exists() and output.resolve(strict=False) != output.absolute():
        raise EvidenceHarnessError("candidate output root must be a physical path")
    for root in (*code_roots, target_root, origin_root):
        _require_lexically_disjoint(output, Path(root), "candidate output root overlaps a protected root")
    return output.resolve(strict=False)


def _load_store_manifest(target_root: Path, approved: ApprovedProjectBinding) -> dict[str, Any]:
    try:
        value = load_store_manifest(
            target_root,
            approved_witness=approved.origin_witness,
            approved_witness_path=approved.origin_witness_path,
        )
    except (ArsError, OSError, ValueError) as exc:
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
    if not isinstance(transaction.get("generation"), int) or transaction["generation"] != len(_TRANSACTION_STATES) - 1:
        raise EvidenceHarnessError("restore transaction final generation is not exact")


def _load_admission_evidence(
    path: Path,
    *,
    operation_evidence: Mapping[str, Any],
    manifest_path: Path,
    transaction_path: Path,
    evidence_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]:
    value, record = _load_canonical_evidence(path, _ADMISSION_SCHEMA_ID)
    required = {
        "schema_id",
        "schema_version",
        "pre_writer",
        "locked_revalidation",
        "registry_path",
        "registry_sha256",
        "bound_artifacts",
    }
    if set(value) != required:
        raise EvidenceHarnessError("admission evidence fields are incomplete")
    pre_writer = value["pre_writer"]
    locked = value["locked_revalidation"]
    if (
        not isinstance(pre_writer, dict)
        or set(pre_writer) != {"status", "result_hash"}
        or pre_writer.get("status") != "verified"
        or pre_writer.get("result_hash") != operation_evidence.get("restore_preflight_result_hash")
        or not isinstance(locked, dict)
        or set(locked) != {"status", "revalidation_sha256"}
        or locked.get("status") != "verified"
    ):
        raise EvidenceHarnessError("pre-writer admission evidence is not verified")
    expected_locked = sha256_hex(
        canonical_bytes(
            {
                "manifest_sha256": _file_record(manifest_path, "manifest")["raw_sha256"],
                "transaction_sha256": _file_record(transaction_path, "transaction")["raw_sha256"],
                "evidence_sha256": _file_record(evidence_path, "operation")["raw_sha256"],
            }
        )
    )
    if locked.get("revalidation_sha256") != expected_locked:
        raise EvidenceHarnessError("locked revalidation evidence does not match current store files")

    registry_path = _absolute_evidence_path(value.get("registry_path"), "registry path")
    registry_record = _file_record(registry_path, "evidence_registry")
    if value.get("registry_sha256") != registry_record["raw_sha256"]:
        raise EvidenceHarnessError("registry hash does not match captured bytes")
    artifacts = value.get("bound_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceHarnessError("bound-artifact evidence is required")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "raw_sha256", "git_blob_sha1"}:
            raise EvidenceHarnessError("bound-artifact evidence fields are invalid")
        artifact_path = _absolute_evidence_path(item.get("path"), "bound-artifact path")
        record_item = _file_record(artifact_path, "bound_artifact")
        if (
            artifact_path.as_posix() in seen
            or item["raw_sha256"] != record_item["raw_sha256"]
            or item["git_blob_sha1"] != record_item["git_blob_sha1"]
        ):
            raise EvidenceHarnessError("bound-artifact evidence does not match captured bytes")
        seen.add(artifact_path.as_posix())
        records.append(record_item)
    return (
        {
            "pre_writer": {"status": "verified", "result_hash": pre_writer["result_hash"]},
            "locked_revalidation": {"status": "verified", "revalidation_sha256": locked["revalidation_sha256"]},
            "evidence_file": record,
        },
        record,
        registry_record,
        tuple(records),
    )


def _load_recovery_evidence(
    path: Path,
    *,
    transaction: Mapping[str, Any],
    transaction_path: Path,
    source_root: Path,
    witness: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    value, record = _load_canonical_evidence(path, _RECOVERY_SCHEMA_ID)
    required = {
        "schema_id",
        "schema_version",
        "transaction_generations",
        "exact_retry",
        "conflicting_retry",
        "rollback_recovery",
    }
    if set(value) != required:
        raise EvidenceHarnessError("interruption/retry evidence fields are incomplete")
    generations = value["transaction_generations"]
    if not isinstance(generations, list) or len(generations) != len(_TRANSACTION_STATES):
        raise EvidenceHarnessError("exact transaction generations are required")
    for index, (item, state) in enumerate(zip(generations, _TRANSACTION_STATES, strict=True)):
        if not isinstance(item, dict) or set(item) != {"generation", "state", "record_sha256"}:
            raise EvidenceHarnessError("transaction generation evidence fields are invalid")
        if item["generation"] != index or item["state"] != state or not _SHA256.fullmatch(str(item["record_sha256"])):
            raise EvidenceHarnessError("transaction generation evidence is not exact")
    current_hash = _file_record(transaction_path, "transaction")["raw_sha256"]
    exact = value["exact_retry"]
    if (
        not isinstance(exact, dict)
        or set(exact)
        != {
            "before_generation",
            "after_generation",
            "before_transaction_sha256",
            "after_transaction_sha256",
            "request_sha256",
        }
        or exact["before_generation"] != transaction["generation"]
        or exact["after_generation"] != transaction["generation"]
        or exact["before_transaction_sha256"] != current_hash
        or exact["after_transaction_sha256"] != current_hash
        or not _SHA256.fullmatch(str(exact["request_sha256"]))
    ):
        raise EvidenceHarnessError("exact retry does not converge to the immutable transaction")
    conflicting = value["conflicting_retry"]
    _validate_no_mutation_probe(conflicting, "conflicting retry", required_failure="conflict")
    rollback = value["rollback_recovery"]
    lineage_hash = sha256_hex(
        canonical_bytes(
            {
                "source_root": str(source_root),
                "source_root_identity": dict(witness.initial_physical_root_identity),
                "origin_witness_sha256": witness.raw_sha256,
            }
        )
    )
    if (
        not isinstance(rollback, dict)
        or set(rollback) != {"recovered_state", "transaction_generation", "transaction_sha256", "source_lineage_sha256"}
        or rollback["recovered_state"] != "cleared"
        or rollback["transaction_generation"] != transaction["generation"]
        or rollback["transaction_sha256"] != current_hash
        or rollback["source_lineage_sha256"] != lineage_hash
    ):
        raise EvidenceHarnessError("rollback/recovery evidence is incomplete")
    return (
        {
            "transaction_generations": generations,
            "exact_retry": {**exact, "result": "converged"},
            "conflicting_retry": {**conflicting, "result": "rejected_without_mutation"},
            "rollback_recovery": rollback,
            "evidence_file": record,
        },
        record,
    )


def _load_rejection_evidence(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value, record = _load_canonical_evidence(path, _REJECTION_SCHEMA_ID)
    required = {"schema_id", "schema_version", "exit_code", "failure_code", "snapshots"}
    if set(value) != required:
        raise EvidenceHarnessError("rejected-admission probe fields are incomplete")
    _validate_no_mutation_probe(value, "rejected admission", required_failure="admission_rejected")
    return (
        {
            "exit_code": value["exit_code"],
            "failure_code": value["failure_code"],
            "snapshots": value["snapshots"],
            "mutation_result": "no_mutation",
            "evidence_file": record,
        },
        record,
    )


def _validate_no_mutation_probe(value: Any, label: str, *, required_failure: str) -> None:
    if not isinstance(value, dict):
        raise EvidenceHarnessError(f"{label} evidence is invalid")
    if value.get("exit_code", 0) == 0 or value.get("failure_code") != required_failure:
        raise EvidenceHarnessError(f"{label} did not record a rejected operation")
    snapshots = value.get("snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise EvidenceHarnessError(f"{label} no-mutation snapshots are required")
    for item in snapshots:
        if not isinstance(item, dict) or set(item) != {"path", "before_raw_sha256", "after_raw_sha256"}:
            raise EvidenceHarnessError(f"{label} snapshot fields are invalid")
        path = _absolute_evidence_path(item.get("path"), f"{label} snapshot path")
        after = _file_record(path, f"{label} snapshot")
        if item["before_raw_sha256"] != item["after_raw_sha256"] or item["after_raw_sha256"] != after["raw_sha256"]:
            raise EvidenceHarnessError(f"{label} probe mutated a durable surface")


def _fresh_process_binding_load(
    *, binding_path: Path, code_root: Path, expected: ApprovedProjectBinding
) -> dict[str, Any]:
    code = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "from research_system.config import ControlBinding\n"
        "binding = ControlBinding.load(Path(sys.argv[1]))\n"
        "print(json.dumps({'control_root': str(binding.control_root), 'project_id': binding.project_id, "
        "'store_identity': binding.store_identity}, sort_keys=True, separators=(',', ':')))\n"
    )
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(code_root), existing)))
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, str(Path(binding_path).resolve(strict=True))],
            cwd=str(code_root.resolve(strict=True)),
            env=env,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise EvidenceHarnessError("fresh-process ControlBinding probe could not start") from exc
    if result.returncode != 0:
        try:
            detail = result.stderr.decode("utf-8", errors="replace").strip().replace("\r", " ").replace("\n", " ")
        except AttributeError:
            detail = ""
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


def _capture_git_identity(expected_commit: str, paths: Sequence[str]) -> dict[str, Any]:
    if not _COMMIT.fullmatch(expected_commit):
        raise EvidenceHarnessError("exact Git subject must be a full commit SHA")
    repo_root = Path(__file__).resolve().parents[2]
    commit = _git(repo_root, "rev-parse", "HEAD")
    if commit != expected_commit:
        raise EvidenceHarnessError("exact Git subject differs from HEAD")
    parent_line = _git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    path_records: list[dict[str, Any]] = []
    for raw_path in paths:
        if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute() or "\\" in raw_path:
            raise EvidenceHarnessError("Git identity path must be a non-empty relative POSIX path")
        if any(part in {"", ".", ".."} for part in Path(raw_path).parts):
            raise EvidenceHarnessError("Git identity path is not canonical")
        rows = _git(repo_root, "ls-tree", "-r", "--full-tree", "HEAD", "--", raw_path).splitlines()
        matches = [row.split(maxsplit=2) for row in rows if row]
        if len(matches) != 1 or len(matches[0]) != 3:
            raise EvidenceHarnessError(f"Git identity path is not exactly tracked at HEAD: {raw_path}")
        mode, object_type, blob_and_path = matches[0]
        blob, path_value = (
            blob_and_path.split(maxsplit=1) if any(char.isspace() for char in blob_and_path) else ("", "")
        )
        if object_type != "blob" or not _SHA1.fullmatch(blob) or path_value != raw_path:
            raise EvidenceHarnessError(f"Git identity blob is invalid: {raw_path}")
        path_records.append({"path": raw_path, "mode": mode, "blob_sha1": blob})
    return {
        "repository_root": str(repo_root),
        "commit": commit,
        "parent_commits": parent_line[1:],
        "tree": tree,
        "subject_resolution": "exact_head_match",
        "paths": path_records,
    }


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceHarnessError("exact Git identity could not be captured") from exc
    return result.stdout.strip()


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
    record = _file_record(path, "operator_evidence")
    value = _read_canonical_json(Path(path), "operator evidence")
    if value.get("schema_id") != schema_id or value.get("schema_version") != "1.0.0":
        raise EvidenceHarnessError(f"unsupported operator evidence schema: {schema_id}")
    return value, record


def _read_canonical_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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
    candidate = Path(path)
    if not candidate.is_absolute():
        raise EvidenceHarnessError(f"{role} path must be absolute")
    try:
        absolute = candidate.absolute()
        metadata = absolute.lstat()
        if not metadata or not absolute.is_file() or absolute.is_symlink():
            raise EvidenceHarnessError(f"{role} must be a regular physical file")
        resolved = absolute.resolve(strict=True)
        if resolved != absolute:
            raise EvidenceHarnessError(f"{role} path is not physical")
        raw = absolute.read_bytes()
    except EvidenceHarnessError:
        raise
    except (OSError, FileNotFoundError) as exc:
        raise EvidenceHarnessError(f"{role} file is unavailable") from exc
    return {
        "path": str(resolved),
        "role": role,
        "size": len(raw),
        "raw_sha256": sha256_hex(raw),
        "git_blob_sha1": _git_blob_sha1(raw),
    }


def _unique_file_records(records: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        path = record["path"]
        if path in seen:
            continue
        seen.add(path)
        result.append(record)
    return tuple(result)


def _path_state(path: Path) -> str:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return "unavailable"
    except OSError as exc:
        raise EvidenceHarnessError("original root availability could not be established") from exc
    if not metadata or not path.is_dir() or path.is_symlink():
        raise EvidenceHarnessError("original root is not a physical directory")
    return "available"


def _require_lexically_disjoint(left: Path, right: Path, message: str) -> None:
    left_value = left.resolve(strict=False)
    right_value = right.resolve(strict=False)
    if left_value == right_value or left_value in right_value.parents or right_value in left_value.parents:
        raise EvidenceHarnessError(message)


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)
