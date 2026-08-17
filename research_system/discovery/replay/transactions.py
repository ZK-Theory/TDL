"""Shared exact-transaction contracts for Discovery replay.

The event ledger guarantees that a transaction is contiguous and consistently
provenanced.  This module owns the next semantic layer: a W11 command's
complete ordered write set.  Reducers may still validate their own state
transition, but may not treat a surviving subset of a multi-stream command as
an independently valid command.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.routes import DISCOVERY_ROW_ROUTES
from research_system.errors import IntegrityError


@dataclass(frozen=True)
class TransactionVariant:
    """One allowed write set and its command-preimage binding policy."""

    event_types: tuple[str, ...]
    command_payload_binding: str


@dataclass(frozen=True)
class TransactionContract:
    """One exhaustive durable transaction contract for an executable W11 row."""

    command_type: str
    variants: tuple[TransactionVariant, ...]


_CATALOGUE_EVENT_ALIASES = {
    "CandidateRevisitRequested/assay": "CandidateAssayRevisitRequested",
    "CandidateRevisitRequested/spike": "CandidateSpikeRevisitRequested",
    "CandidateRevisitResolved/assay": "CandidateAssayRevisitResolved",
    "CandidateRevisitResolved/spike": "CandidateSpikeRevisitResolved",
    "CandidateEvaluationCancelled/spike": "CandidateEvaluationCancelled",
    "SpikeAttemptClosed/partial": "SpikeAttemptClosed",
    "SpikeAttemptClosed/cancelled": "SpikeAttemptClosed",
    "W11AuthorityFileObserved/dossier_expected_set": "W11AuthorityFileObserved",
    "W11AuthorityFileObserved/path_registration": "W11AuthorityFileObserved",
    "AssayReviewRequested": "AssayOutcomeReviewRequested",
}


def _catalogue_write_set(row_id: str) -> tuple[str, ...]:
    """Translate accepted catalogue names to their exact durable event names."""

    return tuple(
        _CATALOGUE_EVENT_ALIASES.get(event_type, event_type)
        for event_type in DISCOVERY_ROW_ROUTES[row_id].catalogue_events
    )


_WRITE_SET_OVERRIDES: dict[str, tuple[tuple[str, ...], ...]] = {
    "OR-109": (
        ("AssayBarStaled",),
        ("AssayAuthoritySuccessorRegistered", "AssayBarStaled"),
    ),
    "OR-011": (
        (
            "AssayRequested",
            "AssayEvidenceCollectionOpened",
            "AssaySuperseded",
            "CandidateAssayRetryStarted",
        ),
    ),
    "OR-019": (
        (
            "SpikePartialRecorded",
            "PartialOutcomeRecorded",
            "LeaseReleased",
            "SpikeAttemptClosed",
            "SpikeLeaseReleased",
            "CandidateSpikePartialLinked",
        ),
    ),
    "OR-022": tuple(
        prefix + ("SpikeCancelled",) + operational + ("CandidateEvaluationCancelled",)
        for prefix in ((), ("SpikeExecutionProposalSupersededByCancellation",))
        for operational in (
            (),
            ("PartialOutcomeRecorded", "LeaseReleased", "SpikeAttemptClosed", "SpikeLeaseReleased"),
        )
    ),
    "OR-025": (
        (
            "SpikePlanned",
            "SpikeApprovalRequested",
            "SpikeSuperseded",
            "CandidateSpikeRetryStarted",
        ),
    ),
}

for _conditional_review_row in ("OR-006", "OR-007", "OR-020", "OR-021", "OR-039", "OR-041"):
    _WRITE_SET_OVERRIDES[_conditional_review_row] = (
        ("ReviewVerdictRecorded",),
        _catalogue_write_set(_conditional_review_row),
    )


STATEFUL_COMMAND_VARIANTS = {
    **{
        (row_id, ("ReviewVerdictRecorded",)): (
            "unsatisfied review verdict reconstructs its subject from the prior Review request"
        )
        for row_id in ("OR-006", "OR-007", "OR-020", "OR-021", "OR-039", "OR-041")
    },
    (
        "OR-028",
        _catalogue_write_set("OR-028"),
    ): "candidate member bytes are bound by accepted expected-set and manifest closure",
    (
        "OR-106",
        _catalogue_write_set("OR-106"),
    ): "authority verdict subject is reconstructed from the prior Review request",
    (
        "OR-108",
        _catalogue_write_set("OR-108"),
    ): "owner resolution replaces its preparation-only transaction marker with the ledger transaction",
    (
        "OR-113",
        _catalogue_write_set("OR-113"),
    ): "authority verdict subject is reconstructed from the prior Review request",
    (
        "OR-115",
        _catalogue_write_set("OR-115"),
    ): "owner resolution replaces its preparation-only transaction marker with the ledger transaction",
    (
        "OR-119",
        _catalogue_write_set("OR-119"),
    ): "authority verdict subject is reconstructed from the prior Review request",
    (
        "OR-121",
        _catalogue_write_set("OR-121"),
    ): "owner resolution replaces its preparation-only transaction marker with the ledger transaction",
}


TRANSACTION_CONTRACTS: dict[str, TransactionContract] = {
    row_id: TransactionContract(
        command_type=route.command_type,
        variants=tuple(
            TransactionVariant(
                event_types=event_types,
                command_payload_binding=(
                    "stateful" if (row_id, event_types) in STATEFUL_COMMAND_VARIANTS else "durable"
                ),
            )
            for event_types in _WRITE_SET_OVERRIDES.get(row_id, (_catalogue_write_set(row_id),))
        ),
    )
    for row_id, route in DISCOVERY_ROW_ROUTES.items()
}

if set(TRANSACTION_CONTRACTS) != set(DISCOVERY_ROW_ROUTES):  # pragma: no cover - import-time architecture fence
    raise RuntimeError("Discovery transaction contracts do not cover every executable W11 row")
if {
    (row_id, variant.event_types)
    for row_id, contract in TRANSACTION_CONTRACTS.items()
    for variant in contract.variants
    if variant.command_payload_binding == "stateful"
} != set(STATEFUL_COMMAND_VARIANTS):  # pragma: no cover - import-time architecture fence
    raise RuntimeError("Discovery stateful command bindings do not match exact transaction variants")


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
        for ref_field in ("governing_refs", "governing_evidence_refs"):
            refs = payload.get(ref_field)
            if isinstance(refs, list):
                rows.update(
                    ref.removeprefix("W11:") for ref in refs if isinstance(ref, str) and ref.startswith("W11:OR-")
                )
    if len(rows) > 1:
        raise IntegrityError("Discovery transaction carries conflicting W11 owner rows")
    return next(iter(rows)) if rows else None


def _assert_exact_event_types(
    events: Sequence[Mapping[str, Any]], expected_variants: tuple[tuple[str, ...], ...], row_id: str
) -> None:
    """Reject a deleted, added, reordered or substituted write-set member."""

    actual = tuple(str(event.get("event_type")) for event in events)
    if actual not in expected_variants:
        raise IntegrityError(f"Discovery transaction write set mismatch for {row_id}")


def _event_stream_subject(event_type: str, payload: Mapping[str, Any]) -> object:
    """Resolve an event's aggregate identity from its immutable payload."""

    if event_type == "W11CatalogueGenesisImported":
        return CATALOGUE_STREAM_ID
    if event_type == "ScoutObservationIngested":
        return payload.get("observation_id")
    if event_type == "CandidateSuperseded":
        predecessor = payload.get("predecessor_ref")
        return predecessor.get("id") if isinstance(predecessor, Mapping) else None
    if event_type == "CandidateRegistered" or event_type.startswith("Candidate"):
        return payload.get("candidate_id")
    if event_type == "AssaySuperseded":
        return payload.get("old_assay_id")
    if event_type.startswith("Assay"):
        return payload.get("assay_id")
    if event_type == "SpikeSuperseded":
        return payload.get("old_spike_id")
    if event_type.startswith("Spike"):
        if event_type == "SpikeExecutionProposalSupersededByCancellation":
            return payload.get("decision_id")
        return payload.get("spike_id")
    if event_type == "ReviewRequested":
        return payload.get("new_review_id")
    if event_type == "ReviewVerdictRecorded":
        return payload.get("review_id")
    if event_type == "DecisionProposed":
        return payload.get("new_decision_id")
    if event_type == "DecisionResolved":
        return payload.get("decision_id")
    if event_type == "PartialOutcomeRecorded":
        return payload.get("attempt_id")
    if event_type == "LeaseReleased":
        return payload.get("lease_id")
    if event_type == "ResearchDossierAdmitted":
        return payload.get("dossier_id")
    if event_type == "PortfolioObjectRegistered":
        return payload.get("record_id")
    if event_type == "ScopeDefinitionRegistered":
        return payload.get("scope_id")
    authority_payload = payload.get("authority_payload")
    if isinstance(authority_payload, Mapping):
        if event_type in {"AssayRubricContentRegistered", "AssayEvidenceScopeContentRegistered"}:
            content = authority_payload.get("content")
            return content.get("record_id") if isinstance(content, Mapping) else None
        if event_type in {"DossierExpectedSetContentRegistered", "PathRegistrationContentRegistered"}:
            # These commands mint a dedicated authority stream distinct from
            # the immutable content record carried by the subject.
            return None
        if event_type in {"AssayBarAccepted", "DossierExpectedSetAccepted", "PathRegistrationAccepted"}:
            return authority_payload.get("decision_id")
    return None


