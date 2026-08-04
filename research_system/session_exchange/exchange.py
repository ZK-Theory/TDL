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
from research_system.errors import ConflictError, SchemaError
from research_system.ids import validate_id
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
    "revision",
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


@dataclass(frozen=True)
class ExternalEvidence:
    """Exact bytes for an independently created record outside this seam."""

    record_locator: str
    path: Path
    media_type: str


@dataclass(frozen=True)
class IndependentReviewEvidence:
    """Operator-supplied independent-review record and its attributed verdict."""

    reviewer_identity_locator: str
    verdict: str
    record: ExternalEvidence


@dataclass(frozen=True)
class OwnerAcceptanceEvidence:
    """Operator-supplied owner decision plus the authority it exercised."""

    acceptor_identity_locator: str
    authority_locator: str
    authority_status: str
    decision: ExternalEvidence
    authority: ExternalEvidence


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


def _external_record(
    source: ExternalEvidence,
    label: str,
    definition_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if source.media_type != "application/json":
        raise SchemaError(f"{label} must use application/json")
    try:
        raw = Path(source.path).read_bytes()
    except (OSError, TypeError) as exc:
        raise SchemaError(f"{label} is unreadable: {source.record_locator}") from exc
    if not raw:
        raise SchemaError(f"{label} is empty: {source.record_locator}")
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaError(f"{label} must be UTF-8 JSON") from exc
    if not isinstance(record, dict):
        raise SchemaError(f"{label} must be a JSON object")
    try:
        expected_raw = canonical_bytes(record)
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"{label} is outside canonical JSON") from exc
    if raw != expected_raw:
        raise SchemaError(f"{label} must be exact canonical JSON")
    schema_path = _SCHEMA_ROOT / "owner-operated-session-evidence.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        record_schema = {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{definition_name}",
        }
        Draft202012Validator.check_schema(record_schema)
        Draft202012Validator(record_schema, format_checker=FormatChecker()).validate(record)
    except (OSError, KeyError, UnicodeDecodeError, json.JSONDecodeError, JsonSchemaError, ValidationError) as exc:
        raise SchemaError(f"invalid {label}") from exc
    evidence = {
        "record_locator": source.record_locator,
        "media_type": source.media_type,
        "raw_sha256": sha256_hex(raw),
        "byte_length": len(raw),
    }
    return evidence, record


def _evidence_core(document: dict[str, Any]) -> dict[str, Any]:
    return {field: document[field] for field in _EVIDENCE_CORE_FIELDS}


def _evidence_subject_raw_sha256(document: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(_evidence_core(document)))


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


