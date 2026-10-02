#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign H)
# Purpose: Lint the shared observation log and compute a review packet's completeness ledger,
# so neither a borrowed resolution stamp nor a hand-assembled "every item accounted for" can pass.
"""Lint ``~/.claude/skill-observations/log.md`` and, optionally, a review packet's ledger.

Checks:

* **A parse that finds nothing fails**, as does an observation with no ``**Status:**`` line: either
  would otherwise drop out of every ledger silently.
* **An unterminated code fence fails**, naming the line that opened it. It would otherwise turn every
  later heading into quoted code and drop every later observation; the later entries are still counted.
* **Fenced text is never a field.** A ``**Status:**`` or ``**Resolution:**`` inside a code fence is a
  quoted example; it is dropped before the fields are read.
* **Duplicate ids.** Concurrent sessions have collided on plain-integer numbering before.
* **Evidence-free closing stamps.** An ACTIONED/CLOSED/DECLINED status must name something a
  reader can check (a commit, PR, Jira key, file path or archive) on its Status line or in a
  ``**Resolution:**`` paragraph. ``**Progress:**`` notes do not count: they record interim work.
  The borrowed stamps of the 2026-09-08 reconciliation pass (obs
  2026-09-08-reconciliation-stamped-a-borrowed-resolution) read like resolutions and named
  nothing. DEFERRED is exempt: it claims no fix.
* **Identical closing text.** The same substantive Status or Resolution text on two ids is the
  borrowing shape, unless the text declares itself a ``batch disposition``.
* **OPEN means open work.** A status beginning OPEN, ESCALATED or PARTIALLY is in the OPEN set (owner
  default): an escalated entry awaits a decision and a partial one is half done, so neither may drop out
  of a ledger. DEFERRED claims no fix and stays outside it.
* **Completeness ledger** (``--packet``). The IDs column of the packet's "Completeness ledger"
  table must equal the log's OPEN set, computed rather than assembled (obs
  2026-09-01-completeness-ledger-missed-six-live-items: a hand ledger was wrong by six). Unknown,
  repeated and missing ids are named, and each row's Count, and the Total, must match its ids. The
  table must end with one row labelled Total: a ledger that omits it states no count to check.

Usage: python tools/observation_log_lint.py LOG.md [--packet PACKET.md]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_CLOSING = ("ACTIONED", "CLOSED", "DECLINED")
# A commit hash must carry a hex letter, or be introduced by the word "commit": an all-digit run is
# far more often a date or a count (`completed on 20260925`) than a hash.
_ARTIFACT = re.compile(
    r"github\.com/[\w.-]+/[\w.-]+/(?:pull|commit|issues)/\w+"
    r"|\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b|\bcommit\s+`?[0-9a-f]{7,40}\b|#\d+|\b[A-Z][A-Z0-9]+-\d+\b|archive/log-"
    r"|[\w-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,5}\b|\b[\w-]+\.(?:py|ps1|md|sh|yml|yaml|json|toml|txt|ts|js|lean|tex)\b"
)
# A bare status word ("CLOSED", "ACTIONED (2026-09-09)") is not borrowable text; the borrowed
# stamps were full sentences. Only substantive closing text is compared across ids.
_SUBSTANTIVE = 40
# Only the paragraphs that state the closure are evidence for it. A Progress paragraph records interim
# work, which may name an abandoned PR; it does not show that the resolution happened.
# The capture ends at a blank line or at the next ``**Field:**`` line, so an adjacent Progress field
# written directly under the Resolution is not read as part of it.
_RESOLUTION = re.compile(r"(?ms)^\*\*(?:Resolution|Closed)[^*]*:\*\*(.*?)(?=\n\s*\n|\n\*\*[^*\n]+:\*\*|\Z)")


_STATUSES = ("OPEN", "ACTIONED", "CLOSED", "DECLINED", "DEFERRED", "ESCALATED", "PARTIALLY")
# Open work: a status that has not been resolved. ESCALATED (an owner decision is awaited) and
# PARTIALLY (half the work is done) count (owner default from the 2026-10-02 dispatch): DEFERRED does not.
_OPEN_STATUSES = ("OPEN", "ESCALATED", "PARTIALLY")
_HEADING = "### Observation "


_FENCE = re.compile(r"\s*(`{3,}|~{3,})(.*)$")


def _fence_opener(line: str) -> str | None:
    """Return the fence run (``` or ~~~, any length of three or more) that opens a fenced block on this line."""
    match = _FENCE.match(line.rstrip("\r\n"))
    if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
        return match.group(1)
    return None


def _closes_fence(line: str, opener: str) -> bool:
    """A fence closes only on the same character, at least as long as the opener, with no text after it."""
    match = _FENCE.match(line.rstrip("\r\n"))
    return bool(
        match and match.group(1)[0] == opener[0] and len(match.group(1)) >= len(opener) and not match.group(2).strip()
    )


def _split(lines: list[str], ignored: set[int]) -> tuple[list[str], int | None]:
    """Split at observation headings outside fenced code; also return the line index of a fence left open, if any."""
    blocks: list[list[str]] = []
    opener: str | None = None
    opened_at = 0
    for index, line in enumerate(lines):
        # Fenced lines (the fences included) are quoted text, not fields of the entry: left in the block,
        # a quoted ``**Status:**`` or ``**Resolution:**`` was read as the entry's own.
        if opener is not None:
            if _closes_fence(line, opener):
                opener = None
            continue
        found = None if index in ignored else _fence_opener(line)
        if found:
            opener, opened_at = found, index
        elif line.startswith(_HEADING):
            blocks.append([line[len(_HEADING) :]])
        elif blocks:
            blocks[-1].append(line)
    return ["".join(block) for block in blocks], (opened_at if opener is not None else None)


def scan(log_text: str) -> tuple[list[str], list[str]]:
    """Split the log into observation blocks; also return a problem for every fence that is never closed.

    An unclosed fence made every later heading look like quoted code, so every later observation
    dropped out of the parse, the OPEN count and every ledger, silently. Each unterminated opener is
    reported with its line number, then the log is split again with that opener read as plain text,
    so the observations after it are still counted.
    """
    lines = log_text.splitlines(keepends=True)
    problems: list[str] = []
    ignored: set[int] = set()
    while True:
        blocks, opened_at = _split(lines, ignored)
        if opened_at is None:
            return blocks, problems
        ignored.add(opened_at)
        shown = lines[opened_at].strip()[:30]
        problems.append(
            f"unterminated fence {shown!r} opened at log line {opened_at + 1}: every observation after it "
            "would read as quoted code; close it, or the earlier fence that should have closed"
        )


def _blocks(log_text: str) -> list[str]:
    """Split the log at observation headings that sit outside fenced code, so a quoted template is not an entry."""
    return scan(log_text)[0]


def parse(log_text: str) -> list[tuple[str, str, str]]:
    """Return (id, status line, whole block) for every observation in order; the status is "" when absent."""
    return _entries(_blocks(log_text))


def _entries(blocks: list[str]) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for block in blocks:
        heading = block.split("\n", 1)[0]
        ident = re.split(r":\s", heading, maxsplit=1)[0].strip().strip("[]").rstrip(":")
        status = re.search(r"(?m)^\*\*Status:\*\*\s*(.*)$", block)
        entries.append((ident, status.group(1).strip() if status else "", block))
    return entries


def status_word(status: str) -> str:
    """Return the leading status word upper-cased, ignoring bold markers (``**OPEN**``); "" when there is none."""
    word = re.match(r"[*\s]*([A-Za-z]+)", status)
    return word.group(1).upper() if word else ""


def is_open(status: str) -> bool:
    """True for a status that is still open work: OPEN, and (owner default) ESCALATED or PARTIALLY.

    Only a leading OPEN counted before, so a standalone ESCALATED or PARTIALLY entry (an owner decision
    awaited, or half the work done) reached no ledger and no OPEN count: obs
    2026-09-30-system-review-prs-stopping-rule-follow-ups.
    """
    return status_word(status) in _OPEN_STATUSES


def lint(entries: list[tuple[str, str, str]]) -> list[str]:
    problems = [f"duplicate id {ident}" for ident, n in Counter(i for i, _, _ in entries).items() if n > 1]
    same: defaultdict[str, list[str]] = defaultdict(list)
    for ident, status, block in entries:
        if not status:
            # Neither OPEN nor closed, so it would silently drop out of every ledger.
            problems.append(f"{ident}: no **Status:** line")
            continue
        if status_word(status) not in _STATUSES:
            # A misspelt status (`OPEM`) is neither OPEN nor closed, so it would drop out of the ledger.
            problems.append(f"{ident}: unrecognised status {status[:40]!r}; expected one of {', '.join(_STATUSES)}")
            continue
        if status_word(status) not in _CLOSING:
            continue
        resolutions = [text.strip() for text in _RESOLUTION.findall(block)]
        if not _ARTIFACT.search(" ".join([status, *resolutions])):
            problems.append(f"{ident}: closing status names no checkable artifact: {status[:100]!r}")
        for text in (status, *resolutions):
            normalised = " ".join(text.split())
            if len(normalised) >= _SUBSTANTIVE and "batch disposition" not in normalised.lower():
                same[normalised].append(ident)
    problems += [
        f"identical closing text on {', '.join(sorted(set(ids)))}: {s[:80]!r}"
        for s, ids in same.items()
        if len(set(ids)) > 1
    ]
    return problems


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _count(cell: str) -> int | None:
    digits = cell.replace("*", "").strip()
    return int(digits) if digits.isdigit() else None


def parse_ledger(packet_text: str) -> tuple[list[str], list[str]]:
    """Return (every id listed in the ledger's IDs column, in order, problems with the table itself).

    Only the IDs column is read, so counts and group names are never mistaken for ids. Each row's
    Count must equal the ids it lists, and the row labelled Total (a Count with no ids) must be present,
    last, and equal their sum.
    """
    match = re.search(r"(?ms)^#+\s*Completeness ledger\s*$(.*?)(?=^#+\s|\Z)", packet_text)
    if not match:
        return [], ["the packet has no Completeness ledger section"]
    rows = [line for line in match.group(1).splitlines() if line.strip().startswith("|")]
    header = next((i for i, row in enumerate(rows) if "ids" in [c.lower() for c in _cells(row)]), None)
    if header is None:
        return [], ["the Completeness ledger has no table with an IDs column"]
    names = [c.lower() for c in _cells(rows[header])]
    if "count" not in names:
        return [], ["the Completeness ledger table has no Count column, so its rows cannot be checked"]
    id_col, count_col = names.index("ids"), names.index("count")
    listed: list[str] = []
    problems: list[str] = []
    totals: list[tuple[int, int | None]] = []  # (data-row position, declared total)
    position = 0
    for row in rows[header + 1 :]:
        cells = _cells(row)
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        position += 1
        ids = [t.strip("`") for t in re.split(r"[\s·,]+", cells[id_col] if id_col < len(cells) else "") if t.strip("`")]
        count = _count(cells[count_col]) if count_col < len(cells) else None
        if re.sub(r"[*`\s]", "", cells[0]).lower() == "total":
            # The Total is the row labelled Total. Any row with a count and no ids was read as one,
            # whatever it was called, and an unlabelled omission passed as a ledger with no Total.
            if ids:
                problems.append("the ledger's Total row lists ids; it must state only the count")
            totals.append((position, count))
            continue
        if count != len(ids):
            problems.append(f"ledger row {cells[0]!r} declares {cells[count_col]!r} but lists {len(ids)} id(s)")
        listed += ids
    # One Total, as the last row, checked against every id listed: a Total placed mid-table was
    # compared only with the rows above it. A ledger with no Total row stated no count to check.
    if not totals:
        problems.append("the ledger has no Total row; end the table with a row labelled Total giving the id count")
    elif len(totals) > 1:
        problems.append(f"the ledger has {len(totals)} Total rows; expected one")
    else:
        where, declared = totals[0]
        if where != position:
            problems.append("the ledger's Total row is not its last row")
        if declared != len(listed):
            problems.append(f"ledger total {declared} does not equal the {len(listed)} ids listed")
    return listed, problems


