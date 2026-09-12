"""06s Phase 2: public Task closure through inherited authority, and its decisive negatives."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
import json
import subprocess
import sys

import pytest

from research_system import cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import spec_task
from research_system.discovery.spec import SpecCoordinator
from research_system.errors import (
    ArsError,
    ConflictError,
    IdempotencyConflictError,
    IntegrityError,
    SchemaError,
)
from research_system.methods.registration import _stable_command_id
from research_system.projection.replay import replay
from tests.research_system.factories import (
    ACTORS,
    GovernedTestCommandService,
    activate_lifecycle_grant,
)
from tests.research_system.integration.test_spec_source import bound_source  # noqa: F401
from tests.research_system.integration.test_wp6_1_c1_readiness_lease import (
    ATTEMPT_ID,
    C1_NOW,
    C1_TRUSTED_RUNTIME_AUTHORITY,
    LEASE_ID,
    OTHER_ATTEMPT_ID,
    RESOURCE_GRANT_ID,
    TASK_ID,
    _c1_command,
    _command_id,
    _release_lease_command,
    _seed_running_attempt,
)

OWNER = ACTORS["actor-a"]
REVIEWER = ACTORS["actor-b"]
REVIEW_ID = "rev_01978abc-9100-7000-8000-000000009100"
OTHER_REVIEW_ID = "rev_01978abc-9101-7000-8000-000000009101"
SECOND_REVIEW_ID = "rev_01978abc-9102-7000-8000-000000009102"

TASK_GRANT_ID = "agr_01978abc-9201-7000-8000-000000009201"
REVIEW_OWNER_GRANT_ID = "agr_01978abc-9202-7000-8000-000000009202"
REVIEWER_GRANT_ID = "agr_01978abc-9203-7000-8000-000000009203"


def close_task_intent(review_id: str = REVIEW_ID) -> dict:
    return {
        "action": spec_task.ACTION,
        "task_id": TASK_ID,
        "attempt_id": ATTEMPT_ID,
        "review_id": review_id,
        "reason": "close the exact operational Task through the public route",
    }


REQUEST_EVIDENCE = {
    "review_type": "software",
    "governing_refs": ["plan:06s"],
    "review_questions": ["Does the exact Task subject satisfy its bounded contract?"],
    "required_evidence_refs": ["evidence:spec-task-subject"],
    "required_lanes": ["software"],
    "reviewer_capability": ["python"],
    "deadline": "2026-12-31T12:00:00Z",
    "escalation_rule": "return rework_required on any material mismatch",
}
VERDICT_EVIDENCE = {
    "required_evidence_refs": ["evidence:spec-task-verdict"],
    "reviewer_profile": "independent-reviewer",
    "reviewer_session": "session:spec-task-review",
    "reviewer_model_metadata": "model:independent",
    "context_manifest_id": "ctx_01978abc-9500-7000-8000-000000009500",
    "context_manifest_sha256": "b" * 64,
    "trace_visibility_evidence_refs": ["evidence:spec-task-trace"],
}
SATISFY_EVIDENCE = {
    "policy_evaluation_refs": ["policy-evaluation:spec-task-review"],
    "satisfaction_gate": "spec-task-acceptance-gate",
}


def _assign_evidence(reviewer_actor_id: str = REVIEWER) -> dict:
    return {
        "reviewer_actor_id": reviewer_actor_id,
        "independence_evidence_refs": ["evidence:independent:spec-task"],
    }


EFFECT_EVIDENCE = {
    "SubmitForReview": None,
    "RequestReview": REQUEST_EVIDENCE,
    "AssignReview": _assign_evidence(),
    "StartReview": None,
    "RecordReviewVerdict": VERDICT_EVIDENCE,
    "SatisfyReview": SATISFY_EVIDENCE,
    "AcceptTask": None,
}


@pytest.fixture
def bound_task(bound_source):  # noqa: F811
    """A Task with terminal Attempt evidence, ready for the public closure route."""
    return _seed_bound_task(bound_source, complete_attempt=True)


@pytest.fixture
def bound_running_task(bound_source):  # noqa: F811
    """The same route subject while its Attempt is still running."""
    return _seed_bound_task(bound_source, complete_attempt=False)


def _seed_bound_task(bound_source, *, complete_attempt: bool):  # noqa: F811
    """Supply Task and Attempt evidence through existing governed contracts.

    The seeding service is the established governed test adapter on the same scratch
    control store. The SPEC route keeps the coordinator's plain CommandService, so
    every route effect resolves real authority rather than an auto-provisioned grant.
    """
    coordinator = bound_source.coordinator
    seeding = GovernedTestCommandService(
        coordinator.binding.control_root,
        coordinator.ledger,
        coordinator.objects,
        coordinator.service.receipts,
        coordinator.schemas,
        authority_resolver=coordinator.resolver,
        clock=lambda: C1_NOW,
        trusted_runtime_authority_provider=lambda: C1_TRUSTED_RUNTIME_AUTHORITY,
        authority_harness=bound_source.harness,
    )
    seed_harness = replace(bound_source.harness, service=seeding)
    # On the bound route the authority ledger is the control ledger, so a grant
    # activated inside admission would move the global position that the resource
    # request must bind. Activate it first; admission then reuses it without an append.
    activate_lifecycle_grant(bound_source.harness, subject_kind="resource", subject_id=RESOURCE_GRANT_ID)
    _seed_running_attempt(seed_harness)
    if complete_attempt:
        completed = _c1_command(
            _command_id(9001),
            "CompleteAttempt",
            ATTEMPT_ID,
            coordinator.ledger.snapshot().stream_versions[ATTEMPT_ID],
            {
                "attempt_id": ATTEMPT_ID,
                "candidate_artefact_ids": [],
                "end_evidence_refs": ["evidence:spec-task-attempt"],
                "output_disposition": "no_candidate_output",
            },
        )
        assert seeding.submit(completed).status == "accepted"

    grants = {
        "task": activate_lifecycle_grant(
            bound_source.harness,
            subject_kind="task",
            subject_id=TASK_ID,
            actor_id=OWNER,
            command_types=("SubmitForReview", "AcceptTask"),
            grant_id=TASK_GRANT_ID,
        ),
        "review_owner": activate_lifecycle_grant(
            bound_source.harness,
            subject_kind="review",
            subject_id=REVIEW_ID,
            actor_id=OWNER,
            command_types=("RequestReview", "AssignReview", "SatisfyReview"),
            grant_id=REVIEW_OWNER_GRANT_ID,
        ),
        "reviewer": activate_lifecycle_grant(
            bound_source.harness,
            subject_kind="review",
            subject_id=REVIEW_ID,
            actor_id=REVIEWER,
            allowed_actor_classes=("agent",),
            command_types=("StartReview", "RecordReviewVerdict"),
            grant_id=REVIEWER_GRANT_ID,
        ),
    }
    return SimpleNamespace(bound=bound_source, coordinator=coordinator, seeding=seeding, grants=grants)


def _streams(coordinator) -> dict:
    """Replay with the coordinator's inherited authority-state validator."""
    return replay(
        tuple(coordinator.ledger.iter_events()),
        schema_registry=coordinator.schemas,
        authority_state_validator=coordinator.resolver.validate_replayed_administration_state,
    )["streams"]


