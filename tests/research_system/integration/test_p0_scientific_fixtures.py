"""Paired calibration for scientific and anti-gaming fixtures."""

from tests.research_system.integration._p0_calibration_assertions import (
    assert_paired_calibration,
)
from research_system.evals.reference_systems import (
    grade_f011,
    grade_f012,
    grade_f013,
    grade_f014,
)

SCIENTIFIC_FIXTURES = ('F-011', 'F-012', 'F-013', 'F-014', 'F-036')


def test_scientific_fixtures_have_paired_byte_stable_calibration():
    assert_paired_calibration(SCIENTIFIC_FIXTURES)


def test_f011_rejects_refit_and_requires_frozen_fingerprint():
    assert grade_f011([{'operation': 'fit'}], 'frozen-v1') == 'fail'
    assert grade_f011(
        [{'operation': 'transform', 'transform_fingerprint': 'frozen-v1'}],
        'frozen-v1',
    ) == 'pass'


def test_f012_ignores_producer_claim_and_recomputes_difference():
    assert grade_f012('same', 'same', producer_pass_flag=True) == 'fail'
    assert grade_f012('before', 'after', producer_pass_flag=False) == 'pass'


def test_f013_requires_one_input_vintage():
    assert grade_f013([{'vintage_id': 'v1'}, {'vintage_id': 'v2'}]) == 'fail'
    assert grade_f013([{'vintage_id': 'v1'}, {'vintage_id': 'v1'}]) == 'pass'


def test_f014_requires_independent_eligible_approver():
    assert grade_f014('actor-a', 'actor-a', 'I1') == 'fail'
    assert grade_f014('actor-a', 'actor-b', 'I1') == 'pass'
