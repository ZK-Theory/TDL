"""Focused liveness controls for the tracked pre-commit launcher."""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import time
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

# What a stand-in writer does to a Repowise-owned file, chosen by HOOK_TEST_MUTATE_MODE:
#   region  — rewrite only generated bytes, as `repowise update` does: the commit hash
#             inside the REPOWISE block, and the `last_commit_at_index` scalar.
#   outside — append a line after the generated block: bytes the updater never owns,
#             standing in for a gate side effect or an author's concurrent save.
#   both    — the two at once.
# HOOK_TEST_FROM / HOOK_TEST_TO let a second wave of generated churn be expressed.
MUTATE_SH = r"""mutate() {
  for p in $HOOK_TEST_MUTATE; do
    f="$HOOK_TEST_REPO/$p"
    case "${HOOK_TEST_MUTATE_MODE:-region}" in
      region|both) sed -i "s/${HOOK_TEST_FROM:-aaaaaaa}/${HOOK_TEST_TO:-bbbbbbb}/g" "$f" ;;
    esac
    case "${HOOK_TEST_MUTATE_MODE:-region}" in
      outside|both) printf 'written outside the generated region\n' >> "$f" ;;
    esac
  done
}"""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr}"
    return completed


def _repowise_fixture_repo(
    tmp_path: Path, mutated_by_gate: tuple[str, ...], mode: str = "region"
) -> tuple[Path, dict[str, str]]:
    """A real git repo whose contract gate mutates ``mutated_by_gate`` as a side effect.

    Real git, not the stub used by the tests above: the property under test is what
    `git status` reports once the whole hook has run, which a stub cannot answer.
    ``mode`` selects which bytes the gate writes; see ``MUTATE_SH``.
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
    # The stand-in interpreter lives under .venv/ and the updater's lock under
    # .repowise/, as in a real checkout; ignoring both keeps `git status` an
    # assertion about tracked bytes only.
    (repo / ".gitignore").write_text(".venv/\n.repowise/\n", encoding="utf-8", newline="\n")
    (repo / ".repowise").mkdir()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")

    _write_fake_interpreter(repo, "  *run_staged_contract_gate.py*) mutate ;;")

    env = os.environ.copy()
    env.update(
        {
            "HOOK_TEST_REPO": _msys_path(repo),
            "HOOK_TEST_MUTATE": " ".join(mutated_by_gate),
            "HOOK_TEST_MUTATE_MODE": mode,
        }
    )
    return repo, env


def _write_fake_interpreter(repo: Path, case_arms: str) -> None:
    """Stand in for the main-checkout interpreter; ``case_arms`` decide what each gate does."""
    _write_executable(
        repo / ".venv" / "Scripts" / "python.exe",
        f"""#!/bin/sh
{MUTATE_SH}
case "$*" in
{case_arms}
esac
exit 0
""",
    )


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


def _wait_until_absent(path: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not path.exists():
            return True
        time.sleep(0.05)
    return not path.exists()


RESTORED = "restored the Repowise-generated region of:"
GATE_3_BLOCKED = "modified tracked file(s) outside the staged set"
OUTSIDE_LINE = b"written outside the generated region\n"


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_restores_the_generated_region_on_the_success_path(tmp_path: Path) -> None:
    """Obs 2026-08-09-commit-gate-repowise-tracked-write: the watched clean-worktree control.

    A gate rewrites the generated bytes of both Repowise-owned files mid-run — standing
    in for the previous commit's backgrounded `repowise update`, the only legitimate
    writer of those bytes — and the SUCCESSFUL-commit path must end with both files
    byte-identical and the worktree clean apart from the author's staged change.

    The mutation is deliberately confined to the generated region. An earlier version
    appended a line past the end of the block; that passed only because the restore
    was a whole-file `cp`, which review of PR #279 showed also erased gate side effects
    and concurrent edits. Those cases are pinned separately below.
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
    assert RESTORED in completed.stderr
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
    assert GATE_3_BLOCKED in completed.stderr
    assert ".claude/CLAUDE.md" in completed.stderr
    assert RESTORED not in completed.stderr


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_restores_the_generated_region_even_when_a_gate_blocks(tmp_path: Path) -> None:
    """A blocked commit must not leave a half-applied refresh behind either.

    The restore runs from an EXIT trap as well as inline, so the early-exit paths
    (a failing gate) hand the worktree back in the state they received it.
    """
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED)
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    _write_fake_interpreter(repo, "  *sync_agent_skills.py*) mutate; exit 1 ;;")

    completed = _run_hook(repo, env)

    assert completed.returncode == 1
    assert "skill trees diverged" in completed.stderr
    for path in REPOWISE_OWNED:
        assert (repo / path).read_bytes() == before[path], f"{path} was not restored on the blocked path"
    assert _git(repo, "status", "--porcelain").stdout == ""


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_blocks_and_keeps_the_evidence_when_a_gate_writes_outside_the_generated_region(
    tmp_path: Path,
) -> None:
    """A gate side effect on a Repowise-owned path must still reach gate 3 (review of PR #279).

    The whole-file restore used to erase this before gate 3 looked, so the commit was
    accepted. Bytes outside the generated region are never the updater's, so they are
    neither restored nor masked: the commit blocks, names the file, and the written
    bytes are still there to investigate.
    """
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED, mode="outside")
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    (repo / "notes.md").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "notes.md")

    completed = _run_hook(repo, env)

    assert completed.returncode == 1, completed.stderr
    assert GATE_3_BLOCKED in completed.stderr
    for path in REPOWISE_OWNED:
        assert path in completed.stderr
        assert (repo / path).read_bytes() == before[path] + OUTSIDE_LINE, f"{path}: the gate's write was erased"
    assert RESTORED not in completed.stderr


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_restores_only_the_generated_region_and_preserves_a_concurrent_edit(tmp_path: Path) -> None:
    """A save landing while the gates run must not be silently reverted (review of PR #279).

    Updater churn inside the generated region and an unrelated edit outside it arrive
    together. The region goes back to its pre-gate bytes; the edit survives untouched
    and is reported by gate 3 rather than overwritten by a stale snapshot.
    """
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED, mode="both")
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    (repo / "notes.md").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "notes.md")

    completed = _run_hook(repo, env)

    assert completed.returncode == 1, completed.stderr
    assert RESTORED in completed.stderr
    assert GATE_3_BLOCKED in completed.stderr
    for path in REPOWISE_OWNED:
        assert (repo / path).read_bytes() == before[
            path
        ] + OUTSIDE_LINE, f"{path}: expected the generated region restored and the concurrent edit kept"


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_waits_for_a_running_updater_before_restoring(tmp_path: Path) -> None:
    """Restoring against a live updater fixes nothing (review of PR #279).

    The updater holds `.repowise/.update.lock`, rewrites the generated region, and
    writes it once more just before releasing. A restore that does not wait lands
    between the two writes, passes gate 3, and hands back a dirty worktree once the
    late write arrives. The hook must wait for the lock, then restore.
    """
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED)
    lock = repo / ".repowise" / ".update.lock"
    _write_fake_interpreter(
        repo,
        """  *run_staged_contract_gate.py*)
    mkdir "$HOOK_TEST_REPO/.repowise/.update.lock"
    mutate
    ( sleep 2
      HOOK_TEST_FROM=bbbbbbb HOOK_TEST_TO=ccccccc mutate
      rmdir "$HOOK_TEST_REPO/.repowise/.update.lock" ) >/dev/null 2>&1 &
    ;;""",
    )
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    (repo / "notes.md").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "notes.md")

    completed = _run_hook(repo, env)

    assert completed.returncode == 0, completed.stderr
    # Judge only once the updater is provably finished: without the wait, the late
    # write has usually not landed yet when the hook returns.
    assert _wait_until_absent(lock, 20.0), "the stand-in updater never released its lock"
    for path in REPOWISE_OWNED:
        assert (repo / path).read_bytes() == before[path], f"{path} was restored before the updater finished"
    assert _git(repo, "status", "--porcelain").stdout == "M  notes.md\n"
    assert "waited" in completed.stderr
    assert RESTORED in completed.stderr


@pytest.mark.integration
@pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required")
def test_pre_commit_does_not_restore_against_an_updater_that_will_not_quiesce(tmp_path: Path) -> None:
    """On quiesce timeout the hook reports the real state instead of racing a live writer."""
    repo, env = _repowise_fixture_repo(tmp_path, REPOWISE_OWNED)
    (repo / ".repowise" / ".update.lock").mkdir()
    env["REPOWISE_QUIESCE_TIMEOUT"] = "1"
    before = {path: (repo / path).read_bytes() for path in REPOWISE_OWNED}
    (repo / "notes.md").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "notes.md")

    completed = _run_hook(repo, env)

    assert completed.returncode == 1, completed.stderr
    assert "skipping the generated-region restore" in completed.stderr
    assert GATE_3_BLOCKED in completed.stderr
    assert RESTORED not in completed.stderr
    for path in REPOWISE_OWNED:
        assert (repo / path).read_bytes() != before[path], f"{path} was restored against a live updater"
