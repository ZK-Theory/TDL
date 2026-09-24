"""06s Phase 4b-2a (P-058): the SPEC-02 live-run approval, operator brief and Spike start on the public route.

The Spike sequence follows a Candidate the owner promoted at the `assay_to_spike` gate. `approve_spec_02`
registers the owner's separate live-run approval, which changes no Candidate state; `prepare_spec_02`
registers the operator brief; `start_spec_02` runs W11 OR-014, OR-015, OR-016 and OR-017 in route order.
"""

from datetime import UTC, datetime, timedelta
from functools import partial
import json
import re

from jsonschema import Draft202012Validator
import pytest

from research_system import cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import spec_assay
from research_system.discovery.accepted_w11 import CATALOGUE_STREAM_ID
from research_system.discovery.rules import _aggregate_content_hash, _record_ref, _review_ref
from research_system.discovery.spec import ACTION_EFFECTS, SpecCoordinator
from research_system.errors import SchemaError
from research_system.ids import new_id
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import PROJECT_ID, REPO_ROOT
from tests.research_system.integration import test_spec_task as tst
from tests.research_system.integration import test_wp6_1_c1_readiness_lease as c1
from tests.research_system.integration.test_spec_assay import (
    BAR_INTENT,
    GENESIS_INTENT,
    OTHER_HUMAN,
    OUTCOME_REVIEWER,
    OUTCOME_VERDICT_EVIDENCE,
    OWNER,
    PRODUCER,
    PROPOSER,
    RETURN_EVIDENCE,
    SPEC_01_FILES,
    STEWARD,
    _advance,
    _bar_steps,
    _built_direct,
    _direct,
    _grant,
    _ingest_direct,
    _invoke,
    _manifest_of,
    _replay,
    _requested,
    _run,
    _seed_task_naming,
    spec_01_intent,
)
from tests.research_system.integration.test_spec_source import bind_scratch_route, source_repo  # noqa: F401
from tests.research_system.integration.test_spec_result import EVIDENCE_IDS
from tests.research_system.integration.test_spec_task import _OUTCOME_COMMANDS, _outcome_payload, _streams, _tail
from tests.research_system.integration.test_wp6_1_c2_operating_lifecycle import _artefact_manifest

UUIDV7 = r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
CANDIDATE = "obj_019fed25-b33e-7740-b280-000000000501"
SPEC_02_ACTIONS = (
    "approve_spec_02",
    "prepare_spec_02",
    "start_spec_02",
    "return_spec_02_complete",
    "return_spec_02_partial",
    "review_spec_02_complete",
    "review_spec_02_partial",
)


def spec_02_intent(action: str, candidate_id: str = CANDIDATE, **extra) -> dict:
    return {"action": action, "reason": f"advance {action} on the public route", "candidate_id": candidate_id, **extra}


def test_the_action_table_adds_the_spec_02_approval_brief_and_start():
    assert ACTION_EFFECTS[spec_assay.APPROVE_02] == ("RegisterArtefact",)
    assert ACTION_EFFECTS[spec_assay.PREPARE_02] == ("RegisterArtefact",)
    # One action runs the four W11 Spike rows in route order: the plan, its execution proposal, the
    # owner's approval of that proposal, and the start against the running Attempt's live Lease.
    assert ACTION_EFFECTS[spec_assay.START_02] == (
        "RegisterSpikePlan",
        "ProposeSpikeExecutionDecision",
        "ResolveDecision",
        "StartSpike",
    )


def test_spec_02_intents_are_a_closed_record():
    """1.3.0 carries all eight SPEC-02 actions, so no later sub-phase changes a merged schema."""
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    assert spec_assay.INTENT_SCHEMA_VERSION == "1.3.0"
    decide = spec_02_intent("decide_spec_02", recommendation="PROMOTE")
    valid = (*(spec_02_intent(action) for action in SPEC_02_ACTIONS), decide)
    for intent in valid:
        schemas.validate(spec_assay.INTENT_SCHEMA_ID, intent, schema_version=spec_assay.INTENT_SCHEMA_VERSION)
    for invalid in (
        *({"action": action, "reason": "no candidate"} for action in (*SPEC_02_ACTIONS, "decide_spec_02")),
        # A Spike follows its Candidate's promoted Assay, so no SPEC-02 action carries an ordinal.
        *({**intent, "assay_ordinal": 2} for intent in valid),
        *({**spec_02_intent(action), "recommendation": "PARK"} for action in SPEC_02_ACTIONS),
        spec_02_intent("decide_spec_02"),
        {**decide, "schema_version": spec_assay.INTENT_SCHEMA_VERSION},
    ):
        with pytest.raises(SchemaError):
            schemas.validate(spec_assay.INTENT_SCHEMA_ID, invalid, schema_version=spec_assay.INTENT_SCHEMA_VERSION)


