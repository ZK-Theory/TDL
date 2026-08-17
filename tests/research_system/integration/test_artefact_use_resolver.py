from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

import research_system.artefacts.use_resolver as use_resolver_module
from research_system.artefacts.authority import (
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
)
from research_system.artefacts.use_resolver import ArtefactUseDenied, ArtefactUseRequest, ArtefactUseResolver
from research_system.canonical import canonical_bytes, sha256_hex
from tests.research_system.factories import ACTORS, PROJECT_ID, control_plane
from tests.research_system.integration.test_artefact_authority_commands import (
    ARTEFACT_ID,
    CONTENT_BYTES,
    CONTENT_SHA256,
    REVIEW_EVIDENCE_ID,
    REVIEW_GRANT_ID,
    REVIEW_ID,
    SCOPE_ID,
    SUBJECT,
    TASK_ID,
    accepted_artefact_commands,
    command,
)


class EvidenceResolver:
    def __init__(self) -> None:
        self.record = {
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
        }

    def resolve(self, reference_id, *, project_id, evaluation_time):
        assert reference_id == REVIEW_EVIDENCE_ID
        assert project_id == PROJECT_ID
        assert evaluation_time.tzinfo == UTC
        return GoverningEvidenceResolution(
            reference_id=reference_id,
            canonical_sha256=sha256_hex(canonical_bytes(self.record)),
            record=self.record,
        )


class ContentReader:
    def __init__(self, content: bytes = CONTENT_BYTES) -> None:
        self.content = content
        self.reads: list[tuple[str, str]] = []

    def read(self, *, root_id: str, relative_path: str) -> bytes:
        self.reads.append((root_id, relative_path))
        return self.content


def request(loader: ArtefactAuthorityContractLoader) -> ArtefactUseRequest:
    predicate, predicate_sha256 = loader.load().predicate_for("result_evidence")
    return ArtefactUseRequest(
        artefact_id=ARTEFACT_ID,
        exact_content_sha256=CONTENT_SHA256,
        consumer_id="release_publication",
        consumer_kind="result_evidence",
        project_id=PROJECT_ID,
        task_id=TASK_ID,
        scope_id=SCOPE_ID,
        predicate_id=str(predicate["predicate_id"]),
        predicate_version=str(predicate["predicate_version"]),
        predicate_sha256=predicate_sha256,
        evaluation_time=datetime(2026, 8, 8, 21, tzinfo=UTC),
        required_decision_kind=None,
    )


def test_public_resolver_reads_real_replay_and_immutable_object_state(tmp_path):
    harness = control_plane(tmp_path)
    for value in accepted_artefact_commands(harness):
        assert harness.service.submit(value).status == "accepted"
    loader = ArtefactAuthorityContractLoader(SUBJECT)
    content_reader = ContentReader()
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=loader,
        governing_evidence=EvidenceResolver(),
        content_reader=content_reader,
    )

    resolved = resolver.resolve(request(loader))

    assert resolved.artefact_id == ARTEFACT_ID
    assert resolved.exact_content_sha256 == CONTENT_SHA256
    assert resolved.governing_review_ids == (REVIEW_ID,)
    assert resolved.decision_id is None
    assert resolved.canonical_manifest_bytes == canonical_bytes(harness.objects.read("artefact", ARTEFACT_ID, 1))
    assert resolved.content_bytes == CONTENT_BYTES
    assert content_reader.reads == [("control", "evidence/evaluation-run.json")]


def test_public_resolver_binds_spec_validator_to_the_exact_replay_snapshot(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    for value in accepted_artefact_commands(harness):
        assert harness.service.submit(value).status == "accepted"
    loader = ArtefactAuthorityContractLoader(SUBJECT)
    captured_events = []
    captured_validators = []

    def sentinel(_projection, _candidate, _event, _park_test):
        return None

    original_replay = use_resolver_module.replay

    def observed_replay(events, **kwargs):
        captured_validators.append(kwargs["spec_execution_authority_validator"])
        return original_replay(events, **kwargs)

    def validator_factory(events):
        captured_events.append(events)
        return sentinel

    monkeypatch.setattr(use_resolver_module, "replay", observed_replay)
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=loader,
        governing_evidence=EvidenceResolver(),
        content_reader=ContentReader(),
        spec_execution_authority_validator_factory=validator_factory,
    )

    resolver.resolve(request(loader))

    assert captured_events == [harness.ledger.snapshot().events]
    assert captured_validators == [sentinel]


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("exact_content_sha256", "9" * 64, "subject_hash_mismatch"),
        ("consumer_id", "unclassified_consumer", "predicate_identity_mismatch"),
        ("scope_id", "release:foreign", "accepted_scope_mismatch"),
        ("predicate_sha256", "8" * 64, "predicate_identity_mismatch"),
    ),
)
def test_public_resolver_failures_are_read_only(tmp_path, field, value, reason):
    harness = control_plane(tmp_path)
    for submitted_command in accepted_artefact_commands(harness):
        assert harness.service.submit(submitted_command).status == "accepted"
    loader = ArtefactAuthorityContractLoader(SUBJECT)
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=loader,
        governing_evidence=EvidenceResolver(),
        content_reader=ContentReader(),
    )
    before = harness.ledger.snapshot()
    before_object = harness.objects.read("artefact", ARTEFACT_ID, 1)

    with pytest.raises(ArtefactUseDenied) as denied:
        resolver.resolve(replace(request(loader), **{field: value}))

    assert denied.value.reason_code == reason
    after = harness.ledger.snapshot()
    assert (after.global_position, after.event_hash) == (before.global_position, before.event_hash)
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == before_object


def test_public_resolver_rejects_substituted_content_bytes_without_any_write(tmp_path):
    harness = control_plane(tmp_path)
    for value in accepted_artefact_commands(harness):
        assert harness.service.submit(value).status == "accepted"
    loader = ArtefactAuthorityContractLoader(SUBJECT)
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=loader,
        governing_evidence=EvidenceResolver(),
        content_reader=ContentReader(b"substituted"),
    )
    before = harness.ledger.snapshot()

    with pytest.raises(ArtefactUseDenied) as denied:
        resolver.resolve(request(loader))

    assert denied.value.reason_code == "content_substitution"
    after = harness.ledger.snapshot()
    assert (after.global_position, after.event_hash) == (before.global_position, before.event_hash)


def test_public_resolver_denies_a_review_added_after_the_bound_no_omission_snapshot(tmp_path):
    harness = control_plane(tmp_path)
    for value in accepted_artefact_commands(harness):
        assert harness.service.submit(value).status == "accepted"
    late_review = command(
        command_id="cmd_019fe47a-1090-7000-8000-000000001090",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=REVIEW_GRANT_ID,
        expected_stream_version=3,
        payload={
            "artefact_id": ARTEFACT_ID,
            "review_id": "rev_019fe47a-1090-7000-8000-000000001090",
            "subject_sha256": CONTENT_SHA256,
            "scientific_review": "approved",
            "evidence_refs": ["arec_019fe47a-1091-7000-8000-000000001091"],
        },
    )
    assert harness.service.submit(late_review).status == "accepted"
    loader = ArtefactAuthorityContractLoader(SUBJECT)
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=loader,
        governing_evidence=EvidenceResolver(),
        content_reader=ContentReader(),
    )

    with pytest.raises(ArtefactUseDenied) as denied:
        resolver.resolve(request(loader))

    assert denied.value.reason_code == "governing_review_changed"
