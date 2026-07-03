"""Evaluation coordinator over an explicitly owned lifecycle port."""

from __future__ import annotations

from typing import Any, Protocol

from research_system.evals.errors import FixtureDefinitionError, MissingEvidence


class EvaluationLifecyclePort(Protocol):
    def start(self, fixture: Any, subject: Any) -> Any: ...

    def finish(self, run: Any, trace: Any, results: tuple[Any, ...]) -> Any: ...

    def fixture_error(self, run: Any, error: Exception) -> Any: ...

    def unable_to_grade(self, run: Any, error: Exception) -> Any: ...


def run_fixture(
    fixture: Any,
    subject: Any,
    trace_collector: Any,
    graders: tuple[Any, ...],
    lifecycle: EvaluationLifecyclePort,
) -> Any:
    """Run a fixture and route every closed failure through its lifecycle."""
    run = lifecycle.start(fixture, subject)
    try:
        subject_result = subject.execute(fixture.stimulus)
        trace = trace_collector.complete(run, subject_result)
        results = tuple(
            grader.grade(fixture, trace, subject_result) for grader in graders
        )
        return lifecycle.finish(run, trace, results)
    except FixtureDefinitionError as exc:
        return lifecycle.fixture_error(run, exc)
    except MissingEvidence as exc:
        return lifecycle.unable_to_grade(run, exc)
