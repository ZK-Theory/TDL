from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

import research_system.cli as cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, SchemaError
from research_system.projection.replay import replay
from tests.research_system.factories import ACTORS, REPO_ROOT, activate_lifecycle_grant
from tests.research_system.integration.test_wp6_1_c1_readiness_lease import (
    TASK_ID,
    ATTEMPT_ID,
    DISPATCH_ID,
    LEASE_ID,
    _c1_command,
    _c1_control_plane,
    _command_id,
    _release_lease_command,
    _c1_scoped_index_path,
    _domain_snapshot,
    _rejection_snapshot,
    _seed_running_attempt,
)


SAFE_C2_COMMAND_EVENTS = {
    "BlockTask": "TaskBlocked",
    "RequestInput": "InputRequested",
    "PauseTask": "TaskPaused",
    "SubmitForReview": "TaskSubmittedForReview",
    "ResumeTask": "TaskResumed",
    "CancelTask": "TaskCancelled",
    "RecordBlocker": "BlockerRecorded",
    "ResolveBlocker": "BlockerResolved",
    "FulfilDispatch": "DispatchFulfilled",
    "WithdrawDispatch": "DispatchWithdrawn",
    "CompleteAttempt": "AttemptCompleted",
    "FailAttempt": "AttemptFailed",
    "RecordAttemptPartial": "PartialOutcomeRecorded",
    "PauseAttempt": "AttemptPaused",
    "ResumeAttempt": "AttemptResumed",
    "RequestAttemptStop": "AttemptStopRequested",
    "ConfirmAttemptStopped": "AttemptAbandoned",
    "SupersedeAttempt": "AttemptSuperseded",
    "RetryAttempt": "AttemptCreated",
    "RecordCheckpoint": "CheckpointRecorded",
    "RequestPause": "PauseRequested",
    "ConfirmPause": "PauseConfirmed",
    "RequestStop": "StopRequested",
    "ConfirmStop": "StopConfirmed",
    "RequestResume": "ResumeRequested",
    "QuarantineOrphan": "OrphanQuarantined",
    "RequestReview": "ReviewRequested",
    "RegisterArtefact": "ArtefactRegistered",
}


def test_c2_runtime_bindings_are_literal_including_authorized_artefact_registration():
    from research_system.schema_registry import runtime_schema_registry

    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    for command_type, event_type in SAFE_C2_COMMAND_EVENTS.items():
        command = schemas.command_binding(command_type)
        event = schemas.event_binding(event_type, command_type)
        assert command is not None, command_type
        assert event is not None, (command_type, event_type)
        assert command.schema_id == f"ars://core/command/{command_type}"
        assert event.schema_id == f"ars://core/event/{event_type}"


ARTEFACT_ID = "art_01978abc-7820-7000-8000-000000007820"


def _artefact_manifest(artefact_id: str) -> dict[str, object]:
    content = canonical_bytes(
        {
            "schema_id": "ars://evals/evaluation-run",
            "schema_version": "1.0.0",
            "outcome": "passed",
        }
    )
    return {
        "artefact_id": artefact_id,
        "aliases": [],
        "artefact_type": "evaluation_run",
        "artefact_schema_id": "ars://evals/evaluation-run",
        "artefact_schema_version": "1.0.0",
        "task_id": TASK_ID,
        "dispatch_id": DISPATCH_ID,
        "attempt_id": ATTEMPT_ID,
        "producer_actor_id": ACTORS["actor-b"],
        "producer_profile": "wp6.4-production",
        "context_packet_id": "ctx_01978abc-7821-7000-8000-000000007821",
        "created_at": "2026-08-09T20:00:00Z",
        "code_commit": "git:sha1:" + "1" * 40,
        "branch_identity": "codex/wp6-1-c2-operating-lifecycle",
        "worktree_identity": "wp6-1-c2-operating-lifecycle",
        "environment_fingerprint": "2" * 64,
        "root_id": "control",
        "relative_path": "evidence/c2-artefact.json",
        "size_bytes": len(content),
        "media_type": "application/json",
        "content_sha256": sha256_hex(content),
        "observed_at": "2026-08-09T20:00:00Z",
        "availability_check_evidence_refs": ["availability-check:c2"],
        "input_dependencies": [],
        "research_provenance": {
            "dataset_ids": [],
            "dataset_vintages": [],
            "representation_ids": [],
            "parameter_ids": [],
            "seed_ids": [],
            "sample_restriction_ids": [],
        },
        "validation": {
            "validation_record_refs": ["validation:c2"],
            "expected_contract_ids": ["06i"],
            "expected_schema_ids": ["ars://evals/evaluation-run"],
        },
        "authority": {
            "availability": "available",
            "regenerability": "non_regenerable",
            "integrity": "verified",
            "structural_validation": "passed",
            "scientific_review": "pending",
            "use_authority": "candidate",
            "accepted_scope": "release:wp6.4",
            "consumer_restrictions": [],
        },
        "operations": {
            "no_overwrite_evidence_refs": ["no-overwrite:c2"],
            "retention_class": "durable",
            "confidentiality_class": "internal",
            "external_data_constraints": [],
        },
    }


