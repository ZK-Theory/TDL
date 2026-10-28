"""Immutable W9 legacy route registry, route classes and transaction row assignment.

This module owns the mapping from each accepted W9 catalogue row to the producer command, payload discriminant, record
schema and ordered event slots that may execute it (design note §3); the routed/deferred classes; and the rules that
assign a persisted W9 transaction to exactly one row (design note §4). The literal table is checked against the
accepted catalogue by :func:`validate_legacy_route_registry`, at genesis and by test, so it cannot drift from the
accepted bytes.

It is a leaf: it imports only the accepted identity and the command family, and nothing else in
:mod:`research_system.legacy`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy.accepted_w9 import ROW_IDS


@dataclass(frozen=True)
class LegacyEventSlot:
    """One ordered event of an accepted row: its normalized type, and whether it repeats (multiplicity ``0..n``)."""

    event_type: str
    repeated: bool


@dataclass(frozen=True)
class LegacyRowRoute:
    """One accepted W9 row as the runtime and replay see it."""

    command_type: str
    payload_discriminant: str
    record_schema_id: str
    events: tuple[LegacyEventSlot, ...]


# Generated from the accepted catalogue's rows; validate_legacy_route_registry checks it against the bytes.
LEGACY_ROW_ROUTES = {
    "LR-001": LegacyRowRoute(
        "ImportAcceptedW9CatalogueGenesis",
        "import-accepted-w9-catalogue-genesis",
        "ars://legacy/import-accepted-w9-catalogue-genesis",
        (LegacyEventSlot("W9CatalogueGenesisImported", False),),
    ),
    "LR-002": LegacyRowRoute(
        "ImportAcceptedW9CatalogueRevision",
        "import-accepted-w9-catalogue-revision",
        "ars://legacy/import-accepted-w9-catalogue-revision",
        (LegacyEventSlot("W9CatalogueRevisionImported", False),),
    ),
    "LR-003": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_path_registration",
        "ars://legacy/legacy-path-registration",
        (LegacyEventSlot("LegacyPathRegistrationProposed", False),),
    ),
    "LR-004": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_path_registration",
        "ars://legacy/legacy-path-registration",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-005": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_path_registration",
        "ars://legacy/legacy-path-registration",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyPathRegistrationRecorded", False),
        ),
    ),
    "LR-006": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_field_family_membership",
        "ars://legacy/legacy-field-family-membership",
        (LegacyEventSlot("LegacyFieldFamilyMembershipProposed", False),),
    ),
    "LR-007": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_field_family_membership",
        "ars://legacy/legacy-field-family-membership",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-008": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_field_family_membership",
        "ars://legacy/legacy-field-family-membership",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-009": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_field_family_membership",
        "ars://legacy/legacy-field-family-membership",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-010": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_field_family_membership",
        "ars://legacy/legacy-field-family-membership",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyFieldFamilyMembershipRecorded", False),
        ),
    ),
    "LR-011": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_light_inventory",
        "ars://legacy/legacy-light-inventory",
        (LegacyEventSlot("LegacyLightInventoryProposed", False),),
    ),
    "LR-012": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_light_inventory_reproduction",
        "ars://legacy/legacy-light-inventory",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-013": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_light_inventory_reproduction",
        "ars://legacy/legacy-light-inventory",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-014": LegacyRowRoute(
        "RecordLegacyLightInventory",
        "record-legacy-light-inventory",
        "ars://legacy/legacy-light-inventory",
        (LegacyEventSlot("LegacyLightInventoryRecorded", False),),
    ),
    "LR-015": LegacyRowRoute(
        "ObserveLegacyRecord",
        "observe-legacy-record",
        "ars://legacy/legacy-observation",
        (LegacyEventSlot("LegacyRecordObserved", False),),
    ),
    "LR-016": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_closed_reference_acceptance",
        "ars://legacy/legacy-closed-reference-acceptance",
        (LegacyEventSlot("LegacyClosedReferenceAcceptanceProposed", False),),
    ),
    "LR-017": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_closed_reference_acceptance",
        "ars://legacy/legacy-closed-reference-acceptance",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-018": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_closed_reference_acceptance",
        "ars://legacy/legacy-closed-reference-acceptance",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-019": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_closed_reference_acceptance",
        "ars://legacy/legacy-closed-reference-acceptance",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-020": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_closed_reference_acceptance",
        "ars://legacy/legacy-closed-reference-acceptance",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyClosedReferenceAcceptanceRecorded", False),
            LegacyEventSlot("LegacyOwnershipTransitionedRecorded", True),
        ),
    ),
    "LR-021": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/integration_pilot_outcome",
        "ars://legacy/legacy-closed-reference-acceptance",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-022": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/integration_pilot_outcome",
        "ars://legacy/legacy-closed-reference-acceptance",
        (LegacyEventSlot("DecisionResolved", False),),
    ),
    "LR-023": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_adoption_decision",
        "ars://legacy/legacy-adoption-decision",
        (LegacyEventSlot("LegacyAdoptionDecisionProposed", False),),
    ),
    "LR-024": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_adoption_reviewer_eligibility",
        "ars://legacy/legacy-adoption-decision",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-025": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_adoption_reviewer_eligibility",
        "ars://legacy/legacy-adoption-decision",
        (LegacyEventSlot("DecisionResolved", False),),
    ),
    "LR-026": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_adoption_decision",
        "ars://legacy/legacy-adoption-decision",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-027": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_adoption_decision",
        "ars://legacy/legacy-adoption-decision",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-028": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_adoption_decision",
        "ars://legacy/legacy-adoption-decision",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-029": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_adoption_decision",
        "ars://legacy/legacy-adoption-decision",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyAdoptionDecisionRecorded", False),
        ),
    ),
    "LR-030": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_discharge_relation",
        "ars://legacy/legacy-discharge-relation",
        (LegacyEventSlot("LegacyDischargeRelationProposed", False),),
    ),
    "LR-031": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_discharge_relation",
        "ars://legacy/legacy-discharge-relation",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-032": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_discharge_relation",
        "ars://legacy/legacy-discharge-relation",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-033": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_discharge_relation",
        "ars://legacy/legacy-discharge-relation",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-034": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_discharge_relation",
        "ars://legacy/legacy-discharge-relation",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyDischargeRelationRecorded", False),
        ),
    ),
    "LR-035": LegacyRowRoute(
        "CreateLegacyPaperRoot",
        "create-legacy-paper-root/ordinary",
        "ars://legacy/legacy-paper-root",
        (LegacyEventSlot("LegacyPaperRootCreated", False),),
    ),
    "LR-036": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_paper_root_recovery",
        "ars://legacy/legacy-paper-root",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-037": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_paper_root_recovery",
        "ars://legacy/legacy-paper-root",
        (LegacyEventSlot("DecisionResolved", False),),
    ),
    "LR-038": LegacyRowRoute(
        "CreateLegacyPaperRoot",
        "create-legacy-paper-root/recovery",
        "ars://legacy/legacy-paper-root",
        (LegacyEventSlot("LegacyPaperRootCreated", False),),
    ),
    "LR-039": LegacyRowRoute(
        "RecordPaperCitationStatus",
        "record-paper-citation-status",
        "ars://legacy/legacy-paper-citation-status",
        (LegacyEventSlot("LegacyPaperCitationStatusRecorded", False),),
    ),
    "LR-040": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_source_inventory",
        "ars://legacy/legacy-source-inventory",
        (LegacyEventSlot("LegacySourceInventoryProposed", False),),
    ),
    "LR-041": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_source_inventory",
        "ars://legacy/legacy-source-inventory",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-042": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_source_inventory",
        "ars://legacy/legacy-source-inventory",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-043": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_source_inventory",
        "ars://legacy/legacy-source-inventory",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-044": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_source_inventory",
        "ars://legacy/legacy-source-inventory",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacySourceInventoryRecorded", False),
        ),
    ),
    "LR-045": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_transition_mapping",
        "ars://legacy/legacy-transition-mapping",
        (LegacyEventSlot("LegacyTransitionMappingProposed", False),),
    ),
    "LR-046": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_transition_mapping",
        "ars://legacy/legacy-transition-mapping",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-047": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_transition_mapping",
        "ars://legacy/legacy-transition-mapping",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-048": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_transition_mapping",
        "ars://legacy/legacy-transition-mapping",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-049": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_transition_mapping",
        "ars://legacy/legacy-transition-mapping",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyTransitionMappingRecorded", False),
        ),
    ),
    "LR-050": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_ownership_transitioned",
        "ars://legacy/legacy-ownership-transitioned",
        (LegacyEventSlot("LegacyOwnershipTransitionedProposed", False),),
    ),
    "LR-051": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_ownership_transitioned",
        "ars://legacy/legacy-ownership-transitioned",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-052": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_ownership_transitioned",
        "ars://legacy/legacy-ownership-transitioned",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-053": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_ownership_transitioned",
        "ars://legacy/legacy-ownership-transitioned",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-054": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_ownership_transitioned/to_successor_owned",
        "ars://legacy/legacy-ownership-transitioned",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyOwnershipTransitionedRecorded", False),
        ),
    ),
    "LR-055": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_ownership_transitioned/successor_to_closed_reference",
        "ars://legacy/legacy-ownership-transitioned",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyOwnershipTransitionedRecorded", False),
        ),
    ),
    "LR-056": LegacyRowRoute(
        "ProposeLegacyRecord",
        "propose-legacy-record/legacy_record_supersession",
        "ars://legacy/legacy-record-supersession",
        (LegacyEventSlot("LegacyRecordSupersessionProposed", False),),
    ),
    "LR-057": LegacyRowRoute(
        "RequestW9AuthorityReview",
        "request-w9-authority-review/legacy_record_supersession",
        "ars://legacy/legacy-record-supersession",
        (LegacyEventSlot("ReviewRequested", False),),
    ),
    "LR-058": LegacyRowRoute(
        "RecordW9AuthorityReview",
        "record-w9-authority-review/legacy_record_supersession",
        "ars://legacy/legacy-record-supersession",
        (LegacyEventSlot("ReviewVerdictRecorded", False),),
    ),
    "LR-059": LegacyRowRoute(
        "ProposeW9AuthorityDecision",
        "propose-w9-authority-decision/legacy_record_supersession",
        "ars://legacy/legacy-record-supersession",
        (LegacyEventSlot("DecisionProposed", False),),
    ),
    "LR-060": LegacyRowRoute(
        "ResolveW9AuthorityDecision",
        "resolve-w9-authority-decision/legacy_record_supersession",
        "ars://legacy/legacy-record-supersession",
        (
            LegacyEventSlot("DecisionResolved", False),
            LegacyEventSlot("LegacyRecordSupersessionRecorded", False),
        ),
    ),
    "LR-061": LegacyRowRoute(
        "RecordAdoptionUseMismatch",
        "record-adoption-use-mismatch",
        "ars://legacy/legacy-adoption-use-mismatch",
        (LegacyEventSlot("LegacyAdoptionUseMismatchRecorded", False),),
    ),
}

# Design note §3: WP9.2 routes genesis only. Every other row is deferred, tagged with what routes it.
LEGACY_ROUTED_ROWS = frozenset({"LR-001"})
LEGACY_DEFERRED_ROWS = {
    "LR-002": "catalogue_revision",
    **dict.fromkeys((f"LR-{number:03d}" for number in range(3, 21)), "WP9.3"),
    **dict.fromkeys(("LR-021", "LR-022", "LR-024", "LR-025", "LR-061"), "WP9.7"),
    **dict.fromkeys(
        ("LR-023", *(f"LR-{number:03d}" for number in range(26, 36)), "LR-039"),
        "WP9.4",
    ),
    **dict.fromkeys((f"LR-{number:03d}" for number in range(40, 56)), "WP9.4"),
    **dict.fromkeys(("LR-036", "LR-037", "LR-038", *(f"LR-{number:03d}" for number in range(56, 61))), "WP9.6"),
}
DEFERRED_TAGS = frozenset({"catalogue_revision", "WP9.3", "WP9.4", "WP9.6", "WP9.7"})
W2_EVENT_TYPES = frozenset({"ReviewRequested", "ReviewVerdictRecorded", "DecisionProposed", "DecisionResolved"})
# Every W9-specific event type. A non-W9 command may never emit one (design note §2.1).
LEGACY_EVENT_TYPES = frozenset(
    slot.event_type
    for route in LEGACY_ROW_ROUTES.values()
    for slot in route.events
    if slot.event_type not in W2_EVENT_TYPES
)
_W9_ROW_REF = re.compile(r"^W9:(LR-\d{3})$")
_E_ONLY_ROWS = {
    (route.command_type, route.payload_discriminant): row_id
    for row_id, route in LEGACY_ROW_ROUTES.items()
    if route.events[0].event_type not in W2_EVENT_TYPES
}
_VERDICT_ROW_FOR_REQUEST = {
    request_id: verdict_id
    for request_id, request in LEGACY_ROW_ROUTES.items()
    if request.command_type == "RequestW9AuthorityReview"
    for verdict_id, verdict in LEGACY_ROW_ROUTES.items()
    if verdict.command_type == "RecordW9AuthorityReview"
    and verdict.payload_discriminant.removeprefix("record-") == request.payload_discriminant.removeprefix("request-")
}


def legacy_event_name(token: Any) -> str:
    """Normalize one accepted W9 event token (``E:`` or ``W2:``) to its persisted event type.

    Args:
        token: An ``ordered_events`` event token from the accepted catalogue.

    Returns:
        The persisted event type, for example ``W9CatalogueGenesisImported`` for ``E:w9-catalogue-genesis-imported``.

    Raises:
        IntegrityError: If the token is not a valid ``E:`` or ``W2:`` token.
    """

    if not isinstance(token, str) or ":" not in token:
        raise IntegrityError("accepted W9 row contains an invalid event token")
    prefix, name = token.split(":", 1)
    if prefix == "W2":
        return name
    if prefix != "E":
        raise IntegrityError("accepted W9 row contains an unknown event namespace")
    base, separator, suffix = name.partition("/")
    normalized = "".join(part.capitalize() for part in base.split("-") if part)
    return f"{normalized}/{suffix}" if separator else normalized


def command_slug(command_type: str) -> str:
    """Return a command type's kebab-case slug, for example ``observe-legacy-record``."""

    return re.sub(r"(?<!^)(?=[A-Z])", "-", command_type).lower()


