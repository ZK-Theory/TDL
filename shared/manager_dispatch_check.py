#!/usr/bin/env python3
# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Manager-side dispatch-readiness gate. Before issuing a Task Prompt to
#   a Worker bus, the Manager runs this to confirm every dispatch prerequisite is
#   actually on disk — not merely described in the envelope: (1) the feature
#   branch's worktree exists with .env (parallel dispatch); (2) the contracts
#   pass the framework's validate-only gate; (3) the input-provenance ledger is
#   green; (4) the Worker's report bus is cleared. Emits a Dispatch Readiness
#   block to paste into the envelope and exits non-zero if any item fails.
#
#   Authored after three Manager dispatches shipped with prerequisites that were
#   described in the envelope but never created: the academic-writing Wave-1
#   batch (no worktree — the branch was checked out in the main working dir), the
#   panel-statistics batch (no worktree, no contracts — both backfilled only
#   after the User caught it), and the B9 recompute (input data not vintage-
#   coherent). All three are the same failure: no forcing function on dispatch.
"""Dispatch-readiness gate (the Manager-side counterpart of the contract gate).

A Worker's commit hits the contract pre-commit gate; the Manager's dispatch hit
nothing — so worktree/contract/input prerequisites could be skipped by writing a
confident envelope. This gate is that missing forcing function. Run it as the
last step before writing the Task Prompt to the bus; paste its output into the
envelope's **Dispatch Readiness** section (the `dispatch-readiness-guard` hook
refuses a branch-bearing bus write that lacks the section).

Usage::

    uv run python -m shared.manager_dispatch_check \\
        --agent panel-statistics-agent \\
        --branch run/b9-b10-recompute --mode parallel \\
        --provenance-manifest contracts/manifests/input-provenance/b9-om-gmm-inputs.yaml

Exit codes:
    0 — every applicable prerequisite passed; the Task is dispatch-ready.
    1 — at least one prerequisite failed; resolve before issuing the Task.
    2 — usage / framework error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from shared.input_provenance import check_manifest, load_manifest, resolve_proj_root


@dataclass
class Check:
    """One dispatch-readiness line item."""

    name: str
    ok: bool
    detail: str


def _worktree_paths(proj_root: Path) -> dict[str, str]:
    """Map branch name -> worktree path from `git worktree list --porcelain`."""
    try:
        out = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=proj_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}
    mapping: dict[str, str] = {}
    cur_path: str | None = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            cur_path = line[len("worktree ") :].strip()
        elif line.startswith("branch ") and cur_path:
            branch = line[len("branch ") :].strip().removeprefix("refs/heads/")
            mapping[branch] = cur_path
    return mapping


def check_worktree(proj_root: Path, branch: str, mode: str) -> list[Check]:
    """Worktree + .env presence (parallel dispatch only)."""
    if mode != "parallel":
        return [
            Check(
                "worktree",
                True,
                f"sequential dispatch — Worker uses the main working dir on '{branch}' (no worktree required)",
            )
        ]
    registered = _worktree_paths(proj_root)
    wt_path = registered.get(branch)
    expected = proj_root / ".apm" / "worktrees" / branch.replace("/", "-")
    if wt_path is None:
        return [
            Check(
                "worktree",
                False,
                f"parallel dispatch but no worktree is checked out on '{branch}'. "
                f"Create it: git worktree add -b {branch} {expected} <base>",
            )
        ]
    wt = Path(wt_path)
    env = wt / ".env"
    env_ok = env.is_file() and env.stat().st_size > 0
    checks = [Check("worktree", True, f"'{branch}' checked out at {wt}")]
    checks.append(
        Check(
            "worktree.env",
            env_ok,
            f".env present ({env.stat().st_size} B)"
            if env_ok
            else f".env MISSING in {wt} — copy it: cp .env {wt}/.env (uv --env-file fails silently without it)",
        )
    )
    return checks


def check_report_bus(proj_root: Path, agent: str) -> Check:
    """The incoming Worker's report bus must be cleared before dispatch."""
    report = proj_root / ".apm" / "bus" / agent / "report.md"
    if not report.is_file():
        return Check("report-bus", True, f"no stale report ({report} absent)")
    cleared = not report.read_text(encoding="utf-8").strip()
    return Check(
        "report-bus",
        cleared,
        "cleared" if cleared else f"{report} still holds a prior report — clear it before dispatch (truncate -s 0)",
    )


