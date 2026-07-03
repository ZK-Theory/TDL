import pytest

from research_system.evals.models import TraceEnvelope


UUID7 = '01978abc-0001-7000-8000-000000000001'


def _trace(**changes: object) -> TraceEnvelope:
    values = {
        'trace_id': f'trc_{UUID7}',
        'evaluation_run_id': f'run_{UUID7}',
        'fixture_id': 'F-001',
        'fixture_revision': 'r1',
        'subject_id': 'candidate-v1',
        'subject_hash': 'a' * 64,
        'items': (),
        'issued_commands': (),
        'route_decision_id': None,
        'routing_evidence_snapshot_id': None,
        'canonical_policy_bundle_id': None,
        'adapter_manifest_version': None,
        'resource_record_ids': (),
        'tool_records': (),
        'artefact_refs': (),
        'review_refs': (),
        'decision_refs': (),
        'claim_refs': (),
        'present_evidence_classes': (),
        'missing_segments': (),
        'clock_source': 'canonical_sequence',
        'ordering_method': 'w2_sequence_and_causation',
        'redaction_record_hash': 'b' * 64,
        'content_hash': 'c' * 64,
    }
    values.update(changes)
    return TraceEnvelope(**values)


def test_trace_requires_terminal_receipt_or_missing_evidence_record():
    trace = _trace(issued_commands=({'command_id': 'pcmd-1'},))
    with pytest.raises(ValueError, match='terminal_or_missing_evidence_required'):
        trace.validate_terminal_evidence()


@pytest.mark.parametrize('terminal_field', ['terminal_ref', 'missing_evidence_ref'])
def test_trace_accepts_explicit_terminal_or_missing_evidence(terminal_field):
    trace = _trace(
        issued_commands=({'command_id': 'pcmd-1', terminal_field: 'receipt-1'},)
    )
    trace.validate_terminal_evidence()


def test_trace_reports_required_evidence_classes_that_are_absent():
    trace = _trace(present_evidence_classes=('command_receipt',))
    assert trace.missing_evidence_classes(
        ('command_receipt', 'resource_stop_record')
    ) == ('resource_stop_record',)


def test_trace_rejects_declared_complete_with_missing_segments():
    with pytest.raises(ValueError, match='complete_trace_has_missing_segments'):
        _trace(trace_complete=True, missing_segments=('provider_receipt',))
