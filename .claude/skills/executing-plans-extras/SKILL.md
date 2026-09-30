---
name: executing-plans-extras
description: Complement superpowers:executing-plans when an implementation plan specifies exact CLI, module, migration, or validation commands. Use whenever exit status alone could hide a no-op entrypoint or when completion depends on command output or a state transition.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - manager
    - implementer
  runtime: agnostic
---

# Executing Plans Extras

Use alongside superpowers:executing-plans. A zero exit status proves normal process termination, not that the intended handler ran.

## Exact-Command Verification

For every exact command named by the plan:

1. Run the literal command from the specified directory and environment; do not substitute a unit-level function call.
2. Identify the declared evidence before execution: required stdout/stderr, created or changed artifact, database state, exit code, or other observable transition.
3. Add or run a subprocess-level test that asserts the command's required evidence.
4. Treat exit zero with missing output or missing state change as a failed verification and investigate entrypoints such as __main__, argument dispatch, and early returns.
5. Record the literal command, exit code, captured evidence, and negative/no-op check in the task report.

A direct handler unit test can supplement this check but cannot replace it.

## Commits And Background Runs

The same rule applies to the agent's own git and test commands: the exit code
describes the process, not the outcome.

- **Confirm a commit by the state it produces.** Record `git rev-parse HEAD`
  before committing; afterwards check that HEAD moved and `git log -1
  --format=%s` is the intended subject. Never pipe `git commit` into `tail`,
  `grep` or `head` without `set -o pipefail`: the pipeline reports the last
  command's status, so a commit blocked by pre-commit reads as exit 0. The
  commit-state guard hook refuses that shape; redirect long hook output to a
  file instead.
- **A killed run is not a red run.** Never wrap a long background test run in
  a shell `timeout`; use the harness's own background execution. Exit 124,
  137 or 143 means the run was killed. Report it as killed and re-run it;
  never read it as a test failure.
- **Do not commit while tests read the tree.** Pre-commit stashes unstaged
  changes and restores them afterwards, rewriting working-tree bytes under any
  running process. Commit first and launch tests against the committed tree,
  or give the test run its own worktree.
- **Check each command did what it said.** An edit that matched nothing, an
  empty heredoc and a process-kill filter that matches the invoking shell all
  report success. Re-read the changed lines after an edit, check a generated
  file is non-empty before using it, and exclude the current shell's PID from
  any kill filter.

## Pre-Delivery Check

Re-run each plan-specified command literally and verify its declared evidence. Do not mark the task complete when only an internal function test passed or when process success produced no observable proof that the handler executed.
