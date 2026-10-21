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
**Evidence:** W0 fixtures F-001/F-002, evidence register §4.3, and the canonical Task Observer observation titled “Bus writes need explicit ownership, not only read-before-write” (2026-06-28; `C:\Users\steph\.claude\skill-observations\log.md`).<br>
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

### P-028 — W3 context-contract acceptance and retrieval-fixture reservation

**Date:** 2026-06-30<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-024; clarifies P-022 and P-025<br>
**Decision:** W3 v0.2 is accepted after adversarial review and approved reconciliation. Context uses immutable base packets plus append-only addenda; governing material cannot be compacted or memorized into replacement authority; distinct-verifier evidence is required only when the assurance grade requires it; and delta-review exposure is policy-bound and attributed (Manager for allowed R2 exposure, Stephen for R3).<br>
**Token rule:** Two independent gates apply before issuance: the versioned W3 reference-token count must satisfy the risk-profile ceiling, and the exact bound-provider count or a W7-evaluated conservative upper bound must satisfy 80% of provider usable input. Counts from different tokenizers are not treated as one unit. Missing provider accounting or either failed gate blocks issuance.<br>
**Fixture rule:** The dated W6 addendum reserves F-025–F-030 without rewriting the P-027 40-fixture catalogue. F-025–F-028 are P0 context-compiler gates; F-029–F-030 are P1 pre-pilot gates. W6 must empirically size mandatory closure for F-025/F-026/F-021/F-022 under both token gates before compiler/profile release.<br>
**Manifest rule:** One canonical out-of-band manifest schema remains binding across tiers. Empty or inapplicable groups are explicit; fields are not dropped merely to create an R0 variant. Any manifest content rendered to the model counts against both token gates.<br>
**Evidence:** `reviews/adversarial-W3-context-review-2026-06-30.md`, `reviews/adversarial-W3-review-reconciliation-2026-06-30.md`, and Stephen's 2026-06-30 approval to proceed.<br>
**Boundary:** This accepts a written specification and fixture reservation only. It creates no compiler, fixture, adapter, runtime, migration, pilot, active APM change, or research claim.<br>
**Remaining gates:** W4/W5 specifications, foundation-critical W6/W7/W8 interfaces and executable evidence, combined-interface review, and Stephen's approval of a separately reviewed implementation plan.<br>
**Affected specifications:** W3, W4, W5, W6, W7; package status and continuation protocol.

### P-029 — W4/W5 routing-assurance acceptance and fixture reservation

**Date:** 2026-06-30<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-022, P-024; finalizes Q-005<br>
**Decision:** W4 v0.2 and W5 v0.2 are accepted after joint adversarial review and reconciliation. For R2, the `AssuranceRequirement` epistemic floor, complete lane scope, and every `not_applicable` rationale must be set by an authority distinct from the prospective producer or independently confirmed at minimum I1; a pack may require I2. R3/P-005 requires I2 requirement-scope review plus Stephen's attributed acceptance. A materially different actual producer relationship stales that acceptance.<br>
**Routing rule:** Before R2/R3 producer dispatch, W4 must demonstrate at least one eligible verifier route at the required capability and independence grade relative to the prospective producer. The final grade is recomputed against the actual producing attempt. R3-required capability coverage below two eligible model families is surfaced as `r3_family_coverage_insufficient` and blocks dispatch.<br>
**Fixture rule:** Addendum `06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md` reserves F-031–F-038. F-031–F-036 are P0 implementation/release blockers for affected interfaces; F-037–F-038 are P1 blockers before the greenfield pilot accepts evidence or promotes claims. Executable materialization and calibration remain deferred.<br>
**Provider rule:** The adapter interface remains provider-generic, with first-release evaluation limited to Claude and Codex. Their two-family coverage is load-bearing for R3 only where both families pass the required capability/eval gates; provider identity never substitutes for eligibility.<br>
**Evidence:** `reviews/adversarial-W4-W5-review-2026-06-30.md`, `reviews/adversarial-W4-W5-review-reconciliation-2026-06-30.md`, and Stephen's 2026-06-30 approval.<br>
**Boundary:** This accepts written specifications and fixture reservations only. It creates no profile, route, adapter, fixture implementation, runtime, migration, pilot, active APM mutation, result reinterpretation, or research claim.<br>
**Remaining gates:** Frozen foundation-critical W6/W7/W8 interfaces and executable evidence, bounded combined-interface review, and Stephen's approval of a separately reviewed implementation plan.<br>
**Affected specifications:** W4, W5, W6, W7, W8, W10; package status and continuation protocol.
### P-030 — Gate 3 W6/W7/W8 interface acceptance

**Date:** 2026-07-01<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-025, P-026, P-028, P-029<br>
**Decision:** W6 v0.3, W7 v0.2, W8 v0.2, and 06c v0.2 are accepted after joint adversarial review and reconciliation. Gate 3 uses a dependency DAG: the W5 requirement, W3 compiled/reference-gated context, W7 provider/capability/tokenizer evidence, and W8 preliminary operational-risk floor/feasibility precede W4 candidate routing; the candidate-specific provider-capacity gate is evaluated during routing; W7 revalidates exact-or-accepted-upper-bound accounting before issue; W8 selected-route grant/lease follows routing.<br>
**Identity rule:** Shared consumers use the exact owner-defined identifiers. W4 already owns `routing_evidence_snapshot_id` / `res_`; W6 owns `trace_id` and `grader_result_id`. A naming mismatch is reconciled to the existing owner and cannot create a duplicate identity.<br>
**Stage rule:** W6 solely owns the closed `gate_stage` enumeration: `interface_review`, `p0_materialization`, `foundation_release`, and `pilot_promotion`. Fixture priority remains independent and non-compensable.<br>
**Proportionality rule:** W8 uses one schema with versioned `trivial`, `bounded`, and `long_running` operational profiles. A trivial profile retains typed request/grant/lease/terminal-receipt evidence while marking benchmark/checkpoint/periodic-heartbeat/recovery groups explicitly `not_applicable`; exceeding the envelope requires a new stronger request.<br>
**Token rule:** W3 owns the gate semantics. W7 owns provider count, usable-capacity, wrapper/system overhead, and reserve evidence. Fixed provider overhead reduces usable input; variable wrapper/system material consumes reserved capacity; missing or overlapping accounting blocks issue.<br>
**Evidence:** `reviews/adversarial-gate3-W6-W7-W8-review-2026-07-01.md`, `reviews/adversarial-gate3-W6-W7-W8-review-reconciliation-2026-07-01.md`, and Stephen's 2026-07-01 approval.<br>
**Boundary:** This accepts written interfaces only. It creates no runtime, fixture package, grader, adapter, process, checkpoint, migration, pilot, active APM change, result reinterpretation, or research claim.<br>
**Remaining gate:** A separately reviewed P0 materialization and narrow-foundation implementation plan, followed by Stephen's explicit approval before implementation.<br>
**Affected specifications:** W3, W4, W6, W7, W8, 06c; package status and implementation sequence.

## Post-Gate-5 owner directions recorded 2026-07-16–17

P-031–P-034 record directions Stephen stated in the 2026-07-16 planning session that
produced `implementation/06-wp6-gate6-readiness-and-integration-plan.md`, written
against the evidence survey in that session (Gate A blockers A1–A8 of the vault-side
TDA-scale programme v1.0.0 cross-checked against the accepted W1–W8 designs, the Gate
5 plan, and the implemented `research_system` foundation). Stephen confirmed their
exact wording on 2026-07-17 (D-G6-1), the same day the Gate 5 foundation was accepted
at merge `f49a27f`. P-035 records Stephen's direct 2026-07-17 approval of the two
owner choices required by the fresh WP6 remediation review. P-036 records Stephen's
exact-revision approval after the R5 review found no Critical, Major, or Minor findings.
The A1 blocker and the WP6 plan-suite review gate are cleared,
and the D-G5-1(a) M/H restriction and O15 deferral carry forward as recorded in the
acceptance decision. Acceptance of these directions authorizes no implementation; the
remaining work-package, future-evidence, migration, and preflight gates remain binding.

### P-031 — Gate 6 pilot definition amendment

**Date:** 2026-07-16<br>
**Status:** Accepted by Stephen (direction 2026-07-16; wording confirmed 2026-07-17)<br>
**Amends:** P-026; 04-plan §4 Gate 6 and §6 pilot operating model<br>
**Decision:** The greenfield pilot boundary becomes *the first ARS-native workflow admitted after Gate 5 acceptance*, rather than strictly the first post-APM paper. The proposed pilot workflow is SCALE-01 (full-path stage telemetry and Markov-fit hoisting), an engineering canary on closed read-only fixtures. The first ARS-initiated paper (the SPEC-01/SPEC-02 spectral-distance PH lane) remains the pilot's research continuation and inherits the original paper-pilot promotion criteria.<br>
**Rationale:** SCALE-01 satisfies Gate 6's own preflight predicates better than any paper: it is non-critical, its inputs and authority are content-addressed and read-only, a negative outcome is a valid terminal result, and rollback cannot touch accepted research evidence. Requiring the pilot to be a paper would force the riskier workload first.<br>
**Evidence:** Gate A blockers and the SCALE-01/SPEC lane definitions in the 2026-07-16 TDA-scale programme v1.0.0; the WP6 planning evidence survey; Stephen's direct direction on 2026-07-16 and exact-wording confirmation on 2026-07-17.<br>
**Boundary:** Pilot preflight criteria themselves are unchanged and SCALE-01 must pass them; this amends only what kind of workflow may occupy the pilot slot.<br>
**Migration consequence:** W9/WP6.4 substitute SCALE-01 only for the pilot occupant; every existing Gate 6 preflight predicate remains, and the first ARS paper retains the inherited research-promotion criteria rather than being treated as already piloted.<br>
**Affected specifications:** W9 (pilot mechanics), 04-plan, `00-master-transition-plan.md`, WP6 master, WP6.4.
**Supersession note (2026-08-22):** This is historical pilot-occupant
provenance. P-049's SCALE-01 eligibility-envelope closure application is
superseded by P-050 and 06q; SCALE-01 is not a current Gate 6 closure
prerequisite.

### P-032 — Full portfolio and Discovery integration (W11)

**Date:** 2026-07-16<br>
**Status:** Accepted by Stephen (direction 2026-07-16; wording confirmed 2026-07-17)<br>
**Decision:** ARS becomes the canonical end-to-end home for research-programme organisation: Candidate registration, Assay scoring, Spike verdicts, PROMOTE/PARK/KILL promotion decisions, pre-registration locks, dispatch, results, and claims as typed canonical records. A new specification `design/11-portfolio-and-discovery-lifecycle.md` (W11) is added to the planned set and passes its own adversarial review gate before implementation. The master plan §6.1 lifecycle (`Candidate → Assay → Spike → Pre-registration → Implementation → Independent verification → Decision lock → Claim promotion → Manuscript integration → Reproducibility release`) is the governing shape.<br>
**Rationale:** Stephen's stated objective is a single integrated system replacing the vault-harness + APM hodgepodge, whose small persistent coordination issues motivated the ARS in the first place. The 2026-07-16 TDA-scale package manifest — hand-computed content addressing standing in for a missing admission interface — is direct evidence of the gap.<br>
**Evidence:** `00-master-transition-plan.md` §6.1; the 2026-07-16 TDA-scale package manifest and Gate A survey; the living legacy Discovery backlog inspected during the planning/review cycle; Stephen's 2026-07-16 direction and 2026-07-17 wording confirmation.<br>
**Boundary:** The vault remains the human reading/annotation surface via generated projections; it ceases to be lifecycle authority for successor-owned Discovery objects. Already-active Discovery items (e.g. the registered sheaf-Laplacian dispatch, the MCbiF decision-pending battery) remain vault/APM-owned under P-004 until an explicit per-item ownership transition; no `dual_owned` state is created.<br>
**Migration consequence:** The living `_backlog.md` remains exclusively legacy-owned until an explicit whole-path cutover. Successor projections and human annotations use separate registered ARS namespaces; per-item transition events move authority one way, and no legacy-named path becomes generated until collision and cutover gates pass.<br>
**Affected specifications:** `00-master-transition-plan.md`; WP6 master/WP6.5/WP6.6/WP6.7; new W11; W1 portfolio catalogue; W2 (`obj` records, ScopeDefinition); W4 (Scout/Portfolio Steward role profiles); W5 (claim promotion); W9; W10.

### P-033 — Full live capability before research dispatch

**Date:** 2026-07-16<br>
**Status:** Accepted by Stephen (direction 2026-07-16; wording confirmed 2026-07-17)<br>
**Amends:** Resolves the D-G5-1(b) deferral into scoped post-Gate-5 work<br>
**Decision:** No interim operator-executed or degraded-mode research dispatch is defined. Live Claude and Codex transports, live semantic parity evidence, the separately accepted live-grader threshold/calibration policy, and instantiated evaluated model profiles (W4 §10) must all exist with direct current evidence before any R2 research task dispatches under ARS. The intent is to start doing real work and test the system in action, on its full capability path.<br>
**Rationale:** An interim human-executed mode would be an undeclared bypass of the routing, parity, and independence machinery — precisely the class of informal side-channel the ARS exists to remove.<br>
**Evidence:** Gate A A3/A6; the fake-only `live_enabled: false` adapter manifests and provider guard; the Gate 5 D-G5-1(a) release restriction; W4 §10 and W7/W8 command/receipt/grant contracts; Stephen's 2026-07-16 direction and 2026-07-17 wording confirmation.<br>
**Migration consequence (as amended by P-035):** The Gate 5 M/H restriction remains until the exact T1b evidence-bearing policy and direct live evidence are accepted; T1a protocol acceptance alone cannot unblock it. No R2 research dispatch, operator bypass, lower-grade fallback, or profile-by-name route is available during the cutover.<br>
**Affected specifications:** W4, W6 (§7.2 threshold clause), W7, W8; WP6 master and WP6.2.

### P-034 — End-to-end consolidation objective and legacy sunset sequencing

**Date:** 2026-07-16<br>
**Status:** Accepted by Stephen (direction 2026-07-16; wording confirmed 2026-07-17)<br>
**Decision:** The programme target is one bespoke, integrated system carrying the valuable lessons of the 2025–2026 tooling (pre-registration, contracts, provenance, fail-closed gates, Partial semantics, the Assay-before-Spike funnel) and retiring the accumulated surfaces — APM orchestration, the vault-side Discovery Harness as authority, and ad-hoc coordination files — once their W9 migration gates pass. Consolidation proceeds by explicit per-item ownership transitions, never by indefinite dual-running.<br>
**Evidence:** P-004/P-021/P-026 migration boundaries; `00-master-transition-plan.md` §6.1; the current T1.28/two-paper legacy boundary and active Discovery items; Stephen's 2026-07-16 direction and 2026-07-17 wording confirmation.<br>
**Boundary:** The P-026 legacy boundary is unchanged: T1.28 and the two current APM-managed papers remain `legacy_owned`; T1.28 terminal review still gates legacy deprecation claims.<br>
**Migration consequence:** Each active item remains on its current authority and physical writer path until its W9 gate and attributed transition event pass. Retirement happens only after the final path-level cutover; no dual writer, implicit import, or bulk status upgrade is permitted.<br>
**Affected specifications:** `00-master-transition-plan.md` §6.1; WP6 master/WP6.5/WP6.6/WP6.7; W9, W10, W11.

### P-035 — WP6.2 staged calibration and composite live evidence

**Date:** 2026-07-17<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-029, P-030, P-033; resolves the structural limb of D-G6-2 and the T7 composition limb of D-G6-3<br>
**Decision:** WP6.2 uses the exact non-circular lifecycle
`T1a → T2 → T3/T4 → T1b → T5 → T6 → T7 → T8`. T1a preregisters and receives
independent review/Stephen acceptance for the calibration protocol without claiming
observed calibration. T2 establishes the secret/cost boundary; T3 and T4 then produce
independent bounded Claude/Codex canary evidence. T1b uses those protected seams to
produce immutable calibration evidence and receives independent review/Stephen
acceptance for the exact evidence-bearing threshold-policy hash. T1a acceptance gates
T2–T4 only; T1b acceptance gates T5–T8 and every M/H eligibility transition.<br>
**Evidence-composition rule:** T7 uses exactly 251 immutable references to otherwise-
available Gate 5 `foundation_release` results plus 51 new `live_capability` results,
for an aggregate closure of 302. Each live result has a one-to-one predecessor mapping
from an unavailable M/H Gate 5 key and actual provider/model/adapter/command/receipt/
grant/lease identities and hashes. Frozen fake results retain their original lifecycle
and identities and are never relabelled as live.<br>
**R2 remediation constraints (accepted under P-036 for exact reviewed plan revision
`fe5f1d40bc8f05f061317c677b5891cea0711249`):** T1b is implemented as the
non-compensable union of separately complete `T1b-M` model evidence and `T1b-H` human
rubric/blinded-case/disagreement/adjudication evidence; only their composite accepted
hash clears T1b. The exact 51 predecessor/successor bindings come from the
content-addressed 06e annex, and the exact P1 11+43 obligations come from the
content-addressed 06f annex, never from observed manifests. W6 `gate_stage` remains the
valid value `pilot_promotion`; `live_capability` is a separate typed `evidence_stage`,
not a new W6 gate-stage alias. The proposed command identities, P1 grader identities,
successor construction, and stage split are authoritative requirements of the approved
plan revision; their future materialized manifests retain their separate exact-hash
review and owner-acceptance gates.<br>
**R3 remediation constraints (accepted under P-036 for exact reviewed plan revision
`fe5f1d40bc8f05f061317c677b5891cea0711249`):** WP6.1 contract materialization precedes
runtime implementation and independently freezes every row's command/event schema
identity, exact authority subject, the atomic Task-plus-Dispatch claim batch/write set,
and the closed correction selector. WP6.2 uses a dedicated strict P1 schema and an
independently produced, reviewed, accepted, content-addressed 54-row expected manifest
containing every literal descriptor hash before descriptor build or observation.
Runtime registries, descriptors, manifests, ledgers, and executions are observed-side
comparison inputs only. A self-consistent coordinated replacement of descriptor bytes
and the candidate expected manifest still rejects against the D-G6-3 accepted manifest
identity. F-037 and F-038 summaries bind exactly 12 and 10 execution hashes,
respectively, with disjoint union 22.<br>
**R4 remediation constraints (accepted under P-036 for exact reviewed plan revision
`fe5f1d40bc8f05f061317c677b5891cea0711249`):** RuleEvaluation has its own authority
subject, ID source, owner projection, and correction-selector target; neither a Decision
grant/projection nor coordinated expected/runtime corruption can substitute for it.
`ClaimDispatch` loads the accepted Dispatch and requires its stored Task ID/revision,
the payload Task ID/revision, and the active lease subject to agree before authority or
idempotency reuse. A valid but foreign current Task, stale Dispatch relation, or wrong
lease subject rejects atomically. The R3 provenance table distinguishes canonical
Git-blob UTF-8/LF bytes from a Windows CRLF checkout hash.<br>
**Rationale:** A single policy gate before T2 is empirically circular because protected
provider seams do not yet exist. A full 302-row live-rerun claim would contradict the
bounded 51-obligation tranche and waste accepted evidence. The staged gate preserves
preregistration and owner authority while allowing admissible calibration evidence;
the composite preserves immutable Gate 5 provenance while making the new live
capability evidence exact.<br>
**Evidence:** Repository-relative review
`docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-review-2026-07-17.md`,
containing commit `80cc5f2b1103357fcd61bb51a1ee10f8112f5ad5`, Git blob
`b962ed11813ff0a0164a0f8be3eef7e926757e5e`, reviewing exact commit
`45d29dd16cc5e654eb0be086d81eda9771711f11`, findings M-1 and M-6;
Stephen's direct approval of both recommended choices on 2026-07-17.<br>
**R2 remediation evidence:** Repository-relative review
`docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r2-review-2026-07-17.md`,
Git blob `b9b3963ccfc6ef9bceba9177497a1c83f69c3c18`, reviewing exact commit
`79f6b1bfb28a02d6a06d5a4a350bfa7262ec6461`. Its seven Major findings and one
Minor define the pending constraints above; the review does not itself accept them.<br>
**R3 remediation evidence:** Repository-relative review
`docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r3-review-2026-07-17.md`,
Git blob `69f140d95bbe33c39b3593833e9789ab409af9a9`, canonical UTF-8/LF SHA-256
`b1a89411496bda995bef9b11211ed1f6078b90babd3bb46f79755e48316e4810`, reviewing exact
commit `3cca017c936a1d2b6a6b2049bc866caf5cb79047`. Its six Major findings and one Minor
define the additional pending constraints above; the review does not itself accept
them.<br>
**R4 remediation evidence:** Repository-relative review
`docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r4-review-2026-07-17.md`,
Git blob `66e82fdc9a014324c9e433cab431386bc6f8471e`, canonical UTF-8/LF SHA-256
`87f226204475d51630ceeb71608d7a6d3fca135bdd68ef5a395c445df6d78a0a`, reviewing exact
commit `aa54fe140de8eff3dabe0472758c3514fa673b19`. Its two Major findings and one Minor
define the R4 constraints above; the review does not itself accept them.<br>
**R5 approval evidence:** Repository-relative review
`docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r5-review-2026-07-17.md`,
Git blob `b6f047db330617f25ffd8e0826da9769facab089`, canonical UTF-8/LF SHA-256
`15af91fa08f248f55765cbcdf9d0efce3153232c7818a66d385b80c4bdb0e065`, reviewing exact
commit `fe5f1d40bc8f05f061317c677b5891cea0711249`. It returned `approved` with zero
Critical, Major, or Minor findings and both required contract commands passing all 98
contracts. Stephen approved that exact revision on 2026-07-17 under P-036.<br>
**Boundary:** P-035 accepts sequencing and evidence composition; P-036 additionally
accepts the R2/R3/R4 constraints, proposed identity choices, and literal D-G6-3 plan
tables at the exact reviewed revision. Neither decision accepts a future T1a protocol
hash, T1b empirical policy hash, WP6.1 schema-identity manifest, WP6.2 descriptor-hash
manifest, live call/result, evaluated profile, M/H eligibility transition, WP6
implementation, migration, Gate 6 preflight, pilot evidence, or claim.<br>
**Migration consequence:** WP6.2 dispatch prompts and branches must reproduce the
staged graph exactly. The implementation must add a lifecycle-aware composite schema
with a valid W6 `gate_stage`, a separate typed `evidence_stage`, and stage-specific
loader/CLI while preserving the existing P0 fake-only loader and
all Gate 5 result identities byte-for-byte.<br>
**Affected specifications:** W4 §10; W6 threshold/calibration, coverage, and
F-037/F-038 contracts; W7 provider command/receipt evidence; W8 grant/lease evidence;
WP6 master; WP6.2 T1a–T8; D-G6-2/D-G6-3; Gate 6 pilot and M/H eligibility gates.

### P-036 — WP6 plan-suite exact-revision approval

**Date:** 2026-07-17<br>
**Status:** Accepted by Stephen<br>
**Closes:** The WP6 plan-suite independent-review and exact-revision owner-approval gate;
the plan-revision limb of D-G6-3<br>
**Decision:** Stephen approves exact reviewed commit
`fe5f1d40bc8f05f061317c677b5891cea0711249` as safe to use as the Gate 6 launch basis.
Its R2/R3/R4 remediation constraints, proposed plan identities, lifecycle composition,
and literal WP6.1/WP6.2 invariant tables are authoritative for dispatch planning.<br>
**Evidence:** The R5 review identified above independently reviewed that exact clean
commit, returned `approved` with zero findings at every severity, reproduced the
104/182, 13, 11+43, 51, and frozen Gate 5 invariants, and passed both contract checks
against 98 contracts. Stephen then gave explicit exact-revision approval.<br>
**Boundary:** This decision closes the plan-suite review gate and authorizes the exact
reviewed plan content as a launch and dispatch-planning basis. It does not itself
authorize runtime implementation, a live provider call, an eligibility transition,
migration, claim promotion, or Gate 6 pilot execution. Every future exact-hash evidence
acceptance and work-package/preflight gate remains mandatory.<br>
**Migration consequence:** WP6.1/WP6.2 task briefs must cite the approved commit and
must preserve its normative plan content. Any substantive plan change requires a new
exact-revision review and owner approval; bookkeeping-only approval provenance does not
alter the reviewed requirements.<br>
**Affected specifications:** WP6 master and WP6.1/WP6.2 child plans; P-035; D-G6-3;
Gate 6 launch and dispatch-planning controls.

### P-037 - WP6.2 T2 cost-grant authority and versioning

**Date:** 2026-07-22<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-035/P-036 by supplying the previously missing T2 canonical-transition
authority; does not alter the accepted WP6.1/T1a bytes or the WP6.2 dependency graph<br>
**Decision:** The existing project-wide `CommandService` remains the sole canonical
writer. A separately content-addressed WP6.2 T2 authority addendum must define exactly
these command families: `IssueCostGrant -> CostGrantIssued`;
`AuthorizeProviderIssue -> [CostGrantReserved, ProviderCommandIssued]` as one atomic
ordered batch; and `RecordProviderReceipt -> [ProviderReceiptRecorded,
CostGrantReconciled]` as one atomic ordered batch. Replay returns the original receipt
and emits no duplicate reservation, issue, provider invocation, receipt,
reconciliation, or refund. No direct or second cost writer is permitted.<br>
**Versioning rule:** New `SecretReference`, `CostGrant`, command, and event identities
begin at `1.0.0`. A required-field expansion of accepted `ProviderCommand` or
`ProviderReceipt` uses an explicit `2.0.0` successor; `1.1.0` is reserved for genuinely
optional backward-compatible additions. Historical schemas and records are never
rewritten.<br>
**Evidence:** The V2 exact-state handback and its assessment verified that P-020 and W2
already settle writer ownership and general versioning, while the accepted 06d
catalogue and current `CommandService` omit the exact T2 transition family. Stephen's
2026-07-22 reply `Approve both` accepted the dedicated ruling together with the
standalone-workflow advisory integration.<br>
**Boundary:** This decision authorizes contract/addendum authorship and fresh
independent review only. It authorizes no runtime implementation, T3/T4, live provider
call, T1b, eligibility transition, result, claim, or mutation of accepted WP6.1/T1a
artifacts.<br>
**Transport clarification (2026-07-23):** P-037's atomic ordered batches are atomic
only within `CommandService`; they do not make the external provider transport atomic
or eliminate its crash window. P-037 does not settle whether `ProviderCommandIssued`
records dispatch intent or a completed invocation, and it defines no accepted
outbox/idempotent-dispatch protocol. Runtime provider work remains blocked until a
separate accepted authority resolves that seam. The exact accepted P-037 proposal is
preserved unchanged.<br>
**Remaining gate:** Fresh independent review followed by Stephen's acceptance of the
exact addendum and identity-manifest repository paths, Git blobs, raw-byte SHA-256
identities, and reviewed commit before any T2 implementation brief may issue.<br>
**Affected specifications:** W2 command/event/versioning contract; W7 provider
command/receipt contract; W8 resource/cost boundary; WP6.2 T2; D-G6-3.

### P-038 - WP6.2 T2 R1 remediation authority

**Date:** 2026-07-22<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-037 only to close the exact R1 contract gaps; the three command families,
ordered event batches, sole-writer rule, and immutable accepted bytes remain unchanged<br>
**Decision:** Authorize one bounded remediation of the rejected T2 authority-addendum
candidate. The remediation introduces an explicit Receipt 2.0 proof surface; rebuildable
idempotency and payload hashes on all five T2 event envelopes; a typed and evidence-
producing eight-seam pre-issue secret boundary; semantic cross-field identity and
authority validation; integer token-ceiling and cost-reconciliation arithmetic; complete
W7 ProviderCommand/ProviderReceipt 2.0 crosswalks; exact lowercase UUIDv7 enforcement;
and an independent machine-readable completeness oracle. Accepted W7 `pcmd_` and
`prcp_` prefixes remain scoped exceptions, while new T2 first-class identities use the
three-letter prefixes fixed in the ruling.<br>
**Exact accepted proposal:**
`proposals/wp6-2-t2-r1-remediation-authority-ruling-2026-07-22.md` at manager commit
`02f7b0b951b2141fb08374bbfcb3bcc368938907`, Git blob
`64dc129bd8147728fe007d31db54b512d633eb1f`, raw-byte SHA-256
`e309b56b8d2142791171e6cfab5150f43cb2c4339d923204d64e36d12479fa52`.<br>
**Boundary:** Candidate `1144d6a6d0feb28473fb540d41ff03bff79eec24` remains immutable
rejected history. P-038 authorizes one contract/addendum remediation cycle and one fresh
independent R2 review only. It authorizes no runtime implementation, live provider call,
T3/T4, T1b, eligibility transition, result, claim, or accepted-artifact rewrite.<br>
**Remaining gate:** The author returns one new immutable candidate and exact-state
handback. A fresh independent reviewer receives no author or manager conversation
history. Stephen must accept the exact remediated paths, blobs, raw-byte hashes,
candidate commit, and approving verdict before any T2 implementation brief may issue.<br>
**Affected specifications:** P-037; W2 receipt/event/idempotency contracts; W7 provider
command/receipt contracts; W8 resource/cost boundary; WP6.2 T2; D-G6-3.

### P-039 - WP6.2 T2 research-first scope and final remediation

**Date:** 2026-07-22<br>
**Status:** Accepted by Stephen<br>
**Amends:** P-038's C3/M2 scope and evidence timing; preserves P-037's three command
families, ordered event batches, sole-writer rule, and immutable accepted bytes<br>
**Decision:** Apply a research-value gate before non-research assurance becomes blocking:
name the protected research asset, concrete failure path, insufficiency of existing
controls, cheapest adequate control, evidentiary lifecycle stage, and bounded effort.
Prioritize mathematical/statistical/result assurance, data/provenance/reproducibility,
then minimal operational enablement. General hardening is separately justified and
defaults to at most 10% of the dispatched workflow budget.<br>
**T2 scope correction:** Retain strict opaque `SecretReference` metadata and exact
authority binding, but remove `PreIssueEvidenceManifest` and eight-seam scanner/sentinel
evidence as T2 blocking artifacts; defer that runtime evidence to T3/T4 against actual
adapter surfaces. Validate only the P-037 authority/cost/provenance subset of
ProviderCommand/ProviderReceipt 2.0 at T2; defer complete W7 runtime qualification to
T3/T4.<br>
**Final-cycle authority:** Authorize one final contract-only remediation of corrected R2
findings C1, C2, C4, M1, M3, and I1, plus the explicit C3/M2 scope reduction, followed
by one fresh static R3. If R3 remains `rework_required`, stop; no third remediation cycle
is authorized.<br>
**Exact accepted proposal:**
`proposals/wp6-2-t2-research-first-scope-and-r3-remediation-ruling-2026-07-22.md` at
manager commit `1301d8a5f089d27270c36b216967000a35472efc`, Git blob
`1c6703b37579a0ffa35bfec0f9cccc7180a37f79`, raw-byte SHA-256
`959ebeafa67368ffc87592134fd9c0caf385b4b562278789273563844295492f`.<br>
**Execution closure:** P-040 and
`reviews/wp6-2-t2-r3-owner-acceptance-2026-07-22.md` supply the immutable R3
candidate commit/tree, changed-path set, artifact blob/raw-hash identities, exact
reviewer subject, review identity, and owner acceptance. This later external record
closes the binding omission without rewriting the accepted P-039 bytes.<br>
**Boundary:** No runtime code, credential resolution, provider call, T3/T4, T1b,
eligibility, result, claim, publication, accepted-artifact mutation, reviewer-authored
security probing, or third remediation cycle is authorized.<br>
**Affected specifications:** P-038; W2 receipt/event/idempotency; W7 T2 subset and later
runtime qualification; W8 cost boundary; WP6.2 T2; large-workflow assurance budgeting.

