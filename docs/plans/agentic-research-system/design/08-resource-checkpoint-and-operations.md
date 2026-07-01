# W8 — Resource, Checkpoint, and Operations Specification

**Date:** 2026-07-01<br>
**Status:** Draft complete; joint Gate 3 review pending<br>
**Specification version:** 0.1<br>
**Design authority:** Accepted W1–W5, W6 catalogue/addenda, D-001–D-008, P-001–P-029, and Stephen's approved Gate 3 conceptual design<br>
**Implementation authority:** None; this document creates no scheduler, lease, process, checkpoint, backup, operator command, runtime, migration, fixture, or `.research-system/` state<br>
**Review owner:** Stephen; bounded joint W6/W7/W8/06c adversarial review required

## 1. Decision summary

W8 turns resource ownership and long-running execution from narrative convention into typed, auditable operational evidence.

It makes these binding draft choices:

1. resource requests, grants, leases, processes and checkpoints have distinct immutable identities;
2. a route or provider command does not own machine resources without a valid W8 grant;
3. benchmark feasibility measures declared full-design work and hidden prerequisites before expensive dispatch;
4. heartbeats are evidence, not proof of progress; lease expiry and personal-machine sleep require explicit revalidation;
5. checkpoint compatibility is a deterministic predicate over code, environment, inputs, parameters, RNG and state schema;
6. stop/pause/resume are separate commands and receipts; a requested stop is not confirmed until process/output-writer termination is proven;
7. orphan processes and artefacts remain visible but cannot satisfy acceptance without authorized rebinding/review;
8. backup/restore proves control-store identity, chain, snapshot and external-artefact availability before writer lease;
9. W8 may raise operational risk but cannot lower W5 epistemic risk or decide scientific validity;
10. this specification defines evidence only; it does not implement a scheduler or run P0 fixtures.

## 2. Sources and evidence

W8 implements:

- W1 dedicated control-store, single-writer, filesystem and recovery boundaries;
- W2 dispatch/attempt/lease/checkpoint/Partial/reopen identities and state separation;
- W3 context budget/expiry evidence needed for long-running work;
- W4 resource class, routing snapshot, permissions and `W8_operational_risk_floor`;
- W5 stop/Partial/negative and acceptance separation;
- W6 F-003, F-007–F-010, F-032–F-034, S-003–S-004, S-009–S-012, S-014 and S-016;
- current TDL evidence from T1.6/T1.28 guardrails and T1.9 checkpoint recovery: hidden prerequisites, invalid parallel projections, multi-hour stop thresholds, resumable checkpoints, worktree/control/result root separation and machine ownership recorded only in prose.

## 3. Scope and exclusions

### 3.1 In scope

- resource request, grant, conflict and release semantics;
- feasibility benchmark/projection evidence;
- execution leases, heartbeats and personal-machine suspend/resume;
- process identity and child-process ownership;
- checkpoint manifests and compatibility;
- start, pause, stop, resume, cancel and Partial transitions;
- orphan process/artefact classification and recovery;
- backup/restore and control-store recovery evidence;
- operator commands, receipts, failure behavior and W6 coverage.

### 3.2 Out of scope

- scheduler/queue/process-manager implementation;
- launching, stopping or inspecting live processes;
- creating checkpoints or backups;
- cloud/cluster orchestration;
- billing or cost optimization;
- changing scientific parameters, stop rules or pre-registrations;
- executable P0 fixtures;
- migration or control of T1.28, current APM tasks or active paper runs.

## 4. Ownership boundary

| Concern | Owner | W8 responsibility |
|---|---|---|
| Task/attempt/command/event state | W1/W2 | Submit operational commands/evidence; never edit canonical state |
| Scientific stop/Partial rules | W5/governing design | Enforce declared operational consequence; never rewrite rule |
| Route/provider selection | W4/W7 | Supply availability/resource evidence; never reroute |
| Fixture grading/release | W6 | Emit gradeable operational trace/evidence; never self-grade |
| Resource/process/checkpoint operations | W8 | Own typed contracts, compatibility, recovery and operator evidence |

