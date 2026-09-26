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
    python .claude/hooks/install-git-hooks.py --install  # activate .githooks for this clone, then verify
"""

from __future__ import annotations

import os
import shlex
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
    "pre-push": None,
    "commit-msg": None,
    "prepare-commit-msg": None,
}


def active_hooks_dir() -> tuple[str, Path]:
    """Resolve the directory git ACTUALLY reads hooks from.

    A relative core.hooksPath is taken relative to the top level of the working
    tree, so it resolves correctly inside linked worktrees too.

    Returns:
        The configured core.hooksPath ('' when unset) and the resolved directory.
        Both are returned together so callers never re-shell to git for the same
        value.
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
        return configured, REPO_ROOT / ".git" / "hooks"
    path = Path(configured)
    return configured, path if path.is_absolute() else REPO_ROOT / path


def foreign_hooks_problem(hooks_dir: Path) -> str | None:
    """Return a problem when the active hook directory lies outside this checkout's own tree.

    A present, executable hook proves a hook will run, not that it is THIS branch's hook
    (obs 2026-09-17-worktree-scoped-hookspath-runs-main-checkout-hooks). Desktop-session
    worktrees carried an absolute `core.hooksPath` in `config.worktree` pointing at the main
    checkout's `.githooks`, so a commit there ran the main checkout's hook bytes and a hook fix
    on the branch never executed at commit time. Tracked hooks must resolve inside the tree.
    """
    toplevel = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    if not toplevel:
        return None
    root = Path(toplevel).resolve()
    if hooks_dir.resolve().is_relative_to(root):
        return None
    scope = subprocess.run(
        ["git", "config", "--show-scope", "--show-origin", "--get", "core.hooksPath"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return (
        f"active hook directory {hooks_dir} is outside this checkout ({root}); commits here run "
        f"another checkout's hook bytes. Set by: {scope or 'unknown'}. Fix it where it was set, "
        f"so the tracked .githooks resolves here: {hookspath_remedy(REPO_ROOT)}"
    )


def hookspath_remedy(checkout: Path) -> str:
    """Return the command that clears a foreign core.hooksPath in the config scope that set it.

    `--worktree` edits only config.worktree, so it cannot clear a value that comes from the
    shared local config or the global one. The local scope is the repository's own binding, so
    it is reset to the relative `.githooks` rather than unset, which would disable the hooks. A
    global or system value is overridden with that same local setting, never removed: other
    repositories on the machine may rely on it.
    """
    scope = (
        subprocess.run(
            ["git", "config", "--show-scope", "--get", "core.hooksPath"],
            cwd=checkout,
            capture_output=True,
            text=True,
            check=False,
        )
        .stdout.split("\t", 1)[0]
        .strip()
    )
    fixes = {
        "worktree": ["--worktree", "--unset", "core.hooksPath"],
        "local": ["--local", "core.hooksPath", ".githooks"],
        "global": ["--local", "core.hooksPath", ".githooks"],
        "system": ["--local", "core.hooksPath", ".githooks"],
    }
    if scope in fixes:
        return shlex.join(["git", "-C", str(checkout), "config", *fixes[scope]])
    return f"core.hooksPath comes from scope '{scope or 'unknown'}' (a -c option or GIT_CONFIG_* variable); remove it there"


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def activate_tracked_hooks() -> tuple[str, Path]:
    """Bind this clone to the tracked hook directory and return the active path."""
    tracked = REPO_ROOT / ".githooks"
    if not tracked.is_dir():
        raise RuntimeError(f"tracked hook directory does not exist: {tracked}")
    proc = subprocess.run(
        ["git", "config", "--local", "core.hooksPath", ".githooks"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        diagnostic = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"could not activate tracked hooks: {diagnostic or 'git config failed'}")
    return ".githooks", tracked


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
    configured, hooks_dir = active_hooks_dir()

    if install and not configured:
        try:
            configured, hooks_dir = activate_tracked_hooks()
        except RuntimeError as exc:
            print(f"FAIL - {exc}", file=sys.stderr)
            return 1
        print("activated clone-local core.hooksPath=.githooks")

    print(f"core.hooksPath : {configured or '(unset)'}")
    print(f"active hooks   : {hooks_dir}")

    problems: list[str] = []

    foreign = foreign_hooks_problem(hooks_dir)
    if foreign:
        print("\nFAIL — the hook gate is not this checkout's:", file=sys.stderr)
        print(f"  - {foreign}", file=sys.stderr)
        return 1

    if not hooks_dir.is_dir():
        # Deliberately NOT created here, even under --install. .githooks/ is tracked,
        # so a missing active hook directory means a broken checkout, not something an
        # installer should quietly conjure into existence — creating it would turn the
        # loudest possible symptom back into the silence this script exists to end.
        # The copy path below creates parents only when it truly has a hook to write.
        problems.append(f"active hook directory does not exist: {hooks_dir}")

    for name, source_name in REQUIRED_HOOKS.items():
        dest = hooks_dir / name
        if not dest.exists():
            if install and source_name:
                src = REPO_ROOT / ".claude" / "hooks" / source_name
                if not src.exists():
                    problems.append(f"{name}: MISSING and no source at {src}")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
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