def record_kind(schema_id: Any) -> str:
    """Return a W9 record schema's kind with underscores, for example ``legacy_path_registration``."""

    if not isinstance(schema_id, str) or not schema_id.startswith("ars://legacy/"):
        raise IntegrityError("W9 record carries no W9 schema id")
    return schema_id.removeprefix("ars://legacy/").replace("-", "_")


def e_only_discriminant(command_type: str, record: Mapping[str, Any]) -> str:
    """Compute the payload discriminant of a transaction with no W2 event (design note §4).

    Args:
        command_type: The transaction's W9 command type.
        record: The payload of the transaction's first event, which is the W9 record itself.

    Returns:
        The discriminant that, with ``command_type``, selects exactly one accepted row.
    """

    if command_type == "ProposeLegacyRecord":
        return f"propose-legacy-record/{record_kind(record.get('schema_id'))}"
    if command_type == "CreateLegacyPaperRoot":
        if "recovery" not in record:
            raise IntegrityError("W9 paper root carries no recovery field")
        return f"create-legacy-paper-root/{'ordinary' if record['recovery'] is None else 'recovery'}"
    return command_slug(command_type)


def w9_row_ref(refs: Any) -> str:
    """Return the one ``W9:LR-nnn`` row a W2 payload's ref list names.

    Raises:
        IntegrityError: If the list is malformed or does not name exactly one W9 row.
    """

    if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
        raise IntegrityError("W9 W2 event carries malformed governing refs")
    rows = [match.group(1) for ref in refs if (match := _W9_ROW_REF.match(ref))]
    if len(rows) != 1 or any(ref.startswith("W9:") for ref in refs if not _W9_ROW_REF.match(ref)):
        raise IntegrityError("W9 W2 event must name exactly one W9 row")
    return rows[0]


