from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from research_system.artefacts.authority import (
    AcceptedContractSubject,
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
)
from research_system.artefacts.use_resolver import ArtefactUseRequest, ArtefactUseResolver, predicate_reference
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.errors import ArsError, ConflictError
from research_system.projection.replay import replay
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import ACTORS, PROJECT_ID, REPO_ROOT, activate_lifecycle_grant, control_plane
from tests.research_system.integration.test_wp6_1_c1_readiness_lease import (
    ATTEMPT_ID as C1_ATTEMPT_ID,
    _c1_command,
    _command_id,
    _mutable_c1_control_plane,
    _seed_running_attempt,
)
from tests.research_system.integration.test_wp6_1_c3_completion_review_decision import (
    ACTOR_C,
    _record_review_verdict,
    _request_review,
    _submit_review_command,
)
from tests.research_system.integration.test_wp6_1_task_scope_lifecycle import _command as _lifecycle_command


ARTEFACT_ID = "art_019fe47a-1000-7000-8000-000000001000"
TASK_ID = "tsk_019fe47a-1001-7000-8000-000000001001"
DISPATCH_ID = "dsp_019fe47a-1002-7000-8000-000000001002"
ATTEMPT_ID = "att_019fe47a-1003-7000-8000-000000001003"
CONTEXT_ID = "ctx_019fe47a-1004-7000-8000-000000001004"
REVIEW_ID = "rev_019fe47a-1005-7000-8000-000000001005"
REVIEW_GRANT_ID = "agr_019fe47a-1006-7000-8000-000000001006"
REVIEW_EVIDENCE_ID = "arec_019fe47a-1007-7000-8000-000000001007"
REPLACEMENT_ARTEFACT_ID = "art_019fe47a-1008-7000-8000-000000001008"
LATE_REVIEW_ID = "rev_019fe47a-1009-7000-8000-000000001009"
CLAIM_DECISION_ID = "dec_019fe47a-1013-7000-8000-000000001013"
SCOPE_ID = "release:wp6.4"
CONTENT_BYTES = canonical_bytes(
    {
        "schema_id": "ars://evals/evaluation-run",
        "schema_version": "1.0.0",
        "outcome": "passed",
    }
)
CONTENT_SHA256 = sha256_hex(CONTENT_BYTES)
SUBJECT = AcceptedContractSubject(
    manifest_git_blob="9d415f9af23caa963c36dbbb8103c2bf55101a95",
    manifest_sha256="365ee6643dc626f361f00bb06901718386dba319549d7079f5182fa672d1cb05",
)
P6_COMMAND_EVENTS = {
    "RecordArtefactAvailability": "ArtefactAvailabilityRecorded",
    "RecordArtefactRegenerability": "ArtefactRegenerabilityRecorded",
    "RecordArtefactIntegrity": "ArtefactIntegrityRecorded",
    "RecordStructuralValidation": "StructuralValidationRecorded",
    "RecordScientificReview": "ScientificReviewRecorded",
    "SetArtefactUseAuthority": "ArtefactUseAuthoritySet",
    "SupersedeArtefact": "ArtefactSuperseded",
    "AdoptLateArtefact": "LateArtefactAdopted",
}


class StaticGoverningEvidenceResolver:
    independence_grade = "I1"

    def resolve(self, reference_id, *, project_id, evaluation_time):
        record = {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": project_id,
            "review_id": REVIEW_ID,
            "subject_sha256": CONTENT_SHA256,
            "reviewer_actor_id": ACTORS["actor-a"],
            "eligible": True,
            "related": False,
            "independence_grade": self.independence_grade,
            "status": "active",
        }
        assert reference_id == REVIEW_EVIDENCE_ID
        assert evaluation_time.tzinfo is not None
        return GoverningEvidenceResolution(
            reference_id=reference_id,
            canonical_sha256=sha256_hex(canonical_bytes(record)),
            record=record,
        )


def artefact_manifest() -> dict[str, object]:
    return {
        "artefact_id": ARTEFACT_ID,
        "aliases": [],
        "artefact_type": "evaluation_run",
        "artefact_schema_id": "ars://evals/evaluation-run",
        "artefact_schema_version": "1.0.0",
        "task_id": TASK_ID,
        "dispatch_id": DISPATCH_ID,
        "attempt_id": ATTEMPT_ID,
        "producer_actor_id": ACTORS["actor-b"],
        "producer_profile": "wp6.4-production",
        "context_packet_id": CONTEXT_ID,
        "created_at": "2026-08-08T20:00:00Z",
        "code_commit": "git:sha1:" + "1" * 40,
        "branch_identity": "codex/wp64-rm-integration-r1",
        "worktree_identity": "wp64-rm-integration-r1",
        "environment_fingerprint": "2" * 64,
        "root_id": "control",
        "relative_path": "evidence/evaluation-run.json",
        "size_bytes": len(CONTENT_BYTES),
        "media_type": "application/json",
        "content_sha256": CONTENT_SHA256,
        "observed_at": "2026-08-08T20:00:00Z",
        "availability_check_evidence_refs": ["availability-check:1"],
        "input_dependencies": [],
        "research_provenance": {
            "dataset_ids": [],
            "dataset_vintages": [],
            "representation_ids": [],
            "parameter_ids": [],
            "seed_ids": [],
            "sample_restriction_ids": [],
        },
        "validation": {
            "validation_record_refs": ["validation:1"],
            "expected_contract_ids": ["06i"],
            "expected_schema_ids": ["ars://evals/evaluation-run"],
        },
        "authority": {
            "availability": "available",
            "regenerability": "non_regenerable",
            "integrity": "verified",
            "structural_validation": "passed",
            "scientific_review": "pending",
            "use_authority": "candidate",
            "accepted_scope": SCOPE_ID,
            "consumer_restrictions": [],
        },
        "operations": {
            "no_overwrite_evidence_refs": ["no-overwrite:1"],
            "retention_class": "durable",
            "confidentiality_class": "internal",
            "external_data_constraints": [],
        },
    }


