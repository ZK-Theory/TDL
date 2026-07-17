# 06d — WP6.1 literal owner-source catalogue

**Date:** 2026-07-17<br>
**Status:** normative plan annex approved under P-036 at exact reviewed plan revision
`fe5f1d40bc8f05f061317c677b5891cea0711249`; authorizes no implementation<br>
**Authority:** accepted W2 §§10–19 and W8 §20; parent plan 06a §3; P-036

This annex is the pre-implementation expected set for WP6.1. A test may parse these
rows, but it must not derive, expand, repair, or filter them from runtime registrations.
Each `key` is unique and is the normalized catalogue identity. Missing, extra, aliased,
or duplicate keys fail before any implementation-completeness claim can pass.

## 1. Closed conventions

- Each row's `cmd/x` / `CommandType` pair is exact. `cmd/x` means
  `.research-system/schemas/core/commands/x.schema.json`; that command-specific schema
  sets `command_type` to the paired PascalCase value with `const`. The versioned
  command identity is the triple (`command_schema_id`, `command_schema_version`,
  `command_schema_sha256`), with `command_type` fixed by that schema. The same complete
  identity is bound by the authority grant, dispatcher, emitted event(s), receipt, and
  WP6 idempotency tuple. W8's snake-case owner tokens map one-to-one to the
  paired PascalCase values shown in §4; this mapping is authoritative for dispatch
  planning under P-036 at the exact reviewed revision above. Its future materialized
  schema-identity manifest still requires separate independent review and exact-hash
  owner acceptance under D-G6-3. No alias is accepted.
- Event schema `evt/x` means
  `.research-system/schemas/core/events/x.schema.json`. Command and event schemas are
  strict, versioned, and registered by exact content hash. A row's listed semantic
  events form its complete ordered event set; a singular event is a one-member set.
- `task_nonterminal` is the closed set `{draft, readiness_pending, ready, in_progress,
  review_pending, blocked, input_required, paused}`. `task_suspended` is
  `{blocked, input_required, paused}`. `task_prior_active` is
  `{draft, readiness_pending, ready, in_progress, review_pending}`. Tests expand these
  classes from this annex's literal sets, never from reducer or registry state names.
- `task_blockable`, `task_input_requestable`, and `task_pausable` equal
  `task_nonterminal` minus `blocked`, `input_required`, and `paused`, respectively;
  no state-preserving suspension edge is implied.
- `attempt_nonterminal` is `{created, claimed, running, paused, stopping}`;
  `attempt_retryable` is `{completed, failed, partial, abandoned}`;
  `review_nonterminal` is `{requested, assigned, in_review, verdict_recorded,
  changes_requested}`; `decision_unresolved` is `{proposed, under_review}`.
- Receipt `R` is the W2 accepted/duplicate/rejected/conflict receipt with command ID,
  idempotency tuple, canonical payload hash, expected/observed versions, event-batch
  ID/hash when accepted, and stable rejection code when rejected.
- Every positive test named below asserts exactly one accepted receipt, the named
  semantic event(s), the named reducer/projection change, and replay equality.
- Every table row is one complete binding record. Its logical key, command type,
  command/event schema IDs and hashes, owner discriminator and exact from/to edge,
  ordered event set, reducer set, projection set or typed selector, authority rule,
  receipt identity, positive-test identity, and expanded negative-test identities retain
  row cardinality even when implementation callables are shared. No component-wide set
  may credit one implementation or one test to two expected rows.
- Negative profiles are closed sets:
  - `N0`: missing field; wrong type; missing/wrong authority; expired grant;
    prohibited actor; wrong authority scope; wrong authority subject kind or ID; stale
    expected version; conflicting payload; same idempotency tuple with different
    payload; atomic no-event/no-receipt-acceptance/no-projection side effect.
  - `NE`: `N0` plus illegal from-state/to-state and invalid command subject identity.
  - `NA`: `NE` plus an authority-rule mutation that retains the command type but changes
    its accepted subject binding or actor class.
  - `NI`: `NA` plus stale subject hash, ineligible/self-related reviewer, insufficient
    independence grade, and incomplete governing review set.
  - `NC`: `NA` plus competing claim/reservation, incompatible lease or checkpoint,
    and preserved predecessor evidence.
  - `NS`: `NA` plus supersession cycle, absent/type-incompatible replacement, missing
    continuing-consumer disposition, and attempted history mutation.
- A row's negative-profile cell is its complete applicable set. Implementations may add
  stricter negatives but may not omit or reinterpret any named member.

### 1.1 Independently accepted command/event-schema identities

T1 has a contract-materialization phase before runtime implementation. It writes the
strict manifest `.research-system/contracts/wp6-1-schema-identities.yaml`,
validated by
`.research-system/schemas/contracts/wp6-1-schema-identities.schema.json`
version `1.0.0`. The manifest contains exactly 104 rows keyed one-to-one by this annex.
Every row repeats its literal `command_type` and schema repository path and supplies the
schema's canonical `$id` as `command_schema_id`, literal `schema_version`, and SHA-256 of
the canonical UTF-8/LF schema bytes as `command_schema_sha256`. It also contains the
complete ordered `event_schema_bindings`; each binding supplies the event type, schema
path, canonical `event_schema_id`, literal `event_schema_version`, and
`event_schema_sha256`. `additionalProperties` is `false` at every object level. Shared
command/event schemas repeat the identical identities in each applicable row;
repetition never collapses catalogue cardinality.

The contract author produces the command schemas and manifest from this annex, a
reviewer who did not implement the schemas independently checks every row against this
annex and recomputes every hash, and Stephen accepts the exact manifest repository path,
schema ID/version, Git blob ID, and SHA-256 in D-G6-3. Runtime registrations and the
schema registry are observed comparison inputs only. They may not produce, fill, filter,
or repair the expected manifest. No dispatcher/reducer implementation starts until that
acceptance is recorded.

For each accepted command, the W2 envelope carries the accepted schema ID and version
and the service resolves and records the accepted content hash. Authority grants contain
the same complete versioned identity in `allowed_command_identities`; dispatcher keys
are the complete identity, not `command_type` alone; every emitted event and receipt
records `command_schema_id`, `command_schema_version`, and `command_schema_sha256`; and
the WP6 idempotency tuple is `(actor_id, authority_scope, command_type,
command_schema_id, command_schema_version, command_schema_sha256, idempotency_key)`.
The event-batch hash covers those fields. A retained `command_type` with any changed
schema ID, version, or content hash rejects before authority reuse, idempotency lookup,
position allocation, event publication, or receipt acceptance.