def _register_artefact_command(harness, number: int = 846) -> tuple[dict[str, object], dict[str, object]]:
    manifest = _artefact_manifest(ARTEFACT_ID)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=ARTEFACT_ID,
        command_types=("RegisterArtefact",),
    )
    return (
        _c1_command(
            _command_id(number),
            "RegisterArtefact",
            ARTEFACT_ID,
            0,
            {"new_artefact_id": ARTEFACT_ID, "manifest": manifest},
            authority_grant_id=grant_id,
        ),
        manifest,
    )


def test_public_artefact_registration_is_event_first_durable_and_replayable(tmp_path):
    harness = _c1_control_plane(tmp_path)
    command, manifest = _register_artefact_command(harness)

    receipt = harness.service.submit(command)

    assert receipt.status == "accepted", receipt
    assert harness.receipts.load(str(command["command_id"])) == receipt
    event = tuple(harness.ledger.iter_events())[-1]
    binding = harness.schemas.command_binding("RegisterArtefact")
    assert binding is not None
    identity = harness.schemas.resolve_identity(binding.schema_id, binding.schema_version)
    assert event["event_type"] == "ArtefactRegistered"
    assert event["payload"] == command["payload"]
    assert (
        event["command_schema_id"],
        event["command_schema_version"],
        event["command_schema_sha256"],
    ) == (identity.schema_id, identity.schema_version, identity.raw_bytes_sha256)
    assert harness.objects.read("artefact", ARTEFACT_ID, 1) == manifest
    index = json.loads(_c1_scoped_index_path(harness, command).read_text(encoding="utf-8"))
    assert index["receipt"]["command_id"] == command["command_id"]
    assert index["receipt"]["status"] == "accepted"

    artefact = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ARTEFACT_ID]
    assert artefact["manifest"] == manifest
    assert artefact["content_sha256"] == manifest["content_sha256"]
    assert artefact["use_authority"] == "candidate"
    assert artefact["manifest"]["authority"] == manifest["authority"]


def test_cli_register_artefact_carries_the_c2_command_through_the_real_service(tmp_path, monkeypatch, capsys):
    harness_root = tmp_path / "harness"
    harness_root.mkdir()
    harness = _c1_control_plane(harness_root)
    command, _ = _register_artefact_command(harness, 847)
    config_path = tmp_path / "binding.yaml"
    config_path.write_text("{}", encoding="utf-8")
    command_path = tmp_path / "register-artefact.json"
    command_path.write_text(json.dumps(command), encoding="utf-8")
    binding = SimpleNamespace(
        control_root=harness.ledger.control_root,
        project_id=harness.ledger.project_id,
        schema_root=REPO_ROOT / ".research-system" / "schemas",
        store_identity=harness.authority_resolver.expected_store_identity,
        origin_witness=harness.authority_resolver.approved_witness,
        origin_witness_path=harness.authority_resolver.approved_witness_path,
    )
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(cli, "LedgerAuthorityGrantResolver", lambda *args, **kwargs: harness.authority_resolver)
    monkeypatch.setattr(cli, "CommandService", lambda *args, **kwargs: harness.service)

    result = cli.main(["command", "submit", "--config", str(config_path), "--command", str(command_path)])

    assert result == 0
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"
    assert tuple(harness.ledger.iter_events())[-1]["event_type"] == "ArtefactRegistered"


@pytest.mark.parametrize(
    ("mutation", "status", "reason_code"),
    [
        ("invalid_initial_authority", "rejected", "artefact_initial_authority_invalid"),
        ("unverifiable_regenerability", "rejected", "artefact_regenerability_evidence_unavailable"),
        ("unauthorized_actor", "rejected", "lifecycle_authority_unauthorized"),
        ("stale_position", "conflict", "stream_version_conflict"),
    ],
)
def test_public_artefact_registration_failures_leave_no_domain_mutation(tmp_path, mutation, status, reason_code):
    harness = _c1_control_plane(tmp_path)
    command, _ = _register_artefact_command(harness, 848)
    if mutation == "invalid_initial_authority":
        command["payload"]["manifest"]["authority"]["use_authority"] = "accepted_for_scope"
    elif mutation == "unverifiable_regenerability":
        command["payload"]["manifest"]["authority"]["regenerability"] = "regenerable_verified"
    elif mutation == "unauthorized_actor":
        command["actor_id"] = ACTORS["actor-b"]
    else:
        command["expected_stream_version"] = 1
    before = _rejection_snapshot(harness)

    receipt = harness.service.submit(command)

    assert receipt.status == status
    assert receipt.reason_code == reason_code
    assert _rejection_snapshot(harness) == before
    assert not (harness.objects.control_root / "objects" / "artefact" / ARTEFACT_ID).exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_id", "ars://core/command/CreateTask"),
        ("schema_version", "9.9.9"),
    ],
)
def test_public_artefact_registration_rejects_mismatched_command_schema_before_mutation(tmp_path, field, value):
    harness = _c1_control_plane(tmp_path)
    command, _ = _register_artefact_command(harness, 849)
    command[field] = value
    before = _rejection_snapshot(harness)

    with pytest.raises(SchemaError):
        harness.service.submit(command)

    assert _rejection_snapshot(harness) == before
    assert not (harness.objects.control_root / "objects" / "artefact" / ARTEFACT_ID).exists()


