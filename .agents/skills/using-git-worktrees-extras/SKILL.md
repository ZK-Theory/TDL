---
name: using-git-worktrees-extras
description: Complement superpowers:using-git-worktrees in multi-interpreter or optional-dependency repositories, and on Windows or sandboxed runtimes where a linked worktree may not be editable by the mandated tool. Use when the full baseline fails outside task scope or when manually created worktrees need operational readiness checks.
---

# Using Git Worktrees Extras

Use alongside superpowers:using-git-worktrees. Isolation is ready only when the runtime can edit, stage, and test inside the same worktree.

## Scoped Baseline Gate

If the full baseline fails:

1. Preserve the complete command, output, collection failures, interpreter, and dependency state.
2. Establish that each excluded failure predates the branch, is outside task paths, and belongs to a separately documented environment or optional dependency surface.
3. Obtain explicit user approval before adopting a scoped baseline.
4. Record the scoped command, excluded test ownership, compatibility debt, and why collection-time imports prevent ordinary marker deselection.
5. Reject the scoped baseline if it excludes any dependency or path used by the planned implementation.

A scoped pass never converts the full baseline to green; report both results.

## Declared-Root Routing

Before attempting an edit on Windows or in a sandboxed runtime, read the
runtime's declared workspace/writable roots. Treat every linked Git worktree as
a separate root even if its path is lexically nested beneath an authorized
checkout.

- If the exact target worktree is not declared writable, do not use the editor
  as a probe. Route code/test work to a task launched with that worktree as its
  workspace.
- A Manager may review a foreign worktree read-only. Remediation returns to the
  owning task or a newly launched task rooted at that worktree.
- For an already-authorized, bounded text-only change on an existing remote
  branch, an exact-SHA GitHub Contents update is permitted: fetch branch and
  blob identity, update only the scoped path, refetch, and compare. It is not a
  substitute for a locally validated code change.
- Do not bypass a split-root denial with shell/base64 writes, `git apply`, or
  another editor. If no valid route exists, report the routing requirement once
  instead of repeating the predictable failure.

A platform-created worktree task normally owns its own worktree root; the
orchestrating task normally does not.

## Edit-Path Preflight

Run this only after the exact worktree is declared writable:

1. Reconfirm the worktree root, branch/detached state, git directory, and common directory.
2. Read a known repository file through the runtime's normal file tool.
3. Use the mandated editor to create and modify a disposable preflight file inside the worktree.
4. Verify index readiness with a reversible intent-to-add/reset cycle, remove the disposable file with the mandated editor, and confirm status returns to its prior state.
5. Run the approved baseline command from that exact worktree.

If a declared-writable worktree still fails the edit/index probe, stop. Prefer
the platform-native worktree mechanism or restart the task with the worktree as
the runtime workspace. Do not retry from the orchestrating task.

## Venv & File-Discovery Operational Readiness

- **Glob/Grep are ignore-blind inside a worktree.** `.apm/worktrees/**` is
  gitignored in the parent repo — the same mechanism as the vault junction
  (Cross-Cutting Principle 3). `Glob`/`Grep` inherit the parent repo's ignore
  rules even when `path` points inside the worktree, so "No files found" is
  indistinguishable from "directory does not exist." Before concluding a
  worktree-relative path is empty or absent, verify with `Get-ChildItem`/`ls`
  (a shell listing) — never trust a Glob/Grep absence signal alone inside
  `.apm/worktrees/` or any other gitignored mount.
- **Never run two `uv run`/`uv sync` against the same venv concurrently**,
  including one backgrounded overlapping a foreground call — they race the
  editable-install and leave the venv missing deps while `uv sync` still
  audits it as clean. Recovery: `uv sync --all-extras --reinstall`. Prefer
  serial `uv run` within a worktree, or give a background job its own
  worktree.
- **A fresh worktree's `uv sync` can fail building a source-only dependency**
  (e.g. petls: no Windows wheel, sdist build breaks under a newer
  scikit-build-core) even though the main venv already has a working build.
  Fix: `uv sync --all-extras --no-install-package <pkg>`, then seed the
  package into the worktree venv from the main venv per its `RECORD` file
  (the package dir + dist-info + any `include`/`lib` payload). Seed AFTER the
  final sync — a later `uv sync --no-install-package <pkg>` removes the
  seeded copy, since uv's satisfaction check is name+version, not
  provenance.
- **`manager_dispatch_check`'s contract sub-check is not worktree-venv-safe.**
  It shells `uv run python .claude/hooks/contract_binding_check.py
  --validate-only` with `cwd=<worktree>` and no `--no-sync`; a brand-new
  worktree has no synced `.venv`, so `uv run` there either fails on a missing
  optional dep or hits a Windows `Access is denied` lock re-syncing the main
  venv — producing a false FAIL that the `dispatch-readiness-guard`
  PreToolUse hook then hard-blocks a bus write on. Workaround: point the
  check at the main repo's already-synced venv with sync disabled —
  `UV_NO_SYNC=1 uv run --no-sync python -m shared.manager_dispatch_check
  --agent <slug> --branch <b> --mode parallel --workspace "C:/Users/steph/TDL"`
  — a freshly created worktree is byte-identical to its base branch, so
  validating contracts against the main venv is authoritative when the
  worktree itself authors no contracts.

## Pre-Delivery Check

Report the full and scoped baseline states separately, the explicit approval for scoping, the exact excluded ownership, and evidence that reads, edits, index operations, and tests all resolved inside one worktree.
