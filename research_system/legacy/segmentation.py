"""The runtime segmenter for ``w9-segmentation/1.0.0`` (WP9.3 note §8.1; owner point I; P-081 item 9).

It implements the accepted segmentation contract (``transition/w9/w9-segmentation-contract-v1.md``) for the W9 runtime.
The reference implementation, ``tools/w9_segmentation.py``, stays as it is, accepted at blob ``43e1454d`` and
non-runtime (P-067 item 2, P-068); importing it here would make it runtime code. The contract's vectors run against both
implementations, and a differential test compares the two on generated inputs from a fixed seed. Where they disagree,
the contract governs (contract §7). WP9.3-1's independent reviewer re-implements the contract a third time and
reproduces every vector (owner point I).

Segmentation is purely line-based over the exact bytes read: no decoding, normalization, BOM stripping or line-ending
conversion (contract §2.1). Rows come out in the shape of ``legacy-light-inventory`` rows.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from research_system.errors import IntegrityError

CONTRACT_ID = "w9-segmentation/1.0.0"
SELECTOR_KINDS = (
    "heading_section",
    "computational_log_entry",
    "tracker_task_row",
    "working_note_entry",
    "log_frontmatter",
    "conventions_unit",
)
_BOM = b"\xef\xbb\xbf"
# Contract §3, the date token: matched at the start of the heading text, followed by the end, a space, a tab or "(".
_DATE_TOKEN = re.compile(rb"~?[0-9]{4}-[0-9]{2}(?:-[0-9]{2}(?:[a-z]|/[0-9]{2})?)?(?:\Z|(?=[ \t(]))")
_STARTS_WITH_DIGIT = re.compile(rb"~?[0-9]")
_TASK_GRAMMAR = re.compile(r"[0-9]+\.[0-9]+[a-z]*(?:-[a-z]+)?\Z")
_SEPARATOR_ROW = re.compile(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\Z")
_FOOTER = re.compile(rb"\*Last updated: .*\*\Z")
_DATED_NOTE = re.compile(r"- \*\*~?[0-9]{4}-[0-9]{2}-[0-9]{2}")


class SegmentationError(IntegrityError):
    """Segmentation is refused: an unknown selector, a missing level or section, or a range outside the file."""


@dataclass(frozen=True)
class _Line:
    """One line (contract §2.2): its 0-based index, start byte, raw bytes with terminator, and match text (§2.3)."""

    index: int
    start: int
    raw: bytes
    match: bytes

    @property
    def blank(self) -> bool:
        """Contract §2.4: only spaces and tabs, or empty."""
        return not self.match.strip(b" \t")

    @property
    def rule(self) -> bool:
        """Contract §2.5: the match text, trailing spaces and tabs removed, is exactly ``---``."""
        return self.match.rstrip(b" \t") == b"---"

    @property
    def level(self) -> int:
        """Contract §2.7: the ATX level, or 0 when the line is not a heading."""
        hashes = len(self.match) - len(self.match.lstrip(b"#"))
        return hashes if 1 <= hashes <= 6 and self.match[hashes : hashes + 1] == b" " else 0

    @property
    def heading_text(self) -> bytes:
        """Contract §2.7: after the hashes and the one space, trailing spaces and tabs removed."""
        return self.match[self.level + 1 :].rstrip(b" \t")


@dataclass
class _Row:
    kind: str
    first: int
    last: int
    anchor: str | None = None
    blocker: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _lines(data: bytes) -> list[_Line]:
    """Split on LF only (contract §2.2): ``bytes.splitlines`` would also split on CR and other separators."""
    out: list[_Line] = []
    start = 0
    while start < len(data):
        end = data.find(b"\n", start)
        raw = data[start:] if end < 0 else data[start : end + 1]
        if raw.endswith(b"\r\n"):
            text = raw[:-2]
        elif raw.endswith(b"\n"):
            text = raw[:-1]
        else:
            text = raw
        if not out and text.startswith(_BOM):
            text = text[len(_BOM) :]
        out.append(_Line(len(out), start, raw, text))
        start += len(raw)
    return out


def _decode(raw: bytes) -> str | None:
    """Contract §3: decoded as UTF-8, never repaired. Invalid bytes make the row a blocker."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _span_end(lines: Sequence[_Line], first: int, last: int, *, trim_rules: bool = True) -> int:
    """The span rule (contract §3): back from ``last`` to the last line that is not blank (nor a rule line)."""
    end = last
    while end > first and (lines[end].blank or (trim_rules and lines[end].rule)):
        end -= 1
    return end


