"""06s Phase 4a-1 (P-058): public W11 bootstrap and the SPEC-01 Assay request on the SPEC route."""

import json
import re

import pytest

from research_system import cli
from research_system.canonical import canonical_bytes
from research_system.discovery import spec_assay
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.discovery.runtime import replay_discovery
from research_system.discovery.spec import ACTION_EFFECTS
from research_system.discovery.spec_source import source_ids
from research_system.errors import ConflictError, SchemaError
from research_system.ids import new_id
from research_system.canonical import sha256_hex
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import ACTORS, PROJECT_ID, REPO_ROOT, activate_lifecycle_grant
from tests.research_system.integration.test_spec_source import (  # noqa: F401
    bind_scratch_route,
    invoke_cli,
    source_intent,
    source_repo,
)
from tests.research_system.integration.test_spec_task import _tail

OWNER = ACTORS["actor-a"]
OTHER_HUMAN = ACTORS["actor-b"]


def _actor(number: int) -> str:
    return f"act_019fed25-b33e-7740-b280-{number:012d}"


# Both committed Assay authority files pin this author, and admission requires it as the submitter (P-058).
PINNED_AUTHOR = _actor(205)
RUBRIC_OBSERVER, SCOPE_OBSERVER, BAR_REQUESTER, BAR_REVIEWER, BAR_PROPOSER = (_actor(n) for n in range(401, 406))
STEWARD, PRODUCER = _actor(411), _actor(412)
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
}

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
    subject = payload["candidate_id"] if command_type == "RequestAssay" else target
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


def test_assay_intent_is_a_closed_record():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    candidate = "obj_019fed25-b33e-7740-b280-000000000501"
    for intent in (GENESIS_INTENT, BAR_INTENT, request_intent(candidate)):
        schemas.validate(spec_assay.INTENT_SCHEMA_ID, intent)
    for invalid in (
        {**GENESIS_INTENT, "unrecognised": True},
        {**GENESIS_INTENT, "candidate_id": candidate},
        {key: value for key, value in BAR_INTENT.items() if key != "producer_actor_id"},
        {**BAR_INTENT, "candidate_id": candidate},
        {"action": spec_assay.REQUEST, "reason": "no candidate"},
        {**request_intent(candidate), "reviewer_actor_id": BAR_REVIEWER},
    ):
        with pytest.raises(SchemaError):
            schemas.validate(spec_assay.INTENT_SCHEMA_ID, invalid)


def test_route_identities_are_deterministic_uuidv7_and_subject_bound():
    first = request_intent("obj_019fed25-b33e-7740-b280-000000000501")
    other = request_intent("obj_019fed25-b33e-7740-b280-000000000502")
    assay_id = spec_assay.subject_ids(PROJECT_ID, first)["assay_id"]
    assert re.fullmatch(f"asy_{UUIDV7}", assay_id)
    assert spec_assay.subject_ids(PROJECT_ID, {**first, "reason": "free text is not identity"})["assay_id"] == assay_id
    assert spec_assay.subject_ids(PROJECT_ID, other)["assay_id"] != assay_id
    bar = spec_assay.subject_ids(PROJECT_ID, BAR_INTENT)
    assert re.fullmatch(f"rev_{UUIDV7}", bar["review_id"]) and re.fullmatch(f"dec_{UUIDV7}", bar["decision_id"])


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
