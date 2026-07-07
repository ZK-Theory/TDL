"""Executors for the WP4.4 control/store fixture shard."""

from __future__ import annotations

from typing import Any


def execute_f001(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Single-slot overwrite: append-only store vs destructive dict store."""
    action = payload["action"]
    existing_owner = "T0.3"
    incoming = action["incoming_owner"]
    if subject == "known_bad":
        slots = {action["slot"]: existing_owner}
        slots[action["slot"]] = incoming
        return {
            "existing_owner": existing_owner,
            "destructive_overwrite": True,
            "surviving_ids": list(slots.values()),
        }
    slots: dict[str, list[str]] = {action["slot"]: [existing_owner]}
    slots[action["slot"]].append(incoming)
    survivors = slots[action["slot"]]
    return {
        "destructive_overwrite": False,
        "surviving_ids": survivors,
        "collision_visible": len(survivors) > 1,
    }


CONTROL_STORE_EXECUTORS = {
    "F-001": execute_f001,
}