def test_spec_02_route_identities_are_deterministic_and_subject_bound():
    approve = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.APPROVE_02))
    prepare = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.PREPARE_02))
    start = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.START_02))
    assert re.fullmatch(f"art_{UUIDV7}", approve["approval_id"])
    assert re.fullmatch(f"art_{UUIDV7}", prepare["spec_02_brief_id"])
    assert re.fullmatch(f"spk_{UUIDV7}", start["spike_id"])
    assert re.fullmatch(f"dec_{UUIDV7}", start["execution_decision_id"])
    # Every SPEC-02 action names the same subjects, and free text is not identity.
    assert approve == prepare == start
    assert spec_assay.subject_ids(PROJECT_ID, {**spec_02_intent(spec_assay.START_02), "reason": "other"}) == start
    other = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.START_02, "obj_019fed25-b33e-7740-b280-000000000502"))  # fmt: skip
    assert other["spike_id"] != start["spike_id"]
    # A Spike follows its Candidate's promoted Assay, which the route reads from the ledger rather than
    # derives, so no SPEC-02 identity is a SPEC-01 one and the SPEC-01 identities are unchanged.
    spec_01 = spec_assay.subject_ids(PROJECT_ID, {"action": spec_assay.PREPARE, "reason": "x", "candidate_id": CANDIDATE})  # fmt: skip
    assert set(start) == {"candidate_id", "approval_id", "spec_02_brief_id", "spike_id", "execution_decision_id"}
    assert not (set(start.values()) & set(spec_01.values())) - {CANDIDATE}


def test_the_spec_02_records_are_closed():
    """The approval and the operator brief are their own closed records, each naming its own action."""
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    for schema_id, action, version in (
        (spec_assay.APPROVAL_SCHEMA_ID, spec_assay.APPROVE_02, "1.0.0"),
        (spec_assay.SPEC_02_BRIEF_SCHEMA_ID, spec_assay.PREPARE_02, "1.0.0"),
    ):
        schema = json.loads(schemas.resolve_identity(schema_id, version).raw_bytes)
        assert schema["additionalProperties"] is False
        intent = Draft202012Validator(schema["properties"]["intent"])
        assert intent.is_valid({"action": action, "candidate_id": CANDIDATE})
        for invalid in (
            {"action": action},
            {"action": "prepare_spec_01", "candidate_id": CANDIDATE},
            {"action": action, "candidate_id": CANDIDATE, "assay_ordinal": 2},
        ):
            assert not intent.is_valid(invalid), (schema_id, invalid)
    # The approval binds the exact promoted Assay Decision and a cost ceiling the plan may not exceed.
    approval = json.loads(schemas.resolve_identity(spec_assay.APPROVAL_SCHEMA_ID, "1.0.0").raw_bytes)
    promotion = approval["properties"]["promotion_decision"]["properties"]
    assert promotion["selected_option"]["const"] == "PROMOTE" and promotion["gate"]["const"] == "assay_to_spike"
    ceiling = approval["properties"]["cost_ceiling"]
    assert ceiling["required"] == ["time_limit_seconds", "worker_limit", "network_access"]
    assert approval["properties"]["route_source"]["properties"]["alias"]["const"] == "SPEC-02"


def test_the_spec_02_limits_are_the_pinned_contracts_own():
    """The route's SPEC-02 resource limits are transcribed from the exact contract bytes the package pins.

    A changed SPEC-02 contract fails here until its limits are transcribed again (PR #298 review). The
    units read "12 GB" and "5 GB" as binary megabytes (Stephen's decision, 2026-09-24).
    """
    package = json.loads((REPO_ROOT / spec_assay.ROUTE_PACKAGE_PATH).read_bytes())
    source = next(source for source in package["sources"] if source["alias"] == "SPEC-02")
    raw = (REPO_ROOT / source["locator"]).read_bytes()
    assert sha256_hex(raw) == source["sha256"] == spec_assay._SPEC_02_LIMITS_SHA256
    limits = (
        "limited to four CPU slots, two hours, 12 GB memory, and 5 GB attempt scratch; no GPU or network is assumed"
    )
    assert limits in " ".join(raw.decode("utf-8").split())
    assert spec_assay._SPEC_02_LIMITS == {
        "worker_limit": 4,
        "time_limit_seconds": 2 * 60 * 60,
        "memory_limit_mb": 12 * 1024,
        "storage_limit_mb": 5 * 1024,
        "network_access": False,
    }


# OR-017 requires a Lease that is live at the route's clock. The C1 fixture leases in a 2026-08-01 window,
# the public CLI runs the route on the real clock, and the bound store's clock is 2026-09-10. The SPEC-02
# tests therefore run the public route on the bound store's clock and translate the fixture's whole window
# so that its own "now" is that clock, every offset unchanged (test-only, P-058 2026-09-18).
C1_WINDOW = {
    "GRANTED_AT": "2026-09-09T23:30:00Z",
    "INITIAL_EXPIRY": "2026-09-10T00:30:00Z",
    "GRANT_EXPIRY": "2026-09-10T01:00:00Z",
    "RENEWED_EXPIRY": "2026-09-10T00:45:00Z",
    "OBSERVED_AT": "2026-09-09T23:50:00Z",
    "HEARTBEAT_AT": "2026-09-10T00:00:00Z",
    "NEXT_HEARTBEAT_AT": "2026-09-10T00:01:00Z",
}
C1_NOW = datetime(2026, 9, 10, tzinfo=UTC)
APPROVAL_EVIDENCE = {
    "scope": "A provider-free check that the promoted finding's bounded predicate holds on the fixture.",
    "cost_ceiling": {
        "time_limit_seconds": 600,
        "worker_limit": 2,
        "memory_limit_mb": 1024,
        "storage_limit_mb": 2048,
        "network_access": False,
    },
}
PLAN_EVIDENCE = {
    "question": "Does the bounded provider-free predicate hold?",
    "inputs": ["fixture:exact"],
    "method_or_object": "No-provider validation",
    "baselines": [],
    "null_or_comparator": None,
    "success_predicates": ["closure holds"],
    "failure_predicates": ["closure fails"],
    "kill_conditions": ["identity mismatch"],
    "partial_rules": ["unable to evaluate is partial"],
    "planned_contracts": ["W11:OR-018"],
    "outputs": ["spike verdict"],
    "prohibited_work": ["provider execution"],
    "outcome_to_next_step": {"PASS": "review"},
    "time_resource_box": {
        "time_limit_seconds": 60,
        "worker_limit": 1,
        "memory_limit_mb": 512,
        "storage_limit_mb": 1024,
        "network_access": False,
    },
}


