from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.lifecycle import (
    changed_task_fields,
    content_hash_matches,
    has_unique_member_ids,
    materialize_scope_member_changes,
    validate_exact_lifecycle_envelope,
)


_TASK_TERMINAL = frozenset({"accepted", "rejected", "partial", "cancelled", "superseded"})


@dataclass(frozen=True)
class ControlPlaneState:
    active_attempt_ids: frozenset[str]
    stream_states: dict[str, dict[str, Any]]


def _reaches(
    edges: dict[tuple[str, int], tuple[str, int]],
    start: tuple[str, int],
    target: tuple[str, int],
) -> bool:
    seen: set[tuple[str, int]] = set()
    pending = [start]
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        replacement = edges.get(node)
        if replacement is not None:
            pending.append(replacement)
    return False


def _task_revision_edges(
    streams: dict[str, dict[str, Any]],
) -> dict[tuple[str, int], tuple[str, int]]:
    edges: dict[tuple[str, int], tuple[str, int]] = {}
    for stream_id, state in streams.items():
        if state.get("task_id") != stream_id:
            continue
        for revision_text, record in state.get("revision_history", {}).items():
            if not isinstance(record, dict):
                continue
            revision = int(revision_text)
            replacement = record.get("replacement")
            if isinstance(replacement, dict):
                edges[(stream_id, revision)] = (
                    str(replacement["task_id"]),
                    int(replacement["revision"]),
                )
            elif record.get("status") == "amended":
                edges[(stream_id, revision)] = (stream_id, revision + 1)
    return edges


def _scope_revision_edges(
    streams: dict[str, dict[str, Any]],
) -> dict[tuple[str, int], tuple[str, int]]:
    edges: dict[tuple[str, int], tuple[str, int]] = {}
    for stream_id, state in streams.items():
        if state.get("scope_definition_id") != stream_id:
            continue
        for revision_text, record in state.get("revision_history", {}).items():
            if not isinstance(record, dict):
                continue
            revision = int(revision_text)
            replacement = record.get("replacement")
            if isinstance(replacement, dict):
                edges[(stream_id, revision)] = (
                    str(replacement["scope_definition_id"]),
                    int(replacement["revision"]),
                )
            elif record.get("status") == "amended":
                edges[(stream_id, revision)] = (stream_id, revision + 1)
    return edges


def _task_definition(state: dict[str, Any]) -> dict[str, Any] | None:
    definition = state.get("definition")
    if isinstance(definition, dict):
        return definition
    legacy = state.get("legacy_definition")
    return legacy if isinstance(legacy, dict) else None


def _task_state_is_rich(state: dict[str, Any]) -> bool:
    return state.get("definition_schema_id") in {
        "ars://core/event/TaskCreated",
        "ars://core/event/TaskAmended",
    }


def validate_task_lifecycle_event(
    streams: dict[str, dict[str, Any]],
    event: dict[str, Any],
) -> None:
    if event.get("event_type") != "TaskSuperseded" or event.get("schema_id") != "ars://core/event/TaskSuperseded":
        return
    payload = event["payload"]
    source_id = event["stream_id"]
    source_state = streams.get(source_id)
    if not isinstance(source_state, dict):
        return
    source_revision = int(source_state.get("current_revision", 1))
    source = (source_id, source_revision)
    replacement = (
        str(payload["replacement_task_id"]),
        int(payload["replacement_task_revision"]),
    )
    edges = _task_revision_edges(streams)
    if _reaches(edges, replacement, source):
        raise ValueError("Task supersession cycle")
    if replacement in edges:
        raise ValueError("Task replacement revision is terminal")

    source_definition = _task_definition(source_state)
    source_rich = _task_state_is_rich(source_state)
    if replacement[0] == source_id:
        if source_rich:
            raise ValueError("TaskSuperseded rich same-Task replacement is uncommitted")
        if replacement[1] <= source_revision:
            raise ValueError("Task replacement revision is stale")
        return

    replacement_state = streams.get(replacement[0])
    if not isinstance(replacement_state, dict):
        raise ValueError("Task replacement revision is missing")
    if int(replacement_state.get("current_revision", 1)) != replacement[1]:
        raise ValueError("Task replacement revision is stale")
    if replacement_state.get("status") in _TASK_TERMINAL:
        raise ValueError("Task replacement revision is terminal")

    replacement_definition = _task_definition(replacement_state)
    replacement_rich = _task_state_is_rich(replacement_state)
    if source_rich != replacement_rich:
        raise ValueError("Task replacement revision is incompatible")
    if source_rich:
        if source_definition.get("project_id") != replacement_definition.get("project_id"):
            raise ValueError("Task replacement revision is incompatible")
        return
    if (
        not isinstance(source_definition, dict)
        or not isinstance(replacement_definition, dict)
        or source_definition.get("task_type") != replacement_definition.get("task_type")
    ):
        raise ValueError("Task replacement revision is incompatible")
    expected_consumers = source_definition.get("continuing_consumers")
    if expected_consumers is not None and set(payload["continuing_consumer_dispositions"]) != set(expected_consumers):
        raise ValueError("Task continuing-consumer dispositions mismatch")


