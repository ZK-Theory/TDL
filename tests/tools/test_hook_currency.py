# Research context: docs/plans/strategy/system-review-2026-09-29-decision-report.md (Campaign S)
# Purpose: Negative and positive controls for the hook-currency check, which tells a session or a
# dispatch that its checkout is running hooks older than the merged ones.
"""Controls for ``tools/hook_currency.py`` and its two call sites.

Obs 2026-10-02-merged-gates-not-live-in-the-main-checkout: on 2026-10-02 the main checkout sat 13
commits behind ``origin/main``. Git resolves ``core.hooksPath=.githooks`` inside the checkout, and the
harness loads ``.claude/settings.json`` from it, so both ran the pre-merge hooks while every report
said the hooks were live. ``install-git-hooks.py`` and the dispatch ``hook-gate`` check that a hook is
wired, not that it is the merged one. These tests build real repositories (a bare remote, a clone that
publishes, and the checkout under test) and watch the check warn when a hook-touching commit is
missing and stay quiet when only other commits are.

The check reads the last-fetched remote ref and never fetches, so a remote that moved since the last
``git fetch`` is invisible to it. ``test_a_remote_that_has_not_been_fetched_is_not_seen`` records that
limit as a control instead of leaving it as a claim.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from shared import manager_dispatch_check as gate
from tools import hook_currency

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "tools" / "hook_currency.py"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

HOOK_FILES = [
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".claude/hooks/guard.sh",
    ".claude/hooks/nested/deep.py",
    ".claude/settings.json",
]
# Near misses: none of these is a file git or the harness reads as a hook.
NOT_HOOK_FILES = [
    "docs/notes.md",
    "tools/helper.py",
    ".claude/settings.json.bak",
    ".claude/rules/python.md",
    ".claude/hooks-notes.md",
    "docs/.githooks/note.md",
]
SEED = {
    ".githooks/pre-commit": "#!/bin/sh\nexit 0\n",
    ".githooks/commit-msg": "#!/bin/sh\nexit 0\n",
    ".claude/hooks/guard.sh": "#!/bin/bash\nexit 0\n",
    ".claude/hooks/nested/deep.py": "print('hook')\n",
    ".claude/settings.json": "{}\n",
    "docs/notes.md": "notes\n",
}


def _git(cwd: Path, *args: str) -> str:
    """Run git with a fixed identity so no global configuration decides the outcome."""
    proc = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    """Write ``files`` into ``repo``, commit them, and return the new commit's full sha."""
    for relative, text in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@dataclass
class Rig:
    """A bare remote, a clone that publishes to it, and the checkout under test."""

    bare: Path
    maker: Path
    checkout: Path
    branch: str

    def publish(self, files: dict[str, str], message: str = "upstream change") -> str:
        """Commit ``files`` on the remote's integration branch and return the commit sha."""
        sha = _commit(self.maker, files, message)
        _git(self.maker, "push", "-q", "origin", f"HEAD:{self.branch}")
        return sha

    def fetch(self) -> None:
        """Update the checkout's remote-tracking refs, as the owner's own fetch would."""
        _git(self.checkout, "fetch", "-q", "origin")


def _rig(tmp_path: Path, branch: str = "main") -> Rig:
    bare = tmp_path / "remote.git"
    maker = tmp_path / "maker"
    checkout = tmp_path / "checkout"
    _git(tmp_path, "init", "-q", "--bare", "-b", branch, str(bare))
    _git(tmp_path, "clone", "-q", str(bare), str(maker))
    _git(maker, "checkout", "-q", "-B", branch)
    _commit(maker, SEED, "seed")
    _git(maker, "push", "-q", "origin", f"HEAD:{branch}")
    _git(tmp_path, "clone", "-q", str(bare), str(checkout))
    return Rig(bare=bare, maker=maker, checkout=checkout, branch=branch)


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    return _rig(tmp_path)


# --- the negative control: a hook-touching commit the checkout lacks must warn ---------------


