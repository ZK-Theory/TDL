# 06m — WP6 lifecycle-family pilot design

| Field | Value |
|---|---|
| Status | Design and dispatch recommendation only |
| Decision class | P00 delivery-organisation decision |
| Prepared from | codex/wp6-lifecycle-family-pilot-design at 5ca5507a7d3b71ecba8c880649e48a43c28dd9bd |
| Date | 2026-08-02 |

This document does not implement or authorize runtime behavior. It does not change any
schema, catalogue, contract, Jira record, provider, external-party record, pull
request, merge, or owner decision.

## 1. Decision

Adopt ten WP6.1 semantic delivery families over four reusable implementation
mechanisms. Treat the accepted 104-row catalogue as a complete semantic and test
census, not as 104 handlers, tasks, pull requests, agents, or Jira issues.

The ten transition-bearing state machines are ScopeDefinition, Task, Dispatch, Lease,
Attempt, Message, Blocker, Artefact, Review, and Decision. Four supporting subjects
are attached to the family that consumes them: resource to Lease, checkpoint and
project-store backup evidence to Attempt/operator recovery, and RuleEvaluation plus
Correction to Decision. This yields ten coherent ownership families without
pretending that every immutable record is another team.

Use four shared mechanisms:

1. E1 — exact versioned command/event binding and payload/event construction;
2. E2 — authority, idempotency, locking, atomic append, and concurrency;
3. E3 — reducers, replay, projections, and history;
4. E4 — operator/compatibility surfaces and the reusable conformance matrices.

E4 is a delivery and conformance mechanism, not a new persistence or event-sourcing
framework.

Run one Message lifecycle pilot first. It covers 13 exact rows through four command
types and four event types. It has enough discriminant, authority, negative-case,
replay, and projection density to test the family model, while avoiding the
cross-stream ClaimDispatch transaction, provider work, recovery cutover, and
owner-operated external action.

## 2. Exact verified state

### 2.1 Git and branch identity

The following was verified before this document was written:

| Fact | Verified value |
|---|---|
| Worktree | C:\Users\steph\.codex\worktrees\95f9\TDL |
| Symbolic branch | codex/wp6-lifecycle-family-pilot-design |
| Exact parent/start | 5ca5507a7d3b71ecba8c880649e48a43c28dd9bd |
| Start tree | 215c7bf514155c82413228edc5b66fcbfbb463e1 |
| Start first parent | ce086a0258a0b6d38addbd4c3cb68e3502576c48 |
| Start second parent | 207d92d93dd614e5e5f70c781d4bd11110b17488 |
| Live origin/main before writing | 207d92d93dd614e5e5f70c781d4bd11110b17488 |
| Live remote task branch before writing | 5ca5507a7d3b71ecba8c880649e48a43c28dd9bd |
| PR #204 merge | 207d92d93dd614e5e5f70c781d4bd11110b17488 |
| PR #204 merge tree | 35e433b8ff11fb87a127c16ef0ec716cf43e54d0 |

Both the exact start and origin/main were ancestors of the attached HEAD. The worktree
was clean. Codex initially started detached; detached HEAD and
refs/heads/codex/wp6-lifecycle-family-pilot-design both resolved to the exact start,
after which one deterministic switch attached that branch. No fallback branch,
rename, detached commit, or foreign-worktree write was used.

The start is a management merge whose second parent is the PR #204 merge. Therefore
the management base contains origin/main through PR #204 without inferring any later
pending branch.

### 2.2 Required authorities read at the exact start

All ten required sources were read in full. Their Git blobs at the design parent were:

| Authority | Git blob |
|---|---|
| handoffs/32-wp6-3-management-handoff-authority-model-and-acceptance-tooling.md | 602bacf815e7906b56418ecc523bacea489a2f44 |
| implementation/06-wp6-gate6-readiness-and-integration-plan.md | 3d0b24bb003d856ccf477c2cb910df3d885fc0b2 |
| implementation/06g-wp6-owner-operated-session-amendment.md | 49696e5b737f59ab8bd58d18c6e9231b0a61a599 |
| implementation/06a-wp6-1-runtime-task-lifecycle-plan.md | 052100192a1e488d1627d58592ecda0f86704dbd |
| implementation/06d-wp6-1-owner-source-catalogue.md | eab2eca016583841bc620690a1b29fa7266bf239 |
| implementation/06e-wp6-1-schema-fact-annex-proposal.md | 73677f4a49a9752f6536b103321f654cd8575075 |
| implementation/06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md | 8d93c11f2cf0c8f989f9c3a0bab44046a779e1ce |
| implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md | 8a68331aef8cb9df3557927bd6e1a1f57385f7d3 |
| design/11-portfolio-and-discovery-lifecycle.md | f90729d0c42a0de98d064fac0824d1969c871c82 |
| implementation/06l-wp6-7-legacy-consolidation-sequencing.md | 81141f84e7ec5e0de35b7e5deb6c918ff69ce7b3 |

Handoffs 27, 29, and 31 were not needed to resolve an implementation identity, so the
old review chain was not replayed.

### 2.3 Protected catalogue and schema identities

The accepted WP6.1 machine catalogue contains exactly 104 unique normalized keys and
182 expanded edges. The accepted generated set is exactly 173 schemas: 87 command
schemas and 86 event schemas. The Stage-2 owner decision protects exact bytes only:

| Protected object | Exact identity |
|---|---|
| Command-schema tree | 9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea; 87 files |
| Event-schema tree | 154ffc4bdde82fe903718734687e7a62797b1f69; 86 files |
| Identity manifest | blob 54a2938d34cea9c4a88d23585ce012a86bc3209d; canonical LF SHA-256 d6d537088f41179b993b94991d5bf5790499cce80bf419c098ca899e794b37e7 |
| Owner catalogue | blob 1adc66921ee9c90d8786ff173748150922f1035e; canonical LF SHA-256 bddc6882b969d322cab88af99f15a214edec9ef90c5f563dc9a9fbd082a632ab |
| External acceptance record | blob f1b73c729ed05c3bfdfcd50e0a916fa9fc70fff5 |

The command and event trees at the design parent still equal the accepted tree IDs.
The immutable manifests retain historical pending fields by design; those fields are
not the later lifecycle authority. The external acceptance record is the decision
layer. No accepted raw schema, manifest, catalogue, or strict-contract byte is opened
by this design.

The W11 design contains exactly 81 owner rows: OR-001 through OR-041 and OR-101
through OR-140, with no gaps in either range. Its accepted raw Git object is blob
f90729d0c42a0de98d064fac0824d1969c871c82, 185,214 bytes, SHA-256
65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70.
PR #204 changed 65 paths and supplied inert W11 catalogue/schema/bootstrap
foundation only. It did not complete KAN-58 or activate any W11 runtime row.

### 2.4 Runtime reality

Direct inspection of SchemaRegistry, CommandService.submit, CommandService._build_event,
EventLedger.append, the reducers, and projection replay confirmed:

- exactly six WP6.1 rows are runtime-active:
  scope.create, scope.amend_revision, scope.supersede, task.create,
  task.amend_revision, and task.supersede;
- the corresponding active command/event pairs are
  CreateScopeDefinition/ScopeDefinitionCreated,
  AmendScopeDefinition/ScopeDefinitionAmended,
  SupersedeScopeDefinition/ScopeDefinitionSuperseded,
  CreateTask/TaskCreated, AmendTask/TaskAmended, and
  SupersedeTask/TaskSuperseded;
- approximately 98 catalogue rows remain inactive;
- ClaimDispatch has legacy handler code, but it lacks an accepted active binding at
  this subject and is not counted as a completed catalogue row;
- SchemaRegistry distinguishes discovery/materialisation from explicit active
  bindings and retains exact raw schema bytes, versions, and hashes;
- CommandService performs binding selection, authority and state checks, while
  EventLedger performs append-time identity and tail checks; and
- replay_control_plane, projection.replay, and rebuild_projection are existing
  mechanisms to extend, not replace.

Schema materialisation, registry discoverability, a handler branch, or a passing
contract test is not runtime activation.

### 2.5 Pending seams and exclusions

Pending state was inspected read-only and is not silently promoted:

