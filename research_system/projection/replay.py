from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

from research_system.authority import SCOPED_AUTHORITY_ADMISSION_VERSION
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import (
    reduce_scope,
    reduce_task,
    validate_scope_lifecycle_event,
    validate_task_lifecycle_event,
)
from research_system.command.lifecycle import validate_exact_lifecycle_envelope
from research_system.command.t2 import apply_t2_event
from research_system.errors import IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry

_ALLOWED_DISPOSITIONS = frozenset(
    {
        "accepted",
        "partial_accepted",
        "deferred",
        "superseded",
        "removed_by_amendment",
        "cancelled",
        "rejected",
    }
)


def _validate_active_lifecycle_binding(
    event: dict[str, Any],
    schema_registry: SchemaRegistry | None,
) -> None:
    try:
        command_type = validate_exact_lifecycle_envelope(event)
    except (TypeError, ValueError) as exc:
        raise IntegrityError("exact lifecycle event provenance mismatch") from exc
    if command_type is None:
        return
    if schema_registry is None:
        raise IntegrityError("exact lifecycle schema registry unavailable")
    command_binding = schema_registry.command_binding(command_type)
    event_binding = schema_registry.event_binding(
        event["event_type"],
        command_type,
    )
    if (
        command_binding is None
        or event_binding is None
        or (
            command_binding.schema_id,
            command_binding.schema_version,
        )
        != (
            event["command_schema_id"],
            event["command_schema_version"],
        )
        or (
            event_binding.schema_id,
            event_binding.schema_version,
        )
        != (
            event["schema_id"],
            event["schema_version"],
        )
    ):
        raise IntegrityError("exact lifecycle active binding mismatch")
    try:
        command_identity = schema_registry.resolve_identity(
            command_binding.schema_id,
            command_binding.schema_version,
        )
    except SchemaError as exc:
        raise IntegrityError("exact lifecycle command binding is unresolved") from exc
    if event["command_schema_sha256"] != command_identity.sha256:
        raise IntegrityError("exact lifecycle command schema hash mismatch")


def _validate_recorded_event_schema(
    event: dict[str, Any],
    schema_registry: SchemaRegistry,
) -> None:
    recorded_schema = str(event.get("schema_id", ""))
    recorded_version = str(event.get("schema_version", ""))
    if recorded_schema == "ars://core/event":
        return
    event_binding = schema_registry.event_binding(
        str(event.get("event_type", "")),
        str(event.get("command_type", "")),
    )
    if event_binding is not None:
        if (recorded_schema, recorded_version) != (
            event_binding.schema_id,
            event_binding.schema_version,
        ):
            raise SchemaError(
                f"active event binding mismatch: {event_binding.schema_id} version {event_binding.schema_version}"
            )
        schema_registry.validate_active(
            event_binding.schema_id,
            event,
            schema_version=event_binding.schema_version,
        )
        return
    payload_schema = f"{recorded_schema}/payload"
    if schema_registry.requires_command_provenance:
        if schema_registry.contains(payload_schema):
            schema_registry.validate(payload_schema, event.get("payload"))
            return
        raise SchemaError(f"inactive event schema: {recorded_schema} version {recorded_version}")
    if schema_registry.contains(recorded_schema):
        schema_registry.validate(
            recorded_schema,
            event,
            schema_version=recorded_version,
        )
    elif schema_registry.contains(payload_schema):
        schema_registry.validate(payload_schema, event.get("payload"))


