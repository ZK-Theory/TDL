"""Discovery review/decision replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.rules import _review_policy_status
from research_system.discovery.rules import _revisit_relation_matches
from research_system.discovery.rules import _valid_revisit_proposal
from research_system.errors import IntegrityError
from typing import Mapping


def reduce_review_requested(scope: EventScope) -> None:
    """Reduce ReviewRequested."""

    required_string_list = scope.required_string_list
    payload = scope.payload
    aggregate_identity_exists = scope.aggregate_identity_exists
    state = scope.state
    required_string = scope.required_string
    event = scope.event

    review_id = payload.get("new_review_id")
    subject_ids = required_string_list("subject_ids")
    subject_hashes = required_string_list("subject_hashes")
    if (
        not isinstance(review_id, str)
        or event.get("stream_id") != review_id
        or aggregate_identity_exists(review_id)
        or len(subject_ids) != 1
        or len(subject_hashes) != 1
    ):
        raise IntegrityError("invalid Discovery review request")
    subject_id = subject_ids[0]
    if subject_id.startswith("asy_"):
        subject_kind = "assay"
    elif subject_id.startswith("spk_"):
        subject_kind = "spike"
    else:
        raise IntegrityError("invalid Discovery review subject")
    state["reviews"][review_id] = {
        "review_id": review_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "subject_sha256": subject_hashes[0],
        "allowed_verdicts": required_string_list("allowed_verdicts"),
        "required_evidence_refs": required_string_list("required_evidence_refs"),
        "required_independence_grade": required_string("required_independence_grade"),
        "request_actor_id": event.get("actor_id"),
        "request_event_id": event.get("event_id"),
        "request_event_hash": event.get("event_hash"),
        "status": "pending",
        "version": event["stream_version"],
    }


def reduce_review_verdict_recorded(scope: EventScope) -> None:
    """Reduce ReviewVerdictRecorded."""

    required_string = scope.required_string
    state = scope.state
    event = scope.event
    payload = scope.payload

    review_id = required_string("review_id")
    review = state["reviews"].get(review_id)
    reviewer_actor_id = required_string("reviewer_actor_id")
    subject_collection = {
        "assay": state["assays"],
        "spike": state["spikes"],
    }.get(review.get("subject_kind") if isinstance(review, dict) else None)
    subject = (
        subject_collection.get(review.get("subject_id"))
        if isinstance(subject_collection, dict) and isinstance(review, dict)
        else None
    )
    if (
        not isinstance(review, dict)
        or not isinstance(subject, dict)
        or event["stream_id"] != review_id
        or review.get("status") != "pending"
        or review.get("subject_sha256") != payload.get("unchanged_subject_sha256")
        or payload.get("verdict") not in review.get("allowed_verdicts", ())
        or reviewer_actor_id != event.get("actor_id")
        or reviewer_actor_id == review.get("request_actor_id")
        or reviewer_actor_id == subject.get("producer_actor_id")
        or payload.get("computed_independence_grade") != review.get("required_independence_grade")
    ):
        raise IntegrityError("invalid Discovery review verdict")
    review.update(
        status=_review_policy_status(payload),
        verdict=required_string("verdict"),
        reviewer_actor_id=reviewer_actor_id,
        verdict_event_id=event.get("event_id"),
        verdict_event_hash=event.get("event_hash"),
        verdict_global_position=event.get("global_position"),
        version=event["stream_version"],
    )


def reduce_decision_proposed(scope: EventScope) -> None:
    """Reduce DecisionProposed."""

    required_string = scope.required_string
    required_string_list = scope.required_string_list
    aggregate_identity_exists = scope.aggregate_identity_exists
    state = scope.state
    event = scope.event
    payload = scope.payload

    decision_id = required_string("new_decision_id")
    options = required_string_list("options")
    if event["stream_id"] != decision_id or aggregate_identity_exists(decision_id) or len(set(options)) != len(options):
        raise IntegrityError("invalid Discovery decision proposal")
    state["decisions"][decision_id] = {
        "status": "proposed",
        "kind": payload.get("discovery_kind"),
        "decision_kind": required_string("decision_kind"),
        "recommendation": required_string("recommendation"),
        "options": options,
        "expires_at": payload.get("expires_at"),
        "proposal_event_hash": event.get("event_hash"),
        "proposal_version": event["stream_version"],
        "version": event["stream_version"],
    }


def reduce_decision_resolved(scope: EventScope) -> None:
    """Reduce DecisionResolved."""

    required_string = scope.required_string
    state = scope.state
    event = scope.event

    decision_id = required_string("decision_id")
    decision = state["decisions"].get(decision_id)
    selected_option = required_string("selected_option")
    if (
        event["stream_id"] != decision_id
        or not isinstance(decision, dict)
        or decision.get("status") != "proposed"
        or selected_option not in decision.get("options", ())
    ):
        raise IntegrityError("invalid Discovery decision resolution")
    decision.update(status="resolved", selected_option=selected_option, version=event["stream_version"])


def reduce_spike_execution_proposal_superseded_by_cancellation(scope: EventScope) -> None:
    """Reduce SpikeExecutionProposalSupersededByCancellation."""

    state = scope.state
    payload = scope.payload
    required_string = scope.required_string
    event = scope.event

    decision = state["decisions"].get(payload.get("decision_id"))
    spike = state["spikes"].get(payload.get("spike_id"))
    if (
        not isinstance(decision, dict)
        or decision.get("status") != "proposed"
        or not isinstance(spike, dict)
        or spike.get("status") != "approval_pending"
        or spike.get("decision_id") != payload.get("decision_id")
        or spike.get("candidate_id") != payload.get("candidate_id")
        or event.get("stream_id") != payload.get("decision_id")
        or not isinstance(event.get("transaction_id"), str)
    ):
        raise IntegrityError("invalid Spike execution proposal cancellation")
    decision.update(
        status="cancellation_pending",
        cancellation_candidate_id=required_string("candidate_id"),
        cancellation_spike_id=required_string("spike_id"),
        cancellation_sha256=required_string("cancellation_sha256"),
        cancellation_transaction_id=event.get("transaction_id"),
        version=event["stream_version"],
    )


def reduce_assay_revisit_requested(scope: EventScope) -> None:
    """Reduce AssayRevisitRequested, SpikeRevisitRequested."""

    state = scope.state
    event_type = scope.event_type
    payload = scope.payload
    required_string = scope.required_string
    event = scope.event

    collection = state["assays"] if event_type.startswith("Assay") else state["spikes"]
    subject_id = payload.get("assay_id") if event_type.startswith("Assay") else payload.get("spike_id")
    subject = collection.get(subject_id)
    review = state["reviews"].get(payload.get("review_id"))
    decision = state["decisions"].get(payload.get("decision_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    if (
        not isinstance(subject, dict)
        or subject.get("candidate_id") != payload.get("candidate_id")
        or subject.get("status") not in {"partial_reviewed", "cancellation_reviewed", "reviewed", "parked"}
        or subject.get("review_id") != payload.get("review_id")
        or not isinstance(review, dict)
        or review.get("status") != "satisfied"
        or not _valid_revisit_proposal(payload.get("w2_payload"), payload.get("review_id"))
        or payload["w2_payload"].get("new_decision_id") != payload.get("decision_id")
        or not isinstance(decision, dict)
        or decision.get("status") != "proposed"
        or decision.get("options") != payload["w2_payload"].get("options")
        or not isinstance(candidate, dict)
        or not _revisit_relation_matches(
            payload.get("revisit_relation"),
            decision_id=payload.get("decision_id"),
            candidate=candidate,
            aggregate_id=subject_id,
            aggregate=subject,
            review=review,
            observations=state["source_observations"],
            recommendation=payload["w2_payload"].get("recommendation"),
            actor_id=event.get("actor_id"),
        )
    ):
        raise IntegrityError("invalid Discovery revisit request")
    subject.update(
        status="revisit_pending",
        decision_id=required_string("decision_id"),
        revisit_relation=deepcopy(payload["revisit_relation"]),
    )


def reduce_candidate_assay_revisit_requested(scope: EventScope) -> None:
    """Reduce CandidateAssayRevisitRequested, CandidateSpikeRevisitRequested."""

    state = scope.state
    payload = scope.payload
    event_type = scope.event_type
    required_string = scope.required_string

    candidate = state["candidates"].get(payload.get("candidate_id"))
    kind = "assay" if event_type.startswith("CandidateAssay") else "spike"
    if not isinstance(candidate, dict) or candidate.get("status") not in {f"{kind}_revisit_eligible", "parked"}:
        raise IntegrityError("invalid Candidate revisit request")
    candidate.update(status=f"{kind}_revisit_pending", decision_id=required_string("decision_id"))


def reduce_assay_revisit_resolved(scope: EventScope) -> None:
    """Reduce AssayRevisitResolved, SpikeRevisitResolved."""

    state = scope.state
    required_string = scope.required_string
    payload = scope.payload
    event = scope.event
    event_type = scope.event_type
    following_transaction_event_matches = scope.following_transaction_event_matches

    kind = "assay" if event_type.startswith("Assay") else "spike"
    collection = state[f"{kind}s"]
    subject_id = payload.get(f"{kind}_id")
    subject = collection.get(subject_id)
    decision = state["decisions"].get(payload.get("decision_id"))
    selected = required_string("selected_option")
    if (
        not isinstance(subject, dict)
        or subject.get("status") != "revisit_pending"
        or subject.get("candidate_id") != payload.get("candidate_id")
        or event.get("stream_id") != subject_id
        or not isinstance(decision, dict)
        or subject.get("decision_id") != payload.get("decision_id")
        or decision.get("status") != "resolved"
        or decision.get("selected_option") != selected
        or selected not in {"RETRY", "PARK", "KILL"}
        or not following_transaction_event_matches(
            event,
            payload,
            event_type=f"Candidate{kind.title()}RevisitResolved",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Discovery revisit resolution")
    subject.update(status={"RETRY": "retry_authorized", "PARK": "parked", "KILL": "killed"}[selected])
    if selected == "PARK":
        subject["parked_at_global_position"] = event["global_position"]


def reduce_candidate_assay_revisit_resolved(scope: EventScope) -> None:
    """Reduce CandidateAssayRevisitResolved, CandidateSpikeRevisitResolved."""

    required_string = scope.required_string
    payload = scope.payload
    event = scope.event
    state = scope.state
    event_type = scope.event_type
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches

    candidate = state["candidates"].get(payload.get("candidate_id"))
    kind = "assay" if event_type.startswith("CandidateAssay") else "spike"
    subject_id = payload.get(f"{kind}_id")
    selected = required_string("selected_option")
    decision = state["decisions"].get(payload.get("decision_id"))
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != f"{kind}_revisit_pending"
        or candidate.get(f"{kind}_id") != subject_id
        or event.get("stream_id") != payload.get("candidate_id")
        or candidate.get("decision_id") != payload.get("decision_id")
        or not isinstance(decision, Mapping)
        or decision.get("status") != "resolved"
        or decision.get("selected_option") != selected
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type=f"{kind.title()}RevisitResolved",
            stream_id=subject_id,
        )
    ):
        raise IntegrityError("invalid Candidate revisit resolution")
    candidate.update(status={"RETRY": f"{kind}_retry_authorized", "PARK": "parked", "KILL": "killed"}.get(selected))
    if candidate.get("status") is None:
        raise IntegrityError("invalid Candidate revisit option")
    if selected == "PARK":
        candidate["parked_at_global_position"] = event["global_position"]


def reduce_assay_superseded(scope: EventScope) -> None:
    """Reduce AssaySuperseded, SpikeSuperseded."""

    state = scope.state
    event_type = scope.event_type
    payload = scope.payload

    collection = state["assays"] if event_type.startswith("Assay") else state["spikes"]
    subject_id = payload.get("old_assay_id") if event_type.startswith("Assay") else payload.get("old_spike_id")
    subject = collection.get(subject_id)
    if not isinstance(subject, dict) or subject.get("status") != "retry_authorized":
        raise IntegrityError("invalid Discovery retry supersession")
    subject.update(status="superseded")


def reduce_candidate_assay_retry_started(scope: EventScope) -> None:
    """Reduce CandidateAssayRetryStarted, CandidateSpikeRetryStarted."""

    state = scope.state
    payload = scope.payload
    event_type = scope.event_type

    candidate = state["candidates"].get(payload.get("candidate_id"))
    kind = "assay" if event_type.startswith("CandidateAssay") else "spike"
    new_id = payload.get("assay_id") if kind == "assay" else payload.get("spike_id")
    if not isinstance(candidate, dict) or candidate.get("status") != f"{kind}_retry_authorized":
        raise IntegrityError("invalid Candidate retry transition")
    candidate.update(status=f"{kind}_pending" if kind == "assay" else "spike_approval_pending")
    candidate[f"{kind}_id"] = new_id
