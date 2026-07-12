from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ControlPlaneState:
    active_attempt_ids: frozenset[str]
    task_states: dict[str, dict[str, Any]]


def reduce_task(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    event_type = event['event_type']
    if event_type == 'TaskCreated':
        if state:
            raise ValueError('TaskCreated requires empty stream')

        return {'task_id': event['stream_id'], 'status': 'draft', 'version': 1}
    if event_type == 'TaskSuperseded':
        terminal = {'accepted', 'rejected', 'partial', 'cancelled', 'superseded'}
        if not state or state.get('status') in terminal:
            raise ValueError('TaskSuperseded requires a nonterminal source revision')
        payload = event['payload']
        source_revision = int(payload['source_task_revision'])
        current_revision = int(state.get('current_revision', 1))
        if source_revision != current_revision:
            raise ValueError('TaskSuperseded source revision is not current')
        replacement = {
            'task_id': payload['replacement_task_id'],
            'revision': int(payload['replacement_task_revision']),
        }
        history = dict(state.get('revision_history', {}))
        history[str(source_revision)] = {
            'status': 'superseded',
            'replacement': replacement,
            'supersession_scope': list(payload['supersession_scope']),
            'continuing_consumers': list(payload['continuing_consumers']),
            'lineage': list(payload['lineage']),
        }
        if replacement['task_id'] == state['task_id']:
            history.setdefault(str(replacement['revision']), {'status': 'draft'})
            return {
                **state,
                'status': 'draft',
                'current_revision': replacement['revision'],
                'revision_history': history,
                'version': state['version'] + 1,
            }
        return {
            **state,
            'status': 'superseded',
            'current_revision': source_revision,
            'replacement': replacement,
            'supersession_scope': list(payload['supersession_scope']),
            'continuing_consumers': list(payload['continuing_consumers']),
            'lineage': list(payload['lineage']),
            'revision_history': history,
            'version': state['version'] + 1,
        }
    if event_type == 'ReadinessRequested' and state.get('status') == 'draft':
        return {
            **state,
            'status': 'readiness_pending',
            'version': state['version'] + 1,
        }
    raise ValueError(
        f'illegal task transition: {state.get("status")} -> {event_type}'
    )


def replay_control_plane(events: Iterable[dict[str, Any]]) -> ControlPlaneState:
    attempts: set[str] = set()
    tasks: dict[str, dict[str, Any]] = {}
    for event in events:
        if event['event_type'] in {'TaskCreated', 'TaskSuperseded'}:
            stream_id = event['stream_id']
            tasks[stream_id] = reduce_task(tasks.get(stream_id, {}), event)
        elif event['event_type'] == 'DispatchClaimed':
            attempts.add(event['payload']['attempt_id'])
        else:
            raise ValueError(f'unsupported event type: {event["event_type"]}')
    return ControlPlaneState(frozenset(attempts), tasks)
