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

## WP6 suite (P-042/06g accepted for governing planning; WP6.3 readiness blocked)

1. [WP6 master — historical Gate 6 launch-basis snapshot](06-wp6-gate6-readiness-and-integration-plan.md) (exact revision `fe5f1d40` preserved under P-036)
2. [WP6.1 — runtime Task lifecycle and operator surface](06a-wp6-1-runtime-task-lifecycle-plan.md) (Gate A A4/A5)
3. [WP6 owner-operated external-session amendment](06g-wp6-owner-operated-session-amendment.md) (effective status `accepted_for_governing_planning` via the [external acceptance record](../reviews/wp6-owner-operated-session-amendment-owner-acceptance-2026-07-26.md); embedded pending status is the reviewed candidate snapshot)
4. [WP6.2 — historical live-capability plan](06b-wp6-2-live-capability-plan.md) (direct-provider execution deferred by P-042)
5. [WP6.1 literal 104-row owner-source catalogue and exact schema/authority/concurrency contracts](06d-wp6-1-owner-source-catalogue.md)

**Current WP6.1 execution control:** [06o capability-campaign plan](06o-wp6-1-lifecycle-execution-plan-after-message-pilot.md) records C1 integrated through PR #212. The fixed pre-C1 `104/19/85` baseline and `23/28/32/2` allocation remain authoritative; the current census is `104/42/62`. WP6.1 remains incomplete, and C2/KAN-73 requires an explicit owner start.

6. [WP6.2 historical 51-row live replacement map](06e-wp6-2-live-replacement-map.md)
7. [WP6.2 historical P1 54-obligation expected-source and descriptor-hash contract](06f-wp6-2-p1-activation-contract.md)
8. [WP6.1 schema identity, producer completeness, and historical-event protocol](06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md) — **G-RM-8 `GRANDFATHER` is selected and constructed under KAN-95, the post-PR #229 binding census is reconciled against final live main, and the single exact-subject review's four findings are remediated; same-reviewer verification and owner acceptance remain open**. The [current producer record](06h-current-producer-and-evidence-record-9736c90-2026-08-09.md) and [final live-main reconciliation evidence](06h-final-live-main-reconciliation-evidence-2f005f1-2026-08-09.md) bind the unchanged 112-row runtime catalogue and complete classified six-site append census without fabricating the non-reconstructible pre-change baseline. The [attributed decision](06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json) binds the exact 79-event Control prefix and zero missing-triple set.
9. [WP6.1 artefact authority and production-consumer firewall](06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md) — **implemented and production-path proven in the WP6.4 integrated candidate; exact-subject review and integration pending**. The candidate uses real command submission, replay-derived authority, governing scientific-review evidence, root-bound content reads, and the fixed production-consumer ports. G-RM-14 disposition follows the final exact-subject review.
10. [WP6.1 W3 context-packet lifecycle and resolution](06j-w3-context-packet-lifecycle-and-resolution-plan.md) — **implemented and production-path proven in the WP6.4 integrated candidate; exact-subject review and integration pending**. The nine-command lifecycle, immutable packet/delivery objects, consumer resolver, and real CommandService adapter execute through the public brief round trip. G-RM-12 disposition follows the final exact-subject review.
11. [WP6.7 legacy consolidation sequencing](06l-wp6-7-legacy-consolidation-sequencing.md) — sequencing only; this is a distinct legacy-integration scope and path from 06i's artefact-authority and production-consumer firewall plan, not a collision or supersession.

