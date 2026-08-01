from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import threading

import pytest

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.command.service import CommandService
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.projection.replay import replay
from research_system.store.ledger import EventLedger
from research_system.store.lock import CompositeWriterLock, WriterLock
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    activate_lifecycle_grant,
    control_plane,
    create_task_command,
    revoke_lifecycle_grant,
    scoped_lifecycle_grant_id,
)


TASK_ID = "tsk_01978abc-7101-7000-8000-000000007101"
COMMAND_ID = "cmd_01978abc-7102-7000-8000-000000007102"
SCOPE_A = "obj_01978abc-7201-7000-8000-000000007201"
SCOPE_B = "obj_01978abc-7202-7000-8000-000000007202"
TASK_A = "tsk_01978abc-7203-7000-8000-000000007203"
TASK_B = "tsk_01978abc-7204-7000-8000-000000007204"
GRANTS = (None,) * 9


def _record_resolver(harness, monkeypatch, *, deny: bool = False):
    """Spy on the exact resolver instance while retaining ledger semantics."""
    resolver = harness.authority_resolver
    calls: list[dict] = []
    original = resolver.resolve_command

    def recorded(**kwargs):
        calls.append(kwargs)
        if deny:
            raise ArsError("authority command denied")
        return original(**kwargs)

    monkeypatch.setattr(resolver, "resolve_command", recorded)
    return resolver, calls


def _submit(harness, command):
    command_type = command["command_type"]
    if command_type in {
        "CreateScopeDefinition",
        "AmendScopeDefinition",
        "SupersedeScopeDefinition",
    }:
        subject_kind = "scope_definition"
        subject_id = command["payload"].get(
            "new_scope_definition_id" if command_type == "CreateScopeDefinition" else "scope_definition_id"
        )
    else:
        subject_kind = "task"
        subject_id = command["payload"].get("new_task_id" if command_type == "CreateTask" else "task_id")
    command["authority_grant_id"] = activate_lifecycle_grant(
        harness,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )
    return harness.service.submit(command)


def _restarted_service(harness, *, clock=None):
    return CommandService(
        harness.service.control_root,
        EventLedger(harness.service.control_root, PROJECT_ID, harness.schemas),
        ObjectStore(harness.service.control_root),
        ReceiptStore(harness.service.control_root),
        harness.schemas,
        authority_resolver=harness.authority_resolver,
        clock=clock,
    )


def _separate_authority_resolver(harness) -> LedgerAuthorityGrantResolver:
    return LedgerAuthorityGrantResolver(
        harness.authority_root,
        PROJECT_ID,
        harness.authority_resolver.expected_store_identity,
        harness.schemas,
    )


def _command(
    command_type: str,
    command_id: str,
    idempotency_key: str,
    target_stream_id: str,
    expected_stream_version: int,
    payload: dict,
    grant_id: str | None,
) -> dict:
    command = create_task_command(
        command_id,
        idempotency_key,
        target_stream_id,
        {"title": "authority-bound command"},
    )
    command.update(
        {
            "command_type": command_type,
            "schema_id": f"ars://core/command/{command_type}",
            "expected_stream_version": expected_stream_version,
            "payload": payload,
            "authority_grant_id": grant_id,
        }
    )
    return command


def _scope_create_payload(scope_id: str) -> dict:
    return {
        "new_scope_definition_id": scope_id,
        "revision": 1,
        "members": [
            {
                "member_id": TASK_A,
                "member_kind": "task",
                "required_disposition": "accepted",
            }
        ],
        "ordering_rules": ["members complete in declared order"],
        "effective_at": "2026-07-30T12:00:00Z",
        "dependency_rules": ["all named dependencies resolve"],
        "completion_predicate": "all required members accepted",
        "amendment_authority": "synthetic-owner",
    }


def _task_definition(task_id: str, title: str, risk: object, revision: int = 1) -> dict:
    definition = deepcopy(
        create_task_command(
            "cmd_01978abc-7291-7000-8000-000000007291",
            f"authority-definition:{task_id}:{revision}",
            task_id,
            {"title": title},
        )["payload"]["definition"]
    )
    definition.update(
        {
            "task_id": task_id,
            "revision": revision,
            "title": title,
            "objective": f"Complete {title}",
            "risk_tier_request": risk,
        }
    )
    definition.pop("content_sha256", None)
    definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
    return definition


def _domain_snapshot(harness) -> tuple[tuple[dict, ...], tuple[str, ...]]:
    events = tuple(harness.ledger.iter_events())
    files = tuple(
        path.relative_to(harness.service.control_root).as_posix()
        for path in harness.service.control_root.rglob("*")
        if path.is_file() and "receipts" not in path.parts
    )
    return events, files


