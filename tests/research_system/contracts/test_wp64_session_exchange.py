from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, SchemaError


BRIEF_ARTIFACT_ID = "art_01978abc-6400-7000-8000-000000000001"
EVIDENCE_ARTIFACT_ID = "art_01978abc-6400-7000-8000-000000000006"
HANDOFF_ID = "hnd_01978abc-6400-7000-8000-000000000002"
SESSION_ID = "ses_01978abc-6400-7000-8000-000000000003"
ATTEMPT_ID = "att_01978abc-6400-7000-8000-000000000004"
TASK_ID = "tsk_01978abc-6400-7000-8000-000000000005"
PRODUCER_LOCATOR = "ars://actors/producer-fixture"
REVIEWER_LOCATOR = "ars://actors/reviewer-fixture"
ACCEPTOR_LOCATOR = "ars://actors/acceptor-fixture"
AUTHORITY_LOCATOR = "ars://authority/owner-acceptance-fixture"


def _external_session_subject(brief):
    return {
        "handoff_id": brief.document["handoff_id"],
        "session_id": brief.document["session_id"],
        "attempt_id": brief.document["attempt_id"],
        "task_id": brief.document["task_id"],
        "brief_artifact_id": brief.document["brief_artifact_id"],
        "brief_revision": brief.document["revision"],
        "brief_document_raw_sha256": brief.raw_sha256,
        "brief_raw_sha256": brief.document["brief"]["raw_sha256"],
        "evidence_artifact_id": EVIDENCE_ARTIFACT_ID,
        "git_subject": brief.document["git_subject"],
    }


def _set_nested(document, path, value):
    cursor = document
    for field in path[:-1]:
        cursor = cursor[field]
    cursor[path[-1]] = value


def _accepted_external_fixture(
    control_root,
    brief,
    *,
    review_mutation=None,
    decision_mutation=None,
    authority_mutation=None,
    noncanonical_record=None,
    caller_verdict="accepted",
    caller_authority_status="active",
):
    from research_system.session_exchange import ExternalEvidence, IndependentReviewEvidence, OwnerAcceptanceEvidence

    subject = _external_session_subject(brief)
    review_document = {
        "schema_id": "ars://wp6-4/independent-session-review-record",
        "schema_version": "1.0.0",
        "record_type": "independent_session_review",
        "subject": copy.deepcopy(subject),
        "reviewer_identity_locator": REVIEWER_LOCATOR,
        "producer_identity_locator": PRODUCER_LOCATOR,
        "verdict": "accepted",
        "reviewed_at": "2026-08-04T09:30:00Z",
    }
    if review_mutation is not None:
        _set_nested(review_document, *review_mutation)
    review_path = control_root / "independent-review.json"
    review_raw = canonical_bytes(review_document)
    if noncanonical_record == "review":
        review_raw += b"\n"
    review_path.write_bytes(review_raw)

    decision_document = {
        "schema_id": "ars://wp6-4/owner-session-acceptance-decision-record",
        "schema_version": "1.0.0",
        "record_type": "owner_session_acceptance_decision",
        "subject": copy.deepcopy(subject),
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
        "authority_locator": AUTHORITY_LOCATOR,
        "review_record_raw_sha256": sha256_hex(review_raw),
        "outcome": "accepted",
        "decided_at": "2026-08-04T09:45:00Z",
    }
    if decision_mutation is not None:
        _set_nested(decision_document, *decision_mutation)
    decision_path = control_root / "owner-decision.json"
    decision_raw = canonical_bytes(decision_document)
    if noncanonical_record == "decision":
        decision_raw += b"\n"
    decision_path.write_bytes(decision_raw)

    authority_document = {
        "schema_id": "ars://wp6-4/owner-session-acceptance-authority-record",
        "schema_version": "1.0.0",
        "record_type": "owner_session_acceptance_authority",
        "subject": copy.deepcopy(subject),
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
        "authority_locator": AUTHORITY_LOCATOR,
        "permitted_action": "accept_owner_operated_session_evidence",
        "status": "active",
        "valid_from": "2026-08-04T09:45:00Z",
        "valid_until": "2026-08-04T11:00:00Z",
    }
    if authority_mutation is not None:
        _set_nested(authority_document, *authority_mutation)
    authority_path = control_root / "owner-authority.json"
    authority_raw = canonical_bytes(authority_document)
    if noncanonical_record == "authority":
        authority_raw += b"\n"
    authority_path.write_bytes(authority_raw)

    return {
        "review_evidence": IndependentReviewEvidence(
            reviewer_identity_locator=REVIEWER_LOCATOR,
            verdict=caller_verdict,
            record=ExternalEvidence(
                record_locator="repo://independent-review.json",
                path=review_path,
                media_type="application/json",
            ),
        ),
        "acceptance_evidence": OwnerAcceptanceEvidence(
            acceptor_identity_locator=ACCEPTOR_LOCATOR,
            authority_locator=AUTHORITY_LOCATOR,
            authority_status=caller_authority_status,
            decision=ExternalEvidence(
                record_locator="repo://owner-decision.json",
                path=decision_path,
                media_type="application/json",
            ),
            authority=ExternalEvidence(
                record_locator="repo://owner-authority.json",
                path=authority_path,
                media_type="application/json",
            ),
        ),
        "review_path": review_path,
        "decision_path": decision_path,
        "authority_path": authority_path,
    }


