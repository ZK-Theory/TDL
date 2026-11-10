# Research context: docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md (owner point I, P-068)
# Purpose: compare the reviewer's independent re-implementation with the runtime segmenter
# (research_system/legacy/segmentation.py) and the reference tool (tools/w9_segmentation.py) on seeded generated
# inputs, aimed at the places where the contract text leaves a reading open. Seed 20261110, recorded here and in the
# review report. Reads no legacy bytes.
"""Three-way differential: reimpl vs runtime segmenter vs reference tool."""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT))

import reimpl_segmentation as mine  # noqa: E402
import w9_segmentation as reference  # noqa: E402

from research_system.legacy import segmentation as runtime  # noqa: E402

ALIGNED = {
    "R-1 block trim": "blank-and-rule",
    "R-3 suppressed record": "level==k",
    "R-4 preamble": "whole",
    "R-5 tracker utf8": "whole-row",
    "R-7 conventions section end": "level==2",
    "R-8 empty-file anchor hash": "none",
    "C-1 tracker cell trim": "all-whitespace",
    "C-2 invalid section title": "item-empty",
    "C-3 conventions footer": "trailing-ws-trimmed",
}
SEED = 20261110
CASES_PER_SELECTOR = 3000
ROW_KEYS = (
    "row_ordinal",
    "row_kind",
    "start_line",
    "line_count",
    "start_byte",
    "byte_length",
    "raw_row_sha256",
    "anchor_line_sha256",
    "anchor_text",
    "blocker_reason",
    "task_id",
    "dated",
    "unit_ordinal",
    "unit_hash",
)

COMMON = [
    b"",
    b" ",
    b"\t",
    b"---",
    b"--- ",
    b"  ---",
    b"text",
    b"  indented",
    b"```",
    b"===",
    b"\xff\xfe bad",
]
HEADINGS = [
    b"# Title",
    b"## a",
    b"## b",
    b"### c",
    b"#### deep",
    b"## \xff",
    b"### \xc3",
    b"##nospace",
    b" ## lead",
    b"## a ##",
    b"## ",
]
LOG = [
    b"## 2026-01-01 x",
    b"### 2026-01-01 x",
    b"### 2026-01-02",
    b"## 2026-03 m",
    b"### 2026-06-03b y",
    b"### 2026-06-01/02 r",
    b"### ~2026-05-01 a",
    b"### 2026-06-05(later)",
    b"### 2026-13x bad",
    b"## 1 looks",
    b"### ~9 looks",
    b"## Notes",
    b"### Results",
    b"# Computational Log",
    b"### 2026-01-01\t tab",
    b"### 2026-06-03bc no",
    b"### \xff2026",
    b"### 2026-01-01 \xff",
]
TRACKER = [
    b"## Task Tracking",
    b"| Task | Status |",
    b"|------|--------|",
    b"| :--- | ---: |",
    b"| 1.37 | done |",
    b"| 1.2g | open |",
    b"| 1.15a-redo | x |",
    b"| 1.1 | dup |",
    b"| 1.1 | dup |",
    b"| bad\\|cell | y |",
    b"| Thread | Note |",
    b"|1.5|tight|",
    b"| 1.6 ",
    b"| \xff | z |",
    b"| | empty |",
    b"|",
    b"| Task |",
    b"| 2.3\t| tab |",
]
NOTES = [
    b"## Working Notes",
    b"- **2026-10-21: a**",
    b"- **2026-10-21: a**",
    b"- **~2026-10-21: approx**",
    b"- undated",
    b"-nospace",
    b"  continuation",
    b"* star",
    b"- \xff",
    b"- trailing   ",
]
CONVENTIONS = [
    b"## Alpha",
    b"## Beta",
    b"- bullet",
    b"* star",
    b"  cont",
    b"\tcont tab",
    b"Para",
    b"para two",
    b"| a | b |",
    b"|---|---|",
    b"*Last updated: 2026-07-16*",
    b"*Last updated: x* ",
    b"**bold**",
    b"- bullet",
]
FRONTMATTER = [b"---", b"---  ", b"k: v", b"# Task Log", b"", b" "]


