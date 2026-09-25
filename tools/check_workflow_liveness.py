#!/usr/bin/env python3
"""Fail closed when a tracked GitHub Actions workflow is not active.

Two modes over a saved `gh api .../actions/workflows` response:

* ``--target-path`` (default): one named workflow must be registered and active.
* ``--all-tracked``: every workflow file git tracks under ``.github/workflows/`` must be
  registered and active. The governed set comes from the tree, not a hand-written list, so a
  workflow added later is covered on arrival (obs
  2026-09-08-workflow-disabled-state-is-invisible-to-the-repo: `ci.yml` sat
  `disabled_manually` for five weeks, a state that lives only in the GitHub API, and the
  watchdog then named only two workflows). The response may be one ``{"workflows": [...]}``
  object or the list of pages ``gh api --paginate --slurp`` produces.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path


DEFAULT_TARGET_PATH = ".github/workflows/ars-artefact-currency.yml"
WORKFLOW_DIR = ".github/workflows/"


def workflow_rows(payload: object) -> list[Mapping[str, object]]:
    """Return every workflow row from one response object or a list of paginated pages."""
    pages = payload if isinstance(payload, list) else [payload]
    rows: list[Mapping[str, object]] = []
    for page in pages:
        if not isinstance(page, Mapping):
            raise ValueError("GitHub Actions response must be a JSON object or a list of them")
        workflows = page.get("workflows")
        if not isinstance(workflows, list):
            raise ValueError("GitHub Actions response must contain a workflows list")
        if not all(isinstance(workflow, Mapping) for workflow in workflows):
            raise ValueError("GitHub Actions response contains an invalid workflow row")
        rows.extend(workflows)
    return rows


def validate_workflow_liveness(payload: Mapping[str, object], *, target_path: str) -> None:
    """Require one target workflow and GitHub's active state for it."""
    matches = [workflow for workflow in workflow_rows(payload) if workflow.get("path") == target_path]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one workflow at {target_path}, found {len(matches)}")
    state = matches[0].get("state")
    if state != "active":
        raise ValueError(f"workflow at {target_path} is {state!r}, expected 'active'")


def tracked_workflow_paths(repo_root: Path) -> list[str]:
    """Return the workflow files git tracks, as repository-relative POSIX paths."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", WORKFLOW_DIR],
        cwd=repo_root,
        capture_output=True,
        check=True,
    ).stdout
    paths = [chunk.decode("utf-8") for chunk in out.split(b"\x00") if chunk]
    return sorted(path for path in paths if path.endswith((".yml", ".yaml")))


def inactive_tracked_workflows(payload: object, tracked: list[str]) -> list[str]:
    """Return one problem line per tracked workflow that is missing, duplicated, or not active."""
    by_path: dict[str, list[Mapping[str, object]]] = {}
    for row in workflow_rows(payload):
        by_path.setdefault(str(row.get("path")), []).append(row)
    problems: list[str] = []
    for path in tracked:
        rows = by_path.get(path, [])
        if not rows:
            problems.append(f"{path}: not registered with GitHub Actions, so it has never run")
        elif len(rows) > 1:
            problems.append(f"{path}: {len(rows)} registrations, expected one")
        elif rows[0].get("state") != "active":
            problems.append(f"{path} is {rows[0].get('state')!r}, expected 'active'")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Check the saved `gh api .../actions/workflows` response."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workflows-json", type=Path, required=True)
    parser.add_argument("--target-path", default=DEFAULT_TARGET_PATH)
    parser.add_argument(
        "--all-tracked",
        action="store_true",
        help="Require every workflow file git tracks under .github/workflows/ to be active.",
    )
    parser.add_argument(
        "--tracked-path",
        action="append",
        default=[],
        help="Override the tracked set (repeatable); default: git ls-files .github/workflows/.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.workflows_json.read_text(encoding="utf-8"))
        if args.all_tracked:
            tracked = args.tracked_path or tracked_workflow_paths(args.repo_root)
            if not tracked:
                raise ValueError(f"no tracked workflow files under {WORKFLOW_DIR}; refusing to pass vacuously")
            problems = inactive_tracked_workflows(payload, tracked)
            if problems:
                for line in problems:
                    print(f"ERROR: {line}", file=sys.stderr)
                return 1
            print(f"{len(tracked)} tracked workflow(s) active: {', '.join(tracked)}")
            return 0
        if not isinstance(payload, Mapping):
            raise ValueError("GitHub Actions response must be a JSON object")
        validate_workflow_liveness(payload, target_path=args.target_path)
    except (OSError, json.JSONDecodeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"active: {args.target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