def command(
    *,
    command_id: str,
    command_type: str,
    actor_id: str,
    authority_grant_id: str,
    expected_stream_version: int,
    payload: dict[str, object],
    target_stream_id: str = ARTEFACT_ID,
) -> dict[str, object]:
    return {
        "command_id": command_id,
        "command_type": command_type,
        "schema_id": f"ars://core/command/{command_type}",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-08T20:00:00Z",
        "actor_id": actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": authority_grant_id,
        "target_stream_id": target_stream_id,
        "expected_stream_version": expected_stream_version,
        "idempotency_key": f"06i:{command_type}:{command_id}",
        "correlation_id": "06i:real-path",
        "causation_id": None,
        "reason": "Exercise the accepted artefact-authority production path.",
        "evidence_refs": list(payload.get("evidence_refs", [])),
        "payload": payload,
        "project_id": PROJECT_ID,
    }


def accepted_artefact_commands(harness) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    harness.service.governing_evidence_resolver = StaticGoverningEvidenceResolver()
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
        grant_id=REVIEW_GRANT_ID,
    )
    loader = ArtefactAuthorityContractLoader(SUBJECT)
    predicate, predicate_sha256 = loader.load().predicate_for("result_evidence")
    register = command(
        command_id="cmd_019fe47a-1010-7000-8000-000000001010",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=0,
        payload={"new_artefact_id": ARTEFACT_ID, "manifest": artefact_manifest()},
    )
    review = command(
        command_id="cmd_019fe47a-1011-7000-8000-000000001011",
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
        command_id="cmd_019fe47a-1012-7000-8000-000000001012",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=2,
        payload={
            "artefact_id": ARTEFACT_ID,
            "use_authority": "accepted_for_scope",
            "subject_sha256": CONTENT_SHA256,
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]),
                str(predicate["predicate_version"]),
                predicate_sha256,
            ),
            "evidence_refs": [REVIEW_ID, REVIEW_EVIDENCE_ID],
        },
    )
    return register, review, use


def test_all_eight_p6_runtime_bindings_are_literal():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    for command_type, event_type in P6_COMMAND_EVENTS.items():
        command_binding = schemas.command_binding(command_type)
        event_binding = schemas.event_binding(event_type, command_type)
        assert command_binding is not None, command_type
        assert event_binding is not None, event_type
        assert command_binding.schema_id == f"ars://core/command/{command_type}"
        assert event_binding.schema_id == f"ars://core/event/{event_type}"


def test_four_artefact_dimensions_are_separate_durable_replayable_rows(tmp_path):
    harness = control_plane(tmp_path)
    grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact", *tuple(P6_COMMAND_EVENTS)[:4]),
    )
    register = command(
        command_id="cmd_019fe47a-1020-7000-8000-000000001020",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=0,
        payload={"new_artefact_id": ARTEFACT_ID, "manifest": artefact_manifest()},
    )
    rows = (
        ("RecordArtefactAvailability", "availability", "available"),
        ("RecordArtefactRegenerability", "regenerability", "regenerable_verified"),
        ("RecordArtefactIntegrity", "integrity", "verified"),
        ("RecordStructuralValidation", "structural_validation", "passed"),
    )
    assert harness.service.submit(register).status == "accepted"
    for offset, (command_type, field, value) in enumerate(rows, start=1):
        payload = {
            "artefact_id": ARTEFACT_ID,
            field: value,
            "subject_sha256": CONTENT_SHA256,
            "evidence_refs": [f"evidence:{field}"],
        }
        if command_type in {"RecordArtefactIntegrity", "RecordStructuralValidation"}:
            payload["validator_identity"] = "validator:wp6-c3"
        receipt = harness.service.submit(
            command(
                command_id=f"cmd_019fe47a-102{offset}-7000-8000-00000000102{offset}",
                command_type=command_type,
                actor_id=ACTORS["actor-a"],
                authority_grant_id=grant,
                expected_stream_version=offset,
                payload=payload,
            )
        )
        assert receipt.status == "accepted", receipt
    projected = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ARTEFACT_ID]
    assert {field: projected[field] for _, field, _ in rows} == {field: value for _, field, value in rows}
    assert len(projected["authority_dimension_evidence"]) == 4