def _doc(rng: random.Random, palette: list[bytes], lead: list[bytes] | None = None) -> bytes:
    pool = palette + COMMON + HEADINGS
    lines = list(lead or []) + [rng.choice(pool) for _ in range(rng.randint(0, 14))]
    if rng.random() < 0.3:
        rng.shuffle(lines)
    endings = rng.choice([[b"\n"], [b"\r\n"], [b"\n", b"\r\n"]])
    out = b"".join(line + rng.choice(endings) for line in lines)
    if out and rng.random() < 0.2:
        out = out.rstrip(b"\r\n")
    if rng.random() < 0.1:
        out = b"\xef\xbb\xbf" + out
    return out


def _norm(result: dict[str, Any]) -> dict[str, Any]:
    rows = [{k: r.get(k) for k in ROW_KEYS} for r in result["rows"]]
    supp = [{k: s.get(k) for k in ("line", "anchor_line_sha256", "heading_text")} for s in result["suppressed_anchors"]]
    return {"rows": rows, "suppressed": supp, "facts": result["file_facts"], "sha": result["file_sha256"]}


def _run(fn: Any, data: bytes, selector: str, kwargs: dict[str, Any]) -> Any:
    try:
        return _norm(fn(data, selector, **kwargs))
    except (mine.ReimplError, runtime.SegmentationError, reference.SegmentationError):  # compared as a refusal only
        return "refused"


def _cases(selector: str) -> list[tuple[bytes, dict[str, Any]]]:
    rng = random.Random(f"{SEED}:{selector}")
    out = []
    for _ in range(CASES_PER_SELECTOR):
        kwargs: dict[str, Any] = {}
        if selector == "heading_section":
            data = _doc(rng, [])
            kwargs["level"] = rng.randint(1, 3)
            n = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
            if n and rng.random() < 0.5:
                lo = rng.randint(1, n)
                hi = rng.randint(lo, n)
                kwargs["region"] = (lo, hi)
                if rng.random() < 0.6:
                    a = rng.randint(lo, hi)
                    kwargs["structural"] = [(a, rng.randint(a, hi))]
        elif selector == "computational_log_entry":
            data = _doc(rng, LOG)
        elif selector == "tracker_task_row":
            data = _doc(rng, TRACKER, lead=[b"## Task Tracking", b"| Task | S |"] if rng.random() < 0.8 else None)
        elif selector == "working_note_entry":
            data = _doc(rng, NOTES, lead=[b"## Working Notes"] if rng.random() < 0.8 else None)
        elif selector == "log_frontmatter":
            data = _doc(rng, FRONTMATTER)
        else:
            data = _doc(rng, CONVENTIONS)
        out.append((data, kwargs))
    return out


def _diffs(left: Any, right: Any, cases: list[tuple[bytes, dict[str, Any]]], selector: str) -> list[Any]:
    return [(d, k) for d, k in cases if _run(left, d, selector, k) != _run(right, d, selector, k)]


@pytest.mark.parametrize("selector", mine.SELECTORS)
def test_runtime_matches_reference(selector: str) -> None:
    """The runtime segmenter against the accepted reference tool."""
    cases = _cases(selector)
    diffs = _diffs(runtime.segment, reference.segment, cases, selector)
    assert diffs == [], f"{len(diffs)} of {len(cases)} differ; first: {diffs[:3]!r}"


