from __future__ import annotations

import json
import os
import secrets
import sys
import time

from collections.abc import Callable, Iterable
from copy import deepcopy
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.authority import (
    AuthorityAdministrationContext,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    GrantedCommandIdentity,
    LedgerAuthorityGrantResolver,
    LifecycleCommandAuthorityEvidence,
    SCOPED_AUTHORITY_ADMISSION_VERSION,
    SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
    SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
    ScopedAuthorityGrant,
    ScopedAuthorityGrantResolution,
    validate_scoped_grant_activation,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.lifecycle import (
    changed_task_fields,
    content_hash_matches,
    has_unique_member_ids,
    materialize_scope_member_changes,
)
from research_system.command.models import Command, Receipt
from research_system.command.t2 import T2_COMMAND_TYPES, T2Receipt, submit_t2
from research_system.errors import (
    ArsError,
    ConflictError,
    IdempotencyConflictError,
    IntegrityError,
    SchemaError,
)
from research_system.evals.release_publication import (
    PublicationEvidenceError,
    ReleasePublicationEvidenceResolver,
    ReleasePublicationRequest,
    VerifiedReleasePublication,
    verify_release_publication,
)
from research_system.ids import new_id, validate_id
from research_system.operations.backups import (
    RestorePreflightResult,
    validate_restore_preflight_result,
)
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaIdentity, SchemaRegistry
from research_system.store.ledger import (
    EventLedger,
    LedgerSnapshot,
    _take_release_submit_guard,
)
from research_system.store.identity import StoreOriginWitness, _physical_root_identity
from research_system.store.lock import (
    CompositeWriterLock,
    WriterLock,
    current_process_instance_id,
    inspect_lock,
    remove_stale_lock,
)
from research_system.store.durability import fsync_directory
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


_release_submit_guard = _take_release_submit_guard()
_CALLER_PROVENANCE_FIELDS = frozenset(
    {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }
)
_SCOPE_COMMAND_TYPES = frozenset(
    {
        "CreateScopeDefinition",
        "AmendScopeDefinition",
        "SupersedeScopeDefinition",
    }
)
_TASK_REVISION_COMMAND_TYPES = frozenset(
    {
        "CreateTask",
        "AmendTask",
        "SupersedeTask",
    }
)
_MESSAGE_COMMAND_TYPES = frozenset(
    {
        "PublishMessage",
        "RecordMessageDelivery",
        "AcknowledgeMessage",
        "RecordMessageDeliveryFailure",
    }
)
_MESSAGE_ADAPTER_COMMAND_TYPES = frozenset({"RecordMessageDelivery", "RecordMessageDeliveryFailure"})
_LIFECYCLE_COMMAND_TYPES = _SCOPE_COMMAND_TYPES | _TASK_REVISION_COMMAND_TYPES | _MESSAGE_COMMAND_TYPES
_COMMAND_EVENT_TYPES = {
    "PublishReleaseGateDecision": "ReleaseGateDecisionPublished",
    "ActivateAuthorityGrant": "AuthorityGrantActivated",
    "ActivateExternalAssuranceRecordGrant": "AuthorityGrantActivated",
    "RevokeAuthorityGrant": "AuthorityGrantRevoked",
    "RevokeIssuedAuthorityGrant": "AuthorityGrantRevoked",
    "RevokeExternalAssuranceRecordGrant": "AuthorityGrantRevoked",
    "CreateScopeDefinition": "ScopeDefinitionCreated",
    "AmendScopeDefinition": "ScopeDefinitionAmended",
    "SupersedeScopeDefinition": "ScopeDefinitionSuperseded",
    "CreateTask": "TaskCreated",
    "AmendTask": "TaskAmended",
    "SupersedeTask": "TaskSuperseded",
    "PublishMessage": "MessagePublished",
    "RecordMessageDelivery": "MessageDelivered",
    "AcknowledgeMessage": "MessageAcknowledged",
    "RecordMessageDeliveryFailure": "MessageDeliveryFailed",
}
_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES = frozenset(
    {
        "ActivateAuthorityGrant",
        "RevokeIssuedAuthorityGrant",
        "ActivateExternalAssuranceRecordGrant",
        "RevokeExternalAssuranceRecordGrant",
    }
)
_SCOPED_ACTIVATION_COMMAND_TYPES = frozenset(
    {
        "ActivateAuthorityGrant",
        "ActivateExternalAssuranceRecordGrant",
    }
)
_SCOPED_ACTIVATION_MARKER_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "command_id",
        "command_sha256",
        "command_identity",
        "target_grant_id",
        "target_generation",
        "prepared_identity",
        "object_kind",
        "object_revision",
        "object_existed_before",
        "owner_pid",
        "owner_process_instance_id",
        "object_sha256",
        "object_value",
    }
)
_SCOPED_ACTIVATION_MARKER_BINDING_FIELDS = _SCOPED_ACTIVATION_MARKER_FIELDS - {
    "owner_pid",
    "owner_process_instance_id",
}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


_T2_AUTHORITY_COORDINATED_COMMAND_TYPES = frozenset(
    {
        "IssueCostGrant",
        "AuthorizeProviderIssue",
    }
)
_AUTHORITY_COORDINATED_COMMAND_TYPES = _LIFECYCLE_COMMAND_TYPES | frozenset(
    {
        "PublishReleaseGateDecision",
        "RevokeAuthorityGrant",
        *_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES,
        *_T2_AUTHORITY_COORDINATED_COMMAND_TYPES,
    }
)


@dataclass
class _CommandView:
    fingerprint: tuple[tuple[str, int, int], ...]
    batches_by_command_id: dict[str, list[dict[str, Any]]]
    batches_by_scope: dict[
        tuple[str, str, str, str, str | None, str | None, str | None],
        list[dict[str, Any]],
    ]
    base_scopes: set[tuple[str, str, str, str]]
    stream_versions: dict[str, int]

    @classmethod
    def from_snapshot(
        cls,
        snapshot: LedgerSnapshot,
        schemas: SchemaRegistry,
        authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
    ) -> _CommandView:
        replay(
            snapshot.events,
            schema_registry=schemas,
            authority_state_validator=authority_state_validator,
        )
        view = cls(
            snapshot.fingerprint,
            {},
            {},
            set(),
            dict(snapshot.stream_versions),
        )
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in snapshot.events:
            batches.setdefault(event["transaction_id"], []).append(event)
        for batch in batches.values():
            view._index_batch(batch)
        return view

    def extend(
        self,
        events: tuple[dict[str, Any], ...],
        fingerprint: tuple[tuple[str, int, int], ...],
    ) -> None:
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            batches.setdefault(event["transaction_id"], []).append(event)
            self.stream_versions[event["stream_id"]] = event["stream_version"]
        for batch in batches.values():
            self._index_batch(batch)
        self.fingerprint = fingerprint

    def _index_batch(self, batch: list[dict[str, Any]]) -> None:
        first = batch[0]
        self.batches_by_command_id[first["command_id"]] = batch
        base_scope = (
            first["actor_id"],
            first["authority_grant_id"],
            first["command_type"],
            first["idempotency_key"],
        )
        self.base_scopes.add(base_scope)
        self.batches_by_scope[
            (
                *base_scope,
                first.get("command_schema_id"),
                first.get("command_schema_version"),
                first.get("command_schema_sha256"),
            )
        ] = batch


@dataclass(frozen=True)
class _TaskRevisionEvidence:
    schema_id: str
    definition: dict[str, Any] | None

    @property
    def exact(self) -> bool:
        return self.schema_id in {
            "ars://core/event/TaskCreated",
            "ars://core/event/TaskAmended",
        }


@dataclass(frozen=True)
class _LifecycleAuthorityEvidence:
    binding: dict[str, Any]
    resolution: dict[str, Any] | None
    canonical_resolution: dict[str, Any] | None
    authority_key: str
    denial: str | None = None


