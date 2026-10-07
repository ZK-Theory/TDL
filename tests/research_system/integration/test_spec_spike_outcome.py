"""06s Phase 4b-2b (P-058): the SPEC-02 Spike return, outcome review and decision on the public route.

`return_spec_02_complete` and `return_spec_02_partial` register one closed operator return, then W11 OR-018 or
OR-019; `review_spec_02_complete` and `review_spec_02_partial` run OR-036 then OR-020, or OR-037 then OR-021; and
`decide_spec_02` runs OR-026 then OR-027 at the `spike_to_preregistration` gate. The complete path ends at an
accepted project-use result that records the Spike. A Partial Spike is terminal on the route.
"""

from datetime import timedelta
from functools import partial
import json
import re

from jsonschema import Draft202012Validator
import pytest

from research_system import cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import spec_assay, spec_result, spec_task
from research_system.discovery.accepted_w11 import CATALOGUE_STREAM_ID
from research_system.discovery.rules import _aggregate_content_hash, _record_ref, _review_ref
from research_system.discovery.spec import ACTION_EFFECTS, SpecCoordinator
from research_system.errors import SchemaError
from research_system.ids import new_id
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import PROJECT_ID, REPO_ROOT, activate_lifecycle_grant
from tests.research_system.integration import test_spec_result as result_route
from tests.research_system.integration import test_wp6_1_c1_readiness_lease as c1
from tests.research_system.integration.test_spec_assay import (
    BAR_INTENT,
    GENESIS_INTENT,
    OUTCOME_REVIEWER,
    OUTCOME_VERDICT_EVIDENCE,
    OWNER,
    PRODUCER,
    PROPOSER,
    STEWARD,
    _advance,
    _advance_task,
    _bar_steps,
    _built_direct,
    _direct,
    _grant,
    _invoke,
    _manifest_of,
    _replay,
    _run,
    _seed_task_naming,
)
from tests.research_system.integration.test_spec_source import source_repo  # noqa: F401
from tests.research_system.integration.test_spec_spike import (
    APPROVAL_EVIDENCE,
    C1_NOW,
    CANDIDATE,
    PLAN_EVIDENCE,
    UUIDV7,
    _bind,
    _direct_promoted,
    _promoted,
    spec_02_intent,
)
from tests.research_system.integration.test_spec_task import _OUTCOME_COMMANDS, _outcome_payload, _streams, _tail
from tests.research_system.integration.test_wp6_1_c2_operating_lifecycle import _artefact_manifest

OUTCOME_ACTIONS = (
    "return_spec_02_complete",
    "return_spec_02_partial",
    "review_spec_02_complete",
    "review_spec_02_partial",
    "decide_spec_02",
)
# The Spike's own evidence, registered outside the route by the owner (operator-mediated, P-058), and one
# artefact a different Attempt produced.
ARTEFACT = "art_019fed25-b33e-7740-b280-000000000991"
VALIDATION = "art_019fed25-b33e-7740-b280-000000000992"
FOREIGN = "art_019fed25-b33e-7740-b280-000000000993"
OTHER_ATTEMPT = "att_019fed25-b33e-7740-b280-000000000994"
# Identities of the Spike the decisive controls start through inherited admission alone.
SPIKE = "spk_019fed25-b33e-7740-b280-000000000995"
EXECUTION = "dec_019fed25-b33e-7740-b280-000000000996"
REVIEW = "rev_019fed25-b33e-7740-b280-000000000997"
DECISION = "dec_019fed25-b33e-7740-b280-000000000998"
SPIKE_PARK = {"selected_option": "PARK", "revisit_triggers": ["a SPEC-02 fixture the owner approves afresh"]}
LATE = C1_NOW + timedelta(minutes=50)


def _evidence_ref(artefact_id: str) -> dict:
    return _record_ref(artefact_id, 1, _artefact_manifest(artefact_id)["content_sha256"])


def spike_evidence(verdict: str = "PASS", *, artefact: str = ARTEFACT) -> dict:
    """The operator's W11 verdict judgements; the route derives the Spike, Candidate, Assay, plan and Attempt refs."""
    cited = _evidence_ref(artefact)
    evidence = {
        "verdict": verdict,
        "success_predicates": [{"predicate": "closure holds", "status": "passed", "evidence_refs": [cited]}],
        "failure_predicates": [{"predicate": "closure fails", "status": "passed", "evidence_refs": [cited]}],
        "kill_conditions": [
            {
                "condition": "identity mismatch",
                "status": "not_triggered",
                "evidence_refs": [cited],
                "consequence": "stop",
            }
        ],
        "artefact_refs": [cited],
        "validation_refs": [_evidence_ref(VALIDATION)],
        "completed_scope": "The declared scope completed.",
        "unmet_scope": "None.",
        "limitations": [],
        "mechanical_recommendation": "PROMOTE",
        "prohibited_inferences": ["This verdict does not authorize dispatch."],
    }
    if verdict == "PARTIAL":
        evidence["success_predicates"][0]["status"] = "unable_to_evaluate"
        evidence.update(
            unmet_scope="The closure predicate could not be evaluated.",
            limitations=["The closure predicate was not evaluated."],
            mechanical_recommendation="PARK",
        )
    return evidence


def _register(bound, artefact_id: str, artefact_type: str, *, attempt_id: str = c1.ATTEMPT_ID) -> None:
    """Register one canonical artefact a Spike verdict may cite; its manifest names the Attempt that produced it."""
    manifest = {**_artefact_manifest(artefact_id), "artefact_type": artefact_type, "attempt_id": attempt_id}
    grant = _grant(bound, "RegisterArtefact", artefact_id, OWNER, human=True)
    command = c1._c1_command(new_id("command"), "RegisterArtefact", artefact_id, 0,
                             {"new_artefact_id": artefact_id, "manifest": manifest}, authority_grant_id=grant,
                             actor_id=OWNER)  # fmt: skip
    assert bound.coordinator.service.submit(command).status == "accepted"


