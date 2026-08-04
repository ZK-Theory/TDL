from copy import deepcopy
import json
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.operations.profiles import CURRENT_OPERATIONAL_PROFILE_POLICY
from research_system.operations.resources import (
    RESOURCE_GRANT_V1_1_SCHEMA_ID,
    RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
    TrustedRuntimeAuthority,
    derive_resource_grant_authority_preimage,
    derive_resource_grant_authority_preimage_ref,
    derive_resource_grant_v1_1_record,
)
from research_system.schema_registry import SchemaRegistry


PROJECT_ID = "prj_0198825f-0001-7000-8000-000000000001"
RESOURCE_GRANT_ID = "rgr_0198825f-0002-7000-8000-000000000002"
RESOURCE_REQUEST_ID = "rsq_0198825f-0003-7000-8000-000000000003"
ATTEMPT_ID = "att_0198825f-0004-7000-8000-000000000004"
TASK_ID = "tsk_0198825f-0005-7000-8000-000000000005"
DISPATCH_ID = "dsp_0198825f-0006-7000-8000-000000000006"


def _trusted_authority() -> TrustedRuntimeAuthority:
    return TrustedRuntimeAuthority(
        host_identity="host:sha256:" + "1" * 64,
        boot_identity="boot:sha256:" + "2" * 64,
        control_store_identity="3" * 64,
        store_manifest_sha256="a" * 64,
    )


def _resource_request(
    *,
    deadline: str = "2026-08-04T14:00:00Z",
    projection_evidence_refs: list[str] | None = None,
) -> dict:
    policy = CURRENT_OPERATIONAL_PROFILE_POLICY
    evidence = {
        "disposition": "required",
        "policy_id": policy.policy_id,
        "rationale": "The bounded execution profile requires this evidence.",
        "applicability_evidence_refs": ["evidence:bounded"],
    }
    return {
        "task_id": TASK_ID,
        "dispatch_id": DISPATCH_ID,
        "attempt_id": ATTEMPT_ID,
        "operation_class": "bounded-analysis",
        "operational_profile": "bounded",
        "resource_request_id": RESOURCE_REQUEST_ID,
        "route_id": "route:unit",
        "provider_requirements": ["python"],
        "runtime_requirements": ["direct-venv"],
        "operational_profile_policy_id": policy.policy_id,
        "operational_profile_revision": policy.policy_revision,
        "requesting_actor_id": "act_0198825f-0007-7000-8000-000000000007",
        "requesting_profile": "unit-test",
        "requesting_authority_grant_id": "agr_0198825f-0008-7000-8000-000000000008",
        "expected_control_store_position": 7,
        "requested_host_pool": ["host:sha256:" + "1" * 64],
        "root_bindings": [
            {
                "root_kind": "workspace",
                "canonical_uri": "C:/unit",
                "workspace_identity": "workspace:unit",
                "access_mode": "read_write",
                "expected_branch": "codex/unit",
                "expected_commit": "git:sha1:" + "b" * 40,
                "provenance_authority": "owner:unit",
            }
        ],
        "resource_ceilings": {
            "cpu_processes": 1,
            "cpu_threads": 2,
            "ram_working_bytes": 1024,
            "ram_peak_bytes": 2048,
            "gpu_devices": [],
            "storage_bytes": 4096,
            "io_bytes": 4096,
        },
        "network_constraints": ["network:none"],
        "external_write_constraints": ["external:none"],
        "sensitivity_constraints": ["internal"],
        "exclusive_resource_keys": ["workspace:unit"],
        "shared_resource_keys": [],
        "compatibility_keys": ["python:3.13"],
        "runtime_distribution": {
            "minimum_seconds": 1,
            "expected_seconds": 10,
            "maximum_seconds": 60,
            "uncertainty_basis": "unit fixture",
        },
        "deadline": deadline,
        "checkpoint_interval_seconds": 30,
        "benchmark_evidence_refs": ["evidence:benchmark"],
        "projection_evidence_refs": ([] if projection_evidence_refs is None else projection_evidence_refs),
        "stop_rules": ["stop on failure"],
        "pause_rules": ["pause on owner request"],
        "partial_rules": ["retain partial output"],
        "escalation_rules": ["escalate to owner"],
        "release_obligations": ["release lease"],
        "cleanup_obligations": ["remove temporary workspace"],
        "bounded_profile_evidence": {
            "heartbeat": evidence,
            "output_tail": evidence,
            "stop": evidence,
            "checkpoint": evidence,
        },
    }


