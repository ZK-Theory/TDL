from datetime import UTC, datetime

import pytest

from research_system.context.registry import resolve_context_packet_for_consumer
from research_system.errors import ArsError, IntegrityError


class MappingObjects:
    def __init__(self, values: dict[tuple[str, int], dict]) -> None:
        self.values = values

    def read(self, kind: str, object_id: str, revision: int):
        assert kind == "context"
        return self.values[(object_id, revision)]


class UnusedSourceResolver:
    def resolve(self, source_ids: set[str]):
        raise AssertionError(f"source resolution should not be reached: {source_ids}")


def test_resolver_fails_closed_on_wrong_recipient_and_changed_currency() -> None:
    context_id = "ctx_01978abc-1000-7000-8000-000000001000"
    packet_hash = "1" * 64
    events = [
        {
            "event_type": name,
            "stream_id": context_id,
            "stream_version": index,
            "payload": payload,
        }
        for index, (name, payload) in enumerate(
            [
                (
                    "ContextPacketRequested",
                    {
                        "context_id": context_id,
                        "request_id": "req-1",
                        "purpose": "methods_brief",
                        "permitted_scopes": ["rm-03-export"],
                    },
                ),
                ("ContextCompilationStarted", {"context_id": context_id}),
                (
                    "ContextPacketCompiled",
                    {
                        "context_id": context_id,
                        "packet_object_id": "packet",
                        "packet_revision": 1,
                        "packet_sha256": packet_hash,
                        "manifest_object_id": "manifest",
                        "manifest_revision": 1,
                        "manifest_sha256": "2" * 64,
                    },
                ),
                ("ContextPacketValidated", {"context_id": context_id}),
                (
                    "ContextPacketIssued",
                    {
                        "context_id": context_id,
                        "packet_revision": 1,
                        "packet_sha256": packet_hash,
                    },
                ),
                (
                    "ContextPacketDelivered",
                    {
                        "context_id": context_id,
                        "packet_sha256": packet_hash,
                        "recipient_id": "consumer-1",
                    },
                ),
            ],
            start=1,
        )
    ]
    with pytest.raises(ArsError, match="recipient"):
        resolve_context_packet_for_consumer(
            events,
            MappingObjects({}),
            context_id=context_id,
            revision=1,
            packet_sha256=packet_hash,
            consumer_id="consumer-2",
            purpose="methods_brief",
            scope="rm-03-export",
            evaluation_time=datetime.now(UTC),
            control_store_identity="store-1",
            source_position=1,
            source_hash="3" * 64,
            source_resolver=UnusedSourceResolver(),
        )


def test_resolver_rejects_reordered_lifecycle_before_object_read() -> None:
    context_id = "ctx_01978abc-1000-7000-8000-000000001000"
    events = [
        {
            "event_type": "ContextPacketRequested",
            "stream_id": context_id,
            "stream_version": 1,
            "payload": {"context_id": context_id},
        },
        {
            "event_type": "ContextPacketIssued",
            "stream_id": context_id,
            "stream_version": 2,
            "payload": {"context_id": context_id},
        },
    ]
    with pytest.raises(IntegrityError, match="transition"):
        resolve_context_packet_for_consumer(
            events,
            MappingObjects({}),
            context_id=context_id,
            revision=1,
            packet_sha256="1" * 64,
            consumer_id="consumer-1",
            purpose="methods_brief",
            scope="rm-03-export",
            evaluation_time=datetime.now(UTC),
            control_store_identity="store-1",
            source_position=1,
            source_hash="3" * 64,
            source_resolver=UnusedSourceResolver(),
        )
