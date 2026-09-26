# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign A)
# Purpose: Refuse a git commit whose outcome the session would misread: piped away
# from its exit status, or made on a branch that moved since the session last looked.
"""Harness hook logic behind ``.claude/hooks/commit-state-guard.sh``.

PreToolUse (Bash, PowerShell) denies three command shapes:

* **Piped commit** (Bash only): ``git commit ... | tail`` reports the last
  command's status, so a commit blocked by pre-commit reads as exit 0
  (obs 2026-09-08-blocked-commit-reported-exit-zero). Admitted when an earlier
  ``set`` statement in the same command turns pipefail on (and none turns it off
  again), or when the commit is the pipeline's last command. PowerShell is
  excluded because its pipeline sets ``$LASTEXITCODE`` from the native command.
* **Branch drift**: HEAD in the commit's repository is not the branch this
  session last saw there (obs 2026-09-08-concurrent-session-branch-switch). A
  checkout or switch in the same repository exempts the commit only when an
  unbroken ``&&`` chain makes the commit depend on it succeeding.
* **Main-commit override**: setting ``TDL_ALLOW_MAIN_COMMIT`` is refused. The
  pre-commit exception is the owner's, used from their own terminal.

Git is found behind ``command``/``env``/``exec``/``time``/``nohup`` prefixes and
subshell or group openers, and the repository follows ``-C``, ``--git-dir`` and
``--work-tree``. A directory change that may fail without stopping the commit
(``cd x; git commit``, ``cd x || git commit``) leaves both directories as
candidates, and every candidate is checked.

PostToolUse (Bash, PowerShell) records, per session, the branch of every
repository a git command touched, one file per session under
``<absolute-git-dir>/tdl-session-branches/``. The git dir is per worktree, so each
worktree keeps its own record, and one file per session means concurrent
sessions never overwrite each other's record. Any git command counts as the
session looking, so after a refusal a single ``git status`` records the new
branch and the commit is admitted knowingly.

The hook reads the payload from stdin and writes a decision (PreToolUse) or
nothing (PostToolUse). Errors propagate; the launcher turns them into a visible
FAILING OPEN.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

STATE_DIR = "tdl-session-branches"
MAX_SESSIONS = 200
DETACHED = "(detached HEAD)"
SEPARATORS = {";", "&&", "||", "&", "\n"}
PIPES = {"|", "|&"}
GIT_TOKEN = re.compile(r"(?:.*[\\/])?git(?:\.exe)?", re.IGNORECASE)
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
OPENERS = {"(", "{", "!"}
WRAPPERS = {"command", "env", "exec", "time", "nohup", "builtin"}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
BRANCH_MOVERS = {"checkout", "switch"}
CHANGE_DIR = {"cd", "Set-Location", "pushd", "sl", "chdir"}
OVERRIDE = re.compile(r"TDL_ALLOW_MAIN_COMMIT\s*=|env:TDL_ALLOW_MAIN_COMMIT", re.IGNORECASE)
SET_PIPEFAIL = re.compile(r"([-+])[a-zA-Z]*o")

PIPE_REASON = (
    "git commit is piped into another command, so the tool reports the LAST command's exit "
    "status: a commit blocked by pre-commit reads as exit 0 "
    "(obs 2026-09-08-blocked-commit-reported-exit-zero). Run the commit unpiped (redirect long "
    "output to a file instead), or prefix `set -o pipefail;`, then confirm with `git log -1` "
    "that HEAD actually moved."
)
OVERRIDE_REASON = (
    "TDL_ALLOW_MAIN_COMMIT is the owner's exception to the pre-commit refusal of commits on main, "
    "for use from the owner's own terminal. An agent does not set it: work reaches main through a "
    "reviewed PR. If a commit on main really is needed, ask the owner to make it."
)


@dataclass(frozen=True)
class Statement:
    segments: list[list[str]]
    separator: str  # the separator that ends this statement ("" at the end of the command)


@dataclass(frozen=True)
class GitCall:
    statement: int
    segment: int
    segment_count: int
    subcommand: str | None
    args: list[str]
    directories: list[str]  # candidate repositories; the first assumes every directory change succeeded


def tokenize(command: str, tool: str) -> list[str]:
    """Split a command into words and operator tokens, respecting quotes.

    PowerShell has no backslash escape, so ``C:\\Users\\x`` must keep its backslashes.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    if tool == "PowerShell":
        lexer.escape = ""
    return list(lexer)


