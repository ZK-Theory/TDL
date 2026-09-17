"""06s Phase 4a-1 (P-058): public W11 bootstrap and the SPEC-01 Assay request on the SPEC route."""

import json
import re

import pytest

from research_system import cli
from research_system.canonical import canonical_bytes
from research_system.discovery import spec_assay, spec_result, spec_task
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.discovery.assay_authority import content_sha256 as assay_content_sha256
from research_system.discovery.rules import _aggregate_content_hash, _axis_set_hash, _record_ref, _review_ref
from research_system.discovery.runtime import replay_discovery
from research_system.discovery.spec import ACTION_EFFECTS
from research_system.discovery.spec_source import source_ids
from research_system.errors import ConflictError, SchemaError
from research_system.ids import new_id
from research_system.canonical import sha256_hex
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import ACTORS, PROJECT_ID, REPO_ROOT, activate_lifecycle_grant
from tests.research_system.integration import test_wp6_1_c1_readiness_lease as c1
from tests.research_system.integration.test_spec_result import EVIDENCE_IDS, REVIEWER, _accept_decision, _result
from tests.research_system.integration.test_spec_source import (  # noqa: F401
    bind_scratch_route,
    invoke_cli,
    source_intent,
    source_repo,
)
from tests.research_system.integration.test_spec_task import _OUTCOME_COMMANDS, _outcome_payload, _seed_bound_task
from tests.research_system.integration.test_spec_task import _advance as _advance_task
from tests.research_system.integration.test_spec_task import _streams, _tail
from tests.research_system.integration.test_wp6_1_c2_operating_lifecycle import _artefact_manifest

OWNER = ACTORS["actor-a"]
OTHER_HUMAN = ACTORS["actor-b"]


def _actor(number: int) -> str:
    return f"act_019fed25-b33e-7740-b280-{number:012d}"


# Both committed Assay authority files pin this author, and admission requires it as the submitter (P-058).
PINNED_AUTHOR = _actor(205)
RUBRIC_OBSERVER, SCOPE_OBSERVER, BAR_REQUESTER, BAR_REVIEWER, BAR_PROPOSER = (_actor(n) for n in range(401, 406))
STEWARD, PRODUCER = _actor(411), _actor(412)
OUTCOME_REVIEWER, PROPOSER = _actor(421), _actor(431)
UUIDV7 = "[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"

# Mirrors DiscoveryRuntime._resolve_authority: the governed subject each command's grant must name.
SUBJECT_KIND = {
    "ImportAcceptedW11CatalogueGenesis": "scope_definition",
    "IngestScoutObservationBatch": "scope_definition",
    "RegisterAssayRubricContent": "scope_definition",
    "RegisterAssayEvidenceScopeContent": "scope_definition",
    "ObserveW11AuthorityFile": "scope_definition",
    "RequestW11AuthorityReview": "review",
    "RecordW11AuthorityReview": "review",
    "ProposeW11AuthorityDecision": "decision",
    "ResolveDecision": "decision",
    "RequestAssay": "scope_definition",
    "RegisterArtefact": "artefact",
    "RecordAssayScore": "scope_definition",
    "RecordAssayPartial": "scope_definition",
    "RequestDiscoveryOutcomeReview": "scope_definition",
    "ReviewDiscoveryOutcome": "review",
    "ProposePromotionDecision": "scope_definition",
}
# These W11 commands' grants name the Candidate rather than their target stream.
CANDIDATE_SCOPED = frozenset(
    {
        "RequestAssay",
        "RecordAssayScore",
        "RecordAssayPartial",
        "RequestDiscoveryOutcomeReview",
        "ProposePromotionDecision",
    }
)

GENESIS_INTENT = {"action": spec_assay.GENESIS, "reason": "import the accepted W11 catalogue"}
BAR_INTENT = {
    "action": spec_assay.BAR,
    "reason": "accept the exact Assay bar",
    "reviewer_actor_id": BAR_REVIEWER,
    "producer_actor_id": PRODUCER,
}
ASSAY_FILES = (spec_assay.ASSAY_RUBRIC_PATH, spec_assay.ASSAY_SCOPE_PATH)


def request_intent(candidate_id: str) -> dict:
    return {"action": spec_assay.REQUEST, "reason": "request the SPEC-01 Assay", "candidate_id": candidate_id}


def _record_id(relative: str) -> str:
    return json.loads((REPO_ROOT / relative).read_bytes())["record_id"]


def _replay(coordinator) -> dict:
    return replay_discovery(
        coordinator.ledger.snapshot().events,
        schemas=coordinator.schemas,
        authority_state_validator=coordinator.resolver.validate_replayed_administration_state,
    )


def _grant(bound, command_type: str, subject_id: str, actor: str, *, human: bool = False) -> str:
    return activate_lifecycle_grant(
        bound.harness,
        subject_kind=SUBJECT_KIND[command_type],
        subject_id=subject_id,
        actor_id=actor,
        allowed_actor_classes=("human",) if human else ("agent",),
        command_types=(command_type,),
        grant_id=new_id("authority_grant"),
    )


def _bar_steps() -> list[tuple[str, str, str, bool]]:
    """Each Assay-bar effect's command, grant subject, distinct actor and actor class, in route order."""
    ids = spec_assay.subject_ids(PROJECT_ID, BAR_INTENT)
    rubric, scope = _record_id(spec_assay.ASSAY_RUBRIC_PATH), _record_id(spec_assay.ASSAY_SCOPE_PATH)
    return [
        ("RegisterAssayRubricContent", rubric, PINNED_AUTHOR, False),
        ("RegisterAssayEvidenceScopeContent", scope, PINNED_AUTHOR, False),
        ("ObserveW11AuthorityFile", rubric, RUBRIC_OBSERVER, False),
        ("ObserveW11AuthorityFile", scope, SCOPE_OBSERVER, False),
        ("RequestW11AuthorityReview", ids["review_id"], BAR_REQUESTER, False),
        ("RecordW11AuthorityReview", ids["review_id"], BAR_REVIEWER, False),
        ("ProposeW11AuthorityDecision", ids["decision_id"], BAR_PROPOSER, False),
        ("ResolveDecision", ids["decision_id"], OWNER, True),
    ]


def _advance(bound, tmp_path, capsys, intent, command_type, subject, actor, human=False) -> dict:
    grant = _grant(bound, command_type, subject, actor, human=human)
    return invoke_cli(bound, tmp_path, capsys, intent, "advance", grant, actor=actor)


def _refuse(bound, tmp_path, capsys, intent: dict, grant: str, actor: str) -> str:
    """Invoke the public advance, expecting refusal with nothing appended; return the error text."""
    intent_path = tmp_path / "refused-intent.json"
    intent_path.write_bytes(canonical_bytes(intent))
    config_path = tmp_path / "refused-operator.json"
    config_path.write_bytes(canonical_bytes({**bound.config, "authority_grant_id": grant, "operator_actor_id": actor}))
    before = _tail(bound.coordinator)
    args = ["discovery", "spec", "advance", "--operator-config", str(config_path)]
    code = cli.main([*args, "--action", intent["action"], "--input", str(intent_path)])
    captured = capsys.readouterr()
    assert code == 1, captured.out
    assert _tail(bound.coordinator) == before, "a refused invocation appended an event"
    return captured.err


def _observe(bound, tmp_path, capsys, source_repo) -> str:  # noqa: F811
    observation = source_intent(source_repo)
    ids = source_ids(PROJECT_ID, observation)
    register = activate_lifecycle_grant(
        bound.harness, subject_kind="artefact", subject_id=ids["artefact_id"], command_types=("RegisterArtefact",)
    )
    scout = activate_lifecycle_grant(
        bound.harness,
        subject_kind="scope_definition",
        subject_id=ids["observation_id"],
        command_types=("IngestScoutObservationBatch",),
    )
    invoke_cli(bound, tmp_path, capsys, observation, "advance", register)
    assert invoke_cli(bound, tmp_path, capsys, observation, "advance", scout)["state"] == "completed"
    return ids["candidate_id"]


def _direct(bound, command_type: str, target: str, payload: dict, actor: str, *, human: bool = False) -> str:
    """Submit straight to inherited Discovery admission, bypassing the route (decisive controls only)."""
    subject = payload["candidate_id"] if command_type in CANDIDATE_SCOPED else target
    command = {
        "command_id": new_id("command"),
        "command_type": command_type,
        "actor_id": actor,
        "authority_grant_id": _grant(bound, command_type, subject, actor, human=human),
        "idempotency_key": f"control:{new_id('command')}",
        "target_stream_id": target,
        "expected_stream_version": bound.coordinator.ledger.snapshot().stream_versions.get(target, 0),
        "payload": payload,
    }
    return bound.coordinator._discovery().submit(command).status


