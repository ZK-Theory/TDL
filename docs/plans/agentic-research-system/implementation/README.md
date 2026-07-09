# ARS P0 Implementation Plan Suite

**Date:** 2026-07-01<br>
**Status:** `accepted_for_p0_implementation`<br>
**Authority:** Stephen explicitly approved the exact reconciled P0 scope and section 7.3 owner decisions on 2026-07-01<br>
**Runtime authority:** Isolated task-by-task P0 implementation with deterministic fakes only

## Read order

1. [Master P0 materialization and foundation plan](../05-p0-materialization-and-foundation-implementation-plan.md)
2. [Work Package 1 — control plane and replay](01-control-plane-and-replay-plan.md)
3. [Work Package 2 — context, routing, and assurance](02-context-routing-and-assurance-plan.md)
4. [Work Package 3 — adapters and operations](03-adapters-and-operations-plan.md)
5. [Work Package 4 — evaluation and P0 fixtures](04-evaluation-and-p0-fixtures-plan.md)
6. [Adversarial P0 plan review](../reviews/adversarial-p0-plan-suite-review-2026-07-01.md)
7. [Review reconciliation](../reviews/adversarial-p0-plan-suite-review-reconciliation-2026-07-01.md)
8. [Python compatibility baseline note](python-compatibility-baseline-2026-07-01.md)

## Execution rule

Work Package 1 freezes shared package/schema/storage primitives. Work Packages 2 and 3 may then proceed independently. Work Package 4 may scaffold against deterministic fakes but can issue an integrated P0 decision only after Packages 1–3 pass their review checkpoints.

Every execution session must use the sub-skill named in the plan header, an isolated worktree, TDD, scoped commits, and explicit review checkpoints. No plan authorizes active APM migration, current-paper writes, live provider use, pilot initialization, or research claims.

## Review gate

- [x] File paths, shared interfaces, and module ownership are coherent across all four reconciled plans.
- [x] Test names and fixture assignments match the accepted catalogue and the WP2/WP3 ownership split.
- [x] Exact commands are syntactically valid for the repository's Python/uv/pytest toolchain; provider commands remain version-bound and disabled.
- [x] The 37-case P0 closure and deferred Gate 5 cases are correct.
- [x] Stop conditions preserve P-026/P-030 boundaries and block unresolved M/H/live-provider policy.
- [x] Stephen approved the exact reconciled suite and section 7.3 owner decisions on 2026-07-01 before execution.

**Outcome:** `ACCEPTED_FOR_P0_IMPLEMENTATION — begin in the isolated codex/ars-p0-foundation worktree; all later-provider, migration, Gate 5, pilot, and claim boundaries remain in force`.
