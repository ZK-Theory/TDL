from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.artefacts.authority import ArtefactAuthorityContractLoader
from research_system.artefacts.runtime import (
    ControlRootArtefactContentReader,
    GoverningScientificReviewStore,
)
from research_system.artefacts.use_resolver import ArtefactUseResolver, predicate_reference
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.cli import main
from research_system.context.command_adapter import CommandServiceContextWriter
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.service import ContextLifecycleService
from research_system.context.tokenizers import ReferenceRegexV1
from research_system.errors import SchemaError
from research_system.evidence.consumers import ArtefactEvidenceConsumers
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    register_candidate_document,
)
from research_system.methods.pack import load_methods_pack
from research_system.methods.verification_records import (
    build_operator_verification_run,
    build_verification_request,
    register_verification_record,
)
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
RETRY_ID = "art_019fe47a-2005-7000-8000-000000002005"
METHODS_ASSET_ARTEFACT_ID = "art_019fe47a-2006-7000-8000-000000002006"
METHODS_ASSET_REVIEW_ID = "rev_019fe47a-2007-7000-8000-000000002007"
METHODS_ASSET_REVIEW_EVIDENCE_ID = "arec_019fe47a-2008-7000-8000-000000002008"


def test_context_event_rejects_wrong_registered_command_identity_without_append(tmp_path) -> None:
    harness = control_plane(tmp_path)
    wrong = harness.schemas.resolve_identity("ars://core/command/CreateTask", "1.0.0")
    payload = {
        "context_id": CONTEXT_ID,
        "request_id": "rm03-context-request",
        "revision": 1,
        "compiler_version": "1.0.0",
        "policy_version": "1.0.0",
    }
    proposed = {
        "event_type": "ContextCompilationStarted",
        "stream_id": CONTEXT_ID,
        "command_id": "cmd_019fe47a-2010-7000-8000-000000002010",
        "command_type": "BeginContextCompilation",
        "command_schema_id": wrong.schema_id,
        "command_schema_version": wrong.schema_version,
        "command_schema_sha256": wrong.sha256,
        "actor_id": ACTORS["actor-a"],
        "authority_grant_id": "agr_019fe47a-2011-7000-8000-000000002011",
        "idempotency_key": "wrong-context-producer-identity",
        "command_payload_hash": sha256_hex(canonical_bytes(payload)),
        "correlation_id": f"context:{CONTEXT_ID}",
        "causation_id": None,
        "schema_id": "ars://core/event/ContextCompilationStarted",
        "schema_version": "1.0.0",
        "occurred_at": None,
        "payload": payload,
    }
    before = tuple(harness.ledger.iter_events())
    with pytest.raises(SchemaError, match="command_schema_id"):
        harness.ledger.append([proposed])
    assert tuple(harness.ledger.iter_events()) == before


VERIFICATION_REQUEST_ID = "art_019fe47a-2013-7000-8000-000000002013"
VERIFICATION_RUN_ID = "art_019fe47a-2014-7000-8000-000000002014"
FOLLOWUP_BRIEF_ID = "art_019fe47a-2015-7000-8000-000000002015"
VERIFICATION_RUN_REVIEW_ID = "rev_019fe47a-2016-7000-8000-000000002016"
VERIFICATION_RUN_REVIEW_EVIDENCE_ID = "arec_019fe47a-2017-7000-8000-000000002017"


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


