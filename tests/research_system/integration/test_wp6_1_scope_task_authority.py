from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

import pytest

from research_system.authority import (
    AuthorityAdministrationContext,
    AuthorityScope,
    ScopedAuthorityGrantResolution,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError
from research_system.projection.replay import replay
from tests.research_system.factories import ACTORS, PROJECT_ID, control_plane, create_task_command


TASK_ID = "tsk_01978abc-7101-7000-8000-000000007101"
COMMAND_ID = "cmd_01978abc-7102-7000-8000-000000007102"
SCOPE_A = "obj_01978abc-7201-7000-8000-000000007201"
SCOPE_B = "obj_01978abc-7202-7000-8000-000000007202"
TASK_A = "tsk_01978abc-7203-7000-8000-000000007203"
TASK_B = "tsk_01978abc-7204-7000-8000-000000007204"
GRANTS = tuple(f"agr_01978abc-72{index:02d}-7000-8000-0000000072{index:02d}" for index in range(10, 19))


@dataclass
class DenyingResolver:
    calls: list[dict]

    def administration_context(self) -> AuthorityAdministrationContext:
        return AuthorityAdministrationContext(
            project_id=PROJECT_ID,
            store_identity="a" * 64,
            bootstrap_manifest_sha256="b" * 64,
            root_grant_id="agr_01978abc-7103-7000-8000-000000007103",
            root_grant_sha256="c" * 64,
            owner_actor_id=ACTORS["actor-a"],
        )

    def resolve_command(self, **kwargs):
        self.calls.append(kwargs)
        raise ArsError("authority command denied")


@dataclass
class RecordingResolver:
    calls: list[dict] = field(default_factory=list)
    resolutions: dict[str, ScopedAuthorityGrantResolution] = field(default_factory=dict)
    allow: bool = True

    def administration_context(self) -> AuthorityAdministrationContext:
        return AuthorityAdministrationContext(
            project_id=PROJECT_ID,
            store_identity="a" * 64,
            bootstrap_manifest_sha256="b" * 64,
            root_grant_id="agr_01978abc-7209-7000-8000-000000007209",
            root_grant_sha256="c" * 64,
            owner_actor_id=ACTORS["actor-a"],
        )

    def resolve_command(self, **kwargs):
        self.calls.append(kwargs)
        if not self.allow:
            raise ArsError("authority command denied")
        grant_id = kwargs["grant_id"]
        resolution = self.resolutions.get(grant_id)
        if resolution is None:
            resolution = ScopedAuthorityGrantResolution(
                authority_grant_id=grant_id,
                authority_grant_sha256=sha256_hex(grant_id.encode("utf-8")),
                schema_id="ars://core/scoped-authority-grant",
                schema_version="2.0.0",
                schema_sha256="e" * 64,
                actor_id=kwargs["actor_id"],
                subject_scope=AuthorityScope(
                    kwargs["project_id"],
                    kwargs["subject_kind"],
                    kwargs["subject_id"],
                ),
                effective_at=datetime(2026, 1, 1, tzinfo=UTC),
                expires_at=datetime(2030, 1, 1, tzinfo=UTC),
                activation_event_id="evt_01978abc-7208-7000-8000-000000007208",
                activation_position=1,
                administration_decision_id="arec_01978abc-7207-7000-8000-000000007207",
                administration_decision_sha256="f" * 64,
                status="active",
                revocation_event_id=None,
            )
            self.resolutions[grant_id] = resolution
        return resolution

    def scoped_grant_identity(self, grant_id: str):
        return self.resolutions.get(grant_id)


def _command(
    command_type: str,
    command_id: str,
    idempotency_key: str,
    target_stream_id: str,
    expected_stream_version: int,
    payload: dict,
    grant_id: str,
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


def test_lifecycle_authority_denial_precedes_domain_mutation(tmp_path):
    harness = control_plane(tmp_path)
    resolver = DenyingResolver([])
    harness.service.authority_resolver = resolver
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

    receipt = harness.service.submit(command)
    retry = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert retry == receipt
    assert len(resolver.calls) == 1
    call = resolver.calls[0]
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


def test_authority_denial_precedes_domain_mutation_for_all_six_commands(tmp_path):
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
        amend_scope_harness.service.submit(
            _command(
                "CreateScopeDefinition",
                "cmd_01978abc-7251-7000-8000-000000007251",
                "setup-amend-scope",
                SCOPE_A,
                0,
                _scope_create_payload(SCOPE_A),
                GRANTS[1],
            )
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
            supersede_scope_harness.service.submit(
                _command(
                    "CreateScopeDefinition",
                    command_id,
                    f"setup-supersede-scope:{scope_id}",
                    scope_id,
                    0,
                    _scope_create_payload(scope_id),
                    grant_id,
                )
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
        amend_task_harness.service.submit(
            _command(
                "CreateTask",
                "cmd_01978abc-7257-7000-8000-000000007257",
                "setup-amend-task",
                TASK_A,
                0,
                {"new_task_id": TASK_A, "definition": _task_definition(TASK_A, "Task A", "R1")},
                GRANTS[7],
            )
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
                    "authority_evidence_refs": ["synthetic-authority-evidence"],
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
            supersede_task_harness.service.submit(
                _command(
                    "CreateTask",
                    command_id,
                    f"setup-supersede-task:{task_id}",
                    task_id,
                    0,
                    {"new_task_id": task_id, "definition": _task_definition(task_id, task_id, "R1")},
                    grant_id,
                )
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
        resolver = DenyingResolver([])
        harness.service.authority_resolver = resolver
        before = _domain_snapshot(harness)
        receipt = harness.service.submit(command)
        assert receipt.status == "rejected", index
        assert resolver.calls[0]["command"].command_type == command["command_type"]
        assert _domain_snapshot(harness) == before


def test_all_six_lifecycle_commands_bind_exact_authority_inputs(tmp_path):
    harness = control_plane(tmp_path)
    resolver = RecordingResolver()
    harness.service.authority_resolver = resolver

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
            "authority_evidence_refs": ["synthetic-authority-evidence"],
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
        receipt = harness.service.submit(command)
        assert receipt.status == "accepted", command["command_type"]

    assert [call["command"].command_type for call in resolver.calls] == [
        "CreateScopeDefinition",
        "AmendScopeDefinition",
        "CreateScopeDefinition",
        "SupersedeScopeDefinition",
        "CreateTask",
        "AmendTask",
        "CreateTask",
        "SupersedeTask",
    ]
    assert [call["required_risk"] for call in resolver.calls] == [
        "R3",
        "R3",
        "R3",
        "R3",
        "R2",
        "R3",
        "R1",
        "R3",
    ]
    for call in resolver.calls:
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


def test_task_risk_binding_uses_current_and_replacement_max_and_fails_closed(tmp_path):
    harness = control_plane(tmp_path)
    resolver = RecordingResolver()
    harness.service.authority_resolver = resolver

    create = _command(
        "CreateTask",
        "cmd_01978abc-7220-7000-8000-000000007220",
        "authority-risk-create",
        TASK_A,
        0,
        {"new_task_id": TASK_A, "definition": _task_definition(TASK_A, "Risk task", "R2")},
        GRANTS[0],
    )
    assert harness.service.submit(create).status == "accepted"

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
            "authority_evidence_refs": ["synthetic-authority-evidence"],
        },
        GRANTS[1],
    )
    assert harness.service.submit(amend).status == "accepted"

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
    assert harness.service.submit(create_malformed).status == "accepted"

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
    assert harness.service.submit(supersede).status == "accepted"

    assert [call["required_risk"] for call in resolver.calls] == ["R2", "R2", "R3", "R3"]


def test_non_owner_actor_class_is_unproven_and_denied_before_domain_mutation(tmp_path):
    harness = control_plane(tmp_path)
    resolver = RecordingResolver()
    harness.service.authority_resolver = resolver
    command = create_task_command(
        "cmd_01978abc-7230-7000-8000-000000007230",
        "authority-unproven-actor",
        TASK_A,
        {"title": "Unproven actor task"},
    )
    command["actor_id"] = ACTORS["actor-b"]
    before = _domain_snapshot(harness)

    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert resolver.calls[0]["actor_class"] == "unproven"
    assert _domain_snapshot(harness) == before
    replayed = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.service.schemas)
    assert replayed["streams"] == {}
    assert replayed.get("authority_grants", {}) == {}
    assert replayed.get("authority_administration_decisions", {}) == {}


def test_authority_evidence_is_durable_for_retry_and_conflicts_on_change(tmp_path):
    harness = control_plane(tmp_path)
    resolver = RecordingResolver()
    harness.service.authority_resolver = resolver
    command = create_task_command(
        "cmd_01978abc-7240-7000-8000-000000007240",
        "authority-evidence-retry",
        TASK_A,
        {"title": "Evidence-bound task"},
    )
    first = harness.service.submit(command)
    before_retry_events = tuple(harness.ledger.iter_events())
    second = harness.service.submit(command)

    assert first.status == "accepted"
    assert second == first
    assert len(resolver.calls) == 1
    assert tuple(harness.ledger.iter_events()) == before_retry_events

    changed_payload = deepcopy(command)
    changed_payload["command_id"] = "cmd_01978abc-7241-7000-8000-000000007241"
    changed_payload["payload"]["definition"]["title"] = "Changed payload"
    with pytest.raises(ConflictError, match="idempotency key conflicts"):
        harness.service.submit(changed_payload)
    assert tuple(harness.ledger.iter_events()) == before_retry_events

    grant_id = command["authority_grant_id"]
    resolver.resolutions[grant_id] = replace(
        resolver.resolutions[grant_id],
        status="revoked",
        revocation_event_id="evt_01978abc-7242-7000-8000-000000007242",
    )
    with pytest.raises(ConflictError, match="idempotency key conflicts"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_events()) == before_retry_events
