from __future__ import annotations

import json

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ConflictError, IntegrityError
from research_system.operations.profiles import CURRENT_OPERATIONAL_PROFILE_POLICY
from research_system.operations.resources import (
    TrustedRuntimeAuthority,
    derive_resource_grant_authority_preimage_ref,
)
from research_system.projection.replay import apply_event, replay
from tests.research_system.factories import (
    ACTORS,
    AUTHORITY_GRANT_ID,
    PROJECT_ID,
    activate_lifecycle_grant,
    control_plane,
    create_task_command,
    scoped_lifecycle_grant_id,
)


TASK_ID = "tsk_01978abc-7200-7000-8000-000000007200"
OTHER_TASK_ID = "tsk_01978abc-7201-7000-8000-000000007201"
DISPATCH_ID = "dsp_01978abc-7202-7000-8000-000000007202"
OTHER_DISPATCH_ID = "dsp_01978abc-7213-7000-8000-000000007213"
ATTEMPT_ID = "att_01978abc-7203-7000-8000-000000007203"
OTHER_ATTEMPT_ID = "att_01978abc-7221-7000-8000-000000007221"
RESOURCE_REQUEST_ID = "rsq_01978abc-7204-7000-8000-000000007204"
RESOURCE_GRANT_ID = "rgr_01978abc-7205-7000-8000-000000007205"
OTHER_RESOURCE_REQUEST_ID = "rsq_01978abc-7214-7000-8000-000000007214"
OTHER_RESOURCE_GRANT_ID = "rgr_01978abc-7215-7000-8000-000000007215"
LEASE_ID = "els_01978abc-7206-7000-8000-000000007206"
OTHER_LEASE_ID = "els_01978abc-7207-7000-8000-000000007207"
PROCESS_ID = "pid_01978abc-7208-7000-8000-000000007208"
OTHER_PROCESS_ID = "pid_01978abc-7209-7000-8000-000000007209"
CONTEXT_ID = "ctx_01978abc-7212-7000-8000-000000007212"
HEARTBEAT_ID = "hbt_01978abc-7210-7000-8000-000000007210"
OTHER_HEARTBEAT_ID = "hbt_01978abc-7216-7000-8000-000000007216"
CHECKPOINT_ID = "cpm_01978abc-7211-7000-8000-000000007211"
POLICY_ID = "pol_01978abc-7212-7000-8000-000000007212"
OPERATOR_RELEASE_GRANT_ID = "agr_01978abc-7220-7000-8000-000000007220"

GRANTED_AT = "2026-08-01T12:00:00Z"
INITIAL_EXPIRY = "2026-08-01T13:00:00Z"
GRANT_EXPIRY = "2026-08-01T13:30:00Z"
RENEWED_EXPIRY = "2026-08-01T13:15:00Z"
OBSERVED_AT = "2026-08-01T12:20:00Z"
C1_NOW = datetime(2026, 8, 1, 12, 30, tzinfo=UTC)
HEARTBEAT_AT = "2026-08-01T12:30:00Z"
NEXT_HEARTBEAT_AT = "2026-08-01T12:31:00Z"
C1_TRUSTED_RUNTIME_AUTHORITY = TrustedRuntimeAuthority(
    host_identity="host:sha256:" + "a" * 64,
    boot_identity="boot:sha256:" + "b" * 64,
    control_store_identity="c" * 64,
    store_manifest_sha256="d" * 64,
)


C1_ROWS = (
    ("task.request_readiness", "RequestReadiness", ("ReadinessRequested",)),
    ("task.approve_readiness", "ApproveReadiness", ("ReadinessApproved",)),
    # ClaimDispatch owns one ordered two-event transaction for each owner row.
    ("task.claim_start", "ClaimDispatch", ("DispatchClaimed", "TaskClaimStarted")),
    ("dispatch.issue", "IssueDispatch", ("DispatchIssued",)),
    ("dispatch.deliver", "RecordDispatchDelivery", ("DispatchDelivered",)),
    ("dispatch.acknowledge", "AcknowledgeDispatch", ("DispatchAcknowledged",)),
    ("dispatch.claim", "ClaimDispatch", ("DispatchClaimed", "TaskClaimStarted")),
    ("dispatch.expire_issued", "ExpireDispatch", ("DispatchExpired",)),
    ("dispatch.expire_delivered", "ExpireDispatch", ("DispatchExpired",)),
    ("dispatch.expire_acknowledged", "ExpireDispatch", ("DispatchExpired",)),
    ("dispatch.withdraw_issued", "WithdrawDispatch", ("DispatchWithdrawn",)),
    ("lease.activate", "ClaimExecutionLease", ("LeaseGranted",)),
    ("lease.renew", "RenewExecutionLease", ("LeaseRenewed",)),
    ("lease.release", "ReleaseExecutionLease", ("LeaseReleased",)),
    ("lease.expire", "ExpireLease", ("LeaseExpired",)),
    ("lease.revoke", "RevokeLease", ("LeaseRevoked",)),
    ("attempt.create", "CreateAttempt", ("AttemptCreated",)),
    ("attempt.claim", "ClaimAttempt", ("AttemptClaimed",)),
    ("attempt.start", "StartAttempt", ("AttemptStarted",)),
    ("operator.request_resource_grant", "RequestResourceGrant", ("ResourceGrantRequested",)),
    ("operator.claim_execution_lease", "ClaimExecutionLease", ("LeaseGranted",)),
    ("operator.record_heartbeat", "RecordHeartbeat", ("HeartbeatRecorded",)),
    ("operator.release_resources", "ReleaseResources", ("ResourcesReleased",)),
)

COMMAND_SCHEMA_SHA256 = {
    "RequestReadiness": "caf2b31f2acc666c0395a7a671c33957dfb7efb8c4db65afc553069ab6e80c5c",
    "ApproveReadiness": "26952636785fce275b8a7109d9b90b1ba6011c5b5605132344cd948311ff78f7",
    "IssueDispatch": "0e72d14c5f5c9ab92aa0f9bd38a36ca9e208f04c921070e2f0afd92e80619462",
    "RecordDispatchDelivery": "04728e65c975cbf10a1b23307fbd9fa8244f8d6a1a51436ddfa46071b1498942",
    "AcknowledgeDispatch": "ca684168885d6b9531cd35a7163601c7d9d499194faea3f99824a0bfd0e99b57",
    "ClaimDispatch": "ffbc261aba4741cbb0b5d937499eef3e70763381fa6d1907253eeb87fba45c7f",
    "ExpireDispatch": "297f938a1eabf729fb9539a4d293fa461d20458fcbd27188863805b91db5a19d",
    "WithdrawDispatch": "1c8004e3218616c4c55598be051bd0be40de95901dbe11e04cee2900a29204d5",
    "ClaimExecutionLease": "a05e176483dadefdf961de3db9432cb1afe110605ae84b9fef194ff9b3bac745",
    "RenewExecutionLease": "28efd26b2e843aa007c52b17ef24236e83941b9c8c5377be3be063d795ce911e",
    "ReleaseExecutionLease": "441756d56ef0349d96c22abe48573eea601fbda4a91ad9a21a44ef9f68f31ae3",
    "ExpireLease": "88412b288968b28e2b11b37350aafb9e5d4e0f88f007a9da24f5dc1472dc3afe",
    "RevokeLease": "510556548df6f43acb34158d6c3b532bca4b70c82e2faf7b8109a3e421b5aeb8",
    "CreateAttempt": "c05ebc6cddbe5698b122a63b19423f98e816c97b1033a0e8f0fa02d33b5a58be",
    "ClaimAttempt": "9d08bbc270978a1b88fec5e122bad4511c45316fd4fd37967ebcdab2a8ffb220",
    "StartAttempt": "d61da75848058fe7621d5052c2c0e27d0653ace6b48e7f3b901f06559efd4d43",
    "RequestResourceGrant": "8a249187b7797cf30ffae5e342fe265a5b3a372269c8b20f13742b50630dfad3",
    "RecordHeartbeat": "b387fdd14389ed16ed53ba20d63732861d7b3ddd93bd69aa100d4811a7403f94",
    "ReleaseResources": "21ed97a83b5536920c4886cdba853d0e811521fc1db234fcf6b88549cc463df0",
}

EVENT_SCHEMA_SHA256 = {
    "ReadinessRequested": "bd432fbf6bbd5c97ff6147b86931adfe846ccf0a9b150263a5cdb0d7fade4d79",
    "ReadinessApproved": "d6df570f67486ab4a2ce6a3005fe72cc6caa245d0ac1eaa30f47bdc65c3e1b55",
    "DispatchIssued": "525b617bdd136673f8717b775d9460fb9da55ca037022cc10f0cb8bef7a61af7",
    "DispatchDelivered": "7febfbd93b70671f7ac3ee55dbc2da9ce131aebdebfd994cfec045627990ccdc",
    "DispatchAcknowledged": "64ed204e229ddf0914020359b01c432696f9bbbc78be60a8dffe3d3116230f2a",
    "DispatchClaimed": "282a636978fdb57bb813f6145e8f45f10180b54da7f5a8a085cee8b4ac63ca88",
    "TaskClaimStarted": "54f74a4f3e47418dbc97f57f1a3c81517a2331e3e5da71c6fbc427d6aae59331",
    "DispatchExpired": "0f01389280795f0d108bb61ad9d0b9713bdf719896a72f8f1952866579428300",
    "DispatchWithdrawn": "9800ebdccbe54f7c0ed7ac25fadc40f3d801fca48a4b218637388dfa5f5b3eca",
    "LeaseGranted": "f23fe9fe580872a1017fab954e19524fc9084f5111732e06d15cbbdea2251121",
    "LeaseRenewed": "c2a5942a50027add02e7907b5f7bdc582bea1bf821ceeaf34a805c071556d73b",
    "LeaseReleased": "8985195917c0f70f91124674f44902478a97b88d80e7f82bbc3ba2f62c862b77",
    "LeaseExpired": "3aa4f643eefc3ec70af4dbb626c358b1e439b5f4ece2759e2ce036bc1acec240",
    "LeaseRevoked": "7a5612a2fd072aabc23c18e099b2a7c8d01fb9adcd20f89863aeff7633431fa0",
    "AttemptCreated": "525df4534bf94ef85d67bcb3d01bbcafd8bfe1e16272799c615ac728b0a6852c",
    "AttemptClaimed": "4a341f83ed93e083393752abfc2675c0bf7716f6170ec18a0f985d9aa54bc285",
    "AttemptStarted": "bb0e917b7f62367932fe52501f2834e562d0918948b5cf9e59e7035e179cc74c",
    "ResourceGrantRequested": "6fec58ce3bd851f58889d46f5d09c47cbab6e2c827ce36119d8e3e48fa576ee7",
    "HeartbeatRecorded": "cb505aaefea412654dd518f6ef93de6e6f33607ec20e5457171565aa52440aa5",
    "ResourcesReleased": "49f4d980a0c521a0c9ce27b07b3513a9ab6ca781e6129a2758fb85e3380b2730",
}


def _command_id(number: int) -> str:
    return f"cmd_01978abc-7300-7000-8000-{number:012d}"


