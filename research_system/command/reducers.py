from __future__ import annotations

import json

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.lifecycle import (
    changed_task_fields,
    content_hash_matches,
    has_unique_member_ids,
    materialize_scope_member_changes,
    validate_exact_lifecycle_envelope,
    validate_scope_completion_members,
)
from research_system.operations.resources import RESOURCE_GRANT_V1_1_SCHEMA_VERSION

_TASK_TERMINAL = frozenset({"accepted", "rejected", "partial", "cancelled", "superseded"})
_ATTEMPT_TERMINAL = frozenset({"completed", "failed", "partial", "abandoned", "superseded"})


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
    if event.get("event_type") == "ScopeCompleted":
        source_state = streams.get(event["stream_id"])
        if isinstance(source_state, dict):
            validate_scope_completion_members(
                source_state.get("definition", {}),
                event["payload"].get("member_dispositions", ()),
                streams,
            )
        return
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
        next_status = "readiness_pending" if state["status"] in {"readiness_pending", "ready"} else state["status"]
        history[str(new_revision)] = {
            "status": next_status,
            "definition": replacement_definition,
            "changed_fields": list(payload["changed_fields"]),
            "rationale": payload["rationale"],
        }
        updated = {
            **{key: value for key, value in state.items() if key not in {"readiness_request", "readiness_approval"}},
            "status": next_status,
            "current_revision": new_revision,
            "definition": replacement_definition,
            "definition_schema_id": event["schema_id"],
            "revision_history": history,
            "version": state["version"] + 1,
        }
        return updated
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
        payload = event["payload"]
        if (
            payload["task_id"] != state.get("task_id")
            or int(payload["task_revision"]) != int(state.get("current_revision", 0))
            or not payload["readiness_evidence_refs"]
        ):
            raise ValueError("ReadinessRequested subject binding mismatch")
        return {
            **state,
            "status": "readiness_pending",
            "readiness_request": payload,
            "version": state["version"] + 1,
        }
    if event_type == "ReadinessApproved" and state.get("status") == "readiness_pending":
        payload = event["payload"]
        if (
            payload["task_id"] != state.get("task_id")
            or int(payload["task_revision"]) != int(state.get("current_revision", 0))
            or not payload["readiness_evidence_refs"]
            or not payload["passed_check_ids"]
        ):
            raise ValueError("ReadinessApproved subject binding mismatch")
        return {
            **state,
            "status": "ready",
            "readiness_approval": payload,
            "version": state["version"] + 1,
        }
    if event_type == "TaskClaimStarted" and state.get("status") == "ready":
        payload = event["payload"]
        if (
            set(payload) != {"task_id", "task_revision"}
            or payload["task_id"] != state.get("task_id")
            or int(payload["task_revision"]) != int(state.get("current_revision", 0))
        ):
            raise ValueError("TaskClaimStarted subject binding mismatch")
        return {
            **state,
            "status": "in_progress",
            "version": state["version"] + 1,
        }
    if event_type == "TaskBlocked" and state.get("status") in {
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "input_required",
        "paused",
    }:
        payload = event["payload"]
        if payload["task_id"] != state.get("task_id"):
            raise ValueError("TaskBlocked subject binding mismatch")
        return {
            **state,
            "status": "blocked",
            "prior_active_status": state.get("prior_active_status", state["status"]),
            "suspension": payload,
            "version": state["version"] + 1,
        }
    if event_type == "InputRequested" and state.get("status") in {
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "blocked",
        "paused",
    }:
        payload = event["payload"]
        if payload["task_id"] != state.get("task_id"):
            raise ValueError("InputRequested subject binding mismatch")
        return {
            **state,
            "status": "input_required",
            "prior_active_status": state.get("prior_active_status", state["status"]),
            "suspension": payload,
            "version": state["version"] + 1,
        }
    if event_type == "TaskPaused" and state.get("status") in {
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "blocked",
        "input_required",
    }:
        payload = event["payload"]
        expected_prior = (
            state.get("prior_active_status")
            if state.get("status") in {"blocked", "input_required"}
            else state.get("status")
        )
        if payload["task_id"] != state.get("task_id") or payload["prior_active_status"] != expected_prior:
            raise ValueError("TaskPaused subject binding mismatch")
        return {
            **state,
            "status": "paused",
            "prior_active_status": payload["prior_active_status"],
            "suspension": payload,
            "version": state["version"] + 1,
        }
    if event_type == "TaskResumed" and state.get("status") in {"blocked", "input_required", "paused"}:
        payload = event["payload"]
        if (
            payload["task_id"] != state.get("task_id")
            or payload["suspended_status"] != state.get("status")
            or payload["prior_active_status"] != state.get("prior_active_status")
            or not payload["resolution_evidence_refs"]
            or not payload["authority_evidence_refs"]
        ):
            raise ValueError("TaskResumed suspension binding mismatch")
        return {
            **state,
            "status": payload["prior_active_status"],
            "last_resume": payload,
            "version": state["version"] + 1,
        }
    if event_type == "TaskSubmittedForReview" and state.get("status") == "in_progress":
        payload = event["payload"]
        if payload["task_id"] != state.get("task_id"):
            raise ValueError("TaskSubmittedForReview subject binding mismatch")
        return {
            **state,
            "status": "review_pending",
            "review_submission": payload,
            "version": state["version"] + 1,
        }
    if event_type == "TaskCancelled" and state.get("status") not in _TASK_TERMINAL:
        payload = event["payload"]
        if payload["task_id"] != state.get("task_id"):
            raise ValueError("TaskCancelled subject binding mismatch")
        return {
            **state,
            "status": "cancelled",
            "cancellation": payload,
            "terminal_record": {"event_id": event["event_id"], "event_hash": event["event_hash"]},
            "version": state["version"] + 1,
        }
    if event_type == "TaskAccepted" and state.get("status") == "review_pending":
        payload = event["payload"]
        if (
            payload["task_id"] != state.get("task_id")
            or int(payload["task_revision"]) != int(state.get("current_revision", 1))
            or not payload["satisfied_review_ids"]
            or not payload["satisfied_acceptance_criteria"]
        ):
            raise ValueError("TaskAccepted subject or evidence binding mismatch")
        return {
            **state,
            "status": "accepted",
            "acceptance": deepcopy(payload),
            "terminal_record": {"event_id": event["event_id"], "event_hash": event["event_hash"]},
            "version": state["version"] + 1,
        }
    if event_type == "TaskRejected" and state.get("status") == "review_pending":
        payload = event["payload"]
        if payload["task_id"] != state.get("task_id") or int(payload["task_revision"]) != int(
            state.get("current_revision", 1)
        ):
            raise ValueError("TaskRejected subject or revision binding mismatch")
        return {
            **state,
            "status": "rejected",
            "rejection": deepcopy(payload),
            "terminal_record": {"event_id": event["event_id"], "event_hash": event["event_hash"]},
            "version": state["version"] + 1,
        }
    if (
        event_type == "PartialOutcomeRecorded"
        and event.get("command_type") == "ClosePartial"
        and state.get("status") not in _TASK_TERMINAL
    ):
        payload = event["payload"]
        if (
            payload["task_id"] != state.get("task_id")
            or not payload["unmet_obligations"]
            or not payload["claim_restrictions"]
        ):
            raise ValueError("PartialOutcomeRecorded Task binding mismatch")
        return {
            **state,
            "status": "partial",
            "partial_outcome": deepcopy(payload),
            "terminal_record": {"event_id": event["event_id"], "event_hash": event["event_hash"]},
            "version": state["version"] + 1,
        }
    if event_type == "TaskReopened" and state.get("status") in {"partial", "rejected", "cancelled"}:
        payload = event["payload"]
        terminal = state.get("terminal_record")
        preserved = payload["preserved_terminal_record_ref"]
        if (
            payload["task_id"] != state.get("task_id")
            or payload["prior_terminal_status"] != state.get("status")
            or int(payload["new_execution_epoch"]) != int(state.get("execution_epoch", 1)) + 1
            or not isinstance(terminal, dict)
            or preserved.get("record_id") != terminal.get("event_id")
            or preserved.get("content_sha256") != terminal.get("event_hash")
        ):
            raise ValueError("TaskReopened terminal history binding mismatch")
        return {
            **state,
            "status": "readiness_pending",
            "execution_epoch": int(payload["new_execution_epoch"]),
            "last_reopen": deepcopy(payload),
            "preserved_terminal_records": [
                *state.get("preserved_terminal_records", []),
                deepcopy(terminal),
            ],
            "version": state["version"] + 1,
        }
    raise ValueError(f"illegal task transition: {state.get('status')} -> {event_type}")


