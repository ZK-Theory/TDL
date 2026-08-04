import hashlib
from pathlib import Path
import re
from types import SimpleNamespace

import pytest
import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.operations.profiles import (
    CURRENT_OPERATIONAL_PROFILE_POLICY,
    CURRENT_PROFILES,
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
    assert has_resource_conflict({"gpu:0": requested}, {"gpu:0": held}, {"gpu:0": capacity}) is expected


def test_operational_profile_yaml_is_authoritative():
    root = Path(__file__).resolve().parents[3]
    payload = yaml.safe_load(
        (root / ".research-system" / "policies" / "operational-profiles.yaml").read_text(encoding="utf-8")
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


def test_operational_profile_v1_1_policy_freezes_heartbeat_and_renewal_controls():
    root = Path(__file__).resolve().parents[3]
    policies = root / ".research-system" / "policies"
    legacy = yaml.safe_load((policies / "operational-profiles.yaml").read_text(encoding="utf-8"))
    current_path = policies / "operational-profiles.v1-1.yaml"
    current_raw = current_path.read_bytes()
    current = yaml.safe_load(current_raw)

    assert legacy["schema_version"] == "1.0.0"
    assert current["schema_version"] == "1.1.0"
    assert current["policy_id"] == "pol_0198825f-7a2b-7f11-8bc1-1c1a00000001"
    assert re.fullmatch(
        r"pol_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        current["policy_id"],
    )
    assert current["policy_revision"] == "1.1.0"
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.policy_id == current["policy_id"]
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.schema_version == current["schema_version"]
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.policy_revision == current["policy_revision"]
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.raw_sha256 == (
        "b456673fa7ba2d7125d6622373a74ac1f739bdc9259e316042035a48c014ffa2"
    )
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.raw_sha256 == hashlib.sha256(current_raw).hexdigest()
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.canonical_sha256 == sha256_hex(canonical_bytes(current))
    assert CURRENT_OPERATIONAL_PROFILE_POLICY.canonical_sha256 == (
        "1d5b42adf4fd74ba5e4ba1a89af4e6cd7e38d7ad2ff7431501cd2f34f44be72b"
    )
    for profile_name in ("bounded", "long_running"):
        profile = current["profiles"][profile_name]
        assert profile["heartbeat"] == {
            "disposition": "required",
            "cadence_seconds": 300,
            "additional_grace_seconds": 600,
            "stale_threshold_seconds": 900,
        }
        assert profile["renewal"] == {"allowed": True}
        assert CURRENT_PROFILES[profile_name].heartbeat_disposition == "required"
        assert CURRENT_PROFILES[profile_name].heartbeat_cadence_seconds == 300
        assert CURRENT_PROFILES[profile_name].heartbeat_additional_grace_seconds == 600
        assert CURRENT_PROFILES[profile_name].heartbeat_stale_threshold_seconds == 900
        assert CURRENT_PROFILES[profile_name].renewal_allowed is True
    assert current["profiles"]["trivial"]["heartbeat"] == {"disposition": "not_applicable"}
    assert current["profiles"]["trivial"]["renewal"] == {"allowed": False}
    assert CURRENT_PROFILES["trivial"].heartbeat_disposition == "not_applicable"
    assert CURRENT_PROFILES["trivial"].heartbeat_cadence_seconds is None
    assert CURRENT_PROFILES["trivial"].renewal_allowed is False