def _ingest_direct(bound, number: int) -> str:
    """Register a throwaway Candidate through inherited admission for a decisive control."""
    candidate_id = f"obj_019fed25-b33e-7740-b280-{900 + number:012d}"
    observation_id = f"obj_019fed25-b33e-7740-b280-{950 + number:012d}"
    batch = {
        "schema_id": "ars://portfolio/scout-observation-batch",
        "schema_version": "1.0.0",
        "source_query": f"exact:{observation_id}",
        "source_version": "1",
        "observed_at": "2026-09-01T00:00:00Z",
        "returned_identifiers": [observation_id],
        "normalized_dedup_keys": [observation_id],
        "raw_source_refs": [{"ref_kind": "external", "locator": observation_id, "content_hash": "9" * 64}],
        "matching_facts": [f"control {number}"],
        "omissions_or_errors": [],
        "viability_judgment_absent": True,
    }
    batch_sha256 = sha256_hex(canonical_bytes(batch))
    blueprint = {
        "candidate_id": candidate_id,
        "revision": 1,
        "content_sha256": sha256_hex(
            canonical_bytes([{"observation_id": observation_id, "content_sha256": batch_sha256}])
        ),
        "source_observation_refs": [observation_id],
        "title": f"control {number}",
    }
    payload = {
        "row_id": "OR-029",
        "observation_id": observation_id,
        "batch": batch,
        "batch_sha256": batch_sha256,
        "candidate_blueprints": [blueprint],
    }
    assert _direct(bound, "IngestScoutObservationBatch", observation_id, payload, OWNER, human=True) == "accepted"
    return candidate_id


def test_the_action_table_adds_the_bootstrap_and_assay_request_actions():
    assert ACTION_EFFECTS[spec_assay.GENESIS] == ("ImportAcceptedW11CatalogueGenesis",)
    assert ACTION_EFFECTS[spec_assay.BAR] == (
        "RegisterAssayRubricContent",
        "RegisterAssayEvidenceScopeContent",
        "ObserveW11AuthorityFile",
        "ObserveW11AuthorityFile",
        "RequestW11AuthorityReview",
        "RecordW11AuthorityReview",
        "ProposeW11AuthorityDecision",
        "ResolveDecision",
    )
    assert ACTION_EFFECTS[spec_assay.REQUEST] == ("RequestAssay",)
    assert ACTION_EFFECTS[spec_assay.PREPARE] == ("RegisterArtefact",)
    assert ACTION_EFFECTS[spec_assay.RETURN] == ("RegisterArtefact", "RecordAssayScore")
    assert ACTION_EFFECTS[spec_assay.REVIEW] == ("RequestDiscoveryOutcomeReview", "ReviewDiscoveryOutcome")
    assert ACTION_EFFECTS[spec_assay.DECIDE] == ("ProposePromotionDecision", "ResolveDecision")
    # 06s Phase 4a′ (P-058, 2026-09-17): the Partial alternatives.
    assert ACTION_EFFECTS[spec_assay.RETURN_PARTIAL] == ("RegisterArtefact", "RecordAssayPartial")
    assert ACTION_EFFECTS[spec_assay.REVIEW_PARTIAL] == ("RequestDiscoveryOutcomeReview", "ReviewDiscoveryOutcome")


def test_assay_intent_is_a_closed_record():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    candidate = "obj_019fed25-b33e-7740-b280-000000000501"
    partial_actions = (spec_assay.RETURN_PARTIAL, spec_assay.REVIEW_PARTIAL)
    partial_intents = tuple(
        {"action": action, "reason": "advance", "candidate_id": candidate} for action in partial_actions
    )
    for intent in (GENESIS_INTENT, BAR_INTENT, request_intent(candidate), *partial_intents):
        schemas.validate(spec_assay.INTENT_SCHEMA_ID, intent, schema_version=spec_assay.INTENT_SCHEMA_VERSION)
    for invalid in (
        {**GENESIS_INTENT, "unrecognised": True},
        {**GENESIS_INTENT, "candidate_id": candidate},
        {key: value for key, value in BAR_INTENT.items() if key != "producer_actor_id"},
        {**BAR_INTENT, "candidate_id": candidate},
        {"action": spec_assay.REQUEST, "reason": "no candidate"},
        {**request_intent(candidate), "reviewer_actor_id": BAR_REVIEWER},
        *({"action": action, "reason": "no candidate"} for action in partial_actions),
        *({**intent, "recommendation": "PARK"} for intent in partial_intents),
        # The version identifies the catalogue entry; an intent never carries it.
        {**request_intent(candidate), "schema_version": spec_assay.INTENT_SCHEMA_VERSION},
    ):
        with pytest.raises(SchemaError):
            schemas.validate(spec_assay.INTENT_SCHEMA_ID, invalid, schema_version=spec_assay.INTENT_SCHEMA_VERSION)


def test_route_identities_are_deterministic_uuidv7_and_subject_bound():
    first = request_intent("obj_019fed25-b33e-7740-b280-000000000501")
    other = request_intent("obj_019fed25-b33e-7740-b280-000000000502")
    assay_id = spec_assay.subject_ids(PROJECT_ID, first)["assay_id"]
    assert re.fullmatch(f"asy_{UUIDV7}", assay_id)
    assert spec_assay.subject_ids(PROJECT_ID, {**first, "reason": "free text is not identity"})["assay_id"] == assay_id
    assert spec_assay.subject_ids(PROJECT_ID, other)["assay_id"] != assay_id
    bar = spec_assay.subject_ids(PROJECT_ID, BAR_INTENT)
    assert re.fullmatch(f"rev_{UUIDV7}", bar["review_id"]) and re.fullmatch(f"dec_{UUIDV7}", bar["decision_id"])
    # Each Partial alternative shares the identities of the complete action it excludes (P-058, 2026-09-17).
    complete = spec_assay.subject_ids(PROJECT_ID, {**first, "action": spec_assay.RETURN})
    for action in (spec_assay.RETURN_PARTIAL, spec_assay.REVIEW, spec_assay.REVIEW_PARTIAL):
        assert spec_assay.subject_ids(PROJECT_ID, {**first, "action": action}) == complete, action


def test_public_bootstrap_and_assay_request_positive_path(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=ASSAY_FILES, genesis=False)
    coordinator = bound.coordinator

    assert coordinator.status(GENESIS_INTENT)["state"] == "not_started"
    genesis_grant = _grant(bound, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID, OWNER, human=True)
    genesis = invoke_cli(bound, tmp_path, capsys, GENESIS_INTENT, "advance", genesis_grant, actor=OWNER)
    assert genesis["state"] == "completed" and genesis["receipt"]["status"] == "accepted"
    tail = _tail(coordinator)
    retried = invoke_cli(bound, tmp_path, capsys, GENESIS_INTENT, "advance", genesis_grant, actor=OWNER)
    assert retried["receipt"] == genesis["receipt"] and _tail(coordinator) == tail

    grants = []
    for index, (command_type, subject, actor, human) in enumerate(_bar_steps()):
        grants.append(_grant(bound, command_type, subject, actor, human=human))
        state = invoke_cli(bound, tmp_path, capsys, BAR_INTENT, "advance", grants[-1], actor=actor)
        effects = ACTION_EFFECTS[spec_assay.BAR]
        assert len(state["effects"]) == index + 1
        assert state["next_effect"] == (effects[index + 1] if index + 1 < len(effects) else None)
    assert state["state"] == "completed"
    bar = _replay(coordinator)["assay_bar_authority"]
    assert bar["status"] == "accepted"
    assert bar["prospective_producer_ref"] == spec_assay.producer_ref(PRODUCER)
    # A lost response to an earlier effect is answered from its receipt; nothing is appended.
    tail = _tail(coordinator)
    retried = invoke_cli(bound, tmp_path, capsys, BAR_INTENT, "advance", grants[2], actor=RUBRIC_OBSERVER)
    assert retried["receipt"]["status"] == "accepted" and _tail(coordinator) == tail

    candidate_id = _observe(bound, tmp_path, capsys, source_repo)
    intent = request_intent(candidate_id)
    assay_id = spec_assay.subject_ids(PROJECT_ID, intent)["assay_id"]
    assert coordinator.status(intent)["state"] == "not_started"
    request_grant = _grant(bound, "RequestAssay", candidate_id, STEWARD)
    requested = invoke_cli(bound, tmp_path, capsys, intent, "advance", request_grant, actor=STEWARD)
    assert requested["state"] == "completed" and requested["assay_id"] == assay_id
    projection = _replay(coordinator)
    assert projection["assays"][assay_id]["status"] == "evidence_collecting"
    assert projection["candidates"][candidate_id]["status"] == "assay_pending"
    tail = _tail(coordinator)
    retried = invoke_cli(bound, tmp_path, capsys, intent, "advance", request_grant, actor=STEWARD)
    assert retried["receipt"] == requested["receipt"] and _tail(coordinator) == tail

    # Each CLI call builds a new coordinator, so this listing re-derives every state from the ledger.
    listing = invoke_cli(bound, tmp_path, capsys, intent, "status", request_grant, actor=STEWARD)
    states = {entry["action"]: entry.get("state") for entry in listing["actions"]}
    assert states[spec_assay.GENESIS] == states[spec_assay.BAR] == states[spec_assay.REQUEST] == "completed"