def verdict_row_for_request(request_row: str) -> str:
    """Return the review-verdict row that answers a review-request row."""

    verdict = _VERDICT_ROW_FOR_REQUEST.get(request_row)
    if verdict is None:
        raise IntegrityError("W9 review verdict answers no W9 review request row")
    return verdict


def assign_row(transaction: Sequence[Mapping[str, Any]], review_request_rows: Mapping[str, str]) -> str:
    """Assign one persisted W9 transaction to exactly one accepted row (design note §4).

    Args:
        transaction: The transaction's events, in order.
        review_request_rows: The request row of every W9 review already requested, by review ID.

    Returns:
        The owner row ID the transaction executes.

    Raises:
        IntegrityError: If no accepted row, or more than one, matches the transaction.
    """

    if not transaction:
        raise IntegrityError("empty W9 transaction")
    first = transaction[0]
    command_type = first.get("command_type")
    payload = first.get("payload")
    if not isinstance(payload, Mapping):
        raise IntegrityError("W9 event payload must be an object")
    w2_events = [event for event in transaction if event.get("event_type") in W2_EVENT_TYPES]
    if not w2_events:
        row_id = _E_ONLY_ROWS.get((command_type, e_only_discriminant(str(command_type), payload)))
        if row_id is None:
            raise IntegrityError("W9 transaction matches no accepted row")
        return row_id
    if len(w2_events) != 1 or w2_events[0] is not first:
        raise IntegrityError("W9 transaction must lead with exactly one W2 event")
    event_type = first.get("event_type")
    if event_type == "ReviewRequested":
        row_id = w9_row_ref(payload.get("governing_refs"))
    elif event_type == "ReviewVerdictRecorded":
        request_row = review_request_rows.get(payload.get("review_id"))
        if request_row is None:
            raise IntegrityError("W9 review verdict answers no requested W9 review")
        row_id = verdict_row_for_request(request_row)
    else:
        row_id = w9_row_ref(payload.get("governing_evidence_refs"))
    route = LEGACY_ROW_ROUTES.get(row_id)
    if route is None or route.command_type != command_type or route.events[0].event_type != event_type:
        raise IntegrityError("W9 W2 event names a row of another command or event")
    return row_id


