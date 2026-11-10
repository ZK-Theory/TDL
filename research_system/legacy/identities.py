"""W9 identities across the shared ledger (WP9.3 design note §4.3, §9.1).

The shared ledger holds W9, W11 and generic events. A non-W9 command can take an ID that W9 has claimed or reserved,
either as the stream it appends to or as a record ID its payload creates (``RecordScientificReview`` appends to the
artefact stream but creates a ``rev_`` ``review_id``). So every dispatch writer, W9, W11 and generic, refuses before
append a command whose events would append to, or create, an ID that is one of W9's fixed identities or that the W9
projection claims or reserves; and W9 replay refuses a W9 claim of any ID a non-W9 event uses, in either order.

**The created-ID table.** The schemas do not mark which ID-shaped payload fields create a record and which refer to
one, so :data:`NON_W9_ID_FIELDS` classifies them. It covers the fields whose pattern is a W9 record ID kind: ``obj_``
(``recordRef``), ``rev_`` (``reviewRef``) and ``dec_`` (``decisionRef``). An ID of any other kind has another prefix,
so it can never equal a W9 identity. A test walks every core, T2 and live-issue event schema and fails on a field of
those kinds the table omits. W11's ``E:`` events are persisted under ``ars://core/event`` with no per-type payload
schema, so for them the table lists every event type Discovery's reducer registry handles, each with the payload
fields that reducer keys a new aggregate by; a test fails on a registry event type the table omits. Whether each class
is right is a human-review question for WP9.3-1's independent reviewer (note §18): the reducers expose no uniform
record of the IDs an event creates.

This module imports :mod:`research_system.legacy.replay` lazily, so the W11 and generic writers that import it pull
nothing from :mod:`research_system.legacy` until they check.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from research_system.errors import IntegrityError
from research_system.legacy import accepted_w9
from research_system.legacy.accepted_w9 import CATALOGUE_STREAM_ID, RESERVED_IDS

W9_CLAIMABLE_PREFIXES = ("obj_", "rev_", "dec_")
FieldClass = Literal["creation", "reference"]
_C: FieldClass = "creation"
_R: FieldClass = "reference"

# Every ID-shaped payload field of a W9-claimable kind, per non-W9 event type, classified creation or reference.
# Paths use "/" between keys and "[]" for every array item.
NON_W9_ID_FIELDS: Mapping[str, Mapping[str, FieldClass]] = {
    # Core events (.research-system/schemas/core/events).
    "ArtefactRegistered": {"manifest/aliases/[]/scope_id": _R},
    "DecisionAmendmentProposed": {"decision_id": _R},
    "DecisionExpired": {"decision_id": _R},
    "DecisionProposed": {"new_decision_id": _C},
    "DecisionRejected": {"decision_id": _R},
    "DecisionResolved": {"decision_id": _R},
    "DecisionReviewRequested": {"decision_id": _R},
    "DecisionSuperseded": {"decision_id": _R, "replacement_decision_id": _R},
    "LateArtefactAdopted": {"review_id": _R},
    "MessagePublished": {"decision_id": _R, "review_id": _R, "verdict_record_id": _R},
    "ReviewAssigned": {"review_id": _R},
    "ReviewChangesRequested": {"review_id": _R},
    "ReviewRequested": {"new_review_id": _C},
    "ReviewSatisfied": {"review_id": _R},
    "ReviewStarted": {"review_id": _R},
    "ReviewSuperseded": {"review_id": _R, "replacement_review_id": _R},
    "ReviewVerdictRecorded": {"review_id": _R},
    "ReviewWithdrawn": {"review_id": _R},
    "ScientificReviewRecorded": {"artefact_id": _R, "review_id": _C},
    "ScopeCompleted": {"scope_definition_id": _R},
    "ScopeDefinitionAmended": {"scope_definition_id": _R},
    "ScopeDefinitionCreated": {"new_scope_definition_id": _C},
    "ScopeDefinitionSuperseded": {"scope_definition_id": _R, "replacement_scope_definition_id": _R},
    "TaskAmended": {"replacement_definition/aliases/[]/scope_id": _R},
    "TaskCreated": {"definition/aliases/[]/scope_id": _R},
    "TaskRejected": {"review_verdict_id": _R},
    # W11 E: events (discovery/replay/registry.py). The fields each reducer keys a new aggregate by.
    "AssayCancellationReviewRequested": {},
    "AssayCancellationReviewed": {},
    "AssayCancelled": {},
    "AssayEvidenceCollectionOpened": {},
    "AssayOutcomeReviewRequested": {},
    "AssayPartialRecorded": {},
    "AssayPartialReviewRequested": {},
    "AssayPartialReviewed": {},
    "AssayRequested": {"assay_id": _C, "candidate_id": _R},
    "AssayReviewed": {},
    "AssayRevisitRequested": {},
    "AssayRevisitResolved": {},
    "AssayScored": {},
    "AssaySuperseded": {},
    "CandidateAssayCancellationReviewed": {},
    "CandidateAssayLinked": {},
    "CandidateAssayPartialLinked": {},
    "CandidateAssayPartialReviewed": {},
    "CandidateAssayRequested": {},
    "CandidateAssayRetryStarted": {},
    "CandidateAssayRevisitRequested": {},
    "CandidateAssayRevisitResolved": {},
    "CandidateEvaluationCancelled": {},
    "CandidatePromotionApplied": {},
    "CandidatePromotionRequested": {},
    "CandidateRegistered": {"candidate_id": _C},
    "CandidateSpikeAuthorized": {},
    "CandidateSpikeCancellationReviewed": {},
    "CandidateSpikePartialLinked": {},
    "CandidateSpikePartialReviewed": {},
    "CandidateSpikePlanLinked": {},
    "CandidateSpikeRetryStarted": {},
    "CandidateSpikeRevisitRequested": {},
    "CandidateSpikeRevisitResolved": {},
    "CandidateSpikeStarted": {},
    "CandidateSpikeVerdictLinked": {},
    "CandidateSuperseded": {},
    "PortfolioObjectRegistered": {"record_id": _C},
    "ResearchDossierAdmitted": {"dossier_id": _C},
    "ScopeDefinitionRegistered": {"scope_id": _C},
    "ScoutObservationIngested": {"observation_id": _C},
    "SpikeApprovalRequested": {},
    "SpikeAttemptClosed": {},
    "SpikeAuthorized": {},
    "SpikeCancellationReviewRequested": {},
    "SpikeCancellationReviewed": {},
    "SpikeCancelled": {},
    "SpikeExecutionDecisionRequested": {},
    "SpikeExecutionProposalSupersededByCancellation": {},
    "SpikeLeaseReleased": {},
    "SpikePartialRecorded": {},
    "SpikePartialReviewRequested": {},
    "SpikePartialReviewed": {},
    "SpikePlanned": {"spike_id": _C},
    "SpikeReviewRequested": {},
    "SpikeReviewed": {},
    "SpikeRevisitRequested": {},
    "SpikeRevisitResolved": {},
    "SpikeStarted": {},
    "SpikeSuperseded": {},
    "SpikeVerdictRecorded": {},
    "W11CatalogueGenesisImported": {},
}


def _values_at(payload: Any, path: Sequence[str]) -> Iterable[Any]:
    if not path:
        yield payload
        return
    head, rest = path[0], path[1:]
    if head == "[]":
        if isinstance(payload, list):
            for item in payload:
                yield from _values_at(item, rest)
    elif isinstance(payload, Mapping) and head in payload:
        yield from _values_at(payload[head], rest)


def created_ids(event: Mapping[str, Any]) -> frozenset[str]:
    """Return the IDs one event takes: its ``stream_id`` and every record ID its payload creates (§4.3).

    Args:
        event: A persisted or prepared event, with ``event_type``, ``stream_id`` and ``payload``.

    Returns:
        The stream ID and every created ID of a W9-claimable kind. A reference is not a creation.
    """

    taken: set[str] = set()
    stream_id = event.get("stream_id")
    if isinstance(stream_id, str):
        taken.add(stream_id)
    fields = NON_W9_ID_FIELDS.get(str(event.get("event_type")), {})
    for path, field_class in fields.items():
        if field_class != "creation":
            continue
        for value in _values_at(event.get("payload"), path.split("/")):
            if isinstance(value, str):
                taken.add(value)
    return frozenset(taken)


def current_pins(pinned_signatures: Collection[Mapping[str, Any]] | None = None) -> tuple[Mapping[str, Any], ...]:
    """The given pins, or the code's pinned W0 signatures read at call time (§9.1)."""

    return tuple(accepted_w9.ACCEPTED_W0_SIGNATURES if pinned_signatures is None else pinned_signatures)


