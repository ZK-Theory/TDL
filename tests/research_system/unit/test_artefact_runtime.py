from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from threading import Event

import pytest

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.artefacts.runtime import (
    ControlRootArtefactContentReader,
    GoverningScientificReviewStore,
    build_artefact_consumers,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError
from research_system.evidence.consumers import ArtefactConsumerContext
from research_system.schema_registry import SchemaRegistry
from research_system.store.objects import ObjectStore
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    REPO_ROOT,
    activate_lifecycle_grant,
    control_plane,
)


REFERENCE_ID = "arec_019fe47a-1007-7000-8000-000000001007"
SECOND_REFERENCE_ID = "arec_019fe47a-1007-7000-8000-000000001008"
REVIEW_ID = "rev_019fe47a-1005-7000-8000-000000001005"


def _record() -> dict[str, object]:
    return {
        "schema_id": "ars://evidence/governing-scientific-review",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "review_id": REVIEW_ID,
        "subject_sha256": "1" * 64,
        "reviewer_actor_id": ACTORS["actor-a"],
        "eligible": True,
        "related": False,
        "independence_grade": "I1",
        "status": "active",
    }


@pytest.fixture(scope="module")
def schemas() -> SchemaRegistry:
    return SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")


def test_governing_review_store_is_write_once_and_project_bound(tmp_path, schemas):
    store = GoverningScientificReviewStore(ObjectStore(tmp_path), schemas)

    first = store.publish(REFERENCE_ID, _record())
    second = store.resolve(
        REFERENCE_ID,
        project_id=PROJECT_ID,
        evaluation_time=datetime(2026, 8, 9, tzinfo=UTC),
    )

    assert first == second
    assert first.canonical_sha256 == sha256_hex(canonical_bytes(_record()))
    with pytest.raises(ArsError, match="different project"):
        store.resolve(
            REFERENCE_ID,
            project_id="prj_01978abc-1000-7000-8000-000000001001",
            evaluation_time=datetime(2026, 8, 9, tzinfo=UTC),
        )


def test_governing_review_direct_publication_is_exactly_idempotent_and_changed_retry_conflicts(
    tmp_path,
    schemas,
    monkeypatch,
):
    objects = ObjectStore(tmp_path)
    store = GoverningScientificReviewStore(objects, schemas)

    first = store.publish(REFERENCE_ID, _record())
    retry = store.publish(REFERENCE_ID, _record())

    assert retry == first
    changed = _record()
    changed["subject_sha256"] = "2" * 64
    write_calls: list[str] = []
    original_write = objects.write

    def record_write(kind, object_id, revision, value):
        write_calls.append(object_id)
        return original_write(kind, object_id, revision, value)

    monkeypatch.setattr(objects, "write", record_write)
    with pytest.raises(ArsError, match="publication identity conflicts"):
        store.publish(REFERENCE_ID, changed)
    assert write_calls == []
    assert objects.read("assurance_record", REFERENCE_ID, 1) == _record()


def test_governing_review_direct_and_batch_publications_share_one_writer_fence(
    tmp_path,
    schemas,
    monkeypatch,
):
    objects = ObjectStore(tmp_path)
    store = GoverningScientificReviewStore(objects, schemas)
    first_write_entered = Event()
    release_first_write = Event()
    original_write = objects.write

    def pause_first_write(kind, object_id, revision, value):
        if object_id == REFERENCE_ID:
            first_write_entered.set()
            assert release_first_write.wait(timeout=10)
        return original_write(kind, object_id, revision, value)

    monkeypatch.setattr(objects, "write", pause_first_write)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(store.publish, REFERENCE_ID, _record())
        try:
            assert first_write_entered.wait(timeout=10)

            second = {**_record(), "review_id": "rev_019fe47a-1005-7000-8000-000000001006"}
            with pytest.raises(ConflictError, match="writer lock exists"):
                store.publish_batch(
                    [{"reference_id": SECOND_REFERENCE_ID, "record": second}],
                    project_id=PROJECT_ID,
                    evaluation_time=datetime(2026, 8, 9, tzinfo=UTC),
                )
            assert not objects.revision_exists("assurance_record", SECOND_REFERENCE_ID, 1)
        finally:
            release_first_write.set()
        first_resolution = first.result(timeout=10)

    assert first_resolution.reference_id == REFERENCE_ID
    assert objects.read("assurance_record", REFERENCE_ID, 1) == _record()


