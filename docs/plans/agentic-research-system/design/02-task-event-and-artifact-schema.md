# W2 — Task, Event, Artefact, Review, and Decision Schema

**Date:** 2026-06-28  
**Revised:** 2026-06-30  
**Status:** Adversarial-review amendments integrated; P-026 gate split recorded; Manager review pending  
**Specification version:** 0.3  
**Design authority:** W1 v0.3, W0 manifest and 2026-06-29 addendum, D-001–D-008, P-001–P-005, and approved amendments P-020–P-026  
**Implementation authority:** None; this document specifies records and lifecycle semantics but creates no schemas, runtime, migration, or `.research-system/` state  
**Review owners:** Stephen and the current research-programme Manager  
**Foundation gate:** W1/W2 Manager confirmation plus accepted W3–W5 and foundation-critical W6–W8 interfaces under P-026  
**Legacy migration gate:** T1.28 terminal review/final W0 addendum and the full Stage 2 scope decision  

## 1. Decision summary

W2 replaces implicit identity and mutable status prose with typed immutable records and deterministic lifecycle projections.

The draft makes these principal choices:

1. Every accepted command reaches one project-wide command service and commits one atomic JSONL event-batch file in the dedicated linear control store. Agents and task worktrees never append or allocate positions independently.
2. Canonical identifiers use a type prefix plus UUIDv7. Human labels such as `T1.28` remain aliases, never primary keys.
3. Task status, dispatch status, attempt status, lease status, review status, and artefact authority are separate state machines.
4. Commands express requested changes; events record accepted facts; messages communicate; artefacts carry outputs; reviews judge evidence; decisions exercise authority.
5. `queued`, `claimed`, `running`, and `checkpointed` are operational projections from dispatches, attempts, leases, and checkpoint events. They are not canonical Task statuses.
6. Partial is a valid attempt outcome and may be a closed Task outcome. Resumption never overwrites the Partial record.
7. Artefact existence, integrity, structural validation, scientific review, and acceptance-for-use are separate dimensions.
8. Message delivery and acknowledgement are immutable events. Clearing an APM compatibility file acknowledges a view; it never deletes the message or history.
9. Deterministic replay uses the dedicated ledger’s global positions/hash chain, stream versions, object hashes, transaction boundaries, pure reducers, and optional verified snapshot anchors. Unknown or inconsistent records fail closed.

These choices are schema proposals pending the W2 review gate. They do not authorize implementation.

## 2. Evidence and governing constraints

W2 implements:

- W1 invariants: stable identity, one canonical owner, command-only mutation, no silent overwrite, provider-neutral authority, disposable projections, and fail-closed compatibility;
- W0 fixtures F-001–F-020, especially overwrite, task/report collision, wrong root, stale projections, narrowed-stage completion, hard guardrails, self-approved contracts, superseded provenance, and provider drift;
- the W0 source hierarchy, 2026-06-29 currency addendum, and selective-import policy;
- the adversarial-review reconciliation and approved amendments P-020–P-025;
- the current APM task/report/log shapes, including frontmatter aliases, worktree roots, output requirements, assurance requirements, attempt narratives, Partial reports, and closeout bookkeeping;
- the canonical Task Observer observation titled “Bus writes need explicit ownership, not only read-before-write” (2026-06-28; `C:\Users\steph\.Codex\skill-observations\log.md`): bus writes need explicit ownership and collision failure, not only read-before-write;
- current research-assurance lanes: topology, stochastic/null, statistical/panel, representation, output/provenance, and paper claim;
- the requirement that T1.28 and all W0 no-migration items remain legacy-owned.

The existing Graphify index was queried for APM task/report/Tracker relationships but returned computational dispatch functions rather than control-plane documents. Direct W0/W1 files, live read-only APM records, and accepted repository evidence remain authoritative.

## 3. Scope and non-goals

### 3.1 In scope

- identifier format and alias rules;
- schema and record versioning;
- immutable object records;
- command envelope, validation, idempotency, and receipt;
- atomic event batches and event envelope;
- Task, dispatch, attempt, lease, message, blocker, Partial, artefact, validation, review, decision, correction, and supersession records;
- lifecycle transitions and authority preconditions;
- deterministic projection and rebuild rules;
- legacy compatibility semantics at record level;
- acceptance scenarios for historical failures.

### 3.2 Deferred

- context packet content and retrieval policy: W3;
- exact role profiles, model routing, and authority-grant policy: W4;
- assurance-pack schemas and scientific review procedures: W5;
- trace privacy, graders, fixtures, and metric thresholds: W6;
- Claude/Codex adapter files and parity implementation: W7;
- resource scheduling, process supervision, heartbeat cadence, checkpoint compatibility, and operator commands: W8;
- legacy import tooling, pilot mechanics, rollback, and deprecation: W9;
- reusable project scaffolding: W10.

### 3.3 Non-goals

- implementing JSON Schema files or runtime code during W2;
- representing every domain result field in the core;
- making a database canonical;
- treating Git commit history alone as the event ledger;
- signing or cryptographically notarising records in the first release;
- importing live TDL tasks or historical Tracker prose;
- converting a task report, process exit, test pass, or merge into acceptance automatically.

## 4. Options considered

### 4.1 Option A — Atomic event batches plus immutable objects

Each accepted command writes referenced immutable objects first, then atomically publishes a small JSONL event-batch file that commits the state change. State is rebuilt by ordered replay.

**Benefits:** Preserves W1's local JSONL authority; no concurrent shared append; exact history; natural retries and supersession; Git-readable; projections are disposable.  
**Costs:** Requires a command writer, reducer versions, hash checks, and careful handling of orphan objects.  
**Decision:** Recommended and specified below.

### 4.2 Option B — Immutable objects plus mutable current-state files

Each operation writes a new object version and updates a current-state pointer.

**Benefits:** Fewer event concepts and simple reads.  
**Costs:** The mutable pointer becomes a collision and recovery boundary; trajectory and rejected transitions are harder to evaluate; multi-object operations are ambiguous.  
**Decision:** Rejected as canonical design. This pattern is suitable only for projections.

### 4.3 Option C — SQLite as the transactional authority

Commands transact directly into a local SQLite database and export human-readable logs.

**Benefits:** Mature transactions, constraints, and querying.  
**Costs:** Contradicts P-001; hides authority from plain version-controlled files; creates a database migration and recovery dependency.  
**Decision:** Rejected as canonical design. SQLite remains a rebuildable index.

## 5. Record model and terminology

The following record types must not be collapsed:

| Record | Meaning | Changes lifecycle state? |
|---|---|---|
| Command | An attributed request to change state | Only if accepted by the command service |
| Receipt | The accepted, duplicate, or rejected outcome of a command submission | No independent mutation |
| Event | An immutable fact accepted into canonical history | Yes, through deterministic reducers |
| Object | An immutable versioned definition or structured payload | Only when referenced by an accepted event |
| Message | Attributed communication between actors | No, unless a separate command acts on it |
| Artefact | A durable external output or evidence object | Registration alone does not imply acceptance |
| Validation | A bounded mechanical or human check of a subject | No automatic Task acceptance |
| Review | A judgment against declared questions and authority requirements | Satisfies a gate; acceptance remains a command |
| Decision | An authorized resolution of a methodological, governance, claim, or migration question | Yes, within its declared scope |
| Projection | Rebuilt current state or human-readable view | Never canonical |

