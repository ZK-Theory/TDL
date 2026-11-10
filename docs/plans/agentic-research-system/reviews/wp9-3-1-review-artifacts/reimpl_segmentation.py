# Research context: docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md (owner point I, P-068)
# Purpose: an independent re-implementation of w9-segmentation/1.0.0, written by WP9.3-1's independent reviewer from
# the contract text and its vectors alone, before reading tools/w9_segmentation.py or research_system/legacy/
# segmentation.py. Review artefact only: not runtime code, not imported by research_system/.
"""Independent re-implementation of ``w9-segmentation/1.0.0`` (contract §7, "Independence").

Where the contract text leaves a choice open, the choice made here is marked ``READING`` and listed in the review
report (§3 of ``wp9-3-1-review-23f8f737-2026-11-10.md``), with whether the vectors fix it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

CONTRACT = "w9-segmentation/1.0.0"
BOM = b"\xef\xbb\xbf"
SELECTORS = (
    "heading_section",
    "computational_log_entry",
    "tracker_task_row",
    "working_note_entry",
    "log_frontmatter",
    "conventions_unit",
)
# §3 date token, matched at the start of the heading text, then end of text, space, tab or "(".
DATE_TOKEN = re.compile(rb"~?[0-9]{4}-[0-9]{2}(-[0-9]{2}([a-z]|/[0-9]{2})?)?(?=$|[ \t(])")
TASK_GRAMMAR = re.compile(r"[0-9]+\.[0-9]+[a-z]*(-[a-z]+)?")
DATED_NOTE = re.compile(rb"- \*\*~?[0-9]{4}-[0-9]{2}-[0-9]{2}")
FOOTER = re.compile(rb"\*Last updated: .*\*")

# Readings of text the contract leaves open. The values below are the reviewer's first, independent choices (commit
# fe24b28a). ALIGNED holds the runtime segmenter's choice for each, found by the differential test after that commit.
# Keys "R-n" are readings the contract text leaves open; keys "C-n" are places where the runtime departs from the
# contract's words, and the first value there is the contract's (except C-2, see the report).
FIRST_READINGS: dict[str, str] = {
    "R-1 block trim": "blank-only",  # runtime: "blank-and-rule"
    "R-3 suppressed record": "level<=k",  # runtime: "level==k"
    "R-4 preamble": "trimmed",  # runtime: "whole"
    "R-5 tracker utf8": "first-cell",  # runtime: "whole-row"
    "R-7 conventions section end": "level<=2",  # runtime: "level==2"
    "R-8 empty-file anchor hash": "sha256-of-empty",  # runtime: "none"
    "C-1 tracker cell trim": "spaces",  # runtime: "all-whitespace"
    "C-2 invalid section title": "item-none",  # contract: "blocker"; runtime: "item-empty"
    "C-3 conventions footer": "exact",  # runtime: "trailing-ws-trimmed"
}
READINGS: dict[str, str] = dict(FIRST_READINGS)


class ReimplError(ValueError):
    """Segmentation refused (contract §3 "Missing sections"), or a bad call."""


@dataclass(frozen=True)
class Line:
    """One line (contract §2.2): bytes with terminator, its text and match text, and its offset."""

    number: int
    raw: bytes
    text: bytes
    match: bytes
    start: int
    terminator: str  # "LF", "CRLF" or ""


def split_lines(data: bytes) -> list[Line]:
    """Split on LF; the terminator is CRLF when the LF follows CR (§2.2); BOM removed from match text (§2.3)."""
    out: list[Line] = []
    pos = 0
    number = 0
    while pos < len(data):
        nl = data.find(b"\n", pos)
        end = len(data) if nl < 0 else nl + 1
        raw = data[pos:end]
        if nl < 0:
            text, term = raw, ""
        elif raw.endswith(b"\r\n"):
            text, term = raw[:-2], "CRLF"
        else:
            text, term = raw[:-1], "LF"
        number += 1
        match = text[len(BOM) :] if number == 1 and text.startswith(BOM) else text
        out.append(Line(number, raw, text, match, pos, term))
        pos = end
    return out


def file_facts(data: bytes, lines: list[Line]) -> dict[str, Any]:
    """§2.8: line-ending kind, final terminator, BOM, line count. Nothing is corrected."""
    kinds = {line.terminator for line in lines if line.terminator}
    if not kinds:
        ending = "none"
    elif len(kinds) == 2:
        ending = "mixed"
    else:
        ending = kinds.pop()
    return {
        "line_ending": ending,
        "ends_with_terminator": data.endswith(b"\n"),
        "has_utf8_bom": data.startswith(BOM),
        "line_count": len(lines),
    }


def is_blank(line: Line) -> bool:
    """§2.4."""
    return line.match.strip(b" \t") == b""


def is_rule(line: Line) -> bool:
    """§2.5."""
    return line.match.rstrip(b" \t") == b"---"


def heading(line: Line) -> tuple[int, bytes] | None:
    """§2.7: (level, heading-text bytes) for an ATX heading of level 1 to 6, else None."""
    m = line.match
    k = 0
    while k < len(m) and m[k : k + 1] == b"#":
        k += 1
    if not 1 <= k <= 6 or m[k : k + 1] != b" ":
        return None
    return k, m[k + 1 :].rstrip(b" \t")


def decode(raw: bytes) -> str | None:
    """§3 anchor text: UTF-8, never repaired; None when the bytes are not valid UTF-8."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Builder:
    """Collects rows and emits them in line order with ordinals."""

    def __init__(self, lines: list[Line]) -> None:
        self.lines = lines
        self.rows: list[dict[str, Any]] = []

    def add(self, kind: str, first: int, last: int, anchor: str | None, reason: str | None, **extra: Any) -> None:
        span = self.lines[first - 1 : last]
        raw = b"".join(line.raw for line in span)
        row = {
            "row_kind": kind,
            "start_line": first,
            "line_count": last - first + 1,
            "start_byte": span[0].start,
            "byte_length": len(raw),
            "raw_row_sha256": sha(raw),
            "anchor_line_sha256": sha(span[0].raw),
            "anchor_text": anchor,
            "blocker_reason": reason,
        }
        row.update(extra)
        self.rows.append(row)

    def finish(self) -> list[dict[str, Any]]:
        self.rows.sort(key=lambda r: r["start_line"])
        for i, row in enumerate(self.rows, start=1):
            row["row_ordinal"] = i
        return self.rows


