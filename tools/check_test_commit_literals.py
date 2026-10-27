#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-10-27-decision-report.md (Group D, item 1)
# Purpose: Fail when a test names a commit that a squash merge will strand, so a negative control cannot
# pass on its PR branch and then error in every clone of main.
"""Check that every commit a test names survives a squash merge.

Obs 2026-10-24-squash-merge-strands-sha-pinned-controls: a W9 control built its "wrong annex" catalogue by
resolving a commit on the PR branch. TDL squash-merges, so after the merge that commit was on no ``main`` ref and
the test errored in any clone without the branch, while all 235 tests passed on the branch.

Every 40-hex token in a ``.py`` file under the root that is a commit **in this checkout** must be one of:

* an ancestor of the main ref (default ``origin/main``);
* contained in a tag the remote has (``tools/commit_reachability.py``; the ``pin/*`` tags are the usual case);
* marked as data, by the comment ``commit-literal: data`` on its own line or the line above, for a literal the
  test compares as a string and never hands to git.

Tokens that are not commits here (blobs, trees, synthetic ids, objects absent from this clone) are not judged: a
test full of made-up hashes is normal. The check therefore belongs on a pull request's own checkout, where the
branch's commits are present.

Usage: python tools/check_test_commit_literals.py [--repo REPO] [--root tests] [--main-ref origin/main]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit_reachability import Publication, object_types  # noqa: E402

_ID = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])")
MARKER = "commit-literal: data"


def literals(root: Path) -> dict[str, list[tuple[Path, int, bool]]]:
    """Map every 40-hex token under ``root`` to (file, line number, marked as data) for each occurrence."""
    found: dict[str, list[tuple[Path, int, bool]]] = {}
    for path in sorted(root.rglob("*.py")):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            marked = MARKER in line or (index > 0 and MARKER in lines[index - 1])
            for oid in dict.fromkeys(_ID.findall(line)):
                found.setdefault(oid, []).append((path, index + 1, marked))
    return found


def _is_ancestor(repo: Path, sha: str, main_ref: str) -> bool:
    done = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, main_ref], check=False)
    return done.returncode == 0


def check(repo: Path, root: Path, main_ref: str = "origin/main") -> tuple[list[str], str]:
    """Return (problems, summary) for every commit literal under ``root``."""
    publication = Publication(repo, accept_pull_refs=False)
    found = literals(root)
    types = object_types(repo, list(found))
    problems: list[str] = []
    counts = {"on main": 0, "tagged": 0, "data": 0, "not a commit here": 0}
    for oid, sites in found.items():
        if types[oid] != "commit":
            counts["not a commit here"] += 1
            continue
        if _is_ancestor(repo, oid, main_ref):
            counts["on main"] += 1
            continue
        if publication.published_by_tag(oid):
            counts["tagged"] += 1
            continue
        unmarked = [(p, n) for p, n, marked in sites if not marked]
        if not unmarked:
            counts["data"] += 1
            continue
        where = ", ".join(f"{str(p.relative_to(repo)).replace(chr(92), '/')}:{n}" for p, n in unmarked[:3])
        problems.append(
            f"{oid[:12]} ({where}) is a commit on neither {main_ref} nor a remote tag, so a squash merge strands "
            f"it; use a commit on main, publish a tag, or mark a string-only literal with '# {MARKER}'"
        )
    summary = "commit literals: " + ", ".join(f"{n} {k}" for k, n in counts.items()) + f", {len(problems)} problem(s)"
    if problems and publication.tag_note:
        summary += f"; {publication.tag_note}"
    return problems, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--root", type=Path, default=None, help="Defaults to REPO/tests.")
    parser.add_argument("--main-ref", default="origin/main")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    problems, summary = check(repo, (args.root or repo / "tests").resolve(), args.main_ref)
    print(summary)
    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