### 1.2 Closed authority-subject bindings

Every one of the 104 semantic-copy rows contains `authority_subject_kind`,
`authority_subject_id_source`, `authority_scope_source`, and `allowed_actor_classes`.
The following table is the complete expected mapping. `envelope.target_stream_id` means
the typed ID of the existing governed record. `payload.new_*_id` is used only for a
create/publish/register command; the grant must already bind that exact proposed ID.

| Catalogue key family / exception | Exact subject kind | Exact subject-ID source |
|---|---|---|
| `scope.*` | `scope_definition` | existing: `envelope.target_stream_id`; `scope.create`: `payload.new_scope_definition_id` |
| `task.*` | `task` | existing: `envelope.target_stream_id`; `task.create`: `payload.new_task_id` |
| `dispatch.*`, including both `ClaimDispatch` rows | `dispatch` | `payload.dispatch_id` (must equal the Dispatch member of the declared write set; claim may affect only the Task revision stored on that Dispatch) |
| `lease.*`, `operator.claim_execution_lease`, `operator.record_heartbeat` | `lease` | existing: `envelope.target_stream_id`; create/claim: `payload.new_lease_id` |
| `attempt.*`, `operator.request_pause`, `operator.confirm_pause`, `operator.request_stop`, `operator.confirm_stop`, `operator.request_resume`, `operator.quarantine_orphan` | `attempt` | existing: `envelope.target_stream_id`; `attempt.create`/`attempt.retry`: `payload.new_attempt_id` |
| `checkpoint.record` | `attempt` | `payload.attempt_id` |
| `message.*` | `message` | existing delivery/ack/failure: `envelope.target_stream_id`; publish: `payload.new_message_id` |
| `blocker.*` | `blocker` | existing: `envelope.target_stream_id`; `blocker.record`: `payload.new_blocker_id` |
| `artefact.*`, `operator.adopt_late_artefact` | `artefact` | existing: `envelope.target_stream_id`; `artefact.register`: `payload.new_artefact_id` |
| `review.*` | `review` | existing: `envelope.target_stream_id`; `review.request`: `payload.new_review_id` |
| `decision.*` | `decision` | existing: `envelope.target_stream_id`; `decision.propose`: `payload.new_decision_id` |
| `rule.evaluate` | `rule_evaluation` | `payload.new_rule_evaluation_id` |
| `correction.record` | `corrected_record` | `payload.erroneous_record_id`, paired with the closed kind in §1.4 |
| `operator.request_resource_grant`, `operator.release_resources` | `resource` | `payload.resource_id` |
| `operator.create_backup`, `operator.verify_restore` | `project_store` | `payload.project_id` |

For every row, `authority_scope_source` is the canonical tuple
`(envelope.project_id, authority_subject_kind, authority_subject_id_source)`,
`authority_grant_id_source` is `envelope.authority_grant_id`, and the effective/expiry
source is the immutable content-addressed grant's `effective_at`/`expires_at`, tested
against the command acceptance time before version/state checks. The exact allowed
actor classes for this WP6 catalogue are `{human, agent, service}`; `importer` is
prohibited. A row's named authority rule and grant can narrow capability within those
classes but cannot widen or replace this expected actor set. Missing/wrong/expired or
not-yet-effective grant, prohibited actor, wrong scope, wrong subject kind, wrong
subject ID, and an authority-rule mutation are executed for every row before
version/state tests and leave the event tail, receipt acceptance state, and every
projection unchanged.

### 1.3 Atomic `ClaimDispatch` contract

The two `ClaimDispatch` catalogue rows are mandatory facets of one atomic command, not
two independently publishable claims. Its envelope/payload binds `dispatch_id`,
`expected_dispatch_stream_version`, `task_id`, `task_revision`,
`expected_task_stream_version`, `expected_global_position`, and `expected_tail_hash`.
Its declared write set is exactly the Dispatch stream and Task stream with their two
expected versions. The accepted ordered atomic batch is exactly
`[DispatchClaimed, TaskClaimStarted]`: `DispatchClaimed` is on the Dispatch stream under
`evt/dispatch_claimed`; `TaskClaimStarted` is on the Task stream under
`evt/task_claim_started` and binds the same command, Dispatch, Task revision, and lease.
Replay applies `acknowledged → claimed` to Dispatch and `ready → in_progress` to the
bound Task revision atomically. The receipt returns both event identities and both
resulting stream versions.

After validating the Dispatch-scoped grant itself, and before reusing that authority
for the Task facet, idempotency lookup, version advancement, or position allocation,
the service loads the accepted Dispatch revision and requires
`(dispatch.task_id, dispatch.task_revision) == (payload.task_id,
payload.task_revision)`. The active lease must bind that same Task revision and
Dispatch. Dispatch-scoped authority is sufficient only for the Task revision already
stored on the authorized Dispatch; it never authorizes the caller to nominate another
Task. A current foreign Task ID/revision, a stale Dispatch-to-Task link, or a lease bound
to another Task or Dispatch rejects before publication and changes neither stream,
receipt acceptance state, nor any projection.

The semantic copy gives `task.claim_start` and `dispatch.claim` the same
`atomic_binding_group: claim_dispatch_task_dispatch_v1`, with exact group cardinality
two. Omission of either facet, omission or staleness of only the Task binding, a
concurrent Task mutation, a mismatched Task revision, a current foreign Task with a
valid version, a stale stored Dispatch-to-Task relation, a wrong lease subject, an
extra/missing write-set member, or a batch/receipt naming only Dispatch rejects before
publication and changes neither projection.

### 1.4 Closed correction-selector mapping

`projection_selector/corrected_record_kind/v1` has this complete accepted domain. Each
kind selects exactly the listed owner projection and, separately, the governance
correction index; no second owner projection is permitted.

