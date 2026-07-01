# Post-Review Continuation Session Handover Prompt

You are continuing the Agentic Research System planning work in `C:\Users\steph\TDL` after the first adversarial review and Stephen's approval of its reconciled conclusions.

## Objective

Begin the approved second specification pass from the reconciled W0/W1/W2/W6 package. W3 is next, followed by W4/W5 and the foundation-critical W6/W7/W8 slices. Preserve the isolated T1.28/APM lane. Do not implement the foundation, migrate live work, or modify active APM/research state until the P-026 gates and a separately approved implementation plan authorize it.

## Repository anchors

- Planning root: `C:\Users\steph\TDL\docs\plans\agentic-research-system`
- Initial specification commit: `bcc3c0739e17869315f8744a50eac32e995dda13`
- Submitted adversarial-review commit: `33ab053e30fa5e564ac7cc999544dec2225e9ccb`
- Adversarial integration commit: `6c9a5ac93d52361af4f0294ca3ce4213922ad057`
- Parallel foundation authority: P-026, approved by Stephen on 2026-06-30
- Legacy bus ownership backport: `7c8de855`
- T1.6 authoritative merge anchor: `7e798464`
- Review verdict: `accept_with_required_changes`
- Review integration authority: Stephen, 2026-06-29
- Implementation authority: none

Verify the live cwd, branch, HEAD, status, and research state before writing. Treat commit anchors as provenance, not proof of current T1.28 state. Do not stage unrelated compute, checkpoint, recovery, or application files.

## Mandatory startup

1. Invoke `task-observer`, read OPEN observations for each skill loaded, and use stable observation identity: canonical path, exact title, date, and status—not a bare ordinal.
2. Read repository `AGENTS.md` and follow its cwd/branch, navigation, GitNexus, and commit rules.
3. Do not spawn subagents unless Stephen explicitly requests delegation or parallel agent work.
4. Prefer direct files over stale indexes. Verify any live-state claim against authoritative artefacts.
5. Preserve the submitted adversarial review and dated W0 manifest unchanged; add a dated record when state changes.

## Read order

1. `README.md`
2. `04-parallel-specification-and-foundation-pilot-plan.md`
3. `reviews/adversarial-review-reconciliation-2026-06-29.md`
4. `reviews/adversarial-first-pass-review-2026-06-29.md`
5. `transition/W0-legacy-closeout-transition-manifest-2026-06-28.md`
6. `transition/W0-legacy-closeout-transition-addendum-2026-06-29.md`
7. `03-decisions-and-open-questions.md`
8. `design/01-system-architecture.md`
9. `design/02-task-event-and-artifact-schema.md`
10. `design/06-evaluation-observability-and-audit.md`
11. `00-master-transition-plan.md`
12. `01-current-system-evidence.md`
13. `02-design-and-deliverables-roadmap.md`
14. `design/README.md`

The original PDFs and meta-research plan remain source material, not the first continuity read:

- `C:\Users\steph\Documents\TDA-Research\02-Notes\2025_Day_3_Rewrite_v1_ContextEngineering.pdf`
- `C:\Users\steph\Documents\TDA-Research\02-Notes\Day_1_v3.pdf`
- `C:\Users\steph\TDL\docs\plans\strategy\Meta-Research-Plan-23-03-2026.md`

Use the PDF skill if the PDFs need to be re-inspected.

## Settled decisions

Treat P-020 through P-026 as Stephen-approved decisions. P-020–P-025 retain their Manager-confirmation gates, while final reconciliation applies to legacy migration and legacy-derived claims; P-026 defines which successor work may proceed independently of T1.28:

- **P-020:** one project-wide command service writes one dedicated linear control store outside task-worktree branches; worktrees submit commands and never allocate canonical ledger positions.
- **P-021:** successor-owned compatibility files use non-shared namespaced paths; any Task handled through unmodified legacy Worker slots remains `legacy_owned`.
- **P-022:** independence is graded and checkable. R0/R1 may use delegated Manager acceptance; R2 requires a verifier context distinct from implementation plus Manager acceptance; R3 and P-005 transitions require Stephen.
- **P-023:** scientific graders must independently establish the asserted property and record producer/grader family and context diversity; required diversity fails closed.
- **P-024:** fixture provenance records both incident basis and input fidelity; the catalogue now reserves F-021–F-024 and S-011–S-016.
- **P-025:** proportional profiles keep R0 minimal and support qualitative work without pretending deterministic scientific validation is available.
- **P-026:** proceed W3 → W4/W5 → foundation-critical W6/W7/W8 → approved implementation plan → narrow permanent foundation → first post-APM paper pilot. T1.28 and both current papers remain legacy-owned and cannot be migrated into the prototype.

Do not reopen these decisions by preference. A proposed supersession requires contrary evidence, a concrete failure mode, affected gates, and an attributed decision.

## Current status and gates

### W0

