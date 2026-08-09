from __future__ import annotations

import copy
from datetime import UTC, datetime
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, SchemaError
from research_system.evidence.consumers import ArtefactConsumerContext
from research_system.session_exchange import (
    EvidenceArtifact,
    SessionRecordLocator,
    UnresolvedFinding,
    prepare_session_brief,
    record_session_evidence,
)
from research_system.store.objects import ObjectStore


BRIEF_ARTIFACT_ID = "art_01978abc-6400-7000-8000-000000000001"
EVIDENCE_ARTIFACT_ID = "art_01978abc-6400-7000-8000-000000000006"
HANDOFF_ID = "hnd_01978abc-6400-7000-8000-000000000002"
SESSION_ID = "ses_01978abc-6400-7000-8000-000000000003"
ATTEMPT_ID = "att_01978abc-6400-7000-8000-000000000004"
TASK_ID = "tsk_01978abc-6400-7000-8000-000000000005"
PRODUCER_LOCATOR = "ars://actors/producer-fixture"
REVIEWER_LOCATOR = "ars://actors/reviewer-fixture"
ACCEPTOR_LOCATOR = "ars://actors/acceptor-fixture"
REVIEW_RECORD_ID = "isr_01978abc-6401-7000-8000-000000000010"

_EVIDENCE_CORE_FIELDS = (
    "schema_id",
    "schema_version",
    "document_type",
    "mechanics_scope",
    "provider_control",
    "evidence_artifact_id",
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


def _prepare_fixture(control_root: Path, **overrides):
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


def _evidence_kwargs(control_root: Path) -> dict[str, object]:
    brief = ObjectStore(control_root).read("artefact", BRIEF_ARTIFACT_ID, 1)
    brief_bytes = canonical_bytes(brief)

    class BriefConsumers:
        def resolve_for_review(self, context, *, consumer_id):
            assert consumer_id == "rm04_followup_review"
            assert context.exact_content_sha256 == sha256_hex(brief_bytes)
            return SimpleNamespace(content_bytes=brief_bytes)

    returned_path = control_root / "candidate.patch"
    returned_path.write_bytes(b"exact candidate bytes\n")
    tests_path = control_root / "focused-tests.txt"
    tests_path.write_bytes(b"2 passed\n")
    return {
        "expected_previous_revision": 0,
        "evidence_artifact_id": EVIDENCE_ARTIFACT_ID,
        "brief_artifact_id": BRIEF_ARTIFACT_ID,
        "handoff_id": HANDOFF_ID,
        "session_id": SESSION_ID,
        "attempt_id": ATTEMPT_ID,
        "producer_identity_locator": PRODUCER_LOCATOR,
        "reviewer_identity_locator": REVIEWER_LOCATOR,
        "acceptor_identity_locator": ACCEPTOR_LOCATOR,
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
            UnresolvedFinding(
                finding_id="F-2",
                severity="major",
                summary="Second unresolved fixture finding.",
            ),
            UnresolvedFinding(
                finding_id="F-1",
                severity="minor",
                summary="First unresolved fixture finding.",
            ),
        ),
        "recorded_at": "2026-08-04T09:30:00Z",
        "artefact_consumers": BriefConsumers(),
        "brief_use_context": ArtefactConsumerContext(
            artefact_id=BRIEF_ARTIFACT_ID,
            exact_content_sha256=sha256_hex(brief_bytes),
            project_id="prj_01978abc-6400-7000-8000-000000000009",
            task_id=TASK_ID,
            scope_id="session-review:wp6.4",
            evaluation_time=datetime(2026, 8, 4, 9, 30, tzinfo=UTC),
        ),
    }


def _artifact_revision_directory(control_root: Path, artefact_id: str) -> Path:
    return control_root / "objects" / "artefact" / artefact_id


def _revision_snapshot(control_root: Path) -> dict[str, bytes]:
    directory = _artifact_revision_directory(control_root, EVIDENCE_ARTIFACT_ID)
    if not directory.exists():
        return {}
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir()) if path.is_file()}


