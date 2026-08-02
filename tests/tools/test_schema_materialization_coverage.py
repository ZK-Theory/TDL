"""Sanity checks for tools/schema_materialization_coverage.py (obs 145).

Why: `.research-system/schemas/core/` holds an accepted specification surface
that `CommandService._build_event` only partially implements, and nothing
published the ratio — a planning session reading only the runtime concluded
a capability was absent and designed a duplicate. This script introspects
both sides live (AST over `_build_event`, `$id` over the schema files) so it
cannot go stale the way a hand-written coverage table would.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "schema_materialization_coverage.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_reports_a_ratio_smaller_than_the_full_accepted_set() -> None:
    """Regression: the whole point is that wired < accepted right now."""
    result = _run()
    assert result.returncode == 0, result.stderr
    assert "Accepted command schemas :" in result.stdout
    assert "Wired in _build_event    :" in result.stdout
    # obs 145's own evidence: 6/86 at filing time. Confirm it stays a small
    # fraction rather than accidentally matching (e.g. a discovery bug that
    # counts every accepted schema as wired would hide the exact gap this
    # tool exists to surface).
    wired_line = next(line for line in result.stdout.splitlines() if line.startswith("Wired in _build_event"))
    wired, _, accepted = wired_line.split(":", 1)[1].strip().partition("/")
    assert int(wired.strip()) < int(accepted.strip())


def test_unwired_only_flag_lists_at_least_one_command() -> None:
    result = _run("--unwired-only")
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) > 0
    # Every emitted name should look like a PascalCase command type, not a
    # stray warning or blank noise leaking into the machine-readable mode.
    assert all(line[0].isupper() and " " not in line for line in lines)
