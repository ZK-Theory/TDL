from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_system.artefacts.runtime import (
    ControlRootArtefactContentReader,
    GoverningScientificReviewStore,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError
from research_system.schema_registry import SchemaRegistry
from research_system.store.objects import ObjectStore
from tests.research_system.factories import ACTORS, PROJECT_ID, REPO_ROOT


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