def _bind(tmp_path, monkeypatch):
    """Bind a scratch SPEC store whose public route runs inside the re-dated Lease window."""
    for name, value in C1_WINDOW.items():
        monkeypatch.setattr(c1, name, value)
    monkeypatch.setattr(c1, "C1_NOW", C1_NOW)
    monkeypatch.setattr(tst, "C1_NOW", C1_NOW)
    bound = bind_scratch_route(tmp_path, monkeypatch, extra_repository_files=SPEC_01_FILES, genesis=False)
    assert bound.coordinator.clock() == C1_NOW
    monkeypatch.setattr(cli, "SpecCoordinator", partial(SpecCoordinator, clock=bound.coordinator.clock))
    return bound


def _promoted(bound, tmp_path, capsys, source_repo, monkeypatch):  # noqa: F811
    """Take a Candidate through SPEC-01 on the public route to the owner's PROMOTE at `assay_to_spike`.

    Returns the Candidate and the seeded Task whose running Attempt the SPEC-02 records cite.
    """
    candidate_id = _requested(bound, tmp_path, capsys, source_repo)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_01_intent(spec_assay.PREPARE, candidate_id))
    task = _seed_task_naming(bound, candidate_id, monkeypatch)
    _run(bound, tmp_path, capsys, spec_01_intent(spec_assay.PREPARE, candidate_id), "RegisterArtefact",
         ids["brief_id"], OWNER, human=True)  # fmt: skip
    evidence = {**RETURN_EVIDENCE, "unresolved_findings": []}
    return_intent = spec_01_intent(spec_assay.RETURN, candidate_id)
    _run(bound, tmp_path, capsys, return_intent, "RegisterArtefact", ids["return_id"], OWNER, human=True,
         evidence=evidence)  # fmt: skip
    _run(bound, tmp_path, capsys, return_intent, "RecordAssayScore", candidate_id, PRODUCER, evidence=evidence)
    review_intent = spec_01_intent(spec_assay.REVIEW, candidate_id)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["review_id"], OUTCOME_REVIEWER,
         evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    decide_intent = spec_01_intent(spec_assay.DECIDE, candidate_id, recommendation="PROMOTE")
    _run(bound, tmp_path, capsys, decide_intent, "ProposePromotionDecision", candidate_id, PROPOSER)
    _run(bound, tmp_path, capsys, decide_intent, "ResolveDecision", ids["decision_id"], OWNER, human=True,
         evidence={"selected_option": "PROMOTE", "revisit_triggers": []})  # fmt: skip
    assert _replay(bound.coordinator)["candidates"][candidate_id]["status"] == "spike_planning_authorized"
    return candidate_id, task


def _register_evidence(bound, artefact_id: str, artefact_type: str) -> dict:
    """Register one canonical artefact a Spike verdict cites, outside the route (operator-mediated, P-058)."""
    manifest = _artefact_manifest(artefact_id)
    manifest["artefact_type"] = artefact_type
    grant = _grant(bound, "RegisterArtefact", artefact_id, OWNER, human=True)
    payload = {"new_artefact_id": artefact_id, "manifest": manifest}
    command = c1._c1_command(new_id("command"), "RegisterArtefact", artefact_id, 0, payload,
                             authority_grant_id=grant, actor_id=OWNER)  # fmt: skip
    assert bound.coordinator.service.submit(command).status == "accepted"
    return _record_ref(artefact_id, 1, manifest["content_sha256"])


