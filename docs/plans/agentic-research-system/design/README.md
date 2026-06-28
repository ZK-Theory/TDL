# Design Specifications

This directory contains the bounded design specifications derived from the master transition plan. A specification marked `review_pending` is a proposal, not implementation authority.

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
| [01-system-architecture.md](01-system-architecture.md) | `manager_review_pending` | Stephen approved 2026-06-28; Manager confirmation and post-T1.28 reconciliation remain pending |
| [02-task-event-and-artifact-schema.md](02-task-event-and-artifact-schema.md) | `review_pending` | Schema and lifecycle semantics specified; implementation and migration prohibited pending review |
| [06-evaluation-observability-and-audit.md](06-evaluation-observability-and-audit.md) | `initial_catalogue_review_pending` | 30-fixture catalogue specified; executable W6 design deferred |
