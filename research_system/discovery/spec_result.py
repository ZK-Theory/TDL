"""06s Phase 3 (P-057): the accepted project-use result on the SPEC route.

Two actions share one subject, the ProjectUseDecision artefact of one accepted Task.
``register_project_use_decision`` registers it under the owner, and
``accept_project_use_decision`` records an independent scientific review followed by
the owner's use authority. The result stays pending until both are complete.

Every reference in a decision is derived from the ledger by ``derive``, the single
function that builds a decision before registration and verifies it afterwards. The
caller supplies only the disposition, rationale, limitations, next gates, the D6
subset qualification and, when no Spike exists, a no_spike reason.

As in close_task, only evidence this route issued advances an action. Each located
event must carry the route's own retry key and the payload the route derives, and
nothing else may sit on the decision's artefact stream.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from research_system.artefacts.authority import ArtefactAuthorityContractLoader
from research_system.artefacts.runtime import ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT
from research_system.artefacts.use_resolver import predicate_reference
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import spec_task
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.spec_source import (
    CORRECTION_SCHEMA,
    SOURCE_REF_PREFIX,
    registration_ref,
    validate_source_refs,
)
from research_system.errors import ConflictError, IntegrityError
from research_system.methods.registration import _stable_command_id
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry

REGISTER = "register_project_use_decision"
ACCEPT = "accept_project_use_decision"
REGISTER_EFFECTS = ("RegisterArtefact",)
ACCEPT_EFFECTS = ("RecordScientificReview", "SetArtefactUseAuthority")
INTENT_SCHEMA_ID = "ars://portfolio/spec-project-use-intent"
DOCUMENT_SCHEMA_ID = "ars://portfolio/project-use-decision"
DOCUMENT_KIND = "project_use_decision_document"
DOCUMENT_TYPE = "project_use_decision"
_ROUTE_IDENTITY = "SPEC-GATE6-RUN-V1"
_BINDING_EVENTS = frozenset({"StoreBindingRepaired", "StoreBindingAdvanced"})
_REVIEW_EVIDENCE = frozenset({"review_id", "evidence_refs"})

# A Candidate is at a terminal owner Decision only in these (gate, option) states.
_TERMINAL_STATUS = {
    ("assay_to_spike", "PARK"): "parked",
    ("assay_to_spike", "KILL"): "killed",
    ("spike_to_preregistration", "PARK"): "parked",
    ("spike_to_preregistration", "KILL"): "killed",
    ("spike_to_preregistration", "PROMOTE"): "preregistration_authorized",
}
# P-050: a PARK never permits default adoption; a KILL permits only rejection.
_PERMITTED_DISPOSITIONS = {
    "PARK": frozenset({"retain_experimental_benchmark"}),
    "KILL": frozenset({"reject"}),
    "PROMOTE": frozenset({"adopt_default", "retain_experimental_benchmark"}),
}
# Route-authored wording. None of it may promote, adopt or claim replication for PARK.
_DISPOSITION_TEXT = {
    "retain_experimental_benchmark": (
        "Keep this method as an experimental or benchmark candidate only. It is not the "
        "project's default empirical method and not the basis of a scientific claim."
    ),
    "adopt_default": "Use this method as the project's default within the stated limitations.",
    "reject": "Do not use this method.",
}
_SUBSET_TEXT = (
    "This result proves the operational route on a bounded subset only. It does not "
    "reproduce the original study and does not establish a scientific claim."
)

_Validator = Callable[[dict[str, Any]], None] | None


@dataclass(frozen=True)
class RouteContext:
    """Stores and readers the result evaluator needs, fixed for one invocation.

    Attributes:
        project_id: Bound project identity.
        objects: Immutable object store holding decision documents.
        schemas: Runtime schema registry.
        validator: Inherited authority-state validator for replay.
        raw_prefix_sha256: Ledger raw-prefix digest at a global position.
        read_source_document: Validated SOURCE document reader by artefact identity.
        check_review_evidence: Inherited governing-review rule over a prospective review
            (registration, review payload, use payload, reviewer, time); raises if the
            evidence could never govern use authority.
    """

    project_id: str
    objects: Any
    schemas: SchemaRegistry
    validator: _Validator
    raw_prefix_sha256: Callable[[int], str]
    read_source_document: Callable[[str], tuple[dict, dict]]
    check_review_evidence: Callable[[dict, dict, dict, str, str], None]


def subject_id(project_id: str, task_id: str) -> str:
    """Return the ProjectUseDecision artefact identity for one Task.

    Args:
        project_id: Bound project identity.
        task_id: The accepted operational Task.

    Returns:
        The deterministic ``art_`` identity; one decision exists per Task.
    """
    key = canonical_bytes([project_id, task_id, DOCUMENT_TYPE]).decode()
    return "art" + _stable_command_id(key)[3:]


def key_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Return the part of an intent that identifies its effects.

    Free text is excluded, as in close_task; registered content is bound by the
    manifest hash inside the payload instead.

    Args:
        intent: Validated project-use intent.

    Returns:
        The action and Task identity only.
    """
    return {"action": intent["action"], "task_id": intent["task_id"]}


