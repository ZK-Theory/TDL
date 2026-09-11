# Research context: TDA-Research/03-Papers/P06/_project.md
# Purpose: Negative and positive controls for the PreToolUse hook that keeps agent
# sessions from taking the P-049 ruleset bypass or rewriting repository rules.
"""Controls for ``.claude/hooks/admin-bypass-guard.sh``.

Decided by Stephen on 2026-09-11 (PR #278). The P-049 ruleset gives the
repository admin role a pull-request bypass, and every agent acts through the
owner's admin login, so the bypass is only deliberate if agent sessions cannot
take it. These tests run the real hook under Git's bash exactly as the harness
does. They fail rather than skip when no usable bash exists, because a guard
whose controls silently skip in CI is unwatched.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "admin-bypass-guard.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the admin-bypass guard's controls cannot run, and must not silently skip")
    return found


def _run(raw_stdin: str) -> tuple[dict, str]:
    """Run the hook on raw stdin and return (parsed stdout JSON, stderr)."""
    result = subprocess.run(
        [_bash(), str(HOOK)],
        input=raw_stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout), result.stderr


def _decision(tool: str, command: str) -> str:
    """Return the hook's permission decision for one tool call."""
    output, _ = _run(json.dumps({"tool_name": tool, "tool_input": {"command": command}}))
    return output["hookSpecificOutput"]["permissionDecision"]


DENIED = [
    ("Bash", "gh pr merge 278 --admin"),
    ("Bash", "gh pr merge --squash --admin 278"),
    ("PowerShell", "gh pr merge 278 --admin --squash"),
    ("Bash", "git fetch && gh pr merge 278 --admin"),
    ("Bash", "gh api -X PUT repos/ZK-Theory/TDL/rulesets/20822054 --input ruleset.json"),
    ("Bash", "gh api --method PATCH repos/o/r/rulesets/1 -f enforcement=disabled"),
    ("Bash", "gh api repos/o/r/rulesets -f name=weaker"),
    ("PowerShell", "gh api -XDELETE repos/o/r/rulesets/20822054"),
    ("Bash", "gh api -X DELETE repos/o/r/branches/main/protection"),
    ("Bash", "gh api -X PUT repos/o/r/pulls/278/merge -f merge_method=squash"),
    (
        "Bash",
        "gh api graphql -f query='mutation { mergePullRequest(input:{pullRequestId:\"x\"}) { clientMutationId } }'",
    ),
    ("Bash", "gh api graphql -f query='mutation { updateRepositoryRuleset(input:{}) { clientMutationId } }'"),
]

ALLOWED = [
    ("Bash", "gh pr merge 278 --squash --auto"),
    ("Bash", "gh api repos/ZK-Theory/TDL/rulesets/20822054"),
    ("Bash", "gh api -X GET repos/o/r/rulesets"),
    ("PowerShell", "gh api repos/o/r/pulls/278/merge"),
    (
        "Bash",
        'gh api graphql -f query=\'query { repository(owner:"o",name:"r") { rulesets(first:5) { nodes { name } } } }\'',
    ),
    ("Bash", "gh pr view 278 --json state"),
    ("Bash", "git commit -m 'document the --admin bypass and the rulesets change'"),
]


@pytest.mark.parametrize(("tool", "command"), DENIED, ids=[command for _, command in DENIED])
def test_agent_bypass_and_rule_changes_are_refused(tool: str, command: str) -> None:
    """Each way an agent could take the bypass or rewrite the rules is denied."""
    assert _decision(tool, command) == "deny"


@pytest.mark.parametrize(("tool", "command"), ALLOWED, ids=[command for _, command in ALLOWED])
def test_reads_and_queued_merges_are_allowed(tool: str, command: str) -> None:
    """Positive controls: the guard must not block ordinary reads and queue merges."""
    assert _decision(tool, command) == "allow"


def test_a_guard_error_on_a_bypass_command_fails_closed() -> None:
    """An unparseable payload that mentions --admin is refused, not waved through."""
    output, stderr = _run('{"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1 --admin"')
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "FAILING CLOSED" in stderr


def test_a_guard_error_on_an_unrelated_command_fails_open_visibly() -> None:
    """Positive control: an unrelated command still runs, with the marker _receipt-wrap records."""
    output, stderr = _run('{"tool_name": "Bash", "tool_input": {"command": "ls"')
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "FAILING OPEN" in stderr


def test_the_guard_is_wired_for_both_shell_tools_through_the_receipt_wrapper() -> None:
    """A guard that exists but is not wired in settings.json guards nothing."""
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    wired = [
        group
        for group in groups
        for hook in group["hooks"]
        if "admin-bypass-guard.sh" in hook["command"] and "_receipt-wrap.sh" in hook["command"]
    ]
    assert len(wired) == 1, "admin-bypass-guard.sh must be wired exactly once, through _receipt-wrap.sh"
    assert set(wired[0]["matcher"].split("|")) >= {"Bash", "PowerShell"}
