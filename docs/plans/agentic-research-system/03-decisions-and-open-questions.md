# Decisions and Open Questions

**Decision register opened:** 2026-06-27  
**Scope:** Agentic Research System transition

## Accepted directions

### D-001 — Create a dedicated working folder before implementation

**Status:** Accepted  
**Decision:** Capture the complete rationale, evidence, target architecture, transition plan, and future deliverables in a durable repository folder before producing implementation specifications.

### D-002 — Treat this as a system redesign, not a collection of prompt edits

**Status:** Accepted  
**Decision:** The design scope includes task state, context, memory, agent roles, model routing, research assurance, provenance, evaluation, observability, runtime adapters, recovery, and portfolio governance.

### D-003 — Preserve the strongest APM mechanisms

**Status:** Accepted  
**Decision:** Preserve and generalise the current bus concept, contracts, pre-registration, provenance manifests, worktrees, non-overwriting outputs, task logs, review lanes, and explicit Partial/blocking outcomes.

### D-004 — Build a domain-general core

**Status:** Accepted  
**Decision:** The core system must support mathematical and social research beyond TDA. TDA-specific topology, Wasserstein, representation, and null-model controls will become optional domain assurance packs.

### D-005 — Transition at a phase boundary

**Status:** Accepted in principle  
**Decision:** Use the end of Paper 1 Phase 1 as the design and transition window. Do not force already-developed Phase 2 work through a disruptive migration.

### D-006 — Keep high-reasoning models on epistemically risky work

**Status:** Accepted  
**Decision:** Opus-class orchestration/design and Codex xhigh implementation remain the default for high-risk mathematical tasks until eval evidence supports a change. Efficiency work should first reduce irrelevant context, repeated work, and manual coordination.

### D-007 — Separate scientific authorities

**Status:** Accepted  
**Decision:** For consequential tasks, the same agent must not be the sole author, implementer, verifier, and approver of a research contract or decision rule.

### D-008 — Use a local, inspectable control plane first

**Status:** Accepted  
**Decision:** Begin with repository-managed schemas, append-only records, and generated views. Borrow protocol ideas such as task identity, lifecycle, messages, and artefacts without initially adopting a network service or external orchestration framework.

## W1 decisions accepted under P-027

Stephen approved these decisions on 2026-06-28, and their review gate passed under P-027 on 2026-06-30. T1.28 remains a legacy-closeout and migration gate, not a condition on their accepted greenfield design authority.

### P-001 — Canonical event storage and optional indexes

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Use append-only JSONL and immutable manifests as canonical storage. SQLite, full-text, graph, vector, dashboard, Tracker, and bus views are disposable projections. Complete state must rebuild without them.  
**Rationale:** This preserves local inspectability and version control while preventing a mutable database or view from becoming hidden authority.  
**Evidence:** W0 fixtures F-001–F-006 and accepted direction D-008.  
**Affected specifications:** W1, W2, W3, W6, W9.  
**Migration consequence:** Existing APM files remain authoritative only for declared legacy-owned tasks; successor state is not reconstructed from mutable views.

### P-002 — Neutral system root

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Retain the working name Agentic Research System and place its provider-neutral installed core under `.research-system/`.  
**Rationale:** The successor must be reusable beyond APM, TDL, TDA, Claude, and Codex while remaining repository-local.  
**Evidence:** Accepted directions D-002, D-004, and D-008.  
**Affected specifications:** W1, W7, W9, W10.  
**Migration consequence:** `.apm/` becomes a guarded compatibility surface and frozen legacy source, not the successor's canonical root.

### P-003 — Serialized command boundary

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Use a modular-monolith architecture in which one local command boundary validates authority and serializes canonical event writes. Agents, Workers, hooks, adapters, and execution processes submit commands rather than editing state directly.  
**Rationale:** Append-only files alone do not prevent concurrent corruption, stale writes, or unauthorized transitions. A narrow writer preserves simple local operation without introducing a distributed service.  
**Evidence:** W0 fixtures F-001–F-004, F-009, and F-014.  
**Affected specifications:** W1, W2, W7, W8.  
**Migration consequence:** Legacy direct edits continue only inside declared legacy ownership; successor-owned tasks use commands and generated views.

