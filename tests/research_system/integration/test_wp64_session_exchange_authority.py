from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import shutil

import pytest

from research_system.assurance.external_records import ExternalRecordResolution
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, SchemaError
from research_system.session_exchange import (
    EvidenceArtifact,
    SessionRecordPublicationContext,
    UnresolvedFinding,
    prepare_session_brief,
    record_session_evidence,
)
from research_system.session_exchange.authority import (
    INDEPENDENT_SESSION_REVIEW,
    OWNER_SESSION_ACCEPTANCE_DECISION,
    SessionEvidenceRecordStore,
    SessionRecordLocator,
    SessionRecordSchemaCatalogue,
    compact_record_receipt,
)
from tests.research_system.factories import REPO_ROOT
from tests.research_system.integration.test_authority_grant_source import ACTOR_ID, PROJECT_ID
from tests.research_system.integration.test_scoped_authority_grant_activation import (
    GRANT_ID,
    NOW,
    _activation_command,
    _decision,
    _system,
)


REVIEW_RECORD_ID = "isr_01978abc-6300-7000-8000-000000006300"
OWNER_DECISION_ID = "osd_01978abc-6301-7000-8000-000000006301"
SELF_REVIEW_RECORD_ID = "isr_01978abc-6310-7000-8000-000000006310"
MISSING_REVIEW_RECORD_ID = "isr_01978abc-6311-7000-8000-000000006311"
EVIDENCE_ARTIFACT_ID = "art_01978abc-6302-7000-8000-000000006302"
RETURNED_ARTIFACT_ID = "art_01978abc-6308-7000-8000-000000006308"
TEST_ARTIFACT_ID = "art_01978abc-6309-7000-8000-000000006309"
PRODUCER_ACTOR_ID = "act_01978abc-6312-7000-8000-000000006312"
REVIEWER_ACTOR_ID = "act_01978abc-6313-7000-8000-000000006313"
REVIEW_GRANT_ID = "agr_01978abc-6314-7000-8000-000000006314"
REVIEW_ACTIVATION_DECISION_ID = "arec_01978abc-6315-7000-8000-000000006315"
OWNER_ACTIVATION_DECISION_ID = "arec_01978abc-6316-7000-8000-000000006316"
REVIEW_ACTIVATION_COMMAND_ID = "cmd_01978abc-6317-7000-8000-000000006317"
OWNER_ACTIVATION_COMMAND_ID = "cmd_01978abc-6318-7000-8000-000000006318"
PUBLICATION_CONTEXT_ID = "ctx_01978abc-6319-7000-8000-000000006319"
PRODUCER_LOCATOR = f"ars://actors/{PRODUCER_ACTOR_ID}"
REVIEWER_LOCATOR = f"ars://actors/{REVIEWER_ACTOR_ID}"
ACCEPTOR_LOCATOR = f"ars://actors/{ACTOR_ID}"

pytestmark = pytest.mark.integration


def _binding(control_root, resolver) -> ControlBinding:
    return ControlBinding(
        code_roots=(control_root.parent / "repo",),
        control_root=control_root,
        project_id=PROJECT_ID,
        schema_root=control_root.parent / "repo" / ".research-system" / "schemas",
        store_identity=resolver.expected_store_identity,
        origin_witness_path=resolver.approved_witness_path,
        origin_witness=resolver.approved_witness,
    )


def _subject() -> dict[str, object]:
    return {
        "handoff_id": "hnd_01978abc-6303-7000-8000-000000006303",
        "session_id": "ses_01978abc-6304-7000-8000-000000006304",
        "attempt_id": "att_01978abc-6305-7000-8000-000000006305",
        "task_id": "tsk_01978abc-6306-7000-8000-000000006306",
        "brief_artifact_id": "art_01978abc-6307-7000-8000-000000006307",
        "brief_revision": 1,
        "brief_document_raw_sha256": "1" * 64,
        "brief_raw_sha256": "2" * 64,
        "evidence_artifact_id": EVIDENCE_ARTIFACT_ID,
        "evidence_revision": 1,
        "evidence_subject_raw_sha256": "3" * 64,
        "git_subject": {"commit_sha": "4" * 40, "tree_sha": "5" * 40},
    }


