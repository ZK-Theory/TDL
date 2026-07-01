from __future__ import annotations

from pathlib import Path
from typing import Any

from research_system.command.models import Command, Receipt
from research_system.errors import ArsError, ConflictError
from research_system.ids import new_id
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


class CommandService:
    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        objects: ObjectStore,
        receipts: ReceiptStore,
        schemas: SchemaRegistry,
    ):
        self.control_root = control_root
        self.ledger = ledger
        self.objects = objects
        self.receipts = receipts
        self.schemas = schemas

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        self.schemas.validate('ars://core/command', envelope)
        command = Command(dict(envelope))
        replay(self.ledger.iter_events())
        existing = self._matching_committed(command)
        if existing is not None:
            return self._return_or_reconstruct(existing)
        with WriterLock(
            self.control_root / 'runtime' / 'writer.lock',
            {'command_id': command.command_id},
        ):
            replay(self.ledger.iter_events())
            existing = self._matching_committed(command)
            if existing is not None:
                return self._return_or_reconstruct(existing)
            observed_version = self._stream_version(command.target_stream_id)
            if observed_version != command.expected_stream_version:
                return Receipt(
                    status='conflict',
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=None,
                    observed_stream_version=observed_version,
                    reason_code='stream_version_conflict',
                )
            event = self._build_event(command)
            ledger_receipt = self.ledger.append([event])
            accepted = Receipt(
                status='accepted',
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=ledger_receipt['event_batch_id'],
                observed_stream_version=observed_version + 1,
            )
            return self.receipts.write(accepted)

    def _matching_committed(self, command: Command) -> list[dict[str, Any]] | None:
        for batch in self.ledger.iter_batches():
            first = batch[0]
            same_scope = (
                first.get('actor_id') == command.actor_id
                and first.get('authority_grant_id')
                == command.envelope['authority_grant_id']
                and first.get('command_type') == command.envelope['command_type']
                and first.get('idempotency_key') == command.idempotency_key
            )
            if not same_scope:
                continue
            if (
                first.get('command_id') != command.command_id
                or first.get('command_payload_hash') != command.payload_hash
                or first.get('command_type') != command.envelope['command_type']
                or first.get('stream_id') != command.target_stream_id
            ):
                raise ConflictError('idempotency key conflicts with committed command')
            return list(batch)
        return None

    def _return_or_reconstruct(self, events: list[dict[str, Any]]) -> Receipt:
        command_id = events[0]['command_id']
        stored = self.receipts.load(command_id)
        if stored is not None:
            return stored
        receipt = Receipt(
            status='accepted',
            command_id=command_id,
            payload_hash=events[0]['command_payload_hash'],
            event_batch_id=events[0]['transaction_id'],
            observed_stream_version=max(event['stream_version'] for event in events),
        )
        return self.receipts.write(receipt)

    def _stream_version(self, stream_id: str) -> int:
        return max(
            (
                event['stream_version']
                for event in self.ledger.iter_events()
                if event['stream_id'] == stream_id
            ),
            default=0,
        )

    def _build_event(self, command: Command) -> dict[str, Any]:
        command_type = command.envelope['command_type']
        if command_type == 'CreateTask':
            self.objects.write(
                'task',
                command.target_stream_id,
                1,
                command.envelope['payload'],
            )
            event_type = 'TaskCreated'
            payload = command.envelope['payload']
        elif command_type == 'ClaimDispatch':
            event_type = 'DispatchClaimed'
            payload = {'attempt_id': new_id('attempt')}
        else:
            raise ArsError(f'unsupported command type: {command_type}')
        return {
            'event_type': event_type,
            'stream_id': command.target_stream_id,
            'command_id': command.command_id,
            'command_type': command_type,
            'actor_id': command.actor_id,
            'authority_grant_id': command.envelope['authority_grant_id'],
            'idempotency_key': command.idempotency_key,
            'command_payload_hash': command.payload_hash,
            'correlation_id': command.envelope['correlation_id'],
            'causation_id': command.envelope['causation_id'],
            'schema_id': f'ars://core/event/{event_type}',
            'schema_version': '1.0.0',
            'occurred_at': None,
            'payload': payload,
        }