### P-004 — Exclusive compatibility ownership

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Every bridged task is exactly one of `legacy_owned`, `successor_owned`, or `closed_reference`; a `dual_owned` state is prohibited.  
**Rationale:** Dual canonical writes would preserve the overwrite and source-precedence failures that the redesign exists to remove.  
**Evidence:** W0 no-migration set and fixtures F-001–F-006, plus the main-checkout/worktree split in the evidence register.  
**Affected specifications:** W1, W2, W7, W9.  
**Migration consequence:** T1.28, T0.3, unresolved Stage 2 work, and all other no-migration items remain `legacy_owned` until explicit closeout or cutover.

### P-005 — Reserved human-approval transitions

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Reserve pre-registration changes, R3 dispatch, decision-lock reversal, claim promotion, and upgrading imported evidence from provisional to authoritative for Stephen's explicit approval.  
**Rationale:** These transitions change methodological authority, publication claims, or the interpretation of historical evidence and must not be inferred from agent output or operational acceptance.  
**Evidence:** Accepted directions D-005–D-007 and the W0 source-precedence and no-migration findings.  
**Affected specifications:** W1, W2, W4, W5, W9.  
**Migration consequence:** Legacy wording such as `Success`, `Done`, or a merged draft cannot be imported as one of these approvals without an explicit decision record.

## W2 decisions accepted under P-027

These schema decisions passed the W2 review gate and are accepted under P-027.

### P-006 — Atomic event batch per accepted command

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Publish one immutable JSONL event-batch file per accepted command, using atomic rename as the commit point; prohibit concurrent raw appends to a shared event file.  
**Rationale:** This preserves JSONL authority while making multi-event commands, crash recovery, and Git inspection reliable.  
**Evidence:** W1 P-001/P-003 and W0 fixtures F-001–F-004.  
**Affected specifications:** W2, W6, W8, W9.  
**Migration consequence:** Legacy files remain observations or projections; successor state begins only at a committed event batch.

### P-007 — Prefixed UUIDv7 canonical identities

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Use a three-letter kind prefix plus UUIDv7 for first-class canonical IDs; retain APM Task numbers, paper IDs, branch names, provider names, and agent slugs as scoped aliases.  
**Rationale:** Canonical identity must remain stable across projects, providers, paths, retries, and migrations without sacrificing rough time locality.  
**Evidence:** W0 overwrite, wrong-root, attempt, and source-precedence findings.  
**Affected specifications:** W2–W10.  
**Migration consequence:** Historical aliases resolve only with namespace and project scope and never become primary keys.

### P-008 — Separate Task and operational state machines

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Keep research-governance Task status separate from dispatch, attempt, lease, checkpoint, review, and artefact state; derive `queued`, `claimed`, `running`, and `checkpoint_available` as operational projections.  
**Rationale:** One status label cannot coherently represent readiness, process activity, evidence review, and scientific acceptance.  
**Evidence:** W0 fixtures F-002, F-004, F-007–F-009 and the stale T1.6 Task log.  
**Affected specifications:** W2, W3, W4, W6, W8, W9.  
**Migration consequence:** APM status text requires explicit mapping and cannot directly produce an accepted successor state.

### P-009 — Immutable messages and clearing-as-acknowledgement

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Record message publication, delivery, and acknowledgement as immutable events; treat clearing a generated APM task/report file as acknowledgement of a projection, never deletion of history.  
**Rationale:** Communication must remain distinguishable from lifecycle mutation and must survive single-slot reuse.  
**Evidence:** W0 fixtures F-001/F-002, evidence register §4.3, and the canonical Task Observer observation titled “Bus writes need explicit ownership, not only read-before-write” (2026-06-28; `C:\Users\steph\.Codex\skill-observations\log.md`).  
**Affected specifications:** W2, W6, W7, W9.  
**Migration consequence:** Compatibility writes require matching Task, agent, message, source-position, and content-hash ownership markers and fail closed on collision.

### P-010 — Partial and reopen preserve execution epochs

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Allow Partial as an attempt outcome and as a closed Task outcome; an authorized reopen creates a new execution epoch while preserving the original Partial evidence, claim restrictions, and stop reason.  
**Rationale:** Long mathematical runs need resumability without rewriting an earlier guardrail-triggered or evidence-limited outcome as if it never occurred.  
**Evidence:** T1.6 guarded attempts, T1.9b checkpoint recovery, and W1's Partial invariant.  
**Affected specifications:** W2, W4, W5, W6, W8.  
**Migration consequence:** Follow-up legacy work imports as linked attempts/epochs rather than replacement status prose.

