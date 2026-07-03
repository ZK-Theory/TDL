"""Owned immutable lifecycle for one fixture evaluation attempt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class LifecycleRun:
    evaluation_run_id: str
    fixture_id: str
    fixture_revision: str
    subject_id: str


@dataclass(frozen=True, slots=True)
class LifecycleOutcome:
    evaluation_run_id: str
    status: str
    trace_hash: str | None
    result_hash: str | None
    reason: str | None


class EvaluationLifecycle:
    """Create immutable run identity and close every terminal outcome."""

    def start(self, fixture: Any, subject: Any) -> LifecycleRun:
        subject_id = str(getattr(subject, 'subject_id', type(subject).__name__))
        identity = canonical_bytes(
            {
                'fixture_id': fixture.fixture_id,
                'fixture_revision': fixture.fixture_revision,
                'subject_id': subject_id,
            }
        )
        return LifecycleRun(
            evaluation_run_id='evr_' + sha256_hex(identity)[:32],
            fixture_id=str(fixture.fixture_id),
            fixture_revision=str(fixture.fixture_revision),
            subject_id=subject_id,
        )

    def finish(
        self,
        run: LifecycleRun,
        trace: Any,
        results: tuple[Any, ...],
    ) -> LifecycleOutcome:
        return LifecycleOutcome(
            evaluation_run_id=run.evaluation_run_id,
            status='finished',
            trace_hash=sha256_hex(canonical_bytes(_jsonable(trace))),
            result_hash=sha256_hex(canonical_bytes(_jsonable(results))),
            reason=None,
        )

    def fixture_error(self, run: LifecycleRun, error: Exception) -> LifecycleOutcome:
        return LifecycleOutcome(
            run.evaluation_run_id,
            'fixture_error',
            None,
            None,
            str(error),
        )

    def unable_to_grade(
        self,
        run: LifecycleRun,
        error: Exception,
    ) -> LifecycleOutcome:
        return LifecycleOutcome(
            run.evaluation_run_id,
            'unable_to_grade',
            None,
            None,
            str(error),
        )
