# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Automatic negative and positive controls for the Manager dispatch-readiness
# guard, which was live (1,567 receipts) but covered by no test.
"""Controls for ``.claude/hooks/dispatch-readiness-guard.sh``.

Obs 2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug (secondary finding): the
guard is wired and fires, and one manual probe on 2026-07-28 recorded a deny, but no test
proves its deny branches still work, and it fails open on error. These tests run the real
hook under Git's bash and fail rather than skip without bash.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "dispatch-readiness-guard.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
BUS = r"C:\Users\steph\TDL\.apm\bus\worker-a\task.md"

TASK_PROMPT = (
    "---\ntasks: [3.1]\nlog_path: .apm/memory/stage-03/task-3-1.md\n---\n# Task 3.1\n\n## Workspace\nworktree\n"
)
READINESS_PASS = "\n## Dispatch Readiness\n- worktree: **PASS**\n- contracts: **PASS**\n"
READINESS_FAIL = "\n## Dispatch Readiness\n- worktree: **PASS**\n- contracts: **FAIL** (missing binding)\n"


def _bash() -> str:
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the dispatch-readiness guard's controls cannot run, and must not silently skip")
    return found


def _run(raw_stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bash(), str(HOOK)], input=raw_stdin, capture_output=True, text=True, encoding="utf-8", timeout=60
    )


def _decision(tool: str, file_path: str, content: str) -> str:
    result = _run(json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path, "content": content}}))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def test_a_task_prompt_without_a_readiness_block_is_denied() -> None:
    assert _decision("Write", BUS, TASK_PROMPT) == "deny"


def test_a_task_prompt_whose_readiness_block_reports_fail_is_denied() -> None:
    assert _decision("Write", BUS, TASK_PROMPT + READINESS_FAIL) == "deny"


def test_a_task_prompt_with_a_passing_readiness_block_is_allowed() -> None:
    assert _decision("Write", BUS, TASK_PROMPT + READINESS_PASS) == "allow"


def test_the_bus_path_is_recognised_in_posix_form() -> None:
    assert _decision("Write", "/c/Users/steph/TDL/.apm/bus/worker-a/task.md", TASK_PROMPT) == "deny"


@pytest.mark.parametrize(
    ("tool", "file_path", "content"),
    [
        ("Write", BUS, "Relay: Worker reports the branch is pushed."),
        ("Write", r"C:\Users\steph\TDL\.apm\bus\worker-a\report.md", TASK_PROMPT),
        ("Write", r"C:\Users\steph\TDL\docs\task.md", TASK_PROMPT),
        ("Edit", BUS, TASK_PROMPT),
    ],
    ids=["relay-without-workspace", "report-not-task", "task-md-outside-bus", "edit-not-write"],
)
def test_out_of_scope_writes_are_allowed(tool: str, file_path: str, content: str) -> None:
    """Positive controls: relays, other bus files, non-bus task.md files and incremental edits pass."""
    assert _decision(tool, file_path, content) == "allow"


def test_malformed_input_fails_open_with_the_receipt_marker() -> None:
    result = _run('{"tool_name": "Write", "tool_input": {"file_path": "x"')
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "FAILING OPEN" in result.stderr


def test_the_guard_is_wired_for_writes_through_the_receipt_wrapper() -> None:
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    wired = [
        group
        for group in groups
        for hook in group["hooks"]
        if "dispatch-readiness-guard.sh" in hook["command"] and "_receipt-wrap.sh" in hook["command"]
    ]
    assert len(wired) == 1
    assert "Write" in wired[0]["matcher"].split("|")