def _review_record(
    subject: dict[str, object] | None = None,
    *,
    record_id: str = REVIEW_RECORD_ID,
) -> dict[str, object]:
    return {
        "schema_id": "ars://wp6-4/independent-session-review-record",
        "schema_version": "1.0.0",
        "record_type": INDEPENDENT_SESSION_REVIEW,
        "review_record_id": record_id,
        "revision": 1,
        "subject": subject or _subject(),
        "reviewer_actor_id": REVIEWER_ACTOR_ID,
        "reviewer_actor_class": "agent",
        "producer_actor_id": PRODUCER_ACTOR_ID,
        "reviewer_identity_locator": REVIEWER_LOCATOR,
        "producer_identity_locator": PRODUCER_LOCATOR,
        "authority_grant_id": REVIEW_GRANT_ID,
        "verdict": "accepted",
        "review_state": "completed",
        "reviewed_at": "2026-07-12T10:00:00Z",
    }


def _owner_decision_record(
    review_resolution,
    subject: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_id": "ars://wp6-4/owner-session-acceptance-decision-record",
        "schema_version": "1.0.0",
        "record_type": OWNER_SESSION_ACCEPTANCE_DECISION,
        "owner_decision_id": OWNER_DECISION_ID,
        "revision": 1,
        "subject": subject or _subject(),
        "acceptor_actor_id": ACTOR_ID,
        "acceptor_actor_class": "human",
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
        "authority_grant_id": GRANT_ID,
        "review_receipt": compact_record_receipt(review_resolution),
        "outcome": "accepted",
        "decision_state": "active",
        "decided_at": "2026-07-12T11:00:00Z",
    }


def _review_resolution() -> ExternalRecordResolution:
    review = _review_record()
    return ExternalRecordResolution(
        record_class=INDEPENDENT_SESSION_REVIEW,
        record_id=REVIEW_RECORD_ID,
        revision=1,
        canonical_sha256=sha256_hex(canonical_bytes(review)),
        record=review,
    )


def test_session_record_schemas_reject_cross_typed_subject_ids_and_loose_timestamps() -> None:
    catalogue = SessionRecordSchemaCatalogue(REPO_ROOT / ".research-system" / "schemas")
    records = (
        (INDEPENDENT_SESSION_REVIEW, REVIEW_RECORD_ID, _review_record(), "reviewed_at"),
        (
            OWNER_SESSION_ACCEPTANCE_DECISION,
            OWNER_DECISION_ID,
            _owner_decision_record(_review_resolution()),
            "decided_at",
        ),
    )
    substitutions = {
        "handoff_id": _subject()["session_id"],
        "session_id": _subject()["attempt_id"],
        "attempt_id": _subject()["task_id"],
        "task_id": _subject()["handoff_id"],
        "brief_artifact_id": _subject()["session_id"],
        "evidence_artifact_id": _subject()["task_id"],
    }

    for record_class, record_id, record, timestamp_field in records:
        catalogue.validate(record_class, record_id, record)
        for field, invalid_value in substitutions.items():
            invalid = deepcopy(record)
            invalid["subject"][field] = invalid_value
            with pytest.raises(SchemaError):
                catalogue.validate(record_class, record_id, invalid)
        invalid = deepcopy(record)
        invalid[timestamp_field] = "2026-07-12T10:00:00.1234567Z"
        with pytest.raises(SchemaError):
            catalogue.validate(record_class, record_id, invalid)


@pytest.mark.parametrize(
    "schema_filename",
    [
        "independent-session-review-record.schema.json",
        "owner-session-acceptance-decision-record.schema.json",
    ],
)
@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("content", "Git blob mismatch"),
        ("crlf", "not exact UTF-8/LF"),
        ("extra-newline", "not exact UTF-8/LF"),
    ],
)
def test_session_record_catalogue_rejects_unpinned_or_non_lf_schema_bytes(
    tmp_path,
    schema_filename: str,
    mutation: str,
    error: str,
) -> None:
    schema_root = tmp_path / "schemas"
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas" / "wp6-4", schema_root / "wp6-4")
    path = schema_root / "wp6-4" / schema_filename
    raw = path.read_bytes()
    if mutation == "content":
        raw = raw.replace(b'  "$schema":', b'   "$schema":', 1)
    elif mutation == "crlf":
        raw = raw.replace(b"\n", b"\r\n")
    else:
        raw += b"\n"
    path.write_bytes(raw)

    with pytest.raises(SchemaError, match=error):
        SessionRecordSchemaCatalogue(schema_root)


