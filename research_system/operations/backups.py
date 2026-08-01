"""W8 backup receipts and authority-bound restore preflight evidence."""

from __future__ import annotations

import json
import os
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from typing import Any, Callable, Iterator
from pathlib import Path

from research_system.authority import GrantedPolicyActionIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, IntegrityError, SchemaError
from research_system.projection.replay import replay
from research_system.store.ledger import EventLedger
from research_system.store.identity import (
    load_restore_binding_evidence,
    load_store_manifest,
    load_store_manifest_unbound,
    manifest_schema_root,
    rebind_restored_store,
)
from research_system.store.lock import WriterLock
from research_system.schema_registry import SchemaRegistry, bundled_runtime_schema_registry


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
    code_roots: tuple[str, ...] = ()
    schema_root: str | None = None
    source_snapshot_hash: str = ""
    target_manifest_bytes_sha256: str = ""
    expected_output_sha256: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"verified", "diagnostic_only"}:
            raise ValueError("invalid restore preflight status")
        predicates_empty = not self.failed_predicates
        if (self.status == "verified") != predicates_empty:
            raise ValueError("restore preflight status must match failed predicates")
        if len(set(self.failed_predicates)) != len(self.failed_predicates):
            raise ValueError("restore preflight failed predicates must be unique")
        for field_name in ("source_snapshot_hash", "target_manifest_bytes_sha256", "expected_output_sha256"):
            value = getattr(self, field_name)
            if value and (not isinstance(value, str) or len(value) != 64):
                raise ValueError(f"{field_name} must be a SHA-256 digest")


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


def _tree_digest(root: Path) -> str:
    """Digest a root's complete file/link inventory for restore TOCTOU checks."""
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise IntegrityError(f"restore binding root is not a directory: {resolved}")
    entries: list[dict[str, str]] = []
    for path in sorted(resolved.rglob("*"), key=lambda item: item.relative_to(resolved).as_posix()):
        relative = path.relative_to(resolved).as_posix()
        if path.is_symlink():
            entries.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append({"path": relative, "kind": "file", "sha256": sha256_hex(path.read_bytes())})
        elif path.is_dir():
            entries.append({"path": relative, "kind": "directory"})
        else:
            raise IntegrityError(f"restore binding root contains unsupported entry: {path}")
    return sha256_hex(canonical_bytes(entries))


def _json_file_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"restore binding JSON file is invalid: {path}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise IntegrityError(f"restore binding JSON file is noncanonical: {path}")
    return value, sha256_hex(raw)


def _authority_grant_files_snapshot(root: Path) -> tuple[dict[str, str], ...]:
    directory = root / "objects" / "authority_grant"
    if not directory.is_dir():
        raise IntegrityError("restore binding authority-grant object directory is missing")
    rows: list[dict[str, str]] = []
    for path in sorted(directory.rglob("*.json"), key=lambda item: item.relative_to(root).as_posix()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_hex(path.read_bytes()),
            }
        )
    return tuple(rows)