def test_prepare_session_brief_publishes_exact_provider_free_subject(tmp_path):
    from research_system.session_exchange import prepare_session_brief

    brief_bytes = b"Review the exact candidate without invoking a provider.\n"
    published = prepare_session_brief(
        tmp_path,
        brief_artifact_id=BRIEF_ARTIFACT_ID,
        handoff_id=HANDOFF_ID,
        session_id=SESSION_ID,
        attempt_id=ATTEMPT_ID,
        task_id=TASK_ID,
        requested_role="independent_exact_subject_review",
        assurance_requirement="output_provenance_and_independent_review",
        operator_identity_locator="ars://actors/operator-fixture",
        producer_identity_locator=PRODUCER_LOCATOR,
        session_family="codex_standalone",
        git_commit_sha="a" * 40,
        git_tree_sha="b" * 40,
        brief_bytes=brief_bytes,
        prepared_at="2026-08-04T09:00:00Z",
    )

    assert published.document["document_state"] == "prepared_for_owner_operated_session"
    assert published.document["brief"]["raw_sha256"] == sha256_hex(brief_bytes)
    assert published.document["git_subject"] == {
        "commit_sha": "a" * 40,
        "tree_sha": "b" * 40,
    }
    assert "review" not in published.document
    assert "acceptance" not in published.document
    assert published.path.read_bytes() == canonical_bytes(published.document)
    assert published.raw_sha256 == sha256_hex(published.path.read_bytes())


