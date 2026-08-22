# 06q — Gate 6 Recovery and Closure Plan

**Date:** 2026-08-22
**Status:** `INCOMPLETE — historical real SPEC run PROVEN; no Gate 6 implementation integrated on main`
**Authority:** sole active Gate 6 recovery and closure plan. Do not create a
06s or another master plan.
**Current base:** `d64c58fa4366e5d7a0b7ddc5b2e0519edafcffd7`
**Jira capability:** KAN-103 under KAN-12; Gate 7 remains blocked on
integrated Gate 6 and final closure evidence.

## 1. Purpose and capability contract

Gate 6 is not complete. A historical real run has proved the research route
can produce a durable, reviewable result, but the implementation that produced
that evidence has not been integrated on `main`.

The target outcome is one connected public path: an authorised Discovery start
and submission, durable SPEC evidence, replay and recovery, task closure, a
fresh bounded real run, a plain-English result, and independently checked
backup/restore evidence. Mocks, temporary stores, fabricated permissions,
synthetic receipts, and agent-written declarations are not Gate 6 proof.

The historical result is retained exactly as evidence: 126 configurations, 42
deterministic reruns, terminal `PROVEN/spec_02_owner_decided`, and ledger
position `444 ResourcesReleased` as the historical run-closure anchor. Later
events exist in the same store, so 444 is not the current store tail. The
immutable event and artefact evidence is listed in the result handoff's
[durable evidence anchors](../handoffs/01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md#durable-evidence-anchors).
The run is a research-use assessment, not a scientific claim. Its `PARK`
decision retains the method as an experimental or benchmark candidate and does
not make it the default empirical method.

## 2. Exact current state and active pointers

- The current base is `d64c58fa4366e5d7a0b7ddc5b2e0519edafcffd7`.
- PR #257 remains an open draft at candidate `dea803490...`; it is an obsolete
  candidate to close unmerged only after a replacement decision is durable.
  Its branch and the dirty `C:\Users\steph\TDL` checkout are preserved.
- PR #258 is closed unmerged at
  `94f8bc1fc92bdc5259acab02e73a3958202ab2e`. Its branch is retained as
  historical evidence. The candidate had 145 changed files, 35,796 additions,
  114 review threads, and seven unresolved P1 families.
- [06r](06r-gate6-pr258-review-convergence-plan.md) is historical PR #258
  convergence evidence only. It is retired/superseded for active execution by
  this plan.
- The result handoff is
  [01M0454KCTYV0E8PB016CP3F6J](../handoffs/01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md).
- P-049 retains the distinction among merge admission, capability integration,
  and Gate 6 closure. Its historical SCALE-01 eligibility-envelope
  application is superseded. P-050 records the real-run outcome and `PARK`
  disposition.
- WP6.1 is integrated prerequisite evidence, not an open Gate 6 lane. KAN-65
  and its C1/C2/C3/R1, Research Methods, and final-proof jobs are `Done`; the
  accepted production subject, independent-review record commit, and merge are
  respectively
  `b0058f396f538a63f94ce68d8f6a49b25f4c4c8f`,
  `0fd4674ee4fc43515c12d498b7f786555f09bba3`, and
  `26df87157013fa078849acb14921bbcfcdfe53f1`.

Step 0 is an administrative reset, not an implementation or closure result.
The documentation writer made no external mutation. The approved plan permits
the main agent, after its own exact-state checks, to create or clean the named
branch/worktree, commit and push the documentation reset, create/update the
replacement PR, update KAN-12 and KAN-103, create six bounded level-0 Tasks,
parent them to the KAN-12 Epic, make each one block KAN-103, read back both
ends of every link, and close PR257 unmerged only after the replacement
decision is durable. It still permits no merge, CodeRabbit trigger or polling,
provider or paid call, live-store write during construction, or final Gate 6
decision.

## 3. Architecture and public boundary

The implementation keeps these existing owners and public seams:

- `DiscoveryRuntime.submit` in `research_system/discovery/runtime.py` for
  Discovery submission;
- `CommandService.submit` in `research_system/command/service.py` for governed
  command publication;
- `replay_discovery` in `research_system/discovery/replay/driver.py` for replay
  and reconstruction;
- `verify_restore_before_writer_lease` in
  `research_system/operations/backups.py` for restore admission before a
  writer lease; and
- the existing task closure contracts, including the ordered
  `SubmitForReview` then `AcceptTask` path.

The six slices rebuild the active behavior as separate components: one action
registry, one pure state evaluator, semantic-intent preparation, transaction
execution and recovery, and result rendering. They must not port the retired
2,900-line `spec_flow.py` or its 5,977-line test wholesale.

The approved public contracts are exact. Every `GitReferenceResolution`
contains `repository_url`, `requested_locator`, `status`, and a non-empty
`resolution_trace`; it contains `subpath` only when the locator has one. A
`resolved` result additionally contains exactly one `canonical_ref`,
`resolved_kind`, and `commit_oid`, and prohibits both `candidates` and
`failure_kind`. An `ambiguous` result instead contains at
least two `candidates`, each with those three fields. An `unavailable` result
contains `failure_kind` exactly `auth`, `timeout`, or `transport`. An `absent`
result is permitted only after the trace proves exhaustive successful
resolution. The three non-resolved states must not emit null or placeholder
singular provenance: `absent` has neither candidates nor a failure kind,
`ambiguous` has no failure kind, and `unavailable` has no candidates. A
malformed locator is an input-validation error, not a resolution result. Every
variant is a closed object: fields not declared for that status are rejected.
`SpecActionIntent` is a semantic
input schema distinct from durable command envelopes: users provide meaningful
inputs, while the system derives IDs, hashes, command envelopes, retry keys,
and receipts. `SpecActionState` is exactly `not_started`, `prepared`, or
`completed`. `ProjectUseDecision` binds the candidate, assay, spike, terminal
owner decision, source correction, evidence artefacts, exact operational Task
identity, and exact governed-code subject. The approved CLI is exactly:

```text
ars discovery spec status --operator-config …
ars discovery spec advance --operator-config … --action … --input …
ars discovery spec result --operator-config … --task-id … --format json|markdown
```

`--operator-config` accepts exactly one JSON `SpecOperatorConfig` document with
schema identity `ars://operations/spec-operator-config` at version `1.0.0`.
Additional fields are forbidden. The required fields are `schema_id`,
`schema_version`, `control_root`, `project_id`, `store_identity`, `route_id`,
`operator_actor_id`, `actor_session_id`, and `authority_grant_id`; `route_id`
must equal `SPEC-GATE6-RUN-V1`. The configuration selects evidence but grants
no authority. The shared loader canonicalizes `control_root`, rejects path
redirection and a wrong root, and verifies the project, store, and route under
the common binding admission. The authority slice separately validates the
named actor, session, and grant for the requested effect. Despite the field's
historical name, `operator_actor_id` is the authenticated caller for that one
invocation: producer, independent-reviewer, owner, and operator actions use
separate configs, sessions, and grants, and the action registry rejects a
caller whose registered role does not match the action.

Step 2 introduces and tests `ars store repair-binding` and `ars store
advance-binding`, which are absent from the Step-0 base. They and the existing
`ars store backup` and `ars store verify-restore` commands must share one
verified binding loader. This plan does not introduce `ars discovery submit`
or `ars discovery status` as new SPEC interfaces, nor a parallel public seam or
second persisted state machine.

The durable store remains append-only. Historical identities are readable;
new writes use canonical identities. Status and advance consume the same
registry and evaluator. A persisted legacy fixture may bypass a new writer
only through an explicitly tested compatibility read path.

## 4. Sequential implementation slices

The following six PRs are sequential latest-`main` slices. Each owns one
invariant family, one observable public path, and one explicit negative matrix.
No live store is written during construction.

### Step 0 — Documentation-only control reset

**Owner:** documentation lane; this iteration.
**Output:** this plan as the sole active Gate 6 recovery/closure authority;
updated pointers in the assigned plan, decision, roadmap, and handoff
documents; historical 06r retirement note.
**Acceptance:** exact assigned documentation paths only, resolved links, no
active SCALE-01 closure prerequisite, P-049/P-050 recorded, PR states accurate,
and `git diff --check` clean.
**Step 0 control boundary:** the approved Step 0 Jira text updates KAN-12 and
KAN-103, creates one level-0 Task job for each of the six PRs, parents every
job to the KAN-12 Epic, and gives every job an outward `Blocks` link to
KAN-103. Jira does not permit a Task to be the parent of another Task, so the
six jobs are KAN-103's blocking siblings rather than its children. KAN-103
must read back six inward blockers and cannot transition terminal while any
one remains open. Each job records its
observable outcome, current gap, next action, authoritative files, closure
evidence, owner, and dependency links, and reads back those links. It also
permits the named branch/commit/push/PR work and closing PR257 unmerged only
after the replacement decision is durable. It does not permit merge, CodeRabbit
trigger or polling, provider/paid work, live-store mutation during
construction, or final Gate 6 closure.

### Step 1 — `G6-SPEC-SOURCE-1`

**Invariant:** source evidence binds exact bytes to a causal prefix. A resolver
must handle heads, lightweight and annotated tags, peeled commits, slash refs,
direct OIDs, and subpaths. It may declare a source absent only after an
exhaustive successful check; ambiguity or unavailability is not absence.

**Main interfaces:** the existing source evidence producer/resolver and its
public SPEC registration path; anchored in-root recovery markers and
append-only correction records bind prior evidence and its causal prefix. The
typed `spec_source_observation` document registers the exact resolved Git
reference and source bytes/hash. Its completion proof separately binds the
later causal registration event before `OR-029` may bind that observation to a
Candidate; the document never self-references its own registration.

**Acceptance boundary:** accept the `neurips2024` lightweight tag at
`145efcde673f1a1897eff250b77221d26c34c479`; preserve the corrected source as
append-only; and reject redirected/junctioned paths, malformed locators,
ambiguity, transport failure, crash-before-publication, and zero-publication
cases without durable side effects.

### Step 2 — `G6-SPEC-STORE-1`

**Invariant:** one verified snapshot and predecessor governs the whole
operation. Selection and read happen under the lock, then revalidate before
publication. Outputs are prevalidated. Marker, object, event, receipt, and
current binding form one recovery identity.

**Main interfaces:** new `repair-binding` and `advance-binding` parsers and
handlers; the `SpecOperatorConfig@1.0.0` schema and shared loader that establish
the canonical root plus exact project/store/route binding for every public
SPEC command; the existing backup and restore seams,
`verify_restore_before_writer_lease`, `replay_discovery`, and all consumers of
one shared verified-binding admission. A reviewed successor may move from the
retired binding to integrated `main`; an arbitrary non-descendant is forbidden.

**Acceptance boundary:** the governed-code manifest versions code, config,
schemas, contracts, locks, and the allowed documentation-only descendant. The
new command parsers and handlers are exercised through their public CLI seam.
One verified-binding admission is shared by all consumers; local
administration is distinct from SPEC semantic authority; schemas remain
append-only. Negatives cover concurrency, crash, wrong root, stale binding,
drift, documentation descendant, separate roots, and historical replay.

### Step 3 — `G6-SPEC-AUTHORITY-1`

**Invariant:** every effect is bound to a session and grant. Semantic
registration intent is a distinct durable schema, and governed producer,
reviewer, and operator roles remain separate. The grant is contained in the
session. An exact completed retry may be read after grant expiry but may create
no new effect.

**Main interfaces:** the common owner/scoped/SPEC authority validator and the
existing command service submission seam. After the Step-2 loader has admitted
the exact store and route, this validator proves that the config-selected
`operator_actor_id`, `actor_session_id`, and `authority_grant_id` authorize the
requested semantic effect; possession of the config is never sufficient.

**Acceptance boundary:** owner, scope, session, grant, effect, and role
separation are checked at the public seam. A retry that is exact and complete
is read-only; a new or incomplete effect after expiry is rejected. No
authority is inferred from a plan, a local file, a test-created permission, or
an agent declaration.

### Step 4 — `G6-SPEC-TASK-1`

**Invariant:** a terminal attempt plus a satisfied review follows the existing
`SubmitForReview` then `AcceptTask` contract. Completion is never inferred
from an attempt, lease, result, or status alone. Failed, partial, incomplete,
or unsatisfied-review work remains open. Restart is idempotent.

**Main interfaces:** the existing task closure commands, projections, replay,
and result handoff seam.

**Acceptance boundary:** append
`tsk_60c5549e-d11f-7d17-8145-d80e144aa537` only after the implementation slice
is merged and its task closure is genuinely satisfied. Tests cover restart,
duplicate closure, failed/partial/incomplete outcomes, and missing review;
none may silently close the task.

### Step 5 — `G6-SPEC-MODEL-1`

**Invariant:** one registry defines every public action, alias, effect set,
document ID, authority requirement, and completion proof. State matrices are
derived from that registry. Completion is conjunctive across route, action,
retry, packet, artefact, content, and registration event.

**Main interfaces:** the shared action registry/evaluator consumed by status,
advance, registration, result rendering, `ProjectUseDecision`, and the result
CLI.

The registry must contain exactly the following 30 actions. Every completed
action has one sealed completion bound to its exact route, action, retry,
packet, subject aggregate, and effect receipts. Variant aliases are
outcome-bound and mutually exclusive for one packet. Repeated Assay work uses
a new `assay_id` and retry ordinal; evidence from an earlier aggregate cannot
complete the later action instance.

For a composite action, each authorized caller may publish only its next exact
effect prefix. The evaluator reports `prepared` between prefixes; a later
producer, reviewer, use-authority actor, or owner continues the same action
identity with a role-specific config and effect-specific retry key. The seal is
written only after every ordered receipt is present. A caller may neither
publish another role's effect nor seal a partial composite action.

The effect and authority tokens below are immutable source bindings, not
implementation-authored summaries:

- `W11 OR-nnn` means the complete owner row in
  `design/11-portfolio-and-discovery-lifecycle.md` at base
  `d64c58fa4366e5d7a0b7ddc5b2e0519edafcffd7`, exact Git blob
  `f90729d0c42a0de98d064fac0824d1969c871c82`.
  Its command/schema, eligible profile, exact authority subject, preconditions,
  ordered events/write set, reducers, projections, receipt, and tests are all
  part of the binding. The corresponding runtime route must equal
  `research_system/discovery/routes.py` Git blob
  `39c28011e1566e2362d08c18eb260c0b6579a400`;
  any disagreement rejects the catalogue.
- `AR`, `SR`, and `AU` mean respectively the exact `artefact.register`,
  `artefact.scientific_review`, and `artefact.use_authority` records in
  `.research-system/contracts/wp6-1-owner-source-catalogue.yaml` Git blob
  `1adc66921ee9c90d8786ff173748150922f1035e`.
  Their complete-record hashes are respectively
  `0b6eadd054aac60b8661747c74a2e92631d7b41b3199d65d8c0716a8c0cc9ff7`,
  `e32c3fc7c7d1d456ba62bbc4011120a944b9c404f9d306d69543ea04f5c0752d`,
  and `1617a904037563d280a73c9a504ef6e96c2b17338776b46a1e9adbc9efce4332`.
  They bind `RegisterArtefact`/`ArtefactRegistered`,
  `RecordScientificReview`/`ScientificReviewRecorded`, and
  `SetArtefactUseAuthority`/`ArtefactUseAuthoritySet`, including their exact
  schemas, subject grants, actor classes, receipts, and negatives.

| Canonical action | Public alias | Ordered effect contract | Required actor/grant | Additional completion proof |
|---|---|---|---|---|
| `bootstrap_genesis` | same | `W11 OR-140` | exact `OR-140` profile and subject grant | exact genesis row |
| `bootstrap_assay_authority` | same | `W11 OR-101`–`OR-108` | exact per-row producer, reviewer, and Stephen grants | all eight rows on one accepted Assay authority subject |
| `bootstrap_dossier_authority` | same | `W11 OR-110`–`OR-115` | exact per-row producer, reviewer, and Stephen grants | all six rows on one accepted expected-set subject |
| `bootstrap_path_authority` | same | `W11 OR-116`–`OR-121` | exact per-row producer, reviewer, and Stephen grants | all six rows on one accepted path-registration subject |
| `admit_dossier` | same | `W11 OR-028` | Operator/auditor R2 exact dossier grant | exact dossier and independent closure tuple |
| `observe_source` | same | `AR(spec_source_observation)` then `W11 OR-029` | source producer `AR` grant and Scout `OR-029` grant | `spec_source_observation` / `ars://portfolio/spec-source-observation` at `1.0.0` contains one `resolved` `GitReferenceResolution` and source bytes/hash; completion separately binds its exact `ArtefactRegistered` event, and `OR-029` binds that artefact in its source-observation multiset |
| `request_spec_01` | same | `W11 OR-003` | Portfolio Steward exact Assay-request grant | exact Candidate, new `assay_id`, accepted bar, and producer relation |
| `register_spec_01_brief_inputs` | same | `AR` for every member of the closed input set | registered input producer with exact per-artefact grants | `spec_01_brief_input_set` / `ars://portfolio/spec-01-brief-input-set` at `1.0.0`; exact registrations only |
| `review_spec_01_brief_inputs` | same | `SR` for every exact registered input | independent verifier with exact per-artefact review grants | all required reviews bind the registered content hashes |
| `accept_spec_01_brief_inputs` | same | `AU` for every exact reviewed input | use-authority actor with exact per-artefact grants | accepted consumer predicates bind the complete governing review set |
| `prepare_spec_01` | same | `AR(spec_01_operator_brief)` | operator/Portfolio Steward exact artefact grant | `ars://portfolio/spec-operator-brief-package` at `1.0.0` |
| `return_spec_01_complete` | `return_spec_01` | `AR(spec_01_return)` then `W11 OR-004` | Assay producer with exact artefact and `OR-004` grants | `ars://portfolio/spec-operator-return` at `1.0.0`; exact complete Assay aggregate |
| `return_spec_01_partial` | `return_spec_01` | `AR(spec_01_return)` then `W11 OR-005` | Assay producer with exact artefact and `OR-005` grants | same schema/version; exact Partial Assay aggregate |
| `review_spec_01_complete` | `review_spec_01` | `W11 OR-034` then `OR-006` | Portfolio Steward request grant and independent-verifier review grant | exact scorecard, request, reviewer relation, and satisfying verdict |
| `review_spec_01_partial` | `review_spec_01` | `W11 OR-035` then `OR-007` | Portfolio Steward request grant and independent-verifier review grant | exact Partial artefact, request, reviewer relation, and satisfying verdict |
| `decide_spec_01` | same | `W11 OR-012` then `OR-013` | Portfolio Steward proposal grant then Stephen exact Decision grant | exact current Assay/review and option-specific state |
| `request_spec_01_revisit` | same | `W11 OR-009` | Portfolio Steward exact revisit-proposal grant | parked Candidate, exact old Assay/review, and satisfied objective revisit predicate |
| `authorize_spec_01_retry` | same | `W11 OR-010` | Stephen exact revisit Decision grant | selected option `RETRY`; old Assay and Candidate become `retry_authorized` |
| `request_spec_01_retry` | same | `W11 OR-011` | Portfolio Steward exact Assay-retry grant | new unused `assay_id`; old/new aggregates and current Assay bar published atomically |
| `correct_spec_01_source` | same | `AR` then `SR` then `AU` | correction producer, independent verifier, and use-authority actor with separate exact grants | `spec_01_source_correction` / `ars://portfolio/spec-01-source-correction` at `1.0.0`; exact amended evidence and causal prefix |
| `approve_spec_02` | same | `AR(spec_02_live_run_approval)` | Stephen exact owner/artefact grant | `ars://portfolio/spec-02-live-run-approval` at `1.0.0`; exact Candidate, promoted Assay Decision, route, scope, and cost ceiling |
| `prepare_spec_02` | same | `AR(spec_02_operator_brief)` | operator/Portfolio Steward exact artefact grant | `ars://portfolio/spec-operator-brief-package` at `1.0.0` |
| `start_spec_02` | same | `W11 OR-014`–`OR-017` | exact Portfolio Steward, Stephen, and Operator/auditor grants from those rows | Candidate is `spike_planning_authorized`; exact Assay `PROMOTE` Decision and separate SPEC-02 approval both bind the plan |
| `return_spec_02_complete` | `return_spec_02` | `AR(spec_02_return)` then `W11 OR-018` | Spike producer with exact artefact and `OR-018` grants | `ars://portfolio/spec-operator-return` at `1.0.0`; exact complete Spike aggregate |
| `return_spec_02_partial` | `return_spec_02` | `AR(spec_02_return)` then `W11 OR-019` | Spike producer with exact artefact and `OR-019` grants | same schema/version; exact Partial Spike/attempt/lease closure |
| `review_spec_02_complete` | `review_spec_02` | `W11 OR-036` then `OR-020` | Portfolio Steward request grant and independent-verifier review grant | exact verdict, request, reviewer relation, and satisfying verdict |
| `review_spec_02_partial` | `review_spec_02` | `W11 OR-037` then `OR-021` | Portfolio Steward request grant and independent-verifier review grant | exact Partial, request, reviewer relation, and satisfying verdict |
| `decide_spec_02` | same | `W11 OR-026` then `OR-027` | Portfolio Steward proposal grant then Stephen exact Decision grant | exact current Spike/review and option-specific state |
| `register_project_use_decision` | same | `AR(project_use_decision)` | registered operator/producer with exact artefact grant | accepted Task already exists; `project_use_decision` / `ars://portfolio/project-use-decision` at `1.0.0` binds the exact result tuple |
| `accept_project_use_decision` | same | `SR(project_use_decision)` then `AU(project_use_decision)` | independent verifier and use-authority actor with exact, non-producer grants | exact registered bytes, complete governing review set, and accepted result-consumer predicate |

`ProjectUseDecision` at `1.0.0` is a closed document. It requires exact references
to the Candidate, current Assay and Spike (or an explicit `no_spike` terminal
reason), terminal owner Decision, source observation and any correction,
evidence artefacts, accepted operational Task, governed-code subject, the
closed disposition `retain_experimental_benchmark | adopt_default | reject`,
plain-language rationale, limitations, and next gates. Unknown fields reject.
The registration action is `prepared` after `ArtefactRegistered` and the result
renderer remains pending until `accept_project_use_decision` records both the
independent scientific review and accepted use authority. An exact completed
retry returns its old receipts; a changed Task, content, binding, or retry key
conflicts and may publish no effect.

A SPEC-01 `PARK` Decision leaves the Candidate `parked` and never satisfies
`start_spec_02`. The separate SPEC-02 approval is necessary but not sufficient.
To continue for the owner-approved Gate 6 operational test, the objective
revisit predicate recorded by the PARK Decision must first become satisfied;
the route then executes `request_spec_01_revisit`,
`authorize_spec_01_retry` with Stephen selecting `RETRY`, and
`request_spec_01_retry`. The complete/Partial return, review, and
`decide_spec_01` actions repeat against the new Assay instance. Only a later
exact `OR-013` `PROMOTE` Decision may create `spike_planning_authorized` and
permit the separately approved SPEC-02 route. If that promotion does not
occur, SPEC-02 remains non-runnable; neither an approval document nor the SPEC
coordinator may bypass W11.

`correct_spec_01_source` remains in the complete registry but is required in a
run only when the accepted evidence establishes that a source correction is
needed. Catalogue-completeness tests fail on any missing or extra canonical
action, alias, effect, document identity, authority requirement, source-token
hash, or completion proof; status, retry, and execution must derive their
matrices from this catalogue rather than maintain subsets.

**Acceptance boundary:** historical IDs remain readable while canonical new
writes use new IDs. Unrelated evidence is isolated. Missing action evidence
evaluates only to `not_started` or `prepared`; there is no fourth
`SpecActionState`. When no correctly bound `ProjectUseDecision` exists, the
human result renderer says `project-use decision pending`. Hash-only or
wrong-binding evidence rejects. The required `--task-id` selector isolates the
historical and fresh results even when both exist. The matrix covers empty,
prepared, completed, conflicting, unrelated, retry, and recovery states for
every registered action. A persisted legacy fixture cannot use the new writer
as a bypass. The frozen-catalogue test also rejects missing, additional, or
divergent actions, aliases, effects, and proofs.

### Step 6 — `G6-SPEC-EXEC-1`, integration, and closure candidate

**Invariant:** semantic intent becomes a snapshot, is evaluated, prepared as a
complete transaction, revalidated under the route lock, published, and sealed.
Status and advance use the same registry and evaluator. Context uses one
accepted snapshot with sealed hash-bound approvals. SPEC-01 runs all required
stages. SPEC-02 requires a separate approval, but a prior `PARK` must also
traverse the exact W11 Assay revisit/retry sequence and end in a later
`PROMOTE`; the approval alone never changes Candidate state.

**Main interfaces:** the semantic-intent preparation and transaction/recovery
seams above, `DiscoveryRuntime.submit`, `CommandService.submit`,
`replay_discovery`, restore-before-writer-lease, and task closure.

**Acceptance boundary:** the route records operator-mediated provider work but
never launches providers, reads credentials, invokes paid services during
construction, or fabricates receipts. A terminal result invokes the existing
task seam. After all six PRs merge and final assembled selection plus an
independent exact-`main` review, admit exactly one owner-reviewed successor
binding, then perform one fresh bounded real SPEC run, replay, task closure,
human result, and governed backup/restore check. A run against a temporary
store or fabricated authority is not closure evidence.

## 5. Review, merge, and exact-subject protocol

Each slice is a latest-`main` PR with the named invariant, observable path,
and negative matrix frozen before implementation. Target size is 25 files;
the hard limit is 35 files and 5,000 non-generated added lines (not generic
changed lines). Terra XHigh owns the
implementation, an independent tester owns the red/green controls, and Sol
Medium performs the whole-boundary logic review for STORE, MODEL, and EXEC.

The affected Gate 6 selection is frozen at each candidate head. Required
checks are exactly `contract-and-session-currency` and
`require-active-currency-workflow`, read back at the exact head. The disabled
repository-wide suite is not represented as green. Generic green tests cannot
substitute for the public-path and no-mutation evidence.
The PR record must capture PR head, candidate head, merge SHA, composed
governed-tree equality, test selection, and review conclusion. Squash/queue
operations must preserve those identities. A second material remediation, or
reopening a P1 in the same invariant family, retires or rescopes the candidate
instead of continuing specimen-by-specimen repair.

Stephen alone triggers or monitors CodeRabbit and authorizes merge. No agent
may trigger CodeRabbit, poll it, merge a PR, or infer owner acceptance. No live
store write occurs in construction slices.

## 6. Fresh live proof and closure sequence

After all six PRs have merged and the composed governed tree has been read back:

1. After all six merges, perform final assembled selection and one independent
   exact-`main` review. The binding request carries that immutable reviewed SHA,
   not the mutable branch name. Under the store writer lock and before the
   first authoritative binding write, the binding service itself performs a
   fresh fetch and independent live-remote read of `refs/heads/main` and
   requires local `HEAD`, refreshed `origin/main`, the live-remote result, and
   the request SHA to be equal. A mismatch rejects with zero authoritative
   binding publication. The locally atomic transaction binds only the reviewed
   commit; because a remote Git ref cannot share the store lock, every later
   binding consumer revalidates live `main` against that commit before any
   semantic effect. An immediate post-publication readback occurs before the
   binding is used. If `main` advances in that interval or later, the exact
   binding remains immutable historical evidence but is non-admissible for new
   effects; repeat candidate selection and independent review before appending
   a reviewed successor. Then append
   the historical `tsk_60c5549e-d11f-7d17-8145-d80e144aa537` acceptance and the
   historical P-050 `ProjectUseDecision` through the same registration and
   independent acceptance actions without rewriting their provenance.
2. Obtain explicit paid-run approval, then repeat Damrich, Berens, and Kobak
   on real `neurips2024` with new IDs and the frozen 126-configuration/42-
   rerun design. Keep producer, reviewer, and operator separate, and obtain a
   separate SPEC-02 approval. When SPEC-01 selects `PARK`, satisfy its recorded
   revisit predicate and complete `OR-009`–`OR-011`, then repeat the Assay and
   obtain an exact later `PROMOTE` before starting SPEC-02; otherwise preserve
   the non-runnable outcome without a state-machine bypass.
3. Persist the fresh route's exact receipt, ledger tail, identity, artefact,
   task, and result bytes. Close the terminal Task only through
   `SubmitForReview` followed by `AcceptTask`, then execute
   `register_project_use_decision` and, through a separate independent reviewer
   session, `accept_project_use_decision`. The public result remains pending
   until both actions complete.
4. Use the historical and fresh read-only result commands with their exact,
   distinct Task IDs, including JSON and Markdown rendering, after replay from
   a fresh process. Verify the historical position-444 `ResourcesReleased`
   run-closure anchor, the fresh terminal Task state, human results, `PARK`
   limitation, and no scientific-promotion language.
5. Create and restore governed backups using the operator-supplied
   `wp64-gate6-backup-root` and `wp64-gate6-restore-verification-root`
   locators. They resolve to distinct fresh roots on the approved same disk.
   This Gate 6 evidence proves logical export and recovery only; it does not
   claim machine-loss resilience. Encrypted off-disk replication, byte/hash
   readback, and its owner evidence remain a separately tracked operational
   capability and are explicitly not a Gate 6 closure requirement.
6. Obtain independent final evidence review, Stephen's closure decision, a
   docs-only final PR, and merged-`main` replay. Reconcile `agent_docs`, Jira,
   and these docs, including KAN-103/KAN-12 transitions. Do not automatically
   rerun a paid workflow after a production defect.

Capability reporting is phase-aware and uses exactly one applicable row:

| Phase | Required status text |
|---|---|
| Construction, before the complete public implementation is on `main` | **Capability status: INCOMPLETE — the historical real SPEC run is PROVEN, but no complete Gate 6 implementation is integrated on `main`.** |
| Assembled code merged and the public path passes, before successor binding | **Capability status: INCOMPLETE — the Gate 6 implementation is integrated on `main`; successor binding and fresh live proof are pending.** |
| Exact integrated implementation bound to the live store | **Capability status: INCOMPLETE — the integrated implementation is bound to the live store; fresh run, task, result, replay, and backup evidence are incomplete.** |
| Fresh run, task, accepted project-use result, replay, and governed same-disk backup/restore evidence complete; final evidence review not complete | **Capability status: INCOMPLETE — integrated fresh proof is complete; independent final evidence review is pending.** |
| All safe closure work and independent final evidence review complete; only Stephen's decision remains | **Capability status: OWNER-BLOCKED — integrated fresh proof is complete; Stephen's Gate 6 closure decision is required.** |
| Stephen's closure decision recorded and final documentation/Jira reconciliation verified | **Capability status: INTEGRATED — Gate 6 is closed on the verified P-050 real SPEC capability.** |

## 7. Assumptions, deferrals, and hard boundaries

- Historical real-run evidence remains valid but does not establish integrated
  code. PR existence, review activity, a green test, or a plan never changes
  that status.
- SCALE-01 v1.0.3 and its eligibility envelope are historical and not a Gate 6
  closure prerequisite. P-049's distinction remains; its SCALE application is
  superseded.
- `PARK` keeps the spectral method out of default empirical use and scientific
  claims. Existing `vis_utils` equivalence and estimand/representation freeze
  are separate empirical-adoption work, not Gate 6 blockers.
- Same-disk verified backup proves Gate 6 logical recovery only. Encrypted
  off-disk replication and byte/hash readback are a separate machine-loss-
  resilience capability, not a Gate 6 closure requirement and not part of the
  Gate 6 status matrix.
- Gate 7 cannot open or dispatch on this evidence alone; it remains blocked on
  integrated Gate 6 and final closure evidence. No scientific promotion is
  implied.
- Step 0 permits the named branch/commit/push/PR and KAN-12/KAN-103 operations,
  six sibling-job/blocking-link readbacks, and eventual unmerged PR257 closure
  after a durable replacement decision. Construction still forbids merge, CodeRabbit
  trigger or polling, provider/paid calls, and live-store mutation; final Gate
  6 closure remains Stephen's owner decision.

## 8. Verification sources

- Historical result: [Gate 6 SPEC real-run result](../handoffs/01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md).
- WP6.1 closure: [historical execution plan and exact integration evidence](06o-wp6-1-lifecycle-execution-plan-after-message-pilot.md).
- Historical convergence evidence: [06r](06r-gate6-pr258-review-convergence-plan.md).
- Decision register: [P-049 and P-050](../03-decisions-and-open-questions.md).
- Historical control distinction: [06p](06p-gate6-control-model-proposal.md).
- Gate-7 boundary: [06l](06l-wp6-7-legacy-consolidation-sequencing.md).