def test_supersession_preserves_both_manifests_and_projects_replacement(tmp_path):
    harness = control_plane(tmp_path)
    main_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact", "SupersedeArtefact"),
    )
    replacement_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=REPLACEMENT_ARTEFACT_ID,
        command_types=("RegisterArtefact",),
    )
    replacement_manifest = deepcopy(artefact_manifest())
    replacement_manifest["artefact_id"] = REPLACEMENT_ARTEFACT_ID
    replacement_manifest["relative_path"] = "evidence/evaluation-run-replacement.json"
    for artefact_id, manifest, grant, number in (
        (ARTEFACT_ID, artefact_manifest(), main_grant, 1030),
        (REPLACEMENT_ARTEFACT_ID, replacement_manifest, replacement_grant, 1031),
    ):
        receipt = harness.service.submit(
            command(
                command_id=f"cmd_019fe47a-{number}-7000-8000-00000000{number}",
                command_type="RegisterArtefact",
                actor_id=ACTORS["actor-a"],
                authority_grant_id=grant,
                expected_stream_version=0,
                payload={"new_artefact_id": artefact_id, "manifest": manifest},
                target_stream_id=artefact_id,
            )
        )
        assert receipt.status == "accepted", receipt
    supersede = command(
        command_id="cmd_019fe47a-1032-7000-8000-000000001032",
        command_type="SupersedeArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=main_grant,
        expected_stream_version=1,
        payload={
            "artefact_id": ARTEFACT_ID,
            "replacement_artefact_id": REPLACEMENT_ARTEFACT_ID,
            "supersession_reason": "replace the bounded evaluation evidence",
            "supersession_scope": SCOPE_ID,
            "replacement_sha256": CONTENT_SHA256,
            "effective_at": "2026-08-08T21:00:00Z",
            "continuing_consumer_dispositions": ["result consumers move to replacement"],
        },
    )
    assert harness.service.submit(supersede).status == "accepted"
    projected = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"]
    assert projected[ARTEFACT_ID]["use_authority"] == "superseded"
    assert projected[ARTEFACT_ID]["supersession"]["replacement_artefact_id"] == REPLACEMENT_ARTEFACT_ID
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == artefact_manifest()
    assert harness.objects.read("artefact", REPLACEMENT_ARTEFACT_ID, 1) == replacement_manifest


def test_supersession_rejects_a_non_mapping_registered_manifest(tmp_path):
    harness = control_plane(tmp_path)
    snapshot = harness.ledger.snapshot()
    malformed_registration = {
        "event_type": "ArtefactRegistered",
        "stream_id": ARTEFACT_ID,
        "payload": {"manifest": "not-a-manifest"},
    }
    replacement_manifest = deepcopy(artefact_manifest())
    replacement_manifest["artefact_id"] = REPLACEMENT_ARTEFACT_ID
    replacement_registration = {
        "event_type": "ArtefactRegistered",
        "stream_id": REPLACEMENT_ARTEFACT_ID,
        "payload": {"manifest": replacement_manifest},
    }
    malformed_snapshot = replace(
        snapshot,
        events=(*snapshot.events, malformed_registration, replacement_registration),
        stream_versions={**snapshot.stream_versions, ARTEFACT_ID: 1, REPLACEMENT_ARTEFACT_ID: 1},
    )
    envelope = command(
        command_id="cmd_019fe47a-1033-7000-8000-000000001033",
        command_type="SupersedeArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id="agr_019fe47a-1033-7000-8000-000000001033",
        expected_stream_version=1,
        payload={
            "artefact_id": ARTEFACT_ID,
            "replacement_artefact_id": REPLACEMENT_ARTEFACT_ID,
            "supersession_reason": "malformed source history must fail closed",
            "supersession_scope": SCOPE_ID,
            "replacement_sha256": CONTENT_SHA256,
            "effective_at": "2026-08-08T21:00:00Z",
            "continuing_consumer_dispositions": ["no consumer mutation"],
        },
    )

    receipt = harness.service._prepare_artefact_authority_command(
        Command(envelope),
        malformed_snapshot,
        1,
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "artefact_subject_hash_mismatch"


def _utc_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _prepared_late_adoption(tmp_path):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    complete = _c1_command(
        _command_id(1040),
        "CompleteAttempt",
        C1_ATTEMPT_ID,
        harness.ledger.snapshot().stream_versions[C1_ATTEMPT_ID],
        {
            "attempt_id": C1_ATTEMPT_ID,
            "candidate_artefact_ids": [ARTEFACT_ID],
            "end_evidence_refs": ["evidence:attempt-complete"],
            "output_disposition": "retained_as_candidate",
        },
    )
    assert harness.service.submit(complete).status == "accepted"
    terminal_event = next(
        event
        for event in reversed(harness.ledger.snapshot().events)
        if event.get("stream_id") == C1_ATTEMPT_ID and event.get("event_type") == "AttemptCompleted"
    )
    terminal_recorded_at = datetime.fromisoformat(terminal_event["recorded_at"].replace("Z", "+00:00"))
    grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact", "AdoptLateArtefact"),
    )
    register = command(
        command_id="cmd_019fe47a-1046-7000-8000-000000001046",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=0,
        payload={
            "new_artefact_id": ARTEFACT_ID,
            "manifest": {**artefact_manifest(), "producer_actor_id": ACTORS["actor-a"]},
        },
    )
    assert harness.service.submit(register).status == "accepted"
    artefact_subject_hash = sha256_hex(
        canonical_bytes(
            replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ARTEFACT_ID]
        )
    )
    _request_review(harness, LATE_REVIEW_ID, 1041, artefact_subject_hash, subject_id=ARTEFACT_ID)
    _record_review_verdict(harness, LATE_REVIEW_ID, artefact_subject_hash, 1042, "approve")
    _submit_review_command(
        harness,
        1045,
        "SatisfyReview",
        LATE_REVIEW_ID,
        {
            "review_id": LATE_REVIEW_ID,
            "prior_review_state": "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:late-adoption"],
            "satisfaction_gate": "late-artefact-adoption",
        },
    )
    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][C1_ATTEMPT_ID]
    adopt = command(
        command_id="cmd_019fe47a-1047-7000-8000-000000001047",
        command_type="AdoptLateArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=1,
        payload={
            "artefact_id": ARTEFACT_ID,
            "attempt_id": C1_ATTEMPT_ID,
            "review_id": LATE_REVIEW_ID,
            "artefact_sha256": CONTENT_SHA256,
            "late_observed_at": _utc_z(terminal_recorded_at + timedelta(seconds=1)),
            "lease_id": attempt["lease_id"],
            "allowed_consumer_scope": [SCOPE_ID],
        },
    )
    adopt["submitted_at"] = _utc_z(terminal_recorded_at + timedelta(seconds=2))
    clock["now"] = terminal_recorded_at + timedelta(seconds=3)
    return harness, adopt, terminal_recorded_at


