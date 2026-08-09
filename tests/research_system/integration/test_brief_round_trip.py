from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from research_system.artefacts.authority import ArtefactAuthorityContractLoader
from research_system.artefacts.runtime import GoverningScientificReviewStore
from research_system.artefacts.use_resolver import predicate_reference
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.cli import brief_export, brief_import
from research_system.context.command_adapter import CommandServiceContextWriter
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.service import ContextLifecycleService
from research_system.context.tokenizers import ReferenceRegexV1
from research_system.projection.replay import replay
from research_system.store.ledger import EventLedger
from tests.research_system.factories import ACTORS, PROJECT_ID, activate_lifecycle_grant, control_plane
from tests.research_system.integration.test_artefact_authority_commands import (
    ARTEFACT_ID,
    CONTENT_BYTES,
    CONTENT_SHA256,
    REVIEW_EVIDENCE_ID,
    REVIEW_ID,
    SCOPE_ID,
    SUBJECT,
    TASK_ID,
    artefact_manifest,
    command,
)


ROOT = Path(__file__).parents[3]
BRIEF_ID = "art_019fe47a-2000-7000-8000-000000002000"
IMPORTED_ID = "art_019fe47a-2001-7000-8000-000000002001"
CONTEXT_ID = "ctx_019fe47a-2002-7000-8000-000000002002"


def _register_review_authorized_subject(harness) -> None:
    content_path = harness.objects.control_root / "evidence" / "evaluation-run.json"
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_bytes(CONTENT_BYTES)
    owner_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact", "SetArtefactUseAuthority"),
    )
    review_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        actor_id=ACTORS["actor-a"],
        command_types=("RecordScientificReview",),
        grant_id="agr_019fe47a-1006-7000-8000-000000001006",
    )
    predicate, predicate_sha = ArtefactAuthorityContractLoader(SUBJECT).load().predicate_for("review_evidence")
    register = command(
        command_id="cmd_019fe47a-2010-7000-8000-000000002010",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=0,
        payload={"new_artefact_id": ARTEFACT_ID, "manifest": artefact_manifest()},
    )
    review = command(
        command_id="cmd_019fe47a-2011-7000-8000-000000002011",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=review_grant,
        expected_stream_version=1,
        payload={
            "artefact_id": ARTEFACT_ID,
            "review_id": REVIEW_ID,
            "subject_sha256": CONTENT_SHA256,
            "scientific_review": "approved",
            "evidence_refs": [REVIEW_EVIDENCE_ID],
        },
    )
    use = command(
        command_id="cmd_019fe47a-2012-7000-8000-000000002012",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=2,
        payload={
            "artefact_id": ARTEFACT_ID,
            "use_authority": "accepted_for_scope",
            "subject_sha256": CONTENT_SHA256,
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]), str(predicate["predicate_version"]), predicate_sha
            ),
            "evidence_refs": [REVIEW_ID, REVIEW_EVIDENCE_ID],
        },
    )
    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(review).status == "accepted"
    governing_reviews = GoverningScientificReviewStore(harness.objects, harness.schemas)
    governing_reviews.publish(
        REVIEW_EVIDENCE_ID,
        {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": PROJECT_ID,
            "review_id": REVIEW_ID,
            "subject_sha256": CONTENT_SHA256,
            "reviewer_actor_id": ACTORS["actor-a"],
            "eligible": True,
            "related": False,
            "independence_grade": "I1",
            "status": "active",
        },
    )
    harness.service.governing_evidence_resolver = governing_reviews
    assert harness.service.submit(use).status == "accepted"


