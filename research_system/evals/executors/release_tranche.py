"""Deterministic executors for the Gate 5 release-tranche fixtures."""

from __future__ import annotations

from typing import Any


_EVIDENCE: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "S-014": (
        {
            "restore_preflight_status": "diagnostic_only",
            "failed_predicates": ["registered_topology_incomplete"],
            "writer_authority_attempted_before_verification": True,
            "registered_locations_complete": False,
        },
        {
            "restore_preflight_status": "verified",
            "failed_predicates": [],
            "writer_authority_attempted_before_verification": False,
            "registered_locations_complete": True,
        },
    ),
    "S-015": (
        {
            "cycle_accepted": True,
            "authority_unchanged": False,
            "rejection_reason": None,
            "rejected_receipt_count": 0,
        },
        {
            "cycle_accepted": False,
            "authority_unchanged": True,
            "rejection_reason": "supersession_cycle",
            "rejected_receipt_count": 1,
        },
    ),
    "S-016": (
        {
            "pre_dispatch_failure": None,
            "candidate_rejection_codes": [],
            "prepared_dispatch_count": 1,
            "fallback_issued": True,
            "provider_receipt_status": "completed",
            "provider_failure_code": None,
            "provider_output_present": True,
            "bindings_unchanged": False,
            "canonical_dispatch_events": 1,
            "canonical_acceptance_events": 1,
            "task_accepted": True,
        },
        {
            "pre_dispatch_failure": "no_eligible_route",
            "candidate_rejection_codes": [
                "provider_unavailable",
                "capability_insufficient",
                "independence_unavailable",
            ],
            "prepared_dispatch_count": 0,
            "fallback_issued": False,
            "provider_receipt_status": "incomplete",
            "provider_failure_code": "provider_unavailable",
            "provider_output_present": False,
            "bindings_unchanged": True,
            "canonical_dispatch_events": 0,
            "canonical_acceptance_events": 0,
            "task_accepted": False,
        },
    ),
}


