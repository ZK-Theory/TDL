from __future__ import annotations

from copy import deepcopy

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.projection.replay import replay
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import (
    ACTORS,
    REPO_ROOT,
    activate_lifecycle_grant,
    control_plane,
    scoped_lifecycle_grant_id,
)
from tests.research_system.integration.test_wp6_1_c1_readiness_lease import (
    ATTEMPT_ID,
    TASK_ID,
    _c1_command,
    _c1_control_plane,
    _command_id,
    _seed_running_attempt,
)
from tests.research_system.integration.test_wp6_1_task_scope_lifecycle import (
    SCOPE_A,
    TASK_A,
    _command,
    _scope_create_payload,
    _task_definition,
)


NON_P6_C3_COMMAND_EVENTS = {
    "CompleteScope": "ScopeCompleted",
    "AcceptTask": "TaskAccepted",
    "RejectTask": "TaskRejected",
    "ClosePartial": "PartialOutcomeRecorded",
    "ReopenTask": "TaskReopened",
    "AssignReview": "ReviewAssigned",
    "StartReview": "ReviewStarted",
    "RecordReviewVerdict": "ReviewVerdictRecorded",
    "RequestReviewChanges": "ReviewChangesRequested",
    "SatisfyReview": "ReviewSatisfied",
    "WithdrawReview": "ReviewWithdrawn",
    "SupersedeReview": "ReviewSuperseded",
    "ProposeDecision": "DecisionProposed",
    "RequestDecisionReview": "DecisionReviewRequested",
    "ResolveDecision": "DecisionResolved",
    "RejectDecision": "DecisionRejected",
    "ExpireDecision": "DecisionExpired",
    "SupersedeDecision": "DecisionSuperseded",
    "RecordRuleEvaluation": "RuleEvaluationRecorded",
    "AmendDecision": "DecisionAmendmentProposed",
    "RecordCorrection": "RecordCorrected",
}

TASK_PARTIAL = "tsk_01978abc-6330-7000-8000-000000006330"
TASK_REVIEW = "tsk_01978abc-6400-7000-8000-000000006400"
REVIEW_IDS = tuple(f"rev_01978abc-64{index:02d}-7000-8000-0000000064{index:02d}" for index in range(1, 6))
ACTOR_C = "act_01978abc-6600-7000-8000-000000006600"
DECISION_IDS = tuple(f"dec_01978abc-66{index:02d}-7000-8000-0000000066{index:02d}" for index in range(1, 6))
DECISION_REVIEW_ID = "rev_01978abc-6611-7000-8000-000000006611"
RULE_EVALUATION_ID = "val_01978abc-6620-7000-8000-000000006620"


def test_non_p6_c3_runtime_bindings_are_literal():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    for command_type, event_type in NON_P6_C3_COMMAND_EVENTS.items():
        command = schemas.command_binding(command_type)
        event = schemas.event_binding(event_type, command_type)
        assert command is not None, command_type
        assert event is not None, (command_type, event_type)
        assert command.schema_id == f"ars://core/command/{command_type}"
        assert event.schema_id == f"ars://core/event/{event_type}"


def test_complete_scope_is_public_durable_idempotent_and_replayable(tmp_path):
    harness = _c1_control_plane(tmp_path)
    review_id = "rev_01978abc-6301-7000-8000-000000006301"
    task_hash = _task_to_review_pending(harness, review_id, 6301)
    _request_review(harness, review_id, 6303, task_hash, subject_id=TASK_ID)
    _record_review_verdict(harness, review_id, task_hash, 6304, "approve")
    _submit_review_command(
        harness,
        6307,
        "SatisfyReview",
        review_id,
        {
            "review_id": review_id,
            "prior_review_state": "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:scope-member-review"],
            "satisfaction_gate": "scope-member-acceptance-gate",
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    accepted = _c1_command(
        _command_id(6308),
        "AcceptTask",
        TASK_ID,
        harness.ledger.snapshot().stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "task_revision": task["current_revision"],
            "satisfied_review_ids": [review_id],
            "satisfied_acceptance_criteria": list(task["definition"]["acceptance_criteria"]),
            "selected_artefact_ids": [],
        },
    )
    assert harness.service.submit(accepted).status == "accepted"
    scope_payload = _scope_create_payload(SCOPE_A, completion="all required members accepted")
    scope_payload["members"][0]["member_id"] = TASK_ID
    created = _command(
        "cmd_01978abc-6311-7000-8000-000000006311",
        "CreateScopeDefinition",
        SCOPE_A,
        0,
        scope_payload,
    )
    assert harness.service.submit(created).status == "accepted"

    command = _command(
        "cmd_01978abc-6312-7000-8000-000000006312",
        "CompleteScope",
        SCOPE_A,
        1,
        {
            "scope_definition_id": SCOPE_A,
            "revision": 1,
            "member_dispositions": [
                {
                    "member_id": TASK_ID,
                    "member_kind": "task",
                    "disposition": "accepted",
                    "completion_evidence_ref": "evidence:task-a-accepted",
                }
            ],
            "completion_predicate": "all required members accepted",
            "completion_evidence_refs": ["evidence:scope-a-complete"],
        },
    )

    first = harness.service.submit(command)
    second = harness.service.submit(command)

    assert first.status == "accepted", first
    assert second == first
    assert harness.receipts.load(str(command["command_id"])) == first
    events = tuple(harness.ledger.iter_events())
    assert [event["event_type"] for event in events[-2:]] == [
        "ScopeDefinitionCreated",
        "ScopeCompleted",
    ]
    completed = events[-1]
    binding = harness.schemas.command_binding("CompleteScope")
    assert binding is not None
    identity = harness.schemas.resolve_identity(binding.schema_id, binding.schema_version)
    assert completed["payload"] == command["payload"]
    assert (
        completed["command_schema_id"],
        completed["command_schema_version"],
        completed["command_schema_sha256"],
    ) == (identity.schema_id, identity.schema_version, identity.raw_bytes_sha256)

    projected = replay(events, schema_registry=harness.schemas)["streams"][SCOPE_A]
    assert projected["status"] == "complete"
    assert projected["completion"]["revision"] == 1
    assert projected["completion"]["member_dispositions"] == command["payload"]["member_dispositions"]


