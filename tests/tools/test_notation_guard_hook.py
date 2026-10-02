# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Automatic negative and positive controls for the W_1 notation guard, whose only
# controls were a manual --selftest that nothing ran.
"""Controls for ``.claude/hooks/notation-guard.sh``.

Obs 2026-09-15-notation-guard-selftest-never-wired: the hook fired 864 times with zero
denies, equally consistent with "the rule held" and "the deny path silently regressed",
because its seven-case ``--selftest`` was invoked by no test and no CI lane. These tests run
the real hook under Git's bash with cases written independently of that selftest, run the
selftest itself, and fail rather than skip without bash.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "notation-guard.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the notation guard's controls cannot run, and must not silently skip")
    return found


def _run(raw_stdin: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bash(), str(HOOK), *args],
        input=raw_stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def _decision(tool_input: dict[str, str]) -> str:
    result = _run(json.dumps({"tool_name": "Write", "tool_input": tool_input}))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


DENIED = [
    {"file_path": "papers/P01-A/drafts/v3/methods.md", "content": "We compare diagrams with W_1."},
    {"file_path": r"C:\Users\steph\TDL\papers\P04\draft.tex", "content": r"the $W_{1}$ distance"},
    {"file_path": "C:/Users/steph/TDL/papers/P01-B/notes.txt", "new_string": "swap to W_1 here"},
    {"file_path": "papers/P05/intro.md", "content": "first line\nW_1\nlast line"},
]

ALLOWED = [
    {"file_path": "papers/P01-A/drafts/v3/methods.md", "content": "We compare diagrams with W_2."},
    {"file_path": "papers/P01-A/drafts/v3/methods.md", "content": "W_12 and W_{16} are cluster labels"},
    {"file_path": "papers/shared/notation.md", "content": "Never write W_1 for the primary metric."},
    {"file_path": "docs/plans/notes.md", "content": "W_1 outside papers/ is not a paper claim"},
    {"file_path": "papers/P01-A/analysis.py", "content": "w_1 = wasserstein(a, b, order=1)"},
]


@pytest.mark.parametrize("tool_input", DENIED, ids=[case["file_path"] for case in DENIED])
def test_w1_in_a_paper_draft_is_denied(tool_input: dict[str, str]) -> None:
    """The watched failure: a W_1 mention in any papers/ prose file, by any path form, is refused."""
    assert _decision(tool_input) == "deny"


@pytest.mark.parametrize("tool_input", ALLOWED, ids=[case["file_path"] for case in ALLOWED])
def test_non_violations_are_allowed(tool_input: dict[str, str]) -> None:
    """Positive controls: W_2, W_12, papers/shared, non-paper paths and code all pass."""
    assert _decision(tool_input) == "allow"


def test_malformed_input_fails_open_with_the_receipt_marker() -> None:
    result = _run("not json at all")
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "FAILING OPEN" in result.stderr


def test_the_hooks_own_selftest_passes_when_run() -> None:
    """The selftest existed but nothing invoked it; now something does, every run."""
    result = _run("", "--selftest")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All notation-guard selftests passed (7/7)" in result.stdout


def test_the_guard_is_wired_for_writes_through_the_receipt_wrapper() -> None:
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    wired = [
        group
        for group in groups
        for hook in group["hooks"]
        if "notation-guard.sh" in hook["command"] and "_receipt-wrap.sh" in hook["command"]
    ]
    assert len(wired) == 1, "notation-guard.sh must be wired exactly once, through _receipt-wrap.sh"
    assert set(wired[0]["matcher"].split("|")) >= {"Write", "Edit"}
