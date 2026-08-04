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
from research_system.errors import ConflictError
from research_system.projection.replay import replay
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
CHECKPOINT_ID = "cpm_01978abc-7211-7000-8000-000000007211"
POLICY_ID = "pol_01978abc-7212-7000-8000-000000007212"

GRANTED_AT = "2026-08-01T12:00:00Z"
INITIAL_EXPIRY = "2026-08-01T13:00:00Z"
GRANT_EXPIRY = "2026-08-01T13:30:00Z"
RENEWED_EXPIRY = "2026-08-01T13:15:00Z"
OBSERVED_AT = "2026-08-01T12:20:00Z"
C1_NOW = datetime(2026, 8, 1, 12, 30, tzinfo=UTC)


C1_ROWS = (
    ("task.request_readiness", "RequestReadiness", "ReadinessRequested"),
    ("task.approve_readiness", "ApproveReadiness", "ReadinessApproved"),
    # One exact command/event pair is the catalogue representation for both
    # lease.activate and operator.claim_execution_lease.
    ("lease.activate+operator.claim_execution_lease", "ClaimExecutionLease", "LeaseGranted"),
    ("lease.renew", "RenewExecutionLease", "LeaseRenewed"),
    ("lease.release", "ReleaseExecutionLease", "LeaseReleased"),
    ("lease.expire", "ExpireLease", "LeaseExpired"),
    ("lease.revoke", "RevokeLease", "LeaseRevoked"),
    ("operator.request_resource_grant", "RequestResourceGrant", "ResourceGrantRequested"),
    ("operator.record_heartbeat", "RecordHeartbeat", "HeartbeatRecorded"),
    ("operator.release_resources", "ReleaseResources", "ResourcesReleased"),
)

COMMAND_SCHEMA_SHA256 = {
    "RequestReadiness": "caf2b31f2acc666c0395a7a671c33957dfb7efb8c4db65afc553069ab6e80c5c",
    "ApproveReadiness": "26952636785fce275b8a7109d9b90b1ba6011c5b5605132344cd948311ff78f7",
    "ClaimExecutionLease": "a05e176483dadefdf961de3db9432cb1afe110605ae84b9fef194ff9b3bac745",
    "RenewExecutionLease": "28efd26b2e843aa007c52b17ef24236e83941b9c8c5377be3be063d795ce911e",
    "ReleaseExecutionLease": "441756d56ef0349d96c22abe48573eea601fbda4a91ad9a21a44ef9f68f31ae3",
    "ExpireLease": "88412b288968b28e2b11b37350aafb9e5d4e0f88f007a9da24f5dc1472dc3afe",
    "RevokeLease": "510556548df6f43acb34158d6c3b532bca4b70c82e2faf7b8109a3e421b5aeb8",
    "RequestResourceGrant": "8a249187b7797cf30ffae5e342fe265a5b3a372269c8b20f13742b50630dfad3",
    "RecordHeartbeat": "b387fdd14389ed16ed53ba20d63732861d7b3ddd93bd69aa100d4811a7403f94",
    "ReleaseResources": "21ed97a83b5536920c4886cdba853d0e811521fc1db234fcf6b88549cc463df0",
}

EVENT_SCHEMA_SHA256 = {
    "ReadinessRequested": "bd432fbf6bbd5c97ff6147b86931adfe846ccf0a9b150263a5cdb0d7fade4d79",
    "ReadinessApproved": "d6df570f67486ab4a2ce6a3005fe72cc6caa245d0ac1eaa30f47bdc65c3e1b55",
    "LeaseGranted": "f23fe9fe580872a1017fab954e19524fc9084f5111732e06d15cbbdea2251121",
    "LeaseRenewed": "c2a5942a50027add02e7907b5f7bdc582bea1bf821ceeaf34a805c071556d73b",
    "LeaseReleased": "8985195917c0f70f91124674f44902478a97b88d80e7f82bbc3ba2f62c862b77",
    "LeaseExpired": "3aa4f643eefc3ec70af4dbb626c358b1e439b5f4ece2759e2ce036bc1acec240",
    "LeaseRevoked": "7a5612a2fd072aabc23c18e099b2a7c8d01fb9adcd20f89863aeff7633431fa0",
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
    resource_grant_id: str = RESOURCE_GRANT_ID,
    resource_request_id: str = RESOURCE_REQUEST_ID,
    dispatch_id: str = DISPATCH_ID,
) -> dict[str, Any]:
    evidence = {
        "disposition": "required",
        "policy_id": POLICY_ID,
        "rationale": "The bounded execution profile requires this evidence.",
        "applicability_evidence_refs": ["evidence:resource-profile:bounded"],
    }
    return {
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
            "operational_profile_policy_id": POLICY_ID,
            "operational_profile_revision": "1.0.0",
            "requesting_actor_id": ACTORS["actor-a"],
            "requesting_profile": "luna-max",
            "requesting_authority_grant_id": scoped_lifecycle_grant_id(resource_grant_id),
            "expected_control_store_position": expected_control_store_position,
            "requested_host_pool": ["host:c1-synthetic"],
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
            "projection_evidence_refs": ["evidence:projection:bounded"],
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


def _expected_resource_grant_record(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload["resource_request"]
    return {
        "schema_id": "ars://operations/resource-grant",
        "schema_version": "1.0.0",
        "resource_grant_id": payload["resource_id"],
        "resource_request_id": request["resource_request_id"],
        "attempt_id": request["attempt_id"],
        "profile_id": request["operational_profile_policy_id"],
        "granted_claims": deepcopy(request),
        "expires_at": request["deadline"],
    }


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
            "renewal_policy_ref": "policy:lease:v1",
            "operational_profile": "bounded",
        },
    )