@pytest.mark.parametrize("missing", ("index", "receipt", "both"))
def test_artefact_registration_identical_retry_repairs_committed_residue_without_new_domain_mutation(tmp_path, missing):
    harness = _c1_control_plane(tmp_path)
    command, _ = _register_artefact_command(harness, 850)
    accepted = harness.service.submit(command)
    assert accepted.status == "accepted"
    index_path = _c1_scoped_index_path(harness, command)
    receipt_path = harness.receipts.receipts_root / f"{command['command_id']}.json"
    expected_index = index_path.read_bytes()
    expected_receipt = receipt_path.read_bytes()
    if missing in {"index", "both"}:
        index_path.unlink()
    if missing in {"receipt", "both"}:
        receipt_path.unlink()
    domain = _domain_snapshot(harness)

    retried = harness.service.submit(deepcopy(command))

    assert retried == accepted
    assert _domain_snapshot(harness) == domain
    assert index_path.read_bytes() == expected_index
    assert receipt_path.read_bytes() == expected_receipt


def test_artefact_registration_changed_retry_conflicts_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    command, _ = _register_artefact_command(harness, 851)
    assert harness.service.submit(command).status == "accepted"
    changed = deepcopy(command)
    changed["payload"]["manifest"]["relative_path"] = "evidence/conflicting-artefact.json"
    domain = _domain_snapshot(harness)

    with pytest.raises(ConflictError):
        harness.service.submit(changed)

    assert _domain_snapshot(harness) == domain


def test_public_block_task_suspends_a_running_c1_task_and_replays(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(800),
        "BlockTask",
        TASK_ID,
        before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "blocker_kind": "owner_input",
            "blocker_owner": "owner:c2",
            "stop_required": False,
            "resume_condition": "owner supplies the requested decision",
            "resolution_evidence_refs": [],
        },
    )

    receipt = harness.service.submit(command)

    assert receipt.status == "accepted", receipt
    assert receipt.observed_stream_version == before.stream_versions[TASK_ID] + 1
    events = tuple(harness.ledger.iter_events())
    assert [event["event_type"] for event in events[-1:]] == ["TaskBlocked"]
    assert events[-1]["payload"] == command["payload"]
    projection = replay(events, schema_registry=harness.schemas)
    task = projection["streams"][TASK_ID]
    assert task["status"] == "blocked"
    assert task["prior_active_status"] == "in_progress"
    assert task["suspension"] == command["payload"]


def _process_disposition(state: str) -> dict[str, object]:
    return {
        "process_state": state,
        "children_closed": True,
        "writers_closed": True,
        "evidence_refs": [f"evidence:{state}"],
    }


def _submit_task_command(harness, number: int, command_type: str, payload: dict[str, object]):
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(number),
        command_type,
        TASK_ID,
        before.stream_versions[TASK_ID],
        payload,
    )
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    return command


