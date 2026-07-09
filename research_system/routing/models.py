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
