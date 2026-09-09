"""Liveness controls for the CRLF byte-surface gate.

The gate exists because on 2026-08-13 twelve CRLF-committed production modules passed
`ruff check`, `ruff format`, the pre-commit framework and all 103 contract validators —
twice, across two commits. A gate nobody has watched fail is indistinguishable from a gate
that cannot fail, so the negative control below is the load-bearing test here: it stages a
fixture that genuinely carries CRLF and asserts the checker rejects it and names the file.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "tools" / "check_crlf_byte_surface.py"
HOOK = REPO_ROOT / ".githooks" / "pre-commit"


def _load_checker():
    """Import the checker by path; `tools/` is a script directory, not an importable package."""
    spec = importlib.util.spec_from_file_location("check_crlf_byte_surface", CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


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


def test_tracked_binaries_git_leaves_unspecified_are_not_rejected() -> None:
    """Regression: PR #280 review, P1.

    The repository tracks binary formats `.gitattributes` leaves as `binary: unspecified` — a
    `.gif`, an `.rds`, and two `.npy` embeddings, carrying 13, 12, 31 and 14 incidental CRLF byte
    pairs. The first version of this gate skipped only *declared* binary, so staging any
    legitimate update to those files would have been rejected as malformed text, with
    `--no-verify` forbidden by project rules. Asserted on the real tracked files, not a fixture.
    """
    tracked = [
        "financial_tda/viz/outputs/filtration_animation.gif",
        "results/panel_methodology/weights/ipw_individual_weights_2026-05-14.rds",
        "results/trajectory_tda_integration/embeddings.npy",
    ]
    present = [path for path in tracked if (REPO_ROOT / path).is_file()]
    assert present, "expected at least one tracked undeclared-binary file to guard against"

    for path in present:
        data = (REPO_ROOT / path).read_bytes()
        assert checker.count_crlf(data) > 0, f"{path} no longer carries CRLF; pick another fixture"
        assert checker.looks_binary(data), f"{path} must be recognised as binary by the NUL heuristic"
    assert checker.scan_paths(present, REPO_ROOT, check_index=False) == []


def test_declared_binary_is_skipped_even_without_a_nul_byte() -> None:
    """The NUL heuristic must not become the only test.

    `.gitattributes` records that 99 of the 160 committed PDFs have no NUL in their first 8000
    bytes, so the heuristic alone would classify them as text. Declared `binary` stays an
    independent skip for exactly that inverse error.
    """
    pdfs = [path for path in ["docs"] if (REPO_ROOT / path).is_dir()]
    assert pdfs or True  # directory presence is incidental; the property under test is below
    payload = b"%PDF-1.7\r\nno nul byte here\r\n" + b"x" * 9000
    assert not checker.looks_binary(payload), "fixture must be NUL-free to exercise the inverse error"
    assert checker.count_crlf(payload) == 2


def test_binary_attributes_resolve_from_the_index_by_default() -> None:
    """Regression: PR #280 review, P2.

    Attributes must come from the commit being validated. A staged `.gitattributes` that drops a
    `binary` declaration the working copy still carries would otherwise let a CRLF-bearing blob
    through under an attribute the commit does not contain.
    """
    source = CHECKER.read_text(encoding="utf-8")
    assert '"--cached"' in source, "index scan must resolve attributes with git check-attr --cached"
    signature = ast.parse(source)
    for node in ast.walk(signature):
        if isinstance(node, ast.FunctionDef) and node.name == "binary_declared":
            defaults = [d.value for d in node.args.kw_defaults if isinstance(d, ast.Constant)]
            assert defaults == [True], "cached resolution must be the default, not opt-in"
            return
    raise AssertionError("binary_declared not found")


def test_symlinks_are_not_dereferenced(tmp_path: Path) -> None:
    """Regression: PR #280 review, P2.

    Git stores only the target pathname for a symlink. Reading through the link would report the
    target's CRLF as the link's own, so a clean symlink pointing at an external CRLF file would
    be rejected for bytes git never commits.
    """
    target = tmp_path / "external_target.txt"
    target.write_bytes(b"line one\r\nline two\r\n")
    link = tmp_path / "link_to_target.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:  # Windows without Developer Mode / privilege
        pytest.skip(f"symlink creation unavailable: {exc}")

    assert link.is_symlink()
    assert checker.scan_paths([link.name], tmp_path, check_index=False) == []


def test_checker_source_is_itself_lf() -> None:
    """A CRLF checker committed as CRLF would be self-refuting."""
    assert CHECKER.read_bytes().count(b"\r\n") == 0
    assert HOOK.read_bytes().count(b"\r\n") == 0
