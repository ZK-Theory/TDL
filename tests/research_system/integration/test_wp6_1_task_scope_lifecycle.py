from __future__ import annotations

from copy import deepcopy

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError, SchemaError
from research_system.projection.replay import replay
from research_system.schema_registry import cached_schema_registry
from research_system.store.ledger import EventLedger
from tests.research_system.factories import (
    AUTHORITY_GRANT_ID,
    PROJECT_ID,
    REPO_ROOT,
    control_plane,
    create_task_command,
    scoped_lifecycle_grant_id,
)


SCOPE_A = "obj_01978abc-6101-7000-8000-000000006101"
SCOPE_B = "obj_01978abc-6102-7000-8000-000000006102"
SCOPE_C = "obj_01978abc-6103-7000-8000-000000006103"
TASK_A = "tsk_01978abc-6201-7000-8000-000000006201"
TASK_B = "tsk_01978abc-6202-7000-8000-000000006202"
TASK_C = "tsk_01978abc-6203-7000-8000-000000006203"

COMMAND_EVENT_PAIRS = {
    "CreateScopeDefinition": "ScopeDefinitionCreated",
    "AmendScopeDefinition": "ScopeDefinitionAmended",
    "SupersedeScopeDefinition": "ScopeDefinitionSuperseded",
    "CreateTask": "TaskCreated",
    "AmendTask": "TaskAmended",
    "SupersedeTask": "TaskSuperseded",
}


def _command(
    command_id: str,
    command_type: str,
    target_stream_id: str,
    expected_stream_version: int,
    payload: dict,
) -> dict:
    command = create_task_command(
        command_id,
        f"wp6-1:{command_type}:{command_id}",
        target_stream_id,
        {"title": "Envelope template"},
    )
    command["command_type"] = command_type
    command["schema_id"] = f"ars://core/command/{command_type}"
    command["expected_stream_version"] = expected_stream_version
    command["payload"] = payload
    return command


def _append_exact_event(
    harness,
    *,
    command_id: str,
    command_type: str,
    event_type: str,
    stream_id: str,
    payload: dict,
    provenance_command_type: str | None = None,
    provenance_schema_type: str | None = None,
    command_payload_hash: str | None = None,
    command_schema_sha256: str | None = None,
) -> None:
    recorded_command_type = provenance_command_type or command_type
    recorded_schema_type = provenance_schema_type or command_type
    template = create_task_command(
        command_id,
        f"raw-event:{command_type}:{command_id}",
        stream_id,
        {"title": "Raw exact event"},
    )
    command_identity = harness.service.schemas.resolve_identity(
        f"ars://core/command/{recorded_schema_type}",
        "1.0.0",
    )
    event_identity = harness.service.schemas.resolve_identity(
        f"ars://core/event/{event_type}",
        "1.0.0",
    )
    harness.ledger.append(
        [
            {
                "event_type": event_type,
                "stream_id": stream_id,
                "command_id": command_id,
                "command_type": recorded_command_type,
                "command_schema_id": command_identity.schema_id,
                "command_schema_version": command_identity.schema_version,
                "command_schema_sha256": (command_schema_sha256 or command_identity.sha256),
                "actor_id": template["actor_id"],
                "authority_grant_id": template["authority_grant_id"],
                "idempotency_key": template["idempotency_key"],
                "command_payload_hash": (command_payload_hash or sha256_hex(canonical_bytes(payload))),
                "correlation_id": template["correlation_id"],
                "causation_id": template["causation_id"],
                "schema_id": event_identity.schema_id,
                "schema_version": event_identity.schema_version,
                "occurred_at": None,
                "payload": payload,
            }
        ]
    )


def _append_generic_task_created(
    harness,
    *,
    command_id: str,
    task_id: str,
    payload: dict,
) -> None:
    template = create_task_command(
        command_id,
        f"raw-generic-create:{command_id}",
        task_id,
        {"title": "Raw generic Task"},
    )
    inert_schemas = cached_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    command_identity = inert_schemas.resolve_identity(
        "ars://core/command",
        "1.0.0",
    )
    harness.objects.write("task", task_id, 1, payload)
    EventLedger(
        harness.service.control_root,
        PROJECT_ID,
        inert_schemas,
    ).append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": task_id,
                "command_id": command_id,
                "command_type": "CreateTask",
                "command_schema_id": command_identity.schema_id,
                "command_schema_version": command_identity.schema_version,
                "command_schema_sha256": command_identity.sha256,
                "actor_id": template["actor_id"],
                "authority_grant_id": template["authority_grant_id"],
                "idempotency_key": template["idempotency_key"],
                "command_payload_hash": sha256_hex(canonical_bytes(payload)),
                "correlation_id": template["correlation_id"],
                "causation_id": template["causation_id"],
                "schema_id": "ars://core/event",
                "schema_version": "1.0.0",
                "occurred_at": None,
                "payload": payload,
            }
        ]
    )


def _append_task_supersession(
    harness,
    *,
    command_id: str,
    source_id: str,
    replacement_id: str,
) -> None:
    _append_exact_event(
        harness,
        command_id=command_id,
        command_type="SupersedeTask",
        event_type="TaskSuperseded",
        stream_id=source_id,
        payload={
            "task_id": source_id,
            "replacement_task_id": replacement_id,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["audit retains both immutable revisions"],
            "lineage_reason": "Exercise replay graph invariants.",
        },
    )


def _append_scope_supersession(
    harness,
    *,
    command_id: str,
    source_id: str,
    replacement_id: str,
) -> None:
    _append_exact_event(
        harness,
        command_id=command_id,
        command_type="SupersedeScopeDefinition",
        event_type="ScopeDefinitionSuperseded",
        stream_id=source_id,
        payload={
            "scope_definition_id": source_id,
            "replacement_scope_definition_id": replacement_id,
            "replacement_revision": 1,
            "lineage_reason": "Exercise replay graph invariants.",
            "member_dispositions": [
                {
                    "member_id": TASK_A,
                    "member_kind": "task",
                    "required_disposition": "superseded",
                }
            ],
            "effective_at": "2026-07-30T13:00:00Z",
        },
    )


def _scope_create_payload(scope_id: str, *, completion: str) -> dict:
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
        "completion_predicate": completion,
        "amendment_authority": "synthetic-owner",
    }


def _task_definition(task_id: str, title: str, revision: int) -> dict:
    template = create_task_command(
        "cmd_01978abc-6299-7000-8000-000000006299",
        f"definition:{task_id}:{revision}",
        task_id,
        {"title": title},
    )["payload"]["definition"]
    definition = deepcopy(template)
    definition["revision"] = revision
    definition["title"] = title
    definition["objective"] = f"Complete {title}"
    definition.pop("content_sha256")
    definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
    return definition


