"""06s Phase 4a (P-058): W11 bootstrap and the SPEC-01 Assay sequence on the public SPEC route.

Each action composes existing W11 Discovery rows; the two operator records are registered
artefacts. Admission keeps every command's own actor, authority grant and transaction;
nothing here adjudicates authority. The route adds only the relations admission was
measured to leave unchecked (P-058 amendment), and refuses them before the first durable
mutation:

- genesis is imported by the authority owner;
- the Assay-bar review requester is not an author of the committed content;
- the Assay requester is neither the prospective producer nor the owner;
- the Assay producer's own invocation carries the operator return it scores;
- the outcome-review requester is neither the producer nor the owner;
- the outcome reviewer is not the owner;
- the promotion proposer is not the producer, the reviewer or the owner;
- the selected option comes from the owner's own invocation;
- PROMOTE is neither proposed nor selected while the Assay's bar has an axis the
  inherited scorecard rule does not evaluate, or while the return lists unresolved findings.

Only evidence this route issued counts. A located effect must carry the route's own
retry key for this intent and the command payload the route derives at that ledger
position, and nothing else may sit on a stream the action owns.

The operator brief package and the operator return take their operational provenance
from the ledger (P-058, 2026-09-15): the one Task whose definition names the Candidate
and no other registered Candidate, still at the revision its Attempt was dispatched on,
and that Attempt while it is running, whose own start record supplies the manifests'
code and environment identities. The scorecard is derived from whichever Assay bar is
accepted; the operator supplies only each rubric axis's value, rationale and unmet
condition codes. Known limit: the committed bar is W11 fixture content, which Phase 5
prep replaces.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.discovery.assay_authority import assay_reconstruction_sha256
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.routes import DISCOVERY_ROW_ROUTES
from research_system.discovery.rules import (
    _aggregate_content_hash,
    _assay_scorecard_matches,
    _axis_set_hash,
    _record_ref,
    _review_ref,
)
from research_system.discovery.spec_result import _BINDING_EVENTS, _event_ref
from research_system.discovery.spec_source import registration_ref
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.methods.registration import _stable_command_id
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry

GENESIS = "bootstrap_genesis"
BAR = "bootstrap_assay_authority"
REQUEST = "request_spec_01"
PREPARE = "prepare_spec_01"
RETURN = "return_spec_01_complete"
REVIEW = "review_spec_01_complete"
DECIDE = "decide_spec_01"
INTENT_SCHEMA_ID = "ars://portfolio/spec-assay-intent"
BRIEF_SCHEMA_ID = "ars://portfolio/spec-operator-brief-package"
RETURN_SCHEMA_ID = "ars://portfolio/spec-operator-return"
BRIEF_KIND = "spec_operator_brief_document"
RETURN_KIND = "spec_operator_return_document"
BRIEF_TYPE = "spec_operator_brief_package"
RETURN_TYPE = "spec_operator_return"
ASSAY_RUBRIC_PATH = ".research-system/contracts/wp6-6/assay-rubric-content-v1.json"
ASSAY_SCOPE_PATH = ".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json"
ROUTE_PACKAGE_PATH = ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json"
_BRIEF_ALIAS = "SPEC-01"
_ROUTE_IDENTITY = "SPEC-GATE6-RUN-V1"
# Known limit (P-058): inherited OR-106 admission reconstructs the review context with this
# fixed literal (runtime.py:1130), so the bar review binds no real reviewer context.
_ASSAY_BAR_REVIEW_CONTEXT_ID = "ctx_019fed25-b33e-7740-b280-000000000105"
# Route-fixed outcome-review and decision policy. Times derive from recorded events.
_OUTCOME_REVIEW_GRADE = "independent"
_REVIEW_WINDOW = timedelta(days=30)
_GATE = "assay_to_spike"
_NEXT_STATE = {"PROMOTE": "spike_planning_authorized", "PARK": "parked", "KILL": "killed"}
_CONSEQUENCES = {"PROMOTE": "authorize Spike planning", "PARK": "park the Candidate", "KILL": "kill the Candidate"}

# The operator records are artefact registrations, not W11 rows.
_BRIEF, _RETURN = "AR:spec_01_operator_brief", "AR:spec_01_operator_return"
_ARTEFACT_ROWS = frozenset({_BRIEF, _RETURN})
ROWS = {
    GENESIS: ("OR-140",),
    BAR: ("OR-101", "OR-102", "OR-103", "OR-104", "OR-105", "OR-106", "OR-107", "OR-108"),
    REQUEST: ("OR-003",),
    PREPARE: (_BRIEF,),
    RETURN: (_RETURN, "OR-004"),
    REVIEW: ("OR-034", "OR-006"),
    DECIDE: ("OR-012", "OR-013"),
}


def _command_type(row: str) -> str:
    return "RegisterArtefact" if row in _ARTEFACT_ROWS else DISCOVERY_ROW_ROUTES[row].command_type


ACTIONS = {action: tuple(_command_type(row) for row in rows) for action, rows in ROWS.items()}
# The rows whose streams an action wholly owns. The Assay stream also carries later SPEC-01 actions.
_OWNED_ROWS = {
    GENESIS: ROWS[GENESIS],
    BAR: ROWS[BAR],
    PREPARE: (_BRIEF,),
    RETURN: (_RETURN,),
    REVIEW: ("OR-034",),
    DECIDE: ("OR-012",),
}
_SPEC_01_ACTIONS = frozenset({REQUEST, PREPARE, RETURN, REVIEW, DECIDE})
_OPERATOR_RETURN = frozenset(
    {
        "axis_results",
        "prohibited_inferences",
        "review_requirements",
        "direct_sources",
        "findings",
        "validation",
        "unresolved_findings",
        "limitations",
    }
)
# The evidence each effect takes from its caller; every other field is derived.
_EVIDENCE = {
    _RETURN: _OPERATOR_RETURN,
    # Admission keeps registration owner-only, so the Assay producer's own invocation re-supplies the
    # return it scores (PR #291 review). Known limit: the fields the scorecard does not carry are
    # checked at that submission but not recorded in the OR-004 event.
    "OR-004": _OPERATOR_RETURN,
    "OR-006": frozenset(
        {
            "reviewer_profile",
            "reviewer_session",
            "reviewer_model_metadata",
            "context_manifest_id",
            "context_manifest_sha256",
            "trace_visibility_evidence_refs",
            "findings",
            "limitations",
        }
    ),
    "OR-013": frozenset({"selected_option", "revisit_triggers"}),
}
_AXIS_EVIDENCE = frozenset({"axis_id", "value", "rationale", "unmet_condition_codes"})

_Validator = Callable[[dict[str, Any]], None] | None


@dataclass(frozen=True)
class AssayContext:
    """Stores and readers the Assay route needs, fixed for one invocation.

    Attributes:
        project_id: Bound project identity.
        schemas: Runtime schema registry.
        validator: Inherited authority-state validator for replay.
        repository_root: Governed repository root holding the committed authority files.
        objects: Immutable object store holding the operator records.
        raw_prefix_sha256: Ledger raw-prefix digest at a global position.
    """

    project_id: str
    schemas: SchemaRegistry
    validator: _Validator
    repository_root: Path
    objects: Any
    raw_prefix_sha256: Callable[[int], str]


def _stable(prefix: str, *parts: str) -> str:
    return prefix + _stable_command_id(canonical_bytes(list(parts)).decode())[3:]


def subject_ids(project_id: str, intent: dict[str, Any]) -> dict[str, str]:
    """Return the governed identities the route derives for an intent.

    Args:
        project_id: Bound project identity.
        intent: Validated Assay route intent.

    Returns:
        The review and Decision identities of the Assay bar; the Candidate and its Assay
        for a request; and, for the later SPEC-01 actions, also the brief and return
        artefacts and the outcome review and Decision. Genesis has none.
    """
    action = intent["action"]
    if action == BAR:
        return {
            "review_id": _stable("rev", project_id, BAR, "review"),
            "decision_id": _stable("dec", project_id, BAR, "decision"),
        }
    if action not in _SPEC_01_ACTIONS:
        return {}
    candidate_id = intent["candidate_id"]
    ids = {"candidate_id": candidate_id, "assay_id": _stable("asy", project_id, candidate_id, REQUEST)}
    if action == REQUEST:
        return ids
    return {
        **ids,
        "brief_id": _stable("art", project_id, candidate_id, PREPARE),
        "return_id": _stable("art", project_id, candidate_id, RETURN),
        "review_id": _stable("rev", project_id, candidate_id, REVIEW),
        "decision_id": _stable("dec", project_id, candidate_id, DECIDE),
    }


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

    Free text is excluded. The Assay bar's reviewer and producer, and a decision's
    recommendation, enter each effect's payload instead, so naming different ones
    conflicts rather than re-deriving.

    Args:
        intent: Validated Assay route intent.

    Returns:
        The action and, for a SPEC-01 action, its Candidate.
    """
    key = {"action": intent["action"]}
    if intent["action"] in _SPEC_01_ACTIONS:
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