@pytest.mark.parametrize("path", HOOK_FILES)
def test_a_hook_touching_commit_one_behind_warns(rig: Rig, path: str) -> None:
    """The watched failure: one missing commit that changes one hook file is named, counted and refused."""
    sha = rig.publish({path: "changed\n"})
    rig.fetch()

    result = hook_currency.check(rig.checkout)

    assert result.status == "STALE"
    assert result.behind == 1
    assert len(result.hook_commits) == 1 and sha.startswith(result.hook_commits[0])
    assert result.files == (path,)
    assert result.line.startswith("hook-currency: WARNING")
    assert "1 commit behind origin/main" in result.line
    assert path in result.line
    assert "last fetch" in result.line


def test_several_commits_are_counted_and_every_touched_hook_file_is_named(rig: Rig) -> None:
    """Of four missing commits, the two that touch hook files are counted and their files all named."""
    rig.publish({"docs/notes.md": "first\n"}, "docs")
    rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"}, "tighten the gate")
    rig.publish({".claude/settings.json": '{"a": 1}\n', ".claude/hooks/guard.sh": "#!/bin/bash\nexit 2\n"}, "rewire")
    rig.publish({"docs/notes.md": "second\n"}, "docs again")
    rig.fetch()

    result = hook_currency.check(rig.checkout)

    assert result.status == "STALE"
    assert result.behind == 4
    assert len(result.hook_commits) == 2
    assert result.files == (".claude/hooks/guard.sh", ".claude/settings.json", ".githooks/pre-commit")
    assert "4 commits behind origin/main" in result.line
    assert "2 of them" in result.line
    for name in result.files:
        assert name in result.line


# --- the quiet controls: nothing the hooks do not read may raise the warning -----------------


@pytest.mark.parametrize("path", NOT_HOOK_FILES)
def test_a_commit_that_touches_no_hook_file_stays_quiet(rig: Rig, path: str) -> None:
    """Positive control on scope: behind by a non-hook commit is reported as behind, never as a warning."""
    rig.publish({path: "changed\n"})
    rig.fetch()

    result = hook_currency.check(rig.checkout)

    assert result.status == "CURRENT"
    assert result.behind == 1
    assert result.hook_commits == () and result.files == ()
    assert result.line.startswith("hook-currency: OK")
    assert "WARNING" not in result.line
    assert "none touch hook files" in result.line


def test_a_checkout_that_has_the_hook_commit_is_current(rig: Rig) -> None:
    """Once the checkout has pulled the hook commit it is the hook tree in force, and nothing warns."""
    sha = rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})
    _git(rig.checkout, "pull", "-q", "--ff-only")

    result = hook_currency.check(rig.checkout)

    assert result.status == "CURRENT"
    assert result.behind == 0
    assert sha.startswith(result.in_force)
    assert result.line.startswith("hook-currency: OK")
    assert result.in_force in result.line


def test_the_hook_tree_in_force_is_the_last_hook_commit_not_head(rig: Rig) -> None:
    """A later docs commit moves HEAD but not the hook tree, so the line must not name HEAD for it."""
    hook_sha = rig.publish({".claude/hooks/guard.sh": "#!/bin/bash\nexit 3\n"}, "hook change")
    docs_sha = rig.publish({"docs/notes.md": "later\n"}, "docs change")
    _git(rig.checkout, "pull", "-q", "--ff-only")

    result = hook_currency.check(rig.checkout)

    assert hook_sha.startswith(result.in_force)
    assert not docs_sha.startswith(result.in_force)
    assert docs_sha.startswith(result.head)


def test_a_remote_that_has_not_been_fetched_is_not_seen(rig: Rig) -> None:
    """The stated limit: the check reads the last-fetched ref and never fetches, so it cannot see ahead.

    SessionStart must not wait on the network, so a checkout whose remote moved after its last fetch
    reads as current until something fetches. After the fetch the same checkout must warn.
    """
    rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})

    assert hook_currency.check(rig.checkout).status == "CURRENT"

    rig.fetch()

    assert hook_currency.check(rig.checkout).status == "STALE"