| Subject | Verified state and consequence |
|---|---|
| Slice L correction | ea589d1a0b450828a7b6d013e2334dfccdca5ee5, parent 1946cd6ec59ae64861b902805934f5c3e37de8ce, tree 2baa95; two paths: research_system/store/lock.py and tests/research_system/unit/test_store.py. It closes the Windows composite-lock cleanup finding but is not an ancestor of this design parent or origin/main. |
| Live PR #205 | On 2026-08-02 the live head was bf2649c6a6fbc02bbd66e1b16403f564e1a22029, not ea589d1. It is a separate durable-authority-evidence line and does not contain ea589d1. The label “PR #205/Slice L” is therefore not a safe Git identity. |
| KAN-67 correction | 263b304733afb2bb34037566ad7884ea2dd47612, parent 4b27b04f7a232fbc71097ff4c82587374016fc83, two paths. It is not an ancestor and is not folded into this pilot. |
| WP6.4 recovery candidate | 3d5a1a7bdf6af80f47e6be3aa68c4d32708fd1ab, parent ebc42596fc4bc7b95fb380e6bbece5efde0f742d, eight paths. Its separate recovery-state-machine decision remains separate. |
| Provider automation | Deferred/superseded by 06g/P-042; no provider activation or call is in this design. |

The pilot must not be dispatched from a base that merely names these subjects. The
dispatch base must be a later owner-selected exact SHA whose ancestry is verified
against every required pending dependency.

## 3. Blunt diagnosis

### 3.1 What is genuinely inefficient

1. T1–T8 are delivery tranches, but they have been used as if they were semantic
   ownership boundaries. A Task transition can be introduced in T1 or T3, rely on a
   T2 claim, gain a T6 operator command, receive its reducer/projection in T7, and
   finally acquire binding negatives in T8. That creates repeated handoffs around one
   state machine.
2. The same central files are reopened for each tranche: schema_registry.py,
   command/service.py, store/ledger.py, command/reducers.py, projection/replay.py, and
   their large tests. Parallel owners would collide even when their catalogue rows do
   not.
3. Catalogue rows have been treated too much like units of implementation. Ten
   message publication rows share one PublishMessage schema, handler, event type, and
   reducer, while still requiring ten discriminant-specific proofs. One row is
   neither one handler nor one PR.
4. Producer, reducer, replay/projection, operator surface, and decisive negatives have
   been allowed to look like successive closure layers. They are one semantic
   vertical and should reach review together.
5. Reusable authority, append, replay, and exact-set fixtures have been rediscovered
   inside slices. Those mechanisms need one central owner and family-parametrised
   matrices.
6. Tranche, PR, task packet, test row, and Jira issue have become easy to conflate.
   That raises coordination cost without creating more semantic closure.

### 3.2 What is unavoidable

1. Exact-byte acceptance of 173 protected schemas is real authority work. It cannot
   be replaced by generating or reserialising “equivalent” schemas.
2. Each of 104 rows remains a distinct semantic/test obligation even when rows share
   code. Discriminants, authority subjects, transition predicates, and negative
   identities must remain exact.
3. ClaimDispatch is genuinely cross-stream and atomic. Its Task and Dispatch events
   cannot be split for convenience.
4. Review and Decision are distinct authority records; review acceptance cannot be
   substituted for owner decision.
5. Central append, reducer, replay, and projection seams require serial integration
   and fresh exact-subject review. Parallel editing cannot remove that dependency.
6. Artifact consumer authority and recovery semantics have wider blast radii than
   their row counts suggest.

### 3.3 Why progress looks slower than row counts imply

The denominator mixes three different things: 104 semantic variants, 173 already
accepted protected schemas, and only six active runtime bindings. Foundation work
made schema identity and exact-byte activation safe, but it did not activate the
remaining rows. Conversely, 98 inactive rows do not imply 98 new handlers: shared
commands such as PublishMessage, ExpireDispatch, ReopenTask, and SatisfyReview collapse
implementation while preserving per-row tests. The honest metric is complete
state-machine closure at an exact subject, not rows mentioned, schemas present, test
files added, PRs merged, or Jira statuses changed.

## 4. Units that must not be conflated

| Unit | Meaning | Not equivalent to |
|---|---|---|
| Semantic family | Rows with one lifecycle owner, aggregate or deliberate aggregate cluster, authority rule, reducer/replay contract, and negative matrix | PR, agent, Jira issue |
| Shared engine | Existing reusable binding, append, replay, or conformance mechanism beneath two or more families | Domain lifecycle |
| PR slice | One reviewable exact Git subject delivering one or more complete verticals under the path cap | Catalogue row or family by definition |
| Test matrix | Literal row-to-positive/negative coverage and mutation census | Runtime implementation |
| Jira issue | Human planning/approval record | Semantic authority or acceptance |

## 5. Family-count comparison

| Count | Credible decomposition | Judgment |
|---|---|---|
| 6 | Work definition; execution ownership; messaging; artefacts; review/decision; recovery | Too collapsed. It puts Task/Blocker and Dispatch/Lease/Attempt behind broad owners, combines review with owner decision, and creates giant negative matrices and central-file subjects. |
| 8 | The starting hypothesis: definition/terminal; readiness/blocker/Partial; dispatch/lease; attempt/control/recovery; message; artefact; review/decision; backup/restore | Better domain language, but still unsafe. It splits the Task and Attempt streams according to prose concerns, while combining Review and Decision despite distinct authority. It would cause cross-family ownership of ordinary transitions. |
| 10 | Scope; Task; Dispatch/atomic claim; Lease/resource; Attempt/operator recovery; Message; Blocker; Artefact; Review; Decision/rule/correction | Chosen. It matches the ten transition-bearing state machines, attaches small supporting records to their consuming lifecycle, and has one explicit cross-aggregate exception: ClaimDispatch. |
| 12 | Split atomic claim from Dispatch, resource from Lease, and operator recovery from Attempt, while retaining separate Scope, Task, Blocker, Message, Artefact, Review, and Decision families | Too split for current interfaces. It turns one atomic command and one attempt control plane into handoffs, increases central-file churn, and creates tiny teams without distinct reducers or authority engines. |

Further collapse would hide authority separation or split stream ownership. Further
split would turn command discriminants and control facets into coordination units.
Ten is therefore the smallest defensible delivery-family count on current evidence.
If implementation proves that project-store recovery is a separately mutable
aggregate rather than gated evidence attached to operator recovery, the count must be
reopened explicitly; the existing WP6.4 candidate is not that decision.

## 6. Minimal reusable architecture

### 6.1 Existing mechanisms to reuse

| Mechanism | Existing seam | Family responsibility |
|---|---|---|
| E1 binding/producer | SchemaRegistry active bindings; CommandService binding selection and event construction | Declare only accepted schema IDs/versions/hashes; build exact payload/event facts; no schema rewriting |
| E2 authority/append | CommandService authority/state/idempotency checks; content-addressed authority resolution; EventLedger append and locks | Supply family subject resolution, declared write set, preconditions, stable rejection and receipt facts |
| E3 state/history | command reducers, replay_control_plane, projection.replay, rebuild_projection | Supply one family reducer and projection mapping; unknown or broken records fail closed |
| E4 conformance/surface | Existing CLI/operator routes and contract/unit/integration/replay tests | Supply one literal family matrix, decisive mutations, compatibility checks, and exact-set closure |

The first implementation must use these interfaces. A family-specific validator or
reducer module is allowed. A new generic abstraction is allowed only when two
implemented families demonstrate the same missing interface and the existing
CommandService/ledger/replay contracts cannot carry it. That evidence must precede
the abstraction PR. No lifecycle DSL, generator, event-sourcing framework, or
persistence layer is proposed.

### 6.2 Central-file ownership

One integration owner serially owns schema_registry.py, command/service.py,
store/ledger.py, command/reducers.py, projection/replay.py, and shared factories.
No two active packets may edit those paths in parallel. A family owner may own a
family module and its tests, but its central seam is integrated serially by that
owner or delivered in the same bounded branch. A PR does not split binding,
producer, reducer, replay/projection, and decisive negatives into separate
acceptance subjects.

### 6.3 Cross-cutting tags

Every WP6.1 row below carries E1, E2, E3, and E4. Additional tags are:

- XAT — exact cross-aggregate atomic transaction;
- DISC — shared command/event schema with a row-specific discriminant;
- OPS — operator/control surface;
- FW — artifact consumer firewall;
- SEP — role/authority separation is decisive;
- GATE-REC — separate owner recovery decision required.

## 7. Complete WP6.1 row-to-family crosswalk

Every accepted normalized key appears exactly once below. Family counts sum to 104.

| Exact catalogue row ID | Primary family | Additional tags |
|---|---|---|
| scope.create | F1 Scope | — |
| scope.amend_revision | F1 Scope | — |
| scope.supersede | F1 Scope | — |
| scope.complete | F1 Scope | — |
| task.create | F2 Task | — |
| task.amend_revision | F2 Task | — |
| task.request_readiness | F2 Task | SEP |
| task.approve_readiness | F2 Task | SEP |
| task.block | F2 Task | — |
| task.request_input | F2 Task | — |
| task.pause | F2 Task | — |
| task.claim_start | F3 Dispatch/claim | XAT, DISC |
| task.submit_review | F2 Task | SEP |
| task.resume | F2 Task | — |
| task.accept | F2 Task | SEP |
| task.reject | F2 Task | SEP |
| task.close_partial | F2 Task | — |
| task.cancel | F2 Task | — |
| task.supersede | F2 Task | — |
| task.reopen_partial | F2 Task | DISC |
| task.reopen_rejected | F2 Task | DISC |
| task.reopen_cancelled | F2 Task | DISC |
| dispatch.issue | F3 Dispatch/claim | — |
| dispatch.deliver | F3 Dispatch/claim | — |
| dispatch.acknowledge | F3 Dispatch/claim | — |
| dispatch.claim | F3 Dispatch/claim | XAT, DISC |
| dispatch.fulfil | F3 Dispatch/claim | — |
| dispatch.expire_issued | F3 Dispatch/claim | DISC |
| dispatch.expire_delivered | F3 Dispatch/claim | DISC |
| dispatch.expire_acknowledged | F3 Dispatch/claim | DISC |
| dispatch.withdraw_issued | F3 Dispatch/claim | DISC |
| dispatch.withdraw_claimed | F3 Dispatch/claim | DISC |
| lease.activate | F4 Lease/resource | DISC |
| lease.renew | F4 Lease/resource | — |
| lease.release | F4 Lease/resource | — |
| lease.expire | F4 Lease/resource | — |
| lease.revoke | F4 Lease/resource | — |
| attempt.create | F5 Attempt/operator recovery | — |
| attempt.claim | F5 Attempt/operator recovery | — |
| attempt.start | F5 Attempt/operator recovery | — |
| attempt.complete | F5 Attempt/operator recovery | — |
| attempt.fail | F5 Attempt/operator recovery | — |
| attempt.partial | F5 Attempt/operator recovery | — |
| attempt.pause | F5 Attempt/operator recovery | — |
| attempt.resume | F5 Attempt/operator recovery | — |
| attempt.request_stop | F5 Attempt/operator recovery | — |
| attempt.abandon | F5 Attempt/operator recovery | — |
| attempt.supersede | F5 Attempt/operator recovery | — |
| attempt.retry | F5 Attempt/operator recovery | — |
| checkpoint.record | F5 Attempt/operator recovery | — |
| message.publish_assignment | F6 Message | DISC |
| message.publish_acknowledgement | F6 Message | DISC |
| message.publish_progress | F6 Message | DISC |
| message.publish_input_request | F6 Message | DISC |
| message.publish_escalation | F6 Message | DISC |
| message.publish_report | F6 Message | DISC |
| message.publish_review_request | F6 Message | DISC |
| message.publish_review_response | F6 Message | DISC |
| message.publish_decision_request | F6 Message | DISC |
| message.publish_handoff | F6 Message | DISC |
| message.deliver | F6 Message | — |
| message.acknowledge | F6 Message | SEP |
| message.delivery_failure | F6 Message | — |
| blocker.record | F7 Blocker | — |
| blocker.resolve | F7 Blocker | SEP |
| artefact.register | F8 Artefact | FW |
| artefact.availability | F8 Artefact | FW |
| artefact.regenerability | F8 Artefact | FW |
| artefact.integrity | F8 Artefact | FW |
| artefact.structural_validation | F8 Artefact | FW, SEP |
| artefact.scientific_review | F8 Artefact | FW, SEP |
| artefact.use_authority | F8 Artefact | FW, SEP |
| artefact.supersede | F8 Artefact | FW |
| review.request | F9 Review | SEP |
| review.assign | F9 Review | SEP |
| review.start | F9 Review | SEP |
| review.record_verdict | F9 Review | SEP |
| review.request_changes | F9 Review | SEP |
| review.satisfy | F9 Review | DISC, SEP |
| review.satisfy_after_changes | F9 Review | DISC, SEP |
| review.withdraw | F9 Review | SEP |
| review.supersede | F9 Review | SEP |
| decision.propose | F10 Decision/rule/correction | SEP |
| decision.request_review | F10 Decision/rule/correction | SEP |
| decision.resolve | F10 Decision/rule/correction | SEP |
| decision.reject | F10 Decision/rule/correction | SEP |
| decision.expire | F10 Decision/rule/correction | SEP |
| decision.supersede | F10 Decision/rule/correction | SEP |
| rule.evaluate | F10 Decision/rule/correction | SEP |
| decision.amend | F10 Decision/rule/correction | SEP |
| correction.record | F10 Decision/rule/correction | SEP |
| operator.request_resource_grant | F4 Lease/resource | OPS |
| operator.claim_execution_lease | F4 Lease/resource | OPS, DISC |
| operator.record_heartbeat | F4 Lease/resource | OPS |
| operator.request_pause | F5 Attempt/operator recovery | OPS |
| operator.confirm_pause | F5 Attempt/operator recovery | OPS, SEP |
| operator.request_stop | F5 Attempt/operator recovery | OPS |
| operator.confirm_stop | F5 Attempt/operator recovery | OPS, SEP |
| operator.request_resume | F5 Attempt/operator recovery | OPS |
| operator.release_resources | F4 Lease/resource | OPS |
| operator.quarantine_orphan | F5 Attempt/operator recovery | OPS, SEP |
| operator.adopt_late_artefact | F8 Artefact | OPS, FW, SEP |
| operator.create_backup | F5 Attempt/operator recovery | OPS, GATE-REC |
| operator.verify_restore | F5 Attempt/operator recovery | OPS, SEP, GATE-REC |

## 8. Family state machines and decisive invariants

The literal command/event census is:

| Family | Exact command types | Exact event types |
|---|---|---|
| F1 | CreateScopeDefinition; AmendScopeDefinition; SupersedeScopeDefinition; CompleteScope | ScopeDefinitionCreated; ScopeDefinitionAmended; ScopeDefinitionSuperseded; ScopeCompleted |
| F2 | CreateTask; AmendTask; RequestReadiness; ApproveReadiness; BlockTask; RequestInput; PauseTask; SubmitForReview; ResumeTask; AcceptTask; RejectTask; ClosePartial; CancelTask; SupersedeTask; ReopenTask | TaskCreated; TaskAmended; ReadinessRequested; ReadinessApproved; TaskBlocked; InputRequested; TaskPaused; TaskSubmittedForReview; TaskResumed; TaskAccepted; TaskRejected; PartialOutcomeRecorded; TaskCancelled; TaskSuperseded; TaskReopened |
| F3 | ClaimDispatch; IssueDispatch; RecordDispatchDelivery; AcknowledgeDispatch; FulfilDispatch; ExpireDispatch; WithdrawDispatch | DispatchClaimed; TaskClaimStarted; DispatchIssued; DispatchDelivered; DispatchAcknowledged; DispatchFulfilled; DispatchExpired; DispatchWithdrawn |
| F4 | ClaimExecutionLease; RenewExecutionLease; ReleaseExecutionLease; ExpireLease; RevokeLease; RequestResourceGrant; RecordHeartbeat; ReleaseResources | LeaseGranted; LeaseRenewed; LeaseReleased; LeaseExpired; LeaseRevoked; ResourceGrantRequested; HeartbeatRecorded; ResourcesReleased |
| F5 | CreateAttempt; ClaimAttempt; StartAttempt; CompleteAttempt; FailAttempt; RecordAttemptPartial; PauseAttempt; ResumeAttempt; RequestAttemptStop; ConfirmAttemptStopped; SupersedeAttempt; RetryAttempt; RecordCheckpoint; RequestPause; ConfirmPause; RequestStop; ConfirmStop; RequestResume; QuarantineOrphan; CreateBackup; VerifyRestore | AttemptCreated; AttemptClaimed; AttemptStarted; AttemptCompleted; AttemptFailed; PartialOutcomeRecorded; AttemptPaused; AttemptResumed; AttemptStopRequested; AttemptAbandoned; AttemptSuperseded; CheckpointRecorded; PauseRequested; PauseConfirmed; StopRequested; StopConfirmed; ResumeRequested; OrphanQuarantined; BackupCreated; RestoreVerified |
| F6 | PublishMessage; RecordMessageDelivery; AcknowledgeMessage; RecordMessageDeliveryFailure | MessagePublished; MessageDelivered; MessageAcknowledged; MessageDeliveryFailed |
| F7 | RecordBlocker; ResolveBlocker | BlockerRecorded; BlockerResolved |
| F8 | RegisterArtefact; RecordArtefactAvailability; RecordArtefactRegenerability; RecordArtefactIntegrity; RecordStructuralValidation; RecordScientificReview; SetArtefactUseAuthority; SupersedeArtefact; AdoptLateArtefact | ArtefactRegistered; ArtefactAvailabilityRecorded; ArtefactRegenerabilityRecorded; ArtefactIntegrityRecorded; StructuralValidationRecorded; ScientificReviewRecorded; ArtefactUseAuthoritySet; ArtefactSuperseded; LateArtefactAdopted |
| F9 | RequestReview; AssignReview; StartReview; RecordReviewVerdict; RequestReviewChanges; SatisfyReview; WithdrawReview; SupersedeReview | ReviewRequested; ReviewAssigned; ReviewStarted; ReviewVerdictRecorded; ReviewChangesRequested; ReviewSatisfied; ReviewWithdrawn; ReviewSuperseded |
| F10 | ProposeDecision; RequestDecisionReview; ResolveDecision; RejectDecision; ExpireDecision; SupersedeDecision; RecordRuleEvaluation; AmendDecision; RecordCorrection | DecisionProposed; DecisionReviewRequested; DecisionResolved; DecisionRejected; DecisionExpired; DecisionSuperseded; RuleEvaluationRecorded; DecisionAmendmentProposed; RecordCorrected |

### F1 — Scope

- Rows: four. Commands/events are CreateScopeDefinition/ScopeDefinitionCreated,
  AmendScopeDefinition/ScopeDefinitionAmended,
  SupersedeScopeDefinition/ScopeDefinitionSuperseded, and
  CompleteScope/ScopeCompleted.
- Aggregate and authority: one ScopeDefinition stream. Authority is scoped to the
  exact proposed or existing scope-definition ID, complete versioned membership,
  dispositions, predicate, and governance facts.
- Atomicity: one command appends one event to one stream. Scope completion may read
  member Task outcomes but may not mutate those Task streams.
- State/history: reduce_scope owns transitions; replay and scope projections must
  rebuild the same revision, membership, supersession, and completion state.
- Concurrency/idempotency: expected stream version, global position/tail, exact
  command identity, and stable duplicate receipt precede allocation.
- Decisive negatives: duplicate ID; stale revision; incomplete or aliased membership;
  changed completion predicate; completion with unresolved members; self-supersession;
  wrong authority subject; and any rejected command changing tail, receipt acceptance,
  or projection.

### F2 — Task

- Rows: 17. Commands/events cover Task creation/amendment, readiness request/approval,
  block/input/pause/resume, review submission, accept/reject/Partial/cancel,
  supersession, and three ReopenTask discriminants. Claim start is excluded because
  it is one facet of F3's atomic ClaimDispatch.
- Aggregate and authority: one Task revision stream, with exact task ID, revision,
  scope membership, readiness evidence, blocker/input references, and outcome
  authority.
- Atomicity: ordinary Task commands append one event to the Task stream. They never
  write Blocker, Review, Artefact, or Decision streams merely because they reference
  them.
- State/history: reduce_task is authoritative; Task projection and replay preserve
  revision, readiness, current state, terminal reason, Partial evidence, and reopen
  lineage.
- Concurrency/idempotency: exact expected Task version and tail; repeated command ID
  returns the original receipt; stale or concurrent readiness/outcome commands lose
  without mutation.
- Decisive negatives: readiness without complete evidence; unresolved blocker or
  input; wrong Task revision; ordinary Task command attempting claim-start; review
  verdict substituted for acceptance; incomplete Partial evidence; reopen from the
  wrong terminal state; reused terminal evidence; and stale authority.

### F3 — Dispatch and atomic claim

- Rows: 11. Commands/events are IssueDispatch/DispatchIssued,
  RecordDispatchDelivery/DispatchDelivered,
  AcknowledgeDispatch/DispatchAcknowledged,
  ClaimDispatch producing DispatchClaimed plus TaskClaimStarted,
  FulfilDispatch/DispatchFulfilled, three ExpireDispatch/DispatchExpired variants,
  and two WithdrawDispatch/DispatchWithdrawn variants.
- Aggregate and authority: the Dispatch stream is primary. ClaimDispatch alone owns a
  declared two-stream write set containing the exact Dispatch and the Task revision
  already stored on that Dispatch.
- Atomicity: the claim batch is exactly ordered
  [DispatchClaimed, TaskClaimStarted]. Both expected stream versions, expected global
  position, and expected tail hash are checked before allocation. There is no
  half-claim or compensating second command.
- State/history: reduce_dispatch and reduce_task apply acknowledged-to-claimed and
  ready-to-in_progress together; replay either applies the complete batch in order or
  fails closed.
- Concurrency/idempotency: the composite lock and idempotency record cover the whole
  declared write set; the receipt binds both event identities and resulting versions.
- Decisive negatives: Dispatch-to-Task mismatch; lease bound to another
  Task/Dispatch; missing/extra/swapped write-set member; reversed event order; stale
  version/tail; duplicate command with changed payload; half append; expiry or
  withdrawal discriminant inconsistent with current state.

### F4 — Lease and resource ownership

- Rows: nine. Commands/events cover ClaimExecutionLease/LeaseGranted,
  RenewExecutionLease/LeaseRenewed, ReleaseExecutionLease/LeaseReleased,
  ExpireLease/LeaseExpired, RevokeLease/LeaseRevoked,
  RequestResourceGrant/ResourceGrantRequested, RecordHeartbeat/HeartbeatRecorded, and
  ReleaseResources/ResourcesReleased.
- Aggregate and authority: Lease is the transition-bearing aggregate; Resource is a
  supporting authority subject. The lease binds exact Task revision, Dispatch,
  Attempt/owner, resource grant, interval, and heartbeat policy.
- Atomicity: each accepted command writes only its declared Lease or Resource stream.
  References to Task, Dispatch, and Attempt are validated snapshots, not hidden writes.
- State/history: reduce_lease and reduce_resource rebuild holder, interval, heartbeat,
  expiry/revocation, and released resources. Replay rejects overlapping or broken
  ownership history.
- Concurrency/idempotency: single current holder, expected version/tail, stable
  duplicate receipt, and monotone heartbeat/renewal positions.
- Decisive negatives: overlapping live lease; expired/not-yet-effective grant; wrong
  holder, task revision, Dispatch, or resource; heartbeat after release/revocation;
  renewal beyond policy; resource release by non-owner; and treating a heartbeat as
  lease renewal.

### F5 — Attempt and operator recovery

- Rows: 21. Commands/events cover the complete Attempt lifecycle, CheckpointRecorded,
  request/confirm pause and stop, request resume, orphan quarantine, BackupCreated,
  and RestoreVerified.
- Aggregate and authority: Attempt is primary; checkpoint and operator control are
  Attempt-scoped facets. Project-store backup/restore evidence is attached here only
  as a gated operational-recovery subject, not as acceptance of the separate WP6.4
  recovery state machine.
- Atomicity: each command appends its declared Attempt/checkpoint/operation/backup
  event only. Request and confirmation remain separate authorized facts; a request
  cannot self-confirm.
