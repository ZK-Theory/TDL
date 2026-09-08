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
        f"{_msys_path(worktree)}/.claude/hooks/run_staged_contract_gate.py --repo-root {_msys_path(worktree)} --",
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
  "diff --no-ext-diff --binary")
    if [ -f "$HOOK_TEST_MARKER" ]; then printf 'synthetic-diff\n'; fi
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
  *run_staged_contract_gate.py*) touch "$HOOK_TEST_MARKER" ;;
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


CLAUDE_MD_BODY = (
    "# CLAUDE.md\n"
    "\n"
    "<!-- REPOWISE:START — Do not edit below this line. Auto-generated by Repowise. -->\n"
    "Last indexed: 2026-01-01 (commit aaaaaaa).\n"
    "<!-- REPOWISE:END -->\n"
)
WORKSPACE_BODY = "version: 1\nrepos:\n- alias: tdl\n  last_commit_at_index: aaaaaaaaaaaaaaaa\n"
REPOWISE_OWNED = (".claude/CLAUDE.md", ".repowise-workspace.yaml")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr}"
    return completed


def _repowise_fixture_repo(tmp_path: Path, mutated_by_gate: tuple[str, ...]) -> tuple[Path, dict[str, str]]:
    """A real git repo whose contract gate mutates ``mutated_by_gate`` as a side effect.

    Real git, not the stub used by the tests above: the property under test is what
    `git status` reports once the whole hook has run, which a stub cannot answer.
    """
    repo = tmp_path / "repo"
    (repo / ".claude").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "hook-test@example.invalid")
    _git(repo, "config", "user.name", "Hook Test")
    _git(repo, "config", "core.autocrlf", "false")

    (repo / ".claude" / "CLAUDE.md").write_text(CLAUDE_MD_BODY, encoding="utf-8", newline="\n")
    (repo / ".repowise-workspace.yaml").write_text(WORKSPACE_BODY, encoding="utf-8", newline="\n")
    (repo / "uv.lock").write_text("version = 1\n", encoding="utf-8", newline="\n")
    (repo / "notes.md").write_text("one\n", encoding="utf-8", newline="\n")
    # The stand-in interpreter lives under .venv/, as it does in a real checkout;
    # ignoring it keeps `git status` an assertion about tracked bytes only.
    (repo / ".gitignore").write_text(".venv/\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")

    _write_executable(
        repo / ".venv" / "Scripts" / "python.exe",
        """#!/bin/sh
case "$*" in
  *run_staged_contract_gate.py*)
    for p in $HOOK_TEST_MUTATE; do
      printf 'rewritten mid-gate by the background repowise updater\\n' >> "$HOOK_TEST_REPO/$p"
    done
    ;;
esac
exit 0
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "HOOK_TEST_REPO": _msys_path(repo),
            "HOOK_TEST_MUTATE": " ".join(mutated_by_gate),
        }
    )
    return repo, env


def _run_hook(repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    git_bash = _git_bash()
    assert git_bash is not None
    return subprocess.run(
        [str(git_bash), _msys_path(HOOK)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_leaves_repowise_owned_files_byte_identical_on_the_success_path(
    tmp_path: Path,
) -> None:
    """Obs 2026-08-09-commit-gate-repowise-tracked-write: the watched clean-worktree control.

    Starts from clean tracked Repowise setup files, runs the full commit validation
    path with a gate that rewrites both of them mid-run — standing in for the
    previous commit's backgrounded `repowise update`, which is what actually writes
    those two paths — and asserts the SUCCESSFUL-commit path (not only the blocked
    one) ends with both files byte-identical to how it found them and the worktree
    clean apart from the author's own staged change.
    """
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED)
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    (repo / "notes.md").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "notes.md")

    completed = _run_hook(repo, env)

    assert completed.returncode == 0, completed.stderr
    for path in REPOWISE_OWNED:
        assert (repo / path).read_bytes() == before[path], f"{path} was not restored byte-for-byte"
    assert _git(repo, "status", "--porcelain").stdout == "M  notes.md\n"
    assert "restored Repowise-owned tracked file(s) to their pre-gate bytes" in completed.stderr
    for path in REPOWISE_OWNED:
        assert path in completed.stderr


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_still_blocks_when_a_gate_rewrites_a_staged_repowise_file(tmp_path: Path) -> None:
    """Negative control: the Repowise exemption must not cover the author's staged bytes.

    A staged `.claude/CLAUDE.md` is deliberate content, not background churn. It is
    never snapshotted, so a gate that rewrites it underneath the author still trips
    gate 3 — the exemption narrows which paths are exempt, it does not disarm the gate.
    """
    repo, env = _repowise_fixture_repo(tmp_path, (".claude/CLAUDE.md",))
    (repo / ".claude" / "CLAUDE.md").write_text(CLAUDE_MD_BODY + "author's own edit\n", encoding="utf-8", newline="\n")
    _git(repo, "add", ".claude/CLAUDE.md")

    completed = _run_hook(repo, env)

    assert completed.returncode == 1
    assert "modified tracked file(s) outside the staged set" in completed.stderr
    assert ".claude/CLAUDE.md" in completed.stderr
    assert "restored Repowise-owned tracked file(s)" not in completed.stderr


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_restores_repowise_owned_files_even_when_a_gate_blocks(tmp_path: Path) -> None:
    """A blocked commit must not leave a half-applied refresh behind either.

    The restore runs from an EXIT trap as well as inline, so the early-exit paths
    (a failing gate) hand the worktree back in the state they received it.
    """
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED)
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    # Make gate 0 fail: the fake interpreter reports failure for sync_agent_skills.py.
    _write_executable(
        repo / ".venv" / "Scripts" / "python.exe",
        """#!/bin/sh
case "$*" in
  *sync_agent_skills.py*)
    for p in $HOOK_TEST_MUTATE; do
      printf 'rewritten mid-gate by the background repowise updater\\n' >> "$HOOK_TEST_REPO/$p"
    done
    exit 1
    ;;
esac
exit 0
""",
    )

    completed = _run_hook(repo, env)

    assert completed.returncode == 1
    assert "skill trees diverged" in completed.stderr
    for path in REPOWISE_OWNED:
        assert (repo / path).read_bytes() == before[path], f"{path} was not restored on the blocked path"
    assert _git(repo, "status", "--porcelain").stdout == ""
