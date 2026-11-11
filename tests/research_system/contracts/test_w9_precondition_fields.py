# Research context: docs/plans/agentic-research-system/implementation/gate7-intake-deferrals.md (§2 row 37; WP9.3-2)
# Purpose: every catalogue precondition that says a payload lists, carries or names a datum maps to a field of the
# row's record schema or of one of its ordered events; LR-016's ownership list is the one exception, owner point E.
"""The precondition-to-field table (Gate 7+ intake §2, observation
``2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema``).

LR-016's precondition says "the proposal lists ... every legacy-ownership-transitioned record", but the acceptance
schema is closed and has no field for them (WP9.3 note §10.5). That was found by reading, after the catalogue was
accepted. This test finds any such precondition mechanically: each one that says a payload lists, carries or names a
datum is mapped to a field the row's schemas actually hold. LR-016's is the one exception, read as "derived" by owner
point E (P-081 item 5). It lives in its own file because the O-8 acceptance envelope binds
``test_w9_expected_catalogue.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = REPO_ROOT / ".research-system/evals/expected/w9-legacy-integration-v1.json"
W9_SCHEMAS = REPO_ROOT / ".research-system/schemas/contracts/w9"
CORE_EVENTS = REPO_ROOT / ".research-system/schemas/core/events"
CLAIM = re.compile(r"\b(lists|carries|names)\b", re.IGNORECASE)
G5_REVIEW = ("DecisionResolved", "considered_review_ids")  # G5's "the review it names"

# (row, the precondition's opening words) -> the schema field that holds the datum: ("record", field) for the row's
# record schema, or (event type, field) for a W2 event's schema.
TABLE: dict[tuple[str, str], tuple[str, str]] = {
    ("LR-002", "the new envelope names"): ("record", "revision_envelope_identity"),
    **{
        (row, "G5: the Decision"): G5_REVIEW
        for row in ("LR-005", "LR-010", "LR-020", "LR-029", "LR-034", "LR-044", "LR-049", "LR-054", "LR-055", "LR-060")
    },
    ("LR-026", "the named reviewer"): ("ReviewRequested", "reviewer_capability"),
    ("LR-039", "every adoption_ref names"): ("record", "adoption_ref"),
}
# Owner point E (P-081 item 5): read as "the proposal determines"; replay derives the list, stores it at LR-016 and
# requires it at LR-020 (note §10.5). No schema field holds it, by design.
EXCEPTIONS = {("LR-016", "the proposal lists"): "derived, not listed (P-081 item 5; note §10.5)"}


def _fields(schema: Any) -> set[str]:
    """Every property name anywhere in a schema, its ``$defs`` included."""
    names: set[str] = set()
    if isinstance(schema, dict):
        names.update(schema.get("properties", {}))
        for value in schema.values():
            names |= _fields(value)
    elif isinstance(schema, list):
        for value in schema:
            names |= _fields(value)
    return names


def _schema_fields(row: dict[str, Any], where: str) -> set[str]:
    if where == "record":
        name = row["record_schema_id"].removeprefix("ars://legacy/")
        return _fields(json.loads((W9_SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8")))
    events = {entry["event"] for entry in row["ordered_events"]}
    if f"W2:{where}" not in events:
        return set()
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", where).lower()
    return _fields(json.loads((CORE_EVENTS / f"{snake}.schema.json").read_text(encoding="utf-8")))


def _unmapped(table: dict[tuple[str, str], tuple[str, str]], exceptions: dict[tuple[str, str], str]) -> list[str]:
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    problems = []
    for row in catalogue["owner_contract_rows"]:
        for text in row["preconditions"]:
            if not CLAIM.search(text):
                continue
            keys = [key for key in (*table, *exceptions) if key[0] == row["owner_row_id"] and text.startswith(key[1])]
            if not keys:
                problems.append(f"{row['owner_row_id']}: unmapped precondition: {text[:60]}")
                continue
            for key in keys:
                if key in exceptions:
                    continue
                where, field = table[key]
                if field not in _schema_fields(row, where):
                    problems.append(f"{row['owner_row_id']}: {where} has no field {field}")
    return problems


def test_every_lists_carries_or_names_precondition_maps_to_a_field() -> None:
    assert _unmapped(TABLE, EXCEPTIONS) == []


def test_lr016_as_accepted_fails_without_owner_point_es_exception() -> None:
    """The control (intake §2 row 37): LR-016's precondition, as accepted at 7979e85a, maps to no field."""
    assert _unmapped(TABLE, {}) == [
        "LR-016: unmapped precondition: the proposal lists, with pre-assigned IDs and full content, "
    ]


def test_a_mapping_to_a_field_the_schema_lacks_fails() -> None:
    table = {**TABLE, ("LR-002", "the new envelope names"): ("record", "ownership_records")}
    assert _unmapped(table, EXCEPTIONS) == ["LR-002: record has no field ownership_records"]


def test_a_w2_event_the_row_does_not_emit_is_not_a_field_source() -> None:
    table = {**TABLE, ("LR-026", "the named reviewer"): ("DecisionResolved", "considered_review_ids")}
    assert _unmapped(table, EXCEPTIONS) == ["LR-026: DecisionResolved has no field considered_review_ids"]


def test_the_table_covers_exactly_the_matching_preconditions() -> None:
    """No stale entry: every table key names a precondition the catalogue holds."""
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    present = {
        (row["owner_row_id"], key[1])
        for row in catalogue["owner_contract_rows"]
        for key in (*TABLE, *EXCEPTIONS)
        if key[0] == row["owner_row_id"] and any(text.startswith(key[1]) for text in row["preconditions"])
    }
    assert present == set(TABLE) | set(EXCEPTIONS)