- State/history: reduce_attempt, reduce_checkpoint, reduce_operation,
  reduce_recovery, and reduce_backup must produce one replay-consistent execution
  history. Checkpoint ancestry and stop/pause handshakes remain visible.
- Concurrency/idempotency: expected Attempt/project-store versions, current lease and
  heartbeat, monotone checkpoint position, stable duplicate receipt, and no late
  completion racing a confirmed stop.
- Decisive negatives: start without current claim/lease; pause/stop confirmation by
  the requester when separation is required; resume without confirmed pause;
  completion after terminal state; broken checkpoint chain; retry without
  supersession lineage; orphan quarantine of a live owner; backup chain mismatch; or
  restore verification being treated as a live restore/cutover.

The GATE-REC rows remain undispatchable until the owner separately decides the
recovery-state-machine boundary and supplies an exact base. The open WP6.4 candidate
is not imported into F5.

### F6 — Message

- Rows: 13. Ten PublishMessage discriminants produce MessagePublished; delivery,
  acknowledgement, and failure use RecordMessageDelivery/MessageDelivered,
  AcknowledgeMessage/MessageAcknowledged, and
  RecordMessageDeliveryFailure/MessageDeliveryFailed.
- Aggregate and authority: one immutable Message stream, scoped to exact sender,
  recipient set, subject, content hash, correlation/reply links, and adapter where
  applicable.
- Atomicity: one event per command on one Message stream. Publication never writes the
  referenced Task, Attempt, Review, Decision, or Artefact.
- State/history: reduce_message implements none-to-published, published-to-delivered,
  delivered-to-acknowledged, or published-to-delivery_failed. Replay preserves exact
  content/linkage and forbids divergent terminal branches.
- Concurrency/idempotency: publish ID uniqueness; exact expected version for later
  transitions; one stable receipt per command ID; delivery/failure races have one
  winner.
- Decisive negatives: unsupported or mismatched publication discriminant; wrong
  sender/recipient/subject; content-hash mutation; broken correlation/reply link;
  unregistered adapter; acknowledgement by a non-recipient or before delivery;
  failure after acknowledgement; and duplicate command with changed content.

### F7 — Blocker

- Rows: two. RecordBlocker/BlockerRecorded and ResolveBlocker/BlockerResolved.
- Aggregate and authority: one Blocker stream bound to its exact Task/Attempt subject,
  category, evidence, required resolver, and resolution predicate.
- Atomicity: Blocker commands do not directly mutate Task state. A Task transition
  must independently validate the current Blocker projection.
- State/history: reduce_blocker and replay preserve open/resolved identity, evidence,
  resolver, and resolution time.
- Concurrency/idempotency: unique blocker ID, expected version/tail, one resolution,
  stable duplicate receipt.
- Decisive negatives: self-attested evidence where independent evidence is required;
  resolver mismatch; resolution without predicate/evidence; changed subject;
  duplicate divergent resolution; and a Task projection silently treating absence as
  resolved.

### F8 — Artefact

- Rows: nine. RegisterArtefact and seven evidence/authority/supersession commands plus
  AdoptLateArtefact produce their exact named events.
- Aggregate and authority: one Artefact stream binds immutable manifest identity,
  availability, regenerability, integrity, structural/scientific review, use
  authority, supersession, and any late-adoption decision.
- Atomicity: publication/evidence facts append to the Artefact stream; no consumer is
  mutated. Consumers resolve the accepted current artefact and authority at use time.
- State/history: reduce_artefact and the bounded recovery reducer rebuild evidence
  history and current use authority. Replay preserves old accepted bytes and explicit
  supersession.
- Concurrency/idempotency: immutable registration, versioned evidence append, exact
  authority/supersession target, stable duplicate receipt.
- Decisive negatives: self-hash or producer self-attestation as authority; silent
  missing evidence; availability substituted for integrity; stale/superseded
  artefact; direct consumer bypass; inconsistent exact bytes; late artefact adopted
  automatically; or consumer acceptance inferred from registration.

### F9 — Review

- Rows: nine. Commands/events cover request, assign, start, verdict, changes,
  satisfaction with or without changes, withdrawal, and supersession.
- Aggregate and authority: one Review stream binds exact subject revision, reviewer
  relation, requested checks, evidence set, verdict, change requests, and
  supersession.
- Atomicity: Review commands write only Review. They never resolve a Decision, accept
  a Task, or set Artefact use authority.
- State/history: reduce_review and replay preserve assignment, independence,
  evidence, verdict, changes, satisfaction, withdrawal, and successor lineage.
- Concurrency/idempotency: one active assignment/revision, expected version/tail,
  stable duplicate receipt, no verdict racing withdrawal/supersession.
- Decisive negatives: proposer/reviewer identity conflict; review of wrong or stale
  subject; missing evidence; verdict before start; satisfaction without required
  changes; changed verdict under same command ID; and treating accept_exact_subject
  as owner acceptance.

### F10 — Decision, rule evaluation, and correction

- Rows: nine. Commands/events cover proposal, review request, resolution, rejection,
  expiry, supersession, amendment proposal, RuleEvaluationRecorded, and
  RecordCorrected.
- Aggregate and authority: Decision is transition-bearing. RuleEvaluation and
  Correction are immutable supporting records with their own exact subject kinds;
  neither is an alias for Decision authority.
- Atomicity: each command writes its declared stream. A correction appends a
  correction record and never rewrites or deletes the erroneous event.
- State/history: reduce_decision, reduce_rule_evaluation, and reduce_correction keep
  proposal/review/resolution lineage, rule facts, and historical correction links
  replay-visible.
- Concurrency/idempotency: expected Decision version/tail, one effective terminal
  resolution, stable duplicate receipt, explicit amendment/supersession lineage.
- Decisive negatives: proposer resolving without authority; review substituted for
  decision; RuleEvaluation treated as Decision; resolution with stale proposal or
  missing review; amendment mutating resolved history; correction targeting a
  prohibited kind; replacement/deletion of the original record; and owner acceptance
  inferred from PR/review/Jira state.

## 9. W11 downstream compatibility stress test

W11 is not fused with WP6.1. Its 81-row catalogue is used only to test whether the
family/engine distinction remains useful downstream. Seven W11 domain families are
sufficient because content observation, independent review, Decision, and exact-byte
authority are horizontal mechanisms applied within the domain that owns the subject.
They are not an eighth monolithic “authority lifecycle.”

The horizontal tags below are:

- H-REV — independent outcome or authority review;
- H-DEC — proposal/resolution or owner Decision;
- H-AUTH — exact content/file/acceptance authority chain;
- OBS — observation without judgment;
- MIG — legacy transition or cutover, still gated;
- GEN — one-time accepted-catalogue genesis, still gated.

### 9.1 Complete W11 row-to-family crosswalk

Every accepted OR row appears exactly once. Family counts sum to 81.