def _facts(data: bytes, lines: Sequence[_Line]) -> dict[str, Any]:
    """Contract §2.8: recorded, never corrected."""
    endings = {b"\r\n" if line.raw.endswith(b"\r\n") else b"\n" for line in lines if line.raw.endswith(b"\n")}
    ending = {frozenset(): "none", frozenset({b"\n"}): "LF", frozenset({b"\r\n"}): "CRLF"}.get(
        frozenset(endings), "mixed"
    )
    return {
        "line_ending": ending,
        "ends_with_terminator": bool(lines) and lines[-1].raw.endswith(b"\n"),
        "has_utf8_bom": data.startswith(_BOM),
        "line_count": len(lines),
    }


def _block_duplicates(rows: Iterable[_Row], key: Any) -> None:
    """Contract §4.3: items sharing an identity are all blockers, never resolved by position."""
    groups: dict[Any, list[_Row]] = {}
    for row in rows:
        if row.kind == "item":
            groups.setdefault(key(row), []).append(row)
    for group in groups.values():
        if len(group) > 1:
            for row in group:
                row.kind, row.blocker = "blocker", "duplicate_anchor"


def _unaddressed(lines: Sequence[_Line], indices: Iterable[int], excluded: set[int]) -> list[_Row]:
    """Contract §4.4: each run of non-blank, non-rule lines outside every item and structural range is one blocker."""
    rows: list[_Row] = []
    run: list[int] = []
    for index in [*indices, None]:
        if index is not None and index not in excluded and not lines[index].blank:
            run.append(index)
            continue
        if run:
            rows.append(_Row("blocker", run[0], run[-1], blocker="unaddressed_region"))
            run = []
    return rows


def _rules(lines: Sequence[_Line], first: int, last: int) -> set[int]:
    return {index for index in range(first, last + 1) if lines[index].rule}


def _declared(structural: Sequence[tuple[int, int]], count: int) -> set[int]:
    declared: set[int] = set()
    for first, last in structural:
        if not 1 <= first <= last <= count:
            raise SegmentationError(f"structural range {first}:{last} is outside the file")
        declared.update(range(first - 1, last))
    return declared


def _heading_sections(
    lines: Sequence[_Line], level: int, region: tuple[int, int], structural: Sequence[tuple[int, int]]
) -> tuple[list[_Row], list[dict[str, Any]]]:
    """``heading_section``: a level-k heading not suppressed, to the next heading of level ≤ k not suppressed."""
    first, last = region[0] - 1, region[1] - 1
    declared = _declared(structural, len(lines))
    rows: list[_Row] = []
    covered: set[int] = set()
    for index in range(first, last + 1):
        if lines[index].level != level or index in declared:
            continue
        stop = next(
            (j - 1 for j in range(index + 1, last + 1) if 1 <= lines[j].level <= level and j not in declared), last
        )
        end = _span_end(lines, index, stop)
        anchor = _decode(lines[index].heading_text)
        rows.append(
            _Row("item", index, end, anchor=anchor)
            if anchor is not None
            else _Row("blocker", index, end, blocker="unparseable_anchor")
        )
        covered.update(range(index, end + 1))
    _block_duplicates(rows, lambda row: row.anchor)
    rows += _unaddressed(lines, range(first, last + 1), covered | declared | _rules(lines, first, last))
    suppressed = [
        {
            "line": index + 1,
            "anchor_line_sha256": hashlib.sha256(lines[index].raw).hexdigest(),
            "heading_text": _decode(lines[index].heading_text),
        }
        for index in range(first, last + 1)
        if index in declared and lines[index].level == level
    ]
    return rows, suppressed


def _log_entries(lines: Sequence[_Line], region: tuple[int, int]) -> list[_Row]:
    """``computational_log_entry``: a level-2 or level-3 heading whose text starts with a date token (contract §3)."""
    first, last = region[0] - 1, region[1] - 1
    headings = [index for index in range(first, last + 1) if lines[index].level]

    def dated(index: int) -> bool:
        return lines[index].level in (2, 3) and bool(_DATE_TOKEN.match(lines[index].heading_text))

    rows: list[_Row] = []
    covered: set[int] = set()
    skip_to = first - 1
    for index in headings:
        level = lines[index].level
        if index <= skip_to or level > 3:
            continue
        stop = next((j - 1 for j in headings if j > index and (lines[j].level <= level or dated(j))), last)
        end = _span_end(lines, index, stop)
        skip_to = stop
        text = lines[index].heading_text
        if dated(index):
            anchor = _decode(text)
            rows.append(
                _Row("item", index, end, anchor=anchor)
                if anchor is not None
                else _Row("blocker", index, end, blocker="unparseable_anchor")
            )
        elif level in (2, 3) and _STARTS_WITH_DIGIT.match(text):
            rows.append(_Row("blocker", index, end, blocker="unparseable_anchor"))
        else:
            rows.append(_Row("structural", index, end))
        covered.update(range(index, end + 1))
    _block_duplicates(rows, lambda row: row.anchor)
    preamble_end = headings[0] if headings else last + 1
    rows += _unaddressed(lines, range(preamble_end, last + 1), covered | _rules(lines, first, last))
    if preamble_end > first:
        # The lines before the first heading are one structural preamble, taken whole.
        rows.append(_Row("structural", first, preamble_end - 1))
    return rows