def pinned_signature_ids(pinned_signatures: Collection[Mapping[str, Any]] | None = None) -> frozenset[str]:
    """Return the ref IDs of the pinned W0 signatures (§9.1)."""

    return frozenset(str(entry["ref"]["id"]) for entry in current_pins(pinned_signatures))


def w9_fixed_identities(pinned_signatures: Collection[Mapping[str, Any]] | None = None) -> frozenset[str]:
    """W9's fixed identities, read from the code constants so they hold before W9 genesis (§4.3)."""

    return frozenset({CATALOGUE_STREAM_ID, *RESERVED_IDS, *pinned_signature_ids(pinned_signatures)})


def w9_claimed_identities(state: Mapping[str, Any]) -> frozenset[str]:
    """Return every ID the W9 projection claims or reserves (§4.3)."""

    return frozenset({*state.get("identities", {}), *state.get("reservations", {})})


def _has_w9_event(events: Iterable[Mapping[str, Any]]) -> bool:
    from research_system.legacy.commands import is_legacy_projection_event

    return any(is_legacy_projection_event(event) for event in events)


def refuse_w9_identity_collision(
    prepared: Iterable[Mapping[str, Any]],
    ledger_events: Sequence[Mapping[str, Any]],
    *,
    schemas: Any = None,
) -> None:
    """Refuse a non-W9 write that would take a W9 identity, before append (§4.3).

    Called by the W11, generic and T2 writers after the stream-version check, over the snapshot they already hold.

    Args:
        prepared: The events the command would append, each with ``event_type``, ``stream_id`` and ``payload``.
        ledger_events: The writer's materialized snapshot events.
        schemas: The writer's schema registry, for the W9 replay.

    Raises:
        IntegrityError: If an event's stream or a created ID is a W9 fixed identity, or one W9 claims or reserves.
    """

    taken: set[str] = set()
    for event in prepared:
        taken |= created_ids(event)
    if not taken:
        return
    if taken & w9_fixed_identities():
        raise IntegrityError("command would take a W9 fixed identity")
    if not _has_w9_event(ledger_events):
        return
    from research_system.legacy.replay.driver import replay_legacy

    state = replay_legacy(ledger_events, schemas=schemas)
    if taken & w9_claimed_identities(state):
        raise IntegrityError("command would take an identity W9 claims or reserves")