def _evidence(bound) -> None:
    _register(bound, ARTEFACT, "evaluation_run")
    _register(bound, VALIDATION, "validation_report")


def _states(coordinator, candidate_id: str) -> dict:
    """The listing's state of each SPEC-02 action on a Candidate, re-derived from the ledger alone."""
    spec_02 = (spec_assay.APPROVE_02, spec_assay.PREPARE_02, spec_assay.START_02, *OUTCOME_ACTIONS)
    return {
        entry["action"]: entry.get("state")
        for entry in coordinator.status()["actions"]
        if entry.get("candidate_id") == candidate_id and entry["action"] in spec_02
    }


def _started(bound, tmp_path, capsys, candidate_id: str) -> dict:
    """Approve, prepare and start the Candidate's Spike on the public route; return its identities."""
    ids = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.RETURN_02, candidate_id))
    _run(bound, tmp_path, capsys, spec_02_intent(spec_assay.APPROVE_02, candidate_id), "RegisterArtefact",
         ids["approval_id"], OWNER, human=True, evidence=APPROVAL_EVIDENCE)  # fmt: skip
    _run(bound, tmp_path, capsys, spec_02_intent(spec_assay.PREPARE_02, candidate_id), "RegisterArtefact",
         ids["spec_02_brief_id"], OWNER, human=True)  # fmt: skip
    start = spec_02_intent(spec_assay.START_02, candidate_id)
    _run(bound, tmp_path, capsys, start, "RegisterSpikePlan", candidate_id, STEWARD, evidence=PLAN_EVIDENCE)
    _run(bound, tmp_path, capsys, start, "ProposeSpikeExecutionDecision", candidate_id, STEWARD)
    _run(bound, tmp_path, capsys, start, "ResolveDecision", ids["execution_decision_id"], OWNER, human=True)
    assert _run(bound, tmp_path, capsys, start, "StartSpike", candidate_id, OWNER, human=True)["state"] == "completed"
    return ids


def test_the_action_table_adds_the_spike_return_review_and_decision():
    assert ACTION_EFFECTS[spec_assay.RETURN_02] == ("RegisterArtefact", "RecordSpikeVerdict")
    assert ACTION_EFFECTS[spec_assay.RETURN_02_PARTIAL] == ("RegisterArtefact", "RecordSpikeVerdict")
    assert ACTION_EFFECTS[spec_assay.REVIEW_02] == ("RequestDiscoveryOutcomeReview", "ReviewDiscoveryOutcome")
    assert ACTION_EFFECTS[spec_assay.REVIEW_02_PARTIAL] == ("RequestDiscoveryOutcomeReview", "ReviewDiscoveryOutcome")
    assert ACTION_EFFECTS[spec_assay.DECIDE_02] == ("ProposePromotionDecision", "ResolveDecision")
    # Every SPEC-02 action the closed intent record names is now a route action (PR #298 known limit 9).
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    intent = json.loads(schemas.resolve_identity(spec_assay.INTENT_SCHEMA_ID, "1.3.0").raw_bytes)
    named = {action for action in intent["properties"]["action"]["enum"] if "_spec_02" in action}
    assert len(named) == 8 and named <= set(spec_assay.ACTIONS)


def test_the_outcome_alternatives_share_their_identities():
    ids = {action: spec_assay.subject_ids(PROJECT_ID, spec_02_intent(action)) for action in OUTCOME_ACTIONS}
    start = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.START_02))
    # Every SPEC-02 action names the same subjects, so the complete and Partial alternatives share one return and
    # one outcome review, and the alternative not taken conflicts (P-058, 2026-09-25).
    assert all(subjects == start for subjects in ids.values())
    assert re.fullmatch(f"art_{UUIDV7}", start["spec_02_return_id"])
    assert re.fullmatch(f"rev_{UUIDV7}", start["spike_review_id"])
    assert re.fullmatch(f"dec_{UUIDV7}", start["spike_decision_id"])
    assert len(set(start.values())) == len(start)
    other = spec_assay.subject_ids(PROJECT_ID, spec_02_intent(spec_assay.RETURN_02, CANDIDATE[:-1] + "2"))
    assert other["spec_02_return_id"] != start["spec_02_return_id"]


def test_the_spike_return_is_one_closed_record_for_both_outcomes():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    schema = json.loads(schemas.resolve_identity(spec_assay.SPEC_02_RETURN_SCHEMA_ID, "1.0.0").raw_bytes)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["operator_return"]["additionalProperties"] is False
    assert set(schema["properties"]["operator_return"]["required"]) == set(spec_assay._SPIKE_JUDGEMENTS)
    assert schema["properties"]["verdict_artifact"] == {"$ref": "ars://portfolio/spike-verdict"}
    intent = Draft202012Validator(schema["properties"]["intent"])
    for action in (spec_assay.RETURN_02, spec_assay.RETURN_02_PARTIAL):
        assert intent.is_valid({"action": action, "candidate_id": CANDIDATE})
    for invalid in (
        {"action": spec_assay.RETURN_02},
        {"action": spec_assay.RETURN, "candidate_id": CANDIDATE},
        {"action": spec_assay.RETURN_02, "candidate_id": CANDIDATE, "assay_ordinal": 2},
    ):
        assert not intent.is_valid(invalid), invalid


