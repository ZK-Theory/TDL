from __future__ import annotations

from copy import deepcopy

from research_system.artefacts.authority import (
    AcceptedContractSubject,
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
)
from research_system.artefacts.use_resolver import predicate_reference
from research_system.canonical import canonical_bytes, sha256_hex
from tests.research_system.factories import ACTORS, PROJECT_ID, activate_lifecycle_grant, control_plane


ARTEFACT_ID = "art_019fe47a-1000-7000-8000-000000001000"
TASK_ID = "tsk_019fe47a-1001-7000-8000-000000001001"
DISPATCH_ID = "dsp_019fe47a-1002-7000-8000-000000001002"
ATTEMPT_ID = "att_019fe47a-1003-7000-8000-000000001003"
CONTEXT_ID = "ctx_019fe47a-1004-7000-8000-000000001004"
REVIEW_ID = "rev_019fe47a-1005-7000-8000-000000001005"
REVIEW_GRANT_ID = "agr_019fe47a-1006-7000-8000-000000001006"
REVIEW_EVIDENCE_ID = "arec_019fe47a-1007-7000-8000-000000001007"
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
    manifest_git_blob="0cd9581ca4427a8515aefd99a7a045d52452ddd3",
    manifest_sha256="0b1f5499d631bfd113dcec0453247d68468a91a2c2bf997b295f6088ff418e6b",
)


class StaticGoverningEvidenceResolver:
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
            "independence_grade": "I1",
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
        "target_stream_id": ARTEFACT_ID,
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


def test_register_review_and_use_authority_are_real_durable_commands(tmp_path):
    harness = control_plane(tmp_path)
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
    harness = control_plane(tmp_path)
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
