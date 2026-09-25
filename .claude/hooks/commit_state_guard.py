# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign A)
# Purpose: Refuse a git commit whose outcome the session would misread: piped away
# from its exit status, or made on a branch that moved since the session last looked.
"""Harness hook logic behind ``.claude/hooks/commit-state-guard.sh``.

PreToolUse (Bash, PowerShell) denies two commit shapes:

* **Piped commit** (Bash only): ``git commit ... | tail`` reports the last
  command's status, so a commit blocked by pre-commit reads as exit 0
  (obs 2026-09-08-blocked-commit-reported-exit-zero). ``set -o pipefail`` or a
  commit at the end of the pipeline is admitted. PowerShell is excluded because
  its pipeline sets ``$LASTEXITCODE`` from the native command.
* **Branch drift**: HEAD in the commit's repository is not the branch this
  session last saw there, and the command does not itself check out a branch
  first (obs 2026-09-08-concurrent-session-branch-switch).

PostToolUse (Bash, PowerShell) records, per session, the branch of every
repository a git command touched, in ``<absolute-git-dir>/tdl-session-branches.json``.
The git dir is per worktree, so each worktree keeps its own record. Any git
command counts as the session looking, so after a refusal a single ``git status``
records the new branch and the commit is admitted knowingly.

The hook reads the payload from stdin and writes a decision (PreToolUse) or
nothing (PostToolUse). Errors propagate; the launcher turns them into a visible
FAILING OPEN.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

STATE_FILE = "tdl-session-branches.json"
MAX_SESSIONS = 200
DETACHED = "(detached HEAD)"
SEPARATORS = {";", "&&", "||", "&", "\n"}
PIPES = {"|", "|&"}
GIT_TOKEN = re.compile(r"(?:.*[\\/])?git(?:\.exe)?", re.IGNORECASE)
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
BRANCH_MOVERS = {"checkout", "switch"}

PIPE_REASON = (
    "git commit is piped into another command, so the tool reports the LAST command's exit "
    "status: a commit blocked by pre-commit reads as exit 0 "
    "(obs 2026-09-08-blocked-commit-reported-exit-zero). Run the commit unpiped (redirect long "
    "output to a file instead), or prefix `set -o pipefail;`, then confirm with `git log -1` "
    "that HEAD actually moved."
)


def tokenize(command: str) -> list[str]:
    """Split a shell command into words and operator tokens, respecting quotes."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    return list(lexer)


def statements(tokens: list[str]) -> list[list[list[str]]]:
    """Group tokens into statements, each a list of pipeline segments."""
    result: list[list[list[str]]] = []
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            if any(segments):
                result.append(segments)
            segments = [[]]
        elif token in PIPES:
            segments.append([])
        else:
            segments[-1].append(token)
    if any(segments):
        result.append(segments)
    return result


def git_call(segment: list[str]) -> tuple[str | None, str | None]:
    """Return (subcommand, -C directory) if the segment runs git, else (None, None)."""
    index = 0
    while index < len(segment) and ASSIGNMENT.fullmatch(segment[index]):
        index += 1
    if index >= len(segment) or not GIT_TOKEN.fullmatch(segment[index]):
        return None, None
    directory: str | None = None
    index += 1
    while index < len(segment):
        token = segment[index]
        if token in GIT_VALUE_OPTIONS:
            if token == "-C" and index + 1 < len(segment):
                directory = segment[index + 1] if directory is None else str(Path(directory) / segment[index + 1])
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token, directory
    return None, directory


def to_native(path: str) -> str:
    """Translate an MSYS drive path (/c/Users/...) into a Windows path; leave others alone."""
    match = re.fullmatch(r"/([a-zA-Z])(/.*)?", path)
    if match and os.name == "nt":
        return f"{match.group(1).upper()}:{match.group(2) or '/'}"
    return os.path.expanduser(path)