| `corrected_record_kind` | Owner projection |
|---|---|
| `scope_definition` | `scope` |
| `task` | `task` |
| `dispatch` | `dispatch` |
| `lease` | `lease` |
| `attempt` | `attempt` |
| `checkpoint` | `checkpoint` |
| `message` | `message` |
| `blocker` | `blocker` |
| `artefact` | `artefact` |
| `review` | `review` |
| `decision` | `decision` |
| `rule_evaluation` | `rule_evaluation` |
| `resource` | `resource` |
| `operation` | `operations` |
| `backup` | `backup` |

The table is copied literally into the accepted semantic YAML before implementation;
the runtime selector registry is comparison input only. Unknown kinds, a swapped
mapping, zero or multiple owner projections, and omission of the governance correction
index reject before publication and leave all projections unchanged.

Decision and RuleEvaluation are non-compensable owner records. A Decision-scoped grant
or Decision projection cannot authorize or absorb `RecordRuleEvaluation`; a
RuleEvaluation-scoped grant or projection cannot authorize or absorb
`ResolveDecision`. Tests corrupt both a candidate expected manifest and runtime selector
to make either substitution self-consistent and still require rejection against the
accepted manifest identity, with the event tail, receipt acceptance state, Decision
projection, RuleEvaluation projection, and governance correction index unchanged.

## 2. Task, scope, dispatch, lease, attempt, and checkpoint rows