### P-011 — Multidimensional artefact authority

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Represent artefact availability, integrity, structural validation, scientific review, and use authority as separate dimensions; prohibit a single `valid` or `accepted` boolean from collapsing them.  
**Rationale:** A file can exist and validate structurally while remaining scientifically invalid, superseded for claims, or usable only for comparison.  
**Evidence:** W0 fixtures F-010–F-019 and accepted direction D-007.  
**Affected specifications:** W2, W3, W5, W6, W9.  
**Migration consequence:** Existing result statuses require consumer-scoped adoption and preserve superseded-but-live provenance.

### P-012 — Versioned scope definitions govern milestone completion

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Require every stage/wave/milestone completion command to name an exact ScopeDefinition revision and a typed disposition for every required member.  
**Rationale:** Completion is a claim about approved scope, not the subset currently visible in a mutable Tracker.  
**Evidence:** W0 Stage 2 scope conflict, fixture F-005, and Task Observer Observation 6.  
**Affected specifications:** W2, W6, W9, W10.  
**Migration consequence:** The legacy “Stage 2 complete” projection cannot be adopted unless the fourteen unlogged tasks are reconciled or removed by a versioned scope amendment.

### P-013 — Review verdicts bind to exact subject hashes

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Bind each review request and verdict to exact object/artefact hashes and declared independence requirements; changed subjects require a new or explicitly bounded-delta review.  
**Rationale:** A review of an earlier implementation or result must not silently approve a changed producer output.  
**Evidence:** W0 fixtures F-014–F-020 and W1 scientific-authority boundaries.  
**Affected specifications:** W2, W4, W5, W6, W7.  
**Migration consequence:** Legacy review prose is adopted only when its inspected subject and authority can be identified.

## W6 initial-catalogue decisions accepted under P-027

These evaluation decisions passed the initial W6 catalogue review gate and are accepted under P-027.

### P-014 — Paired pre-control and post-control evidence

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Every active fixture must demonstrate the intended pre-control failure and a known-good post-control pass under versioned inputs and oracles.  
**Rationale:** A fixture that only passes a preferred implementation does not prove it detects the historical defect.  
**Evidence:** W0 fixture requirement and F-001–F-020.  
**Affected specifications:** W6, W7, W9.  
**Migration consequence:** Historical cases require minimized source-verified baselines before becoming release gates.

### P-015 — Critical graders are non-compensable

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Required deterministic, trajectory, privacy, and scientific hard gates cannot be offset by a weighted aggregate score.  
**Rationale:** Overwrite, invalid inference, unauthorized approval, provenance conflict, leakage, and claim overreach remain failures regardless of other metrics.  
**Evidence:** W0 failure corpus and W1 evidence-before-status principle.  
**Affected specifications:** W5, W6, W7.  
**Migration consequence:** Existing benchmark averages cannot alone authorize an R2/R3 model, adapter, or workflow change.

### P-016 — Deterministic-first grading

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Grade objective state, trace, schema, number, path, hash, authority, and ordering claims deterministically; reserve model/human graders for bounded conceptual and interpretive judgments.  
**Rationale:** Model judgment should not add variance where an executable predicate can decide the requirement.  
**Evidence:** W1 machine-check principle and W2 deterministic replay design.  
**Affected specifications:** W5, W6.  
**Migration consequence:** Each legacy review claim is classified as deterministic, model-graded, or human-authority before fixture materialization.

### P-017 — Minimized and redacted fixture sources

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Fixtures use synthetic or minimized source bundles, hashes, and excerpts; raw UKDA data, secrets, full transcripts, and hidden reasoning are prohibited.  
**Rationale:** Regression evidence must be reproducible without expanding confidentiality or prompt-leakage risk.  
**Evidence:** W0 no-migration set and W1/W2 trust boundaries.  
**Affected specifications:** W6, W9, W10.  
**Migration consequence:** TDL-private fixtures remain separated from public project-template fixtures and may use opaque local references.