def test_public_task_input_pause_and_resume_round_trips_restore_the_running_state(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)

    requested = _submit_task_command(
        harness,
        801,
        "RequestInput",
        {
            "task_id": TASK_ID,
            "required_authority": "owner",
            "question": "Which approved input should execution use?",
            "resume_condition": "owner records the selected input",
            "deadline": "2026-08-09T12:00:00Z",
            "recipient_actor_ids": ["owner:c2"],
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert task["status"] == "input_required"
    assert task["suspension"] == requested["payload"]

    _submit_task_command(
        harness,
        802,
        "ResumeTask",
        {
            "task_id": TASK_ID,
            "prior_active_status": "in_progress",
            "suspended_status": "input_required",
            "resolution_evidence_refs": ["evidence:input-selected"],
            "authority_evidence_refs": ["evidence:owner-authorized"],
        },
    )
    paused = _submit_task_command(
        harness,
        803,
        "PauseTask",
        {
            "task_id": TASK_ID,
            "pause_reason": "operator requested a controlled pause",
            "prior_active_status": "in_progress",
            "resumable_state_ref": "checkpoint:current",
            "process_disposition": _process_disposition("paused"),
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert task["status"] == "paused"
    assert task["suspension"] == paused["payload"]

    _submit_task_command(
        harness,
        804,
        "ResumeTask",
        {
            "task_id": TASK_ID,
            "prior_active_status": "in_progress",
            "suspended_status": "paused",
            "resolution_evidence_refs": ["evidence:pause-cleared"],
            "authority_evidence_refs": ["evidence:resume-authorized"],
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert task["status"] == "in_progress"
    assert task["last_resume"]["suspended_status"] == "paused"


def test_public_blocker_record_and_resolution_are_durable_and_replayable(tmp_path):
    harness = _c1_control_plane(tmp_path)
    blocker_id = "blk_01978abc-7801-7000-8000-000000007801"
    grant_id = activate_lifecycle_grant(harness, subject_kind="blocker", subject_id=blocker_id)
    record = _c1_command(
        _command_id(805),
        "RecordBlocker",
        blocker_id,
        0,
        {
            "new_blocker_id": blocker_id,
            "resume_condition": "the owner records the required decision",
            "blocker_kind": "owner_input",
            "owner_actor_id": ACTORS["actor-a"],
            "stop_required": False,
            "blocker_evidence_refs": ["evidence:blocker-observed"],
        },
        authority_grant_id=grant_id,
    )
    assert harness.service.submit(record).status == "accepted"
    resolve = _c1_command(
        _command_id(806),
        "ResolveBlocker",
        blocker_id,
        1,
        {
            "blocker_id": blocker_id,
            "resolution_evidence_refs": ["evidence:owner-decision"],
            "responsible_authority": "owner",
        },
        authority_grant_id=grant_id,
    )
    assert harness.service.submit(resolve).status == "accepted"

    events = tuple(harness.ledger.iter_events())
    assert [event["event_type"] for event in events[-2:]] == ["BlockerRecorded", "BlockerResolved"]
    blocker = replay(events, schema_registry=harness.schemas)["streams"][blocker_id]
    assert blocker["status"] == "resolved"
    assert blocker["record"] == record["payload"]
    assert blocker["resolution"] == resolve["payload"]


@pytest.mark.parametrize(
    ("command_type", "event_type", "status", "payload"),
    [
        (
            "CompleteAttempt",
            "AttemptCompleted",
            "completed",
            {
                "attempt_id": ATTEMPT_ID,
                "candidate_artefact_ids": ["art_01978abc-7802-7000-8000-000000007802"],
                "end_evidence_refs": ["evidence:attempt-complete"],
                "output_disposition": "retained_as_candidate",
            },
        ),
        (
            "FailAttempt",
            "AttemptFailed",
            "failed",
            {
                "attempt_id": ATTEMPT_ID,
                "end_evidence_refs": ["evidence:attempt-failed"],
                "failure_kind": "execution_error",
                "output_disposition": "quarantined",
            },
        ),
        (
            "RecordAttemptPartial",
            "PartialOutcomeRecorded",
            "partial",
            {
                "attempt_id": ATTEMPT_ID,
                "completed_obligations": ["unit:1"],
                "unmet_obligations": ["unit:2"],
                "candidate_artefact_ids": ["art_01978abc-7803-7000-8000-000000007803"],
                "stop_cause": "owner_window_closed",
                "restrictions": ["not_for_release"],
            },
        ),
    ],
)
def test_public_attempt_terminal_outcomes_are_exact_and_replayable(tmp_path, command_type, event_type, status, payload):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(807),
        command_type,
        ATTEMPT_ID,
        before.stream_versions[ATTEMPT_ID],
        payload,
    )

    receipt = harness.service.submit(command)

    assert receipt.status == "accepted", receipt
    events = tuple(harness.ledger.iter_events())
    assert events[-1]["event_type"] == event_type
    attempt = replay(events, schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["status"] == status
    assert attempt["outcome"] == events[-1]["payload"]


def _checkpoint_disposition(compatibility: str = "compatible") -> dict[str, object]:
    return {
        "checkpoint_manifest_id": "cpm_01978abc-7804-7000-8000-000000007804",
        "compatibility": compatibility,
        "evidence_refs": ["evidence:checkpoint-verified"],
    }


def _submit_attempt_command(harness, number: int, command_type: str, payload: dict[str, object]):
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(number),
        command_type,
        ATTEMPT_ID,
        before.stream_versions[ATTEMPT_ID],
        payload,
    )
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    return command


def test_public_attempt_pause_and_resume_require_compatible_checkpoint_and_active_lease(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        808,
        "PauseAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "process_disposition": _process_disposition("paused"),
            "checkpoint_disposition": _checkpoint_disposition(),
        },
    )
    _submit_attempt_command(
        harness,
        809,
        "ResumeAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "compatibility_fingerprint": "a" * 64,
            "checkpoint_disposition": _checkpoint_disposition(),
            "compatibility": "compatible",
            "lease_id": LEASE_ID,
        },
    )

    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["status"] == "running"
    assert attempt["pause"]["checkpoint_disposition"]["compatibility"] == "compatible"
    assert attempt["resume"]["lease_id"] == LEASE_ID


def test_public_attempt_stop_request_and_confirmation_are_separate_durable_transitions(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        810,
        "RequestAttemptStop",
        {
            "attempt_id": ATTEMPT_ID,
            "stop_deadline": "2026-08-09T12:00:00Z",
            "signal_plan": ["SIGTERM", "SIGKILL"],
            "checkpoint_plan": "record final compatible checkpoint",
        },
    )
    stopping = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert stopping["status"] == "stopping"
    _submit_attempt_command(
        harness,
        811,
        "ConfirmAttemptStopped",
        {
            "attempt_id": ATTEMPT_ID,
            "checkpoint_disposition": _checkpoint_disposition(),
            "process_disposition": _process_disposition("stopped"),
        },
    )
    events = tuple(harness.ledger.iter_events())
    assert [event["event_type"] for event in events[-2:]] == ["AttemptStopRequested", "AttemptAbandoned"]
    assert replay(events, schema_registry=harness.schemas)["streams"][ATTEMPT_ID]["status"] == "abandoned"


def test_public_attempt_supersession_records_distinct_later_epoch_and_evidence(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    replacement_id = "att_01978abc-7805-7000-8000-000000007805"
    command = _submit_attempt_command(
        harness,
        812,
        "SupersedeAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "replacement_attempt_id": replacement_id,
            "execution_epoch": 2,
            "retained_evidence_refs": ["evidence:supersession"],
        },
    )
    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["status"] == "superseded"
    assert attempt["supersession"] == command["payload"]


def test_public_attempt_retry_binds_new_stream_to_exact_terminal_predecessor(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        813,
        "FailAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "end_evidence_refs": ["evidence:retryable-failure"],
            "failure_kind": "transient_execution_error",
            "output_disposition": "discarded",
        },
    )
    retry_id = "att_01978abc-7806-7000-8000-000000007806"
    grant_id = activate_lifecycle_grant(harness, subject_kind="attempt", subject_id=retry_id)
    command = _c1_command(
        _command_id(814),
        "RetryAttempt",
        retry_id,
        0,
        {
            "new_attempt_id": retry_id,
            "attempt_ordinal": 2,
            "execution_epoch": 2,
            "prior_attempt_id": ATTEMPT_ID,
            "reuse_declaration": ["reuse:inputs", "reuse:checkpoint"],
            "prior_outcome": "failed",
        },
        authority_grant_id=grant_id,
    )
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    event = tuple(harness.ledger.iter_events())[-1]
    assert event["event_type"] == "AttemptCreated"
    assert event["payload"]["creation_kind"] == "retry"
    retry = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][retry_id]
    assert retry["status"] == "created"
    assert retry["prior_attempt_id"] == ATTEMPT_ID


def test_public_checkpoint_record_is_state_neutral_and_monotonic_on_the_attempt_stream(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    payload = {
        "attempt_id": ATTEMPT_ID,
        "task_id": TASK_ID,
        "task_revision": 1,
        "checkpoint_manifest_id": "cpm_01978abc-7807-7000-8000-000000007807",
        "compatibility_fingerprint": "b" * 64,
        "completed_units": 3,
        "remaining_units": 7,
        "code_config_data_seed_identities": ["c" * 64, "d" * 64],
        "resume_operation": "resume from unit four",
        "integrity_status": "verified",
        "validation_status": "passed",
        "retention_class": "project",
        "confidentiality_class": "internal",
    }
    command = _c1_command(
        _command_id(815),
        "RecordCheckpoint",
        ATTEMPT_ID,
        before.stream_versions[ATTEMPT_ID],
        payload,
    )
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt

    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["status"] == "running"
    assert attempt["latest_checkpoint"] == payload
    assert attempt["checkpoints"] == [payload]


def test_public_operator_pause_confirmation_and_resume_request_are_ordered(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        816,
        "RequestPause",
        {
            "attempt_id": ATTEMPT_ID,
            "lease_id": LEASE_ID,
            "checkpoint_deadline": "2026-08-09T12:00:00Z",
        },
    )
    requested = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert requested["status"] == "running"
    assert requested["operation_state"] == "pause_requested"
    _submit_attempt_command(
        harness,
        817,
        "ConfirmPause",
        {
            "attempt_id": ATTEMPT_ID,
            "lease_id": LEASE_ID,
            "process_disposition": _process_disposition("paused"),
            "checkpoint_disposition": _checkpoint_disposition(),
        },
    )
    _submit_attempt_command(
        harness,
        818,
        "RequestResume",
        {
            "attempt_id": ATTEMPT_ID,
            "new_execution_epoch": 2,
            "lease_id": LEASE_ID,
            "checkpoint_manifest_id": "cpm_01978abc-7804-7000-8000-000000007804",
            "compatibility": "compatible",
            "compatibility_evidence_refs": ["evidence:checkpoint-compatible"],
            "permitted_work_unit_range": ["unit:4", "unit:10"],
        },
    )
    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["status"] == "paused"
    assert attempt["operation_state"] == "resume_requested"
    assert attempt["resume_request"]["new_execution_epoch"] == 2


def test_public_operator_stop_request_confirmation_and_abandonment_are_ordered(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    stop_record_id = "stp_01978abc-7808-7000-8000-000000007808"
    _submit_attempt_command(
        harness,
        819,
        "RequestStop",
        {
            "attempt_id": ATTEMPT_ID,
            "lease_id": LEASE_ID,
            "stop_reason": "owner requested bounded shutdown",
            "stop_deadline": "2026-08-09T12:00:00Z",
            "stop_record_id": stop_record_id,
            "signals": ["SIGTERM", "SIGKILL"],
        },
    )
    _submit_attempt_command(
        harness,
        820,
        "ConfirmStop",
        {
            "attempt_id": ATTEMPT_ID,
            "lease_id": LEASE_ID,
            "stop_record_id": stop_record_id,
            "checkpoint_disposition": _checkpoint_disposition(),
            "process_disposition": _process_disposition("stopped"),
        },
    )
    confirmed = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert confirmed["status"] == "stopping"
    assert confirmed["operation_state"] == "stop_confirmed"
    _submit_attempt_command(
        harness,
        821,
        "ConfirmAttemptStopped",
        {
            "attempt_id": ATTEMPT_ID,
            "checkpoint_disposition": _checkpoint_disposition(),
            "process_disposition": _process_disposition("stopped"),
        },
    )
    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["status"] == "abandoned"


def _quarantine_payload() -> dict[str, object]:
    return {
        "attempt_id": ATTEMPT_ID,
        "consumer_restrictions": ["no_consumer_access"],
        "process_identity_id": "pid_01978abc-7809-7000-8000-000000007809",
        "artefact_id": "art_01978abc-7810-7000-8000-000000007810",
        "checkpoint_manifest_id": "cpm_01978abc-7811-7000-8000-000000007811",
        "detected_divergence": "process identity no longer owns the canonical lease",
        "canonical_tail_sha256": "e" * 64,
        "projection_sha256": "f" * 64,
        "quarantine_actions": ["isolate_process", "seal_outputs"],
        "unresolved_uncertainty": ["process_exit_time"],
    }


def test_public_orphan_quarantine_rejects_live_owner_without_mutation_then_accepts_after_release(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    live = _c1_command(
        _command_id(822),
        "QuarantineOrphan",
        ATTEMPT_ID,
        before.stream_versions[ATTEMPT_ID],
        _quarantine_payload(),
    )
    rejected = harness.service.submit(live)
    assert rejected.status == "rejected"
    assert rejected.reason_code == "live_attempt_owner"
    after_rejection = harness.ledger.snapshot()
    assert after_rejection.global_position == before.global_position
    assert after_rejection.stream_versions == before.stream_versions

    lease_version = after_rejection.stream_versions[LEASE_ID]
    assert (
        harness.service.submit(_release_lease_command(number=823, expected_stream_version=lease_version)).status
        == "accepted"
    )
    current = harness.ledger.snapshot()
    quarantine = _c1_command(
        _command_id(824),
        "QuarantineOrphan",
        ATTEMPT_ID,
        current.stream_versions[ATTEMPT_ID],
        _quarantine_payload(),
    )
    accepted = harness.service.submit(quarantine)
    assert accepted.status == "accepted", accepted
    attempt = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][ATTEMPT_ID]
    assert attempt["recovery_status"] == "quarantined"
    assert attempt["quarantine"] == quarantine["payload"]


def test_public_dispatch_fulfilment_binds_the_exact_terminal_attempt(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        825,
        "CompleteAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": ["art_01978abc-7812-7000-8000-000000007812"],
            "end_evidence_refs": ["evidence:terminal-output"],
            "output_disposition": "retained_as_candidate",
        },
    )
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(826),
        "FulfilDispatch",
        DISPATCH_ID,
        before.stream_versions[DISPATCH_ID],
        {
            "dispatch_id": DISPATCH_ID,
            "attempt_id": ATTEMPT_ID,
            "terminal_attempt_status": "completed",
            "attempt_evidence_refs": ["evidence:terminal-output"],
        },
    )
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    dispatch = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][DISPATCH_ID]
    assert dispatch["status"] == "fulfilled"
    assert dispatch["fulfilment"] == command["payload"]


