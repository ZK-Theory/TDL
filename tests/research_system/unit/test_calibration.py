from pathlib import Path

from research_system.evals.calibration import calibrate_fixture


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"


def test_calibration_executes_each_subject_twice_and_is_byte_stable():
    calls = []

    def execute(subject, stimulus):
        calls.append((subject, stimulus["fixture_id"]))
        return {"property_satisfied": subject == "known_good"}

    record = calibrate_fixture("F-001", fixture_root=FIXTURES, execute=execute)
    assert calls == [
        ("known_bad", "F-001"),
        ("known_bad", "F-001"),
        ("known_good", "F-001"),
        ("known_good", "F-001"),
    ]
    assert [item.verdict for item in record.known_bad] == ["fail", "fail"]
    assert [item.verdict for item in record.known_good] == ["pass", "pass"]
    assert record.known_bad[0].normalized_bytes == record.known_bad[1].normalized_bytes
    assert record.known_good[0].normalized_bytes == record.known_good[1].normalized_bytes


def test_wrong_known_bad_evidence_is_fixture_error():
    record = calibrate_fixture(
        "F-001",
        fixture_root=FIXTURES,
        execute=lambda subject, stimulus: {"observed_evidence": stimulus[f"{subject}_evidence"]},
    )
    assert [item.verdict for item in record.known_bad] == [
        "fixture_error",
        "fixture_error",
    ]


def test_unexpected_controlled_failure_is_fixture_error_not_pass():
    record = calibrate_fixture(
        "F-001",
        fixture_root=FIXTURES,
        execute=lambda subject, stimulus: {"property_satisfied": False},
    )
    assert [item.verdict for item in record.known_good] == [
        "fixture_error",
        "fixture_error",
    ]


def test_required_live_judgment_remains_blocking():
    record = calibrate_fixture("F-014", fixture_root=FIXTURES)
    assert record.blocking_verdict == "unable_to_grade"


def test_declared_mutations_are_recorded_not_calibrated():
    # Interim honest state (review C-2): mutations are declared and recorded,
    # but the module executes none and fabricates no detection. Real mutation
    # execution/detection lands in WP4.8.
    record = calibrate_fixture("F-036", fixture_root=FIXTURES)
    assert record.mutations == ()
    assert record.mutation_calibration_status == "not_calibrated"
    assert record.declared_mutation_ids
