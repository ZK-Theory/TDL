"""Paired calibration for context and routing fixtures."""

from tests.research_system.integration._p0_calibration_assertions import (
    assert_paired_calibration,
)
from research_system.evals.calibration import calibrate_fixture

CONTEXT_ROUTING_FIXTURES = (
    'F-021', 'F-022', 'F-025', 'F-026', 'F-027',
    'F-028', 'F-031', 'F-033', 'F-035', 'F-036',
)


def test_context_routing_fixtures_have_paired_byte_stable_calibration():
    assert_paired_calibration(CONTEXT_ROUTING_FIXTURES)


def test_f036_detects_all_three_mutations_independently_twice():
    record = calibrate_fixture('F-036')
    assert {item.mutation_id for item in record.mutations} == {
        'expected_value_anchoring',
        'degenerate_fallback',
        'null_invariance',
    }
    for mutation in record.mutations:
        assert len(mutation.known_bad) == 2
        assert len(mutation.known_good) == 2
        assert {item.verdict for item in mutation.known_bad} == {'fail'}
        assert {item.verdict for item in mutation.known_good} == {'pass'}
        assert len({item.normalized_bytes for item in mutation.known_bad}) == 1
        assert len({item.normalized_bytes for item in mutation.known_good}) == 1
        assert all(item.reason == mutation.mutation_id for item in mutation.known_bad)
        assert all(item.reason == 'control_satisfied' for item in mutation.known_good)