def test_route_refuses_the_role_collapses_that_admission_accepts(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=ASSAY_FILES, genesis=False)
    coordinator = bound.coordinator

    for actor, human in ((OTHER_HUMAN, True), (STEWARD, False)):
        grant = _grant(bound, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID, actor, human=human)
        assert "authority owner" in _refuse(bound, tmp_path, capsys, GENESIS_INTENT, grant, actor)
    _advance(bound, tmp_path, capsys, GENESIS_INTENT, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID,
             OWNER, human=True)  # fmt: skip

    steps = _bar_steps()
    for command_type, subject, actor, human in steps[:4]:
        _advance(bound, tmp_path, capsys, BAR_INTENT, command_type, subject, actor, human)
    author_grant = _grant(bound, "RequestW11AuthorityReview", steps[4][1], PINNED_AUTHOR)
    assert "content author" in _refuse(bound, tmp_path, capsys, BAR_INTENT, author_grant, PINNED_AUTHOR)
    for command_type, subject, actor, human in steps[4:]:
        _advance(bound, tmp_path, capsys, BAR_INTENT, command_type, subject, actor, human)
    # A different reviewer after the request is a different bar, never a re-derivation of this one.
    with pytest.raises(ConflictError):
        coordinator.status({**BAR_INTENT, "reviewer_actor_id": _actor(499)})

    candidate_id = _observe(bound, tmp_path, capsys, source_repo)
    intent = request_intent(candidate_id)
    for actor, human in ((PRODUCER, False), (OWNER, True)):
        grant = _grant(bound, "RequestAssay", candidate_id, actor, human=human)
        assert "Assay requester" in _refuse(bound, tmp_path, capsys, intent, grant, actor)

    # Decisive controls: inherited admission accepts each Assay requester the route refused.
    bar = _replay(coordinator)["assay_bar_authority"]
    for number, (actor, human) in enumerate(((PRODUCER, False), (OWNER, True))):
        other = _ingest_direct(bound, number)
        payload = {
            "row_id": "OR-003",
            "candidate_id": other,
            "assay_id": f"asy_019fed25-b33e-7740-b280-{700 + number:012d}",
            "candidate_revision": 1,
            "candidate_sha256": _replay(coordinator)["candidates"][other]["content_sha256"],
            "assay_bar_acceptance_sha256": bar["acceptance_sha256"],
            "producer_relation_sha256": bar["producer_relation_sha256"],
        }
        assert _direct(bound, "RequestAssay", payload["assay_id"], payload, actor, human=human) == "accepted"


def test_admission_accepts_the_bootstrap_role_collapses_the_route_refuses(tmp_path, monkeypatch, capsys):
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=ASSAY_FILES, genesis=False)
    coordinator = bound.coordinator

    # Decisive control: admission records genesis from a non-owner; the route then refuses to claim it.
    accepted = _direct(bound, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID, dict(ACCEPTED), OTHER_HUMAN,
                       human=True)  # fmt: skip
    assert accepted == "accepted"
    with pytest.raises(ConflictError):
        coordinator.status(GENESIS_INTENT)

    # Decisive control: admission records the rubric author's own review request.
    steps = _bar_steps()
    for command_type, subject, actor, human in steps[:4]:
        _advance(bound, tmp_path, capsys, BAR_INTENT, command_type, subject, actor, human)
    request = {
        "row_id": "OR-105",
        "authority_kind": "assay_bar",
        "reviewer_actor_id": BAR_REVIEWER,
        "prospective_producer_ref": spec_assay.producer_ref(PRODUCER),
    }
    assert _direct(bound, "RequestW11AuthorityReview", steps[4][1], request, PINNED_AUTHOR) == "accepted"
    with pytest.raises(ConflictError):
        coordinator.status(BAR_INTENT)


def test_route_refuses_a_foreign_effect_on_a_partial_bar_before_appending(tmp_path, monkeypatch, capsys):
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=ASSAY_FILES, genesis=False)
    coordinator = bound.coordinator
    _advance(bound, tmp_path, capsys, GENESIS_INTENT, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID,
             OWNER, human=True)  # fmt: skip
    register_rubric, register_scope = _bar_steps()[:2]
    _advance(bound, tmp_path, capsys, BAR_INTENT, *register_rubric)

    # Admission observes the rubric before the scope is registered. Appending the scope would leave the
    # route's own observation permanently inadmissible, so the foreign effect must conflict first.
    observation = {"row_id": "OR-103", "authority_kind": "assay_bar"}
    assert _direct(bound, "ObserveW11AuthorityFile", register_rubric[1], observation, RUBRIC_OBSERVER) == "accepted"
    with pytest.raises(ConflictError, match="did not issue"):
        coordinator.status(BAR_INTENT)
    command_type, subject, actor, human = register_scope
    grant = _grant(bound, command_type, subject, actor, human=human)
    assert "did not issue" in _refuse(bound, tmp_path, capsys, BAR_INTENT, grant, actor)


# 06s Phase 4a-2 (P-058): the brief, the return, the outcome review and the decision.
SPEC_01_FILES = (
    *ASSAY_FILES,
    spec_assay.ROUTE_PACKAGE_PATH,
    ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
)
RETURN_EVIDENCE = {
    "axis_results": [
        {
            "axis_id": "identity",
            "value": True,
            "rationale": "The returned sources are exactly the ones the issued brief names.",
            "unmet_condition_codes": [],
        }
    ],
    "prohibited_inferences": ["The scorecard does not itself authorize promotion."],
    "review_requirements": ["independent-review"],
    "direct_sources": ["Damrich, Berens and Kobak (2024), repository tag neurips2024"],
    "findings": ["The accepted fixture rubric expresses only its identity gate."],
    "validation": ["The inherited scorecard rule admits the derived scorecard."],
    "unresolved_findings": ["SPEC-01's own axes need governed Assay authority content (Phase 5 prep)."],
    "limitations": ["scratch store with the W11 fixture Assay bar"],
}
OUTCOME_VERDICT_EVIDENCE = {
    "reviewer_profile": "independent-assay-reviewer",
    "reviewer_session": "session:spec-01-outcome-review",
    "reviewer_model_metadata": "model:independent",
    "context_manifest_id": "ctx_019fed25-b33e-7740-b280-000000000421",
    "context_manifest_sha256": "c" * 64,
    "trace_visibility_evidence_refs": ["trace:spec-01-outcome-review"],
    "findings": [],
    "limitations": ["the fixture Assay bar scores identity only"],
}
PARK_EVIDENCE = {
    "selected_option": "PARK",
    "revisit_triggers": ["governed Assay authority content that expresses SPEC-01's axes"],
}
# 06s Phase 4a′ (P-058, 2026-09-17): collection stopped before any source or validation was reached, which a
# Partial return may state with empty direct sources and validation; its findings must still say why.
PARTIAL_EVIDENCE = {
    "completed_axes": [],
    "completed_evidence": [],
    "unmet_axes": ["identity"],
    "unmet_evidence": ["The issued brief's sources were not reached before collection stopped."],
    "reason_codes": ["collection_stopped"],
    "limitations": ["scratch store with the W11 fixture Assay bar"],
    "revisit_requirements": ["SPEC-01 source access restored"],
    "mechanical_recommendation": "UNABLE_TO_SCORE",
    "direct_sources": [],
    "findings": ["Collection stopped before the identity gate could be answered."],
    "validation": [],
    "unresolved_findings": [],
    "prohibited_inferences": ["A Partial Assay is not a PROMOTE."],
}


def spec_01_intent(action: str, candidate_id: str, **extra) -> dict:
    return {"action": action, "reason": f"advance {action} on the public route", "candidate_id": candidate_id, **extra}


def _invoke(bound, tmp_path, capsys, intent: dict, grant: str, actor: str, *, evidence=None, refused=False):
    """Drive one invocation through the genuine CLI; a refusal must append nothing."""
    intent_path = tmp_path / "spec-01-intent.json"
    intent_path.write_bytes(canonical_bytes(intent if evidence is None else {**intent, "evidence": evidence}))
    config_path = tmp_path / "spec-01-operator.json"
    config_path.write_bytes(canonical_bytes({**bound.config, "authority_grant_id": grant, "operator_actor_id": actor}))
    before = _tail(bound.coordinator)
    args = ["discovery", "spec", "advance", "--operator-config", str(config_path)]
    code = cli.main([*args, "--action", intent["action"], "--input", str(intent_path)])
    captured = capsys.readouterr()
    if refused:
        assert code == 1, captured.out
        assert _tail(bound.coordinator) == before, "a refused invocation appended an event"
        return captured.err
    assert code == 0, captured.err
    return json.loads(captured.out)


def _run(bound, tmp_path, capsys, intent, command_type, subject, actor, *, human=False, evidence=None) -> dict:
    grant = _grant(bound, command_type, subject, actor, human=human)
    return _invoke(bound, tmp_path, capsys, intent, grant, actor, evidence=evidence)


def _requested(bound, tmp_path, capsys, source_repo) -> str:  # noqa: F811
    """Import genesis, accept the bar, observe the source and request its Assay, all on the public route."""
    _advance(bound, tmp_path, capsys, GENESIS_INTENT, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID,
             OWNER, human=True)  # fmt: skip
    for command_type, subject, actor, human in _bar_steps():
        _advance(bound, tmp_path, capsys, BAR_INTENT, command_type, subject, actor, human)
    candidate_id = _observe(bound, tmp_path, capsys, source_repo)
    _run(bound, tmp_path, capsys, request_intent(candidate_id), "RequestAssay", candidate_id, STEWARD)
    return candidate_id


