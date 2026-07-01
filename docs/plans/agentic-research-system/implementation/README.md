# ARS P0 Implementation Plan Suite

**Date:** 2026-07-01<br>
**Status:** `review_pending`<br>
**Authority:** P-026/P-030 permit planning only; implementation requires Stephen's approval of the master plan<br>
**Runtime authority:** None

## Read order

1. [Master P0 materialization and foundation plan](../05-p0-materialization-and-foundation-implementation-plan.md)
2. [Work Package 1 — control plane and replay](01-control-plane-and-replay-plan.md)
3. [Work Package 2 — context, routing, and assurance](02-context-routing-and-assurance-plan.md)
4. [Work Package 3 — adapters and operations](03-adapters-and-operations-plan.md)
5. [Work Package 4 — evaluation and P0 fixtures](04-evaluation-and-p0-fixtures-plan.md)

## Execution rule

Work Package 1 freezes shared package/schema/storage primitives. Work Packages 2 and 3 may then proceed independently. Work Package 4 may scaffold against deterministic fakes but can issue an integrated P0 decision only after Packages 1–3 pass their review checkpoints.

Every execution session must use the sub-skill named in the plan header, an isolated worktree, TDD, scoped commits, and explicit review checkpoints. No plan authorizes active APM migration, current-paper writes, live provider use, pilot initialization, or research claims.

## Review gate

- [ ] File paths and module ownership are coherent across all four plans.
- [ ] Test names and fixture assignments match the accepted catalogue.
- [ ] Exact commands are valid for the repository's Python/uv/pytest toolchain.
- [ ] The 37-case P0 closure and deferred Gate 5 cases are correct.
- [ ] Stop conditions preserve P-026/P-030 boundaries.
- [ ] Stephen approves the suite before execution.

**Outcome:** `REVIEW_PENDING — implementation plan suite complete; no code or fixture materialization authorized`.
