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
"""

from __future__ import annotations

import os
import subprocess
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
        return None