@pytest.mark.parametrize(
    ("mutation", "reason_code"),
    [
        (
            lambda command: command["payload"].update({"revision": 2}),
            "stale_scope_revision",
        ),
        (
            lambda command: command["payload"].update({"completion_predicate": "only the visible subset is complete"}),
            "scope_completion_predicate_mismatch",
        ),
        (
            lambda command: command["payload"].update({"member_dispositions": []}),
            "missing_scope_member_disposition",
        ),
    ],
)
def test_complete_scope_rejects_invalid_completion_without_ledger_side_effects(
    tmp_path,
    mutation,
    reason_code,
):
    harness = control_plane(tmp_path)
    created = _command(
        "cmd_01978abc-6321-7000-8000-000000006321",
        "CreateScopeDefinition",
        SCOPE_A,
        0,
        _scope_create_payload(SCOPE_A, completion="all required members accepted"),
    )
    assert harness.service.submit(created).status == "accepted"
    command = _command(
        "cmd_01978abc-6322-7000-8000-000000006322",
        "CompleteScope",
        SCOPE_A,
        1,
        {
            "scope_definition_id": SCOPE_A,
            "revision": 1,
            "member_dispositions": [
                {
                    "member_id": TASK_A,
                    "member_kind": "task",
                    "disposition": "accepted",
                    "completion_evidence_ref": "evidence:task-a-accepted",
                }
            ],
            "completion_predicate": "all required members accepted",
            "completion_evidence_refs": ["evidence:scope-a-complete"],
        },
    )
    invalid = deepcopy(command)
    mutation(invalid)
    before = tuple(harness.ledger.iter_events())

    receipt = harness.service.submit(invalid)

    assert receipt.status == "rejected"
    assert receipt.reason_code == reason_code
    assert tuple(harness.ledger.iter_events()) == before
    projected = replay(before, schema_registry=harness.schemas)["streams"][SCOPE_A]
    assert projected["status"] == "open"


def test_complete_scope_rejects_an_unresolved_member_without_ledger_side_effects(tmp_path):
    harness = control_plane(tmp_path)
    created = _command(
        "cmd_01978abc-6323-7000-8000-000000006323",
        "CreateScopeDefinition",
        SCOPE_A,
        0,
        _scope_create_payload(SCOPE_A, completion="all required members accepted"),
    )
    assert harness.service.submit(created).status == "accepted"
    command = _command(
        "cmd_01978abc-6324-7000-8000-000000006324",
        "CompleteScope",
        SCOPE_A,
        1,
        {
            "scope_definition_id": SCOPE_A,
            "revision": 1,
            "member_dispositions": [
                {
                    "member_id": TASK_A,
                    "member_kind": "task",
                    "disposition": "accepted",
                    "completion_evidence_ref": "evidence:claimed-task-a-acceptance",
                }
            ],
            "completion_predicate": "all required members accepted",
            "completion_evidence_refs": ["evidence:scope-a-complete"],
        },
    )
    before = tuple(harness.ledger.iter_events())

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "scope_member_not_resolved"
    assert tuple(harness.ledger.iter_events()) == before


def _create_task(harness, task_id: str, command_id: str) -> None:
    command = _command(
        command_id,
        "CreateTask",
        task_id,
        0,
        {
            "new_task_id": task_id,
            "definition": _task_definition(task_id, f"C3 task {task_id}", 1),
        },
    )
    assert harness.service.submit(command).status == "accepted"


def _terminal_ref(harness) -> dict[str, str]:
    event = tuple(harness.ledger.iter_events())[-1]
    return {"record_id": event["event_id"], "content_sha256": event["event_hash"]}


def test_close_partial_and_reopen_preserve_the_terminal_event_and_start_a_new_epoch(tmp_path):
    harness = control_plane(tmp_path)
    _create_task(harness, TASK_PARTIAL, "cmd_01978abc-6331-7000-8000-000000006331")
    partial = _command(
        "cmd_01978abc-6332-7000-8000-000000006332",
        "ClosePartial",
        TASK_PARTIAL,
        1,
        {
            "task_id": TASK_PARTIAL,
            "unmet_obligations": ["independent review remains"],
            "claim_restrictions": ["no completion claim"],
            "completed_obligations": ["bounded implementation"],
            "accepted_artefact_ids": [],
            "resume_policy": "new execution epoch after owner authority",
        },
    )
    assert harness.service.submit(partial).status == "accepted"
    terminal_ref = _terminal_ref(harness)
    reopen = _command(
        "cmd_01978abc-6333-7000-8000-000000006333",
        "ReopenTask",
        TASK_PARTIAL,
        2,
        {
            "task_id": TASK_PARTIAL,
            "prior_terminal_status": "partial",
            "new_execution_epoch": 2,
            "reopen_reason": "resume the unmet reviewed obligations",
            "preserved_terminal_record_ref": terminal_ref,
            "authority_evidence_refs": ["authority:reopen-partial"],
        },
    )

    receipt = harness.service.submit(reopen)

    assert receipt.status == "accepted", receipt
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_PARTIAL]
    assert task["status"] == "readiness_pending"
    assert task["execution_epoch"] == 2
    assert task["preserved_terminal_records"][-1] == {
        "event_id": terminal_ref["record_id"],
        "event_hash": terminal_ref["content_sha256"],
    }


