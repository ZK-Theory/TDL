"""Non-widening resource and operational authority predicates."""


def authorize_operational_surface(*, requested: dict, granted: dict) -> dict:
    for dimension, requested_values in requested.items():
        granted_values = granted.get(dimension, set())
        if not set(requested_values) <= set(granted_values):
            raise ValueError("unauthorized_operational_expansion")
    return requested
