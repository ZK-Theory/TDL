"""06s Phase 2: public Task closure on the SPEC route.

The action composes existing governed Task and Review commands. Every effect keeps
its own recorded actor and authority grant: the producer and the owner decision run
under the owner operator config, and the independent verdict runs under a distinct
reviewer config. Nothing here adjudicates authority; the inherited CommandService
and authority resolver do. Closure follows only from correctly bound effects, never
from attempt completion, lease release or result presence.

Only evidence this route issued can advance the action. Each located closure event
must carry the route's own retry key for this intent, and its payload must equal
what the route derives at that ledger position. Any other event on the Review
stream, or on the Task stream after the review request, is conflicting evidence.
Checking foreign evidence field by field is an open-ended surface; refusing it as a
class is not.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.methods.registration import _stable_command_id
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
_TASK_STREAM_EFFECTS = frozenset({"SubmitForReview", "AcceptTask"})

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
_REVIEW_PENDING = "review_pending"

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

_Validator = Callable[[dict[str, Any]], None] | None


def subject_ids(intent: dict[str, Any]) -> dict[str, str]:
    """Return the pre-existing governed subjects this action binds.

    Args:
        intent: Validated semantic close_task intent.

    Returns:
        The task, attempt and review identities carried by the intent.
    """
    return {key: intent[key] for key in ("task_id", "attempt_id", "review_id")}


_KEY_FIELDS = ("action", "task_id", "attempt_id", "review_id")


def key_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Return the part of an intent that identifies its effects.

    ``reason`` is free text carried on each command envelope, and it is not recorded
    on ledger events. It must not enter the retry key: the enumerating listing rebuilds
    intents from events alone, so it could never reproduce a key that included it, and
    every effect the route issued would then read as foreign.

    Args:
        intent: Validated semantic close_task intent.

    Returns:
        The action and governed subject identities only.
    """
    return {key: intent[key] for key in _KEY_FIELDS}


def retry_key(intent: dict[str, Any], effect: str, actor_id: str, authority_grant_id: str, payload: dict) -> str:
    """Return the route's deterministic retry key for one effect.

    This must equal the key ``SpecCoordinator._submit_effect`` derives for this action,
    which it computes over ``key_intent``. The public
    positive path binds the two: every effect it locates must satisfy this key.

    Args:
        intent: Validated semantic close_task intent.
        effect: The effect name.
        actor_id: Actor recorded on the command.
        authority_grant_id: Authority grant recorded on the command.
        payload: Exact command payload.

    Returns:
        The idempotency and correlation key the route submits the effect under.
    """
    return "spec:" + sha256_hex(canonical_bytes([key_intent(intent), effect, actor_id, authority_grant_id, payload]))


def _issued_by_route(event: dict, intent: dict[str, Any], effect: str) -> bool:
    key = retry_key(intent, effect, event["actor_id"], event["authority_grant_id"], event["payload"])
    return event.get("idempotency_key") == key and event.get("command_id") == _stable_command_id(key)


def _prefix(events: list[dict], position: int) -> list[dict]:
    return [event for event in events if event["global_position"] < position]


def _streams(
    events: list[dict],
    schemas: SchemaRegistry,
    *,
    before_position: int | None = None,
    authority_state_validator: _Validator = None,
) -> dict[str, Any]:
    selected = events if before_position is None else _prefix(events, before_position)
    return replay(tuple(selected), schema_registry=schemas, authority_state_validator=authority_state_validator)[
        "streams"
    ]


def _subject_hash(
    events: list[dict],
    task_id: str,
    schemas: SchemaRegistry,
    *,
    before_position: int | None = None,
    authority_state_validator: _Validator = None,
) -> str:
    task = _streams(
        events, schemas, before_position=before_position, authority_state_validator=authority_state_validator
    ).get(task_id)
    if not isinstance(task, dict):
        raise ArsError(f"close_task requires an existing Task: {task_id}")
    return sha256_hex(canonical_bytes(task))


def _reviewed_subject_hash(
    ids: dict[str, str],
    events: list[dict],
    schemas: SchemaRegistry,
    request: dict | None,
    authority_state_validator: _Validator = None,
) -> str:
    """Return the exact Task hash this action's review is, or will be, raised against."""
    # CommandService validates RequestReview subject hashes against current state, and
    # a Task at review_pending can still be validly paused, blocked or resumed before
    # the request. Once a request exists, its position fixes the reviewed subject.
    before = None if request is None else request["global_position"]
    return _subject_hash(
        events, ids["task_id"], schemas, before_position=before, authority_state_validator=authority_state_validator
    )