| Key | Owner transition/discriminator | Command schema / exact `command_type`; ordered event set; event schema | Reducer; exact projections/selector | Authority / precondition | Receipt; distinct positive test; negatives |
|---|---|---|---|---|---|
| `scope.create` | W2 §10 `none → open` | `cmd/create_scope_definition` / `CreateScopeDefinition`; `ScopeDefinitionCreated`; `evt/scope_definition_created` | `reduce_scope`; scope, governance | unique ID; complete versioned membership, dispositions, predicate, authority | `R`; `pos_scope_create`; `NA` |
| `scope.amend_revision` | W2 §10 `open → open(new revision)` | `cmd/amend_scope_definition` / `AmendScopeDefinition`; `ScopeDefinitionAmended`; `evt/scope_definition_amended` | `reduce_scope`; scope, governance | exact prior revision; member changes, authority, effective boundary | `R`; `pos_scope_amend_revision`; `NS` |
| `scope.supersede` | W2 §10 `open → superseded` | `cmd/supersede_scope_definition` / `SupersedeScopeDefinition`; `ScopeDefinitionSuperseded`; `evt/scope_definition_superseded` | `reduce_scope`; scope, governance | replacement revision/ID, lineage, member disposition effects | `R`; `pos_scope_supersede`; `NS` |
| `scope.complete` | W2 §10 `open → complete` | `cmd/complete_scope` / `CompleteScope`; `ScopeCompleted`; `evt/scope_completed` | `reduce_scope`; scope, governance | exact ScopeDefinition revision; typed disposition for every required member | `R`; `pos_scope_complete`; `NA` |
| `task.create` | W2 §11 `none → draft` | `cmd/create_task` / `CreateTask`; `TaskCreated`; `evt/task_created` | `reduce_task`; task, governance | unique Task ID and valid revision | `R`; `pos_task_create`; `NA` |
| `task.amend_revision` | W2 §§10–11 `task_nonterminal → same status(new revision)` | `cmd/amend_task` / `AmendTask`; `TaskAmended`; `evt/task_amended` | `reduce_task`; task, governance | exact prior revision; changed typed fields, rationale, authority, effective boundary | `R`; `pos_task_amend_revision`; `NS` |
| `task.request_readiness` | W2 §11 `draft → readiness_pending` | `cmd/request_readiness` / `RequestReadiness`; `ReadinessRequested`; `evt/readiness_requested` | `reduce_task`; task, governance | definition complete enough to evaluate | `R`; `pos_task_request_readiness`; `NE` |
| `task.approve_readiness` | W2 §11 `readiness_pending → ready` | `cmd/approve_readiness` / `ApproveReadiness`; `ReadinessApproved`; `evt/readiness_approved` | `reduce_task`; task, governance | complete passing readiness evidence | `R`; `pos_task_approve_readiness`; `NA` |
| `task.block` | W2 §11 `task_blockable → blocked` | `cmd/block_task` / `BlockTask`; `TaskBlocked`; `evt/task_blocked` | `reduce_task`; task, governance | typed blocker, owner, resume condition | `R`; `pos_task_block`; `NE` |
| `task.request_input` | W2 §11 `task_input_requestable → input_required` | `cmd/request_input` / `RequestInput`; `InputRequested`; `evt/input_requested` | `reduce_task`; task, governance, message | named authority, question, resume condition | `R`; `pos_task_request_input`; `NA` |
| `task.pause` | W2 §11 `task_pausable → paused` | `cmd/pause_task` / `PauseTask`; `TaskPaused`; `evt/task_paused` | `reduce_task`; task, governance, operations | typed reason, owner, resumable state | `R`; `pos_task_pause`; `NE` |
| `task.claim_start` | W2 §11 `ready → in_progress`; atomic group `claim_dispatch_task_dispatch_v1` | `cmd/claim_dispatch` / `ClaimDispatch`; `[DispatchClaimed, TaskClaimStarted]`; `[evt/dispatch_claimed, evt/task_claim_started]` | `reduce_dispatch` + `reduce_task`; task, dispatch, operations | payload Task ID/revision equals the Task revision stored on Dispatch; exact Task/Dispatch versions and two-stream write set; lease binds both; authority, context, roots | `R` with both events/versions; `pos_task_claim_start`; `NC` |
| `task.submit_review` | W2 §11 `in_progress → review_pending` | `cmd/submit_for_review` / `SubmitForReview`; `TaskSubmittedForReview`; `evt/task_submitted_for_review` | `reduce_task`; task, governance, review | attempt outcome and candidate artefacts recorded | `R`; `pos_task_submit_review`; `NA` |
| `task.resume` | W2 §11 `task_suspended → task_prior_active` | `cmd/resume_task` / `ResumeTask`; `TaskResumed`; `evt/task_resumed` | `reduce_task`; task, governance, operations | exact prior allowed state; blocker resolved or authority supplied | `R`; `pos_task_resume`; `NE` |
| `task.accept` | W2 §11 `review_pending → accepted` | `cmd/accept_task` / `AcceptTask`; `TaskAccepted`; `evt/task_accepted` | `reduce_task`; task, governance | exact satisfied review/acceptance set | `R`; `pos_task_accept`; `NI` |
| `task.reject` | W2 §11 `review_pending → rejected` | `cmd/reject_task` / `RejectTask`; `TaskRejected`; `evt/task_rejected` | `reduce_task`; task, governance | authorized verdict bound to evidence | `R`; `pos_task_reject`; `NI` |
| `task.close_partial` | W2 §11 `task_nonterminal → partial` | `cmd/close_partial` / `ClosePartial`; `PartialOutcomeRecorded`; `evt/partial_outcome_recorded` | `reduce_task`; task, governance | useful outputs, unmet obligations, restrictions, resume policy | `R`; `pos_task_close_partial`; `NA` |
| `task.cancel` | W2 §11 `task_nonterminal → cancelled` | `cmd/cancel_task` / `CancelTask`; `TaskCancelled`; `evt/task_cancelled` | `reduce_task`; task, governance, operations | cancellation authority and terminal process disposition | `R`; `pos_task_cancel`; `NA` |
| `task.supersede` | W2 §11 `task_nonterminal → superseded` | `cmd/supersede_task` / `SupersedeTask`; `TaskSuperseded`; `evt/task_superseded` | `reduce_task`; task, governance | replacement ID/revision and lineage | `R`; `pos_task_supersede`; `NS` |
| `task.reopen_partial` | W2 §11 `partial → readiness_pending` | `cmd/reopen_task` / `ReopenTask`; `TaskReopened`; `evt/task_reopened` | `reduce_task`; task, governance | explicit authority, new epoch, reason, preserved terminal record | `R`; `pos_task_reopen_partial`; `NS` |
| `task.reopen_rejected` | W2 §11 `rejected → readiness_pending` | `cmd/reopen_task` / `ReopenTask`; `TaskReopened`; `evt/task_reopened` | `reduce_task`; task, governance | explicit authority, new epoch, reason, preserved terminal record | `R`; `pos_task_reopen_rejected`; `NS` |
| `task.reopen_cancelled` | W2 §11 `cancelled → readiness_pending` | `cmd/reopen_task` / `ReopenTask`; `TaskReopened`; `evt/task_reopened` | `reduce_task`; task, governance | explicit authority, new epoch, reason, preserved terminal record | `R`; `pos_task_reopen_cancelled`; `NS` |
| `dispatch.issue` | W2 §12 `none → issued` | `cmd/issue_dispatch` / `IssueDispatch`; `DispatchIssued`; `evt/dispatch_issued` | `reduce_dispatch`; dispatch, queue, operations | ready Task; exact route/context/root/policy/resource bindings | `R`; `pos_dispatch_issue`; `NA` |
| `dispatch.deliver` | W2 §12 `issued → delivered` | `cmd/record_dispatch_delivery` / `RecordDispatchDelivery`; `DispatchDelivered`; `evt/dispatch_delivered` | `reduce_dispatch`; dispatch, queue, message | exact dispatch and delivery evidence | `R`; `pos_dispatch_deliver`; `NE` |
| `dispatch.acknowledge` | W2 §12 `delivered → acknowledged` | `cmd/acknowledge_dispatch` / `AcknowledgeDispatch`; `DispatchAcknowledged`; `evt/dispatch_acknowledged` | `reduce_dispatch`; dispatch, queue | authorized recipient and delivery identity | `R`; `pos_dispatch_acknowledge`; `NE` |
| `dispatch.claim` | W2 §12 `acknowledged → claimed`; atomic group `claim_dispatch_task_dispatch_v1` | `cmd/claim_dispatch` / `ClaimDispatch`; `[DispatchClaimed, TaskClaimStarted]`; `[evt/dispatch_claimed, evt/task_claim_started]` | `reduce_dispatch` + `reduce_task`; task, dispatch, queue, operations | payload Task ID/revision equals the Task revision stored on Dispatch; exact Task/Dispatch versions and two-stream write set; valid exclusive lease binds both | `R` with both events/versions; `pos_dispatch_claim`; `NC` |
| `dispatch.fulfil` | W2 §12 `claimed → fulfilled` | `cmd/fulfil_dispatch` / `FulfilDispatch`; `DispatchFulfilled`; `evt/dispatch_fulfilled` | `reduce_dispatch`; dispatch, queue, operations | terminal producing-attempt disposition recorded | `R`; `pos_dispatch_fulfil`; `NE` |
| `dispatch.expire_issued` | W2 §12 `issued → expired` | `cmd/expire_dispatch` / `ExpireDispatch`; `DispatchExpired`; `evt/dispatch_expired` | `reduce_dispatch`; dispatch, queue | observed deadline and scheduler authority | `R`; `pos_dispatch_expire_issued`; `NE` |
| `dispatch.expire_delivered` | W2 §12 `delivered → expired` | `cmd/expire_dispatch` / `ExpireDispatch`; `DispatchExpired`; `evt/dispatch_expired` | `reduce_dispatch`; dispatch, queue | observed deadline and scheduler authority | `R`; `pos_dispatch_expire_delivered`; `NE` |
| `dispatch.expire_acknowledged` | W2 §12 `acknowledged → expired` | `cmd/expire_dispatch` / `ExpireDispatch`; `DispatchExpired`; `evt/dispatch_expired` | `reduce_dispatch`; dispatch, queue | observed deadline and scheduler authority | `R`; `pos_dispatch_expire_acknowledged`; `NE` |
| `dispatch.withdraw_issued` | W2 §12 `issued → withdrawn` | `cmd/withdraw_dispatch` / `WithdrawDispatch`; `DispatchWithdrawn`; `evt/dispatch_withdrawn` | `reduce_dispatch`; dispatch, queue, operations | withdrawal authority; no active claim | `R`; `pos_dispatch_withdraw_issued`; `NA` |
| `dispatch.withdraw_claimed` | W2 §12 `claimed → withdrawn` | `cmd/withdraw_dispatch` / `WithdrawDispatch`; `DispatchWithdrawn`; `evt/dispatch_withdrawn` | `reduce_dispatch`; dispatch, queue, operations | withdrawal authority plus attempt-stop disposition | `R`; `pos_dispatch_withdraw_claimed`; `NA` |
| `lease.activate` | W2 §12 `none → active` | `cmd/claim_execution_lease` / `ClaimExecutionLease`; `LeaseGranted`; `evt/lease_granted` | `reduce_lease`; lease, operations | valid grant, subject, holder, capability, expiry | `R`; `pos_lease_activate`; `NC` |
| `lease.renew` | W2 §12 `active → active(new expiry)` | `cmd/renew_execution_lease` / `RenewExecutionLease`; `LeaseRenewed`; `evt/lease_renewed` | `reduce_lease`; lease, operations | current holder, renewal policy, heartbeat/currentness evidence | `R`; `pos_lease_renew`; `NC` |
| `lease.release` | W2 §12 `active → released` | `cmd/release_execution_lease` / `ReleaseExecutionLease`; `LeaseReleased`; `evt/lease_released` | `reduce_lease`; lease, operations | current holder or operator authority | `R`; `pos_lease_release`; `NE` |
| `lease.expire` | W2 §12 `active → expired` | `cmd/expire_lease` / `ExpireLease`; `LeaseExpired`; `evt/lease_expired` | `reduce_lease`; lease, operations | observed time plus scheduler/operator authority | `R`; `pos_lease_expire`; `NE` |
| `lease.revoke` | W2 §12 `active → revoked` | `cmd/revoke_lease` / `RevokeLease`; `LeaseRevoked`; `evt/lease_revoked` | `reduce_lease`; lease, operations | revocation authority and typed reason | `R`; `pos_lease_revoke`; `NA` |
| `attempt.create` | W2 §12 `none → created` | `cmd/create_attempt` / `CreateAttempt`; `AttemptCreated`; `evt/attempt_created` | `reduce_attempt`; attempt, operations | new `att_` ID and next ordinal in exact epoch | `R`; `pos_attempt_create`; `NC` |
| `attempt.claim` | W2 §12 `created → claimed` | `cmd/claim_attempt` / `ClaimAttempt`; `AttemptClaimed`; `evt/attempt_claimed` | `reduce_attempt`; attempt, operations | matching claimed dispatch and active lease | `R`; `pos_attempt_claim`; `NC` |
| `attempt.start` | W2 §12 `claimed → running` | `cmd/start_attempt` / `StartAttempt`; `AttemptStarted`; `evt/attempt_started` | `reduce_attempt`; attempt, operations | process/session identity and exact context/roots | `R`; `pos_attempt_start`; `NE` |
| `attempt.complete` | W2 §12 `running → completed` | `cmd/complete_attempt` / `CompleteAttempt`; `AttemptCompleted`; `evt/attempt_completed` | `reduce_attempt`; attempt, operations | terminal execution and candidate-artefact evidence | `R`; `pos_attempt_complete`; `NE` |
| `attempt.fail` | W2 §12 `running → failed` | `cmd/fail_attempt` / `FailAttempt`; `AttemptFailed`; `evt/attempt_failed` | `reduce_attempt`; attempt, operations | typed failure evidence and output disposition | `R`; `pos_attempt_fail`; `NE` |
| `attempt.partial` | W2 §§12/15 `running → partial` | `cmd/record_attempt_partial` / `RecordAttemptPartial`; `PartialOutcomeRecorded`; `evt/partial_outcome_recorded` | `reduce_attempt`; attempt, operations, governance | complete/unmet obligations, artefacts, stop cause, restrictions | `R`; `pos_attempt_partial`; `NA` |
| `attempt.pause` | W2 §12 `running → paused` | `cmd/pause_attempt` / `PauseAttempt`; `AttemptPaused`; `evt/attempt_paused` | `reduce_attempt`; attempt, operations | checkpoint/process disposition and resume rule | `R`; `pos_attempt_pause`; `NE` |
| `attempt.resume` | W2 §12 `paused → running` | `cmd/resume_attempt` / `ResumeAttempt`; `AttemptResumed`; `evt/attempt_resumed` | `reduce_attempt`; attempt, operations | compatible checkpoint fingerprint and valid lease | `R`; `pos_attempt_resume`; `NC` |
| `attempt.request_stop` | W2 §12 `running → stopping` | `cmd/request_attempt_stop` / `RequestAttemptStop`; `AttemptStopRequested`; `evt/attempt_stop_requested` | `reduce_attempt`; attempt, operations | stop authority, deadline, signal/checkpoint plan | `R`; `pos_attempt_request_stop`; `NA` |
| `attempt.abandon` | W2 §12 `stopping → abandoned` | `cmd/confirm_attempt_stopped` / `ConfirmAttemptStopped`; `AttemptAbandoned`; `evt/attempt_abandoned` | `reduce_attempt`; attempt, operations | process/children/writers closed and checkpoint disposition | `R`; `pos_attempt_abandon`; `NA` |
| `attempt.supersede` | W2 §12 `attempt_nonterminal → superseded` | `cmd/supersede_attempt` / `SupersedeAttempt`; `AttemptSuperseded`; `evt/attempt_superseded` | `reduce_attempt`; attempt, operations | replacement attempt/epoch and retained evidence | `R`; `pos_attempt_supersede`; `NS` |
| `attempt.retry` | W2 §12 `attempt_retryable → created(new ID)` | `cmd/retry_attempt` / `RetryAttempt`; `AttemptCreated`; `evt/attempt_created` | `reduce_attempt`; attempt, operations | prior outcome, new ID/ordinal, reuse declaration | `R`; `pos_attempt_retry`; `NC` |
| `checkpoint.record` | W2 §12 state-neutral | `cmd/record_checkpoint` / `RecordCheckpoint`; `CheckpointRecorded`; `evt/checkpoint_recorded` | `reduce_checkpoint`; attempt, checkpoint, operations | manifest, fingerprint, units, identities, validation | `R`; `pos_checkpoint_record`; `NC` |

