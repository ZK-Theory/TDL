"""06s Phase 4a (P-058): W11 bootstrap and the SPEC-01 Assay sequence on the public SPEC route.

Each action composes existing W11 Discovery rows; the two operator records are registered
artefacts. Admission keeps every command's own actor, authority grant and transaction;
nothing here adjudicates authority. The route adds only the relations admission was
measured to leave unchecked (P-058 amendment), and refuses them before the first durable
mutation:

- genesis is imported by the authority owner;
- the Assay-bar review requester is not an author of the committed content;
- the Assay requester is neither the prospective producer nor the owner;
- the Assay producer's own invocation carries the operator return it scores, or the Partial
  return it records;
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

A Partial outcome (06s Phase 4a′, P-058, 2026-09-17) registers its own closed record, then
OR-005, and is reviewed through OR-035 and OR-007. Each Partial action shares the return or
outcome-review identity of the complete action it replaces, so the two sequences exclude each
other at the first durable mutation, and the one not taken conflicts. A reviewed Partial Assay
reaches no promotion Decision; its Candidate is left for a revisit. Known limit: an owner who
registers the wrong alternative cannot switch on that Assay.

A reviewed Partial Assay is revisited, its retry authorized by the owner, and the retry requested
(06s Phase 4b-1, P-058, 2026-09-17). A later Assay in the retry lineage is named by its ordinal;
without one every identity is derived exactly as for the first Assay, and an ordinal is honoured
only for an Assay the route's own retry created from the Assay before it. One Task and its one
running Attempt span the whole lineage, and a later Assay's operator records are version 1.1.0,
whose intent carries its ordinal. The revisit predicate is the earliest SOURCE observation after
the review that the SOURCE route's own completion check accepts and whose one fact is the revisit
requirement, so only a single-requirement Partial can be revisited on the route. The route
refuses the producer, the owner or the outcome reviewer proposing a revisit, and the producer or
the owner requesting a retry; admission keeps the retry authorization owner-only.
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
    _assay_partial_bindings_match,
    _assay_scorecard_matches,
    _axis_set_hash,
    _record_ref,
    _review_ref,
)
from research_system.discovery.spec_result import _BINDING_EVENTS, _event_ref
from research_system.discovery.spec_source import SOURCE_REF_PREFIX, registration_ref, source_ids
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
RETURN_PARTIAL = "return_spec_01_partial"
REVIEW_PARTIAL = "review_spec_01_partial"
DECIDE = "decide_spec_01"
REVISIT = "request_spec_01_revisit"
AUTHORIZE = "authorize_spec_01_retry"
RETRY_REQUEST = "request_spec_01_retry"
# 06s Phase 4b-2a (P-058, 2026-09-18): the owner's SPEC-02 live-run approval, the Spike's operator brief
# and the Spike start, which runs W11 OR-014, OR-015, OR-016 and OR-017 in route order.
APPROVE_02 = "approve_spec_02"
PREPARE_02 = "prepare_spec_02"
START_02 = "start_spec_02"
INTENT_SCHEMA_ID = "ars://portfolio/spec-assay-intent"
INTENT_SCHEMA_VERSION = "1.3.0"
APPROVAL_SCHEMA_ID = "ars://portfolio/spec-02-live-run-approval"
SPEC_02_BRIEF_SCHEMA_ID = "ars://portfolio/spec-02-operator-brief"
APPROVAL_KIND = "spec_02_live_run_approval_document"
SPEC_02_BRIEF_KIND = "spec_02_operator_brief_document"
APPROVAL_TYPE = "spec_02_live_run_approval"
SPEC_02_BRIEF_TYPE = "spec_02_operator_brief"
BRIEF_SCHEMA_ID = "ars://portfolio/spec-operator-brief-package"
RETURN_SCHEMA_ID = "ars://portfolio/spec-operator-return"
PARTIAL_RETURN_SCHEMA_ID = "ars://portfolio/spec-operator-partial-return"
BRIEF_KIND = "spec_operator_brief_document"
RETURN_KIND = "spec_operator_return_document"
PARTIAL_RETURN_KIND = "spec_operator_partial_return_document"
BRIEF_TYPE = "spec_operator_brief_package"
RETURN_TYPE = "spec_operator_return"
PARTIAL_RETURN_TYPE = "spec_operator_partial_return"
_ASSAY_PARTIAL_SCHEMA_ID = "ars://portfolio/assay-partial"
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
_PARTIAL_RETURN = "AR:spec_01_operator_partial_return"
_APPROVAL = "AR:spec_02_live_run_approval"
_SPEC_02_BRIEF = "AR:spec_02_operator_brief"
_ARTEFACT_ROWS = frozenset({_BRIEF, _RETURN, _PARTIAL_RETURN, _APPROVAL, _SPEC_02_BRIEF})
_SPEC_02_ALIAS = "SPEC-02"
# The SPEC-02 actions the route carries. A Spike follows its Candidate's promoted Assay, which the
# route reads from the ledger, so none of them derives an Assay identity (P-058, 2026-09-18).
_SPEC_02_ACTIONS = frozenset({APPROVE_02, PREPARE_02, START_02})
ROWS = {
    GENESIS: ("OR-140",),
    BAR: ("OR-101", "OR-102", "OR-103", "OR-104", "OR-105", "OR-106", "OR-107", "OR-108"),
    REQUEST: ("OR-003",),
    PREPARE: (_BRIEF,),
    RETURN: (_RETURN, "OR-004"),
    RETURN_PARTIAL: (_PARTIAL_RETURN, "OR-005"),
    REVIEW: ("OR-034", "OR-006"),
    REVIEW_PARTIAL: ("OR-035", "OR-007"),
    DECIDE: ("OR-012", "OR-013"),
    REVISIT: ("OR-009",),
    AUTHORIZE: ("OR-010",),
    RETRY_REQUEST: ("OR-011",),
    APPROVE_02: (_APPROVAL,),
    PREPARE_02: (_SPEC_02_BRIEF,),
    START_02: ("OR-014", "OR-015", "OR-016", "OR-017"),
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
    RETURN_PARTIAL: (_PARTIAL_RETURN,),
    REVIEW: ("OR-034",),
    REVIEW_PARTIAL: ("OR-035",),
    DECIDE: ("OR-012",),
    # The revisit and its authorization share the revisit Decision stream; each counts the other's effect.
    REVISIT: ("OR-009",),
    AUTHORIZE: ("OR-010",),
    APPROVE_02: (_APPROVAL,),
    PREPARE_02: (_SPEC_02_BRIEF,),
    # The Spike stream also carries the later Spike rows (OR-018 onward), so the start wholly owns only its
    # execution Decision (OR-015, OR-016), as the Assay stream is left to its later actions (PR #298 review).
    START_02: ("OR-015",),
}
# The revisit trio acts on one Assay of the lineage and creates the next (P-058, 2026-09-17).
_REVISIT_ACTIONS = frozenset({REVISIT, AUTHORIZE, RETRY_REQUEST})
_SPEC_01_ACTIONS = (
    frozenset({REQUEST, PREPARE, RETURN, RETURN_PARTIAL, REVIEW, REVIEW_PARTIAL, DECIDE}) | _REVISIT_ACTIONS
)
# The return alternative each outcome action follows. The complete and Partial sequences share their
# return and outcome-review identities, so one Assay can take only one of them (P-058, 2026-09-17).
_RETURN_OF = {RETURN: RETURN, REVIEW: RETURN, RETURN_PARTIAL: RETURN_PARTIAL, REVIEW_PARTIAL: RETURN_PARTIAL}
# The Spike plan content the operator supplies at start_spec_02; every reference, and the approved
# scope, are derived (P-058, 2026-09-18).
_SPIKE_PLAN_FIELDS = (
    "question",
    "inputs",
    "method_or_object",
    "baselines",
    "null_or_comparator",
    "success_predicates",
    "failure_predicates",
    "kill_conditions",
    "partial_rules",
    "planned_contracts",
    "outputs",
    "prohibited_work",
    "outcome_to_next_step",
    "time_resource_box",
)
_APPROVAL_EVIDENCE = frozenset({"scope", "cost_ceiling"})
# The W11 Partial judgements the operator supplies; every reference in the Partial is derived.
_PARTIAL_JUDGEMENTS = (
    "completed_axes",
    "completed_evidence",
    "unmet_axes",
    "unmet_evidence",
    "reason_codes",
    "limitations",
    "revisit_requirements",
    "mechanical_recommendation",
)
_OPERATOR_PARTIAL_RETURN = frozenset(
    {*_PARTIAL_JUDGEMENTS, "direct_sources", "findings", "validation", "unresolved_findings", "prohibited_inferences"}
)
_VERDICT_EVIDENCE = frozenset(
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
)
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
    _PARTIAL_RETURN: _OPERATOR_PARTIAL_RETURN,
    "OR-005": _OPERATOR_PARTIAL_RETURN,
    "OR-006": _VERDICT_EVIDENCE,
    "OR-007": _VERDICT_EVIDENCE,
    "OR-013": frozenset({"selected_option", "revisit_triggers"}),
    # 06s Phase 4b-2a: the owner's approved scope and cost ceiling, and the Spike plan's own content.
    # The plan's scope is not caller evidence: the route derives it from the approval.
    _APPROVAL: _APPROVAL_EVIDENCE,
    "OR-014": frozenset(_SPIKE_PLAN_FIELDS),
}
_AXIS_EVIDENCE = frozenset({"axis_id", "value", "rationale", "unmet_condition_codes"})
_SPIKE_PLAN_SCHEMA_ID = "ars://portfolio/spike-plan"
_SPIKE_EXECUTION_RELATION = "ars://portfolio/relation/spike-execution-authority"
# The SPEC-02 contract's hard resource limits, transcribed from the exact contract bytes the route package
# pins: four CPU slots (workers), two hours, 12 GB memory and 5 GB attempt scratch, read as decimal
# megabytes (the stricter reading), and no network. The owner's ceiling may not exceed them (PR #298
# review). A test binds this transcription to the pinned bytes, so a changed contract fails until re-read.
_SPEC_02_LIMITS_SHA256 = "f005f4c961f91c4abcfdb6fc8a89d3b609b371ac5e613e82e68aaf5c3cf4dd32"
_SPEC_02_LIMITS = {
    "worker_limit": 4,
    "time_limit_seconds": 7_200,
    "memory_limit_mb": 12_000,
    "storage_limit_mb": 5_000,
    "network_access": False,
}

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
        read_source_document: Validated SOURCE document reader by artefact identity.
        source_state: The SOURCE route's own state of a SOURCE intent over a ledger and its replay.
        operational_state: The control plane's stream states over a ledger prefix, which a Spike start binds.
    """

    project_id: str
    schemas: SchemaRegistry
    validator: _Validator
    repository_root: Path
    objects: Any
    raw_prefix_sha256: Callable[[int], str]
    read_source_document: Callable[[str], tuple[dict, dict]]
    source_state: Callable[[dict, list[dict], dict], dict]
    operational_state: Callable[[list[dict]], dict[str, Any]]


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
        artefacts and the outcome review and Decision. The revisit trio also names the
        revisit Decision and the retry Assay it creates. A later Assay in the retry lineage
        carries its ordinal, and each of its identities also derives from it; the first
        Assay's identities are derived exactly as before (P-058, 2026-09-17). Genesis has none.
    """
    action = intent["action"]
    if action == BAR:
        return {
            "review_id": _stable("rev", project_id, BAR, "review"),
            "decision_id": _stable("dec", project_id, BAR, "decision"),
        }
    if action in _SPEC_02_ACTIONS:
        # A Spike's own subjects. Its Candidate's promoted Assay is read from the ledger, never derived
        # here, because a retried Candidate's current Assay carries an ordinal (P-058, 2026-09-18).
        candidate_id = intent["candidate_id"]
        return {
            "candidate_id": candidate_id,
            "approval_id": _stable("art", project_id, candidate_id, APPROVE_02),
            "spec_02_brief_id": _stable("art", project_id, candidate_id, PREPARE_02),
            "spike_id": _stable("spk", project_id, candidate_id, START_02),
            "execution_decision_id": _stable("dec", project_id, candidate_id, START_02),
        }
    if action not in _SPEC_01_ACTIONS:
        return {}
    candidate_id = intent["candidate_id"]
    ordinal = intent.get("assay_ordinal")
    if ordinal is not None and type(ordinal) is not int:
        # JSON Schema accepts 2.0 as an integer, but it would derive other identities than 2, and P0
        # canonical JSON rejects floating-point values (PR #297 review).
        raise SchemaError(f"assay_ordinal must be an integer literal, not {ordinal!r}")

    def identity(prefix: str, name: str, number: int | None = ordinal) -> str:
        return _stable(prefix, project_id, candidate_id, name, *([str(number)] if number else []))

    ids: dict[str, Any] = {"candidate_id": candidate_id, "assay_id": identity("asy", REQUEST)}
    if ordinal:
        ids["assay_ordinal"] = ordinal
    if action == REQUEST:
        return ids
    ids.update(
        brief_id=identity("art", PREPARE),
        return_id=identity("art", RETURN),
        review_id=identity("rev", REVIEW),
        decision_id=identity("dec", DECIDE),
    )
    if action in _REVISIT_ACTIONS:
        ids.update(
            revisit_decision_id=identity("dec", REVISIT),
            retry_assay_id=identity("asy", REQUEST, (ordinal or 1) + 1),
        )
    return ids


def _intent(action: str, ids: dict[str, Any]) -> dict[str, Any]:
    """Return the route intent for another action on the same Assay of a Candidate's lineage."""
    ordinal = {"assay_ordinal": ids["assay_ordinal"]} if "assay_ordinal" in ids else {}
    return {"action": action, "candidate_id": ids["candidate_id"], **ordinal}


