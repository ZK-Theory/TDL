"""Append-only Gate 6 store-binding publication.

This is deliberately a small coordinator.  The governed-code module owns Git
subject proof, the ledger owns event allocation, and the writer owns durable
control-store paths.  The coordinator only joins those independently owned
facts into one recovery-bound binding transition.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.authority import _validate_bootstrap, authority_bootstrap_sha256
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.git_execution import run_git
from research_system.schema_registry import bundled_schema_registry, runtime_schema_registry
from research_system.store.current_binding import (
    CURRENT_BINDING_RELATIVE_PATH,
    _BINDING_CONFIG_RELATIVE_PATH,
    _ROUTE_RELATIVE_PATH,
    _SOURCE_RELATIVE_PATHS,
    VerifiedCurrentBinding,
    _read_bound_file,
    _schema_catalogue,
    load_current_binding,
)
from research_system.store.governed_code import (
    GovernedCodeManifest,
    build_governed_code_manifest,
    validate_governed_code_manifest,
    validate_persisted_governed_code_manifest,
    validate_reviewed_documentation_successor,
    validate_reviewed_post_divergence_successor,
)
from research_system.store.identity import (
    _restored_manifest_hash,
    load_store_origin_witness,
    validate_approved_origin_witness_path,
)
from research_system.store.ledger import EventLedger, _take_binding_submit_guard
from research_system.store.receipts import ReceiptStore
from research_system.store.writer import CompositeWriterLock, LockedRoot


ADVANCE_COMMAND_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/command/AdvanceStoreBinding"
ADVANCE_INTENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/intent/AdvanceStoreBinding"
ADVANCE_OBJECT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/object/StoreBindingAdvance"
ADVANCE_EVENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/event/StoreBindingAdvanced"
ADVANCE_RECEIPT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingAdvance"
REPAIR_COMMAND_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/command/RepairStoreBinding"
REPAIR_INTENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/intent/RepairStoreBinding"
REPAIR_OBJECT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/object/StoreBindingRepair"
REPAIR_EVENT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired"
REPAIR_RECEIPT_SCHEMA_ID = "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair"
_MARKER_PATH = "runtime/.binding-advance-transaction.json"
_REPAIR_MARKER_PATH = "runtime/.binding-repair-transaction.json"
_STORE_MANIFEST_PATH = "manifests/store-identity.json"
_RESTORE_TRANSACTION_PATH = "manifests/.restore-binding-transaction.json"
_BINDING_OBJECT_DIRECTORY = "objects/binding-repair"
_GOVERNED_OBJECT_DIRECTORY = "objects/governed-code"
_INTEGRATION_REF = "refs/heads/main"


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _git(root: Path, *arguments: str) -> str:
    result = run_git(root, *arguments, unavailable_message="store-binding Git inspection is unavailable")
    if result.returncode != 0:
        raise IntegrityError(f"store-binding Git inspection failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _canonical_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"{label} is invalid") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != raw:
        raise IntegrityError(f"{label} is not canonical JSON")
    return value


def _validate_owner_authority(
    locked: LockedRoot,
    manifest: Mapping[str, Any],
    *,
    project_id: str,
    owner_actor_id: str,
) -> None:
    """Bind the semantic owner to the immutable authority-bootstrap owner."""

    bootstrap = _canonical_object(
        locked.read_exact_file("manifests/authority-bootstrap.json"),
        label="authority bootstrap manifest",
    )
    try:
        validated, _root_grant, _publication_grant = _validate_bootstrap(bootstrap, project_id)
    except (TypeError, ValueError) as exc:
        raise IntegrityError("authority bootstrap manifest is invalid") from exc
    if (
        authority_bootstrap_sha256(validated) != manifest.get("bootstrap_manifest_sha256")
        or validated.get("owner_actor_id") != owner_actor_id
    ):
        raise IntegrityError("binding command actor is not the immutable authority owner")


def _validate_origin_authority(
    *,
    witness_path: Path,
    expected_witness_sha256: str,
    expected_origin_authority_root: Path,
    project_id: str,
    store_identity: str,
) -> None:
    """Join an operation's origin authority to its immutable external witness."""

    try:
        expected_root = expected_origin_authority_root.resolve(strict=True)
    except OSError as exc:
        raise IntegrityError("binding origin authority root is unavailable") from exc
    witness = load_store_origin_witness(witness_path, expected_sha256=expected_witness_sha256)
    _resolved_witness_path, origin_root = validate_approved_origin_witness_path(witness_path, witness)
    if (
        origin_root != expected_root
        or witness.project_id != project_id
        or witness.store_identity != store_identity
        or witness.raw_sha256 != expected_witness_sha256
    ):
        raise IntegrityError("binding origin authority identity is invalid")


def _parse_time(value: str, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ConfigurationError(f"{label} must be a UTC RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ConfigurationError(f"{label} must be a UTC RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ConfigurationError(f"{label} must be UTC")
    return parsed


@dataclass(frozen=True, slots=True)
class AdvanceStoreBinding:
    """Typed semantic intent for a reviewed v1.2 binding advance."""

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
    expected_predecessor_binding_sha256: str
    reviewed_git_head: str
    integrated_main_git_head: str
    integration_ref: str
    reviewed_divergence_authority: dict[str, str] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AdvanceStoreBinding":
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
            "valid_from",
            "expires_at",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "reason",
            "expected_predecessor_binding_sha256",
            "reviewed_git_head",
            "integrated_main_git_head",
            "integration_ref",
        }
        supplied = set(value)
        has_authority = "reviewed_divergence_authority" in supplied
        if supplied != required | ({"reviewed_divergence_authority"} if has_authority else set()):
            raise ConfigurationError("AdvanceStoreBinding intent fields are not exact")
        if (
            value.get("schema_id") != ADVANCE_INTENT_SCHEMA_ID
            or value.get("schema_version") != "1.2.0"
            or value.get("command_type") != "AdvanceStoreBinding"
        ):
            raise ConfigurationError("AdvanceStoreBinding intent schema is unsupported")
        action = value.get("owner_action")
        if action == "advance-reviewed-divergence-store-binding":
            authority = value.get("reviewed_divergence_authority")
            if not isinstance(authority, dict):
                raise ConfigurationError("reviewed divergence authority is required")
            parsed_authority = {str(key): str(item) for key, item in authority.items()}
        elif action == "advance-clean-descendant-store-binding" and not has_authority:
            parsed_authority = None
        else:
            raise ConfigurationError("AdvanceStoreBinding owner action does not match its intent shape")
        scalar_fields = (
            "expected_project_id",
            "expected_store_identity",
            "expected_origin_witness_sha256",
            "valid_from",
            "expires_at",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "reason",
            "expected_predecessor_binding_sha256",
            "reviewed_git_head",
            "integrated_main_git_head",
            "integration_ref",
        )
        if any(not isinstance(value.get(field), str) or not str(value[field]).strip() for field in scalar_fields):
            raise ConfigurationError("AdvanceStoreBinding intent contains an empty field")
        if not all(
            _is_sha256(value[field])
            for field in (
                "expected_store_identity",
                "expected_origin_witness_sha256",
                "expected_predecessor_binding_sha256",
            )
        ):
            raise ConfigurationError("AdvanceStoreBinding expected digest is invalid")
        return cls(
            control_root=Path(str(value["control_root"])),
            candidate_repository_root=Path(str(value["candidate_repository_root"])),
            expected_project_id=str(value["expected_project_id"]),
            expected_store_identity=str(value["expected_store_identity"]),
            expected_origin_authority_root=Path(str(value["expected_origin_authority_root"])),
            expected_origin_witness_sha256=str(value["expected_origin_witness_sha256"]),
            intended_schema_root=Path(str(value["intended_schema_root"])),
            valid_from=str(value["valid_from"]),
            expires_at=str(value["expires_at"]),
            owner_actor_id=str(value["owner_actor_id"]),
            owner_action=str(action),
            idempotency_key=str(value["idempotency_key"]),
            reason=str(value["reason"]),
            expected_predecessor_binding_sha256=str(value["expected_predecessor_binding_sha256"]),
            reviewed_git_head=str(value["reviewed_git_head"]),
            integrated_main_git_head=str(value["integrated_main_git_head"]),
            integration_ref=str(value["integration_ref"]),
            reviewed_divergence_authority=parsed_authority,
        )

    def semantic_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "control_root": str(self.control_root),
            "candidate_repository_root": str(self.candidate_repository_root),
            "expected_project_id": self.expected_project_id,
            "expected_store_identity": self.expected_store_identity,
            "expected_origin_authority_root": str(self.expected_origin_authority_root),
            "expected_origin_witness_sha256": self.expected_origin_witness_sha256,
            "intended_schema_root": str(self.intended_schema_root),
            "valid_from": self.valid_from,
            "expires_at": self.expires_at,
            "owner_actor_id": self.owner_actor_id,
            "owner_action": self.owner_action,
            "idempotency_key": self.idempotency_key,
            "reason": self.reason,
            "expected_predecessor_binding_sha256": self.expected_predecessor_binding_sha256,
            "reviewed_git_head": self.reviewed_git_head,
            "integrated_main_git_head": self.integrated_main_git_head,
            "integration_ref": self.integration_ref,
        }
        if self.reviewed_divergence_authority is not None:
            payload["reviewed_divergence_authority"] = dict(self.reviewed_divergence_authority)
        return payload