def record_session_evidence(
    control_root: Path,
    *,
    evidence_artifact_id: str,
    brief_artifact_id: str,
    handoff_id: str,
    session_id: str,
    attempt_id: str,
    producer_identity_locator: str,
    reviewer_identity_locator: str,
    acceptor_identity_locator: str,
    acceptance_authority_locator: str,
    returned_artifacts: tuple[EvidenceArtifact, ...],
    test_evidence: tuple[EvidenceArtifact, ...],
    producer_verdict: str,
    unresolved_findings: tuple[UnresolvedFinding, ...],
    recorded_at: str,
    review_evidence: IndependentReviewEvidence | None = None,
    acceptance_evidence: OwnerAcceptanceEvidence | None = None,
) -> PublishedSessionDocument:
    """Record exact returned bytes and only externally supplied later evidence."""
    recorded_time = _validate_utc(recorded_at, "recorded_at")
    if len({producer_identity_locator, reviewer_identity_locator, acceptor_identity_locator}) != 3:
        raise SchemaError("producer, reviewer, and acceptor identity locators must be distinct")
    store = ObjectStore(control_root)
    brief = store.read("artefact", brief_artifact_id, 1)
    if not isinstance(brief, dict):
        raise SchemaError("prepared session brief must be an object")
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
        "revision": 1,
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
    review: dict[str, Any]
    acceptance: dict[str, Any]
    document_state: str
    external_locators: list[str] = []
    review_time: datetime | None = None
    review_record_raw_sha256: str | None = None
    if review_evidence is None:
        review = {
            "reviewer_identity_locator": reviewer_identity_locator,
            "status": "pending_independent_review",
            "verdict": None,
            "evidence": None,
        }
        document_state = "produced_unreviewed"
    else:
        if review_evidence.reviewer_identity_locator != reviewer_identity_locator:
            raise ConflictError("independent review identity does not match the expected reviewer")
        review_record, review_document = _external_record(
            review_evidence.record,
            "independent review evidence",
            "independentReviewRecord",
        )
        if review_document["subject"] != expected_subject:
            raise ConflictError("independent review record does not bind the exact session subject")
        if review_document["reviewer_identity_locator"] != reviewer_identity_locator:
            raise ConflictError("independent review record names the wrong reviewer")
        if review_document["producer_identity_locator"] != producer_identity_locator:
            raise ConflictError("independent review record names the wrong producer")
        if review_document["verdict"] != review_evidence.verdict:
            raise ConflictError("independent review caller verdict contradicts the record")
        review_time = _validate_utc(review_document["reviewed_at"], "independent review reviewed_at")
        if review_time < prepared_time:
            raise SchemaError("independent review evidence is stale for the prepared session subject")
        if review_time > recorded_time:
            raise SchemaError("independent review evidence is from the future")
        review_record_raw_sha256 = review_record["raw_sha256"]
        review = {
            "reviewer_identity_locator": reviewer_identity_locator,
            "status": "independent_review_recorded",
            "verdict": review_document["verdict"],
            "reviewed_at": review_document["reviewed_at"],
            "evidence": review_record,
        }
        external_locators.append(review_record["record_locator"])
        document_state = "independently_reviewed_pending_owner_acceptance"
    if acceptance_evidence is None:
        acceptance = {
            "acceptor_identity_locator": acceptor_identity_locator,
            "authority_locator": acceptance_authority_locator,
            "authority_status": "unverified",
            "status": "pending_owner_acceptance",
            "outcome": None,
            "evidence": None,
        }
    else:
        if review_evidence is None or review["verdict"] != "accepted":
            raise SchemaError("owner acceptance requires an accepted independent review record")
        if acceptance_evidence.acceptor_identity_locator != acceptor_identity_locator:
            raise ConflictError("owner acceptance identity does not match the expected acceptor")
        if acceptance_evidence.authority_locator != acceptance_authority_locator:
            raise ConflictError("owner acceptance authority does not match the expected authority")
        decision, decision_document = _external_record(
            acceptance_evidence.decision,
            "owner acceptance decision",
            "ownerAcceptanceDecisionRecord",
        )
        authority, authority_document = _external_record(
            acceptance_evidence.authority,
            "owner acceptance authority",
            "ownerAcceptanceAuthorityRecord",
        )
        for label, record in (
            ("owner acceptance decision", decision_document),
            ("owner acceptance authority", authority_document),
        ):
            if record["subject"] != expected_subject:
                raise ConflictError(f"{label} does not bind the exact session subject")
            if record["acceptor_identity_locator"] != acceptor_identity_locator:
                raise ConflictError(f"{label} names the wrong acceptor")
            if record["authority_locator"] != acceptance_authority_locator:
                raise ConflictError(f"{label} names the wrong authority")
        if acceptance_evidence.authority_status != authority_document["status"]:
            raise ConflictError("owner acceptance caller authority status contradicts the record")
        if authority_document["status"] != "active":
            raise SchemaError("owner acceptance requires active external authority evidence")
        if decision_document["review_record_raw_sha256"] != review_record_raw_sha256:
            raise ConflictError("owner acceptance decision does not bind the exact review record")
        if decision_document["outcome"] != "accepted":
            raise SchemaError("owner acceptance decision record does not accept the subject")
        decision_time = _validate_utc(decision_document["decided_at"], "owner acceptance decided_at")
        if review_time is None or decision_time <= review_time:
            raise SchemaError("owner acceptance decision must be later than the independent review")
        if decision_time > recorded_time:
            raise SchemaError("owner acceptance decision is from the future")
        valid_from = _validate_utc(authority_document["valid_from"], "owner authority valid_from")
        valid_until = _validate_utc(authority_document["valid_until"], "owner authority valid_until")
        if valid_until <= valid_from:
            raise SchemaError("owner acceptance authority validity interval is empty")
        if decision_time < valid_from:
            raise SchemaError("owner acceptance authority is not yet effective")
        if recorded_time >= valid_until:
            raise SchemaError("owner acceptance authority is expired")
        acceptance = {
            "acceptor_identity_locator": acceptor_identity_locator,
            "authority_locator": acceptance_authority_locator,
            "authority_status": "active",
            "status": "owner_acceptance_recorded",
            "outcome": decision_document["outcome"],
            "decided_at": decision_document["decided_at"],
            "authority_valid_from": authority_document["valid_from"],
            "authority_valid_until": authority_document["valid_until"],
            "evidence": {"decision": decision, "authority": authority},
        }
        external_locators.extend([decision["record_locator"], authority["record_locator"]])
        document_state = "owner_accepted"
    all_locators = combined_locators + external_locators
    if len(all_locators) != len(set(all_locators)):
        raise SchemaError("returned and external evidence locators must be disjoint")
    document: dict[str, Any] = {
        **evidence_core,
        "document_state": document_state,
        "evidence_subject_raw_sha256": evidence_subject_raw_sha256,
        "review": review,
        "acceptance": acceptance,
        "recorded_at": recorded_at,
    }
    _validate_document(document, "owner-operated-session-evidence.schema.json")
    if _evidence_subject_raw_sha256(document) != document["evidence_subject_raw_sha256"]:
        raise ConflictError("session evidence document does not bind its exact evidence subject")
    path = store.write("artefact", evidence_artifact_id, 1, document)
    raw = path.read_bytes()
    return PublishedSessionDocument(path=path, raw_sha256=sha256_hex(raw), document=document)
