# Gate 3 W6/W7/W8 Adversarial-Review Reconciliation

**Date:** 2026-07-01<br>
**Status:** Accepted by Stephen on 2026-07-01<br>
**Review:** `adversarial-gate3-W6-W7-W8-review-2026-07-01.md` at commit `7c11eb8`<br>
**Subjects:** W6 v0.3, W7 v0.2, W8 v0.2, and 06c v0.2<br>
**Decision authority:** P-030<br>
**Implementation authority:** None

## 1. Reconciliation outcome

The review verdict `accept_with_required_changes` is technically supported. The three Major findings identify real 06c seam defects, subject to one correction: W4 already defines `routing_evidence_snapshot_id` with prefix `res_`. Reconciliation therefore aligns 06c and W7 to that existing identity rather than creating the review's proposed second identity.

Stephen approved the reconciliation design on 2026-07-01, including the two-stage dependency model and the single-schema proportional W8 operational profile.

| Finding | Disposition | Reconciled location | Result |
|---|---|---|---|
| G3-M1 two-stage dependencies linearized | Accept with semantic refinement | 06c sections 3, 7, 11, 16–17 | W5/W7/W8 pre-route inputs, candidate-bound provider gate, W7 pre-issue revalidation, and post-route W8 grant are explicit |
| G3-M2 incompatible `gate_stage` enumerations | Accept | W6 section 26; 06c sections 9–10, 17 | W6 closed enumeration is canonical and mapped to programme gates |
| G3-M3 identity drift / claimed missing routing identity | Accept naming drift; reject new identity | 06c section 4; W7 section 9; existing W4 section 6.1 | Consumers use W4's existing `routing_evidence_snapshot_id` / `res_`; trace/grader/profile names match owners |
| G3-m4 token rule/evidence ownership | Accept | 06c section 5 | W3 owns the gate rule; W7 owns provider count/capacity/wrapper evidence |
| G3-m5 proportional R0/R1 operations | Accept recommended one-schema form | W8 section 11.1 and section 12 | `trivial`, `bounded`, and `long_running` profiles share one schema with explicit applicability |
| G3-m6 wrapper/system token reserve | Accept | W7 section 13 | Fixed overhead reduces usable input; variable wrapper material consumes reserve; combined capacity fails closed |
| G3-m7 F-010 double ownership | Accept | W8 section 24 | W8 covers only unauthorized operational expansion; W5/W6 retain scientific/provenance oracle |

## 2. G3-M1 — two-stage dependency closure

06c no longer presents Gate 3 as a single linear chain. The accepted order is:

1. W2 authority and the W5 assurance requirement are accepted.
2. W3 compiles the context candidate and applies the reference-token gate.
3. W7 supplies current provider/adapter/capability/parity/tokenizer evidence and W8 supplies preliminary feasibility plus the operational-risk floor.
4. W4 evaluates each candidate, including the candidate-specific W3 provider-capacity gate, W8 constraints, W6 currency, and verifier feasibility.
5. W4 records the selected route and verifier witness.
6. W7 revalidates the selected route, rendered content, exact count or accepted evaluated upper bound, wrapper reserve, and policy currency immediately before issue.
7. W8 grants selected-route resources and a lease.
8. W7 issues the command and normalizes the receipt; W8 retains ongoing operational evidence.
9. W6 grades immutable evidence; W5/W2 retain result and acceptance authority.

This refines the review proposal in two ways required by accepted upstream specifications:

- W5 requirement acceptance precedes W4 because W4 consumes that requirement.
- P-028/W3 permit either an exact bound-provider count or a W7-evaluated conservative upper bound. Reconciliation does not introduce an exact-tokenizer-only requirement.

Scenario A now asserts the separate reference-gate, pre-route evidence, candidate-bound provider gate, pre-issue revalidation, and post-route grant points. The review matrix and freeze criteria test the same order.

An adjacent circularity was removed: W8 `ResourceRequest` now binds Task/dispatch/attempt/route plus normalized provider/runtime requirements, not a required `provider_command_id`. The later W7 command can therefore bind the already-issued grant/lease without either contract depending on a future record.

## 3. G3-M2 — canonical `gate_stage`

W6 remains the sole semantic owner. The closed v0.3 values are:

```text
interface_review
p0_materialization
foundation_release
pilot_promotion
```

06c maps them to Gate 3 written review, post-Gate-4 P0 implementation/calibration, Gate 5 release, and Gate 6 pilot promotion. The draft aliases `gate3_spec_review`, `gate3_interface_evidence`, `gate5_foundation_release`, and `pre_pilot` are invalid. Priority remains independent and cannot be edited to change evidence timing.

## 4. G3-M3 — identity coherence

06c now uses the exact owner-defined names:

- W4: `model_eval_profile_id`, `routing_evidence_snapshot_id` / `res_`;
- W6: `trace_id`, `grader_result_id`, and `fixture_revision`;
- W7: `adapter_profile_id`, `adapter_capability_id`, provider command/receipt identities;
- W8: request/grant/lease/process/checkpoint/stop/recovery identities.

The review's assertion that routing snapshot identity was undefined was not supported by W4 section 6.1, which already contained `routing_evidence_snapshot_id res_...`. No W4 erratum or second prefix is introduced. 06c adds a definition-resolution table and requires every future shared binding to resolve to one owner catalogue.

## 5. Proportional W8 profile decision

P-025 is implemented through one operational schema, not separate fast-path contracts:

- `trivial`: seconds-long R0/R1 work; command-scoped lease and terminal-receipt closure; benchmark/checkpoint/periodic-heartbeat/recovery groups are explicit `not_applicable` with policy and rationale;
- `bounded`: finite process/output work with policy-selected heartbeat, stop, and checkpoint groups;
- `long_running`: full feasibility, heartbeat, process, checkpoint, stop/recovery, and backup obligations as applicable.

No universal permissive duration or cadence default is created. A trivial operation that exceeds its declared envelope, spawns a process, opens a durable writer, or becomes uncertain must stop or re-request under a stronger profile. The live grant is never widened silently.

## 6. Acceptance effect

Stephen's approval and P-030:

1. accept W6 v0.3, W7 v0.2, W8 v0.2, and 06c v0.2;
2. close the Gate 3 joint-interface review and reconciliation;
3. preserve the accepted W1–W5 decisions and F-001–F-038/S-001–S-016 catalogue/reservations;
4. make the next gate a separately reviewed P0 materialization and narrow-foundation implementation plan;
5. authorize no runtime, executable fixture, adapter, process, checkpoint, migration, pilot, active APM mutation, result reinterpretation, or research claim.

## 7. Verification boundary

Reconciliation must verify:

- the retired `gate_stage` values and drifted identity names are absent from active Gate 3 contracts;
- every 06c identity resolves to its owner catalogue;
- W5 requirement, W3 token gates, W7 evidence/revalidation, W8 floor/grant, and W4 route appear in dependency order;
- wrapper/system token accounting reduces usable capacity and consumes reserve without comparing tokenizer units;
- trivial operational applicability is explicit and cannot widen a live grant;
- package links/statuses agree and no `.research-system/` or runtime state is created.

**Outcome:** `ACCEPTED_RECONCILIATION — Gate 3 W6/W7/W8/06c interfaces close under P-030; P0 planning is the next separate gate`.