@pytest.mark.slow
def test_public_spec_02_path_reaches_accepted_project_use(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = _bind(tmp_path, monkeypatch)
    coordinator = bound.coordinator
    candidate_id, task = _promoted(bound, tmp_path, capsys, source_repo, monkeypatch)
    ids = _started(bound, tmp_path, capsys, candidate_id)
    _evidence(bound)
    evidence = spike_evidence()

    return_intent = spec_02_intent(spec_assay.RETURN_02, candidate_id)
    return_grant = _grant(bound, "RegisterArtefact", ids["spec_02_return_id"], OWNER, human=True)
    registered = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=evidence)
    assert registered["state"] == "prepared" and registered["next_effect"] == "RecordSpikeVerdict"
    # A lost response is answered from the committed receipt; nothing is appended.
    tail = _tail(coordinator)
    retried = _invoke(bound, tmp_path, capsys, return_intent, return_grant, OWNER, evidence=evidence)
    assert retried["receipt"] == registered["receipt"] and _tail(coordinator) == tail
    recorded = _run(bound, tmp_path, capsys, return_intent, "RecordSpikeVerdict", candidate_id, PRODUCER,
                    evidence=evidence)  # fmt: skip
    assert recorded["state"] == "completed"

    returned = coordinator.objects.read(spec_assay.SPEC_02_RETURN_KIND, ids["spec_02_return_id"], 1)
    brief = coordinator.objects.read(spec_assay.SPEC_02_BRIEF_KIND, ids["spec_02_brief_id"], 1)
    spike = _replay(coordinator)["spikes"][ids["spike_id"]]
    assert returned["operator_return"] == evidence and returned["task"] == brief["task"]
    assert returned["brief"]["artefact_id"] == ids["spec_02_brief_id"] and returned["producer_actor_id"] == OWNER
    assert spike["status"] == "verdict_recorded" and spike["verdict_sha256"] == returned["verdict_sha256"]
    assert spike["producer_actor_id"] == PRODUCER
    # The route derives every reference in the verdict; the operator's judgements are carried verbatim.
    verdict = returned["verdict_artifact"]
    assert {key: verdict[key] for key in evidence} == evidence
    assert verdict["attempt_ref"]["id"] == c1.ATTEMPT_ID and verdict["spike_plan_ref"]["id"] == ids["spike_id"]
    assert verdict["spike_plan_ref"]["content_hash"] == spike["plan_sha256"]
    assert _manifest_of(coordinator, ids["spec_02_return_id"])["input_dependencies"] == [
        {
            "input_artefact_id": ids["spec_02_brief_id"],
            "input_content_sha256": _manifest_of(coordinator, ids["spec_02_brief_id"])["content_sha256"],
            "dependency_role": "operator_brief",
        }
    ]
    # The record is closed and binds its verdict to the action it records.
    for invalid in (
        {**returned, "unrecognised": True},
        {**returned, "operator_return": {**evidence, "verdict": "PARTIAL"}},
        {**returned, "intent": {**returned["intent"], "action": spec_assay.RETURN_02_PARTIAL}},
    ):
        with pytest.raises(SchemaError):
            coordinator.schemas.validate(spec_assay.SPEC_02_RETURN_SCHEMA_ID, invalid, schema_version="1.0.0")

    review_intent = spec_02_intent(spec_assay.REVIEW_02, candidate_id)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    reviewed = _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["spike_review_id"],
                    OUTCOME_REVIEWER, evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert reviewed["state"] == "completed"
    projection = _replay(coordinator)
    assert projection["spikes"][ids["spike_id"]]["status"] == "reviewed"
    assert projection["reviews"][ids["spike_review_id"]]["status"] == "satisfied"

    decide_intent = spec_02_intent(spec_assay.DECIDE_02, candidate_id, recommendation="PROMOTE")
    _run(bound, tmp_path, capsys, decide_intent, "ProposePromotionDecision", candidate_id, PROPOSER)
    decided = _run(bound, tmp_path, capsys, decide_intent, "ResolveDecision", ids["spike_decision_id"], OWNER,
                   human=True, evidence={"selected_option": "PROMOTE", "revisit_triggers": []})  # fmt: skip
    assert decided["state"] == "completed"
    candidate = _replay(coordinator)["candidates"][candidate_id]
    assert candidate["status"] == "preregistration_authorized"
    assert candidate["promotion_gate"] == "spike_to_preregistration"

    # The listing re-derives every SPEC-02 state from the ledger alone, with the one return alternative taken.
    taken = (spec_assay.APPROVE_02, spec_assay.PREPARE_02, spec_assay.START_02, spec_assay.RETURN_02,
             spec_assay.REVIEW_02, spec_assay.DECIDE_02)  # fmt: skip
    assert _states(coordinator, candidate_id) == dict.fromkeys(taken, "completed")

    # The same Task closes through close_task, and its accepted project-use decision records the Spike, closing
    # PR #288's known limit that the Spike branch was tested at function level only.
    outcome = c1._c1_command(c1._command_id(9001), _OUTCOME_COMMANDS["completed"], c1.ATTEMPT_ID,
                             coordinator.ledger.snapshot().stream_versions[c1.ATTEMPT_ID],
                             _outcome_payload("completed", result_route.EVIDENCE_IDS))  # fmt: skip
    assert task.seeding.submit(outcome).status == "accepted"
    for artefact_id in result_route.EVIDENCE_IDS:
        grant = activate_lifecycle_grant(bound.harness, subject_kind="artefact", subject_id=artefact_id,
                                         command_types=("RegisterArtefact",))  # fmt: skip
        manifest = _artefact_manifest(artefact_id)
        content = canonical_bytes({"artefact_id": artefact_id, "outcome": "passed"})
        manifest.update(content_sha256=sha256_hex(content), size_bytes=len(content),
                        relative_path=f"evidence/{artefact_id}.json")  # fmt: skip
        payload = {"new_artefact_id": artefact_id, "manifest": manifest}
        command = c1._c1_command(
            new_id("command"), "RegisterArtefact", artefact_id, 0, payload, authority_grant_id=grant
        )
        assert task.seeding.submit(command).status == "accepted"
    for effect in spec_task.EFFECTS:
        _advance_task(task, effect, tmp_path, capsys)
    task.decision_id = spec_result.subject_id(PROJECT_ID, c1.TASK_ID)

    def use_grant(actor, commands, *, agent=False):
        return activate_lifecycle_grant(bound.harness, subject_kind="artefact", subject_id=task.decision_id,
                                        actor_id=actor, allowed_actor_classes=("agent",) if agent else ("human",),
                                        command_types=commands, grant_id=new_id("authority_grant"))  # fmt: skip

    grants = {
        "register": use_grant(OWNER, ("RegisterArtefact",)),
        "review": use_grant(result_route.REVIEWER, ("RecordScientificReview",), agent=True),
        "use": use_grant(OWNER, ("SetArtefactUseAuthority",)),
    }
    task.grants_project_use = grants
    # A decided Spike exists, so the project-use decision names it rather than a no_spike reason.
    register = {key: value for key, value in result_route.register_intent().items() if key != "no_spike_reason"}
    # P5-10: the SPEC-02 contract supports no superiority or paper claim, so a Spike PROMOTE cannot adopt the
    # method as the project's default; nothing is appended.
    adopted = {**register, "disposition": "adopt_default"}
    assert "not permitted by a PROMOTE Decision" in result_route._project_use(
        task, tmp_path, capsys, adopted, actor=OWNER, grant=grants["register"], refused=True
    )
    result_route._project_use(task, tmp_path, capsys, register, actor=OWNER, grant=grants["register"])
    review_evidence = result_route._review_evidence(task)
    result_route._project_use(task, tmp_path, capsys, result_route.accept_intent(), actor=result_route.REVIEWER,
                              grant=grants["review"], evidence=review_evidence)  # fmt: skip
    result_route._project_use(task, tmp_path, capsys, result_route.accept_intent(), actor=OWNER, grant=grants["use"])
    result = result_route._result(task, tmp_path, capsys, "json")
    assert result["status"] == "accepted"
    decision = result["project_use_decision"]
    assert decision["spike"]["spike_id"] == ids["spike_id"] and decision["spike"]["status"] == "reviewed"
    assert decision["decision"]["decision_id"] == ids["spike_decision_id"]
    assert decision["decision"]["promotion_gate"] == "spike_to_preregistration"
    assert decision["decision"]["selected_option"] == "PROMOTE"
    assert decision["intent"]["disposition"] == "retain_experimental_benchmark"