def _c1_command(
    command_id: str,
    command_type: str,
    target_stream_id: str,
    expected_stream_version: int,
    payload: dict[str, Any],
    *,
    authority_grant_id: str = AUTHORITY_GRANT_ID,
    actor_id: str = ACTORS["actor-a"],
) -> dict[str, Any]:
    return {
        "command_id": command_id,
        "command_type": command_type,
        "schema_id": f"ars://core/command/{command_type}",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-01T12:00:00Z",
        "actor_id": actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": authority_grant_id,
        "target_stream_id": target_stream_id,
        "expected_stream_version": expected_stream_version,
        "idempotency_key": f"wp6-1-c1:{command_type}:{command_id}",
        "correlation_id": f"wp6-1-c1:{TASK_ID}",
        "causation_id": None,
        "reason": "exercise the frozen C1 readiness and lease/resource seam",
        "evidence_refs": [],
        "project_id": PROJECT_ID,
        "payload": payload,
    }


def _request_readiness_command(
    *,
    number: int,
    task_id: str = TASK_ID,
    task_revision: int = 1,
    expected_stream_version: int = 1,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RequestReadiness",
        task_id,
        expected_stream_version,
        {
            "task_id": task_id,
            "task_revision": task_revision,
            "readiness_evidence_refs": evidence_refs or ["evidence:readiness:r1"],
        },
    )


def _approve_readiness_command(
    *,
    number: int,
    task_id: str = TASK_ID,
    task_revision: int = 1,
    expected_stream_version: int = 2,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    refs = evidence_refs or ["evidence:readiness:r1"]
    return _c1_command(
        _command_id(number),
        "ApproveReadiness",
        task_id,
        expected_stream_version,
        {
            "task_id": task_id,
            "task_revision": task_revision,
            "readiness_evidence_refs": refs,
            "passed_check_ids": ["check:definition-complete", "check:readiness-current"],
        },
    )


def _dispatch_definition() -> dict[str, Any]:
    return {
        "dispatch_id": DISPATCH_ID,
        "task_id": TASK_ID,
        "task_revision": 1,
        "target_role": "bounded-worker",
        "target_profile": "luna-max",
        "target_actor_id": ACTORS["actor-a"],
        "model_eval_profile_ref": "model-eval:bounded:v1",
        "context_packet_id": CONTEXT_ID,
        "policy_version": POLICY_ID,
        "assurance_plan_version": "1.0.0",
        "root_bindings": [
            {
                "root_kind": "workspace",
                "canonical_uri": "C:/workspace/c1",
                "workspace_identity": "workspace:c1-synthetic",
                "access_mode": "read_write",
                "expected_branch": "codex/wp6-1-c1-resource-grant",
                "expected_commit": "git:sha1:" + "a" * 40,
                "provenance_authority": "owner:c1",
            }
        ],
        "branch_identity": "codex/wp6-1-c1-resource-grant",
        "worktree_identity": "worktree:c1-synthetic",
        "expected_commit": "git:sha1:" + "a" * 40,
        "capabilities": ["run:task"],
        "permissions": ["write:workspace"],
        "resource_request_id": RESOURCE_REQUEST_ID,
        "output_namespace": "results:c1-synthetic",
        "delivery_deadline": INITIAL_EXPIRY,
        "claim_deadline": INITIAL_EXPIRY,
        "concurrency_mode": "exclusive",
        "stop_rules": ["stop on failed contract"],
        "partial_rules": ["retain partial output"],
        "escalation_rules": ["escalate to c1-owner"],
    }


def _issue_dispatch_command(*, number: int, definition: dict[str, Any] | None = None) -> dict[str, Any]:
    definition = _dispatch_definition() if definition is None else definition
    return _c1_command(
        _command_id(number),
        "IssueDispatch",
        DISPATCH_ID,
        0,
        {"dispatch_id": DISPATCH_ID, "definition": definition},
    )


def _record_dispatch_delivery_command(*, number: int, expected_stream_version: int = 1) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RecordDispatchDelivery",
        DISPATCH_ID,
        expected_stream_version,
        {
            "dispatch_id": DISPATCH_ID,
            "delivery_adapter_id": "adapter:c1-synthetic",
            "recipient_actor_id": ACTORS["actor-a"],
            "delivery_evidence_refs": ["evidence:dispatch-delivery:c1"],
        },
    )


def _acknowledge_dispatch_command(*, number: int, expected_stream_version: int = 2) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "AcknowledgeDispatch",
        DISPATCH_ID,
        expected_stream_version,
        {
            "dispatch_id": DISPATCH_ID,
            "acknowledged_at": OBSERVED_AT,
            "recipient_actor_id": ACTORS["actor-a"],
            "delivery_identity": "delivery:c1-synthetic",
        },
    )


def _expire_dispatch_command(
    *,
    number: int,
    expected_stream_version: int,
    observed_prior_state: str,
    observed_deadline: str,
    observed_at: str,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ExpireDispatch",
        DISPATCH_ID,
        expected_stream_version,
        {
            "dispatch_id": DISPATCH_ID,
            "observed_prior_state": observed_prior_state,
            "observed_deadline": observed_deadline,
            "observed_at": observed_at,
            "scheduler_authority_ref": "scheduler:c1",
        },
    )


def _withdraw_dispatch_command(
    *,
    number: int,
    expected_stream_version: int,
    observed_prior_state: str = "issued",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dispatch_id": DISPATCH_ID,
        "observed_prior_state": observed_prior_state,
        "withdrawal_reason": "withdraw the bounded C1 Dispatch",
    }
    if observed_prior_state == "claimed":
        payload["attempt_stop_disposition"] = {
            "process_state": "stopped",
            "children_closed": True,
            "writers_closed": True,
            "evidence_refs": ["evidence:attempt-stop:c1"],
        }
    return _c1_command(
        _command_id(number),
        "WithdrawDispatch",
        DISPATCH_ID,
        expected_stream_version,
        payload,
    )


def _claim_dispatch_command(harness, *, number: int) -> dict[str, Any]:
    snapshot = harness.ledger.snapshot()
    return _c1_command(
        _command_id(number),
        "ClaimDispatch",
        DISPATCH_ID,
        3,
        {
            "dispatch_id": DISPATCH_ID,
            "task_id": TASK_ID,
            "task_revision": 1,
            "lease_id": LEASE_ID,
            "expected_dispatch_stream_version": 3,
            "expected_task_stream_version": snapshot.stream_versions[TASK_ID],
            "declared_write_set": ["dispatch", "task"],
            "expected_global_position": len(snapshot.events),
            "expected_tail_hash": snapshot.events[-1]["event_hash"],
        },
    )


def _create_attempt_command(*, number: int) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "CreateAttempt",
        ATTEMPT_ID,
        0,
        {
            "new_attempt_id": ATTEMPT_ID,
            "task_id": TASK_ID,
            "task_revision": 1,
            "dispatch_id": DISPATCH_ID,
            "attempt_ordinal": 1,
            "execution_epoch": 1,
        },
    )


def _claim_attempt_command(*, number: int, expected_stream_version: int = 1) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ClaimAttempt",
        ATTEMPT_ID,
        expected_stream_version,
        {
            "attempt_id": ATTEMPT_ID,
            "lease_id": LEASE_ID,
            "task_id": TASK_ID,
            "task_revision": 1,
            "dispatch_id": DISPATCH_ID,
        },
    )


def _start_attempt_command(*, number: int, expected_stream_version: int = 2) -> dict[str, Any]:
    definition = _dispatch_definition()
    return _c1_command(
        _command_id(number),
        "StartAttempt",
        ATTEMPT_ID,
        expected_stream_version,
        {
            "attempt_id": ATTEMPT_ID,
            "process_identity_id": PROCESS_ID,
            "session_identity": "session:c1-luna",
            "context_packet_id": definition["context_packet_id"],
            "root_bindings": definition["root_bindings"],
            "code_identity": "git:sha1:" + "b" * 40,
            "environment_fingerprint": "c" * 64,
        },
    )


def _resource_request_payload(
    *,
    expected_control_store_position: int,
    trusted_runtime_authority: TrustedRuntimeAuthority,
    resource_grant_id: str = RESOURCE_GRANT_ID,
    resource_request_id: str = RESOURCE_REQUEST_ID,
    dispatch_id: str = DISPATCH_ID,
) -> dict[str, Any]:
    evidence = {
        "disposition": "required",
        "policy_id": CURRENT_OPERATIONAL_PROFILE_POLICY.policy_id,
        "rationale": "The bounded execution profile requires this evidence.",
        "applicability_evidence_refs": ["evidence:resource-profile:bounded"],
    }
    request = {
        "resource_id": resource_grant_id,
        "resource_request": {
            "task_id": TASK_ID,
            "dispatch_id": dispatch_id,
            "attempt_id": ATTEMPT_ID,
            "operation_class": "bounded-analysis",
            "operational_profile": "bounded",
            "resource_request_id": resource_request_id,
            "route_id": "route:c1-synthetic",
            "provider_requirements": ["python"],
            "runtime_requirements": ["direct-venv"],
            "operational_profile_policy_id": CURRENT_OPERATIONAL_PROFILE_POLICY.policy_id,
            "operational_profile_revision": CURRENT_OPERATIONAL_PROFILE_POLICY.policy_revision,
            "requesting_actor_id": ACTORS["actor-a"],
            "requesting_profile": "luna-max",
            "requesting_authority_grant_id": scoped_lifecycle_grant_id(resource_grant_id),
            "expected_control_store_position": expected_control_store_position,
            "requested_host_pool": [trusted_runtime_authority.host_identity],
            "root_bindings": [
                {
                    "root_kind": "workspace",
                    "canonical_uri": "C:/workspace/c1",
                    "workspace_identity": "workspace:c1-synthetic",
                    "access_mode": "read_write",
                    "expected_branch": "codex/wp6-1-c1-luna-readiness-lease",
                    "expected_commit": "git:sha1:" + "a" * 40,
                    "provenance_authority": "owner:c1",
                }
            ],
            "resource_ceilings": {
                "cpu_processes": 1,
                "cpu_threads": 4,
                "ram_working_bytes": 1024,
                "ram_peak_bytes": 2048,
                "gpu_devices": [],
                "storage_bytes": 4096,
                "io_bytes": 4096,
            },
            "network_constraints": ["network:none"],
            "external_write_constraints": ["external:none"],
            "sensitivity_constraints": ["internal"],
            "exclusive_resource_keys": ["workspace:c1"],
            "shared_resource_keys": [],
            "compatibility_keys": ["python:3.13"],
            "runtime_distribution": {
                "minimum_seconds": 1,
                "expected_seconds": 10,
                "maximum_seconds": 60,
                "uncertainty_basis": "synthetic bounded fixture",
            },
            "deadline": GRANT_EXPIRY,
            "checkpoint_interval_seconds": 30,
            "benchmark_evidence_refs": ["evidence:benchmark:bounded"],
            "projection_evidence_refs": [],
            "stop_rules": ["stop on failed contract"],
            "pause_rules": ["pause on owner request"],
            "partial_rules": ["retain partial output"],
            "escalation_rules": ["escalate to c1-owner"],
            "release_obligations": ["release lease before completion"],
            "cleanup_obligations": ["remove temporary workspace"],
            "bounded_profile_evidence": {
                "heartbeat": evidence,
                "output_tail": evidence,
                "stop": evidence,
                "checkpoint": evidence,
            },
        },
    }
    request["resource_request"]["projection_evidence_refs"] = [
        derive_resource_grant_authority_preimage_ref(
            project_id=PROJECT_ID,
            resource_grant_id=resource_grant_id,
            resource_request=request["resource_request"],
            trusted_authority=trusted_runtime_authority,
        )
    ]
    return request