def _committed_event(*, deadline: str = "2026-08-04T14:00:00Z") -> dict:
    request = _resource_request(deadline=deadline)
    request["projection_evidence_refs"] = [_authority_preimage_ref(request)]
    payload = {
        "resource_id": RESOURCE_GRANT_ID,
        "resource_request": request,
    }
    event = {
        "event_id": "evt_0198825f-0009-7000-8000-000000000009",
        "event_type": "ResourceGrantRequested",
        "schema_id": "ars://core/event/ResourceGrantRequested",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "stream_id": RESOURCE_GRANT_ID,
        "stream_version": 1,
        "global_position": 8,
        "transaction_id": "txb_0198825f-0010-7000-8000-000000000010",
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": "cmd_0198825f-0011-7000-8000-000000000011",
        "command_type": "RequestResourceGrant",
        "command_schema_id": "ars://core/command/RequestResourceGrant",
        "command_schema_version": "1.0.0",
        "command_schema_sha256": "c" * 64,
        "idempotency_key": "unit-resource-request",
        "command_payload_hash": sha256_hex(canonical_bytes(payload)),
        "correlation_id": "unit-resource-request",
        "causation_id": None,
        "actor_id": "act_0198825f-0007-7000-8000-000000000007",
        "authority_grant_id": "agr_0198825f-0008-7000-8000-000000000008",
        "occurred_at": "2026-08-04T11:30:00Z",
        "recorded_at": "2026-08-04T12:00:00Z",
        "payload": payload,
        "previous_event_hash": "0" * 64,
        "event_hash": "0" * 64,
    }
    _rehash_event(event)
    return event


def _rehash_event(event: dict) -> None:
    event["command_payload_hash"] = sha256_hex(canonical_bytes(event["payload"]))
    event["event_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in event.items() if key != "event_hash"})
    )


def _rebind_authority_preimage_ref(event: dict) -> None:
    request = event["payload"]["resource_request"]
    request["projection_evidence_refs"] = [_authority_preimage_ref(request)]


def _authority_preimage(request: dict) -> dict:
    return derive_resource_grant_authority_preimage(
        project_id=PROJECT_ID,
        resource_grant_id=RESOURCE_GRANT_ID,
        resource_request=request,
        trusted_authority=_trusted_authority(),
    )


def _authority_preimage_ref(request: dict) -> str:
    return derive_resource_grant_authority_preimage_ref(
        project_id=PROJECT_ID,
        resource_grant_id=RESOURCE_GRANT_ID,
        resource_request=request,
        trusted_authority=_trusted_authority(),
    )


def _derive(event: dict) -> dict:
    return derive_resource_grant_v1_1_record(
        committed_event=event,
        project_id=PROJECT_ID,
        trusted_authority=_trusted_authority(),
    )


def test_resource_grant_v1_1_is_deterministic_content_addressed_and_bounded():
    event = _committed_event()
    request = event["payload"]["resource_request"]
    authority_preimage = _authority_preimage(request)
    authority_ref = _authority_preimage_ref(request)

    grant = _derive(event)

    assert grant == _derive(deepcopy(event))
    assert grant["schema_id"] == RESOURCE_GRANT_V1_1_SCHEMA_ID
    assert grant["schema_version"] == RESOURCE_GRANT_V1_1_SCHEMA_VERSION
    assert grant["record_revision"] == 1
    assert grant["project_id"] == PROJECT_ID
    assert grant["source_event_id"] == event["event_id"]
    assert grant["source_event_hash"] == event["event_hash"]
    assert grant["source_command_id"] == event["command_id"]
    assert grant["source_command_payload_hash"] == event["command_payload_hash"]
    assert grant["issued_at"] == "2026-08-04T11:30:00Z"
    assert grant["maximum_lease_duration_s"] == 3600
    assert grant["expires_at"] == "2026-08-04T12:30:00Z"
    assert request["projection_evidence_refs"] == [authority_ref]
    assert grant["authority_preimage_ref"] == authority_ref
    assert grant["authority_preimage_sha256"] == authority_ref.rsplit("/", 1)[-1]
    assert grant["authority_preimage_sha256"] == sha256_hex(canonical_bytes(authority_preimage))
    assert grant["authority_request_basis_sha256"] == authority_preimage["authority_request_basis_sha256"]
    assert grant["requesting_actor_id"] == request["requesting_actor_id"]
    assert grant["requesting_authority_grant_id"] == request["requesting_authority_grant_id"]
    assert grant["expected_control_store_position"] == 7
    assert grant["accepted_policy_id"] == CURRENT_OPERATIONAL_PROFILE_POLICY.policy_id
    assert grant["accepted_policy_revision"] == "1.1.0"
    assert grant["accepted_policy_raw_sha256"] == (CURRENT_OPERATIONAL_PROFILE_POLICY.raw_sha256)
    assert grant["renewal_policy_ref"] == (
        "ars://operations/operational-profile-policy/"
        f"{CURRENT_OPERATIONAL_PROFILE_POLICY.policy_id}/1.1.0/bounded/renewal"
    )
    expected_claims = json.loads(canonical_bytes(event["payload"]["resource_request"]).decode("utf-8"))
    assert grant["granted_claims"] == expected_claims
    assert grant["resource_request_sha256"] == sha256_hex(canonical_bytes(event["payload"]["resource_request"]))
    assert grant["granted_claims_sha256"] == sha256_hex(canonical_bytes(expected_claims))
    assert grant["resource_request_sha256"] == grant["granted_claims_sha256"]
    assert grant["resource_request_sha256"] != grant["authority_request_basis_sha256"]
    preimage = {key: value for key, value in grant.items() if key != "content_hash"}
    assert grant["content_hash"] == sha256_hex(canonical_bytes(preimage))
    registry = SchemaRegistry(Path(".research-system/schemas"))
    registry.validate("ars://core/event/ResourceGrantRequested", event)
    registry.validate(
        RESOURCE_GRANT_V1_1_SCHEMA_ID,
        grant,
        schema_version=RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
    )


