"""Paired calibration for control-store fixtures."""

from tests.research_system.integration._p0_calibration_assertions import (
    assert_paired_calibration,
)
from research_system.evals.calibration import calibrate_fixture

CONTROL_FIXTURES = (
    'F-001', 'F-002', 'F-003', 'F-004', 'F-005',
    'S-001', 'S-002', 'S-006', 'S-008', 'S-009', 'S-010', 'S-011', 'S-012',
)


def test_control_store_fixtures_have_paired_byte_stable_calibration():
    assert_paired_calibration(CONTROL_FIXTURES)


def test_fixture_revision_mismatch_is_closed_fixture_error():
    record = calibrate_fixture('F-001', expected_fixture_revision='r999')
    assert {item.verdict for item in record.known_bad} == {'fixture_error'}
    assert {item.verdict for item in record.known_good} == {'fixture_error'}
    assert all(
        item.reason == 'fixture_revision_mismatch'
        for item in (*record.known_bad, *record.known_good)
    )


def test_calibration_policy_mismatch_is_closed_fixture_error():
    record = calibrate_fixture('F-001', expected_policy_revision='unexpected')
    assert {item.verdict for item in record.known_bad} == {'fixture_error'}
    assert {item.verdict for item in record.known_good} == {'fixture_error'}
    assert all(
        item.reason == 'calibration_policy_mismatch'
        for item in (*record.known_bad, *record.known_good)
    )
