from __future__ import annotations

from copy import deepcopy
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
)


TASK_ID = "tsk_01978abc-7200-7000-8000-000000007200"
OTHER_TASK_ID = "tsk_01978abc-7201-7000-8000-000000007201"
DISPATCH_ID = "dsp_01978abc-7202-7000-8000-000000007202"
ATTEMPT_ID = "att_01978abc-7203-7000-8000-000000007203"
RESOURCE_REQUEST_ID = "rsq_01978abc-7204-7000-8000-000000007204"
RESOURCE_GRANT_ID = "rgr_01978abc-7205-7000-8000-000000007205"
LEASE_ID = "els_01978abc-7206-7000-8000-000000007206"
OTHER_LEASE_ID = "els_01978abc-7207-7000-8000-000000007207"
PROCESS_ID = "pid_01978abc-7208-7000-8000-000000007208"
OTHER_PROCESS_ID = "pid_01978abc-7209-7000-8000-000000007209"
HEARTBEAT_ID = "hbt_01978abc-7210-7000-8000-000000007210"
CHECKPOINT_ID = "cpm_01978abc-7211-7000-8000-000000007211"
POLICY_ID = "pol_01978abc-7212-7000-8000-000000007212"

GRANTED_AT = "2026-08-01T12:00:00Z"
INITIAL_EXPIRY = "2026-08-01T13:00:00Z"
RENEWED_EXPIRY = "2026-08-01T14:00:00Z"
OBSERVED_AT = "2026-08-01T12:20:00Z"


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