def test_lifecycle_authority_denial_precedes_domain_mutation(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    resolver, calls = _record_resolver(harness, monkeypatch, deny=True)
    command = create_task_command(
        COMMAND_ID,
        "wp6-1-authority-denial",
        TASK_ID,
        {"title": "Authority-bound task"},
    )
    before_events = tuple(harness.ledger.iter_events())
    before_domain_files = tuple(
        path.relative_to(harness.service.control_root).as_posix()
        for path in harness.service.control_root.rglob("*")
        if path.is_file() and "receipts" not in path.parts
    )

    receipt = _submit(harness, command)
    retry = _submit(harness, command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "lifecycle_authority_unauthorized"
    assert receipt.explanation == "authority command denied"
    assert retry == receipt
    assert len(calls) == 2
    call = calls[0]
    assert call["grant_id"] == command["authority_grant_id"]
    assert call["actor_id"] == command["actor_id"]
    assert call["actor_class"] == "human"
    assert call["command"].command_type == "CreateTask"
    assert call["command"].schema_id == command["schema_id"]
    assert call["command"].schema_version == command["schema_version"]
    assert len(call["command"].schema_sha256) == 64
    assert call["required_risk"] == "R1"
    assert call["project_id"] == PROJECT_ID
    assert call["subject_kind"] == "task"
    assert call["subject_id"] == TASK_ID
    assert tuple(harness.ledger.iter_events()) == before_events
    after_domain_files = tuple(
        path.relative_to(harness.service.control_root).as_posix()
        for path in harness.service.control_root.rglob("*")
        if path.is_file() and "receipts" not in path.parts
    )
    assert after_domain_files == before_domain_files


def test_authority_denial_precedes_domain_mutation_for_all_six_commands(tmp_path, monkeypatch):
    def new_harness(name: str):
        root = tmp_path / name
        root.mkdir()
        return control_plane(root)

    cases = []

    create_scope_harness = new_harness("create-scope")
    cases.append(
        (
            create_scope_harness,
            _command(
                "CreateScopeDefinition",
                "cmd_01978abc-7250-7000-8000-000000007250",
                "deny-create-scope",
                SCOPE_A,
                0,
                _scope_create_payload(SCOPE_A),
                GRANTS[0],
            ),
        )
    )

    amend_scope_harness = new_harness("amend-scope")
    assert (
        _submit(
            amend_scope_harness,
            _command(
                "CreateScopeDefinition",
                "cmd_01978abc-7251-7000-8000-000000007251",
                "setup-amend-scope",
                SCOPE_A,
                0,
                _scope_create_payload(SCOPE_A),
                GRANTS[1],
            ),
        ).status
        == "accepted"
    )
    cases.append(
        (
            amend_scope_harness,
            _command(
                "AmendScopeDefinition",
                "cmd_01978abc-7252-7000-8000-000000007252",
                "deny-amend-scope",
                SCOPE_A,
                1,
                {
                    "scope_definition_id": SCOPE_A,
                    "prior_revision": 1,
                    "new_revision": 2,
                    "member_changes": [
                        {
                            "member_id": TASK_A,
                            "member_kind": "task",
                            "disposition": "deferred",
                        }
                    ],
                    "changed_fields": ["members"],
                    "rationale": "Exercise denied scope amendment.",
                    "effective_boundary": "before the next dispatch",
                    "amendment_authority": "synthetic-owner",
                },
                GRANTS[2],
            ),
        )
    )

    supersede_scope_harness = new_harness("supersede-scope")
    for command_id, scope_id, grant_id in (
        (
            "cmd_01978abc-7253-7000-8000-000000007253",
            SCOPE_A,
            GRANTS[3],
        ),
        (
            "cmd_01978abc-7254-7000-8000-000000007254",
            SCOPE_B,
            GRANTS[4],
        ),
    ):
        assert (
            _submit(
                supersede_scope_harness,
                _command(
                    "CreateScopeDefinition",
                    command_id,
                    f"setup-supersede-scope:{scope_id}",
                    scope_id,
                    0,
                    _scope_create_payload(scope_id),
                    grant_id,
                ),
            ).status
            == "accepted"
        )
    cases.append(
        (
            supersede_scope_harness,
            _command(
                "SupersedeScopeDefinition",
                "cmd_01978abc-7255-7000-8000-000000007255",
                "deny-supersede-scope",
                SCOPE_A,
                1,
                {
                    "scope_definition_id": SCOPE_A,
                    "replacement_scope_definition_id": SCOPE_B,
                    "replacement_revision": 1,
                    "lineage_reason": "Exercise denied scope supersession.",
                    "member_dispositions": [
                        {
                            "member_id": TASK_A,
                            "member_kind": "task",
                            "required_disposition": "superseded",
                        }
                    ],
                    "effective_at": "2026-07-30T13:00:00Z",
                },
                GRANTS[5],
            ),
        )
    )

    create_task_harness = new_harness("create-task")
    cases.append(
        (
            create_task_harness,
            _command(
                "CreateTask",
                "cmd_01978abc-7256-7000-8000-000000007256",
                "deny-create-task",
                TASK_A,
                0,
                {"new_task_id": TASK_A, "definition": _task_definition(TASK_A, "Denied task", "R1")},
                GRANTS[6],
            ),
        )
    )

    amend_task_harness = new_harness("amend-task")
    assert (
        _submit(
            amend_task_harness,
            _command(
                "CreateTask",
                "cmd_01978abc-7257-7000-8000-000000007257",
                "setup-amend-task",
                TASK_A,
                0,
                {"new_task_id": TASK_A, "definition": _task_definition(TASK_A, "Task A", "R1")},
                GRANTS[7],
            ),
        ).status
        == "accepted"
    )
    cases.append(
        (
            amend_task_harness,
            _command(
                "AmendTask",
                "cmd_01978abc-7258-7000-8000-000000007258",
                "deny-amend-task",
                TASK_A,
                1,
                {
                    "task_id": TASK_A,
                    "prior_revision": 1,
                    "new_revision": 2,
                    "replacement_definition": _task_definition(TASK_A, "Task A amended", "R2", 2),
                    "changed_fields": ["title", "objective", "risk_tier_request"],
                    "rationale": "Exercise denied task amendment.",
                    "effective_boundary": "before redispatch",
                    "authority_evidence_refs": [scoped_lifecycle_grant_id(TASK_A)],
                },
                GRANTS[8],
            ),
        )
    )

    supersede_task_harness = new_harness("supersede-task")
    for command_id, task_id, grant_id in (
        (
            "cmd_01978abc-7259-7000-8000-000000007259",
            TASK_A,
            GRANTS[0],
        ),
        (
            "cmd_01978abc-7260-7000-8000-000000007260",
            TASK_B,
            GRANTS[1],
        ),
    ):
        assert (
            _submit(
                supersede_task_harness,
                _command(
                    "CreateTask",
                    command_id,
                    f"setup-supersede-task:{task_id}",
                    task_id,
                    0,
                    {"new_task_id": task_id, "definition": _task_definition(task_id, task_id, "R1")},
                    grant_id,
                ),
            ).status
            == "accepted"
        )
    cases.append(
        (
            supersede_task_harness,
            _command(
                "SupersedeTask",
                "cmd_01978abc-7261-7000-8000-000000007261",
                "deny-supersede-task",
                TASK_A,
                1,
                {
                    "task_id": TASK_A,
                    "replacement_task_id": TASK_B,
                    "replacement_task_revision": 1,
                    "continuing_consumer_dispositions": ["retain both for audit"],
                    "lineage_reason": "Exercise denied task supersession.",
                },
                GRANTS[2],
            ),
        )
    )

    for index, (harness, command) in enumerate(cases):
        resolver, calls = _record_resolver(harness, monkeypatch, deny=True)
        before = _domain_snapshot(harness)
        receipt = _submit(harness, command)
        assert receipt.status == "rejected", index
        assert calls[0]["command"].command_type == command["command_type"]
        assert _domain_snapshot(harness) == before


def test_all_six_lifecycle_commands_bind_exact_authority_inputs(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    resolver, calls = _record_resolver(harness, monkeypatch)

    scope_create = _command(
        "CreateScopeDefinition",
        "cmd_01978abc-7210-7000-8000-000000007210",
        "authority-scope-create",
        SCOPE_A,
        0,
        _scope_create_payload(SCOPE_A),
        GRANTS[0],
    )
    scope_amend = _command(
        "AmendScopeDefinition",
        "cmd_01978abc-7211-7000-8000-000000007211",
        "authority-scope-amend",
        SCOPE_A,
        1,
        {
            "scope_definition_id": SCOPE_A,
            "prior_revision": 1,
            "new_revision": 2,
            "member_changes": [
                {
                    "member_id": TASK_A,
                    "member_kind": "task",
                    "disposition": "deferred",
                }
            ],
            "changed_fields": ["members"],
            "rationale": "Bind the scope amendment to the authority subject.",
            "effective_boundary": "before the next task dispatch",
            "amendment_authority": "synthetic-owner",
        },
        GRANTS[1],
    )
    scope_b_create = _command(
        "CreateScopeDefinition",
        "cmd_01978abc-7212-7000-8000-000000007212",
        "authority-scope-replacement-create",
        SCOPE_B,
        0,
        _scope_create_payload(SCOPE_B),
        GRANTS[2],
    )
    scope_supersede = _command(
        "SupersedeScopeDefinition",
        "cmd_01978abc-7213-7000-8000-000000007213",
        "authority-scope-supersede",
        SCOPE_A,
        2,
        {
            "scope_definition_id": SCOPE_A,
            "replacement_scope_definition_id": SCOPE_B,
            "replacement_revision": 1,
            "lineage_reason": "Bind the scope replacement to the source scope.",
            "member_dispositions": [
                {
                    "member_id": TASK_A,
                    "member_kind": "task",
                    "required_disposition": "superseded",
                }
            ],
            "effective_at": "2026-07-30T13:00:00Z",
        },
        GRANTS[3],
    )
    task_create = _command(
        "CreateTask",
        "cmd_01978abc-7214-7000-8000-000000007214",
        "authority-task-create",
        TASK_A,
        0,
        {"new_task_id": TASK_A, "definition": _task_definition(TASK_A, "Task A", "R2")},
        GRANTS[4],
    )
    task_amend_definition = _task_definition(TASK_A, "Task A revised", "R3", revision=2)
    task_amend = _command(
        "AmendTask",
        "cmd_01978abc-7215-7000-8000-000000007215",
        "authority-task-amend",
        TASK_A,
        1,
        {
            "task_id": TASK_A,
            "prior_revision": 1,
            "new_revision": 2,
            "replacement_definition": task_amend_definition,
            "changed_fields": ["title", "objective", "risk_tier_request"],
            "rationale": "Bind the task amendment to the current revision.",
            "effective_boundary": "before redispatch",
            "authority_evidence_refs": [scoped_lifecycle_grant_id(TASK_A)],
        },
        GRANTS[5],
    )
    task_b_create = _command(
        "CreateTask",
        "cmd_01978abc-7216-7000-8000-000000007216",
        "authority-task-replacement-create",
        TASK_B,
        0,
        {"new_task_id": TASK_B, "definition": _task_definition(TASK_B, "Task B", "R1")},
        GRANTS[6],
    )
    task_supersede = _command(
        "SupersedeTask",
        "cmd_01978abc-7217-7000-8000-000000007217",
        "authority-task-supersede",
        TASK_A,
        2,
        {
            "task_id": TASK_A,
            "replacement_task_id": TASK_B,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["audit retains both immutable revisions"],
            "lineage_reason": "Bind the task replacement to the current source revision.",
        },
        GRANTS[7],
    )

    for command in (
        scope_create,
        scope_amend,
        scope_b_create,
        scope_supersede,
        task_create,
        task_amend,
        task_b_create,
        task_supersede,
    ):
        receipt = _submit(harness, command)
        assert receipt.status == "accepted", command["command_type"]

    assert [call["command"].command_type for call in calls] == [
        "CreateScopeDefinition",
        "AmendScopeDefinition",
        "CreateScopeDefinition",
        "SupersedeScopeDefinition",
        "CreateTask",
        "AmendTask",
        "CreateTask",
        "SupersedeTask",
    ]
    assert [call["required_risk"] for call in calls] == [
        "R3",
        "R3",
        "R3",
        "R3",
        "R2",
        "R3",
        "R1",
        "R3",
    ]
    for call in calls:
        identity = call["command"]
        assert identity.schema_id == f"ars://core/command/{identity.command_type}"
        assert identity.schema_version == "1.0.0"
        assert len(identity.schema_sha256) == 64
        assert call["actor_class"] == "human"
        assert call["project_id"] == PROJECT_ID
        assert call["subject_kind"] in {"scope_definition", "task"}
        assert call["subject_id"] in {SCOPE_A, SCOPE_B, TASK_A, TASK_B}

    events = tuple(harness.ledger.iter_events())
    assert len(events) == 8
    replayed = replay(events, schema_registry=harness.service.schemas)
    assert replayed["streams"][SCOPE_A]["status"] == "superseded"
    assert replayed["streams"][TASK_A]["status"] == "superseded"


def test_task_risk_binding_uses_current_and_replacement_max_and_fails_closed(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    _, calls = _record_resolver(harness, monkeypatch)

    create = _command(
        "CreateTask",
        "cmd_01978abc-7220-7000-8000-000000007220",
        "authority-risk-create",
        TASK_A,
        0,
        {"new_task_id": TASK_A, "definition": _task_definition(TASK_A, "Risk task", "R2")},
        GRANTS[0],
    )
    assert _submit(harness, create).status == "accepted"

    amend_definition = _task_definition(TASK_A, "Risk task amended", "R1", revision=2)
    amend = _command(
        "AmendTask",
        "cmd_01978abc-7221-7000-8000-000000007221",
        "authority-risk-amend",
        TASK_A,
        1,
        {
            "task_id": TASK_A,
            "prior_revision": 1,
            "new_revision": 2,
            "replacement_definition": amend_definition,
            "changed_fields": ["title", "objective", "risk_tier_request"],
            "rationale": "Retain the higher current risk ceiling.",
            "effective_boundary": "before redispatch",
            "authority_evidence_refs": [scoped_lifecycle_grant_id(TASK_A)],
        },
        GRANTS[1],
    )
    assert _submit(harness, amend).status == "accepted"

    malformed = _task_definition(TASK_B, "Malformed risk task", "not-a-risk-tier")
    create_malformed = _command(
        "CreateTask",
        "cmd_01978abc-7222-7000-8000-000000007222",
        "authority-risk-malformed-create",
        TASK_B,
        0,
        {"new_task_id": TASK_B, "definition": malformed},
        GRANTS[2],
    )
    assert _submit(harness, create_malformed).status == "accepted"

    supersede = _command(
        "SupersedeTask",
        "cmd_01978abc-7223-7000-8000-000000007223",
        "authority-risk-supersede",
        TASK_A,
        2,
        {
            "task_id": TASK_A,
            "replacement_task_id": TASK_B,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["retain both for audit"],
            "lineage_reason": "Malformed replacement risk must fail closed as R3.",
        },
        GRANTS[3],
    )
    assert _submit(harness, supersede).status == "accepted"

    assert [call["required_risk"] for call in calls] == ["R2", "R2", "R3", "R3"]


def test_non_owner_actor_class_is_unproven_and_denied_before_domain_mutation(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    _, calls = _record_resolver(harness, monkeypatch)
    command = create_task_command(
        "cmd_01978abc-7230-7000-8000-000000007230",
        "authority-unproven-actor",
        TASK_A,
        {"title": "Unproven actor task"},
    )
    command["actor_id"] = ACTORS["actor-b"]
    before = _domain_snapshot(harness)

    receipt = _submit(harness, command)

    assert receipt.status == "rejected"
    assert calls[0]["actor_class"] == "unproven"
    assert _domain_snapshot(harness) == before
    replayed = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.service.schemas)
    assert replayed["streams"] == {}
    assert replayed.get("authority_grants", {}) == {}
    assert replayed.get("authority_administration_decisions", {}) == {}


def test_authority_evidence_is_durable_for_retry_and_conflicts_on_change(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    resolver, calls = _record_resolver(harness, monkeypatch)
    command = create_task_command(
        "cmd_01978abc-7240-7000-8000-000000007240",
        "authority-evidence-retry",
        TASK_A,
        {"title": "Evidence-bound task"},
    )
    first = _submit(harness, command)
    before_retry_events = tuple(harness.ledger.iter_events())
    restarted = _restarted_service(harness)
    second = restarted.submit(command)

    assert first.status == "accepted"
    assert second == first
    assert len(calls) == 2
    assert tuple(harness.ledger.iter_events()) == before_retry_events
    resolution = resolver.scoped_grant_identity(command["authority_grant_id"])
    event = before_retry_events[0]
    assert event["authority_grant_id"] == resolution.authority_grant_id
    assert event["actor_id"] == resolution.actor_id

    changed_payload = deepcopy(command)
    changed_payload["command_id"] = "cmd_01978abc-7241-7000-8000-000000007241"
    changed_payload["payload"]["definition"]["title"] = "Changed payload"
    with pytest.raises(ConflictError, match="idempotency key conflicts"):
        restarted.submit(changed_payload)
    assert tuple(harness.ledger.iter_events()) == before_retry_events

    revoke_lifecycle_grant(harness, subject_id=TASK_A)
    revoked_retry = restarted.submit(command)
    assert revoked_retry.status == "rejected"
    assert revoked_retry.reason_code == "lifecycle_authority_unauthorized"
    assert tuple(harness.ledger.iter_events()) == before_retry_events


def test_default_revocation_decision_ids_are_unique_per_grant(tmp_path):
    harness = control_plane(tmp_path)
    activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_A,
    )
    activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_B,
    )

    revoke_lifecycle_grant(harness, subject_id=TASK_A)
    revoke_lifecycle_grant(harness, subject_id=TASK_B)

    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (harness.authority_root / "objects" / "assurance_record").rglob("*.json")
    ]
    revocations = [record for record in records if record.get("action") == "revoke_issued_authority_grant"]
    assert len(revocations) == 2
    assert len({record["record_id"] for record in revocations}) == 2
    assert all(record["record_id"].startswith("arec_") for record in revocations)


def test_control_plane_clock_override_is_shared_by_domain_and_authority_services(tmp_path):
    expected = datetime(2031, 1, 1, tzinfo=UTC)
    harness = control_plane(tmp_path, clock=lambda: expected)

    assert harness.service.clock() == expected
    assert harness.authority_service.clock() == expected


def test_lifecycle_submit_reuses_one_authority_projection(tmp_path, monkeypatch):
    harness = control_plane(tmp_path, auto_authority=False)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_A,
    )
    command = create_task_command(
        "cmd_01978abc-7247-7000-8000-000000007247",
        "authority-projection-reuse",
        TASK_A,
        {"title": "Projection reuse"},
    )
    command["authority_grant_id"] = grant_id
    resolver = harness.authority_resolver
    original_projection = resolver._projection
    calls = 0

    def counted_projection():
        nonlocal calls
        calls += 1
        return original_projection()

    monkeypatch.setattr(resolver, "_projection", counted_projection)
    receipt = harness.service.submit(command)

    assert receipt.status == "accepted"
    assert calls == 1
    assert tuple(harness.ledger.iter_events())


def test_cross_store_revocation_cannot_commit_between_projection_and_domain_append(tmp_path, monkeypatch):
    harness = control_plane(tmp_path, auto_authority=False)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_A,
    )
    command = create_task_command(
        "cmd_01978abc-7260-7000-8000-000000007260",
        "cross-store-linearization",
        TASK_A,
        {"title": "Cross-store linearization"},
    )
    command["authority_grant_id"] = grant_id
    domain_resolver = _separate_authority_resolver(harness)
    harness.service.authority_resolver = domain_resolver
    original_projection = domain_resolver._projection
    projection_ready = threading.Event()
    release_projection = threading.Event()
    revocation_attempted = threading.Event()
    revocation_prepare_entered = threading.Event()
    revocation_committed = threading.Event()
    results: dict[str, object] = {}
    errors: list[BaseException] = []
    order: list[str] = []

    def paused_projection():
        projection = original_projection()
        projection_ready.set()
        if not release_projection.wait(2):
            raise AssertionError("projection barrier was not released")
        return projection

    monkeypatch.setattr(domain_resolver, "_projection", paused_projection)
    original_prepare = harness.authority_service._prepare_issued_authority_revocation

    def observed_revocation_prepare(command_value, observed_version):
        revocation_prepare_entered.set()
        return original_prepare(command_value, observed_version)

    monkeypatch.setattr(
        harness.authority_service,
        "_prepare_issued_authority_revocation",
        observed_revocation_prepare,
    )

    def submit_domain() -> None:
        try:
            results["domain"] = harness.service.submit(command)
            order.append("domain")
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def revoke() -> None:
        revocation_attempted.set()
        while not revocation_committed.is_set():
            try:
                results["revocation"] = revoke_lifecycle_grant(
                    harness,
                    subject_id=TASK_A,
                )
            except ConflictError:
                threading.Event().wait(0.001)
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)
                return
            else:
                order.append("revocation")
                revocation_committed.set()

    domain_thread = threading.Thread(target=submit_domain)
    revocation_thread = threading.Thread(target=revoke)
    domain_thread.start()
    assert projection_ready.wait(2)
    revocation_thread.start()
    try:
        assert revocation_attempted.wait(2)
        assert not revocation_prepare_entered.wait(0.2)
        assert not any(
            event["command_type"] == "RevokeIssuedAuthorityGrant" for event in harness.authority_ledger.iter_events()
        )
    finally:
        release_projection.set()
        domain_thread.join(4)
        revocation_thread.join(4)

    assert not domain_thread.is_alive()
    assert not revocation_thread.is_alive()
    assert errors == []
    assert results["domain"].status == "accepted"
    assert results["revocation"] == grant_id
    assert order == ["domain", "revocation"]