def test_record_session_evidence_binds_exact_brief_artifacts_and_pending_authorities(tmp_path):
    from research_system.session_exchange import (
        EvidenceArtifact,
        UnresolvedFinding,
        prepare_session_brief,
        record_session_evidence,
    )

    brief = prepare_session_brief(
        tmp_path,
        brief_artifact_id=BRIEF_ARTIFACT_ID,
        handoff_id=HANDOFF_ID,
        session_id=SESSION_ID,
        attempt_id=ATTEMPT_ID,
        task_id=TASK_ID,
        requested_role="independent_exact_subject_review",
        assurance_requirement="output_provenance_and_independent_review",
        operator_identity_locator="ars://actors/operator-fixture",
        producer_identity_locator=PRODUCER_LOCATOR,
        session_family="codex_standalone",
        git_commit_sha="a" * 40,
        git_tree_sha="b" * 40,
        brief_bytes=b"Review the exact candidate without invoking a provider.\n",
        prepared_at="2026-08-04T09:00:00Z",
    )
    returned_path = tmp_path / "candidate.patch"
    returned_path.write_bytes(b"exact candidate bytes\n")
    tests_path = tmp_path / "focused-tests.txt"
    tests_path.write_bytes(b"2 passed\n")

    published = record_session_evidence(
        tmp_path,
        evidence_artifact_id=EVIDENCE_ARTIFACT_ID,
        brief_artifact_id=BRIEF_ARTIFACT_ID,
        handoff_id=HANDOFF_ID,
        session_id=SESSION_ID,
        attempt_id=ATTEMPT_ID,
        producer_identity_locator=PRODUCER_LOCATOR,
        reviewer_identity_locator=REVIEWER_LOCATOR,
        acceptor_identity_locator=ACCEPTOR_LOCATOR,
        acceptance_authority_locator=AUTHORITY_LOCATOR,
        returned_artifacts=(
            EvidenceArtifact(
                artefact_id="art_01978abc-6400-7000-8000-000000000007",
                locator="repo://candidate.patch",
                path=returned_path,
                media_type="text/x-diff",
            ),
        ),
        test_evidence=(
            EvidenceArtifact(
                artefact_id="art_01978abc-6400-7000-8000-000000000008",
                locator="repo://focused-tests.txt",
                path=tests_path,
                media_type="text/plain",
            ),
        ),
        producer_verdict="completed",
        unresolved_findings=(
            UnresolvedFinding(finding_id="MECH-1", severity="minor", summary="Owner acceptance remains pending."),
        ),
        recorded_at="2026-08-04T09:30:00Z",
    )

    assert published.document["document_state"] == "produced_unreviewed"
    assert published.document["handoff_id"] == HANDOFF_ID
    assert published.document["session_id"] == SESSION_ID
    assert published.document["attempt_id"] == ATTEMPT_ID
    assert published.document["brief_subject"] == {
        "brief_artifact_id": BRIEF_ARTIFACT_ID,
        "revision": 1,
        "document_raw_sha256": brief.raw_sha256,
        "brief_raw_sha256": brief.document["brief"]["raw_sha256"],
        "git_subject": {"commit_sha": "a" * 40, "tree_sha": "b" * 40},
    }
    assert published.document["returned_artifacts"][0]["raw_sha256"] == sha256_hex(returned_path.read_bytes())
    assert published.document["test_evidence"][0]["raw_sha256"] == sha256_hex(tests_path.read_bytes())
    assert published.document["review"] == {
        "reviewer_identity_locator": REVIEWER_LOCATOR,
        "status": "pending_independent_review",
        "verdict": None,
        "evidence": None,
    }
    assert published.document["acceptance"] == {
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
        "authority_locator": AUTHORITY_LOCATOR,
        "authority_status": "unverified",
        "status": "pending_owner_acceptance",
        "outcome": None,
        "evidence": None,
    }
    assert published.document["unresolved_findings"] == [
        {
            "finding_id": "MECH-1",
            "severity": "minor",
            "status": "unresolved",
            "summary": "Owner acceptance remains pending.",
        }
    ]
    assert published.path.read_bytes() == canonical_bytes(published.document)
    assert published.raw_sha256 == sha256_hex(published.path.read_bytes())