A process existing, consuming CPU, writing files or returning exit code zero does not establish Task progress, result validity or acceptance.

## 5. Core identities

```text
resource_request_id       rrq_...
resource_grant_id         rgr_...
resource_conflict_id      rcf_...
execution_lease_id        els_...
heartbeat_id              hbt_...
process_identity_id       pid_...
checkpoint_manifest_id    cpm_...
stop_record_id            stp_...
resume_decision_id        rsd_...
recovery_evidence_id      rcv_...
backup_receipt_id         bkr_...
operator_command_id       opc_...
operator_receipt_id       opr_...
```

IDs are separate from provider sessions, operating-system PIDs, Task aliases and filenames. Every record carries revision/hash, host/control-store identity, actor/authority, effective interval, source position and supersession lineage.

## 6. Operational lifecycle

### 6.1 Resource request/grant

```text
requested -> evaluated -> granted -> active -> released
requested/evaluated -> blocked | rejected
active -> expired | revoked
```

### 6.2 Lease

```text
issued -> claimed -> active -> released
issued/claimed/active -> expired | revoked | uncertain
active -> revalidation_required -> active | expired | revoked
```

### 6.3 Attempt operation

```text
prepared -> starting -> running
running -> pause_requested -> paused
running/paused -> stop_requested -> stopped
paused/stopped -> resume_requested -> running | blocked
running/paused/stopped -> partial | failed | superseded
```

Task scientific status remains separate. Operational `stopped` does not mean evidence rejected or Task complete.

## 7. `ResourceRequest`

Required fields include:

- Task/dispatch/attempt/route/provider-command identities;
- requesting actor/profile/authority and expected control-store position;
- requested host pool and typed control/code/result/cache/data roots;
- CPU process/thread limits, RAM working/peak, GPU/device, storage and IO estimates;
- network/external-write/sensitivity constraints;
- exclusive/shared resources and compatibility keys;
- expected runtime distribution, deadline and checkpoint interval;
- benchmark/projection evidence and uncertainty;
- stop/pause/Partial/escalation rules;
- resource-release and cleanup obligations.

Requests state ranges and uncertainty, not a single optimistic estimate.

## 8. `ResourceGrant`

A grant binds:

- request and revision/hash;
- exact host/boot/control-store identity;
- allowed roots and resource ceilings;
- exclusive/shared compatibility and conflict set;
- lease duration, heartbeat policy and expiry;
- process/child-process rules;
- checkpoint/output/cleanup paths;
- authority, issued time and revocation conditions;
- W4 operational risk floor/route expiry consequences.

The effective resource surface is the intersection of W4/W7 permissions and W8 grant. W8 cannot widen tool, root, network or sensitivity authority.

## 9. Resource compatibility and conflicts

Resources use typed keys:

```text
host_cpu
host_ram
host_gpu
storage_bandwidth
network_slot
control_writer
result_root_writer
cache_writer
restricted_data_session
provider_rate_limit
```

Each key declares `exclusive`, `capacity_shared`, or `read_shared`. Conflicts are evaluated atomically at the requested control-store position. Narrative statements such as “owns the machine” or “overnight run” are not grants.

No overcommit policy may hide a hard scientific guardrail. If measured use exceeds a ceiling, W8 records the breach and applies the declared stop/Partial rule; it does not silently grant more.

## 10. Benchmark and feasibility protocol

Before expensive R2/R3 dispatch, the benchmark record must declare:

- full prerequisite DAG and bounded work-unit count;
- whether benchmark mode executes any production-scale prerequisite;
- sample work units, warm-up, repeats and cache state;
- sample count relative to worker/process count;
- backend/process/thread/GIL characteristics;
- worker scaling, RAM/IO/GPU observations and uncertainty;
- serial and parallel projection formulas with units;
- projected full runtime/peak memory and interval;
- comparison with accepted stop thresholds and resource grant;
- invalidity conditions and decision authority.

