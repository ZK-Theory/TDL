"""Versioned P0 operational profiles and resource conflict rules."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

import yaml

from research_system.canonical import canonical_bytes, sha256_hex


@dataclass(frozen=True)
class ResourceClaim:
    """Claim units on one named resource under a sharing mode."""

    mode: str
    units: int

    def __post_init__(self) -> None:
        """Validate the resource mode and positive unit count."""
        if self.mode not in {"exclusive", "capacity_shared", "read_shared"}:
            raise ValueError("unknown_resource_mode")
        if self.units <= 0:
            raise ValueError("resource_units_must_be_positive")


@dataclass(frozen=True)
class OperationalProfile:
    """Immutable runtime and evidence limits for one operational class."""

    profile_id: str
    max_runtime_s: int
    allow_child_process: bool
    allow_durable_writer: bool
    require_benchmark: bool
    require_periodic_heartbeat: bool
    require_checkpoint: bool
    heartbeat_disposition: str = "not_applicable"
    heartbeat_cadence_seconds: int | None = None
    heartbeat_additional_grace_seconds: int | None = None
    heartbeat_stale_threshold_seconds: int | None = None
    renewal_allowed: bool = False


@dataclass(frozen=True)
class OperationalProfilePolicy:
    """Immutable identity and content bindings for the current profile policy."""

    policy_id: str
    schema_version: str
    policy_revision: str
    raw_sha256: str
    canonical_sha256: str


class OperationalRiskRequest(Protocol):
    """Request attributes consumed by the operational risk floor."""

    restricted_data: bool
    external_write: bool
    expected_runtime_s: int
    exclusive_resources: bool
    checkpoint_uncertain: bool
    stop_confirmation_uncertain: bool


PROFILES = {
    "trivial": OperationalProfile("trivial-v1", 120, False, False, False, False, False),
    "bounded": OperationalProfile("bounded-v1", 3600, True, True, False, True, False),
    "long_running": OperationalProfile("long-running-v1", 172800, True, True, True, True, True),
}


def _load_current_operational_profile_policy() -> tuple[OperationalProfilePolicy, Mapping[str, OperationalProfile]]:
    """Load the accepted v1.1 profile policy with its exact byte bindings."""
    path = Path(__file__).resolve().parents[2] / ".research-system" / "policies" / "operational-profiles.v1-1.yaml"
    raw = path.read_bytes()
    payload = yaml.safe_load(raw)
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "policy_id",
        "policy_revision",
        "profiles",
    }:
        raise ValueError("operational_profile_policy_shape_invalid")
    if (
        payload["schema_version"] != "1.1.0"
        or payload["policy_revision"] != "1.1.0"
        or not isinstance(payload["policy_id"], str)
        or not payload["policy_id"].startswith("pol_")
    ):
        raise ValueError("operational_profile_policy_identity_invalid")
    raw_profiles = payload["profiles"]
    if not isinstance(raw_profiles, dict) or set(raw_profiles) != {
        "trivial",
        "bounded",
        "long_running",
    }:
        raise ValueError("operational_profile_policy_profiles_invalid")

    profiles: dict[str, OperationalProfile] = {}
    for name, raw_profile in raw_profiles.items():
        if not isinstance(raw_profile, dict):
            raise ValueError("operational_profile_invalid")
        heartbeat = raw_profile.get("heartbeat")
        renewal = raw_profile.get("renewal")
        if not isinstance(heartbeat, dict) or not isinstance(renewal, dict):
            raise ValueError("operational_profile_controls_invalid")
        profiles[name] = OperationalProfile(
            profile_id=str(raw_profile["profile_id"]),
            max_runtime_s=int(raw_profile["max_runtime_s"]),
            allow_child_process=bool(raw_profile["allow_child_process"]),
            allow_durable_writer=bool(raw_profile["allow_durable_writer"]),
            require_benchmark=bool(raw_profile["require_benchmark"]),
            require_periodic_heartbeat=bool(raw_profile["require_periodic_heartbeat"]),
            require_checkpoint=bool(raw_profile["require_checkpoint"]),
            heartbeat_disposition=str(heartbeat["disposition"]),
            heartbeat_cadence_seconds=(int(heartbeat["cadence_seconds"]) if "cadence_seconds" in heartbeat else None),
            heartbeat_additional_grace_seconds=(
                int(heartbeat["additional_grace_seconds"]) if "additional_grace_seconds" in heartbeat else None
            ),
            heartbeat_stale_threshold_seconds=(
                int(heartbeat["stale_threshold_seconds"]) if "stale_threshold_seconds" in heartbeat else None
            ),
            renewal_allowed=bool(renewal["allowed"]),
        )
    return (
        OperationalProfilePolicy(
            policy_id=payload["policy_id"],
            schema_version=payload["schema_version"],
            policy_revision=payload["policy_revision"],
            raw_sha256=sha256_hex(raw),
            canonical_sha256=sha256_hex(canonical_bytes(payload)),
        ),
        MappingProxyType(profiles),
    )


CURRENT_OPERATIONAL_PROFILE_POLICY, CURRENT_PROFILES = _load_current_operational_profile_policy()

RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


def max_risk(risks: Iterable[str]) -> str:
    """Return the strongest supplied risk classification.

    Args:
        risks: Non-empty iterable of canonical risk labels.

    Returns:
        Strongest risk label under the P0 ordering.

    Raises:
        KeyError: If a risk label is unknown.
        ValueError: If no risks are supplied.
    """
    return max(risks, key=RISK_ORDER.__getitem__)


def validate_profile_request(
    profile: OperationalProfile,
    *,
    expected_runtime_s: int,
    child_process: bool,
    durable_writer: bool,
) -> dict[str, str]:
    """Validate a requested execution surface against a profile envelope.

    Args:
        profile: Selected immutable operational profile.
        expected_runtime_s: Projected runtime in seconds.
        child_process: Whether child-process creation is requested.
        durable_writer: Whether a durable writer is requested.

    Returns:
        Profile identity and required closure mode.

    Raises:
        ValueError: If any request exceeds the selected profile.
    """
    if (
        expected_runtime_s > profile.max_runtime_s
        or child_process
        and not profile.allow_child_process
        or durable_writer
        and not profile.allow_durable_writer
    ):
        raise ValueError("profile_envelope_exceeded")
    return {"profile_id": profile.profile_id, "closure": "terminal_receipt"}


def profile_evidence_dispositions(
    profile: OperationalProfile,
) -> dict[str, str]:
    """Return explicit evidence requirements for an operational profile."""
    return {
        "benchmark": "required" if profile.require_benchmark else "not_applicable",
        "checkpoint": "required" if profile.require_checkpoint else "not_applicable",
        "heartbeat": ("required" if profile.require_periodic_heartbeat else "not_applicable"),
    }


def operational_risk_floor(request: OperationalRiskRequest) -> str:
    """Derive the minimum operational risk from request characteristics."""
    raises = []
    if request.restricted_data or request.external_write:
        raises.append("R3")
    if request.expected_runtime_s > 3600 or request.exclusive_resources:
        raises.append("R2")
    if request.checkpoint_uncertain or request.stop_confirmation_uncertain:
        raises.append("R3")
    return max_risk(["R0", *raises])


def has_resource_conflict(
    requested: Mapping[str, ResourceClaim],
    held: Mapping[str, ResourceClaim],
    capacities: Mapping[str, int],
) -> bool:
    """Return whether requested claims conflict with currently held claims.

    Args:
        requested: Claims requested by resource key.
        held: Existing claims by resource key.
        capacities: Declared capacities for capacity-shared resources.

    Returns:
        True when any overlapping resource claim is incompatible.
    """
    for key, requested_claim in requested.items():
        held_claim = held.get(key)
        if held_claim is None:
            continue
        modes = {requested_claim.mode, held_claim.mode}
        if "exclusive" in modes:
            return True
        if modes == {"read_shared"}:
            continue
        if modes == {"capacity_shared"}:
            capacity = capacities.get(key)
            if capacity is None:
                return True
            if requested_claim.units + held_claim.units > capacity:
                return True
            continue
        return True
    return False