def _record_version(ids: dict[str, Any]) -> str:
    """Return an operator record's schema version: 1.1.0 records a later Assay's ordinal (PR #297 review).

    A first Assay's records stay 1.0.0, so merged records re-derive unchanged.
    """
    return "1.1.0" if "assay_ordinal" in ids else "1.0.0"


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
        The action and, for a SPEC-01 or SPEC-02 action, its Candidate and any Assay ordinal.
    """
    key = {"action": intent["action"]}
    if intent["action"] in _SPEC_01_ACTIONS | _SPEC_02_ACTIONS:
        key["candidate_id"] = intent["candidate_id"]
        if "assay_ordinal" in intent:
            key["assay_ordinal"] = intent["assay_ordinal"]
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
    """Validate a record against the version it names; a later Assay's operator records are 1.1.0."""
    version = document.get("schema_version")
    try:
        if not isinstance(version, str):
            raise SchemaError(f"{schema_id} record names no schema version")
        ctx.schemas.validate(schema_id, document, schema_version=version)
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
        raise IntegrityError(f"the SPEC route requires exactly one {event_type} on {stream_id}")
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
    if row in {_RETURN, _PARTIAL_RETURN}:
        return ids["return_id"]
    if row == _APPROVAL:
        return ids["approval_id"]
    if row == _SPEC_02_BRIEF:
        return ids["spec_02_brief_id"]
    if row in {"OR-014", "OR-017"}:
        return ids["spike_id"]
    if row in {"OR-015", "OR-016"}:
        return ids["execution_decision_id"]
    if row in {"OR-105", "OR-106", "OR-034", "OR-035", "OR-006", "OR-007"}:
        return ids["review_id"]
    if row in {"OR-107", "OR-108", "OR-012", "OR-013"}:
        return ids["decision_id"]
    if row in {"OR-009", "OR-010"}:
        return ids["revisit_decision_id"]
    if row == "OR-011":
        return ids["retry_assay_id"]
    return ids["assay_id"]


