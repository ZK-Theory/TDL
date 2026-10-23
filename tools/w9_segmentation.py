# Research context: docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md (WP9.0, P-065)
# Purpose: reference implementation of w9-segmentation/1.0.0, so item spans and hashes can be reproduced independently.
"""Reference implementation of the W9 segmentation contract ``w9-segmentation/1.0.0``.

This module is a non-runtime tool. It reads bytes it is given and returns item rows; it never opens a store, writes a
file it reads, or decodes and repairs text. The contract document is normative; where this module and the contract
disagree, the contract governs and this module is wrong.

Usage::

    python tools/w9_segmentation.py <selector_kind> <file> [--level K] [--region START:END] [--structural A:B ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONTRACT_ID = "w9-segmentation/1.0.0"
BOM = b"\xef\xbb\xbf"
_LOG_DATE = re.compile(rb"^~?[0-9]{4}-[0-9]{2}(?:-[0-9]{2}(?:[a-z]|/[0-9]{2})?)?(?=$|[ \t(])")
_LOOKS_DATED = re.compile(rb"^~?[0-9]")
_TASK_CELL = re.compile(r"^[0-9]+\.[0-9]+[a-z]*(?:-[a-z]+)?$")
_TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
_FOOTER = re.compile(rb"^\*Last updated: .*\*$")


@dataclass(frozen=True)
class Line:
    """One line: its 1-based number, start byte, raw bytes, and the bytes without terminator."""

    number: int
    start: int
    raw: bytes
    text: bytes
    terminator: bytes


@dataclass
class Row:
    """One inventory row, in the shape of ``legacy-light-inventory`` rows."""

    row_kind: str
    first: int
    last: int
    anchor_text: str | None = None
    blocker_reason: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class SegmentationError(ValueError):
    """Raised for invalid selector parameters."""


def split_lines(data: bytes) -> list[Line]:
    """Split bytes into lines ending with LF (a CR before the LF belongs to the terminator)."""
    lines: list[Line] = []
    position = 0
    number = 1
    while position < len(data):
        end = data.find(b"\n", position)
        if end == -1:
            raw = data[position:]
            lines.append(Line(number, position, raw, raw, b""))
            break
        raw = data[position : end + 1]
        if raw.endswith(b"\r\n"):
            text, terminator = raw[:-2], b"\r\n"
        else:
            text, terminator = raw[:-1], b"\n"
        lines.append(Line(number, position, raw, text, terminator))
        position = end + 1
        number += 1
    return lines


def match_text(line: Line) -> bytes:
    """Bytes used for anchor matching: the line without terminator, and without a BOM on line 1."""
    if line.number == 1 and line.text.startswith(BOM):
        return line.text[len(BOM) :]
    return line.text


def is_blank(line: Line) -> bool:
    """A blank line has, apart from its terminator, only spaces and tabs (a BOM on line 1 is ignored)."""
    return match_text(line).strip(b" \t") == b""


def file_facts(data: bytes, lines: list[Line]) -> dict[str, Any]:
    """Record line endings, final terminator, BOM and line count, without correcting anything."""
    kinds = {line.terminator for line in lines if line.terminator}
    if not kinds:
        ending = "none"
    elif kinds == {b"\n"}:
        ending = "LF"
    elif kinds == {b"\r\n"}:
        ending = "CRLF"
    else:
        ending = "mixed"
    return {
        "line_ending": ending,
        "ends_with_terminator": bool(lines) and lines[-1].terminator != b"",
        "has_utf8_bom": data.startswith(BOM),
        "line_count": len(lines),
    }


def _anchor_string(raw: bytes) -> str | None:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _heading_level(line: Line) -> int:
    text = match_text(line)
    level = len(text) - len(text.lstrip(b"#"))
    if 1 <= level <= 6 and text[level : level + 1] == b" ":
        return level
    return 0


def _heading_text(line: Line) -> bytes:
    level = _heading_level(line)
    return match_text(line)[level + 1 :].rstrip(b" \t")


def _trim_trailing(lines: list[Line], first: int, last: int, *, rules_structural: bool) -> int:
    """Return the last line index in [first, last] that is non-blank (and not a `---` rule if rules_structural)."""
    index = last
    while index > first:
        line = lines[index]
        if is_blank(line) or (rules_structural and match_text(line).rstrip(b" \t") == b"---"):
            index -= 1
            continue
        break
    return index


def _rows_to_json(lines: list[Line], rows: list[Row]) -> list[dict[str, Any]]:
    out = []
    for ordinal, row in enumerate(sorted(rows, key=lambda r: r.first), start=1):
        span = b"".join(line.raw for line in lines[row.first : row.last + 1])
        # An empty file yields one zero-length blocker row at byte 0 (log_frontmatter); every other row has lines.
        out.append(
            {
                "row_ordinal": ordinal,
                "row_kind": row.row_kind,
                "anchor_text": row.anchor_text,
                "start_byte": lines[row.first].start if row.first < len(lines) else 0,
                "byte_length": len(span),
                "start_line": row.first + 1,
                "line_count": max(row.last - row.first + 1, 0),
                "raw_row_sha256": hashlib.sha256(span).hexdigest(),
                # Lets an inventory check its declared covered region against each anchor line's bytes (§3).
                "anchor_line_sha256": hashlib.sha256(lines[row.first].raw).hexdigest() if span else None,
                "blocker_reason": row.blocker_reason,
                **row.extra,
            }
        )
    return out


def _mark_duplicates(rows: list[Row], key: str = "anchor_text") -> None:
    seen: dict[Any, list[Row]] = {}
    for row in rows:
        if row.row_kind == "item":
            value = row.anchor_text if key == "anchor_text" else row.extra.get(key)
            seen.setdefault(value, []).append(row)
    for group in seen.values():
        if len(group) > 1:
            for row in group:
                row.row_kind = "blocker"
                row.blocker_reason = "duplicate_anchor"


def _unaddressed(lines: list[Line], covered: set[int], region: range, structural: set[int]) -> list[Row]:
    rows: list[Row] = []
    run: list[int] = []
    for index in list(region) + [None]:  # type: ignore[list-item]
        if index is not None and index not in covered and index not in structural and not is_blank(lines[index]):
            run.append(index)
            continue
        if run:
            rows.append(Row("blocker", run[0], run[-1], blocker_reason="unaddressed_region"))
            run = []
    return rows


def _expand(spec: list[tuple[int, int]], count: int) -> set[int]:
    out: set[int] = set()
    for first, last in spec:
        if first < 1 or last > count or first > last:
            raise SegmentationError(f"structural range {first}:{last} is outside the file")
        out.update(range(first - 1, last))
    return out


def segment_heading_sections(
    lines: list[Line], level: int, region: tuple[int, int], structural: list[tuple[int, int]]
) -> list[Row]:
    """`heading_section`: items start at level-`level` ATX headings; an item ends before the next heading <= level."""
    first, last = region[0] - 1, region[1] - 1
    declared = _expand(structural, len(lines))
    anchors = [i for i in range(first, last + 1) if _heading_level(lines[i]) == level and i not in declared]
    rows: list[Row] = []
    covered: set[int] = set()
    for i in anchors:
        stop = last
        for j in range(i + 1, last + 1):
            if 1 <= _heading_level(lines[j]) <= level and j not in declared:
                stop = j - 1
                break
        end = _trim_trailing(lines, i, stop, rules_structural=True)
        text = _anchor_string(_heading_text(lines[i]))
        rows.append(
            Row("item", i, end, anchor_text=text)
            if text is not None
            else Row("blocker", i, end, blocker_reason="unparseable_anchor")
        )
        covered.update(range(i, end + 1))
    rules = {i for i in range(first, last + 1) if match_text(lines[i]).rstrip(b" \t") == b"---"}
    _mark_duplicates(rows)
    rows += _unaddressed(lines, covered, range(first, last + 1), declared | rules)
    return rows


def suppressed_anchors(
    lines: list[Line], level: int, region: tuple[int, int], structural: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    """Level-`level` headings inside declared structural ranges: they open no item, and the inventory records them."""
    declared = _expand(structural, len(lines))
    return [
        {
            "line": i + 1,
            "anchor_line_sha256": hashlib.sha256(lines[i].raw).hexdigest(),
            "heading_text": _anchor_string(_heading_text(lines[i])),
        }
        for i in range(region[0] - 1, region[1])
        if i in declared and _heading_level(lines[i]) == level
    ]


def segment_log_entries(lines: list[Line], region: tuple[int, int]) -> list[Row]:
    """`computational_log_entry`: level-2/3 headings whose text starts with a date token.

    A block opened by a heading of level L runs until the next heading of level <= L or the next date anchor, so a
    deeper sub-heading inside an entry belongs to that entry.
    """
    first, last = region[0] - 1, region[1] - 1
    headings = [i for i in range(first, last + 1) if 1 <= _heading_level(lines[i]) <= 6]

    def _is_anchor(index: int) -> bool:
        return _heading_level(lines[index]) in (2, 3) and bool(_LOG_DATE.match(_heading_text(lines[index])))

    rows: list[Row] = []
    covered: set[int] = set()
    covered_until = first - 1
    for i in headings:
        if i <= covered_until:
            continue
        level = _heading_level(lines[i])
        if level > 3:
            continue
        stop = last
        for j in headings:
            if j > i and (_heading_level(lines[j]) <= level or _is_anchor(j)):
                stop = j - 1
                break
        text = _heading_text(lines[i])
        end = _trim_trailing(lines, i, stop, rules_structural=True)
        covered_until = stop
        if _is_anchor(i):
            anchor = _anchor_string(text)
            if anchor is None:
                rows.append(Row("blocker", i, end, blocker_reason="unparseable_anchor"))
            else:
                rows.append(Row("item", i, end, anchor_text=anchor))
        elif level in (2, 3) and _LOOKS_DATED.match(text):
            rows.append(Row("blocker", i, end, blocker_reason="unparseable_anchor"))
        else:
            rows.append(Row("structural", i, end))
        covered.update(range(i, end + 1))
    _mark_duplicates(rows)
    preamble_end = headings[0] if headings else last + 1
    rules = {i for i in range(first, last + 1) if match_text(lines[i]).rstrip(b" \t") == b"---"}
    rows += _unaddressed(lines, covered, range(preamble_end, last + 1), rules)
    rows += [Row("structural", first, preamble_end - 1)] if preamble_end > first else []
    return rows


def _section_range(lines: list[Line], title: bytes) -> tuple[int, int]:
    start = next((i for i, line in enumerate(lines) if match_text(line).rstrip(b" \t") == b"## " + title), None)
    if start is None:
        raise SegmentationError(f"section '## {title.decode()}' not found")
    end = next((j - 1 for j in range(start + 1, len(lines)) if _heading_level(lines[j]) in (1, 2)), len(lines) - 1)
    return start + 1, end


def _split_cells(text: str) -> list[str]:
    cells, current, escaped = [], [], False
    for char in text:
        if char == "|" and not escaped:
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
    cells.append("".join(current))
    return [cell.strip() for cell in cells]


def segment_tracker_rows(lines: list[Line]) -> list[Row]:
    """`tracker_task_row`: rows of stage tables (header first cell `Task`) under `## Task Tracking`."""
    first, last = _section_range(lines, b"Task Tracking")
    rows: list[Row] = []
    index = first
    while index <= last:
        text = match_text(lines[index]).decode("utf-8", errors="replace")
        if not text.startswith("|"):
            index += 1
            continue
        block = index
        while block <= last and match_text(lines[block]).decode("utf-8", errors="replace").startswith("|"):
            block += 1
        header = _split_cells(match_text(lines[index]).decode("utf-8", errors="replace"))
        stage_table = len(header) > 1 and header[1] == "Task"
        for k in range(index, block):
            if not stage_table or k == index:
                continue
            decoded = _anchor_string(match_text(lines[k]))
            if decoded is None:
                rows.append(Row("blocker", k, k, blocker_reason="unparseable_anchor"))
                continue
            cells = _split_cells(decoded)
            cell = cells[1] if len(cells) > 1 else ""
            if _TABLE_SEPARATOR.match(decoded.strip()):
                continue
            if _TASK_CELL.match(cell):
                rows.append(Row("item", k, k, anchor_text=cell, extra={"task_id": f"T{cell}"}))
            else:
                rows.append(Row("blocker", k, k, blocker_reason="unaddressed_region"))
        index = block
    _mark_duplicates(rows)
    return rows


def segment_working_notes(lines: list[Line]) -> list[Row]:
    """`working_note_entry`: top-level bullets (`- ` at column 0) under `## Working Notes`."""
    first, last = _section_range(lines, b"Working Notes")
    anchors = [i for i in range(first, last + 1) if match_text(lines[i]).startswith(b"- ")]
    rows: list[Row] = []
    covered: set[int] = set()
    for position, i in enumerate(anchors):
        stop = (anchors[position + 1] - 1) if position + 1 < len(anchors) else last
        end = _trim_trailing(lines, i, stop, rules_structural=True)
        anchor = _anchor_string(match_text(lines[i]).rstrip(b" \t"))
        if anchor is None:
            rows.append(Row("blocker", i, end, blocker_reason="unparseable_anchor"))
        else:
            dated = bool(re.match(r"^- \*\*~?[0-9]{4}-[0-9]{2}-[0-9]{2}", anchor))
            rows.append(Row("item", i, end, anchor_text=anchor, extra={"dated": dated}))
        covered.update(range(i, end + 1))
    _mark_duplicates(rows)
    rules = {i for i in range(first, last + 1) if match_text(lines[i]).rstrip(b" \t") == b"---"}
    rows += _unaddressed(lines, covered, range(first, last + 1), rules)
    return rows


def segment_frontmatter(lines: list[Line]) -> list[Row]:
    """`log_frontmatter`: from line 1 `---` through the next `---` line, delimiters included."""
    if not lines:
        return [Row("blocker", 0, -1, blocker_reason="unparseable_anchor")]
    if match_text(lines[0]).rstrip(b" \t") != b"---":
        return [Row("blocker", 0, 0, blocker_reason="unparseable_anchor")]
    for j in range(1, len(lines)):
        if match_text(lines[j]).rstrip(b" \t") == b"---":
            return [Row("item", 0, j, anchor_text="frontmatter")]
    return [Row("blocker", 0, len(lines) - 1, blocker_reason="unparseable_anchor")]


def segment_conventions(lines: list[Line]) -> list[Row]:
    """`conventions_unit`: column-0 bullets, paragraphs and tables inside each `## ` section."""
    rows: list[Row] = []
    sections = [i for i, line in enumerate(lines) if _heading_level(line) == 2]
    for position, start in enumerate(sections):
        end = (sections[position + 1] - 1) if position + 1 < len(sections) else len(lines) - 1
        title = _anchor_string(_heading_text(lines[start])) or ""
        i = start + 1
        ordinal = 0
        while i <= end:
            text = match_text(lines[i])
            stripped = text.rstrip(b" \t")
            if is_blank(lines[i]) or stripped == b"---" or _FOOTER.match(stripped) or _heading_level(lines[i]):
                i += 1
                continue
            if text.startswith((b"- ", b"* ")):
                j = i + 1
                while j <= end:
                    nxt = match_text(lines[j])
                    if nxt[:1] in (b" ", b"\t") and not is_blank(lines[j]):
                        j += 1
                        continue
                    if is_blank(lines[j]):
                        k = j
                        while k <= end and is_blank(lines[k]):
                            k += 1
                        if k <= end and match_text(lines[k])[:1] in (b" ", b"\t"):
                            j = k
                            continue
                    break
                unit_end = _trim_trailing(lines, i, j - 1, rules_structural=False)
            elif text.startswith(b"|"):
                j = i
                while j <= end and match_text(lines[j]).startswith(b"|"):
                    j += 1
                unit_end = j - 1
            else:
                j = i
                while j <= end:
                    nxt = match_text(lines[j])
                    nxt_stripped = nxt.rstrip(b" \t")
                    if (
                        is_blank(lines[j])
                        or nxt.startswith((b"- ", b"* ", b"|"))
                        or nxt_stripped == b"---"
                        or _FOOTER.match(nxt_stripped)
                        or _heading_level(lines[j])
                    ):
                        break
                    j += 1
                unit_end = j - 1
            ordinal += 1
            span = b"".join(line.raw for line in lines[i : unit_end + 1])
            rows.append(
                Row(
                    "item",
                    i,
                    unit_end,
                    anchor_text=title,
                    extra={"unit_ordinal": ordinal, "unit_hash": hashlib.sha256(span).hexdigest()},
                )
            )
            i = unit_end + 1
    seen: dict[tuple[str | None, str], list[Row]] = {}
    for row in rows:
        seen.setdefault((row.anchor_text, row.extra["unit_hash"]), []).append(row)
    for group in seen.values():
        if len(group) > 1:
            for row in group:
                row.row_kind, row.blocker_reason = "blocker", "duplicate_anchor"
    return rows


def segment(
    data: bytes,
    selector_kind: str,
    *,
    level: int | None = None,
    region: tuple[int, int] | None = None,
    structural: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Segment `data` under one selector kind and return file facts plus rows.

    Args:
        data: The exact bytes read; never decoded, normalized or stripped of a BOM (contract §2.1).
        selector_kind: One of `heading_section`, `computational_log_entry`, `tracker_task_row`,
            `working_note_entry`, `log_frontmatter` or `conventions_unit` (contract §3).
        level: The heading level k; required for `heading_section`, ignored otherwise.
        region: The covered region as 1-based inclusive line numbers (first, last); defaults to the whole file.
            Used by `heading_section` and `computational_log_entry`; the other selectors have fixed regions.
        structural: Declared structural ranges as 1-based inclusive (first, last) pairs; `heading_section` only.

    Returns:
        A mapping with `segmentation_contract`, `selector_kind`, `file_sha256`, `file_bytes`, `file_facts`
        (line ending, final terminator, BOM, line count), `rows` (each with its ordinal, kind, anchor text, byte
        offset and length, start line, line count, `raw_row_sha256`, `anchor_line_sha256` and blocker reason) and
        `suppressed_anchors`.

    Raises:
        SegmentationError: For an unknown selector kind, a `heading_section` call without `level`, a structural
            range outside the file, or a missing `## Task Tracking` or `## Working Notes` section.
    """
    lines = split_lines(data)
    whole = (1, len(lines))
    suppressed: list[dict[str, Any]] = []
    if selector_kind == "heading_section":
        if level is None:
            raise SegmentationError("heading_section needs --level")
        rows = segment_heading_sections(lines, level, region or whole, structural or [])
        suppressed = suppressed_anchors(lines, level, region or whole, structural or [])
    elif selector_kind == "computational_log_entry":
        rows = segment_log_entries(lines, region or whole)
    elif selector_kind == "tracker_task_row":
        rows = segment_tracker_rows(lines)
    elif selector_kind == "working_note_entry":
        rows = segment_working_notes(lines)
    elif selector_kind == "log_frontmatter":
        rows = segment_frontmatter(lines)
    elif selector_kind == "conventions_unit":
        rows = segment_conventions(lines)
    else:
        raise SegmentationError(f"unknown selector kind: {selector_kind}")
    return {
        "segmentation_contract": CONTRACT_ID,
        "selector_kind": selector_kind,
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "file_bytes": len(data),
        "file_facts": file_facts(data, lines),
        "rows": _rows_to_json(lines, rows),
        "suppressed_anchors": suppressed,
    }


def _range(value: str) -> tuple[int, int]:
    first, _, last = value.partition(":")
    return int(first), int(last)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry: print the segmentation of one file as canonical JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("selector_kind")
    parser.add_argument("path", type=Path)
    parser.add_argument("--level", type=int)
    parser.add_argument("--region", type=_range)
    parser.add_argument("--structural", type=_range, action="append", default=[])
    args = parser.parse_args(argv)
    result = segment(
        args.path.read_bytes(),
        args.selector_kind,
        level=args.level,
        region=args.region,
        structural=args.structural,
    )
    sys.stdout.buffer.write((json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
