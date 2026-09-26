#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign F)
# Purpose: Fail a brief or handoff that cites a repository path absent from the base ref, naming
# the branch that does hold it, before the brief is dispatched.
"""Check that every repository path a brief cites resolves on the base ref.

Obs 2026-09-14-handoff-cited-at-a-path-only-an-unmerged-pr-contains: the Phase 4 dispatch cited a
handoff path that existed only on an open docs PR branch, and locating it cost a repo-wide
``git log --all`` search. A path a brief tells a fresh session to read must exist where that
session starts, or the brief must name the branch that holds it.

What counts as a cited path: a backtick span with no whitespace and no placeholder or glob
characters (``<>*?{}[]$``) that either contains ``/`` or is a root-level file name with a known
file extension (``AGENTS.md``, ``pyproject.toml``, ``.ruff.toml``) or a git dotfile. A ``::``
suffix (a pytest node id) and a line anchor (``:476``, ``:476-484``, ``#L12``, ``#L12-L20``) are
dropped before resolving. A bare name that resolves nowhere but names a kind of file the ref holds
elsewhere (``SKILL.md``, ``_project.md``) is a generic mention and is not reported; one that no
file on the ref is called (``MISSING.md``) is.

Where a path may resolve: at the repository root on the ref, or relative to the brief's own
directory. Nothing else, so a citation that works for neither reading is reported.

When it is still fine: the path is git-ignored (it never lives on a ref), or the same line names
a branch in backticks that holds it (``read `docs/h.md` from branch `docs/handoff```), which is the
remedy this tool prints.

Usage: python tools/check_brief_paths.py BRIEF.md [--ref origin/main] [--repo-root .]
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path

_SPAN = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER = re.compile(r"[<>*?{}\[\]$]")
# Path characters only: a span such as `p=(r+1)/(B+1)` is an expression, not a citation.
_PATH_CHARS = re.compile(r"[\w.@/ -]+")
_EXTENSION = re.compile(
    r"\.(?:md|py|toml|ya?ml|json|txt|cfg|ini|lock|sh|ps1|csv|tex|bib|ipynb|R|r|pdf|html|lean|js|ts)$"
)
_ANCHOR = re.compile(r"(?::\d+(?:-\d+)?|#L\d+(?:-L?\d+)?)$")
_ROOT_FILE = re.compile(
    r"(?:\.?[\w-][\w.-]*\.(?:md|py|toml|ya?ml|json|txt|cfg|ini|lock|sh|ps1|csv|tex|bib|ipynb|R|r)"
    r"|\.gitattributes|\.gitignore|\.gitmodules|\.env)"
)


def _normalise(span: str) -> str | None:
    """Return the repository path a backtick span cites, or None when it is not a path citation."""
    candidate = _ANCHOR.sub("", span.split("::", 1)[0].strip())
    if candidate.startswith("./"):
        candidate = candidate[2:]
    if (
        not candidate
        or re.search(r"[\t\n\r]", candidate)
        or (" " in candidate and "/" not in candidate)
        or not _PATH_CHARS.fullmatch(candidate)
        or _PLACEHOLDER.search(candidate)
        or "://" in candidate
        or candidate.startswith(("-", "/", "~"))
        or re.match(r"[A-Za-z]:", candidate)
    ):
        return None
    if "/" not in candidate and not _ROOT_FILE.fullmatch(candidate):
        return None
    return candidate


def citations(text: str) -> list[tuple[str, list[list[str]]]]:
    """Return (path, per-occurrence lists of the other backtick spans on that line) for each distinct path.

    Occurrences are kept apart: a branch named beside one mention does not qualify another mention
    of the same path on a different line.
    """
    found: dict[str, list[list[str]]] = {}
    for line in text.splitlines():
        spans = _SPAN.findall(line)
        for span in spans:
            path = _normalise(span)
            if path is None:
                continue
            found.setdefault(path, []).append([s.strip() for s in spans if s != span])
    return list(found.items())


def cited_paths(text: str) -> list[str]:
    """Return the distinct repository paths cited in backticks, in order of first mention."""
    return [path for path, _ in citations(text)]


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)


def _is_ref_or_namespace(repo_root: Path, candidate: str) -> bool:
    """True for `origin/main`-style refs and `codex/`-style branch namespaces, which are not file citations."""
    name = candidate.rstrip("/")
    if _git(repo_root, "rev-parse", "--verify", "--quiet", name).returncode == 0:
        return True
    listed = _git(repo_root, "for-each-ref", "--count=1", f"refs/heads/{name}/", f"refs/remotes/origin/{name}/")
    return bool(listed.stdout.strip())


def _brief_directory(repo_root: Path, brief: Path | None) -> str | None:
    """Return the brief's directory, repo-relative, or None when the brief is outside the repository."""
    if brief is None:
        return None
    try:
        relative = brief.resolve().parent.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    return "" if relative == "." else relative


def _exists(repo_root: Path, ref: str, path: str) -> bool:
    return (
        bool(path) and not path.startswith("..") and _git(repo_root, "cat-file", "-e", f"{ref}:{path}").returncode == 0
    )


