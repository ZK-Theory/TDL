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