def capture_restore_binding_snapshot(
    *,
    source_root: Path,
    target_root: Path,
    project_id: str,
    store_identity: str,
    authority_grant_id: str,
    schema_registry: SchemaRegistry,
) -> tuple[dict[str, Any], str]:
    """Capture the immutable source and normalized target facts for one restore."""
    source = source_root.resolve(strict=True)
    target = target_root.resolve(strict=True)
    source_manifest = load_store_manifest(source)
    target_manifest = load_store_manifest_unbound(target)
    if source_manifest.get("project_id") != project_id or target_manifest.get("project_id") != project_id:
        raise IntegrityError("restore binding project identity changed")
    if (
        source_manifest.get("store_identity") != store_identity
        or target_manifest.get("store_identity") != store_identity
    ):
        raise IntegrityError("restore binding store identity changed")
    source_codes = source_manifest.get("code_roots")
    target_codes = target_manifest.get("code_roots")
    if source_codes != target_codes or not isinstance(source_codes, list) or not source_codes:
        raise IntegrityError("restore binding code-root snapshot changed")
    source_schema = manifest_schema_root(source_manifest)
    target_schema = manifest_schema_root(target_manifest)
    if (
        source_schema is None
        or target_schema is None
        or source_schema.resolve(strict=True) != target_schema.resolve(strict=True)
    ):
        raise IntegrityError("restore binding schema-root snapshot changed")
    source_bootstrap, source_bootstrap_bytes_sha256 = _json_file_snapshot(
        source / "manifests" / "authority-bootstrap.json"
    )
    target_bootstrap, target_bootstrap_bytes_sha256 = _json_file_snapshot(
        target / "manifests" / "authority-bootstrap.json"
    )
    if source_bootstrap != target_bootstrap:
        raise IntegrityError("restore binding bootstrap snapshot changed")
    source_identity_bytes = (source / "manifests" / "store-identity.json").read_bytes()
    source_identity_fields = {
        key: value for key, value in source_manifest.items() if key not in {"control_root", "manifest_hash"}
    }
    target_identity_fields = {
        key: value for key, value in target_manifest.items() if key not in {"control_root", "manifest_hash"}
    }
    if source_identity_fields != target_identity_fields:
        raise IntegrityError("restore binding identity snapshot changed")
    source_ledger = EventLedger(source, project_id, schema_registry).snapshot()
    source_events_hash = sha256_hex(canonical_bytes(list(source_ledger.events)))
    target_ledger = EventLedger(target, project_id, schema_registry).snapshot()
    target_events_hash = sha256_hex(canonical_bytes(list(target_ledger.events)))
    source_grants = _authority_grant_files_snapshot(source)
    target_grants = _authority_grant_files_snapshot(target)
    if source_grants != target_grants:
        raise IntegrityError("restore binding authority-grant snapshot changed")
    code_root_values = tuple(str(Path(root).resolve(strict=True)) for root in source_codes)
    target_code_root_values = tuple(str(Path(root).resolve(strict=True)) for root in target_codes)
    schema_root_value = str(source_schema.resolve(strict=True))
    target_schema_root_value = str(target_schema.resolve(strict=True))
    source_code_root_digests = [{"root": root, "sha256": _tree_digest(Path(root))} for root in code_root_values]
    target_code_root_digests = [{"root": root, "sha256": _tree_digest(Path(root))} for root in target_code_root_values]
    source_schema_root_digest = _tree_digest(source_schema)
    target_schema_root_digest = _tree_digest(target_schema)
    snapshot: dict[str, Any] = {
        "schema_id": "ars://internal/restore-binding-source-snapshot",
        "schema_version": "1.0.0",
        "source_root": str(source),
        "target_root": str(target),
        "project_id": project_id,
        "store_identity": store_identity,
        "code_roots": list(code_root_values),
        "schema_root": schema_root_value,
        "target_code_roots": list(target_code_root_values),
        "target_schema_root": target_schema_root_value,
        "source_identity_manifest": {
            "bytes_sha256": sha256_hex(source_identity_bytes),
            "manifest_hash": source_manifest["manifest_hash"],
            "identity_fields_sha256": sha256_hex(canonical_bytes(source_identity_fields)),
            "control_root": source_manifest["control_root"],
        },
        "target_identity_manifest": {
            "identity_fields_sha256": sha256_hex(canonical_bytes(target_identity_fields)),
        },
        "authority_bootstrap": {
            "bytes_sha256": source_bootstrap_bytes_sha256,
            "bootstrap_manifest_sha256": sha256_hex(canonical_bytes(source_bootstrap)),
            "root_grant_id": source_bootstrap["root_grant"]["authority_grant_id"],
            "root_grant_sha256": source_bootstrap["root_grant_sha256"],
            "publication_grant_id": source_bootstrap["publication_grant"]["authority_grant_id"],
            "publication_grant_sha256": source_bootstrap["publication_grant_sha256"],
            "owner_actor_id": source_bootstrap["owner_actor_id"],
        },
        "target_authority_bootstrap_bytes_sha256": target_bootstrap_bytes_sha256,
        "authority_grant_id": authority_grant_id,
        "authority_grant_files": list(source_grants),
        "code_root_digests": source_code_root_digests,
        "schema_root_digest": source_schema_root_digest,
        "target_code_root_digests": target_code_root_digests,
        "target_schema_root_digest": target_schema_root_digest,
        "source_ledger": {
            "tail_position": source_ledger.global_position,
            "tail_hash": source_ledger.event_hash,
            "events_sha256": source_events_hash,
        },
        "target_ledger": {
            "tail_position": target_ledger.global_position,
            "tail_hash": target_ledger.event_hash,
            "events_sha256": target_events_hash,
        },
    }
    return snapshot, sha256_hex(canonical_bytes(snapshot))


