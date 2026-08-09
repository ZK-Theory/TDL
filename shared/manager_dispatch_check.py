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
        --expected-base <required-prerequisite-ref> \\
        --state-manifest contracts/manifests/dispatch-state/panel-statistics.yaml \\
        --provenance-manifest contracts/manifests/input-provenance/b9-om-gmm-inputs.yaml

Exit codes:
    0 — every applicable prerequisite passed; the Task is dispatch-ready.
    1 — at least one prerequisite failed; resolve before issuing the Task.
    2 — usage / framework error.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from shared.input_provenance import check_manifest, load_manifest, resolve_proj_root


@dataclass
class Check:
    """One dispatch-readiness line item.

    ``advisory`` items (e.g. an ``enforced: false`` provenance manifest) are
    reported but do not fail the gate; they render with a distinct marker.
    """

    name: str
    ok: bool
    detail: str
    advisory: bool = False


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


def check_workspace_binding(
    branch: str,
    mode: str,
    workspace: Path,
    worktrees: dict[str, str],
) -> Check:
    """Require a parallel dispatch to execute in the branch-owning worktree.

    A platform-created task may start detached at the right commit while the
    required branch is already attached elsewhere. Commit equality does not
    make that detached checkout the branch owner, so an explicit ``--workspace``
    must not silently route validation or writes into it.
    """
    if mode != "parallel":
        return Check("workspace-binding", True, "sequential dispatch uses the declared workspace")
    owner_raw = worktrees.get(branch)
    if owner_raw is None:
        return Check("workspace-binding", False, f"branch '{branch}' has no owning worktree")
    owner = Path(owner_raw).resolve()
    actual = workspace.resolve()
    try:
        same = os.path.samefile(owner, actual)
    except (FileNotFoundError, OSError):
        same = os.path.normcase(str(owner)) == os.path.normcase(str(actual))
    if not same:
        return Check(
            "workspace-binding",
            False,
            f"workspace {actual} does not own branch '{branch}'; branch owner is {owner}",
        )
    return Check("workspace-binding", True, f"workspace owns branch '{branch}' ({owner})")


def check_branch_ancestry(workspace: Path, expected_base: str) -> Check:
    """Require the declared prerequisite ref to be an ancestor of workspace HEAD."""
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", expected_base, "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return Check("branch-ancestry", True, f"expected base {expected_base} is an ancestor of HEAD")
    diagnostic = (proc.stderr or proc.stdout).strip()
    suffix = f" ({diagnostic})" if diagnostic else ""
    return Check(
        "branch-ancestry",
        False,
        f"expected base {expected_base} is not an ancestor of workspace HEAD{suffix}",
    )


def _resolve_workspace(
    workspace_arg: str | None,
    branch: str,
    wt_map: dict[str, str],
    proj_root: Path,
) -> Path:
    """Resolve the contract-gate workspace to an ABSOLUTE, normalised path.

    A relative ``--workspace`` is resolved against ``proj_root`` (not the
    process cwd). This matters because ``check_contracts`` runs the gate with
    ``cwd=workspace`` and a *workspace-relative* hook path; a relative workspace
    would resolve the hook inside the already-relative cwd and double the path
    (``.apm/worktrees/X/.apm/worktrees/X/...``). Falls back to the branch
    worktree, then ``proj_root``.

    Args:
        workspace_arg: The raw ``--workspace`` value, or None.
        branch: The dispatch feature branch.
        wt_map: Branch -> worktree path mapping from ``git worktree list``.
        proj_root: The project root (absolute).

    Returns:
        An absolute, normalised workspace directory.
    """
    if workspace_arg:
        ws = Path(workspace_arg)
        workspace = ws if ws.is_absolute() else proj_root / ws
    elif branch in wt_map:
        workspace = Path(wt_map[branch])
    else:
        workspace = proj_root
    return workspace.resolve()


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


