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

## Pre-Delivery Check

Re-run each plan-specified command literally and verify its declared evidence. Do not mark the task complete when only an internal function test passed or when process success produced no observable proof that the handler executed.
