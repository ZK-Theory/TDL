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
8. `08-resource-checkpoint-and-operations.md`
9. `09-migration-compatibility-and-pilot.md`
10. `10-project-template-and-domain-packs.md`

The filenames define decomposition, not permission to implement. Each specification will pass its own review gate before an implementation plan is produced.

## Current status

| Specification | Status | Outcome |
|---|---|---|
| [01-system-architecture.md](01-system-architecture.md) | `accepted` | Revision 0.3 passed review on 2026-06-30; implementation remains subject to the downstream P-026 gates |
| [02-task-event-and-artifact-schema.md](02-task-event-and-artifact-schema.md) | `accepted` | Revision 0.3 passed review on 2026-06-30; no runtime/schema implementation follows yet |
| [03-context-memory-and-retrieval.md](03-context-memory-and-retrieval.md) | `accepted` | Revision 0.2 passed adversarial review and reconciliation under P-028; shared W4/W5/W7 interface frozen |
| [04-agent-roles-and-model-routing.md](04-agent-roles-and-model-routing.md) | `accepted` | Revision 0.2 passed joint review and reconciliation under P-029; implementation remains gated |
| [05-research-assurance-and-independent-review.md](05-research-assurance-and-independent-review.md) | `accepted` | Revision 0.2 passed joint review and reconciliation under P-029; implementation remains gated |
| [06-evaluation-observability-and-audit.md](06-evaluation-observability-and-audit.md) | `accepted` | Revision 0.3 executable interface accepted under P-030; earlier catalogue/reservations retained |
| [06a-w3-retrieval-fixture-addendum-2026-06-30.md](06a-w3-retrieval-fixture-addendum-2026-06-30.md) | `accepted_reservation` | P-028 reserves F-025–F-030 and closure sizing; executable evidence remains deferred |
| [06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md](06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md) | `accepted_reservation` | P-029 reserves F-031–F-038; executable evidence remains deferred |
| [06c-gate3-foundation-critical-interface-manifest-2026-07-01.md](06c-gate3-foundation-critical-interface-manifest-2026-07-01.md) | `accepted_interface_manifest` | Revision 0.2 closes identity, two-stage ordering, stage, failure, and evidence coherence under P-030 |
| [07-runtime-adapters-and-policy-parity.md](07-runtime-adapters-and-policy-parity.md) | `accepted` | Revision 0.2 accepted under P-030 with bound-provider/wrapper accounting and canonical identity bindings |
| [08-resource-checkpoint-and-operations.md](08-resource-checkpoint-and-operations.md) | `accepted` | Revision 0.2 accepted under P-030 with proportional operational profiles and non-circular grant binding |
