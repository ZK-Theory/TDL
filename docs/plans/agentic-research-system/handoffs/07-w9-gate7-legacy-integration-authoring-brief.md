# 07 — Authoring Brief: W9 Specification and Gate 7 (Legacy Research Integration)

**Date:** 2026-07-18
**Status:** owner-approved authoring brief (Stephen, 2026-07-18). This brief commissions
the W9 specification and a Gate 7 definition; it authorizes writing and review of those
documents only. It creates no implementation, migration, dispatch, or Gate 6 change.
**Owner direction being implemented:** Gate 6 runs **as-is** (the WP6.8 "P01 completion
lane" supplement proposal of 2026-07-18 was considered and **rejected**); legacy work —
centrally the completion of P01-A and P01-B — integrates through **a separate, later
gate** built on the W9 slot the roadmap already reserves. The papers' completion latency
behind Gate 6 → pilot → promotion is accepted.

---

## 1. What is being commissioned

1. **`design/09-migration-and-pilot.md` (W9)** — the migration/pilot specification the
   02-roadmap reserves: legacy import format and status mapping, `.apm/` compatibility
   views, rollback and stop criteria, baseline and comparison metrics, user review
   points, deprecation path for mutable bus/Tracker state. The W9 description must state
   that legacy import produces only content-addressed, read-only compatibility
   projections and explicitly prohibit copying or writing legacy tasks, bus records,
   logs, claims, or decisions into successor authority, while preserving the existing
   rollback guarantee that pilot failure can be rolled back without changing any accepted
   research artefact or decision.
2. **Gate 7 definition** — a short addition to `04-parallel-specification-and-foundation-
   pilot-plan.md` §4 (plus a currency note): **Gate 7 — Legacy research integration.**
   Formalizes W9 acceptance + WP6.7 execution, with P01-A and P01-B as its first named
   subjects. Sequenced strictly after Gate 6 pilot promotion evidence exists, so the
   machinery that receives the papers has been proven on the non-critical SCALE-01
   workload first (preserving the intent of P-031).

Both documents pass the standard adversarial review (author and reviewer distinct
agents) and reconciliation before Stephen's exact-revision acceptance. Wording changes
to accepted decisions (P-026/P-034 boundary language) are proposed *inside* the W9/Gate-7
drafts as explicit amendment text for Stephen to accept — never edited in place.

## 2. The transition boundary the drafts must encode (verified 2026-07-18 — do not re-derive from older docs)

The existing WP6.7 gate — "Nothing in WP6.7 dispatches while T1.28 or either current
paper remains active" — is stale in both limbs and must be replaced by positive
preconditions matching the verified state:

1. **T1.28 is DONE**, not active: reviewed 2026-07-09 (Manager 12), PR #72 merged
   2026-07-09 (`703101d`), CodeRabbit review-then-merge gate held. Headline: USoc 12/12
   subgroups reject H₀, BHPS 9/11 (the two non-rejecting strata are the pre-registered
   underpowered smallest cells); §6.1 contingency checked and locked.
2. **The W0 addendum the T1.28 terminal disposition triggers is OUTSTANDING.** Both the
   04-plan (§2) and P-026 state the terminal review "triggers a dated W0 addendum and
   bounded delta review"; no such addendum exists in the plans tree. The trigger fired
   2026-07-09 and the obligation is unclaimed. **Gate 7's first deliverable is that
   dated W0 addendum + bounded delta review** — it is intake work for the gate, not a
   blocker on it.
3. **Both papers are formally suspended** under the 2026-07-18 APM prose-freeze
   `[DECISION]` (Computational-Log; CONVENTIONS lock; PR #126 merged 2026-07-18): no
   APM prose authoring, no new APM compute dispatches, legacy record closed for
   writing. "Active" in the old wording meant APM-managed work in flight; nothing is.
4. Housekeeping state the drafts may rely on: PR #118 merged 2026-07-18 (§4.2 table
   reconciliation); CONVENTIONS vault link re-established as a path-resolving symlink
   (2026-07-18); Gate 5 accepted at merge `f49a27f`; WP6 first wave in flight
   (WP6.2/WP6.3 at independent-review-accept, awaiting CodeRabbit + owner acceptance —
   see `.apm/memory/handoffs/2026-07-18-wp6-first-wave-handback.md`).

## 3. Gate 7 intake manifest (enumerate by pointer, not by copy)

The Gate 7 definition must carry an intake manifest listing the parked work it will
receive. Current contents, each with its authority pointer:

| Item | Pointer |
|---|---|
| W0 addendum + bounded delta review (first deliverable; trigger fired 2026-07-09) | 04-plan §2; P-026 |
| §2 parked compute: T1.41 double-null calibration panel | freeze handoff §2; audit hole H1; pre-reg to be filed at dispatch |
| §2 parked compute: Markov-2 α=1 certified recompute — **scoped W₂-only** per the H6 ruling (2026-07-18 `[DECISION]`, PR #129): the landscape L² side is certified-in-hand from the committed α=1 cell JSONs | 2026-07-17 pre-registration; Computational-Log 2026-07-18 H6 entry; `SUPERSEDED.md` split verdict |
| §3 park set (6 items) | freeze handoff §3 (recorded with pointers by Manager 14) |
| Claim-trace audit holes H1–H9 as the rewrite input inventory (H6 now resolved) | `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md` §3.3 |
| Failure inventory → invariants I1a–I11a as the enforcement requirements on any Gate-7 prose/compute deliverable | `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md` |
| Unclosed T1.20 audit: BHPS regression may have consumed parental-NSSEC=NaN pre-extractor-fix (carried in the T1.28 tracker row, never closed) | `.apm/tracker.md` row 1.28 |
| Non-overlap L=1882 arm + 20 subsamples production re-run (H3) — needs an owner scope decision (re-run vs drop the claims) before dispatch | audit hole H3; 2026-07-16 §6.2 `[DECISION]` |

## 4. Constraints the drafts must respect

- **Gate 6 untouched.** No WP6.1–WP6.6 scope, sequencing, or evidence change; no pilot
  or pilot-evidence involvement. Gate 7 consumes Gate 6's *outputs* (a promoted,
  proven runtime) and nothing else.
- **No self-attestation.** Any Gate-7 deliverable property (register compliance, claim
  binding, provenance) is established by a gate or a distinct reviewer, never by the
  producing agent — the freeze's root-cause finding is binding design input.
- **No model-graded acceptance before WP6.2 T1b clears** (D-G5-1(a)/D-G6-2): interim
  review is deterministic gates + CodeRabbit + independent adversarial agents + Stephen.
- **Read-only consumption of canonical evidence.** Gate 7 cites the committed canonical
  artifacts (audit §3.2 list) content-addressed; it never migrates legacy task state,
  bus records, or APM logs into successor authority (P-026's core survives; only its
  "papers finish under APM" premise is amended).
- **Boundary amendments are explicit.** The exact P-026/P-034/WP6.7 wording changes
  appear as quoted old→new text with rationale, for Stephen's acceptance.

## 5. Process

1. Author drafts W9 + the Gate 7 addition on this branch
   (`docs/ars-gate7-legacy-integration-brief` or a successor `docs/` branch).
2. Independent adversarial review (distinct agent) → reconciliation → Stephen's
   exact-revision acceptance; review-then-merge throughout.
3. Nothing dispatches from the accepted documents until Gate 6's pilot-promotion
   milestone is recorded and Stephen separately authorizes Gate 7 opening.