def retry_key(intent: dict[str, Any], effect: str, actor_id: str, grant_id: str, payload: dict) -> str:
    """Return the retry key ``SpecCoordinator._submit_effect`` derives for one effect.

    Args:
        intent: Project-use intent (only its key part is used).
        effect: Effect name.
        actor_id: Actor recorded on the command.
        grant_id: Authority grant recorded on the command.
        payload: Exact submitted payload.

    Returns:
        The idempotency key the route submits the effect under.
    """
    return "spec:" + sha256_hex(canonical_bytes([key_intent(intent), effect, actor_id, grant_id, payload]))


def _event_ref(event: dict) -> dict[str, Any]:
    return {key: event[key] for key in ("event_id", "event_hash", "global_position")}


def _summary(event: dict) -> dict[str, Any]:
    return {key: event[key] for key in ("event_id", "event_hash", "command_id", "actor_id", "authority_grant_id")}


def _registration(events: list[dict], artefact_id: str) -> dict:
    matches = [e for e in events if e["event_type"] == "ArtefactRegistered" and e["stream_id"] == artefact_id]
    if len(matches) != 1:
        raise IntegrityError(f"project-use evidence requires exactly one registered artefact: {artefact_id}")
    return matches[0]


def _result_predicate() -> str:
    predicate, digest = (
        ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load().predicate_for("result_evidence")
    )
    return predicate_reference(predicate["predicate_id"], predicate["predicate_version"], digest)


def _accepted_closure(task_id: str, events: list[dict], ctx: RouteContext) -> dict[str, Any]:
    completed = []
    for closing in spec_task.enumerated_intents(events):
        if closing["task_id"] != task_id:
            continue
        state = spec_task.evaluate(closing, events, schemas=ctx.schemas, authority_state_validator=ctx.validator)
        if state["state"] == "completed":
            completed.append(state)
    if len(completed) != 1:
        raise IntegrityError(f"{REGISTER} requires exactly one Task closure issued by close_task: {task_id}")
    return completed[0]


def spike_record(intent: dict[str, Any], candidate: dict[str, Any], projection: dict[str, Any]) -> dict | None:
    """Return the Spike a decision cites, or None with an explicit no_spike reason.

    Args:
        intent: Register intent.
        candidate: Projected Candidate at a terminal owner Decision.
        projection: Discovery projection.

    Returns:
        The Spike identity, status and version, or None.

    Raises:
        IntegrityError: If the Spike and the no_spike reason disagree with the gate.
    """
    if candidate.get("promotion_gate") == "spike_to_preregistration":
        spike = projection["spikes"].get(candidate.get("spike_id"))
        if not isinstance(spike, dict) or spike.get("candidate_id") != candidate["candidate_id"]:
            raise IntegrityError(f"{REGISTER} requires the Candidate's own Spike")
        if "no_spike_reason" in intent:
            raise IntegrityError(f"{REGISTER} cannot give a no_spike reason when a Spike was decided")
        return {"spike_id": candidate["spike_id"], "status": spike["status"], "version": spike["version"]}
    if candidate.get("spike_id") or "no_spike_reason" not in intent:
        raise IntegrityError(f"{REGISTER} requires an explicit no_spike reason and no Spike at an Assay-gate Decision")
    return None