### P-040 - WP6.2 T2 exact-byte contract acceptance

**Date:** 2026-07-22<br>
**Status:** Accepted by Stephen<br>
**Closes:** P-037's exact addendum, identity-manifest, reviewed-commit, and owner-
acceptance gate<br>
**Decision:** Accept the WP6.2 T2 contract/addendum candidate commit
`391a92753d7f746fa91a6b5455c9ce0fd01baa52`, tree
`0254c5416925126412867d61b3045ee1563abd0c`, for its exact bytes only. The
candidate contains exactly 27 changed paths: 26 present blobs and the P-039-authorized
deletion of the T2 pre-issue evidence manifest. The external decision record, rather
than mutation of the accepted candidate, supplies the accepted lifecycle state.<br>
**Review evidence:** Final static R3 review commit
`655f4173db93447a068adc6e92621455c4abc85d`; report Git blob
`1ad44c1f79ea9738f8ff5e2369bab3a32b4f940d`; raw-byte SHA-256
`17906c4ae1916840dfe94aab3f5991d17e8037940802ec1338c49b53f9506fd8`;
verdict `accept` with 0 Critical, 0 Major, and 0 Minor findings, 135/135 focused
tests, 102/102 contracts, and independent reproduction of the 220-member protected
aggregate.<br>
**Exact acceptance record:**
`reviews/wp6-2-t2-r3-owner-acceptance-2026-07-22.md` records Stephen's direct
confirmation and the exact candidate, handback, authority-addendum, catalogue,
crosswalk, protected-membership, schema-identity, and R3-report identities.<br>
**Boundary:** This closes the contract-candidate review and owner-acceptance gate only.
It authorizes no runtime implementation, credential resolution, provider call, T3/T4,
T1b, eligibility transition, result, claim, publication, accepted-artifact mutation,
PR merge, or further Gate 6 transition. A later implementation brief or integration
action requires separate authority.<br>
**Affected specifications:** P-037; P-038; P-039; W2 receipt/event/idempotency; W7 T2
authority/cost subset; W8 resource/cost boundary; WP6.2 T2; D-G6-3.

### P-041 - WP6.2 T2 rate-mode boundary exact-byte acceptance

**Date:** 2026-07-23<br>
**Status:** Accepted by Stephen<br>
**Decision:** Accept exact commit
`2048f6470a9542db967186cc260d235c3373de2e`, tree
`1be775711befa047c7baa36fa485e5690b2277f1`, for its exact six-path bytes only.
The accepted rule keeps reservation cost as a non-negative integer, requires
`metered` reservations to be at least one, and requires
`zero_cost_authorized` reservations to equal zero at both the
`AuthorizeProviderIssue` command and mandatory `CostGrantReserved` event
boundaries.<br>
**Review evidence:**
`reviews/wp6-2-t2-rate-mode-boundary-review-2026-07-23.md`; fresh independent
verdict `accept` with 0 Critical, 0 Major, and 0 Minor findings. Six directly
relevant boundary cases passed; the review ran no package-wide or
framework-wide suite.<br>
**Exact acceptance record:**
`reviews/wp6-2-t2-rate-mode-boundary-owner-acceptance-2026-07-23.md` records
Stephen's direct confirmation and the complete candidate path/blob/raw-SHA-256
tuple.<br>
**Boundary:** This decision accepts contract/schema/test bytes only. It grants
no runtime T2 implementation, credential resolution, provider call, T3/T4,
T1b, eligibility transition, result, claim, publication, PR merge, or Gate 6
transition authority.<br>
**Affected specifications:** P-037; P-040; W2 receipt/event/idempotency; W7 T2
authority/cost subset; W8 resource/cost boundary; WP6.2 T2.

### P-042 - Owner-operated external model sessions

**Date:** 2026-07-26<br>
**Status:** Accepted by Stephen<br>
**Supersedes:** P-033 and the active first-release sequence in P-035; amends
the provider-runtime portions of P-029/P-030 and qualifies P-036 without
changing its accepted historical bytes<br>
**Decision:** Claude and Codex are user-operated subscription applications
authenticated through their own OAuth flows. ARS must not invoke either
provider, spawn its CLI, make a direct provider API call, select a provider on
the user's behalf, or read/store/resolve/pass OAuth credentials. The authorized
first-release workflow is operator-mediated: ARS prepares and records bounded
briefs, task/role and assurance requirements, exact Git subjects, artifacts,
reviews, decisions, and returned evidence; an authorized operator starts the
external model session and chooses the application/session.<br>
**Gate consequence:** Direct Claude/Codex transports, T3/T4 provider issue,
T1b live calibration, live semantic parity, evaluated provider profiles,
provider-native receipts, and per-call subscription cost accounting are removed
from the first-release Gate A/Gate 6 critical path. The 251+51 live composition
and 54-obligation P1 activation remain historical proposed evidence, not active
release criteria. The active dependency path is WP6.1 plus WP6.3 into WP6.4 and
then Gate 6; WP6.5 remains an independent specification lane.<br>
**Preservation:** P-033/P-035/P-036, the approved WP6/WP6.2 snapshots, accepted
T2 exact-byte artifacts, proposed T3/T4 contracts, replacement maps, and
deterministic fake-adapter tests remain immutable historical evidence. Existing
live-provider runtime behavior remains disabled. Reactivation requires a new
owner decision and independently reviewed plan.<br>
**Evidence:** `reviews/wp6-direct-provider-routing-blast-radius-2026-07-26.md`;
`implementation/06g-wp6-owner-operated-session-amendment.md`.<br>
**Post-merge acceptance:** Stephen merged the remediated PR #165 tree
`9f94eb81de182c564714af6cb7b15298ff13f919` and instructed closure of the
acceptance gate. The external record
`reviews/wp6-owner-operated-session-amendment-owner-acceptance-2026-07-26.md`
sets the effective amendment status to `accepted_for_governing_planning`
without rewriting the reviewed 06g candidate snapshot. This permits KAN-56
WP6.3 readiness assessment, not WP6.3 implementation.<br>
**Boundary:** This decision authorizes plan and dependency correction only. It
does not authorize provider invocation, credential access, runtime
implementation, Gate 6 acceptance, pilot initialization, eligibility
transition, result, or claim.<br>
**Affected specifications:** W4 provider routing, W7 provider adapters/parity,
W8 provider cost/resource boundaries, WP6 master, WP6.2, WP6.3, WP6.4,
D-G6-2, and D-G6-3.

### P-043 - WP6.1 event-schema currency: producer emits

