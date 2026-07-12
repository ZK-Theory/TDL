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

## Pre-Delivery Check

Report the full and scoped baseline states separately, the explicit approval for scoping, the exact excluded ownership, and evidence that reads, edits, index operations, and tests all resolved inside one worktree.