@contextmanager
def restore_binding_writer_locks(
    source_root: Path,
    target_root: Path,
    *,
    lock_factory: Callable[..., Any] = WriterLock,
    held_roots: set[Path] | None = None,
) -> Iterator[None]:
    """Hold source and target restore locks in one deterministic order."""
    source = source_root.resolve(strict=False)
    target = target_root.resolve(strict=False)
    held = {root.resolve(strict=False) for root in (held_roots or set())}
    lock_roots = sorted({source, target}, key=str)
    with ExitStack() as stack:
        try:
            for root in lock_roots:
                if root in held:
                    continue
                stack.enter_context(
                    lock_factory(
                        root / "runtime" / "writer.lock",
                        {
                            "operation": "restore-bind",
                            "source_root": str(source),
                            "target_root": str(target),
                        },
                    )
                )
        except OSError as exc:
            raise ArsError("restore binding writer lock unavailable") from exc
        yield


_RESTORE_BINDING_POLICY_ACTION = "bind_restored_control_store"
_RESTORE_BINDING_POLICY_SCHEMA_ID = "ars://core/policy-action/BindRestoredControlStore"
_RESTORE_BINDING_POLICY_SCHEMA_VERSION = "1.0.0"


def _restore_binding_policy_action(
    *,
    project_id: str,
    store_identity: str,
    actor_id: str,
    authority_grant_id: str,
    source_root: Path,
    target_root: Path,
    source_snapshot: dict[str, Any],
    source_snapshot_hash: str,
    code_roots: tuple[str, ...],
    schema_root: str,
    target_manifest_bytes_sha256: str,
    expected_output: bytes | None,
    now: datetime,
) -> dict[str, Any]:
    source = source_root.resolve(strict=False)
    target = target_root.resolve(strict=False)
    if source_snapshot.get("source_root") != str(source) or source_snapshot.get("target_root") != str(target):
        raise ArsError("restore binding policy source snapshot identity mismatch")
    if source_snapshot.get("project_id") != project_id or source_snapshot.get("store_identity") != store_identity:
        raise ArsError("restore binding policy project/store identity mismatch")
    if source_snapshot_hash != sha256_hex(canonical_bytes(source_snapshot)):
        raise ArsError("restore binding policy source snapshot digest mismatch")
    target_code_roots = source_snapshot.get("target_code_roots")
    target_schema_root = source_snapshot.get("target_schema_root")
    if not isinstance(target_code_roots, list) or not isinstance(target_schema_root, str):
        raise ArsError("restore binding policy target root snapshot is incomplete")
    output_hash = sha256_hex(expected_output) if expected_output is not None else ""
    return {
        "schema_id": _RESTORE_BINDING_POLICY_SCHEMA_ID,
        "schema_version": _RESTORE_BINDING_POLICY_SCHEMA_VERSION,
        "policy_action_type": _RESTORE_BINDING_POLICY_ACTION,
        "project_id": project_id,
        "actor_id": actor_id,
        "actor_class": "human",
        "authority_grant_id": authority_grant_id,
        "subject_scope": {"kind": "project_store", "id": project_id},
        "required_risk": "R2",
        "action_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "source_root": str(source),
        "source_store_identity": store_identity,
        "source_code_roots": list(code_roots),
        "source_code_roots_sha256": sha256_hex(canonical_bytes(list(code_roots))),
        "source_schema_root": schema_root,
        "source_schema_root_sha256": str(source_snapshot.get("schema_root_digest", "")),
        "source_snapshot_sha256": source_snapshot_hash,
        "target_root": str(target),
        "target_store_identity": store_identity,
        "target_code_roots": target_code_roots,
        "target_code_roots_sha256": sha256_hex(canonical_bytes(target_code_roots)),
        "target_schema_root": target_schema_root,
        "target_schema_root_sha256": str(source_snapshot.get("target_schema_root_digest", "")),
        "target_manifest_bytes_sha256": target_manifest_bytes_sha256,
        "config_output_sha256": output_hash,
    }


