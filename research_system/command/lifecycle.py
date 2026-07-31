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
    """Validate provenance carried by an exact lifecycle event.

    Args:
        event: Recorded event envelope to inspect.

    Returns:
        The originating command type for an exact lifecycle event, or ``None``
        for an event outside the exact lifecycle bindings.

    Raises:
        ValueError: If an exact event's type, schema identity, command
            provenance, or canonical payload hash is inconsistent.
    """
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
    """Check a mapping's recorded hash against its canonical unsigned content.

    Args:
        value: Mapping whose ``content_sha256`` field records the expected hash.

    Returns:
        Whether the recorded hash equals the canonical hash after removing the
        hash field, or ``False`` when the value cannot be hashed canonically.
    """
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
    """Return changed Task definition fields excluding revision metadata.

    Args:
        source: Current immutable Task definition.
        replacement: Proposed replacement Task definition.

    Returns:
        Names of fields whose values differ, excluding ``revision`` and
        ``content_sha256``.
    """
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
    """Apply a typed ScopeDefinition member delta to committed membership.

    Args:
        current_members: Materialized members of the current immutable
            ScopeDefinition revision.
        member_changes: Typed additions, disposition changes, or removals.

    Returns:
        The materialized member list with existing order preserved and new
        members appended.

    Raises:
        ValueError: If a removal names an absent member, an existing member is
            named under the wrong kind, or the resulting membership is
            semantically unchanged.
    """
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
    """Return whether every member record has a unique member identity.

    Args:
        records: Member or member-change records to inspect.

    Returns:
        Whether no two records carry the same ``member_id`` value.
    """
    member_ids = [record.get("member_id") for record in records]
    return len(member_ids) == len(set(member_ids))
