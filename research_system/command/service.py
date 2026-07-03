from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_system.command.models import Command, Receipt
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import new_id
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger, LedgerSnapshot
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


@dataclass
class _CommandView:
    fingerprint: tuple[tuple[str, int, int], ...]
    batches_by_command_id: dict[str, list[dict[str, Any]]]
    batches_by_scope: dict[tuple[str, str, str, str], list[dict[str, Any]]]
    stream_versions: dict[str, int]

    @classmethod
    def from_snapshot(cls, snapshot: LedgerSnapshot) -> _CommandView:
        replay(snapshot.events)
        view = cls(snapshot.fingerprint, {}, {}, dict(snapshot.stream_versions))
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in snapshot.events:
            batches.setdefault(event['transaction_id'], []).append(event)
        for batch in batches.values():
            view._index_batch(batch)
        return view

    def extend(
        self,
        events: tuple[dict[str, Any], ...],
        fingerprint: tuple[tuple[str, int, int], ...],
    ) -> None:
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            batches.setdefault(event['transaction_id'], []).append(event)
            self.stream_versions[event['stream_id']] = event['stream_version']
        for batch in batches.values():
            self._index_batch(batch)
        self.fingerprint = fingerprint

    def _index_batch(self, batch: list[dict[str, Any]]) -> None:
        first = batch[0]
        self.batches_by_command_id[first['command_id']] = batch
        self.batches_by_scope[
            (
                first['actor_id'],
                first['authority_grant_id'],
                first['command_type'],
                first['idempotency_key'],
            )
        ] = batch


class CommandService:
    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        objects: ObjectStore,
        receipts: ReceiptStore,
        schemas: SchemaRegistry,
    ) -> None:
        self.control_root = control_root
        self.ledger = ledger
        self.objects = objects
        self.receipts = receipts
        self.schemas = schemas
        self._view: _CommandView | None = None
        self.deletion_manifest_authorizer: Callable[
            [dict[str, Any], str, str],
            dict[str, Any],
        ] | None = None

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Validate WP1 integrity controls; authorization remains downstream."""
        self.schemas.validate('ars://core/command', envelope)
        command = Command(dict(envelope))
        with WriterLock(
            self.control_root / 'runtime' / 'writer.lock',
            {'command_id': command.command_id},
        ):
            stored_conflict = self._stored_conflict_receipt(command)
            if stored_conflict is not None:
                return stored_conflict
            snapshot = self.ledger.snapshot()
            view = self._view_for(snapshot)
            existing = self._matching_committed(command, view)
            if existing is not None:
                return self._return_or_reconstruct(existing)
            observed_version = view.stream_versions.get(command.target_stream_id, 0)
            if observed_version != command.expected_stream_version:
                return self.receipts.write(
                    Receipt(
                        status='conflict',
                        command_id=command.command_id,
                        payload_hash=command.payload_hash,
                        event_batch_id=None,
                        observed_stream_version=observed_version,
                        reason_code='stream_version_conflict',
                    )
                )
            event = self._build_event(command)
            ledger_receipt = self.ledger.append([event], snapshot=snapshot)
            updated = self.ledger.snapshot()
            view.extend(updated.events[len(snapshot.events) :], updated.fingerprint)
            accepted = Receipt(
                status='accepted',
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=ledger_receipt['event_batch_id'],
                observed_stream_version=ledger_receipt[
                    'resulting_stream_versions'
                ][command.target_stream_id],
            )
            return self.receipts.write(accepted)

    def _stored_conflict_receipt(self, command: Command) -> Receipt | None:
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != 'conflict':
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError('command ID conflicts with stored receipt')
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or stored.reason_code != 'stream_version_conflict'
        ):
            raise IntegrityError('stored conflict receipt is inconsistent')
        return stored

    def _view_for(self, snapshot: LedgerSnapshot) -> _CommandView:
        if self._view is None or self._view.fingerprint != snapshot.fingerprint:
            self._view = _CommandView.from_snapshot(snapshot)
        return self._view

    def _matching_committed(
        self, command: Command, view: _CommandView
    ) -> list[dict[str, Any]] | None:
        scope = (
            command.actor_id,
            command.envelope['authority_grant_id'],
            command.envelope['command_type'],
            command.idempotency_key,
        )
        scoped = view.batches_by_scope.get(scope)
        if scoped is not None:
            first = scoped[0]
            same_submission = (
                first.get('command_payload_hash') == command.payload_hash
                and first.get('stream_id') == command.target_stream_id
            )
            if first.get('command_id') == command.command_id and same_submission:
                return list(scoped)
            raise ConflictError('idempotency key conflicts with committed command')
        identified = view.batches_by_command_id.get(command.command_id)
        if identified is not None:
            raise ConflictError('command ID conflicts with committed command')
        return None

    def _return_or_reconstruct(self, events: list[dict[str, Any]]) -> Receipt:
        receipt = Receipt(
            status='accepted',
            command_id=events[0]['command_id'],
            payload_hash=events[0]['command_payload_hash'],
            event_batch_id=events[0]['transaction_id'],
            observed_stream_version=max(
                event['stream_version']
                for event in events
                if event['stream_id'] == events[0]['stream_id']
            ),
        )
        stored = self.receipts.load(receipt.command_id)
        if stored is not None:
            if stored != receipt:
                raise IntegrityError('stored receipt does not match committed batch')
            return stored
        return self.receipts.write(receipt)

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
        elif command_type == 'VerifyEvidenceDeletion':
            if self.deletion_manifest_authorizer is None:
                raise ArsError(
                    'VerifyEvidenceDeletion requires a trusted deletion '
                    'manifest authorizer'
                )
            payload = self.deletion_manifest_authorizer(
                command.envelope['payload'],
                command.actor_id,
                command.envelope['authority_grant_id'],
            )
            if payload.get('status') != 'verified':
                raise ArsError('deletion manifest authorizer did not verify')
            event_type = 'EvidenceDeletionVerified'
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
