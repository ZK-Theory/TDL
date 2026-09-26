# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign A)
# Purpose: Negative and positive controls for the harness hook that refuses a git
# commit whose outcome would be misread: piped away from its exit status, or made on
# a branch that moved since the session last looked.
"""Controls for ``.claude/hooks/commit-state-guard.sh``.

Two observations motivate the guard. ``2026-09-08-blocked-commit-reported-exit-zero``:
a backgrounded ``git commit ... | tail`` was blocked by pre-commit and still reported
exit 0, because a pipeline's status is its last command's. And
``2026-09-08-concurrent-session-branch-switch``: another session moved HEAD in a
shared working directory, and the next commit landed on the wrong branch although the
session had checked its branch earlier. These tests drive the real hook under Git's
bash against real repositories, and fail rather than skip without bash.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "commit-state-guard.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the commit-state guard's controls cannot run, and must not silently skip")
    return found


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr}"
    return completed.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repository on branch ``work`` with a second branch ``other``."""
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q", "-b", "work")
    _git(path, "config", "user.email", "hook-test@example.invalid")
    _git(path, "config", "user.name", "Hook Test")
    (path / "a.txt").write_text("a\n", encoding="utf-8", newline="\n")
    _git(path, "add", "a.txt")
    _git(path, "commit", "-q", "--no-verify", "-m", "seed")
    _git(path, "branch", "other")
    return path


def _run(raw_stdin: str) -> tuple[dict | None, str]:
    """Run the hook on raw stdin; return (parsed stdout JSON or None when silent, stderr)."""
    result = subprocess.run(
        [_bash(), str(HOOK)],
        input=raw_stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return (json.loads(result.stdout) if result.stdout.strip() else None), result.stderr


def _pre(command: str, cwd: Path | str, session: str = "s1", tool: str = "Bash") -> str:
    payload = {
        "session_id": session,
        "cwd": str(cwd),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"command": command},
    }
    output, _ = _run(json.dumps(payload))
    assert output is not None, "PreToolUse must always emit a decision"
    return output["hookSpecificOutput"]["permissionDecision"]


def _post(command: str, cwd: Path, session: str = "s1") -> None:
    payload = {
        "session_id": session,
        "cwd": str(cwd),
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": "", "stderr": ""},
    }
    output, _ = _run(json.dumps(payload))
    assert output is None, "the PostToolUse recorder must stay silent"


PIPED_COMMITS = [
    "git commit -m 'x' 2>&1 | tail -5",
    "git add a.txt && git commit -F msg.txt | tail -30",
    "git -C some/path commit -m x | grep -v IDENTICAL",
    "git commit -m x |& tail",
    # the word pipefail somewhere in the command is not pipefail being on
    "git commit -m pipefail | tail -5",
    "set +o pipefail; git commit -m x | tail",
    "set -o pipefail; set +o pipefail; git commit -m x | tail",
    "git commit -m x | tail; set -o pipefail",
    # wrappers and grouping still run git
    "command git commit -m x | tail -5",
    "env X=1 git commit -m x | tail",
    "(git commit -m x) | tail",
]

NOT_PIPED = [
    "git commit -m 'x'",
    "set -o pipefail; git commit -m x 2>&1 | tail -5",
    "set -euo pipefail; git commit -m x | tail -5",
    "git commit -m 'subject with a | pipe inside the quotes'",
    "git log --oneline | head -3",
    "git commit -m x || echo failed",
]


@pytest.mark.parametrize("command", PIPED_COMMITS)
def test_a_piped_commit_is_refused(command: str, repo: Path) -> None:
    """A pipeline reports its last command's status, so a blocked commit would read as exit 0."""
    assert _pre(command, repo) == "deny"


@pytest.mark.parametrize("command", NOT_PIPED)
def test_unpiped_commits_and_other_pipelines_are_allowed(command: str, repo: Path) -> None:
    """Positive controls: pipefail, a quoted '|', '||', and non-commit pipelines all pass."""
    assert _pre(command, repo) == "allow"


def test_a_branch_moved_by_another_writer_refuses_the_commit(repo: Path) -> None:
    """The session saw ``work``; HEAD moved to ``other`` underneath it; the commit is refused."""
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre("git commit -m x", repo) == "deny"