def _seed_task_naming(bound, candidate_id: str, monkeypatch, *, also_naming=(), outcome=None):
    """Seed the operational Task that names the Candidate, with its Attempt started (P-058, 2026-09-15).

    ``also_naming`` adds further portfolio references; ``outcome`` ends the Attempt after it starts.
    """
    original = c1.create_task_command

    def naming_candidate(*args, **kwargs):
        command = original(*args, **kwargs)
        definition = command["payload"]["definition"]
        definition["portfolio_refs"] = [candidate_id, *also_naming]
        definition.pop("content_sha256")
        definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
        return command

    monkeypatch.setattr(c1, "create_task_command", naming_candidate)
    return _seed_bound_task(bound, outcome=outcome)


def test_public_spec_01_path_reaches_an_accepted_project_use_result(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    task = _seed_task_naming(bound, candidate_id, monkeypatch)
    attempt = _streams(coordinator)[c1.ATTEMPT_ID]

    prepared = _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
                    ids["brief_id"], OWNER, human=True)  # fmt: skip
    assert prepared["state"] == "completed"
    brief = coordinator.objects.read(spec_assay.BRIEF_KIND, ids["brief_id"], 1)
    package = json.loads((REPO_ROOT / spec_assay.ROUTE_PACKAGE_PATH).read_bytes())
    assert brief["brief_source"]["sha256"] == next(s for s in package["sources"] if s["alias"] == "SPEC-01")["sha256"]
    assert brief["task"] == {
        "task_id": c1.TASK_ID,
        "task_revision": attempt["task_revision"],
        "attempt_id": c1.ATTEMPT_ID,
        "dispatch_id": attempt["dispatch_id"],
        "context_packet_id": attempt["start"]["context_packet_id"],
        "code_identity": attempt["start"]["code_identity"],
        "environment_fingerprint": attempt["start"]["environment_fingerprint"],
    }

    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    registered = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=RETURN_EVIDENCE)
    assert registered["state"] == "prepared" and registered["next_effect"] == "RecordAssayScore"
    # A lost response is answered from the committed receipt; nothing is appended.
    tail = _tail(coordinator)
    retried = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=RETURN_EVIDENCE)
    assert retried["receipt"] == registered["receipt"] and _tail(coordinator) == tail
    scored = _run(bound, tmp_path, capsys, return_intent, "RecordAssayScore", candidate_id, PRODUCER,
                  evidence=RETURN_EVIDENCE)  # fmt: skip
    assert scored["state"] == "completed"
    returned = coordinator.objects.read(spec_assay.RETURN_KIND, ids["return_id"], 1)
    assert returned["brief"]["artefact_id"] == ids["brief_id"] and returned["task"] == brief["task"]
    assert returned["operator_return"] == RETURN_EVIDENCE
    assert returned["scorecard"]["mechanical_recommendation"] == "PROMOTE"
    assert _replay(coordinator)["assays"][ids["assay_id"]]["scorecard_sha256"] == returned["scorecard_sha256"]
    # The operator records are closed: an unrecognised field is refused.
    schemas = coordinator.schemas
    for schema_id, document in ((spec_assay.BRIEF_SCHEMA_ID, brief), (spec_assay.RETURN_SCHEMA_ID, returned)):
        with pytest.raises(SchemaError):
            schemas.validate(schema_id, {**document, "unrecognised": True}, schema_version="1.0.0")

    review_intent = spec_01_intent(spec_assay.REVIEW, candidate_id)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    reviewed = _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["review_id"],
                    OUTCOME_REVIEWER, evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert reviewed["state"] == "completed"
    verdict = _replay(coordinator)["reviews"][ids["review_id"]]
    assert verdict["status"] == "satisfied"

    decide_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PARK")
    _run(bound, tmp_path, capsys, decide_intent, "ProposePromotionDecision", candidate_id, PROPOSER)
    decided = _run(bound, tmp_path, capsys, decide_intent, "ResolveDecision", ids["decision_id"], OWNER, human=True,
                   evidence=PARK_EVIDENCE)  # fmt: skip
    assert decided["state"] == "completed"
    assert _replay(coordinator)["candidates"][candidate_id]["status"] == "parked"

    # The listing re-derives every state from the ledger alone.
    states = {
        entry["action"]: entry.get("state")
        for entry in coordinator.status()["actions"]
        if entry.get("candidate_id") == candidate_id
    }
    for action in (spec_assay.REQUEST, spec_assay.PREPARE, spec_assay.RETURN, spec_assay.REVIEW, spec_assay.DECIDE):
        assert states[action] == "completed", action

    # The same Task closes through close_task, and its project-use decision is accepted.
    outcome = c1._c1_command(
        c1._command_id(9001),
        _OUTCOME_COMMANDS["completed"],
        c1.ATTEMPT_ID,
        coordinator.ledger.snapshot().stream_versions[c1.ATTEMPT_ID],
        _outcome_payload("completed", EVIDENCE_IDS),
    )
    assert task.seeding.submit(outcome).status == "accepted"
    for artefact_id in EVIDENCE_IDS:
        grant = activate_lifecycle_grant(
            bound.harness, subject_kind="artefact", subject_id=artefact_id, command_types=("RegisterArtefact",)
        )
        manifest = _artefact_manifest(artefact_id)
        content = canonical_bytes({"artefact_id": artefact_id, "outcome": "passed"})
        manifest.update(
            content_sha256=sha256_hex(content), size_bytes=len(content), relative_path=f"evidence/{artefact_id}.json"
        )
        payload = {"new_artefact_id": artefact_id, "manifest": manifest}
        command = c1._c1_command(
            new_id("command"), "RegisterArtefact", artefact_id, 0, payload, authority_grant_id=grant
        )
        assert task.seeding.submit(command).status == "accepted"
    for effect in spec_task.EFFECTS:
        _advance_task(task, effect, tmp_path, capsys)

    task.decision_id = spec_result.subject_id(PROJECT_ID, c1.TASK_ID)

    def use_grant(actor, commands, *, agent=False):
        return activate_lifecycle_grant(
            bound.harness,
            subject_kind="artefact",
            subject_id=task.decision_id,
            actor_id=actor,
            allowed_actor_classes=("agent",) if agent else ("human",),
            command_types=commands,
            grant_id=new_id("authority_grant"),
        )

    task.grants_project_use = {
        "register": use_grant(OWNER, ("RegisterArtefact",)),
        "review": use_grant(REVIEWER, ("RecordScientificReview",), agent=True),
        "use": use_grant(OWNER, ("SetArtefactUseAuthority",)),
    }
    _accept_decision(task, tmp_path, capsys)
    result = _result(task, tmp_path, capsys, "json")
    assert result["status"] == "accepted"
    decision = result["project_use_decision"]["decision"]
    assert decision["decision_id"] == ids["decision_id"] and decision["selected_option"] == "PARK"
    assert result["project_use_decision"]["spike"] is None