def _register_review_authorized_methods_asset(harness, asset) -> None:
    relative_path = "methods/assets/adversarial-review-protocol.md"
    content_path = harness.objects.control_root / relative_path
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_bytes(asset.raw_bytes)
    content_sha256 = sha256_hex(asset.raw_bytes)
    owner_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=METHODS_ASSET_ARTEFACT_ID,
        command_types=("RegisterArtefact", "SetArtefactUseAuthority"),
    )
    review_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=METHODS_ASSET_ARTEFACT_ID,
        actor_id=ACTORS["actor-a"],
        command_types=("RecordScientificReview",),
        grant_id="agr_019fe47a-2009-7000-8000-000000002009",
    )
    predicate, predicate_sha = ArtefactAuthorityContractLoader(SUBJECT).load().predicate_for("review_evidence")
    manifest = deepcopy(artefact_manifest())
    manifest.update(
        {
            "artefact_id": METHODS_ASSET_ARTEFACT_ID,
            "artefact_type": "methods_asset",
            "artefact_schema_id": "ars://methods/provider-neutral-asset",
            "context_packet_id": CONTEXT_ID,
            "relative_path": relative_path,
            "size_bytes": len(asset.raw_bytes),
            "media_type": "text/markdown",
            "content_sha256": content_sha256,
        }
    )
    manifest["validation"]["expected_schema_ids"] = ["ars://methods/provider-neutral-asset"]
    register = command(
        command_id="cmd_019fe47a-2020-7000-8000-000000002020",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=0,
        payload={"new_artefact_id": METHODS_ASSET_ARTEFACT_ID, "manifest": manifest},
    )
    review = command(
        command_id="cmd_019fe47a-2021-7000-8000-000000002021",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=review_grant,
        expected_stream_version=1,
        payload={
            "artefact_id": METHODS_ASSET_ARTEFACT_ID,
            "review_id": METHODS_ASSET_REVIEW_ID,
            "subject_sha256": content_sha256,
            "scientific_review": "approved",
            "evidence_refs": [METHODS_ASSET_REVIEW_EVIDENCE_ID],
        },
    )
    use = command(
        command_id="cmd_019fe47a-2022-7000-8000-000000002022",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=2,
        payload={
            "artefact_id": METHODS_ASSET_ARTEFACT_ID,
            "use_authority": "accepted_for_scope",
            "subject_sha256": content_sha256,
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]), str(predicate["predicate_version"]), predicate_sha
            ),
            "evidence_refs": [METHODS_ASSET_REVIEW_ID, METHODS_ASSET_REVIEW_EVIDENCE_ID],
        },
    )
    for envelope in (register, review, use):
        envelope["target_stream_id"] = METHODS_ASSET_ARTEFACT_ID
    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(review).status == "accepted"
    governing_reviews = GoverningScientificReviewStore(harness.objects, harness.schemas)
    governing_reviews.publish(
        METHODS_ASSET_REVIEW_EVIDENCE_ID,
        {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": PROJECT_ID,
            "review_id": METHODS_ASSET_REVIEW_ID,
            "subject_sha256": content_sha256,
            "reviewer_actor_id": ACTORS["actor-a"],
            "eligible": True,
            "related": False,
            "independence_grade": "I1",
            "status": "active",
        },
    )
    harness.service.governing_evidence_resolver = governing_reviews
    assert harness.service.submit(use).status == "accepted"