Terms such as “done”, “success”, “merged”, “reported”, and “clear bus” have no lifecycle effect unless mapped to an accepted event with explicit authority.

## 6. Identifier system

### 6.1 Canonical identifiers

Every first-class record uses:

```text
<three-letter-kind>_<lowercase UUIDv7>
```

The UUID retains standard hyphens. Example:

```text
tsk_01979c31-6710-7a2d-8d4b-6d2c62e07f51
```

Required prefixes:

| Prefix | Kind |
|---|---|
| `prj` | project/control ledger |
| `obj` | portfolio or scope object |
| `tsk` | Task |
| `cmd` | command |
| `txb` | event transaction/batch |
| `evt` | event |
| `dsp` | dispatch |
| `att` | execution attempt |
| `lse` | lease |
| `msg` | message |
| `blk` | blocker/input requirement |
| `art` | artefact manifest |
| `val` | validation record |
| `rev` | review |
| `dec` | decision |
| `ctx` | context packet |
| `act` | actor identity |
| `agr` | authority grant |
| `pol` | policy version |

UUIDv7 provides time locality but its embedded time is not an authoritative timestamp. Ordering comes from event position.

### 6.2 Aliases

Human and legacy identifiers are stored as scoped aliases:

```json
{
  "namespace": "tdl.apm.task",
  "value": "T1.28",
  "scope_id": "prj_01979c31-4e54-7c6f-8a0f-87d2f232c7c4"
}
```

Aliases may be non-unique across projects or time. Resolution requires namespace and scope. An alias can be corrected or superseded without changing the canonical ID.

### 6.3 Reference rules

- Internal references use canonical IDs and optional expected revision/hash.
- Paths are not identifiers.
- Branch names, agent slugs, model names, filenames, paper IDs, and Task numbers are aliases or attributes.
- Every external reference declares its namespace, locator, and integrity evidence where available.
- A missing reference blocks the dependent transition; it is not converted to `null` or dropped.

## 7. Schema and object versioning

### 7.1 Schema identity

Every record carries:

- `schema_id`: stable URI-like name, such as `ars://core/task-definition`;
- `schema_version`: semantic version;
- `record_id`;
- `record_revision` where the kind supports revisions;
- `content_hash`: lowercase SHA-256 over RFC 8785 canonical JSON, excluding `content_hash` itself.

Minor schema versions are backward-compatible additions. Major versions require a reducer/reader that explicitly supports both versions or a versioned migration projection. Historical records are never rewritten into the new version.

### 7.2 Immutable object versions

Definitions such as Task revisions, scope definitions, review requests, decision proposals, and artefact manifests are immutable object files. A changed definition creates:

- the same logical ID where revision is appropriate;
- `record_revision + 1`;
- `supersedes_revision`;
- a new content hash;
- an event that authorizes the new revision.

An object file written before its referencing event is inert. If a crash leaves an unreferenced object, recovery classifies it as an orphan candidate; it does not enter state automatically.

### 7.3 Canonical object paths

Proposed path rule:

```text
.research-system/objects/<kind>/<first-two-id-chars>/<record-id>/r<revision>-<hash12>.json
```

Artefact manifests use the canonical `manifests/` root established by W1. Exact path helpers belong to implementation planning, but no consumer may derive authority from a filename alone.

## 8. Command envelope and receipts

### 8.1 Command envelope

Every submitted command contains:

| Field | Requirement |
|---|---|
| `command_id` | Stable `cmd_` ID; retries reuse it |
| `command_type` | Versioned imperative name, such as `IssueDispatch` |
| `schema_id`, `schema_version` | Command schema identity |
| `submitted_at` | UTC RFC 3339 timestamp with offset `Z` |
| `actor_id` | Attributed submitter |
| `on_behalf_of_actor_id` | Optional delegating human/role |
| `authority_grant_id` | Grant evaluated by the command service |
| `target_stream_id` | Task, decision, artefact, or project stream |
| `expected_stream_version` | Optimistic-concurrency precondition |
| `idempotency_key` | Caller-scoped stable operation key |
| `correlation_id` | Groups a research workflow or request |
| `causation_id` | Prior command/event/message causing this request |
| `reason` | Non-empty auditable rationale |
| `evidence_refs` | Governing objects and artefacts |
| `payload` | Command-specific typed body |

Provider prompt text, hidden reasoning, and session transcript are not command authority. Provider, model, reasoning setting, context packet, and tool metadata are trace references defined by W3/W4/W6.

### 8.2 Validation order

The command service validates, in order:

1. envelope and payload schema;
2. record IDs and referenced object existence/hash;
3. canonical owner and compatibility mode;
4. actor and authority grant;
5. expected stream version;
6. idempotency key and payload hash;
7. state-transition preconditions;
8. assurance, review, dependency, and human-approval gates;
9. write-set and event-batch integrity.

Failure at any step writes no lifecycle event.

### 8.3 Receipts

A receipt has one of:

- `accepted`: event batch ID, event IDs, positions, and resulting stream version;
- `duplicate`: the original accepted receipt for the same idempotency key and payload hash;
- `rejected`: stable reason code, human-readable explanation, observed stream version, and unmet preconditions;
- `conflict`: same idempotency key with a different payload hash or stale expected version.

Accepted idempotency outcomes are reconstructible from events. Rejected/conflict receipts are operational audit records governed by W6 retention and privacy rules; they do not masquerade as lifecycle events.

## 9. Atomic event batches

### 9.1 Storage unit

Each accepted command produces one immutable JSONL file in the dedicated project control root:

```text
<control-root>/events/<project-id>/<yyyy>/<mm>/
  <20-digit-start-position>-<transaction-id>.jsonl
```

The one project-wide writer:

1. validates `project_id`, control-store identity, endpoint, and caller root binding;
2. acquires the control-store command lock and proves it is the registered writer instance;
3. verifies the canonical global tail and every expected stream version;
4. writes any referenced immutable objects into the same control store;
5. builds the complete event batch in the control store’s `runtime/` area;
6. validates every event, position allocation, and batch/global hash chain;
7. flushes and closes the temporary file;
8. atomically renames it into `events/`;
9. advances the dedicated linear ledger history and returns the receipt.

The atomic rename is the event commit point. Objects written without a committed batch are inert. A crash cannot leave half an accepted command in the event ledger. Task worktrees never own this path, lock, or history and cannot publish a batch directly.

### 9.2 Event envelope

Every JSONL line contains:

