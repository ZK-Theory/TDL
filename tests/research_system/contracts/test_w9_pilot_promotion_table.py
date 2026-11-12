# Research context: docs/plans/agentic-research-system/implementation/gate7-intake-deferrals.md (§2 row 36; WP9.3-2)
# Purpose: W9 §12.3's fixture-to-row assignments as an owned table, checked against every catalogue row's parsed
# pilot_promotion_fixtures, and the WP9.3-2 reducer's LR-020 constants bound to the parsed row.
"""The ``pilot_promotion`` table (Gate 7+ intake §2, observation ``2026-10-29-note-cited-a-truncated-row-range-and-built-
an-owner-point-on-it``).

The WP9.3 note's revision 1 read LR-020's fixtures from a line range that stopped early, and listed three of seven.
This test reads the set from the parsed catalogue, never from a line range, and holds the expected assignment as an
owned table built from W9 §12.3 (``design/09-migration-compatibility-and-pilot.md`` §12.3), one category per row. It
lives in its own file because the O-8 acceptance envelope binds ``test_w9_expected_catalogue.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.legacy.replay import reducers

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = REPO_ROOT / ".research-system/evals/expected/w9-legacy-integration-v1.json"

# W9 §12.3: "S-007 stale review hash | Every review". The catalogue applies it to every review request, verdict and
# review-backed Decision proposal row.
REVIEW_ROWS = (
    "LR-007 LR-008 LR-009 LR-012 LR-013 LR-017 LR-018 LR-019 LR-026 LR-027 LR-028 LR-031 LR-032 LR-033 "
    "LR-041 LR-042 LR-043 LR-046 LR-047 LR-048 LR-051 LR-052 LR-053 LR-057 LR-058 LR-059"
).split()
TDA_PACK = "F-038"  # "Any item using the TDA pack's lanes"
OWNED_TABLE: dict[str, tuple[tuple[str, str | None], ...]] = {
    **dict.fromkeys(REVIEW_ROWS, (("S-007", None),)),
    # LR-020, closed-reference acceptance: F-017 (sensitivity and comparison files), F-018 and F-037 (every
    # result-family observation), F-023 (every import), S-005 (two results compete), S-014 (re-run after each
    # batch), F-038 (the TDA pack).
    "LR-020": (
        ("F-017", "an item is a sensitivity or comparison file"),
        ("F-018", None),
        ("F-023", None),
        ("F-037", None),
        ("S-005", "two results compete for one object"),
        ("S-014", None),
        (TDA_PACK, "an item uses the TDA pack's lanes"),
    ),
    # LR-029, adoption: F-015 (statistical families), F-019 (adoption for a claim), S-017, F-038.
    "LR-029": (
        ("F-015", "the adopted family is statistical"),
        ("F-019", "the intended use is evidence for a claim"),
        ("S-017", None),
        (TDA_PACK, "the family uses the TDA pack's lanes"),
    ),
    # LR-044, source inventory: F-018, F-023, F-037.
    "LR-044": (("F-018", None), ("F-023", None), ("F-037", None)),
    # LR-054 and LR-055, paper-root transitions: F-006, F-019, F-037 (and F-023 for the import at LR-054), F-038.
    "LR-054": (
        ("F-006", None),
        ("F-019", None),
        ("F-023", None),
        ("F-037", None),
        (TDA_PACK, "the root's families use the TDA pack's lanes"),
    ),
    "LR-055": (
        ("F-006", None),
        ("F-019", None),
        ("F-037", None),
        (TDA_PACK, "the root's families use the TDA pack's lanes"),
    ),
    # LR-060, supersession: "S-015 supersession cycle | Every legacy-record-supersession".
    "LR-060": (("S-015", None),),
}


def _parsed() -> dict[str, tuple[tuple[str, str | None], ...]]:
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return {
        row["owner_row_id"]: tuple((entry["fixture_id"], entry["when"]) for entry in row["pilot_promotion_fixtures"])
        for row in catalogue["owner_contract_rows"]
        if row["pilot_promotion_fixtures"]
    }


def _differences(table: dict[str, tuple[tuple[str, str | None], ...]]) -> list[str]:
    parsed = _parsed()
    return [row for row in sorted(set(parsed) | set(table)) if parsed.get(row) != table.get(row)]


def test_every_catalogue_rows_pilot_promotion_fixtures_equal_the_owned_table() -> None:
    assert _differences(OWNED_TABLE) == []


def test_the_three_fixture_reading_of_lr020_fails() -> None:
    """The control (intake §2 row 36): revision 1's three-fixture reading, F-017, F-018 and F-023, is caught."""
    three = (("F-017", "an item is a sensitivity or comparison file"), ("F-018", None), ("F-023", None))
    assert _differences({**OWNED_TABLE, "LR-020": three}) == ["LR-020"]


@pytest.mark.parametrize("row", ["LR-020", "LR-007"])
def test_dropping_any_row_from_the_owned_table_fails(row: str) -> None:
    table = dict(OWNED_TABLE)
    del table[row]
    assert _differences(table) == [row]


def test_the_acceptance_replay_constants_are_lr020s_parsed_row() -> None:
    """WP9.3-2's reducer holds LR-020's set as constants (note §10.2); they equal the parsed row, split by condition."""
    lr020 = _parsed()["LR-020"]
    assert reducers.UNCONDITIONAL_FIXTURES == tuple(fixture for fixture, when in lr020 if when is None)
    assert reducers.CONDITIONAL_FIXTURES == tuple(fixture for fixture, when in lr020 if when is not None)
    assert reducers.PILOT_FIXTURES == {fixture for fixture, _ in lr020}
