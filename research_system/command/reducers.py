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
    if event_type == 'ReadinessRequested' and state['status'] == 'draft':
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
        if event['event_type'] == 'TaskCreated':
            stream_id = event['stream_id']
            tasks[stream_id] = reduce_task(tasks.get(stream_id, {}), event)
        elif event['event_type'] == 'DispatchClaimed':
            attempts.add(event['payload']['attempt_id'])
        else:
            raise ValueError(f'unsupported event type: {event["event_type"]}')
    return ControlPlaneState(frozenset(attempts), tasks)