@dataclass(frozen=True, slots=True)
class RepairStoreBinding:
    """Typed legacy repair intent retained for the public transition seam."""

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
        if (
            set(value) != required
            or value.get("schema_id") != REPAIR_INTENT_SCHEMA_ID
            or value.get("schema_version") != "1.0.0"
            or value.get("command_type") != "RepairStoreBinding"
        ):
            raise ConfigurationError("RepairStoreBinding intent schema is unsupported")
        stale = value.get("stale_evidence_refs")
        if not isinstance(stale, list) or not stale or not all(isinstance(item, str) and item for item in stale):
            raise ConfigurationError("RepairStoreBinding stale evidence is invalid")
        if value.get("spec_route_ref") != _ROUTE_RELATIVE_PATH.as_posix() or value.get("spec_source_refs") != [
            path.as_posix() for path in _SOURCE_RELATIVE_PATHS
        ]:
            raise ConfigurationError("RepairStoreBinding SPEC evidence refs are invalid")
        if value.get("owner_action") != "repair-stale-store-binding":
            raise ConfigurationError("RepairStoreBinding owner action is invalid")
        return cls(
            Path(str(value["control_root"])),
            Path(str(value["candidate_repository_root"])),
            str(value["expected_project_id"]),
            str(value["expected_store_identity"]),
            Path(str(value["expected_origin_authority_root"])),
            str(value["expected_origin_witness_sha256"]),
            Path(str(value["intended_schema_root"])),
            tuple(stale),
            str(value["spec_route_ref"]),
            tuple(str(item) for item in value["spec_source_refs"]),
            str(value["valid_from"]),
            str(value["expires_at"]),
            str(value["owner_actor_id"]),
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


def _read_intent_mapping(path: Path, *, label: str, schema_id: str, schema_version: str) -> dict[str, Any]:
    """Read a caller-supplied intent as configuration, not execution history."""

    try:
        value = _canonical_object(path.read_bytes(), label=label)
        bundled_schema_registry().validate(schema_id, value, schema_version=schema_version)
    except (AttributeError, OSError, IntegrityError, SchemaError) as exc:
        raise ConfigurationError(f"{label} is invalid") from exc
    return value


def read_advance_intent(path: Path) -> AdvanceStoreBinding:
    return AdvanceStoreBinding.from_mapping(
        _read_intent_mapping(
            path,
            label="AdvanceStoreBinding intent",
            schema_id=ADVANCE_INTENT_SCHEMA_ID,
            schema_version="1.2.0",
        )
    )


def read_repair_intent(path: Path) -> RepairStoreBinding:
    return RepairStoreBinding.from_mapping(
        _read_intent_mapping(
            path,
            label="RepairStoreBinding intent",
            schema_id=REPAIR_INTENT_SCHEMA_ID,
            schema_version="1.0.0",
        )
    )


@dataclass(frozen=True, slots=True)
class _CandidateEvidence:
    root: Path
    schema_root: Path
    git_head: str
    git_tree: str
    schema_catalogue_sha256: str
    route: dict[str, str]
    sources: list[dict[str, Any]]
    manifest: GovernedCodeManifest

    def marker_mapping(self) -> dict[str, Any]:
        return {
            "repository_root": str(self.root),
            "schema_root": str(self.schema_root),
            "git_head": self.git_head,
            "git_tree": self.git_tree,
            "schema_catalogue_sha256": self.schema_catalogue_sha256,
            "route": self.route,
            "sources": self.sources,
            "governed_code_manifest": self.manifest.to_mapping(),
        }


def _candidate_evidence(intent: AdvanceStoreBinding | RepairStoreBinding) -> _CandidateEvidence:
    root = intent.candidate_repository_root.resolve(strict=True)
    if (
        root != intent.candidate_repository_root
        or Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True) != root
    ):
        raise ConfigurationError("candidate repository root is not an exact physical Git worktree")
    schema_root = intent.intended_schema_root.resolve(strict=True)
    if schema_root != root / ".research-system" / "schemas" or not schema_root.is_dir():
        raise ConfigurationError("intended schema root is not candidate-owned")
    manifest = build_governed_code_manifest(root)
    git_head = manifest.git_commit
    git_tree = _git(root, "rev-parse", "HEAD^{tree}")
    route_raw = _read_bound_file(root, _ROUTE_RELATIVE_PATH, git_head, label="bound SPEC route package")
    route = {"ref": _ROUTE_RELATIVE_PATH.as_posix(), "sha256": sha256_hex(route_raw)}
    sources = [
        {"ref": relative.as_posix(), "sha256": sha256_hex(raw), "size_bytes": len(raw)}
        for relative in _SOURCE_RELATIVE_PATHS
        for raw in (_read_bound_file(root, relative, git_head, label="bound SPEC source"),)
    ]
    return _CandidateEvidence(
        root=root,
        schema_root=schema_root,
        git_head=git_head,
        git_tree=git_tree,
        schema_catalogue_sha256=_schema_catalogue(root, schema_root, git_head),
        route=route,
        sources=sources,
        manifest=manifest,
    )


def _revalidate_candidate(candidate: _CandidateEvidence) -> None:
    if (
        _git(candidate.root, "rev-parse", "HEAD") != candidate.git_head
        or _git(candidate.root, "rev-parse", "HEAD^{tree}") != candidate.git_tree
    ):
        raise ConflictError("candidate Git subject changed before authoritative publication")
    validate_governed_code_manifest(candidate.manifest, candidate.root)
    if (
        _schema_catalogue(candidate.root, candidate.schema_root, candidate.git_head)
        != candidate.schema_catalogue_sha256
    ):
        raise IntegrityError("candidate schema catalogue changed before authoritative publication")


@dataclass(frozen=True, slots=True)
class _AdvancePlan:
    marker_raw: bytes
    predecessor_raw: bytes
    predecessor_sha256: str
    binding_raw: bytes
    binding_sha256: str
    governed_manifest_raw: bytes
    governed_manifest_sha256: str
    original_manifest_raw: bytes
    intended_manifest_raw: bytes
    original_config_raw: bytes
    intended_config_raw: bytes
    expected_stream_version: int
    payload_hash: str
    authority_hash: str
    candidate: _CandidateEvidence


@dataclass(frozen=True, slots=True)
class _RepairPlan:
    marker_raw: bytes
    pointer_original: bytes | None
    binding_raw: bytes
    binding_sha256: str
    original_manifest_raw: bytes
    intended_manifest_raw: bytes
    original_config_raw: bytes | None
    intended_config_raw: bytes
    expected_stream_version: int
    payload_hash: str
    authority_hash: str
    candidate: _CandidateEvidence


def _binding_config_bytes(binding: Mapping[str, Any]) -> bytes:
    return canonical_bytes(
        {
            "code_roots": binding["code_roots"],
            "control_root": binding["control_root"],
            "project_id": binding["project_id"],
            "schema_root": binding["schema_root"],
            "store_identity": binding["store_identity"],
        }
    )


def _decode_hex(value: object, *, label: str) -> bytes:
    if not isinstance(value, str):
        raise IntegrityError(f"binding advance marker {label} is invalid")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise IntegrityError(f"binding advance marker {label} is invalid") from exc


def _read_existing_marker(locked: LockedRoot) -> tuple[dict[str, Any], bytes] | None:
    try:
        raw = locked.read_exact_file(_MARKER_PATH)
    except ConflictError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return None
        raise
    return _canonical_object(raw, label="binding advance marker"), raw