def ledger_ids(packet_text: str, known: set[str]) -> set[str]:
    """Return the ids listed in the packet's Completeness ledger that are known observation ids."""
    listed, _ = parse_ledger(packet_text)
    return {ident for ident in listed if ident in known}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint the observation log and a review packet's ledger.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--packet", type=Path, help="Review packet whose Completeness ledger must equal the OPEN set.")
    args = parser.parse_args(argv)

    blocks, fence_problems = scan(args.log.read_text(encoding="utf-8"))
    entries = _entries(blocks)
    if not entries:
        # An empty, truncated or re-formatted log must not read as a clean one.
        print(
            f"ERROR: no observations parsed from {args.log}; the log is empty or its headings changed", file=sys.stderr
        )
        return 1
    problems = fence_problems + lint(entries)
    known = {ident for ident, _, _ in entries}
    open_ids = {ident for ident, status, _ in entries if is_open(status)}
    print(f"{len(entries)} observation(s): {len(open_ids)} OPEN")

    if args.packet:
        listed, table_problems = parse_ledger(args.packet.read_text(encoding="utf-8"))
        problems += table_problems
        unknown = sorted({ident for ident in listed if ident not in known})
        repeated = sorted(ident for ident, n in Counter(listed).items() if n > 1)
        listed_known = {ident for ident in listed if ident in known}
        missing, stale = sorted(open_ids - listed_known), sorted(listed_known - open_ids)
        if missing:
            problems.append("OPEN but missing from the ledger: " + ", ".join(missing))
        if stale:
            problems.append("in the ledger but not OPEN: " + ", ".join(stale))
        if unknown:
            problems.append("in the ledger but not an observation id in the log: " + ", ".join(unknown))
        if repeated:
            problems.append("listed more than once in the ledger: " + ", ".join(repeated))
        if not (missing or stale or unknown or repeated or table_problems):
            print(f"ledger matches the {len(open_ids)} OPEN observation(s)")

    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
