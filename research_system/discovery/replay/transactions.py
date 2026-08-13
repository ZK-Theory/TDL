"""Shared exact-transaction predicates for Discovery replay."""

from __future__ import annotations

from collections.abc import Mapping

from research_system.discovery.replay.scope import EventScope


def transaction_side(scope: EventScope, *, following: bool) -> list[dict[str, object]]:
    """Return the ordered events on one side of the current transaction member."""

    boundary = scope.event.get("transaction_index", 0)
    return [
        event
        for event in scope.transaction_events.get(scope.event.get("transaction_id"), ())
        if (event.get("transaction_index", 0) > boundary) == following and event.get("transaction_index", 0) != boundary
    ]


def decision_event_precedes(scope: EventScope, event_type: str, decision_id: object) -> bool:
    """Bind a lifecycle transition to one exact preceding Decision event."""

    matches = [event for event in transaction_side(scope, following=False) if event.get("event_type") == event_type]
    key = "new_decision_id" if event_type == "DecisionProposed" else "decision_id"
    if len(matches) != 1 or matches[0].get("stream_id") != decision_id:
        return False
    payload = matches[0].get("payload")
    return isinstance(payload, Mapping) and payload.get(key) == decision_id