def _assert_authoritative_resource_grant(harness, *, resource_grant_id: str = RESOURCE_GRANT_ID) -> dict[str, Any]:
    events = [
        event
        for event in harness.ledger.iter_events()
        if event["event_type"] == "ResourceGrantRequested" and event["stream_id"] == resource_grant_id
    ]
    assert len(events) == 1
    event = events[0]
    request = event["payload"]["resource_request"]
    grant = harness.objects.read("resource_grant", resource_grant_id, 1)
    assert grant["schema_id"] == "ars://operations/resource-grant"
    assert grant["schema_version"] == "1.1.0"
    assert grant["record_revision"] == 1
    assert grant["resource_grant_id"] == resource_grant_id
    assert grant["source_event_id"] == event["event_id"]
    assert grant["source_event_hash"] == event["event_hash"]
    assert grant["source_command_id"] == event["command_id"]
    assert grant["source_command_payload_hash"] == event["command_payload_hash"]
    assert grant["resource_request_sha256"] == sha256_hex(canonical_bytes(request))
    assert grant["authority_preimage_ref"] == request["projection_evidence_refs"][0]
    assert grant["granted_claims"] == json.loads(canonical_bytes(request).decode("utf-8"))
    immutable_content = {key: value for key, value in grant.items() if key != "content_hash"}
    assert grant["content_hash"] == sha256_hex(canonical_bytes(immutable_content))
    return grant


def _rebind_resource_request_authority_ref(harness, request_payload: dict[str, Any]) -> None:
    request = request_payload["resource_request"]
    request["projection_evidence_refs"] = [
        derive_resource_grant_authority_preimage_ref(
            project_id=PROJECT_ID,
            resource_grant_id=request_payload["resource_id"],
            resource_request=request,
            trusted_authority=harness.service._current_trusted_runtime_authority(),
        )
    ]


def _request_resource_command(
    harness,
    *,
    number: int,
    resource_grant_id: str = RESOURCE_GRANT_ID,
    resource_request_id: str = RESOURCE_REQUEST_ID,
    dispatch_id: str = DISPATCH_ID,
    expected_control_store_position: int | None = None,
) -> dict[str, Any]:
    snapshot = harness.ledger.snapshot()
    expected_control_store_position = (
        snapshot.global_position if expected_control_store_position is None else expected_control_store_position
    )
    return _c1_command(
        _command_id(number),
        "RequestResourceGrant",
        resource_grant_id,
        0,
        _resource_request_payload(
            expected_control_store_position=expected_control_store_position,
            trusted_runtime_authority=harness.service._current_trusted_runtime_authority(),
            resource_grant_id=resource_grant_id,
            resource_request_id=resource_request_id,
            dispatch_id=dispatch_id,
        ),
    )


def _claim_execution_lease_command(
    *,
    number: int,
    lease_id: str = LEASE_ID,
    expected_stream_version: int = 0,
    resource_grant_id: str = RESOURCE_GRANT_ID,
    dispatch_id: str = DISPATCH_ID,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ClaimExecutionLease",
        lease_id,
        expected_stream_version,
        {
            "new_lease_id": lease_id,
            "task_id": TASK_ID,
            "task_revision": 1,
            "dispatch_id": dispatch_id,
            "attempt_id": ATTEMPT_ID,
            "expires_at": INITIAL_EXPIRY,
            "holder_actor_id": ACTORS["actor-a"],
            "resource_grant_id": resource_grant_id,
            "holder_profile": "luna-max",
            "holder_session": "session:c1-luna",
            "capability_scope": ["run:task", "write:workspace"],
            "granted_at": GRANTED_AT,
            "renewal_policy_ref": _renewal_policy_ref("bounded"),
            "operational_profile": "bounded",
        },
    )


def _heartbeat_command(
    *,
    number: int,
    expected_stream_version: int = 1,
    lease_id: str = LEASE_ID,
    heartbeat_id: str = HEARTBEAT_ID,
    heartbeat_sequence: int = 1,
    wall_time: str = HEARTBEAT_AT,
    monotonic_time: int = 120,
    work_unit_progress: int = 1,
    host_identity: str = C1_TRUSTED_RUNTIME_AUTHORITY.host_identity,
    boot_identity: str = C1_TRUSTED_RUNTIME_AUTHORITY.boot_identity,
    process_identity_id: str = PROCESS_ID,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RecordHeartbeat",
        lease_id,
        expected_stream_version,
        {
            "lease_id": lease_id,
            "heartbeat_sequence": heartbeat_sequence,
            "process_identity_id": process_identity_id,
            "heartbeat_id": heartbeat_id,
            "wall_time": wall_time,
            "monotonic_time": monotonic_time,
            "host_identity": host_identity,
            "boot_identity": boot_identity,
            "work_unit_progress": work_unit_progress,
            "progress_evidence_refs": ["evidence:progress:1"],
            "cpu_observation": 1,
            "ram_observation_bytes": 1024,
            "io_observation_bytes": 256,
            "gpu_observations": [],
            "checkpoint_manifest_id": CHECKPOINT_ID,
            "output_tail_sha256": "b" * 64,
            "blocker_warning_stop_state": "none",
        },
    )


def _renew_lease_command(
    *,
    number: int,
    expected_stream_version: int,
    holder_actor_id: str = ACTORS["actor-a"],
    prior_expiry: str = INITIAL_EXPIRY,
    new_expiry: str = RENEWED_EXPIRY,
    heartbeat_evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RenewExecutionLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "holder_actor_id": holder_actor_id,
            "prior_expiry": prior_expiry,
            "new_expiry": new_expiry,
            "renewal_policy_ref": _renewal_policy_ref("bounded"),
            "heartbeat_evidence_refs": [HEARTBEAT_ID] if heartbeat_evidence_refs is None else heartbeat_evidence_refs,
        },
    )


def _release_lease_command(
    *,
    number: int,
    expected_stream_version: int,
    holder_actor_id: str = ACTORS["actor-a"],
    observed_at: str = OBSERVED_AT,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ReleaseExecutionLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "release_reason": "bounded C1 operation completed",
            "holder_actor_id": holder_actor_id,
            "observed_at": observed_at,
        },
    )


def _expire_lease_command(
    *,
    number: int,
    expected_stream_version: int,
    observed_at: str = OBSERVED_AT,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ExpireLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "observed_at": observed_at,
            "scheduler_authority_ref": "scheduler:c1",
        },
    )


def _revoke_lease_command(
    *,
    number: int,
    expected_stream_version: int,
    observed_at: str = OBSERVED_AT,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RevokeLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "revocation_reason": "owner revoked the bounded lease",
            "observed_at": observed_at,
        },
    )


def _release_resources_command(
    *,
    number: int,
    expected_stream_version: int = 1,
    resource_grant_id: str = RESOURCE_GRANT_ID,
    lease_id: str = LEASE_ID,
    consumption_reconciliation: list[str] | None = None,
    cleanup_evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ReleaseResources",
        resource_grant_id,
        expected_stream_version,
        {
            "resource_id": resource_grant_id,
            "lease_id": lease_id,
            "consumption_reconciliation": (
                ["cpu=1", "ram=1024", "io=256"] if consumption_reconciliation is None else consumption_reconciliation
            ),
            "cleanup_evidence_refs": (
                ["evidence:cleanup:c1"] if cleanup_evidence_refs is None else cleanup_evidence_refs
            ),
        },
    )


def _create_task(
    harness,
    *,
    command_number: int = 1,
    authority_grant_id: str | None = None,
) -> dict[str, Any]:
    command = create_task_command(
        _command_id(command_number),
        f"wp6-1-c1:create-task:{command_number}",
        TASK_ID,
        {"title": "C1 readiness and lease task"},
    )
    if authority_grant_id is not None:
        command["authority_grant_id"] = authority_grant_id
    receipt = harness.service.submit(command)
    assert receipt.status == "accepted"
    return command


def _task_amendment_command(*, number: int, expected_stream_version: int = 2) -> dict[str, Any]:
    source = create_task_command(
        _command_id(number + 100),
        f"wp6-1-c1:amend-definition:{number}",
        TASK_ID,
        {"title": "C1 amended readiness and lease task"},
    )
    replacement = deepcopy(source["payload"]["definition"])
    replacement["revision"] = 2
    replacement["title"] = "C1 amended readiness and lease task"
    replacement["objective"] = "Complete the amended C1 readiness and lease task"
    replacement.pop("content_sha256")
    replacement["content_sha256"] = sha256_hex(canonical_bytes(replacement))
    return _c1_command(
        _command_id(number),
        "AmendTask",
        TASK_ID,
        expected_stream_version,
        {
            "task_id": TASK_ID,
            "prior_revision": 1,
            "new_revision": 2,
            "replacement_definition": replacement,
            "changed_fields": ["title", "objective"],
            "rationale": "Amendment must invalidate readiness evidence for revision 1.",
            "effective_boundary": "before redispatch",
            "authority_evidence_refs": [AUTHORITY_GRANT_ID],
        },
        authority_grant_id=AUTHORITY_GRANT_ID,
    )


