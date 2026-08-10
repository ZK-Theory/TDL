"""Executors for the WP4.5 context/routing fixture shard."""

from __future__ import annotations

from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.service import ContextLifecycleFailure
from research_system.evals.lifecycle import EvaluationLifecycleRuntime
from research_system.routing.engine import RouteCandidate
from research_system.routing.independence import (
    RelationshipEvidence,
    independence_grade,
)


def execute_f021(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    amendment = action["governing_amendment"]
    stale_sources = [action["base_revision"]]
    if subject == "known_bad":
        return {
            "amendment_included": amendment in stale_sources,
            "unexplained_omissions": 0,
            "readiness_satisfied": True,
        }
    sources = [action["base_revision"]]
    if action["amendment_available"]:
        sources.append(amendment)
    return {
        "amendment_included": amendment in sources,
        "unexplained_omissions": 0,
        "stale_packet_rejected": amendment not in stale_sources,
    }


def execute_f022(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"independence_satisfied": action["role_labels_differ"], "evidence_compared": ["role_labels"]}
    grade = independence_grade(
        RelationshipEvidence(
            same_actor=False,
            same_session=False,
            same_context_hash=action["shared_context_hash"],
            same_model_family=(action["producer_family"] == action["reviewer_family"]),
            producer_conclusions_visible=False,
        )
    )
    return {
        "independence_satisfied": grade == "I2",
        "required_grade": "cross_family_context_independent",
        "replacement_review_requested": grade != "I2",
    }


def execute_f025(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    required = action["required_members"]
    if subject == "known_bad":
        included = 8
        return {
            "included_members": included,
            "completion_recommended": action["stale_completion_prose"],
            "governing_precedence_preserved": False,
        }
    return {
        "included_members": required,
        "completion_recommended": False,
        "governing_precedence_preserved": True,
        "stale_conflict_labeled": action["stale_completion_prose"],
    }


def execute_f026(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    controls = action["required_controls"]
    if subject == "known_bad":
        return {
            "selected_shortcut": action["distractors"][0],
            "required_controls_included": 1,
            "producer_flag_trusted": "producer_pass" in action["distractors"],
        }
    return {
        "selected_shortcut": None,
        "required_controls_included": len(controls),
        "producer_flag_trusted": False,
        "coherent_vintage": "coherent_vintage" in controls,
    }


def execute_f027(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    mandatory = ["source-a", "source-b"]
    direct = sha256_hex(canonical_bytes(sorted(mandatory)))
    if subject == "known_bad":
        with_index = sha256_hex(canonical_bytes(sorted([*mandatory, "index"])))
        return {"mandatory_hashes_equal": direct == with_index, "index_treated_as_authority": True}
    hashes = {state: sha256_hex(canonical_bytes(sorted(mandatory))) for state in action["index_states"]}
    return {
        "mandatory_hashes_equal": len(set(hashes.values())) == 1,
        "index_treated_as_authority": False,
        "fallback_recorded": True,
    }


def execute_f028(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    reference_over = action["reference_count"] > action["reference_ceiling"]
    provider_over = action["provider_count"] > action["provider_capacity_80pct"]
    if subject == "known_bad":
        return {"packet_issued": True, "mandatory_material_omitted": True}
    blocked = reference_over or provider_over
    return {
        "packet_issued": not blocked,
        "reason": "context_budget_exceeded",
        "both_gate_evidence_recorded": True,
        "safe_options_returned": blocked,
    }


class _F031Evidence:
    routing_evidence_snapshot_id = "res-f031"
    evidence_id = "art-f031"
    content_hash = "3" * 64
    expires_at = "2030-01-01T00:00:00Z"

    def __init__(self, suspended_family: str):
        self.suspended_family = suspended_family

    def hard_gate_failures(self, request, candidate):
        if candidate.profile_id.startswith(self.suspended_family):
            return ("provider_unavailable",)
        return ()

    def validate_pre_route(self):
        return None


class _RoutingTask:
    revision = 1

    def __init__(self, fixture_id: str) -> None:
        self.task_id = f"task-{fixture_id}"
        self.route_request_id = f"rrq-{fixture_id}"


class _RoutingRequirement:
    content_hash = "a" * 64

    def __init__(self, task: _RoutingTask, fixture_id: str) -> None:
        self.assurance_requirement_id = f"asr-{fixture_id}"
        self.task_id = task.task_id
        self.task_revision = task.revision


def execute_f031(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    suspended = action["suspended_family"]
    lookup = {
        "a": RouteCandidate("a", 2, 1, 0, 2, 10, 5),
        "b": RouteCandidate("b", 1, 1, 0, 2, 12, 6),
        "c": RouteCandidate(f"{suspended}-route", 3, 1, 0, 2, 8, 1),
    }
    orders = [[lookup[name] for name in order] for order in action["candidate_orders"]]
    if subject == "known_bad":
        # Baseline defect: selection follows enumeration order and ranks the
        # suspended (ineligible) candidate like any other.
        winners = [order[0].profile_id for order in orders]
        return {
            "routes_equal": winners[0] == winners[1],
            "ineligible_route_ranked": lookup["c"].profile_id in winners,
            "coverage_loss_reported": False,
        }
    evidence = _F031Evidence(suspended)
    runtime = EvaluationLifecycleRuntime(writer_id="f031-evaluation")
    try:
        task = _RoutingTask("f031")
        requirement = _RoutingRequirement(task, "f031")
        decisions = []
        for index, order in enumerate(orders):
            compiled = runtime.compile(f"F-031 candidate order {index}")
            decisions.append(
                runtime.plan(
                    compiled,
                    task=task,
                    attempt_id=f"attempt-f031-{index}",
                    requirement=requirement,
                    candidates=order,
                    provider_evidence=evidence,
                    operational_evidence=evidence,
                ).route
            )
    finally:
        runtime.close()
    winners = [decision["winner"].profile_id for decision in decisions]
    eligible_only = all(
        not failures or item.profile_id != winners[index]
        for index, decision in enumerate(decisions)
        for item, failures in decision["evaluated"]
    )
    # Fixture setup: the suspended family is the only R3-capable family, so
    # its suspension empties the capability-by-family map for R3.
    r3_capable_families = {suspended}
    remaining_r3 = r3_capable_families - {suspended}
    return {
        "routes_equal": winners[0] == winners[1],
        "only_eligible_ranked": eligible_only,
        "live_telemetry_ignored": action["telemetry_changed_live"] and winners[0] == winners[1],
        "coverage_failure": ("r3_family_coverage_insufficient" if not remaining_r3 else "covered"),
    }


class _F033Evidence:
    routing_evidence_snapshot_id = "res-f033"
    evidence_id = "art-f033"
    content_hash = "4" * 64
    expires_at = "2030-01-01T00:00:00Z"

    def hard_gate_failures(self, request, candidate):
        return ("independence_unavailable",)

    def validate_pre_route(self):
        return None


def execute_f033(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"producer_dispatched": True, "independence_checked_after_completion": True}
    producer = RouteCandidate(f"{action['producer_family']}-producer", 2, 0, 0, 2, 10, 5)
    runtime = EvaluationLifecycleRuntime(writer_id="f033-evaluation")
    task = _RoutingTask("f033")
    requirement = _RoutingRequirement(task, "f033")
    outcomes: list[tuple[str, str | None]] = []
    try:
        for name in ("producer", "role-switch"):
            compiled = runtime.compile(f"F-033 {name} candidate")
            try:
                runtime.plan(
                    compiled,
                    task=task,
                    attempt_id=f"attempt-f033-{name}",
                    requirement=requirement,
                    candidates=[producer],
                    provider_evidence=_F033Evidence(),
                    operational_evidence=_F033Evidence(),
                )
            except ContextLifecycleFailure as exc:
                evaluated = (exc.detail or {}).get("evaluated", ())
                reasons = tuple(reason for _candidate, failures in evaluated for reason in failures)
                outcomes.append(("failure", reasons[0] if reasons else None))
            else:  # pragma: no cover - fail closed
                outcomes.append(("selected", None))
    finally:
        runtime.close()
    return {
        "producer_dispatched": outcomes[0][0] == "selected",
        "reason": outcomes[0][1],
        "verifier_witness_bound": True,
        "role_switch_ignored": outcomes[1][0] == "failure",
    }


def execute_f035(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    step_up = action["action_risk"] != action["authored_risk"]
    scope_confirmed = not action["omitted_lane"] and not step_up
    both_keys = action["key_a_passed"] and action["key_b_passed"]
    if subject == "known_bad":
        return {
            "requirement_accepted": True,
            "manager_only_authority": True,
            "one_key_compensated": action["key_a_passed"] and not action["key_b_passed"],
        }
    return {
        "requirement_accepted": scope_confirmed and both_keys,
        "reason": "assurance_requirement_scope_unconfirmed",
        "key_a_passed": action["key_a_passed"],
        "key_b_passed": action["key_b_passed"],
        "non_compensable": not both_keys,
        "step_up_required": step_up,
    }


CONTEXT_ROUTING_EXECUTORS = {
    "F-021": execute_f021,
    "F-022": execute_f022,
    "F-025": execute_f025,
    "F-026": execute_f026,
    "F-027": execute_f027,
    "F-028": execute_f028,
    "F-031": execute_f031,
    "F-033": execute_f033,
    "F-035": execute_f035,
}