def _heartbeat_command(
    *,
    number: int,
    expected_stream_version: int,
    lease_id: str = LEASE_ID,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RecordHeartbeat",
        lease_id,
        expected_stream_version,
        {
            "lease_id": lease_id,
            "heartbeat_sequence": 1,
            "process_identity_id": PROCESS_ID,
            "heartbeat_id": HEARTBEAT_ID,
            "wall_time": OBSERVED_AT,
            "monotonic_time": 120,
            "host_identity": "host:c1-synthetic",
            "boot_identity": "boot:c1-synthetic",
            "work_unit_progress": 1,
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
            "renewal_policy_ref": "policy:lease:v1",
            "heartbeat_evidence_refs": [HEARTBEAT_ID],
        },
    )


def _release_lease_command(*, number: int, expected_stream_version: int) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ReleaseExecutionLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "release_reason": "bounded C1 operation completed",
            "holder_actor_id": ACTORS["actor-a"],
            "observed_at": OBSERVED_AT,
        },
    )


def _expire_lease_command(*, number: int, expected_stream_version: int) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ExpireLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "observed_at": OBSERVED_AT,
            "scheduler_authority_ref": "scheduler:c1",
        },
    )


def _revoke_lease_command(*, number: int, expected_stream_version: int) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RevokeLease",
        LEASE_ID,
        expected_stream_version,
        {
            "lease_id": LEASE_ID,
            "revocation_reason": "owner revoked the bounded lease",
            "observed_at": OBSERVED_AT,
        },
    )


def _release_resources_command(
    *,
    number: int,
    expected_stream_version: int = 1,
    resource_grant_id: str = RESOURCE_GRANT_ID,
    lease_id: str = LEASE_ID,
) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ReleaseResources",
        resource_grant_id,
        expected_stream_version,
        {
            "resource_id": resource_grant_id,
            "lease_id": lease_id,
            "consumption_reconciliation": ["cpu=1", "ram=1024", "io=256"],
            "cleanup_evidence_refs": ["evidence:cleanup:c1"],
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


def _c1_control_plane(tmp_path: Path, *, now: datetime = C1_NOW):
    return control_plane(tmp_path, clock=lambda: now)


def _mutable_c1_control_plane(tmp_path: Path):
    clock = {"now": C1_NOW}
    return control_plane(tmp_path, clock=lambda: clock["now"]), clock


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
    ("row_id", "command_type", "event_type"),
    C1_ROWS,
    ids=[row_id for row_id, _, _ in C1_ROWS],
)
def test_c1_rows_have_exact_runtime_schema_bindings(tmp_path, row_id, command_type, event_type):
    registry = control_plane(tmp_path).schemas
    command = registry.command_binding(command_type)
    event = registry.event_binding(event_type, command_type)

    assert command is not None, row_id
    assert event is not None, row_id
    assert command.schema_id == f"ars://core/command/{command_type}"
    assert event.schema_id == f"ars://core/event/{event_type}"
    assert command.schema_version == event.schema_version == "1.0.0"


@pytest.mark.parametrize(
    ("row_id", "command_type", "event_type"),
    C1_ROWS,
    ids=[row_id for row_id, _, _ in C1_ROWS],
)
def test_c1_rows_preserve_the_protected_schema_bytes(tmp_path, row_id, command_type, event_type):
    registry = control_plane(tmp_path).schemas
    command_identity = registry.resolve_identity(f"ars://core/command/{command_type}", "1.0.0")
    event_identity = registry.resolve_identity(f"ars://core/event/{event_type}", "1.0.0")

    assert command_identity.sha256 == COMMAND_SCHEMA_SHA256[command_type], row_id
    assert sha256(command_identity.raw_bytes).hexdigest() == COMMAND_SCHEMA_SHA256[command_type]
    assert event_identity.sha256 == EVENT_SCHEMA_SHA256[event_type], row_id
    assert sha256(event_identity.raw_bytes).hexdigest() == EVENT_SCHEMA_SHA256[event_type]


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

    expected_grant = _expected_resource_grant_record(request["payload"])
    assert harness.objects.read("resource_grant", RESOURCE_GRANT_ID, 1) == expected_grant
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][RESOURCE_GRANT_ID] == {
        "resource_id": RESOURCE_GRANT_ID,
        "status": "active",
        "request": expected_grant["granted_claims"],
        "grant": expected_grant,
        "version": 1,
    }
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
    conflicting = _expected_resource_grant_record(request["payload"])
    conflicting["expires_at"] = "2026-08-01T12:45:00Z"
    harness.objects.write("resource_grant", RESOURCE_GRANT_ID, 1, conflicting)
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


