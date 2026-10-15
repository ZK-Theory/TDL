#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group A)
# Purpose: Fail when an authority object under .research-system/ pins a git object that a clean clone of the
# remote cannot fetch, so an accepted record can never again depend on one machine's local branches.
"""Check that every git id pinned under ``.research-system/`` is published.

Obs 2026-10-15-accepted-contracts-pin-commits-on-local-only-branches: five review commits pinned by accepted
contracts existed only on local branches. Locally every test passed. In the nightly CI clone 12 tests failed with
"immutable Git object unavailable", and nothing named the cause.

Every 40-hex token in a ``.yaml``/``.yml``/``.json`` file under the root must be one of:

* a commit published on a remote branch or a remote tag (``tools/commit_reachability.py``);
* a tree or blob present in the checkout (a ``git_blob`` pin; its commit is checked through its own pin);
* listed in ``FOREIGN`` with the repository it belongs to.

An id that is none of these fails as **unavailable**. That is the CI symptom itself: a clean clone without the
object cannot tell a local-only commit from a typo, and either way the record cannot be verified. The check must
therefore run in a full-history checkout with tags (``fetch-depth: 0``); in a shallow one, everything is
unavailable and the check says so instead of passing.

Usage: python tools/check_pinned_commits.py [--repo REPO] [--root .research-system]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit_reachability import Publication, object_types  # noqa: E402

# Ids that name objects in other repositories. Each needs its repository and the record that pins it.
FOREIGN: dict[str, str] = {
    "145efcde673f1a1897eff250b77221d26c34c479": (
        "berenslab/eff-ph tag neurips2024, pinned by schemas/contracts/wp6-6/spec-01-source-correction-v1"
    ),
}

_ID = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")
_SUFFIXES = {".yaml", ".yml", ".json"}


def pinned_ids(root: Path) -> dict[str, list[Path]]:
    """Map every 40-hex id under ``root`` to the files that contain it."""
    found: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*")):
        if path.suffix in _SUFFIXES and path.is_file():
            for oid in dict.fromkeys(_ID.findall(path.read_text(encoding="utf-8", errors="replace"))):
                found.setdefault(oid, []).append(path)
    return found


def check(repo: Path, root: Path) -> tuple[list[str], str]:
    """Return (problems, summary) for every id pinned under ``root``."""
    publication = Publication(repo)
    problems: list[str] = []
    counts = {"commit": 0, "tree/blob": 0, "foreign": 0}
    shallow = (repo / ".git" / "shallow").is_file() or ((repo / ".git").is_file() and _gitdir_shallow(repo))
    pinned = pinned_ids(root)
    types = object_types(repo, [oid for oid in pinned if oid not in FOREIGN])
    for oid, paths in pinned.items():
        where = ", ".join(str(p.relative_to(repo)).replace("\\", "/") for p in paths[:3])
        if oid in FOREIGN:
            counts["foreign"] += 1
            continue
        kind = types[oid]
        if kind == "commit":
            counts["commit"] += 1
            if publication.published_by(oid) is None:
                problems.append(
                    f"{oid[:12]} (pinned in {where}) is a commit on no remote branch or remote tag; "
                    "publish it (a tag is enough) or the record cannot be verified from a clean clone"
                )
        elif kind in ("tree", "blob", "tag"):
            counts["tree/blob"] += 1
        else:
            problems.append(
                f"{oid[:12]} (pinned in {where}) is not an object in this checkout; fetch the remote's full "
                "history and tags, publish the object, or list it in FOREIGN with its repository"
            )
    summary = (
        f"pinned ids: {counts['commit']} commit(s) published-checked, {counts['tree/blob']} tree/blob(s) present, "
        f"{counts['foreign']} foreign, {len(problems)} problem(s)"
    )
    if shallow:
        summary += "; this checkout is shallow, so unavailable ids may only be missing history"
    if problems and publication.tag_note:
        summary += f"; {publication.tag_note}"
    return problems, summary


def _gitdir_shallow(repo: Path) -> bool:
    text = (repo / ".git").read_text(encoding="utf-8").strip()
    gitdir = Path(text.removeprefix("gitdir:").strip())
    return (gitdir / "shallow").is_file()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--root", type=Path, default=None, help="Defaults to REPO/.research-system.")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    root = (args.root or repo / ".research-system").resolve()
    problems, summary = check(repo, root)
    print(summary)
    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