## 3. Messages, blockers, artefacts, reviews, decisions, and corrections

| Key | Owner transition/discriminator | Command schema / exact `command_type`; ordered event set; event schema | Reducer; exact projections/selector | Authority / precondition | Receipt; distinct positive test; negatives |
|---|---|---|---|---|---|
| `message.publish_assignment` | W2 §14 `none → published`, type `assignment` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact recipients/subject/action | `R`; `pos_message_assignment`; `NA` |
| `message.publish_acknowledgement` | W2 §14 `none → published`, type `acknowledgement` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact correlation/reply identity | `R`; `pos_message_acknowledgement`; `NA` |
| `message.publish_progress` | W2 §14 `none → published`, type `progress` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact Task/attempt correlation | `R`; `pos_message_progress`; `NA` |
| `message.publish_input_request` | W2 §14 `none → published`, type `input_request` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; named action/deadline/recipient | `R`; `pos_message_input_request`; `NA` |
| `message.publish_escalation` | W2 §14 `none → published`, type `escalation` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; typed evidence and escalation route | `R`; `pos_message_escalation`; `NA` |
| `message.publish_report` | W2 §14 `none → published`, type `report` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact Task/attempt/artefact refs | `R`; `pos_message_report`; `NA` |
| `message.publish_review_request` | W2 §14 `none → published`, type `review_request` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact review/subject refs | `R`; `pos_message_review_request`; `NA` |
| `message.publish_review_response` | W2 §14 `none → published`, type `review_response` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact review/reply refs | `R`; `pos_message_review_response`; `NA` |
| `message.publish_decision_request` | W2 §14 `none → published`, type `decision_request` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact Decision/question refs | `R`; `pos_message_decision_request`; `NA` |
| `message.publish_handoff` | W2 §14 `none → published`, type `handoff` | `cmd/publish_message` / `PublishMessage`; `MessagePublished`; `evt/message_published` | `reduce_message`; message | sender authority; exact scope/evidence/recipient refs | `R`; `pos_message_handoff`; `NA` |
| `message.deliver` | W2 §14 `published → delivered` | `cmd/record_message_delivery` / `RecordMessageDelivery`; `MessageDelivered`; `evt/message_delivered` | `reduce_message`; message | registered adapter and exact content hash/recipient | `R`; `pos_message_deliver`; `NE` |
| `message.acknowledge` | W2 §14 `delivered → acknowledged` | `cmd/acknowledge_message` / `AcknowledgeMessage`; `MessageAcknowledged`; `evt/message_acknowledged` | `reduce_message`; message | recipient, source position, content hash ownership | `R`; `pos_message_acknowledge`; `NE` |
| `message.delivery_failure` | W2 §14 `published → delivery_failed` | `cmd/record_message_delivery_failure` / `RecordMessageDeliveryFailure`; `MessageDeliveryFailed`; `evt/message_delivery_failed` | `reduce_message`; message | registered adapter and typed failure evidence | `R`; `pos_message_delivery_failure`; `NE` |
| `blocker.record` | W2 §15 `none → open` | `cmd/record_blocker` / `RecordBlocker`; `BlockerRecorded`; `evt/blocker_recorded` | `reduce_blocker`; blocker, governance | typed blocker, owner, stop flag, resume condition | `R`; `pos_blocker_record`; `NA` |
| `blocker.resolve` | W2 §15 `open → resolved` | `cmd/resolve_blocker` / `ResolveBlocker`; `BlockerResolved`; `evt/blocker_resolved` | `reduce_blocker`; blocker, governance | exact resolution evidence and responsible authority | `R`; `pos_blocker_resolve`; `NE` |
| `artefact.register` | W2 §16 `none → candidate` | `cmd/register_artefact` / `RegisterArtefact`; `ArtefactRegistered`; `evt/artefact_registered` | `reduce_artefact`; artefact | immutable content hash and complete manifest provenance | `R`; `pos_artefact_register`; `NA` |
| `artefact.availability` | W2 §16 dimension update | `cmd/record_artefact_availability` / `RecordArtefactAvailability`; `ArtefactAvailabilityRecorded`; `evt/artefact_availability_recorded` | `reduce_artefact`; artefact | observed availability evidence; no authority collapse | `R`; `pos_artefact_availability`; `NE` |
| `artefact.regenerability` | W2 §16 dimension update | `cmd/record_artefact_regenerability` / `RecordArtefactRegenerability`; `ArtefactRegenerabilityRecorded`; `evt/artefact_regenerability_recorded` | `reduce_artefact`; artefact | pinned producer/input/config and regeneration canary | `R`; `pos_artefact_regenerability`; `NE` |
| `artefact.integrity` | W2 §16 dimension update | `cmd/record_artefact_integrity` / `RecordArtefactIntegrity`; `ArtefactIntegrityRecorded`; `evt/artefact_integrity_recorded` | `reduce_artefact`; artefact | exact hash/tool/evidence | `R`; `pos_artefact_integrity`; `NE` |
| `artefact.structural_validation` | W2 §16 dimension update | `cmd/record_structural_validation` / `RecordStructuralValidation`; `StructuralValidationRecorded`; `evt/structural_validation_recorded` | `reduce_artefact`; artefact | exact contract/schema and validator evidence | `R`; `pos_artefact_structural_validation`; `NE` |
| `artefact.scientific_review` | W2 §16 dimension update | `cmd/record_scientific_review` / `RecordScientificReview`; `ScientificReviewRecorded`; `evt/scientific_review_recorded` | `reduce_artefact`; artefact, review | eligible review bound to exact subject hash | `R`; `pos_artefact_scientific_review`; `NI` |
| `artefact.use_authority` | W2 §16 dimension update | `cmd/set_artefact_use_authority` / `SetArtefactUseAuthority`; `ArtefactUseAuthoritySet`; `evt/artefact_use_authority_set` | `reduce_artefact`; artefact, governance | consumer predicate over all six dimensions | `R`; `pos_artefact_use_authority`; `NI` |
| `artefact.supersede` | W2 §§16/19 `current → superseded` | `cmd/supersede_artefact` / `SupersedeArtefact`; `ArtefactSuperseded`; `evt/artefact_superseded` | `reduce_artefact`; artefact, governance | replacement, scope, reason, effective time, continuing consumers | `R`; `pos_artefact_supersede`; `NS` |
| `review.request` | W2 §17 `none → requested` | `cmd/request_review` / `RequestReview`; `ReviewRequested`; `evt/review_requested` | `reduce_review`; review | exact subject hash, questions, lanes, grade, authority | `R`; `pos_review_request`; `NI` |
| `review.assign` | W2 §17 `requested → assigned` | `cmd/assign_review` / `AssignReview`; `ReviewAssigned`; `evt/review_assigned` | `reduce_review`; review | eligible reviewer and computed independence | `R`; `pos_review_assign`; `NI` |
| `review.start` | W2 §17 `assigned → in_review` | `cmd/start_review` / `StartReview`; `ReviewStarted`; `evt/review_started` | `reduce_review`; review | unchanged subject and allowed visibility | `R`; `pos_review_start`; `NI` |
| `review.record_verdict` | W2 §17 `in_review → verdict_recorded` | `cmd/record_review_verdict` / `RecordReviewVerdict`; `ReviewVerdictRecorded`; `evt/review_verdict_recorded` | `reduce_review`; review | verdict evidence, context manifest, subject hash, independence | `R`; `pos_review_record_verdict`; `NI` |
| `review.request_changes` | W2 §17 `verdict_recorded → changes_requested` | `cmd/request_review_changes` / `RequestReviewChanges`; `ReviewChangesRequested`; `evt/review_changes_requested` | `reduce_review`; review | authorized policy evaluation of verdict conditions | `R`; `pos_review_request_changes`; `NI` |
| `review.satisfy` | W2 §17 `verdict_recorded → satisfied` | `cmd/satisfy_review` / `SatisfyReview`; `ReviewSatisfied`; `evt/review_satisfied` | `reduce_review`; review, governance | governing policy accepts exact verdict for named gate | `R`; `pos_review_satisfy`; `NI` |
| `review.satisfy_after_changes` | W2 §17 `changes_requested → satisfied` | `cmd/satisfy_review` / `SatisfyReview`; `ReviewSatisfied`; `evt/review_satisfied` | `reduce_review`; review, governance | changed subject has new/delta review and conditions closed | `R`; `pos_review_satisfy_after_changes`; `NI` |
| `review.withdraw` | W2 §17 `review_nonterminal → withdrawn` | `cmd/withdraw_review` / `WithdrawReview`; `ReviewWithdrawn`; `evt/review_withdrawn` | `reduce_review`; review | requester/review authority and reason | `R`; `pos_review_withdraw`; `NI` |
| `review.supersede` | W2 §§17/19 `review_nonterminal → superseded` | `cmd/supersede_review` / `SupersedeReview`; `ReviewSuperseded`; `evt/review_superseded` | `reduce_review`; review | new review/subject lineage and continuing-gate disposition | `R`; `pos_review_supersede`; `NS` |
| `decision.propose` | W2 §18 `none → proposed` | `cmd/propose_decision` / `ProposeDecision`; `DecisionProposed`; `evt/decision_proposed` | `reduce_decision`; decision | question/options/evidence/required authority/expiry | `R`; `pos_decision_propose`; `NA` |
| `decision.request_review` | W2 §18 `proposed → under_review` | `cmd/request_decision_review` / `RequestDecisionReview`; `DecisionReviewRequested`; `evt/decision_review_requested` | `reduce_decision`; decision, review | exact Decision revision and review requirements | `R`; `pos_decision_request_review`; `NI` |
| `decision.resolve` | W2 §18 `under_review → resolved` | `cmd/resolve_decision` / `ResolveDecision`; `DecisionResolved`; `evt/decision_resolved` | `reduce_decision`; decision, governance | reserved deciding authority; exact evidence/reviews | `R`; `pos_decision_resolve`; `NI` |
| `decision.reject` | W2 §18 `decision_unresolved → rejected` | `cmd/reject_decision` / `RejectDecision`; `DecisionRejected`; `evt/decision_rejected` | `reduce_decision`; decision | required deciding authority and reason | `R`; `pos_decision_reject`; `NI` |
| `decision.expire` | W2 §18 `decision_unresolved → expired` | `cmd/expire_decision` / `ExpireDecision`; `DecisionExpired`; `evt/decision_expired` | `reduce_decision`; decision | observed expiry and scheduler/decision authority | `R`; `pos_decision_expire`; `NE` |
| `decision.supersede` | W2 §§18/19 `decision_unresolved → superseded` | `cmd/supersede_decision` / `SupersedeDecision`; `DecisionSuperseded`; `evt/decision_superseded` | `reduce_decision`; decision | replacement Decision, compatible kind/scope, lineage | `R`; `pos_decision_supersede`; `NS` |
| `rule.evaluate` | W2 §18 state-neutral | `cmd/record_rule_evaluation` / `RecordRuleEvaluation`; `RuleEvaluationRecorded`; `evt/rule_evaluation_recorded` | `reduce_rule_evaluation`; rule_evaluation, governance | pre-registered rule, exact inputs/estimand/metric/evidence; no Decision authority or projection substitution | `R`; `pos_rule_evaluate`; `NA` |
| `decision.amend` | W2 §18 `resolved → proposed(new revision)` | `cmd/amend_decision` / `AmendDecision`; `DecisionAmendmentProposed`; `evt/decision_amendment_proposed` | `reduce_decision`; decision | changed fields, post-work flag, effects, required authority | `R`; `pos_decision_amend`; `NS` |
| `correction.record` | W2 §19 state-neutral; discriminator `corrected_record_kind` | `cmd/record_correction` / `RecordCorrection`; `RecordCorrected`; `evt/record_corrected` | `reduce_correction`; typed selector `projection_selector/corrected_record_kind/v1` resolves exactly one owner projection plus the governance correction index | erroneous record, correction evidence, consumers, authority | `R`; `pos_correction_record`; `NS` |