@pytest.mark.parametrize(
    "publications, message",
    [
        ({}, "must be a list"),
        ([None], "must be a mapping"),
        ([{"reference_id": REFERENCE_ID}], "fields are invalid"),
        ([{"reference_id": REFERENCE_ID, "record": []}], "identities are invalid"),
        ([{"reference_id": None, "record": _record()}], "reference identity is invalid"),
    ],
)
def test_governing_review_batch_rejects_malformed_container_and_members_as_ars_error(
    tmp_path,
    schemas,
    publications,
    message,
):
    store = GoverningScientificReviewStore(ObjectStore(tmp_path), schemas)

    with pytest.raises(ArsError, match=message):
        store.prevalidate_publications(publications)


def test_governing_review_direct_publication_rejects_malformed_identity_and_record_as_ars_error(
    tmp_path,
    schemas,
):
    store = GoverningScientificReviewStore(ObjectStore(tmp_path), schemas)

    with pytest.raises(ArsError, match="reference identity is invalid"):
        store.publish(None, _record())
    with pytest.raises(ArsError, match="record must be a mapping"):
        store.publish(REFERENCE_ID, [])


def test_governing_review_batch_rejects_duplicates_and_wrong_project_before_publication(tmp_path, schemas):
    objects = ObjectStore(tmp_path)
    store = GoverningScientificReviewStore(objects, schemas)
    publication = {"reference_id": REFERENCE_ID, "record": _record()}
    now = datetime(2026, 8, 9, tzinfo=UTC)

    with pytest.raises(ArsError, match="identities are invalid"):
        store.publish_batch(
            [publication, publication],
            project_id=PROJECT_ID,
            evaluation_time=now,
        )
    assert not objects.revision_exists("assurance_record", REFERENCE_ID, 1)

    with pytest.raises(ArsError, match="different project"):
        store.publish_batch(
            [publication],
            project_id="prj_01978abc-1000-7000-8000-000000001001",
            evaluation_time=now,
        )
    assert not objects.revision_exists("assurance_record", REFERENCE_ID, 1)


def test_governing_review_batch_is_exactly_idempotent_and_changed_retry_conflicts(tmp_path, schemas):
    objects = ObjectStore(tmp_path)
    store = GoverningScientificReviewStore(objects, schemas)
    publication = {"reference_id": REFERENCE_ID, "record": _record()}
    now = datetime(2026, 8, 9, tzinfo=UTC)

    first = store.publish_batch([publication], project_id=PROJECT_ID, evaluation_time=now)
    retry = store.publish_batch([publication], project_id=PROJECT_ID, evaluation_time=now)

    assert retry == first
    changed = _record()
    changed["subject_sha256"] = "2" * 64
    with pytest.raises(ArsError, match="identity conflicts"):
        store.publish_batch(
            [{"reference_id": REFERENCE_ID, "record": changed}],
            project_id=PROJECT_ID,
            evaluation_time=now,
        )
    assert objects.read("assurance_record", REFERENCE_ID, 1) == _record()


def test_governing_review_batch_rolls_back_only_new_members_on_synchronous_failure(tmp_path, schemas, monkeypatch):
    objects = ObjectStore(tmp_path)
    store = GoverningScientificReviewStore(objects, schemas)
    second = {**_record(), "review_id": "rev_019fe47a-1005-7000-8000-000000001006"}
    original_write = objects.write

    def fail_second(kind, object_id, revision, value):
        if object_id == SECOND_REFERENCE_ID:
            raise OSError("injected second-member failure")
        return original_write(kind, object_id, revision, value)

    monkeypatch.setattr(objects, "write", fail_second)
    with pytest.raises(OSError, match="second-member"):
        store.publish_batch(
            [
                {"reference_id": REFERENCE_ID, "record": _record()},
                {"reference_id": SECOND_REFERENCE_ID, "record": second},
            ],
            project_id=PROJECT_ID,
            evaluation_time=datetime(2026, 8, 9, tzinfo=UTC),
        )

    assert not objects.revision_exists("assurance_record", REFERENCE_ID, 1)
    assert not objects.revision_exists("assurance_record", SECOND_REFERENCE_ID, 1)


