# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Fail when any tracked hook/tool file other than the two known readers references
# .git/hooks in code, so the 47-day dead-hook incident cannot recur from a sibling copy.
"""Tree-wide lint against writers targeting ``.git/hooks``.

This repository sets ``core.hooksPath=.githooks``, so git ignores ``.git/hooks`` entirely. The
contract validator was installed there on 2026-05-27 and never ran for 47 days.
``.claude/hooks/install-git-hooks.py`` was rewritten to prevent that, but a sibling installer at
``.codex/hooks/install-git-hooks.py`` kept copying into ``.git/hooks`` unnoticed (obs
2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug). Fixing the one file did not fix the
pattern, so the governed set here is every tracked file in the directories that carry hooks and
tooling, derived from git rather than listed by hand.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNED = [".claude/hooks", ".codex", ".githooks", ".github", "tools", "shared", "research_system"]
# Readers only: they resolve or inspect the hooks directory, they never write into it.
ALLOWED = {".claude/hooks/install-git-hooks.py", "shared/manager_dispatch_check.py"}
PATTERN = re.compile(r"""\.git[/\\]hooks|["']\.git["']\s*/\s*["']hooks["']""")


def references_in_code(text: str) -> list[int]:
    """Return 1-based line numbers of non-comment lines that reference .git/hooks."""
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if PATTERN.search(line) and not line.lstrip().startswith(("#", "//"))
    ]


def violations(repo_root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *SCANNED], cwd=repo_root, capture_output=True, check=True
    ).stdout
    found: list[str] = []
    for path in (chunk.decode("utf-8") for chunk in out.split(b"\x00") if chunk):
        if path in ALLOWED:
            continue
        try:
            text = (repo_root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        found += [f"{path}:{line}" for line in references_in_code(text)]
    return found


def test_no_tracked_hook_or_tool_file_writes_to_dot_git_hooks() -> None:
    assert violations(REPO_ROOT) == [], (
        "these files reference .git/hooks in code; git ignores that directory because "
        "core.hooksPath=.githooks, so a hook written there silently never runs"
    )


def test_the_scanner_flags_the_deleted_installer_shape() -> None:
    """Negative control: the exact lines the dead .codex installer carried are flagged."""
    planted = 'GIT_HOOKS_DIR = REPO_ROOT / ".git" / "hooks"\nshutil.copy2(src, ".git/hooks/commit-msg")\n'
    assert references_in_code(planted) == [1, 2]


def test_the_scanner_ignores_comments() -> None:
    """Positive control: explaining the incident in a comment is not a write."""
    assert references_in_code("# anything placed in .git/hooks/ is ignored\n  # .git/hooks again\n") == []