def _validate_moved_restore_source_lineage(
    source_root: Path,
    preflight_result: RestorePreflightResult,
    approved_witness: StoreOriginWitness,
) -> None:
    if not isinstance(preflight_result, RestorePreflightResult):
        raise ArsError("restore source lineage is invalid")
    if not isinstance(preflight_result.source_root, str) or not preflight_result.source_root:
        raise ArsError("restore source lineage is missing")
    try:
        configured_root = source_root.resolve(strict=True)
        preflight_root = Path(preflight_result.source_root).resolve(strict=True)
        witness_root = Path(approved_witness.initial_control_root).resolve(strict=True)
        configured_identity = _physical_root_identity(configured_root)
        preflight_identity = _physical_root_identity(preflight_root)
        witness_identity = _physical_root_identity(witness_root)
    except (ArsError, OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ArsError("restore source lineage identity is unavailable") from exc
    if (
        configured_root != witness_root
        or preflight_root != witness_root
        or configured_identity != approved_witness.initial_physical_root_identity
        or preflight_identity != approved_witness.initial_physical_root_identity
        or witness_identity != approved_witness.initial_physical_root_identity
    ):
        raise ArsError("restore source lineage differs from approved origin witness")


@dataclass(frozen=True)
class MessageAdapterRegistration:
    """An immutable, service-local snapshot entry for one Message adapter."""

    delivery_adapter_id: str
    project_id: str
    registry_revision: str
    registry_content_sha256: str
    status: str
    effective_at: datetime
    expires_at: datetime | None
    applicable_command_types: tuple[str, ...]
    allowed_actor_ids: tuple[str, ...]

    def canonical_content(self) -> dict[str, Any]:
        """Return the immutable content bound by ``registry_content_sha256``."""
        return {
            "delivery_adapter_id": self.delivery_adapter_id,
            "project_id": self.project_id,
            "registry_revision": self.registry_revision,
            "status": self.status,
            "effective_at": self.effective_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "expires_at": (
                None if self.expires_at is None else self.expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            ),
            "applicable_command_types": list(self.applicable_command_types),
            "allowed_actor_ids": list(self.allowed_actor_ids),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.delivery_adapter_id, str) or not self.delivery_adapter_id:
            raise ValueError("message adapter ID must be non-empty")
        validate_id(self.project_id, "project")
        if not isinstance(self.registry_revision, str) or not self.registry_revision:
            raise ValueError("message adapter registry revision must be non-empty")
        if (
            not isinstance(self.registry_content_sha256, str)
            or len(self.registry_content_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.registry_content_sha256)
        ):
            raise ValueError("message adapter registry content hash must be a lowercase SHA-256")
        if self.status not in {"eligible", "suspended", "retired"}:
            raise ValueError("message adapter status is unsupported")
        if type(self.effective_at) is not datetime or self.effective_at.tzinfo is None:
            raise ValueError("message adapter effective_at must be timezone-aware")
        if self.expires_at is not None and (
            type(self.expires_at) is not datetime
            or self.expires_at.tzinfo is None
            or self.expires_at <= self.effective_at
        ):
            raise ValueError("message adapter expiry must follow effective_at")
        if (
            not isinstance(self.applicable_command_types, tuple)
            or not self.applicable_command_types
            or not set(self.applicable_command_types).issubset(_MESSAGE_ADAPTER_COMMAND_TYPES)
            or len(set(self.applicable_command_types)) != len(self.applicable_command_types)
        ):
            raise ValueError("message adapter capabilities must be exact and non-empty")
        if (
            not isinstance(self.allowed_actor_ids, tuple)
            or not self.allowed_actor_ids
            or len(set(self.allowed_actor_ids)) != len(self.allowed_actor_ids)
        ):
            raise ValueError("message adapter allowed actors must be exact and non-empty")
        for actor_id in self.allowed_actor_ids:
            validate_id(actor_id, "actor")
        if self.registry_content_sha256 != sha256_hex(canonical_bytes(self.canonical_content())):
            raise ValueError("message adapter registry content hash does not bind its immutable entry")


class CommandService:
    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        objects: ObjectStore,
        receipts: ReceiptStore,
        schemas: SchemaRegistry,
        *,
        authority_resolver: LedgerAuthorityGrantResolver | None = None,
        release_publication_evidence: ReleasePublicationEvidenceResolver | None = None,
        clock: Callable[[], datetime] | None = None,
        release_lock_timeout_seconds: float = 300.0,
        recovery_lock_timeout_seconds: float = 1.0,
        monotonic: Callable[[], float] | None = None,
        lock_wait: Callable[[float], None] | None = None,
        t2_authority_resolver: Callable[[str, str, int], Any | None] | None = None,
        message_adapter_registry: Iterable[MessageAdapterRegistration] | None = None,
    ) -> None:
        if authority_resolver is not None and type(authority_resolver) is not LedgerAuthorityGrantResolver:
            raise TypeError("authority_resolver must be LedgerAuthorityGrantResolver")
        self.control_root = control_root
        self.ledger = ledger
        self.objects = objects
        self.receipts = receipts
        self.schemas = schemas
        self.authority_resolver = authority_resolver
        self.release_publication_evidence = release_publication_evidence
        self.clock = clock or (lambda: datetime.now(UTC))
        if release_lock_timeout_seconds <= 0:
            raise ValueError("release lock timeout must be positive")
        if recovery_lock_timeout_seconds <= 0:
            raise ValueError("recovery lock timeout must be positive")
        self.release_lock_timeout_seconds = release_lock_timeout_seconds
        self.recovery_lock_timeout_seconds = recovery_lock_timeout_seconds
        self._monotonic = monotonic or time.monotonic
        self._lock_wait = lock_wait or time.sleep
        self.t2_authority_resolver = t2_authority_resolver
        if message_adapter_registry is None:
            self._message_adapter_registry: tuple[MessageAdapterRegistration, ...] = ()
        else:
            snapshot = tuple(message_adapter_registry)
            if any(type(entry) is not MessageAdapterRegistration for entry in snapshot):
                raise TypeError("message adapter registry entries must be MessageAdapterRegistration")
            self._message_adapter_registry = snapshot
        self._t2_authority_root: Path | None = None
        self._t2_authority_identity: tuple[int, int] | None = None
        if t2_authority_resolver is not None:
            (
                self._t2_authority_root,
                self._t2_authority_identity,
            ) = self._freeze_t2_authority_root(t2_authority_resolver)
        self._view: _CommandView | None = None
        self.deletion_manifest_authorizer: (
            Callable[
                [dict[str, Any], str, str],
                dict[str, Any],
            ]
            | None
        ) = None
        self._restore_source_root: Path | None = None
        self._restore_approved_witness: StoreOriginWitness | None = None
        self._restore_preflight_result: RestorePreflightResult | None = None
        self._restore_preflight_rechecker: Callable[[], RestorePreflightResult] | None = None
        self._recover_scoped_activation_markers()

    def _scoped_activation_marker_path(self, command_id: str) -> Path:
        return self.control_root / "runtime" / "scoped-authority-activation-recovery" / f"{command_id}.json"

    @staticmethod
    def _scoped_activation_command_identity(
        command: Command,
        command_schema: SchemaIdentity,
    ) -> dict[str, Any]:
        return {
            "envelope": command.envelope,
            "resolved_schema": {
                "schema_id": command_schema.schema_id,
                "schema_version": str(command_schema.schema_version),
                "sha256": command_schema.sha256,
            },
        }

    @classmethod
    def _validate_scoped_activation_marker_command(
        cls,
        marker: dict[str, Any],
        command: Command,
        command_schema: SchemaIdentity,
    ) -> None:
        identity = cls._scoped_activation_command_identity(command, command_schema)
        if marker["command_identity"] != identity or marker["command_sha256"] != sha256_hex(canonical_bytes(identity)):
            raise ConflictError("scoped activation recovery marker conflicts")

    def _validate_scoped_activation_marker_event_schema(self, marker: dict[str, Any]) -> None:
        prepared = marker["prepared_identity"]
        event_binding = self.schemas.event_binding(
            prepared["event_type"],
            prepared["command_type"],
        )
        event_schema_id = event_binding.schema_id if event_binding is not None else "ars://core/event"
        event_schema_version = event_binding.schema_version if event_binding is not None else "1.0.0"
        try:
            event_schema = self.schemas.resolve_identity(event_schema_id, event_schema_version)
        except SchemaError as exc:
            raise ConflictError("scoped activation recovery marker conflicts") from exc
        if (
            prepared["event_schema_id"],
            prepared["event_schema_version"],
            prepared["event_schema_sha256"],
        ) != (
            event_schema.schema_id,
            str(event_schema.schema_version),
            event_schema.sha256,
        ):
            raise ConflictError("scoped activation recovery marker conflicts")

    def _scoped_activation_marker_temporary_paths(self, path: Path) -> tuple[Path, ...]:
        candidates = [path.with_suffix(".json.tmp"), *sorted(path.parent.glob(f".{path.name}.*.tmp"))]
        return tuple(dict.fromkeys(candidates))

    @staticmethod
    def _quarantine_scoped_activation_marker_temp(path: Path) -> None:
        target = path.with_name(f"{path.name}.quarantine")
        while target.exists():
            target = path.with_name(f"{path.name}.{secrets.token_hex(8)}.quarantine")
        try:
            os.replace(path, target)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise IntegrityError("scoped activation recovery marker temporary data cannot be quarantined") from exc
        fsync_directory(target.parent)

    def _write_scoped_activation_marker(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
        existed_before: bool,
    ) -> None:
        payload = command.envelope.get("payload")
        grant = payload.get("new_grant") if isinstance(payload, dict) else None
        if not isinstance(grant, dict):
            raise IntegrityError("scoped activation recovery marker requires a grant object")
        command_identity = self._scoped_activation_command_identity(command, command_schema)
        event_binding = self.schemas.event_binding(
            "AuthorityGrantActivated",
            command.envelope["command_type"],
        )
        event_schema_id = event_binding.schema_id if event_binding is not None else "ars://core/event"
        event_schema_version = event_binding.schema_version if event_binding is not None else "1.0.0"
        event_schema = self.schemas.resolve_identity(event_schema_id, event_schema_version)
        object_sha256 = sha256_hex(canonical_bytes(grant))
        marker = {
            "schema_id": "ars://core/runtime/scoped-authority-activation-recovery",
            "schema_version": "2.0.0",
            "command_id": command.command_id,
            "command_sha256": sha256_hex(canonical_bytes(command_identity)),
            "command_identity": command_identity,
            "target_grant_id": command.target_stream_id,
            "target_generation": {
                "target_stream_id": command.target_stream_id,
                "expected_stream_version": command.expected_stream_version,
                "resulting_stream_version": command.expected_stream_version + 1,
                "object_revision": 1,
            },
            "prepared_identity": {
                "event_type": "AuthorityGrantActivated",
                "event_schema_id": event_schema_id,
                "event_schema_version": event_schema_version,
                "event_schema_sha256": event_schema.sha256,
                "stream_id": command.target_stream_id,
                "stream_version": command.expected_stream_version + 1,
                "command_id": command.command_id,
                "command_type": command.envelope["command_type"],
                "command_schema_id": command_schema.schema_id,
                "command_schema_version": str(command_schema.schema_version),
                "command_schema_sha256": command_schema.sha256,
                "command_payload_hash": command.payload_hash,
                "object_kind": "authority_grant",
                "object_revision": 1,
                "object_sha256": object_sha256,
            },
            "object_kind": "authority_grant",
            "object_revision": 1,
            "object_existed_before": existed_before,
            "owner_pid": os.getpid(),
            "owner_process_instance_id": current_process_instance_id(),
            "object_sha256": object_sha256,
            "object_value": grant,
        }
        data = canonical_bytes(marker)
        path = self._scoped_activation_marker_path(command.command_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        for temporary in self._scoped_activation_marker_temporary_paths(path):
            if not temporary.exists():
                continue
            try:
                existing = self._load_scoped_activation_marker(temporary)
            except IntegrityError:
                self._quarantine_scoped_activation_marker_temp(temporary)
                continue
            if any(existing[field] != marker[field] for field in _SCOPED_ACTIVATION_MARKER_BINDING_FIELDS):
                raise ConflictError("scoped activation recovery marker temporary data conflicts")
            if path.exists():
                temporary.unlink(missing_ok=True)
                fsync_directory(path.parent)
            else:
                os.replace(temporary, path)
                fsync_directory(path.parent)
                return
        if path.exists():
            existing = self._load_scoped_activation_marker(path)
            if any(existing[field] != marker[field] for field in _SCOPED_ACTIVATION_MARKER_BINDING_FIELDS):
                raise ConflictError("scoped activation recovery marker conflicts")
            return
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            fsync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def _cleanup_scoped_activation_marker_residue(
        self,
        residue: list[tuple[Path, dict[str, Any]]],
    ) -> bool:
        changed = False
        for temporary, _existing in residue:
            temporary.unlink(missing_ok=True)
            changed = True
        return changed

    def _remove_scoped_activation_marker(self, command_id: str) -> None:
        path = self._scoped_activation_marker_path(command_id)
        final_marker = self._load_scoped_activation_marker(path) if path.exists() else None
        residue: list[tuple[Path, dict[str, Any]]] = []
        for temporary in self._scoped_activation_marker_temporary_paths(path):
            if not temporary.exists():
                continue
            try:
                existing = self._load_scoped_activation_marker(temporary)
            except IntegrityError as exc:
                raise IntegrityError("scoped activation recovery marker temporary data is invalid") from exc
            if final_marker is None or any(
                existing[field] != final_marker[field] for field in _SCOPED_ACTIVATION_MARKER_BINDING_FIELDS
            ):
                raise ConflictError("scoped activation recovery marker temporary data conflicts")
            residue.append((temporary, existing))
        changed = final_marker is not None
        path.unlink(missing_ok=True)
        if self._cleanup_scoped_activation_marker_residue(residue):
            changed = True
        if changed and path.parent.exists():
            fsync_directory(path.parent)

    @staticmethod
    def _load_scoped_activation_marker(path: Path) -> dict[str, Any]:
        try:
            data = path.read_bytes()
            marker = json.loads(data)
            canonical = canonical_bytes(marker)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise IntegrityError("scoped activation recovery marker is invalid") from exc
        if (
            not isinstance(marker, dict)
            or set(marker) != _SCOPED_ACTIVATION_MARKER_FIELDS
            or data != canonical
            or marker.get("schema_id") != "ars://core/runtime/scoped-authority-activation-recovery"
            or marker.get("schema_version") != "2.0.0"
            or not isinstance(marker.get("command_id"), str)
            or not _is_sha256(marker.get("command_sha256"))
            or not isinstance(marker.get("target_grant_id"), str)
            or marker.get("object_kind") != "authority_grant"
            or marker.get("object_revision") != 1
            or not isinstance(marker.get("object_existed_before"), bool)
            or not isinstance(marker.get("owner_pid"), int)
            or isinstance(marker.get("owner_pid"), bool)
            or marker.get("owner_pid") < 1
            or not isinstance(marker.get("owner_process_instance_id"), str)
            or not marker.get("owner_process_instance_id")
            or not isinstance(marker.get("object_value"), dict)
            or marker.get("object_sha256") != sha256_hex(canonical_bytes(marker.get("object_value")))
        ):
            raise IntegrityError("scoped activation recovery marker is invalid")
        identity = marker["command_identity"]
        resolved_schema = identity.get("resolved_schema") if isinstance(identity, dict) else None
        envelope = identity.get("envelope") if isinstance(identity, dict) else None
        if (
            not isinstance(identity, dict)
            or set(identity) != {"envelope", "resolved_schema"}
            or not isinstance(envelope, dict)
            or not isinstance(resolved_schema, dict)
            or set(resolved_schema) != {"schema_id", "schema_version", "sha256"}
            or not isinstance(resolved_schema.get("schema_id"), str)
            or not isinstance(resolved_schema.get("schema_version"), str)
            or not _is_sha256(resolved_schema.get("sha256"))
            or marker["command_sha256"] != sha256_hex(canonical_bytes(identity))
            or envelope.get("command_id") != marker["command_id"]
            or envelope.get("target_stream_id") != marker["target_grant_id"]
        ):
            raise IntegrityError("scoped activation recovery marker command identity is invalid")
        generation = marker["target_generation"]
        if (
            not isinstance(generation, dict)
            or set(generation)
            != {"target_stream_id", "expected_stream_version", "resulting_stream_version", "object_revision"}
            or generation.get("target_stream_id") != marker["target_grant_id"]
            or not isinstance(generation.get("expected_stream_version"), int)
            or isinstance(generation.get("expected_stream_version"), bool)
            or generation.get("expected_stream_version") < 0
            or generation.get("resulting_stream_version") != generation.get("expected_stream_version") + 1
            or generation.get("object_revision") != marker["object_revision"]
        ):
            raise IntegrityError("scoped activation recovery marker target generation is invalid")
        prepared = marker["prepared_identity"]
        try:
            expected_payload_hash = sha256_hex(canonical_bytes(envelope["payload"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("scoped activation recovery marker command payload is invalid") from exc
        if (
            not isinstance(prepared, dict)
            or set(prepared)
            != {
                "event_type",
                "event_schema_id",
                "event_schema_version",
                "event_schema_sha256",
                "stream_id",
                "stream_version",
                "command_id",
                "command_type",
                "command_schema_id",
                "command_schema_version",
                "command_schema_sha256",
                "command_payload_hash",
                "object_kind",
                "object_revision",
                "object_sha256",
            }
            or prepared.get("event_type") != "AuthorityGrantActivated"
            or not isinstance(prepared.get("event_schema_id"), str)
            or not isinstance(prepared.get("event_schema_version"), str)
            or not _is_sha256(prepared.get("event_schema_sha256"))
            or prepared.get("stream_id") != marker["target_grant_id"]
            or prepared.get("stream_version") != generation["resulting_stream_version"]
            or prepared.get("command_id") != marker["command_id"]
            or prepared.get("command_type") != envelope.get("command_type")
            or prepared.get("command_schema_id") != resolved_schema["schema_id"]
            or prepared.get("command_schema_version") != resolved_schema["schema_version"]
            or prepared.get("command_schema_sha256") != resolved_schema["sha256"]
            or prepared.get("command_payload_hash") != expected_payload_hash
            or prepared.get("object_kind") != marker["object_kind"]
            or prepared.get("object_revision") != marker["object_revision"]
            or prepared.get("object_sha256") != marker["object_sha256"]
        ):
            raise IntegrityError("scoped activation recovery marker prepared identity is invalid")
        return marker

    def _take_scoped_activation_recovery_lock(
        self,
        marker: dict[str, Any],
    ) -> WriterLock | None:
        path = self.control_root / "runtime" / "writer.lock"
        deadline = self._monotonic() + self.recovery_lock_timeout_seconds
        while True:
            lock = WriterLock(
                path,
                {
                    "operation": "scoped_activation_recovery",
                    "command_id": marker["command_id"],
                },
            )
            try:
                lock.__enter__()
            except ConflictError:
                state, observed, _ = inspect_lock(path)
                if state == "stale" and observed is not None and remove_stale_lock(path, observed):
                    continue
                if self._monotonic() >= deadline:
                    return None
                self._lock_wait(min(0.01, max(0.0, deadline - self._monotonic())))
                continue
            return lock

    @staticmethod
    def _scoped_activation_event_payload(marker: dict[str, Any]) -> dict[str, Any]:
        envelope = marker["command_identity"]["envelope"]
        payload = envelope["payload"]
        grant = payload["new_grant"]
        return {
            "authority_admission_version": SCOPED_AUTHORITY_ADMISSION_VERSION,
            "project_id": envelope["project_id"],
            "bootstrap_manifest_sha256": payload["bootstrap_manifest_sha256"],
            "root_grant_id": payload["root_grant_id"],
            "root_grant_sha256": payload["root_grant_sha256"],
            "administration_decision_id": payload["administration_decision_id"],
            "administration_decision_sha256": payload["administration_decision_sha256"],
            "activated_grant_id": marker["target_grant_id"],
            "activated_grant_sha256": marker["object_sha256"],
            "activated_grant_schema_id": grant["schema_id"],
            "activated_grant_schema_version": grant["schema_version"],
            "activated_grant_schema_sha256": payload["new_grant_schema_sha256"],
            "subject_scope": grant["subject_scope"],
            "effective_at": grant["effective_at"],
            "expires_at": grant["expires_at"],
        }

    @classmethod
    def _scoped_activation_event_matches(
        cls,
        marker: dict[str, Any],
        event: dict[str, Any],
    ) -> bool:
        identity = marker["command_identity"]
        envelope = identity["envelope"]
        resolved_schema = identity["resolved_schema"]
        generation = marker["target_generation"]
        prepared = marker["prepared_identity"]
        expected = {
            "event_type": "AuthorityGrantActivated",
            "stream_id": marker["target_grant_id"],
            "stream_version": generation["resulting_stream_version"],
            "project_id": envelope["project_id"],
            "command_id": marker["command_id"],
            "command_type": envelope["command_type"],
            "command_schema_id": resolved_schema["schema_id"],
            "command_schema_version": resolved_schema["schema_version"],
            "command_schema_sha256": resolved_schema["sha256"],
            "actor_id": envelope["actor_id"],
            "authority_grant_id": envelope["authority_grant_id"],
            "idempotency_key": envelope["idempotency_key"],
            "command_payload_hash": prepared["command_payload_hash"],
            "correlation_id": envelope["correlation_id"],
            "causation_id": envelope["causation_id"],
            "schema_id": prepared["event_schema_id"],
            "schema_version": prepared["event_schema_version"],
        }
        return all(event.get(key) == value for key, value in expected.items()) and event.get(
            "payload"
        ) == cls._scoped_activation_event_payload(marker)

    def _scoped_activation_event_status(self, marker: dict[str, Any]) -> str:
        """Classify the exact prepared generation without trusting target alone."""
        self._validate_scoped_activation_marker_event_schema(marker)
        events = self.ledger.snapshot().events
        same_command = [event for event in events if event.get("command_id") == marker["command_id"]]
        if same_command:
            if len(same_command) != 1 or not self._scoped_activation_event_matches(marker, same_command[0]):
                raise IntegrityError("scoped activation recovery event identity mismatch")
            return "committed"
        generation = marker["target_generation"]
        target_events = [
            event
            for event in events
            if event.get("stream_id") == marker["target_grant_id"]
            and isinstance(event.get("stream_version"), int)
            and not isinstance(event.get("stream_version"), bool)
            and event["stream_version"] >= generation["resulting_stream_version"]
        ]
        return "competing" if target_events else "uncommitted"

    def _reconcile_scoped_activation_marker(
        self,
        marker: dict[str, Any],
        *,
        status: str | None = None,
    ) -> str:
        status = self._scoped_activation_event_status(marker) if status is None else status
        if status in {"committed", "competing"}:
            try:
                actual = self.objects.read(
                    marker["object_kind"],
                    marker["target_grant_id"],
                    marker["object_revision"],
                )
            except (IntegrityError, ValueError) as exc:
                raise IntegrityError(f"{status} scoped activation recovery object is invalid") from exc
            if actual != marker["object_value"]:
                raise IntegrityError(f"{status} scoped activation recovery object mismatch")
            self._remove_scoped_activation_marker(marker["command_id"])
        else:
            self.objects.rollback_new_revision(
                marker["object_kind"],
                marker["target_grant_id"],
                marker["object_revision"],
                marker["object_value"],
                existed_before=marker["object_existed_before"],
            )
            # Keep the canonical command identity until an exact retry
            # commits or the command ID is otherwise collision-checked.
        return status

    def _scoped_activation_marker_committed(self, marker: dict[str, Any]) -> bool:
        return self._scoped_activation_event_status(marker) == "committed"

    def _recover_scoped_activation_markers(self) -> None:
        root = self.control_root / "runtime" / "scoped-authority-activation-recovery"
        if not root.exists():
            return
        for path in sorted(root.glob("*.json")):
            marker = self._load_scoped_activation_marker(path)
            self._validate_scoped_activation_marker_event_schema(marker)
            lock = self._take_scoped_activation_recovery_lock(marker)
            if lock is None:
                continue
            try:
                status = self._scoped_activation_event_status(marker)
                self._reconcile_scoped_activation_marker(marker, status=status)
            finally:
                lock.__exit__(*sys.exc_info())

    def configure_moved_restore(
        self,
        *,
        source_root: Path,
        preflight_result: RestorePreflightResult,
        rechecker: Callable[[], RestorePreflightResult],
        approved_witness: StoreOriginWitness | None = None,
    ) -> None:
        """Bind a moved store to evidence that is rerun before each writer lock."""
        if source_root.resolve(strict=False) == self.control_root.resolve(strict=False):
            raise ValueError("moved restore source must differ from target")
        if approved_witness is None:
            raise ValueError("moved restore requires an approved origin witness")
        _validate_moved_restore_source_lineage(source_root, preflight_result, approved_witness)
        self._restore_source_root = source_root
        self._restore_approved_witness = approved_witness
        self._restore_preflight_result = preflight_result
        self._restore_preflight_rechecker = rechecker

    def _recheck_moved_restore(self, command: Command) -> None:
        if self._restore_source_root is None:
            return
        supplied = self._restore_preflight_result
        rechecker = self._restore_preflight_rechecker
        if supplied is None or rechecker is None or self._restore_approved_witness is None:
            raise ArsError("moved store requires restore preflight")
        current = rechecker()
        _validate_moved_restore_source_lineage(
            self._restore_source_root,
            current,
            self._restore_approved_witness,
        )
        validate_restore_preflight_result(
            current,
            current_root=self.control_root,
            project_id=self.ledger.project_id,
            actor_id=command.actor_id,
            authority_grant_id=command.envelope["authority_grant_id"],
            approved_witness=self._restore_approved_witness,
        )
        if current != supplied:
            raise ArsError("restore preflight changed before writer lock")

    @_release_submit_guard
    def submit(
        self,
        envelope: dict[str, Any],
        release_append: Callable[..., dict[str, Any]] | None = None,
        scoped_authority_append: Callable[..., dict[str, Any]] | None = None,
    ) -> Receipt | T2Receipt:
        """Validate WP1 integrity controls; authorization remains downstream."""
        if release_append is None or scoped_authority_append is None:
            raise ArsError("CommandService.submit requires its guarded continuations")
        if envelope.get("command_type") in T2_COMMAND_TYPES:
            return submit_t2(self, envelope)
        validated_envelope = {key: value for key, value in envelope.items() if key not in _CALLER_PROVENANCE_FIELDS}
        schema_id = str(validated_envelope.get("schema_id", ""))
        schema_version = str(validated_envelope.get("schema_version", ""))
        command_type = str(validated_envelope.get("command_type", ""))
        command_binding = self.schemas.command_binding(command_type)
        if command_binding is not None:
            if (schema_id, schema_version) != (
                command_binding.schema_id,
                command_binding.schema_version,
            ):
                raise SchemaError(
                    f"active command binding mismatch: {command_type} requires "
                    f"{command_binding.schema_id} version {command_binding.schema_version}"
                )
            command_schema = self.schemas.validate_active(
                command_binding.schema_id,
                validated_envelope,
                schema_version=command_binding.schema_version,
            )
        else:
            command_schema = self.schemas.validate(
                "ars://core/command",
                validated_envelope,
            )
        if validated_envelope.get("command_type") == "RevokeAuthorityGrant":
            self.schemas.validate(
                "ars://core/command/RevokeAuthorityGrant/payload",
                validated_envelope.get("payload"),
            )
        elif validated_envelope.get("command_type") == "PublishReleaseGateDecision":
            self.schemas.validate(
                "ars://evals/release-publication-request",
                validated_envelope.get("payload"),
            )
            ReleasePublicationRequest.from_dict(validated_envelope["payload"])
        command = Command(validated_envelope)
        self._before_submission_lock(command)
        activation_command = command.envelope["command_type"] in _SCOPED_ACTIVATION_COMMAND_TYPES
        preloaded_activation_marker: dict[str, Any] | None = None
        if activation_command:
            marker_path = self._scoped_activation_marker_path(command.command_id)
            if marker_path.exists():
                preloaded_activation_marker = self._load_scoped_activation_marker(marker_path)
                self._validate_scoped_activation_marker_command(
                    preloaded_activation_marker,
                    command,
                    command_schema,
                )
                self._validate_scoped_activation_marker_event_schema(preloaded_activation_marker)
        with self._submission_lock(command):
            lifecycle_authority: _LifecycleAuthorityEvidence | None = None

            def write_receipt(receipt: Receipt) -> Receipt:
                return self._write_receipt(
                    command,
                    receipt,
                    lifecycle_authority,
                    command_schema=command_schema,
                )

            self._recheck_moved_restore(command)
            self._before_authority_resolution(command)
            lifecycle = command.envelope["command_type"] in _LIFECYCLE_COMMAND_TYPES
            snapshot = self.ledger.snapshot()
            if lifecycle:
                lifecycle_authority, denial = self._resolve_lifecycle_authority(
                    command,
                    command_schema,
                    snapshot,
                )
                if denial is not None:
                    observed_version = snapshot.stream_versions.get(
                        command.target_stream_id,
                        0,
                    )
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "lifecycle_authority_unauthorized",
                        denial,
                    )
                    stored = self.receipts.load(command.command_id)
                    if (
                        stored is not None
                        and stored.status == "rejected"
                        and stored.payload_hash == command.payload_hash
                    ):
                        return stored
                    # A fresh denial must not return or overwrite an older
                    # accepted receipt for the same logical submission.
                    return rejected
            scoped = self._scoped_authority_receipt(
                command,
                command_schema=command_schema,
                lifecycle_authority=lifecycle_authority,
            )
            if scoped is not None:
                return scoped
            if not lifecycle:
                stored_conflict = self._stored_conflict_receipt(command)
                if stored_conflict is not None:
                    return stored_conflict
                stored_rejected = self._stored_rejected_receipt(command)
                if stored_rejected is not None:
                    return stored_rejected
            view = self._view_for(snapshot)
            activation_marker_preexisting = preloaded_activation_marker is not None
            activation_marker_status: str | None = None
            if preloaded_activation_marker is not None:
                current_marker = self._load_scoped_activation_marker(
                    self._scoped_activation_marker_path(command.command_id)
                )
                self._validate_scoped_activation_marker_command(
                    current_marker,
                    command,
                    command_schema,
                )
                activation_marker_status = self._scoped_activation_event_status(current_marker)
                if activation_marker_status == "competing":
                    self._remove_scoped_activation_marker(command.command_id)
                    preloaded_activation_marker = None
                    activation_marker_preexisting = False
            existing = self._matching_committed(
                command,
                view,
                command_schema=command_schema,
            )
            if existing is not None:
                receipt = write_receipt(self._return_or_reconstruct(existing))
                if activation_marker_status == "committed":
                    self._remove_scoped_activation_marker(command.command_id)
                return receipt
            if (
                command.envelope["command_type"] in _MESSAGE_COMMAND_TYPES
                and self.receipts.load(command.command_id) is not None
            ):
                raise ConflictError(f"receipt already exists: {command.command_id}")
            observed_version = view.stream_versions.get(command.target_stream_id, 0)
            prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None
            activation_object_existed: bool | None = None
            append_started = False
            if command.envelope["command_type"] == "PublishReleaseGateDecision":
                request = ReleasePublicationRequest.from_dict(command.envelope["payload"])
                if (
                    request.project_id != self.ledger.project_id
                    or request.release_decision_id != command.target_stream_id
                    or request.publication_authority_grant_id != command.envelope["authority_grant_id"]
                    or request.idempotency_key != command.idempotency_key
                    or set(command.envelope["evidence_refs"])
                    != {
                        request.evaluation_runs_manifest_ref,
                        request.control_binding_ref,
                    }
                ):
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_evidence_mismatch",
                        "Release publication envelope bindings do not match.",
                    )
                    return write_receipt(rejected)
                if self.authority_resolver is None:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_authorizer_unavailable",
                        "Release publication requires the canonical authority resolver.",
                    )
                    return write_receipt(rejected)
                try:
                    prepared_payload = self._prepare_release_publication(command)
                except IntegrityError:
                    raise
                except PublicationEvidenceError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_evidence_mismatch",
                        str(exc),
                    )
                    return write_receipt(rejected)
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_unauthorized",
                        str(exc),
                    )
                    return write_receipt(rejected)
                if observed_version > 0:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_decision_already_published",
                        "The canonical release decision stream is already published.",
                    )
                    return write_receipt(rejected)
            if observed_version != command.expected_stream_version:
                receipt = Receipt(
                    status="conflict",
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=None,
                    observed_stream_version=observed_version,
                    reason_code="stream_version_conflict",
                )
                return write_receipt(receipt)
            if command.envelope["command_type"] in _SCOPE_COMMAND_TYPES:
                prepared = self._prepare_scope_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _TASK_REVISION_COMMAND_TYPES:
                prepared = self._prepare_task_command(
                    command,
                    snapshot,
                    observed_version,
                    command_schema=command_schema,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _MESSAGE_COMMAND_TYPES:
                prepared = self._prepare_message_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] == "RevokeAuthorityGrant":
                try:
                    prepared_payload = self._prepare_authority_revocation(command, observed_version)
                except IntegrityError:
                    raise
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "authority_revocation_unauthorized",
                        str(exc),
                    )
                    return write_receipt(rejected)
            elif command.envelope["command_type"] in _SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES:
                try:
                    activation = command.envelope["command_type"] in {
                        "ActivateAuthorityGrant",
                        "ActivateExternalAssuranceRecordGrant",
                    }
                    if activation:
                        marker_path = self._scoped_activation_marker_path(command.command_id)
                        if activation_marker_preexisting:
                            existing_marker = self._load_scoped_activation_marker(marker_path)
                            self._validate_scoped_activation_marker_command(
                                existing_marker,
                                command,
                                command_schema,
                            )
                            activation_object_existed = existing_marker["object_existed_before"]
                        else:
                            activation_object_existed = self.objects.revision_exists(
                                "authority_grant",
                                command.target_stream_id,
                                1,
                            )
                        self._write_scoped_activation_marker(
                            command,
                            command_schema=command_schema,
                            existed_before=activation_object_existed,
                        )
                    if activation:
                        prepared_payload = self._prepare_scoped_authority_activation(
                            command,
                            observed_version,
                        )
                    else:
                        prepared_payload = self._prepare_issued_authority_revocation(
                            command,
                            observed_version,
                        )
                except IntegrityError:
                    self._cleanup_failed_scoped_activation(
                        command,
                        existed_before=activation_object_existed,
                        marker_preexisting=activation_marker_preexisting,
                    )
                    raise
                except ConflictError:
                    self._cleanup_failed_scoped_activation(
                        command,
                        existed_before=activation_object_existed,
                        marker_preexisting=activation_marker_preexisting,
                    )
                    raise
                except ArsError as exc:
                    self._cleanup_failed_scoped_activation(
                        command,
                        existed_before=activation_object_existed,
                        marker_preexisting=activation_marker_preexisting,
                    )
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "scoped_authority_administration_unauthorized",
                        str(exc),
                    )
                    return write_receipt(rejected)
            try:
                event = self._build_event(
                    command,
                    prepared_payload,
                    command_schema=command_schema,
                )
                append_started = True
                if isinstance(prepared_payload, VerifiedReleasePublication):
                    ledger_receipt = release_append(
                        self.ledger,
                        event,
                        lambda allocated: prepared_payload.payload_for(allocated.event_id),
                        snapshot=snapshot,
                    )
                elif (
                    command.envelope["command_type"] == "RevokeAuthorityGrant"
                    or command.envelope["command_type"] in _SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES
                ):
                    ledger_receipt = scoped_authority_append(
                        self.ledger,
                        event,
                        snapshot=snapshot,
                    )
                else:
                    ledger_receipt = self.ledger.append([event], snapshot=snapshot)
                updated = self.ledger.snapshot()
                view.extend(updated.events[len(snapshot.events) :], updated.fingerprint)
                accepted = Receipt(
                    status="accepted",
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=ledger_receipt["event_batch_id"],
                    observed_stream_version=ledger_receipt["resulting_stream_versions"][command.target_stream_id],
                )
                receipt = write_receipt(accepted)
                if activation_object_existed is not None:
                    self._remove_scoped_activation_marker(command.command_id)
                return receipt
            except Exception:
                if activation_object_existed is not None:
                    if self._scoped_activation_committed(command, command_schema=command_schema):
                        self._remove_scoped_activation_marker(command.command_id)
                    else:
                        self._rollback_scoped_authority_activation(
                            command,
                            existed_before=activation_object_existed,
                        )
                        if not append_started:
                            self._remove_scoped_activation_marker(command.command_id)
                raise

    def _scoped_activation_committed(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
    ) -> bool:
        path = self._scoped_activation_marker_path(command.command_id)
        if not path.exists():
            return False
        marker = self._load_scoped_activation_marker(path)
        self._validate_scoped_activation_marker_command(marker, command, command_schema)
        return self._scoped_activation_event_status(marker) == "committed"

    def _reconcile_scoped_activation_receipt(
        self,
        command: Command,
        command_schema: SchemaIdentity,
    ) -> None:
        if command.envelope["project_id"] != self.ledger.project_id:
            raise ConflictError("scoped activation recovery marker conflicts")
        marker_path = self._scoped_activation_marker_path(command.command_id)
        if not marker_path.exists():
            residue: list[tuple[Path, dict[str, Any]]] = []
            foreign_residue = False
            for temporary in self._scoped_activation_marker_temporary_paths(marker_path):
                if not temporary.exists():
                    continue
                try:
                    existing = self._load_scoped_activation_marker(temporary)
                except IntegrityError as exc:
                    raise IntegrityError("scoped activation recovery marker temporary data is invalid") from exc
                try:
                    self._validate_scoped_activation_marker_command(existing, command, command_schema)
                except ConflictError:
                    foreign_residue = True
                    continue
                status = self._scoped_activation_event_status(existing)
                if status != "committed":
                    raise IntegrityError("scoped accepted receipt does not match recovery marker")
                try:
                    actual = self.objects.read(
                        existing["object_kind"],
                        existing["target_grant_id"],
                        existing["object_revision"],
                    )
                except (IntegrityError, ValueError) as exc:
                    raise IntegrityError("committed scoped activation recovery object is invalid") from exc
                if actual != existing["object_value"]:
                    raise IntegrityError("committed scoped activation recovery object mismatch")
                residue.append((temporary, existing))
            if foreign_residue:
                raise ConflictError("scoped activation recovery marker temporary data conflicts")
            if self._cleanup_scoped_activation_marker_residue(residue) and marker_path.parent.exists():
                fsync_directory(marker_path.parent)
            return
        marker = self._load_scoped_activation_marker(marker_path)
        self._validate_scoped_activation_marker_command(marker, command, command_schema)
        status = self._scoped_activation_event_status(marker)
        if status != "committed":
            raise IntegrityError("scoped accepted receipt does not match recovery marker")
        self._reconcile_scoped_activation_marker(marker, status=status)

    def _rollback_scoped_authority_activation(
        self,
        command: Command,
        *,
        existed_before: bool,
    ) -> None:
        payload = command.envelope.get("payload")
        if not isinstance(payload, dict):
            return
        grant = payload.get("new_grant")
        if not isinstance(grant, dict):
            return
        self.objects.rollback_new_revision(
            "authority_grant",
            command.target_stream_id,
            1,
            grant,
            existed_before=existed_before,
        )

    def _cleanup_failed_scoped_activation(
        self,
        command: Command,
        *,
        existed_before: bool | None,
        marker_preexisting: bool,
    ) -> None:
        """Undo a newly prepared activation while retaining pre-existing evidence."""
        if existed_before is None:
            return
        self._rollback_scoped_authority_activation(command, existed_before=existed_before)
        if not marker_preexisting:
            self._remove_scoped_activation_marker(command.command_id)

    def _before_submission_lock(self, command: Command) -> None:
        """Provide a post-validation setup seam before writer-lock acquisition."""

    def _before_authority_resolution(self, command: Command) -> None:
        """Provide a locked setup seam immediately before authority evaluation."""

    @contextmanager
    def _submission_lock(self, command: Command):
        """Serialize authority-governed submits across all participating roots."""
        identity = {"command_id": command.command_id}
        command_type = command.envelope["command_type"]
        roots: tuple[Path, ...] = (self.control_root,)
        if command_type in _T2_AUTHORITY_COORDINATED_COMMAND_TYPES:
            t2_root = self._t2_authority_root_for_lock()
            if t2_root is not None:
                roots = (self.control_root, t2_root)
        elif command_type in _AUTHORITY_COORDINATED_COMMAND_TYPES:
            resolver = self._canonical_authority_resolver()
            if resolver is not None:
                roots = (self.control_root, resolver.control_root)
        retry_on_conflict = command_type in {
            "PublishReleaseGateDecision",
            *_LIFECYCLE_COMMAND_TYPES,
            *_T2_AUTHORITY_COORDINATED_COMMAND_TYPES,
        }
        deadline = self._monotonic() + self.release_lock_timeout_seconds
        while True:
            lock = CompositeWriterLock(
                roots,
                identity,
                lock_factory=WriterLock,
            )
            try:
                lock.__enter__()
            except ConflictError:
                if not retry_on_conflict or self._monotonic() >= deadline:
                    raise
                self._lock_wait(0.01)
                continue
            break
        try:
            yield lock
        finally:
            lock.__exit__(*sys.exc_info())

    def with_locked_authority(
        self,
        *,
        authority_grant_id: str,
        actor_id: str,
        command_type: str,
        project_id: str,
        subject_kind: str,
        subject_id: str,
        callback: Callable[[Any], Any],
    ) -> Any:
        """Recheck current canonical authority and run a callback under W2 lock.

        Args:
            authority_grant_id: Grant to revalidate against canonical history.
            actor_id: Attributed actor performing the governed operation.
            command_type: Exact governed command type.
            project_id: Project identity of the governed target.
            subject_kind: Registered governed subject kind.
            subject_id: Exact governed subject identity.
            callback: Operation invoked with replay-derived authority evidence.

        Returns:
            The callback result.

        Raises:
            ArsError: If no resolver exists or current authority is invalid.
            ConflictError: If the W2 writer lock cannot be acquired.
            IntegrityError: If canonical authority evidence is invalid.
        """
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("governed operation requires authority resolver")
        with CompositeWriterLock(
            (self.control_root, resolver.control_root),
            {"command_id": new_id("command")},
            lock_factory=WriterLock,
        ):
            snapshot = self.ledger.snapshot()
            replay(
                snapshot.events,
                schema_registry=self.schemas,
                authority_state_validator=self._authority_state_validator(),
            )
            resolved = resolver.resolve(
                authority_grant_id,
                actor_id,
                command_type,
                project_id,
                subject_kind,
                subject_id,
                self.clock(),
            )
            return callback(resolved)

    @staticmethod
    def _authority_scope(command: Command) -> tuple[str, str, str, str]:
        return (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )

    def _scoped_authority_receipt(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
        lifecycle_authority: _LifecycleAuthorityEvidence | None = None,
    ) -> Receipt | None:
        command_type = command.envelope["command_type"]
        if command_type in _LIFECYCLE_COMMAND_TYPES:
            if lifecycle_authority is None:
                raise IntegrityError("lifecycle command missing fresh authority resolution")
            return self._load_lifecycle_authority_receipt(
                command,
                command_schema,
                lifecycle_authority,
            )
        if command_type not in {
            "RevokeAuthorityGrant",
            "PublishReleaseGateDecision",
            *_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES,
        }:
            return None
        if command_type == "PublishReleaseGateDecision":
            hash_field = "publication_authority_sha256"
        elif command_type == "RevokeAuthorityGrant":
            hash_field = "authority_grant_sha256"
        else:
            hash_field = "root_grant_sha256"
        grant_hash = command.envelope.get("payload", {}).get(hash_field)
        if not isinstance(grant_hash, str):
            return None
        publication = command_type == "PublishReleaseGateDecision"
        try:
            receipt = self.receipts.load_scoped(
                self._authority_scope(command),
                command.payload_hash,
                grant_hash,
                command.expected_stream_version,
                project_id=self.ledger.project_id if publication else None,
                target_stream_id=(command.target_stream_id if publication else None),
            )
        except IdempotencyConflictError:
            if not publication:
                raise
            conflict = Receipt(
                status="conflict",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=None,
                observed_stream_version=self.ledger.snapshot().stream_versions.get(
                    command.target_stream_id,
                    0,
                ),
                reason_code="idempotency_conflict",
            )
            return self.receipts.write(conflict)
        if receipt is None:
            return receipt
        if command.envelope["command_type"] in _SCOPED_ACTIVATION_COMMAND_TYPES and receipt.status == "accepted":
            self._reconcile_scoped_activation_receipt(command, command_schema)
        self._reconcile_scoped_authority_receipt(command, receipt)
        return self._return_scoped_receipt_or_raise(command, receipt)

    def _reconcile_scoped_authority_receipt(
        self,
        command: Command,
        receipt: Receipt,
        *,
        lifecycle_resolution: dict[str, Any] | None = None,
        canonical_resolution: dict[str, Any] | None = None,
        command_schema: SchemaIdentity | None = None,
    ) -> None:
        scope = self._authority_scope(command)
        snapshot = self.ledger.snapshot()
        replay(
            snapshot.events,
            schema_registry=self.schemas,
            authority_state_validator=self._authority_state_validator(),
        )
        events = tuple(snapshot.events)
        scoped_events = tuple(
            event
            for event in events
            if (
                event.get("actor_id"),
                event.get("authority_grant_id"),
                event.get("command_type"),
                event.get("idempotency_key"),
            )
            == scope
        )
        if receipt.status == "accepted":
            matching = tuple(event for event in scoped_events if event.get("transaction_id") == receipt.event_batch_id)
            command_type = command.envelope["command_type"]
            try:
                expected_event_type = _COMMAND_EVENT_TYPES[command_type]
            except KeyError as exc:
                raise IntegrityError(f"no canonical event type for {command_type}") from exc
            if (
                len(matching) != 1
                or matching[0].get("event_type") != expected_event_type
                or matching[0].get("command_id") != receipt.command_id
                or matching[0].get("command_payload_hash") != receipt.payload_hash
                or matching[0].get("stream_id") != command.target_stream_id
                or matching[0].get("stream_version") != command.expected_stream_version + 1
                or receipt.observed_stream_version != matching[0].get("stream_version")
                or matching[0].get("project_id") != self.ledger.project_id
            ):
                raise IntegrityError("scoped accepted receipt does not match canonical ledger")
            if lifecycle_resolution is not None:
                if command_schema is None:
                    raise IntegrityError("lifecycle command schema evidence is missing")
                self._validate_lifecycle_authority_history(
                    command,
                    command_schema=command_schema,
                    receipt=receipt,
                    resolution=lifecycle_resolution,
                    event=matching[0],
                    canonical_resolution=canonical_resolution,
                )
        elif scoped_events:
            raise IntegrityError("scoped terminal receipt conflicts with canonical ledger")
        stored = self.receipts.load(receipt.command_id)
        if stored is not None and stored != receipt:
            raise IntegrityError("receipt does not match scoped index")
        self._validate_message_scoped_retry_identity(command, receipt)
        if stored is None:
            self.receipts.write(receipt)

    def _validate_lifecycle_authority_history(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
        receipt: Receipt,
        resolution: dict[str, Any],
        event: dict[str, Any],
        canonical_resolution: dict[str, Any] | None,
    ) -> None:
        if receipt.status != "accepted":
            return
        if not isinstance(resolution, dict):
            raise IntegrityError("lifecycle authority resolution evidence is invalid")
        grant_id = resolution.get("authority_grant_id")
        canonical_history = canonical_resolution
        if (
            not isinstance(grant_id, str)
            or not grant_id
            or not isinstance(canonical_history, dict)
            or canonical_history.get("authority_grant_id") != grant_id
        ):
            raise IntegrityError("lifecycle authority evidence has no canonical grant history")
        if self._authority_key(canonical_history) != resolution.get("authority_grant_sha256"):
            raise IntegrityError("lifecycle authority resolution grant hash disagrees with canonical history")
        if (
            event.get("authority_grant_id") != grant_id
            or event.get("actor_id") != resolution.get("actor_id")
            or event.get("stream_id") != command.target_stream_id
            or event.get("command_type") != command.envelope["command_type"]
            or event.get("command_schema_id") != command_schema.schema_id
            or event.get("command_schema_version") != command_schema.schema_version
            or event.get("command_schema_sha256") != command_schema.sha256
            or event.get("command_payload_hash") != command.payload_hash
        ):
            raise IntegrityError("lifecycle authority resolution is not bound to history")

    def _write_receipt(
        self,
        command: Command,
        receipt: Receipt,
        lifecycle_authority: _LifecycleAuthorityEvidence | None = None,
        *,
        command_schema: SchemaIdentity | None = None,
    ) -> Receipt:
        command_type = command.envelope["command_type"]
        if command_type in _MESSAGE_COMMAND_TYPES and receipt.status != "accepted":
            return receipt
        if command_type in _LIFECYCLE_COMMAND_TYPES:
            if lifecycle_authority is None:
                raise IntegrityError("lifecycle command missing resolved authority evidence")
            if lifecycle_authority.resolution is None:
                raise IntegrityError("lifecycle command missing resolution evidence")
            if command_schema is None:
                raise IntegrityError("lifecycle command schema evidence is missing")
            if receipt.status == "accepted":
                snapshot = self.ledger.snapshot()
                replay(
                    snapshot.events,
                    schema_registry=self.schemas,
                    authority_state_validator=self._authority_state_validator(),
                )
                event = next(
                    (
                        event
                        for event in snapshot.events
                        if event.get("transaction_id") == receipt.event_batch_id
                        and event.get("stream_id") == command.target_stream_id
                    ),
                    None,
                )
                if event is None:
                    raise IntegrityError("accepted lifecycle receipt has no canonical event")
                self._validate_lifecycle_authority_history(
                    command,
                    command_schema=command_schema,
                    receipt=receipt,
                    resolution=lifecycle_authority.resolution,
                    event=event,
                    canonical_resolution=lifecycle_authority.canonical_resolution,
                )
            result = self.receipts.write_scoped(
                self._authority_scope(command),
                lifecycle_authority.authority_key,
                command.expected_stream_version,
                receipt,
                project_id=command.envelope.get("project_id"),
                target_stream_id=command.target_stream_id,
            )
            return result
        if command_type not in {
            "RevokeAuthorityGrant",
            "PublishReleaseGateDecision",
            *_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES,
        }:
            return self.receipts.write(receipt)
        publication = command_type == "PublishReleaseGateDecision"
        if publication:
            hash_field = "publication_authority_sha256"
        elif command_type == "RevokeAuthorityGrant":
            hash_field = "authority_grant_sha256"
        else:
            hash_field = "root_grant_sha256"
        grant_hash = command.envelope["payload"].get(hash_field)
        if not isinstance(grant_hash, str):
            return self.receipts.write(receipt)
        return self.receipts.write_scoped(
            self._authority_scope(command),
            grant_hash,
            command.expected_stream_version,
            receipt,
            project_id=self.ledger.project_id if publication else None,
            target_stream_id=(command.target_stream_id if publication else None),
        )

    @staticmethod
    def _risk_tier(value: object) -> str:
        return value if isinstance(value, str) and value in {"R0", "R1", "R2", "R3"} else "R3"

    @classmethod
    def _max_risk(cls, *values: object) -> str:
        order = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
        return max(
            (cls._risk_tier(value) for value in values),
            key=order.__getitem__,
        )

    def _task_current_risk(self, snapshot: LedgerSnapshot, task_id: str) -> str:
        current, _, _ = self._revision_graph(snapshot)
        revision = current.get(task_id)
        if revision is None:
            return "R3"
        definition = self._task_revision_object(task_id, revision)
        if definition is None:
            return "R3"
        return self._risk_tier(definition.get("risk_tier_request"))

    def _lifecycle_authority_inputs(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
    ) -> tuple[str, str, str, str]:
        command_type = command.envelope["command_type"]
        payload = command.envelope["payload"]
        project_id = str(command.envelope.get("project_id", ""))
        if command_type in _SCOPE_COMMAND_TYPES:
            subject_id = str(
                payload.get(
                    "new_scope_definition_id" if command_type == "CreateScopeDefinition" else "scope_definition_id",
                    "",
                )
            )
            return project_id, "scope_definition", subject_id, "R3"

        if command_type in _MESSAGE_COMMAND_TYPES:
            subject_id = str(
                payload.get(
                    "new_message_id" if command_type == "PublishMessage" else "message_id",
                    "",
                )
            )
            return project_id, "message", subject_id, "R3"

        subject_id = str(
            payload.get(
                "new_task_id" if command_type == "CreateTask" else "task_id",
                "",
            )
        )
        if command_type == "CreateTask":
            definition = payload.get("definition")
            proposed_risk = definition.get("risk_tier_request") if isinstance(definition, dict) else None
            return project_id, "task", subject_id, self._risk_tier(proposed_risk)

        current_risk = self._task_current_risk(snapshot, subject_id)
        if command_type == "AmendTask":
            replacement = payload.get("replacement_definition")
            replacement_risk = replacement.get("risk_tier_request") if isinstance(replacement, dict) else None
        else:
            replacement_id = payload.get("replacement_task_id")
            replacement_revision = payload.get("replacement_task_revision")
            replacement = None
            if (
                isinstance(replacement_id, str)
                and isinstance(replacement_revision, int)
                and not isinstance(replacement_revision, bool)
                and replacement_revision >= 1
            ):
                replacement = self._task_revision_object(replacement_id, replacement_revision)
            replacement_risk = replacement.get("risk_tier_request") if isinstance(replacement, dict) else None
        return project_id, "task", subject_id, self._max_risk(current_risk, replacement_risk)

    @staticmethod
    def _message_content_sha256(state: dict[str, Any]) -> str:
        payload = state.get("published_payload")
        if not isinstance(payload, dict):
            raise IntegrityError("Message history has no immutable publication payload")
        return sha256_hex(canonical_bytes(payload))

    def _message_state(
        self,
        snapshot: LedgerSnapshot,
        message_id: str,
    ) -> dict[str, Any] | None:
        projection = replay(
            snapshot.events,
            schema_registry=self.schemas,
            authority_state_validator=self._authority_state_validator(),
        )
        value = projection.get("streams", {}).get(message_id)
        return dict(value) if isinstance(value, dict) else None

    def _message_adapter_denial(self, command: Command) -> str | None:
        if command.envelope["command_type"] not in _MESSAGE_ADAPTER_COMMAND_TYPES:
            return None
        adapter_id = command.envelope["payload"].get("delivery_adapter_id")
        matches = [entry for entry in self._message_adapter_registry if entry.delivery_adapter_id == adapter_id]
        if len(matches) != 1:
            return "Message adapter registration is missing or ambiguous."
        entry = matches[0]
        now = self.clock()
        if entry.project_id != self.ledger.project_id:
            return "Message adapter registration project does not match the control store."
        if entry.status != "eligible":
            return "Message adapter registration is not eligible."
        if now < entry.effective_at or (entry.expires_at is not None and now >= entry.expires_at):
            return "Message adapter registration is not currently effective."
        if command.envelope["command_type"] not in entry.applicable_command_types:
            return "Message adapter registration lacks the required capability."
        if command.actor_id not in entry.allowed_actor_ids:
            return "Message adapter registration does not bind the command actor."
        return None

    def _prepare_message_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "Message command project must match the control-store project.",
            )
        message_id = payload.get("new_message_id") if command_type == "PublishMessage" else payload.get("message_id")
        if message_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_message_subject_identity",
                "Message payload identity must equal the target stream.",
            )
        state = self._message_state(snapshot, command.target_stream_id)
        if command_type == "PublishMessage":
            if state is not None or observed_version != 0:
                return self._rejected(
                    command,
                    observed_version,
                    "message_already_published",
                    "Message publication requires an absent stream.",
                )
            if payload.get("sender_actor_id") != command.actor_id:
                return self._rejected(
                    command,
                    observed_version,
                    "message_sender_mismatch",
                    "Message sender must equal the authority-attributed actor.",
                )
            if payload.get("reply_to_message_id") == message_id:
                return self._rejected(
                    command,
                    observed_version,
                    "message_self_reference",
                    "Message reply linkage cannot reference the new Message itself.",
                )
            if payload.get("message_type") == "acknowledgement" and (
                payload.get("correlation_message_id") != payload.get("reply_to_message_id")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "message_correlation_mismatch",
                    "Acknowledgement publication correlation must equal its reply link.",
                )
            return payload
        if state is None:
            return self._rejected(
                command,
                observed_version,
                "message_not_published",
                "Message transition requires a committed MessagePublished event.",
            )
        if command_type in _MESSAGE_ADAPTER_COMMAND_TYPES:
            denial = self._message_adapter_denial(command)
            if denial is not None:
                return self._rejected(
                    command,
                    observed_version,
                    "message_adapter_unauthorized",
                    denial,
                )
        content_sha256 = self._message_content_sha256(state)
        recipients = state.get("published_payload", {}).get("recipient_actor_ids")
        if command_type == "RecordMessageDelivery":
            if state.get("status") != "published":
                return self._rejected(
                    command, observed_version, "invalid_message_transition", "Message is not publishable for delivery."
                )
            if not payload.get("delivery_evidence_refs"):
                return self._rejected(
                    command,
                    observed_version,
                    "message_evidence_required",
                    "Message delivery requires immutable delivery evidence.",
                )
            if payload.get("content_sha256") != content_sha256 or payload.get("recipient_actor_ids") != recipients:
                return self._rejected(
                    command,
                    observed_version,
                    "message_content_mismatch",
                    "Delivery must bind the published Message payload and recipients.",
                )
        elif command_type == "AcknowledgeMessage":
            if state.get("status") != "delivered":
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_message_transition",
                    "Message acknowledgement requires delivery.",
                )
            if command.actor_id not in recipients:
                return self._rejected(
                    command,
                    observed_version,
                    "message_recipient_mismatch",
                    "Only a published recipient may acknowledge a Message.",
                )
            if (
                payload.get("content_sha256") != content_sha256
                or payload.get("recipient_actor_ids") != recipients
                or payload.get("source_position") != state.get("published_position")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "message_content_mismatch",
                    "Acknowledgement must bind the publication payload, recipients, and source position.",
                )
        elif command_type == "RecordMessageDeliveryFailure":
            if state.get("status") != "published":
                return self._rejected(
                    command, observed_version, "invalid_message_transition", "Message failure requires published state."
                )
            if not payload.get("failure_evidence_refs"):
                return self._rejected(
                    command,
                    observed_version,
                    "message_evidence_required",
                    "Message delivery failure requires immutable failure evidence.",
                )
        else:
            raise IntegrityError("unknown Message command")
        return payload

    def _canonical_authority_resolver(self) -> LedgerAuthorityGrantResolver | None:
        resolver = self.authority_resolver
        return resolver if type(resolver) is LedgerAuthorityGrantResolver else None

    @staticmethod
    def _freeze_t2_authority_root(resolver: Any) -> tuple[Path, tuple[int, int]]:
        if not callable(resolver):
            raise ArsError("T2 authority resolver must be callable")
        candidate = getattr(resolver, "control_root", None)
        if candidate is None:
            raise ArsError("T2 authority resolver requires an existing control_root")
        try:
            root = Path(candidate).resolve(strict=True)
            observed = root.stat()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ArsError("T2 authority resolver control_root is not verifiable") from exc
        if not root.is_dir():
            raise ArsError("T2 authority resolver control_root must be an existing directory")
        return root, (observed.st_dev, observed.st_ino)

    def _t2_authority_root_for_lock(self) -> Path | None:
        resolver = self.t2_authority_resolver
        if resolver is None:
            return None
        root, identity = self._freeze_t2_authority_root(resolver)
        if (root, identity) != (self._t2_authority_root, self._t2_authority_identity):
            raise ArsError("T2 authority resolver control_root changed after construction")
        return self._t2_authority_root

    @staticmethod
    def _authority_time(value: object) -> object:
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return value

    @classmethod
    def _authority_resolution_record(cls, resolution: Any | None) -> dict[str, Any] | None:
        if resolution is None:
            return None
        if type(resolution) is not ScopedAuthorityGrantResolution:
            raise IntegrityError("lifecycle authority resolver returned non-canonical evidence")
        subject_scope = getattr(resolution, "subject_scope", None)
        if hasattr(subject_scope, "to_dict"):
            subject_scope = subject_scope.to_dict()
        return {
            "authority_grant_id": getattr(resolution, "authority_grant_id", None),
            "authority_grant_sha256": getattr(resolution, "authority_grant_sha256", None),
            "schema_id": getattr(resolution, "schema_id", None),
            "schema_version": getattr(resolution, "schema_version", None),
            "schema_sha256": getattr(resolution, "schema_sha256", None),
            "actor_id": getattr(resolution, "actor_id", None),
            "subject_scope": subject_scope,
            "effective_at": cls._authority_time(getattr(resolution, "effective_at", None)),
            "expires_at": cls._authority_time(getattr(resolution, "expires_at", None)),
            "activation_event_id": getattr(resolution, "activation_event_id", None),
            "activation_position": getattr(resolution, "activation_position", None),
            "administration_decision_id": getattr(resolution, "administration_decision_id", None),
            "administration_decision_sha256": getattr(resolution, "administration_decision_sha256", None),
            "status": getattr(resolution, "status", None),
            "revocation_event_id": getattr(resolution, "revocation_event_id", None),
        }

    def _lifecycle_authority_binding(
        self,
        command: Command,
        command_schema: SchemaIdentity,
        snapshot: LedgerSnapshot,
        *,
        actor_class: str,
    ) -> tuple[dict[str, Any], str]:
        project_id, subject_kind, subject_id, required_risk = self._lifecycle_authority_inputs(
            command,
            snapshot,
        )
        binding = {
            "actor_id": command.actor_id,
            "actor_class": actor_class,
            "authority_grant_id": command.envelope["authority_grant_id"],
            "command_type": command.envelope["command_type"],
            "idempotency_key": command.idempotency_key,
            "command_schema_id": command_schema.schema_id,
            "command_schema_version": command_schema.schema_version,
            "command_schema_sha256": command_schema.sha256,
            "project_id": project_id,
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "required_risk": required_risk,
            "target_stream_id": command.target_stream_id,
            "expected_stream_version": command.expected_stream_version,
            "payload_hash": command.payload_hash,
        }
        return binding, actor_class

    @staticmethod
    def _authority_key(
        resolution: dict[str, Any] | None,
    ) -> str:
        grant_hash = resolution.get("authority_grant_sha256") if resolution is not None else None
        if (
            isinstance(grant_hash, str)
            and len(grant_hash) == 64
            and all(character in "0123456789abcdef" for character in grant_hash)
        ):
            return grant_hash
        raise IntegrityError("lifecycle authority resolution has no canonical grant hash")

    def _resolve_lifecycle_authority(
        self,
        command: Command,
        command_schema: SchemaIdentity,
        snapshot: LedgerSnapshot,
    ) -> tuple[_LifecycleAuthorityEvidence, str | None]:
        resolver = self._canonical_authority_resolver()
        binding, _ = self._lifecycle_authority_binding(
            command,
            command_schema,
            snapshot,
            actor_class="unproven",
        )
        resolution: dict[str, Any] | None = None
        canonical_resolution: dict[str, Any] | None = None
        denial: str | None = None
        if resolver is None:
            denial = "Lifecycle commands require the canonical scoped authority resolver."
        else:
            command_identity = GrantedCommandIdentity(
                command_type=command.envelope["command_type"],
                schema_id=command_schema.schema_id,
                schema_version=str(command_schema.schema_version),
                schema_sha256=command_schema.sha256,
            )
            project_id = binding["project_id"]
            subject_kind = binding["subject_kind"]
            subject_id = binding["subject_id"]
            required_risk = binding["required_risk"]
            try:
                evidence = resolver.resolve_lifecycle_command(
                    grant_id=command.envelope["authority_grant_id"],
                    actor_id=command.actor_id,
                    command=command_identity,
                    required_risk=required_risk,
                    project_id=project_id,
                    subject_kind=subject_kind,
                    subject_id=subject_id,
                    now=self.clock(),
                )
                if type(evidence) is not LifecycleCommandAuthorityEvidence:
                    raise ArsError("authority resolver returned non-canonical lifecycle evidence")
                context = evidence.administration_context
                if (
                    type(context) is not AuthorityAdministrationContext
                    or context.project_id != project_id
                    or type(evidence.command_resolution) is not ScopedAuthorityGrantResolution
                    or type(evidence.canonical_grant_identity) is not ScopedAuthorityGrantResolution
                ):
                    raise IntegrityError("lifecycle authority bundle evidence is invalid")
                expected_actor_class = "human" if command.actor_id == context.owner_actor_id else "unproven"
                if evidence.actor_class != expected_actor_class:
                    raise IntegrityError("lifecycle authority actor class disagrees with owner context")
                if evidence.actor_class != "human":
                    raise ArsError("authority actor class is not proven by the bootstrap owner")
                resolution = self._authority_resolution_record(evidence.command_resolution)
                canonical_resolution = self._authority_resolution_record(evidence.canonical_grant_identity)
                if canonical_resolution != resolution:
                    raise IntegrityError("lifecycle authority bundle resolutions disagree")
                binding = {**binding, "actor_class": evidence.actor_class}
            except IntegrityError:
                raise
            except ArsError as exc:
                resolution = None
                canonical_resolution = None
                denial = str(exc)
        return (
            _LifecycleAuthorityEvidence(
                binding=binding,
                resolution=resolution,
                canonical_resolution=canonical_resolution,
                authority_key=(self._authority_key(canonical_resolution) if canonical_resolution is not None else ""),
                denial=denial,
            ),
            denial,
        )

    def _load_lifecycle_authority_receipt(
        self,
        command: Command,
        command_schema: SchemaIdentity,
        lifecycle_authority: _LifecycleAuthorityEvidence,
    ) -> Receipt | None:
        if lifecycle_authority.resolution is None:
            raise IntegrityError("lifecycle command missing fresh resolution evidence")
        receipt = self.receipts.load_scoped(
            self._authority_scope(command),
            command.payload_hash,
            lifecycle_authority.authority_key,
            command.expected_stream_version,
            project_id=command.envelope.get("project_id"),
            target_stream_id=command.target_stream_id,
        )
        if receipt is None:
            return None
        self._reconcile_scoped_authority_receipt(
            command,
            receipt,
            lifecycle_resolution=lifecycle_authority.resolution,
            canonical_resolution=lifecycle_authority.canonical_resolution,
            command_schema=command_schema,
        )
        return self._return_scoped_receipt_or_raise(command, receipt)

    def _validate_message_scoped_retry_identity(
        self,
        command: Command,
        receipt: Receipt,
    ) -> None:
        if command.envelope["command_type"] not in _MESSAGE_COMMAND_TYPES:
            return
        if command.command_id == receipt.command_id:
            return
        if self.receipts.load(command.command_id) is not None:
            raise ConflictError("command ID conflicts with stored receipt")
        if any(event.get("command_id") == command.command_id for event in self.ledger.snapshot().events):
            raise ConflictError("command ID conflicts with committed command")
        raise ConflictError("idempotency key conflicts with committed command")

    def _return_scoped_receipt_or_raise(
        self,
        command: Command,
        receipt: Receipt,
    ) -> Receipt:
        if command.command_id == receipt.command_id:
            return receipt
        if self.receipts.load(command.command_id) is not None:
            raise ConflictError("command ID conflicts with stored receipt")
        if any(event.get("command_id") == command.command_id for event in self.ledger.snapshot().events):
            raise ConflictError("command ID conflicts with committed command")
        return receipt

    def _stored_rejected_receipt(self, command: Command) -> Receipt | None:
        """Return an idempotent rejected receipt while holding WriterLock."""
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != "rejected":
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError("command ID conflicts with stored receipt")
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or not stored.reason_code
            or not stored.explanation
            or not stored.unmet_preconditions
        ):
            raise IntegrityError("stored rejected receipt is inconsistent")
        return stored

    def _rejected(
        self,
        command: Command,
        observed_version: int,
        reason_code: str,
        explanation: str,
    ) -> Receipt:
        return Receipt(
            status="rejected",
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=None,
            observed_stream_version=observed_version,
            reason_code=reason_code,
            explanation=explanation,
            unmet_preconditions=(reason_code,),
        )

    def _task_revision_object(
        self,
        task_id: str,
        revision: int,
    ) -> dict[str, Any] | None:
        directory = self.control_root / "objects" / "task" / task_id
        matches = sorted(directory.glob(f"{revision:08d}-*.json"))
        if not matches:
            return None
        value = self.objects.read("task", task_id, revision)
        if not isinstance(value, dict):
            raise IntegrityError("Task revision object must be a mapping")
        return value

    @staticmethod
    def _revision_graph(
        snapshot: LedgerSnapshot,
    ) -> tuple[
        dict[str, int],
        dict[tuple[str, int], tuple[str, int]],
        dict[tuple[str, int], _TaskRevisionEvidence],
    ]:
        current: dict[str, int] = {}
        edges: dict[tuple[str, int], tuple[str, int]] = {}
        evidence: dict[tuple[str, int], _TaskRevisionEvidence] = {}
        for event in snapshot.events:
            if event["event_type"] == "TaskCreated":
                payload = event.get("payload", {})
                if not isinstance(payload, dict):
                    raise IntegrityError("TaskCreated payload must be a mapping")
                if event.get("schema_id") == "ars://core/event/TaskCreated":
                    definition = payload.get("definition", {})
                    revision = int(definition["revision"])
                else:
                    definition = payload
                    revision = int(payload.get("revision", 1))
                current.setdefault(event["stream_id"], revision)
                evidence[(event["stream_id"], revision)] = _TaskRevisionEvidence(
                    str(event.get("schema_id", "")),
                    definition,
                )
            elif event["event_type"] == "TaskAmended":
                payload = event["payload"]
                task_id = str(payload["task_id"])
                prior_revision = int(payload["prior_revision"])
                new_revision = int(payload["new_revision"])
                if current.get(task_id) != prior_revision:
                    raise IntegrityError("Task amendment history is not current")
                source = (task_id, prior_revision)
                if source in edges:
                    raise IntegrityError("Task revision has multiple successor edges")
                edges[source] = (task_id, new_revision)
                current[task_id] = new_revision
                evidence[(task_id, new_revision)] = _TaskRevisionEvidence(
                    str(event.get("schema_id", "")),
                    payload.get("replacement_definition"),
                )
            elif event["event_type"] == "TaskSuperseded":
                payload = event["payload"]
                if event.get("schema_id") == "ars://core/event/TaskSuperseded":
                    source_id = str(payload["task_id"])
                    source_revision = current.get(source_id)
                    if source_revision is None:
                        raise IntegrityError("Task supersession source history is absent")
                    source = (source_id, source_revision)
                else:
                    source = (
                        str(payload["source_task_id"]),
                        int(payload["source_task_revision"]),
                    )
                replacement = (
                    str(payload["replacement_task_id"]),
                    int(payload["replacement_task_revision"]),
                )
                if source in edges:
                    raise IntegrityError("Task revision has multiple supersession edges")
                edges[source] = replacement
                if source[0] == replacement[0]:
                    current[source[0]] = replacement[1]
                    source_evidence = evidence.get(source)
                    if source_evidence is not None:
                        evidence[replacement] = _TaskRevisionEvidence(
                            source_evidence.schema_id,
                            None,
                        )
        return current, edges, evidence

    @staticmethod
    def _reaches(
        edges: dict[tuple[str, int], tuple[str, int]],
        start: tuple[str, int],
        target: tuple[str, int],
    ) -> bool:
        seen: set[tuple[str, int]] = set()
        pending = [start]
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            replacement = edges.get(node)
            if replacement is not None:
                pending.append(replacement)
        return False

    @staticmethod
    def _derived_lineage(
        edges: dict[tuple[str, int], tuple[str, int]],
        source: tuple[str, int],
        replacement: tuple[str, int],
    ) -> list[dict[str, Any]]:
        reverse = {target: origin for origin, target in edges.items()}
        lineage = [source]
        seen = {source}
        while lineage[0] in reverse:
            predecessor = reverse[lineage[0]]
            if predecessor in seen:
                raise IntegrityError("supersession lineage cycle")
            seen.add(predecessor)
            lineage.insert(0, predecessor)
        lineage.append(replacement)
        return [{"task_id": task_id, "revision": revision} for task_id, revision in lineage]

    @staticmethod
    def _content_hash_matches(value: dict[str, Any]) -> bool:
        return content_hash_matches(value)

    @classmethod
    def _is_rich_task_definition(cls, value: dict[str, Any]) -> bool:
        return (
            isinstance(value.get("task_id"), str)
            and isinstance(value.get("revision"), int)
            and not isinstance(value.get("revision"), bool)
            and isinstance(value.get("project_id"), str)
            and cls._content_hash_matches(value)
        )

    def _task_revision_kind(
        self,
        value: dict[str, Any],
        evidence: _TaskRevisionEvidence | None,
        *,
        task_id: str,
        revision: int,
    ) -> str | None:
        if evidence is None:
            return None
        if evidence.definition is not None and value != evidence.definition:
            raise IntegrityError("Task revision object differs from committed event content")
        if evidence.exact:
            if (
                evidence.definition is None
                or not self._is_rich_task_definition(value)
                or value.get("task_id") != task_id
                or value.get("revision") != revision
                or value.get("project_id") != self.ledger.project_id
            ):
                return None
            return "rich"
        consumers = value.get("continuing_consumers")
        if (
            not isinstance(value.get("task_type"), str)
            or not value["task_type"]
            or not isinstance(consumers, list)
            or not consumers
            or not all(isinstance(item, str) and item for item in consumers)
        ):
            return None
        return "generic"

    def _scope_revision_object(
        self,
        scope_id: str,
        revision: int,
        committed_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        directory = self.control_root / "objects" / "scope_definition" / scope_id
        if not list(directory.glob(f"{revision:08d}-*.json")):
            return None
        value = self.objects.read("scope_definition", scope_id, revision)
        if not isinstance(value, dict):
            raise IntegrityError("ScopeDefinition revision object must be a mapping")
        if committed_payload is not None and value != committed_payload:
            raise IntegrityError("ScopeDefinition revision object differs from committed event content")
        return value

    @staticmethod
    def _scope_revision_graph(
        snapshot: LedgerSnapshot,
    ) -> tuple[
        dict[str, int],
        dict[tuple[str, int], tuple[str, int]],
        dict[tuple[str, int], dict[str, Any]],
    ]:
        current: dict[str, int] = {}
        edges: dict[tuple[str, int], tuple[str, int]] = {}
        evidence: dict[tuple[str, int], dict[str, Any]] = {}
        for event in snapshot.events:
            event_type = event["event_type"]
            if event_type == "ScopeDefinitionCreated":
                payload = event["payload"]
                scope_id = str(payload["new_scope_definition_id"])
                revision = int(payload["revision"])
                current.setdefault(scope_id, revision)
                if event.get("schema_id") == "ars://core/event/ScopeDefinitionCreated":
                    evidence[(scope_id, revision)] = payload
            elif event_type == "ScopeDefinitionAmended":
                payload = event["payload"]
                scope_id = str(payload["scope_definition_id"])
                prior = int(payload["prior_revision"])
                new = int(payload["new_revision"])
                if current.get(scope_id) != prior:
                    raise IntegrityError("ScopeDefinition amendment history is not current")
                source = (scope_id, prior)
                if source in edges:
                    raise IntegrityError("ScopeDefinition revision has multiple successor edges")
                edges[source] = (scope_id, new)
                current[scope_id] = new
                if event.get("schema_id") == "ars://core/event/ScopeDefinitionAmended":
                    evidence[(scope_id, new)] = payload
            elif event_type == "ScopeDefinitionSuperseded":
                payload = event["payload"]
                source_id = str(payload["scope_definition_id"])
                source_revision = current.get(source_id)
                if source_revision is None:
                    raise IntegrityError("ScopeDefinition supersession source history is absent")
                source = (source_id, source_revision)
                replacement = (
                    str(payload["replacement_scope_definition_id"]),
                    int(payload["replacement_revision"]),
                )
                if source in edges:
                    raise IntegrityError("ScopeDefinition revision has multiple successor edges")
                edges[source] = replacement
                if source[0] == replacement[0]:
                    current[source[0]] = replacement[1]
        return current, edges, evidence

    def _scope_definition(
        self,
        scope_id: str,
        revision: int,
        evidence: dict[tuple[str, int], dict[str, Any]],
    ) -> dict[str, Any]:
        created = self._scope_revision_object(
            scope_id,
            1,
            evidence.get((scope_id, 1)),
        )
        if created is None:
            raise IntegrityError("ScopeDefinition base revision is absent")
        definition = dict(created)
        for candidate_revision in range(2, revision + 1):
            amendment = self._scope_revision_object(
                scope_id,
                candidate_revision,
                evidence.get((scope_id, candidate_revision)),
            )
            if amendment is None:
                raise IntegrityError("ScopeDefinition amendment revision is absent")
            try:
                members = materialize_scope_member_changes(
                    definition.get("members", []),
                    amendment.get("member_changes", []),
                )
            except ValueError as exc:
                raise IntegrityError(
                    "ScopeDefinition amendment history contains an invalid typed member delta"
                ) from exc
            definition = {
                **definition,
                "revision": candidate_revision,
                "members": members,
            }
        return definition

    def _scope_members(
        self,
        scope_id: str,
        revision: int,
        evidence: dict[tuple[str, int], dict[str, Any]],
    ) -> dict[str, str]:
        definition = self._scope_definition(scope_id, revision, evidence)
        return {str(member["member_id"]): str(member["member_kind"]) for member in definition.get("members", [])}

    def _prepare_task_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
        *,
        command_schema: SchemaIdentity,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "Task command project must match the control-store project.",
            )
        task_id = payload.get("new_task_id") if command_type == "CreateTask" else payload.get("task_id")
        if task_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "Task payload identity must equal the target stream.",
            )

        if command_type == "CreateTask":
            definition = payload["definition"]
            if (
                definition.get("task_id") != task_id
                or definition.get("project_id") != self.ledger.project_id
                or command.envelope.get("project_id") != self.ledger.project_id
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "Task definition identity and project must bind the command.",
                )
            if definition.get("revision") != 1:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_revision",
                    "A new Task must begin at revision 1.",
                )
            if not self._content_hash_matches(definition):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_definition_hash",
                    "Task definition content hash does not match canonical content.",
                )
            return payload

        if command_type == "SupersedeTask":
            return self._prepare_supersession(
                command,
                snapshot,
                observed_version,
            )

        current, edges, evidence = self._revision_graph(snapshot)
        prior_revision = int(payload["prior_revision"])
        new_revision = int(payload["new_revision"])
        replacement = payload["replacement_definition"]
        if (
            current.get(command.target_stream_id) != prior_revision
            or (command.target_stream_id, prior_revision) in edges
        ):
            return self._rejected(
                command,
                observed_version,
                "stale_task_revision",
                "Task amendment must name the current nonterminal revision.",
            )
        if new_revision != prior_revision + 1:
            return self._rejected(
                command,
                observed_version,
                "invalid_task_revision",
                "Task amendment must advance exactly one revision.",
            )
        if (
            replacement.get("task_id") != command.target_stream_id
            or replacement.get("revision") != new_revision
            or replacement.get("project_id") != self.ledger.project_id
            or command.envelope.get("project_id") != self.ledger.project_id
        ):
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "Replacement Task definition must bind the command and revision.",
            )
        if not self._content_hash_matches(replacement):
            return self._rejected(
                command,
                observed_version,
                "invalid_task_definition_hash",
                "Replacement Task definition hash does not match canonical content.",
            )
        source_definition = self._task_revision_object(
            command.target_stream_id,
            prior_revision,
        )
        if source_definition is None:
            return self._rejected(
                command,
                observed_version,
                "task_revision_missing",
                "The prior immutable Task revision is absent.",
            )
        source_kind = self._task_revision_kind(
            source_definition,
            evidence.get((command.target_stream_id, prior_revision)),
            task_id=command.target_stream_id,
            revision=prior_revision,
        )
        if source_kind != "rich":
            return self._rejected(
                command,
                observed_version,
                "source_task_definition_incompatible",
                "Task amendment requires a matching rich source definition.",
            )
        actual_changes = changed_task_fields(
            source_definition,
            replacement,
        )
        if not actual_changes or set(payload["changed_fields"]) != actual_changes:
            return self._rejected(
                command,
                observed_version,
                "task_changed_fields_mismatch",
                "Task changed_fields must name the exact typed definition delta.",
            )
        if command_schema.schema_id != "ars://core/command/AmendTask":
            raise IntegrityError("Task amendment used an unexpected schema identity")
        return payload

    def _prepare_scope_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "ScopeDefinition command project must match the control-store project.",
            )
        scope_id = (
            payload.get("new_scope_definition_id")
            if command_type == "CreateScopeDefinition"
            else payload.get("scope_definition_id")
        )
        if scope_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "ScopeDefinition payload identity must equal the target stream.",
            )

        if command_type == "CreateScopeDefinition":
            members = payload["members"]
            if (
                payload["revision"] != 1
                or not has_unique_member_ids(members)
                or command.envelope.get("project_id") != self.ledger.project_id
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_definition",
                    "A new ScopeDefinition requires revision 1 and unique members.",
                )
            return payload

        current, edges, evidence = self._scope_revision_graph(snapshot)
        source_revision = current.get(command.target_stream_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                "scope_revision_missing",
                "The current ScopeDefinition revision is absent.",
            )
        source = (command.target_stream_id, source_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                "scope_revision_terminal",
                "The current ScopeDefinition revision is terminal.",
            )

        if command_type == "AmendScopeDefinition":
            prior_revision = int(payload["prior_revision"])
            new_revision = int(payload["new_revision"])
            if source_revision != prior_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "stale_scope_revision",
                    "ScopeDefinition amendment must name the current revision.",
                )
            if new_revision != prior_revision + 1:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_revision",
                    "ScopeDefinition amendment must advance exactly one revision.",
                )
            if set(payload["changed_fields"]) != {"members"}:
                return self._rejected(
                    command,
                    observed_version,
                    "unsupported_scope_amendment_field",
                    "The accepted delta contract materializes only member changes.",
                )
            member_changes = payload["member_changes"]
            if not member_changes or not has_unique_member_ids(member_changes):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_definition",
                    "ScopeDefinition amendment member identities must be unique.",
                )
            if (
                self._scope_revision_object(
                    command.target_stream_id,
                    prior_revision,
                    evidence.get((command.target_stream_id, prior_revision)),
                )
                is None
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "scope_revision_missing",
                    "The prior immutable ScopeDefinition revision is absent.",
                )
            source_definition = self._scope_definition(
                command.target_stream_id,
                prior_revision,
                evidence,
            )
            try:
                materialize_scope_member_changes(
                    source_definition.get("members", []),
                    member_changes,
                )
            except ValueError as exc:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_definition",
                    str(exc),
                )
            return payload

        replacement = (
            str(payload["replacement_scope_definition_id"]),
            int(payload["replacement_revision"]),
        )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                "scope_supersession_cycle",
                "The replacement ScopeDefinition reaches the source revision.",
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                "replacement_scope_revision_terminal",
                "The replacement ScopeDefinition revision is terminal.",
            )
        if (
            current.get(replacement[0]) != replacement[1]
            or self._scope_revision_object(
                *replacement,
                committed_payload=evidence.get(replacement),
            )
            is None
        ):
            return self._rejected(
                command,
                observed_version,
                "replacement_scope_revision_missing",
                "The replacement must be the current immutable ScopeDefinition revision.",
            )
        expected_members = self._scope_members(*source, evidence=evidence)
        if not has_unique_member_ids(payload["member_dispositions"]):
            return self._rejected(
                command,
                observed_version,
                "duplicate_scope_member_disposition",
                "Each current ScopeDefinition member requires one disposition.",
            )
        dispositions = {str(item["member_id"]): str(item["member_kind"]) for item in payload["member_dispositions"]}
        if dispositions != expected_members:
            return self._rejected(
                command,
                observed_version,
                "missing_scope_member_disposition",
                "Every current ScopeDefinition member requires one exact disposition.",
            )
        return payload

    def _prepare_exact_supersession(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        replacement_id = str(payload["replacement_task_id"])
        replacement_revision = int(payload["replacement_task_revision"])
        dispositions = payload["continuing_consumer_dispositions"]
        if not dispositions:
            return self._rejected(
                command,
                observed_version,
                "missing_continuing_consumer_disposition",
                "Task supersession requires explicit continuing-consumer dispositions.",
            )

        current, edges, evidence = self._revision_graph(snapshot)
        source_id = command.target_stream_id
        source_revision = current.get(source_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                "source_revision_missing",
                "The source Task revision is absent from committed events.",
            )
        source = (source_id, source_revision)
        replacement = (replacement_id, replacement_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                "source_revision_terminal",
                "The source Task revision is already terminal.",
            )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                "supersession_cycle",
                "The proposed replacement reaches the source revision.",
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_terminal",
                "The replacement Task revision is already terminal.",
            )

        source_object = self._task_revision_object(source_id, source_revision)
        replacement_object = self._task_revision_object(*replacement)
        if source_object is None or replacement_object is None:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_missing",
                "The replacement must be an existing immutable Task revision.",
            )
        if replacement_id == source_id:
            if replacement_revision <= source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "replacement_revision_stale",
                    "A same-Task replacement must be a higher revision.",
                )
        elif current.get(replacement_id) != replacement_revision:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_stale",
                "The replacement is not the current Task revision.",
            )
        source_evidence = evidence.get(source)
        source_kind = self._task_revision_kind(
            source_object,
            source_evidence,
            task_id=source_id,
            revision=source_revision,
        )
        if replacement_id == source_id and source_kind == "rich":
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_uncommitted",
                "A rich same-Task replacement requires a committed revision transition.",
            )
        replacement_evidence = evidence.get(replacement)
        if (
            replacement_id == source_id
            and replacement_evidence is None
            and source_evidence is not None
            and not source_evidence.exact
        ):
            replacement_evidence = _TaskRevisionEvidence(
                source_evidence.schema_id,
                None,
            )
        replacement_kind = self._task_revision_kind(
            replacement_object,
            replacement_evidence,
            task_id=replacement_id,
            revision=replacement_revision,
        )
        if (
            source_kind is None
            or replacement_kind is None
            or source_kind != replacement_kind
            or (source_kind == "generic" and source_object.get("task_type") != replacement_object.get("task_type"))
        ):
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_incompatible",
                "The replacement Task revision is type-incompatible.",
            )
        expected_consumers = source_object.get("continuing_consumers")
        if expected_consumers is not None and set(dispositions) != set(expected_consumers):
            return self._rejected(
                command,
                observed_version,
                "continuing_consumers_mismatch",
                "Continuing-consumer dispositions must equal the legacy source contract.",
            )
        return dict(payload)

    def _prepare_supersession(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate a revision-qualified edge from one committed snapshot."""
        if command.envelope.get("schema_id") == "ars://core/command/SupersedeTask":
            return self._prepare_exact_supersession(
                command,
                snapshot,
                observed_version,
            )
        payload = command.envelope["payload"]
        exact_fields = {
            "replacement_task_id",
            "replacement_task_revision",
            "supersession_scope",
            "continuing_consumers",
        }
        if set(payload) != exact_fields:
            return self._rejected(
                command,
                observed_version,
                "invalid_supersession_payload",
                "SupersedeTask payload fields are not exact; caller lineage is forbidden.",
            )
        replacement_id = payload["replacement_task_id"]
        replacement_revision = payload["replacement_task_revision"]
        scope = payload["supersession_scope"]
        consumers = payload["continuing_consumers"]
        if (
            not isinstance(replacement_id, str)
            or not isinstance(replacement_revision, int)
            or isinstance(replacement_revision, bool)
            or replacement_revision < 1
            or not isinstance(scope, list)
            or not scope
            or len(scope) != len(set(scope))
            or not all(isinstance(item, str) and item for item in scope)
            or not isinstance(consumers, list)
            or not consumers
            or len(consumers) != len(set(consumers))
            or not all(isinstance(item, str) and item for item in consumers)
        ):
            return self._rejected(
                command,
                observed_version,
                "invalid_supersession_payload",
                "SupersedeTask requires positive revisions and non-empty exact sets.",
            )

        current, edges, evidence = self._revision_graph(snapshot)
        source_id = command.target_stream_id
        source_revision = current.get(source_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                "source_revision_missing",
                "The source Task revision is absent from committed events.",
            )
        source = (source_id, source_revision)
        replacement = (replacement_id, replacement_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                "source_revision_terminal",
                "The source Task revision is already terminal.",
            )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                "supersession_cycle",
                "The proposed replacement reaches the source revision.",
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_terminal",
                "The replacement Task revision is already terminal.",
            )

        source_object = self._task_revision_object(source_id, source_revision)
        replacement_object = self._task_revision_object(
            replacement_id,
            replacement_revision,
        )
        if source_object is None or replacement_object is None:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_missing",
                "The replacement must be an existing immutable Task revision.",
            )
        if replacement_id == source_id:
            if replacement_revision <= source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "replacement_revision_stale",
                    "A same-Task replacement must be a higher revision.",
                )
        elif current.get(replacement_id) != replacement_revision:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_stale",
                "The replacement is not the current Task revision.",
            )
        source_kind = self._task_revision_kind(
            source_object,
            evidence.get(source),
            task_id=source_id,
            revision=source_revision,
        )
        replacement_evidence = evidence.get(replacement)
        if (
            replacement_id == source_id
            and replacement_evidence is None
            and evidence.get(source) is not None
            and not evidence[source].exact
        ):
            replacement_evidence = _TaskRevisionEvidence(
                evidence[source].schema_id,
                None,
            )
        replacement_kind = self._task_revision_kind(
            replacement_object,
            replacement_evidence,
            task_id=replacement_id,
            revision=replacement_revision,
        )
        if (
            source_kind != "generic"
            or replacement_kind != "generic"
            or source_object.get("task_type") != replacement_object.get("task_type")
        ):
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_incompatible",
                "The replacement Task revision is type-incompatible.",
            )
        expected_consumers = source_object.get("continuing_consumers")
        if expected_consumers is not None and set(consumers) != set(expected_consumers):
            return self._rejected(
                command,
                observed_version,
                "continuing_consumers_mismatch",
                "Continuing consumers must equal the source revision contract.",
            )
        return {
            "source_task_id": source_id,
            "source_task_revision": source_revision,
            "replacement_task_id": replacement_id,
            "replacement_task_revision": replacement_revision,
            "supersession_scope": list(scope),
            "continuing_consumers": sorted(consumers),
            "actor_id": command.actor_id,
            "authority_grant_id": command.envelope["authority_grant_id"],
            "lineage": self._derived_lineage(edges, source, replacement),
        }

    def _stored_conflict_receipt(self, command: Command) -> Receipt | None:
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != "conflict":
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError("command ID conflicts with stored receipt")
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or stored.reason_code not in {"stream_version_conflict", "idempotency_conflict"}
        ):
            raise IntegrityError("stored conflict receipt is inconsistent")
        return stored

    def _view_for(self, snapshot: LedgerSnapshot) -> _CommandView:
        if self._view is None or self._view.fingerprint != snapshot.fingerprint:
            self._view = _CommandView.from_snapshot(
                snapshot,
                self.schemas,
                self._authority_state_validator(),
            )
        return self._view

    def _authority_state_validator(
        self,
    ) -> Callable[[dict[str, Any]], None] | None:
        resolver = self._canonical_authority_resolver()
        return resolver.validate_replayed_administration_state if resolver is not None else None

    def _matching_committed(
        self,
        command: Command,
        view: _CommandView,
        *,
        command_schema: SchemaIdentity,
    ) -> list[dict[str, Any]] | None:
        base_scope = (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )
        schema_scope = (
            command_schema.schema_id,
            command_schema.schema_version,
            command_schema.sha256,
        )
        scope = (*base_scope, *schema_scope)
        scoped = view.batches_by_scope.get(scope)
        if scoped is not None:
            first = scoped[0]
            if (
                command.envelope["command_type"] in _MESSAGE_COMMAND_TYPES
                and first.get("command_id") != command.command_id
            ):
                raise ConflictError("idempotency key conflicts with committed command")
            same_submission = (
                first.get("command_payload_hash") == command.payload_hash
                and first.get("stream_id") == command.target_stream_id
                and first.get("stream_version") == command.expected_stream_version + 1
            )
            if same_submission:
                return list(scoped)
            raise ConflictError("idempotency key conflicts with committed command")
        if base_scope in view.base_scopes:
            raise ConflictError("idempotency key conflicts with committed command schema")
        identified = view.batches_by_command_id.get(command.command_id)
        if identified is not None:
            raise ConflictError("command ID conflicts with committed command")
        return None

    def _return_or_reconstruct(self, events: list[dict[str, Any]]) -> Receipt:
        receipt = Receipt(
            status="accepted",
            command_id=events[0]["command_id"],
            payload_hash=events[0]["command_payload_hash"],
            event_batch_id=events[0]["transaction_id"],
            observed_stream_version=max(
                event["stream_version"] for event in events if event["stream_id"] == events[0]["stream_id"]
            ),
        )
        stored = self.receipts.load(receipt.command_id)
        if stored is not None:
            if stored != receipt:
                raise IntegrityError("stored receipt does not match committed batch")
            return stored
        return self.receipts.write(receipt)

    def _build_event(
        self,
        command: Command,
        prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None,
        *,
        command_schema: SchemaIdentity,
    ) -> dict[str, Any]:
        command_type = command.envelope["command_type"]
        if command_type == "CreateScopeDefinition":
            self.objects.write(
                "scope_definition",
                command.target_stream_id,
                int(command.envelope["payload"]["revision"]),
                command.envelope["payload"],
            )
            event_type = "ScopeDefinitionCreated"
            payload = command.envelope["payload"]
        elif command_type == "AmendScopeDefinition":
            self.objects.write(
                "scope_definition",
                command.target_stream_id,
                int(command.envelope["payload"]["new_revision"]),
                command.envelope["payload"],
            )
            event_type = "ScopeDefinitionAmended"
            payload = command.envelope["payload"]
        elif command_type == "SupersedeScopeDefinition":
            event_type = "ScopeDefinitionSuperseded"
            payload = command.envelope["payload"]
        elif command_type == "CreateTask":
            create_binding = self.schemas.command_binding("CreateTask")
            activated_create = create_binding is not None and (
                command_schema.schema_id,
                command_schema.schema_version,
            ) == (
                create_binding.schema_id,
                create_binding.schema_version,
            )
            self.objects.write(
                "task",
                command.target_stream_id,
                1,
                (command.envelope["payload"]["definition"] if activated_create else command.envelope["payload"]),
            )
            event_type = "TaskCreated"
            payload = command.envelope["payload"]
        elif command_type == "AmendTask":
            self.objects.write(
                "task",
                command.target_stream_id,
                int(command.envelope["payload"]["new_revision"]),
                command.envelope["payload"]["replacement_definition"],
            )
            event_type = "TaskAmended"
            payload = command.envelope["payload"]
        elif command_type == "ClaimDispatch":
            event_type = "DispatchClaimed"
            payload = {"attempt_id": new_id("attempt")}
        elif command_type == "SupersedeTask":
            if prepared_payload is None:
                raise IntegrityError("SupersedeTask requires prepared graph payload")
            event_type = "TaskSuperseded"
            payload = prepared_payload
        elif command_type == "PublishMessage":
            event_type = "MessagePublished"
            payload = deepcopy(command.envelope["payload"])
        elif command_type == "RecordMessageDelivery":
            event_type = "MessageDelivered"
            payload = deepcopy(command.envelope["payload"])
        elif command_type == "AcknowledgeMessage":
            event_type = "MessageAcknowledged"
            payload = deepcopy(command.envelope["payload"])
        elif command_type == "RecordMessageDeliveryFailure":
            event_type = "MessageDeliveryFailed"
            payload = deepcopy(command.envelope["payload"])
        elif command_type == "VerifyEvidenceDeletion":
            authorizer = self.deletion_manifest_authorizer
            if authorizer is None:
                raise ArsError("VerifyEvidenceDeletion requires a trusted deletion manifest authorizer")
            payload = authorizer(
                command.envelope["payload"],
                command.actor_id,
                command.envelope["authority_grant_id"],
            )
            if payload.get("status") != "verified":
                raise ArsError("deletion manifest authorizer did not verify")
            event_type = "EvidenceDeletionVerified"
        elif command_type == "RevokeAuthorityGrant":
            if prepared_payload is None:
                raise IntegrityError("RevokeAuthorityGrant requires prepared payload")
            event_type = "AuthorityGrantRevoked"
            payload = prepared_payload
        elif command_type in {
            "ActivateAuthorityGrant",
            "ActivateExternalAssuranceRecordGrant",
        }:
            if prepared_payload is None:
                raise IntegrityError(f"{command_type} requires prepared payload")
            event_type = "AuthorityGrantActivated"
            payload = prepared_payload
        elif command_type in {
            "RevokeIssuedAuthorityGrant",
            "RevokeExternalAssuranceRecordGrant",
        }:
            if prepared_payload is None:
                raise IntegrityError(f"{command_type} requires prepared payload")
            event_type = "AuthorityGrantRevoked"
            payload = prepared_payload
        elif command_type == "PublishReleaseGateDecision":
            if not isinstance(prepared_payload, VerifiedReleasePublication):
                raise IntegrityError("PublishReleaseGateDecision requires verified publication")
            event_type = "ReleaseGateDecisionPublished"
            payload = None
        else:
            raise ArsError(f"unsupported command type: {command_type}")
        event_binding = self.schemas.event_binding(event_type, command_type)
        event_schema_id = event_binding.schema_id if event_binding is not None else "ars://core/event"
        event_schema_version = event_binding.schema_version if event_binding is not None else "1.0.0"
        if event_type == "ReleaseGateDecisionPublished" and event_binding is None:
            event_schema_id = "ars://core/event/ReleaseGateDecisionPublished"
        envelope = {
            "event_type": event_type,
            "stream_id": command.target_stream_id,
            "command_id": command.command_id,
            "command_type": command_type,
            "command_schema_id": command_schema.schema_id,
            "command_schema_version": command_schema.schema_version,
            "command_schema_sha256": command_schema.sha256,
            "actor_id": command.actor_id,
            "authority_grant_id": command.envelope["authority_grant_id"],
            "idempotency_key": command.idempotency_key,
            "command_payload_hash": command.payload_hash,
            "correlation_id": command.envelope["correlation_id"],
            "causation_id": command.envelope["causation_id"],
            "schema_id": event_schema_id,
            "schema_version": event_schema_version,
            "occurred_at": None,
        }
        return envelope if payload is None else {**envelope, "payload": payload}

    def _prepare_release_publication(
        self,
        command: Command,
    ) -> VerifiedReleasePublication:
        evidence = self.release_publication_evidence
        if evidence is None:
            raise PublicationEvidenceError("release publication evidence resolver is unavailable")
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("release publication requires the canonical authority resolver")
        request = ReleasePublicationRequest.from_dict(command.envelope["payload"])
        resolved = resolver.resolve(
            request.publication_authority_grant_id,
            command.actor_id,
            "PublishReleaseGateDecision",
            self.ledger.project_id,
            "release_gate_decision",
            command.target_stream_id,
            self.clock(),
        )
        if resolved.authority_grant_sha256 != request.publication_authority_sha256:
            raise ArsError("publication authority hash mismatch")
        verified = verify_release_publication(request, evidence, self.schemas)
        if (
            verified.publication_authority_grant_id != command.envelope["authority_grant_id"]
            or verified.publication_authority_sha256 != resolved.authority_grant_sha256
        ):
            raise ArsError("publication authority evidence mismatch")
        return verified

    def _prepare_authority_revocation(self, command: Command, observed_version: int) -> dict[str, Any]:
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("RevokeAuthorityGrant requires authority resolver")
        payload = command.envelope["payload"]
        fields = {
            "project_id",
            "target_grant_id",
            "target_grant_sha256",
            "authority_grant_sha256",
            "reason",
        }
        if set(payload) != fields or not isinstance(payload.get("reason"), str) or not payload["reason"]:
            raise ArsError("invalid authority revocation payload")
        if payload["project_id"] != self.ledger.project_id:
            raise ArsError("authority revocation project mismatch")
        if payload["target_grant_id"] != command.target_stream_id:
            raise ArsError("authority revocation target mismatch")
        now = self.clock()
        authorizing = resolver.resolve(
            command.envelope["authority_grant_id"],
            command.actor_id,
            "RevokeAuthorityGrant",
            self.ledger.project_id,
            "authority_grant",
            command.target_stream_id,
            now,
        )
        target = resolver.grant_at(command.target_stream_id, now)
        if authorizing.authority_grant_sha256 != payload["authority_grant_sha256"]:
            raise ArsError("authority revocation authorizing hash mismatch")
        if target.authority_grant_sha256 != payload["target_grant_sha256"]:
            raise ArsError("authority revocation target hash mismatch")
        if observed_version != 1:
            raise ArsError("authority revocation requires active version 1")
        return {
            "project_id": self.ledger.project_id,
            "target_grant_id": target.authority_grant_id,
            "target_grant_sha256": target.authority_grant_sha256,
            "authorizing_grant_id": authorizing.authority_grant_id,
            "authorizing_grant_sha256": authorizing.authority_grant_sha256,
            "reason": payload["reason"],
        }

    def _prepare_scoped_authority_activation(
        self,
        command: Command,
        observed_version: int,
    ) -> dict[str, Any]:
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("ActivateAuthorityGrant requires authority resolver")
        payload = command.envelope["payload"]
        context = resolver.administration_context()
        if (
            observed_version != 0
            or command.envelope.get("project_id") != self.ledger.project_id
            or payload.get("project_id") != self.ledger.project_id
            or payload.get("bootstrap_manifest_sha256") != context.bootstrap_manifest_sha256
            or command.envelope.get("authority_grant_id") != context.root_grant_id
            or payload.get("root_grant_id") != context.root_grant_id
            or payload.get("root_grant_sha256") != context.root_grant_sha256
            or command.actor_id != context.owner_actor_id
            or command.envelope.get("on_behalf_of_actor_id") is not None
        ):
            raise ArsError("scoped authority activation anchor mismatch")
        grant_schema_id, grant_schema_version = self._scoped_grant_schema_for_command(command.envelope["command_type"])
        grant_value = payload.get("new_grant")
        try:
            grant = ScopedAuthorityGrant.from_dict(
                grant_value,
                expected_schema_id=grant_schema_id,
                expected_schema_version=grant_schema_version,
            )
        except ValueError as exc:
            raise ArsError("scoped authority grant invalid") from exc
        if grant.authority_grant_id != command.target_stream_id or grant.canonical_sha256 != payload.get(
            "new_grant_sha256"
        ):
            raise ArsError("scoped authority activation target mismatch")
        schema_identity = self.schemas.resolve_identity(
            grant_schema_id,
            grant_schema_version,
            expected_sha256=str(payload.get("new_grant_schema_sha256", "")),
        )
        if not self.schemas.is_active(
            schema_identity.schema_id,
            str(schema_identity.schema_version),
        ):
            raise ArsError("scoped authority grant schema is not active")
        self.schemas.validate_active(
            schema_identity.schema_id,
            grant_value,
            schema_version=grant_schema_version,
            expected_sha256=schema_identity.sha256,
        )
        validate_scoped_grant_activation(
            grant,
            self.schemas,
            owner_actor_id=context.owner_actor_id,
        )
        decision = resolver.verify_owner_administration_decision(
            str(payload.get("administration_decision_id", "")),
            str(payload.get("administration_decision_sha256", "")),
            action="activate_authority_grant",
            target_grant_id=grant.authority_grant_id,
            target_grant_sha256=grant.canonical_sha256,
            target_grant_schema_sha256=schema_identity.sha256,
            target_grant_schema_id=schema_identity.schema_id,
            target_grant_schema_version=str(schema_identity.schema_version),
            subject_scope=grant.subject_scope,
            effective_at=grant.effective_at,
            expires_at=grant.expires_at,
            owner_actor_id=command.actor_id,
            now=self.clock(),
        )
        if decision.record_id not in command.envelope.get("evidence_refs", []):
            raise ArsError("owner authority administration decision evidence missing")
        self.objects.write(
            "authority_grant",
            grant.authority_grant_id,
            1,
            grant_value,
        )
        return {
            "authority_admission_version": SCOPED_AUTHORITY_ADMISSION_VERSION,
            "project_id": self.ledger.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision.record_id,
            "administration_decision_sha256": decision.canonical_sha256,
            "activated_grant_id": grant.authority_grant_id,
            "activated_grant_sha256": grant.canonical_sha256,
            "activated_grant_schema_id": schema_identity.schema_id,
            "activated_grant_schema_version": schema_identity.schema_version,
            "activated_grant_schema_sha256": schema_identity.sha256,
            "subject_scope": grant.subject_scope.to_dict(),
            "effective_at": payload["new_grant"]["effective_at"],
            "expires_at": payload["new_grant"]["expires_at"],
        }

    @staticmethod
    def _scoped_grant_schema_for_command(command_type: str) -> tuple[str, str]:
        if command_type == "ActivateExternalAssuranceRecordGrant":
            return EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID, EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION
        return SCOPED_AUTHORITY_GRANT_SCHEMA_ID, SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION

    def _prepare_issued_authority_revocation(
        self,
        command: Command,
        observed_version: int,
    ) -> dict[str, Any]:
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("RevokeIssuedAuthorityGrant requires authority resolver")
        payload = command.envelope["payload"]
        context = resolver.administration_context()
        if (
            observed_version != 1
            or command.envelope.get("project_id") != self.ledger.project_id
            or payload.get("project_id") != self.ledger.project_id
            or payload.get("bootstrap_manifest_sha256") != context.bootstrap_manifest_sha256
            or command.envelope.get("authority_grant_id") != context.root_grant_id
            or payload.get("root_grant_id") != context.root_grant_id
            or payload.get("root_grant_sha256") != context.root_grant_sha256
            or command.actor_id != context.owner_actor_id
            or command.envelope.get("on_behalf_of_actor_id") is not None
            or payload.get("target_grant_id") != command.target_stream_id
            or payload.get("reason") != command.envelope.get("reason")
        ):
            raise ArsError("issued authority revocation anchor mismatch")
        target = resolver.scoped_grant_identity(command.target_stream_id)
        if (
            target.status != "active"
            or target.authority_grant_sha256 != payload.get("target_grant_sha256")
            or target.schema_sha256 != payload.get("target_grant_schema_sha256")
        ):
            raise ArsError("issued authority revocation target mismatch")
        decision = resolver.verify_owner_administration_decision(
            str(payload.get("administration_decision_id", "")),
            str(payload.get("administration_decision_sha256", "")),
            action="revoke_issued_authority_grant",
            target_grant_id=target.authority_grant_id,
            target_grant_sha256=target.authority_grant_sha256,
            target_grant_schema_sha256=target.schema_sha256,
            target_grant_schema_id=target.schema_id,
            target_grant_schema_version=target.schema_version,
            subject_scope=target.subject_scope,
            effective_at=target.effective_at,
            expires_at=target.expires_at,
            owner_actor_id=command.actor_id,
            now=self.clock(),
        )
        if decision.record_id not in command.envelope.get("evidence_refs", []):
            raise ArsError("owner authority administration decision evidence missing")
        return {
            "authority_admission_version": SCOPED_AUTHORITY_ADMISSION_VERSION,
            "project_id": self.ledger.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision.record_id,
            "administration_decision_sha256": decision.canonical_sha256,
            "target_grant_id": target.authority_grant_id,
            "target_grant_sha256": target.authority_grant_sha256,
            "target_grant_schema_id": target.schema_id,
            "target_grant_schema_version": target.schema_version,
            "target_grant_schema_sha256": target.schema_sha256,
            "reason": payload["reason"],
        }


del _release_submit_guard
