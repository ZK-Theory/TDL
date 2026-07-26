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

## Gate 5 suite (approved for Gate 5 execution 2026-07-10)

- [WP5 — Gate 5 foundation acceptance scope and sequencing](05-wp5-gate5-foundation-acceptance-plan.md), with child plans 05a–05e.

## WP6 suite (P-042 owner direction accepted; revised execution path pending 06g consistency review and acceptance)

1. [WP6 master — historical Gate 6 launch-basis snapshot](06-wp6-gate6-readiness-and-integration-plan.md) (exact revision `fe5f1d40` preserved under P-036)
2. [WP6.1 — runtime Task lifecycle and operator surface](06a-wp6-1-runtime-task-lifecycle-plan.md) (Gate A A4/A5)
3. [WP6 owner-operated external-session amendment](06g-wp6-owner-operated-session-amendment.md) (`owner_direction_accepted_review_pending`; no dispatch authority)
4. [WP6.2 — historical live-capability plan](06b-wp6-2-live-capability-plan.md) (direct-provider execution deferred by P-042)
5. [WP6.1 literal 104-row owner-source catalogue and exact schema/authority/concurrency contracts](06d-wp6-1-owner-source-catalogue.md)
6. [WP6.2 historical 51-row live replacement map](06e-wp6-2-live-replacement-map.md)
7. [WP6.2 historical P1 54-obligation expected-source and descriptor-hash contract](06f-wp6-2-p1-activation-contract.md)

WP6.3–WP6.7 (TDA/panel assurance pack, project binding + Gate 6 preflight, W11
portfolio/Discovery specification, dossier admission, legacy consolidation) are scoped
in the WP6 master plan; their dispatch plans are written when their gates approach.
Owner directions P-031–P-034 are recorded as `accepted` (wording confirmed
2026-07-17) in
[../03-decisions-and-open-questions.md](../03-decisions-and-open-questions.md).
P-042 records the accepted owner direction to supersede the direct-provider
WP6.2 sequence. The proposed first-release path, WP6.1 plus WP6.3 into WP6.4 and
Gate 6, remains non-dispatchable until the 06g fresh consistency review and
acceptance gate complete. ARS does not invoke Claude or Codex or handle their
OAuth credentials.

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
