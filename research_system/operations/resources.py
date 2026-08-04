"""Non-widening resource and operational authority predicates."""

import json

from research_system.canonical import canonical_bytes


RESOURCE_GRANT_SCHEMA_ID = "ars://operations/resource-grant"
RESOURCE_GRANT_SCHEMA_VERSION = "1.0.0"


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
