from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

from research_system.authority import (
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    SCOPED_AUTHORITY_ADMISSION_VERSION,
    SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
    SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
    LEGACY_SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import (
    reduce_attempt,
    reduce_artefact,
    reduce_backup,
    reduce_restore_verification,
    reduce_blocker,
    reduce_checkpoint,
    reduce_dispatch,
    reduce_decision,
    reduce_lease,
    reduce_message,
    reduce_operation,
    reduce_recovery,
    reduce_review,
    reduce_resource,
    reduce_rule_evaluation,
    reduce_scope,
    reduce_task,
    validate_scope_lifecycle_event,
    validate_task_lifecycle_event,
)
from research_system.command.lifecycle import validate_exact_lifecycle_envelope
from research_system.command.t2 import apply_t2_event
from research_system.discovery.commands import discovery_resolve_transaction_ids, is_discovery_projection_event
from research_system.errors import IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry

_SCOPED_ACTIVATION_SCHEMA_VERSIONS = {
    ("1.0.0", "1.0.0"): LEGACY_SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
    ("1.1.0", "1.1.0"): SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
}

_ISSUED_REVOCATION_SCHEMA_VERSIONS = {
    ("1.0.0", "1.0.0"): LEGACY_SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
    ("1.0.0", "1.1.0"): SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
}


def _scoped_grant_schema_for_command(
    command_type: str,
    *,
    command_schema_version: str | None = None,
    event_schema_version: str | None = None,
) -> tuple[str, str, str]:
    if command_type == "ActivateExternalAssuranceRecordGrant":
        return (
            EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
            EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
            "ars://core/event/ExternalAssuranceRecordGrantActivated",
        )
    if command_schema_version is None or event_schema_version is None:
        grant_version = SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION
    else:
        try:
            grant_version = _SCOPED_ACTIVATION_SCHEMA_VERSIONS[(command_schema_version, event_schema_version)]
        except KeyError as exc:
            raise IntegrityError("unsupported scoped authority activation schema versions") from exc
    return (
        SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
        grant_version,
        "ars://core/event/ScopedAuthorityGrantActivated",
    )


def _is_historical_scoped_activation(event: dict[str, Any]) -> bool:
    return (
        event.get("command_type") == "ActivateAuthorityGrant"
        and event.get("command_schema_id") == "ars://core/command/ActivateAuthorityGrant"
        and event.get("schema_id") == "ars://core/event/ScopedAuthorityGrantActivated"
        and (event.get("command_schema_version"), event.get("schema_version")) == ("1.0.0", "1.0.0")
    )


def _is_historical_issued_revocation(event: dict[str, Any]) -> bool:
    return (
        event.get("command_type") == "RevokeIssuedAuthorityGrant"
        and event.get("command_schema_id") == "ars://core/command/RevokeIssuedAuthorityGrant"
        and event.get("command_schema_version") == "1.0.0"
        and event.get("schema_id") == "ars://core/event/IssuedAuthorityGrantRevoked"
        and event.get("schema_version") == "1.0.0"
    )


def _issued_revocation_schema_for_command(
    command_type: str,
    *,
    command_schema_version: str | None = None,
    event_schema_version: str | None = None,
) -> tuple[str, str, str]:
    if command_type == "RevokeExternalAssuranceRecordGrant":
        return (
            EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
            EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
            "ars://core/event/ExternalAssuranceRecordGrantRevoked",
        )
    if command_type == "RevokeIssuedAuthorityGrant":
        if command_schema_version is None or event_schema_version is None:
            grant_version = SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION
        else:
            try:
                grant_version = _ISSUED_REVOCATION_SCHEMA_VERSIONS[(command_schema_version, event_schema_version)]
            except KeyError as exc:
                raise IntegrityError("unsupported issued authority revocation schema versions") from exc
        return (
            SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
            grant_version,
            "ars://core/event/IssuedAuthorityGrantRevoked",
        )
    raise ValueError(f"unsupported issued authority revocation command: {command_type}")


def _reject_legacy_revocation_of_typed_grant(
    current: dict[str, Any],
) -> None:
    if "schema_id" not in current and "schema_version" not in current:
        return
    if (
        current.get("schema_id") == SCOPED_AUTHORITY_GRANT_SCHEMA_ID
        and current.get("schema_version") == SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION
    ):
        raise IntegrityError("legacy authority revocation cannot target scoped grant")
    raise IntegrityError("legacy authority revocation cannot target typed grant with unknown schema marker")


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
    if _is_historical_scoped_activation(event):
        try:
            command_identity = schema_registry.resolve_identity(
                "ars://core/command/ActivateAuthorityGrant",
                "1.0.0",
            )
        except SchemaError as exc:
            raise IntegrityError("historical authority command binding is unresolved") from exc
        if event["command_schema_sha256"] != command_identity.sha256:
            raise IntegrityError("exact lifecycle command schema hash mismatch")
        return
    if _is_historical_issued_revocation(event):
        try:
            command_identity = schema_registry.resolve_identity(
                "ars://core/command/RevokeIssuedAuthorityGrant",
                "1.0.0",
            )
        except SchemaError as exc:
            raise IntegrityError("historical authority command binding is unresolved") from exc
        if event["command_schema_sha256"] != command_identity.sha256:
            raise IntegrityError("exact lifecycle command schema hash mismatch")
        return
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
    if _is_historical_scoped_activation(event):
        schema_registry.validate(
            "ars://core/event/ScopedAuthorityGrantActivated",
            event,
            schema_version="1.0.0",
        )
        return
    if _is_historical_issued_revocation(event):
        schema_registry.validate(
            "ars://core/event/IssuedAuthorityGrantRevoked",
            event,
            schema_version="1.0.0",
        )
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


def _validate_claim_dispatch_transaction(
    events: tuple[dict[str, Any], ...],
    schema_registry: SchemaRegistry | None,
) -> None:
    """Require ClaimDispatch's exact two-stream atomic transaction shape."""
    claim_events = [event for event in events if event.get("event_type") in {"DispatchClaimed", "TaskClaimStarted"}]
    if not claim_events:
        return
    if len(events) != 2 or [event.get("event_type") for event in events] != [
        "DispatchClaimed",
        "TaskClaimStarted",
    ]:
        raise IntegrityError("ClaimDispatch requires exact ordered Dispatch/Task event pair")
    if schema_registry is None:
        raise IntegrityError("ClaimDispatch schema registry unavailable")
    dispatch_event, task_event = events
    dispatch_payload = dispatch_event.get("payload")
    task_payload = task_event.get("payload")
    if not isinstance(dispatch_payload, dict) or not isinstance(task_payload, dict):
        raise IntegrityError("ClaimDispatch payloads must be mappings")
    expected_dispatch_stream_version = dispatch_payload.get("expected_dispatch_stream_version")
    expected_task_stream_version = dispatch_payload.get("expected_task_stream_version")
    expected_global_position = dispatch_payload.get("expected_global_position")
    if any(
        type(value) is not int
        for value in (
            expected_dispatch_stream_version,
            expected_task_stream_version,
            expected_global_position,
        )
    ):
        raise IntegrityError("ClaimDispatch expected positions must be integers")
    if (
        dispatch_event.get("command_type") != "ClaimDispatch"
        or task_event.get("command_type") != "ClaimDispatch"
        or dispatch_event.get("stream_id") != dispatch_payload.get("dispatch_id")
        or task_event.get("stream_id") != dispatch_payload.get("task_id")
        or task_payload
        != {
            "task_id": dispatch_payload.get("task_id"),
            "task_revision": dispatch_payload.get("task_revision"),
        }
        or dispatch_payload.get("declared_write_set") != ["dispatch", "task"]
        or dispatch_event.get("stream_version") != expected_dispatch_stream_version + 1
        or task_event.get("stream_version") != expected_task_stream_version + 1
        or dispatch_event.get("global_position") != expected_global_position + 1
        or dispatch_event.get("previous_event_hash") != dispatch_payload.get("expected_tail_hash")
    ):
        raise IntegrityError("ClaimDispatch stream, version, or tail binding mismatch")
    common_fields = {
        "transaction_id",
        "transaction_count",
        "command_id",
        "command_type",
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
        "command_payload_hash",
        "actor_id",
        "authority_grant_id",
        "idempotency_key",
        "correlation_id",
        "causation_id",
        "project_id",
    }
    if any(dispatch_event.get(field) != task_event.get(field) for field in common_fields):
        raise IntegrityError("ClaimDispatch events do not share one command provenance")
    command_binding = schema_registry.command_binding("ClaimDispatch")
    if command_binding is None:
        raise IntegrityError("ClaimDispatch command schema binding is unavailable")
    try:
        command_identity = schema_registry.resolve_identity(
            command_binding.schema_id,
            command_binding.schema_version,
        )
    except SchemaError as exc:
        raise IntegrityError("ClaimDispatch command schema binding is unresolved") from exc
    expected_command_identity = (
        command_identity.schema_id,
        command_identity.schema_version,
        command_identity.sha256,
    )
    if any(
        (
            event.get("command_schema_id"),
            event.get("command_schema_version"),
            event.get("command_schema_sha256"),
        )
        != expected_command_identity
        for event in events
    ):
        raise IntegrityError("ClaimDispatch command schema binding mismatch")
    dispatch_binding = schema_registry.event_binding("DispatchClaimed", "ClaimDispatch")
    task_binding = schema_registry.event_binding("TaskClaimStarted", "ClaimDispatch")
    if dispatch_binding is None or task_binding is None:
        raise IntegrityError("ClaimDispatch event schema bindings are unavailable")
    exact_pair = (dispatch_event.get("schema_id"), dispatch_event.get("schema_version")) == (
        dispatch_binding.schema_id,
        dispatch_binding.schema_version,
    ) and (task_event.get("schema_id"), task_event.get("schema_version")) == (
        task_binding.schema_id,
        task_binding.schema_version,
    )
    generic_pair = (
        dispatch_event.get("schema_id") == "ars://core/event" and task_event.get("schema_id") == "ars://core/event"
    )
    if not exact_pair and not generic_pair:
        raise IntegrityError("ClaimDispatch event schema representation mismatch")


def apply_event(
    state: dict[str, Any],
    event: dict[str, Any],
    *,
    discovery_projection_event: bool = False,
) -> dict[str, Any]:
    """Apply one validated event to a copied projection state.

    Args:
        state: Current projection state, which remains unmodified.
        event: Canonical event to reduce.
        discovery_projection_event: Whether Discovery owns the event's semantic
            reduction at the shared replay boundary.

    Returns:
        A deep-copied projection containing the event's durable effects.

    Raises:
        IntegrityError: If the event is unsupported or violates a projection
            invariant owned by its reducer.
    """

    updated = deepcopy(state)
    streams = updated.setdefault("streams", {})
    stream_id = event["stream_id"]
    event_type = event["event_type"]
    if str(event.get("schema_id", "")).startswith("ars://wp6-2/t2/event/"):
        return apply_t2_event(updated, event)
    if discovery_projection_event:
        # The shared-ledger envelope, schema, hash-chain, stream-version and
        # transaction checks are performed by _replay. Discovery semantics are
        # validated once by replay_discovery at that same generic boundary.
        return updated
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
    elif event_type == "OwnerAuthorityAdministrationDecisionPublished":
        payload = event["payload"]
        decision = payload.get("decision")
        grant = payload.get("proposed_grant")
        publications = updated.setdefault("owner_authority_decision_publications", {})
        decision_id = decision.get("record_id") if isinstance(decision, dict) else None
        if (
            event.get("command_type") != "PublishOwnerAuthorityAdministrationDecision"
            or event.get("schema_id") != "ars://core/event/OwnerAuthorityAdministrationDecisionPublished"
            or event.get("transaction_index") != 1
            or event.get("transaction_count") != 1
            or not isinstance(decision_id, str)
            or event.get("stream_id") != decision_id
            or decision_id in publications
            or not isinstance(grant, dict)
            or decision.get("target_grant_id") != grant.get("authority_grant_id")
            or decision.get("target_grant_sha256") != sha256_hex(canonical_bytes(grant))
            or event.get("actor_id") != updated.get("authority_owner_actor_id")
            or event.get("authority_grant_id") != updated.get("authority_root_id")
        ):
            raise IntegrityError("owner authority decision publication binding mismatch")
        publications[decision_id] = {
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "target_grant_id": grant["authority_grant_id"],
            "event_id": event["event_id"],
            "position": event["global_position"],
            "recorded_at": event["recorded_at"],
            "consumed": False,
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
        elif event.get("command_type") in {
            "ActivateAuthorityGrant",
            "ActivateExternalAssuranceRecordGrant",
        }:
            grant_schema_id, grant_schema_version, event_schema_id = _scoped_grant_schema_for_command(
                str(event.get("command_type")),
                command_schema_version=str(event.get("command_schema_version")),
                event_schema_version=str(event.get("schema_version")),
            )
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
                event.get("schema_id") != event_schema_id
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
                or payload.get("activated_grant_schema_id") != grant_schema_id
                or payload.get("activated_grant_schema_version") != grant_schema_version
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
            publications = updated.get("owner_authority_decision_publications", {})
            publication = publications.get(decision_id) if isinstance(publications, dict) else None
            if publication is not None:
                if (
                    publication.get("consumed") is not False
                    or publication.get("administration_decision_sha256") != payload["administration_decision_sha256"]
                    or publication.get("target_grant_id") != stream_id
                ):
                    raise IntegrityError("owner authority decision publication consumption mismatch")
                publication["consumed"] = True
                publication["consumption_event_id"] = event["event_id"]
                publication["consumption_position"] = event["global_position"]
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
            _reject_legacy_revocation_of_typed_grant(current)
            if (
                payload.get("target_grant_id") != stream_id
                or payload.get("target_grant_sha256") != current["authority_grant_sha256"]
            ):
                raise IntegrityError("authority revocation target mismatch")
            if payload.get("authorizing_grant_id") != root_id or payload.get("authorizing_grant_sha256") != grants.get(
                root_id, {}
            ).get("authority_grant_sha256"):
                raise IntegrityError("authority revocation root mismatch")
        elif event.get("command_type") in {
            "RevokeIssuedAuthorityGrant",
            "RevokeExternalAssuranceRecordGrant",
        }:
            grant_schema_id, grant_schema_version, event_schema_id = _issued_revocation_schema_for_command(
                event["command_type"],
                command_schema_version=str(event.get("command_schema_version", "")),
                event_schema_version=str(event.get("schema_version", "")),
            )
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
                or event.get("schema_id") != event_schema_id
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
                or current.get("schema_id") != grant_schema_id
                or current.get("schema_version") != grant_schema_version
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
                if event.get("command_type")
                in {
                    "RevokeIssuedAuthorityGrant",
                    "RevokeExternalAssuranceRecordGrant",
                }
                else {}
            ),
        }
    elif event_type in {
        "TaskCreated",
        "TaskAmended",
        "TaskSuperseded",
        "ReadinessRequested",
        "ReadinessApproved",
        "TaskClaimStarted",
        "TaskBlocked",
        "InputRequested",
        "TaskPaused",
        "TaskSubmittedForReview",
        "TaskResumed",
        "TaskCancelled",
        "TaskAccepted",
        "TaskRejected",
        "TaskReopened",
    } or (event_type == "PartialOutcomeRecorded" and event.get("command_type") == "ClosePartial"):
        validate_task_lifecycle_event(streams, event)
        streams[stream_id] = reduce_task(streams.get(stream_id, {}), event)
    elif event_type in {
        "ScopeDefinitionCreated",
        "ScopeDefinitionAmended",
        "ScopeDefinitionSuperseded",
        "ScopeCompleted",
    }:
        validate_scope_lifecycle_event(streams, event)
        streams[stream_id] = reduce_scope(streams.get(stream_id, {}), event)
    elif event_type in {
        "MessagePublished",
        "MessageDelivered",
        "MessageAcknowledged",
        "MessageDeliveryFailed",
    }:
        try:
            streams[stream_id] = reduce_message(streams.get(stream_id, {}), event)
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {"BlockerRecorded", "BlockerResolved"}:
        try:
            streams[stream_id] = reduce_blocker(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {
        "DispatchIssued",
        "DispatchDelivered",
        "DispatchAcknowledged",
        "DispatchExpired",
        "DispatchWithdrawn",
        "DispatchClaimed",
        "DispatchFulfilled",
    }:
        try:
            streams[stream_id] = reduce_dispatch(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {
        "LeaseGranted",
        "LeaseRenewed",
        "LeaseReleased",
        "LeaseExpired",
        "LeaseRevoked",
        "HeartbeatRecorded",
    }:
        try:
            streams[stream_id] = reduce_lease(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {
        "AttemptCreated",
        "AttemptClaimed",
        "AttemptStarted",
        "AttemptCompleted",
        "AttemptFailed",
        "PartialOutcomeRecorded",
        "AttemptPaused",
        "AttemptResumed",
        "AttemptStopRequested",
        "AttemptAbandoned",
        "AttemptSuperseded",
    }:
        try:
            streams[stream_id] = reduce_attempt(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type == "CheckpointRecorded":
        try:
            streams[stream_id] = reduce_checkpoint(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {"PauseRequested", "PauseConfirmed", "StopRequested", "StopConfirmed", "ResumeRequested"}:
        try:
            streams[stream_id] = reduce_operation(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type == "OrphanQuarantined":
        try:
            streams[stream_id] = reduce_recovery(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {
        "ReviewRequested",
        "ReviewAssigned",
        "ReviewStarted",
        "ReviewVerdictRecorded",
        "ReviewChangesRequested",
        "ReviewSatisfied",
        "ReviewWithdrawn",
        "ReviewSuperseded",
    }:
        try:
            streams[stream_id] = reduce_review(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {"ResourceGrantRequested", "ResourcesReleased"}:
        try:
            streams[stream_id] = reduce_resource(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type == "BackupCreated":
        try:
            streams[stream_id] = reduce_backup(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type == "RestoreVerified":
        try:
            streams[stream_id] = reduce_restore_verification(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {
        "ArtefactRegistered",
        "ArtefactAvailabilityRecorded",
        "ArtefactRegenerabilityRecorded",
        "ArtefactIntegrityRecorded",
        "StructuralValidationRecorded",
        "ScientificReviewRecorded",
        "ArtefactUseAuthoritySet",
        "ArtefactSuperseded",
        "LateArtefactAdopted",
    }:
        try:
            streams[stream_id] = reduce_artefact(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
    elif event_type in {
        "DecisionProposed",
        "DecisionReviewRequested",
        "DecisionResolved",
        "DecisionRejected",
        "DecisionExpired",
        "DecisionSuperseded",
        "DecisionAmendmentProposed",
    }:
        try:
            projection = reduce_decision(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
        updated.setdefault("decisions", {})[stream_id] = projection
        streams[stream_id] = projection
    elif event_type == "RuleEvaluationRecorded":
        try:
            projection = reduce_rule_evaluation(streams.get(stream_id, {}), event)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(str(exc)) from exc
        updated.setdefault("rule_evaluations", {})[stream_id] = projection
        streams[stream_id] = projection
    elif event_type == "RecordCorrected":
        payload = event["payload"]
        correction_index = payload.get("governance_correction_index") if isinstance(payload, dict) else None
        corrections = updated.setdefault("governance_correction_index", {})
        if (
            not isinstance(payload, dict)
            or payload.get("erroneous_record_id") != stream_id
            or stream_id not in streams
            or not isinstance(correction_index, str)
            or not correction_index
            or correction_index in corrections
        ):
            raise IntegrityError("invalid governance correction transition")
        corrections[correction_index] = {
            **deepcopy(payload),
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
            "stream_version": event["stream_version"],
        }
    elif event_type in {
        "ContextPacketRequested",
        "ContextCompilationStarted",
        "ContextPacketCompiled",
        "ContextPacketValidated",
        "ContextPacketIssued",
        "ContextPacketDelivered",
        "ContextPacketFailed",
        "ContextPacketExpired",
        "ContextPacketSuperseded",
        "OwnerOperatedContextHandoffPrepared",
        "OwnerOperatedContextHandoffValidated",
        "OwnerOperatedContextHandoffIssued",
        "OwnerOperatedContextDelivered",
    }:
        payload = event["payload"]
        if not isinstance(payload, dict) or payload.get("context_id") != stream_id:
            raise IntegrityError("invalid context lifecycle identity")
        current = streams.get(stream_id)
        current_state = current.get("status") if isinstance(current, dict) else None
        next_state = {
            "ContextPacketRequested": "requested",
            "ContextCompilationStarted": "compiling",
            "ContextPacketCompiled": "compiled",
            "ContextPacketValidated": "validated",
            "ContextPacketIssued": "issued",
            "ContextPacketDelivered": "delivered",
            "ContextPacketFailed": "failed",
            "ContextPacketExpired": "expired",
            "ContextPacketSuperseded": "superseded",
            "OwnerOperatedContextHandoffPrepared": "owner_prepared",
            "OwnerOperatedContextHandoffValidated": "owner_validated",
            "OwnerOperatedContextHandoffIssued": "owner_issued",
            "OwnerOperatedContextDelivered": "owner_delivered",
        }[event_type]
        allowed = {
            None: {"requested"},
            "requested": {"compiling", "failed"},
            "compiling": {"compiled", "failed"},
            "compiled": {"validated", "failed", "owner_prepared"},
            "validated": {"issued"},
            "issued": {"delivered", "expired", "superseded"},
            "delivered": {"expired", "superseded"},
            "owner_prepared": {"owner_validated"},
            "owner_validated": {"owner_issued"},
            "owner_issued": {"owner_delivered"},
            "owner_delivered": set(),
            "failed": set(),
            "expired": set(),
            "superseded": set(),
        }
        if next_state not in allowed[current_state]:
            raise IntegrityError("invalid context lifecycle transition")
        history = list(current.get("history", [])) if isinstance(current, dict) else []
        history.append(
            {
                "event_type": event_type,
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
                "payload": deepcopy(payload),
            }
        )
        streams[stream_id] = {
            **(current if isinstance(current, dict) else {}),
            "context_id": stream_id,
            "status": next_state,
            "history": history,
            "request": deepcopy(payload) if event_type == "ContextPacketRequested" else (current or {}).get("request"),
            "compilation": deepcopy(payload)
            if event_type == "ContextPacketCompiled"
            else (current or {}).get("compilation"),
            "validation": deepcopy(payload)
            if event_type == "ContextPacketValidated"
            else (current or {}).get("validation"),
            "issuance": deepcopy(payload) if event_type == "ContextPacketIssued" else (current or {}).get("issuance"),
            "delivery": deepcopy(payload)
            if event_type == "ContextPacketDelivered"
            else (current or {}).get("delivery"),
            "terminal": deepcopy(payload)
            if next_state in {"failed", "expired", "superseded"}
            else (current or {}).get("terminal"),
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
    elif event_type == "StoreBindingRepaired":
        payload = event.get("payload")
        if (
            event.get("command_type") != "RepairStoreBinding"
            or event.get("schema_id") != "ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired"
            or not isinstance(payload, dict)
            or set(payload)
            != {
                "recovery_binding_sha256",
                "recovery_binding_path",
                "object_path",
                "git_head",
                "git_tree",
                "prior_manifest_sha256",
            }
            or payload.get("recovery_binding_path") != "manifests/binding-repair-current.json"
        ):
            raise IntegrityError("binding repair event relation is invalid")
        repairs = updated.setdefault("binding_repairs", {})
        key = str(event.get("command_payload_hash"))
        existing = repairs.get(key)
        projection = {
            **deepcopy(payload),
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
            "event_batch_id": event["transaction_id"],
            "global_position": event["global_position"],
        }
        if existing is not None and existing != projection:
            raise IntegrityError("binding repair projection conflicts")
        repairs[key] = projection
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
    """Rebuild projection state from canonical ledger events.

    Args:
        events: Ordered canonical event records.
        supported_major: Event-schema major version accepted by this replay.
        schema_registry: Optional active schema registry for runtime validation.
        legacy_command_provenance_through_position: Retained rejected input; any
            nonzero value raises ``IntegrityError``. Use
            ``replay_grandfathered`` for exact G-RM-8 prefix admission.
        authority_state_validator: Optional validator for authority projections.

    Returns:
        The rebuilt projection state.

    Raises:
        IntegrityError: If event integrity fails or the legacy position-only
            provenance parameter is nonzero.
        ValueError: If the legacy position-only parameter is negative.
    """
    if legacy_command_provenance_through_position < 0:
        raise ValueError("legacy command provenance position must be non-negative")
    if legacy_command_provenance_through_position:
        raise IntegrityError(
            "position-only legacy command provenance admission is insufficient; "
            "use the exact grandfather prefix protocol"
        )
    return _replay(
        events,
        supported_major=supported_major,
        schema_registry=schema_registry,
        grandfathered_missing_positions=frozenset(),
        authority_state_validator=authority_state_validator,
    )


def _replay(
    events: Iterable[dict[str, Any]],
    *,
    supported_major: int,
    schema_registry: SchemaRegistry | None,
    grandfathered_missing_positions: frozenset[int],
    authority_state_validator: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    ordered_events = tuple(events)
    resolve_transaction_ids = discovery_resolve_transaction_ids(ordered_events)
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
    transaction_events: list[dict[str, Any]] = []
    for source in ordered_events:
        event = deepcopy(source)
        position = event.get("global_position")
        if _major(event) != supported_major:
            raise IntegrityError(f"unsupported major at {position}")
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
        grandfathered_missing = not recorded_provenance and position in grandfathered_missing_positions
        if recorded_provenance and recorded_provenance != provenance_fields:
            raise IntegrityError(f"incomplete command schema identity at {position}")
        if schema_registry is not None and not recorded_provenance and position not in grandfathered_missing_positions:
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
                if grandfathered_missing:
                    schema_registry.validate("ars://core/event", event)
                elif t2_event:
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
                    if (
                        schema_registry.event_binding(
                            str(event.get("event_type", "")),
                            str(event.get("command_type", "")),
                        )
                        is None
                    ):
                        schema_registry.validate("ars://core/event", event)
                    _validate_recorded_event_schema(event, schema_registry)
            except SchemaError as exc:
                raise IntegrityError(f"event schema validation failed at {position}") from exc
        schema_id = event.get("schema_id")
        if not isinstance(schema_id, str) or not (
            schema_id == "ars://core/event"
            or schema_id.startswith("ars://core/event/")
            or schema_id.startswith("ars://wp6-2/t2/event/")
            or schema_id.startswith("ars://wp6-6/event/")
        ):
            raise IntegrityError(f"unknown event schema at {position}")
        if position != state["last_position"] + 1:
            raise IntegrityError("event position gap or overlap")
        if event.get("previous_event_hash") != state["last_hash"]:
            raise IntegrityError("event hash-chain mismatch")
        if not _verify_event_hash(event):
            raise IntegrityError(f"event hash mismatch at {position}")
        projection_event = event
        if grandfathered_missing:
            if schema_registry is None:
                raise IntegrityError(f"grandfathered schema registry unavailable at {position}")
            binding = schema_registry.event_binding(
                str(event.get("event_type", "")),
                str(event.get("command_type", "")),
            )
            if binding is None:
                raise IntegrityError(f"grandfathered event binding unavailable at {position}")
            command = schema_registry.command_binding(str(event.get("command_type", "")))
            if command is None:
                raise IntegrityError(f"grandfathered command binding unavailable at {position}")
            command_identity = schema_registry.resolve_identity(command.schema_id, command.schema_version)
            projection_event = {
                **event,
                "command_schema_id": command_identity.schema_id,
                "command_schema_version": command_identity.schema_version,
                "command_schema_sha256": command_identity.raw_bytes_sha256,
            }
        discovery_projection_event = is_discovery_projection_event(
            projection_event,
            resolve_transaction_ids=resolve_transaction_ids,
        )
        if not discovery_projection_event:
            _validate_active_lifecycle_binding(projection_event, schema_registry)
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
            transaction_events = []
        if event.get("transaction_count") != transaction_count:
            raise IntegrityError("event transaction count mismatch")
        if t2_event != transaction_zero_based:
            raise IntegrityError("mixed transaction index convention")
        expected_index = transaction_seen if transaction_zero_based else transaction_seen + 1
        if event.get("transaction_index") != expected_index:
            raise IntegrityError("event transaction index gap or overlap")
        transaction_seen += 1
        transaction_events.append(projection_event)
        if transaction_seen == transaction_count:
            _validate_claim_dispatch_transaction(tuple(transaction_events), schema_registry)
        state = apply_event(
            state,
            projection_event,
            discovery_projection_event=discovery_projection_event,
        )
        state["last_position"] = position
        state["last_hash"] = event["event_hash"]
    if transaction_id is not None and transaction_seen != transaction_count:
        raise IntegrityError("incomplete event transaction")
    if state.get("authority_administration_decisions"):
        if authority_state_validator is None:
            raise IntegrityError("authority administration decision validator unavailable")
        authority_state_validator(state)
    if any(
        is_discovery_projection_event(event, resolve_transaction_ids=resolve_transaction_ids)
        for event in ordered_events
    ):
        # Lazy import keeps the command-family predicate a leaf while making
        # public shared-ledger replay reject Discovery semantic tampering.
        from research_system.discovery.runtime import replay_discovery

        replay_discovery(ordered_events, schemas=schema_registry)
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