def _json_files(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*.json")}


def _claim_dispatch_scoped_index_path(harness) -> Path:
    matches = [
        path
        for path in harness.receipts.index_root.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("scope", [None, None, None])[2] == "ClaimDispatch"
    ]
    assert len(matches) == 1
    return matches[0]


def _renewal_policy_ref(profile_name: str) -> str:
    return (
        "ars://operations/operational-profile-policy/"
        f"{CURRENT_OPERATIONAL_PROFILE_POLICY.policy_id}/"
        f"{CURRENT_OPERATIONAL_PROFILE_POLICY.policy_revision}/{profile_name}/renewal"
    )


def _c1_control_plane(tmp_path: Path, *, now: datetime = C1_NOW):
    return control_plane(
        tmp_path,
        clock=lambda: now,
        trusted_runtime_authority_provider=lambda: C1_TRUSTED_RUNTIME_AUTHORITY,
    )


def _mutable_c1_control_plane(tmp_path: Path):
    clock = {"now": C1_NOW}
    return (
        control_plane(
            tmp_path,
            clock=lambda: clock["now"],
            trusted_runtime_authority_provider=lambda: C1_TRUSTED_RUNTIME_AUTHORITY,
        ),
        clock,
    )


def _mutable_c1_authority_control_plane(tmp_path: Path):
    authority = {"current": C1_TRUSTED_RUNTIME_AUTHORITY}
    harness = control_plane(
        tmp_path,
        clock=lambda: C1_NOW,
        trusted_runtime_authority_provider=lambda: authority["current"],
    )
    return harness, authority


def _drifted_runtime_authority(binding: str) -> TrustedRuntimeAuthority:
    values = {
        "host_identity": C1_TRUSTED_RUNTIME_AUTHORITY.host_identity,
        "boot_identity": C1_TRUSTED_RUNTIME_AUTHORITY.boot_identity,
        "control_store_identity": C1_TRUSTED_RUNTIME_AUTHORITY.control_store_identity,
        "store_manifest_sha256": C1_TRUSTED_RUNTIME_AUTHORITY.store_manifest_sha256,
    }
    replacements = {
        "host_identity": "host:sha256:" + "e" * 64,
        "boot_identity": "boot:sha256:" + "f" * 64,
        "control_store_identity": "9" * 64,
        "store_manifest_sha256": "8" * 64,
    }
    values[binding] = replacements[binding]
    return TrustedRuntimeAuthority(**values)


def _resource_grant_path(harness) -> Path:
    matches = sorted(
        (harness.objects.control_root / "objects" / "resource_grant" / RESOURCE_GRANT_ID).glob("00000001-*.json")
    )
    assert len(matches) == 1
    return matches[0]


def _replace_resource_grant_record(harness, record: dict[str, Any]) -> None:
    _resource_grant_path(harness).unlink()
    harness.objects.write("resource_grant", RESOURCE_GRANT_ID, 1, record)


def _domain_snapshot(harness) -> dict[str, Any]:
    events = tuple(harness.ledger.iter_events())
    ledger_snapshot = harness.ledger.snapshot()
    return {
        "events": events,
        "batches": tuple(harness.ledger.iter_batches()),
        "stream_versions": dict(ledger_snapshot.stream_versions),
        "objects": _json_files(harness.objects.control_root / "objects"),
        "projection": replay(events, schema_registry=harness.schemas),
    }


def _fold_trusted_c1_tail_batches(
    prefix_state: dict[str, Any],
    batches: tuple[tuple[dict[str, Any], ...], ...],
) -> dict[str, Any]:
    """Apply already-validated physical tail batches without partial publication."""

    state = deepcopy(prefix_state)
    for batch in batches:
        candidate = deepcopy(state)
        for event in batch:
            candidate = apply_event(candidate, event)
            candidate["last_position"] = event["global_position"]
            candidate["last_hash"] = event["event_hash"]
        state = candidate
    return state


def _grant_admission_snapshot(harness) -> dict[str, Any]:
    return {
        **_domain_snapshot(harness),
        "receipts": _json_files(harness.objects.control_root / "receipts"),
    }


def _rejection_snapshot(harness) -> dict[str, Any]:
    receipts = _json_files(harness.objects.control_root / "receipts")
    return {
        **_domain_snapshot(harness),
        "accepted_receipts": {
            path: value
            for path, value in receipts.items()
            if (record := json.loads(value)).get("receipt", record).get("status") == "accepted"
        },
    }


def _assert_event(
    harness,
    command: dict[str, Any],
    *,
    event_type: str,
    resulting_stream_version: int,
    event_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = harness.service.submit(command)
    assert isinstance(receipt, Receipt)
    assert receipt.status == "accepted"
    event = tuple(harness.ledger.iter_events())[-1]
    assert event["event_type"] == event_type
    assert event["schema_id"] == f"ars://core/event/{event_type}"
    assert event["schema_version"] == "1.0.0"
    assert event["stream_id"] == command["target_stream_id"]
    assert event["stream_version"] == resulting_stream_version
    assert event["command_id"] == command["command_id"]
    assert event["command_type"] == command["command_type"]
    assert event["command_schema_id"] == command["schema_id"]
    assert event["command_schema_version"] == command["schema_version"]
    assert event["payload"] == (command["payload"] if event_payload is None else event_payload)
    return event


def _seed_ready_task(harness) -> None:
    _create_task(harness, command_number=1)
    _assert_event(
        harness,
        _request_readiness_command(number=2),
        event_type="ReadinessRequested",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _approve_readiness_command(number=3),
        event_type="ReadinessApproved",
        resulting_stream_version=3,
    )


def _seed_acknowledged_dispatch(harness) -> None:
    _assert_event(
        harness,
        _issue_dispatch_command(number=100),
        event_type="DispatchIssued",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _record_dispatch_delivery_command(number=101),
        event_type="DispatchDelivered",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _acknowledge_dispatch_command(number=102),
        event_type="DispatchAcknowledged",
        resulting_stream_version=3,
    )


def _seed_preclaim_dispatch(harness, *, state: str, definition: dict[str, Any]) -> None:
    _seed_ready_task(harness)
    _assert_event(
        harness,
        _issue_dispatch_command(number=100, definition=definition),
        event_type="DispatchIssued",
        resulting_stream_version=1,
    )
    if state == "issued":
        return
    _assert_event(
        harness,
        _record_dispatch_delivery_command(number=101),
        event_type="DispatchDelivered",
        resulting_stream_version=2,
    )
    if state == "delivered":
        return
    assert state == "acknowledged"
    _assert_event(
        harness,
        _acknowledge_dispatch_command(number=102),
        event_type="DispatchAcknowledged",
        resulting_stream_version=3,
    )


def _seed_ready_resource_request(harness) -> None:
    _seed_ready_task(harness)
    _seed_acknowledged_dispatch(harness)
    _assert_event(
        harness,
        _request_resource_command(harness, number=103),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )


def _seed_lease(harness) -> None:
    _seed_ready_resource_request(harness)
    receipt = harness.service.submit(_claim_execution_lease_command(number=104))
    assert receipt.status == "accepted"
    event = tuple(harness.ledger.iter_events())[-1]
    assert event["event_type"] == "LeaseGranted"


def _seed_claimed_attempt(harness) -> None:
    _seed_lease(harness)
    claim_dispatch = _claim_dispatch_command(harness, number=105)
    assert harness.service.submit(claim_dispatch).status == "accepted"
    create_attempt = _create_attempt_command(number=106)
    assert harness.service.submit(create_attempt).status == "accepted"
    assert harness.service.submit(_claim_attempt_command(number=107)).status == "accepted"


def _seed_running_attempt(harness) -> None:
    _seed_lease(harness)
    claim_dispatch = _claim_dispatch_command(harness, number=105)
    assert harness.service.submit(claim_dispatch).status == "accepted"
    assert [event["event_type"] for event in tuple(harness.ledger.iter_events())[-2:]] == [
        "DispatchClaimed",
        "TaskClaimStarted",
    ]
    create_attempt = _create_attempt_command(number=106)
    _assert_event(
        harness,
        create_attempt,
        event_type="AttemptCreated",
        resulting_stream_version=1,
        event_payload={**create_attempt["payload"], "creation_kind": "initial"},
    )
    _assert_event(
        harness,
        _claim_attempt_command(number=107),
        event_type="AttemptClaimed",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _start_attempt_command(number=108),
        event_type="AttemptStarted",
        resulting_stream_version=3,
    )


def _expiry_consumer_command(harness, *, stage: str) -> tuple[dict[str, Any], str]:
    _seed_ready_task(harness)
    _seed_acknowledged_dispatch(harness)
    _assert_event(
        harness,
        _request_resource_command(harness, number=105),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _claim_execution_lease_command(number=106),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    if stage == "claim-dispatch":
        return _claim_dispatch_command(harness, number=107), "claim_dispatch_precondition_failed"

    assert harness.service.submit(_claim_dispatch_command(harness, number=107)).status == "accepted"
    assert harness.service.submit(_create_attempt_command(number=108)).status == "accepted"
    if stage == "claim-attempt":
        return _claim_attempt_command(number=109), "claim_attempt_precondition_failed"

    assert stage == "start-attempt"
    assert harness.service.submit(_claim_attempt_command(number=109)).status == "accepted"
    return _start_attempt_command(number=110), "start_attempt_precondition_failed"


@pytest.mark.parametrize(
    ("row_id", "command_type", "event_types"),
    C1_ROWS,
    ids=[row_id for row_id, _, _ in C1_ROWS],
)
def test_c1_rows_have_exact_runtime_schema_bindings(tmp_path, row_id, command_type, event_types):
    registry = control_plane(tmp_path).schemas
    command = registry.command_binding(command_type)

    assert command is not None, row_id
    assert command.schema_id == f"ars://core/command/{command_type}"
    assert command.schema_version == "1.0.0"
    for event_type in event_types:
        event = registry.event_binding(event_type, command_type)

        assert event is not None, row_id
        assert event.schema_id == f"ars://core/event/{event_type}"
        assert event.schema_version == "1.0.0"


@pytest.mark.parametrize(
    ("row_id", "command_type", "event_types"),
    C1_ROWS,
    ids=[row_id for row_id, _, _ in C1_ROWS],
)
def test_c1_rows_preserve_the_protected_schema_bytes(tmp_path, row_id, command_type, event_types):
    registry = control_plane(tmp_path).schemas
    command_identity = registry.resolve_identity(f"ars://core/command/{command_type}", "1.0.0")

    assert command_identity.sha256 == COMMAND_SCHEMA_SHA256[command_type], row_id
    assert sha256(command_identity.raw_bytes).hexdigest() == COMMAND_SCHEMA_SHA256[command_type]
    for event_type in event_types:
        event_identity = registry.resolve_identity(f"ars://core/event/{event_type}", "1.0.0")

        assert event_identity.sha256 == EVENT_SCHEMA_SHA256[event_type], row_id
        assert sha256(event_identity.raw_bytes).hexdigest() == EVENT_SCHEMA_SHA256[event_type]


def test_c1_crosswalk_has_exact_campaign_geometry():
    expected_rows = (
        ("task.request_readiness", "RequestReadiness", ("ReadinessRequested",)),
        ("task.approve_readiness", "ApproveReadiness", ("ReadinessApproved",)),
        ("task.claim_start", "ClaimDispatch", ("DispatchClaimed", "TaskClaimStarted")),
        ("dispatch.issue", "IssueDispatch", ("DispatchIssued",)),
        ("dispatch.deliver", "RecordDispatchDelivery", ("DispatchDelivered",)),
        ("dispatch.acknowledge", "AcknowledgeDispatch", ("DispatchAcknowledged",)),
        ("dispatch.claim", "ClaimDispatch", ("DispatchClaimed", "TaskClaimStarted")),
        ("dispatch.expire_issued", "ExpireDispatch", ("DispatchExpired",)),
        ("dispatch.expire_delivered", "ExpireDispatch", ("DispatchExpired",)),
        ("dispatch.expire_acknowledged", "ExpireDispatch", ("DispatchExpired",)),
        ("dispatch.withdraw_issued", "WithdrawDispatch", ("DispatchWithdrawn",)),
        ("lease.activate", "ClaimExecutionLease", ("LeaseGranted",)),
        ("lease.renew", "RenewExecutionLease", ("LeaseRenewed",)),
        ("lease.release", "ReleaseExecutionLease", ("LeaseReleased",)),
        ("lease.expire", "ExpireLease", ("LeaseExpired",)),
        ("lease.revoke", "RevokeLease", ("LeaseRevoked",)),
        ("attempt.create", "CreateAttempt", ("AttemptCreated",)),
        ("attempt.claim", "ClaimAttempt", ("AttemptClaimed",)),
        ("attempt.start", "StartAttempt", ("AttemptStarted",)),
        ("operator.request_resource_grant", "RequestResourceGrant", ("ResourceGrantRequested",)),
        ("operator.claim_execution_lease", "ClaimExecutionLease", ("LeaseGranted",)),
        ("operator.record_heartbeat", "RecordHeartbeat", ("HeartbeatRecorded",)),
        ("operator.release_resources", "ReleaseResources", ("ResourcesReleased",)),
    )
    commands = {command_type for _, command_type, _ in C1_ROWS}
    events = {event_type for _, _, event_types in C1_ROWS for event_type in event_types}

    assert C1_ROWS == expected_rows
    assert len(C1_ROWS) == 23
    assert len(commands) == 19
    assert len(events) == 20
    assert set(COMMAND_SCHEMA_SHA256) == commands
    assert set(EVENT_SCHEMA_SHA256) == events


def test_readiness_public_seam_transitions_draft_pending_ready(tmp_path):
    harness = control_plane(tmp_path)
    _create_task(harness)

    request = _request_readiness_command(number=2)
    _assert_event(
        harness,
        request,
        event_type="ReadinessRequested",
        resulting_stream_version=2,
    )
    pending = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert pending["status"] == "readiness_pending"
    assert pending["current_revision"] == 1

    approve = _approve_readiness_command(number=3)
    _assert_event(
        harness,
        approve,
        event_type="ReadinessApproved",
        resulting_stream_version=3,
    )
    ready = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert ready["status"] == "ready"
    assert ready["current_revision"] == 1


@pytest.mark.parametrize(
    ("prior_state", "expected_stream_version", "deadline_field"),
    (
        ("issued", 1, "delivery_deadline"),
        ("delivered", 2, "claim_deadline"),
        ("acknowledged", 3, "claim_deadline"),
    ),
)
def test_expire_dispatch_uses_the_exact_deadline_for_each_preclaim_state(
    tmp_path,
    prior_state,
    expected_stream_version,
    deadline_field,
):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    definition = _dispatch_definition()
    definition["delivery_deadline"] = "2026-08-01T12:45:00Z"
    definition["claim_deadline"] = INITIAL_EXPIRY
    _seed_preclaim_dispatch(harness, state=prior_state, definition=definition)
    clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
    command = _expire_dispatch_command(
        number=103,
        expected_stream_version=expected_stream_version,
        observed_prior_state=prior_state,
        observed_deadline=definition[deadline_field],
        observed_at=INITIAL_EXPIRY,
    )

    _assert_event(
        harness,
        command,
        event_type="DispatchExpired",
        resulting_stream_version=expected_stream_version + 1,
    )

    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][DISPATCH_ID]["status"] == "expired"


def test_withdraw_dispatch_is_limited_to_issued_before_any_claim(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_preclaim_dispatch(harness, state="issued", definition=_dispatch_definition())
    command = _withdraw_dispatch_command(number=101, expected_stream_version=1)

    _assert_event(
        harness,
        command,
        event_type="DispatchWithdrawn",
        resulting_stream_version=2,
    )

    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][DISPATCH_ID]["status"] == "withdrawn"


@pytest.mark.parametrize(
    ("case", "observed_deadline", "observed_at"),
    (
        ("lexical-equal-instant", "2026-08-01T13:00:00.000Z", INITIAL_EXPIRY),
        ("before-deadline", INITIAL_EXPIRY, "2026-08-01T12:59:59Z"),
        ("future-observation", INITIAL_EXPIRY, "2026-08-01T13:00:01Z"),
    ),
)
def test_expire_dispatch_rejects_nonexact_or_out_of_window_deadline_observations(
    tmp_path,
    case,
    observed_deadline,
    observed_at,
):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    _seed_preclaim_dispatch(harness, state="issued", definition=_dispatch_definition())
    clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
    command = _expire_dispatch_command(
        number=101,
        expected_stream_version=1,
        observed_prior_state="issued",
        observed_deadline=observed_deadline,
        observed_at=observed_at,
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected", case
    assert rejected.reason_code == "dispatch_expiry_observation_invalid", case
    assert _rejection_snapshot(harness) == before, case


def test_expire_dispatch_rejects_a_schema_valid_wrong_state_discriminant_without_mutation(tmp_path):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    definition = _dispatch_definition()
    definition["delivery_deadline"] = "2026-08-01T12:45:00Z"
    definition["claim_deadline"] = INITIAL_EXPIRY
    _seed_preclaim_dispatch(harness, state="issued", definition=definition)
    clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
    command = _expire_dispatch_command(
        number=101,
        expected_stream_version=1,
        observed_prior_state="delivered",
        observed_deadline=definition["claim_deadline"],
        observed_at=INITIAL_EXPIRY,
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "invalid_dispatch_transition"
    assert _rejection_snapshot(harness) == before


def test_expire_dispatch_rejects_claimed_dispatch_without_mutation(tmp_path):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    _seed_lease(harness)
    assert harness.service.submit(_claim_dispatch_command(harness, number=105)).status == "accepted"
    clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
    command = _expire_dispatch_command(
        number=106,
        expected_stream_version=4,
        observed_prior_state="acknowledged",
        observed_deadline=INITIAL_EXPIRY,
        observed_at=INITIAL_EXPIRY,
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "invalid_dispatch_transition"
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize("state", ("delivered", "acknowledged", "expired", "claimed"))
def test_withdraw_dispatch_rejects_nonissued_or_claimed_paths_without_mutation(tmp_path, state):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    if state == "claimed":
        _seed_lease(harness)
        assert harness.service.submit(_claim_dispatch_command(harness, number=105)).status == "accepted"
        command = _withdraw_dispatch_command(
            number=106,
            expected_stream_version=4,
            observed_prior_state="claimed",
        )
    else:
        _seed_preclaim_dispatch(
            harness, state=state if state != "expired" else "issued", definition=_dispatch_definition()
        )
        if state == "expired":
            clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
            assert (
                harness.service.submit(
                    _expire_dispatch_command(
                        number=101,
                        expected_stream_version=1,
                        observed_prior_state="issued",
                        observed_deadline=INITIAL_EXPIRY,
                        observed_at=INITIAL_EXPIRY,
                    )
                ).status
                == "accepted"
            )
            expected_stream_version = 2
        else:
            expected_stream_version = {"delivered": 2, "acknowledged": 3}[state]
        command = _withdraw_dispatch_command(number=103, expected_stream_version=expected_stream_version)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected", state
    assert rejected.reason_code == "invalid_dispatch_transition", state
    assert _rejection_snapshot(harness) == before, state


def test_amendment_invalidates_old_readiness_evidence_without_escaping_pending(tmp_path):
    harness = control_plane(tmp_path)
    _create_task(harness)
    request = _request_readiness_command(number=2)
    _assert_event(
        harness,
        request,
        event_type="ReadinessRequested",
        resulting_stream_version=2,
    )

    _assert_event(
        harness,
        _task_amendment_command(number=3),
        event_type="TaskAmended",
        resulting_stream_version=3,
    )
    amended = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][TASK_ID]
    assert amended["status"] == "readiness_pending"
    assert amended["current_revision"] == 2
    assert amended["revision_history"]["1"]["status"] == "amended"

    before_stale_approval = _domain_snapshot(harness)
    stale_approval = _approve_readiness_command(number=4, task_revision=1, expected_stream_version=3)
    rejected = harness.service.submit(stale_approval)
    assert rejected.status in {"rejected", "conflict"}
    assert _domain_snapshot(harness) == before_stale_approval


def test_readiness_wrong_subject_or_stale_version_does_not_mutate_domain(tmp_path):
    harness = control_plane(tmp_path)
    _create_task(harness)
    cases = (
        ("wrong-subject", {"target_stream_id": OTHER_TASK_ID}),
        ("stale-version", {"expected_stream_version": 0}),
    )
    for label, mutation in cases:
        command = _request_readiness_command(number=10 if label == "wrong-subject" else 11)
        command.update(mutation)
        before = _domain_snapshot(harness)
        rejected = harness.service.submit(command)
        assert rejected.status in {"rejected", "conflict"}, label
        assert _domain_snapshot(harness) == before, label


def test_readiness_requires_the_current_authority_subject(tmp_path):
    harness = control_plane(tmp_path, auto_authority=False)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="task",
        subject_id=TASK_ID,
    )
    _create_task(harness, authority_grant_id=grant_id)
    command = _request_readiness_command(number=12)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)
    assert rejected.status in {"rejected", "conflict"}
    assert _domain_snapshot(harness) == before


def test_resource_request_materializes_active_grant_and_admits_lease(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    _seed_acknowledged_dispatch(harness)
    request = _request_resource_command(harness, number=4)

    _assert_event(
        harness,
        request,
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )

    materialized_grant = _assert_authoritative_resource_grant(harness)
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    resource_projection = projection["streams"][RESOURCE_GRANT_ID]
    requested_resource = request["payload"]["resource_request"]

    assert set(resource_projection) == {
        "resource_id",
        "status",
        "request",
        "request_sha256",
        "authority_preimage_ref",
        "grant_ref",
        "version",
    }
    assert resource_projection["resource_id"] == RESOURCE_GRANT_ID
    assert resource_projection["status"] == "active"
    assert resource_projection["request"] == requested_resource
    assert resource_projection["request"]["requested_host_pool"] == [C1_TRUSTED_RUNTIME_AUTHORITY.host_identity]
    assert resource_projection["grant_ref"] == {
        "kind": "resource_grant",
        "id": RESOURCE_GRANT_ID,
        "revision": 1,
        "schema_version": "1.1.0",
    }
    assert resource_projection["request_sha256"] == materialized_grant["resource_request_sha256"]
    assert resource_projection["authority_preimage_ref"] == materialized_grant["authority_preimage_ref"]
    assert resource_projection["authority_preimage_ref"].startswith(
        "ars://operations/resource-grant-authority-preimage/sha256/"
    )
    assert {
        "host_identity",
        "boot_identity",
        "control_store_identity",
        "store_manifest_sha256",
        "granted_claims",
        "resource_grant_record",
        "record_bytes",
    }.isdisjoint(resource_projection)
    assert {
        "host_identity",
        "boot_identity",
        "control_store_identity",
        "store_manifest_sha256",
        "granted_claims",
        "resource_grant_record",
        "record_bytes",
    }.isdisjoint(resource_projection["request"])
    assert "grant" not in resource_projection
    _assert_event(
        harness,
        _claim_execution_lease_command(number=5),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )


def test_resource_grant_preexisting_conflict_blocks_request_without_event(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    request = _request_resource_command(harness, number=4)
    harness.objects.write("resource_grant", RESOURCE_GRANT_ID, 1, {"foreign": "preexisting"})
    before = _domain_snapshot(harness)

    with pytest.raises(ConflictError, match="resource grant revision conflicts"):
        harness.service.submit(request)

    assert _domain_snapshot(harness) == before


def test_resource_request_requires_the_exact_captured_control_store_position(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    captured = harness.ledger.snapshot().global_position
    stale = _request_resource_command(harness, number=4)
    assert stale["payload"]["resource_request"]["expected_control_store_position"] == captured
    _assert_event(
        harness,
        _issue_dispatch_command(number=5),
        event_type="DispatchIssued",
        resulting_stream_version=1,
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(stale)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_request_stale_position"
    assert _rejection_snapshot(harness) == before

    exact = _request_resource_command(harness, number=6)
    exact_position = exact["payload"]["resource_request"]["expected_control_store_position"]
    event = _assert_event(
        harness,
        exact,
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    assert event["global_position"] == exact_position + 1


def test_claim_execution_lease_rejects_missing_materialization_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    _resource_grant_path(harness).unlink()
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(_claim_execution_lease_command(number=5))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_unmaterialized"
    assert _domain_snapshot(harness) == before


def test_request_resource_grant_fails_closed_without_runtime_authority_provider_before_mutation(tmp_path):
    harness = control_plane(tmp_path, clock=lambda: C1_NOW)
    _seed_ready_task(harness)
    request = _c1_command(
        _command_id(4),
        "RequestResourceGrant",
        RESOURCE_GRANT_ID,
        0,
        _resource_request_payload(
            expected_control_store_position=harness.ledger.snapshot().global_position,
            trusted_runtime_authority=C1_TRUSTED_RUNTIME_AUTHORITY,
        ),
    )
    before = _rejection_snapshot(harness)

    with pytest.raises(IntegrityError, match="trusted runtime authority provider is unavailable"):
        harness.service.submit(request)

    assert _rejection_snapshot(harness) == before


def test_claim_execution_lease_rejects_content_hash_invalid_materialization_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    invalid = deepcopy(harness.objects.read("resource_grant", RESOURCE_GRANT_ID, 1))
    invalid["content_hash"] = "0" * 64
    _replace_resource_grant_record(harness, invalid)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(_claim_execution_lease_command(number=5))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_invalid"
    assert _domain_snapshot(harness) == before


def test_claim_execution_lease_rejects_mismatched_materialization_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    mismatched = deepcopy(harness.objects.read("resource_grant", RESOURCE_GRANT_ID, 1))
    mismatched["expires_at"] = "2026-08-01T12:45:00Z"
    mismatched["content_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in mismatched.items() if key != "content_hash"})
    )
    _replace_resource_grant_record(harness, mismatched)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(_claim_execution_lease_command(number=5))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_mismatch"
    assert _domain_snapshot(harness) == before


@pytest.mark.parametrize(
    "binding",
    ("host_identity", "boot_identity", "control_store_identity", "store_manifest_sha256"),
)
def test_claim_execution_lease_rejects_current_authority_drift_without_domain_mutation(tmp_path, binding):
    harness, authority = _mutable_c1_authority_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    authority["current"] = _drifted_runtime_authority(binding)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(_claim_execution_lease_command(number=5))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_invalid"
    assert _domain_snapshot(harness) == before


def test_claim_execution_lease_rejects_expired_materialization_without_domain_mutation(tmp_path):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    clock["now"] = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    _seed_ready_task(harness)
    _seed_acknowledged_dispatch(harness)
    request = _request_resource_command(harness, number=4)
    request["payload"]["resource_request"]["deadline"] = "2026-08-01T12:15:00Z"
    _rebind_resource_request_authority_ref(harness, request["payload"])
    _assert_event(
        harness,
        request,
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    clock["now"] = C1_NOW
    lease = _claim_execution_lease_command(number=5)
    lease["payload"]["expires_at"] = "2026-08-01T12:15:00Z"
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(lease)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_expired"
    assert _domain_snapshot(harness) == before


def test_second_authorized_same_lease_claim_rejects_before_append_and_preserves_replay(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    _assert_event(
        harness,
        _claim_execution_lease_command(number=5),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    second = _claim_execution_lease_command(number=6, expected_stream_version=1)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(second)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lease_already_granted"
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize(
    ("case", "mutation"),
    (
        ("holder-profile", {"holder_profile": "unbound-profile"}),
        (
            "added-capability",
            {"capability_scope": ["run:task", "write:workspace", "admin:anything"]},
        ),
        ("removed-capability", {"capability_scope": ["run:task"]}),
        (
            "substituted-capability",
            {"capability_scope": ["run:task", "admin:anything"]},
        ),
    ),
)
def test_claim_execution_lease_requires_exact_profile_and_capability_bindings(tmp_path, case, mutation):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    substituted = _claim_execution_lease_command(number=5)
    substituted["payload"].update(mutation)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(substituted)

    assert rejected.status == "rejected", case
    assert rejected.reason_code == "resource_grant_binding_mismatch", case
    assert _rejection_snapshot(harness) == before, case
    assert harness.service.submit(_claim_execution_lease_command(number=6)).status == "accepted", case


def test_claim_execution_lease_rejects_missing_referenced_dispatch_without_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    request = _request_resource_command(harness, number=4, dispatch_id=OTHER_DISPATCH_ID)
    _assert_event(
        harness,
        request,
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    lease = _claim_execution_lease_command(number=5, dispatch_id=OTHER_DISPATCH_ID)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(lease)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_binding_mismatch"
    assert _rejection_snapshot(harness) == before


def test_claim_execution_lease_rejects_mismatched_referenced_dispatch_without_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    definition = _dispatch_definition()
    definition["target_profile"] = "unbound-profile"
    _assert_event(
        harness,
        _issue_dispatch_command(number=4, definition=definition),
        event_type="DispatchIssued",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _record_dispatch_delivery_command(number=5),
        event_type="DispatchDelivered",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _acknowledge_dispatch_command(number=6),
        event_type="DispatchAcknowledged",
        resulting_stream_version=3,
    )
    _assert_event(
        harness,
        _request_resource_command(harness, number=7),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(_claim_execution_lease_command(number=8))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_binding_mismatch"
    assert _rejection_snapshot(harness) == before


def test_live_grant_rejects_an_already_expired_proposed_lease_without_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    lease = _claim_execution_lease_command(number=5)
    lease["payload"]["expires_at"] = "2026-08-01T12:15:00Z"
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(lease)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lease_expired"
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize("stage", ("claim-dispatch", "claim-attempt", "start-attempt"))
def test_elapsed_lease_expiry_rejects_each_c1_consumer_without_mutation(tmp_path, stage):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    command, expected_reason = _expiry_consumer_command(harness, stage=stage)
    clock["now"] = datetime(2026, 8, 1, 13, 1, tzinfo=UTC)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected", stage
    assert rejected.reason_code == expected_reason, stage
    assert _rejection_snapshot(harness) == before, stage


def test_claim_dispatch_fails_closed_for_a_non_aware_clock_without_mutation(tmp_path, monkeypatch):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    command, _ = _expiry_consumer_command(harness, stage="claim-dispatch")
    clock["now"] = datetime(2026, 8, 1, 12, 45)
    before = _rejection_snapshot(harness)

    def resolver_must_not_run(**_kwargs):
        raise AssertionError("C1 authority resolution must not run with an invalid trusted clock")

    monkeypatch.setattr(harness.authority_resolver, "resolve_lifecycle_command", resolver_must_not_run)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lifecycle_authority_unauthorized"
    assert _rejection_snapshot(harness) == before


def test_c1_authority_resolver_value_error_is_not_downgraded_to_a_rejection(tmp_path, monkeypatch):
    harness, _ = _mutable_c1_control_plane(tmp_path)
    command, _ = _expiry_consumer_command(harness, stage="claim-dispatch")
    before = _rejection_snapshot(harness)

    def malformed_authority_evidence(**_kwargs):
        raise ValueError("malformed authority evidence")

    monkeypatch.setattr(harness.authority_resolver, "resolve_lifecycle_command", malformed_authority_evidence)

    with pytest.raises(ValueError, match="malformed authority evidence"):
        harness.service.submit(command)

    assert _rejection_snapshot(harness) == before


def test_request_resource_grant_retry_repairs_event_only_after_object_interruption(tmp_path, monkeypatch):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    request = _request_resource_command(harness, number=4)
    original_write = harness.objects.write
    before_interruption = _grant_admission_snapshot(harness)

    def interrupted_write(kind, object_id, revision, value):
        if (kind, object_id, revision) == ("resource_grant", RESOURCE_GRANT_ID, 1):
            raise OSError("interrupted after append")
        return original_write(kind, object_id, revision, value)

    monkeypatch.setattr(harness.objects, "write", interrupted_write)
    with pytest.raises(OSError, match="interrupted after append"):
        harness.service.submit(request)
    committed = tuple(harness.ledger.iter_events())
    assert committed[-1]["event_type"] == "ResourceGrantRequested"
    assert len([event for event in committed if event["event_type"] == "ResourceGrantRequested"]) == 1
    assert not harness.objects.revision_exists("resource_grant", RESOURCE_GRANT_ID, 1)
    assert harness.receipts.load(request["command_id"]) is None
    assert _grant_admission_snapshot(harness)["receipts"] == before_interruption["receipts"]

    monkeypatch.setattr(harness.objects, "write", original_write)
    receipt = harness.service.submit(request)

    assert receipt.status == "accepted"
    assert tuple(harness.ledger.iter_events()) == committed
    _assert_authoritative_resource_grant(harness)
    assert harness.receipts.load(request["command_id"]) == receipt


@pytest.mark.parametrize(
    "binding",
    ("host_identity", "boot_identity", "control_store_identity", "store_manifest_sha256"),
)
def test_request_resource_grant_event_only_retry_rejects_current_authority_drift_then_repairs(
    tmp_path, monkeypatch, binding
):
    harness, authority = _mutable_c1_authority_control_plane(tmp_path)
    _seed_ready_task(harness)
    request = _request_resource_command(harness, number=4)
    original_write = harness.objects.write

    def interrupted_write(kind, object_id, revision, value):
        if (kind, object_id, revision) == ("resource_grant", RESOURCE_GRANT_ID, 1):
            raise OSError("interrupted after append")
        return original_write(kind, object_id, revision, value)

    monkeypatch.setattr(harness.objects, "write", interrupted_write)
    with pytest.raises(OSError, match="interrupted after append"):
        harness.service.submit(request)
    committed = tuple(harness.ledger.iter_events())
    assert len([event for event in committed if event["event_type"] == "ResourceGrantRequested"]) == 1
    assert not harness.objects.revision_exists("resource_grant", RESOURCE_GRANT_ID, 1)
    assert harness.receipts.load(request["command_id"]) is None

    monkeypatch.setattr(harness.objects, "write", original_write)
    authority["current"] = _drifted_runtime_authority(binding)
    before_drift_retry = _grant_admission_snapshot(harness)
    with pytest.raises(IntegrityError, match="resource grant materialization is invalid"):
        harness.service.submit(request)
    assert _grant_admission_snapshot(harness) == before_drift_retry

    authority["current"] = C1_TRUSTED_RUNTIME_AUTHORITY
    receipt = harness.service.submit(request)

    assert receipt.status == "accepted"
    assert tuple(harness.ledger.iter_events()) == committed
    _assert_authoritative_resource_grant(harness)


def test_public_admission_chain_reaches_claimed_task_and_running_attempt(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    _assert_event(
        harness,
        _issue_dispatch_command(number=10),
        event_type="DispatchIssued",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _record_dispatch_delivery_command(number=11),
        event_type="DispatchDelivered",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _acknowledge_dispatch_command(number=12),
        event_type="DispatchAcknowledged",
        resulting_stream_version=3,
    )
    _assert_event(
        harness,
        _request_resource_command(harness, number=13),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _claim_execution_lease_command(number=14),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    prefix_batches = tuple(harness.ledger.iter_batches())
    prefix_events = tuple(event for batch in prefix_batches for event in batch)
    prefix_projection = replay(prefix_events, schema_registry=harness.schemas)
    claim_dispatch = _claim_dispatch_command(harness, number=15)
    claim_receipt = harness.service.submit(claim_dispatch)
    assert claim_receipt.status == "accepted"
    assert [event["event_type"] for event in tuple(harness.ledger.iter_events())[-2:]] == [
        "DispatchClaimed",
        "TaskClaimStarted",
    ]
    create_attempt = _create_attempt_command(number=16)
    create_receipt = harness.service.submit(create_attempt)
    assert create_receipt.status == "accepted"
    created_event = tuple(harness.ledger.iter_events())[-1]
    assert created_event["event_type"] == "AttemptCreated"
    assert created_event["stream_id"] == ATTEMPT_ID
    assert created_event["stream_version"] == 1
    assert created_event["payload"] == {**create_attempt["payload"], "creation_kind": "initial"}
    _assert_event(
        harness,
        _claim_attempt_command(number=17),
        event_type="AttemptClaimed",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _start_attempt_command(number=18),
        event_type="AttemptStarted",
        resulting_stream_version=3,
    )

    all_batches = tuple(harness.ledger.iter_batches())
    all_events = tuple(event for batch in all_batches for event in batch)
    projection = replay(all_events, schema_registry=harness.schemas)
    tail_batches = all_batches[len(prefix_batches) :]
    assert [event["event_type"] for event in tail_batches[0]] == [
        "DispatchClaimed",
        "TaskClaimStarted",
    ]
    incremental_projection = _fold_trusted_c1_tail_batches(prefix_projection, tail_batches)
    c1_stream_ids = (TASK_ID, DISPATCH_ID, RESOURCE_GRANT_ID, LEASE_ID, ATTEMPT_ID)

    def c1_projection_view(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "project_id": state["project_id"],
            "last_position": state["last_position"],
            "last_hash": state["last_hash"],
            "streams": {stream_id: state["streams"][stream_id] for stream_id in sorted(c1_stream_ids)},
        }

    assert canonical_bytes(c1_projection_view(incremental_projection)) == canonical_bytes(
        c1_projection_view(projection)
    )
    assert any(
        event["event_type"] == "TaskClaimStarted" and event["stream_id"] == TASK_ID
        for event in harness.ledger.iter_events()
    )
    assert projection["streams"][TASK_ID]["status"] == "in_progress"
    assert projection["streams"][ATTEMPT_ID]["status"] == "running"


def test_create_attempt_rejects_a_foreign_task_with_the_same_revision_before_append(tmp_path):
    harness = _c1_control_plane(tmp_path)
    foreign_task = create_task_command(
        _command_id(900),
        "wp6-1-c1:foreign-task",
        OTHER_TASK_ID,
        {"title": "Foreign same-revision Task"},
    )
    assert harness.service.submit(foreign_task).status == "accepted"
    _seed_lease(harness)
    assert harness.service.submit(_claim_dispatch_command(harness, number=105)).status == "accepted"
    command = _create_attempt_command(number=106)
    command["payload"]["task_id"] = OTHER_TASK_ID
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "attempt_creation_precondition_failed"
    assert _rejection_snapshot(harness) == before


def test_create_attempt_requires_the_current_active_lease_before_append(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    assert harness.service.submit(_claim_dispatch_command(harness, number=105)).status == "accepted"
    assert harness.service.submit(_release_lease_command(number=106, expected_stream_version=1)).status == "accepted"
    command = _create_attempt_command(number=107)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "attempt_creation_precondition_failed"
    assert _rejection_snapshot(harness) == before


def test_claim_attempt_rejects_a_substituted_lease_tuple_before_append(tmp_path, monkeypatch):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    assert harness.service.submit(_claim_dispatch_command(harness, number=105)).status == "accepted"
    assert harness.service.submit(_create_attempt_command(number=106)).status == "accepted"
    command = _claim_attempt_command(number=107)
    original_streams = harness.service._c1_streams

    def substituted_streams(snapshot):
        streams = deepcopy(original_streams(snapshot))
        streams[LEASE_ID]["task_id"] = OTHER_TASK_ID
        return streams

    monkeypatch.setattr(harness.service, "_c1_streams", substituted_streams)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "claim_attempt_precondition_failed"
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize("substitution", ("lease_tuple", "session"))
def test_start_attempt_rejects_substituted_lease_tuple_or_holder_session_before_append(
    tmp_path,
    monkeypatch,
    substitution,
):
    harness = _c1_control_plane(tmp_path)
    _seed_claimed_attempt(harness)
    command = _start_attempt_command(number=108)
    if substitution == "lease_tuple":
        original_streams = harness.service._c1_streams

        def substituted_streams(snapshot):
            streams = deepcopy(original_streams(snapshot))
            streams[LEASE_ID]["task_id"] = OTHER_TASK_ID
            return streams

        monkeypatch.setattr(harness.service, "_c1_streams", substituted_streams)
    else:
        command["payload"]["session_identity"] = "session:foreign"
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "start_attempt_precondition_failed"
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize("missing", ("none", "index", "receipt", "both"))
def test_claim_dispatch_same_command_retry_repairs_each_receipt_residue_without_a_new_event(tmp_path, missing):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    command = _claim_dispatch_command(harness, number=105)
    accepted = harness.service.submit(command)
    index_path = _claim_dispatch_scoped_index_path(harness)
    receipt_path = harness.receipts.receipts_root / f"{command['command_id']}.json"
    expected_index = index_path.read_bytes()
    expected_receipt = receipt_path.read_bytes()
    if missing in {"index", "both"}:
        index_path.unlink()
    if missing in {"receipt", "both"}:
        receipt_path.unlink()
    before = _domain_snapshot(harness)

    retried = harness.service.submit(deepcopy(command))

    assert retried == accepted
    assert _domain_snapshot(harness) == before
    assert index_path.read_bytes() == expected_index
    assert receipt_path.read_bytes() == expected_receipt


def test_claim_dispatch_changed_command_id_cannot_repair_missing_receipt_or_index(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    command = _claim_dispatch_command(harness, number=105)
    assert harness.service.submit(command).status == "accepted"
    index_path = _claim_dispatch_scoped_index_path(harness)
    receipt_path = harness.receipts.receipts_root / f"{command['command_id']}.json"
    index_path.unlink()
    receipt_path.unlink()
    changed = deepcopy(command)
    changed["command_id"] = _command_id(106)
    before_domain = _domain_snapshot(harness)
    before_receipts = _json_files(harness.receipts.receipts_root)
    before_index = _json_files(harness.receipts.index_root)

    with pytest.raises(ConflictError, match="idempotency key conflicts with committed command"):
        harness.service.submit(changed)

    assert _domain_snapshot(harness) == before_domain
    assert _json_files(harness.receipts.receipts_root) == before_receipts
    assert _json_files(harness.receipts.index_root) == before_index
    assert not index_path.exists()
    assert not receipt_path.exists()


def test_same_snapshot_claim_dispatch_conflicts_once_without_creating_an_attempt(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    _assert_event(
        harness,
        _issue_dispatch_command(number=10),
        event_type="DispatchIssued",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _record_dispatch_delivery_command(number=11),
        event_type="DispatchDelivered",
        resulting_stream_version=2,
    )
    _assert_event(
        harness,
        _acknowledge_dispatch_command(number=12),
        event_type="DispatchAcknowledged",
        resulting_stream_version=3,
    )
    _assert_event(
        harness,
        _request_resource_command(harness, number=13),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _claim_execution_lease_command(number=14),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    first = _claim_dispatch_command(harness, number=15)
    second = _claim_dispatch_command(harness, number=16)

    assert first["command_id"] != second["command_id"]
    assert first["actor_id"] == second["actor_id"] == ACTORS["actor-a"]
    assert first["payload"] == second["payload"]
    assert harness.service.submit(first).status == "accepted"
    assert harness.service.submit(second).status == "conflict"

    claim_batches = [
        [event["event_type"] for event in batch]
        for batch in harness.ledger.iter_batches()
        if any(event["event_type"] in {"DispatchClaimed", "TaskClaimStarted"} for event in batch)
    ]
    assert claim_batches == [["DispatchClaimed", "TaskClaimStarted"]]
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][DISPATCH_ID]["status"] == "claimed"
    assert projection["streams"][TASK_ID]["status"] == "in_progress"
    assert ATTEMPT_ID not in projection["streams"]
    assert not any(event["event_type"].startswith("Attempt") for event in harness.ledger.iter_events())


@pytest.mark.parametrize(
    ("row_id", "command_type", "event_type", "command_factory", "expected_status"),
    (
        ("lease.expire", "ExpireLease", "LeaseExpired", _expire_lease_command, "expired"),
        ("lease.revoke", "RevokeLease", "LeaseRevoked", _revoke_lease_command, "revoked"),
    ),
    ids=["lease.expire", "lease.revoke"],
)
def test_lease_terminal_rows_are_exact_and_close_the_live_lease(
    tmp_path,
    row_id,
    command_type,
    event_type,
    command_factory,
    expected_status,
):
    if command_type == "ExpireLease":
        harness, clock = _mutable_c1_control_plane(tmp_path)
    else:
        harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    if command_type == "ExpireLease":
        clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
        observed_at = INITIAL_EXPIRY
    else:
        observed_at = OBSERVED_AT

    terminal = command_factory(number=8, expected_stream_version=1, observed_at=observed_at)
    _assert_event(
        harness,
        terminal,
        event_type=event_type,
        resulting_stream_version=2,
        event_payload=(
            {"lease_id": terminal["payload"]["lease_id"], "observed_at": terminal["payload"]["observed_at"]}
            if command_type == "ExpireLease"
            else None
        ),
    )
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][LEASE_ID]["status"] == expected_status, (row_id, command_type)

    before_illegal_heartbeat = _domain_snapshot(harness)
    illegal_heartbeat = _heartbeat_command(number=9, expected_stream_version=2)
    rejected = harness.service.submit(illegal_heartbeat)
    assert rejected.status in {"rejected", "conflict"}
    assert _domain_snapshot(harness) == before_illegal_heartbeat


def test_authorized_operator_can_release_the_exact_holder_lease(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    operator_grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="lease",
        subject_id=LEASE_ID,
        actor_id=ACTORS["actor-b"],
        command_types=("ReleaseExecutionLease",),
        grant_id=OPERATOR_RELEASE_GRANT_ID,
    )
    command = _release_lease_command(number=9, expected_stream_version=1)
    command["actor_id"] = ACTORS["actor-b"]
    command["authority_grant_id"] = operator_grant_id

    receipt = harness.service.submit(command)

    assert receipt.status == "accepted"
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][LEASE_ID]["status"] == "released"
    assert projection["streams"][LEASE_ID]["release"]["holder_actor_id"] == ACTORS["actor-a"]


def test_operator_release_rejects_unauthorised_actor_or_substituted_holder_without_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    unauthorised = _release_lease_command(number=9, expected_stream_version=1)
    unauthorised["actor_id"] = ACTORS["actor-b"]
    before_unauthorised = _rejection_snapshot(harness)

    rejected = harness.service.submit(unauthorised)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lifecycle_authority_unauthorized"
    assert _rejection_snapshot(harness) == before_unauthorised
    operator_grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="lease",
        subject_id=LEASE_ID,
        actor_id=ACTORS["actor-b"],
        command_types=("ReleaseExecutionLease",),
        grant_id=OPERATOR_RELEASE_GRANT_ID,
    )
    substituted_holder = _release_lease_command(
        number=10,
        expected_stream_version=1,
        holder_actor_id=ACTORS["actor-b"],
    )
    substituted_holder["actor_id"] = ACTORS["actor-b"]
    substituted_holder["authority_grant_id"] = operator_grant_id
    before_substitution = _rejection_snapshot(harness)

    rejected = harness.service.submit(substituted_holder)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lease_holder_mismatch"
    assert _rejection_snapshot(harness) == before_substitution


def test_expire_lease_requires_an_expiry_observation_not_before_the_lease_deadline(tmp_path):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    _seed_lease(harness)
    clock["now"] = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)
    command = _expire_lease_command(
        number=9,
        expected_stream_version=1,
        observed_at="2026-08-01T12:59:59Z",
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lease_expiry_observation_invalid"
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize(
    ("command_factory", "clock_now", "observed_at", "reason_code"),
    (
        (
            _release_lease_command,
            C1_NOW,
            "2026-08-01T12:31:00Z",
            "lease_release_observation_invalid",
        ),
        (
            _revoke_lease_command,
            C1_NOW,
            "2026-08-01T12:31:00Z",
            "lease_revocation_observation_invalid",
        ),
        (
            _expire_lease_command,
            datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
            "2026-08-01T13:01:00Z",
            "lease_expiry_observation_invalid",
        ),
    ),
    ids=["release-future", "revoke-future", "expire-future"],
)
def test_lease_terminal_commands_reject_a_future_observation_without_mutation(
    tmp_path,
    command_factory,
    clock_now,
    observed_at,
    reason_code,
):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    _seed_lease(harness)
    clock["now"] = clock_now
    command = command_factory(number=9, expected_stream_version=1, observed_at=observed_at)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert rejected.reason_code == reason_code
    assert _rejection_snapshot(harness) == before


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("holder_actor_id", ACTORS["actor-b"]),
        ("prior_expiry", "2026-08-01T12:59:00Z"),
    ),
    ids=["wrong-holder", "substituted-expiry"],
)
def test_live_lease_holder_and_expiry_cannot_be_substituted(tmp_path, field, value):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    command = _renew_lease_command(number=10, expected_stream_version=1)
    command["payload"][field] = value
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)
    assert rejected.status in {"rejected", "conflict"}
    assert _domain_snapshot(harness) == before


def test_renewal_rejects_lexically_later_spelling_of_the_same_instant_without_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    lease = _claim_execution_lease_command(number=5)
    lease["payload"]["expires_at"] = "2026-08-01T13:00:00.000Z"
    _assert_event(
        harness,
        lease,
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    renewal = _renew_lease_command(number=10, expected_stream_version=1)
    renewal["payload"]["prior_expiry"] = "2026-08-01T13:00:00.000Z"
    renewal["payload"]["new_expiry"] = INITIAL_EXPIRY
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(renewal)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "lease_renewal_mismatch"
    assert _domain_snapshot(harness) == before


def test_renewal_cannot_exceed_its_immutable_resource_grant_ceiling(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _assert_event(
        harness,
        _heartbeat_command(number=109),
        event_type="HeartbeatRecorded",
        resulting_stream_version=2,
    )
    renewal = _renew_lease_command(
        number=110,
        expected_stream_version=2,
        new_expiry="2026-08-01T14:00:00Z",
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(renewal)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_expiry_exceeded"
    assert _rejection_snapshot(harness) == before


def test_renewal_accepts_later_fractional_instant_below_deliberately_later_grant_ceiling(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _assert_event(
        harness,
        _heartbeat_command(number=109),
        event_type="HeartbeatRecorded",
        resulting_stream_version=2,
    )
    renewal = _renew_lease_command(number=110, expected_stream_version=2)
    renewal["payload"]["new_expiry"] = "2026-08-01T13:00:00.500Z"

    receipt = harness.service.submit(renewal)

    assert receipt.status == "accepted"
    assert (
        replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][LEASE_ID]["expires_at"]
        == "2026-08-01T13:00:00.500Z"
    )


def test_resource_release_requires_its_owning_lease_but_can_follow_lease_release(tmp_path):
    harness, authority = _mutable_c1_authority_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    _assert_event(
        harness,
        _claim_execution_lease_command(number=5),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _request_resource_command(
            harness,
            number=6,
            resource_grant_id=OTHER_RESOURCE_GRANT_ID,
            resource_request_id=OTHER_RESOURCE_REQUEST_ID,
        ),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _claim_execution_lease_command(
            number=7,
            lease_id=OTHER_LEASE_ID,
            resource_grant_id=OTHER_RESOURCE_GRANT_ID,
        ),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    active = _release_resources_command(number=8, lease_id=LEASE_ID)
    before_active = _rejection_snapshot(harness)

    rejected = harness.service.submit(active)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_release_lease_not_terminal"
    assert _rejection_snapshot(harness) == before_active
    foreign = _release_resources_command(number=9, lease_id=OTHER_LEASE_ID)
    before_foreign = _rejection_snapshot(harness)

    rejected = harness.service.submit(foreign)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_lease_mismatch"
    assert _rejection_snapshot(harness) == before_foreign
    _assert_event(
        harness,
        _release_lease_command(number=10, expected_stream_version=1),
        event_type="LeaseReleased",
        resulting_stream_version=2,
    )
    empty_consumption = _release_resources_command(
        number=11,
        consumption_reconciliation=[],
    )
    before_empty_consumption = _rejection_snapshot(harness)

    rejected = harness.service.submit(empty_consumption)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_consumption_reconciliation_invalid"
    assert _rejection_snapshot(harness) == before_empty_consumption
    empty_cleanup = _release_resources_command(number=12, cleanup_evidence_refs=[])
    before_empty_cleanup = _rejection_snapshot(harness)

    rejected = harness.service.submit(empty_cleanup)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_cleanup_evidence_missing"
    assert _rejection_snapshot(harness) == before_empty_cleanup
    authority["current"] = _drifted_runtime_authority("host_identity")
    receipt = harness.service.submit(_release_resources_command(number=13))
    assert receipt.status == "accepted"
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][LEASE_ID]["status"] == "released"
    assert projection["streams"][RESOURCE_GRANT_ID]["status"] == "released"


def test_first_heartbeat_is_accepted_only_after_the_public_chain_reaches_running_attempt(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)

    event = _assert_event(
        harness,
        _heartbeat_command(number=109),
        event_type="HeartbeatRecorded",
        resulting_stream_version=2,
    )

    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][LEASE_ID]["last_heartbeat"] == event["payload"]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("host_identity", "host:sha256:" + "e" * 64),
        ("boot_identity", "boot:sha256:" + "f" * 64),
        ("process_identity_id", OTHER_PROCESS_ID),
    ),
    ids=["wrong-host", "wrong-boot", "wrong-process"],
)
def test_heartbeat_rejects_valid_shaped_wrong_host_boot_or_process_without_mutation(tmp_path, field, value):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    command = _heartbeat_command(number=109)
    command["payload"][field] = value
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected"
    assert _domain_snapshot(harness) == before


def test_heartbeat_rejects_missing_and_non_running_attempt_without_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    before_missing = _domain_snapshot(harness)

    missing = harness.service.submit(_heartbeat_command(number=109))

    assert missing.status == "rejected"
    assert _domain_snapshot(harness) == before_missing
    claim_dispatch = _claim_dispatch_command(harness, number=105)
    assert harness.service.submit(claim_dispatch).status == "accepted"
    create_attempt = _create_attempt_command(number=106)
    _assert_event(
        harness,
        create_attempt,
        event_type="AttemptCreated",
        resulting_stream_version=1,
        event_payload={**create_attempt["payload"], "creation_kind": "initial"},
    )
    before_non_running = _domain_snapshot(harness)

    non_running = harness.service.submit(_heartbeat_command(number=110))

    assert non_running.status == "rejected"
    assert _domain_snapshot(harness) == before_non_running


@pytest.mark.parametrize(
    ("case", "overrides"),
    (
        ("repeated-sequence", {"heartbeat_sequence": 1}),
        ("skipped-sequence", {"heartbeat_sequence": 3}),
        ("duplicate-heartbeat-id", {"heartbeat_id": HEARTBEAT_ID}),
        ("non-increasing-wall-time", {"wall_time": HEARTBEAT_AT}),
        ("non-increasing-monotonic-time", {"monotonic_time": 120}),
        ("non-increasing-progress", {"work_unit_progress": 1}),
    ),
)
def test_heartbeat_rejects_non_monotonic_identity_or_progression_without_mutation(tmp_path, case, overrides):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _assert_event(
        harness,
        _heartbeat_command(number=109),
        event_type="HeartbeatRecorded",
        resulting_stream_version=2,
    )
    command = _heartbeat_command(
        number=110,
        expected_stream_version=2,
        heartbeat_id=OTHER_HEARTBEAT_ID,
        heartbeat_sequence=2,
        wall_time=NEXT_HEARTBEAT_AT,
        monotonic_time=121,
        work_unit_progress=2,
    )
    command["payload"].update(overrides)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)

    assert rejected.status == "rejected", case
    assert _domain_snapshot(harness) == before, case


@pytest.mark.parametrize(
    ("now", "expected_reason"),
    (
        (datetime(2026, 8, 1, 12, 46, tzinfo=UTC), "heartbeat_stale"),
        (datetime(2026, 8, 1, 13, 1, tzinfo=UTC), "lease_expired"),
    ),
    ids=["stale", "expired"],
)
def test_heartbeat_cannot_revive_stale_or_expired_lease_without_mutation(tmp_path, now, expected_reason):
    harness, clock = _mutable_c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    clock["now"] = now
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(_heartbeat_command(number=109))

    assert rejected.status == "rejected"
    assert rejected.reason_code == expected_reason
    assert _domain_snapshot(harness) == before


def test_renewal_accepts_the_latest_fresh_heartbeat_from_the_running_attempt(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_running_attempt(harness)
    _assert_event(
        harness,
        _heartbeat_command(number=109),
        event_type="HeartbeatRecorded",
        resulting_stream_version=2,
    )

    _assert_event(
        harness,
        _renew_lease_command(number=110, expected_stream_version=2),
        event_type="LeaseRenewed",
        resulting_stream_version=3,
    )


@pytest.mark.parametrize(
    "case",
    ("missing", "wrong", "stale", "wrong-policy", "authority-drift"),
)
def test_renewal_requires_exact_latest_fresh_heartbeat_current_policy_and_authority(tmp_path, case):
    if case == "authority-drift":
        harness, authority = _mutable_c1_authority_control_plane(tmp_path)
        clock = None
    elif case == "stale":
        harness, clock = _mutable_c1_control_plane(tmp_path)
        authority = None
    else:
        harness = _c1_control_plane(tmp_path)
        authority = None
        clock = None
    _seed_running_attempt(harness)
    expected_stream_version = 1
    if case != "missing":
        _assert_event(
            harness,
            _heartbeat_command(number=109),
            event_type="HeartbeatRecorded",
            resulting_stream_version=2,
        )
        expected_stream_version = 2
    renewal = _renew_lease_command(number=110, expected_stream_version=expected_stream_version)
    if case == "wrong":
        renewal["payload"]["heartbeat_evidence_refs"] = [OTHER_HEARTBEAT_ID]
    elif case == "stale":
        assert clock is not None
        clock["now"] = datetime(2026, 8, 1, 12, 46, tzinfo=UTC)
    elif case == "wrong-policy":
        renewal["payload"]["renewal_policy_ref"] = "policy:foreign"
    elif case == "authority-drift":
        assert authority is not None
        authority["current"] = _drifted_runtime_authority("host_identity")
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(renewal)

    assert rejected.status == "rejected", case
    assert _domain_snapshot(harness) == before, case


@pytest.mark.parametrize(
    ("row_id", "command_factory"),
    (
        ("lease.activate", _claim_execution_lease_command),
        ("lease.renew", _renew_lease_command),
        ("lease.release", _release_lease_command),
        ("lease.expire", _expire_lease_command),
        ("lease.revoke", _revoke_lease_command),
        ("operator.record_heartbeat", _heartbeat_command),
        ("operator.release_resources", _release_resources_command),
    ),
    ids=[
        "lease.activate",
        "lease.renew",
        "lease.release",
        "lease.expire",
        "lease.revoke",
        "operator.record_heartbeat",
        "operator.release_resources",
    ],
)
def test_lease_and_resource_rows_reject_illegal_empty_state_without_mutation(tmp_path, row_id, command_factory):
    harness = control_plane(tmp_path)
    command = command_factory(number=20, expected_stream_version=0)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)
    assert rejected.status in {"rejected", "conflict"}, row_id
    assert _domain_snapshot(harness) == before, row_id


def test_conflicting_readiness_retry_does_not_mutate_ledger_receipt_or_projection(tmp_path):
    harness = control_plane(tmp_path)
    _create_task(harness)
    request = _request_readiness_command(number=30)
    accepted = harness.service.submit(request)
    assert accepted.status == "accepted"
    before_retry = _domain_snapshot(harness)

    identical = harness.service.submit(deepcopy(request))
    assert identical == accepted
    assert _domain_snapshot(harness) == before_retry

    changed_command_id = deepcopy(request)
    changed_command_id["command_id"] = _command_id(31)
    with pytest.raises(ConflictError):
        harness.service.submit(changed_command_id)
    assert _domain_snapshot(harness) == before_retry
