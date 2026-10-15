# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group E)
# Purpose: Prove the workflow-step harness runs a step the way GitHub does: the two bugs a string check missed
# on #329 (errexit ending the step, CRLF kept by mapfile) must reproduce through it, or it proves nothing.
"""Controls for ``tests/tools/workflow_steps.py``.

Obs 2026-10-06-workflow-step-tested-by-string-not-by-running.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.tools.workflow_steps import run_step


def _workflow(script: str) -> dict:
    return {"jobs": {"lane": {"steps": [{"name": "step", "run": script}]}}}


def test_errexit_ends_the_step_at_a_failing_command(tmp_path: Path) -> None:
    """The pre-238fd54d shard step: pytest exit 1 ended the step before the baseline line ran."""
    pre_fix = "tool_under_test\necho reached > reached.txt\n"
    result = run_step(_workflow(pre_fix), "lane", "step", tmp_path, prelude="tool_under_test() { return 1; }\n")
    assert result.returncode == 1
    assert not (tmp_path / "reached.txt").exists(), "the harness did not apply GitHub's -e"

    fixed = "status=0\ntool_under_test || status=$?\necho reached > reached.txt\n"
    result = run_step(_workflow(fixed), "lane", "step", tmp_path, prelude="tool_under_test() { return 1; }\n")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "reached.txt").exists()


def test_pipefail_reports_a_failure_inside_a_pipeline(tmp_path: Path) -> None:
    result = run_step(_workflow("false | cat\necho reached > reached.txt\n"), "lane", "step", tmp_path)
    assert result.returncode == 1
    assert not (tmp_path / "reached.txt").exists(), "the harness did not apply GitHub's -o pipefail"


def test_mapfile_keeps_the_carriage_returns_windows_python_writes(tmp_path: Path) -> None:
    """The second #329 bug: shard paths reached pytest with a trailing \\r."""
    (tmp_path / "shard.txt").write_bytes(b"a.py\r\nb.py\r\n")
    script = "mapfile -t files < shard.txt\nprintf '%s|' \"${files[@]}\" > out.txt\n"
    result = run_step(_workflow(script), "lane", "step", tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.txt").read_bytes() == b"a.py\r|b.py\r|"


def test_a_replacement_must_match_exactly_once(tmp_path: Path) -> None:
    """A renamed command must not leave its stub unused while the real tool runs."""
    with pytest.raises(AssertionError, match="occurs 0 times"):
        run_step(_workflow("echo hi\n"), "lane", "step", tmp_path, replace={"pytest": "fake"})