def test_governing_review_batch_never_rolls_back_a_preexisting_exact_retry(tmp_path, schemas, monkeypatch):
    objects = ObjectStore(tmp_path)
    store = GoverningScientificReviewStore(objects, schemas)
    existing = _record()
    second = {**existing, "review_id": "rev_019fe47a-1005-7000-8000-000000001006"}
    store.publish(REFERENCE_ID, existing)
    original_write = objects.write

    def fail_second(kind, object_id, revision, value):
        if object_id == SECOND_REFERENCE_ID:
            raise OSError("injected second-member failure")
        return original_write(kind, object_id, revision, value)

    monkeypatch.setattr(objects, "write", fail_second)
    with pytest.raises(OSError, match="second-member"):
        store.publish_batch(
            [
                {"reference_id": REFERENCE_ID, "record": existing},
                {"reference_id": SECOND_REFERENCE_ID, "record": second},
            ],
            project_id=PROJECT_ID,
            evaluation_time=datetime(2026, 8, 9, tzinfo=UTC),
        )

    assert objects.read("assurance_record", REFERENCE_ID, 1) == existing
    assert not objects.revision_exists("assurance_record", SECOND_REFERENCE_ID, 1)


@pytest.mark.parametrize(
    "evaluation_time",
    [None, datetime(2026, 8, 9), datetime(2026, 8, 9, tzinfo=timezone(timedelta(hours=1)))],
)
def test_governing_review_batch_rejects_invalid_evaluation_time(tmp_path, schemas, evaluation_time):
    store = GoverningScientificReviewStore(ObjectStore(tmp_path), schemas)

    with pytest.raises(ArsError, match="evaluation time must be UTC"):
        store.publish_batch(
            [{"reference_id": REFERENCE_ID, "record": _record()}],
            project_id=PROJECT_ID,
            evaluation_time=evaluation_time,
        )


def test_control_content_reader_rejects_escape_and_foreign_root(tmp_path):
    control = tmp_path / "control"
    control.mkdir()
    evidence = control / "evidence.json"
    evidence.write_bytes(b"evidence")
    reader = ControlRootArtefactContentReader(control)

    assert reader.read(root_id="control", relative_path="evidence.json") == b"evidence"
    with pytest.raises(ArsError, match="selected control store"):
        reader.read(root_id="backup", relative_path="evidence.json")
    with pytest.raises(ArsError, match="safe control-relative"):
        reader.read(root_id="control", relative_path="../outside.json")


@pytest.mark.integration
def test_production_consumers_validate_scoped_authority_replay_before_resolution(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    artefact_id = "art_019fe47a-1020-7000-8000-000000001020"
    activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=artefact_id,
        command_types=("RegisterArtefact",),
    )
    authority = harness.authority_resolver
    binding = ControlBinding(
        code_roots=(REPO_ROOT,),
        control_root=harness.authority_root,
        project_id=PROJECT_ID,
        schema_root=REPO_ROOT / ".research-system" / "schemas",
        store_identity=authority.expected_store_identity,
        origin_witness_path=authority.approved_witness_path,
        origin_witness=authority.approved_witness,
    )
    validated_states: list[dict[str, object]] = []
    original_validator = LedgerAuthorityGrantResolver.validate_replayed_administration_state

    def record_validation(self, state):
        validated_states.append(state)
        original_validator(self, state)

    monkeypatch.setattr(
        LedgerAuthorityGrantResolver,
        "validate_replayed_administration_state",
        record_validation,
    )
    consumers = build_artefact_consumers(binding)

    with pytest.raises(ArsError, match="no current replay-derived registration"):
        consumers.resolve_for_review(
            ArtefactConsumerContext(
                artefact_id=artefact_id,
                exact_content_sha256="1" * 64,
                project_id=PROJECT_ID,
                task_id="tsk_019fe47a-1021-7000-8000-000000001021",
                scope_id="obj_019fe47a-1022-7000-8000-000000001022",
                evaluation_time=datetime(2026, 8, 9, tzinfo=UTC),
            ),
            consumer_id="rm03_brief_review",
        )
    assert len(validated_states) == 1
