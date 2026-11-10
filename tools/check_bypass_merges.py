#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-11-10-decision-report.md (Group A, item 3)
# Purpose: Report every bypassed update to main whose required checks were not green on the merged head, or whose
# pull request states no reason for the bypass.
"""Audit the admin bypasses of ruleset 20822054 after the fact.

Obs 2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red: #420 merged by admin bypass about ninety seconds
after its last commit. Two required checks were still running on the merged head, its suite had gone red on the
previous head, and ``main`` failed two tests. A required check binds only the merges that do not bypass it, and the
bypass stays open for gate-file edits (CONVENTIONS, "Ordinary merges go through the merge queue; a bypass states its
reason"), so this audit checks each bypass afterwards.

For every rule-suite evaluation on ``refs/heads/main`` with ``result: bypass`` in the window, it finds the pull request
that merged the commit and reports:

* each required check (the ruleset's required contexts plus ``suite-verdict``) that had not completed with
  ``success`` on the pull request's head before the merge;
* a pull request whose description and comments carry no line starting ``Bypass reason:``.

Reading rule suites needs the repository owner's token, which a workflow's ``GITHUB_TOKEN`` cannot be granted, so
the weekly system review runs this in its step 1. ``audit`` is pure, and its controls run in admission-controls.

Usage: python tools/check_bypass_merges.py [--repo OWNER/NAME] [--ruleset 20822054] [--days 7]
Exit 0 when every bypass is clean, 1 when any is reported, 2 when GitHub cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

EXTRA_REQUIRED = ("suite-verdict",)
_REASON = re.compile(r"(?im)^\s*\**bypass reason:\**\s*\S")


@dataclass(frozen=True)
class Bypass:
    """One bypassed update to main and what the audit needs to judge it."""

    after_sha: str
    pushed_at: str
    pr_number: int | None
    merged_at: str | None
    head_sha: str | None
    texts: tuple[str, ...] = ()
    checks: Mapping[str, list[tuple[str | None, str | None]]] = field(default_factory=dict)


def _before(completed_at: str | None, merged_at: str | None) -> bool:
    if completed_at is None or merged_at is None:
        return False
    return completed_at <= merged_at


def audit(bypasses: Iterable[Bypass], required: Iterable[str]) -> list[str]:
    """Return one problem line per defect; empty means every bypass had green checks and a stated reason.

    ``checks`` maps a check name to its runs on the head as ``(conclusion, completed_at)``. A check passes when some
    run completed with ``success`` at or before the merge.
    """
    names = sorted(set(required) | set(EXTRA_REQUIRED))
    problems: list[str] = []
    for bypass in bypasses:
        label = f"{bypass.after_sha[:8]} ({bypass.pushed_at})"
        if bypass.pr_number is None:
            problems.append(f"{label}: bypassed update to main with no pull request")
            continue
        label = f"#{bypass.pr_number} {label}"
        for name in names:
            runs = bypass.checks.get(name, [])
            if not any(conclusion == "success" and _before(done, bypass.merged_at) for conclusion, done in runs):
                states = ", ".join(f"{c or 'in progress'} at {done or '-'}" for c, done in runs) or "never ran"
                problems.append(
                    f"{label}: required check {name} was not green on head {(bypass.head_sha or '')[:8]} "
                    f"when it merged at {bypass.merged_at} ({states})"
                )
        if not any(_REASON.search(text or "") for text in bypass.texts):
            problems.append(f"{label}: bypass with no 'Bypass reason:' line in the pull request")
    return problems


def _gh(*args: str) -> Any:
    completed = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"gh {' '.join(args)} failed")
    return json.loads(completed.stdout or "null")


def _paged(path: str) -> list[Any]:
    data = _gh("api", "--paginate", "--slurp", path)
    return [item for page in data for item in (page if isinstance(page, list) else page.get("check_runs", []))]


def collect(repo: str, ruleset: int, days: int, now: datetime) -> tuple[list[Bypass], list[str]]:
    """Read the bypasses in the window and the required contexts from GitHub."""
    rules = _gh("api", f"repos/{repo}/rulesets/{ruleset}")
    required = [
        check["context"]
        for rule in rules.get("rules", [])
        if rule.get("type") == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
    ]
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    suites = _paged(f"repos/{repo}/rulesets/rule-suites?ref=refs/heads/main&time_period=month")
    bypasses: list[Bypass] = []
    for suite in suites:
        if suite.get("result") != "bypass" or suite.get("pushed_at", "") < since:
            continue
        sha = suite["after_sha"]
        pulls = [p for p in _gh("api", f"repos/{repo}/commits/{sha}/pulls") if p.get("merged_at")]
        if not pulls:
            bypasses.append(Bypass(sha, suite["pushed_at"], None, None, None))
            continue
        pr = pulls[0]
        head = pr["head"]["sha"]
        comments = _gh("api", f"repos/{repo}/issues/{pr['number']}/comments")
        checks: dict[str, list[tuple[str | None, str | None]]] = {}
        for run in _paged(f"repos/{repo}/commits/{head}/check-runs?per_page=100"):
            checks.setdefault(run["name"], []).append((run.get("conclusion"), run.get("completed_at")))
        texts = (pr.get("body") or "", *(c.get("body") or "" for c in comments))
        bypasses.append(Bypass(sha, suite["pushed_at"], pr["number"], pr["merged_at"], head, texts, checks))
    return bypasses, required


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="ZK-Theory/TDL")
    parser.add_argument("--ruleset", type=int, default=20822054)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)
    try:
        bypasses, required = collect(args.repo, args.ruleset, args.days, datetime.now(UTC))
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"bypass audit: cannot read GitHub: {error}", file=sys.stderr)
        return 2
    problems = audit(bypasses, required)
    for problem in problems:
        print(f"ERROR: {problem}")
    print(f"bypass audit: {len(bypasses)} bypassed update(s) to main in {args.days} day(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