| Field | Meaning |
|---|---|
| `event_id` | Stable `evt_` ID |
| `event_type` | Past-tense fact, such as `DispatchIssued` |
| `schema_id`, `schema_version` | Event schema identity |
| `project_id` | Owning ledger |
| `stream_id` | Aggregate stream affected |
| `stream_version` | Monotonic version within that stream |
| `global_position` | Monotonic position within the project ledger |
| `transaction_id` | Shared `txb_` ID for the batch |
| `transaction_index`, `transaction_count` | Complete batch ordering |
| `command_id` | Accepted command that caused the event |
| `correlation_id`, `causation_id` | Workflow lineage |
| `actor_id`, `authority_grant_id` | Accepted authority snapshot |
| `occurred_at` | Domain occurrence time if distinct |
| `recorded_at` | Ledger commit time |
| `payload` | Typed immutable fact |
| `previous_event_hash` | Hash of prior global event or genesis marker |
| `event_hash` | SHA-256 over canonical event content excluding `event_hash` |

`recorded_at` and UUID time do not determine replay order. `global_position` does. It is allocated only by the registered project writer; a task worktree cannot propose or reserve it.

### 9.3 Event naming

Events use past-tense domain facts, not UI actions. Core examples:

```text
TaskCreated                ReadinessRequested       ReadinessApproved
DispatchIssued             DispatchAcknowledged    DispatchClaimed
AttemptCreated             AttemptStarted          CheckpointRecorded
AttemptPaused              AttemptCompleted        AttemptFailed
TaskBlocked                InputRequested           TaskResumed
TaskSubmittedForReview     ReviewRequested          ReviewVerdictRecorded
ArtefactRegistered         ValidationRecorded       ArtefactUseAccepted
PartialOutcomeRecorded     TaskAccepted             TaskRejected
TaskCancelled              TaskSuperseded           DecisionResolved
MessagePublished           MessageDelivered         MessageAcknowledged
LeaseGranted               LeaseRenewed              LeaseReleased
LeaseExpired               BlockerResolved           RecordCorrected
ProjectionDriftDetected
```

A generic `StatusChanged` event is prohibited because it hides transition meaning and preconditions.

## 10. Task definition

### 10.1 Required fields

An immutable Task revision contains:

| Group | Fields |
|---|---|
| Identity | `task_id`, `revision`, aliases, project, portfolio/scope references |
| Purpose | title, objective, bounded scope, non-goals |
| Dependency | required Task/decision/artefact IDs and satisfaction predicates |
| Research design | governing pre-registration/design/contract refs and risk tier request |
| Assurance | touched lanes, machine checks, human questions, independent-review requirements |
| Delivery | expected artefact types, acceptance criteria, Partial criteria, prohibited shortcuts |
| Execution | root-binding requirements, concurrency policy, resource-policy reference, checkpoint expectation |
| Authority | who may dispatch, amend, cancel, review, accept, reopen, or supersede |
| Provenance | creator, creation time, source/import refs, content hash |

Free-text instructions may explain work but cannot weaken typed requirements. If text and typed fields conflict, the command fails readiness and requires a new Task revision.

### 10.2 Scope definitions and milestones

A stage, wave, paper gate, or milestone is a versioned `ScopeDefinition` object containing:

- member Task/scope IDs;
- required disposition for each member;
- dependency and ordering rules;
- completion predicate;
- authority required to add, remove, defer, or supersede a member;
- effective revision and supersession lineage.

Allowed member dispositions are `accepted`, `partial_accepted`, `deferred`, `superseded`, `removed_by_amendment`, `cancelled`, and `rejected`. The ScopeDefinition completion predicate declares which dispositions satisfy its gate and which require named authority.

`CompleteScope` must reference an exact ScopeDefinition revision and a disposition for every required member. An absent Tracker row is not a disposition. This makes the W0 Stage 2 narrowed-scope collapse unrepresentable as valid completion.

## 11. Separate lifecycle projections

### 11.1 Task status

Canonical Task status describes research-governance progress:

| Status | Meaning |
|---|---|
| `draft` | Definition exists but is not ready for assurance/readiness evaluation |
| `readiness_pending` | Dependencies, inputs, contracts, authority, roots, and resource assumptions are being checked |
| `ready` | Readiness accepted; dispatch may be issued |
| `in_progress` | At least one authorized attempt is active or has produced work awaiting submission |
| `review_pending` | Producing work ended and required review/acceptance evidence is incomplete |
| `blocked` | A non-human dependency or rule prevents progress |
| `input_required` | A named human or authority decision is required |
| `paused` | Progress intentionally suspended with a resumable state |
| `accepted` | Terminal: acceptance criteria and authority gates satisfied |
| `rejected` | Terminal: submitted outcome not accepted |
| `partial` | Terminal: useful bounded output accepted as incomplete with explicit claim restrictions |
| `cancelled` | Terminal: authorized stop without acceptance |
| `superseded` | Terminal: replaced by a declared Task/revision |

### 11.2 Operational status

Views derive, but do not store as Task status:

- `not_dispatched`;
- `queued` from an open dispatch;
- `acknowledged` from delivery/acknowledgement;
- `claimed` from a valid claim and lease;
- `running` from an active attempt;
- `checkpoint_available` from one or more compatible checkpoint records;
- `stopping` from a stop request not yet confirmed;
- `idle` when no dispatch or attempt is active;
- `orphan_suspected` when process evidence outlives its lease/attempt projection.

This separation allows a Task to be `input_required` while a stopped attempt retains checkpoints, or `review_pending` while no process is running.

### 11.3 Allowed Task transitions

| From | Command/event | To | Minimum precondition |
|---|---|---|---|
| none | `CreateTask` / `TaskCreated` | `draft` | Unique Task ID and valid revision |
| `draft` | `RequestReadiness` | `readiness_pending` | Definition complete enough to evaluate |
| `readiness_pending` | `ApproveReadiness` | `ready` | All required readiness evidence passes |
| `readiness_pending` | `BlockTask` or `RequestInput` | `blocked` / `input_required` | Typed blocker and resume condition |
| `ready` | first valid claim/attempt | `in_progress` | Open dispatch, authority, lease, context, roots |
| `in_progress` | `SubmitForReview` | `review_pending` | Producing attempt outcome and candidate artefacts recorded |
| nonterminal | `BlockTask`, `RequestInput`, `PauseTask` | suspended status | Typed reason, owner, resumption rule |
| suspended | `ResumeTask` | prior allowed active status | Blocker resolved or authority supplied |
| `review_pending` | `AcceptTask` | `accepted` | Every acceptance and review gate satisfied |
| `review_pending` | `RejectTask` | `rejected` | Authorized verdict with evidence |
| nonterminal | `ClosePartial` | `partial` | Useful outputs, unmet obligations, and claim restrictions accepted |
| nonterminal | `CancelTask` | `cancelled` | Cancellation authority and process handling recorded |
| any nonterminal | `SupersedeTask` | `superseded` | Replacement ID/revision and lineage |
| `partial`, `rejected`, `cancelled` | `ReopenTask` | `readiness_pending` | Explicit authority, new execution epoch, reason, preserved terminal record |

An `accepted` or `superseded` Task cannot reopen. Changed work creates a new Task or revision linked by supersession.

## 12. Dispatch, claim, lease, and attempt

### 12.1 Dispatch record

A dispatch binds one Task revision to:

- target role/profile and optional actor;
- required model/eval profile reference;
- context packet ID;
- policy and assurance-plan versions;
- explicit control, code, result, cache, paper, vault, and external-data roots;
- branch/worktree identity and expected commit;
- capability and permission set;
- resource-request reference;
- output namespace;
- delivery deadline and claim deadline;
- concurrency mode;
- stop/Partial/escalation rules.

Root bindings contain `root_kind`, canonical URI/path, workspace identity, access mode, expected branch/commit where applicable, and provenance authority. No root is inferred from the current working directory.

### 12.2 Dispatch state

```text
issued -> delivered -> acknowledged -> claimed -> fulfilled
   |         |             |            |
   +------> expired <-------+            +--> withdrawn
   +------------------------------------------> withdrawn
```

Delivery and acknowledgement do not claim work. Claim is a command with expected dispatch and Task stream versions.

### 12.3 Lease record

A lease grants bounded operational ownership of a Task/attempt/resource key:

- lease ID and subject IDs;
- holder actor/profile/session;
- capability scope;
- granted and expiry times;
- renewal policy;
- last accepted heartbeat event;
- release, expiry, or revocation reason.

Lease projection states are `active`, `released`, `expired`, and `revoked`. Time passing alone does not mutate replayed state. A scheduler/operator submits `ExpireLease`, producing `LeaseExpired` at an observed time.

An expired lease does not delete a process or artefact. Subsequent output is registered as `late_candidate` and cannot satisfy acceptance until an authorized review links it to a valid attempt.

### 12.4 Attempt record and states

Every execution try receives a new `att_` ID and monotonically increasing attempt ordinal within the Task execution epoch.

```text
created -> claimed -> running -> completed
                       |  |  |
                       |  |  +-> failed
                       |  +----> partial
                       +-------> paused -> running
                       +-------> stopping -> abandoned
any nonterminal ----------------> superseded
```

Attempt records include dispatch, lease, actor/profile, context, roots, code/environment identity, start/end evidence, checkpoints, candidate artefacts, tests, and outcome reason. Attempt `completed` means producing execution ended; it never means Task `accepted`.

### 12.5 Checkpoints

`CheckpointRecorded` references an artefact manifest and declares:

- attempt and Task revision;
- compatibility fingerprint;
- completed and remaining units;
- code/config/data/seed identity;
- resume command or operation reference;
- integrity and validation status;
- retention and confidentiality class.

Checkpointing does not change Task status. A resume command must prove fingerprint compatibility or explicitly start a new attempt.

### 12.6 Retry and competing attempts

- A retry always creates a new attempt ID; it never rewrites attempt ordinal or output.
- The retry command references the prior outcome and states what is reused.
- Default concurrency mode is `exclusive`: one active producing lease.
- `comparative` and `redundant` modes require Task-level authorization and an acceptance rule for competing results.
- Competing candidate artefacts retain their attempt lineage even if one is rejected or superseded.
- Acceptance names the selected/combined artefacts and explains treatment of alternatives.

### 12.7 Cancellation and stop

Dispatch withdrawal, attempt stop, process termination, and Task cancellation are distinct:

1. `WithdrawDispatch` prevents a new claim.
2. `RequestAttemptStop` records intent and deadline.
3. `ConfirmAttemptStopped` records process evidence and checkpoint disposition.
4. `CancelTask` closes the governance object after active attempts are stopped, abandoned, or explicitly declared orphaned.

A kill signal without these records is an operational observation, not complete cancellation.

## 13. Idempotency and concurrency

### 13.1 Idempotency rule

The tuple `(actor_id, authority_scope, command_type, idempotency_key)` identifies one logical submission.

- Same tuple and same canonical payload hash returns the original receipt.
- Same tuple with a different payload hash is `idempotency_conflict`.
- A caller must not generate a new key merely because a response was lost.
- Accepted event envelopes retain the command ID, key hash, and payload hash needed to rebuild the idempotency index.

### 13.2 Optimistic concurrency

Every mutating command supplies `expected_stream_version` for each affected stream and `expected_global_position`/tail hash for non-commutative project-wide mutations. The project command lock protects physical publication; expected versions protect semantic intent. A stale command is rejected with the observed versions and no automatic retry.

Automatic resubmission is allowed only for commands declared commutative and only after revalidation against current state. Acceptance, cancellation, decision, contract activation, and claim promotion are never auto-rebased.

### 13.3 Transaction scope

One command may produce several events across several streams in one batch. The batch declares its complete write set and expected versions. Either the entire file becomes visible or none of it does. Reducers reject a batch with missing indexes, duplicate positions, overlapping stream versions, or an invalid hash chain.

There is exactly one writer lease per `project_id`. Worktrees and provider sessions are clients identified in the command envelope; they submit over the registered local endpoint or CLI and receive receipts. A second service instance, per-worktree control root, divergent ledger branch, or mismatched store identity is rejected before position allocation. Ledger history permits append and compensating events only; merge, rebase, reset, and event-file revert are invalid control-store operations.

## 14. Messages and compatibility ownership

### 14.1 Message record

Messages contain:

- message ID, type, sender, recipients, and audience;
- Task/dispatch/attempt/review/decision correlation IDs;
- `reply_to_message_id` and thread ID;
- typed subject and concise body or body-artefact reference;
- requested action and deadline where applicable;
- sensitivity/retention class;
- publication, delivery, acknowledgement, and failure events.

Core message types are `assignment`, `acknowledgement`, `progress`, `input_request`, `escalation`, `report`, `review_request`, `review_response`, `decision_request`, and `handoff`.

### 14.2 State boundary

A message may carry a proposed command, but publication does not execute it. For example:

- a Worker report does not complete a Task;
- an escalation does not change a guardrail;
- a review response does not accept a Task;
- an instruction file does not grant authority.

The receiving actor or adapter submits the corresponding command with the message as causation evidence.

### 14.3 APM compatibility files

For a `successor_owned` Task, the adapter writes only a registered ARS-namespaced view such as `.apm/bus/<agent>/ars/<message-id>.task.md` or `.report.md`. It never writes the shared legacy `task.md` or `report.md` slot. If an unmodified legacy Worker must use that slot, the Task is `legacy_owned`.

Generated namespaced frontmatter includes:

```yaml
ars_projection: true
ars_task_id: tsk_...
ars_dispatch_id: dsp_...
ars_message_id: msg_...
ars_recipient_actor_id: act_...
ars_source_position: 1234
ars_projector_version: 1.0.0
ars_content_hash: <sha256>
```

The adapter writes only when every ownership field and registered namespaced path match and the target is empty or contains the same generated identity at the expected source position. Any other non-empty content is a collision and fails closed. Hooks may reject accidental direct writes but cannot authorize a shared legacy path.

Clearing an ARS-aware namespaced view submits `AcknowledgeMessage`; it does not delete `MessagePublished`, delivery, prior content hash, or receipt. This applies the 2026-06-28 Task Observer observation titled “Bus writes need explicit ownership, not only read-before-write.”

## 15. Blockers, input requirements, and Partial outcomes

### 15.1 Typed blocker

A blocker record contains:

