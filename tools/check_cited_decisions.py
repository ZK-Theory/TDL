#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-10-27-decision-report.md (Group E, item 2)
# Purpose: Before a brief or handoff is issued, report every P-NNN it cites that a later register entry supersedes
# or amends, so a superseded decision is not carried into intake as a live constraint.
"""Report cited decisions that a later register entry supersedes or amends.

Obs 2026-10-21-gate7-brief-restated-superseded-and-closed-items: the Gate 7 prep brief asked whether P-033 binds
Gate 7 compute. P-042 had superseded P-033 nearly three months earlier, and 06g said so in a table.

The register (``03-decisions-and-open-questions.md``) heads each decision ``### P-NNN — title`` and records
supersession in ``**Supersedes:**`` and amendment in ``**Amends:**`` fields. For each file given, every ``P-NNN``
it cites is looked up. A citation is reported when a later entry supersedes or amends it and the citing line does
not also name that later entry. Supersession fails the run; amendment is reported as a note, because an amended
decision usually still stands in part.

Usage: python tools/check_cited_decisions.py FILE [FILE ...] [--register PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REGISTER = Path("docs/plans/agentic-research-system/03-decisions-and-open-questions.md")
_ENTRY = re.compile(r"(?m)^### (P-\d{3})\b")
_FIELD = re.compile(r"(?ms)^\*\*(Supersedes|Amends):\*\*(.*?)(?=^\*\*[^*\n]+:\*\*|^\s*$|^#)")
_ID = re.compile(r"\bP-\d{3}\b")


def later_entries(register_text: str) -> dict[str, list[tuple[str, str]]]:
    """Map each decision id to the (later id, "supersedes" | "amends") entries that name it."""
    starts = [(m.start(), m.group(1)) for m in _ENTRY.finditer(register_text)]
    named: dict[str, list[tuple[str, str]]] = {}
    for index, (start, ident) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(register_text)
        for field in _FIELD.finditer(register_text[start:end]):
            kind = field.group(1).lower()
            # "Supersedes: P-033 ...; amends P-035" names P-035 as an amendment, not a supersession.
            for clause in re.split(r";", field.group(2)):
                clause_kind = "amends" if kind == "supersedes" and re.search(r"(?i)\bamend", clause) else kind
                for cited in _ID.findall(clause):
                    if cited != ident:
                        named.setdefault(cited, []).append((ident, clause_kind))
    return named


def check(paths: list[Path], register_text: str) -> tuple[list[str], list[str]]:
    """Return (problems, notes): unacknowledged supersessions and unacknowledged amendments."""
    named = later_entries(register_text)
    problems: list[str] = []
    notes: list[str] = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for cited in dict.fromkeys(_ID.findall(line)):
                for later, kind in named.get(cited, []):
                    if later in line:
                        continue
                    text = f"{path}:{number}: cites {cited}, which {later} {kind}"
                    (problems if kind == "supersedes" else notes).append(text)
    return problems, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--register", type=Path, default=Path(__file__).resolve().parents[1] / REGISTER)
    args = parser.parse_args(argv)
    problems, notes = check(args.files, args.register.read_text(encoding="utf-8"))
    print(f"cited decisions: {len(problems)} superseded, {len(notes)} amended without the later entry named")
    for line in notes:
        print(f"NOTE: {line}")
    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
