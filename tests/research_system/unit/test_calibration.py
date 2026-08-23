import json
from pathlib import Path

import pytest

from research_system.evals.calibration import calibrate_fixture
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.executors import require_executor
from research_system.errors import ArsError

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"


def test_missing_executor_is_fixture_definition_error():
    with pytest.raises(FixtureDefinitionError, match="executor_missing"):
        require_executor("F-999")


def test_lifecycle_fixture_rejects_raw_calibration_executor_injection():
    with pytest.raises(ArsError, match="lifecycle execution authority required"):
        calibrate_fixture(
            "F-025",
            fixture_root=FIXTURES,
            execute=lambda subject, payload: {"subject": subject, "payload": payload},
        )


def test_executor_receives_stimulus_payload_only():
    seen = []

    def spy(subject, payload):
        seen.append(dict(payload))
        return require_executor("F-001")(subject, payload)

    calibrate_fixture("F-001", fixture_root=FIXTURES, execute=spy)
    for payload in seen:
        assert set(payload) <= {"contract", "action", "producer_passed", "mutation_id"}
        assert not any(key.endswith("_evidence") for key in payload)


def test_f001_known_bad_fails_twice_and_known_good_passes_twice():
    record = calibrate_fixture("F-001", fixture_root=FIXTURES)
    assert [item.verdict for item in record.known_bad] == ["fail", "fail"]
    assert [item.reason for item in record.known_bad] == ["intended_failure"] * 2
    assert [item.verdict for item in record.known_good] == ["pass", "pass"]
    assert record.known_bad[0].normalized_bytes == record.known_bad[1].normalized_bytes
    assert record.blocking_verdict is None


def test_s014_known_bad_calibration_uses_its_declared_mutation() -> None:
    calls = []
    pre_expected = json.loads((FIXTURES / "S-014" / "expected" / "pre-control.json").read_text(encoding="utf-8"))[
        "assertions"
    ][0]["expected_evidence"]
    post_expected = json.loads((FIXTURES / "S-014" / "expected" / "post-control.json").read_text(encoding="utf-8"))[
        "assertions"
    ][0]["expected_evidence"]

    def spy(subject, payload):
        calls.append((subject, dict(payload)))
        return pre_expected if subject == "known_bad" else post_expected

    record = calibrate_fixture("S-014", fixture_root=FIXTURES, execute=spy)

    known_bad = [payload for subject, payload in calls if subject == "known_bad" and not payload.get("producer_passed")]
    assert [payload["mutation_id"] for payload in known_bad] == [
        "remove_registered_backup_restore_closure",
        "remove_registered_backup_restore_closure",
    ]
    assert [item.verdict for item in record.known_bad] == ["fail", "fail"]
    assert record.blocking_verdict is None


def test_observed_mismatch_is_fixture_error_not_pass():
    record = calibrate_fixture(
        "F-001",
        fixture_root=FIXTURES,
        execute=lambda subject, payload: {"unexpected": True},
    )
    assert {item.verdict for item in (*record.known_bad, *record.known_good)} == {"fixture_error"}
    assert record.blocking_verdict == "fixture_error"


def test_mutations_are_executed_and_detection_is_derived():
    calls = []

    def spy(subject, payload):
        calls.append((subject, payload.get("mutation_id"), payload.get("producer_passed", False)))
        return require_executor("F-001")(subject, payload)

    record = calibrate_fixture("F-001", fixture_root=FIXTURES, execute=spy)
    mutation_calls = [item for item in calls if item[1] is not None and item[2]]
    assert len(mutation_calls) == 2 * len(record.mutations)
    for mutation in record.mutations:
        assert [item.verdict for item in mutation.decisions] == ["pass", "pass"]
        assert [item.reason for item in mutation.decisions] == ["mutation_detected"] * 2


def test_undetected_mutation_is_fixture_error():
    good = require_executor("F-001")

    def defect_invisible(subject, payload):
        if payload.get("mutation_id") is not None:
            return good("known_good", {k: v for k, v in payload.items() if k != "mutation_id"})
        return good(subject, payload)

    record = calibrate_fixture("F-001", fixture_root=FIXTURES, execute=defect_invisible)
    assert record.mutations[0].decisions[0].verdict == "fixture_error"
    assert record.mutations[0].decisions[0].reason == "mutation_undetected"
    assert record.blocking_verdict == "fixture_error"


def test_mutation_detection_ignores_producer_flag():
    executor = require_executor("F-001")
    payload = {
        "contract": "immutable_message_ownership",
        "action": {"operation": "publish_message", "slot": "task.md", "incoming_owner": "T0.12"},
    }
    flagged = executor("known_bad", {**payload, "producer_passed": True})
    unflagged = executor("known_bad", payload)
    assert flagged == unflagged


def test_f036_three_named_mutations_detected():
    record = calibrate_fixture("F-036", fixture_root=FIXTURES)
    assert record.fixture_revision == "r2"
    assert record.declared_mutation_ids == (
        "expected_value_anchoring",
        "degenerate_constant_fallback",
        "null_operation_invariance",
    )
    for mutation in record.mutations:
        assert [item.reason for item in mutation.decisions] == ["mutation_detected"] * 2
    # F-036 has a required M grader, so it stays blocked -- but honestly:
    assert record.blocking_verdict == "unable_to_grade"
