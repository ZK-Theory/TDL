# Agentic Research System Working Folder

**Status:** W1–W5 and Gate 3 accepted under P-027–P-030; P0 plan suite written and review pending; runtime remains gated<br>
**Created:** 2026-06-27  
**Working title:** Agentic Research System (ARS)  
**First evidence base:** TDL trajectory-TDA research programme  
**Intended scope:** Mathematical, statistical, computational, and social research projects beyond TDA

## Purpose

This folder is the durable planning workspace for moving from the current APM-based workflow to a more reliable, generalisable agentic research system.

The transition began near the end of the current Paper 1 Phase 1 run. T1.28 remains an active, potentially multi-day APM computation and the two current papers retain legacy authority. Under P-026, that closeout gates legacy migration but not successor design. ARS will proceed through W3–W5, foundation-critical W6–W8 gates, a narrow production-intended foundation, and a greenfield pilot on the first paper initiated after the two current APM-managed papers.

The objective is not to automate research judgment away. It is to make agent activity easier to bound, inspect, reproduce, challenge, and recover while retaining explicit human authority over methodological and paper-level decisions.

## Working-folder map

| File | Responsibility |
|---|---|
| [00-master-transition-plan.md](00-master-transition-plan.md) | Complete programme charter, findings, target system, transition sequence, risks, and success criteria |
| [01-current-system-evidence.md](01-current-system-evidence.md) | Auditable evidence and source register behind the diagnosis |
| [02-design-and-deliverables-roadmap.md](02-design-and-deliverables-roadmap.md) | Design work packages, dependencies, review gates, and intended deliverables |
| [03-decisions-and-open-questions.md](03-decisions-and-open-questions.md) | Accepted directions, assumptions requiring confirmation, and bounded design decisions |
| [04-parallel-specification-and-foundation-pilot-plan.md](04-parallel-specification-and-foundation-pilot-plan.md) | P-026 parallel lanes, specification sequence, foundation scope, gates, and greenfield pilot boundary |
| [05-p0-materialization-and-foundation-implementation-plan.md](05-p0-materialization-and-foundation-implementation-plan.md) | Review-pending Gate 4 master plan for the 37-case P0 closure and narrow production-intended foundation |
| [proposals/wp6-2-t2-cost-grant-authority-and-versioning-ruling-2026-07-22.md](proposals/wp6-2-t2-cost-grant-authority-and-versioning-ruling-2026-07-22.md) | P-037 accepted ruling for the T2 CommandService transition family and non-destructive schema versioning; no implementation authority |
| [proposals/wp6-2-t2-r1-remediation-authority-ruling-2026-07-22.md](proposals/wp6-2-t2-r1-remediation-authority-ruling-2026-07-22.md) | Proposed P-038 ruling closing the R1 receipt, idempotency, secret-boundary, identity, cost, and W7 completeness gaps; pending exact owner acceptance |
| [implementation/README.md](implementation/README.md) | Ordered index for the P0 work packages, the Gate 5 suite, and the draft WP6 suite |
| [implementation/06-wp6-gate6-readiness-and-integration-plan.md](implementation/06-wp6-gate6-readiness-and-integration-plan.md) | Owner-approved WP6 launch-basis plan at exact reviewed revision `fe5f1d40`: Gate A closure (A2–A8), Gate 6 preflight, W11 portfolio/Discovery integration, and consolidation sequencing |
| [implementation/06a-wp6-1-runtime-task-lifecycle-plan.md](implementation/06a-wp6-1-runtime-task-lifecycle-plan.md) | Owner-approved WP6.1 dispatch-plan content at exact reviewed revision `fe5f1d40`: rich Task/ScopeDefinition runtime and W8 operator surface; future materialization gates remain |
| [implementation/06b-wp6-2-live-capability-plan.md](implementation/06b-wp6-2-live-capability-plan.md) | Owner-approved WP6.2 dispatch-plan content at exact reviewed revision `fe5f1d40`: live adapters, parity, threshold policy, and evaluated model profiles; future evidence gates remain |
| [implementation/06d-wp6-1-owner-source-catalogue.md](implementation/06d-wp6-1-owner-source-catalogue.md) | Normative WP6.1 104-row complete-binding catalogue with versioned schema identities, authority subjects, atomic claim, and correction mapping |
| [implementation/06e-wp6-2-live-replacement-map.md](implementation/06e-wp6-2-live-replacement-map.md) | Normative WP6.2 literal 51-row frozen-predecessor/live-successor map |
| [implementation/06f-wp6-2-p1-activation-contract.md](implementation/06f-wp6-2-p1-activation-contract.md) | Normative WP6.2 independent expected-source and descriptor-hash contract for the 11+43 P1 closure |
| [transition/W0-legacy-closeout-transition-manifest-2026-06-28.md](transition/W0-legacy-closeout-transition-manifest-2026-06-28.md) | Commit-anchored legacy closeout inventory, no-migration boundary, and eval-fixture shortlist |
| [transition/W0-legacy-closeout-transition-addendum-2026-06-29.md](transition/W0-legacy-closeout-transition-addendum-2026-06-29.md) | Dated currency update for T1.6, live T1.28 state, legacy bus backport, and A-001/A-002 status |
| [design/README.md](design/README.md) | Structure and entry criteria for the forthcoming design specifications |
| [design/01-system-architecture.md](design/01-system-architecture.md) | W1 component ownership, canonical/projected state, trust and filesystem boundaries, dependency direction, and `.apm/` compatibility architecture |
| [design/02-task-event-and-artifact-schema.md](design/02-task-event-and-artifact-schema.md) | W2 identities, commands, atomic events, lifecycle state machines, messages, artefacts, reviews, decisions, and deterministic replay |
| [design/03-context-memory-and-retrieval.md](design/03-context-memory-and-retrieval.md) | W3 immutable context packets/addenda, manifests, hard budgets, retrieval, memory provenance, staleness, and independence inputs |
| [design/04-agent-roles-and-model-routing.md](design/04-agent-roles-and-model-routing.md) | W4 role profiles, risk, capability evidence, routing, independence, provider support, fallback, and multi-agent refusal |
| [design/05-research-assurance-and-independent-review.md](design/05-research-assurance-and-independent-review.md) | W5 assurance requirements, domain packs, two-key validity, proof obligations, review, Partial/negative evidence, and claim promotion |
| [design/06-evaluation-observability-and-audit.md](design/06-evaluation-observability-and-audit.md) | W6 v0.3 executable evaluation interface accepted under P-030; catalogue/reservations retained |
| [design/06a-w3-retrieval-fixture-addendum-2026-06-30.md](design/06a-w3-retrieval-fixture-addendum-2026-06-30.md) | P-028 reservation of W3 retrieval fixtures F-025–F-030 and mandatory-closure sizing precondition |
| [design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md](design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md) | P-029 reservation of W4/W5 routing and assurance fixtures F-031–F-038 |
| [design/06c-gate3-foundation-critical-interface-manifest-2026-07-01.md](design/06c-gate3-foundation-critical-interface-manifest-2026-07-01.md) | Gate 3 v0.2 identity, ownership, two-stage ordering, failure, and freeze manifest accepted under P-030 |
| [design/07-runtime-adapters-and-policy-parity.md](design/07-runtime-adapters-and-policy-parity.md) | W7 v0.2 canonical policy, provider adapter, receipt, parity, token-accounting, and upgrade interfaces; accepted under P-030 |
| [design/08-resource-checkpoint-and-operations.md](design/08-resource-checkpoint-and-operations.md) | W8 v0.2 proportional resources, leases, checkpoints, stop/resume, recovery, backup, and operator interfaces; accepted under P-030 |
| [reviews/adversarial-first-pass-review-2026-06-29.md](reviews/adversarial-first-pass-review-2026-06-29.md) | Independent review of the plan and W1/W2/W6 first pass; preserved unchanged |
| [reviews/adversarial-review-reconciliation-2026-06-29.md](reviews/adversarial-review-reconciliation-2026-06-29.md) | Stephen-approved dispositions, evidence-timing reconciliation, and integration authority |
| [reviews/w1-w2-w6-review-acceptance-2026-06-30.md](reviews/w1-w2-w6-review-acceptance-2026-06-30.md) | Dated acceptance record closing the W1/W2/W6 review gates without authorizing implementation |
| [reviews/adversarial-W3-context-review-2026-06-30.md](reviews/adversarial-W3-context-review-2026-06-30.md) | Independent W3 adversarial review; preserved unchanged |
| [reviews/adversarial-W3-review-reconciliation-2026-06-30.md](reviews/adversarial-W3-review-reconciliation-2026-06-30.md) | Stephen-approved W3 finding dispositions and integration boundary |
| [reviews/adversarial-W4-W5-review-2026-06-30.md](reviews/adversarial-W4-W5-review-2026-06-30.md) | Independent joint review of W4/W5 v0.1; `accept_with_required_changes` |
| [reviews/adversarial-W4-W5-review-reconciliation-2026-06-30.md](reviews/adversarial-W4-W5-review-reconciliation-2026-06-30.md) | Stephen-approved W4/W5 v0.2 finding dispositions and P-029 acceptance boundary |
| [reviews/adversarial-gate3-W6-W7-W8-review-2026-07-01.md](reviews/adversarial-gate3-W6-W7-W8-review-2026-07-01.md) | Joint Gate 3 adversarial review; `accept_with_required_changes` |
| [reviews/adversarial-gate3-W6-W7-W8-review-reconciliation-2026-07-01.md](reviews/adversarial-gate3-W6-W7-W8-review-reconciliation-2026-07-01.md) | Stephen-approved finding dispositions and P-030 Gate 3 acceptance boundary |
| [reviews/w3-v0.2-delta-review-2026-06-30.md](reviews/w3-v0.2-delta-review-2026-06-30.md) | Bounded integration check closing the W3 findings and preserving downstream gates |
| [reviews/adversarial-wp6-plan-suite-remediation-review-2026-07-17.md](reviews/adversarial-wp6-plan-suite-remediation-review-2026-07-17.md) | First WP6 remediation re-review; portable evidence for P-035 sequencing/composition decisions |
| [reviews/adversarial-wp6-plan-suite-remediation-r2-review-2026-07-17.md](reviews/adversarial-wp6-plan-suite-remediation-r2-review-2026-07-17.md) | R2 WP6 remediation review identifying the binding-contract work in this revision |
| [reviews/adversarial-wp6-plan-suite-remediation-r3-review-2026-07-17.md](reviews/adversarial-wp6-plan-suite-remediation-r3-review-2026-07-17.md) | R3 WP6 remediation review identifying strict-schema, independent-oracle, authority, concurrency, and selector gaps |
| [reviews/adversarial-wp6-plan-suite-remediation-r4-review-2026-07-17.md](reviews/adversarial-wp6-plan-suite-remediation-r4-review-2026-07-17.md) | R4 WP6 remediation review identifying RuleEvaluation ownership and Dispatch-bound Task integrity gaps |
| [reviews/adversarial-wp6-plan-suite-remediation-r5-review-2026-07-17.md](reviews/adversarial-wp6-plan-suite-remediation-r5-review-2026-07-17.md) | R5 independent approval of exact WP6 remediation commit `fe5f1d40bc8f05f061317c677b5891cea0711249`; zero findings |
| [reviews/adversarial-wp6-2-t2-authority-addendum-r1-review-2026-07-22.md](reviews/adversarial-wp6-2-t2-authority-addendum-r1-review-2026-07-22.md) | Durable R1 `rework_required` verdict and manager triage for exact T2 authority-addendum candidate `1144d6a6`; four Critical and three Major findings |