def _tail(coordinator) -> tuple[int, str]:
    """Return the exact authoritative ledger tail."""
    snapshot = coordinator.ledger.snapshot()
    return snapshot.global_position, snapshot.event_hash


def _effect_command(coordinator, effect, intent, state, *, actor_id, evidence=None):
    return spec_task.effect_command(
        effect,
        intent,
        state,
        coordinator.ledger.snapshot().events,
        actor_id=actor_id,
        evidence=evidence,
        schemas=coordinator.schemas,
        authority_state_validator=coordinator.resolver.validate_replayed_administration_state,
    )


def _effect_identity(effect: str, grants: dict) -> tuple[str, str]:
    """Return the actor and grant that inherited authority permits for one effect."""
    if effect in {"StartReview", "RecordReviewVerdict"}:
        return REVIEWER, grants["reviewer"]
    if effect in {"SubmitForReview", "AcceptTask"}:
        return OWNER, grants["task"]
    return OWNER, grants["review_owner"]


def _cli_args(bound_task, effect, tmp_path, *, intent=None, evidence=None, actor=None, grant=None) -> list[str]:
    """Write the operator config and intent, and return the genuine CLI arguments."""
    default_actor, default_grant = _effect_identity(effect, bound_task.grants)
    payload = dict(intent or close_task_intent())
    supplied = EFFECT_EVIDENCE[effect] if evidence is None else evidence
    if supplied is not None:
        payload["evidence"] = supplied
    intent_path = tmp_path / "intent.json"
    intent_path.write_bytes(canonical_bytes(payload))
    config_path = tmp_path / "operator.json"
    config_path.write_bytes(
        canonical_bytes(
            {
                **bound_task.bound.config,
                "authority_grant_id": grant or default_grant,
                "operator_actor_id": actor or default_actor,
            }
        )
    )
    return [
        "discovery",
        "spec",
        "advance",
        "--operator-config",
        str(config_path),
        "--action",
        spec_task.ACTION,
        "--input",
        str(intent_path),
    ]


