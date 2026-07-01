# Gate 3 Manifest — Foundation-Critical W6/W7/W8 Interfaces

**Date:** 2026-07-01<br>
**Status:** Accepted under P-030 after joint adversarial review and reconciliation<br>
**Manifest version:** 0.2<br>
**Applies to:** Accepted W6 v0.3, W7 v0.2, W8 v0.2, W1–W5, and W6 addenda 06a/06b<br>
**Design authority:** P-026, P-028, P-029, P-030, and Stephen's approved Gate 3 reconciliation<br>
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

| Deliverable | Scope | Status after reconciliation |
|---|---|---|
| W6 v0.3 | Executable fixture/trace/grader/evaluation/coverage/release interfaces | `accepted` under P-030 |
| W7 v0.2 | Canonical policy, provider adapters, commands/receipts and parity | `accepted` under P-030 |
| W8 v0.2 | Resources, feasibility, leases, processes, checkpoints and recovery | `accepted` under P-030 |
| 06c v0.2 | Shared ownership, two-stage ordering, scenarios and freeze criteria | `accepted_interface_manifest` under P-030 |
| P0 materialization plan | Exact fixture packages, runner, implementation sequence and calibration | Next separately reviewed planning gate; not authorized by P-030 |

## 3. Dependency direction

Gate 3 is a dependency DAG with two-stage W3, W7, and W8 participation; it is not a single-pass pipeline. The authoritative producing flow is:

```text
W1/W2 Task, command, authority and source position
  + W5 accepted AssuranceRequirement
  + W3 compiled context candidate and reference-token gate
  + W7 current provider/model/adapter/tokenizer/capability/parity evidence
  + W8 preliminary feasibility and operational-risk floor
    -> W4 candidate evaluation
       - candidate-specific W3 provider-capacity gate using W7 exact count
         or an accepted evaluated upper-bound counter
       - W8 operational constraints and resource availability
       - W6 evaluation currency and required verifier feasibility
    -> W4 RouteDecision plus verifier-route witness
    -> W7 selected-route pre-issue revalidation
       - policy/parity/currentness, rendered hash, provider accounting,
         wrapper/system reserve, and both W3 token gates
    -> W8 selected-route ResourceGrant and ExecutionLease
    -> W7 ProviderCommand issue and ProviderReceipt
    -> W8 process/checkpoint/stop/recovery evidence as applicable
    -> W6 trace, graders, coverage and ReleaseGateDecision
    -> W5 assurance/result review through W2 decision authority
    -> claim candidacy only through the separate P-005 path
```

W5 requirement acceptance, W7 provider evidence, and W8 preliminary risk/feasibility are inputs to W4; they do not follow route selection. W8 grant/lease remains downstream of the selected route. W3 reaches `compiled` after the reference gate, but reaches `validated` only after W4 binds a candidate and W7 supplies an exact count or accepted evaluated upper bound. W7 revalidates the selected route immediately before issue; accepted W3 semantics do not require an exact tokenizer when an evaluated upper-bound counter is the accepted evidence.

Dependencies may be read in reverse for validation, but authority does not reverse. W6 cannot create provider or operational facts. W7/W8 cannot publish canonical events or fixture verdicts. W5 cannot choose provider/resource routes.

## 4. Shared identity bindings

Every Gate 3 evaluation run binds, where applicable, the exact identifiers defined by its owning specification:

```text
task_id / task_revision
command_id / expected_control_position
dispatch_id / attempt_id / execution_epoch
assurance_requirement_id / hash
context_candidate_id / packet_hash / addendum_hashes
route_decision_id / model_eval_profile_id / routing_evidence_snapshot_id
canonical_policy_bundle_id / adapter_profile_id / adapter_capability_id
provider_command_id / provider_receipt_id
resource_request_id / resource_grant_id / execution_lease_id / process_identity_id
checkpoint_manifest_id / stop_record_id / recovery_evidence_id
fixture_id / fixture_revision / evaluation_run_id
trace_id / grader_result_id
coverage_manifest_id / release_gate_decision_id
```

A run may bind multiple `grader_result_id` values, but the field identity remains singular. An omitted inapplicable binding is explicit with rationale. A missing applicable binding is incomplete evidence.

### 4.1 Definition-resolution self-check

