# Research context: docs/superpowers/plans/2026-05-28-tdl-research-skillset-design.md
# Purpose: Guard the non-destructive file-level mirror step of
#   tools/sync_agent_skills.py: an update must never delete a whole skill
#   directory, must survive a Windows open handle on a destination file
#   (2026-07-02 incident: rmtree half-deleted a mirrored skill before
#   crashing on the locked directory), and must fail recoverably with the
#   affected skill named while other skills still sync.
"""Tests for the dual-tree skill sync tool's mirror step."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools import sync_agent_skills as sas


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def trees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A minimal source/destination tree pair with two manifest skills."""
    agents = tmp_path / "agents_skills"
    claude = tmp_path / "claude_skills"
    agents.mkdir()
    claude.mkdir()
    monkeypatch.setattr(sas, "SYNC_SKILLS", {"skill-a", "skill-b"})
    return agents, claude


def test_mirror_skill_creates_missing_destination(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(src / "SKILL.md", "body")
    _write(src / "references" / "notes.md", "notes")

    sas.mirror_skill(src, dst)

    assert (dst / "SKILL.md").read_text(encoding="utf-8") == "body"
    assert (dst / "references" / "notes.md").read_text(encoding="utf-8") == "notes"


def test_mirror_skill_updates_removes_stale_keeps_directory(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(src / "SKILL.md", "new body")
    _write(src / "keep.md", "same")
    _write(dst / "SKILL.md", "old body")
    _write(dst / "keep.md", "same")
    _write(dst / "stale.md", "gone")
    _write(dst / "stale_dir" / "old.md", "gone")

    sas.mirror_skill(src, dst)

    assert (dst / "SKILL.md").read_text(encoding="utf-8") == "new body"
    assert (dst / "keep.md").read_text(encoding="utf-8") == "same"
    assert not (dst / "stale.md").exists()
    assert not (dst / "stale_dir").exists()
    assert dst.is_dir()


def test_run_sync_update_never_deletes_whole_directory(
    trees: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The update path must not reach for rmtree — the 2026-07-02 failure mode."""
    agents, claude = trees
    _write(agents / "skill-a" / "SKILL.md", "new")
    _write(claude / "skill-a" / "SKILL.md", "old")

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("whole-directory delete attempted during mirror")

    monkeypatch.setattr(sas.shutil, "rmtree", _forbidden)

    assert sas.run_sync(agents, claude, check_only=False) == 0
    assert (claude / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "new"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows sharing semantics")
def test_run_sync_survives_open_handle_on_destination_file(
    trees: tuple[Path, Path],
) -> None:
    """An open handle denies delete but allows overwrite — sync must succeed."""
    agents, claude = trees
    _write(agents / "skill-a" / "SKILL.md", "new")
    _write(claude / "skill-a" / "SKILL.md", "old")

    with open(claude / "skill-a" / "SKILL.md", encoding="utf-8"):
        assert sas.run_sync(agents, claude, check_only=False) == 0

    assert (claude / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "new"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows sharing semantics")
def test_run_sync_locked_stale_file_fails_recoverably_and_continues(
    trees: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A stale file that cannot be removed names the skill, exits 1, and does
    not stop the remaining skills from syncing."""
    agents, claude = trees
    _write(agents / "skill-a" / "SKILL.md", "same")
    _write(claude / "skill-a" / "SKILL.md", "same")
    _write(claude / "skill-a" / "stale.md", "locked")
    _write(agents / "skill-b" / "SKILL.md", "new")
    _write(claude / "skill-b" / "SKILL.md", "old")

    with open(claude / "skill-a" / "stale.md", encoding="utf-8"):
        exit_code = sas.run_sync(agents, claude, check_only=False)

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "skill-a" in err
    # Non-stale content untouched, and the failure did not abort the run.
    assert (claude / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "same"
    assert (claude / "skill-b" / "SKILL.md").read_text(encoding="utf-8") == "new"
