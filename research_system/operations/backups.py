"""W8 backup receipts and authority-bound restore preflight evidence."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass, field, replace
from typing import Any
from pathlib import Path

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, IntegrityError
from research_system.projection.replay import replay
from research_system.store.identity import (
    StoreOriginWitness,
    _require_physical_disjoint,
    _restore_preflight_anchor,
    canonical_restore_binding_output,
    load_store_manifest_unbound,
    manifest_schema_root,
    validate_approved_origin_witness_path,
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


@dataclass(frozen=True, slots=True)
class RestoreBoundFile:
    """One exact regular file observed by the full restore preflight."""

    relative_path: str
    raw_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class RestoreBoundArtefact:
    """One receipt-bound artefact and its exact manifest observation."""

    artefact_id: str
    relative_path: str
    artefact_sha256: str
    observation_sha256: str


@dataclass(frozen=True, slots=True)
class RestoreAdmissionClosure:
    """Immutable checked-input closure for the bounded locked recheck."""

    target_root: str
    snapshot: RestoreBoundFile
    endpoint_ownership: RestoreBoundFile
    artefact_manifest: RestoreBoundFile
    artefacts: tuple[RestoreBoundArtefact, ...]
    registry: object
    registry_state_sha256: str


@dataclass(frozen=True, slots=True)
class RestoreAdmissionBundle:
    """Full preflight result plus its immutable checked-input closure."""

    result: RestorePreflightResult
    closure: RestoreAdmissionClosure | None


class _RestorePreflightWithClosure(RestorePreflightResult):
    """API-compatible result carrying non-serialized admission state."""

    __slots__ = ("_admission_closure",)


def restore_admission_bundle_for_result(result: RestorePreflightResult) -> RestoreAdmissionBundle:
    """Recover the checked-input bundle carried by a full verifier result."""
    return RestoreAdmissionBundle(
        result=result,
        closure=getattr(result, "_admission_closure", None),
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value.resolve(strict=False))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(item) for item in value), key=canonical_bytes)
    return value


def _registry_state_sha256(registry: object) -> str:
    fields = getattr(registry, "__dataclass_fields__", None)
    if not isinstance(fields, dict):
        raise ArsError("restore registry does not expose immutable state")
    try:
        state = {name: _jsonable(getattr(registry, name)) for name in fields}
        return sha256_hex(canonical_bytes(state))
    except (TypeError, ValueError) as exc:
        raise ArsError("restore registry state is not canonical") from exc


def _strict_relative_path(root: Path, path: Path) -> tuple[Path, str]:
    target = root.resolve(strict=False)
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ArsError("restore input path must be absolute")
    try:
        relative = candidate.relative_to(target)
    except ValueError as exc:
        raise ArsError("restore input path escapes target root") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ArsError("restore input path is not canonical")
    if "\\" in relative.as_posix():
        raise ArsError("restore input path is not canonical")

    current = target
    for part in relative.parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise ArsError("restore input path is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ArsError("restore input path crosses a reparse point")
    if not stat.S_ISREG(metadata.st_mode):
        raise ArsError("restore input path is not a regular file")
    return current, relative.as_posix()


def _read_bound_json(root: Path, path: Path) -> tuple[dict[str, Any] | None, RestoreBoundFile | None]:
    try:
        current, relative = _strict_relative_path(root, path)
        data = current.read_bytes()
        value = json.loads(data.decode("utf-8"))
    except (ArsError, OSError, UnicodeError, json.JSONDecodeError):
        return None, None
    if not isinstance(value, dict):
        return None, None
    return value, RestoreBoundFile(
        relative_path=relative,
        raw_sha256=sha256_hex(data),
        canonical_sha256=sha256_hex(canonical_bytes(value)),
    )


def _read_bound_bytes(root: Path, relative_path: str) -> tuple[bytes, str, tuple[int, int]]:
    if not isinstance(relative_path, str) or "\\" in relative_path:
        raise ArsError("restore artefact path is not canonical")
    relative = Path(relative_path)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ArsError("restore artefact path is not canonical")
    current, canonical_relative = _strict_relative_path(root, root / relative)
    metadata = os.stat(current)
    return current.read_bytes(), canonical_relative, (metadata.st_dev, metadata.st_ino)


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
    _capture_bundle: bool = False,
) -> RestorePreflightResult | RestoreAdmissionBundle:
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
            validated_witness_path, origin_root = validate_approved_origin_witness_path(
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

    snapshot, snapshot_binding = _read_bound_json(target, snapshot_path)
    snapshot_hash = snapshot_binding.raw_sha256 if snapshot_binding is not None else "0" * 64
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

    endpoint, endpoint_binding = _read_bound_json(target, endpoint_ownership_path)
    endpoint_hash = endpoint_binding.raw_sha256 if endpoint_binding is not None else "0" * 64
    if endpoint is None or not (
        endpoint.get("target_root") == str(target)
        and endpoint.get("endpoint_scheme") == receipt.source_endpoint_scheme
        and endpoint.get("owner_actor_id") == actor_id == receipt.verified_by_actor_id
        and endpoint.get("authority_grant_id") == authority_grant_id == receipt.verification_authority_grant_id
        and endpoint.get("observed_at")
    ):
        failed.append("endpoint_authority_mismatch")

    manifest, manifest_binding = _read_bound_json(target, artefact_manifest_path)
    artefact_manifest_hash = manifest_binding.raw_sha256 if manifest_binding is not None else "0" * 64
    observations: list[dict[str, Any]] = []
    rows = manifest.get("artefacts", []) if manifest is not None else []
    bound_artefacts: list[RestoreBoundArtefact] = []
    if artefact_manifest_hash != receipt.external_artefact_manifest_hash:
        failed.append("artefact_manifest_mismatch")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        rows = []
        failed.append("artefact_manifest_mismatch")
    rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        artefact_id = item.get("artefact_id")
        if not isinstance(artefact_id, str) or not artefact_id:
            failed.append("artefact_manifest_mismatch")
            continue
        rows_by_id.setdefault(artefact_id, []).append(item)
    if any(len(items) != 1 for items in rows_by_id.values()):
        failed.append("artefact_manifest_mismatch")
    receipt_ids = [binding.artefact_id for binding in receipt.artefact_bindings]
    if len(receipt_ids) != len(set(receipt_ids)):
        failed.append("artefact_manifest_mismatch")
    bound_paths: set[str] = set()
    bound_identities: set[tuple[int, int]] = set()
    for binding in receipt.artefact_bindings:
        matches = rows_by_id.get(binding.artefact_id, [])
        row = matches[0] if len(matches) == 1 else None
        artefact_bytes: bytes | None = None
        canonical_relative = ""
        physical_identity: tuple[int, int] | None = None
        if row is not None:
            try:
                artefact_bytes, canonical_relative, physical_identity = _read_bound_bytes(
                    target,
                    row.get("relative_path"),
                )
            except (ArsError, OSError, TypeError):
                pass
        if (
            row is None
            or row.get("artefact_hash") != binding.artefact_hash
            or row.get("availability_status") != "available"
            or row.get("authority_grant_id") != authority_grant_id
            or not row.get("observed_at")
            or artefact_bytes is None
            or physical_identity is None
            or sha256_hex(artefact_bytes) != binding.artefact_hash
            or canonical_relative in bound_paths
            or physical_identity in bound_identities
        ):
            failed.append("artefact_unavailable")
            continue
        bound_paths.add(canonical_relative)
        bound_identities.add(physical_identity)
        observation = {
            "artefact_id": row["artefact_id"],
            "artefact_hash": row["artefact_hash"],
            "availability_status": row["availability_status"],
            "observed_at": row["observed_at"],
            "authority_grant_id": row["authority_grant_id"],
        }
        observations.append(observation)
        bound_artefacts.append(
            RestoreBoundArtefact(
                artefact_id=binding.artefact_id,
                relative_path=canonical_relative,
                artefact_sha256=binding.artefact_hash,
                observation_sha256=sha256_hex(canonical_bytes(observation)),
            )
        )
    availability_hash = sha256_hex(canonical_bytes(observations))
    if receipt.availability_status != "available" or availability_hash != receipt.availability_observation_hash:
        failed.append("availability_observation_mismatch")

    registry_hash = str(getattr(registry, "registry_hash", ""))
    try:
        registry_state_sha256 = _registry_state_sha256(registry)
    except ArsError:
        registry_state_sha256 = "0" * 64
        failed.append("registered_topology_incomplete")
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
    sealed = seal_restore_preflight_result(result)
    closure = None
    if (
        sealed.status == "verified"
        and snapshot_binding is not None
        and endpoint_binding is not None
        and manifest_binding is not None
        and len(bound_artefacts) == len(receipt.artefact_bindings)
    ):
        closure = RestoreAdmissionClosure(
            target_root=str(target),
            snapshot=snapshot_binding,
            endpoint_ownership=endpoint_binding,
            artefact_manifest=manifest_binding,
            artefacts=tuple(bound_artefacts),
            registry=registry,
            registry_state_sha256=registry_state_sha256,
        )
    carried = _RestorePreflightWithClosure(**asdict(sealed))
    object.__setattr__(carried, "_admission_closure", closure)
    bundle = RestoreAdmissionBundle(result=carried, closure=closure)
    return bundle if _capture_bundle else carried


def prepare_restore_admission_before_writer_lease(
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
) -> RestoreAdmissionBundle:
    """Run the full preflight once and retain its exact bounded input closure."""
    bundle = verify_restore_before_writer_lease(
        target_root=target_root,
        receipt=receipt,
        snapshot_path=snapshot_path,
        endpoint_ownership_path=endpoint_ownership_path,
        artefact_manifest_path=artefact_manifest_path,
        registry=registry,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        approved_witness=approved_witness,
        approved_witness_path=approved_witness_path,
        _capture_bundle=True,
    )
    if not isinstance(bundle, RestoreAdmissionBundle):
        raise ArsError("restore admission preparation did not return a checked-input bundle")
    return bundle


def revalidate_restore_admission_closure(bundle: RestoreAdmissionBundle) -> None:
    """Recheck the full preflight's bounded mutable inputs under the target lock."""
    closure = bundle.closure
    if closure is None:
        raise ArsError("verified restore admission requires checked-input closure")
    target = Path(closure.target_root)
    for label, expected in (
        ("snapshot", closure.snapshot),
        ("endpoint ownership", closure.endpoint_ownership),
        ("artefact manifest", closure.artefact_manifest),
    ):
        value, observed = _read_bound_json(target, target / Path(expected.relative_path))
        if (
            value is None
            or observed is None
            or observed.raw_sha256 != expected.raw_sha256
            or observed.canonical_sha256 != expected.canonical_sha256
        ):
            raise IntegrityError(f"restore {label} changed after full preflight")
    for expected in closure.artefacts:
        try:
            data, relative, _identity = _read_bound_bytes(target, expected.relative_path)
        except (ArsError, OSError) as exc:
            raise IntegrityError("restore artefact changed after full preflight") from exc
        if relative != expected.relative_path or sha256_hex(data) != expected.artefact_sha256:
            raise IntegrityError("restore artefact changed after full preflight")
    try:
        current_registry_sha256 = _registry_state_sha256(closure.registry)
    except ArsError as exc:
        raise IntegrityError("restore registry changed after full preflight") from exc
    if current_registry_sha256 != closure.registry_state_sha256:
        raise IntegrityError("restore registry changed after full preflight")


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
