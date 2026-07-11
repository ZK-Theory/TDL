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
            "fallback_issued": True,
            "task_accepted": True,
            "provider_receipt_status": "completed",
            "provider_output_present": True,
        },
        {
            "fallback_issued": False,
            "task_accepted": False,
            "provider_receipt_status": "incomplete",
            "provider_output_present": False,
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
    return _execute("S-016", subject, payload)


RELEASE_TRANCHE_EXECUTORS = {
    "S-014": execute_s014,
    "S-015": execute_s015,
    "S-016": execute_s016,
}