def _section(lines: Sequence[_Line], title: bytes) -> tuple[int, int]:
    """The fixed region after ``## <title>`` to the line before the next heading of level 1 or 2 (contract §3)."""
    heading = b"## " + title
    start = next((line.index for line in lines if line.match.rstrip(b" \t") == heading), None)
    if start is None:
        raise SegmentationError(f"section '## {title.decode()}' not found")
    end = next((line.index - 1 for line in lines[start + 1 :] if line.level in (1, 2)), len(lines) - 1)
    return start + 1, end


def _cells(text: str) -> list[str]:
    """Cells split on ``|`` not preceded by a backslash, each trimmed of spaces (contract §3)."""
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in text:
        if char == "|" and not escaped:
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
    cells.append("".join(current))
    return [cell.strip() for cell in cells]


def _tracker_rows(lines: Sequence[_Line]) -> list[_Row]:
    """``tracker_task_row``: data rows of stage tables (first header cell ``Task``) under ``## Task Tracking``."""
    first, last = _section(lines, b"Task Tracking")
    rows: list[_Row] = []
    index = first
    while index <= last:
        if not lines[index].match.startswith(b"|"):
            index += 1
            continue
        table_end = index
        while table_end <= last and lines[table_end].match.startswith(b"|"):
            table_end += 1
        header = _cells(lines[index].match.decode("utf-8", errors="replace"))
        if len(header) > 1 and header[1] == "Task":
            for row_index in range(index + 1, table_end):
                text = _decode(lines[row_index].match)
                if text is None:
                    rows.append(_Row("blocker", row_index, row_index, blocker="unparseable_anchor"))
                    continue
                if _SEPARATOR_ROW.match(text.strip()):
                    continue
                cells = _cells(text)
                cell = cells[1] if len(cells) > 1 else ""
                if _TASK_GRAMMAR.match(cell):
                    rows.append(_Row("item", row_index, row_index, anchor=cell, extra={"task_id": f"T{cell}"}))
                else:
                    rows.append(_Row("blocker", row_index, row_index, blocker="unaddressed_region"))
        index = table_end
    _block_duplicates(rows, lambda row: row.anchor)
    return rows


def _working_notes(lines: Sequence[_Line]) -> list[_Row]:
    """``working_note_entry``: top-level bullets (``- `` at column 0) under ``## Working Notes``."""
    first, last = _section(lines, b"Working Notes")
    anchors = [index for index in range(first, last + 1) if lines[index].match.startswith(b"- ")]
    rows: list[_Row] = []
    covered: set[int] = set()
    for position, index in enumerate(anchors):
        stop = anchors[position + 1] - 1 if position + 1 < len(anchors) else last
        end = _span_end(lines, index, stop)
        anchor = _decode(lines[index].match.rstrip(b" \t"))
        if anchor is None:
            rows.append(_Row("blocker", index, end, blocker="unparseable_anchor"))
        else:
            rows.append(_Row("item", index, end, anchor=anchor, extra={"dated": bool(_DATED_NOTE.match(anchor))}))
        covered.update(range(index, end + 1))
    _block_duplicates(rows, lambda row: row.anchor)
    rows += _unaddressed(lines, range(first, last + 1), covered | _rules(lines, first, last))
    return rows


def _frontmatter(lines: Sequence[_Line]) -> list[_Row]:
    """``log_frontmatter``: line 1 ``---`` through the next ``---`` line, both included (contract §3, §4.5)."""
    if not lines:
        return [_Row("blocker", 0, -1, blocker="unparseable_anchor")]
    if not lines[0].rule:
        return [_Row("blocker", 0, 0, blocker="unparseable_anchor")]
    closing = next((line.index for line in lines[1:] if line.rule), None)
    if closing is None:
        return [_Row("blocker", 0, len(lines) - 1, blocker="unparseable_anchor")]
    return [_Row("item", 0, closing, anchor="frontmatter")]


