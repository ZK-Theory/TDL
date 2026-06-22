# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Unit tests for the dispatch-readiness gate's pure-ish checks
#   (report-bus, worktree mode, render verdict). The end-to-end git/subprocess
#   paths are exercised by running the CLI; these lock the decision logic.
"""Tests for shared.manager_dispatch_check."""

from __future__ import annotations

from pathlib import Path

from shared.manager_dispatch_check import (
    Check,
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


def test_check_worktree_mode(tmp_path: Path) -> None:
    """Sequential needs no worktree; parallel without one fails."""
    seq = check_worktree(tmp_path, "run/x", "sequential")
    assert all(c.ok for c in seq)

    # tmp_path is not a git repo -> no worktree registered for the branch.
    par = check_worktree(tmp_path, "run/x", "parallel")
    assert not par[0].ok
    assert "no worktree" in par[0].detail