def _artefact_content_hash(events: list[dict], artefact_id: str) -> str:
    matches = [
        event for event in events if event["event_type"] == "ArtefactRegistered" and event["stream_id"] == artefact_id
    ]
    if len(matches) != 1:
        raise IntegrityError(f"close_task cannot bind an exact candidate artefact hash: {artefact_id}")
    return matches[0]["payload"]["manifest"]["content_sha256"]


def _producing_actors(ids: dict[str, str], events: list[dict]) -> frozenset[str]:
    """Return every actor that produced the bound Attempt.

    The submitter of a Task is not necessarily its producer. Attempt lifecycle
    commands require the lease holder, and lease admission binds the holder to the
    claiming actor, so the producers are the Attempt stream's actors together with the
    holder of any lease bound to that Attempt.
    """
    actors = {event["actor_id"] for event in events if event["stream_id"] == ids["attempt_id"]}
    for event in events:
        payload = event.get("payload")
        if (
            isinstance(payload, dict)
            and payload.get("attempt_id") == ids["attempt_id"]
            and payload.get("holder_actor_id")
        ):
            actors.add(str(payload["holder_actor_id"]))
    return frozenset(actors)


def _locate(effect: str, ids: dict[str, str], events: list[dict], after_position: int) -> dict | None:
    """Find the first event of this effect's type on this action's stream."""
    event_type = _EFFECT_EVENTS[effect]
    stream_id = ids["task_id"] if effect in _TASK_STREAM_EFFECTS else ids["review_id"]
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
        return event
    return None


def _assigned_reviewer(ids: dict[str, str], events: list[dict]) -> str:
    assigned = _locate("AssignReview", ids, events, 0)
    if assigned is None:
        raise IntegrityError("close_task review has no assigned reviewer")
    return str(assigned["payload"]["reviewer_actor_id"])


def _check_evidence(effect: str, evidence: dict[str, Any] | None) -> dict[str, Any]:
    required = _REQUIRED_EVIDENCE.get(effect)
    if required is None:
        if evidence is not None:
            raise IntegrityError(f"close_task {effect} takes no independent evidence")
        return {}
    if not isinstance(evidence, dict):
        raise ArsError(f"{effect} requires independent evidence in --input")
    if set(evidence) != set(required):
        raise IntegrityError(f"close_task {effect} evidence fields are not exact")
    return dict(evidence)


def _check_actor_relation(
    effect: str, ids: dict[str, str], events: list[dict], *, actor_id: str, reviewer_actor_id: str | None = None
) -> None:
    """Refuse a reviewer related to the reviewed work.

    These restate boundaries CommandService also enforces for the requester and the
    assignment, so the route refuses before submitting. test_spec_task.py exercises
    the inherited refusals directly, so neither layer is trusted on the other's behalf.
    """
    if effect not in {"AssignReview", "StartReview", "RecordReviewVerdict"}:
        return
    producers = set(_producing_actors(ids, events))
    submitted = _locate("SubmitForReview", ids, events, 0)
    if submitted is not None:
        producers.add(submitted["actor_id"])
    if effect == "AssignReview":
        if reviewer_actor_id in producers:
            raise IntegrityError("close_task cannot assign the producing actor as its own reviewer")
        return
    if actor_id in producers:
        raise IntegrityError(f"close_task {effect} requires an actor independent of the producer")
    if actor_id != _assigned_reviewer(ids, events):
        raise IntegrityError(f"close_task {effect} requires the assigned reviewer")


