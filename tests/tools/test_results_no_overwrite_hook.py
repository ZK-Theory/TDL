# Research context: docs/plans/strategy/system-review-2026-09-29-decision-report.md (Campaign N)
# Purpose: Negative and positive controls for the PreToolUse hook that enforces the locked "results
# are never overwritten" rule, which had fired 2,026 times without a recorded deny.
"""Controls for ``.claude/hooks/results-no-overwrite.sh``.

Obs 2026-09-29-results-no-overwrite-never-watched-to-fail: ``hook-receipts.log`` held 2,026
receipts for this hook since 2026-07-28 and every one was ``decision=allow``. That is evidence the
hook runs, not that it can deny, and it fails open on any error, so a regression in its Python
block would have read as the same stream of allows. These tests run the real hook through the real
``_receipt-wrap.sh``, as ``.claude/settings.json`` wires it, and assert a deny case per branch of
the hook with its deny reason, the three allow cases the rule permits, and the fail-open warning.
They fail rather than skip when no usable bash exists, because a guard whose controls silently
skip in CI is unwatched.

Out of scope, and stated in the hook's header: result scripts write through Python, never the
Write tool, so nothing here can observe a script-side overwrite.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "results-no-overwrite.sh"
RECEIPT_WRAP = REPO_ROOT / ".claude" / "hooks" / "_receipt-wrap.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

JSON_BODY = '{"w2": 12.7}\n'
BINARY_BODY = b"\x93NUMPY\x01\x00not-a-real-array"


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the results-no-overwrite controls cannot run, and must not silently skip")
    return found


def _bash_path(path: Path) -> str:
    """Return ``path`` in the ``/c/...`` form the wrapper hands to ``exec``."""
    resolved = path.resolve().as_posix()
    return f"/{resolved[0].lower()}{resolved[2:]}" if resolved[1:3] == ":/" else resolved


@dataclass(frozen=True)
class Outcome:
    """One hook invocation: the decision the harness would act on and what the wrapper recorded."""

    decision: str
    reason: str
    stderr: str
    receipt: list[str]


def _invoke(project: Path, raw_stdin: str, hook: Path = HOOK) -> Outcome:
    """Run ``hook`` through the real receipt wrapper, with receipts kept inside ``project``.

    The returned receipt holds only the lines this call appended, so several calls may share a project.
    """
    (project / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    log = project / ".claude" / "hooks" / "hook-receipts.log"
    already = len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0
    result = subprocess.run(
        [_bash(), _bash_path(RECEIPT_WRAP), _bash_path(hook)],
        input=raw_stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    emitted = json.loads(result.stdout)["hookSpecificOutput"]
    assert emitted["hookEventName"] == "PreToolUse"
    receipt = log.read_text(encoding="utf-8").splitlines()[already:]
    return Outcome(emitted["permissionDecision"], emitted.get("permissionDecisionReason", ""), result.stderr, receipt)


def _call(tool: str, file_path: Path | str, **fields: object) -> str:
    """Build the PreToolUse payload the harness sends for one tool call."""
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"file_path": str(file_path), **fields}}
    )


def _decide(project: Path, tool: str, file_path: Path | str, **fields: object) -> Outcome:
    """Run one tool call and assert the wrapper left one receipt agreeing with the decision."""
    outcome = _invoke(project, _call(tool, file_path, **fields))
    assert len(outcome.receipt) == 1, outcome.receipt
    assert f"hook=results-no-overwrite decision={outcome.decision} " in outcome.receipt[0], outcome.receipt
    return outcome


def _seed(root: Path, relative: str) -> Path:
    """Create an existing file under ``root`` and return its path."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(BINARY_BODY if path.suffix in {".npy", ".npz"} else JSON_BODY.encode("utf-8"))
    return path


EDIT = {"old_string": "12.7", "new_string": "13.1"}
MULTI_EDIT = {"edits": [{"old_string": "12.7", "new_string": "13.1"}]}