def test_public_claimed_dispatch_withdrawal_requires_terminal_attempt_stop_disposition(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        827,
        "RequestAttemptStop",
        {
            "attempt_id": ATTEMPT_ID,
            "stop_deadline": "2026-08-09T12:00:00Z",
            "signal_plan": ["SIGTERM"],
            "checkpoint_plan": "seal current state",
        },
    )
    _submit_attempt_command(
        harness,
        828,
        "ConfirmAttemptStopped",
        {
            "attempt_id": ATTEMPT_ID,
            "checkpoint_disposition": _checkpoint_disposition(),
            "process_disposition": _process_disposition("stopped"),
        },
    )
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(829),
        "WithdrawDispatch",
        DISPATCH_ID,
        before.stream_versions[DISPATCH_ID],
        {
            "dispatch_id": DISPATCH_ID,
            "observed_prior_state": "claimed",
            "withdrawal_reason": "terminal attempt stopped before fulfilment",
            "attempt_stop_disposition": _process_disposition("stopped"),
        },
    )
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    dispatch = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][DISPATCH_ID]
    assert dispatch["status"] == "withdrawn"
    assert dispatch["withdrawal"] == command["payload"]


def test_public_task_cancellation_requires_terminal_attempt_and_closed_process(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        830,
        "RequestAttemptStop",
        {
            "attempt_id": ATTEMPT_ID,
            "stop_deadline": "2026-08-09T12:00:00Z",
            "signal_plan": ["SIGTERM"],
            "checkpoint_plan": "seal final state",
        },
    )
    _submit_attempt_command(
        harness,
        831,
        "ConfirmAttemptStopped",
        {
            "attempt_id": ATTEMPT_ID,
            "checkpoint_disposition": _checkpoint_disposition(),
            "process_disposition": _process_disposition("stopped"),
        },
    )
    command = _submit_task_command(
        harness,
        832,
        "CancelTask",
        {
            "task_id": TASK_ID,
            "cancellation_reason": "owner cancelled after bounded shutdown",
            "process_disposition": _process_disposition("stopped"),
            "active_attempt_dispositions": [ATTEMPT_ID],
        },
    )
    task = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert task["status"] == "cancelled"
    assert task["cancellation"] == command["payload"]