### P-018 — Change-to-fixture coverage manifests

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** Every model, reasoning, prompt, policy, skill, hook, schema, reducer, context, grader, or adapter change declares affected fixtures, omissions, results, regressions, and authority.  
**Rationale:** Harness changes are otherwise deployed without an auditable statement of regression coverage.  
**Evidence:** W0 F-020 and W1 evaluation/observability boundary.  
**Affected specifications:** W3–W8.  
**Migration consequence:** Provider/model changes cannot rely on informal spot checks for the risk tiers they serve.

### P-019 — P0 and P1 fixture gates

**Date:** 2026-06-28  
**Status:** Accepted under P-027<br>
**Decision:** F-001–F-005, F-007–F-014, and F-020 are P0 implementation/release blockers; F-006 and F-015–F-019 are P1 gates before a research pilot promotes evidence or claims.  
**Rationale:** The W0 priority set protects foundational state, operations, scientific validity, authority, and parity before higher-level claim workflow.  
**Evidence:** W0 priority declaration and W2 fixture mapping.  
**Affected specifications:** W6, W7, W9.  
**Migration consequence:** Pilot selection cannot bypass an uncalibrated or failing relevant P0/P1 fixture.

## Adversarial-review amendments approved 2026-06-29

These amendments implement the approved reconciliation of review commit `33ab053e`. They preserve the earlier decision text as historical rationale and take precedence where they narrow or qualify it. The review confirmation passed under P-027; the existing implementation and migration gates still apply.

### P-020 — Project-wide single writer and dedicated linear ledger

**Date:** 2026-06-29  
**Status:** Accepted under P-027<br>
**Amends:** P-001, P-002, P-003, P-006; Q-001, Q-002  
**Decision:** One project-wide command service owns one dedicated canonical control-store root with a protected linear history. Task worktrees submit commands and never allocate canonical positions, advance event chains, or hold independently writable ledger copies.  
**Storage boundary:** The code repository's `.research-system/` root holds tracked schemas, policies, pack declarations, adapter/eval definitions, and a stable control-store binding. Dynamic canonical events, immutable objects, receipts, and accepted manifests live in the dedicated ledger repository/root outside task-worktree branches.  
**History rule:** The global position and hash chain remain valid because one writer allocates them. Ledger history is never rebased, reset, merged from task branches, or corrected by reverting event files; corrections are compensating events.  
**Rationale:** This retains plain-file/Git inspectability without reproducing the main-checkout/worktree split or creating a distributed merge algorithm.  
**Affected specifications:** W1, W2, W6, W8, W9.

### P-021 — Non-shared legacy compatibility paths

**Date:** 2026-06-29  
**Status:** Accepted under P-027<br>
**Amends:** P-003, P-004, P-009  
**Decision:** A successor-owned Task never shares the mutable legacy `task.md` or `report.md` slot. Compatibility projections use registered ARS-namespaced paths that unmodified legacy tooling does not write. If an unmodified APM Worker must use the legacy bus, the Task remains `legacy_owned`.  
**Rationale:** Ownership markers checked only by ARS cannot prevent a direct legacy writer from overwriting a shared path. Hooks may add protection but do not establish authority.  
**Affected specifications:** W1, W2, W6, W7, W9.

### P-022 — Graded independence and delegated acceptance

**Date:** 2026-06-29  
**Status:** Accepted under P-027<br>
**Amends:** D-007, P-005, P-013; Q-004, Q-006  
**Decision:** Independence is a checkable evidence profile, not a role label or attestation. R0/R1 may use delegated Manager acceptance; R2 requires a verifier context distinct from the implementer plus Manager acceptance; R3 and every P-005 transition require Stephen. Solo operation records contextual/model independence honestly and never claims independent human authorities that do not exist.  
**Evidence rule:** Review records bind actor, role, session, model family/version, context manifest, trace-visibility policy, subject hash, and relationship to the producing attempt. The verifier inspects the subject artefact but does not inherit implementer conclusions or hidden reasoning.  
**Affected specifications:** W1, W2, W3, W4, W5, W6.

### P-023 — Independent scientific-property grading

**Date:** 2026-06-29  
**Status:** Accepted under P-027<br>
**Amends:** P-014, P-016  
**Decision:** A deterministic or trajectory grader cannot certify a scientific property from a producer-emitted pass flag. It independently recomputes or bounds the property from immutable fixture inputs. Scientific model graders declare their relationship to the producer and use a different model family when the fixture requires family diversity; unavailable required diversity is blocking.  
**Calibration rule:** Scientific fixtures include producer-correlated errors and mutations that exercise plausible constant, no-op, fallback, or otherwise degenerate paths.  
**Affected specifications:** W5, W6.

