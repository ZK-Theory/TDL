#!/usr/bin/env python3
"""Verify (and, if asked, install) the repository's git hooks in the ACTIVE hook directory.

Why this file is a verifier and not a copier
--------------------------------------------
The previous version hardcoded ``.git/hooks`` as the install target and never
consulted ``core.hooksPath``. This repository sets ``core.hooksPath = .githooks``
(commit a54a2c4, 2026-04-10), so git ignores ``.git/hooks`` entirely. The contract
validator was installed to ``.git/hooks/pre-commit`` on 2026-05-27 and never ran
once — for 47 days the installer printed "Installed pre-commit -> .../.git/hooks/
pre-commit" and exited 0 while having no effect whatsoever. A hook that is absent
does not error; it silently does nothing, which is why nothing surfaced.

Hooks now live in ``.githooks/``, which is tracked. That means there is nothing to
install: every clone and every linked worktree gets them from the working tree.
The job left for this script is to *prove the gate is live* — the check that was
missing.

Usage:
    python .claude/hooks/install-git-hooks.py            # verify (exit 1 on problems)
    python .claude/hooks/install-git-hooks.py --install  # copy any missing hook into the active dir
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/ -> .claude/ -> repo root

# Hooks that must exist in the ACTIVE hook directory, and their fallback source
# in .claude/hooks/ if one needs (re)installing. A None source means the tracked
# copy in the active directory is the only source of truth.
REQUIRED_HOOKS: dict[str, str | None] = {
    "pre-commit": None,
    "commit-msg": None,
    "prepare-commit-msg": None,
}


def active_hooks_dir() -> Path:
    """Resolve the directory git ACTUALLY reads hooks from.

    A relative core.hooksPath is taken relative to the top level of the working
    tree, so it resolves correctly inside linked worktrees too.
    """
    try:
        configured = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError as exc:  # pragma: no cover - git absent
        print(f"ERROR: could not invoke git: {exc}", file=sys.stderr)
        sys.exit(2)

    if not configured:
        return REPO_ROOT / ".git" / "hooks"
    path = Path(configured)
    return path if path.is_absolute() else REPO_ROOT / path


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def index_mode(path: Path) -> str | None:
    """Return the git index mode for a tracked file (e.g. '100755'), else None.

    On Windows the filesystem exec bit is invisible to os.stat, so it is useless as
    an executability signal — git runs hooks there regardless. The portable signal
    that actually matters is the mode recorded in the git index, because that is
    what POSIX clones check out. Check that, not the local stat.
    """
    rel = path.relative_to(REPO_ROOT).as_posix()
    out = subprocess.run(
        ["git", "ls-files", "-s", "--", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return out.split()[0] if out else None


def executable_problem(path: Path, name: str) -> str | None:
    """Report an executability problem, or None. Windows-aware."""
    mode = index_mode(path)
    if mode is not None:
        # Tracked: the index mode is authoritative for every clone.
        if mode != "100755":
            return f"{name}: git index mode is {mode}, not 100755 — POSIX clones will not run it (git update-index --chmod=+x)"
        return None
    # Untracked (e.g. copied into a worktree): only POSIX can tell us anything.
    if os.name != "nt" and not path.stat().st_mode & stat.S_IXUSR:
        return f"{name}: present but not executable — git will not run it"
    return None


def verify(install: bool = False) -> int:
    hooks_dir = active_hooks_dir()
    configured = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    print(f"core.hooksPath : {configured or '(unset)'}")
    print(f"active hooks   : {hooks_dir}")

    problems: list[str] = []

    if not hooks_dir.is_dir():
        problems.append(f"active hook directory does not exist: {hooks_dir}")

    for name, source_name in REQUIRED_HOOKS.items():
        dest = hooks_dir / name
        if not dest.exists():
            if install and source_name:
                src = REPO_ROOT / ".claude" / "hooks" / source_name
                if not src.exists():
                    problems.append(f"{name}: MISSING and no source at {src}")
                    continue
                shutil.copy2(src, dest)
                make_executable(dest)
                print(f"  [installed] {name} -> {dest}")
            else:
                problems.append(f"{name}: MISSING from the active hook directory — this hook NEVER RUNS")
                print(f"  [MISSING]   {name}")
                continue
        problem = executable_problem(dest, name)
        if problem:
            problems.append(problem)
            print(f"  [NOT EXEC]  {name}")
            continue
        print(f"  [ok]        {name}")

    # A hook sitting in .git/hooks while core.hooksPath points elsewhere is dead
    # weight that reads as "installed" to anyone who looks. Say so loudly.
    if configured:
        shadowed_dir = REPO_ROOT / ".git" / "hooks"
        if shadowed_dir.is_dir():
            dead = [
                p.name
                for p in shadowed_dir.iterdir()
                if p.is_file() and not p.name.endswith(".sample") and p.name in REQUIRED_HOOKS
            ]
            if dead:
                print(
                    f"\nWARNING: .git/hooks contains {', '.join(sorted(dead))}, which git IGNORES "
                    f"because core.hooksPath={configured}. These files do not run. Delete them so "
                    f"they cannot be mistaken for active hooks."
                )

    if problems:
        print("\nFAIL — the hook gate is not live:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print("\nOK — every required hook is present and executable in the directory git actually reads.")
    return 0


if __name__ == "__main__":
    sys.exit(verify(install="--install" in sys.argv))