def resolve(base: str, target: str | None) -> str:
    if not target:
        return base
    native = to_native(target)
    return native if Path(native).is_absolute() else str(Path(base) / native)


def git(directory: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", directory, *args], capture_output=True, text=True, encoding="utf-8", timeout=15, check=False
    )


def branch_and_state(directory: str) -> tuple[str, Path] | None:
    """Return (current branch, state file) for the repository at ``directory``, or None if not a repo."""
    git_dir = git(directory, "rev-parse", "--absolute-git-dir")
    if git_dir.returncode != 0 or not git_dir.stdout.strip():
        return None
    head = git(directory, "symbolic-ref", "-q", "--short", "HEAD")
    branch = head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else DETACHED
    return branch, Path(git_dir.stdout.strip()) / STATE_FILE


def load(state: Path) -> dict[str, str]:
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def save(state: Path, records: dict[str, str]) -> None:
    trimmed = dict(list(records.items())[-MAX_SESSIONS:])
    temporary = state.with_name(state.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(trimmed, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, state)


def walk(command: str, cwd: str):
    """Yield (statement index, segment index, segment count, subcommand, repo dir) for each git call."""
    current = cwd
    for s_index, statement in enumerate(statements(tokenize(command))):
        for g_index, segment in enumerate(statement):
            words = [w for w in segment if not ASSIGNMENT.fullmatch(w)]
            if words[:1] in (["cd"], ["Set-Location"], ["pushd"]) and len(statement) == 1:
                current = resolve(current, words[1] if len(words) > 1 else os.path.expanduser("~"))
                continue
            subcommand, directory = git_call(segment)
            if subcommand is not None or directory is not None:
                yield s_index, g_index, len(statement), subcommand, resolve(current, directory)


def decide(payload: dict) -> dict | None:
    event = payload.get("hook_event_name", "PreToolUse")
    command = str((payload.get("tool_input") or {}).get("command") or "")
    cwd = str(payload.get("cwd") or os.getcwd())
    session = str(payload.get("session_id") or "")
    tool = str(payload.get("tool_name") or "")
    calls = list(walk(command, cwd))

    if event == "PostToolUse":
        for _, _, _, _, directory in calls:
            found = branch_and_state(directory)
            if found and session:
                branch, state = found
                records = load(state)
                records.pop(session, None)
                records[session] = branch
                save(state, records)
        return None

    def emit(decision: str, reason: str | None = None) -> dict:
        out: dict = {"hookEventName": "PreToolUse", "permissionDecision": decision}
        if reason:
            out["permissionDecisionReason"] = reason
        return {"hookSpecificOutput": out}

    commits = [call for call in calls if call[3] == "commit"]
    if not commits:
        return emit("allow")

    piped = any(g_index < count - 1 for _, g_index, count, _, _ in commits)
    if tool == "Bash" and piped and "pipefail" not in command:
        return emit("deny", PIPE_REASON)

    first_commit = min(s_index for s_index, *_ in commits)
    moves_branch = any(call[3] in BRANCH_MOVERS and call[0] <= first_commit for call in calls)
    if moves_branch or not session:
        return emit("allow")
    for _, _, _, _, directory in commits:
        found = branch_and_state(directory)
        if not found:
            continue
        branch, state = found
        seen = load(state).get(session)
        if seen is not None and seen != branch:
            return emit(
                "deny",
                f"HEAD in {directory} is on '{branch}', but this session last saw '{seen}' there. Another "
                "session sharing this working directory may have switched branches "
                "(obs 2026-09-08-concurrent-session-branch-switch). Check `git reflog -5` and "
                f"`git branch --show-current`. If '{branch}' really is where this commit belongs, any git read "
                "(e.g. `git status`) records it and the commit will be admitted.",
            )
    return emit("allow")


def main() -> int:
    decision = decide(json.load(sys.stdin))
    if decision is not None:
        sys.stdout.write(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
