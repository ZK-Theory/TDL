"""Validation boundary for evidence returned by an owner-operated session."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, SchemaError
from research_system.schema_registry import SchemaRegistry
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    CommandSubmitter,
    RegisteredCandidate,
    register_candidate_document,
)


_DOCUMENT_SCHEMAS = {
    "ReviewFindingSet": "ars://methods/review-finding-set",
    "CounterexampleCandidate": "ars://methods/counterexample-candidate",
    "TheoremCitation": "ars://methods/theorem-citation",
    "ExploratoryMemo": "ars://methods/exploratory-memo",
    "VerificationRequest": "ars://methods/verification-request",
    "OperatorVerificationRun": "ars://methods/operator-verification-run",
}


@dataclass(frozen=True)
class ReturnedDocument:
    document_type: str
    schema_id: str
    raw_bytes: bytes
    content_sha256: str
    value: dict[str, Any]
    use_authority: str = "candidate"

    @staticmethod
    def sha256_of(raw_bytes: bytes) -> str:
        return sha256(raw_bytes).hexdigest()


def _validate_brief_identity(brief: dict[str, Any]) -> str:
    brief_hash = brief.get("brief_sha256")
    unsigned = deepcopy(brief)
    unsigned.pop("brief_sha256", None)
    if not isinstance(brief_hash, str) or brief_hash != sha256_hex(canonical_bytes(unsigned)):
        raise ArsError("brief manifest content identity is invalid")
    return brief_hash


def _validate_review_finding_set(document: dict[str, Any], brief: dict[str, Any]) -> None:
    review_subject = document["review_subject"]
    brief_review_subjects = [subject for subject in brief["subjects"] if subject.get("role") == "review_subject"]
    if len(brief_review_subjects) != 1:
        raise ArsError("ReviewFindingSet brief requires exactly one brief review_subject")
    if review_subject != brief_review_subjects[0]:
        raise ArsError("review finding set does not bind an exact brief review subject")

    dispositions = document["candidate_dispositions"]
    candidate_ids = [item["candidate_id"] for item in dispositions]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ArsError("review finding set candidate dispositions are not unique")

    findings = document["findings"]
    finding_ids = [item["finding_id"] for item in findings]
    finding_candidate_ids = [item["candidate_id"] for item in findings]
    if len(finding_ids) != len(set(finding_ids)) or len(finding_candidate_ids) != len(set(finding_candidate_ids)):
        raise ArsError("review finding set retained findings are not unique")

    retained_candidate_ids = {item["candidate_id"] for item in dispositions if item["disposition"] == "retained"}
    if retained_candidate_ids != set(finding_candidate_ids):
        raise ArsError("review finding set retained candidates do not match findings")


def validate_return_bundle(
    *,
    brief: dict[str, Any],
    session: dict[str, Any],
    document: dict[str, Any],
    schema_registry: SchemaRegistry,
) -> ReturnedDocument:
    """Validate one exact returned document without granting canonical use."""
    try:
        schema_registry.validate("ars://methods/brief-manifest", brief)
    except SchemaError as exc:
        raise ArsError(f"brief manifest schema rejected the document: {exc}") from exc
    brief_hash = _validate_brief_identity(brief)
    try:
        schema_registry.validate("ars://methods/session-record", session)
    except SchemaError as exc:
        raise ArsError(f"session record schema rejected the document: {exc}") from exc
    if session.get("responds_to_brief_manifest_sha256") != brief_hash:
        raise ArsError("session does not bind the exact brief manifest")

    document_type = document.get("document_type")
    schema_id = _DOCUMENT_SCHEMAS.get(document_type)
    if schema_id is None or document_type not in brief.get("expected_import_types", []):
        raise ArsError("returned document type is not expected by this brief")
    if document.get("responds_to_brief_manifest_sha256") != brief_hash:
        raise ArsError("returned document does not bind the exact brief manifest")
    try:
        schema_registry.validate(schema_id, document)
    except SchemaError as exc:
        raise ArsError(f"returned document schema rejected the document: {exc}") from exc
    if document_type == "ReviewFindingSet":
        _validate_review_finding_set(document, brief)
    raw = canonical_bytes(document)
    return ReturnedDocument(
        document_type=document_type,
        schema_id=schema_id,
        raw_bytes=raw,
        content_sha256=sha256_hex(raw),
        value=deepcopy(document),
    )


def import_return_bundle(
    *,
    brief: dict[str, Any],
    session: dict[str, Any],
    document: dict[str, Any],
    schema_registry: SchemaRegistry,
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
) -> tuple[ReturnedDocument, RegisteredCandidate]:
    """Validate exact returned bytes and register them at forced candidate authority."""
    returned = validate_return_bundle(
        brief=brief,
        session=session,
        document=document,
        schema_registry=schema_registry,
    )
    registered = register_candidate_document(
        value=returned.value,
        registration=registration,
        document_store=document_store,
        command_service=command_service,
    )
    if registered.raw_bytes != returned.raw_bytes:
        raise ArsError("registered import bytes differ from the validated document")
    return returned, registered
