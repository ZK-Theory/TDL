# Research context: docs/plans/agentic-research-system/03-decisions-and-open-questions.md (P-082 item 5; review M-2)
# Purpose: LR-011's check of a "from the first anchor after" region against the resolution its bytes give.
"""The shared first-anchor resolution and LR-011's resolution check (WP9.3-1b; contract §3; note §8.3)."""

from __future__ import annotations

import hashlib
import random
from typing import Any

import pytest

from research_system.errors import IntegrityError
from research_system.legacy.preparers import check_resegmentation, inventory_rows
from research_system.legacy.segmentation import SegmentationError, resolve_first_anchor_after, segment

RESOLUTION = "W9 inventory region resolution differs from the first anchor after its after_line"
UNRESOLVABLE = "W9 inventory region cannot be resolved"

# The review's M-2 source: ten lines, level-2 anchors at lines 3, 6 and 9.
SOURCE = b"# Title\n\n## a\nlegacy text a\n\n## b\nlegacy text b\n\n## c\nlegacy text c\n"
LOG = b"# Log\n\n## Not dated\ntext\n\n## 2026-01-02 -- first\ntext\n\n### 2026-01-03 -- second\ntext\n"


def _line(data: bytes, number: int) -> bytes:
    lines = data.split(b"\n")
    return lines[number - 1] + (b"\n" if number < len(lines) else b"")