- blocker ID and type;
- affected Task/attempt/artefact/review;
- evidence and discovery event;
- responsible owner/authority;
- severity and whether work must stop;
- exact resume condition;
- valid preserved artefacts/checkpoints;
- prohibited actions and claims;
- review deadline or escalation path.

Core blocker types:

```text
missing_input              provenance_conflict       dependency_incomplete
contract_pending           scientific_conflict       representation_conflict
resource_guardrail         authority_required        external_access
policy_violation           runtime_failure           provider_unavailable
review_unavailable         scope_ambiguity            other_typed_extension
```

Use `input_required` when a named human/authority choice is the resume condition; otherwise use `blocked`.

### 15.2 Attempt Partial

An attempt may end `partial` while the Task becomes `blocked`, `input_required`, `paused`, or remains `in_progress` for another authorized attempt. The attempt outcome records:

- completed obligations;
- unmet obligations;
- valid candidate artefacts;
- invalid or unverified artefacts;
- guardrail or evidence causing stop;
- claim restrictions;
- recommended next command without executing it.

### 15.3 Task Partial

`ClosePartial` is a terminal governance decision for the current Task execution epoch. It requires:

- accepted useful outputs and exact acceptance scope;
- unmet acceptance criteria;
- unresolved blockers;
- downstream consumers allowed and prohibited;
- paper/claim restrictions;
- resume policy: new Task, superseding revision, or authorized reopen.

Reopening creates a new execution epoch and preserves the original Partial outcome. No status text is overwritten from Partial to Success.

## 16. Artefact manifests and validation

### 16.1 Manifest fields

Every artefact manifest contains:

| Group | Required fields |
|---|---|
| Identity | artefact ID, type, schema/version, aliases |
| Production | Task, dispatch, attempt, actor/profile, context packet |
| Code/environment | commit, branch/worktree identity, environment/toolchain fingerprint |
| Location | declared root ID, relative path/URI, size, media type |
| Integrity | SHA-256, creation/observation time, availability check |
| Inputs | input artefact IDs/hashes and dependency roles |
| Research provenance | dataset vintage, representation, parameters, seeds, sample restrictions where applicable |
| Validation | expected contract/schema IDs and validation-record refs |
| Authority | candidate/accepted/superseded/rejected scope and consumer restrictions |
| Operations | no-overwrite evidence, retention, confidentiality, external-data constraints |

Large result files, manuscripts, caches, and checkpoints remain in their domain roots. The manifest is small and canonical. One artefact ID binds one immutable content hash: changed bytes always receive a new `art_` ID and explicit derivation or supersession lineage.

### 16.2 Independent state dimensions

No single `valid: true` or `status: accepted` field may collapse these dimensions:

| Dimension | Values |
|---|---|
| Availability | `available`, `missing`, `inaccessible`, `quarantined` |
| Regenerability | `not_declared`, `regenerable_verified`, `non_regenerable`, `unknown` |
| Integrity | `unverified`, `verified`, `failed` |
| Structural validation | `not_run`, `passed`, `failed`, `partial`, `not_applicable` |
| Scientific review | `not_required`, `pending`, `approved`, `rejected`, `unable_to_verify` |
| Use authority | `candidate`, `accepted_for_scope`, `rejected`, `superseded`, `restricted` |

An artefact is usable by a consumer only if that consumer's policy predicate over all dimensions passes. `regenerable_verified` requires pinned producer code/environment, input identities and hashes, parameters/seeds, a regeneration command, and a deterministic content or semantic canary. Missing-but-regenerable does not become available by assertion; the consumer policy decides whether regeneration is required before use.

### 16.3 Validation record

A validation record declares:

- subject artefact/object and exact hash;
- validator identity/version and assertion scope;
- command/tool invocation or human procedure reference;
- inputs and environment;
- observed results and retained evidence;
- verdict and limitations;
- whether the check is deterministic, model-graded, or human-reviewed;
- creation actor and time.

A later validation does not edit the prior record. It supersedes or coexists with an explicit reason.

### 16.4 Supersession and continuing provenance

Supersession changes authority, not existence. An artefact may be:

- superseded for paper claims;
- retained as a comparison input;
- prohibited for new analyses;
- preserved for audit or reproducibility.

`ArtefactSuperseded` names replacement, scope, reason, effective time, and allowed continuing consumers. Deletion is a separate retention action and cannot be inferred.

## 17. Reviews

### 17.1 Review request

A review request is an immutable object with:

- review ID, subject IDs/hashes, and review type;
- governing Task/design/decision/contract versions;
- specific review questions;
- required evidence and assurance lanes;
- reviewer capability and required independence grade, including actor/session/context/model-family separation;
- subject-artefact and implementation-trace visibility policy, including excluded implementer conclusions/hidden reasoning;
- allowed verdicts;
- authority required to satisfy the gate;
- deadline and escalation rule.

Review types include `software`, `provenance`, `mathematical`, `statistical`, `topological`, `representation`, `claim`, `operations`, `adapter_parity`, and `migration`.

### 17.2 Review lifecycle

Review projection states are `requested`, `assigned`, `in_review`, `verdict_recorded`, `changes_requested`, `satisfied`, `withdrawn`, and `superseded`. `verdict_recorded` means a verdict exists; `satisfied` means the governing acceptance policy has accepted that verdict for a named gate. A new subject hash creates a new review request or an explicitly scoped delta review.

### 17.3 Review verdict

Verdicts are:

```text
approve
approve_with_conditions
changes_requested
reject
unable_to_verify
withdrawn
```

The verdict records findings, evidence, limitations, conditions, reviewer actor/profile/session/model metadata, context-manifest ID/hash, subject hash, producing-attempt relationship, trace-visibility evidence, and the independence grade established from those fields. A self-declared attestation alone establishes nothing. `approve_with_conditions` satisfies a gate only when the acceptance policy declares the conditions non-blocking and records their owner.

### 17.4 Review authority

- A reviewer cannot approve a subject hash it did not inspect.
- A changed subject requires a new review or an explicit bounded-delta review.
- R2/R3 implementers cannot be the sole governing-rule or scientific approver.
- R0/R1 may use delegated Manager acceptance when policy permits; R2 requires a distinct verifier context plus Manager acceptance; R3 and P-005 transitions require Stephen.
- A verifier may inspect the exact subject artefact but cannot inherit the producer's conclusion or hidden reasoning unless a declared delta-review policy requires and records that exposure.
- Passing software/provenance review cannot substitute for scientific review.
- A review verdict never changes Task state directly; `AcceptTask` references the satisfied review set.

## 18. Decisions and rule evaluations

### 18.1 Decision kinds

Core kinds:

```text
design_lock                 preregistration_amendment
methodological_exception    runtime_guardrail_override
result_interpretation       claim_promotion
scope_amendment             migration_authority
policy_exception            task_reopen
```

### 18.2 Decision lifecycle

Decision projection states are `proposed`, `under_review`, `resolved`, `rejected`, `expired`, and `superseded`. Only an authorized `ResolveDecision` command creates `resolved`; a recommendation, mechanical rule evaluation, or review verdict cannot do so implicitly.

### 18.3 Proposal and resolution

