from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.errors import ArsError
from research_system.schema_registry import SchemaBinding, SchemaIdentity, SchemaRegistry
from research_system.store.ledger import EventLedger


PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"
EVENT_TYPE = "BoundEvent"
COMMAND_SCHEMA_ID = "ars://test/command/BoundCommand"
BOUND_EVENT_SCHEMA_ID = "ars://test/event/BoundEvent"
INACTIVE_EVENT_SCHEMA_ID = "ars://test/event/InactiveEvent"


def _write_schema(root: Path, name: str, schema_id: str) -> None:
    (root / name).write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": schema_id,
                "type": "object",
                "properties": {"schema_version": {"const": "1.0.0"}},
            }
        ),
        encoding="utf-8",
        newline="\n",
    )


def _runtime_ledger(tmp_path: Path) -> tuple[EventLedger, SchemaIdentity]:
    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    _write_schema(schema_root, "command.schema.json", COMMAND_SCHEMA_ID)
    _write_schema(schema_root, "bound-event.schema.json", BOUND_EVENT_SCHEMA_ID)
    _write_schema(schema_root, "inactive-event.schema.json", INACTIVE_EVENT_SCHEMA_ID)
    schemas = SchemaRegistry(
        schema_root,
        active_bindings=(
            SchemaBinding(COMMAND_SCHEMA_ID, "1.0.0", command_type="BoundCommand"),
            SchemaBinding(
                BOUND_EVENT_SCHEMA_ID,
                "1.0.0",
                event_type=EVENT_TYPE,
                producer_command_type="BoundCommand",
            ),
        ),
    )
    return (
        EventLedger(tmp_path / "control", project_id=PROJECT_ID, schemas=schemas),
        schemas.resolve_identity(COMMAND_SCHEMA_ID, "1.0.0"),
    )


def _event(
    command_identity: SchemaIdentity,
    *,
    schema_id: str,
    command_type: str | None = None,
) -> dict[str, object]:
    event = {
        "event_type": EVENT_TYPE,
        "stream_id": "evt_01978abc-0003-7000-8000-000000000003",
        "schema_id": schema_id,
        "schema_version": "1.0.0",
        "command_schema_id": command_identity.schema_id,
        "command_schema_version": command_identity.schema_version,
        "command_schema_sha256": command_identity.sha256,
        "payload": {},
    }
    if command_type is not None:
        event["command_type"] = command_type
    return event


def test_omitted_producer_reports_normalized_internal_producer_for_active_bound_event(tmp_path: Path) -> None:
    """remediation-red: defaulted producer selects the same diagnostic path as the persisted event."""

    ledger, command_identity = _runtime_ledger(tmp_path)

    with pytest.raises(ArsError, match="unbound event producer: BoundEvent from LedgerInternalAppend"):
        ledger.append([_event(command_identity, schema_id=BOUND_EVENT_SCHEMA_ID)])

    assert tuple(ledger.iter_batches()) == ()


def test_explicit_unbound_producer_remains_the_active_bound_event_diagnostic(tmp_path: Path) -> None:
    ledger, command_identity = _runtime_ledger(tmp_path)

    with pytest.raises(ArsError, match="unbound event producer: BoundEvent from WrongProducer"):
        ledger.append(
            [
                _event(
                    command_identity,
                    schema_id=BOUND_EVENT_SCHEMA_ID,
                    command_type="WrongProducer",
                )
            ]
        )

    assert tuple(ledger.iter_batches()) == ()


@pytest.mark.parametrize("command_type", [None, "WrongProducer"])
def test_inactive_event_schema_precedes_unbound_producer_for_omitted_and_explicit_producers(
    tmp_path: Path,
    command_type: str | None,
) -> None:
    ledger, command_identity = _runtime_ledger(tmp_path)

    with pytest.raises(ArsError, match=f"inactive event schema: {INACTIVE_EVENT_SCHEMA_ID} version 1.0.0"):
        ledger.append(
            [
                _event(
                    command_identity,
                    schema_id=INACTIVE_EVENT_SCHEMA_ID,
                    command_type=command_type,
                )
            ]
        )

    assert tuple(ledger.iter_batches()) == ()


def test_active_bound_event_continues_to_append_with_its_explicit_producer(tmp_path: Path) -> None:
    ledger, command_identity = _runtime_ledger(tmp_path)

    receipt = ledger.append(
        [
            _event(
                command_identity,
                schema_id=BOUND_EVENT_SCHEMA_ID,
                command_type="BoundCommand",
            )
        ]
    )

    events = tuple(ledger.iter_events())

    assert receipt["event_ids"] == [events[0]["event_id"]]
    assert events[0]["command_type"] == "BoundCommand"
    assert tuple(event["event_type"] for event in events) == (EVENT_TYPE,)