def test_resource_grant_authority_reference_is_generated_before_final_request():
    request = _resource_request()

    authority_ref = _authority_preimage_ref(request)
    preimage = _authority_preimage(request)
    request["projection_evidence_refs"] = [authority_ref]

    assert _authority_preimage_ref(request) == authority_ref
    assert authority_ref == (
        f"ars://operations/resource-grant-authority-preimage/sha256/{sha256_hex(canonical_bytes(preimage))}"
    )
    basis = {key: value for key, value in request.items() if key != "projection_evidence_refs"}
    assert preimage["authority_request_basis_sha256"] == sha256_hex(canonical_bytes(basis))
    assert sha256_hex(canonical_bytes(request)) != preimage["authority_request_basis_sha256"]


def test_resource_grant_v1_1_uses_request_deadline_when_it_precedes_profile_maximum():
    grant = _derive(_committed_event(deadline="2026-08-04T12:15:00Z"))

    assert grant["expires_at"] == "2026-08-04T12:15:00Z"


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("non_singleton_host_pool", "resource_grant_host_pool_invalid"),
        ("foreign_singleton_host", "resource_grant_host_pool_invalid"),
        ("missing_authority_preimage_ref", "resource_grant_authority_preimage_invalid"),
        ("extra_authority_preimage_ref", "resource_grant_authority_preimage_invalid"),
        ("wrong_authority_preimage_ref", "resource_grant_authority_preimage_invalid"),
        ("policy_id_mismatch", "resource_grant_policy_mismatch"),
        ("policy_revision_mismatch", "resource_grant_policy_mismatch"),
        ("forged_source_event_hash", "resource_grant_source_event_invalid"),
        ("expired_at_issue", "resource_grant_time_bounds_invalid"),
    ],
)
def test_resource_grant_v1_1_rejects_valid_shaped_authority_and_source_negatives(case, expected):
    event = _committed_event()
    if case == "non_singleton_host_pool":
        event["payload"]["resource_request"]["requested_host_pool"].append("host:sha256:" + "d" * 64)
        _rebind_authority_preimage_ref(event)
    elif case == "foreign_singleton_host":
        event["payload"]["resource_request"]["requested_host_pool"] = ["host:sha256:" + "b" * 64]
        _rebind_authority_preimage_ref(event)
    elif case == "missing_authority_preimage_ref":
        event["payload"]["resource_request"]["projection_evidence_refs"] = []
    elif case == "extra_authority_preimage_ref":
        event["payload"]["resource_request"]["projection_evidence_refs"].append(
            "ars://operations/resource-grant-authority-preimage/sha256/" + "e" * 64
        )
    elif case == "wrong_authority_preimage_ref":
        event["payload"]["resource_request"]["projection_evidence_refs"] = [
            "ars://operations/resource-grant-authority-preimage/sha256/" + "f" * 64
        ]
    elif case == "policy_id_mismatch":
        event["payload"]["resource_request"]["operational_profile_policy_id"] = (
            "pol_0198825f-0012-7000-8000-000000000012"
        )
    elif case == "policy_revision_mismatch":
        event["payload"]["resource_request"]["operational_profile_revision"] = "1.0.0"
    elif case == "forged_source_event_hash":
        event["event_hash"] = "f" * 64
    elif case == "expired_at_issue":
        event = _committed_event(deadline="2026-08-04T11:30:00Z")

    if case not in {
        "forged_source_event_hash",
        "expired_at_issue",
    }:
        _rehash_event(event)

    with pytest.raises(ValueError, match=expected):
        _derive(event)