# (id, tool, existing results file, tool_input fields, text the deny reason must carry)
DENIED = [
    ("edit-json", "Edit", "results/p01/w2_2026-09-01.json", EDIT, "is an existing results file"),
    ("multiedit-json", "MultiEdit", "results/p01/w2_2026-09-01.json", MULTI_EDIT, "is an existing results file"),
    ("edit-npy", "Edit", "results/p01/diagrams_2026-09-01.npy", EDIT, "is an existing results file"),
    ("multiedit-npz", "MultiEdit", "results/p01/diagrams_2026-09-01.npz", MULTI_EDIT, "is an existing results file"),
    (
        "write-npy",
        "Write",
        "results/p01/diagrams_2026-09-01.npy",
        {"content": "x"},
        "existing binary results file (.npy)",
    ),
    (
        "write-npz",
        "Write",
        "results/p01/diagrams_2026-09-01.npz",
        {"content": "x"},
        "existing binary results file (.npz)",
    ),
    (
        "write-differing-json",
        "Write",
        "results/p01/w2_2026-09-01.json",
        {"content": '{"w2": 99.0}\n'},
        "already exists and the new content differs",
    ),
    (
        "write-json-differing-by-a-trailing-newline",
        "Write",
        "results/p01/w2_2026-09-01.json",
        {"content": JSON_BODY + "\n"},
        "already exists and the new content differs",
    ),
]


@pytest.mark.parametrize(
    ("tool", "relative", "fields", "reason"),
    [case[1:] for case in DENIED],
    ids=[case[0] for case in DENIED],
)
def test_overwriting_an_existing_results_file_is_denied_with_its_reason(
    tmp_path: Path, tool: str, relative: str, fields: dict[str, object], reason: str
) -> None:
    """The watched failure: each deny branch refuses, names its own reason, and leaves a deny receipt."""
    target = _seed(tmp_path / "work", relative)
    before = target.read_bytes()

    outcome = _decide(tmp_path / "project", tool, target, **fields)

    assert outcome.decision == "deny"
    assert reason in outcome.reason
    assert str(target) in outcome.reason
    assert outcome.stderr == ""
    assert target.read_bytes() == before, "the guard must never touch the file it protects"


@pytest.mark.parametrize("spelling", ["native", "posix"])
def test_both_path_spellings_reach_the_deny_branch(tmp_path: Path, spelling: str) -> None:
    """A Windows path with backslashes and its forward-slash form are the same results file."""
    target = _seed(tmp_path / "work", "results/p01/w2_2026-09-01.json")
    given = str(target) if spelling == "native" else target.as_posix()

    outcome = _decide(tmp_path / "project", "Edit", given, **EDIT)

    assert outcome.decision == "deny"
    assert "is an existing results file" in outcome.reason


def test_a_new_date_suffixed_file_is_allowed(tmp_path: Path) -> None:
    """Positive control: the sanctioned way to change a result, a new suffix beside the old file, passes."""
    _seed(tmp_path / "work", "results/p01/w2_2026-09-01.json")
    fresh = tmp_path / "work" / "results" / "p01" / "w2_2026-10-02.json"

    for tool, fields in (("Write", {"content": '{"w2": 13.1}\n'}), ("Edit", EDIT)):
        outcome = _decide(tmp_path / "project", tool, fresh, **fields)
        assert outcome.decision == "allow", tool
        assert outcome.reason == ""
    fresh_array = tmp_path / "work" / "results" / "p01" / "diagrams_2026-10-02.npy"
    assert _decide(tmp_path / "project", "Write", fresh_array, content="x").decision == "allow"


def test_a_byte_identical_rewrite_is_allowed(tmp_path: Path) -> None:
    """Positive control: an idempotent rerun that reproduces the existing bytes overwrites nothing."""
    target = _seed(tmp_path / "work", "results/p01/w2_2026-09-01.json")

    outcome = _decide(tmp_path / "project", "Write", target, content=JSON_BODY)

    assert outcome.decision == "allow"
    assert outcome.reason == ""


# (id, tool, existing file the call targets, fields): none of these is a results record.
OUTSIDE_THE_RULE = [
    ("json-outside-results", "Write", "docs/notes/w2.json", {"content": '{"w2": 99.0}\n'}),
    ("edit-outside-results", "Edit", "docs/notes/w2.json", EDIT),
    ("multiedit-outside-results", "MultiEdit", "docs/notes/w2.json", MULTI_EDIT),
    ("directory-merely-ending-in-results", "Edit", "my_results/w2.json", EDIT),
    ("directory-merely-starting-with-results", "Edit", "results_old/w2.json", EDIT),
    ("extension-outside-the-rule", "Write", "results/p01/table.csv", {"content": "a,b\n"}),
]