def _subjects(ids: dict[str, str], events: list[dict], ctx: AssayContext) -> tuple[dict, dict, dict]:
    if "assay_ordinal" in ids:
        # A later Assay counts only if the route's own retry created it from the Assay before it.
        ordinal = ids["assay_ordinal"] - 1
        prior = {"candidate_id": ids["candidate_id"], **({"assay_ordinal": ordinal} if ordinal > 1 else {})}
        _completed(RETRY_REQUEST, prior, events, ctx)
    projection = _projection(events, ctx)
    candidate = projection["candidates"].get(ids["candidate_id"])
    assay = projection["assays"].get(ids["assay_id"])
    if (
        not isinstance(candidate, dict)
        or not isinstance(assay, dict)
        or assay.get("candidate_id") != ids["candidate_id"]
    ):
        raise IntegrityError(f"the SPEC route requires the Candidate's route-requested Assay: {ids['assay_id']}")
    return projection, candidate, assay


def _completed(action: str, ids: dict[str, str], events: list[dict], ctx: AssayContext, **extra: Any) -> dict[str, Any]:
    state = evaluate({**_intent(action, ids), **extra}, events, ctx)
    if state["state"] != "completed":
        raise IntegrityError(f"the SPEC route requires {action} to be completed first")
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
        raise IntegrityError("SPEC operator records require a store-binding event for the governed-code subject")
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
        raise IntegrityError(f"SPEC operator records require exactly one Task naming Candidate {candidate_id}")
    registered = _projection(events, ctx)["candidates"]
    named = [ref for ref in streams[tasks[0]]["definition"]["portfolio_refs"] if ref in registered]
    if named != [candidate_id]:
        raise IntegrityError(f"SPEC operator records require Task {tasks[0]} to name no other registered Candidate")
    attempts = [
        stream_id
        for stream_id, stream in streams.items()
        if str(stream_id).startswith("att_")
        and isinstance(stream, dict)
        and stream.get("task_id") == tasks[0]
        and isinstance(stream.get("start"), dict)
    ]
    if len(attempts) != 1:
        raise IntegrityError(f"SPEC operator records require exactly one started Attempt of Task {tasks[0]}")
    attempt = streams[attempts[0]]
    if attempt.get("task_revision") != streams[tasks[0]].get("current_revision"):
        raise IntegrityError(f"SPEC operator records require Task {tasks[0]} unamended since its Attempt's dispatch")
    if attempt.get("status") != "running":
        raise IntegrityError(f"SPEC operator records require Attempt {attempts[0]} to be running")
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
    return _route_source(ctx, _BRIEF_ALIAS, PREPARE)


def _route_source(ctx: AssayContext, alias: str, action: str) -> dict[str, Any]:
    """Return the committed route-package source an operator record binds, by its alias."""
    try:
        package_raw = (ctx.repository_root / ROUTE_PACKAGE_PATH).read_bytes()
        sources = [
            source
            for source in json.loads(package_raw).get("sources", ())
            if isinstance(source, dict) and source.get("alias") == alias
        ]
        source = sources[0] if len(sources) == 1 else {}
        raw = (ctx.repository_root / source["locator"]).read_bytes()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise IntegrityError(f"{action} requires the committed route package and its {alias} source") from exc
    if len(raw) != source.get("size_bytes") or sha256_hex(raw) != source.get("sha256"):
        raise IntegrityError(f"{action} requires {alias} bytes that match the route package")
    return {
        "alias": alias,
        "locator": source["locator"],
        "media_type": source["media_type"],
        "size_bytes": len(raw),
        "sha256": source["sha256"],
        "route_package_sha256": sha256_hex(package_raw),
    }


