# Parallel Specification and Foundation Pilot Plan

**Date:** 2026-06-30  
**Status:** W1–W5 and Gate 3 accepted under P-027–P-030; P0 plan suite written and review pending; no implementation authority<br>
**Authority:** P-026, approved by Stephen on 2026-06-30  
**Implementation authority:** None yet; foundation implementation requires the gates in section 4 and a separately approved implementation plan  
**Pilot boundary:** The first paper initiated after the two current APM-managed papers

**Currency note (2026-10-22, G7-C):** The header fields, §§1–3 and 5–8, and §4's Gates 1 to 6 are the 2026-06-30 and
2026-07-01 text and are not re-derived here. Gate 6 closed on 2026-10-21 against the accepted 06s §4 contract (P-058).
§4 now ends with Gate 7, added by G7-C. When P-062 is accepted, it holds the operative wording of the §2, §5, §6 and §7
sentences it amends; until then the text below stands.

## 1. Purpose

T1.28 is a heavy legacy computation that may remain active for up to a week. Its duration does not create a useful reason to suspend ARS design. This plan separates the continuing APM research lane from a successor-system lane so specification and, after explicit gates, a narrow production-intended foundation can advance without touching current research authority.

The foundation is not disposable. It is the smallest defensible ARS v1 intended to evolve into the permanent system. Its first research testbed is a clean paper created under ARS after the two papers currently governed by APM.

## 2. Binding boundary

T1.28 and the two current papers remain entirely `legacy_owned`. Their tasks, bus state, contracts, processes, checkpoints, results, logs, reviews, decisions, and claims are never migrated into the prototype and are never used as live pilot inputs.

T1.28 completion gates:

- final W0 currency and Phase 1 closeout;
- any proposal to migrate or adopt legacy APM evidence;
- deprecation of legacy APM authority;
- claims that the historical transition boundary is sealed.

T1.28 completion does not gate:

- W3, W4, or W5 specification work;
- the foundation-critical W6, W7, and W8 interface slices;
- an implementation plan for a non-migrating foundation after the specification gates pass;
- construction and synthetic/historical-fixture evaluation of that foundation;
- initialization of the first post-APM paper as a greenfield ARS pilot once its pilot gate passes.

When T1.28 reaches a reviewed terminal disposition, its new evidence triggers a dated W0 addendum and bounded delta review. That review may amend the foundation but does not invalidate it by default.

## 3. Parallel lanes

| Lane | Scope | Authority | Current action |
|---|---|---|---|
| Legacy research | T1.28 and the two current APM-managed papers | APM remains canonical | Continue compute and event-triggered closeout; no ARS writes or migration |
| Successor specifications | W3–W5 and Gate 3 accepted; P0 plan suite written; addenda 06a/06b reserve F-025–F-038 | Versioned ARS design/plan documents | Run the bounded P0 plan review; no implementation yet |
| Foundation implementation | Minimal production-intended ARS v1 | Activates only after section 4 gates and an approved implementation plan | Not yet authorized |
| Greenfield pilot | First paper initiated after the two current APM papers | ARS from project initialization after pilot preflight | Candidate not yet selected |

The lanes share lessons through dated evidence and decisions, not mutable task state or dual-owned files.

## 4. Sequence and gates

**Gate status at 2026-07-01:** W1–W5, the W6 catalogue/reservations, and Gate 3 W6 v0.3/W7 v0.2/W8 v0.2/06c v0.2 are accepted under P-027–P-030. No executable closure sizing, fixture result, adapter, process, or runtime evidence is claimed.

### Gate 1 — W3 context contract

Specify context packets and manifests, retrieval by role/risk, provenance, staleness/conflict handling, compaction, procedural-memory selection, size budgets, and retrieval-recall evaluation.

**Exit:** The written context contract is accepted. Before implementation, F-025/F-026/F-021/F-022 must demonstrate mandatory closure under both token gates, and F-027–F-030 must satisfy the dated W6 addendum.

### Gate 2 — W4/W5 authority interfaces

The bounded joint adversarial review and reconciliation are complete. P-029 accepts W4 v0.2 and W5 v0.2 across W3's frozen interface and reserves addendum 06b. The requirement-scope authority rule, pre-dispatch verifier witness, R3 family-coverage block, and F-031–F-038 designs now govern downstream specification work.

