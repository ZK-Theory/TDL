"""Append-only SPEC source corrections bound to exact causal ledger evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping, Protocol

from research_system.errors import ConfigurationError, IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry


class LedgerPrefixReader(Protocol):
    def snapshot(self) -> Any: ...

    def raw_prefix_sha256(self, global_position: int) -> str: ...


_REF_FIELDS = {
    "artefact_id",
    "content_sha256",
    "registration_event_id",
    "registration_event_hash",
    "registration_global_position",
}


def _registration_event_for_ref(
    reference: Mapping[str, object],
    *,
    events: tuple[dict[str, Any], ...],
    prefix_position: int,
) -> dict[str, Any]:
    if set(reference) != _REF_FIELDS:
        raise IntegrityError("source correction artefact reference is not exact")
    position = reference.get("registration_global_position")
    if type(position) is not int or position < 1 or position > prefix_position or position > len(events):
        raise IntegrityError("source correction artefact position is outside the causal prefix")
    event = events[position - 1]
    payload = event.get("payload")
    manifest = payload.get("manifest") if isinstance(payload, Mapping) else None
    if (
        event.get("global_position") != position
        or event.get("event_type") != "ArtefactRegistered"
        or event.get("stream_id") != reference.get("artefact_id")
        or event.get("event_id") != reference.get("registration_event_id")
        or event.get("event_hash") != reference.get("registration_event_hash")
        or not isinstance(manifest, Mapping)
        or manifest.get("artefact_id") != reference.get("artefact_id")
        or manifest.get("content_sha256") != reference.get("content_sha256")
    ):
        raise IntegrityError("source correction artefact does not match its registration event")
    return event


def validate_spec_source_correction(
    value: object,
    *,
    ledger: LedgerPrefixReader,
    schemas: SchemaRegistry,
) -> dict[str, object]:
    """Validate a v2 correction against its immutable evidence and raw prefix."""

    if not isinstance(value, dict):
        raise IntegrityError("SPEC source correction must be an object")
    try:
        schemas.validate(
            "ars://portfolio/spec-01-source-correction",
            value,
            schema_version="2.0.0",
        )
    except SchemaError as exc:
        raise IntegrityError("SPEC source correction schema is invalid") from exc
    snapshot = ledger.snapshot()
    events = getattr(snapshot, "events", None)
    prefix = value.get("causal_ledger_prefix")
    if not isinstance(events, tuple) or not isinstance(prefix, Mapping):
        raise IntegrityError("SPEC source correction ledger evidence is unavailable")
    position = prefix.get("global_position")
    if type(position) is not int or position < 1 or position > len(events):
        raise IntegrityError("SPEC source correction causal prefix is invalid")
    tail = events[position - 1]
    if (
        tail.get("global_position") != position
        or prefix.get("event_hash") != tail.get("event_hash")
        or prefix.get("raw_prefix_sha256") != ledger.raw_prefix_sha256(position)
    ):
        raise IntegrityError("SPEC source correction causal prefix does not match persisted bytes")
    corrected = value.get("corrected_source_observation_ref")
    amended = value.get("amended_evidence_refs")
    if not isinstance(corrected, Mapping) or not isinstance(amended, list):
        raise IntegrityError("SPEC source correction references are invalid")
    source_event = _registration_event_for_ref(corrected, events=events, prefix_position=position)
    source_manifest = source_event["payload"]["manifest"]
    if (
        source_manifest.get("artefact_type") != "spec_source_observation"
        or source_manifest.get("artefact_schema_id") != "ars://portfolio/spec-source-observation"
        or source_manifest.get("artefact_schema_version") != "1.0.0"
    ):
        raise IntegrityError("SPEC source correction does not bind a source observation")
    seen: set[tuple[object, object]] = set()
    for reference in amended:
        if not isinstance(reference, Mapping):
            raise IntegrityError("SPEC source correction amended evidence reference is invalid")
        _registration_event_for_ref(reference, events=events, prefix_position=position)
        identity = (reference.get("artefact_id"), reference.get("registration_event_id"))
        if identity in seen:
            raise IntegrityError("SPEC source correction repeats amended evidence")
        seen.add(identity)
    return deepcopy(value)


def prepare_spec_source_correction(
    *,
    route_id: str,
    correction_id: str,
    recorded_at: str,
    producer_actor_id: str,
    producer_session_id: str,
    amended_evidence_refs: tuple[Mapping[str, object], ...],
    corrected_source_observation_ref: Mapping[str, object],
    incorrect_assertions: tuple[str, ...],
    withdrawn_conditions: tuple[str, ...],
    preserved_findings: tuple[str, ...],
    scientific_disposition: str,
    ledger: LedgerPrefixReader,
    schemas: SchemaRegistry,
) -> dict[str, object]:
    """Prepare a new correction without rewriting any earlier evidence."""

    if not isinstance(recorded_at, str) or not recorded_at.endswith("Z"):
        raise ConfigurationError("source correction time must be UTC")
    try:
        datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError("source correction time is invalid") from exc
    snapshot = ledger.snapshot()
    if snapshot.global_position < 1:
        raise IntegrityError("source correction requires a non-empty causal ledger prefix")
    value: dict[str, object] = {
        "schema_id": "ars://portfolio/spec-01-source-correction",
        "schema_version": "2.0.0",
        "document_type": "spec_01_source_correction",
        "route_id": route_id,
        "correction_id": correction_id,
        "recorded_at": recorded_at,
        "producer": {
            "actor_id": producer_actor_id,
            "session_id": producer_session_id,
            "role": "source-correction producer",
        },
        "amended_evidence_refs": [deepcopy(dict(item)) for item in amended_evidence_refs],
        "corrected_source_observation_ref": deepcopy(dict(corrected_source_observation_ref)),
        "causal_ledger_prefix": {
            "global_position": snapshot.global_position,
            "event_hash": snapshot.event_hash,
            "raw_prefix_sha256": ledger.raw_prefix_sha256(snapshot.global_position),
        },
        "incorrect_assertions": list(incorrect_assertions),
        "correction_effect": {
            "withdrawn_conditions": list(withdrawn_conditions),
            "preserved_findings": list(preserved_findings),
        },
        "scientific_disposition": scientific_disposition,
    }
    return validate_spec_source_correction(value, ledger=ledger, schemas=schemas)


__all__ = [
    "LedgerPrefixReader",
    "prepare_spec_source_correction",
    "validate_spec_source_correction",
]
