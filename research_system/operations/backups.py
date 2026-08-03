"""W8 backup receipts and authority-bound restore preflight evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from typing import Any
from pathlib import Path

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError
from research_system.projection.replay import replay
from research_system.store.identity import (
    StoreOriginWitness,
    _require_physical_disjoint,
    _restore_preflight_anchor,
    _validate_approved_origin_witness_path,
    canonical_restore_binding_output,
    load_store_manifest_unbound,
    manifest_schema_root,
)
from research_system.store.layout import require_existing_control_root
from research_system.store.ledger import EventLedger
from research_system.schema_registry import bundled_runtime_schema_registry


@dataclass(frozen=True, slots=True)
class ArtefactBinding:
    artefact_id: str
    artefact_hash: str


@dataclass(frozen=True, slots=True)
class BackupReceipt:
    receipt_id: str
    receipt_revision: int
    receipt_hash: str
    project_id: str
    store_identity: str
    canonical_tail_position: int
    canonical_tail_hash: str
    snapshot_id: str
    snapshot_hash: str
    snapshot_source_position: int
    snapshot_source_hash: str
    snapshot_state_hash: str
    replay_start_position: int
    replay_end_position: int
    schema_versions: tuple[str, ...]
    tool_versions: tuple[str, ...]
    encryption_class: str
    redaction_class: str
    external_artefact_manifest_hash: str
    artefact_bindings: tuple[ArtefactBinding, ...]
    availability_status: str
    availability_observation_hash: str
    created_at: str
    created_by_actor_id: str
    verified_at: str
    verified_by_actor_id: str
    verification_authority_grant_id: str
    destination_class: str
    source_endpoint_scheme: str
    evidence_registry_hash: str


@dataclass(frozen=True, slots=True)
class RestorePreflightResult:
    status: str
    failed_predicates: tuple[str, ...]
    receipt_hash: str
    ledger_hash: str
    snapshot_hash: str
    target_endpoint_ownership_hash: str
    artefact_manifest_hash: str
    availability_observations_hash: str
    registry_hash: str
    target_root: str
    project_id: str
    store_identity: str
    tail_position: int
    tail_hash: str
    snapshot_id: str
    actor_id: str
    authority_grant_id: str
    result_hash: str
    source_root: str = ""
    code_roots: list[str] = field(default_factory=list)
    schema_root: str = ""
    source_snapshot_hash: str = ""
    target_manifest_bytes_sha256: str = ""
    expected_output_sha256: str = ""
    origin_witness_path: str = ""
    origin_witness_sha256: str = ""
    origin_initial_control_root: str = ""
    origin_initial_physical_root_identity: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"verified", "diagnostic_only"}:
            raise ValueError("invalid restore preflight status")
        predicates_empty = not self.failed_predicates
        if (self.status == "verified") != predicates_empty:
            raise ValueError("restore preflight status must match failed predicates")
        if len(set(self.failed_predicates)) != len(self.failed_predicates):
            raise ValueError("restore preflight failed predicates must be unique")


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _hash_without(value: object, field: str) -> str:
    payload = asdict(value)
    payload[field] = ""
    return sha256_hex(canonical_bytes(_jsonable(payload)))


def seal_backup_receipt(receipt: BackupReceipt) -> BackupReceipt:
    """Return a backup receipt with its canonical content hash populated."""
    if receipt.receipt_revision < 1:
        raise ValueError("backup receipt revision must be positive")
    return replace(receipt, receipt_hash=_hash_without(receipt, "receipt_hash"))


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, "0" * 64
    return (value if isinstance(value, dict) else None), sha256_hex(data)


def _inside(root: Path, relative: str) -> Path | None:
    target = (root / relative).resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    if target == resolved_root or resolved_root not in target.parents:
        return None
    return target


def verify_restore_before_writer_lease(
    *,
    target_root: Path,
    receipt: BackupReceipt,
    snapshot_path: Path,
    endpoint_ownership_path: Path,
    artefact_manifest_path: Path,
    registry: object,
    actor_id: str,
    authority_grant_id: str,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
) -> RestorePreflightResult:
    """Independently inspect a moved store and derive a pre-writer result."""
    target = target_root.resolve(strict=False)
    failed: list[str] = []
    validated_witness_path: Path | None = None
    origin_root: Path | None = None
    if approved_witness is None:
        failed.append("origin_witness_required")
    if approved_witness_path is None or not approved_witness_path.is_absolute():
        failed.append("origin_witness_path_required")
    elif approved_witness is not None:
        try:
            validated_witness_path, origin_root = _validate_approved_origin_witness_path(
                approved_witness_path,
                approved_witness,
            )
            _require_physical_disjoint(
                origin_root,
                target,
                message="origin authority root must be physically disjoint from the restored target",
            )
        except (ArsError, OSError):
            failed.append("origin_witness_path_invalid")
    if receipt.receipt_hash != _hash_without(receipt, "receipt_hash"):
        failed.append("receipt_hash_mismatch")

    identity, identity_raw_hash = _read_json(target / "manifests" / "store-identity.json")
    actual_project = receipt.project_id
    actual_store = receipt.store_identity
    source_root: Path | None = None
    code_roots: list[str] = []
    schema_root = ""
    target_manifest_bytes_sha256 = identity_raw_hash
    expected_output_sha256 = "0" * 64
    ordinary_manifest_hash_valid = False
    if identity is None:
        failed.append("store_identity_manifest_invalid")
    else:
        recorded_hash = identity.get("manifest_hash")
        unsigned = {key: value for key, value in identity.items() if key != "manifest_hash"}
        ordinary_manifest_hash_valid = recorded_hash == sha256_hex(canonical_bytes(unsigned))
        actual_project = str(identity.get("project_id", ""))
        actual_store = str(identity.get("store_identity", ""))
        if actual_project != receipt.project_id:
            failed.append("project_identity_mismatch")
        if actual_store != receipt.store_identity:
            failed.append("store_identity_mismatch")
        roots_value = identity.get("code_roots")
        if isinstance(roots_value, list) and roots_value and all(isinstance(item, str) for item in roots_value):
            code_roots = [str(Path(item).resolve(strict=False)) for item in roots_value]
        else:
            failed.append("code_root_binding_invalid")
        if identity.get("endpoint_scheme") != receipt.source_endpoint_scheme:
            failed.append("endpoint_scheme_mismatch")
        try:
            source_root = Path(str(identity.get("control_root"))).resolve(strict=False)
        except OSError:
            failed.append("source_root_invalid")
        try:
            loaded_manifest = load_store_manifest_unbound(target)
            target_manifest_bytes_sha256 = sha256_hex((target / "manifests" / "store-identity.json").read_bytes())
            persisted_schema_root = manifest_schema_root(loaded_manifest)
            if persisted_schema_root is not None:
                schema_root = str(persisted_schema_root.resolve(strict=False))
            elif code_roots:
                schema_root = str(Path(code_roots[0]) / ".research-system" / "schemas")
        except Exception:
            failed.append("store_identity_manifest_invalid")
        else:
            if approved_witness is not None and validated_witness_path is not None:
                try:
                    immutable_preflight = _restore_preflight_anchor(
                        target,
                        loaded_manifest,
                        approved_witness,
                        validated_witness_path,
                    )
                except (ArsError, OSError, ValueError):
                    if not ordinary_manifest_hash_valid:
                        failed.append("store_identity_manifest_invalid")
                    failed.append("origin_witness_manifest_mismatch")
                else:
                    if immutable_preflight is not None:
                        source_root = Path(str(immutable_preflight["source_root"])).resolve(strict=False)
                        target_manifest_bytes_sha256 = str(immutable_preflight["target_manifest_bytes_sha256"])
                    elif not ordinary_manifest_hash_valid:
                        failed.append("store_identity_manifest_invalid")
            elif not ordinary_manifest_hash_valid:
                failed.append("store_identity_manifest_invalid")

    if source_root == target:
        failed.append("store_not_moved")

    if approved_witness is not None and validated_witness_path is not None:
        if source_root is not None and source_root != Path(approved_witness.initial_control_root):
            failed.append("origin_witness_source_mismatch")
        if origin_root is not None:
            try:
                _require_physical_disjoint(
                    origin_root,
                    source_root or target,
                    message="origin authority root must be physically disjoint from the restore source",
                )
            except (ArsError, OSError):
                failed.append("origin_witness_source_overlap")

    if code_roots and schema_root:
        try:
            expected_output = canonical_restore_binding_output(
                target,
                actual_project,
                actual_store,
                [Path(root) for root in code_roots],
                Path(schema_root),
            )
            expected_output_sha256 = sha256_hex(expected_output)
        except Exception:
            failed.append("restore_output_binding_invalid")

    try:
        schemas = bundled_runtime_schema_registry()
        if not code_roots:
            raise ArsError("store code roots are unavailable")
        require_existing_control_root([Path(root) for root in code_roots], target)
        ledger_snapshot = EventLedger(target, receipt.project_id, schemas).snapshot()
        resolver = LedgerAuthorityGrantResolver(
            target,
            receipt.project_id,
            receipt.store_identity,
            schemas,
            approved_witness=approved_witness,
            approved_witness_path=validated_witness_path,
            restore_source_alias=True,
        )
        replay_state = replay(
            ledger_snapshot.events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
        ledger_hash = sha256_hex(canonical_bytes(list(ledger_snapshot.events)))
        if (
            ledger_snapshot.global_position != receipt.canonical_tail_position
            or ledger_snapshot.event_hash != receipt.canonical_tail_hash
        ):
            failed.append("ledger_tail_mismatch")
    except Exception:
        ledger_snapshot = None
        replay_state = {}
        ledger_hash = "0" * 64
        failed.append("ledger_replay_invalid")

    snapshot, snapshot_hash = _read_json(snapshot_path)
    source_snapshot_hash = sha256_hex(canonical_bytes(snapshot)) if snapshot is not None else "0" * 64
    if snapshot is None:
        failed.append("snapshot_binding_mismatch")
    else:
        expected_snapshot = (
            snapshot_hash == receipt.snapshot_hash
            and snapshot.get("snapshot_id") == receipt.snapshot_id
            and snapshot.get("source_position") == receipt.snapshot_source_position
            and snapshot.get("source_hash") == receipt.snapshot_source_hash
            and snapshot.get("state_hash") == receipt.snapshot_state_hash
            and snapshot.get("replay_start_position") == receipt.replay_start_position
            and snapshot.get("replay_end_position") == receipt.replay_end_position
        )
        if not expected_snapshot:
            failed.append("snapshot_binding_mismatch")
        if tuple(snapshot.get("schema_versions", ())) != receipt.schema_versions:
            failed.append("schema_version_unsupported")
        if tuple(snapshot.get("tool_versions", ())) != receipt.tool_versions:
            failed.append("tool_version_unsupported")
        if snapshot.get("state_hash") != sha256_hex(canonical_bytes(replay_state)):
            failed.append("snapshot_state_mismatch")
        if ledger_snapshot is not None and (
            snapshot.get("source_position") != ledger_snapshot.global_position
            or snapshot.get("source_hash") != ledger_snapshot.event_hash
        ):
            failed.append("snapshot_tail_mismatch")

    endpoint, endpoint_hash = _read_json(endpoint_ownership_path)
    if endpoint is None or not (
        endpoint.get("target_root") == str(target)
        and endpoint.get("endpoint_scheme") == receipt.source_endpoint_scheme
        and endpoint.get("owner_actor_id") == actor_id == receipt.verified_by_actor_id
        and endpoint.get("authority_grant_id") == authority_grant_id == receipt.verification_authority_grant_id
        and endpoint.get("observed_at")
    ):
        failed.append("endpoint_authority_mismatch")

    manifest, artefact_manifest_hash = _read_json(artefact_manifest_path)
    observations: list[dict[str, Any]] = []
    rows = manifest.get("artefacts", []) if manifest is not None else []
    if artefact_manifest_hash != receipt.external_artefact_manifest_hash:
        failed.append("artefact_manifest_mismatch")
    for binding in receipt.artefact_bindings:
        row = next(
            (item for item in rows if isinstance(item, dict) and item.get("artefact_id") == binding.artefact_id),
            None,
        )
        path = _inside(target, str(row.get("relative_path", ""))) if row else None
        if (
            row is None
            or row.get("artefact_hash") != binding.artefact_hash
            or row.get("availability_status") != "available"
            or row.get("authority_grant_id") != authority_grant_id
            or not row.get("observed_at")
            or path is None
            or not path.is_file()
            or sha256_hex(path.read_bytes()) != binding.artefact_hash
        ):
            failed.append("artefact_unavailable")
            continue
        observations.append(
            {
                "artefact_id": row["artefact_id"],
                "artefact_hash": row["artefact_hash"],
                "availability_status": row["availability_status"],
                "observed_at": row["observed_at"],
                "authority_grant_id": row["authority_grant_id"],
            }
        )
    availability_hash = sha256_hex(canonical_bytes(observations))
    if receipt.availability_status != "available" or availability_hash != receipt.availability_observation_hash:
        failed.append("availability_observation_mismatch")

    registry_hash = str(getattr(registry, "registry_hash", ""))
    if registry_hash != receipt.evidence_registry_hash:
        failed.append("registry_hash_mismatch")
    try:
        checked = set(registry.checked_locations())
    except (AttributeError, ValueError):
        checked = set()
        failed.append("registered_topology_incomplete")
    if target not in checked or source_root is None or source_root not in checked:
        failed.append("registered_topology_incomplete")
    if actor_id != receipt.verified_by_actor_id or (
        actor_id,
        authority_grant_id,
    ) not in getattr(registry, "verifier_authority_bindings", ()):
        failed.append("verification_authority_mismatch")

    predicates = tuple(sorted(set(failed)))
    result = RestorePreflightResult(
        status="diagnostic_only" if predicates else "verified",
        failed_predicates=predicates,
        receipt_hash=receipt.receipt_hash,
        ledger_hash=ledger_hash,
        snapshot_hash=snapshot_hash,
        target_endpoint_ownership_hash=endpoint_hash,
        artefact_manifest_hash=artefact_manifest_hash,
        availability_observations_hash=availability_hash,
        registry_hash=registry_hash,
        target_root=str(target),
        project_id=actual_project,
        store_identity=actual_store,
        tail_position=(ledger_snapshot.global_position if ledger_snapshot else -1),
        tail_hash=(ledger_snapshot.event_hash if ledger_snapshot else "0" * 64),
        snapshot_id=str(snapshot.get("snapshot_id", "")) if snapshot else "",
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        result_hash="",
        source_root=str(source_root) if source_root is not None else "",
        code_roots=code_roots,
        schema_root=schema_root,
        source_snapshot_hash=source_snapshot_hash,
        target_manifest_bytes_sha256=target_manifest_bytes_sha256,
        expected_output_sha256=expected_output_sha256,
        origin_witness_path=(str(validated_witness_path) if validated_witness_path is not None else ""),
        origin_witness_sha256=approved_witness.raw_sha256 if approved_witness is not None else "",
        origin_initial_control_root=(approved_witness.initial_control_root if approved_witness is not None else ""),
        origin_initial_physical_root_identity=(
            dict(approved_witness.initial_physical_root_identity) if approved_witness is not None else {}
        ),
    )
    return seal_restore_preflight_result(result)


def seal_restore_preflight_result(
    result: RestorePreflightResult,
) -> RestorePreflightResult:
    """Return the result with its canonical content hash populated."""
    return replace(result, result_hash=_hash_without(result, "result_hash"))


def validate_restore_preflight_result(
    result: RestorePreflightResult,
    *,
    current_root: Path,
    project_id: str,
    actor_id: str,
    authority_grant_id: str,
    approved_witness: StoreOriginWitness | None = None,
) -> None:
    """Recheck a preflight result immediately before writer-lock acquisition."""
    if not isinstance(result, RestorePreflightResult):
        raise ArsError("restore preflight result required")
    if result.result_hash != _hash_without(result, "result_hash"):
        raise ArsError("restore preflight result hash mismatch")
    if result.status != "verified" or result.failed_predicates:
        raise ArsError("restore preflight is not verified")
    if Path(result.target_root).resolve(strict=False) != current_root.resolve(strict=False):
        raise ArsError("restore preflight target root mismatch")
    if result.project_id != project_id:
        raise ArsError("restore preflight project mismatch")
    if result.actor_id != actor_id or result.authority_grant_id != authority_grant_id:
        raise ArsError("restore preflight authority mismatch")
    if approved_witness is None:
        raise ArsError("restore preflight requires approved origin witness")
    if (
        result.origin_witness_sha256 != approved_witness.raw_sha256
        or result.origin_initial_control_root != approved_witness.initial_control_root
        or result.origin_initial_physical_root_identity != approved_witness.initial_physical_root_identity
    ):
        raise ArsError("restore preflight origin witness mismatch")
