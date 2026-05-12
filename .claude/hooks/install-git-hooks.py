#!/usr/bin/env python3
"""Install repository git hooks from .claude/hooks into .git/hooks."""

from pathlib import Path
import shutil
import stat
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
GIT_HOOKS_DIR = REPO_ROOT / ".git" / "hooks"

HOOKS = {
    "commit-msg": "git-commit-msg.sh",
}


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_hooks() -> None:
    if not GIT_HOOKS_DIR.exists():
        print("ERROR: .git/hooks directory not found. Run this from the repository root.", file=sys.stderr)
        sys.exit(1)

    for dest_name, src_name in HOOKS.items():
        src_path = HOOKS_DIR / src_name
        dest_path = GIT_HOOKS_DIR / dest_name
        if not src_path.exists():
            print(f"ERROR: hook source not found: {src_path}", file=sys.stderr)
            sys.exit(1)

        shutil.copy2(src_path, dest_path)
        make_executable(dest_path)
        print(f"Installed {dest_name} -> {dest_path}")


if __name__ == "__main__":
    install_hooks()