def check_contracts(workspace: Path) -> Check:
    """Run the contract framework's validate-only gate (gates 1+2) in workspace."""
    hook = workspace / ".claude" / "hooks" / "contract_binding_check.py"
    if not hook.is_file():
        return Check("contracts", False, f"contract gate not found at {hook}")
    proc = subprocess.run(
        ["uv", "run", "python", str(hook), "--validate-only"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    msg = tail[-1] if tail else f"exit {proc.returncode}"
    return Check("contracts", proc.returncode == 0, msg)


def check_provenance(manifests: list[Path], repo_root: Path, proj_root: Path) -> list[Check]:
    """Run the input-provenance check on each declared manifest."""
    if not manifests:
        return [Check("input-provenance", True, "no input-data manifest declared")]
    checks: list[Check] = []
    for m in manifests:
        if not m.is_file():
            checks.append(Check(f"provenance:{m.name}", False, f"manifest not found: {m}"))
            continue
        result = check_manifest(load_manifest(m), repo_root, proj_root)
        if result.ok:
            checks.append(Check(f"provenance:{result.manifest_id}", True, "inputs coherent"))
        elif not result.enforced:
            checks.append(
                Check(
                    f"provenance:{result.manifest_id}",
                    False,
                    f"inputs NOT coherent (advisory, enforced:false): {result.violations}",
                )
            )
        else:
            checks.append(
                Check(
                    f"provenance:{result.manifest_id}",
                    False,
                    f"inputs NOT coherent: {result.violations}",
                )
            )
    return checks


def render(agent: str, branch: str, mode: str, checks: list[Check]) -> str:
    """Render the Dispatch Readiness markdown block pasted into the envelope."""
    all_ok = all(c.ok for c in checks)
    verdict = "PASS" if all_ok else "FAIL"
    lines = [
        "## Dispatch Readiness",
        "",
        f"`manager_dispatch_check` — agent **{agent}**, branch `{branch}` ({mode}) — **{verdict}**",
        "",
    ]
    for c in checks:
        mark = "x" if c.ok else " "
        lines.append(f"- [{mark}] **{c.name}** — {c.detail}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Manager dispatch-readiness gate.")
    p.add_argument("--agent", required=True, help="Worker agent slug (bus dir name).")
    p.add_argument("--branch", required=True, help="Feature branch for the dispatch.")
    p.add_argument(
        "--mode",
        choices=["parallel", "sequential"],
        default="parallel",
        help="Dispatch mode (parallel requires a worktree).",
    )
    p.add_argument(
        "--provenance-manifest",
        action="append",
        default=[],
        help="Input-provenance manifest path(s) for the Task's input data.",
    )
    p.add_argument(
        "--workspace",
        default=None,
        help="Dir to run the contract gate in (default: the branch worktree, else PROJ_ROOT).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path.cwd()
    proj_root = resolve_proj_root(repo_root)

    checks: list[Check] = []
    checks.extend(check_worktree(proj_root, args.branch, args.mode))
    checks.append(check_report_bus(proj_root, args.agent))

    wt_map = _worktree_paths(proj_root)
    if args.workspace:
        workspace = Path(args.workspace)
    elif args.branch in wt_map:
        workspace = Path(wt_map[args.branch])
    else:
        workspace = proj_root
    checks.append(check_contracts(workspace))

    manifests = [Path(m) for m in args.provenance_manifest]
    checks.extend(check_provenance(manifests, repo_root, proj_root))

    print(render(args.agent, args.branch, args.mode, checks))
    if all(c.ok for c in checks):
        return 0
    print(
        "\nDispatch-readiness gate FAILED — do not write the Task Prompt to the "
        "bus until every item is green (or sequential dispatch is justified).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
