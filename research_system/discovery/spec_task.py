"""06s Phase 2: public Task closure on the SPEC route.

The action composes existing governed Task and Review commands. Every effect keeps
its own recorded actor and authority grant: the producer and the owner decision run
under the owner operator config, and the independent verdict runs under a distinct
reviewer config. Nothing here adjudicates authority; the inherited CommandService
and authority resolver do. Closure follows only from correctly bound effects, never
from attempt completion, lease release or result presence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry

ACTION = "close_task"
INTENT_SCHEMA_ID = "ars://portfolio/spec-task-intent"

EFFECTS = (
    "SubmitForReview",
    "RequestReview",
    "AssignReview",
    "StartReview",
    "RecordReviewVerdict",
    "SatisfyReview",
    "AcceptTask",
)

_EFFECT_EVENTS = {
    "SubmitForReview": "TaskSubmittedForReview",
    "RequestReview": "ReviewRequested",
    "AssignReview": "ReviewAssigned",
    "StartReview": "ReviewStarted",
    "RecordReviewVerdict": "ReviewVerdictRecorded",
    "SatisfyReview": "ReviewSatisfied",
    "AcceptTask": "TaskAccepted",
}

# Route-fixed review policy. The caller supplies evidence, never the independence
# grade, the visibility policy, the satisfaction authority or the allowed verdicts.
#
# The computed grade equals the required grade because it is exactly what this route
# evidences and nothing more: a distinct recorded actor, a distinct authority grant
# and a verdict bound to the exact reviewed subject hash. Never record a grade the
# route cannot demonstrate; a stronger independence claim needs evidence about actor
# families, sessions and context that this route does not collect.
_INDEPENDENCE_GRADE = "independent_exact_subject"
_VISIBILITY_POLICY = "owner_and_reviewer"
_SATISFACTION_AUTHORITY = "owner"
_APPROVE_VERDICT = "approve"
# The route records only an approving verdict; refusal is the reviewer's other
# option and must therefore be permitted by the request the verdict answers.
_ALLOWED_VERDICTS = ("approve", "reject")
_VERDICT_RECORDED = "verdict_recorded"
# A Review that reached one of these can never answer the request it was raised for.
_TERMINAL_REVIEW_EVENTS = ("ReviewWithdrawn", "ReviewSuperseded")

_REQUIRED_EVIDENCE: dict[str, frozenset[str]] = {
    "RequestReview": frozenset(
        {
            "review_type",
            "governing_refs",
            "review_questions",
            "required_evidence_refs",
            "required_lanes",
            "reviewer_capability",
            "deadline",
            "escalation_rule",
        }
    ),
    "AssignReview": frozenset({"reviewer_actor_id", "independence_evidence_refs"}),
    "RecordReviewVerdict": frozenset(
        {
            "required_evidence_refs",
            "reviewer_profile",
            "reviewer_session",
            "reviewer_model_metadata",
            "context_manifest_id",
            "context_manifest_sha256",
            "trace_visibility_evidence_refs",
        }
    ),
    "SatisfyReview": frozenset({"policy_evaluation_refs", "satisfaction_gate"}),
}


def subject_ids(intent: dict[str, Any]) -> dict[str, str]:
    """Return the pre-existing governed subjects this action binds.

    Args:
        intent: Validated semantic close_task intent.

    Returns:
        The task, attempt and review identities carried by the intent.
    """
    return {key: intent[key] for key in ("task_id", "attempt_id", "review_id")}


def _streams(
    events: list[dict],
    schemas: SchemaRegistry,
    *,
    before_position: int | None = None,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    selected = events if before_position is None else [e for e in events if e["global_position"] < before_position]
    return replay(tuple(selected), schema_registry=schemas, authority_state_validator=authority_state_validator)[
        "streams"
    ]


def _reviewed_subject_hash(
    ids: dict[str, str],
    events: list[dict],
    schemas: SchemaRegistry,
    request: dict | None,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    """Return the exact Task hash this action's review is, or will be, raised against.

    Args:
        ids: This action's governed subjects.
        events: Full ordered ledger event list.
        schemas: Runtime schema registry used for projection.
        request: The located ReviewRequested event, or None before one exists.
        authority_state_validator: Inherited validator for authority projections.

    Returns:
        The Task state hash as of just before the request, or the current hash.
    """
    # CommandService validates RequestReview subject hashes against current state, and
    # a Task at review_pending can still be validly paused, blocked or resumed. Hashing
    # the state right after SubmitForReview would therefore go stale and strand the
    # route on stale_subject_hash with no way back to review_pending.
    before = None if request is None else request["global_position"]
    return _subject_hash(
        events, ids["task_id"], schemas, before_position=before, authority_state_validator=authority_state_validator
    )


def _subject_hash(
    events: list[dict],
    task_id: str,
    schemas: SchemaRegistry,
    *,
    before_position: int | None = None,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    task = _streams(
        events, schemas, before_position=before_position, authority_state_validator=authority_state_validator
    ).get(task_id)
    if not isinstance(task, dict):
        raise ArsError(f"close_task requires an existing Task: {task_id}")
    return sha256_hex(canonical_bytes(task))


def _artefact_content_hash(events: list[dict], artefact_id: str, *, before_position: int | None = None) -> str:
    matches = [
        event
        for event in events
        if event["event_type"] == "ArtefactRegistered"
        and event["stream_id"] == artefact_id
        and (before_position is None or event["global_position"] < before_position)
    ]
    if len(matches) != 1:
        raise IntegrityError(f"close_task cannot bind an exact candidate artefact hash: {artefact_id}")
    return matches[0]["payload"]["manifest"]["content_sha256"]


def _locate(effect: str, ids: dict[str, str], events: list[dict], after_position: int) -> dict | None:
    """Find the one event that correctly binds this effect to this action's subjects."""
    event_type = _EFFECT_EVENTS[effect]
    stream_id = ids["task_id"] if effect in {"SubmitForReview", "AcceptTask"} else ids["review_id"]
    for event in events:
        if event["event_type"] != event_type or event["stream_id"] != stream_id:
            continue
        if event["global_position"] <= after_position:
            continue
        payload = event["payload"]
        if effect == "SubmitForReview" and (
            payload.get("attempt_id") != ids["attempt_id"]
            or ids["review_id"] not in tuple(payload.get("requested_review_ids", ()))
        ):
            continue
        if effect == "AcceptTask" and ids["review_id"] not in tuple(payload.get("satisfied_review_ids", ())):
            continue
        return event
    return None