def _validate_scope_completion(payload: dict[str, Any]) -> None:
    reference = payload.get("scope_definition_ref")
    if (
        not isinstance(reference, dict)
        or not reference.get("object_id")
        or not isinstance(reference.get("revision"), int)
        or reference["revision"] < 1
    ):
        raise IntegrityError("scope completion requires an exact definition revision")
    required = payload.get("required_member_ids")
    dispositions = payload.get("member_dispositions")
    if not isinstance(required, list) or len(required) != len(set(required)):
        raise IntegrityError("scope completion has invalid required members")
    if not isinstance(dispositions, dict):
        raise IntegrityError("scope completion requires member dispositions")
    missing = sorted(set(required).difference(dispositions))
    if missing:
        raise IntegrityError(f"missing dispositions: {', '.join(missing)}")
    extra = sorted(set(dispositions).difference(required))
    if extra:
        raise IntegrityError(f"unexpected dispositions: {', '.join(extra)}")
    invalid = sorted(member for member, disposition in dispositions.items() if disposition not in _ALLOWED_DISPOSITIONS)
    if invalid:
        raise IntegrityError(f"invalid dispositions: {', '.join(invalid)}")


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(state)
    streams = updated.setdefault("streams", {})
    stream_id = event["stream_id"]
    event_type = event["event_type"]
    if str(event.get("schema_id", "")).startswith("ars://wp6-2/t2/event/"):
        return apply_t2_event(updated, event)
    if event_type == "AuthorityRootInitialized":
        payload = event["payload"]
        if set(payload) != {
            "bootstrap_manifest_sha256",
            "authorizing_grant_id",
            "authorizing_grant_sha256",
            "activated_grant_id",
            "activated_grant_sha256",
        }:
            raise IntegrityError("authority root payload fields must be exact")
        if (
            event.get("global_position") != 1
            or event.get("transaction_index") != 1
            or event.get("transaction_count") != 2
        ):
            raise IntegrityError("authority root must be genesis index 1/2")
        bootstrap_hash = payload.get("bootstrap_manifest_sha256")
        bootstrap_key = f"authority-bootstrap:{bootstrap_hash}"
        if (
            event.get("schema_id") != "ars://core/event/AuthorityRootInitialized"
            or event.get("command_type") != "InitializeAuthorityRoot"
            or event.get("authority_grant_id") != stream_id
            or not isinstance(event.get("command_id"), str)
            or not isinstance(event.get("actor_id"), str)
            or event.get("command_payload_hash") != bootstrap_hash
            or event.get("idempotency_key") != bootstrap_key
            or event.get("correlation_id") != bootstrap_key
            or event.get("causation_id") is not None
        ):
            raise IntegrityError("authority genesis envelope binding mismatch")
        if payload.get("activated_grant_id") != stream_id or payload.get("authorizing_grant_id") != stream_id:
            raise IntegrityError("authority root stream binding mismatch")
        if payload.get("activated_grant_sha256") != payload.get("authorizing_grant_sha256"):
            raise IntegrityError("authority root hash binding mismatch")
        grants = updated.setdefault("authority_grants", {})
        if grants:
            raise IntegrityError("authority root already initialized")
        grants[stream_id] = {
            "authority_grant_id": stream_id,
            "authority_grant_sha256": payload["activated_grant_sha256"],
            "status": "active",
            "activation_event_id": event["event_id"],
            "activation_position": event["global_position"],
            "revocation_event_id": None,
            "revocation_position": None,
        }
        updated["authority_root_id"] = stream_id
        updated["authority_owner_actor_id"] = event["actor_id"]
        updated["bootstrap_manifest_sha256"] = payload["bootstrap_manifest_sha256"]
        updated["_authority_genesis_envelope"] = {
            field: event.get(field)
            for field in (
                "command_id",
                "command_type",
                "actor_id",
                "authority_grant_id",
                "idempotency_key",
                "command_payload_hash",
                "correlation_id",
                "causation_id",
            )
        }
    elif event_type == "AuthorityGrantActivated":
        payload = event["payload"]
        grants = updated.setdefault("authority_grants", {})
        root_id = updated.get("authority_root_id")
        if event.get("command_type") == "InitializeAuthorityRoot":
            if set(payload) != {
                "authorizing_grant_id",
                "authorizing_grant_sha256",
                "activated_grant_id",
                "activated_grant_sha256",
            }:
                raise IntegrityError("authority activation payload fields must be exact")
            if (
                event.get("global_position") != 2
                or event.get("transaction_index") != 2
                or event.get("transaction_count") != 2
            ):
                raise IntegrityError("publication grant must be genesis index 2/2")
            genesis_envelope = updated.pop("_authority_genesis_envelope", None)
            if (
                event.get("schema_id") != "ars://core/event/AuthorityGrantActivated"
                or not isinstance(genesis_envelope, dict)
                or any(event.get(field) != expected for field, expected in genesis_envelope.items())
            ):
                raise IntegrityError("authority genesis envelope binding mismatch")
            if payload.get("authorizing_grant_id") != root_id or payload.get("authorizing_grant_sha256") != grants.get(
                root_id, {}
            ).get("authority_grant_sha256"):
                raise IntegrityError("publication activation authority mismatch")
            if payload.get("activated_grant_id") != stream_id or stream_id in grants:
                raise IntegrityError("publication activation stream mismatch or duplicate")
            grants[stream_id] = {
                "authority_grant_id": stream_id,
                "authority_grant_sha256": payload["activated_grant_sha256"],
                "status": "active",
                "activation_event_id": event["event_id"],
                "activation_position": event["global_position"],
                "revocation_event_id": None,
                "revocation_position": None,
            }
        elif event.get("command_type") == "ActivateAuthorityGrant":
            expected_fields = {
                "authority_admission_version",
                "project_id",
                "bootstrap_manifest_sha256",
                "root_grant_id",
                "root_grant_sha256",
                "administration_decision_id",
                "administration_decision_sha256",
                "activated_grant_id",
                "activated_grant_sha256",
                "activated_grant_schema_id",
                "activated_grant_schema_version",
                "activated_grant_schema_sha256",
                "subject_scope",
                "effective_at",
                "expires_at",
            }
            if set(payload) != expected_fields:
                raise IntegrityError("scoped authority activation fields must be exact")
            root_record = grants.get(root_id, {})
            decisions = updated.setdefault("authority_administration_decisions", {})
            decision_id = payload.get("administration_decision_id")
            if (
                event.get("schema_id") != "ars://core/event/ScopedAuthorityGrantActivated"
                or event.get("transaction_index") != 1
                or event.get("transaction_count") != 1
                or event.get("authority_grant_id") != root_id
                or event.get("actor_id") != updated.get("authority_owner_actor_id")
                or payload.get("authority_admission_version") != SCOPED_AUTHORITY_ADMISSION_VERSION
                or payload.get("project_id") != updated.get("project_id")
                or payload.get("bootstrap_manifest_sha256") != updated.get("bootstrap_manifest_sha256")
                or payload.get("root_grant_id") != root_id
                or payload.get("root_grant_sha256") != root_record.get("authority_grant_sha256")
                or root_record.get("status") != "active"
                or payload.get("activated_grant_id") != stream_id
                or stream_id in grants
                or payload.get("activated_grant_schema_id") != "ars://core/scoped-authority-grant"
                or payload.get("activated_grant_schema_version") != "2.0.0"
                or not isinstance(decision_id, str)
                or decision_id in decisions
            ):
                raise IntegrityError("scoped authority activation binding mismatch")
            grants[stream_id] = {
                "authority_grant_id": stream_id,
                "authority_grant_sha256": payload["activated_grant_sha256"],
                "schema_id": payload["activated_grant_schema_id"],
                "schema_version": payload["activated_grant_schema_version"],
                "schema_sha256": payload["activated_grant_schema_sha256"],
                "subject_scope": payload["subject_scope"],
                "effective_at": payload["effective_at"],
                "expires_at": payload["expires_at"],
                "administration_decision_id": decision_id,
                "administration_decision_sha256": payload["administration_decision_sha256"],
                "status": "active",
                "activation_event_id": event["event_id"],
                "activation_position": event["global_position"],
                "revocation_event_id": None,
                "revocation_position": None,
            }
            decisions[decision_id] = {
                "action": "activate_authority_grant",
                "target_grant_id": stream_id,
                "administration_decision_sha256": payload["administration_decision_sha256"],
                "event_id": event["event_id"],
                "position": event["global_position"],
                "recorded_at": event["recorded_at"],
            }
        else:
            raise IntegrityError("unbound authority activation producer")
    elif event_type == "AuthorityGrantRevoked":
        payload = event["payload"]
        grants = updated.setdefault("authority_grants", {})
        current = grants.get(stream_id)
        root_id = updated.get("authority_root_id")
        if event.get("command_type") == "RevokeAuthorityGrant":
            if set(payload) != {
                "project_id",
                "target_grant_id",
                "target_grant_sha256",
                "authorizing_grant_id",
                "authorizing_grant_sha256",
                "reason",
            }:
                raise IntegrityError("authority revocation payload fields must be exact")
            if event.get("schema_id") != "ars://core/event":
                raise IntegrityError("legacy authority revocation schema mismatch")
            if payload.get("project_id") != updated.get("project_id"):
                raise IntegrityError("authority revocation project mismatch")
            if current is None or current["status"] != "active":
                raise IntegrityError("authority revocation requires active grant")
            if (
                payload.get("target_grant_id") != stream_id
                or payload.get("target_grant_sha256") != current["authority_grant_sha256"]
            ):
                raise IntegrityError("authority revocation target mismatch")
            if payload.get("authorizing_grant_id") != root_id or payload.get("authorizing_grant_sha256") != grants.get(
                root_id, {}
            ).get("authority_grant_sha256"):
                raise IntegrityError("authority revocation root mismatch")
        elif event.get("command_type") == "RevokeIssuedAuthorityGrant":
            expected_fields = {
                "authority_admission_version",
                "project_id",
                "bootstrap_manifest_sha256",
                "root_grant_id",
                "root_grant_sha256",
                "administration_decision_id",
                "administration_decision_sha256",
                "target_grant_id",
                "target_grant_sha256",
                "target_grant_schema_id",
                "target_grant_schema_version",
                "target_grant_schema_sha256",
                "reason",
            }
            decisions = updated.setdefault("authority_administration_decisions", {})
            decision_id = payload.get("administration_decision_id")
            if (
                set(payload) != expected_fields
                or event.get("schema_id") != "ars://core/event/IssuedAuthorityGrantRevoked"
                or event.get("transaction_index") != 1
                or event.get("transaction_count") != 1
                or event.get("authority_grant_id") != root_id
                or event.get("actor_id") != updated.get("authority_owner_actor_id")
                or payload.get("authority_admission_version") != SCOPED_AUTHORITY_ADMISSION_VERSION
                or payload.get("project_id") != updated.get("project_id")
                or payload.get("bootstrap_manifest_sha256") != updated.get("bootstrap_manifest_sha256")
                or payload.get("root_grant_id") != root_id
                or payload.get("root_grant_sha256") != grants.get(root_id, {}).get("authority_grant_sha256")
                or current is None
                or current.get("status") != "active"
                or current.get("schema_id") != "ars://core/scoped-authority-grant"
                or payload.get("target_grant_id") != stream_id
                or payload.get("target_grant_sha256") != current.get("authority_grant_sha256")
                or payload.get("target_grant_schema_id") != current.get("schema_id")
                or payload.get("target_grant_schema_version") != current.get("schema_version")
                or payload.get("target_grant_schema_sha256") != current.get("schema_sha256")
                or not isinstance(decision_id, str)
                or decision_id in decisions
            ):
                raise IntegrityError("issued authority revocation binding mismatch")
            decisions[decision_id] = {
                "action": "revoke_issued_authority_grant",
                "target_grant_id": stream_id,
                "administration_decision_sha256": payload["administration_decision_sha256"],
                "event_id": event["event_id"],
                "position": event["global_position"],
                "recorded_at": event["recorded_at"],
            }
        else:
            raise IntegrityError("unbound authority revocation producer")
        grants[stream_id] = {
            **current,
            "status": "revoked",
            "revocation_event_id": event["event_id"],
            "revocation_position": event["global_position"],
            **(
                {
                    "revocation_administration_decision_id": decision_id,
                    "revocation_administration_decision_sha256": payload["administration_decision_sha256"],
                }
                if event.get("command_type") == "RevokeIssuedAuthorityGrant"
                else {}
            ),
        }
    elif event_type in {"TaskCreated", "TaskAmended", "TaskSuperseded"}:
        validate_task_lifecycle_event(streams, event)
        streams[stream_id] = reduce_task(streams.get(stream_id, {}), event)
    elif event_type in {
        "ScopeDefinitionCreated",
        "ScopeDefinitionAmended",
        "ScopeDefinitionSuperseded",
    }:
        validate_scope_lifecycle_event(streams, event)
        streams[stream_id] = reduce_scope(streams.get(stream_id, {}), event)
    elif event_type == "DispatchClaimed":
        current = streams.get(
            stream_id,
            {
                "dispatch_id": stream_id,
                "status": "unclaimed",
                "active_attempt_ids": [],
                "version": 0,
            },
        )
        if current["status"] != "unclaimed":
            raise IntegrityError("dispatch already has an active attempt")
        streams[stream_id] = {
            **current,
            "status": "claimed",
            "active_attempt_ids": [event["payload"]["attempt_id"]],
            "version": current["version"] + 1,
        }
    elif event_type == "ScopeCompleted":
        _validate_scope_completion(event["payload"])
        streams[stream_id] = {
            "scope_id": stream_id,
            "status": "completed",
            "scope_definition_ref": event["payload"]["scope_definition_ref"],
            "member_dispositions": dict(event["payload"]["member_dispositions"]),
            "version": event["stream_version"],
        }
    elif event_type in {"EvidenceDeletionVerified", "EvidenceDeletionPending"}:
        payload = event["payload"]
        expected_status = "verified" if event_type == "EvidenceDeletionVerified" else "deletion_pending"
        if payload.get("status") != expected_status:
            raise IntegrityError("deletion event status mismatch")
        required = {
            "evidence_store_id",
            "evidence_id",
            "evidence_hash",
            "retention_rule_id",
            "policy_revision",
            "registry_hash",
            "manifest_hash",
        }
        missing = sorted(required.difference(payload))
        if missing:
            raise IntegrityError("deletion event missing fields: " + ", ".join(missing))
        evidence_store_id = payload["evidence_store_id"]
        streams[evidence_store_id] = {
            "evidence_store_id": evidence_store_id,
            "status": ("expired_deleted" if expected_status == "verified" else "deletion_pending"),
            "evidence_id": payload["evidence_id"],
            "evidence_hash": payload["evidence_hash"],
            "retention_rule_id": payload["retention_rule_id"],
            "policy_revision": payload["policy_revision"],
            "registry_hash": payload["registry_hash"],
            "deletion_manifest_hash": payload["manifest_hash"],
            "r2_intake_blocked": expected_status != "verified",
            "version": event["stream_version"],
        }
    elif event_type == "ReleaseGateDecisionPublished":
        payload = event["payload"]
        expected_fields = {
            "release_decision",
            "source_decision_sha256",
            "evaluation_runs_manifest_ref",
            "evaluation_runs_manifest_sha256",
            "control_binding_ref",
            "control_binding_sha256",
            "publication_authority_grant_id",
            "publication_authority_sha256",
            "gate5_authorized",
            "candidate_status",
        }
        if set(payload) != expected_fields:
            raise IntegrityError("release publication payload fields must be exact")
        decision = payload.get("release_decision")
        stream_id = event.get("stream_id")
        publication_grant_id = payload.get("publication_authority_grant_id")
        publication_grant = updated.get("authority_grants", {}).get(publication_grant_id)
        if (
            not isinstance(decision, dict)
            or not isinstance(stream_id, str)
            or not stream_id.startswith("rgd_")
            or decision.get("release_gate_decision_id") != stream_id
            or decision.get("canonical_event_ref") != event.get("event_id")
            or decision.get("decision") != "blocked"
            or payload.get("gate5_authorized") is not False
            or payload.get("candidate_status") != "blocked"
            or event.get("authority_grant_id") != publication_grant_id
            or not isinstance(publication_grant, dict)
            or publication_grant.get("status") != "active"
            or publication_grant.get("authority_grant_sha256") != payload.get("publication_authority_sha256")
        ):
            raise IntegrityError("release publication identity or disposition mismatch")
        source = deepcopy(decision)
        source["canonical_event_ref"] = "unpublished:p0"
        if payload.get("source_decision_sha256") != sha256_hex(canonical_bytes(source)):
            raise IntegrityError("release publication source hash mismatch")
        releases = updated.setdefault("release_decisions", {})
        if stream_id in releases:
            raise IntegrityError("release decision is already projected")
        projection = {
            "release_decision_id": stream_id,
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
            "event_position": event["global_position"],
            "project_id": event["project_id"],
            "release_decision": decision,
            "source_decision_sha256": payload["source_decision_sha256"],
            "evaluation_runs_manifest_ref": payload["evaluation_runs_manifest_ref"],
            "evaluation_runs_manifest_sha256": payload["evaluation_runs_manifest_sha256"],
            "control_binding_ref": payload["control_binding_ref"],
            "control_binding_sha256": payload["control_binding_sha256"],
            "publication_authority_grant_id": payload["publication_authority_grant_id"],
            "publication_authority_sha256": payload["publication_authority_sha256"],
            "publication_authority_activation_position": publication_grant["activation_position"],
            "gate5_authorized": False,
            "candidate_status": "blocked",
            "version": event["stream_version"],
        }
        releases[stream_id] = projection
        streams[stream_id] = projection
    else:
        raise IntegrityError(f"unsupported event type: {event_type}")
    return updated


