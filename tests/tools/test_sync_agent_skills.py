# Research context: docs/superpowers/plans/2026-05-28-tdl-research-skillset-design.md
# Purpose: Guard the non-destructive file-level mirror step of
#   tools/sync_agent_skills.py: an update must never delete a whole skill
#   directory, must survive a Windows open handle on a destination file
#   (2026-07-02 incident: rmtree half-deleted a mirrored skill before
#   crashing on the locked directory), and must fail recoverably with the
#   affected skill named while other skills still sync.
#   SKL-3 additions: three-way mirror-state detection — MIRROR_EDITED skills
#   are refused instead of silently overwritten.
"""Tests for the dual-tree skill sync tool's mirror step."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from tools import sync_agent_skills as sas


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256_str(text: str) -> str:
    """SHA-256 of text encoded as UTF-8 — matches _write() file bytes."""
    return hashlib.sha256(text.encode()).hexdigest()


def _write_state(state_path: Path, skills: dict[str, dict[str, str]]) -> None:
    """Write a state JSON; each file value is a raw content string to hash."""
    data = {skill: {rel: _sha256_str(content) for rel, content in files.items()} for skill, files in skills.items()}
    state_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture
def trees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A minimal source/destination tree pair with two manifest skills."""
    agents = tmp_path / "agents_skills"
    claude = tmp_path / "claude_skills"
    agents.mkdir()
    claude.mkdir()
    monkeypatch.setattr(sas, "SYNC_SKILLS", {"skill-a", "skill-b"})
    return agents, claude


