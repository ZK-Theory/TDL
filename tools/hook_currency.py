#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-29-decision-report.md (Campaign S)
# Purpose: Say whether this checkout is running the hooks that were merged, or older ones, so a
# merged gate that is not live in a checkout is reported instead of assumed.
"""Hook currency: is the hook tree in force in this checkout the merged one?

Merging a gate makes it available, not live (obs 2026-10-02-merged-gates-not-live-in-the-main-
checkout). Git resolves ``core.hooksPath=.githooks`` inside the checkout and the harness loads
``.claude/settings.json`` and ``.claude/hooks/`` from it, so a checkout that is behind runs the old
hooks, silently, while ``install-git-hooks.py`` and the dispatch ``hook-gate`` report them wired. This
module compares ``HEAD`` with the integration branch and names any hook-touching commit the checkout
lacks.

Two callers: the SessionStart harness hook (``--session-start``, one line, always exit 0) and
``shared/manager_dispatch_check.py`` (the ``hook-currency`` check).

Reference. ``origin/main`` when it exists, otherwise ``@{upstream}``. The upstream alone is the wrong
default: a branch pushed with ``-u`` tracks its own remote branch, and measuring against that reads as
current however far behind main it is.

Limits, stated because they are the ways this check can say less than the truth:

* It reads the last-fetched remote ref and never runs ``git fetch``. SessionStart must not wait on the
  network, so a remote that moved since the last fetch is invisible until something fetches. It can
  under-report, never over-report.
* The check lives in the tree it checks. A checkout that has not yet pulled the commit that added it
  does not run it, so it protects a checkout against the next hook change, not against this one.
* The hook tree in force is the working tree, which may carry uncommitted edits; the report names them.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Everything git or the harness reads as a hook, relative to the work tree root.
HOOK_PATHS = (".githooks", ".claude/hooks", ".claude/settings.json")
DEFAULT_REF = "origin/main"
GIT_TIMEOUT_SECONDS = 8
MAX_FILES_SHOWN = 6

CURRENT = "CURRENT"
STALE = "STALE"
UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class Currency:
    """The outcome of one currency check.

    Attributes:
        status: ``CURRENT``, ``STALE`` (a hook-touching commit is missing) or ``UNVERIFIED``.
        message: The finding, starting ``OK``, ``WARNING`` or ``UNVERIFIED``.
        head: Abbreviated ``HEAD`` commit, empty when there is none.
        ref: The reference compared against, empty when none could be resolved.
        behind: Commits on ``ref`` that ``HEAD`` lacks.
        hook_commits: Abbreviated ids of those commits that touch a hook file.
        files: Sorted hook files touched by those commits.
        in_force: Abbreviated id of the last commit on ``HEAD`` that touched a hook file.
        dirty: Hook files with uncommitted edits, which are part of what actually runs.
    """

    status: str
    message: str
    head: str = ""
    ref: str = ""
    behind: int = 0
    hook_commits: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    in_force: str = ""
    dirty: tuple[str, ...] = ()

    @property
    def line(self) -> str:
        """The one-line form printed at session start."""
        return f"hook-currency: {self.message}"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a read-only git command; ``GIT_OPTIONAL_LOCKS=0`` keeps it from contending for the index lock."""
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )


def _names(output: str) -> list[str]:
    """Split ``-z`` output into non-empty names, with stray newlines removed."""
    return [name.strip("\n") for name in output.split("\0") if name.strip("\n")]


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _shown(files: tuple[str, ...]) -> str:
    """Join file names, capped so the line stays one readable line."""
    if len(files) <= MAX_FILES_SHOWN:
        return ", ".join(files)
    return f"{', '.join(files[:MAX_FILES_SHOWN])} (+{len(files) - MAX_FILES_SHOWN} more)"


def _unverified(
    reason: str, head: str = "", in_force: str = "", date: str = "", dirty: tuple[str, ...] = ()
) -> Currency:
    """Build the finding for a check that could not reach a verdict, still naming what is in force."""
    clause = f" Hook tree in force is {in_force} ({date})." if in_force else ""
    return Currency(UNVERIFIED, f"UNVERIFIED - {reason}.{clause}", head=head, in_force=in_force, dirty=dirty)


def _resolve_reference(root: Path, ref: str | None) -> tuple[str | None, str]:
    """Return ``(reference, problem)``: the first reference that resolves, else the reason none did."""
    if ref:
        found = _git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}")
        return (ref, "") if found.returncode == 0 else (None, f"reference {ref} does not exist here")
    if _git(root, "rev-parse", "--verify", "-q", f"refs/remotes/{DEFAULT_REF}^{{commit}}").returncode == 0:
        return DEFAULT_REF, ""
    upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream.returncode == 0 and upstream.stdout.strip():
        return upstream.stdout.strip(), ""
    return None, f"no {DEFAULT_REF} or upstream ref to compare against (no remote, or never fetched)"


def _uncommitted(root: Path) -> tuple[str, ...]:
    """Hook files edited, staged or added but not committed; none of them is in ``HEAD``'s hook tree."""
    tracked = _git(root, "diff", "--name-only", "--no-renames", "-z", "HEAD", "--", *HOOK_PATHS)
    untracked = _git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", *HOOK_PATHS)
    return tuple(sorted({*_names(tracked.stdout), *_names(untracked.stdout)}))


