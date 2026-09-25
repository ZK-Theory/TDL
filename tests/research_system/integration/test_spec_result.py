"""06s Phase 3 (P-057): the accepted project-use result on the public SPEC route, and its decisive negatives."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import subprocess
import sys
import uuid

import pytest

from research_system import cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import spec_result, spec_task
from research_system.discovery.runtime import DiscoveryRuntime, replay_discovery
from research_system.discovery.spec import _REGISTRATION_SERVICES, ACTION_EFFECTS
from research_system.discovery.spec_source import source_ids
from research_system.errors import ConflictError, IntegrityError, SchemaError
from research_system.ids import new_id
from research_system.methods.registration import _stable_command_id
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import ACTORS, PROJECT_ID, REPO_ROOT, activate_lifecycle_grant
from tests.research_system.integration import test_wp6_1_c1_readiness_lease as c1
from tests.research_system.integration import test_wp6_6_discovery_runtime as w11
from tests.research_system.integration.test_artefact_authority_commands import command as artefact_command
from tests.research_system.integration.test_artefact_authority_commands import artefact_manifest
from tests.research_system.integration.test_spec_source import (  # noqa: F401
    bind_scratch_route,
    invoke_cli,
    source_intent,
    source_repo,
)
from tests.research_system.integration.test_spec_task import _advance, _seed_bound_task, _streams, _tail
from tests.research_system.integration.test_wp6_1_c2_operating_lifecycle import _artefact_manifest

OWNER = ACTORS["actor-a"]
REVIEWER = ACTORS["actor-b"]
ASSAY_REVIEWER = "act_019fed25-b33e-7740-b280-6f661aaeff71"
EVIDENCE_IDS = ("art_01978abc-9600-7000-8000-000000009600", "art_01978abc-9601-7000-8000-000000009601")
ASSAY_ID = "asy_019fed25-b33e-7740-b280-6f661aaeff69"
ASSAY_REVIEW_ID = "rev_019fed25-b33e-7740-b280-6f661aaeff70"
PARK_DECISION_ID = "dec_019fed25-b33e-7740-b280-6f661aaeff6b"
DEADLINE = "2026-12-31T00:00:00Z"
FORBIDDEN_ROUTE_WORDS = ("promot", "replicat", "adopt")

# Owner prose deliberately avoids the forbidden words, so any hit is route wording.
REGISTER_TEXT = {
    "disposition": "retain_experimental_benchmark",
    "rationale": "The bounded route evidence supports keeping the method only as an experimental benchmark.",
    "limitations": ["synthetic scratch evidence only", "no estimand or representation is fixed"],
    "next_gates": ["an owner-approved revisit before any wider use"],
    "subset_qualification": "Scratch route-proof subset of the operational route.",
    "no_spike_reason": "The owner parked the Candidate at the Assay gate, so no Spike ran.",
}


def register_intent(**overrides) -> dict:
    return {
        "action": spec_result.REGISTER,
        "task_id": c1.TASK_ID,
        "reason": "record the owner's project-use decision",
        **REGISTER_TEXT,
        **overrides,
    }


def accept_intent() -> dict:
    return {"action": spec_result.ACCEPT, "task_id": c1.TASK_ID, "reason": "independently accept the decision"}


def _replay_discovery(coordinator) -> dict:
    return replay_discovery(
        coordinator.ledger.snapshot().events,
        schemas=coordinator.schemas,
        authority_state_validator=coordinator.resolver.validate_replayed_administration_state,
    )


def _governed_discovery(bound) -> DiscoveryRuntime:
    """The bound store's Discovery runtime, issuing each W11 row the exact scoped grant it needs."""
    coordinator, harness = bound.coordinator, bound.harness
    candidate_scoped = {"RequestAssay", "RecordAssayScore", "RequestDiscoveryOutcomeReview", "ProposePromotionDecision"}
    subject_kinds = {
        "RequestAssay": "scope_definition",
        "RecordAssayScore": "scope_definition",
        "RequestDiscoveryOutcomeReview": "scope_definition",
        "ReviewDiscoveryOutcome": "review",
        "ProposePromotionDecision": "scope_definition",
        "RegisterAssayRubricContent": "scope_definition",
        "RegisterAssayEvidenceScopeContent": "scope_definition",
        "ObserveW11AuthorityFile": "scope_definition",
        "RequestW11AuthorityReview": "review",
        "RecordW11AuthorityReview": "review",
        "ProposeW11AuthorityDecision": "decision",
        "ResolveDecision": "decision",
    }

    class Governed(DiscoveryRuntime):
        def submit(self, envelope):
            value = deepcopy(envelope)
            command_type = value["command_type"]
            subject_id = (
                value["payload"]["candidate_id"] if command_type in candidate_scoped else value["target_stream_id"]
            )
            raw = bytearray(hashlib.sha256(f"{command_type}:{subject_id}".encode()).digest()[:16])
            raw[6] = (raw[6] & 0x0F) | 0x70
            raw[8] = (raw[8] & 0x3F) | 0x80
            grant_id = f"agr_{uuid.UUID(bytes=bytes(raw))}"
            activate_lifecycle_grant(
                harness,
                subject_kind=subject_kinds[command_type],
                subject_id=subject_id,
                actor_id=value["actor_id"],
                allowed_actor_classes=("human",) if value["actor_id"] == OWNER else ("agent",),
                command_types=(command_type,),
                grant_id=grant_id,
            )
            value["authority_grant_id"] = grant_id
            w2_payload = value.get("payload", {}).get("w2_payload")
            if isinstance(w2_payload, dict) and w2_payload.get("decision_authority_grant_id") == w11.GRANT_ID:
                w2_payload["decision_authority_grant_id"] = grant_id
            return super().submit(value)

    binding = coordinator.binding
    return Governed(
        binding.control_root,
        coordinator.ledger,
        coordinator.schemas,
        catalogue_path=binding.repository_root / ".research-system/evals/expected/w11-portfolio-discovery-v1.json",
        authority_resolver=coordinator.resolver,
        clock=coordinator.clock,
        repository_root=binding.repository_root,
        root_tokens={"control": binding.control_root, "repo": binding.repository_root},
        operational_ledger=coordinator.ledger,
    )