def test_late_adoption_requires_terminal_attempt_satisfied_review_and_exact_hash(tmp_path):
    harness, adopt, _terminal_recorded_at = _prepared_late_adoption(tmp_path)
    first = harness.service.submit(adopt)
    assert first.status == "accepted", first
    assert harness.service.submit(deepcopy(adopt)) == first
    projected = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ARTEFACT_ID]
    assert projected["late_adoptions"][0]["review_id"] == LATE_REVIEW_ID


@pytest.mark.parametrize(
    "late_observed_at",
    ("before_terminal", "at_terminal", "after_submission"),
)
def test_late_adoption_rejects_observation_outside_terminal_to_submission_interval_without_publication(
    tmp_path,
    late_observed_at,
):
    harness, adopt, terminal_recorded_at = _prepared_late_adoption(tmp_path)
    submitted_at = datetime.fromisoformat(adopt["submitted_at"].replace("Z", "+00:00"))
    invalid_times = {
        "before_terminal": terminal_recorded_at - timedelta(microseconds=1),
        "at_terminal": terminal_recorded_at,
        "after_submission": submitted_at + timedelta(microseconds=1),
    }
    adopt["payload"]["late_observed_at"] = _utc_z(invalid_times[late_observed_at])
    before_snapshot = harness.ledger.snapshot()
    before_batches = tuple(harness.ledger.iter_batches())
    before_object = deepcopy(harness.objects.read("artefact", ARTEFACT_ID, 1))

    receipt = harness.service.submit(adopt)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "late_artefact_adoption_invalid"
    assert harness.receipts.load(receipt.command_id) == receipt
    assert harness.ledger.snapshot() == before_snapshot
    assert tuple(harness.ledger.iter_batches()) == before_batches
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == before_object


def test_late_adoption_rejects_future_observation_and_submission_without_publication(tmp_path):
    harness, adopt, _terminal_recorded_at = _prepared_late_adoption(tmp_path)
    adopt["payload"]["late_observed_at"] = "2099-01-01T00:00:00Z"
    adopt["submitted_at"] = "2099-01-02T00:00:00Z"
    before_snapshot = harness.ledger.snapshot()
    before_batches = tuple(harness.ledger.iter_batches())
    before_object = deepcopy(harness.objects.read("artefact", ARTEFACT_ID, 1))

    receipt = harness.service.submit(adopt)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "late_artefact_adoption_invalid"
    assert harness.receipts.load(receipt.command_id) == receipt
    assert harness.ledger.snapshot() == before_snapshot
    assert tuple(harness.ledger.iter_batches()) == before_batches
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == before_object


def test_new_p6_precondition_failures_leave_no_event_or_object_residue(tmp_path):
    harness = control_plane(tmp_path)
    command_types = (
        "RegisterArtefact",
        "RecordArtefactAvailability",
        "RecordArtefactRegenerability",
        "RecordArtefactIntegrity",
        "RecordStructuralValidation",
        "SupersedeArtefact",
        "AdoptLateArtefact",
    )
    grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=command_types,
    )
    register = command(
        command_id="cmd_019fe47a-1050-7000-8000-000000001050",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=0,
        payload={"new_artefact_id": ARTEFACT_ID, "manifest": artefact_manifest()},
    )
    assert harness.service.submit(register).status == "accepted"
    before_events = tuple(harness.ledger.iter_events())
    before_object = deepcopy(harness.objects.read("artefact", ARTEFACT_ID, 1))
    invalid_payloads = (
        (
            "RecordArtefactAvailability",
            {"availability": "available", "subject_sha256": "0" * 64, "evidence_refs": ["e:a"]},
        ),
        (
            "RecordArtefactRegenerability",
            {"regenerability": "regenerable_verified", "subject_sha256": "0" * 64, "evidence_refs": ["e:r"]},
        ),
        (
            "RecordArtefactIntegrity",
            {
                "integrity": "verified",
                "validator_identity": "validator:c3",
                "subject_sha256": "0" * 64,
                "evidence_refs": ["e:i"],
            },
        ),
        (
            "RecordStructuralValidation",
            {
                "structural_validation": "passed",
                "validator_identity": "validator:c3",
                "subject_sha256": "0" * 64,
                "evidence_refs": ["e:s"],
            },
        ),
        (
            "SupersedeArtefact",
            {
                "replacement_artefact_id": REPLACEMENT_ARTEFACT_ID,
                "supersession_reason": "missing replacement must deny",
                "supersession_scope": SCOPE_ID,
                "replacement_sha256": CONTENT_SHA256,
                "effective_at": "2026-08-11T00:00:00Z",
                "continuing_consumer_dispositions": ["no mutation"],
            },
        ),
        (
            "AdoptLateArtefact",
            {
                "attempt_id": C1_ATTEMPT_ID,
                "review_id": LATE_REVIEW_ID,
                "artefact_sha256": CONTENT_SHA256,
                "late_observed_at": "2026-08-11T00:00:00Z",
                "lease_id": "els_019fe47a-1051-7000-8000-000000001051",
                "allowed_consumer_scope": [SCOPE_ID],
            },
        ),
    )
    for offset, (command_type, fields) in enumerate(invalid_payloads, start=1):
        payload = {"artefact_id": ARTEFACT_ID, **fields}
        rejected = harness.service.submit(
            command(
                command_id=f"cmd_019fe47a-105{offset}-7000-8000-00000000105{offset}",
                command_type=command_type,
                actor_id=ACTORS["actor-a"],
                authority_grant_id=grant,
                expected_stream_version=1,
                payload=payload,
            )
        )
        assert rejected.status == "rejected", (command_type, rejected)
        assert harness.receipts.load(rejected.command_id) == rejected
    assert tuple(harness.ledger.iter_events()) == before_events
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == before_object


