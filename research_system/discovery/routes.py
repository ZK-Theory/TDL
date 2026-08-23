"""Immutable Discovery route registry and shared-ledger partition.

This module owns the mapping from an accepted W11 catalogue row to the exact
producer command and ordered event set that may execute it, the disjoint
partition of the shared ledger into Discovery / artefact / operational replay,
and the single global immutable-identity contract.

It is a leaf: it may import the accepted envelope identity and the shared command
family, and nothing else in :mod:`research_system.discovery`.  Dispatch is
derived here from the accepted row and the exact producer command, never from
caller-controlled payload shape, so no other module needs to restate a route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_system.command.models import Command
from research_system.discovery.accepted_w11 import CATALOGUE_STREAM_ID
from research_system.discovery.commands import is_discovery_projection_event
from research_system.errors import IntegrityError


ARTEFACT_EVENT_TYPES = {
    "ArtefactRegistered",
    "ArtefactAvailabilityRecorded",
    "ArtefactRegenerabilityRecorded",
    "ArtefactIntegrityRecorded",
    "StructuralValidationRecorded",
    "ScientificReviewRecorded",
    "ArtefactUseAuthoritySet",
    "ArtefactSuperseded",
    "LateArtefactAdopted",
}
CONTEXT_EVENT_TYPES = {
    "ContextPacketRequested",
    "ContextCompilationStarted",
    "ContextPacketCompiled",
    "ContextPacketValidated",
    "ContextPacketIssued",
    "ContextPacketDelivered",
    "ContextPacketFailed",
    "ContextPacketExpired",
    "ContextPacketSuperseded",
}
CONTROL_EVENT_TYPES = {
    "AuthorityRootInitialized",
    "AuthorityGrantActivated",
    "AuthorityGrantRevoked",
    "StoreBindingRepaired",
    "StoreBindingAdvanced",
}


@dataclass(frozen=True)
class DiscoveryRowRoute:
    """One executable accepted-catalogue route and its owning preparer family."""

    command_type: str
    family: str
    catalogue_events: tuple[str, ...]


DISCOVERY_EXCLUDED_ROWS = frozenset({"OR-031", "OR-032", "OR-033"} | {f"OR-{number:03d}" for number in range(122, 140)})
DISCOVERY_DEFERRED_ROWS = {
    "OR-030": "WP6.7 annotation-epoch contract and initial authority activation",
}
DISCOVERY_ROW_ROUTES = {
    "OR-001": DiscoveryRowRoute("RegisterCandidate", "candidate", ("CandidateRegistered",)),
    "OR-002": DiscoveryRowRoute("SupersedeDiscoveryRecord", "supersede", ("CandidateSuperseded",)),
    "OR-003": DiscoveryRowRoute(
        "RequestAssay", "assay", ("AssayRequested", "AssayEvidenceCollectionOpened", "CandidateAssayRequested")
    ),
    "OR-004": DiscoveryRowRoute("RecordAssayScore", "assay", ("AssayScored", "CandidateAssayLinked")),
    "OR-005": DiscoveryRowRoute("RecordAssayPartial", "assay", ("AssayPartialRecorded", "CandidateAssayPartialLinked")),
    "OR-006": DiscoveryRowRoute("ReviewDiscoveryOutcome", "assay", ("ReviewVerdictRecorded", "AssayReviewed")),
    "OR-007": DiscoveryRowRoute(
        "ReviewDiscoveryOutcome",
        "assay",
        ("ReviewVerdictRecorded", "AssayPartialReviewed", "CandidateAssayPartialReviewed"),
    ),
    "OR-008": DiscoveryRowRoute(
        "CancelDiscoveryEvaluation", "assay", ("AssayCancelled", "CandidateEvaluationCancelled")
    ),
    "OR-009": DiscoveryRowRoute(
        "ProposeRevisitDecision",
        "assay",
        ("DecisionProposed", "AssayRevisitRequested", "CandidateRevisitRequested/assay"),
    ),
    "OR-010": DiscoveryRowRoute(
        "ResolveDecision", "assay", ("DecisionResolved", "AssayRevisitResolved", "CandidateRevisitResolved/assay")
    ),
    "OR-011": DiscoveryRowRoute("RequestAssay", "assay", ("AssaySuperseded", "CandidateAssayRetryStarted")),
    "OR-012": DiscoveryRowRoute(
        "ProposePromotionDecision", "spike", ("DecisionProposed", "CandidatePromotionRequested")
    ),
    "OR-013": DiscoveryRowRoute("ResolveDecision", "spike", ("DecisionResolved", "CandidatePromotionApplied")),
    "OR-014": DiscoveryRowRoute(
        "RegisterSpikePlan", "spike", ("SpikePlanned", "SpikeApprovalRequested", "CandidateSpikePlanLinked")
    ),
    "OR-015": DiscoveryRowRoute(
        "ProposeSpikeExecutionDecision", "spike", ("DecisionProposed", "SpikeExecutionDecisionRequested")
    ),
    "OR-016": DiscoveryRowRoute(
        "ResolveDecision", "spike", ("DecisionResolved", "SpikeAuthorized", "CandidateSpikeAuthorized")
    ),
    "OR-017": DiscoveryRowRoute("StartSpike", "spike", ("SpikeStarted", "CandidateSpikeStarted")),
    "OR-018": DiscoveryRowRoute("RecordSpikeVerdict", "spike", ("SpikeVerdictRecorded", "CandidateSpikeVerdictLinked")),
    "OR-019": DiscoveryRowRoute(
        "RecordSpikeVerdict",
        "spike",
        ("SpikePartialRecorded", "SpikeAttemptClosed/partial", "CandidateSpikePartialLinked"),
    ),
    "OR-020": DiscoveryRowRoute("ReviewDiscoveryOutcome", "spike", ("ReviewVerdictRecorded", "SpikeReviewed")),
    "OR-021": DiscoveryRowRoute(
        "ReviewDiscoveryOutcome",
        "spike",
        ("ReviewVerdictRecorded", "SpikePartialReviewed", "CandidateSpikePartialReviewed"),
    ),
    "OR-022": DiscoveryRowRoute(
        "CancelDiscoveryEvaluation",
        "spike",
        (
            "SpikeCancelled",
            "SpikeAttemptClosed/cancelled",
            "SpikeExecutionProposalSupersededByCancellation",
            "CandidateEvaluationCancelled/spike",
        ),
    ),
    "OR-023": DiscoveryRowRoute(
        "ProposeRevisitDecision",
        "spike",
        ("DecisionProposed", "SpikeRevisitRequested", "CandidateRevisitRequested/spike"),
    ),
    "OR-024": DiscoveryRowRoute(
        "ResolveDecision", "spike", ("DecisionResolved", "SpikeRevisitResolved", "CandidateRevisitResolved/spike")
    ),
    "OR-025": DiscoveryRowRoute("RegisterSpikePlan", "spike", ("SpikeSuperseded", "CandidateSpikeRetryStarted")),
    "OR-026": DiscoveryRowRoute(
        "ProposePromotionDecision", "spike", ("DecisionProposed", "CandidatePromotionRequested")
    ),
    "OR-027": DiscoveryRowRoute("ResolveDecision", "spike", ("DecisionResolved", "CandidatePromotionApplied")),
    "OR-028": DiscoveryRowRoute(
        "AdmitResearchDossier",
        "dossier",
        ("ResearchDossierAdmitted", "PortfolioObjectRegistered", "ScopeDefinitionRegistered"),
    ),
    "OR-029": DiscoveryRowRoute(
        "IngestScoutObservationBatch", "scout", ("ScoutObservationIngested", "CandidateRegistered")
    ),
    "OR-034": DiscoveryRowRoute("RequestDiscoveryOutcomeReview", "assay", ("ReviewRequested", "AssayReviewRequested")),
    "OR-035": DiscoveryRowRoute(
        "RequestDiscoveryOutcomeReview", "assay", ("ReviewRequested", "AssayPartialReviewRequested")
    ),
    "OR-036": DiscoveryRowRoute("RequestDiscoveryOutcomeReview", "spike", ("ReviewRequested", "SpikeReviewRequested")),
    "OR-037": DiscoveryRowRoute(
        "RequestDiscoveryOutcomeReview", "spike", ("ReviewRequested", "SpikePartialReviewRequested")
    ),
    "OR-038": DiscoveryRowRoute(
        "RequestDiscoveryOutcomeReview", "assay", ("ReviewRequested", "AssayCancellationReviewRequested")
    ),
    "OR-039": DiscoveryRowRoute(
        "ReviewDiscoveryOutcome",
        "assay",
        ("ReviewVerdictRecorded", "AssayCancellationReviewed", "CandidateAssayCancellationReviewed"),
    ),
    "OR-040": DiscoveryRowRoute(
        "RequestDiscoveryOutcomeReview", "spike", ("ReviewRequested", "SpikeCancellationReviewRequested")
    ),
    "OR-041": DiscoveryRowRoute(
        "ReviewDiscoveryOutcome",
        "spike",
        ("ReviewVerdictRecorded", "SpikeCancellationReviewed", "CandidateSpikeCancellationReviewed"),
    ),
    "OR-101": DiscoveryRowRoute("RegisterAssayRubricContent", "assay_authority", ("AssayRubricContentRegistered",)),
    "OR-102": DiscoveryRowRoute(
        "RegisterAssayEvidenceScopeContent", "assay_authority", ("AssayEvidenceScopeContentRegistered",)
    ),
    "OR-103": DiscoveryRowRoute("ObserveW11AuthorityFile", "assay_authority", ("W11AuthorityFileObserved",)),
    "OR-104": DiscoveryRowRoute("ObserveW11AuthorityFile", "assay_authority", ("W11AuthorityFileObserved",)),
    "OR-105": DiscoveryRowRoute("RequestW11AuthorityReview", "assay_authority", ("ReviewRequested",)),
    "OR-106": DiscoveryRowRoute("RecordW11AuthorityReview", "assay_authority", ("ReviewVerdictRecorded",)),
    "OR-107": DiscoveryRowRoute("ProposeW11AuthorityDecision", "assay_authority", ("DecisionProposed",)),
    "OR-108": DiscoveryRowRoute("ResolveDecision", "assay_authority", ("DecisionResolved", "AssayBarAccepted")),
    "OR-109": DiscoveryRowRoute("RecordAssayBarStaleness", "assay_authority", ("AssayBarStaled",)),
    "OR-110": DiscoveryRowRoute(
        "RegisterDossierExpectedSetContent", "authority", ("DossierExpectedSetContentRegistered",)
    ),
    "OR-111": DiscoveryRowRoute(
        "ObserveW11AuthorityFile", "authority", ("W11AuthorityFileObserved/dossier_expected_set",)
    ),
    "OR-112": DiscoveryRowRoute("RequestW11AuthorityReview", "authority", ("ReviewRequested",)),
    "OR-113": DiscoveryRowRoute("RecordW11AuthorityReview", "authority", ("ReviewVerdictRecorded",)),
    "OR-114": DiscoveryRowRoute("ProposeW11AuthorityDecision", "authority", ("DecisionProposed",)),
    "OR-115": DiscoveryRowRoute("ResolveDecision", "authority", ("DecisionResolved", "DossierExpectedSetAccepted")),
    "OR-116": DiscoveryRowRoute("RegisterPathRegistrationContent", "authority", ("PathRegistrationContentRegistered",)),
    "OR-117": DiscoveryRowRoute(
        "ObserveW11AuthorityFile", "authority", ("W11AuthorityFileObserved/path_registration",)
    ),
    "OR-118": DiscoveryRowRoute("RequestW11AuthorityReview", "authority", ("ReviewRequested",)),
    "OR-119": DiscoveryRowRoute("RecordW11AuthorityReview", "authority", ("ReviewVerdictRecorded",)),
    "OR-120": DiscoveryRowRoute("ProposeW11AuthorityDecision", "authority", ("DecisionProposed",)),
    "OR-121": DiscoveryRowRoute("ResolveDecision", "authority", ("DecisionResolved", "PathRegistrationAccepted")),
    "OR-140": DiscoveryRowRoute("ImportAcceptedW11CatalogueGenesis", "genesis", ("W11CatalogueGenesisImported",)),
}
DISCOVERY_AUTHORITY_SHADOWS = {
    "OR-101": ("assay_bar", "AssayRubricContentRegistered"),
    "OR-102": ("assay_bar", "AssayEvidenceScopeContentRegistered"),
    "OR-103": ("assay_bar", "W11AuthorityFileObserved"),
    "OR-104": ("assay_bar", "W11AuthorityFileObserved"),
    "OR-108": ("assay_bar", "AssayBarAccepted"),
    "OR-109": ("assay_bar", "AssayBarStaled"),
    "OR-110": ("dossier_expected_set", "DossierExpectedSetContentRegistered"),
    "OR-111": ("dossier_expected_set", "W11AuthorityFileObserved"),
    "OR-115": ("dossier_expected_set", "DossierExpectedSetAccepted"),
    "OR-116": ("path_registration", "PathRegistrationContentRegistered"),
    "OR-117": ("path_registration", "W11AuthorityFileObserved"),
    "OR-121": ("path_registration", "PathRegistrationAccepted"),
}
DISCOVERY_MINT_ROWS = frozenset(
    {
        "OR-001",
        "OR-003",
        "OR-009",
        "OR-011",
        "OR-012",
        "OR-014",
        "OR-015",
        "OR-023",
        "OR-025",
        "OR-026",
        "OR-028",
        "OR-029",
        "OR-034",
        "OR-035",
        "OR-036",
        "OR-037",
        "OR-038",
        "OR-040",
        "OR-101",
        "OR-102",
        "OR-105",
        "OR-107",
        "OR-110",
        "OR-112",
        "OR-114",
        "OR-116",
        "OR-118",
        "OR-120",
        "OR-140",
    }
)
DISCOVERY_EXISTING_TARGETS = {
    **dict.fromkeys(("OR-002",), "candidates"),
    **dict.fromkeys(("OR-004", "OR-005", "OR-008"), "assays"),
    **dict.fromkeys(("OR-006", "OR-007", "OR-020", "OR-021", "OR-039", "OR-041"), "reviews"),
    **dict.fromkeys(("OR-010", "OR-013", "OR-016", "OR-024", "OR-027"), "decisions"),
    **dict.fromkeys(("OR-017", "OR-018", "OR-019", "OR-022"), "spikes"),
    **dict.fromkeys(
        (
            "OR-103",
            "OR-104",
            "OR-106",
            "OR-108",
            "OR-109",
            "OR-111",
            "OR-113",
            "OR-115",
            "OR-117",
            "OR-119",
            "OR-121",
        ),
        "authority_streams",
    ),
}
DISCOVERY_IDENTITY_COLLECTIONS = (
    "source_observations",
    "candidates",
    "assays",
    "spikes",
    "decisions",
    "reviews",
    "dossiers",
    "portfolio_objects",
    "scopes",
    "artefact_streams",
    "authority_streams",
)


def discovery_identity_exists(state: Mapping[str, Any], identity: Any) -> bool:
    """Apply the single global immutable-identity contract to every aggregate kind."""

    return bool(
        identity == CATALOGUE_STREAM_ID
        or any(identity in state.get(collection, {}) for collection in DISCOVERY_IDENTITY_COLLECTIONS)
    )


def shared_event_partition(
    event: Mapping[str, Any],
    *,
    resolve_transaction_ids: frozenset[str] = frozenset(),
) -> str:
    """Assign every shared-ledger event to exactly one replay reducer."""

    event_type = event.get("event_type")
    if event_type in {"PartialOutcomeRecorded", "LeaseReleased"}:
        return "operational"
    if is_discovery_projection_event(event, resolve_transaction_ids=resolve_transaction_ids):
        return "discovery"
    if event_type in ARTEFACT_EVENT_TYPES:
        return "artefact"
    if event_type in CONTEXT_EVENT_TYPES:
        return "context"
    if event_type in CONTROL_EVENT_TYPES:
        return "control"
    return "operational"


def catalogue_event_name(value: Any) -> str:
    """Normalize one accepted W11 event token for route-registry comparison."""

    if not isinstance(value, str) or ":" not in value:
        raise IntegrityError("accepted W11 row contains an invalid event token")
    prefix, name = value.split(":", 1)
    if prefix == "W2":
        return name
    if prefix != "E":
        raise IntegrityError("accepted W11 row contains an unknown event namespace")
    base, separator, suffix = name.partition("/")
    normalized = "".join(part.capitalize() for part in base.split("-") if part)
    return f"{normalized}/{suffix}" if separator else normalized


def validate_discovery_route_registry(catalogue: Mapping[str, Any]) -> None:
    """Prove the production route registry is an exact partition of accepted W11."""

    rows = catalogue.get("owner_contract_rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise IntegrityError("accepted W11 catalogue rows are invalid")
    by_id = {row.get("owner_row_id"): row for row in rows}
    if (
        len(by_id) != 81
        or len(DISCOVERY_ROW_ROUTES) != 59
        or len(DISCOVERY_EXCLUDED_ROWS) != 21
        or len(DISCOVERY_DEFERRED_ROWS) != 1
        or set(DISCOVERY_ROW_ROUTES) & (DISCOVERY_EXCLUDED_ROWS | set(DISCOVERY_DEFERRED_ROWS))
        or DISCOVERY_EXCLUDED_ROWS & set(DISCOVERY_DEFERRED_ROWS)
        or set(DISCOVERY_ROW_ROUTES) | DISCOVERY_EXCLUDED_ROWS | set(DISCOVERY_DEFERRED_ROWS) != set(by_id)
        or DISCOVERY_MINT_ROWS & set(DISCOVERY_EXISTING_TARGETS)
        or DISCOVERY_MINT_ROWS | set(DISCOVERY_EXISTING_TARGETS) != set(DISCOVERY_ROW_ROUTES)
    ):
        raise IntegrityError("Discovery route registry does not partition accepted W11")
    for row_id, route in DISCOVERY_ROW_ROUTES.items():
        row = by_id[row_id]
        ordered_events = row.get("ordered_events")
        if (
            row.get("command_type") != route.command_type
            or not isinstance(ordered_events, list)
            or tuple(catalogue_event_name(value) for value in ordered_events) != route.catalogue_events
        ):
            raise IntegrityError(f"Discovery route registry differs from accepted {row_id}")
    deferred = by_id["OR-030"]
    deferred_events = deferred.get("ordered_events")
    if (
        deferred.get("command_type") != "IngestDiscoveryAnnotation"
        or not isinstance(deferred_events, list)
        or tuple(catalogue_event_name(value) for value in deferred_events) != ("DiscoveryAnnotationIngested",)
    ):
        raise IntegrityError("Discovery deferred route differs from accepted OR-030")


def discovery_route(command: Command) -> tuple[str, DiscoveryRowRoute]:
    """Resolve dispatch exclusively from the accepted row and exact producer command."""

    command_type = command.envelope["command_type"]
    if command_type == "ImportAcceptedW11CatalogueGenesis":
        row_id = "OR-140"
    elif command_type == "RegisterCandidate":
        row_id = "OR-001"
    else:
        row_id = command.envelope["payload"].get("row_id")
    route = DISCOVERY_ROW_ROUTES.get(row_id)
    if route is None or route.command_type != command_type:
        raise IntegrityError("Discovery command does not match an executable accepted W11 row")
    return str(row_id), route