def _submit_idempotently(harness, command: dict) -> dict:
    before = tuple(harness.ledger.iter_events())
    first = harness.service.submit(command)
    second = harness.service.submit(command)
    after = tuple(harness.ledger.iter_events())

    assert first.status == "accepted"
    assert second == first
    assert len(after) == len(before) + 1

    event = after[-1]
    expected_event_type = COMMAND_EVENT_PAIRS[command["command_type"]]
    command_identity = harness.service.schemas.resolve_identity(
        command["schema_id"],
        command["schema_version"],
    )
    event_identity = harness.service.schemas.resolve_identity(
        f"ars://core/event/{expected_event_type}",
        "1.0.0",
    )

    assert event["event_type"] == expected_event_type
    assert event["schema_id"] == event_identity.schema_id
    assert event["schema_version"] == event_identity.schema_version
    assert event["command_schema_id"] == command_identity.schema_id
    assert event["command_schema_version"] == command_identity.schema_version
    assert event["command_schema_sha256"] == command_identity.sha256
    assert event["actor_id"] == command["actor_id"]
    assert event["authority_grant_id"] == scoped_lifecycle_grant_id(command["target_stream_id"])
    assert event["stream_id"] == command["target_stream_id"]
    assert event["payload"] == command["payload"]
    harness.service.schemas.validate_active(
        event_identity.schema_id,
        event,
        schema_version=event_identity.schema_version,
        expected_sha256=event_identity.sha256,
    )
    return event


def test_scope_definition_create_amend_supersede_is_exact_and_replayable(
    tmp_path,
):
    harness = control_plane(tmp_path)
    created_payload = _scope_create_payload(
        SCOPE_A,
        completion="all required members accepted",
    )
    created = _command(
        "cmd_01978abc-6111-7000-8000-000000006111",
        "CreateScopeDefinition",
        SCOPE_A,
        0,
        created_payload,
    )
    created.update(
        {
            "command_schema_id": "ars://caller/forged",
            "command_schema_version": "9.0.0",
            "command_schema_sha256": "0" * 64,
        }
    )
    created_event = _submit_idempotently(harness, created)

    amended_payload = {
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
        "rationale": "Defer the member without rewriting revision 1.",
        "effective_boundary": "after current attempts stop",
        "amendment_authority": "independent-scope-reviewer",
    }
    amended_event = _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6112-7000-8000-000000006112",
            "AmendScopeDefinition",
            SCOPE_A,
            1,
            amended_payload,
        ),
    )

    replacement_payload = _scope_create_payload(
        SCOPE_B,
        completion="replacement scope accepted",
    )
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6113-7000-8000-000000006113",
            "CreateScopeDefinition",
            SCOPE_B,
            0,
            replacement_payload,
        ),
    )
    superseded_payload = {
        "scope_definition_id": SCOPE_A,
        "replacement_scope_definition_id": SCOPE_B,
        "replacement_revision": 1,
        "lineage_reason": "Replace the amended scope with its accepted successor.",
        "member_dispositions": [
            {
                "member_id": TASK_A,
                "member_kind": "task",
                "required_disposition": "superseded",
            }
        ],
        "effective_at": "2026-07-30T13:00:00Z",
    }
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6114-7000-8000-000000006114",
            "SupersedeScopeDefinition",
            SCOPE_A,
            2,
            superseded_payload,
        ),
    )

    assert created_event["payload"] == created_payload
    assert amended_event["payload"] == amended_payload
    assert harness.objects.read("scope_definition", SCOPE_A, 1) == created_payload
    assert harness.objects.read("scope_definition", SCOPE_A, 2) == amended_payload

    projection = replay(
        harness.ledger.iter_events(),
        schema_registry=harness.service.schemas,
    )
    scope = projection["streams"][SCOPE_A]
    assert scope["status"] == "superseded"
    assert scope["current_revision"] == 2
    assert scope["replacement"] == {
        "scope_definition_id": SCOPE_B,
        "revision": 1,
    }
    assert scope["definition"]["amendment_authority"] == "synthetic-owner"
    assert scope["last_amendment"]["amendment_authority"] == "independent-scope-reviewer"
    assert set(scope["revision_history"]) == {"1", "2"}


def test_task_create_amend_supersede_preserves_rich_revision_history(
    tmp_path,
):
    harness = control_plane(tmp_path)
    definition_1 = _task_definition(TASK_A, "Task A revision 1", 1)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6211-7000-8000-000000006211",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_A, "definition": definition_1},
        ),
    )

    definition_2 = _task_definition(TASK_A, "Task A revision 2", 2)
    amended_payload = {
        "task_id": TASK_A,
        "prior_revision": 1,
        "new_revision": 2,
        "replacement_definition": definition_2,
        "changed_fields": ["title", "objective"],
        "rationale": "Clarify the bounded Task without mutating revision 1.",
        "effective_boundary": "before redispatch",
        "authority_evidence_refs": [AUTHORITY_GRANT_ID],
    }
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6212-7000-8000-000000006212",
            "AmendTask",
            TASK_A,
            1,
            amended_payload,
        ),
    )

    replacement_definition = _task_definition(TASK_B, "Task B", 1)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6213-7000-8000-000000006213",
            "CreateTask",
            TASK_B,
            0,
            {
                "new_task_id": TASK_B,
                "definition": replacement_definition,
            },
        ),
    )
    superseded_payload = {
        "task_id": TASK_A,
        "replacement_task_id": TASK_B,
        "replacement_task_revision": 1,
        "continuing_consumer_dispositions": ["audit retains both immutable Task revisions"],
        "lineage_reason": "Replace Task A revision 2 with Task B revision 1.",
    }
    superseded_event = _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6214-7000-8000-000000006214",
            "SupersedeTask",
            TASK_A,
            2,
            superseded_payload,
        ),
    )

    assert "task_type" not in definition_1
    assert "continuing_consumers" not in definition_1
    assert harness.objects.read("task", TASK_A, 1) == definition_1
    assert harness.objects.read("task", TASK_A, 2) == definition_2
    assert (
        superseded_event["payload"]["continuing_consumer_dispositions"]
        == (superseded_payload["continuing_consumer_dispositions"])
    )

    projection = replay(
        harness.ledger.iter_events(),
        schema_registry=harness.service.schemas,
    )
    task = projection["streams"][TASK_A]
    assert task["status"] == "superseded"
    assert task["current_revision"] == 2
    assert task["replacement"] == {"task_id": TASK_B, "revision": 1}
    assert set(task["revision_history"]) == {"1", "2"}
    assert task["continuing_consumer_dispositions"] == (superseded_payload["continuing_consumer_dispositions"])


@pytest.mark.parametrize(
    ("command_type", "command_id"),
    [
        (
            "CreateScopeDefinition",
            "cmd_01978abc-6311-7000-8000-000000006311",
        ),
        (
            "AmendScopeDefinition",
            "cmd_01978abc-6312-7000-8000-000000006312",
        ),
        (
            "SupersedeScopeDefinition",
            "cmd_01978abc-6313-7000-8000-000000006313",
        ),
        ("AmendTask", "cmd_01978abc-6314-7000-8000-000000006314"),
        ("SupersedeTask", "cmd_01978abc-6315-7000-8000-000000006315"),
    ],
)
def test_newly_activated_command_cannot_bypass_exact_binding_with_generic_schema(
    tmp_path,
    command_type,
    command_id,
):
    harness = control_plane(tmp_path)
    command = create_task_command(
        command_id,
        f"generic-bypass:{command_type}",
        TASK_A,
        {"title": "Generic bypass"},
    )
    command["command_type"] = command_type
    command["schema_id"] = "ars://core/command"
    command["payload"] = {}
    command.pop("project_id")

    with pytest.raises(SchemaError, match="active command binding mismatch"):
        harness.service.submit(command)

    assert tuple(harness.ledger.iter_batches()) == ()
    assert harness.receipts.load(command_id) is None
    assert not list((harness.objects.control_root / "objects").rglob("*.json"))


