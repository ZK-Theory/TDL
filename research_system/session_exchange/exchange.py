"""Immutable brief-out and evidence-back documents for owner-operated sessions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError as JsonSchemaError
from jsonschema.exceptions import ValidationError

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, SchemaError
from research_system.evidence.consumers import ArtefactConsumerContext, ArtefactEvidenceConsumers
from research_system.ids import validate_id
from research_system.session_exchange.authority import (
    INDEPENDENT_SESSION_REVIEW,
    OWNER_SESSION_ACCEPTANCE_DECISION,
    SessionEvidenceRecordStore,
    SessionRecordLocator,
    authority_replay_receipt,
    compact_record_receipt,
)
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore

_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / ".research-system" / "schemas" / "wp6-4"
_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")
_EVIDENCE_CORE_FIELDS = (
    "schema_id",
    "schema_version",
    "document_type",
    "mechanics_scope",
    "provider_control",
    "evidence_artifact_id",
    "handoff_id",
    "session_id",
    "attempt_id",
    "task_id",
    "brief_subject",
    "producer_identity_locator",
    "producer_verdict",
    "returned_artifacts",
    "test_evidence",
    "unresolved_findings",
)


@dataclass(frozen=True)
class PublishedSessionDocument:
    """One exact immutable document revision and its raw-byte identity."""

    path: Path
    raw_sha256: str
    document: dict[str, Any]


@dataclass(frozen=True)
class EvidenceArtifact:
    """Caller-supplied artifact bytes and the identities ARS must retain."""

    artefact_id: str
    locator: str
    path: Path
    media_type: str


@dataclass(frozen=True)
class UnresolvedFinding:
    """One finding that remains unresolved when evidence is returned."""

    finding_id: str
    severity: str
    summary: str


def _validate_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise SchemaError(f"{label} must be strict RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise SchemaError(f"{label} must be UTC")
    return parsed


def _validate_document(document: dict[str, Any], schema_name: str) -> None:
    schema_path = _SCHEMA_ROOT / schema_name
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, JsonSchemaError, ValidationError) as exc:
        raise SchemaError(f"invalid WP6.4 session document: {schema_name}") from exc


def prepare_session_brief(
    control_root: Path,
    *,
    brief_artifact_id: str,
    handoff_id: str,
    session_id: str,
    attempt_id: str,
    task_id: str,
    requested_role: str,
    assurance_requirement: str,
    operator_identity_locator: str,
    producer_identity_locator: str,
    session_family: str,
    git_commit_sha: str,
    git_tree_sha: str,
    brief_bytes: bytes,
    prepared_at: str,
) -> PublishedSessionDocument:
    """Prepare one immutable, provider-free owner-operated session brief.

    The caller supplies all identities and the exact UTF-8 brief bytes. This
    seam records them; it does not mint parties, invoke a provider, or handle
    credentials.
    """
    if not isinstance(brief_bytes, bytes) or not brief_bytes:
        raise SchemaError("brief bytes must be non-empty bytes")
    if brief_bytes.startswith(b"\xef\xbb\xbf"):
        raise SchemaError("brief bytes must be BOM-free UTF-8")
    try:
        brief_text = brief_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SchemaError("brief bytes must be UTF-8") from exc
    _validate_utc(prepared_at, "prepared_at")
    document: dict[str, Any] = {
        "schema_id": "ars://wp6-4/owner-operated-session-brief",
        "schema_version": "1.0.0",
        "document_type": "owner_operated_session_brief",
        "document_state": "prepared_for_owner_operated_session",
        "mechanics_scope": "fixture_or_operator_supplied_inputs_only",
        "provider_control": "owner_operated_no_ars_transport",
        "brief_artifact_id": brief_artifact_id,
        "revision": 1,
        "handoff_id": handoff_id,
        "session_id": session_id,
        "attempt_id": attempt_id,
        "task_id": task_id,
        "requested_role": requested_role,
        "assurance_requirement": assurance_requirement,
        "operator_identity_locator": operator_identity_locator,
        "producer_identity_locator": producer_identity_locator,
        "session_family": session_family,
        "git_subject": {"commit_sha": git_commit_sha, "tree_sha": git_tree_sha},
        "brief": {
            "media_type": "text/plain; charset=utf-8",
            "body_text": brief_text,
            "raw_sha256": sha256_hex(brief_bytes),
            "byte_length": len(brief_bytes),
        },
        "prepared_at": prepared_at,
    }
    _validate_document(document, "owner-operated-session-brief.schema.json")
    path = ObjectStore(control_root).write("artefact", brief_artifact_id, 1, document)
    raw = path.read_bytes()
    return PublishedSessionDocument(path=path, raw_sha256=sha256_hex(raw), document=document)


def _artifact_evidence(source: EvidenceArtifact) -> dict[str, Any]:
    validate_id(source.artefact_id, "artefact")
    try:
        raw = Path(source.path).read_bytes()
    except OSError as exc:
        raise SchemaError(f"evidence artifact is unreadable: {source.locator}") from exc
    if not raw:
        raise SchemaError(f"evidence artifact is empty: {source.locator}")
    return {
        "artefact_id": source.artefact_id,
        "locator": source.locator,
        "media_type": source.media_type,
        "raw_sha256": sha256_hex(raw),
        "byte_length": len(raw),
    }


def _artifact_evidence_set(sources: tuple[EvidenceArtifact, ...], label: str) -> list[dict[str, Any]]:
    if not sources:
        raise SchemaError(f"{label} must not be empty")
    evidence = [_artifact_evidence(source) for source in sources]
    ids = [item["artefact_id"] for item in evidence]
    locators = [item["locator"] for item in evidence]
    if len(ids) != len(set(ids)) or len(locators) != len(set(locators)):
        raise SchemaError(f"{label} identities must be unique")
    return evidence


def _trusted_session_store(
    binding: ControlBinding | None,
    control_root: Path,
) -> SessionEvidenceRecordStore:
    if not isinstance(binding, ControlBinding):
        raise SchemaError("later evidence revisions require a verified ControlBinding")
    store = SessionEvidenceRecordStore(binding)
    try:
        evidence_root = Path(control_root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SchemaError("session evidence control root is unavailable") from exc
    if store.control_root != evidence_root:
        raise ConflictError("session records and evidence must use the same bound control store")
    return store


def _evidence_core(document: dict[str, Any]) -> dict[str, Any]:
    return {field: document[field] for field in _EVIDENCE_CORE_FIELDS}


def _evidence_subject_raw_sha256(document: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(_evidence_core(document)))


def _evidence_revision_history(store: ObjectStore, evidence_artifact_id: str) -> dict[int, dict[str, Any]]:
    latest = store.latest_revision("artefact", evidence_artifact_id)
    if latest is None:
        return {}
    history: dict[int, dict[str, Any]] = {}
    for revision in range(1, latest + 1):
        document = store.read("artefact", evidence_artifact_id, revision)
        if not isinstance(document, dict):
            raise SchemaError("session evidence revision must be an object")
        _validate_document(document, "owner-operated-session-evidence.schema.json")
        if document.get("evidence_artifact_id") != evidence_artifact_id or document.get("revision") != revision:
            raise ConflictError("session evidence revision history contains a foreign identity")
        history[revision] = document
    return history


def _validate_expected_previous_revision(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 2:
        raise ConflictError("expected_previous_revision must be 0, 1, or 2")


def _session_subject(
    brief: dict[str, Any],
    brief_raw: bytes,
    evidence_artifact_id: str,
    evidence_subject_raw_sha256: str,
) -> dict[str, Any]:
    return {
        "handoff_id": brief["handoff_id"],
        "session_id": brief["session_id"],
        "attempt_id": brief["attempt_id"],
        "task_id": brief["task_id"],
        "brief_artifact_id": brief["brief_artifact_id"],
        "brief_revision": brief["revision"],
        "brief_document_raw_sha256": sha256_hex(brief_raw),
        "brief_raw_sha256": brief["brief"]["raw_sha256"],
        "evidence_artifact_id": evidence_artifact_id,
        "evidence_revision": 1,
        "evidence_subject_raw_sha256": evidence_subject_raw_sha256,
        "git_subject": brief["git_subject"],
    }


def _resolve_independent_review(
    store: SessionEvidenceRecordStore,
    locator: SessionRecordLocator,
    *,
    expected_subject: dict[str, Any],
    reviewer_identity_locator: str,
    producer_identity_locator: str,
    prepared_time: datetime,
    recorded_time: datetime,
    authority_resolution_time: datetime | None = None,
):
    if locator.record_class != INDEPENDENT_SESSION_REVIEW:
        raise SchemaError("independent review locator names the wrong trusted record class")
    resolution = store.resolve(locator)
    record = resolution.record
    if record["subject"] != expected_subject:
        raise ConflictError("independent review record does not bind the exact session subject")
    if record["reviewer_identity_locator"] != reviewer_identity_locator:
        raise ConflictError("independent review record names the wrong reviewer")
    if record["producer_identity_locator"] != producer_identity_locator:
        raise ConflictError("independent review record names the wrong producer")
    if record["reviewer_identity_locator"] != f"ars://actors/{record['reviewer_actor_id']}":
        raise ConflictError("independent review record does not bind its governed reviewer actor")
    if record["producer_identity_locator"] != f"ars://actors/{record['producer_actor_id']}":
        raise ConflictError("independent review record does not bind its producer actor")
    if record["reviewer_actor_id"] == record["producer_actor_id"]:
        raise SchemaError("independent review cannot be producer self-review")
    reviewed_at = _validate_utc(str(record["reviewed_at"]), "independent review reviewed_at")
    if reviewed_at < prepared_time:
        raise SchemaError("independent review evidence is stale for the prepared session subject")
    if reviewed_at > recorded_time:
        raise SchemaError("independent review evidence is from the future")
    action, authority, resolved_at = store.replay_record_authority(
        resolution,
        resolved_at=authority_resolution_time,
    )
    return (
        {
            "reviewer_identity_locator": reviewer_identity_locator,
            "status": "independent_review_recorded",
            "verdict": record["verdict"],
            "reviewed_at": record["reviewed_at"],
            "evidence": {
                "record": store.receipt_evidence(resolution),
                "authority": authority_replay_receipt(action, authority, resolved_at),
            },
        },
        resolution,
        reviewed_at,
    )


def _resolve_owner_acceptance(
    store: SessionEvidenceRecordStore,
    locator: SessionRecordLocator,
    *,
    acceptor_identity_locator: str,
    expected_subject: dict[str, Any],
    review_resolution,
    review_time: datetime,
    recorded_time: datetime,
    authority_resolution_time: datetime | None = None,
) -> dict[str, Any]:
    if locator.record_class != OWNER_SESSION_ACCEPTANCE_DECISION:
        raise SchemaError("owner decision locator names the wrong trusted record class")
    decision = store.resolve(locator)
    record = decision.record
    if record["subject"] != expected_subject:
        raise ConflictError("owner acceptance decision does not bind the exact session subject")
    if record["acceptor_identity_locator"] != acceptor_identity_locator:
        raise ConflictError("owner acceptance decision names the wrong acceptor")
    if record["review_receipt"] != compact_record_receipt(review_resolution):
        raise ConflictError("owner acceptance decision does not bind the exact review receipt")
    if record["acceptor_identity_locator"] != f"ars://actors/{record['acceptor_actor_id']}":
        raise ConflictError("owner acceptance decision does not bind its governed owner actor")
    if record["outcome"] != "accepted":
        raise SchemaError("owner acceptance decision does not accept the session subject")
    decided_at = _validate_utc(str(record["decided_at"]), "owner acceptance decided_at")
    if decided_at <= review_time:
        raise SchemaError("owner acceptance decision must be later than the independent review")
    if decided_at > recorded_time:
        raise SchemaError("owner acceptance decision is from the future")
    action, authority, resolved_at = store.replay_record_authority(
        decision,
        resolved_at=authority_resolution_time,
    )
    replay = authority_replay_receipt(action, authority, resolved_at)
    return {
        "acceptor_identity_locator": acceptor_identity_locator,
        "authority_grant_id": record["authority_grant_id"],
        "authority_status": "active",
        "status": "owner_acceptance_recorded",
        "outcome": "accepted",
        "decided_at": record["decided_at"],
        "authority_effective_at": replay["effective_at"],
        "authority_expires_at": replay["expires_at"],
        "evidence": {
            "decision": store.receipt_evidence(decision),
            "authority": replay,
        },
    }


def record_session_evidence(
    control_root: Path,
    *,
    expected_previous_revision: int,
    evidence_artifact_id: str,
    brief_artifact_id: str,
    handoff_id: str,
    session_id: str,
    attempt_id: str,
    producer_identity_locator: str,
    reviewer_identity_locator: str,
    acceptor_identity_locator: str,
    returned_artifacts: tuple[EvidenceArtifact, ...],
    test_evidence: tuple[EvidenceArtifact, ...],
    producer_verdict: str,
    unresolved_findings: tuple[UnresolvedFinding, ...],
    recorded_at: str,
    artefact_consumers: ArtefactEvidenceConsumers,
    brief_use_context: ArtefactConsumerContext,
    authority_binding: ControlBinding | None = None,
    review_record: SessionRecordLocator | None = None,
    owner_decision_record: SessionRecordLocator | None = None,
) -> PublishedSessionDocument:
    """Record exact returned bytes and resolve later states from trusted authority."""
    _validate_expected_previous_revision(expected_previous_revision)
    if review_record is not None and not isinstance(review_record, SessionRecordLocator):
        raise SchemaError("independent review must use an opaque trusted record locator")
    if owner_decision_record is not None and not isinstance(owner_decision_record, SessionRecordLocator):
        raise SchemaError("owner acceptance must use an opaque trusted decision locator")
    if review_record is None:
        if owner_decision_record is not None:
            raise SchemaError("owner acceptance requires a trusted independent review locator")
        target_revision = 1
    elif owner_decision_record is None:
        target_revision = 2
    else:
        target_revision = 3
    if target_revision != expected_previous_revision + 1:
        raise ConflictError("session evidence must advance exactly one immutable revision")
    recorded_time = _validate_utc(recorded_at, "recorded_at")
    if len({producer_identity_locator, reviewer_identity_locator, acceptor_identity_locator}) != 3:
        raise SchemaError("producer, reviewer, and acceptor identity locators must be distinct")
    store = ObjectStore(control_root)
    if brief_use_context.artefact_id != brief_artifact_id:
        raise ConflictError("brief authority context names a different artefact")
    try:
        resolved_brief = artefact_consumers.resolve_for_review(
            brief_use_context,
            consumer_id="rm04_followup_review",
        )
        brief = json.loads(resolved_brief.content_bytes)
    except (ArsError, AttributeError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaError("prepared session brief authority resolution failed") from exc
    if not isinstance(brief, dict):
        raise SchemaError("prepared session brief must be an object")
    if canonical_bytes(brief) != resolved_brief.content_bytes:
        raise SchemaError("prepared session brief bytes must be canonical JSON")
    _validate_document(brief, "owner-operated-session-brief.schema.json")
    expected_join = {
        "handoff_id": handoff_id,
        "session_id": session_id,
        "attempt_id": attempt_id,
        "producer_identity_locator": producer_identity_locator,
    }
    mismatches = [field for field, expected in expected_join.items() if brief.get(field) != expected]
    if mismatches:
        raise ConflictError(f"evidence does not bind the prepared brief: {', '.join(mismatches)}")
    brief_raw = canonical_bytes(brief)
    prepared_time = _validate_utc(brief["prepared_at"], "brief prepared_at")
    if recorded_time < prepared_time:
        raise SchemaError("recorded_at cannot precede the prepared session brief")
    artifacts = _artifact_evidence_set(returned_artifacts, "returned artifacts")
    tests = _artifact_evidence_set(test_evidence, "test evidence")
    combined_ids = [item["artefact_id"] for item in artifacts + tests]
    combined_locators = [item["locator"] for item in artifacts + tests]
    if len(combined_ids) != len(set(combined_ids)) or len(combined_locators) != len(set(combined_locators)):
        raise SchemaError("returned artifact and test evidence identities must be disjoint")
    validate_id(evidence_artifact_id, "artefact")
    document_ids = {brief_artifact_id, evidence_artifact_id}
    if len(document_ids) != 2 or document_ids.intersection(combined_ids):
        raise SchemaError("document and returned evidence identities must be disjoint")
    findings = [
        {
            "finding_id": finding.finding_id,
            "severity": finding.severity,
            "status": "unresolved",
            "summary": finding.summary,
        }
        for finding in unresolved_findings
    ]
    finding_ids = [finding["finding_id"] for finding in findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise SchemaError("unresolved finding identities must be unique")
    brief_subject = {
        "brief_artifact_id": brief_artifact_id,
        "revision": 1,
        "document_raw_sha256": sha256_hex(brief_raw),
        "brief_raw_sha256": brief["brief"]["raw_sha256"],
        "git_subject": brief["git_subject"],
    }
    evidence_core: dict[str, Any] = {
        "schema_id": "ars://wp6-4/owner-operated-session-evidence",
        "schema_version": "1.0.0",
        "document_type": "owner_operated_session_evidence",
        "mechanics_scope": "fixture_or_operator_supplied_inputs_only",
        "provider_control": "owner_operated_no_ars_transport",
        "evidence_artifact_id": evidence_artifact_id,
        "handoff_id": handoff_id,
        "session_id": session_id,
        "attempt_id": attempt_id,
        "task_id": brief["task_id"],
        "brief_subject": brief_subject,
        "producer_identity_locator": producer_identity_locator,
        "producer_verdict": producer_verdict,
        "returned_artifacts": artifacts,
        "test_evidence": tests,
        "unresolved_findings": findings,
    }
    evidence_subject_raw_sha256 = _evidence_subject_raw_sha256(evidence_core)
    expected_subject = _session_subject(
        brief,
        brief_raw,
        evidence_artifact_id,
        evidence_subject_raw_sha256,
    )
    with WriterLock(
        Path(control_root) / "runtime" / "writer.lock",
        {
            "operation": "record_owner_operated_session_evidence",
            "evidence_artifact_id": evidence_artifact_id,
            "revision": str(target_revision),
            "expected_previous_revision": str(expected_previous_revision),
            "session_id": session_id,
        },
    ):
        history = _evidence_revision_history(store, evidence_artifact_id)
        latest = max(history) if history else 0
        if latest not in {expected_previous_revision, target_revision}:
            raise ConflictError(f"expected previous revision {expected_previous_revision}, observed {latest}")
        previous = history.get(expected_previous_revision)
        existing = history.get(target_revision)
        if existing is not None and (
            _evidence_core(existing) != evidence_core or existing["recorded_at"] != recorded_at
        ):
            raise ConflictError("session evidence retry changes the immutable document")
        if target_revision > 1:
            if previous is None:
                raise ConflictError("session evidence predecessor revision is missing")
            if _evidence_core(previous) != evidence_core:
                raise ConflictError("session evidence revision changes the immutable evidence subject")
            if target_revision == 2 and previous["document_state"] != "produced_unreviewed":
                raise ConflictError("independent review must supersede produced evidence")
            if target_revision == 3 and (
                previous["document_state"] != "independently_reviewed_pending_owner_acceptance"
            ):
                raise ConflictError("owner acceptance must supersede independently reviewed evidence")

        review: dict[str, Any]
        acceptance: dict[str, Any]
        document_state: str
        if target_revision == 1:
            review = {
                "reviewer_identity_locator": reviewer_identity_locator,
                "status": "pending_independent_review",
                "verdict": None,
                "evidence": None,
            }
            acceptance = {
                "acceptor_identity_locator": acceptor_identity_locator,
                "authority_grant_id": None,
                "authority_status": "unverified",
                "status": "pending_owner_acceptance",
                "outcome": None,
                "evidence": None,
            }
            document_state = "produced_unreviewed"
        else:
            trusted_store = _trusted_session_store(authority_binding, control_root)
            if review_record is None:
                raise SchemaError("later evidence revisions require a trusted review locator")
            review_authority_resolution_time = None
            review_authority_source = existing
            if review_authority_source is None and target_revision == 3:
                review_authority_source = previous
            if review_authority_source is not None:
                review_authority_resolution_time = _validate_utc(
                    review_authority_source["review"]["evidence"]["authority"]["resolved_at"],
                    "review authority resolved_at",
                )
            review, review_resolution, review_time = _resolve_independent_review(
                trusted_store,
                review_record,
                expected_subject=expected_subject,
                reviewer_identity_locator=reviewer_identity_locator,
                producer_identity_locator=producer_identity_locator,
                prepared_time=prepared_time,
                recorded_time=recorded_time,
                authority_resolution_time=review_authority_resolution_time,
            )
            if target_revision == 2:
                acceptance = {
                    "acceptor_identity_locator": acceptor_identity_locator,
                    "authority_grant_id": None,
                    "authority_status": "unverified",
                    "status": "pending_owner_acceptance",
                    "outcome": None,
                    "evidence": None,
                }
                document_state = "independently_reviewed_pending_owner_acceptance"
            else:
                if review["verdict"] != "accepted":
                    raise SchemaError("owner acceptance requires an accepted independent review")
                if not isinstance(authority_binding, ControlBinding):
                    raise SchemaError("owner acceptance requires a verified ControlBinding")
                if not isinstance(owner_decision_record, SessionRecordLocator):
                    raise SchemaError("owner acceptance requires a trusted decision locator")
                authority_resolution_time = None
                if existing is not None:
                    authority_resolution_time = _validate_utc(
                        existing["acceptance"]["evidence"]["authority"]["resolved_at"],
                        "owner authority resolved_at",
                    )
                acceptance = _resolve_owner_acceptance(
                    trusted_store,
                    owner_decision_record,
                    acceptor_identity_locator=acceptor_identity_locator,
                    expected_subject=expected_subject,
                    review_resolution=review_resolution,
                    review_time=review_time,
                    recorded_time=recorded_time,
                    authority_resolution_time=authority_resolution_time,
                )
                document_state = "owner_accepted"

        document: dict[str, Any] = {
            **evidence_core,
            "revision": target_revision,
            "supersedes_revision": None,
            "supersedes_document_raw_sha256": None,
            "document_state": document_state,
            "evidence_subject_raw_sha256": evidence_subject_raw_sha256,
            "review": review,
            "acceptance": acceptance,
            "recorded_at": recorded_at,
        }
        if target_revision > 1:
            document["supersedes_revision"] = expected_previous_revision
            document["supersedes_document_raw_sha256"] = sha256_hex(canonical_bytes(previous))
            if target_revision == 3 and previous["review"] != document["review"]:
                raise ConflictError("owner acceptance changes the recorded independent review")
        if existing is not None and existing != document:
            raise ConflictError("session evidence retry changes the immutable document")
        _validate_document(document, "owner-operated-session-evidence.schema.json")
        if _evidence_subject_raw_sha256(document) != document["evidence_subject_raw_sha256"]:
            raise ConflictError("session evidence document does not bind its exact evidence subject")
        path = store.write("artefact", evidence_artifact_id, target_revision, document)
    raw = path.read_bytes()
    return PublishedSessionDocument(path=path, raw_sha256=sha256_hex(raw), document=document)
