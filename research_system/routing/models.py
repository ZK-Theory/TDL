"""Immutable routing request models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRequest:
    request_id: str
    task_id: str
    task_revision: int
    assurance_requirement_id: str
    assurance_requirement_hash: str
    context_candidate_id: str
    context_hash: str
    capability: str = "unspecified"
    risk_tier: str = "R0"
    independence_grade: str = "I0"
    authority_grant_id: str = ""
    root_bindings_hash: str = ""
    tool_permissions_hash: str = ""
    sensitivity_class: str = "internal"
    policy_revision: str = "unspecified"
    evaluation_revision: str = "unspecified"