@pytest.mark.parametrize("aggregate", ["scope_definition", "task"])
def test_create_rejects_payload_subject_that_differs_from_target_stream(
    tmp_path,
    aggregate,
):
    harness = control_plane(tmp_path)
    if aggregate == "scope_definition":
        command = _command(
            "cmd_01978abc-6411-7000-8000-000000006411",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_B,
                completion="mismatched subject must not publish",
            ),
        )
    else:
        definition = _task_definition(TASK_A, "Bound Task", 1)
        command = _command(
            "cmd_01978abc-6412-7000-8000-000000006412",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_B, "definition": definition},
        )

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "invalid_command_subject_identity"
    assert tuple(harness.ledger.iter_batches()) == ()
    assert not list((harness.objects.control_root / "objects").rglob("*.json"))


def _object_bytes(harness) -> dict[str, bytes]:
    root = harness.objects.control_root / "objects"
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*.json")}


def test_task_definition_hash_and_stale_amendment_reject_atomically(tmp_path):
    harness = control_plane(tmp_path)
    definition = _task_definition(TASK_A, "Hash-bound Task", 1)
    bad_hash = deepcopy(definition)
    bad_hash["content_sha256"] = "0" * 64
    rejected = harness.service.submit(
        _command(
            "cmd_01978abc-6511-7000-8000-000000006511",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_A, "definition": bad_hash},
        )
    )
    assert rejected.status == "rejected"
    assert rejected.reason_code == "invalid_task_definition_hash"
    assert tuple(harness.ledger.iter_batches()) == ()
    assert _object_bytes(harness) == {}

    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6512-7000-8000-000000006512",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_A, "definition": definition},
        ),
    )
    before_events = tuple(harness.ledger.iter_events())
    before_objects = _object_bytes(harness)
    revision_3 = _task_definition(TASK_A, "Skipped revision", 3)
    stale = harness.service.submit(
        _command(
            "cmd_01978abc-6513-7000-8000-000000006513",
            "AmendTask",
            TASK_A,
            1,
            {
                "task_id": TASK_A,
                "prior_revision": 2,
                "new_revision": 3,
                "replacement_definition": revision_3,
                "changed_fields": ["title"],
                "rationale": "A stale prior revision must not publish.",
                "effective_boundary": "before redispatch",
                "authority_evidence_refs": [AUTHORITY_GRANT_ID],
            },
        )
    )
    assert stale.status == "rejected"
    assert stale.reason_code == "stale_task_revision"
    assert tuple(harness.ledger.iter_events()) == before_events
    assert _object_bytes(harness) == before_objects


def test_scope_delta_and_supersession_dispositions_fail_closed(tmp_path):
    harness = control_plane(tmp_path)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6611-7000-8000-000000006611",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    before_events = tuple(harness.ledger.iter_events())
    before_objects = _object_bytes(harness)
    unsupported = harness.service.submit(
        _command(
            "cmd_01978abc-6612-7000-8000-000000006612",
            "AmendScopeDefinition",
            SCOPE_A,
            1,
            {
                "scope_definition_id": SCOPE_A,
                "prior_revision": 1,
                "new_revision": 2,
                "member_changes": [],
                "changed_fields": ["completion_predicate"],
                "rationale": "The accepted delta has no replacement value.",
                "effective_boundary": "after current attempts stop",
                "amendment_authority": "synthetic-owner",
            },
        )
    )
    assert unsupported.status == "rejected"
    assert unsupported.reason_code == "unsupported_scope_amendment_field"
    assert tuple(harness.ledger.iter_events()) == before_events
    assert _object_bytes(harness) == before_objects

    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6613-7000-8000-000000006613",
            "CreateScopeDefinition",
            SCOPE_B,
            0,
            _scope_create_payload(
                SCOPE_B,
                completion="replacement scope accepted",
            ),
        ),
    )
    before_events = tuple(harness.ledger.iter_events())
    missing = harness.service.submit(
        _command(
            "cmd_01978abc-6614-7000-8000-000000006614",
            "SupersedeScopeDefinition",
            SCOPE_A,
            1,
            {
                "scope_definition_id": SCOPE_A,
                "replacement_scope_definition_id": SCOPE_B,
                "replacement_revision": 1,
                "lineage_reason": "Missing member disposition must reject.",
                "member_dispositions": [],
                "effective_at": "2026-07-30T13:00:00Z",
            },
        )
    )
    assert missing.status == "rejected"
    assert missing.reason_code == "missing_scope_member_disposition"
    assert tuple(harness.ledger.iter_events()) == before_events


def test_task_supersession_requires_a_consumer_disposition(tmp_path):
    harness = control_plane(tmp_path)
    for task_id, command_id in (
        (TASK_A, "cmd_01978abc-6711-7000-8000-000000006711"),
        (TASK_B, "cmd_01978abc-6712-7000-8000-000000006712"),
    ):
        _submit_idempotently(
            harness,
            _command(
                command_id,
                "CreateTask",
                task_id,
                0,
                {
                    "new_task_id": task_id,
                    "definition": _task_definition(task_id, task_id, 1),
                },
            ),
        )
    before_events = tuple(harness.ledger.iter_events())
    before_objects = _object_bytes(harness)
    rejected = harness.service.submit(
        _command(
            "cmd_01978abc-6713-7000-8000-000000006713",
            "SupersedeTask",
            TASK_A,
            1,
            {
                "task_id": TASK_A,
                "replacement_task_id": TASK_B,
                "replacement_task_revision": 1,
                "continuing_consumer_dispositions": [],
                "lineage_reason": "Missing disposition must reject.",
            },
        )
    )
    assert rejected.status == "rejected"
    assert rejected.reason_code == "missing_continuing_consumer_disposition"
    assert tuple(harness.ledger.iter_events()) == before_events
    assert _object_bytes(harness) == before_objects