def trim_item(lines: list[Line], first: int, end_excl: int) -> int:
    """Span rule (§3): the last line before the boundary that is neither blank nor a rule line; never above first."""
    last = end_excl - 1
    while last > first and (is_blank(lines[last - 1]) or is_rule(lines[last - 1])):
        last -= 1
    return last


def trim_block(lines: list[Line], first: int, end_excl: int) -> int:
    """READING R-1: structural blocks and block blockers drop trailing blank lines only, not rule lines."""
    if READINGS["R-1 block trim"] == "blank-and-rule":
        return trim_item(lines, first, end_excl)
    last = end_excl - 1
    while last > first and is_blank(lines[last - 1]):
        last -= 1
    return last


def unaddressed(b: Builder, lines: list[Line], region: tuple[int, int], covered: set[int]) -> None:
    """§4.4: each maximal run of consecutive non-blank, non-rule lines outside every item or block (READING R-2)."""
    run: list[int] = []
    for n in range(region[0], region[1] + 1):
        line = lines[n - 1]
        if n not in covered and not is_blank(line) and not is_rule(line):
            run.append(n)
            continue
        if run:
            b.add("blocker", run[0], run[-1], None, "unaddressed_region")
            run = []
    if run:
        b.add("blocker", run[0], run[-1], None, "unaddressed_region")


def mark_duplicates(items: list[dict[str, Any]], key: str = "anchor_text") -> None:
    """§4.3: every item sharing an identity with another becomes a duplicate_anchor blocker, anchor text kept."""
    counts: dict[Any, int] = {}
    for row in items:
        counts[row["_id"]] = counts.get(row["_id"], 0) + 1
    for row in items:
        if counts[row["_id"]] > 1:
            row["row_kind"] = "blocker"
            row["blocker_reason"] = "duplicate_anchor"


def _region(lines: list[Line], region: tuple[int, int] | None) -> tuple[int, int]:
    if region is None:
        return (1, len(lines))
    first, last = region
    if not 1 <= first <= last <= len(lines):
        raise ReimplError(f"region {region} outside 1..{len(lines)}")
    return first, last


