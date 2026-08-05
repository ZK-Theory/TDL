"""Governed WP6.4 review and owner-decision records.

The two WP6.4 record classes have their own closed schema profile, but reuse
the established external-record binding, authority, lock, CAS, receipt, and
resolution substrate.  Governed publication is the repository's operator-
exercise boundary: it binds the exact record bytes to the attributed actor and
grant, then re-resolves that authority under the writer lock.  This proves an
owner-attributed repository action, not provider or physical-person
authentication.  Record bodies are never accepted at the evidence seam;
callers supply only opaque locators after governed publication.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError as JsonSchemaError
from jsonschema.exceptions import ValidationError

from research_system.assurance.external_records import (
    ExternalAssuranceRecordStore,
    ExternalRecordPublicationContext,
    ExternalRecordResolution,
    ExternalRecordSchemaRow,
    git_blob_id,
)
from research_system.authority import GrantedPolicyActionIdentity, ScopedAuthorityGrantResolution
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.ids import validate_id
from research_system.schema_registry import runtime_schema_registry


INDEPENDENT_SESSION_REVIEW = "independent_session_review"
OWNER_SESSION_ACCEPTANCE_DECISION = "owner_session_acceptance_decision"
PUBLISH_OWNER_OPERATED_SESSION_REVIEW = "publish_owner_operated_session_review"
ACCEPT_OWNER_OPERATED_SESSION_EVIDENCE = "accept_owner_operated_session_evidence"

_REVIEW_POLICY_SCHEMA_ID = "ars://core/policy-action/PublishOwnerOperatedSessionReview"
_ACCEPTANCE_POLICY_SCHEMA_ID = "ars://core/policy-action/AcceptOwnerOperatedSessionEvidence"
_POLICY_SCHEMA_VERSION = "1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")
_ACTOR_LOCATOR = "ars://actors/{actor_id}"

SessionRecordPublicationContext = ExternalRecordPublicationContext


_ROW_DEFINITIONS = (
    (
        INDEPENDENT_SESSION_REVIEW,
        INDEPENDENT_SESSION_REVIEW,
        "review_record_id",
        "review_state",
        "completed",
        "ars://wp6-4/independent-session-review-record",
        "independent-session-review-record.schema.json",
    ),
    (
        OWNER_SESSION_ACCEPTANCE_DECISION,
        OWNER_SESSION_ACCEPTANCE_DECISION,
        "owner_decision_id",
        "decision_state",
        "active",
        "ars://wp6-4/owner-session-acceptance-decision-record",
        "owner-session-acceptance-decision-record.schema.json",
    ),
)


class SessionRecordSchemaCatalogue:
    """Closed two-row schema profile, separate from WP6.3's frozen catalogue."""

    def __init__(self, schema_root: Path) -> None:
        try:
            root = schema_root.resolve(strict=True) / "wp6-4"
            if not root.is_dir():
                raise FileNotFoundError(root)
        except OSError as exc:
            raise SchemaError("WP6.4 session-record schema root is unavailable") from exc
        rows: dict[str, ExternalRecordSchemaRow] = {}
        validators: dict[str, Draft202012Validator] = {}
        for (
            record_class,
            record_type,
            identity_field,
            state_field,
            active_state,
            schema_id,
            filename,
        ) in _ROW_DEFINITIONS:
            path = root / filename
            try:
                raw = path.read_bytes()
                schema = json.loads(raw.decode("utf-8"))
                Draft202012Validator.check_schema(schema)
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                JsonSchemaError,
            ) as exc:
                raise SchemaError(f"invalid WP6.4 session-record schema: {filename}") from exc
            if (
                not isinstance(schema, dict)
                or schema.get("$id") != schema_id
                or schema.get("properties", {}).get("schema_version", {}).get("const") != _POLICY_SCHEMA_VERSION
            ):
                raise SchemaError(f"WP6.4 session-record schema identity mismatch: {filename}")
            row = ExternalRecordSchemaRow(
                record_class=record_class,
                record_type=record_type,
                schema_id=schema_id,
                schema_version=_POLICY_SCHEMA_VERSION,
                repository_path=f".research-system/schemas/wp6-4/{filename}",
                schema_json_pointer="#",
                schema_git_blob=git_blob_id(raw),
                schema_canonical_sha256=sha256_hex(raw),
                identity_field=identity_field,
                state_field=state_field,
                active_state=active_state,
                schema=schema,
            )
            rows[record_class] = row
            validators[record_class] = Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
            )
        if tuple(rows) != (
            INDEPENDENT_SESSION_REVIEW,
            OWNER_SESSION_ACCEPTANCE_DECISION,
        ):
            raise SchemaError("WP6.4 session-record profile must contain exactly two rows")
        self._rows = rows
        self._validators = validators

    @property
    def record_classes(self) -> tuple[str, str]:
        return (
            INDEPENDENT_SESSION_REVIEW,
            OWNER_SESSION_ACCEPTANCE_DECISION,
        )

    def row(self, record_class: str) -> ExternalRecordSchemaRow:
        try:
            return self._rows[record_class]
        except (KeyError, TypeError) as exc:
            raise SchemaError("record class is outside the WP6.4 session-record profile") from exc

    def validate(
        self,
        record_class: str,
        record_id: str,
        record: object,
    ) -> ExternalRecordSchemaRow:
        row = self.row(record_class)
        try:
            validate_id(record_id, record_class)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError(f"record identity prefix does not match class: {record_class}") from exc
        if not isinstance(record, Mapping):
            raise SchemaError("WP6.4 session record must be a JSON object")
        try:
            self._validators[record_class].validate(record)
        except ValidationError as exc:
            raise SchemaError(f"invalid WP6.4 session record: {record_class}") from exc
        if record.get("record_type") != row.record_type or record.get(row.identity_field) != record_id:
            raise SchemaError(f"WP6.4 session record identity mismatch: {record_class}")
        return row