def test_public_task_review_submission_and_review_request_link_exact_terminal_subjects(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    artefact_id = "art_01978abc-7813-7000-8000-000000007813"
    review_id = "rev_01978abc-7814-7000-8000-000000007814"
    _submit_attempt_command(
        harness,
        833,
        "CompleteAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": [artefact_id],
            "end_evidence_refs": ["evidence:review-candidate"],
            "output_disposition": "retained_as_candidate",
        },
    )
    submission = _submit_task_command(
        harness,
        834,
        "SubmitForReview",
        {
            "task_id": TASK_ID,
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": [artefact_id],
            "attempt_outcome": "completed",
            "candidate_artefact_hashes": ["a" * 64],
            "requested_review_ids": [review_id],
        },
    )
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    task = projection["streams"][TASK_ID]
    attempt = projection["streams"][ATTEMPT_ID]
    assert task["status"] == "review_pending"
    assert task["review_submission"] == submission["payload"]

    grant_id = activate_lifecycle_grant(harness, subject_kind="review", subject_id=review_id)
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(835),
        "RequestReview",
        review_id,
        0,
        {
            "new_review_id": review_id,
            "review_type": "software",
            "subject_ids": [TASK_ID, ATTEMPT_ID],
            "subject_hashes": [
                sha256_hex(canonical_bytes(task)),
                sha256_hex(canonical_bytes(attempt)),
            ],
            "governing_refs": ["plan:06o", "catalogue:06d"],
            "review_questions": ["Does the exact C2 subject preserve lifecycle authority?"],
            "required_evidence_refs": ["evidence:review-candidate"],
            "required_lanes": ["software", "provenance"],
            "reviewer_capability": ["python", "event-sourcing"],
            "required_independence_grade": "independent_exact_subject",
            "visibility_policy": "owner_and_reviewer",
            "allowed_verdicts": ["accept_exact_subject", "rework_required"],
            "satisfaction_authority": "owner",
            "deadline": "2026-08-10T12:00:00Z",
            "escalation_rule": "return rework_required on any material mismatch",
        },
        authority_grant_id=grant_id,
    )
    assert before.stream_versions.get(review_id, 0) == 0
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted", receipt
    review = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][review_id]
    assert review["status"] == "requested"
    assert review["request"] == command["payload"]


