"""06s Phase 4a-1 (P-058): W11 bootstrap and the SPEC-01 Assay request on the public SPEC route.

Each action composes existing W11 Discovery rows. Discovery admission keeps every
command's own actor, authority grant and transaction; nothing here adjudicates
authority. The route adds only the relations admission was measured to leave
unchecked (P-058 amendment), and refuses them before the first durable mutation:

- genesis is imported by the authority owner;
- the Assay-bar review requester is not an author of the committed content;
- the Assay requester is neither the prospective producer nor the owner.

Only evidence this route issued counts. A located effect must carry the route's own
retry key for this intent and the command payload the route derives at that ledger
position, and nothing else may sit on a stream the action owns.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.discovery.assay_authority import assay_reconstruction_sha256
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.routes import DISCOVERY_ROW_ROUTES
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.methods.registration import _stable_command_id
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry

GENESIS = "bootstrap_genesis"
BAR = "bootstrap_assay_authority"
REQUEST = "request_spec_01"
INTENT_SCHEMA_ID = "ars://portfolio/spec-assay-intent"
ASSAY_RUBRIC_PATH = ".research-system/contracts/wp6-6/assay-rubric-content-v1.json"
ASSAY_SCOPE_PATH = ".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json"
_ROUTE_IDENTITY = "SPEC-GATE6-RUN-V1"
# Known limit (P-058): inherited OR-106 admission reconstructs the review context with this
# fixed literal (runtime.py:1130), so the bar review binds no real reviewer context.
_ASSAY_BAR_REVIEW_CONTEXT_ID = "ctx_019fed25-b33e-7740-b280-000000000105"

ROWS = {
    GENESIS: ("OR-140",),
    BAR: ("OR-101", "OR-102", "OR-103", "OR-104", "OR-105", "OR-106", "OR-107", "OR-108"),
    REQUEST: ("OR-003",),
}
ACTIONS = {action: tuple(DISCOVERY_ROW_ROUTES[row].command_type for row in rows) for action, rows in ROWS.items()}
# Streams wholly owned by an action; the Assay stream also carries later SPEC-01 actions.
_EXCLUSIVE_ACTIONS = frozenset({GENESIS, BAR})

_Validator = Callable[[dict[str, Any]], None] | None


@dataclass(frozen=True)
class AssayContext:
    """Stores and readers the Assay route needs, fixed for one invocation.

    Attributes:
        project_id: Bound project identity.
        schemas: Runtime schema registry.
        validator: Inherited authority-state validator for replay.
        repository_root: Governed repository root holding the committed Assay authority files.
    """

    project_id: str
    schemas: SchemaRegistry
    validator: _Validator
    repository_root: Path


def _stable(prefix: str, *parts: str) -> str:
    return prefix + _stable_command_id(canonical_bytes(list(parts)).decode())[3:]


def subject_ids(project_id: str, intent: dict[str, Any]) -> dict[str, str]:
    """Return the governed identities the route derives for an intent.

    Args:
        project_id: Bound project identity.
        intent: Validated Assay route intent.

    Returns:
        The review and Decision identities of the Assay bar, or the Candidate and its
        Assay identity for a request; genesis has none.
    """
    action = intent["action"]
    if action == BAR:
        return {
            "review_id": _stable("rev", project_id, BAR, "review"),
            "decision_id": _stable("dec", project_id, BAR, "decision"),
        }
    if action == REQUEST:
        candidate_id = intent["candidate_id"]
        return {"candidate_id": candidate_id, "assay_id": _stable("asy", project_id, candidate_id, REQUEST)}
    return {}


def producer_ref(producer_actor_id: str) -> dict[str, Any]:
    """Return the prospective producer relation the route binds for an actor.

    Known limit (P-058): W11 §4.3 relates actor, profile, context and grant; the
    inherited runtime models one record reference whose hash it never checks. The route
    derives that hash from the actor and route identity, so the relation is actor-only.

    Args:
        producer_actor_id: The named Assay producer.

    Returns:
        The exact ``{id, record_revision, content_hash}`` reference.
    """
    relation = {"relation": "spec-assay-producer", "route_id": _ROUTE_IDENTITY, "actor_id": producer_actor_id}
    return {"id": producer_actor_id, "record_revision": 1, "content_hash": sha256_hex(canonical_bytes(relation))}


def key_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Return the part of an intent that identifies its effects.

    Free text is excluded. The Assay bar's reviewer and producer enter each effect's
    payload instead, so naming different ones conflicts rather than re-deriving.

    Args:
        intent: Validated Assay route intent.

    Returns:
        The action and, for a request, its Candidate.
    """
    key = {"action": intent["action"]}
    if intent["action"] == REQUEST:
        key["candidate_id"] = intent["candidate_id"]
    return key