@pytest.fixture
def readings(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    table = dict(mine.FIRST_READINGS)
    monkeypatch.setattr(mine, "READINGS", table)
    return table


@pytest.mark.parametrize("selector", mine.SELECTORS)
def test_reimpl_with_runtime_readings_matches_runtime(selector: str, readings: dict[str, str]) -> None:
    """With each open reading set to the runtime's choice, the re-implementation equals the runtime everywhere."""
    readings.update(ALIGNED)
    cases = _cases(selector)
    diffs = _diffs(mine.segment, runtime.segment, cases, selector)
    assert diffs == [], f"{len(diffs)} of {len(cases)} differ; first: {diffs[:3]!r}"


# The difference count each reading makes on its own (all others at the runtime's choice), on these seeded cases.
OBSERVED = {
    "R-1 block trim": ("computational_log_entry", 268),
    "R-3 suppressed record": ("heading_section", 90),
    "R-4 preamble": ("computational_log_entry", 252),
    "R-5 tracker utf8": ("tracker_task_row", 81),
    "R-7 conventions section end": ("conventions_unit", 143),
    "R-8 empty-file anchor hash": ("log_frontmatter", 179),
    "C-1 tracker cell trim": ("tracker_task_row", 77),
    "C-2 invalid section title": ("conventions_unit", 313),
    "C-3 conventions footer": ("conventions_unit", 268),
}


@pytest.mark.parametrize("key", sorted(OBSERVED))
def test_each_reading_alone_is_a_real_difference(key: str, readings: dict[str, str]) -> None:
    """No switch is idle: the reviewer's first value of each reading, alone, differs from the runtime."""
    readings.update(ALIGNED)
    readings[key] = mine.FIRST_READINGS[key]
    selector, count = OBSERVED[key]
    assert len(_diffs(mine.segment, runtime.segment, _cases(selector), selector)) == count


# Contract departures shared by the runtime segmenter and the reference tool (review findings m-1 to m-3).


@pytest.mark.parametrize("impl", [runtime.segment, reference.segment], ids=["runtime", "reference"])
def test_c1_tracker_cells_are_trimmed_of_every_whitespace_not_only_spaces(impl: Any, readings: dict[str, str]) -> None:
    """Contract §3: "each cell is trimmed of spaces". A tab or a no-break space around a task cell is trimmed too."""
    for pad in (b"\t", b"\xc2\xa0", b"\x0b"):
        data = b"## Task Tracking\n| Task | S |\n|---|---|\n| 2.3" + pad + b" | x |\n"
        got = [(r["row_kind"], r["anchor_text"], r.get("task_id")) for r in impl(data, "tracker_task_row")["rows"]]
        assert got == [("item", "2.3", "T2.3")], pad
        contract = [(r["row_kind"], r["blocker_reason"]) for r in mine.segment(data, "tracker_task_row")["rows"]]
        assert contract == [("blocker", "unaddressed_region")], pad


@pytest.mark.parametrize("impl", [runtime.segment, reference.segment], ids=["runtime", "reference"])
def test_c2_invalid_utf8_section_title_gives_items_with_empty_anchor(impl: Any, readings: dict[str, str]) -> None:
    """Contract §3: bytes that are not valid UTF-8 make the row a blocker. Here they give items anchored on ""."""
    data = b"## \xff\n- x\n## \n- y\n- x\n"
    got = [(r["row_kind"], r["anchor_text"], r["blocker_reason"]) for r in impl(data, "conventions_unit")["rows"]]
    # The invalid title and the empty title share the anchor "": the two "- x" units collide as duplicates.
    assert got == [("blocker", "", "duplicate_anchor"), ("item", "", None), ("blocker", "", "duplicate_anchor")]
    readings["C-2 invalid section title"] = "blocker"
    contract = [(r["row_kind"], r["blocker_reason"]) for r in mine.segment(data, "conventions_unit")["rows"]]
    assert contract == [("blocker", "unparseable_anchor"), ("item", None), ("item", None)]


@pytest.mark.parametrize("impl", [runtime.segment, reference.segment], ids=["runtime", "reference"])
def test_c3_footer_with_trailing_space_is_structural(impl: Any, readings: dict[str, str]) -> None:
    """Contract §3: the footer matches `*Last updated: …*` "exactly". A trailing space still makes it the footer."""
    data = b"## S\n- x\n*Last updated: 2026-07-16* \n"
    assert [r["start_line"] for r in impl(data, "conventions_unit")["rows"]] == [2]
    assert [r["start_line"] for r in mine.segment(data, "conventions_unit")["rows"]] == [2, 3]