def _record_pass_verdict(bound, candidate_id: str, spike_id: str) -> None:
    """Record a PASS Spike verdict through inherited admission, as the later SPEC-02 return will (OR-018)."""
    refs = (
        _register_evidence(bound, "art_019fed25-b33e-7740-b280-000000000991", "evaluation_run"),
        _register_evidence(bound, "art_019fed25-b33e-7740-b280-000000000992", "validation_report"),
    )
    projection = _replay(bound.coordinator)
    candidate, spike = projection["candidates"][candidate_id], projection["spikes"][spike_id]
    assay = projection["assays"][candidate["assay_id"]]
    candidate_ref = _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"])
    verdict = {
        "schema_id": "ars://portfolio/spike-verdict",
        "schema_version": "1.0.0",
        "spike_id": spike_id,
        "candidate_ref": candidate_ref,
        "originating_assay_ref": _record_ref(candidate["assay_id"], 1, assay["scorecard_sha256"]),
        "spike_plan_ref": _record_ref(spike_id, 1, spike["plan_sha256"]),
        "attempt_ref": _record_ref(spike["attempt_id"], 1, spike["attempt_sha256"]),
        "verdict": "PASS",
        "success_predicates": [{"predicate": "closure holds", "status": "passed", "evidence_refs": [candidate_ref]}],
        "failure_predicates": [{"predicate": "closure fails", "status": "passed", "evidence_refs": [candidate_ref]}],
        "kill_conditions": [
            {
                "condition": "identity mismatch",
                "status": "not_triggered",
                "evidence_refs": [candidate_ref],
                "consequence": "stop",
            }
        ],
        "artefact_refs": [refs[0]],
        "validation_refs": [refs[1]],
        "completed_scope": "The declared scope completed.",
        "unmet_scope": "None.",
        "limitations": [],
        "mechanical_recommendation": "NONE",
        "prohibited_inferences": ["This verdict does not authorize dispatch."],
    }
    payload = {
        "row_id": "OR-018",
        "candidate_id": candidate_id,
        "spike_id": spike_id,
        "verdict": "PASS",
        "verdict_sha256": sha256_hex(canonical_bytes(verdict)),
        "verdict_artifact": verdict,
        "evidence_refs": ["evidence:provider-free"],
    }
    assert _direct(bound, "RecordSpikeVerdict", spike_id, payload, PRODUCER) == "accepted"


def _spec_02_states(coordinator, candidate_id: str) -> dict:
    """The listing's state of each SPEC-02 action on a Candidate, re-derived from the ledger alone."""
    return {
        entry["action"]: entry.get("state")
        for entry in coordinator.status()["actions"]
        if entry.get("candidate_id") == candidate_id and entry["action"] in SPEC_02_ACTIONS
    }