def test_spec_01_route_refuses_the_role_collapses_that_admission_accepts(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))

    # With no Task naming the Candidate, the brief has no real operational provenance to cite.
    prepare_intent = spec_01_intent(spec_assay.PREPARE, candidate_id)
    brief_grant = _grant(bound, "RegisterArtefact", ids["brief_id"], OWNER, human=True)
    assert "Task naming Candidate" in _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER, refused=True)
    _seed_task_naming(bound, candidate_id, monkeypatch)
    _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER)

    # Operator evidence that admission would refuse at OR-004 is refused before the return is registered.
    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    untyped = {**RETURN_EVIDENCE, "axis_results": [{**RETURN_EVIDENCE["axis_results"][0], "value": 1}]}
    inexact = {key: value for key, value in RETURN_EVIDENCE.items() if key != "findings"}
    # The brief requires a direct-source table, findings and focused validation; an empty section is refused.
    sections = ("direct_sources", "findings", "validation")
    empty = tuple(({**RETURN_EVIDENCE, section: []}, "not schema-valid") for section in sections)
    for evidence, reason in ((untyped, "scorecard"), (inexact, "evidence fields are not exact"), *empty):
        assert reason in _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=evidence,
                                 refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=RETURN_EVIDENCE)
    # The Assay producer's own invocation must carry the exact return it scores; the owner registered the bytes.
    other_return = {**RETURN_EVIDENCE, "findings": ["A finding the operator did not return."]}
    score_grant = _grant(bound, "RecordAssayScore", candidate_id, PRODUCER)
    for evidence, reason in ((None, "evidence fields are not exact"), (other_return, "exact operator return")):
        assert reason in _invoke(bound, tmp_path, capsys, return_intent, score_grant, PRODUCER, evidence=evidence,
                                 refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, return_intent, score_grant, PRODUCER, evidence=RETURN_EVIDENCE)
    # A completed action conflicts on any invocation that repeats no committed effect, such as changed evidence.
    assert "already completed" in _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER,
                                          evidence=other_return, refused=True)  # fmt: skip

    review_intent = spec_01_intent(spec_assay.REVIEW, candidate_id)
    for actor, human in ((PRODUCER, False), (OWNER, True)):
        grant = _grant(bound, "RequestDiscoveryOutcomeReview", candidate_id, actor, human=human)
        assert "outcome-review requester" in _invoke(bound, tmp_path, capsys, review_intent, grant, actor, refused=True)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    owner_review = _grant(bound, "ReviewDiscoveryOutcome", ids["review_id"], OWNER, human=True)
    assert "must not be the owner" in _invoke(bound, tmp_path, capsys, review_intent, owner_review, OWNER,
                                              evidence=OUTCOME_VERDICT_EVIDENCE, refused=True)  # fmt: skip
    review_grant = _grant(bound, "ReviewDiscoveryOutcome", ids["review_id"], OUTCOME_REVIEWER)
    reviewed = _invoke(bound, tmp_path, capsys, review_intent, review_grant, OUTCOME_REVIEWER,
                       evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    # The reviewer's exact repeat is answered from its receipt; the same evidence with an extra field is not a
    # repeat, so it conflicts as it would have been refused before the review was recorded.
    retried = _invoke(bound, tmp_path, capsys, review_intent, review_grant, OUTCOME_REVIEWER,
                      evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert retried["receipt"] == reviewed["receipt"]
    padded = {**OUTCOME_VERDICT_EVIDENCE, "unrecognised": True}
    assert "already completed" in _invoke(bound, tmp_path, capsys, review_intent, review_grant, OUTCOME_REVIEWER,
                                          evidence=padded, refused=True)  # fmt: skip

    decide_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PARK")
    for actor, human in ((PRODUCER, False), (OUTCOME_REVIEWER, False), (OWNER, True)):
        grant = _grant(bound, "ProposePromotionDecision", candidate_id, actor, human=human)
        assert "proposer" in _invoke(bound, tmp_path, capsys, decide_intent, grant, actor, refused=True)
    # The scorecard is a mechanical PROMOTE, but the return lists an unresolved finding: PROMOTE is neither
    # proposed nor, whatever was proposed, selected.
    promote_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PROMOTE")
    grant = _grant(bound, "ProposePromotionDecision", candidate_id, PROPOSER)
    assert "unresolved findings" in _invoke(bound, tmp_path, capsys, promote_intent, grant, PROPOSER, refused=True)
    _run(bound, tmp_path, capsys, decide_intent, "ProposePromotionDecision", candidate_id, PROPOSER)
    resolve_grant = _grant(bound, "ResolveDecision", ids["decision_id"], OWNER, human=True)
    assert "revisit triggers" in _invoke(bound, tmp_path, capsys, decide_intent, resolve_grant, OWNER,
                                         evidence={**PARK_EVIDENCE, "revisit_triggers": []}, refused=True)  # fmt: skip
    promote = {"selected_option": "PROMOTE", "revisit_triggers": []}
    assert "unresolved findings" in _invoke(bound, tmp_path, capsys, decide_intent, resolve_grant, OWNER,
                                            evidence=promote, refused=True)  # fmt: skip

    # Decisive controls on a second Candidate: inherited admission accepts each collapse the route refused.
    other = _ingest_direct(bound, 0)
    other_assay = "asy_019fed25-b33e-7740-b280-000000000800"
    other_review = "rev_019fed25-b33e-7740-b280-000000000801"
    other_decision = "dec_019fed25-b33e-7740-b280-000000000802"
    projection = _replay(coordinator)
    bar = projection["assay_bar_authority"]
    request = {
        "row_id": "OR-003",
        "candidate_id": other,
        "assay_id": other_assay,
        "candidate_revision": 1,
        "candidate_sha256": projection["candidates"][other]["content_sha256"],
        "assay_bar_acceptance_sha256": bar["acceptance_sha256"],
        "producer_relation_sha256": bar["producer_relation_sha256"],
    }
    assert _direct(bound, "RequestAssay", other_assay, request, STEWARD) == "accepted"
    projection = _replay(coordinator)
    subjects = {"candidate_id": other, "assay_id": other_assay}
    scorecard = spec_assay._scorecard(subjects, projection, projection["candidates"][other],
                                      projection["assays"][other_assay], RETURN_EVIDENCE,
                                      coordinator._assay_context())  # fmt: skip
    # The mechanical recommendation is the one the inherited scorecard rule admits: a failed gate is KILL.
    failing = {**RETURN_EVIDENCE, "axis_results": [{**RETURN_EVIDENCE["axis_results"][0], "value": False}]}
    killed = spec_assay._scorecard(subjects, projection, projection["candidates"][other],
                                   projection["assays"][other_assay], failing, coordinator._assay_context())  # fmt: skip
    assert (scorecard["mechanical_recommendation"], killed["mechanical_recommendation"]) == ("PROMOTE", "KILL")
    digest = sha256_hex(canonical_bytes(scorecard))
    score = {**subjects, "row_id": "OR-004", "scorecard_sha256": digest, "scorecard_artifact": scorecard,
             "producer_relation_sha256": bar["producer_relation_sha256"]}  # fmt: skip
    # Admission records the producer's score, which carries no operator return.
    assert _direct(bound, "RecordAssayScore", other_assay, score, PRODUCER) == "accepted"
    contract = {
        "review_type": "provenance",
        "new_review_id": other_review,
        "subject_ids": [other_assay],
        "subject_hashes": [digest],
        "governing_refs": ["W11:OR-034"],
        "review_questions": ["Is the scorecard exact?"],
        "required_evidence_refs": ["scorecard:exact"],
        "required_lanes": ["provenance"],
        "reviewer_capability": ["assay-independent-review"],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": ["approve", "changes_requested", "reject"],
        "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
        "deadline": "2026-12-31T00:00:00Z",
        "escalation_rule": "owner-ruling",
    }
    requested = {**subjects, "row_id": "OR-034", "review_id": other_review, "subject_sha256": digest,
                 "review_contract": contract}  # fmt: skip
    assert _direct(bound, "RequestDiscoveryOutcomeReview", other_review, requested, PRODUCER) == "accepted"
    verdict = {
        "review_id": other_review,
        "verdict": "approve",
        "findings": [],
        "required_evidence_refs": ["scorecard:exact"],
        "limitations": [],
        "conditions": [],
        "reviewer_actor_id": OWNER,
        **{
            key: OUTCOME_VERDICT_EVIDENCE[key]
            for key in (
                "reviewer_profile",
                "reviewer_session",
                "reviewer_model_metadata",
                "context_manifest_id",
                "context_manifest_sha256",
                "trace_visibility_evidence_refs",
            )
        },  # fmt: skip
        "unchanged_subject_sha256": digest,
        "producing_attempt_id": "att_019fed25-b33e-7740-b280-000000000803",
        "computed_independence_grade": "independent",
    }
    recorded = {**subjects, "row_id": "OR-006", "review_id": other_review, "subject_sha256": digest,
                "verdict": "approve", "review_verdict": verdict}  # fmt: skip
    assert _direct(bound, "ReviewDiscoveryOutcome", other_review, recorded, OWNER, human=True) == "accepted"
    projection = _replay(coordinator)
    assay, review, candidate = (projection["assays"][other_assay], projection["reviews"][other_review],
                                projection["candidates"][other])  # fmt: skip
    aggregate = _record_ref(other_assay, assay["version"], _aggregate_content_hash(assay))
    proposal = {
        "row_id": "OR-012",
        "candidate_id": other,
        "decision_id": other_decision,
        "review_id": other_review,
        "w2_payload": {
            "question": "assay_to_spike",
            "recommendation": "PARK",
            "new_decision_id": other_decision,
            "decision_revision": 1,
            "decision_kind": "design_lock",
            "options": ["PROMOTE", "PARK", "KILL"],
            "governing_evidence_refs": ["evidence:exact"],
            "affected_task_ids": [],
            "affected_claim_ids": [],
            "required_authority": "owner",
            "expires_at": "2026-12-31T00:00:00Z",
            "review_date": "2026-09-11T00:00:00Z",
            "consequences": ["park the candidate"],
        },
        "promotion_relation": {
            "schema_id": "ars://portfolio/relation/discovery-promotion",
            "schema_version": "1.0.0",
            "relation_kind": "discovery_promotion",
            "decision_id": other_decision,
            "candidate_ref": _record_ref(other, candidate["revision"], candidate["content_sha256"]),
            "gate": "assay_to_spike",
            "aggregate_ref": aggregate,
            "aggregate_relation_hash": assay["producer_relation_sha256"],
            "evidence_ref": aggregate,
            "selected_option": "PARK",
            "next_candidate_state": "parked",
            "rationale": "Decisive control: the producer proposes.",
            "considered_evidence_refs": [_review_ref(review)],
            "conditions": [],
            "effective_scope": f"assay_to_spike:{other}",
            "revisit_triggers": [],
            "actor_id": PRODUCER,
        },
    }
    assert _direct(bound, "ProposePromotionDecision", other_decision, proposal, PRODUCER) == "accepted"


def test_operator_record_bytes_are_reused_only_when_they_rederive(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    task = _seed_task_naming(bound, candidate_id, monkeypatch)
    context = coordinator._assay_context()
    stopped_at = "2026-09-10T00:00:00Z"

    # A process published the brief's bytes and stopped before registering them. The exact record this
    # route derives at their causal prefix is reused rather than replaced.
    orphan = spec_assay._build(spec_assay._BRIEF, ids, coordinator.ledger.snapshot().events, context, actor_id=OWNER,
                               recorded_at=stopped_at, evidence=None)  # fmt: skip
    coordinator.objects.write(spec_assay.BRIEF_KIND, ids["brief_id"], 1, orphan)
    prepare_intent = spec_01_intent(spec_assay.PREPARE, candidate_id)
    prepared = _run(bound, tmp_path, capsys, prepare_intent, "RegisterArtefact", ids["brief_id"], OWNER, human=True)
    assert prepared["state"] == "completed"
    assert coordinator.objects.read(spec_assay.BRIEF_KIND, ids["brief_id"], 1) == orphan

    # Return bytes left for different operator content bind another record, so this invocation is
    # refused with nothing appended. The invocation carrying that content reuses them.
    other_content = {**RETURN_EVIDENCE, "findings": ["A finding the stopped invocation carried."]}
    stale = spec_assay._build(spec_assay._RETURN, ids, coordinator.ledger.snapshot().events, context,
                              actor_id=OWNER, recorded_at=stopped_at, evidence=other_content)  # fmt: skip
    coordinator.objects.write(spec_assay.RETURN_KIND, ids["return_id"], 1, stale)
    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    assert "bind a different record" in _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER,
                                                evidence=RETURN_EVIDENCE, refused=True)  # fmt: skip
    reused = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=other_content)
    assert reused["state"] == "prepared"
    assert coordinator.objects.read(spec_assay.RETURN_KIND, ids["return_id"], 1) == stale

    # A registration on an operator record's stream that this route did not issue is foreign evidence.
    foreign_candidate = "obj_019fed25-b33e-7740-b280-000000000900"
    artefact_id = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, foreign_candidate))["brief_id"]
    grant = activate_lifecycle_grant(
        bound.harness, subject_kind="artefact", subject_id=artefact_id, command_types=("RegisterArtefact",)
    )
    payload = {"new_artefact_id": artefact_id, "manifest": _artefact_manifest(artefact_id)}
    command = c1._c1_command(new_id("command"), "RegisterArtefact", artefact_id, 0, payload, authority_grant_id=grant)
    assert task.seeding.submit(command).status == "accepted"
    with pytest.raises(ConflictError, match="did not issue"):
        coordinator.status(spec_01_intent(spec_assay.PREPARE, foreign_candidate))


