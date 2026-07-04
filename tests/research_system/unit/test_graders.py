from types import SimpleNamespace

import pytest

from research_system.evals.errors import UnableToGrade
from research_system.evals.graders import validate_grader_result
from research_system.evals.models import GraderResult, TraceEnvelope
from research_system.evals.trace import assert_trace_complete


UUID7 = "01978abc-0001-7000-8000-000000000001"


def _trace(**changes: object) -> TraceEnvelope:
    values = {
        "trace_id": f"trc_{UUID7}",
        "evaluation_run_id": f"run_{UUID7}",
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "subject_id": "candidate-v1",
        "subject_hash": "a" * 64,
        "items": (),
        "issued_commands": (),
        "issued_resources": (),
        "route_decision_id": None,
        "routing_evidence_snapshot_id": None,
        "canonical_policy_bundle_id": None,
        "adapter_manifest_version": None,
        "resource_record_ids": (),
        "tool_records": (),
        "artefact_refs": (),
        "review_refs": (),
        "decision_refs": (),
        "claim_refs": (),
        "present_evidence_classes": ("provider_receipt",),
        "missing_segments": (),
        "clock_source": "canonical_sequence",
        "ordering_method": "w2_sequence_and_causation",
        "redaction_record_hash": "b" * 64,
        "content_hash": "c" * 64,
        "trace_complete": True,
    }
    values.update(changes)
    return TraceEnvelope(**values)


def _result(**changes: object) -> GraderResult:
    values = {
        "grader_result_id": f"grr_{UUID7}",
        "evaluation_run_id": f"run_{UUID7}",
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "grader_id": "state",
        "grader_class": "D",
        "grader_version": "v1",
        "verdict": "pass",
        "severity": "critical",
        "critical": True,
        "required": True,
        "subject_hash": "a" * 64,
        "trace_hash": "b" * 64,
        "oracle_hash": "c" * 64,
        "policy_hash": "d" * 64,
        "threshold_policy_hash": "e" * 64,
        "evidence_refs": ("evidence-1",),
        "independently_recomputed": True,
        "producer_family": "candidate-family",
        "grader_family": "deterministic",
        "context_relationship": "deterministic_independent",
        "limitations": (),
        "redactions": (),
        "duration_ms": 1,
        "cost_microunits": 0,
        "executed_by_actor_id": f"act_{UUID7}",
    }
    values.update(changes)
    return GraderResult(**values)


def test_missing_provider_receipt_is_unable_to_grade_and_blocking():
    fixture = SimpleNamespace(required_evidence_classes=("provider_receipt",))
    with pytest.raises(UnableToGrade, match="missing evidence classes"):
        assert_trace_complete(
            _trace(present_evidence_classes=(), trace_complete=False),
            fixture,
        )


def test_issued_command_without_terminal_record_is_unable_to_grade():
    fixture = SimpleNamespace(required_evidence_classes=())
    trace = _trace(issued_commands=({"command_id": "pcmd-1"},))
    with pytest.raises(UnableToGrade, match="terminal evidence"):
        assert_trace_complete(trace, fixture)


def test_declared_trace_gap_is_unable_to_grade():
    fixture = SimpleNamespace(required_evidence_classes=())
    trace = _trace(trace_complete=False, missing_segments=("resource_stop",))
    with pytest.raises(UnableToGrade, match="missing trace segments"):
        assert_trace_complete(trace, fixture)


def test_complete_trace_passes_without_inferred_evidence():
    fixture = SimpleNamespace(required_evidence_classes=("provider_receipt",))
    assert assert_trace_complete(_trace(), fixture) is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"threshold_policy_hash": ""}, "threshold policy"),
        ({"context_relationship": "producer_correlated"}, "independence"),
        ({"independently_recomputed": False}, "independent recomputation"),
    ],
)
def test_required_judgment_never_passes_with_missing_policy_or_independence(
    change,
    message,
):
    with pytest.raises(UnableToGrade, match=message):
        validate_grader_result(
            _result(**change),
            expected_subject_hash="a" * 64,
            expected_trace_hash="b" * 64,
            expected_oracle_hash="c" * 64,
            expected_policy_hash="d" * 64,
            expected_threshold_policy_hash="e" * 64,
            required_independence="deterministic_independent",
        )


def test_exact_immutable_grader_binding_is_gradeable():
    assert (
        validate_grader_result(
            _result(),
            expected_subject_hash="a" * 64,
            expected_trace_hash="b" * 64,
            expected_oracle_hash="c" * 64,
            expected_policy_hash="d" * 64,
            expected_threshold_policy_hash="e" * 64,
            required_independence="deterministic_independent",
        )
        is None
    )
