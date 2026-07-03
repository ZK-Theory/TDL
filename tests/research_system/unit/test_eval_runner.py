"""Contract tests for the owned evaluation lifecycle and runner."""

from dataclasses import dataclass

from research_system.evals.errors import FixtureDefinitionError, MissingEvidence
from research_system.evals.lifecycle import EvaluationLifecycle
from research_system.evals.runner import run_fixture


@dataclass(frozen=True)
class _Fixture:
    fixture_id: str = 'F-001'
    fixture_revision: str = 'r1'
    stimulus: dict = None

    def __post_init__(self):
        object.__setattr__(self, 'stimulus', {'immutable': True})


class _Subject:
    subject_id = 'known-good-v1'

    def __init__(self, error=None):
        self.error = error

    def execute(self, stimulus):
        if self.error is not None:
            raise self.error
        return {'subject_id': self.subject_id, 'stimulus': stimulus}


class _TraceCollector:
    def complete(self, run, subject_result):
        return {'evaluation_run_id': run.evaluation_run_id, 'subject': subject_result}


class _Grader:
    def grade(self, fixture, trace, subject_result):
        del trace, subject_result
        return {'fixture_id': fixture.fixture_id, 'verdict': 'pass'}


def test_runner_finishes_with_immutable_identity_and_terminal_hashes():
    lifecycle = EvaluationLifecycle()
    first = run_fixture(
        _Fixture(), _Subject(), _TraceCollector(), (_Grader(),), lifecycle
    )
    second = run_fixture(
        _Fixture(), _Subject(), _TraceCollector(), (_Grader(),), lifecycle
    )
    assert first.status == 'finished'
    assert first.evaluation_run_id == second.evaluation_run_id
    assert first.trace_hash == second.trace_hash
    assert first.result_hash == second.result_hash


def test_runner_closes_fixture_errors_without_system_pass():
    outcome = run_fixture(
        _Fixture(),
        _Subject(FixtureDefinitionError('broken fixture')),
        _TraceCollector(),
        (_Grader(),),
        EvaluationLifecycle(),
    )
    assert outcome.status == 'fixture_error'
    assert outcome.trace_hash is None
    assert outcome.result_hash is None


def test_runner_closes_missing_evidence_as_unable_to_grade():
    outcome = run_fixture(
        _Fixture(),
        _Subject(MissingEvidence('missing required trace')),
        _TraceCollector(),
        (_Grader(),),
        EvaluationLifecycle(),
    )
    assert outcome.status == 'unable_to_grade'
    assert outcome.trace_hash is None
    assert outcome.result_hash is None