def _validate(schema_id: str, document: dict[str, Any], ctx: AssayContext) -> None:
    try:
        ctx.schemas.validate(schema_id, document, schema_version="1.0.0")
    except SchemaError as exc:
        raise IntegrityError(f"{schema_id} record is not schema-valid: {exc}") from exc


def _same_record(supplied: Any, registered: Any) -> bool:
    """Compare as canonical JSON bytes: Python equality treats ``1`` and ``true`` as equal (PR #291 known limit 17)."""
    try:
        return canonical_bytes(supplied) == canonical_bytes(registered)
    except (TypeError, ValueError):
        return False


def _strings(value: Any, label: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise IntegrityError(f"{label} must be a list of non-empty strings")


def _time(recorded_at: str, delta: timedelta = timedelta()) -> str:
    moment = datetime.fromisoformat(recorded_at.replace("Z", "+00:00")).astimezone(UTC) + delta
    return moment.isoformat().replace("+00:00", "Z")


def _one(events: list[dict], stream_id: str, event_type: str) -> dict:
    matches = [event for event in events if event["stream_id"] == stream_id and event["event_type"] == event_type]
    if len(matches) != 1:
        raise IntegrityError(f"the SPEC-01 route requires exactly one {event_type} on {stream_id}")
    return matches[0]


def _stream(row: str, ids: dict[str, str], ctx: AssayContext) -> str:
    if row == "OR-140":
        return CATALOGUE_STREAM_ID
    if row in {"OR-101", "OR-103"}:
        return _content(ctx, ASSAY_RUBRIC_PATH)["record_id"]
    if row in {"OR-102", "OR-104"}:
        return _content(ctx, ASSAY_SCOPE_PATH)["record_id"]
    if row == _BRIEF:
        return ids["brief_id"]
    if row == _RETURN:
        return ids["return_id"]
    if row in {"OR-105", "OR-106", "OR-034", "OR-006"}:
        return ids["review_id"]
    if row in {"OR-107", "OR-108", "OR-012", "OR-013"}:
        return ids["decision_id"]
    return ids["assay_id"]


def _subjects(ids: dict[str, str], events: list[dict], ctx: AssayContext) -> tuple[dict, dict, dict]:
    projection = _projection(events, ctx)
    candidate = projection["candidates"].get(ids["candidate_id"])
    assay = projection["assays"].get(ids["assay_id"])
    if (
        not isinstance(candidate, dict)
        or not isinstance(assay, dict)
        or assay.get("candidate_id") != ids["candidate_id"]
    ):
        raise IntegrityError(f"the SPEC-01 route requires the Candidate's route-requested Assay: {ids['assay_id']}")
    return projection, candidate, assay


def _completed(action: str, ids: dict[str, str], events: list[dict], ctx: AssayContext) -> dict[str, Any]:
    state = evaluate({"action": action, "candidate_id": ids["candidate_id"]}, events, ctx)
    if state["state"] != "completed":
        raise IntegrityError(f"the SPEC-01 route requires {action} to be completed first")
    return state


def _causal_prefix(events: list[dict], ctx: AssayContext) -> dict[str, Any]:
    tail = events[-1] if events else None
    position = tail["global_position"] if tail else 0
    return {
        "global_position": position,
        "event_hash": tail["event_hash"] if tail else "0" * 64,
        "raw_prefix_sha256": ctx.raw_prefix_sha256(position),
    }


def _governed_code_subject(events: list[dict]) -> dict[str, Any]:
    bindings = [event for event in events if event["event_type"] in _BINDING_EVENTS]
    if not bindings:
        raise IntegrityError("SPEC-01 operator records require a store-binding event for the governed-code subject")
    binding = bindings[-1]
    return {
        "binding_event": _event_ref(binding),
        "event_type": binding["event_type"],
        **{key: binding["payload"][key] for key in ("recovery_binding_sha256", "git_head", "git_tree")},
    }


def _task_provenance(candidate_id: str, events: list[dict], ctx: AssayContext) -> dict[str, Any]:
    """Return the operational provenance of the operator records (P-058, 2026-09-15).

    Admission never checks a manifest's Task, dispatch, attempt, context packet, code
    commit or environment fingerprint, and the caller cannot supply them, so they come
    from the one Task naming the Candidate and that Task's started Attempt (PR #291 review):
    - the Task names no other registered Candidate, as the project-use result requires;
    - the Task is still at the revision the Attempt was dispatched on, so an amendment
      after dispatch cannot lend the Attempt a definition it never ran;
    - the Attempt is still running, so a finished Attempt is never cited as producing a
      record created after it ended.
    """
    streams = replay(tuple(events), schema_registry=ctx.schemas, authority_state_validator=ctx.validator)["streams"]
    tasks = [
        stream_id
        for stream_id, stream in streams.items()
        if str(stream_id).startswith("tsk_")
        and isinstance(stream, dict)
        and candidate_id in tuple((stream.get("definition") or {}).get("portfolio_refs") or ())
    ]
    if len(tasks) != 1:
        raise IntegrityError(f"SPEC-01 operator records require exactly one Task naming Candidate {candidate_id}")
    registered = _projection(events, ctx)["candidates"]
    named = [ref for ref in streams[tasks[0]]["definition"]["portfolio_refs"] if ref in registered]
    if named != [candidate_id]:
        raise IntegrityError(f"SPEC-01 operator records require Task {tasks[0]} to name no other registered Candidate")
    attempts = [
        stream_id
        for stream_id, stream in streams.items()
        if str(stream_id).startswith("att_")
        and isinstance(stream, dict)
        and stream.get("task_id") == tasks[0]
        and isinstance(stream.get("start"), dict)
    ]
    if len(attempts) != 1:
        raise IntegrityError(f"SPEC-01 operator records require exactly one started Attempt of Task {tasks[0]}")
    attempt = streams[attempts[0]]
    if attempt.get("task_revision") != streams[tasks[0]].get("current_revision"):
        raise IntegrityError(f"SPEC-01 operator records require Task {tasks[0]} unamended since its Attempt's dispatch")
    if attempt.get("status") != "running":
        raise IntegrityError(f"SPEC-01 operator records require Attempt {attempts[0]} to be running")
    start = attempt["start"]
    return {
        "task_id": tasks[0],
        "task_revision": attempt["task_revision"],
        "attempt_id": attempts[0],
        "dispatch_id": attempt["dispatch_id"],
        "context_packet_id": start["context_packet_id"],
        "code_identity": start["code_identity"],
        "environment_fingerprint": start["environment_fingerprint"],
    }


def _brief_source(ctx: AssayContext) -> dict[str, Any]:
    try:
        package_raw = (ctx.repository_root / ROUTE_PACKAGE_PATH).read_bytes()
        sources = [
            source
            for source in json.loads(package_raw).get("sources", ())
            if isinstance(source, dict) and source.get("alias") == _BRIEF_ALIAS
        ]
        source = sources[0] if len(sources) == 1 else {}
        raw = (ctx.repository_root / source["locator"]).read_bytes()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise IntegrityError(f"{PREPARE} requires the committed route package and its SPEC-01 brief") from exc
    if len(raw) != source.get("size_bytes") or sha256_hex(raw) != source.get("sha256"):
        raise IntegrityError(f"{PREPARE} requires SPEC-01 brief bytes that match the route package")
    return {
        "alias": _BRIEF_ALIAS,
        "locator": source["locator"],
        "media_type": source["media_type"],
        "size_bytes": len(raw),
        "sha256": source["sha256"],
        "route_package_sha256": sha256_hex(package_raw),
    }


def _brief(ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str) -> dict:
    """Derive the operator brief package from a ledger prefix; refuses before registration."""
    _, candidate, assay = _subjects(ids, events, ctx)
    _completed(REQUEST, ids, events, ctx)
    if assay.get("status") != "evidence_collecting" or candidate.get("status") != "assay_pending":
        raise IntegrityError(f"{PREPARE} requires an Assay that is still collecting evidence")
    document = {
        "schema_id": BRIEF_SCHEMA_ID,
        "schema_version": "1.0.0",
        "document_type": BRIEF_TYPE,
        "intent": {"action": PREPARE, "candidate_id": ids["candidate_id"]},
        "recorded_at": recorded_at,
        "producer_actor_id": actor_id,
        "causal_prefix": _causal_prefix(events, ctx),
        "route_id": _ROUTE_IDENTITY,
        "brief_source": _brief_source(ctx),
        "task": _task_provenance(ids["candidate_id"], events, ctx),
        "candidate": {key: candidate[key] for key in ("candidate_id", "revision", "content_sha256")},
        "assay": {
            "assay_id": ids["assay_id"],
            "request_event": _event_ref(_one(events, ids["assay_id"], "AssayRequested")),
            "assay_bar_acceptance_sha256": assay["assay_bar_acceptance_sha256"],
            "producer_relation_sha256": assay["producer_relation_sha256"],
        },
        "governed_code_subject": _governed_code_subject(events),
    }
    _validate(BRIEF_SCHEMA_ID, document, ctx)
    return document


def _scorecard(
    ids: dict[str, str], projection: dict, candidate: dict, assay: dict, evidence: dict, ctx: AssayContext
) -> dict[str, Any]:
    """Derive the scorecard from the accepted bar and the operator's axis answers.

    The mechanical recommendation is the one the inherited admission rule accepts, so the
    route never restates that rule and refuses an inadmissible scorecard before the return
    is registered.
    """
    bar = projection["assay_bar_authority"]
    acceptance = bar.get("acceptance")
    if bar.get("status") != "accepted" or not isinstance(acceptance, dict):
        raise IntegrityError(f"{RETURN} requires an accepted Assay bar")
    rubric, scope = bar["contents"]["rubric"]["content"], bar["contents"]["scope"]["content"]
    definitions, rows, supplied = rubric["axis_definitions"], scope["evidence_rows"], evidence["axis_results"]
    if (
        not isinstance(supplied, list)
        or len(supplied) != len(definitions)
        or len(rows) != len(definitions)
        or any(not isinstance(result, dict) or set(result) != _AXIS_EVIDENCE for result in supplied)
        or [result["axis_id"] for result in supplied] != [definition.get("axis_id") for definition in definitions]
    ):
        raise IntegrityError(f"{RETURN} must answer every rubric axis exactly once, in rubric order")
    for result in supplied:
        _strings(result["unmet_condition_codes"], f"{RETURN} unmet_condition_codes")
    for label in ("limitations", "prohibited_inferences", "review_requirements"):
        _strings(evidence[label], f"{RETURN} {label}")
    file_refs = [
        _record_ref(content["record_id"], content["record_revision"], bar["observations"][kind]["file_sha256"])
        for kind, content in (("rubric", rubric), ("scope", scope))
    ]
    producer = acceptance["prospective_producer_ref"]
    base = {
        "schema_id": "ars://portfolio/assay-scorecard",
        "schema_version": "1.0.0",
        "candidate_ref": _record_ref(ids["candidate_id"], candidate["revision"], candidate["content_sha256"]),
        "assay_id": ids["assay_id"],
        "assay_requested_event_ref": _record_ref(
            ids["assay_id"], assay["request_version"], assay["requested_event_hash"]
        ),
        "assay_relation_hash": assay["producer_relation_sha256"],
        "rubric_ref": acceptance["rubric_ref"],
        "scope_ref": acceptance["scope_ref"],
        "assay_bar_acceptance_ref": _record_ref(acceptance["decision_id"], 1, bar["acceptance_sha256"]),
        "file_observation_refs": file_refs,
        "producer_relation_ref": producer,
        "axis_results": [
            {
                "axis_id": definition["axis_id"],
                "axis_kind": definition["axis_kind"],
                "value": result["value"],
                "rationale": result["rationale"],
                "evidence_refs": file_refs,
                "unmet_condition_codes": result["unmet_condition_codes"],
                "validator_id": row["validator_id"],
                "validator_hash": row["validator_hash"],
            }
            for definition, result, row in zip(definitions, supplied, rows, strict=True)
        ],
        "required_axis_set_hash": acceptance["required_axis_set_hash"],
        "observed_axis_set_hash": _axis_set_hash([definition["axis_id"] for definition in definitions]),
        "rule_evaluation_ref": _record_ref(
            rubric["rule_evaluation_algorithm_id"], 1, rubric["rule_evaluation_algorithm_hash"]
        ),
        "limitations": evidence["limitations"],
        "prohibited_inferences": evidence["prohibited_inferences"],
        "producer_actor_id": producer["id"],
        "producer_profile_ref": producer,
        "producer_context_ref": producer,
        "review_requirements": evidence["review_requirements"],
    }
    for recommendation in ("PROMOTE", "KILL"):
        scorecard = {**base, "mechanical_recommendation": recommendation}
        _validate("ars://portfolio/assay-scorecard", scorecard, ctx)
        payload = {
            "candidate_id": ids["candidate_id"],
            "assay_id": ids["assay_id"],
            "scorecard_sha256": sha256_hex(canonical_bytes(scorecard)),
        }
        if _assay_scorecard_matches(scorecard, payload, candidate, assay, bar, producer["id"]):
            return scorecard
    raise IntegrityError(f"{RETURN} scorecard would not be admitted: each axis value must satisfy the accepted rubric")


def _operator_return(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str, evidence: dict
) -> dict:
    """Derive the operator return from a ledger prefix and the operator's content."""
    projection, candidate, assay = _subjects(ids, events, ctx)
    prepared = _completed(PREPARE, ids, events, ctx)
    registration = next(event for event in events if event["event_id"] == prepared["effects"][0]["event_id"])
    brief = _read_document(_BRIEF, registration, ctx)
    task = _task_provenance(ids["candidate_id"], events, ctx)
    if task != brief["task"]:
        raise IntegrityError(f"{RETURN} must come from the Task and Attempt the brief was issued to")
    if assay.get("status") != "evidence_collecting" or candidate.get("status") != "assay_pending":
        raise IntegrityError(f"{RETURN} requires an Assay that is still collecting evidence")
    scorecard = _scorecard(ids, projection, candidate, assay, evidence, ctx)
    document = {
        "schema_id": RETURN_SCHEMA_ID,
        "schema_version": "1.0.0",
        "document_type": RETURN_TYPE,
        "intent": {"action": RETURN, "candidate_id": ids["candidate_id"]},
        "recorded_at": recorded_at,
        "producer_actor_id": actor_id,
        "causal_prefix": _causal_prefix(events, ctx),
        "route_id": _ROUTE_IDENTITY,
        "brief": registration_ref(registration),
        "task": task,
        "candidate": {key: candidate[key] for key in ("candidate_id", "revision", "content_sha256")},
        "assay": {"assay_id": ids["assay_id"]},
        "operator_return": deepcopy(evidence),
        "scorecard": scorecard,
        "scorecard_sha256": sha256_hex(canonical_bytes(scorecard)),
        "governed_code_subject": _governed_code_subject(events),
    }
    _validate(RETURN_SCHEMA_ID, document, ctx)
    return document


def _build(
    row: str,
    ids: dict[str, str],
    events: list[dict],
    ctx: AssayContext,
    *,
    actor_id: str,
    recorded_at: str,
    evidence: dict | None,
) -> dict:
    if row == _BRIEF:
        return _brief(ids, events, ctx, actor_id=actor_id, recorded_at=recorded_at)
    return _operator_return(ids, events, ctx, actor_id=actor_id, recorded_at=recorded_at, evidence=evidence or {})


def _stored(row: str, artefact_id: str, ctx: AssayContext) -> dict | None:
    """Return an operator record's immutable bytes, or None. Each kind is named literally (06i)."""
    if row == _BRIEF:
        if not ctx.objects.revision_exists(BRIEF_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(BRIEF_KIND, artefact_id, 1)
    else:
        if not ctx.objects.revision_exists(RETURN_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(RETURN_KIND, artefact_id, 1)
    _validate(BRIEF_SCHEMA_ID if row == _BRIEF else RETURN_SCHEMA_ID, document, ctx)
    return document


def _read_document(row: str, registration: dict, ctx: AssayContext) -> dict:
    artefact_id = registration["stream_id"]
    document = _stored(row, artefact_id, ctx)
    if document is None:
        raise IntegrityError(f"SPEC-01 operator record bytes are absent for its registration: {artefact_id}")
    manifest = (registration.get("payload") or {}).get("manifest") or {}
    raw = canonical_bytes(document)
    kind = BRIEF_KIND if row == _BRIEF else RETURN_KIND
    if (
        manifest.get("content_sha256") != sha256_hex(raw)
        or manifest.get("size_bytes") != len(raw)
        or manifest.get("relative_path") != f"objects/{kind}/{artefact_id}/00000001-{sha256_hex(raw)}.json"
    ):
        raise IntegrityError(f"SPEC-01 operator record registration and immutable bytes disagree: {artefact_id}")
    return document


def _manifest(row: str, document: dict[str, Any], artefact_id: str) -> dict[str, Any]:
    kind, document_type, schema_id = (
        (BRIEF_KIND, BRIEF_TYPE, BRIEF_SCHEMA_ID) if row == _BRIEF else (RETURN_KIND, RETURN_TYPE, RETURN_SCHEMA_ID)
    )
    raw = canonical_bytes(document)
    digest = sha256_hex(raw)
    task = document["task"]
    inputs = (
        []
        if row == _BRIEF
        else [
            {
                "input_artefact_id": document["brief"]["artefact_id"],
                "input_content_sha256": document["brief"]["content_sha256"],
                "dependency_role": "operator_brief",
            }
        ]
    )
    return {
        "task_id": task["task_id"],
        "dispatch_id": task["dispatch_id"],
        "attempt_id": task["attempt_id"],
        "context_packet_id": task["context_packet_id"],
        "producer_profile": f"{_ROUTE_IDENTITY}:{document_type}",
        # The producing Attempt's own identities (PR #291 review), not the store binding's.
        "code_commit": task["code_identity"],
        "branch_identity": _ROUTE_IDENTITY,
        "worktree_identity": _ROUTE_IDENTITY,
        "environment_fingerprint": task["environment_fingerprint"],
        "artefact_id": artefact_id,
        "aliases": [],
        "artefact_type": document_type,
        "artefact_schema_id": schema_id,
        "artefact_schema_version": "1.0.0",
        "producer_actor_id": document["producer_actor_id"],
        "created_at": document["recorded_at"],
        "observed_at": document["recorded_at"],
        "root_id": "control",
        "relative_path": f"objects/{kind}/{artefact_id}/00000001-{digest}.json",
        "size_bytes": len(raw),
        "media_type": "application/json",
        "content_sha256": digest,
        "availability_check_evidence_refs": [],
        "input_dependencies": inputs,
        "research_provenance": {
            key: []
            for key in (
                "dataset_ids",
                "dataset_vintages",
                "representation_ids",
                "parameter_ids",
                "seed_ids",
                "sample_restriction_ids",
            )
        },
        "validation": {"validation_record_refs": [], "expected_contract_ids": [], "expected_schema_ids": [schema_id]},
        "authority": {
            "availability": "available",
            "regenerability": "non_regenerable",
            "integrity": "verified",
            "structural_validation": "passed",
            "scientific_review": "pending",
            "use_authority": "candidate",
            "accepted_scope": f"spec:{document_type}:{document['candidate']['candidate_id']}",
            "consumer_restrictions": [],
        },
        "operations": {
            "no_overwrite_evidence_refs": [],
            "retention_class": "durable",
            "confidentiality_class": "internal",
            "external_data_constraints": [],
        },
    }


def _refuse_blocked_promote(ids: dict[str, str], events: list[dict], ctx: AssayContext) -> None:
    """Refuse a PROMOTE the SPEC-01 brief forbids but admission would accept (PR #291 review).

    Admission derives a mechanical PROMOTE from the required gate axes alone, so an axis it
    does not evaluate, such as SPEC-01's integer data and novelty scores, cannot stop one.
    While the Assay's bar has such an axis, PROMOTE stays refused until its rule is
    evaluated (Phase 5 prep). The bar is read from the registered return's scorecard, which
    admission bound to the Assay's frozen bar when it scored, never from a later accepted
    bar. The brief makes an unresolved primary-paper/code discrepancy blocking, and the
    return cannot mark which findings block, so any unresolved finding refuses PROMOTE.
    """
    returned = _read_document(_RETURN, _one(events, ids["return_id"], "ArtefactRegistered"), ctx)
    scorecard = returned["scorecard"]
    # Equal axis-set hashes mean every axis is required; a non-gate axis is only bounds-checked.
    if scorecard["required_axis_set_hash"] != scorecard["observed_axis_set_hash"] or any(
        result["axis_kind"] != "gate" for result in scorecard["axis_results"]
    ):
        raise IntegrityError(
            f"{DECIDE} cannot PROMOTE: the Assay's bar has an axis the scorecard rule does not evaluate"
        )
    if returned["operator_return"]["unresolved_findings"]:
        raise IntegrityError(f"{DECIDE} cannot PROMOTE while the operator return lists unresolved findings")


def _payload(
    row: str,
    intent: dict[str, Any],
    ids: dict[str, str],
    events: list[dict],
    ctx: AssayContext,
    *,
    actor_id: str | None = None,
    grant_id: str | None = None,
    evidence: dict | None = None,
) -> dict:
    """Return the exact command payload for one W11 row from the ledger before it.

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
    if row == "OR-003":
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
    subject = {"candidate_id": ids["candidate_id"], "assay_id": ids["assay_id"]}
    if row == "OR-004":
        document = _read_document(_RETURN, _one(events, ids["return_id"], "ArtefactRegistered"), ctx)
        if not _same_record(evidence, document["operator_return"]):
            raise IntegrityError(f"{RETURN} Assay producer must supply the exact operator return that was registered")
        _, _, assay = _subjects(ids, events, ctx)
        return {
            "row_id": "OR-004",
            **subject,
            "scorecard_sha256": document["scorecard_sha256"],
            "scorecard_artifact": document["scorecard"],
            "producer_relation_sha256": assay["producer_relation_sha256"],
        }
    if row == "OR-034":
        _completed(RETURN, ids, events, ctx)
        _, _, assay = _subjects(ids, events, ctx)
        if assay.get("status") != "scored":
            raise IntegrityError(f"{REVIEW} requires a scored Assay")
        digest = assay["scorecard_sha256"]
        returned = _one(events, ids["return_id"], "ArtefactRegistered")
        scored = _one(events, ids["assay_id"], "AssayScored")
        return {
            "row_id": "OR-034",
            **subject,
            "review_id": ids["review_id"],
            "subject_sha256": digest,
            "review_contract": {
                "review_type": "provenance",
                "new_review_id": ids["review_id"],
                "subject_ids": [ids["assay_id"]],
                "subject_hashes": [digest],
                "governing_refs": ["W11:OR-034", f"{_ROUTE_IDENTITY}:{_BRIEF_ALIAS}"],
                "review_questions": [
                    "Is the scorecard exactly the one the operator returned against the issued brief and the "
                    "accepted Assay bar?"
                ],
                "required_evidence_refs": [
                    f"scorecard:{digest}",
                    f"operator-return:{returned['payload']['manifest']['content_sha256']}",
                ],
                "required_lanes": ["output", "provenance"],
                "reviewer_capability": ["assay-independent-review"],
                "required_independence_grade": _OUTCOME_REVIEW_GRADE,
                "visibility_policy": "owner-visible",
                "allowed_verdicts": ["approve", "changes_requested", "reject"],
                "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
                "deadline": _time(scored["recorded_at"], _REVIEW_WINDOW),
                "escalation_rule": "owner-ruling",
            },
        }
    if row == "OR-006":
        projection, _, _ = _subjects(ids, events, ctx)
        review = projection["reviews"].get(ids["review_id"])
        if not isinstance(review, dict) or review.get("status") != "pending":
            raise IntegrityError(f"{REVIEW} requires its pending outcome review")
        returned = _read_document(_RETURN, _one(events, ids["return_id"], "ArtefactRegistered"), ctx)
        supplied = evidence or {}
        verdict = {
            "review_id": ids["review_id"],
            "verdict": "approve",
            "findings": supplied["findings"],
            "required_evidence_refs": list(review["required_evidence_refs"]),
            "limitations": supplied["limitations"],
            "conditions": [],
            "reviewer_actor_id": actor_id,
            **{
                key: supplied[key]
                for key in (
                    "reviewer_profile",
                    "reviewer_session",
                    "reviewer_model_metadata",
                    "context_manifest_id",
                    "context_manifest_sha256",
                    "trace_visibility_evidence_refs",
                )
            },
            "unchanged_subject_sha256": review["subject_sha256"],
            "producing_attempt_id": returned["task"]["attempt_id"],
            "computed_independence_grade": review["required_independence_grade"],
        }
        return {
            "row_id": "OR-006",
            **subject,
            "review_id": ids["review_id"],
            "subject_sha256": review["subject_sha256"],
            "verdict": "approve",
            "review_verdict": verdict,
        }
    if row == "OR-012":
        _completed(REVIEW, ids, events, ctx)
        projection, candidate, assay = _subjects(ids, events, ctx)
        review = projection["reviews"].get(ids["review_id"])
        recommendation = intent["recommendation"]
        if not isinstance(review, dict) or review.get("status") != "satisfied":
            raise IntegrityError(f"{DECIDE} requires a satisfied outcome review")
        if recommendation == "PROMOTE" and assay.get("mechanical_recommendation") != "PROMOTE":
            raise IntegrityError(f"{DECIDE} cannot propose PROMOTE without a mechanical PROMOTE scorecard")
        if recommendation == "PROMOTE":
            _refuse_blocked_promote(ids, events, ctx)
        reviewed = _one(events, ids["review_id"], "ReviewVerdictRecorded")
        aggregate = _record_ref(ids["assay_id"], assay.get("version"), _aggregate_content_hash(assay))
        return {
            "row_id": "OR-012",
            "candidate_id": ids["candidate_id"],
            "decision_id": ids["decision_id"],
            "review_id": ids["review_id"],
            "w2_payload": {
                "question": _GATE,
                "recommendation": recommendation,
                "new_decision_id": ids["decision_id"],
                "decision_revision": 1,
                "decision_kind": "design_lock",
                "options": ["PROMOTE", "PARK", "KILL"],
                "governing_evidence_refs": [f"scorecard:{assay['scorecard_sha256']}", f"review:{ids['review_id']}"],
                "affected_task_ids": [],
                "affected_claim_ids": [],
                "required_authority": "owner",
                "expires_at": _time(reviewed["recorded_at"], _REVIEW_WINDOW),
                "review_date": _time(reviewed["recorded_at"]),
                "consequences": [_CONSEQUENCES[recommendation]],
            },
            "promotion_relation": {
                "schema_id": "ars://portfolio/relation/discovery-promotion",
                "schema_version": "1.0.0",
                "relation_kind": "discovery_promotion",
                "decision_id": ids["decision_id"],
                "candidate_ref": _record_ref(ids["candidate_id"], candidate["revision"], candidate["content_sha256"]),
                "gate": _GATE,
                "aggregate_ref": aggregate,
                "aggregate_relation_hash": assay["producer_relation_sha256"],
                "evidence_ref": aggregate,
                "selected_option": recommendation,
                "next_candidate_state": _NEXT_STATE[recommendation],
                "rationale": "The route proposes this option against the exact reviewed scorecard; the owner decides.",
                "considered_evidence_refs": [_review_ref(review)],
                "conditions": [],
                "effective_scope": f"{_GATE}:{ids['candidate_id']}",
                "revisit_triggers": [],
                "actor_id": actor_id,
            },
        }
    if row == "OR-013":
        decision = _projection(events, ctx)["decisions"].get(ids["decision_id"])
        if not isinstance(decision, dict) or decision.get("status") != "proposed":
            raise IntegrityError(f"{DECIDE} requires its proposed Decision")
        supplied = evidence or {}
        selected, triggers = supplied.get("selected_option"), supplied.get("revisit_triggers")
        if selected not in _NEXT_STATE:
            raise IntegrityError(f"{DECIDE} selected option must be PROMOTE, PARK or KILL")
        _strings(triggers, f"{DECIDE} revisit_triggers")
        if selected == "PARK" and not triggers:
            raise IntegrityError(f"{DECIDE} PARK requires the owner's revisit triggers")
        # Admission lets the owner select PROMOTE on any mechanical PROMOTE, whatever was proposed.
        if selected == "PROMOTE":
            _refuse_blocked_promote(ids, events, ctx)
        proposal = _one(events, ids["decision_id"], "DecisionProposed")
        return {
            "row_id": "OR-013",
            "candidate_id": ids["candidate_id"],
            "decision_id": ids["decision_id"],
            "w2_payload": {
                "decision_id": ids["decision_id"],
                "selected_option": selected,
                "effective_scope": "exact Discovery subject",
                "decision_revision": 1,
                "deciding_actor_id": actor_id,
                "decision_authority_grant_id": grant_id,
                "governing_evidence_refs": list(proposal["payload"]["governing_evidence_refs"]),
                "considered_review_ids": [ids["review_id"]],
                "effective_at": _time(proposal["recorded_at"]),
                "permitted_commands": [],
                "superseded_decision_ids": [],
                "conditions": [],
                "revisit_triggers": triggers,
            },
        }
    raise IntegrityError(f"the Assay route has no payload for row {row}")


def _check_relation(row: str, ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str) -> None:
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
    if row not in {"OR-034", "OR-006", "OR-012"}:
        return
    owner = _owner(events, ctx)
    producer = (_projection(events, ctx)["assays"].get(ids["assay_id"]) or {}).get("producer_actor_id")
    if row == "OR-034" and actor_id in {producer, owner}:
        raise IntegrityError(f"{REVIEW} outcome-review requester must be neither the producer nor the owner")
    if row == "OR-006" and actor_id == owner:
        raise IntegrityError(f"{REVIEW} outcome reviewer must not be the owner")
    if row == "OR-012":
        reviewers = {
            event["actor_id"]
            for event in events
            if event["stream_id"] == ids["review_id"] and event["event_type"] == "ReviewVerdictRecorded"
        }
        if actor_id in {producer, owner, *reviewers}:
            raise IntegrityError(f"{DECIDE} proposer must be neither the producer, the reviewer nor the owner")


def _check_evidence(row: str, evidence: dict | None) -> None:
    required = _EVIDENCE.get(row)
    if required is None:
        if evidence is not None:
            raise IntegrityError(f"{_command_type(row)} takes no independent evidence")
        return
    if not isinstance(evidence, dict) or set(evidence) != required:
        raise IntegrityError(f"{_command_type(row)} evidence fields are not exact: expected {sorted(required)}")


def _recorded_evidence(
    row: str, event: dict, ids: dict[str, str], prefix: list[dict], ctx: AssayContext
) -> dict | None:
    """Recover the caller evidence an OR row carried, from its event or, for OR-004, the registered return."""
    if row == "OR-004":
        return _read_document(_RETURN, _one(prefix, ids["return_id"], "ArtefactRegistered"), ctx)["operator_return"]
    if row not in {"OR-006", "OR-013"}:
        return None
    payload = event.get("payload") or {}
    return {key: payload.get(key) for key in _EVIDENCE[row]}


def _issued(event: dict, intent: dict[str, Any], effect: str, payload: dict) -> bool:
    key = retry_key(intent, effect, event["actor_id"], event["authority_grant_id"], payload)
    return (
        event.get("idempotency_key") == key
        and event.get("command_id") == _stable_command_id(key)
        and event.get("command_payload_hash") == sha256_hex(canonical_bytes(payload))
    )


def _issued_registration(event: dict, intent: dict[str, Any]) -> bool:
    """Whether a registration carries this route's key over its own recorded payload."""
    key = retry_key(
        intent, "RegisterArtefact", event["actor_id"], event["authority_grant_id"], event.get("payload") or {}
    )
    return event.get("idempotency_key") == key and event.get("command_id") == _stable_command_id(key)


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


def _verified_document(
    row: str, ids: dict[str, str], registration: dict, events: list[dict], ctx: AssayContext
) -> dict:
    """Re-derive an operator record at its own recorded causal prefix and require equality."""
    document = _read_document(row, registration, ctx)
    position = document["causal_prefix"]["global_position"]
    if position >= registration["global_position"]:
        raise IntegrityError("a SPEC-01 operator record cannot cite its own or a later registration")
    expected = _build(
        row,
        ids,
        [event for event in events if event["global_position"] <= position],
        ctx,
        actor_id=registration["actor_id"],
        recorded_at=document["recorded_at"],
        evidence=document.get("operator_return"),
    )
    if document != expected:
        raise IntegrityError("a SPEC-01 operator record is not the document this route derives")
    return document


def _verify_effect(
    row: str, intent: dict[str, Any], ids: dict[str, str], first: dict, events: list[dict], ctx: AssayContext
) -> None:
    action = intent["action"]
    prefix = _prefix(events, first["global_position"])
    foreign = ConflictError(f"{action} found {first['event_type']} on its stream that this route did not issue")
    if row in _ARTEFACT_ROWS:
        if first["event_type"] != "ArtefactRegistered" or not _issued_registration(first, intent):
            raise foreign
        target = _stream(row, ids, ctx)
        document = _verified_document(row, ids, first, events, ctx)
        if first["payload"] != {"new_artefact_id": target, "manifest": _manifest(row, document, target)}:
            raise IntegrityError(f"{action} registration does not carry the document this route derives")
    else:
        payload = _payload(
            row,
            intent,
            ids,
            prefix,
            ctx,
            actor_id=first["actor_id"],
            grant_id=first["authority_grant_id"],
            evidence=_recorded_evidence(row, first, ids, prefix, ctx),
        )
        if not _issued(first, intent, _command_type(row), payload):
            raise foreign
    _check_relation(row, ids, prefix, ctx, actor_id=first["actor_id"])


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
        _verify_effect(row, intent, ids, transaction[0], events, ctx)
    # Scan even while the action is partial: an effect this route did not issue can land on a stream
    # before the route reaches it, and appending past it can leave a later route effect inadmissible.
    if action in _OWNED_ROWS:
        owned = {_stream(row, ids, ctx) for row in _OWNED_ROWS[action]}
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
    intent: dict[str, Any],
    evidence: dict | None,
    events: list[dict],
    ctx: AssayContext,
    *,
    actor_id: str,
    grant_id: str,
    now: str,
) -> tuple[str, str, dict[str, Any], tuple[str, dict] | None]:
    """Build the next effect for an action, refusing before any durable mutation.

    Args:
        intent: Validated Assay route intent.
        evidence: Caller evidence, for the effects that take it.
        events: Full ordered ledger event list from one snapshot.
        ctx: Route context.
        actor_id: Actor of this invocation.
        grant_id: Authority grant of this invocation.
        now: Trusted submission time, recorded in a new operator record.

    Returns:
        The command type, target stream, exact payload and, for an operator record, the
        object kind and document to publish.

    Raises:
        IntegrityError: If the action is complete or this actor may not take the next effect.
        ConflictError: If unregistered operator-record bytes bind a different record.
    """
    state = evaluate(intent, events, ctx)
    if state["next_effect"] is None:
        raise IntegrityError(f"{intent['action']} is already completed")
    row = ROWS[intent["action"]][len(state["effects"])]
    ids = subject_ids(ctx.project_id, intent)
    _check_evidence(row, evidence)
    _check_relation(row, ids, events, ctx, actor_id=actor_id)
    target = _stream(row, ids, ctx)
    if row not in _ARTEFACT_ROWS:
        payload = _payload(row, intent, ids, events, ctx, actor_id=actor_id, grant_id=grant_id, evidence=evidence)
        return state["next_effect"], target, payload, None
    orphan = _stored(row, target, ctx)
    if orphan is None:
        document = _build(row, ids, events, ctx, actor_id=actor_id, recorded_at=now, evidence=evidence)
    else:
        # A process that stopped after publishing the bytes, before appending the registration,
        # left them behind. Immutable bytes cannot be replaced, so they are reused only if they are
        # exactly the record this route derives at their own causal prefix for this invocation, and
        # only while the record's prerequisites still hold on the current ledger.
        _build(row, ids, events, ctx, actor_id=actor_id, recorded_at=now, evidence=evidence)
        position = orphan["causal_prefix"]["global_position"]
        expected = _build(
            row,
            ids,
            [event for event in events if event["global_position"] <= position],
            ctx,
            actor_id=actor_id,
            recorded_at=orphan["recorded_at"],
            evidence=evidence,
        )
        if orphan != expected:
            raise ConflictError(f"{intent['action']} left unregistered bytes that bind a different record")
        document = orphan
    kind = BRIEF_KIND if row == _BRIEF else RETURN_KIND
    payload = {"new_artefact_id": target, "manifest": _manifest(row, document, target)}
    return state["next_effect"], target, payload, (kind, document)


def exact_retry(
    intent: dict[str, Any],
    evidence: dict | None,
    events: list[dict],
    ctx: AssayContext,
    *,
    actor_id: str,
    grant_id: str,
) -> dict | None:
    """Recognise a repeated invocation of an effect that is already committed.

    An invocation reproduces an effect's retry key only with that effect's actor, grant,
    evidence and payload. A recognised retry is answered from its receipt and never
    resubmitted.

    Args:
        intent: Validated Assay route intent.
        evidence: Evidence of the repeated invocation.
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
        if (row in _EVIDENCE) != (evidence is not None):
            continue
        # Payloads read only the known evidence fields, so an inexact field set must not match a retry.
        if evidence is not None and (not isinstance(evidence, dict) or set(evidence) != _EVIDENCE[row]):
            continue
        try:
            if row in _ARTEFACT_ROWS:
                payload = first.get("payload") or {}
                if row == _RETURN:
                    registered = _read_document(_RETURN, first, ctx).get("operator_return")
                    if not _same_record(evidence, registered):
                        continue
            else:
                prefix = _prefix(events, first["global_position"])
                payload = _payload(
                    row, intent, ids, prefix, ctx, actor_id=actor_id, grant_id=grant_id, evidence=evidence
                )
        except (ArsError, KeyError, TypeError):
            continue
        if retry_key(intent, _command_type(row), actor_id, grant_id, payload) == first.get("idempotency_key"):
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
        if not isinstance(candidate_id, str):
            continue
        ids = subject_ids(ctx.project_id, {"action": DECIDE, "candidate_id": candidate_id})
        if assay.get("assay_id") != ids["assay_id"]:
            continue
        for action in (REQUEST, PREPARE, RETURN, REVIEW):
            candidates.append({"action": action, "reason": f"recorded route {action}", "candidate_id": candidate_id})
        proposal = next(
            (e for e in events if e["stream_id"] == ids["decision_id"] and e["event_type"] == "DecisionProposed"), None
        )
        if proposal is not None and (proposal.get("payload") or {}).get("recommendation") in _NEXT_STATE:
            candidates.append(
                {
                    "action": DECIDE,
                    "reason": "recorded route decision",
                    "candidate_id": candidate_id,
                    "recommendation": proposal["payload"]["recommendation"],
                }
            )
    intents = []
    for intent in candidates:
        try:
            located = _located(intent, events, ctx)
            if not located:
                continue
            row, transaction = located[0]
            first = transaction[0]
            if row in _ARTEFACT_ROWS:
                issued = _issued_registration(first, intent)
            else:
                ids, prefix = subject_ids(ctx.project_id, intent), _prefix(events, first["global_position"])
                payload = _payload(
                    row,
                    intent,
                    ids,
                    prefix,
                    ctx,
                    actor_id=first["actor_id"],
                    grant_id=first["authority_grant_id"],
                    evidence=_recorded_evidence(row, first, ids, prefix, ctx),
                )
                issued = _issued(first, intent, _command_type(row), payload)
        except (ArsError, KeyError, TypeError):
            # Report the subject rather than hide it or deny the whole listing: evaluating
            # it lists the error as unreadable.
            intents.append(intent)
            continue
        if issued:
            intents.append(intent)
    return intents