- Status remains `PARTIAL`: the manifest exists, but the legacy boundary is not sealed.
- T1.28 was active and incomplete at the 2026-06-29 addendum check: compute/checkpoint evidence existed, but no final `stratified_w2_*.json` and no `task-01-28.log.md` existed.
- Stephen expects the heavy computation may take up to a week. This is a planning estimate, not a result-state claim; inspect only the declared W0 currency triggers.
- T1.28 and all related files/processes/contracts/checkpoints/bus state remain `legacy_owned` and in the no-migration set.
- A-001 remains pending until T1.28 reaches a reviewed terminal disposition and the current Manager confirms Phase 1 closure.
- A-002 remains scope-qualified: eight Wave-1 outputs retain their recorded authority, while fourteen Plan-defined Stage 2 tasks require acceptance, deferral, removal, or explicit supersession.
- If any of this has changed, add a new dated W0 currency record; do not rewrite the 2026-06-28 manifest or 2026-06-29 addendum.

### W1

- Revision 0.3 integrates the adversarial architecture amendments and the P-026 foundation/migration gate split.
- Manager confirmation remains pending; final post-T1.28 reconciliation remains a legacy-migration gate.
- Outcome remains `MANAGER_REVIEW_PENDING`; greenfield-foundation implementation also requires the P-026 downstream gates, while legacy migration remains prohibited.

### W2

- Revision 0.3 integrates concurrency, compatibility, independence, typed-referent, retention, recovery, replay, and the P-026 gate split.
- Manager review remains pending.
- No runtime, JSON Schema implementation, event store, adapter, or migration authority follows from the specification alone; P-026 still requires Manager confirmation, downstream interface gates, and an approved implementation plan.

### W6

- Revision 0.2 is a 40-fixture catalogue: F-001–F-024 and S-001–S-016.
- It adds two-axis fixture provenance, independent scientific-property grading, grader-diversity evidence, proportional profiles, qualitative coverage, and non-aggregated P0 gates.
- It is not an executable W6 implementation. Materialization, grader code, thresholds, trace schemas, retention, and tooling remain separately gated.

### Parallel successor lane

- W3 is authorized as the next specification while T1.28 remains active.
- W4/W5 follow the frozen W3 shared interface.
- Foundation-critical W6/W7/W8 slices precede any implementation plan.
- The prototype is a narrow production-intended foundation, not disposable scaffolding.
- Its research pilot is the first paper initiated after the two current APM-managed papers, under ARS from inception.
- W1/W2 Manager confirmation and Stephen's approval of the implementation plan remain required; T1.28 terminal completion does not.

## Revised design in one view

ARS remains a provider-neutral, domain-general local control plane with optional specialist assurance packs. Canonical mutation occurs through one serialized project command boundary into a dedicated linear control store. The code repository holds versioned schemas, policies, pack definitions, adapters, eval definitions, and the stable store binding; task worktrees hold neither independent canonical ledgers nor shared successor/legacy bus slots.

W2 keeps immutable identities, commands, receipts, append-only events, deterministic reducers, typed artefact authority, explicit attempts/reviews/decisions, exact subject binding, compensating corrections, verified snapshot anchors, and lifecycle states that cannot be changed by messages alone. W6 tests these controls with historical and synthetic fixtures while keeping scientific validity distinct from software correctness.

## Next work

1. Verify package integrity, P-026, and the live repository boundary.
2. Author W3 as a bounded specification consuming W1/W2 v0.3 and P-020–P-026.
3. Make W3 freeze the context-manifest, omission, provenance, staleness, budget, and independence inputs required by W4/W5.
4. Review W3 before beginning W4/W5; allow W4 and W5 to overlap only across the frozen shared interface.
5. Define the foundation-critical W6/W7/W8 slices and run a bounded combined-interface review.
6. Obtain W1/W2 Manager confirmation, then prepare a separate foundation implementation plan for Stephen's approval.
7. Monitor T1.28 only through W0 currency triggers and add a dated reconciliation when terminal evidence appears. Do not make W3–W8 wait on routine compute progress.

## Stop conditions

- Stop before any action that changes active APM/research state, ownership, authority, pre-registration, scope, or claim status.
- Stop before foundation runtime work until W1/W2 Manager confirmation, accepted W3–W5 specifications, foundation-critical W6–W8 gates, and Stephen's approval of an exact implementation plan.
- Treat missing or contradictory evidence as `Partial` or `decision_required`; do not infer completion from an empty bus, `Success`, merged prose, or a dashboard.
- Keep exact pre-registered designs and hard runtime guardrails intact unless an attributed amendment changes them.
- Never place raw UKDA data, secrets, `.env` content, hidden reasoning, or full transcripts into reusable contexts, fixtures, or audit records.
- If a proposed change reverses a Stephen-approved amendment or expands implementation authority, present the evidence and request a decision before editing the accepted direction.

## Completion standard for the next session

Return a concise status containing: live W0 currency, the completed W3 work or blocker, W1/W2/W6 review state, and the exact next successor gate. Do not relitigate settled decisions, turn routine T1.28 progress into a design hold, or imply foundation implementation authority.