## 4. W8 §20 normalized operator rows

These are thirteen separate expected keys. Each command uses a W2 envelope and receipt;
no alias, shared row, or implementation-defined substitute satisfies the catalogue.

| Key | Owner command/discriminator | Command schema / exact `command_type`; ordered event set; event schema | Reducer; exact projections/selector | Authority / precondition | Receipt; distinct positive test; negatives |
|---|---|---|---|---|---|
| `operator.request_resource_grant` | W8 §20 `request_resource_grant` | `cmd/request_resource_grant` / `RequestResourceGrant`; `ResourceGrantRequested`; `evt/resource_grant_requested` | `reduce_resource`; resource, operations | request profile, feasibility evidence, actor authority | `R`; `pos_operator_request_resource_grant`; `NA` |
| `operator.claim_execution_lease` | W8 §20 `claim_execution_lease` | `cmd/claim_execution_lease` / `ClaimExecutionLease`; `LeaseGranted`; `evt/lease_granted` | `reduce_lease`; lease, operations | valid grant, exact subject/holder/capability/expiry | `R`; `pos_operator_claim_execution_lease`; `NC` |
| `operator.record_heartbeat` | W8 §20 `record_heartbeat` | `cmd/record_heartbeat` / `RecordHeartbeat`; `HeartbeatRecorded`; `evt/heartbeat_recorded` | `reduce_lease`; lease, operations | active lease; matching host/boot/process identity | `R`; `pos_operator_record_heartbeat`; `NE` |
| `operator.request_pause` | W8 §20 `request_pause` | `cmd/request_pause` / `RequestPause`; `PauseRequested`; `evt/pause_requested` | `reduce_operation`; attempt, operations | active attempt/lease; checkpoint deadline | `R`; `pos_operator_request_pause`; `NA` |
| `operator.confirm_pause` | W8 §20 `confirm_pause` | `cmd/confirm_pause` / `ConfirmPause`; `PauseConfirmed`; `evt/pause_confirmed` | `reduce_operation`; attempt, checkpoint, operations | process quiesced; checkpoint/writer disposition | `R`; `pos_operator_confirm_pause`; `NA` |
| `operator.request_stop` | W8 §20 `request_stop` | `cmd/request_stop` / `RequestStop`; `StopRequested`; `evt/stop_requested` | `reduce_operation`; attempt, operations | stop authority; deadline and signal plan | `R`; `pos_operator_request_stop`; `NA` |
| `operator.confirm_stop` | W8 §20 `confirm_stop` | `cmd/confirm_stop` / `ConfirmStop`; `StopConfirmed`; `evt/stop_confirmed` | `reduce_operation`; attempt, operations | process exited; children and writers closed | `R`; `pos_operator_confirm_stop`; `NA` |
| `operator.request_resume` | W8 §20 `request_resume` | `cmd/request_resume` / `RequestResume`; `ResumeRequested`; `evt/resume_requested` | `reduce_operation`; attempt, checkpoint, operations | compatible checkpoint, valid grant/lease, resolved blocker | `R`; `pos_operator_request_resume`; `NC` |
| `operator.release_resources` | W8 §20 `release_resources` | `cmd/release_resources` / `ReleaseResources`; `ResourcesReleased`; `evt/resources_released` | `reduce_resource`; resource, lease, operations | holder/operator authority; consumption reconciliation | `R`; `pos_operator_release_resources`; `NE` |
| `operator.quarantine_orphan` | W8 §20 `quarantine_orphan` | `cmd/quarantine_orphan` / `QuarantineOrphan`; `OrphanQuarantined`; `evt/orphan_quarantined` | `reduce_recovery`; attempt, artefact, operations | invalid/uncertain process identity; quarantine evidence | `R`; `pos_operator_quarantine_orphan`; `NA` |
| `operator.adopt_late_artefact` | W8 §20 `adopt_late_artefact` | `cmd/adopt_late_artefact` / `AdoptLateArtefact`; `LateArtefactAdopted`; `evt/late_artefact_adopted` | `reduce_recovery`; artefact, governance | exact late timing, valid attempt link, review and consumer scope | `R`; `pos_operator_adopt_late_artefact`; `NI` |
| `operator.create_backup` | W8 §20 `create_backup` | `cmd/create_backup` / `CreateBackup`; `BackupCreated`; `evt/backup_created` | `reduce_backup`; backup, operations | exact store/tail, snapshot, schema, external availability | `R`; `pos_operator_create_backup`; `NA` |
| `operator.verify_restore` | W8 §20 `verify_restore` | `cmd/verify_restore` / `VerifyRestore`; `RestoreVerified`; `evt/restore_verified` | `reduce_backup`; backup, operations | store/project identity, chain, replay, endpoint, schemas, artefacts | `R`; `pos_operator_verify_restore`; `NA` |

