# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group B)
# Purpose: Controls for the SessionStart line that says when the weekly system review is overdue.
"""Controls for ``tools/review_staleness.py``.

Obs 2026-10-15-weekly-review-missed-its-run-without-signal: the scheduled review skipped 2026-10-13 and nothing
said so.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "review_staleness.py"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def _run(tmp_path: Path, content: str | None, *args: str) -> subprocess.CompletedProcess[str]:
    date_file = tmp_path / "last-review-date.txt"
    if content is not None:
        date_file.write_text(content, encoding="utf-8")
    argv = [sys.executable, str(TOOL), "--date-file", str(date_file), "--today", "2026-10-15", *args]
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def test_a_review_nine_days_old_warns_and_one_two_days_old_does_not(tmp_path: Path) -> None:
    stale = _run(tmp_path, "2026-10-06")
    assert stale.returncode == 1
    assert stale.stdout.startswith("WARNING: the weekly system review last ran 2026-10-06, 9 days ago")
    fresh = _run(tmp_path, "2026-10-13")
    assert fresh.returncode == 0, fresh.stdout
    assert fresh.stdout.startswith("OK: the weekly system review last ran 2026-10-13 (2 days ago)")


def test_the_boundary_is_eight_days(tmp_path: Path) -> None:
    assert _run(tmp_path, "2026-10-07").returncode == 0
    assert _run(tmp_path, "2026-10-06").returncode == 1


def test_a_missing_or_unreadable_date_warns_rather_than_reading_as_current(tmp_path: Path) -> None:
    missing = _run(tmp_path, None)
    assert missing.returncode == 1 and missing.stdout.startswith("WARNING: no system review date recorded")
    garbled = _run(tmp_path, "not a date ⊆ " * 50)
    assert garbled.returncode == 1 and garbled.stdout.startswith("WARNING: unreadable system review date")
    assert len(garbled.stdout) < 400, "the unreadable value is echoed truncated, not whole"


def test_session_start_never_fails_the_session(tmp_path: Path) -> None:
    result = _run(tmp_path, "2026-09-01", "--session-start")
    assert result.returncode == 0
    assert result.stdout.startswith("WARNING:")


def test_session_start_runs_the_staleness_line() -> None:
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    commands = [hook["command"] for group in hooks for hook in group["hooks"]]
    assert any("tools/review_staleness.py" in c and "--session-start" in c for c in commands)