def _policy_grant(
    schemas,
    *,
    grant_id: str,
    actor_id: str,
    actor_class: str,
    policy_action_type: str,
    policy_schema_id: str,
    risk: str,
) -> dict[str, object]:
    policy = schemas.resolve_identity(policy_schema_id, "1.0.0")
    return {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.0.0",
        "authority_grant_id": grant_id,
        "actor_id": actor_id,
        "allowed_actor_classes": [actor_class],
        "allowed_commands": [],
        "allowed_policy_actions": [
            {
                "policy_action_type": policy_action_type,
                "schema_id": policy.schema_id,
                "schema_version": policy.schema_version,
                "schema_sha256": policy.sha256,
            }
        ],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "artefact", "id": EVIDENCE_ARTIFACT_ID},
        },
        "risk_ceiling": risk,
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }


def _activate_grant(
    resolver,
    schemas,
    objects,
    service,
    grant: dict[str, object],
    *,
    decision_id: str,
    command_id: str,
) -> None:
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=decision_id,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", decision_id, 1, decision)
    command = _activation_command(
        resolver,
        schemas,
        grant,
        decision,
        command_id=command_id,
    )
    command["target_stream_id"] = grant["authority_grant_id"]
    command["idempotency_key"] = f"activate-{grant['authority_grant_id']}"
    command["correlation_id"] = f"wp64-{grant['authority_grant_id']}"
    assert service.submit(command).status == "accepted"


def _activate_session_authorities(schemas, resolver, objects, service) -> None:
    review_grant = _policy_grant(
        schemas,
        grant_id=REVIEW_GRANT_ID,
        actor_id=REVIEWER_ACTOR_ID,
        actor_class="agent",
        policy_action_type="publish_owner_operated_session_review",
        policy_schema_id="ars://core/policy-action/PublishOwnerOperatedSessionReview",
        risk="R2",
    )
    owner_grant = _policy_grant(
        schemas,
        grant_id=GRANT_ID,
        actor_id=ACTOR_ID,
        actor_class="human",
        policy_action_type="accept_owner_operated_session_evidence",
        policy_schema_id="ars://core/policy-action/AcceptOwnerOperatedSessionEvidence",
        risk="R3",
    )
    _activate_grant(
        resolver,
        schemas,
        objects,
        service,
        review_grant,
        decision_id=REVIEW_ACTIVATION_DECISION_ID,
        command_id=REVIEW_ACTIVATION_COMMAND_ID,
    )
    _activate_grant(
        resolver,
        schemas,
        objects,
        service,
        owner_grant,
        decision_id=OWNER_ACTIVATION_DECISION_ID,
        command_id=OWNER_ACTIVATION_COMMAND_ID,
    )


def _publication_context(
    binding: ControlBinding,
    resolver,
    record: dict[str, object],
    *,
    record_class: str,
    record_id: str,
) -> SessionRecordPublicationContext:
    if record_class == INDEPENDENT_SESSION_REVIEW:
        actor_id = REVIEWER_ACTOR_ID
        actor_class = "agent"
        grant_id = REVIEW_GRANT_ID
        risk = "R2"
        occurred_at = str(record["reviewed_at"])
    else:
        actor_id = ACTOR_ID
        actor_class = "human"
        grant_id = GRANT_ID
        risk = "R3"
        occurred_at = str(record["decided_at"])
    return SessionRecordPublicationContext(
        caller_actor_id=actor_id,
        caller_actor_class=actor_class,
        authority_grant_id=grant_id,
        record_action="create",
        record_class=record_class,
        record_id=record_id,
        revision=1,
        expected_previous_revision=0,
        project_id=PROJECT_ID,
        store_identity=str(binding.store_identity),
        authority_root=resolver.administration_context().root_grant_id,
        canonical_sha256=sha256_hex(canonical_bytes(record)),
        task_id=str(record["subject"]["task_id"]),
        session_id=PUBLICATION_CONTEXT_ID,
        relationship_record_id=None,
        required_risk=risk,
        occurred_at=occurred_at,
    )