def test_cancelled_task_reopens_only_from_its_exact_terminal_event(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before_attempt = harness.ledger.snapshot()
    completed_attempt = _c1_command(
        _command_id(6341),
        "CompleteAttempt",
        ATTEMPT_ID,
        before_attempt.stream_versions[ATTEMPT_ID],
        {
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": [],
            "end_evidence_refs": ["evidence:bounded-cancellation"],
            "output_disposition": "no_candidate_output",
        },
    )
    assert harness.service.submit(completed_attempt).status == "accepted"
    before_cancel = harness.ledger.snapshot()
    cancelled = _c1_command(
        _command_id(6342),
        "CancelTask",
        TASK_ID,
        before_cancel.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "cancellation_reason": "bounded cancellation after the attempt terminated",
            "process_disposition": {
                "process_state": "stopped",
                "children_closed": True,
                "writers_closed": True,
                "evidence_refs": ["evidence:process-stopped"],
            },
            "active_attempt_dispositions": [ATTEMPT_ID],
        },
    )
    assert harness.service.submit(cancelled).status == "accepted"
    terminal_ref = _terminal_ref(harness)
    reopen = _c1_command(
        _command_id(6343),
        "ReopenTask",
        TASK_ID,
        before_cancel.stream_versions[TASK_ID] + 1,
        {
            "task_id": TASK_ID,
            "prior_terminal_status": "cancelled",
            "new_execution_epoch": 2,
            "reopen_reason": "owner restored the cancelled work",
            "preserved_terminal_record_ref": terminal_ref,
            "authority_evidence_refs": ["authority:reopen-cancelled"],
        },
    )

    receipt = harness.service.submit(reopen)

    assert receipt.status == "accepted", receipt
    events = tuple(harness.ledger.iter_events())
    assert [event["event_type"] for event in events[-2:]] == ["TaskCancelled", "TaskReopened"]
    assert replay(events, schema_registry=harness.schemas)["streams"][TASK_ID]["status"] == "readiness_pending"


def _request_review(
    harness,
    review_id: str,
    number: int,
    subject_hash: str,
    *,
    subject_id: str = TASK_REVIEW,
) -> None:
    request = _command(
        f"cmd_01978abc-{number:04d}-7000-8000-00000000{number:04d}",
        "RequestReview",
        review_id,
        0,
        {
            "new_review_id": review_id,
            "review_type": "software",
            "subject_ids": [subject_id],
            "subject_hashes": [subject_hash],
            "governing_refs": ["plan:06o", "catalogue:06d"],
            "review_questions": ["Does the exact C3 subject satisfy its bounded contract?"],
            "required_evidence_refs": ["evidence:c3-review-subject"],
            "required_lanes": ["software", "provenance"],
            "reviewer_capability": ["python", "event-sourcing"],
            "required_independence_grade": "independent_exact_subject",
            "visibility_policy": "owner_and_reviewer",
            "allowed_verdicts": ["accept_exact_subject", "rework_required"],
            "satisfaction_authority": "owner",
            "deadline": "2026-08-10T12:00:00Z",
            "escalation_rule": "return rework_required on any material mismatch",
        },
    )
    receipt = harness.service.submit(request)
    assert receipt.status == "accepted", receipt


def _reviewer_grant(harness, review_id: str, number: int) -> str:
    return activate_lifecycle_grant(
        harness,
        subject_kind="review",
        subject_id=review_id,
        actor_id=ACTORS["actor-b"],
        allowed_actor_classes=("agent",),
        command_types=("StartReview", "RecordReviewVerdict"),
        grant_id=f"agr_01978abc-74{number:02d}-7000-8000-0000000074{number:02d}",
    )


def _submit_review_command(
    harness,
    number: int,
    command_type: str,
    review_id: str,
    payload: dict,
    *,
    actor_id: str | None = None,
    authority_grant_id: str | None = None,
):
    version = harness.ledger.snapshot().stream_versions.get(review_id, 0)
    command = _command(
        f"cmd_01978abc-{number:04d}-7000-8000-00000000{number:04d}",
        command_type,
        review_id,
        version,
        payload,
    )
    if actor_id is not None:
        command["actor_id"] = actor_id
    if authority_grant_id is not None:
        command["authority_grant_id"] = authority_grant_id
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    return command


def _review_condition() -> dict[str, object]:
    return {
        "condition_text": "close the exact bounded finding",
        "gate_disposition": "blocking",
        "owner_actor_id": ACTORS["actor-a"],
        "policy_id": "pol_01978abc-6400-7000-8000-000000006400",
        "evidence_refs": ["evidence:condition"],
    }