def _advance(bound_task, effect, tmp_path, capsys, **kwargs):
    """Drive one effect through the genuine public CLI and require success."""
    args = _cli_args(bound_task, effect, tmp_path, **kwargs)
    assert cli.main(args) == 0
    return json.loads(capsys.readouterr().out)


def _refuse(bound_task, effect, tmp_path, capsys, **kwargs) -> str:
    """Require the genuine public CLI to refuse one effect, and return its message."""
    before = _tail(bound_task.coordinator)
    args = _cli_args(bound_task, effect, tmp_path, **kwargs)
    assert cli.main(args) == 1
    assert _tail(bound_task.coordinator) == before, "a refused effect appended an authoritative event"
    return capsys.readouterr().err


def test_public_close_task_positive_path_status_and_replay(bound_task, tmp_path, capsys):
    intent = close_task_intent()
    initial = bound_task.coordinator.status(intent)
    assert initial["state"] == "not_started"
    assert initial["next_effect"] == "SubmitForReview"
    assert initial["effects"] == []

    for index, effect in enumerate(spec_task.EFFECTS):
        result = _advance(bound_task, effect, tmp_path, capsys)
        assert result["receipt"]["status"] == "accepted", (effect, result["receipt"])
        assert len(result["effects"]) == index + 1, effect
        expected_next = spec_task.EFFECTS[index + 1] if index + 1 < len(spec_task.EFFECTS) else None
        assert result["next_effect"] == expected_next, effect
        assert result["state"] == ("completed" if expected_next is None else "prepared"), effect

    final = bound_task.coordinator.status(intent)
    assert final["state"] == "completed" and final["next_effect"] is None
    assert {entry["actor_id"] for entry in final["effects"]} == {OWNER, REVIEWER}
    verdict = final["effects"][spec_task.EFFECTS.index("RecordReviewVerdict")]
    producer = final["effects"][spec_task.EFFECTS.index("SubmitForReview")]
    assert verdict["actor_id"] == REVIEWER and producer["actor_id"] == OWNER
    assert verdict["authority_grant_id"] != producer["authority_grant_id"]
    assert _streams(bound_task.coordinator)[TASK_ID]["status"] == "accepted"

    # The enumerating status recovers the same action from ledger evidence alone.
    listed = bound_task.coordinator.status()
    closures = [action for action in listed["actions"] if action.get("action") == spec_task.ACTION]
    assert len(closures) == 1 and closures[0]["state"] == "completed"
    assert spec_task.ACTION in listed["available_actions"]


