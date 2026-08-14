"""Owner-governed registration of real Codex Desktop authority sessions.

The public input is semantic owner intent.  Actor IDs, registration IDs, object
hashes, event identity, and the receipt are derived only after the repaired
binding and authority bootstrap have been verified by ``OwnerAuthoritySetup``.
"""

from __future__ import annotations

import json
import hashlib
import os
import uuid
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError, ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry
from research_system.store.durability import fsync_directory
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore


COMMAND_SCHEMA_ID = "ars://wp6-6/gate6/authority/command/RegisterAuthorityActor"
EVENT_SCHEMA_ID = "ars://wp6-6/gate6/authority/event/AuthorityActorRegistered"
ACTOR_SCHEMA_ID = "ars://wp6-6/gate6/authority/object/CanonicalAuthorityActor"
REGISTRATION_SCHEMA_ID = "ars://wp6-6/gate6/authority/object/AuthorityActorRegistration"
RECEIPT_SCHEMA_ID = "ars://wp6-6/gate6/authority/receipt/AuthorityActorRegistration"
_MARKER_PREFIX = ".authority-actor-registration-"


def _require_physical_target(root: Path, relative: Path, *, label: str) -> None:
    """Reject redirected components before touching immutable actor evidence."""
    current = root
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise IntegrityError(f"{label} path is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse:
            raise IntegrityError(f"{label} path has a redirected component")


def _deterministic_id(kind: str, prefix: str, value: object) -> str:
    digest = bytearray(hashlib.sha256(canonical_bytes({"kind": kind, "value": value})).digest()[:16])
    digest[6] = (digest[6] & 0x0F) | 0x70
    digest[8] = (digest[8] & 0x3F) | 0x80
    return f"{prefix}_{uuid.UUID(bytes=bytes(digest))}"


def _utc_text(value: object, field: str) -> tuple[datetime, str]:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ConfigurationError(f"{field} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ConfigurationError(f"{field} must be a canonical UTC timestamp") from exc
    canonical = parsed.isoformat().replace("+00:00", "Z")
    if parsed.tzinfo != UTC or canonical != value:
        raise ConfigurationError(f"{field} must be a canonical UTC timestamp")
    return parsed, canonical


def _publish(path: Path, value: Mapping[str, Any]) -> Path:
    data = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ConflictError(f"actor registration artifact conflicts: {path}")
        return path
    temporary = path.with_name(f".{path.name}.{sha256_hex(data)[:16]}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return path


@dataclass(frozen=True)
class RegisterAuthorityActor:
    canonical_display_name: str
    actor_class: str
    app_family: str
    observed_app_version: str
    session_identity: str
    session_purpose: str
    actor_role: str
    authority_lane: str
    effective_at: str
    expires_at: str
    evidence_refs: tuple[str, ...]
    reason: str
    owner_action: str
    retry_key: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RegisterAuthorityActor":
        expected = {
            "schema_id",
            "schema_version",
            "command_type",
            "retry_key",
            "canonical_display_name",
            "actor_class",
            "app_family",
            "observed_app_version",
            "session_identity",
            "session_purpose",
            "actor_role",
            "authority_lane",
            "effective_at",
            "expires_at",
            "evidence_refs",
            "reason",
            "owner_action",
        }
        if set(value) != expected:
            raise ConfigurationError("RegisterAuthorityActor intent fields are not exact")
        if (
            value.get("schema_id") != COMMAND_SCHEMA_ID
            or value.get("schema_version") != "1.0.0"
            or value.get("command_type") != "RegisterAuthorityActor"
        ):
            raise ConfigurationError("RegisterAuthorityActor intent schema is unsupported")
        strings = (
            "retry_key",
            "canonical_display_name",
            "observed_app_version",
            "session_identity",
            "session_purpose",
            "authority_lane",
            "effective_at",
            "expires_at",
            "reason",
            "owner_action",
        )
        if any(not isinstance(value.get(field), str) or not value[field].strip() for field in strings):
            raise ConfigurationError("RegisterAuthorityActor intent contains an empty field")
        refs = value.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref for ref in refs):
            raise ConfigurationError("RegisterAuthorityActor evidence_refs must be non-empty strings")
        actor_class = value.get("actor_class")
        if actor_class not in {"agent", "service"}:
            raise ConfigurationError("RegisterAuthorityActor actor_class must be agent or service")
        if value.get("app_family") != "codex_desktop":
            raise ConfigurationError("RegisterAuthorityActor requires the observed codex_desktop app")
        role = value.get("actor_role")
        if role not in {"producer", "independent_reviewer", "operator"}:
            raise ConfigurationError("RegisterAuthorityActor actor_role is not supported")
        if value.get("owner_action") != "register-codex-desktop-actor":
            raise ConfigurationError("RegisterAuthorityActor owner action is not governed")
        return cls(
            canonical_display_name=str(value["canonical_display_name"]),
            actor_class=str(actor_class),
            app_family="codex_desktop",
            observed_app_version=str(value["observed_app_version"]),
            session_identity=str(value["session_identity"]),
            session_purpose=str(value["session_purpose"]),
            actor_role=str(role),
            authority_lane=str(value["authority_lane"]),
            effective_at=str(value["effective_at"]),
            expires_at=str(value["expires_at"]),
            evidence_refs=tuple(str(ref) for ref in refs),
            reason=str(value["reason"]),
            owner_action=str(value["owner_action"]),
            retry_key=str(value["retry_key"]),
        )

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "canonical_display_name": self.canonical_display_name,
            "actor_class": self.actor_class,
            "app_family": self.app_family,
            "observed_app_version": self.observed_app_version,
            "session_identity": self.session_identity,
            "session_purpose": self.session_purpose,
            "actor_role": self.actor_role,
            "authority_lane": self.authority_lane,
            "effective_at": self.effective_at,
            "expires_at": self.expires_at,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
            "owner_action": self.owner_action,
        }


def read_actor_registration_intent(path: Path) -> RegisterAuthorityActor:
    try:
        raw = path.resolve(strict=True).read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("invalid RegisterAuthorityActor intent") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise ConfigurationError("RegisterAuthorityActor intent must be canonical JSON")
    return RegisterAuthorityActor.from_mapping(value)


class AuthorityActorRegistrationService:
    def __init__(
        self,
        root: Path,
        project_id: str,
        store_identity: str,
        schemas: SchemaRegistry,
        resolver: Any,
        objects: ObjectStore,
        route_commands: frozenset[str],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = root
        self.project_id = validate_id(project_id, "project")
        self.store_identity = store_identity
        self.schemas = schemas
        self.resolver = resolver
        self.objects = objects
        self.route_commands = route_commands
        self.clock = clock or (lambda: datetime.now(UTC))

    def _validate_lane(self, intent: RegisterAuthorityActor) -> None:
        # Import lazily so owner_authority can consume registration evidence
        # without creating a module import cycle.
        from research_system.owner_authority import _LANE_COMMAND_POLICY, _LANE_CONTEXT_POLICY

        lane_commands = _LANE_COMMAND_POLICY.get(intent.authority_lane)
        lane_context = _LANE_CONTEXT_POLICY.get(intent.authority_lane)
        if lane_commands is None or lane_context is None or not lane_commands <= self.route_commands:
            raise ArsError("authority actor lane is outside the committed SPEC route")
        if intent.actor_role == "producer" and not intent.authority_lane.startswith("producer/"):
            raise ArsError("producer actor must use a producer SPEC lane")
        if intent.actor_role == "independent_reviewer" and not intent.authority_lane.startswith(
            "independent_reviewer/"
        ):
            raise ArsError("independent reviewer must use an independent-reviewer SPEC lane")
        if intent.actor_role == "operator" and not intent.authority_lane.startswith("operator/"):
            raise ArsError("operator actor must use an operator SPEC lane")
        allowed = {"agent", "service"}
        if intent.actor_role == "independent_reviewer":
            allowed = {"agent", "service"}
        if intent.actor_class not in allowed:
            raise ArsError("authority actor class is not permitted for this SPEC lane")

    def _existing_event(
        self,
        ledger: EventLedger,
        intent: RegisterAuthorityActor,
        payload_hash: str,
        expected_payload: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        matches = [
            event
            for event in ledger.iter_events()
            if event.get("command_type") == "RegisterAuthorityActor"
            and event.get("idempotency_key") == intent.retry_key
        ]
        if not matches:
            return None
        if len(matches) != 1 or matches[0].get("command_payload_hash") != payload_hash:
            raise ConflictError("actor registration retry key conflicts with durable event")
        event = matches[0]
        unsigned = dict(event)
        recorded_hash = unsigned.pop("event_hash", None)
        if recorded_hash != sha256_hex(canonical_bytes(unsigned)):
            raise IntegrityError("actor registration event bytes are tampered")
        payload = event.get("payload")
        if (
            not isinstance(payload, dict)
            or payload != dict(expected_payload)
            or payload.get("actor_id") != event.get("stream_id")
        ):
            raise IntegrityError("actor registration event relation is invalid")
        return event

    def register(
        self,
        intent: RegisterAuthorityActor,
        *,
        phase_hook: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        now = self.clock()
        if now.tzinfo != UTC:
            raise ConfigurationError("actor registration clock must be UTC")
        effective, effective_text = _utc_text(intent.effective_at, "effective_at")
        expires, expires_text = _utc_text(intent.expires_at, "expires_at")
        if effective >= expires or now < effective or now >= expires:
            raise ConfigurationError("actor registration window is not current and finite")
        self._validate_lane(intent)
        context = self.resolver.administration_context()
        owner_actor_id = context.owner_actor_id
        if intent.actor_class not in {"agent", "service"} or intent.app_family != "codex_desktop":
            raise ArsError("authority actor registration is not a real Codex Desktop session")
        if intent.observed_app_version.strip().lower() in {"unknown", "n/a", "unspecified"}:
            raise ArsError("authority actor registration requires an observed app version")
        if intent.session_identity.strip().lower() in {"unknown", "synthetic", "fake", "unspecified"}:
            raise ArsError("authority actor registration requires a real session identity")
        if intent.session_identity == owner_actor_id:
            raise ArsError("the bound owner actor cannot be registered as a non-owner lane")

        semantic = intent.semantic_payload()
        payload_hash = sha256_hex(canonical_bytes(semantic))
        actor_identity = {
            "project_id": self.project_id,
            "app_family": intent.app_family,
            "session_identity": intent.session_identity,
        }
        actor_id = _deterministic_id("authority-actor", "act", actor_identity)
        registration_id = _deterministic_id(
            "authority-actor-registration", "arec", {"owner_actor_id": owner_actor_id, "semantic": semantic}
        )
        command_id = _deterministic_id(
            "authority-actor-command", "cmd", {"owner_actor_id": owner_actor_id, "retry_key": intent.retry_key}
        )
        marker_path = self.root / "runtime" / f"{_MARKER_PREFIX}{sha256_hex(intent.retry_key.encode('utf-8'))}.json"
        ledger = EventLedger(self.root, self.project_id, self.schemas, store_identity=self.store_identity)
        actor_existing = None
        _require_physical_target(self.root, Path("objects/canonical_actor") / actor_id, label="canonical actor")
        _require_physical_target(
            self.root, Path("objects/assurance_record") / registration_id, label="actor registration"
        )
        actor_revision = self.objects.latest_revision("canonical_actor", actor_id)
        if actor_revision is not None:
            actor_existing = self.objects.read("canonical_actor", actor_id, actor_revision)
        registration_existing = None
        registration_revision = self.objects.latest_revision("assurance_record", registration_id)
        if registration_revision is not None:
            registration_existing = self.objects.read("assurance_record", registration_id, registration_revision)
        actor_value = {
            "schema_id": ACTOR_SCHEMA_ID,
            "schema_version": "1.0.0",
            "actor_id": actor_id,
            "project_id": self.project_id,
            "store_identity": self.store_identity,
            "owner_actor_id": owner_actor_id,
            **semantic,
            "effective_at": effective_text,
            "expires_at": expires_text,
            "registration_id": registration_id,
            "revoked": False,
        }
        actor_sha = sha256_hex(canonical_bytes(actor_value))
        registration_value = {
            "schema_id": REGISTRATION_SCHEMA_ID,
            "schema_version": "1.0.0",
            "registration_id": registration_id,
            "project_id": self.project_id,
            "store_identity": self.store_identity,
            "owner_actor_id": owner_actor_id,
            "owner_action": intent.owner_action,
            "idempotency_key": intent.retry_key,
            "command_payload_hash": payload_hash,
            "actor_id": actor_id,
            "actor_sha256": actor_sha,
            "semantic_intent": semantic,
            "accepted_at": (
                registration_existing.get("accepted_at")
                if isinstance(registration_existing, dict)
                else now.isoformat().replace("+00:00", "Z")
            ),
            "revoked": False,
        }
        _utc_text(registration_value["accepted_at"], "accepted_at")
        registration_sha = sha256_hex(canonical_bytes(registration_value))
        actor_path = f"objects/canonical_actor/{actor_id}/00000001-{actor_sha}.json"
        registration_path = f"objects/assurance_record/{registration_id}/00000001-{registration_sha}.json"
        expected_event_payload = {
            "project_id": self.project_id,
            "store_identity": self.store_identity,
            "owner_actor_id": owner_actor_id,
            "actor_id": actor_id,
            "actor_sha256": actor_sha,
            "actor_object_path": actor_path,
            "registration_id": registration_id,
            "registration_sha256": registration_sha,
            "registration_object_path": registration_path,
        }
        existing_event = self._existing_event(ledger, intent, payload_hash, expected_event_payload)
        # A matching recovery marker means this invocation is completing an
        # interrupted publication and may legitimately find the actor object
        # already durable.
        if actor_existing is not None and existing_event is None and not marker_path.exists():
            raise ConflictError("authority actor session is already registered")
        receipt_path = self.root / "receipts" / "authority_actor" / f"{registration_id}.json"
        marker = {
            "schema_id": "ars://internal/authority-actor-registration-transaction",
            "schema_version": "1.0.0",
            "payload_hash": payload_hash,
            "retry_key": intent.retry_key,
            "actor_id": actor_id,
            "registration_id": registration_id,
        }
        command_schema = self.schemas.resolve_identity(COMMAND_SCHEMA_ID, "1.0.0")
        self.schemas.validate(
            COMMAND_SCHEMA_ID,
            {
                "schema_id": COMMAND_SCHEMA_ID,
                "schema_version": "1.0.0",
                "command_type": "RegisterAuthorityActor",
                "payload": semantic,
            },
        )
        self.schemas.validate(ACTOR_SCHEMA_ID, actor_value)
        self.schemas.validate(REGISTRATION_SCHEMA_ID, registration_value)

        with WriterLock(
            self.root / "runtime" / "writer.lock",
            {"writer_id": f"authority-actor:{payload_hash}", "command_type": "RegisterAuthorityActor"},
        ):
            if marker_path.exists():
                try:
                    stored_marker = json.loads(marker_path.read_bytes())
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise IntegrityError("actor registration recovery marker is invalid") from exc
                if stored_marker != marker:
                    raise ConflictError("actor registration recovery marker conflicts with intent")
            else:
                _publish(marker_path, marker)
            self.objects.write("canonical_actor", actor_id, 1, actor_value)
            if phase_hook:
                phase_hook("actor")
            self.objects.write("assurance_record", registration_id, 1, registration_value)
            if phase_hook:
                phase_hook("registration")
            event = self._existing_event(ledger, intent, payload_hash, expected_event_payload)
            if event is None:
                result = ledger._append_authority_actor_from_validated_service(
                    {
                        "event_type": "AuthorityActorRegistered",
                        "stream_id": actor_id,
                        "schema_id": EVENT_SCHEMA_ID,
                        "schema_version": "1.0.0",
                        "command_id": command_id,
                        "command_type": "RegisterAuthorityActor",
                        "idempotency_key": intent.retry_key,
                        "command_payload_hash": payload_hash,
                        "correlation_id": intent.retry_key,
                        "causation_id": None,
                        "actor_id": owner_actor_id,
                        "authority_grant_id": context.root_grant_id,
                        "occurred_at": now.isoformat().replace("+00:00", "Z"),
                        "command_schema_id": command_schema.schema_id,
                        "command_schema_version": command_schema.schema_version,
                        "command_schema_sha256": command_schema.sha256,
                        "payload": expected_event_payload,
                    },
                    snapshot=ledger.snapshot(),
                )
                event = self._existing_event(ledger, intent, payload_hash, expected_event_payload)
                if event is None:
                    raise IntegrityError("actor registration event was not persisted")
                event_batch_id = str(result["event_batch_id"])
            else:
                event_batch_id = str(event["transaction_id"])
            if phase_hook:
                phase_hook("event")
            receipt = {
                "schema_id": RECEIPT_SCHEMA_ID,
                "schema_version": "1.0.0",
                "status": "accepted",
                "command_id": command_id,
                "command_payload_hash": payload_hash,
                "event_batch_id": event_batch_id,
                "actor_id": actor_id,
                "registration_id": registration_id,
                "actor_sha256": actor_sha,
                "registration_sha256": registration_sha,
            }
            if receipt_path.exists() and receipt_path.read_bytes() != canonical_bytes(receipt):
                raise ConflictError("actor registration receipt conflicts")
            _publish(receipt_path, receipt)
            self.schemas.validate(RECEIPT_SCHEMA_ID, receipt)
            if phase_hook:
                phase_hook("receipt")
            marker_path.unlink(missing_ok=True)
            fsync_directory(marker_path.parent)
            return {
                "status": "accepted" if existing_event is None else "duplicate",
                "actor_id": actor_id,
                "registration_id": registration_id,
                "actor_sha256": actor_sha,
                "registration_sha256": registration_sha,
                "event_batch_id": event_batch_id,
                "receipt": receipt,
            }


def register_authority_actor(
    intent: RegisterAuthorityActor,
    *,
    root: Path,
    project_id: str,
    store_identity: str,
    schemas: SchemaRegistry,
    resolver: Any,
    objects: ObjectStore,
    route_commands: frozenset[str],
    clock: Callable[[], datetime] | None = None,
    phase_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    return AuthorityActorRegistrationService(
        root,
        project_id,
        store_identity,
        schemas,
        resolver,
        objects,
        route_commands,
        clock=clock,
    ).register(intent, phase_hook=phase_hook)