def test_review_lifecycle_preserves_independence_and_both_satisfaction_discriminants(tmp_path):
    harness = control_plane(tmp_path)
    _create_task(harness, TASK_REVIEW, "cmd_01978abc-6400-7000-8000-000000006400")
    subject = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_REVIEW]
    subject_hash = sha256_hex(canonical_bytes(subject))
    for offset, review_id in enumerate(REVIEW_IDS, start=1):
        _request_review(harness, review_id, 6400 + offset, subject_hash)

    for offset, review_id in enumerate(REVIEW_IDS[:2], start=1):
        reviewer_grant = _reviewer_grant(harness, review_id, offset)
        _submit_review_command(
            harness,
            6410 + offset,
            "AssignReview",
            review_id,
            {
                "review_id": review_id,
                "reviewer_actor_id": ACTORS["actor-b"],
                "computed_independence_grade": "I2",
                "independence_evidence_refs": [f"evidence:independent:{review_id}"],
            },
        )
        _submit_review_command(
            harness,
            6420 + offset,
            "StartReview",
            review_id,
            {
                "review_id": review_id,
                "unchanged_subject_sha256": subject_hash,
                "visibility_policy": "owner_and_reviewer",
            },
            actor_id=ACTORS["actor-b"],
            authority_grant_id=reviewer_grant,
        )
        changed = offset == 2
        _submit_review_command(
            harness,
            6430 + offset,
            "RecordReviewVerdict",
            review_id,
            {
                "review_id": review_id,
                "verdict": "changes_requested" if changed else "approve",
                "findings": ["bounded finding"] if changed else [],
                "reviewer_actor_id": ACTORS["actor-b"],
                "required_evidence_refs": ["evidence:review-verdict"],
                "limitations": [],
                "conditions": [_review_condition()] if changed else [],
                "reviewer_profile": "independent-reviewer",
                "reviewer_session": "session:c3-review",
                "reviewer_model_metadata": "model:independent",
                "context_manifest_id": "ctx_01978abc-6400-7000-8000-000000006400",
                "context_manifest_sha256": "a" * 64,
                "unchanged_subject_sha256": subject_hash,
                "producing_attempt_id": "att_01978abc-6400-7000-8000-000000006400",
                "trace_visibility_evidence_refs": ["evidence:trace-visibility"],
                "computed_independence_grade": "I2",
            },
            actor_id=ACTORS["actor-b"],
            authority_grant_id=reviewer_grant,
        )
        if changed:
            _submit_review_command(
                harness,
                6440 + offset,
                "RequestReviewChanges",
                review_id,
                {
                    "review_id": review_id,
                    "policy_evaluation_refs": ["policy-evaluation:changes"],
                    "conditions": [_review_condition()],
                },
            )
        satisfaction = {
            "review_id": review_id,
            "prior_review_state": "changes_requested" if changed else "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:satisfied"],
            "satisfaction_gate": "exact-review-gate",
        }
        if changed:
            satisfaction["unchanged_subject_sha256"] = subject_hash
        _submit_review_command(harness, 6450 + offset, "SatisfyReview", review_id, satisfaction)

    _submit_review_command(
        harness,
        6461,
        "WithdrawReview",
        REVIEW_IDS[2],
        {"review_id": REVIEW_IDS[2], "withdrawal_reason": "requester withdrew the bounded subject"},
    )
    _submit_review_command(
        harness,
        6462,
        "SupersedeReview",
        REVIEW_IDS[3],
        {
            "review_id": REVIEW_IDS[3],
            "replacement_review_id": REVIEW_IDS[4],
            "unchanged_subject_sha256": subject_hash,
            "continuing_gate_disposition": "replacement review owns the same gate",
        },
    )

    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert [projection["streams"][review_id]["status"] for review_id in REVIEW_IDS] == [
        "satisfied",
        "satisfied",
        "withdrawn",
        "superseded",
        "requested",
    ]
    assert "decision_id" not in projection["streams"][REVIEW_IDS[0]]


def test_satisfy_changed_review_rejects_unrelated_subject_hash_without_append(tmp_path):
    harness = control_plane(tmp_path)
    review_id = "rev_01978abc-6456-7000-8000-000000006456"
    _create_task(harness, TASK_REVIEW, "cmd_01978abc-6455-7000-8000-000000006455")
    subject = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_REVIEW]
    subject_hash = sha256_hex(canonical_bytes(subject))
    _request_review(harness, review_id, 6456, subject_hash)
    _record_review_verdict(harness, review_id, subject_hash, 6457, "changes_requested")
    _submit_review_command(
        harness,
        6460,
        "RequestReviewChanges",
        review_id,
        {
            "review_id": review_id,
            "policy_evaluation_refs": ["policy-evaluation:changes"],
            "conditions": [_review_condition()],
        },
    )
    command = _command(
        "cmd_01978abc-6461-7000-8000-000000006461",
        "SatisfyReview",
        review_id,
        harness.ledger.snapshot().stream_versions[review_id],
        {
            "review_id": review_id,
            "prior_review_state": "changes_requested",
            "policy_evaluation_refs": ["policy-evaluation:satisfied"],
            "satisfaction_gate": "exact-review-gate",
            "unchanged_subject_sha256": "b" * 64,
        },
    )
    before = tuple(harness.ledger.iter_events())

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "review_satisfaction_precondition_failed"
    assert tuple(harness.ledger.iter_events()) == before