def statements(tokens: list[str]) -> list[Statement]:
    """Group tokens into statements, each a list of pipeline segments plus its closing separator."""
    result: list[Statement] = []
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            if any(segments):
                result.append(Statement(segments, token))
            segments = [[]]
        elif token in PIPES:
            segments.append([])
        else:
            segments[-1].append(token)
    if any(segments):
        result.append(Statement(segments, ""))
    return result


def _strip_prefixes(segment: list[str]) -> list[str]:
    """Drop assignments, subshell/group openers and command wrappers ahead of the real command."""
    index = 0
    while index < len(segment):
        token = segment[index]
        if token in OPENERS or ASSIGNMENT.fullmatch(token):
            index += 1
        elif token in WRAPPERS:
            index += 1
            while index < len(segment) and segment[index].startswith("-") and segment[index] != "--":
                index += 2 if segment[index] in ("-u", "-C", "-S") else 1
        else:
            break
    return segment[index:]


def git_call(segment: list[str]) -> tuple[str | None, list[str], str | None] | None:
    """Return (subcommand, its arguments, repository directory) if the segment runs git, else None.

    The directory combines ``-C`` with ``--work-tree`` (or ``--git-dir``), as git does.
    """
    words = _strip_prefixes(segment)
    if not words or not GIT_TOKEN.fullmatch(words[0]):
        return None
    directory: str | None = None
    git_dir: str | None = None
    work_tree: str | None = None
    index = 1
    while index < len(words):
        token = words[index]
        name, has_value, inline = token.partition("=")
        if has_value and name in ("--git-dir", "--work-tree"):
            git_dir, work_tree = (inline, work_tree) if name == "--git-dir" else (git_dir, inline)
            index += 1
            continue
        if token in GIT_VALUE_OPTIONS:
            value = words[index + 1] if index + 1 < len(words) else None
            if token == "-C" and value is not None:
                directory = value if directory is None else str(Path(directory) / value)
            elif token == "--git-dir":
                git_dir = value
            elif token == "--work-tree":
                work_tree = value
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        target = work_tree or git_dir
        if target:
            directory = target if directory is None else str(Path(directory) / target)
        return token, [w for w in words[index + 1 :] if w not in (")", "}")], directory
    return None, [], directory


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


def _dedupe(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(paths))


def walk(parsed: list[Statement], cwd: str) -> list[GitCall]:
    """Return every git call with the repositories it may run in.

    A directory change whose statement ends in ``&&`` guards what follows it; if it
    fails, the chain is skipped until a different separator, after which the old
    directory is live again. Any other separator lets the next statement run in
    either directory, so both stay candidates.
    """
    calls: list[GitCall] = []
    possible = [cwd]
    deferred: list[str] = []  # directories live again once the current && chain ends
    for s_index, statement in enumerate(parsed):
        for g_index, segment in enumerate(statement.segments):
            words = [w for w in _strip_prefixes(segment) if w not in (")", "}")]
            if words[:1] and words[0] in CHANGE_DIR and len(statement.segments) == 1:
                target = words[1] if len(words) > 1 else os.path.expanduser("~")
                old = possible
                possible = _dedupe([resolve(p, target) for p in old])
                if statement.separator == "&&":
                    deferred = _dedupe(deferred + old)
                else:
                    possible = _dedupe(possible + old)
                continue
            found = git_call(segment)
            if found is not None:
                subcommand, args, directory = found
                calls.append(
                    GitCall(
                        s_index,
                        g_index,
                        len(statement.segments),
                        subcommand,
                        args,
                        _dedupe([resolve(p, directory) for p in possible]),
                    )
                )
        if statement.separator != "&&" and deferred:
            possible = _dedupe(possible + deferred)
            deferred = []
    return calls


def pipefail_before(parsed: list[Statement], statement: int) -> bool:
    """Whether ``set`` statements ahead of ``statement`` leave pipefail on."""
    enabled = False
    for current in parsed[:statement]:
        words = current.segments[0] if len(current.segments) == 1 else []
        if words[:1] != ["set"]:
            continue
        for flag, value in zip(words[1:], words[2:]):
            match = SET_PIPEFAIL.fullmatch(flag)
            if match and value == "pipefail":
                enabled = match.group(1) == "-"
    return enabled