def test_scope_member_identity_must_be_unique(tmp_path):
    harness = control_plane(tmp_path)
    payload = _scope_create_payload(
        SCOPE_A,
        completion="duplicate identities must reject",
    )
    payload["members"].append(
        {
            "member_id": TASK_A,
            "member_kind": "scope",
            "required_disposition": "deferred",
        }
    )

    receipt = harness.service.submit(
        _command(
            "cmd_01978abc-6811-7000-8000-000000006811",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            payload,
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "invalid_scope_definition"
    assert tuple(harness.ledger.iter_events()) == ()
    assert _object_bytes(harness) == {}


def test_scope_supersession_rejects_duplicate_member_dispositions(tmp_path):
    harness = control_plane(tmp_path)
    for scope_id, command_id in (
        (SCOPE_A, "cmd_01978abc-6821-7000-8000-000000006821"),
        (SCOPE_B, "cmd_01978abc-6822-7000-8000-000000006822"),
    ):
        _submit_idempotently(
            harness,
            _command(
                command_id,
                "CreateScopeDefinition",
                scope_id,
                0,
                _scope_create_payload(
                    scope_id,
                    completion="all required members accepted",
                ),
            ),
        )
    before_events = tuple(harness.ledger.iter_events())
    receipt = harness.service.submit(
        _command(
            "cmd_01978abc-6823-7000-8000-000000006823",
            "SupersedeScopeDefinition",
            SCOPE_A,
            1,
            {
                "scope_definition_id": SCOPE_A,
                "replacement_scope_definition_id": SCOPE_B,
                "replacement_revision": 1,
                "lineage_reason": "Duplicate member effects must reject.",
                "member_dispositions": [
                    {
                        "member_id": TASK_A,
                        "member_kind": "task",
                        "required_disposition": "superseded",
                    },
                    {
                        "member_id": TASK_A,
                        "member_kind": "task",
                        "required_disposition": "deferred",
                    },
                ],
                "effective_at": "2026-07-30T13:00:00Z",
            },
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "duplicate_scope_member_disposition"
    assert tuple(harness.ledger.iter_events()) == before_events


def test_task_amendment_changed_fields_bind_exact_delta(tmp_path):
    harness = control_plane(tmp_path)
    definition = _task_definition(TASK_A, "Task A revision 1", 1)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6831-7000-8000-000000006831",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_A, "definition": definition},
        ),
    )
    replacement = _task_definition(TASK_A, "Task A revision 2", 2)
    before_events = tuple(harness.ledger.iter_events())
    receipt = harness.service.submit(
        _command(
            "cmd_01978abc-6832-7000-8000-000000006832",
            "AmendTask",
            TASK_A,
            1,
            {
                "task_id": TASK_A,
                "prior_revision": 1,
                "new_revision": 2,
                "replacement_definition": replacement,
                "changed_fields": ["title"],
                "rationale": "The objective change must also be declared.",
                "effective_boundary": "before redispatch",
                "authority_evidence_refs": [AUTHORITY_GRANT_ID],
            },
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "task_changed_fields_mismatch"
    assert tuple(harness.ledger.iter_events()) == before_events
    assert harness.objects.latest_revision("task", TASK_A) == 1


def test_exact_lifecycle_commands_reject_foreign_project(tmp_path):
    harness = control_plane(tmp_path)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6841-7000-8000-000000006841",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    scope_command = _command(
        "cmd_01978abc-6842-7000-8000-000000006842",
        "AmendScopeDefinition",
        SCOPE_A,
        1,
        {
            "scope_definition_id": SCOPE_A,
            "prior_revision": 1,
            "new_revision": 2,
            "member_changes": [],
            "changed_fields": ["members"],
            "rationale": "A foreign project must not mutate this scope.",
            "effective_boundary": "after current attempts stop",
            "amendment_authority": "synthetic-owner",
        },
    )
    scope_command["project_id"] = "prj_01978abc-6849-7000-8000-000000006849"
    before_events = tuple(harness.ledger.iter_events())

    scope_receipt = harness.service.submit(scope_command)

    assert scope_receipt.status == "rejected"
    assert scope_receipt.reason_code == "lifecycle_authority_unauthorized"
    assert scope_receipt.explanation == "authority subject scope mismatch"
    assert scope_receipt.unmet_preconditions == ("lifecycle_authority_unauthorized",)
    assert tuple(harness.ledger.iter_events()) == before_events

    for task_id, command_id in (
        (TASK_A, "cmd_01978abc-6843-7000-8000-000000006843"),
        (TASK_B, "cmd_01978abc-6844-7000-8000-000000006844"),
    ):
        _submit_idempotently(
            harness,
            _command(
                command_id,
                "CreateTask",
                task_id,
                0,
                {
                    "new_task_id": task_id,
                    "definition": _task_definition(task_id, task_id, 1),
                },
            ),
        )
    task_command = _command(
        "cmd_01978abc-6845-7000-8000-000000006845",
        "SupersedeTask",
        TASK_A,
        1,
        {
            "task_id": TASK_A,
            "replacement_task_id": TASK_B,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["audit retains both revisions"],
            "lineage_reason": "A foreign project must not supersede this Task.",
        },
    )
    task_command["project_id"] = "prj_01978abc-6849-7000-8000-000000006849"
    before_events = tuple(harness.ledger.iter_events())

    task_receipt = harness.service.submit(task_command)

    assert task_receipt.status == "rejected"
    assert task_receipt.reason_code == "lifecycle_authority_unauthorized"
    assert task_receipt.explanation == "authority subject scope mismatch"
    assert task_receipt.unmet_preconditions == ("lifecycle_authority_unauthorized",)
    assert tuple(harness.ledger.iter_events()) == before_events


def test_rich_same_task_supersession_rejects_uncommitted_orphan_revision(
    tmp_path,
):
    harness = control_plane(tmp_path)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6851-7000-8000-000000006851",
            "CreateTask",
            TASK_A,
            0,
            {
                "new_task_id": TASK_A,
                "definition": _task_definition(TASK_A, "Task A revision 1", 1),
            },
        ),
    )
    harness.objects.write(
        "task",
        TASK_A,
        2,
        _task_definition(TASK_A, "Uncommitted Task A revision 2", 2),
    )
    before_events = tuple(harness.ledger.iter_events())

    receipt = harness.service.submit(
        _command(
            "cmd_01978abc-6852-7000-8000-000000006852",
            "SupersedeTask",
            TASK_A,
            1,
            {
                "task_id": TASK_A,
                "replacement_task_id": TASK_A,
                "replacement_task_revision": 2,
                "continuing_consumer_dispositions": ["audit retains both immutable revisions"],
                "lineage_reason": "An orphan object cannot activate itself.",
            },
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "replacement_revision_uncommitted"
    assert tuple(harness.ledger.iter_events()) == before_events


def test_project_binding_precedes_committed_idempotency_reconstruction(
    tmp_path,
):
    harness = control_plane(tmp_path)
    command = _command(
        "cmd_01978abc-6861-7000-8000-000000006861",
        "CreateTask",
        TASK_A,
        0,
        {
            "new_task_id": TASK_A,
            "definition": _task_definition(TASK_A, "Project-bound Task", 1),
        },
    )
    accepted = harness.service.submit(command)
    foreign_retry = deepcopy(command)
    foreign_retry["project_id"] = "prj_01978abc-6869-7000-8000-000000006869"
    before_events = tuple(harness.ledger.iter_events())

    foreign_receipt = harness.service.submit(foreign_retry)
    assert foreign_receipt.status == "rejected"
    assert foreign_receipt.reason_code == "lifecycle_authority_unauthorized"
    assert foreign_receipt.explanation == "authority subject scope mismatch"
    assert foreign_receipt.unmet_preconditions == ("lifecycle_authority_unauthorized",)

    assert accepted.status == "accepted"
    assert harness.receipts.load(command["command_id"]) == accepted
    assert tuple(harness.ledger.iter_events()) == before_events


def test_scope_amendment_requires_declared_nonempty_member_delta(tmp_path):
    harness = control_plane(tmp_path)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6871-7000-8000-000000006871",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    before_events = tuple(harness.ledger.iter_events())
    receipt = harness.service.submit(
        _command(
            "cmd_01978abc-6872-7000-8000-000000006872",
            "AmendScopeDefinition",
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
                "changed_fields": [],
                "rationale": "The member delta must be declared.",
                "effective_boundary": "after current attempts stop",
                "amendment_authority": "synthetic-owner",
            },
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "unsupported_scope_amendment_field"
    assert tuple(harness.ledger.iter_events()) == before_events


def test_replay_rejects_exact_event_subject_mismatches(tmp_path):
    task_root = tmp_path / "task-create"
    task_root.mkdir()
    task_harness = control_plane(task_root)
    mismatched_definition = _task_definition(
        TASK_B,
        "Mismatched Task definition",
        1,
    )
    _append_exact_event(
        task_harness,
        command_id="cmd_01978abc-6881-7000-8000-000000006881",
        command_type="CreateTask",
        event_type="TaskCreated",
        stream_id=TASK_A,
        payload={
            "new_task_id": TASK_B,
            "definition": mismatched_definition,
        },
    )
    with pytest.raises(ValueError, match="TaskCreated subject binding mismatch"):
        replay(
            task_harness.ledger.iter_events(),
            schema_registry=task_harness.service.schemas,
        )

    scope_root = tmp_path / "scope-create"
    scope_root.mkdir()
    scope_harness = control_plane(scope_root)
    _append_exact_event(
        scope_harness,
        command_id="cmd_01978abc-6882-7000-8000-000000006882",
        command_type="CreateScopeDefinition",
        event_type="ScopeDefinitionCreated",
        stream_id=SCOPE_A,
        payload=_scope_create_payload(
            SCOPE_B,
            completion="mismatched subject must reject",
        ),
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinitionCreated subject binding mismatch",
    ):
        replay(
            scope_harness.ledger.iter_events(),
            schema_registry=scope_harness.service.schemas,
        )

    supersede_root = tmp_path / "task-supersede"
    supersede_root.mkdir()
    supersede_harness = control_plane(supersede_root)
    for task_id, command_id in (
        (TASK_A, "cmd_01978abc-6883-7000-8000-000000006883"),
        (TASK_B, "cmd_01978abc-6884-7000-8000-000000006884"),
    ):
        _submit_idempotently(
            supersede_harness,
            _command(
                command_id,
                "CreateTask",
                task_id,
                0,
                {
                    "new_task_id": task_id,
                    "definition": _task_definition(task_id, task_id, 1),
                },
            ),
        )
    _append_exact_event(
        supersede_harness,
        command_id="cmd_01978abc-6885-7000-8000-000000006885",
        command_type="SupersedeTask",
        event_type="TaskSuperseded",
        stream_id=TASK_A,
        payload={
            "task_id": TASK_B,
            "replacement_task_id": TASK_B,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["audit retains both revisions"],
            "lineage_reason": "Mismatched source identity must reject.",
        },
    )
    with pytest.raises(ValueError, match="TaskSuperseded subject binding mismatch"):
        replay(
            supersede_harness.ledger.iter_events(),
            schema_registry=supersede_harness.service.schemas,
        )


def test_replay_mirrors_exact_lifecycle_semantic_invariants(tmp_path):
    amend_root = tmp_path / "task-amend-delta"
    amend_root.mkdir()
    amend_harness = control_plane(amend_root)
    _submit_idempotently(
        amend_harness,
        _command(
            "cmd_01978abc-6891-7000-8000-000000006891",
            "CreateTask",
            TASK_A,
            0,
            {
                "new_task_id": TASK_A,
                "definition": _task_definition(TASK_A, "Task A revision 1", 1),
            },
        ),
    )
    replacement = _task_definition(TASK_A, "Task A revision 2", 2)
    _append_exact_event(
        amend_harness,
        command_id="cmd_01978abc-6892-7000-8000-000000006892",
        command_type="AmendTask",
        event_type="TaskAmended",
        stream_id=TASK_A,
        payload={
            "task_id": TASK_A,
            "prior_revision": 1,
            "new_revision": 2,
            "replacement_definition": replacement,
            "changed_fields": ["title"],
            "rationale": "The objective delta is intentionally omitted.",
            "effective_boundary": "before redispatch",
            "authority_evidence_refs": [AUTHORITY_GRANT_ID],
        },
    )
    with pytest.raises(ValueError, match="TaskAmended changed_fields mismatch"):
        replay(
            amend_harness.ledger.iter_events(),
            schema_registry=amend_harness.service.schemas,
        )

    orphan_root = tmp_path / "task-orphan-supersession"
    orphan_root.mkdir()
    orphan_harness = control_plane(orphan_root)
    _submit_idempotently(
        orphan_harness,
        _command(
            "cmd_01978abc-6893-7000-8000-000000006893",
            "CreateTask",
            TASK_A,
            0,
            {
                "new_task_id": TASK_A,
                "definition": _task_definition(TASK_A, "Task A revision 1", 1),
            },
        ),
    )
    _append_exact_event(
        orphan_harness,
        command_id="cmd_01978abc-6894-7000-8000-000000006894",
        command_type="SupersedeTask",
        event_type="TaskSuperseded",
        stream_id=TASK_A,
        payload={
            "task_id": TASK_A,
            "replacement_task_id": TASK_A,
            "replacement_task_revision": 2,
            "continuing_consumer_dispositions": ["audit retains both immutable revisions"],
            "lineage_reason": "An uncommitted rich revision cannot activate.",
        },
    )
    with pytest.raises(
        ValueError,
        match="TaskSuperseded rich same-Task replacement is uncommitted",
    ):
        replay(
            orphan_harness.ledger.iter_events(),
            schema_registry=orphan_harness.service.schemas,
        )

    duplicate_root = tmp_path / "scope-duplicate-member"
    duplicate_root.mkdir()
    duplicate_harness = control_plane(duplicate_root)
    duplicate_payload = _scope_create_payload(
        SCOPE_A,
        completion="duplicate member identity must reject",
    )
    duplicate_payload["members"].append(
        {
            "member_id": TASK_A,
            "member_kind": "scope",
            "required_disposition": "deferred",
        }
    )
    _append_exact_event(
        duplicate_harness,
        command_id="cmd_01978abc-6895-7000-8000-000000006895",
        command_type="CreateScopeDefinition",
        event_type="ScopeDefinitionCreated",
        stream_id=SCOPE_A,
        payload=duplicate_payload,
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinitionCreated duplicate member identity",
    ):
        replay(
            duplicate_harness.ledger.iter_events(),
            schema_registry=duplicate_harness.service.schemas,
        )

    scope_amend_root = tmp_path / "scope-amend-delta"
    scope_amend_root.mkdir()
    scope_amend_harness = control_plane(scope_amend_root)
    _submit_idempotently(
        scope_amend_harness,
        _command(
            "cmd_01978abc-6896-7000-8000-000000006896",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    _append_exact_event(
        scope_amend_harness,
        command_id="cmd_01978abc-6897-7000-8000-000000006897",
        command_type="AmendScopeDefinition",
        event_type="ScopeDefinitionAmended",
        stream_id=SCOPE_A,
        payload={
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
            "changed_fields": [],
            "rationale": "The member delta is intentionally undeclared.",
            "effective_boundary": "after current attempts stop",
            "amendment_authority": "synthetic-owner",
        },
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinitionAmended changed_fields mismatch",
    ):
        replay(
            scope_amend_harness.ledger.iter_events(),
            schema_registry=scope_amend_harness.service.schemas,
        )


def test_replay_rejects_task_and_scope_replacement_graph_violations(tmp_path):
    task_cycle_root = tmp_path / "task-cycle"
    task_cycle_root.mkdir()
    task_cycle = control_plane(task_cycle_root)
    for task_id, command_id in (
        (TASK_A, "cmd_01978abc-68a1-7000-8000-0000000068a1"),
        (TASK_B, "cmd_01978abc-68a2-7000-8000-0000000068a2"),
    ):
        _submit_idempotently(
            task_cycle,
            _command(
                command_id,
                "CreateTask",
                task_id,
                0,
                {
                    "new_task_id": task_id,
                    "definition": _task_definition(task_id, task_id, 1),
                },
            ),
        )
    _append_task_supersession(
        task_cycle,
        command_id="cmd_01978abc-68a3-7000-8000-0000000068a3",
        source_id=TASK_A,
        replacement_id=TASK_B,
    )
    _append_task_supersession(
        task_cycle,
        command_id="cmd_01978abc-68a4-7000-8000-0000000068a4",
        source_id=TASK_B,
        replacement_id=TASK_A,
    )
    with pytest.raises(ValueError, match="Task supersession cycle"):
        replay(
            task_cycle.ledger.iter_events(),
            schema_registry=task_cycle.service.schemas,
        )

    task_missing_root = tmp_path / "task-missing"
    task_missing_root.mkdir()
    task_missing = control_plane(task_missing_root)
    _submit_idempotently(
        task_missing,
        _command(
            "cmd_01978abc-68b1-7000-8000-0000000068b1",
            "CreateTask",
            TASK_A,
            0,
            {
                "new_task_id": TASK_A,
                "definition": _task_definition(TASK_A, TASK_A, 1),
            },
        ),
    )
    _append_task_supersession(
        task_missing,
        command_id="cmd_01978abc-68b2-7000-8000-0000000068b2",
        source_id=TASK_A,
        replacement_id=TASK_B,
    )
    with pytest.raises(ValueError, match="Task replacement revision is missing"):
        replay(
            task_missing.ledger.iter_events(),
            schema_registry=task_missing.service.schemas,
        )

    task_terminal_root = tmp_path / "task-terminal"
    task_terminal_root.mkdir()
    task_terminal = control_plane(task_terminal_root)
    for task_id, command_id in (
        (TASK_A, "cmd_01978abc-68c1-7000-8000-0000000068c1"),
        (TASK_B, "cmd_01978abc-68c2-7000-8000-0000000068c2"),
        (TASK_C, "cmd_01978abc-68c3-7000-8000-0000000068c3"),
    ):
        _submit_idempotently(
            task_terminal,
            _command(
                command_id,
                "CreateTask",
                task_id,
                0,
                {
                    "new_task_id": task_id,
                    "definition": _task_definition(task_id, task_id, 1),
                },
            ),
        )
    _append_task_supersession(
        task_terminal,
        command_id="cmd_01978abc-68c4-7000-8000-0000000068c4",
        source_id=TASK_B,
        replacement_id=TASK_C,
    )
    _append_task_supersession(
        task_terminal,
        command_id="cmd_01978abc-68c5-7000-8000-0000000068c5",
        source_id=TASK_A,
        replacement_id=TASK_B,
    )
    with pytest.raises(ValueError, match="Task replacement revision is terminal"):
        replay(
            task_terminal.ledger.iter_events(),
            schema_registry=task_terminal.service.schemas,
        )

    scope_cycle_root = tmp_path / "scope-cycle"
    scope_cycle_root.mkdir()
    scope_cycle = control_plane(scope_cycle_root)
    for scope_id, command_id in (
        (SCOPE_A, "cmd_01978abc-68d1-7000-8000-0000000068d1"),
        (SCOPE_B, "cmd_01978abc-68d2-7000-8000-0000000068d2"),
    ):
        _submit_idempotently(
            scope_cycle,
            _command(
                command_id,
                "CreateScopeDefinition",
                scope_id,
                0,
                _scope_create_payload(
                    scope_id,
                    completion="all required members accepted",
                ),
            ),
        )
    _append_scope_supersession(
        scope_cycle,
        command_id="cmd_01978abc-68d3-7000-8000-0000000068d3",
        source_id=SCOPE_A,
        replacement_id=SCOPE_B,
    )
    _append_scope_supersession(
        scope_cycle,
        command_id="cmd_01978abc-68d4-7000-8000-0000000068d4",
        source_id=SCOPE_B,
        replacement_id=SCOPE_A,
    )
    with pytest.raises(ValueError, match="ScopeDefinition supersession cycle"):
        replay(
            scope_cycle.ledger.iter_events(),
            schema_registry=scope_cycle.service.schemas,
        )

    scope_missing_root = tmp_path / "scope-missing"
    scope_missing_root.mkdir()
    scope_missing = control_plane(scope_missing_root)
    _submit_idempotently(
        scope_missing,
        _command(
            "cmd_01978abc-68e1-7000-8000-0000000068e1",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    _append_scope_supersession(
        scope_missing,
        command_id="cmd_01978abc-68e2-7000-8000-0000000068e2",
        source_id=SCOPE_A,
        replacement_id=SCOPE_B,
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinition replacement revision is missing",
    ):
        replay(
            scope_missing.ledger.iter_events(),
            schema_registry=scope_missing.service.schemas,
        )

    scope_terminal_root = tmp_path / "scope-terminal"
    scope_terminal_root.mkdir()
    scope_terminal = control_plane(scope_terminal_root)
    for scope_id, command_id in (
        (SCOPE_A, "cmd_01978abc-68f1-7000-8000-0000000068f1"),
        (SCOPE_B, "cmd_01978abc-68f2-7000-8000-0000000068f2"),
        (SCOPE_C, "cmd_01978abc-68f3-7000-8000-0000000068f3"),
    ):
        _submit_idempotently(
            scope_terminal,
            _command(
                command_id,
                "CreateScopeDefinition",
                scope_id,
                0,
                _scope_create_payload(
                    scope_id,
                    completion="all required members accepted",
                ),
            ),
        )
    _append_scope_supersession(
        scope_terminal,
        command_id="cmd_01978abc-68f4-7000-8000-0000000068f4",
        source_id=SCOPE_B,
        replacement_id=SCOPE_C,
    )
    _append_scope_supersession(
        scope_terminal,
        command_id="cmd_01978abc-68f5-7000-8000-0000000068f5",
        source_id=SCOPE_A,
        replacement_id=SCOPE_B,
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinition replacement revision is terminal",
    ):
        replay(
            scope_terminal.ledger.iter_events(),
            schema_registry=scope_terminal.service.schemas,
        )


def test_replay_rejects_exact_provenance_and_payload_hash_mismatch(tmp_path):
    binding_root = tmp_path / "wrong-binding"
    binding_root.mkdir()
    binding_harness = control_plane(binding_root)
    definition = _task_definition(TASK_A, "Wrong binding", 1)
    _append_exact_event(
        binding_harness,
        command_id="cmd_01978abc-6901-7000-8000-000000006901",
        command_type="CreateTask",
        event_type="TaskCreated",
        stream_id=TASK_A,
        payload={"new_task_id": TASK_A, "definition": definition},
        provenance_command_type="CreateScopeDefinition",
        provenance_schema_type="CreateScopeDefinition",
    )
    with pytest.raises(
        IntegrityError,
        match="exact lifecycle event provenance mismatch",
    ):
        replay(
            binding_harness.ledger.iter_events(),
            schema_registry=binding_harness.service.schemas,
        )

    hash_root = tmp_path / "wrong-payload-hash"
    hash_root.mkdir()
    hash_harness = control_plane(hash_root)
    _append_exact_event(
        hash_harness,
        command_id="cmd_01978abc-6902-7000-8000-000000006902",
        command_type="CreateTask",
        event_type="TaskCreated",
        stream_id=TASK_A,
        payload={"new_task_id": TASK_A, "definition": definition},
        command_payload_hash="0" * 64,
    )
    with pytest.raises(
        IntegrityError,
        match="exact lifecycle event provenance mismatch",
    ):
        replay(
            hash_harness.ledger.iter_events(),
            schema_registry=hash_harness.service.schemas,
        )

    schema_hash_root = tmp_path / "wrong-schema-hash"
    schema_hash_root.mkdir()
    schema_hash_harness = control_plane(schema_hash_root)
    with pytest.raises(
        SchemaError,
        match="schema hash mismatch",
    ):
        _append_exact_event(
            schema_hash_harness,
            command_id="cmd_01978abc-6903-7000-8000-000000006903",
            command_type="CreateTask",
            event_type="TaskCreated",
            stream_id=TASK_A,
            payload={"new_task_id": TASK_A, "definition": definition},
            command_schema_sha256="0" * 64,
        )
    assert tuple(schema_hash_harness.ledger.iter_events()) == ()

    no_registry_root = tmp_path / "no-schema-registry"
    no_registry_root.mkdir()
    no_registry_harness = control_plane(no_registry_root)
    _append_exact_event(
        no_registry_harness,
        command_id="cmd_01978abc-6904-7000-8000-000000006904",
        command_type="CreateTask",
        event_type="TaskCreated",
        stream_id=TASK_A,
        payload={"new_task_id": TASK_A, "definition": definition},
    )
    with pytest.raises(
        IntegrityError,
        match="exact lifecycle schema registry unavailable",
    ):
        replay(no_registry_harness.ledger.iter_events())


def test_submit_and_replay_reject_noop_revisions(tmp_path):
    task_root = tmp_path / "task-noop"
    task_root.mkdir()
    task_harness = control_plane(task_root)
    definition = _task_definition(TASK_A, "No-op Task", 1)
    _submit_idempotently(
        task_harness,
        _command(
            "cmd_01978abc-6911-7000-8000-000000006911",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_A, "definition": definition},
        ),
    )
    replacement = deepcopy(definition)
    replacement["revision"] = 2
    replacement.pop("content_sha256")
    replacement["content_sha256"] = sha256_hex(canonical_bytes(replacement))
    payload = {
        "task_id": TASK_A,
        "prior_revision": 1,
        "new_revision": 2,
        "replacement_definition": replacement,
        "changed_fields": [],
        "rationale": "A revision must change a typed field.",
        "effective_boundary": "before redispatch",
        "authority_evidence_refs": [AUTHORITY_GRANT_ID],
    }
    before_events = tuple(task_harness.ledger.iter_events())
    receipt = task_harness.service.submit(
        _command(
            "cmd_01978abc-6912-7000-8000-000000006912",
            "AmendTask",
            TASK_A,
            1,
            payload,
        )
    )
    assert receipt.status == "rejected"
    assert receipt.reason_code == "task_changed_fields_mismatch"
    assert tuple(task_harness.ledger.iter_events()) == before_events
    _append_exact_event(
        task_harness,
        command_id="cmd_01978abc-6913-7000-8000-000000006913",
        command_type="AmendTask",
        event_type="TaskAmended",
        stream_id=TASK_A,
        payload=payload,
    )
    with pytest.raises(ValueError, match="TaskAmended changed_fields mismatch"):
        replay(
            task_harness.ledger.iter_events(),
            schema_registry=task_harness.service.schemas,
        )

    scope_root = tmp_path / "scope-noop"
    scope_root.mkdir()
    scope_harness = control_plane(scope_root)
    _submit_idempotently(
        scope_harness,
        _command(
            "cmd_01978abc-6914-7000-8000-000000006914",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    scope_payload = {
        "scope_definition_id": SCOPE_A,
        "prior_revision": 1,
        "new_revision": 2,
        "member_changes": [],
        "changed_fields": ["members"],
        "rationale": "A revision must contain a member change.",
        "effective_boundary": "after current attempts stop",
        "amendment_authority": "synthetic-owner",
    }
    before_events = tuple(scope_harness.ledger.iter_events())
    receipt = scope_harness.service.submit(
        _command(
            "cmd_01978abc-6915-7000-8000-000000006915",
            "AmendScopeDefinition",
            SCOPE_A,
            1,
            scope_payload,
        )
    )
    assert receipt.status == "rejected"
    assert receipt.reason_code == "invalid_scope_definition"
    assert tuple(scope_harness.ledger.iter_events()) == before_events
    _append_exact_event(
        scope_harness,
        command_id="cmd_01978abc-6916-7000-8000-000000006916",
        command_type="AmendScopeDefinition",
        event_type="ScopeDefinitionAmended",
        stream_id=SCOPE_A,
        payload=scope_payload,
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinitionAmended duplicate or empty member changes",
    ):
        replay(
            scope_harness.ledger.iter_events(),
            schema_registry=scope_harness.service.schemas,
        )


@pytest.mark.parametrize(
    ("member_change", "replay_error"),
    [
        (
            {
                "member_id": TASK_A,
                "member_kind": "task",
                "disposition": "accepted",
            },
            "ScopeDefinitionAmended has no semantic member delta",
        ),
        (
            {
                "member_id": TASK_A,
                "member_kind": "scope",
                "disposition": "removed_by_amendment",
            },
            "ScopeDefinitionAmended member kind mismatch",
        ),
        (
            {
                "member_id": TASK_B,
                "member_kind": "task",
                "disposition": "removed_by_amendment",
            },
            "ScopeDefinitionAmended member change refers to absent member",
        ),
    ],
    ids=("identical-member", "wrong-kind-removal", "absent-removal"),
)
def test_scope_amendment_requires_a_typed_semantic_member_delta(
    tmp_path,
    member_change,
    replay_error,
):
    harness = control_plane(tmp_path)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6917-7000-8000-000000006917",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            _scope_create_payload(
                SCOPE_A,
                completion="all required members accepted",
            ),
        ),
    )
    payload = {
        "scope_definition_id": SCOPE_A,
        "prior_revision": 1,
        "new_revision": 2,
        "member_changes": [member_change],
        "changed_fields": ["members"],
        "rationale": "Reject a malformed or semantically empty typed member delta.",
        "effective_boundary": "after current attempts stop",
        "amendment_authority": "independent-scope-reviewer",
    }

    before_events = tuple(harness.ledger.iter_events())
    receipt = harness.service.submit(
        _command(
            "cmd_01978abc-6918-7000-8000-000000006918",
            "AmendScopeDefinition",
            SCOPE_A,
            1,
            payload,
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "invalid_scope_definition"
    assert tuple(harness.ledger.iter_events()) == before_events

    _append_exact_event(
        harness,
        command_id="cmd_01978abc-6919-7000-8000-000000006919",
        command_type="AmendScopeDefinition",
        event_type="ScopeDefinitionAmended",
        stream_id=SCOPE_A,
        payload=payload,
    )
    with pytest.raises(ValueError, match=replay_error):
        replay(
            harness.ledger.iter_events(),
            schema_registry=harness.service.schemas,
        )


def test_recorded_schema_provenance_prevents_rich_generic_reinterpretation(
    tmp_path,
):
    harness = control_plane(tmp_path)
    rich_looking_generic = _task_definition(
        TASK_A,
        "Generic provenance with rich shape",
        1,
    )
    _append_generic_task_created(
        harness,
        command_id="cmd_01978abc-6921-7000-8000-000000006921",
        task_id=TASK_A,
        payload=rich_looking_generic,
    )
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6922-7000-8000-000000006922",
            "CreateTask",
            TASK_B,
            0,
            {
                "new_task_id": TASK_B,
                "definition": _task_definition(TASK_B, "Exact Task", 1),
            },
        ),
    )
    before_events = tuple(harness.ledger.iter_events())
    command = _command(
        "cmd_01978abc-6923-7000-8000-000000006923",
        "SupersedeTask",
        TASK_A,
        1,
        {
            "task_id": TASK_A,
            "replacement_task_id": TASK_B,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["audit retains both revisions"],
            "lineage_reason": "Recorded schema identity selects the reader.",
        },
    )

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "replacement_revision_incompatible"
    assert tuple(harness.ledger.iter_events()) == before_events
    _append_exact_event(
        harness,
        command_id="cmd_01978abc-6924-7000-8000-000000006924",
        command_type="SupersedeTask",
        event_type="TaskSuperseded",
        stream_id=TASK_A,
        payload=command["payload"],
    )
    with pytest.raises(ValueError, match="Task replacement revision is incompatible"):
        replay(
            harness.ledger.iter_events(),
            schema_registry=harness.service.schemas,
        )


def test_committed_task_definition_binds_object_content(tmp_path):
    harness = control_plane(tmp_path)
    definition = _task_definition(TASK_A, "Committed definition", 1)
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6931-7000-8000-000000006931",
            "CreateTask",
            TASK_A,
            0,
            {"new_task_id": TASK_A, "definition": definition},
        ),
    )
    directory = harness.service.control_root / "objects" / "task" / TASK_A
    original = next(directory.glob("00000001-*.json"))
    tampered = _task_definition(TASK_A, "Coordinated replacement", 1)
    tampered_bytes = canonical_bytes(tampered)
    original.unlink()
    (directory / f"00000001-{sha256_hex(tampered_bytes)}.json").write_bytes(tampered_bytes)
    replacement = _task_definition(TASK_A, "Revision 2", 2)
    command = _command(
        "cmd_01978abc-6932-7000-8000-000000006932",
        "AmendTask",
        TASK_A,
        1,
        {
            "task_id": TASK_A,
            "prior_revision": 1,
            "new_revision": 2,
            "replacement_definition": replacement,
            "changed_fields": ["title", "objective"],
            "rationale": "Object content must remain ledger-bound.",
            "effective_boundary": "before redispatch",
            "authority_evidence_refs": [AUTHORITY_GRANT_ID],
        },
    )

    with pytest.raises(
        IntegrityError,
        match="differs from committed event content",
    ):
        harness.service.submit(command)


def test_committed_scope_definition_binds_object_content(tmp_path):
    harness = control_plane(tmp_path)
    created = _scope_create_payload(
        SCOPE_A,
        completion="All required members accepted.",
    )
    _submit_idempotently(
        harness,
        _command(
            "cmd_01978abc-6933-7000-8000-000000006933",
            "CreateScopeDefinition",
            SCOPE_A,
            0,
            created,
        ),
    )
    directory = harness.service.control_root / "objects" / "scope_definition" / SCOPE_A
    original = next(directory.glob("00000001-*.json"))
    tampered = {
        **created,
        "completion_predicate": "Coordinated replacement predicate.",
    }
    tampered_bytes = canonical_bytes(tampered)
    original.unlink()
    (directory / f"00000001-{sha256_hex(tampered_bytes)}.json").write_bytes(tampered_bytes)
    command = _command(
        "cmd_01978abc-6934-7000-8000-000000006934",
        "AmendScopeDefinition",
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
            "rationale": "Object content must remain ledger-bound.",
            "effective_boundary": "after current attempts stop",
            "amendment_authority": "synthetic-owner",
        },
    )

    with pytest.raises(
        IntegrityError,
        match="differs from committed event content",
    ):
        harness.service.submit(command)


def test_replay_rejects_stale_replacements_and_disposition_gaps(tmp_path):
    task_root = tmp_path / "task-stale"
    task_root.mkdir()
    task_harness = control_plane(task_root)
    for task_id, command_id in (
        (TASK_A, "cmd_01978abc-6941-7000-8000-000000006941"),
        (TASK_B, "cmd_01978abc-6942-7000-8000-000000006942"),
    ):
        _submit_idempotently(
            task_harness,
            _command(
                command_id,
                "CreateTask",
                task_id,
                0,
                {
                    "new_task_id": task_id,
                    "definition": _task_definition(task_id, task_id, 1),
                },
            ),
        )
    _append_exact_event(
        task_harness,
        command_id="cmd_01978abc-6943-7000-8000-000000006943",
        command_type="SupersedeTask",
        event_type="TaskSuperseded",
        stream_id=TASK_A,
        payload={
            "task_id": TASK_A,
            "replacement_task_id": TASK_B,
            "replacement_task_revision": 2,
            "continuing_consumer_dispositions": ["audit retains both revisions"],
            "lineage_reason": "The named replacement revision is stale.",
        },
    )
    with pytest.raises(ValueError, match="Task replacement revision is stale"):
        replay(
            task_harness.ledger.iter_events(),
            schema_registry=task_harness.service.schemas,
        )

    scope_root = tmp_path / "scope-stale"
    scope_root.mkdir()
    scope_harness = control_plane(scope_root)
    for scope_id, command_id in (
        (SCOPE_A, "cmd_01978abc-6944-7000-8000-000000006944"),
        (SCOPE_B, "cmd_01978abc-6945-7000-8000-000000006945"),
    ):
        _submit_idempotently(
            scope_harness,
            _command(
                command_id,
                "CreateScopeDefinition",
                scope_id,
                0,
                _scope_create_payload(
                    scope_id,
                    completion="all required members accepted",
                ),
            ),
        )
    _append_exact_event(
        scope_harness,
        command_id="cmd_01978abc-6946-7000-8000-000000006946",
        command_type="SupersedeScopeDefinition",
        event_type="ScopeDefinitionSuperseded",
        stream_id=SCOPE_A,
        payload={
            "scope_definition_id": SCOPE_A,
            "replacement_scope_definition_id": SCOPE_B,
            "replacement_revision": 2,
            "lineage_reason": "The named replacement revision is stale.",
            "member_dispositions": [
                {
                    "member_id": TASK_A,
                    "member_kind": "task",
                    "required_disposition": "superseded",
                }
            ],
            "effective_at": "2026-07-30T13:00:00Z",
        },
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinition replacement revision is stale",
    ):
        replay(
            scope_harness.ledger.iter_events(),
            schema_registry=scope_harness.service.schemas,
        )

    coverage_root = tmp_path / "scope-coverage"
    coverage_root.mkdir()
    coverage_harness = control_plane(coverage_root)
    for scope_id, command_id in (
        (SCOPE_A, "cmd_01978abc-6947-7000-8000-000000006947"),
        (SCOPE_B, "cmd_01978abc-6948-7000-8000-000000006948"),
    ):
        _submit_idempotently(
            coverage_harness,
            _command(
                command_id,
                "CreateScopeDefinition",
                scope_id,
                0,
                _scope_create_payload(
                    scope_id,
                    completion="all required members accepted",
                ),
            ),
        )
    _append_exact_event(
        coverage_harness,
        command_id="cmd_01978abc-6949-7000-8000-000000006949",
        command_type="SupersedeScopeDefinition",
        event_type="ScopeDefinitionSuperseded",
        stream_id=SCOPE_A,
        payload={
            "scope_definition_id": SCOPE_A,
            "replacement_scope_definition_id": SCOPE_B,
            "replacement_revision": 1,
            "lineage_reason": "Every current member requires a disposition.",
            "member_dispositions": [],
            "effective_at": "2026-07-30T13:00:00Z",
        },
    )
    with pytest.raises(
        ValueError,
        match="ScopeDefinitionSuperseded member disposition mismatch",
    ):
        replay(
            coverage_harness.ledger.iter_events(),
            schema_registry=coverage_harness.service.schemas,
        )