@pytest.mark.parametrize(
    ("trusted_now", "submitted_at", "effective_at", "expected_status"),
    (
        (
            datetime(2026, 8, 8, 20, 0, tzinfo=UTC),
            "2026-08-08T20:00:00Z",
            "2026-08-08T19:00:00Z",
            "accepted",
        ),
        (
            datetime(2026, 8, 9, 20, 0, tzinfo=UTC),
            "2026-08-08T20:00:00Z",
            "2026-08-08T19:00:00Z",
            "accepted",
        ),
        (
            datetime(2026, 8, 8, 20, 0, tzinfo=UTC),
            "2026-08-09T20:00:00Z",
            "2026-08-09T19:00:00Z",
            "rejected",
        ),
    ),
    ids=("current_p005_decision", "historical_p005_decision", "future_p005_decision"),
)
def test_claim_consumption_binds_current_p005_owner_decision_and_review_set(
    tmp_path,
    trusted_now,
    submitted_at,
    effective_at,
    expected_status,
):
    class I2GoverningEvidenceResolver(StaticGoverningEvidenceResolver):
        independence_grade = "I2"

    base = control_plane(tmp_path, clock=lambda: trusted_now)
    harness = replace(
        base,
        service=base.authority_service,
        ledger=base.authority_ledger,
        objects=base.authority_objects,
        receipts=base.authority_receipts,
    )
    harness.service.governing_evidence_resolver = I2GoverningEvidenceResolver()
    artefact_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
    )
    register = command(
        command_id="cmd_019fe47a-1060-7000-8000-000000001060",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=artefact_grant,
        expected_stream_version=0,
        payload={"new_artefact_id": ARTEFACT_ID, "manifest": artefact_manifest()},
    )
    scientific_review = command(
        command_id="cmd_019fe47a-1061-7000-8000-000000001061",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=artefact_grant,
        expected_stream_version=1,
        payload={
            "artefact_id": ARTEFACT_ID,
            "review_id": REVIEW_ID,
            "subject_sha256": CONTENT_SHA256,
            "scientific_review": "approved",
            "evidence_refs": [REVIEW_EVIDENCE_ID],
        },
    )
    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(scientific_review).status == "accepted"

    proposer_grant = activate_lifecycle_grant(
        harness,
        subject_kind="decision",
        subject_id=CLAIM_DECISION_ID,
        actor_id=ACTOR_C,
        allowed_actor_classes=("agent",),
        command_types=("ProposeDecision", "RequestDecisionReview"),
        grant_id="agr_019fe47a-1162-7000-8000-000000001162",
    )
    propose = _lifecycle_command(
        "cmd_019fe47a-1062-7000-8000-000000001062",
        "ProposeDecision",
        CLAIM_DECISION_ID,
        0,
        {
            "new_decision_id": CLAIM_DECISION_ID,
            "question": "May the exact claim evidence be promoted?",
            "recommendation": "approve",
            "options": ["approve", "deny"],
            "decision_revision": 1,
            "decision_kind": "claim_promotion",
            "governing_evidence_refs": [REVIEW_EVIDENCE_ID],
            "affected_task_ids": [],
            "affected_claim_ids": [],
            "required_authority": "Stephen",
            "expires_at": "2026-08-12T00:00:00Z",
            "review_date": "2026-08-10T00:00:00Z",
            "consequences": ["only the exact accepted scope may consume the evidence"],
        },
    )
    propose["actor_id"] = ACTOR_C
    propose["authority_grant_id"] = proposer_grant
    assert harness.service.submit(propose).status == "accepted"
    request_decision_review = _lifecycle_command(
        "cmd_019fe47a-1063-7000-8000-000000001063",
        "RequestDecisionReview",
        CLAIM_DECISION_ID,
        1,
        {
            "decision_id": CLAIM_DECISION_ID,
            "decision_revision": 1,
            "review_requirements": ["independent exact-subject review"],
            "governing_evidence_refs": [REVIEW_EVIDENCE_ID],
        },
    )
    request_decision_review["actor_id"] = ACTOR_C
    request_decision_review["authority_grant_id"] = proposer_grant
    assert harness.service.submit(request_decision_review).status == "accepted"
    decision_hash = sha256_hex(
        canonical_bytes(
            replay(
                tuple(harness.ledger.iter_events()),
                schema_registry=harness.schemas,
                authority_state_validator=harness.authority_resolver.validate_replayed_administration_state,
            )["streams"][CLAIM_DECISION_ID]
        )
    )

    review_owner_grant = activate_lifecycle_grant(
        harness,
        subject_kind="review",
        subject_id=REVIEW_ID,
        command_types=("RequestReview", "AssignReview", "SatisfyReview"),
        grant_id="agr_019fe47a-1164-7000-8000-000000001164",
    )
    reviewer_grant = activate_lifecycle_grant(
        harness,
        subject_kind="review",
        subject_id=REVIEW_ID,
        actor_id=ACTORS["actor-b"],
        allowed_actor_classes=("agent",),
        command_types=("StartReview", "RecordReviewVerdict"),
        grant_id="agr_019fe47a-1165-7000-8000-000000001165",
    )
    review_commands = [
        (
            "RequestReview",
            ACTORS["actor-a"],
            review_owner_grant,
            {
                "new_review_id": REVIEW_ID,
                "review_type": "software",
                "subject_ids": [CLAIM_DECISION_ID],
                "subject_hashes": [decision_hash],
                "governing_refs": ["P-005", "06i"],
                "review_questions": ["Does the decision bind the exact governing review set?"],
                "required_evidence_refs": [REVIEW_EVIDENCE_ID],
                "required_lanes": ["scientific", "provenance"],
                "reviewer_capability": ["claim-promotion"],
                "required_independence_grade": "independent_exact_subject",
                "visibility_policy": "owner_and_reviewer",
                "allowed_verdicts": ["accept_exact_subject", "rework_required"],
                "satisfaction_authority": "owner",
                "deadline": "2026-08-11T00:00:00Z",
                "escalation_rule": "rework on any binding mismatch",
            },
        ),
        (
            "AssignReview",
            ACTORS["actor-a"],
            review_owner_grant,
            {
                "review_id": REVIEW_ID,
                "reviewer_actor_id": ACTORS["actor-b"],
                "computed_independence_grade": "I2",
                "independence_evidence_refs": ["evidence:independent"],
            },
        ),
        (
            "StartReview",
            ACTORS["actor-b"],
            reviewer_grant,
            {
                "review_id": REVIEW_ID,
                "unchanged_subject_sha256": decision_hash,
                "visibility_policy": "owner_and_reviewer",
            },
        ),
        (
            "RecordReviewVerdict",
            ACTORS["actor-b"],
            reviewer_grant,
            {
                "review_id": REVIEW_ID,
                "verdict": "approve",
                "findings": [],
                "reviewer_actor_id": ACTORS["actor-b"],
                "required_evidence_refs": [REVIEW_EVIDENCE_ID],
                "limitations": [],
                "conditions": [],
                "reviewer_profile": "independent-reviewer",
                "reviewer_session": "session:p005",
                "reviewer_model_metadata": "model:independent",
                "context_manifest_id": CONTEXT_ID,
                "context_manifest_sha256": "a" * 64,
                "unchanged_subject_sha256": decision_hash,
                "producing_attempt_id": ATTEMPT_ID,
                "trace_visibility_evidence_refs": ["evidence:trace"],
                "computed_independence_grade": "I2",
            },
        ),
        (
            "SatisfyReview",
            ACTORS["actor-a"],
            review_owner_grant,
            {
                "review_id": REVIEW_ID,
                "prior_review_state": "verdict_recorded",
                "policy_evaluation_refs": ["policy-evaluation:p005"],
                "satisfaction_gate": "claim-promotion",
            },
        ),
    ]
    for offset, (command_type, actor_id, grant_id, payload) in enumerate(review_commands):
        review_command = _lifecycle_command(
            f"cmd_019fe47a-107{offset}-7000-8000-00000000107{offset}",
            command_type,
            REVIEW_ID,
            offset,
            payload,
        )
        review_command["actor_id"] = actor_id
        review_command["authority_grant_id"] = grant_id
        assert harness.service.submit(review_command).status == "accepted"

    decision_owner_grant = activate_lifecycle_grant(
        harness,
        subject_kind="decision",
        subject_id=CLAIM_DECISION_ID,
        command_types=("ResolveDecision",),
        grant_id="agr_019fe47a-1180-7000-8000-000000001180",
    )
    resolve = _lifecycle_command(
        "cmd_019fe47a-1080-7000-8000-000000001080",
        "ResolveDecision",
        CLAIM_DECISION_ID,
        2,
        {
            "decision_id": CLAIM_DECISION_ID,
            "selected_option": "approve",
            "effective_scope": f"claim_promotion:{SCOPE_ID}",
            "effective_at": effective_at,
            "decision_revision": 1,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": decision_owner_grant,
            "governing_evidence_refs": [REVIEW_EVIDENCE_ID],
            "considered_review_ids": [REVIEW_ID],
            "permitted_commands": ["SetArtefactUseAuthority"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["subject or review change"],
        },
    )
    resolve["actor_id"] = ACTORS["actor-a"]
    resolve["authority_grant_id"] = decision_owner_grant
    assert harness.service.submit(resolve).status == "accepted"

    contract = ArtefactAuthorityContractLoader(SUBJECT).load()
    claim, claim_sha256 = contract.predicate_for("claim_evidence")
    use = command(
        command_id="cmd_019fe47a-1081-7000-8000-000000001081",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=artefact_grant,
        expected_stream_version=2,
        payload={
            "artefact_id": ARTEFACT_ID,
            "use_authority": "accepted_for_scope",
            "subject_sha256": CONTENT_SHA256,
            "consumer_predicate": predicate_reference(
                str(claim["predicate_id"]), str(claim["predicate_version"]), claim_sha256
            ),
            "evidence_refs": [REVIEW_ID, REVIEW_EVIDENCE_ID, CLAIM_DECISION_ID],
        },
    )
    use["submitted_at"] = submitted_at
    before_snapshot = harness.ledger.snapshot()
    before_batches = tuple(harness.ledger.iter_batches())
    before_object = deepcopy(harness.objects.read("artefact", ARTEFACT_ID, 1))
    accepted = harness.service.submit(use)
    if expected_status == "rejected":
        assert accepted.status == "rejected"
        assert accepted.reason_code == "artefact_authority_time_invalid"
        assert harness.receipts.load(accepted.command_id) == accepted
        assert harness.ledger.snapshot() == before_snapshot
        assert tuple(harness.ledger.iter_batches()) == before_batches
        assert harness.objects.read("artefact", ARTEFACT_ID, 1) == before_object
        return
    assert accepted.status == "accepted", accepted

    class ContentReader:
        def read(self, *, root_id: str, relative_path: str) -> bytes:
            assert (root_id, relative_path) == ("control", "evidence/evaluation-run.json")
            return CONTENT_BYTES

    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=ArtefactAuthorityContractLoader(SUBJECT),
        governing_evidence=I2GoverningEvidenceResolver(),
        content_reader=ContentReader(),
        authority_state_validator=harness.authority_resolver.validate_replayed_administration_state,
    )
    resolved = resolver.resolve(
        ArtefactUseRequest(
            artefact_id=ARTEFACT_ID,
            exact_content_sha256=CONTENT_SHA256,
            consumer_id="rm03_claim_assessment",
            consumer_kind="claim_evidence",
            project_id=PROJECT_ID,
            task_id=TASK_ID,
            scope_id=SCOPE_ID,
            predicate_id=str(claim["predicate_id"]),
            predicate_version=str(claim["predicate_version"]),
            predicate_sha256=claim_sha256,
            evaluation_time=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
            required_decision_kind="claim_promotion",
        )
    )
    assert resolved.decision_id == CLAIM_DECISION_ID
    assert resolved.decision_event_id
    assert resolved.decision_event_hash
    assert resolved.decision_projection_sha256
    assert resolved.governing_review_ids == (REVIEW_ID,)
    assert resolved.governing_review_set_sha256