def test_public_spec_02_path_starts_the_approved_spike(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = _bind(tmp_path, monkeypatch)
    coordinator = bound.coordinator
    candidate_id, task = _promoted(bound, tmp_path, capsys, source_repo, monkeypatch)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.APPROVE_02, candidate_id))
    promoted = _replay(coordinator)["candidates"][candidate_id]

    approve_intent = spec_02_intent(spec_assay.APPROVE_02, candidate_id)
    approve_grant = _grant(bound, "RegisterArtefact", ids["approval_id"], OWNER, human=True)
    approved = _invoke(bound, tmp_path, capsys, approve_intent, approve_grant, OWNER, evidence=APPROVAL_EVIDENCE)
    assert approved["state"] == "completed"
    # A lost response is answered from the committed receipt; nothing is appended.
    tail = _tail(coordinator)
    retried = _invoke(bound, tmp_path, capsys, approve_intent, approve_grant, OWNER, evidence=APPROVAL_EVIDENCE)
    assert retried["receipt"] == approved["receipt"] and _tail(coordinator) == tail
    # A revised scope or ceiling is not a retry: the completed approval conflicts (PR #298 review).
    for revised in (
        {**APPROVAL_EVIDENCE, "scope": "A revised scope."},
        {**APPROVAL_EVIDENCE, "cost_ceiling": {**APPROVAL_EVIDENCE["cost_ceiling"], "worker_limit": 1}},
    ):
        assert "already completed" in _invoke(bound, tmp_path, capsys, approve_intent, approve_grant, OWNER,
                                              evidence=revised, refused=True)  # fmt: skip
    approval = coordinator.objects.read(spec_assay.APPROVAL_KIND, ids["approval_id"], 1)
    package = json.loads((REPO_ROOT / spec_assay.ROUTE_PACKAGE_PATH).read_bytes())
    spec_02 = next(source for source in package["sources"] if source["alias"] == "SPEC-02")
    assert approval["route_source"]["sha256"] == spec_02["sha256"]
    assert approval["producer_actor_id"] == OWNER
    assert approval["candidate"]["content_sha256"] == promoted["content_sha256"]
    assert approval["assay"]["assay_id"] == promoted["assay_id"]
    assert approval["promotion_decision"]["decision_id"] == promoted["decision_id"]
    assert {key: approval[key] for key in APPROVAL_EVIDENCE} == APPROVAL_EVIDENCE
    # The approval is a record only: the Candidate's state is unchanged.
    assert _replay(coordinator)["candidates"][candidate_id] == promoted

    prepared = _run(bound, tmp_path, capsys, spec_02_intent(spec_assay.PREPARE_02, candidate_id), "RegisterArtefact",
                    ids["spec_02_brief_id"], OWNER, human=True)  # fmt: skip
    assert prepared["state"] == "completed"
    brief = coordinator.objects.read(spec_assay.SPEC_02_BRIEF_KIND, ids["spec_02_brief_id"], 1)
    assert brief["approval"] == {
        "artefact_id": ids["approval_id"],
        "content_sha256": _manifest_of(coordinator, ids["approval_id"])["content_sha256"],
        **APPROVAL_EVIDENCE,
    }
    assert brief["task"] == approval["task"] and brief["brief_source"]["sha256"] == spec_02["sha256"]
    # The brief depends on the owner's approval, not on a SPEC-01 operator brief.
    assert _manifest_of(coordinator, ids["spec_02_brief_id"])["input_dependencies"] == [
        {
            "input_artefact_id": ids["approval_id"],
            "input_content_sha256": brief["approval"]["content_sha256"],
            "dependency_role": "spec_02_live_run_approval",
        }
    ]
    assert _replay(coordinator)["candidates"][candidate_id] == promoted

    # One action runs the four Spike rows: the steward plans and proposes, the owner approves and starts.
    start_intent = spec_02_intent(spec_assay.START_02, candidate_id)
    planned = _run(bound, tmp_path, capsys, start_intent, "RegisterSpikePlan", candidate_id, STEWARD,
                   evidence=PLAN_EVIDENCE)  # fmt: skip
    assert planned["state"] == "prepared" and planned["next_effect"] == "ProposeSpikeExecutionDecision"
    proposed = _run(bound, tmp_path, capsys, start_intent, "ProposeSpikeExecutionDecision", candidate_id, STEWARD)
    assert proposed["next_effect"] == "ResolveDecision"
    resolved = _run(bound, tmp_path, capsys, start_intent, "ResolveDecision", ids["execution_decision_id"], OWNER,
                    human=True)  # fmt: skip
    assert resolved["next_effect"] == "StartSpike"
    started = _run(bound, tmp_path, capsys, start_intent, "StartSpike", candidate_id, OWNER, human=True)
    assert started["state"] == "completed"

    projection = _replay(coordinator)
    assert projection["candidates"][candidate_id]["status"] == "spike_running"
    assert projection["spikes"][ids["spike_id"]]["status"] == "running"
    events = coordinator.ledger.snapshot().events
    plan = next(
        event["payload"]["plan_artifact"]
        for event in events
        if event["stream_id"] == ids["spike_id"] and event["event_type"] == "SpikePlanned"
    )
    proposal = next(
        event["payload"]
        for event in events
        if event["stream_id"] == ids["execution_decision_id"] and event["event_type"] == "DecisionProposed"
    )
    # The execution proposal cites the owner's approval as its governing evidence.
    assert proposal["governing_evidence_refs"] == [f"approval:{ids['approval_id']}"]
    # The plan runs the scope the owner approved, under the owner's authority, from the promoted Assay.
    assert plan["scope"] == APPROVAL_EVIDENCE["scope"] and plan["required_approving_authority"] == OWNER
    assert {key: plan[key] for key in PLAN_EVIDENCE} == PLAN_EVIDENCE
    assert plan["assay_promotion_decision_ref"]["id"] == promoted["decision_id"]
    assert plan["originating_assay_ref"]["id"] == promoted["assay_id"]
    assert _streams(coordinator)[c1.ATTEMPT_ID]["status"] == "running"

    # The listing re-derives every state from the ledger alone.
    completed = dict.fromkeys((spec_assay.APPROVE_02, spec_assay.PREPARE_02, spec_assay.START_02), "completed")
    assert _spec_02_states(coordinator, candidate_id) == completed

    # The start stays completed when a later Spike row lands on the Spike stream, and when the Attempt it
    # started ends: it is verified against the ledger prefix it was issued at (PR #298 review). Re-deriving
    # a recorded row consults no clock either, so these readings hold although the Lease the start bound
    # has expired by the moment they are taken.
    _record_pass_verdict(bound, candidate_id, ids["spike_id"])
    assert _replay(coordinator)["spikes"][ids["spike_id"]]["status"] == "verdict_recorded"
    assert _spec_02_states(coordinator, candidate_id) == completed
    outcome = c1._c1_command(
        c1._command_id(9001),
        _OUTCOME_COMMANDS["completed"],
        c1.ATTEMPT_ID,
        coordinator.ledger.snapshot().stream_versions[c1.ATTEMPT_ID],
        _outcome_payload("completed", EVIDENCE_IDS),
    )
    assert task.seeding.submit(outcome).status == "accepted"
    assert _streams(coordinator)[c1.ATTEMPT_ID]["status"] != "running"
    assert _spec_02_states(coordinator, candidate_id) == completed