### P-024 — Fixture provenance and expanded coverage

**Date:** 2026-06-29  
**Status:** Accepted under P-027<br>
**Amends:** P-014, P-018, P-019  
**Decision:** Fixture provenance separates historical incident basis from input fidelity. F-001 and the overwrite portion of F-002 are `historical` incidents with `reconstructed` fixture inputs. Reserve F-021–F-024 and S-011–S-016 with the priorities and dependencies recorded in W6.  
**Rationale:** A destroyed source message cannot be represented as preserved historical input, while the observed failure can still motivate a calibrated reconstruction.  
**Affected specifications:** W3, W5, W6, W7, W8, W9, W10.

### P-025 — Proportional operating profiles

**Date:** 2026-06-29  
**Status:** Accepted under P-027<br>
**Decision:** Define a minimal R0 command/event/receipt fast path, a small-project profile, and an explicit qualitative/non-computational assurance boundary. Deterministic scientific validation may be `not_applicable` for qualitative artefacts, but provenance, lifecycle, review, authority, and claim controls still apply.  
**Rationale:** Controls that are disproportionate to reversible work will be bypassed; domain-generality must not imply quantitative validation where none is meaningful.  
**Affected specifications:** W1, W2, W4, W5, W6, W10.

### P-026 — Parallel specification and clean-paper foundation pilot

**Date:** 2026-06-30  
**Status:** Accepted by Stephen  
**Gate amendment:** Supersedes any W1/W2 wording that makes T1.28 terminal completion a prerequisite for a non-migrating greenfield foundation; it remains a prerequisite for legacy closeout and migration claims.  
**Decision:** ARS specification work continues while T1.28 remains active. After the now-satisfied W1/W2 review gate, accepted W3–W5 specifications, foundation-critical W6–W8 interface gates, and a separately approved implementation plan, a narrow production-intended ARS foundation may be built without waiting for T1.28 to finish. The first research pilot is the first paper initiated after the two papers currently governed by APM, created under ARS from inception.
**Legacy boundary:** T1.28 and both current papers remain `legacy_owned`; the foundation cannot write, migrate, normalize, or promote their tasks, evidence, decisions, or claims. T1.28 terminal review still triggers a W0 addendum and bounded design reconciliation.  
**Rationale:** A multi-day legacy computation is a valid migration boundary but not a useful global hold on independent successor design. A clean-paper pilot tests the permanent system without contaminating current research authority.  
**Implementation rule:** This decision authorizes the specification sequence and later implementation planning. Runtime implementation begins only after the named gates and Stephen's approval of the exact implementation plan.  
**Affected specifications:** W1, W2, W3, W4, W5, W6, W7, W8, W9, W10; master plan and continuation protocol.

### P-027 — W1/W2/W6 review acceptance

**Date:** 2026-06-30<br>
**Status:** Accepted by Stephen<br>
**Decision:** Stephen confirmed that W1 v0.3, W2 v0.3, and the W6 v0.2 initial catalogue had been reviewed and passed. Their pending review gates are closed and their interfaces may govern W3 and the remaining P-026 specification sequence.<br>
**Boundary:** W6 acceptance covers the 40-fixture catalogue and its grading/provenance rules, not executable fixture materialization, thresholds, retention, or tooling. No runtime implementation, migration, pilot, or active APM change follows from this acceptance.<br>
**Evidence:** `reviews/w1-w2-w6-review-acceptance-2026-06-30.md` and Stephen's direct 2026-06-30 confirmation.<br>
**Remaining gates:** Accepted W3–W5, frozen foundation-critical W6–W8 interfaces, and Stephen's approval of a separately reviewed implementation plan. T1.28 remains the legacy-closeout/migration boundary only.<br>
**Affected specifications:** W1, W2, W3, W4, W5, W6, W7, W8; package status and continuation protocol.
## Assumptions requiring confirmation

### A-001 — T1.28 is the final Phase 1 task

