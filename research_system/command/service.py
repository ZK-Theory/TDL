from __future__ import annotations

import json

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_system.command.models import Command, Receipt
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import new_id
from research_system.operations.backups import (
    RestorePreflightResult,
    validate_restore_preflight_result,
)
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
        self._restore_source_root: Path | None = None
        self._restore_preflight_result: RestorePreflightResult | None = None
        self._restore_preflight_rechecker: Callable[[], RestorePreflightResult] | None = None

    def configure_moved_restore(
        self,
        *,
        source_root: Path,
        preflight_result: RestorePreflightResult,
        rechecker: Callable[[], RestorePreflightResult],
    ) -> None:
        """Bind a moved store to evidence that is rerun before each writer lock."""
        if source_root.resolve(strict=False) == self.control_root.resolve(strict=False):
            raise ValueError("moved restore source must differ from target")
        self._restore_source_root = source_root
        self._restore_preflight_result = preflight_result
        self._restore_preflight_rechecker = rechecker

    def _recheck_moved_restore(self, command: Command) -> None:
        if self._restore_source_root is None:
            return
        supplied = self._restore_preflight_result
        rechecker = self._restore_preflight_rechecker
        if supplied is None or rechecker is None:
            raise ArsError("moved store requires restore preflight")
        current = rechecker()
        validate_restore_preflight_result(
            current,
            current_root=self.control_root,
            project_id=self.ledger.project_id,
            actor_id=command.actor_id,
            authority_grant_id=command.envelope["authority_grant_id"],
        )
        if current != supplied:
            raise ArsError("restore preflight changed before writer lock")

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Validate WP1 integrity controls; authorization remains downstream."""
        self.schemas.validate('ars://core/command', envelope)
        command = Command(dict(envelope))
        self._recheck_moved_restore(command)
        with WriterLock(
            self.control_root / 'runtime' / 'writer.lock',
            {'command_id': command.command_id},
        ):
            stored_conflict = self._stored_conflict_receipt(command)
            if stored_conflict is not None:
                return stored_conflict
            stored_rejected = self._stored_rejected_receipt(command)
            if stored_rejected is not None:
                return stored_rejected
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
            prepared_payload = None
            if command.envelope['command_type'] == 'SupersedeTask':
                prepared = self._prepare_supersession(
                    command, snapshot, observed_version
                )
                if isinstance(prepared, Receipt):
                    return self.receipts.write(prepared)
                prepared_payload = prepared
            event = self._build_event(command, prepared_payload)
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

    def _stored_rejected_receipt(self, command: Command) -> Receipt | None:
        """Return an idempotent rejected receipt while holding WriterLock."""
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != 'rejected':
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError('command ID conflicts with stored receipt')
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or not stored.reason_code
            or not stored.explanation
            or not stored.unmet_preconditions
        ):
            raise IntegrityError('stored rejected receipt is inconsistent')
        return stored

    def _rejected(
        self,
        command: Command,
        observed_version: int,
        reason_code: str,
        explanation: str,
    ) -> Receipt:
        return Receipt(
            status='rejected',
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=None,
            observed_stream_version=observed_version,
            reason_code=reason_code,
            explanation=explanation,
            unmet_preconditions=(reason_code,),
        )

    def _task_revision_object(
        self,
        task_id: str,
        revision: int,
    ) -> dict[str, Any] | None:
        directory = self.control_root / 'objects' / 'task' / task_id
        matches = sorted(directory.glob(f'{revision:08d}-*.json'))
        if not matches:
            return None
        if len(matches) != 1:
            raise IntegrityError('duplicate immutable Task revision')
        try:
            value = json.loads(matches[0].read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityError('invalid immutable Task revision') from exc
        if not isinstance(value, dict):
            raise IntegrityError('Task revision object must be a mapping')
        return value

    @staticmethod
    def _revision_graph(
        snapshot: LedgerSnapshot,
    ) -> tuple[
        dict[str, int],
        dict[tuple[str, int], tuple[str, int]],
    ]:
        current: dict[str, int] = {}
        edges: dict[tuple[str, int], tuple[str, int]] = {}
        for event in snapshot.events:
            if event['event_type'] == 'TaskCreated':
                revision = int(event.get('payload', {}).get('revision', 1))
                current.setdefault(event['stream_id'], revision)
            elif event['event_type'] == 'TaskSuperseded':
                payload = event['payload']
                source = (
                    str(payload['source_task_id']),
                    int(payload['source_task_revision']),
                )
                replacement = (
                    str(payload['replacement_task_id']),
                    int(payload['replacement_task_revision']),
                )
                if source in edges:
                    raise IntegrityError('Task revision has multiple supersession edges')
                edges[source] = replacement
                if source[0] == replacement[0]:
                    current[source[0]] = replacement[1]
        return current, edges

    @staticmethod
    def _reaches(
        edges: dict[tuple[str, int], tuple[str, int]],
        start: tuple[str, int],
        target: tuple[str, int],
    ) -> bool:
        seen: set[tuple[str, int]] = set()
        pending = [start]
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            replacement = edges.get(node)
            if replacement is not None:
                pending.append(replacement)
        return False

    @staticmethod
    def _derived_lineage(
        edges: dict[tuple[str, int], tuple[str, int]],
        source: tuple[str, int],
        replacement: tuple[str, int],
    ) -> list[dict[str, Any]]:
        reverse = {target: origin for origin, target in edges.items()}
        lineage = [source]
        while lineage[0] in reverse:
            lineage.insert(0, reverse[lineage[0]])
        lineage.append(replacement)
        return [
            {'task_id': task_id, 'revision': revision}
            for task_id, revision in lineage
        ]

    def _prepare_supersession(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate a revision-qualified edge from one committed snapshot."""
        payload = command.envelope['payload']
        exact_fields = {
            'replacement_task_id',
            'replacement_task_revision',
            'supersession_scope',
            'continuing_consumers',
        }
        if set(payload) != exact_fields:
            return self._rejected(
                command,
                observed_version,
                'invalid_supersession_payload',
                'SupersedeTask payload fields are not exact; caller lineage is forbidden.',
            )
        replacement_id = payload['replacement_task_id']
        replacement_revision = payload['replacement_task_revision']
        scope = payload['supersession_scope']
        consumers = payload['continuing_consumers']
        if (
            not isinstance(replacement_id, str)
            or not isinstance(replacement_revision, int)
            or isinstance(replacement_revision, bool)
            or replacement_revision < 1
            or not isinstance(scope, list)
            or not scope
            or len(scope) != len(set(scope))
            or not all(isinstance(item, str) and item for item in scope)
            or not isinstance(consumers, list)
            or not consumers
            or len(consumers) != len(set(consumers))
            or not all(isinstance(item, str) and item for item in consumers)
        ):
            return self._rejected(
                command,
                observed_version,
                'invalid_supersession_payload',
                'SupersedeTask requires positive revisions and non-empty exact sets.',
            )

        current, edges = self._revision_graph(snapshot)
        source_id = command.target_stream_id
        source_revision = current.get(source_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                'source_revision_missing',
                'The source Task revision is absent from committed events.',
            )
        source = (source_id, source_revision)
        replacement = (replacement_id, replacement_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                'source_revision_terminal',
                'The source Task revision is already terminal.',
            )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                'supersession_cycle',
                'The proposed replacement reaches the source revision.',
            )

        source_object = self._task_revision_object(source_id, source_revision)
        replacement_object = self._task_revision_object(
            replacement_id,
            replacement_revision,
        )
        if source_object is None or replacement_object is None:
            return self._rejected(
                command,
                observed_version,
                'replacement_revision_missing',
                'The replacement must be an existing immutable Task revision.',
            )
        if source_object.get('task_type', 'task') != replacement_object.get(
            'task_type', 'task'
        ):
            return self._rejected(
                command,
                observed_version,
                'replacement_revision_incompatible',
                'The replacement Task revision is type-incompatible.',
            )
        if replacement_id == source_id:
            if replacement_revision <= source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    'replacement_revision_stale',
                    'A same-Task replacement must be a higher revision.',
                )
        elif current.get(replacement_id) != replacement_revision:
            return self._rejected(
                command,
                observed_version,
                'replacement_revision_stale',
                'The replacement is not the current Task revision.',
            )
        expected_consumers = source_object.get('continuing_consumers')
        if expected_consumers is not None and set(consumers) != set(expected_consumers):
            return self._rejected(
                command,
                observed_version,
                'continuing_consumers_mismatch',
                'Continuing consumers must equal the source revision contract.',
            )
        return {
            'source_task_id': source_id,
            'source_task_revision': source_revision,
            'replacement_task_id': replacement_id,
            'replacement_task_revision': replacement_revision,
            'supersession_scope': list(scope),
            'continuing_consumers': sorted(consumers),
            'actor_id': command.actor_id,
            'authority_grant_id': command.envelope['authority_grant_id'],
            'lineage': self._derived_lineage(edges, source, replacement),
        }
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

    def _build_event(
        self,
        command: Command,
        prepared_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
        elif command_type == 'SupersedeTask':
            if prepared_payload is None:
                raise IntegrityError('SupersedeTask requires prepared graph payload')
            event_type = 'TaskSuperseded'
            payload = prepared_payload
        elif command_type == 'VerifyEvidenceDeletion':
            authorizer = self.deletion_manifest_authorizer
            if authorizer is None:
                raise ArsError(
                    'VerifyEvidenceDeletion requires a trusted deletion '
                    'manifest authorizer'
                )
            payload = authorizer(
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