def _brief(ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str) -> dict:
    """Derive the operator brief package from a ledger prefix; refuses before registration."""
    _, candidate, assay = _subjects(ids, events, ctx)
    if "assay_ordinal" not in ids:
        # A later Assay was created by the route's retry, which _subjects has already required.
        _completed(REQUEST, ids, events, ctx)
    if assay.get("status") != "evidence_collecting" or candidate.get("status") != "assay_pending":
        raise IntegrityError(f"{PREPARE} requires an Assay that is still collecting evidence")
    document = {
        "schema_id": BRIEF_SCHEMA_ID,
        "schema_version": _record_version(ids),
        "document_type": BRIEF_TYPE,
        "intent": _intent(PREPARE, ids),
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


def _return_basis(action: str, ids: dict[str, str], events: list[dict], ctx: AssayContext) -> tuple:
    """Return the projection, Candidate, Assay, brief registration and Task a return of either outcome cites.

    Refuses before registration unless the return comes from the Task and Attempt the brief was issued
    to, and the Assay is still collecting evidence.
    """
    projection, candidate, assay = _subjects(ids, events, ctx)
    prepared = _completed(PREPARE, ids, events, ctx)
    registration = next(event for event in events if event["event_id"] == prepared["effects"][0]["event_id"])
    brief = _read_document(_BRIEF, registration, ctx)
    task = _task_provenance(ids["candidate_id"], events, ctx)
    if task != brief["task"]:
        raise IntegrityError(f"{action} must come from the Task and Attempt the brief was issued to")
    if assay.get("status") != "evidence_collecting" or candidate.get("status") != "assay_pending":
        raise IntegrityError(f"{action} requires an Assay that is still collecting evidence")
    return projection, candidate, assay, registration, task


def _operator_return(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str, evidence: dict
) -> dict:
    """Derive the operator return from a ledger prefix and the operator's content."""
    projection, candidate, assay, registration, task = _return_basis(RETURN, ids, events, ctx)
    scorecard = _scorecard(ids, projection, candidate, assay, evidence, ctx)
    document = {
        "schema_id": RETURN_SCHEMA_ID,
        "schema_version": _record_version(ids),
        "document_type": RETURN_TYPE,
        "intent": _intent(RETURN, ids),
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


def _partial_artifact(
    ids: dict[str, str], projection: dict, candidate: dict, assay: dict, evidence: dict, ctx: AssayContext
) -> dict[str, Any]:
    """Derive the Assay Partial from the Assay's bar and the operator's Partial judgements.

    Every reference is derived. The inherited Partial binding rule, and the Assay-bar check
    admission makes with it (``DiscoveryRuntime._valid_assay_partial``), run before the return is
    registered, so an inadmissible Partial is refused before any durable mutation.
    """
    bar = projection["assay_bar_authority"]
    acceptance = bar.get("acceptance")
    if (
        bar.get("status") != "accepted"
        or not isinstance(acceptance, dict)
        or assay.get("assay_bar_acceptance_sha256") != bar.get("acceptance_sha256")
    ):
        raise IntegrityError(f"{RETURN_PARTIAL} requires the Assay's accepted bar")
    artifact = {
        "schema_id": _ASSAY_PARTIAL_SCHEMA_ID,
        "schema_version": "1.0.0",
        "assay_id": ids["assay_id"],
        "candidate_ref": _record_ref(ids["candidate_id"], candidate["revision"], candidate["content_sha256"]),
        "rubric_ref": acceptance["rubric_ref"],
        "scope_ref": acceptance["scope_ref"],
        "assay_bar_acceptance_ref": _record_ref(acceptance["decision_id"], 1, bar["acceptance_sha256"]),
        "assay_relation_hash": assay["producer_relation_sha256"],
        **{key: deepcopy(evidence[key]) for key in _PARTIAL_JUDGEMENTS},
    }
    _validate(_ASSAY_PARTIAL_SCHEMA_ID, artifact, ctx)
    payload = {
        "candidate_id": ids["candidate_id"],
        "assay_id": ids["assay_id"],
        "partial_sha256": sha256_hex(canonical_bytes(artifact)),
    }
    if not _assay_partial_bindings_match(artifact, payload, candidate, assay, bar, acceptance):
        raise IntegrityError(
            f"{RETURN_PARTIAL} Partial would not be admitted: its axes must partition the rubric's required axes"
        )
    return artifact


def _operator_partial_return(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str, evidence: dict
) -> dict:
    """Derive the operator Partial return from a ledger prefix and the operator's content."""
    projection, candidate, assay, registration, task = _return_basis(RETURN_PARTIAL, ids, events, ctx)
    partial = _partial_artifact(ids, projection, candidate, assay, evidence, ctx)
    document = {
        "schema_id": PARTIAL_RETURN_SCHEMA_ID,
        "schema_version": _record_version(ids),
        "document_type": PARTIAL_RETURN_TYPE,
        "intent": _intent(RETURN_PARTIAL, ids),
        "recorded_at": recorded_at,
        "producer_actor_id": actor_id,
        "causal_prefix": _causal_prefix(events, ctx),
        "route_id": _ROUTE_IDENTITY,
        "brief": registration_ref(registration),
        "task": task,
        "candidate": {key: candidate[key] for key in ("candidate_id", "revision", "content_sha256")},
        "assay": {"assay_id": ids["assay_id"]},
        "operator_partial_return": deepcopy(evidence),
        "partial_artifact": partial,
        "partial_sha256": sha256_hex(canonical_bytes(partial)),
        "governed_code_subject": _governed_code_subject(events),
    }
    _validate(PARTIAL_RETURN_SCHEMA_ID, document, ctx)
    return document


def _promoted_assay(ids: dict[str, str], events: list[dict], ctx: AssayContext) -> tuple[dict, dict, dict, dict]:
    """Return the projection, the Candidate, its promoted Assay and the PROMOTE Decision that opened it.

    The Spike follows the Assay the Candidate carries, and that Assay must be one this route decided:
    its ordinal is recovered from the Candidate's lineage and its ``decide_spec_01`` must be completed
    (P-058, 2026-09-18). A Candidate promoted outside the route is therefore not a SPEC-02 subject.
    """
    projection = _projection(events, ctx)
    candidate = projection["candidates"].get(ids["candidate_id"])
    if not isinstance(candidate, dict):
        raise IntegrityError(f"the SPEC-02 route requires a registered Candidate: {ids['candidate_id']}")
    assay = projection["assays"].get(candidate.get("assay_id"))
    decision = projection["decisions"].get(candidate.get("decision_id"))
    if (
        not isinstance(assay, dict)
        or not isinstance(decision, dict)
        or decision.get("selected_option") != "PROMOTE"
        or candidate.get("promotion_gate") != _GATE
    ):
        raise IntegrityError(f"the SPEC-02 route requires a Candidate the owner promoted at the {_GATE} gate")
    ordinal = 1
    while True:
        lineage = {"candidate_id": ids["candidate_id"], **({"assay_ordinal": ordinal} if ordinal > 1 else {})}
        spec_01 = subject_ids(ctx.project_id, {"action": DECIDE, **lineage})
        if spec_01["assay_id"] == candidate.get("assay_id"):
            break
        if spec_01["assay_id"] not in projection["assays"]:
            raise IntegrityError("the SPEC-02 route requires the Candidate's promoted Assay to be this route's own")
        ordinal += 1
    # The decide intent carries the proposal's recommendation, which the route recovers as its listing does.
    proposal = _one(events, spec_01["decision_id"], "DecisionProposed")
    _completed(DECIDE, spec_01, events, ctx, recommendation=(proposal.get("payload") or {}).get("recommendation"))
    return projection, candidate, assay, decision


def _promotion_ref(candidate: dict, decision: dict) -> dict[str, Any]:
    """Return the exact reference to the OR-013 PROMOTE Decision that authorized Spike planning."""
    return _record_ref(candidate["decision_id"], decision["proposal_version"], decision["proposal_event_hash"])


def _live_run_approval(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str, evidence: dict
) -> dict:
    """Derive the owner's SPEC-02 live-run approval from a ledger prefix (P-058, 2026-09-18).

    The approval binds the promoted Candidate, its Assay, that Assay's PROMOTE Decision, the approved
    SPEC-02 route source, the approved scope and the cost ceiling a Spike plan may not exceed. It is a
    record only: no Candidate state changes when it is registered.
    """
    _, candidate, assay, decision = _promoted_assay(ids, events, ctx)
    if candidate.get("status") != "spike_planning_authorized":
        raise IntegrityError(f"{APPROVE_02} requires a Candidate that is authorized for Spike planning")
    document = {
        "schema_id": APPROVAL_SCHEMA_ID,
        "schema_version": "1.0.0",
        "document_type": APPROVAL_TYPE,
        "intent": _intent(APPROVE_02, ids),
        "recorded_at": recorded_at,
        "producer_actor_id": actor_id,
        "causal_prefix": _causal_prefix(events, ctx),
        "route_id": _ROUTE_IDENTITY,
        "route_source": _route_source(ctx, _SPEC_02_ALIAS, APPROVE_02),
        # The approval is registered inside the Spike's governed Attempt, whose provenance its manifest records.
        "task": _task_provenance(ids["candidate_id"], events, ctx),
        "candidate": {key: candidate[key] for key in ("candidate_id", "revision", "content_sha256")},
        "assay": {"assay_id": candidate["assay_id"], "scorecard_sha256": assay.get("scorecard_sha256")},
        "promotion_decision": {
            "decision_id": candidate["decision_id"],
            "record_revision": decision.get("proposal_version"),
            "content_hash": decision.get("proposal_event_hash"),
            "selected_option": "PROMOTE",
            "gate": _GATE,
        },
        "scope": evidence["scope"],
        "cost_ceiling": deepcopy(evidence["cost_ceiling"]),
        "governed_code_subject": _governed_code_subject(events),
    }
    _validate(APPROVAL_SCHEMA_ID, document, ctx)
    # The approval binds the SPEC-02 contract, so its ceiling states every limit that contract sets.
    if not _within_ceiling(document["cost_ceiling"], _SPEC_02_LIMITS):
        raise IntegrityError(f"{APPROVE_02} cost ceiling exceeds the SPEC-02 contract's resource limits")
    return document


def _spec_02_brief(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str, recorded_at: str
) -> dict:
    """Derive the Spike's operator brief, which cites the owner's approval and the promoted Assay."""
    _completed(APPROVE_02, ids, events, ctx)
    _, candidate, assay, decision = _promoted_assay(ids, events, ctx)
    if candidate.get("status") != "spike_planning_authorized":
        raise IntegrityError(f"{PREPARE_02} requires a Candidate that is authorized for Spike planning")
    registration = _one(events, ids["approval_id"], "ArtefactRegistered")
    approval = _read_document(_APPROVAL, registration, ctx)
    document = {
        "schema_id": SPEC_02_BRIEF_SCHEMA_ID,
        "schema_version": "1.0.0",
        "document_type": SPEC_02_BRIEF_TYPE,
        "intent": _intent(PREPARE_02, ids),
        "recorded_at": recorded_at,
        "producer_actor_id": actor_id,
        "causal_prefix": _causal_prefix(events, ctx),
        "route_id": _ROUTE_IDENTITY,
        "brief_source": _route_source(ctx, _SPEC_02_ALIAS, PREPARE_02),
        "task": _task_provenance(ids["candidate_id"], events, ctx),
        "candidate": {key: candidate[key] for key in ("candidate_id", "revision", "content_sha256")},
        "assay": {
            "assay_id": candidate["assay_id"],
            "scorecard_sha256": assay.get("scorecard_sha256"),
            "promotion_decision": _promotion_ref(candidate, decision),
        },
        "approval": {
            "artefact_id": ids["approval_id"],
            "content_sha256": ((registration.get("payload") or {}).get("manifest") or {}).get("content_sha256"),
            "scope": approval["scope"],
            "cost_ceiling": deepcopy(approval["cost_ceiling"]),
        },
        "governed_code_subject": _governed_code_subject(events),
    }
    _validate(SPEC_02_BRIEF_SCHEMA_ID, document, ctx)
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
    if row == _SPEC_02_BRIEF:
        return _spec_02_brief(ids, events, ctx, actor_id=actor_id, recorded_at=recorded_at)
    if row == _APPROVAL:
        return _live_run_approval(ids, events, ctx, actor_id=actor_id, recorded_at=recorded_at,
                                  evidence=evidence or {})  # fmt: skip
    build = _operator_partial_return if row == _PARTIAL_RETURN else _operator_return
    return build(ids, events, ctx, actor_id=actor_id, recorded_at=recorded_at, evidence=evidence or {})


def _record_identity(row: str) -> tuple[str, str, str]:
    """Return an operator record row's object kind, document type and schema."""
    if row == _BRIEF:
        return BRIEF_KIND, BRIEF_TYPE, BRIEF_SCHEMA_ID
    if row == _RETURN:
        return RETURN_KIND, RETURN_TYPE, RETURN_SCHEMA_ID
    if row == _APPROVAL:
        return APPROVAL_KIND, APPROVAL_TYPE, APPROVAL_SCHEMA_ID
    if row == _SPEC_02_BRIEF:
        return SPEC_02_BRIEF_KIND, SPEC_02_BRIEF_TYPE, SPEC_02_BRIEF_SCHEMA_ID
    return PARTIAL_RETURN_KIND, PARTIAL_RETURN_TYPE, PARTIAL_RETURN_SCHEMA_ID


def _stored(row: str, artefact_id: str, ctx: AssayContext) -> dict | None:
    """Return an operator record's immutable bytes, or None. Each kind is named literally (06i)."""
    if row == _BRIEF:
        if not ctx.objects.revision_exists(BRIEF_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(BRIEF_KIND, artefact_id, 1)
    elif row == _RETURN:
        if not ctx.objects.revision_exists(RETURN_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(RETURN_KIND, artefact_id, 1)
    elif row == _APPROVAL:
        if not ctx.objects.revision_exists(APPROVAL_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(APPROVAL_KIND, artefact_id, 1)
    elif row == _SPEC_02_BRIEF:
        if not ctx.objects.revision_exists(SPEC_02_BRIEF_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(SPEC_02_BRIEF_KIND, artefact_id, 1)
    else:
        if not ctx.objects.revision_exists(PARTIAL_RETURN_KIND, artefact_id, 1):
            return None
        document = ctx.objects.read(PARTIAL_RETURN_KIND, artefact_id, 1)
    _validate(_record_identity(row)[2], document, ctx)
    return document


def _read_document(row: str, registration: dict, ctx: AssayContext) -> dict:
    artefact_id = registration["stream_id"]
    document = _stored(row, artefact_id, ctx)
    if document is None:
        raise IntegrityError(f"SPEC operator record bytes are absent for its registration: {artefact_id}")
    manifest = (registration.get("payload") or {}).get("manifest") or {}
    raw = canonical_bytes(document)
    kind = _record_identity(row)[0]
    if (
        manifest.get("content_sha256") != sha256_hex(raw)
        or manifest.get("size_bytes") != len(raw)
        or manifest.get("relative_path") != f"objects/{kind}/{artefact_id}/00000001-{sha256_hex(raw)}.json"
    ):
        raise IntegrityError(f"SPEC operator record registration and immutable bytes disagree: {artefact_id}")
    return document


def _manifest(row: str, document: dict[str, Any], artefact_id: str) -> dict[str, Any]:
    kind, document_type, schema_id = _record_identity(row)
    raw = canonical_bytes(document)
    digest = sha256_hex(raw)
    task = document["task"]
    if row in {_BRIEF, _APPROVAL}:
        inputs: list[dict[str, Any]] = []
    elif row == _SPEC_02_BRIEF:
        # The Spike's brief depends on the owner's approval, not on a SPEC-01 operator brief.
        inputs = [
            {
                "input_artefact_id": document["approval"]["artefact_id"],
                "input_content_sha256": document["approval"]["content_sha256"],
                "dependency_role": "spec_02_live_run_approval",
            }
        ]
    else:
        inputs = [
            {
                "input_artefact_id": document["brief"]["artefact_id"],
                "input_content_sha256": document["brief"]["content_sha256"],
                "dependency_role": "operator_brief",
            }
        ]
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
        "artefact_schema_version": document["schema_version"],
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
    if row in {"OR-014", "OR-015", "OR-016", "OR-017"}:
        # A Spike row names no Assay of its own: it follows the Candidate's promoted Assay.
        return _spike_start(row, ids, events, ctx, actor_id=actor_id, grant_id=grant_id, evidence=evidence)
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
    if row == "OR-005":
        document = _read_document(_PARTIAL_RETURN, _one(events, ids["return_id"], "ArtefactRegistered"), ctx)
        if not _same_record(evidence, document["operator_partial_return"]):
            raise IntegrityError(
                f"{RETURN_PARTIAL} Assay producer must supply the exact operator Partial return that was registered"
            )
        _, _, assay = _subjects(ids, events, ctx)
        return {
            "row_id": "OR-005",
            **subject,
            "producer_relation_sha256": assay["producer_relation_sha256"],
            "partial_sha256": document["partial_sha256"],
            "partial_artifact": document["partial_artifact"],
        }
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
    if row in {"OR-034", "OR-035"}:
        partial = row == "OR-035"
        _completed(RETURN_PARTIAL if partial else RETURN, ids, events, ctx)
        _, _, assay = _subjects(ids, events, ctx)
        if partial and assay.get("status") != "partial_recorded":
            raise IntegrityError(f"{REVIEW_PARTIAL} requires a Partial Assay")
        if not partial and assay.get("status") != "scored":
            raise IntegrityError(f"{REVIEW} requires a scored Assay")
        digest = assay["outcome_sha256" if partial else "scorecard_sha256"]
        returned = _one(events, ids["return_id"], "ArtefactRegistered")
        scored = _one(events, ids["assay_id"], "AssayPartialRecorded" if partial else "AssayScored")
        subject_label, return_label = (
            ("assay-partial", "operator-partial-return") if partial else ("scorecard", "operator-return")
        )
        return {
            "row_id": row,
            **subject,
            "review_id": ids["review_id"],
            "subject_sha256": digest,
            "review_contract": {
                "review_type": "provenance",
                "new_review_id": ids["review_id"],
                "subject_ids": [ids["assay_id"]],
                "subject_hashes": [digest],
                "governing_refs": [f"W11:{row}", f"{_ROUTE_IDENTITY}:{_BRIEF_ALIAS}"],
                "review_questions": [
                    f"Is the {'Partial' if partial else 'scorecard'} exactly the one the operator returned against the "
                    "issued brief and the accepted Assay bar?"
                ],
                "required_evidence_refs": [
                    f"{subject_label}:{digest}",
                    f"{return_label}:{returned['payload']['manifest']['content_sha256']}",
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
    if row in {"OR-006", "OR-007"}:
        partial = row == "OR-007"
        projection, _, _ = _subjects(ids, events, ctx)
        review = projection["reviews"].get(ids["review_id"])
        if not isinstance(review, dict) or review.get("status") != "pending":
            raise IntegrityError(f"{REVIEW_PARTIAL if partial else REVIEW} requires its pending outcome review")
        registration = _one(events, ids["return_id"], "ArtefactRegistered")
        returned = _read_document(_PARTIAL_RETURN if partial else _RETURN, registration, ctx)
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
            "row_id": row,
            **subject,
            "review_id": ids["review_id"],
            "subject_sha256": review["subject_sha256"],
            "verdict": "approve",
            "review_verdict": verdict,
        }
    if row == "OR-012":
        # OR-012 requires a scored, reviewed Assay; a reviewed Partial is revisited instead (P-058, 2026-09-17).
        if _return_taken(ids, events) == RETURN_PARTIAL:
            raise IntegrityError(f"{DECIDE} cannot decide a Partial Assay: its Candidate is revisited instead")
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
    if row == "OR-009":
        return _revisit_payload(ids, events, ctx, actor_id=actor_id)
    if row == "OR-010":
        _completed(REVISIT, ids, events, ctx)
        decision = _projection(events, ctx)["decisions"].get(ids["revisit_decision_id"])
        if not isinstance(decision, dict) or decision.get("status") != "proposed":
            raise IntegrityError(f"{AUTHORIZE} requires its proposed revisit Decision")
        proposal = _one(events, ids["revisit_decision_id"], "DecisionProposed")
        return {
            "row_id": "OR-010",
            **subject,
            "decision_id": ids["revisit_decision_id"],
            "w2_payload": {
                "decision_id": ids["revisit_decision_id"],
                # The route authorizes only a retry; a revisit PARK or KILL is not a route action.
                "selected_option": "RETRY",
                "effective_scope": "exact Discovery subject",
                "decision_revision": 1,
                "deciding_actor_id": actor_id,
                "decision_authority_grant_id": grant_id,
                "governing_evidence_refs": list(proposal["payload"]["governing_evidence_refs"]),
                "considered_review_ids": [ids["review_id"]],
                "effective_at": _time(proposal["recorded_at"]),
                "permitted_commands": ["RequestAssay"],
                "superseded_decision_ids": [],
                "conditions": [],
                "revisit_triggers": [],
            },
        }
    if row == "OR-011":
        _completed(AUTHORIZE, ids, events, ctx)
        projection, candidate, assay = _subjects(ids, events, ctx)
        bar = projection["assay_bar_authority"]
        if assay.get("status") != "retry_authorized" or candidate.get("status") != "assay_retry_authorized":
            raise IntegrityError(f"{RETRY_REQUEST} requires an Assay whose retry the owner authorized")
        if bar.get("status") != "accepted":
            raise IntegrityError(f"{RETRY_REQUEST} requires an accepted Assay bar")
        return {
            "row_id": "OR-011",
            "candidate_id": ids["candidate_id"],
            "old_assay_id": ids["assay_id"],
            "assay_id": ids["retry_assay_id"],
            "candidate_revision": candidate["revision"],
            "candidate_sha256": candidate["content_sha256"],
            "assay_bar_acceptance_sha256": bar["acceptance_sha256"],
            "producer_relation_sha256": bar["producer_relation_sha256"],
        }
    raise IntegrityError(f"the Assay route has no payload for row {row}")


def _within_ceiling(box: Any, ceiling: Any) -> bool:
    """Whether a plan's time and resource box stays inside the owner's approved cost ceiling.

    Each limit the ceiling sets binds the plan, which must state it at or under the ceiling, so a plan
    cannot escape a limit by omitting it; a limit the ceiling leaves open is the plan's own. Network
    access needs the ceiling's permission.
    """
    if not isinstance(box, dict) or not isinstance(ceiling, dict):
        return False
    for key in ("time_limit_seconds", "worker_limit", "memory_limit_mb", "storage_limit_mb"):
        if key in ceiling and (not isinstance(box.get(key), int) or box[key] > ceiling[key]):
            return False
    return not box.get("network_access") or ceiling.get("network_access") is True


def _execution_pair(ids: dict[str, str], events: list[dict], ctx: AssayContext) -> tuple[str, dict, dict]:
    """Return the Task's running Attempt and the live Lease OR-017 binds, as held at this ledger prefix."""
    task = _task_provenance(ids["candidate_id"], events, ctx)
    state = ctx.operational_state(events)
    attempt = state.get(task["attempt_id"])
    lease = state.get((attempt or {}).get("lease_id")) if isinstance(attempt, dict) else None
    if (
        not isinstance(attempt, dict)
        or attempt.get("status") != "running"
        or not isinstance(lease, dict)
        or lease.get("status") != "active"
        or lease.get("attempt_id") != task["attempt_id"]
    ):
        raise IntegrityError(f"{START_02} requires the Task's running Attempt to hold its active Lease")
    return task["attempt_id"], attempt, lease


def _execution_relation(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, candidate: dict, assay: dict, spike: dict
) -> dict[str, Any]:
    """Derive the Spike execution-authority relation, which names the owner as its deciding actor."""
    _, _, lease = _execution_pair(ids, events, ctx)
    resource_id = lease.get("resource_grant_id")
    resource = ctx.operational_state(events).get(resource_id)
    if not isinstance(resource, dict):
        raise IntegrityError(f"{START_02} requires the resource grant the Lease holds")
    plan_ref = _record_ref(ids["spike_id"], 1, spike.get("plan_sha256"))
    return {
        "schema_id": _SPIKE_EXECUTION_RELATION,
        "schema_version": "1.0.0",
        "relation_kind": "spike_execution_authority",
        "decision_id": ids["execution_decision_id"],
        "spike_ref": plan_ref,
        "candidate_ref": _record_ref(candidate["candidate_id"], candidate["revision"], candidate["content_sha256"]),
        "plan_ref": plan_ref,
        "resource_ref": _record_ref(resource_id, 1, sha256_hex(canonical_bytes(resource))),
        "route_ref": plan_ref,
        "assurance_ref": _record_ref(candidate["assay_id"], 1, assay.get("scorecard_sha256")),
        "selected_option": "AUTHORIZE",
        "actor_id": _owner(events, ctx),
    }


def _spike_plan(
    ids: dict[str, str], events: list[dict], ctx: AssayContext, subjects: tuple[dict, dict, dict], evidence: dict
) -> dict[str, Any]:
    """Derive the Spike plan from the operator's content, the promoted Assay and the owner's approval."""
    candidate, assay, decision = subjects
    approval = _read_document(_APPROVAL, _one(events, ids["approval_id"], "ArtefactRegistered"), ctx)
    if not _within_ceiling(evidence.get("time_resource_box"), approval["cost_ceiling"]):
        raise IntegrityError(f"{START_02} plan exceeds the owner's approved cost ceiling")
    assay_ref = _record_ref(candidate["assay_id"], 1, assay.get("scorecard_sha256"))
    artifact = {
        "schema_id": _SPIKE_PLAN_SCHEMA_ID,
        "schema_version": "1.0.0",
        "spike_id": ids["spike_id"],
        "candidate_ref": _record_ref(candidate["candidate_id"], candidate["revision"], candidate["content_sha256"]),
        "originating_assay_ref": assay_ref,
        "source_scorecard_refs": [assay_ref],
        "assay_promotion_decision_ref": _promotion_ref(candidate, decision),
        "required_approving_authority": _owner(events, ctx),
        # The Spike runs the scope the owner approved, not a scope the caller restates.
        "scope": approval["scope"],
        **{key: deepcopy(evidence[key]) for key in _SPIKE_PLAN_FIELDS},
    }
    _validate(_SPIKE_PLAN_SCHEMA_ID, artifact, ctx)
    return artifact


def _spike_start(
    row: str,
    ids: dict[str, str],
    events: list[dict],
    ctx: AssayContext,
    *,
    actor_id: str | None,
    grant_id: str | None,
    evidence: dict | None,
) -> dict[str, Any]:
    """Return the exact payload for one row of ``start_spec_02`` (W11 OR-014 to OR-017)."""
    _completed(PREPARE_02, ids, events, ctx)
    projection, candidate, assay, decision = _promoted_assay(ids, events, ctx)
    subject = {"row_id": row, "candidate_id": ids["candidate_id"], "spike_id": ids["spike_id"]}
    if row == "OR-014":
        if candidate.get("status") != "spike_planning_authorized":
            raise IntegrityError(f"{START_02} requires a Candidate that is authorized for Spike planning")
        plan = _spike_plan(ids, events, ctx, (candidate, assay, decision), evidence or {})
        return {**subject, "plan_sha256": sha256_hex(canonical_bytes(plan)), "plan_artifact": plan}
    spike = projection["spikes"].get(ids["spike_id"])
    if not isinstance(spike, dict) or spike.get("candidate_id") != ids["candidate_id"]:
        raise IntegrityError(f"{START_02} requires the Spike its own plan registered")
    if row == "OR-017":
        attempt_id, attempt, lease = _execution_pair(ids, events, ctx)
        return {
            **subject,
            "attempt_id": attempt_id,
            "attempt_sha256": sha256_hex(canonical_bytes(attempt)),
            "lease_id": attempt["lease_id"],
            "resource_grant_id": lease["resource_grant_id"],
        }
    payload = {
        **subject,
        "decision_id": ids["execution_decision_id"],
        "execution_authority_relation": _execution_relation(ids, events, ctx, candidate, assay, spike),
    }
    planned = _one(events, ids["spike_id"], "SpikePlanned")
    if row == "OR-015":
        return {
            **payload,
            "w2_payload": {
                "question": "spike_execution",
                "recommendation": "approve",
                "new_decision_id": ids["execution_decision_id"],
                "decision_revision": 1,
                "decision_kind": "design_lock",
                "options": ["approve", "reject"],
                "governing_evidence_refs": [f"approval:{ids['approval_id']}"],
                "affected_task_ids": [],
                "affected_claim_ids": [],
                "required_authority": "owner",
                "expires_at": _time(planned["recorded_at"], _REVIEW_WINDOW),
                "review_date": _time(planned["recorded_at"]),
                "consequences": ["authorize the approved bounded Spike"],
            },
        }
    proposal = _one(events, ids["execution_decision_id"], "DecisionProposed")
    return {
        **payload,
        "w2_payload": {
            "decision_id": ids["execution_decision_id"],
            "selected_option": "approve",
            "effective_scope": "exact Discovery subject",
            "decision_revision": 1,
            "deciding_actor_id": actor_id,
            "decision_authority_grant_id": grant_id,
            "governing_evidence_refs": list(proposal["payload"]["governing_evidence_refs"]),
            "considered_review_ids": [],
            "effective_at": _time(proposal["recorded_at"]),
            "permitted_commands": ["StartSpike"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": [],
        },
    }


def _route_source_observation(
    observation_id: str, observation: dict, events: list[dict], projection: dict, ctx: AssayContext
) -> bool:
    """Whether an observation is the one the SOURCE route completed for its own ``observe_source`` intent.

    It must cite exactly one SOURCE registration whose document's intent derives this observation's
    identity, and the SOURCE route's own completion check must accept that intent over the same ledger:
    the exact batch that route derives, its registration and the Candidate it registers (PR #297 review).
    """
    batch = observation.get("batch") or {}
    refs = batch.get("raw_source_refs") or []
    if len(refs) != 1 or not str(refs[0].get("locator", "")).startswith(SOURCE_REF_PREFIX):
        return False
    try:
        document, _ = ctx.read_source_document(refs[0]["locator"][len(SOURCE_REF_PREFIX) :].partition(":")[0])
        intent = document.get("intent") or {}
        return bool(
            intent.get("action") == "observe_source"
            and source_ids(ctx.project_id, intent)["observation_id"] == observation_id
            and ctx.source_state(intent, events, projection)["state"] == "completed"
        )
    except (ArsError, KeyError, TypeError):
        return False


def _revisit_payload(ids: dict[str, Any], events: list[dict], ctx: AssayContext, *, actor_id: str | None) -> dict:
    """Derive the OR-009 revisit proposal of a route-reviewed Partial Assay (P-058, 2026-09-17).

    The predicate is the earliest route-issued SOURCE observation, later than the outcome review
    verdict and any PARK, whose facts contain every revisit requirement. The caller names none.
    """
    _completed(REVIEW_PARTIAL, ids, events, ctx)
    projection, candidate, assay = _subjects(ids, events, ctx)
    review = projection["reviews"].get(ids["review_id"])
    requirements = assay.get("revisit_requirements")
    if assay.get("status") != "partial_reviewed" or not isinstance(review, dict) or not requirements:
        raise IntegrityError(f"{REVISIT} requires a reviewed Partial Assay")
    verdict = _one(events, ids["review_id"], "ReviewVerdictRecorded")
    threshold = max(verdict["global_position"], candidate.get("parked_at_global_position") or 0)
    excluded = {ids["candidate_id"], ids["assay_id"], ids["review_id"]}
    observations = sorted(projection["source_observations"].items(), key=lambda item: item[1]["global_position"])
    predicate_id = next(
        (
            observation_id
            for observation_id, observation in observations
            if observation["global_position"] > threshold
            and observation_id not in excluded
            and set(requirements) <= set((observation.get("batch") or {}).get("matching_facts") or ())
            and _route_source_observation(observation_id, observation, events, projection, ctx)
        ),
        None,
    )
    if predicate_id is None:
        raise IntegrityError(
            f"{REVISIT} revisit predicate is not satisfied: no later route SOURCE observation carries every "
            "revisit requirement"
        )
    predicate = projection["source_observations"][predicate_id]
    observed = _one(events, predicate_id, "ScoutObservationIngested")
    decision_id = ids["revisit_decision_id"]
    return {
        "row_id": "OR-009",
        "candidate_id": ids["candidate_id"],
        "assay_id": ids["assay_id"],
        "review_id": ids["review_id"],
        "decision_id": decision_id,
        "w2_payload": {
            "question": "Retry the exact SPEC-01 Assay?",
            "recommendation": "RETRY",
            "new_decision_id": decision_id,
            "decision_revision": 1,
            "decision_kind": "design_lock",
            "options": ["RETRY", "PARK", "KILL"],
            "governing_evidence_refs": [ids["review_id"]],
            "affected_task_ids": [],
            "affected_claim_ids": [],
            "required_authority": "owner",
            "expires_at": _time(observed["recorded_at"], _REVIEW_WINDOW),
            "review_date": _time(observed["recorded_at"]),
            "consequences": ["authorize an exact Assay retry"],
        },
        "revisit_relation": {
            "schema_id": "ars://portfolio/relation/discovery-revisit",
            "schema_version": "1.0.0",
            "relation_kind": "discovery_revisit",
            "decision_id": decision_id,
            "candidate_ref": _record_ref(ids["candidate_id"], candidate["revision"], candidate["content_sha256"]),
            "prior_aggregate_ref": _record_ref(ids["assay_id"], assay["version"], _aggregate_content_hash(assay)),
            "prior_outcome_review_ref": _review_ref(review),
            "satisfied_revisit_predicate_ref": _record_ref(predicate_id, 1, predicate["content_sha256"]),
            "selected_option": "RETRY",
            "actor_id": actor_id,
        },
    }


def _check_relation(row: str, ids: dict[str, str], events: list[dict], ctx: AssayContext, *, actor_id: str) -> None:
    """Refuse the role collapses inherited admission was measured to accept (P-058 amendment)."""
    if row == "OR-140" and actor_id != _owner(events, ctx):
        raise IntegrityError(f"{GENESIS} requires the authority owner as its actor")
    if row == "OR-105":
        authors = {_content(ctx, path).get("created_by_actor_id") for path in (ASSAY_RUBRIC_PATH, ASSAY_SCOPE_PATH)}
        if actor_id in authors:
            raise IntegrityError(f"{BAR} review requester must not be a content author")
    if row in {"OR-003", "OR-011"}:
        # A retry request was measured to accept the same collapses as the first request (P-058, 2026-09-17).
        bar = _projection(events, ctx)["assay_bar_authority"]
        producer = (bar.get("prospective_producer_ref") or {}).get("id")
        if row == "OR-003" and actor_id in {producer, _owner(events, ctx)}:
            raise IntegrityError(f"{REQUEST} Assay requester must be neither the prospective producer nor the owner")
        if row == "OR-011" and actor_id in {producer, _owner(events, ctx)}:
            raise IntegrityError(
                f"{RETRY_REQUEST} retry requester must be neither the prospective producer nor the owner"
            )
    if row in {_APPROVAL, "OR-014", "OR-015"}:
        # Measured (P-058, 2026-09-18): admission accepts the plan from the steward, the producer, the
        # owner and an unrelated human, and its execution proposal from the producer, the owner and the
        # steward, so the route refuses the collapses. OR-016 stays owner-only by admission, and OR-017
        # binds the Lease holder. The route holds the live-run approval to the owner.
        bar = _projection(events, ctx)["assay_bar_authority"]
        producer = (bar.get("prospective_producer_ref") or {}).get("id")
        if row == _APPROVAL and actor_id != _owner(events, ctx):
            raise IntegrityError(f"{APPROVE_02} requires the authority owner as its actor")
        if row in {"OR-014", "OR-015"} and actor_id in {producer, _owner(events, ctx)}:
            raise IntegrityError(
                f"{START_02} Spike planning requires an actor who is neither the prospective producer nor the owner"
            )
    if row not in {"OR-034", "OR-035", "OR-006", "OR-007", "OR-012", "OR-009"}:
        return
    owner = _owner(events, ctx)
    producer = (_projection(events, ctx)["assays"].get(ids["assay_id"]) or {}).get("producer_actor_id")
    # The Partial review rows were measured to accept the same collapses (P-058, 2026-09-17).
    review = REVIEW_PARTIAL if row in {"OR-035", "OR-007"} else REVIEW
    if row in {"OR-034", "OR-035"} and actor_id in {producer, owner}:
        raise IntegrityError(f"{review} outcome-review requester must be neither the producer nor the owner")
    if row in {"OR-006", "OR-007"} and actor_id == owner:
        raise IntegrityError(f"{review} outcome reviewer must not be the owner")
    if row in {"OR-012", "OR-009"}:
        reviewers = {
            event["actor_id"]
            for event in events
            if event["stream_id"] == ids["review_id"] and event["event_type"] == "ReviewVerdictRecorded"
        }
        if row == "OR-012" and actor_id in {producer, owner, *reviewers}:
            raise IntegrityError(f"{DECIDE} proposer must be neither the producer, the reviewer nor the owner")
        if row == "OR-009" and actor_id in {producer, owner, *reviewers}:
            raise IntegrityError(
                f"{REVISIT} revisit proposer must be neither the producer, the outcome reviewer nor the owner"
            )


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
    """Recover the caller evidence an OR row carried, from its event or, for OR-004/005, the registered return."""
    if row == "OR-004":
        return _read_document(_RETURN, _one(prefix, ids["return_id"], "ArtefactRegistered"), ctx)["operator_return"]
    if row == "OR-005":
        registration = _one(prefix, ids["return_id"], "ArtefactRegistered")
        return _read_document(_PARTIAL_RETURN, registration, ctx)["operator_partial_return"]
    if row == "OR-014":
        # The Spike plan the row recorded carries the operator's own content verbatim.
        artifact = (event.get("payload") or {}).get("plan_artifact") or {}
        return {key: deepcopy(artifact.get(key)) for key in _SPIKE_PLAN_FIELDS}
    if row not in {"OR-006", "OR-007", "OR-013"}:
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


def _return_taken(ids: dict[str, str], events: list[dict]) -> str | None:
    """Return the return alternative whose route-keyed registration opens the Assay's return stream, if any.

    Both alternatives register at the same identity, and admission refuses a second registration there,
    so at most one is ever taken. This reads identity only; the taken action's own evaluation verifies it.
    A later Assay's registration is keyed by its ordinal, so each alternative is read at that ordinal.
    """
    first = next((event for event in events if event["stream_id"] == ids["return_id"]), None)
    if first is None or first.get("event_type") != "ArtefactRegistered":
        return None
    return next(
        (action for action in (RETURN, RETURN_PARTIAL) if _issued_registration(first, _intent(action, ids))), None
    )


def _located(intent: dict[str, Any], events: list[dict], ctx: AssayContext) -> list[tuple[str, list[dict]]]:
    """Return each row's first transaction on its stream, in route order, until one is absent."""
    ids = subject_ids(ctx.project_id, intent)
    found: list[tuple[str, list[dict]]] = []
    after = 0
    if intent["action"] == AUTHORIZE:
        # The authorization follows the revisit proposal on the same Decision stream.
        proposed = _located({**intent, "action": REVISIT}, events, ctx)
        if not proposed:
            return []
        after = max(e["global_position"] for e in proposed[-1][1])
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
        raise IntegrityError("a SPEC operator record cannot cite its own or a later registration")
    expected = _build(
        row,
        ids,
        [event for event in events if event["global_position"] <= position],
        ctx,
        actor_id=registration["actor_id"],
        recorded_at=document["recorded_at"],
        evidence=_document_evidence(row, document),
    )
    if document != expected:
        raise IntegrityError("a SPEC operator record is not the document this route derives")
    return document


def _document_evidence(row: str, document: dict[str, Any]) -> dict | None:
    """Recover the caller evidence a registered record carries, so the route re-derives it exactly."""
    if row == _APPROVAL:
        return {key: deepcopy(document[key]) for key in _APPROVAL_EVIDENCE}
    if row in {_BRIEF, _SPEC_02_BRIEF}:
        return None
    return document.get("operator_partial_return" if row == _PARTIAL_RETURN else "operator_return")


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
        ConflictError: If evidence this route did not issue sits on the action's streams, or the
            Assay took the other outcome alternative.
        IntegrityError: If route-keyed evidence breaks a relation the route enforces.
    """
    action = intent["action"]
    ids = subject_ids(ctx.project_id, intent)
    if action in _RETURN_OF:
        taken = _return_taken(ids, events)
        if taken not in {None, _RETURN_OF[action]}:
            raise ConflictError(f"{action} is excluded: this Assay's operator return was registered by {taken}")
    located = _located(intent, events, ctx)
    for row, transaction in located:
        _verify_effect(row, intent, ids, transaction[0], events, ctx)
    # Scan even while the action is partial: an effect this route did not issue can land on a stream
    # before the route reaches it, and appending past it can leave a later route effect inadmissible.
    if action in _OWNED_ROWS:
        owned = {_stream(row, ids, ctx) for row in _OWNED_ROWS[action]}
        issued = {event["event_id"] for _, transaction in located for event in transaction}
        if action in {REVISIT, AUTHORIZE}:
            # Each locates, and the other's own evaluation verifies, its effect on the shared Decision stream.
            partner = AUTHORIZE if action == REVISIT else REVISIT
            partner_located = _located({**intent, "action": partner}, events, ctx)
            issued |= {event["event_id"] for _, transaction in partner_located for event in transaction}
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
    payload = {"new_artefact_id": target, "manifest": _manifest(row, document, target)}
    return state["next_effect"], target, payload, (_record_identity(row)[0], document)


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
                # A record's caller evidence is in its bytes, not its retry key, so a registration that
                # takes evidence is a retry only of the exact evidence it recorded (PR #298 review).
                if row in _EVIDENCE:
                    registered = _document_evidence(row, _read_document(row, first, ctx))
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
    streams = {event["stream_id"] for event in events}
    lineages = dict.fromkeys(
        assay["candidate_id"] for assay in projection["assays"].values() if isinstance(assay.get("candidate_id"), str)
    )
    for candidate_id in lineages:
        # Walk the Candidate's route lineage: the requested Assay, then each Assay a route retry created.
        ordinal = 1
        while True:
            lineage = {"candidate_id": candidate_id, **({"assay_ordinal": ordinal} if ordinal > 1 else {})}
            ids = subject_ids(ctx.project_id, {"action": REVISIT, **lineage})
            if ids["assay_id"] not in projection["assays"]:
                break
            # Only the outcome alternative the route registered is a subject; the other one is excluded.
            taken = _return_taken(ids, events)
            outcome = (RETURN_PARTIAL, REVIEW_PARTIAL) if taken == RETURN_PARTIAL else (RETURN, REVIEW)
            actions = [*((REQUEST,) if ordinal == 1 else ()), PREPARE, *outcome]
            if ids["revisit_decision_id"] in streams:
                actions += [REVISIT, AUTHORIZE]
            if ids["retry_assay_id"] in projection["assays"]:
                actions.append(RETRY_REQUEST)
            for action in actions:
                candidates.append({"action": action, "reason": f"recorded route {action}", **lineage})
            proposal = next(
                (e for e in events if e["stream_id"] == ids["decision_id"] and e["event_type"] == "DecisionProposed"),
                None,
            )
            if proposal is not None and (proposal.get("payload") or {}).get("recommendation") in _NEXT_STATE:
                candidates.append(
                    {
                        "action": DECIDE,
                        "reason": "recorded route decision",
                        **lineage,
                        "recommendation": proposal["payload"]["recommendation"],
                    }
                )
            ordinal += 1
        # The Candidate's SPEC-02 subjects follow its promoted Assay; each is listed once its stream exists.
        spec_02 = subject_ids(ctx.project_id, {"action": START_02, "candidate_id": candidate_id})
        for action, stream in (
            (APPROVE_02, spec_02["approval_id"]),
            (PREPARE_02, spec_02["spec_02_brief_id"]),
            (START_02, spec_02["spike_id"]),
        ):
            if stream in streams:
                candidates.append(
                    {"action": action, "reason": f"recorded route {action}", "candidate_id": candidate_id}
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