def _park_candidate(bound, candidate_id: str, monkeypatch) -> None:
    """Drive the Candidate through the governed W11 Assay rows to an owner PARK Decision."""
    coordinator = bound.coordinator
    monkeypatch.setattr(w11, "replay_discovery", lambda events, **_: _replay_discovery(coordinator))
    runtime = _governed_discovery(bound)
    candidate_sha256 = _replay_discovery(coordinator)["candidates"][candidate_id]["content_sha256"]
    bar_sha256, producer_sha256 = w11._accept_assay_bar(runtime)

    def submit(command_type, target, version, payload, actor=OWNER):
        command = w11._command(command_type, target, version, payload)
        command["actor_id"] = actor
        assert runtime.submit(command).status == "accepted", command_type

    submit("RequestAssay", ASSAY_ID, 0, {
        "row_id": "OR-003", "candidate_id": candidate_id, "assay_id": ASSAY_ID, "candidate_revision": 1,
        "candidate_sha256": candidate_sha256, "assay_bar_acceptance_sha256": bar_sha256,
        "producer_relation_sha256": producer_sha256,
    })  # fmt: skip
    scorecard = w11._scorecard(runtime, candidate_id, ASSAY_ID, candidate_sha256, producer_sha256)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
    submit("RecordAssayScore", ASSAY_ID, 2, {
        "row_id": "OR-004", "candidate_id": candidate_id, "assay_id": ASSAY_ID, "scorecard_sha256": scorecard_sha256,
        "scorecard_artifact": scorecard, "producer_relation_sha256": producer_sha256,
    })  # fmt: skip
    submit("RequestDiscoveryOutcomeReview", ASSAY_REVIEW_ID, 0, {
        "row_id": "OR-034", "candidate_id": candidate_id, "assay_id": ASSAY_ID, "review_id": ASSAY_REVIEW_ID,
        "subject_sha256": scorecard_sha256,
        "review_contract": {
            "review_type": "provenance", "new_review_id": ASSAY_REVIEW_ID, "subject_ids": [ASSAY_ID],
            "subject_hashes": [scorecard_sha256], "governing_refs": ["W11:OR-034"],
            "review_questions": ["Is the scorecard exact?"], "required_evidence_refs": ["scorecard:exact"],
            "required_lanes": ["provenance"], "reviewer_capability": ["assay-independent-review"],
            "required_independence_grade": "independent", "visibility_policy": "owner-visible",
            "allowed_verdicts": ["approve", "changes_requested", "reject"],
            "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
            "deadline": DEADLINE, "escalation_rule": "owner-ruling",
        },
    })  # fmt: skip
    submit("ReviewDiscoveryOutcome", ASSAY_REVIEW_ID, 1, {
        "row_id": "OR-006", "candidate_id": candidate_id, "assay_id": ASSAY_ID, "review_id": ASSAY_REVIEW_ID,
        "subject_sha256": scorecard_sha256, "verdict": "approve",
        "review_verdict": {
            "review_id": ASSAY_REVIEW_ID, "verdict": "approve", "findings": [],
            "required_evidence_refs": ["scorecard:exact"], "limitations": [], "conditions": [],
            "reviewer_actor_id": ASSAY_REVIEWER, "reviewer_profile": "independent-assay-reviewer",
            "reviewer_session": "session-spec-result-assay", "reviewer_model_metadata": "test",
            "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff72", "context_manifest_sha256": "7" * 64,
            "unchanged_subject_sha256": scorecard_sha256,
            "producing_attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff73",
            "trace_visibility_evidence_refs": ["trace:assay"], "computed_independence_grade": "independent",
        },
    }, actor=ASSAY_REVIEWER)  # fmt: skip
    submit("ProposePromotionDecision", PARK_DECISION_ID, 0, {
        "row_id": "OR-012", "candidate_id": candidate_id, "decision_id": PARK_DECISION_ID,
        "review_id": ASSAY_REVIEW_ID,
        "w2_payload": {
            "question": "assay_to_spike", "recommendation": "PARK", "new_decision_id": PARK_DECISION_ID,
            "decision_revision": 1, "decision_kind": "design_lock", "options": ["PROMOTE", "PARK", "KILL"],
            "governing_evidence_refs": ["evidence:exact"], "affected_task_ids": [], "affected_claim_ids": [],
            "required_authority": "owner", "expires_at": DEADLINE, "review_date": "2026-09-11T00:00:00Z",
            "consequences": ["park the candidate"],
        },
        "promotion_relation": w11._promotion_relation(
            runtime, decision_id=PARK_DECISION_ID, candidate_id=candidate_id, aggregate_id=ASSAY_ID,
            review_id=ASSAY_REVIEW_ID, gate="assay_to_spike", recommendation="PARK",
        ),
    })  # fmt: skip
    submit("ResolveDecision", PARK_DECISION_ID, 1, {
        "row_id": "OR-013", "candidate_id": candidate_id, "decision_id": PARK_DECISION_ID,
        "w2_payload": {
            "decision_id": PARK_DECISION_ID, "selected_option": "PARK", "effective_scope": "exact Discovery subject",
            "decision_revision": 1, "deciding_actor_id": OWNER, "decision_authority_grant_id": w11.GRANT_ID,
            "governing_evidence_refs": ["evidence:exact"], "considered_review_ids": [],
            "effective_at": "2026-09-10T00:00:00Z", "permitted_commands": [], "superseded_decision_ids": [],
            "conditions": [], "revisit_triggers": ["new objective evidence"],
        },
    })  # fmt: skip
    assert _replay_discovery(coordinator)["candidates"][candidate_id]["status"] == "parked"


