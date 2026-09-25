#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign H)
# Purpose: Lint the shared observation log and compute a review packet's completeness ledger,
# so neither a borrowed resolution stamp nor a hand-assembled "every item accounted for" can pass.
"""Lint ``~/.claude/skill-observations/log.md`` and, optionally, a review packet's ledger.

Checks:

* **Duplicate ids.** Concurrent sessions have collided on plain-integer numbering before.
* **Evidence-free closing stamps.** An ACTIONED/CLOSED/DECLINED status must name something a
  reader can check (a commit, PR, Jira key, file path or archive) on its Status line or on a
  ``**Resolution:**`` line. The borrowed stamps of the 2026-09-08 reconciliation pass (obs
  2026-09-08-reconciliation-stamped-a-borrowed-resolution) read like resolutions and named
  nothing. DEFERRED is exempt: it claims no fix.
* **Identical closing stamps.** The same closing text on two ids is the borrowing shape, unless
  the text declares itself a ``batch disposition``.
* **Completeness ledger** (``--packet``). The ids in the packet's "Completeness ledger" section
  must equal the log's OPEN set, computed rather than assembled (obs
  2026-09-01-completeness-ledger-missed-six-live-items: a hand ledger was wrong by six).

Usage: python tools/observation_log_lint.py LOG.md [--packet PACKET.md]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_CLOSING = ("ACTIONED", "CLOSED", "DECLINED")
_ARTIFACT = re.compile(
    r"\b[0-9a-f]{7,40}\b|#\d+|\b[A-Z][A-Z0-9]+-\d+\b|archive/log-"
    r"|[\w-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,5}\b|\b[\w-]+\.(?:py|ps1|md|sh|yml|yaml|json|toml|txt|ts|js|lean|tex)\b"
)
# A bare status word ("CLOSED", "ACTIONED (2026-09-09)") is not borrowable text; the borrowed
# stamps were full sentences. Only substantive closing text is compared across ids.
_SUBSTANTIVE = 40


def parse(log_text: str) -> list[tuple[str, str, str]]:
    """Return (id, status line, whole block) for every observation in order."""
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
        if not status.upper().startswith(_CLOSING):
            continue
        resolutions = " ".join(
            re.findall(r"(?ms)^\*\*(?:Resolution|Progress|Closed)[^*]*:\*\*.*?(?=\n\s*\n|\Z)", block)
        )
        if not _ARTIFACT.search(status + " " + resolutions):
            problems.append(f"{ident}: closing status names no checkable artifact: {status[:100]!r}")
        if len(status) >= _SUBSTANTIVE and "batch disposition" not in status.lower():
            same[status].append(ident)
    problems += [f"identical closing status on {', '.join(ids)}: {s[:80]!r}" for s, ids in same.items() if len(ids) > 1]
    return problems


def ledger_ids(packet_text: str, known: set[str]) -> set[str]:
    """Return the known ids that appear in the packet's Completeness ledger section."""
    match = re.search(r"(?ms)^#+\s*Completeness ledger\s*$(.*?)(?=^#+\s|\Z)", packet_text)
    section = match.group(1) if match else ""
    tokens = set(re.findall(r"[A-Za-z0-9][\w.-]*", section))
    return {ident for ident in known if ident in tokens}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint the observation log and a review packet's ledger.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--packet", type=Path, help="Review packet whose Completeness ledger must equal the OPEN set.")
    args = parser.parse_args(argv)

    entries = parse(args.log.read_text(encoding="utf-8"))
    problems = lint(entries)
    open_ids = {ident for ident, status, _ in entries if is_open(status)}
    print(f"{len(entries)} observation(s): {len(open_ids)} OPEN")

    if args.packet:
        listed = ledger_ids(args.packet.read_text(encoding="utf-8"), {ident for ident, _, _ in entries})
        missing, stale = sorted(open_ids - listed), sorted(listed - open_ids)
        if missing:
            problems.append("OPEN but missing from the ledger: " + ", ".join(missing))
        if stale:
            problems.append("in the ledger but not OPEN: " + ", ".join(stale))
        if not missing and not stale:
            print(f"ledger matches the {len(open_ids)} OPEN observation(s)")

    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
