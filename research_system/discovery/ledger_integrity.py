"""Durable Discovery ledger integrity.

Owns the two checks that must pass before any event is interpreted as a
lifecycle transition: the complete ordered hash chain, and the exact common,
schema, project, stream and transaction envelope of every persisted event.

This is a leaf module: it validates persisted bytes and knows nothing about
Candidate, Assay, Spike, dossier or authority semantics.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.routes import DISCOVERY_AUTHORITY_SHADOWS, DISCOVERY_ROW_ROUTES
from research_system.errors import IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry


def _validate_hash_chain(events: tuple[dict[str, Any], ...]) -> None:
    """Validate the complete ordered Discovery event hash chain."""
    last_position = 0
    last_hash = "0" * 64
    for event in events:
        if event.get("global_position") != last_position + 1 or event.get("previous_event_hash") != last_hash:
            raise IntegrityError("Discovery event chain mismatch")
        unsigned = dict(event)
        recorded = unsigned.pop("event_hash", None)
        if recorded != sha256_hex(canonical_bytes(unsigned)):
            raise IntegrityError("Discovery event hash mismatch")
        last_position = event["global_position"]
        last_hash = event["event_hash"]


def _validate_persisted_event_envelopes(
    events: tuple[dict[str, Any], ...],
    schemas: SchemaRegistry,
) -> None:
    """Validate the exact common, schema, project, stream, and transaction envelope."""

    project_id: Any = None
    stream_versions: dict[Any, int] = {}
    closed_transactions: set[Any] = set()
    current_transaction: Any = None
    transaction_count = 0
    transaction_seen = 0
    transaction_zero_based = False
    transaction_provenance: dict[str, Any] = {}
    provenance_fields = (
        "project_id",
        "command_id",
        "command_type",
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
        "idempotency_key",
        "command_payload_hash",
        "correlation_id",
        "causation_id",
        "actor_id",
        "authority_grant_id",
        "occurred_at",
    )
    for event in events:
        position = event.get("global_position")
        event_type = str(event.get("event_type", ""))
        command_type = str(event.get("command_type", ""))
        recorded_schema = str(event.get("schema_id", ""))
        recorded_version = str(event.get("schema_version", ""))
        shadow_payload = event.get("payload")
        is_authority_shadow = bool(
            isinstance(shadow_payload, Mapping)
            and set(shadow_payload) == {"owner_row_id", "authority_kind", "authority_event_type", "authority_payload"}
            and shadow_payload.get("authority_event_type") == event_type
            and isinstance(shadow_payload.get("authority_payload"), Mapping)
        )
        try:
            if is_authority_shadow:
                owner_row_id = shadow_payload.get("owner_row_id")
                route = DISCOVERY_ROW_ROUTES.get(owner_row_id)
                if (
                    route is None
                    or route.command_type != command_type
                    or DISCOVERY_AUTHORITY_SHADOWS.get(owner_row_id)
                    != (shadow_payload.get("authority_kind"), event_type)
                ):
                    raise IntegrityError("authority shadow producer mismatch")
            command_binding = schemas.command_binding(command_type)
            if command_binding is None or (
                event.get("command_schema_id"),
                event.get("command_schema_version"),
            ) != (command_binding.schema_id, command_binding.schema_version):
                raise SchemaError("active command binding mismatch")
            schemas.resolve_identity(
                str(event.get("command_schema_id", "")),
                str(event.get("command_schema_version", "")),
                expected_sha256=str(event.get("command_schema_sha256", "")),
            )
            event_binding = None if is_authority_shadow else schemas.event_binding(event_type, command_type)
            if event_binding is not None:
                if (recorded_schema, recorded_version) != (
                    event_binding.schema_id,
                    event_binding.schema_version,
                ):
                    raise SchemaError("active event binding mismatch")
                schemas.validate_active(
                    event_binding.schema_id,
                    event,
                    schema_version=event_binding.schema_version,
                )
            elif is_authority_shadow:
                if recorded_schema != "ars://core/event" or recorded_version != "1.0.0":
                    raise SchemaError("generic event schema mismatch")
                schemas.validate("ars://core/event", event, schema_version="1.0.0")
            elif schemas.has_producer_bindings(event_type):
                raise SchemaError("unbound event producer")
            elif recorded_schema == "ars://core/event":
                if recorded_version != "1.0.0":
                    raise SchemaError("generic event schema mismatch")
                schemas.validate("ars://core/event", event, schema_version="1.0.0")
            elif schemas.contains(recorded_schema):
                schemas.validate(recorded_schema, event, schema_version=recorded_version)
            else:
                raise SchemaError("unknown event schema")
        except SchemaError as exc:
            raise IntegrityError(f"Discovery persisted schema provenance mismatch at {position}") from exc

        event_project_id = event.get("project_id")
        if project_id is None:
            project_id = event_project_id
        elif event_project_id != project_id:
            raise IntegrityError("Discovery persisted project identity mismatch")

        stream_id = event.get("stream_id")
        expected_stream_version = stream_versions.get(stream_id, 0) + 1
        if event.get("stream_version") != expected_stream_version:
            raise IntegrityError("Discovery persisted stream version mismatch")
        stream_versions[stream_id] = expected_stream_version

        transaction_id = event.get("transaction_id")
        t2_event = recorded_schema.startswith("ars://wp6-2/t2/event/")
        if transaction_id != current_transaction:
            if current_transaction is not None:
                if transaction_seen != transaction_count:
                    raise IntegrityError("incomplete Discovery persisted transaction")
                closed_transactions.add(current_transaction)
            if transaction_id in closed_transactions:
                raise IntegrityError("non-contiguous Discovery persisted transaction")
            current_transaction = transaction_id
            transaction_count = event.get("transaction_count")
            transaction_seen = 0
            transaction_zero_based = t2_event
            transaction_provenance = {field: event.get(field) for field in provenance_fields}
        if (
            type(transaction_count) is not int
            or transaction_count < 1
            or event.get("transaction_count") != transaction_count
            or t2_event != transaction_zero_based
            or any(event.get(field) != value for field, value in transaction_provenance.items())
        ):
            raise IntegrityError("Discovery persisted transaction provenance mismatch")
        expected_index = transaction_seen if transaction_zero_based else transaction_seen + 1
        if event.get("transaction_index") != expected_index:
            raise IntegrityError("Discovery persisted transaction index mismatch")
        transaction_seen += 1
        if transaction_seen > transaction_count:
            raise IntegrityError("Discovery persisted transaction count mismatch")
    if current_transaction is not None and transaction_seen != transaction_count:
        raise IntegrityError("incomplete Discovery persisted transaction")


@lru_cache(maxsize=1)
def _default_replay_schemas() -> SchemaRegistry:
    """Load exact bundled schemas for public standalone replay."""

    return runtime_schema_registry(Path(__file__).resolve().parents[2] / ".research-system" / "schemas")
