#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign H)
# Purpose: Lint the shared observation log and compute a review packet's completeness ledger,
# so neither a borrowed resolution stamp nor a hand-assembled "every item accounted for" can pass.
"""Lint ``~/.claude/skill-observations/log.md`` and, optionally, a review packet's ledger.

Checks:

* **A parse that finds nothing fails**, as does an observation with no ``**Status:**`` line: either
  would otherwise drop out of every ledger silently.
* **Duplicate ids.** Concurrent sessions have collided on plain-integer numbering before.
* **Evidence-free closing stamps.** An ACTIONED/CLOSED/DECLINED status must name something a
  reader can check (a commit, PR, Jira key, file path or archive) on its Status line or in a
  ``**Resolution:**`` paragraph. ``**Progress:**`` notes do not count: they record interim work.
  The borrowed stamps of the 2026-09-08 reconciliation pass (obs
  2026-09-08-reconciliation-stamped-a-borrowed-resolution) read like resolutions and named
  nothing. DEFERRED is exempt: it claims no fix.
* **Identical closing text.** The same substantive Status or Resolution text on two ids is the
  borrowing shape, unless the text declares itself a ``batch disposition``.
* **Completeness ledger** (``--packet``). The IDs column of the packet's "Completeness ledger"
  table must equal the log's OPEN set, computed rather than assembled (obs
  2026-09-01-completeness-ledger-missed-six-live-items: a hand ledger was wrong by six). Unknown,
  repeated and missing ids are named, and each row's Count, and the Total, must match its ids.

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
    r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b|\bcommit\s+`?[0-9a-f]{7,40}\b|#\d+|\b[A-Z][A-Z0-9]+-\d+\b|archive/log-"
    r"|[\w-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,5}\b|\b[\w-]+\.(?:py|ps1|md|sh|yml|yaml|json|toml|txt|ts|js|lean|tex)\b"
)
# A bare status word ("CLOSED", "ACTIONED (2026-09-09)") is not borrowable text; the borrowed
# stamps were full sentences. Only substantive closing text is compared across ids.
_SUBSTANTIVE = 40
# Only the paragraphs that state the closure are evidence for it. A Progress paragraph records interim
# work, which may name an abandoned PR; it does not show that the resolution happened.
_RESOLUTION = re.compile(r"(?ms)^\*\*(?:Resolution|Closed)[^*]*:\*\*(.*?)(?=\n\s*\n|\Z)")


def parse(log_text: str) -> list[tuple[str, str, str]]:
    """Return (id, status line, whole block) for every observation in order; the status is "" when absent."""
    entries: list[tuple[str, str, str]] = []
    for block in re.split(r"(?m)^### Observation ", log_text)[1:]:
        heading = block.split("\n", 1)[0]
        ident = re.split(r":\s", heading, maxsplit=1)[0].strip().strip("[]").rstrip(":")
        status = re.search(r"(?m)^\*\*Status:\*\*\s*(.*)$", block)
        entries.append((ident, status.group(1).strip() if status else "", block))
    return entries


def is_open(status: str) -> bool:
    return status.upper().startswith("OPEN")


def lint(entries: list[tuple[str, str, str]]) -> list[str]:
    problems = [f"duplicate id {ident}" for ident, n in Counter(i for i, _, _ in entries).items() if n > 1]
    same: defaultdict[str, list[str]] = defaultdict(list)
    for ident, status, block in entries:
        if not status:
            # Neither OPEN nor closed, so it would silently drop out of every ledger.
            problems.append(f"{ident}: no **Status:** line")
            continue
        if not status.upper().startswith(_CLOSING):
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
    Count must equal the ids it lists, and a Total row (a Count with no ids) must equal their sum.
    """
    match = re.search(r"(?ms)^#+\s*Completeness ledger\s*$(.*?)(?=^#+\s|\Z)", packet_text)
    if not match:
        return [], ["the packet has no Completeness ledger section"]
    rows = [line for line in match.group(1).splitlines() if line.strip().startswith("|")]
    header = next((i for i, row in enumerate(rows) if "ids" in [c.lower() for c in _cells(row)]), None)
    if header is None:
        return [], ["the Completeness ledger has no table with an IDs column"]
    names = [c.lower() for c in _cells(rows[header])]
    id_col, count_col = names.index("ids"), names.index("count") if "count" in names else None
    listed: list[str] = []
    problems: list[str] = []
    counted = 0
    for row in rows[header + 1 :]:
        cells = _cells(row)
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        ids = [t.strip("`") for t in re.split(r"[\s·,]+", cells[id_col] if id_col < len(cells) else "") if t.strip("`")]
        count = _count(cells[count_col]) if count_col is not None and count_col < len(cells) else None
        if not ids:
            if count is not None and count != counted:
                problems.append(f"ledger total {count} does not equal the {counted} ids listed")
            continue
        if count_col is not None and count != len(ids):
            problems.append(f"ledger row {cells[0]!r} declares {cells[count_col]!r} but lists {len(ids)} id(s)")
        counted += len(ids)
        listed += ids
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

    entries = parse(args.log.read_text(encoding="utf-8"))
    if not entries:
        # An empty, truncated or re-formatted log must not read as a clean one.
        print(
            f"ERROR: no observations parsed from {args.log}; the log is empty or its headings changed", file=sys.stderr
        )
        return 1
    problems = lint(entries)
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