def check_hook_gate(workspace: Path) -> Check:
    """Assert the Worker's commit-time contract gate is actually live in workspace.

    R-C — the contract/provenance re-assertion at the Worker's commit — is a
    *passive* gate: nothing runs it, so nothing reports when it is absent. That is
    how it went unnoticed that core.hooksPath was redirected to .githooks on
    2026-04-10 while the validator was installed to .git/hooks/pre-commit on
    2026-05-27, where git never read it: the hook did not fail, it simply never
    ran, for 47 days.

    R-B (this gate) is *active* — a Manager runs it and reads the output — so the
    liveness assertion for R-C belongs here. Passive enforcement is unverifiable
    enforcement; every gate needs a positive liveness signal from somewhere that
    is actually read.

    Liveness only: presence of an executable pre-commit in the directory git will
    actually consult. Running the full gate is check_contracts' job.
    """
    configured = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    hooks_dir = Path(configured) if configured else Path(".git/hooks")
    if not hooks_dir.is_absolute():
        hooks_dir = workspace / hooks_dir

    hook = hooks_dir / "pre-commit"
    where = f"core.hooksPath={configured or '(unset)'} -> {hook}"
    if not hook.is_file():
        return Check(
            "hook-gate",
            False,
            f"NO pre-commit hook where git reads them ({where}) — the Worker's commit-time "
            f"contract gate would silently not run. Fix before dispatch: "
            f"uv run python .claude/hooks/install-git-hooks.py",
        )
    return Check("hook-gate", True, f"pre-commit live ({where})")


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
            # enforced:false -> advisory: reported, but does not block dispatch.
            checks.append(
                Check(
                    f"provenance:{result.manifest_id}",
                    True,
                    f"inputs NOT coherent (advisory, enforced:false): {result.violations}",
                    advisory=True,
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


def _state_root(name: str, workspace: Path, proj_root: Path) -> Path | None:
    """Resolve a declared state-manifest root without guessing."""
    if name == "worktree":
        return workspace
    if name == "proj_root":
        return proj_root
    return None


def _scoped_state_path(root: Path | None, raw_path: object) -> Path | None:
    """Resolve a relative manifest path without permitting root escape."""
    if root is None or not isinstance(raw_path, str) or not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return None
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved


def _run_state_predicate(command: object, cwd: Path) -> tuple[bool, str]:
    """Run a trusted same-branch argv predicate without shell interpretation."""
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(argument, str) and argument for argument in command)
    ):
        return False, "predicate must be a non-empty argv list"
    proc = subprocess.run(
        command,
        cwd=cwd,
        shell=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output = (proc.stderr or proc.stdout).strip().splitlines()
    return proc.returncode == 0, (output[-1] if output else f"exit {proc.returncode}")


def check_state_manifest(path: Path, workspace: Path, proj_root: Path) -> list[Check]:
    """Verify trusted same-branch dispatch-state claims as advisories.

    Args:
        path: Path to the tracked, owner-authored state-manifest YAML.
        workspace: Worktree root used for ``root: worktree`` declarations.
        proj_root: Project root used for ``root: proj_root`` declarations.

    Returns:
        Warning-first checks. State findings remain advisory and do not make
        the dispatch-readiness command exit non-zero during calibration.
    """
    if not path.is_file():
        return [Check("state-manifest", False, f"required manifest not found: {path}")]
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [Check("state-manifest", False, f"unreadable required manifest: {exc}")]
    if not isinstance(payload, dict) or not isinstance(payload.get("task_id"), str):
        return [Check("state-manifest", False, "required task_id is absent")]

    checks: list[Check] = []
    for kind in (
        "deliverables",
        "blockers",
        "planned_contracts",
        "inputs",
        "outputs",
        "lanes",
        "registries",
        "derived_fields",
        "required_fields",
    ):
        if kind not in payload:
            checks.append(Check(f"state:{kind}", True, f"WARNING: required {kind} section is absent", advisory=True))
            payload[kind] = []
        elif not isinstance(payload[kind], list):
            checks.append(Check(f"state:{kind}", True, f"WARNING: {kind} must be a list", advisory=True))
            payload[kind] = []

    for item in payload.get("deliverables", []):
        if not isinstance(item, dict):
            checks.append(Check("state:deliverable", True, "WARNING: malformed entry", advisory=True))
            continue
        root = _state_root(item.get("root", ""), workspace, proj_root)
        target = _scoped_state_path(root, item.get("path"))
        required = ("path", "root", "owner_task", "completion_predicate")
        missing = [field for field in required if not item.get(field)]
        if missing or target is None:
            detail = f"WARNING: missing/invalid {', '.join(missing) or 'root'}"
        elif target.exists() and item["owner_task"] == payload["task_id"]:
            complete, diagnostic = _run_state_predicate(item["completion_predicate"], root)
            detail = (
                f"WARNING: existing deliverable owned by {item['owner_task']} "
                "is complete; dispatch should be review-only"
                if complete
                else f"deliverable exists but is incomplete ({diagnostic}); fresh dispatch retained"
            )
        else:
            detail = (
                "deliverable absent; fresh dispatch retained"
                if not target.exists()
                else "deliverable belongs to another task; fresh dispatch retained"
            )
        checks.append(Check(f"state:deliverable:{item.get('path', '?')}", True, detail, advisory="WARNING:" in detail))

    for item in payload.get("blockers", []):
        if not isinstance(item, dict) or not item.get("id") or not item.get("check"):
            checks.append(Check("state:blocker", True, "WARNING: blocker requires id and check", advisory=True))
            continue
        live, diagnostic = _run_state_predicate(item["check"], workspace)
        detail = "blocker remains live" if live else f"WARNING: blocker is stale ({diagnostic})"
        checks.append(Check(f"state:blocker:{item['id']}", True, detail, advisory=not live))

    for item in payload.get("planned_contracts", []):
        if not isinstance(item, dict):
            checks.append(Check("state:contract", True, "WARNING: malformed entry", advisory=True))
            continue
        root = _state_root(item.get("root", ""), workspace, proj_root)
        target = _scoped_state_path(root, item.get("path"))
        expected = item.get("ready_status", "")
        try:
            contract = yaml.safe_load(target.read_text(encoding="utf-8")) if target and target.is_file() else {}
        except (OSError, yaml.YAMLError):
            contract = {}
        actual_id = contract.get("id") or contract.get("contract_id") if isinstance(contract, dict) else None
        ready_ok = False
        if isinstance(expected, str) and "=" in expected and isinstance(contract, dict):
            field, value = expected.split("=", 1)
            ready_ok = str(contract.get(field.strip())).lower() == value.strip().lower()
        ok = bool(target and target.is_file() and actual_id == item.get("id") and ready_ok)
        detail = "contract materialized and ready" if ok else "WARNING: contract missing, wrong-id, or not ready"
        checks.append(Check(f"state:contract:{item.get('id', '?')}", True, detail, advisory=not ok))

    for item in payload.get("inputs", []):
        root = _state_root(item.get("root", "") if isinstance(item, dict) else "", workspace, proj_root)
        target = _scoped_state_path(root, item.get("path")) if isinstance(item, dict) else None
        ok = target is not None and target.exists()
        checks.append(
            Check(
                f"state:input:{item.get('path', '?') if isinstance(item, dict) else '?'}",
                True,
                "input resolved" if ok else "WARNING: input has wrong/missing root or does not resolve",
                advisory=not ok,
            )
        )

    for item in payload.get("outputs", []):
        root = _state_root(item.get("root", "") if isinstance(item, dict) else "", workspace, proj_root)
        rel = item.get("path", "") if isinstance(item, dict) else ""
        target = _scoped_state_path(root, rel)
        proc = (
            subprocess.run(["git", "check-ignore", "-q", "--", str(target)], cwd=root, check=False)
            if target and root
            else None
        )
        ok = proc is not None and proc.returncode == 1
        infrastructure_error = proc is not None and proc.returncode not in (0, 1)
        checks.append(
            Check(
                f"state:output:{rel or '?'}",
                True,
                "output is trackable"
                if ok
                else "WARNING: git trackability check failed"
                if infrastructure_error
                else "WARNING: output is missing or gitignored",
                advisory=not ok,
            )
        )

    for item in payload.get("lanes", []):
        if not isinstance(item, dict) or not item.get("id"):
            checks.append(Check("state:lane", True, "WARNING: lane requires id", advisory=True))
            continue
        lane_id = item["id"]
        next_gate = item.get("next_gate")
        complete, diagnostic = _run_state_predicate(item.get("completion_predicate"), workspace)
        if complete and isinstance(next_gate, str) and next_gate:
            detail = f"WARNING: lane is complete; skip author dispatch and advance to {next_gate}"
            advisory = True
        elif complete:
            detail = "WARNING: completed lane requires a non-empty next_gate"
            advisory = True
        elif diagnostic == "predicate must be a non-empty argv list":
            detail = f"WARNING: {diagnostic}"
            advisory = True
        else:
            detail = "lane remains active"
            advisory = False
        checks.append(Check(f"state:lane:{lane_id}", True, detail, advisory=advisory))

    for item in payload.get("registries", []):
        if not isinstance(item, dict):
            checks.append(Check("state:registry", True, "WARNING: malformed entry", advisory=True))
            continue
        registry_id = item.get("id", "?")
        root = _state_root(item.get("root", ""), workspace, proj_root)
        target = _scoped_state_path(root, item.get("path"))
        symbol = item.get("symbol")
        disposition = item.get("disposition")
        allowed_dispositions = {"writable", "certified_unchanged"}
        ok = (
            isinstance(symbol, str)
            and bool(symbol)
            and _source_declares_symbol(target, symbol)
            and disposition in allowed_dispositions
        )
        detail = (
            f"registry dependency resolved ({disposition})"
            if ok
            else "WARNING: registry path, symbol, or disposition is unresolved"
        )
        checks.append(Check(f"state:registry:{registry_id}", True, detail, advisory=not ok))

    for item in payload.get("derived_fields", []):
        if not isinstance(item, dict):
            checks.append(Check("state:derived-field", True, "WARNING: malformed entry", advisory=True))
            continue
        name = item.get("name", "?")
        ok = all(
            isinstance(item.get(field), str) and item[field].strip() for field in ("name", "preimage", "semantics")
        )
        detail = (
            "derived-field preimage and semantics declared"
            if ok
            else "WARNING: derived field requires name, preimage, and semantics"
        )
        checks.append(Check(f"state:derived-field:{name}", True, detail, advisory=not ok))

    for item in payload.get("required_fields", []):
        if not isinstance(item, dict):
            checks.append(Check("state:required-field", True, "WARNING: malformed entry", advisory=True))
            continue
        name = item.get("name", "?")
        source = item.get("source")
        resolved, diagnostic = _run_state_predicate(item.get("resolution_check"), workspace)
        ok = isinstance(name, str) and bool(name) and isinstance(source, str) and bool(source.strip()) and resolved
        detail = "required-field source resolved" if ok else f"WARNING: required-field source unresolved ({diagnostic})"
        checks.append(Check(f"state:required-field:{name}", True, detail, advisory=not ok))
    return checks or [Check("state-manifest", True, "manifest has no state claims")]


def _source_declares_symbol(target: Path | None, symbol: str) -> bool:
    """Match a declared registry symbol, excluding comments and longer names."""
    if target is None or not target.is_file():
        return False
    try:
        source = target.read_text(encoding="utf-8")
    except OSError:
        return False
    if target.suffix == ".py":
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return False
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol:
                return True
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(candidate, ast.Name) and candidate.id == symbol for candidate in targets):
                    return True
        return False
    token = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])")
    return any(token.search(line) for line in source.splitlines() if not line.lstrip().startswith("#"))


