# Research context: docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md (WP9.0, P-065)
# Purpose: synthetic vectors for tools/w9_segmentation.py; each expected span is stated by line range and its hash is
# recomputed here from those lines, independently of the tool's own line splitting.
"""Vectors for the W9 segmentation contract ``w9-segmentation/1.0.0`` (contract §7).

No legacy bytes are used. Every vector states its expected rows as (kind, first line, last line, anchor text,
blocker reason). The expected SHA-256, start byte and byte length are recomputed from the vector's own bytes.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import w9_segmentation as seg  # noqa: E402

Expected = tuple[str, int, int, str | None, str | None]


def _lines(data: bytes) -> list[bytes]:
    """Split on LF only, keeping terminators; written apart from the tool so the vectors check it."""
    parts = data.split(b"\n")
    out = [part + b"\n" for part in parts[:-1]]
    if parts[-1]:
        out.append(parts[-1])
    return out


def _check(result: dict[str, Any], data: bytes, expected: list[Expected]) -> None:
    lines = _lines(data)
    rows = result["rows"]
    got = [
        (r["row_kind"], r["start_line"], r["start_line"] + r["line_count"] - 1, r["anchor_text"], r["blocker_reason"])
        for r in rows
    ]
    assert got == expected
    for row, (_, first, last, _, _) in zip(rows, expected, strict=True):
        span = b"".join(lines[first - 1 : last])
        assert row["raw_row_sha256"] == hashlib.sha256(span).hexdigest()
        assert row["byte_length"] == len(span)
        assert row["start_byte"] == sum(len(line) for line in lines[: first - 1])
    assert [r["row_ordinal"] for r in rows] == list(range(1, len(rows) + 1))
    assert result["segmentation_contract"] == "w9-segmentation/1.0.0"
    assert result["file_sha256"] == hashlib.sha256(data).hexdigest()


# --- Lines, terminators, BOM -------------------------------------------------------------------------------------


def test_lf_sections_trailing_blank_and_rule_are_structural() -> None:
    data = b"# Title\n\n## a\nbody\n\n---\n## b\nx\n"
    result = seg.segment(data, "heading_section", level=2, region=(3, 8))
    _check(result, data, [("item", 3, 4, "a", None), ("item", 7, 8, "b", None)])
    assert result["file_facts"] == {
        "line_ending": "LF",
        "ends_with_terminator": True,
        "has_utf8_bom": False,
        "line_count": 8,
    }


def test_crlf_blank_lines_are_blank_and_anchor_text_has_no_cr() -> None:
    data = b"## a\r\nbody\r\n\r\n---\r\n## b\r\nx\r\n"
    result = seg.segment(data, "heading_section", level=2)
    _check(result, data, [("item", 1, 2, "a", None), ("item", 5, 6, "b", None)])
    assert result["file_facts"]["line_ending"] == "CRLF"


def test_mixed_endings_and_missing_final_terminator() -> None:
    data = b"## a\r\nx\n## b\ny"
    result = seg.segment(data, "heading_section", level=2)
    _check(result, data, [("item", 1, 2, "a", None), ("item", 3, 4, "b", None)])
    assert result["file_facts"]["line_ending"] == "mixed"
    assert result["file_facts"]["ends_with_terminator"] is False


def test_bom_before_heading_is_hashed_but_ignored_for_matching() -> None:
    data = b"\xef\xbb\xbf## a\nx\n"
    result = seg.segment(data, "heading_section", level=2)
    _check(result, data, [("item", 1, 2, "a", None)])
    assert result["file_facts"]["has_utf8_bom"] is True


def test_bom_before_frontmatter() -> None:
    data = b"\xef\xbb\xbf---\nk: v\n---\nbody\n"
    _check(seg.segment(data, "log_frontmatter"), data, [("item", 1, 3, "frontmatter", None)])


def test_bom_only_line_one_is_blank() -> None:
    data = b"\xef\xbb\xbf\n## a\nx\n"
    _check(seg.segment(data, "heading_section", level=2), data, [("item", 2, 3, "a", None)])


# --- No Markdown parsing -------------------------------------------------------------------------------------------


def test_hash_line_inside_a_fence_is_a_heading() -> None:
    data = b"## a\n```\n## b\n```\n"
    result = seg.segment(data, "heading_section", level=2)
    _check(result, data, [("item", 1, 2, "a", None), ("item", 3, 4, "b", None)])


def test_setext_underline_is_not_a_heading_and_trailing_rule_is_structural() -> None:
    data = b"## a\nTitle\n===\nmore\n---\n"
    _check(seg.segment(data, "heading_section", level=2), data, [("item", 1, 4, "a", None)])


def test_closing_hashes_stay_in_anchor_text() -> None:
    data = b"## a ##  \nx\n"
    _check(seg.segment(data, "heading_section", level=2), data, [("item", 1, 2, "a ##", None)])


def test_non_atx_forms_are_not_headings() -> None:
    data = b"## real\n ## leading space\n##\ttab\n##nospace\n####### seven\n"
    _check(seg.segment(data, "heading_section", level=2), data, [("item", 1, 5, "real", None)])


def test_invalid_utf8_anchor_is_unparseable() -> None:
    data = b"## \xff\nx\n"
    _check(seg.segment(data, "heading_section", level=2), data, [("blocker", 1, 2, None, "unparseable_anchor")])


# --- heading_section regions -----------------------------------------------------------------------------------------


def test_declared_structural_range_suppresses_anchors() -> None:
    data = b"## Lifecycle\n```\n## fake\n```\n---\n## item-a\nx\n"
    _check(
        seg.segment(data, "heading_section", level=2, region=(1, 7), structural=[(1, 5)]),
        data,
        [("item", 6, 7, "item-a", None)],
    )
    _check(
        seg.segment(data, "heading_section", level=2, region=(1, 7)),
        data,
        [("item", 1, 2, "Lifecycle", None), ("item", 3, 4, "fake", None), ("item", 6, 7, "item-a", None)],
    )


def test_unaddressed_region_is_a_blocker() -> None:
    data = b"stray\n## a\nx\n"
    _check(
        seg.segment(data, "heading_section", level=2),
        data,
        [("blocker", 1, 1, None, "unaddressed_region"), ("item", 2, 3, "a", None)],
    )


def test_duplicate_heading_anchor_blocks_both() -> None:
    data = b"## a\nx\n## a\ny\n"
    _check(
        seg.segment(data, "heading_section", level=2),
        data,
        [("blocker", 1, 2, "a", "duplicate_anchor"), ("blocker", 3, 4, "a", "duplicate_anchor")],
    )


# --- computational_log_entry -----------------------------------------------------------------------------------------

LOG = (
    b"# Computational Log\n"
    b"\n"
    b"### 2026-01-02 -- x\n"
    b"body\n"
    b"#### sub\n"
    b"more\n"
    b"\n"
    b"---\n"
    b"\n"
    b"## 2026-03 month\n"
    b"### sub3\n"
    b"b\n"
    b"### 2026-06-03b y\n"
    b"z\n"
    b"### ~2026-05-01 approx\n"
    b"q\n"
    b"### 2026-13x bad\n"
    b"w\n"
    b"## Notes\n"
    b"n\n"
)


def test_log_entries_dates_nesting_and_blockers() -> None:
    _check(
        seg.segment(LOG, "computational_log_entry"),
        LOG,
        [
            ("structural", 1, 1, None, None),
            ("item", 3, 6, "2026-01-02 -- x", None),
            ("item", 10, 12, "2026-03 month", None),
            ("item", 13, 14, "2026-06-03b y", None),
            ("item", 15, 16, "~2026-05-01 approx", None),
            ("blocker", 17, 18, None, "unparseable_anchor"),
            ("structural", 19, 20, None, None),
        ],
    )


def test_log_date_range_and_parenthetical_forms() -> None:
    data = b"### 2026-06-01/02 two days\na\n### 2026-06-05(later)\nb\n### 2026-06-07\nc\n"
    _check(
        seg.segment(data, "computational_log_entry"),
        data,
        [
            ("item", 1, 2, "2026-06-01/02 two days", None),
            ("item", 3, 4, "2026-06-05(later)", None),
            ("item", 5, 6, "2026-06-07", None),
        ],
    )


def test_log_duplicate_anchor_blocks_both() -> None:
    data = b"### 2026-01-01 a\nx\n### 2026-01-01 a\ny\n"
    _check(
        seg.segment(data, "computational_log_entry"),
        data,
        [("blocker", 1, 2, "2026-01-01 a", "duplicate_anchor"), ("blocker", 3, 4, "2026-01-01 a", "duplicate_anchor")],
    )


def test_log_preamble_and_orphan_deep_heading() -> None:
    data = b"---\ntitle: x\n---\n#### orphan\nz\n### 2026-01-01 a\n"
    _check(
        seg.segment(data, "computational_log_entry"),
        data,
        [
            ("structural", 1, 3, None, None),
            ("blocker", 4, 5, None, "unaddressed_region"),
            ("item", 6, 6, "2026-01-01 a", None),
        ],
    )


# --- tracker_task_row and working_note_entry -------------------------------------------------------------------------

TRACKER = (
    b"# T\n"
    b"## Task Tracking\n"
    b"\n"
    b"| Task | Status |\n"
    b"|------|--------|\n"
    b"| 1.37 | done |\n"
    b"| 1.2g | open |\n"
    b"| 1.15a-redo | x |\n"
    b"| bad\\|cell | y |\n"
    b"\n"
    b"| Thread | Note |\n"
    b"| T1.20 x | y |\n"
    b"\n"
    b"## Working Notes\n"
    b"\n"
    b"- **2026-10-21: a**\n"
    b"  more\n"
    b"\n"
    b"- **2026-10-21: b**\n"
    b"- undated note\n"
    b"\n"
    b"---\n"
)


def test_tracker_stage_table_rows() -> None:
    result = seg.segment(TRACKER, "tracker_task_row")
    _check(
        result,
        TRACKER,
        [
            ("item", 6, 6, "1.37", None),
            ("item", 7, 7, "1.2g", None),
            ("item", 8, 8, "1.15a-redo", None),
            ("blocker", 9, 9, None, "unaddressed_region"),
        ],
    )
    assert [r.get("task_id") for r in result["rows"][:3]] == ["T1.37", "T1.2g", "T1.15a-redo"]


def test_tracker_duplicate_task_row_blocks() -> None:
    data = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.1 | b |\n"
    _check(
        seg.segment(data, "tracker_task_row"),
        data,
        [("blocker", 4, 4, "1.1", "duplicate_anchor"), ("blocker", 5, 5, "1.1", "duplicate_anchor")],
    )


def test_working_notes_full_first_line_is_anchor() -> None:
    result = seg.segment(TRACKER, "working_note_entry")
    _check(
        result,
        TRACKER,
        [
            ("item", 16, 17, "- **2026-10-21: a**", None),
            ("item", 19, 19, "- **2026-10-21: b**", None),
            ("item", 20, 20, "- undated note", None),
        ],
    )
    assert [r["dated"] for r in result["rows"]] == [True, True, False]


def test_working_notes_duplicate_and_unaddressed() -> None:
    data = b"## Working Notes\nstray text\n- **2026-01-01: same**\n- **2026-01-01: same**\n"
    _check(
        seg.segment(data, "working_note_entry"),
        data,
        [
            ("blocker", 2, 2, None, "unaddressed_region"),
            ("blocker", 3, 3, "- **2026-01-01: same**", "duplicate_anchor"),
            ("blocker", 4, 4, "- **2026-01-01: same**", "duplicate_anchor"),
        ],
    )


# --- log_frontmatter -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"---\na: b\n---\nbody\n", [("item", 1, 3, "frontmatter", None)]),
        (b"---\na: b\n", [("blocker", 1, 2, None, "unparseable_anchor")]),
        (b"# Task Log\n", [("blocker", 1, 1, None, "unparseable_anchor")]),
        (b"\n \n", [("blocker", 1, 1, None, "unparseable_anchor")]),
        (b"---  \r\na: b\r\n---\r\n", [("item", 1, 3, "frontmatter", None)]),
    ],
)
def test_frontmatter(data: bytes, expected: list[Expected]) -> None:
    _check(seg.segment(data, "log_frontmatter"), data, expected)


def test_empty_file_frontmatter_is_one_zero_length_blocker() -> None:
    rows = seg.segment(b"", "log_frontmatter")["rows"]
    assert len(rows) == 1
    assert rows[0]["row_kind"] == "blocker"
    assert rows[0]["blocker_reason"] == "unparseable_anchor"
    assert (rows[0]["start_byte"], rows[0]["byte_length"], rows[0]["line_count"]) == (0, 0, 0)
    assert rows[0]["raw_row_sha256"] == hashlib.sha256(b"").hexdigest()


# --- conventions_unit ------------------------------------------------------------------------------------------------

CONVENTIONS = (
    b"# CONVENTIONS\n"
    b"> preamble\n"
    b"\n"
    b"## Alpha\n"
    b"\n"
    b"- bullet one\n"
    b"  continued\n"
    b"\n"
    b"  after blank\n"
    b"- bullet two\n"
    b"\n"
    b"Para line 1\n"
    b"para line 2\n"
    b"| a | b |\n"
    b"|---|---|\n"
    b"\n"
    b"---\n"
    b"\n"
    b"## Beta\n"
    b"\n"
    b"* x\n"
    b"\n"
    b"---\n"
    b"\n"
    b"*Last updated: 2026-07-16*\n"
)


def test_conventions_units() -> None:
    result = seg.segment(CONVENTIONS, "conventions_unit")
    _check(
        result,
        CONVENTIONS,
        [
            ("item", 6, 9, "Alpha", None),
            ("item", 10, 10, "Alpha", None),
            ("item", 12, 13, "Alpha", None),
            ("item", 14, 15, "Alpha", None),
            ("item", 21, 21, "Beta", None),
        ],
    )
    assert [r["unit_ordinal"] for r in result["rows"]] == [1, 2, 3, 4, 1]
    assert all(r["unit_hash"] == r["raw_row_sha256"] for r in result["rows"])


def test_conventions_duplicate_unit_blocks_both() -> None:
    data = b"## S\n- x\n- x\n"
    _check(
        seg.segment(data, "conventions_unit"),
        data,
        [("blocker", 2, 2, "S", "duplicate_anchor"), ("blocker", 3, 3, "S", "duplicate_anchor")],
    )


def test_unknown_selector_and_missing_level_are_rejected() -> None:
    with pytest.raises(seg.SegmentationError):
        seg.segment(b"", "nonesuch")
    with pytest.raises(seg.SegmentationError):
        seg.segment(b"## a\n", "heading_section")
