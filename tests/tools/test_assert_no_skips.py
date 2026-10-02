# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Controls for the CI check that refuses a lane whose controls skipped or never ran.
"""Controls for ``tools/assert_no_skips.py``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "assert_no_skips.py"


def _report(tmp_path: Path, cases: str) -> Path:
    path = tmp_path / "report.xml"
    path.write_text(f'<?xml version="1.0"?><testsuites><testsuite name="pytest">{cases}</testsuite></testsuites>')
    return path


def _run(report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), str(report)], capture_output=True, text=True, check=False)


PASSED = '<testcase classname="tests.tools.t" name="test_a"/>'
SKIPPED = '<testcase classname="tests.tools.t" name="test_b"><skipped message="Git Bash is required"/></testcase>'


def test_all_executed_passes(tmp_path: Path) -> None:
    result = _run(_report(tmp_path, PASSED * 3))
    assert result.returncode == 0, result.stderr
    assert "3 control(s) executed, none skipped" in result.stdout


def test_a_skipped_control_fails_and_is_named(tmp_path: Path) -> None:
    result = _run(_report(tmp_path, PASSED + SKIPPED))
    assert result.returncode == 1
    assert "tests.tools.t::test_b" in result.stderr


def test_an_empty_report_fails(tmp_path: Path) -> None:
    """Zero tests is not a pass: the lane never ran its controls."""
    result = _run(_report(tmp_path, ""))
    assert result.returncode == 1
    assert "no tests" in result.stderr


def test_a_missing_report_fails(tmp_path: Path) -> None:
    result = _run(tmp_path / "absent.xml")
    assert result.returncode == 1