def test_register_review_and_use_authority_are_real_durable_commands(tmp_path):
    harness = control_plane(tmp_path, clock=lambda: datetime(2026, 8, 8, 20, 0, tzinfo=UTC))
    commands = accepted_artefact_commands(harness)

    receipts = [harness.service.submit(value) for value in commands]
    events = tuple(harness.ledger.iter_events())

    assert [receipt.status for receipt in receipts] == ["accepted", "accepted", "accepted"]
    assert [event["event_type"] for event in events] == [
        "ArtefactRegistered",
        "ScientificReviewRecorded",
        "ArtefactUseAuthoritySet",
    ]
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == artefact_manifest()
    assert harness.service.submit(deepcopy(commands[0])) == receipts[0]


@pytest.mark.parametrize(
    ("method_name", "command_index"),
    (
        ("prevalidate_register_artefact_batch", 0),
        ("prevalidate_artefact_authority_batch", 1),
    ),
)
@pytest.mark.parametrize("collision", ("command_id", "idempotency_scope"))
def test_artefact_batch_prevalidation_rejects_duplicate_transaction_identity_without_mutation(
    tmp_path,
    method_name,
    command_index,
    collision,
):
    harness = control_plane(tmp_path)
    base = accepted_artefact_commands(harness)[command_index]
    second = deepcopy(base)
    second["target_stream_id"] = REPLACEMENT_ARTEFACT_ID
    if second["command_type"] == "RegisterArtefact":
        second["payload"]["new_artefact_id"] = REPLACEMENT_ARTEFACT_ID
        second["payload"]["manifest"]["artefact_id"] = REPLACEMENT_ARTEFACT_ID
    else:
        second["payload"]["artefact_id"] = REPLACEMENT_ARTEFACT_ID
    if collision == "idempotency_scope":
        second["command_id"] = "cmd_019fe47a-1090-7000-8000-000000001090"
    before = tuple(
        (path.relative_to(harness.service.control_root).as_posix(), path.read_bytes())
        for path in sorted(harness.service.control_root.rglob("*"))
        if path.is_file()
    )

    expected_message = "command IDs" if collision == "command_id" else "idempotency scopes"
    with pytest.raises(ArsError, match=expected_message):
        getattr(harness.service, method_name)([base, second])

    after = tuple(
        (path.relative_to(harness.service.control_root).as_posix(), path.read_bytes())
        for path in sorted(harness.service.control_root.rglob("*"))
        if path.is_file()
    )
    assert after == before