def _in_force_clause(in_force: str, date: str, dirty: tuple[str, ...]) -> str:
    base = f"hook tree in force is {in_force} ({date})" if in_force else "no commit here has touched a hook file"
    if dirty:
        base += f", plus uncommitted edits to {_plural(len(dirty), 'hook file')}: {_shown(dirty)}"
    return base


def check(repo: Path | str = ".", ref: str | None = None) -> Currency:
    """Compare the hook tree in ``repo`` with the integration branch's last-fetched state.

    Args:
        repo: Any directory inside the work tree, including a linked worktree or a subdirectory.
        ref: Reference to compare against. Default: ``origin/main``, then ``@{upstream}``.

    Returns:
        The finding. Never raises for an ordinary repository shape (no remote, no commits, detached
        HEAD, not a repository); a failure to run git at all is reported as ``UNVERIFIED``.
    """
    start = Path(repo)
    if not start.is_dir():
        return _unverified(f"{start} is not a directory")
    try:
        return _check(start, ref)
    except (OSError, subprocess.SubprocessError) as exc:
        return _unverified(f"git could not be run ({type(exc).__name__})")


def _check(start: Path, ref: str | None) -> Currency:
    top = _git(start, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or not top.stdout.strip():
        return _unverified("not inside a git work tree")
    root = Path(top.stdout.strip())

    head_log = _git(root, "log", "-1", "--format=%h", "HEAD")
    if head_log.returncode != 0 or not head_log.stdout.strip():
        return _unverified("the repository has no commits yet")
    head = head_log.stdout.strip()
    branch = _git(root, "symbolic-ref", "-q", "--short", "HEAD")
    where = f"HEAD {head} ({branch.stdout.strip()})" if branch.returncode == 0 else f"detached HEAD {head}"

    force_log = _git(root, "log", "-1", "--format=%h %cs", "HEAD", "--", *HOOK_PATHS).stdout.split()
    in_force, date = (force_log + ["", ""])[:2]
    dirty = _uncommitted(root)

    reference, problem = _resolve_reference(root, ref)
    if reference is None:
        return _unverified(problem, head=head, in_force=in_force, date=date, dirty=dirty)

    behind_out = _git(root, "rev-list", "--count", f"HEAD..{reference}")
    if behind_out.returncode != 0:
        return _unverified(
            f"could not compare HEAD with {reference}", head=head, in_force=in_force, date=date, dirty=dirty
        )
    behind = int(behind_out.stdout.strip() or 0)
    commits = _git(root, "log", "--format=%h", f"HEAD..{reference}", "--", *HOOK_PATHS).stdout.split()
    touched = _git(
        root, "log", "-m", "--no-renames", "--name-only", "-z", "--format=", f"HEAD..{reference}", "--", *HOOK_PATHS
    )
    files = tuple(sorted(set(_names(touched.stdout))))
    held = _in_force_clause(in_force, date, dirty)
    common = {"head": head, "ref": reference, "behind": behind, "in_force": in_force, "dirty": dirty}

    if commits:
        if len(commits) == behind == 1:
            ours = "it changes"
        elif len(commits) == 1:
            ours = "1 of them changes"
        else:
            ours = f"{len(commits)} of them change"
        message = (
            f"WARNING - {where} is {_plural(behind, 'commit')} behind {reference} as of the last fetch, {ours} hook files: "
            f"{_shown(files)}. {held[:1].upper()}{held[1:]}, so this checkout runs the pre-merge hooks and loads "
            f"the pre-merge harness hooks. Update it (git pull --ff-only on main, otherwise rebase onto "
            f"{reference}), restart the session, then run: uv run python .claude/hooks/install-git-hooks.py"
        )
        return Currency(STALE, message, hook_commits=tuple(commits), files=files, **common)

    gap = (
        f"{_plural(behind, 'commit')} behind {reference} as of the last fetch; none touch hook files"
        if behind
        else f"level with {reference} as of the last fetch"
    )
    return Currency(CURRENT, f"OK - {held}; {where} is {gap}.", **common)


def _emit(text: str) -> None:
    """Print ``text`` as one ASCII-safe line, so a console that cannot encode a path name never raises."""
    print(text.encode("ascii", "replace").decode("ascii"))


def main(argv: list[str] | None = None) -> int:
    """Print the finding; exit 1 when stale, except under ``--session-start``, which never fails."""
    parser = argparse.ArgumentParser(description="Report whether this checkout runs the merged hooks.")
    parser.add_argument("--repo", default=None, help="Directory to check (default: $CLAUDE_PROJECT_DIR, else cwd).")
    parser.add_argument(
        "--ref", default=None, help=f"Reference to compare with (default: {DEFAULT_REF}, then upstream)."
    )
    parser.add_argument(
        "--session-start",
        action="store_true",
        help="SessionStart mode: always one line, always exit 0, even when the check itself fails.",
    )
    args = parser.parse_args(argv)
    repo = args.repo or os.environ.get("CLAUDE_PROJECT_DIR") or "."

    if args.session_start:
        try:
            _emit(check(repo, args.ref).line)
        except Exception as exc:  # a session must start; the failure is reported, not raised
            _emit(f"hook-currency: UNVERIFIED - the check itself failed ({type(exc).__name__}: {exc}).")
        return 0

    result = check(repo, args.ref)
    _emit(result.line)
    return 1 if result.status == STALE else 0


if __name__ == "__main__":
    sys.exit(main())
