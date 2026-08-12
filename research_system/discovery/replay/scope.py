"""The per-event replay scope handed to exactly one owning reducer.

`replay_discovery` owns the mutable projection and the transaction-join helpers.
A reducer never reaches around this object: everything it may read is named here,
so a reducer's dependencies are visible in its own prologue instead of being
captured implicitly from a two-thousand-line enclosing function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from research_system.schema_registry import SchemaRegistry


@dataclass(frozen=True)
class EventScope:
    """One persisted Discovery event plus the shared state its reducer may touch."""

    state: dict[str, Any]
    event: dict[str, Any]
    payload: dict[str, Any]
    event_type: str
    active_schemas: SchemaRegistry
    transaction_events: dict[Any, list[dict[str, Any]]]
    operational_events: list[dict[str, Any]]
    canonical_artefact_streams: dict[str, dict[str, Any]]
    required_string: Callable[[str], str]
    required_int: Callable[[str], int]
    required_string_list: Callable[[str], list[str]]
    aggregate_identity_exists: Callable[..., bool]
    claim_authority_stream: Callable[..., None]
    candidate_spike_link_matches: Callable[..., bool]
    preceding_transaction_event_matches: Callable[..., bool]
    following_transaction_event_matches: Callable[..., bool]
    candidate_assay_link_matches: Callable[..., bool]
    candidate_spike_plan_link_matches: Callable[..., bool]
    spike_operational_closure_matches: Callable[..., bool]
    dossier_materialization_transaction_matches: Callable[..., bool]
