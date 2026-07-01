# Gate 3 Manifest — Foundation-Critical W6/W7/W8 Interfaces

**Date:** 2026-07-01<br>
**Status:** Draft complete; joint Gate 3 review pending<br>
**Manifest version:** 0.1<br>
**Applies to:** W6 v0.3 draft, W7 v0.1 draft, W8 v0.1 draft, accepted W1–W5 and W6 addenda 06a/06b<br>
**Design authority:** P-026, P-028, P-029 and Stephen's approved Gate 3 conceptual design<br>
**Implementation authority:** None; this manifest creates no schemas, fixture packages, graders, adapters, leases, processes, checkpoints, runtime, migration, P0 result, or `.research-system/` state

## 1. Purpose

This manifest is the small joint contract that prevents W6 evaluation, W7 provider adaptation and W8 operations from freezing internally coherent but mutually incompatible interfaces.

It does not own domain semantics. It records:

- which specification owns each shared field;
- allowed dependency direction and lifecycle order;
- exact cross-spec identities and evidence passed between components;
- distinction between fixture priority and materialization gate stage;
- normative end-to-end review scenarios;
- freeze criteria and the boundary before executable P0 planning.

## 2. Deliverable set

| Deliverable | Scope | Status in this pass |
|---|---|---|
| W6 v0.3 | Executable fixture/trace/grader/evaluation/coverage/release interfaces | `review_pending` |
| W7 v0.1 | Canonical policy, provider adapters, commands/receipts and parity | `review_pending` |
| W8 v0.1 | Resources, feasibility, leases, processes, checkpoints and recovery | `review_pending` |
| 06c v0.1 | Shared ownership, ordering, scenarios and freeze criteria | `review_pending` |
| P0 materialization plan | Exact fixture packages, runner, implementation sequence and calibration | Deferred until written Gate 3 review accepts this set |

## 3. Dependency direction

```text
W1/W2 canonical command + event authority
  -> W3 immutable context candidate and two token gates
  -> W4 eligible route and verifier-feasibility witness
  -> W5 accepted assurance requirement
  -> W7 provider command translation
  -> W8 resource grant / lease / process / checkpoint evidence
  -> W7 normalized provider receipt
  -> W6 trace + graders + coverage + release decision
  -> W5 assurance/result decision through W2 authority
```

Dependencies may be read in the reverse direction for validation, but authority does not reverse. W6 cannot create provider or operational facts. W7/W8 cannot publish canonical events or fixture verdicts. W5 cannot choose provider/resource routes.

## 4. Shared identity bindings

Every Gate 3 evaluation run binds, where applicable:

```text
task_id / task_revision
command_id / expected_control_position
dispatch_id / attempt_id / execution_epoch
assurance_requirement_id / hash
context_candidate_id / packet_hash / addendum_hashes
route_decision_id / profile_eval_id / routing_snapshot_id
canonical_policy_bundle_id / adapter_profile_id
provider_command_id / provider_receipt_id
resource_grant_id / execution_lease_id / process_identity_id
checkpoint_manifest_id / stop_record_id / recovery_evidence_id
fixture_id / revision / evaluation_run_id
trace_envelope_id / grader_result_ids
coverage_manifest_id / release_gate_decision_id
```

An omitted inapplicable binding is explicit with rationale. A missing applicable binding is incomplete evidence.

## 5. Field ownership matrix

| Field family | Sole semantic owner | Consumers | Prohibited reinterpretation |
|---|---|---|---|
| Command/event/state position, idempotency, authority | W2 | W6/W7/W8 | Provider/ops success cannot create state |
| Context fragments, bytes/hashes, token gates, exclusions | W3 | W6/W7 | Adapter cannot rewrite managed content |
| Capability/risk route, profile, independence, routing snapshot | W4 | W6/W7/W8 | Cost/availability cannot lower requirements |
| Assurance lanes, proof/review/human gates | W5 | W6/W7 | Adapter/eval cannot drop or compensate |
| Fixture, trace, grader, coverage, release verdict | W6 | W4/W5/W7/W8 | Producer/provider/ops cannot self-grade |
| Canonical policy projection, adapter capability, provider command/receipt, parity | W7 | W4/W6/W8 | Receipt cannot decide acceptance |
| Resource/grant/lease/process/checkpoint/stop/recovery/backup | W8 | W4/W6/W7 | Operational evidence cannot decide science |

If two documents define the same semantic field differently, the joint gate fails; 06c does not choose a winner silently.

## 6. Version and currency rules

A downstream record is current only when every bound upstream major schema is supported and every exact revision/hash remains effective.

- Major schema changes require explicit migration/compatibility or block consumption.
- Minor additions are compatible only when consumers preserve unknown fields and no required semantic is missing.
- Provider/adapter/tokenizer/tool changes stale W7 evidence and affected W4 eligibility.
- Host/boot/process/resource/checkpoint changes stale W8 feasibility or continuation evidence.
- Fixture/oracle/grader/policy changes create new W6 revisions; they never rewrite prior verdicts.
- Any stale critical binding expires dependent provider commands and evaluation runs.