def _sources(
    candidate: dict, projection: dict, events: list[dict], streams: dict[str, Any], ctx: RouteContext
) -> list[dict]:
    registrations: dict[str, dict] = {}
    for observation_id in candidate.get("source_observation_refs", ()):
        observation = projection["source_observations"].get(observation_id)
        if not isinstance(observation, dict):
            raise IntegrityError(f"{REGISTER} requires the Candidate's source observation: {observation_id}")
        refs = observation["batch"].get("raw_source_refs") or []
        if not refs or any(not str(ref.get("locator", "")).startswith(SOURCE_REF_PREFIX) for ref in refs):
            raise IntegrityError(f"{REGISTER} requires every Candidate source to be a SOURCE route registration")
        validate_source_refs(observation["batch"], events, before_position=observation["global_position"])
        for ref in refs:
            identity = ref["locator"][len(SOURCE_REF_PREFIX) :].partition(":")[0]
            # A ledger reference alone is hash-only; the SOURCE bytes themselves must verify.
            ctx.read_source_document(identity)
            registrations[identity] = _registration(events, identity)
    # Accepted corrections of a cited source are sources too, transitively.
    corrections = [
        event
        for event in events
        if event["event_type"] == "ArtefactRegistered"
        and event["payload"]["manifest"].get("artefact_schema_id") == CORRECTION_SCHEMA
        and event["payload"]["manifest"].get("artefact_schema_version") == "2.0.0"
    ]
    # Inclusion follows the replayed current use authority, so a correction later
    # superseded or otherwise withdrawn is not a source of any decision derived after that.
    accepted = {
        stream_id
        for stream_id, stream in streams.items()
        if isinstance(stream, dict) and stream.get("use_authority") == "accepted_for_scope"
    }
    changed = True
    while changed:
        changed = False
        for event in corrections:
            if event["stream_id"] in registrations or event["stream_id"] not in accepted:
                continue
            document, _ = ctx.read_source_document(event["stream_id"])
            if document["prior_evidence"]["artefact_id"] in registrations:
                registrations[event["stream_id"]] = event
                changed = True
    return [registration_ref(event) for event in sorted(registrations.values(), key=lambda e: e["global_position"])]


