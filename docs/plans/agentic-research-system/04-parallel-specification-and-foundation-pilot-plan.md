# Parallel Specification and Foundation Pilot Plan

**Date:** 2026-06-30  
**Status:** Approved programme direction; W1/W2/W3 and W6 catalogue/addendum accepted; W4/W5 next<br>
**Authority:** P-026, approved by Stephen on 2026-06-30  
**Implementation authority:** None yet; foundation implementation requires the gates in section 4 and a separately approved implementation plan  
**Pilot boundary:** The first paper initiated after the two current APM-managed papers

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
| Successor specifications | W3 accepted; W4/W5, then foundation-critical W6/W7/W8 slices | Versioned ARS design documents | Begin W4 and W5 across the frozen W3 interface; review each bounded specification before its consumers proceed |
| Foundation implementation | Minimal production-intended ARS v1 | Activates only after section 4 gates and an approved implementation plan | Not yet authorized |
| Greenfield pilot | First paper initiated after the two current APM papers | ARS from project initialization after pilot preflight | Candidate not yet selected |

The lanes share lessons through dated evidence and decisions, not mutable task state or dual-owned files.

## 4. Sequence and gates

**Gate status at 2026-06-30:** W1 v0.3, W2 v0.3, and the W6 v0.2 initial catalogue passed under P-027. W3 v0.2 and the W6 F-025–F-030 reservation passed the written-specification portion of Gate 1 under P-028. Executable closure sizing and fixture results remain foundation-critical W6/W7 gates; no implementation authority follows.

### Gate 1 — W3 context contract

Specify context packets and manifests, retrieval by role/risk, provenance, staleness/conflict handling, compaction, procedural-memory selection, size budgets, and retrieval-recall evaluation.

**Exit:** The written context contract is accepted. Before implementation, F-025/F-026/F-021/F-022 must demonstrate mandatory closure under both token gates, and F-027–F-030 must satisfy the dated W6 addendum.

### Gate 2 — W4/W5 authority interfaces

After W3 freezes the context-manifest and independence inputs, specify W4 agent/model routing and W5 research assurance. They may proceed in parallel only across an explicitly frozen shared interface.

**Exit:** Routing is reproducible from risk/eval evidence, and R2/R3 work cannot bypass independent scientific review or human-reserved decisions.

### Gate 3 — Foundation-critical W6/W7/W8 slices

Before implementation planning, freeze:

- the minimum executable W6 fixture set and non-aggregated P0 release gate;
- the provider-adapter command/receipt and semantic-parity boundary from W7;
- the writer lease, resource, checkpoint, recovery, backup, and operator boundary from W8.

Full W6–W8 specifications may continue later, but no foundation code may depend on an unspecified critical interface.

### Gate 4 — Foundation implementation plan

The implementation plan must map every component to accepted W1–W5 decisions, the minimum W6–W8 gates, deterministic tests, fixtures, failure behavior, and rollback. The W1/W2 review prerequisite passed under P-027. T1.28 terminal completion is not required.

**Exit:** Stephen approves the implementation plan and its exact foundation scope.

### Gate 5 — Foundation acceptance

The foundation passes its required deterministic tests, P0 fixtures, recovery cases, adapter parity checks, and bounded independent review. Failures produce revision or stop; they do not weaken the acceptance set.

### Gate 6 — Greenfield paper preflight

The first post-APM paper may become the pilot only when its initial workflow is non-critical, its inputs and authority are clear, the foundation has passed Gate 5, and rollback can occur without changing accepted research evidence.

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

Author W4 agent/model routing and W5 research assurance in parallel across accepted W3 v0.2. Preserve the P-028 two-gate accounting, independent-verifier, delta-exposure, and F-025–F-030 dependencies; do not begin foundation implementation.
