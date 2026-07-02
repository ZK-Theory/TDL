from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from research_system.operations.profiles import (
    PROFILES,
    OperationalProfile,
    ResourceClaim,
    has_resource_conflict,
    operational_risk_floor,
    profile_evidence_dispositions,
    validate_profile_request,
)


def _trivial():
    return OperationalProfile("trivial-v1", 120, False, False, False, False, False)


def test_trivial_profile_requires_typed_grant_and_terminal_closure():
    grant = validate_profile_request(
        _trivial(),
        expected_runtime_s=60,
        child_process=False,
        durable_writer=False,
    )
    assert grant == {"profile_id": "trivial-v1", "closure": "terminal_receipt"}


def test_trivial_profile_marks_benchmark_checkpoint_heartbeat_not_applicable():
    assert profile_evidence_dispositions(_trivial()) == {
        "benchmark": "not_applicable",
        "checkpoint": "not_applicable",
        "heartbeat": "not_applicable",
    }


def test_trivial_profile_cannot_spawn_process_or_open_durable_writer():
    with pytest.raises(ValueError, match="profile_envelope_exceeded"):
        validate_profile_request(
            _trivial(),
            expected_runtime_s=60,
            child_process=True,
            durable_writer=True,
        )


def test_operational_floor_raises_route_risk_before_selection():
    request = SimpleNamespace(
        restricted_data=True,
        external_write=False,
        expected_runtime_s=60,
        exclusive_resources=(),
        checkpoint_uncertain=False,
        stop_confirmation_uncertain=False,
    )
    assert operational_risk_floor(request) == "R3"


@pytest.mark.parametrize(
    ("requested", "held", "capacity", "expected"),
    [
        (ResourceClaim("exclusive", 1), ResourceClaim("exclusive", 1), 1, True),
        (ResourceClaim("exclusive", 1), ResourceClaim("read_shared", 1), 1, True),
        (ResourceClaim("read_shared", 1), ResourceClaim("exclusive", 1), 1, True),
        (ResourceClaim("read_shared", 1), ResourceClaim("read_shared", 1), 1, False),
        (
            ResourceClaim("capacity_shared", 4),
            ResourceClaim("capacity_shared", 5),
            10,
            False,
        ),
        (
            ResourceClaim("capacity_shared", 6),
            ResourceClaim("capacity_shared", 5),
            10,
            True,
        ),
        (
            ResourceClaim("read_shared", 1),
            ResourceClaim("capacity_shared", 1),
            10,
            True,
        ),
        (
            ResourceClaim("capacity_shared", 1),
            ResourceClaim("read_shared", 1),
            10,
            True,
        ),
    ],
)
def test_resource_conflict_matrix_is_symmetric(requested, held, capacity, expected):
    assert (
        has_resource_conflict(
            {"gpu:0": requested}, {"gpu:0": held}, {"gpu:0": capacity}
        )
        is expected
    )


def test_operational_profile_yaml_is_authoritative():
    root = Path(__file__).resolve().parents[3]
    payload = yaml.safe_load(
        (
            root
            / ".research-system"
            / "policies"
            / "operational-profiles.yaml"
        ).read_text(encoding="utf-8")
    )
    assert payload["profiles"] == {
        name: {
            "profile_id": profile.profile_id,
            "max_runtime_s": profile.max_runtime_s,
            "allow_child_process": profile.allow_child_process,
            "allow_durable_writer": profile.allow_durable_writer,
            "require_benchmark": profile.require_benchmark,
            "require_periodic_heartbeat": profile.require_periodic_heartbeat,
            "require_checkpoint": profile.require_checkpoint,
        }
        for name, profile in PROFILES.items()
    }
