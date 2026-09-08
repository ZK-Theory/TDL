"""Byte-level LF guard for executable hook scripts (obs 2026-09-08-claude-hooks-lack-lf-attribute).

Why: a CRLF shebang is `#!/bin/bash\r`. A shell that does not tolerate it answers
`bad interpreter: /bin/bash^M`, so the hook does not run — and an advisory hook that
does not run is indistinguishable from one that ran and found nothing. That is the
same silent-absence shape as the `.git/hooks` vs `.githooks` incident (a redirect in
force for 47 days while every report claimed hooks ran clean) and as the PostToolUse
hooks that carried zero receipts.

This is not hypothetical. Agent edits silently rewrote `.claude/hooks/_receipt-wrap.sh`
and `.claude/settings.json` from LF to CRLF on 2026-09-08, and again
`tests/tools/test_gitattributes_lf_coverage.py` an hour later, on a checkout with
`core.autocrlf=false` where nothing had asked for it. Each was caught only by noticing
an implausible diffstat. Until that day no `.gitattributes` pattern matched `.claude/`,
`.codex/`, or `.githooks/` at all — including the five git hooks that are the
commit-time gate.

Two assertions, because either alone is insufficient:

- the `.gitattributes` pin, which stops a CRLF working-tree copy being committed
- the committed bytes, because the pin does nothing about a blob that was already
  CRLF before the pin landed

Distinct from `test_gitattributes_lf_coverage.py`, which guards the contract system's
`canonical_byte_surface` hashes. Same attribute, unrelated failure mode: that one is
about hash equality, this one is about whether a script executes at all.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# The hook surface: every tracked shell script anywhere, plus the extensionless git
# hooks under .githooks/ (which carry shebangs but no suffix to match on).
GITHOOKS_DIR = ".githooks/"
SHELL_SUFFIX = ".sh"

CRLF = b"\r\n"
CR = b"\r"


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def _is_hook_script(rel: str) -> bool:
    return rel.endswith(SHELL_SUFFIX) or rel.startswith(GITHOOKS_DIR)


def _hook_scripts() -> list[str]:
    return [rel for rel in _tracked_files() if _is_hook_script(rel)]


def _committed_bytes(rel: str) -> bytes:
    """Bytes as committed at HEAD — not the working tree, which may legitimately be CRLF
    on an `autocrlf=true` checkout. The blob is what every other clone and CI receives."""
    return subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{rel}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout


def _check_attr(rel: str, attr: str) -> str:
    out = subprocess.run(
        ["git", "check-attr", attr, "--", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.rsplit(":", 1)[-1].strip()


@pytest.fixture(scope="module")
def hook_scripts() -> list[str]:
    scripts = _hook_scripts()
    assert scripts, "no tracked hook scripts discovered — this canary's discovery is broken"
    return scripts


def test_every_hook_script_is_pinned_to_lf(hook_scripts: list[str]) -> None:
    """The pin is what stops a CRLF working-tree copy reaching a commit."""
    unpinned = [rel for rel in hook_scripts if _check_attr(rel, "eol") != "lf"]
    assert not unpinned, f".gitattributes does not pin eol=lf for these hook scripts: {unpinned}"


def test_no_hook_script_is_committed_with_crlf(hook_scripts: list[str]) -> None:
    """The pin does nothing about a blob that was already CRLF before the pin landed."""
    offenders = [rel for rel in hook_scripts if CRLF in _committed_bytes(rel)]
    assert not offenders, f"hook scripts committed with CRLF line endings: {offenders}"


def test_no_hook_script_shebang_carries_a_carriage_return(hook_scripts: list[str]) -> None:
    """The specific byte that breaks execution, asserted on the specific line that carries it.

    Kept separate from the whole-file check so a failure names the actual consequence
    (`bad interpreter`) rather than a generic line-ending complaint.
    """
    broken = []
    for rel in hook_scripts:
        first_line = _committed_bytes(rel).split(b"\n", 1)[0]
        if first_line.startswith(b"#!") and first_line.endswith(CR):
            broken.append(rel)
    assert not broken, f"hook scripts whose shebang ends in CR (`bad interpreter: /bin/bash^M`): {broken}"


def test_discovery_covers_both_the_claude_and_githooks_surfaces(hook_scripts: list[str]) -> None:
    """A pattern that silently stopped matching a root would make the checks above vacuous.

    The `.githooks/` entries are the ones most easily lost: they have no `.sh` suffix, so
    a suffix-only discovery drops the commit-time gate while still looking healthy.
    """
    for root in (".claude/hooks/", ".codex/hooks/", GITHOOKS_DIR):
        assert any(rel.startswith(root) for rel in hook_scripts), f"no hook script discovered under {root}"


def test_negative_control_the_crlf_predicate_flags_crlf_bytes() -> None:
    """Proves the byte check can fail, rather than passing because every blob is clean.

    Uses the same predicate the assertions above apply, against bytes known to be CRLF —
    the check is only meaningful if it rejects something.
    """
    crlf_script = b"#!/bin/bash\r\necho hi\r\n"
    lf_script = b"#!/bin/bash\necho hi\n"
    assert CRLF in crlf_script
    assert CRLF not in lf_script
    assert crlf_script.split(b"\n", 1)[0].endswith(CR)
    assert not lf_script.split(b"\n", 1)[0].endswith(CR)


def test_negative_control_an_unpinned_path_is_still_reported_as_unpinned() -> None:
    """Proves the pin check reads real attribute state rather than always returning lf.

    CONVENTIONS.md carries no eol pin (the LF-coverage canary asserts the same thing for
    its own negative control), so a check that called it `lf` would be broken.
    """
    assert _check_attr("CONVENTIONS.md", "eol") != "lf"