_LISTINGS: dict[tuple[str, str], list[str]] = {}


def _tree(repo_root: Path, ref: str) -> list[str]:
    key = (str(repo_root), ref)
    if key not in _LISTINGS:
        _LISTINGS[key] = _git(repo_root, "ls-tree", "-r", "--name-only", ref).stdout.splitlines()
    return _LISTINGS[key]


def _basename_on_ref(repo_root: Path, ref: str, name: str) -> bool:
    """Whether any file on ``ref`` is called ``name``: a bare `SKILL.md` is a kind of file, not a root citation."""
    return any(posixpath.basename(line) == name for line in _tree(repo_root, ref))


def _suffix_matches(repo_root: Path, ref: str, target: str) -> list[str]:
    """Return files on ``ref`` whose path ends with ``/target``: what a partial citation probably meant."""
    return [line for line in _tree(repo_root, ref) if line.endswith("/" + target)]


def _top_level(repo_root: Path, ref: str) -> set[str]:
    return {line.split("/", 1)[0] for line in _tree(repo_root, ref)}


def _path_shaped(repo_root: Path, ref: str, target: str) -> bool:
    """Whether a slash-bearing span looks like a path rather than prose such as `try/except`.

    It must end in a known file extension, start with `..` or a top-level entry of ``ref``, or end in `/`.
    """
    first = target.split("/", 1)[0]
    return (
        bool(_EXTENSION.search(target)) or first in _top_level(repo_root, ref) or first == ".." or target.endswith("/")
    )


def unresolved(
    paths: list[str] | list[tuple[str, list[list[str]]]], repo_root: Path, ref: str, brief: Path | None = None
) -> list[str]:
    """Return one problem line per path absent from ``ref``, naming the branches that do hold it.

    ``paths`` is either plain paths or :func:`citations` pairs; with pairs, a path is branch-qualified,
    and so acceptable, only when EVERY mention of it names on its own line a branch that holds it.
    """
    if _git(repo_root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        return [f"ref {ref!r} does not resolve to a commit; no citation can be checked against it"]
    problems: list[str] = []
    directory = _brief_directory(repo_root, brief)
    for item in paths:
        path, contexts = (item, [[]]) if isinstance(item, str) else item
        target = path.rstrip("/")
        readings = [target]
        if directory is not None:
            readings.append(posixpath.normpath(posixpath.join(directory, target)))
        if any(_exists(repo_root, ref, reading) for reading in readings):
            continue
        if _is_ref_or_namespace(repo_root, path):
            continue
        if " " in target and target.split("/", 1)[0] not in _top_level(repo_root, ref):
            continue  # a command line such as `uv run python tools/x.py`, not a spaced path
        if "/" in target and not _path_shaped(repo_root, ref, target):
            continue
        if "/" not in target and _basename_on_ref(repo_root, ref, target):
            continue
        if "/" in target and (suggestions := _suffix_matches(repo_root, ref, target)):
            problems.append(
                f"{path}: not at the repository root or beside the brief on {ref}; cite the full path "
                f"({', '.join(suggestions[:3])})"
            )
            continue

        def qualified(context: list[str], readings: list[str] = readings) -> bool:
            named = [c for c in context if _is_ref_or_namespace(repo_root, c)]
            return any(_exists(repo_root, c.rstrip("/"), reading) for c in named for reading in readings)

        if all(qualified(context) for context in contexts):
            continue
        last = _git(repo_root, "log", "--all", "-1", "--format=%H", "--", target).stdout.strip()
        if not last:
            if _git(repo_root, "check-ignore", "-q", "--no-index", target).returncode == 0:
                # Never tracked and ignored (data, .env): no ref can hold it, so check the checkout
                # the Worker reads from. Ignored patterns such as `docs/*` also cover force-added
                # tracked files, which is why this runs only once no branch has ever held the path.
                if not (repo_root / target).exists():
                    problems.append(f"{path}: git-ignored, never tracked, and not present in {repo_root}")
                continue
            problems.append(f"{path}: absent from {ref} and from every branch")
            continue
        branches = [
            name
            for name in _git(repo_root, "branch", "-a", "--contains", last, "--format=%(refname:short)").stdout.split()
            if name != ref and _exists(repo_root, name, target)  # a later deletion leaves nothing to read
        ]
        where = ", ".join(branches) if branches else f"no branch tip (last touched in commit {last[:12]})"
        problems.append(f"{path}: absent from {ref}; present on {where}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a brief's cited repository paths resolve on the base ref.")
    parser.add_argument("brief", type=Path)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    cited = citations(args.brief.read_text(encoding="utf-8"))
    problems = unresolved(cited, args.repo_root, args.ref, brief=args.brief)
    if problems:
        print(f"{len(problems)} cited path(s) do not resolve on {args.ref}:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        print(
            "Merge the source first, or name the branch holding it in backticks on the same line "
            "(read `path` from branch `name`).",
            file=sys.stderr,
        )
        return 1
    print(f"{len(cited)} cited path(s) resolve on {args.ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
