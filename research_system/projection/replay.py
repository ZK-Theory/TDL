from __future__ import annotations

import os
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import reduce_task
from research_system.errors import IntegrityError

_ALLOWED_DISPOSITIONS = frozenset(
    {
        'accepted',
        'partial_accepted',
        'deferred',
        'superseded',
        'removed_by_amendment',
        'cancelled',
        'rejected',
    }
)


def _validate_scope_completion(payload: dict[str, Any]) -> None:
    reference = payload.get('scope_definition_ref')
    if (
        not isinstance(reference, dict)
        or not reference.get('object_id')
        or not isinstance(reference.get('revision'), int)
        or reference['revision'] < 1
    ):
        raise IntegrityError('scope completion requires an exact definition revision')
    required = payload.get('required_member_ids')
    dispositions = payload.get('member_dispositions')
    if not isinstance(required, list) or len(required) != len(set(required)):
        raise IntegrityError('scope completion has invalid required members')
    if not isinstance(dispositions, dict):
        raise IntegrityError('scope completion requires member dispositions')
    missing = sorted(set(required).difference(dispositions))
    if missing:
        raise IntegrityError(f'missing dispositions: {", ".join(missing)}')
    extra = sorted(set(dispositions).difference(required))
    if extra:
        raise IntegrityError(f'unexpected dispositions: {", ".join(extra)}')
    invalid = sorted(
        member
        for member, disposition in dispositions.items()
        if disposition not in _ALLOWED_DISPOSITIONS
    )
    if invalid:
        raise IntegrityError(f'invalid dispositions: {", ".join(invalid)}')


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(state)
    streams = updated.setdefault('streams', {})
    stream_id = event['stream_id']
    event_type = event['event_type']
    if event_type == 'TaskCreated':
        streams[stream_id] = reduce_task(streams.get(stream_id, {}), event)
    elif event_type == 'DispatchClaimed':
        current = streams.get(
            stream_id,
            {
                'dispatch_id': stream_id,
                'status': 'unclaimed',
                'active_attempt_ids': [],
                'version': 0,
            },
        )
        if current['status'] != 'unclaimed':
            raise IntegrityError('dispatch already has an active attempt')
        streams[stream_id] = {
            **current,
            'status': 'claimed',
            'active_attempt_ids': [event['payload']['attempt_id']],
            'version': current['version'] + 1,
        }
    elif event_type == 'ScopeCompleted':
        _validate_scope_completion(event['payload'])
        streams[stream_id] = {
            'scope_id': stream_id,
            'status': 'completed',
            'scope_definition_ref': event['payload']['scope_definition_ref'],
            'member_dispositions': dict(event['payload']['member_dispositions']),
            'version': event['stream_version'],
        }
    else:
        raise IntegrityError(f'unsupported event type: {event_type}')
    return updated


def _major(event: dict[str, Any]) -> int:
    try:
        return int(str(event['schema_version']).split('.', maxsplit=1)[0])
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError('invalid event schema version') from exc


def _verify_event_hash(event: dict[str, Any]) -> bool:
    unsigned = dict(event)
    recorded = unsigned.pop('event_hash', None)
    return recorded == sha256_hex(canonical_bytes(unsigned))


def replay(
    events: Iterable[dict[str, Any]],
    supported_major: int = 1,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        'streams': {},
        'last_position': 0,
        'last_hash': '0' * 64,
        'project_id': None,
    }
    stream_versions: dict[str, int] = {}
    transaction_id: str | None = None
    transaction_count = 0
    transaction_index = 0
    for source in events:
        event = deepcopy(source)
        position = event.get('global_position')
        if _major(event) != supported_major:
            raise IntegrityError(f'unsupported major at {position}')
        schema_id = event.get('schema_id')
        if not isinstance(schema_id, str) or not schema_id.startswith(
            'ars://core/event/'
        ):
            raise IntegrityError(f'unknown event schema at {position}')
        if position != state['last_position'] + 1:
            raise IntegrityError('event position gap or overlap')
        if event.get('previous_event_hash') != state['last_hash']:
            raise IntegrityError('event hash-chain mismatch')
        if not _verify_event_hash(event):
            raise IntegrityError(f'event hash mismatch at {position}')
        project_id = event.get('project_id')
        if state['project_id'] is None:
            state['project_id'] = project_id
        elif project_id != state['project_id']:
            raise IntegrityError('event project identity mismatch')
        stream_id = event.get('stream_id')
        expected_stream_version = stream_versions.get(stream_id, 0) + 1
        if event.get('stream_version') != expected_stream_version:
            raise IntegrityError('stream version gap or overlap')
        stream_versions[stream_id] = expected_stream_version
        current_transaction = event.get('transaction_id')
        if current_transaction != transaction_id:
            if transaction_id is not None and transaction_index != transaction_count:
                raise IntegrityError('incomplete event transaction')
            transaction_id = current_transaction
            transaction_count = event.get('transaction_count')
            transaction_index = 0
        if event.get('transaction_count') != transaction_count:
            raise IntegrityError('event transaction count mismatch')
        transaction_index += 1
        if event.get('transaction_index') != transaction_index:
            raise IntegrityError('event transaction index gap or overlap')
        state = apply_event(state, event)
        state['last_position'] = position
        state['last_hash'] = event['event_hash']
    if transaction_id is not None and transaction_index != transaction_count:
        raise IntegrityError('incomplete event transaction')
    return state


def rebuild_projection(
    events: Iterable[dict[str, Any]],
    output: Path,
) -> dict[str, Any]:
    state = replay(events)
    data = canonical_bytes(state) + b'\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f'.{output.name}.tmp')
    with temporary.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    return state
