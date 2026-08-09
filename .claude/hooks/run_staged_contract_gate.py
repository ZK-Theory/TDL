#!/usr/bin/env python3
"""Run the contract validator against an isolated materialization of the index."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def run(repo_root: Path, validator_args: list[str]) -> int:
    """Materialize index bytes outside the repository and validate only them."""
    root = repo_root.resolve()
    git_dir = Path(_git(root, "rev-parse", "--absolute-git-dir").stdout.strip()).resolve()
    with tempfile.TemporaryDirectory(prefix="tdl-staged-contract-") as temp_dir:
        staged_root = Path(temp_dir).resolve()
        prefix = staged_root.as_posix().rstrip("/") + "/"
        _git(root, "checkout-index", "--all", "--force", f"--prefix={prefix}")
        # Several validators locate the repository by walking for a .git entry
        # before they invoke Git. A normal linked worktree uses this same
        # gitfile form, so expose the real object database without copying any
        # working-tree bytes into the candidate.
        (staged_root / ".git").write_text(f"gitdir: {git_dir.as_posix()}\n", encoding="utf-8")
        validator = staged_root / ".claude" / "hooks" / "contract_binding_check.py"
        if not validator.is_file():
            print("ERROR: staged candidate omits contract_binding_check.py", file=sys.stderr)
            return 2
        env = os.environ.copy()
        env.update(
            {
                "GIT_DIR": str(git_dir),
                "GIT_WORK_TREE": str(staged_root),
                "PYTHONDONTWRITEBYTECODE": "1",
                "TDL_STAGED_CANDIDATE": "1",
            }
        )
        completed = subprocess.run(
            [sys.executable, str(validator), *validator_args],
            cwd=staged_root,
            env=env,
            check=False,
        )
        return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("validator_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    validator_args = args.validator_args[1:] if args.validator_args[:1] == ["--"] else args.validator_args
    return run(args.repo_root, validator_args)


if __name__ == "__main__":
    raise SystemExit(main())