## Handover prompts

| Prompt | Purpose |
|---|---|
| [handoffs/01-next-session-continuation-prompt.md](handoffs/01-next-session-continuation-prompt.md) | Historical pre-review continuity brief; superseded by handoff 03 |
| [handoffs/02-adversarial-review-prompt.md](handoffs/02-adversarial-review-prompt.md) | Executed adversarial-review brief; retained as review provenance |
| [handoffs/03-post-review-continuation-prompt.md](handoffs/03-post-review-continuation-prompt.md) | W3 authoring continuity brief; retained as provenance after P-028 acceptance |
| [handoffs/04-p0-review-and-implementation-handover-prompt.md](handoffs/04-p0-review-and-implementation-handover-prompt.md) | Fresh-agent entry point for the P0 plan review gate and explicitly approved foundation implementation |

## Governing constraints

1. Preserve the strongest existing controls: pre-registration, contracts, provenance, worktree isolation, date-suffixed outputs, non-overwrite rules, partial/escalation semantics, and user decision locks.
2. Do not migrate or reinterpret active Phase 1 or Phase 2 results merely to fit the new system.
3. Separate research validity from software correctness. Passing code tests is necessary but insufficient.
4. Separate design, implementation, verification, and acceptance authority for epistemically consequential work.
5. Keep task state and evidence durable outside any one model session or provider-specific harness.
6. Generate provider adapters from canonical policy rather than maintaining divergent Claude and Codex copies by hand.
7. Route models by evaluated capability and epistemic risk. Cost savings must not weaken R2/R3 mathematical work.
8. Prefer focused, independently testable components over a monolithic framework.
9. Adopt new infrastructure only where historical failure evidence shows it earns its maintenance cost.
10. Retain human-readable, version-controlled artefacts even if indexed views or a database are later added.

## Current working conclusion

The recommended path is **evolutionary APM replacement**:

- retain the useful filesystem bus semantics and research-assurance machinery;
- introduce immutable task identity, append-only events, typed artefacts, acknowledgements, attempts, and explicit state transitions;
- compile bounded role-specific context rather than loading the entire programme history;
- add independent scientific verification and agent-system evaluation;
- provide a domain-neutral core with TDA-specific assurance packs layered on top.

This is preferable to either patching the current mutable files indefinitely or adopting a networked agent framework wholesale.

The approved delivery path is specification → narrow permanent foundation → greenfield paper pilot. W1–W5, the W6 catalogue/addenda, and Gate 3 are accepted under P-027–P-030. The P0 materialization and narrow-foundation implementation plan suite is written and review pending; no runtime follows until Stephen accepts its exact scope. T1.28 and the two current papers remain outside that path except as dated evidence sources.

## Change discipline

- Planning decisions are recorded in `03-decisions-and-open-questions.md` before being assumed by a design specification.
- Each design specification must identify which accepted decision and evidence item it implements.
- No implementation begins until the relevant specification has passed its review gate.
- No active APM task is used as a migration experiment.
- Significant changes to this folder should preserve dated decision history rather than silently rewriting earlier conclusions.
