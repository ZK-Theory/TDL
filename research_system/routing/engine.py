"""Eligibility-first deterministic route selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from research_system.routing.models import RouteRequest


class RoutingEvidenceSnapshot(Protocol):
    routing_evidence_snapshot_id: str

    def hard_gate_failures(self, request: RouteRequest, candidate: RouteCandidate) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class RouteCandidate:
    profile_id: str
    capability_margin: int
    independence_margin: int
    limitation_count: int
    snapshot_reliability: int
    snapshot_latency_ms: int
    snapshot_cost_units: int


@dataclass(frozen=True)
class _DispatchPlan:
    attempt_id: str
    assurance_requirement_id: str
    assurance_requirement_hash: str
    context: object
    route: object
    provider_evidence_id: str
    provider_evidence_hash: str
    operational_evidence_id: str
    operational_evidence_hash: str
    expires_at: str
    state: str = "unissued"


REJECTION_ORDER = (
    "provider_unavailable",
    "capability_insufficient",
    "risk_exceeded",
    "authority_missing",
    "permission_missing",
    "context_budget_exceeded",
    "assurance_unsatisfied",
    "independence_unavailable",
    "fixture_coverage_missing",
    "resource_unavailable",
)


def _select_route(
    request: RouteRequest,
    candidates: Sequence[RouteCandidate],
    evidence: RoutingEvidenceSnapshot,
) -> dict[str, Any]:
    """Evaluate stable hard gates before ranking eligible candidates."""
    evaluated = []
    for candidate in sorted(candidates, key=lambda item: item.profile_id):
        failures = tuple(evidence.hard_gate_failures(request, candidate))
        unknown = set(failures) - set(REJECTION_ORDER)
        if unknown:
            raise ValueError(f"unknown route rejection reason: {sorted(unknown)}")
        evaluated.append((candidate, tuple(sorted(failures, key=REJECTION_ORDER.index))))
    eligible = [item for item, failures in evaluated if not failures]
    if not eligible:
        return {
            "kind": "failure",
            "request_id": request.request_id,
            "routing_evidence_snapshot_id": evidence.routing_evidence_snapshot_id,
            "evaluated": tuple(evaluated),
        }
    winner = min(
        eligible,
        key=lambda item: (
            -item.capability_margin,
            -item.independence_margin,
            item.limitation_count,
            -item.snapshot_reliability,
            item.snapshot_latency_ms,
            item.snapshot_cost_units,
            item.profile_id,
        ),
    )
    return {
        "kind": "selected",
        "request_id": request.request_id,
        "routing_evidence_snapshot_id": evidence.routing_evidence_snapshot_id,
        "winner": winner,
        "evaluated": tuple(evaluated),
    }
