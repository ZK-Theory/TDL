from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError
from research_system.ids import new_id, validate_id
from research_system.schema_registry import SchemaRegistry, bundled_schema_registry

_PROTECTED_FIELDS = frozenset(
    {
        'event_id',
        'project_id',
        'stream_version',
        'global_position',
        'transaction_id',
        'transaction_index',
        'transaction_count',
        'previous_event_hash',
        'event_hash',
        'recorded_at',
    }
)


@dataclass(frozen=True)
class LedgerSnapshot:
    """Materialized immutable ledger state used by one command transaction."""

    events: tuple[dict[str, Any], ...]
    global_position: int
    event_hash: str
    stream_versions: Mapping[str, int]
    fingerprint: tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class AllocatedEvent:
    """Ledger-owned identity and position exposed only to a draft finalizer."""

    event_id: str
    project_id: str
    stream_id: str
    stream_version: int
    global_position: int
    transaction_id: str
    transaction_index: int
    transaction_count: int
    recorded_at: str


@dataclass(frozen=True)
class EventDraft:
    """Internal typed event whose payload is finalized after allocation."""

    envelope: Mapping[str, Any]
    finalize_payload: Callable[[AllocatedEvent], Mapping[str, Any]]


class EventLedger:
    def __init__(
        self,
        control_root: Path,
        project_id: str,
        schemas: SchemaRegistry = bundled_schema_registry(),
    ) -> None:
        self.control_root = control_root
        self.project_id = validate_id(project_id, 'project')
        if not isinstance(schemas, SchemaRegistry):
            raise TypeError('EventLedger requires a trusted SchemaRegistry')
        self.schemas = schemas
        self.events_root = control_root / 'events' / project_id
        self.runtime_root = control_root / 'runtime'
        self.events_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._snapshot: LedgerSnapshot | None = None

    def snapshot(self) -> LedgerSnapshot:
        """Return a verified-state input, reloading only when ledger files change."""
        fingerprint = self._fingerprint()
        if self._snapshot is not None and self._snapshot.fingerprint == fingerprint:
            return self._snapshot
        events = tuple(self.iter_events())
        if self._fingerprint() != fingerprint:
            raise ConflictError('ledger changed while materializing snapshot')
        stream_versions: dict[str, int] = {}
        for event in events:
            stream_versions[event['stream_id']] = event['stream_version']
        self._snapshot = LedgerSnapshot(
            events=events,
            global_position=events[-1]['global_position'] if events else 0,
            event_hash=events[-1]['event_hash'] if events else '0' * 64,
            stream_versions=stream_versions,
            fingerprint=fingerprint,
        )
        return self._snapshot

    def append(
        self,
        proposed_events: Iterable[Mapping[str, Any] | EventDraft],
        *,
        snapshot: LedgerSnapshot | None = None,
    ) -> dict[str, Any]:
        """Atomically append a batch using a caller-verified materialized state."""
        proposed = list(proposed_events)
        if not proposed:
            raise ArsError('event batch must not be empty')
        current = self.snapshot() if snapshot is None else snapshot
        if self._fingerprint() != current.fingerprint:
            self._snapshot = None
            raise ConflictError('ledger changed since materialized snapshot')
        if self._persisted_tail() != (current.global_position, current.event_hash):
            self._snapshot = None
            raise ConflictError('persisted ledger tail differs from snapshot')
        next_position = current.global_position + 1
        previous_hash = current.event_hash
        stream_versions = dict(current.stream_versions)
        transaction_id = new_id('event_batch')
        recorded_at = datetime.now(UTC)
        count = len(proposed)
        events: list[dict[str, Any]] = []
        for offset, proposed_event in enumerate(proposed):
            draft = proposed_event if isinstance(proposed_event, EventDraft) else None
            candidate = dict(
                draft.envelope if draft is not None else proposed_event
            )
            protected = _PROTECTED_FIELDS.intersection(candidate)
            if protected:
                raise ArsError(f'caller supplied protected event fields: {sorted(protected)}')
            try:
                event_type = candidate.pop('event_type')
                stream_id = candidate.pop('stream_id')
            except KeyError as exc:
                raise ArsError(f'missing event field: {exc.args[0]}') from exc
            stream_version = stream_versions.get(stream_id, 0) + 1
            stream_versions[stream_id] = stream_version
            event_id = new_id('event')
            recorded_at_text = recorded_at.isoformat().replace('+00:00', 'Z')
            if draft is None and event_type == 'ReleaseGateDecisionPublished':
                raise ArsError('release publication requires a ledger event finalizer')
            if draft is not None and 'payload' in candidate:
                raise ArsError('event draft payload must be ledger-finalized')
            allocated = AllocatedEvent(
                event_id=event_id,
                project_id=self.project_id,
                stream_id=stream_id,
                stream_version=stream_version,
                global_position=next_position + offset,
                transaction_id=transaction_id,
                transaction_index=offset + 1,
                transaction_count=count,
                recorded_at=recorded_at_text,
            )
            payload = (
                dict(draft.finalize_payload(allocated))
                if draft is not None
                else candidate.pop('payload', {})
            )
            if draft is None:
                internal_key = (
                    f'ledger-internal:{transaction_id}:{offset + 1}'
                )
                candidate.setdefault(
                    'schema_id', f'ars://core/event/{event_type}'
                )
                candidate.setdefault('schema_version', '1.0.0')
                candidate.setdefault('command_id', new_id('command'))
                candidate.setdefault('command_type', 'LedgerInternalAppend')
                candidate.setdefault('idempotency_key', internal_key)
                candidate.setdefault(
                    'command_payload_hash', sha256_hex(canonical_bytes(payload))
                )
                candidate.setdefault('correlation_id', internal_key)
                candidate.setdefault('causation_id', None)
                candidate.setdefault('actor_id', new_id('actor'))
                candidate.setdefault('authority_grant_id', new_id('authority_grant'))
                candidate.setdefault('occurred_at', None)
            event = {
                'event_id': event_id,
                'event_type': event_type,
                'project_id': self.project_id,
                'stream_id': stream_id,
                'stream_version': stream_version,
                'global_position': next_position + offset,
                'transaction_id': transaction_id,
                'transaction_index': offset + 1,
                'transaction_count': count,
                'recorded_at': recorded_at_text,
                'payload': payload,
                **candidate,
                'previous_event_hash': previous_hash,
            }
            if draft is not None and event_type == 'ReleaseGateDecisionPublished':
                decision = payload.get('release_decision')
                if (
                    candidate.get('occurred_at') is not None
                    or not isinstance(decision, dict)
                    or decision.get('release_gate_decision_id') != stream_id
                    or decision.get('canonical_event_ref') != event_id
                ):
                    raise ArsError(
                        'release event finalizer violated ledger allocation'
                    )
            prehash = {**event, 'event_hash': '0' * 64}
            self.schemas.validate('ars://core/event', prehash)
            event_schema = f'ars://core/event/{event_type}'
            if self.schemas.contains(event_schema):
                self.schemas.validate(event_schema, prehash)
            event['event_hash'] = sha256_hex(canonical_bytes(event))
            self.schemas.validate('ars://core/event', event)
            if self.schemas.contains(event_schema):
                self.schemas.validate(event_schema, event)
            previous_hash = event['event_hash']
            events.append(event)
        date_root = self.events_root / f'{recorded_at.year:04d}' / f'{recorded_at.month:02d}'
        date_root.mkdir(parents=True, exist_ok=True)
        target = date_root / f'{next_position:020d}-{transaction_id}.jsonl'
        if target.exists():
            raise ConflictError(f'event batch already exists: {target}')
        temporary = self.runtime_root / f'{transaction_id}.jsonl.tmp'
        with temporary.open('xb') as handle:
            for event in events:
                handle.write(canonical_bytes(event) + b'\n')
            handle.flush()
            os.fsync(handle.fileno())
        self._after_batch_fsync(temporary)
        self._publish(temporary, target)
        self._after_publish(target)
        self._snapshot = LedgerSnapshot(
            events=current.events + tuple(events),
            global_position=events[-1]['global_position'],
            event_hash=events[-1]['event_hash'],
            stream_versions=stream_versions,
            fingerprint=self._fingerprint(),
        )
        return {
            'event_batch_id': transaction_id,
            'event_ids': [event['event_id'] for event in events],
            'global_positions': [event['global_position'] for event in events],
            'resulting_stream_versions': stream_versions,
        }

    def iter_events(self) -> Iterator[dict[str, Any]]:
        for batch in self.iter_batches():
            yield from batch

    def iter_batches(self) -> Iterator[tuple[dict[str, Any], ...]]:
        for path in self._batch_paths():
            with path.open(encoding='utf-8') as handle:
                yield tuple(json.loads(line) for line in handle if line.strip())

    def _batch_paths(self) -> list[Path]:
        paths = list(self.events_root.rglob('*.jsonl'))
        try:
            return sorted(
                paths,
                key=lambda path: int(path.name.partition('-')[0]),
            )
        except ValueError as exc:
            raise ConflictError('invalid event batch filename') from exc

    def _persisted_tail(self) -> tuple[int, str]:
        paths = self._batch_paths()
        if not paths:
            return 0, '0' * 64
        tail_path = max(
            paths,
            key=lambda path: int(path.name.partition('-')[0]),
        )
        lines = [
            line
            for line in tail_path.read_text(encoding='utf-8').splitlines()
            if line.strip()
        ]
        if not lines:
            raise ConflictError('persisted ledger tail batch is empty')
        tail = json.loads(lines[-1])
        return tail['global_position'], tail['event_hash']

    def _fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        records = []
        for path in sorted(self.events_root.rglob('*.jsonl')):
            stat = path.stat()
            records.append(
                (
                    path.relative_to(self.events_root).as_posix(),
                    stat.st_size,
                    stat.st_mtime_ns,
                )
            )
        return tuple(records)

    def _after_batch_fsync(self, temporary: Path) -> None:
        pass

    def _after_publish(self, target: Path) -> None:
        pass

    def _publish(self, source: Path, target: Path) -> None:
        os.replace(source, target)