def test_replay_from_a_fresh_process_reconstructs_the_accepted_closure(bound_task, tmp_path, capsys):
    for effect in spec_task.EFFECTS:
        _advance(bound_task, effect, tmp_path, capsys)
    expected = bound_task.coordinator.status(close_task_intent())
    tail = _tail(bound_task.coordinator)

    # A fresh process imports the public CLI and changes only its scratch foundation selection.
    code = (
        "import sys; from pathlib import Path; from research_system import cli; "
        "cli.canonical_foundation_path=lambda:Path(sys.argv[1]); "
        "raise SystemExit(cli.main(sys.argv[2:]))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            code,
            str(bound_task.bound.fixture.foundation_path),
            "discovery",
            "spec",
            "status",
            "--operator-config",
            str(tmp_path / "operator.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    listed = [action for action in json.loads(result.stdout)["actions"] if action.get("action") == spec_task.ACTION]
    assert listed == [expected]
    assert _tail(bound_task.coordinator) == tail


def test_closure_is_not_inferred_from_attempt_completion_or_lease_release(bound_task):
    """A terminal Attempt and a released lease are not Task closure."""
    coordinator = bound_task.coordinator
    intent = close_task_intent()
    assert _streams(coordinator)[ATTEMPT_ID]["status"] == "completed"
    state = coordinator.status(intent)
    assert state["state"] == "not_started" and state["effects"] == []

    released = _release_lease_command(
        number=9002,
        expected_stream_version=coordinator.ledger.snapshot().stream_versions[LEASE_ID],
    )
    assert bound_task.seeding.submit(released).status == "accepted"
    assert _streams(coordinator)[LEASE_ID]["status"] != "held"

    after_release = coordinator.status(intent)
    assert after_release["state"] == "not_started" and after_release["effects"] == []
    assert _streams(coordinator)[TASK_ID]["status"] != "accepted"


def test_self_review_is_rejected_and_appends_no_authoritative_effect(bound_task, tmp_path, capsys):
    for effect in ("SubmitForReview", "RequestReview"):
        _advance(bound_task, effect, tmp_path, capsys)

    message = _refuse(bound_task, "AssignReview", tmp_path, capsys, evidence=_assign_evidence(OWNER))
    assert "own reviewer" in message

    _advance(bound_task, "AssignReview", tmp_path, capsys)
    owner_as_reviewer = _refuse(
        bound_task,
        "StartReview",
        tmp_path,
        capsys,
        actor=OWNER,
        grant=bound_task.grants["review_owner"],
    )
    assert "independent of the producer" in owner_as_reviewer
    assert bound_task.coordinator.status(close_task_intent())["next_effect"] == "StartReview"


def test_non_owner_acceptance_is_rejected_and_appends_no_authoritative_effect(bound_task, tmp_path, capsys):
    for effect in spec_task.EFFECTS[:-1]:
        _advance(bound_task, effect, tmp_path, capsys)
    non_owner_grant = activate_lifecycle_grant(
        bound_task.bound.harness,
        subject_kind="task",
        subject_id=TASK_ID,
        actor_id=REVIEWER,
        allowed_actor_classes=("agent",),
        command_types=("AcceptTask",),
        grant_id="agr_01978abc-9205-7000-8000-000000009205",
    )
    message = _refuse(bound_task, "AcceptTask", tmp_path, capsys, actor=REVIEWER, grant=non_owner_grant)
    # The refusal must come from inherited authority, not an incidental precondition.
    assert "lifecycle_authority_unauthorized" in message, message
    state = bound_task.coordinator.status(close_task_intent())
    assert state["state"] == "prepared" and state["next_effect"] == "AcceptTask"
    assert _streams(bound_task.coordinator)[TASK_ID]["status"] == "review_pending"


def test_non_owner_producer_cannot_submit_for_review(bound_task, tmp_path, capsys):
    non_owner_grant = activate_lifecycle_grant(
        bound_task.bound.harness,
        subject_kind="task",
        subject_id=TASK_ID,
        actor_id=REVIEWER,
        allowed_actor_classes=("agent",),
        command_types=("SubmitForReview",),
        grant_id="agr_01978abc-9206-7000-8000-000000009206",
    )
    message = _refuse(bound_task, "SubmitForReview", tmp_path, capsys, actor=REVIEWER, grant=non_owner_grant)
    assert "lifecycle_authority_unauthorized" in message, message
    assert bound_task.coordinator.status(close_task_intent())["state"] == "not_started"


def test_acceptance_requires_satisfied_review_evidence(bound_task, tmp_path, capsys):
    """Acceptance built before SatisfyReview is refused and leaves no effect."""
    for effect in spec_task.EFFECTS[:-2]:
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    before = _tail(coordinator)
    state = coordinator.status(close_task_intent())
    assert state["next_effect"] == "SatisfyReview"

    _, payload = _effect_command(coordinator, "AcceptTask", close_task_intent(), state, actor_id=OWNER)
    accept = _c1_command(
        _command_id(9003),
        "AcceptTask",
        TASK_ID,
        coordinator.ledger.snapshot().stream_versions[TASK_ID],
        payload,
        actor_id=OWNER,
        authority_grant_id=bound_task.grants["task"],
    )
    receipt = coordinator.service.submit(accept)
    assert receipt.status == "rejected"
    assert receipt.reason_code == "task_acceptance_precondition_failed"
    assert _tail(coordinator) == before
    assert coordinator.status(close_task_intent())["state"] == "prepared"


def test_expired_actor_cannot_create_a_new_effect_while_completed_state_stays_readable(bound_task, tmp_path, capsys):
    for effect in spec_task.EFFECTS:
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    completed = coordinator.status(close_task_intent())

    # Valid when activated at the fixture clock, expired at the later route clock.
    expired = activate_lifecycle_grant(
        bound_task.bound.harness,
        subject_kind="task",
        subject_id=TASK_ID,
        actor_id=OWNER,
        command_types=("SubmitForReview", "AcceptTask"),
        grant_id="agr_01978abc-9207-7000-8000-000000009207",
        effective_at="2026-01-01T00:00:00Z",
        expires_at="2026-09-11T00:00:00Z",
    )
    # Grant activation is itself an authoritative append on this shared ledger.
    tail = _tail(coordinator)
    config_path = tmp_path / "expired-operator.json"
    config_path.write_bytes(
        canonical_bytes({**bound_task.bound.config, "authority_grant_id": expired, "operator_actor_id": OWNER})
    )
    late = SpecCoordinator(
        cli._load_gate6_binding_context(config_path),
        replace(coordinator.operator, authority_grant_id=expired, operator_actor_id=OWNER),
        clock=lambda: datetime(2027, 1, 1, tzinfo=UTC),
    )

    # The completed action reads its recorded effects without requiring new authority.
    assert late.advance(close_task_intent(), None) == completed
    assert _tail(coordinator) == tail

    # A new effect for a fresh review subject under the same expired grant is refused.
    fresh = close_task_intent(OTHER_REVIEW_ID)
    assert late.status(fresh)["state"] == "not_started"
    with pytest.raises(ArsError, match="expired"):
        late.advance(fresh, None)
    assert _tail(coordinator) == tail


def test_exact_retry_reads_the_existing_receipt_without_new_effects(bound_task, tmp_path, capsys):
    for effect in spec_task.EFFECTS:
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    completed = coordinator.status(close_task_intent())
    tail = _tail(coordinator)

    repeated = _advance(bound_task, "AcceptTask", tmp_path, capsys)
    assert repeated == completed
    assert "receipt" not in repeated
    assert _tail(coordinator) == tail

    # Rebuild the exact original command: the shared retry key is derived from the
    # semantic intent, effect, actor, grant and payload alone.
    intent = close_task_intent()
    events = coordinator.ledger.snapshot().events
    accepted_event = next(
        event for event in events if event["event_type"] == "TaskAccepted" and event["stream_id"] == TASK_ID
    )
    _, payload = _effect_command(coordinator, "AcceptTask", intent, completed, actor_id=OWNER)
    assert payload == dict(accepted_event["payload"])
    retry = "spec:" + sha256_hex(canonical_bytes([intent, "AcceptTask", OWNER, bound_task.grants["task"], payload]))
    assert _stable_command_id(retry) == accepted_event["command_id"]

    def accept_command(expected_stream_version: int) -> dict:
        return {
            "command_id": _stable_command_id(retry),
            "command_type": "AcceptTask",
            "schema_id": "ars://core/command/AcceptTask",
            "schema_version": "1.0.0",
            "submitted_at": "2026-09-10T00:00:00Z",
            "actor_id": OWNER,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": bound_task.grants["task"],
            "target_stream_id": TASK_ID,
            "expected_stream_version": expected_stream_version,
            "idempotency_key": retry,
            "correlation_id": retry,
            "causation_id": None,
            "reason": intent["reason"],
            "evidence_refs": [],
            "project_id": coordinator.binding.project_id,
            "payload": payload,
        }

    # The exact retry reads its existing receipt verbatim and appends nothing.
    original_version = accepted_event["stream_version"] - 1
    retried = coordinator.service.submit(accept_command(original_version))
    assert _tail(coordinator) == tail, "an exact retry appended a duplicate authoritative effect"
    assert retried.command_id == accepted_event["command_id"]
    assert retried.status in {"accepted", "replayed"}
    assert coordinator.service.submit(accept_command(original_version)) == retried
    assert _tail(coordinator) == tail

    # The same key rebound to a later version is refused rather than duplicated.
    with pytest.raises(IdempotencyConflictError):
        coordinator.service.submit(accept_command(accepted_event["stream_version"]))
    assert _tail(coordinator) == tail


def test_close_task_intent_rejects_unrecognized_and_missing_fields(bound_task):
    coordinator = bound_task.coordinator
    with pytest.raises(SchemaError):
        coordinator.status({**close_task_intent(), "owner_actor_id": OWNER})
    with pytest.raises(SchemaError):
        coordinator.status({key: value for key, value in close_task_intent().items() if key != "review_id"})


def test_verdict_bound_to_another_subject_is_not_completion(bound_task, tmp_path, capsys):
    """A verdict whose exact subject hash differs does not satisfy the action."""
    for effect in ("SubmitForReview", "RequestReview", "AssignReview", "StartReview"):
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    intent = close_task_intent()
    state = coordinator.status(intent)
    _, payload = _effect_command(
        coordinator, "RecordReviewVerdict", intent, state, actor_id=REVIEWER, evidence=VERDICT_EVIDENCE
    )
    drifted = {**payload, "unchanged_subject_sha256": sha256_hex(b"another subject")}
    before = _tail(coordinator)
    command = _c1_command(
        _command_id(9004),
        "RecordReviewVerdict",
        REVIEW_ID,
        coordinator.ledger.snapshot().stream_versions[REVIEW_ID],
        drifted,
        actor_id=REVIEWER,
        authority_grant_id=bound_task.grants["reviewer"],
    )
    receipt = coordinator.service.submit(command)
    assert receipt.status == "rejected"
    assert receipt.reason_code == "review_verdict_precondition_failed"
    assert _tail(coordinator) == before
    assert coordinator.status(intent)["next_effect"] == "RecordReviewVerdict"


def test_inherited_enforcement_refuses_self_review_independently_of_the_route(bound_task, tmp_path, capsys):
    """The governed boundary refuses self-review even with the route check bypassed.

    The route refuses these before submitting, so each command is built and submitted
    directly to prove the inherited rule is what holds, not only the fail-fast check.
    """
    for effect in ("SubmitForReview", "RequestReview"):
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    before = _tail(coordinator)

    # AssignReview naming the requester as reviewer.
    assign = _c1_command(
        _command_id(9005),
        "AssignReview",
        REVIEW_ID,
        coordinator.ledger.snapshot().stream_versions[REVIEW_ID],
        {
            "review_id": REVIEW_ID,
            "reviewer_actor_id": OWNER,
            "computed_independence_grade": "independent_exact_subject",
            "independence_evidence_refs": ["evidence:self-review-attempt"],
        },
        actor_id=OWNER,
        authority_grant_id=bound_task.grants["review_owner"],
    )
    receipt = coordinator.service.submit(assign)
    assert receipt.status == "rejected"
    # That code covers a four-way condition. The other three clauses are excluded by
    # construction: the review is in "requested", the actor IS the requester, and the
    # independence refs are non-empty. Only reviewer == requester can fire.
    assert receipt.reason_code == "review_assignment_precondition_failed"
    assert "distinct from the requester" in receipt.explanation
    assert _tail(coordinator) == before

    # With an independent reviewer assigned, the producer still cannot start the
    # review, under a grant that does permit the command for that actor.
    _advance(bound_task, "AssignReview", tmp_path, capsys)
    owner_start_grant = activate_lifecycle_grant(
        bound_task.bound.harness,
        subject_kind="review",
        subject_id=REVIEW_ID,
        actor_id=OWNER,
        command_types=("StartReview",),
        grant_id="agr_01978abc-9208-7000-8000-000000009208",
    )
    assigned_tail = _tail(coordinator)
    state = coordinator.status(close_task_intent())
    start = _c1_command(
        _command_id(9006),
        "StartReview",
        REVIEW_ID,
        coordinator.ledger.snapshot().stream_versions[REVIEW_ID],
        {
            "review_id": REVIEW_ID,
            "unchanged_subject_sha256": state["subject_sha256"],
            "visibility_policy": "owner_and_reviewer",
        },
        actor_id=OWNER,
        authority_grant_id=owner_start_grant,
    )
    started = coordinator.service.submit(start)
    assert started.status == "rejected"
    # Authority is deliberately satisfied by owner_start_grant, the review is in
    # "assigned", the assignment exists, and the bound subject hash is the exact one
    # the request carries. Only actor != assigned reviewer can fire, despite the
    # inherited code naming this reason after the subject clause.
    assert started.reason_code == "review_start_subject_mismatch"
    assert "requires the assigned reviewer" in started.explanation
    assert _tail(coordinator) == assigned_tail


def test_submit_for_review_requires_terminal_attempt_evidence(bound_running_task, tmp_path, capsys):
    """A running Attempt is not review-ready, and the refusal leaves no effect."""
    coordinator = bound_running_task.coordinator
    assert _streams(coordinator)[ATTEMPT_ID]["status"] == "running"
    message = _refuse(bound_running_task, "SubmitForReview", tmp_path, capsys)
    assert "c2_dependency_not_terminal" in message, message
    assert coordinator.status(close_task_intent())["state"] == "not_started"


def test_a_non_approving_verdict_conflicts_instead_of_under_reporting(bound_task, tmp_path, capsys):
    """A satisfied non-approving verdict is conflicting evidence, not "prepared"."""
    for effect in ("SubmitForReview", "RequestReview", "AssignReview", "StartReview"):
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    intent = close_task_intent()
    state = coordinator.status(intent)
    _, approving = _effect_command(
        coordinator, "RecordReviewVerdict", intent, state, actor_id=REVIEWER, evidence=VERDICT_EVIDENCE
    )
    refusing = {**approving, "verdict": "reject", "findings": ["the exact subject does not satisfy its contract"]}
    command = _c1_command(
        _command_id(9007),
        "RecordReviewVerdict",
        REVIEW_ID,
        coordinator.ledger.snapshot().stream_versions[REVIEW_ID],
        refusing,
        actor_id=REVIEWER,
        authority_grant_id=bound_task.grants["reviewer"],
    )
    assert coordinator.service.submit(command).status == "accepted"
    with pytest.raises(ConflictError, match="does not approve"):
        coordinator.status(intent)

    # The enumerating listing must survive it: one decided Task cannot deny the route.
    listed = coordinator.status()
    closures = [action for action in listed["actions"] if action.get("action") == spec_task.ACTION]
    assert len(closures) == 1
    assert "does not approve" in closures[0]["unreadable"]
    assert "state" not in closures[0], "a conflict entry must not read as a route state"
    assert listed["route_id"] == coordinator.operator.route_id
    assert spec_task.ACTION in listed["available_actions"]


def test_effects_that_take_no_evidence_reject_supplied_evidence(bound_task, tmp_path, capsys):
    message = _refuse(bound_task, "SubmitForReview", tmp_path, capsys, evidence=SATISFY_EVIDENCE)
    assert "takes no independent evidence" in message, message
    assert bound_task.coordinator.status(close_task_intent())["state"] == "not_started"


def test_status_listing_survives_an_unrelated_task_review_submission(bound_task):
    """One governed submission naming a non-review id must not fail the listing."""
    unrelated = spec_task.enumerated_intents(
        [
            {
                "event_type": "TaskSubmittedForReview",
                "stream_id": "tsk_01978abc-9300-7000-8000-000000009300",
                "payload": {"attempt_id": ATTEMPT_ID, "requested_review_ids": ["pending-review", REVIEW_ID]},
            }
        ]
    )
    assert [intent["review_id"] for intent in unrelated] == [REVIEW_ID]
    assert bound_task.coordinator.status()["actions"] == []


def test_verdict_naming_another_attempt_is_not_completion(bound_task, tmp_path, capsys):
    """Review admission ignores producing_attempt_id, so the route must bind it."""
    for effect in ("SubmitForReview", "RequestReview", "AssignReview", "StartReview"):
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    intent = close_task_intent()
    state = coordinator.status(intent)
    _, payload = _effect_command(
        coordinator, "RecordReviewVerdict", intent, state, actor_id=REVIEWER, evidence=VERDICT_EVIDENCE
    )
    foreign = {**payload, "producing_attempt_id": OTHER_ATTEMPT_ID}
    command = _c1_command(
        _command_id(9008),
        "RecordReviewVerdict",
        REVIEW_ID,
        coordinator.ledger.snapshot().stream_versions[REVIEW_ID],
        foreign,
        actor_id=REVIEWER,
        authority_grant_id=bound_task.grants["reviewer"],
    )
    # Admission accepts it: no review precondition validates that field.
    assert coordinator.service.submit(command).status == "accepted"
    with pytest.raises(IntegrityError, match="another producing Attempt"):
        coordinator.status(intent)


def test_review_request_binds_the_task_state_current_at_request(bound_task, tmp_path, capsys):
    """A Task validly paused and resumed at review_pending must not strand the route."""
    coordinator = bound_task.coordinator
    _advance(bound_task, "SubmitForReview", tmp_path, capsys)
    after_submit = coordinator.status(close_task_intent())["subject_sha256"]

    paused = _c1_command(
        _command_id(9009),
        "PauseTask",
        TASK_ID,
        coordinator.ledger.snapshot().stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "pause_reason": "owner paused the Task while it awaited review",
            "prior_active_status": "review_pending",
            "resumable_state_ref": "evidence:resumable-review-pending",
            "process_disposition": {
                "process_state": "quiesced",
                "children_closed": True,
                "writers_closed": True,
                "evidence_refs": ["evidence:pause-process"],
            },
        },
    )
    assert bound_task.seeding.submit(paused).status == "accepted"
    resumed = _c1_command(
        _command_id(9010),
        "ResumeTask",
        TASK_ID,
        coordinator.ledger.snapshot().stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "suspended_status": "paused",
            "prior_active_status": "review_pending",
            "resolution_evidence_refs": ["evidence:pause-resolved"],
            "authority_evidence_refs": ["evidence:pause-authority"],
        },
    )
    assert bound_task.seeding.submit(resumed).status == "accepted"

    # The reviewed subject moved, so the route must re-derive it or RequestReview
    # is refused with stale_subject_hash and review_pending cannot be re-entered.
    after_resume = coordinator.status(close_task_intent())["subject_sha256"]
    assert after_resume != after_submit
    result = _advance(bound_task, "RequestReview", tmp_path, capsys)
    assert result["receipt"]["status"] == "accepted"
    assert result["next_effect"] == "AssignReview"
    assert result["subject_sha256"] == after_resume


