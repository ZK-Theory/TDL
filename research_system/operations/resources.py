"""Non-widening resource and operational authority predicates."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.operations.profiles import (
    CURRENT_OPERATIONAL_PROFILE_POLICY,
    CURRENT_PROFILES,
    OperationalProfile,
)


RESOURCE_GRANT_SCHEMA_ID = "ars://operations/resource-grant"
RESOURCE_GRANT_SCHEMA_VERSION = "1.0.0"
RESOURCE_GRANT_V1_1_SCHEMA_ID = RESOURCE_GRANT_SCHEMA_ID
RESOURCE_GRANT_V1_1_SCHEMA_VERSION = "1.1.0"
RESOURCE_GRANT_V1_1_SCHEMA_SHA256 = "3cf8e8b48e90c63d06eb7f807d02ef15fdc0507416ac3a014dd326ae10e8da39"
RESOURCE_GRANT_AUTHORITY_PREIMAGE_SCHEMA_ID = "ars://operations/resource-grant-authority-preimage"
RESOURCE_GRANT_AUTHORITY_PREIMAGE_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HOST_ID_RE = re.compile(r"^host:sha256:[0-9a-f]{64}$")
_BOOT_ID_RE = re.compile(r"^boot:sha256:[0-9a-f]{64}$")
_AUTHORITY_PREIMAGE_REF_RE = re.compile(r"^ars://operations/resource-grant-authority-preimage/sha256/[0-9a-f]{64}$")
_IDENTIFIER_PATTERNS = {
    "project_id": re.compile(r"^prj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "resource_grant_id": re.compile(r"^rgr_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "resource_request_id": re.compile(r"^rsq_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "task_id": re.compile(r"^tsk_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "dispatch_id": re.compile(r"^dsp_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "attempt_id": re.compile(r"^att_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "event_id": re.compile(r"^evt_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "command_id": re.compile(r"^cmd_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "actor_id": re.compile(r"^act_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
    "authority_grant_id": re.compile(r"^agr_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
}
_REQUIRED_SOURCE_EVENT_FIELDS = frozenset(
    {
        "event_id",
        "event_type",
        "schema_id",
        "schema_version",
        "project_id",
        "stream_id",
        "stream_version",
        "global_position",
        "transaction_id",
        "transaction_index",
        "transaction_count",
        "command_id",
        "command_type",
        "idempotency_key",
        "command_payload_hash",
        "correlation_id",
        "causation_id",
        "actor_id",
        "authority_grant_id",
        "occurred_at",
        "recorded_at",
        "payload",
        "previous_event_hash",
        "event_hash",
    }
)
_COMMAND_PROVENANCE_FIELDS = frozenset(
    {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }
)
_FIXED_REVOCATION_CONDITIONS = (
    "trusted_host_identity_changed",
    "trusted_boot_identity_changed",
    "trusted_control_store_identity_changed",
    "trusted_store_manifest_changed",
    "operational_profile_policy_changed",
)


@dataclass(frozen=True)
class TrustedRuntimeAuthority:
    """Frozen runtime bindings injected by the trusted control-plane owner."""

    host_identity: str
    boot_identity: str
    control_store_identity: str
    store_manifest_sha256: str

    def __post_init__(self) -> None:
        """Reject malformed bindings before they become an authority preimage."""
        if (
            _HOST_ID_RE.fullmatch(self.host_identity) is None
            or _BOOT_ID_RE.fullmatch(self.boot_identity) is None
            or _SHA256_RE.fullmatch(self.control_store_identity) is None
            or _SHA256_RE.fullmatch(self.store_manifest_sha256) is None
        ):
            raise ValueError("trusted_runtime_authority_invalid")


def _require_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER_PATTERNS[field].fullmatch(value) is None:
        raise ValueError("resource_grant_source_event_invalid")
    return value


def _require_sha256(value: object, error: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(error)
    return value


def _parse_utc_timestamp(value: object, error: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(error)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(error) from exc
    if parsed.tzinfo != UTC:
        raise ValueError(error)
    return parsed


def _format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _authority_request_basis(resource_request: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in resource_request.items() if key != "projection_evidence_refs"}


def derive_resource_grant_authority_preimage(
    *,
    project_id: str,
    resource_grant_id: str,
    resource_request: Mapping[str, Any],
    trusted_authority: TrustedRuntimeAuthority,
) -> dict[str, Any]:
    """Return the non-self-referential typed authority preimage for a request."""
    if not isinstance(trusted_authority, TrustedRuntimeAuthority):
        raise TypeError("trusted_runtime_authority_required")
    if not isinstance(resource_request, Mapping):
        raise ValueError("resource_grant_authority_preimage_invalid")
    request = dict(resource_request)
    profile_name = request.get("operational_profile")
    policy = CURRENT_OPERATIONAL_PROFILE_POLICY
    if (
        not isinstance(profile_name, str)
        or profile_name not in CURRENT_PROFILES
        or request.get("operational_profile_policy_id") != policy.policy_id
        or request.get("operational_profile_revision") != policy.policy_revision
    ):
        raise ValueError("resource_grant_policy_mismatch")
    expected_position = request.get("expected_control_store_position")
    if type(expected_position) is not int or expected_position < 0:
        raise ValueError("resource_grant_authority_preimage_invalid")
    return {
        "schema_id": RESOURCE_GRANT_AUTHORITY_PREIMAGE_SCHEMA_ID,
        "schema_version": RESOURCE_GRANT_AUTHORITY_PREIMAGE_SCHEMA_VERSION,
        "project_id": _require_identifier(project_id, "project_id"),
        "resource_grant_id": _require_identifier(resource_grant_id, "resource_grant_id"),
        "resource_request_id": _require_identifier(request.get("resource_request_id"), "resource_request_id"),
        "authority_request_basis_sha256": sha256_hex(canonical_bytes(_authority_request_basis(request))),
        "requesting_actor_id": _require_identifier(request.get("requesting_actor_id"), "actor_id"),
        "requesting_authority_grant_id": _require_identifier(
            request.get("requesting_authority_grant_id"), "authority_grant_id"
        ),
        "expected_control_store_position": expected_position,
        "host_identity": trusted_authority.host_identity,
        "boot_identity": trusted_authority.boot_identity,
        "control_store_identity": trusted_authority.control_store_identity,
        "store_manifest_sha256": trusted_authority.store_manifest_sha256,
        "operational_profile": profile_name,
        "accepted_policy_id": policy.policy_id,
        "accepted_policy_revision": policy.policy_revision,
        "accepted_policy_raw_sha256": policy.raw_sha256,
    }


def derive_resource_grant_authority_preimage_ref(
    *,
    project_id: str,
    resource_grant_id: str,
    resource_request: Mapping[str, Any],
    trusted_authority: TrustedRuntimeAuthority,
) -> str:
    """Return the typed URI generated before appending a protected request."""
    preimage = derive_resource_grant_authority_preimage(
        project_id=project_id,
        resource_grant_id=resource_grant_id,
        resource_request=resource_request,
        trusted_authority=trusted_authority,
    )
    return _authority_preimage_ref(preimage)


def _authority_preimage_ref(preimage: Mapping[str, Any]) -> str:
    return f"ars://operations/resource-grant-authority-preimage/sha256/{sha256_hex(canonical_bytes(preimage))}"


def _require_exact_authority_preimage_ref(
    request: Mapping[str, Any],
    *,
    project_id: str,
    resource_grant_id: str,
    trusted_authority: TrustedRuntimeAuthority,
) -> tuple[str, dict[str, Any]]:
    preimage = derive_resource_grant_authority_preimage(
        project_id=project_id,
        resource_grant_id=resource_grant_id,
        resource_request=request,
        trusted_authority=trusted_authority,
    )
    expected_ref = _authority_preimage_ref(preimage)
    refs = request.get("projection_evidence_refs")
    if (
        not isinstance(refs, list)
        or refs != [expected_ref]
        or _AUTHORITY_PREIMAGE_REF_RE.fullmatch(expected_ref) is None
    ):
        raise ValueError("resource_grant_authority_preimage_invalid")
    return expected_ref, preimage


def _require_exact_committed_resource_grant_event(
    committed_event: Mapping[str, Any],
    *,
    project_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], datetime]:
    if not isinstance(committed_event, Mapping):
        raise ValueError("resource_grant_source_event_invalid")
    event = dict(committed_event)
    fields = frozenset(event)
    if fields not in {
        _REQUIRED_SOURCE_EVENT_FIELDS,
        _REQUIRED_SOURCE_EVENT_FIELDS | _COMMAND_PROVENANCE_FIELDS,
    }:
        raise ValueError("resource_grant_source_event_invalid")
    if (
        event.get("event_type") != "ResourceGrantRequested"
        or event.get("schema_id") != "ars://core/event/ResourceGrantRequested"
        or event.get("schema_version") != "1.0.0"
        or event.get("command_type") != "RequestResourceGrant"
        or event.get("project_id") != project_id
    ):
        raise ValueError("resource_grant_source_event_invalid")
    _require_identifier(event.get("project_id"), "project_id")
    _require_identifier(event.get("event_id"), "event_id")
    _require_identifier(event.get("command_id"), "command_id")
    _require_sha256(event.get("event_hash"), "resource_grant_source_event_invalid")
    _require_sha256(event.get("command_payload_hash"), "resource_grant_source_event_invalid")
    if fields == _REQUIRED_SOURCE_EVENT_FIELDS | _COMMAND_PROVENANCE_FIELDS:
        _require_sha256(event.get("command_schema_sha256"), "resource_grant_source_event_invalid")
        if (
            not isinstance(event.get("command_schema_id"), str)
            or not event["command_schema_id"]
            or event.get("command_schema_version") != "1.0.0"
        ):
            raise ValueError("resource_grant_source_event_invalid")
    _parse_utc_timestamp(event.get("recorded_at"), "resource_grant_source_event_invalid")
    issued_at = _parse_utc_timestamp(event.get("occurred_at"), "resource_grant_source_event_invalid")
    payload = event.get("payload")
    if not isinstance(payload, dict) or set(payload) != {
        "resource_id",
        "resource_request",
    }:
        raise ValueError("resource_grant_source_event_invalid")
    resource_id = _require_identifier(payload.get("resource_id"), "resource_grant_id")
    if event.get("stream_id") != resource_id:
        raise ValueError("resource_grant_source_event_invalid")
    request = payload.get("resource_request")
    if not isinstance(request, dict):
        raise ValueError("resource_grant_source_event_invalid")
    for field in ("resource_request_id", "task_id", "dispatch_id", "attempt_id"):
        _require_identifier(request.get(field), field)
    if event["command_payload_hash"] != sha256_hex(canonical_bytes(payload)):
        raise ValueError("resource_grant_source_event_invalid")
    expected_event_hash = sha256_hex(
        canonical_bytes({key: value for key, value in event.items() if key != "event_hash"})
    )
    if event["event_hash"] != expected_event_hash:
        raise ValueError("resource_grant_source_event_invalid")
    return event, payload, request, issued_at


def _profile_constraints(profile: OperationalProfile) -> dict[str, object]:
    return {
        "profile_id": profile.profile_id,
        "max_runtime_s": profile.max_runtime_s,
        "allow_child_process": profile.allow_child_process,
        "allow_durable_writer": profile.allow_durable_writer,
        "require_benchmark": profile.require_benchmark,
        "require_periodic_heartbeat": profile.require_periodic_heartbeat,
        "require_checkpoint": profile.require_checkpoint,
        "renewal_allowed": profile.renewal_allowed,
    }


def _heartbeat_policy(profile: OperationalProfile) -> dict[str, object]:
    return {
        "disposition": profile.heartbeat_disposition,
        "cadence_seconds": profile.heartbeat_cadence_seconds,
        "additional_grace_seconds": profile.heartbeat_additional_grace_seconds,
        "stale_threshold_seconds": profile.heartbeat_stale_threshold_seconds,
    }


def _renewal_policy_ref(profile_name: str) -> str:
    policy = CURRENT_OPERATIONAL_PROFILE_POLICY
    return (
        "ars://operations/operational-profile-policy/"
        f"{policy.policy_id}/{policy.policy_revision}/{profile_name}/renewal"
    )


def derive_resource_grant_v1_1_record(
    *,
    committed_event: Mapping[str, Any],
    project_id: str,
    trusted_authority: TrustedRuntimeAuthority,
) -> dict[str, Any]:
    """Derive a v1.1 grant only from an exact committed request and trusted runtime."""
    project_id = _require_identifier(project_id, "project_id")
    event, payload, request, issued_at = _require_exact_committed_resource_grant_event(
        committed_event,
        project_id=project_id,
    )
    authority_ref, authority_preimage = _require_exact_authority_preimage_ref(
        request,
        project_id=project_id,
        resource_grant_id=payload["resource_id"],
        trusted_authority=trusted_authority,
    )
    profile_name = request.get("operational_profile")
    profile = CURRENT_PROFILES.get(profile_name) if isinstance(profile_name, str) else None
    policy = CURRENT_OPERATIONAL_PROFILE_POLICY
    if (
        profile is None
        or request.get("operational_profile_policy_id") != policy.policy_id
        or request.get("operational_profile_revision") != policy.policy_revision
    ):
        raise ValueError("resource_grant_policy_mismatch")
    host_pool = request.get("requested_host_pool")
    if not isinstance(host_pool, list) or len(host_pool) != 1 or host_pool[0] != trusted_authority.host_identity:
        raise ValueError("resource_grant_host_pool_invalid")
    deadline = _parse_utc_timestamp(request.get("deadline"), "resource_grant_time_bounds_invalid")
    if deadline <= issued_at:
        raise ValueError("resource_grant_time_bounds_invalid")
    maximum_expiry = issued_at + timedelta(seconds=profile.max_runtime_s)
    expires_at = min(deadline, maximum_expiry)
    if expires_at <= issued_at:
        raise ValueError("resource_grant_time_bounds_invalid")
    canonical_request = canonical_bytes(request)
    granted_claims = json.loads(canonical_request.decode("utf-8"))
    record: dict[str, Any] = {
        "schema_id": RESOURCE_GRANT_V1_1_SCHEMA_ID,
        "schema_version": RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
        "record_revision": 1,
        "project_id": project_id,
        "resource_grant_id": payload["resource_id"],
        "resource_request_id": request["resource_request_id"],
        "task_id": request["task_id"],
        "dispatch_id": request["dispatch_id"],
        "attempt_id": request["attempt_id"],
        "source_event_id": event["event_id"],
        "source_event_hash": event["event_hash"],
        "source_command_id": event["command_id"],
        "source_command_payload_hash": event["command_payload_hash"],
        "resource_request_sha256": sha256_hex(canonical_request),
        "authority_request_basis_sha256": authority_preimage["authority_request_basis_sha256"],
        "authority_preimage_ref": authority_ref,
        "authority_preimage_sha256": authority_ref.rsplit("/", 1)[-1],
        "requesting_actor_id": authority_preimage["requesting_actor_id"],
        "requesting_authority_grant_id": authority_preimage["requesting_authority_grant_id"],
        "expected_control_store_position": authority_preimage["expected_control_store_position"],
        "host_identity": trusted_authority.host_identity,
        "boot_identity": trusted_authority.boot_identity,
        "control_store_identity": trusted_authority.control_store_identity,
        "store_manifest_sha256": trusted_authority.store_manifest_sha256,
        "operational_profile": profile_name,
        "accepted_policy_id": policy.policy_id,
        "accepted_policy_revision": policy.policy_revision,
        "accepted_policy_raw_sha256": policy.raw_sha256,
        "renewal_policy_ref": _renewal_policy_ref(profile_name),
        "profile_constraints": _profile_constraints(profile),
        "heartbeat_policy": _heartbeat_policy(profile),
        "granted_claims": granted_claims,
        "granted_claims_sha256": sha256_hex(canonical_bytes(granted_claims)),
        "issued_at": _format_utc_timestamp(issued_at),
        "maximum_lease_duration_s": profile.max_runtime_s,
        "expires_at": _format_utc_timestamp(expires_at),
        "revocation_conditions": list(_FIXED_REVOCATION_CONDITIONS),
    }
    record["content_hash"] = sha256_hex(canonical_bytes(record))
    return record


def derive_resource_grant_record(payload: dict) -> dict:
    """Return the immutable C1 grant record determined by an accepted request."""
    resource_id = payload.get("resource_id")
    request = payload.get("resource_request")
    if not isinstance(resource_id, str) or not isinstance(request, dict):
        raise ValueError("invalid_resource_grant_request")
    granted_claims = json.loads(canonical_bytes(request).decode("utf-8"))
    return {
        "schema_id": RESOURCE_GRANT_SCHEMA_ID,
        "schema_version": RESOURCE_GRANT_SCHEMA_VERSION,
        "resource_grant_id": resource_id,
        "resource_request_id": granted_claims["resource_request_id"],
        "attempt_id": granted_claims["attempt_id"],
        "profile_id": granted_claims["operational_profile_policy_id"],
        "granted_claims": granted_claims,
        "expires_at": granted_claims["deadline"],
    }


def authorize_operational_surface(*, requested: dict, granted: dict) -> dict:
    for dimension, requested_values in requested.items():
        granted_values = granted.get(dimension, set())
        if not set(requested_values) <= set(granted_values):
            raise ValueError("unauthorized_operational_expansion")
    return requested
