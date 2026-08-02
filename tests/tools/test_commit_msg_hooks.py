"""Liveness controls for commit-msg / prepare-commit-msg template-injection hardening.

Why (obs 154): a producer supplied an intended ``[PIPELINE] P00: ...`` message
via ``git commit -F``, but the committed subject came back as ``[EXPLORE]
PXX:`` with prepare-commit-msg's own suggestion comments baked into the body.
Root cause, reproduced here: prepare-commit-msg's "commit source" skip-list
did not include ``message`` (git's source value for -m/-F), and a UTF-8 BOM
on the message file defeated its "already has a valid prefix" check even when
it did run — so the hook prepended a ``$PREFIX PXX:`` template above the
original content, and commit-msg accepted the result because it only ever
checked the prefix, never the placeholder subject or the injected comments.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PREPARE_HOOK = REPO_ROOT / ".githooks" / "prepare-commit-msg"
COMMIT_MSG_HOOK = REPO_ROOT / ".githooks" / "commit-msg"


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


def _run_prepare(msg_file: Path, source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_git_bash(), str(PREPARE_HOOK), str(msg_file), source],
        capture_output=True,
        text=True,
        check=False,
    )


def _run_commit_msg(msg_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_git_bash(), str(COMMIT_MSG_HOOK), str(msg_file)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_prepare_commit_msg_skips_message_source_even_with_valid_prefix(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    original = "[PIPELINE] P00: a normal message\n\nbody text\n"
    msg.write_text(original, encoding="utf-8")
    result = _run_prepare(msg, "message")
    assert result.returncode == 0
    assert msg.read_text(encoding="utf-8") == original


def test_prepare_commit_msg_skips_message_source_even_with_bom(tmp_path: Path) -> None:
    """The exact obs 154 trigger: -F/-m source plus a BOM must never be rewritten."""
    msg = tmp_path / "msg.txt"
    original = "\ufeff[PIPELINE] P00: a bom-prefixed message\n\nbody\n"
    msg.write_bytes(original.encode("utf-8"))
    result = _run_prepare(msg, "message")
    assert result.returncode == 0
    assert msg.read_bytes() == original.encode("utf-8")
    assert "Suggested prefix" not in msg.read_text(encoding="utf-8")


def test_prepare_commit_msg_still_injects_template_for_real_editor_commits(tmp_path: Path) -> None:
    """Regression: the fix must not disable the suggestion feature entirely."""
    msg = tmp_path / "msg.txt"
    msg.write_text("no prefix supplied\n", encoding="utf-8")
    result = _run_prepare(msg, "")
    assert result.returncode == 0
    assert "Suggested prefix" in msg.read_text(encoding="utf-8")


def test_commit_msg_rejects_bom(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_bytes("\ufeff[PIPELINE] P00: message\n".encode("utf-8"))
    result = _run_commit_msg(msg)
    assert result.returncode == 1
    assert "BOM" in result.stdout


def test_commit_msg_rejects_template_marker_lines(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text(
        "[EXPLORE] PXX: \n\n# Suggested prefix: [EXPLORE]\n# Vault action: none\n",
        encoding="utf-8",
    )
    result = _run_commit_msg(msg)
    assert result.returncode == 1
    assert "suggestion template" in result.stdout


def test_commit_msg_rejects_pxx_placeholder(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text("[EXPLORE] PXX: \n\nsome body\n", encoding="utf-8")
    result = _run_commit_msg(msg)
    assert result.returncode == 1
    assert "placeholder identifier" in result.stdout


def test_commit_msg_still_accepts_a_normal_valid_message(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text("[PIPELINE] P00: fix something real\n\nbody text here\n", encoding="utf-8")
    result = _run_commit_msg(msg)
    assert result.returncode == 0


def test_commit_msg_still_rejects_missing_prefix(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text("no prefix here\n", encoding="utf-8")
    result = _run_commit_msg(msg)
    assert result.returncode == 1
    assert "Missing TDL commit prefix" in result.stdout


def test_commit_msg_still_allows_merge_commits(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text("Merge branch main\n", encoding="utf-8")
    result = _run_commit_msg(msg)
    assert result.returncode == 0