def _major(event: dict[str, Any]) -> int:
    try:
        return int(str(event["schema_version"]).split(".", maxsplit=1)[0])
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError("invalid event schema version") from exc


def _verify_event_hash(event: dict[str, Any]) -> bool:
    unsigned = dict(event)
    recorded = unsigned.pop("event_hash", None)
    return recorded == sha256_hex(canonical_bytes(unsigned))


def replay(
    events: Iterable[dict[str, Any]],
    supported_major: int = 1,
    schema_registry: SchemaRegistry | None = None,
    legacy_command_provenance_through_position: int = 0,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if legacy_command_provenance_through_position < 0:
        raise ValueError("legacy command provenance position must be non-negative")
    state: dict[str, Any] = {
        "streams": {},
        "last_position": 0,
        "last_hash": "0" * 64,
        "project_id": None,
    }
    stream_versions: dict[str, int] = {}
    transaction_id: str | None = None
    transaction_count = 0
    transaction_seen = 0
    transaction_zero_based = False
    for source in events:
        event = deepcopy(source)
        position = event.get("global_position")
        release_event = event.get("event_type") == "ReleaseGateDecisionPublished"
        t2_event = str(event.get("schema_id", "")).startswith("ars://wp6-2/t2/event/")
        if release_event and schema_registry is None:
            raise IntegrityError("release event schema validator unavailable")
        provenance_fields = {
            "command_schema_id",
            "command_schema_version",
            "command_schema_sha256",
        }
        recorded_provenance = provenance_fields.intersection(event)
        if recorded_provenance and recorded_provenance != provenance_fields:
            raise IntegrityError(f"incomplete command schema identity at {position}")
        if (
            schema_registry is not None
            and not recorded_provenance
            and (not isinstance(position, int) or position > legacy_command_provenance_through_position)
        ):
            raise IntegrityError(f"missing command schema identity at {position}")
        if schema_registry is not None:
            if recorded_provenance:
                try:
                    schema_registry.resolve_identity(
                        event["command_schema_id"],
                        event["command_schema_version"],
                        expected_sha256=event["command_schema_sha256"],
                    )
                except SchemaError as exc:
                    raise IntegrityError(f"command schema identity mismatch at {position}") from exc
            try:
                if t2_event:
                    schema_registry.validate(
                        event["schema_id"],
                        event,
                        schema_version=str(event.get("schema_version", "")),
                    )
                elif release_event:
                    schema_registry.validate(
                        "ars://core/event/ReleaseGateDecisionPublished",
                        event,
                        schema_version=str(event.get("schema_version", "")),
                    )
                else:
                    schema_registry.validate("ars://core/event", event)
                    _validate_recorded_event_schema(event, schema_registry)
            except SchemaError as exc:
                raise IntegrityError(f"event schema validation failed at {position}") from exc
        if _major(event) != supported_major:
            raise IntegrityError(f"unsupported major at {position}")
        schema_id = event.get("schema_id")
        if not isinstance(schema_id, str) or not (
            schema_id == "ars://core/event"
            or schema_id.startswith("ars://core/event/")
            or schema_id.startswith("ars://wp6-2/t2/event/")
        ):
            raise IntegrityError(f"unknown event schema at {position}")
        if position != state["last_position"] + 1:
            raise IntegrityError("event position gap or overlap")
        if event.get("previous_event_hash") != state["last_hash"]:
            raise IntegrityError("event hash-chain mismatch")
        if not _verify_event_hash(event):
            raise IntegrityError(f"event hash mismatch at {position}")
        _validate_active_lifecycle_binding(event, schema_registry)
        project_id = event.get("project_id")
        if state["project_id"] is None:
            state["project_id"] = project_id
        elif project_id != state["project_id"]:
            raise IntegrityError("event project identity mismatch")
        stream_id = event.get("stream_id")
        expected_stream_version = stream_versions.get(stream_id, 0) + 1
        if event.get("stream_version") != expected_stream_version:
            raise IntegrityError("stream version gap or overlap")
        stream_versions[stream_id] = expected_stream_version
        current_transaction = event.get("transaction_id")
        if current_transaction != transaction_id:
            if transaction_id is not None and transaction_seen != transaction_count:
                raise IntegrityError("incomplete event transaction")
            transaction_id = current_transaction
            transaction_count = event.get("transaction_count")
            transaction_seen = 0
            transaction_zero_based = t2_event
        if event.get("transaction_count") != transaction_count:
            raise IntegrityError("event transaction count mismatch")
        if t2_event != transaction_zero_based:
            raise IntegrityError("mixed transaction index convention")
        expected_index = transaction_seen if transaction_zero_based else transaction_seen + 1
        if event.get("transaction_index") != expected_index:
            raise IntegrityError("event transaction index gap or overlap")
        transaction_seen += 1
        state = apply_event(state, event)
        state["last_position"] = position
        state["last_hash"] = event["event_hash"]
    if transaction_id is not None and transaction_seen != transaction_count:
        raise IntegrityError("incomplete event transaction")
    if state.get("authority_administration_decisions"):
        if authority_state_validator is None:
            raise IntegrityError("authority administration decision validator unavailable")
        authority_state_validator(state)
    return state


def rebuild_projection(
    events: Iterable[dict[str, Any]],
    output: Path,
    schema_registry: SchemaRegistry | None = None,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    state = replay(
        events,
        schema_registry=schema_registry,
        authority_state_validator=authority_state_validator,
    )
    data = canonical_bytes(state) + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    return state