def test_orphaned_record_bytes_are_refused_once_their_prerequisites_lapse(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    _seed_task_naming(bound, candidate_id, monkeypatch)
    context = coordinator._assay_context()

    # A process published the brief's exact bytes while the Assay was collecting evidence, then stopped.
    orphan = spec_assay._build(spec_assay._BRIEF, ids, coordinator.ledger.snapshot().events, context, actor_id=OWNER,
                               recorded_at="2026-09-10T00:00:00Z", evidence=None)  # fmt: skip
    coordinator.objects.write(spec_assay.BRIEF_KIND, ids["brief_id"], 1, orphan)

    # The Assay is then scored through inherited admission, so no brief may be issued for it any more.
    projection = _replay(coordinator)
    subjects = {"candidate_id": candidate_id, "assay_id": ids["assay_id"]}
    scorecard = spec_assay._scorecard(subjects, projection, projection["candidates"][candidate_id],
                                      projection["assays"][ids["assay_id"]], RETURN_EVIDENCE, context)  # fmt: skip
    score = {**subjects, "row_id": "OR-004", "scorecard_sha256": sha256_hex(canonical_bytes(scorecard)),
             "scorecard_artifact": scorecard,
             "producer_relation_sha256": projection["assay_bar_authority"]["producer_relation_sha256"]}  # fmt: skip
    assert _direct(bound, "RecordAssayScore", ids["assay_id"], score, PRODUCER) == "accepted"

    # The orphan still re-derives at its own causal prefix, but it is not registered out of order.
    prepare_intent = spec_01_intent(spec_assay.PREPARE, candidate_id)
    brief_grant = _grant(bound, "RegisterArtefact", ids["brief_id"], OWNER, human=True)
    assert "still collecting evidence" in _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER,
                                                  refused=True)  # fmt: skip
    assert coordinator.status(prepare_intent)["state"] == "not_started"


def test_operator_records_cite_the_dispatched_attempt_exactly(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    task = _seed_task_naming(bound, candidate_id, monkeypatch)
    start = _streams(coordinator)[c1.ATTEMPT_ID]["start"]
    prepared = _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
                    ids["brief_id"], OWNER, human=True)  # fmt: skip
    assert prepared["state"] == "completed"

    # The manifest names the producing Attempt, so it carries that Attempt's own code and environment
    # identities. Here they differ from the store binding's.
    brief = coordinator.objects.read(spec_assay.BRIEF_KIND, ids["brief_id"], 1)
    events = list(coordinator.ledger.snapshot().events)
    manifest = spec_assay._one(events, ids["brief_id"], "ArtefactRegistered")["payload"]["manifest"]
    subject = brief["governed_code_subject"]
    assert manifest["code_commit"] == start["code_identity"]
    assert manifest["environment_fingerprint"] == start["environment_fingerprint"]
    assert start["code_identity"] != "git:sha1:" + subject["git_head"]
    assert start["environment_fingerprint"] != subject["recovery_binding_sha256"]
    # A code identity that is not a commit a manifest can record does not make a valid record.
    uncommitted = {**brief, "task": {**brief["task"], "code_identity": "session:c1-luna"}}
    with pytest.raises(SchemaError):
        coordinator.schemas.validate(spec_assay.BRIEF_SCHEMA_ID, uncommitted, schema_version="1.0.0")

    # The Task is amended after its Attempt was dispatched, so the Attempt never ran the Task's current
    # definition, and the return may not cite it.
    version = coordinator.ledger.snapshot().stream_versions[c1.TASK_ID]
    assert task.seeding.submit(c1._task_amendment_command(number=9101, expected_stream_version=version)).status == (
        "accepted"
    )
    streams = _streams(coordinator)
    assert (streams[c1.TASK_ID]["current_revision"], streams[c1.ATTEMPT_ID]["task_revision"]) == (2, 1)
    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    assert "unamended since" in _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER,
                                        evidence=RETURN_EVIDENCE, refused=True)  # fmt: skip
    assert coordinator.status(return_intent)["state"] == "not_started"


def test_records_need_a_running_attempt_and_a_single_candidate_task(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    # The Task also names a reference that is not yet a registered Candidate, and its only Attempt has failed.
    other = "obj_019fed25-b33e-7740-b280-000000000901"
    _seed_task_naming(bound, candidate_id, monkeypatch, also_naming=(other,), outcome="failed")
    assert _streams(coordinator)[c1.ATTEMPT_ID]["status"] == "failed"

    # A finished Attempt cannot be cited as producing a record created after it ended.
    prepare_intent = spec_01_intent(spec_assay.PREPARE, candidate_id)
    brief_grant = _grant(bound, "RegisterArtefact", ids["brief_id"], OWNER, human=True)
    assert "to be running" in _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER, refused=True)

    # Once the other reference is a registered Candidate, the Task names two, and the project-use result it
    # would close could never be reached.
    assert _ingest_direct(bound, 1) == other
    assert "no other registered Candidate" in _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER,
                                                      refused=True)  # fmt: skip
    assert coordinator.status(prepare_intent)["state"] == "not_started"


def test_the_producer_return_is_compared_as_canonical_json(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    _seed_task_naming(bound, candidate_id, monkeypatch)
    _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
         ids["brief_id"], OWNER, human=True)  # fmt: skip
    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=RETURN_EVIDENCE)
    returned = coordinator.objects.read(spec_assay.RETURN_KIND, ids["return_id"], 1)
    assert returned["operator_return"]["axis_results"][0]["value"] is True

    # The integer 1 equals the registered boolean in Python, but it is not the registered return.
    substituted = {**RETURN_EVIDENCE, "axis_results": [{**RETURN_EVIDENCE["axis_results"][0], "value": 1}]}
    assert substituted == RETURN_EVIDENCE and canonical_bytes(substituted) != canonical_bytes(RETURN_EVIDENCE)
    score_grant = _grant(bound, "RecordAssayScore", candidate_id, PRODUCER)
    assert "exact operator return" in _invoke(bound, tmp_path, capsys, return_intent, score_grant, PRODUCER,
                                              evidence=substituted, refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, return_intent, score_grant, PRODUCER, evidence=RETURN_EVIDENCE)

    # On the completed return, each exact repeat is answered from its receipt; the substitution is not.
    for grant, actor in ((return_grant, OWNER), (score_grant, PRODUCER)):
        tail = _tail(coordinator)
        retried = _invoke(bound, tmp_path, capsys, return_intent, grant, actor, evidence=RETURN_EVIDENCE)
        assert retried["state"] == "completed" and retried["receipt"]["status"] == "accepted", actor
        assert _tail(coordinator) == tail
        assert "already completed" in _invoke(bound, tmp_path, capsys, return_intent, grant, actor,
                                              evidence=substituted, refused=True), actor  # fmt: skip


