"""Discovery assay replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.rules import _aggregate_content_hash
from research_system.discovery.rules import _assay_cancellation_matches
from research_system.discovery.rules import _assay_partial_bindings_match
from research_system.discovery.rules import _assay_scorecard_matches
from research_system.discovery.rules import _current_assay_bar_matches
from research_system.discovery.rules import _review_subject_matches
from research_system.discovery.rules import _valid_review_supersession
from research_system.errors import IntegrityError
from typing import Mapping


def reduce_assay_requested(scope: EventScope) -> None:
    """Reduce AssayRequested."""

    payload = scope.payload
    aggregate_identity_exists = scope.aggregate_identity_exists
    state = scope.state
    required_int = scope.required_int
    required_string = scope.required_string
    event = scope.event
    following_transaction_event_matches = scope.following_transaction_event_matches

    assay_id = required_string("assay_id")
    candidate_id = required_string("candidate_id")
    if (
        aggregate_identity_exists(assay_id)
        or state["candidates"].get(candidate_id, {}).get("status") not in {"registered", "assay_retry_authorized"}
        or not _current_assay_bar_matches(payload, state["assay_bar_authority"])
        or (
            payload.get("row_id") == "OR-003"
            and not following_transaction_event_matches(
                event,
                payload,
                event_type="CandidateAssayRequested",
                stream_id=candidate_id,
            )
        )
    ):
        raise IntegrityError("invalid Assay request transition")
    state["assays"][assay_id] = {
        "assay_id": assay_id,
        "candidate_id": candidate_id,
        "candidate_revision": required_int("candidate_revision"),
        "candidate_sha256": required_string("candidate_sha256"),
        "assay_bar_acceptance_sha256": required_string("assay_bar_acceptance_sha256"),
        "producer_relation_sha256": required_string("producer_relation_sha256"),
        "producer_actor_id": required_string("producer_actor_id"),
        "request_version": event["stream_version"],
        "requested_event_hash": event.get("event_hash"),
        "status": "requested",
        "version": event["stream_version"],
    }


def reduce_assay_evidence_collection_opened(scope: EventScope) -> None:
    """Reduce AssayEvidenceCollectionOpened."""

    state = scope.state
    payload = scope.payload
    event = scope.event

    assay = state["assays"].get(payload.get("assay_id"))
    if not isinstance(assay, dict) or assay.get("status") != "requested":
        raise IntegrityError("invalid Assay evidence transition")
    assay.update(status="evidence_collecting", version=event["stream_version"])


def reduce_candidate_assay_requested(scope: EventScope) -> None:
    """Reduce CandidateAssayRequested."""

    state = scope.state
    payload = scope.payload
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches
    event = scope.event
    required_string = scope.required_string

    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(payload.get("assay_id"))
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != "registered"
        or event.get("stream_id") != payload.get("candidate_id")
        or not isinstance(assay, Mapping)
        or assay.get("candidate_id") != payload.get("candidate_id")
        or assay.get("status") != "evidence_collecting"
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="AssayRequested",
            stream_id=payload.get("assay_id"),
        )
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="AssayEvidenceCollectionOpened",
            stream_id=payload.get("assay_id"),
        )
    ):
        raise IntegrityError("invalid Candidate Assay transition")
    candidate.update(status="assay_pending", assay_id=required_string("assay_id"), version=event["stream_version"])


def reduce_assay_scored(scope: EventScope) -> None:
    """Reduce AssayScored."""

    payload = scope.payload
    state = scope.state
    required_string = scope.required_string
    event = scope.event

    assay = state["assays"].get(payload.get("assay_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    artifact = payload.get("scorecard_artifact")
    if (
        not isinstance(assay, dict)
        or not isinstance(candidate, dict)
        or not isinstance(artifact, dict)
        or assay.get("status") != "evidence_collecting"
        or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
        or not _current_assay_bar_matches(assay, state["assay_bar_authority"], event.get("actor_id"))
        or not _assay_scorecard_matches(
            artifact,
            payload,
            candidate,
            assay,
            state["assay_bar_authority"],
            event.get("actor_id"),
        )
    ):
        raise IntegrityError("invalid Assay score transition")
    assay.update(
        status="scored",
        scorecard_sha256=required_string("scorecard_sha256"),
        mechanical_recommendation=artifact.get("mechanical_recommendation"),
        producer_actor_id=event.get("actor_id"),
        version=event["stream_version"],
    )


def reduce_candidate_assay_linked(scope: EventScope) -> None:
    """Reduce CandidateAssayLinked."""

    candidate_assay_link_matches = scope.candidate_assay_link_matches
    event = scope.event
    payload = scope.payload
    state = scope.state
    required_string = scope.required_string

    if not candidate_assay_link_matches(event, payload):
        raise IntegrityError("invalid Candidate Assay score transition")
    candidate = state["candidates"][payload["candidate_id"]]
    candidate.update(
        status="assay_scored",
        scorecard_sha256=required_string("scorecard_sha256"),
        version=event["stream_version"],
    )


def reduce_assay_partial_recorded(scope: EventScope) -> None:
    """Reduce AssayPartialRecorded."""

    state = scope.state
    payload = scope.payload
    following_transaction_event_matches = scope.following_transaction_event_matches
    event = scope.event
    required_string = scope.required_string

    assay = state["assays"].get(payload.get("assay_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    artifact = payload.get("partial_artifact")
    bar = state["assay_bar_authority"]
    acceptance = bar.get("acceptance") if isinstance(bar, dict) else None
    if (
        not isinstance(assay, dict)
        or not isinstance(candidate, dict)
        or not isinstance(artifact, dict)
        or not isinstance(acceptance, dict)
        or assay.get("status") != "evidence_collecting"
        or not _current_assay_bar_matches(assay, bar, event.get("actor_id"))
        or not _assay_partial_bindings_match(artifact, payload, candidate, assay, bar, acceptance)
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateAssayPartialLinked",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Assay partial transition")
    assay.update(
        status="partial_recorded",
        outcome_sha256=required_string("partial_sha256"),
        partial_artifact=deepcopy(artifact),
        revisit_requirements=deepcopy(artifact["revisit_requirements"]),
        producer_actor_id=event.get("actor_id"),
        version=event["stream_version"],
    )


def reduce_candidate_assay_partial_linked(scope: EventScope) -> None:
    """Reduce CandidateAssayPartialLinked."""

    state = scope.state
    payload = scope.payload
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches
    event = scope.event

    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(payload.get("assay_id"))
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != "assay_pending"
        or event.get("stream_id") != payload.get("candidate_id")
        or candidate.get("assay_id") != payload.get("assay_id")
        or not isinstance(assay, Mapping)
        or assay.get("candidate_id") != payload.get("candidate_id")
        or assay.get("status") != "partial_recorded"
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="AssayPartialRecorded",
            stream_id=payload.get("assay_id"),
        )
    ):
        raise IntegrityError("invalid Candidate Assay partial transition")
    candidate.update(status="assay_partial_recorded", version=event["stream_version"])


def reduce_assay_cancelled(scope: EventScope) -> None:
    """Reduce AssayCancelled."""

    state = scope.state
    payload = scope.payload
    following_transaction_event_matches = scope.following_transaction_event_matches
    event = scope.event
    required_string = scope.required_string

    assay = state["assays"].get(payload.get("assay_id"))
    candidate = state["candidates"].get(payload.get("candidate_id"))
    if (
        not isinstance(assay, dict)
        or assay.get("status") not in {"requested", "evidence_collecting"}
        or not isinstance(candidate, dict)
        or assay.get("candidate_id") != payload.get("candidate_id")
        or not _assay_cancellation_matches(
            payload.get("cancellation_artifact"),
            payload=payload,
            candidate=candidate,
            assay=assay,
            state=state,
        )
        or not following_transaction_event_matches(
            event,
            payload,
            event_type="CandidateEvaluationCancelled",
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Assay cancellation")
    assay.update(
        status="cancelled",
        outcome_sha256=required_string("cancellation_sha256"),
        cancellation_artifact=deepcopy(payload["cancellation_artifact"]),
        revisit_requirements=[payload["cancellation_artifact"]["reason"]],
        producer_actor_id=event.get("actor_id"),
        version=event["stream_version"],
    )


def reduce_candidate_evaluation_cancelled(scope: EventScope) -> None:
    """Reduce CandidateEvaluationCancelled."""

    state = scope.state
    payload = scope.payload
    event = scope.event
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches

    candidate = state["candidates"].get(payload.get("candidate_id"))
    if not isinstance(candidate, dict) or payload.get("evaluation_kind") not in {"assay", "spike"}:
        raise IntegrityError("invalid Candidate evaluation cancellation")
    if payload.get("evaluation_kind") == "spike":
        spike = state["spikes"].get(payload.get("spike_id"))
        decision = state["decisions"].get(spike.get("decision_id")) if isinstance(spike, dict) else None
        if (
            not isinstance(spike, dict)
            or event.get("stream_id") != payload.get("candidate_id")
            or candidate.get("status") not in {"spike_approval_pending", "spike_authorized", "spike_running"}
            or candidate.get("spike_id") != payload.get("spike_id")
            or spike.get("candidate_id") != payload.get("candidate_id")
            or spike.get("status") != "cancelled"
            or not preceding_transaction_event_matches(
                event,
                payload,
                event_type="SpikeCancelled",
                stream_id=payload.get("spike_id"),
            )
        ):
            raise IntegrityError("invalid Candidate evaluation cancellation")
        if (
            spike.get("decision_id") is not None
            and isinstance(decision, dict)
            and decision.get("status") in {"cancellation_pending", "candidate_cancellation_pending"}
        ):
            if (
                decision.get("status") != "candidate_cancellation_pending"
                or decision.get("cancellation_candidate_id") != payload.get("candidate_id")
                or decision.get("cancellation_spike_id") != payload.get("spike_id")
                or decision.get("cancellation_sha256") != payload.get("cancellation_sha256")
                or decision.get("cancellation_transaction_id") != event.get("transaction_id")
            ):
                raise IntegrityError("invalid Spike execution proposal cancellation")
            decision.update(status="superseded_by_cancellation")
    else:
        assay = state["assays"].get(payload.get("assay_id"))
        if (
            event.get("stream_id") != payload.get("candidate_id")
            or candidate.get("status") != "assay_pending"
            or candidate.get("assay_id") != payload.get("assay_id")
            or not isinstance(assay, Mapping)
            or assay.get("status") != "cancelled"
            or assay.get("candidate_id") != payload.get("candidate_id")
            or not preceding_transaction_event_matches(
                event,
                payload,
                event_type="AssayCancelled",
                stream_id=payload.get("assay_id"),
            )
        ):
            raise IntegrityError("invalid Candidate evaluation cancellation")
    candidate.update(
        status=f"{payload['evaluation_kind']}_cancelled",
        version=event["stream_version"],
    )


def reduce_assay_cancellation_review_requested(scope: EventScope) -> None:
    """Reduce AssayCancellationReviewRequested, AssayOutcomeReviewRequested, AssayPartialReviewRequested."""

    event_type = scope.event_type
    payload = scope.payload
    state = scope.state
    required_string = scope.required_string
    event = scope.event

    assay = state["assays"].get(payload.get("assay_id"))
    expected_status = {
        "AssayOutcomeReviewRequested": "scored",
        "AssayPartialReviewRequested": "partial_recorded",
        "AssayCancellationReviewRequested": "cancelled",
    }[event_type]
    if not isinstance(assay, dict) or assay.get("status") != expected_status:
        raise IntegrityError("invalid Assay outcome review request")
    review = state["reviews"].get(payload.get("review_id"))
    prior_review = state["reviews"].get(assay.get("review_id"))
    relation = payload.get("review_subject_supersession")
    if (
        event.get("stream_id") != payload.get("assay_id")
        or assay.get("candidate_id") != payload.get("candidate_id")
        or not _review_subject_matches(
            review,
            subject_kind="assay",
            subject_id=payload.get("assay_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
    ):
        raise IntegrityError("invalid Assay outcome review request")
    if assay.get("review_id") is None:
        if relation is not None or payload.get("subject_sha256") != _aggregate_content_hash(assay):
            raise IntegrityError("invalid Assay review supersession")
    elif not _valid_review_supersession(
        relation,
        prior_review,
        review.get("subject_sha256"),
        review.get("required_evidence_refs"),
    ):
        raise IntegrityError("invalid Assay review supersession")
    else:
        prior_review.update(status="superseded", superseded_by_review_id=review["review_id"])
    assay.update(
        review_id=required_string("review_id"),
        review_subject_sha256=required_string("subject_sha256"),
        review_pending=True,
        version=event["stream_version"],
    )


def reduce_assay_reviewed(scope: EventScope) -> None:
    """Reduce AssayReviewed."""

    state = scope.state
    payload = scope.payload
    event = scope.event
    review_verdict_precedes = scope.review_verdict_precedes

    assay = state["assays"].get(payload.get("assay_id"))
    review = state["reviews"].get(payload.get("review_id"))
    if (
        not isinstance(assay, dict)
        or event.get("stream_id") != payload.get("assay_id")
        or assay.get("status") != "scored"
        or not assay.get("review_pending")
        or assay.get("review_id") != payload.get("review_id")
        or not isinstance(review, dict)
        or review.get("status") != "satisfied"
        or not _review_subject_matches(
            review,
            subject_kind="assay",
            subject_id=payload.get("assay_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
        or payload.get("subject_sha256") != assay.get("review_subject_sha256")
        or not review_verdict_precedes(event, payload)
    ):
        raise IntegrityError("invalid Assay reviewed transition")
    assay.update(status="reviewed", review_pending=False, version=event["stream_version"])


def reduce_assay_cancellation_reviewed(scope: EventScope) -> None:
    """Reduce AssayCancellationReviewed, AssayPartialReviewed."""

    event_type = scope.event_type
    state = scope.state
    payload = scope.payload
    event = scope.event
    following_transaction_event_matches = scope.following_transaction_event_matches
    review_verdict_precedes = scope.review_verdict_precedes

    assay = state["assays"].get(payload.get("assay_id"))
    review = state["reviews"].get(payload.get("review_id"))
    expected_status = "partial_recorded" if event_type == "AssayPartialReviewed" else "cancelled"
    if (
        not isinstance(assay, dict)
        or event.get("stream_id") != payload.get("assay_id")
        or assay.get("status") != expected_status
        or assay.get("candidate_id") != payload.get("candidate_id")
        or not assay.get("review_pending")
        or assay.get("review_id") != payload.get("review_id")
        or not isinstance(review, dict)
        or review.get("status") != "satisfied"
        or not _review_subject_matches(
            review,
            subject_kind="assay",
            subject_id=payload.get("assay_id"),
            subject_sha256=payload.get("subject_sha256"),
        )
        or payload.get("subject_sha256") != assay.get("review_subject_sha256")
        or not review_verdict_precedes(event, payload)
        or not following_transaction_event_matches(
            event,
            payload,
            event_type=(
                "CandidateAssayPartialReviewed"
                if event_type == "AssayPartialReviewed"
                else "CandidateAssayCancellationReviewed"
            ),
            stream_id=payload.get("candidate_id"),
        )
    ):
        raise IntegrityError("invalid Assay reviewed transition")
    assay.update(
        status="partial_reviewed" if event_type == "AssayPartialReviewed" else "cancellation_reviewed",
        review_pending=False,
        version=event["stream_version"],
    )


def reduce_candidate_assay_cancellation_reviewed(scope: EventScope) -> None:
    """Reduce CandidateAssayCancellationReviewed, CandidateAssayPartialReviewed."""

    event_type = scope.event_type
    state = scope.state
    payload = scope.payload
    event = scope.event
    preceding_transaction_event_matches = scope.preceding_transaction_event_matches

    candidate = state["candidates"].get(payload.get("candidate_id"))
    assay = state["assays"].get(payload.get("assay_id"))
    expected_status = "assay_partial_recorded" if event_type == "CandidateAssayPartialReviewed" else "assay_cancelled"
    expected_assay_status = (
        "partial_reviewed" if event_type == "CandidateAssayPartialReviewed" else "cancellation_reviewed"
    )
    if (
        not isinstance(candidate, dict)
        or candidate.get("status") != expected_status
        or event.get("stream_id") != payload.get("candidate_id")
        or candidate.get("assay_id") != payload.get("assay_id")
        or not isinstance(assay, dict)
        or assay.get("candidate_id") != payload.get("candidate_id")
        or assay.get("status") != expected_assay_status
        or assay.get("review_id") != payload.get("review_id")
        or not preceding_transaction_event_matches(
            event,
            payload,
            event_type="AssayPartialReviewed"
            if event_type == "CandidateAssayPartialReviewed"
            else "AssayCancellationReviewed",
            stream_id=payload.get("assay_id"),
        )
    ):
        raise IntegrityError("invalid Candidate Assay review transition")
    candidate.update(status="assay_revisit_eligible", version=event["stream_version"])
