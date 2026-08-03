from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError, SchemaError
from research_system.schema_registry import SchemaIdentity

T2_COMMAND_TYPES = frozenset({"IssueCostGrant", "AuthorizeProviderIssue", "RecordProviderReceipt"})
_EVENT_ORDER = {
    "IssueCostGrant": ("CostGrantIssued",),
    "AuthorizeProviderIssue": ("CostGrantReserved", "ProviderCommandIssued"),
    "RecordProviderReceipt": ("ProviderReceiptRecorded", "CostGrantReconciled"),
}
_SCOPES = {
    "IssueCostGrant": "wp6.2.t2.cost-grant.issue",
    "AuthorizeProviderIssue": "wp6.2.t2.provider.issue",
    "RecordProviderReceipt": "wp6.2.t2.provider.receipt.record",
}
_STREAM_ROLES = {
    "IssueCostGrant": ("cost_grant",),
    "AuthorizeProviderIssue": ("cost_grant", "provider_command"),
    "RecordProviderReceipt": ("provider_command", "cost_grant"),
}
_SUBJECT_STEMS = {
    "IssueCostGrant": (
        "cost_grant",
        "resource_grant",
        "task",
        "dispatch",
        "attempt",
        "provider_command",
        "secret_reference",
        "rate_evidence",
    ),
    "AuthorizeProviderIssue": (
        "cost_grant",
        "resource_grant",
        "task",
        "dispatch",
        "attempt",
        "provider_command",
        "secret_reference",
        "reservation",
        "rate_evidence",
    ),
    "RecordProviderReceipt": (
        "provider_command",
        "resource_grant",
        "task",
        "dispatch",
        "attempt",
        "provider_receipt",
        "cost_grant",
        "reservation",
        "secret_reference",
        "rate_evidence",
    ),
}


@dataclass(frozen=True)
class T2Receipt:
    """Strict Receipt 2.0 value returned by the T2 command boundary."""

    record: Mapping[str, Any]

    @property
    def status(self) -> str:
        return str(self.record["outcome"])

    @property
    def command_id(self) -> str:
        return str(self.record["command_id"])

    @property
    def payload_hash(self) -> str:
        return str(self.record["payload_hash"])

    @property
    def event_batch_id(self) -> str | None:
        value = self.record["event_batch_id"]
        return None if value is None else str(value)

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self.record["events"])

    def to_record(self) -> dict[str, Any]:
        return {key: [dict(item) for item in value] if key == "events" else value for key, value in self.record.items()}

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> T2Receipt:
        return cls(dict(record))


@dataclass(frozen=True)
class _T2Command:
    envelope: dict[str, Any]

    @property
    def command_id(self) -> str:
        return str(self.envelope["command_id"])

    @property
    def actor_id(self) -> str:
        return str(self.envelope["actor_id"])

    @property
    def idempotency_key(self) -> str:
        return str(self.envelope["idempotency_key"])

    @property
    def payload_hash(self) -> str:
        return str(self.envelope["payload_hash"])


def _receipt_id(command_id: str) -> str:
    return "rcp_" + command_id.removeprefix("cmd_")


def _event_proof(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "transaction_position": event["transaction_index"],
            "stream_id": event["stream_id"],
            "prior_stream_version": event["stream_version"] - 1,
            "resulting_stream_version": event["stream_version"],
        }
        for event in events
    ]


def _receipt(
    envelope: Mapping[str, Any],
    outcome: str,
    *,
    events: list[dict[str, Any]] | None = None,
    event_batch_id: str | None = None,
    stable_reason: str | None = None,
    original_accepted_receipt_hash: str | None = None,
) -> T2Receipt:
    proof = _event_proof(events or [])
    record: dict[str, Any] = {
        "schema_id": "ars://core/receipt/v2",
        "schema_version": "2.0.0",
        "receipt_id": _receipt_id(str(envelope["command_id"])),
        "outcome": outcome,
        "command_type": envelope["command_type"],
        "command_id": envelope["command_id"],
        "idempotency_key_hash": sha256_hex(str(envelope["idempotency_key"]).encode("utf-8")),
        "payload_hash": envelope["payload_hash"],
        "event_batch_id": event_batch_id,
        "events": proof,
        "stable_reason": stable_reason,
        "unmet_preconditions": [] if stable_reason is None else [stable_reason],
        "original_accepted_receipt_hash": original_accepted_receipt_hash,
        "outcome_binding_hash": "0" * 64,
        "new_event_count": len(proof) if outcome == "accepted" else 0,
        "new_invocation_count": 0,
    }
    binding = dict(record)
    binding.pop("outcome_binding_hash")
    record["outcome_binding_hash"] = sha256_hex(canonical_bytes(binding))
    return T2Receipt(record)


def _accepted_receipt(envelope: Mapping[str, Any], events: list[dict[str, Any]]) -> T2Receipt:
    return _receipt(
        envelope,
        "accepted",
        events=events,
        event_batch_id=events[0]["transaction_id"],
    )


def _duplicate_receipt(accepted: T2Receipt) -> T2Receipt:
    source = accepted.to_record()
    envelope = {
        "command_id": source["command_id"],
        "command_type": source["command_type"],
        "idempotency_key": "",
        "payload_hash": source["payload_hash"],
    }
    # The logical key itself is not retained in Receipt 2.0, so preserve its
    # accepted hash after constructing the duplicate proof.
    duplicate = _receipt(
        envelope,
        "duplicate",
        events=[],
        event_batch_id=source["event_batch_id"],
        original_accepted_receipt_hash=sha256_hex(canonical_bytes(source)),
    ).to_record()
    duplicate["idempotency_key_hash"] = source["idempotency_key_hash"]
    duplicate["events"] = source["events"]
    # Receipt 2.0 binds a duplicate to the exact original accepted outcome
    # proof, even though the duplicate reports zero new effects.
    duplicate["outcome_binding_hash"] = source["outcome_binding_hash"]
    return T2Receipt(duplicate)


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp is not a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return parsed.astimezone(UTC)