def _inventory(
    data: bytes,
    after_line: int,
    first: int,
    last: int,
    *,
    selector: str = "heading_section",
    level: int | None = 2,
    structural: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """An inventory whose rows are the true segmentation of its *declared* range, as a hand-builder would make."""
    structural = structural or []
    kwargs: dict[str, Any] = {"region": (first, last), "structural": structural}
    if level is not None:
        kwargs["level"] = level
    segmented = segment(data, selector, **kwargs)
    return {
        "selector_kind": selector,
        "heading_level": level,
        "covered_region": {
            "form": "first_anchor_after",
            "after_line": after_line,
            "after_line_sha256": hashlib.sha256(_line(data, after_line)).hexdigest(),
            "resolved_first_line": first,
            "resolved_last_line": last,
        },
        "structural_ranges": [{"first_line": a, "last_line": b} for a, b in structural],
        "rows": inventory_rows(segmented, selector),
        "suppressed_anchors": segmented["suppressed_anchors"],
        "file_facts": segmented["file_facts"],
    }


def test_the_resolution_is_the_first_anchor_after_the_line_and_the_files_last_line() -> None:
    assert resolve_first_anchor_after(SOURCE, "heading_section", 1, level=2) == (3, 10)
    assert resolve_first_anchor_after(SOURCE, "heading_section", 3, level=2) == (6, 10)
    assert resolve_first_anchor_after(SOURCE, "heading_section", 8, level=2) == (9, 10)


def test_the_true_resolution_is_admitted() -> None:
    record = _inventory(SOURCE, 1, 3, 10)
    check_resegmentation(SOURCE, record)
    assert [row["anchor_text"] for row in record["rows"]] == ["a", "b", "c"]


@pytest.mark.parametrize(
    ("first", "last"),
    [(6, 10), (3, 5), (6, 8)],
    ids=["skips-the-first-anchor", "stops-before-the-end", "both"],
)
def test_a_wrong_resolution_is_refused(first: int, last: int) -> None:
    """Review M-2's three cases: the after_line hash is right and the rows match the declared range, yet items drop."""
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(SOURCE, _inventory(SOURCE, 1, first, last))


def test_a_wrong_after_line_hash_is_still_refused_first() -> None:
    record = _inventory(SOURCE, 1, 6, 10)  # also a wrong resolution: the hash check is reached alone
    record["covered_region"]["after_line_sha256"] = "0" * 64
    with pytest.raises(IntegrityError, match="anchor-line hashes"):
        check_resegmentation(SOURCE, record)


def test_no_anchor_after_the_line_is_refused() -> None:
    record = _inventory(SOURCE, 9, 10, 10)
    with pytest.raises(IntegrityError, match=f"{UNRESOLVABLE}: no anchor follows line 9"):
        check_resegmentation(SOURCE, record)


def test_an_after_line_outside_the_file_is_refused() -> None:
    with pytest.raises(SegmentationError, match="after_line 11 is outside the file"):
        resolve_first_anchor_after(SOURCE, "heading_section", 11, level=2)
    with pytest.raises(SegmentationError, match="after_line 0 is outside the file"):
        resolve_first_anchor_after(SOURCE, "heading_section", 0, level=2)


@pytest.mark.parametrize("after_line", [0, 12, 99])
def test_a_declared_after_line_outside_the_file_is_refused_not_indexed(after_line: int) -> None:
    """The hash check no longer indexes past the file (``IndexError``) or wraps at line 0: such a line has no hash."""
    record = _inventory(SOURCE, 1, 3, 10)
    record["covered_region"]["after_line"] = after_line
    with pytest.raises(IntegrityError, match="anchor-line hashes"):
        check_resegmentation(SOURCE, record)


@pytest.mark.parametrize(
    ("selector", "level", "message"),
    [
        ("tracker_task_row", None, "tracker_task_row takes no declared region"),
        ("conventions_unit", None, "conventions_unit takes no declared region"),
        ("heading_section", None, "heading_section needs a level"),
    ],
)
def test_the_resolution_refuses_what_has_no_declared_region(selector: str, level: int | None, message: str) -> None:
    with pytest.raises(SegmentationError, match=message):
        resolve_first_anchor_after(SOURCE, selector, 1, level=level)


def test_a_suppressed_heading_is_not_the_first_anchor() -> None:
    """Line 3 lies in a declared structural range, so the first anchor after line 1 is line 6."""
    assert resolve_first_anchor_after(SOURCE, "heading_section", 1, level=2, structural=[(3, 4)]) == (6, 10)
    check_resegmentation(SOURCE, _inventory(SOURCE, 1, 6, 10, structural=[(3, 4)]))
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(SOURCE, _inventory(SOURCE, 1, 3, 10, structural=[(3, 4)]))


def test_a_computational_log_anchor_is_a_dated_level_2_or_3_heading() -> None:
    """The undated level-2 heading at line 3 is no anchor; line 6 is, and so is the level-3 line 9."""
    assert resolve_first_anchor_after(LOG, "computational_log_entry", 1) == (6, 10)
    assert resolve_first_anchor_after(LOG, "computational_log_entry", 6) == (9, 10)
    check_resegmentation(LOG, _inventory(LOG, 1, 6, 10, selector="computational_log_entry", level=None))
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(LOG, _inventory(LOG, 1, 3, 10, selector="computational_log_entry", level=None))


def test_a_digit_heading_that_is_no_date_is_a_blocker_anchor_the_resolution_keeps() -> None:
    """``## 2026/01 x`` opens an unparseable_anchor blocker, so the region starts there and the blocker stays."""
    data = b"# Log\n\n## 2026/01 x\ntext\n\n## 2026-01-02 y\ntext\n"
    assert resolve_first_anchor_after(data, "computational_log_entry", 1) == (3, 7)
    record = _inventory(data, 1, 3, 7, selector="computational_log_entry", level=None)
    check_resegmentation(data, record)
    assert [row["blocker_reason"] for row in record["rows"] if row["row_kind"] == "blocker"] == ["unparseable_anchor"]
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(data, _inventory(data, 1, 6, 7, selector="computational_log_entry", level=None))


def test_a_non_integer_after_line_is_refused() -> None:
    record = _inventory(SOURCE, 1, 3, 10)
    # A null hash matches the null a non-line gets, so the hash check passes and the resolution's own guard refuses.
    record["covered_region"]["after_line"] = True
    record["covered_region"]["after_line_sha256"] = None
    with pytest.raises(IntegrityError, match=f"{UNRESOLVABLE}: after_line is not a line number"):
        check_resegmentation(SOURCE, record)


def _generated(rng: random.Random) -> bytes:
    pieces = [
        b"## a\n",
        b"### b\n",
        b"## 2026-01-02 x\n",
        b"### 2026-02 y\n",
        b"## 2026/01 z\n",
        b"#### deep\n",
        b"text\n",
        b"\n",
        b"---\n",
        b"# T\n",
    ]
    ending = rng.choice([b"", b"\r"])
    body = b"".join(rng.choice(pieces).replace(b"\n", ending + b"\n") for _ in range(rng.randint(1, 14)))
    return body if rng.random() < 0.8 else body.rstrip(b"\r\n")


def test_the_resolution_agrees_with_the_segmenters_own_anchors_on_generated_inputs() -> None:
    """Property, seed 20261110: the resolved first line opens the range's first item or blocker row under ``segment``,
    and no anchor line lies between ``after_line`` and it."""
    rng = random.Random(20261110)
    resolved = refused = 0
    for _ in range(1500):
        data = _generated(rng)
        count = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
        after = rng.randint(1, count)
        for selector, kwargs in (("heading_section", {"level": rng.choice([2, 3])}), ("computational_log_entry", {})):
            try:
                first, last = resolve_first_anchor_after(data, selector, after, **kwargs)
            except SegmentationError as exc:
                assert str(exc) == f"no anchor follows line {after}"
                refused += 1
                continue
            assert after < first <= last == count
            rows = segment(data, selector, region=(first, last), **kwargs)["rows"]
            opened = [row for row in rows if row["row_kind"] != "structural" and row["anchor_line_sha256"]]
            assert opened and opened[0]["start_line"] == first, (data, selector, after)
            # Nothing between after_line and the resolution opens a row: segmenting that gap gives none.
            if first - 1 > after:
                gap = segment(data, selector, region=(after + 1, first - 1), **kwargs)["rows"]
                assert not [
                    row
                    for row in gap
                    if row["row_kind"] == "item"
                    or row["blocker_reason"]
                    in (
                        "unparseable_anchor",
                        "duplicate_anchor",
                    )
                ], (data, selector, after)
            resolved += 1
    assert resolved > 500 and refused > 50