def test_cli_command_submit_carries_a_c2_command_through_the_real_service(tmp_path, monkeypatch, capsys):
    harness_root = tmp_path / "harness"
    harness_root.mkdir()
    harness = _c1_control_plane(harness_root)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(836),
        "BlockTask",
        TASK_ID,
        before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "blocker_kind": "owner_input",
            "blocker_owner": "owner:c2",
            "stop_required": False,
            "resume_condition": "owner supplies the requested decision",
            "resolution_evidence_refs": [],
        },
    )
    config_path = tmp_path / "binding.yaml"
    config_path.write_text("{}", encoding="utf-8")
    command_path = tmp_path / "block-task.json"
    command_path.write_text(json.dumps(command), encoding="utf-8")
    binding = SimpleNamespace(
        control_root=harness.ledger.control_root,
        project_id=harness.ledger.project_id,
        schema_root=REPO_ROOT / ".research-system" / "schemas",
        store_identity=harness.authority_resolver.expected_store_identity,
        origin_witness=harness.authority_resolver.approved_witness,
        origin_witness_path=harness.authority_resolver.approved_witness_path,
    )
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(cli, "LedgerAuthorityGrantResolver", lambda *args, **kwargs: harness.authority_resolver)
    monkeypatch.setattr(cli, "CommandService", lambda *args, **kwargs: harness.service)

    result = cli.main(["command", "submit", "--config", str(config_path), "--command", str(command_path)])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"
    assert tuple(harness.ledger.iter_events())[-1]["event_type"] == "TaskBlocked"