def _deliver_real_context(harness):
    grant = activate_lifecycle_grant(
        harness,
        subject_kind="context",
        subject_id=CONTEXT_ID,
        command_types=(
            "RequestContextPacket",
            "BeginContextCompilation",
            "CompleteContextCompilation",
            "ValidateContextPacket",
            "IssueContextPacket",
            "RecordContextDelivery",
        ),
    )
    writer = CommandServiceContextWriter(
        harness.service,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        clock=lambda: datetime(2026, 8, 8, 12, tzinfo=UTC),
    )
    lifecycle = ContextLifecycleService(harness.objects, writer, writer_id="rm03-production")
    content = "governing exact methods brief context"
    compiled = lifecycle.compile_packet(
        request={
            "request_id": "rm03-context-request",
            "context_id": CONTEXT_ID,
            "revision": 1,
            "project_id": PROJECT_ID,
            "task_id": TASK_ID,
            "task_revision": 1,
            "purpose": "independent_review",
            "role": "reviewer",
            "risk": "R2",
            "actor_id": ACTORS["actor-a"],
            "session_id": "operator-session",
            "producing_attempt_id": None,
            "parent_context_id": None,
            "permitted_scopes": [SCOPE_ID],
            "control_store_identity": "store-one",
            "source_position": 7,
            "source_hash": "a" * 64,
            "compiler_version": "1.0.0",
            "policy_version": "1.0.0",
            "reference_profile": "bounded-r2",
            "reference_token_budget": 100,
            "provider_tokenizer_id": None,
            "provider_token_count": None,
            "provider_upper_bound_id": None,
            "provider_upper_bound_count": None,
            "provider_usable_capacity": None,
            "provider_reserve": None,
            "candidate_set_digest": "b" * 64,
            "retrieval_trace_refs": [],
            "confidence_summary": "all mandatory sources are direct and exact",
            "security_declaration": "no credentials, restricted data, transcripts, or hidden reasoning",
            "independence_evidence_refs": [],
            "delivery_receipt_refs": [],
            "currency_triggers": ["project-stream"],
            "retention_class": "project",
            "sensitivity_class": "internal",
            "supersession_lineage": [],
            "cumulative_addendum_bytes": 0,
            "expires_at": "2030-01-01T00:00:00Z",
        },
        fragments=[SourceFragment("method-source", "1", 10, True, content, sha256_hex(content.encode()))],
        profile=ContextProfile("bounded-r2", 100),
        reference_counter=ReferenceRegexV1(),
        required_source_ids={"method-source"},
    )
    validated = lifecycle.validate(
        compiled,
        capability=compiled.capability,
        validation_evidence={
            "route_decision_id": "route-1",
            "route_witness_sha256": "c" * 64,
            "selected_route_evidence_sha256": "d" * 64,
        },
        provider_template={"operation": "compile_brief"},
    )
    restarted = ContextLifecycleService(harness.objects, writer, writer_id="rm03-production")
    recovered = restarted.recover_validated(compiled.context_id)
    assert recovered == validated
    restarted.issue(recovered)
    restarted.record_delivery(
        compiled,
        recipient_id="operator",
        recipient_session_id="operator-session",
        adapter_id="owner-operated",
        delivered_sha256=compiled.packet_sha256,
    )
    return compiled


def _registration(artefact_id: str, context_id: str) -> dict:
    manifest = deepcopy(artefact_manifest())
    manifest.update(
        {
            "artefact_id": artefact_id,
            "context_packet_id": context_id,
            "artefact_type": "methods_document",
            "artefact_schema_id": "ars://methods/brief-manifest",
        }
    )
    manifest["authority"]["accepted_scope"] = SCOPE_ID
    return {
        "artefact_id": artefact_id,
        "project_id": PROJECT_ID,
        "actor_id": ACTORS["actor-a"],
        "authority_grant_id": artefact_id.replace("art_", "agr_", 1),
        "submitted_at": "2026-08-08T12:00:00Z",
        "correlation_id": "rm03-round-trip",
        "reason": "register exact methods document",
        "manifest": manifest,
    }