def render(agent: str, branch: str, mode: str, checks: list[Check]) -> str:
    """Render the Dispatch Readiness markdown block pasted into the envelope."""
    all_ok = all(c.ok for c in checks)
    has_advisory = any(c.advisory for c in checks)
    if not all_ok:
        verdict = "FAIL"
    elif has_advisory:
        verdict = "PASS (with advisories)"
    else:
        verdict = "PASS"
    lines = [
        "## Dispatch Readiness",
        "",
        f"`manager_dispatch_check` — agent **{agent}**, branch `{branch}` ({mode}) — **{verdict}**",
        "",
    ]
    for c in checks:
        mark = "~" if c.advisory else ("x" if c.ok else " ")
        lines.append(f"- [{mark}] **{c.name}** — {c.detail}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Manager dispatch-readiness gate.")
    p.add_argument("--agent", required=True, help="Worker agent slug (bus dir name).")
    p.add_argument("--branch", required=True, help="Feature branch for the dispatch.")
    p.add_argument(
        "--expected-base",
        required=True,
        help="Required prerequisite ref that must be an ancestor of workspace HEAD.",
    )
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
    p.add_argument("--state-manifest", required=True, help="Tracked task-state manifest (YAML).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path.cwd()
    proj_root = resolve_proj_root(repo_root)

    checks: list[Check] = []
    checks.extend(check_worktree(proj_root, args.branch, args.mode))
    checks.append(check_report_bus(proj_root, args.agent))

    wt_map = _worktree_paths(proj_root)
    workspace = _resolve_workspace(args.workspace, args.branch, wt_map, proj_root)
    checks.append(check_workspace_binding(args.branch, args.mode, workspace, wt_map))
    checks.append(check_branch_ancestry(workspace, args.expected_base))
    checks.append(check_contracts(workspace))
    checks.append(check_hook_gate(workspace))

    manifests = [Path(m) for m in args.provenance_manifest]
    checks.extend(check_provenance(manifests, repo_root, proj_root))
    state_path = Path(args.state_manifest)
    if not state_path.is_absolute():
        state_path = workspace / state_path
    checks.extend(check_state_manifest(state_path, workspace, proj_root))

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
