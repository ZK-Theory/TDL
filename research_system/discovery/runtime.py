from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from research_system.authority import GrantedCommandIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command, Receipt
from research_system.command.reducers import reduce_artefact, replay_control_plane
from research_system.discovery.authority import prepare_authority_transition, replay_authority
from research_system.discovery.assay_authority import (
    content_sha256 as assay_content_sha256,
    replay_assay_bar_authority,
)
from research_system.discovery.commands import (
    DISCOVERY_COMMAND_TYPES,
    discovery_resolve_transaction_ids,
    is_discovery_projection_event,
)
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierAdmissionRejected,
    DossierMember,
    RegisteredRoot,
    accepted_expected_set_hash,
    admission_profile_hash,
    canonical_dossier_hash,
    prepare_dossier_admission,
)
from research_system.errors import ConflictError, IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.lock import CompositeWriterLock, WriterLock
from research_system.store.receipts import ReceiptStore


_ACCEPTED = {
    "accepted_commit": "09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6",
    "accepted_tree": "151e0f8b24ad76913640aa0f1de66cd177a44f8f",
    "catalogue_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
    "catalogue_bytes": 136229,
    "catalogue_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
    "bootstrap_blob": "aac7242072c3ce62370dd74d9a27a29e1a33070d",
    "bootstrap_sha256": "ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38",
    "review_commit": "bd61f00d05191de1fd330e997d33ba74ac1b506c",
    "review_blob": "2e0deee51e526cc712c6b04a79695abaa4fb6442",
    "review_sha256": "beb96faa0b58d3ba5faf326b94bb7bc7e1d6649b00c577f2239e1083fe09eaf9",
    "owner_decision": "I accept the KAN 84 envelope, proceed.",
}
_ROW_IDS = tuple(
    [*(f"OR-{number:03d}" for number in range(1, 42)), *(f"OR-{number:03d}" for number in range(101, 141))]
)
_COMMAND_FIELDS = {
    "command_id",
    "command_type",
    "actor_id",
    "authority_grant_id",
    "idempotency_key",
    "target_stream_id",
    "expected_stream_version",
    "payload",
}
_CATALOGUE_STREAM_ID = "obj_019fed25-b33e-7740-b280-000000000001"
_GIT_TIMEOUT_SECONDS = 10
_ARTEFACT_EVENT_TYPES = {
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


class DiscoveryLedgerReplayError(IntegrityError):
    """A persisted Discovery ledger cannot be reconstructed before command preparation."""


_DISCOVERY_COMMAND_TYPES = DISCOVERY_COMMAND_TYPES


@dataclass(frozen=True)
class DiscoveryRowRoute:
    """One executable accepted-catalogue route and its owning preparer family."""

    command_type: str
    family: str
    catalogue_events: tuple[str, ...]


_DISCOVERY_EXCLUDED_ROWS = frozenset(
    {"OR-031", "OR-032", "OR-033"} | {f"OR-{number:03d}" for number in range(122, 140)}
)
_DISCOVERY_DEFERRED_ROWS = {
    "OR-030": "WP6.7 annotation-epoch contract and initial authority activation",
}
_DISCOVERY_ROW_ROUTES = {
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
_DISCOVERY_MINT_ROWS = frozenset(
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
_DISCOVERY_EXISTING_TARGETS = {
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


def _shared_event_partition(
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
    if event_type in _ARTEFACT_EVENT_TYPES:
        return "artefact"
    return "operational"


def _catalogue_event_name(value: Any) -> str:
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


def _validate_discovery_route_registry(catalogue: Mapping[str, Any]) -> None:
    """Prove the production route registry is an exact partition of accepted W11."""

    rows = catalogue.get("owner_contract_rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise IntegrityError("accepted W11 catalogue rows are invalid")
    by_id = {row.get("owner_row_id"): row for row in rows}
    if (
        len(by_id) != 81
        or len(_DISCOVERY_ROW_ROUTES) != 59
        or len(_DISCOVERY_EXCLUDED_ROWS) != 21
        or len(_DISCOVERY_DEFERRED_ROWS) != 1
        or set(_DISCOVERY_ROW_ROUTES) & (_DISCOVERY_EXCLUDED_ROWS | set(_DISCOVERY_DEFERRED_ROWS))
        or _DISCOVERY_EXCLUDED_ROWS & set(_DISCOVERY_DEFERRED_ROWS)
        or set(_DISCOVERY_ROW_ROUTES) | _DISCOVERY_EXCLUDED_ROWS | set(_DISCOVERY_DEFERRED_ROWS) != set(by_id)
        or _DISCOVERY_MINT_ROWS & set(_DISCOVERY_EXISTING_TARGETS)
        or _DISCOVERY_MINT_ROWS | set(_DISCOVERY_EXISTING_TARGETS) != set(_DISCOVERY_ROW_ROUTES)
    ):
        raise IntegrityError("Discovery route registry does not partition accepted W11")
    for row_id, route in _DISCOVERY_ROW_ROUTES.items():
        row = by_id[row_id]
        ordered_events = row.get("ordered_events")
        if (
            row.get("command_type") != route.command_type
            or not isinstance(ordered_events, list)
            or tuple(_catalogue_event_name(value) for value in ordered_events) != route.catalogue_events
        ):
            raise IntegrityError(f"Discovery route registry differs from accepted {row_id}")
    deferred = by_id["OR-030"]
    deferred_events = deferred.get("ordered_events")
    if (
        deferred.get("command_type") != "IngestDiscoveryAnnotation"
        or not isinstance(deferred_events, list)
        or tuple(_catalogue_event_name(value) for value in deferred_events) != ("DiscoveryAnnotationIngested",)
    ):
        raise IntegrityError("Discovery deferred route differs from accepted OR-030")


def _discovery_route(command: Command) -> tuple[str, DiscoveryRowRoute]:
    """Resolve dispatch exclusively from the accepted row and exact producer command."""

    command_type = command.envelope["command_type"]
    if command_type == "ImportAcceptedW11CatalogueGenesis":
        row_id = "OR-140"
    elif command_type == "RegisterCandidate":
        row_id = "OR-001"
    else:
        row_id = command.envelope["payload"].get("row_id")
    route = _DISCOVERY_ROW_ROUTES.get(row_id)
    if route is None or route.command_type != command_type:
        raise IntegrityError("Discovery command does not match an executable accepted W11 row")
    return str(row_id), route


_ASSAY_PARTIAL_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "assay_id",
        "candidate_ref",
        "rubric_ref",
        "scope_ref",
        "assay_bar_acceptance_ref",
        "assay_relation_hash",
        "completed_axes",
        "completed_evidence",
        "unmet_axes",
        "unmet_evidence",
        "reason_codes",
        "limitations",
        "revisit_requirements",
        "mechanical_recommendation",
    }
)


def _valid_assay_partial_shape(artifact: Mapping[str, Any]) -> bool:
    """Validate the closed non-reference shape of an Assay Partial artifact."""
    list_fields = (
        "completed_axes",
        "completed_evidence",
        "unmet_axes",
        "unmet_evidence",
        "reason_codes",
        "limitations",
        "revisit_requirements",
    )
    return bool(
        set(artifact) == _ASSAY_PARTIAL_FIELDS
        and artifact.get("schema_id") == "ars://portfolio/assay-partial"
        and artifact.get("schema_version") == "1.0.0"
        and all(
            isinstance(artifact.get(field), list) and all(isinstance(value, str) for value in artifact[field])
            for field in list_fields
        )
        and all(artifact.get(field) for field in ("unmet_axes", "reason_codes", "revisit_requirements"))
        and artifact.get("mechanical_recommendation") in {"PARK", "KILL", "UNABLE_TO_SCORE"}
    )


def _valid_promotion_options(value: Any) -> bool:
    """Return whether a proposal carries the exact PromotionDecision option set."""
    return bool(
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(option, str) for option in value)
        and set(value) == {"PROMOTE", "PARK", "KILL"}
    )


def _valid_spike_execution_proposal(value: Any) -> bool:
    """Return whether a Spike execution proposal carries the closed option set."""

    return bool(
        isinstance(value, Mapping)
        and value.get("recommendation") in {"approve", "reject"}
        and isinstance(value.get("options"), list)
        and len(value["options"]) == 2
        and set(value["options"]) == {"approve", "reject"}
    )


def _valid_revisit_proposal(value: Any, review_id: Any) -> bool:
    """Return whether a revisit proposal carries the closed option set."""

    return bool(
        isinstance(value, Mapping)
        and isinstance(review_id, str)
        and value.get("recommendation") in {"RETRY", "PARK", "KILL"}
        and isinstance(value.get("options"), list)
        and len(value["options"]) == 3
        and all(isinstance(option, str) for option in value["options"])
        and set(value["options"]) == {"RETRY", "PARK", "KILL"}
        and isinstance(value.get("governing_evidence_refs"), list)
        and review_id in value["governing_evidence_refs"]
    )


def _record_ref(record_id: Any, revision: Any, content_hash: Any) -> dict[str, Any]:
    """Build the exact immutable record reference used by W11 relations."""

    return {"id": record_id, "record_revision": revision, "content_hash": content_hash}


def _candidate_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Build the immutable content reference for one Candidate."""

    return _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))


def _candidate_supersession_lineage(
    candidates: Mapping[str, Any],
    predecessor: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Derive the acyclic immutable Candidate lineage ending in a replacement."""

    reverse_lineage: list[dict[str, Any]] = []
    seen: set[Any] = set()
    current: Mapping[str, Any] | None = predecessor
    while current is not None:
        candidate_id = current.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id in seen:
            raise IntegrityError("Candidate supersession lineage is cyclic")
        seen.add(candidate_id)
        reverse_lineage.append(_candidate_ref(current))
        prior_id = current.get("supersedes_candidate_id")
        if prior_id is None:
            break
        prior = candidates.get(prior_id)
        if not isinstance(prior, Mapping):
            raise IntegrityError("Candidate supersession lineage is incomplete")
        current = prior
    replacement_id = replacement.get("candidate_id")
    if replacement_id in seen:
        raise IntegrityError("Candidate supersession lineage is cyclic")
    return [*reversed(reverse_lineage), _candidate_ref(replacement)]


def _review_ref(review: Mapping[str, Any]) -> dict[str, Any]:
    """Build the immutable reference to a satisfied review verdict."""

    return _record_ref(review.get("review_id"), review.get("version"), review.get("verdict_event_hash"))


def _aggregate_content_hash(aggregate: Mapping[str, Any]) -> Any:
    """Return the exact terminal evidence hash for an Assay or Spike."""

    return aggregate.get("scorecard_sha256", aggregate.get("verdict_sha256", aggregate.get("outcome_sha256")))


def _promotion_relation_matches(
    relation: Any,
    *,
    decision_id: Any,
    candidate: Mapping[str, Any],
    aggregate_id: Any,
    aggregate: Mapping[str, Any],
    review: Mapping[str, Any],
    gate: str,
    recommendation: Any,
    actor_id: Any,
) -> bool:
    """Validate the strict W11 discovery-promotion companion relation."""

    next_state = {
        "PROMOTE": {
            "assay_to_spike": "spike_planning_authorized",
            "spike_to_preregistration": "preregistration_authorized",
        }.get(gate),
        "PARK": "parked",
        "KILL": "killed",
    }.get(recommendation)
    evidence_hash = _aggregate_content_hash(aggregate)
    expected_aggregate_ref = _record_ref(aggregate_id, aggregate.get("version"), evidence_hash)
    expected_review_ref = _review_ref(review)
    return bool(
        isinstance(relation, Mapping)
        and set(relation)
        == {
            "schema_id",
            "schema_version",
            "relation_kind",
            "decision_id",
            "candidate_ref",
            "gate",
            "aggregate_ref",
            "aggregate_relation_hash",
            "evidence_ref",
            "selected_option",
            "next_candidate_state",
            "rationale",
            "considered_evidence_refs",
            "conditions",
            "effective_scope",
            "revisit_triggers",
            "actor_id",
        }
        and relation.get("schema_id") == "ars://portfolio/relation/discovery-promotion"
        and relation.get("schema_version") == "1.0.0"
        and relation.get("relation_kind") == "discovery_promotion"
        and relation.get("decision_id") == decision_id
        and relation.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and relation.get("gate") == gate
        and relation.get("aggregate_ref") == expected_aggregate_ref
        and relation.get("aggregate_relation_hash")
        == aggregate.get("producer_relation_sha256", aggregate.get("plan_sha256"))
        and relation.get("evidence_ref") == expected_aggregate_ref
        and relation.get("selected_option") == recommendation
        and relation.get("next_candidate_state") == next_state
        and isinstance(relation.get("rationale"), str)
        and bool(relation["rationale"])
        and relation.get("considered_evidence_refs") == [expected_review_ref]
        and isinstance(relation.get("conditions"), list)
        and isinstance(relation.get("effective_scope"), str)
        and bool(relation["effective_scope"])
        and isinstance(relation.get("revisit_triggers"), list)
        and relation.get("actor_id") == actor_id
        and review.get("status") == "satisfied"
    )


def _revisit_relation_matches(
    relation: Any,
    *,
    decision_id: Any,
    candidate: Mapping[str, Any],
    aggregate_id: Any,
    aggregate: Mapping[str, Any],
    review: Mapping[str, Any],
    observations: Mapping[str, Any],
    recommendation: Any,
    actor_id: Any,
) -> bool:
    """Validate a discovery-revisit relation and its later objective evidence."""

    predicate_ref = relation.get("satisfied_revisit_predicate_ref") if isinstance(relation, Mapping) else None
    predicate = observations.get(predicate_ref.get("id")) if isinstance(predicate_ref, Mapping) else None
    predicate_batch = predicate.get("batch") if isinstance(predicate, Mapping) else None
    matching_facts = predicate_batch.get("matching_facts") if isinstance(predicate_batch, Mapping) else None
    revisit_requirements = aggregate.get("revisit_requirements")
    review_position = review.get("verdict_global_position")
    parked_position = candidate.get("parked_at_global_position")
    threshold = max(
        review_position if isinstance(review_position, int) else -1,
        parked_position if isinstance(parked_position, int) else -1,
    )
    return bool(
        isinstance(relation, Mapping)
        and set(relation)
        == {
            "schema_id",
            "schema_version",
            "relation_kind",
            "decision_id",
            "candidate_ref",
            "prior_aggregate_ref",
            "prior_outcome_review_ref",
            "satisfied_revisit_predicate_ref",
            "selected_option",
            "actor_id",
        }
        and relation.get("schema_id") == "ars://portfolio/relation/discovery-revisit"
        and relation.get("schema_version") == "1.0.0"
        and relation.get("relation_kind") == "discovery_revisit"
        and relation.get("decision_id") == decision_id
        and relation.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and relation.get("prior_aggregate_ref")
        == _record_ref(aggregate_id, aggregate.get("version"), _aggregate_content_hash(aggregate))
        and relation.get("prior_outcome_review_ref") == _review_ref(review)
        and isinstance(predicate, Mapping)
        and predicate_ref == _record_ref(predicate_ref.get("id"), 1, predicate.get("content_sha256"))
        and predicate_ref.get("id") not in {candidate.get("candidate_id"), aggregate_id, review.get("review_id")}
        and isinstance(predicate.get("global_position"), int)
        and predicate["global_position"] > threshold
        and isinstance(revisit_requirements, list)
        and bool(revisit_requirements)
        and isinstance(matching_facts, list)
        and all(isinstance(requirement, str) and requirement in matching_facts for requirement in revisit_requirements)
        and relation.get("selected_option") == recommendation
        and relation.get("actor_id") == actor_id
    )


_DISCOVERY_IDENTITY_COLLECTIONS = (
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


def _discovery_identity_exists(state: Mapping[str, Any], identity: Any) -> bool:
    """Apply the single global immutable-identity contract to every aggregate kind."""

    return bool(
        (state.get("catalogue") is not None and identity == _CATALOGUE_STREAM_ID)
        or any(identity in state.get(collection, {}) for collection in _DISCOVERY_IDENTITY_COLLECTIONS)
    )


def _current_assay_bar_matches(subject: Mapping[str, Any], bar: Mapping[str, Any], actor_id: Any = None) -> bool:
    """Bind every Assay route to the current accepted bar and prospective producer."""

    producer_ref = bar.get("prospective_producer_ref")
    producer_id = producer_ref.get("id") if isinstance(producer_ref, Mapping) else None
    return bool(
        bar.get("status") == "accepted"
        and subject.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
        and subject.get("producer_relation_sha256") == bar.get("producer_relation_sha256")
        and isinstance(producer_id, str)
        and subject.get("producer_actor_id") == producer_id
        and (actor_id is None or actor_id == producer_id)
    )


def _current_projection_record_ref(state: Mapping[str, Any], value: Any) -> dict[str, Any] | None:
    """Resolve one exact current immutable Discovery record reference."""

    if not isinstance(value, Mapping) or set(value) != {"id", "record_revision", "content_hash"}:
        return None
    record_id = value.get("id")
    record: Mapping[str, Any] | None = None
    revision: Any = None
    content_hash: Any = None
    for collection in (
        "source_observations",
        "candidates",
        "assays",
        "spikes",
        "decisions",
        "reviews",
        "portfolio_objects",
        "scopes",
    ):
        candidate = state.get(collection, {}).get(record_id)
        if isinstance(candidate, Mapping):
            record = candidate
            if collection == "source_observations":
                revision = candidate.get("version")
                content_hash = candidate.get("content_sha256")
            elif collection == "candidates":
                revision = candidate.get("revision")
                content_hash = candidate.get("content_sha256")
            elif collection == "assays":
                revision = 1
                content_hash = _aggregate_content_hash(candidate)
            elif collection == "spikes":
                revision = 1
                content_hash = candidate.get("verdict_sha256", candidate.get("plan_sha256"))
            elif collection == "decisions":
                revision = candidate.get("proposal_version")
                content_hash = candidate.get("proposal_event_hash")
            elif collection == "portfolio_objects":
                revision = candidate.get("record_revision")
                content_hash = candidate.get("content_sha256")
            elif collection == "scopes":
                revision = candidate.get("scope_revision")
                content_hash = candidate.get("content_sha256")
            else:
                revision = candidate.get("version")
                content_hash = candidate.get("verdict_event_hash", candidate.get("request_event_hash"))
            break
    resolved = _record_ref(record_id, revision, content_hash)
    return resolved if record is not None and value == resolved and isinstance(content_hash, str) else None


def _projection_record_ref_matches(state: Mapping[str, Any], value: Any) -> bool:
    """Return whether a reference resolves to an exact current Discovery record."""

    return _current_projection_record_ref(state, value) is not None


def _axis_set_hash(axis_ids: Iterable[str]) -> str:
    """Return the canonical P0 multiset hash for an observed axis closure."""

    return sha256_hex(canonical_bytes(sorted(axis_ids)))


def _assay_scorecard_matches(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    bar: Mapping[str, Any],
    actor_id: Any,
) -> bool:
    """Bind an Assay scorecard to its frozen accepted bar and evidence closure."""

    acceptance = bar.get("acceptance")
    contents = bar.get("contents")
    observations = bar.get("observations")
    if (
        not isinstance(acceptance, Mapping)
        or not isinstance(contents, Mapping)
        or not isinstance(observations, Mapping)
    ):
        return False
    rubric_state = contents.get("rubric")
    scope_state = contents.get("scope")
    rubric_observation = observations.get("rubric")
    scope_observation = observations.get("scope")
    if not all(
        isinstance(value, Mapping) for value in (rubric_state, scope_state, rubric_observation, scope_observation)
    ):
        return False
    rubric = rubric_state.get("content")
    scope = scope_state.get("content")
    if not isinstance(rubric, Mapping) or not isinstance(scope, Mapping):
        return False
    axis_definitions = rubric.get("axis_definitions")
    axis_results = artifact.get("axis_results")
    evidence_rows = scope.get("evidence_rows")
    if (
        not isinstance(axis_definitions, list)
        or not isinstance(axis_results, list)
        or not isinstance(evidence_rows, list)
        or len(axis_results) != len(axis_definitions)
        or len(evidence_rows) != len(axis_definitions)
    ):
        return False
    expected_file_refs = [
        _record_ref(
            rubric.get("record_id"),
            rubric.get("record_revision"),
            rubric_observation.get("file_sha256"),
        ),
        _record_ref(
            scope.get("record_id"),
            scope.get("record_revision"),
            scope_observation.get("file_sha256"),
        ),
    ]
    for definition, result, evidence_row in zip(axis_definitions, axis_results, evidence_rows, strict=True):
        if not all(isinstance(value, Mapping) for value in (definition, result, evidence_row)):
            return False
        value = result.get("value")
        allowed = definition.get("allowed_set")
        bounds = definition.get("bounds")
        minimum = bounds.get("minimum") if isinstance(bounds, Mapping) else None
        maximum = bounds.get("maximum") if isinstance(bounds, Mapping) else None
        value_type = definition.get("value_type")
        typed_value = (
            type(value) is bool
            if value_type == "boolean"
            else type(value) is int
            if value_type == "integer"
            else isinstance(value, (int, float)) and not isinstance(value, bool)
            if value_type == "number"
            else False
        )
        if (
            result.get("axis_id") != definition.get("axis_id")
            or result.get("axis_kind") != definition.get("axis_kind")
            or result.get("validator_id") != evidence_row.get("validator_id")
            or result.get("validator_hash") != evidence_row.get("validator_hash")
            or result.get("evidence_refs") != expected_file_refs
            or not typed_value
            or (isinstance(allowed, list) and value not in allowed)
            or (isinstance(minimum, (int, float)) and value < minimum)
            or (isinstance(maximum, (int, float)) and value > maximum)
        ):
            return False
    axis_ids = [definition.get("axis_id") for definition in axis_definitions]
    expected_candidate = _record_ref(
        payload.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256")
    )
    expected_acceptance = _record_ref(acceptance.get("decision_id"), 1, bar.get("acceptance_sha256"))
    expected_request = _record_ref(
        payload.get("assay_id"), assay.get("request_version"), assay.get("requested_event_hash")
    )
    expected_rule = _record_ref(
        rubric.get("rule_evaluation_algorithm_id"),
        1,
        rubric.get("rule_evaluation_algorithm_hash"),
    )
    required_results = [
        (definition, result)
        for definition, result in zip(axis_definitions, axis_results, strict=True)
        if definition.get("required") is True
    ]
    recommendation = (
        "PROMOTE"
        if all(
            definition.get("axis_kind") != "gate" or result.get("value") is True
            for definition, result in required_results
        )
        else "KILL"
    )
    try:
        artifact_sha256 = sha256_hex(canonical_bytes(artifact))
    except (TypeError, ValueError):
        return False
    producer_ref = acceptance.get("prospective_producer_ref")
    return bool(
        bar.get("status") == "accepted"
        and assay.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
        and artifact.get("candidate_ref") == expected_candidate
        and artifact.get("assay_id") == payload.get("assay_id")
        and artifact.get("assay_requested_event_ref") == expected_request
        and artifact.get("assay_relation_hash") == assay.get("producer_relation_sha256")
        and artifact.get("rubric_ref") == acceptance.get("rubric_ref")
        and artifact.get("scope_ref") == acceptance.get("scope_ref")
        and artifact.get("assay_bar_acceptance_ref") == expected_acceptance
        and artifact.get("file_observation_refs") == expected_file_refs
        and artifact.get("producer_relation_ref") == producer_ref
        and artifact.get("producer_profile_ref") == producer_ref
        and artifact.get("producer_context_ref") == producer_ref
        and artifact.get("required_axis_set_hash") == acceptance.get("required_axis_set_hash")
        and artifact.get("observed_axis_set_hash") == _axis_set_hash(axis_ids)
        and artifact.get("mechanical_recommendation") == recommendation
        and artifact.get("rule_evaluation_ref") == expected_rule
        and artifact.get("producer_actor_id") == actor_id
        and artifact_sha256 == payload.get("scorecard_sha256")
    )


def _spike_execution_relation_matches(
    relation: Any,
    *,
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    spike: Mapping[str, Any],
    decision_id: Any,
    resource: Mapping[str, Any],
) -> bool:
    """Bind the complete Spike execution subject to its plan and assurance."""

    plan_ref = _record_ref(spike.get("spike_id"), 1, spike.get("plan_sha256"))
    return bool(
        isinstance(relation, Mapping)
        and relation.get("schema_id") == "ars://portfolio/relation/spike-execution-authority"
        and relation.get("schema_version") == "1.0.0"
        and relation.get("relation_kind") == "spike_execution_authority"
        and relation.get("decision_id") == decision_id
        and relation.get("spike_ref") == plan_ref
        and relation.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and relation.get("plan_ref") == plan_ref
        and relation.get("route_ref") == plan_ref
        and relation.get("assurance_ref") == _record_ref(assay.get("assay_id"), 1, assay.get("scorecard_sha256"))
        and relation.get("resource_ref")
        == _record_ref(relation.get("resource_ref", {}).get("id"), 1, sha256_hex(canonical_bytes(resource)))
        and relation.get("selected_option") == "AUTHORIZE"
        and isinstance(relation.get("actor_id"), str)
    )


def _spike_plan_matches(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any] | None,
    promotion_decision: Mapping[str, Any] | None,
) -> bool:
    """Bind one Spike plan to the exact Candidate, Assay and promotion decision."""

    return bool(
        isinstance(assay, Mapping)
        and artifact.get("spike_id") == payload.get("spike_id")
        and artifact.get("candidate_ref")
        == _record_ref(
            payload.get("candidate_id"),
            candidate.get("revision"),
            candidate.get("content_sha256"),
        )
        and artifact.get("originating_assay_ref", {}).get("id") == candidate.get("assay_id")
        and artifact.get("originating_assay_ref", {}).get("content_hash") == assay.get("scorecard_sha256")
        and artifact.get("source_scorecard_refs") == [artifact.get("originating_assay_ref")]
        and isinstance(promotion_decision, Mapping)
        and artifact.get("assay_promotion_decision_ref")
        == _record_ref(
            candidate.get("decision_id"),
            promotion_decision.get("proposal_version"),
            promotion_decision.get("proposal_event_hash"),
        )
        and payload.get("plan_sha256") == sha256_hex(canonical_bytes(artifact))
    )


def _spike_verdict_matches(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    spike: Mapping[str, Any],
    state: Mapping[str, Any],
    artefact_streams: Mapping[str, Any],
) -> bool:
    """Resolve every Spike verdict relationship, predicate and evidence ref."""

    plan = spike.get("plan_artifact")
    if not isinstance(plan, Mapping):
        return False
    expected_candidate = _record_ref(
        payload.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256")
    )
    predicate_evidence_refs = [
        *(
            ref
            for result in [
                *artifact.get("success_predicates", ()),
                *artifact.get("failure_predicates", ()),
                *artifact.get("kill_conditions", ()),
            ]
            if isinstance(result, Mapping)
            for ref in result.get("evidence_refs", ())
        ),
    ]
    relationships_match = (
        artifact.get("spike_id") == payload.get("spike_id")
        and artifact.get("candidate_ref") == expected_candidate
        and artifact.get("originating_assay_ref", {}).get("id") == candidate.get("assay_id")
        and artifact.get("originating_assay_ref", {}).get("content_hash") == assay.get("scorecard_sha256")
        and artifact.get("spike_plan_ref") == _record_ref(payload.get("spike_id"), 1, spike.get("plan_sha256"))
        and artifact.get("attempt_ref") == _record_ref(spike.get("attempt_id"), 1, spike.get("attempt_sha256"))
        and artifact.get("verdict") == payload.get("verdict")
        and sha256_hex(canonical_bytes(artifact)) == payload.get("verdict_sha256")
        and bool(artifact.get("artefact_refs"))
        and bool(artifact.get("validation_refs"))
        and bool(predicate_evidence_refs)
        and all(
            _canonical_artefact_ref_matches(artefact_streams, ref, validation=False)
            for ref in artifact.get("artefact_refs", ())
        )
        and all(
            _canonical_artefact_ref_matches(artefact_streams, ref, validation=True)
            for ref in artifact.get("validation_refs", ())
        )
        and all(
            _projection_record_ref_matches(state, ref)
            or _canonical_artefact_ref_matches(artefact_streams, ref, validation=False)
            for ref in predicate_evidence_refs
        )
        and any("dispatch" in value.casefold() for value in artifact.get("prohibited_inferences", ()))
    )
    success = artifact.get("success_predicates", [])
    failure = artifact.get("failure_predicates", [])
    kills = artifact.get("kill_conditions", [])
    if not all(isinstance(value, Mapping) for value in [*success, *failure, *kills]):
        return False
    has_unknown = any(value.get("status") == "unable_to_evaluate" for value in [*success, *failure, *kills])
    predicate_closure = (
        [value.get("predicate") for value in success] == plan.get("success_predicates")
        and [value.get("predicate") for value in failure] == plan.get("failure_predicates")
        and [value.get("condition") for value in kills] == plan.get("kill_conditions")
    )
    if artifact.get("verdict") == "PASS":
        truth_table = (
            not has_unknown
            and bool(success)
            and all(value.get("status") == "passed" for value in success)
            and all(value.get("status") != "failed" for value in failure)
            and all(value.get("status") == "not_triggered" for value in kills)
        )
    elif artifact.get("verdict") == "FAIL":
        truth_table = not has_unknown and (
            any(value.get("status") == "failed" for value in failure)
            or any(value.get("status") == "triggered" for value in kills)
        )
    else:
        truth_table = bool(
            has_unknown
            and artifact.get("completed_scope")
            and artifact.get("unmet_scope")
            and artifact.get("limitations")
            and artifact.get("mechanical_recommendation") != "PROMOTE"
        )
    return bool(relationships_match and predicate_closure and truth_table)


def _canonical_artefact_ref_matches(streams: Mapping[str, Any], value: Any, *, validation: bool) -> bool:
    """Resolve an immutable Spike evidence ref from the canonical artefact projection."""

    if not isinstance(value, Mapping) or set(value) != {"id", "record_revision", "content_hash"}:
        return False
    state = streams.get(value.get("id"))
    manifest = state.get("manifest") if isinstance(state, Mapping) else None
    artefact_type = manifest.get("artefact_type") if isinstance(manifest, Mapping) else None
    if not isinstance(artefact_type, str):
        return False
    if validation and not any(token in artefact_type.casefold() for token in ("validation", "verification", "review")):
        return False
    return bool(
        state.get("artefact_id") == value.get("id")
        and value.get("record_revision") == 1
        and state.get("content_sha256") == value.get("content_hash")
        and state.get("use_authority") not in {"rejected", "superseded"}
    )


def _assay_partial_axes_match(artifact: Mapping[str, Any], bar: Mapping[str, Any]) -> bool:
    """Require an Assay Partial to partition the accepted required-axis closure exactly once."""

    contents = bar.get("contents")
    rubric_state = contents.get("rubric") if isinstance(contents, Mapping) else None
    rubric = rubric_state.get("content") if isinstance(rubric_state, Mapping) else None
    required = rubric.get("required_axis_ids") if isinstance(rubric, Mapping) else None
    completed = artifact.get("completed_axes")
    unmet = artifact.get("unmet_axes")
    return bool(
        isinstance(required, list)
        and required
        and isinstance(completed, list)
        and isinstance(unmet, list)
        and len(completed) == len(set(completed))
        and len(unmet) == len(set(unmet))
        and not (set(completed) & set(unmet))
        and set(completed) | set(unmet) == set(required)
    )


def _assay_cancellation_matches(
    artifact: Any,
    *,
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Bind one Assay cancellation to its exact aggregate, producer and evidence subject."""

    if not isinstance(artifact, Mapping) or set(artifact) != {
        "assay_id",
        "candidate_ref",
        "assay_requested_event_ref",
        "producer_relation_sha256",
        "evidence_refs",
        "reason",
    }:
        return False
    evidence_refs = artifact.get("evidence_refs")
    return bool(
        artifact.get("assay_id") == payload.get("assay_id")
        and artifact.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and artifact.get("assay_requested_event_ref")
        == _record_ref(assay.get("assay_id"), assay.get("request_version"), assay.get("requested_event_hash"))
        and artifact.get("producer_relation_sha256") == assay.get("producer_relation_sha256")
        and isinstance(evidence_refs, list)
        and bool(evidence_refs)
        and all(_projection_record_ref_matches(state, ref) for ref in evidence_refs)
        and isinstance(artifact.get("reason"), str)
        and bool(artifact["reason"])
        and sha256_hex(canonical_bytes(artifact)) == payload.get("cancellation_sha256")
    )


def _assay_staleness_matches(payload: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    """Resolve one OR-109 trigger to a later observation proving an exact authority change."""

    refs = payload.get("trigger_evidence_refs")
    observations = state.get("source_observations")
    if not isinstance(refs, list) or not refs or not isinstance(observations, Mapping):
        return False
    bar = state.get("assay_bar_authority")
    contents = bar.get("contents") if isinstance(bar, Mapping) else None
    accepted_hashes: set[str] = set()
    if isinstance(contents, Mapping):
        for kind in ("rubric", "scope"):
            current = contents.get(kind)
            if isinstance(current, Mapping) and isinstance(current.get("content_sha256"), str):
                accepted_hashes.add(current["content_sha256"])
    if isinstance(bar, Mapping) and isinstance(bar.get("producer_relation_sha256"), str):
        accepted_hashes.add(bar["producer_relation_sha256"])
    accepted_position = bar.get("accepted_global_position") if isinstance(bar, Mapping) else None
    if not isinstance(accepted_position, int):
        return False
    for ref in refs:
        if not _projection_record_ref_matches(state, ref):
            return False
        observation = observations.get(ref.get("id")) if isinstance(ref, Mapping) else None
        if not isinstance(observation, Mapping) or observation.get("global_position", -1) <= accepted_position:
            return False
        batch = observation.get("batch") if isinstance(observation, Mapping) else None
        facts = batch.get("matching_facts") if isinstance(batch, Mapping) else None
        if not isinstance(facts, list):
            return False
        demonstrated = False
        for fact in facts:
            if not isinstance(fact, str):
                continue
            parts = fact.split(":")
            if (
                len(parts) == 4
                and parts[0] == "assay-bar-change"
                and parts[1] in {"rubric", "scope", "producer"}
                and parts[2] in accepted_hashes
                and len(parts[3]) == 64
                and parts[3] != parts[2]
                and all(char in "0123456789abcdef" for char in parts[3])
            ):
                demonstrated = True
                break
        if not demonstrated:
            return False
    return True


def _spike_cancellation_matches(
    artifact: Any,
    *,
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    spike: Mapping[str, Any],
    decision: Mapping[str, Any] | None,
    state: Mapping[str, Any],
) -> bool:
    """Validate the closed Spike cancellation subject and its immutable evidence."""

    if not isinstance(artifact, Mapping) or set(artifact) != {
        "spike_id",
        "candidate_ref",
        "plan_ref",
        "attempt_ref",
        "lease_ref",
        "execution_proposal_ref",
        "reason",
        "evidence_refs",
        "completed_scope",
        "unmet_scope",
        "restrictions",
    }:
        return False
    running = spike.get("status") == "running"
    proposal_ref = (
        _record_ref(
            spike.get("decision_id"),
            decision.get("proposal_version"),
            decision.get("proposal_event_hash"),
        )
        if isinstance(decision, Mapping)
        and decision.get("status") in {"proposed", "cancellation_pending", "candidate_cancellation_pending"}
        else None
    )
    evidence_refs = artifact.get("evidence_refs")
    return bool(
        artifact.get("spike_id") == payload.get("spike_id")
        and artifact.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and artifact.get("plan_ref") == _record_ref(spike.get("spike_id"), 1, spike.get("plan_sha256"))
        and artifact.get("attempt_ref")
        == (_record_ref(spike.get("attempt_id"), 1, spike.get("attempt_sha256")) if running else None)
        and artifact.get("lease_ref")
        == (_record_ref(spike.get("lease_id"), 1, spike.get("lease_sha256")) if running else None)
        and artifact.get("execution_proposal_ref") == proposal_ref
        and isinstance(artifact.get("reason"), str)
        and bool(artifact["reason"])
        and isinstance(evidence_refs, list)
        and bool(evidence_refs)
        and all(_projection_record_ref_matches(state, ref) for ref in evidence_refs)
        and isinstance(artifact.get("completed_scope"), list)
        and isinstance(artifact.get("unmet_scope"), list)
        and bool(artifact["unmet_scope"])
        and isinstance(artifact.get("restrictions"), list)
        and "no_promotion" in artifact["restrictions"]
        and sha256_hex(canonical_bytes(artifact)) == payload.get("cancellation_sha256")
    )


def _spike_execution_ids_available(
    spikes: Mapping[str, Mapping[str, Any]],
    spike_id: Any,
    attempt_id: Any,
    lease_id: Any,
) -> bool:
    """Return whether an Attempt and Lease are unused by every other Spike."""
    return all(
        current_id == spike_id or (spike.get("attempt_id") != attempt_id and spike.get("lease_id") != lease_id)
        for current_id, spike in spikes.items()
    )


def _review_subject_matches(
    review: Any,
    *,
    subject_kind: str,
    subject_id: Any,
    subject_sha256: Any,
) -> bool:
    """Bind a companion lifecycle event to its exact governed review subject."""

    return bool(
        isinstance(review, Mapping)
        and review.get("subject_kind") == subject_kind
        and review.get("subject_id") == subject_id
        and review.get("subject_sha256") == subject_sha256
    )


def _valid_spike_promotion_option(spike: Mapping[str, Any], option: Any) -> bool:
    """Apply the closed reviewed Spike verdict-to-disposition truth table."""

    verdict = spike.get("verdict")
    if verdict == "PASS":
        return option in {"PROMOTE", "PARK", "KILL"}
    if verdict != "FAIL":
        return False
    artifact = spike.get("verdict_artifact")
    kill_conditions = artifact.get("kill_conditions") if isinstance(artifact, Mapping) else None
    triggered_kill = isinstance(kill_conditions, list) and any(
        isinstance(condition, Mapping) and condition.get("status") == "triggered" for condition in kill_conditions
    )
    return option == "KILL" if triggered_kill else option in {"PARK", "KILL"}


def _spike_start_operational_matches(
    operational_events: Iterable[Mapping[str, Any]],
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Resolve the exact running Attempt, live Lease, and resource identity for a Spike start."""

    try:
        operational = replay_control_plane(operational_events)
        attempt = operational.stream_states.get(payload.get("attempt_id"))
        lease = operational.stream_states.get(payload.get("lease_id"))
        relation = payload.get("execution_authority_relation")
        resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
        resource = operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
        occurred_at = datetime.fromisoformat(str(event.get("occurred_at")).replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(str(lease.get("expires_at")).replace("Z", "+00:00"))
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return bool(
        event.get("stream_id") == payload.get("spike_id")
        and isinstance(attempt, Mapping)
        and attempt.get("status") == "running"
        and sha256_hex(canonical_bytes(attempt)) == payload.get("attempt_sha256")
        and attempt.get("lease_id") == payload.get("lease_id")
        and isinstance(lease, Mapping)
        and lease.get("status") == "active"
        and sha256_hex(canonical_bytes(lease)) == payload.get("lease_sha256")
        and lease.get("attempt_id") == payload.get("attempt_id")
        and lease.get("holder_actor_id") == event.get("actor_id")
        and lease.get("resource_grant_id") == payload.get("resource_grant_id")
        and isinstance(resource, Mapping)
        and resource.get("status") == "active"
        and resource_ref == _record_ref(resource_ref.get("id"), 1, sha256_hex(canonical_bytes(resource)))
        and occurred_at.tzinfo is not None
        and expires_at.tzinfo is not None
        and expires_at > occurred_at
    )


def _accepted_dossier_admission_matches(
    authority: Any,
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Rebind a durable admission envelope to the exact accepted expected-set authority."""

    if not isinstance(authority, Mapping) or authority.get("status") != "accepted":
        return False
    subject = authority.get("subject")
    expected_value = subject.get("expected_set") if isinstance(subject, Mapping) else None
    if not isinstance(expected_value, Mapping):
        return False
    try:
        expected = AcceptedExpectedSet(
            **{
                **expected_value,
                "members": tuple(DossierMember(**member) for member in expected_value["members"]),
            }
        )
    except (KeyError, TypeError, ValueError):
        return False
    observed_members = [
        {
            "member_key": member.member_key,
            "member_kind": member.member_kind,
            "root_id": member.root_id,
            "relative_path": member.relative_path,
            "size_bytes": member.size_bytes,
            "sha256": member.sha256,
            "provenance_id": member.provenance_id,
            "provenance_revision": member.provenance_revision,
            "provenance_hash": member.provenance_hash,
        }
        for member in expected.members
    ]
    return bool(
        accepted_expected_set_hash(expected) == expected.content_hash
        and admission_profile_hash(expected.admission_profile_id, expected.admission_profile_revision)
        == expected.admission_profile_hash
        and event.get("stream_id") == expected.dossier_id
        and payload.get("dossier_id") == expected.dossier_id
        and payload.get("project_id") == expected.project_id
        and payload.get("package_id") == expected.package_id
        and payload.get("package_version") == expected.package_version
        and payload.get("expected_set_id") == expected.expected_set_id
        and payload.get("expected_set_revision") == expected.revision
        and payload.get("expected_set_hash") == expected.content_hash
        and payload.get("admission_profile_id") == expected.admission_profile_id
        and payload.get("admission_profile_revision") == expected.admission_profile_revision
        and payload.get("admission_profile_hash") == expected.admission_profile_hash
        and payload.get("candidate_manifest_hash") == expected.manifest_sha256
        and payload.get("member_count") == len(expected.members)
        and payload.get("member_closure_hash") == canonical_dossier_hash(observed_members)
        and payload.get("provider_execution") == "forbidden"
        and payload.get("ownership_effect") == "successor_owned_new_objects_only"
    )


def _git_blob(data: bytes) -> str:
    """Return the Git blob identity for exact bytes."""
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data,
        usedforsecurity=False,
    ).hexdigest()


def _source_observation_multiset_hash(observation_ids: list[str], observations: Mapping[str, Mapping[str, Any]]) -> str:
    """Hash an exact sorted multiset of resolved source-observation identities."""

    resolved = []
    for observation_id in sorted(observation_ids):
        observation = observations.get(observation_id)
        if not isinstance(observation, Mapping) or not isinstance(observation.get("content_sha256"), str):
            raise IntegrityError("Candidate source observation is not registered")
        resolved.append({"observation_id": observation_id, "content_sha256": observation["content_sha256"]})
    return sha256_hex(canonical_bytes(resolved))


def _review_policy_status(payload: Mapping[str, Any]) -> str:
    """Return the closed W11 review-policy projection status."""

    verdict = payload.get("verdict")
    if verdict == "approve":
        return "satisfied"
    if verdict == "approve_with_conditions":
        conditions = payload.get("conditions")
        if (
            isinstance(conditions, list)
            and conditions
            and all(
                isinstance(condition, dict)
                and condition.get("gate_disposition") == "non_blocking"
                and isinstance(condition.get("owner_actor_id"), str)
                and isinstance(condition.get("policy_id"), str)
                and isinstance(condition.get("evidence_refs"), list)
                and bool(condition["evidence_refs"])
                for condition in conditions
            )
        ):
            return "satisfied"
        return "changes_requested"
    if verdict == "changes_requested":
        return "changes_requested"
    if verdict in {"reject", "unable_to_verify"}:
        return "verdict_recorded"
    if verdict == "withdrawn":
        return "withdrawn"
    raise IntegrityError("invalid Discovery review verdict policy")


def _valid_review_supersession(
    relation: object,
    prior_review: object,
    new_subject_sha256: object,
    new_required_evidence_refs: object,
) -> bool:
    """Validate the closed W11 relation for replacing a non-satisfying review."""

    if not isinstance(relation, Mapping) or not isinstance(prior_review, Mapping):
        return False
    changed_refs = relation.get("changed_evidence_refs")
    delta_scope = relation.get("accepted_delta_scope")
    mode = relation.get("mode")
    prior_status = prior_review.get("status")
    prior_subject = prior_review.get("subject_sha256")
    prior_evidence_refs = prior_review.get("required_evidence_refs")
    same_subject = new_subject_sha256 == prior_subject
    if (
        prior_status not in {"changes_requested", "verdict_recorded", "withdrawn"}
        or relation.get("prior_review_id") != prior_review.get("review_id")
        or relation.get("prior_request_event_id") != prior_review.get("request_event_id")
        or relation.get("prior_request_event_hash") != prior_review.get("request_event_hash")
        or relation.get("prior_verdict_event_id") != prior_review.get("verdict_event_id")
        or relation.get("prior_verdict_event_hash") != prior_review.get("verdict_event_hash")
        or relation.get("prior_subject_sha256") != prior_subject
        or relation.get("new_subject_sha256") != new_subject_sha256
        or not isinstance(changed_refs, list)
        or not changed_refs
        or not all(isinstance(ref, str) and ref for ref in changed_refs)
        or len(set(changed_refs)) != len(changed_refs)
        or not isinstance(prior_evidence_refs, list)
        or not isinstance(new_required_evidence_refs, list)
        or set(changed_refs) & set(prior_evidence_refs)
        or set(new_required_evidence_refs) != {*prior_evidence_refs, *changed_refs}
        or not isinstance(relation.get("reason"), str)
        or not relation["reason"]
        or not isinstance(relation.get("proposed_reviewer_relation"), str)
        or not relation["proposed_reviewer_relation"]
        or mode not in {"superseding_subject", "bounded_delta"}
        or (same_subject and prior_status != "withdrawn")
        or (prior_review.get("verdict") == "reject" and mode != "superseding_subject")
    ):
        return False
    if mode == "bounded_delta":
        return bool(
            relation.get("unchanged_base_sha256") == prior_subject
            and isinstance(delta_scope, list)
            and delta_scope
            and all(isinstance(item, str) and item for item in delta_scope)
            and len(set(delta_scope)) == len(delta_scope)
            and new_subject_sha256
            == sha256_hex(
                canonical_bytes(
                    {
                        "unchanged_base_sha256": prior_subject,
                        "accepted_delta_scope": delta_scope,
                        "changed_evidence_refs": changed_refs,
                    }
                )
            )
        )
    return relation.get("unchanged_base_sha256") is None and relation.get("accepted_delta_scope") is None


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


@lru_cache(maxsize=1)
def _default_replay_schemas() -> SchemaRegistry:
    """Load exact bundled schemas for public standalone replay."""

    return runtime_schema_registry(Path(__file__).resolve().parents[2] / ".research-system" / "schemas")


def replay_discovery(
    events: Iterable[dict[str, Any]],
    *,
    schemas: SchemaRegistry | None = None,
) -> dict[str, Any]:
    """Rebuild Discovery state while rejecting malformed transitions.

    Args:
        events: Ordered persisted events from one Discovery ledger.

    Returns:
        The deterministic Discovery projection reconstructed from ``events``.

    Raises:
        IntegrityError: If the event chain, payload, authority relation, or lifecycle transition is malformed.
    """
    ordered = tuple(deepcopy(tuple(events)))
    _validate_hash_chain(ordered)
    resolve_transaction_ids = discovery_resolve_transaction_ids(ordered)
    state: dict[str, Any] = {
        "catalogue": None,
        "source_observations": {},
        "candidates": {},
        "assays": {},
        "spikes": {},
        "decisions": {},
        "reviews": {},
        "dossiers": {},
        "portfolio_objects": {},
        "scopes": {},
        "artefact_streams": {},
        "authority_events": [],
        "authorities": {},
        "authority_streams": {},
        "authority_subject_streams": {},
        "assay_bar_authority_events": [],
        "assay_bar_authority": {"contents": {}, "observations": {}, "status": "empty"},
    }
    operational_events: list[dict[str, Any]] = []
    canonical_artefact_streams: dict[str, dict[str, Any]] = {}

    def aggregate_identity_exists(identity: Any) -> bool:
        """Return whether an immutable identity is already owned by any Discovery aggregate."""
        return _discovery_identity_exists(state, identity)

    def claim_authority_stream(identity: Any, kind: Any) -> None:
        """Reserve a W11 authority stream without crossing any aggregate namespace."""

        if not isinstance(identity, str) or kind not in {"dossier_expected_set", "path_registration", "assay_bar"}:
            raise IntegrityError("invalid W11 authority stream identity")
        existing = state["authority_streams"].get(identity)
        if existing is None:
            if aggregate_identity_exists(identity):
                raise IntegrityError("W11 authority stream identity collision")
            state["authority_streams"][identity] = kind
        elif existing != kind:
            raise IntegrityError("W11 authority stream identity collision")

    for event in ordered:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise IntegrityError("Discovery event payload must be an object")
        if event.get("command_type") == "IngestDiscoveryAnnotation" or event_type == "DiscoveryAnnotationIngested":
            raise IntegrityError("Discovery annotation route is deferred pending accepted epoch authority")
        partition = _shared_event_partition(event, resolve_transaction_ids=resolve_transaction_ids)
        if partition == "artefact":
            stream_id = event.get("stream_id")
            if not isinstance(stream_id, str):
                raise IntegrityError("invalid canonical artefact stream identity")
            if stream_id not in state["artefact_streams"] and _discovery_identity_exists(state, stream_id):
                raise IntegrityError("canonical artefact identity collision")
            try:
                canonical_artefact_streams[stream_id] = reduce_artefact(
                    canonical_artefact_streams.get(stream_id, {}), event
                )
                if event_type == "ArtefactRegistered":
                    canonical_artefact_streams[stream_id]["registration_actor_id"] = event.get("actor_id")
                state["artefact_streams"][stream_id] = deepcopy(canonical_artefact_streams[stream_id])
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityError("invalid canonical artefact evidence") from exc
            continue
        if partition == "operational":
            # OR-019 closes the canonical operational Attempt and Lease in the
            # same ledger transaction as its Discovery relations. Their state
            # is reduced by replay_control_plane, not by this projection.
            operational_events.append(event)
            continue

        def required_string(key: str) -> str:
            value = payload.get(key)
            if not isinstance(value, str):
                raise IntegrityError(f"Discovery event payload requires {key}")
            return value

        def required_int(key: str) -> int:
            value = payload.get(key)
            if not isinstance(value, int) or isinstance(value, bool):
                raise IntegrityError(f"Discovery event payload requires {key}")
            return value

        def required_string_list(key: str) -> list[str]:
            value = payload.get(key)
            if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
                raise IntegrityError(f"Discovery event payload requires {key}")
            return value

        if "authority_event_type" in payload:
            authority_payload = payload.get("authority_payload")
            if not isinstance(authority_payload, dict):
                raise IntegrityError("Discovery event payload requires authority_payload")
            authority_payload = deepcopy(authority_payload)
            if payload.get("authority_event_type") in {
                "DecisionResolved",
                "DossierExpectedSetAccepted",
                "PathRegistrationAccepted",
                "AssayBarAccepted",
            }:
                authority_payload["transaction_id"] = event.get("transaction_id")
            if payload.get("authority_event_type") == "AssayBarAccepted":
                authority_payload["accepted_global_position"] = event.get("global_position")
            authority_kind = required_string("authority_kind")
            authority_event = {
                "owner_row_id": required_string("owner_row_id"),
                "authority_kind": authority_kind,
                "event_type": required_string("authority_event_type"),
                "payload": authority_payload,
            }
            if authority_kind == "assay_bar":
                if authority_event["event_type"] == "W11AuthorityFileObserved":
                    content_kind = authority_payload.get("content_kind")
                    content_state = state["assay_bar_authority"].get("contents", {}).get(content_kind)
                    content = content_state.get("content") if isinstance(content_state, Mapping) else None
                    if not isinstance(content, Mapping) or event.get("stream_id") != content.get("record_id"):
                        raise IntegrityError("Assay-bar observation stream mismatch")
                state["assay_bar_authority_events"].append(authority_event)
                claim_authority_stream(event["stream_id"], authority_kind)
                try:
                    state["assay_bar_authority"] = replay_assay_bar_authority(state["assay_bar_authority_events"])
                except ValueError as exc:
                    raise IntegrityError(str(exc)) from exc
                continue
            if authority_event["event_type"] in {
                "DossierExpectedSetContentRegistered",
                "PathRegistrationContentRegistered",
            }:
                state["authority_subject_streams"][authority_kind] = event.get("stream_id")
            elif authority_event["event_type"] == "W11AuthorityFileObserved" and event.get("stream_id") != state[
                "authority_subject_streams"
            ].get(authority_kind):
                raise IntegrityError("W11 authority observation stream mismatch")
            state["authority_events"].append(authority_event)
            claim_authority_stream(event["stream_id"], authority_kind)
            state["authorities"] = replay_authority(state["authority_events"])
            continue
        if event.get("command_type") in {
            "RequestW11AuthorityReview",
            "RecordW11AuthorityReview",
            "ProposeW11AuthorityDecision",
        } or (event.get("command_type") == "ResolveDecision" and event["stream_id"] in state["authority_streams"]):
            if event_type not in {
                "ReviewRequested",
                "ReviewVerdictRecorded",
                "DecisionProposed",
                "DecisionResolved",
            }:
                raise IntegrityError("unsupported W11 authority event type")
            if event_type == "DecisionProposed" and event.get("stream_id") != payload.get("new_decision_id"):
                raise IntegrityError("W11 authority decision stream mismatch")
            if event_type == "DecisionResolved" and event.get("stream_id") != payload.get("decision_id"):
                raise IntegrityError("W11 authority decision stream mismatch")
            kind = state["authority_streams"].get(event["stream_id"])
            if kind is None and event_type == "ReviewRequested":
                refs = payload.get("governing_refs", [])
                kind = next(
                    (
                        value.removeprefix("authority-kind:")
                        for value in refs
                        if isinstance(value, str) and value.startswith("authority-kind:")
                    ),
                    None,
                )
                claim_authority_stream(event["stream_id"], kind)
            elif kind is None and event_type == "DecisionProposed":
                refs = payload.get("governing_evidence_refs", [])
                kind = next(
                    (
                        value.removeprefix("authority-kind:")
                        for value in refs
                        if isinstance(value, str) and value.startswith("authority-kind:")
                    ),
                    None,
                )
                claim_authority_stream(event["stream_id"], kind)
            if kind not in {"dossier_expected_set", "path_registration", "assay_bar"}:
                raise IntegrityError("missing explicit W11 authority kind")
            if kind == "assay_bar":
                current = state["assay_bar_authority"]
                if event_type == "ReviewRequested":
                    reviewer_capability = payload.get("reviewer_capability")
                    governing_refs = payload.get("governing_refs")
                    producer_value = (
                        next(
                            (
                                value.removeprefix("prospective-producer:")
                                for value in governing_refs
                                if isinstance(value, str) and value.startswith("prospective-producer:")
                            ),
                            None,
                        )
                        if isinstance(governing_refs, list)
                        else None
                    )
                    try:
                        prospective_producer_ref = json.loads(producer_value) if producer_value is not None else None
                    except json.JSONDecodeError as exc:
                        raise IntegrityError("invalid Assay-bar producer relation") from exc
                    if (
                        not isinstance(reviewer_capability, list)
                        or not reviewer_capability
                        or not isinstance(reviewer_capability[0], str)
                        or not isinstance(prospective_producer_ref, dict)
                    ):
                        raise IntegrityError("invalid Assay-bar review request")
                    shadow = {
                        "actor_id": event["actor_id"],
                        "reviewer_actor_id": reviewer_capability[0],
                        "review_id": required_string("new_review_id"),
                        "subject_sha256": required_string_list("subject_hashes")[0],
                        "prospective_producer_ref": prospective_producer_ref,
                    }
                elif event_type == "ReviewVerdictRecorded":
                    shadow = {
                        "actor_id": event["actor_id"],
                        "verdict": required_string("verdict"),
                        "unchanged_subject_sha256": required_string("unchanged_subject_sha256"),
                        "context_manifest_id": required_string("context_manifest_id"),
                        "reconstruction_sha256": required_string("context_manifest_sha256"),
                    }
                elif event_type == "DecisionProposed":
                    shadow = {
                        "actor_id": event["actor_id"],
                        "decision_id": required_string("new_decision_id"),
                        "proposed_decision": required_string("recommendation"),
                        "subject_sha256": current.get("subject_sha256"),
                    }
                else:
                    shadow = {
                        "actor_id": event["actor_id"],
                        "decision_id": required_string("decision_id"),
                        "decision": required_string("selected_option"),
                        "transaction_id": event.get("transaction_id"),
                    }
                state["assay_bar_authority_events"].append(
                    {
                        "owner_row_id": {
                            "ReviewRequested": "OR-105",
                            "ReviewVerdictRecorded": "OR-106",
                            "DecisionProposed": "OR-107",
                            "DecisionResolved": "OR-108",
                        }[event_type],
                        "authority_kind": kind,
                        "event_type": event_type,
                        "payload": shadow,
                    }
                )
                try:
                    state["assay_bar_authority"] = replay_assay_bar_authority(state["assay_bar_authority_events"])
                except ValueError as exc:
                    raise IntegrityError(str(exc)) from exc
                continue
            current = state["authorities"].get(kind, {})
            if event_type == "ReviewRequested":
                reviewer_capability = payload.get("reviewer_capability")
                if (
                    not isinstance(reviewer_capability, list)
                    or not reviewer_capability
                    or not isinstance(reviewer_capability[0], str)
                ):
                    raise IntegrityError("Discovery event payload requires reviewer_capability")
                shadow = {
                    "actor_id": event["actor_id"],
                    "reviewer_actor_id": reviewer_capability[0],
                    "review_id": required_string("new_review_id"),
                    "subject_sha256": current.get("subject_sha256"),
                    "file_sha256": current.get("file_sha256"),
                }
            elif event_type == "ReviewVerdictRecorded":
                shadow = {
                    "actor_id": event["actor_id"],
                    "verdict": required_string("verdict"),
                    "unchanged_subject_sha256": required_string("unchanged_subject_sha256"),
                    "unchanged_file_sha256": current.get("file_sha256"),
                    "reconstruction_sha256": required_string("context_manifest_sha256"),
                }
            elif event_type == "DecisionProposed":
                shadow = {
                    "actor_id": event["actor_id"],
                    "decision_id": required_string("new_decision_id"),
                    "proposed_decision": required_string("recommendation"),
                    "subject_sha256": current.get("subject_sha256"),
                    "file_sha256": current.get("file_sha256"),
                }
            else:
                shadow = {
                    "actor_id": event["actor_id"],
                    "decision_id": required_string("decision_id"),
                    "decision": required_string("selected_option"),
                    "transaction_id": event.get("transaction_id"),
                }
            state["authority_events"].append(
                {
                    "owner_row_id": {
                        "ReviewRequested": "OR-112" if kind == "dossier_expected_set" else "OR-118",
                        "ReviewVerdictRecorded": "OR-113" if kind == "dossier_expected_set" else "OR-119",
                        "DecisionProposed": "OR-114" if kind == "dossier_expected_set" else "OR-120",
                        "DecisionResolved": "OR-115" if kind == "dossier_expected_set" else "OR-121",
                    }[event_type],
                    "authority_kind": kind,
                    "event_type": event_type,
                    "payload": shadow,
                }
            )
            state["authorities"] = replay_authority(state["authority_events"])
            continue
        if event_type == "W11CatalogueGenesisImported":
            if (
                state["catalogue"] is not None
                or event.get("command_type") != "ImportAcceptedW11CatalogueGenesis"
                or payload.get("owner_row_id") != "OR-140"
            ):
                raise IntegrityError("W11 genesis appears more than once")
            state["catalogue"] = deepcopy(payload)
        elif event_type == "ScoutObservationIngested":
            observation_id = required_string("observation_id")
            if _discovery_identity_exists(state, observation_id):
                raise IntegrityError("source observation identity collision")
            batch = payload.get("batch")
            dedup_keys = payload.get("normalized_dedup_keys")
            if (
                not isinstance(batch, dict)
                or not isinstance(dedup_keys, list)
                or not dedup_keys
                or not all(isinstance(value, str) and value for value in dedup_keys)
                or len(dedup_keys) != len(set(dedup_keys))
                or required_string("content_sha256") != sha256_hex(canonical_bytes(batch))
                or any(
                    set(dedup_keys) & set(existing.get("normalized_dedup_keys", []))
                    for existing in state["source_observations"].values()
                )
            ):
                raise IntegrityError("invalid Scout observation event")
            state["source_observations"][observation_id] = {
                **deepcopy(payload),
                "global_position": event["global_position"],
                "version": event["stream_version"],
            }
        elif event_type == "CandidateRegistered":
            if state["catalogue"] is None:
                raise IntegrityError("Candidate event predates W11 genesis")
            candidate_id = payload.get("candidate_id")
            observations = payload.get("source_observation_refs")
            expected_owner_row = {
                "RegisterCandidate": "OR-001",
                "IngestScoutObservationBatch": "OR-029",
            }.get(event.get("command_type"))
            if (
                not isinstance(candidate_id, str)
                or event.get("stream_id") != candidate_id
                or payload.get("owner_row_id") != expected_owner_row
                or _discovery_identity_exists(state, candidate_id)
                or not isinstance(observations, list)
                or not observations
                or not all(isinstance(item, str) and item for item in observations)
            ):
                raise IntegrityError("Candidate identity collision")
            multiset_hash = _source_observation_multiset_hash(observations, state["source_observations"])
            if (
                payload.get("source_observation_multiset_hash") != multiset_hash
                or payload.get("content_sha256") != multiset_hash
            ):
                raise IntegrityError("Candidate source observation identity mismatch")
            state["candidates"][candidate_id] = {**deepcopy(payload), "status": "registered", "version": 1}
        elif event_type == "CandidateSuperseded":
            predecessor_ref = payload.get("predecessor_ref")
            replacement_ref = payload.get("replacement_ref")
            predecessor_id = predecessor_ref.get("id") if isinstance(predecessor_ref, Mapping) else None
            replacement_id = replacement_ref.get("id") if isinstance(replacement_ref, Mapping) else None
            predecessor = state["candidates"].get(predecessor_id)
            replacement = state["candidates"].get(replacement_id)
            if not isinstance(predecessor, dict) or not isinstance(replacement, dict):
                raise IntegrityError("invalid Candidate supersession subject")
            if predecessor_id == replacement_id:
                raise IntegrityError("invalid Candidate supersession")
            try:
                lineage = _candidate_supersession_lineage(state["candidates"], predecessor, replacement)
                lineage_sha256 = sha256_hex(
                    canonical_bytes({"lineage": lineage, "lineage_reason": payload.get("lineage_reason")})
                )
            except (TypeError, ValueError) as exc:
                raise IntegrityError("invalid Candidate supersession lineage") from exc
            if (
                event.get("command_type") != "SupersedeDiscoveryRecord"
                or event.get("stream_id") != predecessor_id
                or payload.get("owner_row_id") != "OR-002"
                or predecessor_id == replacement_id
                or predecessor_ref != _candidate_ref(predecessor)
                or replacement_ref != _candidate_ref(replacement)
                or predecessor.get("status") == "superseded"
                or replacement.get("status") == "superseded"
                or replacement.get("supersedes_candidate_id") is not None
                or payload.get("lineage") != lineage
                or payload.get("lineage_sha256") != lineage_sha256
                or not isinstance(payload.get("lineage_reason"), str)
                or not payload["lineage_reason"]
            ):
                raise IntegrityError("invalid Candidate supersession")
            predecessor.update(
                status="superseded",
                superseded_by=replacement_id,
                supersession_sha256=lineage_sha256,
                version=event["stream_version"],
            )
            replacement["supersedes_candidate_id"] = predecessor_id
        elif event_type == "AssayRequested":
            assay_id = payload.get("assay_id")
            candidate_id = payload.get("candidate_id")
            if (
                not isinstance(assay_id, str)
                or aggregate_identity_exists(assay_id)
                or state["candidates"].get(candidate_id, {}).get("status")
                not in {"registered", "assay_retry_authorized"}
                or not _current_assay_bar_matches(payload, state["assay_bar_authority"])
            ):
                raise IntegrityError("invalid Assay request transition")
            state["assays"][assay_id] = {
                "assay_id": assay_id,
                "candidate_id": candidate_id,
                "candidate_revision": required_int("candidate_revision"),
                "candidate_sha256": required_string("candidate_sha256"),
                "assay_bar_acceptance_sha256": required_string("assay_bar_acceptance_sha256"),
                "producer_relation_sha256": required_string("producer_relation_sha256"),
                "producer_actor_id": required_string("producer_actor_id"),
                "request_version": event["stream_version"],
                "requested_event_hash": event.get("event_hash"),
                "status": "requested",
                "version": event["stream_version"],
            }
        elif event_type == "AssayEvidenceCollectionOpened":
            assay = state["assays"].get(payload.get("assay_id"))
            if not isinstance(assay, dict) or assay.get("status") != "requested":
                raise IntegrityError("invalid Assay evidence transition")
            assay.update(status="evidence_collecting", version=event["stream_version"])
        elif event_type == "CandidateAssayRequested":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "registered":
                raise IntegrityError("invalid Candidate Assay transition")
            candidate.update(
                status="assay_pending", assay_id=required_string("assay_id"), version=event["stream_version"]
            )
        elif event_type == "AssayScored":
            assay = state["assays"].get(payload.get("assay_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            artifact = payload.get("scorecard_artifact")
            if (
                not isinstance(assay, dict)
                or not isinstance(candidate, dict)
                or not isinstance(artifact, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
                or not _current_assay_bar_matches(assay, state["assay_bar_authority"], event.get("actor_id"))
                or not _assay_scorecard_matches(
                    artifact,
                    payload,
                    candidate,
                    assay,
                    state["assay_bar_authority"],
                    event.get("actor_id"),
                )
            ):
                raise IntegrityError("invalid Assay score transition")
            assay.update(
                status="scored",
                scorecard_sha256=required_string("scorecard_sha256"),
                mechanical_recommendation=artifact.get("mechanical_recommendation"),
                producer_actor_id=event.get("actor_id"),
                version=event["stream_version"],
            )
        elif event_type == "CandidateAssayLinked":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "assay_pending":
                raise IntegrityError("invalid Candidate Assay score transition")
            candidate.update(
                status="assay_scored",
                scorecard_sha256=required_string("scorecard_sha256"),
                version=event["stream_version"],
            )
        elif event_type == "AssayPartialRecorded":
            assay = state["assays"].get(payload.get("assay_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            artifact = payload.get("partial_artifact")
            bar = state["assay_bar_authority"]
            acceptance = bar.get("acceptance") if isinstance(bar, dict) else None
            expected_acceptance = (
                {
                    "id": acceptance.get("decision_id"),
                    "record_revision": 1,
                    "content_hash": bar.get("acceptance_sha256"),
                }
                if isinstance(acceptance, dict)
                else None
            )
            if (
                not isinstance(assay, dict)
                or not isinstance(candidate, dict)
                or not isinstance(artifact, dict)
                or not isinstance(acceptance, dict)
                or not _valid_assay_partial_shape(artifact)
                or assay.get("status") != "evidence_collecting"
                or not _current_assay_bar_matches(assay, bar, event.get("actor_id"))
                or artifact.get("candidate_ref")
                != {
                    "id": payload.get("candidate_id"),
                    "record_revision": candidate.get("revision"),
                    "content_hash": candidate.get("content_sha256"),
                }
                or artifact.get("assay_id") != payload.get("assay_id")
                or artifact.get("rubric_ref") != acceptance.get("rubric_ref")
                or artifact.get("scope_ref") != acceptance.get("scope_ref")
                or artifact.get("assay_bar_acceptance_ref") != expected_acceptance
                or artifact.get("assay_relation_hash") != assay.get("producer_relation_sha256")
                or not _assay_partial_axes_match(artifact, bar)
                or sha256_hex(canonical_bytes(artifact)) != payload.get("partial_sha256")
            ):
                raise IntegrityError("invalid Assay partial transition")
            assay.update(
                status="partial_recorded",
                outcome_sha256=required_string("partial_sha256"),
                partial_artifact=deepcopy(artifact),
                revisit_requirements=deepcopy(artifact["revisit_requirements"]),
                producer_actor_id=event.get("actor_id"),
                version=event["stream_version"],
            )
        elif event_type == "CandidateAssayPartialLinked":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "assay_pending":
                raise IntegrityError("invalid Candidate Assay partial transition")
            candidate.update(status="assay_partial_recorded", version=event["stream_version"])
        elif event_type == "AssayCancelled":
            assay = state["assays"].get(payload.get("assay_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if (
                not isinstance(assay, dict)
                or assay.get("status") not in {"requested", "evidence_collecting"}
                or not isinstance(candidate, dict)
                or assay.get("candidate_id") != payload.get("candidate_id")
                or not _assay_cancellation_matches(
                    payload.get("cancellation_artifact"),
                    payload=payload,
                    candidate=candidate,
                    assay=assay,
                    state=state,
                )
            ):
                raise IntegrityError("invalid Assay cancellation")
            assay.update(
                status="cancelled",
                outcome_sha256=required_string("cancellation_sha256"),
                cancellation_artifact=deepcopy(payload["cancellation_artifact"]),
                revisit_requirements=[payload["cancellation_artifact"]["reason"]],
                producer_actor_id=event.get("actor_id"),
                version=event["stream_version"],
            )
        elif event_type == "CandidateEvaluationCancelled":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or payload.get("evaluation_kind") not in {"assay", "spike"}:
                raise IntegrityError("invalid Candidate evaluation cancellation")
            if payload.get("evaluation_kind") == "spike":
                spike = state["spikes"].get(payload.get("spike_id"))
                decision = state["decisions"].get(spike.get("decision_id")) if isinstance(spike, dict) else None
                if (
                    not isinstance(spike, dict)
                    or spike.get("candidate_id") != payload.get("candidate_id")
                    or spike.get("status") != "cancelled"
                ):
                    raise IntegrityError("invalid Candidate evaluation cancellation")
                if (
                    spike.get("decision_id") is not None
                    and isinstance(decision, dict)
                    and decision.get("status") in {"cancellation_pending", "candidate_cancellation_pending"}
                ):
                    if (
                        decision.get("status") != "candidate_cancellation_pending"
                        or decision.get("cancellation_candidate_id") != payload.get("candidate_id")
                        or decision.get("cancellation_spike_id") != payload.get("spike_id")
                        or decision.get("cancellation_sha256") != payload.get("cancellation_sha256")
                        or decision.get("cancellation_transaction_id") != event.get("transaction_id")
                    ):
                        raise IntegrityError("invalid Spike execution proposal cancellation")
                    decision.update(status="superseded_by_cancellation")
            candidate.update(
                status=f"{payload['evaluation_kind']}_cancelled",
                version=event["stream_version"],
            )
        elif event_type == "ReviewRequested":
            review_id = payload.get("new_review_id")
            subject_ids = required_string_list("subject_ids")
            subject_hashes = required_string_list("subject_hashes")
            if (
                not isinstance(review_id, str)
                or event.get("stream_id") != review_id
                or aggregate_identity_exists(review_id)
                or len(subject_ids) != 1
                or len(subject_hashes) != 1
            ):
                raise IntegrityError("invalid Discovery review request")
            subject_id = subject_ids[0]
            if subject_id.startswith("asy_"):
                subject_kind = "assay"
            elif subject_id.startswith("spk_"):
                subject_kind = "spike"
            else:
                raise IntegrityError("invalid Discovery review subject")
            state["reviews"][review_id] = {
                "review_id": review_id,
                "subject_id": subject_id,
                "subject_kind": subject_kind,
                "subject_sha256": subject_hashes[0],
                "allowed_verdicts": required_string_list("allowed_verdicts"),
                "required_evidence_refs": required_string_list("required_evidence_refs"),
                "required_independence_grade": required_string("required_independence_grade"),
                "request_actor_id": event.get("actor_id"),
                "request_event_id": event.get("event_id"),
                "request_event_hash": event.get("event_hash"),
                "status": "pending",
                "version": event["stream_version"],
            }
        elif event_type in {
            "AssayOutcomeReviewRequested",
            "AssayPartialReviewRequested",
            "AssayCancellationReviewRequested",
        }:
            assay = state["assays"].get(payload.get("assay_id"))
            expected_status = {
                "AssayOutcomeReviewRequested": "scored",
                "AssayPartialReviewRequested": "partial_recorded",
                "AssayCancellationReviewRequested": "cancelled",
            }[event_type]
            if not isinstance(assay, dict) or assay.get("status") != expected_status:
                raise IntegrityError("invalid Assay outcome review request")
            review = state["reviews"].get(payload.get("review_id"))
            prior_review = state["reviews"].get(assay.get("review_id"))
            relation = payload.get("review_subject_supersession")
            if (
                event.get("stream_id") != payload.get("assay_id")
                or assay.get("candidate_id") != payload.get("candidate_id")
                or not _review_subject_matches(
                    review,
                    subject_kind="assay",
                    subject_id=payload.get("assay_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
            ):
                raise IntegrityError("invalid Assay outcome review request")
            if assay.get("review_id") is None:
                if relation is not None or payload.get("subject_sha256") != _aggregate_content_hash(assay):
                    raise IntegrityError("invalid Assay review supersession")
            elif not _valid_review_supersession(
                relation,
                prior_review,
                review.get("subject_sha256"),
                review.get("required_evidence_refs"),
            ):
                raise IntegrityError("invalid Assay review supersession")
            else:
                prior_review.update(status="superseded", superseded_by_review_id=review["review_id"])
            assay.update(
                review_id=required_string("review_id"),
                review_subject_sha256=required_string("subject_sha256"),
                review_pending=True,
                version=event["stream_version"],
            )
        elif event_type == "ReviewVerdictRecorded":
            review_id = required_string("review_id")
            review = state["reviews"].get(review_id)
            reviewer_actor_id = required_string("reviewer_actor_id")
            subject_collection = {
                "assay": state["assays"],
                "spike": state["spikes"],
            }.get(review.get("subject_kind") if isinstance(review, dict) else None)
            subject = (
                subject_collection.get(review.get("subject_id"))
                if isinstance(subject_collection, dict) and isinstance(review, dict)
                else None
            )
            if (
                not isinstance(review, dict)
                or not isinstance(subject, dict)
                or event["stream_id"] != review_id
                or review.get("status") != "pending"
                or review.get("subject_sha256") != payload.get("unchanged_subject_sha256")
                or payload.get("verdict") not in review.get("allowed_verdicts", ())
                or reviewer_actor_id != event.get("actor_id")
                or reviewer_actor_id == review.get("request_actor_id")
                or reviewer_actor_id == subject.get("producer_actor_id")
                or payload.get("computed_independence_grade") != review.get("required_independence_grade")
            ):
                raise IntegrityError("invalid Discovery review verdict")
            review.update(
                status=_review_policy_status(payload),
                verdict=required_string("verdict"),
                reviewer_actor_id=reviewer_actor_id,
                verdict_event_id=event.get("event_id"),
                verdict_event_hash=event.get("event_hash"),
                verdict_global_position=event.get("global_position"),
                version=event["stream_version"],
            )
        elif event_type == "AssayReviewed":
            assay = state["assays"].get(payload.get("assay_id"))
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(assay, dict)
                or event.get("stream_id") != payload.get("assay_id")
                or not assay.get("review_pending")
                or assay.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not _review_subject_matches(
                    review,
                    subject_kind="assay",
                    subject_id=payload.get("assay_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
                or payload.get("subject_sha256") != assay.get("review_subject_sha256")
            ):
                raise IntegrityError("invalid Assay reviewed transition")
            assay.update(status="reviewed", review_pending=False, version=event["stream_version"])
        elif event_type in {"AssayPartialReviewed", "AssayCancellationReviewed"}:
            assay = state["assays"].get(payload.get("assay_id"))
            review = state["reviews"].get(payload.get("review_id"))
            expected_status = "partial_recorded" if event_type == "AssayPartialReviewed" else "cancelled"
            if (
                not isinstance(assay, dict)
                or event.get("stream_id") != payload.get("assay_id")
                or assay.get("status") != expected_status
                or assay.get("candidate_id") != payload.get("candidate_id")
                or not assay.get("review_pending")
                or assay.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not _review_subject_matches(
                    review,
                    subject_kind="assay",
                    subject_id=payload.get("assay_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
                or payload.get("subject_sha256") != assay.get("review_subject_sha256")
            ):
                raise IntegrityError("invalid Assay reviewed transition")
            assay.update(
                status="partial_reviewed" if event_type == "AssayPartialReviewed" else "cancellation_reviewed",
                review_pending=False,
                version=event["stream_version"],
            )
        elif event_type in {"CandidateAssayPartialReviewed", "CandidateAssayCancellationReviewed"}:
            candidate = state["candidates"].get(payload.get("candidate_id"))
            assay = state["assays"].get(payload.get("assay_id"))
            expected_status = (
                "assay_partial_recorded" if event_type == "CandidateAssayPartialReviewed" else "assay_cancelled"
            )
            expected_assay_status = (
                "partial_reviewed" if event_type == "CandidateAssayPartialReviewed" else "cancellation_reviewed"
            )
            if (
                not isinstance(candidate, dict)
                or candidate.get("status") != expected_status
                or not isinstance(assay, dict)
                or assay.get("candidate_id") != payload.get("candidate_id")
                or assay.get("status") != expected_assay_status
            ):
                raise IntegrityError("invalid Candidate Assay review transition")
            candidate.update(status="assay_revisit_eligible", version=event["stream_version"])
        elif event_type == "DecisionProposed":
            decision_id = required_string("new_decision_id")
            options = required_string_list("options")
            if (
                event["stream_id"] != decision_id
                or aggregate_identity_exists(decision_id)
                or len(set(options)) != len(options)
            ):
                raise IntegrityError("invalid Discovery decision proposal")
            state["decisions"][decision_id] = {
                "status": "proposed",
                "kind": payload.get("discovery_kind"),
                "decision_kind": required_string("decision_kind"),
                "recommendation": required_string("recommendation"),
                "options": options,
                "expires_at": payload.get("expires_at"),
                "proposal_event_hash": event.get("event_hash"),
                "proposal_version": event["stream_version"],
                "version": event["stream_version"],
            }
        elif event_type == "DecisionResolved":
            decision_id = required_string("decision_id")
            decision = state["decisions"].get(decision_id)
            selected_option = required_string("selected_option")
            if (
                event["stream_id"] != decision_id
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or selected_option not in decision.get("options", ())
            ):
                raise IntegrityError("invalid Discovery decision resolution")
            decision.update(status="resolved", selected_option=selected_option, version=event["stream_version"])
        elif event_type == "SpikeExecutionProposalSupersededByCancellation":
            decision = state["decisions"].get(payload.get("decision_id"))
            spike = state["spikes"].get(payload.get("spike_id"))
            if (
                not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or not isinstance(spike, dict)
                or spike.get("status") != "approval_pending"
                or spike.get("decision_id") != payload.get("decision_id")
                or spike.get("candidate_id") != payload.get("candidate_id")
                or event.get("stream_id") != payload.get("decision_id")
                or not isinstance(event.get("transaction_id"), str)
            ):
                raise IntegrityError("invalid Spike execution proposal cancellation")
            decision.update(
                status="cancellation_pending",
                cancellation_candidate_id=required_string("candidate_id"),
                cancellation_spike_id=required_string("spike_id"),
                cancellation_sha256=required_string("cancellation_sha256"),
                cancellation_transaction_id=event.get("transaction_id"),
                version=event["stream_version"],
            )
        elif event_type in {"AssayRevisitRequested", "SpikeRevisitRequested"}:
            collection = state["assays"] if event_type.startswith("Assay") else state["spikes"]
            subject_id = payload.get("assay_id") if event_type.startswith("Assay") else payload.get("spike_id")
            subject = collection.get(subject_id)
            review = state["reviews"].get(payload.get("review_id"))
            decision = state["decisions"].get(payload.get("decision_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if (
                not isinstance(subject, dict)
                or subject.get("candidate_id") != payload.get("candidate_id")
                or subject.get("status") not in {"partial_reviewed", "cancellation_reviewed", "reviewed", "parked"}
                or subject.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not _valid_revisit_proposal(payload.get("w2_payload"), payload.get("review_id"))
                or payload["w2_payload"].get("new_decision_id") != payload.get("decision_id")
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or decision.get("options") != payload["w2_payload"].get("options")
                or not isinstance(candidate, dict)
                or not _revisit_relation_matches(
                    payload.get("revisit_relation"),
                    decision_id=payload.get("decision_id"),
                    candidate=candidate,
                    aggregate_id=subject_id,
                    aggregate=subject,
                    review=review,
                    observations=state["source_observations"],
                    recommendation=payload["w2_payload"].get("recommendation"),
                    actor_id=event.get("actor_id"),
                )
            ):
                raise IntegrityError("invalid Discovery revisit request")
            subject.update(
                status="revisit_pending",
                decision_id=required_string("decision_id"),
                revisit_relation=deepcopy(payload["revisit_relation"]),
            )
        elif event_type in {"CandidateAssayRevisitRequested", "CandidateSpikeRevisitRequested"}:
            candidate = state["candidates"].get(payload.get("candidate_id"))
            kind = "assay" if event_type.startswith("CandidateAssay") else "spike"
            if not isinstance(candidate, dict) or candidate.get("status") not in {f"{kind}_revisit_eligible", "parked"}:
                raise IntegrityError("invalid Candidate revisit request")
            candidate.update(status=f"{kind}_revisit_pending", decision_id=required_string("decision_id"))
        elif event_type in {"AssayRevisitResolved", "SpikeRevisitResolved"}:
            collection = state["assays"] if event_type.startswith("Assay") else state["spikes"]
            subject_id = payload.get("assay_id") if event_type.startswith("Assay") else payload.get("spike_id")
            subject = collection.get(subject_id)
            decision = state["decisions"].get(payload.get("decision_id"))
            selected = required_string("selected_option")
            if (
                not isinstance(subject, dict)
                or subject.get("status") != "revisit_pending"
                or subject.get("candidate_id") != payload.get("candidate_id")
                or not isinstance(decision, dict)
                or decision.get("status") != "resolved"
                or decision.get("selected_option") != selected
                or selected not in {"RETRY", "PARK", "KILL"}
            ):
                raise IntegrityError("invalid Discovery revisit resolution")
            subject.update(status={"RETRY": "retry_authorized", "PARK": "parked", "KILL": "killed"}[selected])
            if selected == "PARK":
                subject["parked_at_global_position"] = event["global_position"]
        elif event_type in {"CandidateAssayRevisitResolved", "CandidateSpikeRevisitResolved"}:
            candidate = state["candidates"].get(payload.get("candidate_id"))
            kind = "assay" if event_type.startswith("CandidateAssay") else "spike"
            selected = required_string("selected_option")
            if not isinstance(candidate, dict) or candidate.get("status") != f"{kind}_revisit_pending":
                raise IntegrityError("invalid Candidate revisit resolution")
            candidate.update(
                status={"RETRY": f"{kind}_retry_authorized", "PARK": "parked", "KILL": "killed"}.get(selected)
            )
            if candidate.get("status") is None:
                raise IntegrityError("invalid Candidate revisit option")
            if selected == "PARK":
                candidate["parked_at_global_position"] = event["global_position"]
        elif event_type in {"AssaySuperseded", "SpikeSuperseded"}:
            collection = state["assays"] if event_type.startswith("Assay") else state["spikes"]
            subject_id = payload.get("old_assay_id") if event_type.startswith("Assay") else payload.get("old_spike_id")
            subject = collection.get(subject_id)
            if not isinstance(subject, dict) or subject.get("status") != "retry_authorized":
                raise IntegrityError("invalid Discovery retry supersession")
            subject.update(status="superseded")
        elif event_type in {"CandidateAssayRetryStarted", "CandidateSpikeRetryStarted"}:
            candidate = state["candidates"].get(payload.get("candidate_id"))
            kind = "assay" if event_type.startswith("CandidateAssay") else "spike"
            new_id = payload.get("assay_id") if kind == "assay" else payload.get("spike_id")
            if not isinstance(candidate, dict) or candidate.get("status") != f"{kind}_retry_authorized":
                raise IntegrityError("invalid Candidate retry transition")
            candidate.update(status=f"{kind}_pending" if kind == "assay" else "spike_approval_pending")
            candidate[f"{kind}_id"] = new_id
        elif event_type == "CandidatePromotionRequested":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            decision = state["decisions"].get(payload.get("decision_id"))
            gate = required_string("promotion_gate")
            expected_status = {
                "assay_to_spike": "assay_scored",
                "spike_to_preregistration": "spike_verdict_recorded",
            }.get(gate)
            aggregate_id = (
                candidate.get("assay_id" if gate == "assay_to_spike" else "spike_id")
                if isinstance(candidate, dict)
                else None
            )
            aggregate = (
                state["assays"].get(aggregate_id) if gate == "assay_to_spike" else state["spikes"].get(aggregate_id)
            )
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(candidate, dict)
                or candidate.get("status") != expected_status
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or not _valid_promotion_options(decision.get("options"))
                or not isinstance(aggregate, dict)
                or not isinstance(review, dict)
                or not _promotion_relation_matches(
                    payload.get("promotion_relation"),
                    decision_id=payload.get("decision_id"),
                    candidate=candidate,
                    aggregate_id=aggregate_id,
                    aggregate=aggregate,
                    review=review,
                    gate=gate,
                    recommendation=decision.get("recommendation"),
                    actor_id=event.get("actor_id"),
                )
                or (
                    decision.get("recommendation") == "PROMOTE"
                    and gate == "assay_to_spike"
                    and aggregate.get("mechanical_recommendation") != "PROMOTE"
                )
                or (
                    gate == "spike_to_preregistration"
                    and not _valid_spike_promotion_option(aggregate, decision.get("recommendation"))
                )
            ):
                raise IntegrityError("invalid Candidate promotion request")
            decision.update(kind="discovery_promotion", promotion_relation=deepcopy(payload["promotion_relation"]))
            candidate.update(
                status="promotion_pending",
                decision_id=required_string("decision_id"),
                promotion_gate=gate,
            )
        elif event_type == "CandidatePromotionApplied":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            decision = state["decisions"].get(payload.get("decision_id"))
            gate = required_string("promotion_gate")
            selected_option = required_string("selected_option")
            next_state = required_string("next_candidate_state")
            expected_next_state = {
                "PROMOTE": {
                    "assay_to_spike": "spike_planning_authorized",
                    "spike_to_preregistration": "preregistration_authorized",
                }.get(gate),
                "PARK": "parked",
                "KILL": "killed",
            }.get(selected_option)
            if (
                not isinstance(candidate, dict)
                or candidate.get("status") != "promotion_pending"
                or candidate.get("decision_id") != payload.get("decision_id")
                or candidate.get("promotion_gate") != gate
                or next_state != expected_next_state
                or not isinstance(decision, dict)
                or decision.get("status") != "resolved"
                or decision.get("kind") != "discovery_promotion"
                or decision.get("selected_option") != selected_option
                or (
                    selected_option == "PROMOTE"
                    and gate == "assay_to_spike"
                    and state["assays"].get(candidate.get("assay_id"), {}).get("mechanical_recommendation") != "PROMOTE"
                )
                or (
                    gate == "spike_to_preregistration"
                    and not _valid_spike_promotion_option(
                        state["spikes"].get(candidate.get("spike_id"), {}),
                        selected_option,
                    )
                )
            ):
                raise IntegrityError("invalid Candidate promotion application")
            candidate.update(status=next_state)
            if selected_option == "PARK":
                candidate["parked_at_global_position"] = event["global_position"]
        elif event_type == "SpikePlanned":
            spike_id = required_string("spike_id")
            candidate = state["candidates"].get(payload.get("candidate_id"))
            assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
            artifact = payload.get("plan_artifact")
            if aggregate_identity_exists(spike_id):
                raise IntegrityError("Spike identity collision")
            if (
                not isinstance(candidate, Mapping)
                or not isinstance(artifact, Mapping)
                or not _spike_plan_matches(
                    artifact,
                    payload,
                    candidate,
                    assay,
                    state["decisions"].get(candidate.get("decision_id")),
                )
            ):
                raise IntegrityError("invalid Spike plan")
            state["spikes"][spike_id] = {**deepcopy(payload), "status": "planned", "version": event["stream_version"]}
        elif event_type == "SpikeApprovalRequested":
            spike = state["spikes"].get(payload.get("spike_id"))
            if not isinstance(spike, dict):
                raise IntegrityError("invalid Spike approval request")
            spike.update(status="approval_pending")
        elif event_type == "CandidateSpikePlanLinked":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict):
                raise IntegrityError("invalid Candidate Spike plan link")
            candidate.update(status="spike_approval_pending", spike_id=required_string("spike_id"))
        elif event_type == "SpikeExecutionDecisionRequested":
            spike = state["spikes"].get(payload.get("spike_id"))
            decision = state["decisions"].get(payload.get("decision_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
            relation = payload.get("execution_authority_relation")
            resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
            try:
                operational = replay_control_plane(operational_events)
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityError("invalid Spike execution decision request") from exc
            resource = (
                operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
            )
            if (
                not isinstance(spike, dict)
                or not isinstance(decision, dict)
                or not isinstance(candidate, dict)
                or not isinstance(assay, dict)
                or decision.get("status") != "proposed"
                or not _valid_spike_execution_proposal(payload.get("w2_payload"))
                or payload["w2_payload"].get("new_decision_id") != payload.get("decision_id")
                or not isinstance(resource, Mapping)
                or not _spike_execution_relation_matches(
                    relation,
                    candidate=candidate,
                    assay=assay,
                    spike=spike,
                    decision_id=payload.get("decision_id"),
                    resource=resource,
                )
            ):
                raise IntegrityError("invalid Spike execution decision request")
            spike.update(
                decision_id=required_string("decision_id"),
                execution_authority_relation=deepcopy(payload["execution_authority_relation"]),
            )
        elif event_type == "SpikeAuthorized":
            spike = state["spikes"].get(payload.get("spike_id"))
            decision = state["decisions"].get(payload.get("decision_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
            relation = payload.get("execution_authority_relation")
            resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
            try:
                operational = replay_control_plane(operational_events)
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityError("invalid Spike authorization") from exc
            resource = (
                operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
            )
            if (
                not isinstance(spike, dict)
                or spike.get("decision_id") != payload.get("decision_id")
                or not isinstance(decision, dict)
                or not isinstance(candidate, Mapping)
                or not isinstance(assay, Mapping)
                or decision.get("status") != "resolved"
                or decision.get("selected_option") != "approve"
                or relation != spike.get("execution_authority_relation")
                or spike.get("execution_authority_relation", {}).get("actor_id") != event.get("actor_id")
                or not isinstance(resource, Mapping)
                or resource.get("status") != "active"
                or not _spike_execution_relation_matches(
                    relation,
                    candidate=candidate,
                    assay=assay,
                    spike=spike,
                    decision_id=payload.get("decision_id"),
                    resource=resource,
                )
            ):
                raise IntegrityError("invalid Spike authorization")
            spike.update(status="authorized")
        elif event_type == "CandidateSpikeAuthorized":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict):
                raise IntegrityError("invalid Candidate Spike authorization")
            candidate.update(status="spike_authorized")
        elif event_type == "SpikeStarted":
            spike = state["spikes"].get(payload.get("spike_id"))
            attempt_id = required_string("attempt_id")
            lease_id = required_string("lease_id")
            if (
                not isinstance(spike, dict)
                or spike.get("status") != "authorized"
                or not _spike_execution_ids_available(
                    state["spikes"],
                    payload.get("spike_id"),
                    attempt_id,
                    lease_id,
                )
                or payload.get("execution_authority_relation") != spike.get("execution_authority_relation")
                or spike.get("execution_authority_relation", {}).get("resource_ref", {}).get("id")
                != payload.get("resource_grant_id")
                or not _spike_start_operational_matches(operational_events, event, payload)
            ):
                raise IntegrityError("invalid Spike start")
            spike.update(
                status="running",
                attempt_id=attempt_id,
                attempt_sha256=required_string("attempt_sha256"),
                lease_id=lease_id,
                lease_sha256=required_string("lease_sha256"),
                lease_status="active",
            )
        elif event_type == "CandidateSpikeStarted":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict):
                raise IntegrityError("invalid Candidate Spike start")
            candidate.update(status="spike_running")
        elif event_type == "SpikeVerdictRecorded":
            spike = state["spikes"].get(payload.get("spike_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
            artifact = payload.get("verdict_artifact")
            if (
                not isinstance(spike, dict)
                or not isinstance(candidate, dict)
                or not isinstance(assay, dict)
                or not isinstance(artifact, dict)
                or spike.get("status") != "running"
                or not _spike_verdict_matches(
                    artifact, payload, candidate, assay, spike, state, canonical_artefact_streams
                )
            ):
                raise IntegrityError("invalid Spike verdict")
            spike.update(
                status="verdict_recorded",
                verdict=required_string("verdict"),
                verdict_sha256=required_string("verdict_sha256"),
                verdict_artifact=deepcopy(artifact),
                producer_actor_id=event.get("actor_id"),
            )
        elif event_type == "SpikePartialRecorded":
            spike = state["spikes"].get(payload.get("spike_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            assay = state["assays"].get(candidate.get("assay_id")) if isinstance(candidate, Mapping) else None
            artifact = payload.get("verdict_artifact")
            if (
                not isinstance(spike, dict)
                or not isinstance(candidate, dict)
                or not isinstance(assay, dict)
                or not isinstance(artifact, dict)
                or spike.get("status") != "running"
                or not _spike_verdict_matches(
                    artifact, payload, candidate, assay, spike, state, canonical_artefact_streams
                )
            ):
                raise IntegrityError("invalid Spike partial verdict")
            spike.update(
                status="partial_recorded",
                verdict=required_string("verdict"),
                verdict_sha256=required_string("verdict_sha256"),
                verdict_artifact=deepcopy(artifact),
                revisit_requirements=deepcopy(spike.get("plan_artifact", {}).get("partial_rules", [])),
                producer_actor_id=event.get("actor_id"),
            )
        elif event_type == "SpikeAttemptClosed":
            spike = state["spikes"].get(payload.get("spike_id"))
            if (
                not isinstance(spike, dict)
                or spike.get("status") not in {"partial_recorded", "cancelled"}
                or spike.get("attempt_id") != payload.get("attempt_id")
            ):
                raise IntegrityError("invalid Spike attempt closure")
            spike.update(attempt_status="cancelled" if spike.get("status") == "cancelled" else "partial")
        elif event_type == "SpikeLeaseReleased":
            spike = state["spikes"].get(payload.get("spike_id"))
            if (
                not isinstance(spike, dict)
                or spike.get("attempt_status") not in {"partial", "cancelled"}
                or payload.get("lease_id") != spike.get("lease_id")
            ):
                raise IntegrityError("invalid Spike lease release")
            spike.update(lease_status="released")
        elif event_type == "CandidateSpikeVerdictLinked":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict):
                raise IntegrityError("invalid Candidate Spike verdict link")
            candidate.update(status="spike_verdict_recorded")
        elif event_type == "CandidateSpikePartialLinked":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "spike_running":
                raise IntegrityError("invalid Candidate Spike partial link")
            candidate.update(status="spike_partial_recorded")
        elif event_type in {"SpikeReviewRequested", "SpikePartialReviewRequested", "SpikeCancellationReviewRequested"}:
            spike = state["spikes"].get(payload.get("spike_id"))
            expected_status = {
                "SpikeReviewRequested": "verdict_recorded",
                "SpikePartialReviewRequested": "partial_recorded",
                "SpikeCancellationReviewRequested": "cancelled",
            }[event_type]
            if not isinstance(spike, dict) or spike.get("status") != expected_status:
                raise IntegrityError("invalid Spike review request")
            review = state["reviews"].get(payload.get("review_id"))
            prior_review = state["reviews"].get(spike.get("review_id"))
            relation = payload.get("review_subject_supersession")
            if (
                event.get("stream_id") != payload.get("spike_id")
                or spike.get("candidate_id") != payload.get("candidate_id")
                or not _review_subject_matches(
                    review,
                    subject_kind="spike",
                    subject_id=payload.get("spike_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
            ):
                raise IntegrityError("invalid Spike review request")
            if spike.get("review_id") is None:
                if relation is not None or payload.get("subject_sha256") != _aggregate_content_hash(spike):
                    raise IntegrityError("invalid Spike review supersession")
            elif not _valid_review_supersession(
                relation,
                prior_review,
                review.get("subject_sha256"),
                review.get("required_evidence_refs"),
            ):
                raise IntegrityError("invalid Spike review supersession")
            else:
                prior_review.update(status="superseded", superseded_by_review_id=review["review_id"])
            spike.update(
                review_id=required_string("review_id"),
                review_subject_sha256=required_string("subject_sha256"),
                review_pending=True,
            )
        elif event_type == "SpikeReviewed":
            spike = state["spikes"].get(payload.get("spike_id"))
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(spike, dict)
                or event.get("stream_id") != payload.get("spike_id")
                or not spike.get("review_pending")
                or spike.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not _review_subject_matches(
                    review,
                    subject_kind="spike",
                    subject_id=payload.get("spike_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
                or payload.get("subject_sha256") != spike.get("review_subject_sha256")
            ):
                raise IntegrityError("invalid Spike reviewed transition")
            spike.update(status="reviewed", review_pending=False)
        elif event_type == "CandidateSpikePartialReviewed":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "spike_partial_recorded":
                raise IntegrityError("invalid Candidate Spike partial review")
            candidate.update(status="spike_revisit_eligible")
        elif event_type == "SpikePartialReviewed":
            spike = state["spikes"].get(payload.get("spike_id"))
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(spike, dict)
                or event.get("stream_id") != payload.get("spike_id")
                or spike.get("status") != "partial_recorded"
                or not spike.get("review_pending")
                or spike.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not _review_subject_matches(
                    review,
                    subject_kind="spike",
                    subject_id=payload.get("spike_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
                or payload.get("subject_sha256") != spike.get("review_subject_sha256")
            ):
                raise IntegrityError("invalid Spike partial review")
            spike.update(status="partial_reviewed", review_pending=False)
        elif event_type == "SpikeCancelled":
            spike = state["spikes"].get(payload.get("spike_id"))
            candidate = state["candidates"].get(payload.get("candidate_id"))
            decision = state["decisions"].get(spike.get("decision_id")) if isinstance(spike, Mapping) else None
            if (
                not isinstance(spike, dict)
                or not isinstance(candidate, dict)
                or event.get("stream_id") != payload.get("spike_id")
                or spike.get("status") not in {"planned", "approval_pending", "authorized", "running"}
                or not _spike_cancellation_matches(
                    payload.get("cancellation_artifact"),
                    payload=payload,
                    candidate=candidate,
                    spike=spike,
                    decision=decision,
                    state=state,
                )
            ):
                raise IntegrityError("invalid Spike cancellation")
            decision = state["decisions"].get(spike.get("decision_id"))
            if spike.get("status") == "approval_pending" and spike.get("decision_id") is not None:
                if (
                    not isinstance(decision, dict)
                    or decision.get("status") != "cancellation_pending"
                    or decision.get("cancellation_candidate_id") != payload.get("candidate_id")
                    or decision.get("cancellation_spike_id") != payload.get("spike_id")
                    or decision.get("cancellation_sha256") != payload.get("cancellation_sha256")
                    or decision.get("cancellation_transaction_id") != event.get("transaction_id")
                ):
                    raise IntegrityError("invalid Spike execution proposal cancellation")
                decision.update(status="candidate_cancellation_pending")
            spike.update(
                status="cancelled",
                outcome_sha256=required_string("cancellation_sha256"),
                producer_actor_id=event.get("actor_id"),
            )
        elif event_type == "SpikeCancellationReviewed":
            spike = state["spikes"].get(payload.get("spike_id"))
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(spike, dict)
                or event.get("stream_id") != payload.get("spike_id")
                or spike.get("status") != "cancelled"
                or not spike.get("review_pending")
                or spike.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not _review_subject_matches(
                    review,
                    subject_kind="spike",
                    subject_id=payload.get("spike_id"),
                    subject_sha256=payload.get("subject_sha256"),
                )
                or payload.get("subject_sha256") != spike.get("review_subject_sha256")
            ):
                raise IntegrityError("invalid Spike cancellation review")
            spike.update(status="cancellation_reviewed", review_pending=False)
        elif event_type == "CandidateSpikeCancellationReviewed":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "spike_cancelled":
                raise IntegrityError("invalid Candidate Spike cancellation review")
            candidate.update(status="spike_revisit_eligible")
        elif event_type == "ResearchDossierAdmitted":
            dossier_id = payload.get("dossier_id")
            if not isinstance(dossier_id, str) or aggregate_identity_exists(dossier_id):
                raise IntegrityError("Research dossier identity collision")
            if not _accepted_dossier_admission_matches(
                state["authorities"].get("dossier_expected_set"),
                event,
                payload,
            ):
                raise IntegrityError("Research dossier admission authority mismatch")
            state["dossiers"][dossier_id] = {**deepcopy(payload), "status": "admitted"}
        elif event_type == "PortfolioObjectRegistered":
            record_id = payload.get("record_id")
            blueprint = payload.get("blueprint")
            if isinstance(blueprint, dict) and "proposed_edge_id" in blueprint:
                blueprint_preimage = {
                    key: deepcopy(value) for key, value in blueprint.items() if key != "expected_content_hash"
                }
            elif isinstance(blueprint, dict):
                blueprint_preimage = {
                    key: deepcopy(value)
                    for key, value in blueprint.items()
                    if key not in {"blueprint_hash", "expected_content_hash"}
                }
            else:
                blueprint_preimage = {}
            blueprint_hash = sha256_hex(canonical_bytes(blueprint_preimage))
            if (
                not isinstance(record_id, str)
                or aggregate_identity_exists(record_id)
                or not isinstance(blueprint, dict)
                or blueprint.get("proposed_record_id", blueprint.get("proposed_edge_id")) != record_id
                or payload.get("record_revision") != 1
                or payload.get("content_sha256") != blueprint_hash
                or blueprint.get("expected_content_hash") != blueprint_hash
                or ("proposed_record_id" in blueprint and blueprint.get("blueprint_hash") != blueprint_hash)
            ):
                raise IntegrityError("Portfolio object identity collision")
            state["portfolio_objects"][record_id] = deepcopy(payload)
        elif event_type == "ScopeDefinitionRegistered":
            scope_id = payload.get("scope_id")
            blueprint = payload.get("blueprint")
            blueprint_preimage = (
                {
                    key: deepcopy(value)
                    for key, value in blueprint.items()
                    if key not in {"blueprint_hash", "expected_content_hash"}
                }
                if isinstance(blueprint, dict)
                else {}
            )
            blueprint_hash = sha256_hex(canonical_bytes(blueprint_preimage))
            if (
                not isinstance(scope_id, str)
                or aggregate_identity_exists(scope_id)
                or not isinstance(blueprint, dict)
                or blueprint.get("proposed_scope_id") != scope_id
                or payload.get("scope_revision") != 1
                or payload.get("content_sha256") != blueprint_hash
                or blueprint.get("blueprint_hash") != blueprint_hash
                or blueprint.get("expected_content_hash") != blueprint_hash
            ):
                raise IntegrityError("Scope identity collision")
            state["scopes"][scope_id] = deepcopy(payload)
        else:
            raise IntegrityError(f"unsupported Discovery event: {event_type}")
    if any(
        decision.get("status") in {"cancellation_pending", "candidate_cancellation_pending"}
        for decision in state["decisions"].values()
    ):
        raise IntegrityError("incomplete Spike execution proposal cancellation")
    for dossier_id, dossier in state["dossiers"].items():
        object_count = sum(
            value.get("dossier_id") == dossier_id and value.get("portfolio_kind") != "dependency_edge"
            for value in state["portfolio_objects"].values()
        )
        edge_count = sum(
            value.get("dossier_id") == dossier_id and value.get("portfolio_kind") == "dependency_edge"
            for value in state["portfolio_objects"].values()
        )
        scope_count = sum(value.get("dossier_id") == dossier_id for value in state["scopes"].values())
        semantic_identities: dict[str, tuple[int, str]] = {}
        semantic_identity_collision = False
        for value in state["portfolio_objects"].values():
            blueprint = value.get("blueprint")
            if (
                value.get("dossier_id") == dossier_id
                and value.get("portfolio_kind") != "dependency_edge"
                and isinstance(blueprint, dict)
                and isinstance(blueprint.get("object_key"), str)
            ):
                if blueprint["object_key"] in semantic_identities:
                    semantic_identity_collision = True
                semantic_identities[blueprint["object_key"]] = (
                    value.get("record_revision"),
                    value.get("content_sha256"),
                )
        for value in state["scopes"].values():
            blueprint = value.get("blueprint")
            if (
                value.get("dossier_id") == dossier_id
                and isinstance(blueprint, dict)
                and isinstance(blueprint.get("scope_key"), str)
            ):
                if blueprint["scope_key"] in semantic_identities:
                    semantic_identity_collision = True
                semantic_identities[blueprint["scope_key"]] = (
                    value.get("scope_revision"),
                    value.get("content_sha256"),
                )
        relationships = dossier.get("relationships")
        relationship_keys: set[str] = set()
        valid_relationships = isinstance(relationships, list) and bool(relationships)
        if valid_relationships:
            for relationship in relationships:
                if not isinstance(relationship, dict):
                    valid_relationships = False
                    break
                relationship_key = relationship.get("relationship_key")
                members = relationship.get("ordered_member_keys_with_revisions_hashes")
                if (
                    not isinstance(relationship_key, str)
                    or relationship_key in relationship_keys
                    or not isinstance(members, list)
                    or not members
                    or not isinstance(relationship.get("relationship_kind"), str)
                    or not isinstance(relationship.get("relation_schema_id"), str)
                    or not isinstance(relationship.get("relation_schema_version"), str)
                    or any(
                        not isinstance(member, dict)
                        or not isinstance(member.get("key"), str)
                        or (member.get("revision"), member.get("content_hash"))
                        != semantic_identities.get(member.get("key"))
                        for member in members
                    )
                    or {member["key"] for member in members} != set(semantic_identities)
                    or relationship.get("relation_hash") != sha256_hex(canonical_bytes(members))
                ):
                    valid_relationships = False
                    break
                relationship_keys.add(relationship_key)
        if (
            dossier.get("object_count") != object_count
            or dossier.get("edge_count") != edge_count
            or dossier.get("scope_count") != scope_count
            or dossier.get("relationship_count") != len(relationship_keys)
            or not valid_relationships
            or semantic_identity_collision
        ):
            raise IntegrityError("Research dossier materialization closure mismatch")
    return state


class DiscoveryRuntime:
    """Public, provider-free W11 genesis and Discovery lifecycle seam."""

    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        schemas: SchemaRegistry,
        *,
        catalogue_path: Path,
        authority_resolver: LedgerAuthorityGrantResolver,
        clock: Callable[[], datetime],
        repository_root: Path,
        root_tokens: Mapping[str, Path],
        operational_ledger: EventLedger,
    ) -> None:
        """Bind the governed runtime to exact repository and root configuration.

        Args:
            control_root: Discovery receipt and writer-lock root.
            ledger: Durable Discovery event ledger.
            schemas: Active schema registry used for command and event identities.
            catalogue_path: Exact accepted W11 catalogue path.
            authority_resolver: Canonical current-grant resolver.
            clock: Trusted timezone-aware runtime clock.
            repository_root: Repository root containing the accepted catalogue and authority files.
            root_tokens: Accepted dossier path tokens and their configured physical roots.
            operational_ledger: Canonical same-project Attempt and Lease ledger.

        Raises:
            IntegrityError: If configured paths, project identity, or runtime bindings are inconsistent.
            TypeError: If a canonical authority resolver or concrete operational ledger is not supplied.
        """
        self.control_root = control_root
        self.ledger = ledger
        self.schemas = schemas
        self.catalogue_path = catalogue_path
        try:
            self.repository_root = repository_root.resolve(strict=True)
        except OSError as exc:
            raise IntegrityError("configured repository root is unavailable") from exc
        try:
            resolved_catalogue = catalogue_path.resolve(strict=True)
        except OSError as exc:
            raise IntegrityError("catalogue path is unavailable") from exc
        try:
            resolved_catalogue.relative_to(self.repository_root)
        except ValueError as exc:
            raise IntegrityError("catalogue path is outside configured repository root") from exc
        self.root_tokens = {key: Path(value) for key, value in root_tokens.items()}
        if type(operational_ledger) is not EventLedger:
            raise TypeError("DiscoveryRuntime requires a concrete operational EventLedger")
        if operational_ledger.project_id != ledger.project_id:
            raise IntegrityError("operational ledger project mismatch")
        if operational_ledger is not ledger:
            raise IntegrityError("Discovery and operational state require one atomic ledger")
        self.operational_ledger = operational_ledger
        self.receipts = ReceiptStore(control_root)
        if not isinstance(authority_resolver, LedgerAuthorityGrantResolver):
            raise TypeError("DiscoveryRuntime requires LedgerAuthorityGrantResolver")
        self.authority_resolver = authority_resolver
        self.clock = clock

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Authorize and atomically submit one public Discovery command.

        Args:
            envelope: Complete governed command envelope.

        Returns:
            Durable accepted, rejected, or conflict receipt for the exact command.

        Raises:
            ConflictError: If a committed receipt or writer state conflicts with the command identity.
            IntegrityError: If authority, payload, replay state, or the requested transition is invalid.
        """
        if set(envelope) != _COMMAND_FIELDS or not isinstance(envelope.get("payload"), dict):
            raise IntegrityError("invalid Discovery command envelope")
        command = Command(deepcopy(envelope))
        try:
            command.payload_hash
        except (TypeError, ValueError) as exc:
            raise IntegrityError("Discovery command payload is not P0-canonical") from exc
        if envelope["command_type"] == "ImportAcceptedW11CatalogueGenesis" and command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        with CompositeWriterLock(
            (self.control_root, self.authority_resolver.control_root, self.operational_ledger.control_root),
            {"command_id": command.command_id},
            lock_factory=WriterLock,
        ):
            authority_evidence = self._resolve_authority(command)
            return self._submit_authorized(command, authority_evidence)

    def _resolve_authority(self, command: Command) -> Any:
        """Resolve current canonical scoped authority for one command."""
        command_type = command.envelope["command_type"]
        binding = self.schemas.command_binding(command_type)
        if binding is None:
            raise IntegrityError(f"inactive Discovery command binding: {command_type}")
        identity = self.schemas.resolve_identity(binding.schema_id, binding.schema_version)
        subject_kind = {
            "ImportAcceptedW11CatalogueGenesis": "scope_definition",
            "IngestScoutObservationBatch": "scope_definition",
            "RegisterCandidate": "scope_definition",
            "SupersedeDiscoveryRecord": "scope_definition",
            "RequestAssay": "scope_definition",
            "RecordAssayScore": "scope_definition",
            "RecordAssayPartial": "scope_definition",
            "CancelDiscoveryEvaluation": "scope_definition",
            "ProposeRevisitDecision": "decision",
            "RequestDiscoveryOutcomeReview": "review",
            "ReviewDiscoveryOutcome": "review",
            "ProposePromotionDecision": "decision",
            "RegisterSpikePlan": "scope_definition",
            "ProposeSpikeExecutionDecision": "decision",
            "StartSpike": "scope_definition",
            "RecordSpikeVerdict": "scope_definition",
            "RegisterAssayRubricContent": "scope_definition",
            "RegisterAssayEvidenceScopeContent": "scope_definition",
            "RecordAssayBarStaleness": "decision",
            "RegisterDossierExpectedSetContent": "scope_definition",
            "RegisterPathRegistrationContent": "scope_definition",
            "ObserveW11AuthorityFile": "scope_definition",
            "RequestW11AuthorityReview": "review",
            "RecordW11AuthorityReview": "review",
            "ProposeW11AuthorityDecision": "decision",
            "ResolveDecision": "decision",
            "AdmitResearchDossier": "scope_definition",
        }.get(command_type)
        if subject_kind is None:
            raise IntegrityError(f"unsupported Discovery authority command: {command_type}")
        subject_id = command.target_stream_id
        if command_type in {
            "RequestAssay",
            "RecordAssayScore",
            "RecordAssayPartial",
            "CancelDiscoveryEvaluation",
            "RegisterSpikePlan",
            "StartSpike",
            "RecordSpikeVerdict",
        }:
            subject_id = command.envelope["payload"].get("candidate_id")
            if not isinstance(subject_id, str):
                raise IntegrityError("Discovery lifecycle authority requires candidate_id")
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery authority clock must return an aware datetime")
        return self.authority_resolver.resolve_lifecycle_command(
            command.envelope["authority_grant_id"],
            command.actor_id,
            GrantedCommandIdentity(
                command_type=command_type,
                schema_id=identity.schema_id,
                schema_version=identity.schema_version,
                schema_sha256=identity.sha256,
            ),
            "R2",
            self.ledger.project_id,
            subject_kind,
            subject_id,
            now.astimezone(UTC),
        )

    @staticmethod
    def _require_candidate_target(command: Command, projection: Mapping[str, Any]) -> None:
        """Fence Candidate-scoped authority to the exact lifecycle stream it may mutate."""

        command_type = command.envelope["command_type"]
        if command_type not in {
            "RequestAssay",
            "RecordAssayScore",
            "RecordAssayPartial",
            "CancelDiscoveryEvaluation",
            "RegisterSpikePlan",
            "StartSpike",
            "RecordSpikeVerdict",
        }:
            return
        payload = command.envelope["payload"]
        candidate_id = payload.get("candidate_id")
        target_id = command.target_stream_id
        if not isinstance(candidate_id, str) or candidate_id not in projection["candidates"]:
            raise IntegrityError("Discovery lifecycle target is outside authorized Candidate")
        if command_type == "RequestAssay":
            valid = target_id == payload.get("assay_id") and not _discovery_identity_exists(projection, target_id)
        elif command_type in {"RecordAssayScore", "RecordAssayPartial"}:
            assay = projection["assays"].get(target_id)
            valid = isinstance(assay, Mapping) and assay.get("candidate_id") == candidate_id
        elif command_type == "RegisterSpikePlan":
            valid = target_id == payload.get("spike_id") and not _discovery_identity_exists(projection, target_id)
        elif command_type in {"StartSpike", "RecordSpikeVerdict"}:
            spike = projection["spikes"].get(target_id)
            valid = isinstance(spike, Mapping) and spike.get("candidate_id") == candidate_id
        elif payload.get("evaluation_kind") == "assay":
            assay = projection["assays"].get(target_id)
            valid = (
                target_id == payload.get("assay_id")
                and isinstance(assay, Mapping)
                and assay.get("candidate_id") == candidate_id
            )
        else:
            spike = projection["spikes"].get(target_id)
            valid = (
                target_id == payload.get("spike_id")
                and isinstance(spike, Mapping)
                and spike.get("candidate_id") == candidate_id
            )
        if not valid:
            raise IntegrityError("Discovery lifecycle target is outside authorized Candidate")

    @staticmethod
    def _require_admissible_target(command: Command, projection: Mapping[str, Any]) -> None:
        """Apply the row registry's global mint-or-advance identity contract."""

        row_id, _ = _discovery_route(command)
        target = command.target_stream_id
        if row_id in _DISCOVERY_MINT_ROWS:
            if row_id == "OR-101" and projection["authority_streams"].get(target) == "assay_bar":
                return
            if _discovery_identity_exists(projection, target):
                raise IntegrityError("Discovery command target identity collision")
            return
        collection = _DISCOVERY_EXISTING_TARGETS[row_id]
        if collection == "authority_streams":
            authority_kind = command.envelope["payload"].get("authority_kind")
            if projection[collection].get(target) != authority_kind:
                raise IntegrityError("W11 authority stream identity collision")
            return
        if target not in projection.get(collection, {}):
            raise IntegrityError("Discovery command target is owned by another aggregate")

    def _submit_authorized(self, command: Command, authority_evidence: Any) -> Receipt:
        """Prepare, append, and receipt one already-authorized command."""
        envelope = command.envelope
        authority_sha256 = authority_evidence.command_resolution.authority_grant_sha256
        idempotency_scope = (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )
        envelope_sha256 = sha256_hex(
            canonical_bytes(
                {
                    "command_id": command.command_id,
                    "command_type": envelope["command_type"],
                    "actor_id": command.actor_id,
                    "authority_grant_id": envelope["authority_grant_id"],
                    "authority_grant_sha256": authority_sha256,
                    "idempotency_key": command.idempotency_key,
                    "target_stream_id": command.target_stream_id,
                    "expected_stream_version": command.expected_stream_version,
                    "payload_hash": command.payload_hash,
                }
            )
        )

        def persist(receipt: Receipt) -> Receipt:
            return self.receipts.write_scoped(
                idempotency_scope,
                authority_sha256,
                command.expected_stream_version,
                receipt,
                project_id=self.ledger.project_id,
                target_stream_id=command.target_stream_id,
            )

        scoped = self.receipts.load_scoped(
            idempotency_scope,
            command.payload_hash,
            authority_sha256,
            command.expected_stream_version,
            project_id=self.ledger.project_id,
            target_stream_id=command.target_stream_id,
        )
        if scoped is not None:
            if self.receipts.load(scoped.command_id) is None:
                self.receipts.write(scoped)
            return scoped
        snapshot = self.ledger.snapshot()

        def committed_envelope_matches(event: Mapping[str, Any]) -> bool:
            """Bind a recovered command id to the complete immutable submission envelope."""

            return bool(
                event.get("command_payload_hash") == command.payload_hash
                and event.get("command_type") == envelope["command_type"]
                and event.get("actor_id") == command.actor_id
                and event.get("authority_grant_id") == envelope["authority_grant_id"]
                and event.get("idempotency_key") == command.idempotency_key
                and event.get("correlation_id") == envelope_sha256
            )

        committed = next(
            (event for event in snapshot.events if event.get("command_id") == command.command_id),
            None,
        )
        existing = self.receipts.load(command.command_id)
        if existing is not None:
            if (
                existing.status != "accepted"
                or existing.payload_hash != command.payload_hash
                or not isinstance(committed, Mapping)
                or not committed_envelope_matches(committed)
            ):
                raise ConflictError("command receipt envelope mismatch")
            return persist(existing)
        if committed is not None:
            if not committed_envelope_matches(committed):
                raise ConflictError("committed command envelope mismatch")
            transaction_events = tuple(
                event for event in snapshot.events if event.get("transaction_id") == committed["transaction_id"]
            )
            target_versions = [
                event["stream_version"]
                for event in transaction_events
                if event.get("stream_id") == command.target_stream_id
            ]
            receipt = Receipt(
                status="accepted",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=committed["transaction_id"],
                observed_stream_version=max(target_versions),
                reason_code=None,
            )
            return persist(receipt)
        observed = snapshot.stream_versions.get(command.target_stream_id, 0)
        if observed != command.expected_stream_version:
            receipt = Receipt(
                status="conflict",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=None,
                observed_stream_version=observed,
                reason_code="stream_version_conflict",
            )
            return persist(receipt)

        try:
            projection = replay_discovery(snapshot.events, schemas=self.schemas)
        except (IntegrityError, TypeError, ValueError) as exc:
            raise DiscoveryLedgerReplayError(
                "persisted Discovery ledger failed replay before command preparation"
            ) from exc
        self._require_admissible_target(command, projection)
        self._require_candidate_target(command, projection)
        _, route = _discovery_route(command)
        if route.family == "genesis":
            event_type, event_payload = self._prepare_genesis(command, projection)
            prepared = [(event_type, command.target_stream_id, event_payload)]
        elif route.family == "scout":
            prepared = self._prepare_scout_observation(command, projection)
        elif route.family == "candidate":
            event_type, event_payload = self._prepare_candidate(command, projection)
            prepared = [(event_type, command.target_stream_id, event_payload)]
        elif route.family == "supersede":
            prepared = self._prepare_candidate_supersession(command, projection)
        elif route.family == "assay":
            prepared = self._prepare_assay(command, projection)
        elif route.family == "spike":
            prepared = self._prepare_spike(command, projection)
        elif route.family == "dossier":
            try:
                prepared = self._prepare_dossier(command, projection)
            except DossierAdmissionRejected:
                raise
            except (TypeError, ValueError) as exc:
                raise DossierAdmissionRejected("invalid_canonical_value") from exc
        elif route.family == "assay_authority":
            prepared = self._prepare_assay_bar_authority(command, projection)
        elif route.family == "authority":
            prepared = self._prepare_authority(command, projection)
        else:
            raise IntegrityError(f"unsupported Discovery route family: {route.family}")
        command_binding = self.schemas.command_binding(envelope["command_type"])
        if command_binding is None:
            raise IntegrityError(f"inactive Discovery command binding: {envelope['command_type']}")
        binding = self.schemas.resolve_identity(command_binding.schema_id, command_binding.schema_version)
        occurred_at = self.clock()
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise IntegrityError("Discovery runtime clock must return an aware datetime")
        occurred_at_value = occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

        def event_schema(event_type: str, payload: Mapping[str, Any]) -> tuple[str, str]:
            """Resolve an exact producer binding, falling back only for Discovery shadow events."""

            shadow_keys = {
                "owner_row_id",
                "authority_kind",
                "authority_event_type",
                "authority_payload",
            }
            is_authority_shadow = (
                set(payload) == shadow_keys
                and payload.get("authority_event_type") == event_type
                and isinstance(payload.get("authority_payload"), Mapping)
            )
            if is_authority_shadow:
                return "ars://core/event", "1.0.0"
            if "authority_event_type" in payload:
                raise IntegrityError("invalid Discovery authority shadow payload")
            event_binding = self.schemas.event_binding(event_type, envelope["command_type"])
            if event_binding is not None:
                return event_binding.schema_id, event_binding.schema_version
            if self.schemas.has_producer_bindings(event_type):
                raise IntegrityError(
                    f"inactive Discovery event producer binding: {event_type}/{envelope['command_type']}"
                )
            return "ars://core/event", "1.0.0"

        event_records = []
        for prepared_event_type, prepared_stream_id, prepared_payload in prepared:
            schema_id, schema_version = event_schema(prepared_event_type, prepared_payload)
            event_records.append(
                {
                    "event_type": prepared_event_type,
                    "schema_id": schema_id,
                    "schema_version": schema_version,
                    "stream_id": prepared_stream_id,
                    "command_id": command.command_id,
                    "command_type": envelope["command_type"],
                    "command_schema_id": binding.schema_id,
                    "command_schema_version": binding.schema_version,
                    "command_schema_sha256": binding.raw_bytes_sha256,
                    "idempotency_key": command.idempotency_key,
                    "command_payload_hash": command.payload_hash,
                    "correlation_id": envelope_sha256,
                    "causation_id": None,
                    "actor_id": command.actor_id,
                    "authority_grant_id": envelope["authority_grant_id"],
                    "occurred_at": occurred_at_value,
                    "payload": prepared_payload,
                }
            )
        result = self.ledger.append(event_records, snapshot=snapshot)
        receipt = Receipt(
            status="accepted",
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=result["event_batch_id"],
            observed_stream_version=result["resulting_stream_versions"][command.target_stream_id],
            reason_code=None,
        )
        return persist(receipt)

    def _prepare_authority(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare one ordered W11 authority transition."""
        payload = command.envelope["payload"]
        row = payload.get("row_id")
        routes = {
            "OR-110": ("dossier_expected_set", "register"),
            "OR-111": ("dossier_expected_set", "observe"),
            "OR-112": ("dossier_expected_set", "request_review"),
            "OR-113": ("dossier_expected_set", "record_review"),
            "OR-114": ("dossier_expected_set", "propose"),
            "OR-115": ("dossier_expected_set", "resolve"),
            "OR-116": ("path_registration", "register"),
            "OR-117": ("path_registration", "observe"),
            "OR-118": ("path_registration", "request_review"),
            "OR-119": ("path_registration", "record_review"),
            "OR-120": ("path_registration", "propose"),
            "OR-121": ("path_registration", "resolve"),
        }
        if row not in routes:
            raise IntegrityError("invalid W11 authority row")
        kind, action = routes[row]
        if payload.get("authority_kind") != kind:
            raise IntegrityError("W11 authority kind mismatch")
        if action in {"register", "request_review", "propose"} and _discovery_identity_exists(
            projection, command.target_stream_id
        ):
            raise IntegrityError("W11 authority stream identity collision")
        current_authority = projection["authorities"].get(kind, {})
        if action == "record_review" and command.target_stream_id != current_authority.get("review_id"):
            raise IntegrityError("W11 authority review stream mismatch")
        if action == "propose" and command.target_stream_id != payload.get("decision_id"):
            raise IntegrityError("W11 authority decision stream mismatch")
        if action == "resolve" and command.target_stream_id != payload.get("decision_id"):
            raise IntegrityError("W11 authority decision stream mismatch")
        transition_payload = {
            key: deepcopy(value) for key, value in payload.items() if key not in {"row_id", "authority_kind"}
        }
        if action == "observe":
            current = projection["authorities"].get(kind)
            if not isinstance(current, dict) or command.target_stream_id != projection["authority_subject_streams"].get(
                kind
            ):
                raise IntegrityError("authority subject is not registered")
            subject = current.get("subject")
            if not isinstance(subject, dict):
                raise IntegrityError("authority subject is invalid")
            repository_path = subject.get("authority_file_path")
            if not isinstance(repository_path, str) or not repository_path:
                raise IntegrityError("authority file path is not sealed")
            repository_root = self.repository_root
            lexical_path = Path(repository_path)
            if lexical_path.is_absolute() or lexical_path.as_posix() != repository_path:
                raise IntegrityError("authority file path is not canonical")
            authority_file = (repository_root / repository_path).resolve(strict=True)
            try:
                authority_file.relative_to(repository_root)
            except ValueError as exc:
                raise IntegrityError("authority file escapes repository root") from exc
            raw = authority_file.read_bytes()
            file_sha256 = sha256_hex(raw)
            relative_path = authority_file.relative_to(repository_root).as_posix()
            if relative_path != repository_path:
                raise IntegrityError("authority file path alias is forbidden")
            try:
                git_commit = subprocess.run(
                    ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=_GIT_TIMEOUT_SECONDS,
                ).stdout.strip()
                git_blob = subprocess.run(
                    ["git", "-C", str(repository_root), "rev-parse", f"{git_commit}:{relative_path}"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=_GIT_TIMEOUT_SECONDS,
                ).stdout.strip()
                committed_raw = subprocess.run(
                    ["git", "-C", str(repository_root), "show", f"{git_commit}:{relative_path}"],
                    check=True,
                    capture_output=True,
                    timeout=_GIT_TIMEOUT_SECONDS,
                ).stdout
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                raise IntegrityError("authority file lacks current Git identity") from exc
            computed_blob = _git_blob(raw)
            if committed_raw != raw or computed_blob != git_blob:
                raise IntegrityError("authority file differs from captured Git bytes")
            try:
                serialized_subject = json.loads(committed_raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntegrityError("authority file is not canonical JSON content") from exc
            semantic_subject = {
                key: value
                for key, value in subject.items()
                if key != "subject_sha256" and not key.startswith("authority_file_")
            }
            if serialized_subject != semantic_subject:
                raise IntegrityError("authority file content does not match registered subject")
            if (
                subject.get("authority_file_size") != len(raw)
                or subject.get("authority_file_sha256") != file_sha256
                or subject.get("authority_file_git_commit") != git_commit
                or subject.get("authority_file_git_blob") != git_blob
            ):
                raise IntegrityError("authority file identity mismatch")
            transition_payload = {
                "subject_sha256": current["subject_sha256"],
                "repository_path": relative_path,
                "git_commit": git_commit,
                "git_blob": git_blob,
                "file_size": len(raw),
                "file_sha256": file_sha256,
            }
        elif action == "resolve":
            # The ledger replaces this preparation-only marker with its atomic
            # transaction identity in both persisted authority shadows.
            transition_payload["transaction_id"] = "pending-ledger-transaction"
        try:
            events = prepare_authority_transition(
                events=projection["authority_events"],
                kind=kind,
                action=action,
                actor_id=command.actor_id,
                payload=transition_payload,
            )
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
        current = projection["authorities"].get(kind, {})
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery authority clock must return an aware datetime")
        normalized_now = now.astimezone(UTC)

        def stable_id(prefix: str, suffix: int) -> str:
            return (
                f"{prefix}_019fed25-b33e-7740-b280-{(1100 if kind == 'dossier_expected_set' else 1200) + suffix:012d}"
            )

        def persisted_payload(event: dict[str, object]) -> dict[str, Any]:
            event_type = str(event["event_type"])
            shadow = event["payload"]
            current_time = normalized_now.isoformat().replace("+00:00", "Z")
            deadline = (normalized_now + timedelta(days=1)).isoformat().replace("+00:00", "Z")
            if event_type == "ReviewRequested":
                return {
                    "review_type": "provenance",
                    "new_review_id": command.target_stream_id,
                    "subject_ids": [stable_id("obj", 3)],
                    "subject_hashes": [current["subject_sha256"]],
                    "governing_refs": [f"W11:{event['owner_row_id']}", f"authority-kind:{kind}"],
                    "review_questions": [
                        "Does the exact authority subject and independently observed file identity match?"
                    ],
                    "required_evidence_refs": [current["file_sha256"]],
                    "required_lanes": ["provenance"],
                    "reviewer_capability": [shadow["reviewer_actor_id"]],
                    "required_independence_grade": "independent",
                    "visibility_policy": "owner-visible",
                    "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
                    "satisfaction_authority": "ars://portfolio/policy/w11-authority-review@1.0.0",
                    "deadline": deadline,
                    "escalation_rule": "owner-ruling",
                }
            if event_type == "ReviewVerdictRecorded":
                return {
                    "review_id": current["review_id"],
                    "verdict": shadow["verdict"],
                    "findings": [],
                    "required_evidence_refs": [current["file_sha256"]],
                    "limitations": [],
                    "conditions": [],
                    "reviewer_actor_id": command.actor_id,
                    "reviewer_profile": "independent-w11-authority-reviewer",
                    "reviewer_session": f"session-{kind}",
                    "reviewer_model_metadata": "independent-runtime-review",
                    "context_manifest_id": stable_id("ctx", 1),
                    "context_manifest_sha256": shadow["reconstruction_sha256"],
                    "unchanged_subject_sha256": shadow["unchanged_subject_sha256"],
                    "producing_attempt_id": stable_id("att", 2),
                    "trace_visibility_evidence_refs": [current["file_sha256"]],
                    "computed_independence_grade": "independent",
                }
            if event_type == "DecisionProposed":
                return {
                    "new_decision_id": shadow["decision_id"],
                    "question": f"Accept exact {kind} authority?",
                    "recommendation": shadow["proposed_decision"],
                    "options": ["accept", "reject"],
                    "decision_revision": 1,
                    "decision_kind": "design_lock",
                    "governing_evidence_refs": [current["file_sha256"], f"authority-kind:{kind}"],
                    "affected_task_ids": [],
                    "affected_claim_ids": [],
                    "required_authority": "owner",
                    "expires_at": deadline,
                    "review_date": current_time,
                    "consequences": [f"the exact {kind} subject becomes admission authority"],
                }
            if event_type == "DecisionResolved":
                return {
                    "decision_id": shadow["decision_id"],
                    "selected_option": shadow["decision"],
                    "effective_scope": f"exact {kind} subject",
                    "effective_at": current_time,
                    "decision_revision": 1,
                    "deciding_actor_id": command.actor_id,
                    "decision_authority_grant_id": command.envelope["authority_grant_id"],
                    "governing_evidence_refs": [current["file_sha256"]],
                    "considered_review_ids": [current["review_id"]],
                    "permitted_commands": ["AdmitResearchDossier"],
                    "superseded_decision_ids": [],
                    "conditions": [],
                    "revisit_triggers": ["authority subject changes"],
                }
            persisted_shadow = deepcopy(shadow)
            if isinstance(persisted_shadow, dict):
                persisted_shadow.pop("transaction_id", None)
            return {
                "owner_row_id": event["owner_row_id"],
                "authority_kind": event["authority_kind"],
                "authority_event_type": event["event_type"],
                "authority_payload": persisted_shadow,
            }

        return [
            (
                str(event["event_type"]),
                command.target_stream_id,
                persisted_payload(event),
            )
            for event in events
        ]

    def _prepare_assay_bar_authority(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare the exact OR-101--OR-109 Assay-bar authority transition."""

        payload = command.envelope["payload"]
        row = payload.get("row_id")
        state = projection["assay_bar_authority"]
        if payload.get("authority_kind") != "assay_bar":
            raise IntegrityError("Assay-bar authority kind mismatch")

        def wrapped(event_type: str, shadow: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
            return (
                event_type,
                command.target_stream_id,
                {
                    "owner_row_id": row,
                    "authority_kind": "assay_bar",
                    "authority_event_type": event_type,
                    "authority_payload": deepcopy(dict(shadow)),
                },
            )

        if row in {"OR-101", "OR-102"}:
            expected_command = "RegisterAssayRubricContent" if row == "OR-101" else "RegisterAssayEvidenceScopeContent"
            kind = "rubric" if row == "OR-101" else "scope"
            event_type = "AssayRubricContentRegistered" if kind == "rubric" else "AssayEvidenceScopeContentRegistered"
            content = payload.get("content")
            path = payload.get("authority_file_path")
            schema_id = (
                "ars://portfolio/assay-rubric-content"
                if kind == "rubric"
                else "ars://portfolio/assay-evidence-scope-content"
            )
            if (
                command.envelope["command_type"] != expected_command
                or not isinstance(content, dict)
                or not isinstance(path, str)
                or not path
                or command.target_stream_id != content.get("record_id")
                or content.get("created_by_actor_id") != command.actor_id
                or (state.get("status") == "stale" and kind != "rubric")
                or (state.get("status") != "stale" and _discovery_identity_exists(projection, command.target_stream_id))
            ):
                raise IntegrityError("invalid Assay-bar content registration")
            try:
                self.schemas.validate(schema_id, content, schema_version="1.0.0")
            except SchemaError as exc:
                raise IntegrityError("invalid Assay-bar content") from exc
            axis_definitions = content.get("axis_definitions") if kind == "rubric" else ()
            if kind == "rubric" and (
                not isinstance(axis_definitions, list)
                or any(
                    isinstance(definition, Mapping) and definition.get("value_type") == "number"
                    for definition in axis_definitions
                )
            ):
                raise IntegrityError("numeric Assay rubric is not P0-canonical; use an explicit scaled integer")
            try:
                content_digest = assay_content_sha256(content)
            except (TypeError, ValueError) as exc:
                raise IntegrityError("Assay-bar content is not P0-canonical") from exc
            if content_digest != content.get("content_hash"):
                raise IntegrityError("Assay-bar content hash mismatch")
            if kind in state["contents"] and state.get("status") != "stale":
                raise IntegrityError("Assay-bar content identity collision")
            if kind == "scope":
                rubric = state["contents"].get("rubric")
                if not isinstance(rubric, dict) or content.get("rubric_ref") != {
                    "id": rubric["content"]["record_id"],
                    "record_revision": rubric["content"]["record_revision"],
                    "content_hash": rubric["content_sha256"],
                }:
                    raise IntegrityError("Assay scope does not bind the current rubric")
            shadow = {
                "content": deepcopy(content),
                "content_sha256": content["content_hash"],
                "authority_file_path": path,
                "actor_id": command.actor_id,
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": event_type,
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [wrapped(event_type, shadow)]

        if row in {"OR-103", "OR-104"}:
            kind = "rubric" if row == "OR-103" else "scope"
            content_state = state["contents"].get(kind)
            content = content_state.get("content") if isinstance(content_state, Mapping) else None
            if (
                command.envelope["command_type"] != "ObserveW11AuthorityFile"
                or not isinstance(content_state, dict)
                or not isinstance(content, Mapping)
                or command.target_stream_id != content.get("record_id")
            ):
                raise IntegrityError("Assay-bar content is not registered")
            observation = self._observe_assay_authority_content(content_state)
            shadow = {"content_kind": kind, "actor_id": command.actor_id, **observation}
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "W11AuthorityFileObserved",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [wrapped("W11AuthorityFileObserved", shadow)]

        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery authority clock must return an aware datetime")
        current_time = now.astimezone(UTC).isoformat().replace("+00:00", "Z")
        deadline = (now.astimezone(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")

        if row == "OR-105":
            producer_ref = payload.get("prospective_producer_ref")
            reviewer = payload.get("reviewer_actor_id")
            if (
                command.envelope["command_type"] != "RequestW11AuthorityReview"
                or state.get("status") != "observed"
                or not isinstance(producer_ref, dict)
                or not isinstance(reviewer, str)
                or reviewer == producer_ref.get("id")
                or _discovery_identity_exists(projection, command.target_stream_id)
            ):
                raise IntegrityError("invalid Assay-bar review request")
            subject = {
                "rubric_sha256": state["contents"]["rubric"]["content_sha256"],
                "scope_sha256": state["contents"]["scope"]["content_sha256"],
                "rubric_file_sha256": state["observations"]["rubric"]["file_sha256"],
                "scope_file_sha256": state["observations"]["scope"]["file_sha256"],
                "prospective_producer_ref": producer_ref,
            }
            subject_hash = sha256_hex(canonical_bytes(subject))
            shadow = {
                "actor_id": command.actor_id,
                "reviewer_actor_id": reviewer,
                "review_id": command.target_stream_id,
                "subject_sha256": subject_hash,
                "prospective_producer_ref": deepcopy(producer_ref),
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "ReviewRequested",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [
                (
                    "ReviewRequested",
                    command.target_stream_id,
                    {
                        "review_type": "provenance",
                        "new_review_id": command.target_stream_id,
                        "subject_ids": [
                            state["contents"]["rubric"]["content"]["record_id"],
                            state["contents"]["scope"]["content"]["record_id"],
                        ],
                        "subject_hashes": [subject_hash],
                        "governing_refs": [
                            "W11:OR-105",
                            "authority-kind:assay_bar",
                            "prospective-producer:" + json.dumps(producer_ref, sort_keys=True, separators=(",", ":")),
                        ],
                        "review_questions": [
                            "Does the exact Assay bar bind both observed contents and producer relation?"
                        ],
                        "required_evidence_refs": [
                            state["observations"]["rubric"]["file_sha256"],
                            state["observations"]["scope"]["file_sha256"],
                        ],
                        "required_lanes": ["provenance"],
                        "reviewer_capability": [reviewer],
                        "required_independence_grade": "independent",
                        "visibility_policy": "owner-visible",
                        "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
                        "satisfaction_authority": "ars://portfolio/policy/w11-authority-review@1.0.0",
                        "deadline": deadline,
                        "escalation_rule": "owner-ruling",
                    },
                )
            ]

        if row == "OR-106":
            if (
                command.envelope["command_type"] != "RecordW11AuthorityReview"
                or state.get("status") != "review_requested"
                or command.target_stream_id != state.get("review_id")
            ):
                raise IntegrityError("invalid Assay-bar review verdict")
            shadow = {
                "actor_id": command.actor_id,
                "verdict": payload.get("verdict"),
                "unchanged_subject_sha256": payload.get("unchanged_subject_sha256"),
                "context_manifest_id": "ctx_019fed25-b33e-7740-b280-000000000105",
                "reconstruction_sha256": payload.get("reconstruction_sha256"),
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "ReviewVerdictRecorded",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [
                (
                    "ReviewVerdictRecorded",
                    command.target_stream_id,
                    {
                        "review_id": state["review_id"],
                        "verdict": payload.get("verdict"),
                        "findings": [],
                        "required_evidence_refs": [state["subject_sha256"]],
                        "limitations": [],
                        "conditions": [],
                        "reviewer_actor_id": command.actor_id,
                        "reviewer_profile": "independent-assay-bar-reviewer",
                        "reviewer_session": "session-assay-bar",
                        "reviewer_model_metadata": "independent-runtime-review",
                        "context_manifest_id": "ctx_019fed25-b33e-7740-b280-000000000105",
                        "context_manifest_sha256": payload.get("reconstruction_sha256"),
                        "unchanged_subject_sha256": payload.get("unchanged_subject_sha256"),
                        "producing_attempt_id": "att_019fed25-b33e-7740-b280-000000000106",
                        "trace_visibility_evidence_refs": [state["subject_sha256"]],
                        "computed_independence_grade": "independent",
                    },
                )
            ]

        if row == "OR-107":
            if (
                command.envelope["command_type"] != "ProposeW11AuthorityDecision"
                or state.get("status") != "reviewed"
                or _discovery_identity_exists(projection, command.target_stream_id)
            ):
                raise IntegrityError("invalid Assay-bar decision proposal")
            shadow = {
                "actor_id": command.actor_id,
                "decision_id": command.target_stream_id,
                "proposed_decision": payload.get("proposed_decision"),
                "subject_sha256": state["subject_sha256"],
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "DecisionProposed",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [
                (
                    "DecisionProposed",
                    command.target_stream_id,
                    {
                        "new_decision_id": command.target_stream_id,
                        "question": "Accept the exact current Assay bar?",
                        "recommendation": payload.get("proposed_decision"),
                        "options": ["accept", "reject"],
                        "decision_revision": 1,
                        "decision_kind": "design_lock",
                        "governing_evidence_refs": [state["subject_sha256"], "authority-kind:assay_bar"],
                        "affected_task_ids": [],
                        "affected_claim_ids": [],
                        "required_authority": "owner",
                        "expires_at": deadline,
                        "review_date": current_time,
                        "consequences": ["the exact Assay bar becomes current collection authority"],
                    },
                )
            ]

        if row == "OR-108":
            if (
                command.envelope["command_type"] != "ResolveDecision"
                or state.get("status") != "decision_proposed"
                or command.target_stream_id != state.get("decision_id")
                or payload.get("decision_id") != state.get("decision_id")
                or payload.get("decision") != "accept"
            ):
                raise IntegrityError("invalid Assay-bar owner resolution")
            resolved = {
                "decision_id": state["decision_id"],
                "selected_option": "accept",
                "effective_scope": "exact current Assay bar",
                "effective_at": current_time,
                "decision_revision": 1,
                "deciding_actor_id": command.actor_id,
                "decision_authority_grant_id": command.envelope["authority_grant_id"],
                "governing_evidence_refs": [state["subject_sha256"]],
                "considered_review_ids": [state["review_id"]],
                "permitted_commands": ["RequestAssay"],
                "superseded_decision_ids": [],
                "conditions": [],
                "revisit_triggers": ["rubric, scope, or producer relation changes"],
            }
            acceptance = {
                "subject_sha256": state["subject_sha256"],
                "rubric_ref": {
                    "id": state["contents"]["rubric"]["content"]["record_id"],
                    "record_revision": state["contents"]["rubric"]["content"]["record_revision"],
                    "content_hash": state["contents"]["rubric"]["content_sha256"],
                },
                "scope_ref": {
                    "id": state["contents"]["scope"]["content"]["record_id"],
                    "record_revision": state["contents"]["scope"]["content"]["record_revision"],
                    "content_hash": state["contents"]["scope"]["content_sha256"],
                },
                "rubric_file_sha256": state["observations"]["rubric"]["file_sha256"],
                "scope_file_sha256": state["observations"]["scope"]["file_sha256"],
                "review_id": state["review_id"],
                "decision_id": state["decision_id"],
                "required_axis_set_hash": state["contents"]["rubric"]["content"]["required_axis_set_hash"],
                "scope_closure_hash": state["contents"]["scope"]["content"]["scope_closure_algorithm_hash"],
                "prospective_producer_ref": deepcopy(state["prospective_producer_ref"]),
                "producer_relation_sha256": state["producer_relation_sha256"],
                "acceptor_actor_id": command.actor_id,
            }
            return [
                ("DecisionResolved", command.target_stream_id, resolved),
                wrapped("AssayBarAccepted", acceptance),
            ]

        if row == "OR-109":
            if (
                command.envelope["command_type"] != "RecordAssayBarStaleness"
                or state.get("status") != "accepted"
                or payload.get("acceptance_sha256") != state.get("acceptance_sha256")
                or not _assay_staleness_matches(payload, projection)
            ):
                raise IntegrityError("invalid Assay-bar staleness transition")
            return [
                wrapped(
                    "AssayBarStaled",
                    {
                        "acceptance_sha256": state["acceptance_sha256"],
                        "trigger_evidence_refs": deepcopy(payload["trigger_evidence_refs"]),
                        "effective_at": current_time,
                        "actor_id": command.actor_id,
                    },
                )
            ]
        raise IntegrityError("invalid Assay-bar authority row")

    def _observe_assay_authority_content(self, content_state: Mapping[str, Any]) -> dict[str, Any]:
        """Observe one registered Assay authority file at an exact Git commit:path."""

        repository_path = content_state.get("authority_file_path")
        content = content_state.get("content")
        if not isinstance(repository_path, str) or not isinstance(content, dict):
            raise IntegrityError("invalid Assay authority content state")
        lexical_path = Path(repository_path)
        if lexical_path.is_absolute() or lexical_path.as_posix() != repository_path:
            raise IntegrityError("authority file path is not canonical")
        try:
            authority_file = (self.repository_root / repository_path).resolve(strict=True)
            authority_file.relative_to(self.repository_root)
            raw = authority_file.read_bytes()
        except (OSError, ValueError) as exc:
            raise IntegrityError("authority file is unavailable") from exc
        try:
            git_commit = subprocess.run(
                ["git", "-C", str(self.repository_root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=_GIT_TIMEOUT_SECONDS,
            ).stdout.strip()
            relative_path = authority_file.relative_to(self.repository_root).as_posix()
            git_blob = subprocess.run(
                ["git", "-C", str(self.repository_root), "rev-parse", f"{git_commit}:{relative_path}"],
                check=True,
                capture_output=True,
                text=True,
                timeout=_GIT_TIMEOUT_SECONDS,
            ).stdout.strip()
            committed_raw = subprocess.run(
                ["git", "-C", str(self.repository_root), "show", f"{git_commit}:{relative_path}"],
                check=True,
                capture_output=True,
                timeout=_GIT_TIMEOUT_SECONDS,
            ).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise IntegrityError("authority file lacks current Git identity") from exc
        if committed_raw != raw or _git_blob(raw) != git_blob:
            raise IntegrityError("authority file differs from captured Git bytes")
        try:
            serialized = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("authority file is not canonical JSON content") from exc
        if serialized != content:
            raise IntegrityError("authority file content does not match registered content")
        return {
            "content_sha256": content_state["content_sha256"],
            "repository_path": relative_path,
            "git_commit": git_commit,
            "git_blob": git_blob,
            "file_size": len(raw),
            "file_sha256": sha256_hex(raw),
        }

    def _prepare_dossier(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare real dossier admission from replayed accepted authority."""
        expected: AcceptedExpectedSet | None = None
        roots: dict[str, RegisteredRoot] | None = None
        current_revision: int | None = None
        accepted_expected = projection["authorities"].get("dossier_expected_set")
        accepted_paths = projection["authorities"].get("path_registration")
        if accepted_expected and accepted_expected.get("status") == "accepted":
            subject = accepted_expected["subject"]
            expected_value = subject.get("expected_set")
            if isinstance(expected_value, dict):
                expected = AcceptedExpectedSet(
                    **{
                        **expected_value,
                        "members": tuple(DossierMember(**member) for member in expected_value["members"]),
                    }
                )
                current_revision = expected.revision
        if accepted_paths and accepted_paths.get("status") == "accepted":
            root_values = accepted_paths["subject"].get("registered_roots")
            if isinstance(root_values, list):
                required_root_fields = {
                    "path",
                    "root_id",
                    "registration_revision",
                    "registration_hash",
                    "authorized",
                }
                if any(
                    not isinstance(value, Mapping) or not required_root_fields.issubset(value) for value in root_values
                ):
                    raise IntegrityError("accepted path authority contains an invalid registered root")
                path_tokens = self.root_tokens
                if any(value.get("path") not in path_tokens for value in root_values):
                    raise IntegrityError("accepted path authority contains an unconfigured root token")
                roots = {
                    value["root_id"]: RegisteredRoot(
                        root_id=value["root_id"],
                        path=path_tokens[value["path"]],
                        registration_revision=value["registration_revision"],
                        registration_hash=value["registration_hash"],
                        authorized=value["authorized"],
                    )
                    for value in root_values
                }
        if expected is None or roots is None or current_revision is None:
            raise IntegrityError("accepted dossier authority is not active")
        payload = command.envelope["payload"]
        if (
            set(payload) != {"row_id", "dossier_id", "expected_set_id", "candidate_members", "candidate_manifest"}
            or payload.get("row_id") != "OR-028"
            or payload.get("dossier_id") != expected.dossier_id
            or payload.get("expected_set_id") != expected.expected_set_id
            or command.target_stream_id != expected.dossier_id
            or not isinstance(payload.get("candidate_members"), list)
            or not isinstance(payload.get("candidate_manifest"), dict)
        ):
            raise IntegrityError("invalid AdmitResearchDossier command")
        try:
            members = tuple(DossierMember(**member) for member in payload["candidate_members"])
        except (TypeError, ValueError) as exc:
            raise IntegrityError("invalid dossier candidate member") from exc
        try:
            self.schemas.validate(
                "ars://portfolio/research-dossier-manifest",
                payload["candidate_manifest"],
                schema_version="1.0.0",
            )
        except SchemaError as exc:
            raise DossierAdmissionRejected("invalid_research_dossier_manifest") from exc
        prepared = prepare_dossier_admission(
            expected_set=expected,
            current_expected_set_revision=current_revision,
            candidate_members=members,
            candidate_manifest=payload["candidate_manifest"],
            registered_roots=roots,
            existing_identities=frozenset(
                {
                    *({_CATALOGUE_STREAM_ID} if projection["catalogue"] is not None else set()),
                    *projection["source_observations"],
                    *projection["candidates"],
                    *projection["assays"],
                    *projection["spikes"],
                    *projection["decisions"],
                    *projection["reviews"],
                    *projection["dossiers"],
                    *projection["portfolio_objects"],
                    *projection["scopes"],
                    *projection["artefact_streams"],
                    *projection["authority_streams"],
                }
            ),
        )
        result: list[tuple[str, str, dict[str, Any]]] = []
        for event in prepared.events:
            event_type = event["event_type"]
            event_payload = event["payload"]
            stream_id = {
                "ResearchDossierAdmitted": expected.dossier_id,
                "PortfolioObjectRegistered": event_payload.get("record_id"),
                "ScopeDefinitionRegistered": event_payload.get("scope_id"),
            }.get(event_type)
            if not isinstance(stream_id, str):
                raise IntegrityError("dossier event lacks immutable stream identity")
            result.append((event_type, stream_id, event_payload))
        return result

    def _valid_promotion_relation(
        self,
        relation: Any,
        **expected: Any,
    ) -> bool:
        """Validate the accepted schema and exact promotion subject joins."""

        if not isinstance(relation, dict):
            return False
        try:
            self.schemas.validate(
                "ars://portfolio/relation/discovery-promotion",
                relation,
                schema_version="1.0.0",
            )
        except SchemaError:
            return False
        return _promotion_relation_matches(relation, **expected)

    def _valid_revisit_relation(
        self,
        relation: Any,
        **expected: Any,
    ) -> bool:
        """Validate the accepted schema and exact revisit predicate joins."""

        if not isinstance(relation, dict):
            return False
        try:
            self.schemas.validate(
                "ars://portfolio/relation/discovery-revisit",
                relation,
                schema_version="1.0.0",
            )
        except SchemaError:
            return False
        return _revisit_relation_matches(relation, **expected)

    def _valid_spike_execution_relation(
        self,
        relation: Any,
        *,
        candidate: Mapping[str, Any],
        assay: Mapping[str, Any],
        spike: Mapping[str, Any],
        decision_id: Any,
    ) -> bool:
        """Validate the accepted execution subject and current resource identity."""

        if not isinstance(relation, dict):
            return False
        try:
            self.schemas.validate(
                "ars://portfolio/relation/spike-execution-authority",
                relation,
                schema_version="1.0.0",
            )
            operational = replay_control_plane(self._operational_events())
        except (SchemaError, KeyError, TypeError, ValueError):
            return False
        resource_ref = relation.get("resource_ref")
        resource = operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
        return bool(
            isinstance(resource, Mapping)
            and resource.get("status") == "active"
            and resource_ref == _record_ref(resource_ref.get("id"), 1, sha256_hex(canonical_bytes(resource)))
            and _spike_execution_relation_matches(
                relation,
                candidate=candidate,
                assay=assay,
                spike=spike,
                decision_id=decision_id,
                resource=resource,
            )
        )

    def _prepare_spike(self, command: Command, projection: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare one Spike lifecycle transition batch."""
        p = command.envelope["payload"]
        row = p.get("row_id")
        candidate_id, spike_id, decision_id, review_id = (
            p.get(k) for k in ("candidate_id", "spike_id", "decision_id", "review_id")
        )
        candidate = projection["candidates"].get(candidate_id)
        spike = projection["spikes"].get(spike_id)
        assay = projection["assays"].get(candidate.get("assay_id")) if isinstance(candidate, dict) else None
        decision = projection["decisions"].get(decision_id)
        ct = command.envelope["command_type"]

        def out(*events: tuple[str, str]) -> list[tuple[str, str, dict[str, Any]]]:
            return [(event, stream, deepcopy(p.get("w2_payload", p))) for event, stream in events]

        if (
            ct == "ProposePromotionDecision"
            and row == "OR-012"
            and candidate
            and candidate.get("status") == "assay_scored"
            and isinstance(assay, dict)
            and assay.get("status") == "reviewed"
            and p.get("review_id") == assay.get("review_id")
            and isinstance(projection["reviews"].get(p.get("review_id")), dict)
            and projection["reviews"][p["review_id"]].get("status") == "satisfied"
            and command.target_stream_id == decision_id
            and decision is None
            and not _discovery_identity_exists(projection, decision_id)
            and isinstance(p.get("w2_payload"), dict)
            and p["w2_payload"].get("new_decision_id") == decision_id
            and p["w2_payload"].get("decision_kind") == "design_lock"
            and _valid_promotion_options(p["w2_payload"].get("options"))
            and (
                p["w2_payload"].get("recommendation") != "PROMOTE"
                or assay.get("mechanical_recommendation") == "PROMOTE"
            )
            and self._valid_promotion_relation(
                p.get("promotion_relation"),
                decision_id=decision_id,
                candidate=candidate,
                aggregate_id=assay.get("assay_id"),
                aggregate=assay,
                review=projection["reviews"][p["review_id"]],
                gate="assay_to_spike",
                recommendation=p["w2_payload"].get("recommendation"),
                actor_id=command.actor_id,
            )
        ):
            promotion_payload = {**deepcopy(p), "promotion_gate": "assay_to_spike"}
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionRequested", candidate_id, promotion_payload),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-013"
            and decision
            and decision.get("status") == "proposed"
            and decision.get("kind") == "discovery_promotion"
            and candidate
            and candidate.get("status") == "promotion_pending"
            and candidate.get("decision_id") == decision_id
            and candidate.get("promotion_gate") == "assay_to_spike"
            and command.target_stream_id == decision_id
            and isinstance(p.get("w2_payload"), dict)
            and p.get("w2_payload", {}).get("decision_id") == decision_id
            and p["w2_payload"].get("selected_option") in {"PROMOTE", "PARK", "KILL"}
            and p["w2_payload"]["selected_option"] in decision.get("options", ())
            and (
                p["w2_payload"].get("selected_option") != "PROMOTE"
                or isinstance(assay, Mapping)
                and assay.get("mechanical_recommendation") == "PROMOTE"
            )
        ):
            selected_option = p["w2_payload"]["selected_option"]
            applied_payload = {
                **deepcopy(p),
                "promotion_gate": "assay_to_spike",
                "selected_option": selected_option,
                "next_candidate_state": {
                    "PROMOTE": "spike_planning_authorized",
                    "PARK": "parked",
                    "KILL": "killed",
                }[selected_option],
            }
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionApplied", candidate_id, applied_payload),
            ]
        if (
            ct == "RegisterSpikePlan"
            and row in {"OR-014", "OR-025"}
            and candidate
            and candidate.get("status")
            == ("spike_planning_authorized" if row == "OR-014" else "spike_retry_authorized")
            and spike is None
            and not _discovery_identity_exists(projection, spike_id)
            and command.target_stream_id == spike_id
            and isinstance(p.get("plan_artifact"), dict)
            and self._valid_spike_plan(
                p["plan_artifact"],
                p,
                candidate,
                assay,
                projection["decisions"].get(candidate.get("decision_id")),
            )
        ):
            if row == "OR-025":
                old_spike_id = p.get("old_spike_id")
                old_spike = projection["spikes"].get(old_spike_id)
                if (
                    not isinstance(old_spike, dict)
                    or old_spike.get("status") != "retry_authorized"
                    or candidate.get("spike_id") != old_spike_id
                ):
                    raise IntegrityError("invalid Spike retry transition")
                return out(
                    ("SpikePlanned", spike_id),
                    ("SpikeApprovalRequested", spike_id),
                    ("SpikeSuperseded", old_spike_id),
                    ("CandidateSpikeRetryStarted", candidate_id),
                )
            return out(
                ("SpikePlanned", spike_id),
                ("SpikeApprovalRequested", spike_id),
                ("CandidateSpikePlanLinked", candidate_id),
            )
        if (
            ct == "ProposeSpikeExecutionDecision"
            and row == "OR-015"
            and spike
            and spike.get("status") == "approval_pending"
            and spike.get("candidate_id") == candidate_id
            and command.target_stream_id == decision_id
            and decision is None
            and not _discovery_identity_exists(projection, decision_id)
            and isinstance(p.get("w2_payload"), dict)
            and p["w2_payload"].get("new_decision_id") == decision_id
            and _valid_spike_execution_proposal(p["w2_payload"])
            and isinstance(assay, dict)
            and self._valid_spike_execution_relation(
                p.get("execution_authority_relation"),
                candidate=candidate,
                assay=assay,
                spike=spike,
                decision_id=decision_id,
            )
        ):
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("SpikeExecutionDecisionRequested", spike_id, deepcopy(p)),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-016"
            and decision
            and decision.get("status") == "proposed"
            and spike
            and spike.get("decision_id") == decision_id
            and spike.get("candidate_id") == candidate_id
            and candidate
            and candidate.get("status") == "spike_approval_pending"
            and command.target_stream_id == decision_id
            and isinstance(p.get("w2_payload"), dict)
            and p.get("w2_payload", {}).get("decision_id") == decision_id
            and p.get("w2_payload", {}).get("selected_option") == "approve"
            and p["w2_payload"]["selected_option"] in decision.get("options", ())
            and p.get("execution_authority_relation") == spike.get("execution_authority_relation")
            and spike.get("execution_authority_relation", {}).get("actor_id") == command.actor_id
            and self._valid_spike_execution_relation(
                p.get("execution_authority_relation"),
                candidate=candidate,
                assay=assay,
                spike=spike,
                decision_id=decision_id,
            )
        ):
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("SpikeAuthorized", spike_id, deepcopy(p)),
                ("CandidateSpikeAuthorized", candidate_id, deepcopy(p)),
            ]
        if (
            ct == "StartSpike"
            and row == "OR-017"
            and spike
            and spike.get("status") == "authorized"
            and spike.get("candidate_id") == candidate_id
            and candidate
            and candidate.get("status") == "spike_authorized"
            and command.target_stream_id == spike_id
            and isinstance(p.get("attempt_id"), str)
            and isinstance(p.get("attempt_sha256"), str)
            and len(p["attempt_sha256"]) == 64
            and isinstance(p.get("lease_id"), str)
            and _spike_execution_ids_available(
                projection["spikes"],
                spike_id,
                p.get("attempt_id"),
                p.get("lease_id"),
            )
            and self._valid_live_spike_lease(p, command)
            and isinstance(spike.get("execution_authority_relation"), Mapping)
            and spike["execution_authority_relation"].get("resource_ref", {}).get("id") == p.get("resource_grant_id")
        ):
            operational = replay_control_plane(self._operational_events())
            lease = operational.stream_states.get(p.get("lease_id"))
            if not isinstance(lease, Mapping):
                raise IntegrityError("invalid Spike transition")
            start_payload = {
                **deepcopy(p),
                "lease_sha256": sha256_hex(canonical_bytes(lease)),
                "execution_authority_relation": deepcopy(spike["execution_authority_relation"]),
            }
            return [
                ("SpikeStarted", spike_id, deepcopy(start_payload)),
                ("CandidateSpikeStarted", candidate_id, deepcopy(start_payload)),
            ]
        if (
            ct == "RecordSpikeVerdict"
            and row in {"OR-018", "OR-019"}
            and spike
            and spike.get("status") == "running"
            and spike.get("candidate_id") == candidate_id
            and candidate
            and candidate.get("status") == "spike_running"
            and command.target_stream_id == spike_id
            and isinstance(p.get("verdict_artifact"), dict)
            and self._valid_spike_verdict(p["verdict_artifact"], p, candidate, assay, spike, projection)
        ):
            if (p.get("verdict") == "PARTIAL") != (row == "OR-019"):
                raise IntegrityError("invalid Spike transition")
            if row == "OR-019":
                attempt, lease = self._live_spike_operational_pair(spike, require_unexpired=True)
                now = self.clock()
                if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                    raise IntegrityError("Discovery operational clock must return an aware datetime")
                artifact = p["verdict_artifact"]
                closure_payload = {
                    **deepcopy(p),
                    "attempt_id": spike.get("attempt_id"),
                    "lease_id": spike.get("lease_id"),
                }
                return [
                    ("SpikePartialRecorded", spike_id, deepcopy(p)),
                    (
                        "PartialOutcomeRecorded",
                        str(attempt["attempt_id"]),
                        {
                            "attempt_id": attempt["attempt_id"],
                            "completed_obligations": [artifact["completed_scope"]],
                            "unmet_obligations": [artifact["unmet_scope"]],
                            "candidate_artefact_ids": [p["verdict_sha256"]],
                            "stop_cause": "spike_partial",
                            "restrictions": list(
                                dict.fromkeys([*artifact["limitations"], *artifact["prohibited_inferences"]])
                            ),
                            "subject_kind": "attempt",
                        },
                    ),
                    (
                        "LeaseReleased",
                        str(lease["lease_id"]),
                        {
                            "lease_id": lease["lease_id"],
                            "release_reason": "spike_partial",
                            "holder_actor_id": lease["holder_actor_id"],
                            "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                        },
                    ),
                    ("SpikeAttemptClosed", spike_id, closure_payload),
                    ("SpikeLeaseReleased", spike_id, deepcopy(closure_payload)),
                    ("CandidateSpikePartialLinked", candidate_id, deepcopy(p)),
                ]
            return out(("SpikeVerdictRecorded", spike_id), ("CandidateSpikeVerdictLinked", candidate_id))
        if ct == "CancelDiscoveryEvaluation" and row == "OR-022":
            artifact = p.get("cancellation_artifact")
            if (
                not isinstance(spike, dict)
                or spike.get("status") not in {"planned", "approval_pending", "authorized", "running"}
                or spike.get("candidate_id") != candidate_id
                or not isinstance(candidate, dict)
                or candidate.get("status") not in {"spike_approval_pending", "spike_authorized", "spike_running"}
                or command.target_stream_id != spike_id
                or p.get("evaluation_kind") != "spike"
                or not isinstance(artifact, dict)
                or not _spike_cancellation_matches(
                    artifact,
                    payload=p,
                    candidate=candidate,
                    spike=spike,
                    decision=projection["decisions"].get(spike.get("decision_id")),
                    state=projection,
                )
            ):
                raise IntegrityError("invalid Spike cancellation transition")
            events: list[tuple[str, str, dict[str, Any]]] = []
            execution_decision = projection["decisions"].get(spike.get("decision_id"))
            if isinstance(execution_decision, dict) and execution_decision.get("status") == "proposed":
                events.append(
                    (
                        "SpikeExecutionProposalSupersededByCancellation",
                        str(spike["decision_id"]),
                        {
                            "candidate_id": candidate_id,
                            "spike_id": spike_id,
                            "decision_id": spike["decision_id"],
                            "cancellation_sha256": p["cancellation_sha256"],
                        },
                    )
                )
            events.append(("SpikeCancelled", spike_id, deepcopy(p)))
            if spike.get("status") == "running":
                attempt, lease = self._live_spike_operational_pair(spike)
                now = self.clock()
                if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                    raise IntegrityError("Discovery operational clock must return an aware datetime")
                events.extend(
                    [
                        (
                            "PartialOutcomeRecorded",
                            str(attempt["attempt_id"]),
                            {
                                "attempt_id": attempt["attempt_id"],
                                "completed_obligations": list(artifact.get("completed_scope", [])),
                                "unmet_obligations": list(artifact.get("unmet_scope", ["cancelled"])),
                                "candidate_artefact_ids": [p["cancellation_sha256"]],
                                "stop_cause": "discovery_evaluation_cancelled",
                                "restrictions": list(artifact.get("restrictions", ["no_promotion"])),
                                "subject_kind": "attempt",
                            },
                        ),
                        (
                            "LeaseReleased",
                            str(lease["lease_id"]),
                            {
                                "lease_id": lease["lease_id"],
                                "release_reason": "discovery_evaluation_cancelled",
                                "holder_actor_id": lease["holder_actor_id"],
                                "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                            },
                        ),
                        (
                            "SpikeAttemptClosed",
                            spike_id,
                            {**deepcopy(p), "attempt_id": spike.get("attempt_id"), "lease_id": spike.get("lease_id")},
                        ),
                        (
                            "SpikeLeaseReleased",
                            spike_id,
                            {**deepcopy(p), "attempt_id": spike.get("attempt_id"), "lease_id": spike.get("lease_id")},
                        ),
                    ]
                )
            events.append(("CandidateEvaluationCancelled", candidate_id, deepcopy(p)))
            return events
        spike_review_subject = (
            spike.get("outcome_sha256")
            if row in {"OR-040", "OR-041"} and isinstance(spike, dict)
            else spike.get("verdict_sha256")
            if isinstance(spike, dict)
            else None
        )
        prior_spike_review = projection["reviews"].get(spike.get("review_id")) if isinstance(spike, dict) else None
        spike_supersession = p.get("review_subject_supersession")
        spike_review_contract = p.get("review_contract")
        valid_spike_review_relation = bool(
            isinstance(spike, dict)
            and isinstance(spike_review_contract, Mapping)
            and (
                (spike.get("review_id") is None and spike_supersession is None)
                or _valid_review_supersession(
                    spike_supersession,
                    prior_spike_review,
                    p.get("subject_sha256"),
                    spike_review_contract.get("required_evidence_refs"),
                )
            )
        )
        if (
            ct == "RequestDiscoveryOutcomeReview"
            and row in {"OR-036", "OR-037", "OR-040"}
            and spike
            and spike.get("status")
            == {"OR-036": "verdict_recorded", "OR-037": "partial_recorded", "OR-040": "cancelled"}[row]
            and spike.get("candidate_id") == candidate_id
            and command.target_stream_id == review_id
            and not _discovery_identity_exists(projection, review_id)
            and valid_spike_review_relation
            and (
                p.get("subject_sha256") == spike_review_subject
                or isinstance(spike_supersession, Mapping)
                and spike_supersession.get("prior_subject_sha256") == spike_review_subject
            )
            and spike_review_contract.get("new_review_id") == review_id
            and spike_review_contract.get("subject_ids") == [spike_id]
            and spike_review_contract.get("subject_hashes") == [p.get("subject_sha256")]
        ):
            return [
                ("ReviewRequested", review_id, deepcopy(p["review_contract"])),
                (
                    {
                        "OR-036": "SpikeReviewRequested",
                        "OR-037": "SpikePartialReviewRequested",
                        "OR-040": "SpikeCancellationReviewRequested",
                    }[row],
                    spike_id,
                    deepcopy(p),
                ),
            ]
        if (
            ct == "ReviewDiscoveryOutcome"
            and row in {"OR-020", "OR-021", "OR-041"}
            and spike
            and spike.get("review_pending")
            and spike.get("review_id") == review_id
            and spike.get("candidate_id") == candidate_id
            and projection["reviews"].get(review_id, {}).get("status") == "pending"
            and command.target_stream_id == review_id
            and p.get("subject_sha256") == projection["reviews"][review_id].get("subject_sha256")
            and isinstance(p.get("review_verdict"), dict)
            and p["review_verdict"].get("review_id") == review_id
            and p["review_verdict"].get("reviewer_actor_id") == command.actor_id
            and projection["reviews"][review_id].get("request_actor_id") != command.actor_id
            and spike.get("producer_actor_id") != command.actor_id
            and p["review_verdict"].get("computed_independence_grade")
            == projection["reviews"][review_id].get("required_independence_grade")
            and p["review_verdict"].get("verdict") in projection["reviews"][review_id].get("allowed_verdicts", ())
            and p.get("review_verdict", {}).get("unchanged_subject_sha256")
            == projection["reviews"][review_id].get("subject_sha256")
        ):
            events = [("ReviewVerdictRecorded", review_id, deepcopy(p["review_verdict"]))]
            if _review_policy_status(p["review_verdict"]) == "satisfied":
                if row == "OR-020" and spike.get("status") == "verdict_recorded":
                    events.append(("SpikeReviewed", spike_id, deepcopy(p)))
                elif row == "OR-021" and spike.get("status") == "partial_recorded":
                    events.extend(
                        [
                            ("SpikePartialReviewed", spike_id, deepcopy(p)),
                            ("CandidateSpikePartialReviewed", candidate_id, deepcopy(p)),
                        ]
                    )
                elif row == "OR-041" and spike.get("status") == "cancelled":
                    events.extend(
                        [
                            ("SpikeCancellationReviewed", spike_id, deepcopy(p)),
                            ("CandidateSpikeCancellationReviewed", candidate_id, deepcopy(p)),
                        ]
                    )
                else:
                    raise IntegrityError("invalid Spike review row binding")
            return events
        if (
            ct == "ProposePromotionDecision"
            and row == "OR-026"
            and isinstance(candidate, dict)
            and candidate.get("status") == "spike_verdict_recorded"
            and candidate.get("spike_id") == spike_id
            and isinstance(spike, dict)
            and spike.get("status") == "reviewed"
            and spike.get("candidate_id") == candidate_id
            and p.get("verdict_sha256") == spike.get("verdict_sha256")
            and p.get("review_id") == spike.get("review_id")
            and projection["reviews"].get(p.get("review_id"), {}).get("status") == "satisfied"
            and command.target_stream_id == decision_id
            and decision is None
            and not _discovery_identity_exists(projection, decision_id)
            and isinstance(p.get("w2_payload"), dict)
            and _valid_spike_promotion_option(spike, p["w2_payload"].get("recommendation"))
            and p["w2_payload"].get("new_decision_id") == decision_id
            and p["w2_payload"].get("decision_kind") == "design_lock"
            and _valid_promotion_options(p["w2_payload"].get("options"))
            and self._valid_promotion_relation(
                p.get("promotion_relation"),
                decision_id=decision_id,
                candidate=candidate,
                aggregate_id=spike_id,
                aggregate=spike,
                review=projection["reviews"][p["review_id"]],
                gate="spike_to_preregistration",
                recommendation=p["w2_payload"].get("recommendation"),
                actor_id=command.actor_id,
            )
        ):
            promotion_payload = {**deepcopy(p), "promotion_gate": "spike_to_preregistration"}
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionRequested", candidate_id, promotion_payload),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-027"
            and isinstance(decision, dict)
            and decision.get("status") == "proposed"
            and decision.get("kind") == "discovery_promotion"
            and isinstance(candidate, dict)
            and candidate.get("status") == "promotion_pending"
            and candidate.get("promotion_gate") == "spike_to_preregistration"
            and candidate.get("decision_id") == decision_id
            and candidate.get("spike_id") == spike_id
            and isinstance(spike, dict)
            and spike.get("status") == "reviewed"
            and spike.get("candidate_id") == candidate_id
            and p.get("verdict_sha256") == spike.get("verdict_sha256")
            and p.get("review_id") == spike.get("review_id")
            and command.target_stream_id == decision_id
            and isinstance(p.get("w2_payload"), dict)
            and _valid_spike_promotion_option(spike, p["w2_payload"].get("selected_option"))
            and p["w2_payload"].get("decision_id") == decision_id
            and p["w2_payload"].get("selected_option") in {"PROMOTE", "PARK", "KILL"}
            and p["w2_payload"]["selected_option"] in decision.get("options", ())
        ):
            selected_option = p["w2_payload"]["selected_option"]
            applied_payload = {
                **deepcopy(p),
                "promotion_gate": "spike_to_preregistration",
                "selected_option": selected_option,
                "next_candidate_state": {
                    "PROMOTE": "preregistration_authorized",
                    "PARK": "parked",
                    "KILL": "killed",
                }[selected_option],
            }
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionApplied", candidate_id, applied_payload),
            ]
        if ct == "ProposeRevisitDecision" and row == "OR-023":
            review = projection["reviews"].get(p.get("review_id"))
            if (
                not isinstance(spike, dict)
                or spike.get("status") not in {"reviewed", "partial_reviewed", "cancellation_reviewed", "parked"}
                or spike.get("candidate_id") != candidate_id
                or spike.get("review_id") != p.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not isinstance(candidate, dict)
                or candidate.get("status") not in {"spike_revisit_eligible", "parked"}
                or _discovery_identity_exists(projection, decision_id)
                or command.target_stream_id != decision_id
                or not _valid_revisit_proposal(p.get("w2_payload"), p.get("review_id"))
                or p["w2_payload"].get("new_decision_id") != decision_id
                or not self._valid_revisit_relation(
                    p.get("revisit_relation"),
                    decision_id=decision_id,
                    candidate=candidate,
                    aggregate_id=spike_id,
                    aggregate=spike,
                    review=review,
                    observations=projection["source_observations"],
                    recommendation=p["w2_payload"].get("recommendation"),
                    actor_id=command.actor_id,
                )
            ):
                raise IntegrityError("invalid Spike revisit proposal")
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("SpikeRevisitRequested", spike_id, deepcopy(p)),
                ("CandidateSpikeRevisitRequested", candidate_id, deepcopy(p)),
            ]
        if ct == "ResolveDecision" and row == "OR-024":
            w2_payload = p.get("w2_payload")
            if (
                not isinstance(w2_payload, dict)
                or w2_payload.get("decision_id") != decision_id
                or w2_payload.get("selected_option") not in {"RETRY", "PARK", "KILL"}
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or w2_payload.get("selected_option") not in decision.get("options", ())
                or not isinstance(spike, dict)
                or spike.get("status") != "revisit_pending"
                or spike.get("candidate_id") != candidate_id
                or spike.get("decision_id") != decision_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "spike_revisit_pending"
                or candidate.get("decision_id") != decision_id
                or command.target_stream_id != decision_id
            ):
                raise IntegrityError("invalid Spike revisit resolution")
            resolved_payload = {**deepcopy(p), "selected_option": w2_payload["selected_option"]}
            return [
                ("DecisionResolved", decision_id, deepcopy(w2_payload)),
                ("SpikeRevisitResolved", spike_id, deepcopy(resolved_payload)),
                ("CandidateSpikeRevisitResolved", candidate_id, deepcopy(resolved_payload)),
            ]
        raise IntegrityError(f"invalid Spike transition: {ct}/{row}")

    def _valid_live_spike_lease(self, payload: dict[str, Any], command: Command) -> bool:
        """Resolve the current operational Attempt/Lease relation under the shared writer lock."""
        state = replay_control_plane(self._operational_events())
        attempt = state.stream_states.get(payload.get("attempt_id"))
        lease = state.stream_states.get(payload.get("lease_id"))
        if not isinstance(lease, dict):
            return False
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery operational clock must return an aware datetime")
        try:
            expires_at = datetime.fromisoformat(str(lease.get("expires_at")).replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise IntegrityError("invalid operational lease expiry") from exc
        return bool(
            isinstance(attempt, dict)
            and attempt.get("status") == "running"
            and payload.get("attempt_sha256") == sha256_hex(canonical_bytes(attempt))
            and attempt.get("lease_id") == payload.get("lease_id")
            and isinstance(lease, dict)
            and lease.get("status") == "active"
            and lease.get("attempt_id") == payload.get("attempt_id")
            and lease.get("holder_actor_id") == command.actor_id
            and expires_at > now.astimezone(UTC)
            and payload.get("resource_grant_id") == lease.get("resource_grant_id")
        )

    def _live_spike_operational_pair(
        self,
        spike: Mapping[str, Any],
        *,
        require_unexpired: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the exact current running Attempt and active Lease for a Spike."""

        try:
            state = replay_control_plane(self._operational_events())
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("invalid operational Attempt or Lease history") from exc
        attempt = state.stream_states.get(spike.get("attempt_id"))
        lease = state.stream_states.get(spike.get("lease_id"))
        if (
            not isinstance(attempt, dict)
            or attempt.get("status") != "running"
            or sha256_hex(canonical_bytes(attempt)) != spike.get("attempt_sha256")
            or attempt.get("lease_id") != spike.get("lease_id")
            or not isinstance(lease, dict)
            or lease.get("status") != "active"
            or lease.get("attempt_id") != spike.get("attempt_id")
        ):
            raise IntegrityError("invalid Spike operational closure")
        if require_unexpired:
            now = self.clock()
            if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                raise IntegrityError("Discovery operational clock must return an aware datetime")
            try:
                expires_at = datetime.fromisoformat(str(lease.get("expires_at")).replace("Z", "+00:00"))
            except (AttributeError, TypeError, ValueError) as exc:
                raise IntegrityError("invalid operational lease expiry") from exc
            if expires_at <= now.astimezone(UTC):
                raise IntegrityError("invalid Spike operational closure")
        return attempt, lease

    def _operational_events(self) -> tuple[dict[str, Any], ...]:
        """Select canonical control-plane events from the shared atomic ledger."""

        events = self.operational_ledger.snapshot().events
        resolve_transaction_ids = discovery_resolve_transaction_ids(events)
        return tuple(
            event
            for event in events
            if _shared_event_partition(event, resolve_transaction_ids=resolve_transaction_ids) == "operational"
        )

    def _valid_spike_plan(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any] | None,
        promotion_decision: dict[str, Any] | None,
    ) -> bool:
        """Validate and bind the exact Spike plan used by later evidence."""

        try:
            self.schemas.validate("ars://portfolio/spike-plan", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Spike plan artifact") from exc
        return _spike_plan_matches(artifact, payload, candidate, assay, promotion_decision)

    def _valid_spike_verdict(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any] | None,
        spike: dict[str, Any],
        projection: dict[str, Any],
    ) -> bool:
        """Validate exact evidence relationships and the PASS/FAIL truth table."""

        try:
            self.schemas.validate("ars://portfolio/spike-verdict", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Spike verdict artifact") from exc
        if not isinstance(assay, dict):
            return False
        artefact_streams: dict[str, dict[str, Any]] = {}
        events = self.operational_ledger.snapshot().events
        resolve_transaction_ids = discovery_resolve_transaction_ids(events)
        for event in events:
            if _shared_event_partition(event, resolve_transaction_ids=resolve_transaction_ids) != "artefact":
                continue
            stream_id = event.get("stream_id")
            if not isinstance(stream_id, str):
                return False
            try:
                artefact_streams[stream_id] = reduce_artefact(artefact_streams.get(stream_id, {}), event)
            except (KeyError, TypeError, ValueError):
                return False
        return _spike_verdict_matches(artifact, payload, candidate, assay, spike, projection, artefact_streams)

    def _prepare_assay(self, command: Command, projection: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare one Assay lifecycle transition batch."""
        payload = command.envelope["payload"]
        candidate_id = payload.get("candidate_id")
        assay_id = payload.get("assay_id")
        review_id = payload.get("review_id")
        candidate = projection["candidates"].get(candidate_id)
        assay = projection["assays"].get(assay_id)
        review = projection["reviews"].get(review_id)
        command_type = command.envelope["command_type"]
        if command_type == "RequestAssay":
            if payload.get("row_id") == "OR-011":
                old_assay_id = payload.get("old_assay_id")
                old_assay = projection["assays"].get(old_assay_id)
                bar = projection["assay_bar_authority"]
                producer_ref = bar.get("prospective_producer_ref") if isinstance(bar, dict) else None
                if (
                    command.target_stream_id != assay_id
                    or not isinstance(assay_id, str)
                    or assay is not None
                    or _discovery_identity_exists(projection, assay_id)
                    or not isinstance(old_assay, dict)
                    or old_assay.get("status") != "retry_authorized"
                    or not isinstance(candidate, dict)
                    or candidate.get("status") != "assay_retry_authorized"
                    or candidate.get("assay_id") != old_assay_id
                    or payload.get("candidate_revision") != candidate.get("revision")
                    or payload.get("candidate_sha256") != candidate.get("content_sha256")
                    or bar.get("status") != "accepted"
                    or payload.get("assay_bar_acceptance_sha256") != bar.get("acceptance_sha256")
                    or payload.get("producer_relation_sha256") != bar.get("producer_relation_sha256")
                    or not isinstance(producer_ref, dict)
                    or not isinstance(producer_ref.get("id"), str)
                ):
                    raise IntegrityError("invalid RequestAssay retry transition")
                retry_payload = {**deepcopy(payload), "producer_actor_id": producer_ref["id"]}
                return [
                    ("AssayRequested", assay_id, deepcopy(retry_payload)),
                    ("AssayEvidenceCollectionOpened", assay_id, deepcopy(retry_payload)),
                    ("AssaySuperseded", old_assay_id, deepcopy(retry_payload)),
                    ("CandidateAssayRetryStarted", candidate_id, deepcopy(retry_payload)),
                ]
            bar = projection["assay_bar_authority"]
            producer_ref = bar.get("prospective_producer_ref") if isinstance(bar, dict) else None
            if (
                payload.get("row_id") != "OR-003"
                or command.target_stream_id != assay_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "registered"
                or candidate.get("revision") != payload.get("candidate_revision")
                or candidate.get("content_sha256") != payload.get("candidate_sha256")
                or assay is not None
                or _discovery_identity_exists(projection, assay_id)
                or bar.get("status") != "accepted"
                or payload.get("assay_bar_acceptance_sha256") != bar.get("acceptance_sha256")
                or payload.get("producer_relation_sha256") != bar.get("producer_relation_sha256")
                or not isinstance(producer_ref, dict)
                or not isinstance(producer_ref.get("id"), str)
            ):
                raise IntegrityError("invalid RequestAssay transition")
            request_payload = {**deepcopy(payload), "producer_actor_id": producer_ref["id"]}
            return [
                ("AssayRequested", assay_id, deepcopy(request_payload)),
                ("AssayEvidenceCollectionOpened", assay_id, deepcopy(request_payload)),
                ("CandidateAssayRequested", candidate_id, deepcopy(request_payload)),
            ]
        if command_type == "RecordAssayScore":
            if (
                payload.get("row_id") != "OR-004"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("candidate_id") != candidate_id
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
                or assay.get("producer_actor_id") != command.actor_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
                or not isinstance(payload.get("scorecard_artifact"), dict)
                or not self._valid_assay_scorecard(
                    payload["scorecard_artifact"],
                    payload,
                    candidate,
                    assay,
                    projection["assay_bar_authority"],
                    command,
                )
            ):
                raise IntegrityError("invalid RecordAssayScore transition")
            return [
                ("AssayScored", assay_id, deepcopy(payload)),
                ("CandidateAssayLinked", candidate_id, deepcopy(payload)),
            ]
        if command_type == "RecordAssayPartial":
            artifact = payload.get("partial_artifact")
            if (
                payload.get("row_id") != "OR-005"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("candidate_id") != candidate_id
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
                or assay.get("producer_actor_id") != command.actor_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
                or not isinstance(artifact, dict)
                or not self._valid_assay_partial(
                    artifact,
                    payload,
                    candidate,
                    assay,
                    projection["assay_bar_authority"],
                )
            ):
                raise IntegrityError("invalid RecordAssayPartial transition")
            return [
                ("AssayPartialRecorded", assay_id, deepcopy(payload)),
                ("CandidateAssayPartialLinked", candidate_id, deepcopy(payload)),
            ]
        if command_type == "CancelDiscoveryEvaluation":
            artifact = payload.get("cancellation_artifact")
            if (
                payload.get("row_id") != "OR-008"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") not in {"requested", "evidence_collecting"}
                or assay.get("candidate_id") != candidate_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
                or payload.get("evaluation_kind") != "assay"
                or not _assay_cancellation_matches(
                    artifact,
                    payload=payload,
                    candidate=candidate,
                    assay=assay,
                    state=projection,
                )
            ):
                raise IntegrityError("invalid Assay cancellation transition")
            return [
                ("AssayCancelled", assay_id, deepcopy(payload)),
                ("CandidateEvaluationCancelled", candidate_id, deepcopy(payload)),
            ]
        if command_type == "RequestDiscoveryOutcomeReview":
            review_contract = payload.get("review_contract")
            row = payload.get("row_id")
            expected_status = {"OR-034": "scored", "OR-035": "partial_recorded", "OR-038": "cancelled"}.get(row)
            current_subject_sha256 = (
                assay.get("scorecard_sha256")
                if expected_status == "scored" and isinstance(assay, dict)
                else assay.get("outcome_sha256")
                if isinstance(assay, dict)
                else None
            )
            prior_review = projection["reviews"].get(assay.get("review_id")) if isinstance(assay, dict) else None
            supersession = payload.get("review_subject_supersession")
            valid_review_relation = bool(
                isinstance(assay, dict)
                and (
                    (assay.get("review_id") is None and supersession is None)
                    or _valid_review_supersession(
                        supersession,
                        prior_review,
                        payload.get("subject_sha256"),
                        review_contract.get("required_evidence_refs") if isinstance(review_contract, Mapping) else None,
                    )
                )
            )
            if (
                expected_status is None
                or command.target_stream_id != review_id
                or review is not None
                or _discovery_identity_exists(projection, review_id)
                or not isinstance(assay, dict)
                or assay.get("status") != expected_status
                or not valid_review_relation
                or (
                    current_subject_sha256 != payload.get("subject_sha256")
                    and (
                        not isinstance(supersession, Mapping)
                        or supersession.get("prior_subject_sha256") != current_subject_sha256
                    )
                )
                or not isinstance(review_contract, dict)
                or review_contract.get("new_review_id") != review_id
                or review_contract.get("subject_ids") != [assay_id]
                or review_contract.get("subject_hashes") != [payload.get("subject_sha256")]
            ):
                raise IntegrityError("invalid RequestDiscoveryOutcomeReview transition")
            return [
                ("ReviewRequested", review_id, deepcopy(review_contract)),
                (
                    {
                        "OR-034": "AssayOutcomeReviewRequested",
                        "OR-035": "AssayPartialReviewRequested",
                        "OR-038": "AssayCancellationReviewRequested",
                    }[row],
                    assay_id,
                    deepcopy(payload),
                ),
            ]
        if command_type == "ReviewDiscoveryOutcome":
            review_verdict = payload.get("review_verdict")
            row = payload.get("row_id")
            expected_status = {"OR-006": "scored", "OR-007": "partial_recorded", "OR-039": "cancelled"}.get(row)
            expected_candidate_status = {
                "OR-006": "assay_scored",
                "OR-007": "assay_partial_recorded",
                "OR-039": "assay_cancelled",
            }.get(row)
            if (
                expected_status is None
                or command.target_stream_id != review_id
                or not isinstance(review_verdict, dict)
                or review_verdict.get("review_id") != review_id
                or payload.get("verdict") != review_verdict.get("verdict")
                or review_verdict.get("unchanged_subject_sha256") != payload.get("subject_sha256")
                or review_verdict.get("reviewer_actor_id") != command.actor_id
                or not isinstance(review, dict)
                or review.get("status") != "pending"
                or review.get("subject_sha256") != payload.get("subject_sha256")
                or review.get("request_actor_id") == command.actor_id
                or review_verdict.get("verdict") not in review.get("allowed_verdicts", ())
                or review_verdict.get("computed_independence_grade") != review.get("required_independence_grade")
                or not isinstance(assay, dict)
                or assay.get("candidate_id") != candidate_id
                or not assay.get("review_pending")
                or assay.get("review_id") != review_id
                or assay.get("status") != expected_status
                or assay.get("producer_actor_id") == command.actor_id
                or projection["assay_bar_authority"].get("prospective_producer_ref", {}).get("id") == command.actor_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != expected_candidate_status
            ):
                raise IntegrityError("invalid ReviewDiscoveryOutcome transition")
            events = [("ReviewVerdictRecorded", review_id, deepcopy(review_verdict))]
            if _review_policy_status(review_verdict) == "satisfied":
                if row == "OR-006":
                    events.append(("AssayReviewed", assay_id, deepcopy(payload)))
                elif row == "OR-007":
                    events.extend(
                        [
                            ("AssayPartialReviewed", assay_id, deepcopy(payload)),
                            ("CandidateAssayPartialReviewed", candidate_id, deepcopy(payload)),
                        ]
                    )
                else:
                    events.extend(
                        [
                            ("AssayCancellationReviewed", assay_id, deepcopy(payload)),
                            ("CandidateAssayCancellationReviewed", candidate_id, deepcopy(payload)),
                        ]
                    )
            return events
        if command_type == "ProposeRevisitDecision":
            decision_id = payload.get("decision_id")
            review = projection["reviews"].get(payload.get("review_id"))
            if (
                payload.get("row_id") != "OR-009"
                or command.target_stream_id != decision_id
                or _discovery_identity_exists(projection, decision_id)
                or not isinstance(assay, dict)
                or assay.get("status") not in {"reviewed", "partial_reviewed", "cancellation_reviewed", "parked"}
                or assay.get("candidate_id") != candidate_id
                or assay.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not isinstance(candidate, dict)
                or candidate.get("status") not in {"assay_revisit_eligible", "parked"}
                or not _valid_revisit_proposal(payload.get("w2_payload"), payload.get("review_id"))
                or payload["w2_payload"].get("new_decision_id") != decision_id
                or not self._valid_revisit_relation(
                    payload.get("revisit_relation"),
                    decision_id=decision_id,
                    candidate=candidate,
                    aggregate_id=assay_id,
                    aggregate=assay,
                    review=review,
                    observations=projection["source_observations"],
                    recommendation=payload["w2_payload"].get("recommendation"),
                    actor_id=command.actor_id,
                )
            ):
                raise IntegrityError("invalid Assay revisit proposal")
            return [
                ("DecisionProposed", decision_id, deepcopy(payload["w2_payload"])),
                ("AssayRevisitRequested", assay_id, deepcopy(payload)),
                ("CandidateAssayRevisitRequested", candidate_id, deepcopy(payload)),
            ]
        if command_type == "ResolveDecision":
            decision_id = payload.get("decision_id")
            w2_payload = payload.get("w2_payload")
            decision = projection["decisions"].get(decision_id)
            if (
                payload.get("row_id") != "OR-010"
                or command.target_stream_id != decision_id
                or not isinstance(w2_payload, dict)
                or w2_payload.get("decision_id") != decision_id
                or w2_payload.get("selected_option") not in {"RETRY", "PARK", "KILL"}
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or w2_payload.get("selected_option") not in decision.get("options", ())
                or not isinstance(assay, dict)
                or assay.get("status") != "revisit_pending"
                or assay.get("candidate_id") != candidate_id
                or assay.get("decision_id") != decision_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_revisit_pending"
                or candidate.get("decision_id") != decision_id
            ):
                raise IntegrityError("invalid Assay revisit resolution")
            resolved_payload = {**deepcopy(payload), "selected_option": w2_payload["selected_option"]}
            return [
                ("DecisionResolved", decision_id, deepcopy(w2_payload)),
                ("AssayRevisitResolved", assay_id, deepcopy(resolved_payload)),
                ("CandidateAssayRevisitResolved", candidate_id, deepcopy(resolved_payload)),
            ]
        raise IntegrityError(f"unsupported Assay command: {command_type}")

    def _valid_assay_scorecard(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any],
        bar: dict[str, Any],
        command: Command,
    ) -> bool:
        """Validate and bind the exact Assay scorecard before publication."""
        try:
            self.schemas.validate("ars://portfolio/assay-scorecard", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Assay scorecard artifact") from exc
        return _assay_scorecard_matches(artifact, payload, candidate, assay, bar, command.actor_id)

    def _valid_assay_partial(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any],
        bar: dict[str, Any],
    ) -> bool:
        """Validate and bind the exact Assay Partial artifact before publication."""
        try:
            self.schemas.validate("ars://portfolio/assay-partial", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Assay Partial artifact") from exc
        acceptance = bar.get("acceptance")
        if not isinstance(acceptance, dict):
            return False
        expected_candidate = {
            "id": payload.get("candidate_id"),
            "record_revision": candidate.get("revision"),
            "content_hash": candidate.get("content_sha256"),
        }
        expected_acceptance = {
            "id": acceptance.get("decision_id"),
            "record_revision": 1,
            "content_hash": bar.get("acceptance_sha256"),
        }
        return bool(
            _valid_assay_partial_shape(artifact)
            and _assay_partial_axes_match(artifact, bar)
            and bar.get("status") == "accepted"
            and assay.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
            and artifact.get("candidate_ref") == expected_candidate
            and artifact.get("assay_id") == payload.get("assay_id")
            and artifact.get("rubric_ref") == acceptance.get("rubric_ref")
            and artifact.get("scope_ref") == acceptance.get("scope_ref")
            and artifact.get("assay_bar_acceptance_ref") == expected_acceptance
            and artifact.get("assay_relation_hash") == assay.get("producer_relation_sha256")
            and sha256_hex(canonical_bytes(artifact)) == payload.get("partial_sha256")
        )

    def _prepare_genesis(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Verify and prepare the one-time accepted W11 catalogue import."""
        if projection["catalogue"] is not None:
            raise IntegrityError("W11 genesis already exists")
        if command.target_stream_id != _CATALOGUE_STREAM_ID or command.expected_stream_version != 0:
            raise IntegrityError("W11 genesis stream identity mismatch")
        if command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        try:
            raw = self.catalogue_path.read_bytes()
        except OSError as exc:
            raise IntegrityError("catalogue path is unavailable") from exc
        if (
            len(raw) != _ACCEPTED["catalogue_bytes"]
            or sha256_hex(raw) != _ACCEPTED["catalogue_sha256"]
            or _git_blob(raw) != _ACCEPTED["catalogue_blob"]
        ):
            raise IntegrityError("catalogue identity mismatch")
        repository_root = self.repository_root
        bootstrap = (
            repository_root / ".research-system" / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
        )
        try:
            bootstrap_raw = bootstrap.read_bytes()
        except OSError as exc:
            raise IntegrityError("bootstrap contract is unavailable") from exc
        if (
            sha256_hex(bootstrap_raw) != _ACCEPTED["bootstrap_sha256"]
            or _git_blob(bootstrap_raw) != _ACCEPTED["bootstrap_blob"]
        ):
            raise IntegrityError("bootstrap identity mismatch")
        catalogue = json.loads(raw)
        row_ids = tuple(row.get("owner_row_id") for row in catalogue.get("owner_contract_rows", ()))
        if catalogue.get("owner_row_count") != 81 or row_ids != _ROW_IDS or len(set(row_ids)) != 81:
            raise IntegrityError("catalogue row set mismatch")
        _validate_discovery_route_registry(catalogue)
        return (
            "W11CatalogueGenesisImported",
            {
                "accepted_commit": _ACCEPTED["accepted_commit"],
                "accepted_tree": _ACCEPTED["accepted_tree"],
                "catalogue_blob": _ACCEPTED["catalogue_blob"],
                "catalogue_bytes": _ACCEPTED["catalogue_bytes"],
                "catalogue_sha256": _ACCEPTED["catalogue_sha256"],
                "bootstrap_blob": _ACCEPTED["bootstrap_blob"],
                "bootstrap_sha256": _ACCEPTED["bootstrap_sha256"],
                "review_commit": _ACCEPTED["review_commit"],
                "review_blob": _ACCEPTED["review_blob"],
                "review_sha256": _ACCEPTED["review_sha256"],
                "owner_row_id": "OR-140",
                "row_count": 81,
                "row_ids": list(_ROW_IDS),
            },
        )

    def _prepare_candidate(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Validate and prepare the thinnest Candidate registration."""
        if projection["catalogue"] is None:
            raise IntegrityError("W11 genesis is required before Candidate registration")
        payload = command.envelope["payload"]
        required = {"candidate_id", "revision", "content_sha256", "source_observation_refs", "title"}
        if set(payload) != required or payload.get("candidate_id") != command.target_stream_id:
            raise IntegrityError("invalid Candidate registration")
        if payload.get("revision") != 1 or not isinstance(payload.get("title"), str) or not payload["title"]:
            raise IntegrityError("invalid Candidate registration")
        digest = payload.get("content_sha256")
        observations = payload.get("source_observation_refs")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not isinstance(observations, list)
            or not observations
            or not all(isinstance(item, str) and item for item in observations)
        ):
            raise IntegrityError("invalid Candidate registration")
        if _discovery_identity_exists(projection, command.target_stream_id):
            raise IntegrityError("Candidate identity collision")
        multiset_hash = _source_observation_multiset_hash(observations, projection["source_observations"])
        if digest != multiset_hash:
            raise IntegrityError("Candidate content hash does not match resolved observations")
        return "CandidateRegistered", {
            **deepcopy(payload),
            "owner_row_id": "OR-001",
            "source_observation_multiset_hash": multiset_hash,
        }

    def _prepare_candidate_supersession(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare the exact OR-002 Candidate supersession relation."""

        payload = command.envelope["payload"]
        if set(payload) != {"row_id", "predecessor_ref", "replacement_ref", "lineage_reason"}:
            raise IntegrityError("invalid Candidate supersession command")
        predecessor_ref = payload.get("predecessor_ref")
        replacement_ref = payload.get("replacement_ref")
        predecessor_id = predecessor_ref.get("id") if isinstance(predecessor_ref, Mapping) else None
        replacement_id = replacement_ref.get("id") if isinstance(replacement_ref, Mapping) else None
        predecessor = projection["candidates"].get(predecessor_id)
        replacement = projection["candidates"].get(replacement_id)
        reason = payload.get("lineage_reason")
        if not isinstance(predecessor, Mapping) or not isinstance(replacement, Mapping):
            raise IntegrityError("invalid Candidate supersession subject")
        if predecessor_id == replacement_id:
            raise IntegrityError("invalid Candidate supersession")
        lineage = _candidate_supersession_lineage(projection["candidates"], predecessor, replacement)
        if (
            payload.get("row_id") != "OR-002"
            or command.target_stream_id != predecessor_id
            or predecessor_id == replacement_id
            or predecessor_ref != _candidate_ref(predecessor)
            or replacement_ref != _candidate_ref(replacement)
            or predecessor.get("status") == "superseded"
            or replacement.get("status") == "superseded"
            or replacement.get("supersedes_candidate_id") is not None
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise IntegrityError("invalid Candidate supersession")
        lineage_sha256 = sha256_hex(canonical_bytes({"lineage": lineage, "lineage_reason": reason}))
        event_payload = {
            "owner_row_id": "OR-002",
            "predecessor_ref": deepcopy(predecessor_ref),
            "replacement_ref": deepcopy(replacement_ref),
            "lineage_reason": reason,
            "lineage": lineage,
            "lineage_sha256": lineage_sha256,
        }
        return [("CandidateSuperseded", str(predecessor_id), event_payload)]

    def _prepare_scout_observation(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Ingest one exact Scout observation batch and its explicit Candidates."""

        if projection["catalogue"] is None:
            raise IntegrityError("W11 genesis is required before Scout observation ingestion")
        payload = command.envelope["payload"]
        required = {"row_id", "observation_id", "batch", "batch_sha256", "candidate_blueprints"}
        observation_id = payload.get("observation_id")
        batch = payload.get("batch")
        blueprints = payload.get("candidate_blueprints")
        if (
            set(payload) != required
            or payload.get("row_id") != "OR-029"
            or observation_id != command.target_stream_id
            or not isinstance(observation_id, str)
            or not isinstance(batch, dict)
            or not isinstance(blueprints, list)
            or not blueprints
            or _discovery_identity_exists(projection, observation_id)
        ):
            raise IntegrityError("invalid Scout observation ingestion")
        try:
            self.schemas.validate("ars://portfolio/scout-observation-batch", batch, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Scout observation batch") from exc
        batch_sha256 = sha256_hex(canonical_bytes(batch))
        dedup_keys = batch.get("normalized_dedup_keys")
        if (
            payload.get("batch_sha256") != batch_sha256
            or not isinstance(dedup_keys, list)
            or not dedup_keys
            or len(dedup_keys) != len(set(dedup_keys))
            or any(
                set(dedup_keys) & set(existing.get("normalized_dedup_keys", []))
                for existing in projection["source_observations"].values()
            )
        ):
            raise IntegrityError("Scout observation identity or alias collision")
        observed = {
            **projection["source_observations"],
            observation_id: {"content_sha256": batch_sha256, "normalized_dedup_keys": deepcopy(dedup_keys)},
        }
        candidate_events: list[tuple[str, str, dict[str, Any]]] = []
        seen_candidates: set[str] = set()
        for blueprint in blueprints:
            if not isinstance(blueprint, dict):
                raise IntegrityError("invalid Scout Candidate blueprint")
            candidate_id = blueprint.get("candidate_id")
            refs = blueprint.get("source_observation_refs")
            if (
                set(blueprint) != {"candidate_id", "revision", "content_sha256", "source_observation_refs", "title"}
                or not isinstance(candidate_id, str)
                or candidate_id in seen_candidates
                or _discovery_identity_exists(projection, candidate_id)
                or candidate_id == observation_id
                or blueprint.get("revision") != 1
                or not isinstance(blueprint.get("title"), str)
                or not blueprint["title"]
                or not isinstance(refs, list)
                or observation_id not in refs
            ):
                raise IntegrityError("invalid Scout Candidate blueprint")
            multiset_hash = _source_observation_multiset_hash(refs, observed)
            if blueprint.get("content_sha256") != multiset_hash:
                raise IntegrityError("Scout Candidate content hash does not match observations")
            seen_candidates.add(candidate_id)
            candidate_events.append(
                (
                    "CandidateRegistered",
                    candidate_id,
                    {
                        **deepcopy(blueprint),
                        "owner_row_id": "OR-029",
                        "source_observation_multiset_hash": multiset_hash,
                    },
                )
            )
        observation_payload = {
            "row_id": "OR-029",
            "observation_id": observation_id,
            "batch": deepcopy(batch),
            "content_sha256": batch_sha256,
            "normalized_dedup_keys": deepcopy(dedup_keys),
        }
        return [("ScoutObservationIngested", observation_id, observation_payload), *candidate_events]