def test_register_batch_prevalidation_accepts_exact_replay_but_rejects_changed_command_identity(tmp_path):
    harness = control_plane(tmp_path)
    register, _, _ = accepted_artefact_commands(harness)
    harness.service.prevalidate_register_artefact_batch([register])
    accepted = harness.service.submit(register)
    before = harness.ledger.snapshot()

    harness.service.prevalidate_register_artefact_batch([deepcopy(register)])
    changed = deepcopy(register)
    changed["command_id"] = "cmd_019fe47a-1091-7000-8000-000000001091"
    with pytest.raises(ConflictError, match="idempotency key"):
        harness.service.prevalidate_register_artefact_batch([changed])
    with pytest.raises(ConflictError, match="idempotency key"):
        harness.service.submit(changed)

    assert harness.ledger.snapshot() == before
    assert harness.receipts.load(str(changed["command_id"])) is None
    assert accepted.status == "accepted"


def test_register_batch_prevalidation_rejects_expected_version_before_publication(tmp_path):
    harness = control_plane(tmp_path)
    register, _, _ = accepted_artefact_commands(harness)
    register["expected_stream_version"] = 1
    before = harness.ledger.snapshot()

    with pytest.raises(ConflictError, match="stream version"):
        harness.service.prevalidate_register_artefact_batch([register])

    assert harness.ledger.snapshot() == before
    assert harness.receipts.load(str(register["command_id"])) is None


