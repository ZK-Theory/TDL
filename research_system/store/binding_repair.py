"""Owner-governed bootstrap repair for a stale store code/schema binding.

This module deliberately does not load :class:`ControlBinding`: that loader is
the capability being repaired.  It consumes only owner intent, immutable
foundation identity pins, the origin witness, and independently derived
candidate repository facts.
"""

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from research_system.authority import _validate_bootstrap, authority_bootstrap_sha256
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.git_execution import run_git
from research_system.git_provenance import read_exact_committed_physical_file as _committed_candidate_file
from research_system.ids import validate_id
from research_system.schema_registry import runtime_schema_registry
from research_system.store.contained_files import (
    publish_contained_exact_no_replace,
    replace_contained_exact_predecessor,
)
from research_system.store.durability import fsync_directory
from research_system.store.identity import (
    _require_physical_directory,
    _require_physical_regular_file,
    _restored_manifest_hash,
    load_store_manifest,
    load_store_manifest_unbound,
    load_store_origin_witness,
    manifest_schema_root,
)
from research_system.store.ledger import EventLedger, _issue_validated_service_session
from research_system.store.lock import WriterLock
from research_system.store.receipts import ReceiptStore


COMMAND_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/command/RepairStoreBinding"
EVENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired"
OBJECT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/object/StoreBindingRepair"
RECEIPT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair"
ADVANCE_RECEIPT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingAdvance"
ADVANCE_COMMAND_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/command/AdvanceStoreBinding"
ADVANCE_INTENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/intent/AdvanceStoreBinding"
ADVANCE_EVENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/event/StoreBindingAdvanced"
ADVANCE_OBJECT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/object/StoreBindingAdvance"
RECOVERY_BINDING_SCHEMA_ID = "ars://internal/store-binding-recovery"
RECOVERY_BINDING_NAME = "binding-repair-current.json"
_MARKER_NAME = ".binding-repair-transaction.json"
_STORE_MANIFEST = Path("manifests/store-identity.json")
_RESTORE_TRANSACTION = Path("manifests/.restore-binding-transaction.json")
_ROUTE_RELATIVE = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_SPEC_SOURCE_RELATIVES = (
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md"),
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md"),
)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _parse_time(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ConfigurationError(f"{field} must be a finite UTC RFC 3339 time")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ConfigurationError(f"{field} must be a finite UTC RFC 3339 time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ConfigurationError(f"{field} must be UTC")
    return parsed


def _run_git(root: Path, *arguments: str) -> str:
    result = run_git(
        root,
        *arguments,
        unavailable_message="candidate Git inspection timed out or is unavailable",
    )
    if result.returncode != 0:
        raise ConfigurationError(f"candidate Git inspection failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _governed_schema_catalogue(candidate: Path, schema_root: Path, *, label: str) -> str:
    """Return a catalogue digest only for physical schema files at exact ``HEAD``.

    The runtime registry consumes every ``*.schema.json`` leaf below this root.
    A clean Git worktree alone does not establish that those bytes are the
    committed subject: a committed symlink can keep its target outside the
    repository, and a later target mutation is invisible to Git.  Bind each
    input individually before constructing the aggregate digest.
    """
    expected_root = candidate / ".research-system" / "schemas"
    physical_root = _require_physical_directory(schema_root, label=f"{label} root")
    if schema_root != expected_root or physical_root != expected_root:
        raise IntegrityError(f"{label} root is not candidate-owned")
    records: list[dict[str, str]] = []
    for path in sorted(schema_root.rglob("*.schema.json"), key=lambda item: item.as_posix()):
        relative = path.relative_to(candidate)
        raw = _committed_candidate_file(candidate, relative, label=f"{label} file")
        records.append(
            {
                "path": path.relative_to(schema_root).as_posix(),
                "sha256": sha256_hex(raw),
            }
        )
    return sha256_hex(canonical_bytes(records))


def _read_canonical_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"invalid {label}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise IntegrityError(f"{label} is not canonical JSON")
    return value, raw


def _physical_artifact_path(control_root: Path, path: Path, *, create_parent: bool) -> Path:
    root = control_root.resolve(strict=True)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise IntegrityError("binding-repair artifact escapes the control root") from exc
    current = root
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if not create_parent:
                raise IntegrityError("binding-repair artifact parent is unavailable") from None
            try:
                current.mkdir()
                metadata = current.lstat()
            except OSError as exc:
                raise IntegrityError("binding-repair artifact parent is unavailable") from exc
        except OSError as exc:
            raise IntegrityError("binding-repair artifact parent is unavailable") from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise IntegrityError("binding-repair artifact parent is redirected")
    target = current / relative.name
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        return target
    except OSError as exc:
        raise IntegrityError("binding-repair artifact identity is unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & reparse
    ):
        raise IntegrityError("binding-repair artifact is redirected")
    return target


def _publish(control_root: Path, path: Path, data: bytes) -> None:
    control = control_root.resolve(strict=True)
    path = _physical_artifact_path(control, path, create_parent=True)
    publish_contained_exact_no_replace(
        control,
        path.relative_to(control).as_posix(),
        data,
        conflict_message=f"published binding-repair artifact conflicts: {path.name}",
    )
    path = _physical_artifact_path(control, path, create_parent=False)
    if path.read_bytes() != data:
        raise IntegrityError("binding-repair artifact publication is not exact")


def _replace(control_root: Path, path: Path, data: bytes, *, expected: bytes | None = None) -> None:
    """Durably replace a binding leaf and reconcile an exact interrupted replacement."""
    control = control_root.resolve(strict=True)
    path = _physical_artifact_path(control, path, create_parent=False)
    current: bytes | None
    try:
        current = path.read_bytes()
    except FileNotFoundError as exc:
        if expected is None:
            raise IntegrityError("binding-repair artifact is unavailable for replacement") from exc
        # A hard stop after predecessor removal has no final leaf.  The shared
        # exact-predecessor protocol recognizes and reconciles only its own
        # deterministic stage/backup state; a wholly absent leaf still fails
        # closed there.
        current = None
        predecessor = expected
    except OSError as exc:
        raise IntegrityError("binding-repair artifact is unavailable for replacement") from exc
    else:
        predecessor = current if expected is None else expected
    if current is not None and current not in {predecessor, data}:
        raise ConflictError(f"binding-repair artifact replacement conflicts: {path.name}")
    if current == data and expected is None:
        return
    replace_contained_exact_predecessor(
        control,
        path.relative_to(control).as_posix(),
        data,
        expected=predecessor,
        conflict_message=f"binding-repair artifact replacement conflicts: {path.name}",
    )
    path = _physical_artifact_path(control, path, create_parent=False)
    if path.read_bytes() != data:
        raise IntegrityError("binding-repair artifact replacement is not exact")


@dataclass(frozen=True)
class RepairStoreBinding:
    """Meaningful owner intent; all evidence identities are runtime-derived."""

    control_root: Path
    candidate_repository_root: Path
    expected_project_id: str
    expected_store_identity: str
    expected_origin_authority_root: Path
    expected_origin_witness_sha256: str
    intended_schema_root: Path
    stale_evidence_refs: tuple[str, ...]
    spec_route_ref: str
    spec_source_refs: tuple[str, str]
    valid_from: str
    expires_at: str
    owner_actor_id: str
    owner_action: str
    idempotency_key: str
    reason: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RepairStoreBinding":
        required = {
            "schema_id",
            "schema_version",
            "command_type",
            "control_root",
            "candidate_repository_root",
            "expected_project_id",
            "expected_store_identity",
            "expected_origin_authority_root",
            "expected_origin_witness_sha256",
            "intended_schema_root",
            "stale_evidence_refs",
            "spec_route_ref",
            "spec_source_refs",
            "valid_from",
            "expires_at",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "reason",
        }
        if set(value) != required:
            raise ConfigurationError("RepairStoreBinding intent fields are not exact")
        if value.get("schema_id") != COMMAND_SCHEMA_ID or value.get("schema_version") != "1.0.0":
            raise ConfigurationError("RepairStoreBinding intent schema is unsupported")
        if value.get("command_type") != "RepairStoreBinding":
            raise ConfigurationError("raw generic command forgery is not admitted")
        stale = value.get("stale_evidence_refs")
        sources = value.get("spec_source_refs")
        if not isinstance(stale, list) or not stale or not all(isinstance(item, str) and item for item in stale):
            raise ConfigurationError("stale evidence refs are required")
        if (
            not isinstance(sources, list)
            or len(sources) != 2
            or set(sources)
            != {
                ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
                ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
            }
        ):
            raise ConfigurationError("exact SPEC-01/SPEC-02 source refs are required")
        text_fields = (
            "expected_store_identity",
            "expected_origin_witness_sha256",
            "spec_route_ref",
            "valid_from",
            "expires_at",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "reason",
        )
        if any(not isinstance(value.get(field), str) or not value[field].strip() for field in text_fields):
            raise ConfigurationError("RepairStoreBinding intent contains an empty field")
        return cls(
            Path(str(value["control_root"])),
            Path(str(value["candidate_repository_root"])),
            validate_id(str(value["expected_project_id"]), "project"),
            str(value["expected_store_identity"]),
            Path(str(value["expected_origin_authority_root"])),
            str(value["expected_origin_witness_sha256"]),
            Path(str(value["intended_schema_root"])),
            tuple(stale),
            str(value["spec_route_ref"]),
            (str(sources[0]), str(sources[1])),
            str(value["valid_from"]),
            str(value["expires_at"]),
            validate_id(str(value["owner_actor_id"]), "actor"),
            str(value["owner_action"]),
            str(value["idempotency_key"]),
            str(value["reason"]),
        )

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "control_root": str(self.control_root),
            "candidate_repository_root": str(self.candidate_repository_root),
            "expected_project_id": self.expected_project_id,
            "expected_store_identity": self.expected_store_identity,
            "expected_origin_authority_root": str(self.expected_origin_authority_root),
            "expected_origin_witness_sha256": self.expected_origin_witness_sha256,
            "intended_schema_root": str(self.intended_schema_root),
            "stale_evidence_refs": list(self.stale_evidence_refs),
            "spec_route_ref": self.spec_route_ref,
            "spec_source_refs": list(self.spec_source_refs),
            "valid_from": self.valid_from,
            "expires_at": self.expires_at,
            "owner_actor_id": self.owner_actor_id,
            "owner_action": self.owner_action,
            "idempotency_key": self.idempotency_key,
            "reason": self.reason,
        }


def read_repair_intent(path: Path) -> RepairStoreBinding:
    value, _raw = _read_canonical_json(path, "RepairStoreBinding intent")
    return RepairStoreBinding.from_mapping(value)


@dataclass(frozen=True)
class AdvanceStoreBinding:
    """Semantic owner intent for one clean descendant binding advance."""

    control_root: Path
    candidate_repository_root: Path
    expected_project_id: str
    expected_store_identity: str
    expected_origin_authority_root: Path
    expected_origin_witness_sha256: str
    intended_schema_root: Path
    valid_from: str
    expires_at: str
    owner_actor_id: str
    owner_action: str
    idempotency_key: str
    reason: str
    expected_predecessor_binding_sha256: str | None = None
    expected_candidate_git_head: str | None = None
    expected_predecessor_route_sha256: str | None = None
    expected_successor_route_sha256: str | None = None
    input_schema_id: str = ADVANCE_INTENT_SCHEMA_ID
    input_schema_version: str = "1.0.0"

    @property
    def spec_route_ref(self) -> str:
        return _ROUTE_RELATIVE.as_posix()

    @property
    def spec_source_refs(self) -> tuple[str, str]:
        return (
            ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
            ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
        )

    def semantic_payload(self) -> dict[str, Any]:
        names = (
            "control_root",
            "candidate_repository_root",
            "expected_project_id",
            "expected_store_identity",
            "expected_origin_authority_root",
            "expected_origin_witness_sha256",
            "intended_schema_root",
            "valid_from",
            "expires_at",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "reason",
        )
        payload = {name: str(value) if isinstance(value := getattr(self, name), Path) else value for name in names}
        route_successor = {
            "expected_predecessor_binding_sha256": self.expected_predecessor_binding_sha256,
            "expected_candidate_git_head": self.expected_candidate_git_head,
            "expected_predecessor_route_sha256": self.expected_predecessor_route_sha256,
            "expected_successor_route_sha256": self.expected_successor_route_sha256,
        }
        if any(value is not None for value in route_successor.values()):
            payload.update(route_successor)
        return payload

    def input_mapping(self) -> dict[str, Any]:
        """Return the canonical flat public intent document."""

        return {
            "schema_id": self.input_schema_id,
            "schema_version": self.input_schema_version,
            "command_type": "AdvanceStoreBinding",
            **self.semantic_payload(),
        }

    def route_successor_binding(self) -> dict[str, str] | None:
        fields = {
            "predecessor_binding_sha256": self.expected_predecessor_binding_sha256,
            "candidate_git_head": self.expected_candidate_git_head,
            "predecessor_route_sha256": self.expected_predecessor_route_sha256,
            "successor_route_sha256": self.expected_successor_route_sha256,
        }
        if all(value is None for value in fields.values()):
            return None
        if not all(isinstance(value, str) and value for value in fields.values()):
            raise ConfigurationError("AdvanceStoreBinding route successor bindings must be complete")
        return {name: str(value) for name, value in fields.items()}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AdvanceStoreBinding":
        payload = dict(value)
        input_schema_id = payload.pop("schema_id", None)
        input_schema_version = payload.pop("schema_version", None)
        if (
            input_schema_id not in {ADVANCE_INTENT_SCHEMA_ID, ADVANCE_COMMAND_SCHEMA_ID}
            or input_schema_version != "1.0.0"
        ):
            raise ConfigurationError("AdvanceStoreBinding intent schema is unsupported")
        if payload.pop("command_type", None) != "AdvanceStoreBinding":
            raise ConfigurationError("raw generic command forgery is not admitted")
        base_fields = {
            "control_root",
            "candidate_repository_root",
            "expected_project_id",
            "expected_store_identity",
            "expected_origin_authority_root",
            "expected_origin_witness_sha256",
            "intended_schema_root",
            "valid_from",
            "expires_at",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "reason",
        }
        route_fields = {
            "expected_predecessor_binding_sha256",
            "expected_candidate_git_head",
            "expected_predecessor_route_sha256",
            "expected_successor_route_sha256",
        }
        payload_fields = frozenset(payload)
        if payload_fields not in {frozenset(base_fields), frozenset(base_fields | route_fields)}:
            raise ConfigurationError("AdvanceStoreBinding intent fields are not exact")
        route_successor = route_fields <= payload_fields
        if (route_successor and payload.get("owner_action") != "advance-reviewed-route-successor-store-binding") or (
            not route_successor and payload.get("owner_action") != "advance-clean-descendant-store-binding"
        ):
            raise ConfigurationError("AdvanceStoreBinding owner action does not match its exact intent shape")
        if input_schema_id == ADVANCE_COMMAND_SCHEMA_ID and route_successor:
            raise ConfigurationError("legacy AdvanceStoreBinding identity cannot authorize a route successor")
        for field in (
            "control_root",
            "candidate_repository_root",
            "expected_origin_authority_root",
            "intended_schema_root",
        ):
            payload[field] = Path(str(payload[field]))
        payload["expected_project_id"] = validate_id(str(payload["expected_project_id"]), "project")
        payload["owner_actor_id"] = validate_id(str(payload["owner_actor_id"]), "actor")
        return cls(
            **payload,
            input_schema_id=str(input_schema_id),
            input_schema_version=str(input_schema_version),
        )


def read_advance_intent(path: Path) -> AdvanceStoreBinding:
    value, _raw = _read_canonical_json(path, "AdvanceStoreBinding intent")
    intent = AdvanceStoreBinding.from_mapping(value)
    if intent.input_schema_id == ADVANCE_INTENT_SCHEMA_ID:
        from research_system.schema_registry import bundled_schema_registry

        bundled_schema_registry().validate(
            ADVANCE_INTENT_SCHEMA_ID,
            value,
            schema_version=intent.input_schema_version,
        )
    return intent


def _foundation_pins(
    repository: Path,
    intent: RepairStoreBinding | AdvanceStoreBinding,
) -> tuple[dict[str, Any], Any, Path]:
    path = repository / ".research-system" / "config" / "foundation.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError("canonical foundation pins are unavailable") from exc
    if not isinstance(value, dict) or value.get("binding_source") != "store-recovery":
        raise ConfigurationError("foundation does not explicitly authorize store recovery binding")
    fixed = {
        "project_id": intent.expected_project_id,
        "control_root": str(intent.control_root),
        "store_identity": intent.expected_store_identity,
        "origin_authority_root": str(intent.expected_origin_authority_root),
        "origin_witness_sha256": intent.expected_origin_witness_sha256,
    }
    if any(str(value.get(field)) != expected for field, expected in fixed.items()):
        raise IntegrityError("repair intent differs from immutable foundation identity")
    witness_path = Path(str(value.get("origin_witness_path")))
    witness = load_store_origin_witness(witness_path, expected_sha256=intent.expected_origin_witness_sha256)
    if witness.project_id != intent.expected_project_id or witness.store_identity != intent.expected_store_identity:
        raise IntegrityError("origin witness identity differs from repair intent")
    return value, witness, witness_path


def _candidate_evidence(intent: RepairStoreBinding | AdvanceStoreBinding) -> dict[str, Any]:
    candidate = intent.candidate_repository_root.resolve(strict=True)
    if (
        candidate != intent.candidate_repository_root
        or Path(_run_git(candidate, "rev-parse", "--show-toplevel")).resolve(strict=True) != candidate
    ):
        raise ConfigurationError("candidate repository root is moved or aliased")
    if _run_git(candidate, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ConflictError("candidate repository contains dirty or uncommitted state")
    head = _run_git(candidate, "rev-parse", "HEAD")
    tree = _run_git(candidate, "rev-parse", "HEAD^{tree}")
    schema_root = intent.intended_schema_root.resolve(strict=True)
    if schema_root != candidate / ".research-system" / "schemas" or not schema_root.is_dir():
        raise ConfigurationError("intended schema root is not the candidate repository schema root")
    route_ref = Path(intent.spec_route_ref)
    if route_ref != _ROUTE_RELATIVE:
        raise ConfigurationError("SPEC route ref is not the governed route package")
    try:
        route_raw = _committed_candidate_file(candidate, route_ref, label="SPEC route package")
        route = json.loads(route_raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("invalid SPEC route package") from exc
    if not isinstance(route, dict):
        raise IntegrityError("invalid SPEC route package")
    if route.get("route_id") != "SPEC-GATE6-RUN-V1" or route.get("execution_authorized") is not False:
        raise IntegrityError("SPEC route authority state is invalid")
    source_by_locator = {item.get("locator"): item for item in route.get("sources", []) if isinstance(item, dict)}
    sources: list[dict[str, Any]] = []
    for reference in intent.spec_source_refs:
        record = source_by_locator.get(reference)
        raw = _committed_candidate_file(candidate, Path(reference), label="SPEC route source")
        if not record or len(raw) != record.get("size_bytes") or sha256_hex(raw) != record.get("sha256"):
            raise IntegrityError("SPEC route/source SHA mismatch")
        sources.append({"ref": reference, "sha256": sha256_hex(raw), "size_bytes": len(raw)})
    catalogue_sha256 = _governed_schema_catalogue(candidate, schema_root, label="candidate schema catalogue")
    schemas = runtime_schema_registry(schema_root)
    for schema_id in (
        COMMAND_SCHEMA_ID,
        EVENT_SCHEMA_ID,
        OBJECT_SCHEMA_ID,
        RECEIPT_SCHEMA_ID,
        ADVANCE_RECEIPT_SCHEMA_ID,
    ):
        schemas.resolve_identity(schema_id, "1.0.0")
    return {
        "repository_root": str(candidate),
        "git_head": head,
        "git_tree": tree,
        "git_clean": True,
        "schema_root": str(schema_root),
        "schema_catalogue_sha256": catalogue_sha256,
        "route": {"ref": route_ref.as_posix(), "sha256": sha256_hex(route_raw)},
        "sources": sources,
    }


def _validate_owner_authority(control: Path, intent: RepairStoreBinding | AdvanceStoreBinding) -> None:
    manifest = load_store_manifest_unbound(control)
    bootstrap, _raw = _read_canonical_json(
        control / "manifests" / "authority-bootstrap.json", "authority bootstrap manifest"
    )
    try:
        validated, _root, _publication = _validate_bootstrap(bootstrap, intent.expected_project_id)
    except (TypeError, ValueError) as exc:
        raise IntegrityError("authority bootstrap manifest is invalid") from exc
    if (
        authority_bootstrap_sha256(validated) != manifest.get("bootstrap_manifest_sha256")
        or validated.get("owner_actor_id") != intent.owner_actor_id
    ):
        raise IntegrityError("binding command actor is not the immutable authority owner")


def _validate_stale_store(
    intent: RepairStoreBinding, witness: Any, witness_path: Path
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    control = intent.control_root.resolve(strict=True)
    if control != intent.control_root:
        raise ConfigurationError("control root is moved or aliased")
    manifest = load_store_manifest_unbound(control)
    if (
        manifest.get("control_root") != str(intent.control_root)
        or manifest.get("project_id") != intent.expected_project_id
    ):
        raise IntegrityError("control root or project identity mismatch")
    if manifest.get("store_identity") != intent.expected_store_identity:
        raise IntegrityError("store identity mismatch")
    manifest_path = control / _STORE_MANIFEST
    manifest_value, manifest_raw = _read_canonical_json(manifest_path, "store manifest")
    restore_path = _require_physical_regular_file(
        control / _RESTORE_TRANSACTION,
        label="cleared restore transaction",
    )
    restore, _restore_raw = _read_canonical_json(restore_path, "cleared restore transaction")
    if manifest_value != manifest or manifest.get("manifest_hash") != _restored_manifest_hash(
        manifest, str(restore.get("approval_sha256"))
    ):
        raise IntegrityError("store manifest hash mismatch")
    persisted_schema = manifest_schema_root(manifest)
    bound_code_roots = [Path(str(item)) for item in manifest.get("code_roots", [])]
    if (
        persisted_schema is not None
        and persisted_schema.exists()
        and bound_code_roots
        and all(root.exists() for root in bound_code_roots)
    ):
        raise ConflictError("store binding is currently valid; repair is forbidden")
    if (
        restore.get("state") != "cleared"
        or restore.get("project_id") != intent.expected_project_id
        or restore.get("store_identity") != intent.expected_store_identity
        or restore.get("target_root") != str(control)
        or restore.get("origin_witness_sha256") != witness.raw_sha256
        or restore.get("origin_witness_path") != str(witness_path.resolve(strict=True))
        or restore.get("origin_initial_control_root") != witness.initial_control_root
        or restore.get("origin_initial_physical_root_identity") != witness.initial_physical_root_identity
        or restore.get("source_root") != witness.initial_control_root
        or restore.get("source_root_identity") != witness.initial_physical_root_identity
        or restore.get("intended_manifest_bytes") != manifest_raw.hex()
        or restore.get("intended_manifest_sha256") != sha256_hex(manifest_raw)
    ):
        raise IntegrityError("cleared restore transaction does not bind the stale manifest and origin witness")
    stale_paths = []
    if persisted_schema is not None and not persisted_schema.exists():
        stale_paths.append(str(persisted_schema))
    stale_paths.extend(str(root) for root in bound_code_roots if not root.exists())
    if not Path(str(restore["source_root"])).exists():
        stale_paths.append(str(restore["source_root"]))
    if _RESTORE_TRANSACTION.as_posix() not in intent.stale_evidence_refs:
        raise ConfigurationError("stale evidence must include the exact cleared restore transaction")
    for reference in intent.stale_evidence_refs:
        unresolved = control / reference
        ref_path = _require_physical_regular_file(unresolved, label="stale binding evidence")
        if control not in ref_path.parents or ref_path != unresolved:
            raise ConfigurationError("stale evidence ref escapes the exact control root")
    if not stale_paths:
        raise ConflictError("store binding is currently valid; repair is forbidden")
    return manifest, manifest_raw, {"missing_paths": sorted(set(stale_paths)), "refs": list(intent.stale_evidence_refs)}


def _event_for_command(ledger: EventLedger, payload_hash: str, idempotency_key: str) -> dict[str, Any] | None:
    matches = [
        event
        for event in ledger.iter_events()
        if event.get("command_type") == "RepairStoreBinding" and event.get("idempotency_key") == idempotency_key
    ]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("command_payload_hash") != payload_hash:
        raise ConflictError("binding-repair idempotency key conflicts with durable event")
    return matches[0]


def _binding_receipt_record(receipt: Receipt) -> dict[str, Any]:
    """Render the generic durable receipt for command-specific validation."""
    return {
        "schema_id": "ars://core/receipt",
        "schema_version": "1.0.0",
        "command_id": receipt.command_id,
        "status": receipt.status,
        "payload_hash": receipt.payload_hash,
        "outcome": {
            "event_batch_id": receipt.event_batch_id,
            "observed_stream_version": receipt.observed_stream_version,
            "reason_code": receipt.reason_code,
        },
    }


def _advance_event_for_command(ledger: EventLedger, payload_hash: str, idempotency_key: str) -> dict[str, Any] | None:
    matches = [
        event
        for event in ledger.iter_events()
        if event.get("command_type") == "AdvanceStoreBinding" and event.get("idempotency_key") == idempotency_key
    ]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("command_payload_hash") != payload_hash:
        raise ConflictError("binding-advance idempotency key conflicts with durable event")
    return matches[0]


def _guard_advance_file(path: Path, label: str, expected: bytes | None = None) -> None:
    """Reject redirected or conflicting AdvanceStoreBinding transaction files."""
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise IntegrityError(f"{label} identity is unavailable") from exc
    physical = _require_physical_regular_file(path, label=label)
    if expected is not None and physical.read_bytes() != expected:
        raise ConflictError(f"{label} conflicts with the binding advance")


def advance_store_binding(
    intent: AdvanceStoreBinding,
    *,
    now: Callable[[], datetime] | None = None,
    phase_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Advance a valid repaired binding only to a clean Git descendant."""

    clock = datetime.now(UTC) if now is None else now()
    starts = _parse_time(intent.valid_from, "valid_from")
    expires = _parse_time(intent.expires_at, "expires_at")
    if starts >= expires:
        raise ConfigurationError("AdvanceStoreBinding owner intent is expired or nonfinite")
    route_successor = intent.route_successor_binding()
    expected_action = (
        "advance-reviewed-route-successor-store-binding"
        if route_successor is not None
        else "advance-clean-descendant-store-binding"
    )
    if intent.owner_action != expected_action or len(intent.reason.strip()) < 12:
        raise ConfigurationError("AdvanceStoreBinding requires the exact semantic owner action and reason")
    if not _is_sha256(intent.expected_store_identity) or not _is_sha256(intent.expected_origin_witness_sha256):
        raise ConfigurationError("AdvanceStoreBinding expected identities are invalid")
    if route_successor is not None and (
        not _is_sha256(route_successor["predecessor_binding_sha256"])
        or not _is_sha256(route_successor["predecessor_route_sha256"])
        or not _is_sha256(route_successor["successor_route_sha256"])
        or len(route_successor["candidate_git_head"]) != 40
        or any(character not in "0123456789abcdef" for character in route_successor["candidate_git_head"])
    ):
        raise ConfigurationError("AdvanceStoreBinding route successor identities are invalid")
    control = intent.control_root.resolve(strict=True)
    runtime = _require_physical_directory(control / "runtime", label="binding advance runtime")
    marker_path = runtime / ".binding-advance-transaction.json"
    intent_is_current = starts <= clock < expires
    _guard_advance_file(marker_path, "binding advance recovery marker")
    if not intent_is_current and not marker_path.exists():
        raise ConfigurationError("AdvanceStoreBinding owner intent is expired or nonfinite")
    # Refuse an unauthenticated intent before publishing even the transient
    # writer-lock record. The same immutable authority is checked again inside
    # the lock with the source manifest and predecessor census.
    _validate_owner_authority(control, intent)
    payload = intent.semantic_payload()
    payload_hash = sha256_hex(canonical_bytes(payload))
    with WriterLock(runtime / "writer.lock", {"writer_id": f"binding-advance:{payload_hash}"}):
        return _advance_store_binding_locked(
            intent,
            control=control,
            clock=clock,
            intent_is_current=intent_is_current,
            payload=payload,
            payload_hash=payload_hash,
            phase_hook=phase_hook,
        )


def _advance_store_binding_locked(
    intent: AdvanceStoreBinding,
    *,
    control: Path,
    clock: datetime,
    intent_is_current: bool,
    payload: dict[str, Any],
    payload_hash: str,
    phase_hook: Callable[[str], None] | None,
) -> dict[str, Any]:
    """Select one authoritative predecessor and complete its transaction while locked."""

    marker_path = control / "runtime" / ".binding-advance-transaction.json"
    _guard_advance_file(marker_path, "binding advance recovery marker")
    if not intent_is_current and not marker_path.exists():
        raise ConfigurationError("AdvanceStoreBinding owner intent is expired or nonfinite")

    candidate = _candidate_evidence(intent)
    _foundation_pins(Path(candidate["repository_root"]), intent)
    _validate_owner_authority(control, intent)
    # The predecessor recovery binding necessarily records the prior Git HEAD.
    # Admission of that binding would reject the clean descendant before this
    # governed command can verify and advance it, so use only the manifest
    # identity preflight here.  The explicit predecessor/candidate/route checks
    # below are the advance-specific authority boundary.
    source_manifest = load_store_manifest_unbound(control)
    if (
        source_manifest.get("control_root") != str(control)
        or source_manifest.get("project_id") != intent.expected_project_id
        or source_manifest.get("store_identity") != intent.expected_store_identity
    ):
        raise IntegrityError("binding advance source-bound manifest identity is invalid")
    recovery_path = _require_physical_regular_file(
        control / "manifests" / RECOVERY_BINDING_NAME,
        label="binding repair successor",
    )
    predecessor, predecessor_raw = _read_canonical_json(recovery_path, "current repaired binding")
    if (
        predecessor.get("schema_id") != RECOVERY_BINDING_SCHEMA_ID
        or predecessor.get("schema_version") not in {"1.0.0", "1.1.0"}
        or predecessor.get("project_id") != intent.expected_project_id
        or predecessor.get("store_identity") != intent.expected_store_identity
        or predecessor.get("control_root") != str(control)
        or predecessor.get("origin_witness_sha256") != intent.expected_origin_witness_sha256
        or predecessor.get("code_roots") != [candidate["repository_root"]]
        or predecessor.get("schema_root") != candidate["schema_root"]
    ):
        raise IntegrityError("current repaired binding identity is invalid")
    if (
        source_manifest.get("code_roots") != [candidate["repository_root"]]
        or source_manifest.get("schema_root") != candidate["schema_root"]
        or source_manifest.get("code_roots") != predecessor.get("code_roots")
        or source_manifest.get("schema_root") != predecessor.get("schema_root")
    ):
        raise IntegrityError("binding advance source-bound manifest identity is invalid")
    old_head = str(predecessor.get("git_head", ""))
    old_tree = str(predecessor.get("git_tree", ""))
    if not (len(old_head) == 40 and len(old_tree) == 40):
        raise IntegrityError("current repaired binding Git identity is invalid")
    if _run_git(Path(candidate["repository_root"]), "rev-parse", f"{old_head}^{{tree}}") != old_tree:
        raise IntegrityError("current repaired binding Git object changed")

    scope = (intent.owner_actor_id, "store-binding-recovery", "AdvanceStoreBinding", intent.idempotency_key)
    authority_hash = sha256_hex(canonical_bytes({"actor_id": intent.owner_actor_id, "action": intent.owner_action}))
    schemas = runtime_schema_registry(Path(candidate["schema_root"]))
    ledger = EventLedger(
        control,
        intent.expected_project_id,
        schemas,
        store_identity=intent.expected_store_identity,
    )
    receipt_store = ReceiptStore(control)
    existing_receipt = receipt_store.load_scoped(
        scope,
        payload_hash,
        authority_hash,
        0,
        project_id=intent.expected_project_id,
        target_stream_id=intent.expected_project_id,
    )
    if predecessor.get("schema_version") == "1.1.0" and predecessor.get("command_payload_hash") == payload_hash:
        if existing_receipt is None:
            raise IntegrityError("binding advance recovery exists without its durable receipt")
        if _advance_event_for_command(ledger, payload_hash, intent.idempotency_key) is None:
            raise IntegrityError("binding advance recovery exists without its durable event")
        schemas.validate(ADVANCE_RECEIPT_SCHEMA_ID, _binding_receipt_record(existing_receipt))
        expected_marker = canonical_bytes(
            {
                "schema_id": "ars://internal/store-binding-advance-transaction",
                "schema_version": "1.0.0",
                "payload_hash": payload_hash,
                "predecessor_binding_sha256": predecessor.get("predecessor_binding_sha256"),
                "successor_binding_sha256": sha256_hex(predecessor_raw),
            }
        )
        _guard_advance_file(marker_path, "binding advance recovery marker", expected_marker)
        marker_path.unlink(missing_ok=True)
        fsync_directory(marker_path.parent)
        return {"status": "advanced", "recovery_binding": predecessor, "receipt": existing_receipt.__dict__}

    existing_event = _advance_event_for_command(ledger, payload_hash, intent.idempotency_key)
    if intent.input_schema_id == ADVANCE_COMMAND_SCHEMA_ID and existing_event is None:
        raise ConflictError("legacy AdvanceStoreBinding intent identity is permitted only for an exact committed retry")

    _run_git(Path(candidate["repository_root"]), "merge-base", "--is-ancestor", old_head, candidate["git_head"])
    if old_head == candidate["git_head"]:
        raise ConflictError("binding advance requires a strict Git descendant")
    route_successor = intent.route_successor_binding()
    if route_successor is None and (
        predecessor.get("route") != candidate["route"] or predecessor.get("sources") != candidate["sources"]
    ):
        raise IntegrityError("binding advance changed protected route or SPEC bytes")
    if route_successor is not None and (
        sha256_hex(predecessor_raw) != route_successor["predecessor_binding_sha256"]
        or candidate["git_head"] != route_successor["candidate_git_head"]
        or not isinstance(predecessor.get("route"), dict)
        or predecessor["route"].get("sha256") != route_successor["predecessor_route_sha256"]
        or candidate["route"].get("sha256") != route_successor["successor_route_sha256"]
        or predecessor.get("route") == candidate["route"]
        or predecessor.get("sources") != candidate["sources"]
    ):
        raise IntegrityError("binding advance route successor authority is not exact")

    successor = {
        **predecessor,
        "schema_version": "1.1.0",
        "git_head": candidate["git_head"],
        "git_tree": candidate["git_tree"],
        "schema_catalogue_sha256": candidate["schema_catalogue_sha256"],
        "predecessor_binding_sha256": sha256_hex(predecessor_raw),
        "command_payload_hash": payload_hash,
        "owner_actor_id": intent.owner_actor_id,
        "owner_action": intent.owner_action,
        "idempotency_key": intent.idempotency_key,
    }
    successor.pop("route_successor_authority", None)
    if route_successor is not None:
        successor["route"] = candidate["route"]
        successor["route_successor_authority"] = route_successor
    successor_raw = canonical_bytes(successor)
    successor_sha = sha256_hex(successor_raw)
    object_path = control / "objects" / "binding-repair" / f"sha256-{successor_sha}.json"
    marker_raw = canonical_bytes(
        {
            "schema_id": "ars://internal/store-binding-advance-transaction",
            "schema_version": "1.0.0",
            "payload_hash": payload_hash,
            "predecessor_binding_sha256": sha256_hex(predecessor_raw),
            "successor_binding_sha256": successor_sha,
        }
    )
    command_schema = ledger.schemas.resolve_identity(ADVANCE_COMMAND_SCHEMA_ID, "1.0.0")
    ledger.schemas.validate(
        ADVANCE_COMMAND_SCHEMA_ID,
        {
            "schema_id": ADVANCE_COMMAND_SCHEMA_ID,
            "schema_version": "1.0.0",
            "command_type": "AdvanceStoreBinding",
            "payload": payload,
        },
    )
    ledger.schemas.validate(ADVANCE_OBJECT_SCHEMA_ID, successor)
    _physical_artifact_path(control, object_path, create_parent=True)
    _guard_advance_file(marker_path, "binding advance recovery marker", marker_raw)
    _publish(control, marker_path, marker_raw)
    try:
        if phase_hook:
            phase_hook("marker")
        _guard_advance_file(object_path, "binding advance object", successor_raw)
        _publish(control, object_path, successor_raw)
        if phase_hook:
            phase_hook("object")
        event = existing_event
        if event is None:
            result = ledger._append_binding_repair_from_validated_service(
                {
                    "event_type": "StoreBindingAdvanced",
                    "stream_id": intent.expected_project_id,
                    "schema_id": ADVANCE_EVENT_SCHEMA_ID,
                    "schema_version": "1.0.0",
                    "command_id": f"binding-advance-{payload_hash}",
                    "command_type": "AdvanceStoreBinding",
                    "idempotency_key": intent.idempotency_key,
                    "command_payload_hash": payload_hash,
                    "correlation_id": intent.idempotency_key,
                    "causation_id": None,
                    "actor_id": intent.owner_actor_id,
                    "authority_grant_id": "store-binding-recovery",
                    "occurred_at": clock.isoformat().replace("+00:00", "Z"),
                    "command_schema_id": command_schema.schema_id,
                    "command_schema_version": command_schema.schema_version,
                    "command_schema_sha256": command_schema.sha256,
                    "payload": {
                        "recovery_binding_sha256": successor_sha,
                        "recovery_binding_path": "manifests/binding-repair-current.json",
                        "object_path": object_path.relative_to(control).as_posix(),
                        "git_head": candidate["git_head"],
                        "git_tree": candidate["git_tree"],
                        "predecessor_binding_sha256": sha256_hex(predecessor_raw),
                    },
                },
                snapshot=ledger.snapshot(),
                session=_issue_validated_service_session(ledger),
            )
            event = _advance_event_for_command(ledger, payload_hash, intent.idempotency_key)
            event_batch_id = str(result["event_batch_id"])
            observed_version = int(result["resulting_stream_versions"][intent.expected_project_id])
        else:
            event_batch_id = str(event["transaction_id"])
            observed_version = int(event["stream_version"])
        if phase_hook:
            phase_hook("event")
        receipt = Receipt(
            "accepted",
            f"binding-advance-{payload_hash}",
            payload_hash,
            event_batch_id,
            observed_version,
            None,
            None,
            (),
        )
        ledger.schemas.validate(ADVANCE_RECEIPT_SCHEMA_ID, _binding_receipt_record(receipt))
        receipt_store.write_scoped(
            scope,
            authority_hash,
            0,
            receipt,
            project_id=intent.expected_project_id,
            target_stream_id=intent.expected_project_id,
        )
        if phase_hook:
            phase_hook("receipt")
        _guard_advance_file(recovery_path, "binding advance recovery", predecessor_raw)
        _replace(control, recovery_path, successor_raw, expected=predecessor_raw)
        if phase_hook:
            phase_hook("recovery")
        marker_path.unlink(missing_ok=True)
        fsync_directory(marker_path.parent)
        return {"status": "advanced", "recovery_binding": successor, "receipt": receipt.__dict__}
    except BaseException:
        if _advance_event_for_command(ledger, payload_hash, intent.idempotency_key) is None:
            _guard_advance_file(object_path, "binding advance object", successor_raw)
            if object_path.exists():
                object_path.unlink()
            _guard_advance_file(marker_path, "binding advance recovery marker", marker_raw)
            marker_path.unlink(missing_ok=True)
        raise


def repair_store_binding(
    intent: RepairStoreBinding,
    *,
    now: Callable[[], datetime] | None = None,
    phase_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Execute or recover one exact stale-binding repair transaction."""

    clock = datetime.now(UTC) if now is None else now()
    starts = _parse_time(intent.valid_from, "valid_from")
    expires = _parse_time(intent.expires_at, "expires_at")
    if starts >= expires:
        raise ConfigurationError("RepairStoreBinding owner intent is expired or nonfinite")
    intent_is_current = starts <= clock < expires
    if intent.owner_action != "repair-stale-store-binding" or len(intent.reason.strip()) < 12:
        raise ConfigurationError("RepairStoreBinding requires the exact semantic owner action and reason")
    if not _is_sha256(intent.expected_store_identity) or not _is_sha256(intent.expected_origin_witness_sha256):
        raise ConfigurationError("RepairStoreBinding expected identities are invalid")
    candidate = _candidate_evidence(intent)
    _foundation, witness, witness_path = _foundation_pins(Path(candidate["repository_root"]), intent)
    control = intent.control_root.resolve(strict=True)
    _validate_owner_authority(control, intent)
    payload = intent.semantic_payload()
    payload_hash = sha256_hex(canonical_bytes(payload))
    scope = (intent.owner_actor_id, "store-binding-recovery", "RepairStoreBinding", intent.idempotency_key)
    authority_hash = sha256_hex(canonical_bytes({"actor_id": intent.owner_actor_id, "action": intent.owner_action}))
    marker_parent = _require_physical_directory(control / "runtime", label="binding repair marker parent")
    marker_path = marker_parent / _MARKER_NAME
    recovery_path = control / "manifests" / RECOVERY_BINDING_NAME
    binding_path = control / "manifests" / "binding-repair-control-binding.json"
    schemas = runtime_schema_registry(Path(candidate["schema_root"]))
    receipt_store = ReceiptStore(control)
    existing_receipt = receipt_store.load_scoped(
        scope,
        payload_hash,
        authority_hash,
        0,
        project_id=intent.expected_project_id,
        target_stream_id=intent.expected_project_id,
    )
    if existing_receipt is not None:
        schemas.validate(RECEIPT_SCHEMA_ID, _binding_receipt_record(existing_receipt))
        try:
            recovery_path.lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise IntegrityError("binding recovery manifest identity is unavailable") from exc
        else:
            _require_physical_regular_file(recovery_path, label="binding recovery manifest")
            load_store_manifest(control, approved_witness=witness, approved_witness_path=witness_path)
            recovery = load_recovery_binding(
                control,
                expected_project_id=intent.expected_project_id,
                expected_store_identity=intent.expected_store_identity,
                expected_origin_witness_sha256=intent.expected_origin_witness_sha256,
            )
            return {
                "status": "repaired",
                "recovery_binding": recovery,
                "binding_config_path": str(binding_path),
                "receipt": existing_receipt.__dict__,
            }
    lock_identity = {"writer_id": f"binding-repair:{payload_hash}", "command_type": "RepairStoreBinding"}
    with WriterLock(control / "runtime" / "writer.lock", lock_identity):
        marker: dict[str, Any] | None = None
        marker_new = False
        try:
            marker_path.lstat()
        except FileNotFoundError:
            marker_exists = False
        except OSError as exc:
            raise IntegrityError("binding repair recovery marker identity is unavailable") from exc
        else:
            marker_exists = True
        if marker_exists:
            physical_marker = _require_physical_regular_file(
                marker_path,
                label="binding repair recovery marker",
            )
            marker, _ = _read_canonical_json(physical_marker, "binding repair recovery marker")
            marker_fields = {
                "schema_id",
                "schema_version",
                "state",
                "payload_hash",
                "original_manifest_hex",
                "original_manifest_sha256",
                "stale_evidence",
                "candidate",
            }
            if set(marker) != marker_fields or marker.get("schema_version") != "2.0.0":
                raise IntegrityError("binding repair recovery marker is invalid")
            if marker.get("payload_hash") != payload_hash:
                raise ConflictError("binding repair recovery marker conflicts with owner intent")
            if marker.get("candidate") != candidate:
                raise IntegrityError("binding repair Git candidate changed after transaction start")
            original_manifest = bytes.fromhex(str(marker["original_manifest_hex"]))
            stale = dict(marker["stale_evidence"])
        else:
            if not intent_is_current:
                raise ConfigurationError("RepairStoreBinding owner intent is expired or nonfinite")
            manifest, original_manifest, stale = _validate_stale_store(intent, witness, witness_path)
            marker = {
                "schema_id": "ars://internal/store-binding-repair-transaction",
                "schema_version": "2.0.0",
                "state": "prepared",
                "payload_hash": payload_hash,
                "original_manifest_hex": original_manifest.hex(),
                "original_manifest_sha256": sha256_hex(original_manifest),
                "stale_evidence": stale,
                "candidate": candidate,
            }
            marker_new = True
        old_manifest = json.loads(original_manifest)
        repaired_manifest = dict(old_manifest)
        repaired_manifest["code_roots"] = [candidate["repository_root"]]
        repaired_manifest["schema_root"] = candidate["schema_root"]
        repaired_manifest["schema_binding_version"] = "1.0.0"
        restore_path = _require_physical_regular_file(
            control / _RESTORE_TRANSACTION,
            label="cleared restore transaction",
        )
        restore_record = json.loads(restore_path.read_bytes())
        repaired_manifest["manifest_hash"] = _restored_manifest_hash(
            repaired_manifest, str(restore_record["approval_sha256"])
        )
        repaired_manifest_raw = canonical_bytes(repaired_manifest)
        recovery = {
            "schema_id": RECOVERY_BINDING_SCHEMA_ID,
            "schema_version": "1.0.0",
            "project_id": intent.expected_project_id,
            "store_identity": intent.expected_store_identity,
            "control_root": str(control),
            "code_roots": [candidate["repository_root"]],
            "schema_root": candidate["schema_root"],
            "origin_witness_sha256": intent.expected_origin_witness_sha256,
            "git_head": candidate["git_head"],
            "git_tree": candidate["git_tree"],
            "git_clean": True,
            "schema_catalogue_sha256": candidate["schema_catalogue_sha256"],
            "route": candidate["route"],
            "sources": candidate["sources"],
            "stale_evidence": stale,
            "command_payload_hash": payload_hash,
            "owner_actor_id": intent.owner_actor_id,
            "owner_action": intent.owner_action,
            "idempotency_key": intent.idempotency_key,
            "prior_restore_transaction_id": restore_record["transaction_id"],
            "prior_restore_intended_manifest_sha256": restore_record["intended_manifest_sha256"],
        }
        binding_value = {
            "code_roots": [candidate["repository_root"]],
            "control_root": str(control),
            "project_id": intent.expected_project_id,
            "schema_root": candidate["schema_root"],
            "store_identity": intent.expected_store_identity,
        }
        binding_bytes = canonical_bytes(binding_value)
        recovery["binding_config_path"] = binding_path.relative_to(control).as_posix()
        recovery["binding_config_sha256"] = sha256_hex(binding_bytes)
        recovery_bytes = canonical_bytes(recovery)
        recovery_sha = sha256_hex(recovery_bytes)
        object_path = control / "objects" / "binding-repair" / f"sha256-{recovery_sha}.json"
        _physical_artifact_path(control, object_path, create_parent=True)
        _physical_artifact_path(control, binding_path, create_parent=False)
        _physical_artifact_path(control, recovery_path, create_parent=False)
        if marker_new:
            _publish(control, marker_path, canonical_bytes(marker))
        ledger = EventLedger(
            control,
            intent.expected_project_id,
            runtime_schema_registry(Path(candidate["schema_root"])),
            store_identity=intent.expected_store_identity,
        )
        command_schema = ledger.schemas.resolve_identity(COMMAND_SCHEMA_ID, "1.0.0")
        ledger.schemas.validate(
            COMMAND_SCHEMA_ID,
            {
                "schema_id": COMMAND_SCHEMA_ID,
                "schema_version": "1.0.0",
                "command_type": "RepairStoreBinding",
                "payload": payload,
            },
        )
        ledger.schemas.validate(OBJECT_SCHEMA_ID, recovery)
        try:
            current_raw = (control / _STORE_MANIFEST).read_bytes()
            if current_raw not in {original_manifest, repaired_manifest_raw}:
                raise IntegrityError("store manifest changed during binding repair")
            _replace(control, control / _STORE_MANIFEST, repaired_manifest_raw, expected=original_manifest)
            if phase_hook:
                phase_hook("manifest")
            _publish(control, object_path, recovery_bytes)
            if phase_hook:
                phase_hook("object")
            event = _event_for_command(ledger, payload_hash, intent.idempotency_key)
            if event is None:
                snapshot = ledger.snapshot()
                result = ledger._append_binding_repair_from_validated_service(
                    {
                        "event_type": "StoreBindingRepaired",
                        "stream_id": intent.expected_project_id,
                        "schema_id": EVENT_SCHEMA_ID,
                        "schema_version": "1.0.0",
                        "command_id": f"binding-repair-{payload_hash}",
                        "command_type": "RepairStoreBinding",
                        "idempotency_key": intent.idempotency_key,
                        "command_payload_hash": payload_hash,
                        "correlation_id": intent.idempotency_key,
                        "causation_id": None,
                        "actor_id": intent.owner_actor_id,
                        "authority_grant_id": "store-binding-recovery",
                        "occurred_at": clock.isoformat().replace("+00:00", "Z"),
                        "command_schema_id": command_schema.schema_id,
                        "command_schema_version": command_schema.schema_version,
                        "command_schema_sha256": command_schema.sha256,
                        "payload": {
                            "recovery_binding_sha256": recovery_sha,
                            "recovery_binding_path": recovery_path.relative_to(control).as_posix(),
                            "object_path": object_path.relative_to(control).as_posix(),
                            "git_head": candidate["git_head"],
                            "git_tree": candidate["git_tree"],
                            "prior_manifest_sha256": sha256_hex(original_manifest),
                        },
                    },
                    snapshot=snapshot,
                    session=_issue_validated_service_session(ledger),
                )
                event_batch_id = str(result["event_batch_id"])
                observed_version = int(result["resulting_stream_versions"][intent.expected_project_id])
                event = _event_for_command(ledger, payload_hash, intent.idempotency_key)
            else:
                event_batch_id = str(event["transaction_id"])
                observed_version = int(event["stream_version"])
            if phase_hook:
                phase_hook("event")
            receipt = Receipt(
                "accepted",
                f"binding-repair-{payload_hash}",
                payload_hash,
                event_batch_id,
                observed_version,
                None,
                None,
                (),
            )
            ledger.schemas.validate(RECEIPT_SCHEMA_ID, _binding_receipt_record(receipt))
            receipt_store.write_scoped(
                scope,
                authority_hash,
                0,
                receipt,
                project_id=intent.expected_project_id,
                target_stream_id=intent.expected_project_id,
            )
            if phase_hook:
                phase_hook("receipt")
            _publish(control, binding_path, binding_bytes)
            _publish(control, recovery_path, recovery_bytes)
            physical_marker = _require_physical_regular_file(
                marker_path,
                label="binding repair recovery marker",
            )
            current_marker, _ = _read_canonical_json(physical_marker, "binding repair recovery marker")
            if current_marker != marker:
                raise IntegrityError("binding repair recovery marker changed before cleanup")
            marker_path.unlink(missing_ok=True)
            fsync_directory(marker_parent)
            return {
                "status": "repaired",
                "recovery_binding": recovery,
                "binding_config_path": str(binding_path),
                "receipt": receipt.__dict__,
            }
        except BaseException:
            # Before the event is durable every newly published artifact is safely reversible.
            if _event_for_command(ledger, payload_hash, intent.idempotency_key) is None:
                if object_path.exists() and object_path.read_bytes() == recovery_bytes:
                    object_path.unlink()
                _replace(control, control / _STORE_MANIFEST, original_manifest, expected=repaired_manifest_raw)
            raise


def load_recovery_binding(
    control_root: Path, *, expected_project_id: str, expected_store_identity: str, expected_origin_witness_sha256: str
) -> dict[str, Any]:
    """Load the exact store-owned binding selected by store-recovery foundation policy."""
    if not control_root.is_absolute():
        raise IntegrityError("binding recovery control root must be the exact absolute physical path")
    control = _require_physical_directory(control_root, label="binding recovery control root")
    recovery_path = _require_physical_regular_file(
        control / "manifests" / RECOVERY_BINDING_NAME,
        label="binding recovery manifest",
    )
    value, _raw = _read_canonical_json(recovery_path, "binding recovery manifest")
    if (
        value.get("schema_id") != RECOVERY_BINDING_SCHEMA_ID
        or value.get("schema_version") not in {"1.0.0", "1.1.0"}
        or value.get("project_id") != expected_project_id
        or value.get("store_identity") != expected_store_identity
        or value.get("control_root") != str(control)
        or value.get("origin_witness_sha256") != expected_origin_witness_sha256
        or value.get("git_clean") is not True
    ):
        raise IntegrityError("binding recovery manifest identity is invalid")
    if value.get("schema_version") == "1.1.0" and not _is_sha256(value.get("predecessor_binding_sha256")):
        raise IntegrityError("binding recovery predecessor identity is invalid")
    code_roots = value.get("code_roots")
    if not isinstance(code_roots, list) or len(code_roots) != 1 or not isinstance(code_roots[0], str):
        raise IntegrityError("binding recovery candidate root is invalid")
    root_path = Path(code_roots[0])
    schema_path = Path(str(value.get("schema_root")))
    if not root_path.is_absolute() or not schema_path.is_absolute():
        raise IntegrityError("binding recovery candidate paths must be absolute")
    root = _require_physical_directory(root_path, label="binding recovery candidate root")
    schema = _require_physical_directory(schema_path, label="binding recovery schema root")
    if root != root_path or schema != schema_path:
        raise IntegrityError("binding recovery candidate paths are redirected")
    if schema != root / ".research-system" / "schemas":
        raise IntegrityError("binding recovery schema root is not candidate-owned")
    if _run_git(root, "rev-parse", "HEAD") != value.get("git_head") or _run_git(
        root, "rev-parse", "HEAD^{tree}"
    ) != value.get("git_tree"):
        raise IntegrityError("binding recovery Git subject changed")
    if _run_git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise IntegrityError("binding recovery repository is dirty")
    catalogue_sha256 = value.get("schema_catalogue_sha256")
    if not _is_sha256(catalogue_sha256):
        raise IntegrityError("binding recovery schema catalogue identity is invalid")
    if _governed_schema_catalogue(root, schema, label="binding recovery schema catalogue") != catalogue_sha256:
        raise IntegrityError("binding recovery schema catalogue changed")
    route = value.get("route")
    sources = value.get("sources")
    if (
        not isinstance(route, dict)
        or set(route) != {"ref", "sha256"}
        or route.get("ref") != _ROUTE_RELATIVE.as_posix()
        or not _is_sha256(route.get("sha256"))
        or not isinstance(sources, list)
        or len(sources) != 2
        or tuple(
            Path(source.get("ref"))
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("ref"), str)
        )
        != _SPEC_SOURCE_RELATIVES
    ):
        raise IntegrityError("binding recovery route evidence is invalid")
    route_raw = _committed_candidate_file(root, _ROUTE_RELATIVE, label="binding recovery route package")
    if sha256_hex(route_raw) != route["sha256"]:
        raise IntegrityError("binding recovery route package changed")
    for source in sources:
        if (
            not isinstance(source, dict)
            or set(source) != {"ref", "sha256", "size_bytes"}
            or not isinstance(source.get("ref"), str)
            or not _is_sha256(source.get("sha256"))
            or not isinstance(source.get("size_bytes"), int)
            or isinstance(source.get("size_bytes"), bool)
        ):
            raise IntegrityError("binding recovery source evidence is invalid")
        source_raw = _committed_candidate_file(
            root,
            Path(source["ref"]),
            label="binding recovery SPEC source",
        )
        if len(source_raw) != source["size_bytes"] or sha256_hex(source_raw) != source["sha256"]:
            raise IntegrityError("binding recovery SPEC source changed")
    if value.get("schema_version") == "1.1.0":
        try:
            runtime_schema_registry(schema).validate(ADVANCE_OBJECT_SCHEMA_ID, value)
        except SchemaError as exc:
            raise IntegrityError("binding recovery advance authority is invalid") from exc
        if value.get("owner_action") == "advance-reviewed-route-successor-store-binding":
            authority = value["route_successor_authority"]
            predecessor_sha256 = value["predecessor_binding_sha256"]
            predecessor_path = _require_physical_regular_file(
                control / "objects" / "binding-repair" / f"sha256-{predecessor_sha256}.json",
                label="binding recovery route predecessor object",
            )
            predecessor, predecessor_raw = _read_canonical_json(
                predecessor_path,
                "binding recovery route predecessor object",
            )
            predecessor_route = predecessor.get("route")
            if (
                sha256_hex(predecessor_raw) != predecessor_sha256
                or authority["predecessor_binding_sha256"] != predecessor_sha256
                or authority["candidate_git_head"] != value.get("git_head")
                or not isinstance(predecessor_route, dict)
                or authority["predecessor_route_sha256"] != predecessor_route.get("sha256")
                or authority["successor_route_sha256"] != route["sha256"]
                or predecessor.get("route") == route
                or predecessor.get("sources") != sources
            ):
                raise IntegrityError("binding recovery route successor relation is invalid")
    return value
