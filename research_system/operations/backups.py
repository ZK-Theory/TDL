"""W8 backup receipts and authority-bound restore preflight evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Any
from pathlib import Path

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError
from research_system.projection.replay import replay
from research_system.store.ledger import EventLedger


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
) -> RestorePreflightResult:
    """Independently inspect a moved store and derive a pre-writer result."""
    target = target_root.resolve(strict=False)
    failed: list[str] = []
    if receipt.receipt_hash != _hash_without(receipt, "receipt_hash"):
        failed.append("receipt_hash_mismatch")

    identity, _ = _read_json(target / "manifests" / "store-identity.json")
    actual_project = receipt.project_id
    actual_store = receipt.store_identity
    source_root: Path | None = None
    if identity is None:
        failed.append("store_identity_manifest_invalid")
    else:
        recorded_hash = identity.get("manifest_hash")
        unsigned = {key: value for key, value in identity.items() if key != "manifest_hash"}
        if recorded_hash != sha256_hex(canonical_bytes(unsigned)):
            failed.append("store_identity_manifest_invalid")
        actual_project = str(identity.get("project_id", ""))
        actual_store = str(identity.get("store_identity", ""))
        if actual_project != receipt.project_id:
            failed.append("project_identity_mismatch")
        if actual_store != receipt.store_identity:
            failed.append("store_identity_mismatch")
        if identity.get("endpoint_scheme") != receipt.source_endpoint_scheme:
            failed.append("endpoint_scheme_mismatch")
        try:
            source_root = Path(str(identity.get("control_root"))).resolve(strict=False)
        except OSError:
            failed.append("source_root_invalid")
        if source_root == target:
            failed.append("store_not_moved")

    try:
        ledger_snapshot = EventLedger(target, receipt.project_id).snapshot()
        replay_state = replay(ledger_snapshot.events)
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
        and endpoint.get("authority_grant_id")
        == authority_grant_id
        == receipt.verification_authority_grant_id
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
            (
                item
                for item in rows
                if isinstance(item, dict) and item.get("artefact_id") == binding.artefact_id
            ),
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
    if (
        receipt.availability_status != "available"
        or availability_hash != receipt.availability_observation_hash
    ):
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