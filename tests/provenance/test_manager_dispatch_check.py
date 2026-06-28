# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Unit tests for the dispatch-readiness gate's pure-ish checks
#   (report-bus, worktree mode, render verdict). The end-to-end git/subprocess
#   paths are exercised by running the CLI; these lock the decision logic.
"""Tests for shared.manager_dispatch_check."""

from __future__ import annotations

from pathlib import Path

from shared.manager_dispatch_check import (
    Check,
    _resolve_workspace,
    check_report_bus,
    check_worktree,
    render,
)


def test_render_verdict_reflects_checks() -> None:
    """PASS only when every check is ok; FAIL otherwise."""
    ok = render("a", "run/x", "parallel", [Check("c1", True, "ok")])
    assert "**PASS**" in ok
    assert "- [x] **c1**" in ok
    bad = render("a", "run/x", "parallel", [Check("c1", True, "ok"), Check("c2", False, "no")])
    assert "**FAIL**" in bad
    assert "- [ ] **c2**" in bad


def test_check_report_bus(tmp_path: Path) -> None:
    """Absent or empty report bus is ok; a non-empty prior report is not."""
    bus = tmp_path / ".apm" / "bus" / "agent-x"
    bus.mkdir(parents=True)
    assert check_report_bus(tmp_path, "agent-x").ok  # absent

    (bus / "report.md").write_text("   \n", encoding="utf-8")
    assert check_report_bus(tmp_path, "agent-x").ok  # whitespace-only == cleared

    (bus / "report.md").write_text("# prior report\nstuff", encoding="utf-8")
    assert not check_report_bus(tmp_path, "agent-x").ok  # uncleared


def test_resolve_workspace_relative_not_doubled(tmp_path: Path) -> None:
    """A relative --workspace resolves against proj_root, never doubled.

    Regression for the path-doubling bug: a relative ``--workspace`` was kept
    relative, then check_contracts ran with cwd=workspace AND a
    workspace-relative hook path, yielding
    ``.apm/worktrees/X/.apm/worktrees/X/...``.
    """
    rel = ".apm/worktrees/run-x"
    ws = _resolve_workspace(rel, "run/x", {}, tmp_path)
    assert ws.is_absolute()
    assert ws == (tmp_path / ".apm" / "worktrees" / "run-x").resolve()
    assert str(ws).count("run-x") == 1  # the segment appears exactly once


def test_resolve_workspace_explicit_worktree_and_fallback(tmp_path: Path) -> None:
    """Absolute --workspace is preserved; else the worktree, else proj_root."""
    abs_ws = (tmp_path / "abs").resolve()
    assert _resolve_workspace(str(abs_ws), "run/x", {}, tmp_path) == abs_ws

    wt = str((tmp_path / "wt").resolve())
    assert _resolve_workspace(None, "run/x", {"run/x": wt}, tmp_path) == Path(wt).resolve()

    assert _resolve_workspace(None, "run/x", {}, tmp_path) == tmp_path.resolve()


def test_check_worktree_mode(tmp_path: Path) -> None:
    """Sequential needs no worktree; parallel without one fails."""
    seq = check_worktree(tmp_path, "run/x", "sequential")
    assert all(c.ok for c in seq)

    # tmp_path is not a git repo -> no worktree registered for the branch.
    par = check_worktree(tmp_path, "run/x", "parallel")
    assert not par[0].ok
    assert "no worktree" in par[0].detail