def _outcome_store(tmp_path, monkeypatch, capsys, source_repo) -> tuple:  # noqa: F811
    """A started Spike, its evidence and another Attempt's artefact registered: what every refusal family needs.

    The SPEC-02 outcome refusals are split by family (return; verdict and review; decision) so that no test carries
    every refusal, and a mutation control re-runs only its own family (test-cost follow-up, 2026-10-05).
    """
    bound = _bind(tmp_path, monkeypatch)
    candidate_id, _ = _promoted(bound, tmp_path, capsys, source_repo, monkeypatch)
    ids = _started(bound, tmp_path, capsys, candidate_id)
    _evidence(bound)
    _register(bound, FOREIGN, "evaluation_run", attempt_id=OTHER_ATTEMPT)
    register = _grant(bound, "RegisterArtefact", ids["spec_02_return_id"], OWNER, human=True)
    return bound, candidate_id, ids, register


def _returned(bound, tmp_path, capsys, candidate_id: str, register: str) -> None:
    """The owner registers the complete return, then the producer records its PASS verdict."""
    complete = spec_02_intent(spec_assay.RETURN_02, candidate_id)
    _invoke(bound, tmp_path, capsys, complete, register, OWNER, evidence=spike_evidence())
    producer = _grant(bound, "RecordSpikeVerdict", candidate_id, PRODUCER)
    _invoke(bound, tmp_path, capsys, complete, producer, PRODUCER, evidence=spike_evidence())