def _lookup(service: Any, kind: str, object_id: str, revision: int) -> Mapping[str, Any] | None:
    resolver = service.t2_authority_resolver
    if resolver is None:
        return None
    value = resolver(kind, object_id, revision)
    return value if isinstance(value, Mapping) else None


def _triple_matches(record: Mapping[str, Any], kind: str, stem: str, payload: Mapping[str, Any]) -> bool:
    record_id = record.get(f"{stem}_id", record.get("id"))
    record_revision = record.get(f"{stem}_revision", record.get("revision"))
    record_hash = record.get(
        f"{stem}_hash",
        record.get("content_hash", record.get("revision_hash")),
    )
    record_kind = record.get("kind")
    return (
        (
            record_kind == kind
            or (kind == "provider_receipt" and record.get("schema_id") == "ars://adapters/provider-receipt/v2")
        )
        and record_id == payload.get(f"{stem}_id")
        and record_revision == payload.get(f"{stem}_revision")
        and record_hash == payload.get(f"{stem}_hash")
    )


def _subject_reason(command_type: str, stem: str) -> str:
    if stem == "cost_grant":
        return "cost_grant_identity_mismatch"
    if stem == "provider_command":
        return "provider_command_identity_mismatch"
    if stem == "provider_receipt":
        return "provider_receipt_identity_mismatch"
    if stem == "secret_reference":
        return "secret_reference_identity_mismatch"
    if command_type == "RecordProviderReceipt":
        return "provider_receipt_identity_mismatch"
    return "schema_identity_mismatch"


def _subject_gate(service: Any, envelope: Mapping[str, Any]) -> str | None:
    """Bind every applicable payload triple to an independently resolved record."""
    command_type = str(envelope["command_type"])
    payload = envelope["payload"]
    for stem in _SUBJECT_STEMS[command_type]:
        record = _lookup(
            service,
            stem,
            payload[f"{stem}_id"],
            payload[f"{stem}_revision"],
        )
        if record is None or not _triple_matches(record, stem, stem, payload):
            return _subject_reason(command_type, stem)
    zero = payload.get("zero_cost_authority")
    if isinstance(zero, Mapping):
        record = _lookup(
            service,
            "zero_cost_authority",
            str(zero.get("subject_id")),
            int(zero.get("subject_revision", 0)),
        )
        if (
            record is None
            or record.get("kind") != "zero_cost_authority"
            or record.get("id") != zero.get("subject_id")
            or record.get("revision") != zero.get("subject_revision")
            or record.get("content_hash") != zero.get("subject_hash")
        ):
            return "schema_identity_mismatch"
    return None


def _current(record: Mapping[str, Any], now: datetime) -> bool:
    if record.get("revoked") is True or record.get("status") == "revoked":
        return False
    expires_at = record.get("expires_at")
    if expires_at is None:
        return True
    # Reject resolver-provided records whose expires_at is not a well-formed
    # timezone-aware ISO 8601 string rather than letting _parse_time raise.
    if not isinstance(expires_at, str):
        return False
    try:
        return _parse_time(expires_at) > now
    except ValueError:
        return False


def _evidence_covers(payload: Mapping[str, Any], evidence: object) -> bool:
    if not isinstance(evidence, list):
        return False
    supplied = {
        (
            item.get("subject_id"),
            item.get("subject_revision"),
            item.get("subject_hash"),
        )
        for item in evidence
        if isinstance(item, Mapping)
    }
    stems = {
        key.removesuffix("_id")
        for key in payload
        if key.endswith("_id")
        and f"{key.removesuffix('_id')}_revision" in payload
        and f"{key.removesuffix('_id')}_hash" in payload
    }
    required = {
        (
            payload[f"{stem}_id"],
            payload[f"{stem}_revision"],
            payload[f"{stem}_hash"],
        )
        for stem in stems
    }
    zero = payload.get("zero_cost_authority")
    if isinstance(zero, Mapping):
        required.add((zero.get("subject_id"), zero.get("subject_revision"), zero.get("subject_hash")))
    return required.issubset(supplied)


def _rate_valid(payload: Mapping[str, Any], *, actual: bool = False) -> bool:
    mode = payload.get("rate_mode")
    input_rate = payload.get("input_microunits_per_million_tokens")
    output_rate = payload.get("output_microunits_per_million_tokens")
    reserved = payload.get("reserved_cost_microunits")
    zero = payload.get("zero_cost_authority")
    if mode == "metered":
        return (
            isinstance(input_rate, int)
            and not isinstance(input_rate, bool)
            and input_rate > 0
            and isinstance(output_rate, int)
            and not isinstance(output_rate, bool)
            and output_rate > 0
            and isinstance(reserved, int)
            and reserved > 0
            and zero is None
        )
    return (
        mode == "zero_cost_authorized"
        and input_rate == 0
        and output_rate == 0
        and reserved == 0
        and isinstance(zero, Mapping)
        and (not actual or payload.get("consumed_cost_microunits") == 0)
    )


def _ceil_cost(input_tokens: int, output_tokens: int, input_rate: int, output_rate: int) -> int:
    return (input_tokens * input_rate + 999_999) // 1_000_000 + (output_tokens * output_rate + 999_999) // 1_000_000


