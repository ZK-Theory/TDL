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
| [01-system-architecture.md](01-system-architecture.md) | `manager_review_pending` | Revision 0.3 integrates the adversarial amendments and P-026 gate split; Manager confirmation remains pending, while T1.28 continues to gate legacy migration only |
| [02-task-event-and-artifact-schema.md](02-task-event-and-artifact-schema.md) | `manager_review_pending` | Revision 0.3 integrates concurrency, compatibility, independence, referent, retention, and replay amendments; foundation implementation still requires Manager confirmation |
| `03-context-memory-and-retrieval.md` | `next_authorized` | W3 is the next bounded specification under P-026; it must freeze the context/independence interface consumed by W4/W5 |
| `04-agent-roles-and-model-routing.md` | `queued` | Begins after the W3 shared interface is reviewable |
| `05-research-assurance-and-independent-review.md` | `queued` | May proceed alongside W4 only after the shared W3 interface is frozen |
| [06-evaluation-observability-and-audit.md](06-evaluation-observability-and-audit.md) | `manager_review_pending` | Revision 0.2 contains the 40-fixture catalogue; its foundation-critical executable slice follows W3–W5 |
