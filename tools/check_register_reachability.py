#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-10-27-decision-report.md (Group B, item 2)
# Purpose: List decision-register and owner-acceptance text that exists on a branch but not on main, so an owner
# decision recorded on an unmerged branch is found in days, not in 82.
"""Report register content that some branch holds and ``main`` does not.

Obs 2026-10-22-w11-owner-acceptance-stranded-on-unmerged-branch: Stephen's 2026-08-01 W11 acceptance was recorded
in a commit that reached only a Codex branch. Main's register said limb 1 was open for 82 days, and a later spec
was drafted against it. The fix for that finding then sat five days on an unpushed local branch.

TDL squash-merges, so "the commit is not an ancestor of main" would flag every merged PR. This check reads content
instead. For each local or remote-tracking branch whose tip is not on the main ref, it diffs the merge base to the
tip over the governed paths and asks whether main holds what the branch added:

* the register (``03-decisions-and-open-questions.md``): the share of the branch's added lines, ignoring lines of
  25 characters or fewer, that appear verbatim in main's copy;
* an owner-acceptance record (``reviews/*owner-acceptance*``): whether the file exists on main.

A branch below 90% is reported with its tip and the counts. A branch that is the head of an open PR is reported as
pending rather than stranded, and does not fail the run. ``KNOWN`` holds branches the owner has decided not to land,
each with its reason.

Usage: python tools/check_register_reachability.py [--repo REPO] [--main-ref origin/main] [--no-network]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = "docs/plans/agentic-research-system/"
REGISTER = ROOT + "03-decisions-and-open-questions.md"
REVIEWS = ROOT + "reviews/"
THRESHOLD = 0.9
MIN_LINE = 25

# Branches whose register text is deliberately not landing. Each needs the owner's reason.
KNOWN: dict[str, str] = {}


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return done.stdout if done.returncode == 0 else ""


def _added(diff: str) -> dict[str, list[str]]:
    """Map each governed file in a ``--unified=0`` diff to its added lines longer than ``MIN_LINE``."""
    added: dict[str, list[str]] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            current = path if path and (path == REGISTER or "owner-acceptance" in path) else None
        elif current and line.startswith("+") and len(line[1:].strip()) > MIN_LINE:
            added.setdefault(current, []).append(line[1:].strip())
    return added


def _open_pr_heads(repo: Path) -> dict[str, tuple[int, str]] | None:
    """Map each open PR's head branch to (number, head commit), or None when ``gh`` cannot list them."""
    done = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--limit", "200", "--json", "number,headRefName,headRefOid"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        return None
    return {pr["headRefName"]: (pr["number"], pr["headRefOid"]) for pr in json.loads(done.stdout or "[]")}


def _pending_pr(repo: Path, name: str, tip: str, open_prs: dict[str, tuple[int, str]]) -> int | None:
    """The open PR that carries this branch: same head branch name, or a head that contains the tip."""
    if name in open_prs:
        return open_prs[name][0]
    for number, head in open_prs.values():
        if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", tip, head]).returncode == 0:
            return number
    return None


def check(
    repo: Path, main_ref: str = "origin/main", open_prs: dict[str, tuple[int, str]] | None = None
) -> tuple[list[str], str]:
    """Return (problems, summary); a pending open-PR branch is listed in the summary, not in the problems."""
    main_lines = {line.strip() for line in _git(repo, "show", f"{main_ref}:{REGISTER}").splitlines()}
    refs = _git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads", "refs/remotes")
    problems: list[str] = []
    pending: list[str] = []
    checked = 0
    for entry in refs.splitlines():
        ref, _, tip = entry.partition(" ")
        # A merge-queue ref is GitHub's transient copy of a queued PR, not a branch anyone owns.
        if not tip or ref.endswith("/HEAD") or ref in KNOWN or "gh-readonly-queue/" in ref:
            continue
        if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", tip, main_ref]).returncode == 0:
            continue
        base = _git(repo, "merge-base", tip, main_ref).strip()
        if not base:
            continue
        checked += 1
        added = _added(_git(repo, "diff", "--unified=0", f"{base}..{tip}", "--", REGISTER, REVIEWS))
        for path, lines in added.items():
            if path == REGISTER:
                present = sum(line in main_lines for line in lines)
            else:
                on_main = _git(repo, "cat-file", "-t", f"{main_ref}:{path}").strip() == "blob"
                present = len(lines) if on_main else 0
            if present >= THRESHOLD * len(lines):
                continue
            name = ref.removeprefix("origin/")
            text = (
                f"{ref} (tip {tip[:8]}): {path.removeprefix(ROOT)} has {present}/{len(lines)} added lines on {main_ref}"
            )
            number = _pending_pr(repo, name, tip, open_prs) if open_prs is not None else None
            if number is not None:
                pending.append(f"{text} (open PR #{number})")
            else:
                problems.append(f"{text}; land it, or record in KNOWN why it is not landing")
    summary = f"register reachability: {checked} unmerged branch(es) checked, {len(problems)} stranded"
    summary += f", {len(pending)} pending in open PRs"
    if open_prs is None:
        summary += "; open PRs not looked up, so a pending branch reads as stranded"
    return problems, summary + "".join(f"\n  pending: {p}" for p in pending)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--no-network", action="store_true", help="Do not look up open PRs with gh.")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    problems, summary = check(repo, args.main_ref, None if args.no_network else _open_pr_heads(repo))
    print(summary)
    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
