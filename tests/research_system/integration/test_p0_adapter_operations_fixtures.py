"""Paired calibration for provider-adapter and operations fixtures."""

from tests.research_system.integration._p0_calibration_assertions import (
    assert_paired_calibration,
)

ADAPTER_OPERATIONS_FIXTURES = (
    'F-007', 'F-008', 'F-009', 'F-010', 'F-020', 'F-032', 'F-034',
    'S-003', 'S-004', 'S-013',
)


def test_adapter_operations_fixtures_have_paired_byte_stable_calibration():
    assert_paired_calibration(ADAPTER_OPERATIONS_FIXTURES)
