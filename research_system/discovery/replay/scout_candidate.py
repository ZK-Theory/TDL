"""Discovery scout/candidate replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.canonical import canonical_bytes
from research_system.canonical import sha256_hex
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.routes import discovery_identity_exists as _discovery_identity_exists
from research_system.discovery.rules import _candidate_ref
from research_system.discovery.rules import _candidate_replacement_is_used
from research_system.discovery.rules import _candidate_supersession_lineage
from research_system.discovery.rules import _source_observation_multiset_hash
from research_system.errors import IntegrityError
from typing import Mapping


def reduce_scout_observation_ingested(scope: EventScope) -> None:
    """Reduce ScoutObservationIngested."""

    required_string = scope.required_string
    state = scope.state
    payload = scope.payload
    transaction_events = scope.transaction_events
    event = scope.event
    aggregate_identity_exists = scope.aggregate_identity_exists

    observation_id = required_string("observation_id")
    if _discovery_identity_exists(state, observation_id):
        raise IntegrityError("source observation identity collision")
    batch = payload.get("batch")
    dedup_keys = payload.get("normalized_dedup_keys")
    source_refs = batch.get("raw_source_refs") if isinstance(batch, dict) else None
    registered_source_valid = True
    if isinstance(batch, dict) and batch.get("schema_version") == "2.0.0":
        registered_source_valid = False
        if isinstance(source_refs, list) and len(source_refs) == 1 and isinstance(source_refs[0], Mapping):
            source_ref = source_refs[0]
            artefact = state["artefact_streams"].get(source_ref.get("artefact_id"))
            if isinstance(artefact, Mapping):
                manifest = artefact.get("manifest")
                registered_source_valid = bool(
                    isinstance(manifest, Mapping)
                    and manifest.get("artefact_type") == "spec_source_observation"
                    and manifest.get("artefact_schema_id") == "ars://portfolio/spec-source-observation"
                    and manifest.get("artefact_schema_version") == "1.0.0"
                    and source_ref.get("content_hash") == artefact.get("content_sha256")
                    and source_ref.get("registration_event_id") == artefact.get("registration_event_id")
                    and source_ref.get("registration_event_hash") == artefact.get("registration_event_hash")
                    and source_ref.get("registration_global_position") == artefact.get("registration_global_position")
                    and artefact.get("registration_global_position", 0) < event.get("global_position", 0)
                )
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
        or not registered_source_valid
    ):
        raise IntegrityError("invalid Scout observation event")
    members = transaction_events.get(event.get("transaction_id"), ())
    candidates = [member for member in members if member.get("event_type") == "CandidateRegistered"]
    reconstructed_blueprints = []
    for candidate_event in candidates:
        candidate_payload = candidate_event.get("payload")
        if not isinstance(candidate_payload, Mapping):
            raise IntegrityError("Scout transaction shape mismatch")
        candidate_id = candidate_payload.get("candidate_id")
        if isinstance(candidate_id, str) and (
            candidate_id == observation_id or aggregate_identity_exists(candidate_id)
        ):
            raise IntegrityError("Candidate identity collision")
        reconstructed_blueprints.append(
            {
                key: deepcopy(value)
                for key, value in candidate_payload.items()
                if key not in {"owner_row_id", "source_observation_multiset_hash"}
            }
        )
    reconstructed_command = {
        "row_id": "OR-029",
        "observation_id": observation_id,
        "batch": deepcopy(batch),
        "batch_sha256": required_string("content_sha256"),
        "candidate_blueprints": reconstructed_blueprints,
    }
    if (
        len(members) != len(candidates) + 1
        or members[0].get("event_type") != "ScoutObservationIngested"
        or event.get("stream_id") != observation_id
        or not candidates
        or any(
            candidate_event.get("command_type") != "IngestScoutObservationBatch"
            or candidate_event.get("payload", {}).get("owner_row_id") != "OR-029"
            for candidate_event in candidates
        )
        or payload.get("candidate_blueprints_sha256") != sha256_hex(canonical_bytes(reconstructed_blueprints))
        or sha256_hex(canonical_bytes(reconstructed_command)) != event.get("command_payload_hash")
    ):
        raise IntegrityError("Scout transaction shape mismatch")
    state["source_observations"][observation_id] = {
        **deepcopy(payload),
        "global_position": event["global_position"],
        "version": event["stream_version"],
    }


def reduce_candidate_registered(scope: EventScope) -> None:
    """Reduce CandidateRegistered."""

    state = scope.state
    payload = scope.payload
    event = scope.event
    transaction_events = scope.transaction_events

    if state["catalogue"] is None:
        raise IntegrityError("Candidate event predates W11 genesis")
    candidate_id = payload.get("candidate_id")
    observations = payload.get("source_observation_refs")
    expected_owner_row = {
        "RegisterCandidate": "OR-001",
        "IngestScoutObservationBatch": "OR-029",
    }.get(event.get("command_type"))
    if event.get("command_type") == "RegisterCandidate":
        members = transaction_events.get(event.get("transaction_id"), ())
        command_payload = {
            key: deepcopy(payload.get(key))
            for key in ("candidate_id", "revision", "content_sha256", "source_observation_refs", "title")
        }
        if (
            len(members) != 1
            or members[0].get("event_type") != "CandidateRegistered"
            or members[0].get("stream_id") != payload.get("candidate_id")
        ):
            raise IntegrityError("RegisterCandidate transaction shape mismatch")
        if sha256_hex(canonical_bytes(command_payload)) != event.get("command_payload_hash"):
            raise IntegrityError("RegisterCandidate command digest mismatch")
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


def reduce_candidate_superseded(scope: EventScope) -> None:
    """Reduce CandidateSuperseded."""

    payload = scope.payload
    state = scope.state
    event = scope.event
    transaction = scope.transaction_events.get(event.get("transaction_id"), ())

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
    command_payload = {
        "row_id": "OR-002",
        "predecessor_ref": predecessor_ref,
        "replacement_ref": replacement_ref,
        "lineage_reason": payload.get("lineage_reason"),
    }
    if (
        len(transaction) != 1
        or transaction[0].get("event_id") != event.get("event_id")
        or event.get("command_payload_hash") != sha256_hex(canonical_bytes(command_payload))
    ):
        raise IntegrityError("Candidate supersession transaction mismatch")
    if (
        event.get("command_type") != "SupersedeDiscoveryRecord"
        or event.get("stream_id") != predecessor_id
        or payload.get("owner_row_id") != "OR-002"
        or predecessor_id == replacement_id
        or predecessor_ref != _candidate_ref(predecessor)
        or replacement_ref != _candidate_ref(replacement)
        or predecessor.get("status") == "superseded"
        or replacement.get("status") == "superseded"
        or _candidate_replacement_is_used(state["candidates"], replacement_id)
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