def test_real_cli_export_import_restart_and_replay(monkeypatch, tmp_path, capsys) -> None:
    harness = control_plane(tmp_path)
    _register_review_authorized_subject(harness)
    compiled = _deliver_real_context(harness)
    for artefact_id in (BRIEF_ID, IMPORTED_ID):
        activate_lifecycle_grant(
            harness, subject_kind="artefact", subject_id=artefact_id, command_types=("RegisterArtefact",)
        )
    binding = SimpleNamespace(
        control_root=harness.objects.control_root,
        project_id=PROJECT_ID,
        store_identity="store-one",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    monkeypatch.setattr("research_system.cli.ControlBinding.load", lambda path: binding)
    monkeypatch.setattr(
        "research_system.cli._brief_runtime",
        lambda args: (binding, harness.schemas, harness.ledger, harness.objects, harness.service),
    )
    request_path = tmp_path / "export.json"
    request_path.write_text(
        json.dumps(
            {
                "brief": {
                    "brief_purpose": "independent_review",
                    "context": {
                        "context_id": CONTEXT_ID,
                        "revision": 1,
                        "packet_sha256": compiled.packet_sha256,
                        "consumer_id": "operator",
                        "purpose": "independent_review",
                        "scope": SCOPE_ID,
                        "evaluation_time": "2026-08-08T12:00:00Z",
                        "control_store_identity": "store-one",
                        "source_position": 7,
                        "source_hash": "a" * 64,
                    },
                    "created_at": "2026-08-08T12:00:00Z",
                    "subjects": [
                        {
                            "artefact_id": ARTEFACT_ID,
                            "content_sha256": CONTENT_SHA256,
                            "task_id": TASK_ID,
                            "subject_kind": "artefact",
                            "path_or_name": "evidence/evaluation-run.json",
                            "role": "review_subject",
                        }
                    ],
                    "assets": [
                        {
                            "artefact_id": ARTEFACT_ID,
                            "content_sha256": CONTENT_SHA256,
                            "task_id": TASK_ID,
                            "asset_id": "adversarial-review",
                            "version": "1.0.0",
                            "identity": CONTENT_SHA256,
                            "identity_scheme": "lf_canonical_sha256",
                        }
                    ],
                    "expected_import_types": ["ReviewFindingSet"],
                    "deidentification": None,
                    "prohibitions": ["no execution", "no provider operation"],
                    "required_session_fields": ["operator_actor_id"],
                },
                "registration": _registration(BRIEF_ID, CONTEXT_ID),
            }
        ),
        encoding="utf-8",
    )
    assert brief_export(argparse.Namespace(config=tmp_path / "binding.json", request=request_path)) == 0
    exported = json.loads(capsys.readouterr().out)
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(canonical_bytes(exported["brief"]))
    brief_hash = exported["brief"]["brief_sha256"]
    session_path = tmp_path / "session.json"
    session_path.write_bytes(
        canonical_bytes(
            {
                "operator_actor_id": ACTORS["actor-a"],
                "application_family": "operator editor",
                "application_version": "1",
                "application_choice_by": "operator",
                "session_date": "2026-08-08",
                "responds_to_brief_manifest_sha256": brief_hash,
            }
        )
    )
    document = {
        "document_type": "ReviewFindingSet",
        "responds_to_brief_manifest_sha256": brief_hash,
        "status": "imported",
        "findings": [],
    }
    document_path = tmp_path / "document.json"
    document_path.write_bytes(canonical_bytes(document))
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(json.dumps(_registration(IMPORTED_ID, CONTEXT_ID)), encoding="utf-8")
    assert (
        brief_import(
            argparse.Namespace(
                config=tmp_path / "binding.json",
                brief=brief_path,
                session=session_path,
                document=document_path,
                registration=registration_path,
            )
        )
        == 0
    )
    imported = json.loads(capsys.readouterr().out)
    assert imported["use_authority"] == "candidate"
    assert (harness.objects.control_root / imported["relative_path"]).read_bytes() == canonical_bytes(document)
    before = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    restarted = EventLedger(harness.objects.control_root, PROJECT_ID, harness.schemas)
    after = replay(tuple(restarted.iter_events()), schema_registry=harness.schemas)
    assert after == before
    assert after["streams"][BRIEF_ID]["use_authority"] == "candidate"
    assert after["streams"][IMPORTED_ID]["use_authority"] == "candidate"
