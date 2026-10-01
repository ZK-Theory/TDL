#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Fail a CI lane whose controls skipped or never ran, which a green pytest exit hides.
"""Fail when a pytest JUnit report contains skipped tests, or no tests at all.

Why (obs 2026-09-17-hook-test-outside-ci-rotted-after-a-gate-was-added): the git-hook suites
skip when Git Bash is missing, and a lane of skipped controls still exits 0 and shows green.
A lane that ran zero tests is the same failure seen from the other side (obs
2026-09-16-red-run-exit-code-shared-with-missing-pytest): an exit code alone cannot tell a
passing control from one that never executed.

Usage: python tools/assert_no_skips.py report.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def summarise(report: Path) -> tuple[int, list[str]]:
    """Return (tests executed, ids of skipped tests) from a pytest JUnit XML report."""
    root = ET.parse(report).getroot()
    cases = list(root.iter("testcase"))
    skipped = [
        f"{case.get('classname', '')}::{case.get('name', '')}" for case in cases if case.find("skipped") is not None
    ]
    return len(cases), skipped


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: assert_no_skips.py report.xml", file=sys.stderr)
        return 2
    try:
        total, skipped = summarise(Path(args[0]))
    except (OSError, ET.ParseError) as exc:
        print(f"ERROR: cannot read JUnit report {args[0]}: {exc}", file=sys.stderr)
        return 1
    if total == 0:
        print("ERROR: the report contains no tests; the controls never ran.", file=sys.stderr)
        return 1
    if skipped:
        print(
            f"ERROR: {len(skipped)} of {total} control(s) skipped; a skipped control is not a passing one:",
            file=sys.stderr,
        )
        for test_id in skipped:
            print(f"  {test_id}", file=sys.stderr)
        return 1
    print(f"{total} control(s) executed, none skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
