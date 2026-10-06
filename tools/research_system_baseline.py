#!/usr/bin/env python3
# Research context: 2026-10-02 research_system suite triage (obs 2026-10-03-shared-seam-change-merged-without-its-dependents)
# Purpose: fail the research_system lanes on any failure outside a shrink-only known-failures list.
"""Hold the research_system suite to a known-failures baseline that can only shrink.

Reads one or more JUnit XML reports and compares the failing node ids with the baseline
file (one pytest node id per line, ``#`` comments allowed). Exit status:

* 1 if any test failed or errored that the baseline does not list (a new failure);
* 1 if any baseline entry ran in these reports and passed (it must be removed);
* 1 if the reports contain no executed tests (an empty or vacuous run is not green);
* 0 otherwise.

Entries for tests absent from these reports are ignored, so each CI shard checks only
its own files. Skipped tests count as executed but neither fail nor pass an entry.

Usage:
    research_system_baseline.py --baseline tools/research_system_known_failures.txt REPORT.xml [...]
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def node_id(case: ET.Element) -> str:
    """Rebuild ``path::name`` from a pytest JUnit testcase (classname is dotted path + class)."""
    classname = case.get("classname", "")
    name = case.get("name", "")
    parts = classname.split(".")
    for cut in range(len(parts), 0, -1):
        candidate = Path(*parts[:cut]).with_suffix(".py")
        if candidate.name.startswith("test_"):
            rest = parts[cut:]
            return "::".join([candidate.as_posix(), *rest, name])
    return f"{classname}::{name}"


def outcomes(reports: list[Path]) -> dict[str, str]:
    """Return ``node id -> passed|failed|skipped`` over every report."""
    result: dict[str, str] = {}
    for report in reports:
        for case in ET.parse(report).iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                state = "failed"
            elif case.find("skipped") is not None:
                state = "skipped"
            else:
                state = "passed"
            result[node_id(case)] = state
    return result


def load_baseline(path: Path) -> set[str]:
    """Return baseline node ids, ignoring blank lines and ``#`` comments."""
    entries = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped:
            entries.add(stripped)
    return entries


def check(results: dict[str, str], baseline: set[str]) -> list[str]:
    """Return human-readable problems; empty means the run honours the baseline."""
    if not results:
        return ["no executed tests in the reports"]
    problems = [
        f"new failure (not in baseline): {node}"
        for node, state in sorted(results.items())
        if state == "failed" and node not in baseline
    ]
    problems += [
        f"baseline entry now passes; remove it: {node}" for node in sorted(baseline) if results.get(node) == "passed"
    ]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("reports", type=Path, nargs="+")
    args = parser.parse_args(argv)
    results = outcomes(args.reports)
    problems = check(results, load_baseline(args.baseline))
    failed = sum(1 for state in results.values() if state == "failed")
    print(f"{len(results)} tests, {failed} failed, baseline {len(load_baseline(args.baseline))} entries")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