def test_external_review_and_owner_records_are_required_before_recorded_acceptance(tmp_path):
    from research_system.session_exchange import (
        EvidenceArtifact,
        prepare_session_brief,
        record_session_evidence,
    )

    brief = prepare_session_brief(
        tmp_path,
        brief_artifact_id=BRIEF_ARTIFACT_ID,
        handoff_id=HANDOFF_ID,
        session_id=SESSION_ID,
        attempt_id=ATTEMPT_ID,
        task_id=TASK_ID,
        requested_role="independent_exact_subject_review",
        assurance_requirement="output_provenance_and_independent_review",
        operator_identity_locator="ars://actors/operator-fixture",
        producer_identity_locator=PRODUCER_LOCATOR,
        session_family="codex_standalone",
        git_commit_sha="a" * 40,
        git_tree_sha="b" * 40,
        brief_bytes=b"Review the exact candidate without invoking a provider.\n",
        prepared_at="2026-08-04T09:00:00Z",
    )
    returned_path = tmp_path / "candidate.patch"
    returned_path.write_bytes(b"exact candidate bytes\n")
    tests_path = tmp_path / "focused-tests.txt"
    tests_path.write_bytes(b"2 passed\n")
    external = _accepted_external_fixture(tmp_path, brief)

    published = record_session_evidence(
        tmp_path,
        evidence_artifact_id=EVIDENCE_ARTIFACT_ID,
        brief_artifact_id=BRIEF_ARTIFACT_ID,
        handoff_id=HANDOFF_ID,
        session_id=SESSION_ID,
        attempt_id=ATTEMPT_ID,
        producer_identity_locator=PRODUCER_LOCATOR,
        reviewer_identity_locator=REVIEWER_LOCATOR,
        acceptor_identity_locator=ACCEPTOR_LOCATOR,
        acceptance_authority_locator=AUTHORITY_LOCATOR,
        returned_artifacts=(
            EvidenceArtifact(
                artefact_id="art_01978abc-6400-7000-8000-000000000007",
                locator="repo://candidate.patch",
                path=returned_path,
                media_type="text/x-diff",
            ),
        ),
        test_evidence=(
            EvidenceArtifact(
                artefact_id="art_01978abc-6400-7000-8000-000000000008",
                locator="repo://focused-tests.txt",
                path=tests_path,
                media_type="text/plain",
            ),
        ),
        producer_verdict="completed",
        unresolved_findings=(),
        review_evidence=external["review_evidence"],
        acceptance_evidence=external["acceptance_evidence"],
        recorded_at="2026-08-04T10:00:00Z",
    )

    assert published.document["document_state"] == "owner_accepted"
    assert published.document["review"]["verdict"] == "accepted"
    assert published.document["review"]["reviewed_at"] == "2026-08-04T09:30:00Z"
    assert published.document["review"]["evidence"]["raw_sha256"] == sha256_hex(external["review_path"].read_bytes())
    assert published.document["acceptance"]["status"] == "owner_acceptance_recorded"
    assert published.document["acceptance"]["decided_at"] == "2026-08-04T09:45:00Z"
    assert published.document["acceptance"]["authority_valid_from"] == "2026-08-04T09:45:00Z"
    assert published.document["acceptance"]["authority_valid_until"] == "2026-08-04T11:00:00Z"
    assert published.document["acceptance"]["evidence"]["decision"]["raw_sha256"] == sha256_hex(
        external["decision_path"].read_bytes()
    )
    assert published.document["acceptance"]["evidence"]["authority"]["raw_sha256"] == sha256_hex(
        external["authority_path"].read_bytes()
    )
    assert published.document["mechanics_scope"] == "fixture_or_operator_supplied_inputs_only"