def _resolve_restore_authority(
    *,
    authority_root: Path,
    project_id: str,
    store_identity: str,
    actor_id: str,
    authority_grant_id: str,
    schemas: SchemaRegistry,
    now: datetime,
    source_root: Path,
    target_root: Path,
    source_snapshot: dict[str, Any],
    source_snapshot_hash: str,
    code_roots: tuple[str, ...],
    schema_root: str,
    target_manifest_bytes_sha256: str,
    expected_output: bytes | None,
) -> None:
    binding = schemas.policy_action_binding(_RESTORE_BINDING_POLICY_ACTION)
    if binding is None or (binding.schema_id, binding.schema_version) != (
        _RESTORE_BINDING_POLICY_SCHEMA_ID,
        _RESTORE_BINDING_POLICY_SCHEMA_VERSION,
    ):
        raise ArsError("restore binding policy-action identity is not active; owner decision required")
    action = _restore_binding_policy_action(
        project_id=project_id,
        store_identity=store_identity,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        source_root=source_root,
        target_root=target_root,
        source_snapshot=source_snapshot,
        source_snapshot_hash=source_snapshot_hash,
        code_roots=code_roots,
        schema_root=schema_root,
        target_manifest_bytes_sha256=target_manifest_bytes_sha256,
        expected_output=expected_output,
        now=now,
    )
    identity = schemas.resolve_identity(binding.schema_id, binding.schema_version)
    schemas.validate_active(binding.schema_id, action, schema_version=binding.schema_version)
    resolver = LedgerAuthorityGrantResolver(
        authority_root,
        project_id,
        store_identity,
        schemas,
    )
    resolver.resolve_policy_action(
        authority_grant_id,
        actor_id,
        "human",
        GrantedPolicyActionIdentity(
            _RESTORE_BINDING_POLICY_ACTION,
            identity.schema_id,
            str(identity.schema_version),
            identity.sha256,
        ),
        "R2",
        project_id,
        "project_store",
        project_id,
        now,
    )


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
    source_root: Path | None = None,
    schema_registry: SchemaRegistry | None = None,
    now: datetime | None = None,
    expected_output: bytes | None = None,
) -> RestorePreflightResult:
    """Independently inspect a moved store and derive a pre-writer result."""
    target = target_root.resolve(strict=False)
    schemas = schema_registry or bundled_runtime_schema_registry()
    trusted_now = now or datetime.now(UTC)
    requested_source = source_root.resolve(strict=False) if source_root is not None else None
    failed: list[str] = []
    if receipt.receipt_hash != _hash_without(receipt, "receipt_hash"):
        failed.append("receipt_hash_mismatch")

    identity, target_manifest_bytes_sha256 = _read_json(target / "manifests" / "store-identity.json")
    actual_project = receipt.project_id
    actual_store = receipt.store_identity
    source_root: Path | None = None
    source_root_value = ""
    code_roots: tuple[str, ...] = ()
    schema_root: str | None = None
    binding_evidence: dict[str, Any] | None = None
    if identity is None:
        failed.append("store_identity_manifest_invalid")
    else:
        try:
            raw_identity = (target / "manifests" / "store-identity.json").read_bytes()
            if raw_identity != canonical_bytes(identity):
                failed.append("store_identity_manifest_invalid")
        except OSError:
            failed.append("store_identity_manifest_invalid")
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
            recorded_root = identity.get("control_root")
            if not isinstance(recorded_root, str) or not Path(recorded_root).is_absolute():
                raise ValueError("invalid source root")
            recorded_source = Path(recorded_root).resolve(strict=False)
            source_root = recorded_source
            source_root_value = str(recorded_source)
            recorded_codes = identity.get("code_roots")
            if (
                not isinstance(recorded_codes, list)
                or not recorded_codes
                or any(not isinstance(root, str) or not Path(root).is_absolute() for root in recorded_codes)
            ):
                raise ValueError("invalid code roots")
            code_roots = tuple(recorded_codes)
            persisted_schema_root = manifest_schema_root(identity)
            schema_root = str(persisted_schema_root) if persisted_schema_root is not None else None
        except (OSError, ValueError, ArsError):
            failed.append("source_root_invalid")
        if (
            source_root is not None
            and requested_source is not None
            and source_root != target
            and source_root != requested_source
        ):
            failed.append("restore_source_binding_mismatch")
        if source_root == target:
            binding_evidence = load_restore_binding_evidence(target)
            if binding_evidence is None:
                failed.append("store_not_moved")
            elif requested_source is None:
                failed.append("restore_source_proof_missing")
            else:
                source_root = requested_source
                source_root_value = str(source_root)
                if (
                    binding_evidence["source_root"] != source_root_value
                    or binding_evidence["receipt_hash"] != receipt.receipt_hash
                    or binding_evidence["project_id"] != actual_project
                    or binding_evidence["store_identity"] != actual_store
                    or binding_evidence["manifest_hash"] != identity.get("manifest_hash")
                    or binding_evidence["target_manifest_bytes_sha256"] != target_manifest_bytes_sha256
                ):
                    failed.append("restore_binding_evidence_mismatch")
        elif requested_source is not None:
            if source_root != requested_source:
                failed.append("restore_source_binding_mismatch")
            source_root = requested_source
            source_root_value = str(source_root)
        elif source_root is None:
            failed.append("restore_source_proof_missing")

    try:
        ledger_snapshot = EventLedger(target, receipt.project_id, schemas).snapshot()
        authority_root = source_root if source_root is not None and source_root != target else target
        authority_resolver = LedgerAuthorityGrantResolver(
            authority_root,
            receipt.project_id,
            receipt.store_identity,
            schemas,
        )
        replay_state = replay(
            ledger_snapshot.events,
            schema_registry=schemas,
            authority_state_validator=authority_resolver.validate_replayed_administration_state,
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

    source_snapshot: dict[str, Any] | None = None
    source_snapshot_hash = ""
    if source_root is not None and identity is not None:
        try:
            source_snapshot, source_snapshot_hash = capture_restore_binding_snapshot(
                source_root=source_root,
                target_root=target,
                project_id=actual_project,
                store_identity=actual_store,
                authority_grant_id=authority_grant_id,
                schema_registry=schemas,
            )
            if binding_evidence is not None and (
                binding_evidence["source_snapshot_hash"] != source_snapshot_hash
                or binding_evidence["source_snapshot"] != source_snapshot
            ):
                failed.append("restore_binding_evidence_mismatch")
        except (ArsError, OSError, ValueError, UnicodeError):
            failed.append("source_snapshot_mismatch")
    else:
        failed.append("source_snapshot_mismatch")

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
    if source_root is None or source_snapshot is None or schema_root is None:
        failed.append("verification_authority_mismatch")
    else:
        try:
            _resolve_restore_authority(
                authority_root=(source_root if source_root != target else target),
                project_id=actual_project,
                store_identity=actual_store,
                actor_id=actor_id,
                authority_grant_id=authority_grant_id,
                schemas=schemas,
                now=trusted_now,
                source_root=source_root,
                target_root=target,
                source_snapshot=source_snapshot,
                source_snapshot_hash=source_snapshot_hash,
                code_roots=code_roots,
                schema_root=schema_root,
                target_manifest_bytes_sha256=target_manifest_bytes_sha256,
                expected_output=expected_output,
            )
        except (ArsError, IntegrityError, OSError, ValueError, SchemaError) as exc:
            if "owner decision" in str(exc):
                failed.append("restore_binding_authority_unavailable")
            else:
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
        source_root=source_root_value,
        code_roots=code_roots,
        schema_root=schema_root,
        source_snapshot_hash=source_snapshot_hash,
        target_manifest_bytes_sha256=target_manifest_bytes_sha256,
        expected_output_sha256=sha256_hex(expected_output) if expected_output is not None else "",
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
    if not result.source_snapshot_hash:
        raise ArsError("restore preflight source snapshot is missing")
    if not result.target_manifest_bytes_sha256:
        raise ArsError("restore preflight target manifest snapshot is missing")


def finalize_verified_restore_binding(
    *,
    target_root: Path,
    source_root: Path,
    supplied: RestorePreflightResult,
    current: RestorePreflightResult,
    project_id: str,
    actor_id: str,
    authority_grant_id: str,
    schema_registry: SchemaRegistry | None = None,
    now: datetime | None = None,
    expected_output: bytes | None = None,
) -> dict[str, Any]:
    """Finalize a verified restore after the caller's current writer-lock recheck.

    The caller must invoke this while holding the store ``WriterLock`` and only
    after independently deriving ``current`` from the live target.  No domain
    mutation belongs before this call succeeds.
    """
    validate_restore_preflight_result(
        supplied,
        current_root=target_root,
        project_id=project_id,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
    )
    validate_restore_preflight_result(
        current,
        current_root=target_root,
        project_id=project_id,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
    )
    if current != supplied:
        raise ArsError("restore preflight changed before binding finalization")
    if not current.source_root or Path(current.source_root).resolve(strict=False) != source_root.resolve(strict=False):
        raise ArsError("restore source binding mismatch")
    if not current.code_roots:
        raise ArsError("restore code-root binding missing")
    expected_output_hash = sha256_hex(expected_output) if expected_output is not None else ""
    if current.expected_output_sha256 != expected_output_hash:
        raise ArsError("restore output binding changed before finalization")
    schemas = schema_registry or bundled_runtime_schema_registry()
    expected_schema_root = Path(current.schema_root) if current.schema_root else None
    if expected_schema_root is None:
        raise ArsError("restore schema-root binding missing")
    trusted_now = now or datetime.now(UTC)
    source_snapshot, source_snapshot_hash = capture_restore_binding_snapshot(
        source_root=source_root,
        target_root=target_root,
        project_id=project_id,
        store_identity=current.store_identity,
        authority_grant_id=authority_grant_id,
        schema_registry=schemas,
    )
    if source_snapshot_hash != current.source_snapshot_hash:
        raise ArsError("restore source snapshot changed before binding finalization")

    def revalidate_source_snapshot() -> None:
        try:
            live_snapshot, live_hash = capture_restore_binding_snapshot(
                source_root=source_root,
                target_root=target_root,
                project_id=project_id,
                store_identity=current.store_identity,
                authority_grant_id=authority_grant_id,
                schema_registry=schemas,
            )
            live_target_manifest_bytes_sha256 = sha256_hex(
                (target_root.resolve(strict=True) / "manifests" / "store-identity.json").read_bytes()
            )
        except (ArsError, OSError, ValueError, UnicodeError) as exc:
            raise ArsError("restore source snapshot changed before manifest replacement") from exc
        if (
            live_hash != current.source_snapshot_hash
            or live_target_manifest_bytes_sha256 != current.target_manifest_bytes_sha256
        ):
            raise ArsError("restore source snapshot changed before manifest replacement")
        _resolve_restore_authority(
            authority_root=(
                source_root if source_root.resolve(strict=False) != target_root.resolve(strict=False) else target_root
            ),
            project_id=project_id,
            store_identity=current.store_identity,
            actor_id=actor_id,
            authority_grant_id=authority_grant_id,
            schemas=schemas,
            now=trusted_now,
            source_root=source_root,
            target_root=target_root,
            source_snapshot=live_snapshot,
            source_snapshot_hash=live_hash,
            code_roots=current.code_roots,
            schema_root=str(expected_schema_root),
            target_manifest_bytes_sha256=live_target_manifest_bytes_sha256,
            expected_output=expected_output,
        )

    return rebind_restored_store(
        target_root,
        source_root,
        expected_project_id=project_id,
        expected_store_identity=current.store_identity,
        expected_code_roots=[Path(root) for root in current.code_roots],
        expected_schema_root=expected_schema_root,
        expected_restore_receipt_hash=current.receipt_hash,
        source_snapshot=source_snapshot,
        expected_source_snapshot_hash=current.source_snapshot_hash,
        expected_target_manifest_bytes_sha256=current.target_manifest_bytes_sha256,
        expected_output=expected_output,
        source_snapshot_validator=revalidate_source_snapshot,
    )