def validate_transaction_shape(row_id: str, event_types: Sequence[str]) -> None:
    """Require a transaction's event types to match its row's accepted ordered events exactly.

    A ``0..n`` slot may repeat any number of times, including none; every other slot occurs exactly once, in order.

    Raises:
        IntegrityError: If the event types differ from the row's accepted write set.
    """

    remaining = list(event_types)
    for slot in LEGACY_ROW_ROUTES[row_id].events:
        if slot.repeated:
            while remaining and remaining[0] == slot.event_type:
                remaining.pop(0)
            continue
        if not remaining or remaining.pop(0) != slot.event_type:
            raise IntegrityError(f"W9 transaction differs from accepted {row_id}")
    if remaining:
        raise IntegrityError(f"W9 transaction differs from accepted {row_id}")


def validate_legacy_route_registry(catalogue: Mapping[str, Any]) -> None:
    """Prove the route table is exact to the accepted W9 catalogue and partitions it 1 routed / 60 deferred.

    Raises:
        IntegrityError: If a row is missing, differs from its accepted bytes, or the classes do not partition the rows.
    """

    rows = catalogue.get("owner_contract_rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise IntegrityError("accepted W9 catalogue rows are invalid")
    by_id = {row.get("owner_row_id"): row for row in rows}
    if (
        tuple(by_id) != ROW_IDS
        or tuple(LEGACY_ROW_ROUTES) != ROW_IDS
        or len(LEGACY_ROUTED_ROWS) != 1
        or len(LEGACY_DEFERRED_ROWS) != 60
        or LEGACY_ROUTED_ROWS & set(LEGACY_DEFERRED_ROWS)
        or LEGACY_ROUTED_ROWS | set(LEGACY_DEFERRED_ROWS) != set(ROW_IDS)
        or set(LEGACY_DEFERRED_ROWS.values()) != DEFERRED_TAGS
    ):
        raise IntegrityError("W9 route registry does not partition the accepted W9 catalogue")
    for row_id, route in LEGACY_ROW_ROUTES.items():
        row = by_id[row_id]
        ordered_events = row.get("ordered_events")
        if not isinstance(ordered_events, list) or not all(isinstance(slot, Mapping) for slot in ordered_events):
            raise IntegrityError(f"W9 route registry differs from accepted {row_id}")
        accepted_slots = tuple(
            LegacyEventSlot(legacy_event_name(slot.get("event")), slot.get("multiplicity") == "0..n")
            for slot in ordered_events
        )
        if (
            row.get("command_type") != route.command_type
            or row.get("payload_discriminant") != route.payload_discriminant
            or row.get("record_schema_id") != route.record_schema_id
            or row.get("record_schema_version") != "1.0.0"
            or any(slot.get("multiplicity") not in {"1", "0..n"} for slot in ordered_events)
            or accepted_slots != route.events
        ):
            raise IntegrityError(f"W9 route registry differs from accepted {row_id}")
