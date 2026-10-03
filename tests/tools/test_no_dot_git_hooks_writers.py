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

import ast
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNED = [".claude/hooks", ".codex", ".githooks", ".github", "tools", "shared", "research_system"]
# Read sites only, matched as substrings of the stripped line: each resolves or inspects the hooks
# directory and never writes into it. The rest of these two files is scanned like any other file, so a
# write added to either is seen (they were skipped whole before).
ALLOWED_LINES: dict[str, tuple[str, ...]] = {
    ".claude/hooks/install-git-hooks.py": (
        'return configured, REPO_ROOT / ".git" / "hooks"',
        'shadowed_dir = REPO_ROOT / ".git" / "hooks"',
        "WARNING: .git/hooks contains",
    ),
    "shared/manager_dispatch_check.py": ('hooks_dir = Path(configured) if configured else Path(".git/hooks")',),
}
PATTERN = re.compile(r"""\.git[/\\]hooks|["']\.git["']\s*/\s*["']hooks["']""")


def _docstring_lines(text: str) -> set[int]:
    """Line numbers covered by module, class and function docstrings: prose, not code."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return lines


def references_in_code(text: str, path: str = "") -> list[int]:
    """Return 1-based line numbers of code lines that reference .git/hooks.

    Comments and (for Python) docstrings are prose. A line is also skipped when it is one of the
    ``ALLOWED_LINES`` read sites of ``path``.
    """
    prose = _docstring_lines(text) if path.endswith(".py") or not path else set()
    allowed = ALLOWED_LINES.get(path, ())
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if PATTERN.search(line)
        and not line.lstrip().startswith(("#", "//"))
        and number not in prose
        and not any(site in line for site in allowed)
    ]


def violations(repo_root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *SCANNED], cwd=repo_root, capture_output=True, check=True
    ).stdout
    found: list[str] = []
    for path in (chunk.decode("utf-8") for chunk in out.split(b"\x00") if chunk):
        try:
            text = (repo_root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        found += [f"{path}:{line}" for line in references_in_code(text, path)]
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


def _repo_with(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo


def test_a_writer_inside_an_allowlisted_installer_is_still_flagged(tmp_path: Path) -> None:
    """The two reader files were skipped whole, so a write added to either went unseen.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #303): only the read sites are
    allowed, line for line; anything else in those files is scanned like any other file.
    """
    installer = chr(10).join(
        [
            "import shutil",
            "",
            "",
            "def active(configured, REPO_ROOT):",
            '    return configured, REPO_ROOT / ".git" / "hooks"',  # an allowed read site, verbatim
            "",
            "",
            "def install(src, root):",
            '    shutil.copy2(src, root / ".git" / "hooks" / "pre-commit")',
            "",
        ]
    )
    repo = _repo_with(tmp_path, {".claude/hooks/install-git-hooks.py": installer})

    assert violations(repo) == [".claude/hooks/install-git-hooks.py:9"]