def _conventions(lines: Sequence[_Line]) -> list[_Row]:
    """``conventions_unit``: bullets, tables and paragraphs within each ``## `` section (contract §3)."""

    def skipped(line: _Line) -> bool:
        return line.blank or line.rule or bool(_FOOTER.match(line.match.rstrip(b" \t"))) or bool(line.level)

    def indented(line: _Line) -> bool:
        return line.match[:1] in (b" ", b"\t")

    rows: list[_Row] = []
    sections = [line.index for line in lines if line.level == 2]
    for position, start in enumerate(sections):
        end = sections[position + 1] - 1 if position + 1 < len(sections) else len(lines) - 1
        title = _decode(lines[start].heading_text) or ""
        index, ordinal = start + 1, 0
        while index <= end:
            line = lines[index]
            if skipped(line):
                index += 1
                continue
            if line.match.startswith((b"- ", b"* ")):
                cursor = index + 1
                while cursor <= end:
                    if indented(lines[cursor]) and not lines[cursor].blank:
                        cursor += 1
                        continue
                    if lines[cursor].blank:
                        after = cursor
                        while after <= end and lines[after].blank:
                            after += 1
                        if after <= end and indented(lines[after]):
                            cursor = after
                            continue
                    break
                unit_end = _span_end(lines, index, cursor - 1, trim_rules=False)
            elif line.match.startswith(b"|"):
                cursor = index
                while cursor <= end and lines[cursor].match.startswith(b"|"):
                    cursor += 1
                unit_end = cursor - 1
            else:
                cursor = index
                while cursor <= end and not (
                    skipped(lines[cursor]) or lines[cursor].match.startswith((b"- ", b"* ", b"|"))
                ):
                    cursor += 1
                unit_end = cursor - 1
            ordinal += 1
            unit = b"".join(item.raw for item in lines[index : unit_end + 1])
            rows.append(
                _Row(
                    "item",
                    index,
                    unit_end,
                    anchor=title,
                    extra={"unit_ordinal": ordinal, "unit_hash": hashlib.sha256(unit).hexdigest()},
                )
            )
            index = unit_end + 1
    _block_duplicates(rows, lambda row: (row.anchor, row.extra["unit_hash"]))
    return rows


def _rows(lines: Sequence[_Line], rows: list[_Row]) -> list[dict[str, Any]]:
    out = []
    for ordinal, row in enumerate(sorted(rows, key=lambda item: item.first), start=1):
        span = b"".join(line.raw for line in lines[row.first : row.last + 1])
        out.append(
            {
                "row_ordinal": ordinal,
                "row_kind": row.kind,
                "anchor_text": row.anchor,
                # An empty file gives one zero-length blocker at byte 0 (contract §4.5).
                "start_byte": lines[row.first].start if row.first < len(lines) else 0,
                "byte_length": len(span),
                "start_line": row.first + 1,
                "line_count": max(row.last - row.first + 1, 0),
                "raw_row_sha256": hashlib.sha256(span).hexdigest(),
                "anchor_line_sha256": hashlib.sha256(lines[row.first].raw).hexdigest() if span else None,
                "blocker_reason": row.blocker,
                **row.extra,
            }
        )
    return out


def segment(
    data: bytes,
    selector_kind: str,
    *,
    level: int | None = None,
    region: tuple[int, int] | None = None,
    structural: Sequence[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Segment exact bytes under one selector kind (contract §2 to §4).

    Args:
        data: The exact bytes read, never decoded, normalized or stripped of a BOM.
        selector_kind: One of :data:`SELECTOR_KINDS`.
        level: The heading level k; required for ``heading_section``.
        region: The covered region as 1-based inclusive lines; the whole file when omitted. ``heading_section`` and
            ``computational_log_entry`` use it; the other selectors have fixed regions.
        structural: Declared structural ranges (1-based inclusive); ``heading_section`` only.

    Returns:
        ``segmentation_contract``, ``selector_kind``, ``file_sha256``, ``file_bytes``, ``file_facts``, ``rows`` and
        ``suppressed_anchors``.

    Raises:
        SegmentationError: For an unknown selector, a ``heading_section`` without a level, a structural range outside
            the file, or a missing ``## Task Tracking`` or ``## Working Notes`` section.
    """
    if not isinstance(data, bytes):
        raise SegmentationError("segmentation reads bytes")
    lines = _lines(data)
    whole = (1, len(lines))
    suppressed: list[dict[str, Any]] = []
    if selector_kind == "heading_section":
        if level is None:
            raise SegmentationError("heading_section needs a level")
        rows, suppressed = _heading_sections(lines, level, region or whole, structural or ())
    elif selector_kind == "computational_log_entry":
        rows = _log_entries(lines, region or whole)
    elif selector_kind == "tracker_task_row":
        rows = _tracker_rows(lines)
    elif selector_kind == "working_note_entry":
        rows = _working_notes(lines)
    elif selector_kind == "log_frontmatter":
        rows = _frontmatter(lines)
    elif selector_kind == "conventions_unit":
        rows = _conventions(lines)
    else:
        raise SegmentationError(f"unknown selector kind: {selector_kind}")
    return {
        "segmentation_contract": CONTRACT_ID,
        "selector_kind": selector_kind,
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "file_bytes": len(data),
        "file_facts": _facts(data, lines),
        "rows": _rows(lines, rows),
        "suppressed_anchors": suppressed,
    }
