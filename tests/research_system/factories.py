from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_system.command.reducers import ControlPlaneState, replay_control_plane
from research_system.command.service import CommandService
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore

PROJECT_ID = 'prj_01978abc-1000-7000-8000-000000001000'
AUTHORITY_GRANT_ID = 'agr_01978abc-1001-7000-8000-000000001001'
ACTORS = {
    'actor-a': 'act_01978abc-1002-7000-8000-000000001002',
    'actor-b': 'act_01978abc-1003-7000-8000-000000001003',
}


@dataclass(frozen=True)
class ControlPlaneHarness:
    service: CommandService
    ledger: EventLedger
    objects: ObjectStore
    receipts: ReceiptStore

    def replay(self) -> ControlPlaneState:
        return replay_control_plane(self.ledger.iter_events())


def control_plane(tmp_path: Path) -> ControlPlaneHarness:
    root = tmp_path / 'control'
    root.mkdir()
    ledger = EventLedger(root, project_id=PROJECT_ID)
    objects = ObjectStore(root)
    receipts = ReceiptStore(root)
    schemas = SchemaRegistry(Path('.research-system/schemas'))
    service = CommandService(root, ledger, objects, receipts, schemas)
    return ControlPlaneHarness(service, ledger, objects, receipts)


def _command(
    command_id: str,
    idempotency_key: str,
    target_stream_id: str,
    payload: dict[str, Any],
    *,
    command_type: str,
    actor_id: str,
    expected_version: int,
) -> dict[str, Any]:
    return {
        'command_id': command_id,
        'command_type': command_type,
        'schema_id': 'ars://core/command',
        'schema_version': '1.0.0',
        'submitted_at': '2026-07-01T12:00:00Z',
        'actor_id': actor_id,
        'on_behalf_of_actor_id': None,
        'authority_grant_id': AUTHORITY_GRANT_ID,
        'target_stream_id': target_stream_id,
        'expected_stream_version': expected_version,
        'idempotency_key': idempotency_key,
        'correlation_id': 'synthetic-control-plane',
        'causation_id': None,
        'reason': 'synthetic P0 command test',
        'evidence_refs': [],
        'payload': payload,
    }


def create_task_command(
    command_id: str,
    idempotency_key: str,
    task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return _command(
        command_id,
        idempotency_key,
        task_id,
        payload,
        command_type='CreateTask',
        actor_id=ACTORS['actor-a'],
        expected_version=0,
    )


def claim_dispatch_command(
    command_id: str,
    actor: str,
    dispatch_id: str,
    *,
    expected_version: int,
) -> dict[str, Any]:
    return _command(
        command_id,
        f'claim-{actor}',
        dispatch_id,
        {},
        command_type='ClaimDispatch',
        actor_id=ACTORS[actor],
        expected_version=expected_version,
    )