WP6.3–WP6.7 (TDA/panel assurance pack, project binding + Gate 6 preflight, W11
portfolio/Discovery specification, dossier admission, legacy consolidation) are scoped
in the WP6 master plan; their dispatch plans are written when their gates approach.
Owner directions P-031–P-034 are recorded as `accepted` (wording confirmed
2026-07-17) in
[../03-decisions-and-open-questions.md](../03-decisions-and-open-questions.md).
P-042 and the 06g acceptance record supersede the direct-provider WP6.2
sequence. The governing first-release dependency path is WP6.1 plus WP6.3 into
WP6.4 and Gate 6. The
[KAN-56 readiness assessment](../reviews/wp6-3-gate-a-readiness-assessment-2026-07-26.md)
found WP6.3 not ready for implementation: its upstream contract remains
unaccepted, its six skill identities are stale, two required contract references
remain pending, and the `assurance_pack` ID kind is unavailable. Gate A A7
therefore remains open; no WP6.3 implementation brief or WP6.4 dispatch is
authorized. ARS does not invoke Claude or Codex or handle their OAuth
credentials.

## Research Methods obligations — integrated by P-047, **candidate production path proven**

P-047 retires separate-lane tracking. WP6.1 owns 06h, 06i, 06j and RM-01;
WP6.4 owns RM-02, RM-03 and RM-04's governed non-executing verification-return
path; Gate 9 owns only RM-04's manuscript pilot. RM-05 remains deferred behind
G-RM-11. The WP6.4 integrated candidate now contains the RM-02 assets and
history verifier, real `ars brief export` / `ars brief import` production path,
and RM-04 non-executing verification-request/return records. The public path is
proven with durable candidate registration and restart/replay equality; it is
not integrated on `main` until final exact-subject review and merge complete.

**G-RM-3 is closed** for exact commit `0137d2c` and tree `ee7d510` by the
2026-07-31 owner record after zero-finding independent review. Do not repeat it.
That acceptance does not satisfy G-RM-12/G-RM-13/G-RM-14 or make unimplemented
capabilities runnable.

1. [RM-00 — integrated obligation/gate crosswalk](rm-00-research-methods-lane-master-plan.md) (historical identities plus live ownership; not a separate campaign)
2. [RM-01 — suite recovery and quality accounting](rm-01-unblock-and-suite-recovery-plan.md) (consumes the pre-06h baseline and compares the same post-change cohort)
3. [RM-02 — Research Methods Pack v1](rm-02-research-methods-pack-plan.md) (independent Git history anchor plus 06i acceptance authority)
4. [RM-03 — brief export/import on accepted artefact and context-packet paths](rm-03-brief-export-import-plan.md) (depends on accepted 06i, 06j, and RM-02)
5. [RM-04 — manuscript review lane and operator verification records](rm-04-manuscript-review-and-verification-records-plan.md) (**no execution**; depends on accepted 06i, 06j, RM-03, and exact G-RM-13 use authority before follow-up consumption)
6. RM-05 — isolated verification execution: **unwritten**, gated on G-RM-11 readiness acceptance

Review provenance: the
[initial adversarial review](../reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md),
the [initial response](../reviews/rm-lane-review-response-2026-07-29.md), the
[2026-07-30 adversarial rereview](../reviews/adversarial-rm-lane-plan-suite-rereview-2026-07-30.md),
the [revision-3 remediation response](../reviews/rm-lane-rereview-response-2026-07-30.md),
the [PR #198 pre-merge review](../reviews/pr-198-premerge-review-c7ace86-2026-07-30.md),
the [revision-4 response](../reviews/rm-lane-pr198-premerge-review-response-2026-07-30.md),
the [PR #198 exact-subject rereview](../reviews/pr-198-premerge-rereview-8e091a1-2026-07-30.md),
the [PR198-RR1 response](../reviews/rm-lane-pr198-premerge-rereview-response-2026-07-30.md),
the [`d6c9647` constructibility/authority rereview](../reviews/pr-198-premerge-rereview-d6c9647-2026-07-30.md),
its [revision-5 response](../reviews/rm-lane-pr198-premerge-rereview-d6c9647-response-2026-07-30.md),
the [`85f33e6` transitive caller rereview](../reviews/pr-198-premerge-rereview-85f33e6-2026-07-30.md),
and its [revision-6 response](../reviews/rm-lane-pr198-premerge-rereview-85f33e6-response-2026-07-31.md).
ARS invokes no provider and handles no OAuth credentials in any RM plan
(P-042), and no RM plan executes externally-proposed code (review C-4).

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