def _assert_stream_contract(events: Sequence[Mapping[str, Any]], row_id: str) -> None:
    """Bind every event stream whose subject is represented in durable payload."""

    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            raise IntegrityError(f"Discovery transaction payload mismatch for {row_id}")
        expected_stream = _event_stream_subject(str(event.get("event_type")), payload)
        if expected_stream is not None and event.get("stream_id") != expected_stream:
            raise IntegrityError(f"Discovery transaction stream mismatch for {row_id}")


def _command_payload_candidates(row_id: str, events: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    """Return deterministic public-command preimages recoverable from a batch."""

    candidates: list[Mapping[str, Any]] = []
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        candidates.append(dict(payload))
        normalized = deepcopy(dict(payload))
        if "owner_row_id" in normalized:
            normalized["row_id"] = normalized.pop("owner_row_id")
        for derived in (
            "execution_authority_relation",
            "lease_sha256",
            "producer_actor_id",
            "source_observation_multiset_hash",
            "lineage",
            "lineage_sha256",
            "promotion_gate",
            "selected_option",
            "next_candidate_state",
        ):
            normalized.pop(derived, None)
        candidates.append(normalized)

    if row_id == "OR-001" and candidates:
        direct = dict(candidates[0])
        direct.pop("owner_row_id", None)
        direct.pop("source_observation_multiset_hash", None)
        candidates.append(direct)
    elif row_id == "OR-002" and candidates:
        direct = dict(candidates[0])
        direct["row_id"] = direct.pop("owner_row_id", row_id)
        direct.pop("lineage", None)
        direct.pop("lineage_sha256", None)
        candidates.append(direct)
    elif row_id == "OR-029" and events:
        observation = events[0].get("payload")
        blueprints = [event.get("payload") for event in events[1:]]
        if isinstance(observation, Mapping) and all(isinstance(value, Mapping) for value in blueprints):
            candidates.append(
                {
                    "row_id": "OR-029",
                    "observation_id": observation.get("observation_id"),
                    "batch": deepcopy(observation.get("batch")),
                    "batch_sha256": observation.get("content_sha256"),
                    "candidate_blueprints": [
                        {
                            key: deepcopy(value)
                            for key, value in blueprint.items()
                            if key not in {"owner_row_id", "source_observation_multiset_hash"}
                        }
                        for blueprint in blueprints
                    ],
                }
            )
    elif row_id == "OR-140":
        candidates.append(dict(ACCEPTED))
    if events:
        source_event = (
            next(
                (
                    event
                    for event in events
                    if isinstance(event.get("payload"), Mapping)
                    and event["payload"].get("authority_event_type") == "AssayBarStaled"
                ),
                events[0],
            )
            if row_id == "OR-109"
            else events[0]
        )
        payload = source_event.get("payload")
        if isinstance(payload, Mapping):
            authority_payload = payload.get("authority_payload")
            authority_kind = payload.get("authority_kind")
            if isinstance(authority_payload, Mapping) and isinstance(authority_kind, str):
                base = {"row_id": row_id, "authority_kind": authority_kind}
                if row_id in {"OR-101", "OR-102"}:
                    candidates.append(
                        {
                            **base,
                            "content": deepcopy(authority_payload.get("content")),
                            "authority_file_path": authority_payload.get("authority_file_path"),
                        }
                    )
                elif row_id in {"OR-103", "OR-104"}:
                    candidates.append(base)
                elif row_id == "OR-109":
                    candidate = {
                        **base,
                        "acceptance_sha256": authority_payload.get("acceptance_sha256"),
                        "trigger_evidence_refs": deepcopy(authority_payload.get("trigger_evidence_refs")),
                    }
                    if "source_correction_trigger" in authority_payload:
                        candidate["source_correction_trigger"] = deepcopy(
                            authority_payload["source_correction_trigger"]
                        )
                    candidates.append(candidate)
                elif row_id in {"OR-110", "OR-116"}:
                    candidates.append({**base, "subject": deepcopy(authority_payload.get("subject"))})
                elif row_id in {"OR-111", "OR-117"}:
                    candidates.append({**base, "subject_sha256": authority_payload.get("subject_sha256")})
            if row_id in {"OR-105", "OR-112", "OR-118"}:
                refs = payload.get("governing_refs")
                reviewer = payload.get("reviewer_capability")
                kind = (
                    next(
                        (
                            value.removeprefix("authority-kind:")
                            for value in refs
                            if isinstance(value, str) and value.startswith("authority-kind:")
                        ),
                        None,
                    )
                    if isinstance(refs, list)
                    else None
                )
                if isinstance(reviewer, list) and reviewer and isinstance(kind, str):
                    candidate = {"row_id": row_id, "authority_kind": kind, "reviewer_actor_id": reviewer[0]}
                    if row_id == "OR-105":
                        producer_ref = next(
                            (
                                value.removeprefix("prospective-producer:")
                                for value in refs
                                if isinstance(value, str) and value.startswith("prospective-producer:")
                            ),
                            None,
                        )
                        if isinstance(producer_ref, str):
                            try:
                                candidate["prospective_producer_ref"] = json.loads(producer_ref)
                            except json.JSONDecodeError:
                                pass
                    candidates.append(candidate)
            elif row_id in {"OR-107", "OR-114", "OR-120"}:
                refs = payload.get("governing_evidence_refs")
                kind = (
                    next(
                        (
                            value.removeprefix("authority-kind:")
                            for value in refs
                            if isinstance(value, str) and value.startswith("authority-kind:")
                        ),
                        None,
                    )
                    if isinstance(refs, list)
                    else None
                )
                if isinstance(kind, str):
                    candidate = {
                        "row_id": row_id,
                        "authority_kind": kind,
                        "proposed_decision": payload.get("recommendation"),
                    }
                    if row_id != "OR-107":
                        candidate["decision_id"] = payload.get("new_decision_id")
                    candidates.append(candidate)
    return tuple(candidates)


def _assert_command_payload_hash(
    events: Sequence[Mapping[str, Any]], command_payload_hash: object, *, row_id: str
) -> None:
    """Bind a persisted transaction back to its submitted command payload."""

    if not isinstance(command_payload_hash, str) or not any(
        sha256_hex(canonical_bytes(candidate)) == command_payload_hash
        for candidate in _command_payload_candidates(row_id, events)
    ):
        raise IntegrityError(f"Discovery command payload mismatch for {row_id}")


def _matching_contract_rows(events: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Resolve route candidates from exact command and durable event sequence."""

    actual = tuple(str(event.get("event_type")) for event in events)
    command_types = {event.get("command_type") for event in events}
    if len(command_types) != 1:
        raise IntegrityError("Discovery transaction carries conflicting command types")
    command_type = next(iter(command_types))

    def matches(row_id: str, contract: TransactionContract) -> bool:
        if row_id == "OR-028":
            return bool(
                actual
                and actual[0] == "ResearchDossierAdmitted"
                and set(actual[1:]) <= {"PortfolioObjectRegistered", "ScopeDefinitionRegistered"}
                and "PortfolioObjectRegistered" in actual
                and "ScopeDefinitionRegistered" in actual
            )
        if row_id == "OR-029":
            return bool(
                len(actual) >= 2
                and actual[0] == "ScoutObservationIngested"
                and set(actual[1:]) == {"CandidateRegistered"}
            )
        return actual in {variant.event_types for variant in contract.variants}

    return tuple(
        row_id
        for row_id, contract in TRANSACTION_CONTRACTS.items()
        if contract.command_type == command_type and matches(row_id, contract)
    )


def _authority_route_from_refs(events: Sequence[Mapping[str, Any]], matched_rows: tuple[str, ...]) -> str | None:
    """Disambiguate shared W2 authority events from their sealed kind reference."""

    if not events:
        return None
    payload = events[0].get("payload")
    if not isinstance(payload, Mapping):
        return None
    refs = payload.get("governing_refs", payload.get("governing_evidence_refs"))
    kind = (
        next(
            (
                value.removeprefix("authority-kind:")
                for value in refs
                if isinstance(value, str) and value.startswith("authority-kind:")
            ),
            None,
        )
        if isinstance(refs, list)
        else None
    )
    route_by_kind = {
        frozenset({"OR-105", "OR-112", "OR-118"}): {
            "assay_bar": "OR-105",
            "dossier_expected_set": "OR-112",
            "path_registration": "OR-118",
        },
        frozenset({"OR-107", "OR-114", "OR-120"}): {
            "assay_bar": "OR-107",
            "dossier_expected_set": "OR-114",
            "path_registration": "OR-120",
        },
    }
    return route_by_kind.get(frozenset(matched_rows), {}).get(kind)


def validate_transaction_contract(events: Sequence[Mapping[str, Any]]) -> None:
    """Validate the static W11 transaction contract before reducer dispatch.

    Every executable W11 row is represented. Reducers still own lifecycle
    state, but no Discovery event can bypass route, write-set, stream, or
    recoverable command-preimage validation merely because its event schema is
    generic.
    """

    if not events:
        return
    row_id = _owner_row_id(events)
    matched_rows = _matching_contract_rows(events)
    discovery_command_types = {contract.command_type for contract in TRANSACTION_CONTRACTS.values()}
    command_type = events[0].get("command_type")
    if row_id is None:
        if matched_rows:
            # Several authority rows deliberately share one W2 event shape;
            # their stateful reducers resolve the exact authority family.
            row_id = _authority_route_from_refs(events, matched_rows) or matched_rows[0]
        elif command_type == "ResolveDecision":
            # A singleton generic C3 ResolveDecision shares the public ledger
            # but is not a Discovery transaction.
            return
        elif command_type not in discovery_command_types:
            return
        else:
            raise IntegrityError("Discovery transaction has no executable W11 route")
    contract = TRANSACTION_CONTRACTS.get(row_id)
    if contract is None:
        if command_type in discovery_command_types:
            raise IntegrityError("Discovery transaction has an unknown W11 owner row")
        return
    if command_type != contract.command_type or row_id not in matched_rows:
        raise IntegrityError(f"Discovery transaction route mismatch for {row_id}")
    actual_event_types = tuple(str(event.get("event_type")) for event in events)
    variant = (
        contract.variants[0]
        if row_id in {"OR-028", "OR-029"}
        else next((item for item in contract.variants if item.event_types == actual_event_types), None)
    )
    if variant is None:
        raise IntegrityError(f"Discovery transaction write set mismatch for {row_id}")
    if row_id not in {"OR-028", "OR-029"}:
        _assert_exact_event_types(events, tuple(item.event_types for item in contract.variants), row_id)
    _assert_stream_contract(events, row_id)
    if variant.command_payload_binding == "durable":
        _assert_command_payload_hash(events, events[0].get("command_payload_hash"), row_id=row_id)


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
            "command_type": TRANSACTION_CONTRACTS[row_id].command_type,
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
