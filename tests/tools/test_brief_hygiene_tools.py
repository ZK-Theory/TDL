# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign F)
# Purpose: Controls for the two mechanical brief-hygiene checks: cited paths must resolve on the
# base ref, and formatter collateral must be shown semantics-preserving rather than assumed.
"""Controls for ``tools/check_brief_paths.py`` and ``tools/ast_equivalence.py``.

Obs 2026-09-14-handoff-cited-at-a-path-only-an-unmerged-pr-contains: a dispatch cited a handoff that
existed only on an open docs PR branch, and finding it cost a repo-wide ``git log --all`` search.
Obs 2026-09-08-formatter-collateral-needs-a-semantics-proof: a one-line edit triggered a 15-file
reformat, "formatters are safe" was assumed, and one file's docstring whitespace changed the AST.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIEF_PATHS = REPO_ROOT / "tools" / "check_brief_paths.py"
AST_EQUIVALENCE = REPO_ROOT / "tools" / "ast_equivalence.py"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr}"
    return completed.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """main holds `docs/plan.md` and `tools/a.py`; branch `docs/handoff` alone adds the handoff."""
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "tools").mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "brief-test@example.invalid")
    _git(root, "config", "user.name", "Brief Test")
    (root / "docs" / "plan.md").write_text("plan\n", newline="\n")
    (root / "tools" / "a.py").write_text('def f():\n    """Say hi."""\n    return 1\n', newline="\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-verify", "-m", "seed")
    _git(root, "checkout", "-q", "-b", "docs/handoff")
    (root / "docs" / "handoff.md").write_text("handoff\n", newline="\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-verify", "-m", "handoff on a branch only")
    _git(root, "checkout", "-q", "main")
    return root


def _brief(repo: Path, text: str) -> Path:
    path = repo.parent / "brief.md"
    path.write_text(text, newline="\n")
    return path


def _check(repo: Path, brief: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BRIEF_PATHS), str(brief), "--ref", "main", "--repo-root", str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_path_present_only_on_an_unmerged_branch_is_named_with_its_branch(repo: Path) -> None:
    result = _check(repo, _brief(repo, "Read `docs/handoff.md` first, then `docs/plan.md`.\n"))

    assert result.returncode == 1
    assert "docs/handoff.md: absent from main; present on docs/handoff" in result.stderr
    assert "docs/plan.md" not in result.stderr


def test_a_path_on_no_ref_at_all_is_reported_missing(repo: Path) -> None:
    result = _check(repo, _brief(repo, "See `docs/never-written.md`.\n"))

    assert result.returncode == 1
    assert "docs/never-written.md: absent from main and from every branch" in result.stderr


def test_resolvable_paths_placeholders_and_non_paths_pass(repo: Path) -> None:
    """Positive controls: real paths, a directory, placeholders, globs, and code spans that are not paths."""
    text = (
        "Edit `tools/a.py` and `docs/plan.md` in `docs/`. Output goes to `results/<run>/x.json` and "
        "`papers/*/draft.md`. Run `uv run pytest -q` and set `core.hooksPath`.\n"
    )
    result = _check(repo, _brief(repo, text))

    assert result.returncode == 0, result.stderr
    assert "3 cited path(s) resolve on main" in result.stdout


def test_refs_branch_namespaces_and_brief_relative_paths_are_not_false_positives(repo: Path) -> None:
    """Found running the checker on the real Phase 4 remainder handoff: three false alarms.

    `origin/main`-style refs and `docs/`-style branch namespaces are not file citations, and a
    handoff under `docs/` citing `plan.md` relative to its own directory is correct.
    """
    _git(repo, "branch", "codex/topic")
    brief = repo / "docs" / "notes" / "brief.md"
    brief.parent.mkdir()
    (repo / "docs" / "notes" / "sub").mkdir()
    (repo / "docs" / "notes" / "sub" / "local.md").write_text("x\n", newline="\n")
    brief.write_text("x\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "brief")
    brief.write_text(
        "Base on `refs/heads/main`, branch from `codex/`, see `sub/local.md` and `../plan.md`.\n", newline="\n"
    )

    result = _check(repo, brief)

    assert result.returncode == 0, result.stderr


def test_a_path_resolving_only_under_an_ancestor_of_the_brief_is_reported(repo: Path) -> None:
    """Only the repository root and the brief's own directory are readings a Worker would try."""
    brief = repo / "docs" / "notes" / "brief.md"
    brief.parent.mkdir()
    (repo / "docs" / "notes" / "local.md").write_text("x\n", newline="\n")
    brief.write_text("x\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "brief")
    brief.write_text("See `notes/local.md`.\n", newline="\n")

    result = _check(repo, brief)

    assert result.returncode == 1
    assert "notes/local.md: not at the repository root or beside the brief" in result.stderr
    assert "docs/notes/local.md" in result.stderr, "the full path it probably meant is named"


@pytest.mark.parametrize("anchor", [":2", ":1-2", "#L2", "#L1-L2"])
def test_line_anchors_are_dropped_before_resolving(repo: Path, anchor: str) -> None:
    result = _check(repo, _brief(repo, f"See `tools/a.py{anchor}`.\n"))

    assert result.returncode == 0, result.stderr


def test_root_level_files_are_checked(repo: Path) -> None:
    """A slash-less file name was ignored, so a missing root file passed as '0 cited path(s)'."""
    (repo / "AGENTS.md").write_text("x\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "agents")

    missing = _check(repo, _brief(repo, "Read `AGENTS.md` and `MISSING.md`.\n"))
    generic = _check(repo, _brief(repo, "Every `plan.md` must say so; then read `AGENTS.md`.\n"))

    assert missing.returncode == 1
    assert "MISSING.md: absent from main" in missing.stderr
    assert "AGENTS.md" not in missing.stderr
    assert generic.returncode == 0, "a bare name some file on the ref carries is a kind of file, not a citation"


def test_a_branch_qualified_citation_is_accepted(repo: Path) -> None:
    """The remedy the tool prints must clear it: name the holding branch on the same line."""
    result = _check(repo, _brief(repo, "Read `docs/handoff.md` from branch `docs/handoff`.\n"))

    assert result.returncode == 0, result.stderr


def test_naming_a_branch_that_does_not_hold_the_path_does_not_qualify_it(repo: Path) -> None:
    _git(repo, "branch", "docs/other", "main")
    result = _check(repo, _brief(repo, "Read `docs/handoff.md` from branch `docs/other`.\n"))

    assert result.returncode == 1


def test_branch_qualification_is_per_mention(repo: Path) -> None:
    """A branch named beside a later mention does not qualify an earlier, bare instruction."""
    text = "Read `docs/handoff.md` first.\nIt lives on: `docs/handoff.md` from branch `docs/handoff`.\n"
    assert _check(repo, _brief(repo, text)).returncode == 1


def test_a_branch_whose_tip_deleted_the_path_is_not_named_as_holding_it(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "docs/vanished")
    (repo / "docs" / "vanished.md").write_text("x\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "add")
    _git(repo, "rm", "-q", "docs/vanished.md")
    _git(repo, "commit", "-q", "--no-verify", "-m", "delete")
    _git(repo, "checkout", "-q", "main")

    result = _check(repo, _brief(repo, "Read `docs/vanished.md`.\n"))

    assert result.returncode == 1
    assert "present on docs/vanished" not in result.stderr
    assert "no branch tip" in result.stderr


def test_an_ignored_citation_must_exist_in_the_checkout(repo: Path) -> None:
    """Ignored paths never live on a ref, so they are checked on disk rather than waved through."""
    (repo / ".gitignore").write_text("data/\n", newline="\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "--no-verify", "-m", "ignore data")

    missing = _check(repo, _brief(repo, "Input: `data/never.csv`.\n"))
    (repo / "data").mkdir()
    (repo / "data" / "present.csv").write_text("x\n", newline="\n")
    present = _check(repo, _brief(repo, "Input: `data/present.csv`.\n"))

    assert missing.returncode == 1 and "git-ignored, never tracked" in missing.stderr
    assert present.returncode == 0, present.stderr


def test_an_ignored_pattern_does_not_hide_a_path_held_only_on_a_branch(repo: Path) -> None:
    """This repository ignores `docs/*` and force-adds tracked docs: the motivating case must still be named."""
    (repo / ".gitignore").write_text("docs/*\n", newline="\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "--no-verify", "-m", "ignore docs")

    result = _check(repo, _brief(repo, "Read `docs/handoff.md`.\n"))

    assert result.returncode == 1
    assert "docs/handoff.md: absent from main; present on docs/handoff" in result.stderr


def test_declared_outputs_need_not_exist_yet(repo: Path) -> None:
    """A test the task will author is an output, not a prerequisite; the brief declares it explicitly."""
    inline = _check(repo, _brief(repo, "Author the test in `tests/test_new.py` (new), then run it.\n"))
    section = _check(repo, _brief(repo, "## Deliverables\n\n- `results/h2_2026-09-26.json`\n- `tests/test_new.py`\n"))
    undeclared = _check(repo, _brief(repo, "Author the test in `tests/test_new.py`.\n"))

    assert inline.returncode == 0, inline.stderr
    assert section.returncode == 0, section.stderr
    assert undeclared.returncode == 1, "an undeclared missing path is still a missing prerequisite"


def test_vault_relative_citations_resolve_under_the_vault_root(repo: Path, tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "04-Methods").mkdir(parents=True)
    (vault / "04-Methods" / "Computational-Log.md").write_text("log\n", newline="\n")
    brief = _brief(repo, "Log it in `04-Methods/Computational-Log.md`.\n")

    without = _check(repo, brief)
    with_vault = subprocess.run(
        [
            sys.executable,
            str(BRIEF_PATHS),
            str(brief),
            "--ref",
            "main",
            "--repo-root",
            str(repo),
            "--vault-root",
            str(vault),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert without.returncode == 1
    assert with_vault.returncode == 0, with_vault.stderr


def test_an_invalid_ref_fails_even_with_no_citations(repo: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(BRIEF_PATHS),
            str(_brief(repo, "No paths here.\n")),
            "--ref",
            "mian",
            "--repo-root",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "does not resolve to a commit" in result.stderr


def test_paths_with_spaces_are_checked_but_command_lines_are_not(repo: Path) -> None:
    missing = _check(repo, _brief(repo, "See `docs/Research Papers/missing.md`.\n"))
    command = _check(repo, _brief(repo, "Run `uv run python tools/a.py` then `git -C docs/x status`.\n"))

    assert missing.returncode == 1 and "docs/Research Papers/missing.md" in missing.stderr
    assert command.returncode == 0, command.stderr


def test_slash_bearing_prose_and_formulas_are_not_citations(repo: Path) -> None:
    result = _check(repo, _brief(repo, "Wrap it in `try/except`; the p-value is `p=(r+1)/(B+1)`, and `and/or`.\n"))
    assert result.returncode == 0, result.stderr


def test_dispatch_check_requires_a_brief_or_a_stated_reason(repo: Path) -> None:
    from shared.manager_dispatch_check import brief_checks

    (none,) = brief_checks([], None, repo, "main")
    (waived,) = brief_checks([], "sequential hot-fix, prompt written inline", repo, "main")

    assert none.name == "brief-paths" and not none.ok
    assert waived.ok and "sequential hot-fix" in waived.detail


def test_dispatch_check_defaults_to_the_workspace_head(repo: Path) -> None:
    """A stacked branch not cut from main is checked on the commit the Worker actually starts from."""
    from shared.manager_dispatch_check import brief_checks, workspace_head

    _git(repo, "checkout", "-q", "docs/handoff")
    brief = [str(_brief(repo, "Read `docs/handoff.md`.\n"))]

    assert brief_checks(brief, None, repo, workspace_head(repo))[0].ok
    assert not brief_checks(brief, None, repo, "main")[0].ok


def test_dispatch_check_reports_brief_paths_as_a_named_check(repo: Path) -> None:
    from shared.manager_dispatch_check import check_brief_paths

    missing = check_brief_paths(_brief(repo, "Read `docs/handoff.md`.\n"), repo, "main")
    clean = check_brief_paths(_brief(repo, "Read `docs/plan.md`.\n"), repo, "main")

    assert missing.name == "brief-paths" and not missing.ok
    assert "docs/handoff" in missing.detail
    assert clean.ok


def _equivalence(repo: Path, *files: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AST_EQUIVALENCE), "--base", "HEAD", *files],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_pure_reformat_is_equivalent(repo: Path) -> None:
    (repo / "tools" / "a.py").write_text('def f(  ):\n    """Say hi."""\n    return (1)\n', newline="\n")

    result = _equivalence(repo, "tools/a.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EQUIVALENT  tools/a.py" in result.stdout


def test_a_docstring_whitespace_change_is_not_equivalent(repo: Path) -> None:
    """The motivating case: one of fifteen reformatted files changed a docstring, which the AST sees."""
    (repo / "tools" / "a.py").write_text('def f():\n    """Say  hi."""\n    return 1\n', newline="\n")

    result = _equivalence(repo, "tools/a.py")

    assert result.returncode == 1
    assert "CHANGED     tools/a.py" in result.stdout


def test_a_file_new_since_the_base_is_reported_not_skipped(repo: Path) -> None:
    (repo / "tools" / "b.py").write_text("x = 1\n", newline="\n")

    result = _equivalence(repo, "tools/b.py")

    assert result.returncode == 1
    assert "NEW         tools/b.py" in result.stdout


def test_an_unreadable_brief_is_a_failed_check_not_a_traceback(repo: Path) -> None:
    """A mistyped path or a non-UTF-8 file raised from ``read_text`` and printed a traceback.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #305): the failure must be a check
    result a dispatch can read, naming the file.
    """
    missing = _check(repo, repo.parent / "no-such-brief.md")
    binary = repo.parent / "binary-brief.md"
    binary.write_bytes(b"\xff\xfe\x00 not utf-8 \x80")
    undecodable = _check(repo, binary)

    for result, name in ((missing, "no-such-brief.md"), (undecodable, "binary-brief.md")):
        assert result.returncode == 1, result.stderr
        assert "Traceback" not in result.stderr, result.stderr
        assert "cannot read brief" in result.stderr and name in result.stderr


def test_the_dispatch_gate_reports_an_unreadable_brief_as_a_failed_check(repo: Path) -> None:
    """The same unreadable brief must fail the named dispatch check, not raise through the Manager's run."""
    from shared.manager_dispatch_check import check_brief_paths

    check = check_brief_paths(repo.parent / "no-such-brief.md", repo, "main")

    assert not check.ok
    assert "cannot read brief" in check.detail


def test_branch_qualification_is_tried_before_the_suffix_suggestion(repo: Path) -> None:
    """A citation that names the branch holding it was rejected because a same-named file lives deeper on main.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #305): the suffix suggestion ran
    first and ``continue``d, so the branch-qualified reading never got a turn.
    """
    (repo / "vendor" / "docs").mkdir(parents=True)
    (repo / "vendor" / "docs" / "h2.md").write_text("vendored\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "vendored copy on main")
    _git(repo, "checkout", "-q", "docs/handoff")
    (repo / "docs" / "h2.md").write_text("second handoff\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "h2 on the branch")
    _git(repo, "checkout", "-q", "main")

    qualified = _check(repo, _brief(repo, "Read `docs/h2.md` from branch `docs/handoff`.\n"))
    unqualified = _check(repo, _brief(repo, "Read `docs/h2.md`.\n"))

    assert qualified.returncode == 0, qualified.stderr
    assert unqualified.returncode == 1
    assert "cite the full path (vendor/docs/h2.md)" in unqualified.stderr, "the suggestion survives, last"


def test_branch_discovery_reads_the_brief_relative_reading(repo: Path) -> None:
    """The branch lookup used the root reading alone, so a brief-relative citation was 'on no branch at all'.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #305).
    """
    brief = repo / "docs" / "notes" / "brief.md"
    brief.parent.mkdir()
    brief.write_text("x\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "brief")
    _git(repo, "checkout", "-q", "-b", "docs/notes-branch")
    (repo / "docs" / "notes" / "sub").mkdir()
    (repo / "docs" / "notes" / "sub" / "h3.md").write_text("beside the brief\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "h3 beside the brief, on a branch")
    _git(repo, "checkout", "-q", "main")
    brief.write_text("Read `sub/h3.md`.\n", newline="\n")

    result = _check(repo, brief)

    assert result.returncode == 1
    assert "sub/h3.md: absent from main; present on docs/notes-branch" in result.stderr, result.stderr


def test_every_branch_holding_the_path_is_named_not_only_those_containing_its_last_commit(repo: Path) -> None:
    """``branch --contains <last commit>`` named only branches descended from the newest touch of the path."""
    for name in ("alpha", "beta"):
        _git(repo, "checkout", "-q", "-b", name, "main")
        (repo / "docs" / "d.md").write_text(f"written on {name}\n", newline="\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "--no-verify", "-m", f"d on {name}")
    _git(repo, "checkout", "-q", "main")

    result = _check(repo, _brief(repo, "Read `docs/d.md`.\n"))

    assert result.returncode == 1
    assert "alpha" in result.stderr and "beta" in result.stderr, result.stderr


def test_an_ignored_citation_is_checked_against_every_reading(repo: Path) -> None:
    """The ignore and existence tests used the root reading alone, so an ignored file beside the brief failed.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #305).
    """
    brief = repo / "docs" / "notes" / "brief.md"
    brief.parent.mkdir()
    (repo / ".gitignore").write_text("docs/notes/*.csv\n", newline="\n")
    brief.write_text("x\n", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "brief and ignore rule")
    brief.write_text("Input: `local-data.csv`.\n", newline="\n")

    missing = _check(repo, brief)
    (repo / "docs" / "notes" / "local-data.csv").write_text("x\n", newline="\n")
    present = _check(repo, brief)

    assert missing.returncode == 1
    assert "git-ignored, never tracked, and not present" in missing.stderr, missing.stderr
    assert present.returncode == 0, present.stderr
