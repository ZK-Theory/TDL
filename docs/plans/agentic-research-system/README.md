# Agentic Research System Working Folder

**Status:** Adversarial first-pass review integrated into W0/W1/W2/W6; bounded Manager review pending; implementation remains prohibited  
**Created:** 2026-06-27  
**Working title:** Agentic Research System (ARS)  
**First evidence base:** TDL trajectory-TDA research programme  
**Intended scope:** Mathematical, statistical, computational, and social research projects beyond TDA

## Purpose

This folder is the durable planning workspace for moving from the current APM-based workflow to a more reliable, generalisable agentic research system.

The transition is being planned at the end of the current Paper 1 Phase 1 run. T1.28 is treated as the expected final Phase 1 computational task, subject to confirmation from the live APM state. Phase 2 work already developed in parallel must be preserved. The new system will therefore be introduced through compatibility layers and a bounded pilot rather than by migrating active work in place.

The objective is not to automate research judgment away. It is to make agent activity easier to bound, inspect, reproduce, challenge, and recover while retaining explicit human authority over methodological and paper-level decisions.

## Working-folder map

| File | Responsibility |
|---|---|
| [00-master-transition-plan.md](00-master-transition-plan.md) | Complete programme charter, findings, target system, transition sequence, risks, and success criteria |
| [01-current-system-evidence.md](01-current-system-evidence.md) | Auditable evidence and source register behind the diagnosis |
| [02-design-and-deliverables-roadmap.md](02-design-and-deliverables-roadmap.md) | Design work packages, dependencies, review gates, and intended deliverables |
| [03-decisions-and-open-questions.md](03-decisions-and-open-questions.md) | Accepted directions, assumptions requiring confirmation, and bounded design decisions |
| [transition/W0-legacy-closeout-transition-manifest-2026-06-28.md](transition/W0-legacy-closeout-transition-manifest-2026-06-28.md) | Commit-anchored legacy closeout inventory, no-migration boundary, and eval-fixture shortlist |
| [transition/W0-legacy-closeout-transition-addendum-2026-06-29.md](transition/W0-legacy-closeout-transition-addendum-2026-06-29.md) | Dated currency update for T1.6, live T1.28 state, legacy bus backport, and A-001/A-002 status |
| [design/README.md](design/README.md) | Structure and entry criteria for the forthcoming design specifications |
| [design/01-system-architecture.md](design/01-system-architecture.md) | W1 component ownership, canonical/projected state, trust and filesystem boundaries, dependency direction, and `.apm/` compatibility architecture |
| [design/02-task-event-and-artifact-schema.md](design/02-task-event-and-artifact-schema.md) | W2 identities, commands, atomic events, lifecycle state machines, messages, artefacts, reviews, decisions, and deterministic replay |
| [design/06-evaluation-observability-and-audit.md](design/06-evaluation-observability-and-audit.md) | Revised W6 catalogue: F-001–F-024 and S-001–S-016, grader independence, provenance, privacy, calibration, and change gates |
| [reviews/adversarial-first-pass-review-2026-06-29.md](reviews/adversarial-first-pass-review-2026-06-29.md) | Independent review of the plan and W1/W2/W6 first pass; preserved unchanged |
| [reviews/adversarial-review-reconciliation-2026-06-29.md](reviews/adversarial-review-reconciliation-2026-06-29.md) | Stephen-approved dispositions, evidence-timing reconciliation, and integration authority |

## Handover prompts

| Prompt | Purpose |
|---|---|
| [handoffs/01-next-session-continuation-prompt.md](handoffs/01-next-session-continuation-prompt.md) | Historical pre-review continuity brief; superseded by handoff 03 |
| [handoffs/02-adversarial-review-prompt.md](handoffs/02-adversarial-review-prompt.md) | Executed adversarial-review brief; retained as review provenance |
| [handoffs/03-post-review-continuation-prompt.md](handoffs/03-post-review-continuation-prompt.md) | Current continuity brief for bounded review of the reconciled W0/W1/W2/W6 package |

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

## Change discipline

- Planning decisions are recorded in `03-decisions-and-open-questions.md` before being assumed by a design specification.
- Each design specification must identify which accepted decision and evidence item it implements.
- No implementation begins until the relevant specification has passed its review gate.
- No active APM task is used as a migration experiment.
- Significant changes to this folder should preserve dated decision history rather than silently rewriting earlier conclusions.
