"""Liveness controls for the CRLF byte-surface gate.

The gate exists because on 2026-08-13 twelve CRLF-committed production modules passed
`ruff check`, `ruff format`, the pre-commit framework and all 103 contract validators —
twice, across two commits. A gate nobody has watched fail is indistinguishable from a gate
that cannot fail, so the negative control below is the load-bearing test here: it stages a
fixture that genuinely carries CRLF and asserts the checker rejects it and names the file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "tools" / "check_crlf_byte_surface.py"
HOOK = REPO_ROOT / ".githooks" / "pre-commit"


def _run(*paths: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the checker against explicit paths, relative to `cwd`."""
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(cwd), *[p.name for p in paths]],
        capture_output=True,
        text=True,
        check=False,
    )


def test_negative_control_crlf_fixture_is_rejected(tmp_path: Path) -> None:
    """A file carrying CRLF must fail the gate, and the failure must name the file.

    This is the watched failure. Written with `newline=""` so Python performs no translation
    of its own and the fixture's bytes are unambiguous.
    """
    fixture = tmp_path / "crlf_fixture.py"
    fixture.write_bytes(b"x = 1\r\ny = 2\r\n")
    assert fixture.read_bytes().count(b"\r\n") == 2, "fixture must actually contain CRLF"

    result = _run(fixture, cwd=tmp_path)

    assert result.returncode == 1, f"gate did not fire on CRLF: {result.stdout}{result.stderr}"
    assert "crlf_fixture.py" in result.stderr, "failure must name the offending file"
    assert "2 CRLF pair(s)" in result.stderr, "failure must report the byte-pair count"


def test_positive_control_lf_file_passes(tmp_path: Path) -> None:
    """An LF file must pass, or the gate is vacuously strict rather than correct."""
    fixture = tmp_path / "lf_fixture.py"
    fixture.write_bytes(b"x = 1\ny = 2\n")

    result = _run(fixture, cwd=tmp_path)

    assert result.returncode == 0, f"gate fired on clean LF: {result.stdout}{result.stderr}"


def test_lone_cr_is_not_counted(tmp_path: Path) -> None:
    """A bare CR is not a CRLF pair; counting bytes must not drift into counting CRs.

    During the original diagnosis `grep -c $'\\r$'` gave the wrong answer in both directions,
    which is why detection counts the pair explicitly rather than matching a line ending.
    """
    fixture = tmp_path / "cr_only.txt"
    fixture.write_bytes(b"a\rb\rc\n")

    result = _run(fixture, cwd=tmp_path)

    assert result.returncode == 0, f"lone CR must not be reported as CRLF: {result.stderr}"


def test_gate_is_wired_into_the_tracked_pre_commit_hook() -> None:
    """An unwired checker is the `.git/hooks` failure shape again — enforcement that never runs."""
    hook = HOOK.read_text(encoding="utf-8")
    assert "check_crlf_byte_surface.py" in hook, "the CRLF gate must be invoked by .githooks/pre-commit"
    assert "Gate 1b" in hook, "the gate must be documented in the hook's gate list"


def test_gate_runs_after_the_ruff_gate() -> None:
    """Ordering is load-bearing: ruff-format re-emitted CRLF *after* normalisation in the incident.

    A CRLF check placed before gate 1 would validate bytes that gate 1 then rewrites.
    """
    hook = HOOK.read_text(encoding="utf-8")
    ruff_index = hook.index("# Gate 1 — ruff")
    crlf_index = hook.index("# Gate 1b — CRLF")
    assert ruff_index < crlf_index, "the CRLF gate must run after ruff, not before it"


def test_checker_source_is_itself_lf() -> None:
    """A CRLF checker committed as CRLF would be self-refuting."""
    assert CHECKER.read_bytes().count(b"\r\n") == 0
    assert HOOK.read_bytes().count(b"\r\n") == 0