def test_spec_02_route_binds_the_approval_and_the_spike_plan(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = _bind(tmp_path, monkeypatch)
    candidate_id, _ = _promoted(bound, tmp_path, capsys, source_repo, monkeypatch)
    ids = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.APPROVE_02, candidate_id))
    approve_intent = spec_02_intent(spec_assay.APPROVE_02, candidate_id)
    prepare_intent = spec_02_intent(spec_assay.PREPARE_02, candidate_id)
    start_intent = spec_02_intent(spec_assay.START_02, candidate_id)

    # A Candidate this route did not promote is not a SPEC-02 subject.
    other = _ingest_direct(bound, 11)
    other_ids = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.APPROVE_02, other))
    grant = _grant(bound, "RegisterArtefact", other_ids["approval_id"], OWNER, human=True)
    assert "promoted at the assay_to_spike gate" in _invoke(bound, tmp_path, capsys, spec_02_intent(
        spec_assay.APPROVE_02, other), grant, OWNER, evidence=APPROVAL_EVIDENCE, refused=True)  # fmt: skip

    # The brief does not precede the owner's approval.
    brief_grant = _grant(bound, "RegisterArtefact", ids["spec_02_brief_id"], OWNER, human=True)
    assert "approve_spec_02 to be completed first" in _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant,
                                                              OWNER, refused=True)  # fmt: skip

    # The approval is the owner's alone and carries exactly the scope and a well-formed ceiling.
    other_human = _grant(bound, "RegisterArtefact", ids["approval_id"], OTHER_HUMAN, human=True)
    assert "authority owner" in _invoke(bound, tmp_path, capsys, approve_intent, other_human, OTHER_HUMAN,
                                        evidence=APPROVAL_EVIDENCE, refused=True)  # fmt: skip
    approve_grant = _grant(bound, "RegisterArtefact", ids["approval_id"], OWNER, human=True)
    # The ceiling stays inside the SPEC-02 contract's own limits: every limit, and no network (PR #298 review).
    ceiling = APPROVAL_EVIDENCE["cost_ceiling"]
    beyond_contract = (
        {**ceiling, "worker_limit": 5},
        {**ceiling, "time_limit_seconds": 7201},
        {**ceiling, "memory_limit_mb": 12 * 1024 + 1},
        {key: value for key, value in ceiling.items() if key != "storage_limit_mb"},
        {**ceiling, "network_access": True},
    )
    for evidence, reason in (
        ({"scope": APPROVAL_EVIDENCE["scope"]}, "evidence fields are not exact"),
        ({**APPROVAL_EVIDENCE, "cost_ceiling": {"time_limit_seconds": 600}}, "not schema-valid"),
        *(
            ({**APPROVAL_EVIDENCE, "cost_ceiling": over}, "SPEC-02 contract's resource limits")
            for over in beyond_contract
        ),
    ):
        assert reason in _invoke(bound, tmp_path, capsys, approve_intent, approve_grant, OWNER, evidence=evidence,
                                 refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, approve_intent, approve_grant, OWNER, evidence=APPROVAL_EVIDENCE)
    # Nor does the start precede the brief, even once the approval is registered.
    plan_grant = _grant(bound, "RegisterSpikePlan", candidate_id, STEWARD)
    assert "prepare_spec_02 to be completed first" in _invoke(bound, tmp_path, capsys, start_intent, plan_grant,
                                                              STEWARD, evidence=PLAN_EVIDENCE, refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, prepare_intent, brief_grant, OWNER)

    # Neither the prospective producer nor the owner plans the Spike.
    for actor, human in ((PRODUCER, False), (OWNER, True)):
        grant = _grant(bound, "RegisterSpikePlan", candidate_id, actor, human=human)
        assert "neither the prospective producer nor the owner" in _invoke(
            bound, tmp_path, capsys, start_intent, grant, actor, evidence=PLAN_EVIDENCE, refused=True)  # fmt: skip
    # The plan stays inside the owner's ceiling: every limit it sets, and no network it does not permit.
    box = PLAN_EVIDENCE["time_resource_box"]
    for over in (
        {**box, "worker_limit": 3},
        {**box, "memory_limit_mb": 2048},
        {key: value for key, value in box.items() if key != "memory_limit_mb"},
        {**box, "network_access": True},
    ):
        assert "cost ceiling" in _invoke(bound, tmp_path, capsys, start_intent, plan_grant, STEWARD,
                                         evidence={**PLAN_EVIDENCE, "time_resource_box": over}, refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, start_intent, plan_grant, STEWARD, evidence=PLAN_EVIDENCE)
    # A Lease the replay still marks active is not live once it has expired. The execution rows are
    # refused at the submission time they would be recorded at, so the route never records an authority
    # OR-017 could not start and renewal could not rescue (PR #298 review).
    propose_grant = _grant(bound, "ProposeSpikeExecutionDecision", candidate_id, STEWARD)
    with monkeypatch.context() as expired:
        expired.setattr(cli, "SpecCoordinator", partial(SpecCoordinator, clock=lambda: C1_NOW + timedelta(minutes=50)))
        assert "Lease that has not expired" in _invoke(bound, tmp_path, capsys, start_intent, propose_grant, STEWARD,
                                                       refused=True)  # fmt: skip
    # Nor does either propose its execution.
    for actor, human in ((PRODUCER, False), (OWNER, True)):
        grant = _grant(bound, "ProposeSpikeExecutionDecision", candidate_id, actor, human=human)
        assert "neither the prospective producer nor the owner" in _invoke(bound, tmp_path, capsys, start_intent,
                                                                           grant, actor, refused=True)  # fmt: skip
    proposed = _run(bound, tmp_path, capsys, start_intent, "ProposeSpikeExecutionDecision", candidate_id, STEWARD)
    assert proposed["next_effect"] == "ResolveDecision"