def test_acceptance_names_every_requested_review(bound_task, tmp_path, capsys):
    """One satisfied review must not terminally accept a multi-review submission."""
    coordinator = bound_task.coordinator
    submitted = _c1_command(
        _command_id(9011),
        "SubmitForReview",
        TASK_ID,
        coordinator.ledger.snapshot().stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": [],
            "attempt_outcome": "completed",
            "candidate_artefact_hashes": [],
            "requested_review_ids": [REVIEW_ID, SECOND_REVIEW_ID],
        },
    )
    assert bound_task.seeding.submit(submitted).status == "accepted"

    for effect in ("RequestReview", "AssignReview", "StartReview", "RecordReviewVerdict", "SatisfyReview"):
        _advance(bound_task, effect, tmp_path, capsys)
    intent = close_task_intent()
    state = coordinator.status(intent)
    assert state["next_effect"] == "AcceptTask"

    _, payload = _effect_command(coordinator, "AcceptTask", intent, state, actor_id=OWNER)
    assert payload["satisfied_review_ids"] == [REVIEW_ID, SECOND_REVIEW_ID]

    # The second requested review is unsatisfied, so acceptance must be refused.
    message = _refuse(bound_task, "AcceptTask", tmp_path, capsys)
    assert "task_acceptance_precondition_failed" in message, message
    assert _streams(coordinator)[TASK_ID]["status"] == "review_pending"