@dataclass(frozen=True)
class SessionRecordLocator:
    """Opaque semantic locator for one governed WP6.4 record."""

    record_class: str
    record_id: str

    def __post_init__(self) -> None:
        if self.record_class not in {
            INDEPENDENT_SESSION_REVIEW,
            OWNER_SESSION_ACCEPTANCE_DECISION,
        }:
            raise SchemaError("session-record locator names an unsupported record class")
        try:
            validate_id(self.record_id, self.record_class)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError("session-record locator has the wrong typed identity") from exc


def compact_record_receipt(resolution: ExternalRecordResolution) -> dict[str, object]:
    """Return the schema-bound receipt fragment persisted in dependent records."""

    return {
        "record_class": resolution.record_class,
        "record_id": resolution.record_id,
        "revision": resolution.revision,
        "canonical_sha256": resolution.canonical_sha256,
    }


def authority_replay_receipt(
    action: Mapping[str, object],
    resolution: ScopedAuthorityGrantResolution,
    resolved_at: datetime,
) -> dict[str, object]:
    """Freeze a replay-derived authority decision without a parallel receipt type."""

    return {
        "policy_action_schema_id": action["schema_id"],
        "policy_action_schema_version": action["schema_version"],
        "policy_action_schema_sha256": action["policy_action_schema_sha256"],
        "policy_action_raw_sha256": sha256_hex(canonical_bytes(action)),
        "authority_grant_id": resolution.authority_grant_id,
        "authority_grant_sha256": resolution.authority_grant_sha256,
        "actor_id": resolution.actor_id,
        "actor_class": action["actor_class"],
        "subject_scope": {
            "kind": resolution.subject_scope.subject_kind,
            "id": resolution.subject_scope.subject_id,
        },
        "effective_at": _utc_text(resolution.effective_at),
        "expires_at": _utc_text(resolution.expires_at),
        "activation_event_id": resolution.activation_event_id,
        "activation_position": resolution.activation_position,
        "administration_decision_id": resolution.administration_decision_id,
        "administration_decision_sha256": resolution.administration_decision_sha256,
        "status": resolution.status,
        "revocation_event_id": resolution.revocation_event_id,
        "resolved_at": _utc_text(resolved_at),
    }


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise SchemaError(f"{label} must be strict RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise SchemaError(f"{label} must be UTC")
    return parsed


def _aware_utc(value: object, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IntegrityError(f"{label} must be timezone-aware")
    return value.astimezone(timezone.utc)


class SessionEvidenceRecordStore(ExternalAssuranceRecordStore):
    """Publish operator-exercised WP6.4 records through the governed writer seam."""

    def _build_catalogue(self, schema_root: Path) -> SessionRecordSchemaCatalogue:
        return SessionRecordSchemaCatalogue(schema_root)

    def __init__(
        self,
        binding: ControlBinding,
        *,
        clock: Any | None = None,
    ) -> None:
        super().__init__(binding, clock=clock)

    @property
    def control_root(self) -> Path:
        return self.objects.control_root

    def _storage_object_key(
        self,
        record_class: str,
        record_id: str,
        *,
        record: Mapping[str, Any] | None = None,
    ) -> tuple[str, str]:
        del record
        self.catalogue.row(record_class)
        try:
            validate_id(record_id, record_class)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError(f"record identity prefix does not match class: {record_class}") from exc
        return record_class, record_id

    def _check_revision_policy(
        self,
        *,
        record_class: str,
        record: Mapping[str, Any],
        history: Mapping[int, Any],
        revision: int,
        expected_previous_revision: int,
    ) -> None:
        del record_class, record, history, expected_previous_revision
        if revision != 1:
            raise ConflictError("governed WP6.4 session records are immutable revision-1 records")

    @staticmethod
    def _validate_context_id(value: object, kind: str, label: str) -> str:
        if not isinstance(value, str):
            raise SchemaError(f"session-record publication {label} is not a valid {kind} id")
        try:
            return validate_id(value, kind)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError(f"session-record publication {label} is not a valid {kind} id") from exc

    def _validate_publication_context(
        self,
        *,
        context: ExternalRecordPublicationContext,
        record_class: str,
        record_id: str,
        revision: int,
        expected_previous_revision: int,
        record: Mapping[str, Any],
    ) -> None:
        if not isinstance(context, ExternalRecordPublicationContext):
            raise SchemaError("governed session-record publication context is required")
        if (
            context.record_class != record_class
            or context.record_id != record_id
            or context.revision != revision
            or context.expected_previous_revision != expected_previous_revision
        ):
            raise SchemaError("session-record publication context does not match the request")
        if revision != 1 or expected_previous_revision != 0 or context.record_action != "create":
            raise ConflictError("governed WP6.4 session records are immutable revision-1 records")
        if context.project_id != self.binding.project_id:
            raise SchemaError("session-record publication project does not match the bound project")
        if context.store_identity != self.binding.store_identity:
            raise SchemaError("session-record publication store identity does not match the bound store")
        if context.canonical_sha256 != sha256_hex(canonical_bytes(record)):
            raise SchemaError("session-record publication body hash does not match the record")
        if context.relationship_record_id is not None:
            raise SchemaError("WP6.4 session records do not accept a relationship-record substitution")
        self._validate_context_id(context.caller_actor_id, "actor", "caller actor")
        self._validate_context_id(context.authority_grant_id, "authority_grant", "authority grant")
        self._validate_context_id(context.authority_root, "authority_grant", "authority root")
        self._validate_context_id(context.task_id, "task", "task")
        self._validate_context_id(context.session_id, "context", "session")
        subject = record.get("subject")
        if not isinstance(subject, Mapping) or subject.get("task_id") != context.task_id:
            raise SchemaError("session-record publication task does not match the exact subject")

        self._validate_record_semantics(record_class, record)

        if record_class == INDEPENDENT_SESSION_REVIEW:
            if (
                record.get("reviewer_actor_id") != context.caller_actor_id
                or record.get("reviewer_actor_class") != context.caller_actor_class
                or record.get("authority_grant_id") != context.authority_grant_id
            ):
                raise SchemaError("review publication caller or authority does not match the record")
            if record.get("reviewer_actor_id") == record.get("producer_actor_id"):
                raise SchemaError("independent session review cannot be producer self-review")
            if record.get("reviewer_identity_locator") != _ACTOR_LOCATOR.format(
                actor_id=record.get("reviewer_actor_id")
            ) or record.get("producer_identity_locator") != _ACTOR_LOCATOR.format(
                actor_id=record.get("producer_actor_id")
            ):
                raise SchemaError("review actor identities do not match their persisted locators")
            if context.required_risk != "R2" or record.get("reviewed_at") != context.occurred_at:
                raise SchemaError("review publication risk or timestamp does not match the record")
        elif record_class == OWNER_SESSION_ACCEPTANCE_DECISION:
            if (
                record.get("acceptor_actor_id") != context.caller_actor_id
                or record.get("acceptor_actor_class") != context.caller_actor_class
                or record.get("authority_grant_id") != context.authority_grant_id
            ):
                raise SchemaError("owner-decision caller or authority does not match the record")
            if record.get("acceptor_identity_locator") != _ACTOR_LOCATOR.format(
                actor_id=record.get("acceptor_actor_id")
            ):
                raise SchemaError("owner actor identity does not match its persisted locator")
            if (
                context.caller_actor_class != "human"
                or context.required_risk != "R3"
                or record.get("decided_at") != context.occurred_at
                or record.get("outcome") != "accepted"
            ):
                raise SchemaError("owner acceptance publication requires exact human R3 acceptance")

    @staticmethod
    def _validate_record_semantics(
        record_class: str,
        record: Mapping[str, Any],
    ) -> None:
        if record_class == INDEPENDENT_SESSION_REVIEW:
            reviewer = record.get("reviewer_actor_id")
            producer = record.get("producer_actor_id")
            try:
                validate_id(reviewer, "actor")
                validate_id(producer, "actor")
                validate_id(record.get("authority_grant_id"), "authority_grant")
            except (AttributeError, TypeError, ValueError) as exc:
                raise SchemaError("independent review has invalid governed actor or grant identity") from exc
            if reviewer == producer:
                raise SchemaError("independent session review cannot be producer self-review")
            if record.get("reviewer_identity_locator") != _ACTOR_LOCATOR.format(actor_id=reviewer) or record.get(
                "producer_identity_locator"
            ) != _ACTOR_LOCATOR.format(actor_id=producer):
                raise SchemaError("review actor identities do not match their persisted locators")
        elif record_class == OWNER_SESSION_ACCEPTANCE_DECISION:
            acceptor = record.get("acceptor_actor_id")
            try:
                validate_id(acceptor, "actor")
                validate_id(record.get("authority_grant_id"), "authority_grant")
            except (AttributeError, TypeError, ValueError) as exc:
                raise SchemaError("owner decision has invalid governed actor or grant identity") from exc
            if record.get("acceptor_actor_class") != "human" or record.get(
                "acceptor_identity_locator"
            ) != _ACTOR_LOCATOR.format(actor_id=acceptor):
                raise SchemaError("owner actor identity does not match its persisted locator")

    def _authority_components(self):
        if self._authority_schemas is None or self._authority_resolver is None:
            self._authority_schemas = runtime_schema_registry(self.binding.schema_root)
            from research_system.authority import LedgerAuthorityGrantResolver

            self._authority_resolver = LedgerAuthorityGrantResolver(
                self.control_root,
                self.binding.project_id,
                self.binding.store_identity,
                self._authority_schemas,
                approved_witness=self.binding.origin_witness,
                approved_witness_path=self.binding.origin_witness_path,
            )
        return self._authority_schemas, self._authority_resolver

    def _policy_action(
        self,
        resolution: ExternalRecordResolution,
    ) -> tuple[dict[str, object], str, datetime]:
        record = resolution.record
        schemas, _ = self._authority_components()
        subject = record.get("subject")
        if not isinstance(subject, Mapping):
            raise SchemaError("governed session record has no exact subject")
        if resolution.record_class == INDEPENDENT_SESSION_REVIEW:
            schema_id = _REVIEW_POLICY_SCHEMA_ID
            action_type = PUBLISH_OWNER_OPERATED_SESSION_REVIEW
            actor_id = record["reviewer_actor_id"]
            actor_class = record["reviewer_actor_class"]
            authority_grant_id = record["authority_grant_id"]
            receipt_field = "review_receipt"
            receipt = compact_record_receipt(resolution)
            required_risk = "R2"
            occurred_at = _utc(record["reviewed_at"], "reviewed_at")
        elif resolution.record_class == OWNER_SESSION_ACCEPTANCE_DECISION:
            schema_id = _ACCEPTANCE_POLICY_SCHEMA_ID
            action_type = ACCEPT_OWNER_OPERATED_SESSION_EVIDENCE
            actor_id = record["acceptor_actor_id"]
            actor_class = record["acceptor_actor_class"]
            authority_grant_id = record["authority_grant_id"]
            receipt_field = "owner_decision_receipt"
            receipt = compact_record_receipt(resolution)
            required_risk = "R3"
            occurred_at = _utc(record["decided_at"], "decided_at")
        else:
            raise SchemaError("record is outside the governed WP6.4 session profile")
        identity = schemas.resolve_identity(schema_id, _POLICY_SCHEMA_VERSION)
        action: dict[str, object] = {
            "schema_id": schema_id,
            "schema_version": _POLICY_SCHEMA_VERSION,
            "policy_action_type": action_type,
            "policy_action_schema_sha256": identity.sha256,
            "project_id": self.binding.project_id,
            "actor_id": actor_id,
            "actor_class": actor_class,
            "authority_grant_id": authority_grant_id,
            "subject_scope": {
                "kind": "artefact",
                "id": subject["evidence_artifact_id"],
            },
            "evidence_subject_raw_sha256": subject["evidence_subject_raw_sha256"],
            receipt_field: receipt,
            "required_risk": required_risk,
        }
        if resolution.record_class == OWNER_SESSION_ACCEPTANCE_DECISION:
            action["review_receipt"] = record["review_receipt"]
        return action, required_risk, occurred_at

    def replay_record_authority(
        self,
        resolution: ExternalRecordResolution,
        *,
        resolved_at: datetime | None = None,
        expected_authority_root: str | None = None,
    ) -> tuple[dict[str, object], ScopedAuthorityGrantResolution, datetime]:
        """Re-resolve the exact record action from ledger authority."""

        if not isinstance(resolution, ExternalRecordResolution):
            raise TypeError("session-record authority replay requires a storage-derived resolution")
        self.catalogue.validate(resolution.record_class, resolution.record_id, resolution.record)
        self._validate_record_semantics(resolution.record_class, resolution.record)
        if resolution.revision != 1 or resolution.canonical_sha256 != sha256_hex(canonical_bytes(resolution.record)):
            raise IntegrityError("session-record storage receipt is not canonical revision 1")
        if resolved_at is None:
            try:
                resolved_at = self._clock()
            except Exception as exc:  # noqa: BLE001 - trusted clock failures must close the seam
                raise IntegrityError("trusted session-record authority clock failed") from exc
        now = _aware_utc(resolved_at, "session-record authority replay time")
        schemas, resolver = self._authority_components()
        administration = resolver.administration_context()
        if (
            administration.project_id != self.binding.project_id
            or administration.store_identity != self.binding.store_identity
            or (expected_authority_root is not None and expected_authority_root != administration.root_grant_id)
        ):
            raise ArsError("session-record publication authority root or store binding mismatch")
        action, required_risk, occurred_at = self._policy_action(resolution)
        schemas.validate_active(
            str(action["schema_id"]),
            action,
            schema_version=str(action["schema_version"]),
        )
        authority = resolver.resolve_policy_action(
            str(action["authority_grant_id"]),
            str(action["actor_id"]),
            str(action["actor_class"]),
            GrantedPolicyActionIdentity(
                str(action["policy_action_type"]),
                str(action["schema_id"]),
                str(action["schema_version"]),
                str(action["policy_action_schema_sha256"]),
            ),
            required_risk,
            self.binding.project_id,
            "artefact",
            str(action["subject_scope"]["id"]),
            now,
        )
        if occurred_at > now or not (authority.effective_at <= occurred_at < authority.expires_at):
            raise ArsError("session-record decision time is outside the replayed authority interval")
        return action, authority, now

    def _resolve_current_publication_authority(
        self,
        context: ExternalRecordPublicationContext,
        *,
        record: Mapping[str, Any],
    ) -> None:
        try:
            now = _aware_utc(self._clock(), "trusted session-record publication clock")
        except Exception as exc:
            if isinstance(exc, (IntegrityError, SchemaError)):
                raise
            raise IntegrityError("trusted session-record publication clock failed") from exc
        predicted = ExternalRecordResolution(
            record_class=context.record_class,
            record_id=context.record_id,
            revision=context.revision,
            canonical_sha256=sha256_hex(canonical_bytes(record)),
            record=dict(record),
        )
        self.replay_record_authority(
            predicted,
            resolved_at=now,
            expected_authority_root=context.authority_root,
        )

    def resolve(self, locator: SessionRecordLocator) -> ExternalRecordResolution:
        """Resolve one opaque locator with a storage-derived canonical receipt."""

        if not isinstance(locator, SessionRecordLocator):
            raise TypeError("session-record resolution requires a SessionRecordLocator")
        return self.resolve_from_storage(
            record_class=locator.record_class,
            record_id=locator.record_id,
        )

    def receipt_evidence(self, resolution: ExternalRecordResolution) -> dict[str, object]:
        row = self.catalogue.row(resolution.record_class)
        return {
            **compact_record_receipt(resolution),
            "schema_id": row.schema_id,
            "schema_version": row.schema_version,
            "schema_sha256": row.schema_canonical_sha256,
            "store_identity": self.binding.store_identity,
            "control_root": str(self.control_root),
        }


__all__ = [
    "ACCEPT_OWNER_OPERATED_SESSION_EVIDENCE",
    "INDEPENDENT_SESSION_REVIEW",
    "OWNER_SESSION_ACCEPTANCE_DECISION",
    "PUBLISH_OWNER_OPERATED_SESSION_REVIEW",
    "SessionEvidenceRecordStore",
    "SessionRecordLocator",
    "SessionRecordPublicationContext",
    "authority_replay_receipt",
    "compact_record_receipt",
]