def test_operator_record_registration_refuses_a_ledger_that_moved_after_derivation(
    tmp_path,
    monkeypatch,
    capsys,
    source_repo,  # noqa: F811
):
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    task = _seed_task_naming(bound, candidate_id, monkeypatch)
    prepare_intent = spec_01_intent(spec_assay.PREPARE, candidate_id)
    brief_grant = _grant(bound, "RegisterArtefact", ids["brief_id"], OWNER, human=True)
    derive, moved = spec_assay.next_command, []

    def derive_then_amend(*args, **kwargs):
        built = derive(*args, **kwargs)
        # Another writer amends the Task after the brief is derived, lapsing its prerequisite before the lock.
        version = coordinator.ledger.snapshot().stream_versions[c1.TASK_ID]
        amendment = c1._task_amendment_command(number=9101, expected_stream_version=version)
        assert task.seeding.submit(amendment).status == "accepted"
        moved.append(coordinator.ledger.snapshot())
        return built

    intent_path, config_path = tmp_path / "moved-intent.json", tmp_path / "moved-operator.json"
    intent_path.write_bytes(canonical_bytes(prepare_intent))
    config_path.write_bytes(
        canonical_bytes({**bound.config, "authority_grant_id": brief_grant, "operator_actor_id": OWNER})
    )
    args = ["discovery", "spec", "advance", "--operator-config", str(config_path)]
    before = _tail(coordinator)
    with monkeypatch.context() as patched:
        patched.setattr(spec_assay, "next_command", derive_then_amend)
        code = cli.main([*args, "--action", prepare_intent["action"], "--input", str(intent_path)])
    captured = capsys.readouterr()
    assert code == 1, captured.out
    assert "moved past" in captured.err and "nothing was published" in captured.err, captured.err
    [appended] = moved
    assert _tail(coordinator) == (appended.global_position, appended.event_hash) != before
    assert not coordinator.objects.revision_exists(spec_assay.BRIEF_KIND, ids["brief_id"], 1)
    assert coordinator.status(prepare_intent)["state"] == "not_started"

    # Derived again from the moved ledger, the lapsed prerequisite refuses the brief with nothing appended.
    assert "unamended since" in _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER, refused=True)


def _unevaluated_axis_bar() -> dict[str, bytes]:
    """The committed fixture bar plus one required integer axis, which admission only bounds-checks."""
    rubric = json.loads((REPO_ROOT / spec_assay.ASSAY_RUBRIC_PATH).read_bytes())
    scope = json.loads((REPO_ROOT / spec_assay.ASSAY_SCOPE_PATH).read_bytes())
    axis = {key: value for key, value in rubric["axis_definitions"][0].items() if key != "allowed_set"}
    axis.update(
        axis_id="data_feasibility",
        axis_kind="integer_score",
        bounds={"minimum": 0, "maximum": 3},
        failure_codes=["data_infeasible"],
        value_schema="integer",
        value_type="integer",
    )
    rubric["axis_definitions"].append(axis)
    for field in ("required_axis_ids", "evaluation_order"):
        rubric[field].append("data_feasibility")
    rubric["required_axis_set_hash"] = _axis_set_hash(rubric["required_axis_ids"])
    rubric["content_hash"] = assay_content_sha256(rubric)
    row = {**scope["evidence_rows"][0], "evidence_key": "data-feasibility", "validator_id": "data-feasibility"}
    scope["evidence_rows"].append(row)
    scope["rubric_ref"]["content_hash"] = rubric["content_hash"]
    scope["content_hash"] = assay_content_sha256(scope)
    return {
        spec_assay.ASSAY_RUBRIC_PATH: canonical_bytes(rubric) + b"\n",
        spec_assay.ASSAY_SCOPE_PATH: canonical_bytes(scope) + b"\n",
    }


def test_promote_is_refused_while_the_bar_has_an_unevaluated_axis(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False,
                               repository_overrides=_unevaluated_axis_bar())  # fmt: skip
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    _seed_task_naming(bound, candidate_id, monkeypatch)
    _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
         ids["brief_id"], OWNER, human=True)  # fmt: skip

    # The gate passes and the integer axis scores zero, which SPEC-01 forbids for PROMOTE, yet admission
    # derives a mechanical PROMOTE. Nothing is unresolved, so only the unevaluated axis can block.
    zero = {
        "axis_id": "data_feasibility",
        "value": 0,
        "rationale": "No governed data can support the estimand.",
        "unmet_condition_codes": ["data_infeasible"],
    }
    evidence = {**RETURN_EVIDENCE, "axis_results": [RETURN_EVIDENCE["axis_results"][0], zero],
                "unresolved_findings": []}  # fmt: skip
    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    _run(bound, tmp_path, capsys, return_intent, "RegisterArtefact", ids["return_id"], OWNER, human=True,
         evidence=evidence)  # fmt: skip
    _run(bound, tmp_path, capsys, return_intent, "RecordAssayScore", candidate_id, PRODUCER, evidence=evidence)
    assert _replay(coordinator)["assays"][ids["assay_id"]]["mechanical_recommendation"] == "PROMOTE"
    review_intent = spec_01_intent(spec_assay.REVIEW, candidate_id)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["review_id"], OUTCOME_REVIEWER,
         evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip

    promote_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PROMOTE")
    grant = _grant(bound, "ProposePromotionDecision", candidate_id, PROPOSER)
    assert "does not evaluate" in _invoke(bound, tmp_path, capsys, promote_intent, grant, PROPOSER, refused=True)
    decide_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PARK")
    _run(bound, tmp_path, capsys, decide_intent, "ProposePromotionDecision", candidate_id, PROPOSER)
    resolve_grant = _grant(bound, "ResolveDecision", ids["decision_id"], OWNER, human=True)
    promote = {"selected_option": "PROMOTE", "revisit_triggers": []}
    assert "does not evaluate" in _invoke(bound, tmp_path, capsys, decide_intent, resolve_grant, OWNER,
                                          evidence=promote, refused=True)  # fmt: skip


# 06s Phase 4a′ (P-058, 2026-09-17): the Partial return and its outcome review.
PARTIAL_ARTEFACT_FIELDS = (
    "completed_axes",
    "completed_evidence",
    "unmet_axes",
    "unmet_evidence",
    "reason_codes",
    "limitations",
    "revisit_requirements",
    "mechanical_recommendation",
)


def test_public_spec_01_partial_path_ends_at_a_reviewed_partial_assay(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    _seed_task_naming(bound, candidate_id, monkeypatch)
    start = _streams(coordinator)[c1.ATTEMPT_ID]["start"]
    _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
         ids["brief_id"], OWNER, human=True)  # fmt: skip

    # The owner registers the operator's Partial return; a lost response is answered from its receipt.
    return_intent = spec_01_intent(spec_assay.RETURN_PARTIAL, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    registered = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=PARTIAL_EVIDENCE)
    assert registered["state"] == "prepared" and registered["next_effect"] == "RecordAssayPartial"
    tail = _tail(coordinator)
    retried = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=PARTIAL_EVIDENCE)
    assert retried["receipt"] == registered["receipt"] and _tail(coordinator) == tail
    # The Assay producer's own invocation records the Partial it carries.
    recorded = _run(bound, tmp_path, capsys, return_intent, "RecordAssayPartial", candidate_id, PRODUCER,
                    evidence=PARTIAL_EVIDENCE)  # fmt: skip
    assert recorded["state"] == "completed"

    returned = coordinator.objects.read(spec_assay.PARTIAL_RETURN_KIND, ids["return_id"], 1)
    brief = coordinator.objects.read(spec_assay.BRIEF_KIND, ids["brief_id"], 1)
    assert returned["brief"]["artefact_id"] == ids["brief_id"] and returned["task"] == brief["task"]
    assert returned["operator_partial_return"] == PARTIAL_EVIDENCE
    projection = _replay(coordinator)
    bar, candidate = projection["assay_bar_authority"], projection["candidates"][candidate_id]
    # Every reference in the Partial is derived; only the operator's judgements come from the caller.
    assert returned["partial_artifact"] == {
        "schema_id": "ars://portfolio/assay-partial",
        "schema_version": "1.0.0",
        "assay_id": ids["assay_id"],
        "candidate_ref": _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
        "rubric_ref": bar["acceptance"]["rubric_ref"],
        "scope_ref": bar["acceptance"]["scope_ref"],
        "assay_bar_acceptance_ref": _record_ref(bar["acceptance"]["decision_id"], 1, bar["acceptance_sha256"]),
        "assay_relation_hash": bar["producer_relation_sha256"],
        **{key: PARTIAL_EVIDENCE[key] for key in PARTIAL_ARTEFACT_FIELDS},
    }
    assert returned["partial_sha256"] == sha256_hex(canonical_bytes(returned["partial_artifact"]))
    assay = projection["assays"][ids["assay_id"]]
    assert (assay["status"], assay["outcome_sha256"]) == ("partial_recorded", returned["partial_sha256"])
    manifest = spec_assay._one(list(coordinator.ledger.snapshot().events), ids["return_id"], "ArtefactRegistered")[
        "payload"
    ]["manifest"]
    assert manifest["artefact_schema_id"] == spec_assay.PARTIAL_RETURN_SCHEMA_ID
    assert (manifest["code_commit"], manifest["environment_fingerprint"]) == (
        start["code_identity"],
        start["environment_fingerprint"],
    )
    assert [dependency["input_artefact_id"] for dependency in manifest["input_dependencies"]] == [ids["brief_id"]]
    with pytest.raises(SchemaError):
        coordinator.schemas.validate(spec_assay.PARTIAL_RETURN_SCHEMA_ID, {**returned, "unrecognised": True},
                                     schema_version="1.0.0")  # fmt: skip

    review_intent = spec_01_intent(spec_assay.REVIEW_PARTIAL, candidate_id)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    reviewed = _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["review_id"],
                    OUTCOME_REVIEWER, evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert reviewed["state"] == "completed"

    # 4a′ ends here: a reviewed Partial Assay whose Candidate may be revisited, with no Decision.
    projection = _replay(coordinator)
    assay, candidate = projection["assays"][ids["assay_id"]], projection["candidates"][candidate_id]
    assert projection["reviews"][ids["review_id"]]["status"] == "satisfied"
    assert assay["status"] == "partial_reviewed"
    assert assay["revisit_requirements"] == PARTIAL_EVIDENCE["revisit_requirements"]
    assert candidate["status"] == "assay_revisit_eligible" and candidate.get("decision_id") is None

    # The listing re-derives only the alternative taken; the complete ones are neither listed nor unreadable.
    listing = coordinator.status()["actions"]
    assert not [entry for entry in listing if "unreadable" in entry and entry["action"] in spec_assay.ACTIONS]
    states = {
        entry["action"]: entry["state"]
        for entry in listing
        if entry["action"] in spec_assay.ACTIONS and entry.get("candidate_id") == candidate_id
    }
    assert states == {
        spec_assay.REQUEST: "completed",
        spec_assay.PREPARE: "completed",
        spec_assay.RETURN_PARTIAL: "completed",
        spec_assay.REVIEW_PARTIAL: "completed",
    }
    for action in (spec_assay.RETURN, spec_assay.REVIEW):
        with pytest.raises(ConflictError, match=spec_assay.RETURN_PARTIAL):
            coordinator.status(spec_01_intent(action, candidate_id))
    decide_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PARK")
    grant = _grant(bound, "ProposePromotionDecision", candidate_id, PROPOSER)
    assert "Partial Assay" in _invoke(bound, tmp_path, capsys, decide_intent, grant, PROPOSER, refused=True)


