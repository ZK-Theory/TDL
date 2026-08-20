"""Discovery spike replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.command.reducers import replay_control_plane
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.replay.transactions import is_exact_legacy_unclosed_spike_verdict
from research_system.discovery.rules import _aggregate_content_hash
from research_system.discovery.rules import _review_subject_matches
from research_system.discovery.rules import _spike_cancellation_matches
from research_system.discovery.rules import _spike_execution_ids_available
from research_system.discovery.rules import _spike_execution_relation_matches
from research_system.discovery.rules import _spike_plan_matches
from research_system.discovery.rules import _spike_start_operational_matches
from research_system.discovery.rules import _spike_verdict_matches
from research_system.discovery.rules import _valid_review_supersession
from research_system.discovery.rules import _valid_spike_execution_proposal
from research_system.errors import IntegrityError
from typing import Mapping


def reduce_spike_planned(scope: EventScope) -> None:
    """Reduce SpikePlanned."""

    required_string = scope.required_string
    aggregate_identity_exists = scope.aggregate_identity_exists
    payload = scope.payload
    state = scope.state
    event = scope.event

    spike_id = required_string("spike_id")
    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
    artifact = payload.get("plan_artifact")
    if aggregate_identity_exists(spike_id):
        raise IntegrityError("Spike identity collision")
    if (
        not isinstance(candidate, Mapping)
        or not isinstance(artifact, Mapping)
        or not _spike_plan_matches(
            artifact,
            payload,
            candidate,
            assay,
            state["decisions"].get(candidate.get("decision_id")),
        )
    ):
        raise IntegrityError("invalid Spike plan")
    state["spikes"][spike_id] = {**deepcopy(payload), "status": "planned", "version": event["stream_version"]}


def reduce_spike_approval_requested(scope: EventScope) -> None:
    """Reduce SpikeApprovalRequested."""

    state = scope.state
    payload = scope.payload
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(spike, dict)
        or event.get("stream_id") != payload.get("spike_id")
        or spike.get("status") != "planned"
    ):
        raise IntegrityError("invalid Spike approval request")
    spike.update(status="approval_pending", version=event["stream_version"])


def reduce_candidate_spike_plan_linked(scope: EventScope) -> None:
    """Reduce CandidateSpikePlanLinked."""

    candidate_spike_plan_link_matches = scope.candidate_spike_plan_link_matches
    event = scope.event
    payload = scope.payload
    state = scope.state
    required_string = scope.required_string

    if not candidate_spike_plan_link_matches(event, payload):
        raise IntegrityError("invalid Candidate Spike plan link")
    candidate = state["candidates"][payload["candidate_id"]]
    candidate.update(
        status="spike_approval_pending",
        spike_id=required_string("spike_id"),
        version=event["stream_version"],
    )


def reduce_spike_execution_decision_requested(scope: EventScope) -> None:
    """Reduce SpikeExecutionDecisionRequested."""

    payload = scope.payload
    operational_events = scope.operational_events
    state = scope.state
    required_string = scope.required_string
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    decision = state["decisions"].get(payload.get("decision_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
    relation = payload.get("execution_authority_relation")
    resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
    try:
        operational = replay_control_plane(operational_events)
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError("invalid Spike execution decision request") from exc
    resource = operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
    if (
        not isinstance(spike, dict)
        or not isinstance(decision, dict)
        or not isinstance(candidate, dict)
        or not isinstance(assay, dict)
        or decision.get("status") != "proposed"
        or event.get("stream_id") != payload.get("spike_id")
        or not preceding_transaction_event_matches(
            event,
            payload.get("w2_payload"),
            event_type="DecisionProposed",
            stream_id=payload.get("decision_id"),
        )
        or not _valid_spike_execution_proposal(payload.get("w2_payload"))
        or payload["w2_payload"].get("new_decision_id") != payload.get("decision_id")
        or not isinstance(resource, Mapping)
        or not _spike_execution_relation_matches(
            relation,
            candidate=candidate,
            assay=assay,
            spike=spike,
            decision_id=payload.get("decision_id"),
            resource=resource,
        )
    ):
        raise IntegrityError("invalid Spike execution decision request")
    spike.update(
        decision_id=required_string("decision_id"),
        execution_authority_relation=deepcopy(payload["execution_authority_relation"]),
        version=event["stream_version"],
    )


def reduce_spike_authorized(scope: EventScope) -> None:
    """Reduce SpikeAuthorized."""

    payload = scope.payload
    operational_events = scope.operational_events
    state = scope.state
    following_transaction_event_matches = scope.following_transaction_event_matches
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    decision = state["decisions"].get(payload.get("decision_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
    relation = payload.get("execution_authority_relation")
    resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
    try:
        operational = replay_control_plane(operational_events)
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError("invalid Spike authorization") from exc
    resource = operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
    if (
        not isinstance(spike, dict)
        or spike.get("decision_id") != payload.get("decision_id")
        or not isinstance(decision, dict)
        or not isinstance(candidate, Mapping)
        or not isinstance(assay, Mapping)
        or decision.get("status") != "resolved"
        or decision.get("selected_option") != "approve"
        or not preceding_transaction_event_matches(
            event,
            payload.get("w2_payload"),
            event_type="DecisionResolved",
            stream_id=payload.get("decision_id"),
        )
        or relation != spike.get("execution_authority_relation")
        or spike.get("execution_authority_relation", {}).get("actor_id") != event.get("actor_id")
        or not isinstance(resource, Mapping)
        or resource.get("status") != "active"
        or not _spike_execution_relation_matches(
            relation,
            candidate=candidate,
            assay=assay,
            spike=spike,
            decision_id=payload.get("decision_id"),
            resource=resource,
        )
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateSpikeAuthorized",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Spike authorization")
    spike.update(status="authorized", version=event["stream_version"])


def reduce_candidate_spike_authorized(scope: EventScope) -> None:
    """Reduce CandidateSpikeAuthorized."""

    state = scope.state
    payload = scope.payload
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches
    event = scope.event

    candidate = state["candidates"].get(payload.get("candidate_id"))
    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != "spike_approval_pending"
        or candidate.get("spike_id") != payload.get("spike_id")
        or event.get("stream_id") != payload.get("candidate_id")
        or not isinstance(spike, Mapping)
        or spike.get("candidate_id") != payload.get("candidate_id")
        or spike.get("status") != "authorized"
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="SpikeAuthorized",
            stream_id=payload.get("spike_id"),
        )
    ):
        raise IntegrityError("invalid Candidate Spike authorization")
    candidate.update(status="spike_authorized", version=event["stream_version"])


def reduce_spike_started(scope: EventScope) -> None:
    """Reduce SpikeStarted."""

    required_string = scope.required_string
    state = scope.state
    payload = scope.payload
    operational_events = scope.operational_events
    event = scope.event
    following_transaction_event_matches = scope.following_transaction_event_matches

    spike = state["spikes"].get(payload.get("spike_id"))
    attempt_id = required_string("attempt_id")
    lease_id = required_string("lease_id")
    if (
        not isinstance(spike, dict)
        or spike.get("status") != "authorized"
        or not _spike_execution_ids_available(
            state["spikes"],
            payload.get("spike_id"),
            attempt_id,
            lease_id,
        )
        or payload.get("execution_authority_relation") != spike.get("execution_authority_relation")
        or spike.get("execution_authority_relation", {}).get("resource_ref", {}).get("id")
        != payload.get("resource_grant_id")
        or not _spike_start_operational_matches(operational_events, event, payload)
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateSpikeStarted",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Spike start")
    spike.update(
        status="running",
        attempt_id=attempt_id,
        attempt_sha256=required_string("attempt_sha256"),
        lease_id=lease_id,
        lease_sha256=required_string("lease_sha256"),
        lease_status="active",
        version=event["stream_version"],
    )


def reduce_candidate_spike_started(scope: EventScope) -> None:
    """Reduce CandidateSpikeStarted."""

    payload = scope.payload
    state = scope.state
    event = scope.event

    candidate_id = payload.get("candidate_id")
    spike_id = payload.get("spike_id")
    candidate = state["candidates"].get(candidate_id)
    spike = state["spikes"].get(spike_id)
    if (
        not isinstance(candidate, dict)
        or not isinstance(spike, dict)
        or event.get("stream_id") != candidate_id
        or candidate.get("status") != "spike_authorized"
        or candidate.get("spike_id") != spike_id
        or spike.get("status") != "running"
        or spike.get("candidate_id") != candidate_id
        or any(
            payload.get(field) != spike.get(field)
            for field in (
                "attempt_id",
                "attempt_sha256",
                "lease_id",
                "lease_sha256",
                "execution_authority_relation",
            )
        )
        or payload.get("resource_grant_id")
        != spike.get("execution_authority_relation", {}).get("resource_ref", {}).get("id")
    ):
        raise IntegrityError("invalid Candidate Spike start")
    candidate.update(status="spike_running", version=event["stream_version"])


def reduce_spike_verdict_recorded(scope: EventScope) -> None:
    """Reduce SpikeVerdictRecorded."""

    payload = scope.payload
    state = scope.state
    canonical_artefact_streams = scope.canonical_artefact_streams
    required_string = scope.required_string
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
    artifact = payload.get("verdict_artifact")
    if (
        not isinstance(spike, dict)
        or not isinstance(candidate, dict)
        or not isinstance(assay, dict)
        or not isinstance(artifact, dict)
        or spike.get("status") != "running"
        or not _spike_verdict_matches(artifact, payload, candidate, assay, spike, state, canonical_artefact_streams)
        or not _spike_result_write_set_matches(scope, partial=False)
    ):
        raise IntegrityError("invalid Spike verdict")
    spike.update(
        status="verdict_recorded",
        verdict=required_string("verdict"),
        verdict_sha256=required_string("verdict_sha256"),
        verdict_artifact=deepcopy(artifact),
        producer_actor_id=event.get("actor_id"),
        version=event["stream_version"],
    )


def reduce_spike_partial_recorded(scope: EventScope) -> None:
    """Reduce SpikePartialRecorded."""

    payload = scope.payload
    state = scope.state
    canonical_artefact_streams = scope.canonical_artefact_streams
    required_string = scope.required_string
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
    artifact = payload.get("verdict_artifact")
    if (
        not isinstance(spike, dict)
        or not isinstance(candidate, dict)
        or not isinstance(assay, dict)
        or not isinstance(artifact, dict)
        or spike.get("status") != "running"
        or not _spike_verdict_matches(artifact, payload, candidate, assay, spike, state, canonical_artefact_streams)
        or not _spike_result_write_set_matches(scope, partial=True)
    ):
        raise IntegrityError("invalid Spike partial verdict")
    spike.update(
        status="partial_recorded",
        verdict=required_string("verdict"),
        verdict_sha256=required_string("verdict_sha256"),
        verdict_artifact=deepcopy(artifact),
        revisit_requirements=deepcopy(spike.get("plan_artifact", {}).get("partial_rules", [])),
        producer_actor_id=event.get("actor_id"),
        version=event["stream_version"],
    )


def _spike_result_write_set_matches(scope: EventScope, *, partial: bool) -> bool:
    """Require the complete exact Candidate and operational result transaction."""

    event = scope.event
    payload = scope.payload
    spike = scope.state["spikes"].get(payload.get("spike_id"))
    if not isinstance(spike, Mapping):
        return False
    members = sorted(
        scope.transaction_events.get(event.get("transaction_id"), ()),
        key=lambda item: item.get("transaction_index", 0),
    )
    if not partial:
        legacy = tuple(member.get("event_type") for member in members) == (
            "SpikeVerdictRecorded",
            "CandidateSpikeVerdictLinked",
        )
        if legacy:
            return bool(
                is_exact_legacy_unclosed_spike_verdict(members)
                and members[0].get("stream_id") == payload.get("spike_id")
                and members[0].get("payload") == payload
                and members[1].get("stream_id") == payload.get("candidate_id")
                and members[1].get("payload") == payload
            )
        closure_payload = {
            **deepcopy(payload),
            "attempt_id": spike.get("attempt_id"),
            "lease_id": spike.get("lease_id"),
        }
        return bool(
            tuple(member.get("event_type") for member in members)
            == (
                "SpikeVerdictRecorded",
                "AttemptCompleted",
                "LeaseReleased",
                "SpikeAttemptClosed",
                "SpikeLeaseReleased",
                "CandidateSpikeVerdictLinked",
            )
            and members[0].get("stream_id") == payload.get("spike_id")
            and members[0].get("payload") == payload
            and members[1].get("stream_id") == spike.get("attempt_id")
            and members[2].get("stream_id") == spike.get("lease_id")
            and members[3].get("stream_id") == payload.get("spike_id")
            and members[3].get("payload") == closure_payload
            and members[4].get("stream_id") == payload.get("spike_id")
            and members[4].get("payload") == closure_payload
            and members[5].get("stream_id") == payload.get("candidate_id")
            and members[5].get("payload") == payload
        )

    expected_types = (
        "SpikePartialRecorded",
        "PartialOutcomeRecorded",
        "LeaseReleased",
        "SpikeAttemptClosed",
        "SpikeLeaseReleased",
        "CandidateSpikePartialLinked",
    )
    closure_payload = {
        **deepcopy(payload),
        "attempt_id": spike.get("attempt_id"),
        "lease_id": spike.get("lease_id"),
    }
    return bool(
        tuple(member.get("event_type") for member in members) == expected_types
        and members[0].get("stream_id") == payload.get("spike_id")
        and members[0].get("payload") == payload
        and members[1].get("stream_id") == spike.get("attempt_id")
        and members[2].get("stream_id") == spike.get("lease_id")
        and members[3].get("stream_id") == payload.get("spike_id")
        and members[3].get("payload") == closure_payload
        and members[4].get("stream_id") == payload.get("spike_id")
        and members[4].get("payload") == closure_payload
        and members[5].get("stream_id") == payload.get("candidate_id")
        and members[5].get("payload") == payload
    )


def reduce_spike_attempt_closed(scope: EventScope) -> None:
    """Reduce SpikeAttemptClosed."""

    state = scope.state
    payload = scope.payload
    spike_operational_closure_matches = scope.spike_operational_closure_matches
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(spike, dict)
        or spike.get("status") not in {"verdict_recorded", "partial_recorded", "cancelled"}
        or spike.get("attempt_id") != payload.get("attempt_id")
        or not spike_operational_closure_matches(event, payload)
    ):
        raise IntegrityError("invalid Spike attempt closure")
    attempt_status = {
        "verdict_recorded": "completed",
        "partial_recorded": "partial",
        "cancelled": "cancelled",
    }[spike["status"]]
    spike.update(attempt_status=attempt_status)


def reduce_spike_lease_released(scope: EventScope) -> None:
    """Reduce SpikeLeaseReleased."""

    state = scope.state
    payload = scope.payload
    spike_operational_closure_matches = scope.spike_operational_closure_matches
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(spike, dict)
        or spike.get("attempt_status") not in {"completed", "partial", "cancelled"}
        or payload.get("lease_id") != spike.get("lease_id")
        or not spike_operational_closure_matches(event, payload)
    ):
        raise IntegrityError("invalid Spike lease release")
    spike.update(lease_status="released")


def reduce_candidate_spike_verdict_linked(scope: EventScope) -> None:
    """Reduce CandidateSpikeVerdictLinked."""

    candidate_spike_link_matches = scope.candidate_spike_link_matches
    event = scope.event
    payload = scope.payload
    state = scope.state

    if not candidate_spike_link_matches(
        event,
        payload,
        candidate_status="spike_running",
        spike_status="verdict_recorded",
        spike_event_type="SpikeVerdictRecorded",
    ):
        raise IntegrityError("invalid Candidate Spike verdict link")
    candidate = state["candidates"][payload["candidate_id"]]
    candidate.update(status="spike_verdict_recorded", version=event["stream_version"])


def reduce_candidate_spike_partial_linked(scope: EventScope) -> None:
    """Reduce CandidateSpikePartialLinked."""

    candidate_spike_link_matches = scope.candidate_spike_link_matches
    event = scope.event
    payload = scope.payload
    state = scope.state

    if not candidate_spike_link_matches(
        event,
        payload,
        candidate_status="spike_running",
        spike_status="partial_recorded",
        spike_event_type="SpikePartialRecorded",
    ):
        raise IntegrityError("invalid Candidate Spike partial link")
    candidate = state["candidates"][payload["candidate_id"]]
    candidate.update(status="spike_partial_recorded", version=event["stream_version"])


def reduce_spike_cancellation_review_requested(scope: EventScope) -> None:
    """Reduce SpikeCancellationReviewRequested, SpikePartialReviewRequested, SpikeReviewRequested."""

    event_type = scope.event_type
    payload = scope.payload
    state = scope.state
    required_string = scope.required_string
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    expected_status = {
        "SpikeReviewRequested": "verdict_recorded",
        "SpikePartialReviewRequested": "partial_recorded",
        "SpikeCancellationReviewRequested": "cancelled",
    }[event_type]
    if not isinstance(spike, dict) or spike.get("status") != expected_status:
        raise IntegrityError("invalid Spike review request")
    review = state["reviews"].get(payload.get("review_id"))
    prior_review = state["reviews"].get(spike.get("review_id"))
    relation = payload.get("review_subject_supersession")
    if (
        event.get("stream_id") != payload.get("spike_id")
        or spike.get("candidate_id") != payload.get("candidate_id")
        or not _review_subject_matches(
            review,
            subject_kind="spike",
            subject_id=payload.get("spike_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
    ):
        raise IntegrityError("invalid Spike review request")
    if spike.get("review_id") is None:
        if relation is not None or payload.get("subject_sha256") != _aggregate_content_hash(spike):
            raise IntegrityError("invalid Spike review supersession")
    elif not _valid_review_supersession(
        relation,
        prior_review,
        review.get("subject_sha256"),
        review.get("required_evidence_refs"),
    ):
        raise IntegrityError("invalid Spike review supersession")
    else:
        prior_review.update(status="superseded", superseded_by_review_id=review["review_id"])
    spike.update(
        review_id=required_string("review_id"),
        review_subject_sha256=required_string("subject_sha256"),
        review_pending=True,
        version=event["stream_version"],
    )


def reduce_spike_reviewed(scope: EventScope) -> None:
    """Reduce SpikeReviewed."""

    state = scope.state
    payload = scope.payload
    event = scope.event
    review_verdict_precedes = scope.review_verdict_precedes

    spike = state["spikes"].get(payload.get("spike_id"))
    review = state["reviews"].get(payload.get("review_id"))
    if (
        not isinstance(spike, dict)
        or event.get("stream_id") != payload.get("spike_id")
        or spike.get("status") != "verdict_recorded"
        or not spike.get("review_pending")
        or spike.get("review_id") != payload.get("review_id")
        or not isinstance(review, dict)
        or review.get("status") != "satisfied"
        or not _review_subject_matches(
            review,
            subject_kind="spike",
            subject_id=payload.get("spike_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
        or payload.get("subject_sha256") != spike.get("review_subject_sha256")
        or not review_verdict_precedes(event, payload)
    ):
        raise IntegrityError("invalid Spike reviewed transition")
    spike.update(status="reviewed", review_pending=False, version=event["stream_version"])


def reduce_candidate_spike_partial_reviewed(scope: EventScope) -> None:
    """Reduce CandidateSpikePartialReviewed."""

    state = scope.state
    payload = scope.payload
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches
    event = scope.event

    candidate = state["candidates"].get(payload.get("candidate_id"))
    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != "spike_partial_recorded"
        or candidate.get("spike_id") != payload.get("spike_id")
        or event.get("stream_id") != payload.get("candidate_id")
        or not isinstance(spike, Mapping)
        or spike.get("candidate_id") != payload.get("candidate_id")
        or spike.get("status") != "partial_reviewed"
        or spike.get("review_id") != payload.get("review_id")
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="SpikePartialReviewed",
            stream_id=payload.get("spike_id"),
        )
    ):
        raise IntegrityError("invalid Candidate Spike partial review")
    candidate.update(status="spike_revisit_eligible", version=event["stream_version"])


def reduce_spike_partial_reviewed(scope: EventScope) -> None:
    """Reduce SpikePartialReviewed."""

    state = scope.state
    payload = scope.payload
    following_transaction_event_matches = scope.following_transaction_event_matches
    review_verdict_precedes = scope.review_verdict_precedes
    event = scope.event

    spike = state["spikes"].get(payload.get("spike_id"))
    review = state["reviews"].get(payload.get("review_id"))
    if (
        not isinstance(spike, dict)
        or event.get("stream_id") != payload.get("spike_id")
        or spike.get("status") != "partial_recorded"
        or not spike.get("review_pending")
        or spike.get("review_id") != payload.get("review_id")
        or not isinstance(review, dict)
        or review.get("status") != "satisfied"
        or not _review_subject_matches(
            review,
            subject_kind="spike",
            subject_id=payload.get("spike_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
        or payload.get("subject_sha256") != spike.get("review_subject_sha256")
        or not review_verdict_precedes(event, payload)
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateSpikePartialReviewed",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Spike partial review")
    spike.update(status="partial_reviewed", review_pending=False, version=event["stream_version"])


def reduce_spike_cancelled(scope: EventScope) -> None:
    """Reduce SpikeCancelled."""

    state = scope.state
    payload = scope.payload
    required_string = scope.required_string
    event = scope.event
    following_transaction_event_matches = scope.following_transaction_event_matches

    spike = state["spikes"].get(payload.get("spike_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    decision = state["decisions"].get(spike.get("decision_id")) if isinstance(spike, Mapping) else None
    if (
        not isinstance(spike, dict)
        or not isinstance(candidate, dict)
        or event.get("stream_id") != payload.get("spike_id")
        or spike.get("status") not in {"planned", "approval_pending", "authorized", "running"}
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateEvaluationCancelled",
            stream_id=payload.get("candidate_id"),
        )
        or not _spike_cancellation_matches(
            payload.get("cancellation_artifact"),
            payload=payload,
            candidate=candidate,
            spike=spike,
            decision=decision,
            state=state,
        )
        or (spike.get("status") == "running" and not _running_cancellation_write_set_matches(scope))
    ):
        raise IntegrityError("invalid Spike cancellation")
    decision = state["decisions"].get(spike.get("decision_id"))
    if spike.get("status") == "approval_pending" and spike.get("decision_id") is not None:
        if (
            not isinstance(decision, dict)
            or decision.get("status") != "cancellation_pending"
            or decision.get("cancellation_candidate_id") != payload.get("candidate_id")
            or decision.get("cancellation_spike_id") != payload.get("spike_id")
            or decision.get("cancellation_sha256") != payload.get("cancellation_sha256")
            or decision.get("cancellation_transaction_id") != event.get("transaction_id")
        ):
            raise IntegrityError("invalid Spike execution proposal cancellation")
        decision.update(status="candidate_cancellation_pending")
    spike.update(
        status="cancelled",
        outcome_sha256=required_string("cancellation_sha256"),
        producer_actor_id=event.get("actor_id"),
        version=event["stream_version"],
    )


def _running_cancellation_write_set_matches(scope: EventScope) -> bool:
    """Require OR-022 to close a running Attempt and Lease in its own batch."""

    event = scope.event
    payload = scope.payload
    members = sorted(
        scope.transaction_events.get(event.get("transaction_id"), ()),
        key=lambda member: member.get("transaction_index", 0),
    )
    expected = (
        "SpikeCancelled",
        "PartialOutcomeRecorded",
        "LeaseReleased",
        "SpikeAttemptClosed",
        "SpikeLeaseReleased",
        "CandidateEvaluationCancelled",
    )
    if members and members[0].get("event_type") == "SpikeExecutionProposalSupersededByCancellation":
        expected = ("SpikeExecutionProposalSupersededByCancellation", *expected)
    if tuple(member.get("event_type") for member in members) != expected:
        return False
    offset = len(members) - 6
    spike = scope.state["spikes"].get(payload.get("spike_id"))
    if not isinstance(spike, Mapping):
        return False
    closure_payload = {**deepcopy(payload), "attempt_id": spike.get("attempt_id"), "lease_id": spike.get("lease_id")}
    return bool(
        members[offset].get("stream_id") == payload.get("spike_id")
        and members[offset].get("payload") == payload
        and members[offset + 3].get("stream_id") == payload.get("spike_id")
        and members[offset + 3].get("payload") == closure_payload
        and members[offset + 4].get("stream_id") == payload.get("spike_id")
        and members[offset + 4].get("payload") == closure_payload
        and members[offset + 5].get("stream_id") == payload.get("candidate_id")
        and members[offset + 5].get("payload") == payload
    )


def reduce_spike_cancellation_reviewed(scope: EventScope) -> None:
    """Reduce SpikeCancellationReviewed."""

    state = scope.state
    payload = scope.payload
    event = scope.event
    following_transaction_event_matches = scope.following_transaction_event_matches
    review_verdict_precedes = scope.review_verdict_precedes

    spike = state["spikes"].get(payload.get("spike_id"))
    review = state["reviews"].get(payload.get("review_id"))
    if (
        not isinstance(spike, dict)
        or event.get("stream_id") != payload.get("spike_id")
        or spike.get("status") != "cancelled"
        or not spike.get("review_pending")
        or spike.get("review_id") != payload.get("review_id")
        or not isinstance(review, dict)
        or review.get("status") != "satisfied"
        or not _review_subject_matches(
            review,
            subject_kind="spike",
            subject_id=payload.get("spike_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
        or payload.get("subject_sha256") != spike.get("review_subject_sha256")
        or not review_verdict_precedes(event, payload)
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateSpikeCancellationReviewed",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Spike cancellation review")
    spike.update(status="cancellation_reviewed", review_pending=False, version=event["stream_version"])


def reduce_candidate_spike_cancellation_reviewed(scope: EventScope) -> None:
    """Reduce CandidateSpikeCancellationReviewed."""

    state = scope.state
    payload = scope.payload
    event = scope.event
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches

    candidate = state["candidates"].get(payload.get("candidate_id"))
    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != "spike_cancelled"
        or event.get("stream_id") != payload.get("candidate_id")
        or candidate.get("spike_id") != payload.get("spike_id")
        or not isinstance(spike, Mapping)
        or spike.get("candidate_id") != payload.get("candidate_id")
        or spike.get("status") != "cancellation_reviewed"
        or spike.get("review_id") != payload.get("review_id")
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="SpikeCancellationReviewed",
            stream_id=payload.get("spike_id"),
        )
    ):
        raise IntegrityError("invalid Candidate Spike cancellation review")
    candidate.update(status="spike_revisit_eligible", version=event["stream_version"])