@pytest.mark.parametrize(
    ("tool", "relative", "fields"),
    [case[1:] for case in OUTSIDE_THE_RULE],
    ids=[case[0] for case in OUTSIDE_THE_RULE],
)
def test_paths_outside_the_rule_are_allowed(
    tmp_path: Path, tool: str, relative: str, fields: dict[str, object]
) -> None:
    """Positive controls on scope: only results/**/*.{json,npy,npz} is guarded, whatever the edit."""
    target = _seed(tmp_path / "work", relative)

    outcome = _decide(tmp_path / "project", tool, target, **fields)

    assert outcome.decision == "allow"
    assert outcome.reason == ""


def test_a_call_with_no_file_path_is_allowed(tmp_path: Path) -> None:
    """A payload that names no file has nothing to protect and must not be denied or crash."""
    outcome = _invoke(
        tmp_path / "project", json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {}})
    )
    assert outcome.decision == "allow"
    assert outcome.stderr == ""


@pytest.mark.parametrize(
    "raw",
    ['{"tool_name": "Edit", "tool_input": {"file_path": "results/x.json"', "not json at all", ""],
    ids=["truncated-json", "not-json", "empty"],
)
def test_a_malformed_payload_fails_open_with_the_warning_and_receipt(tmp_path: Path, raw: str) -> None:
    """The documented fail-open path: the write is allowed, loudly, and the receipt marks it unchecked."""
    project = tmp_path / "project"

    outcome = _invoke(project, raw)

    assert outcome.decision == "allow"
    assert "FAILING OPEN" in outcome.stderr
    assert "results-immutability rule manually" in outcome.stderr
    assert len(outcome.receipt) == 1
    assert "hook=results-no-overwrite decision=FAILOPEN(" in outcome.receipt[0]


def test_the_hook_is_wired_for_write_edit_and_multiedit_through_the_receipt_wrapper() -> None:
    """A guard that exists but is not wired for a tool guards nothing for that tool."""
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    wired = [
        (group, hook)
        for group in groups
        for hook in group["hooks"]
        if "results-no-overwrite.sh" in hook["command"] and "_receipt-wrap.sh" in hook["command"]
    ]
    assert len(wired) == 1, "results-no-overwrite.sh must be wired exactly once, through _receipt-wrap.sh"
    group, hook = wired[0]
    assert set(group["matcher"].split("|")) >= {"Write", "Edit", "MultiEdit"}
    assert "--advisory" not in hook["command"], "a PreToolUse gate in advisory mode is recorded as MISWIRED"


def test_the_multiedit_control_discriminates_a_hook_that_lost_its_multiedit_branch(tmp_path: Path) -> None:
    """The suite can tell a broken hook from the real one, so a pass is evidence rather than silence.

    The mutant drops MultiEdit from the Edit/MultiEdit deny branch, so a MultiEdit falls through
    to the Write logic and, carrying no ``content``, is allowed. The same call must be denied by
    the real hook. ``tools/mutation_check.py`` runs the wider set of mutants; this one stays in the
    suite so that the rest of it cannot quietly stop being able to fail.
    """
    anchor = "if tool in ('Edit', 'MultiEdit'):"
    source = HOOK.read_bytes().decode("utf-8")
    assert source.count(anchor) == 1, "the hook changed shape; re-anchor this mutant"
    mutant = tmp_path / "results-no-overwrite.sh"
    mutant.write_bytes(source.replace(anchor, "if tool in ('Edit',):", 1).encode("utf-8"))
    target = _seed(tmp_path / "work", "results/p01/w2_2026-09-01.json")
    payload = _call("MultiEdit", target, **MULTI_EDIT)

    assert _invoke(tmp_path / "project-real", payload).decision == "deny"
    assert _invoke(tmp_path / "project-mutant", payload, hook=mutant).decision == "allow"
