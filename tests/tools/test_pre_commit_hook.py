"""Focused liveness controls for the tracked pre-commit launcher."""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".githooks" / "pre-commit"
VALIDATOR = REPO_ROOT / ".claude" / "hooks" / "contract_binding_check.py"


def _gate_3_source() -> str:
    """Return the source of the binding-test runner, located by AST rather than by line."""
    tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "gate_3_run_bindings":
            return ast.get_source_segment(VALIDATOR.read_text(encoding="utf-8"), node) or ""
    raise AssertionError("gate_3_run_bindings not found in the contract validator")


def test_binding_gate_honours_the_launcher_interpreter_instead_of_re_entering_uv() -> None:
    """The launcher's interpreter choice must not be undone one layer down.

    ``.githooks/pre-commit`` resolves the main checkout's interpreter so a linked worktree's own
    venv is never used or bootstrapped mid-commit. Gate 3 used to run ``uv run pytest`` with
    ``cwd`` set to the worktree, which made ``uv`` resolve that worktree as its project and try to
    sync it — so a source-only dependency failing to build there failed the *contract* gate, an
    environment fault wearing a correctness fault's clothes.

    Asserted against the source rather than by executing the gate: running it would invoke the
    whole contract suite, and the property under test is which interpreter is chosen, which is a
    static fact.
    """
    source = _gate_3_source()
    assert "sys.executable" in source, "gate 3 must run the interpreter it was launched with"
    assert '"uv"' not in source and "'uv'" not in source, (
        "gate 3 must not re-enter uv: it resolves the project at cwd, which in a linked worktree "
        "is the worktree, reintroducing the sync/build the launcher exists to avoid"
    )


def test_the_interpreter_running_the_validator_can_run_pytest() -> None:
    """``sys.executable -m pytest`` is only safe if pytest is importable from that interpreter."""
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def _git_bash() -> Path | None:
    # A Git-for-Windows install has several git.exe copies (cmd/, bin/,
    # mingw64/bin/) at different depths from the shared bin/bash.exe, so
    # deriving bash's path from wherever `which git` resolved is unreliable —
    # it silently skipped every test in this file when git resolved through
    # mingw64/bin/. Try the discovered git's sibling bin/ first, then the
    # standard install-root fallback.
    discovered = shutil.which("git")
    candidates = [
        Path(discovered).resolve().parents[1] / "bin" / "bash.exe" if discovered else None,
        Path(discovered).resolve().parents[2] / "bin" / "bash.exe" if discovered else None,
        Path(r"C:\Program Files\Git\bin\bash.exe"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    return None


def _msys_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix()[2:]
    return f"/{drive}{tail}"


def _write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(0o755)


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_linked_worktree_uses_main_python_without_bootstrapping_local_venv(tmp_path: Path) -> None:
    """Observation 108: hook routing must leave a venv-free worktree untouched."""
    main_root = tmp_path / "main"
    worktree = tmp_path / "linked-worktree"
    fake_bin = tmp_path / "fake-bin"
    bash_env = tmp_path / "bash-env"
    invocation_log = tmp_path / "python-invocations.log"
    main_root.joinpath(".git").mkdir(parents=True)
    worktree.mkdir()

    _write_executable(
        fake_bin / "git",
        """#!/bin/sh
case "$*" in
  "rev-parse --show-toplevel") printf '%s\n' "$HOOK_TEST_WORKTREE" ;;
  "rev-parse --git-common-dir") printf '%s\n' "$HOOK_TEST_MAIN/.git" ;;
  *) exit 0 ;;
esac
""",
    )
    _write_executable(bash_env, 'export PATH="$HOOK_TEST_PATH"\n')
    _write_executable(
        main_root / ".venv" / "Scripts" / "python.exe",
        """#!/bin/sh
printf '%s\n' "$*" >> "$HOOK_TEST_LOG"
exit 0
""",
    )

    env = os.environ.copy()
    git_bash = _git_bash()
    assert git_bash is not None
    env.update(
        {
            "HOOK_TEST_MAIN": _msys_path(main_root),
            "HOOK_TEST_WORKTREE": _msys_path(worktree),
            "HOOK_TEST_LOG": _msys_path(invocation_log),
            "HOOK_TEST_PATH": f"{_msys_path(fake_bin)}:/usr/bin:/bin",
            "BASH_ENV": _msys_path(bash_env),
        }
    )
    completed = subprocess.run(
        [str(git_bash), _msys_path(HOOK)],
        cwd=worktree,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert not (worktree / ".venv").exists()
    invocations = invocation_log.read_text(encoding="utf-8").splitlines()
    assert invocations == [
        f"{_msys_path(worktree)}/tools/sync_agent_skills.py --check",
        f"{_msys_path(worktree)}/.claude/hooks/contract_binding_check.py",
    ]


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_blocks_when_a_gate_mutates_a_tracked_file(tmp_path: Path) -> None:
    """Obs 01KYQ6AMEXS5SZEEGX9RB9QKHF: a validation gate must not leave a side effect.

    A timed-out `git commit` left orphaned pre-commit children running, which
    completed and rewrote a clean, unstaged, unrelated `uv.lock`. Simulates a
    gate (standing in for contract_binding_check.py) that mutates a tracked
    file as a side effect, and asserts the new no-new-diff gate blocks it
    rather than letting the commit proceed with an unremarked mutation.
    """
    main_root = tmp_path / "main"
    worktree = tmp_path / "linked-worktree"
    fake_bin = tmp_path / "fake-bin"
    bash_env = tmp_path / "bash-env"
    marker = tmp_path / "gate-mutated-a-tracked-file"
    main_root.joinpath(".git").mkdir(parents=True)
    worktree.mkdir()

    _write_executable(
        fake_bin / "git",
        """#!/bin/sh
case "$*" in
  "rev-parse --show-toplevel") printf '%s\n' "$HOOK_TEST_WORKTREE" ;;
  "rev-parse --git-common-dir") printf '%s\n' "$HOOK_TEST_MAIN/.git" ;;
  "diff --name-only")
    if [ -f "$HOOK_TEST_MARKER" ]; then printf 'uv.lock\n'; fi
    ;;
  *) exit 0 ;;
esac
""",
    )
    _write_executable(bash_env, 'export PATH="$HOOK_TEST_PATH"\n')
    _write_executable(
        main_root / ".venv" / "Scripts" / "python.exe",
        """#!/bin/sh
case "$*" in
  *contract_binding_check.py*) touch "$HOOK_TEST_MARKER" ;;
esac
exit 0
""",
    )

    env = os.environ.copy()
    git_bash = _git_bash()
    assert git_bash is not None
    env.update(
        {
            "HOOK_TEST_MAIN": _msys_path(main_root),
            "HOOK_TEST_WORKTREE": _msys_path(worktree),
            "HOOK_TEST_MARKER": _msys_path(marker),
            "HOOK_TEST_PATH": f"{_msys_path(fake_bin)}:/usr/bin:/bin",
            "BASH_ENV": _msys_path(bash_env),
        }
    )
    completed = subprocess.run(
        [str(git_bash), _msys_path(HOOK)],
        cwd=worktree,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "modified tracked file(s) outside the staged set" in completed.stderr
    assert "uv.lock" in completed.stderr