A benchmark with fewer independent work units than workers cannot justify worker scaling. Hidden prerequisites count in the full design. A projection crossing a hard threshold emits the governing stop/input-required/Partial transition; it cannot be converted into a scientific result claim.

## 11. Operational risk floor

W8 owns `W8_operational_risk_floor`, separate from W5's epistemic component. Raising triggers include:

- irreversible/external write or restricted-data exposure;
- unbounded or multi-hour execution without calibrated checkpoint/recovery;
- exclusive machine/resource ownership;
- new backend/process model or uncertain worker scaling;
- incomplete stop confirmation;
- checkpoint or restore uncertainty;
- broader roots/network/tool surface;
- unresolved orphan process/artefact.

W4 computes the maximum risk. W8 cannot lower another floor or waive a human-reserved action.

## 12. `ExecutionLease` and heartbeat

A lease binds grant, attempt, process identity, actor, host/boot ID, issued/claimed/expiry times, heartbeat policy and revocation conditions.

Heartbeats record:

- monotonic sequence and observed wall/monotonic times;
- process/host/boot identity;
- declared work-unit progress and evidence pointer;
- CPU/RAM/IO/GPU observations;
- checkpoint/output tail identity;
- blocker/warning/stop state.

Heartbeat presence proves liveness evidence only. Progress claims require a monotone work-unit/checkpoint/output predicate. Repeated identical heartbeats cannot disguise stalled or hidden prerequisite work.

Cadence and grace are versioned policy fields; no permissive universal default exists. Missing accepted values blocks lease activation.

## 13. Personal-machine sleep and resume

System suspend does not silently extend a lease. On wake or detected wall/monotonic discontinuity:

1. mark active leases `revalidation_required`;
2. verify host and boot identity, PID/start identity and child processes;
3. verify resource conflicts and external provider/session state;
4. verify checkpoint/output tail and stop threshold;
5. either reactivate through an attributed operator receipt or expire/revoke.

A process that continued remotely during local sleep is reconciled through provider/process evidence. A missing observation becomes `uncertain`, not presumed safe.

## 14. `ProcessIdentity`

Required fields include:

- host/boot identity, OS PID and process start time;
- executable identity/hash, normalized command digest and environment fingerprint;
- parent/child process relationships and backend;
- Task/attempt/lease/provider-command correlation;
- cwd plus typed control/code/result/cache/data roots;
- output/checkpoint handles and writer ownership;
- actor/profile/authority and sensitivity class.

PID alone is never stable identity. PID reuse, changed start time, executable mismatch or boot change breaks identity.

## 15. `CheckpointManifest`

A checkpoint binds:

- Task/attempt/execution epoch and producing process;
- code commit/source hash and environment fingerprint;
- input IDs/hashes/vintages and row/sample restrictions;
- representation/model/loadings/scaler/label fingerprints;
- parameters, seeds, RNG algorithm and serialized RNG state;
- null/model order, B/L and completed/remaining work units;
- checkpoint schema/version, payload hashes and dependency closure;
- result/cache/output roots and no-overwrite disposition;
- stop reason, limitations and allowed consumers.

A filename or successful deserialize is insufficient.

## 16. Checkpoint compatibility

Resume is permitted only when a deterministic predicate confirms:

- compatible checkpoint schema;
- identical governing design/amendment and scientific parameters;
- compatible code/environment or an accepted migration rule;
- identical inputs/vintages/representation fingerprints;
- consistent RNG/work-unit lineage with no duplicated or skipped units;
- valid payload/hash/dependency closure;
- authorized roots and resource grant;
- no superseding result/decision that forbids continuation.

Compatibility returns `compatible`, `incompatible`, or `unable_to_determine` with evidence. Only `compatible` may resume. A changed design creates a new attempt/epoch and preserves the old checkpoint as evidence.

## 17. Stop, pause, cancel and resume

### 17.1 `StopRecord` and stop confirmation

`StopRecord` binds the request, actor/authority, attempt/lease/process/provider identities, reason, timestamps, signals, writer/checkpoint disposition, evidence and terminal confidence. It distinguishes:

```text
requested
signal_sent
provider_cancel_requested
process_exited
children_exited
writers_closed
confirmed
uncertain
```

`confirmed` requires process/child/provider reconciliation and proof that no output/checkpoint writer remains. A timeout without proof is `uncertain` and escalates.

### 17.2 Pause

Pause requires a compatible checkpoint or an explicit declaration that no resumable state exists. `paused` preserves lease/resource disposition and expiry; it is not Task Partial by itself.

### 17.3 `ResumeDecision`

`ResumeDecision` records the checkpoint compatibility verdict, current resource/context/route/authority checks, approving authority, new execution epoch, and permitted work-unit range. A permitted resume creates a new execution epoch and preserves the earlier stop/pause evidence. It never rewrites the prior attempt.

### 17.4 Partial

When the governing stop rule fires or required continuation evidence is unavailable, W8 submits operational evidence for a W2/W5 Partial decision. It cannot decide scientific consumer permissions itself.

## 18. Orphan processes and artefacts

An orphan is any process/output/checkpoint whose Task/attempt/lease/provider relationship is missing, expired, divergent or unprovable.

`RecoveryEvidence` binds the detected condition, canonical tail and projection hash, process/child reconciliation, checkpoint and artefact manifests, actions taken, unresolved uncertainty, consumer restrictions, and attributed authority. It proves what was recovered or quarantined; it never upgrades an orphan into accepted evidence by assertion.

Required handling:

- detect and record identity/evidence without adopting it;
- prohibit automatic deletion when it may contain unique research evidence;
- block use for acceptance or claim promotion;
- allow quarantine, termination or rebinding only through typed authority;
- preserve late artefacts with exact timing and consumer restrictions;
- never infer completion from a final-looking filename.

## 19. `BackupReceipt`, backup and restore

`BackupReceipt` binds:

- project/control-store identity and canonical tail position/hash;
- accepted snapshot identity/hash and replay range;
- schema/tool versions and encryption/redaction class;
- external artefact manifest and availability status;
- creation/verification times and authority;
- destination class without storing credentials.

Restore on another machine must prove store/project identity, hash chain, snapshot/tail replay, endpoint ownership, schema support and external artefact availability before any writer lease. Partial restore produces a diagnostic projection only.

## 20. Operator commands and receipts

Initial normalized operator commands are:

```text
request_resource_grant
claim_execution_lease
record_heartbeat
request_pause
confirm_pause
request_stop
confirm_stop
request_resume
release_resources
quarantine_orphan
adopt_late_artefact
create_backup
verify_restore
```

Every command carries expected state/version, idempotency, actor/profile/authority, subject and evidence. W8 submits through W2; operator tools never edit canonical files directly.

## 21. Failure behavior

| Failure | Required result |
|---|---|
| Resource request incomplete/uncertain | Block grant; name missing evidence |
| Hard resource conflict | `resource_conflict`; no overcommit |
| Benchmark hides prerequisites or invalid scaling | `feasibility_invalid`; no expensive dispatch |
| Projection crosses hard stop threshold | Stop/input-required/Partial per governing rule |
| Lease/heartbeat policy missing | Block activation |
| Lease expires or host/boot identity changes | `revalidation_required` then expire/revoke unless proven safe |
| PID/start/executable mismatch | Process identity invalid; classify orphan/uncertain |
| Checkpoint compatibility fails/unknown | Block resume; preserve checkpoint |
| Stop requested but not confirmed | `stop_uncertain`; retain resource conflict and escalate |
| Late/orphan artefact exists | Preserve/quarantine; no acceptance without review |
| Backup chain/snapshot/external artefacts fail | Restore diagnostic only; no writer lease |
| Operational evidence succeeds but science fails | No scientific acceptance; evidence remains operational only |

## 22. Privacy and security