def _resource_request_payload() -> dict[str, Any]:
    evidence = {
        "disposition": "required",
        "policy_id": "policy:bounded-profile-v1",
        "rationale": "The bounded execution profile requires this evidence.",
        "applicability_evidence_refs": ["evidence:resource-profile:bounded"],
    }
    return {
        "resource_id": RESOURCE_GRANT_ID,
        "resource_request": {
            "task_id": TASK_ID,
            "dispatch_id": DISPATCH_ID,
            "attempt_id": ATTEMPT_ID,
            "operation_class": "bounded-analysis",
            "operational_profile": "bounded",
            "resource_request_id": RESOURCE_REQUEST_ID,
            "route_id": "route:c1-synthetic",
            "provider_requirements": ["python"],
            "runtime_requirements": ["direct-venv"],
            "operational_profile_policy_id": POLICY_ID,
            "operational_profile_revision": "1.0.0",
            "requesting_actor_id": ACTORS["actor-a"],
            "requesting_profile": "luna-max",
            "requesting_authority_grant_id": AUTHORITY_GRANT_ID,
            "expected_control_store_position": 0,
            "requested_host_pool": ["host:c1-synthetic"],
            "root_bindings": [
                {
                    "root_kind": "workspace",
                    "canonical_uri": "C:/workspace/c1",
                    "workspace_identity": "workspace:c1-synthetic",
                    "access_mode": "read_write",
                    "expected_branch": "codex/wp6-1-c1-luna-readiness-lease",
                    "expected_commit": "a" * 40,
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
            "deadline": INITIAL_EXPIRY,
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


def _request_resource_command(*, number: int) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "RequestResourceGrant",
        RESOURCE_GRANT_ID,
        0,
        _resource_request_payload(),
    )


def _claim_execution_lease_command(
    *,
    number: int,
    lease_id: str = LEASE_ID,
    expected_stream_version: int = 0,
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
            "dispatch_id": DISPATCH_ID,
            "attempt_id": ATTEMPT_ID,
            "expires_at": INITIAL_EXPIRY,
            "holder_actor_id": ACTORS["actor-a"],
            "resource_grant_id": RESOURCE_GRANT_ID,
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
            "new_expiry": RENEWED_EXPIRY,
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


def _release_resources_command(*, number: int, expected_stream_version: int = 1) -> dict[str, Any]:
    return _c1_command(
        _command_id(number),
        "ReleaseResources",
        RESOURCE_GRANT_ID,
        expected_stream_version,
        {
            "resource_id": RESOURCE_GRANT_ID,
            "lease_id": LEASE_ID,
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


def _domain_snapshot(harness) -> dict[str, Any]:
    events = tuple(harness.ledger.iter_events())
    ledger_snapshot = harness.ledger.snapshot()
    return {
        "events": events,
        "batches": tuple(harness.ledger.iter_batches()),
        "stream_versions": dict(ledger_snapshot.stream_versions),
        "objects": _json_files(harness.objects.control_root / "objects"),
        "receipts": _json_files(harness.receipts.receipts_root),
        "projection": replay(events, schema_registry=harness.schemas),
    }


def _assert_event(
    harness,
    command: dict[str, Any],
    *,
    event_type: str,
    resulting_stream_version: int,
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
    assert event["payload"] == command["payload"]
    return event


def _seed_lease(harness) -> None:
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
    _assert_event(
        harness,
        _request_resource_command(number=4),
        event_type="ResourceGrantRequested",
        resulting_stream_version=1,
    )
    _assert_event(
        harness,
        _claim_execution_lease_command(number=5),
        event_type="LeaseGranted",
        resulting_stream_version=1,
    )


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


def test_lease_resource_positive_path_preserves_live_identity_and_reconciles_release(tmp_path):
    harness = control_plane(tmp_path)
    _seed_lease(harness)

    heartbeat = _heartbeat_command(number=6, expected_stream_version=1)
    _assert_event(
        harness,
        heartbeat,
        event_type="HeartbeatRecorded",
        resulting_stream_version=2,
    )
    renewed = _renew_lease_command(number=7, expected_stream_version=2)
    renewed_event = _assert_event(
        harness,
        renewed,
        event_type="LeaseRenewed",
        resulting_stream_version=3,
    )
    assert renewed_event["payload"]["lease_id"] == LEASE_ID
    assert renewed_event["payload"]["holder_actor_id"] == ACTORS["actor-a"]
    assert renewed_event["payload"]["prior_expiry"] == INITIAL_EXPIRY
    assert renewed_event["payload"]["new_expiry"] == RENEWED_EXPIRY

    released = _release_lease_command(number=8, expected_stream_version=3)
    released_event = _assert_event(
        harness,
        released,
        event_type="LeaseReleased",
        resulting_stream_version=4,
    )
    assert released_event["payload"]["holder_actor_id"] == ACTORS["actor-a"]

    resources_released = _release_resources_command(number=9)
    resources_event = _assert_event(
        harness,
        resources_released,
        event_type="ResourcesReleased",
        resulting_stream_version=2,
    )
    assert resources_event["payload"]["resource_id"] == RESOURCE_GRANT_ID
    assert resources_event["payload"]["lease_id"] == LEASE_ID
    assert resources_event["payload"]["consumption_reconciliation"] == ["cpu=1", "ram=1024", "io=256"]


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
    harness = control_plane(tmp_path)
    _seed_lease(harness)

    terminal = command_factory(number=8, expected_stream_version=1)
    _assert_event(
        harness,
        terminal,
        event_type=event_type,
        resulting_stream_version=2,
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
    harness = control_plane(tmp_path)
    _seed_lease(harness)
    command = _renew_lease_command(number=10, expected_stream_version=1)
    command["payload"][field] = value
    before = _domain_snapshot(harness)

    rejected = harness.service.submit(command)
    assert rejected.status in {"rejected", "conflict"}
    assert _domain_snapshot(harness) == before


@pytest.mark.parametrize(
    "field",
    ("host_identity", "boot_identity", "process_identity_id"),
    ids=["wrong-host", "wrong-boot", "wrong-process"],
)
def test_heartbeat_requires_the_live_host_boot_and_process_identity(tmp_path, field):
    harness = control_plane(tmp_path)
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
    kwargs = {"number": 20}
    if command_factory is _claim_execution_lease_command:
        kwargs["expected_stream_version"] = 0
    elif command_factory is _renew_lease_command:
        kwargs["expected_stream_version"] = 0
    elif command_factory is _release_lease_command:
        kwargs["expected_stream_version"] = 0
    elif command_factory is _expire_lease_command:
        kwargs["expected_stream_version"] = 0
    elif command_factory is _revoke_lease_command:
        kwargs["expected_stream_version"] = 0
    elif command_factory is _heartbeat_command:
        kwargs["expected_stream_version"] = 0
    else:
        kwargs["expected_stream_version"] = 0
    command = command_factory(**kwargs)
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