def test_prepare_session_brief_publishes_exact_provider_free_subject(tmp_path: Path) -> None:
    brief_bytes = b"Review the exact candidate without invoking a provider.\n"

    published = _prepare_fixture(tmp_path, brief_bytes=brief_bytes)

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


def test_r1_evidence_binds_exact_brief_artifacts_and_pending_authority(tmp_path: Path) -> None:
    brief = _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)

    published = record_session_evidence(tmp_path, **kwargs)

    assert published.document["revision"] == 1
    assert published.document["document_state"] == "produced_unreviewed"
    assert published.document["supersedes_revision"] is None
    assert published.document["supersedes_document_raw_sha256"] is None
    assert published.document["brief_subject"] == {
        "brief_artifact_id": BRIEF_ARTIFACT_ID,
        "revision": 1,
        "document_raw_sha256": brief.raw_sha256,
        "brief_raw_sha256": brief.document["brief"]["raw_sha256"],
        "git_subject": {"commit_sha": "a" * 40, "tree_sha": "b" * 40},
    }
    returned_path = kwargs["returned_artifacts"][0].path
    tests_path = kwargs["test_evidence"][0].path
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
        "authority_grant_id": None,
        "authority_status": "unverified",
        "status": "pending_owner_acceptance",
        "outcome": None,
        "evidence": None,
    }
    evidence_core = {field: published.document[field] for field in _EVIDENCE_CORE_FIELDS}
    assert "revision" not in evidence_core
    assert published.document["evidence_subject_raw_sha256"] == sha256_hex(canonical_bytes(evidence_core))
    assert published.path.read_bytes() == canonical_bytes(published.document)
    assert published.raw_sha256 == sha256_hex(published.path.read_bytes())


@pytest.mark.parametrize(
    "legacy_keyword",
    [
        "review_evidence",
        "acceptance_evidence",
        "authority_grant_id",
        "acceptor_actor_id",
    ],
)
def test_caller_json_keywords_cannot_publish_later_revisions(
    tmp_path: Path,
    legacy_keyword: str,
) -> None:
    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    published = record_session_evidence(tmp_path, **kwargs)
    before = _revision_snapshot(tmp_path)
    caller_path = tmp_path / f"caller-{legacy_keyword}.json"
    caller_path.write_bytes(
        canonical_bytes(
            {
                "status": "active",
                "verdict": "accepted",
                "authority_grant_id": "agr_01978abc-6402-7000-8000-000000000020",
            }
        )
    )
    legacy_value = {
        "record_locator": f"repo://{caller_path.name}",
        "path": caller_path,
        "media_type": "application/json",
        "verdict": "accepted",
        "authority_status": "active",
    }
    later = {
        **kwargs,
        "expected_previous_revision": 1,
        legacy_keyword: legacy_value,
    }

    assert legacy_keyword not in inspect.signature(record_session_evidence).parameters
    with pytest.raises(TypeError, match=f"unexpected keyword argument '{legacy_keyword}'"):
        record_session_evidence(tmp_path, **later)

    assert ObjectStore(tmp_path).latest_revision("artefact", EVIDENCE_ARTIFACT_ID) == 1
    assert _revision_snapshot(tmp_path) == before
    assert published.path.read_bytes() == before[published.path.name]


@pytest.mark.parametrize("expected_previous_revision", [0, 2])
def test_review_transition_requires_the_adjacent_r1_predecessor_without_mutation(
    tmp_path: Path,
    expected_previous_revision: int,
) -> None:
    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    record_session_evidence(tmp_path, **kwargs)
    before = _revision_snapshot(tmp_path)
    review_locator = SessionRecordLocator(
        "independent_session_review",
        REVIEW_RECORD_ID,
    )

    with pytest.raises(ConflictError, match="advance exactly one immutable revision"):
        record_session_evidence(
            tmp_path,
            **{
                **kwargs,
                "expected_previous_revision": expected_previous_revision,
                "review_record": review_locator,
            },
        )

    assert ObjectStore(tmp_path).latest_revision("artefact", EVIDENCE_ARTIFACT_ID) == 1
    assert _revision_snapshot(tmp_path) == before