def _task_to_review_pending(harness, review_id: str, number: int) -> str:
    _seed_running_attempt(harness)
    before_attempt = harness.ledger.snapshot()
    completed = _c1_command(
        _command_id(number),
        "CompleteAttempt",
        ATTEMPT_ID,
        before_attempt.stream_versions[ATTEMPT_ID],
        {
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": [],
            "end_evidence_refs": ["evidence:c3-task-review"],
            "output_disposition": "no_candidate_output",
        },
    )
    assert harness.service.submit(completed).status == "accepted"
    before_task = harness.ledger.snapshot()
    submitted = _c1_command(
        _command_id(number + 1),
        "SubmitForReview",
        TASK_ID,
        before_task.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": [],
            "attempt_outcome": "completed",
            "candidate_artefact_hashes": [],
            "requested_review_ids": [review_id],
        },
    )
    assert harness.service.submit(submitted).status == "accepted"
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert task["status"] == "review_pending"
    return sha256_hex(canonical_bytes(task))


def _record_review_verdict(
    harness,
    review_id: str,
    subject_hash: str,
    number: int,
    verdict: str,
) -> None:
    reviewer_grant = _reviewer_grant(harness, review_id, number % 100)
    _submit_review_command(
        harness,
        number,
        "AssignReview",
        review_id,
        {
            "review_id": review_id,
            "reviewer_actor_id": ACTORS["actor-b"],
            "computed_independence_grade": "I2",
            "independence_evidence_refs": ["evidence:task-review-independence"],
        },
    )
    _submit_review_command(
        harness,
        number + 1,
        "StartReview",
        review_id,
        {
            "review_id": review_id,
            "unchanged_subject_sha256": subject_hash,
            "visibility_policy": "owner_and_reviewer",
        },
        actor_id=ACTORS["actor-b"],
        authority_grant_id=reviewer_grant,
    )
    _submit_review_command(
        harness,
        number + 2,
        "RecordReviewVerdict",
        review_id,
        {
            "review_id": review_id,
            "verdict": verdict,
            "findings": ["task evidence is insufficient"] if verdict != "approve" else [],
            "reviewer_actor_id": ACTORS["actor-b"],
            "required_evidence_refs": ["evidence:task-review-verdict"],
            "limitations": [],
            "conditions": [],
            "reviewer_profile": "independent-reviewer",
            "reviewer_session": "session:c3-task-review",
            "reviewer_model_metadata": "model:independent",
            "context_manifest_id": "ctx_01978abc-6500-7000-8000-000000006500",
            "context_manifest_sha256": "b" * 64,
            "unchanged_subject_sha256": subject_hash,
            "producing_attempt_id": ATTEMPT_ID,
            "trace_visibility_evidence_refs": ["evidence:task-review-trace"],
            "computed_independence_grade": "I2",
        },
        actor_id=ACTORS["actor-b"],
        authority_grant_id=reviewer_grant,
    )


def test_accept_task_requires_a_satisfied_exact_review_and_complete_criteria_set(tmp_path):
    harness = _c1_control_plane(tmp_path)
    review_id = "rev_01978abc-6501-7000-8000-000000006501"
    subject_hash = _task_to_review_pending(harness, review_id, 6501)
    _request_review(harness, review_id, 6503, subject_hash, subject_id=TASK_ID)
    _record_review_verdict(harness, review_id, subject_hash, 6504, "approve")
    _submit_review_command(
        harness,
        6507,
        "SatisfyReview",
        review_id,
        {
            "review_id": review_id,
            "prior_review_state": "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:task-acceptance"],
            "satisfaction_gate": "task-acceptance-gate",
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    before = harness.ledger.snapshot()
    accepted = _c1_command(
        _command_id(6508),
        "AcceptTask",
        TASK_ID,
        before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "task_revision": task["current_revision"],
            "satisfied_review_ids": [review_id],
            "satisfied_acceptance_criteria": list(task["definition"]["acceptance_criteria"]),
            "selected_artefact_ids": [],
        },
    )

    receipt = harness.service.submit(accepted)

    assert receipt.status == "accepted", receipt
    projected = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert projected["status"] == "accepted"
    assert projected["acceptance"] == accepted["payload"]


def test_accept_task_rejects_a_satisfied_review_for_a_different_subject_without_append(tmp_path):
    harness = _c1_control_plane(tmp_path)
    review_id = "rev_01978abc-6502-7000-8000-000000006502"
    _task_to_review_pending(harness, review_id, 6521)
    _create_task(harness, TASK_REVIEW, "cmd_01978abc-6522-7000-8000-000000006522")
    foreign_subject = replay(
        tuple(harness.ledger.iter_events()),
        schema_registry=harness.schemas,
    )["streams"][TASK_REVIEW]
    foreign_hash = sha256_hex(canonical_bytes(foreign_subject))
    _request_review(harness, review_id, 6523, foreign_hash, subject_id=TASK_REVIEW)
    _record_review_verdict(harness, review_id, foreign_hash, 6524, "approve")
    _submit_review_command(
        harness,
        6527,
        "SatisfyReview",
        review_id,
        {
            "review_id": review_id,
            "prior_review_state": "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:foreign-task-review"],
            "satisfaction_gate": "task-acceptance-gate",
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    before = tuple(harness.ledger.iter_events())
    command = _c1_command(
        _command_id(6528),
        "AcceptTask",
        TASK_ID,
        harness.ledger.snapshot().stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "task_revision": task["current_revision"],
            "satisfied_review_ids": [review_id],
            "satisfied_acceptance_criteria": list(task["definition"]["acceptance_criteria"]),
            "selected_artefact_ids": [],
        },
    )

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "task_acceptance_precondition_failed"
    assert tuple(harness.ledger.iter_events()) == before


