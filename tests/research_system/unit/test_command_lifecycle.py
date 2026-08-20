from __future__ import annotations

import pytest

from research_system.command.lifecycle import validate_exact_lifecycle_envelope


@pytest.mark.parametrize(
    ("event_type", "schema_id", "command_type"),
    [
        ("AttemptCompleted", "ars://core/event/AttemptCompleted", "RecordSpikeVerdict"),
        ("PartialOutcomeRecorded", "ars://core/event/PartialOutcomeRecorded", "RecordSpikeVerdict"),
        ("LeaseReleased", "ars://core/event/LeaseReleased", "RecordSpikeVerdict"),
        ("PartialOutcomeRecorded", "ars://core/event/PartialOutcomeRecorded", "CancelDiscoveryEvaluation"),
        ("LeaseReleased", "ars://core/event/LeaseReleased", "CancelDiscoveryEvaluation"),
    ],
)
def test_discovery_operational_events_are_exact_producer_events(
    event_type: str, schema_id: str, command_type: str
) -> None:
    event = {
        "event_type": event_type,
        "schema_id": schema_id,
        "schema_version": "1.0.0",
        "command_type": command_type,
        "command_schema_id": "ars://core/command",
        "command_schema_version": "1.0.0",
        "command_payload_hash": "f" * 64,
        "payload": {},
    }

    assert validate_exact_lifecycle_envelope(event) == command_type
