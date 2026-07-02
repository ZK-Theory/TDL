from __future__ import annotations

import json
import os
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError
from research_system.ids import new_id, validate_id

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


class EventLedger:
    def __init__(self, control_root: Path, project_id: str):
        self.control_root = control_root
        self.project_id = validate_id(project_id, 'project')
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
        proposed_events: Iterable[Mapping[str, Any]],
        *,
        snapshot: LedgerSnapshot | None = None,
    ) -> dict[str, Any]:
        """Atomically append a batch using a caller-verified materialized state."""
        proposed = [dict(event) for event in proposed_events]
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
        for offset, candidate in enumerate(proposed):
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
            event = {
                'event_id': new_id('event'),
                'event_type': event_type,
                'project_id': self.project_id,
                'stream_id': stream_id,
                'stream_version': stream_version,
                'global_position': next_position + offset,
                'transaction_id': transaction_id,
                'transaction_index': offset + 1,
                'transaction_count': count,
                'recorded_at': recorded_at.isoformat().replace('+00:00', 'Z'),
                'payload': candidate.pop('payload', {}),
                **candidate,
                'previous_event_hash': previous_hash,
            }
            event['event_hash'] = sha256_hex(canonical_bytes(event))
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
        for path in sorted(self.events_root.rglob('*.jsonl')):
            with path.open(encoding='utf-8') as handle:
                for line in handle:
                    if line.strip():
                        yield json.loads(line)

    def iter_batches(self) -> Iterator[tuple[dict[str, Any], ...]]:
        for path in sorted(self.events_root.rglob('*.jsonl')):
            with path.open(encoding='utf-8') as handle:
                yield tuple(json.loads(line) for line in handle if line.strip())

    def _persisted_tail(self) -> tuple[int, str]:
        paths = sorted(self.events_root.rglob('*.jsonl'))
        if not paths:
            return 0, '0' * 64
        lines = [
            line
            for line in paths[-1].read_text(encoding='utf-8').splitlines()
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
