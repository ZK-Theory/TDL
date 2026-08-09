"""Non-executing verification request and operator-report records."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any

from research_system.errors import ArsError, SchemaError
from research_system.schema_registry import SchemaRegistry
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    CommandSubmitter,
    RegisteredCandidate,
    register_candidate_document,
)


def _validate(schema_registry: SchemaRegistry, schema_id: str, value: dict[str, Any]) -> dict[str, Any]:
    try:
        schema_registry.validate(schema_id, value)
    except SchemaError as exc:
        raise ArsError(f"verification record schema rejected the document: {exc}") from exc
    return value


def build_verification_request(
    *,
    brief_sha256: str,
    request_artefact_id: str,
    candidate_artefact_id: str,
    script_source: str,
    recorded_at: str,
    schema_registry: SchemaRegistry,
) -> dict[str, Any]:
    """Record opaque proposed script text without executing or selecting a runner."""
    record = {
        "document_type": "VerificationRequest",
        "responds_to_brief_manifest_sha256": brief_sha256,
        "request_artefact_id": request_artefact_id,
        "candidate_artefact_id": candidate_artefact_id,
        "script_sha256": sha256(script_source.encode("utf-8")).hexdigest(),
        "script_source": script_source,
        "proposed_by": "external_session",
        "recorded_at": recorded_at,
    }
    return _validate(schema_registry, "ars://methods/verification-request", record)


def build_operator_verification_run(
    *,
    request: dict[str, Any],
    run_artefact_id: str,
    outcome: str,
    exit_code: int | None,
    stdout_excerpt: str,
    stderr_excerpt: str,
    traceback: str,
    environment_description: str,
    executed_by_actor_id: str,
    executed_on: str,
    schema_registry: SchemaRegistry,
) -> dict[str, Any]:
    """Record an attributed operator report; this function performs no execution."""
    request_copy = deepcopy(request)
    try:
        schema_registry.validate("ars://methods/verification-request", request_copy)
    except SchemaError as exc:
        raise ArsError(f"verification request schema rejected the document: {exc}") from exc
    recomputed = sha256(str(request_copy["script_source"]).encode("utf-8")).hexdigest()
    if request_copy.get("script_sha256") != recomputed:
        raise ArsError("verification request script hash is invalid")
    record = {
        "document_type": "OperatorVerificationRun",
        "responds_to_brief_manifest_sha256": request_copy["responds_to_brief_manifest_sha256"],
        "run_artefact_id": run_artefact_id,
        "request_artefact_id": request_copy["request_artefact_id"],
        "candidate_artefact_id": request_copy["candidate_artefact_id"],
        "script_sha256": recomputed,
        "outcome": outcome,
        "exit_code": exit_code,
        "stdout_excerpt": stdout_excerpt,
        "stderr_excerpt": stderr_excerpt,
        "traceback": traceback,
        "environment_description": environment_description,
        "executed_by_actor_id": executed_by_actor_id,
        "executed_on": executed_on,
        "attestation": "operator_self_attested",
    }
    return _validate(schema_registry, "ars://methods/operator-verification-run", record)


def register_verification_record(
    *,
    record: dict[str, Any],
    schema_registry: SchemaRegistry,
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Register a validated request or operator report without executing it."""
    document_type = record.get("document_type")
    schema_by_type = {
        "VerificationRequest": "ars://methods/verification-request",
        "OperatorVerificationRun": "ars://methods/operator-verification-run",
    }
    try:
        schema_id = schema_by_type[document_type]
    except KeyError as exc:
        raise ArsError("verification record type is not accepted") from exc
    _validate(schema_registry, schema_id, deepcopy(record))
    return register_candidate_document(
        value=record,
        registration=registration,
        document_store=document_store,
        command_service=command_service,
    )