def test_cross_store_revocation_wins_first_rejects_without_domain_mutation_and_retries(
    tmp_path,
    monkeypatch,
):
    harness = control_plane(tmp_path, auto_authority=False)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_B,
    )
    command = create_task_command(
        "cmd_01978abc-7261-7000-8000-000000007261",
        "cross-store-revocation-first",
        TASK_B,
        {"title": "Cross-store revocation first"},
    )
    command["authority_grant_id"] = grant_id
    domain_resolver = _separate_authority_resolver(harness)
    harness.service.authority_resolver = domain_resolver
    original_projection = domain_resolver._projection
    projection_entered = threading.Event()
    authority_locked = threading.Event()
    release_authority = threading.Event()
    results: dict[str, object] = {}
    errors: list[BaseException] = []
    before_domain = _domain_snapshot(harness)

    def observed_projection():
        projection_entered.set()
        return original_projection()

    monkeypatch.setattr(domain_resolver, "_projection", observed_projection)
    original_prepare = harness.authority_service._prepare_issued_authority_revocation

    def paused_revocation(command_value, observed_version):
        authority_locked.set()
        if not release_authority.wait(2):
            raise AssertionError("authority barrier was not released")
        return original_prepare(command_value, observed_version)

    monkeypatch.setattr(
        harness.authority_service,
        "_prepare_issued_authority_revocation",
        paused_revocation,
    )

    def revoke() -> None:
        try:
            results["revocation"] = revoke_lifecycle_grant(
                harness,
                subject_id=TASK_B,
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def submit_domain() -> None:
        try:
            results["domain"] = harness.service.submit(command)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    revocation_thread = threading.Thread(target=revoke)
    domain_thread = threading.Thread(target=submit_domain)
    revocation_thread.start()
    assert authority_locked.wait(2)
    domain_thread.start()
    try:
        assert not projection_entered.wait(0.2)
    finally:
        release_authority.set()
        revocation_thread.join(4)
        domain_thread.join(4)

    assert not revocation_thread.is_alive()
    assert not domain_thread.is_alive()
    assert errors == []
    assert results["revocation"] == grant_id
    rejected = results["domain"]
    assert rejected.status == "rejected"
    assert rejected.reason_code == "lifecycle_authority_unauthorized"
    assert _domain_snapshot(harness) == before_domain
    assert harness.receipts.load(command["command_id"]) is None

    retry = harness.service.submit(command)
    assert retry == rejected
    assert _domain_snapshot(harness) == before_domain


def test_composite_writer_lock_deduplicates_roots_and_has_bounded_conflict_cleanup(tmp_path):
    same_root = tmp_path / "same"
    first_root = tmp_path / "a"
    second_root = tmp_path / "b"
    for root in (same_root, first_root, second_root):
        (root / "runtime").mkdir(parents=True)

    same = CompositeWriterLock(
        (same_root, same_root),
        {"command_id": "cmd_01978abc-7262-7000-8000-000000007262"},
    )
    with same:
        assert len(same.paths) == 1
        assert same.locked_root(same_root).runtime_final_path == same.paths[0].parent

    candidate = CompositeWriterLock(
        (first_root, second_root),
        {"command_id": "cmd_01978abc-7264-7000-8000-000000007264"},
    )
    ordered_members = tuple(candidate._members)
    ordered_lock_paths = tuple(member.representative.runtime_final_path / "writer.lock" for member in ordered_members)
    blocker = WriterLock(
        ordered_lock_paths[-1],
        {"command_id": "cmd_01978abc-7263-7000-8000-000000007263"},
    )
    with blocker:
        with pytest.raises(ConflictError, match="writer lock exists"):
            with candidate:
                pass
        assert all(not path.exists() for path in ordered_lock_paths[:-1])

    roots = (second_root, first_root)
    first = CompositeWriterLock(
        roots,
        {"command_id": "cmd_01978abc-7265-7000-8000-000000007265"},
    )
    second = CompositeWriterLock(
        tuple(reversed(roots)),
        {"command_id": "cmd_01978abc-7266-7000-8000-000000007266"},
    )
    with first:
        first_order = tuple(locked.identity for locked in first._locked_roots)
        first_paths = first.paths
    with second:
        second_order = tuple(locked.identity for locked in second._locked_roots)
    assert second_order == first_order
    entered = threading.Event()
    release = threading.Event()
    outcomes: list[str] = []
    errors: list[BaseException] = []

    def hold() -> None:
        try:
            with first:
                entered.set()
                if not release.wait(2):
                    raise AssertionError("lock holder barrier was not released")
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def contend() -> None:
        if not entered.wait(2):
            errors.append(AssertionError("lock contender did not observe holder"))
            return
        try:
            with second:
                outcomes.append("acquired")
        except ConflictError:
            outcomes.append("conflict")

    holder = threading.Thread(target=hold)
    contender = threading.Thread(target=contend)
    holder.start()
    contender.start()
    contender.join(2)
    assert not contender.is_alive()
    assert outcomes == ["conflict"]
    assert holder.is_alive()
    release.set()
    holder.join(2)
    assert not holder.is_alive()
    assert errors == []
    assert all(not path.exists() for path in first_paths)


def test_composite_writer_lock_deduplicates_physical_windows_aliases(tmp_path):
    root = tmp_path / "physical-root"
    (root / "runtime").mkdir(parents=True)
    aliases = [root, root.resolve(), Path(os.path.relpath(root, Path.cwd()))]
    if os.name == "nt":
        aliases.append(Path(str(root).swapcase()))
        aliases.append(Path("\\\\?\\" + str(root.resolve())))

    first = CompositeWriterLock(
        aliases,
        {"command_id": "cmd_01978abc-7267-7000-8000-000000007267"},
    )
    second = CompositeWriterLock(
        tuple(reversed(aliases)),
        {"command_id": "cmd_01978abc-7268-7000-8000-000000007268"},
    )

    with first:
        first_paths = first.paths
        first_order = tuple(locked.identity for locked in first._locked_roots)
    with second:
        assert len(second.paths) == 1
        assert second.paths == first_paths
        assert tuple(locked.identity for locked in second._locked_roots) == first_order


def test_composite_writer_lock_deduplicates_reparse_alias_when_available(tmp_path):
    root = tmp_path / "reparse-target"
    alias = tmp_path / "reparse-alias"
    (root / "runtime").mkdir(parents=True)
    try:
        alias.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink/reparse creation unavailable on this host")

    lock = CompositeWriterLock(
        (root, alias),
        {"command_id": "cmd_01978abc-7269-7000-8000-000000007269"},
    )

    with lock:
        assert len(lock.paths) == 1


@pytest.mark.parametrize("replace_position", [0, 1])
def test_composite_writer_lock_rejects_each_member_replacement_before_acquisition(
    tmp_path,
    replace_position,
):
    roots = (tmp_path / "member-a", tmp_path / "member-b")
    for root in roots:
        (root / "runtime").mkdir(parents=True)

    candidate = CompositeWriterLock(
        roots,
        {"command_id": f"cmd_01978abc-7270-7000-8000-00000000727{replace_position}"},
    )
    saved = tmp_path / f"member-{replace_position}-saved"
    roots[replace_position].rename(saved)
    (roots[replace_position] / "runtime").mkdir(parents=True)

    with pytest.raises(ConflictError, match="identity|existing directory"):
        with candidate:
            raise AssertionError("protected callback ran after root replacement")

    for location in (*roots, saved):
        assert not (location / "runtime" / "writer.lock").exists()


@pytest.mark.parametrize("replace_position", [0, 1])
def test_composite_writer_lock_final_fence_rejects_reparse_replacement_and_cleans_siblings(
    tmp_path,
    replace_position,
    monkeypatch,
):
    targets = (tmp_path / "target-a", tmp_path / "target-b")
    aliases = (tmp_path / "alias-a", tmp_path / "alias-b")
    for target, alias in zip(targets, aliases):
        (target / "runtime").mkdir(parents=True)
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            pytest.skip("directory reparse creation unavailable on this host")
    replacement = tmp_path / f"replacement-{replace_position}"
    (replacement / "runtime").mkdir(parents=True)

    supplied = (aliases[replace_position], targets[1 - replace_position])
    candidate = CompositeWriterLock(
        supplied,
        {"command_id": f"cmd_01978abc-7271-7000-8000-00000000727{replace_position}"},
    )
    original_fence = candidate._final_fence
    protected_calls: list[str] = []

    def replace_alias_before_fence(acquired):
        aliases[replace_position].unlink()
        aliases[replace_position].symlink_to(replacement, target_is_directory=True)
        return original_fence(acquired)

    monkeypatch.setattr(candidate, "_final_fence", replace_alias_before_fence)
    with pytest.raises(ConflictError, match="alias changed"):
        with candidate:
            protected_calls.append("ran")

    assert protected_calls == []
    for location in (*targets, *aliases, replacement):
        assert not (location / "runtime" / "writer.lock").exists()


@pytest.mark.parametrize("replace_position", [0, 1])
def test_composite_writer_lock_rejects_reparse_replacement_after_anchor_before_lock(
    tmp_path,
    replace_position,
):
    targets = (tmp_path / "anchor-target-a", tmp_path / "anchor-target-b")
    aliases = (tmp_path / "anchor-alias-a", tmp_path / "anchor-alias-b")
    for target, alias in zip(targets, aliases):
        (target / "runtime").mkdir(parents=True)
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            pytest.skip("directory reparse creation unavailable on this host")
    replacement = tmp_path / f"anchor-replacement-{replace_position}"
    (replacement / "runtime").mkdir(parents=True)
    supplied = (aliases[replace_position], targets[1 - replace_position])
    replacement_seen = False

    def lock_factory(path, identity):
        nonlocal replacement_seen
        if not replacement_seen and path.parent.parent.name == targets[replace_position].name:
            aliases[replace_position].unlink()
            aliases[replace_position].symlink_to(replacement, target_is_directory=True)
            replacement_seen = True
        return WriterLock(path, identity)

    candidate = CompositeWriterLock(
        supplied,
        {"command_id": f"cmd_01978abc-7273-7000-8000-00000000727{replace_position}"},
        lock_factory=lock_factory,
    )
    with pytest.raises(ConflictError, match="alias changed"):
        with candidate:
            raise AssertionError("protected callback ran after anchor replacement")

    assert replacement_seen
    for location in (*targets, *aliases, replacement):
        assert not (location / "runtime" / "writer.lock").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows directory-handle replacement control")
@pytest.mark.parametrize("held_name", ["root", "runtime"])
def test_composite_writer_lock_held_directories_reject_ordinary_replacement_before_callback(
    tmp_path,
    held_name,
    monkeypatch,
):
    root = tmp_path / "held-root"
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    candidate = CompositeWriterLock(
        (root,),
        {"command_id": f"cmd_01978abc-7270-7000-8000-00000000727{held_name[0]}"},
    )
    held = root if held_name == "root" else runtime
    replacement = tmp_path / f"{held_name}-replacement"
    protected_calls: list[str] = []

    def fence(_acquired):
        try:
            os.replace(held, replacement)
        except OSError:
            pass
        else:  # pragma: no cover - a passing replacement is the defect
            replacement.rename(held)
            raise AssertionError(f"held {held_name} directory was replaceable")
        raise ConflictError("test final fence stopped before protected work")

    monkeypatch.setattr(candidate, "_final_fence", fence)
    with pytest.raises(ConflictError, match="test final fence"):
        with candidate:
            protected_calls.append("ran")

    assert protected_calls == []
    assert not replacement.exists()


def test_submission_lock_yields_the_acquired_composite_lease(tmp_path):
    from types import SimpleNamespace

    root = tmp_path / "submission-root"
    (root / "runtime").mkdir(parents=True)
    service = object.__new__(CommandService)
    service.control_root = root
    service.release_lock_timeout_seconds = 1.0
    service._monotonic = lambda: 0.0
    service._lock_wait = lambda _seconds: None
    command = SimpleNamespace(
        command_id="cmd_01978abc-7272-7000-8000-000000007272",
        envelope={"command_type": "UncoordinatedProbe"},
    )

    with service._submission_lock(command) as lease:
        assert isinstance(lease, CompositeWriterLock)
        assert lease.locked_root(root).identity == lease._locked_roots[0].identity


def test_missing_lifecycle_index_rebuilds_only_after_canonical_history_join(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    command = create_task_command(
        "cmd_01978abc-7244-7000-8000-000000007244",
        "authority-index-rebuild",
        TASK_A,
        {"title": "Canonical history rebuild"},
    )
    first = _submit(harness, command)
    assert first.status == "accepted"

    grant_id = command["authority_grant_id"]
    resolver = harness.authority_resolver
    canonical_calls: list[str] = []
    original_identity = resolver.scoped_grant_identity

    def record_canonical_identity(requested_grant_id: str, **kwargs):
        canonical_calls.append(requested_grant_id)
        return original_identity(requested_grant_id, **kwargs)

    monkeypatch.setattr(resolver, "scoped_grant_identity", record_canonical_identity)
    index_paths = tuple(harness.receipts.index_root.glob("*.json"))
    assert len(index_paths) == 1
    index_path = index_paths[0]
    index_path.unlink()
    before_events = tuple(harness.ledger.iter_events())

    restarted = _restarted_service(harness)
    retry = restarted.submit(command)

    assert retry == first
    assert canonical_calls == [grant_id]
    assert index_path.exists()
    assert tuple(harness.ledger.iter_events()) == before_events


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("missing", "object revision must resolve exactly once"),
        ("tampered", "object revision filename hash mismatch"),
        ("ambiguous", "object revision must resolve exactly once"),
        ("hash-mismatched", "owner authority administration decision evidence mismatch"),
    ],
)
def test_missing_lifecycle_index_fails_closed_without_canonical_authority_evidence(
    tmp_path,
    failure,
    reason,
):
    harness = control_plane(tmp_path)
    command = create_task_command(
        "cmd_01978abc-7245-7000-8000-000000007245",
        f"authority-index-{failure}",
        TASK_A,
        {"title": "Canonical history failure"},
    )
    first = _submit(harness, command)
    assert first.status == "accepted"
    index_path = next(harness.receipts.index_root.glob("*.json"))
    index_path.unlink()
    grant_path = next(
        (harness.authority_root / "objects" / "authority_grant" / command["authority_grant_id"]).glob("*.json")
    )
    if failure == "missing":
        grant_path.unlink()
    elif failure == "tampered":
        tampered = json.loads(grant_path.read_text(encoding="utf-8"))
        tampered["actor_id"] = ACTORS["actor-b"]
        grant_path.write_bytes(canonical_bytes(tampered))
    elif failure == "ambiguous":
        duplicate = grant_path.with_name(f"00000001-{'f' * 64}.json")
        duplicate.write_bytes(grant_path.read_bytes())
    else:
        activation_path = next(
            path
            for path in (harness.authority_root / "events" / PROJECT_ID).rglob("*.jsonl")
            if '"ActivateAuthorityGrant"' in path.read_text(encoding="utf-8")
        )
        original_lines = activation_path.read_bytes().splitlines(keepends=True)
        activation_path.write_bytes(b"".join((*original_lines, b"\n")))
        lines = activation_path.read_bytes().splitlines(keepends=True)
        target_index = next(index for index, line in enumerate(lines) if b'"ActivateAuthorityGrant"' in line)
        activation = json.loads(lines[target_index].decode("utf-8"))
        activation["payload"]["activated_grant_sha256"] = "f" * 64
        activation.pop("event_hash")
        activation["event_hash"] = sha256_hex(canonical_bytes(activation))
        line_ending = b"\r\n" if lines[target_index].endswith(b"\r\n") else b"\n"
        lines[target_index] = canonical_bytes(activation) + line_ending
        activation_path.write_bytes(b"".join(lines))
        assert len(lines) == len(original_lines) + 1
        assert all(
            line == before
            for index, (line, before) in enumerate(zip(lines, [*original_lines, b"\n"]))
            if index != target_index
        )
    before = _domain_snapshot(harness)
    before_receipts = tuple(harness.receipts.receipts_root.glob("*.json"))
    restarted = _restarted_service(harness)

    with pytest.raises(IntegrityError, match=reason):
        restarted.submit(command)

    assert _domain_snapshot(harness) == before
    assert tuple(harness.receipts.receipts_root.glob("*.json")) == before_receipts
    assert not index_path.exists()