@pytest.fixture
def bound_result(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    """A Task accepted through close_task whose named Candidate the owner parked; no decision yet."""
    return _bound_result(tmp_path, monkeypatch, capsys, source_repo)


@pytest.fixture
def bound_amended_result(tmp_path, monkeypatch, capsys, source_repo):  # noqa: F811
    """As ``bound_result``, but the Task is amended after its Attempt ran and before closure."""
    return _bound_result(tmp_path, monkeypatch, capsys, source_repo, amend_after_dispatch=True)


def _bound_result(tmp_path, monkeypatch, capsys, source_repo, *, amend_after_dispatch=False):  # noqa: F811
    bound = bind_scratch_route(
        tmp_path, monkeypatch, extra_repository_files=(w11.ASSAY_RUBRIC_PATH, w11.ASSAY_SCOPE_PATH)
    )
    observation = source_intent(source_repo)
    ids = source_ids(PROJECT_ID, observation)
    register_source = activate_lifecycle_grant(
        bound.harness, subject_kind="artefact", subject_id=ids["artefact_id"], command_types=("RegisterArtefact",)
    )
    scout = activate_lifecycle_grant(
        bound.harness,
        subject_kind="scope_definition",
        subject_id=ids["observation_id"],
        command_types=("IngestScoutObservationBatch",),
    )
    invoke_cli(bound, tmp_path, capsys, observation, "advance", register_source)
    assert invoke_cli(bound, tmp_path, capsys, observation, "advance", scout)["state"] == "completed"
    _park_candidate(bound, ids["candidate_id"], monkeypatch)

    # The governed Task names its Candidate; that relation is what the decision binds.
    original = c1.create_task_command

    def naming_candidate(*args, **kwargs):
        command = original(*args, **kwargs)
        definition = command["payload"]["definition"]
        definition["portfolio_refs"] = [ids["candidate_id"]]
        definition.pop("content_sha256")
        definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
        return command

    monkeypatch.setattr(c1, "create_task_command", naming_candidate)
    task = _seed_bound_task(bound, outcome="completed", candidates=EVIDENCE_IDS)
    if amend_after_dispatch:
        # The Attempt was dispatched on revision 1. Both revisions name the Candidate, so only the dispatched
        # revision distinguishes them.
        version = bound.coordinator.ledger.snapshot().stream_versions[c1.TASK_ID]
        amendment = c1._task_amendment_command(number=9101, expected_stream_version=version)
        assert task.seeding.submit(amendment).status == "accepted"
    for artefact_id in EVIDENCE_IDS:
        grant = activate_lifecycle_grant(
            bound.harness, subject_kind="artefact", subject_id=artefact_id, command_types=("RegisterArtefact",)
        )
        # SubmitForReview requires distinct candidate hashes, so each artefact has its own content.
        manifest = _artefact_manifest(artefact_id)
        content = canonical_bytes({"artefact_id": artefact_id, "outcome": "passed"})
        manifest.update(
            content_sha256=sha256_hex(content), size_bytes=len(content), relative_path=f"evidence/{artefact_id}.json"
        )
        registered = c1._c1_command(
            new_id("command"),
            "RegisterArtefact",
            artefact_id,
            0,
            {"new_artefact_id": artefact_id, "manifest": manifest},
            authority_grant_id=grant,
        )
        assert task.seeding.submit(registered).status == "accepted"
    for effect in spec_task.EFFECTS:
        _advance(task, effect, tmp_path, capsys)

    decision_id = spec_result.subject_id(PROJECT_ID, c1.TASK_ID)

    def grant(actor, commands, *, agent=False, subject=decision_id):
        return activate_lifecycle_grant(
            bound.harness,
            subject_kind="artefact",
            subject_id=subject,
            actor_id=actor,
            allowed_actor_classes=("agent",) if agent else ("human",),
            command_types=commands,
            grant_id=new_id("authority_grant"),
        )

    grants = {
        # The registration grant also permits use authority, so refusing its reuse is decisive.
        "register": grant(OWNER, ("RegisterArtefact", "SetArtefactUseAuthority")),
        "owner_review": grant(OWNER, ("RecordScientificReview",)),
        "review": grant(REVIEWER, ("RecordScientificReview",), agent=True),
        "use": grant(OWNER, ("SetArtefactUseAuthority",)),
        "reviewer_register": grant(REVIEWER, ("RegisterArtefact",), agent=True),
    }
    task.grant = grant
    task.grants_project_use = grants
    task.candidate_id = ids["candidate_id"]
    task.source_artefact_id = ids["artefact_id"]
    task.decision_id = decision_id
    return task


def _config(fixture, tmp_path, *, actor, grant):
    path = tmp_path / "project-use-operator.json"
    path.write_bytes(canonical_bytes({**fixture.bound.config, "operator_actor_id": actor, "authority_grant_id": grant}))
    return path


def _project_use(fixture, tmp_path, capsys, intent, *, actor, grant, evidence=None, refused=False):
    """Drive one project-use invocation through the genuine CLI."""
    payload = dict(intent)
    if evidence is not None:
        payload["evidence"] = evidence
    intent_path = tmp_path / "project-use-intent.json"
    intent_path.write_bytes(canonical_bytes(payload))
    before = _tail(fixture.coordinator)
    args = [
        "discovery",
        "spec",
        "advance",
        "--operator-config",
        str(_config(fixture, tmp_path, actor=actor, grant=grant)),
    ]
    code = cli.main([*args, "--action", intent["action"], "--input", str(intent_path)])
    captured = capsys.readouterr()
    if refused:
        assert code == 1, captured.out
        assert _tail(fixture.coordinator) == before, "a refused project-use invocation appended an event"
        return captured.err
    assert code == 0, captured.err
    return json.loads(captured.out)


def _result(fixture, tmp_path, capsys, output_format, task_id=c1.TASK_ID):
    config = _config(fixture, tmp_path, actor=OWNER, grant=fixture.grants_project_use["use"])
    args = ["discovery", "spec", "result", "--operator-config", str(config), "--task-id", task_id]
    assert cli.main([*args, "--format", output_format]) == 0
    out = capsys.readouterr().out
    return json.loads(out) if output_format == "json" else out


def _review_evidence(fixture, reviewer=REVIEWER, subject=None) -> dict:
    subject = subject or fixture.decision_id
    registration = next(
        event
        for event in fixture.coordinator.ledger.snapshot().events
        if event["event_type"] == "ArtefactRegistered" and event["stream_id"] == subject
    )
    review_id, record_id = new_id("review"), new_id("assurance_record")
    fixture.coordinator.service.governing_evidence_resolver.publish(
        record_id,
        {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": PROJECT_ID,
            "review_id": review_id,
            "subject_sha256": registration["payload"]["manifest"]["content_sha256"],
            "reviewer_actor_id": reviewer,
            "eligible": True,
            "related": False,
            "independence_grade": "I1",
            "status": "active",
        },
    )
    return {"review_id": review_id, "evidence_refs": [record_id]}


def _accept_decision(fixture, tmp_path, capsys) -> dict:
    grants = fixture.grants_project_use
    _project_use(fixture, tmp_path, capsys, register_intent(), actor=OWNER, grant=grants["register"])
    evidence = _review_evidence(fixture)
    _project_use(fixture, tmp_path, capsys, accept_intent(), actor=REVIEWER, grant=grants["review"], evidence=evidence)
    _project_use(fixture, tmp_path, capsys, accept_intent(), actor=OWNER, grant=grants["use"])
    return evidence


def test_the_action_table_names_every_route_action_and_its_ordered_effects():
    assert ACTION_EFFECTS == {
        "observe_source": ("RegisterArtefact", "IngestScoutObservationBatch"),
        "correct_spec_01_source": ("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
        "close_task": (
            "SubmitForReview",
            "RequestReview",
            "AssignReview",
            "StartReview",
            "RecordReviewVerdict",
            "SatisfyReview",
            "AcceptTask",
        ),
        "register_project_use_decision": ("RegisterArtefact",),
        "accept_project_use_decision": ("RecordScientificReview", "SetArtefactUseAuthority"),
        "bootstrap_genesis": ("ImportAcceptedW11CatalogueGenesis",),
        "bootstrap_assay_authority": (
            "RegisterAssayRubricContent",
            "RegisterAssayEvidenceScopeContent",
            "ObserveW11AuthorityFile",
            "ObserveW11AuthorityFile",
            "RequestW11AuthorityReview",
            "RecordW11AuthorityReview",
            "ProposeW11AuthorityDecision",
            "ResolveDecision",
        ),
        "request_spec_01": ("RequestAssay",),
        "prepare_spec_01": ("RegisterArtefact",),
        "return_spec_01_complete": ("RegisterArtefact", "RecordAssayScore"),
        "return_spec_01_partial": ("RegisterArtefact", "RecordAssayPartial"),
        "review_spec_01_complete": ("RequestDiscoveryOutcomeReview", "ReviewDiscoveryOutcome"),
        "review_spec_01_partial": ("RequestDiscoveryOutcomeReview", "ReviewDiscoveryOutcome"),
        "decide_spec_01": ("ProposePromotionDecision", "ResolveDecision"),
        "request_spec_01_revisit": ("ProposeRevisitDecision",),
        "authorize_spec_01_retry": ("ResolveDecision",),
        "request_spec_01_retry": ("RequestAssay",),
        "approve_spec_02": ("RegisterArtefact",),
        "prepare_spec_02": ("RegisterArtefact",),
        "start_spec_02": ("RegisterSpikePlan", "ProposeSpikeExecutionDecision", "ResolveDecision", "StartSpike"),
    }


def test_each_document_service_publishes_only_its_route_kind():
    """Each service names its kind literally (06i storage boundary); the literal must be its route's kind."""

    class Recorder:
        def __init__(self):
            self.kinds = set()

        def revision_exists(self, kind, artefact_id, revision):
            self.kinds.add(kind)
            return False

        def write(self, kind, artefact_id, revision, value):
            self.kinds.add(kind)

        def rollback_new_revision(self, kind, artefact_id, revision, value, *, existed_before):
            self.kinds.add(kind)

    assert set(_REGISTRATION_SERVICES) == {
        "spec_source_document",
        spec_result.DOCUMENT_KIND,
        "spec_operator_brief_document",
        "spec_operator_return_document",
        "spec_operator_partial_return_document",
        "spec_02_live_run_approval_document",
        "spec_02_operator_brief_document",
    }
    for kind, service_type in _REGISTRATION_SERVICES.items():
        service = object.__new__(service_type)
        service.objects, service.document = Recorder(), {"document": kind}
        service._withdraw(
            "art_01978abc-9605-7000-8000-000000009605", service._publish("art_01978abc-9605-7000-8000-000000009605")
        )
        assert service.objects.kinds == {kind}


def _document() -> dict:
    ref = {"event_id": "evt_01978abc-9700-7000-8000-000000009700", "event_hash": "a" * 64, "global_position": 5}
    registration = {"artefact_id": EVIDENCE_IDS[0], "content_sha256": "b" * 64, **ref}
    return {
        "schema_id": spec_result.DOCUMENT_SCHEMA_ID,
        "schema_version": "1.0.0",
        "document_type": spec_result.DOCUMENT_TYPE,
        "intent": register_intent(),
        "recorded_at": "2026-09-10T00:00:00Z",
        "producer_actor_id": OWNER,
        "causal_prefix": {"global_position": 4, "event_hash": "c" * 64, "raw_prefix_sha256": "d" * 64},
        "task": {
            "task_id": c1.TASK_ID,
            "attempt_id": c1.ATTEMPT_ID,
            "acceptance_event": ref,
            "selected_artefact_ids": [EVIDENCE_IDS[0]],
        },
        "candidate": {
            "candidate_id": "obj_01978abc-9702-7000-8000-000000009702",
            "revision": 1,
            "content_sha256": "e" * 64,
            "status": "parked",
        },  # fmt: skip
        "assay": {"assay_id": ASSAY_ID, "status": "reviewed", "version": 5},
        "spike": None,
        "decision": {
            "decision_id": PARK_DECISION_ID,
            "promotion_gate": "assay_to_spike",
            "selected_option": "PARK",
            "deciding_actor_id": OWNER,
            "resolution_event": ref,
        },  # fmt: skip
        "sources": [registration],
        "evidence": [registration],
        "governed_code_subject": {
            "binding_event": ref,
            "event_type": "StoreBindingAdvanced",
            "recovery_binding_sha256": "f" * 64,
            "git_head": "1" * 40,
            "git_tree": "2" * 40,
        },  # fmt: skip
    }


def _attempt() -> dict:
    """A replayed closure Attempt whose start identities differ from the document's store binding."""
    return {
        "dispatch_id": "dsp_01978abc-9703-7000-8000-000000009703",
        "task_revision": 1,
        "start": {
            "context_packet_id": "ctx_01978abc-9704-7000-8000-000000009704",
            "code_identity": "git:sha1:" + "3" * 40,
            "environment_fingerprint": "4" * 64,
        },
    }


def test_the_decision_manifest_lists_its_sources_and_evidence_as_inputs():
    """PR #288 known limit 9: manifest-only provenance names every input the decision cites."""
    document = _document()
    source = {
        **document["sources"][0],
        "artefact_id": "art_01978abc-9701-7000-8000-000000009701",
        "content_sha256": "c" * 64,
    }
    document["sources"] = [source]
    manifest = spec_result._manifest(document, spec_result.subject_id(PROJECT_ID, c1.TASK_ID), _attempt())
    assert manifest["input_dependencies"] == [
        {"input_artefact_id": source["artefact_id"], "input_content_sha256": "c" * 64, "dependency_role": "source"},
        {"input_artefact_id": EVIDENCE_IDS[0], "input_content_sha256": "b" * 64, "dependency_role": "evidence"},
    ]


def test_the_decision_manifest_carries_its_closure_attempts_own_identities():
    """The manifest names the closure Attempt, so its code and environment identities are that Attempt's."""
    document, attempt = _document(), _attempt()
    manifest = spec_result._manifest(document, spec_result.subject_id(PROJECT_ID, c1.TASK_ID), attempt)
    start, subject = attempt["start"], document["governed_code_subject"]
    assert manifest["attempt_id"] == document["task"]["attempt_id"]
    assert manifest["dispatch_id"] == attempt["dispatch_id"]
    assert manifest["code_commit"] == start["code_identity"] != "git:sha1:" + subject["git_head"]
    assert manifest["environment_fingerprint"] == start["environment_fingerprint"] != subject["recovery_binding_sha256"]


def test_project_use_intent_and_document_are_closed_records():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system/schemas")
    schemas.validate(spec_result.INTENT_SCHEMA_ID, register_intent())
    schemas.validate(spec_result.INTENT_SCHEMA_ID, accept_intent())
    for invalid in (
        {**register_intent(), "extra_claim": "unrecognised"},
        {key: value for key, value in register_intent().items() if key != "subset_qualification"},
        {**accept_intent(), "disposition": "reject"},
        {**accept_intent(), "no_spike_reason": "an acceptance names no Spike"},
    ):
        with pytest.raises(SchemaError):
            schemas.validate(spec_result.INTENT_SCHEMA_ID, invalid)
    schemas.validate(spec_result.DOCUMENT_SCHEMA_ID, _document(), schema_version="1.0.0")
    for invalid in (
        {**_document(), "extra_claim": "unrecognised"},
        {**_document(), "evidence": []},
        {**_document(), "decision": {**_document()["decision"], "hash_only": "f" * 64}},
    ):
        with pytest.raises(SchemaError):
            schemas.validate(spec_result.DOCUMENT_SCHEMA_ID, invalid, schema_version="1.0.0")


def test_the_spike_and_disposition_follow_the_owner_decision():
    projection = {"spikes": {"spk_01978abc-9703-7000-8000-000000009703": {"candidate_id": "obj_x", "status": "reviewed",
                                                                          "version": 8}}}  # fmt: skip
    spiked = {"candidate_id": "obj_x", "promotion_gate": "spike_to_preregistration",
              "spike_id": "spk_01978abc-9703-7000-8000-000000009703"}  # fmt: skip
    without_reason = {k: v for k, v in register_intent().items() if k != "no_spike_reason"}
    assert spec_result.spike_record(without_reason, spiked, projection)["version"] == 8
    with pytest.raises(IntegrityError, match="no_spike reason when a Spike"):
        spec_result.spike_record(register_intent(), spiked, projection)
    assay_gate = {"candidate_id": "obj_x", "promotion_gate": "assay_to_spike"}
    assert spec_result.spike_record(register_intent(), assay_gate, projection) is None
    with pytest.raises(IntegrityError, match="explicit no_spike reason"):
        spec_result.spike_record(without_reason, assay_gate, projection)
    with pytest.raises(IntegrityError, match="explicit no_spike reason"):
        spec_result.spike_record(register_intent(), {**assay_gate, "spike_id": spiked["spike_id"]}, projection)
    assert spec_result._PERMITTED_DISPOSITIONS == {
        "PARK": {"retain_experimental_benchmark"},
        "KILL": {"reject"},
        "PROMOTE": {"adopt_default", "retain_experimental_benchmark"},
    }


def test_route_wording_never_promotes_adopts_or_claims_replication_for_park():
    for text in (spec_result._DISPOSITION_TEXT["retain_experimental_benchmark"], spec_result._SUBSET_TEXT):
        assert not any(word in text.lower() for word in FORBIDDEN_ROUTE_WORDS), text
    pending = spec_result.render_markdown(
        {"task_id": c1.TASK_ID, "status": "pending",
         "actions": {"register": {"next_effect": "RegisterArtefact"}, "accept": {"next_effect": "RecordScientificReview"}}}
    )  # fmt: skip
    assert "project-use decision pending" in pending and "Disposition" not in pending


def test_sources_are_the_candidate_cited_registrations_plus_accepted_corrections():
    """Sources follow the ledger only: cited SOURCE registrations whose bytes verify, then 2.0.0 corrections
    whose current replayed use authority is accepted, transitively."""
    from research_system.discovery.spec_source import CORRECTION_SCHEMA, OBSERVATION_SCHEMA, source_ref

    def registered(artefact_id, position, schema_id, version):
        manifest = {
            "content_sha256": f"{position:064x}",
            "artefact_schema_id": schema_id,
            "artefact_schema_version": version,
        }
        return {
            "event_type": "ArtefactRegistered",
            "stream_id": artefact_id,
            "event_id": f"evt_{position}",
            "event_hash": f"{position + 100:064x}",
            "global_position": position,
            "payload": {"manifest": manifest},
        }

    source, chained, correction, unaccepted, legacy, withdrawn = (f"art_source_{name}" for name in "abcdef")
    events = [
        registered(source, 1, OBSERVATION_SCHEMA, "1.0.0"),
        # A correction of a correction, registered first, so inclusion needs a second pass.
        registered(chained, 2, CORRECTION_SCHEMA, "2.0.0"),
        registered(correction, 3, CORRECTION_SCHEMA, "2.0.0"),
        registered(unaccepted, 6, CORRECTION_SCHEMA, "2.0.0"),
        registered(legacy, 7, CORRECTION_SCHEMA, "1.0.0"),
        registered(withdrawn, 9, CORRECTION_SCHEMA, "2.0.0"),
    ]
    accepted = {"use_authority": "accepted_for_scope"}
    # Replayed current use authority. The withdrawn correction was accepted once, then superseded.
    streams = {
        correction: accepted,
        chained: accepted,
        unaccepted: {"use_authority": "candidate"},
        legacy: accepted,
        withdrawn: {"use_authority": "superseded"},
    }
    documents = {
        source: {},
        chained: {"prior_evidence": {"artefact_id": correction}},
        correction: {"prior_evidence": {"artefact_id": source}},
        unaccepted: {"prior_evidence": {"artefact_id": source}},
        withdrawn: {"prior_evidence": {"artefact_id": source}},
    }
    read = []

    def read_source_document(artefact_id):
        read.append(artefact_id)
        return documents[artefact_id], {}

    context = spec_result.RouteContext(
        project_id=PROJECT_ID,
        objects=None,
        schemas=None,
        validator=None,
        raw_prefix_sha256=lambda position: "0" * 64,
        read_source_document=read_source_document,
        check_review_evidence=lambda *args: None,
    )
    candidate = {"source_observation_refs": ["obj_observation"]}
    projection = {
        "source_observations": {
            "obj_observation": {"global_position": 10, "batch": {"raw_source_refs": [source_ref(events[0])]}}
        }
    }
    sources = spec_result._sources(candidate, projection, events, streams, context)
    # Unaccepted, withdrawn and historical 1.0.0 corrections are not sources.
    assert [ref["artefact_id"] for ref in sources] == [source, chained, correction]
    assert source in read, "the cited SOURCE document itself must be read and verified"

    # A cited SOURCE whose bytes do not verify is refused, although its ledger reference is exact.
    def unverifiable(artefact_id):
        if artefact_id == source:
            raise IntegrityError("SOURCE registered manifest and immutable document disagree")
        return documents[artefact_id], {}

    with pytest.raises(IntegrityError, match="immutable document disagree"):
        spec_result._sources(
            candidate, projection, events, streams, replace(context, read_source_document=unverifiable)
        )

    external = {"ref_kind": "external", "locator": "https://example.invalid/paper.pdf", "content_hash": "9" * 64}
    projection["source_observations"]["obj_observation"]["batch"]["raw_source_refs"] = [external]
    with pytest.raises(IntegrityError, match="SOURCE route registration"):
        spec_result._sources(candidate, projection, events, streams, context)


def test_public_project_use_result_is_pending_until_independently_accepted(bound_result, tmp_path, capsys):
    fixture = bound_result
    coordinator, grants = fixture.coordinator, fixture.grants_project_use
    empty = _result(fixture, tmp_path, capsys, "json")
    assert empty["status"] == "pending" and empty["actions"]["register"]["state"] == "not_started"
    assert "project-use decision pending" in _result(fixture, tmp_path, capsys, "markdown")

    # Accept-all: the Task's acceptance selected exactly its registered candidate artefacts.
    task = _streams(coordinator)[c1.TASK_ID]
    assert task["acceptance"]["selected_artefact_ids"] == list(EVIDENCE_IDS)
    registered_hashes = [
        next(e for e in coordinator.ledger.snapshot().events if e["stream_id"] == artefact_id)["payload"]["manifest"][
            "content_sha256"
        ]
        for artefact_id in EVIDENCE_IDS
    ]
    assert task["review_submission"]["candidate_artefact_hashes"] == registered_hashes

    registered = _project_use(fixture, tmp_path, capsys, register_intent(), actor=OWNER, grant=grants["register"])
    assert registered["state"] == "completed" and registered["receipt"]["status"] == "accepted"
    assert _result(fixture, tmp_path, capsys, "json")["status"] == "pending"
    assert "project-use decision pending" in _result(fixture, tmp_path, capsys, "markdown")

    evidence = _review_evidence(fixture)
    reviewed = _project_use(
        fixture, tmp_path, capsys, accept_intent(), actor=REVIEWER, grant=grants["review"], evidence=evidence
    )
    assert reviewed["state"] == "prepared" and reviewed["next_effect"] == "SetArtefactUseAuthority"
    assert _result(fixture, tmp_path, capsys, "json")["status"] == "pending"

    accepted = _project_use(fixture, tmp_path, capsys, accept_intent(), actor=OWNER, grant=grants["use"])
    assert accepted["state"] == "completed" and accepted["receipt"]["status"] == "accepted"

    output = _result(fixture, tmp_path, capsys, "json")
    document = output["project_use_decision"]
    assert output["status"] == "accepted"
    assert document["candidate"]["candidate_id"] == fixture.candidate_id and document["candidate"]["status"] == "parked"
    assert document["decision"] == {
        "decision_id": PARK_DECISION_ID,
        "promotion_gate": "assay_to_spike",
        "selected_option": "PARK",
        "deciding_actor_id": OWNER,
        "resolution_event": document["decision"]["resolution_event"],
    }
    assert document["assay"]["assay_id"] == ASSAY_ID and document["spike"] is None
    assert [ref["artefact_id"] for ref in document["sources"]] == [fixture.source_artefact_id]
    assert [ref["artefact_id"] for ref in document["evidence"]] == list(EVIDENCE_IDS)
    assert document["task"]["selected_artefact_ids"] == list(EVIDENCE_IDS)
    assert document["governed_code_subject"]["git_head"] == coordinator.binding.binding["git_head"]
    # The manifest names the closure Attempt, so it carries that Attempt's own code and environment identities,
    # which here differ from the store binding the document records.
    streams = _streams(coordinator)
    start = streams[c1.ATTEMPT_ID]["start"]
    manifest = next(e for e in coordinator.ledger.snapshot().events if e["stream_id"] == fixture.decision_id)[
        "payload"
    ]["manifest"]
    assert manifest["attempt_id"] == document["task"]["attempt_id"] == c1.ATTEMPT_ID
    subject = document["governed_code_subject"]
    assert manifest["code_commit"] == start["code_identity"] != "git:sha1:" + subject["git_head"]
    assert manifest["environment_fingerprint"] == start["environment_fingerprint"] != subject["recovery_binding_sha256"]
    assert streams[c1.TASK_ID]["current_revision"] == streams[c1.ATTEMPT_ID]["task_revision"]
    assert output["acceptance"]["scientific_review"]["reviewer_actor_id"] == REVIEWER
    assert output["acceptance"]["use_authority"]["actor_id"] == OWNER

    markdown = _result(fixture, tmp_path, capsys, "markdown")
    assert output["disposition_statement"] in markdown and output["subset_statement"] in markdown
    assert "project-use decision pending" not in markdown
    assert not any(word in markdown.lower() for word in FORBIDDEN_ROUTE_WORDS), markdown

    # Exact retries read their committed receipts and append nothing.
    tail = _tail(coordinator)
    for intent, actor, grant, retry_evidence in (
        (register_intent(), OWNER, grants["register"], None),
        (accept_intent(), REVIEWER, grants["review"], evidence),
        (accept_intent(), OWNER, grants["use"], None),
    ):
        retried = _project_use(fixture, tmp_path, capsys, intent, actor=actor, grant=grant, evidence=retry_evidence)
        assert retried["receipt"]["status"] == "accepted" and _tail(coordinator) == tail
    # Changed content for the same Task conflicts and publishes nothing.
    message = _project_use(
        fixture,
        tmp_path,
        capsys,
        register_intent(rationale="A different rationale."),
        actor=OWNER,
        grant=grants["register"],
        refused=True,
    )
    assert "already binds a different decision" in message

    # Unrelated evidence leaves the result unchanged; another Task's result stays isolated.
    unrelated = "art_01978abc-9602-7000-8000-000000009602"
    grant = fixture.grant(OWNER, ("RegisterArtefact",), subject=unrelated)
    submitted = artefact_command(
        command_id=new_id("command"),
        command_type="RegisterArtefact",
        actor_id=OWNER,
        authority_grant_id=grant,
        expected_stream_version=0,
        payload={"new_artefact_id": unrelated, "manifest": {**artefact_manifest(), "artefact_id": unrelated}},
        target_stream_id=unrelated,
    )
    assert coordinator.service.submit(submitted).status == "accepted"
    assert _result(fixture, tmp_path, capsys, "json") == output
    other = _result(fixture, tmp_path, capsys, "json", task_id=c1.OTHER_TASK_ID)
    assert other["status"] == "pending" and "project_use_decision" not in other
    assert other["artefact_id"] != output["artefact_id"]

    listed = coordinator.status()["actions"]
    project_use = [a for a in listed if a.get("action") in {spec_result.REGISTER, spec_result.ACCEPT}]
    assert [(a["action"], a["state"]) for a in project_use] == [
        (spec_result.REGISTER, "completed"),
        (spec_result.ACCEPT, "completed"),
    ]

    # A fresh process replays the same accepted result from ledger evidence alone.
    code = (
        "import sys; from pathlib import Path; from research_system import cli; "
        "cli.canonical_foundation_path=lambda:Path(sys.argv[1]); "
        "raise SystemExit(cli.main(sys.argv[2:]))"
    )
    config = _config(fixture, tmp_path, actor=OWNER, grant=grants["use"])
    replayed = subprocess.run(
        [sys.executable, "-B", "-c", code, str(fixture.bound.fixture.foundation_path), "discovery", "spec", "result",
         "--operator-config", str(config), "--task-id", c1.TASK_ID, "--format", "json"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert json.loads(replayed.stdout) == output


def test_completed_project_use_actions_conflict_unless_the_invocation_repeats_a_committed_effect(
    bound_result, tmp_path, capsys
):
    """A completed action answers only a repeat of a committed effect; anything else conflicts.

    This is the route package's ``changed_command_outcome: conflict_without_publication``.
    """
    fixture = bound_result
    coordinator, grants = fixture.coordinator, fixture.grants_project_use
    evidence = _accept_decision(fixture, tmp_path, capsys)
    tail = _tail(coordinator)

    # The same decision under another grant, and a different review, repeat no committed effect.
    changed = (
        (register_intent(), OWNER, grants["use"], None),
        (accept_intent(), REVIEWER, grants["review"], _review_evidence(fixture)),
    )
    for intent, actor, grant, supplied in changed:
        message = _project_use(
            fixture, tmp_path, capsys, intent, actor=actor, grant=grant, evidence=supplied, refused=True
        )
        assert "already completed" in message, intent["action"]

    # Exact retries of every committed effect are still answered from their receipts.
    for intent, actor, grant, supplied in (
        (register_intent(), OWNER, grants["register"], None),
        (accept_intent(), REVIEWER, grants["review"], evidence),
        (accept_intent(), OWNER, grants["use"], None),
    ):
        retried = _project_use(fixture, tmp_path, capsys, intent, actor=actor, grant=grant, evidence=supplied)
        assert retried["receipt"]["status"] == "accepted" and retried["state"] == "completed"
    assert _tail(coordinator) == tail


def test_project_use_refusals_precede_every_durable_mutation(bound_result, tmp_path, capsys):
    fixture = bound_result
    coordinator, grants = fixture.coordinator, fixture.grants_project_use
    context = coordinator._result_context()
    events = coordinator.ledger.snapshot().events

    # Registration needs an accepted close_task closure: refused at the prefix before TaskAccepted.
    accepted_at = next(e for e in events if e["event_type"] == "TaskAccepted")["global_position"]
    with pytest.raises(IntegrityError, match="exactly one Task closure"):
        spec_result.next_command(
            register_intent(),
            None,
            [event for event in events if event["global_position"] < accepted_at],
            context,
            actor_id=OWNER,
            grant_id=grants["register"],
            now="2026-09-10T00:00:00Z",
        )

    refuse = lambda intent, **kwargs: _project_use(fixture, tmp_path, capsys, intent, refused=True, **kwargs)  # noqa: E731
    owner_register = {"actor": OWNER, "grant": grants["register"]}
    assert "not permitted by a PARK Decision" in refuse(register_intent(disposition="adopt_default"), **owner_register)
    missing_reason = {key: value for key, value in register_intent().items() if key != "no_spike_reason"}
    assert "explicit no_spike reason" in refuse(missing_reason, **owner_register)
    refuse({**register_intent(), "extra_claim": "unrecognised"}, **owner_register)
    # Inherited admission keeps registration owner-only.
    assert "lifecycle_authority_unauthorized" in refuse(
        register_intent(), actor=REVIEWER, grant=grants["reviewer_register"]
    )
    placeholder = {"review_id": new_id("review"), "evidence_refs": [new_id("assurance_record")]}
    assert "requires a registered ProjectUseDecision" in refuse(
        accept_intent(), actor=REVIEWER, grant=grants["review"], evidence=placeholder
    )

    # A process that stopped after publishing the decision bytes, before appending the
    # registration, left them behind. Another decision is refused; the same one reuses them.
    orphaned_at = "2026-01-02T03:04:05Z"
    *_, orphan = spec_result.next_command(
        register_intent(),
        None,
        coordinator.ledger.snapshot().events,
        context,
        actor_id=OWNER,
        grant_id=grants["register"],
        now=orphaned_at,
    )
    coordinator.objects.write(spec_result.DOCUMENT_KIND, fixture.decision_id, 1, orphan)
    assert "already binds a different decision" in refuse(
        register_intent(rationale="A different rationale."), **owner_register
    )
    registered = _project_use(fixture, tmp_path, capsys, register_intent(), **owner_register)
    assert registered["state"] == "completed" and registered["receipt"]["status"] == "accepted"
    registration = next(e for e in coordinator.ledger.snapshot().events if e["stream_id"] == fixture.decision_id)
    assert registration["payload"]["manifest"]["created_at"] == orphaned_at

    # The producer cannot review its own decision, and review evidence must be exact.
    self_review = _review_evidence(fixture, reviewer=OWNER)
    assert "independent of the registering producer" in refuse(
        accept_intent(), actor=OWNER, grant=grants["owner_review"], evidence=self_review
    )
    assert "fields are not exact" in refuse(
        accept_intent(), actor=REVIEWER, grant=grants["review"], evidence={"review_id": new_id("review")}
    )
    # Evidence that could never govern use authority is refused before the one review is recorded.
    ungoverning = (
        {"review_id": new_id("review"), "evidence_refs": [new_id("assurance_record")]},
        {**_review_evidence(fixture), "review_id": new_id("review")},
        {"review_id": new_id("review"), "evidence_refs": []},
    )
    for evidence in ungoverning:
        assert "would not govern use authority" in refuse(
            accept_intent(), actor=REVIEWER, grant=grants["review"], evidence=evidence
        )
    _project_use(
        fixture,
        tmp_path,
        capsys,
        accept_intent(),
        actor=REVIEWER,
        grant=grants["review"],
        evidence=_review_evidence(fixture),
    )
    # Use authority may not reuse the registration grant, and takes no evidence.
    assert "separate actor and grant" in refuse(accept_intent(), **owner_register)
    assert "takes no independent evidence" in refuse(
        accept_intent(), actor=OWNER, grant=grants["use"], evidence=placeholder
    )
    assert coordinator.status(accept_intent())["state"] == "prepared"

    # Decisive controls: on a throwaway artefact, inherited admission accepts the inputs refused above.
    for subject in (
        "art_01978abc-9603-7000-8000-000000009603",
        "art_01978abc-9604-7000-8000-000000009604",
        "art_01978abc-9606-7000-8000-000000009606",
    ):
        shared = fixture.grant(OWNER, ("RegisterArtefact", "SetArtefactUseAuthority"), subject=subject)
        body = {**artefact_manifest(), "artefact_id": subject, "producer_actor_id": OWNER}
        assert coordinator.service.submit(
            artefact_command(command_id=new_id("command"), command_type="RegisterArtefact", actor_id=OWNER,
                             authority_grant_id=shared, expected_stream_version=0,
                             payload={"new_artefact_id": subject, "manifest": body}, target_stream_id=subject)
        ).status == "accepted"  # fmt: skip
        subject_hash = body["content_sha256"]
        if subject.endswith("9603"):
            evidence = _review_evidence(fixture, reviewer=OWNER, subject=subject)
            owner_review = fixture.grant(OWNER, ("RecordScientificReview",), subject=subject)
            payload = {
                "artefact_id": subject,
                "subject_sha256": subject_hash,
                "scientific_review": "approved",
                **evidence,
            }
            receipt = coordinator.service.submit(
                artefact_command(command_id=new_id("command"), command_type="RecordScientificReview", actor_id=OWNER,
                                 authority_grant_id=owner_review, expected_stream_version=1, payload=payload,
                                 target_stream_id=subject)
            )  # fmt: skip
            assert receipt.status == "accepted", "admission is expected to accept a producer self-review"
        elif subject.endswith("9606"):
            reviewer = fixture.grant(REVIEWER, ("RecordScientificReview",), agent=True, subject=subject)
            payload = {
                "artefact_id": subject,
                "subject_sha256": subject_hash,
                "scientific_review": "approved",
                "review_id": new_id("review"),
                "evidence_refs": [new_id("assurance_record")],
            }
            receipt = coordinator.service.submit(
                artefact_command(command_id=new_id("command"), command_type="RecordScientificReview",
                                 actor_id=REVIEWER, authority_grant_id=reviewer, expected_stream_version=1,
                                 payload=payload, target_stream_id=subject)
            )  # fmt: skip
            assert receipt.status == "accepted", "admission is expected to record evidence that cannot govern use"
        else:
            evidence = _review_evidence(fixture, subject=subject)
            reviewer = fixture.grant(REVIEWER, ("RecordScientificReview",), agent=True, subject=subject)
            payload = {
                "artefact_id": subject,
                "subject_sha256": subject_hash,
                "scientific_review": "approved",
                **evidence,
            }
            assert coordinator.service.submit(
                artefact_command(command_id=new_id("command"), command_type="RecordScientificReview",
                                 actor_id=REVIEWER, authority_grant_id=reviewer, expected_stream_version=1,
                                 payload=payload, target_stream_id=subject)
            ).status == "accepted"  # fmt: skip
            use = {
                "artefact_id": subject,
                "subject_sha256": subject_hash,
                "use_authority": "accepted_for_scope",
                "consumer_predicate": spec_result._result_predicate(),
                "evidence_refs": [evidence["review_id"], *evidence["evidence_refs"]],
            }
            receipt = coordinator.service.submit(
                artefact_command(command_id=new_id("command"), command_type="SetArtefactUseAuthority",
                                 actor_id=OWNER, authority_grant_id=shared, expected_stream_version=2,
                                 payload=use, target_stream_id=subject)
            )  # fmt: skip
            assert receipt.status == "accepted", "admission is expected to accept use authority under the same grant"


def test_a_decision_is_refused_for_a_task_amended_after_its_attempts_dispatch(bound_amended_result, tmp_path, capsys):
    """The closure Attempt ran the revision it was dispatched on, so an amended Task cannot lend it another."""
    fixture = bound_amended_result
    coordinator, grants = fixture.coordinator, fixture.grants_project_use
    streams = _streams(coordinator)
    task, attempt = streams[c1.TASK_ID], streams[c1.ATTEMPT_ID]
    assert (task["status"], task["current_revision"], attempt["task_revision"]) == ("accepted", 2, 1)
    # The accepted Task's current definition still names the Candidate, so the Candidate match cannot refuse.
    assert fixture.candidate_id in task["definition"]["portfolio_refs"]

    message = _project_use(
        fixture, tmp_path, capsys, register_intent(), actor=OWNER, grant=grants["register"], refused=True
    )
    assert "unamended since its Attempt's dispatch" in message, message
    assert not coordinator.objects.revision_exists(spec_result.DOCUMENT_KIND, fixture.decision_id, 1)
    assert coordinator.status(register_intent())["state"] == "not_started"


def test_project_use_registration_refuses_a_ledger_that_moved_after_derivation(
    bound_result, tmp_path, capsys, monkeypatch
):
    """The decision is derived before admission's writer lock; inside the lock a moved ledger refuses it."""
    fixture = bound_result
    coordinator, grants = fixture.coordinator, fixture.grants_project_use
    derive, moved = spec_result.next_command, []

    def derive_then_foreign_append(*args, **kwargs):
        built = derive(*args, **kwargs)
        # Another writer appends to an unrelated stream after the decision is derived, before the lock.
        fixture.grant(REVIEWER, ("RecordScientificReview",), agent=True, subject=new_id("artefact"))
        moved.append(coordinator.ledger.snapshot())
        return built

    intent_path = tmp_path / "moved-intent.json"
    intent_path.write_bytes(canonical_bytes(register_intent()))
    config = _config(fixture, tmp_path, actor=OWNER, grant=grants["register"])
    args = ["discovery", "spec", "advance", "--operator-config", str(config)]
    before = coordinator.ledger.snapshot()
    with monkeypatch.context() as patched:
        patched.setattr(spec_result, "next_command", derive_then_foreign_append)
        code = cli.main([*args, "--action", spec_result.REGISTER, "--input", str(intent_path)])
    captured = capsys.readouterr()
    assert code == 1, captured.out
    assert "moved past" in captured.err and "nothing was published" in captured.err, captured.err
    [appended] = moved
    after = coordinator.ledger.snapshot()
    assert after.global_position > before.global_position
    assert (after.global_position, after.event_hash) == (appended.global_position, appended.event_hash)
    assert not coordinator.objects.revision_exists(spec_result.DOCUMENT_KIND, fixture.decision_id, 1)
    assert coordinator.status(register_intent())["state"] == "not_started"

    # Derived again from the moved ledger, the same invocation registers.
    registered = _project_use(fixture, tmp_path, capsys, register_intent(), actor=OWNER, grant=grants["register"])
    assert registered["state"] == "completed" and registered["receipt"]["status"] == "accepted"


class _Documents:
    """Object store that serves chosen decision documents and delegates everything else."""

    def __init__(self, real, documents):
        self.real, self.documents = real, documents

    def revision_exists(self, kind, artefact_id, revision):
        if kind == spec_result.DOCUMENT_KIND:
            return artefact_id in self.documents
        return self.real.revision_exists(kind, artefact_id, revision)

    def read(self, kind, artefact_id, revision):
        if kind == spec_result.DOCUMENT_KIND:
            return deepcopy(self.documents[artefact_id])
        return self.real.read(kind, artefact_id, revision)


def _rebind(events, fixture, document):
    """Rewrite the registration so it carries the route's own key over a manifest for ``document``."""
    events = deepcopy(events)
    registration = next(e for e in events if e["stream_id"] == fixture.decision_id)
    raw = canonical_bytes(document)
    digest = sha256_hex(raw)
    registration["payload"]["manifest"].update(
        content_sha256=digest,
        size_bytes=len(raw),
        relative_path=f"objects/{spec_result.DOCUMENT_KIND}/{fixture.decision_id}/00000001-{digest}.json",
    )
    key = spec_result.retry_key(
        register_intent(),
        "RegisterArtefact",
        registration["actor_id"],
        registration["authority_grant_id"],
        registration["payload"],
    )
    registration.update(idempotency_key=key, command_id=_stable_command_id(key))
    return [e for e in events if e["global_position"] <= registration["global_position"]]


def test_foreign_hash_only_misbound_and_unrecognised_decision_evidence_is_rejected(bound_result, tmp_path, capsys):
    fixture = bound_result
    coordinator = fixture.coordinator
    _accept_decision(fixture, tmp_path, capsys)
    events = coordinator.ledger.snapshot().events
    context = coordinator._result_context()
    document = coordinator.objects.read(spec_result.DOCUMENT_KIND, fixture.decision_id, 1)
    stream = [e for e in events if e["stream_id"] == fixture.decision_id]
    registration_prefix = [e for e in events if e["global_position"] <= stream[0]["global_position"]]

    def evaluate(candidate_events, documents=None, action=spec_result.REGISTER):
        ctx = context if documents is None else replace(context, objects=_Documents(coordinator.objects, documents))
        return spec_result.evaluate(action, c1.TASK_ID, candidate_events, ctx)

    assert evaluate(registration_prefix)["state"] == "completed"
    # Identity: a registration carrying any other key was not issued by this route.
    foreign = deepcopy(registration_prefix)
    foreign[-1]["idempotency_key"] = "spec:" + "0" * 64
    with pytest.raises(ConflictError, match="did not issue"):
        evaluate(foreign)
    # Hash-only: a correctly keyed registration whose document bytes are absent.
    with pytest.raises(IntegrityError, match="bytes are absent"):
        evaluate(registration_prefix, documents={})
    # Wrong binding: exact bytes and key, but a reference the ledger does not support.
    misbound = deepcopy(document)
    misbound["evidence"] = misbound["evidence"][:1]
    with pytest.raises(IntegrityError, match="does not carry the decision this route derives"):
        evaluate(_rebind(events, fixture, misbound), documents={fixture.decision_id: misbound})
    # Unrecognised field: the closed record rejects it before any derivation.
    extended = {**document, "extra_claim": "unrecognised"}
    with pytest.raises(SchemaError):
        evaluate(_rebind(events, fixture, extended), documents={fixture.decision_id: extended})
    # Exclusivity: anything else on the decision's stream conflicts.
    extra = deepcopy(stream[-1])
    extra.update(event_id=new_id("event"), global_position=events[-1]["global_position"] + 1)
    with pytest.raises(ConflictError, match="did not issue"):
        evaluate([*events, extra], action=spec_result.ACCEPT)
    # Independence: a correctly keyed review by the registering producer is not acceptance.
    self_reviewed = [deepcopy(e) for e in events if e["global_position"] <= stream[1]["global_position"]]
    review = next(e for e in self_reviewed if e["event_id"] == stream[1]["event_id"])
    review.update(actor_id=stream[0]["actor_id"])
    key = spec_result.retry_key(
        accept_intent(), "RecordScientificReview", review["actor_id"], review["authority_grant_id"], review["payload"]
    )
    review.update(idempotency_key=key, command_id=_stable_command_id(key))
    with pytest.raises(IntegrityError, match="not independent of the registering producer"):
        evaluate(self_reviewed, action=spec_result.ACCEPT)
    # None of the in-memory tampering touched the real ledger, which still reads as accepted.
    assert coordinator.status(accept_intent())["state"] == "completed"
