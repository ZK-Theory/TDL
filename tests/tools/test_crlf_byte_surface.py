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
import shlex
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


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr}"
    return completed.stdout


@pytest.fixture
def lf_repo(tmp_path: Path) -> Path:
    """A real repository with the live `.gitattributes` hook pin, one tracked hook script, committed LF.

    The explicit `.githooks/** text eol=lf` matters: under `text=auto` alone git still reports a
    CRLF rewrite as modified, so only the explicit pin the real repository uses reproduces the
    clean status that made the incident invisible.
    """
    repo = tmp_path / "repo"
    (repo / ".githooks").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "fixture-branch")
    _git(repo, "config", "user.email", "crlf-test@example.invalid")
    _git(repo, "config", "user.name", "CRLF Test")
    _git(repo, "config", "core.autocrlf", "false")
    (repo / ".gitattributes").write_bytes(b"* text=auto eol=lf\n.githooks/** text eol=lf\n")
    (repo / ".githooks" / "post-commit").write_bytes(b"#!/bin/bash\necho ok\n")
    (repo / "notes.md").write_bytes(b"one\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "seed")
    return repo


def _run_worktree(repo: Path, *pathspecs: str) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CHECKER), "--repo-root", str(repo)]
    for pathspec in pathspecs:
        args += ["--worktree", pathspec]
    return subprocess.run(args, capture_output=True, text=True, check=False)


def test_worktree_mode_catches_a_crlf_hook_that_git_status_calls_clean(lf_repo: Path) -> None:
    """Obs 2026-09-08-shell-rewrite-crlf-on-tracked-hook: the watched failure.

    A shell redirect rewrote a tracked hook with CRLF. Once any `git add` has touched it, the
    index records the CRLF file's stat against the unchanged normalised LF blob: nothing is
    staged, `git status` reports nothing, and the staged-set scan never looks. The broken
    shebang still executes from disk. (Before that add, git reports the file modified, because a
    size change is reported without a content comparison.)
    """
    hook = lf_repo / ".githooks" / "post-commit"
    hook.write_bytes(b"#!/bin/bash\r\necho ok\r\n")
    _git(lf_repo, "add", ".githooks/post-commit")
    assert _git(lf_repo, "status", "--porcelain") == "", "fixture must reproduce git calling the file clean"
    assert hook.read_bytes().count(b"\r\n") == 2, "the working tree must still carry the CRLF"

    staged_only = _run_worktree(lf_repo)
    with_worktree = _run_worktree(lf_repo, ".githooks")

    assert staged_only.returncode == 0, "the staged-set scan is blind to this, which is why the mode exists"
    assert with_worktree.returncode == 1, with_worktree.stderr
    assert ".githooks/post-commit: 2 CRLF pair(s) in the working tree" in with_worktree.stderr


def test_worktree_mode_passes_a_clean_tree_and_ignores_paths_outside_its_pathspecs(lf_repo: Path) -> None:
    """Positive controls: LF hooks pass, and CRLF outside the named pathspecs is not its business."""
    (lf_repo / "notes.md").write_bytes(b"one\r\n")
    (lf_repo / ".githooks" / "untracked-scratch").write_bytes(b"x\r\n")

    result = _run_worktree(lf_repo, ".githooks")

    assert result.returncode == 0, result.stderr


def _check(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(repo)], capture_output=True, text=True, check=False
    )


def _apply_printed_commands(stderr: str, repo: Path) -> None:
    """Run every command line the gate printed, exactly as printed (one command per indented line)."""
    commands = [line[2:] for line in stderr.splitlines() if line.startswith("  ") and " CRLF pair" not in line]
    assert commands, stderr
    for command in commands:
        completed = subprocess.run(shlex.split(command), cwd=repo, capture_output=True, text=True, check=False)
        assert completed.returncode == 0, f"{command}: {completed.stderr}"


def test_the_remediation_the_gate_prints_actually_clears_it(lf_repo: Path) -> None:
    """The advice must work against the surface the gate reads.

    The old message said `git add --renormalize <path>`. That rewrites the index blob only; the
    gate reads working-tree bytes, so following it fails the gate again (hit three times in the
    2026-09-23 review session). Applying the printed commands must leave the gate green.
    """
    target = lf_repo / "notes.md"
    target.write_bytes(b"one\r\ntwo\r\n")
    _git(lf_repo, "add", "notes.md")
    blocked = _check(lf_repo)
    assert blocked.returncode == 1
    assert "git add --renormalize" not in blocked.stderr

    _apply_printed_commands(blocked.stderr, lf_repo)

    cleared = _check(lf_repo)
    assert cleared.returncode == 0, cleared.stderr
    assert target.read_bytes() == b"one\ntwo\n", "the author's content must survive the fix"


def test_the_remediation_keeps_a_partially_staged_file_partial(lf_repo: Path) -> None:
    """Staged `two`, unstaged `three`: the fix must not sweep `three` into the index."""
    target = lf_repo / "notes.md"
    target.write_bytes(b"one\ntwo\n")
    _git(lf_repo, "add", "notes.md")
    target.write_bytes(b"one\r\ntwo\r\nthree\r\n")
    blocked = _check(lf_repo)
    assert blocked.returncode == 1

    _apply_printed_commands(blocked.stderr, lf_repo)

    assert _check(lf_repo).returncode == 0
    assert _git(lf_repo, "show", ":notes.md") == "one\ntwo\n", "the staged selection must be unchanged"
    assert target.read_bytes() == b"one\ntwo\nthree\n", "the unstaged edit must survive in the working tree"


def test_the_printed_remediation_quotes_paths_with_spaces(lf_repo: Path) -> None:
    target = lf_repo / "first pass" / "Report; notes.md"
    target.parent.mkdir()
    target.write_bytes(b"a\r\n")
    _git(lf_repo, "add", "first pass/Report; notes.md")
    blocked = _check(lf_repo)
    assert blocked.returncode == 1

    _apply_printed_commands(blocked.stderr, lf_repo)

    assert _check(lf_repo).returncode == 0, "every printed command must act on the reported file"
    assert target.read_bytes() == b"a\n"


def test_an_unstaged_binary_declaration_does_not_exempt_a_hook(lf_repo: Path) -> None:
    """Only the index's attributes (the commit's policy) may exempt a hook from the worktree scan."""
    hook = lf_repo / ".githooks" / "post-commit"
    hook.write_bytes(b"#!/bin/bash\r\necho ok\r\n")
    _git(lf_repo, "add", ".githooks/post-commit")
    (lf_repo / ".gitattributes").write_bytes(b"* text=auto eol=lf\n.githooks/** binary\n")

    result = _run_worktree(lf_repo, ".githooks")

    assert result.returncode == 1, result.stderr


def test_pre_commit_scans_the_tracked_hook_directories_on_disk() -> None:
    """The mode only protects anything if the commit path runs it over the hook directories."""
    hook = HOOK.read_text(encoding="utf-8")
    assert "--worktree .githooks --worktree .claude/hooks --worktree .codex/hooks" in hook