def _direct_promoted(bound, number: int) -> tuple[str, str]:
    """Promote a Candidate at `assay_to_spike` through inherited admission alone (decisive controls only)."""
    coordinator = bound.coordinator
    candidate_id = _ingest_direct(bound, number)
    assay_id = f"asy_019fed25-b33e-7740-b280-{970 + number:012d}"
    review_id = f"rev_019fed25-b33e-7740-b280-{973 + number:012d}"
    decision_id = f"dec_019fed25-b33e-7740-b280-{976 + number:012d}"
    pair = {"candidate_id": candidate_id, "assay_id": assay_id}
    projection = _replay(coordinator)
    bar = projection["assay_bar_authority"]
    request = {
        **pair,
        "row_id": "OR-003",
        "candidate_revision": 1,
        "candidate_sha256": projection["candidates"][candidate_id]["content_sha256"],
        "assay_bar_acceptance_sha256": bar["acceptance_sha256"],
        "producer_relation_sha256": bar["producer_relation_sha256"],
    }
    assert _direct(bound, "RequestAssay", assay_id, request, STEWARD) == "accepted"
    projection = _replay(coordinator)
    scorecard = spec_assay._scorecard(pair, projection, projection["candidates"][candidate_id],
                                      projection["assays"][assay_id], RETURN_EVIDENCE,
                                      coordinator._assay_context())  # fmt: skip
    digest = sha256_hex(canonical_bytes(scorecard))
    score = {**pair, "row_id": "OR-004", "scorecard_sha256": digest, "scorecard_artifact": scorecard,
             "producer_relation_sha256": bar["producer_relation_sha256"]}  # fmt: skip
    assert _direct(bound, "RecordAssayScore", assay_id, score, PRODUCER) == "accepted"
    contract = {
        "review_type": "provenance",
        "new_review_id": review_id,
        "subject_ids": [assay_id],
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
    requested = {**pair, "row_id": "OR-034", "review_id": review_id, "subject_sha256": digest,
                 "review_contract": contract}  # fmt: skip
    assert _direct(bound, "RequestDiscoveryOutcomeReview", review_id, requested, STEWARD) == "accepted"
    verdict = {
        "review_id": review_id,
        "verdict": "approve",
        "findings": [],
        "required_evidence_refs": ["scorecard:exact"],
        "limitations": [],
        "conditions": [],
        "reviewer_actor_id": OUTCOME_REVIEWER,
        **{key: OUTCOME_VERDICT_EVIDENCE[key] for key in spec_assay._VERDICT_EVIDENCE - {"findings", "limitations"}},
        "unchanged_subject_sha256": digest,
        "producing_attempt_id": "att_019fed25-b33e-7740-b280-000000000979",
        "computed_independence_grade": "independent",
    }
    reviewed = {**pair, "row_id": "OR-006", "review_id": review_id, "subject_sha256": digest, "verdict": "approve",
                "review_verdict": verdict}  # fmt: skip
    assert _direct(bound, "ReviewDiscoveryOutcome", review_id, reviewed, OUTCOME_REVIEWER) == "accepted"
    projection = _replay(coordinator)
    assay, review, candidate = (projection["assays"][assay_id], projection["reviews"][review_id],
                                projection["candidates"][candidate_id])  # fmt: skip
    aggregate = _record_ref(assay_id, assay["version"], _aggregate_content_hash(assay))
    proposal = {
        "row_id": "OR-012",
        "candidate_id": candidate_id,
        "decision_id": decision_id,
        "review_id": review_id,
        "w2_payload": {
            "question": "assay_to_spike",
            "recommendation": "PROMOTE",
            "new_decision_id": decision_id,
            "decision_revision": 1,
            "decision_kind": "design_lock",
            "options": ["PROMOTE", "PARK", "KILL"],
            "governing_evidence_refs": [f"review:{review_id}"],
            "affected_task_ids": [],
            "affected_claim_ids": [],
            "required_authority": "owner",
            "expires_at": "2026-12-31T00:00:00Z",
            "review_date": "2026-09-11T00:00:00Z",
            "consequences": ["authorize Spike planning"],
        },
        "promotion_relation": {
            "schema_id": "ars://portfolio/relation/discovery-promotion",
            "schema_version": "1.0.0",
            "relation_kind": "discovery_promotion",
            "decision_id": decision_id,
            "candidate_ref": _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
            "gate": "assay_to_spike",
            "aggregate_ref": aggregate,
            "aggregate_relation_hash": assay["producer_relation_sha256"],
            "evidence_ref": aggregate,
            "selected_option": "PROMOTE",
            "next_candidate_state": "spike_planning_authorized",
            "rationale": "Decisive control: promote the scored Assay to Spike planning.",
            "considered_evidence_refs": [_review_ref(review)],
            "conditions": [],
            "effective_scope": f"assay_to_spike:{candidate_id}",
            "revisit_triggers": [],
            "actor_id": PROPOSER,
        },
    }
    assert _direct(bound, "ProposePromotionDecision", decision_id, proposal, PROPOSER) == "accepted"

    def resolution(grant: str) -> dict:
        return {
            "row_id": "OR-013",
            "candidate_id": candidate_id,
            "decision_id": decision_id,
            "w2_payload": {
                "decision_id": decision_id,
                "selected_option": "PROMOTE",
                "effective_scope": "exact Discovery subject",
                "decision_revision": 1,
                "deciding_actor_id": OWNER,
                "decision_authority_grant_id": grant,
                "governing_evidence_refs": [f"review:{review_id}"],
                "considered_review_ids": [review_id],
                "effective_at": "2026-09-11T00:00:00Z",
                "permitted_commands": ["RegisterSpikePlan"],
                "superseded_decision_ids": [],
                "conditions": [],
                "revisit_triggers": [],
            },
        }

    status = _built_direct(bound, "ResolveDecision", decision_id, resolution, OWNER, subject=decision_id, human=True)
    assert status == "accepted"
    assert _replay(coordinator)["candidates"][candidate_id]["status"] == "spike_planning_authorized"
    return candidate_id, assay_id


def test_admission_accepts_the_spike_planning_collapses_the_route_refuses(tmp_path, monkeypatch, capsys):
    bound = _bind(tmp_path, monkeypatch)
    coordinator = bound.coordinator
    _advance(bound, tmp_path, capsys, GENESIS_INTENT, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID,
             OWNER, human=True)  # fmt: skip
    for command_type, subject, actor, human in _bar_steps():
        _advance(bound, tmp_path, capsys, BAR_INTENT, command_type, subject, actor, human)
    promoted = [_direct_promoted(bound, number) for number in (1, 2)]
    # The execution relation binds the resource grant the seeded Lease holds.
    _seed_task_naming(bound, promoted[0][0], monkeypatch)
    # A Candidate promoted outside the route is not a SPEC-02 subject, even with a Task naming it.
    foreign = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.APPROVE_02, promoted[0][0]))
    grant = _grant(bound, "RegisterArtefact", foreign["approval_id"], OWNER, human=True)
    assert "promoted Assay to be this route's own" in _invoke(bound, tmp_path, capsys, spec_02_intent(
        spec_assay.APPROVE_02, promoted[0][0]), grant, OWNER, evidence=APPROVAL_EVIDENCE, refused=True)  # fmt: skip

    # Inherited admission records a Spike plan registered by the prospective producer or the owner.
    spikes = []
    for index, (actor, human) in enumerate(((PRODUCER, False), (OWNER, True))):
        candidate_id, assay_id = promoted[index]
        spike_id = f"spk_019fed25-b33e-7740-b280-{980 + index:012d}"
        projection = _replay(coordinator)
        candidate, assay = projection["candidates"][candidate_id], projection["assays"][assay_id]
        promotion = projection["decisions"][candidate["decision_id"]]
        assay_ref = _record_ref(assay_id, 1, assay["scorecard_sha256"])
        plan = {
            "schema_id": "ars://portfolio/spike-plan",
            "schema_version": "1.0.0",
            "spike_id": spike_id,
            "candidate_ref": _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
            "originating_assay_ref": assay_ref,
            "source_scorecard_refs": [assay_ref],
            "assay_promotion_decision_ref": _record_ref(
                candidate["decision_id"], promotion["proposal_version"], promotion["proposal_event_hash"]
            ),  # fmt: skip
            "required_approving_authority": OWNER,
            "scope": APPROVAL_EVIDENCE["scope"],
            **PLAN_EVIDENCE,
        }
        payload = {"row_id": "OR-014", "candidate_id": candidate_id, "spike_id": spike_id,
                   "plan_sha256": sha256_hex(canonical_bytes(plan)), "plan_artifact": plan}  # fmt: skip
        assert _direct(bound, "RegisterSpikePlan", spike_id, payload, actor, human=human) == "accepted", actor
        spikes.append(spike_id)

    # It also records an execution proposal from the owner or the prospective producer.
    resource = coordinator._operational_state(coordinator.ledger.snapshot().events)[c1.RESOURCE_GRANT_ID]
    for index, (actor, human) in enumerate(((OWNER, True), (PRODUCER, False))):
        candidate_id, assay_id = promoted[index]
        decision_id = f"dec_019fed25-b33e-7740-b280-{985 + index:012d}"
        projection = _replay(coordinator)
        candidate, assay = projection["candidates"][candidate_id], projection["assays"][assay_id]
        plan_ref = _record_ref(spikes[index], 1, projection["spikes"][spikes[index]]["plan_sha256"])
        payload = {
            "row_id": "OR-015",
            "candidate_id": candidate_id,
            "spike_id": spikes[index],
            "decision_id": decision_id,
            "w2_payload": {
                "question": "spike_execution",
                "recommendation": "approve",
                "new_decision_id": decision_id,
                "decision_revision": 1,
                "decision_kind": "design_lock",
                "options": ["approve", "reject"],
                "governing_evidence_refs": ["evidence:exact"],
                "affected_task_ids": [],
                "affected_claim_ids": [],
                "required_authority": "owner",
                "expires_at": "2026-12-31T00:00:00Z",
                "review_date": "2026-09-11T00:00:00Z",
                "consequences": ["authorize the bounded Spike"],
            },
            "execution_authority_relation": {
                "schema_id": "ars://portfolio/relation/spike-execution-authority",
                "schema_version": "1.0.0",
                "relation_kind": "spike_execution_authority",
                "decision_id": decision_id,
                "spike_ref": plan_ref,
                "candidate_ref": _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
                "plan_ref": plan_ref,
                "resource_ref": _record_ref(c1.RESOURCE_GRANT_ID, 1, sha256_hex(canonical_bytes(resource))),
                "route_ref": plan_ref,
                "assurance_ref": _record_ref(assay_id, 1, assay["scorecard_sha256"]),
                "selected_option": "AUTHORIZE",
                "actor_id": OWNER,
            },
        }
        status = _direct(bound, "ProposeSpikeExecutionDecision", decision_id, payload, actor, human=human)
        assert status == "accepted", actor