def test_reject_and_reopen_task_bind_the_exact_verdict_subject_and_terminal_event(tmp_path):
    harness = _c1_control_plane(tmp_path)
    review_id = "rev_01978abc-6511-7000-8000-000000006511"
    subject_hash = _task_to_review_pending(harness, review_id, 6511)
    _request_review(harness, review_id, 6513, subject_hash, subject_id=TASK_ID)
    _record_review_verdict(harness, review_id, subject_hash, 6514, "reject")
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    before = harness.ledger.snapshot()
    rejected = _c1_command(
        _command_id(6517),
        "RejectTask",
        TASK_ID,
        before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "task_revision": task["current_revision"],
            "rejection_reason": "the exact independent verdict rejected the subject",
            "review_verdict_id": review_id,
            "verdict_subject_sha256": subject_hash,
        },
    )
    assert harness.service.submit(rejected).status == "accepted"
    terminal_ref = _terminal_ref(harness)
    before_reopen = harness.ledger.snapshot()
    reopened = _c1_command(
        _command_id(6518),
        "ReopenTask",
        TASK_ID,
        before_reopen.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "prior_terminal_status": "rejected",
            "new_execution_epoch": 2,
            "reopen_reason": "owner authorized a new epoch after the rejection",
            "preserved_terminal_record_ref": terminal_ref,
            "authority_evidence_refs": ["authority:reopen-rejected"],
        },
    )

    receipt = harness.service.submit(reopened)

    assert receipt.status == "accepted", receipt
    projected = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert projected["status"] == "readiness_pending"
    assert projected["last_reopen"]["prior_terminal_status"] == "rejected"


def _decision_payload(decision_id: str, *, recommendation: str = "proceed") -> dict[str, object]:
    return {
        "new_decision_id": decision_id,
        "question": "Which bounded C3 option should govern?",
        "recommendation": recommendation,
        "options": ["proceed", "stop"],
        "decision_revision": 1,
        "decision_kind": "design_lock",
        "governing_evidence_refs": ["evidence:c3-decision"],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": "2026-08-10T12:00:00Z",
        "review_date": "2026-08-10T10:00:00Z",
        "consequences": ["the selected option governs only the bounded C3 subject"],
    }


def _submit_decision_command(
    harness,
    number: int,
    command_type: str,
    decision_id: str,
    payload: dict[str, object],
    *,
    actor_id: str | None = None,
    authority_grant_id: str | None = None,
):
    if command_type == "ProposeDecision" and actor_id is None:
        actor_id = ACTOR_C
        authority_grant_id = activate_lifecycle_grant(
            harness,
            subject_kind="decision",
            subject_id=decision_id,
            actor_id=ACTOR_C,
            allowed_actor_classes=("agent",),
            command_types=("ProposeDecision",),
            grant_id=f"agr_01978abc-{number:04d}-7000-8000-00000000{number:04d}",
        )
    version = harness.ledger.snapshot().stream_versions.get(decision_id, 0)
    command = _command(
        f"cmd_01978abc-{number:04d}-7000-8000-00000000{number:04d}",
        command_type,
        decision_id,
        version,
        payload,
    )
    if actor_id is not None:
        command["actor_id"] = actor_id
    if authority_grant_id is not None:
        command["authority_grant_id"] = authority_grant_id
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    return command


