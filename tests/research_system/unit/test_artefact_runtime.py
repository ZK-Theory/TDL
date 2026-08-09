from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.artefacts.runtime import (
    ControlRootArtefactContentReader,
    GoverningScientificReviewStore,
    build_artefact_consumers,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError
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


def test_governing_review_store_is_write_once_and_project_bound(tmp_path):
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
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