**Date:** 2026-07-28<br>
**Status:** Accepted by Stephen<br>
**Context:** Handoff 26 (`handoffs/26-research-system-suite-red-briefing.md`)
established, reproduced on a detached worktree at `449b0d00`, that 86 generated
event schemas under `.research-system/schemas/core/events/` (88 files
repo-wide) require `command_schema_id`, `command_schema_version`, and
`command_schema_sha256`, while no production code emits them;
`CommandService.submit` → `ledger.append` → `SchemaRegistry.validate`
therefore fails on `main`. The contracts suite stayed green because it
validates the WP6.1 materialization, not the runtime append path.<br>
**Decision:** The runtime producer rises to meet the accepted schemas. The
command-submission path derives all three fields at submit time from the
registered command schema actually used to validate the submitted command.
`command_schema_sha256` is the SHA-256 digest of the exact schema bytes used
for that validation — never of a reserialized or reconstructed representation
— so an independent recomputation from the schema file must reproduce the
emitted value. The generated event schemas are not relaxed. Caller-supplied
values for these fields are never authoritative.<br>
**Rationale:** The fields exist to bind events to exact command-schema
identities — the WP6.1 binding intent. Relaxing an owner-reviewed generated
schema family to fit an incomplete producer would weaken an accepted
materialization to accommodate a defect.<br>
**Execution:** ~~RM-01 Task A
(`implementation/rm-01-unblock-and-suite-recovery-plan.md`, PR #177)~~ —
superseded 2026-07-29, see the amendment below; acceptance of the repair is
recorded against WP6.1 currency, not the RM lane.<br>
**Amendment (2026-07-29, execution pointer only — the decision is unchanged):**
the 2026-07-29 independent adversarial review
(`reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md` §C-1) found the
RM-01 repair unexecutable as planned: `SchemaRegistry` discards both the raw
schema bytes and their source path at construction, so the byte-exactness this
decision requires is unobtainable through the current interface, while RM-01
prohibited the registry change needed to expose it. Execution moves to
`implementation/06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md`,
a WP6.1 main-path plan, which additionally carries the historical-event policy
this entry did not dispose of. New owner gates G-RM-8 (historical events) and
G-RM-9 (registry interface) govern it. The direction — producer emits, schemas
not relaxed — is unaffected.<br>
**Boundary:** No schema edit under `schemas/core/events/`; no change to WP6.3
accepted bytes; no invariant drift in the P0 eval corpus.

### P-044 - Research Methods lane (RM)

**Date:** 2026-07-28<br>
**Status:** Accepted by Stephen<br>
**Relationship to P-042:** P-042's boundary clause authorizes plan and
dependency correction only; this entry supplies the new owner decision P-042
requires before implementation of operator-mediated tooling.<br>
**Decision:** Create an independent Research Methods (RM) lane — parallel to
the WP6.1+WP6.3 → WP6.4 → Gate 6 path and never on its critical path — that
implements, inside the P-042 owner-operated-session regime:

1. a provider-neutral Research Methods Pack (versioned W3 procedural-memory
   assets distilled from Woodruff et al., *Accelerating Scientific Research
   with Gemini*, cited as evidence lineage only);
2. `ars brief export` / `ars brief import` — fail-closed compilation and
   recording of bounded operator briefs, and typed append-only landing of
   operator-returned results strictly below result acceptance and claim
   promotion;
3. a bounded local verification-execution lane (`ars brief verify`) and a
   manuscript-review lane feeding, never performing, W5 review.

Naming is provider-neutral throughout (accepted D-3). The lane runs as
plan-per-package with independent adversarial review before each dispatch
(governing suite: `implementation/rm-00-research-methods-lane-master-plan.md`
and RM-01..RM-04, PR #177).<br>
**Amendment (2026-07-29, scope of item 3 — the lane decision is unchanged):**
the independent adversarial review
(`reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md` §C-4) found the
"bounded local verification-execution lane (`ars brief verify`)" in item 3
unsafe as specified: it executed model-proposed Python with the project
interpreter beside a gitignored `.env` and the vault, without OS-enforced
isolation, egress denial, W8 grant/lease/process records, or non-self-attested
approval, making credential and restricted-data leakage reachable by design.
**Execution is withdrawn from the lane** and deferred behind new owner gate
G-RM-11, which requires a threat model and a real isolation substrate before
any plan is written. The manuscript-review half of item 3 proceeds unchanged in
`implementation/rm-04-manuscript-review-and-verification-records-plan.md`,
which records operator-produced verification outcomes as explicitly
self-attested evidence rather than executing anything. Items 1 and 2 stand;
their execution plans are revision 2, and the whole suite awaits a fresh
G-RM-3 review.<br>
**Owner gates preserved:** the G-RM-1..G-RM-6 checklist in rm-00 §3, extended
2026-07-29 by G-RM-7..G-RM-11 (rm-00 §3); W5 §19.3
claim promotion remains exclusively Stephen's P-005 authority; pack-asset
acceptance is an explicit owner action (G-RM-4).<br>
**Boundary:** This decision authorizes the RM plan suite's review and, upon
per-plan review acceptance (G-RM-3), bounded implementation of RM-01..RM-04
only. It does not authorize provider invocation, credential access, any Gate
6 artifact, W11/WP6.5 interaction, migration, pilot-paper initialization,
eligibility transition, result acceptance, or claim. Reactivation of any
direct-provider transport still requires a separate future decision.<br>
**Evidence:** `proposals/research-methods-integration-plan-2026-07-28.md`;
`implementation/rm-00-research-methods-lane-master-plan.md` (obligation
register and forward-obligation scan);
`proposals/rm-decision-entry-drafts-2026-07-28.md` (drafts these entries were
entered from, on Stephen's instruction, 2026-07-28).

#### P-044 amendment — 06i/06j candidate stages and gate identities

**Date accepted:** 2026-07-30<br>
**Status:** **Accepted by Stephen** against exact PR #198 head
`fa7d8a6dec4f8d31b9a94747c33e137d4048c376`.<br>
**Decision:** Extend P-044 only enough to permit bounded, inert contract candidate
authoring in 06i Stage A and 06j Stage A after accepted 06h, an admissible
independent exact-subject suite review, and Stephen's separate explicit G-RM-3
acceptance of those exact suite bytes. Stage A remains confined to each plan's
candidate directory and contract-shape tests; it may not modify canonical
schemas/policies, `research_system/**`, replay, CLI, registration or runtime
surfaces.<br>
**Gate identities:**

- preserve G-RM-10 unchanged as confirmation that RM uses the already accepted
  `RegisterArtefact` / `SetArtefactUseAuthority` family rather than a new event
  family;
- define G-RM-12 as Stephen's acceptance of the independently reviewed exact 06j
  Stage A candidate bytes before 06j Stage B or RM-03 packet use;
- define G-RM-13 as Stephen's exact-scope use-authority decision for an
  independently reviewed `OperatorVerificationRun`, with result/claim use still
  prohibited; and
- define G-RM-14 as Stephen's acceptance of the independently reviewed exact 06i
  Stage A candidate bytes before 06i Stage B or canonical RM consumption.

**Limits:** This amendment grants no Stage B implementation, provider,
credential, execution, result, claim, migration, pilot, merge or automatic gate
authority. G-RM-3, G-RM-12, G-RM-13 and G-RM-14 remain separately open; each
requires its own prerequisites and explicit Stephen decision. Acceptance of this
amendment activates the gate definitions and bounded Stage A authority only—it
does not satisfy any of those gates.
### P-045 - Generic event envelope clean-start activation

**Date:** 2026-07-30<br>
**Status:** Accepted by Stephen<br>
**Decision:** Approve a clean-start provenance disposition for
`.research-system/schemas/core/event.schema.json`, schema ID
`ars://core/event`, version `1.0.0`. The effective envelope bytes are Git blob
`bc3efc0fd41e3d9f24c383f2d0d196e26ba0d1e5`, raw-byte SHA-256
`3aaaa6d609dce1271db3e22d8620935929fc272add1fe5c06badb77050f6d021`.
The prior catalogue blob
`188deb32ce833cec9a59ab74026762eb93f5a607` was never activated as a runtime
history contract and is preserved as an unactivated predecessor, not
reinterpreted history.<br>
**Cutover evidence:** The configured external control-store inventory admitted
no existing event history. The default command-provenance cutover is therefore
global position `0`: every replayed event at position 1 or later must carry the
complete command-schema identity unless a later explicit migration decision
establishes a different versioned boundary. No configured external history was
admitted by this decision.<br>
**Late-history ruling:** If an undisclosed external store or other pre-cutover
event history later surfaces, stop replay and migration before modifying that
store. Pin and inventory its exact event bytes, schema identities, positions,
and provenance coverage; then obtain a new owner decision selecting explicit
versioned readers or a separately reviewed migration. Never silently widen the
cutover, reinterpret old bytes under this envelope, or rewrite the surfaced
history.<br>
**Binding:** `tests/research_system/unit/test_p045_envelope_decision.py`
recomputes the envelope Git blob and raw SHA-256 from committed or explicitly
selected revision bytes and rejects decision drift. Working-tree runs are
pre-commit checks only and are non-certifying.<br>
**Boundary:** This decision activates no additional WP6.1 schema, changes no
generic-envelope bytes, writes or migrates no external control store, and
grants no authority capability.<br>
**Affected specifications:** W2 schema versioning and replay; P-043; Handoff 32
§5A0; A0 runtime schema binding.

### P-046 - Owner-bound scoped-authority admission

**Date:** 2026-07-31<br>
**Status:** Accepted by Stephen as a design direction under the current owner
instruction; implementation acceptance, independent re-review, and every live
grant or decision remain outstanding.<br>
**Owner provenance:** Stephen's 2026-07-31 instruction authorises Handoff 32's
recommended least-privilege post-genesis issuer and scope direction and permits
the bounded technical choice recorded here. The runtime owner is not a caller
claim: it is the actor in the exact bootstrap root grant, cross-bound to the
current project, store identity, bootstrap-manifest hash, root-grant identity,
and root-grant hash.<br>
**Decision:** Post-genesis `ActivateAuthorityGrant` and
`RevokeIssuedAuthorityGrant` are owner-reserved operations. Each operation
requires one immutable, typed, one-time
`OwnerAuthorityAdministrationDecision` for one exact v2 grant target, schema
hash, subject scope, and finite `[effective_at, expires_at)` interval. After the
command service verifies that decision against the bound bootstrap owner and
store, publication uses a one-shot continuation bound to that exact ledger
instance. A raw event append carrying the expected producer, owner, decision
ID, or hash strings is not authority and must fail before publication. Replay
requires the exact `owner-bound-v1` admission marker on both scoped
administration event families, so any earlier record without the cutover marker
remains permanently inadmissible rather than becoming authoritative after a
later registry change. Replay and resolution re-load the immutable decision and
re-check its canonical hash, project/store/bootstrap/root/owner/action/target/
schema/scope/time cross-bindings. Missing, foreign, tampered, reused, or
mismatched decision evidence makes history invalid; copied event fields cannot
repair it.<br>
**Exact scope:** Activation resolves authority identities immediately against
the active exact-version/raw-hash registry. The closed command mapping is
`CreateScopeDefinition`, `AmendScopeDefinition`, and
`SupersedeScopeDefinition` to `scope_definition`, and `CreateTask`,
`AmendTask`, and `SupersedeTask` to `task`. The only admitted policy action is
`accept_r3_assurance_requirement` to one exact `assurance_requirement`. Every
unresolved, inactive, wrong-hash, wrong-version, or wrong-subject identity is
rejected at activation; no other materialised schema is activated, and a later
binding cannot wake a rejected proposal. Grants remain finite,
non-delegable, non-wildcard, and one-subject only.<br>
**Human-owner rule:** `accept_r3_assurance_requirement` is available only to
the exact bootstrap owner acting as `human`. Actor class is derived by this
bound policy rather than accepted from a caller mapping. An `agent`, a
`service`, or any actor other than the bound owner cannot satisfy the R3/P-005
acceptance check.<br>
**Rejected alternatives:** The decision rejects wildcard identities or
subjects; direct event self-attestation by producer/owner/decision strings; a
general legacy-root grant expansion; delegated administration; latent active
grants that wake after registry changes; and caller-supplied actor-class maps
for R3 acceptance.<br>
**Boundary:** This decision does not create or accept a live grant or owner
decision, activate the remaining WP6.1 catalogue, or change valid legacy
genesis history. Preserving legacy `RevokeAuthorityGrant` means preserving
valid legacy history and CommandService-issued legacy revocation; it grants no
direct append authority and cannot target typed v2 grants. This decision does
not accept the remediation implementation or its tests, complete the
control-store writer/acceptance runner, or imply merge, Gate 6, or owner
acceptance after review.<br>
**Evidence:** Current owner instruction dated 2026-07-31;
`handoffs/32-wp6-3-management-handoff-authority-model-and-acceptance-tooling.md`;
`reviews/wp6-3-control-store-acceptance-mechanics-2026-07-30.md`;
`reviews/adversarial-wp6-3-scoped-authority-255f607-exact-subject-review-2026-07-31.md`.<br>
**Affected specifications:** P-005; W2 authority event admission and replay;
W5 R3 assurance acceptance; Handoff 32 scoped-grant and control-store
sequencing.

### P-047 - Integrate Research Methods obligations into WP6 and later gates

**Date:** 2026-08-05<br>
**Status:** Accepted by Stephen as programme-organisation direction.<br>
**Supersedes:** P-044 only where it makes RM a separately tracked lane whose
completion is disconnected from WP6/Gate completion. It does not alter P-042,
G-RM-4 through G-RM-14, accepted exact-byte identities, or the no-provider,
no-execution, no-result, no-claim boundaries.<br>
**Decision:** There is no separately completed Research Methods lane. Its
required capabilities are owned where they are consumed:

1. WP6.1 owns 06h schema currency/closure, 06i artefact authority and consumer
   firewall, 06j W3 context-packet lifecycle/resolution, and RM-01's current
   append-path family completeness and quality gate.
2. WP6.4 owns RM-02 provider-neutral methods assets, RM-03 real brief
   export/import, and RM-04's non-executing verification-request and
   operator-return record path. These form part of the owner-operated external
   session capability and Gate 6 closure evidence.
3. Gate 9 owns only RM-04's manuscript-review pilot and manuscript-specific
   G-RM-5/G-RM-13 use decision after the Gate 6 return path exists.
4. RM-05 remains deferred behind G-RM-11. It is not silently implied by any
   WP6 or Gate completion claim.

**Current evidence correction:** G-RM-3 is closed for exact accepted commit
`0137d2caadd8b80d7c133bf63fe5f6bea065cf2d` and tree
`ee7d5109719565d1911da7f9000798973859aedf`, as recorded in
`reviews/rm-lane-pr198-g-rm-3-owner-acceptance-2026-07-31.md`. No repeat suite
review or owner acceptance is required for those bytes. This historical
statement is superseded for 06i and 06j by their later accepted and integrated
exact subjects; G-RM-13 remains separate for its later manuscript-specific
run.<br>
**Integration consequence:** RM-00 remains the obligation and gate crosswalk,
not a live parallel campaign. Executable work was tracked beneath KAN-65,
KAN-57 and KAN-22. WP6.1, WP6.3, and WP6.4 are integrated. WP6.1 closed with
KAN-65, KAN-71 through KAN-75, KAN-95 through KAN-97, and KAN-102 `Done`, the
accepted production subject `b0058f396f538a63f94ce68d8f6a49b25f4c4c8f`, independent-review
record commit `0fd4674ee4fc43515c12d498b7f786555f09bba3`, and merge
`26df87157013fa078849acb14921bbcfcdfe53f1` on current `main`. WP6.1 is
completed prerequisite evidence, not an open Gate 6 lane. Gate 6 still requires
the recovery implementation and assembled closure evidence in 06q; the Gate 9
manuscript pilot does not block Gate 6.<br>
**Boundary:** This decision reorganises and makes already-required work
visible. It does not accept an unbuilt runtime, satisfy a future exact-subject
owner gate, authorize an external session, execute returned content, promote a
result or claim, or authorize migration.<br>
**Affected specifications:** RM-00 through RM-04; 06h, 06i, 06j; WP6.1; 06g
WP6.4 owner-operated session amendment; Gate 6 control; Gate 9 successor plan.

### P-048 - C-1 ARS artefact-currency gate recovery

**Date:** 2026-08-13<br>
**Status:** Accepted by Stephen as bounded corrective-maintenance direction.<br>
**Supersedes:** The claim in `.github/workflows/ci.yml` that its disabled
repository-wide suite is the live post-merge ARS currency signal.<br>
**Decision:** The active C-1 signal is `ARS Artefact Currency` at
`.github/workflows/ars-artefact-currency.yml`. It runs the direct 06i
artefact-authority contract, canonical loader, WP6.4 session-exchange, and
watchdog negative-control tests on pull requests and `main`. The independent
`ARS Artefact Currency Watchdog` queries GitHub's workflow API on every `main`
push and daily; it fails closed unless that exact workflow is `active`.

The legacy repository-wide `CI` workflow remains disabled because its full-tree
lint baseline is red. It is not re-enabled or represented as a green gate by
this decision. The stale 06i direct-storage inventory is corrected to name the
single live artefact writer, `record_session_evidence`, and its duplicate
candidate/canonical materialization identities are renewed together.<br>
**Boundary:** This is a narrow C-1 control recovery. It does not reinstate
repository-wide CI, impose branch protection, accept or close G-RM-14, change
provider/execution authority, or close WP6/Gate 6. Any later full-suite or
branch-protection policy requires its own owner decision.<br>
**Affected specifications:** 06i artefact-authority interface; WP6.4 session
exchange; ARS post-merge currency control.

### P-049 — Keep merge admission, capability integration, and Gate 6 closure distinct

**Date:** 2026-08-16<br>
**Status:** Accepted distinction; the SCALE-01 closure application in the
historical 06p text is superseded.<br>
**Decision:** A reviewed change entering `main` is **merge admission** only; a
real public/production path proven on integrated `main` is **capability
integration**; and Gate 6 closes only after its own assembled evidence,
independent review, and Stephen's owner decision. A plan, schema, test suite,
PR, review, Jira state, or historical run is evidence for one of those
decisions, never the decision itself. The active Gate 6 recovery/closure route
is [06q](implementation/06q-gate6-spec-real-run-integration-and-follow-up.md).
SCALE-01 remains historical evidence and is not a Gate 6 closure prerequisite.
<br>**Amendment/current application (2026-08-22):** 06q applies this distinction
to the reset. Step 0 permits the named clean branch/commit/push/PR and
KAN-12/KAN-103 operations, including six bounded Jira child jobs and readbacks,
and permits closing PR257 unmerged only after the replacement decision is
durable. It still permits no merge, CodeRabbit trigger or polling, provider or
paid run, live-store write during construction, or final Gate 6 decision.<br>
**Affected specifications:** 06p, 06q, 06r, WP6/Gate 6, and the Gate-7
sequencing boundary.

### P-050 — SPEC real-run outcome and research-use disposition

**Date:** 2026-08-16<br>
**Status:** Accepted record of the historical real run; implementation remains
unintegrated.<br>
**Decision:** The real SPEC run is the Gate 6 proof target. It assessed 126
configurations with 42 deterministic reruns, reached terminal
`PROVEN/spec_02_owner_decided`, and reached its historical run-closure anchor at
position `444 ResourcesReleased`. Later events exist in the same store, so 444
is not described as the current store tail. Its research-use decision is
**PARK**: retain the method as
an experimental or benchmark candidate, not as the default empirical method or
the basis of a scientific claim. The `neurips2024` locator is a lightweight Git
tag at commit `145efcde673f1a1897eff250b77221d26c34c479`; the source error was
corrected append-only.<br>**Boundary:** PARK does not promote the method,
resolve upstream `vis_utils` equivalence, freeze the project's estimand or
representation, or open Gate 7. Those are separate empirical-adoption or
later-gate decisions. Same-disk verified backup proves logical recovery only;
an off-disk copy is separate. This decision authorizes no provider call, paid
run, live-store mutation, merge, review trigger, or owner closure.<br>**Affected
specifications:** 06q, the Gate 6 result handoff, and the empirical-adoption
materials.
<br>**Amendment/current application (2026-08-22):** The historical result and
PARK disposition remain the proof target and research-use boundary in 06q; the
amendment does not recast them as integrated capability or scientific
promotion. Step 0's named branch/PR and Jira work is administrative control
reset only; the later fresh proof still needs explicit paid-run approval and
Stephen's closure decision.

The immutable evidence for the 126/42 counts, terminal decision, source
correction, position-444 run closure, seven registered artefacts, and their
verified content hashes is recorded in the result handoff's
[durable evidence anchors](handoffs/01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md#durable-evidence-anchors).
That evidence is the operational source for this decision; this register and
06q are its governance and execution pointers, not circular proof.

## WP6.4 mechanics integration status (non-decision)

PR #208 was merged at
`be0a6cb57d7ec2839f3b4549a5d68e1b8a64c348` with final PR head
`a958452d608ec49bbc94f3a943b49f55578cbc3b`, and Stephen explicitly approved
the merged PR on 2026-08-03. The merge integrates the independently accepted
external origin-witness, restore-recovery, approved temporary-path,
restore-admission, and deterministic registry-closure mechanics together with
their exact-subject review records. The merge tree is byte-identical to the
final PR-head tree. The exact integration record is
`reviews/wp6-4-pr208-integration-record-2026-08-03.md`.

That was superseded operationally by the real KAN-78 Source-to-Control run.
The canonical Control store now has the owner-approved bootstrap identity,
write-once external origin witness, governed backup/restore evidence and real
A8 candidate `a8c_2034a902cc3e597d7094e4efb1cebe975690afe97f615bb54ea5bde0355b6e7b`
with raw SHA-256
`64f9ab15db7d07d12f0d9dd32866a955bcf00cabee94d03292024ca0440bd68d6`.
Fresh-process load and replay succeed after the original Source is unavailable.

WP6.3 and WP6.4 are now integrated on `main`. PR #239 merged the final WP6.4
artifact subject `056cd683be21b7046c3943208e3ba8e9898051dc` as
`b61dddec8f2ba0a7e456b1e3a57d265db1f60caf`; its candidate and merge tree are
`2c29ba05e10c93f20e9d0a28fe7f548b960c3255`. The capability runs the
owner-operated public brief-out/evidence-back path through real 06j context
authority, RM-02 assets, 06i artefact-use resolution and RM-04 candidate
registration, with restart and replay equality, governed backup creation, and
restore verification before writer-lease authorization.

D-G6-5 is accepted. The protected SCALE-01 v1.0.3 package and preflight remain
`pending_wp6_6`, `dispatchable: false` and `execution_authorized: false`; their
accepted bytes are unchanged. WP6.1 C1–C3 plus 06h, 06i and 06j are integrated.
WP6.1 R1 and the final WP6.1 proof remain, followed by final assembled Gate 6
acceptance. WP6.5 is independent under P-042/06g, while WP6.6 dossier admission
and WP6.7 legacy consolidation retain their separate gates. No provider
invocation, credentials, returned-content execution, result promotion, claim
promotion, research execution or pilot dispatch is authorized by this status
record.

**Gate 6 reset note (2026-08-22):** The preceding WP6.4 mechanics paragraph is
historical status evidence. The historical real SPEC run is PROVEN, but no Gate
6 implementation is integrated on `main`. Use [06q](implementation/06q-gate6-spec-real-run-integration-and-follow-up.md)
as the sole active recovery and closure plan; SCALE-01 is not a Gate 6 closure
prerequisite and Gate 7 remains blocked on integrated Gate 6 plus final closure
evidence.

## W11 specification status (non-decision)

The WP6.5 specification-only draft exists at
`design/11-portfolio-and-discovery-lifecycle.md` with status `review_pending`.
Independent review of exact revision `70074d42eade8460808e4d1d29348b7806eff2d0`
returned `rework_required` (2 Critical, 6 Major, 2 Minor). R2 review of exact revision
`d24df9d26f0d906d177eafa1eaeabb65a5515004` also returned `rework_required`
(0 Critical, 5 Major). R3 review of exact revision
`3e068c1ee5100e5a6e0bc57d0d047d993b406b2b` returned `rework_required`
(0 Critical, 6 Major). On 2026-07-18 Stephen approved the two bounded remediation
policies: pre-runtime catalogue authority may be an external exact Git/blob acceptance
envelope imported later through verified one-time genesis, and legacy annotation
cutover may bind an accepted inbox epoch that is atomically fenced while post-fence
annotations route to a successor epoch. Those approvals do not accept W11 itself.
R4 review of exact revision `4b941326e290582db7be07113d5d7bb78d8b97a3`
returned `rework_required` (0 Critical, 1 Major, 1 Minor): recorded negative or
unverifiable Discovery review verdicts could still clear the outcome gate, and three
verdict rows omitted the Review projection. Revision 0.5 records author reconciliation
of every R1/R2/R3/R4 finding and the complete
entry/invariant/test/decision/assurance/cross-spec matrices; it defines an acyclic hash
DAG and bootstrap, reconciles 81 owner rows with W4/projections/test identities, adds
separate cancellation review and overlay cleanup, and closes the annotation cutover
race with the accepted epoch/fence protocol. It also separates W2 verdict recording
from W11 gate satisfaction through a closed six-subject verdict/effect and review-
supersession policy. The dated addendum remains in the tracked
root evidence register. A fresh independent R5 review of the new exact commit is
mandatory and author reconciliation is not acceptance. This status entry does not
amend P-032/P-034, accept W11, authorize implementation or WP6.6/WP6.7, create any
schema/projection, ingest/admit any item, transition ownership, cut over a path, or
perform any result/eligibility/claim action. D-G6-4 remains open for (1) Stephen's
exact-revision acceptance after the fresh review and reconciliation and (2) a
separately content-addressed first ownership-transition batch using the accepted W11
relation.

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
**Disposition:** P-029. The adapter interface is provider-generic, with first-release evaluation limited to Claude and Codex. Two-family eligibility is load-bearing for an R3 capability only when both families pass its required capability/eval gates; insufficient coverage blocks dispatch.

### Q-006 — Human approval points

**Decision to make:** Which state transitions require Stephen's explicit approval.  
**Default recommendation:** Require approval for pre-registration changes, R3 task dispatch, decision-lock reversal, claim promotion, and migration of imported evidence from provisional to authoritative.
**W1 disposition:** P-005 as amended by P-022: R0/R1 may use delegated Manager acceptance, R2 requires independent verification plus Manager acceptance, and R3/P-005 transitions require Stephen.

### Q-007 — Historical import depth

**Decision to make:** Import the complete APM history or only authoritative decisions, active dependencies, and selected failure fixtures.  
**Default recommendation:** Do not normalize the entire tracker. Import authoritative decisions and active dependencies; preserve the old files as immutable historical evidence.

## 06s delivery revisions — accepted 2026-09-05

The following [DECISION] entries record Stephen's instruction after the plan review:
"Update the plan with these revisions and begine phase 0 when ready."
The accepted revisions and their operational application are in
[06s](implementation/06s-gate6-delivery-replan-and-gate7-integration.md), §§3–5.
They supersede conflicting 06q execution instructions and its active-plan pointers
in P-049/P-050, while preserving those decisions' historical evidence and the
distinction between merge admission, capability integration and owner closure.
Authorization is Phase 0 only; later dispatches and owner-only actions remain gated.

### P-051 — [DECISION] 06s D1: finite action table and early public integration

**Date/status:** 2026-09-05; accepted by Stephen.<br>
**Decision:** Preserve the finite SPEC action composition, implement its entries
incrementally on one public status/advance/result path, and derive completion from
all correctly bound effects for the same subject. Individual commands retain
their actor and transaction boundaries. No blob-hash registry, document parser,
composite seal or additional persisted workflow state.<br>
**Rationale/evidence:** The review identified deferred CLI assembly and multi-actor
actions hidden by a single-role table; 06q §4 Step 5 and W11 supply the underlying
composition and command semantics. 06s Phases 1–4 define progressive public exits.<br>
**Affected specifications:** 06q Step 5, 06s D1 and construction sequence.<br>
**Migration consequence:** No historical event or schema rewrite. A second material
review round requires diagnosis and an owner continuation decision, not automatic
retirement. Preserve valid implementation.<br>
**Supersedes:** 06q registry ceremony and automatic retirement; no successor decision.

### P-052 — [DECISION] 06s D2: reuse inherited authority checks

**Date/status:** 2026-09-05; accepted by Stephen.<br>
**Decision:** Omit additional SPEC session/grant machinery; preserve existing
CommandService/DiscoveryRuntime authority checks, including expiry and exact-subject
independence. SpecOperatorConfig@1.0.0 stays authority-neutral and unchanged.
Permitted actions derive from existing authority records, not a new declared role.<br>
**Rationale/evidence:** research_system/config.py supplies actor/session/grant IDs
and rejects additional fields; discovery/runtime.py resolves lifecycle grants.
The smaller route must use those interfaces rather than assume absent role/owner
fields or introduce an authority bypass.<br>
**Affected specifications:** 06q AUTHORITY, 06s D2 and Phase 2.<br>
**Migration consequence:** None; existing grants and historical validation remain.
No session containment or authority migration is commissioned.<br>
**Supersedes:** Additional SPEC authority machinery in 06q and v2 D2's proposal to
drop inherited expiry semantics; no successor decision.

### P-053 — [DECISION] 06s D3: explicit record validation without global policy change

**Date/status:** 2026-09-05; accepted by Stephen.<br>
**Decision:** Preserve existing validators and historical versions. New operative
records declare required/optional fields and reject unrecognized fields. Version
only required record changes; no global ignore-with-warning path.<br>
**Rationale/evidence:** The approved review distinguishes ordinary validation from
unnecessary schema machinery; strict current config validation remains inherited.<br>
**Affected specifications:** 06s D3 and new SOURCE/MODEL documents.<br>
**Migration consequence:** Historical bytes remain readable unchanged.<br>
**Supersedes:** v2 D3's unknown-field warning proposal; no successor decision.

### P-054 — [DECISION] 06s D4: version the causal-prefix source correction

**Date/status:** 2026-09-05; accepted by Stephen.<br>
**Decision:** Keep spec_01_source_correction@1.0.0 readable for historical replay.
Register the new causal-prefix form as 2.0.0; never replace historical bytes.<br>
**Rationale/evidence:** P-050 and its evidence handoff preserve the historical
append-only correction; 06s Phase 1 requires a correctly bound fresh correction.<br>
**Affected specifications:** 06q SOURCE and 06s D4/Phase 1.<br>
**Migration consequence:** Append-only new version only; no rewrite.<br>
**Supersedes:** Any fresh-path instruction using the historical version for the
new form; no successor decision.

### P-055 — [DECISION] 06s D5: inherited STORE and bounded verification

**Date/status:** 2026-09-05; accepted by Stephen.<br>
**Decision:** Select current merged main, account for relevant production deltas,
run the named Phase 0 packet and a genuine scratch CLI publication/readback/retry.
Historical test counts are provenance, not acceptance totals. Protect STORE from
speculative work. A demonstrated required-path defect needs a reproducer and the
smallest proposed repair, with an explicit scoped exception before implementation.<br>
**Rationale/evidence:** PR #268 is integrated; current baseline
ced524b7b59d019ad35bb44a5580400e757787b8 includes PR #270 production remediation.
The review found fake-service CLI routing and direct service tests insufficient
alone to prove the assembled positive CLI path.<br>
**Affected specifications:** 06q STORE, 06s D5 and Phase 0.<br>
**Migration consequence:** No production change is authorized in Phase 0. On
2026-09-08 Stephen authorized the demonstrated test-helper repair in
`tests/research_system/integration/test_current_binding.py`: numeric ledger
batch ordering and two deterministic opposite-month regression controls. This
is a narrow verification-instrument exception, not an expansion of inherited
STORE scope. Scope/review checkpoints preserve the candidate rather than force
a restart.<br>
**Supersedes:** Old-baseline/docs-only-delta stop and fixed historical test totals;
no successor decision.

### P-056 — [DECISION] 06s D6: bounded operational closure permits legitimate PARK

**Date/status:** 2026-09-05; accepted by Stephen.<br>
**Decision:** A fresh owner-approved subset of the historical 126/42 design proves
the operational route. A legitimate terminal PARK/no_spike may satisfy that proof
when Task acceptance, independently accepted result, replay and governed restore
all succeed. Scratch verification covers allowed/blocked SPEC-02 branches; the
historical full real SPEC-02 run remains historical evidence. Fresh live SPEC-02
is optional, only with valid promotion and separate owner approval.<br>
**Rationale/evidence:** A bounded Assay may legitimately remain PARK. W11's
revisit predicate and later PROMOTE cannot be manufactured to complete the gate.
The review explicitly proposed this alternative and Stephen approved the revisions.<br>
**Affected specifications:** 06q §6's mandatory fresh live SPEC-02 requirement,
P-049/P-050's current execution application, and 06s §§3–5.<br>
**Migration consequence:** Preserve historical science and source evidence. The
fresh ProjectUseDecision states the subset and limitations; no replication or
scientific-promotion claim. Paid-run subset/cost, live writes, merges and final
closure still require separate owner approval. Final closure includes replay after
the final documentation merge and verified Jira reconciliation. Gate 7 cannot add
requirements back to Gate 6.<br>
**Supersedes:** Mandatory fresh full 126/42 computation and mandatory fresh live
SPEC-02 for Gate 6 closure; no successor decision.

### P-057 — [DECISION] 06s C2: the historical SPEC run stays historical; Gate 6 closes on the fresh route

**Date/status:** 2026-09-14; accepted by Stephen.<br>
**Decision:** Historical run 01M0454KCTYV0E8PB016CP3F6J remains historical evidence
under P-050: its PARK disposition, the tracked hash-verified evidence manifest and
anchors 432/433/444. Gate 6 no longer requires closing historical Task
tsk_60c5549e-d11f-7d17-8145-d80e144aa537, registering a historical
ProjectUseDecision, or replaying the historical control-store ledger under
integrated code. Gate 6 closes on the fresh owner-approved bounded run (D6), whose
Task, ProjectUseDecision, replay and governed restore all use the integrated route.<br>
ProjectUseDecision references are derived from the ledger only. The Candidate is
the one the accepted Task's definition names in `portfolio_refs`. The Assay, Spike
and terminal owner Decision come from that Candidate. Sources are the Phase 1 SOURCE
registrations its observation batch cites, plus accepted corrections of them.
Evidence is exactly the artefacts the accepted Task selected. The governed-code
subject is the latest store-binding event. The caller supplies only the disposition,
rationale, limitations, next gates and D6 subset qualification.<br>
Phase 3 also delivers accept-all Task artefact selection. `close_task` accepts a
candidate-bearing Attempt when every candidate is a registered artefact and no two
share content (inherited SubmitForReview requires distinct hashes). Submission
hashes derive from those registrations, and AcceptTask selects exactly all
submitted candidates. There is no subset choice and no intent change.<br>
**Rationale/evidence:** Stephen authorised a read-only extraction on 2026-09-14.
The store fingerprint was unchanged, and the identity manifest, anchors and all
seven artefact hashes were verified. The historical ledger fails bed57bf8 replay at
position 147: 91 events use six command schemas that existed only on the unmerged
PR #258 branch and are absent from the current catalogue. Schema-identity history
cannot alias a schema with no active successor. The historical Task stopped at
TaskClaimStarted with a five-candidate Attempt. The Candidate cites only external
URLs. Making that history replayable and closable means porting the retired
machinery 06s excludes.<br>
**Affected specifications:** 06s §1, §4 items 4–6, Phase 3 and Phase 5; KAN-103, KAN-108.<br>
**Migration consequence:** None. No historical bytes, events or schemas change, and
P-050 stands.<br>
**Supersedes:** 06s §4's historical Task/ProjectUseDecision closure and
historical-replay requirements. PR #286 known limit 5 is superseded once Phase 3
delivers accept-all selection. No successor decision.

### P-058 — [DECISION] 06s Phase 4 scope: a fresh store, the required action subset and its delivery split

**Date/status:** 2026-09-14; accepted by Stephen.<br>
**Decision:** This records D1's required list for Phase 4. Of 06q §4 Step 5's 30
actions, four are delivered: `observe_source`, `correct_spec_01_source`,
`register_project_use_decision` and `accept_project_use_decision`. Phase 2's
`close_task` is not one of the 30, so 26 remain.
- **Fresh store.** The Phase 5 fresh bounded run uses a fresh control store. The live
  store `C:/Users/steph/TDL-ARS-WP64-Control` is not appended to, and it stays
  historical evidence under P-050 and P-057. Because of this, `bootstrap_genesis`
  (OR-140) and `bootstrap_assay_authority` (OR-101–108) are required route actions.
- **4a** covers the minimum the Phase 5 PARK/no_spike run needs:
  `bootstrap_genesis`, `bootstrap_assay_authority`, `request_spec_01`,
  `prepare_spec_01`, `return_spec_01_complete`, `review_spec_01_complete` and
  `decide_spec_01`. It also carries the fix for PR #288 known limit 9.
- **4a′** covers `return_spec_01_partial` and `review_spec_01_partial`, so a real
  Partial outcome is not a dead end. It may be folded into 4a.
- **4b** is scratch only: `request_spec_01_revisit`, `authorize_spec_01_retry`,
  `request_spec_01_retry`, `approve_spec_02`, `prepare_spec_02`, `start_spec_02`,
  `return_spec_02_complete`/`_partial`, `review_spec_02_complete`/`_partial` and
  `decide_spec_02`.
- **4c** is the assembled exact-main selection and independent boundary review.
- **Removed from the required list:**
  - `bootstrap_dossier_authority`, `bootstrap_path_authority` and `admit_dossier`;
  - `register_`, `review_` and `accept_spec_01_brief_inputs`, with the
    `spec_01_brief_input_set` record.
- **Records kept** (closed under D3): `spec-operator-brief-package`,
  `spec-operator-return` (the `return_*` actions register operator-supplied bytes)
  and `spec-02-live-run-approval`.
- **Scratch revisit proof** starts from a Partial Assay, with no runtime change (D5).
  4b first runs a scratch reproducer of revisit after a scored-Assay PARK; if the
  refusal is confirmed, it is recorded as a known limit.
- **SPEC-02 on scratch.** `start_spec_02` first tries to seed the running attempt,
  lease and resource grant that OR-017 requires through the existing operational
  fixture, as Phases 2–3 seed Tasks. If that is insufficient, the executor returns to
  Stephen before adding anything.
- **Scope checkpoint.** The §5.0 checkpoint applies to each sub-phase.<br>
**Rationale/evidence:** This comes from the Phase 4 scope table, read statically at
`3f3de7b5` before construction.
- `DiscoveryRuntime` refuses to prepare a command when the persisted ledger fails
  replay (`research_system/discovery/runtime.py:476-484`). P-057's extraction found
  the live ledger fails replay at position 147.
- No SPEC-01/02 row reads dossier expected-set or path-registration authority; only
  dossier admission does (`runtime.py:1361-1362`). No W11 row consumes the
  brief-input set.
- The revisit relation requires non-empty `revisit_requirements`
  (`rules.py:307-310`). Replay sets that field only for Partial and cancelled Assays
  and for Spikes (`replay/assay.py:211,281`, `replay/spike.py:376`), so a scored-Assay
  PARK appears unrevisitable. The existing revisit test uses a Partial Assay.<br>
**Affected specifications:** 06s D1 (its required list), Phase 4, and Phase 5 steps 1,
3 and 5; 06q §4 Step 5 (inventory only); KAN-109.<br>
**Migration consequence:** None. No historical bytes, events or schemas change, and the
live store is not read or mutated.<br>
**Supersedes:** 06s Phase 4's implied use of the complete 06q inventory, and its
unqualified "after PARK" revisit path for the scratch proof. No successor decision.<br>
**Amendment (2026-09-14, measured admission):** paired scratch-store probes at
`3f3de7b5` changed only the actor at an identical state.
- **Inherited admission enforces:**
  - author versus observer (OR-103/104);
  - reviewer versus author, requester and producer (OR-105/106, OR-006);
  - proposer versus reviewer (OR-107);
  - recorder equals producer (OR-004);
  - owner-only decisions (OR-108, OR-013).
- **It accepts:**
  - OR-140 genesis from any grant holder;
  - an OR-105 review requested by the rubric author;
  - an OR-003 Assay requested by the prospective producer, a non-owner human or the
    owner;
  - an OR-034 review requested by the producer or the future reviewer;
  - an OR-006 review recorded by the owner or a non-owner human;
  - an OR-012 proposal from the producer, the reviewer or the owner.

Stephen decided:
- **Route bindings.** The route refuses each of those through relations derived from
  the ledger, with no declared role, and `SpecOperatorConfig@1.0.0` is unchanged:
  - the genesis actor is the authority owner;
  - the OR-105 requester is not a content author;
  - the OR-003 requester is neither the prospective producer nor the owner;
  - the OR-034 requester is neither the producer nor the owner;
  - the OR-006 reviewer is not the owner;
  - the OR-012 proposer is not the producer, the reviewer or the owner;
  - the OR-013 selected option comes from the owner's own invocation.

  Each refusal ships a decisive control showing that admission would accept the
  input.
- **Pinned author identity.** Both committed Assay authority content files pin
  `created_by_actor_id` to the W11 test identity
  `act_019fed25-b33e-7740-b280-000000000205`, and admission requires it as the
  submitter. Which identity signs that content on the fresh store is decided at
  Phase 5 prep.
- **Known limits, with no change under D5:**
  - the OR-106 review context is fixed runtime literals
    (`research_system/discovery/runtime.py:1126-1166`);
  - the OR-006 context-manifest hash, trace refs and independence grade are
    unchecked caller strings.

**Design acceptance (2026-09-14):** Stephen accepted the Phase 4a design
recommendations.
- **Inline operator return.** The operator return record carries the operator's
  scorecard and closed string lists inline, not separately registered artefacts. The
  accepted Task's evidence stays bound at result time through the ProjectUseDecision.
- **Two PRs for 4a.**
  - 4a-1: `bootstrap_genesis`, `bootstrap_assay_authority` and `request_spec_01`,
    with the closed `spec-assay-intent` record and the PR #288 known limit 9 fix.
  - 4a-2: `prepare_spec_01`, `return_spec_01_complete`, `review_spec_01_complete`
    and `decide_spec_01`, with both operator records and the positive path to an
    accepted project-use result.
- **Producer relation, a known limit (D5).** The route derives the prospective
  producer relation's hash from the producer actor and the route identity. W11
  §4.3's profile, context and grant references are not modelled by the inherited
  runtime.

**4a-2 design decisions (2026-09-15):** Stephen accepted both recommendations from
the 4a-2 design pass at `52c2ce42`, after PR #290 merged.
- **Operational provenance of the operator records.**
  - **The problem:** every `RegisterArtefact` manifest names a Task, dispatch,
    attempt and context packet, and admission checks none of them (Phase 3
    measurement). The merged `spec-assay-intent` 1.0.0 carries no production
    fields, and IDs invented by the route would be fabricated.
  - **The decision:** the brief package and the operator return derive them from
    the ledger. The source is the one Task whose definition names the Candidate, and
    that Task's started Attempt: an Attempt carries `dispatch_id` from creation and
    `start` from `AttemptStarted` (`research_system/command/reducers.py:777,815`).
    The intent schema is unchanged.
  - **Consequence for Phase 5:** that Task is created and its Attempt started before
    `prepare_spec_01`. The same Task is later closed and cited by the
    ProjectUseDecision.
- **The accepted Assay bar is fixture content.**
  - **What the committed content is:** W11 test-fixture authority, with one boolean
    `identity` gate axis, placeholder `1111…` hashes and a pinned test author.
  - **What admission allows:** it binds every axis result to those files, and
    derives the mechanical recommendation as PROMOTE or KILL only
    (`research_system/discovery/rules.py:466-540`).
  - **The decision:** 4a-2 derives the scorecard from whichever bar is accepted.
    The operator supplies each rubric axis's value, rationale and unmet condition
    codes. The route derives every other field, and runs the inherited scorecard
    rule over the result before the return is registered. Tests use the fixture
    bar, and this is a known limit.
  - **Phase 5 prep now decides both** the replacement Assay authority content, which
    must express SPEC-01's axes, and the identity that signs it.

**4a-2 review decisions (2026-09-15):** Codex reviewed PR #291 at `3d1bf07b`. Stephen
chose the recommended option for two of its findings.
- **The Assay producer re-supplies the operator return.**
  - **The problem:** 06q assigns `return_spec_01_complete` to the Assay producer.
    Inherited admission, however, keeps `RegisterArtefact` owner-only
    (`tests/research_system/integration/test_spec_result.py:794-797`). So the owner's
    invocation supplied the return's content, while the scorecard is attributed to
    the producer.
  - **The decision:** the owner still registers the bytes. The producer's own OR-004
    invocation must carry the exact operator return that was registered, or it is
    refused before anything is appended.
  - **Known limit:** four of the return's fields are not in the scorecard: direct
    sources, findings, validation and unresolved findings. They are checked at the
    producer's submission, but the OR-004 event does not record them.
- **No non-approving outcome review.**
  - **The basis:** 06q defines `review_spec_01_complete` as recording a satisfying
    verdict, and D1's list has no action for any other verdict. The route keeps
    `approve` fixed.
  - **Consequence:** a reviewer who does not approve does not invoke the action. The
    review stays pending and `decide_spec_01` stays refused.
  - **Known limit:** nothing durably records a negative review.

**4a-2 review decisions, round 2 (2026-09-16):** Codex reviewed PR #291 at `1cb6053a`
and raised five findings. Each was confirmed against the code, and Stephen accepted
every recommendation.
- **The manifests carry the producing Attempt's identities.**
  - **The problem:** each operator record's manifest paired its Attempt ID with the
    store binding's git head and recovery digest. The Attempt's own `code_identity`
    and `environment_fingerprint` (`AttemptStarted`) went unused, and admission checks
    neither manifest field. The test fixture already showed the mismatch.
  - **The decision:** both records carry the Attempt's start identities, and the
    manifests take them from there. A code identity that is not a git commit makes an
    invalid record.
- **The Task must be unamended since dispatch.**
  - **The problem:** admission accepts `AmendTask` while an Attempt runs, and the
    Attempt keeps its dispatched `task_revision`. The route matched the Candidate
    against the Task's latest definition.
  - **The decision:** the records refuse unless the Task's current revision is the
    Attempt's. Both records carry that revision. Phase 5 must not amend the Task
    mid-Attempt.
- **SPEC-01's numeric PROMOTE rule is never evaluated.**
  - **The problem:** admission derives a mechanical PROMOTE from the required gate
    axes alone (`research_system/discovery/rules.py:506-513`). Integer axes are only
    type- and bounds-checked, and the rubric's `rule_evaluation_algorithm_id` is bound
    by hash but never run. SPEC-01 requires Axis 1 pass, Axes 2+3 at least 4 and
    neither zero, so a topology pass with both integer axes at zero would still be
    admitted as mechanical PROMOTE. The 2026-09-15 Phase 5 prep decision assumed that
    replacing the content would carry the rule. It cannot.
  - **The decision:** the route refuses to propose (OR-012) or select (OR-013)
    PROMOTE while the accepted bar has any axis the inherited rule does not evaluate:
    a non-gate axis, or one outside the required set. The fixture bar has none, so
    scratch PROMOTE is unaffected. Real SPEC-01 content cannot reach PROMOTE until its
    rule is evaluated, which becomes a Phase 5 prep prerequisite. Implementing the rule
    now would bind to axis IDs that Phase 5 has not authored, and evaluating it in
    admission is a runtime change (D5).
- **The complete return's evidence sections must be non-empty.** The brief requires
  a direct-source table, findings and focused validation. `direct_sources`,
  `findings` and `validation` each require at least one item. The operator return
  schema is not yet on main, so its version is unchanged.
- **PROMOTE is refused while the return lists unresolved findings.**
  - **The basis:** the brief makes an unresolved primary-paper/code discrepancy
    blocking, and says any gate the scorecard cannot express makes the outcome PARK.
  - **The decision:** OR-012 and OR-013 both refuse PROMOTE while the registered
    return lists any unresolved finding. Both are needed, because admission lets the
    owner select PROMOTE on any mechanical PROMOTE, whatever was proposed.
  - **Known limit:** the return cannot mark which findings block, so every unresolved
    finding blocks. Non-blocking items belong under limitations.
- **Outside this PR:** the merged project-use route (`spec_result.py`, PR #288)
  derives its manifest identities and Task match the same way as the first two
  findings. That fix is a post-merge follow-up.

**4a-2 review decisions, round 3 (2026-09-16):** Codex reviewed PR #291 at `4822f41f`
and raised five findings, each confirmed against the code. Stephen chose option 1 of
the convergence assessment: a final fix round, one known limit, and a stopping rule.
- **The convergence finding.**
  - **Flat on count and severity:** the three rounds returned 5, 5 and 5 findings,
    with four rated P1 each time.
  - **Families saturated:** round 3 opened no new finding family.
  - **Origin:** four of its findings were latent since `7cc883cc`, and one sat in code
    the round-2 fix added.
  - **Reachability:** none can occur on the planned Phase 5 path.
  - **Why the count will not reach zero:** each route guard over inherited admission
    has its own edge cases.
- **Fixed in this round.**
  - A record requires its Attempt to be running. A finished Attempt keeps its start
    record, so it could otherwise be cited as producing a record created after it
    ended.
  - The Task must name no other registered Candidate. The project-use result requires
    exactly one (`research_system/discovery/spec_result.py:302-304`), so the records
    would otherwise be registered for a lineage that could never close.
  - An exact retry requires the exact evidence field set. OR-006 and OR-013 payloads
    read only the known fields, so a padded repeat was answered from the receipt
    although it would have been refused before the effect.
  - The PROMOTE refusal reads the Assay's bar from the registered return's scorecard,
    which admission bound to that bar when it scored. It no longer reads the currently
    accepted bar, which W11 allows to be succeeded while an opened Assay keeps its
    frozen bar (`design/11-portfolio-and-discovery-lifecycle.md:717-720`).
- **Known limit: derivation before the registration lock.**
  - **The gap:** a record is derived from a ledger snapshot before the writer lock is
    taken. A concurrent writer that scores or cancels the Assay, or amends the Task,
    in between would leave a registered record whose prerequisites held only at its
    stated causal prefix.
  - **Why not fixed here:** this is the same shape as PR #290 known limit 7, and Phase
    5's single operator does not create the race.
  - **Follow-up:** the shared document registration service already runs inside
    admission's writer lock, and could refuse when the ledger tail has moved. That fix
    belongs in one follow-up covering the SOURCE, project-use and operator-record
    registrations together.
- **Stopping rule for PR #291 from round 4.** A review finding gets code in this PR
  only if it is either:
  - a defect in code that round 3 added; or
  - a false durable claim reachable on the planned Phase 5 path as amended.

  Every other finding is recorded as a known limit or a follow-up, and the PR proceeds
  to Stephen's review and merge.
- **§5.0 continuation.** 4a-2 has passed the "one session plus one follow-up"
  checkpoint. Stephen's acceptance of option 1 is the owner decision to continue for
  this final round, within the 2,500-line checkpoint.

**4a-2 follow-up decisions (2026-09-16):** after PR #291 merged at `9fbab7ec`, the
follow-up design pass put three questions to Stephen, who chose the recommended
option for each.
- **The project-use decision cites its closure Attempt.**
  - **The problem (PR #291 known limit 10):** the merged route (`spec_result.py`,
    PR #288) paired the closure Attempt's ID in the ProjectUseDecision manifest with
    the store binding's git head and recovery digest. It also matched the Candidate
    against the Task's current definition, although admission accepts `AmendTask`
    after the Attempt has run. A scratch-store fixture showed the second gap is
    reachable: the Task was amended after its Attempt completed, `close_task`
    accepted it, and the decision was registered.
  - **The decision:** the manifest's `code_commit` and `environment_fingerprint` are
    the closure Attempt's start identities. They are re-derived from the ledger, like
    its dispatch, Attempt and context packet. The registration refuses unless the
    accepted Task is still at the revision the Attempt was dispatched on, which also
    settles the Candidate match. The round-3 running-Attempt rule cannot apply, because
    the decision is registered after closure.
  - **No schema change:** `project-use-decision` stays 1.0.0, and its
    `governed_code_subject` still records the store binding at decision time. A
    non-git Attempt code identity is refused by the inherited `RegisterArtefact`
    command schema before anything is published.
  - **Migration consequence:** registrations made under the earlier derivation no
    longer re-verify. Only scratch stores hold them.
- **Known limit: orphan reuse on the project-use route.** Orphaned decision bytes are
  re-derived only at their own causal prefix. Unlike the operator records since PR #291
  round 1, the route does not re-check their prerequisites on the current ledger. The
  gap needs a crash between publication and registration followed by a lapse, such as
  a later revisit or a superseded correction. It is a follow-up.
- **Document registrations refuse a moved ledger.**
  - **The problem (PR #291 known limit 14):** every SPEC document registration derives
    its document and prerequisites from a ledger snapshot before admission takes its
    writer lock. A concurrent writer in that window could leave a registered record
    whose prerequisites held only at an earlier prefix.
  - **The measurement:** nothing in a route invocation appends in that window. Binding
    revalidation only reads. Admission appends only the command's own events, after
    the bytes are published. Grant auto-activation exists only in the
    `GovernedTestCommandService` test adapter.
  - **The decision:** inside the lock and before publishing, the shared document
    registration service compares the ledger tail's position and hash with the
    snapshot the effect was derived from, and refuses if they differ. This covers
    SOURCE, project-use and both SPEC-01 operator records. The SOURCE path takes its
    snapshot when `advance` starts. Re-deriving under the lock was rejected, because
    it would hold the writer lock through several replays.
  - **Consequence:** an unrelated writer appending in the window also refuses the
    registration, and the caller retries. A concurrent identical registration
    conflicts instead of replaying, and a later retry reads its receipt.

**4a′ design decisions (2026-09-17):** the 4a′ design pass at `8e14d1da` put six
questions to Stephen for `return_spec_01_partial` and `review_spec_01_partial`. Paired
scratch-store probes measured OR-005, OR-035 and OR-007 first. Stephen accepted every
recommendation.
- **A separate closed Partial return record.**
  - **The problem:** the merged `spec-operator-return` 1.0.0 fixes `intent.action` to
    `return_spec_01_complete` and requires `scorecard` and `scorecard_sha256`. OR-005
    binds an `ars://portfolio/assay-partial` artefact instead
    (`research_system/discovery/rules.py:54-75, 717-775`).
  - **The decision:** a new closed record, `ars://portfolio/spec-operator-partial-return`
    1.0.0, with its own object kind. The operator supplies the W11 Partial judgements
    (completed and unmet axes and evidence, reason codes, limitations, revisit
    requirements, and a PARK, KILL or UNABLE_TO_SCORE recommendation) and the brief's
    return fields (direct sources, findings, validation, unresolved findings and
    prohibited inferences). The route derives every reference, the Partial artefact and
    its digest, and runs the inherited Partial binding rule before registration.
    `spec-operator-return` 1.0.0 is unchanged.
  - **Rejected:** a 2.0.0 return covering both outcomes. It changes a merged version, and
    with one object kind, bytes orphaned by a crash on the complete path would block the
    Partial on that Assay permanently.
  - **Supersedes:** 06q's "same schema/version" for `return_spec_01_partial`, and adds a
    record to P-058's records-kept list.
- **`spec-assay-intent` 1.1.0.**
  - **The problem:** the merged 1.0.0 is a closed enum of the seven 4a actions, so neither
    Partial action validates.
  - **The decision:** a new 1.1.0 adds both Partial actions, each with a Candidate and no
    other field. 1.0.0 stays. The route validates intents at 1.1.0. Intents are never
    stored, so no historical bytes change. 4b decides its own version at its design pass.
- **Shared identities for each alternative pair.**
  - **The decision:** `return_spec_01_partial` uses the return artefact identity and
    `review_spec_01_partial` the outcome-review identity that the complete actions
    already derive. The alternatives exclude each other at the first durable mutation:
    the route refuses anything else on a stream the action owns, and inherited
    admission refuses a second registration on an existing artefact stream
    (`research_system/command/reducers.py:1423-1434`). OR-004/OR-005 and OR-034/OR-035
    are already exclusive by Assay status.
  - **Evaluation:** the alternative not taken conflicts, naming the one taken; there is no
    fourth state. The status listing enumerates only the alternative the route issued.
  - **Known limit:** an owner who registers the wrong alternative cannot switch on that
    Assay. W11's recovery, cancellation (OR-008), is not on D1's list.
  - **No public aliases** (`return_spec_01`, `review_spec_01`) are added.
- **4a′ ends at a reviewed Partial Assay.**
  - **The measurement:** after an approving OR-007, the Assay is `partial_reviewed`, the
    review `satisfied`, and the Candidate `assay_revisit_eligible` with no Decision.
    OR-012 requires an `assay_scored` Candidate and a `reviewed` Assay
    (`research_system/discovery/runtime.py:1567-1604`), and the project-use result
    requires a resolved terminal Decision (`research_system/discovery/spec_result.py:310-316`).
  - **The decision:** `decide_spec_01` and the project-use registration refuse on a Partial;
    status adds no field or state. 4b's revisit starts from this state.
  - **Consequences:** each revisit requirement must later appear verbatim in a Scout
    observation's `matching_facts` (`research_system/discovery/rules.py:307-310`), so the
    operator writes them as exact facts. Whether an OR-010 PARK or KILL after a Partial
    can close through project-use is a 4b design question.
- **Measured admission and route bindings.** Each probe changed one actor or field at an
  identical Assay state.
  - **OR-005:** admission refuses every recorder but the Assay producer (steward, owner,
    another human, the future reviewer), and a PROMOTE, an empty unmet-axis or
    revisit-requirement list, or a wrong digest. It accepts any of the three
    recommendations with any reason codes or evidence claims, and needs no brief, Task
    or registered return. The route adds no actor check; the producer's own OR-005 must
    carry the exact registered Partial return, compared as canonical JSON.
  - **OR-035:** admission accepts a request from the producer, the owner, the future
    reviewer and the steward. The route refuses the producer and the owner, as for OR-034.
  - **OR-007:** admission refuses the requester and the producer, and accepts the owner and
    a non-owner human. The route refuses the owner, as for OR-006.
  - **Non-approving review:** admission records `changes_requested` without satisfying the
    review, and then refuses a later `approve` on it. The route records only `approve`, so
    PR #291 known limit 9 extends to the Partial.
- **The 4a-2 rules apply unchanged**, with one exception.
  - **Unchanged:** the ledger provenance (the one Task naming only this Candidate, unamended
    since dispatch, its running Attempt, and the Task and Attempt the brief was issued to);
    the Attempt's identities in the manifest; owner registration with the producer's exact
    re-supply; the in-lock moved-ledger refusal; the completed-action conflict; the exact
    retry field set; and orphan reuse only when the bytes re-derive and their
    prerequisites still hold. The PROMOTE refusals do not apply.
  - **The exception:** the Partial return requires non-empty `findings` only. A Partial may
    stop before any source or validation is reached (W11 §4.3), and its unmet evidence and
    reason codes record why. `direct_sources` and `validation` may be empty.
- **Scope:** about nine files and 900–1,200 added lines, within the §5.0 checkpoint.

**4b design decisions (2026-09-17):** after PR #296 merged at `dc04e830`, the 4b design pass
put six questions to Stephen. Paired scratch-store probes at `dc04e830` measured OR-009,
OR-010 and OR-011 first, and reproduced the scored-Assay PARK revisit. Stephen accepted
every recommendation.
- **4b ships as two PRs.**
  - **4b-1:** `request_spec_01_revisit` (OR-009), `authorize_spec_01_retry` (OR-010,
    RETRY) and `request_spec_01_retry` (OR-011), with the retry identity model.
  - **4b-2:** the SPEC-02 sequence and the `spec-02-live-run-approval` record, with its own
    design pass after 4b-1 merges.
  - **The basis:** 4a's seven actions took two PRs (+1,180 and +2,194 lines) and 4a′'s two
    took +895, so eleven actions in one PR would pass the §5.0 checkpoint.
- **Retry identities: an optional `assay_ordinal`.**
  - **The problem:** every SPEC-01 route identity (Assay, brief, return, review and
    Decision) is derived from the Candidate and the action name alone
    (`research_system/discovery/spec_assay.py::subject_ids`), so a retry Assay would
    derive the first sequence's identities, and the status listing enumerates only the
    first Assay.
  - **The decision:** SPEC-01 intents take an optional `assay_ordinal` of 2 or more. Without
    it, every identity is derived exactly as before, so merged records re-derive unchanged.
    With it, the identities also derive from the ordinal. The route requires Assay *n* to
    have been created by its own route-issued retry from Assay *n−1*.
  - **Rejected:** acting on the Candidate's current Assay implicitly. An earlier Assay could
    not be addressed, and a completed action would read `not_started` again after a retry.
- **One Task and one running Attempt across the retry lineage.**
  - **The decision:** the operator records keep their rules unchanged: exactly one Task
    naming only the Candidate, unamended since dispatch, and its one started Attempt,
    still running. That Attempt therefore stays running from the first brief to the last
    return of every Assay in the Candidate's lineage.
  - **Rejected:** a new Attempt per Assay. It changes the one-started-Attempt rule and meets
    PR #286's known limit that there is no rework path once an Attempt ends.
  - **Phase 5:** no retry is planned, so its ordering is unchanged.
- **The revisit predicate comes from a route-issued SOURCE observation.**
  - **The measurement:** OR-009 requires one Scout observation, later than both the outcome
    review verdict and any PARK, whose `matching_facts` contain every revisit requirement
    verbatim (`research_system/discovery/rules.py:253-313`). Admission refuses an OR-029
    batch with no Candidate blueprint, so every predicate observation also registers a
    Candidate.
  - **The decision:** `request_spec_01_revisit` selects the earliest route-issued
    `observe_source` observation after that point whose facts contain every requirement.
    The caller supplies no observation identity. With none, the revisit is refused.
  - **Known limits:** `observe_source` records exactly one fact, its title, so only a Partial
    with a single revisit requirement can be revisited on the route, and each revisit
    observation registers a Candidate named after the requirement.
  - **Rejected:** a new route action for a multi-fact predicate observation (outside D1's
    list), and a caller-named Scout observation (not route-issued evidence).
- **Measured admission and route bindings.** Each acceptance consumed its own identical Partial
  Assay.
  - **OR-009:** admission accepts a proposal from the producer, the owner, the outcome reviewer
    and the steward. The route refuses the producer, the owner and that Assay's outcome
    reviewer, as for OR-012.
  - **OR-010:** admission refuses a non-owner human, the steward and the producer, and accepts
    the owner. The route adds no actor check and fixes the selected option to RETRY.
  - **OR-011:** admission accepts a retry request from the producer, the owner and the steward.
    The route refuses the producer and the owner, as for OR-003.
  - **After OR-011:** the new Assay is `evidence_collecting`, the old one `superseded`, and the
    Candidate `assay_pending` on the new Assay.
- **`spec-assay-intent` 1.2.0** adds the three actions and `assay_ordinal`; 1.0.0 and 1.1.0
  stay.
- **Known limits, with no runtime change (D5):**
  - **A scored-Assay PARK cannot be revisited (reproduced).** After an OR-013 PARK, the
    Candidate is `parked` but the Assay stays `reviewed`, with no revisit requirements, and
    OR-009 is refused. The identical construction on a Partial Assay is accepted. This
    confirms the P-058 scope decision of 2026-09-14.
  - **A revisit resolved PARK or KILL is off the route.** `authorize_spec_01_retry` records
    only RETRY. A revisit PARK leaves the Candidate `parked` with no promotion gate
    (measured), so the project-use result cannot close it.
- **Scope (4b-1):** about ten files and 1,500–2,200 added lines, near the §5.0 checkpoint.

**PR #297 review decisions (2026-09-17):** Codex's first review of `0512f924` found four
defects in 4b-1. Stephen accepted the review stopping rule for #297, and decided the one
finding that needed a schema version.
- **A later Assay's operator records carry its ordinal.**
  - **The defect:** a retried Assay's brief, return and Partial return recorded their intent
    as `{action, candidate_id}`. That intent derives the first Assay's identities, while
    the record's own `assay_id` names the later Assay.
  - **The decision:** `spec-operator-brief-package`, `spec-operator-return` and
    `spec-operator-partial-return` each gain version 1.1.0, whose intent requires an
    `assay_ordinal` of 2 or more. The route writes 1.1.0 only for Assay 2 and later, so
    every first-Assay record stays 1.0.0 and merged records re-derive unchanged. Each
    registration manifest names its record's version.
  - **Rejected:** deferring it to 4b-2 or 4c as a known limit.
- **Route corrections that needed no decision:**
  - **The revisit predicate:** an observation counts only if the SOURCE route's own
    completion check accepts it. Checking three of its fields let an observation that
    SOURCE status rejects satisfy the predicate.
  - **The taken return:** the route now recognizes which return alternative an Assay took
    at that Assay's ordinal. Before, a later Assay's Partial return was missing from the
    listing and not excluded against its complete alternative.
  - **A non-integer ordinal literal is refused.** JSON Schema accepts `2.0` as an
    integer, but it derives other identities and P0 canonical JSON rejects
    floating-point values.

**4b-2 design decisions (2026-09-18):** after PR #297 merged at `f690efd6`, the 4b-2 design
pass measured the whole SPEC-02 Spike sequence on scratch stores: OR-014, OR-015, OR-016,
OR-017, OR-018, OR-019, OR-036, OR-037, OR-020, OR-021, OR-026 and OR-027, each with actor
variations. The complete path ran end to end and left the Candidate
`preregistration_authorized`. Stephen accepted every recommendation.
- **4b-2 ships as two PRs.**
  - **4b-2a:** `approve_spec_02`, `prepare_spec_02` and `start_spec_02` (OR-014 to OR-017).
  - **4b-2b:** `return_spec_02_complete`, `return_spec_02_partial`, `review_spec_02_complete`,
    `review_spec_02_partial` and `decide_spec_02`.
  - **The basis:** eight actions and fifteen effects, plus three new records, exceed the
    §5.0 checkpoint that 4a-2's seven actions already split across two PRs.
- **SPEC-02 gets its own records.**
  - **The measurement:** the merged `spec-operator-brief-package` and `spec-operator-return`
    fix `intent.action` to `prepare_spec_01` and `return_spec_01_complete`, and the return
    requires an Assay scorecard, which a Spike has not. A Spike's own artefacts are the
    inherited `ars://portfolio/spike-plan` and `ars://portfolio/spike-verdict`, both 1.0.0.
  - **The decision:** new closed schemas with their own object kinds for the SPEC-02 brief and
    return, as 4a′ did for the Partial return. The merged SPEC-01 records are untouched.
- **The SPEC-02 approval record.** New closed `ars://portfolio/spec-02-live-run-approval`
  1.0.0, registered by the owner, binding the Candidate, the exact OR-013 PROMOTE Decision,
  the route, the scope and the cost ceiling. It changes no Candidate state, and
  `start_spec_02` is refused without it.
- **Spike evidence artefacts stay operator-mediated.** The verdict must cite registered
  canonical artefacts, one of a validation, verification or review type (measured). No SPEC
  action registers them, and none is added; the route verifies the refs the operator names.
- **The operational fixture is re-dated in the SPEC-02 tests (test-only).**
  - **The measurement:** `bind_scratch_route` fixes the route clock at 2026-09-10, while the
    C1 fixture leases in a 2026-08-01 window. OR-017 requires a live lease, so every start was
    refused, and a renewal was refused as `lease_expired`. Re-dating the fixture's window onto
    the route's day seeds an active lease and admits the start.
  - **The decision:** the SPEC-02 tests re-date the fixture. No production change (P-058's
    "return to Stephen" point for `start_spec_02` seeding).
- **Route bindings mirror SPEC-01's, against measured admission.** Admission accepts the plan
  from the steward, the producer, the owner and an unrelated human; the execution proposal from
  the producer, the owner and the steward; the verdict, the review request and the decision
  proposal from the producer. It already holds the execution approval and the final resolution
  to the owner, and binds the start to the lease holder.
  - The route refuses the producer and the owner registering the plan or proposing execution,
    binds the verdict to the Spike producer, refuses the producer or the owner requesting the
    outcome review and the owner recording it, and refuses the producer, the reviewer or the
    owner proposing the decision, as for OR-012.
  - **Known limit:** rows after OR-017 record one accepted actor each, because an acceptance
    consumes the row and a store holds one Attempt and Lease.
- **A Partial Spike is terminal on the route (measured).** OR-019 leaves the Candidate
  `spike_partial_recorded`; OR-037 and OR-021 leave it `spike_revisit_eligible` with the Spike
  `partial_reviewed`; OR-026 is then refused for PROMOTE and for PARK. The Spike revisit rows
  (OR-023 to OR-025) are outside the agreed action list. The Partial pair still ships, with
  this recorded as a known limit and no runtime change.
- **`spec-assay-intent` 1.3.0** adds the eight SPEC-02 actions; 1.0.0, 1.1.0 and 1.2.0 stay.
  SPEC-02 actions carry no `assay_ordinal`: a Spike follows its Candidate's promoted Assay.

**PR #298 review decisions (2026-09-24):** two rounds of Codex review and one CodeRabbit review
on the SPEC-02 start, under the stopping rule Stephen accepted for #298 on 2026-09-18.

- **The SPEC-02 contract's "12 GB" and "5 GB" are binary megabytes (Stephen's decision,
  2026-09-24):** `memory_limit_mb` 12,288 and `storage_limit_mb` 5,120, not the decimal 12,000
  and 5,000 the first transcription chose. The open question was raised when the contract-limits
  check was added in round 1; Stephen resolved it as the value everyone here means by GB. The
  route transcribes the pinned contract's prose, so the reading is a decision, not a derivation,
  and a test binds the transcription to the contract's pinned bytes.
- **A Lease's liveness is a fact about the moment its row was taken (round 2, Codex P1).** The
  route holds the Spike execution rows to a Lease that is live at the trusted submission time,
  and re-derives a recorded row with no clock at all. Admission reads a Lease's expiry only at
  OR-017, so without this the route recorded an execution authority OR-017 must refuse and
  renewal cannot rescue.
  - **Measured, and it changed the design:** the bound fixture stamps ledger `recorded_at` from
    the real clock while its operational payloads carry the re-dated Lease window. Two clocks
    over one store, so a row's own `recorded_at` is not a moment its Lease can be judged against.
  - **Known limit:** nothing re-checks a Lease between the rows of one start, and the route has
    no Spike revisit, so a start whose Lease expires mid-sequence is abandoned, not resumed.
- **CodeRabbit's three findings are declined, each verified against the code first.** None is a
  defect in the latest round's code, and none is a false durable claim on the Phase 5 path.
  - **The approval ceiling cannot omit a limit.** The route already refuses it: the ceiling is
    checked against every key of `_SPEC_02_LIMITS`, and a missing key fails the integer test.
    **Known limit:** the record's own schema does not restate this, so a future contract that
    dropped a limit would leave the plan's matching limit unbounded.
  - **The five deferred 4b-2b actions fall through to the SOURCE contract,** which refuses them
    before any state evaluation or ledger change. The refusal names the SOURCE contract rather
    than the unimplemented action. Error reporting only; 4b-2b implements them.
  - **The Ruff findings do not hold under the governing config.** Root `.ruff.toml` sets only
    `line-length`, so neither `E501` nor `I` is selected; CodeRabbit forced both with
    `--select I,E501`. Four lines in the SPEC-02 tests do exceed 120 characters, all from
    `5f78e5d0` rather than the latest round, and `# fmt: skip` is the house idiom that keeps
    them. Recorded as a follow-up, not a fix in this PR.

**4b-2b design decisions (2026-09-25):** PR #298 merged at `764d8b9f`, whose tree equals the
certified candidate `3dfe0456`. The 4b-2b design pass then measured the Spike's return, review
and decision rows at `764d8b9f`: nineteen probes, each on its own scratch store with the Spike
started, and one run from a Candidate the public SOURCE and SPEC-01 route promoted. Stephen
accepted every recommendation.
- **Measured admission.**
  - OR-018 records a PASS or FAIL verdict from the producer, the steward, the owner or an
    unrelated human, with the Lease expired, and after the Attempt has completed.
  - OR-019 records a Partial verdict from the steward, and is refused once the Lease has
    expired. It leaves the Attempt `partial` and the Lease `released`.
  - A verdict citing an artefact whose manifest names another Attempt is recorded.
  - OR-036 accepts the owner and the producer as the review requester. OR-020 refuses the
    producer and the requester, and accepts the owner and an unrelated human.
  - OR-026 accepts the owner, the reviewer, the steward and the producer as proposer. OR-027 is
    owner-only and is not bound to the proposal: PROMOTE was selected after a PARK proposal,
    and PARK was selected with no revisit triggers.
  - Both rows apply the verdict truth table: after a FAIL with a triggered kill condition only
    KILL, after a FAIL without one PARK or KILL, and after a PASS any option, including KILL.
  - From the public Candidate, the complete Spike path ran through `close_task` to an accepted
    project-use result that records the Spike.
- **Decisions.**
  1. **One return record.** A new closed `ars://portfolio/spec-02-operator-return` 1.0.0, with
     its own object kind, serves both return actions: one W11 `spike-verdict` carries PASS, FAIL
     and PARTIAL, and 06q gives both returns the same schema and version. Its verdict must
     match the action. The two actions share the return and outcome-review identities, so the
     alternative not taken conflicts, as in 4a′. The operator supplies the eleven W11 verdict
     judgements; the route derives the Spike, Candidate, Assay, plan and Attempt references
     and runs admission's own verdict rule before registration.
  2. **The cited evidence comes from the Spike's own Attempt.** Every `artefact_refs` entry must
     name the Spike's Attempt in its registered manifest. `validation_refs` keep admission's
     type check only, so an independent validator may be cited. Every artefact that a success
     predicate, failure predicate or kill condition cites as evidence must name the Spike's Attempt
     too; a predicate may still cite a portfolio record (PR #309 review, 2026-10-02, Codex P1).
  3. **A Partial return needs a live Lease.** Both Partial rows are held to a Lease that is live
     at their trusted submission time, the rule the start rows have, and re-deriving a recorded
     row consults no clock. The complete return needs no Lease. **Known limit:** a Lease that
     expires between the two Partial rows leaves the return unrecordable, as for the start.
  4. **The mechanical recommendation is evidence only** (W11 §4.4). The route adds no PROMOTE
     condition beyond admission's verdict truth table. SPEC-01's check reads the recommendation
     admission derives; for a Spike, the fact admission validates is the verdict.
  5. **No KILL after a PASS.** W11 §4.5 requires a satisfied kill or failure condition for KILL,
     and admission accepts a KILL proposal after a PASS, so the route refuses it at both OR-026
     and OR-027.
  6. **The complete public path reaches an accepted project-use result** through `close_task`,
     closing PR #288's known limit that the Spike branch is tested at function level only.
     **Phase 5 prep:** a Spike PROMOTE permits `adopt_default`, while the SPEC-02 contract says
     no result supports a superiority or paper claim.
  7. **The stuck start is asserted in 4b-2b (Stephen, 2026-09-24).** PR #298 known limit 7:
     once the Lease expires between the start's rows, the route refuses the next row, the start
     stays `prepared`, and a renewal is rejected as `lease_expired`, so the start cannot be
     resumed.
  8. **The four SPEC-02 test lines over 120 characters** are wrapped in 4b-2b, in their own
     commit.
- **Confirmed by measurement** (the 2026-09-18 bindings): the route records the verdict only from
  the prospective producer; refuses the producer or the owner requesting the outcome review,
  and the owner recording it; records only an approving review; and refuses the producer, the
  reviewer or the owner proposing the decision. A PARK needs the owner's revisit triggers, as
  for SPEC-01. A Partial Spike is terminal: `decide_spec_02` refuses it, so it reaches no
  project-use result.
- **Known limits:** a validation artefact's independence is not checked; the operator's
  mechanical recommendation is not validated; nothing checks the accepted plan's
  outcome-to-next-step mapping after a FAIL without a triggered kill condition; and OR-019
  closes the Attempt as Partial, so its Task reaches no project-use result.

**Test-cost decisions (2026-10-01):** the certifying packet for 4b-2b's candidate `bd5c971e`
needed about a day of Stephen's machine, with single tests running for hours. Stephen stopped it
on 2026-09-26. The route tests' cost had grown with every sub-phase since #291 and was recorded
as a known limit, not escalated. It was measured before any fix was chosen.
- **Measured.** These runs used scratch stores at `bd5c971e`, each one process, or eight on the
  machine's eight performance cores. The simulated caches wrapped functions from outside the
  code.
  - The public SPEC-01 path test alone took 16m47s for 31 CLI invocations, on a ledger of at most
    89 events. The cost of an invocation grew from 5 s to 115 s. Git was a flat 2.5 s per
    invocation, 8% of the test.
  - Replay was 78% of the time: 895 ledger replays, and 75% of their time repeated an event
    list the same invocation had already replayed. Every replay re-loads every owner
    administration decision from the object store (33,181 loads in the test), and
    `SchemaRegistry.validate` rebuilds its reference registry and validator on each of its
    152,875 calls.
  - A replay cache for the route's own calls, one invocation's lifetime, plus validator
    reuse, both simulated, cut the SPEC-02 refusals test from 7,395 s to 873 s of CPU (2h12m
    to 17.6 minutes), the complete SPEC-02 path from 5,531 s to 2,219 s, and the SPEC-01 path
    from 1,137 s to 608 s. Every assertion passed under each.
  - Also loading each owner decision once per invocation took only 2 more points off the
    SPEC-02 path.
  - With both fixes simulated, the next cost is the store binding's revalidation. It runs about
    five times per invocation, and each run re-checks the whole schema catalogue against the
    bound Git subject: `git archive`, then a byte comparison of every schema file, 1.3 s each,
    about 37% of what remains.
- **Decisions (Stephen accepted every recommendation, 2026-10-01).**
  1. **A route-side replay cache, in 4b-2b as its own commit.** Within one coordinator
     operation (`status`, `advance` or `result`), the route replays an identical event list
     once. The cache is keyed by the list's exact canonical bytes and the replay options,
     every caller receives its own copy, and it ends with the operation. Admission, the
     command service and the authority resolver keep their own replays, so no check moves
     out from under the writer lock.
  2. **Schema-validator reuse** in `SchemaRegistry.validate` goes in a separate PR, because it
     is platform code outside P-058. 4b-2b does not depend on it.
  3. **The owner-decision re-load stays.** Loading each decision once would weaken a
     deliberate re-load for 2 points.
  4. **The binding's schema-catalogue re-check stays (D5).** It is recorded as a Phase 5 prep
     cost. Phase 5 runs on a fresh store (P-058, 2026-09-14), whose ledger is about as long as
     the test stores', so live invocations cost about what the tests measure.
  5. **Test restructuring is deferred**: a shared starting state, and mutation controls aimed
     at smaller tests. It is revisited only if a budget fails.
  6. **A time budget.**
     - Certification runs only between 02:00 and 11:00, on 8 workers.
     - A group over 60 minutes fails the packet's budget. The runner records the breach and
       lets the group finish, so its evidence stands.
     - The whole packet takes 5 hours or less.
     - A test whose time rises by more than 25% from one sub-phase to the next goes in that
       PR's decision table.
     - The public-route tests that take minutes are marked `slow`.

**4c disposition (2026-10-07):** Stephen accepted 4c as complete, with the boundary review's Blocking finding
routed to Phase 5 prep (option A of the 4c handback).
- **Subject.** `e5179b57811f74346707a4fe5fe7c407772cb3dc`, main after #338. It includes #331's split of the
  SPEC-02 refusals test and six platform PRs merged after the last SPEC certification: #313, #322, #324, #325,
  #333 and #341.
- **Assembled selection.**
  - **Scope.** 310 nodes in 64 groups, as Stephen accepted on 2026-10-06: the Phase 0 STORE packet (06s §12,
    69 nodes), the Phase 1–4 packets (125) and the CI `contract-and-session-currency` list with
    `test_schema_registry.py` (116).
  - **Grouping.** A test that took 15 minutes or more runs alone. Other integration tests run in groups of at
    most five tests and 30 minutes. Light unit and contract files run whole.
  - **Result.** It ran from 02:00 on 2026-10-07 on 8 workers. Every node reconciled once against its JUnit
    record: 309 passed, and 1 was the documented skip (the network probe
    `test_neurips2024_exact_public_registration`). Nothing failed or errored, nothing was cut off, no run
    needed the environment retry, and the tree was clean afterwards.
  - **STORE pre-check.** At the same SHA the evening before, it passed 69/69. #320 fixed the 2026-10-02
    failures in `test_current_binding.py` and `test_store_binding_service.py`.
- **Budget: failed.**
  - 13 groups ran over 60 minutes, and the packet took 5h00m58s.
  - The worst was the complete SPEC-02 path at 166.6 minutes, against 54.0 in #331. Summed test time was
    39.7 h, against 14.8 h for the same tests in #331.
  - The STORE tests ran 2.4 times as long as the pre-check at the same SHA, so machine conditions and the
    platform PRs were confounded.
  - **A/B (2026-10-07, 07:52).** The public SPEC-01 path test ran at #331's certified `5d2a259c` and at
    `e5179b57` side by side, under the same load: 356.0 s and 356.7 s. The platform PRs did not slow the
    route. The breach was machine conditions during the window, whose source was not established, so the
    tests' cost is unchanged. Before a certification window, the machine is checked for other heavy jobs.
- **Boundary review.** A fresh-context Claude Code session reviewed the SHA in its own detached worktree, from
  `reviews/06s-phase4c-boundary-review-brief-2026-10-06.md`. Its report is
  `reviews/06s-phase4c-boundary-review-e5179b57-2026-10-07.md`. It found no authority, owner or paid-gate
  bypass, no durable corruption or mispublication, and no replay divergence. Verdict: FAIL on one Blocking
  finding. Stephen's dispositions:

  | ID | Finding | Disposition |
  |---|---|---|
  | B-1 | The committed foundation names only the live store. `store init` refuses another root, and the SPEC CLI refuses a store the foundation does not name, so Phase 5 cannot create or address its fresh store. The re-pin is governed configuration, so the bound SHA cannot be `e5179b57`. The origin-witness digest must be pinned before `store init` writes it. Verified by reading `foundation.yaml`, `cli.py`, `config.py` and `identity.py` at the SHA. | Routed to Phase 5 prep: one fresh store, created once by an owner-authorized procedure. Step 1 binds the post-prep SHA after a delta assurance (06s Phase 5, 2026-10-07). |
  | M-1 | Under #341, every Phase 5 invocation must run from one non-linked checkout outside the agent worktree directories, kept clean at the bound head. The foundation's `code_roots` lists agent worktrees. | Phase 5 prep: choose and freeze that checkout. |
  | M-2 | The SOURCE registration's manifest copies its production references from the caller's intent, and nothing verifies them. | Phase 5 prep: derive them from the ledger and verify them, as for the operator records. A code change in its own certified PR. |
  | m-1 | The SPEC-02 aliases (`return_spec_02`, `review_spec_02`) are not exposed, and no decision covered that. | Declined: the drop is confirmed, as 4a′ did for SPEC-01. |
  | m-2 | The SPEC-02 approval binds the Spike plan by content, not by reference. | Known limit. |
  | m-3 | `correct_spec_01_source` lacks project-use's governing-review pre-check, so it can stall. It fails closed, off the PARK path. | Known limit. |
  | m-4 | An admission refusal of a time-free effect repeats for the same actor and grant. | Phase 5 runbook note: retry under a new grant. |
  | i-1 | `spec_result.py`'s docstring says "the owner's use authority". | Wording fix at a later touch. |

**Phase 5 prep design decisions (2026-10-07):** Stephen reviewed the prep design pass
(`implementation/06s-phase5-prep-design-pass-2026-10-07.md`, merged in #346 at `3559251f`) and accepted every
recommendation, P5-1 to P5-12, "unless or until we find another blocker".
- **The measurement.** Every probe ran the genuine CLI from a non-linked scratch clone at `b0cda615`, with no
  foundation monkeypatch.
  - The witness digest cannot be pinned blind. Init draws a random store nonce, and the witness pins the
    identity of the stage folder init creates.
  - Reserving the witness and stage, pinning the reserved digest, and then running the unchanged `store init`
    succeeds.
  - A freshly initialized store then has no public path to its first binding. `spec status` refuses, and
    `repair-binding` needs a cleared restore transaction (`binding_service.py:862`). `advance-binding` needs a
    predecessor.
  - Every scratch SPEC store in the tests is bound by hand-written fixtures. This is **B-2**, a Blocking gap
    beyond B-1.
- **Decisions.**
  1. **P5-1, the reservation (D5 exception granted).** Add `ars store reserve`. It runs init's existing code to
     its `after-identity` point and stops. It takes the origin-authority root explicitly and prints the exact
     foundation fields, with the pre-init tail `(0, "0"*64)`. The re-pin commit then merges, and the unchanged
     `store init` consumes the reservation under the pin.
  2. **P5-2, the foundation.** The re-pin replaces the live store. The live store stays historical evidence, and
     a later read uses a pre-re-pin checkout.
     - The re-pin rewrites the expected values of `test_foundation_origin_witness_contract.py` (marked
       `live_store`).
     - The frozen SCALE packages, which record the live foundation as current, stay unchanged. No gate compares
       them with the committed foundation.
  3. **P5-3, the first binding (D5 exception granted).** One new owner action binds a never-bound,
     freshly initialized store. Its admission requires:
     - no binding pointer and no restore transaction;
     - a store manifest equal to the origin witness's initial manifest;
     - the candidate to be the manifest's single code root.

     It publishes a 1.0.0-shaped root binding. `current_binding` accepts that initial root, with the
     witness's initial manifest standing in for the restore join. The contrived restore (option A) and dropping
     the staleness requirement (option B2) were rejected.
  4. **P5-4, step 6.** The 1.0.0 root admits only the exact bound SHA, so step 6 replays from the frozen checkout
     at that SHA after the docs PR merges. That PR is not pulled into the checkout, and no advance path from
     the initial root is built.
  5. **P5-5, the durable checkout (M-1).** A dedicated non-linked clone, `C:/Users/steph/TDL-ARS-G6-Checkout`,
     cloned from GitHub with local `main` at the bound SHA. It is the foundation's only code root and its schema
     root. No worktree is added to it and nothing is pulled into it after step 1.
  6. **P5-6, the roots and project.** Control root `C:/Users/steph/TDL-ARS-G6-Control` and origin authority
     `C:/Users/steph/TDL-ARS-G6-Origin-Authority`, both new. The project stays
     `prj_01978abc-1000-7000-8000-000000001000`.
  7. **P5-7, SOURCE provenance (M-2).** The SOURCE registration cites a separate SOURCE Task with a running
     Attempt. The route refuses, before any write, unless:
     - the named Task names no registered Candidate;
     - it has one started, running Attempt and is unamended since that Attempt's dispatch;
     - the intent's dispatch, Attempt, context-packet, code-commit and environment fields equal the ledger's.

     `spec-source-intent` stays 1.0.0. Producer profile, branch, worktree and accepted scope stay caller
     strings, a known limit.
  8. **P5-8, SPEC-01's rule (D5 exception granted for W11 admission).** Admission evaluates the rubric's declared
     algorithm. A registered legacy algorithm yields:
     - PROMOTE when Axis 1 passes, Axis 2 + Axis 3 ≥ 4 and neither is 0;
     - KILL when Axis 1 fails;
     - PARK otherwise.

     The fixture algorithm keeps today's behaviour. The route's blanket PROMOTE refusal narrows to bars whose
     algorithm admission does not evaluate.
  9. **P5-9, the Assay bar.** SPEC-01's content replaces both committed Assay authority files. The current
     fixture bytes move to test fixtures, and the route tests keep their behaviour. A dedicated non-owner actor
     signs the content: author, reviewer and acceptor are three identities, and the fresh run's actor plan is a
     prep output.
  10. **P5-10, `adopt_default`.** After PROMOTE, the SPEC route permits only `retain_experimental_benchmark`.
  11. **P5-11, the census first.** Before any PR is cut, a disposable driver walks the live sequence through the
      public CLI only and records every refusal. This includes grant activation and Task/Attempt seeding, which
      tests replace with adapters. Its report fixes the PR list.
  12. **P5-12, the delta assurance.** The full 4c selection plus the new nodes runs on the post-prep SHA, through
      the 4c runner with a new node list. P-058's window and budget apply, and a recorded machine check comes
      before each window. Each prep PR is certified with its own packet plus the SPEC-01 public path as canary.
- **Live sequence.** Design pass §4, authorization points A1 to A7. The re-pin merges after the live
  reservation and before `store init`.
- **Migration consequence.** None yet. No code, schema or store changes until the construction PRs.

**Census result (2026-10-07):** the C0 census (`implementation/06s-phase5-prep-census-2026-10-07.md`) ran on a
scratch store created by the P5-1 procedure.
- **Result.** 22 of 22 commands passed through the public `ars command submit`: grant activation, the whole Task
  and Attempt lifecycle, Attempt completion and evidence registration.
- **One new gap, B-3 (Material, not blocking).** The owner's administration decision that `ActivateAuthorityGrant`
  verifies has no public writer; only internal code places it in the control object store.
- **B-3 under Stephen's standing instruction** ("go with the recommended path … unless or until we find another
  blocker"): PR-G adds `ars authority activate-grant`. It derives and writes the owner decision and submits the
  activation, with admission unchanged.
- **The construction PR list is now fixed:**
  - PR-A: reserve and the first binding;
  - PR-B: SOURCE provenance;
  - PR-C: the Assay bar and SPEC-01's rule;
  - PR-D: `adopt_default`;
  - PR-G: the grant activation command;
  - the runbook docs;
  - PR-F: the re-pin, after the live reservation.

**PR-A construction decisions (2026-10-07):** PR-A (`pipe/g6-store-reserve-first-binding`) implements P5-1 and P5-3.
- **The first binding uses the repair family, as P5-3 says.**
  - **What it is:** `RepairStoreBinding` 1.1.0 (intent and command schemas) adds the owner action
    `bind-initialized-store`, with empty stale evidence. The repair action keeps its 1.0.0 meaning.
  - **What is new:** one object schema, `StoreBindingInitial` 1.0.0, which pins the witness's initial manifest
    in place of a restore.
  - **What is unchanged:** the event, `StoreBindingRepaired`, whose `prior_manifest_sha256` is the initial
    manifest; the receipt; replay; and every record that cites a binding event.
  - **Why not a new event type:** a first attempt with a new event type was reverted. Ten closed SPEC record
    schemas fix `governed_code_subject.event_type` to `StoreBindingRepaired` or `StoreBindingAdvanced`, so a new
    event type would have forced new versions of all ten (D3).
- **Protected-surface re-acceptance** (needs Stephen's acceptance at PR review, as P-059 did). The 06h census's
  runtime-binding digest moves from `70a6bf2f…` to
  `f359855bf5e760c3336dd201dd69e765d5bd0a91836dedcb5ddfecaeea0470d7`. The row count stays 261: only the active
  `RepairStoreBinding` command row moves from 1.0.0 to 1.1.0. No append site is added.
- **The binding test.** `test_fresh_store_public_procedure.py` (slow) runs the genuine `ars` CLI as a
  subprocess from a non-linked scratch clone, through reserve, re-pin, `store init`, the first binding and
  `spec status`, with no fixture on any seam. It also checks the refusals:
  - `store init` before the re-pin;
  - `spec status` before the binding;
  - a second first binding;
  - a restore appearing under an initial binding;
  - a reserve from a checkout with linked worktrees;
  - the initial action on a restored store.

**P5-7 amended (Stephen, 2026-10-07): one Task spans SOURCE to closure.**
- **The finding.** Building PR-B showed that admission never checks a Task's `portfolio_refs`. `source_ids`
  derives the Candidate ID from the project, the SOURCE intent's `production.task_id`, the action and the source
  key, so it is known before the Candidate exists.
- **The decision.** Stephen accepted the lighter design, "with the reduced test churn".
  - The SPEC-01 Task names the Candidate's derived ID, is created, and its Attempt started, before
    `observe_source`.
  - The SOURCE registration's production references are verified against that Task's running Attempt.
  - There is no separate SOURCE Task.
  - It replaces P5-7's separate SOURCE Task and its "names no registered Candidate" rule.
- **What the route refuses**, before any write, for `observe_source` and `correct_spec_01_source`. It refuses
  unless all of these hold:
  - `production.task_id` names a Task whose definition names no registered Candidate other than the one this
    observation derives;
  - the Task has exactly one started Attempt, and that Attempt is running;
  - the Task is unamended since that Attempt's dispatch;
  - the intent's dispatch, Attempt, context-packet, code-commit and environment fields equal the ledger's.
- **What does not change:** `spec-source-intent` stays 1.0.0. Producer profile, branch, worktree and accepted
  scope stay caller strings, a known limit.
- **Phase 5 step 3:** create the SPEC-01 Task naming the derived Candidate ID and start its Attempt before
  `observe_source`. Keep it running until the operator return is registered.

**Prep construction complete (2026-10-15).** Every construction PR is merged. Main is `bbdcb068` (#352), and its
tree is byte-identical to the certified PR-C head `b09813e6` (tree `6ec37ed1…`).
- **Merged.**

  | PR | Scope | Merged as | Head |
  |---|---|---|---|
  | #348 | PR-A: `store reserve` and the first binding (P5-1, P5-3) | `e0bf729b` | `b25fa64b` |
  | #349 | PR-B: SOURCE provenance (M-2, P5-7 amended) | `29e56afe` | `28e89dc4` |
  | #350 | PR-D: `adopt_default` (P5-10) | `570c66f3` | `8061a9f7` |
  | #351 | PR-G: `ars authority activate-grant` (B-3) | `968746ce` | `dcc035bf` |
  | #352 | PR-C: SPEC-01's bar and rule (P5-8, P5-9) | `bbdcb068` | `b09813e6` |
  | #353 | the Phase 5 runbook | `15776b9e` | `f790f84f` |

  Stephen merged #348 to #351 on 2026-10-07, after review. #352 followed once its review fix was in.
- **What changed during review, by PR.**
  - **PR-B.**
    - CI found four regressions; the full local runs found three more:
      - an import cycle (`spec_source` imported the replay layer that imports it);
      - three `test_spec_assay` tests: a Task-amendment helper had dropped the seeded Task's `portfolio_refs`,
        and the "no Task naming the Candidate" refusal had become unreachable (it moved to its own test);
      - three `test_spec_source` tests that advanced SOURCE without seeding the Task.
    - Fixed in `98fcebea`. `1966f62d` then kept the correction's prior-registration refusal ahead of the new
      check.
    - CodeRabbit's finding (`28e89dc4`): every link of a SOURCE lineage must cite the production Task. A
      correction under one Task can no longer carry another Task's observation, or its Candidate, into this
      Task.
  - **PR-C.**
    - "Neither score zero" is held at function level (`ae7f62a1`). On the bounded [0,3] axes the clause changes
      no admissible outcome, and mutation control c2 showed it.
    - CodeRabbit's finding (`b09813e6`): the decide-time PROMOTE guard is decided on the frozen rubric the
      scorecard binds, using admission's own predicate (ID, version and descriptor hash). The scorecard's rule
      reference carries no version.
  - **PR-G.** CodeRabbit's two findings (`dcc035bf`):
    - `authority` refusals go through the CLI's error handler (exit 1);
    - grant-scope validation and the decision's time checks now run before the owner decision is written. A
      request that fails either check is refused with nothing written, where before admission refused it only
      after the decision was stored;
    - a changed request under a used grant ID is refused with "needs a new authority_grant_id" (the m-4 rule).
      No rollback was added.
- **Mutation controls.** All hold, each re-checked for the intended failure reason:
  - PR-A: c1 to c5, at `515b3766`; the merged head adds only this record;
  - PR-B: b1 to b4, at `28e89dc4`;
  - PR-C: c1 to c4, at `b09813e6`;
  - PR-D: d1, at `8061a9f7`;
  - PR-G: g1 to g4, at `dcc035bf`.
- **Certification, and how it departed from P5-12.**
  - **The departure.** P5-12 certified each prep PR with its own packet. Four PRs merged before their packets
    ran, so one integrated packet replaced the five. It ran at `b09813e6`, which equals main `bbdcb068`.
  - **The selection, 607 nodes.** It is the union of the five per-PR selections, rebuilt from each PR's diff,
    plus every test file the prep changed and the discovery architecture tests.
    - The diff rebuild was needed because PR-B's hand-picked selection had held none of the tests CI later
      found failing.
  - **The result.**
    - 606 passed and 1 skipped, the opt-in network probe `test_neurips2024_exact_public_registration`.
    - The JUnit reconciliation found every node once. The tree was clean after.
  - **Runs.**
    - 2026-10-08 02:10–04:04: stopped by Stephen.
    - 2026-10-15 07:53–08:36: resumed.
    - 08:38–09:02, with `--now` by Stephen's decision: a re-run of the 8 groups the stop had left with
      interrupted results.
    - The machine check was recorded before the 2026-10-15 run.
  - **Budget.** No run exceeded the 5-hour packet budget. One group exceeded 60 minutes:
    `p14-spec_spike_outcome-2`, at 69.7 min on 2026-10-08. Its test passed.
  - **Evidence.** `C:/Users/steph/.codex/tmp/g6-p5prep/prep-b09813e6/`.
- **Not yet done: the delta assurance (P5-12, KAN-110 exit).**
  - **The selection.** 253 of the 4c selection's 310 nodes already passed at this tree in the integrated packet.
    57 did not run: mostly WP6.4 session-exchange contracts, 06i stage-A contracts and workflow-liveness
    tools tests.
  - **The fresh-context review** of `e5179b57`..post-prep has not run.
- **Decisions (Stephen, 2026-10-15).**
  1. **PR-B's naming rule is confirmed.** It refines the amended P5-7. That wording said the Task names "no
     registered Candidate other than the one this observation derives", but a revisit observation under the same
     Task derives its own Candidate. So the rule is: the SPEC-01 Task may name only Candidates that SOURCE
     observations citing this Task derive, and each lineage stays under this Task.
  2. **Delta assurance selection, option A.** The integrated packet counts toward the delta assurance's
     selection. The delta assurance re-runs only the 57 nodes of the 4c selection that the packet did not run.
     - It runs on M1, the post-prep main SHA, with JUnit reconciliation and a recorded machine check.
     - All 57 node IDs were confirmed to exist at `bbdcb068`.
     - The fresh-context review of `e5179b57..M1` is still required.
- **Outside prep, recorded for the Phase 5 thread.**
  - **The CI suite lane is red on main.** The 2026-10-07 nightly had 135 failures outside the 3-entry
    known-failures list. About 87 are the S-014 physical preflight in the release-publication tests, which pass
    locally (CI-runner-specific). They are not prep regressions: every PR's failures were a subset of the
    nightly's, except PR-B's.
  - **`test_observation_log_lint.py::test_reachability_reads_only_open_entries_and_skips_carried_hashes` is
    flaky.** It fails when a random 9-character hash prefix is all digits, about 1.5% of runs.

**Delta assurance: the selection and the network probe passed on M1 (2026-10-15).** This is P5-12 under option
A, KAN-110's exit. Recorded at Stephen's instruction. The fresh-context review is still running, so KAN-110 stays
open.
- **M1:** `100730e0319ff975116fb1e18eb897f46d81a627`, main after #354, recorded before the first write.
  - Beyond `bbdcb068` it changes four Markdown files and nothing else, so the selection stands.
  - It contains `bbdcb068` and `e5179b57`.
- **The selection.**
  - The handoff's `comm` recipe over the 4c and prep collect files re-derives the appendix's 57 lines byte for
    byte.
  - All 57 were collected at M1 (`57 tests collected`), an exact match with the appendix.
- **The run.**
  - **Setup.** The runner was `certify_delta.py`, a copy of `certify_prep.py` whose only change is its output
    root. It ran in the linked worktree `C:/Users/steph/TDL-g6-p5` at M1, which was clean before and after.
  - **The window.** Stephen authorized `--now`, waiving the 02:00–11:00 window. A runner already waiting for
    that window was stopped before any group ran.
  - **Execution.** The run began 13:54:14 and took 20 s on 8 workers, in 7 groups. Every group exited 0 and
    executed all its nodes.
  - **Result:** 57 passed.
    - The JUnit reconciliation found 57 expected and 57 reported, none missing, unexpected or duplicated.
    - Nothing failed, errored or was skipped.
    - No group went over budget, nothing was cut off, no run needed the environment retry, and the tree was
      clean after.
- **Machine checks.**
  - 13:45, before the window: 95.8% idle.
  - At launch, by the runner: 84.4% idle, with one other agent session running.
- **The network probe (Stephen agreed, 2026-10-15).**
  - **Setup.** `test_spec_source.py::test_neurips2024_exact_public_registration` ran once with
    `ARS_SOURCE_NETWORK_PROOF=1`, at exact M1 (the worktree was detached to M1 for it). It made a read-only
    public Git fetch with no credentials, into a scratch store.
  - **Result:** 1 passed in 114 s.
    - `refs/tags/neurips2024` resolved to `145efcde673f1a1897eff250b77221d26c34c479`.
    - The source's SHA-256 was `3eea9174db28f4dd5bcf4e622709280f25fd6bfe0843ff1fc2e1d1559401f9df` and its size
      24,145,920 bytes.
  - **Why it matters.** This probe was the one skip in both the 4c selection and the integrated prep packet. It
    has now passed against the step 3 source.
- **Evidence.** All under `C:/Users/steph/.codex/tmp/g6-p5/`:
  - `delta-collect-100730e0.txt` (the node list);
  - `certify_delta.py` and `certify_delta.diff`;
  - `machine-check-prewindow-2026-10-15.json`;
  - `delta-100730e0/`: `results.json`, the per-group JUnit and logs, `machine-check.json` and
    `NOW-AUTHORIZATION.txt`;
  - `probe-100730e0/`: `probe.xml`, `probe.log` and `AUTHORIZATION.txt`.
- **Still open: the fresh-context review of `e5179b57..M1`.**
  - The brief is `reviews/06s-phase5-delta-review-brief-2026-10-15.md`. Stephen dispatched the reviewer, and the
    review is in progress.
  - It must confirm closed:
    - B-1, B-2 and B-3;
    - M-1 and M-2;
    - the SPEC-01 rule and bar.
  - KAN-110 closes when Stephen records the review's disposition. Until then there is no successor binding and
    no live step (runbook §0).

**Delta assurance complete: the review passed, the dispositions, and KAN-110's exit (Stephen, 2026-10-15).**
- **The review.**
  - **Verdict:** PASS at `100730e0` against `e5179b57`, with no Blocking finding.
  - **Who and how:** a fresh-context reviewer, working from the brief in a detached worktree at M1.
  - **The report:** `reviews/06s-phase5-delta-review-e5179b57-100730e0-2026-10-15.md` (source sha256
    `999b2800…`).
- **Closure.**
  - **B-1, B-2, B-3:** closed. B-1 is closed as a mechanism. The re-pin itself lands as PR-F, and L5 re-assures
    M2.
  - **The SPEC-01 rule and bar:** closed. The reviewer recomputed the truth table over the committed rubric:
    4,096 cases, 0 mismatches.
  - **M-1:** closed with residual m-2.
  - **M-2:** closed with residual m-1.
- **The executor's check.** Before this disposition, the executor confirmed both residuals at M1:
  - `spec_source.py`'s naming check does not require the Task to name the derived Candidate;
  - the runbook gave no location for operator files or for PR-F.
- **Dispositions (Stephen).**

  | ID | Finding | Disposition |
  |---|---|---|
  | m-1 (Minor) | The route does not require the SOURCE production Task to name the Candidate the observation derives, so "one Task spans SOURCE to closure" is held by procedure. The reviewer reproduced steps 1 and 2. No record is false. | **Known limit.** Runbook §4 step 4 gains a verify line: before `observe_source`, the Task's `portfolio_refs` include `source_ids(...)["candidate_id"]`. No code change, so no M3. |
  | m-2 (Minor) | The runbook fixed no location for operator-supplied files or for authoring PR-F. A file inside the durable checkout makes the L7 binding refuse. PR-F authored there breaks L6's fast-forward. All cases fail closed. | **Fixed before L3**, as runbook text (§3): every operator file lives in the run's evidence folder, outside the checkout; PR-F is authored in a worktree of the primary repository. |
  | i-1 (Info) | An admission refusal of `activate-grant` on grounds other than scope or time leaves an inert owner decision. | **Known limit**, already recorded in PR-G. |
  | i-2 (Info) | `activate-grant` takes the owner from the request and a `ControlBinding`: the local trust model of P-042. | **Declined:** no new bypass. |
  | i-3 (Info) | The 06h census runtime-binding digest moved to `f359855bf5e760c3336dd201dd69e765d5bd0a91836dedcb5ddfecaeea0470d7` (261 rows; `RepairStoreBinding` 1.0.0 → 1.1.0) without an explicit acceptance line. | **Accepted by Stephen (2026-10-15)**, as P-059 did for its pins. |
  | i-4 (Info) | No test writes a SPEC record, or runs backup or verify-restore, on an initial-root store. Two refusals are tested through a monkeypatch or the service rather than the CLI. | **Known limit.** Steps 3 and 5 are the first end-to-end exercise, so watch them. |
  | i-5 (Info) | The owner may resolve PARK or KILL against the mechanical result; admission gates only PROMOTE. | **Declined:** owner discretion, unchanged from 4c. |

- **Coverage: accepted as reported.** The reviewer declared these unexamined:
  - the evidence-scope content's rows (their methodological content was Stephen's PR-C review);
  - the delivery replan §3 to §5.0;
  - the PR descriptions of #348 to #352 beyond P-058's summary.
- **KAN-110's exit.**
  - **Recorded.** The delta assurance (P5-12) is complete: the 57-node selection, the network probe and the
    review all passed, and the dispositions above are recorded.
  - **Next:** A0, Stephen's decisions for the run (runbook §0.3).
  - **Still gated:** no live step runs without its own authorization. The successor binding waits for L7.

**A0: Stephen's decisions for the run (Stephen, 2026-10-15).** Runbook §0.3. These are decisions only: nothing
was executed, and no store, checkout or grant exists yet.
- **The owner actor.** Reuse `act_01978abc-1002-7000-8000-000000001002`. It was the live store's owner and the
  census owner, and P5-6 keeps the project ID, so one human keeps one owner identity.
- **The actor plan (runbook §1).** The bar author is fixed by #352. The other roles take 11 new UUIDv7 IDs, all
  distinct from each other, the owner and the author:

  | Role | Actor |
  |---|---|
  | Bar author | `act_01a1169f-019f-7fbb-b9f6-0246970f1d9a` |
  | Rubric observer | `act_01a14020-044d-7a2a-8f17-cb417f5a80a3` |
  | Scope observer | `act_01a14020-044f-7877-b62d-04221f9f6949` |
  | Bar review requester | `act_01a14020-0451-7b04-bed0-137bbfb8871b` |
  | Bar reviewer | `act_01a14020-0454-778d-9ee1-402fc21947b3` |
  | Bar proposer | `act_01a14020-0456-792c-8a1d-18855aae1f7b` |
  | Steward | `act_01a14020-0459-708d-ae88-bbbe336eae97` |
  | Producer (operator) | `act_01a14020-045b-7374-b432-b180a4e67a27` |
  | Outcome reviewer | `act_01a14020-045e-71e9-9c6a-e5d8409cbc2d` |
  | Decision proposer | `act_01a14020-0460-7fd4-8c59-cc3e1a70d874` |
  | Task reviewer | `act_01a14020-0462-70d7-9c6c-b563450976a0` |
  | Project-use reviewer | `act_01a14020-0465-7cef-8e72-d4f66f4e2f7a` |

- **Who runs the Task and Attempt commands (runbook §4 step 4).** The owner, as in the census (22/22 through the
  public CLI).
  - The route requires only that the Task reviewer be independent of the Attempt's producers: the Attempt
    stream's actors, the lease holder and the SubmitForReview submitter (`spec_task.py:267-348`).
  - The owner already submits for review, so this adds no collapse.
- **The authority bootstrap (runbook §2).** `ars://core/authority-bootstrap-input` 1.0.0, validated against the
  input, manifest and grant 1.1.0 schemas.
  - **The owner and project:** the owner above, on project `prj_01978abc-1000-7000-8000-000000001000`.
  - **The root grant:** `agr_01a14020-046a-76f3-a823-20f007c71cd9`, `RevokeAuthorityGrant` on the publication
    grant, R2, with no expiry.
  - **The publication grant:** `agr_01a14020-0468-7fb3-b8a7-d91c7fb23217`, `PublishReleaseGateDecision` on
    `rgd_01a14020-046d-7293-ab83-25a7975fb5db`, R2, expiring `2026-12-31T23:59:59Z`.
  - **Effective:** both grants from `2026-10-15T00:00:00Z`.
  - **`approved_bootstrap_sha256`:**
    `a68cfbed4bb83d5f7bba9d674dcce19e111adb26c8023d0055d49192e487138b`.
  - **The file:** sha256 `3248306b25c2c71f59a1c9a52dfef9aa1f7f5d66a9e9838c45910f0a7118e0ae`, kept with the run's
    evidence in `C:/Users/steph/.codex/tmp/g6-p5/a0/bootstrap.json`, outside the durable checkout. The actor plan
    is in `actor-plan.json` beside it.
- **D6: the paid-run subset and cost ceiling (P-056).**
  - **The subset: SPEC-01 only.** One fresh SPEC-01 Assay of Damrich–Berens–Kobak at `neurips2024`. SPEC-02 runs
    0 of the 126 primary configurations and 0 of the 42 reruns under this approval.
  - **SPEC-02 later.** It still needs a valid OR-013 PROMOTE and a separate `spec_02_live_run_approval`.
    - If that arises, the recommendation is the full frozen 126/42, within the contract's own ceiling: 7,200 s,
      4 workers, 12,288 MB memory, 5,120 MB storage, no network. The contract fixes seven methods for every
      fixture cell.
  - **The cost ceiling.**
    - **Spend:** no metered provider or API spend by ARS (£0). Both contracts already stop on provider use,
      provider launch or credential access. No cloud compute.
    - **Network:** public, read-only paper and Git access only. No credentials and no survey data.
    - **Sessions:** one operator session for the SPEC-01 return, up to 4 h wall time. One session each for the
      bar reviewer, the outcome reviewer, the Task reviewer and the project-use reviewer, up to 1 h each. All
      run on the owner's existing agent plan.
    - **On defect:** a production defect stops the run, with no automatic rerun.
- **Open, for L5's scope (to decide before L4).** Since M1, main has taken #356 to #362. Several change more than
  documentation:
  - `research_system/evals/executors/release_tranche.py`;
  - `test_fresh_store_public_procedure.py` and `test_store.py`;
  - `.claude/hooks/commit_state_guard.py` and `.claude/settings.json`;
  - the CI workflows and `tools/`.

  PR-F merges onto that main. So M2 is M1 plus #356 to #362 plus PR-F, not "M1 plus PR-F" as runbook L5 assumed.
  L5's selection and review must cover `100730e0..M2`.
- **Next:** A1, the durable checkout (runbook §3 L1). It needs Stephen's own authorization.

**Live steps A1 to A4, and the L5 scope (Stephen, 2026-10-15/16).** Each step was authorized by Stephen on its
own, run alone, and verified from durable state before the next.
- **A1 to A3** were each one exact script. Their scripts, logs and authorization notes are in
  `C:/Users/steph/.codex/tmp/g6-p5/a1/` to `a3/`.
- **A4** was the push of `a40b3f01` and the opening of PR #365, under its own authorization. `a4/` holds that note
  and the pre-push procedure-test log. This sentence was corrected on 2026-10-21 (final review m-6).
- **A1, the durable checkout (L1).**
  - **What ran:** `run-a1.sh` (sha256 `69ace3fc…`), at 23:53Z on 2026-10-15. It cloned
    `C:/Users/steph/TDL-ARS-G6-Checkout` from GitHub, set `main` to M1 `100730e0` and ran `uv sync --locked`.
  - **Verified:** `.git` is a directory; there is one worktree; the status is empty, untracked files included;
    HEAD is `main` at M1; `research_system` imports from the checkout. A fresh-shell re-check agreed.
- **A2, the origin-authority root (L2).**
  - **What ran:** `run-a2.sh` (sha256 `4b32e5d3…`), which created the empty
    `C:/Users/steph/TDL-ARS-G6-Origin-Authority`.
  - **Verified:** it is empty, the control root does not exist, and the checkout is clean at M1.
- **A3, the reservation (L3).**
  - **What ran:** `run-a3.sh` (sha256 `3cc1afe7…`), at 23:55Z. It ran `ars store reserve` from the evidence
    folder, with the A0 bootstrap (`3248306b…`) and `--foundation-output` outside the checkout (delta review m-2).
  - **Result:** status `reserved`.
    - **Store identity:** `5e3b95a956a8a416accd697f250088b5c8723924eb68544f01064ede6eb18d69`.
    - **Witness:** `store-origins\sha256-200ee8f2ddb6ee387d208d57b8c427bb961ec3d7d0e021f53356fe0055095996.json`,
      sha256 `1a7aa957917f20d537fbc99e23e23fc094f60e94906d80e4a2250577d7ffe7c4`.
    - **On disk:** one stage, `.TDL-ARS-G6-Control.authority-stage-a68cfbed4bb8-8abc9894`, and no store.
    - **The foundation:** file sha256 `0bf20c381ccb821d30f4950bf06178bfa8381cb8821092f513b1b82a4a0897e0`.
  - **Verified:** the printed digest equals the witness bytes, and the foundation file equals the printed
    foundation. The checkout stayed clean at M1. A fresh-shell re-check agreed.
- **A4, PR-F (L4).**
  - **What was authored:** in the primary-repo worktree `C:/Users/steph/TDL-g6-pr-f`, branch
    `pipe/g6-phase5-repin`, commit `a40b3f01`, cut from main `0f037415`. It holds the foundation, byte for
    byte, and the `live_store` contract test with the new pins.
  - **Verified before pushing:**
    - hooks and the contract gates pass;
    - `test_fresh_store_public_procedure.py` passes 3/3 at `a40b3f01`;
    - the contract test's value assertions pass. Its load fails until L6 creates the control root ("approved
      project binding path is unavailable").
  - **What A4 did:** pushed the branch and opened [PR #365](https://github.com/ZK-Theory/TDL/pull/365). Stephen
    reviews and merges it, which gives M2.
- **Checked and harmless.** The WP6.4 `tda-scale` packs record the old foundation as `current_exact`. That record
  is pinned at commit `03107b48`, and no code or test compares it with the live file.
- **The L5 scope (Stephen, 2026-10-16).** The delta assurance on M2 covers `100730e0..M2`.
  - **The selection, JUnit-reconciled:**
    - `test_fresh_store_public_procedure.py`;
    - the Phase 0 STORE packet (06s §12);
    - `unit/test_store.py`;
    - the five test files that exercise `release_tranche`: `test_gate5_release_tranche.py`,
      `test_gate5_release_tranche_fixture_corpus.py`, `test_wp64_real_a8_evidence.py`,
      `test_context_packet_lifecycle.py` and `unit/test_coverage.py`;
    - the test files of any further non-docs change that lands before M2.
  - **The window:** 02:00–11:00, unless Stephen says `--now`.
  - **A review:** a short fresh-context review of the non-docs diff. PR-F is the executor's construction, and the
    review also confirms that the SYS tooling, hook and CI changes do not touch the route's runtime.
  - **The `live_store` foundation contract test** moves to L6's verification.
- **Next:** Stephen's review and merge of #365, then A5 (L5) on M2. It needs his authorization.

**L5 review: PASS, and M2 (Stephen, 2026-10-16).**
- **M2:** `4d867d85574dcf90300f059ab1fd52324be3c85a`, main after #365 (PR-F). The foundation on main is the A3
  file, byte for byte (`0bf20c38…`). Nothing else non-docs landed after PR-F's base (#363 and #366 are docs).
- **The review.**
  - **Verdict:** PASS at `4d867d85` against `100730e0`, with no Blocking or Material finding.
  - **Who and how:** a fresh-context reviewer, working from the brief, in a detached worktree at M2.
  - **The report:** `reviews/06s-phase5-l5-review-100730e0-4d867d85-2026-10-16.md` (source sha256 `5057bed8…`).
    The brief is beside it.
  - **What it established:**
    - the 1.0.0 foundation is accepted by every consumer L6 and L7 use: `store init`,
      `ApprovedProjectBinding.load`, `repair-binding --owner_action bind-initialized-store` and
      `load_current_binding`. The reviewer checked this in code, and with a scratch probe that ran reserve,
      re-pin, init, bind and load on a clone of M2 (passed, 79 s);
    - no change outside `research_system/` and `.research-system/` reaches the `ars` runtime.
- **Dispositions (Stephen: record only).**

  | ID | Finding | Disposition |
  |---|---|---|
  | F1 (Minor) | The #360 primary-checkout guard (`.claude/hooks/commit_state_guard.py`) treats any non-linked checkout on `main` as primary. So in a Claude Code session it would deny L6's fast-forward if that were written as `reset --hard`, `checkout`, `switch` or `rebase`. `merge --ff-only` passes. Fails closed. | **Recorded in the runbook.** L6's fast-forward is `git -C <checkout> fetch origin`, then `git -C <checkout> merge --ff-only 4d867d85574dcf90300f059ab1fd52324be3c85a`. The hook is unchanged before L6, and its wider-than-named scope is logged as an observation. |
  | F2 (Minor) | #364 turned a missing deny-list-ACE precondition in `unit/test_store.py` into a skip, and the runner counts executed tests per batch. On this machine the test still runs (2 passed, 0 skipped). | **At L5 reconciliation:** confirm both `test_windows_delete_protected_anchor_fences_a_directory_that_denies_listing` nodes are passed, not skipped. Follow-up: skip only on CI. |
  | F3 (Info) | The harness PostToolUse recorder writes `.git/tdl-session-branches/<id>` in any checkout a Claude Code session reads with git, including the durable checkout. Git reports nothing inside `.git`, and the checkout's status stays empty. | **Recorded as harmless hook state.** It is not a write to the worktree. |
  | F4 (Info) | The genuine-CLI procedure test never calls `ApprovedProjectBinding.load` on the re-pinned foundation. | **After Phase 5**, fold that assertion into the test. On the live file, the `live_store` contract test covers it at L6. |
  | F5 (Info) | The WP6.4 `tda-scale` packs' `current_foundation` record is stale. | **Confirmed harmless:** no code or test compares it with the live file. |

- **Still open for A5:** the 327-node selection runs at 02:00 on 2026-10-17 (recorded as partial at Stephen's
  decision). When it ends, its JUnit is reconciled (including F2's check) and Stephen records it.
- **Next:** A6, the fast-forward and `store init`. It needs its own authorization.

**L5 delta assurance on M2: passed; A5 closed (Stephen, 2026-10-17).**
- **The subject:** M2, `4d867d85574dcf90300f059ab1fd52324be3c85a`.
- **The run.**
  - **Where:** the worktree `C:/Users/steph/TDL-g6-p5`, detached at M2, clean before and after.
  - **The runner:** the committed `tools/certify_packet.py` (#362), with `--base 100730e0` and
    `--partial-reason` citing Stephen's L5 scope.
  - **Timing:** from 02:00:00 on 2026-10-17, 23 minutes on 8 workers.
  - **The selection:** 327 nodes in 72 groups, selection hash `60ccf9d7…`.
- **The result: 327 passed.**
  - The JUnit reconciliation (independent of the runner's summary) found 327 expected and 327 reported, none
    missing, unexpected or duplicated. Nothing failed, errored or was skipped.
  - All 72 groups exited 0. No run needed the environment retry, nothing was cut off and no group went over budget.
    The slowest group was `store_binding_service-1`, at 23.0 minutes.
- **F2 confirmed.** Both `test_windows_delete_protected_anchor_fences_a_directory_that_denies_listing` nodes, the
  `registered-root` and `registered-member` cases, **passed**, not skipped.
- **The partial selection.** The runner's diff rule required 3,579 nodes, 3,279 more than this selection. The run
  records Stephen's narrower scope as partial. PR-F's PR-lane affected suite had passed on CI (`select` plus
  `suite` 1 to 8).
- **The machine check.** It was recorded before the window, on 2026-10-16 at 08:07 (81.3% idle). The committed
  runner records cleanliness at launch and at window start, but no machine check of its own.
- **Evidence:** `C:/Users/steph/.codex/tmp/g6-p5/l5/out/4d867d85-60ccf9d7/`. `results.json` (sha256 `4384605c…`)
  is there with the per-group JUnit and logs; `l5-collect-4d867d85.txt` is beside it.
- **A5 is closed.** With the L5 review's PASS above, the delta assurance on M2 is complete.
- **Next:** A6 (L6), the durable checkout's fast-forward to M2 with `fetch` then `merge --ff-only`, then
  `store init`. It needs its own authorization.

**A6 (L6): the checkout at M2, and the fresh store initialized (Stephen, 2026-10-17).**
- **What ran:** `run-a6.sh` (sha256 `dbcc32b4…`), from 02:02Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/a6/`: the script, `a6.log`, `init-output.json` (`bf670b77…`),
  `foundation-contract.xml` and the authorization note.
- **The fast-forward.** `git -C <checkout> fetch origin`, then `merge --ff-only 4d867d85…`: the durable checkout's
  only update in Phase 5.
  - **Verified:** `main` at M2, the status empty with untracked files included, one worktree, and the foundation
    file `0bf20c38…`.
  - **The lock:** `uv.lock` and `pyproject.toml` are unchanged from M1 to M2, so no sync ran.
- **`store init`.** It ran from the evidence folder with the A0 bootstrap, and consumed the A3 reservation under the
  PR-F pin.
  - **Store identity:** `5e3b95a956a8a416accd697f250088b5c8723924eb68544f01064ede6eb18d69`.
  - **Origin witness:** `1a7aa957917f20d537fbc99e23e23fc094f60e94906d80e4a2250577d7ffe7c4`.
  - **Bootstrap manifest:** `a68cfbed4bb83d5f7bba9d674dcce19e111adb26c8023d0055d49192e487138b`.
  - **On disk:** the control root `C:/Users/steph/TDL-ARS-G6-Control` holds `events`, `manifests`, `objects`,
    `receipts`, `runtime` and `snapshots`. No stage is left.
- **Verified (L6).**
  - The identity and witness digest equal the pins, and so does the bootstrap digest.
  - `ApprovedProjectBinding` loads from the checkout's foundation, with control root `TDL-ARS-G6-Control`.
  - The `live_store` foundation contract test passed, 1/1 (moved to L6 by the L5 scope).
  - The checkout is clean at M2.
- **How the contract test ran.** The script stopped at that test. The checkout's venv was synced at A1 without dev
  extras and has no pytest, and that stop also skipped the script's closing cleanliness check. The test was
  then run from the worktree `TDL-g6-p5` at M2, whose foundation and test file are byte-identical to the
  checkout's. Its load resolves the checkout's schema root and the new control root. A separate check confirmed
  the checkout clean at M2. Nothing was installed into the checkout.
- **Next:** A7 (L7, step 1), the first binding through `ars store repair-binding` with the
  `bind-initialized-store` action, then `spec status`. It needs its own authorization.

**A7 (L7): the first binding is published, and Phase 5 step 1 is complete (Stephen, 2026-10-17).**
- **What ran:** `run-a7.sh` (sha256 `0aa86ad0…`), from 03:19Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/a7/`: the script, `a7.log` (`6b81d35e…`), the intent `first-binding.json`
  (`09e7af88…`), `bind-output.json` (`786ce925…`), the status outputs and the authorization note.
- **The inputs.**
  - **The intent:** `RepairStoreBinding` 1.1.0, from the prepared template (`d97ded91…`), with `owner_action:
    bind-initialized-store`, `stale_evidence_refs: []`, the durable checkout as candidate and schema root, the
    pins, the owner `act_01978abc-1002…` and the idempotency key `g6-phase5-first-binding-2026-10-17`. Its
    30-minute validity window was stamped once at run time.
  - **The owner config:** `owner-status.json` (`217cc19e…`), a `SpecOperatorConfig@1.0.0` for the read-only
    `spec status`. Its grant ID, `agr_01a147d4-4551-701f-…`, is never activated. Step 3 uses one config per actor,
    each naming that actor's activated grant.
- **The result.**
  - **Before:** the read-only `spec status` was refused with "current store binding is unavailable" (the B-2
    premise), and the ledger held 2 events.
  - **The binding:** `ars store repair-binding` returned `initial-binding-published` and appended 1 event (3
    events).
  - **`binding_sha256`:** `594ab32398599aee7ca3f5c201c3b28bfbc6285af7f081e8b249a45d0a0ce34f`.
  - **What it binds:** `git_head` M2 `4d867d85…`, tree `ae446314…`, clean; `owner_action`
    `bind-initialized-store`; the initial manifest `b9a9921e…`; witness `1a7aa957…`; the schema catalogue
    `37973233…`; route `fad7c5a9…`; the SPEC-01 brief `d3b1eac0…` and the SPEC-02 contract `f005f4c9…`.
- **Verified (L7).**
  - An exact retry returned the same `binding_sha256` and appended nothing.
  - `ars discovery spec status --operator-config owner-status.json` succeeds, lists the route's actions, and
    appended nothing.
  - `load_current_binding` returns `594ab323…`, also from a fresh shell.
  - The checkout is clean at M2, with one worktree.
- **From here,** nothing is pulled into the checkout and no worktree is added (runbook L7) until step 6.
- **Next:** Phase 5 step 3, the bounded run (runbook §4). Each owner-authorized batch needs its own authorization;
  the first is the grant activations and `bootstrap_genesis`.

**Step 3 batch 1: the genesis grant and W11 genesis (Stephen, 2026-10-17).** Runbook §4, items 1 and 2.
- **What ran:** `run-s3b1.sh` (sha256 `f929268b…`), from 04:06Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/s3-b1/`: the inputs, `s3b1.log` (`f4fea58f…`), `activate-output.json`
  (`8a094c02…`), `genesis-output.json` (`a68e9dc0…`), the status files and the authorization note.
- **The grant (item 1).** `ars authority activate-grant`, with `--config owner-control-binding.json`
  (`d6777f33…`, equal to A7's `binding_config_sha256`), activated `agr_01a147fc-2c7c-71e9-b2aa-51c8c863aa80`.
  - **What it grants:** to the owner `act_01978abc-1002…`, as class `human`, the single command
    `ImportAcceptedW11CatalogueGenesis`.
  - **Its scope:** subject `scope_definition` `obj_019fed25-b33e-7740-b280-000000000001`, the accepted W11
    catalogue stream. Risk ceiling R3, effective 2026-10-17, expires 2026-12-31. Its owner decision is
    one-time use: it authorizes exactly one activation. The grant itself is not single-use.
  - **`decided_at`:** `2026-10-17T03:51:11Z`, fixed at preparation.
  - **The result:** status `accepted`, owner decision `arec_01a147fc-…`, grant sha256 `69aa2a76…`. The grant
    resolves to the owner. An exact retry returned the same receipt and appended nothing.
- **W11 genesis (item 2).** `ars discovery spec advance --action bootstrap_genesis`, run as the owner under that
  grant, gave state `completed`.
  - **The effect:** one, OR-140, command `cmd_d561d9cc-…`, event `evt_01a1480b-81d5-…` (hash `5ad31bc3…`), with
    receipt `accepted`.
  - **Retry:** an exact retry returned the same receipt and appended nothing.
- **Verified.**
  - The ledger went from 3 events to 4 after activation and 5 after genesis, and the retries left it unchanged.
  - `spec status` lists `bootstrap_genesis` exactly once, as `completed`, also from a fresh shell.
  - The checkout is clean at M2.
- **Next:** batch 2, the Assay bar (`bootstrap_assay_authority`, runbook §4 item 3): eight effects, each by its
  own actor under its own grant. It needs its own authorization.

**Step 3 batch 2: SPEC-01's Assay bar is accepted (Stephen, 2026-10-17).** Runbook §4, item 3.
- **The inputs.** The evidence is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b2/`.
  - **The bar intent** (`fdd99b5c…`) names the bar reviewer `act_01a14020-0454-…` and the prospective producer
    `act_01a14020-045b-…`.
  - **Eight grants, one per effect** (R3, effective 2026-10-17, expiring 2026-12-31, `decided_at` `04:15:29Z`),
    each with its own operator config. Each owner decision is one-time use. The step-to-actor map is in `steps.json` (`0f487833…`).
- **The first run stopped safely.** `run-s3b2.sh` (`1078b63f…`) activated grant 1 (`agr_01a14812-6b38-…`), and the
  activation was accepted. The script's own check then failed: Windows Python ends printed lines with CRLF, so
  the grant ID the shell read back carried a `\r` and compared unequal.
  - **The state at the stop,** confirmed from durable records: the ledger at 6 events, no bar effect, the bar
    not listed in status, and the checkout clean.
  - **The fix,** authorized separately by Stephen as v2: `run-s3b2-v2.sh` (`a0b470f7…`). It differs only in passing
    the shell's two reads of Python output through `tr -d '\r'`, and in keeping the first run's
    `activate-1.json` as `activate-1.first-run.json`.
- **The v2 run, from 05:03Z.**
  - **Grant 1:** re-activated as an exact retry, with the same receipt and status `accepted`. It appended nothing.
  - **The eight effects, in route order:** each one's grant was activated just before its use, and each ran as
    its own actor, with `next_effect` checked first.

  | # | Command | Actor |
  |---|---|---|
  | 1 | `RegisterAssayRubricContent` | the bar author `act_01a1169f-…` |
  | 2 | `RegisterAssayEvidenceScopeContent` | the bar author |
  | 3 | `ObserveW11AuthorityFile` (rubric) | the rubric observer |
  | 4 | `ObserveW11AuthorityFile` (scope) | the scope observer |
  | 5 | `RequestW11AuthorityReview` | the bar review requester |
  | 6 | `RecordW11AuthorityReview` | the bar reviewer |
  | 7 | `ProposeW11AuthorityDecision` | the bar proposer |
  | 8 | `ResolveDecision` | the owner |

  - **Each step:** receipt `accepted`, and the last effect is by the expected actor under its grant.
  - **No bar-review session ran** (added 2026-10-21, final review m-3, a material record correction).
    `RecordW11AuthorityReview` recorded the route's fixed OR-106 review context under the bar reviewer's identity,
    which is the inherited known limit. The bar's substance rests on #352's review and the delta assurance. All
    eight effects were submitted by batch 2's runner, from each actor's operator config (runbook §1).
- **The result.** `bootstrap_assay_authority` is `completed`, with 8 effects by 7 distinct actors under 8
  distinct grants. The ledger went from 6 to 22 events. An exact retry of step 8 returned the same receipt and
  appended nothing. A fresh-shell status agrees, and the checkout is clean at M2.
- **Evidence:** `s3b2.log` (`ed9e90bb…`), the per-step `activate-N.json` and `advance-N.json` (`advance-8.json`
  `59d30034…`), `status-after.json` (`78edf304…`), and both authorization notes.
- **Next:** batch 3, the SPEC-01 Task before `observe_source` (runbook §4 item 4). It needs its own authorization.

**Step 3 batch 3: decisions, the Task definition and a passing scratch rehearsal (Stephen, 2026-10-17).** Runbook
§4 item 4. Nothing live has run for this batch. The evidence is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b3/`
(`batch3-design.md`, `rehearsal-notes.md`).
- **Why it needed design.** Batch 3 submits raw C1 lifecycle commands, and the caller writes every field. The C0
  census ran this sequence with synthetic fixture values, so each needs a genuine one.
- **Stephen's decisions** (the six recommendations, accepted as written):
  1. **The source key** is `damrich-berens-kobak-neurips2024`, which fixes the Candidate ID
     `obj_a9ba6213-1073-7b78-ab6f-552cfdf9c2b7` for Task `tsk_01a14850-ab08-73c6-aef0-f3eb01a139d9`
     (`spec_source.source_ids`).
  2. **The Task definition:**
     - **Scope:** the D6 subset.
     - **Authorities:** `Stephen`, except review, which names the Task reviewer.
     - **Risk:** R3.
     - **Resource policy:** the committed bounded profile policy `pol_0198825f-…` 1.1.0.
     - **Root binding:** read-only, to the durable checkout at M2.
     - **`portfolio_refs`:** the Candidate.

     The full text is in `task-definition.json`, with `content_sha256`
     `f52ddda3487bf9946d6312c33a41acc3f1f74757a52cd9baa54063cb1f40c16e`, for Stephen's review.
  3. **The environment fingerprint:** sha256 of the canonical JSON of the Python version, the platform, the
     `uv.lock` sha256 and M2. Rehearsed value: `01f53658dd59…`.
  4. **The resource request and lease:** the `bounded` profile, network `public-read-only`, no external writes.
  5. **The host and boot identities:** derived from the machine name and its last boot time.
  6. **The context packet and process identity:** fresh IDs with no compiled context packet.
- **Option A (Stephen, 2026-10-17): a 1 h envelope.**
  - **The cause.** The bounded profile caps a resource grant at 3,600 s (`operations/profiles.py`): its expiry is
    `min(deadline, issued_at + max_runtime_s)`, with no renewal. That conflicts with D6's 4 h operator session, and
    rehearsal 2 refused the 4 h lease.
  - **The decision:** keep `bounded` with an honest 1 h envelope. The lease and the resource deadline end 1 h
    after stamping, and the runtime maximum is 3,600 s.
  - **The consequence is a known limit.** The SPEC-01 Attempt stays `running` for the operator return after the
    lease lapses. `CompleteAttempt` needs only a running Attempt, and the SPEC-01 route rows do not consult the
    lease.
- **The rehearsal, on scratch stores** made by the reserve, init and first-binding procedure in scratch clones of
  M2.
  - **Rehearsal 1:** stopped at `ClaimExecutionLease` (`resource_grant_binding_mismatch`). The lease
    `holder_profile` must equal the request's `requesting_profile` and the dispatch's `target_profile`, so one
    profile string now serves all three.
  - **Rehearsal 2:** stopped on the 1 h cap above.
  - **Rehearsal 3:** all 17 steps accepted.
    - **The steps:** five owner grant activations and twelve C1 commands, `CreateTask` through `StartAttempt`.
    - **The read-only checks:** the Attempt is `running`; the Task names the Candidate (m-1); and the route's own
      `verify_source_production` accepts the prepared SOURCE intent against the replayed ledger.
    - **Exact resume:** a second run skipped every step and appended nothing.
- **Known limits for the live batch:**
  - the lapsed lease (option A);
  - the fingerprint is a declared convention;
  - the host and boot identities are asserted;
  - there is no compiled context packet.
- **A record correction.** The batch 1 and 2 blocks above called the grants "one-time use". `one_time_use` is on
  the owner's administration decision: it authorizes exactly one activation. The grant is not single-use; the
  census used one grant for several commands in its scope. Both blocks are corrected.
- **Next:** the exact live script for batch 3, which runs the same driver against the live store from the durable
  checkout, for Stephen's authorization.

**Step 3 batch 3, live: the SPEC-01 Task is created and its Attempt is running (Stephen, 2026-10-17).**
- **What ran:** `run-s3b3.sh` (sha256 `c069aed9…`), from 05:46Z, authorized alone. It ran the rehearsed driver
  (`driver.py` `7731ff72…`) from the durable checkout's interpreter and code.
  - **Its inputs, all hash-pinned:** the config `d6777f33…`, `values.json`, `task-definition.json` and
    `grant-1..5.json`.
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b3/live/`: `s3b3.log` (`5d22a2c2…`), `driver.log`,
    `runtime.json` (`87d41013…`), every step's input, stdout and result, and the authorization note.
- **The result: all 17 steps accepted, exactly as rehearsed.** The live ledger went from 22 to 40 events.
  - **The owner grants:** five, activated just before their use (`agr_01a14850-ab62-…`, `-ab63-…`, `-ab64-…`,
    `-ab65-7dfe-…` and `-ab65-78a2-…`).
  - **The Task:** `CreateTask` for `tsk_01a14850-ab08-73c6-aef0-f3eb01a139d9`, with the definition Stephen reviewed
    (`content_sha256` `f52ddda3…`), naming the Candidate `obj_a9ba6213-1073-7b78-ab6f-552cfdf9c2b7`. Then
    `RequestReadiness` and `ApproveReadiness`.
  - **The dispatch:** `IssueDispatch`, `RecordDispatchDelivery` and `AcknowledgeDispatch`.
  - **The resource grant and lease:**
    - `RequestResourceGrant`, with the asserted host and boot identities;
    - `ClaimExecutionLease`, 1 h (option A), expiring `2026-10-17T06:46:39Z`;
    - `ClaimDispatch`, which appended two events.
  - **The Attempt:** `CreateAttempt`, `ClaimAttempt` and `StartAttempt` for
    `att_01a14850-ab08-7e7e-930d-9942f8ec546e`. Its `code_identity` is `git:sha1:4d867d85…` (M2) and its environment
    fingerprint `01f53658dd59…`, equal to the rehearsal's.
- **Verified,** also from a fresh shell with the driver's read-only `--verify-only`:
  - the Attempt is `running`;
  - the Task's `portfolio_refs` include the Candidate, and its rederivation from the Task ID and source key agrees
    (m-1);
  - the route's own `verify_source_production` accepts `live/source-intent.json` (`6023d76e…`, byte-identical to the
    rehearsal's) against the replayed live ledger;
  - the checkout is clean at M2.
- **Hold.** The Task is not amended, and the Attempt stays running until the operator return is registered (P5-7
  amended). The lease lapses at 06:46:39Z, the option A known limit.
- **Next:** batch 4, `observe_source` for `neurips2024` with that SOURCE intent and its grants (runbook §4 item 5).
  It needs its own authorization.

**Step 3 batch 4, live: the SOURCE is registered and the Candidate exists (Stephen, 2026-10-17).** Runbook §4 item 5.
- **The rehearsal first.** On the batch 3 scratch store, which holds the same Task, Attempt and IDs, `batch4.py`
  (`5615a1d1…`) first ran W11 genesis, because OR-029 refuses Scout ingestion before it. Then:
  - effect 1 fetched and registered the public source at exactly the values the public-registration probe pinned;
  - effect 2, OR-029, registered the Candidate;
  - an exact retry appended nothing.
- **What ran live:** `run-s3b4.sh` (sha256 `e71c6fb6…`), from 06:58Z, authorized alone. It ran `batch4.py` from the
  durable checkout, as the owner.
  - **Its inputs, all hash-pinned:** the SOURCE intent `6023d76e…` that the route's verifier accepted after
    batch 3, and two grant requests with their configs.
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b4/live/`: `s3b4.log` (`2e59dcd7…`), each step's
    output (`2-advance-register.json` `96dc0af3…`, `4-advance-ingest.json` `cdd4447e…`), the retry and the
    authorization note.
  - **The hold, re-checked first** (read-only, with the batch 3 driver's `--verify-only`): the Attempt was still
    running and the verifier still accepted the intent.
- **The result.** The live ledger went from 40 to 45 events.
  - **Grant 1:** `agr_01a14887-592d-…`, `RegisterArtefact` on the SOURCE artefact
    `art_87c22454-9078-7e77-a83f-9ded3957f05e`.
  - **Effect 1, `RegisterArtefact`:** the route's SOURCE verifier, then the read-only public Git fetch of
    `https://github.com/berenslab/eff-ph.git`, with no credentials.
    - `refs/tags/neurips2024` resolved to `145efcde673f1a1897eff250b77221d26c34c479`.
    - The source's sha256 is `3eea9174db28f4dd5bcf4e622709280f25fd6bfe0843ff1fc2e1d1559401f9df`.
  - **Grant 2:** `agr_01a14887-592e-…`, `IngestScoutObservationBatch` on the observation
    `obj_a24e7360-236c-7143-a9c7-8e71ea6ddd94`.
  - **Effect 2, OR-029:** the Scout observation batch, which registered the Candidate
    `obj_a9ba6213-1073-7b78-ab6f-552cfdf9c2b7` (two events).
- **Verified.**
  - An exact retry returned `completed` and appended nothing.
  - The Candidate is in the replayed Discovery candidates.
  - A fresh-shell `spec status` shows `observe_source` completed with 2 effects, alongside genesis (1) and the bar
    (8).
  - The checkout is clean at M2.
- **Next:** batch 5, `request_spec_01` by the steward and `prepare_spec_01` by the owner, which issues the operator
  brief (runbook §4 item 6). It needs its own authorization.

**Step 3 batch 5, live: the Assay is requested and the operator brief is issued (Stephen, 2026-10-17).** Runbook
§4 item 6, first two steps.
- **The rehearsal first.** The first scratch attempt stopped correctly: "request_spec_01 requires an accepted Assay
  bar", because the scratch store had never had batch 2's bar. Its only write was one grant activation.
  `rehearse_bar.py` then ran batch 2's own eight bar effects on the scratch store from batch 2's exact inputs, and
  `batch5.py` (`0ab60c87…`) passed: both actions completed, both retries appended nothing, and the brief bound the
  source and the Attempt.
- **What ran live:** `run-s3b5.sh` (sha256 `952df4b9…`), from 12:40Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/s3-b5/live/`: `s3b5.log` (`dee1f7a8…`), `advance-request.json` (`a6576864…`),
  `advance-prepare.json` (`17661854…`), `brief.json` (`45f0d20a…`), the retries and the authorization note.
- **The result.** The live ledger went from 45 to 51 events.
  - **`request_spec_01` (OR-003, `RequestAssay`):** by the steward `act_01a14020-0459-…`, in its own ARS actor session (submitted by the batch runner; runbook §1), under
    `agr_01a148ba-8cf5-…`, scoped to the Candidate `obj_a9ba6213-…`. It appended 3 events. The route refuses the
    producer or the owner as requester.
  - **`prepare_spec_01` (`RegisterArtefact`):** by the owner under `agr_01a148ba-8cf8-…`, issuing the operator brief
    `art_13fdb997-1fb2-74bb-8967-ab9a1ae930e0` for the Assay `asy_58d83420-807f-7917-80ef-666b340e7f32`.
- **Verified.**
  - Both actions completed, by the expected actor under the expected grant.
  - Both exact retries returned the same receipt and appended nothing.
  - The brief's `brief_source` sha256 is the route package's SPEC-01 source, `d3b1eac0…`.
  - The brief's `task` equals the running Attempt's identities: the Task and its revision, the Attempt, the
    dispatch, the context packet, code `git:sha1:4d867d85…` and fingerprint `01f53658…`.
  - A fresh-shell status shows `observe_source`, genesis, the bar, `request_spec_01` and `prepare_spec_01`
    completed.
  - The checkout is clean at M2.
- **Next:** the operator's SPEC-01 work from the issued brief, by the producer `act_01a14020-045b-…` in a separate
  owner-operated session. It drafts the operator return; nothing is registered until `return_spec_01_complete`,
  which needs its own authorization.

**Step 3 batch 6, live: the operator return is registered and the Assay is scored PARK (Stephen, 2026-10-20).**
Runbook §4 item 6, the return.
- **The operator session.** The producer `act_01a14020-045b-…` worked in a separate, fresh-context session from
  `s3-b6/producer-session-brief.md` and registered nothing.
  - **The draft:** `s3-b6/output/operator-return-draft.json`, sha256 `568447c7…` (29,749 bytes). The pre-flight
    checker passes.
  - **The axes:** topology true; data feasibility 2 and novelty 1, so 3, below PROMOTE's 4. Four further gates are
    false: the non-redundant primary claim, the named estimand and representation freeze, the SPEC-02 design within
    the envelope, and no unresolved paper/code discrepancy.
  - **Two paper/code discrepancies (D1, D2).** D1: `get_toy_data` re-seeds one RandomState for both the basis and
    the noise, so the noise is not independent as the paper says (found by reading the code, not running it). D2:
    the paper's ripser commit `140670f` is not on the branch, and it does not build the binary the code invokes.
  - **Open points for the outcome review:** the session attributed the score shortfall to novelty alone, and it
    could not re-derive the source hash `3eea9174…` (it verified the commit and tree instead).
  - **Beyond the brief:** the session also wrote owner-action prompts, a decision sheet and a SPEC-02 amendment
    draft. Nothing here relies on them.
- **The rehearsal first.** `batch6.py` (`7c7aaa16…`) ran on the scratch store from 51 to 56 events. Both effects
  completed, admission's recommendation was PARK, the runner's own recomputation of the bar rule from the ten axis
  values was also PARK, and a full rerun skipped both effects and appended nothing.
- **What ran live:** `run-s3b6.sh` (sha256 `acc9f79c…`), from 05:43Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/s3-b7/live/`: `s3b6.log` (`91f88547…`), `advance-register.json`
  (`216c6232…`), `advance-score.json` (`5c1a707f…`, byte-equal to `retry-score.json`), `return.json`
  (`86ea24df…`), and the authorization note.
- **The result.** The live ledger went from 51 to 56 events.
  - **`RegisterArtefact`:** by the owner under `agr_01a157ce-589d-…`, scoped to the return artefact. It registered
    the return `art_fc1c4531-4398-761c-8787-e2355e7c1ebd`, and the action stood `prepared`.
  - **`RecordAssayScore` (OR-004):** by the producer, in a new ARS actor session (submitted by the batch runner with
    the producer session's draft unchanged; runbook §1), under `agr_01a157ce-589f-…`, scoped to the
    Candidate. It re-supplied the same return bytes and appended `AssayScored` and `CandidateAssayLinked`.
- **Verified.**
  - Both effects ran by the expected actor under the expected grant, and the action completed.
  - The exact retry returned the same receipt and appended nothing.
  - The registered `operator_return` equals the draft, and the return binds the brief `art_13fdb997-…` and its
    Task.
  - The scorecard's producer is the producer, and its mechanical recommendation is PARK. That agrees with the bar
    rule recomputed from the axis values.
  - A fresh, read-only process replayed the ledger at 56 events. The Assay is `scored` with scorecard
    `09c9eb50…`, the same as the return's. The Candidate is `assay_scored`, and the Attempt is still running.
  - The checkout is clean at M2.
  - The scorecard hash differs from the rehearsal's (`73ff7f2e…`). A field diff shows only three ledger-reference
    hashes differ: the bar acceptance, the Assay request and the Candidate. Each store has its own events.
- **Next:** `review_spec_01_complete`, requested by the steward and recorded by an independent outcome reviewer.
  It needs its own authorization.

**Step 3 batch 7, live: the steward requests the outcome review (Stephen, 2026-10-20).** Runbook §4 item 6, the
outcome review's first effect.
- **Why it is split.** `review_spec_01_complete` has two effects:
  - `RequestDiscoveryOutcomeReview` (OR-034), by the steward;
  - `ReviewDiscoveryOutcome` (OR-006), by the outcome reviewer `act_01a14020-045e-…`, with the reviewer's verdict
    evidence.

  The request runs first, so that the independent reviewer works from the live review contract. This follows
  the pattern of batches 5 and 6, where the brief was issued before the operator worked. The verdict needs its
  own later authorization. The route records only an approving verdict (an inherited limit). If the reviewer
  will not approve, the owner rules.
- **The rehearsal first.** `batch7.py` ran the whole action on the scratch store:
  - the request, 56 to 59 events;
  - then the verdict, with a placeholder evidence object labelled rehearsal-only, 59 to 62 events, leaving the
    review `satisfied`.

  The runner's last check expected the Assay still `scored` after the verdict, so it stopped. It is `reviewed`
  by then. I fixed the check (`batch7.py` is now `dd54fe94…`), and the resumed run passed.
- **Scratch reset to after the request.** A copy of the store directory was refused: "store physical root
  identity differs from approved origin witness". The witness binds the root directory's device and inode. I
  moved the original root back and replaced only its contents with the post-request snapshot. The request path
  then passed again with the final runner. Scratch is at 59, with the review pending, ready to rehearse the real
  verdict.
- **What ran live:** `run-s3b7.sh` (sha256 `b24850c4…`), from 07:13Z, authorized alone.
  - The evidence is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b8/live-request/`: `s3b7.log` (`27697878…`),
    `advance-request.json` (`d227f61b…`, byte-equal to `retry-request.json`), `review-request.json`
    (`bd18354d…`), and the authorization note.
  - The inputs came from `prepare.py`, which checked each grant request's exact fields, its active command
    binding and each operator config read-only against the live binding.
- **The result.** The live ledger went from 56 to 59 events: the grant activation `agr_01a1581f-0e6c-…`,
  `ReviewRequested` on `rev_0e21fa01-150d-77e2-a07f-237b8789f726`, and `AssayOutcomeReviewRequested` on the Assay,
  both by the steward, in a new ARS actor session (submitted by the batch runner; runbook §1).
- **Verified.**
  - The effect ran by the steward under the expected grant. The action stands `prepared`, next
    `ReviewDiscoveryOutcome`.
  - The exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 59 events and found the review `pending`:
    - its subject is the registered scorecard `09c9eb50…`;
    - its required evidence is `scorecard:09c9eb50…` and `operator-return:fc07ca42…`, the registered return's
      content hash;
    - its grade is `independent`, its capability `assay-independent-review`, and its deadline
      2026-11-19T05:45Z, 30 days after the score.
  - The Assay is still `scored`, and the Attempt is still running.
  - My first fresh-check script expected the event type `AssayReviewRequested`, from the route table. The stored
    type is `AssayOutcomeReviewRequested`, which is the runtime's name for OR-034. I corrected the script, and it
    passed. The ledger was never in question.
  - The checkout is clean at M2.
- **Next:**
  - The outcome reviewer works in a separate, fresh-context session from `s3-b8/outcome-reviewer-session-brief.md`
    and drafts the verdict evidence. It registers nothing.
  - Then `ReviewDiscoveryOutcome` runs, rehearsed on scratch with the real draft, under its own authorization.

**Step 3 batch 8, live: the independent outcome review approves (Stephen, 2026-10-20).** Runbook §4 item 6, the
outcome review's second effect.
- **The review session.**
  - **Who:** the outcome reviewer `act_01a14020-045e-…`, in a separate, fresh-context session
    (`local_79528633-…`, Claude Opus 5.5).
  - **What it worked from:** `s3-b8/outcome-reviewer-session-brief.md` and eight inputs. The assembly checked
    every input against the ledger: the stored return's bytes (`fc07ca42…`, the review's `operator-return:` ref),
    the scorecard (`09c9eb50…`, the subject), the stored brief (`7b4f9eb2…`), the draft, SPEC-01's brief, rubric
    and evidence scope, and the live review request. The manifest is `81e8673c…`, and the context is
    `ctx_01a1582f-…`.
  - **What it touched:** it registered nothing and read no other session. Its only writes were in
    `s3-b8/review-output/`. Afterwards the inputs were byte-identical, the store was at 59, and both checkouts were
    clean.
- **The verdict: approve.** Checks 1 to 4 hold:
  - the registered `operator_return` equals the draft, as parsed JSON (key order differs);
  - the ten scorecard axes match the return;
  - PARK follows from the bar;
  - the brief, Task, producer and subject bindings hold.

  The draft `verdict-evidence-draft.json` (`901003af…`) passes `check_verdict.py`.
  - **Eight findings, none blocking, none changing PARK:**
    - the topology pass rests on no verified decisive failure, not a positive demonstration;
    - the disconnected-graph amendment is not tracked by a revisit predicate;
    - the benchmark gate passes despite D1;
    - the shortfall code sits on novelty only;
    - the return cites the issued brief as `45f0d20a…`, not `7b4f9eb2…`;
    - the per-axis evidence refs name the rubric and scope;
    - D1 and D2 rest on the producer's static reading alone;
    - none of these contradicts a score.
  - **The brief hash, checked.** On the fifth point, `45f0d20a…` is batch 5's pretty-printed `brief.json`.
    Parsed, it is the same object as the stored brief `7b4f9eb2…`.
  - **Seven limitations,** including inputs-only, topology and paper-claim out of scope, and approve-only.
- **The rehearsal first.** `batch7.py --effects verdict` ran on the scratch store from 59 to 62 events with
  `verdict-intent.json` (`196ca580…`, the request intent plus the draft unchanged). The review went `satisfied`,
  and a rerun appended nothing.
- **What ran live:** `run-s3b8.sh` (sha256 `7e0bd7b7…`), from 10:16Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/s3-b8/live-verdict/`: `s3b8.log` (`ff9f140d…`), `advance-verdict.json`
  (`7fa10632…`, byte-equal to `retry-verdict.json`), `review-verdict.json` (`0c419efc…`), and the authorization
  note.
- **The result.** The live ledger went from 59 to 62 events: the grant activation `agr_01a1581f-0e77-…`, then
  `ReviewVerdictRecorded` on `rev_0e21fa01-…` and `AssayReviewed` on the Assay, both by the outcome reviewer.
- **Verified.**
  - The effect ran by the outcome reviewer under the expected grant, and `review_spec_01_complete` completed.
  - The exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 62 events:
    - the review is `satisfied`, with `approve`, by the outcome reviewer;
    - the reviewer is neither the requester nor the producer;
    - the verdict's unchanged subject is the scorecard `09c9eb50…`;
    - every supplied evidence field is recorded as drafted.
  - The Assay is `reviewed` with mechanical PARK, the Candidate is `assay_scored`, and the Attempt is still
    running.
  - The checkout is clean at M2.
- **Next:** `decide_spec_01`. The decision proposer proposes (OR-012), and the owner resolves (OR-013). Stephen
  decides, under its own authorization.

**Step 3 batch 9, live: the owner parks the SPEC-01 Candidate (Stephen, 2026-10-20).** Runbook §4 item 6, the
decision.
- **The decision.** Stephen decided in chat, from `s3-b9/decision-sheet.md`:
  - **The proposer's recommendation:** PARK.
  - **The owner's selection:** PARK.
  - **The revisit triggers,** as drafted:
    - R1 to R5, the operator's revisit predicates;
    - R6, the outcome reviewer's untracked point: an explicit connected-components check as a SPEC-02
      amendment;
    - the rule, as a seventh string: revisit only when R1 to R6 all hold, because R1 to R3 alone make only a
      synthetic reproduction runnable.
- **What admission allowed.**
  - **PARK:** with revisit triggers.
  - **KILL:** admissible, but the brief requires a directly verified decisive failure, and none was verified.
  - **PROMOTE:** refused without a mechanical PROMOTE.
- **Carried into the decision:** the outcome reviewer's findings, and the limits:
  - the route records only approving reviews;
  - the review was inputs-only;
  - topology and paper-claim assurance were out of the review's scope;
  - the producer and the reviewer ran on the same model family as the session running the route.
- **The rehearsal first.** `batch9.py` (`c16a7798…`) ran both effects on the scratch store from 62 to 68 events,
  and a rerun appended nothing.
  - **The intents:**
    - `decide-intent.json` (`0c106113…`, recommendation PARK);
    - `resolve-intent.json` (`3576a411…`), the same intent plus `resolution-evidence.json` (`310e53ce…`).
  - **The grants and configs** came from `prepare.py`, checked read-only against the live binding. The owner
    keeps its A0 session.
- **What ran live:** `run-s3b9.sh` (sha256 `dc939afe…`), from 10:33Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/s3-b9/live/`: `s3b9.log` (`70139d81…`), `advance-propose.json` (`0b7766aa…`),
  `advance-resolve.json` (`355bed60…`, byte-equal to `retry-resolve.json`), `decision.json` (`05442fe0…`), the
  decision note and the authorization note.
- **The result.** The live ledger went from 62 to 68 events.
  - **`ProposePromotionDecision` (OR-012):** by the decision proposer `act_01a14020-0460-…`, under
    `agr_01a158d8-e0e0-…`. It appended `DecisionProposed` on `dec_1c6c1254-da10-716b-8def-c72f4232bddf` and
    `CandidatePromotionRequested`, citing `scorecard:09c9eb50…` and `review:rev_0e21fa01-…`.
  - **`ResolveDecision` (OR-013):** by the owner, under a human-only grant, `agr_01a158d8-e0ea-…`. It appended
    `DecisionResolved` and `CandidatePromotionApplied`. The route names these Candidate events "promotion"
    whatever the option; the relation carries PARK.
- **Verified.**
  - Both effects ran by the expected actor under the expected grant, and the action completed.
  - The proposer is neither the owner, the producer nor the outcome reviewer.
  - The exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 68 events:
    - the Decision is `resolved` with PARK, decided by the owner;
    - it considered the review `rev_0e21fa01-…`;
    - its seven revisit triggers are exactly the owner's;
    - the Candidate is `parked`, the Assay is `reviewed` with PARK, and the Attempt is still running.
  - The checkout is clean at M2.
- **Next:** closure (runbook §4 item 7): end the Attempt, register the evidence artefacts, run `close_task`, then
  `register_project_use_decision` and `accept_project_use_decision`. Each part needs its own authorization.

**Closure plan (Stephen, 2026-10-20).** Stephen accepted `s3-b10/closure-plan.md` (`35aa559f…`) as recommended.
- **Four live batches.** Each Task-level review is requested live before its reviewer works, as in batches 7 and 8:
  - batch 10: `CompleteAttempt`, then `close_task` effects 1 to 3;
  - the Task-review session;
  - batch 11: `close_task` effects 4 to 7;
  - batch 12: `register_project_use_decision`;
  - the project-use review session;
  - batch 13: `accept_project_use_decision`.
- **Option A: the Attempt's evidence.** The Attempt names the two route-registered outputs that the Task
  definition's `expected_artefact_types` lists: the SOURCE observation `art_87c22454-…` and the operator return
  `art_fc1c4531-…`, which carries the scorecard. Nothing new is registered.
  - **Why not B:** registering new evidence through C1 `RegisterArtefact` would record a manifest whose bytes
    admission does not read.
  - **Probed on scratch first:** `CompleteAttempt` was accepted with the lease long lapsed, and `SubmitForReview`
    accepted both as distinct registered candidates. Scratch was then restored to 68 inside its original root.
- **The Task review request:** as drafted in the plan.
  - **Type and lanes:** `provenance`, on the lanes `output` and `provenance`.
  - **The question:** whether the exact Task subject satisfies its bounded contract on the ledger.
  - **Governing refs:** the Task definition `f52ddda3…`, A0, D6 and runbook §4.
  - **Required evidence:** the two candidates by content hash, the scorecard, the outcome review and the Decision.
  - **Deadline and escalation:** 2026-11-19, and owner-ruling.
- **Known limit: acceptance asserts all five criteria.** `AcceptTask`'s route-derived payload records every
  acceptance criterion as satisfied (`spec_task.py:710`).
  - **Criterion 4,** Task closure, is the acceptance itself.
  - **Criterion 5,** the reviewed project-use decision, can exist only after acceptance, because the project-use
    route requires an accepted Task.
  - **The Task cannot be amended:** the project-use route refuses a Task amended since dispatch.
  - **So:** the Task reviewer judges criteria 1 to 3 on the evidence and 4 to 5 as procedural. Batches 12 and 13
    discharge criterion 5 after the ledger already asserts it.
- **Known limit: the lapsed lease is not released.** The bounded lease lapsed on 2026-10-17 (option A). Closure
  does not need its release (`spec_task.py`: "never from attempt completion, lease release or result presence"),
  so the resource request's release obligation stays unmet. This extends the option A known limit.
- **Also carried:**
  - the Task review's verdict evidence has no `findings` or `limitations` fields, so findings live in the
    reviewer's notes, cited by sha256;
  - the route records only `approve`.

**Step 3 batch 10, live: the Attempt ends, and the Task review is requested (Stephen, 2026-10-20).** Runbook §4
item 7, closure part 1.
- **The rehearsal first.** `batch10.py` ran on the scratch store from 68 to 75 events: `CompleteAttempt`, then
  `SubmitForReview`, `RequestReview` and `AssignReview`.
  - **One stop, in my own check.** The final check compared the submitted candidate hashes with the live-pinned
    ones, but scratch registered its own bytes.
  - **The fix:** the check now compares against the store's own registrations, and against the pinned hashes in
    live mode only. `batch10.py` is now `bd9f0a21…`, and the resumed run passed, skipping every recorded step.
  - **Inputs:** from `prepare.py`, read-only against the live ledger for the two content hashes. There are three
    owner grants:
    - `CompleteAttempt` on the Attempt;
    - `SubmitForReview` alone on the Task (`AcceptTask` gets its own grant in batch 11);
    - `RequestReview` and `AssignReview` on the new review (`SatisfyReview` waits for batch 11).
- **What ran live:** `run-s3b10.sh` (sha256 `e199e93c…`), from 15:11Z, authorized alone. It ran
  `complete-attempt.json` (`5e7d1942…`) and the three intents.
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b10/live/`: `s3b10.log` (`29aaac16…`),
    `complete-attempt.json` (`8fd0f090…`), `advance-AssignReview.json` (`361a6a59…`, byte-equal to the retry),
    `task-review-request.json` (`faca7386…`), and the authorization note.
- **The result.** The live ledger went from 68 to 75 events, all by the owner:
  - three grant activations;
  - `AttemptCompleted`, naming `art_87c22454-…` and `art_fc1c4531-…` with `candidate_output_recorded`;
  - `TaskSubmittedForReview` on `tsk_01a14850-…`;
  - `ReviewRequested` and `ReviewAssigned` on the Task review `rev_01a158ed-5755-76ee-a925-928f5fd95ac6`.
- **Verified.**
  - Each effect ran under its own grant, and the exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 75 events:
    - the Attempt is `completed`, by the exact prepared command;
    - the submission carries both candidates with their registered hashes, `b46dfda8…` and `fc07ca42…`, the
      latter being the outcome review's `operator-return:` ref;
    - the request equals the owner's field by field;
    - the review is `assigned` to the Task reviewer `act_01a14020-0462-…`;
    - the Task is `review_pending`, and the Candidate is still `parked`.
  - The checkout is clean at M2.
- **Next:** the Task reviewer works in a separate, fresh-context session from the Task-review package and drafts
  the verdict evidence. Then batch 11 runs, under its own authorization.

**Step 3 batch 11, live: the Task review approves, and the SPEC-01 Task is accepted (Stephen, 2026-10-20).** Runbook
§4 item 7, closure part 2.
- **The Task-review session.**
  - **Who:** the Task reviewer `act_01a14020-0462-…`, in a separate, fresh-context session (`local_f2505387-…`,
    Claude Opus 5.5).
  - **What it worked from:** `s3-b11/task-reviewer-session-brief.md` and eight inputs, assembled read-only from
    the live store with every hash checked against the ledger:
    - the stored Task object;
    - the ledger's 75 events;
    - the two candidates' stored bytes;
    - the scorecard;
    - the review request, assignment and submission;
    - SPEC-01's brief and rubric.

    The manifest is `4c5f979e…`, and the context is `ctx_01a15a04-…`.
  - **What it touched:** it registered nothing and read no other session. Afterwards the inputs were
    byte-identical and the store was at 75.
- **The verdict: approve.**
  - The submission is the Attempt's.
  - Criterion 1 holds: the sealed producer relation `7d32f19b…`, and `AssayScored` by the producer.
  - Criterion 2 holds: the outcome review is independent of its requester and the producer.
  - Criterion 3 holds: the owner's `DecisionResolved` PARK.
  - Check 5 found no breach of the bounded scope, non-goals or prohibited shortcuts.
  - Criteria 4 and 5 were judged procedural, as accepted.
  - The draft (`b525891d…`) passes `check_task_verdict.py`. Its trace ref is `review-notes.md` (`3bf9efe3…`),
    since the route's verdict carries no findings field.
- **Findings, in the notes** (F1 to F7 and L1 to L7; selected here. Completed 2026-10-21, final review m-4.)
  - **F1:** the unreleased lease departs from the resource request's stated release obligation (accepted).
  - **F2:** the session-time limits are not evidenced on the ledger.
  - **F3:** the brief package `art_13fdb997-…` is a third registered artefact under the Attempt, read as in scope.
  - **F4:** "Promotion" in the Candidate events is route vocabulary for PARK.
  - **F5:** the return is bound to the outcome review as required evidence.
  - **F6:** the outcome review's findings remain open at the scientific level; D1 and D2 were re-derived by no
    reviewer.
  - **F7:** the return document's `producer_actor_id` is the registering owner, and the scorecard's is the
    producer.
  - **L5:** the review request's `subject_hashes` value `9da8e928…` did not reproduce from the inputs. I
    reproduced it read-only: it is the sha256 of the replayed Task stream state before the request.
- **The rehearsal first.** `batch11.py` (`7fa2dc53…`) ran effects 4 to 7 on the scratch store from 75 to 82
  events, and a rerun appended nothing.
  - **The inputs** came from `prepare.py`:
    - the Task reviewer's agent grant for `StartReview` and `RecordReviewVerdict`, in a new ARS actor session (the
      runner submitted the review session's draft unchanged; runbook §1);
    - the owner's separate grants for `SatisfyReview` and `AcceptTask`;
    - the verdict intent `c6bc410a…`, which is the close_task intent plus the draft unchanged;
    - the owner's satisfaction evidence `ecc31d3c…`: an approval-policy ref, the review notes' hash, and the gate
      `spec-01-task-acceptance-gate`.
      - **What the gate name is:** only `SatisfyReview`'s required evidence label.
      - **Where the governing records are:** the Task review request's `governing_refs`. They are the Task
        definition `f52ddda3…` (its acceptance criteria), P-058 A0 and D6, and runbook §4 (P-058, "Closure plan").
      - **The research assurance behind them:** the SPEC-01 bar and decision rule (#352, accepted in batch 2),
        and the delta assurance on M1 and M2 (P-058, "L5 delta assurance on M2").
      - Clarified 2026-10-21 in answer to review.
- **What ran live:** `run-s3b11.sh` (sha256 `f3436b2a…`), from 16:30Z, authorized alone. The evidence is in
  `C:/Users/steph/.codex/tmp/g6-p5/s3-b12/live/`: `s3b11.log` (`b3349f1f…`), `advance-RecordReviewVerdict.json`
  (`59dd137a…`), `advance-AcceptTask.json` (`f540c374…`, byte-equal to the retry), `task-closure.json`
  (`a48f6b70…`), and the authorization note.
- **The result.** The live ledger went from 75 to 82 events:
  - three grant activations;
  - `ReviewStarted` and `ReviewVerdictRecorded`, by the Task reviewer;
  - `ReviewSatisfied` and `TaskAccepted`, by the owner.
- **Verified.**
  - Each effect ran by the expected actor under its own grant, and `close_task` completed.
  - The exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 82 events:
    - the verdict is `approve`, carrying the draft field for field;
    - the satisfaction carries the owner's evidence;
    - the Task is `accepted`, the Task review `satisfied` and the Attempt `completed`;
    - the acceptance selects the two candidates and records all five criteria, the accepted known limit.
  - The checkout is clean at M2.
- **Next:** batch 12, `register_project_use_decision`, in Stephen's words, under its own authorization.

**Finding: the project-use review's governing evidence has no public writer (2026-10-20).** This is a gap of the
census B-3 kind, found while preparing batch 12.
- **What admission requires.** `accept_project_use_decision` is two effects, `RecordScientificReview` by the
  project-use reviewer and then `SetArtefactUseAuthority` by the owner. `SetArtefactUseAuthority` admission
  (`command/service.py:4733-4792`) requires the review's single `evidence_refs` entry to resolve to a governing
  scientific-review record in `objects/assurance_record`. The record (`ars://evidence/governing-scientific-review`
  1.0.0) is checked in full. It must carry:
  - `schema_id` `ars://evidence/governing-scientific-review` and `schema_version` `1.0.0`;
  - the ledger's `project_id`;
  - the review (`review_id`), which must equal the recorded review's;
  - the decision's content hash (`subject_sha256`);
  - the reviewer (`reviewer_actor_id`), which must equal the reviewing actor;
  - `eligible: true`, `related: false` and `status: active`;
  - an `independence_grade` at or above the rule's minimum.

  Its canonical sha256 must also equal its resolution (`service.py:4762-4786`). This list is complete; it was
  completed on 2026-10-21 in answer to review.
- **The review is refused first.** The route runs the same rule before recording the review (`spec.py:288-302`),
  so the first effect is refused.
- **No public path writes the record.**
  - `GoverningScientificReviewStore.publish` (`artefacts/runtime.py:61`) is called only by tests.
  - `ars assurance-record write` covers twelve other record classes, not this one.
  - The 2026-10-07 census covered Task seeding through evidence registration, not project-use acceptance.
- **The review's substance is off the ledger too.** The record has no notes field, and admission requires exactly
  one `evidence_refs` entry, so the project-use review's findings cannot be cited on the ledger.

**Option A for batch 13 (Stephen, 2026-10-21).** Stephen chose option A from `s3-b13/project-use-decision-sheet.md`
(`a5b1885a…`).
- **What A does:** the owner places the one governing record with the internal
  `GoverningScientificReviewStore.publish`, from a hash-pinned script, after the project-use reviewer's session.
  Admission still checks the record's schema, subject hash, reviewer and grade.
- **Why not the others:**
  - **B,** a certified public writer like PR-G, would need a new code identity and a re-pin mid-run. It is
    better as a follow-up.
  - **C,** stopping at registration, would leave criterion 5 and the D6 project-use result unmet.
- **The known limit:**
  - the live procedure depends on an internal API at this one seam;
  - `eligible`, `related` and the grade are owner assertions about the reviewer.
- **Probed on scratch** (`s3-b14/probe_option_a.py`, which refuses any `TDL-ARS-*` root).
  - **Positive, grade I1:** with the two grants, the placed record and both effects, scratch went from 84 to 88.
    The route's `result` reads `accepted`, with its disposition wording.
  - **Negative control, grade I0:** after a reset, the reviewer's advance was refused before recording
    (`governing_scientific_review_invalid`) and appended nothing. So admission checks the placed record, and I1
    meets the minimum.
  - **Afterwards:** scratch was reset to 84 inside its original root. The live store was untouched: 82 events and
    30 assurance records.

**Step 3 batch 12, live: the project-use decision is registered (Stephen, 2026-10-21).** Runbook §4 item 7,
closure part 3.
- **Stephen's words,** accepted as drafted in the sheet:
  - **The disposition:** `retain_experimental_benchmark`, the only one permitted for a PARK.
  - **The rationale:** the PARK outcome and why.
  - **Seven limitations:** review scope, D1 and D2 static, no survey data, approve-only and inputs-only reviews,
    one model family, the lapsed lease, and the acceptance asserting criterion 5.
  - **Two next gates:** revisit only on R1 to R6; and SPEC-02 only after a later passing outcome, an owner
    decision and a separate approval.
  - **The D6 subset qualification and a `no_spike_reason`.**
  - **The word rule:** the prose avoids the route-reserved *promot*, *replicat* and *adopt*. `prepare.py` checks
    this, and validates the intent against `ars://portfolio/spec-project-use-intent`.
- **The rehearsal first.** `batch12.py` (`224ca671…`) ran on the scratch store from 82 to 84 events, and the
  route's `result` read `pending`, with `RecordScientificReview` next.
- **What ran live:** `run-s3b12.sh` (sha256 `0e5b3cb7…`), from 00:15Z, authorized alone. It ran
  `register-intent.json` (`05b222c5…`).
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b13/live/`: `s3b12.log` (`876523d5…`),
    `advance-register.json` (`bd37daf4…`, byte-equal to the retry), `decision.json` (`7e664eb4…`), the JSON and
    Markdown results, and the authorization note.
- **The result.** The live ledger went from 82 to 84 events: the grant activation `agr_01a15bc7-…`, and
  `ArtefactRegistered` of the ProjectUseDecision `art_fbd584af-f080-7cde-b090-59ddb1b7a442` by the owner, with
  content `4ed88262…`.
- **Verified.**
  - The exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 84 events:
    - the stored document hashes to the manifest's content and is schema-valid;
    - its `intent` equals the accepted intent as parsed JSON (corrected 2026-10-21 from "byte for byte"; the same
      overstatement as final review m-1);
    - it cites the accepted Task, its two selected artefacts as evidence, the owner's PARK, no Spike, and the
      parked Candidate;
    - no review is recorded yet.
  - The route's result reads `pending`.
  - The checkout is clean at M2.
- **Next:** the project-use reviewer `act_01a14020-0465-…` works in a separate, fresh-context session. Then batch
  13 runs under option A: the owner places the governing record, then the reviewer's `RecordScientificReview` and
  the owner's `SetArtefactUseAuthority`. It needs its own authorization.

**Step 3 batch 13, live: the project-use review approves, and the project-use result is accepted (Stephen,
2026-10-21).** Runbook §4 item 7, closure part 4, under option A. Closure is complete.
- **The project-use review session.**
  - **Who:** the project-use reviewer `act_01a14020-0465-…`, in a separate, fresh-context session
    (`local_86af1798-…`, Claude Opus 5.5).
  - **What it worked from:** `s3-b15/project-use-reviewer-session-brief.md` and seven inputs, assembled read-only
    from the live store with every hash checked against the ledger:
    - the stored decision `4ed88262…`;
    - the ledger's 84 events;
    - the Task;
    - the return and the scorecard;
    - the A0 D6 text, verbatim from main.

    The manifest is `0961aaed…`, and the context is `ctx_01a15cf9-…`.
  - **What it touched:** it registered nothing, read no other session, and did not touch the governing-record
    draft. Afterwards the inputs were byte-identical.
- **The verdict: approve.**
  - The subject is exact, and every reference matches the ledger.
  - The owner's words are true to the evidence, with no claim beyond it.
  - The reviewer is not the owner, did not register the decision, and held no earlier role.
  - The attestation (`6c13d795…`) passes `check_attestation.py`. It binds the review ID, the subject and the
    notes (`a25025a7…`).
  - **Eight minor findings, none material.** Off the ledger by construction; the Computational-Log keeps them:
    - F1: "seven triggers" counts six triggers plus the rule;
    - F2: "topology passed" is a gate value only;
    - F3: the threshold of 4 is confirmed from the return, not the rubric;
    - F4: this review also ran on Claude Opus 5.5, so the one-model-family limit extends to it;
    - F5: the Task review's inputs-only claim is not checkable from these inputs;
    - F6: D2 also rests on reading the public Ripser repository;
    - F7: two unresolved items (dtype and tolerances; the unversioned diffusion figures) are named by no revisit
      trigger;
    - F8: D6 cost-ceiling compliance is not stated.
- **The rehearsal first.** `batch13.py` ran on the scratch store from 84 to 88 events.
  - **One stop, in my own check.** I expected the use authority's `evidence_refs` to be just the review and record
    IDs. Admission appends its governing-review census: the record's canonical sha256, the review-set digest, the
    store identity and the ledger position.
  - **The fix:** the check now requires the two IDs first and the census's record hash. `batch13.py` is now
    `d09838b9…`.
  - **Rehearsed again:** scratch was reset to 84, and the final runner ran end to end.
  - **The inputs** came from `prepare.py`: the reviewer's agent grant for `RecordScientificReview` in a new ARS actor session (the runner
    submitted the review evidence the attestation binds; runbook §1),
    the owner's grant for `SetArtefactUseAuthority`, and the review intent `b42c22d5…` with evidence
    `{review_id, evidence_refs: [the record ID]}`.
- **What ran live:** `run-s3b13.sh` (sha256 `fb5421a9…`), from 06:08Z, authorized alone. It pinned the
  attestation, the notes and the reviewed draft `0f596221…`, and refused if the record already existed.
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b16/live/`: `s3b13.log` (`a82d5ae9…`),
    `advance-use.json` (`ca86cba7…`, byte-equal to the retry), the JSON and Markdown results (`1f4db7c6…`,
    `9ceafa14…`), `governing-record-placed.json` (`0f596221…`), and the authorization note.
- **The result.**
  - **Before the effects:** the runner checked the attestation, activated the two grants, and placed the
    governing record `arec_01a15cf9-57b3-73fe-809e-392bb169ad59` through the internal
    `GoverningScientificReviewStore.publish`. This is the option A seam: an object, not an event.
  - **The effects:** the live ledger went from 84 to 88 events. `ScientificReviewRecorded` by the project-use
    reviewer, then `ArtefactUseAuthoritySet` (`accepted_for_scope`) by the owner, both on `art_fbd584af-…`.
- **Verified.**
  - The exact retry returned the same receipt and appended nothing.
  - A fresh, read-only process replayed the ledger at 88 events:
    - the review `rev_01a15cf9-57b3-79c0-a463-bb12c57ef5e5` (event 87) is `approved`, by the reviewer, on the
      registered subject, citing the review ID and the record (ID added 2026-10-21, final review m-5);
    - the placed record is the reviewed draft byte for byte, and resolves to canonical sha256 `0f596221…`;
    - the use authority cites the review, the record, the census's matching record hash and this store's
      identity.
  - The route's result reads **accepted**. Its Markdown renders the disposition, the subset qualification and the
    route's own subset sentence, the rationale, all seven limitations, both next gates and the evidence chain.
  - The checkout is clean at M2.
- **Next:** step 4, the result render from a fresh process, with the Task-isolation and PARK-wording checks
  (runbook §5). It needs its own authorization.

**Step 4, live and read-only: the result renders, isolated, with the PARK wording (Stephen, 2026-10-21).** Runbook
§4 item 8 and §5 step 4.
- **The rehearsal first.** `step4.py` (`2353f324…`) passed all ten checks on the scratch store at 88 events, and
  its fingerprints before and after were equal.
- **What ran live:** `run-s4.sh` (sha256 `e84fef7f…`), from 06:18Z, authorized alone. It rendered
  `ars discovery spec result --task-id tsk_01a14850-… --format json` and `--format markdown`, each in a new
  process, plus a result for a freshly minted, unregistered Task ID.
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b17/live/`: `s4.log` (`81b0b2e5…`),
    `result.json` (`1f4db7c6…`), `result.md` (`9ceafa14…`), `other-task-result.json` (`40f16e77…`),
    `step4-checks.json` (`1ce375c0…`), and the authorization note.
- **Task isolation (delta review m-1, held by this step):**
  - the store holds exactly one Task, `tsk_01a14850-…`, and one Attempt;
  - the SOURCE registration's `production` names that Task, Attempt and dispatch;
  - the Task's `portfolio_refs` name exactly the one Candidate `obj_a9ba6213-…`;
  - the result is `accepted`, and its decision cites that Task, Candidate and artefact `art_fbd584af-…`;
  - the other Task ID's result reads `pending`, with no decision and a different artefact identity.
- **The PARK wording:**
  - the decision is the owner's PARK, with no Spike and the disposition `retain_experimental_benchmark`;
  - the disposition and subset statements are the route's own text;
  - the Markdown reads accepted and carries both statements;
  - none of *promot*, *replicat* or *adopt* appears in it.
- **Nothing was written.** The ledger stayed at 88, the object-file fingerprint was unchanged (`784c9f5d…`), and
  the checkout is clean at M2.
- **Reproducible:** both renders are byte-identical to the ones batch 13 made in earlier processes.
- **Next:** step 5, `ars store backup` and `ars store verify-restore`, under its own authorization.

**Step 5, live: the governed backup and an evidence-only restore verification (Stephen, 2026-10-21).** Runbook §5
step 5, same-disk recovery only. This is the initial-root store's first backup and verify-restore (delta review
i-4).
- **What the commands need, beyond the runbook line.**
  - **A grant:** an owner grant for `CreateBackup` and `VerifyRestore` on the `project_store` subject.
  - **A backup request:** 22 exact fields, with at least one external artefact. Each artefact has a canonical
    `art_` ID, an absolute path, a sha256 and availability evidence.
  - **Two schema-valid evidence-store registry files** (`ars://evals/evidence-store-registry`), loaded by the
    real loader:
    - the backup registry names the source, the destination, and the hidden stage sibling;
    - the restore registry carries the hash the backup recorded.
  - **An endpoint-ownership file** in the restore copy.
  - **A `VerifyRestore` command whose payload carries the restore preflight's results.** No public command
    derives that payload, so the runner builds it from the internal, read-only
    `verify_restore_before_writer_lease`, as the WP6.4 test does. `ars store verify-restore` then re-runs the
    full preflight itself before admitting. A **known limit**, read-only, beside option A's seam.
- **The external artefacts** (Stephen accepted the pinned set). Six evidence files outside the store, pinned in
  `s3-b18/external-artefacts.json` (`b5e76d50…`):
  - the outcome review notes and the Task review notes, both cited on the ledger by sha256;
  - the project-use review notes and attestation, the option A basis;
  - the operator's notes and handback.
- **The rehearsal first.** `step5.py` ran on the scratch store from 88 to 91 events, through the genuine
  `backup` and `verify-restore`.
  - **Two stops, in my own comparison code.** A tuple was passed to canonical JSON. The artefact manifest names
    its digest `artefact_hash`. Both were fixed.
  - **Rehearsed again:** after a reset, the final runner (`1d6f5fd1…`) ran end to end and passed all seven
    comparisons.
- **What ran live:** `run-s5.sh` (sha256 `d4764fa3…`), from 06:45Z, authorized alone. It refused if either run
  directory existed.
  - **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b18/live/`: `s5.log` (`60a79570…`),
    `backup.json` (`8d8474e5…`), `verify-restore-command.json` (`debfb7bb…`), `verify-restore.json` (`81e8d03d…`),
    `preflight.json` (`7e26490e…`, `verified`, no failed predicates), `step5-comparisons.json` (`e583e7f2…`), the
    two registry files, and the authorization note.
- **The result.** The live ledger went from 88 to 91 events, all by the owner:
  - the grant activation `agr_01a15d2c-dcc8-…`;
  - `BackupCreated`, receipt `bkr_01a15d2c-dcde-7d16-9aab-fdc21ddf9301`;
  - `RestoreVerified`, recovery evidence `rcv_01a15d2c-dcde-…`, verification only with no cutover.
- **Where the copies are:**
  - the backup is in `C:/Users/steph/TDL-ARS-WP64-Backups/g6-p5-spec01-2026-10-21`, with receipt
    `bkr_01a15d2c-…`. Its `receipt_hash` is `aca75bb6…`, and the receipt file `manifests/backup-receipt.json` has
    sha256 `6532d983…` (clarified 2026-10-21, final review m-7);
  - the same-disk restore copy is in `C:/Users/steph/TDL-ARS-WP64-Restore-Verification/g6-p5-spec01-2026-10-21`;
  - each is 33 MB. The backup snapshot's tail is position 89.
- **The comparisons, all pass:**
  - **identity:** the restore copy's manifests equal the source's, file for file;
  - **ledger:** its 89 events equal the source's first 89, event for event;
  - **artefacts:** its manifest lists exactly the six pinned files by ID and sha256, and each stored file equals
    its source;
  - **bytes:** all 164 object files are byte-identical, all 78 event files are byte prefixes of the source's, and
    the backup and the restore copy are byte-identical apart from the endpoint-ownership file.
- **Verified from a fresh, read-only process.**
  - The ledger is at 91 and replays.
  - `RestoreVerified` cites the receipt, this store's identity and the recovery evidence.
  - The restore copy's ledger replays on its own, equal to the source prefix.
  - The checkout is clean at M2.
- **Next:** step 6 (P5-4):
  - the independent final evidence review;
  - Stephen's recorded closure;
  - the docs-only final PR, merged and not pulled into the checkout;
  - the replay from the frozen checkout at M2.

**Step 6: the independent final evidence review, PASS WITH FINDINGS (Stephen, 2026-10-21).** Runbook §5 step 6,
P5-4, first part.
- **The review session.** A separate, fresh-context session (`local_cff829c8-…`, Claude Opus 5.5), dispatched by
  Stephen. It holds no role in the run, and it reviewed the evidence and record, not the code.
  - **The brief:** `s3-b19/final-reviewer-session-brief.md` (`c1c1a228…`).
  - **The package,** assembled read-only (manifest `25575a21…`):
    - the record at #381's head `21bf67e0`;
    - the live ledger at 91;
    - an index of the 104,531 files under the evidence root, with sha256;
    - the A0 plan;
    - step 4's result and checks;
    - step 5's comparisons.
  - **The report:** `s3-b19/review-output/final-review-report.md` (`aa3d657e…`), with the handback (`f235df49…`).
- **The verdict: PASS WITH FINDINGS.** All eight checks hold:
  - every one of the 91 events falls in exactly one authorized step, with its pinned script, authorization note
    and log, and 615 step files were re-hashed against the index;
  - the recorded counts, actors, grants and IDs match the ledger;
  - the separation holds, on the ledger;
  - the stated outcomes are the ledger's;
  - the disclosed limits are complete;
  - the bounds held: no SPEC-02, no provider or credential trace, nothing written to `TDL-ARS-WP64-Control`, and
    the checkout clean at M2 throughout;
  - there is no claim beyond the evidence;
  - the rehearsal stops are honestly recorded.
- **Findings, and where each was corrected (Stephen: m-2 and m-3 are material record corrections).**
  - **m-1:** the return was equal as parsed JSON to the draft, not byte-equal. Corrected in runbook §3 batch 6. The
    same overstatement in this log's batch 12 ("byte for byte" for the decision's intent) was found while applying
    m-1 and corrected too.
  - **m-2 (material):** non-owner actors acted through ARS actor sessions submitted by the batch runners. Only the
    producer and the three reviewers had separate agent sessions. Corrected in runbook §1 ("How each actor
    acted"), and at the five "own/new session" phrasings in batches 5, 6, 7, 11 and 13.
  - **m-3 (material):** no bar-review session ran; the bar review was the route's fixed OR-106 literals. Added to
    batch 2.
  - **m-4:** batch 11's findings were a selection; F3, F4, F6 and F7 were added.
  - **m-5:** batch 13 now names the review `rev_01a15cf9-…`.
  - **m-6:** "Live steps A1 to A4" now says A4 was a push and a PR, with no script.
  - **m-7:** step 5 now distinguishes the receipt ID, its `receipt_hash` `aca75bb6…`, and the receipt file's
    sha256 `6532d983…`.
  - **m-8:** runbook §3 batch 9 now says six triggers and the rule.
- **Notes, recorded here.**
  - **i-1:** A5 (L5) has no authorization note in `l5/`. Its authorization is recorded only in this log.
  - **i-2:** each batch's authorization note sits in the batch folder (for example `s3-b3/AUTHORIZATION.txt`), not
    in `live/` as the batch blocks say. The folders are offset from the batch numbers: batch 6's evidence is in
    `s3-b7/`, batch 11's in `s3-b12/`, and batch 13's in `s3-b16/`. Each block names its exact path.
- **Where the run's evidence lives, and how to check it** (added 2026-10-21 in answer to review). Every
  `C:/Users/steph/.codex/tmp/g6-p5/…` path in Phase 5's blocks is in the run's evidence root.
  - **Where it is:** on Stephen's owner machine, outside the repository by design. It holds the live logs,
    pinned scripts, authorization notes and review packages, and none of it is committed.
  - **How to check it:** its complete sha256 index, 104,531 files as of position 91, is
    `s3-b19/inputs/evidence-index.json` (`66d45785…`), part of the final review's package (manifest `25575a21…`).
    Any hash a block cites can be checked against it.
  - **What is backed up:** the live store and six external evidence files are in step 5's governed backup.
  - **Access:** the owner's local filesystem. Nothing is published elsewhere.
- **The reviewer's limits.**
  - It read only the inputs and the evidence root.
  - Scratch rehearsals outside the evidence root (all but batch 3's) cannot exclude an unrecorded rehearsal stop.
  - Session compliance (time ceilings, stop rules, the D6 cost ceiling) rests on the sessions' own statements.
  - It too ran on Claude Opus 5.5.
- **A boundary observation, from my check after the session.**
  - The session's deliberate writes were only its two files.
  - Ten git-internal `loose-*.pack` files appeared during it, inside the `.git` folders of two throwaway pytest
    clones under `a4/b/`. This is consistent with git's automatic loose-object maintenance after a git read.
  - No indexed file is missing or changed. The live store stayed at 91, and both checkouts are clean.
- **Next:**
  - Stephen's recorded closure, in his words (a draft is in `s3-b19/closure-draft.md`);
  - the docs-only final PR, merged on GitHub and not pulled into the checkout;
  - the frozen-checkout replay, `run-s6-replay.sh <final PR number>`, under its own authorization.

**06s Gate 6 Phase 5 is closed (Stephen, 2026-10-21).**

**The run.** The bounded live run of the SPEC-01 route on the fresh store `TDL-ARS-G6-Control` ran from genesis
to an accepted project-use result, at 91 events. Each live step was:
- prepared as an exact, hash-pinned script;
- authorized by me alone;
- rehearsed first on a scratch store;
- verified from durable state;
- recorded here.

**How the actors acted.**
- **Who submitted:** the non-owner actors' effects were submitted by the batch runners, each from that actor's own
  operator config and ARS actor session.
- **Who judged:** separate fresh-context sessions did the judgement work, and each draft was submitted unchanged
  and checked by hash:
  - the operator's return;
  - the outcome review;
  - the Task review;
  - the project-use review.
- **The bar review:** it was the route's fixed OR-106 literals. No bar-review session ran.

**The outcome.** A PARK of the Damrich–Berens–Kobak spectral-distance Candidate, mechanical under SPEC-01's bar
(2 + 1 < 4, with four further gates failing). It was independently reviewed and decided by me, with six revisit
triggers and the rule. It is retained as an experimental benchmark candidate only, with no scientific claim, on the
D6 subset: SPEC-02 ran nothing.

**Assurance.**
- **Independent reviews** of the outcome, the Task and the project-use decision all approved.
- **The independent final evidence review** found PASS WITH FINDINGS. Its findings m-1 to m-8 are corrected in the
  record, with m-2 and m-3 treated as material.
- **Recovery:** a governed same-disk backup and an evidence-only restore verification passed their identity,
  ledger, artefact and byte comparisons.
- **The replay:** this record is the docs-only final PR. After it merges, the frozen checkout at M2 replays the run
  (P5-4). That replay is recorded in the Computational-Log, and in the next record update.

**Known limits carried.**
- The 1 h bounded lease (option A): it lapsed and was not released.
- Two internal-API seams:
  - the governing scientific-review record placed through the internal store (option A, batch 13);
  - the verify-restore payload built from the internal, read-only restore preflight (step 5).
- Task acceptance asserting all five criteria, though criterion 5 could only follow it.
- Approve-only reviews, whose findings live off the ledger.
- The bar review as fixed literals.
- One model family across every session, including the reviewers.

**Follow-ups:**
- public writers for the governing scientific-review record and the verify-restore payload;
- the project-use review's F7 items (dtype and tolerance binding; the unversioned diffusion figures) at any SPEC-01
  revisit;
- KAN-103 closes on this record.

**Step 6, live and read-only: the frozen checkout at M2 replays the run after the final PR (Stephen, 2026-10-21).**
P5-4, the last part of step 6. Recorded after #381, as the closure said it would be.
- **What ran:** `run-s6-replay.sh 381` (sha256 `92b21433…`), from 17:46Z, authorized alone. It ran
  `step6_replay.py` (`38b9c8e2…`), rehearsed on the scratch store first.
- **Its preconditions, all met:**
  - #381, the docs-only final PR, is merged as `df5ba1ec`, and GitHub main is `df5ba1ec`, read from the primary
    repository and never from the checkout;
  - the durable checkout is clean on `main` at M2 `4d867d85…`, with one worktree and nothing pulled;
  - the live store is at 91 events.
- **What it did:** each in a new process, from the frozen checkout:
  - `ars replay verify --operator-config …` passed the Gate 6 binding admission, which accepts only the bound SHA,
    and replayed the ledger;
  - `ars discovery spec status`;
  - `ars discovery spec result --task-id tsk_01a14850-… --format json` and `--format markdown`.
- **The checks, eight, all pass:**
  - the replay ran through the ledger's tail, at position 91 with hash `601dd4e5…`;
  - its authority state names the owner and the store's 36 grants;
  - `spec status` reads every SPEC-01 action through closure as completed;
  - the result reads `accepted`, byte-identical to step 4's JSON (`1f4db7c6…`) and Markdown (`9ceafa14…`);
  - nothing was written: the ledger stayed at 91 and the object fingerprint was unchanged (`1744f888…`).
- **The evidence** is in `C:/Users/steph/.codex/tmp/g6-p5/s3-b19/live-replay/`: `s6-replay.log` (`51ce56fb…`),
  `replay-verify.json` (`08ab7c0c…`), `spec-status.json` (`dcf682f5…`), `step6-replay-checks.json`
  (`35fa3c5d…`), the two renders, and the authorization note `s3-b19/AUTHORIZATION-replay.txt`.
- **The rehearsal's one correction.** My first check expected the replay's streams to cover every ledger stream.
  `replay verify` is the control-plane replay, so its coverage is shown by its reported tail position and hash,
  not by Discovery streams. The check was corrected before the live script was pinned.
- **With this, step 6 is complete, and Phase 5's live work is finished.** The durable checkout stays frozen at M2,
  and the store at 91 events.

### P-059 - Protected-surface pin refresh after the 2026-10-02 suite triage

**Date:** 2026-10-03<br>
**Status:** Accepted by Stephen (in-session approval of the triage recommendations,
2026-10-03; confirmed at PR review)<br>
**Context:** A full research_system run at `54808984` found 195 failures on main that no CI lane
saw. Three protected surfaces had gone red because later work changed bytes they pin, without
the matching owner re-acceptance. None of the drifts changes accepted semantics; each is
re-accepted here at exact bytes.<br>
**Decision:**
- **T2 line-ending control artifact.** `.gitattributes` moves from Git blob
  `2c71799535efcdf46828e7b94ebce4f7293a6586` to `8213d721e44bc28b89079cddd5bd573a5dedaaf8`,
  raw SHA-256 `655d2ac34f4ea214c7f0c8c2de04784b9b13d490e350713df8e4edf4127f520f`
  (#274 and #275, 2026-09-08: whole-repo `eol=lf` with binaries declared). This updates
  `.research-system/contracts/wp6-2-t2-schema-identities.yaml`.
- **T2 validator seals.** The same manifest seals its own validators.
  `wp6_2_t2_authority_validation.py` and `wp6_2_t2_expectations.py` were edited at
  `3f82c8df` (2026-08-09) without refreshing their seals, and `wp6_2_t2_expectations.py` is
  edited again by this decision. Both seals are refreshed to the committed bytes.
- **T2 protected WP6.1 trees.** `PROTECTED_TREE_IDENTITIES` becomes commands
  `8a86a0c4921343e6a3afca3f491fad33e9a8a10f` and events
  `058c1d5ddcb9d249916977f12b11768b6d15de0f`. The only edits to protected paths since
  `START_REVISION` are the already-authorized context-packet successors (#222). Two files
  added under protected globs are authorized: `tests/research_system/contracts/test_wp6_1_c1_campaign_census.py`
  (#212) and `.research-system/contracts/wp6-1-artifact-roles.yaml` (#281). Neither changes
  accepted bytes.
- **06h append census.** `accounted_base` must be an ancestor of HEAD. Equality with
  today's merge-base held only on the authoring branch. Two append sites are classified:
  `EventLedger._append_binding_repair_from_validated_service` as
  `guarded_binding_repair_service_producer` (#265; injected one-shot by `binding_guard`, like
  the release and scoped-authority continuations), and `DiscoveryRuntime._submit_authorized` as
  `discovery_command_producer` (#248; appends under the three-root `CompositeWriterLock`
  after scoped-authority resolution, with full command provenance). The accounted runtime
  binding set grows from 218 (`96ac13de...`) to 261
  (`70a6bf2fc871a83db78876d8aad6aa72bb87babc27e08d9f8f626359413e45a6`). The 43 added rows are
  26 WP6.6 Discovery commands and 13 of their events, plus 4 Gate 6 binding-repair
  command/event bindings; no row was removed.<br>
**Binding:** `test_wp6_2_t2_authority_contract.py`, `test_wp6_2_live_issue_contract.py` and
`smoke/test_wp6_1_06h_append_path_closure.py` check every value above at exact bytes.<br>
**Boundary:** This re-accepts recorded bytes only. It activates nothing, changes no schema or
runtime behaviour, and does not touch the WP6.3 private assurance pack (handled separately by
restoring the pinned skill bytes) or any external control store.

### P-060 - 06t: split the artefact-authority pins by what they assert, after Gate 6 closes

**Date:** 2026-10-07<br>
**Status:** Accepted by Stephen (Option C ticked in 06t §7; activation timing decided in session,
2026-10-07). Deferred: no contract change is made until the slice is dispatched.<br>
**Context:** `.research-system/contracts/artefact-authority-interface.v1.yaml` (06i, interface digest
`dd085c86fdd5f673e294df42a655aa51404ad8fac5232b52c50787f81edfb998`, `candidate_state: proposed`) pins
47 call sites to exact source paths, so a pure module move under `research_system/` is a contract
amendment. 06t analysed the four pin classes and the trade-offs (observation
`2026-08-12-file-map-frozen-since-wp1`, limb 2; carried onto main by #335). At `e5179b57` the contract,
both identity manifests and `test_06i_stage_a_candidate.py` are unchanged since `ced524b`, and the
interface is still `candidate_state: proposed`.<br>
**Decision:**
- **Option C.** The 38 call-graph pins (11 `dispatch_bindings`, 25 `transitive_root_bindings`,
  2 `public_export` entrypoints) become symbol-bound. The discovered path is kept as a non-normative
  `observed_in` field that the test does not compare. The 9 storage pins
  (`direct_storage_inventory` and `dynamic_object_store_kind_exclusions`) stay path-bound, because for
  them the module is the privilege boundary. Option B (symbol-bind everything) is rejected.
- **Required control.** The same change adds the invariant that every pinned `owner.qualname` has
  exactly one definition site under `research_system/`, with a negative control that writes a second
  definition into a `tmp_path` module and watches the check fail. Without it, Option C does not ship.
- **Scope of the slice.** `test_06i_stage_a_candidate.py`, the interface YAML and both identity
  manifests (`.research-system/contracts/candidates/06i-artefact-authority-v1/` and
  `.research-system/contracts/artefact-authority-v1/`), regenerated in lockstep. No `research_system/`
  change. The resulting candidate identity is presented to Stephen for review. The adjacent finding in
  06t §6 (the command-token assertion in `_cli_handlers_and_tokens`) is not part of this decision.
- **Activation: not before Gate 6 closes.** The slice is a standalone job, dispatched by Stephen only
  after 06s §8 reports Gate 6 INTEGRATED. Phase 4c certifies a main SHA whose CI currency group includes
  `test_06i_stage_a_candidate.py`; Phase 5 step 1 binds the reviewed main SHA; and Phase 5 step 6
  requires documentation-only governed-code descent from that SHA to final main. A contract and test
  change merged in between would either change the reviewed subject or break that descent check.
- **Hold.** The 06i candidate does not leave `candidate_state: proposed` before the slice lands.
  Amending after acceptance would supersede an owner-accepted authority object. If an acceptance of the
  06i candidate is proposed first, this decision is raised to Stephen before it proceeds.<br>
**Binding:** None mechanized now, and none is needed before activation. The hold is guarded by the
acceptance act itself: accepting the candidate changes the pinned bytes, which regenerates both
identity manifests and needs Stephen's review, where this entry applies. At activation, the uniqueness
invariant and its negative control are the slice's binding.<br>
**Boundary:** Adds nothing to Gate 6 or to the 06s §4 closure contract, and is not a Gate 7
prerequisite. Changes no contract, manifest, test or runtime behaviour now. No Jira issue yet; the
delivered 06i capability is KAN-96 (Done, under KAN-65).

### P-061 - SPEC-01 after the PARK: continue at a later gate, with the retry terms fixed now

**Date:** 2026-10-21<br>
**Status:** Accepted by Stephen (in chat, 2026-10-21). OD-5 to OD-8 are the proposals PD-1 to PD-4 that he
confirmed on 2026-10-17. This entry records scope only. It builds, authorizes and runs nothing, and writes
nothing to any store.<br>
**Context:** P-058 closed 06s Gate 6 Phase 5 with the owner's PARK of the SPEC-01 Candidate
`obj_a9ba6213-1073-7b78-ab6f-552cfdf9c2b7` (Decision `dec_1c6c1254-da10-716b-8def-c72f4232bddf`, "Step 3
batch 9"). The PARK carries six revisit triggers and the revisit rule, seven strings in all:
- **R1:** D1 is resolved by an owner decision on which noise model SPEC-02 reproduces: the bit-faithful code
  fixture, or the paper's independent noise as a declared variant.
- **R2:** D2 is resolved by binding the authoritative Ripser engine commit, with its build flags and a written
  diagram-equivalence check.
- **R3:** a no-GPU kNN backend is chosen, with an exact tie rule and its equivalence to the keops path specified
  as a SPEC-02 preflight.
- **R4:** an owner-accepted survey estimand and representation freeze, including a verified BHPS/USoc
  crosswalk for the feature block and the frozen representation's ambient dimension. If that dimension is low
  enough that Euclidean PH is not expected to fail, the Candidate is recorded as redundant instead.
- **R5:** one owner-accepted, non-redundant primary claim.
- **R6:** an explicit connected-components check is recorded as a SPEC-02 amendment, so that disconnected
  graphs are blocked rather than silently repaired.
- **The rule:** revisit SPEC-01 only when R1 to R6 all hold. R1 to R3 alone would make only a synthetic
  reproduction runnable, which is not a contribution.

The operator's owner decision sheet (`owner-decision-sheet.md`, sha256 `624200af…`, 2026-10-17) set out a retry
route and the decisions OD-1 to OD-8. The issued route package `SPEC-GATE6-RUN-V1` (`fad7c5a9…`) lists
OR-008 to OR-011 (cancellation, revisit and retry) under `intentional_exclusions`: outside the one-time route,
with an honest terminal-for-now branch for a partial. Phase 5 ends at `decide_spec_01`, closure and the result
(runbook §4; P-056, P-058). 06q describes `request_spec_01_revisit`, `authorize_spec_01_retry` (RETRY),
`request_spec_01_retry` and a new Assay as the general route. It is not this run's authority.<br>
**Decision:**
1. **Continue: yes, at a later gate.** Not a Gate 6 extension. Phase 5, D6 and the P-058 closure stay closed as
   recorded. The continuation is Gate 7+ intake work. How that gate carries the parked Candidate and the
   Decision `dec_1c6c1254-…` into its own route is for its intake to specify. No revisit, retry or SPEC-02
   action is taken in the Gate 6 store.
2. **The route requirement.** The later gate needs a new route-package version that admits OR-009, OR-010 and
   OR-011, with its own authority review and the same closed-input discipline. The retry Assay needs its own
   Task and Attempt, with a running return window, because the SPEC-01 Task is closed and its Attempt ended.
   This is a requirement on that gate. Nothing is built or authorized here.
3. **OD-1 to OD-8 are accepted now,** each with its wording and effect from the decision sheet §2. They bind the
   later gate's retry. A change to any of them needs a superseding decision.
   - **OD-1, sequencing.** The retry route, with the PARK return left unchanged (`operator-return-draft.json`,
     sha256 `568447c7…`). *Effect:* fixes enter through the retry Assay, not by editing the return. *Why:* the
     frozen return stays the evidence of what the reviewer and the owner judged.
   - **OD-2 (D1), fixture.** A bit-faithful code fixture: `get_toy_data` at `145efcde` is used verbatim,
     including the shared re-seeded basis/noise stream and the `linspace` endpoint. *Effect:* the coupling is
     declared as a deviation from the paper's stated noise model. SPEC-02 asserts the generator's identity and
     does not "fix" it. The claim boundary must say the fixture reproduces the published figures' generator,
     not the paper's prose noise model. *Why:* it reproduces the generator behind the published figures, and the
     deviation from the prose is declared instead of silently corrected.
   - **OD-3 (D2), PH engine.** Ripser `representative-cycles` head `4d61b79efe086c5feef14ff059c8f4744bbd1519`,
     target `ripser-representatives`, Z/2. *Effect:* the paper's "140670f" is recorded as an erroneous pin, a
     master-line commit that cannot produce the parsed representative output. *Why:* only this head produces
     the output the route parses.
   - **OD-4, claim.** The primary claim is robustness only (the operator's proposal, sheet §4). *Effect:*
     novelty is expected to stay about 1 in the retry. *Why:* the claim is methodological, not a labour-market
     finding, so it needs no substantive survey result to stand.
   - **OD-5 (PD-1, R3), kNN backend.** Exact brute-force float64 on CPU, ties broken by lower index, self
     removed by index (amendment §A4). *Effect:* the owner-decision limb of R3 is on record. Correctness is
     shown by the blocking A4 preflight inside the SPEC-02 attempt. *Why:* it needs no GPU, and the tie rule
     makes equivalence checkable.
   - **OD-6 (PD-2), toolchain.** LLVM clang++ 21.1.0, `-std=c++11 -O3 -ffast-math -DNDEBUG`. *Effect:* binds
     the A3 build. *Why:* that is clang's spelling of `-Ofast`, written out because clang deprecates the alias.
     MSVC 2022 is installed and was not chosen.
   - **OD-7 (PD-3), Python.** CPython 3.10.4 with numpy 1.23.5 and scipy 1.10.0, in a dedicated venv prepared
     before the run. Block if any version is unavailable. *Effect:* binds the A6 environment. *Why:* it matches
     the source's numerics. None is installed now, so the venv is a prerequisite of the retry.
   - **OD-8 (PD-4), vendoring.** The source functions are vendored verbatim, by blob and line range, with only
     edits E1 to E3. *Effect:* binds A1. *Why:* `utils/dist_utils.py` imports `umap`, `openTSNE` and
     `vis_utils` at module top, so it cannot be imported on the envelope. The only substantive change is the
     kNN call inside `get_sknn`.
4. **`correct_spec_01_source` is not needed.** D1 and D2 correct the *binding* (which generator, which engine).
   They do not touch the registered source identity `145efcde673f1a1897eff250b77221d26c34c479`.
5. **SPEC-02 v1.2.0: adopt, plus R6.** SPEC-02 v1.2.0 (draft `spec-02-amendment-draft-v1.2.0.md`, sha256
   `de29763b…`) becomes the governed successor to v1.1.0, subject to three things: its own review, a contract
   version, and an update to the route package's source binding. It is amended to add R6's explicit
   connected-components check. This entry records the decision only. The amendment work is a follow-up, and
   the draft, which sits outside the repository, is not part of this PR.
6. **R4, the crosswalk step: required, with the later gate.** A separate documentation-only task
   (`/bhps-wave-crosswalk`, no microdata) verifies the coding of the 9-state activity and income block across
   BHPS and USoc. It is authorized only when the later gate opens. It is not authorized now.
7. **R5, the redundancy test: the rule now, the value later.**
   - **The rule:** a numeric threshold on the frozen 20-dimensional representation's PCA spectrum (the share of
     variance beyond the leading components) must be pre-registered in the vault before any survey PH is
     computed.
   - **Below the threshold:** the claim is recorded as redundant and the Candidate is KILLed for redundancy.
   - **Above it:** the robustness comparison proceeds.
   - **The value** is set in that later pre-registration, not here, and never on outcomes chosen post hoc.
   - **Scope:** this is the objective form of R4's redundancy clause and of R5's "non-redundant". The 20
     dimensions are the operator's proposed default (`trajectory_tda/embedding/ngram_embed.py`: 9 states,
     unigrams plus bigrams, 90 raw dimensions, `StandardScaler`, PCA to 20, `random_state = 42`). Owner
     acceptance of that freeze is still R4's open item, and the rule applies to the representation as it is
     frozen.

**Standing after this entry.** None of R1 to R6 is declared met.
- **R1 to R3:** their owner-decision limbs are now on record (OD-2, OD-3 with OD-6 and OD-7, OD-5). The written
  checks they name (the fixture identity check, the diagram-equivalence check and the kNN preflight, sheet
  amendment §A2 to §A4) live in SPEC-02 v1.2.0, which is not yet adopted.
- **R4:** open. It needs the crosswalk and owner acceptance of the estimand and freeze.
- **R5:** partly open. The claim is accepted (OD-4) and the redundancy rule is locked. The threshold value is
  open.
- **R6:** open. It needs the amendment in point 5.
- **The revisit rule** is not met.

**Expected arithmetic.** This is the producer's projection, not a score commitment. With a robustness-only
claim, novelty is expected to stay about 1. A retry PROMOTEs only if data feasibility reaches 3 and every gate
passes. Data feasibility at 3 needs survey access verified in-session, the feature block crosswalk-verified,
and the environment bound. Otherwise the retry PARKs again. The retry operator scores on the evidence it
holds.<br>
**Carried into the later gate's intake (cited, not decided here):**
- **Retry identity model.** P-058 4b-1 (2026-09-17) decided one Task and one running Attempt across a retry
  lineage, and rejected a new Attempt per Assay. Phase 5 ended that Attempt and closed the Task. Point 2's
  own Task and Attempt differ from that rule, and the route-package review is where the difference is settled.
- **Revisit on a scored-Assay PARK.** P-058 4b-1 reproduced on scratch that a scored-Assay PARK cannot be
  revisited by OR-009, and that the revisit predicate is read from one route-issued SOURCE observation whose
  facts contain every requirement verbatim, with `observe_source` recording a single fact. The seven strings
  above are not a single fact.
- **The project-use review's F7 items** (P-058 closure): dtype and tolerance binding, and the unversioned
  diffusion figures, named by no revisit trigger. They are due at any SPEC-01 revisit. OD-5 fixes float64 for
  the kNN only, so this entry does not treat F7 as resolved. The other P-058 follow-ups are not restated.<br>
**Binding:** None mechanized now, because this entry records scope and requirements for a gate that is not
open. The enforcement artifacts are the follow-ups named below, each with its own review: the SPEC-02 v1.2.0
contract version and binding test, the route-package version's authority review, and the vault pre-registration
of the R5 threshold before any survey PH is computed.<br>
**Boundary:** Docs only; no store writes. This does not amend P-056, P-058 or the Phase 5 closure, reopens no
Gate 6 action, and registers nothing in the Gate 6 store's ledger. OD-1 to OD-8 are recorded here as owner
decisions and are not events in that ledger. The later gate's intake decides how they are bound into its route.
No survey data is touched. No Jira issue yet.<br>
**Follow-ups (none authorized by this entry):**
- Gate 7+ intake: the new route-package version, its authority review, and the retry Task and Attempt (point 2).
- SPEC-02 v1.2.0: review, contract version, R6 amendment, and the route package's source-binding update
  (point 5).
- The R4 crosswalk task, when the later gate opens (point 6).
- The R5 threshold pre-registration, before any survey PH (point 7).

## Decision protocol

Each future decision entry must record:

- identifier and date;
- status: proposed, accepted, superseded, or rejected;
- decision and rationale;
- evidence references;
- affected specifications;
- migration consequence;
- superseding decision, where applicable.