| Exact W11 row ID | Primary W11 family | Horizontal tags |
|---|---|---|
| OR-001 | W2 Candidate/Assay | OBS |
| OR-002 | W2 Candidate/Assay | — |
| OR-003 | W2 Candidate/Assay | H-AUTH |
| OR-004 | W2 Candidate/Assay | — |
| OR-005 | W2 Candidate/Assay | — |
| OR-006 | W2 Candidate/Assay | H-REV |
| OR-007 | W2 Candidate/Assay | H-REV |
| OR-008 | W2 Candidate/Assay | — |
| OR-009 | W2 Candidate/Assay | H-DEC |
| OR-010 | W2 Candidate/Assay | H-DEC |
| OR-011 | W2 Candidate/Assay | H-DEC, H-AUTH |
| OR-012 | W2 Candidate/Assay | H-DEC |
| OR-013 | W2 Candidate/Assay | H-DEC |
| OR-014 | W3 Spike | — |
| OR-015 | W3 Spike | H-DEC |
| OR-016 | W3 Spike | H-DEC |
| OR-017 | W3 Spike | H-AUTH |
| OR-018 | W3 Spike | — |
| OR-019 | W3 Spike | — |
| OR-020 | W3 Spike | H-REV |
| OR-021 | W3 Spike | H-REV |
| OR-022 | W3 Spike | — |
| OR-023 | W3 Spike | H-DEC |
| OR-024 | W3 Spike | H-DEC |
| OR-025 | W3 Spike | H-DEC |
| OR-026 | W3 Spike | H-DEC |
| OR-027 | W3 Spike | H-DEC |
| OR-028 | W4 Dossier expected-set/admission | H-AUTH |
| OR-029 | W5 Scout/annotation/observation | OBS |
| OR-030 | W5 Scout/annotation/observation | OBS |
| OR-031 | W7 Legacy transition/cutover | OBS, MIG |
| OR-032 | W7 Legacy transition/cutover | H-DEC, MIG |
| OR-033 | W7 Legacy transition/cutover | H-DEC, MIG |
| OR-034 | W2 Candidate/Assay | H-REV |
| OR-035 | W2 Candidate/Assay | H-REV |
| OR-036 | W3 Spike | H-REV |
| OR-037 | W3 Spike | H-REV |
| OR-038 | W2 Candidate/Assay | H-REV |
| OR-039 | W2 Candidate/Assay | H-REV |
| OR-040 | W3 Spike | H-REV |
| OR-041 | W3 Spike | H-REV |
| OR-101 | W2 Candidate/Assay | H-AUTH |
| OR-102 | W2 Candidate/Assay | H-AUTH |
| OR-103 | W2 Candidate/Assay | H-AUTH, OBS |
| OR-104 | W2 Candidate/Assay | H-AUTH, OBS |
| OR-105 | W2 Candidate/Assay | H-AUTH, H-REV |
| OR-106 | W2 Candidate/Assay | H-AUTH, H-REV |
| OR-107 | W2 Candidate/Assay | H-AUTH, H-DEC |
| OR-108 | W2 Candidate/Assay | H-AUTH, H-DEC |
| OR-109 | W2 Candidate/Assay | H-AUTH |
| OR-110 | W4 Dossier expected-set/admission | H-AUTH |
| OR-111 | W4 Dossier expected-set/admission | H-AUTH, OBS |
| OR-112 | W4 Dossier expected-set/admission | H-AUTH, H-REV |
| OR-113 | W4 Dossier expected-set/admission | H-AUTH, H-REV |
| OR-114 | W4 Dossier expected-set/admission | H-AUTH, H-DEC |
| OR-115 | W4 Dossier expected-set/admission | H-AUTH, H-DEC |
| OR-116 | W6 Path registration/successor projection | H-AUTH |
| OR-117 | W6 Path registration/successor projection | H-AUTH, OBS |
| OR-118 | W6 Path registration/successor projection | H-AUTH, H-REV |
| OR-119 | W6 Path registration/successor projection | H-AUTH, H-REV |
| OR-120 | W6 Path registration/successor projection | H-AUTH, H-DEC |
| OR-121 | W6 Path registration/successor projection | H-AUTH, H-DEC |
| OR-122 | W7 Legacy transition/cutover | H-AUTH, MIG |
| OR-123 | W7 Legacy transition/cutover | H-AUTH, OBS, MIG |
| OR-124 | W7 Legacy transition/cutover | H-AUTH, H-REV, MIG |
| OR-125 | W7 Legacy transition/cutover | H-AUTH, H-REV, MIG |
| OR-126 | W7 Legacy transition/cutover | H-AUTH, H-DEC, MIG |
| OR-127 | W7 Legacy transition/cutover | H-AUTH, H-DEC, MIG |
| OR-128 | W7 Legacy transition/cutover | H-AUTH, MIG |
| OR-129 | W7 Legacy transition/cutover | H-AUTH, OBS, MIG |
| OR-130 | W7 Legacy transition/cutover | H-AUTH, H-REV, MIG |
| OR-131 | W7 Legacy transition/cutover | H-AUTH, H-REV, MIG |
| OR-132 | W7 Legacy transition/cutover | H-AUTH, H-DEC, MIG |
| OR-133 | W7 Legacy transition/cutover | H-AUTH, H-DEC, MIG |
| OR-134 | W7 Legacy transition/cutover | H-AUTH, MIG |
| OR-135 | W7 Legacy transition/cutover | H-AUTH, OBS, MIG |
| OR-136 | W7 Legacy transition/cutover | H-AUTH, H-REV, MIG |
| OR-137 | W7 Legacy transition/cutover | H-AUTH, H-REV, MIG |
| OR-138 | W7 Legacy transition/cutover | H-AUTH, H-DEC, MIG |
| OR-139 | W7 Legacy transition/cutover | H-AUTH, H-DEC, MIG |
| OR-140 | W1 Catalogue genesis/activation | H-AUTH, GEN |

### 9.2 W11 family counts and compatibility result

| W11 family | Rows | Count | Result |
|---|---|---:|---|
| W1 Catalogue genesis/activation | OR-140 | 1 | One-time externally authorized genesis is distinct from catalogue authorship and runtime discovery. |
| W2 Candidate/Assay | OR-001–OR-013, OR-034–OR-035, OR-038–OR-039, OR-101–OR-109 | 26 | Candidate, Assay, outcome review, and Assay-bar authority form one domain chain while retaining horizontal role separation. |
| W3 Spike | OR-014–OR-027, OR-036–OR-037, OR-040–OR-041 | 18 | Spike planning/execution/outcome stays separate from Assay but reuses the same authority/review/decision mechanisms. |
| W4 Dossier expected-set/admission | OR-028, OR-110–OR-115 | 7 | Expected-set acceptance and admission remain one bounded domain; expected and observed producers remain separate. |
| W5 Scout/annotation/observation | OR-029–OR-030 | 2 | Observation is explicitly non-authoritative and does not become another judgment lifecycle. |
| W6 Path registration/successor projection | OR-116–OR-121 | 6 | Path authority is independent of legacy transition/cutover. |
| W7 Legacy transition/cutover | OR-031–OR-033, OR-122–OR-139 | 21 | Observation, mapping, transition, closure, and cutover remain gated and must not execute from this crosswalk. |

This stress test supports the engine/family split: E1–E4 can be reused, while the
seven W11 primary domains retain distinct subjects and gates. It does not establish
W11 runtime feasibility, implementation authority, KAN-58 completion, genesis,
migration, or cutover.

## 10. Dependency-ordered WP6.1 PR plan

### 10.1 Pre-dispatch integration gate

There is no single verified SHA today containing the design base and every pending
infrastructure subject. Therefore no implementation packet is currently
dispatchable. Before P1, the owner must supply one exact integration SHA and the
dispatcher must verify:

1. 207d92d93dd614e5e5f70c781d4bd11110b17488 is an ancestor;
2. the accepted command/event trees still equal
   9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea and
   154ffc4bdde82fe903718734687e7a62797b1f69;
3. ea589d1a0b450828a7b6d013e2334dfccdca5ee5, or an explicitly accepted
   superseding correction, is an ancestor;
4. the owner has reconciled the live PR #205 identity discrepancy and identified
   whether bf2649c6a6fbc02bbd66e1b16403f564e1a22029 is a required dependency;
5. the exact base is clean, attached to the pre-created implementation branch, and
   has no uncommitted setup rewrites; and
6. separate runtime implementation authority has been given.

The missing integration SHA is a deliberate stop, not permission to merge, cherry-pick,
or manufacture a fallback base.

### 10.2 Serial PR sequence

Path budgets count changed repository paths, including tests. Every PR must stay under
100 paths. The target is under 90; exceeding the target requires a named dependency
or blast-radius explanation before work continues.

