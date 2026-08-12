"""Shared Discovery command-family identity.

The control-plane and Discovery projections share one atomic event ledger.  This
closed set lets each projection validate the common envelope and then route the
event to exactly one semantic reducer without importing the Discovery runtime.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


DISCOVERY_COMMAND_TYPES = frozenset(
    {
        "ImportAcceptedW11CatalogueGenesis",
        "IngestScoutObservationBatch",
        "RegisterCandidate",
        "SupersedeDiscoveryRecord",
        "RequestAssay",
        "RecordAssayScore",
        "RecordAssayPartial",
        "CancelDiscoveryEvaluation",
        "ProposeRevisitDecision",
        "RequestDiscoveryOutcomeReview",
        "ReviewDiscoveryOutcome",
        "ProposePromotionDecision",
        "RegisterSpikePlan",
        "ProposeSpikeExecutionDecision",
        "StartSpike",
        "RecordSpikeVerdict",
        "RegisterAssayRubricContent",
        "RegisterAssayEvidenceScopeContent",
        "RecordAssayBarStaleness",
        "RegisterDossierExpectedSetContent",
        "RegisterPathRegistrationContent",
        "ObserveW11AuthorityFile",
        "RequestW11AuthorityReview",
        "RecordW11AuthorityReview",
        "ProposeW11AuthorityDecision",
        "ResolveDecision",
        "AdmitResearchDossier",
    }
)
DISCOVERY_RESOLVE_ROWS = frozenset({"OR-010", "OR-013", "OR-016", "OR-024", "OR-027", "OR-108", "OR-115", "OR-121"})


def discovery_resolve_transaction_ids(events: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    """Identify exact multi-event Discovery ``ResolveDecision`` transactions."""

    transaction_ids: set[str] = set()
    for event in events:
        if event.get("command_type") != "ResolveDecision":
            continue
        payload = event.get("payload")
        transaction_id = event.get("transaction_id")
        owner_row_id = payload.get("owner_row_id") if isinstance(payload, Mapping) else None
        command_row_id = payload.get("row_id") if isinstance(payload, Mapping) else None
        if (
            isinstance(payload, Mapping)
            and (owner_row_id in DISCOVERY_RESOLVE_ROWS or command_row_id in DISCOVERY_RESOLVE_ROWS)
            and isinstance(transaction_id, str)
        ):
            transaction_ids.add(transaction_id)
    return frozenset(transaction_ids)


def is_discovery_projection_event(
    event: Mapping[str, Any],
    *,
    resolve_transaction_ids: frozenset[str] = frozenset(),
) -> bool:
    """Return whether the event belongs to the Discovery semantic reducer.

    OR-019 deliberately emits ``PartialOutcomeRecorded`` and ``LeaseReleased``
    under a Discovery command in the same transaction. Those two events remain
    owned by the operational reducer.
    """

    command_type = event.get("command_type")
    event_type = event.get("event_type")
    if event_type in {"PartialOutcomeRecorded", "LeaseReleased"}:
        return False
    if command_type not in DISCOVERY_COMMAND_TYPES:
        return False
    if command_type != "ResolveDecision":
        return True
    return event.get("transaction_id") in resolve_transaction_ids