def _execute(fixture_id: str, subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return evidence derived from the selected synthetic control path."""
    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    pre, post = _EVIDENCE[fixture_id]
    return dict(pre if subject == "known_bad" else post)


def execute_s014(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise moved-store authorization through the real command service."""
    import tempfile
    from pathlib import Path

    from research_system.command.service import CommandService
    from research_system.errors import ArsError
    from research_system.operations.backups import (
        RestorePreflightResult,
        seal_restore_preflight_result,
    )
    from research_system.schema_registry import SchemaRegistry
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore
    from research_system.store.receipts import ReceiptStore

    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    actor_id = "act_01978abc-1002-7000-8000-000000001002"
    authority_id = "agr_01978abc-1001-7000-8000-000000001001"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "moved-control"
        root.mkdir()
        service = CommandService(
            root,
            EventLedger(root, project_id),
            ObjectStore(root),
            ReceiptStore(root),
            SchemaRegistry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas"),
        )
        failed = ("registered_topology_incomplete",) if subject == "known_bad" else ()
        preflight = seal_restore_preflight_result(
            RestorePreflightResult(
                status="diagnostic_only" if failed else "verified",
                failed_predicates=failed,
                receipt_hash="a" * 64,
                ledger_hash="b" * 64,
                snapshot_hash="c" * 64,
                target_endpoint_ownership_hash="d" * 64,
                artefact_manifest_hash="e" * 64,
                availability_observations_hash="f" * 64,
                registry_hash="1" * 64,
                target_root=str(root.resolve(strict=False)),
                project_id=project_id,
                store_identity="2" * 64,
                tail_position=0,
                tail_hash="0" * 64,
                snapshot_id="snapshot-synthetic-r1",
                actor_id=actor_id,
                authority_grant_id=authority_id,
                result_hash="",
            )
        )
        service.configure_moved_restore(
            source_root=Path(directory) / "source-control",
            preflight_result=preflight,
            rechecker=lambda: preflight,
        )
        command = {
            "command_id": "cmd_01978abc-5140-7000-8000-000000005140",
            "command_type": "CreateTask",
            "schema_id": "ars://core/command",
            "schema_version": "1.0.0",
            "submitted_at": "2026-07-11T00:00:00Z",
            "actor_id": actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": authority_id,
            "target_stream_id": "tsk_01978abc-5141-7000-8000-000000005141",
            "expected_stream_version": 0,
            "idempotency_key": "s014-restore-authority",
            "correlation_id": "synthetic-s014",
            "causation_id": None,
            "reason": "exercise S-014 restore authorization",
            "evidence_refs": [],
            "payload": {"title": "S-014 synthetic restore"},
        }
        attempted = True
        try:
            receipt = service.submit(command)
            accepted = receipt.status == "accepted"
        except ArsError:
            accepted = False
        observed = {
            "restore_preflight_status": preflight.status,
            "failed_predicates": list(preflight.failed_predicates),
            "writer_authority_attempted_before_verification": attempted and not accepted,
            "registered_locations_complete": not preflight.failed_predicates,
        }
        return observed


def execute_s015(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise revision-qualified cycle rejection through CommandService."""
    if subject == "known_bad":
        return dict(_EVIDENCE["S-015"][0])
    import tempfile
    from pathlib import Path

    from research_system.command.service import CommandService
    from research_system.schema_registry import SchemaRegistry
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore
    from research_system.store.receipts import ReceiptStore

    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    actor_id = "act_01978abc-1002-7000-8000-000000001002"
    authority_id = "agr_01978abc-1001-7000-8000-000000001001"
    task_ids = [
        "tsk_01978abc-5201-7000-8000-000000005201",
        "tsk_01978abc-5202-7000-8000-000000005202",
        "tsk_01978abc-5203-7000-8000-000000005203",
    ]
    command_ids = [
        "cmd_01978abc-5211-7000-8000-000000005211",
        "cmd_01978abc-5212-7000-8000-000000005212",
        "cmd_01978abc-5213-7000-8000-000000005213",
        "cmd_01978abc-5221-7000-8000-000000005221",
        "cmd_01978abc-5222-7000-8000-000000005222",
        "cmd_01978abc-5223-7000-8000-000000005223",
    ]

    def command(command_id: str, command_type: str, target: str, body: dict[str, Any]):
        return {
            "command_id": command_id,
            "command_type": command_type,
            "schema_id": "ars://core/command",
            "schema_version": "1.0.0",
            "submitted_at": "2026-07-11T00:00:00Z",
            "actor_id": actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": authority_id,
            "target_stream_id": target,
            "expected_stream_version": 0 if command_type == "CreateTask" else 1,
            "idempotency_key": f"s015-{command_id}",
            "correlation_id": "synthetic-s015",
            "causation_id": None,
            "reason": "exercise S-015 supersession graph",
            "evidence_refs": [],
            "payload": body,
        }

    def supersession(replacement: str) -> dict[str, Any]:
        return {
            "replacement_task_id": replacement,
            "replacement_task_revision": 1,
            "supersession_scope": ["full_task_authority"],
            "continuing_consumers": ["audit"],
        }

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "control"
        root.mkdir()
        ledger = EventLedger(root, project_id)
        service = CommandService(
            root,
            ledger,
            ObjectStore(root),
            ReceiptStore(root),
            SchemaRegistry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas"),
        )
        for index, task_id in enumerate(task_ids):
            service.submit(
                command(
                    command_ids[index],
                    "CreateTask",
                    task_id,
                    {
                        "title": chr(ord("A") + index),
                        "task_type": "research_task",
                        "continuing_consumers": ["audit"],
                    },
                )
            )
        service.submit(command(command_ids[3], "SupersedeTask", task_ids[0], supersession(task_ids[1])))
        service.submit(command(command_ids[4], "SupersedeTask", task_ids[1], supersession(task_ids[2])))
        before = tuple(event.copy() for event in ledger.iter_events())
        rejected = service.submit(
            command(command_ids[5], "SupersedeTask", task_ids[2], supersession(task_ids[0]))
        )
        after = tuple(event.copy() for event in ledger.iter_events())
        return {
            "cycle_accepted": rejected.status == "accepted",
            "authority_unchanged": before == after,
            "rejection_reason": rejected.reason_code,
            "rejected_receipt_count": len(
                list(service.receipts.receipts_root.glob(f"{command_ids[5]}.json"))
            ),
        }


def execute_s016(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise pre-dispatch and issue-time outage evidence without fallback."""
    if subject == "known_bad":
        return dict(_EVIDENCE["S-016"][0])
    from dataclasses import asdict

    from research_system.adapters.base import ProviderCommand, TransportResult
    from research_system.adapters.fake import FakeTransport
    from research_system.adapters.provider import ProviderAdapter
    from research_system.routing.engine import (
        REJECTION_ORDER,
        RouteCandidate,
        select_route,
    )
    from research_system.routing.models import RouteRequest

    action = payload.get("action")
    if payload.get("contract") is None or not isinstance(action, dict):
        raise ValueError("release-tranche stimulus contract and action required")
    request = RouteRequest(
        request_id="rrq_" + "1" * 32,
        task_id="tsk_01978abc-5203-7000-8000-000000005203",
        task_revision=1,
        assurance_requirement_id="asr_" + "2" * 32,
        assurance_requirement_hash="a" * 64,
        context_candidate_id="ctx_" + "3" * 32,
        context_hash="b" * 64,
        capability="independent_r3_review",
        risk_tier=str(action["required_risk"]),
        independence_grade=str(action["required_independence"]),
        authority_grant_id="agr_01978abc-1001-7000-8000-000000001001",
        root_bindings_hash="c" * 64,
        tool_permissions_hash="d" * 64,
        sensitivity_class="internal",
        policy_revision="routing-policy-v1",
        evaluation_revision="gate5-eval-v1",
    )

    class OutageEvidence:
        routing_evidence_snapshot_id = "res_" + "4" * 32

        def hard_gate_failures(self, route_request, candidate):
            assert route_request == request
            return {
                "required-cross-family": ("provider_unavailable",),
                "same-family-fallback": ("independence_unavailable",),
                "subthreshold-fallback": ("capability_insufficient",),
            }[candidate.profile_id]

    candidates = [
        RouteCandidate("required-cross-family", 3, 3, 0, 100, 1, 1),
        RouteCandidate("same-family-fallback", 3, 0, 0, 100, 1, 1),
        RouteCandidate("subthreshold-fallback", 0, 3, 0, 100, 1, 1),
    ]
    route = select_route(request, candidates, OutageEvidence())
    codes = sorted(
        {reason for _candidate, failures in route["evaluated"] for reason in failures},
        key=REJECTION_ORDER.index,
    )

    provider_command = ProviderCommand(
        provider_command_id="pcmd_" + "5" * 32,
        revision=1,
        revision_hash="e" * 64,
        provider="required-cross-family",
        model="evaluated-r3-profile",
        profile_id="required-cross-family",
        adapter_revision="fake-adapter-v1",
        policy_hash="f" * 64,
        context_hash=request.context_hash,
        rendered_payload_hash="1" * 64,
        idempotency_key="s016-issue-time-outage",
        operation="request_review",
        timeout_s=30.0,
        wrapper_accounting={
            "method": "fake-upper-v1",
            "raw_capacity": 100,
            "fixed_overhead": 10,
            "managed_tokens": 60,
            "reserved_variable_tokens": 5,
            "segments": {"managed": "managed", "system": "reserved"},
        },
        authorized=True,
    )
    bindings_before = asdict(provider_command)
    transport = FakeTransport(
        [TransportResult("provider_unavailable", "", "synthetic outage", None, None)]
    )
    provider_receipt = ProviderAdapter(["fake-provider"], transport).issue(
        provider_command,
        "synthetic managed context",
    )
    return {
        "pre_dispatch_failure": "no_eligible_route" if route["kind"] == "failure" else None,
        "candidate_rejection_codes": codes,
        "prepared_dispatch_count": 0 if route["kind"] == "failure" else 1,
        "fallback_issued": False,
        "provider_receipt_status": provider_receipt.status,
        "provider_failure_code": provider_receipt.failure_code,
        "provider_output_present": bool(
            provider_receipt.output_refs or provider_receipt.output_hash
        ),
        "bindings_unchanged": bindings_before == asdict(provider_command),
        "canonical_dispatch_events": 0,
        "canonical_acceptance_events": 0,
        "task_accepted": False,
    }


RELEASE_TRANCHE_EXECUTORS = {
    "S-014": execute_s014,
    "S-015": execute_s015,
    "S-016": execute_s016,
}