def _publish_review(records, binding, resolver, subject):
    review = _review_record(subject)
    receipt = records.write(
        record_class=INDEPENDENT_SESSION_REVIEW,
        record_id=REVIEW_RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=review,
        publication_context=_publication_context(
            binding,
            resolver,
            review,
            record_class=INDEPENDENT_SESSION_REVIEW,
            record_id=REVIEW_RECORD_ID,
        ),
    )
    resolution = records.resolve(SessionRecordLocator(INDEPENDENT_SESSION_REVIEW, REVIEW_RECORD_ID))
    assert resolution.canonical_sha256 == receipt.canonical_sha256
    return resolution


def test_session_records_require_governed_publication_and_block_actor_substitution(
    tmp_path,
) -> None:
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    binding = _binding(control_root, resolver)
    _activate_session_authorities(schemas, resolver, objects, service)
    records = SessionEvidenceRecordStore(binding, clock=lambda: NOW)
    review = _review_record()

    with pytest.raises(SchemaError, match="publication context is required"):
        records.write(
            record_class=INDEPENDENT_SESSION_REVIEW,
            record_id=REVIEW_RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=review,
        )
    assert objects.latest_revision(INDEPENDENT_SESSION_REVIEW, REVIEW_RECORD_ID) is None

    context = _publication_context(
        binding,
        resolver,
        review,
        record_class=INDEPENDENT_SESSION_REVIEW,
        record_id=REVIEW_RECORD_ID,
    )
    substituted = replace(context, caller_actor_id=PRODUCER_ACTOR_ID)
    with pytest.raises(SchemaError, match="caller or authority"):
        records.write(
            record_class=INDEPENDENT_SESSION_REVIEW,
            record_id=REVIEW_RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=review,
            publication_context=substituted,
        )
    assert objects.latest_revision(INDEPENDENT_SESSION_REVIEW, REVIEW_RECORD_ID) is None

    cross_typed_subject = deepcopy(review)
    cross_typed_subject["subject"]["handoff_id"] = str(cross_typed_subject["subject"]["session_id"])
    with pytest.raises(SchemaError):
        records.write(
            record_class=INDEPENDENT_SESSION_REVIEW,
            record_id=REVIEW_RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=cross_typed_subject,
            publication_context=_publication_context(
                binding,
                resolver,
                cross_typed_subject,
                record_class=INDEPENDENT_SESSION_REVIEW,
                record_id=REVIEW_RECORD_ID,
            ),
        )
    assert objects.latest_revision(INDEPENDENT_SESSION_REVIEW, REVIEW_RECORD_ID) is None

    self_review = _review_record(record_id=SELF_REVIEW_RECORD_ID)
    self_review["producer_actor_id"] = REVIEWER_ACTOR_ID
    self_review["producer_identity_locator"] = REVIEWER_LOCATOR
    self_context = _publication_context(
        binding,
        resolver,
        self_review,
        record_class=INDEPENDENT_SESSION_REVIEW,
        record_id=SELF_REVIEW_RECORD_ID,
    )
    with pytest.raises(SchemaError, match="self-review"):
        records.write(
            record_class=INDEPENDENT_SESSION_REVIEW,
            record_id=SELF_REVIEW_RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=self_review,
            publication_context=self_context,
        )
    assert objects.latest_revision(INDEPENDENT_SESSION_REVIEW, SELF_REVIEW_RECORD_ID) is None

    review_resolution = _publish_review(records, binding, resolver, _subject())
    assert review_resolution.record == review
    assert records.catalogue.record_classes == (
        INDEPENDENT_SESSION_REVIEW,
        OWNER_SESSION_ACCEPTANCE_DECISION,
    )

    owner_decision = _owner_decision_record(review_resolution)
    owner_context = _publication_context(
        binding,
        resolver,
        owner_decision,
        record_class=OWNER_SESSION_ACCEPTANCE_DECISION,
        record_id=OWNER_DECISION_ID,
    )
    substituted_owner = replace(
        owner_context,
        caller_actor_id=REVIEWER_ACTOR_ID,
        caller_actor_class="agent",
        authority_grant_id=REVIEW_GRANT_ID,
    )
    with pytest.raises(SchemaError, match="caller or authority"):
        records.write(
            record_class=OWNER_SESSION_ACCEPTANCE_DECISION,
            record_id=OWNER_DECISION_ID,
            revision=1,
            expected_previous_revision=0,
            record=owner_decision,
            publication_context=substituted_owner,
        )
    assert objects.latest_revision(OWNER_SESSION_ACCEPTANCE_DECISION, OWNER_DECISION_ID) is None

    changed = deepcopy(review)
    changed["verdict"] = "rework_required"
    with pytest.raises(ConflictError, match="different content"):
        records.write(
            record_class=INDEPENDENT_SESSION_REVIEW,
            record_id=REVIEW_RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=changed,
            publication_context=_publication_context(
                binding,
                resolver,
                changed,
                record_class=INDEPENDENT_SESSION_REVIEW,
                record_id=REVIEW_RECORD_ID,
            ),
        )