| Identity family | Defining owner/section | Consumer rule |
|---|---|---|
| Task/command/dispatch/attempt | W2 identity catalogues | 06c never aliases canonical IDs |
| Assurance requirement | W5 assurance contract | W4/W6/W7 bind exact revision/hash |
| Context candidate/packet/addendum | W3 context contracts | W4/W7/W6 preserve candidate and content hashes |
| Route/profile/routing evidence | W4 section 6.1 and route contracts | Consumers use `model_eval_profile_id` and `routing_evidence_snapshot_id` / `res_` |
| Policy/adapter/provider | W7 section 5 and contracts | Consumers use W7 names without provider-native aliases |
| Resource/process/checkpoint/recovery | W8 section 5 and contracts | W7/W6 bind W8 IDs, not filenames or PIDs |
| Fixture/trace/grader/coverage/release | W6 sections 19–25 | Consumers use `trace_id` and `grader_result_id` exactly |

Every binding added to this section must resolve to one defining owner catalogue before interface freeze. A naming mismatch is reconciled to the existing owner; it does not create a second identity.

## 5. Field ownership matrix

| Field family | Sole semantic owner | Consumers | Prohibited reinterpretation |
|---|---|---|---|
| Command/event/state position, idempotency, authority | W2 | W6/W7/W8 | Provider/ops success cannot create state |
| Context fragments, bytes/hashes, reference-token gate, provider-capacity rule, exclusions | W3 | W4/W6/W7 | Adapter cannot rewrite managed content or redefine the gate |
| Capability/risk route, profile, independence, routing-evidence snapshot | W4 | W6/W7/W8 | Cost/availability cannot lower requirements |
| Assurance lanes, proof/review/human gates | W5 | W6/W7 | Adapter/eval cannot drop or compensate |
| Fixture, trace, grader, coverage, release verdict | W6 | W4/W5/W7/W8 | Producer/provider/ops cannot self-grade |
| Canonical policy projection, adapter capability, provider command/receipt, provider tokenizer/count/usable-capacity/wrapper evidence, parity | W7 | W3/W4/W6/W8 | Receipt cannot decide acceptance; count evidence cannot redefine the W3 rule |
| Preliminary operational-risk floor/feasibility and selected-route resource/grant/lease/process/checkpoint/stop/recovery/backup | W8 | W4/W6/W7 | Operational evidence cannot decide science |

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

1. accept the W2 Task/design authority and W5 assurance requirement at an effective source position;
2. compile the W3 candidate, apply the reference-token gate, and preserve it as unissued;
3. obtain current W7 provider/adapter/capability/parity/tokenizer evidence and W8 preliminary feasibility plus operational-risk floor;
4. have W4 evaluate each candidate against the W5 requirement, W3 candidate-specific provider-capacity gate, W7 evidence, W8 constraints, W6 currency, and verifier feasibility;
5. record the W4 RouteDecision and verifier-route witness;
6. have W7 revalidate the selected route, rendered payload hash, exact-or-evaluated-upper-bound provider count, wrapper/system reserve, policy/parity, and currentness before issue;
7. obtain the W8 selected-route ResourceGrant and ExecutionLease;
8. issue the W7 ProviderCommand and retain its normalized ProviderReceipt;
9. retain W8 process/checkpoint/stop/recovery evidence as applicable;
10. complete the W6 trace and non-compensable grader verdicts;
11. complete W5 assurance/result review and a separate W2 decision;
12. permit claim candidacy/promotion only through the separate P-005 path.

No later success repairs an earlier absent authority. Resume revalidates steps 1–7 and creates a new execution epoch. W7 provider evidence and W8 risk/feasibility appear before W4; W8 grant/lease appears only after route selection.

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

W6 v0.3 is the sole owner of the closed `gate_stage` enumeration:

```text
interface_review
p0_materialization
foundation_release
pilot_promotion
```

| Programme point | Canonical `gate_stage` | Meaning |
|---|---|---|
| Gate 3 joint written-interface review | `interface_review` | Normative design/scenario evidence; no executable fixture result is implied |
| After Gate 4 plan approval, during P0 implementation/calibration | `p0_materialization` | First executable fixture/runner/calibration evidence |
| Gate 5 foundation evaluation | `foundation_release` | Evidence required before the foundation can release |
| Gate 6 greenfield-pilot preflight and promotion | `pilot_promotion` | Evidence required before pilot evidence/claims may advance |

- `priority` expresses severity/release importance (`P0` or `P1`).
- `gate_stage` expresses the earliest programme point at which the fixture/scenario must provide the applicable evidence.
- A P1 scenario may be required at `interface_review` as a normative seam proof without becoming P0.
- A P0 fixture remains non-compensable even when executable evidence begins at `p0_materialization` or `foundation_release`.
- Any omission from a change gate requires a coverage-manifest rationale and capability restriction; priority is never edited to make a gate pass.

