"""Immutable recovery intent for multi-effect SPEC document actions."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.path_safety import read_contained_regular_file
from research_system.errors import IntegrityError


ROUTE_ID = "SPEC-GATE6-RUN-V1"
DOCUMENT_ACTIONS = (
    "prepare_spec_01",
    "return_spec_01_complete",
    "return_spec_01_partial",
    "correct_spec_01_source",
    "approve_spec_02",
    "prepare_spec_02",
    "return_spec_02_complete",
    "return_spec_02_partial",
)
PACKET_FIELDS = frozenset(
    {"schema_id", "schema_version", "route_id", "action", "retry_id", "commands", "document", "registration"}
)
JOURNAL_DIRECTORY = Path("runtime/spec-flow-preparations")


def preparation_value(action: str, packet: Mapping[str, Any]) -> dict[str, Any]:
    """Return the one canonical preparation journal value for an exact packet."""

    return {
        "schema_id": "ars://internal/spec-flow-action-preparation",
        "schema_version": "1.0.0",
        "route_id": ROUTE_ID,
        "action": action,
        "packet": deepcopy(dict(packet)),
    }


def read_preparation(control_root: Path, action: str) -> dict[str, Any] | None:
    """Read and fully validate one action preparation without treating it as completion."""

    relative = (JOURNAL_DIRECTORY / f"{action}.json").as_posix()
    target = control_root / relative
    if not target.exists() and not target.is_symlink():
        return None
    try:
        raw = read_contained_regular_file(control_root, relative, label="SPEC action preparation journal")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("SPEC action preparation journal is unavailable") from exc
    packet = value.get("packet") if isinstance(value, Mapping) else None
    if not isinstance(packet, dict):
        raise IntegrityError("SPEC action preparation journal is invalid")
    retry_preimage = {key: deepcopy(item) for key, item in packet.items() if key != "retry_id"}
    expected_retry_id = f"spec-flow:{action}:{sha256_hex(canonical_bytes(retry_preimage))}"
    if (
        not isinstance(value, dict)
        or raw != canonical_bytes(value)
        or value != preparation_value(action, packet)
        or set(packet) != PACKET_FIELDS
        or packet.get("schema_id") != "ars://portfolio/spec-flow-action"
        or packet.get("schema_version") != "1.0.0"
        or packet.get("route_id") != ROUTE_ID
        or packet.get("action") != action
        or packet.get("retry_id") != expected_retry_id
        or not isinstance(packet.get("commands"), list)
    ):
        raise IntegrityError("SPEC action preparation journal is invalid")
    return value


def pending_preparation(
    control_root: Path,
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Resolve at most one prepared document action without a sealed completion event."""

    completed = {
        event["payload"].get("action")
        for event in events
        if event.get("event_type") == "SpecFlowActionCompleted" and isinstance(event.get("payload"), Mapping)
    }
    pending = [
        value
        for action in DOCUMENT_ACTIONS
        for value in (read_preparation(control_root, action),)
        if value is not None and action not in completed
    ]
    if len(pending) > 1:
        raise IntegrityError("multiple SPEC document actions are awaiting exact recovery")
    return pending[0] if pending else None


__all__ = [
    "DOCUMENT_ACTIONS",
    "JOURNAL_DIRECTORY",
    "PACKET_FIELDS",
    "pending_preparation",
    "preparation_value",
    "read_preparation",
]
