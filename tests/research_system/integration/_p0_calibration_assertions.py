"""Shared assertions for the exact P0 paired-calibration corpus."""

from collections.abc import Iterable

from research_system.evals.calibration import calibrate_fixture

LIVE_JUDGMENT_CLASSES = frozenset({'M', 'H'})


def assert_paired_calibration(fixture_ids: Iterable[str]) -> None:
    for fixture_id in fixture_ids:
        record = calibrate_fixture(fixture_id)
        assert record.fixture_id == fixture_id
        assert record.fixture_revision == 'r1'
        assert record.policy_revision == 'p0-calibration-v1'
        assert record.repetitions == 2
        assert len(record.known_bad) == 2
        assert len(record.known_good) == 2
        assert len({item.normalized_bytes for item in record.known_bad}) == 1
        assert len({item.normalized_bytes for item in record.known_good}) == 1
        assert all(item.oracle_hash != item.subject_hash for item in record.known_bad)
        assert all(item.oracle_hash != item.subject_hash for item in record.known_good)
        assert all(item.independently_recomputed for item in record.known_bad)
        assert all(item.independently_recomputed for item in record.known_good)

        requires_live_judgment = bool(
            LIVE_JUDGMENT_CLASSES.intersection(record.required_grader_classes)
        )
        if requires_live_judgment:
            assert {item.verdict for item in record.known_bad} == {'unable_to_grade'}
            assert {item.verdict for item in record.known_good} == {'unable_to_grade'}
            assert all(
                item.reason == 'required_live_judgment_unavailable'
                for item in (*record.known_bad, *record.known_good)
            )
        else:
            assert {item.verdict for item in record.known_bad} == {'fail'}
            assert {item.verdict for item in record.known_good} == {'pass'}
            assert all(item.reason == record.failure_class for item in record.known_bad)
            assert all(item.reason == 'control_satisfied' for item in record.known_good)