def test_claim_execution_lease_rejects_mismatched_materialization_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_resource_request(harness)
    mismatched = deepcopy(harness.objects.read("resource_grant", RESOURCE_GRANT_ID, 1))
    mismatched["expires_at"] = "2026-08-01T12:45:00Z"
    _replace_resource_grant_record(harness, mismatched)
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(_claim_execution_lease_command(number=5))

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_mismatch"
    assert _domain_snapshot(harness) == before


def test_claim_execution_lease_rejects_expired_materialization_without_domain_mutation(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    _seed_acknowledged_dispatch(harness)
    request = _request_resource_command(harness, number=4)
    request["payload"]["resource_request"]["deadline"] = "2026-08-01T12:15:00Z"
    _assert_event(
        harness,
        request,
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
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
    assert not harness.objects.revision_exists("resource_grant", RESOURCE_GRANT_ID, 1)
    assert _grant_admission_snapshot(harness)["receipts"] == before_interruption["receipts"]

    monkeypatch.setattr(harness.objects, "write", original_write)
    receipt = harness.service.submit(request)

    assert receipt.status == "accepted"
    assert tuple(harness.ledger.iter_events()) == committed
    assert harness.objects.read("resource_grant", RESOURCE_GRANT_ID, 1) == _expected_resource_grant_record(
        request["payload"]
    )


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

    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert any(
        event["event_type"] == "TaskClaimStarted" and event["stream_id"] == TASK_ID
        for event in harness.ledger.iter_events()
    )
    assert projection["streams"][TASK_ID]["status"] == "in_progress"
    assert projection["streams"][ATTEMPT_ID]["status"] == "running"


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
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)

    terminal = command_factory(number=8, expected_stream_version=1)
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
    _seed_lease(harness)
    renewal = _renew_lease_command(
        number=10,
        expected_stream_version=1,
        new_expiry="2026-08-01T14:00:00Z",
    )
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(renewal)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_grant_expiry_exceeded"
    assert _rejection_snapshot(harness) == before


def test_renewal_accepts_later_fractional_instant_below_deliberately_later_grant_ceiling(tmp_path):
    harness = _c1_control_plane(tmp_path)
    _seed_ready_task(harness)
    _seed_acknowledged_dispatch(harness)
    request = _request_resource_command(harness, number=4)
    request["payload"]["resource_request"]["deadline"] = "2026-08-01T14:00:00Z"
    _assert_event(
        harness,
        request,
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _claim_execution_lease_command(number=5),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )
    renewal = _renew_lease_command(number=10, expected_stream_version=1)
    renewal["payload"]["new_expiry"] = "2026-08-01T13:00:00.500Z"

    receipt = harness.service.submit(renewal)

    assert receipt.status == "accepted"
    assert (
        replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)["streams"][LEASE_ID]["expires_at"]
        == "2026-08-01T13:00:00.500Z"
    )


def test_resource_release_requires_its_owning_lease_but_can_follow_lease_release(tmp_path):
    harness = _c1_control_plane(tmp_path)
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
    foreign = _release_resources_command(number=8, lease_id=OTHER_LEASE_ID)
    before = _rejection_snapshot(harness)

    rejected = harness.service.submit(foreign)

    assert rejected.status == "rejected"
    assert rejected.reason_code == "resource_lease_mismatch"
    assert _rejection_snapshot(harness) == before
    _assert_event(
        harness,
        _release_lease_command(number=9, expected_stream_version=1),
        event_type="LeaseReleased",
        resulting_stream_version=2,
    )
    receipt = harness.service.submit(_release_resources_command(number=10))
    assert receipt.status == "accepted"
    projection = replay(tuple(harness.ledger.iter_events()), schema_registry=harness.schemas)
    assert projection["streams"][LEASE_ID]["status"] == "released"
    assert projection["streams"][RESOURCE_GRANT_ID]["status"] == "released"


@pytest.mark.parametrize(
    "field",
    ("host_identity", "boot_identity", "process_identity_id"),
    ids=["wrong-host", "wrong-boot", "wrong-process"],
)
def test_heartbeat_requires_the_live_host_boot_and_process_identity(tmp_path, field):
    harness = _c1_control_plane(tmp_path)
    _seed_lease(harness)
    command = _heartbeat_command(number=11, expected_stream_version=1)
    command["payload"][field] = OTHER_PROCESS_ID if field == "process_identity_id" else f"{field}:other"
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)
    assert rejected.status in {"rejected", "conflict"}
    assert _domain_snapshot(harness) == before


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