**W0 status (addendum 2026-06-29):** Pending; the current Manager's sole-open-task statement remains the coordination basis, but T1.28 is now active and Phase 1 closeout is not confirmed.  
**Current basis:** T1.6 is authoritatively re-merged at `7e798464`. Commit `e7204373` records T1.28's extractor-defect blocker and follow-up; compute logs/checkpoints exist, but no final `stratified_w2_*.json` or task log existed at the addendum check.  
**Confirmation condition:** The current Manager confirms no additional Phase 1 computational or assurance task remains open after T1.28 review and closeout.  
**Effect if false:** The design work can continue, but the migration pilot moves to the first clean boundary after the remaining task.

### A-002 — Existing Phase 2 artefacts remain authoritative

**W0 status (2026-06-28):** Partially confirmed and scope-qualified.  
**Current basis:** Eight Wave-1 Stage 2 task logs are `Success` and their commits are ancestors of `main`. The Plan still defines twenty-two Stage 2 tasks; fourteen have no Stage 2 task log, including the T2.22 v2-completion gate.  
**Confirmation condition:** The Manager and Stephen confirm whether those fourteen tasks remain required or formally supersede them in the Plan.  
**Effect if false:** Provisional items are carried into the new ledger as imported history with explicit confidence and review state; they are not silently upgraded.

## Bounded design decisions

These questions must be resolved in the specifications. They are deliberately bounded so they do not become open-ended architecture debates.

### Q-001 — Canonical event storage

**Decision to make:** Append-only JSONL alone, or JSONL plus a rebuildable SQLite index.  
**Default recommendation:** JSONL is canonical; SQLite is a disposable local projection for queries and dashboards.  
**W1 disposition:** P-001 as amended by P-020: a project-wide single writer owns a dedicated linear ledger; SQLite remains a disposable projection.  
**Acceptance test:** Complete state can be reconstructed from the dedicated versioned ledger and referenced manifests without a database or any task-worktree branch.

### Q-002 — System name and repository placement

**Decision to make:** Retain the working name `Agentic Research System`, and decide whether the installed core remains under `.apm/` or moves to a neutral `.research-system/` root.  
**Default recommendation:** Use `.research-system/` for the provider-neutral core and provide an `.apm/` compatibility adapter during migration.
**W1 disposition:** P-002 as amended by P-020/P-021: tracked provider-neutral definitions remain under `.research-system/`; dynamic canonical state is bound to the dedicated control root; legacy compatibility paths are non-shared.

### Q-003 — First pilot task

**Decision to make:** Select the first new, bounded research task after the current phase boundary.  
**Default recommendation:** Pilot a task that has a mathematical design, a modest implementation, deterministic contracts, and an independent review path, but no multi-day computation or paper-critical deadline.

### Q-004 — Independent-review diversity

**Decision to make:** When a verifier must use a different model family, a fresh context from the same family, or both.  
**Disposition:** P-022/P-023. R3 requires cross-family and independently compiled context. R2 requires a distinct verifier context and the family-diversity policy declared by its assurance profile. Context provenance is checked; the exact subject artefact remains visible while implementer conclusions and hidden reasoning remain excluded.

### Q-005 — Runtime support boundary

**Decision to make:** Whether the first release officially supports only Claude and Codex or defines a generic adapter interface immediately.  
**Default recommendation:** Define the generic interface in the schema, but implement and evaluate only Claude and Codex adapters in the first release.

### Q-006 — Human approval points

**Decision to make:** Which state transitions require Stephen's explicit approval.  
**Default recommendation:** Require approval for pre-registration changes, R3 task dispatch, decision-lock reversal, claim promotion, and migration of imported evidence from provisional to authoritative.
**W1 disposition:** P-005 as amended by P-022: R0/R1 may use delegated Manager acceptance, R2 requires independent verification plus Manager acceptance, and R3/P-005 transitions require Stephen.

### Q-007 — Historical import depth

**Decision to make:** Import the complete APM history or only authoritative decisions, active dependencies, and selected failure fixtures.  
**Default recommendation:** Do not normalize the entire tracker. Import authoritative decisions and active dependencies; preserve the old files as immutable historical evidence.

## Decision protocol

Each future decision entry must record:

- identifier and date;
- status: proposed, accepted, superseded, or rejected;
- decision and rationale;
- evidence references;
- affected specifications;
- migration consequence;
- superseding decision, where applicable.