| Order | Complete vertical subject | Rows/families | Dependency | Planned path budget and ownership |
|---|---|---|---|---|
| P1 | Message pilot | F6; 13 rows | Pre-dispatch integration gate | Target 8–12, hard plan ceiling 14. One Terra vertical owner; one central-file owner. |
| P2 | Scope completion plus remaining Task and Blocker closure | F1 remaining 1, F2 remaining 14, F7 all 2 | P1 family decision = proceed | Target 12–20, ceiling 28. One Terra owner; Scope completion may be a bounded Luna subpacket only after the central pattern is frozen. |
| P3 | Lease and resource ownership | F4; 9 rows | P2 Task readiness state | Target 12–20, ceiling 28. Terra owns lease/authority/replay; mechanical resource fixtures may be Spark only after semantics freeze. |
| P4 | Dispatch and atomic ClaimDispatch | F3; 11 rows | P2 and P3; composite-lock correction present | Target 14–24, ceiling 32. Terra owns the exact two-stream transaction and both reducers. No parallel Task/Dispatch owner. |
| P5 | Attempt, checkpoint, and operator control excluding GATE-REC | F5; 19 ungated rows | P3 and P4 | Target 16–28, ceiling 36. Terra owns Attempt/control/replay; Luna may take a known-pattern single-stream leaf only after exact interfaces freeze. |
| P6 | Artefact authority and consumer firewall | F8; 9 rows | P5 publishes valid attempt/artefact references | Target below 90, hard ceiling 99. Terra owns producer plus all direct consumers named by caller search; if 99 cannot hold, stop for architectural replan instead of splitting acceptance semantics. |
| P7 | Review and Decision closure | F9 and F10; 18 rows | P6 artifact/evidence subjects | Target 18–32, ceiling 40. One Terra owner preserves Review/Decision non-substitution; one Sol exact-subject review. |
| P8 | Backup/restore catalogue rows | F5 GATE-REC; 2 rows | Separate owner decision on WP6.4 recovery boundary and an exact accepted base | Target 10–20, ceiling 28. Not dispatchable from this design; never absorb 3d5a1a merely because it is open. |

Each PR includes its accepted runtime bindings, payload/event producer, authority and
state validation, declared append set, reducer, replay/projection, receipt facts,
decisive positives/negatives, and compatibility surface. No later “T7/T8 cleanup PR”
is planned. After P8, the exact-set binding suite is a validation gate on the candidate
head, not a semantic substitute and not automatically another PR.

No W11 implementation PR is authorized by this sequence.

## 11. Model and task routing

| Route | Honest packet shape | Examples |
|---|---|---|
| Spark | Frozen, mechanical, exactly 1–3 paths, exact prompt and expected tests, no state-machine or authority judgment | Add already-specified literal matrix cases; update a frozen fixture list; mechanical path/hash assertion |
| Luna | Bounded known-pattern vertical after an existing accepted family establishes the interface | ScopeCompleted on the established Scope pattern; a simple single-stream Blocker leaf if all authority/state facts are frozen |
| Terra | One cross-cutting state machine, authority seam, atomic write set, reducer/replay seam, or bounded consumer firewall | Message pilot; Lease/resource; ClaimDispatch; Attempt control; Artefact firewall; Review/Decision |
| Sol | Architecture, ambiguous boundaries, dependency reconciliation, and fresh independent exact-subject review | This design; pilot proceed/regroup decision; exact candidate review |

The following cannot honestly be sent to Spark: any runtime binding activation,
authority subject resolution, CommandService or EventLedger change, reducer/replay
logic, concurrency/idempotency logic, or protected-identity decision.

The following cannot honestly be sent to Spark or Luna: ClaimDispatch atomicity,
recovery-state-machine reconciliation, Artefact consumer-firewall closure,
Review/Decision authority separation, a new shared-engine abstraction, or fresh
exact-subject acceptance review. Their correctness depends on judgment across
multiple authority and history seams.

Semantic family does not imply one agent. PR slice does not imply one Jira issue.
Only the central owner edits the central seam, serially.

## 12. Recommended pilot: F6 Message

### 12.1 Why this pilot maximises information at bounded risk

Message is the smallest family that still tests row cardinality versus implementation
cardinality: ten exact publication rows share PublishMessage and MessagePublished,
while delivery, acknowledgement, and failure add real competing transitions. It
exercises exact active bindings, discriminant-specific payload construction,
authority, immutable linkage, idempotency, concurrency, reducer/replay, projections,
and negative-matrix reuse. It has one stream per command and no provider, filesystem
mutation, owner Decision, multi-stream append, migration, or cutover.

It therefore answers whether the central engines can carry a coherent family before
the programme risks the two-stream ClaimDispatch or the broad Artefact firewall.

### 12.2 Prompt-ready implementation brief

#### Role and boundary

Implement exactly the WP6.1 F6 Message runtime vertical. Do not change accepted schema,
catalogue, manifest, strict-contract, or owner-decision bytes. Do not invoke providers,
publish external messages, create external-party records, update Jira, request
CodeRabbit, merge, or claim acceptance.

#### Exact base dependency

The exact required dependencies are:

- main foundation 207d92d93dd614e5e5f70c781d4bd11110b17488;
- accepted command tree 9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea;
- accepted event tree 154ffc4bdde82fe903718734687e7a62797b1f69; and
- Windows lock correction ea589d1a0b450828a7b6d013e2334dfccdca5ee5,
  unless the owner names one exact accepted successor.

The owner must insert one exact integrated BASE_SHA that contains those dependencies
and resolves the live PR #205 identity before dispatch. Verify cwd, symbolic branch,
HEAD equals BASE_SHA, required ancestry, upstream, and clean status before writing.
If no such single SHA is supplied, stop. Do not merge, cherry-pick, invent a fallback
branch, or use a foreign worktree to create it.

#### Owned semantic rows

Exactly:

message.publish_assignment,
message.publish_acknowledgement,
message.publish_progress,
message.publish_input_request,
message.publish_escalation,
message.publish_report,
message.publish_review_request,
message.publish_review_response,
message.publish_decision_request,
message.publish_handoff,
message.deliver,
message.acknowledge, and
message.delivery_failure.

No Task, Attempt, Review, Decision, Artefact, provider, or W11 transition is owned.
Those records may be validated references only.

#### Protected identities

All versions are 1.0.0. The implementation consumes, and must not edit, these exact
accepted identities:

| Type | Repository path | Schema ID | Canonical schema SHA-256 |
|---|---|---|---|
| Command | .research-system/schemas/core/commands/publish_message.schema.json | ars://core/command/PublishMessage | 14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c |
| Event | .research-system/schemas/core/events/message_published.schema.json | ars://core/event/MessagePublished | f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f |
| Command | .research-system/schemas/core/commands/record_message_delivery.schema.json | ars://core/command/RecordMessageDelivery | 9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828 |
| Event | .research-system/schemas/core/events/message_delivered.schema.json | ars://core/event/MessageDelivered | 7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388 |
| Command | .research-system/schemas/core/commands/acknowledge_message.schema.json | ars://core/command/AcknowledgeMessage | 3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d |
| Event | .research-system/schemas/core/events/message_acknowledged.schema.json | ars://core/event/MessageAcknowledged | 576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be |
| Command | .research-system/schemas/core/commands/record_message_delivery_failure.schema.json | ars://core/command/RecordMessageDeliveryFailure | afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89 |
| Event | .research-system/schemas/core/events/message_delivery_failed.schema.json | ars://core/event/MessageDeliveryFailed | 0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5 |

Before and after implementation, verify the accepted command and event tree IDs, not
working-tree reserialisations.

#### Owned paths

The initial owned path allowlist is:

- research_system/schema_registry.py;
- research_system/command/service.py;
- research_system/command/reducers.py;
- research_system/projection/replay.py;
- tests/research_system/factories.py;
- tests/research_system/unit/test_schema_registry.py;
- tests/research_system/unit/test_command_service.py;
- tests/research_system/unit/test_replay.py; and
- one new tests/research_system/integration/test_wp6_1_message_lifecycle.py.

research_system/store/ledger.py is read-only unless a contract-first red test proves
the existing single-stream append interface cannot preserve an accepted Message
invariant. If that trigger occurs, stop and obtain central-owner approval before
adding it. A family-specific message module may replace service.py growth only if it
uses the current service interface and does not create a generic framework.

No .research-system path is writable. The PR target is 8–12 paths and must not exceed
14 without a Sol replan.

#### Contract-first red tests

Write failing tests first with literal catalogue row IDs in test IDs:

1. exactly the four command and four event bindings above become active and preserve
   ID, version, accepted SHA, and raw bytes;
2. each of the ten PublishMessage discriminants produces MessagePublished with the
   exact row-specific required facts and no foreign fields;
3. Message progresses only
   none-to-published-to-delivered-to-acknowledged or
   none-to-published-to-delivery_failed;
4. every row rejects missing, wrong, expired, not-yet-effective, wrong-kind,
   wrong-subject, and wrong-actor authority before state/version mutation;
5. unsupported, missing, aliased, or payload-inconsistent discriminants reject;
6. wrong sender, recipient, subject, content hash, correlation/reply identity, adapter,
   and source position reject as applicable;