def retry_key(intent: dict[str, Any], effect: str, actor_id: str, grant_id: str, payload: dict) -> str:
    """Return the retry key ``SpecCoordinator._submit_effect`` derives for one effect.

    Args:
        intent: Assay route intent (only its key part is used).
        effect: Command type of the effect.
        actor_id: Actor recorded on the command.
        grant_id: Authority grant recorded on the command.
        payload: Exact submitted payload.

    Returns:
        The idempotency key the route submits the effect under.
    """
    return "spec:" + sha256_hex(canonical_bytes([key_intent(intent), effect, actor_id, grant_id, payload]))


def _content(ctx: AssayContext, relative: str) -> dict[str, Any]:
    try:
        return json.loads((ctx.repository_root / relative).read_bytes())
    except (OSError, ValueError) as exc:
        raise IntegrityError(f"{BAR} requires the committed Assay authority file: {relative}") from exc


def _owner(events: list[dict], ctx: AssayContext) -> Any:
    state = replay(tuple(events), schema_registry=ctx.schemas, authority_state_validator=ctx.validator)
    return state.get("authority_owner_actor_id")


def _projection(events: list[dict], ctx: AssayContext) -> dict[str, Any]:
    return replay_discovery(tuple(events), schemas=ctx.schemas, authority_state_validator=ctx.validator)


def _prefix(events: list[dict], position: int) -> list[dict]:
    return [event for event in events if event["global_position"] < position]


def _stream(row: str, ids: dict[str, str], ctx: AssayContext) -> str:
    if row == "OR-140":
        return CATALOGUE_STREAM_ID
    if row in {"OR-101", "OR-103"}:
        return _content(ctx, ASSAY_RUBRIC_PATH)["record_id"]
    if row in {"OR-102", "OR-104"}:
        return _content(ctx, ASSAY_SCOPE_PATH)["record_id"]
    if row in {"OR-105", "OR-106"}:
        return ids["review_id"]
    if row in {"OR-107", "OR-108"}:
        return ids["decision_id"]
    return ids["assay_id"]


def _payload(row: str, intent: dict[str, Any], ids: dict[str, str], events: list[dict], ctx: AssayContext) -> dict:
    """Return the exact command payload for one row from the ledger before it.

    This is the single source for building a command, verifying a located one and
    recognising a retry, so no derived field can be generated without being checked.
    """
    if row == "OR-140":
        return deepcopy(dict(ACCEPTED))
    if row in {"OR-101", "OR-102"}:
        path = ASSAY_RUBRIC_PATH if row == "OR-101" else ASSAY_SCOPE_PATH
        return {
            "row_id": row,
            "authority_kind": "assay_bar",
            "content": _content(ctx, path),
            "authority_file_path": path,
        }
    if row in {"OR-103", "OR-104", "OR-107"}:
        payload = {"row_id": row, "authority_kind": "assay_bar"}
        return {**payload, "proposed_decision": "accept"} if row == "OR-107" else payload
    if row == "OR-105":
        return {
            "row_id": row,
            "authority_kind": "assay_bar",
            "reviewer_actor_id": intent["reviewer_actor_id"],
            "prospective_producer_ref": producer_ref(intent["producer_actor_id"]),
        }
    if row == "OR-106":
        bar = _projection(events, ctx)["assay_bar_authority"]
        if bar.get("status") != "review_requested":
            raise IntegrityError(f"{BAR} can record its review only once the review is requested")
        return {
            "row_id": row,
            "authority_kind": "assay_bar",
            "verdict": "approve",
            "unchanged_subject_sha256": bar["subject_sha256"],
            "reconstruction_sha256": assay_reconstruction_sha256(bar, _ASSAY_BAR_REVIEW_CONTEXT_ID),
        }
    if row == "OR-108":
        return {"row_id": row, "authority_kind": "assay_bar", "decision_id": ids["decision_id"], "decision": "accept"}
    projection = _projection(events, ctx)
    candidate = projection["candidates"].get(ids["candidate_id"])
    bar = projection["assay_bar_authority"]
    if not isinstance(candidate, dict):
        raise IntegrityError(f"{REQUEST} names no registered Candidate: {ids['candidate_id']}")
    if bar.get("status") != "accepted":
        raise IntegrityError(f"{REQUEST} requires an accepted Assay bar")
    return {
        "row_id": "OR-003",
        "candidate_id": ids["candidate_id"],
        "assay_id": ids["assay_id"],
        "candidate_revision": candidate["revision"],
        "candidate_sha256": candidate["content_sha256"],
        "assay_bar_acceptance_sha256": bar["acceptance_sha256"],
        "producer_relation_sha256": bar["producer_relation_sha256"],
    }