**Exit:** Routing is reproducible from risk/eval evidence, and R2/R3 work cannot bypass independent scientific review or human-reserved decisions.

### Gate 3 — Foundation-critical W6/W7/W8 slices

Before implementation planning, freeze:

- the minimum executable W6 fixture set and non-aggregated P0 release gate;
- the provider-adapter command/receipt and semantic-parity boundary from W7;
- the writer lease, resource, checkpoint, recovery, backup, and operator boundary from W8.

The four written Gate 3 documents passed joint review and reconciliation under P-030. This closes the interface gate only; no foundation code or P0 fixture materialization may begin until Gate 4 approves the separate plan.

### Gate 4 — Foundation implementation plan

**Current status (2026-07-01):** The master plan and four separable work-package plans are written and `review_pending`. They define a 37-case P0 closure, exact files/tests/commits, independent review points, and stop conditions; they authorize no implementation.

The implementation plan must map every component to accepted W1–W5 decisions, the minimum W6–W8 gates, deterministic tests, fixtures, failure behavior, and rollback. The W1/W2 review prerequisite passed under P-027. T1.28 terminal completion is not required.

**Exit:** Stephen approves the implementation plan and its exact foundation scope.

### Gate 5 — Foundation acceptance

The foundation passes its required deterministic tests, P0 fixtures, recovery cases, adapter parity checks, and bounded independent review. Failures produce revision or stop; they do not weaken the acceptance set.

### Gate 6 — Greenfield paper preflight

The first post-APM paper may become the pilot only when its initial workflow is non-critical, its inputs and authority are clear, the foundation has passed Gate 5, and rollback can occur without changing accepted research evidence.

### Gate 7 — Legacy research integration

**Status (2026-10-22):** OPEN since 2026-10-22 (P-063). The bounded intake is the W9 implementation plan only. G7-C
revision 3 was accepted by Stephen on 2026-10-22 (P-062). This section authorizes no opening, dispatch,
implementation, import, transition or store write. Its old→new amendments to other texts are in register entry P-062.

**Objective.** Bring legacy research under ARS without writing a legacy file or upgrading a legacy record by its
status word. Gate 7 formalizes W9's acceptance and the execution of WP6.7 through 06l's Steps 1 to 7. Its first named
subjects are the two `legacy_owned` papers, P01-A and P01-B (P-026, P-034). Other legacy result families, P04's among
them, stay `legacy_owned` and unregistered until their own intake (W9-D13).

**Governing documents.**

| Document | State |
|---|---|
| G7-A: `transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md`, revision 3, blob `1ebcf96f` | Accepted 2026-10-22; W0 series `post_terminal_recorded`, not `sealed` |
| G7-B: W9, `design/09-migration-compatibility-and-pilot.md`, draft 0.5, blob `ea3a8e4a` | Accepted 2026-10-22; its conditions were completed by P-062's acceptance (`reviews/g7b-w9-owner-acceptance-2026-10-22.md`; completion record `reviews/g7c-gate7-definition-owner-acceptance-2026-10-22.md`) |
| G7-B Discovery inventory: `transition/discovery-backlog-observation-2026-10-22.md`, revision 2, blob `026a9d10` | Accepted 2026-10-22, for backlog bytes `96b5775c…` |
| G7-C: this section and P-062 | Accepted 2026-10-22, revision 3; see P-062's status line |

**Opening bar.** Gate 7 opens only when all four hold:

1. G7-A, W9 and G7-C are accepted at exact revisions;
2. Gate 6 closure evidence under the accepted 06s §4 contract is on file: P-058's recorded closure, the docs-only final
   PR #381 (`df5ba1ec`) and the post-merge frozen-checkout replay (#386, `bb9d91d4`);
3. Stephen records a separate opening decision that names the bounded intake it authorizes;
4. 06l Step 1, as P-062 amends it (A3, A4), holds: a distinct exact-subject check that the evidence on file is P-058's
   accepted closure evidence; no unresolved KAN-22 to KAN-26 contradiction; no provider or credential path; and no
   claim that a plan or Jira status is runtime evidence.

SCALE-01 is not a condition (06u D-2). The W0 post-terminal addendum is not an opening condition; it is already
accepted, and 06l Step 3 and later steps require it. Opening by itself imports, transitions, dispatches and implements
nothing.