7. duplicate identical command returns the original receipt and changed reuse of the
   command ID rejects;
8. delivery versus failure and acknowledgement races have one winner with a stable
   loser reason and unchanged event tail;
9. reducer replay and external projection rebuild reproduce exact state and linkage;
10. unknown major event identity, broken provenance, missing reducer, or divergent
    terminal history fails closed; and
11. every rejected command leaves event tail, receipt acceptance state, and all
    projections unchanged.

The matrix must enumerate all 13 row IDs once. Shared parametrisation is encouraged;
wildcard tests or one generic “message works” case are not sufficient.

#### Required behavior

Use SchemaRegistry active bindings, CommandService authority/idempotency/state
validation and event construction, EventLedger single-stream append, reduce_message,
projection replay, and existing receipt conventions. Strip caller-supplied
provenance, derive exact command/event identity from the active binding, preserve
immutable content/linkage, and return stable rejection codes. Do not add a lifecycle
DSL, generator, persistence layer, or external adapter action.

#### Validation ladder

1. Identity preflight: verify cwd/branch/HEAD/status/ancestry, then verify the accepted
   command/event tree IDs and the eight schema hashes.
2. Red contract: run the new Message integration module and exact new unit node IDs;
   record that failures are semantic, not missing fixtures.
3. Focused green:
   uv run pytest -q tests/research_system/integration/test_wp6_1_message_lifecycle.py
   plus the exact Message node IDs added to test_schema_registry.py,
   test_command_service.py, and test_replay.py.
4. Changed-behavior regression: run the complete four touched unit modules only if
   shared helper changes make node-level selection incomplete. State that trigger.
5. Broader package/full suite only if a narrow failure identifies wider impact, a
   shared API changed, or an explicit gate requires it. Run any required broad suite
   once at final candidate HEAD.
6. Direct artifact check: diff against BASE_SHA; only allowlisted runtime/test paths;
   no .research-system or unrelated change; accepted schema tree IDs unchanged.
7. Run repository hooks through the normal commit. Use a multiline OS temp file and
   git commit -F. Do not bypass hooks.

#### Commit, PR, and review rules

- Suggested subject: [PIPELINE] P00: activate WP6.1 message lifecycle.
- One implementation commit is preferred; remediation commits are allowed without
  rewriting protected history.
- Push only the named implementation branch supplied by the owner.
- The owner or dispatcher may open the PR only if separately authorized.
- Fresh Sol exact-subject review must resolve candidate commit, parent, tree, changed
  paths, protected trees, 13-row matrix, and exact validation evidence.
- Review acceptance is not owner acceptance, merge authority, Jira completion, or
  Gate 6 closure. Stephen triggers and monitors CodeRabbit manually.

#### Stop conditions

Stop without workaround if:

- BASE_SHA or required ancestry is absent;
- any protected schema/catalogue/contract/acceptance byte changes;
- a row ID, authority subject, payload fact, reducer target, or negative identity is
  ambiguous;
- the current interface cannot express the family without a new generic framework;
- a second stream or external action appears necessary;
- another active owner edits a central path;
- the change would exceed 14 paths;
- focused tests expose a dependency on pending recovery, provider, migration, or W11
  work; or
- the requested action becomes merge, owner decision, Jira update, or external
  publication.

## 13. Measurable pilot completion and programme decision

### 13.1 Pilot completion rule

The pilot is implementation-complete only when one exact candidate satisfies all of:

1. 13 of 13 exact catalogue row IDs appear once in the executable matrix;
2. four exact command and four exact event bindings are active;
3. all eight accepted schema identities/hashes and both accepted schema trees are
   unchanged;
4. all 13 positive cases pass;
5. every matrix row passes the common authority, idempotency, concurrency, failed-
   mutation, replay, and projection axes, plus its applicable decisive negatives;
6. the two competing terminal paths are race-tested with one stable winner;
7. replay and projection rebuild are byte/field equivalent to online reduction for
   the observed state;
8. the diff is allowlisted, no more than 14 paths, and contains binding, producer,
   reducer, replay/projection, and decisive tests together;
9. hooks and the justified validation ladder pass at the exact candidate HEAD; and
10. a fresh independent Sol review records an exact-subject verdict with no unresolved
    Critical or Major finding.

These conditions establish a reviewable implementation candidate only. A separate
owner decision is still required to proceed.

### 13.2 Proceed, regroup, or abandon

Proceed to P2 when all completion conditions hold and:

- one central owner delivered the family in one PR;
- no new generic framework or persistence layer was needed;
- family-specific logic has one owner and one reducer;
- shared mechanisms were extended by stable interfaces rather than copied; and
- the owner explicitly chooses proceed after reviewing exact evidence.

Regroup before P2 when the semantic behavior passes but any of these occurs:

- Message needs more than one PR or more than 14 paths;
- more than five shared central paths require semantic edits;
- publication and delivery cannot share one aggregate/reducer without aliases;
- identical missing-interface logic appears in at least two concrete families; or
- the exact negative matrix exposes a different authority or projection owner.

Regroup means revise family/engine boundaries and review the new design; it does not
authorize a framework.

Abandon the current family decomposition when:

- accepted Message schemas cannot express the required state machine without an
  exact-byte defect and owner-approved reopening;
- the existing append/replay model cannot preserve Message atomicity or history
  without a new persistence/event-sourcing layer;
- one family cannot own the required authority, append set, reducer, replay, and
  decisive negatives as one review subject; or
- the next two concrete families independently falsify the same chosen boundary.

Abandonment returns to Sol architecture and owner decision. It does not reactivate
T1–T8 as implementation ownership by default.

## 14. Explicit non-goals and human gates

### Non-goals

- No runtime code, schema, catalogue, contract, acceptance record, or Jira change in
  this design subject.
- No provider automation, live provider call, owner-operated external session, or
  external-party record.
- No W11 runtime, KAN-58 completion, OR-140 genesis, research execution, legacy
  observation, mapping, transition, migration, or cutover.
- No absorption of KAN-67, Slice L, live PR #205, or the WP6.4 recovery candidate.
- No generic lifecycle DSL, generator, event-sourcing framework, or persistence layer.
- No one-handler, one-agent, one-PR, or one-Jira-issue-per-row plan.
- No inference of semantic completion from documentation, materialisation, passing
  tests, PR merge, CodeRabbit, owner silence, or Jira status.

### Owner/human gates

Stephen or an explicitly authorized human owner must:

1. reconcile the exact pending-branch/PR identities and choose one integration SHA;
2. authorize the bounded runtime pilot from that exact SHA;
3. decide any protected-byte defect before accepted bytes are reopened;
4. decide whether a new shared abstraction is warranted after two concrete failures;
5. decide the separate WP6.4 recovery boundary before GATE-REC rows;
6. review the exact pilot evidence after independent exact-subject review;
7. choose proceed, regroup, or abandon; and
8. separately authorize PR creation, merge, Jira changes, any external action, W11
   genesis, or legacy cutover.

## 15. Unresolved design risks

1. No single current SHA contains the management/main base plus the named pending lock
   correction, and live PR #205 no longer denotes that correction. Exact integration
   identity is the immediate dispatch blocker.
2. CommandService._build_event is already branch-heavy. The pilot must measure whether
   a family-specific module is sufficient before anyone proposes a generic router.
3. F5's project-store backup/restore rows may ultimately require a separately accepted
   recovery family. This design maps them but keeps them gated.
4. The F8 consumer firewall may approach the 90-path target because caller closure,
   not catalogue row count, defines its blast radius. The hard cap remains 99.
5. W11 demonstrates compatible decomposition on paper only. Its external authority,
   genesis, successor projection, and legacy fences require separate exact-subject
   implementation evidence.
6. The six active rows establish a useful pattern but do not prove that authority,
   append, replay, and projection interfaces carry every remaining family.

## 16. Final recommendation

Approve this as the dispatch design, not as runtime or owner acceptance. Resolve the
exact integration base first. Then dispatch one Terra-owned F6 Message vertical with
one central owner and a fresh Sol exact-subject review. Use its measured result to
decide whether the ten-family/four-engine organisation materially reduces handoffs
without weakening exact authority, atomicity, replay, projection, or negative-case
closure.