def evaluate(
    intent: dict[str, Any],
    events: list[dict],
    *,
    schemas: SchemaRegistry,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Derive close_task state purely from correctly bound ledger evidence.

    Args:
        intent: Validated semantic close_task intent.
        events: Full ordered ledger event list.
        schemas: Runtime schema registry used for projection.
        authority_state_validator: Inherited validator for authority projections.

    Returns:
        One state record with the ordered completed effects and the next effect.

    Raises:
        ConflictError: If located evidence contradicts closure through this action.
        IntegrityError: If located evidence binds another subject, another actor
            relation or another exact subject hash than this action requires.
    """
    ids = subject_ids(intent)
    state: dict[str, Any] = {
        "action": ACTION,
        "state": "not_started",
        **ids,
        "next_effect": EFFECTS[0],
        "effects": [],
    }
    located: list[dict] = []
    position = 0
    for effect in EFFECTS:
        event = _locate(effect, ids, events, position)
        if event is None:
            break
        located.append(event)
        position = event["global_position"]

    if located:
        _validate_binding(intent, ids, located, events, schemas, authority_state_validator)
        state["state"] = "prepared"
        state["subject_sha256"] = _reviewed_subject_hash(
            ids, events, schemas, _locate("RequestReview", ids, events, 0), authority_state_validator
        )
    else:
        # Terminality is deliberately not checked here: the inherited SubmitForReview
        # precondition owns it, and a decisive negative control covers that refusal.
        streams = _streams(events, schemas, authority_state_validator=authority_state_validator)
        attempt = streams.get(ids["attempt_id"])
        if not isinstance(streams.get(ids["task_id"]), dict):
            raise IntegrityError(f"close_task names no existing Task: {ids['task_id']}")
        if not isinstance(attempt, dict) or attempt.get("task_id") != ids["task_id"]:
            raise IntegrityError(f"close_task Attempt is not bound to this Task: {ids['attempt_id']}")
        if any(event["stream_id"] == ids["review_id"] for event in events):
            # RequestReview requires an empty Review stream and SubmitForReview cannot
            # be repeated from review_pending, so starting here would strand the Task.
            raise IntegrityError(f"close_task review identity is already in use: {ids['review_id']}")
        state["subject_sha256"] = _reviewed_subject_hash(ids, events, schemas, None, authority_state_validator)
    state["effects"] = [
        {
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
            "command_id": event["command_id"],
            "actor_id": event["actor_id"],
            "authority_grant_id": event["authority_grant_id"],
        }
        for event in located
    ]
    state["next_effect"] = EFFECTS[len(located)] if len(located) < len(EFFECTS) else None
    if state["next_effect"] is None:
        state["state"] = "completed"
    return state


def _validate_binding(
    intent: dict[str, Any],
    ids: dict[str, str],
    located: list[dict],
    events: list[dict],
    schemas: SchemaRegistry,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Reject located evidence that does not bind this exact subject and actors."""
    by_effect = dict(zip(EFFECTS, located, strict=False))
    submitted = by_effect["SubmitForReview"]
    request = by_effect.get("RequestReview")
    subject_sha256 = _reviewed_subject_hash(ids, events, schemas, request, authority_state_validator)

    # F4: a withdrawn or superseded Review can never answer its request, so every
    # remaining effect would be refused forever. That is conflicting evidence, not
    # progress, and the coordinator's listing already contains a ConflictError.
    terminal = [
        event
        for event in events
        if event["event_type"] in _TERMINAL_REVIEW_EVENTS and event["stream_id"] == ids["review_id"]
    ]
    if terminal:
        raise ConflictError(f"close_task review reached {terminal[-1]['event_type']} and cannot be answered")

    # N7: inherited SubmitForReview admission checks candidate identities against the
    # Attempt but only the COUNT of supplied hashes, so verify the values here.
    submitted_payload = submitted["payload"]
    candidates = tuple(submitted_payload.get("candidate_artefact_ids", ()))
    hashes = tuple(submitted_payload.get("candidate_artefact_hashes", ()))
    if len(candidates) != len(hashes):
        raise IntegrityError("close_task submission candidate identities and hashes are not paired")
    for candidate, claimed in zip(candidates, hashes, strict=True):
        if claimed != _artefact_content_hash(events, candidate, before_position=submitted["global_position"]):
            raise IntegrityError(f"close_task submission claims an unregistered candidate hash: {candidate}")

    if request is not None:
        payload = request["payload"]
        pairs = tuple(zip(payload.get("subject_ids", ()), payload.get("subject_hashes", ()), strict=False))
        if (ids["task_id"], subject_sha256) not in pairs:
            raise IntegrityError("close_task review request does not bind the exact reviewed Task subject")
        if payload.get("required_independence_grade") != _INDEPENDENCE_GRADE:
            raise IntegrityError("close_task review request does not require exact-subject independence")
        if payload.get("satisfaction_authority") != _SATISFACTION_AUTHORITY:
            raise IntegrityError("close_task review request does not reserve satisfaction to the owner")
        # N1: a Review raised elsewhere may permit verdicts this route cannot answer
        # with, and admission does not compare the recorded verdict to this set.
        if _APPROVE_VERDICT not in tuple(payload.get("allowed_verdicts", ())):
            raise IntegrityError("close_task review request does not permit an approving verdict")
        # N4: the reviewed subject is pinned at the request, but acceptance hashes the
        # Task as it stands. If it drifted, every remaining effect is already doomed.
        if "AcceptTask" not in by_effect:
            current = _subject_hash(
                events, ids["task_id"], schemas, authority_state_validator=authority_state_validator
            )
            if current != subject_sha256:
                raise ConflictError("close_task reviewed Task subject changed after its review request")

    # The next three checks restate boundaries CommandService also enforces, so the
    # route refuses before submitting anything. test_spec_task.py exercises those
    # inherited refusals directly, so neither layer is trusted on the other's behalf.
    assigned = by_effect.get("AssignReview")
    reviewer = assigned["payload"].get("reviewer_actor_id") if assigned is not None else None
    if assigned is not None:
        if reviewer == submitted["actor_id"]:
            raise IntegrityError("close_task cannot assign the producing actor as its own reviewer")
        if assigned["payload"].get("computed_independence_grade") != _INDEPENDENCE_GRADE:
            raise IntegrityError("close_task review assignment does not establish exact-subject independence")

    verdict = by_effect.get("RecordReviewVerdict")
    if verdict is not None:
        recorded = verdict["payload"].get("verdict")
        if recorded != _APPROVE_VERDICT:
            # The inherited path can satisfy and accept a non-approving verdict, so
            # reporting "prepared" here would under-report an already decided Task.
            raise ConflictError(f"close_task review verdict does not approve the subject: {recorded}")
        if verdict["actor_id"] == submitted["actor_id"]:
            raise IntegrityError("close_task review verdict lacks an independent actor")
        if reviewer is not None and verdict["actor_id"] != reviewer:
            raise IntegrityError("close_task review verdict was not recorded by the assigned reviewer")
        if verdict["payload"].get("unchanged_subject_sha256") != subject_sha256:
            raise IntegrityError("close_task review verdict does not bind the exact reviewed Task subject")
        if verdict["payload"].get("producing_attempt_id") != ids["attempt_id"]:
            # Review admission does not validate this field, and AcceptTask ignores it,
            # so a verdict naming another Attempt would otherwise complete the action.
            raise IntegrityError("close_task review verdict names another producing Attempt")

    accepted = by_effect.get("AcceptTask")
    if accepted is not None:
        requested = set(str(value) for value in submitted_payload.get("requested_review_ids", ()))
        satisfied = set(str(value) for value in accepted["payload"].get("satisfied_review_ids", ()))
        if not requested.issubset(satisfied):
            # Admission validates only the ids the payload supplies, so an acceptance
            # raised elsewhere can close the Task with other requested gates open.
            raise IntegrityError("close_task acceptance omits reviews the submission requested")
        if verdict["authority_grant_id"] == submitted["authority_grant_id"]:
            raise IntegrityError("close_task review verdict reuses the producing authority grant")

    # Acceptance ordering and Task binding need no check here: _locate already
    # requires strictly increasing positions on this exact Task stream, and the
    # inherited AcceptTask precondition requires the named review to be satisfied
    # against the exact Task hash.


def effect_command(
    effect: str,
    intent: dict[str, Any],
    state: dict[str, Any],
    events: list[dict],
    *,
    actor_id: str,
    evidence: dict[str, Any] | None,
    schemas: SchemaRegistry,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the exact target stream and payload for one close_task effect.

    Args:
        effect: The next uncompleted effect name.
        intent: Validated semantic close_task intent.
        state: Current evaluated state for this action.
        events: Full ordered ledger event list.
        actor_id: Actor recorded on this individual command.
        evidence: Independent evidence supplied for effects that require it.
        schemas: Runtime schema registry used for projection.
        authority_state_validator: Inherited validator for authority projections.

    Returns:
        The target stream identity and the exact command payload.

    Raises:
        ArsError: If a required evidence document is absent.
        IntegrityError: If evidence fields are inexact or the actor relation for
            this effect is not permitted.
    """
    ids = subject_ids(intent)
    required = _REQUIRED_EVIDENCE.get(effect)
    if required is None:
        if evidence is not None:
            raise IntegrityError(f"close_task {effect} takes no independent evidence")
    else:
        if not isinstance(evidence, dict):
            raise ArsError(f"{effect} requires independent evidence in --input")
        if set(evidence) != set(required):
            raise IntegrityError(f"close_task {effect} evidence fields are not exact")
    streams = _streams(events, schemas, authority_state_validator=authority_state_validator)

    if effect == "SubmitForReview":
        return ids["task_id"], _submit_payload(ids, streams, events)
    if effect == "AcceptTask":
        return ids["task_id"], _accept_payload(ids, streams, _locate("SubmitForReview", ids, events, 0))

    producer = state["effects"][0]
    subject_sha256 = state["subject_sha256"]
    if effect == "RequestReview":
        return ids["review_id"], {
            "new_review_id": ids["review_id"],
            "subject_ids": [ids["task_id"]],
            "subject_hashes": [subject_sha256],
            "required_independence_grade": _INDEPENDENCE_GRADE,
            "visibility_policy": _VISIBILITY_POLICY,
            "satisfaction_authority": _SATISFACTION_AUTHORITY,
            "allowed_verdicts": list(_ALLOWED_VERDICTS),
            **evidence,
        }
    if effect == "AssignReview":
        if evidence["reviewer_actor_id"] == producer["actor_id"]:
            raise IntegrityError("close_task cannot assign the producing actor as its own reviewer")
        return ids["review_id"], {
            "review_id": ids["review_id"],
            "computed_independence_grade": _INDEPENDENCE_GRADE,
            **evidence,
        }

    assigned_reviewer = _assigned_reviewer(ids, events)
    if effect in {"StartReview", "RecordReviewVerdict"}:
        if actor_id == producer["actor_id"]:
            raise IntegrityError(f"close_task {effect} requires an actor independent of the producer")
        if actor_id != assigned_reviewer:
            raise IntegrityError(f"close_task {effect} requires the assigned reviewer")
    if effect == "StartReview":
        return ids["review_id"], {
            "review_id": ids["review_id"],
            "unchanged_subject_sha256": subject_sha256,
            "visibility_policy": _VISIBILITY_POLICY,
        }
    if effect == "RecordReviewVerdict":
        requested = _request_event(ids, events)
        if _APPROVE_VERDICT not in tuple(requested["payload"].get("allowed_verdicts", ())):
            raise IntegrityError("close_task review request does not permit an approving verdict")
        return ids["review_id"], {
            "review_id": ids["review_id"],
            "verdict": _APPROVE_VERDICT,
            "findings": [],
            "reviewer_actor_id": actor_id,
            "limitations": [],
            "conditions": [],
            "unchanged_subject_sha256": subject_sha256,
            "producing_attempt_id": ids["attempt_id"],
            "computed_independence_grade": _INDEPENDENCE_GRADE,
            **evidence,
        }
    if effect == "SatisfyReview":
        review = streams.get(ids["review_id"])
        prior = review.get("status") if isinstance(review, dict) else None
        if prior != _VERDICT_RECORDED:
            raise IntegrityError(f"close_task cannot satisfy a review in state {prior}")
        return ids["review_id"], {
            "review_id": ids["review_id"],
            "prior_review_state": _VERDICT_RECORDED,
            **evidence,
        }
    raise ArsError(f"unsupported close_task effect: {effect}")


def _request_event(ids: dict[str, str], events: list[dict]) -> dict:
    requested = [
        event for event in events if event["event_type"] == "ReviewRequested" and event["stream_id"] == ids["review_id"]
    ]
    if not requested:
        raise IntegrityError("close_task has no review request to answer")
    return requested[0]


def _assigned_reviewer(ids: dict[str, str], events: list[dict]) -> str:
    assigned = [
        event for event in events if event["event_type"] == "ReviewAssigned" and event["stream_id"] == ids["review_id"]
    ]
    if not assigned:
        raise IntegrityError("close_task review has no assigned reviewer")
    return assigned[0]["payload"]["reviewer_actor_id"]


def _submit_payload(ids: dict[str, str], streams: dict[str, Any], events: list[dict]) -> dict[str, Any]:
    attempt = streams.get(ids["attempt_id"])
    if not isinstance(attempt, dict) or attempt.get("task_id") != ids["task_id"]:
        raise IntegrityError("close_task requires a terminal Attempt bound to this Task")
    candidates = list((attempt.get("outcome") or {}).get("candidate_artefact_ids") or [])
    return {
        "task_id": ids["task_id"],
        "attempt_id": ids["attempt_id"],
        "candidate_artefact_ids": candidates,
        "attempt_outcome": attempt.get("status"),
        "candidate_artefact_hashes": [_artefact_content_hash(events, value) for value in candidates],
        "requested_review_ids": [ids["review_id"]],
    }


def _accept_payload(ids: dict[str, str], streams: dict[str, Any], submitted: dict | None) -> dict[str, Any]:
    task = streams.get(ids["task_id"])
    if not isinstance(task, dict):
        raise ArsError(f"close_task requires an existing Task: {ids['task_id']}")
    if submitted is None:
        raise IntegrityError("close_task has no review submission to accept")
    # Name every review the submission requested, not just this action's own. Inherited
    # admission validates only the ids supplied here, so accepting on one satisfied
    # review would terminally accept a Task whose other requested gates are open.
    requested = [str(value) for value in submitted["payload"].get("requested_review_ids", ())]
    if ids["review_id"] not in requested:
        raise IntegrityError("close_task review is not among the submitted requested reviews")
    # N5: acceptance admission compares criterion SETS, so an empty set passes, but
    # reduce_task rejects an empty satisfied set. Never build an event whose own
    # reducer refuses it; that would leave the ledger unreplayable.
    if not tuple(task.get("definition", {}).get("acceptance_criteria", ())):
        raise IntegrityError("close_task cannot accept a Task with no acceptance criteria")
    # N8: the governed contract supports selecting a bounded subset of the submitted
    # candidates, and this route has no way for an owner to express that choice.
    # Refuse rather than accept the Task with its deliverables silently discarded.
    if tuple(submitted["payload"].get("candidate_artefact_ids", ())):
        raise IntegrityError("close_task cannot select accepted artefacts; the submission carried candidates")
    return {
        "task_id": ids["task_id"],
        "task_revision": task.get("current_revision"),
        "satisfied_review_ids": requested,
        "satisfied_acceptance_criteria": list(task.get("definition", {}).get("acceptance_criteria", ())),
        "selected_artefact_ids": [],
    }


def enumerated_intents(events: list[dict]) -> list[dict[str, Any]]:
    """Recover every close_task intent already present in the ledger.

    Args:
        events: Full ordered ledger event list.

    Returns:
        One semantic intent per bound Task review submission, in ledger order.
    """
    intents = []
    for event in events:
        if event["event_type"] != "TaskSubmittedForReview":
            continue
        payload = event["payload"]
        for review_id in tuple(payload.get("requested_review_ids", ())):
            # requested_review_ids is an unconstrained string list on the governed
            # command, so another flow's submission can name a non-review value.
            # Such a Task is not a close_task subject and must not fail the listing.
            if not str(review_id).startswith("rev_"):
                continue
            intents.append(
                {
                    "action": ACTION,
                    "task_id": event["stream_id"],
                    "attempt_id": payload["attempt_id"],
                    "review_id": review_id,
                    "reason": "recorded Task review submission",
                }
            )
    return intents