## 7. Lifecycle ordering

Required order for an R2/R3 producing flow:

1. accepted Task/design/assurance requirement and effective source position;
2. current W3 context candidate and both token gates;
3. W4 eligible producer route plus required verifier-route witness;
4. active W7 policy/adapter capability and parity evidence;
5. W8 feasibility evidence and compatible resource grant/lease;
6. W7 provider command issue and normalized receipt;
7. W8 process/checkpoint/stop/recovery evidence as applicable;
8. W6 trace completion and non-compensable grader verdicts;
9. W5 assurance/result review and separate W2 decision;
10. claim candidacy/promotion only through the separate P-005 path.

No later success repairs an earlier absent authority. Resume revalidates steps 1–5 and creates a new execution epoch.

## 8. Failure precedence

When multiple failures occur, all remain visible. The terminal operational action follows the strongest applicable constraint:

1. security/restricted-data/authority violation -> deny/stop and preserve minimal evidence;
2. invalid canonical identity/schema/hash -> block consumption;
3. failed W3/W4/W5 hard gate -> no provider/resource dispatch;
4. W7 parity/accounting/receipt failure -> no dispatch/delivery satisfaction;
5. W8 resource/lease/checkpoint/stop uncertainty -> block or Partial/recovery path;
6. W6 fixture/grader failure -> no release or acceptance;
7. diagnostic cost/latency degradation -> report without overriding correctness.

One subsystem may add a stronger block but cannot downgrade another subsystem's failure.

## 9. Priority versus `gate_stage`

W6 v0.3 preserves accepted fixture `priority` and adds an orthogonal planning field:

```text
gate3_spec_review
gate3_interface_evidence
gate5_foundation_release
pre_pilot
```

- `priority` expresses severity/release importance (`P0` or `P1`).
- `gate_stage` expresses when a fixture/scenario must be materialized and passed.
- A P1 scenario may be required early to prove an interface seam without becoming P0.
- A P0 fixture remains non-compensable even if its executable run belongs to Gate 5 because the implemented surface does not yet exist at Gate 3.
- Any omission from a change gate requires a coverage-manifest rationale and capability restriction; priority is never edited to make a gate pass.

This resolves the initial-catalogue ambiguity where S-001–S-010 appeared in early materialization order without an accepted P0 label.

## 10. Deferred P0 planning rule

This specifications-only pass creates normative examples, not executable fixture packages.

After joint review accepts W6/W7/W8/06c, the P0 implementation plan must:

1. enumerate the exact dependency closure of accepted P0 fixtures for the proposed interface surface;
2. add any P1/unprioritized scenarios required at `gate3_interface_evidence` without relabeling their priority;
3. state which cases require a reference simulator versus the later foundation runtime;
4. define package paths, schemas, graders, commands, calibration samples and expected evidence;
5. demonstrate pre-control failure and post-control success before activation;
6. stop as Partial when a required interface/runtime does not yet exist rather than fabricating evidence.

The plan cannot authorize foundation runtime implementation; that remains Gate 4 after combined-interface review.

## 11. Normative scenario A — R2 production and verification

Preconditions:

- accepted R2 assurance requirement with producer-independent scope confirmation;
- W3 producer/reviewer contexts;
- producer route and eligible verifier witness;
- W7 adapter profiles and parity evidence;
- W8 producer/verifier resource feasibility.

Required trajectory:

1. producer command binds exact context/route/policy/grant;
2. provider receipt and W8 process evidence bind actual attempt;
3. produced artefact is immutable and separately referenced;
4. final verifier route recomputes independence against actual producer;
5. W6 grades command/receipt/trace/property evidence;
6. W5 both keys pass before Manager acceptance.

Forbidden: producer self-review, witness-as-final-review, missing receipt, operational success as scientific pass.

## 12. Normative scenario B — provider outage

A required provider becomes unavailable after route selection.

Required result:

- W7 records outage without choosing fallback;
- W8 releases or re-evaluates reserved resources safely;
- W4 reroutes under the original risk/assurance/context/permission/independence requirements;
- W3 provider accounting is recomputed for the new bound candidate;
- if no eligible route exists, the Task waits/blocks with evidence;
- W6 grades F-032/S-016 behavior.

Forbidden: lower family diversity, omitted context, broadened permission, stale receipt or cost-driven downgrade.

## 13. Normative scenario C — long-run guardrail and checkpoint resume

A feasibility projection exceeds the accepted threshold or a running job reaches its stop rule.

Required result:

- W8 benchmark counts hidden prerequisites and validates units/backend/scaling;
- threshold crossing emits stop/input-required/Partial, not final science;
- stop confirmation proves provider/process/children/writers terminated;
- checkpoint manifest binds design/code/environment/input/representation/RNG/work units;
- resume creates a new epoch and revalidates W3–W8 currency;
- W6 grades F-007–F-009 and S-003/S-004 trajectories.

Forbidden: benchmark-only full work, invalid worker extrapolation, silent continuation or checkpoint overwrite.

## 14. Normative scenario D — crash and restore

The command writer or host crashes around publication/receipt.

Required result:

- W2 idempotency and atomicity yield zero or one committed command batch;
- W7 reconciliation returns the original receipt or uncertain status without duplicate state;
- W8 detects process/orphan/checkpoint state and prevents unproven adoption;
- backup restore proves store/project identity, chain, snapshot/tail and external artefacts before writer lease;
- W6 grades S-001/S-009/S-011/S-012/S-014 evidence.

Forbidden: divergent ledgers, last-write-wins, partial projection publication or writer lease on unverified restore.

## 15. Normative scenario E — restricted-data denial

A provider/tool route requests raw restricted data or a broader root than authorized.

Required result:

- W4/W7/W8 effective-permission intersection denies issue;
- no raw data, credentials or sensitive arguments enter provider command/trace;
- W6 privacy grader receives minimized denial evidence;
- Task remains blocked/input-required without widening permission.

Forbidden: convenience upload, secret-bearing trace, opaque “provider handled securely” attestation or missing denial receipt.

## 16. Review evidence matrix

| Design claim | Specification owner | Required review evidence |
|---|---|---|
| Fixture/trace/grader schemas are sufficient | W6 | Field closure against F-001–F-038/S-001–S-016 and scenarios A–E |
| Claude/Codex enforce equivalent critical semantics | W7 | Semantic coverage matrix with explicit gaps and non-compensable consequences |
| Long runs can stop/resume/recover mechanically | W8 | Lifecycle/compatibility review against F-007–F-009 and S-003/S-004/S-009/S-014 |
| Cross-spec ordering has no temporal inversion | 06c | Scenario sequence and failure-precedence audit |
| Units are dimensionally coherent | W3/W6/W7/W8 | Separate tokenizer counts; declared time/work/resource units and conversions |
| P0 is not conflated with materialization stage | W6/06c | Catalogue/plan crosswalk preserving accepted priority |
| No active research state is used | All | Filesystem diff and no-runtime/no-migration declaration |

## 17. Interface freeze criteria

Gate 3 written interfaces may be frozen only when:

- every shared field has one semantic owner and all consumers reference it consistently;
- identity/version/hash/currency behavior is explicit;
- algorithm ordering matches state-machine ordering;
- missing/unknown/stale evidence fails closed;
- W7/W8 provide every field W6 needs without W6 synthesizing facts;
- W6 priority and `gate_stage` are non-overlapping;
- normative scenarios A–E have deterministic required/forbidden trajectories;
- privacy/redaction/retention boundaries are consistent;
- P0 implementation remains a separately reviewed follow-on plan;
- no `.research-system/`, fixture, adapter, process or migration state is created.

## 18. Joint adversarial review questions

1. Does any field have two owners or no owner?
2. Does any later receipt/verdict retroactively repair an earlier missing authority?
3. Are reference/provider token counts or runtime/work-unit estimates compared across incompatible units?
4. Can W7 or W8 self-grade evidence consumed by W6?
5. Can W6 infer a provider/resource fact absent from normalized evidence?
6. Can `gate_stage` be abused to demote a P0 failure?
7. Can a provider outage, sleep, crash or restore weaken independence, context or authority?
8. Do scenarios A–E expose every material shared-interface seam?

## 19. Review gate

06c can move from `review_pending` to `accepted_interface_manifest` only when Stephen confirms after bounded joint review that:

- [ ] W6/W7/W8 responsibilities and dependency direction are non-circular.
- [ ] Shared IDs/fields have one semantic owner and consistent consumers.
- [ ] Lifecycle and failure ordering contain no temporal inversion.
- [ ] Units/tokenizers/resource quantities are dimensionally explicit.
- [ ] Missing, stale, unknown and unsupported evidence fails closed.
- [ ] Priority and `gate_stage` cannot weaken each other.
- [ ] Scenarios A–E are complete enough to drive the P0 plan.
- [ ] Privacy and restricted-data denial are enforced across all interfaces.
- [ ] The P0 plan and foundation implementation remain separately gated.
- [ ] No runtime, migration, fixture materialization, active APM change or research claim is introduced.

## 20. Outcome

**Outcome:** `REVIEW_PENDING — 06c v0.1 binds the foundation-critical W6/W7/W8 interfaces; freeze and P0 planning remain gated`.

The next action is a bounded joint adversarial review of W6 v0.3, W7 v0.1, W8 v0.1 and this manifest. Only after acceptance should a writing plan specify executable P0 materialization.
