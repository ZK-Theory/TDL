# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group A)
# Purpose: One definition of "this commit has been delivered", shared by the observation-log lint and the
# pinned-commit check, so a tag pushed to the remote counts and a local-only branch or tag never does.
"""Decide whether a commit is published: reachable from a remote-tracking branch or from a tag the remote has.

Obs 2026-10-15-accepted-contracts-pin-commits-on-local-only-branches: accepted contracts on ``main`` pinned five
review commits that existed only on local branches. A clean CI clone could not fetch them, and a branch prune plus
``git gc`` would have made three owner-acceptance records unverifiable everywhere. The fix published them as tags,
so a tag must count as delivery, but only a tag the remote actually has: a local tag is as stranded as a local
branch.

The remote's tags are listed with ``git ls-remote --tags``. Where that fails (offline, or a credential-less CI
checkout of a private repository), the tags in a GitHub Actions checkout came from the remote by construction, so
they are trusted there and nowhere else; anywhere else the failure is reported and tags do not count.

A squash-merged PR's commits count too: GitHub keeps every PR head as ``refs/pull/<n>/head`` after the branch is
deleted, so they stay fetchable. A PR head is matched from ``git ls-remote``; a commit inside such a PR, with
``pulls_lookup`` set, by GitHub's commit-to-PR association for a merged PR.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


def git_out(repo: Path, *args: str) -> str | None:
    """Return a git command's stripped stdout, or None when it fails."""
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


def object_type(repo: Path, oid: str) -> str | None:
    """Return ``commit``/``tree``/``blob``/``tag`` for an object in ``repo``, or None when it is absent."""
    return git_out(repo, "cat-file", "-t", oid)


def object_types(repo: Path, oids: list[str]) -> dict[str, str | None]:
    """Return each id's object type (None when absent), from one ``git cat-file --batch-check`` call."""
    done = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="".join(f"{oid}\n" for oid in oids),
        capture_output=True,
        text=True,
        check=True,
    )
    types: dict[str, str | None] = dict.fromkeys(oids)
    for line in done.stdout.splitlines():
        name, _, kind = line.partition(" ")
        if kind != "missing" and name in types:
            types[name] = kind
    return types


@dataclass
class Publication:
    """The remote's view of ``repo``: which tag names it has, and why tags are not trusted when they are not."""

    repo: Path
    remote: str = "origin"
    # Last resort for a commit inside a squash-merged PR that is not the PR's head: GitHub's commit-to-PR
    # association. None disables it (offline, or a test that must not reach the network).
    pulls_lookup: Callable[[Path, str], int | None] | None = None
    # PR refs are delivery for the observation log (the work reached its reader), but not for a pinned record:
    # a CI checkout (fetch-depth: 0) fetches branches and tags, never refs/pull/*.
    accept_pull_refs: bool = True
    _pull_refs: dict[str, str] | None = None
    _remote_tags: set[str] | None = None
    _tag_note: str | None = None
    _loaded: bool = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        listing = git_out(self.repo, "ls-remote", "--tags", self.remote)
        if listing is not None:
            names = {line.split("\t", 1)[1] for line in listing.splitlines() if "\t" in line}
            self._remote_tags = {name.removesuffix("^{}") for name in names}
        elif os.environ.get("GITHUB_ACTIONS") == "true":
            # The checkout fetched these tags from the remote; nothing else can have created them.
            local = git_out(self.repo, "for-each-ref", "--format=%(refname)", "refs/tags") or ""
            self._remote_tags = set(local.splitlines())
        else:
            self._remote_tags = set()
            self._tag_note = f"could not list {self.remote}'s tags, so tags were not counted as published"

    @property
    def tag_note(self) -> str | None:
        """Why tags were not counted, when they were not."""
        self._load()
        return self._tag_note

    def published_by(self, sha: str) -> str | None:
        """Return a remote ref that contains ``sha``, or None when the commit is on no published ref."""
        branches = git_out(self.repo, "for-each-ref", "--contains", sha, "--format=%(refname)", "refs/remotes")
        if branches:
            return branches.splitlines()[0]
        self._load()
        tags = git_out(self.repo, "for-each-ref", "--contains", sha, "--format=%(refname)", "refs/tags") or ""
        for ref in tags.splitlines():
            if ref in (self._remote_tags or set()):
                return ref
        if not self.accept_pull_refs:
            return None
        full = git_out(self.repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}") or sha
        pull = self._pull_heads().get(full)
        if pull:
            return pull
        merged = self.pulls_lookup(self.repo, full) if self.pulls_lookup else None
        return f"merged PR #{merged}" if merged else None

    def published_by_tag(self, sha: str) -> str | None:
        """Return a remote tag that contains ``sha``, or None. Unlike a branch, a tag survives a squash merge."""
        self._load()
        tags = git_out(self.repo, "for-each-ref", "--contains", sha, "--format=%(refname)", "refs/tags") or ""
        return next((ref for ref in tags.splitlines() if ref in (self._remote_tags or set())), None)

    def _pull_heads(self) -> dict[str, str]:
        """Map each remote ``refs/pull/<n>/head`` commit to its ref, listed once.

        Obs 2026-10-17-squash-merge-strands-the-pr-commits-entries-cite: a squash-merged PR's branch is deleted,
        but GitHub keeps its head as ``refs/pull/<n>/head``, fetchable from a clean clone.
        """
        if self._pull_refs is None:
            listing = git_out(self.repo, "ls-remote", self.remote, "refs/pull/*/head") or ""
            self._pull_refs = {
                line.split("\t", 1)[0]: line.split("\t", 1)[1] for line in listing.splitlines() if "\t" in line
            }
        return self._pull_refs


def merged_pull_request(repo: Path, sha: str) -> int | None:
    """The number of a merged PR GitHub associates with ``sha`` (its commits stay fetchable as pull/N/head)."""
    done = subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/commits/{sha}/pulls", "--jq", "[.[] | select(.merged_at) | .number]"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        return None
    try:
        numbers = json.loads(done.stdout or "[]")
    except ValueError:
        return None
    return numbers[0] if numbers else None
