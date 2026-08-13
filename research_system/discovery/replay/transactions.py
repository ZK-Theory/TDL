"""Shared exact-transaction contracts for Discovery replay.

The event ledger guarantees that a transaction is contiguous and consistently
provenanced.  This module owns the next semantic layer: a W11 command's
complete ordered write set.  Reducers may still validate their own state
transition, but may not treat a surviving subset of a multi-stream command as
an independently valid command.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.replay.scope import EventScope
from research_system.errors import IntegrityError


# These contracts state facts absent from ``ordered_events`` alone: internal
# operational events, stream ownership and the complete atomic batch.  They
# deliberately sit apart from the producers and reducers, so neither can
# certify a transaction against itself.
_EXACT_WRITE_SETS: dict[str, tuple[str, ...]] = {
    "OR-003": ("AssayRequested", "AssayEvidenceCollectionOpened", "CandidateAssayRequested"),
    "OR-011": (
        "AssayRequested",
        "AssayEvidenceCollectionOpened",
        "AssaySuperseded",
        "CandidateAssayRetryStarted",
    ),
    "OR-014": ("SpikePlanned", "SpikeApprovalRequested", "CandidateSpikePlanLinked"),
}


def _owner_row_id(events: Sequence[Mapping[str, Any]]) -> str | None:
    """Resolve the one W11 owner row carried by a durable transaction."""

    rows: set[str] = set()
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        row_id = payload.get("owner_row_id", payload.get("row_id"))
        if isinstance(row_id, str):
            rows.add(row_id)
    return next(iter(rows)) if len(rows) == 1 else None


def _assert_exact_event_types(events: Sequence[Mapping[str, Any]], expected: tuple[str, ...], row_id: str) -> None:
    """Reject a deleted, added, reordered or substituted write-set member."""

    actual = tuple(str(event.get("event_type")) for event in events)
    if actual != expected:
        raise IntegrityError(f"Discovery transaction write set mismatch for {row_id}")


def _assert_same_payload_and_streams(
    events: Sequence[Mapping[str, Any]],
    *,
    streams: tuple[str, ...],
    row_id: str,
) -> Mapping[str, Any] | None:
    """Bind each member to the same command payload and declared stream fields."""

    first = events[0].get("payload")
    if not isinstance(first, Mapping):
        return None
    for event, field in zip(events, streams, strict=True):
        payload = event.get("payload")
        if not isinstance(payload, Mapping) or payload != first or event.get("stream_id") != first.get(field):
            # The owning reducer preserves its precise domain error for an
            # incomplete single-member mutation.  This contract must instead
            # catch a coordinated rewrite that keeps the batch internally
            # coherent but no longer matches the submitted command digest.
            return None
    return first


def _assert_command_payload_hash(payload: Mapping[str, Any], command_payload_hash: object, *, row_id: str) -> None:
    """Bind a persisted transaction back to its submitted command payload."""

    command_payload = deepcopy(dict(payload))
    # Producer-only fields are derived from the accepted Assay-bar relation and
    # are not part of RequestAssay's public command schema.
    command_payload.pop("producer_actor_id", None)
    if (
        not isinstance(command_payload_hash, str)
        or sha256_hex(canonical_bytes(command_payload)) != command_payload_hash
    ):
        raise IntegrityError(f"Discovery command payload mismatch for {row_id}")


def validate_transaction_contract(events: Sequence[Mapping[str, Any]]) -> None:
    """Validate the static W11 transaction contract before reducer dispatch.

    Transactions outside the currently declarative set are intentionally left
    to their owning reducer contracts.  The registry is additive: each new
    multi-event row is added here with its complete write set rather than by
    another one-sided reducer check.
    """

    if not events:
        return
    row_id = _owner_row_id(events)
    if row_id not in _EXACT_WRITE_SETS:
        return
    _assert_exact_event_types(events, _EXACT_WRITE_SETS[row_id], row_id)
    if row_id == "OR-003":
        payload = _assert_same_payload_and_streams(
            events, streams=("assay_id", "assay_id", "candidate_id"), row_id=row_id
        )
    elif row_id == "OR-011":
        payload = _assert_same_payload_and_streams(
            events,
            streams=("assay_id", "assay_id", "old_assay_id", "candidate_id"),
            row_id=row_id,
        )
    else:
        payload = _assert_same_payload_and_streams(
            events, streams=("spike_id", "spike_id", "candidate_id"), row_id=row_id
        )
    if payload is not None:
        _assert_command_payload_hash(payload, events[0].get("command_payload_hash"), row_id=row_id)


def validate_prepared_transaction_contract(
    row_id: str,
    command_payload_hash: str,
    prepared: Sequence[tuple[str, str, Mapping[str, Any]]],
) -> None:
    """Apply the same contract to a producer batch before ledger append."""

    events = tuple(
        {
            "event_type": event_type,
            "stream_id": stream_id,
            "command_payload_hash": command_payload_hash,
            "payload": payload,
        }
        for event_type, stream_id, payload in prepared
    )
    validate_transaction_contract(events)


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