def test_observing_the_branch_again_admits_the_commit(repo: Path) -> None:
    """After the refusal the session re-reads git state, which records the branch it now knowingly commits to."""
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")
    assert _pre("git commit -m x", repo) == "deny"

    _post("git branch --show-current", repo)

    assert _pre("git commit -m x", repo) == "allow"


def test_the_sessions_own_checkout_is_not_drift(repo: Path) -> None:
    """A branch switch the session made through a tool call is recorded, not treated as foreign."""
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")
    _post("git checkout other", repo)

    assert _pre("git commit -m x", repo) == "allow"


def test_a_checkout_in_the_same_command_as_the_commit_is_not_drift(repo: Path) -> None:
    """``git checkout -b new && git commit`` moves the branch deliberately inside one call."""
    _post("git status", repo)

    assert _pre("git checkout -q -b fresh && git commit -m x", repo) == "allow"


@pytest.mark.parametrize(
    "command",
    [
        "git checkout missing; git commit -m x",
        "git checkout missing || git commit -m x",
        "git checkout -- a.txt && git commit -m x",
    ],
)
def test_a_checkout_that_does_not_gate_the_commit_does_not_exempt_it(command: str, repo: Path) -> None:
    """Only a branch move the commit depends on through ``&&`` explains the new branch."""
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre(command, repo) == "deny"


def test_a_checkout_in_another_repository_does_not_exempt_the_commit(repo: Path, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    _git(elsewhere, "init", "-q", "-b", "topic")
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre(f"git -C {elsewhere.as_posix()} checkout topic && git commit -m x", repo) == "deny"


@pytest.mark.parametrize("command", ["cd missing; git commit -m x", "cd missing || git commit -m x"])
def test_a_directory_change_that_can_fail_still_checks_the_original_repository(command: str, repo: Path) -> None:
    """If the ``cd`` fails the commit still runs here, so this repository's drift must still refuse it."""
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre(command, repo) == "deny"


def test_a_guarded_directory_change_moves_the_check(repo: Path, tmp_path: Path) -> None:
    """``cd elsewhere && git commit`` only commits if the cd succeeded, so the original repository is not checked."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    _git(elsewhere, "init", "-q", "-b", "topic")
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre(f"cd {elsewhere.as_posix()} && git commit -m x", repo) == "allow"


def test_git_dir_and_work_tree_select_the_repository(repo: Path, tmp_path: Path) -> None:
    _post(f"git --git-dir={(repo / '.git').as_posix()} --work-tree {repo.as_posix()} status", tmp_path)
    _git(repo, "checkout", "-q", "other")

    command = f"git --git-dir {(repo / '.git').as_posix()} --work-tree={repo.as_posix()} commit -m x"
    assert _pre(command, tmp_path) == "deny"


def test_powershell_paths_keep_their_backslashes(repo: Path, tmp_path: Path) -> None:
    """``git -C C:\\Users\\...`` in PowerShell must resolve to that directory, not ``C:Users...``."""
    windows = str(repo).replace("/", "\\")
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre(f"git -C {windows} commit -m x", tmp_path, tool="PowerShell") == "deny"


@pytest.mark.parametrize(
    ("command", "tool"),
    [
        ("TDL_ALLOW_MAIN_COMMIT=1 git commit -m x", "Bash"),
        ("export TDL_ALLOW_MAIN_COMMIT=1", "Bash"),
        ("$env:TDL_ALLOW_MAIN_COMMIT = '1'; git commit -m x", "PowerShell"),
    ],
)
def test_an_agent_cannot_set_the_owner_main_commit_override(command: str, tool: str, repo: Path) -> None:
    assert _pre(command, repo, tool=tool) == "deny"


def test_concurrent_recorders_keep_every_sessions_record(repo: Path) -> None:
    """Sessions record in separate files, so concurrent PostToolUse runs cannot drop each other's record."""
    from concurrent.futures import ThreadPoolExecutor

    sessions = [f"c{i}" for i in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda s: _post("git status", repo, session=s), sessions))
    _git(repo, "checkout", "-q", "other")

    assert all(_pre("git commit -m x", repo, session=s) == "deny" for s in sessions)