def _derived(
    effect: str,
    ids: dict[str, str],
    events: list[dict],
    *,
    actor_id: str,
    schemas: SchemaRegistry,
    authority_state_validator: _Validator = None,
) -> dict[str, Any]:
    """Return the fields this route derives for one effect from the evidence before it.

    This is the single source for both building a command and verifying a located
    one, so a derived field cannot be generated without also being checked.
    """
    streams = _streams(events, schemas, authority_state_validator=authority_state_validator)
    if effect == "SubmitForReview":
        return _submit_payload(ids, streams, events)
    if effect == "AcceptTask":
        return _accept_payload(ids, streams, _locate("SubmitForReview", ids, events, 0))
    if effect == "RequestReview":
        task = streams.get(ids["task_id"])
        status = task.get("status") if isinstance(task, dict) else None
        if status != _REVIEW_PENDING:
            # Admission does not require review_pending here. A request bound to a
            # paused Task can be reviewed but never accepted, and resuming changes the
            # Task hash the review is bound to.
            raise IntegrityError(f"close_task can request review only while the Task is review_pending, not {status}")
        return {
            "new_review_id": ids["review_id"],
            "subject_ids": [ids["task_id"]],
            "subject_hashes": [sha256_hex(canonical_bytes(task))],
            "required_independence_grade": _INDEPENDENCE_GRADE,
            "visibility_policy": _VISIBILITY_POLICY,
            "satisfaction_authority": _SATISFACTION_AUTHORITY,
            "allowed_verdicts": list(_ALLOWED_VERDICTS),
        }
    request = _locate("RequestReview", ids, events, 0)
    if request is None:
        raise IntegrityError("close_task has no review request to answer")
    reviewed = _reviewed_subject_hash(ids, events, schemas, request, authority_state_validator)
    if effect == "AssignReview":
        return {"review_id": ids["review_id"], "computed_independence_grade": _INDEPENDENCE_GRADE}
    if effect == "StartReview":
        return {
            "review_id": ids["review_id"],
            "unchanged_subject_sha256": reviewed,
            "visibility_policy": _VISIBILITY_POLICY,
        }
    if effect == "RecordReviewVerdict":
        return {
            "review_id": ids["review_id"],
            "verdict": _APPROVE_VERDICT,
            "findings": [],
            "reviewer_actor_id": actor_id,
            "limitations": [],
            "conditions": [],
            "unchanged_subject_sha256": reviewed,
            "producing_attempt_id": ids["attempt_id"],
            "computed_independence_grade": _INDEPENDENCE_GRADE,
        }
    if effect == "SatisfyReview":
        review = streams.get(ids["review_id"])
        prior = review.get("status") if isinstance(review, dict) else None
        if prior != _VERDICT_RECORDED:
            raise IntegrityError(f"close_task cannot satisfy a review in state {prior}")
        return {"review_id": ids["review_id"], "prior_review_state": _VERDICT_RECORDED}
    raise ArsError(f"unsupported close_task effect: {effect}")


