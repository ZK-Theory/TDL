"""Provider-neutral owner-operated research brief construction."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, SchemaError
from research_system.evidence.consumers import ArtefactConsumerContext, ArtefactEvidenceConsumers
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    CommandSubmitter,
    RegisteredCandidate,
    register_candidate_document,
)
from research_system.methods.pack import MethodsAsset, MethodsPack
from research_system.schema_registry import SchemaRegistry


BRIEF_SCHEMA_ID = "ars://methods/brief-manifest"

_PURPOSE_CONSUMER = {
    "result_analysis": ("resolve_for_result", "rm03_result_assessment"),
    "result_reproduction": ("resolve_for_result", "rm03_result_assessment"),
    "scientific_review": ("resolve_for_review", "rm03_brief_review"),
    "independent_review": ("resolve_for_review", "rm03_brief_review"),
    "manuscript_review": ("resolve_for_manuscript", "rm03_brief_manuscript"),
    "claim_review": ("resolve_for_claim", "rm03_claim_assessment"),
    "claim_promotion_preparation": ("resolve_for_claim", "rm03_claim_assessment"),
}


@dataclass(frozen=True)
class BriefExportResult:
    manifest: dict[str, Any]
    registered: RegisteredCandidate
    context_packet: Any
    resolved_subjects: tuple[Any, ...]
    rendered_verification: dict[str, Any] | None


def _resolve_artefact(
    consumers: ArtefactEvidenceConsumers,
    *,
    purpose: str,
    context: ArtefactConsumerContext,
    attachment: bool = False,
) -> Any:
    if attachment:
        if purpose in {"scientific_review", "independent_review"}:
            return consumers.resolve_for_review(context, consumer_id="rm04_followup_review")
        if purpose == "manuscript_review":
            return consumers.resolve_for_manuscript(context, consumer_id="rm04_manuscript_pilot")
        raise ArsError("verification results may be attached only to review or manuscript briefs")
    try:
        method_name, consumer_id = _PURPOSE_CONSUMER[purpose]
    except KeyError as exc:
        raise ArsError("brief purpose has no artefact consumer") from exc
    return getattr(consumers, method_name)(context, consumer_id=consumer_id)


def _resolve_methods_asset(methods_pack: MethodsPack, requested: dict[str, Any]) -> MethodsAsset:
    matches = tuple(asset for asset in methods_pack.assets if asset.asset_id == requested.get("asset_id"))
    if len(matches) != 1:
        raise ArsError("brief asset is not a current RM-02 Methods Pack asset")
    asset = matches[0]
    expected = {
        "version": asset.version,
        "identity": asset.identity,
        "identity_scheme": asset.identity_scheme,
    }
    for field, value in expected.items():
        if requested.get(field) != value:
            raise ArsError(f"brief asset does not bind the current RM-02 {field}")
    return asset


def export_brief(
    *,
    request: dict[str, Any],
    context_resolver: Callable[..., Any],
    context_events: Callable[[], Iterable[dict[str, Any]]],
    context_objects: Any,
    artefact_consumers: ArtefactEvidenceConsumers,
    methods_pack: MethodsPack,
    schema_registry: SchemaRegistry,
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
) -> BriefExportResult:
    """Export and register one exact brief through the 06j and 06i public seams."""
    context_args = deepcopy(request["context"])
    context_args["events"] = tuple(context_events())
    context_args["objects"] = context_objects
    first_context = context_resolver(**context_args)
    purpose = str(request["brief_purpose"])
    resolved: list[Any] = []
    subject_rows: list[dict[str, Any]] = []
    for subject in request["subjects"]:
        consumer_context = ArtefactConsumerContext(
            artefact_id=subject["artefact_id"],
            exact_content_sha256=subject["content_sha256"],
            project_id=registration.project_id,
            task_id=subject["task_id"],
            scope_id=context_args["scope"],
            evaluation_time=context_args["evaluation_time"],
        )
        evidence = _resolve_artefact(artefact_consumers, purpose=purpose, context=consumer_context)
        resolved.append(evidence)
        subject_rows.append(
            {
                "subject_id": evidence.artefact_id,
                "subject_kind": subject["subject_kind"],
                "path_or_name": subject["path_or_name"],
                "sha256": evidence.exact_content_sha256,
                "role": subject["role"],
                "use_predicate_id": evidence.predicate_id,
                "use_predicate_version": evidence.predicate_version,
                "use_predicate_sha256": evidence.predicate_sha256,
            }
        )
    asset_rows: list[dict[str, Any]] = []
    for asset in request["assets"]:
        selected_asset = _resolve_methods_asset(methods_pack, asset)
        consumer_context = ArtefactConsumerContext(
            artefact_id=asset["artefact_id"],
            exact_content_sha256=asset["content_sha256"],
            project_id=registration.project_id,
            task_id=asset["task_id"],
            scope_id=context_args["scope"],
            evaluation_time=context_args["evaluation_time"],
        )
        evidence = _resolve_artefact(artefact_consumers, purpose=purpose, context=consumer_context)
        if evidence.content_bytes != selected_asset.raw_bytes:
            raise ArsError("authorized brief asset bytes differ from the current RM-02 asset")
        resolved.append(evidence)
        asset_rows.append(
            {
                "asset_id": selected_asset.asset_id,
                "version": selected_asset.version,
                "identity": selected_asset.identity,
                "identity_scheme": selected_asset.identity_scheme,
                "accepted_use_event_id": evidence.authority_event_id,
                "accepted_use_event_sha256": evidence.authority_event_hash,
            }
        )
    verification_context = None
    rendered_verification = None
    attach = request.get("attach_result")
    if attach is not None:
        attachment_context = ArtefactConsumerContext(
            artefact_id=attach["artefact_id"],
            exact_content_sha256=attach["content_sha256"],
            project_id=registration.project_id,
            task_id=attach["task_id"],
            scope_id=context_args["scope"],
            evaluation_time=context_args["evaluation_time"],
        )
        attachment = _resolve_artefact(
            artefact_consumers,
            purpose=purpose,
            context=attachment_context,
            attachment=True,
        )
        try:
            value = json.loads(attachment.content_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArsError("accepted verification result is not canonical JSON") from exc
        if canonical_bytes(value) != attachment.content_bytes:
            raise ArsError("accepted verification result is not canonical JSON")
        schema_registry.validate("ars://methods/operator-verification-run", value)
        verification_context = {
            "schema_id": "ars://methods/operator-verification-run",
            "schema_version": "1.0.0",
            "operator_verification_run_id": attachment.artefact_id,
            "content_hash": attachment.exact_content_sha256,
        }
        rendered_verification = {
            "outcome": value["outcome"],
            "traceback": value["traceback"],
            "stdout_excerpt": value["stdout_excerpt"],
            "stderr_excerpt": value["stderr_excerpt"],
            "attestation": value["attestation"],
        }
        resolved.append(attachment)
    manifest = finalize_brief_manifest(
        {
            "brief_artefact_id": registration.artefact_id,
            "brief_purpose": purpose,
            "context_packet": {
                "context_id": first_context.context_id,
                "revision": first_context.revision,
                "packet_sha256": first_context.packet_sha256,
                "delivery_receipt_id": first_context.delivery["delivery_receipt_id"],
                "delivery_receipt_sha256": sha256_hex(canonical_bytes(dict(first_context.delivery))),
            },
            "created_at": request["created_at"],
            "subjects": subject_rows,
            "assets": asset_rows,
            "expected_import_types": request["expected_import_types"],
            "deidentification": request.get("deidentification"),
            "prohibitions": request["prohibitions"],
            "required_session_fields": request["required_session_fields"],
            "verification_context": verification_context,
        },
        schema_registry=schema_registry,
    )
    context_args["events"] = tuple(context_events())
    final_context = context_resolver(**context_args)
    if final_context != first_context:
        raise ArsError("context packet changed during brief export")
    registered = register_candidate_document(
        value=manifest,
        registration=registration,
        document_store=document_store,
        command_service=command_service,
    )
    return BriefExportResult(manifest, registered, final_context, tuple(resolved), rendered_verification)


def finalize_brief_manifest(
    manifest: dict[str, Any],
    *,
    schema_registry: SchemaRegistry,
) -> dict[str, Any]:
    """Add the deterministic brief identity and validate the closed contract."""
    if "brief_sha256" in manifest:
        raise ArsError("caller-supplied brief_sha256 is prohibited")
    candidate = deepcopy(manifest)
    candidate["brief_sha256"] = sha256_hex(canonical_bytes(candidate))
    try:
        schema_registry.validate(BRIEF_SCHEMA_ID, candidate)
    except SchemaError as exc:
        raise ArsError(f"brief manifest schema rejected the document: {exc}") from exc
    return candidate
