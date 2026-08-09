"""Negative and positive controls for the local-main integration boundary."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".githooks" / "pre-push"


def _git_bash() -> str:
    candidates = [
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(shutil.which("bash") or ""),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    pytest.skip("Git Bash is unavailable")


def _run(update: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_git_bash(), str(HOOK), "origin", "https://example.invalid/repo.git"],
        input=update,
        capture_output=True,
        text=True,
        check=False,
    )


def test_pre_push_rejects_direct_main_update() -> None:
    result = _run("refs/heads/main aaa refs/heads/main bbb\n")
    assert result.returncode == 1
    assert "reviewed remote PR seam" in result.stderr


def test_pre_push_allows_feature_branch_update() -> None:
    result = _run("refs/heads/topic aaa refs/heads/topic bbb\n")
    assert result.returncode == 0
