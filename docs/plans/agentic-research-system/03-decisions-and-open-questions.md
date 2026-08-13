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
not a live parallel campaign. Executable work is tracked beneath KAN-65,
KAN-57 and KAN-22. WP6.3 and WP6.4 are integrated. Gate 6 still requires WP6.1
R1, the final WP6.1 proof and final assembled Gate 6 acceptance; the Gate 9
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

## Decision protocol

Each future decision entry must record:

- identifier and date;
- status: proposed, accepted, superseded, or rejected;
- decision and rationale;
- evidence references;
- affected specifications;
- migration consequence;
- superseding decision, where applicable.
