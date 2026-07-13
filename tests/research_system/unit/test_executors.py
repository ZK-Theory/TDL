"""Unit tests for the per-fixture executor registry.

Task 1 registers only the F-001 control/store executor; Tasks 2-3 append
coverage for the remaining P0 cases to this module.
"""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.evals.calibration import calibrate_fixture
from research_system.evals import coverage as coverage_module
from research_system.evals.coverage import P0_CASES
from research_system.evals.executors import EXECUTORS, require_executor
from research_system.evals.executors.control_store import (
    CONTROL_STORE_EXECUTORS,
    execute_f001,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"


def test_f020_r2_preserves_r1_observations_and_derives_ten_control_operations():
    result = _f020_result()
    assert result["semantic_parity"] is True
    assert result["poorer_source_overwrite_blocked"] is True
    assert result["affected_dispatch_waits"] is True
    assert sum(len(item["operations"]) for item in result["controls"].values()) == 10


def _f020_result() -> dict:
    return require_executor("F-020")(
        "known_good",
        {
            "action": {
                "operation": "compare_adapter_policies",
                "source_controls": ["readiness", "dispatch_guard"],
                "target_controls": ["readiness"],
            }
        },
    )


def _assert_only_operation_changed(before: dict, after: dict, control_id: str, operation: str) -> None:
    assert {key: before[key] for key in before if key != "controls"} == {
        key: after[key] for key in after if key != "controls"
    }
    for observed_control, control in before["controls"].items():
        for observed_operation, record in control["operations"].items():
            changed = after["controls"][observed_control]["operations"][observed_operation]
            if (observed_control, observed_operation) == (control_id, operation):
                assert changed != record
            else:
                assert changed == record


def test_f020_authorized_undeclared_shell_regression_changes_only_shell_evidence(monkeypatch):
    from research_system.adapters import provider as provider_module

    before = _f020_result()
    original = getattr(provider_module, "enforce_provider_operation_policy", None)

    def allow_undeclared_shell(command, policy):
        if command.operation == "undeclared_shell":
            return None
        return original(command, policy)

    monkeypatch.setattr(
        provider_module,
        "enforce_provider_operation_policy",
        allow_undeclared_shell,
        raising=False,
    )
    _assert_only_operation_changed(before, _f020_result(), "no-shell", "invoke_declared_tool")


def test_f020_direct_writer_regression_changes_only_command_service_evidence(monkeypatch):
    from research_system.operations import coordinator

    before = _f020_result()

    def direct_writer(command_service, command):
        return SimpleNamespace(
            receipt=command_service.submit(command),
            state_change_path="direct_event_writer",
            direct_writer_used=True,
        )

    monkeypatch.setattr(coordinator, "submit_ars_command", direct_writer, raising=False)
    _assert_only_operation_changed(
        before,
        _f020_result(),
        "no-direct-event-write",
        "submit_ars_command",
    )


@pytest.mark.parametrize(
    "operation",
    ("cancel_provider_work", "query_provider_status", "request_model_work", "request_review"),
)
def test_f020_default_live_route_regression_changes_only_selected_operation(monkeypatch, operation):
    from research_system.adapters import provider as provider_module

    before = _f020_result()
    original = getattr(provider_module, "enforce_provider_operation_policy", None)

    def allow_selected_live_route(command, policy):
        if command.operation == operation:
            return None
        return original(command, policy)

    monkeypatch.setattr(
        provider_module,
        "enforce_provider_operation_policy",
        allow_selected_live_route,
        raising=False,
    )
    _assert_only_operation_changed(
        before,
        _f020_result(),
        "no-live-provider-by-default",
        operation,
    )


@pytest.mark.parametrize(
    "operation",
    ("deliver_context", "deliver_message", "request_model_work", "request_review"),
)
def test_f020_receipt_retention_regression_changes_only_selected_operation(monkeypatch, operation):
    from research_system.adapters import provider as provider_module

    before = _f020_result()
    original = provider_module.normalize_receipt

    def retain_selected_raw_transcript(command, result):
        receipt = original(command, result)
        if command.operation == operation:
            return replace(receipt, redaction="raw_transport_content_retained")
        return receipt

    monkeypatch.setattr(provider_module, "normalize_receipt", retain_selected_raw_transcript)
    after = _f020_result()
    _assert_only_operation_changed(
        before,
        after,
        "no-raw-transcript-retention",
        operation,
    )
    assert after["controls"]["no-raw-transcript-retention"]["operations"][operation][
        "receipt_mode"
    ] == "raw_retained"


def test_f020_declared_tool_evidence_depends_on_adapter_probe(monkeypatch):
    from research_system.adapters.provider import ProviderAdapter
    from research_system.errors import ArsError

    def reject_every_issue(self, command, managed_content):
        del self, command, managed_content
        raise ArsError("probe rejected")

    monkeypatch.setattr(ProviderAdapter, "issue", reject_every_issue)
    observed = require_executor("F-020")(
        "known_good",
        {
            "action": {
                "operation": "compare_adapter_policies",
                "source_controls": ["readiness", "dispatch_guard"],
                "target_controls": ["readiness"],
            }
        },
    )["controls"]
    assert observed["no-shell"]["operations"]["invoke_declared_tool"]["declared_tool_only"] is False


ADAPTER_SCIENTIFIC_CLEAN = [
    "F-007",
    "F-008",
    "F-009",
    "F-010",
    "F-011",
    "F-012",
    "F-013",
    "F-014",
    "F-020",
    "F-032",
    "F-034",
    "S-003",
    "S-004",
    "S-013",
]

_F001_PAYLOAD = {
    "contract": "immutable_message_ownership",
    "action": {
        "operation": "publish_message",
        "slot": "task.md",
        "incoming_owner": "T0.12",
    },
}


def test_control_store_registers_f001():
    assert CONTROL_STORE_EXECUTORS["F-001"] is execute_f001
    assert EXECUTORS["F-001"] is execute_f001
    assert require_executor("F-001") is execute_f001


def test_execute_f001_known_bad_reproduces_destructive_overwrite():
    observed = execute_f001("known_bad", _F001_PAYLOAD)
    assert observed == {
        "existing_owner": "T0.3",
        "destructive_overwrite": True,
        "surviving_ids": ["T0.12"],
    }


def test_execute_f001_known_good_preserves_both_owners():
    observed = execute_f001("known_good", _F001_PAYLOAD)
    assert observed == {
        "destructive_overwrite": False,
        "surviving_ids": ["T0.3", "T0.12"],
        "collision_visible": True,
    }


def test_adapter_scientific_paired_calibration_is_real_and_clean():
    for fixture_id in ADAPTER_SCIENTIFIC_CLEAN:
        record = calibrate_fixture(fixture_id, fixture_root=FIXTURES)
        assert [d.verdict for d in record.known_bad] == ["fail", "fail"], fixture_id
        assert [d.verdict for d in record.known_good] == ["pass", "pass"], fixture_id
        assert all(d.verdict == "pass" for m in record.mutations for d in m.decisions), fixture_id
        assert record.blocking_verdict in (None, "unable_to_grade"), fixture_id


def test_f036_calibrates_honestly_as_unable_to_grade():
    record = calibrate_fixture("F-036", fixture_root=FIXTURES)
    assert record.blocking_verdict == "unable_to_grade"
    assert {d.verdict for d in record.known_good} == {"pass"}


def test_f012_null_shuffle_actually_changes_the_tested_object():
    from research_system.evals.executors.adapter_scientific import execute_f012

    good = execute_f012(
        "known_good",
        {
            "action": {
                "operation": "apply_null_shuffle",
                "pre_tested_object_hash": "same",
                "post_tested_object_hash": "same",
                "producer_passed": True,
            }
        },
    )
    assert good["tested_object_changed"] is True
    assert good["producer_flag_trusted"] is False


def test_every_p0_case_has_exactly_one_registered_executor():
    assert len(P0_CASES) == 37
    assert set(EXECUTORS) == set(coverage_module.FOUNDATION_CASES)


def test_full_corpus_calibration_has_no_fixture_errors():
    expected_errors = set()
    errors = {
        fixture_id
        for fixture_id in sorted(P0_CASES)
        if calibrate_fixture(fixture_id, fixture_root=FIXTURES).blocking_verdict == "fixture_error"
    }
    assert errors == expected_errors
