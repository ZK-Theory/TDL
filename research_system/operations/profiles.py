"""Versioned P0 operational profiles and resource conflict rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceClaim:
    mode: str
    units: int

    def __post_init__(self):
        if self.mode not in {"exclusive", "capacity_shared", "read_shared"}:
            raise ValueError("unknown_resource_mode")
        if self.units <= 0:
            raise ValueError("resource_units_must_be_positive")


@dataclass(frozen=True)
class OperationalProfile:
    profile_id: str
    max_runtime_s: int
    allow_child_process: bool
    allow_durable_writer: bool
    require_benchmark: bool
    require_periodic_heartbeat: bool
    require_checkpoint: bool


PROFILES = {
    "trivial": OperationalProfile(
        "trivial-v1", 120, False, False, False, False, False
    ),
    "bounded": OperationalProfile(
        "bounded-v1", 3600, True, True, False, True, False
    ),
    "long_running": OperationalProfile(
        "long-running-v1", 172800, True, True, True, True, True
    ),
}

RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


def max_risk(risks):
    return max(risks, key=RISK_ORDER.__getitem__)


def validate_profile_request(
    profile,
    *,
    expected_runtime_s,
    child_process,
    durable_writer,
):
    if (
        expected_runtime_s > profile.max_runtime_s
        or child_process
        and not profile.allow_child_process
        or durable_writer
        and not profile.allow_durable_writer
    ):
        raise ValueError("profile_envelope_exceeded")
    return {"profile_id": profile.profile_id, "closure": "terminal_receipt"}


def profile_evidence_dispositions(profile):
    return {
        "benchmark": "required" if profile.require_benchmark else "not_applicable",
        "checkpoint": "required" if profile.require_checkpoint else "not_applicable",
        "heartbeat": (
            "required" if profile.require_periodic_heartbeat else "not_applicable"
        ),
    }


def operational_risk_floor(request):
    raises = []
    if request.restricted_data or request.external_write:
        raises.append("R3")
    if request.expected_runtime_s > 3600 or request.exclusive_resources:
        raises.append("R2")
    if request.checkpoint_uncertain or request.stop_confirmation_uncertain:
        raises.append("R3")
    return max_risk(["R0", *raises])


def has_resource_conflict(requested, held, capacities):
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