@pytest.mark.parametrize(
    "command",
    ["git commit --no-verify -m x", "git commit -n -m x", "git commit -anm x", "git push --no-verify origin work"],
)
def test_skipping_the_git_hooks_is_refused(command: str, repo: Path) -> None:
    """--no-verify skips gate -1, so a fresh session could land a commit on main unrefused."""
    assert _pre(command, repo) == "deny"


def test_a_message_that_looks_like_a_flag_is_not_no_verify(repo: Path) -> None:
    assert _pre('git commit -m "-n"', repo) == "allow"


def test_a_backgrounded_commit_is_refused_even_with_pipefail(repo: Path) -> None:
    assert _pre("set -o pipefail; git commit -m x | tail &", repo) == "deny"
    assert _pre("git commit -m x &", repo) == "deny"


def test_env_dash_c_moves_the_commit_target(repo: Path, tmp_path: Path) -> None:
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre(f"env -C {repo.as_posix()} git commit -m x", tmp_path) == "deny"
    assert _pre(f"env --chdir={repo.as_posix()} git commit -m x", tmp_path) == "deny"


def test_a_checkout_that_restores_a_path_is_not_a_branch_move(repo: Path) -> None:
    """``git checkout a.txt`` restores a file (no branch has that name), so it cannot explain a new branch."""
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre("git checkout a.txt && git commit -m x", repo) == "deny"
    assert _pre("git checkout work && git commit -m x", repo) == "allow", "a real branch move still exempts"


def test_two_distinct_detached_heads_are_not_the_same_state(repo: Path) -> None:
    """A session mid-rebase at commit A; another session detaches the shared tree at B."""
    first = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "b.txt").write_text("b\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "--no-verify", "-m", "second")
    second = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-q", "--detach", first)
    _post("git status", repo)
    _git(repo, "checkout", "-q", "--detach", second)

    assert _pre("git commit -m x", repo) == "deny"


def test_sessions_are_isolated(repo: Path) -> None:
    """One session's observation neither refuses nor admits another session's commit."""
    _post("git status", repo, session="s1")
    _git(repo, "checkout", "-q", "other")

    assert _pre("git commit -m x", repo, session="s2") == "allow"
    assert _pre("git commit -m x", repo, session="s1") == "deny"


def test_the_commit_target_follows_git_dash_c(repo: Path, tmp_path: Path) -> None:
    """The branch checked is the one ``git -C`` commits in, not the tool call's cwd."""
    _post(f"git -C {repo.as_posix()} status", tmp_path)
    _git(repo, "checkout", "-q", "other")

    assert _pre(f"git -C {repo.as_posix()} commit -m x", tmp_path) == "deny"


def test_no_prior_observation_admits_and_records(repo: Path) -> None:
    """A first commit with no record is allowed; the guard cannot know an earlier expectation."""
    assert _pre("git commit -m x", repo, session="fresh") == "allow"


def test_non_commit_commands_are_allowed(repo: Path) -> None:
    _post("git status", repo)
    _git(repo, "checkout", "-q", "other")

    assert _pre("git push origin other", repo) == "allow"
    assert _pre("ls", repo) == "allow"


def test_a_guard_error_fails_open_visibly() -> None:
    """Malformed input still lets the command run, with the marker _receipt-wrap records."""
    output, stderr = _run('{"tool_name": "Bash", "tool_input": {"command": "git commit -m x"')
    assert output is not None
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "FAILING OPEN" in stderr


def test_the_guard_is_wired_before_and_after_both_shell_tools() -> None:
    """A guard that exists but is not wired guards nothing; the recorder must be advisory-wrapped."""
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
    for event, advisory in (("PreToolUse", False), ("PostToolUse", True)):
        wired = [
            group
            for group in hooks[event]
            for hook in group["hooks"]
            if "commit-state-guard.sh" in hook["command"] and "_receipt-wrap.sh" in hook["command"]
        ]
        assert len(wired) == 1, f"commit-state-guard.sh must be wired exactly once for {event}"
        assert set(wired[0]["matcher"].split("|")) >= {"Bash", "PowerShell"}
        command = next(h["command"] for h in wired[0]["hooks"] if "commit-state-guard.sh" in h["command"])
        assert ("--advisory" in command) is advisory
