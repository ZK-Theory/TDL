from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex


EXACT_LIFECYCLE_BINDINGS = {
    "ars://core/event/ScopeDefinitionCreated": (
        "ScopeDefinitionCreated",
        "CreateScopeDefinition",
        "ars://core/command/CreateScopeDefinition",
    ),
    "ars://core/event/ScopeDefinitionAmended": (
        "ScopeDefinitionAmended",
        "AmendScopeDefinition",
        "ars://core/command/AmendScopeDefinition",
    ),
    "ars://core/event/ScopeDefinitionSuperseded": (
        "ScopeDefinitionSuperseded",
        "SupersedeScopeDefinition",
        "ars://core/command/SupersedeScopeDefinition",
    ),
    "ars://core/event/TaskCreated": (
        "TaskCreated",
        "CreateTask",
        "ars://core/command/CreateTask",
    ),
    "ars://core/event/TaskAmended": (
        "TaskAmended",
        "AmendTask",
        "ars://core/command/AmendTask",
    ),
    "ars://core/event/TaskSuperseded": (
        "TaskSuperseded",
        "SupersedeTask",
        "ars://core/command/SupersedeTask",
    ),
}


def validate_exact_lifecycle_envelope(
    event: Mapping[str, Any],
) -> str | None:
    binding = EXACT_LIFECYCLE_BINDINGS.get(str(event.get("schema_id", "")))
    if binding is None:
        return None
    event_type, command_type, command_schema_id = binding
    payload = event.get("payload")
    if (
        event.get("event_type") != event_type
        or event.get("schema_version") != "1.0.0"
        or event.get("command_type") != command_type
        or event.get("command_schema_id") != command_schema_id
        or event.get("command_schema_version") != "1.0.0"
        or event.get("command_payload_hash") != sha256_hex(canonical_bytes(payload))
    ):
        raise ValueError("exact lifecycle event provenance mismatch")
    return command_type


def content_hash_matches(value: Mapping[str, Any]) -> bool:
    recorded = value.get("content_sha256")
    if not isinstance(recorded, str):
        return False
    unsigned = dict(value)
    unsigned.pop("content_sha256", None)
    try:
        return recorded == sha256_hex(canonical_bytes(unsigned))
    except (TypeError, ValueError):
        return False


def changed_task_fields(
    source: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> set[str]:
    metadata = {"revision", "content_sha256"}
    return {
        field
        for field in source.keys() | replacement.keys()
        if field not in metadata and source.get(field) != replacement.get(field)
    }


def materialize_scope_member_changes(
    current_members: Iterable[Mapping[str, Any]],
    member_changes: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    members = [dict(member) for member in current_members]
    original_members = [dict(member) for member in members]
    member_indexes = {str(member["member_id"]): index for index, member in enumerate(members)}
    removed: set[str] = set()
    additions: list[dict[str, Any]] = []

    for change in member_changes:
        member_id = str(change["member_id"])
        member_kind = str(change["member_kind"])
        disposition = str(change["disposition"])
        index = member_indexes.get(member_id)
        if index is None:
            if disposition == "removed_by_amendment":
                raise ValueError("ScopeDefinitionAmended member change refers to absent member")
            additions.append(
                {
                    "member_id": member_id,
                    "member_kind": member_kind,
                    "required_disposition": disposition,
                }
            )
            continue

        if str(members[index]["member_kind"]) != member_kind:
            raise ValueError("ScopeDefinitionAmended member kind mismatch")
        if disposition == "removed_by_amendment":
            removed.add(member_id)
        else:
            members[index] = {
                "member_id": member_id,
                "member_kind": member_kind,
                "required_disposition": disposition,
            }

    materialized = [member for member in members if str(member["member_id"]) not in removed]
    materialized.extend(additions)
    if materialized == original_members:
        raise ValueError("ScopeDefinitionAmended has no semantic member delta")
    return materialized


def has_unique_member_ids(records: Iterable[Mapping[str, Any]]) -> bool:
    member_ids = [record.get("member_id") for record in records]
    return len(member_ids) == len(set(member_ids))
