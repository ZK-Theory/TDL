"""Ledger-derived W3 context packet state and exact consumer resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.sources import SourceResolver, resolve_sources
from research_system.errors import ArsError, IntegrityError


_EVENT_STATE = {
    "ContextPacketRequested": "requested",
    "ContextCompilationStarted": "compiling",
    "ContextPacketCompiled": "compiled",
    "ContextPacketValidated": "validated",
    "ContextPacketIssued": "issued",
    "ContextPacketDelivered": "delivered",
    "ContextPacketFailed": "failed",
    "ContextPacketExpired": "expired",
    "ContextPacketSuperseded": "superseded",
}

_ALLOWED_TRANSITIONS = {
    None: frozenset({"requested"}),
    "requested": frozenset({"compiling", "failed"}),
    "compiling": frozenset({"compiled", "failed"}),
    "compiled": frozenset({"validated", "failed"}),
    "validated": frozenset({"issued"}),
    "issued": frozenset({"delivered", "expired", "superseded"}),
    "delivered": frozenset({"expired", "superseded"}),
    "failed": frozenset(),
    "expired": frozenset(),
    "superseded": frozenset(),
}


class ContextObjectReader(Protocol):
    """Read one verified immutable object revision."""

    def read(self, kind: str, object_id: str, revision: int) -> Any: ...


@dataclass(frozen=True, slots=True)
class ContextLifecycleState:
    context_id: str
    state: str
    stream_version: int
    request: Mapping[str, Any]
    compilation: Mapping[str, Any] | None = None
    validation: Mapping[str, Any] | None = None
    issuance: Mapping[str, Any] | None = None
    delivery: Mapping[str, Any] | None = None
    terminal: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ResolvedContextPacket:
    context_id: str
    revision: int
    packet_sha256: str
    packet: Mapping[str, Any]
    manifest: Mapping[str, Any]
    delivery: Mapping[str, Any]


_OWNER_EVENT_ORDER = (
    "OwnerOperatedContextHandoffPrepared",
    "OwnerOperatedContextHandoffValidated",
    "OwnerOperatedContextHandoffIssued",
    "OwnerOperatedContextDelivered",
)


def rebuild_owner_operated_handoff(
    events: Iterable[Mapping[str, Any]], context_id: str
) -> tuple[Mapping[str, Any], ...] | None:
    selected = sorted(
        (
            event
            for event in events
            if event.get("stream_id") == context_id and event.get("event_type") in _OWNER_EVENT_ORDER
        ),
        key=lambda event: int(event.get("stream_version", 0)),
    )
    if not selected:
        return None
    if tuple(event.get("event_type") for event in selected) != _OWNER_EVENT_ORDER:
        raise IntegrityError("owner-operated context handoff lifecycle is incomplete or reordered")
    versions = tuple(int(event.get("stream_version", 0)) for event in selected)
    if versions != tuple(range(versions[0], versions[0] + 4)):
        raise IntegrityError("owner-operated context handoff stream is not contiguous")
    payloads = tuple(_payload(event) for event in selected)
    binding_fields = (
        "context_id",
        "request_id",
        "packet_revision",
        "packet_sha256",
        "manifest_sha256",
        "owner_profile_sha256",
    )
    if any(payload.get("context_id") != context_id for payload in payloads) or any(
        payload.get(field) != payloads[0].get(field) for payload in payloads[1:] for field in binding_fields
    ):
        raise IntegrityError("owner-operated context handoff identity changed")
    profile = payloads[0].get("owner_profile")
    delivery = payloads[-1]
    if not isinstance(profile, Mapping) or delivery.get("recipient_session_id") != profile.get("operator_session_id"):
        raise ArsError("owner-operated delivery does not bind the prepared operator session")
    if delivery.get("recipient_id") != profile.get("recipient_id"):
        raise ArsError("owner-operated delivery does not bind the prepared recipient")
    return payloads


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise IntegrityError("context lifecycle event payload is missing")
    return payload


def rebuild_context_lifecycle(events: Iterable[Mapping[str, Any]], context_id: str) -> ContextLifecycleState:
    """Reduce one context stream and reject gaps, reorderings, and mixed identities."""
    selected = [
        event for event in events if event.get("stream_id") == context_id and event.get("event_type") in _EVENT_STATE
    ]
    selected.sort(key=lambda event: int(event.get("stream_version", 0)))
    if not selected:
        raise ArsError("context packet was never requested")

    current: str | None = None
    request: Mapping[str, Any] | None = None
    compilation = validation = issuance = delivery = terminal = None
    for index, event in enumerate(selected, start=1):
        if event.get("stream_version") != index:
            raise IntegrityError("context lifecycle stream version is not contiguous")
        payload = _payload(event)
        if payload.get("context_id") != context_id:
            raise IntegrityError("context lifecycle event has a cross-packet identity")
        next_state = _EVENT_STATE[str(event["event_type"])]
        if next_state not in _ALLOWED_TRANSITIONS[current]:
            raise IntegrityError(f"invalid context lifecycle transition: {current!r} -> {next_state!r}")
        current = next_state
        if next_state == "requested":
            request = payload
        elif next_state == "compiled":
            compilation = payload
        elif next_state == "validated":
            validation = payload
        elif next_state == "issued":
            issuance = payload
        elif next_state == "delivered":
            delivery = payload
        elif next_state in {"failed", "expired", "superseded"}:
            terminal = payload

    if request is None or current is None:
        raise IntegrityError("context lifecycle is missing its request")
    return ContextLifecycleState(
        context_id=context_id,
        state=current,
        stream_version=len(selected),
        request=request,
        compilation=compilation,
        validation=validation,
        issuance=issuance,
        delivery=delivery,
        terminal=terminal,
    )


def _read_exact(
    objects: ContextObjectReader,
    object_id: str,
    revision: int,
    expected_sha256: str,
) -> Mapping[str, Any]:
    value = objects.read("context", object_id, revision)
    if not isinstance(value, Mapping):
        raise IntegrityError("context object is not a mapping")
    observed = sha256_hex(canonical_bytes(dict(value)))
    if observed != expected_sha256:
        raise IntegrityError("context object hash differs from lifecycle authority")
    return value


def _parse_z(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise IntegrityError(f"{field} is not a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise IntegrityError(f"{field} is not a valid timestamp") from exc
    return parsed.astimezone(UTC)


def resolve_context_packet_for_consumer(
    events: Iterable[Mapping[str, Any]],
    objects: ContextObjectReader,
    *,
    context_id: str,
    revision: int,
    packet_sha256: str,
    consumer_id: str,
    purpose: str,
    scope: str,
    evaluation_time: datetime,
    control_store_identity: str,
    source_position: int,
    source_hash: str,
    source_resolver: SourceResolver,
) -> ResolvedContextPacket:
    """Resolve only an exact delivered, current packet from verified ledger state."""
    if (
        not isinstance(evaluation_time, datetime)
        or evaluation_time.tzinfo is None
        or evaluation_time.utcoffset() is None
    ):
        raise ValueError("evaluation_time must be timezone-aware")
    evaluated_at = evaluation_time.astimezone(UTC)
    event_values = tuple(events)
    state = rebuild_context_lifecycle(event_values, context_id)
    owner = rebuild_owner_operated_handoff(event_values, context_id)
    owner_mode = owner is not None
    if owner_mode:
        if state.state != "compiled" or state.compilation is None:
            raise ArsError(f"owner-operated context packet is not consumable from state {state.state}")
        prepared, validation, issuance, delivery = owner
        profile = prepared.get("owner_profile")
        if (
            not isinstance(profile, Mapping)
            or profile.get("provider_launch") is not False
            or sha256_hex(canonical_bytes(dict(profile))) != prepared.get("owner_profile_sha256")
        ):
            raise IntegrityError("owner-operated profile binding differs")
        if (
            profile.get("context_id") != context_id
            or profile.get("packet_revision") != revision
            or profile.get("packet_sha256") != packet_sha256
            or profile.get("recipient_id") != consumer_id
            or profile.get("purpose") != purpose
            or profile.get("scope") != scope
            or delivery.get("recipient_session_id") != profile.get("operator_session_id")
        ):
            raise ArsError("owner-operated profile does not authorize this consumer request")
        if not (
            _parse_z(profile.get("valid_from"), "owner valid_from")
            <= evaluated_at
            < _parse_z(profile.get("expires_at"), "owner expires_at")
        ):
            raise ArsError("owner-operated delivery is outside its finite window")
    else:
        if state.state != "delivered":
            raise ArsError(f"context packet is not consumable in state {state.state}")
        if not all((state.compilation, state.validation, state.issuance, state.delivery)):
            raise IntegrityError("delivered context lifecycle is incomplete")
        validation = state.validation
        issuance = state.issuance
        delivery = state.delivery

    compilation = state.compilation
    assert compilation is not None and issuance is not None and delivery is not None
    if (
        compilation.get("packet_revision") != revision
        or compilation.get("packet_sha256") != packet_sha256
        or issuance.get("packet_revision") != revision
        or issuance.get("packet_sha256") != packet_sha256
        or delivery.get("packet_sha256") != packet_sha256
    ):
        raise ArsError("requested packet identity does not match issued bytes")
    request = state.request
    if request.get("purpose") != purpose or scope not in request.get("permitted_scopes", []):
        raise ArsError("consumer purpose or scope is not authorized by the request")
    if delivery.get("recipient_id") != consumer_id:
        raise ArsError("delivery recipient does not match the consumer")
    assert validation is not None
    if owner_mode:
        if compilation.get("manifest_sha256") != issuance.get("manifest_sha256"):
            raise IntegrityError("owner-operated issuance manifest binding differs")
    elif (
        validation.get("capability_digest") != issuance.get("capability_digest")
        or validation.get("provider_template_sha256") != issuance.get("provider_template_sha256")
        or compilation.get("manifest_sha256") != issuance.get("manifest_sha256")
    ):
        raise IntegrityError("validation and issuance bindings disagree")

    packet = _read_exact(
        objects,
        str(compilation["packet_object_id"]),
        int(compilation["packet_revision"]),
        str(compilation["packet_sha256"]),
    )
    manifest = _read_exact(
        objects,
        str(compilation["manifest_object_id"]),
        int(compilation["manifest_revision"]),
        str(compilation["manifest_sha256"]),
    )
    if (
        packet.get("context_id") != context_id
        or packet.get("revision") != revision
        or packet.get("request_id") != request.get("request_id")
        or manifest.get("context_id") != context_id
        or manifest.get("request_id") != request.get("request_id")
        or manifest.get("rendered_packet_sha256") != packet.get("rendered_sha256")
    ):
        raise IntegrityError("packet and manifest lifecycle bindings disagree")
    if manifest.get("freshness_verdict") != "current" or manifest.get("conflicts"):
        raise ArsError("context packet is stale or conflicted")
    if manifest.get("control_store_identity") != control_store_identity:
        raise ArsError("control-store identity changed since compilation")
    if manifest.get("source_position") != source_position or manifest.get("source_hash") != source_hash:
        raise ArsError("context currency source changed since compilation")
    source_manifest = manifest.get("included")
    if not isinstance(source_manifest, list) or not source_manifest:
        raise IntegrityError("context source manifest is unavailable")
    source_ids = {str(item.get("source_id")) for item in source_manifest}
    current_sources = resolve_sources(source_resolver, source_ids)
    current_by_id = {source.source_id: source for source in current_sources}
    for item in source_manifest:
        source_id = str(item.get("source_id"))
        current_source = current_by_id[source_id]
        if (
            str(item.get("revision")) != current_source.revision
            or item.get("content_hash") != current_source.content_hash
        ):
            raise ArsError(f"direct source changed since compilation: {source_id}")
    expires_at = manifest.get("expires_at")
    if expires_at is not None and evaluated_at >= _parse_z(expires_at, "expires_at"):
        raise ArsError("context packet has expired")
    delivery_receipt = _read_exact(
        objects,
        str(delivery["delivery_receipt_object_id"]),
        int(delivery["delivery_receipt_revision"]),
        str(delivery["delivery_receipt_sha256"]),
    )
    invalid_receipt = (
        delivery_receipt.get("context_id") != context_id
        or delivery_receipt.get("packet_sha256") != packet_sha256
        or delivery_receipt.get("recipient_id") != consumer_id
        or delivery_receipt.get("recipient_session_id") != delivery.get("recipient_session_id")
    )
    if owner_mode:
        invalid_receipt = (
            invalid_receipt
            or delivery_receipt.get("provider_launch") is not False
            or (delivery_receipt.get("owner_profile_sha256") != delivery.get("owner_profile_sha256"))
        )
    else:
        invalid_receipt = invalid_receipt or delivery_receipt.get("adapter_id") != delivery.get("adapter_id")
    if invalid_receipt:
        raise IntegrityError("delivery receipt does not bind the delivered packet")
    return ResolvedContextPacket(
        context_id=context_id,
        revision=revision,
        packet_sha256=packet_sha256,
        packet=packet,
        manifest=manifest,
        delivery=delivery_receipt,
    )