**Per-item conditions.** W9 §4.5's matrix is the operative precondition list for each class of action. The conditions
below add to it and never relax it. Each also adds to the 06l step's own inputs, review and proof.

- **Pilot promotion.** Each item dispatches or is accepted only after the W6 `gate_stage: pilot_promotion` evidence for
  its W9 §12.3 set is produced, or explicitly waived by Stephen, with its fixture IDs named. W9 §12.3 assigns the set
  by item kind, including every result-family observation, every import and every review. The item's independent
  reviewer proposes the set and Stephen fixes it in the batch decision.
- **Phase 1 and Stage 2 state.** Any closed-reference batch acceptance, ownership transition, cutover, deprecation or
  retirement needs Stephen's W0-D1 signature on all eight W0 manifest §14 items (W9 §4.5), with the enumerated A-001
  (G7-A §10) signed after the independent check W0-D1 names. A transition, cutover, deprecation or retirement that the
  Stage 2 state affects also needs the Stage 2 scope decision (W0-D2, at 06l Step 3).
- **Discovery.** No Discovery item takes a 06l Step 3 or later action except on the accepted Discovery inventory
  (W0-D4). Under the inventory's acceptance record (`reviews/d8c-discovery-inventory-owner-acceptance-2026-10-22.md`):
  the inventory covers only backlog bytes `96b5775c…`, so a changed backlog needs a fresh accepted non-author
  observation first; a transition still needs a fresh handle-bound observation at transition time; and WT-2 and WT-3
  are revived only as new successor Candidates.
- **R3 items.** P-029's two-family rule applies at dispatch over P-005's full R3 set, with eligibility checked before
  dispatch (W9-D3, W9 §11.2). Without it the item records `r3_family_coverage_insufficient` and does not dispatch.
- **W0 currency.** The latest accepted W0 addendum must post-date every G7-A §17 trigger that has fired. It is required
  before any 06l Step 3 or later action (B1, B2). For T1.41 or the Markov-2 recompute, Stephen accepts the addendum
  recording the dispatch before dispatch (W9 §10 item 5).

**Work and order after opening.**

| Track | Content | Sequencing and own bar |
|---|---|---|
| W9 machinery | The W9 implementation plan: schemas, catalogue, bootstrap contract, genesis, detectors and commands, with W9 re-check Info I-c | A separately reviewed plan that Stephen approves, then implementation. The store is the one W9-D10 names, never the Gate 6 store, after W11's genesis in a new store, with P-059 re-acceptance. No W9 observation, import or transition precedes it |
| Legacy integration | 06l Steps 3 to 7 | The integration pilot comes first: a closed-reference batch under W9 §14.2, with thresholds pre-registered under W9 §14.3. Wider adoption needs Stephen's separate authorization after the pilot (W9-D12a). Papers come last, as whole roots (W9 §12.1) |
| Parked compute | T1.41 and the Markov-2 α=1 exact-W₂ recompute | New successor Tasks under W9 §10. Their preconditions are W9 §4.5's successor-compute row; outputs go only under the registered successor root `results/ars/` (W9 §10 item 4, W9-D14). Their legacy rows are proposed as members of the integration-pilot batch, within W9 §14.2's rubric and bound. Compute waits neither for those rows' acceptance nor for the pilot's threshold evaluation (G7C-D3), unless the compute uses such a row as an input: a legacy input it uses needs its closed-reference acceptance and adoption first (W9 §4.5). A missed threshold does not stop dispatched compute, and a wrong row is superseded under W9 §13.2. Markov-2 also needs Stephen's decision on review finding A1 (06u D-7) and a new pre-registration carrying the change A1 requires |
| SPEC-01 continuation | ARS-native, not legacy (06u D-3; P-061) | Needs Gate 7 open, then its own bar: a new route-package version with its own authority review, SPEC-02 v1.2.0 with R6, the R4 crosswalk task and the R5 threshold pre-registration (P-061 points 2 and 5 to 7) |
| Manuscript prose | H4, H8, the park-set prose directions and any rewrite | Waits for Gate 9's manuscript-review capability (W9-D7, P-047) |

