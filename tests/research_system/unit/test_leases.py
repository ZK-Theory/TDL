import pytest

from research_system.operations.leases import (
    artifact_disposition,
    heartbeat_disposition,
    runtime_disposition,
    stop_confirmation,
)
from research_system.operations.resources import authorize_operational_surface


def test_trivial_heartbeat_requires_explicit_not_applicable_reason():
    expected = {
        "status": "not_applicable",
        "reason": "terminal_receipt_closes_lease",
    }
    assert heartbeat_disposition("trivial", expected) == expected
    with pytest.raises(ValueError, match="invalid trivial heartbeat"):
        heartbeat_disposition("trivial", {"status": "not_applicable"})


def test_hard_runtime_limit_requires_stop_without_scientific_claim():
    assert runtime_disposition(elapsed_s=721, hard_limit_s=720) == {
        "status": "stop_required",
        "reason": "hard_runtime_limit",
    }


def test_late_artifact_is_preserved_but_restricted():
    assert artifact_disposition(
        observed_at="2026-07-02T12:01:00Z",
        lease_expires_at="2026-07-02T12:00:00Z",
    ) == {
        "status": "late_artifact",
        "preserve": True,
        "acceptance_allowed": False,
    }


def test_stop_remains_uncertain_until_every_writer_and_process_is_terminal():
    assert stop_confirmation(
        provider="terminal",
        process_children="terminal",
        output_writer="unknown",
        checkpoint_writer="terminal",
    ) == "stop_uncertain"


def test_operational_surface_cannot_expand_grant():
    with pytest.raises(ValueError, match="unauthorized_operational_expansion"):
        authorize_operational_surface(
            requested={"roots": {"C:/tmp", "D:/outside"}, "tools": {"python"}},
            granted={"roots": {"C:/tmp"}, "tools": {"python"}},
        )