@pytest.mark.slow
def test_spec_02_return_route_refuses_what_admission_accepts(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound, candidate_id, ids, register = _outcome_store(tmp_path, monkeypatch, capsys, source_repo)
    evidence = spike_evidence()
    complete = spec_02_intent(spec_assay.RETURN_02, candidate_id)
    partial_return = spec_02_intent(spec_assay.RETURN_02_PARTIAL, candidate_id)

    # The verdict matches the action that records it.
    assert "PASS or FAIL" in _invoke(bound, tmp_path, capsys, complete, register, OWNER,
                                     evidence=spike_evidence("PARTIAL"), refused=True)  # fmt: skip
    assert "PARTIAL verdict" in _invoke(bound, tmp_path, capsys, partial_return, register, OWNER, evidence=evidence,
                                        refused=True)  # fmt: skip
    # A verdict inherited admission would not record is refused before registration: a PASS with a failed failure
    # predicate breaks the W11 truth table.
    failed = spike_evidence()
    failed["failure_predicates"][0]["status"] = "failed"
    assert "would not be admitted" in _invoke(bound, tmp_path, capsys, complete, register, OWNER, evidence=failed,
                                              refused=True)  # fmt: skip
    # Every artefact the verdict cites comes from the Spike's own Attempt (P-058, 2026-09-25): its artefact refs,
    # and each artefact a success predicate, failure predicate or kill condition cites as evidence (PR #309 review).
    # Admission accepts any registered artefact in either place. Each case borrows in one place only, so each check
    # is the only one that can refuse it.
    borrowed = spike_evidence()
    borrowed["artefact_refs"] = [_evidence_ref(FOREIGN)]
    assert "Spike's own Attempt" in _invoke(bound, tmp_path, capsys, complete, register, OWNER, evidence=borrowed,
                                            refused=True)  # fmt: skip
    for predicates in ("success_predicates", "failure_predicates", "kill_conditions"):
        borrowed = spike_evidence()
        borrowed[predicates][0]["evidence_refs"] = [_evidence_ref(FOREIGN)]
        assert "Spike's own Attempt" in _invoke(bound, tmp_path, capsys, complete, register, OWNER,
                                                evidence=borrowed, refused=True)  # fmt: skip
    missing = {key: value for key, value in evidence.items() if key != "limitations"}
    assert "evidence fields are not exact" in _invoke(bound, tmp_path, capsys, complete, register, OWNER,
                                                      evidence=missing, refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, complete, register, OWNER, evidence=evidence)
    # The Partial alternative shares the return identity, so it is now excluded.
    assert "is excluded" in _invoke(bound, tmp_path, capsys, partial_return, register, OWNER,
                                    evidence=spike_evidence("PARTIAL"), refused=True)  # fmt: skip


@pytest.mark.slow
def test_spec_02_review_route_refuses_what_admission_accepts(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    """The verdict row's and the outcome review's refusals, after the complete return is registered."""
    bound, candidate_id, ids, register = _outcome_store(tmp_path, monkeypatch, capsys, source_repo)
    evidence = spike_evidence()
    complete = spec_02_intent(spec_assay.RETURN_02, candidate_id)
    _invoke(bound, tmp_path, capsys, complete, register, OWNER, evidence=evidence)

    # Only the prospective producer records the verdict, and only the exact return the owner registered.
    for actor, human in ((OWNER, True), (STEWARD, False)):
        grant = _grant(bound, "RecordSpikeVerdict", candidate_id, actor, human=human)
        assert "prospective producer" in _invoke(bound, tmp_path, capsys, complete, grant, actor, evidence=evidence,
                                                 refused=True)  # fmt: skip
    producer = _grant(bound, "RecordSpikeVerdict", candidate_id, PRODUCER)
    revised = {**evidence, "limitations": ["A limitation the registered return does not state."]}
    assert "exact operator return" in _invoke(bound, tmp_path, capsys, complete, producer, PRODUCER, evidence=revised,
                                              refused=True)  # fmt: skip
    _invoke(bound, tmp_path, capsys, complete, producer, PRODUCER, evidence=evidence)

    # Neither the producer nor the owner requests the outcome review, and the owner does not record it.
    review_intent = spec_02_intent(spec_assay.REVIEW_02, candidate_id)
    for actor, human in ((PRODUCER, False), (OWNER, True)):
        grant = _grant(bound, "RequestDiscoveryOutcomeReview", candidate_id, actor, human=human)
        assert "neither the producer nor the owner" in _invoke(bound, tmp_path, capsys, review_intent, grant, actor,
                                                               refused=True)  # fmt: skip
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    owner_review = _grant(bound, "ReviewDiscoveryOutcome", ids["spike_review_id"], OWNER, human=True)
    assert "must not be the owner" in _invoke(bound, tmp_path, capsys, review_intent, owner_review, OWNER,
                                              evidence=OUTCOME_VERDICT_EVIDENCE, refused=True)  # fmt: skip
    _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["spike_review_id"], OUTCOME_REVIEWER,
         evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert _states(bound.coordinator, candidate_id)[spec_assay.REVIEW_02] == "completed"


@pytest.mark.slow
def test_spec_02_decision_refuses_what_admission_accepts(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    """The Spike decision's refusals, after the return, the verdict and the outcome review are recorded."""
    bound, candidate_id, ids, register = _outcome_store(tmp_path, monkeypatch, capsys, source_repo)
    _returned(bound, tmp_path, capsys, candidate_id, register)
    review_intent = spec_02_intent(spec_assay.REVIEW_02, candidate_id)
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["spike_review_id"], OUTCOME_REVIEWER,
         evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip

    # None of the producer, the outcome reviewer or the owner proposes the decision.
    promote = spec_02_intent(spec_assay.DECIDE_02, candidate_id, recommendation="PROMOTE")
    for actor, human in ((PRODUCER, False), (OUTCOME_REVIEWER, False), (OWNER, True)):
        grant = _grant(bound, "ProposePromotionDecision", candidate_id, actor, human=human)
        assert "neither the producer, the reviewer nor the owner" in _invoke(
            bound, tmp_path, capsys, promote, grant, actor, refused=True)  # fmt: skip
    # No KILL after a PASS (W11 §4.5), whether proposed or selected.
    proposer = _grant(bound, "ProposePromotionDecision", candidate_id, PROPOSER)
    kill = spec_02_intent(spec_assay.DECIDE_02, candidate_id, recommendation="KILL")
    assert "cannot KILL after a PASS" in _invoke(bound, tmp_path, capsys, kill, proposer, PROPOSER, refused=True)
    park = spec_02_intent(spec_assay.DECIDE_02, candidate_id, recommendation="PARK")
    _invoke(bound, tmp_path, capsys, park, proposer, PROPOSER)
    owner = _grant(bound, "ResolveDecision", ids["spike_decision_id"], OWNER, human=True)
    assert "cannot KILL after a PASS" in _invoke(bound, tmp_path, capsys, park, owner, OWNER,
                                                 evidence={"selected_option": "KILL", "revisit_triggers": []},
                                                 refused=True)  # fmt: skip
    # A PARK needs the owner's revisit triggers, as for SPEC-01.
    assert "revisit triggers" in _invoke(bound, tmp_path, capsys, park, owner, OWNER,
                                         evidence={"selected_option": "PARK", "revisit_triggers": []},
                                         refused=True)  # fmt: skip
    assert _invoke(bound, tmp_path, capsys, park, owner, OWNER, evidence=SPIKE_PARK)["state"] == "completed"
    assert _replay(bound.coordinator)["candidates"][candidate_id]["status"] == "parked"


@pytest.mark.slow
def test_public_spec_02_partial_path_ends_at_a_partial_review(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    bound = _bind(tmp_path, monkeypatch)
    coordinator = bound.coordinator
    candidate_id, _ = _promoted(bound, tmp_path, capsys, source_repo, monkeypatch)
    ids = _started(bound, tmp_path, capsys, candidate_id)
    _evidence(bound)
    evidence = spike_evidence("PARTIAL")
    partial_return = spec_02_intent(spec_assay.RETURN_02_PARTIAL, candidate_id)
    register = _grant(bound, "RegisterArtefact", ids["spec_02_return_id"], OWNER, human=True)
    producer = _grant(bound, "RecordSpikeVerdict", candidate_id, PRODUCER)

    # OR-019 closes the Attempt and its Lease, so admission refuses it on an expired Lease. Both Partial rows are
    # held to a Lease that is live when each is taken, so the route never registers a Partial return that OR-019
    # would refuse at that moment (P-058, 2026-09-25).
    with monkeypatch.context() as expired:
        expired.setattr(cli, "SpecCoordinator", partial(SpecCoordinator, clock=lambda: LATE))
        assert "Lease that has not expired" in _invoke(bound, tmp_path, capsys, partial_return, register, OWNER,
                                                       evidence=evidence, refused=True)  # fmt: skip
    registered = _invoke(bound, tmp_path, capsys, partial_return, register, OWNER, evidence=evidence)
    assert registered["state"] == "prepared" and registered["next_effect"] == "RecordSpikeVerdict"
    with monkeypatch.context() as expired:
        expired.setattr(cli, "SpecCoordinator", partial(SpecCoordinator, clock=lambda: LATE))
        assert "Lease that has not expired" in _invoke(bound, tmp_path, capsys, partial_return, producer, PRODUCER,
                                                       evidence=evidence, refused=True)  # fmt: skip
    recorded = _invoke(bound, tmp_path, capsys, partial_return, producer, PRODUCER, evidence=evidence)
    assert recorded["state"] == "completed"
    projection = _replay(coordinator)
    assert projection["spikes"][ids["spike_id"]]["status"] == "partial_recorded"
    assert projection["candidates"][candidate_id]["status"] == "spike_partial_recorded"
    streams = _streams(coordinator)
    assert streams[c1.ATTEMPT_ID]["status"] == "partial" and streams[c1.LEASE_ID]["status"] == "released"
    returned = coordinator.objects.read(spec_assay.SPEC_02_RETURN_KIND, ids["spec_02_return_id"], 1)
    assert returned["intent"]["action"] == spec_assay.RETURN_02_PARTIAL and returned["operator_return"] == evidence
    # The complete alternative shares the return identity, so it is excluded.
    assert "is excluded" in _invoke(bound, tmp_path, capsys, spec_02_intent(spec_assay.RETURN_02, candidate_id),
                                    register, OWNER, evidence=spike_evidence(), refused=True)  # fmt: skip

    review_intent = spec_02_intent(spec_assay.REVIEW_02_PARTIAL, candidate_id)
    owner_request = _grant(bound, "RequestDiscoveryOutcomeReview", candidate_id, OWNER, human=True)
    assert "neither the producer nor the owner" in _invoke(bound, tmp_path, capsys, review_intent, owner_request,
                                                           OWNER, refused=True)  # fmt: skip
    _run(bound, tmp_path, capsys, review_intent, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    owner_review = _grant(bound, "ReviewDiscoveryOutcome", ids["spike_review_id"], OWNER, human=True)
    assert "must not be the owner" in _invoke(bound, tmp_path, capsys, review_intent, owner_review, OWNER,
                                              evidence=OUTCOME_VERDICT_EVIDENCE, refused=True)  # fmt: skip
    reviewed = _run(bound, tmp_path, capsys, review_intent, "ReviewDiscoveryOutcome", ids["spike_review_id"],
                    OUTCOME_REVIEWER, evidence=OUTCOME_VERDICT_EVIDENCE)  # fmt: skip
    assert reviewed["state"] == "completed"
    projection = _replay(coordinator)
    assert projection["spikes"][ids["spike_id"]]["status"] == "partial_reviewed"
    assert projection["candidates"][candidate_id]["status"] == "spike_revisit_eligible"
    complete_review = _grant(bound, "RequestDiscoveryOutcomeReview", candidate_id, STEWARD)
    assert "is excluded" in _invoke(bound, tmp_path, capsys, spec_02_intent(spec_assay.REVIEW_02, candidate_id),
                                    complete_review, STEWARD, refused=True)  # fmt: skip

    # A Partial Spike is terminal on the route: the Spike revisit rows are outside the agreed action list.
    proposer = _grant(bound, "ProposePromotionDecision", candidate_id, PROPOSER)
    decide = spec_02_intent(spec_assay.DECIDE_02, candidate_id, recommendation="PARK")
    assert "Partial Spike" in _invoke(bound, tmp_path, capsys, decide, proposer, PROPOSER, refused=True)
    taken = (spec_assay.APPROVE_02, spec_assay.PREPARE_02, spec_assay.START_02, spec_assay.RETURN_02_PARTIAL,
             spec_assay.REVIEW_02_PARTIAL)  # fmt: skip
    assert _states(coordinator, candidate_id) == dict.fromkeys(taken, "completed")


def _control_store(tmp_path, monkeypatch, capsys) -> tuple:
    """A Candidate promoted and its Spike started through inherited admission alone (decisive controls only)."""
    bound = _bind(tmp_path, monkeypatch)
    coordinator = bound.coordinator
    _advance(bound, tmp_path, capsys, GENESIS_INTENT, "ImportAcceptedW11CatalogueGenesis", CATALOGUE_STREAM_ID,
             OWNER, human=True)  # fmt: skip
    for command_type, subject, actor, human in _bar_steps():
        _advance(bound, tmp_path, capsys, BAR_INTENT, command_type, subject, actor, human)
    candidate_id, assay_id = _direct_promoted(bound, 1)
    _seed_task_naming(bound, candidate_id, monkeypatch)
    projection = _replay(coordinator)
    candidate, assay = projection["candidates"][candidate_id], projection["assays"][assay_id]
    promotion = projection["decisions"][candidate["decision_id"]]
    assay_ref = _record_ref(assay_id, 1, assay["scorecard_sha256"])
    candidate_ref = _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"])
    plan = {
        "schema_id": "ars://portfolio/spike-plan",
        "schema_version": "1.0.0",
        "spike_id": SPIKE,
        "candidate_ref": candidate_ref,
        "originating_assay_ref": assay_ref,
        "source_scorecard_refs": [assay_ref],
        "assay_promotion_decision_ref": _record_ref(
            candidate["decision_id"], promotion["proposal_version"], promotion["proposal_event_hash"]
        ),
        "required_approving_authority": OWNER,
        "scope": APPROVAL_EVIDENCE["scope"],
        **PLAN_EVIDENCE,
    }
    subject = {"candidate_id": candidate_id, "spike_id": SPIKE}
    plan_sha256 = sha256_hex(canonical_bytes(plan))
    registered = {**subject, "row_id": "OR-014", "plan_sha256": plan_sha256, "plan_artifact": plan}
    assert _direct(bound, "RegisterSpikePlan", SPIKE, registered, STEWARD) == "accepted"
    resource = coordinator._operational_state(coordinator.ledger.snapshot().events)[c1.RESOURCE_GRANT_ID]
    plan_ref = _record_ref(SPIKE, 1, plan_sha256)
    relation = {
        "schema_id": "ars://portfolio/relation/spike-execution-authority",
        "schema_version": "1.0.0",
        "relation_kind": "spike_execution_authority",
        "decision_id": EXECUTION,
        "spike_ref": plan_ref,
        "candidate_ref": candidate_ref,
        "plan_ref": plan_ref,
        "resource_ref": _record_ref(c1.RESOURCE_GRANT_ID, 1, sha256_hex(canonical_bytes(resource))),
        "route_ref": plan_ref,
        "assurance_ref": assay_ref,
        "selected_option": "AUTHORIZE",
        "actor_id": OWNER,
    }
    proposal = {
        **subject,
        "row_id": "OR-015",
        "decision_id": EXECUTION,
        "w2_payload": {
            "question": "spike_execution",
            "recommendation": "approve",
            "new_decision_id": EXECUTION,
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
        "execution_authority_relation": relation,
    }
    assert _direct(bound, "ProposeSpikeExecutionDecision", EXECUTION, proposal, STEWARD) == "accepted"

    def approval(grant: str) -> dict:
        return {
            **subject,
            "row_id": "OR-016",
            "decision_id": EXECUTION,
            "w2_payload": _resolution(EXECUTION, "approve", grant, ["evidence:exact"], [], ["StartSpike"], []),
            "execution_authority_relation": relation,
        }

    status = _built_direct(bound, "ResolveDecision", EXECUTION, approval, OWNER, subject=EXECUTION, human=True)
    assert status == "accepted"
    attempt = coordinator._operational_state(coordinator.ledger.snapshot().events)[c1.ATTEMPT_ID]
    start = {
        **subject,
        "row_id": "OR-017",
        "attempt_id": c1.ATTEMPT_ID,
        "attempt_sha256": sha256_hex(canonical_bytes(attempt)),
        "lease_id": c1.LEASE_ID,
        "resource_grant_id": c1.RESOURCE_GRANT_ID,
    }
    assert _direct(bound, "StartSpike", SPIKE, start, OWNER, human=True) == "accepted"
    _evidence(bound)
    _register(bound, FOREIGN, "evaluation_run", attempt_id=OTHER_ATTEMPT)
    return bound, candidate_id


def _resolution(decision_id, option, grant, governing, reviews, commands, triggers) -> dict:
    return {
        "decision_id": decision_id,
        "selected_option": option,
        "effective_scope": "exact Discovery subject",
        "decision_revision": 1,
        "deciding_actor_id": OWNER,
        "decision_authority_grant_id": grant,
        "governing_evidence_refs": governing,
        "considered_review_ids": reviews,
        "effective_at": "2026-09-11T00:00:00Z",
        "permitted_commands": commands,
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": triggers,
    }


def _verdict(bound, candidate_id: str, actor: str, evidence: dict, *, human: bool = False) -> str:
    projection = _replay(bound.coordinator)
    candidate, spike = projection["candidates"][candidate_id], projection["spikes"][SPIKE]
    assay = projection["assays"][candidate["assay_id"]]
    artifact = {
        "schema_id": "ars://portfolio/spike-verdict",
        "schema_version": "1.0.0",
        "spike_id": SPIKE,
        "candidate_ref": _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
        "originating_assay_ref": _record_ref(candidate["assay_id"], 1, assay["scorecard_sha256"]),
        "spike_plan_ref": _record_ref(SPIKE, 1, spike["plan_sha256"]),
        "attempt_ref": _record_ref(spike["attempt_id"], 1, spike["attempt_sha256"]),
        **evidence,
    }
    payload = {"row_id": "OR-018", "candidate_id": candidate_id, "spike_id": SPIKE, "verdict": artifact["verdict"],
               "verdict_sha256": sha256_hex(canonical_bytes(artifact)), "verdict_artifact": artifact}  # fmt: skip
    return _direct(bound, "RecordSpikeVerdict", SPIKE, payload, actor, human=human)


def _review_request(bound, candidate_id: str, actor: str, *, human: bool = False) -> str:
    digest = _replay(bound.coordinator)["spikes"][SPIKE]["verdict_sha256"]
    contract = {
        "review_type": "provenance",
        "new_review_id": REVIEW,
        "subject_ids": [SPIKE],
        "subject_hashes": [digest],
        "governing_refs": ["W11:OR-036"],
        "review_questions": ["Is the Spike verdict exact?"],
        "required_evidence_refs": ["spike-verdict:exact"],
        "required_lanes": ["provenance"],
        "reviewer_capability": ["spike-independent-review"],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": ["approve", "changes_requested", "reject"],
        "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
        "deadline": "2026-12-31T00:00:00Z",
        "escalation_rule": "owner-ruling",
    }
    payload = {"row_id": "OR-036", "candidate_id": candidate_id, "spike_id": SPIKE, "review_id": REVIEW,
               "subject_sha256": digest, "review_contract": contract}  # fmt: skip
    return _direct(bound, "RequestDiscoveryOutcomeReview", REVIEW, payload, actor, human=human)


def _review(bound, candidate_id: str, actor: str, *, human: bool = False) -> str:
    digest = _replay(bound.coordinator)["spikes"][SPIKE]["verdict_sha256"]
    verdict = {
        "review_id": REVIEW,
        "verdict": "approve",
        "findings": [],
        "required_evidence_refs": ["spike-verdict:exact"],
        "limitations": [],
        "conditions": [],
        "reviewer_actor_id": actor,
        **{key: OUTCOME_VERDICT_EVIDENCE[key] for key in spec_assay._VERDICT_EVIDENCE - {"findings", "limitations"}},
        "unchanged_subject_sha256": digest,
        "producing_attempt_id": c1.ATTEMPT_ID,
        "computed_independence_grade": "independent",
    }
    payload = {"row_id": "OR-020", "candidate_id": candidate_id, "spike_id": SPIKE, "review_id": REVIEW,
               "subject_sha256": digest, "review_verdict": verdict}  # fmt: skip
    return _direct(bound, "ReviewDiscoveryOutcome", REVIEW, payload, actor, human=human)


def _proposal(bound, candidate_id: str, option: str, actor: str, *, human: bool = False) -> str:
    projection = _replay(bound.coordinator)
    candidate, spike = projection["candidates"][candidate_id], projection["spikes"][SPIKE]
    aggregate = _record_ref(SPIKE, spike["version"], _aggregate_content_hash(spike))
    next_state = {"PROMOTE": "preregistration_authorized", "PARK": "parked", "KILL": "killed"}[option]
    payload = {
        "row_id": "OR-026",
        "candidate_id": candidate_id,
        "spike_id": SPIKE,
        "decision_id": DECISION,
        "review_id": REVIEW,
        "verdict_sha256": spike["verdict_sha256"],
        "w2_payload": {
            "question": "spike_to_preregistration",
            "recommendation": option,
            "new_decision_id": DECISION,
            "decision_revision": 1,
            "decision_kind": "design_lock",
            "options": ["PROMOTE", "PARK", "KILL"],
            "governing_evidence_refs": [f"review:{REVIEW}"],
            "affected_task_ids": [],
            "affected_claim_ids": [],
            "required_authority": "owner",
            "expires_at": "2026-12-31T00:00:00Z",
            "review_date": "2026-09-11T00:00:00Z",
            "consequences": ["decide the reviewed Spike"],
        },
        "promotion_relation": {
            "schema_id": "ars://portfolio/relation/discovery-promotion",
            "schema_version": "1.0.0",
            "relation_kind": "discovery_promotion",
            "decision_id": DECISION,
            "candidate_ref": _record_ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
            "gate": "spike_to_preregistration",
            "aggregate_ref": aggregate,
            "aggregate_relation_hash": spike["plan_sha256"],
            "evidence_ref": aggregate,
            "selected_option": option,
            "next_candidate_state": next_state,
            "rationale": "Decisive control: decide the reviewed Spike.",
            "considered_evidence_refs": [_review_ref(projection["reviews"][REVIEW])],
            "conditions": [],
            "effective_scope": f"spike_to_preregistration:{candidate_id}",
            "revisit_triggers": [],
            "actor_id": actor,
        },
    }
    return _direct(bound, "ProposePromotionDecision", DECISION, payload, actor, human=human)


def _selection(bound, candidate_id: str, option: str, triggers: list[str]) -> str:
    verdict_sha256 = _replay(bound.coordinator)["spikes"][SPIKE]["verdict_sha256"]

    def build(grant: str) -> dict:
        return {
            "row_id": "OR-027",
            "candidate_id": candidate_id,
            "spike_id": SPIKE,
            "decision_id": DECISION,
            "review_id": REVIEW,
            "verdict_sha256": verdict_sha256,
            "w2_payload": _resolution(DECISION, option, grant, [f"review:{REVIEW}"], [REVIEW], [], triggers),
        }

    return _built_direct(bound, "ResolveDecision", DECISION, build, OWNER, subject=DECISION, human=True)


@pytest.mark.slow
@pytest.mark.parametrize("store", ("verdict", "review", "proposal"))
def test_admission_accepts_the_spike_outcome_collapses_the_route_refuses(store, tmp_path, monkeypatch, capsys):
    """Each relation the route refuses is one inherited admission records; one store per started Spike."""
    bound, candidate_id = _control_store(tmp_path, monkeypatch, capsys)
    if store == "verdict":
        # The owner, not the prospective producer, records a verdict citing another Attempt's artefact, in its
        # artefact refs and as every predicate's evidence; the owner requests its review; the outcome reviewer
        # proposes; and the owner parks with no revisit trigger.
        foreign = spike_evidence(artefact=FOREIGN)
        assert _verdict(bound, candidate_id, OWNER, foreign, human=True) == "accepted"
        assert _review_request(bound, candidate_id, OWNER, human=True) == "accepted"
        assert _review(bound, candidate_id, OUTCOME_REVIEWER) == "accepted"
        assert _proposal(bound, candidate_id, "PARK", OUTCOME_REVIEWER) == "accepted"
        assert _selection(bound, candidate_id, "PARK", []) == "accepted"
    elif store == "review":
        # The producer requests the review, the owner records it and proposes, and the owner selects KILL after
        # a PASS although PROMOTE was proposed.
        assert _verdict(bound, candidate_id, PRODUCER, spike_evidence()) == "accepted"
        assert _review_request(bound, candidate_id, PRODUCER) == "accepted"
        assert _review(bound, candidate_id, OWNER, human=True) == "accepted"
        assert _proposal(bound, candidate_id, "PROMOTE", OWNER, human=True) == "accepted"
        assert _selection(bound, candidate_id, "KILL", []) == "accepted"
    else:
        # The producer proposes KILL after a PASS.
        assert _verdict(bound, candidate_id, PRODUCER, spike_evidence()) == "accepted"
        assert _review_request(bound, candidate_id, STEWARD) == "accepted"
        assert _review(bound, candidate_id, OUTCOME_REVIEWER) == "accepted"
        assert _proposal(bound, candidate_id, "KILL", PRODUCER) == "accepted"
    assert _manifest_of(bound.coordinator, FOREIGN)["attempt_id"] == OTHER_ATTEMPT