Any project-use acceptance, including those of successor compute and the SPEC-01 continuation, needs either a public
writer for the governing scientific-review record or another option-A owner placement (06u §6.3, a P-058 follow-up).
The other P-058 follow-up, a public deriver for the verify-restore payload, is an intake unit below, not a blocker.
D-G5-1(a) still blocks M/H model-graded acceptance, so reviews are distinct-session reviews with Stephen's acceptance.

**Intake set.** The intake set is fixed at G7-C's acceptance as the units below. Each needs one attributed disposition.
06u §6 gives each unit's pointer and precondition; the acceptance record names the 06u blob it read. Adding or removing
a unit needs Stephen's recorded decision.

| Units | Count |
|---|---|
| A-001 items 1 to 12 (G7-A §10). They include T1.41 (item 1, hole H1), the Markov-2 recompute (item 2, hole H2), hole H3 (item 5), hole H7 (item 6) and hole H9 (item 10); each counts once | 12 |
| Audit holes not already in A-001: H4, H5 and H8 (H6 resolved by #129) | 3 |
| Stage 2 rows needing a disposition (G7-A §9) | 15 |
| Park-set bullets (G7-A §12): the #106 dedup prose, WT-3, WT-2, the §6.2/§4.3/§S6 prose directions, the t128 and ARS-scale briefs | 5 |
| The SPEC-01 continuation (06u §6.2, P-061), ARS-native | 1 |
| The P-058 follow-ups (06u §6.3): the scientific-review record writer and the verify-restore payload deriver | 2 |

Two groups of units name one object and take one consistent disposition: hole H4 with the park-set bullet for the
§6.2/§4.3/§S6 prose directions; and the park-set bullet for the #106 dedup prose with Stage 2 rows T2.17a and T2.24.
T1.20 (closed 2026-07-11) and #105 (remediated by #117) are closed records, not units. The enforcement inputs (06u §6.5)
bind every deliverable and are not units. P-060 (06u §6.4) is standalone, not Gate 7. The four strategy documents bind
as follows (KAN-17):

| Document | Binds |
|---|---|
| `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md` | Audit holes H1 to H9 (H6 resolved by #129); the audit verdicts carried as qualifiers on paper-root transitions; the artifact map from which the reviewer derives each paper's cited-family set (W9 §12.1) |
| `docs/plans/strategy/P01-Adversarial-Mathematical-Review-2026-07-18.md` | Finding A1 as A-001 item 3, A2 as item 4, A4 as item 9 and B1 to B7 as item 12 (G7-A §10); A3, the missing calibration, through item 1 (T1.41, whose design answers A3, W9 §10 item 2); class C findings in the prose track; no rung-4/5 rejection claim advances before A1 is decided and the calibration has run |
| `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md` | Invariants I1a to I11a, binding every Gate 7 deliverable |
| `docs/plans/strategy/Theorem-Derived-Invariant-Battery-2026-07-18.md` | The invariant battery (#131), including the P2 calibration harness, binding every Gate 7 deliverable and successor compute in particular |

**Owner decisions carried into intake, not decided here:** the A1 fork (06u D-7); the H3 scope (06u D-8); the risk
tier of T1.41 and of the Markov-2 recompute (06u D-6, §7 question 2); the §14 signatures (W0-D1); the Stage 2 scope
(W0-D2); the integration-pilot thresholds (W9 §14.3); wider adoption (W9-D12a); the dated W6 addendum for S-016
(W9-D12b); the W9 store (W9-D10).

**Stop and rollback.** W9 §13.4's stop criteria apply. They restate §7 for Gate 7 items, and where the two differ,
§13.4 governs a Gate 7 item. Rollback is one way and successor-side
(W9 §13.1). Before commit, a stop leaves the item `legacy_owned`. After commit, recovery goes by supersession or a
recovery record, and authority never returns to `legacy_owned` or to APM. No accepted research artefact, result or
decision changes.

**Exit.** Gate 7 closes when Stephen records its closure against this section, and only once:

- every intake unit has an attributed disposition: transitioned, accepted `closed_reference`, discharged by a
  successor result, completed under its own bar (the ARS-native units), scoped out by Stephen, or deferred by Stephen
  to a named later gate;
- each P01 paper root has transitioned under W9 §12.1, or Stephen has recorded that it stays `legacy_owned` and why.

Retiring an APM surface (06l Step 7) may happen inside Gate 7 but is not an exit condition (G7C-D2). After closure, a
remaining 06l Step 6 cutover or Step 7 retirement proceeds under 06l as P-062 amends it and under W9 §4.5, each by
Stephen's separate decision. It does not reopen Gate 7.

**Capability reporting.** Lead with the lowest row in the table whose condition holds, then the exact gap and the next
action. In an OPEN, INCOMPLETE row, a stop under W9 §13.4 is reported as "stopped under W9 §13.4: <criterion>". The
parked compute and SPEC-01 tracks each get one extra line naming their own state.

| Position | Required leading status |
|---|---|
| Documents not all accepted | Gate 7 status: NOT OPEN — one or more of G7-A, W9 and G7-C is not accepted; name which. |
| Documents accepted | Gate 7 status: OWNER-BLOCKED — the documents are accepted and the Gate 6 closure evidence is on file; the 06l Step 1 check (condition 4) and Stephen's opening decision are required. |
| Open; W9 machinery not accepted | Gate 7 status: OPEN, INCOMPLETE — no W9 implementation is accepted, so no observation, import or transition can run. |
| Open; machinery accepted; integration pilot not passed | Gate 7 status: OPEN, INCOMPLETE — the integration pilot is pending, running or failed against its pre-registered thresholds. |
| Open; pilot passed; units remain | Gate 7 status: OPEN, INCOMPLETE — wider adoption, batch transitions or paper roots are pending; name them. |
| Open; every unit disposed | Gate 7 status: OWNER-BLOCKED — every intake unit has an attributed disposition; Stephen's closure decision is required. |
| Closure recorded | Gate 7 status: CLOSED — closed against this section and its recorded evidence. |

## 5. Narrow foundation scope

The foundation includes only:

- project identity and stable control-store binding;
- one project-wide command service and writer lease;
- immutable objects, receipts, atomic event batches, hash-linked linear history, and verified snapshots;
- pure reducers and human-readable task/message/artefact/review/decision projections;
- the minimum Task, dispatch, attempt, Partial/blocker, message, artefact, validation, review, and Decision lifecycle;
- W3 context manifests and bounded packets;
- W4 actor, authority, risk, model-routing, and independence evidence;
- W5 assurance requirements and result-to-claim gates;
- the minimum W6 fixture runner and release report;
- the smallest Claude/Codex command adapters and local operator interface needed by the pilot;
- backup, restore, failure recovery, and auditable diagnostics.

The foundation excludes:

- migration or normalization of either current paper;
- imports that promote legacy evidence into successor authority;
- a distributed service, cloud scheduler, or network protocol;
- broad dashboards, autonomous portfolio optimization, or generalized workflow features not required by the pilot;
- complete domain-pack coverage beyond what the pilot and core regression suite require;
- replacement of Git, research code, paper folders, result roots, or external-data controls.

## 6. Pilot operating model

The pilot paper is initialized under ARS from inception. ARS is the sole successor authority for its task lifecycle. A legacy-style view may be generated for inspection, but unmodified APM tooling cannot write it and no dual ownership is permitted.

Initial pilot work should use bounded R0/R1 tasks and one representative R2 workflow before any paper-critical computation. Promotion to broader use requires:

- deterministic replay and recovery;
- no silent overwrite or ambiguous authority;
- complete input/output/code/model/context/review provenance;
- successful required scientific and operational graders;
- smaller context without reduced governing-evidence recall;
- acceptable operator burden;
- explicit Stephen approval for any R3 or claim transition.

## 7. Stop and rollback rules

Stop foundation or pilot progression when:

- a critical interface remains unspecified;
- a P0 fixture fails or cannot be graded independently;
- a second canonical writer or shared legacy path is required;
- the prototype would need current-paper data/state migration;
- required model or reviewer independence is unavailable;
- recovery cannot prove the canonical tail and projected state;
- operational overhead causes routine bypass of required controls.

Rollback preserves every event, artefact, verdict, and decision produced before the stop. It may retire the prototype or return the greenfield paper to manual operation, but it never rewrites accepted research evidence.

## 8. Immediate next action

Run a bounded adversarial review of the master P0 plan and four child plans, reconcile required changes, and obtain Stephen's exact-scope approval; do not begin implementation from the review-pending plan.