def test_caller_labels_cannot_promote_contradictory_wrong_subject_records(tmp_path):
    from research_system.session_exchange import record_session_evidence

    brief = _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    external = _accepted_external_fixture(
        tmp_path,
        brief,
        review_mutation=(
            ("subject", "session_id"),
            "ses_01978abc-6400-7000-8000-000000000099",
        ),
        decision_mutation=(("outcome",), "rejected"),
        authority_mutation=(("status",), "inactive"),
    )
    kwargs.update(review_evidence=external["review_evidence"], acceptance_evidence=external["acceptance_evidence"])

    with pytest.raises(ConflictError, match="does not bind the exact session subject"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


@pytest.mark.parametrize(
    ("record_name", "mutation", "caller_verdict", "caller_authority_status", "error_type", "error_match"),
    [
        (
            "review",
            (("subject", "attempt_id"), "att_01978abc-6400-7000-8000-000000000099"),
            "accepted",
            "active",
            ConflictError,
            "exact session subject",
        ),
        (
            "review",
            (("reviewer_identity_locator",), "ars://actors/foreign-reviewer"),
            "accepted",
            "active",
            ConflictError,
            "wrong reviewer",
        ),
        (
            "review",
            (("producer_identity_locator",), "ars://actors/foreign-producer"),
            "accepted",
            "active",
            ConflictError,
            "wrong producer",
        ),
        (
            "review",
            (("subject", "git_subject", "commit_sha"), "c" * 40),
            "accepted",
            "active",
            ConflictError,
            "exact session subject",
        ),
        (
            "review",
            (("subject", "evidence_artifact_id"), "art_01978abc-6400-7000-8000-000000000099"),
            "accepted",
            "active",
            ConflictError,
            "exact session subject",
        ),
        (
            "review",
            (("verdict",), "rejected"),
            "accepted",
            "active",
            ConflictError,
            "caller verdict contradicts",
        ),
        (
            "review",
            (("reviewed_at",), "2026-08-04T08:59:59Z"),
            "accepted",
            "active",
            SchemaError,
            "stale",
        ),
        (
            "review",
            (("reviewed_at",), "2026-08-04T10:00:01Z"),
            "accepted",
            "active",
            SchemaError,
            "future",
        ),
        (
            "review",
            (("unexpected",), True),
            "accepted",
            "active",
            SchemaError,
            "invalid independent review evidence",
        ),
        (
            "decision",
            (("subject", "handoff_id"), "hnd_01978abc-6400-7000-8000-000000000099"),
            "accepted",
            "active",
            ConflictError,
            "exact session subject",
        ),
        (
            "decision",
            (("acceptor_identity_locator",), "ars://actors/foreign-acceptor"),
            "accepted",
            "active",
            ConflictError,
            "wrong acceptor",
        ),
        (
            "decision",
            (("authority_locator",), "ars://authority/foreign"),
            "accepted",
            "active",
            ConflictError,
            "wrong authority",
        ),
        (
            "decision",
            (("review_record_raw_sha256",), "f" * 64),
            "accepted",
            "active",
            ConflictError,
            "exact review record",
        ),
        (
            "decision",
            (("outcome",), "rejected"),
            "accepted",
            "active",
            SchemaError,
            "does not accept",
        ),
        (
            "decision",
            (("decided_at",), "2026-08-04T09:30:00Z"),
            "accepted",
            "active",
            SchemaError,
            "later than",
        ),
        (
            "decision",
            (("decided_at",), "2026-08-04T10:00:01Z"),
            "accepted",
            "active",
            SchemaError,
            "future",
        ),
        (
            "decision",
            (("unexpected",), True),
            "accepted",
            "active",
            SchemaError,
            "invalid owner acceptance decision",
        ),
        (
            "authority",
            (("subject", "brief_artifact_id"), "art_01978abc-6400-7000-8000-000000000099"),
            "accepted",
            "active",
            ConflictError,
            "exact session subject",
        ),
        (
            "authority",
            (("authority_locator",), "ars://authority/foreign"),
            "accepted",
            "active",
            ConflictError,
            "wrong authority",
        ),
        (
            "authority",
            (("acceptor_identity_locator",), "ars://actors/foreign-acceptor"),
            "accepted",
            "active",
            ConflictError,
            "wrong acceptor",
        ),
        (
            "authority",
            (("status",), "inactive"),
            "accepted",
            "active",
            ConflictError,
            "caller authority status contradicts",
        ),
        (
            "authority",
            (("status",), "inactive"),
            "accepted",
            "inactive",
            SchemaError,
            "requires active",
        ),
        (
            "authority",
            (("valid_until",), "2026-08-04T10:00:00Z"),
            "accepted",
            "active",
            SchemaError,
            "expired",
        ),
        (
            "authority",
            (("valid_from",), "2026-08-04T09:45:01Z"),
            "accepted",
            "active",
            SchemaError,
            "not yet effective",
        ),
        (
            "authority",
            (("unexpected",), True),
            "accepted",
            "active",
            SchemaError,
            "invalid owner acceptance authority",
        ),
    ],
    ids=[
        "review-wrong-subject",
        "review-wrong-actor",
        "review-wrong-producer",
        "review-wrong-git-subject",
        "review-wrong-evidence-artifact",
        "review-caller-relabel",
        "review-stale-before-brief",
        "review-future",
        "review-open-record",
        "decision-wrong-subject",
        "decision-wrong-actor",
        "decision-wrong-authority",
        "decision-wrong-review",
        "decision-rejected",
        "decision-not-after-review",
        "decision-future",
        "decision-open-record",
        "authority-wrong-subject",
        "authority-wrong-locator",
        "authority-wrong-acceptor",
        "authority-caller-relabel",
        "authority-inactive",
        "authority-expired-at-boundary",
        "authority-not-yet-effective",
        "authority-open-record",
    ],
)
def test_external_record_semantics_reject_before_publication(
    tmp_path,
    record_name,
    mutation,
    caller_verdict,
    caller_authority_status,
    error_type,
    error_match,
):
    from research_system.session_exchange import record_session_evidence

    brief = _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs["recorded_at"] = "2026-08-04T10:00:00Z"
    external = _accepted_external_fixture(
        tmp_path,
        brief,
        **{f"{record_name}_mutation": mutation},
        caller_verdict=caller_verdict,
        caller_authority_status=caller_authority_status,
    )
    kwargs.update(review_evidence=external["review_evidence"], acceptance_evidence=external["acceptance_evidence"])

    with pytest.raises(error_type, match=error_match):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


@pytest.mark.parametrize("record_name", ["review", "decision", "authority"])
def test_noncanonical_external_record_rejects_before_publication(tmp_path, record_name):
    from research_system.session_exchange import record_session_evidence

    brief = _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs["recorded_at"] = "2026-08-04T10:00:00Z"
    external = _accepted_external_fixture(tmp_path, brief, noncanonical_record=record_name)
    kwargs.update(review_evidence=external["review_evidence"], acceptance_evidence=external["acceptance_evidence"])

    with pytest.raises(SchemaError, match="must be exact canonical JSON"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_json_record_relabelled_as_non_json_rejects_before_publication(tmp_path):
    from research_system.session_exchange import ExternalEvidence, IndependentReviewEvidence, record_session_evidence

    brief = _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs["recorded_at"] = "2026-08-04T10:00:00Z"
    external = _accepted_external_fixture(tmp_path, brief)
    review = external["review_evidence"]
    kwargs["review_evidence"] = IndependentReviewEvidence(
        reviewer_identity_locator=review.reviewer_identity_locator,
        verdict=review.verdict,
        record=ExternalEvidence(
            record_locator=review.record.record_locator,
            path=review.record.path,
            media_type="text/plain",
        ),
    )
    kwargs["acceptance_evidence"] = external["acceptance_evidence"]

    with pytest.raises(SchemaError, match="must use application/json"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def _prepare_fixture(control_root, **overrides):
    from research_system.session_exchange import prepare_session_brief

    values = {
        "brief_artifact_id": BRIEF_ARTIFACT_ID,
        "handoff_id": HANDOFF_ID,
        "session_id": SESSION_ID,
        "attempt_id": ATTEMPT_ID,
        "task_id": TASK_ID,
        "requested_role": "independent_exact_subject_review",
        "assurance_requirement": "output_provenance_and_independent_review",
        "operator_identity_locator": "ars://actors/operator-fixture",
        "producer_identity_locator": PRODUCER_LOCATOR,
        "session_family": "codex_standalone",
        "git_commit_sha": "a" * 40,
        "git_tree_sha": "b" * 40,
        "brief_bytes": b"Review the exact candidate without invoking a provider.\n",
        "prepared_at": "2026-08-04T09:00:00Z",
    }
    values.update(overrides)
    return prepare_session_brief(control_root, **values)


def _evidence_kwargs(control_root):
    from research_system.session_exchange import EvidenceArtifact, UnresolvedFinding

    returned_path = control_root / "candidate.patch"
    returned_path.write_bytes(b"exact candidate bytes\n")
    tests_path = control_root / "focused-tests.txt"
    tests_path.write_bytes(b"2 passed\n")
    return {
        "evidence_artifact_id": EVIDENCE_ARTIFACT_ID,
        "brief_artifact_id": BRIEF_ARTIFACT_ID,
        "handoff_id": HANDOFF_ID,
        "session_id": SESSION_ID,
        "attempt_id": ATTEMPT_ID,
        "producer_identity_locator": PRODUCER_LOCATOR,
        "reviewer_identity_locator": REVIEWER_LOCATOR,
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
        "acceptance_authority_locator": AUTHORITY_LOCATOR,
        "returned_artifacts": (
            EvidenceArtifact(
                artefact_id="art_01978abc-6400-7000-8000-000000000007",
                locator="repo://candidate.patch",
                path=returned_path,
                media_type="text/x-diff",
            ),
        ),
        "test_evidence": (
            EvidenceArtifact(
                artefact_id="art_01978abc-6400-7000-8000-000000000008",
                locator="repo://focused-tests.txt",
                path=tests_path,
                media_type="text/plain",
            ),
        ),
        "producer_verdict": "partial",
        "unresolved_findings": (
            UnresolvedFinding(finding_id="F-2", severity="major", summary="Second unresolved fixture finding."),
            UnresolvedFinding(finding_id="F-1", severity="minor", summary="First unresolved fixture finding."),
        ),
        "recorded_at": "2026-08-04T09:30:00Z",
    }


def _artifact_revision_directory(control_root, artefact_id):
    return control_root / "objects" / "artefact" / artefact_id


def test_identical_retry_converges_and_changed_brief_or_artifact_conflicts_without_mutation(tmp_path):
    from research_system.session_exchange import record_session_evidence

    brief = _prepare_fixture(tmp_path)
    brief_bytes = brief.path.read_bytes()
    assert _prepare_fixture(tmp_path).path == brief.path
    with pytest.raises(ConflictError, match="object revision already exists"):
        _prepare_fixture(tmp_path, brief_bytes=b"changed brief bytes\n")
    assert brief.path.read_bytes() == brief_bytes

    kwargs = _evidence_kwargs(tmp_path)
    evidence = record_session_evidence(tmp_path, **kwargs)
    evidence_bytes = evidence.path.read_bytes()
    assert evidence.document["unresolved_findings"] == [
        {
            "finding_id": "F-2",
            "severity": "major",
            "status": "unresolved",
            "summary": "Second unresolved fixture finding.",
        },
        {
            "finding_id": "F-1",
            "severity": "minor",
            "status": "unresolved",
            "summary": "First unresolved fixture finding.",
        },
    ]
    assert record_session_evidence(tmp_path, **kwargs).path == evidence.path
    kwargs["returned_artifacts"][0].path.write_bytes(b"changed candidate bytes\n")
    with pytest.raises(ConflictError, match="object revision already exists"):
        record_session_evidence(tmp_path, **kwargs)
    assert evidence.path.read_bytes() == evidence_bytes
    kwargs["returned_artifacts"][0].path.write_bytes(b"exact candidate bytes\n")
    kwargs["session_id"] = "ses_01978abc-6400-7000-8000-000000000099"
    with pytest.raises(ConflictError, match="does not bind the prepared brief"):
        record_session_evidence(tmp_path, **kwargs)
    assert evidence.path.read_bytes() == evidence_bytes


@pytest.mark.parametrize(
    ("field", "foreign_identity"),
    [
        ("handoff_id", "hnd_01978abc-6400-7000-8000-000000000099"),
        ("session_id", "ses_01978abc-6400-7000-8000-000000000099"),
        ("attempt_id", "att_01978abc-6400-7000-8000-000000000099"),
    ],
)
def test_foreign_handoff_session_or_attempt_identity_rejects_without_publication(tmp_path, field, foreign_identity):
    from research_system.session_exchange import record_session_evidence

    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs[field] = foreign_identity

    with pytest.raises(ConflictError, match="does not bind the prepared brief"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_missing_artifact_and_producer_self_review_reject_without_publication(tmp_path):
    from research_system.session_exchange import EvidenceArtifact, record_session_evidence

    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs["returned_artifacts"] = (
        EvidenceArtifact(
            artefact_id="art_01978abc-6400-7000-8000-000000000007",
            locator="repo://missing.patch",
            path=tmp_path / "missing.patch",
            media_type="text/x-diff",
        ),
    )
    with pytest.raises(SchemaError, match="unreadable"):
        record_session_evidence(tmp_path, **kwargs)
    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()

    kwargs = _evidence_kwargs(tmp_path)
    kwargs["reviewer_identity_locator"] = PRODUCER_LOCATOR
    with pytest.raises(SchemaError, match="must be distinct"):
        record_session_evidence(tmp_path, **kwargs)
    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()

    kwargs = _evidence_kwargs(tmp_path)
    kwargs["acceptor_identity_locator"] = PRODUCER_LOCATOR
    with pytest.raises(SchemaError, match="must be distinct"):
        record_session_evidence(tmp_path, **kwargs)
    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_brief_evidence_returned_and_test_artifact_identities_must_be_disjoint(tmp_path):
    from research_system.session_exchange import record_session_evidence

    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    colliding_id = kwargs["returned_artifacts"][0].artefact_id
    kwargs["evidence_artifact_id"] = colliding_id

    with pytest.raises(SchemaError, match="document and returned evidence identities must be disjoint"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, colliding_id).exists()


def test_unresolved_finding_identities_are_unique_without_collapsing_their_order(tmp_path):
    from research_system.session_exchange import UnresolvedFinding, record_session_evidence

    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs["unresolved_findings"] = (
        UnresolvedFinding(finding_id="F-1", severity="major", summary="First version."),
        UnresolvedFinding(finding_id="F-1", severity="minor", summary="Conflicting duplicate."),
    )

    with pytest.raises(SchemaError, match="unresolved finding identities must be unique"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_owner_acceptance_without_readable_external_authority_rejects_without_publication(tmp_path):
    from research_system.session_exchange import (
        ExternalEvidence,
        OwnerAcceptanceEvidence,
        record_session_evidence,
    )

    brief = _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    external = _accepted_external_fixture(tmp_path, brief)
    kwargs["review_evidence"] = external["review_evidence"]
    kwargs["acceptance_evidence"] = OwnerAcceptanceEvidence(
        acceptor_identity_locator=ACCEPTOR_LOCATOR,
        authority_locator=AUTHORITY_LOCATOR,
        authority_status="active",
        decision=external["acceptance_evidence"].decision,
        authority=ExternalEvidence(
            record_locator="repo://missing-owner-authority.json",
            path=tmp_path / "missing-owner-authority.json",
            media_type="application/json",
        ),
    )

    with pytest.raises(SchemaError, match="owner acceptance authority is unreadable"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()

    inactive = _accepted_external_fixture(
        tmp_path,
        brief,
        authority_mutation=(("status",), "inactive"),
        caller_authority_status="inactive",
    )
    kwargs.update(review_evidence=inactive["review_evidence"], acceptance_evidence=inactive["acceptance_evidence"])
    with pytest.raises(SchemaError, match="requires active external authority"):
        record_session_evidence(tmp_path, **kwargs)
    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("prepared_at", "2026-02-30T09:00:00Z"),
        ("prepared_at", "2026-08-04T09:00:00+00:00"),
        ("git_commit_sha", "A" * 40),
        ("git_tree_sha", "b" * 39),
        ("brief_bytes", b"\xef\xbb\xbfnot BOM-free"),
    ],
)
def test_malformed_utc_git_subject_or_brief_encoding_rejects_without_publication(tmp_path, field, invalid_value):
    with pytest.raises(SchemaError):
        _prepare_fixture(tmp_path, **{field: invalid_value})

    assert not _artifact_revision_directory(tmp_path, BRIEF_ARTIFACT_ID).exists()


def test_closed_schemas_reject_malformed_hashes_and_future_evidence_in_the_brief(tmp_path):
    from research_system.session_exchange import record_session_evidence

    brief = _prepare_fixture(tmp_path)
    evidence = record_session_evidence(tmp_path, **_evidence_kwargs(tmp_path))
    repository_root = Path(__file__).resolve().parents[3]
    brief_schema = json.loads(
        (repository_root / ".research-system/schemas/wp6-4/owner-operated-session-brief.schema.json").read_text(
            encoding="utf-8"
        )
    )
    evidence_schema = json.loads(
        (repository_root / ".research-system/schemas/wp6-4/owner-operated-session-evidence.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(brief_schema)
    Draft202012Validator.check_schema(evidence_schema)

    invalid_brief_hash = copy.deepcopy(brief.document)
    invalid_brief_hash["brief"]["raw_sha256"] = "not-a-sha256"
    with pytest.raises(ValidationError):
        Draft202012Validator(brief_schema).validate(invalid_brief_hash)
    future_review = copy.deepcopy(brief.document)
    future_review["review"] = {"status": "accepted"}
    with pytest.raises(ValidationError):
        Draft202012Validator(brief_schema).validate(future_review)
    invalid_artifact_hash = copy.deepcopy(evidence.document)
    invalid_artifact_hash["returned_artifacts"][0]["raw_sha256"] = "f" * 63
    with pytest.raises(ValidationError):
        Draft202012Validator(evidence_schema).validate(invalid_artifact_hash)
    open_nested_acceptance = copy.deepcopy(evidence.document)
    open_nested_acceptance["acceptance"]["self_attested"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(evidence_schema).validate(open_nested_acceptance)


def test_interruption_before_evidence_publication_allows_only_identical_retry(tmp_path, monkeypatch):
    import research_system.store.objects as object_module
    from research_system.session_exchange import record_session_evidence

    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)

    def interrupt_before_publication(_temporary):
        raise OSError("synthetic mechanics-only interruption")

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", interrupt_before_publication)
    with pytest.raises(OSError, match="synthetic mechanics-only interruption"):
        record_session_evidence(tmp_path, **kwargs)
    evidence_directory = _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID)
    assert evidence_directory.exists()
    assert list(evidence_directory.iterdir()) == []

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", lambda _temporary: None)
    published = record_session_evidence(tmp_path, **kwargs)
    assert published.document["document_state"] == "produced_unreviewed"
    assert record_session_evidence(tmp_path, **kwargs).path == published.path
