"""Deterministic Discovery replay.

This module owns the durable-ledger preconditions, the mutable projection, the
shared-ledger partition, the transaction-join helpers and the authority shadow
lane.  It owns no lifecycle policy: every accepted event type is reduced by
exactly one function in :mod:`research_system.discovery.replay.registry`.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable, Iterable, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import reduce_artefact, replay_control_plane
from research_system.discovery.assay_authority import replay_assay_bar_authority
from research_system.discovery.authority import replay_authority
from research_system.discovery.commands import discovery_resolve_transaction_ids
from research_system.discovery.ledger_integrity import (
    _default_replay_schemas,
    _validate_hash_chain,
    _validate_persisted_event_envelopes,
)
from research_system.discovery.replay.registry import REDUCERS
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.replay.transactions import validate_transaction_contract
from research_system.discovery.routes import discovery_identity_exists as _discovery_identity_exists
from research_system.discovery.routes import shared_event_partition as _shared_event_partition
from research_system.errors import IntegrityError
from research_system.schema_registry import SchemaRegistry


def replay_discovery(
    events: Iterable[dict[str, Any]],
    *,
    schemas: SchemaRegistry | None = None,
    registered_source_resolver: Callable[[Mapping[str, object]], Mapping[str, object]] | None = None,
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
    active_schemas = schemas or _default_replay_schemas()
    _validate_persisted_event_envelopes(ordered, active_schemas)
    resolve_transaction_ids = discovery_resolve_transaction_ids(ordered)
    transaction_events: dict[Any, list[dict[str, Any]]] = {}
    for persisted_event in ordered:
        transaction_events.setdefault(persisted_event.get("transaction_id"), []).append(persisted_event)
    for transaction in transaction_events.values():
        validate_transaction_contract(transaction)

    def raw_prefix_sha256(global_position: int) -> str:
        """Reconstruct exact canonical batch bytes through a transaction boundary."""

        if type(global_position) is not int or global_position < 0:
            raise IntegrityError("raw ledger prefix position is invalid")
        prefix = bytearray()
        for transaction in transaction_events.values():
            positions = [event.get("global_position") for event in transaction]
            if not positions or not all(type(position) is int for position in positions):
                raise IntegrityError("raw ledger prefix transaction position is invalid")
            first_position = min(positions)
            last_position = max(positions)
            if last_position <= global_position:
                for persisted_event in transaction:
                    prefix.extend(canonical_bytes(persisted_event))
                    prefix.extend(b"\n")
            elif first_position <= global_position:
                raise IntegrityError("raw ledger prefix splits one atomic event batch")
            else:
                break
        return sha256_hex(bytes(prefix))

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

    def candidate_spike_link_matches(
        event: Mapping[str, Any],
        payload: Mapping[str, Any],
        *,
        candidate_status: str,
        spike_status: str,
        spike_event_type: str,
    ) -> bool:
        """Bind a Candidate link to its exact preceding Spike result transaction."""

        candidate_id = payload.get("candidate_id")
        spike_id = payload.get("spike_id")
        candidate = state["candidates"].get(candidate_id)
        spike = state["spikes"].get(spike_id)
        preceding_spike_events = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") == spike_event_type
        ]
        return bool(
            isinstance(candidate, Mapping)
            and isinstance(spike, Mapping)
            and event.get("stream_id") == candidate_id
            and candidate.get("status") == candidate_status
            and candidate.get("spike_id") == spike_id
            and spike.get("status") == spike_status
            and spike.get("candidate_id") == candidate_id
            and len(preceding_spike_events) == 1
            and preceding_spike_events[0].get("stream_id") == spike_id
            and preceding_spike_events[0].get("payload") == payload
        )

    def preceding_transaction_event_matches(
        event: Mapping[str, Any],
        payload: Mapping[str, Any],
        *,
        event_type: str,
        stream_id: Any,
    ) -> bool:
        """Bind a shadow transition to one exact preceding same-transaction event."""

        preceding = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") == event_type
        ]
        return bool(
            len(preceding) == 1
            and preceding[0].get("stream_id") == stream_id
            and preceding[0].get("payload") == payload
        )

    def following_transaction_event_matches(
        event: Mapping[str, Any],
        payload: Mapping[str, Any],
        *,
        event_type: str,
        stream_id: Any,
    ) -> bool:
        """Bind a primary transition to one exact following same-transaction shadow."""

        following = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) > event.get("transaction_index", 0)
            and transaction_event.get("event_type") == event_type
        ]
        if len(following) != 1 or following[0].get("stream_id") != stream_id:
            return False
        following_payload = following[0].get("payload")
        if not isinstance(following_payload, Mapping):
            return False
        for key in payload:
            if key not in following_payload:
                raise IntegrityError(f"Discovery event payload requires {key}")
        for key in following_payload:
            if key not in payload:
                raise IntegrityError(f"Discovery event payload requires {key}")
        return following_payload == payload

    def review_verdict_precedes(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
        """Bind a satisfied lifecycle transition to its exact review verdict transaction."""

        preceding = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") == "ReviewVerdictRecorded"
        ]
        if len(preceding) != 1 or preceding[0].get("stream_id") != payload.get("review_id"):
            return False
        verdict = preceding[0].get("payload")
        return bool(
            isinstance(verdict, Mapping)
            and verdict.get("review_id") == payload.get("review_id")
            and verdict.get("unchanged_subject_sha256") == payload.get("subject_sha256")
        )

    def candidate_assay_link_matches(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
        """Bind a Candidate link to the exact Assay score in its transaction."""

        candidate_id = payload.get("candidate_id")
        assay_id = payload.get("assay_id")
        candidate = state["candidates"].get(candidate_id)
        assay = state["assays"].get(assay_id)
        scored_events = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") == "AssayScored"
        ]
        return bool(
            isinstance(candidate, Mapping)
            and isinstance(assay, Mapping)
            and event.get("stream_id") == candidate_id
            and candidate.get("status") == "assay_pending"
            and candidate.get("assay_id") == assay_id
            and assay.get("status") == "scored"
            and assay.get("candidate_id") == candidate_id
            and len(scored_events) == 1
            and scored_events[0].get("stream_id") == assay_id
            and scored_events[0].get("payload") == payload
        )

    def candidate_spike_plan_link_matches(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
        """Bind a Candidate link to the exact planned and approval-pending Spike."""

        candidate_id = payload.get("candidate_id")
        spike_id = payload.get("spike_id")
        candidate = state["candidates"].get(candidate_id)
        spike = state["spikes"].get(spike_id)
        preceding = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") in {"SpikePlanned", "SpikeApprovalRequested"}
        ]
        return bool(
            isinstance(candidate, Mapping)
            and isinstance(spike, Mapping)
            and event.get("stream_id") == candidate_id
            and candidate.get("status") == "spike_planning_authorized"
            and spike.get("status") == "approval_pending"
            and spike.get("candidate_id") == candidate_id
            and len(preceding) == 2
            and tuple(item.get("event_type") for item in preceding) == ("SpikePlanned", "SpikeApprovalRequested")
            and all(item.get("stream_id") == spike_id and item.get("payload") == payload for item in preceding)
        )

    def spike_operational_closure_matches(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
        """Join a Spike shadow closure to its exact canonical Attempt and Lease events."""

        spike = state["spikes"].get(payload.get("spike_id"))
        if not isinstance(spike, Mapping) or spike.get("status") not in {"partial_recorded", "cancelled"}:
            return False
        transaction_id = event.get("transaction_id")
        preceding = [
            transaction_event
            for transaction_event in transaction_events.get(transaction_id, ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") in {"PartialOutcomeRecorded", "LeaseReleased"}
        ]
        partials = [item for item in preceding if item.get("event_type") == "PartialOutcomeRecorded"]
        releases = [item for item in preceding if item.get("event_type") == "LeaseReleased"]
        try:
            prior_operational = replay_control_plane(
                item for item in operational_events if item.get("transaction_id") != transaction_id
            )
            attempt = prior_operational.stream_states.get(spike.get("attempt_id"))
            lease = prior_operational.stream_states.get(spike.get("lease_id"))
            artifact_key = "verdict_artifact" if spike.get("status") == "partial_recorded" else "cancellation_artifact"
            artifact = payload.get(artifact_key)
            if not isinstance(artifact, Mapping):
                return False
            if spike.get("status") == "partial_recorded":
                expected_partial = {
                    "attempt_id": attempt["attempt_id"],
                    "completed_obligations": [artifact["completed_scope"]],
                    "unmet_obligations": [artifact["unmet_scope"]],
                    "candidate_artefact_ids": [payload["verdict_sha256"]],
                    "stop_cause": "spike_partial",
                    "restrictions": list(dict.fromkeys([*artifact["limitations"], *artifact["prohibited_inferences"]])),
                    "subject_kind": "attempt",
                }
                release_reason = "spike_partial"
            else:
                expected_partial = {
                    "attempt_id": attempt["attempt_id"],
                    "completed_obligations": list(artifact.get("completed_scope", [])),
                    "unmet_obligations": list(artifact.get("unmet_scope", ["cancelled"])),
                    "candidate_artefact_ids": [payload["cancellation_sha256"]],
                    "stop_cause": "discovery_evaluation_cancelled",
                    "restrictions": list(artifact.get("restrictions", ["no_promotion"])),
                    "subject_kind": "attempt",
                }
                release_reason = "discovery_evaluation_cancelled"
            expected_release = {
                "lease_id": lease["lease_id"],
                "release_reason": release_reason,
                "holder_actor_id": lease["holder_actor_id"],
                "observed_at": event["occurred_at"],
            }
        except (AttributeError, KeyError, TypeError, ValueError):
            return False
        return bool(
            event.get("stream_id") == payload.get("spike_id")
            and payload.get("attempt_id") == spike.get("attempt_id")
            and payload.get("lease_id") == spike.get("lease_id")
            and isinstance(attempt, Mapping)
            and attempt.get("status") == "running"
            and sha256_hex(canonical_bytes(attempt)) == spike.get("attempt_sha256")
            and attempt.get("lease_id") == spike.get("lease_id")
            and isinstance(lease, Mapping)
            and lease.get("status") == "active"
            and sha256_hex(canonical_bytes(lease)) == spike.get("lease_sha256")
            and lease.get("attempt_id") == spike.get("attempt_id")
            and len(partials) == len(releases) == 1
            and partials[0].get("stream_id") == spike.get("attempt_id")
            and partials[0].get("payload") == expected_partial
            and releases[0].get("stream_id") == spike.get("lease_id")
            and releases[0].get("payload") == expected_release
            and releases[0].get("occurred_at") == event.get("occurred_at")
        )

    def dossier_materialization_transaction_matches(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
        """Bind one materialization to its exact admission in the same transaction."""

        dossier_id = payload.get("dossier_id")
        dossier = state["dossiers"].get(dossier_id)
        admissions = [
            transaction_event
            for transaction_event in transaction_events.get(event.get("transaction_id"), ())
            if transaction_event.get("transaction_index", 0) < event.get("transaction_index", 0)
            and transaction_event.get("event_type") == "ResearchDossierAdmitted"
            and transaction_event.get("stream_id") == dossier_id
            and isinstance(transaction_event.get("payload"), Mapping)
            and transaction_event["payload"].get("dossier_id") == dossier_id
        ]
        return bool(
            isinstance(dossier_id, str)
            and isinstance(dossier, Mapping)
            and dossier.get("status") == "admitted"
            and len(admissions) == 1
        )

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
                    canonical_artefact_streams[stream_id].update(
                        {
                            "registration_actor_id": event.get("actor_id"),
                            "registration_event_id": event.get("event_id"),
                            "registration_event_hash": event.get("event_hash"),
                            "registration_global_position": event.get("global_position"),
                        }
                    )
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
            if state.get("catalogue") is None:
                raise IntegrityError("W11 genesis is required before authority replay")
            authority_payload = payload.get("authority_payload")
            if not isinstance(authority_payload, dict):
                raise IntegrityError("Discovery event payload requires authority_payload")
            authority_payload = deepcopy(authority_payload)
            accepted_authority_types = {
                "DossierExpectedSetAccepted",
                "PathRegistrationAccepted",
                "AssayBarAccepted",
            }
            if payload.get("authority_event_type") in accepted_authority_types:
                shadow_actor_id = authority_payload.get("acceptor_actor_id")
            else:
                shadow_actor_id = authority_payload.get("actor_id")
            if shadow_actor_id != event.get("actor_id"):
                raise IntegrityError("Discovery authority shadow actor mismatch")
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
            if event_type == "ReviewRequested" and event.get("stream_id") != payload.get("new_review_id"):
                raise IntegrityError("W11 authority review stream mismatch")
            if event_type == "ReviewVerdictRecorded" and event.get("stream_id") != payload.get("review_id"):
                raise IntegrityError("W11 authority verdict stream mismatch")
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
                if event_type == "ReviewVerdictRecorded" and payload.get("review_id") != current.get("review_id"):
                    raise IntegrityError("W11 authority verdict review mismatch")
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
            if event_type == "ReviewVerdictRecorded" and payload.get("review_id") != current.get("review_id"):
                raise IntegrityError("W11 authority verdict review mismatch")
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
        reducer = REDUCERS.get(event_type)
        if reducer is None:
            raise IntegrityError(f"unsupported Discovery event: {event_type}")
        reducer(
            EventScope(
                state=state,
                event=event,
                payload=payload,
                event_type=event_type,
                active_schemas=active_schemas,
                transaction_events=transaction_events,
                operational_events=operational_events,
                canonical_artefact_streams=canonical_artefact_streams,
                raw_prefix_sha256=raw_prefix_sha256,
                registered_source_resolver=registered_source_resolver,
                required_string=required_string,
                required_int=required_int,
                required_string_list=required_string_list,
                aggregate_identity_exists=aggregate_identity_exists,
                claim_authority_stream=claim_authority_stream,
                candidate_spike_link_matches=candidate_spike_link_matches,
                preceding_transaction_event_matches=preceding_transaction_event_matches,
                following_transaction_event_matches=following_transaction_event_matches,
                review_verdict_precedes=review_verdict_precedes,
                candidate_assay_link_matches=candidate_assay_link_matches,
                candidate_spike_plan_link_matches=candidate_spike_plan_link_matches,
                spike_operational_closure_matches=spike_operational_closure_matches,
                dossier_materialization_transaction_matches=dossier_materialization_transaction_matches,
            )
        )
    try:
        replay_control_plane(operational_events)
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError("invalid Discovery operational partition") from exc
    if any(
        decision.get("status") in {"cancellation_pending", "candidate_cancellation_pending"}
        for decision in state["decisions"].values()
    ):
        raise IntegrityError("incomplete Spike execution proposal cancellation")
    for dossier_id, dossier in state["dossiers"].items():
        manifest = dossier.get("candidate_manifest")
        if not isinstance(manifest, Mapping):
            raise IntegrityError("Research dossier materialization manifest mismatch")
        manifest_objects = manifest.get("object_blueprints")
        manifest_edges = manifest.get("dependency_edges")
        manifest_scopes = manifest.get("scope_definition_blueprints")
        if not all(isinstance(value, list) for value in (manifest_objects, manifest_edges, manifest_scopes)):
            raise IntegrityError("Research dossier materialization manifest mismatch")
        expected_objects = {
            value.get("proposed_record_id"): value for value in manifest_objects if isinstance(value, Mapping)
        }
        expected_edges = {
            value.get("proposed_edge_id"): value for value in manifest_edges if isinstance(value, Mapping)
        }
        expected_scopes = {
            value.get("proposed_scope_id"): value for value in manifest_scopes if isinstance(value, Mapping)
        }
        observed_objects = {
            key: value
            for key, value in state["portfolio_objects"].items()
            if value.get("dossier_id") == dossier_id and value.get("portfolio_kind") != "dependency_edge"
        }
        observed_edges = {
            key: value
            for key, value in state["portfolio_objects"].items()
            if value.get("dossier_id") == dossier_id and value.get("portfolio_kind") == "dependency_edge"
        }
        observed_scopes = {
            key: value for key, value in state["scopes"].items() if value.get("dossier_id") == dossier_id
        }
        if (
            set(expected_objects) != set(observed_objects)
            or set(expected_edges) != set(observed_edges)
            or set(expected_scopes) != set(observed_scopes)
            or any(observed_objects[key].get("blueprint") != expected for key, expected in expected_objects.items())
            or any(observed_edges[key].get("blueprint") != expected for key, expected in expected_edges.items())
            or any(observed_scopes[key].get("blueprint") != expected for key, expected in expected_scopes.items())
            or dossier.get("relationships") != manifest.get("relationships")
        ):
            raise IntegrityError("Research dossier materialization closure mismatch")
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