def test_session_evidence_advances_only_from_governed_distinct_party_records(
    tmp_path,
) -> None:
    control_root, schemas, resolver, _, objects, service = _system(tmp_path)
    binding = _binding(control_root, resolver)
    _activate_session_authorities(schemas, resolver, objects, service)
    records = SessionEvidenceRecordStore(binding, clock=lambda: NOW)
    subject = _subject()

    brief = prepare_session_brief(
        control_root,
        brief_artifact_id=str(subject["brief_artifact_id"]),
        handoff_id=str(subject["handoff_id"]),
        session_id=str(subject["session_id"]),
        attempt_id=str(subject["attempt_id"]),
        task_id=str(subject["task_id"]),
        requested_role="implementation producer",
        assurance_requirement="independent review followed by owner acceptance",
        operator_identity_locator=f"ars://actors/{ACTOR_ID}",
        producer_identity_locator=PRODUCER_LOCATOR,
        session_family="codex_standalone",
        git_commit_sha=str(subject["git_subject"]["commit_sha"]),
        git_tree_sha=str(subject["git_subject"]["tree_sha"]),
        brief_bytes=b"Return exact implementation and test evidence.",
        prepared_at="2026-07-12T09:00:00Z",
    )
    returned_path = tmp_path / "returned.txt"
    test_path = tmp_path / "test.txt"
    returned_path.write_bytes(b"implementation evidence\n")
    test_path.write_bytes(b"targeted tests passed\n")
    common = {
        "evidence_artifact_id": EVIDENCE_ARTIFACT_ID,
        "brief_artifact_id": str(subject["brief_artifact_id"]),
        "handoff_id": str(subject["handoff_id"]),
        "session_id": str(subject["session_id"]),
        "attempt_id": str(subject["attempt_id"]),
        "producer_identity_locator": PRODUCER_LOCATOR,
        "reviewer_identity_locator": REVIEWER_LOCATOR,
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
        "returned_artifacts": (
            EvidenceArtifact(
                artefact_id=RETURNED_ARTIFACT_ID,
                locator="file:///returned.txt",
                path=returned_path,
                media_type="text/plain",
            ),
        ),
        "test_evidence": (
            EvidenceArtifact(
                artefact_id=TEST_ARTIFACT_ID,
                locator="file:///test.txt",
                path=test_path,
                media_type="text/plain",
            ),
        ),
        "producer_verdict": "completed",
        "unresolved_findings": (UnresolvedFinding("WP64-NOTE", "note", "Owner acceptance remains separate."),),
    }

    revision_1 = record_session_evidence(
        control_root,
        expected_previous_revision=0,
        recorded_at="2026-07-12T09:30:00Z",
        **common,
    )
    assert revision_1.document["revision"] == 1
    assert revision_1.document["document_state"] == "produced_unreviewed"

    missing_locator = SessionRecordLocator(
        INDEPENDENT_SESSION_REVIEW,
        MISSING_REVIEW_RECORD_ID,
    )
    before = set((control_root / "objects" / "artefact" / EVIDENCE_ARTIFACT_ID).glob("*.json"))
    with pytest.raises(ArsError, match="no persisted revision"):
        record_session_evidence(
            control_root,
            expected_previous_revision=1,
            recorded_at="2026-07-12T10:30:00Z",
            authority_binding=binding,
            review_record=missing_locator,
            **common,
        )
    assert set((control_root / "objects" / "artefact" / EVIDENCE_ARTIFACT_ID).glob("*.json")) == before

    exact_subject = {
        **subject,
        "brief_document_raw_sha256": sha256_hex(canonical_bytes(brief.document)),
        "brief_raw_sha256": brief.document["brief"]["raw_sha256"],
        "evidence_subject_raw_sha256": revision_1.document["evidence_subject_raw_sha256"],
    }
    review_resolution = _publish_review(records, binding, resolver, exact_subject)
    review_locator = SessionRecordLocator(INDEPENDENT_SESSION_REVIEW, REVIEW_RECORD_ID)
    revision_2 = record_session_evidence(
        control_root,
        expected_previous_revision=1,
        recorded_at="2026-07-12T10:30:00Z",
        authority_binding=binding,
        review_record=review_locator,
        **common,
    )
    assert revision_2.document["revision"] == 2
    assert revision_2.document["document_state"] == ("independently_reviewed_pending_owner_acceptance")
    assert revision_2.document["supersedes_document_raw_sha256"] == revision_1.raw_sha256
    review_evidence = revision_2.document["review"]["evidence"]
    assert review_evidence["record"]["canonical_sha256"] == review_resolution.canonical_sha256
    assert review_evidence["record"]["store_identity"] == binding.store_identity
    assert review_evidence["authority"]["actor_id"] == REVIEWER_ACTOR_ID
    assert review_evidence["authority"]["subject_scope"] == {
        "kind": "artefact",
        "id": EVIDENCE_ARTIFACT_ID,
    }
    revision_2_retry = record_session_evidence(
        control_root,
        expected_previous_revision=1,
        recorded_at="2026-07-12T10:30:00Z",
        authority_binding=binding,
        review_record=review_locator,
        **common,
    )
    assert revision_2_retry.raw_sha256 == revision_2.raw_sha256
    assert revision_2_retry.document == revision_2.document

    owner_decision = _owner_decision_record(review_resolution, exact_subject)
    owner_receipt = records.write(
        record_class=OWNER_SESSION_ACCEPTANCE_DECISION,
        record_id=OWNER_DECISION_ID,
        revision=1,
        expected_previous_revision=0,
        record=owner_decision,
        publication_context=_publication_context(
            binding,
            resolver,
            owner_decision,
            record_class=OWNER_SESSION_ACCEPTANCE_DECISION,
            record_id=OWNER_DECISION_ID,
        ),
    )
    owner_locator = SessionRecordLocator(
        OWNER_SESSION_ACCEPTANCE_DECISION,
        OWNER_DECISION_ID,
    )
    revision_3 = record_session_evidence(
        control_root,
        expected_previous_revision=2,
        recorded_at="2026-07-12T11:30:00Z",
        authority_binding=binding,
        review_record=review_locator,
        owner_decision_record=owner_locator,
        **common,
    )
    assert revision_3.document["revision"] == 3
    assert revision_3.document["document_state"] == "owner_accepted"
    assert revision_3.document["supersedes_document_raw_sha256"] == revision_2.raw_sha256
    assert revision_3.document["review"] == revision_2.document["review"]
    assert (
        revision_3.document["acceptance"]["evidence"]["decision"]["canonical_sha256"] == owner_receipt.canonical_sha256
    )
    authority_evidence = revision_3.document["acceptance"]["evidence"]["authority"]
    assert authority_evidence["status"] == "active"
    assert authority_evidence["actor_id"] == ACTOR_ID
    assert authority_evidence["subject_scope"] == {
        "kind": "artefact",
        "id": EVIDENCE_ARTIFACT_ID,
    }

    retry = record_session_evidence(
        control_root,
        expected_previous_revision=2,
        recorded_at="2026-07-12T11:30:00Z",
        authority_binding=binding,
        review_record=review_locator,
        owner_decision_record=owner_locator,
        **common,
    )
    assert retry.raw_sha256 == revision_3.raw_sha256
    assert retry.document == revision_3.document
