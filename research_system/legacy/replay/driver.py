"""Deterministic W9 legacy replay.

``replay_legacy`` reduces the W9 half of the shared ledger. The generic boundary calls it after the shared-ledger
envelope, schema, hash-chain, stream-version and transaction checks (U-7 site 4), and ``LegacyRuntime`` calls it before
every command. It owns the W9 semantics the generic replay does not check:

- every W9 event's command is a W9 command, and every W9 command's events are W9 or W2 events (design note §2.1);
- each transaction is assigned to exactly one accepted row (§4), and a deferred row is refused (§3);
- each transaction's event types are its row's accepted ordered events;
- each ``E:`` payload validates against its row's record schema through the registry (P-069 item 2), and each W2
  event is recorded under its own W2 schema (C2);
- no W9 payload names a W11 owner row (C3);
- the reducers' invariants (§7.4).
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from typing import Any

from research_system.errors import IntegrityError, SchemaError
from research_system.legacy.accepted_w9 import ACCEPTED_REVISIONS
from research_system.legacy.commands import LEGACY_COMMAND_TYPES, is_legacy_projection_event
from research_system.legacy.replay.reducers import REDUCERS, new_legacy_state
from research_system.legacy.routes import (
    LEGACY_DEFERRED_ROWS,
    LEGACY_EVENT_TYPES,
    LEGACY_ROUTED_ROWS,
    LEGACY_ROW_ROUTES,
    W2_EVENT_TYPES,
    assign_row,
    validate_transaction_shape,
)
from research_system.schema_registry import SchemaRegistry


def _refuse_w11_row(payload: Mapping[str, Any]) -> None:
    """C3: no W9 payload names a W11 owner row where Discovery's row reader looks (design note §2.3)."""

    for key in ("owner_row_id", "row_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith("OR-"):
            raise IntegrityError("W9 payload names a W11 owner row")
    for key in ("governing_refs", "governing_evidence_refs"):
        refs = payload.get(key)
        if isinstance(refs, list) and any(isinstance(ref, str) and ref.startswith("W11:OR-") for ref in refs):
            raise IntegrityError("W9 payload names a W11 owner row")


# The one E: event whose record schema is not its row's: LR-020 writes ownership transitions beside its acceptance.
_EVENT_RECORD_SCHEMAS = {"LegacyOwnershipTransitionedRecorded": "ars://legacy/legacy-ownership-transitioned"}


def _validate_payload(event: Mapping[str, Any], record_schema_id: str, schemas: SchemaRegistry) -> None:
    event_type = event.get("event_type")
    if event_type in W2_EVENT_TYPES:
        if event.get("schema_id") != f"ars://core/event/{event_type}":
            raise IntegrityError("W9 W2 event is recorded under another schema")
        return
    if (event.get("schema_id"), event.get("schema_version")) != ("ars://core/event", "1.0.0"):
        raise IntegrityError("W9 event is recorded under another schema")
    try:
        schemas.validate(
            _EVENT_RECORD_SCHEMAS.get(str(event_type), record_schema_id), event.get("payload"), schema_version="1.0.0"
        )
    except SchemaError as exc:
        raise IntegrityError("W9 event payload does not validate against its record schema") from exc


def _transactions(ordered: tuple[Mapping[str, Any], ...]) -> list[tuple[Mapping[str, Any], ...]]:
    """Group the W9 events into their ledger transactions, refusing a transaction that mixes command families."""

    members: dict[Any, list[Mapping[str, Any]]] = {}
    order: list[Any] = []
    for event in ordered:
        transaction_id = event.get("transaction_id")
        if transaction_id not in members:
            members[transaction_id] = []
            order.append(transaction_id)
        members[transaction_id].append(event)
    transactions = []
    for transaction_id in order:
        events = members[transaction_id]
        legacy = [is_legacy_projection_event(event) for event in events]
        if not any(legacy):
            continue
        if not all(legacy) or len({event.get("command_id") for event in events}) != 1:
            raise IntegrityError("W9 transaction mixes commands or command families")
        transactions.append(tuple(events))
    return transactions


def replay_legacy(
    events: Iterable[Mapping[str, Any]],
    *,
    schemas: SchemaRegistry | None = None,
    routed_rows: Collection[str] = LEGACY_ROUTED_ROWS,
    accepted_revisions: Collection[Mapping[str, Any]] = ACCEPTED_REVISIONS,
) -> dict[str, Any]:
    """Rebuild the W9 legacy projection while rejecting malformed W9 transitions.

    Args:
        events: The ordered persisted events of the whole shared ledger.
        schemas: The schema registry for payload validation; the bundled registry when omitted.
        routed_rows: The rows this code routes. Production routes LR-001 only (design note §3); tests pass a wider set
            to exercise the deferred rows' reducers.
        accepted_revisions: The accepted catalogue revisions LR-002 may import. None exists in v1.

    Returns:
        The legacy projection.

    Raises:
        IntegrityError: If any W9 event, transaction or transition is malformed.
    """

    ordered = tuple(events)
    if schemas is None:
        from research_system.discovery.ledger_integrity import _default_replay_schemas

        schemas = _default_replay_schemas()
    for event in ordered:
        if event.get("event_type") in LEGACY_EVENT_TYPES and event.get("command_type") not in LEGACY_COMMAND_TYPES:
            raise IntegrityError("W9 event type under a non-W9 command")
    first_w11_genesis = next(
        (
            index
            for index, event in enumerate(ordered)
            if event.get("command_type") == "ImportAcceptedW11CatalogueGenesis"
            and event.get("event_type") == "W11CatalogueGenesisImported"
        ),
        None,
    )
    position_of = {id(event): index for index, event in enumerate(ordered)}
    state = new_legacy_state()
    review_request_rows: dict[str, str] = {}
    for transaction in _transactions(ordered):
        command_type = transaction[0].get("command_type")
        row_id = assign_row(transaction, review_request_rows)
        if row_id not in routed_rows:
            tag = LEGACY_DEFERRED_ROWS.get(row_id, "unrouted")
            raise IntegrityError(f"W9 row not routed in this version: {row_id} ({tag})")
        route = LEGACY_ROW_ROUTES[row_id]
        validate_transaction_shape(row_id, [str(event.get("event_type")) for event in transaction])
        for event in transaction:
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                raise IntegrityError("W9 event payload must be an object")
            _refuse_w11_row(payload)
            _validate_payload(event, route.record_schema_id, schemas)
        if command_type != "ImportAcceptedW9CatalogueGenesis" and state["catalogue"] is None:
            raise IntegrityError(f"W9 genesis is required before {row_id}")
        context = {
            "w11_genesis_seen": first_w11_genesis is not None and first_w11_genesis < position_of[id(transaction[0])],
            "accepted_revisions": accepted_revisions,
        }
        REDUCERS[str(command_type)](state, row_id, transaction, context)
        if command_type == "RequestW9AuthorityReview":
            review_request_rows[transaction[0]["payload"]["new_review_id"]] = row_id
        state["row_counts"][row_id] = state["row_counts"].get(row_id, 0) + 1
    return state