def seg_heading_section(
    b: Builder, lines: list[Line], level: int, region: tuple[int, int], structural: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    """§3 heading_section."""
    in_struct = {n for lo, hi in structural for n in range(lo, hi + 1)}
    suppressed: list[dict[str, Any]] = []
    bounds: list[int] = []  # non-suppressed headings of level <= k
    anchors: list[tuple[int, bytes]] = []
    for n in range(region[0], region[1] + 1):
        h = heading(lines[n - 1])
        if h is None or h[0] > level:
            continue
        if n in in_struct:
            # READING R-3: every heading of level <= k inside a declared structural range is suppressed; "level<=k"
            # records each of them, "level==k" records only the would-be anchors.
            if READINGS["R-3 suppressed record"] == "level<=k" or h[0] == level:
                suppressed.append(
                    {"line": n, "anchor_line_sha256": sha(lines[n - 1].raw), "heading_text": decode(h[1])}
                )
            continue
        bounds.append(n)
        if h[0] == level:
            anchors.append((n, h[1]))
    covered = set(in_struct)
    items: list[dict[str, Any]] = []
    for n, text in anchors:
        nxt = [m for m in bounds if m > n]
        end_excl = nxt[0] if nxt else region[1] + 1
        covered.update(range(n, end_excl))
        last = trim_item(lines, n, end_excl)
        anchor = decode(text)
        if anchor is None:
            b.add("blocker", n, last, None, "unparseable_anchor")
            continue
        b.add("item", n, last, anchor, None, _id=anchor)
        items.append(b.rows[-1])
    mark_duplicates(items)
    unaddressed(b, lines, region, covered)
    return suppressed


def seg_log(b: Builder, lines: list[Line], region: tuple[int, int]) -> None:
    """§3 computational_log_entry, with non-anchor heading blocks and the preamble."""
    first_heading = next((n for n in range(region[0], region[1] + 1) if heading(lines[n - 1])), None)
    pre_end = (first_heading or region[1] + 1) - 1
    if READINGS["R-4 preamble"] == "whole":
        if pre_end >= region[0]:
            b.add("structural", region[0], pre_end, None, None)
    elif pre_end >= region[0] and any(not is_blank(lines[n - 1]) for n in range(region[0], pre_end + 1)):
        # READING R-4: the preamble is one structural row, from the region's first line, trailing blanks dropped.
        last = pre_end
        while last > region[0] and is_blank(lines[last - 1]):
            last -= 1
        b.add("structural", region[0], last, None, None)
    covered = set(range(region[0], pre_end + 1))

    def classify(n: int) -> tuple[str, int, bytes] | None:
        h = heading(lines[n - 1])
        if h is None or h[0] > 3:
            return None
        lvl, text = h
        if lvl in (2, 3) and DATE_TOKEN.match(text):
            return "date", lvl, text
        if lvl in (2, 3) and (text[:1].isdigit() or (text[:1] == b"~" and text[1:2].isdigit())):
            return "looks", lvl, text
        return "other", lvl, text

    opens = [(n, c) for n in range(region[0], region[1] + 1) if (c := classify(n))]
    items: list[dict[str, Any]] = []
    i = 0
    while i < len(opens):
        n, (kind, lvl, text) = opens[i]
        j = i + 1
        # A block ends at the next heading of level <= its level, or at the next date anchor.
        while j < len(opens) and not (opens[j][1][1] <= lvl or opens[j][1][0] == "date"):
            j += 1
        end_excl = opens[j][0] if j < len(opens) else region[1] + 1
        covered.update(range(n, end_excl))
        if kind == "date":
            last = trim_item(lines, n, end_excl)
            anchor = decode(text)
            if anchor is None:
                b.add("blocker", n, last, None, "unparseable_anchor")
            else:
                b.add("item", n, last, anchor, None, _id=anchor)
                items.append(b.rows[-1])
        elif kind == "looks":
            b.add("blocker", n, trim_block(lines, n, end_excl), None, "unparseable_anchor")
        else:
            b.add("structural", n, trim_block(lines, n, end_excl), None, None)
        i = j
    mark_duplicates(items)
    unaddressed(b, lines, region, covered)


def _section(lines: list[Line], title: bytes) -> tuple[int, int]:
    """The fixed region after a level-2 heading named ``title``, to before the next level 1 or 2 heading."""
    start = next((line.number for line in lines if heading(line) == (2, title)), None)
    if start is None:
        raise ReimplError(f"no '## {title.decode()}' section: segmentation refused")
    end = len(lines)
    for line in lines[start:]:
        h = heading(line)
        if h is not None and h[0] <= 2:
            end = line.number - 1
            break
    return start + 1, end


def _strip(cell: bytes) -> bytes:
    """C-1: the contract trims spaces; the runtime's str.strip() trims every Unicode whitespace character."""
    if READINGS["C-1 tracker cell trim"] == "all-whitespace":
        return cell.decode("utf-8", errors="replace").strip().encode("utf-8")
    return cell.strip(b" ")


def _cells(text: bytes) -> list[bytes]:
    """Split on "|" not preceded by a backslash; trim spaces; drop the empty piece before the leading pipe."""
    cells = re.split(rb"(?<!\\)\|", text)
    if cells and _strip(cells[0]) == b"":
        cells = cells[1:]
    if cells and _strip(cells[-1]) == b"" and _strip(text).endswith(b"|"):
        cells = cells[:-1]
    return [_strip(c) for c in cells]


def seg_tracker(b: Builder, lines: list[Line]) -> None:
    """§3 tracker_task_row."""
    lo, hi = _section(lines, b"Task Tracking")
    items: list[dict[str, Any]] = []
    n = lo
    while n <= hi:
        if not lines[n - 1].match.startswith(b"|"):
            n += 1
            continue
        table = []
        while n <= hi and lines[n - 1].match.startswith(b"|"):
            table.append(n)
            n += 1
        first_cells = _cells(lines[table[0] - 1].match)
        if not first_cells or first_cells[0] != b"Task":
            continue  # not a stage table: structural
        for m in table[1:]:
            if READINGS["R-5 tracker utf8"] == "whole-row" and decode(lines[m - 1].match) is None:
                b.add("blocker", m, m, None, "unparseable_anchor")
                continue
            cells = _cells(lines[m - 1].match)
            if cells and all(re.fullmatch(rb":?-+:?", c) for c in cells):
                continue  # separator row
            cell = cells[0] if cells else b""
            text = decode(cell)  # READING R-5: the UTF-8 check is on the first cell's bytes
            if text is None:
                b.add("blocker", m, m, None, "unparseable_anchor")
            elif TASK_GRAMMAR.fullmatch(text):
                b.add("item", m, m, text, None, task_id="T" + text, _id=text)
                items.append(b.rows[-1])
            else:
                b.add("blocker", m, m, None, "unaddressed_region")
    mark_duplicates(items)


def seg_working_notes(b: Builder, lines: list[Line]) -> None:
    """§3 working_note_entry."""
    lo, hi = _section(lines, b"Working Notes")
    starts = [n for n in range(lo, hi + 1) if lines[n - 1].match.startswith(b"- ")]
    covered: set[int] = set()
    items: list[dict[str, Any]] = []
    for i, n in enumerate(starts):
        end_excl = starts[i + 1] if i + 1 < len(starts) else hi + 1
        covered.update(range(n, end_excl))
        raw_anchor = lines[n - 1].match.rstrip(b" \t")
        anchor = decode(raw_anchor)
        last = trim_item(lines, n, end_excl)
        if anchor is None:
            b.add("blocker", n, last, None, "unparseable_anchor")
            continue
        b.add("item", n, last, anchor, None, dated=bool(DATED_NOTE.match(raw_anchor)), _id=anchor)
        items.append(b.rows[-1])
    mark_duplicates(items)
    if lo <= hi:
        unaddressed(b, lines, (lo, hi), covered)


def seg_frontmatter(b: Builder, lines: list[Line]) -> None:
    """§3 log_frontmatter; §4.5 blockers."""
    if not lines:
        b.rows.append(
            {
                "row_kind": "blocker",
                "start_line": 1,
                "line_count": 0,
                "start_byte": 0,
                "byte_length": 0,
                "raw_row_sha256": sha(b""),
                "anchor_line_sha256": sha(b"") if READINGS["R-8 empty-file anchor hash"] == "sha256-of-empty" else None,
                "anchor_text": None,
                "blocker_reason": "unparseable_anchor",
            }
        )
        return
    if not is_rule(lines[0]):
        b.add("blocker", 1, 1, None, "unparseable_anchor")  # READING R-6: line 1 alone
        return
    close = next((line.number for line in lines[1:] if is_rule(line)), None)
    if close is None:
        b.add("blocker", 1, len(lines), None, "unparseable_anchor")  # READING R-6: the whole file
        return
    b.add("item", 1, close, "frontmatter", None)


def seg_conventions(b: Builder, lines: list[Line]) -> None:
    """§3 conventions_unit."""
    sections: list[tuple[int, int, str | None]] = []
    heads = [(line.number, heading(line)) for line in lines]
    starts = [n for n, h in heads if h is not None and h[0] == 2]
    for i, n in enumerate(starts):
        end = len(lines)
        for m, h in heads[n:]:
            stops = h is not None and (
                h[0] <= 2 if READINGS["R-7 conventions section end"] == "level<=2" else h[0] == 2
            )
            if stops:  # READING R-7: a level-1 heading also ends a section
                end = m - 1
                break
        text = heads[n - 1][1]
        assert text is not None
        sections.append((n, end, decode(text[1])))
    items: list[dict[str, Any]] = []
    for start, end, title in sections:
        ordinal = 0
        invalid_title = title is None
        if invalid_title and READINGS["C-2 invalid section title"] == "item-empty":
            title = ""

        def structural_line(line: Line) -> bool:
            footer_text = line.match
            if READINGS["C-3 conventions footer"] == "trailing-ws-trimmed":
                footer_text = footer_text.rstrip(b" \t")
            return is_blank(line) or is_rule(line) or bool(FOOTER.fullmatch(footer_text)) or heading(line) is not None

        def bullet(line: Line) -> bool:
            return line.match.startswith((b"- ", b"* "))

        def table_line(line: Line) -> bool:
            return line.match.startswith(b"|")

        n = start + 1
        while n <= end:
            line = lines[n - 1]
            if structural_line(line):
                n += 1
                continue
            if bullet(line):
                j = n + 1
                while j <= end:
                    cur = lines[j - 1]
                    if is_blank(cur):
                        k = j
                        while k <= end and is_blank(lines[k - 1]):
                            k += 1
                        if k <= end and lines[k - 1].match[:1] in (b" ", b"\t"):
                            j = k
                            continue
                        break
                    if cur.match[:1] in (b" ", b"\t"):
                        j += 1
                        continue
                    break
                last = trim_item(lines, n, j)
            elif table_line(line):
                j = n
                while j <= end and table_line(lines[j - 1]):
                    j += 1
                last = j - 1
            else:
                j = n
                while j <= end:
                    cur = lines[j - 1]
                    if structural_line(cur) or bullet(cur) or table_line(cur):
                        break
                    j += 1
                last = j - 1
            ordinal += 1
            span = b"".join(x.raw for x in lines[n - 1 : last])
            if invalid_title and READINGS["C-2 invalid section title"] == "blocker":
                # Contract §3: anchor bytes that are not valid UTF-8 make the row a blocker (unparseable_anchor).
                b.add("blocker", n, last, None, "unparseable_anchor", unit_ordinal=ordinal, unit_hash=sha(span))
            else:
                b.add("item", n, last, title, None, unit_ordinal=ordinal, unit_hash=sha(span), _id=(title, sha(span)))
                items.append(b.rows[-1])
            n = j
    mark_duplicates(items)


def segment(
    data: bytes,
    selector: str,
    *,
    level: int | None = None,
    region: tuple[int, int] | None = None,
    structural: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Segment ``data`` under ``selector``; the result mirrors a light inventory's rows plus suppressed anchors."""
    if selector not in SELECTORS:
        raise ReimplError(f"unknown selector {selector!r}")
    lines = split_lines(data)
    b = Builder(lines)
    suppressed: list[dict[str, Any]] = []
    if selector == "heading_section":
        if level is None or not 1 <= level <= 6:
            raise ReimplError("heading_section needs a declared level k")
        suppressed = seg_heading_section(b, lines, level, _region(lines, region), list(structural or []))
    elif selector == "computational_log_entry":
        seg_log(b, lines, _region(lines, region))
    elif selector == "tracker_task_row":
        seg_tracker(b, lines)
    elif selector == "working_note_entry":
        seg_working_notes(b, lines)
    elif selector == "log_frontmatter":
        seg_frontmatter(b, lines)
    else:
        seg_conventions(b, lines)
    rows = b.finish()
    for row in rows:
        row.pop("_id", None)
    return {
        "segmentation_contract": CONTRACT,
        "selector_kind": selector,
        "file_sha256": sha(data),
        "file_facts": file_facts(data, lines),
        "rows": rows,
        "suppressed_anchors": suppressed,
    }
