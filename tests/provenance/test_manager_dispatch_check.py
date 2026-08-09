# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Unit tests for the dispatch-readiness gate's pure-ish checks
#   (report-bus, worktree mode, render verdict). The end-to-end git/subprocess
#   paths are exercised by running the CLI; these lock the decision logic.
"""Tests for shared.manager_dispatch_check."""

from __future__ import annotations

import subprocess
from pathlib import Path

from shared.manager_dispatch_check import (
    Check,
    _resolve_workspace,
    check_report_bus,
    check_state_manifest,
    check_worktree,
    check_workspace_binding,
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


def test_parallel_workspace_must_equal_branch_owned_worktree(tmp_path: Path) -> None:
    """A detached duplicate workspace cannot impersonate the branch owner."""
    owner = (tmp_path / "owner").resolve()
    duplicate = (tmp_path / "duplicate").resolve()
    owner.mkdir()
    duplicate.mkdir()
    mapping = {"run/x": str(owner)}

    assert check_workspace_binding("run/x", "parallel", owner, mapping).ok
    mismatch = check_workspace_binding("run/x", "parallel", duplicate, mapping)
    assert not mismatch.ok
    assert str(owner) in mismatch.detail
    assert str(duplicate) in mismatch.detail


def test_state_manifest_fully_valid_and_existing_deliverable_warns(tmp_path: Path) -> None:
    """A valid manifest runs every predicate; completed prior work warns only."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "done.txt").write_text("complete", encoding="utf-8")
    (tmp_path / "input.csv").write_text("x", encoding="utf-8")
    (tmp_path / "contract.yaml").write_text("id: contract-a\npending: false\n", encoding="utf-8")
    manifest = tmp_path / "state.yaml"
    manifest.write_text(
        """
task_id: task-a
deliverables:
  - path: done.txt
    root: worktree
    owner_task: task-a
    completion_predicate: [python, -c, "import pathlib; assert pathlib.Path('done.txt').read_text() == 'complete'"]
blockers:
  - id: live
    check: [python, -c, "raise SystemExit(0)"]
planned_contracts:
  - id: contract-a
    path: contract.yaml
    root: worktree
    ready_status: pending=false
inputs:
  - path: input.csv
    root: worktree
outputs:
  - path: output/new.json
    root: worktree
""",
        encoding="utf-8",
    )
    checks = check_state_manifest(manifest, tmp_path, tmp_path)
    assert any(c.name == "state:deliverable:done.txt" and c.advisory for c in checks)
    assert next(c for c in checks if c.name == "state:blocker:live").detail == "blocker remains live"
    assert next(c for c in checks if c.name == "state:contract:contract-a").detail == "contract materialized and ready"
    assert next(c for c in checks if c.name == "state:input:input.csv").detail == "input resolved"
    assert next(c for c in checks if c.name == "state:output:output/new.json").detail == "output is trackable"
    assert all(c.ok for c in checks)  # warning-first never blocks dispatch


def test_state_manifest_required_negative_controls(tmp_path: Path) -> None:
    """Stale blocker, missing contract, wrong root, and ignored output all warn."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    manifest = tmp_path / "state.yaml"
    manifest.write_text(
        """
task_id: task-a
deliverables: []
blockers:
  - id: stale
    check: [python, -c, "raise SystemExit(1)"]
planned_contracts:
  - id: missing
    path: contracts/missing.yaml
    root: worktree
    ready_status: pending=false
inputs:
  - path: input.csv
    root: nowhere
outputs:
  - path: ignored/result.json
    root: worktree
""",
        encoding="utf-8",
    )
    checks = check_state_manifest(manifest, tmp_path, tmp_path)
    for name in (
        "state:blocker:stale",
        "state:contract:missing",
        "state:input:input.csv",
        "state:output:ignored/result.json",
    ):
        check = next(c for c in checks if c.name == name)
        assert check.ok and check.advisory and "WARNING:" in check.detail


def test_state_manifest_foreign_owner_and_malformed_sections_do_not_suppress_dispatch(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "done.txt").write_text("complete", encoding="utf-8")
    (tmp_path / "incomplete.txt").write_text("partial", encoding="utf-8")
    (tmp_path / "broken.yaml").write_text("x: [", encoding="utf-8")
    manifest = tmp_path / "state.yaml"
    manifest.write_text(
        """
task_id: task-a
deliverables:
  - malformed
  - path: done.txt
    root: worktree
    owner_task: task-b
    completion_predicate: [python, -c, "raise SystemExit(0)"]
  - path: incomplete.txt
    root: worktree
    owner_task: task-a
    completion_predicate: [python, -c, "raise SystemExit(1)"]
blockers: not-a-list
planned_contracts:
  - malformed
  - id: broken
    path: broken.yaml
    root: worktree
    ready_status: pending=false
inputs: []
outputs: []
""",
        encoding="utf-8",
    )
    checks = check_state_manifest(manifest, tmp_path, tmp_path)
    assert next(c for c in checks if c.name == "state:deliverable:done.txt").detail == (
        "deliverable belongs to another task; fresh dispatch retained"
    )
    assert (
        "deliverable exists but is incomplete"
        in next(c for c in checks if c.name == "state:deliverable:incomplete.txt").detail
    )
    assert next(c for c in checks if c.name == "state:deliverable").advisory
    assert next(c for c in checks if c.name == "state:blockers").advisory
    assert next(c for c in checks if c.name == "state:contract").advisory
    assert next(c for c in checks if c.name == "state:contract:broken").advisory


def test_state_manifest_rejects_shell_strings_and_paths_outside_declared_roots(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "done.txt").write_text("complete", encoding="utf-8")
    manifest = tmp_path / "state.yaml"
    manifest.write_text(
        f"""
task_id: task-a
deliverables:
  - path: done.txt
    root: worktree
    owner_task: task-a
    completion_predicate: python -c "raise SystemExit(0)" && echo unsafe
blockers:
  - id: unsafe
    check: echo live && echo shell
planned_contracts:
  - id: escaped
    path: {tmp_path.parent.as_posix()}/outside.yaml
    root: worktree
    ready_status: pending=false
inputs: []
outputs:
  - path: ../outside.json
    root: worktree
""",
        encoding="utf-8",
    )
    checks = check_state_manifest(manifest, tmp_path, tmp_path)
    assert (
        "predicate must be a non-empty argv list"
        in next(c for c in checks if c.name == "state:deliverable:done.txt").detail
    )
    assert (
        "predicate must be a non-empty argv list" in next(c for c in checks if c.name == "state:blocker:unsafe").detail
    )
    assert next(c for c in checks if c.name == "state:contract:escaped").advisory
    assert next(c for c in checks if c.name == "state:output:../outside.json").advisory


def test_state_manifest_closes_lanes_registries_and_derived_field_sources(tmp_path: Path) -> None:
    """Prompt-ready means every lane and production dependency is resolved."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "registry.py").write_text("REQUIRED_REGISTRY = {}\n", encoding="utf-8")
    manifest = tmp_path / "state.yaml"
    manifest.write_text(
        """
task_id: task-a
deliverables: []
blockers: []
planned_contracts: []
inputs: []
outputs: []
lanes:
  - id: author
    completion_predicate: [python, -c, "raise SystemExit(0)"]
    next_gate: independent-review
  - id: integration
    completion_predicate: [python, -c, "raise SystemExit(1)"]
    next_gate: merge
registries:
  - id: lifecycle-bindings
    path: registry.py
    root: worktree
    symbol: REQUIRED_REGISTRY
    disposition: writable
derived_fields:
  - name: content_sha256
    preimage: canonical message content bytes
    semantics: lowercase SHA-256 over the exact preimage
required_fields:
  - name: assurance_pack_id
    source: accepted allocation record
    resolution_check: [python, -c, "raise SystemExit(0)"]
""",
        encoding="utf-8",
    )

    checks = check_state_manifest(manifest, tmp_path, tmp_path)
    author = next(c for c in checks if c.name == "state:lane:author")
    integration = next(c for c in checks if c.name == "state:lane:integration")
    assert author.advisory and "advance to independent-review" in author.detail
    assert not integration.advisory and integration.detail == "lane remains active"
    assert next(c for c in checks if c.name == "state:registry:lifecycle-bindings").detail == (
        "registry dependency resolved (writable)"
    )
    assert next(c for c in checks if c.name == "state:derived-field:content_sha256").detail == (
        "derived-field preimage and semantics declared"
    )
    assert next(c for c in checks if c.name == "state:required-field:assurance_pack_id").detail == (
        "required-field source resolved"
    )


def test_state_manifest_dependency_closure_near_misses_warn(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "registry.py").write_text("OTHER = {}\n", encoding="utf-8")
    manifest = tmp_path / "state.yaml"
    manifest.write_text(
        """
task_id: task-a
lanes:
  - id: author
    completion_predicate: not-an-argv
    next_gate: ""
registries:
  - id: lifecycle-bindings
    path: registry.py
    root: worktree
    symbol: REQUIRED_REGISTRY
    disposition: guessed
derived_fields:
  - name: content_sha256
    preimage: ""
    semantics: ""
required_fields:
  - name: assurance_pack_id
    source: accepted allocation record
    resolution_check: [python, -c, "raise SystemExit(1)"]
""",
        encoding="utf-8",
    )

    checks = check_state_manifest(manifest, tmp_path, tmp_path)
    for name in (
        "state:lane:author",
        "state:registry:lifecycle-bindings",
        "state:derived-field:content_sha256",
        "state:required-field:assurance_pack_id",
    ):
        check = next(c for c in checks if c.name == name)
        assert check.ok and check.advisory and "WARNING:" in check.detail