def test_uncommitted_edits_to_hook_files_are_reported_with_the_commit_in_force(rig: Rig) -> None:
    """The hook tree in force is the working tree, so an uncommitted edit is part of what runs."""
    (rig.checkout / ".githooks" / "pre-commit").write_text("#!/bin/sh\nexit 9\n", encoding="utf-8", newline="\n")
    (rig.checkout / "docs" / "scratch.md").parent.mkdir(exist_ok=True)
    (rig.checkout / "docs" / "scratch.md").write_text("not a hook\n", encoding="utf-8")

    result = hook_currency.check(rig.checkout)

    assert result.status == "CURRENT"
    assert result.dirty == (".githooks/pre-commit",)
    assert "uncommitted" in result.line
    assert ".githooks/pre-commit" in result.line


# --- repository shapes the check must survive -------------------------------------------------


def test_a_repository_with_no_remote_is_unverified_not_an_error(tmp_path: Path) -> None:
    repo = tmp_path / "solo"
    repo.mkdir()
    _git(repo, "init", "-q")
    sha = _commit(repo, SEED, "seed")

    result = hook_currency.check(repo)

    assert result.status == "UNVERIFIED"
    assert result.line.startswith("hook-currency: UNVERIFIED")
    assert "no origin/main or upstream" in result.line
    assert sha.startswith(result.in_force)


def test_a_repository_with_no_commits_is_unverified_not_an_error(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo, "init", "-q")

    result = hook_currency.check(repo)

    assert result.status == "UNVERIFIED"
    assert "no commits" in result.line


def test_a_directory_that_is_not_a_repository_is_unverified_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()

    result = hook_currency.check(plain)

    assert result.status == "UNVERIFIED"
    assert "not inside a git work tree" in result.line


def test_a_detached_head_is_still_measured_against_the_remote(rig: Rig) -> None:
    _git(rig.checkout, "checkout", "-q", "--detach")
    rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})
    rig.fetch()

    result = hook_currency.check(rig.checkout)

    assert result.status == "STALE"
    assert "detached HEAD" in result.line


def test_a_linked_worktree_is_judged_by_its_own_head_not_the_main_checkout(rig: Rig, tmp_path: Path) -> None:
    """A worktree cut from an old commit runs old hooks even when the main checkout is up to date."""
    old = _git(rig.checkout, "rev-parse", "HEAD")
    rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})
    rig.fetch()
    worktree = tmp_path / "linked"
    _git(rig.checkout, "worktree", "add", "-q", "--detach", str(worktree), old)
    _git(rig.checkout, "merge", "-q", "--ff-only", "origin/main")

    assert hook_currency.check(rig.checkout).status == "CURRENT"
    stale = hook_currency.check(worktree)

    assert stale.status == "STALE"
    assert stale.files == (".githooks/pre-commit",)
    assert old.startswith(stale.head)


def test_a_check_started_in_a_subdirectory_reads_the_whole_checkout(rig: Rig) -> None:
    rig.publish({".claude/settings.json": '{"b": 2}\n'})
    rig.fetch()
    (rig.checkout / "docs").mkdir(exist_ok=True)

    result = hook_currency.check(rig.checkout / "docs")

    assert result.status == "STALE"
    assert result.files == (".claude/settings.json",)


def test_a_feature_branch_is_measured_against_main_not_against_its_own_remote_branch(rig: Rig) -> None:
    """A branch pushed with ``-u`` tracks itself; comparing with that would read as current forever."""
    _git(rig.checkout, "checkout", "-q", "-b", "pipe/feature")
    _git(rig.checkout, "push", "-q", "-u", "origin", "pipe/feature")
    rig.publish({".claude/hooks/guard.sh": "#!/bin/bash\nexit 4\n"})
    rig.fetch()

    result = hook_currency.check(rig.checkout)

    assert result.status == "STALE"
    assert result.ref == "origin/main"


def test_the_upstream_is_the_reference_when_there_is_no_origin_main(tmp_path: Path) -> None:
    """A remote whose integration branch is not called main is still measured, through ``@{upstream}``."""
    trunk = _rig(tmp_path, branch="trunk")
    trunk.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})
    trunk.fetch()

    result = hook_currency.check(trunk.checkout)

    assert result.status == "STALE"
    assert result.ref == "origin/trunk"