@pytest.mark.parametrize("missing", ("none", "index", "receipt", "both"))
def test_c2_identical_retry_repairs_receipt_residue_without_new_domain_mutation(tmp_path, missing):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(837),
        "BlockTask",
        TASK_ID,
        before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "blocker_kind": "owner_input",
            "blocker_owner": "owner:c2",
            "stop_required": False,
            "resume_condition": "owner supplies the requested decision",
            "resolution_evidence_refs": [],
        },
    )
    accepted = harness.service.submit(command)
    assert accepted.status == "accepted"
    index_path = _c1_scoped_index_path(harness, command)
    receipt_path = harness.receipts.receipts_root / f"{command['command_id']}.json"
    expected_index = index_path.read_bytes()
    expected_receipt = receipt_path.read_bytes()
    if missing in {"index", "both"}:
        index_path.unlink()
    if missing in {"receipt", "both"}:
        receipt_path.unlink()
    domain = _domain_snapshot(harness)

    retried = harness.service.submit(deepcopy(command))

    assert retried == accepted
    assert _domain_snapshot(harness) == domain
    assert index_path.read_bytes() == expected_index
    assert receipt_path.read_bytes() == expected_receipt


def test_c2_changed_identical_identity_conflicts_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    before = harness.ledger.snapshot()
    command = _c1_command(
        _command_id(838),
        "BlockTask",
        TASK_ID,
        before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "blocker_kind": "owner_input",
            "blocker_owner": "owner:c2",
            "stop_required": False,
            "resume_condition": "owner supplies decision A",
            "resolution_evidence_refs": [],
        },
    )
    assert harness.service.submit(command).status == "accepted"
    changed = deepcopy(command)
    changed["payload"]["resume_condition"] = "owner supplies decision B"
    domain = _domain_snapshot(harness)

    with pytest.raises(ConflictError):
        harness.service.submit(changed)

    assert _domain_snapshot(harness) == domain


def test_c2_unauthorized_and_late_terminal_submissions_do_not_mutate_domain_state(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    task_before = harness.ledger.snapshot()
    unauthorized = _c1_command(
        _command_id(839),
        "BlockTask",
        TASK_ID,
        task_before.stream_versions[TASK_ID],
        {
            "task_id": TASK_ID,
            "blocker_kind": "owner_input",
            "blocker_owner": "owner:c2",
            "stop_required": False,
            "resume_condition": "owner supplies the requested decision",
            "resolution_evidence_refs": [],
        },
        actor_id=ACTORS["actor-b"],
    )
    before_rejection = _rejection_snapshot(harness)
    rejected = harness.service.submit(unauthorized)
    assert rejected.status == "rejected"
    assert _rejection_snapshot(harness) == before_rejection

    attempt_before = harness.ledger.snapshot()
    late_complete = _c1_command(
        _command_id(840),
        "CompleteAttempt",
        ATTEMPT_ID,
        attempt_before.stream_versions[ATTEMPT_ID],
        {
            "attempt_id": ATTEMPT_ID,
            "candidate_artefact_ids": ["art_01978abc-7815-7000-8000-000000007815"],
            "end_evidence_refs": ["evidence:late-completion"],
            "output_disposition": "retained_as_candidate",
        },
    )
    _submit_attempt_command(
        harness,
        841,
        "PauseAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "process_disposition": _process_disposition("paused"),
            "checkpoint_disposition": _checkpoint_disposition(),
        },
    )
    domain = _domain_snapshot(harness)
    conflicted = harness.service.submit(late_complete)
    assert conflicted.status == "conflict"
    assert conflicted.reason_code == "stream_version_conflict"
    assert _domain_snapshot(harness) == domain


def test_c2_retry_race_accepts_one_successor_and_rejects_a_competing_new_identity(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _submit_attempt_command(
        harness,
        842,
        "FailAttempt",
        {
            "attempt_id": ATTEMPT_ID,
            "end_evidence_refs": ["evidence:retry-race"],
            "failure_kind": "transient_execution_error",
            "output_disposition": "discarded",
        },
    )
    retry_ids = (
        "att_01978abc-7816-7000-8000-000000007816",
        "att_01978abc-7817-7000-8000-000000007817",
    )
    commands = []
    for number, retry_id in enumerate(retry_ids, start=843):
        grant_id = activate_lifecycle_grant(harness, subject_kind="attempt", subject_id=retry_id)
        commands.append(
            _c1_command(
                _command_id(number),
                "RetryAttempt",
                retry_id,
                0,
                {
                    "new_attempt_id": retry_id,
                    "attempt_ordinal": 2,
                    "execution_epoch": 2,
                    "prior_attempt_id": ATTEMPT_ID,
                    "reuse_declaration": ["reuse:inputs"],
                    "prior_outcome": "failed",
                },
                authority_grant_id=grant_id,
            )
        )
    assert harness.service.submit(commands[0]).status == "accepted"
    domain = _domain_snapshot(harness)

    rejected = harness.service.submit(commands[1])

    assert rejected.status == "rejected"
    assert rejected.reason_code == "attempt_already_retried"
    assert _domain_snapshot(harness) == domain