The retired draft values `gate3_spec_review`, `gate3_interface_evidence`, `gate5_foundation_release`, and `pre_pilot` are invalid aliases and must not appear in coverage data.

## 10. Deferred P0 planning rule

This specifications-only pass creates normative examples, not executable fixture packages.

With W6/W7/W8/06c accepted under P-030, the separately reviewed P0 implementation plan must:

1. enumerate the exact dependency closure of accepted P0 fixtures for the proposed interface surface;
2. add any P1/unprioritized scenarios required at `p0_materialization` without relabeling their priority; normative `interface_review` scenarios remain design evidence until materialized;
3. state which cases require a reference simulator versus the later foundation runtime;
4. define package paths, schemas, graders, commands, calibration samples and expected evidence;
5. demonstrate pre-control failure and post-control success before activation;
6. stop as Partial when a required interface/runtime does not yet exist rather than fabricating evidence.

The plan cannot authorize foundation runtime implementation; that remains Gate 4 after combined-interface review.

## 11. Normative scenario A — R2 production and verification

Preconditions:

- accepted R2 assurance requirement with producer-independent scope confirmation;
- W3 producer/reviewer contexts and reference-token gate;
- current W7 capability/parity/tokenizer evidence and W8 preliminary operational-risk floor/feasibility;
- producer route and eligible verifier witness;
- W7 adapter profiles and parity evidence;
- W8 producer/verifier resource feasibility.

Required trajectory:

1. W3 compiles and passes the reference-token gate without claiming provider validation;
2. W8 supplies the operational-risk floor/feasibility and W7 supplies current provider/tokenizer/parity evidence before W4 routing;
3. W4 evaluates the candidate-specific provider-capacity gate using an exact count or accepted evaluated upper bound and records the producer route plus verifier witness;
4. W7 revalidates the selected route, wrapper/system reserve and both token gates before issue;
5. the provider command binds exact context/route/policy/grant and the receipt/W8 process evidence bind the actual attempt;
6. the produced artefact is immutable and separately referenced;
7. the final verifier route recomputes independence against the actual producer;
8. W6 grades command/receipt/trace/property evidence;
9. W5 both keys pass before Manager acceptance.

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
| Two-stage token/resource evaluation is dimensionally and temporally coherent | W3/W4/W7/W8/06c | W3 reference gate before route; candidate-specific exact/evaluated provider count during W4; W7 pre-issue revalidation including wrapper reserve; W8 risk floor before route and grant/lease after route |
| P0 is not conflated with materialization stage | W6/06c | Catalogue/plan crosswalk preserving accepted priority |
| No active research state is used | All | Filesystem diff and no-runtime/no-migration declaration |

## 17. Interface freeze criteria

Gate 3 written interfaces may be frozen only when:

- every shared field has one semantic owner, resolves to its defining catalogue, and all consumers use the exact identifier;
- identity/version/hash/currency behavior is explicit;
- W3 reference/provider gates and W8 floor/grant appear at their distinct evaluation points;
- W4 consumes accepted W5 requirements plus current W7/W8 inputs before route selection;
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

06c moved to `accepted_interface_manifest` after the bounded joint review, technical reconciliation, and Stephen's 2026-07-01 approval confirmed that:

- [x] W6/W7/W8 responsibilities and dependency direction are non-circular.
- [x] Shared IDs/fields have one semantic owner and consistent consumers.
- [x] Lifecycle and failure ordering contain no temporal inversion.
- [x] Units/tokenizers/resource quantities are dimensionally explicit.
- [x] Missing, stale, unknown and unsupported evidence fails closed.
- [x] Priority and `gate_stage` cannot weaken each other.
- [x] Scenarios A–E are complete enough to drive the P0 plan.
- [x] Privacy and restricted-data denial are enforced across all interfaces.
- [x] The P0 plan and foundation implementation remain separately gated.
- [x] No runtime, migration, fixture materialization, active APM change or research claim is introduced.

## 20. Outcome

**Outcome:** `ACCEPTED_INTERFACE_MANIFEST — 06c v0.2 closes Gate 3 ordering, identity, ownership, and stage coherence under P-030; runtime and P0 materialization remain separately gated`.

The next action is a separately reviewed P0 materialization and narrow-foundation implementation plan. P-030 itself authorizes no executable fixture, adapter, process, runtime, migration, pilot, or research claim.