def validate_scope_lifecycle_event(
    streams: dict[str, dict[str, Any]],
    event: dict[str, Any],
) -> None:
    if event.get("event_type") != "ScopeDefinitionSuperseded":
        return
    payload = event["payload"]
    source_id = event["stream_id"]
    source_state = streams.get(source_id)
    if not isinstance(source_state, dict):
        return
    source_revision = int(source_state.get("current_revision", 1))
    source = (source_id, source_revision)
    replacement = (
        str(payload["replacement_scope_definition_id"]),
        int(payload["replacement_revision"]),
    )
    edges = _scope_revision_edges(streams)
    if _reaches(edges, replacement, source):
        raise ValueError("ScopeDefinition supersession cycle")
    if replacement in edges:
        raise ValueError("ScopeDefinition replacement revision is terminal")
    replacement_state = streams.get(replacement[0])
    if not isinstance(replacement_state, dict):
        raise ValueError("ScopeDefinition replacement revision is missing")
    if int(replacement_state.get("current_revision", 1)) != replacement[1]:
        raise ValueError("ScopeDefinition replacement revision is stale")
    if replacement_state.get("status") != "open":
        raise ValueError("ScopeDefinition replacement revision is terminal")


def reduce_task(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    if event_type == "TaskCreated":
        if state:
            raise ValueError("TaskCreated requires empty stream")
        if event.get("schema_id") == "ars://core/event/TaskCreated":
            payload = event["payload"]
            definition = payload["definition"]
            revision = int(definition["revision"])
            if (
                payload["new_task_id"] != event["stream_id"]
                or definition["task_id"] != event["stream_id"]
                or revision != 1
                or definition["project_id"] != event.get("project_id")
                or not content_hash_matches(definition)
            ):
                raise ValueError("TaskCreated subject binding mismatch")
            return {
                "task_id": event["stream_id"],
                "status": "draft",
                "current_revision": revision,
                "definition": definition,
                "definition_schema_id": event["schema_id"],
                "revision_history": {
                    str(revision): {
                        "status": "draft",
                        "definition": definition,
                    }
                },
                "version": 1,
            }

        created = {
            "task_id": event["stream_id"],
            "status": "draft",
            "version": 1,
        }
        legacy_definition = event.get("payload")
        if isinstance(legacy_definition, dict):
            created.update(
                {
                    "current_revision": 1,
                    "legacy_definition": legacy_definition,
                    "definition_schema_id": event.get("schema_id"),
                    "revision_history": {
                        "1": {
                            "status": "draft",
                            "definition": legacy_definition,
                        }
                    },
                }
            )
        return created
    if event_type == "TaskAmended":
        if not state or state.get("status") in _TASK_TERMINAL:
            raise ValueError("TaskAmended requires a nonterminal source revision")
        payload = event["payload"]
        prior_revision = int(payload["prior_revision"])
        new_revision = int(payload["new_revision"])
        current_revision = int(state.get("current_revision", 1))
        if prior_revision != current_revision or new_revision != prior_revision + 1:
            raise ValueError("TaskAmended revision is not current and consecutive")
        source_definition = state.get("definition")
        replacement_definition = payload["replacement_definition"]
        if (
            not isinstance(source_definition, dict)
            or not content_hash_matches(source_definition)
            or not _task_state_is_rich(state)
            or payload["task_id"] != state["task_id"]
            or replacement_definition["task_id"] != state["task_id"]
            or int(replacement_definition["revision"]) != new_revision
            or replacement_definition["project_id"] != event.get("project_id")
            or not content_hash_matches(replacement_definition)
        ):
            raise ValueError("TaskAmended subject binding mismatch")
        actual_changes = changed_task_fields(
            source_definition,
            replacement_definition,
        )
        if not actual_changes or set(payload["changed_fields"]) != actual_changes:
            raise ValueError("TaskAmended changed_fields mismatch")
        history = dict(state.get("revision_history", {}))
        prior = dict(history.get(str(prior_revision), {}))
        prior["status"] = "amended"
        history[str(prior_revision)] = prior
        history[str(new_revision)] = {
            "status": state["status"],
            "definition": replacement_definition,
            "changed_fields": list(payload["changed_fields"]),
            "rationale": payload["rationale"],
        }
        return {
            **state,
            "current_revision": new_revision,
            "definition": replacement_definition,
            "definition_schema_id": event["schema_id"],
            "revision_history": history,
            "version": state["version"] + 1,
        }
    if event_type == "TaskSuperseded":
        if not state or state.get("status") in _TASK_TERMINAL:
            raise ValueError("TaskSuperseded requires a nonterminal source revision")
        payload = event["payload"]
        current_revision = int(state.get("current_revision", 1))
        exact = event.get("schema_id") == "ars://core/event/TaskSuperseded"
        if exact and (payload["task_id"] != state["task_id"] or payload["task_id"] != event["stream_id"]):
            raise ValueError("TaskSuperseded subject binding mismatch")
        if exact and not payload["continuing_consumer_dispositions"]:
            raise ValueError("TaskSuperseded requires consumer dispositions")
        source_revision = current_revision if exact else int(payload["source_task_revision"])
        if source_revision != current_revision:
            raise ValueError("TaskSuperseded source revision is not current")
        replacement = {
            "task_id": payload["replacement_task_id"],
            "revision": int(payload["replacement_task_revision"]),
        }
        if exact and replacement["task_id"] == state["task_id"] and isinstance(state.get("definition"), dict):
            raise ValueError("TaskSuperseded rich same-Task replacement is uncommitted")
        if exact:
            legacy_definition = state.get("legacy_definition")
            expected_consumers = (
                legacy_definition.get("continuing_consumers") if isinstance(legacy_definition, dict) else None
            )
            if expected_consumers is not None and set(payload["continuing_consumer_dispositions"]) != set(
                expected_consumers
            ):
                raise ValueError("Task continuing-consumer dispositions mismatch")
        history = dict(state.get("revision_history", {}))
        source_record = dict(history.get(str(source_revision), {}))
        source_record.update(
            {
                "status": "superseded",
                "replacement": replacement,
            }
        )
        if exact:
            source_record.update(
                {
                    "continuing_consumer_dispositions": list(payload["continuing_consumer_dispositions"]),
                    "lineage_reason": payload["lineage_reason"],
                }
            )
        else:
            source_record.update(
                {
                    "supersession_scope": list(payload["supersession_scope"]),
                    "continuing_consumers": list(payload["continuing_consumers"]),
                    "lineage": list(payload["lineage"]),
                }
            )
        history[str(source_revision)] = source_record
        if replacement["task_id"] == state["task_id"]:
            history.setdefault(str(replacement["revision"]), {"status": "draft"})
            return {
                **state,
                "status": "draft",
                "current_revision": replacement["revision"],
                "revision_history": history,
                "version": state["version"] + 1,
            }
        updated = {
            **state,
            "status": "superseded",
            "current_revision": source_revision,
            "replacement": replacement,
            "revision_history": history,
            "version": state["version"] + 1,
        }
        if exact:
            updated.update(
                {
                    "continuing_consumer_dispositions": list(payload["continuing_consumer_dispositions"]),
                    "lineage_reason": payload["lineage_reason"],
                }
            )
        else:
            updated.update(
                {
                    "supersession_scope": list(payload["supersession_scope"]),
                    "continuing_consumers": list(payload["continuing_consumers"]),
                    "lineage": list(payload["lineage"]),
                }
            )
        return updated
    if event_type == "ReadinessRequested" and state.get("status") == "draft":
        return {
            **state,
            "status": "readiness_pending",
            "version": state["version"] + 1,
        }
    raise ValueError(f"illegal task transition: {state.get('status')} -> {event_type}")


def _materialize_scope_definition(
    definition: dict[str, Any],
    amendment: dict[str, Any],
) -> dict[str, Any]:
    return {
        **definition,
        "revision": int(amendment["new_revision"]),
        "members": materialize_scope_member_changes(
            definition["members"],
            amendment["member_changes"],
        ),
    }


def reduce_scope(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "ScopeDefinitionCreated":
        if state:
            raise ValueError("ScopeDefinitionCreated requires empty stream")
        revision = int(payload["revision"])
        if payload["new_scope_definition_id"] != event["stream_id"] or revision != 1:
            raise ValueError("ScopeDefinitionCreated subject binding mismatch")
        if not has_unique_member_ids(payload["members"]):
            raise ValueError("ScopeDefinitionCreated duplicate member identity")
        return {
            "scope_definition_id": event["stream_id"],
            "status": "open",
            "current_revision": revision,
            "definition": payload,
            "revision_history": {
                str(revision): {
                    "status": "open",
                    "definition": payload,
                }
            },
            "version": 1,
        }
    if event_type == "ScopeDefinitionAmended":
        if not state or state.get("status") != "open":
            raise ValueError("ScopeDefinitionAmended requires an open scope")
        prior_revision = int(payload["prior_revision"])
        new_revision = int(payload["new_revision"])
        if (
            payload["scope_definition_id"] != state["scope_definition_id"]
            or prior_revision != state["current_revision"]
            or new_revision != prior_revision + 1
        ):
            raise ValueError("ScopeDefinitionAmended revision binding mismatch")
        if set(payload["changed_fields"]) != {"members"}:
            raise ValueError("ScopeDefinitionAmended changed_fields mismatch")
        if not payload["member_changes"] or not has_unique_member_ids(payload["member_changes"]):
            raise ValueError("ScopeDefinitionAmended duplicate or empty member changes")
        definition = _materialize_scope_definition(
            state["definition"],
            payload,
        )
        history = dict(state["revision_history"])
        prior = dict(history[str(prior_revision)])
        prior["status"] = "amended"
        history[str(prior_revision)] = prior
        history[str(new_revision)] = {
            "status": "open",
            "definition": definition,
            "amendment": payload,
        }
        return {
            **state,
            "current_revision": new_revision,
            "definition": definition,
            "last_amendment": payload,
            "revision_history": history,
            "version": state["version"] + 1,
        }
    if event_type == "ScopeDefinitionSuperseded":
        if not state or state.get("status") != "open":
            raise ValueError("ScopeDefinitionSuperseded requires an open scope")
        if payload["scope_definition_id"] != state["scope_definition_id"]:
            raise ValueError("ScopeDefinitionSuperseded subject binding mismatch")
        if not has_unique_member_ids(payload["member_dispositions"]):
            raise ValueError("ScopeDefinitionSuperseded duplicate member disposition")
        expected_members = {
            str(member["member_id"]): str(member["member_kind"]) for member in state["definition"]["members"]
        }
        observed_members = {
            str(member["member_id"]): str(member["member_kind"]) for member in payload["member_dispositions"]
        }
        if observed_members != expected_members:
            raise ValueError("ScopeDefinitionSuperseded member disposition mismatch")
        replacement = {
            "scope_definition_id": payload["replacement_scope_definition_id"],
            "revision": int(payload["replacement_revision"]),
        }
        history = dict(state["revision_history"])
        current_revision = int(state["current_revision"])
        current = dict(history[str(current_revision)])
        current.update(
            {
                "status": "superseded",
                "replacement": replacement,
                "member_dispositions": list(payload["member_dispositions"]),
                "lineage_reason": payload["lineage_reason"],
            }
        )
        history[str(current_revision)] = current
        return {
            **state,
            "status": "superseded",
            "replacement": replacement,
            "member_dispositions": list(payload["member_dispositions"]),
            "lineage_reason": payload["lineage_reason"],
            "revision_history": history,
            "version": state["version"] + 1,
        }
    raise ValueError(f"illegal scope transition: {state.get('status')} -> {event_type}")


def reduce_message(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce one exact Message stream without widening its terminal states."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    stream_id = event["stream_id"]
    if event_type == "MessagePublished":
        if state:
            raise ValueError("MessagePublished requires an absent Message stream")
        if payload.get("new_message_id") != stream_id:
            raise ValueError("MessagePublished subject binding mismatch")
        if payload.get("sender_actor_id") != event.get("actor_id"):
            raise ValueError("MessagePublished sender binding mismatch")
        if payload.get("reply_to_message_id") == stream_id:
            raise ValueError("MessagePublished self reference is invalid")
        if payload.get("message_type") == "acknowledgement" and (
            payload.get("correlation_message_id") != payload.get("reply_to_message_id")
        ):
            raise ValueError("MessagePublished acknowledgement correlation is inconsistent")
        return {
            "message_id": stream_id,
            "status": "published",
            "published_payload": payload,
            "content_sha256": sha256_hex(canonical_bytes(payload)),
            "published_position": event["global_position"],
            "version": 1,
        }
    if not state:
        raise ValueError(f"{event_type} requires a published Message stream")
    if payload.get("message_id") != state.get("message_id"):
        raise ValueError("Message transition subject binding mismatch")
    if event_type == "MessageDelivered":
        if state.get("status") != "published":
            raise ValueError("MessageDelivered requires published Message state")
        if (
            payload.get("content_sha256") != state.get("content_sha256")
            or payload.get("recipient_actor_ids") != state["published_payload"].get("recipient_actor_ids")
            or not payload.get("delivery_evidence_refs")
        ):
            raise ValueError("MessageDelivered content or recipient binding mismatch")
        return {
            **state,
            "status": "delivered",
            "delivery": payload,
            "version": state["version"] + 1,
        }
    if event_type == "MessageAcknowledged":
        if state.get("status") != "delivered":
            raise ValueError("MessageAcknowledged requires delivered Message state")
        if event.get("actor_id") not in state["published_payload"].get("recipient_actor_ids", []):
            raise ValueError("MessageAcknowledged recipient binding mismatch")
        if (
            payload.get("content_sha256") != state.get("content_sha256")
            or payload.get("recipient_actor_ids") != state["published_payload"].get("recipient_actor_ids")
            or payload.get("source_position") != state.get("published_position")
        ):
            raise ValueError("MessageAcknowledged content, recipient, or source binding mismatch")
        return {
            **state,
            "status": "acknowledged",
            "acknowledgement": payload,
            "version": state["version"] + 1,
        }
    if event_type == "MessageDeliveryFailed":
        if state.get("status") != "published":
            raise ValueError("MessageDeliveryFailed requires published Message state")
        if not payload.get("failure_evidence_refs"):
            raise ValueError("MessageDeliveryFailed requires failure evidence")
        return {
            **state,
            "status": "delivery_failed",
            "failure": payload,
            "version": state["version"] + 1,
        }
    raise ValueError(f"illegal message transition: {state.get('status')} -> {event_type}")


def replay_control_plane(events: Iterable[dict[str, Any]]) -> ControlPlaneState:
    attempts: set[str] = set()
    stream_states: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] in {
            "TaskCreated",
            "TaskAmended",
            "TaskSuperseded",
        }:
            stream_id = event["stream_id"]
            validate_task_lifecycle_event(stream_states, event)
            stream_states[stream_id] = reduce_task(
                stream_states.get(stream_id, {}),
                event,
            )
        elif event["event_type"] in {
            "ScopeDefinitionCreated",
            "ScopeDefinitionAmended",
            "ScopeDefinitionSuperseded",
        }:
            stream_id = event["stream_id"]
            validate_scope_lifecycle_event(stream_states, event)
            stream_states[stream_id] = reduce_scope(
                stream_states.get(stream_id, {}),
                event,
            )
        elif event["event_type"] in {
            "MessagePublished",
            "MessageDelivered",
            "MessageAcknowledged",
            "MessageDeliveryFailed",
        }:
            stream_id = event["stream_id"]
            stream_states[stream_id] = reduce_message(
                stream_states.get(stream_id, {}),
                event,
            )
        elif event["event_type"] == "DispatchClaimed":
            attempts.add(event["payload"]["attempt_id"])
        else:
            raise ValueError(f"unsupported event type: {event['event_type']}")
    return ControlPlaneState(frozenset(attempts), stream_states)
