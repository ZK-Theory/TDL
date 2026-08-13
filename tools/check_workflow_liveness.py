#!/usr/bin/env python3
"""Fail closed when the designated ARS currency workflow is not active."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path


DEFAULT_TARGET_PATH = ".github/workflows/ars-artefact-currency.yml"


def validate_workflow_liveness(payload: Mapping[str, object], *, target_path: str) -> None:
    """Require one target workflow and GitHub's active state for it."""
    workflows = payload.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("GitHub Actions response must contain a workflows list")
    if not all(isinstance(workflow, Mapping) for workflow in workflows):
        raise ValueError("GitHub Actions response contains an invalid workflow row")

    matches = [workflow for workflow in workflows if workflow.get("path") == target_path]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one workflow at {target_path}, found {len(matches)}")
    state = matches[0].get("state")
    if state != "active":
        raise ValueError(f"workflow at {target_path} is {state!r}, expected 'active'")


def main(argv: list[str] | None = None) -> int:
    """Check the saved `gh api .../actions/workflows` response."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows-json", type=Path, required=True)
    parser.add_argument("--target-path", default=DEFAULT_TARGET_PATH)
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.workflows_json.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("GitHub Actions response must be a JSON object")
        validate_workflow_liveness(payload, target_path=args.target_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"active: {args.target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
