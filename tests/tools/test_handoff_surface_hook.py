# Research context: TDA-Research/00-Meta/Discovery/_backlog.md
# Purpose: Negative controls for the SessionStart handoff-surface hook, so the
# gate cannot pass silently while surfacing nothing (observation 135).

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "handoff-surface.sh"


def _bash() -> str | None:
    """Resolve a real Bash, not Windows' WSL launcher stub.

    ``shutil.which("bash")`` finds ``C:\\Windows\\System32\\bash.exe`` first on
    this platform, which is the Store/WSL shim and exits nonzero with a
    UTF-16 error when no distribution is installed. Prefer Git's bundled Bash,
    which is what the hooks actually run under.
    """
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if found and "system32" in found.lower():
        return None
    return found


BASH = _bash()

pytestmark = pytest.mark.skipif(BASH is None, reason="no non-WSL bash available")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs" / "plans" / "x" / "handoffs").mkdir(parents=True)
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def _write_handoff(repo: Path, name: str, title: str, audience: str | None) -> None:
    body = f"# {title}\n\n**Created:** 2026-07-28\n"
    if audience is not None:
        body += f"**For:** {audience}\n"
    (repo / "docs" / "plans" / "x" / "handoffs" / name).write_text(body, encoding="utf-8")


def _run(repo: Path, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    import os

    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo), **env_overrides}
    return subprocess.run(
        [BASH, str(HOOK)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_surfaces_a_recent_handoff_with_its_audience(tmp_path):
    """Positive: the audience line is the payload, so it must be shown."""
    repo = _repo(tmp_path)
    _write_handoff(repo, "26-briefing.md", "Suite is red", "the agent working the N+1 repair")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add handoff")

    result = _run(repo)

    assert result.returncode == 0
    assert "26-briefing.md" in result.stdout
    assert "Suite is red" in result.stdout
    assert "For: the agent working the N+1 repair" in result.stdout


@pytest.mark.parametrize("days", ["0"])
def test_zero_day_window_surfaces_nothing(tmp_path, days):
    repo = _repo(tmp_path)
    _write_handoff(repo, "26-briefing.md", "Suite is red", "somebody")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add handoff")

    # A commit made "now" sits inside any window, so backdate it to prove the
    # cutoff is real. The hook reads committer date (%ct) -- when the handoff
    # landed -- so --date alone, which sets author date, would not move it.
    import os

    subprocess.run(
        ["git", "commit", "-q", "--amend", "--no-edit", "--date", "2020-01-01T00:00:00"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_COMMITTER_DATE": "2020-01-01T00:00:00"},
    )

    result = _run(repo, HANDOFF_SURFACE_DAYS=days)

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_no_handoffs_directory_is_silent(tmp_path):
    """A repository without handoffs must produce no noise at all."""
    repo = tmp_path / "bare"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))

    result = _run(repo)

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_handoff_without_audience_is_listed_without_a_for_line(tmp_path):
    """Missing audience must degrade, not crash or emit an empty 'For:'."""
    repo = _repo(tmp_path)
    _write_handoff(repo, "27-no-audience.md", "Implementation brief", None)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add handoff")

    result = _run(repo)

    assert result.returncode == 0
    assert "27-no-audience.md" in result.stdout
    assert "Implementation brief" in result.stdout
    # Match the indented entry line only; the closing advisory legitimately
    # mentions "For:" while describing what to look for.
    assert not [line for line in result.stdout.splitlines() if line.startswith("      For:")]


def test_listing_is_capped(tmp_path):
    """The cap bounds session-start context cost."""
    repo = _repo(tmp_path)
    for i in range(6):
        _write_handoff(repo, f"{i:02d}-h.md", f"Handoff {i}", "someone")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add handoffs")

    result = _run(repo, HANDOFF_SURFACE_MAX="2")

    assert result.returncode == 0
    assert sum(1 for line in result.stdout.splitlines() if line.startswith("  - ")) == 2


def test_hook_never_blocks_on_a_broken_repository(tmp_path):
    """Fail-open: advisory hooks must not be able to stop a session starting."""
    missing = tmp_path / "does-not-exist"

    result = (
        _run(missing)
        if missing.exists()
        else subprocess.run(
            [BASH, str(HOOK)],
            cwd=tmp_path,
            env={"CLAUDE_PROJECT_DIR": str(missing)},
            capture_output=True,
            text=True,
        )
    )

    assert result.returncode == 0