def _check_relation(row: str, events: list[dict], ctx: AssayContext, *, actor_id: str) -> None:
    """Refuse the role collapses inherited admission was measured to accept (P-058 amendment)."""
    if row == "OR-140" and actor_id != _owner(events, ctx):
        raise IntegrityError(f"{GENESIS} requires the authority owner as its actor")
    if row == "OR-105":
        authors = {_content(ctx, path).get("created_by_actor_id") for path in (ASSAY_RUBRIC_PATH, ASSAY_SCOPE_PATH)}
        if actor_id in authors:
            raise IntegrityError(f"{BAR} review requester must not be a content author")
    if row == "OR-003":
        bar = _projection(events, ctx)["assay_bar_authority"]
        producer = (bar.get("prospective_producer_ref") or {}).get("id")
        if actor_id in {producer, _owner(events, ctx)}:
            raise IntegrityError(f"{REQUEST} Assay requester must be neither the prospective producer nor the owner")


def _issued(event: dict, intent: dict[str, Any], effect: str, payload: dict) -> bool:
    key = retry_key(intent, effect, event["actor_id"], event["authority_grant_id"], payload)
    return (
        event.get("idempotency_key") == key
        and event.get("command_id") == _stable_command_id(key)
        and event.get("command_payload_hash") == sha256_hex(canonical_bytes(payload))
    )


def _located(intent: dict[str, Any], events: list[dict], ctx: AssayContext) -> list[tuple[str, list[dict]]]:
    """Return each row's first transaction on its stream, in route order, until one is absent."""
    ids = subject_ids(ctx.project_id, intent)
    found: list[tuple[str, list[dict]]] = []
    after = 0
    for row in ROWS[intent["action"]]:
        stream = _stream(row, ids, ctx)
        first = next((e for e in events if e["stream_id"] == stream and e["global_position"] > after), None)
        if first is None:
            break
        transaction = [e for e in events if e["command_id"] == first["command_id"]]
        found.append((row, transaction))
        after = max(e["global_position"] for e in transaction)
    return found


def evaluate(intent: dict[str, Any], events: list[dict], ctx: AssayContext) -> dict[str, Any]:
    """Derive one Assay route action's state purely from route-issued ledger evidence.

    Args:
        intent: Validated Assay route intent.
        events: Full ordered ledger event list.
        ctx: Route context.

    Returns:
        A state record: not_started, prepared or completed, with its effects.

    Raises:
        ConflictError: If evidence this route did not issue sits on the action's streams.
        IntegrityError: If route-keyed evidence breaks a relation the route enforces.
    """
    action = intent["action"]
    ids = subject_ids(ctx.project_id, intent)
    located = _located(intent, events, ctx)
    for row, transaction in located:
        first = transaction[0]
        effect = DISCOVERY_ROW_ROUTES[row].command_type
        prefix = _prefix(events, first["global_position"])
        if not _issued(first, intent, effect, _payload(row, intent, ids, prefix, ctx)):
            raise ConflictError(f"{action} found {first['event_type']} on its stream that this route did not issue")
        _check_relation(row, prefix, ctx, actor_id=first["actor_id"])
    if action in _EXCLUSIVE_ACTIONS and len(located) == len(ROWS[action]):
        owned = {_stream(row, ids, ctx) for row in ROWS[action]}
        issued = {event["event_id"] for _, transaction in located for event in transaction}
        for event in events:
            if event["stream_id"] in owned and event["event_id"] not in issued:
                raise ConflictError(f"{action} found {event['event_type']} on its stream that this route did not issue")
    if action == REQUEST and not located:
        candidate = _projection(events, ctx)["candidates"].get(ids["candidate_id"])
        if isinstance(candidate, dict) and candidate.get("assay_id") not in {None, ids["assay_id"]}:
            raise ConflictError(f"{REQUEST} Candidate already has an Assay this route did not issue")
    effects = ACTIONS[action]
    return {
        "action": action,
        "state": "completed" if len(located) == len(effects) else "prepared" if located else "not_started",
        **ids,
        "next_effect": effects[len(located)] if len(located) < len(effects) else None,
        "effects": [
            {
                key: transaction[0][key]
                for key in ("event_id", "event_hash", "command_id", "actor_id", "authority_grant_id")
            }
            for _, transaction in located
        ],
    }