A decision proposal contains question, options, recommendation, governing evidence, affected Tasks/claims, required authority, expiry/review date, and consequences.

A resolution records:

- selected option or rejection;
- deciding actor and authority grant;
- evidence and reviews considered;
- effective scope and time;
- downstream commands permitted;
- superseded decisions;
- conditions and revisit triggers.

Reserved P-005 transitions require Stephen's explicit attributed resolution.

### 18.4 Mechanical rule evaluation

A deterministic pre-registered outcome mapping is a `RuleEvaluation`, not automatically a human decision. It records rule version, typed referent/estimand or mathematical object, compared subjects, metric and denominator, exact input IDs/hashes, calculation/validator, output, and evidence hash. A separate authorized Decision is required whenever policy promotes the output into interpretation, prose, claim, amendment, exception, or migration authority. Pure mechanical state projection may stand without a Decision. W5 owns the broader result-versus-decision policy.

This preserves the distinction seen in T1.9b between a mechanical output and a manuscript-facing lock.

### 18.5 Amendments

Amendments never edit prior decisions or pre-registrations. They declare:

- amended subject and version;
- fields/rules changed;
- rationale and evidence;
- whether producing work already occurred;
- affected Tasks/artefacts/claims;
- effective boundary;
- required redispatch, rerun, or disclosure.

An amendment after producing work cannot be presented as pre-registration.

## 19. Corrections and supersession

### 19.1 Correction event

`RecordCorrection` references the erroneous record, identifies the incorrect assertion, supplies corrected evidence/object, names affected projections/consumers, and records authority. The original event remains in the hash chain.

Reducers apply corrections only through explicit correction semantics; they never mutate or omit the original line silently.

### 19.2 Supersession graph

Tasks, objects, artefacts, reviews, and decisions use directed supersession links. Requirements:

- no cycles;
- replacement subject exists and is type-compatible;
- scope of supersession is explicit;
- continuing consumers are declared;
- transitive resolution is deterministic;
- historical references remain resolvable.

### 19.3 Reversal

A decision reversal creates a new decision resolution that supersedes the old one and explains changed evidence or authority. It does not relabel the old decision as if it never applied.

## 20. Authority and actor records

W4 defines exact profiles, but W2 requires every command/event to carry:

- stable actor ID;
- actor type: `human`, `agent`, `service`, or `importer`;
- provider/model/profile/session metadata reference where applicable;
- authority grant ID and scope;
- delegating actor where applicable;
- independence-evidence profile: producing-attempt relationship, prior roles, context-manifest ID/hash, model family/version, session, and trace-visibility class;
- actual time-bounded capability, not only a role name.

Authority grants are immutable versions specifying allowed command types, subject scope, risk ceiling, effective interval, delegability, and revocation. Replay uses the authority snapshot recorded at acceptance; it does not query today's policy to decide whether a historical event happened.

## 21. Deterministic replay and projections

### 21.1 Replay algorithm

A conforming rebuild:

1. enumerates event-batch files by path and filename position;
2. validates file schema, transaction completeness, and filename/start-position agreement;
3. validates contiguous global positions and previous-event hash chain;
4. validates event IDs, schema versions, object refs/hashes, and per-stream versions;
5. rejects duplicate or overlapping positions and streams;
6. dispatches each supported event to a pure versioned reducer;
7. records projection version and terminal source position/hash;
8. compares generated invariants and optional golden checksums;
9. writes projections atomically only after the full rebuild passes.

Reducers cannot read the current clock, provider session, environment variables, network, mutable Tracker, or optional index. Clock-dependent facts such as lease expiry require recorded events.

### 21.2 Unknown records

- Unknown major schema or event type stops replay.
- Unknown backward-compatible optional fields are preserved/ignored according to schema policy.
- A missing external artefact may produce an availability projection but cannot change the historical event.
- A broken hash/reference stops authoritative projection and emits a separate diagnostic.

### 21.3 Snapshots and indexes

Snapshots, SQLite, search indexes, dashboards, and compatibility views may accelerate startup but declare source position/hash, state hash, reducer/schema versions, and projector version. A snapshot becomes an authoritative replay anchor only after a full verification records its preceding chain, terminal position/hash, state checksum, reducer set, and recovery test. Replay from an accepted anchor plus all later events is a release acceptance test; periodic genesis replay remains an audit while supported. This permits retirement of pre-anchor reducer implementations only through an attributed compatibility decision that preserves the verifying snapshot and audit evidence. A snapshot mismatch triggers deletion/rebuild or fail-closed recovery, never event repair.

### 21.4 Drift detection

Generated files include source position/hash. Manual change produces `projection_drift` diagnostics. A stale log, Tracker, or paper dashboard cannot coexist as equally current authority; the generated view is rebuilt and the drift remains auditable.

## 22. Legacy import and compatibility records

### 22.1 Import envelope

Every imported observation contains:

- importer actor/tool/version;
- source path/URI and commit/hash;
- observed and imported times;
- legacy source type;
- W0 source-authority class;
- parsed alias and candidate mapping;
- confidence and unresolved conflicts;
- raw-source artefact reference;
- explicit statement of what was not inferred.

### 22.2 Two-step authority

`LegacyRecordObserved` records what the importer found. It does not create `TaskAccepted`, `DecisionResolved`, or `CompleteScope`. An authorized `AdoptLegacyAuthority` command may later map selected evidence to successor state after W9 review.

`Success`, `Complete`, `Done`, an empty bus, a merged branch, or a paper section is not independently sufficient for adoption.

### 22.3 Ownership modes

W1 modes remain exact:

- `legacy_owned`: ARS records observations only and never writes legacy state;
- `successor_owned`: ARS events are canonical and only non-shared ARS-namespaced compatibility views/import channels are permitted;
- `closed_reference`: legacy source is frozen evidence with no synchronization.

No command can change ownership mode without migration authority, collision checks, and an event naming the cutover position. `dual_owned` is schema-invalid.

### 22.4 Current boundary

T1.28, T0.3, unresolved Stage 2 work, retained worktrees, superseded-but-live artefacts, checkpoints/caches, and restricted data remain outside W2 migration. The live APM bus was read only to understand shape; W2 writes no bus, task log, Tracker, result, contract, branch, or worktree state.

## 23. Failure and recovery behavior

| Failure | Required result |
|---|---|
| Duplicate command after lost response | Return original receipt; no new events |
| Same idempotency key, different payload | Reject conflict; retain both submission traces under W6 policy |
| Stale expected stream version | Reject; caller must re-read and decide |
| Crash before event-batch rename | No accepted state; orphan objects/runtime file quarantined |
| Crash after atomic rename before receipt | Retry discovers committed command and returns receipt |
| Partial/corrupt batch file | Replay fails closed; file never treated as committed if publication protocol was followed |
| Event position gap or overlap | Authoritative projection stops with diagnostic |
| Second writer, divergent worktree ledger, or store-identity mismatch | Reject before allocation; preserve submission trace outside canonical lifecycle |
| Missing referenced object | Projection stops at offending event; no silent null |
| Lease expires while process runs | Record expiry; mark process/output orphan/late candidate; preserve evidence |
| Compatibility file has foreign content | Refuse write/import; create collision diagnostic |
| Successor task targets a shared legacy `task.md`/`report.md` slot | Reject path registration; Task remains legacy-owned or uses a namespaced view |
| Independence grade relies only on attestation or reused producer context | Verdict cannot satisfy gate; request a compliant verifier context |
| Attempt produces result after cancellation | Register as late candidate, never auto-accept |
| Validation passes but scientific review fails | Preserve both records; block artefact use and Task acceptance |
| Reviewer inspects stale hash | Verdict cannot satisfy gate |
| Stage completion omits a member | Reject `CompleteScope` command |
| Supersession cycle | Reject command |
| Unknown event major version | Stop rebuild until supported reader exists |

