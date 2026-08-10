"""Pure two-stage dispatch planning without issue authority."""

from dataclasses import dataclass

from research_system.errors import ArsError
from research_system.routing.engine import _DispatchPlan, _select_route
from research_system.routing.models import RouteRequest


def assert_requirement_current(task, requirement) -> None:
    """Fail when the immutable W5 requirement no longer matches the task."""
    checker = getattr(task, "requirement_is_current", None)
    if checker is not None:
        current = checker(requirement)
    else:
        current = requirement.task_id == task.task_id and requirement.task_revision == task.revision
    if not current:
        raise ArsError("assurance_requirement_stale")


@dataclass(frozen=True)
class _BoundPreRouteEvidence:
    provider: object
    operational: object
    routing_evidence_snapshot_id: str

    def hard_gate_failures(self, request, candidate) -> tuple[str, ...]:
        provider_failures = self.provider.hard_gate_failures(request, candidate)
        operational_failures = self.operational.hard_gate_failures(request, candidate)
        return tuple(provider_failures) + tuple(operational_failures)


def bind_pre_route_evidence(provider_evidence, operational_evidence):
    """Bind matching immutable W7/W8 evidence into the W4 gate port."""
    provider_snapshot = provider_evidence.routing_evidence_snapshot_id
    operational_snapshot = operational_evidence.routing_evidence_snapshot_id
    if provider_snapshot != operational_snapshot:
        raise ArsError("routing evidence snapshot mismatch")
    provider_evidence.validate_pre_route()
    operational_evidence.validate_pre_route()
    return _BoundPreRouteEvidence(
        provider_evidence,
        operational_evidence,
        provider_snapshot,
    )


def build_route_request(task, requirement, compiled) -> RouteRequest:
    """Build the immutable W4 request from current W2/W5/W3 identities."""
    return RouteRequest(
        request_id=task.route_request_id,
        task_id=task.task_id,
        task_revision=task.revision,
        assurance_requirement_id=requirement.assurance_requirement_id,
        assurance_requirement_hash=requirement.content_hash,
        context_candidate_id=compiled.context_candidate_id,
        context_hash=compiled.content_hash,
    )


def _plan_dispatch(
    task,
    attempt_id,
    requirement,
    compiled,
    candidates,
    provider_evidence,
    operational_evidence,
):
    """Return a route failure or an unissued cross-package dispatch record."""
    assert_requirement_current(task, requirement)
    if compiled.state != "compiled":
        raise ArsError("context candidate must be compiled and unissued")
    reference_gate = getattr(compiled, "assert_reference_gate", None)
    if reference_gate is not None:
        reference_gate()
    preliminary = bind_pre_route_evidence(provider_evidence, operational_evidence)
    route = _select_route(build_route_request(task, requirement, compiled), candidates, preliminary)
    if route["kind"] == "failure":
        return route
    return _DispatchPlan(
        attempt_id=attempt_id,
        assurance_requirement_id=requirement.assurance_requirement_id,
        assurance_requirement_hash=requirement.content_hash,
        context=compiled,
        route=route,
        provider_evidence_id=provider_evidence.evidence_id,
        provider_evidence_hash=provider_evidence.content_hash,
        operational_evidence_id=operational_evidence.evidence_id,
        operational_evidence_hash=operational_evidence.content_hash,
        expires_at=min(
            provider_evidence.expires_at,
            operational_evidence.expires_at,
        ),
        state="unissued",
    )