def test_identical_retry_converges_and_changed_inputs_conflict_without_mutation(tmp_path: Path) -> None:
    brief = _prepare_fixture(tmp_path)
    brief_bytes = brief.path.read_bytes()
    assert _prepare_fixture(tmp_path).path == brief.path
    with pytest.raises(ConflictError, match="object revision already exists"):
        _prepare_fixture(tmp_path, brief_bytes=b"changed brief bytes\n")
    assert brief.path.read_bytes() == brief_bytes

    kwargs = _evidence_kwargs(tmp_path)
    evidence = record_session_evidence(tmp_path, **kwargs)
    evidence_bytes = evidence.path.read_bytes()
    assert record_session_evidence(tmp_path, **kwargs).path == evidence.path
    kwargs["returned_artifacts"][0].path.write_bytes(b"changed candidate bytes\n")
    with pytest.raises(ConflictError, match="retry changes the immutable document"):
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
def test_foreign_brief_identity_rejects_without_publication(
    tmp_path: Path,
    field: str,
    foreign_identity: str,
) -> None:
    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    kwargs[field] = foreign_identity

    with pytest.raises(ConflictError, match="does not bind the prepared brief"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_missing_artifact_and_self_review_reject_without_publication(tmp_path: Path) -> None:
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

    for identity_field in ("reviewer_identity_locator", "acceptor_identity_locator"):
        kwargs = _evidence_kwargs(tmp_path)
        kwargs[identity_field] = PRODUCER_LOCATOR
        with pytest.raises(SchemaError, match="must be distinct"):
            record_session_evidence(tmp_path, **kwargs)
        assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_document_returned_and_test_artifact_identities_must_be_disjoint(tmp_path: Path) -> None:
    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    colliding_id = kwargs["returned_artifacts"][0].artefact_id
    kwargs["evidence_artifact_id"] = colliding_id

    with pytest.raises(SchemaError, match="document and returned evidence identities must be disjoint"):
        record_session_evidence(tmp_path, **kwargs)

    assert not _artifact_revision_directory(tmp_path, colliding_id).exists()

    kwargs = _evidence_kwargs(tmp_path)
    kwargs["test_evidence"] = kwargs["returned_artifacts"]
    with pytest.raises(SchemaError, match="identities must be disjoint"):
        record_session_evidence(tmp_path, **kwargs)
    assert not _artifact_revision_directory(tmp_path, EVIDENCE_ARTIFACT_ID).exists()


def test_unresolved_finding_identities_are_unique_without_reordering(tmp_path: Path) -> None:
    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)
    evidence = record_session_evidence(tmp_path, **kwargs)
    assert [finding["finding_id"] for finding in evidence.document["unresolved_findings"]] == [
        "F-2",
        "F-1",
    ]

    second_root = tmp_path / "duplicate-findings"
    second_root.mkdir()
    _prepare_fixture(second_root)
    duplicate_kwargs = _evidence_kwargs(second_root)
    duplicate_kwargs["unresolved_findings"] = (
        UnresolvedFinding(finding_id="F-1", severity="major", summary="First version."),
        UnresolvedFinding(finding_id="F-1", severity="minor", summary="Conflicting duplicate."),
    )
    with pytest.raises(SchemaError, match="unresolved finding identities must be unique"):
        record_session_evidence(second_root, **duplicate_kwargs)
    assert not _artifact_revision_directory(second_root, EVIDENCE_ARTIFACT_ID).exists()


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
def test_malformed_time_git_subject_or_brief_encoding_rejects_without_publication(
    tmp_path: Path,
    field: str,
    invalid_value: object,
) -> None:
    with pytest.raises(SchemaError):
        _prepare_fixture(tmp_path, **{field: invalid_value})

    assert not _artifact_revision_directory(tmp_path, BRIEF_ARTIFACT_ID).exists()


def test_closed_schemas_reject_malformed_hashes_and_future_fields(tmp_path: Path) -> None:
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


def test_interruption_before_r1_publication_allows_only_identical_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.objects as object_module

    _prepare_fixture(tmp_path)
    kwargs = _evidence_kwargs(tmp_path)

    def interrupt_before_publication(_temporary: Path) -> None:
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
