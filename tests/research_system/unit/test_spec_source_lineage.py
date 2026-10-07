"""SOURCE lineage stays under one SPEC-01 Task (P-058, 2026-10-07, M-2 and P5-7 amended)."""

from __future__ import annotations

import pytest

from research_system.discovery.spec_source import DOCUMENT_KIND, _lineage_candidate, source_ids
from research_system.errors import IntegrityError
from tests.research_system.factories import PROJECT_ID

TASK_A = "tsk_01978abc-7200-7000-8000-00000000000a"
TASK_B = "tsk_01978abc-7200-7000-8000-00000000000b"
OBSERVATION_ID = "art_01978abc-7300-7000-8000-000000000001"
CORRECTION_ID = "art_01978abc-7300-7000-8000-000000000002"


class _Documents:
    """The SOURCE documents a lineage reads, keyed by artefact ID."""

    def __init__(self, documents: dict[str, dict]) -> None:
        self.documents = documents

    def revision_exists(self, kind: str, artefact_id: str, revision: int) -> bool:
        return kind == DOCUMENT_KIND and revision == 1 and artefact_id in self.documents

    def read(self, kind: str, artefact_id: str, revision: int) -> dict:
        assert self.revision_exists(kind, artefact_id, revision)
        return {"intent": self.documents[artefact_id]}


def _observation(task_id: str) -> dict:
    return {"action": "observe_source", "source_key": "paper-code", "production": {"task_id": task_id}}


def _correction(task_id: str, corrects: str, key: str = "paper-code-correction") -> dict:
    return {
        "action": "correct_spec_01_source",
        "source_key": key,
        "corrects_artefact_id": corrects,
        "production": {"task_id": task_id},
    }


def test_a_lineage_under_one_task_derives_its_observations_candidate():
    observation = _observation(TASK_A)
    documents = _Documents({OBSERVATION_ID: observation})
    expected = source_ids(PROJECT_ID, observation)["candidate_id"]
    assert _lineage_candidate(PROJECT_ID, observation, documents, task_id=TASK_A) == expected
    correction = _correction(TASK_A, OBSERVATION_ID)
    assert _lineage_candidate(PROJECT_ID, correction, documents, task_id=TASK_A) == expected


def test_a_correction_cannot_carry_another_tasks_observation_into_its_task():
    """CodeRabbit on #349: a correction under Task B targeting Task A's observation must not admit A's Candidate."""
    documents = _Documents({OBSERVATION_ID: _observation(TASK_A)})
    with pytest.raises(IntegrityError, match="under a Task other than"):
        _lineage_candidate(PROJECT_ID, _correction(TASK_B, OBSERVATION_ID), documents, task_id=TASK_B)


def test_every_link_of_a_correction_chain_stays_under_the_task():
    documents = _Documents({OBSERVATION_ID: _observation(TASK_B), CORRECTION_ID: _correction(TASK_A, OBSERVATION_ID)})
    chained = _correction(TASK_B, CORRECTION_ID, key="paper-code-second-correction")
    with pytest.raises(IntegrityError, match="under a Task other than"):
        _lineage_candidate(PROJECT_ID, chained, documents, task_id=TASK_B)