def test_owner_activated_agent_grant_records_independent_scientific_review(tmp_path):
    harness = control_plane(tmp_path)
    owner_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact",),
    )
    review_grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        actor_id=ACTORS["actor-b"],
        allowed_actor_classes=("agent",),
        command_types=("RecordScientificReview",),
        grant_id=REVIEW_GRANT_ID,
    )
    manifest = artefact_manifest()
    manifest["producer_actor_id"] = ACTORS["actor-a"]
    register = command(
        command_id="cmd_019fe47a-1020-7000-8000-000000001020",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=owner_grant,
        expected_stream_version=0,
        payload={"new_artefact_id": ARTEFACT_ID, "manifest": manifest},
    )
    review = command(
        command_id="cmd_019fe47a-1021-7000-8000-000000001021",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-b"],
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

    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(review).status == "accepted"
    recorded = tuple(harness.ledger.iter_events())[-1]
    assert recorded["event_type"] == "ScientificReviewRecorded"
    assert recorded["actor_id"] == ACTORS["actor-b"]


def test_register_rejects_caller_selected_accepted_state_without_any_write(tmp_path):
    harness = control_plane(tmp_path)
    register, _, _ = accepted_artefact_commands(harness)
    register["payload"]["manifest"]["authority"]["use_authority"] = "accepted_for_scope"

    receipt = harness.service.submit(register)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "artefact_initial_authority_invalid"
    assert tuple(harness.ledger.iter_events()) == ()
    assert harness.receipts.load(str(register["command_id"])).status == "rejected"
    assert not (harness.objects.control_root / "objects" / "artefact" / ARTEFACT_ID).exists()


def test_use_authority_rejects_without_independent_review_resolver(tmp_path):
    harness = control_plane(tmp_path, clock=lambda: datetime(2026, 8, 8, 20, 0, tzinfo=UTC))
    register, review, use = accepted_artefact_commands(harness)
    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(review).status == "accepted"
    before = harness.ledger.snapshot()
    harness.service.governing_evidence_resolver = None

    receipt = harness.service.submit(use)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "governing_review_resolver_unavailable"
    after = harness.ledger.snapshot()
    assert (after.global_position, after.event_hash) == (before.global_position, before.event_hash)


def test_use_authority_rejects_future_submission_before_resolving_governing_evidence_without_publication(tmp_path):
    trusted_now = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)

    class FutureGoverningEvidenceResolver(StaticGoverningEvidenceResolver):
        def __init__(self) -> None:
            self.evaluation_times: list[datetime] = []

        def resolve(self, reference_id, *, project_id, evaluation_time):
            self.evaluation_times.append(evaluation_time)
            assert evaluation_time == trusted_now + timedelta(seconds=1)
            return super().resolve(reference_id, project_id=project_id, evaluation_time=evaluation_time)

    harness = control_plane(tmp_path, clock=lambda: trusted_now)
    register, review, use = accepted_artefact_commands(harness)
    resolver = FutureGoverningEvidenceResolver()
    harness.service.governing_evidence_resolver = resolver
    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(review).status == "accepted"
    use["submitted_at"] = _utc_z(trusted_now + timedelta(seconds=1))
    before_snapshot = harness.ledger.snapshot()
    before_batches = tuple(harness.ledger.iter_batches())
    before_object = deepcopy(harness.objects.read("artefact", ARTEFACT_ID, 1))

    receipt = harness.service.submit(use)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "artefact_authority_time_invalid"
    assert resolver.evaluation_times == []
    assert harness.receipts.load(receipt.command_id) == receipt
    assert harness.ledger.snapshot() == before_snapshot
    assert tuple(harness.ledger.iter_batches()) == before_batches
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == before_object