def test_lifecycle_resolution_hash_must_match_canonical_history_before_append(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_A,
    )
    command = create_task_command(
        "cmd_01978abc-7246-7000-8000-000000007246",
        "authority-hash-mismatch",
        TASK_A,
        {"title": "Hash mismatch"},
    )
    command["authority_grant_id"] = grant_id
    resolver = harness.authority_resolver
    original_resolve_command = resolver.resolve_command

    def forged_resolution(**kwargs):
        resolved = original_resolve_command(**kwargs)
        return replace(resolved, authority_grant_sha256="f" * 64)

    monkeypatch.setattr(resolver, "resolve_command", forged_resolution)
    before = _domain_snapshot(harness)

    with pytest.raises(IntegrityError, match="disagrees with canonical history"):
        harness.service.submit(command)

    assert _domain_snapshot(harness) == before
    assert not tuple(harness.receipts.index_root.glob("*.json"))


def test_lifecycle_receipt_hash_check_uses_an_independent_canonical_value(tmp_path):
    harness = control_plane(tmp_path)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_A,
    )
    command = create_task_command(
        "cmd_01978abc-7248-7000-8000-000000007248",
        "authority-independent-hash",
        TASK_A,
        {"title": "Independent hash"},
    )
    command["authority_grant_id"] = grant_id
    first = harness.service.submit(command)
    assert first.status == "accepted"
    event = tuple(harness.ledger.iter_events())[-1]
    command_schema = harness.service.schemas.resolve_identity(
        "ars://core/command/CreateTask",
        "1.0.0",
    )
    canonical = harness.service._canonical_lifecycle_resolution(grant_id)
    forged = {**canonical, "authority_grant_sha256": "f" * 64}
    projection = harness.authority_resolver._projection()

    with pytest.raises(IntegrityError, match="canonical grant hash"):
        harness.service._validate_lifecycle_authority_history(
            Command(command),
            command_schema=command_schema,
            receipt=first,
            resolution=forged,
            event=event,
            authority_projection=projection,
        )


def test_restart_rejects_currently_expired_lifecycle_grant(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(
        "cmd_01978abc-7243-7000-8000-000000007243",
        "authority-evidence-expiry",
        TASK_A,
        {"title": "Expiry-bound task"},
    )
    assert _submit(harness, command).status == "accepted"
    expired = _restarted_service(
        harness,
        clock=lambda: datetime(2031, 1, 1, tzinfo=UTC),
    )
    retry = expired.submit(command)
    assert retry.status == "rejected"
    assert retry.reason_code == "lifecycle_authority_unauthorized"


def test_lifecycle_service_rejects_resolver_substitution(tmp_path):
    harness = control_plane(tmp_path)
    with pytest.raises(TypeError, match="LedgerAuthorityGrantResolver"):
        CommandService(
            harness.service.control_root,
            harness.ledger,
            harness.objects,
            harness.receipts,
            harness.schemas,
            authority_resolver=object(),
        )