def reduce_dispatch(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce the C1 Dispatch state machine from its exact event payloads."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "DispatchIssued":
        definition = payload["definition"]
        if state or payload["dispatch_id"] != event["stream_id"] or definition["dispatch_id"] != event["stream_id"]:
            raise ValueError("DispatchIssued requires an empty bound Dispatch stream")
        return {
            "dispatch_id": event["stream_id"],
            "status": "issued",
            "task_id": definition["task_id"],
            "task_revision": int(definition["task_revision"]),
            "definition": definition,
            "version": event["stream_version"],
        }
    if not state or payload.get("dispatch_id") != state.get("dispatch_id"):
        raise ValueError(f"{event_type} Dispatch subject binding mismatch")
    if event_type == "DispatchDelivered":
        if state.get("status") != "issued" or not payload["delivery_evidence_refs"]:
            raise ValueError("DispatchDelivered requires issued Dispatch and delivery evidence")
        return {**state, "status": "delivered", "delivery": payload, "version": event["stream_version"]}
    if event_type == "DispatchAcknowledged":
        if state.get("status") != "delivered":
            raise ValueError("DispatchAcknowledged requires delivered Dispatch")
        delivery = state.get("delivery", {})
        if payload["recipient_actor_id"] != delivery.get("recipient_actor_id"):
            raise ValueError("DispatchAcknowledged recipient mismatch")
        return {**state, "status": "acknowledged", "acknowledgement": payload, "version": event["stream_version"]}
    if event_type == "DispatchExpired":
        if state.get("status") not in {"issued", "delivered", "acknowledged"}:
            raise ValueError("DispatchExpired requires a claimable pre-claim Dispatch")
        if payload["observed_prior_state"] != state.get("status"):
            raise ValueError("DispatchExpired observed state mismatch")
        return {**state, "status": "expired", "expiry": payload, "version": event["stream_version"]}
    if event_type == "DispatchWithdrawn":
        if state.get("status") not in {"issued", "claimed"} or payload["observed_prior_state"] != state.get("status"):
            raise ValueError("DispatchWithdrawn observed state mismatch")
        if state.get("status") == "claimed":
            stop = payload.get("attempt_stop_disposition")
            if not isinstance(stop, dict) or not stop.get("children_closed") or not stop.get("writers_closed"):
                raise ValueError("Claimed Dispatch withdrawal requires closed Attempt disposition")
        return {**state, "status": "withdrawn", "withdrawal": payload, "version": event["stream_version"]}
    if event_type == "DispatchClaimed":
        if state.get("status") != "acknowledged":
            raise ValueError("DispatchClaimed requires acknowledged Dispatch")
        if (
            payload["task_id"] != state.get("task_id")
            or int(payload["task_revision"]) != int(state.get("task_revision", 0))
            or payload["declared_write_set"] != ["dispatch", "task"]
        ):
            raise ValueError("DispatchClaimed relation or write-set mismatch")
        return {
            **state,
            "status": "claimed",
            "lease_id": payload["lease_id"],
            "claim": payload,
            "version": event["stream_version"],
        }
    if event_type == "DispatchFulfilled":
        if state.get("status") != "claimed":
            raise ValueError("DispatchFulfilled requires claimed Dispatch")
        return {**state, "status": "fulfilled", "fulfilment": payload, "version": event["stream_version"]}
    raise ValueError(f"illegal dispatch transition: {state.get('status')} -> {event_type}")


def reduce_blocker(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce the C2 Blocker record and exact resolution evidence."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "BlockerRecorded":
        if state or payload["new_blocker_id"] != event["stream_id"] or not payload["blocker_evidence_refs"]:
            raise ValueError("BlockerRecorded requires an empty bound stream and evidence")
        return {
            "blocker_id": event["stream_id"],
            "status": "open",
            "record": payload,
            "version": event["stream_version"],
        }
    if event_type == "BlockerResolved":
        if (
            not state
            or state.get("status") != "open"
            or payload["blocker_id"] != state.get("blocker_id")
            or not payload["resolution_evidence_refs"]
        ):
            raise ValueError("BlockerResolved requires an open bound Blocker and evidence")
        return {
            **state,
            "status": "resolved",
            "resolution": payload,
            "version": event["stream_version"],
        }
    raise ValueError(f"illegal blocker transition: {state.get('status')} -> {event_type}")


def reduce_lease(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce C1 lease ownership and heartbeat facts."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "LeaseGranted":
        if state or payload["new_lease_id"] != event["stream_id"]:
            raise ValueError("LeaseGranted requires an empty bound Lease stream")
        return {
            "lease_id": event["stream_id"],
            "status": "active",
            "task_id": payload["task_id"],
            "task_revision": int(payload["task_revision"]),
            "dispatch_id": payload["dispatch_id"],
            "attempt_id": payload["attempt_id"],
            "resource_grant_id": payload["resource_grant_id"],
            "holder_actor_id": payload["holder_actor_id"],
            "expires_at": payload["expires_at"],
            "renewal_policy_ref": payload["renewal_policy_ref"],
            "grant": payload,
            "version": event["stream_version"],
        }
    if not state or payload.get("lease_id") != state.get("lease_id"):
        raise ValueError(f"{event_type} Lease subject binding mismatch")
    if event_type == "LeaseRenewed":
        if (
            state.get("status") != "active"
            or payload["holder_actor_id"] != state.get("holder_actor_id")
            or payload["prior_expiry"] != state.get("expires_at")
            or payload["renewal_policy_ref"] != state.get("renewal_policy_ref")
        ):
            raise ValueError("LeaseRenewed current-holder binding mismatch")
        return {**state, "expires_at": payload["new_expiry"], "renewal": payload, "version": event["stream_version"]}
    if event_type == "LeaseReleased":
        if state.get("status") != "active" or payload["holder_actor_id"] != state.get("holder_actor_id"):
            raise ValueError("LeaseReleased current-holder binding mismatch")
        return {**state, "status": "released", "release": payload, "version": event["stream_version"]}
    if event_type == "LeaseExpired":
        if state.get("status") != "active":
            raise ValueError("LeaseExpired requires active Lease")
        return {**state, "status": "expired", "expiry": payload, "version": event["stream_version"]}
    if event_type == "LeaseRevoked":
        if state.get("status") != "active":
            raise ValueError("LeaseRevoked requires active Lease")
        return {**state, "status": "revoked", "revocation": payload, "version": event["stream_version"]}
    if event_type == "HeartbeatRecorded":
        if state.get("status") != "active":
            raise ValueError("HeartbeatRecorded requires active Lease")
        return {**state, "last_heartbeat": payload, "version": event["stream_version"]}
    raise ValueError(f"illegal lease transition: {state.get('status')} -> {event_type}")


def reduce_attempt(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce C1 Attempt creation, claim, and running admission."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "AttemptCreated":
        if state or payload["new_attempt_id"] != event["stream_id"]:
            raise ValueError("AttemptCreated requires an empty bound Attempt stream")
        if payload["creation_kind"] == "initial":
            return {
                "attempt_id": event["stream_id"],
                "status": "created",
                "task_id": payload["task_id"],
                "task_revision": int(payload["task_revision"]),
                "dispatch_id": payload["dispatch_id"],
                "attempt_ordinal": int(payload["attempt_ordinal"]),
                "execution_epoch": int(payload["execution_epoch"]),
                "creation": payload,
                "version": event["stream_version"],
            }
        if payload["creation_kind"] != "retry":
            raise ValueError("AttemptCreated creation kind is invalid")
        return {
            "attempt_id": event["stream_id"],
            "status": "created",
            "attempt_ordinal": int(payload["attempt_ordinal"]),
            "execution_epoch": int(payload["execution_epoch"]),
            "prior_attempt_id": payload["prior_attempt_id"],
            "prior_outcome": payload["prior_outcome"],
            "creation": payload,
            "version": event["stream_version"],
        }
    if not state or (event_type != "PartialOutcomeRecorded" and payload.get("attempt_id") != state.get("attempt_id")):
        raise ValueError(f"{event_type} Attempt subject binding mismatch")
    if event_type == "AttemptClaimed":
        if (
            state.get("status") != "created"
            or payload["task_id"] != state.get("task_id")
            or int(payload["task_revision"]) != int(state.get("task_revision", 0))
            or payload["dispatch_id"] != state.get("dispatch_id")
        ):
            raise ValueError("AttemptClaimed relation mismatch")
        return {
            **state,
            "status": "claimed",
            "lease_id": payload["lease_id"],
            "claim": payload,
            "version": event["stream_version"],
        }
    if event_type == "AttemptStarted":
        if state.get("status") != "claimed":
            raise ValueError("AttemptStarted requires claimed Attempt")
        return {**state, "status": "running", "start": payload, "version": event["stream_version"]}
    if event_type in {"AttemptCompleted", "AttemptFailed", "PartialOutcomeRecorded"}:
        if state.get("status") != "running":
            raise ValueError(f"{event_type} requires running Attempt")
        if event_type == "PartialOutcomeRecorded" and (
            payload.get("subject_kind") != "task" or payload.get("task_id") != state.get("task_id")
        ):
            raise ValueError("PartialOutcomeRecorded task relation mismatch")
        status = {
            "AttemptCompleted": "completed",
            "AttemptFailed": "failed",
            "PartialOutcomeRecorded": "partial",
        }[event_type]
        return {**state, "status": status, "outcome": payload, "version": event["stream_version"]}
    if event_type == "AttemptPaused":
        if state.get("status") != "running":
            raise ValueError("AttemptPaused requires running Attempt")
        return {**state, "status": "paused", "pause": payload, "version": event["stream_version"]}
    if event_type == "AttemptResumed":
        checkpoint = payload.get("checkpoint_disposition")
        if (
            state.get("status") != "paused"
            or payload.get("compatibility") != "compatible"
            or not isinstance(checkpoint, dict)
            or checkpoint.get("compatibility") != "compatible"
        ):
            raise ValueError("AttemptResumed requires paused compatible checkpoint state")
        return {**state, "status": "running", "resume": payload, "version": event["stream_version"]}
    if event_type == "AttemptStopRequested":
        if state.get("status") != "running":
            raise ValueError("AttemptStopRequested requires running Attempt")
        return {**state, "status": "stopping", "stop_request": payload, "version": event["stream_version"]}
    if event_type == "AttemptAbandoned":
        process = payload.get("process_disposition")
        if (
            state.get("status") != "stopping"
            or not isinstance(process, dict)
            or not process.get("children_closed")
            or not process.get("writers_closed")
        ):
            raise ValueError("AttemptAbandoned requires confirmed stopped process")
        return {**state, "status": "abandoned", "abandonment": payload, "version": event["stream_version"]}
    if event_type == "AttemptSuperseded":
        if state.get("status") not in {"created", "claimed", "running", "paused", "stopping"}:
            raise ValueError("AttemptSuperseded requires nonterminal Attempt")
        return {**state, "status": "superseded", "supersession": payload, "version": event["stream_version"]}
    raise ValueError(f"illegal attempt transition: {state.get('status')} -> {event_type}")


def reduce_resource(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce the bounded C1 resource-request and release records."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "ResourceGrantRequested":
        if state or payload["resource_id"] != event["stream_id"]:
            raise ValueError("ResourceGrantRequested requires an empty bound Resource stream")
        request = json.loads(canonical_bytes(payload["resource_request"]).decode("utf-8"))
        authority_refs = request.get("projection_evidence_refs")
        if not isinstance(authority_refs, list) or len(authority_refs) != 1 or not isinstance(authority_refs[0], str):
            raise ValueError("ResourceGrantRequested requires one authority preimage reference")
        return {
            "resource_id": event["stream_id"],
            "status": "active",
            "request": request,
            "request_sha256": sha256_hex(canonical_bytes(request)),
            "authority_preimage_ref": authority_refs[0],
            "grant_ref": {
                "kind": "resource_grant",
                "id": event["stream_id"],
                "revision": 1,
                "schema_version": RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
            },
            "version": event["stream_version"],
        }
    if event_type == "ResourcesReleased":
        if not state or state.get("status") != "active" or payload["resource_id"] != state.get("resource_id"):
            raise ValueError("ResourcesReleased requires active Resource")
        return {**state, "status": "released", "release": payload, "version": event["stream_version"]}
    raise ValueError(f"illegal resource transition: {state.get('status')} -> {event_type}")


def reduce_checkpoint(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Attach a state-neutral, monotonic checkpoint fact to its Attempt."""
    validate_exact_lifecycle_envelope(event)
    payload = event["payload"]
    if (
        event["event_type"] != "CheckpointRecorded"
        or not state
        or payload["attempt_id"] != state.get("attempt_id")
        or payload["task_id"] != state.get("task_id")
        or int(payload["task_revision"]) != int(state.get("task_revision", 0))
    ):
        raise ValueError("CheckpointRecorded Attempt relation mismatch")
    latest = state.get("latest_checkpoint")
    if isinstance(latest, dict) and (
        payload["checkpoint_manifest_id"] == latest.get("checkpoint_manifest_id")
        or int(payload["completed_units"]) < int(latest.get("completed_units", 0))
        or int(payload["remaining_units"]) > int(latest.get("remaining_units", 0))
        or payload["compatibility_fingerprint"] != latest.get("compatibility_fingerprint")
    ):
        raise ValueError("CheckpointRecorded progression mismatch")
    return {
        **state,
        "latest_checkpoint": payload,
        "checkpoints": [*state.get("checkpoints", []), payload],
        "version": event["stream_version"],
    }


def reduce_operation(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce ordered C2 operator request and confirmation facts on an Attempt."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    if not state or payload.get("attempt_id") != state.get("attempt_id"):
        raise ValueError(f"{event_type} Attempt relation mismatch")
    if event_type == "PauseRequested":
        if state.get("status") != "running" or state.get("operation_state") in {
            "pause_requested",
            "stop_requested",
        }:
            raise ValueError("PauseRequested requires running Attempt without pending control")
        return {
            **state,
            "operation_state": "pause_requested",
            "pause_request": payload,
            "version": event["stream_version"],
        }
    if event_type == "PauseConfirmed":
        if state.get("status") != "running" or state.get("operation_state") != "pause_requested":
            raise ValueError("PauseConfirmed requires pending pause request")
        return {
            **state,
            "status": "paused",
            "operation_state": "pause_confirmed",
            "pause_confirmation": payload,
            "version": event["stream_version"],
        }
    if event_type == "ResumeRequested":
        if (
            state.get("status") != "paused"
            or state.get("operation_state") != "pause_confirmed"
            or payload.get("compatibility") != "compatible"
        ):
            raise ValueError("ResumeRequested requires confirmed compatible pause")
        return {
            **state,
            "operation_state": "resume_requested",
            "resume_request": payload,
            "version": event["stream_version"],
        }
    if event_type == "StopRequested":
        if state.get("status") not in {"running", "paused"}:
            raise ValueError("StopRequested requires active or paused Attempt")
        return {
            **state,
            "status": "stopping",
            "operation_state": "stop_requested",
            "stop_request": payload,
            "version": event["stream_version"],
        }
    if event_type == "StopConfirmed":
        if state.get("status") != "stopping" or state.get("operation_state") != "stop_requested":
            raise ValueError("StopConfirmed requires pending stop request")
        if payload.get("stop_record_id") != state.get("stop_request", {}).get("stop_record_id"):
            raise ValueError("StopConfirmed record mismatch")
        return {
            **state,
            "operation_state": "stop_confirmed",
            "stop_confirmation": payload,
            "version": event["stream_version"],
        }
    raise ValueError(f"illegal operator transition: {state.get('status')} -> {event_type}")


def reduce_recovery(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Attach a durable orphan-quarantine record without rewriting Attempt history."""
    validate_exact_lifecycle_envelope(event)
    payload = event["payload"]
    if event["event_type"] != "OrphanQuarantined" or payload.get("attempt_id") != state.get("attempt_id"):
        raise ValueError("OrphanQuarantined Attempt relation mismatch")
    return {
        **state,
        "recovery_status": "quarantined",
        "quarantine": payload,
        "version": event["stream_version"],
    }


def reduce_review(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Project the exact Review lifecycle without conferring Decision authority."""
    validate_exact_lifecycle_envelope(event)
    payload = event["payload"]
    event_type = event["event_type"]
    if event_type == "ReviewRequested":
        if state or payload["new_review_id"] != event["stream_id"]:
            raise ValueError("ReviewRequested requires an empty bound Review stream")
        if not payload["subject_ids"] or len(payload["subject_ids"]) != len(payload["subject_hashes"]):
            raise ValueError("ReviewRequested subject identities and hashes mismatch")
        return {
            "review_id": event["stream_id"],
            "status": "requested",
            "request": deepcopy(payload),
            "requester_actor_id": event["actor_id"],
            "version": event["stream_version"],
        }
    if not state or payload.get("review_id") != state.get("review_id"):
        raise ValueError(f"{event_type} requires its exact current Review")
    status = state.get("status")
    if event_type == "ReviewAssigned" and status == "requested":
        if payload["reviewer_actor_id"] == state.get("requester_actor_id") or not payload["independence_evidence_refs"]:
            raise ValueError("ReviewAssigned independence binding mismatch")
        return {
            **state,
            "status": "assigned",
            "assignment": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "ReviewStarted" and status == "assigned":
        if (
            event["actor_id"] != state["assignment"]["reviewer_actor_id"]
            or payload["unchanged_subject_sha256"] not in state["request"]["subject_hashes"]
        ):
            raise ValueError("ReviewStarted subject hash mismatch")
        return {
            **state,
            "status": "in_review",
            "subject_sha256": payload["unchanged_subject_sha256"],
            "start": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "ReviewVerdictRecorded" and status == "in_review":
        assignment = state["assignment"]
        if (
            payload["reviewer_actor_id"] != event["actor_id"]
            or payload["reviewer_actor_id"] != assignment["reviewer_actor_id"]
            or payload["unchanged_subject_sha256"] != state["subject_sha256"]
            or payload["computed_independence_grade"] != assignment["computed_independence_grade"]
        ):
            raise ValueError("ReviewVerdictRecorded reviewer or subject binding mismatch")
        return {
            **state,
            "status": "verdict_recorded",
            "verdict": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "ReviewChangesRequested" and status == "verdict_recorded":
        if not payload["policy_evaluation_refs"] or not payload["conditions"]:
            raise ValueError("ReviewChangesRequested policy evidence is incomplete")
        return {
            **state,
            "status": "changes_requested",
            "changes_request": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "ReviewSatisfied" and status in {"verdict_recorded", "changes_requested"}:
        if payload["prior_review_state"] != status or not payload["policy_evaluation_refs"]:
            raise ValueError("ReviewSatisfied prior-state binding mismatch")
        if status == "changes_requested" and payload.get("unchanged_subject_sha256") != state.get("subject_sha256"):
            raise ValueError("ReviewSatisfied changed subject hash mismatch")
        return {
            **state,
            "status": "satisfied",
            "satisfaction": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "ReviewWithdrawn" and status not in {"satisfied", "withdrawn", "superseded"}:
        return {
            **state,
            "status": "withdrawn",
            "withdrawal": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "ReviewSuperseded" and status not in {"satisfied", "withdrawn", "superseded"}:
        if payload["unchanged_subject_sha256"] != (
            state.get("subject_sha256")
            or (state["request"]["subject_hashes"][0] if len(state["request"]["subject_hashes"]) == 1 else None)
        ):
            raise ValueError("ReviewSuperseded subject hash mismatch")
        return {
            **state,
            "status": "superseded",
            "supersession": deepcopy(payload),
            "version": event["stream_version"],
        }
    raise ValueError(f"illegal review transition: {status} -> {event_type}")


def reduce_decision(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Project Decision history while keeping Review evidence non-authoritative."""
    validate_exact_lifecycle_envelope(event)
    payload = event["payload"]
    event_type = event["event_type"]
    if event_type == "DecisionProposed":
        if state or payload["new_decision_id"] != event["stream_id"] or payload["decision_revision"] != 1:
            raise ValueError("DecisionProposed requires an empty revision-1 Decision stream")
        return {
            **deepcopy(payload),
            "decision_id": event["stream_id"],
            "proposer_actor_id": event["actor_id"],
            "status": "proposed",
            "history": [{"event_id": event["event_id"], "event_type": event_type, "revision": 1}],
            "version": event["stream_version"],
        }
    if not state or payload.get("decision_id") != state.get("decision_id"):
        raise ValueError(f"{event_type} requires its exact current Decision")
    status = state.get("status")
    revision = int(state.get("decision_revision", 1))
    updated = deepcopy(state)
    if event_type == "DecisionReviewRequested" and status == "proposed":
        if payload["decision_revision"] != revision:
            raise ValueError("DecisionReviewRequested revision mismatch")
        updated.update({"status": "under_review", "review_request": deepcopy(payload)})
    elif event_type == "DecisionResolved" and status == "under_review":
        if payload["decision_revision"] != revision:
            raise ValueError("DecisionResolved revision mismatch")
        updated.update({**deepcopy(payload), "status": "resolved"})
    elif event_type == "DecisionRejected" and status in {"proposed", "under_review"}:
        if payload["decision_revision"] != revision:
            raise ValueError("DecisionRejected revision mismatch")
        updated.update({"status": "rejected", "rejection": deepcopy(payload)})
    elif event_type == "DecisionExpired" and status in {"proposed", "under_review"}:
        if payload["decision_revision"] != revision:
            raise ValueError("DecisionExpired revision mismatch")
        updated.update({"status": "expired", "expiry": deepcopy(payload)})
    elif event_type == "DecisionSuperseded" and status in {"proposed", "under_review"}:
        if payload["decision_revision"] != revision:
            raise ValueError("DecisionSuperseded revision mismatch")
        updated.update({"status": "superseded", "supersession": deepcopy(payload)})
    elif event_type == "DecisionAmendmentProposed" and status == "resolved":
        if payload["decision_revision"] != revision + 1:
            raise ValueError("DecisionAmendmentProposed revision mismatch")
        updated.update(
            {
                "status": "proposed",
                "decision_revision": payload["decision_revision"],
                "amendment": deepcopy(payload),
            }
        )
    else:
        raise ValueError(f"illegal decision transition: {status} -> {event_type}")
    updated["history"] = [
        *state.get("history", []),
        {"event_id": event["event_id"], "event_type": event_type, "revision": updated["decision_revision"]},
    ]
    updated["version"] = event["stream_version"]
    return updated


def reduce_rule_evaluation(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Project one immutable rule evaluation without converting it to a Decision."""
    validate_exact_lifecycle_envelope(event)
    payload = event["payload"]
    if (
        state
        or event["event_type"] != "RuleEvaluationRecorded"
        or payload["new_rule_evaluation_id"] != event["stream_id"]
        or len(payload["input_ids"]) != len(payload["input_hashes"])
    ):
        raise ValueError("RuleEvaluationRecorded requires one empty stream and paired exact inputs")
    return {
        **deepcopy(payload),
        "rule_evaluation_id": event["stream_id"],
        "status": "recorded",
        "version": event["stream_version"],
    }


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
    if event_type == "ScopeCompleted":
        if not state or state.get("status") != "open":
            raise ValueError("ScopeCompleted requires an open scope")
        revision = int(payload["revision"])
        if (
            payload["scope_definition_id"] != state["scope_definition_id"]
            or revision != state["current_revision"]
            or payload["completion_predicate"] != state["definition"].get("completion_predicate")
        ):
            raise ValueError("ScopeCompleted revision or predicate binding mismatch")
        if not has_unique_member_ids(payload["member_dispositions"]):
            raise ValueError("ScopeCompleted duplicate member disposition")
        expected_members = {
            str(member["member_id"]): str(member["member_kind"]) for member in state["definition"]["members"]
        }
        observed_members = {
            str(member["member_id"]): str(member["member_kind"]) for member in payload["member_dispositions"]
        }
        if observed_members != expected_members:
            raise ValueError("ScopeCompleted member disposition mismatch")
        completion = deepcopy(payload)
        history = dict(state["revision_history"])
        current = dict(history[str(revision)])
        current.update({"status": "complete", "completion": completion})
        history[str(revision)] = current
        return {
            **state,
            "status": "complete",
            "completion": completion,
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


def reduce_artefact(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce the exact P6 artefact-authority lifecycle without rewriting history."""
    validate_exact_lifecycle_envelope(event)
    event_type = event["event_type"]
    payload = event["payload"]
    stream_id = event["stream_id"]
    if event_type == "ArtefactRegistered":
        manifest = payload.get("manifest") if isinstance(payload, dict) else None
        authority = manifest.get("authority") if isinstance(manifest, dict) else None
        if (
            state
            or not isinstance(authority, dict)
            or payload.get("new_artefact_id") != stream_id
            or manifest.get("artefact_id") != stream_id
            or authority.get("use_authority") != "candidate"
            or authority.get("regenerability") == "regenerable_verified"
        ):
            raise ValueError("invalid artefact registration transition")
        return {
            "artefact_id": stream_id,
            "manifest": deepcopy(manifest),
            "content_sha256": manifest.get("content_sha256"),
            "availability": authority.get("availability"),
            "regenerability": authority.get("regenerability"),
            "integrity": authority.get("integrity"),
            "structural_validation": authority.get("structural_validation"),
            "scientific_reviews": [],
            "use_authority": "candidate",
            "late_adoptions": [],
            "version": event["stream_version"],
        }
    if not state or payload.get("artefact_id") != stream_id:
        raise ValueError(f"{event_type} artefact subject binding mismatch")
    if state.get("use_authority") in {"rejected", "superseded"}:
        raise ValueError("terminal artefact authority cannot transition")

    dimension_events = {
        "ArtefactAvailabilityRecorded": "availability",
        "ArtefactRegenerabilityRecorded": "regenerability",
        "ArtefactIntegrityRecorded": "integrity",
        "StructuralValidationRecorded": "structural_validation",
    }
    if event_type in dimension_events:
        dimension = dimension_events[event_type]
        if payload.get("subject_sha256") != state.get("content_sha256"):
            raise ValueError("artefact dimension subject hash mismatch")
        evidence = list(state.get("authority_dimension_evidence", []))
        evidence.append(
            {
                "dimension": dimension,
                "value": payload[dimension],
                "evidence_refs": list(payload["evidence_refs"]),
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
            }
        )
        return {
            **state,
            dimension: payload[dimension],
            "authority_dimension_evidence": evidence,
            "version": event["stream_version"],
        }
    if event_type == "ScientificReviewRecorded":
        if payload.get("subject_sha256") != state.get("content_sha256"):
            raise ValueError("scientific review subject hash mismatch")
        reviews = list(state.get("scientific_reviews", []))
        if any(review.get("review_id") == payload.get("review_id") for review in reviews):
            raise ValueError("duplicate scientific review identity")
        reviews.append(
            {
                **deepcopy(payload),
                "reviewer_actor_id": event["actor_id"],
                "stream_version": event["stream_version"],
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
                "recorded_at": event["recorded_at"],
            }
        )
        return {**state, "scientific_reviews": reviews, "version": event["stream_version"]}
    if event_type == "ArtefactUseAuthoritySet":
        if payload.get("subject_sha256") != state.get("content_sha256") or payload.get("use_authority") == "candidate":
            raise ValueError("invalid artefact use-authority transition")
        return {
            **state,
            "use_authority": payload["use_authority"],
            "consumer_predicate": payload["consumer_predicate"],
            "authority_evidence_refs": list(payload["evidence_refs"]),
            "authority_event_id": event["event_id"],
            "authority_event_hash": event["event_hash"],
            "version": event["stream_version"],
        }
    if event_type == "ArtefactSuperseded":
        if payload.get("replacement_artefact_id") == stream_id:
            raise ValueError("artefact cannot supersede itself")
        return {
            **state,
            "use_authority": "superseded",
            "supersession": deepcopy(payload),
            "version": event["stream_version"],
        }
    if event_type == "LateArtefactAdopted":
        if payload.get("artefact_sha256") != state.get("content_sha256"):
            raise ValueError("late adoption subject hash mismatch")
        adoptions = list(state.get("late_adoptions", []))
        if adoptions:
            raise ValueError("late artefact adoption is already recorded")
        adoptions.append({**deepcopy(payload), "event_id": event["event_id"], "event_hash": event["event_hash"]})
        return {**state, "late_adoptions": adoptions, "version": event["stream_version"]}
    raise ValueError(f"illegal artefact transition: {state.get('use_authority')} -> {event_type}")


def reduce_backup(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Project one immutable ``BackupCreated`` snapshot on its project stream."""
    validate_exact_lifecycle_envelope(event)
    if event.get("event_type") != "BackupCreated" or event.get("schema_id") != "ars://core/event/BackupCreated":
        raise ValueError("reduce_backup requires the exact BackupCreated event")

    payload = event["payload"]
    project_id = payload["project_id"]
    if event.get("project_id") != project_id or event.get("stream_id") != project_id:
        raise ValueError("BackupCreated project stream identity mismatch")

    tail_position = payload["canonical_tail_position"]
    tail_hash = payload["canonical_tail_sha256"]
    if (
        type(tail_position) is not int
        or event.get("global_position") != tail_position + 1
        or event.get("previous_event_hash") != tail_hash
    ):
        raise ValueError("BackupCreated pre-event tail mismatch")

    replay_start = payload["replay_start_position"]
    replay_end = payload["replay_end_position"]
    if (
        type(replay_start) is not int
        or type(replay_end) is not int
        or replay_start < 0
        or replay_start > replay_end
        or replay_end != tail_position
    ):
        raise ValueError("BackupCreated replay range must end at the pre-event tail")

    external_artefacts = payload["external_artefacts"]
    if not isinstance(external_artefacts, list) or any(not isinstance(item, dict) for item in external_artefacts):
        raise ValueError("BackupCreated external artefacts must be records")
    artefact_ids = [item.get("artefact_id") for item in external_artefacts]
    if any(not isinstance(artefact_id, str) for artefact_id in artefact_ids) or len(artefact_ids) != len(
        set(artefact_ids)
    ):
        raise ValueError("BackupCreated requires unique external artefacts")
    if any(item.get("availability") != "available" for item in external_artefacts):
        raise ValueError("BackupCreated requires available external artefacts")

    store_identity = payload["store_identity"]
    if state and (
        state.get("project_id") != project_id
        or state.get("store_identity") != store_identity
        or not isinstance(state.get("snapshots"), dict)
    ):
        raise ValueError("BackupCreated immutable project-store binding mismatch")
    snapshots = deepcopy(state.get("snapshots", {}))
    snapshot_id = payload["snapshot_id"]
    if snapshot_id in snapshots:
        raise ValueError("BackupCreated snapshot identity is already projected")
    snapshots[snapshot_id] = {
        **deepcopy(payload),
        "event_id": event["event_id"],
        "event_hash": event["event_hash"],
        "event_position": event["global_position"],
        "stream_version": event["stream_version"],
        "command_id": event["command_id"],
    }
    return {
        "project_id": project_id,
        "store_identity": store_identity,
        "snapshots": snapshots,
        "latest_snapshot_id": snapshot_id,
        "version": event["stream_version"],
    }


def replay_control_plane(events: Iterable[dict[str, Any]]) -> ControlPlaneState:
    attempts: set[str] = set()
    stream_states: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] in {
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
        } or (event["event_type"] == "PartialOutcomeRecorded" and event.get("command_type") == "ClosePartial"):
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
            "ScopeCompleted",
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
        elif event["event_type"] in {"BlockerRecorded", "BlockerResolved"}:
            stream_id = event["stream_id"]
            stream_states[stream_id] = reduce_blocker(
                stream_states.get(stream_id, {}),
                event,
            )
        elif event["event_type"] in {
            "DispatchIssued",
            "DispatchDelivered",
            "DispatchAcknowledged",
            "DispatchExpired",
            "DispatchWithdrawn",
            "DispatchClaimed",
            "DispatchFulfilled",
        }:
            stream_states[event["stream_id"]] = reduce_dispatch(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] in {
            "LeaseGranted",
            "LeaseRenewed",
            "LeaseReleased",
            "LeaseExpired",
            "LeaseRevoked",
            "HeartbeatRecorded",
        }:
            stream_states[event["stream_id"]] = reduce_lease(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] in {
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
            attempt_id = event["stream_id"]
            stream_states[attempt_id] = reduce_attempt(
                stream_states.get(event["stream_id"], {}),
                event,
            )
            if stream_states[attempt_id].get("status") in _ATTEMPT_TERMINAL:
                attempts.discard(attempt_id)
            else:
                attempts.add(attempt_id)
        elif event["event_type"] == "CheckpointRecorded":
            stream_states[event["stream_id"]] = reduce_checkpoint(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] in {
            "PauseRequested",
            "PauseConfirmed",
            "StopRequested",
            "StopConfirmed",
            "ResumeRequested",
        }:
            stream_states[event["stream_id"]] = reduce_operation(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] == "OrphanQuarantined":
            stream_states[event["stream_id"]] = reduce_recovery(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] in {
            "ReviewRequested",
            "ReviewAssigned",
            "ReviewStarted",
            "ReviewVerdictRecorded",
            "ReviewChangesRequested",
            "ReviewSatisfied",
            "ReviewWithdrawn",
            "ReviewSuperseded",
        }:
            stream_states[event["stream_id"]] = reduce_review(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] in {
            "DecisionProposed",
            "DecisionReviewRequested",
            "DecisionResolved",
            "DecisionRejected",
            "DecisionExpired",
            "DecisionSuperseded",
            "DecisionAmendmentProposed",
        }:
            stream_states[event["stream_id"]] = reduce_decision(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] == "RuleEvaluationRecorded":
            stream_states[event["stream_id"]] = reduce_rule_evaluation(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] in {"ResourceGrantRequested", "ResourcesReleased"}:
            stream_states[event["stream_id"]] = reduce_resource(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        elif event["event_type"] == "BackupCreated":
            stream_states[event["stream_id"]] = reduce_backup(
                stream_states.get(event["stream_id"], {}),
                event,
            )
        else:
            raise ValueError(f"unsupported event type: {event['event_type']}")
    return ControlPlaneState(frozenset(attempts), stream_states)