def derive(
    intent: dict[str, Any],
    events: list[dict],
    ctx: RouteContext,
    *,
    artefact_id: str,
    actor_id: str,
    recorded_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive the ProjectUseDecision document and its manifest from a ledger prefix.

    Every closing precondition is checked here, so a refusal always precedes the
    registration, the first durable mutation.

    Args:
        intent: Register intent carrying the owner's disposition and prose only.
        events: Ledger events up to and including the causal-prefix tail.
        ctx: Route context.
        artefact_id: The decision's artefact identity.
        actor_id: The registering (producing) actor.
        recorded_at: The document's recorded time.

    Returns:
        The closed document and its artefact manifest.

    Raises:
        IntegrityError: If any reference cannot be derived or bound.
        ConflictError: If the Task closure carries evidence the route did not issue.
    """
    task_id = intent["task_id"]
    closure = _accepted_closure(task_id, events, ctx)
    by_id = {event["event_id"]: event for event in events}
    acceptance = by_id[closure["effects"][-1]["event_id"]]
    state = replay(tuple(events), schema_registry=ctx.schemas, authority_state_validator=ctx.validator)
    streams = state["streams"]
    task = streams[task_id]
    attempt = streams[closure["attempt_id"]]
    selected = list(task.get("acceptance", {}).get("selected_artefact_ids", ()))
    if task.get("status") != "accepted" or not selected:
        raise IntegrityError(f"{REGISTER} requires an accepted Task that selected evidence artefacts")
    # The decision names the closure Attempt, which ran the revision it was dispatched on. An amendment after
    # dispatch would match the Candidate below on a definition that Attempt never ran.
    if attempt.get("task_revision") != task.get("current_revision"):
        raise IntegrityError(f"{REGISTER} requires Task {task_id} unamended since its Attempt's dispatch")

    projection = replay_discovery(tuple(events), schemas=ctx.schemas, authority_state_validator=ctx.validator)
    named = [ref for ref in task["definition"].get("portfolio_refs", ()) if ref in projection["candidates"]]
    if len(named) != 1:
        raise IntegrityError(f"{REGISTER} requires the accepted Task to name exactly one Candidate")
    candidate = projection["candidates"][named[0]]
    decision_id = candidate.get("decision_id")
    decision = projection["decisions"].get(decision_id)
    if not isinstance(decision, dict) or decision.get("status") != "resolved":
        raise IntegrityError(f"{REGISTER} requires a resolved Candidate Decision")
    gate, option = candidate.get("promotion_gate"), decision.get("selected_option")
    if _TERMINAL_STATUS.get((gate, option)) != candidate.get("status"):
        raise IntegrityError(f"{REGISTER} requires a Candidate at a terminal owner Decision")
    resolutions = [e for e in events if e["event_type"] == "DecisionResolved" and e["stream_id"] == decision_id]
    if len(resolutions) != 1 or resolutions[0]["actor_id"] != state.get("authority_owner_actor_id"):
        raise IntegrityError(f"{REGISTER} requires the terminal Decision to be resolved by the owner")
    if intent["disposition"] not in _PERMITTED_DISPOSITIONS[option]:
        raise IntegrityError(f"{REGISTER} disposition {intent['disposition']} is not permitted by a {option} Decision")
    assay = projection["assays"].get(candidate.get("assay_id"))
    if not isinstance(assay, dict) or assay.get("candidate_id") != candidate["candidate_id"]:
        raise IntegrityError(f"{REGISTER} requires the Candidate's current Assay")

    bindings = [event for event in events if event["event_type"] in _BINDING_EVENTS]
    if not bindings:
        raise IntegrityError(f"{REGISTER} requires a store-binding event for the governed-code subject")
    binding = bindings[-1]
    tail = events[-1] if events else None
    document = {
        "schema_id": DOCUMENT_SCHEMA_ID,
        "schema_version": "1.0.0",
        "document_type": DOCUMENT_TYPE,
        "intent": dict(intent),
        "recorded_at": recorded_at,
        "producer_actor_id": actor_id,
        "causal_prefix": {
            "global_position": tail["global_position"] if tail else 0,
            "event_hash": tail["event_hash"] if tail else "0" * 64,
            "raw_prefix_sha256": ctx.raw_prefix_sha256(tail["global_position"] if tail else 0),
        },
        "task": {
            "task_id": task_id,
            "attempt_id": closure["attempt_id"],
            "acceptance_event": _event_ref(acceptance),
            "selected_artefact_ids": selected,
        },
        "candidate": {key: candidate[key] for key in ("candidate_id", "revision", "content_sha256", "status")},
        "assay": {"assay_id": candidate["assay_id"], "status": assay["status"], "version": assay["version"]},
        "spike": spike_record(intent, candidate, projection),
        "decision": {
            "decision_id": decision_id,
            "promotion_gate": gate,
            "selected_option": option,
            "deciding_actor_id": resolutions[0]["actor_id"],
            "resolution_event": _event_ref(resolutions[0]),
        },
        "sources": _sources(candidate, projection, events, streams, ctx),
        "evidence": [registration_ref(_registration(events, selected_id)) for selected_id in selected],
        "governed_code_subject": {
            "binding_event": _event_ref(binding),
            "event_type": binding["event_type"],
            **{key: binding["payload"][key] for key in ("recovery_binding_sha256", "git_head", "git_tree")},
        },
    }
    ctx.schemas.validate(DOCUMENT_SCHEMA_ID, document, schema_version="1.0.0")
    return document, _manifest(document, artefact_id, attempt)


def _input_dependencies(document: dict[str, Any]) -> list[dict[str, str]]:
    """Name every cited source and evidence artefact as a manifest input (PR #288 known limit 9)."""
    return [
        {
            "input_artefact_id": ref["artefact_id"],
            "input_content_sha256": ref["content_sha256"],
            "dependency_role": role,
        }
        for role, refs in (("source", document["sources"]), ("evidence", document["evidence"]))
        for ref in refs
    ]


def _manifest(document: dict[str, Any], artefact_id: str, attempt: dict[str, Any]) -> dict[str, Any]:
    raw = canonical_bytes(document)
    digest = sha256_hex(raw)
    return {
        "task_id": document["task"]["task_id"],
        "dispatch_id": attempt["dispatch_id"],
        "attempt_id": document["task"]["attempt_id"],
        "context_packet_id": attempt["start"]["context_packet_id"],
        "producer_profile": f"{_ROUTE_IDENTITY}:{DOCUMENT_TYPE}",
        # The closure Attempt's own identities, not the store binding's, which the document's
        # governed_code_subject records. Admission's manifest schema refuses a non-git code identity.
        "code_commit": attempt["start"]["code_identity"],
        "branch_identity": _ROUTE_IDENTITY,
        "worktree_identity": _ROUTE_IDENTITY,
        "environment_fingerprint": attempt["start"]["environment_fingerprint"],
        "artefact_id": artefact_id,
        "aliases": [],
        "artefact_type": DOCUMENT_TYPE,
        "artefact_schema_id": DOCUMENT_SCHEMA_ID,
        "artefact_schema_version": "1.0.0",
        "producer_actor_id": document["producer_actor_id"],
        "created_at": document["recorded_at"],
        "observed_at": document["recorded_at"],
        "root_id": "control",
        "relative_path": f"objects/{DOCUMENT_KIND}/{artefact_id}/00000001-{digest}.json",
        "size_bytes": len(raw),
        "media_type": "application/json",
        "content_sha256": digest,
        "availability_check_evidence_refs": [],
        "input_dependencies": _input_dependencies(document),
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
        "validation": {
            "validation_record_refs": [],
            "expected_contract_ids": [],
            "expected_schema_ids": [DOCUMENT_SCHEMA_ID],
        },
        "authority": {
            "availability": "available",
            "regenerability": "non_regenerable",
            "integrity": "verified",
            "structural_validation": "passed",
            "scientific_review": "pending",
            "use_authority": "candidate",
            "accepted_scope": f"spec:project-use:{document['task']['task_id']}",
            "consumer_restrictions": [],
        },
        "operations": {
            "no_overwrite_evidence_refs": [],
            "retention_class": "durable",
            "confidentiality_class": "internal",
            "external_data_constraints": [],
        },
    }


def _review_payload(artefact_id: str, digest: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"artefact_id": artefact_id, "subject_sha256": digest, "scientific_review": "approved", **evidence}


def _use_payload(artefact_id: str, digest: str, review: dict) -> dict[str, Any]:
    return {
        "artefact_id": artefact_id,
        "subject_sha256": digest,
        "use_authority": "accepted_for_scope",
        "consumer_predicate": _result_predicate(),
        "evidence_refs": [review["payload"]["review_id"], *review["payload"]["evidence_refs"]],
    }


def _issued(event: dict, action: str, task_id: str, effect: str, payload: dict) -> bool:
    key = retry_key(
        {"action": action, "task_id": task_id}, effect, event["actor_id"], event["authority_grant_id"], payload
    )
    return event.get("idempotency_key") == key and event.get("command_id") == _stable_command_id(key)


def _read_document(artefact_id: str, registration: dict, ctx: RouteContext) -> dict[str, Any]:
    manifest = registration["payload"]["manifest"]
    if not ctx.objects.revision_exists(DOCUMENT_KIND, artefact_id, 1):
        raise IntegrityError(f"ProjectUseDecision bytes are absent for its registration: {artefact_id}")
    document = ctx.objects.read(DOCUMENT_KIND, artefact_id, 1)
    raw = canonical_bytes(document)
    if (
        manifest.get("content_sha256") != sha256_hex(raw)
        or manifest.get("size_bytes") != len(raw)
        or manifest.get("relative_path") != f"objects/{DOCUMENT_KIND}/{artefact_id}/00000001-{sha256_hex(raw)}.json"
    ):
        raise IntegrityError(f"ProjectUseDecision registration and immutable document disagree: {artefact_id}")
    return document


def _verify_registration(task_id: str, artefact_id: str, event: dict, events: list[dict], ctx: RouteContext) -> dict:
    if event["event_type"] != "ArtefactRegistered" or not _issued(
        event, REGISTER, task_id, "RegisterArtefact", event["payload"]
    ):
        raise ConflictError(
            f"{REGISTER} found {event['event_type']} on its artefact stream that this route did not issue"
        )
    document = _read_document(artefact_id, event, ctx)
    ctx.schemas.validate(DOCUMENT_SCHEMA_ID, document, schema_version="1.0.0")
    if document["causal_prefix"]["global_position"] >= event["global_position"]:
        raise IntegrityError(f"{REGISTER} document cannot cite its own or a later registration")
    manifest = _rederive(document, events, ctx, artefact_id=artefact_id, actor_id=event["actor_id"])
    if event["payload"] != {"new_artefact_id": artefact_id, "manifest": manifest}:
        raise IntegrityError(f"{REGISTER} does not carry the decision this route derives")
    return document


def _rederive(document: dict, events: list[dict], ctx: RouteContext, *, artefact_id: str, actor_id: str) -> dict:
    """Re-derive a schema-valid decision at its recorded causal prefix and return its manifest."""
    position = document["causal_prefix"]["global_position"]
    expected, manifest = derive(
        document["intent"],
        [e for e in events if e["global_position"] <= position],
        ctx,
        artefact_id=artefact_id,
        actor_id=actor_id,
        recorded_at=document["recorded_at"],
    )
    if document != expected:
        raise IntegrityError(f"{REGISTER} does not carry the decision this route derives")
    return manifest


def _verify_review(task_id: str, artefact_id: str, event: dict, registration: dict) -> None:
    payload = event["payload"]
    digest = registration["payload"]["manifest"]["content_sha256"]
    if event["event_type"] != "ScientificReviewRecorded" or not _issued(
        event, ACCEPT, task_id, "RecordScientificReview", payload
    ):
        raise ConflictError(
            f"{ACCEPT} found {event['event_type']} on its artefact stream that this route did not issue"
        )
    evidence = {key: payload.get(key) for key in _REVIEW_EVIDENCE}
    if payload != _review_payload(artefact_id, digest, evidence):
        raise IntegrityError(f"{ACCEPT} review does not carry the payload this route derives")
    if (
        event["actor_id"] == registration["actor_id"]
        or event["authority_grant_id"] == registration["authority_grant_id"]
    ):
        raise IntegrityError(f"{ACCEPT} review is not independent of the registering producer")


def _verify_use(task_id: str, artefact_id: str, event: dict, registration: dict, review: dict) -> None:
    digest = registration["payload"]["manifest"]["content_sha256"]
    submitted = _use_payload(artefact_id, digest, review)
    if event["event_type"] != "ArtefactUseAuthoritySet" or not _issued(
        event, ACCEPT, task_id, "SetArtefactUseAuthority", submitted
    ):
        raise ConflictError(
            f"{ACCEPT} found {event['event_type']} on its artefact stream that this route did not issue"
        )
    payload = event["payload"]
    refs = submitted["evidence_refs"]
    # Admission appends the governing-review binding it verified to the submitted refs.
    if {k: v for k, v in payload.items() if k != "evidence_refs"} != {
        k: v for k, v in submitted.items() if k != "evidence_refs"
    } or payload.get("evidence_refs", [])[: len(refs)] != refs:
        raise IntegrityError(f"{ACCEPT} use authority does not carry the payload this route derives")
    if event["actor_id"] == review["actor_id"] or event["authority_grant_id"] in {
        registration["authority_grant_id"],
        review["authority_grant_id"],
    }:
        raise IntegrityError(f"{ACCEPT} use authority needs a separate actor and grant from the review")


def _states(task_id: str, events: list[dict], ctx: RouteContext) -> dict[str, Any]:
    artefact_id = subject_id(ctx.project_id, task_id)
    base = {"task_id": task_id, "artefact_id": artefact_id}
    register = {"action": REGISTER, "state": "not_started", **base, "next_effect": REGISTER_EFFECTS[0], "effects": []}
    accept = {"action": ACCEPT, "state": "not_started", **base, "next_effect": ACCEPT_EFFECTS[0], "effects": []}
    stream = [event for event in events if event["stream_id"] == artefact_id]
    located: dict[str, Any] = {"document": None, "registration": None, "review": None, "use": None}
    if not stream:
        return {"register": register, "accept": accept, **located}
    registration = stream[0]
    located["document"] = _verify_registration(task_id, artefact_id, registration, events, ctx)
    located["registration"] = registration
    register.update(state="completed", next_effect=None, effects=[_summary(registration)])
    if len(stream) > 1:
        _verify_review(task_id, artefact_id, stream[1], registration)
        located["review"] = stream[1]
        accept.update(state="prepared", next_effect=ACCEPT_EFFECTS[1], effects=[_summary(stream[1])])
    if len(stream) > 2:
        _verify_use(task_id, artefact_id, stream[2], registration, stream[1])
        located["use"] = stream[2]
        accept.update(state="completed", next_effect=None, effects=[_summary(stream[1]), _summary(stream[2])])
    if len(stream) > 3:
        raise ConflictError(
            f"{ACCEPT} found {stream[3]['event_type']} on its artefact stream that this route did not issue"
        )
    return {"register": register, "accept": accept, **located}


def evaluate(action: str, task_id: str, events: list[dict], ctx: RouteContext, *, intent: dict | None = None) -> dict:
    """Derive one project-use action's state purely from route-issued evidence.

    Args:
        action: ``register_project_use_decision`` or ``accept_project_use_decision``.
        task_id: The Task whose decision is evaluated.
        events: Full ordered ledger event list.
        ctx: Route context.
        intent: Explicit register intent; must equal the registered one when present.

    Returns:
        A state record: not_started, prepared or completed, with its effects.

    Raises:
        ConflictError: If foreign or differently bound evidence sits on the subject.
        IntegrityError: If route-keyed evidence does not carry the derived payload.
    """
    states = _states(task_id, events, ctx)
    document = states["document"]
    if intent is not None and action == REGISTER and document is not None and document["intent"] != intent:
        raise ConflictError(f"{REGISTER} already binds a different decision for Task {task_id}")
    return states["register"] if action == REGISTER else states["accept"]


def next_command(
    intent: dict[str, Any],
    evidence: dict | None,
    events: list[dict],
    ctx: RouteContext,
    *,
    actor_id: str,
    grant_id: str,
    now: str,
) -> tuple[str, str, dict[str, Any], dict | None]:
    """Build the next effect for an action, refusing before any durable mutation.

    Args:
        intent: Validated project-use intent.
        evidence: Independent evidence (review only).
        events: Full ordered ledger event list from one snapshot.
        ctx: Route context.
        actor_id: Actor of this invocation.
        grant_id: Authority grant of this invocation.
        now: Trusted submission time.

    Returns:
        The effect, target stream, exact payload and the document to publish (register only).

    Raises:
        IntegrityError: If the effect cannot be honestly built for this actor.
        ConflictError: If unregistered decision bytes left for this Task bind another intent.
    """
    task_id = intent["task_id"]
    artefact_id = subject_id(ctx.project_id, task_id)
    states = _states(task_id, events, ctx)
    if intent["action"] == REGISTER:
        if evidence is not None:
            raise IntegrityError(f"{REGISTER} takes no independent evidence")
        if ctx.objects.revision_exists(DOCUMENT_KIND, artefact_id, 1):
            # A process that stopped after publishing the bytes, before appending the
            # registration, left them behind. Immutable bytes cannot be replaced, so they
            # are reused, but only if they are exactly the decision this route derives at
            # their own causal prefix for this intent and producer.
            document = ctx.objects.read(DOCUMENT_KIND, artefact_id, 1)
            ctx.schemas.validate(DOCUMENT_SCHEMA_ID, document, schema_version="1.0.0")
            if document["intent"] != intent or document["producer_actor_id"] != actor_id:
                raise ConflictError(f"{REGISTER} already binds a different decision for Task {task_id}")
            manifest = _rederive(document, events, ctx, artefact_id=artefact_id, actor_id=actor_id)
        else:
            document, manifest = derive(
                intent, events, ctx, artefact_id=artefact_id, actor_id=actor_id, recorded_at=now
            )
        return "RegisterArtefact", artefact_id, {"new_artefact_id": artefact_id, "manifest": manifest}, document
    registration = states["registration"]
    if registration is None:
        raise IntegrityError(f"{ACCEPT} requires a registered ProjectUseDecision for Task {task_id}")
    digest = registration["payload"]["manifest"]["content_sha256"]
    if states["review"] is None:
        if not isinstance(evidence, dict) or set(evidence) != _REVIEW_EVIDENCE:
            raise IntegrityError(f"{ACCEPT} review evidence fields are not exact")
        if actor_id == registration["actor_id"] or grant_id == registration["authority_grant_id"]:
            raise IntegrityError(f"{ACCEPT} requires a reviewer independent of the registering producer")
        payload = _review_payload(artefact_id, digest, evidence)
        # The decision's stream admits one review, so evidence that could never govern use
        # authority must be refused before the review is recorded, not at use authority.
        ctx.check_review_evidence(
            registration, payload, _use_payload(artefact_id, digest, {"payload": payload}), actor_id, now
        )
        return "RecordScientificReview", artefact_id, payload, None
    if evidence is not None:
        raise IntegrityError(f"{ACCEPT} use authority takes no independent evidence")
    review = states["review"]
    if actor_id == review["actor_id"] or grant_id in {registration["authority_grant_id"], review["authority_grant_id"]}:
        raise IntegrityError(f"{ACCEPT} use authority needs a separate actor and grant from the review")
    return "SetArtefactUseAuthority", artefact_id, _use_payload(artefact_id, digest, review), None


def exact_retry(
    intent: dict[str, Any],
    evidence: dict | None,
    events: list[dict],
    ctx: RouteContext,
    *,
    actor_id: str,
    grant_id: str,
) -> dict | None:
    """Recognise a repeated invocation of an effect that is already committed.

    The review and the use authority differ in actor and evidence, so an invocation
    valid for one can never reproduce the other's retry key.

    Args:
        intent: Validated project-use intent.
        evidence: Evidence of the repeated invocation.
        events: Full ordered ledger event list.
        ctx: Route context.
        actor_id: Actor of the repeated invocation.
        grant_id: Authority grant of the repeated invocation.

    Returns:
        The committed event this invocation repeats, or None.
    """
    states = _states(intent["task_id"], events, ctx)
    registration = states["registration"]
    if registration is None:
        return None
    if intent["action"] == REGISTER:
        document = states["document"]
        same = evidence is None and document["intent"] == intent
        if same and (registration["actor_id"], registration["authority_grant_id"]) == (actor_id, grant_id):
            return registration
        return None
    artefact_id, digest = registration["stream_id"], registration["payload"]["manifest"]["content_sha256"]
    candidates = []
    if states["review"] is not None and isinstance(evidence, dict) and set(evidence) == _REVIEW_EVIDENCE:
        candidates.append((states["review"], "RecordScientificReview", _review_payload(artefact_id, digest, evidence)))
    if states["use"] is not None and evidence is None:
        candidates.append(
            (states["use"], "SetArtefactUseAuthority", _use_payload(artefact_id, digest, states["review"]))
        )
    for event, effect, payload in candidates:
        if retry_key(intent, effect, actor_id, grant_id, payload) == event.get("idempotency_key"):
            return event
    return None


def enumerated_tasks(events: list[dict]) -> list[str]:
    """Return every Task that has a registered ProjectUseDecision, in ledger order.

    Args:
        events: Full ordered ledger event list.

    Returns:
        Task identities recovered from decision registrations.
    """
    return [
        event["payload"]["manifest"]["task_id"]
        for event in events
        if event["event_type"] == "ArtefactRegistered"
        and event["payload"]["manifest"].get("artefact_type") == DOCUMENT_TYPE
    ]


def result(task_id: str, events: list[dict], ctx: RouteContext, *, route_id: str) -> dict[str, Any]:
    """Return the Task-specific project-use result.

    Args:
        task_id: The selected Task.
        events: Full ordered ledger event list.
        ctx: Route context.
        route_id: Operator route identity.

    Returns:
        ``pending`` until registration and independent acceptance both exist, then
        ``accepted`` with the decision and its acceptance evidence.
    """
    states = _states(task_id, events, ctx)
    accepted = states["register"]["state"] == "completed" and states["accept"]["state"] == "completed"
    output: dict[str, Any] = {
        "route_id": route_id,
        "task_id": task_id,
        "artefact_id": states["register"]["artefact_id"],
        "status": "accepted" if accepted else "pending",
        "actions": {"register": states["register"], "accept": states["accept"]},
    }
    if accepted:
        document = states["document"]
        output["project_use_decision"] = document
        output["disposition_statement"] = _DISPOSITION_TEXT[document["intent"]["disposition"]]
        output["subset_statement"] = _SUBSET_TEXT
        output["acceptance"] = {
            "registration": _event_ref(states["registration"]),
            "scientific_review": {**_event_ref(states["review"]), "reviewer_actor_id": states["review"]["actor_id"]},
            "use_authority": {**_event_ref(states["use"]), "actor_id": states["use"]["actor_id"]},
        }
    return output


def render_markdown(output: dict[str, Any]) -> str:
    """Render a project-use result for a human reader.

    Args:
        output: A value returned by :func:`result`.

    Returns:
        Markdown text. A pending result states only that the decision is pending.
    """
    lines = [f"# Project-use result for {output['task_id']}", ""]
    if output["status"] != "accepted":
        register, accept = output["actions"]["register"], output["actions"]["accept"]
        step = register["next_effect"] or accept["next_effect"]
        lines += ["**Status:** project-use decision pending", "", f"Next required effect: `{step}`."]
        return "\n".join(lines) + "\n"
    document = output["project_use_decision"]
    intent, decision = document["intent"], document["decision"]
    spike = document["spike"]
    lines += [
        "**Status:** accepted",
        "",
        f"**Disposition:** {output['disposition_statement']}",
        "",
        f"**Route-proof subset:** {intent['subset_qualification']} {output['subset_statement']}",
        "",
        "## Rationale",
        "",
        intent["rationale"],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in intent["limitations"]],
        "",
        "## Next gates",
        "",
        *[f"- {item}" for item in intent["next_gates"]],
        "",
        "## Evidence",
        "",
        f"- Owner decision: {decision['selected_option']} at {decision['promotion_gate']} "
        f"(`{decision['decision_id']}`, position {decision['resolution_event']['global_position']})",
        f"- Candidate: `{document['candidate']['candidate_id']}` ({document['candidate']['status']})",
        f"- Assay: `{document['assay']['assay_id']}` ({document['assay']['status']})",
        f"- Spike: `{spike['spike_id']}` ({spike['status']})"
        if spike
        else f"- Spike: none. {intent['no_spike_reason']}",
        f"- Task: `{document['task']['task_id']}` accepted at position "
        f"{document['task']['acceptance_event']['global_position']}",
        *[f"- Source: `{ref['artefact_id']}` sha256 `{ref['content_sha256']}`" for ref in document["sources"]],
        *[
            f"- Evidence artefact: `{ref['artefact_id']}` sha256 `{ref['content_sha256']}`"
            for ref in document["evidence"]
        ],
        f"- Governed code: git `{document['governed_code_subject']['git_head']}` "
        f"(binding `{document['governed_code_subject']['recovery_binding_sha256']}`)",
        f"- Independent review by `{output['acceptance']['scientific_review']['reviewer_actor_id']}`; "
        f"use authority by `{output['acceptance']['use_authority']['actor_id']}`",
    ]
    return "\n".join(lines) + "\n"