def _authorize_verification_run_for_review(harness, content_sha256: str) -> None:
    owner_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=VERIFICATION_RUN_ID,
        command_types=("SetArtefactUseAuthority",),
        grant_id="agr_019fe47a-2019-7000-8000-000000002019",
    )
    review_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=VERIFICATION_RUN_ID,
        actor_id=ACTORS["actor-a"],
        command_types=("RecordScientificReview",),
        grant_id="agr_019fe47a-2018-7000-8000-000000002018",
    )
    predicate, predicate_sha = ArtefactAuthorityContractLoader(SUBJECT).load().predicate_for("review_evidence")
    review = command(
        command_id="cmd_019fe47a-2023-7000-8000-000000002023",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=review_grant,
        expected_stream_version=1,
        payload={
            "artefact_id": VERIFICATION_RUN_ID,
            "review_id": VERIFICATION_RUN_REVIEW_ID,
            "subject_sha256": content_sha256,
            "scientific_review": "approved",
            "evidence_refs": [VERIFICATION_RUN_REVIEW_EVIDENCE_ID],
        },
    )
    use = command(
        command_id="cmd_019fe47a-2024-7000-8000-000000002024",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=2,
        payload={
            "artefact_id": VERIFICATION_RUN_ID,
            "use_authority": "accepted_for_scope",
            "subject_sha256": content_sha256,
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]), str(predicate["predicate_version"]), predicate_sha
            ),
            "evidence_refs": [VERIFICATION_RUN_REVIEW_ID, VERIFICATION_RUN_REVIEW_EVIDENCE_ID],
        },
    )
    for envelope in (review, use):
        envelope["target_stream_id"] = VERIFICATION_RUN_ID
    assert harness.service.submit(review).status == "accepted"
    governing_reviews = GoverningScientificReviewStore(harness.objects, harness.schemas)
    governing_reviews.publish(
        VERIFICATION_RUN_REVIEW_EVIDENCE_ID,
        {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": PROJECT_ID,
            "review_id": VERIFICATION_RUN_REVIEW_ID,
            "subject_sha256": content_sha256,
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


def _registration(
    artefact_id: str,
    context_id: str,
    schema_id: str = "ars://methods/brief-manifest",
) -> dict:
    manifest = deepcopy(artefact_manifest())
    manifest.update(
        {
            "artefact_id": artefact_id,
            "context_packet_id": context_id,
            "artefact_type": "methods_document",
            "artefact_schema_id": schema_id,
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


def test_candidate_registration_exact_retry_replays_real_command(tmp_path) -> None:
    class InterruptOnceStore(CandidateDocumentStore):
        attempts = 0

        def write(self, artefact_id, raw_bytes):
            self.attempts += 1
            if self.attempts == 1:
                raise OSError("simulated post-authority publication interruption")
            return super().write(artefact_id, raw_bytes)

    harness = control_plane(tmp_path)
    activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=RETRY_ID,
        command_types=("RegisterArtefact",),
    )
    registration = CandidateRegistration(**_registration(RETRY_ID, CONTEXT_ID))
    store = InterruptOnceStore(harness.objects.control_root)
    value = {"document_type": "ReviewFindingSet", "findings": []}

    with pytest.raises(OSError, match="interruption"):
        register_candidate_document(
            value=value,
            registration=registration,
            document_store=store,
            command_service=harness.service,
        )

    assert not (harness.objects.control_root / store.relative_path(RETRY_ID)).exists()
    events_after_acceptance = tuple(event for event in harness.ledger.iter_events() if event["stream_id"] == RETRY_ID)
    assert len(events_after_acceptance) == 1

    recovered = register_candidate_document(
        value=value,
        registration=registration,
        document_store=store,
        command_service=harness.service,
    )

    assert (harness.objects.control_root / recovered.relative_path).read_bytes() == recovered.raw_bytes
    assert recovered.receipt.status == "accepted"
    assert tuple(event for event in harness.ledger.iter_events() if event["stream_id"] == RETRY_ID) == (
        events_after_acceptance
    )


def test_real_cli_export_import_restart_and_replay(monkeypatch, tmp_path, capsys) -> None:
    harness = control_plane(tmp_path)
    _register_review_authorized_subject(harness)
    methods_pack = load_methods_pack(ROOT)
    selected_asset = next(asset for asset in methods_pack.assets if asset.asset_id == "mth_adversarial_review_protocol")
    _register_review_authorized_methods_asset(harness, selected_asset)
    compiled = _deliver_real_context(harness)
    for artefact_id in (
        BRIEF_ID,
        IMPORTED_ID,
        VERIFICATION_REQUEST_ID,
        VERIFICATION_RUN_ID,
        FOLLOWUP_BRIEF_ID,
    ):
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
    consumers = ArtefactEvidenceConsumers(
        ArtefactUseResolver(
            ledger=harness.ledger,
            objects=harness.objects,
            schemas=harness.schemas,
            contract_loader=ArtefactAuthorityContractLoader(SUBJECT),
            governing_evidence=GoverningScientificReviewStore(harness.objects, harness.schemas),
            content_reader=ControlRootArtefactContentReader(harness.objects.control_root),
            authority_state_validator=harness.authority_resolver.validate_replayed_administration_state,
        )
    )
    monkeypatch.setattr("research_system.cli.build_artefact_consumers", lambda binding: consumers)
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
                            "artefact_id": METHODS_ASSET_ARTEFACT_ID,
                            "content_sha256": sha256_hex(selected_asset.raw_bytes),
                            "task_id": TASK_ID,
                            "asset_id": selected_asset.asset_id,
                            "version": selected_asset.version,
                            "identity": selected_asset.identity,
                            "identity_scheme": selected_asset.identity_scheme,
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
    assert (
        main(
            [
                "brief",
                "export",
                "--config",
                str(tmp_path / "binding.json"),
                "--request",
                str(request_path),
            ]
        )
        == 0
    )
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
        "review_subject": exported["brief"]["subjects"][0],
        "findings": [],
        "candidate_dispositions": [
            {
                "candidate_id": "candidate-content-identity",
                "summary": "The subject content identity might not reproduce.",
                "disposition": "rejected",
                "rationale": "The canonical preimage reproduces the declared identity.",
            }
        ],
    }
    document_path = tmp_path / "document.json"
    document_path.write_bytes(canonical_bytes(document))
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(json.dumps(_registration(IMPORTED_ID, CONTEXT_ID)), encoding="utf-8")
    assert (
        main(
            [
                "brief",
                "import",
                "--config",
                str(tmp_path / "binding.json"),
                "--brief",
                str(brief_path),
                "--session",
                str(session_path),
                "--document",
                str(document_path),
                "--registration",
                str(registration_path),
            ]
        )
        == 0
    )
    imported = json.loads(capsys.readouterr().out)
    assert imported["use_authority"] == "candidate"
    assert (harness.objects.control_root / imported["relative_path"]).read_bytes() == canonical_bytes(document)

    verification_request = build_verification_request(
        brief_sha256=brief_hash,
        request_artefact_id=VERIFICATION_REQUEST_ID,
        candidate_artefact_id=IMPORTED_ID,
        script_source="assert returned_document_hash",
        recorded_at="2026-08-08T12:10:00Z",
        schema_registry=harness.schemas,
    )
    registered_request = register_verification_record(
        record=verification_request,
        schema_registry=harness.schemas,
        registration=CandidateRegistration(
            **_registration(
                VERIFICATION_REQUEST_ID,
                CONTEXT_ID,
                "ars://methods/verification-request",
            )
        ),
        document_store=CandidateDocumentStore(harness.objects.control_root),
        command_service=harness.service,
    )
    verification_run = build_operator_verification_run(
        request=verification_request,
        run_artefact_id=VERIFICATION_RUN_ID,
        outcome="failed",
        exit_code=1,
        stdout_excerpt="",
        stderr_excerpt="candidate hash differed",
        traceback="trace exact candidate mismatch",
        environment_description="owner-operated workstation",
        executed_by_actor_id=ACTORS["actor-a"],
        executed_on="2026-08-08T12:15:00Z",
        schema_registry=harness.schemas,
    )
    registered_run = register_verification_record(
        record=verification_run,
        schema_registry=harness.schemas,
        registration=CandidateRegistration(
            **_registration(
                VERIFICATION_RUN_ID,
                CONTEXT_ID,
                "ars://methods/operator-verification-run",
            )
        ),
        document_store=CandidateDocumentStore(harness.objects.control_root),
        command_service=harness.service,
    )
    assert (harness.objects.control_root / registered_request.relative_path).read_bytes() == canonical_bytes(
        verification_request
    )
    assert (harness.objects.control_root / registered_run.relative_path).read_bytes() == canonical_bytes(
        verification_run
    )
    _authorize_verification_run_for_review(harness, registered_run.content_sha256)

    followup_path = tmp_path / "followup-export.json"
    followup_path.write_text(
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
                        "evaluation_time": "2026-08-08T12:20:00Z",
                        "control_store_identity": "store-one",
                        "source_position": 7,
                        "source_hash": "a" * 64,
                    },
                    "created_at": "2026-08-08T12:20:00Z",
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
                            "artefact_id": METHODS_ASSET_ARTEFACT_ID,
                            "content_sha256": sha256_hex(selected_asset.raw_bytes),
                            "task_id": TASK_ID,
                            "asset_id": selected_asset.asset_id,
                            "version": selected_asset.version,
                            "identity": selected_asset.identity,
                            "identity_scheme": selected_asset.identity_scheme,
                        }
                    ],
                    "expected_import_types": ["ReviewFindingSet"],
                    "deidentification": None,
                    "prohibitions": ["no execution", "no provider operation"],
                    "required_session_fields": ["operator_actor_id"],
                    "attach_result": {
                        "artefact_id": VERIFICATION_RUN_ID,
                        "content_sha256": registered_run.content_sha256,
                        "task_id": TASK_ID,
                    },
                },
                "registration": _registration(FOLLOWUP_BRIEF_ID, CONTEXT_ID),
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "brief",
                "export",
                "--config",
                str(tmp_path / "binding.json"),
                "--request",
                str(followup_path),
                "--attach-result",
                VERIFICATION_RUN_ID,
            ]
        )
        == 0
    )
    followup = json.loads(capsys.readouterr().out)
    assert followup["rendered_verification"]["traceback"] == "trace exact candidate mismatch"
    assert followup["brief"]["verification_context"]["operator_verification_run_id"] == VERIFICATION_RUN_ID
    before = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    restarted = EventLedger(harness.objects.control_root, PROJECT_ID, harness.schemas)
    after = replay(tuple(restarted.iter_events()), schema_registry=harness.schemas)
    assert after == before
    assert after["streams"][BRIEF_ID]["use_authority"] == "candidate"
    assert after["streams"][IMPORTED_ID]["use_authority"] == "candidate"
    assert after["streams"][VERIFICATION_REQUEST_ID]["use_authority"] == "candidate"
    assert after["streams"][VERIFICATION_RUN_ID]["use_authority"] == "accepted_for_scope"
    assert after["streams"][FOLLOWUP_BRIEF_ID]["use_authority"] == "candidate"
