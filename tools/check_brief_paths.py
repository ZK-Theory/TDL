#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign F)
# Purpose: Fail a brief or handoff that cites a repository path absent from the base ref, naming
# the branch that does hold it, before the brief is dispatched.
"""Check that every repository path a brief cites resolves on the base ref.

Obs 2026-09-14-handoff-cited-at-a-path-only-an-unmerged-pr-contains: the Phase 4 dispatch cited a
handoff path that existed only on an open docs PR branch, and locating it cost a repo-wide
``git log --all`` search. A path a brief tells a fresh session to read must exist where that
session starts, or the brief must name the branch that holds it.

A backtick span counts as a path when it contains ``/``, has no whitespace, and carries no
placeholder or glob characters (``<>*?{}[]$``); a ``::`` suffix (a pytest node id) is dropped.

Usage: python tools/check_brief_paths.py BRIEF.md [--ref origin/main] [--repo-root .]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_SPAN = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER = re.compile(r"[<>*?{}\[\]$]")


def cited_paths(text: str) -> list[str]:
    """Return the distinct repository paths cited in backticks, in order of first mention."""
    found: list[str] = []
    for span in _SPAN.findall(text):
        candidate = span.split("::", 1)[0].strip()
        if candidate.startswith("./"):
            candidate = candidate[2:]
        if (
            "/" not in candidate
            or re.search(r"\s", candidate)
            or _PLACEHOLDER.search(candidate)
            or "://" in candidate
            or candidate.startswith(("-", "/", "~"))
            or re.match(r"[A-Za-z]:", candidate)
        ):
            continue
        if candidate not in found:
            found.append(candidate)
    return found


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)


def _is_ref_or_namespace(repo_root: Path, candidate: str) -> bool:
    """True for `origin/main`-style refs and `codex/`-style branch namespaces, which are not file citations."""
    name = candidate.rstrip("/")
    if _git(repo_root, "rev-parse", "--verify", "--quiet", name).returncode == 0:
        return True
    listed = _git(repo_root, "for-each-ref", "--count=1", f"refs/heads/{name}/", f"refs/remotes/origin/{name}/")
    return bool(listed.stdout.strip())


def _brief_bases(repo_root: Path, brief: Path | None) -> list[str]:
    """Return the brief's directory and its ancestors, repo-relative: a brief may cite paths relative to itself."""
    if brief is None:
        return []
    try:
        relative = brief.resolve().parent.relative_to(repo_root.resolve())
    except ValueError:
        return []
    return [part.as_posix() for part in (relative, *relative.parents) if part.as_posix() != "."]


def unresolved(paths: list[str], repo_root: Path, ref: str, brief: Path | None = None) -> list[str]:
    """Return one problem line per path absent from ``ref``, naming the branches that do hold it."""
    problems: list[str] = []
    bases = _brief_bases(repo_root, brief)
    for path in paths:
        target = path.rstrip("/")
        if any(
            _git(repo_root, "cat-file", "-e", f"{ref}:{prefix}{target}").returncode == 0
            for prefix in ["", *(f"{base}/" for base in bases)]
        ):
            continue
        if _is_ref_or_namespace(repo_root, path):
            continue
        last = _git(repo_root, "log", "--all", "-1", "--format=%H", "--", target).stdout.strip()
        if not last:
            problems.append(f"{path}: absent from {ref} and from every branch")
            continue
        branches = [
            name
            for name in _git(repo_root, "branch", "-a", "--contains", last, "--format=%(refname:short)").stdout.split()
            if name != ref
        ]
        where = ", ".join(branches) if branches else f"commit {last[:12]} only"
        problems.append(f"{path}: absent from {ref}; present on {where}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a brief's cited repository paths resolve on the base ref.")
    parser.add_argument("brief", type=Path)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    paths = cited_paths(args.brief.read_text(encoding="utf-8"))
    problems = unresolved(paths, args.repo_root, args.ref, brief=args.brief)
    if problems:
        print(f"{len(problems)} cited path(s) do not resolve on {args.ref}:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        print("Merge the source first, or cite the path with its branch/PR.", file=sys.stderr)
        return 1
    print(f"{len(paths)} cited path(s) resolve on {args.ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