def test_an_explicit_reference_overrides_the_default_and_a_missing_one_is_unverified(rig: Rig) -> None:
    _git(rig.maker, "push", "-q", "origin", "HEAD:refs/heads/release")
    rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})
    _git(rig.maker, "push", "-q", "origin", "HEAD:refs/heads/release")
    rig.fetch()

    explicit = hook_currency.check(rig.checkout, ref="origin/release")
    missing = hook_currency.check(rig.checkout, ref="origin/nonexistent")

    assert explicit.status == "STALE" and explicit.ref == "origin/release"
    assert missing.status == "UNVERIFIED"
    assert "origin/nonexistent" in missing.line


# --- the command line: the SessionStart line and the exit codes -------------------------------


def _stale(rig: Rig) -> None:
    rig.publish({".githooks/pre-commit": "#!/bin/sh\nexit 1\n"})
    rig.fetch()


def test_session_start_prints_exactly_one_line_and_exits_zero_even_when_stale(
    rig: Rig, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(rig)

    code = hook_currency.main(["--session-start", "--repo", str(rig.checkout)])

    lines = capsys.readouterr().out.splitlines()
    assert code == 0
    assert len(lines) == 1 and lines[0].startswith("hook-currency: WARNING")


def test_session_start_prints_the_hook_tree_in_force_on_a_current_checkout(
    rig: Rig, capsys: pytest.CaptureFixture[str]
) -> None:
    """Positive control: every session start leaves one line saying which hook commit is in force."""
    code = hook_currency.main(["--session-start", "--repo", str(rig.checkout)])

    lines = capsys.readouterr().out.splitlines()
    in_force = _git(
        rig.checkout, "log", "-1", "--format=%h", "--", ".githooks", ".claude/hooks", ".claude/settings.json"
    )
    assert code == 0
    assert len(lines) == 1 and lines[0].startswith("hook-currency: OK")
    assert in_force in lines[0]


def test_the_default_mode_exits_one_when_stale_and_zero_when_current(
    rig: Rig, capsys: pytest.CaptureFixture[str]
) -> None:
    assert hook_currency.main(["--repo", str(rig.checkout)]) == 0
    _stale(rig)

    assert hook_currency.main(["--repo", str(rig.checkout)]) == 1
    assert "WARNING" in capsys.readouterr().out


def test_the_repository_defaults_to_the_harness_project_directory(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(rig)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(rig.checkout))
    monkeypatch.chdir(rig.maker)

    hook_currency.main(["--session-start"])

    assert "WARNING" in capsys.readouterr().out


def test_session_start_reports_a_failure_of_the_check_itself_and_still_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A check that dies silently would read as 'current' forever; it must say it could not check."""

    def explode(*_args: object, **_kwargs: object) -> hook_currency.Currency:
        raise RuntimeError("boom")

    monkeypatch.setattr(hook_currency, "check", explode)

    code = hook_currency.main(["--session-start", "--repo", "."])

    lines = capsys.readouterr().out.splitlines()
    assert code == 0
    assert len(lines) == 1
    assert lines[0].startswith("hook-currency: UNVERIFIED") and "RuntimeError: boom" in lines[0]


# --- wiring: the line must reach a session through the settings the harness reads --------------


def _session_start_commands() -> list[str]:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    return [hook["command"] for group in settings["hooks"]["SessionStart"] for hook in group["hooks"]]


def test_settings_runs_the_check_at_session_start_beside_handoff_surface() -> None:
    commands = _session_start_commands()
    assert any("handoff-surface.sh" in command for command in commands)
    wired = [command for command in commands if "tools/hook_currency.py" in command]
    assert len(wired) == 1, "tools/hook_currency.py must be wired exactly once at SessionStart"
    assert "--session-start" in wired[0]
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    timeouts = [hook["timeout"] for group in groups for hook in group["hooks"] if "hook_currency" in hook["command"]]
    assert timeouts and all(timeout <= 10 for timeout in timeouts)


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the SessionStart wiring control cannot run, and must not silently skip")
    return found


def _run_wired_command(project: Path) -> subprocess.CompletedProcess[str]:
    """Run the SessionStart command exactly as settings.json spells it, with ``project`` as the project dir."""
    (project / "tools").mkdir(exist_ok=True)
    shutil.copy2(MODULE, project / "tools" / "hook_currency.py")
    command = next(command for command in _session_start_commands() if "hook_currency" in command)
    return subprocess.run(
        [_bash(), "-c", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
        timeout=60,
        check=False,
    )


def test_the_wired_command_prints_the_in_force_line_on_a_current_checkout(rig: Rig) -> None:
    """Positive control through the real wiring: the command string, ``$CLAUDE_PROJECT_DIR`` and ``python``."""
    result = _run_wired_command(rig.checkout)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert len(lines) == 1 and lines[0].startswith("hook-currency: OK"), result.stdout


def test_the_wired_command_warns_on_a_checkout_missing_a_hook_commit(rig: Rig) -> None:
    """Negative control through the real wiring: a stale checkout is told so at session start."""
    _stale(rig)

    result = _run_wired_command(rig.checkout)

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 1 and lines[0].startswith("hook-currency: WARNING"), result.stdout
    assert ".githooks/pre-commit" in lines[0]


# --- the dispatch gate: manager_dispatch_check's hook-currency check ---------------------------


def test_the_gate_fails_a_workspace_missing_a_hook_commit_and_says_how_to_proceed(rig: Rig) -> None:
    _stale(rig)

    check = gate.check_hook_currency(rig.checkout, None)

    assert check.name == "hook-currency"
    assert check.ok is False
    assert ".githooks/pre-commit" in check.detail
    assert "--allow-stale-hooks" in check.detail


def test_the_gate_records_a_stated_waiver_as_an_advisory_and_refuses_a_blank_one(rig: Rig) -> None:
    _stale(rig)

    waived = gate.check_hook_currency(rig.checkout, "stacked on an unmerged prerequisite")
    blank = gate.check_hook_currency(rig.checkout, "   ")

    assert waived.ok is True and waived.advisory is True
    assert "stacked on an unmerged prerequisite" in waived.detail
    assert blank.ok is False


def test_the_gate_passes_a_current_workspace_without_an_advisory(rig: Rig) -> None:
    check = gate.check_hook_currency(rig.checkout, None)

    assert check.ok is True and check.advisory is False
    assert check.detail.startswith("OK - ")


def test_the_gate_cannot_verify_without_a_remote_and_says_so_without_failing(tmp_path: Path) -> None:
    repo = tmp_path / "solo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _commit(repo, SEED, "seed")

    check = gate.check_hook_currency(repo, None)

    assert check.ok is True and check.advisory is True
    assert "UNVERIFIED" in check.detail


def test_main_runs_the_currency_check_and_a_stale_workspace_fails_the_dispatch(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A check that exists but is not called from main() guards nothing at the dispatch seam."""
    monkeypatch.setattr(gate, "check_contracts", lambda _workspace: gate.Check("contracts", True, "patched"))
    monkeypatch.setattr(gate, "check_hook_gate", lambda _workspace: gate.Check("hook-gate", True, "patched"))
    monkeypatch.setattr(gate, "check_state_manifest", lambda *_args: [gate.Check("state-manifest", True, "patched")])
    monkeypatch.chdir(rig.checkout)
    argv = [
        "--agent",
        "a",
        "--branch",
        "main",
        "--expected-base",
        "HEAD",
        "--mode",
        "sequential",
        "--state-manifest",
        "unused.yaml",
        "--no-brief",
        "test",
    ]

    assert gate.main(argv) == 0
    assert "hook-currency" in capsys.readouterr().out
    _stale(rig)

    assert gate.main(argv) == 1
    assert "[ ] **hook-currency**" in capsys.readouterr().out
    assert gate.main([*argv, "--allow-stale-hooks", "stacked on an unmerged prerequisite"]) == 0
