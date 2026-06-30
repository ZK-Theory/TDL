# Design Specifications

This directory contains the bounded design specifications derived from the master transition plan. A specification marked `review_pending` is a proposal, not implementation authority. P-026 authorizes the next design sequence while T1.28 remains active; it does not bypass any specification review gate.

## Entry criteria

A specification may be written when:

1. its governing decisions are accepted or explicitly marked as assumptions;
2. its evidence inputs are listed in the evidence register;
3. its boundaries and consumers are identified;
4. it has a review owner independent of its primary author for R2/R3 research logic;
5. its acceptance tests can be stated before implementation.

## Planned specification set

1. `01-system-architecture.md`
2. `02-task-event-and-artifact-schema.md`
3. `03-context-memory-and-retrieval.md`
4. `04-agent-roles-and-model-routing.md`
5. `05-research-assurance-and-independent-review.md`
6. `06-evaluation-observability-and-audit.md`
7. `07-runtime-adapters-and-policy-parity.md`
8. `08-migration-compatibility-and-pilot.md`
9. `09-operations-recovery-and-maintenance.md`
10. `10-project-template-and-domain-packs.md`

The filenames define decomposition, not permission to implement. Each specification will pass its own review gate before an implementation plan is produced.

## Current status

| Specification | Status | Outcome |
|---|---|---|
| [01-system-architecture.md](01-system-architecture.md) | `accepted` | Revision 0.3 passed review on 2026-06-30; implementation remains subject to the downstream P-026 gates |
| [02-task-event-and-artifact-schema.md](02-task-event-and-artifact-schema.md) | `accepted` | Revision 0.3 passed review on 2026-06-30; no runtime/schema implementation follows yet |
| [03-context-memory-and-retrieval.md](03-context-memory-and-retrieval.md) | `review_pending` | Revision 0.1 freezes the proposed context/independence interface for W4/W5 and awaits bounded written-specification review |
| `04-agent-roles-and-model-routing.md` | `queued` | Begins after the W3 shared interface is reviewable |
| `05-research-assurance-and-independent-review.md` | `queued` | May proceed alongside W4 only after the shared W3 interface is frozen |
| [06-evaluation-observability-and-audit.md](06-evaluation-observability-and-audit.md) | `accepted_catalogue` | Revision 0.2 initial 40-fixture catalogue passed review on 2026-06-30; its foundation-critical executable slice follows W3–W5 |