## 5. Binding and exact-set test

T1's contract-materialization phase copies these rows without semantic alteration into
`.research-system/contracts/wp6-1-owner-source-catalogue.yaml`. The YAML records this
annex's repository path, Git blob ID, SHA-256, and every row/key above. The SHA-256 is
computed over the Git blob's canonical UTF-8/LF bytes, not platform-translated
worktree line endings. It also embeds the literal §1.4 selector table, references the
accepted schema-identity manifest from §1.1 by repository path/Git blob/SHA-256, and
requires the four exact authority fields in §1.2 for every row. Its validator:

1. parses the accepted annex and validates the closed state-class and negative-profile
   definitions;
2. expands only the literal state classes and preserves a multiset of complete binding
   records; the expanded set has 182 concrete edges while the normalized row set remains
   exactly 104;
3. compares each complete record one-to-one with independently accepted command
   schema IDs/versions/hashes and runtime types, event schemas
   and ordered sets, discriminators/edges, reducers, projections/selectors, authority
   rules, receipts, distinct positive tests, and expanded negative-test identities;
4. rejects missing, extra, duplicate, aliased, swapped-key, class-incomplete, or
   hash-mismatched records before checking behavior; and
5. proves every negative leaves the event tail and all affected projections unchanged.

The mutation suite changes one complete-record field at a time. It includes a
`command_type`-only alias; retained type with changed schema ID, version, or hash; one
duplicated binding under two logical keys; swapped keys;
two positive-test names resolving to one callable; a removed reducer; a removed or
wrong projection/selector; a changed message-type discriminator; a changed exact edge;
and a reordered/omitted event. It also mutates every row's authority rule/subject
binding, including Decision/RuleEvaluation cross-substitution; exercises unknown/
swapped/zero-owner/multiple-owner/missing-governance-index and coordinated expected/
runtime correction mappings; and exercises the Task-only omissions, stale versions,
foreign-current-Task relation, wrong lease subject, races, and write-set defects in
§1.3. Both `ClaimDispatch` facets must be present and prove the
same ordered `[DispatchClaimed, TaskClaimStarted]` batch reduces Task (`ready →
in_progress`) and Dispatch (`acknowledged → claimed`) atomically; global component presence cannot
compensate for either missing facet or effect.

The runtime registry is comparison input only. It is never an expected-set source.