## 24. Minimal illustrative records

### 24.1 Task object excerpt

```json
{
  "schema_id": "ars://core/task-definition",
  "schema_version": "1.0.0",
  "task_id": "tsk_01979c31-6710-7a2d-8d4b-6d2c62e07f51",
  "record_revision": 1,
  "aliases": [
    {"namespace": "example.task", "value": "T2.7", "scope_id": "prj_01979c31-4e54-7c6f-8a0f-87d2f232c7c4"}
  ],
  "objective": "Produce the bounded evidence artefacts named by the governing design.",
  "scope_definition_ref": {"record_id": "obj_01979c31-8bcb-73f3-a10c-f786729dc81b", "revision": 3},
  "dependencies": [],
  "expected_artefact_types": ["result_json", "validation_report"],
  "concurrency_mode": "exclusive",
  "content_hash": "<sha256>"
}
```

### 24.2 Event excerpt

```json
{
  "event_id": "evt_01979c31-a089-78fb-8df4-e27f9d48b9e2",
  "event_type": "DispatchIssued",
  "schema_id": "ars://core/event/dispatch-issued",
  "schema_version": "1.0.0",
  "project_id": "prj_01979c31-4e54-7c6f-8a0f-87d2f232c7c4",
  "stream_id": "tsk_01979c31-6710-7a2d-8d4b-6d2c62e07f51",
  "stream_version": 4,
  "global_position": 1234,
  "transaction_id": "txb_01979c31-a02e-75a2-bd42-84b6e6247d70",
  "transaction_index": 1,
  "transaction_count": 2,
  "command_id": "cmd_01979c31-9fdf-7bb6-a980-81936acec7df",
  "actor_id": "act_01979c31-9d7d-7358-91c3-4c3db7775361",
  "authority_grant_id": "agr_01979c31-9dca-721e-bc45-d93ad4d68519",
  "payload": {"dispatch_id": "dsp_01979c31-a044-72d0-a9ce-0a7d8e908927"},
  "previous_event_hash": "<sha256>",
  "event_hash": "<sha256>"
}
```

Examples omit optional trace fields but are otherwise consistent with the proposed format. Placeholder hashes make them illustrative, not fixture data.

## 25. Core invariants

1. Canonical IDs never depend on path, provider, branch, role slug, or human task number.
2. One accepted command produces one complete atomic event batch.
3. Every event position and stream version is unique and contiguous within its scope.
4. Commands never mutate state without authority, expected version, and idempotency validation.
5. Messages never substitute for commands or decisions.
6. Task, dispatch, attempt, lease, review, and artefact state machines remain separate.
7. Attempt completion never implies Task acceptance.
8. Checkpoint existence never implies a running or successful Task.
9. Partial records completed and unmet obligations without weakening requirements.
10. Reopen creates a new execution epoch and preserves the prior terminal outcome.
11. Artefact availability, integrity, structural validity, scientific review, and use authority never collapse into one boolean.
12. Review verdicts bind to exact subject hashes.
13. R2/R3 governing rules and scientific acceptance cannot be self-approved by the sole implementer.
14. Scope completion requires every member's typed disposition under an exact scope revision.
15. Supersession changes authority within a declared scope but never erases lineage.
16. Compatibility writes prove ownership and fail closed on collision.
17. Clearing a compatibility file is acknowledgement, not deletion.
18. Rebuild uses only canonical records and pure reducers.
19. Legacy observation and successor adoption are separate events.
20. Restricted data, secrets, and hidden reasoning never enter core records.
21. One registered writer allocates all global positions for one project control store.
22. Task-worktree branches never contain or merge independently advanced canonical ledgers.
23. A successor-owned compatibility path is non-shared with unmodified legacy tooling.
24. Review independence is computed from recorded evidence and cannot be satisfied by attestation alone.

## 26. Historical fixture acceptance matrix

| Fixture | W2 representation and expected control |
|---|---|
| F-001 | Two dispatch/message IDs and immutable events survive; ownership mismatch rejects overwrite |
| F-002 | Task assignment and report are distinct messages/streams; report acknowledgement cannot occupy or erase dispatch state |
| F-003 | Dispatch carries explicit control/code/result/cache root bindings; current directory is irrelevant |
| F-004 | Accepted result/review events outrank stale manual log; projection drift is diagnosed |
| F-005 | `CompleteScope` requires the exact 22-member scope revision and a disposition for every member |
| F-006 | Paper dashboard is a projection with source position/hash and rebuilds from events |
| F-007 | Benchmark and prerequisite obligations are Task/resource records; hidden uncapped work blocks readiness/acceptance |
| F-008 | Feasibility validation records backend, sample size, worker count, memory, and projection limitations |
| F-009 | Guardrail produces blocker/input-required/Partial and a separate explicit override decision |
| F-010 | Correction/supersession scope preserves valid upstream artefacts and rejects unauthorized expansion |
| F-011 | Artefact/input manifests and representation assurance bind frozen transform identity |
| F-012 | Null-operation validation is a required evidence record before readiness/acceptance |
| F-013 | Input artefact hashes/vintages and dependency predicates reject incoherent assembly |
| F-014 | Authority grants and review independence prevent sole implementer contract activation/acceptance |
| F-015 | Review records distinguish sanity bounds from target values and bind to inspected evidence |
| F-016 | Scientific review/known-case validation can reject structurally valid output |
| F-017 | Consumer-required fields are Task acceptance criteria and structural validations |
| F-018 | Scoped supersession preserves comparison/audit consumers and full lineage |
| F-019 | Claim-promotion decision requires claim review and cannot be inferred from result acceptance |
| F-020 | Policy/adapter versions are event/object references; parity review gates adapter use |
| F-021 | Context manifest binds the governing amendment and omission record; stale pre-amendment context cannot satisfy review/readiness |
| F-022 | Independence grade compares producer/verifier actors, sessions, model families, context manifests, and trace visibility |
| F-023 | P-005 decisions require an explicit attributed resolution; ambiguous prose/status cannot resolve them |
| F-024 | Qualitative artefacts use provenance/lifecycle/review/authority records while deterministic scientific validation may be `not_applicable` |

### Required W2 stress scenarios