def gated_by_move(parsed: list[Statement], calls: list[GitCall], commit: GitCall) -> bool:
    """Whether a same-repository checkout/switch earlier in an unbroken && chain gates this commit."""
    for call in calls:
        if call.subcommand not in BRANCH_MOVERS or call.statement >= commit.statement or "--" in call.args:
            continue
        if not set(call.directories) & set(commit.directories):
            continue
        if all(parsed[i].separator == "&&" for i in range(call.statement, commit.statement)):
            return True
    return False


def git(directory: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", directory, *args], capture_output=True, text=True, encoding="utf-8", timeout=15, check=False
    )


def branch_and_state(directory: str, session: str) -> tuple[str, Path] | None:
    """Return (current branch, this session's record file) for the repository at ``directory``, or None."""
    if not Path(directory).is_dir():
        return None
    git_dir = git(directory, "rev-parse", "--absolute-git-dir")
    if git_dir.returncode != 0 or not git_dir.stdout.strip():
        return None
    head = git(directory, "symbolic-ref", "-q", "--short", "HEAD")
    branch = head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else DETACHED
    name = hashlib.sha256(session.encode("utf-8")).hexdigest()[:32]
    return branch, Path(git_dir.stdout.strip()) / STATE_DIR / name


def load(record: Path) -> str | None:
    try:
        return record.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def save(record: Path, branch: str) -> None:
    """Write this session's record atomically, then prune the oldest records beyond MAX_SESSIONS."""
    record.parent.mkdir(exist_ok=True)
    temporary = record.with_name(f"{record.name}.{os.getpid()}.tmp")
    temporary.write_text(branch + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, record)
    records = [p for p in record.parent.iterdir() if p.is_file() and not p.name.endswith(".tmp")]
    if len(records) > MAX_SESSIONS:
        records.sort(key=lambda p: p.stat().st_mtime)
        for stale in records[: len(records) - MAX_SESSIONS]:
            stale.unlink(missing_ok=True)


def emit(decision: str, reason: str | None = None) -> dict:
    out: dict = {"hookEventName": "PreToolUse", "permissionDecision": decision}
    if reason:
        out["permissionDecisionReason"] = reason
    return {"hookSpecificOutput": out}


def decide(payload: dict) -> dict | None:
    event = payload.get("hook_event_name", "PreToolUse")
    command = str((payload.get("tool_input") or {}).get("command") or "")
    cwd = str(payload.get("cwd") or os.getcwd())
    session = str(payload.get("session_id") or "")
    tool = str(payload.get("tool_name") or "")
    parsed = statements(tokenize(command, tool))
    calls = walk(parsed, cwd)

    if event == "PostToolUse":
        for call in calls:
            found = branch_and_state(call.directories[0], session) if session else None
            if found:
                save(found[1], found[0])
        return None

    if OVERRIDE.search(command):
        return emit("deny", OVERRIDE_REASON)

    commits = [call for call in calls if call.subcommand == "commit"]
    if not commits:
        return emit("allow")

    if tool == "Bash":
        for commit in commits:
            if commit.segment < commit.segment_count - 1 and not pipefail_before(parsed, commit.statement):
                return emit("deny", PIPE_REASON)

    if not session:
        return emit("allow")
    for commit in commits:
        if gated_by_move(parsed, calls, commit):
            continue
        for directory in commit.directories:
            found = branch_and_state(directory, session)
            if not found:
                continue
            branch, record = found
            seen = load(record)
            if seen is not None and seen != branch:
                return emit(
                    "deny",
                    f"HEAD in {directory} is on '{branch}', but this session last saw '{seen}' there. Another "
                    "session sharing this working directory may have switched branches "
                    "(obs 2026-09-08-concurrent-session-branch-switch). Check `git reflog -5` and "
                    f"`git branch --show-current`. If '{branch}' really is where this commit belongs, any git "
                    "read (e.g. `git status`) records it and the commit will be admitted.",
                )
    return emit("allow")


def main() -> int:
    decision = decide(json.load(sys.stdin))
    if decision is not None:
        sys.stdout.write(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
