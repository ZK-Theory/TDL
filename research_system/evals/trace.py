"""Trace-completeness enforcement for W6 graders."""

from research_system.evals.errors import UnableToGrade
from research_system.evals.models import FixtureDefinition, TraceEnvelope


def assert_trace_complete(
    trace: TraceEnvelope,
    fixture: FixtureDefinition,
) -> None:
    """Require declared evidence classes, terminal records, and closed segments."""
    missing_classes = trace.missing_evidence_classes(
        fixture.required_evidence_classes
    )
    if missing_classes:
        raise UnableToGrade(
            'missing evidence classes: ' + ','.join(missing_classes)
        )
    try:
        trace.validate_terminal_evidence()
    except ValueError as exc:
        raise UnableToGrade(f'missing terminal evidence: {exc}') from exc
    if trace.missing_segments:
        raise UnableToGrade(
            'missing trace segments: ' + ','.join(trace.missing_segments)
        )
    if not trace.trace_complete:
        raise UnableToGrade('trace not declared complete')
