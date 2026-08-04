"""Governed publication of runner-owned relationship-evidence facts.

The assurance-pack runner consumes immutable facts from
``runtime/relationship-evidence-facts/<rel>/``.  This module is the narrow
production seam that publishes those files.  It does not write external
assurance records or create parties, grants, reviews, acceptances, or pack
candidates; publication authority is resolved against the already protected
``producer_relationship_evidence`` record.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from research_system.assurance.external_records import ExternalRecordPublicationContext
from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.authority import GrantedPolicyActionIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.ids import validate_id
from research_system.routing.independence import RelationshipEvidence, independence_grade
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.durability import fsync_directory
from research_system.store.identity import load_store_manifest, manifest_schema_root, verify_store_identity
from research_system.store.layout import (
    require_control_root_disjoint_from_code_roots,
    require_existing_control_root,
)
from research_system.store.lock import WriterLock


FACTS_ROOT = "relationship-evidence-facts"
FACTS_SCHEMA_ID = "ars://wp6-3-authority/relationship-evidence-facts/1.0"
_PUBLICATION_POLICY_ACTION = "publish_external_assurance_record"
_PUBLICATION_POLICY_ACTION_SCHEMA_ID = "ars://core/policy-action/PublishExternalAssuranceRecord"
_PUBLICATION_POLICY_ACTION_SCHEMA_VERSION = "1.0.0"
_CALLER_ACTOR_CLASSES = frozenset({"human", "agent", "service"})
_RFC3339_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FACT_ID = re.compile(r"^rel_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_STABLE_HANDOFF_OR_RUN_ID = re.compile(
    r"^(?:run|hnd)_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_OPERATOR_SESSION_ID = re.compile(r"^ses_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_REVISION_FILE = re.compile(r"^(?P<revision>[0-9]{8})-(?P<sha>[0-9a-f]{64})\.json$")


@dataclass(frozen=True)
class RelationshipEvidenceParticipant:
    actor_id: str
    task_id: str
    session_id: str
    operator_session_id: str
    context_hash: str
    model_family: str
    stable_handoff_or_run_id: str


@dataclass(frozen=True)
class ProtectedRelationshipReference:
    relationship_record_id: str
    revision: int
    canonical_sha256: str
    relationship_context: str
    grade: str
    effective_at: str
    expires_at: str


@dataclass(frozen=True)
class RelationshipEvidenceFactsReceipt:
    relationship_evidence_facts_id: str
    revision: int
    canonical_sha256: str
    schema_id: str
    schema_version: str
    caller_actor_id: str
    authority_grant_id: str
    record_action: str
    publication_context_sha256: str


class RelationshipEvidenceFactsStore:
    """Publish derived relationship facts through replay-backed authority."""

    def __init__(self, binding: ControlBinding, *, clock: Callable[[], datetime] | None = None) -> None:
        if not isinstance(binding, ControlBinding):
            raise TypeError("relationship-evidence facts require a validated ControlBinding")
        try:
            if binding.origin_witness is None:
                raise IntegrityError("control binding has no approved origin witness")
            code_roots = [root.resolve(strict=True) for root in binding.code_roots]
            control_root = require_existing_control_root(code_roots, binding.control_root)
            verify_store_identity(
                control_root,
                binding.project_id,
                binding.store_identity,
                code_roots,
                approved_witness=binding.origin_witness,
                approved_witness_path=binding.origin_witness_path,
            )
            require_control_root_disjoint_from_code_roots(code_roots, control_root)
            manifest_schema = manifest_schema_root(
                load_store_manifest(
                    control_root,
                    approved_witness=binding.origin_witness,
                    approved_witness_path=binding.origin_witness_path,
                )
            )
            if manifest_schema is not None and manifest_schema.resolve(strict=True) != binding.schema_root.resolve(
                strict=True
            ):
                raise IntegrityError("binding schema root differs from store manifest")
        except (OSError, KeyError, ValueError) as exc:
            raise IntegrityError("control binding is not valid for relationship-evidence facts") from exc
        self.binding = binding
        self.control_root = control_root
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._schema = self._load_schema()
        self._authority_schemas: SchemaRegistry | None = None
        self._authority_resolver: LedgerAuthorityGrantResolver | None = None

    def publish(
        self,
        *,
        relationship_evidence_facts_id: str,
        revision: int,
        expected_previous_revision: int,
        relationship_scope: str,
        protected_relationship: ProtectedRelationshipReference,
        reviewed_subject: Mapping[str, object],
        producer: RelationshipEvidenceParticipant,
        reviewer: RelationshipEvidenceParticipant,
        evidence_author_actor_id: str,
        producer_conclusions_visibility: str,
        reviewed_at: str,
        publication_context: ExternalRecordPublicationContext,
    ) -> RelationshipEvidenceFactsReceipt:
        """Derive facts, authorize publication in-lock, and persist by CAS."""

        self._validate_revision_numbers(revision, expected_previous_revision)
        protected_record = self._validate_protected_relationship(protected_relationship)
        self._validate_relationship_participants(protected_record, producer=producer, reviewer=reviewer)
        record = self._build_record(
            relationship_evidence_facts_id=relationship_evidence_facts_id,
            relationship_scope=relationship_scope,
            protected_relationship=protected_relationship,
            reviewed_subject=reviewed_subject,
            producer=producer,
            reviewer=reviewer,
            evidence_author_actor_id=evidence_author_actor_id,
            producer_conclusions_visibility=producer_conclusions_visibility,
            reviewed_at=reviewed_at,
        )
        self._validate_publication_context(
            context=publication_context,
            record=record,
            revision=revision,
            expected_previous_revision=expected_previous_revision,
        )
        published_at = self._trusted_now()
        self._validate_current_at_publication(record, published_at)
        with WriterLock(
            self.control_root / "runtime" / "writer.lock",
            {
                "operation": "relationship_evidence_facts_publication",
                "relationship_evidence_facts_id": relationship_evidence_facts_id,
                "protected_relationship_record_id": protected_relationship.relationship_record_id,
                "revision": str(revision),
                "session_id": publication_context.session_id,
                "record_action": publication_context.record_action,
                "authority_grant_id": publication_context.authority_grant_id,
                "canonical_sha256": publication_context.canonical_sha256,
            },
        ):
            self._resolve_current_publication_authority(publication_context, now=published_at)
            return self._write_storage(
                relationship_evidence_facts_id=relationship_evidence_facts_id,
                revision=revision,
                expected_previous_revision=expected_previous_revision,
                record=record,
                publication_context=publication_context,
            )

    def derive_record(
        self,
        *,
        relationship_evidence_facts_id: str,
        relationship_scope: str,
        protected_relationship: ProtectedRelationshipReference,
        reviewed_subject: Mapping[str, object],
        producer: RelationshipEvidenceParticipant,
        reviewer: RelationshipEvidenceParticipant,
        evidence_author_actor_id: str,
        producer_conclusions_visibility: str,
        reviewed_at: str,
    ) -> dict[str, object]:
        """Return the canonical facts body derived from concrete provenance inputs."""

        return self._build_record(
            relationship_evidence_facts_id=relationship_evidence_facts_id,
            relationship_scope=relationship_scope,
            protected_relationship=protected_relationship,
            reviewed_subject=reviewed_subject,
            producer=producer,
            reviewer=reviewer,
            evidence_author_actor_id=evidence_author_actor_id,
            producer_conclusions_visibility=producer_conclusions_visibility,
            reviewed_at=reviewed_at,
        )

    def _validate_protected_relationship(
        self,
        protected_relationship: ProtectedRelationshipReference,
    ) -> Mapping[str, object]:
        try:
            resolution = ControlStoreAuthorityResolver(self.binding).resolve_with_receipt(
                record_id=protected_relationship.relationship_record_id,
                record_class="producer_relationship_evidence",
                authority_root=self.binding.store_identity,
                phase="load",
            )
        except (ArsError, IntegrityError, SchemaError, ValueError, TypeError) as exc:
            raise SchemaError("protected relationship does not resolve exactly") from exc
        record = resolution.record
        if (
            resolution.revision != protected_relationship.revision
            or resolution.canonical_sha256 != protected_relationship.canonical_sha256
            or record.get("relationship_context") != protected_relationship.relationship_context
            or record.get("grade") != protected_relationship.grade
            or record.get("effective_at") != protected_relationship.effective_at
            or record.get("expires_at") != protected_relationship.expires_at
        ):
            raise SchemaError("protected relationship reference differs from the external record")
        return record

    @staticmethod
    def _validate_relationship_participants(
        protected_record: Mapping[str, object],
        *,
        producer: RelationshipEvidenceParticipant,
        reviewer: RelationshipEvidenceParticipant,
    ) -> None:
        if (
            protected_record.get("subject_actor_id") != reviewer.actor_id
            or protected_record.get("object_actor_id") != producer.actor_id
        ):
            raise SchemaError("protected relationship actors do not match supplied reviewer and producer")

    def _load_schema(self) -> Mapping[str, object]:
        path = self.binding.schema_root / "wp6-3-authority" / "relationship-evidence-facts.schema.json"
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise SchemaError("relationship-evidence-facts schema is invalid") from exc
        if schema.get("$id") != FACTS_SCHEMA_ID:
            raise SchemaError("relationship-evidence-facts schema identity is not accepted")
        return schema

    @staticmethod
    def _validate_revision_numbers(revision: int, expected_previous_revision: int) -> None:
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ConflictError("relationship-evidence-facts revision must be positive")
        if (
            isinstance(expected_previous_revision, bool)
            or not isinstance(expected_previous_revision, int)
            or expected_previous_revision < 0
        ):
            raise ConflictError("expected previous relationship-evidence-facts revision must be non-negative")
        if revision != expected_previous_revision + 1:
            raise ConflictError("relationship-evidence-facts revision must be the expected previous revision plus one")

    @staticmethod
    def _parse_utc(value: object, label: str) -> datetime:
        if not isinstance(value, str) or _RFC3339_UTC.fullmatch(value) is None:
            raise SchemaError(f"{label} must be strict RFC3339 UTC")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SchemaError(f"{label} is not a valid timestamp") from exc
        if parsed.tzinfo != timezone.utc:
            raise SchemaError(f"{label} must be UTC")
        return parsed

    def _trusted_now(self) -> datetime:
        try:
            authority_time = self._clock()
        except Exception as exc:  # noqa: BLE001 - a failed trusted clock must fail closed
            raise IntegrityError("trusted relationship-evidence-facts clock failed") from exc
        if (
            not isinstance(authority_time, datetime)
            or authority_time.tzinfo is None
            or authority_time.utcoffset() is None
        ):
            raise IntegrityError("trusted relationship-evidence-facts clock must return a timezone-aware datetime")
        return authority_time.astimezone(timezone.utc)

    @staticmethod
    def _validate_participant(value: RelationshipEvidenceParticipant, label: str) -> None:
        if not isinstance(value, RelationshipEvidenceParticipant):
            raise SchemaError(f"{label} participant provenance is required")
        try:
            validate_id(value.actor_id, "actor")
            validate_id(value.task_id, "task")
            validate_id(value.session_id, "context")
        except ValueError as exc:
            raise SchemaError(f"{label} participant identity is malformed") from exc
        if _OPERATOR_SESSION_ID.fullmatch(value.operator_session_id) is None:
            raise SchemaError(f"{label} operator session id is malformed")
        if not _SHA256.fullmatch(value.context_hash):
            raise SchemaError(f"{label} context hash is not a lowercase SHA-256")
        if not isinstance(value.model_family, str) or not value.model_family:
            raise SchemaError(f"{label} model family is required")
        if _STABLE_HANDOFF_OR_RUN_ID.fullmatch(value.stable_handoff_or_run_id) is None:
            raise SchemaError(f"{label} stable handoff/run id is malformed")

    def _build_record(
        self,
        *,
        relationship_evidence_facts_id: str,
        relationship_scope: str,
        protected_relationship: ProtectedRelationshipReference,
        reviewed_subject: Mapping[str, object],
        producer: RelationshipEvidenceParticipant,
        reviewer: RelationshipEvidenceParticipant,
        evidence_author_actor_id: str,
        producer_conclusions_visibility: str,
        reviewed_at: str,
    ) -> dict[str, object]:
        try:
            validate_id(relationship_evidence_facts_id, "producer_relationship_evidence")
            validate_id(protected_relationship.relationship_record_id, "producer_relationship_evidence")
            validate_id(evidence_author_actor_id, "actor")
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError("relationship-evidence-facts identities are malformed") from exc
        if relationship_evidence_facts_id != protected_relationship.relationship_record_id:
            raise SchemaError("relationship-evidence-facts id must equal the protected relationship id")
        if relationship_scope not in {"requirement_scope", "pack_review"}:
            raise SchemaError("relationship-evidence-facts scope is not accepted")
        if relationship_scope == "requirement_scope" and protected_relationship.relationship_context != (
            "requirement_scope_review"
        ):
            raise SchemaError("requirement-scope facts must protect the requirement-scope relationship")
        if (
            relationship_scope == "pack_review"
            and protected_relationship.relationship_context != "pack_scientific_review"
        ):
            raise SchemaError("pack-review facts must protect the pack-review relationship")
        if isinstance(protected_relationship.revision, bool) or protected_relationship.revision < 1:
            raise SchemaError("protected relationship revision must be positive")
        if not _SHA256.fullmatch(protected_relationship.canonical_sha256):
            raise SchemaError("protected relationship canonical hash is not a lowercase SHA-256")
        if protected_relationship.grade not in {"I2", "I3"}:
            raise SchemaError("protected relationship grade must be I2 or I3")
        self._validate_participant(producer, "producer")
        self._validate_participant(reviewer, "reviewer")
        if evidence_author_actor_id != reviewer.actor_id:
            raise SchemaError("relationship-evidence-facts author must be the reviewer actor")
        if producer.task_id == reviewer.task_id:
            raise SchemaError("relationship-evidence-facts require separate task provenance")
        if producer_conclusions_visibility not in {"hidden_from_reviewer", "visible_to_reviewer"}:
            raise SchemaError("producer conclusions visibility is not accepted")
        if not isinstance(reviewed_subject, Mapping):
            raise SchemaError("reviewed subject must be an object")
        reviewed_time = self._parse_utc(reviewed_at, "relationship-evidence-facts reviewed_at")
        effective_at = self._parse_utc(protected_relationship.effective_at, "protected relationship effective_at")
        expires_at = self._parse_utc(protected_relationship.expires_at, "protected relationship expires_at")
        if not effective_at <= reviewed_time < expires_at:
            raise SchemaError("relationship-evidence-facts timing is outside protected relationship validity")

        comparisons = {
            "same_actor": producer.actor_id == reviewer.actor_id,
            "same_session": producer.operator_session_id == reviewer.operator_session_id,
            "same_context_hash": producer.context_hash == reviewer.context_hash,
            "same_model_family": producer.model_family == reviewer.model_family,
            "producer_conclusions_visible": producer_conclusions_visibility == "visible_to_reviewer",
        }
        grade = independence_grade(RelationshipEvidence(**comparisons))
        if grade != "I2":
            raise SchemaError("relationship-evidence-facts independence grade is below I2")
        record = {
            "record_type": "relationship_evidence_facts",
            "relationship_evidence_facts_id": relationship_evidence_facts_id,
            "relationship_scope": relationship_scope,
            "protected_relationship": {
                "relationship_record_id": protected_relationship.relationship_record_id,
                "revision": protected_relationship.revision,
                "canonical_sha256": protected_relationship.canonical_sha256,
                "relationship_context": protected_relationship.relationship_context,
                "grade": protected_relationship.grade,
                "effective_at": protected_relationship.effective_at,
                "expires_at": protected_relationship.expires_at,
            },
            "reviewed_subject": dict(reviewed_subject),
            "producer": asdict(producer),
            "reviewer": asdict(reviewer),
            "evidence_author_actor_id": evidence_author_actor_id,
            "producer_conclusions_visibility": producer_conclusions_visibility,
            "derived_comparisons": comparisons,
            "independence_grade": grade,
            "review_state": "completed",
            "reviewed_at": reviewed_at,
        }
        errors = sorted(
            Draft202012Validator(self._schema, format_checker=FormatChecker()).iter_errors(record),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            raise SchemaError(f"relationship-evidence-facts schema validation failed: {errors[0].message}")
        return record

    def _validate_current_at_publication(self, record: Mapping[str, object], published_at: datetime) -> None:
        protected = record.get("protected_relationship")
        if not isinstance(protected, Mapping):
            raise SchemaError("protected relationship is malformed")
        reviewed_at = self._parse_utc(record.get("reviewed_at"), "relationship-evidence-facts reviewed_at")
        expires_at = self._parse_utc(protected.get("expires_at"), "protected relationship expires_at")
        if not reviewed_at <= published_at < expires_at:
            raise SchemaError("relationship-evidence-facts are not current at trusted publication time")

    @staticmethod
    def _validate_context_id(value: object, kind: str, label: str) -> str:
        try:
            return validate_id(str(value), kind)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError(f"publication context {label} is not a valid {kind} id") from exc

    def _validate_publication_context(
        self,
        *,
        context: ExternalRecordPublicationContext,
        record: Mapping[str, object],
        revision: int,
        expected_previous_revision: int,
    ) -> None:
        if not isinstance(context, ExternalRecordPublicationContext):
            raise SchemaError("relationship-evidence-facts publication context is required")
        protected = record["protected_relationship"]
        if not isinstance(protected, Mapping):
            raise SchemaError("protected relationship is malformed")
        protected_id = str(protected["relationship_record_id"])
        expected_action = "create" if revision == 1 and expected_previous_revision == 0 else "revise"
        if context.record_class != "producer_relationship_evidence":
            raise SchemaError("facts publication must be scoped to producer_relationship_evidence")
        if context.record_id != protected_id or context.relationship_record_id != protected_id:
            raise SchemaError("facts publication context does not match the protected relationship")
        if context.revision != revision or context.expected_previous_revision != expected_previous_revision:
            raise SchemaError("facts publication context revision does not match the request")
        if context.record_action != expected_action:
            raise SchemaError("facts publication context record action does not match revision")
        if context.project_id != self.binding.project_id:
            raise SchemaError("facts publication context project does not match the bound project")
        if context.store_identity != self.binding.store_identity:
            raise SchemaError("facts publication context store identity does not match the bound store")
        if context.canonical_sha256 != sha256_hex(canonical_bytes(record)):
            raise SchemaError("facts publication context canonical body hash does not match the record")
        if context.caller_actor_id != record.get("evidence_author_actor_id"):
            raise SchemaError("facts publication caller is not the evidence author")
        reviewer = record.get("reviewer")
        if not isinstance(reviewer, Mapping):
            raise SchemaError("relationship-evidence-facts reviewer provenance is malformed")
        if context.task_id != reviewer.get("task_id") or context.session_id != reviewer.get("session_id"):
            raise SchemaError("facts publication context does not match reviewer provenance")
        self._validate_context_id(context.caller_actor_id, "actor", "caller actor")
        if context.caller_actor_class not in _CALLER_ACTOR_CLASSES:
            raise SchemaError("facts publication caller actor class is not accepted")
        self._validate_context_id(context.authority_grant_id, "authority_grant", "authority grant")
        self._validate_context_id(context.authority_root, "authority_grant", "authority root")
        self._validate_context_id(context.task_id, "task", "task")
        self._validate_context_id(context.session_id, "context", "session")
        if context.required_risk not in {"R0", "R1", "R2", "R3"}:
            raise SchemaError("facts publication risk must be R0 through R3")
        self._parse_utc(context.occurred_at, "facts publication context occurred_at")

    @staticmethod
    def _publication_action_payload(context: ExternalRecordPublicationContext) -> dict[str, Any]:
        return {
            "schema_id": _PUBLICATION_POLICY_ACTION_SCHEMA_ID,
            "schema_version": _PUBLICATION_POLICY_ACTION_SCHEMA_VERSION,
            "policy_action_type": _PUBLICATION_POLICY_ACTION,
            "project_id": context.project_id,
            "actor_id": context.caller_actor_id,
            "actor_class": context.caller_actor_class,
            "authority_grant_id": context.authority_grant_id,
            "subject_scope": {
                "kind": "external_assurance_record",
                "id": context.record_id,
            },
            "record_class": context.record_class,
            "record_id": context.record_id,
            "record_action": context.record_action,
            "revision": context.revision,
            "expected_previous_revision": context.expected_previous_revision,
            "store_identity": context.store_identity,
            "authority_root": context.authority_root,
            "task_id": context.task_id,
            "session_id": context.session_id,
            "relationship_record_id": context.relationship_record_id,
            "required_risk": context.required_risk,
            "canonical_sha256": context.canonical_sha256,
            "occurred_at": context.occurred_at,
        }

    def _resolve_current_publication_authority(
        self,
        context: ExternalRecordPublicationContext,
        *,
        now: datetime,
    ) -> None:
        if self._authority_schemas is None or self._authority_resolver is None:
            self._authority_schemas = runtime_schema_registry(self.binding.schema_root)
            self._authority_resolver = LedgerAuthorityGrantResolver(
                self.control_root,
                self.binding.project_id,
                self.binding.store_identity,
                self._authority_schemas,
                approved_witness=self.binding.origin_witness,
                approved_witness_path=self.binding.origin_witness_path,
            )
        action = self._publication_action_payload(context)
        self._authority_schemas.validate_active(
            _PUBLICATION_POLICY_ACTION_SCHEMA_ID,
            action,
            schema_version=_PUBLICATION_POLICY_ACTION_SCHEMA_VERSION,
        )
        administration = self._authority_resolver.administration_context()
        if (
            administration.project_id != self.binding.project_id
            or administration.store_identity != self.binding.store_identity
            or context.authority_root != administration.root_grant_id
        ):
            raise ArsError("facts publication authority root or store binding mismatch")
        policy = self._authority_schemas.resolve_identity(
            _PUBLICATION_POLICY_ACTION_SCHEMA_ID,
            _PUBLICATION_POLICY_ACTION_SCHEMA_VERSION,
        )
        self._authority_resolver.resolve_policy_action(
            context.authority_grant_id,
            context.caller_actor_id,
            context.caller_actor_class,
            GrantedPolicyActionIdentity(
                _PUBLICATION_POLICY_ACTION,
                policy.schema_id,
                policy.schema_version,
                policy.sha256,
            ),
            context.required_risk,
            context.project_id,
            "external_assurance_record",
            context.record_id,
            now,
        )

    def _validated_history(self, relationship_evidence_facts_id: str) -> dict[int, Mapping[str, object]]:
        directory = self.control_root / "runtime" / FACTS_ROOT / relationship_evidence_facts_id
        try:
            paths = sorted(directory.glob("*.json"))
        except OSError as exc:
            raise IntegrityError("relationship-evidence-facts history is unreadable") from exc
        history: dict[int, Mapping[str, object]] = {}
        for path in paths:
            match = _REVISION_FILE.fullmatch(path.name)
            if match is None:
                raise IntegrityError("relationship-evidence-facts revision filename is malformed")
            revision = int(match.group("revision"))
            if revision in history:
                raise IntegrityError("relationship-evidence-facts revision history is ambiguous")
            try:
                raw = path.read_bytes()
                value = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntegrityError("relationship-evidence-facts revision is unreadable") from exc
            if canonical_bytes(value) != raw:
                raise IntegrityError("relationship-evidence-facts revision is not canonical")
            if match.group("sha") != sha256_hex(raw):
                raise IntegrityError("relationship-evidence-facts filename hash mismatch")
            if not isinstance(value, Mapping):
                raise IntegrityError("relationship-evidence-facts revision is not an object")
            errors = sorted(
                Draft202012Validator(self._schema, format_checker=FormatChecker()).iter_errors(value),
                key=lambda error: list(error.absolute_path),
            )
            if errors:
                raise IntegrityError("relationship-evidence-facts history fails schema validation")
            if value.get("relationship_evidence_facts_id") != relationship_evidence_facts_id:
                raise IntegrityError("relationship-evidence-facts history contains a foreign identity")
            history[revision] = value
        if history and set(history) != set(range(1, max(history) + 1)):
            raise IntegrityError("relationship-evidence-facts revision history is not contiguous")
        return history

    def _write_storage(
        self,
        *,
        relationship_evidence_facts_id: str,
        revision: int,
        expected_previous_revision: int,
        record: Mapping[str, object],
        publication_context: ExternalRecordPublicationContext,
    ) -> RelationshipEvidenceFactsReceipt:
        if _FACT_ID.fullmatch(relationship_evidence_facts_id) is None:
            raise SchemaError("relationship-evidence-facts id is not a relationship identity")
        history = self._validated_history(relationship_evidence_facts_id)
        latest = max(history) if history else None
        observed = 0 if latest is None else latest
        if latest == revision:
            if history[revision] == dict(record):
                return self._receipt(relationship_evidence_facts_id, revision, record, publication_context)
            raise ConflictError("relationship-evidence-facts revision already exists with different content")
        if observed != expected_previous_revision:
            raise ConflictError(
                "expected previous relationship-evidence-facts revision "
                f"{expected_previous_revision}, observed {observed}"
            )
        data = canonical_bytes(record)
        directory = self.control_root / "runtime" / FACTS_ROOT / relationship_evidence_facts_id
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise IntegrityError("relationship-evidence-facts directory could not be created") from exc
        path = directory / f"{revision:08d}-{sha256_hex(data)}.json"
        temporary = directory / f".{path.name}.{secrets.token_hex(16)}.tmp"
        failure: BaseException | None = None
        try:
            try:
                descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                if path.exists():
                    if path.read_bytes() != data:
                        raise ConflictError("relationship-evidence-facts publication conflicts with existing bytes")
                    return self._receipt(relationship_evidence_facts_id, revision, record, publication_context)
                try:
                    os.link(temporary, path)
                except FileExistsError:
                    if path.read_bytes() != data:
                        raise ConflictError("relationship-evidence-facts publication conflicts with existing bytes")
                else:
                    fsync_directory(directory)
                if path.read_bytes() != data:
                    raise IntegrityError("relationship-evidence-facts publication could not be verified")
            except (ConflictError, IntegrityError):
                raise
            except OSError as exc:
                raise IntegrityError("relationship-evidence-facts publication failed") from exc
        except BaseException as exc:
            failure = exc
            raise
        finally:
            try:
                temporary.unlink(missing_ok=True)
                fsync_directory(directory)
            except OSError as exc:
                if failure is None:
                    raise IntegrityError("relationship-evidence-facts temporary cleanup failed") from exc
        return self._receipt(relationship_evidence_facts_id, revision, record, publication_context)

    @staticmethod
    def _receipt(
        relationship_evidence_facts_id: str,
        revision: int,
        record: Mapping[str, object],
        publication_context: ExternalRecordPublicationContext,
    ) -> RelationshipEvidenceFactsReceipt:
        return RelationshipEvidenceFactsReceipt(
            relationship_evidence_facts_id=relationship_evidence_facts_id,
            revision=revision,
            canonical_sha256=sha256_hex(canonical_bytes(record)),
            schema_id=FACTS_SCHEMA_ID,
            schema_version="1.0.0",
            caller_actor_id=publication_context.caller_actor_id,
            authority_grant_id=publication_context.authority_grant_id,
            record_action=publication_context.record_action,
            publication_context_sha256=sha256_hex(canonical_bytes(asdict(publication_context))),
        )
