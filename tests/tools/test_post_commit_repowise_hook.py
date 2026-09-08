"""Guard-branch controls for the tracked repowise auto-sync post-commit hook.

Obs 2026-08-11-post-commit-repowise-guard-untested. `.githooks/post-commit` fires
`repowise update` into the background after every commit and carries three
purpose-built protective branches — no-op when `.repowise/` is absent, no-op when
`.repowise` is a symlink (a hostile-clone redirect), and an atomic `mkdir` lock so
concurrent commits cannot spawn overlapping updaters. `.repowise/.update.log`
shows the happy path runs, but the happy path is not evidence for branches that
exist specifically to handle the uncommon case: each needed its own watched
failure, in the same shape `tests/tools/test_system_review_hook_gates.py` already
gives the sibling `mirror-tree-guard.sh`.

Each test drives the tracked hook script directly against a disposable repo with a
stand-in updater on PATH, so "the updater did not run" is an observed fact rather
than an inference from the script's text.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".githooks" / "post-commit"

# How long to let the backgrounded updater appear. The hook spawns it within
# milliseconds; the positive control asserts the generous bound is real, and the
# guard tests then wait the shorter one for something that must never appear.
UPDATER_APPEARS_WITHIN = 20.0
UPDATER_ABSENT_FOR = 3.0


def _git_bash() -> Path | None:
    # Same resolution as tests/tools/test_pre_commit_hook.py: a Git-for-Windows
    # install has several git.exe copies at different depths from the shared
    # bin/bash.exe, so try the discovered git's sibling bin/ first.
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


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr}"
    return completed


@pytest.fixture
def hook_repo(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    """A disposable committed repo, a stand-in updater on PATH, and its marker file.

    Both `repowise` and `uv` are shadowed: the hook accepts either as an executor,
    so a test that stubbed only one could watch the wrong branch run for real.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "hook-test@example.invalid")
    _git(repo, "config", "user.name", "Hook Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")

    marker = tmp_path / "updater-invocations.log"
    fake_bin = tmp_path / "fake-bin"
    for name in ("repowise", "uv"):
        _write_executable(
            fake_bin / name,
            f"""#!/bin/sh
printf '{name} %s\\n' "$*" >> "$HOOK_TEST_MARKER"
exit 0
""",
        )
    bash_env = tmp_path / "bash-env"
    _write_executable(bash_env, 'export PATH="$HOOK_TEST_FAKE_BIN:$PATH"\n')

    env = os.environ.copy()
    env.update(
        {
            "HOOK_TEST_MARKER": _msys_path(marker),
            "HOOK_TEST_FAKE_BIN": _msys_path(fake_bin),
            "BASH_ENV": _msys_path(bash_env),
        }
    )
    return repo, env, marker


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


def _wait_until_present(path: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return path.exists()


def _assert_absent_throughout(path: Path, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        assert not path.exists(), f"{path.name} appeared: the updater ran when it must not have"
        time.sleep(0.05)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(_git_bash() is None, reason="Git Bash is required"),
]


def test_updater_runs_once_when_the_state_dir_is_a_real_directory(
    hook_repo: tuple[Path, dict[str, str], Path],
) -> None:
    """Positive control. Without it the three guard assertions below are vacuous.

    Also pins the coalescing loop: HEAD does not move during the run, so the
    updater is invoked exactly once, not once per iteration.
    """
    repo, env, marker = hook_repo
    (repo / ".repowise").mkdir()

    completed = _run_hook(repo, env)
    assert completed.returncode == 0, completed.stderr

    assert _wait_until_present(marker, UPDATER_APPEARS_WITHIN), "the updater never ran"
    # The lock holder re-reads HEAD until it stops moving; a static HEAD is one pass.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        time.sleep(0.1)
    assert marker.read_text(encoding="utf-8").splitlines() == ["repowise update"]

    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    queued = json.loads((repo / ".repowise" / ".update.queued").read_text(encoding="utf-8"))
    assert queued["target_commit"] == head
    assert "post-commit hook fired" in (repo / ".repowise" / ".update.log").read_text(encoding="utf-8")


def test_missing_state_dir_is_a_true_no_op(
    hook_repo: tuple[Path, dict[str, str], Path],
) -> None:
    """Guard 1: no `.repowise/` — exit 0, no updater, and no state files conjured.

    The updater is resolved only after this guard, so an unconfigured clone must
    not be handed `.update.queued`/`.update.log` it will never act on.

    Watched failure, recorded because it is not the obvious one: deleting the `-d`
    guard alone does NOT make this test fail. The lock's `mkdir "$LOCK"` has no
    `-p`, so with no `.repowise/` to hold it the lock cannot be taken and the
    updater is blocked one line further down. This test therefore pins the
    contract ("an unconfigured checkout gets nothing"), which is defended by both
    lines; it fails when the `-d` guard and the lock's non-recursive `mkdir` are
    disarmed together. Anyone adding `-p` to that `mkdir` for convenience removes
    the second line and must keep the first.
    """
    repo, env, marker = hook_repo
    assert not (repo / ".repowise").exists()

    completed = _run_hook(repo, env)
    assert completed.returncode == 0, completed.stderr

    _assert_absent_throughout(marker, UPDATER_ABSENT_FOR)
    assert not (repo / ".repowise").exists(), "the hook created a state dir it was told to skip"


def test_symlinked_state_dir_is_refused_and_not_followed(
    hook_repo: tuple[Path, dict[str, str], Path],
) -> None:
    """Guard 2: `.repowise` as a symlink is the hostile-clone redirect the hook names.

    Asserts both halves: the updater does not run, and nothing is written through
    the link into its target — a redirect that lands writes outside the checkout is
    the failure this branch exists to prevent.
    """
    repo, env, marker = hook_repo
    outside = repo.parent / "outside-the-checkout"
    outside.mkdir()
    try:
        os.symlink(outside, repo / ".repowise", target_is_directory=True)
    except OSError as exc:  # pragma: no cover - depends on the host's symlink privilege
        pytest.skip(f"cannot create a directory symlink here: {exc}")

    completed = _run_hook(repo, env)
    assert completed.returncode == 0, completed.stderr

    _assert_absent_throughout(marker, UPDATER_ABSENT_FOR)
    assert list(outside.iterdir()) == [], "the hook wrote through the symlink into its target"


def test_a_held_lock_blocks_a_second_updater_without_dropping_the_request(
    hook_repo: tuple[Path, dict[str, str], Path],
) -> None:
    """Guard 3: the atomic `mkdir` lock, plus the queue semantics behind it.

    A commit that cannot take the lock must not spawn an overlapping updater — but
    it must also not silently drop its request: `.update.queued` records the HEAD it
    wanted indexed, and the log records that the hook fired, so the lock holder's
    re-read of HEAD is the mechanism that absorbs the work rather than a lost write.
    A fresh lock is also not eligible for the 30-minute stale reclaim.
    """
    repo, env, marker = hook_repo
    state = repo / ".repowise"
    state.mkdir()
    lock = state / ".update.lock"
    lock.mkdir()

    completed = _run_hook(repo, env)
    assert completed.returncode == 0, completed.stderr

    _assert_absent_throughout(marker, UPDATER_ABSENT_FOR)
    assert lock.is_dir(), "a fresh lock was reclaimed as stale"

    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    queued = json.loads((state / ".update.queued").read_text(encoding="utf-8"))
    assert queued["target_commit"] == head, "the lock-blocked request was dropped, not queued"
    assert "post-commit hook fired" in (state / ".update.log").read_text(encoding="utf-8")