def next_command(
    intent: dict[str, Any], events: list[dict], ctx: AssayContext, *, actor_id: str
) -> tuple[str, str, dict[str, Any]]:
    """Build the next effect for an action, refusing before any durable mutation.

    Args:
        intent: Validated Assay route intent.
        events: Full ordered ledger event list from one snapshot.
        ctx: Route context.
        actor_id: Actor of this invocation.

    Returns:
        The command type, target stream and exact payload.

    Raises:
        IntegrityError: If the action is complete or this actor may not take the next effect.
    """
    state = evaluate(intent, events, ctx)
    if state["next_effect"] is None:
        raise IntegrityError(f"{intent['action']} is already completed")
    row = ROWS[intent["action"]][len(state["effects"])]
    ids = subject_ids(ctx.project_id, intent)
    payload = _payload(row, intent, ids, events, ctx)
    _check_relation(row, events, ctx, actor_id=actor_id)
    return state["next_effect"], _stream(row, ids, ctx), payload


def exact_retry(
    intent: dict[str, Any], events: list[dict], ctx: AssayContext, *, actor_id: str, grant_id: str
) -> dict | None:
    """Recognise a repeated invocation of an effect that is already committed.

    Every row's payload differs, so an invocation can reproduce only its own effect's
    retry key. A recognised retry is answered from its receipt and never resubmitted.

    Args:
        intent: Validated Assay route intent.
        events: Full ordered ledger event list.
        ctx: Route context.
        actor_id: Actor of the repeated invocation.
        grant_id: Authority grant of the repeated invocation.

    Returns:
        The committed event this invocation repeats, or None.
    """
    ids = subject_ids(ctx.project_id, intent)
    for row, transaction in _located(intent, events, ctx):
        first = transaction[0]
        try:
            payload = _payload(row, intent, ids, _prefix(events, first["global_position"]), ctx)
        except ArsError:
            continue
        effect = DISCOVERY_ROW_ROUTES[row].command_type
        if retry_key(intent, effect, actor_id, grant_id, payload) == first.get("idempotency_key"):
            return first
    return None


def enumerated_intents(events: list[dict], ctx: AssayContext) -> list[dict[str, Any]]:
    """Recover every Assay route intent whose first effect this route issued.

    W11 history the route did not issue is not a route subject, so it is not listed;
    an explicit status query for that subject still reports the conflict.

    Args:
        events: Full ordered ledger event list.
        ctx: Route context.

    Returns:
        One semantic intent per route subject, genesis and bar first.
    """
    projection = _projection(events, ctx)
    bar = projection["assay_bar_authority"]
    candidates: list[dict[str, Any]] = [{"action": GENESIS, "reason": "recorded route genesis"}]
    # A bar subject exists only once its content is registered. Until then the listing
    # must not read the committed authority files, which a bound store need not carry.
    if isinstance((bar.get("contents") or {}).get("rubric"), dict):
        candidates.append(
            {
                "action": BAR,
                "reason": "recorded route Assay bar",
                "reviewer_actor_id": bar.get("reviewer_actor_id"),
                "producer_actor_id": (bar.get("prospective_producer_ref") or {}).get("id"),
            }
        )
    for assay in projection["assays"].values():
        candidate_id = assay.get("candidate_id")
        if isinstance(candidate_id, str) and assay.get("assay_id") == subject_ids(
            ctx.project_id, {"action": REQUEST, "candidate_id": candidate_id}
        ).get("assay_id"):
            candidates.append(
                {"action": REQUEST, "reason": "recorded route Assay request", "candidate_id": candidate_id}
            )
    intents = []
    for intent in candidates:
        try:
            located = _located(intent, events, ctx)
            if not located:
                continue
            row, transaction = located[0]
            prefix = _prefix(events, transaction[0]["global_position"])
            payload = _payload(row, intent, subject_ids(ctx.project_id, intent), prefix, ctx)
        except ArsError:
            # Report the subject rather than hide it or deny the whole listing: evaluating
            # it lists the error as unreadable.
            intents.append(intent)
            continue
        if _issued(transaction[0], intent, DISCOVERY_ROW_ROUTES[row].command_type, payload):
            intents.append(intent)
    return intents