@dataclass(frozen=True)
class PrePinCheck:
    """The read-only pre-pin check of a candidate W0 signature ref (§9.1), from one ledger snapshot."""

    candidate_id: str
    collisions: tuple[str, ...]
    global_position: int
    event_hash: str

    @property
    def passed(self) -> bool:
        """Whether neither part found the candidate ID in use."""
        return not self.collisions

    @property
    def expected_ledger_head(self) -> str:
        """The checked head, as ``ars store advance-binding --expected-ledger-head`` takes it."""
        return f"{self.global_position}:{self.event_hash}"


def check_w0_pin_candidate(
    ledger: Any,
    candidate_id: str,
    *,
    schemas: Any,
    authority_state_validator: Callable[..., Any] | None = None,
    pinned_signatures: Collection[Mapping[str, Any]] | None = None,
) -> PrePinCheck:
    """Run the pre-pin check for a candidate W0 signature ref over one snapshot. Writes nothing and takes no lock.

    Both parts and the recorded head come from one ``LedgerSnapshot``: the public shared replay and a W9 replay with
    the candidate pin added, and a scan of every event's stream and created record IDs, of any partition.

    Args:
        ledger: The store's ``EventLedger``.
        candidate_id: The candidate signature ref ID.
        schemas: The store's schema registry.
        authority_state_validator: The authority replay validator the public replay takes.
        pinned_signatures: The pins already accepted.

    Returns:
        The check, with each collision found and the snapshot's head.

    Raises:
        IntegrityError: If the ledger already fails the public shared replay. That replay does not use the candidate,
            so its failure is the ledger's, not a collision; reporting it as one would hide it behind every candidate.
    """

    from research_system.legacy.replay.driver import replay_legacy
    from research_system.projection.replay import replay as replay_shared

    snapshot = ledger.snapshot()
    events = snapshot.events
    collisions: list[str] = []
    candidate_pin = {"ref": {"id": candidate_id}}
    try:
        replay_shared(events, schema_registry=schemas, authority_state_validator=authority_state_validator)
    except (IntegrityError, TypeError, ValueError) as exc:
        raise IntegrityError(f"pre-pin check refused: the ledger fails the public shared replay: {exc}") from exc
    try:
        if _has_w9_event(events):
            replay_legacy(events, schemas=schemas, pinned_signatures=(*current_pins(pinned_signatures), candidate_pin))
    except (IntegrityError, TypeError, ValueError) as exc:
        collisions.append(f"replay: {exc}")
    for event in events:
        if candidate_id in created_ids(event):
            collisions.append(f"event {event.get('global_position')} ({event.get('event_type')}) takes the candidate")
    return PrePinCheck(candidate_id, tuple(collisions), snapshot.global_position, snapshot.event_hash)


def select_w0_signature_ref(
    ledger: Any,
    domain: str,
    accepted_at: str,
    *,
    schemas: Any,
    authority_state_validator: Callable[..., Any] | None = None,
    pinned_signatures: Collection[Mapping[str, Any]] | None = None,
    max_suffix: int = 100,
) -> PrePinCheck:
    """Derive the candidate ref, re-deriving with ``#<n>`` (the next unused ``n``) until the pre-pin check passes."""

    from research_system.legacy.records import w0_signature_ref_id

    for suffix in (None, *range(1, max_suffix + 1)):
        check = check_w0_pin_candidate(
            ledger,
            w0_signature_ref_id(domain, accepted_at, suffix),
            schemas=schemas,
            authority_state_validator=authority_state_validator,
            pinned_signatures=pinned_signatures,
        )
        if check.passed:
            return check
    raise IntegrityError("no unused W0 signature ref within the suffix bound")