def evaluate(
    intent: dict[str, Any],
    events: list[dict],
    *,
    schemas: SchemaRegistry,
    authority_state_validator: _Validator = None,
) -> dict[str, Any]:
    """Derive close_task state purely from route-issued ledger evidence.

    Args:
        intent: Validated semantic close_task intent.
        events: Full ordered ledger event list.
        schemas: Runtime schema registry used for projection.
        authority_state_validator: Inherited validator for authority projections.

    Returns:
        One state record with the ordered completed effects and the next effect.

    Raises:
        ConflictError: If evidence this route did not issue sits on the action's
            streams, so no remaining effect can be trusted or can succeed.
        IntegrityError: If route-keyed evidence does not carry the derived payload,
            relates the reviewer to the reviewed work, or names absent subjects.
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
        _validate_located(intent, ids, located, events, schemas, authority_state_validator)
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


def _validate_located(
    intent: dict[str, Any],
    ids: dict[str, str],
    located: list[dict],
    events: list[dict],
    schemas: SchemaRegistry,
    authority_state_validator: _Validator,
) -> None:
    """Refuse located evidence this route did not issue or would not have derived."""
    by_effect = dict(zip(EFFECTS, located, strict=False))

    # Layer 1, identity: only the route's own commands for this intent count.
    for effect, event in by_effect.items():
        if not _issued_by_route(event, intent, effect):
            raise ConflictError(f"close_task {event['event_type']} was not issued by this route")

    # Layer 2, content: a route-keyed event must carry exactly the fields the route
    # derives at its position. The key covers whatever payload was submitted, so
    # identity alone would accept a correctly keyed but altered command.
    for effect, event in by_effect.items():
        prefix = _prefix(events, event["global_position"])
        derived = _derived(
            effect,
            ids,
            prefix,
            actor_id=event["actor_id"],
            schemas=schemas,
            authority_state_validator=authority_state_validator,
        )
        payload = event["payload"]
        expected_fields = set(derived) | set(_REQUIRED_EVIDENCE.get(effect, frozenset()))
        if set(payload) != expected_fields or any(payload.get(key) != value for key, value in derived.items()):
            raise IntegrityError(f"close_task {effect} does not carry the payload this route derives")
        _check_actor_relation(
            effect,
            ids,
            prefix,
            actor_id=event["actor_id"],
            reviewer_actor_id=payload.get("reviewer_actor_id") if effect == "AssignReview" else None,
        )

    # Layer 3, exclusivity: nothing else may touch the Review stream, or the Task
    # stream once the review is requested. A withdrawal, a foreign verdict, a pause
    # after the request or a reopening all leave remaining effects untrustworthy or
    # unable to succeed.
    issued = {event["event_id"] for event in located}
    for event in events:
        if event["stream_id"] == ids["review_id"] and event["event_id"] not in issued:
            raise ConflictError(
                f"close_task found {event['event_type']} on its Review stream that this route did not issue"
            )
    request = by_effect.get("RequestReview")
    if request is not None:
        for event in events:
            if (
                event["stream_id"] == ids["task_id"]
                and event["global_position"] > request["global_position"]
                and event["event_id"] not in issued
            ):
                raise ConflictError(
                    f"close_task found {event['event_type']} on its Task stream after the review request"
                    " that this route did not issue"
                )


def effect_command(
    effect: str,
    intent: dict[str, Any],
    events: list[dict],
    *,
    actor_id: str,
    evidence: dict[str, Any] | None,
    schemas: SchemaRegistry,
    authority_state_validator: _Validator = None,
) -> tuple[str, dict[str, Any]]:
    """Build the exact target stream and payload for one close_task effect.

    Args:
        effect: The next uncompleted effect name.
        intent: Validated semantic close_task intent.
        events: Full ordered ledger event list.
        actor_id: Actor recorded on this individual command.
        evidence: Independent evidence supplied for effects that require it.
        schemas: Runtime schema registry used for projection.
        authority_state_validator: Inherited validator for authority projections.

    Returns:
        The target stream identity and the exact command payload.

    Raises:
        ArsError: If a required evidence document is absent.
        IntegrityError: If evidence fields are inexact, the actor relation is not
            permitted, or the governed state cannot take this effect.
    """
    ids = subject_ids(intent)
    supplied = _check_evidence(effect, evidence)
    _check_actor_relation(effect, ids, events, actor_id=actor_id, reviewer_actor_id=supplied.get("reviewer_actor_id"))
    derived = _derived(
        effect, ids, events, actor_id=actor_id, schemas=schemas, authority_state_validator=authority_state_validator
    )
    target = ids["task_id"] if effect in _TASK_STREAM_EFFECTS else ids["review_id"]
    return target, {**derived, **supplied}


def exact_retry(
    intent: dict[str, Any],
    state: dict[str, Any],
    events: list[dict],
    *,
    actor_id: str,
    authority_grant_id: str,
    evidence: dict[str, Any] | None,
    schemas: SchemaRegistry,
    authority_state_validator: _Validator = None,
) -> tuple[str, str, dict[str, Any], int] | None:
    """Recognise a repeated public invocation of the most recent committed effect.

    A caller who loses the response to an effect repeats the identical invocation.
    By then the state has moved on, so deriving the next effect would build a
    different command with the wrong evidence or grant. Instead, rebuild what this
    invocation would have submitted for the last committed effect, as of that effect's
    own position; if its retry key matches the recorded one, the invocation is that
    retry. Adjacent effects never share actor, grant and evidence shape, so a new
    invocation of the next effect cannot collide with the previous effect's key.

    Args:
        intent: Validated semantic close_task intent.
        state: Current evaluated state for this action.
        events: Full ordered ledger event list.
        actor_id: Actor of the repeated invocation.
        authority_grant_id: Authority grant of the repeated invocation.
        evidence: Evidence of the repeated invocation.
        schemas: Runtime schema registry used for projection.
        authority_state_validator: Inherited validator for authority projections.

    Returns:
        The effect, target stream, payload and original expected stream version to
        resubmit, or None when this invocation is not a retry of the last effect.
    """
    if not state["effects"]:
        return None
    recorded = state["effects"][-1]
    event = next((candidate for candidate in events if candidate["event_id"] == recorded["event_id"]), None)
    if event is None:
        return None
    effect = EFFECTS[len(state["effects"]) - 1]
    try:
        supplied = _check_evidence(effect, evidence)
        derived = _derived(
            effect,
            subject_ids(intent),
            _prefix(events, event["global_position"]),
            actor_id=actor_id,
            schemas=schemas,
            authority_state_validator=authority_state_validator,
        )
    except ArsError:
        # This invocation cannot have produced that effect, so it is not its retry.
        return None
    payload = {**derived, **supplied}
    if retry_key(intent, effect, actor_id, authority_grant_id, payload) != event.get("idempotency_key"):
        return None
    return effect, event["stream_id"], payload, int(event["stream_version"]) - 1


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
        # Built from the evidence before the submission, so a later or fabricated
        # registration can never back a claimed candidate hash.
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
    # Acceptance admission compares criterion SETS, so an empty set passes, but
    # reduce_task rejects an empty satisfied set. Never build an event whose own
    # reducer refuses it; that would leave the ledger unreplayable.
    if not tuple(task.get("definition", {}).get("acceptance_criteria", ())):
        raise IntegrityError("close_task cannot accept a Task with no acceptance criteria")
    # The governed contract supports selecting a bounded subset of the submitted
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