def _partial_request(candidate_id: str, assay_id: str, review_id: str, digest: str) -> dict:
    """A well-formed OR-035 request for a decisive control, bypassing the route."""
    return {
        "row_id": "OR-035",
        "candidate_id": candidate_id,
        "assay_id": assay_id,
        "review_id": review_id,
        "subject_sha256": digest,
        "review_contract": {
            "review_type": "provenance",
            "new_review_id": review_id,
            "subject_ids": [assay_id],
            "subject_hashes": [digest],
            "governing_refs": ["W11:OR-035"],
            "review_questions": ["Is the Partial exact?"],
            "required_evidence_refs": ["assay-partial:exact"],
            "required_lanes": ["provenance"],
            "reviewer_capability": ["assay-independent-review"],
            "required_independence_grade": "independent",
            "visibility_policy": "owner-visible",
            "allowed_verdicts": ["approve", "changes_requested", "reject"],
            "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
            "deadline": "2026-12-31T00:00:00Z",
            "escalation_rule": "owner-ruling",
        },
    }


def test_spec_01_partial_route_refuses_what_admission_accepts(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    coordinator = bound.coordinator
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    _seed_task_naming(bound, candidate_id, monkeypatch)
    _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
         ids["brief_id"], OWNER, human=True)  # fmt: skip

    # A Partial return without findings, one the inherited Partial rule would refuse at OR-005, and one with
    # an inexact field set are each refused before anything is registered.
    return_intent = spec_01_intent(spec_assay.RETURN_PARTIAL, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["return_id"], OWNER, human=True)
    no_findings = {**PARTIAL_EVIDENCE, "findings": []}
    unpartitioned = {**PARTIAL_EVIDENCE, "unmet_axes": ["not-a-rubric-axis"]}
    inexact = {key: value for key, value in PARTIAL_EVIDENCE.items() if key != "validation"}
    for evidence, reason in (
        (no_findings, "not schema-valid"),
        (unpartitioned, "would not be admitted"),
        (inexact, "evidence fields are not exact"),
    ):
        assert reason in _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=evidence,
                                 refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=PARTIAL_EVIDENCE)
    # The alternatives share the return identity, so the complete return is now excluded for this Assay.
    complete_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    assert "excluded" in _invoke(bound, tmp_path, capsys, complete_intent, return_grant, OWNER,
                                 evidence=RETURN_EVIDENCE, refused=True)  # fmt: skip

    # The Assay producer's own invocation must carry the exact Partial return the owner registered.
    other_partial = {**PARTIAL_EVIDENCE, "reason_codes": ["a reason the operator did not return"]}
    partial_grant = _grant(bound, "RecordAssayPartial", candidate_id, PRODUCER)
    for evidence, reason in ((None, "evidence fields are not exact"), (other_partial, "exact operator Partial return")):
        assert reason in _invoke(bound, tmp_path, capsys, return_intent, partial_grant, PRODUCER, evidence=evidence,
                                 refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, return_intent, partial_grant, PRODUCER, evidence=PARTIAL_EVIDENCE)
    assert "already completed" in _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER,
                                          evidence=other_partial, refused=True)  # fmt: skip

    review_intent = spec_01_intent(spec_assay.REVIEW_PARTIAL, candidate_id)
    for actor, human in ((PRODUCER, False), (OWNER, True)):
        grant = _grant(bound, "RequestDiscoveryOutcomeReview", candidate_id, actor, human=human)
        assert "outcome-review requester" in _invoke(bound, tmp_path, capsys, review_intent, grant, actor, refused=True)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    owner_review = _grant(bound, "ReviewDiscoveryOutcome", ids["review_id"], OWNER, human=True)
    assert "must not be the owner" in _invoke(bound, tmp_path, capsys, review_intent, owner_review, OWNER,
                                              evidence=OUTCOME_VERDICT_EVIDENCE, refused=True)  # fmt: skip
    review_grant = _grant(bound, "ReviewDiscoveryOutcome", ids["review_id"], OUTCOME_REVIEWER)
    reviewed = _invoke(bound, tmp_path, capsys, review_intent, review_grant, OUTCOME_REVIEWER,
                       evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    retried = _invoke(bound, tmp_path, capsys, review_intent, review_grant, OUTCOME_REVIEWER,
                      evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert retried["receipt"] == reviewed["receipt"]
    padded = {**OUTCOME_VERDICT_EVIDENCE, "unrecognised": True}
    assert "already completed" in _invoke(bound, tmp_path, capsys, review_intent, review_grant, OUTCOME_REVIEWER,
                                          evidence=padded, refused=True)  # fmt: skip

    # Decisive controls on further Candidates: inherited admission records a Partial with no brief, Task or
    # registered return, the producer's and the owner's Partial review requests, and the owner's review.
    context = coordinator._assay_context()
    requested_by = {}
    for number, (requester, human) in enumerate(((PRODUCER, False), (OWNER, True))):
        other = _ingest_direct(bound, number)
        other_assay = f"asy_019fed25-b33e-7740-b280-{810 + number:012d}"
        other_review = f"rev_019fed25-b33e-7740-b280-{820 + number:012d}"
        projection = _replay(coordinator)
        bar = projection["assay_bar_authority"]
        request = {
            "row_id": "OR-003",
            "candidate_id": other,
            "assay_id": other_assay,
            "candidate_revision": 1,
            "candidate_sha256": projection["candidates"][other]["content_sha256"],
            "assay_bar_acceptance_sha256": bar["acceptance_sha256"],
            "producer_relation_sha256": bar["producer_relation_sha256"],
        }
        assert _direct(bound, "RequestAssay", other_assay, request, STEWARD) == "accepted"
        projection = _replay(coordinator)
        subjects = {"candidate_id": other, "assay_id": other_assay}
        partial = spec_assay._partial_artifact(subjects, projection, projection["candidates"][other],
                                               projection["assays"][other_assay], PARTIAL_EVIDENCE, context)  # fmt: skip
        digest = sha256_hex(canonical_bytes(partial))
        recorded = {**subjects, "row_id": "OR-005", "partial_sha256": digest, "partial_artifact": partial,
                    "producer_relation_sha256": bar["producer_relation_sha256"]}  # fmt: skip
        assert _direct(bound, "RecordAssayPartial", other_assay, recorded, PRODUCER) == "accepted"
        request = _partial_request(other, other_assay, other_review, digest)
        assert _direct(bound, "RequestDiscoveryOutcomeReview", other_review, request, requester, human=human) == (
            "accepted"
        )
        requested_by[requester] = (other, other_assay, other_review, digest)
    other, other_assay, other_review, digest = requested_by[PRODUCER]
    verdict = {
        "review_id": other_review,
        "verdict": "approve",
        "findings": [],
        "required_evidence_refs": ["assay-partial:exact"],
        "limitations": [],
        "conditions": [],
        "reviewer_actor_id": OWNER,
        **{
            key: OUTCOME_VERDICT_EVIDENCE[key]
            for key in (
                "reviewer_profile",
                "reviewer_session",
                "reviewer_model_metadata",
                "context_manifest_id",
                "context_manifest_sha256",
                "trace_visibility_evidence_refs",
            )
        },
        "unchanged_subject_sha256": digest,
        "producing_attempt_id": "att_019fed25-b33e-7740-b280-000000000813",
        "computed_independence_grade": "independent",
    }
    recorded = {"candidate_id": other, "assay_id": other_assay, "row_id": "OR-007", "review_id": other_review,
                "subject_sha256": digest, "verdict": "approve", "review_verdict": verdict}  # fmt: skip
    assert _direct(bound, "ReviewDiscoveryOutcome", other_review, recorded, OWNER, human=True) == "accepted"
    assert _replay(coordinator)["assays"][other_assay]["status"] == "partial_reviewed"