@pytest.fixture
def trees_with_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Like trees but also returns an (absent) state file path."""
    agents = tmp_path / "agents_skills"
    claude = tmp_path / "claude_skills"
    agents.mkdir()
    claude.mkdir()
    monkeypatch.setattr(sas, "SYNC_SKILLS", {"skill-a", "skill-b"})
    return agents, claude, tmp_path / "skill_sync_state.json"


# ---------------------------------------------------------------------------
# Existing tests (unchanged — state_path omitted → legacy path, no three-way)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# SKL-3 new tests — three-way mirror state
# ---------------------------------------------------------------------------


def test_run_sync_mirror_edited_exits_1_no_overwrite(
    trees_with_state: tuple[Path, Path, Path],
) -> None:
    """dst edited since last sync → MIRROR_EDITED, exit 1, dst untouched."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "src-content")
    _write(claude / "skill-a" / "SKILL.md", "mirror-edit")
    # Recorded state reflects an older version; dst has since been changed.
    _write_state(state_path, {"skill-a": {"SKILL.md": "old-recorded"}})

    exit_code = sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert exit_code == 1
    assert (claude / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "mirror-edit"


def test_run_sync_mirror_edited_names_skill_files_and_remedies(
    trees_with_state: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Error output names the skill, the edited file, and the --force-mirror remedy."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "src")
    _write(claude / "skill-a" / "SKILL.md", "mirror-edit")
    _write_state(state_path, {"skill-a": {"SKILL.md": "old"}})

    sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    err = capsys.readouterr().err
    assert "skill-a" in err
    assert "SKILL.md" in err
    assert "--force-mirror" in err


def test_run_sync_bootstrap_identical_trees_writes_state(
    trees_with_state: tuple[Path, Path, Path],
) -> None:
    """Absent state file + identical trees → writes state, exits 0."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "same")
    _write(claude / "skill-a" / "SKILL.md", "same")
    assert not state_path.exists()

    exit_code = sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert exit_code == 0
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["skill-a"]["SKILL.md"] == _sha256_str("same")


def test_run_sync_bootstrap_divergent_treats_as_mirror_edited(
    trees_with_state: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Absent state file + divergent dst → MIRROR_EDITED (fail safe), exit 1, no overwrite."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "src")
    _write(claude / "skill-a" / "SKILL.md", "diverged")
    assert not state_path.exists()

    exit_code = sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert exit_code == 1
    assert (claude / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "diverged"
    err = capsys.readouterr().err
    assert "skill-a" in err


def test_run_sync_force_mirror_overrides_mirror_edited(
    trees_with_state: tuple[Path, Path, Path],
) -> None:
    """--force-mirror overwrites a MIRROR_EDITED skill, exits 0, refreshes state."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "src-content")
    _write(claude / "skill-a" / "SKILL.md", "mirror-edit")
    _write_state(state_path, {"skill-a": {"SKILL.md": "old-recorded"}})

    exit_code = sas.run_sync(agents, claude, check_only=False, state_path=state_path, force_mirror=True)

    assert exit_code == 0
    assert (claude / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "src-content"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["skill-a"]["SKILL.md"] == _sha256_str("src-content")


def test_run_sync_state_updated_after_successful_mirror(
    trees_with_state: tuple[Path, Path, Path],
) -> None:
    """After a normal UPDATED sync, state records the new dst file hashes."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "new-content")
    _write(claude / "skill-a" / "SKILL.md", "old-content")
    # Recorded = old-content (dst was unchanged since last sync).
    _write_state(state_path, {"skill-a": {"SKILL.md": "old-content"}})

    exit_code = sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert exit_code == 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["skill-a"]["SKILL.md"] == _sha256_str("new-content")


def test_run_sync_check_reports_mirror_edited_distinctly_from_diverged(
    trees_with_state: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """--check labels MIRROR_EDITED skills separately from DIVERGED skills."""
    agents, claude, state_path = trees_with_state
    # skill-a: src updated, dst unchanged → DIVERGED (needs sync, not a mirror edit)
    _write(agents / "skill-a" / "SKILL.md", "new-src")
    _write(claude / "skill-a" / "SKILL.md", "old-content")
    # skill-b: dst was edited independently → MIRROR_EDITED
    _write(agents / "skill-b" / "SKILL.md", "src-b")
    _write(claude / "skill-b" / "SKILL.md", "mirror-edit-b")
    _write_state(
        state_path,
        {
            "skill-a": {"SKILL.md": "old-content"},  # dst unchanged since last sync
            "skill-b": {"SKILL.md": "old-b"},  # dst changed to mirror-edit-b
        },
    )

    exit_code = sas.run_sync(agents, claude, check_only=True, state_path=state_path)

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "DIVERGED" in out and "skill-a" in out
    assert "MIRROR_EDITED" in out and "skill-b" in out


def test_stale_mirror_file_edited_since_sync_is_mirror_edited(
    trees_with_state: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A stale dst file (absent in src) whose hash differs from the recorded
    hash must be classified as MIRROR_EDITED, not silently removed."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "src-content")
    _write(claude / "skill-a" / "SKILL.md", "src-content")
    # Extra file exists only in mirror and has been edited since last sync.
    _write(claude / "skill-a" / "extra.md", "mirror-edited-content")
    _write_state(
        state_path,
        {
            "skill-a": {
                "SKILL.md": "src-content",
                "extra.md": "original-content",  # recorded ≠ current mirror content
            },
        },
    )

    exit_code = sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert exit_code == 1
    # The edited stale file must NOT have been removed.
    assert (claude / "skill-a" / "extra.md").exists()
    assert (claude / "skill-a" / "extra.md").read_text(encoding="utf-8") == "mirror-edited-content"
    err = capsys.readouterr().err
    assert "skill-a" in err
    assert "extra.md" in err


def test_content_hash_is_eol_invariant(tmp_path: Path) -> None:
    """_content_hash must be identical for LF and CRLF encodings of the same
    content — the checkout-independence fix (Principle 5; obs 71, 82, 89, 90)."""
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"line one\nline two\n")
    crlf.write_bytes(b"line one\r\nline two\r\n")
    assert sas._content_hash(lf) == sas._content_hash(crlf)


def test_verify_state_passes_when_recorded_matches(
    trees_with_state: tuple[Path, Path, Path],
) -> None:
    """After a bootstrap sync, verify-state finds every recorded hash matching."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "same")
    _write(claude / "skill-a" / "SKILL.md", "same")
    sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert sas.run_verify_state(claude, state_path) == 0


def test_verify_state_detects_drift_when_trees_identical(
    trees_with_state: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """recorded != actual mirror bytes must FAIL verify-state even though the
    authoring and mirror trees are byte-identical (obs 90 success-branch blind
    spot). This is the state file's negative control — proof it can go RED."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "same")
    _write(claude / "skill-a" / "SKILL.md", "same")
    # State records a WRONG hash for the (byte-identical) mirror file.
    _write_state(state_path, {"skill-a": {"SKILL.md": "stale-recorded-content"}})

    exit_code = sas.run_verify_state(claude, state_path)

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "STATE DRIFT" in err
    assert "skill-a/SKILL.md" in err


def test_verify_state_no_state_file_exits_2(
    trees_with_state: tuple[Path, Path, Path],
) -> None:
    """verify-state fails closed (exit 2) when no state file exists."""
    _agents, claude, state_path = trees_with_state
    assert not state_path.exists()
    assert sas.run_verify_state(claude, state_path) == 2


def test_load_state_malformed_json_exits_2(
    trees_with_state: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed state file must produce exit code 2 via stderr, not a traceback."""
    agents, claude, state_path = trees_with_state
    _write(agents / "skill-a" / "SKILL.md", "content")
    _write(claude / "skill-a" / "SKILL.md", "content")
    state_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        sas.run_sync(agents, claude, check_only=False, state_path=state_path)

    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "malformed state file" in err