1. Lost response followed by identical retry yields one event batch and the original receipt.
2. Two actors claim an exclusive dispatch; exactly one claim succeeds by expected version/lease.
3. An attempt expires, continues computing, and emits a late artefact that remains visible but unusable pending review.
4. A Partial attempt resumes under a new attempt without rewriting its stop reason or checkpoints.
5. Two comparative attempts produce conflicting valid artefacts; neither is silently selected.
6. A compatibility task file contains another Task's ownership marker; write is rejected and both messages survive.
7. A reviewer approves hash A after the producer publishes hash B; the verdict cannot satisfy B's gate.
8. A stage completion command names only eight of twenty-two Tasks; command is rejected.
9. SQLite/projections are deleted; replay recreates identical state and checksums.
10. An unknown event major version stops authoritative rebuild before any new projection is published.
11. The writer crashes before/after atomic rename; recovery produces zero or one committed batch and the correct receipt.
12. Two task branches submit against the same tail; the single service allocates distinct positions or rejects stale intent, and no divergent ledger can be merged.
13. A malformed or unauthorized adapter command is rejected without a canonical event.
14. Backup/restore on another machine verifies store identity, chain, snapshots, and external artefact availability before service start.
15. A supersession cycle is rejected without changing authority.
16. No evaluated R3 provider is available; the Task waits rather than routing to a sub-threshold model.

## 27. Verification programme

### 27.1 Schema verification

Implementation planning must provide deterministic tests for:

- all ID prefixes and UUIDv7 validation;
- canonical JSON and content/event hashes;
- schema/version compatibility;
- reference and revision resolution;
- command authority, expected-version, and idempotency checks;
- every allowed and forbidden state transition;
- transaction position, count, and hash-chain integrity;
- supersession cycles and scope;
- artefact multidimensional state;
- review subject-hash and evidence-derived independence binding;
- compatibility ownership markers;
- secret/restricted-data rejection.

### 27.2 Replay verification

- golden dedicated ledgers rebuild expected projections from genesis and accepted snapshot anchors;
- repeated replay is byte-stable except declared generated timestamps, which are excluded from canonical projections;
- incremental replay equals full replay;
- optional snapshot/index removal changes no projected state;
- corrupted, missing, duplicate, overlapping, reordered, and unknown-major events fail before publication;
- object or artefact unavailability is represented without rewriting history.

### 27.3 Research-assurance classification

W2 touches Output/Provenance and Paper Claim governance and defines carrying fields for all assurance lanes. It changes no formula, null, estimand, representation, topological result, or paper claim.

Machine-checkable claims include identity, transition legality, version/hash integrity, authority presence, review independence evidence, artefact-field completeness, regenerability evidence, scope-member dispositions, ownership paths, writer/store identity, and replay determinism.

Human-review questions are:

1. Does separation of execution, validation, review, and decision prevent structurally valid but scientifically invalid work from being accepted?
2. Are Partial and reopen semantics conservative enough for long mathematical runs without making recovery impractical?
3. Do scope completion and supersession rules preserve negative and unresolved evidence without freezing the programme?

## 28. Constraints passed downstream

### W3

Context packets, memory, and retrieval use canonical IDs/revisions/hashes; they cannot alter state. Context compilation references Task, dispatch, assurance, source positions, governing amendments, omission records, and producing-attempt relationships needed to establish independence.

### W4

Profiles and routing instantiate actor, authority grant, evidence-derived independence grade, model/eval profile, delegated acceptance, risk ceiling, and fallback fields required here.

### W5

Assurance packs define Task assurance requirements, validation types, review questions, governing-rule objects, and consumer predicates without changing core lifecycle.

### W6

Fixtures must generate commands/events/messages/artefacts/reviews and grade both outcome and trajectory. Scientific properties are independently recomputed or bounded; model-family/context independence is graded. Rejected receipts and traces obey privacy/retention rules.

### W7

Adapters translate provider actions into commands/messages and expose receipts. They cannot write event batches directly or register a successor view at a shared legacy path.

### W8

Resource grants, heartbeat cadence, personal-machine sleep/resume handling, lease expiry, process identity, checkpoint fingerprinting, stop confirmation, control-store backup, and orphan handling extend the records defined here.

### W9

Migration uses two-step observation/adoption, exclusive ownership modes, non-shared successor paths, explicit cutover events, and no inferred acceptance from mutable legacy prose.

## 29. Proposed decisions introduced by W2

The decision register must record, pending W2 review:

- atomic JSONL batch-per-command storage;
- prefixed UUIDv7 canonical IDs with scoped aliases;
- separate Task and operational state machines;
- immutable messages with clearing-as-acknowledgement;
- attempt and Task Partial/reopen semantics;
- multidimensional artefact validation and authority;
- exact ScopeDefinition revision for milestone completion;
- review verdict binding to exact subject hash;
- project-wide writer/control-store identity and non-shared compatibility paths;
- evidence-derived reviewer independence and delegated acceptance;
- typed RuleEvaluation referents and regenerability evidence;
- verified-snapshot replay anchors and reserved F-021–F-024/S-011–S-016 coverage.

## 30. W2 review gate

W2 can move from `review_pending` to `accepted` only when Stephen and the current Manager confirm:

- [ ] Atomic JSONL batches in one dedicated linear ledger satisfy W1’s canonical-storage decision without SQLite or per-worktree ledgers.
- [ ] ID format, aliases, revisions, and hashes are sufficiently stable and provider-neutral.
- [ ] Command, receipt, event, object, message, artefact, validation, review, decision, and projection meanings are non-overlapping.
- [ ] Task status is correctly separated from dispatch, attempt, lease, checkpoint, and review status.
- [ ] Every lifecycle transition has a typed command/event, precondition, and authority boundary.
- [ ] Dispatch, claim, lease, retry, cancellation, and idempotency preserve all attempts and messages.
- [ ] Partial, blocked, input-required, pause, resume, reopen, and supersession semantics fit long-running mathematical work.
- [ ] Artefact existence, integrity, structural validation, scientific review, and use authority remain distinct.
- [ ] Review and decision records enforce evidence-derived independence, delegated R0–R2 acceptance, and P-005/R3 human approvals.
- [ ] Scope completion cannot omit Plan-defined work without a versioned scope amendment.
- [ ] Genesis and accepted-snapshot replay fail closed on corruption, gaps, unknown schemas, stale projections, and control-store identity mismatch.
- [ ] Compatibility ownership applies the titled 2026-06-28 bus-ownership observation and prevents shared legacy/successor write paths.
- [ ] Legacy observation cannot silently become successor acceptance.
- [ ] F-001–F-024 and S-001–S-016 are representable with explicit provenance and dependency status.
- [ ] T1.28 and the W0 no-migration set remain untouched.
- [ ] W3–W9 can extend these records without reversing W1 dependency direction.

## 31. W2 outcome

**Outcome:** `MANAGER_REVIEW_PENDING — greenfield-foundation implementation prohibited pending Manager confirmation and P-026 downstream gates; legacy migration separately prohibited`.

W3 may now consume W2 v0.3 while Manager review remains pending. A foundation implementation plan begins only after W1/W2 Manager confirmation and the accepted P-026 downstream interfaces. T1.28 terminal evidence still requires a bounded W0/W2 reconciliation before any legacy adoption or migration, but does not hold the greenfield foundation.