def test_resolve_decision_rejects_an_empty_stream_without_append(tmp_path):
    harness = control_plane(tmp_path)
    decision_id = "dec_01978abc-6690-7000-8000-000000006690"
    owner_grant = scoped_lifecycle_grant_id(decision_id)
    resolution = _command(
        "cmd_01978abc-6692-7000-8000-000000006692",
        "ResolveDecision",
        decision_id,
        0,
        {
            "decision_id": decision_id,
            "selected_option": "proceed",
            "effective_scope": "C3 empty-stream negative",
            "effective_at": "2026-08-09T12:00:00Z",
            "decision_revision": 1,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": owner_grant,
            "governing_evidence_refs": ["evidence:owner-decision"],
            "considered_review_ids": [DECISION_REVIEW_ID],
            "permitted_commands": ["AmendDecision"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["material subject change"],
        },
    )
    resolution["actor_id"] = ACTORS["actor-a"]
    resolution["authority_grant_id"] = owner_grant
    before = tuple(harness.ledger.iter_events())

    receipt = harness.service.submit(resolution)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "decision_resolution_precondition_failed", receipt
    assert tuple(harness.ledger.iter_events()) == before


def test_decision_rule_and_correction_rows_are_append_only_and_review_does_not_resolve(tmp_path):
    harness = control_plane(tmp_path)
    primary, rejected_id, expired_id, superseded_id, replacement_id = DECISION_IDS
    proposer_grant = activate_lifecycle_grant(
        harness,
        subject_kind="decision",
        subject_id=primary,
        actor_id=ACTOR_C,
        allowed_actor_classes=("agent",),
        command_types=("ProposeDecision", "RequestDecisionReview"),
        grant_id="agr_01978abc-7601-7000-8000-000000007601",
    )
    _submit_decision_command(
        harness,
        6601,
        "ProposeDecision",
        primary,
        _decision_payload(primary),
        actor_id=ACTOR_C,
        authority_grant_id=proposer_grant,
    )
    _submit_decision_command(
        harness,
        6602,
        "RequestDecisionReview",
        primary,
        {
            "decision_id": primary,
            "decision_revision": 1,
            "review_requirements": ["independent exact-subject review"],
            "governing_evidence_refs": ["evidence:decision-review-request"],
        },
        actor_id=ACTOR_C,
        authority_grant_id=proposer_grant,
    )
    decision_state = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][primary]
    decision_hash = sha256_hex(canonical_bytes(decision_state))
    _request_review(
        harness,
        DECISION_REVIEW_ID,
        6603,
        decision_hash,
        subject_id=primary,
    )
    _record_review_verdict(harness, DECISION_REVIEW_ID, decision_hash, 6604, "approve")
    _submit_review_command(
        harness,
        6607,
        "SatisfyReview",
        DECISION_REVIEW_ID,
        {
            "review_id": DECISION_REVIEW_ID,
            "prior_review_state": "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:decision-review"],
            "satisfaction_gate": "decision-review-gate",
        },
    )
    owner_grant = scoped_lifecycle_grant_id(primary)
    invalid_resolution = _command(
        "cmd_01978abc-6698-7000-8000-000000006698",
        "ResolveDecision",
        primary,
        harness.ledger.snapshot().stream_versions[primary],
        {
            "decision_id": primary,
            "selected_option": "not-a-listed-option",
            "effective_scope": "C3 decision test only",
            "effective_at": "2026-08-09T12:00:00Z",
            "decision_revision": 1,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": owner_grant,
            "governing_evidence_refs": ["evidence:owner-decision"],
            "considered_review_ids": [DECISION_REVIEW_ID],
            "permitted_commands": ["AmendDecision"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["material subject change"],
        },
    )
    invalid_resolution["actor_id"] = ACTORS["actor-a"]
    invalid_resolution["authority_grant_id"] = owner_grant
    before_invalid_resolution = tuple(harness.ledger.iter_events())

    rejected_resolution = harness.service.submit(invalid_resolution)

    assert rejected_resolution.status == "rejected"
    assert rejected_resolution.reason_code == "decision_resolution_precondition_failed"
    assert tuple(harness.ledger.iter_events()) == before_invalid_resolution
    _submit_decision_command(
        harness,
        6608,
        "ResolveDecision",
        primary,
        {
            "decision_id": primary,
            "selected_option": "proceed",
            "effective_scope": "C3 decision test only",
            "effective_at": "2026-08-09T12:00:00Z",
            "decision_revision": 1,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": owner_grant,
            "governing_evidence_refs": ["evidence:owner-decision"],
            "considered_review_ids": [DECISION_REVIEW_ID],
            "permitted_commands": ["AmendDecision"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["material subject change"],
        },
    )
    _submit_decision_command(
        harness,
        6609,
        "AmendDecision",
        primary,
        {
            "decision_id": primary,
            "decision_revision": 2,
            "changed_fields": ["effective_scope"],
            "rationale": "propose a bounded scope amendment without rewriting revision 1",
            "governing_evidence_refs": ["evidence:decision-amendment"],
            "producing_work_occurred": False,
            "affected_task_ids": [],
            "affected_artefact_ids": [],
            "effective_boundary": "after a new owner resolution",
            "redispatch_rerun_disclosure_requirements": ["disclose the superseded scope"],
        },
    )
    _submit_decision_command(
        harness,
        6630,
        "RequestDecisionReview",
        primary,
        {
            "decision_id": primary,
            "decision_revision": 2,
            "review_requirements": ["independent exact-subject review"],
            "governing_evidence_refs": ["evidence:decision-review-request:revision-2"],
        },
        actor_id=ACTOR_C,
        authority_grant_id=proposer_grant,
    )
    revision_2_state = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][primary]
    revision_2_hash = sha256_hex(canonical_bytes(revision_2_state))
    revision_2_review_id = "rev_01978abc-6631-7000-8000-000000006631"
    _request_review(harness, revision_2_review_id, 6631, revision_2_hash, subject_id=primary)
    _record_review_verdict(harness, revision_2_review_id, revision_2_hash, 6632, "approve")
    _submit_review_command(
        harness,
        6635,
        "SatisfyReview",
        revision_2_review_id,
        {
            "review_id": revision_2_review_id,
            "prior_review_state": "verdict_recorded",
            "policy_evaluation_refs": ["policy-evaluation:decision-review:revision-2"],
            "satisfaction_gate": "decision-review-gate",
        },
    )
    _submit_decision_command(
        harness,
        6636,
        "ResolveDecision",
        primary,
        {
            "decision_id": primary,
            "selected_option": "proceed",
            "effective_scope": "C3 amended decision test only",
            "effective_at": "2026-08-09T14:00:00Z",
            "decision_revision": 2,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": owner_grant,
            "governing_evidence_refs": ["evidence:owner-decision:revision-2"],
            "considered_review_ids": [revision_2_review_id],
            "permitted_commands": ["AmendDecision"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["material subject change"],
        },
    )
    duplicate_resolution = _command(
        "cmd_01978abc-6637-7000-8000-000000006637",
        "ResolveDecision",
        primary,
        harness.ledger.snapshot().stream_versions[primary],
        {
            "decision_id": primary,
            "selected_option": "proceed",
            "effective_scope": "C3 amended decision test only",
            "effective_at": "2026-08-09T14:00:00Z",
            "decision_revision": 2,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": owner_grant,
            "governing_evidence_refs": ["evidence:owner-decision:revision-2"],
            "considered_review_ids": [revision_2_review_id],
            "permitted_commands": ["AmendDecision"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["material subject change"],
        },
    )
    duplicate_resolution["actor_id"] = ACTORS["actor-a"]
    duplicate_resolution["authority_grant_id"] = owner_grant
    before_duplicate = tuple(harness.ledger.iter_events())

    duplicate_receipt = harness.service.submit(duplicate_resolution)

    assert duplicate_receipt.status == "rejected"
    assert duplicate_receipt.reason_code == "decision_already_resolved"
    assert tuple(harness.ledger.iter_events()) == before_duplicate

    _submit_decision_command(harness, 6610, "ProposeDecision", rejected_id, _decision_payload(rejected_id))
    _submit_decision_command(
        harness,
        6611,
        "RejectDecision",
        rejected_id,
        {
            "decision_id": rejected_id,
            "rejection_reason": "the owner rejects this bounded proposal",
            "decision_revision": 1,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": scoped_lifecycle_grant_id(rejected_id),
        },
    )
    _submit_decision_command(harness, 6612, "ProposeDecision", expired_id, _decision_payload(expired_id))
    _submit_decision_command(
        harness,
        6613,
        "ExpireDecision",
        expired_id,
        {"decision_id": expired_id, "observed_at": "2026-08-11T12:00:00Z", "decision_revision": 1},
    )
    _submit_decision_command(harness, 6614, "ProposeDecision", superseded_id, _decision_payload(superseded_id))
    _submit_decision_command(harness, 6615, "ProposeDecision", replacement_id, _decision_payload(replacement_id))
    _submit_decision_command(
        harness,
        6616,
        "SupersedeDecision",
        superseded_id,
        {
            "decision_id": superseded_id,
            "replacement_decision_id": replacement_id,
            "decision_revision": 1,
            "lineage_reason": "replace the unresolved proposal with its compatible successor",
            "effective_at": "2026-08-09T13:00:00Z",
        },
    )

    rule = _command(
        "cmd_01978abc-6620-7000-8000-000000006620",
        "RecordRuleEvaluation",
        RULE_EVALUATION_ID,
        0,
        {
            "new_rule_evaluation_id": RULE_EVALUATION_ID,
            "rule_version": "1.0.0",
            "referent_id": primary,
            "input_ids": [primary],
            "input_hashes": [decision_hash],
            "output": "review evidence exists but does not itself resolve the Decision",
            "rule_id": "rule:c3-review-separation",
            "referent_kind": "decision",
            "estimand_or_mathematical_object": "decision authority separation",
            "compared_subject_ids": [primary],
            "metric": "exact-state predicate",
            "denominator": "one bounded Decision",
            "calculation_validator": "deterministic-c3-rule-validator",
            "evidence_sha256": "c" * 64,
        },
    )
    assert harness.service.submit(rule).status == "accepted"
    rule_event = tuple(harness.ledger.iter_events())[-1]
    correction_grant = activate_lifecycle_grant(
        harness,
        subject_kind="corrected_record",
        subject_id=RULE_EVALUATION_ID,
        actor_id=ACTOR_C,
        allowed_actor_classes=("agent",),
        command_types=("RecordCorrection",),
        grant_id="agr_01978abc-7621-7000-8000-000000007621",
    )
    correction = _command(
        "cmd_01978abc-6621-7000-8000-000000006621",
        "RecordCorrection",
        RULE_EVALUATION_ID,
        1,
        {
            "erroneous_record_id": RULE_EVALUATION_ID,
            "incorrect_assertion": "the explanatory output omitted the owner-resolution boundary",
            "affected_consumer_ids": ["consumer:governance-audit"],
            "corrected_record_kind": "rule_evaluation",
            "corrected_evidence_refs": ["evidence:corrected-rule-explanation"],
            "corrected_object_ref": {
                "record_id": rule_event["event_id"],
                "content_sha256": rule_event["event_hash"],
            },
            "affected_projections": ["rule_evaluations"],
            "correction_authority": "owner",
            "governance_correction_index": "correction:c3-rule-1",
        },
    )
    correction["actor_id"] = ACTOR_C
    correction["authority_grant_id"] = correction_grant
    assert harness.service.submit(correction).status == "accepted"

    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][primary]["status"] == "resolved"
    assert projection["streams"][primary]["decision_revision"] == 2
    assert projection["streams"][primary]["effective_scope"] == "C3 amended decision test only"
    assert projection["streams"][rejected_id]["status"] == "rejected"
    assert projection["streams"][expired_id]["status"] == "expired"
    assert projection["streams"][superseded_id]["status"] == "superseded"
    assert projection["streams"][RULE_EVALUATION_ID]["status"] == "recorded"
    assert (
        projection["governance_correction_index"]["correction:c3-rule-1"]["erroneous_record_id"] == RULE_EVALUATION_ID
    )
    assert projection["streams"][DECISION_REVIEW_ID]["status"] == "satisfied"
