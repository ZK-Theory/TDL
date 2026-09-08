"""Hermetic liveness controls for the two D4 hook gates."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / ".claude" / "hooks" / "install-git-hooks.py"
MIRROR_GUARD = ROOT / ".claude" / "hooks" / "mirror-tree-guard.sh"
RECEIPT_WRAP = ROOT / ".claude" / "hooks" / "_receipt-wrap.sh"
SETTINGS = ROOT / ".claude" / "settings.json"
RESEARCH_CONTEXT_CHECK = ROOT / ".claude" / "hooks" / "research-context-check.sh"
RESULTS_VAULT_REMINDER = ROOT / ".claude" / "hooks" / "results-vault-reminder.sh"


def _git_bash() -> str:
    discovered = shutil.which("bash")
    candidates = [
        Path(discovered) if discovered and "system32" not in discovered.lower() else None,
        Path(r"C:\Program Files\Git\bin\bash.exe"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)
    pytest.skip("Git Bash is not available")


def _bash_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    return f"/{resolved[0].lower()}{resolved[2:]}" if resolved[1:3] == ":/" else resolved


def _installer_module():
    spec = importlib.util.spec_from_file_location("install_git_hooks_under_test", INSTALLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _hook_repo(tmp_path: Path, *, configure: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    if configure:
        _git(repo, "config", "core.hooksPath", ".githooks")
    hooks = repo / ".githooks"
    hooks.mkdir()
    for name in ("pre-commit", "pre-push", "commit-msg", "prepare-commit-msg"):
        hook = hooks / name
        hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)
    _git(repo, "add", ".githooks")
    for name in ("pre-commit", "pre-push", "commit-msg", "prepare-commit-msg"):
        _git(repo, "update-index", "--chmod=+x", f".githooks/{name}")
    return repo


def test_install_activates_tracked_hooks_and_real_push_boundary(tmp_path: Path, monkeypatch) -> None:
    module = _installer_module()
    repo = _hook_repo(tmp_path, configure=False)
    (repo / ".githooks" / "pre-push").write_bytes((ROOT / ".githooks" / "pre-push").read_bytes())
    _git(repo, "add", ".githooks/pre-push")
    _git(repo, "update-index", "--chmod=+x", ".githooks/pre-push")
    monkeypatch.setattr(module, "REPO_ROOT", repo)

    assert module.verify(install=True) == 0
    configured = subprocess.run(
        ["git", "config", "--local", "--get", "core.hooksPath"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert configured == ".githooks"

    _git(repo, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "hooks")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    feature = subprocess.run(
        ["git", "push", "origin", "HEAD:refs/heads/topic"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert feature.returncode == 0
    main = subprocess.run(
        ["git", "push", "origin", "HEAD:refs/heads/main"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert main.returncode != 0
    assert "reviewed remote PR seam" in main.stderr


def test_install_git_hooks_missing_directory_and_hook(tmp_path: Path, monkeypatch) -> None:
    module = _installer_module()
    repo = _hook_repo(tmp_path)
    monkeypatch.setattr(module, "REPO_ROOT", repo)
    (repo / ".githooks" / "pre-commit").unlink()
    assert module.verify() == 1
    for path in (repo / ".githooks").iterdir():
        path.unlink()
    (repo / ".githooks").rmdir()
    assert module.verify() == 1


def test_install_git_hooks_rejects_non_executable_index_mode(tmp_path: Path, monkeypatch) -> None:
    module = _installer_module()
    repo = _hook_repo(tmp_path)
    monkeypatch.setattr(module, "REPO_ROOT", repo)
    _git(repo, "update-index", "--chmod=-x", ".githooks/pre-commit")
    assert module.verify() == 1


def test_install_git_hooks_requires_pre_push_main_boundary(tmp_path: Path, monkeypatch) -> None:
    module = _installer_module()
    repo = _hook_repo(tmp_path)
    monkeypatch.setattr(module, "REPO_ROOT", repo)
    (repo / ".githooks" / "pre-push").unlink()
    assert module.verify() == 1


def test_install_git_hooks_resolves_linked_worktree_hooks(tmp_path: Path, monkeypatch) -> None:
    module = _installer_module()
    repo = _hook_repo(tmp_path)
    _git(repo, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "hooks")
    worktree = tmp_path / "linked"
    _git(repo, "worktree", "add", "-q", "-b", "test-linked", str(worktree))
    monkeypatch.setattr(module, "REPO_ROOT", worktree)
    configured, hooks_dir = module.active_hooks_dir()
    assert configured == ".githooks"
    assert hooks_dir == worktree / ".githooks"
    assert module.verify() == 0


def _run_guard(path: str, project: Path, payload: str | None = None) -> subprocess.CompletedProcess[str]:
    body = payload or json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(
        [_git_bash(), _bash_path(MIRROR_GUARD)],
        input=body,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.parametrize(
    "relative",
    [".claude/skills/demo/SKILL.md", r".claude\skills\demo\SKILL.md"],
)
def test_mirror_tree_guard_denies_project_posix_and_windows_paths(tmp_path: Path, relative: str) -> None:
    target = str(tmp_path / relative)
    result = _run_guard(target, tmp_path)
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_mirror_tree_guard_allows_global_and_denies_linked_prefix(tmp_path: Path) -> None:
    outside = tmp_path.parent / ".claude" / "skills" / "global" / "SKILL.md"
    assert json.loads(_run_guard(str(outside), tmp_path).stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    linked = tmp_path / ".apm" / "worktrees" / "x" / ".claude" / "skills" / "s" / "SKILL.md"
    assert json.loads(_run_guard(str(linked), tmp_path).stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_mirror_tree_guard_malformed_input_fails_open_with_receipt(tmp_path: Path) -> None:
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    result = subprocess.run(
        [_git_bash(), _bash_path(RECEIPT_WRAP), _bash_path(MIRROR_GUARD)],
        input="{malformed",
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert "FAILING OPEN" in result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    receipt = (tmp_path / ".claude" / "hooks" / "hook-receipts.log").read_text(encoding="utf-8")
    assert "hook=mirror-tree-guard decision=FAILOPEN" in receipt


# --- PostToolUse advisory-hook receipts -------------------------------------
# obs 2026-09-08-posttooluse-hooks-lack-receipt-wrap: both PostToolUse hooks are
# advisory-only (every path exits 0), so nothing downstream can observe whether
# they ran. The receipt line is their entire liveness signal, which makes these
# the negative controls the observation asks for: a matching fixture Write must
# land `decision=advise` and a non-matching one `decision=silent`, so the log
# distinguishes "ran and found nothing" from "never ran" (both previously
# indistinguishable: zero receipts for either hook across the log's history).


def _run_advisory(hook: Path, project: Path, payload: dict) -> str:
    """Run a PostToolUse hook through the receipt wrapper; return the receipt log."""
    (project / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    result = subprocess.run(
        [_git_bash(), _bash_path(RECEIPT_WRAP), "--advisory", _bash_path(hook)],
        input=json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Write", **payload}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return (project / ".claude" / "hooks" / "hook-receipts.log").read_text(encoding="utf-8")


def test_results_vault_reminder_receipt_records_advise_and_silent(tmp_path: Path) -> None:
    fired = _run_advisory(
        RESULTS_VAULT_REMINDER,
        tmp_path / "fired",
        {"tool_input": {"file_path": "papers/P01/results/w2_permutation_2026-09-08.json"}},
    )
    assert "hook=results-vault-reminder decision=advise" in fired
    assert "file=papers/P01/results/w2_permutation_2026-09-08.json" in fired

    quiet = _run_advisory(
        RESULTS_VAULT_REMINDER,
        tmp_path / "quiet",
        {"tool_input": {"file_path": "docs/notes/summary.md"}},
    )
    assert "hook=results-vault-reminder decision=silent" in quiet


def test_research_context_check_receipt_records_advise_and_silent(tmp_path: Path) -> None:
    headerless = _run_advisory(
        RESEARCH_CONTEXT_CHECK,
        tmp_path / "headerless",
        {"tool_input": {"file_path": "trajectory_tda/scripts/run_probe.py", "content": "import numpy as np\n"}},
    )
    assert "hook=research-context-check decision=advise" in headerless
    assert "file=trajectory_tda/scripts/run_probe.py" in headerless

    with_header = _run_advisory(
        RESEARCH_CONTEXT_CHECK,
        tmp_path / "with_header",
        {
            "tool_input": {
                "file_path": "trajectory_tda/scripts/run_probe.py",
                "content": "# Research context: TDA-Research/03-Papers/P01/_project.md\n# Purpose: probe\n",
            }
        },
    )
    assert "hook=research-context-check decision=silent" in with_header


def test_advisory_mode_flags_a_pretooluse_gate_instead_of_downgrading_it(tmp_path: Path) -> None:
    """A gate wrapped in advisory mode must be flagged, never recorded as mere advice.

    This is the dangerous mis-wiring direction: a real `deny` from a PreToolUse
    guard would otherwise be filed as `advise`, turning the receipt into false
    evidence that the gate allowed the write.
    """
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    subprocess.run(
        [_git_bash(), _bash_path(RECEIPT_WRAP), "--advisory", _bash_path(MIRROR_GUARD)],
        input=json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / ".claude" / "skills" / "demo" / "SKILL.md")},
            }
        ),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    receipt = (tmp_path / ".claude" / "hooks" / "hook-receipts.log").read_text(encoding="utf-8")
    assert "hook=mirror-tree-guard decision=MISWIRED(PreToolUse)" in receipt


def test_settings_wires_both_posttooluse_hooks_through_receipt_wrap() -> None:
    """The receipt only exists if settings.json actually routes through the wrapper.

    Wiring is the thing that regressed; a hook can carry perfect receipt logic
    and still emit nothing because settings.json invokes it directly.
    """
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for group in settings["hooks"]["PostToolUse"]
        for hook in group["hooks"]
        if "research-context-check.sh" in hook["command"] or "results-vault-reminder.sh" in hook["command"]
    ]
    assert len(commands) == 2, commands
    for command in commands:
        assert "_receipt-wrap.sh" in command
        assert "--advisory" in command


def test_receipt_wrap_selftests_pass() -> None:
    """The wrapper's own sanitizer and mode negative controls still hold."""
    result = subprocess.run(
        [_git_bash(), _bash_path(RECEIPT_WRAP), "--selftest"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL:" not in result.stdout