- Process/environment fingerprints exclude secrets and raw environment values.
- Command lines/tool arguments are redacted by stable field policy before storage.
- Restricted-data processes record opaque dataset/session identity, not participant data.
- Checkpoints containing restricted inputs remain in approved roots and are referenced by hash/manifest.
- Backups declare encryption/access class and never embed credentials in receipts.
- Full provider transcripts and hidden reasoning are prohibited.

## 23. Observability and metrics

W8 emits normalized evidence for:

- grant wait/conflict/revocation and utilization;
- benchmark work units, scaling, projection error and uncertainty;
- lease/heartbeat/stall/expiry/revalidation;
- process/child identity and backend;
- checkpoint creation, compatibility, resume and duplicated/skipped work;
- stop latency and uncertain stop rate;
- orphan process/artefact detection and disposition;
- backup verification and restore/replay success;
- actual versus projected runtime/memory/IO.

Cost/resource metrics never override correctness or stop gates.

## 24. W6 coverage obligations

Foundation-critical W8 coverage includes:

- F-003 wrong control/result root;
- F-007 hidden benchmark prerequisite;
- F-008 invalid parallel projection;
- F-009 long-run guardrail;
- F-010 downstream correction overreach where operational scope expands;
- F-032 outage/resource re-evaluation;
- F-034 permission/root/sensitivity and unsafe decomposition;
- S-003 late artefact after lease expiry;
- S-004 Partial resume lineage;
- S-009 projection rebuild;
- S-011 writer crash window;
- S-012 divergent task branches;
- S-014 backup/restore and machine move;
- S-016 provider outage.

Some are not accepted P0-priority fixtures. W6/06c must use separate `gate_stage` rather than relabeling priority.

## 25. Downstream constraints

### W6

Grade the exact operational records and trajectories. Do not infer resource safety or checkpoint compatibility from exit codes or producer flags.

### W7

Bind provider commands/receipts to W8 grant/lease/process evidence. Provider cancellation cannot self-certify confirmed stop.

### W9/W10

Migration and templates define machine-specific policies without hard-coding TDL hosts, usernames or roots. Backup/restore examples use synthetic projects.

## 26. Joint Gate 3 review questions

1. Can any process run without a typed grant and valid lease?
2. Can heartbeats or output mtimes fake progress?
3. Can sleep/reboot/PID reuse preserve a false process identity?
4. Can a checkpoint resume under changed inputs, representation, RNG or design?
5. Can stop be reported before child/provider/output writers terminate?
6. Can an orphan artefact become accepted merely because it looks complete?
7. Can backup restore grant writer authority without proving chain/tail identity?
8. Can operational success substitute for scientific validity?

## 27. Review gate

W8 can move from `review_pending` to `accepted` only when Stephen confirms after joint W6/W7/W8/06c review that:

- [ ] Resource requests/grants/conflicts are typed, atomic and non-widening.
- [ ] Benchmark feasibility counts hidden prerequisites and validates scaling/units.
- [ ] Operational and epistemic risk floors remain separate and monotone.
- [ ] Lease/heartbeat/sleep behavior fails closed without accepted cadence policy.
- [ ] Process identity survives PID reuse, reboot and child-process cases.
- [ ] Checkpoint compatibility binds design, code, environment, inputs, representation, RNG and work units.
- [ ] Stop/pause/resume/Partial meanings and ordering are non-overlapping.
- [ ] Orphan and late evidence remains visible but unauthorized.
- [ ] Backup/restore proves canonical chain/snapshot/tail before writer lease.
- [ ] Privacy rules protect environment, restricted data, checkpoints and backups.
- [ ] W6 receives sufficient evidence to grade runtime, recovery and guardrails.
- [ ] No process, checkpoint, backup, runtime, migration or active-task change is introduced.

## 28. Outcome

**Outcome:** `REVIEW_PENDING — W8 v0.1 resource/checkpoint/operations specification complete; implementation and P0 evidence remain gated`.

The next action is bounded joint Gate 3 adversarial review with W6 v0.3, W7 v0.1 and manifest 06c. No scheduler, process control, checkpoint or backup implementation begins before that review and a separately approved P0 plan.