def test_a_withdrawn_review_conflicts_instead_of_advertising_progress(bound_task, tmp_path, capsys):
    for effect in ("SubmitForReview", "RequestReview"):
        _advance(bound_task, effect, tmp_path, capsys)
    coordinator = bound_task.coordinator
    withdraw_grant = activate_lifecycle_grant(
        bound_task.bound.harness,
        subject_kind="review",
        subject_id=REVIEW_ID,
        actor_id=OWNER,
        command_types=("WithdrawReview",),
        grant_id="agr_01978abc-9209-7000-8000-000000009209",
    )
    withdrawn = _c1_command(
        _command_id(9012),
        "WithdrawReview",
        REVIEW_ID,
        coordinator.ledger.snapshot().stream_versions[REVIEW_ID],
        {"review_id": REVIEW_ID, "withdrawal_reason": "the requested review is no longer required"},
        actor_id=OWNER,
        authority_grant_id=withdraw_grant,
    )
    assert coordinator.service.submit(withdrawn).status == "accepted"
    with pytest.raises(ConflictError, match="ReviewWithdrawn"):
        coordinator.status(close_task_intent())
    # The listing still renders, carrying the conflict rather than denying the route.
    closures = [a for a in coordinator.status()["actions"] if a.get("action") == spec_task.ACTION]
    assert len(closures) == 1 and "ReviewWithdrawn" in closures[0]["unreadable"]


def test_absent_or_unbound_governed_subjects_are_not_runnable_actions(bound_task):
    coordinator = bound_task.coordinator
    missing_task = {**close_task_intent(), "task_id": "tsk_01978abc-9400-7000-8000-000000009400"}
    with pytest.raises(IntegrityError, match="no existing Task"):
        coordinator.status(missing_task)
    unbound_attempt = {**close_task_intent(), "attempt_id": OTHER_ATTEMPT_ID}
    with pytest.raises(IntegrityError, match="not bound to this Task"):
        coordinator.status(unbound_attempt)