def reduce_cost_grant(state: Mapping[str, Any] | None, event: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a cost-grant stream by one T2 event.

    Args:
        state: Current cost-grant projection state, or ``None`` if the stream
            has not yet been opened.
        event: A T2 ledger event whose ``event_type`` is one of
            ``CostGrantIssued``, ``CostGrantReserved``, or
            ``CostGrantReconciled``.

    Returns:
        Updated cost-grant state dictionary containing the merged reservation
        table, available balance, and stream version.

    Raises:
        IntegrityError: If the event violates stream-lifecycle invariants (e.g.
            issuing into an existing stream, or transitioning a stream that has
            not been opened).
    """
    payload = dict(event["payload"])
    event_type = event["event_type"]
    if event_type == "CostGrantIssued":
        if state is not None:
            raise IntegrityError("CostGrantIssued requires a new stream")
        return {
            **payload,
            "reservations": {},
            "reconciled_receipt_ids": [],
            "version": event["stream_version"],
        }
    if state is None:
        raise IntegrityError("cost grant transition requires issued state")
    updated = dict(state)
    reservations = dict(updated.get("reservations", {}))
    if event_type == "CostGrantReserved":
        reservation_id = payload["reservation_id"]
        if reservation_id in reservations:
            raise IntegrityError("reservation already exists")
        reservations[reservation_id] = payload
        updated.update(
            {
                "reservations": reservations,
                "available_cost_microunits": payload["remaining_cost_microunits"],
                "version": event["stream_version"],
            }
        )
        return updated
    if event_type == "CostGrantReconciled":
        reservation = reservations.get(payload["reservation_id"])
        if reservation is None or reservation.get("reconciled"):
            raise IntegrityError("reconciliation requires an open reservation")
        reservations[payload["reservation_id"]] = {
            **reservation,
            "reconciled": True,
            "provider_receipt_id": payload["provider_receipt_id"],
        }
        receipt_ids = list(updated.get("reconciled_receipt_ids", []))
        if payload["provider_receipt_id"] in receipt_ids:
            raise IntegrityError("provider receipt already reconciled")
        receipt_ids.append(payload["provider_receipt_id"])
        updated.update(
            {
                "reservations": reservations,
                "reconciled_receipt_ids": receipt_ids,
                "available_cost_microunits": payload["remaining_cost_microunits"],
                "version": event["stream_version"],
            }
        )
        return updated
    raise IntegrityError(f"unsupported cost grant event: {event_type}")


def reduce_provider_command(state: Mapping[str, Any] | None, event: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a provider-command stream by one T2 event.

    Args:
        state: Current provider-command projection state, or ``None`` if the
            stream has not yet been opened.
        event: A T2 ledger event whose ``event_type`` is one of
            ``ProviderCommandIssued`` or ``ProviderReceiptRecorded``.

    Returns:
        Updated provider-command state dictionary carrying the command identity,
        current status, and stream version.

    Raises:
        IntegrityError: If the event violates stream-lifecycle invariants (e.g.
            recording a receipt before the command has been issued).
    """
    payload = dict(event["payload"])
    if event["event_type"] == "ProviderCommandIssued":
        if state is not None:
            raise IntegrityError("ProviderCommandIssued requires a new stream")
        return {**payload, "status": "issued", "version": event["stream_version"]}
    if event["event_type"] == "ProviderReceiptRecorded":
        if state is None or state.get("status") != "issued":
            raise IntegrityError("provider receipt requires one issued command")
        if payload["provider_command_id"] != state["provider_command_id"]:
            raise IntegrityError("provider receipt command mismatch")
        return {
            **dict(state),
            "status": "receipt_recorded",
            "provider_receipt_id": payload["provider_receipt_id"],
            "provider_receipt_hash": payload["provider_receipt_hash"],
            "version": event["stream_version"],
        }
    raise IntegrityError(f"unsupported provider command event: {event['event_type']}")


def apply_t2_event(state: dict[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one T2 ledger event to a mutable global T2 projection state.

    Dispatches the event to the appropriate sub-reducer (``reduce_cost_grant``
    or ``reduce_provider_command``) and maintains the denormalised ``streams``
    index so callers can look up any stream by ID without knowing its type.

    Args:
        state: Mutable global T2 projection dictionary with ``cost_grants``,
            ``provider_commands``, ``provider_receipts``, and ``streams`` sub-
            dictionaries, as produced by ``_t2_projection``.
        event: A validated T2 ledger event with a recognised ``event_type``.

    Returns:
        The same ``state`` dictionary after in-place mutation, returned for
        convenience.

    Raises:
        IntegrityError: If the event type is not recognised, or if a sub-
            reducer detects a stream-lifecycle violation.
    """
    event_type = event["event_type"]
    if event_type in {"CostGrantIssued", "CostGrantReserved", "CostGrantReconciled"}:
        grants = state.setdefault("cost_grants", {})
        stream_id = event["stream_id"]
        grants[stream_id] = reduce_cost_grant(grants.get(stream_id), event)
    elif event_type in {"ProviderCommandIssued", "ProviderReceiptRecorded"}:
        commands = state.setdefault("provider_commands", {})
        stream_id = event["stream_id"]
        commands[stream_id] = reduce_provider_command(commands.get(stream_id), event)
        if event_type == "ProviderReceiptRecorded":
            receipts = state.setdefault("provider_receipts", {})
            receipt_id = event["payload"]["provider_receipt_id"]
            if receipt_id in receipts:
                raise IntegrityError("provider receipt identity already recorded")
            receipts[receipt_id] = dict(event["payload"])
    else:
        raise IntegrityError(f"unsupported T2 event type: {event_type}")
    state.setdefault("streams", {})[event["stream_id"]] = state.get("cost_grants", {}).get(
        event["stream_id"]
    ) or state.get("provider_commands", {}).get(event["stream_id"])
    return state


def _t2_projection(events: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    state: dict[str, Any] = {"cost_grants": {}, "provider_commands": {}, "provider_receipts": {}}
    for event in events:
        if str(event.get("schema_id", "")).startswith("ars://wp6-2/t2/event/"):
            apply_t2_event(state, event)
    return state


def _common_semantics(envelope: Mapping[str, Any]) -> str | None:
    command_type = envelope["command_type"]
    payload = envelope["payload"]
    write_set = envelope["write_set"]
    if envelope.get("authority_scope") != _SCOPES[command_type]:
        return "schema_identity_mismatch"
    if [entry.get("stream_role") for entry in write_set] != list(_STREAM_ROLES[command_type]):
        return "schema_identity_mismatch"
    expected_ids = {
        "cost_grant": payload.get("cost_grant_id"),
        "provider_command": payload.get("provider_command_id"),
    }
    if any(entry.get("stream_id") != expected_ids[entry["stream_role"]] for entry in write_set):
        return "schema_identity_mismatch"
    if envelope.get("target_stream_id") != write_set[0]["stream_id"]:
        return "schema_identity_mismatch"
    if not _evidence_covers(payload, envelope.get("evidence_refs")):
        return "schema_identity_mismatch"
    return None


def _issue_semantics(service: Any, envelope: Mapping[str, Any], now: datetime) -> str | None:
    payload = envelope["payload"]
    if envelope["write_set"][0]["expected_stream_version"] != 0:
        return "stale_stream_version"
    subject_error = _subject_gate(service, envelope)
    if subject_error is not None:
        return subject_error
    resource = _lookup(service, "resource_grant", payload["resource_grant_id"], payload["resource_grant_revision"])
    authority = _lookup(service, "authority_grant", envelope["authority_grant_id"], 1)
    if resource is None or not _triple_matches(resource, "resource_grant", "resource_grant", payload):
        return "schema_identity_mismatch"
    if authority is None or authority.get("kind") != "authority_grant":
        return "schema_identity_mismatch"
    if not _current(resource, now) or not _current(authority, now):
        return "schema_identity_mismatch"
    try:
        if _parse_time(payload["expires_at"]) <= now:
            return "cost_grant_expired"
    except ValueError:
        return "schema_identity_mismatch"
    return None


def _authorize_semantics(
    service: Any,
    envelope: Mapping[str, Any],
    state: Mapping[str, Any],
    now: datetime,
) -> str | None:
    payload = envelope["payload"]
    if (
        envelope["write_set"][0]["expected_stream_version"] != payload["cost_grant_revision"]
        or envelope["write_set"][1]["expected_stream_version"] != 0
        or payload["reservation_id"] != "crs_" + str(envelope["command_id"]).split("_", 1)[1]
    ):
        return "schema_identity_mismatch"
    grant = state["cost_grants"].get(payload["cost_grant_id"])
    if grant is None:
        return (
            "cost_grant_wrong_type"
            if envelope["write_set"][0]["stream_id"] in state["provider_commands"]
            else "cost_grant_missing"
        )
    if (
        grant.get("cost_grant_id") != payload["cost_grant_id"]
        or grant.get("cost_grant_hash") != payload["cost_grant_hash"]
        or grant.get("version") != payload["cost_grant_revision"]
    ):
        return "cost_grant_identity_mismatch"
    for stem in (
        "resource_grant",
        "task",
        "dispatch",
        "attempt",
        "provider_command",
        "secret_reference",
    ):
        if any(grant.get(f"{stem}_{part}") != payload.get(f"{stem}_{part}") for part in ("id", "revision", "hash")):
            return (
                "provider_command_identity_mismatch" if stem == "provider_command" else "cost_grant_identity_mismatch"
            )
    secret = _lookup(
        service,
        "secret_reference",
        payload["secret_reference_id"],
        payload["secret_reference_revision"],
    )
    if secret is None:
        return "secret_reference_missing"
    if secret.get("kind") != "secret_reference":
        return "secret_reference_wrong_type"
    if not _triple_matches(secret, "secret_reference", "secret_reference", payload):
        return "secret_reference_identity_mismatch"
    if secret.get("revoked") is True or secret.get("status") == "revoked":
        return "secret_reference_revoked"
    if not _current(secret, now):
        return "secret_reference_expired"
    allowed_scope = secret.get("allowed_scope")
    if allowed_scope not in (
        envelope["authority_scope"],
        [envelope["authority_scope"]],
        (envelope["authority_scope"],),
    ):
        return "secret_reference_identity_mismatch"
    resource = _lookup(
        service,
        "resource_grant",
        payload["resource_grant_id"],
        payload["resource_grant_revision"],
    )
    authority = _lookup(service, "authority_grant", envelope["authority_grant_id"], 1)
    if (
        resource is None
        or not _triple_matches(resource, "resource_grant", "resource_grant", payload)
        or authority is None
        or authority.get("kind") != "authority_grant"
        or not _current(resource, now)
        or not _current(authority, now)
    ):
        return "schema_identity_mismatch"
    override = _lookup(service, "cost_grant", payload["cost_grant_id"], payload["cost_grant_revision"])
    if override is not None:
        if override.get("kind") != "cost_grant":
            return "cost_grant_wrong_type"
        if not _triple_matches(override, "cost_grant", "cost_grant", payload):
            return "cost_grant_identity_mismatch"
        if override.get("revoked") is True or override.get("status") == "revoked":
            return "cost_grant_revoked"
        if override.get("status") == "zero":
            return "cost_grant_zero"
        if override.get("status") == "exhausted":
            return "cost_grant_exhausted"
        if not _current(override, now):
            return "cost_grant_expired"
    subject_error = _subject_gate(service, envelope)
    if subject_error is not None:
        return subject_error
    try:
        if _parse_time(grant["expires_at"]) <= now:
            return "cost_grant_expired"
    except ValueError:
        return "cost_grant_identity_mismatch"
    available = grant["available_cost_microunits"]
    if grant["cost_ceiling_microunits"] == 0:
        return "cost_grant_zero"
    if available == 0:
        return "cost_grant_exhausted"
    if payload["expected_available_microunits"] != available:
        return "cost_grant_identity_mismatch"
    if payload["reserved_cost_microunits"] > available:
        return "cost_grant_insufficient_balance"
    requested = payload["requested_tokens"]
    ceilings = grant["token_ceilings"]
    if requested["total_tokens"] != requested["input_tokens"] + requested["output_tokens"]:
        return "cost_grant_insufficient_balance"
    if any(requested[key] > ceilings[key] for key in requested):
        return "cost_grant_insufficient_balance"
    if (
        payload["currency"] != grant["currency"]
        or any(
            payload[f"rate_evidence_{part}"] != grant[f"rate_evidence_{part}"] for part in ("id", "revision", "hash")
        )
        or not _rate_valid(payload)
    ):
        return "schema_identity_mismatch"
    if payload["rate_mode"] == "metered":
        minimum = _ceil_cost(
            requested["input_tokens"],
            requested["output_tokens"],
            payload["input_microunits_per_million_tokens"],
            payload["output_microunits_per_million_tokens"],
        )
        if payload["reserved_cost_microunits"] < minimum:
            return "cost_grant_insufficient_balance"
    return None


def _record_semantics(service: Any, envelope: Mapping[str, Any], state: Mapping[str, Any]) -> str | None:
    payload = envelope["payload"]
    command = state["provider_commands"].get(payload["provider_command_id"])
    grant = state["cost_grants"].get(payload["cost_grant_id"])
    if command is None:
        return "provider_command_identity_mismatch"
    if grant is None:
        return "cost_grant_missing"
    reservation = grant.get("reservations", {}).get(payload["reservation_id"])
    if reservation is None or reservation.get("reconciled"):
        return "reconciliation_actuals_invalid"
    if payload["provider_receipt_id"] in state["provider_receipts"]:
        return "provider_receipt_identity_mismatch"
    subject_error = _subject_gate(service, envelope)
    if subject_error is not None:
        return subject_error
    provider_receipt = _lookup(
        service,
        "provider_receipt",
        payload["provider_receipt_id"],
        payload["provider_receipt_revision"],
    )
    if provider_receipt is None or not _triple_matches(
        provider_receipt, "provider_receipt", "provider_receipt", payload
    ):
        return "provider_receipt_identity_mismatch"
    if (
        payload["provider_receipt_schema_id"] != "ars://adapters/provider-receipt/v2"
        or payload["provider_receipt_schema_version"] != "2.0.0"
    ):
        return "schema_identity_mismatch"
    if payload["receipt_complete"] is not True:
        return "provider_receipt_incomplete"
    try:
        service.schemas.validate(
            "ars://adapters/provider-receipt/v2",
            provider_receipt,
        )
    except SchemaError:
        return "provider_receipt_identity_mismatch"
    receipt_command = provider_receipt["command_binding"]["provider_command"]
    if (
        receipt_command.get("id"),
        receipt_command.get("revision"),
        receipt_command.get("content_hash"),
    ) != (
        payload["provider_command_id"],
        payload["provider_command_revision"],
        payload["provider_command_hash"],
    ):
        return "provider_receipt_identity_mismatch"
    receipt_authority = provider_receipt["authority_binding"]
    for stem in (
        "resource_grant",
        "task",
        "dispatch",
        "attempt",
        "cost_grant",
        "reservation",
        "secret_reference",
        "provider_receipt",
    ):
        triple = receipt_authority[stem]
        if (
            triple.get("id"),
            triple.get("revision"),
            triple.get("content_hash"),
        ) != (
            payload[f"{stem}_id"],
            payload[f"{stem}_revision"],
            payload[f"{stem}_hash"],
        ):
            return "provider_receipt_identity_mismatch"
    if (
        envelope["write_set"][0]["expected_stream_version"] != payload["provider_command_revision"]
        or envelope["write_set"][1]["expected_stream_version"] != payload["cost_grant_revision"]
        or command.get("version") != payload["provider_command_revision"]
        or grant.get("version") != payload["cost_grant_revision"]
        or command.get("provider_command_hash") != payload["provider_command_hash"]
        or grant.get("cost_grant_hash") != payload["cost_grant_hash"]
    ):
        return "provider_receipt_identity_mismatch"
    for stem in (
        "resource_grant",
        "task",
        "dispatch",
        "attempt",
        "secret_reference",
    ):
        source = grant
        if any(source.get(f"{stem}_{part}") != payload.get(f"{stem}_{part}") for part in ("id", "revision", "hash")):
            return (
                "provider_command_identity_mismatch"
                if stem == "provider_command"
                else "provider_receipt_identity_mismatch"
            )
    actual = payload["actual_tokens"]
    reserved = payload["reserved_token_ceilings"]
    receipt_accounting = provider_receipt["token_accounting"]
    if (
        receipt_accounting.get("actual_input_tokens"),
        receipt_accounting.get("actual_output_tokens"),
        receipt_accounting.get("actual_total_tokens"),
        receipt_accounting.get("reserved_cost_microunits"),
        receipt_accounting.get("consumed_cost_microunits"),
        receipt_accounting.get("refund_cost_microunits"),
        receipt_accounting.get("currency"),
        receipt_accounting.get("rate_evidence_id"),
        receipt_accounting.get("rate_evidence_revision"),
        receipt_accounting.get("rate_evidence_hash"),
        provider_receipt.get("terminal_outcome", {}).get("status"),
        provider_receipt.get("completeness", {}).get("complete"),
    ) != (
        actual["input_tokens"],
        actual["output_tokens"],
        actual["total_tokens"],
        payload["reserved_cost_microunits"],
        payload["consumed_cost_microunits"],
        payload["refund_cost_microunits"],
        payload["currency"],
        payload["rate_evidence_id"],
        payload["rate_evidence_revision"],
        payload["rate_evidence_hash"],
        payload["provider_terminal_status"],
        payload["receipt_complete"],
    ):
        return "reconciliation_actuals_invalid"
    if (
        actual["total_tokens"] != actual["input_tokens"] + actual["output_tokens"]
        or reserved != reservation["reserved_tokens"]
        or any(actual[key] > reserved[key] for key in actual)
        or payload["reserved_cost_microunits"] != reservation["reserved_cost_microunits"]
        or payload["currency"] != reservation["currency"]
        or any(
            payload[f"rate_evidence_{part}"] != reservation[f"rate_evidence_{part}"]
            for part in ("id", "revision", "hash")
        )
        or not _rate_valid(payload, actual=True)
    ):
        return "reconciliation_actuals_invalid"
    cost = _ceil_cost(
        actual["input_tokens"],
        actual["output_tokens"],
        payload["input_microunits_per_million_tokens"],
        payload["output_microunits_per_million_tokens"],
    )
    refund = payload["reserved_cost_microunits"] - cost
    disposition = "fully_consumed" if refund == 0 else "refunded"
    if (
        payload["consumed_cost_microunits"] != cost
        or refund < 0
        or payload["refund_cost_microunits"] != refund
        or payload["refund_disposition"] != disposition
        or grant["available_cost_microunits"] + refund > grant["cost_ceiling_microunits"]
    ):
        return "reconciliation_actuals_invalid"
    return None


def _event_envelope(
    envelope: Mapping[str, Any],
    command_schema: SchemaIdentity,
    event_type: str,
    stream_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": f"ars://wp6-2/t2/event/{event_type}",
        "schema_version": "1.1.0",
        "event_type": event_type,
        "stream_id": stream_id,
        "command_id": envelope["command_id"],
        "authority_scope": envelope["authority_scope"],
        "command_type": envelope["command_type"],
        "idempotency_key": envelope["idempotency_key"],
        "idempotency_key_hash": sha256_hex(str(envelope["idempotency_key"]).encode("utf-8")),
        "payload_hash": envelope["payload_hash"],
        "correlation_id": envelope["correlation_id"],
        "causation_id": envelope["causation_id"] or envelope["command_id"],
        "actor_id": envelope["actor_id"],
        "authority_grant_id": envelope["authority_grant_id"],
        "command_schema_id": command_schema.schema_id,
        "command_schema_version": command_schema.schema_version,
        "command_schema_sha256": command_schema.sha256,
        "payload": dict(payload),
    }


def _events_for(
    envelope: Mapping[str, Any],
    state: Mapping[str, Any],
    command_schema: SchemaIdentity,
) -> list[dict[str, Any]]:
    payload = envelope["payload"]
    if envelope["command_type"] == "IssueCostGrant":
        return [
            _event_envelope(
                envelope,
                command_schema,
                "CostGrantIssued",
                payload["cost_grant_id"],
                {
                    **payload,
                    "grant_status": "active",
                    "available_cost_microunits": payload["cost_ceiling_microunits"],
                },
            )
        ]
    if envelope["command_type"] == "AuthorizeProviderIssue":
        grant = state["cost_grants"][payload["cost_grant_id"]]
        reserved = payload["reserved_cost_microunits"]
        return [
            _event_envelope(
                envelope,
                command_schema,
                "CostGrantReserved",
                payload["cost_grant_id"],
                {
                    "cost_grant_id": payload["cost_grant_id"],
                    "reservation_id": payload["reservation_id"],
                    "provider_command_id": payload["provider_command_id"],
                    "reserved_tokens": payload["requested_tokens"],
                    "reserved_cost_microunits": reserved,
                    "remaining_cost_microunits": grant["available_cost_microunits"] - reserved,
                    "currency": payload["currency"],
                    "rate_evidence_id": payload["rate_evidence_id"],
                    "rate_evidence_revision": payload["rate_evidence_revision"],
                    "rate_evidence_hash": payload["rate_evidence_hash"],
                    "input_microunits_per_million_tokens": payload["input_microunits_per_million_tokens"],
                    "output_microunits_per_million_tokens": payload["output_microunits_per_million_tokens"],
                    "rate_mode": payload["rate_mode"],
                    "zero_cost_authority": payload["zero_cost_authority"],
                },
            ),
            _event_envelope(
                envelope,
                command_schema,
                "ProviderCommandIssued",
                payload["provider_command_id"],
                {
                    "provider_command_id": payload["provider_command_id"],
                    "provider_command_revision": payload["provider_command_revision"],
                    "provider_command_hash": payload["provider_command_hash"],
                    "cost_grant_id": payload["cost_grant_id"],
                    "reservation_id": payload["reservation_id"],
                    "secret_reference_id": payload["secret_reference_id"],
                    "rendered_payload_hash": payload["rendered_payload_hash"],
                    "transport_invocation_authorized": True,
                },
            ),
        ]
    grant = state["cost_grants"][payload["cost_grant_id"]]
    remaining = grant["available_cost_microunits"] + payload["refund_cost_microunits"]
    return [
        _event_envelope(
            envelope,
            command_schema,
            "ProviderReceiptRecorded",
            payload["provider_command_id"],
            {
                "provider_command_id": payload["provider_command_id"],
                "provider_receipt_id": payload["provider_receipt_id"],
                "provider_receipt_revision": payload["provider_receipt_revision"],
                "provider_receipt_hash": payload["provider_receipt_hash"],
                "cost_grant_id": payload["cost_grant_id"],
                "reservation_id": payload["reservation_id"],
                "provider_terminal_status": payload["provider_terminal_status"],
                "receipt_complete": True,
            },
        ),
        _event_envelope(
            envelope,
            command_schema,
            "CostGrantReconciled",
            payload["cost_grant_id"],
            {
                "cost_grant_id": payload["cost_grant_id"],
                "reservation_id": payload["reservation_id"],
                "provider_command_id": payload["provider_command_id"],
                "provider_receipt_id": payload["provider_receipt_id"],
                "actual_input_tokens": payload["actual_tokens"]["input_tokens"],
                "actual_output_tokens": payload["actual_tokens"]["output_tokens"],
                "actual_total_tokens": payload["actual_tokens"]["total_tokens"],
                "reserved_input_tokens": payload["reserved_token_ceilings"]["input_tokens"],
                "reserved_output_tokens": payload["reserved_token_ceilings"]["output_tokens"],
                "reserved_total_tokens": payload["reserved_token_ceilings"]["total_tokens"],
                "reserved_cost_microunits": payload["reserved_cost_microunits"],
                "consumed_cost_microunits": payload["consumed_cost_microunits"],
                "refund_cost_microunits": payload["refund_cost_microunits"],
                "refund_disposition": payload["refund_disposition"],
                "remaining_cost_microunits": remaining,
                "currency": payload["currency"],
                "rate_evidence_id": payload["rate_evidence_id"],
                "rate_evidence_revision": payload["rate_evidence_revision"],
                "rate_evidence_hash": payload["rate_evidence_hash"],
                "input_microunits_per_million_tokens": payload["input_microunits_per_million_tokens"],
                "output_microunits_per_million_tokens": payload["output_microunits_per_million_tokens"],
                "rate_mode": payload["rate_mode"],
                "zero_cost_authority": payload["zero_cost_authority"],
            },
        ),
    ]


def submit_t2(service: Any, raw_envelope: dict[str, Any]) -> T2Receipt:
    """Execute one closed T2 command with no provider or credential operation."""
    envelope = dict(raw_envelope)
    command_type = envelope.get("command_type")
    expected_schema = f"ars://wp6-2/t2/command/{command_type}"
    if command_type not in T2_COMMAND_TYPES:
        raise IntegrityError("unsupported T2 command type")
    command = _T2Command(envelope)
    with service._submission_lock(command) as submission:
        try:
            command_binding = service.schemas.command_binding(str(command_type))
            if command_binding is None:
                raise SchemaError(f"inactive T2 command binding: {command_type}")
            if (
                command_binding.schema_id,
                command_binding.schema_version,
            ) != (
                expected_schema,
                envelope.get("schema_version"),
            ):
                raise SchemaError(f"T2 command binding mismatch: {command_type}")
            command_schema = service.schemas.validate_active(
                command_binding.schema_id,
                envelope,
                schema_version=command_binding.schema_version,
            )
        except SchemaError:
            reason = (
                "provider_receipt_incomplete"
                if command_type == "RecordProviderReceipt"
                and isinstance(envelope.get("payload"), Mapping)
                and envelope["payload"].get("receipt_complete") is not True
                else "schema_identity_mismatch"
            )
            rejected = _receipt(envelope, "rejected", stable_reason=reason)
            service.schemas.validate("ars://core/receipt/v2", rejected.to_record())
            return service.receipts.write_t2(rejected)
        if envelope["schema_id"] != expected_schema:
            rejected = _receipt(envelope, "rejected", stable_reason="schema_identity_mismatch")
            service.schemas.validate("ars://core/receipt/v2", rejected.to_record())
            return service.receipts.write_t2(rejected)
        computed_hash = sha256_hex(canonical_bytes(envelope["payload"]))
        if computed_hash != envelope["payload_hash"]:
            rejected = _receipt(envelope, "rejected", stable_reason="schema_hash_mismatch")
            service.schemas.validate("ars://core/receipt/v2", rejected.to_record())
            return service.receipts.write_t2(rejected)
        snapshot = submission.snapshot
        from research_system.projection.replay import replay

        replay(
            snapshot.events,
            schema_registry=service.schemas,
            authority_state_validator=service._authority_state_validator(),
        )
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in snapshot.events:
            if str(event.get("schema_id", "")).startswith("ars://wp6-2/t2/event/"):
                batches.setdefault(event["transaction_id"], []).append(event)
        scope = (
            envelope["actor_id"],
            envelope["authority_scope"],
            command_type,
            command_schema.schema_id,
            command_schema.schema_version,
            command_schema.sha256,
            envelope["idempotency_key"],
        )
        stored = service.receipts.load_t2(command.command_id)
        if stored is not None:
            try:
                service.schemas.validate(
                    "ars://core/receipt/v2",
                    stored.to_record(),
                )
            except SchemaError as exc:
                raise IntegrityError("stored Receipt 2.0 is schema-invalid") from exc
            matching = next(
                (events for events in batches.values() if events[0]["command_id"] == command.command_id),
                None,
            )
            if stored.status == "accepted":
                if matching is None:
                    raise IntegrityError("stored accepted Receipt 2.0 has no ledger proof")
                reconstructed = _accepted_receipt(matching[0], matching)
                if stored.to_record() != reconstructed.to_record():
                    raise IntegrityError("stored Receipt 2.0 differs from ledger proof")
                first = matching[0]
                existing_scope = (
                    first["actor_id"],
                    first["authority_scope"],
                    first["command_type"],
                    first["command_schema_id"],
                    first["command_schema_version"],
                    first["command_schema_sha256"],
                    first["idempotency_key"],
                )
                if (
                    existing_scope != scope
                    or first["command_id"] != command.command_id
                    or first["payload_hash"] != command.payload_hash
                ):
                    return _receipt(
                        envelope,
                        "conflict",
                        stable_reason="idempotency_conflict",
                    )
                duplicate = _duplicate_receipt(stored)
                service.schemas.validate(
                    "ars://core/receipt/v2",
                    duplicate.to_record(),
                )
                return duplicate
            if (
                stored.record["command_type"] != command_type
                or stored.payload_hash != command.payload_hash
                or stored.record["idempotency_key_hash"] != sha256_hex(command.idempotency_key.encode("utf-8"))
            ):
                return _receipt(
                    envelope,
                    "conflict",
                    stable_reason="idempotency_conflict",
                )
            return stored
        for events in batches.values():
            first = events[0]
            existing_scope = (
                first["actor_id"],
                first["authority_scope"],
                first["command_type"],
                first["command_schema_id"],
                first["command_schema_version"],
                first["command_schema_sha256"],
                first["idempotency_key"],
            )
            if existing_scope == scope:
                if first["command_id"] == command.command_id and first["payload_hash"] == command.payload_hash:
                    accepted = _accepted_receipt(envelope, events)
                    persisted = service.receipts.load_t2(command.command_id)
                    if persisted is not None and persisted != accepted:
                        raise IntegrityError("stored Receipt 2.0 differs from ledger proof")
                    if persisted is None:
                        service.receipts.write_t2(accepted)
                    duplicate = _duplicate_receipt(accepted)
                    service.schemas.validate("ars://core/receipt/v2", duplicate.to_record())
                    return duplicate
                conflict = _receipt(envelope, "conflict", stable_reason="idempotency_conflict")
                service.schemas.validate("ars://core/receipt/v2", conflict.to_record())
                return service.receipts.write_t2(conflict)
            if first["command_id"] == command.command_id:
                conflict = _receipt(envelope, "conflict", stable_reason="idempotency_conflict")
                service.schemas.validate("ars://core/receipt/v2", conflict.to_record())
                return service.receipts.write_t2(conflict)
        common_error = _common_semantics(envelope)
        if common_error is not None:
            rejected = _receipt(envelope, "rejected", stable_reason=common_error)
            service.schemas.validate("ars://core/receipt/v2", rejected.to_record())
            return service.receipts.write_t2(rejected)
        state = _t2_projection(snapshot.events)
        if (
            command_type == "AuthorizeProviderIssue"
            and envelope["payload"]["cost_grant_id"] not in state["cost_grants"]
        ):
            rejected = _receipt(envelope, "rejected", stable_reason="cost_grant_missing")
            service.schemas.validate("ars://core/receipt/v2", rejected.to_record())
            return service.receipts.write_t2(rejected)
        for entry in envelope["write_set"]:
            observed = snapshot.stream_versions.get(entry["stream_id"], 0)
            if observed != entry["expected_stream_version"]:
                conflict = _receipt(envelope, "conflict", stable_reason="stale_stream_version")
                service.schemas.validate("ars://core/receipt/v2", conflict.to_record())
                return service.receipts.write_t2(conflict)
        now = service.clock()
        if command_type == "IssueCostGrant":
            semantic_error = _issue_semantics(service, envelope, now)
        elif command_type == "AuthorizeProviderIssue":
            semantic_error = _authorize_semantics(service, envelope, state, now)
        else:
            semantic_error = _record_semantics(service, envelope, state)
        if semantic_error is not None:
            rejected = _receipt(envelope, "rejected", stable_reason=semantic_error)
            service.schemas.validate("ars://core/receipt/v2", rejected.to_record())
            return service.receipts.write_t2(rejected)
        proposed = _events_for(envelope, state, command_schema)
        ledger_result = service.ledger.append(proposed, snapshot=snapshot)
        service._retire_moved_restore_preflight()
        updated = service.ledger.snapshot()
        committed = list(updated.events[len(snapshot.events) :])
        if tuple(event["event_type"] for event in committed) != _EVENT_ORDER[command_type]:
            raise IntegrityError("T2 event batch order invalid")
        if ledger_result["event_batch_id"] != committed[0]["transaction_id"]:
            raise IntegrityError("T2 ledger receipt mismatch")
        accepted = _accepted_receipt(envelope, committed)
        service.schemas.validate("ars://core/receipt/v2", accepted.to_record())
        return service.receipts.write_t2(accepted)