def _replace_or_verify(locked: LockedRoot, path: str, original: bytes, intended: bytes) -> None:
    current = locked.read_exact_file(path)
    if current == intended:
        return
    if current != original:
        raise ConflictError(f"binding advance mutable effect conflicts: {path}")
    locked.replace_exact_file(path, original, intended)


def _write_or_replace(locked: LockedRoot, path: str, original: bytes | None, intended: bytes) -> None:
    if original is None:
        try:
            current = locked.read_exact_file(path)
        except ConflictError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                locked.write_exact_file(path, intended)
                return
            raise
        if current != intended:
            raise ConflictError(f"binding repair mutable effect conflicts: {path}")
        return
    _replace_or_verify(locked, path, original, intended)


class StoreBindingService:
    """Own one guarded, recovery-bound binding repair/advance publication seam."""

    def __init__(
        self,
        control_root: Path,
        project_id: str,
        store_identity: str,
        *,
        foundation_path: Path | None = None,
        now: Callable[[], datetime] | None = None,
        phase_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.control_root = control_root.resolve(strict=True)
        self.project_id = project_id
        self.store_identity = store_identity
        self.foundation_path = foundation_path
        self.now = now or (lambda: datetime.now(UTC))
        self.phase_hook = phase_hook
        self.ledger: EventLedger
        self.receipts = ReceiptStore(self.control_root)

    def advance(self, intent: AdvanceStoreBinding) -> dict[str, Any]:
        candidate = _candidate_evidence(intent)
        self.ledger = EventLedger(
            self.control_root,
            self.project_id,
            runtime_schema_registry(candidate.schema_root),
            store_identity=self.store_identity,
        )
        return self.submit(("advance", intent, candidate))

    def repair(self, intent: RepairStoreBinding) -> dict[str, Any]:
        """Retain a typed repair endpoint; repair execution remains v1.0 only."""

        candidate = _candidate_evidence(intent)
        self.ledger = EventLedger(
            self.control_root,
            self.project_id,
            runtime_schema_registry(candidate.schema_root),
            store_identity=self.store_identity,
        )
        return self.submit(("repair", intent, candidate))

    @_take_binding_submit_guard()
    def submit(
        self,
        operation: tuple[str, AdvanceStoreBinding | RepairStoreBinding, _CandidateEvidence],
        append_binding: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        kind, intent, candidate = operation
        if kind == "advance" and isinstance(intent, AdvanceStoreBinding):
            return self._advance(intent, candidate, append_binding)
        if kind == "repair" and isinstance(intent, RepairStoreBinding):
            return self._repair(intent, candidate, append_binding)
        raise TypeError("store-binding operation is invalid")

    def _repair(
        self,
        intent: RepairStoreBinding,
        candidate: _CandidateEvidence,
        append_binding: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        if (
            self.control_root != intent.control_root.resolve(strict=True)
            or self.project_id != intent.expected_project_id
            or self.store_identity != intent.expected_store_identity
        ):
            raise ConfigurationError("StoreBindingService identity differs from the semantic intent")
        starts = _parse_time(intent.valid_from, label="valid_from")
        expires = _parse_time(intent.expires_at, label="expires_at")
        if starts >= expires:
            raise ConfigurationError("RepairStoreBinding validity interval is invalid")
        payload_hash = sha256_hex(canonical_bytes(intent.semantic_payload()))
        lock_identity = {"writer_id": f"store-binding-repair:{payload_hash}", "command_type": "RepairStoreBinding"}
        with CompositeWriterLock((self.control_root,), lock_identity) as writer_lock:
            locked = writer_lock.locked_root(self.control_root)
            marker = self._read_repair_marker(locked)
            if marker is not None:
                plan = self._repair_plan(intent, candidate, payload_hash, locked, marker)
                return self._publish_repair(plan, intent, locked, append_binding)
            completed = self._binding_event_for(
                "binding-repair", payload_hash, intent.idempotency_key, "StoreBindingRepaired"
            )
            if completed is not None:
                return self._completed_repair(completed, payload_hash, locked)
            if not starts <= self.now() < expires:
                raise ConfigurationError("RepairStoreBinding owner intent is expired")
            plan = self._repair_plan(intent, candidate, payload_hash, locked, None)
            return self._publish_repair(plan, intent, locked, append_binding)

    @staticmethod
    def _read_repair_marker(locked: LockedRoot) -> tuple[dict[str, Any], bytes] | None:
        try:
            raw = locked.read_exact_file(_REPAIR_MARKER_PATH)
        except ConflictError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                return None
            raise
        return _canonical_object(raw, label="binding repair marker"), raw

    def _completed_binding_terminal(
        self,
        *,
        event: Mapping[str, Any],
        payload_hash: str,
        locked: LockedRoot,
        command_prefix: str,
        command_type: str,
        expected_schema_version: str,
        require_governed_manifest: bool,
    ) -> tuple[str, dict[str, Any], Receipt]:
        """Verify every durable effect before an exact marker-free retry succeeds."""

        payload = event.get("payload")
        stream_version = event.get("stream_version")
        if (
            not isinstance(payload, Mapping)
            or not _is_sha256(payload.get("recovery_binding_sha256"))
            or event.get("command_id") != f"{command_prefix}-{payload_hash}"
            or event.get("command_type") != command_type
            or event.get("command_payload_hash") != payload_hash
            or type(stream_version) is not int
            or stream_version < 1
        ):
            raise IntegrityError("binding completed event history is invalid")
        binding_sha256 = str(payload["recovery_binding_sha256"])
        binding_raw = locked.read_exact_file(f"{_BINDING_OBJECT_DIRECTORY}/sha256-{binding_sha256}.json")
        binding = _canonical_object(binding_raw, label="published binding")
        if (
            sha256_hex(binding_raw) != binding_sha256
            or binding.get("schema_version") != expected_schema_version
            or locked.read_exact_file(CURRENT_BINDING_RELATIVE_PATH.as_posix()) != binding_raw
            or locked.read_exact_file(_BINDING_CONFIG_RELATIVE_PATH.as_posix()) != _binding_config_bytes(binding)
        ):
            raise IntegrityError("binding completed terminal effects are incomplete")
        store_manifest = _canonical_object(
            locked.read_exact_file(_STORE_MANIFEST_PATH),
            label="published store manifest",
        )
        if (
            store_manifest.get("project_id") != binding.get("project_id")
            or store_manifest.get("store_identity") != binding.get("store_identity")
            or store_manifest.get("control_root") != binding.get("control_root")
            or store_manifest.get("code_roots") != binding.get("code_roots")
            or store_manifest.get("schema_root") != binding.get("schema_root")
        ):
            raise IntegrityError("binding completed store effects are incomplete")
        if require_governed_manifest:
            manifest_sha256 = binding.get("governed_code_manifest_sha256")
            manifest_path = binding.get("governed_code_manifest_path")
            if (
                not _is_sha256(manifest_sha256)
                or manifest_path != f"{_GOVERNED_OBJECT_DIRECTORY}/sha256-{manifest_sha256}.json"
            ):
                raise IntegrityError("binding completed governed manifest relation is invalid")
            governed = GovernedCodeManifest.from_mapping(
                _canonical_object(
                    locked.read_exact_file(str(manifest_path)),
                    label="published governed code manifest",
                )
            )
            if governed.manifest_sha256 != manifest_sha256:
                raise IntegrityError("binding completed governed manifest is invalid")
        receipt = self.receipts.load(f"{command_prefix}-{payload_hash}")
        if receipt is None or receipt.observed_stream_version != stream_version:
            raise IntegrityError("binding completed receipt history is invalid")
        authority_hash = sha256_hex(
            canonical_bytes({"actor_id": binding.get("owner_actor_id"), "action": binding.get("owner_action")})
        )
        try:
            scoped = self.receipts.load_scoped(
                (
                    str(binding.get("owner_actor_id")),
                    "store-binding-recovery",
                    command_type,
                    str(binding.get("idempotency_key")),
                ),
                payload_hash,
                authority_hash,
                stream_version - 1,
                project_id=self.project_id,
                target_stream_id=self.project_id,
            )
        except ConflictError as exc:
            raise IntegrityError("binding completed scoped receipt history is invalid") from exc
        if scoped != receipt:
            raise IntegrityError("binding completed scoped receipt history is invalid")
        return binding_sha256, binding, receipt

    def _completed_repair(
        self,
        event: Mapping[str, Any],
        payload_hash: str,
        locked: LockedRoot,
    ) -> dict[str, Any]:
        binding_sha256, binding, receipt = self._completed_binding_terminal(
            event=event,
            payload_hash=payload_hash,
            locked=locked,
            command_prefix="binding-repair",
            command_type="RepairStoreBinding",
            expected_schema_version="1.0.0",
            require_governed_manifest=False,
        )
        return {
            "status": "repaired",
            "binding_sha256": binding_sha256,
            "binding": binding,
            "receipt": self._receipt_record(receipt),
        }

    def _repair_plan(
        self,
        intent: RepairStoreBinding,
        candidate: _CandidateEvidence,
        payload_hash: str,
        locked: LockedRoot,
        existing_marker: tuple[dict[str, Any], bytes] | None,
    ) -> _RepairPlan:
        if existing_marker is not None:
            marker, marker_raw = existing_marker
            required = {
                "schema_id",
                "schema_version",
                "command_type",
                "payload_hash",
                "candidate",
                "pointer_original_hex",
                "binding_raw_hex",
                "binding_sha256",
                "original_manifest_raw_hex",
                "intended_manifest_raw_hex",
                "original_config_raw_hex",
                "intended_config_raw_hex",
                "expected_stream_version",
                "authority_hash",
            }
            if (
                set(marker) != required
                or marker.get("schema_id") != "ars://internal/store-binding-repair-transaction"
                or marker.get("schema_version") != "1.0.0"
                or marker.get("command_type") != "RepairStoreBinding"
                or marker.get("payload_hash") != payload_hash
                or marker.get("candidate") != candidate.marker_mapping()
            ):
                raise ConflictError("binding repair recovery marker conflicts with semantic intent")
            pointer_hex = marker.get("pointer_original_hex")
            pointer_original = None if pointer_hex is None else _decode_hex(pointer_hex, label="repair pointer bytes")
            binding_raw = _decode_hex(marker["binding_raw_hex"], label="repair binding bytes")
            if marker.get("binding_sha256") != sha256_hex(binding_raw):
                raise IntegrityError("binding repair marker object hash is invalid")
            return _RepairPlan(
                marker_raw,
                pointer_original,
                binding_raw,
                sha256_hex(binding_raw),
                _decode_hex(marker["original_manifest_raw_hex"], label="repair manifest bytes"),
                _decode_hex(marker["intended_manifest_raw_hex"], label="repair intended manifest bytes"),
                None
                if marker.get("original_config_raw_hex") is None
                else _decode_hex(marker["original_config_raw_hex"], label="repair config bytes"),
                _decode_hex(marker["intended_config_raw_hex"], label="repair intended config bytes"),
                int(marker["expected_stream_version"]),
                payload_hash,
                str(marker["authority_hash"]),
                candidate,
            )

        original_manifest_raw = locked.read_exact_file(_STORE_MANIFEST_PATH)
        original_manifest = _canonical_object(original_manifest_raw, label="stale store manifest")
        restore = _canonical_object(
            locked.read_exact_file(_RESTORE_TRANSACTION_PATH), label="cleared restore transaction"
        )
        if (
            _RESTORE_TRANSACTION_PATH not in intent.stale_evidence_refs
            or restore.get("state") != "cleared"
            or not isinstance(restore.get("transaction_id"), str)
            or not _is_sha256(restore.get("intended_manifest_sha256"))
            or not _is_sha256(restore.get("approval_sha256"))
            or original_manifest.get("project_id") != self.project_id
            or original_manifest.get("store_identity") != self.store_identity
            or original_manifest.get("control_root") != str(self.control_root)
            or original_manifest.get("origin_witness_sha256") != intent.expected_origin_witness_sha256
        ):
            raise IntegrityError("RepairStoreBinding stale restore evidence is invalid")
        witness_path_value = original_manifest.get("origin_witness_path")
        if not isinstance(witness_path_value, str) or not Path(witness_path_value).is_absolute():
            raise IntegrityError("RepairStoreBinding origin witness locator is invalid")
        _validate_origin_authority(
            witness_path=Path(witness_path_value),
            expected_witness_sha256=intent.expected_origin_witness_sha256,
            expected_origin_authority_root=intent.expected_origin_authority_root,
            project_id=self.project_id,
            store_identity=self.store_identity,
        )
        _validate_owner_authority(
            locked,
            original_manifest,
            project_id=self.project_id,
            owner_actor_id=intent.owner_actor_id,
        )
        try:
            pointer_original = locked.read_exact_file(CURRENT_BINDING_RELATIVE_PATH.as_posix())
        except ConflictError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                pointer_original = None
            else:
                raise
        else:
            try:
                pointer = _canonical_object(pointer_original, label="current binding pointer")
                if pointer.get("schema_version") in {"1.0.0", "1.1.0", "1.2.0"}:
                    raise ConflictError("RepairStoreBinding is forbidden while a current binding exists")
            except ConflictError:
                raise
            except IntegrityError:
                pass
        legacy_paths = [Path(item) for item in original_manifest.get("code_roots", []) if isinstance(item, str)]
        schema_value = original_manifest.get("schema_root")
        if isinstance(schema_value, str):
            legacy_paths.append(Path(schema_value))
        missing_paths = sorted(str(path) for path in legacy_paths if not path.exists())
        if not missing_paths:
            raise ConflictError("RepairStoreBinding requires a demonstrably stale store")
        try:
            original_config_raw = locked.read_exact_file(_BINDING_CONFIG_RELATIVE_PATH.as_posix())
        except ConflictError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                original_config_raw = None
            else:
                raise
        intended_manifest = dict(original_manifest)
        intended_manifest["code_roots"] = [str(candidate.root)]
        intended_manifest["schema_root"] = str(candidate.schema_root)
        intended_manifest["schema_binding_version"] = "1.0.0"
        intended_manifest["manifest_hash"] = _restored_manifest_hash(intended_manifest, str(restore["approval_sha256"]))
        intended_manifest_raw = canonical_bytes(intended_manifest)
        intended_config_raw = canonical_bytes(
            {
                "code_roots": [str(candidate.root)],
                "control_root": str(self.control_root),
                "project_id": self.project_id,
                "schema_root": str(candidate.schema_root),
                "store_identity": self.store_identity,
            }
        )
        binding = {
            "schema_id": "ars://internal/store-binding-recovery",
            "schema_version": "1.0.0",
            "project_id": self.project_id,
            "store_identity": self.store_identity,
            "control_root": str(self.control_root),
            "code_roots": [str(candidate.root)],
            "schema_root": str(candidate.schema_root),
            "origin_witness_sha256": intent.expected_origin_witness_sha256,
            "git_head": candidate.git_head,
            "git_tree": candidate.git_tree,
            "git_clean": True,
            "schema_catalogue_sha256": candidate.schema_catalogue_sha256,
            "route": candidate.route,
            "sources": candidate.sources,
            "stale_evidence": {"refs": list(intent.stale_evidence_refs), "missing_paths": missing_paths},
            "command_payload_hash": payload_hash,
            "owner_actor_id": intent.owner_actor_id,
            "owner_action": intent.owner_action,
            "idempotency_key": intent.idempotency_key,
            "prior_restore_transaction_id": restore["transaction_id"],
            "prior_restore_intended_manifest_sha256": restore["intended_manifest_sha256"],
            "binding_config_path": _BINDING_CONFIG_RELATIVE_PATH.as_posix(),
            "binding_config_sha256": sha256_hex(intended_config_raw),
        }
        self.ledger.schemas.validate(REPAIR_OBJECT_SCHEMA_ID, binding, schema_version="1.0.0")
        command_binding = self.ledger.schemas.command_binding("RepairStoreBinding")
        if (
            command_binding is None
            or command_binding.schema_id != REPAIR_COMMAND_SCHEMA_ID
            or command_binding.schema_version != "1.0.0"
        ):
            raise IntegrityError("RepairStoreBinding v1.0 is not active")
        self.ledger.schemas.validate(
            REPAIR_COMMAND_SCHEMA_ID,
            {
                "schema_id": command_binding.schema_id,
                "schema_version": command_binding.schema_version,
                "command_type": "RepairStoreBinding",
                "payload": intent.semantic_payload(),
            },
            schema_version=command_binding.schema_version,
        )
        snapshot = self.ledger.snapshot()
        expected_stream_version = snapshot.stream_versions.get(self.project_id, 0)
        binding_raw = canonical_bytes(binding)
        authority_hash = sha256_hex(canonical_bytes({"actor_id": intent.owner_actor_id, "action": intent.owner_action}))
        marker = {
            "schema_id": "ars://internal/store-binding-repair-transaction",
            "schema_version": "1.0.0",
            "command_type": "RepairStoreBinding",
            "payload_hash": payload_hash,
            "candidate": candidate.marker_mapping(),
            "pointer_original_hex": None if pointer_original is None else pointer_original.hex(),
            "binding_raw_hex": binding_raw.hex(),
            "binding_sha256": sha256_hex(binding_raw),
            "original_manifest_raw_hex": original_manifest_raw.hex(),
            "intended_manifest_raw_hex": intended_manifest_raw.hex(),
            "original_config_raw_hex": None if original_config_raw is None else original_config_raw.hex(),
            "intended_config_raw_hex": intended_config_raw.hex(),
            "expected_stream_version": expected_stream_version,
            "authority_hash": authority_hash,
        }
        return _RepairPlan(
            canonical_bytes(marker),
            pointer_original,
            binding_raw,
            sha256_hex(binding_raw),
            original_manifest_raw,
            intended_manifest_raw,
            original_config_raw,
            intended_config_raw,
            expected_stream_version,
            payload_hash,
            authority_hash,
            candidate,
        )

    def _publish_repair(
        self,
        plan: _RepairPlan,
        intent: RepairStoreBinding,
        locked: LockedRoot,
        append_binding: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        marker = self._read_repair_marker(locked)
        if marker is None:
            _revalidate_candidate(plan.candidate)
            locked.write_exact_file(_REPAIR_MARKER_PATH, plan.marker_raw)
        elif marker[1] != plan.marker_raw:
            raise ConflictError("binding repair marker changed before publication")
        locked.write_exact_file(f"{_BINDING_OBJECT_DIRECTORY}/sha256-{plan.binding_sha256}.json", plan.binding_raw)
        _write_or_replace(locked, _STORE_MANIFEST_PATH, plan.original_manifest_raw, plan.intended_manifest_raw)
        _write_or_replace(
            locked, _BINDING_CONFIG_RELATIVE_PATH.as_posix(), plan.original_config_raw, plan.intended_config_raw
        )
        event = self._binding_event_for(
            "binding-repair", plan.payload_hash, intent.idempotency_key, "StoreBindingRepaired"
        )
        if event is None:
            _revalidate_candidate(plan.candidate)
            snapshot = self.ledger.snapshot()
            if snapshot.stream_versions.get(self.project_id, 0) != plan.expected_stream_version:
                raise ConflictError("binding repair predecessor stream version changed")
            command_identity = self.ledger.schemas.resolve_identity(REPAIR_COMMAND_SCHEMA_ID, "1.0.0")
            appended = append_binding(
                {
                    "event_type": "StoreBindingRepaired",
                    "stream_id": self.project_id,
                    "schema_id": REPAIR_EVENT_SCHEMA_ID,
                    "schema_version": "1.0.0",
                    "command_id": f"binding-repair-{plan.payload_hash}",
                    "command_type": "RepairStoreBinding",
                    "idempotency_key": intent.idempotency_key,
                    "command_payload_hash": plan.payload_hash,
                    "correlation_id": intent.idempotency_key,
                    "causation_id": None,
                    "actor_id": intent.owner_actor_id,
                    "authority_grant_id": "store-binding-recovery",
                    "occurred_at": self.now().isoformat().replace("+00:00", "Z"),
                    "command_schema_id": command_identity.schema_id,
                    "command_schema_version": command_identity.schema_version,
                    "command_schema_sha256": command_identity.sha256,
                    "payload": {
                        "recovery_binding_sha256": plan.binding_sha256,
                        "recovery_binding_path": CURRENT_BINDING_RELATIVE_PATH.as_posix(),
                        "object_path": f"{_BINDING_OBJECT_DIRECTORY}/sha256-{plan.binding_sha256}.json",
                        "git_head": plan.candidate.git_head,
                        "git_tree": plan.candidate.git_tree,
                        "prior_manifest_sha256": sha256_hex(plan.original_manifest_raw),
                    },
                },
                snapshot=snapshot,
            )
            event_batch_id = str(appended["event_batch_id"])
            observed_stream_version = int(appended["resulting_stream_versions"][self.project_id])
        else:
            event_batch_id = str(event["transaction_id"])
            observed_stream_version = int(event["stream_version"])
        if self.phase_hook:
            self.phase_hook("event")
        receipt = Receipt(
            "accepted",
            f"binding-repair-{plan.payload_hash}",
            plan.payload_hash,
            event_batch_id,
            observed_stream_version,
            None,
            None,
            (),
        )
        receipt_record = self._receipt_record(receipt)
        self.ledger.schemas.validate(REPAIR_RECEIPT_SCHEMA_ID, receipt_record, schema_version="1.0.0")
        self.receipts.write_scoped(
            (intent.owner_actor_id, "store-binding-recovery", "RepairStoreBinding", intent.idempotency_key),
            plan.authority_hash,
            plan.expected_stream_version,
            receipt,
            project_id=self.project_id,
            target_stream_id=self.project_id,
        )
        if self.phase_hook:
            self.phase_hook("receipt")
        _write_or_replace(locked, CURRENT_BINDING_RELATIVE_PATH.as_posix(), plan.pointer_original, plan.binding_raw)
        if locked.read_exact_file(CURRENT_BINDING_RELATIVE_PATH.as_posix()) != plan.binding_raw:
            raise IntegrityError("binding repair pointer readback differs")
        if locked.read_exact_file(f"{_BINDING_OBJECT_DIRECTORY}/sha256-{plan.binding_sha256}.json") != plan.binding_raw:
            raise IntegrityError("binding repair object readback differs")
        if self.receipts.load(receipt.command_id) != receipt:
            raise IntegrityError("binding repair receipt readback differs")
        locked.remove_exact_file(_REPAIR_MARKER_PATH, plan.marker_raw)
        return {
            "status": "repaired",
            "binding_sha256": plan.binding_sha256,
            "binding": _canonical_object(plan.binding_raw, label="published repair binding"),
            "receipt": receipt_record,
        }

    @staticmethod
    def _receipt_record(receipt: Receipt) -> dict[str, Any]:
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

    def _binding_event_for(
        self, command_prefix: str, payload_hash: str, idempotency_key: str, event_type: str
    ) -> dict[str, Any] | None:
        events = [
            event
            for event in self.ledger.iter_events()
            if event.get("command_id") == f"{command_prefix}-{payload_hash}"
        ]
        if not events:
            return None
        if (
            len(events) != 1
            or events[0].get("event_type") != event_type
            or events[0].get("idempotency_key") != idempotency_key
        ):
            raise IntegrityError("binding event history is ambiguous")
        return events[0]

    def _advance(
        self,
        intent: AdvanceStoreBinding,
        candidate: _CandidateEvidence,
        append_binding: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        if (
            self.control_root != intent.control_root.resolve(strict=True)
            or self.project_id != intent.expected_project_id
            or self.store_identity != intent.expected_store_identity
        ):
            raise ConfigurationError("StoreBindingService identity differs from the semantic intent")
        if not intent.expected_origin_authority_root.is_absolute() or intent.integration_ref != _INTEGRATION_REF:
            raise ConfigurationError("AdvanceStoreBinding origin or integration identity is invalid")
        started, expires = (
            _parse_time(intent.valid_from, label="valid_from"),
            _parse_time(intent.expires_at, label="expires_at"),
        )
        if started >= expires:
            raise ConfigurationError("AdvanceStoreBinding validity interval is invalid")
        payload = intent.semantic_payload()
        payload_hash = sha256_hex(canonical_bytes(payload))
        lock_identity = {"writer_id": f"store-binding-advance:{payload_hash}", "command_type": "AdvanceStoreBinding"}
        with CompositeWriterLock((self.control_root,), lock_identity) as writer_lock:
            locked = writer_lock.locked_root(self.control_root)
            marker = _read_existing_marker(locked)
            if marker is not None:
                plan = self._advance_plan(intent, candidate, payload_hash, locked, marker)
                return self._publish_advance(plan, intent, locked, append_binding)
            completed = self._binding_event(payload_hash, intent.idempotency_key)
            if completed is not None:
                return self._completed_advance(completed, payload_hash, locked)
            if not started <= self.now() < expires:
                raise ConfigurationError("AdvanceStoreBinding owner intent is expired")
            try:
                plan = self._advance_plan(intent, candidate, payload_hash, locked, None)
            except _DocumentationOnly as documentation:
                return {"status": "documentation-only-noop", "binding": dict(documentation.predecessor)}
            return self._publish_advance(plan, intent, locked, append_binding)

    def _completed_advance(
        self,
        event: Mapping[str, Any],
        payload_hash: str,
        locked: LockedRoot,
    ) -> dict[str, Any]:
        binding_sha256, binding, receipt = self._completed_binding_terminal(
            event=event,
            payload_hash=payload_hash,
            locked=locked,
            command_prefix="binding-advance",
            command_type="AdvanceStoreBinding",
            expected_schema_version="1.2.0",
            require_governed_manifest=True,
        )
        return {
            "status": "advanced",
            "binding_sha256": binding_sha256,
            "binding": binding,
            "receipt": self._receipt_record(receipt),
        }

    def _advance_plan(
        self,
        intent: AdvanceStoreBinding,
        candidate: _CandidateEvidence,
        payload_hash: str,
        locked: LockedRoot,
        existing_marker: tuple[dict[str, Any], bytes] | None,
    ) -> _AdvancePlan:
        if existing_marker is not None:
            marker, marker_raw = existing_marker
            required = {
                "schema_id",
                "schema_version",
                "command_type",
                "payload_hash",
                "predecessor_binding_sha256",
                "predecessor_binding_raw_hex",
                "binding_raw_hex",
                "binding_sha256",
                "governed_manifest_raw_hex",
                "governed_manifest_sha256",
                "original_manifest_raw_hex",
                "intended_manifest_raw_hex",
                "original_config_raw_hex",
                "intended_config_raw_hex",
                "expected_stream_version",
                "authority_hash",
                "candidate",
            }
            if (
                set(marker) != required
                or marker.get("schema_id") != "ars://internal/store-binding-advance-transaction"
                or marker.get("schema_version") != "1.2.0"
                or marker.get("command_type") != "AdvanceStoreBinding"
                or marker.get("payload_hash") != payload_hash
            ):
                raise ConflictError("binding advance recovery marker conflicts with semantic intent")
            if marker.get("candidate") != candidate.marker_mapping():
                raise ConflictError("binding advance candidate differs from its recovery marker")
            predecessor_raw = _decode_hex(marker["predecessor_binding_raw_hex"], label="predecessor bytes")
            binding_raw = _decode_hex(marker["binding_raw_hex"], label="binding bytes")
            governed_raw = _decode_hex(marker["governed_manifest_raw_hex"], label="governed manifest bytes")
            original_manifest_raw = _decode_hex(marker["original_manifest_raw_hex"], label="original manifest bytes")
            intended_manifest_raw = _decode_hex(marker["intended_manifest_raw_hex"], label="intended manifest bytes")
            original_config_raw = _decode_hex(marker["original_config_raw_hex"], label="original config bytes")
            intended_config_raw = _decode_hex(marker["intended_config_raw_hex"], label="intended config bytes")
            predecessor_sha256 = sha256_hex(predecessor_raw)
            governed_manifest = GovernedCodeManifest.from_mapping(
                _canonical_object(governed_raw, label="governed code manifest")
            )
            if (
                marker.get("predecessor_binding_sha256") != predecessor_sha256
                or marker.get("binding_sha256") != sha256_hex(binding_raw)
                or marker.get("governed_manifest_sha256") != governed_manifest.manifest_sha256
                or type(marker.get("expected_stream_version")) is not int
                or not _is_sha256(marker.get("authority_hash"))
            ):
                raise IntegrityError("binding advance recovery marker hash relation is invalid")
            self.ledger.schemas.validate(
                ADVANCE_OBJECT_SCHEMA_ID,
                _canonical_object(binding_raw, label="binding advance object"),
                schema_version="1.2.0",
            )
            if candidate.manifest != governed_manifest:
                raise IntegrityError("binding advance governed manifest differs from recovery marker")
            current = locked.read_exact_file(CURRENT_BINDING_RELATIVE_PATH.as_posix())
            if current not in {predecessor_raw, binding_raw}:
                raise ConflictError("current binding differs from its recovery marker")
            return _AdvancePlan(
                marker_raw,
                predecessor_raw,
                predecessor_sha256,
                binding_raw,
                sha256_hex(binding_raw),
                governed_raw,
                governed_manifest.manifest_sha256,
                original_manifest_raw,
                intended_manifest_raw,
                original_config_raw,
                intended_config_raw,
                int(marker["expected_stream_version"]),
                payload_hash,
                str(marker["authority_hash"]),
                candidate,
            )

        predecessor_raw = locked.read_exact_file(CURRENT_BINDING_RELATIVE_PATH.as_posix())
        predecessor = _canonical_object(predecessor_raw, label="current binding predecessor")
        predecessor_sha256 = sha256_hex(predecessor_raw)
        if predecessor_sha256 != intent.expected_predecessor_binding_sha256:
            raise ConflictError("AdvanceStoreBinding predecessor binding changed")
        predecessor_roots = predecessor.get("code_roots")
        if (
            not isinstance(predecessor_roots, list)
            or len(predecessor_roots) != 1
            or not isinstance(predecessor_roots[0], str)
        ):
            raise IntegrityError("AdvanceStoreBinding predecessor code root is invalid")
        foundation_path = self.foundation_path or (
            Path(predecessor_roots[0]) / ".research-system" / "config" / "foundation.yaml"
        )
        admitted = load_current_binding(
            foundation_path=foundation_path,
            repository_root=Path(predecessor_roots[0]),
            expected_control_root=self.control_root,
            expected_project_id=self.project_id,
            expected_store_identity=self.store_identity,
            expected_binding_sha256=predecessor_sha256,
        )
        if canonical_bytes(admitted.binding) != predecessor_raw:
            raise ConflictError("AdvanceStoreBinding admitted predecessor changed")
        _validate_origin_authority(
            witness_path=admitted.origin_witness_path,
            expected_witness_sha256=intent.expected_origin_witness_sha256,
            expected_origin_authority_root=intent.expected_origin_authority_root,
            project_id=self.project_id,
            store_identity=self.store_identity,
        )
        if predecessor.get("schema_version") not in {"1.1.0", "1.2.0"}:
            raise IntegrityError("AdvanceStoreBinding predecessor version is unsupported")
        self.ledger.schemas.validate(
            ADVANCE_OBJECT_SCHEMA_ID, predecessor, schema_version=str(predecessor["schema_version"])
        )
        object_path = f"{_BINDING_OBJECT_DIRECTORY}/sha256-{predecessor_sha256}.json"
        if locked.read_exact_file(object_path) != predecessor_raw:
            raise IntegrityError("current binding predecessor immutable object differs from its pointer")
        original_manifest_raw = locked.read_exact_file(_STORE_MANIFEST_PATH)
        original_manifest = _canonical_object(original_manifest_raw, label="current store manifest")
        original_config_raw = locked.read_exact_file(_BINDING_CONFIG_RELATIVE_PATH.as_posix())
        if original_config_raw != _binding_config_bytes(predecessor):
            raise IntegrityError("current binding control config differs from its predecessor")
        if (
            predecessor.get("project_id") != self.project_id
            or predecessor.get("store_identity") != self.store_identity
            or predecessor.get("control_root") != str(self.control_root)
            or predecessor.get("origin_witness_sha256") != intent.expected_origin_witness_sha256
            or original_manifest.get("project_id") != self.project_id
            or original_manifest.get("store_identity") != self.store_identity
            or original_manifest.get("control_root") != str(self.control_root)
        ):
            raise IntegrityError("current binding/store identity is invalid")
        _validate_owner_authority(
            locked,
            original_manifest,
            project_id=self.project_id,
            owner_actor_id=intent.owner_actor_id,
        )
        if original_manifest.get("code_roots") != predecessor.get("code_roots") or original_manifest.get(
            "schema_root"
        ) != predecessor.get("schema_root"):
            raise IntegrityError("current binding differs from materialized store manifest")
        restore = _canonical_object(locked.read_exact_file(_RESTORE_TRANSACTION_PATH), label="restore transaction")
        if (
            restore.get("transaction_id") != predecessor.get("prior_restore_transaction_id")
            or restore.get("intended_manifest_sha256") != predecessor.get("prior_restore_intended_manifest_sha256")
            or not isinstance(restore.get("approval_sha256"), str)
        ):
            raise IntegrityError("current binding restore identity is invalid")
        if (
            intent.reviewed_git_head != candidate.git_head
            or intent.integrated_main_git_head != candidate.git_head
            or _git(candidate.root, "rev-parse", "--verify", f"{_INTEGRATION_REF}^{{commit}}") != candidate.git_head
        ):
            raise IntegrityError("AdvanceStoreBinding reviewed integrated-main subject is not exact")

        if intent.owner_action == "advance-reviewed-divergence-store-binding":
            if (
                predecessor.get("schema_version") != "1.1.0"
                or predecessor.get("owner_action") != "advance-clean-descendant-store-binding"
                or "route_successor_authority" in predecessor
            ):
                raise IntegrityError("reviewed divergence requires the exact clean legacy v1.1 predecessor")
            if predecessor.get("route") != candidate.route or predecessor.get("sources") != candidate.sources:
                raise IntegrityError("reviewed divergence changed protected route or SPEC source bytes")
            authority = {
                "predecessor_binding_sha256": predecessor_sha256,
                "predecessor_git_head": predecessor.get("git_head"),
                "candidate_git_head": candidate.git_head,
                "integration_ref": _INTEGRATION_REF,
                "protected_route_sha256": candidate.route["sha256"],
                "protected_sources_sha256": sha256_hex(canonical_bytes(candidate.sources)),
                "governed_code_manifest_sha256": candidate.manifest.manifest_sha256,
            }
            if intent.reviewed_divergence_authority != authority:
                raise IntegrityError("reviewed divergence authority is not exact")
        elif intent.owner_action == "advance-clean-descendant-store-binding":
            if predecessor.get("schema_version") != "1.2.0":
                raise IntegrityError("clean v1.2 advance requires a v1.2 predecessor")
            if predecessor.get("route") != candidate.route or predecessor.get("sources") != candidate.sources:
                raise IntegrityError("clean v1.2 advance changed protected SPEC evidence")
            predecessor_manifest_path = predecessor.get("governed_code_manifest_path")
            if not isinstance(predecessor_manifest_path, str):
                raise IntegrityError("v1.2 predecessor governed manifest path is invalid")
            predecessor_manifest = GovernedCodeManifest.from_mapping(
                _canonical_object(
                    locked.read_exact_file(predecessor_manifest_path), label="predecessor governed code manifest"
                )
            )
            try:
                successor = validate_reviewed_post_divergence_successor(
                    predecessor_manifest,
                    candidate.root,
                    reviewed_commit=intent.reviewed_git_head,
                    refreshed_main_commit=intent.integrated_main_git_head,
                )
            except IntegrityError as code_error:
                try:
                    validate_reviewed_documentation_successor(
                        predecessor_manifest,
                        candidate.root,
                        successor_commit=intent.reviewed_git_head,
                        reviewed_commit=intent.integrated_main_git_head,
                    )
                except IntegrityError:
                    raise code_error
                return self._documentation_only_result(predecessor)
            if successor.successor_manifest != candidate.manifest:
                raise IntegrityError("reviewed code successor manifest differs from the candidate inventory")
        else:
            raise ConfigurationError("AdvanceStoreBinding owner action is invalid")

        intended_manifest = dict(original_manifest)
        intended_manifest["code_roots"] = [str(candidate.root)]
        intended_manifest["schema_root"] = str(candidate.schema_root)
        intended_manifest["schema_binding_version"] = "1.0.0"
        intended_manifest["manifest_hash"] = _restored_manifest_hash(intended_manifest, str(restore["approval_sha256"]))
        intended_manifest_raw = canonical_bytes(intended_manifest)
        binding_config_raw = canonical_bytes(
            {
                "code_roots": [str(candidate.root)],
                "control_root": str(self.control_root),
                "project_id": self.project_id,
                "schema_root": str(candidate.schema_root),
                "store_identity": self.store_identity,
            }
        )
        binding: dict[str, Any] = {
            **predecessor,
            "schema_version": "1.2.0",
            "code_roots": [str(candidate.root)],
            "schema_root": str(candidate.schema_root),
            "git_head": candidate.git_head,
            "git_tree": candidate.git_tree,
            "schema_catalogue_sha256": candidate.schema_catalogue_sha256,
            "route": candidate.route,
            "sources": candidate.sources,
            "command_payload_hash": payload_hash,
            "owner_actor_id": intent.owner_actor_id,
            "owner_action": intent.owner_action,
            "idempotency_key": intent.idempotency_key,
            "predecessor_binding_sha256": predecessor_sha256,
            "governed_code_manifest_sha256": candidate.manifest.manifest_sha256,
            "governed_code_manifest_path": f"{_GOVERNED_OBJECT_DIRECTORY}/sha256-{candidate.manifest.manifest_sha256}.json",
            "reviewed_git_head": intent.reviewed_git_head,
            "integrated_main_git_head": intent.integrated_main_git_head,
            "integration_ref": _INTEGRATION_REF,
            "binding_config_sha256": sha256_hex(binding_config_raw),
        }
        binding.pop("route_successor_authority", None)
        binding.pop("reviewed_divergence_authority", None)
        if intent.reviewed_divergence_authority is not None:
            binding["reviewed_divergence_authority"] = dict(intent.reviewed_divergence_authority)
        binding_raw = canonical_bytes(binding)
        self.ledger.schemas.validate(ADVANCE_OBJECT_SCHEMA_ID, binding, schema_version="1.2.0")
        governed_raw = canonical_bytes(candidate.manifest.to_mapping())
        snapshot = self.ledger.snapshot()
        expected_stream_version = snapshot.stream_versions.get(self.project_id, 0)
        authority_hash = sha256_hex(canonical_bytes({"actor_id": intent.owner_actor_id, "action": intent.owner_action}))
        marker = {
            "schema_id": "ars://internal/store-binding-advance-transaction",
            "schema_version": "1.2.0",
            "command_type": "AdvanceStoreBinding",
            "payload_hash": payload_hash,
            "predecessor_binding_sha256": predecessor_sha256,
            "predecessor_binding_raw_hex": predecessor_raw.hex(),
            "binding_raw_hex": binding_raw.hex(),
            "binding_sha256": sha256_hex(binding_raw),
            "governed_manifest_raw_hex": governed_raw.hex(),
            "governed_manifest_sha256": candidate.manifest.manifest_sha256,
            "original_manifest_raw_hex": original_manifest_raw.hex(),
            "intended_manifest_raw_hex": intended_manifest_raw.hex(),
            "original_config_raw_hex": original_config_raw.hex(),
            "intended_config_raw_hex": binding_config_raw.hex(),
            "expected_stream_version": expected_stream_version,
            "authority_hash": authority_hash,
            "candidate": candidate.marker_mapping(),
        }
        return _AdvancePlan(
            canonical_bytes(marker),
            predecessor_raw,
            predecessor_sha256,
            binding_raw,
            sha256_hex(binding_raw),
            governed_raw,
            candidate.manifest.manifest_sha256,
            original_manifest_raw,
            intended_manifest_raw,
            original_config_raw,
            binding_config_raw,
            expected_stream_version,
            payload_hash,
            authority_hash,
            candidate,
        )

    def _documentation_only_result(self, predecessor: Mapping[str, Any]) -> _AdvancePlan:
        # This private sentinel is converted before publication; no marker or mutable store write is allowed.
        raise _DocumentationOnly(predecessor)

    def _publish_advance(
        self,
        plan: _AdvancePlan,
        intent: AdvanceStoreBinding,
        locked: LockedRoot,
        append_binding: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            current_marker = _read_existing_marker(locked)
            if current_marker is None:
                _revalidate_candidate(plan.candidate)
                locked.write_exact_file(_MARKER_PATH, plan.marker_raw)
            elif current_marker[1] != plan.marker_raw:
                raise ConflictError("binding advance recovery marker changed before publication")
            if self.phase_hook:
                self.phase_hook("marker")
            locked.write_exact_file(
                f"{_GOVERNED_OBJECT_DIRECTORY}/sha256-{plan.governed_manifest_sha256}.json", plan.governed_manifest_raw
            )
            locked.write_exact_file(f"{_BINDING_OBJECT_DIRECTORY}/sha256-{plan.binding_sha256}.json", plan.binding_raw)
            _replace_or_verify(locked, _STORE_MANIFEST_PATH, plan.original_manifest_raw, plan.intended_manifest_raw)
            _replace_or_verify(
                locked, _BINDING_CONFIG_RELATIVE_PATH.as_posix(), plan.original_config_raw, plan.intended_config_raw
            )
            if self.phase_hook:
                self.phase_hook("mutable-effects")
            event = self._binding_event(plan.payload_hash, intent.idempotency_key)
            if event is None:
                _revalidate_candidate(plan.candidate)
                if self.ledger.snapshot().stream_versions.get(self.project_id, 0) != plan.expected_stream_version:
                    raise ConflictError("binding advance predecessor stream version changed")
                command_binding = self.ledger.schemas.command_binding("AdvanceStoreBinding")
                if (
                    command_binding is None
                    or command_binding.schema_id != ADVANCE_COMMAND_SCHEMA_ID
                    or command_binding.schema_version != "1.2.0"
                ):
                    raise IntegrityError("AdvanceStoreBinding v1.2 is not the active runtime command")
                command_identity = self.ledger.schemas.resolve_identity(
                    command_binding.schema_id, command_binding.schema_version
                )
                self.ledger.schemas.validate(
                    ADVANCE_COMMAND_SCHEMA_ID,
                    {
                        "schema_id": command_identity.schema_id,
                        "schema_version": command_identity.schema_version,
                        "command_type": "AdvanceStoreBinding",
                        "payload": intent.semantic_payload(),
                    },
                    schema_version=command_identity.schema_version,
                )
                appended = append_binding(
                    {
                        "event_type": "StoreBindingAdvanced",
                        "stream_id": self.project_id,
                        "schema_id": ADVANCE_EVENT_SCHEMA_ID,
                        "schema_version": "1.0.0",
                        "command_id": f"binding-advance-{plan.payload_hash}",
                        "command_type": "AdvanceStoreBinding",
                        "idempotency_key": intent.idempotency_key,
                        "command_payload_hash": plan.payload_hash,
                        "correlation_id": intent.idempotency_key,
                        "causation_id": None,
                        "actor_id": intent.owner_actor_id,
                        "authority_grant_id": "store-binding-recovery",
                        "occurred_at": self.now().isoformat().replace("+00:00", "Z"),
                        "command_schema_id": command_identity.schema_id,
                        "command_schema_version": command_identity.schema_version,
                        "command_schema_sha256": command_identity.sha256,
                        "payload": {
                            "recovery_binding_sha256": plan.binding_sha256,
                            "recovery_binding_path": CURRENT_BINDING_RELATIVE_PATH.as_posix(),
                            "object_path": f"{_BINDING_OBJECT_DIRECTORY}/sha256-{plan.binding_sha256}.json",
                            "git_head": plan.candidate.git_head,
                            "git_tree": plan.candidate.git_tree,
                            "predecessor_binding_sha256": plan.predecessor_sha256,
                        },
                    },
                    snapshot=self.ledger.snapshot(),
                )
                event_batch_id = str(appended["event_batch_id"])
                observed_stream_version = int(appended["resulting_stream_versions"][self.project_id])
            else:
                event_batch_id = str(event["transaction_id"])
                observed_stream_version = int(event["stream_version"])
            if self.phase_hook:
                self.phase_hook("event")
            receipt = Receipt(
                "accepted",
                f"binding-advance-{plan.payload_hash}",
                plan.payload_hash,
                event_batch_id,
                observed_stream_version,
                None,
                None,
                (),
            )
            receipt_record = {
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
            self.ledger.schemas.validate(ADVANCE_RECEIPT_SCHEMA_ID, receipt_record)
            self.receipts.write_scoped(
                (intent.owner_actor_id, "store-binding-recovery", "AdvanceStoreBinding", intent.idempotency_key),
                plan.authority_hash,
                plan.expected_stream_version,
                receipt,
                project_id=self.project_id,
                target_stream_id=self.project_id,
            )
            if self.phase_hook:
                self.phase_hook("receipt")
            _replace_or_verify(locked, CURRENT_BINDING_RELATIVE_PATH.as_posix(), plan.predecessor_raw, plan.binding_raw)
            self._readback(plan, intent, receipt)
            locked.remove_exact_file(_MARKER_PATH, plan.marker_raw)
            return {
                "status": "advanced",
                "binding_sha256": plan.binding_sha256,
                "binding": _canonical_object(plan.binding_raw, label="published binding"),
                "receipt": receipt_record,
            }
        except OSError:
            # Keep availability failures distinct from integrity and contention.
            raise

    def _binding_event(self, payload_hash: str, idempotency_key: str) -> dict[str, Any] | None:
        events = [
            event for event in self.ledger.iter_events() if event.get("command_id") == f"binding-advance-{payload_hash}"
        ]
        if not events:
            return None
        if (
            len(events) != 1
            or events[0].get("event_type") != "StoreBindingAdvanced"
            or events[0].get("idempotency_key") != idempotency_key
        ):
            raise IntegrityError("binding advance event history is ambiguous")
        return events[0]

    def _readback(self, plan: _AdvancePlan, intent: AdvanceStoreBinding, receipt: Receipt) -> None:
        if self.control_root.joinpath(*CURRENT_BINDING_RELATIVE_PATH.parts).read_bytes() != plan.binding_raw:
            raise IntegrityError("binding advance current pointer readback differs")
        binding_object_path = self.control_root / _BINDING_OBJECT_DIRECTORY / f"sha256-{plan.binding_sha256}.json"
        if binding_object_path.read_bytes() != plan.binding_raw:
            raise IntegrityError("binding advance immutable object readback differs")
        manifest_path = self.control_root / _GOVERNED_OBJECT_DIRECTORY / f"sha256-{plan.governed_manifest_sha256}.json"
        manifest_raw = manifest_path.read_bytes()
        parsed_manifest = GovernedCodeManifest.from_mapping(
            _canonical_object(manifest_raw, label="binding advance governed manifest")
        )
        if (
            manifest_raw != plan.governed_manifest_raw
            or parsed_manifest.manifest_sha256 != plan.governed_manifest_sha256
        ):
            raise IntegrityError("binding advance governed manifest readback differs")
        event = self._binding_event(plan.payload_hash, intent.idempotency_key)
        if event is None or event.get("stream_version") != receipt.observed_stream_version:
            raise IntegrityError("binding advance event readback differs")
        generic = self.receipts.load(receipt.command_id)
        scoped = self.receipts.load_scoped(
            (intent.owner_actor_id, "store-binding-recovery", "AdvanceStoreBinding", intent.idempotency_key),
            plan.payload_hash,
            plan.authority_hash,
            plan.expected_stream_version,
            project_id=self.project_id,
            target_stream_id=self.project_id,
        )
        if generic != receipt or scoped != receipt:
            raise IntegrityError("binding advance receipt readback differs")


class _DocumentationOnly(Exception):
    def __init__(self, predecessor: Mapping[str, Any]) -> None:
        self.predecessor = dict(predecessor)


@dataclass(frozen=True, slots=True)
class VerifiedBindingContext:
    """Verified current binding plus its optional v1.2 governed-code object."""

    current_binding: VerifiedCurrentBinding
    governed_code_manifest: GovernedCodeManifest | None

    @property
    def binding(self) -> dict[str, Any]:
        return self.current_binding.binding

    @property
    def binding_sha256(self) -> str:
        return self.current_binding.binding_sha256


def load_verified_binding_context(
    *,
    foundation_path: Path,
    repository_root: Path,
    expected_control_root: Path,
    expected_project_id: str,
    expected_store_identity: str,
) -> VerifiedBindingContext:
    verified = load_current_binding(
        foundation_path=foundation_path,
        repository_root=repository_root,
        expected_control_root=expected_control_root,
        expected_project_id=expected_project_id,
        expected_store_identity=expected_store_identity,
    )
    binding = verified.binding
    manifest: GovernedCodeManifest | None = None
    if binding.get("schema_version") == "1.2.0":
        raw = (expected_control_root / str(binding["governed_code_manifest_path"])).read_bytes()
        manifest = GovernedCodeManifest.from_mapping(_canonical_object(raw, label="verified governed manifest"))
        if manifest.manifest_sha256 != binding.get("governed_code_manifest_sha256"):
            raise IntegrityError("verified binding governed manifest hash is invalid")
        validate_persisted_governed_code_manifest(
            manifest,
            repository_root,
            expected_commit=str(binding["git_head"]),
        )
    return VerifiedBindingContext(current_binding=verified, governed_code_manifest=manifest)


__all__ = [
    "AdvanceStoreBinding",
    "RepairStoreBinding",
    "StoreBindingService",
    "VerifiedBindingContext",
    "load_verified_binding_context",
    "read_advance_intent",
    "read_repair_intent",
]
