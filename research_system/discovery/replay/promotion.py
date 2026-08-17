"""Discovery promotion replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.replay.transactions import decision_event_precedes
from research_system.discovery.rules import _promotion_relation_matches
from research_system.discovery.rules import _valid_promotion_options
from research_system.discovery.rules import _valid_spike_promotion_option
from research_system.errors import IntegrityError


def reduce_candidate_promotion_requested(scope: EventScope) -> None:
    """Reduce CandidatePromotionRequested."""

    required_string = scope.required_string
    state = scope.state
    payload = scope.payload
    event = scope.event

    candidate_id = required_string("candidate_id")
    decision_id = required_string("decision_id")
    candidate = state["candidates"].get(candidate_id)
    decision = state["decisions"].get(decision_id)
    gate = required_string("promotion_gate")
    expected_status = {
        "assay_to_spike": "assay_scored",
        "spike_to_preregistration": "spike_verdict_recorded",
    }.get(gate)
    aggregate_id = (
        candidate.get("assay_id" if gate == "assay_to_spike" else "spike_id") if isinstance(candidate, dict) else None
    )
    aggregate = state["assays"].get(aggregate_id) if gate == "assay_to_spike" else state["spikes"].get(aggregate_id)
    review = state["reviews"].get(payload.get("review_id"))
    if (
        not isinstance(candidate, dict)
        or event.get("stream_id") != candidate_id
        or candidate.get("status") != expected_status
        or not isinstance(decision, dict)
        or decision.get("status") != "proposed"
        or not _valid_promotion_options(decision.get("options"))
        or not isinstance(aggregate, dict)
        or not isinstance(review, dict)
        or not decision_event_precedes(scope, "DecisionProposed", decision_id)
        or not _promotion_relation_matches(
            payload.get("promotion_relation"),
            decision_id=payload.get("decision_id"),
            candidate=candidate,
            aggregate_id=aggregate_id,
            aggregate=aggregate,
            review=review,
            gate=gate,
            recommendation=decision.get("recommendation"),
            actor_id=event.get("actor_id"),
        )
        or (
            decision.get("recommendation") == "PROMOTE"
            and gate == "assay_to_spike"
            and aggregate.get("mechanical_recommendation") != "PROMOTE"
        )
        or (
            gate == "spike_to_preregistration"
            and not _valid_spike_promotion_option(aggregate, decision.get("recommendation"))
        )
    ):
        raise IntegrityError("invalid Candidate promotion request")
    decision.update(kind="discovery_promotion", promotion_relation=deepcopy(payload["promotion_relation"]))
    candidate.update(
        status="promotion_pending",
        decision_id=decision_id,
        promotion_gate=gate,
        version=event["stream_version"],
    )


def reduce_candidate_promotion_applied(scope: EventScope) -> None:
    """Reduce CandidatePromotionApplied."""

    required_string = scope.required_string
    event = scope.event
    state = scope.state
    payload = scope.payload

    candidate_id = required_string("candidate_id")
    decision_id = required_string("decision_id")
    candidate = state["candidates"].get(candidate_id)
    decision = state["decisions"].get(decision_id)
    gate = required_string("promotion_gate")
    selected_option = required_string("selected_option")
    next_state = required_string("next_candidate_state")
    expected_next_state = {
        "PROMOTE": {
            "assay_to_spike": "spike_planning_authorized",
            "spike_to_preregistration": "preregistration_authorized",
        }.get(gate),
        "PARK": "parked",
        "KILL": "killed",
    }.get(selected_option)
    if (
        not isinstance(candidate, dict)
        or event.get("stream_id") != candidate_id
        or candidate.get("status") != "promotion_pending"
        or candidate.get("decision_id") != payload.get("decision_id")
        or candidate.get("promotion_gate") != gate
        or next_state != expected_next_state
        or not isinstance(decision, dict)
        or decision.get("status") != "resolved"
        or decision.get("kind") != "discovery_promotion"
        or decision.get("selected_option") != selected_option
        or not decision_event_precedes(scope, "DecisionResolved", decision_id)
        or (
            selected_option == "PROMOTE"
            and gate == "assay_to_spike"
            and state["assays"].get(candidate.get("assay_id"), {}).get("mechanical_recommendation") != "PROMOTE"
        )
        or (
            gate == "spike_to_preregistration"
            and not _valid_spike_promotion_option(
                state["spikes"].get(candidate.get("spike_id"), {}),
                selected_option,
            )
        )
    ):
        raise IntegrityError("invalid Candidate promotion application")
    candidate.update(status=next_state, version=event["stream_version"])
    decision.update(terminal_event_id=event.get("event_id"), terminal_event_hash=event.get("event_hash"))
    if selected_option == "PARK":
        candidate["parked_at_global_position"] = event["global_position"]
