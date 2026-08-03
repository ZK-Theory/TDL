# 06p — WP6.1 lifecycle macro-campaign execution plan

| Field | Value |
|---|---|
| Status | Successor planning proposal; requires fresh adversarial review and owner acceptance before delivery |
| Date | 2026-08-03 |
| Exact planning base / current `main` | `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e` |
| Planning-base tree | `e765b75c458ebf194dd80cef6c66d11e5360e6a7` |
| Planning branch | `codex/wp6-1-lifecycle-macro-campaign-plan` |
| Preserved design authority | `0e842969c770811edf5c81dcd7e4f7a647e050ad:docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md` |
| Superseded execution ordering | `a557ab0e00d5d1497735f21b593823b12a5df866:docs/plans/agentic-research-system/implementation/06o-wp6-1-lifecycle-execution-plan-after-message-pilot.md` |
| Workflow | Standalone; supervision phase `certify` until this exact plan is reviewed and accepted |

This document replaces the P2–P8 execution ordering in 06o. It does **not** reject
the ten-family semantic ownership design in 06m, the Message-pilot retrospective,
the verified 104/19/85 row census, or the candidate-readiness controls learned from
that pilot. The defect was narrower and consequential: 06o promoted semantic family
grouping into implementation order without proving that each early slice already had
the Attempt, Artefact, Review, Decision, authority, linkage, and projection evidence
producers its rows consume.

This is planning and dispatch design only. It does not change or authorize runtime
code, tests, protected schema or catalogue bytes, Jira, pull requests, decision
registers, external review services, providers, merges, Gate 6, or research execution.
Plan acceptance and semantic-contract acceptance are distinct owner acts.

## 1. Decision: campaigns, not a row queue

The ten families remain the ownership map:

`Scope`, `Task`, `Dispatch/claim`, `Lease/resource`, `Attempt/operator`, `Message`,
`Blocker`, `Artefact`, `Review`, and `Decision/rule/correction`.

They are not the execution schedule. The remaining work is reorganized into three
end-to-end capability campaigns and one separately gated recovery subject:

| Unit | Capability delivered | Remaining rows |
|---|---|---:|
| C1 — Admission to running | A current Task can pass readiness, acquire resources, be dispatched and atomically claimed, and start an Attempt | 23 |
| C2 — Controlled execution and outcome handoff | A running Attempt can checkpoint, pause/resume, stop, terminate, register outputs, request exact Review, submit the Task to review, drive blockers/input/suspension through every accepted source state, close operational dispatch state, and cancel safely | 28 |
| C3 — Evidence to governance closure | Registered outputs gain independent evidence and use authority; requested Reviews and Decisions become canonical; Tasks can accept, reject, close Partial, reopen, and permit exact Scope completion | 32 |
| R1 — Backup/restore assurance | Backup creation and restore verification only, under a separate owner-approved recovery contract | 2 |
| **Total** | | **85** |

The campaign is the orchestration and completion unit. A catalogue row is an
acceptance-census item, never a one-row work ticket. Each campaign may use a small
dependency-ordered PR stack when the exact dependency graph or the `<100`-file
external-review cap requires it, but the manager holds one campaign goal and delivers
the whole named capability. Parallel work is admitted inside that goal after semantic
freeze; it is not deferred until the preceding family is entirely complete.

```mermaid
flowchart LR
    G0["Global semantic freeze"] --> C1["C1: Admission to running (23)"]
    C1 --> G2["C2 contract freeze"]
    G2 --> C2["C2: Controlled execution and outcome handoff (28)"]
    C2 --> G3["C3 authority and epoch freeze"]
    G3 --> C3["C3: Evidence to governance closure (32)"]
    C3 --> GR["Recovery owner decision"]
    GR --> R1["R1: Backup/restore assurance (2)"]
```

The semantic-freeze nodes contain zero lifecycle rows. They are upstream contract and
owner-decision subjects, not miniature implementation slices and not permission to
redesign protected schemas in place.

## 2. Exact state and authority boundary

At the planning base:

- the accepted catalogue contains 104 unique normalized WP6.1 rows;
- 19 rows are active: the six Scope/Task foundation rows and the 13 Message rows;
- 85 rows remain;
- the protected command tree is
  `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` (87 files);
- the protected event tree is
  `154ffc4bdde82fe903718734687e7a62797b1f69` (86 files);
- file presence is not runtime activation; only explicit exact bindings activate a
  command/event pair (`research_system/schema_registry.py:56-76`, `:79-183`,
  `:308-384`, `:456-512`);
- the accepted Message implementation remains evidence for four command/event pairs
  and 13 normalized rows only.

The active normalized rows are:

`scope.create`, `scope.amend_revision`, `scope.supersede`, `task.create`,
`task.amend_revision`, `task.supersede`, all ten `message.publish_*` discriminants,
`message.deliver`, `message.acknowledge`, and `message.delivery_failure`.

`task.supersede` is not counted again. Every campaign that changes Task reduction,
replay, projection, currentness, or retry behavior carries the existing SupersedeTask
compatibility controls as regressions, including the separately named stale-
classification manifestation.

No accepted source authorizes mutation or equivalent reserialization of the 173
protected schema bytes. If a required relation cannot be expressed, the contract
author must propose a separately versioned successor identity while preserving every
accepted `1.0.0` byte. That subject requires fresh review and owner acceptance before
activation.

## 3. Why the 06o P2 execution unit was not dependency-complete

The family decomposition was sound. The P2 execution boundary was not.

| Early P2 row or seam | Missing or later evidence producer | Controlling evidence |
|---|---|---|
| `task.submit_review` | Attempt outcome, candidate Artefact IDs/hashes, and requested Review identities | `docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md:231`; W2 §§16–17 |
| `task.accept` / `task.reject` | Exact satisfied Review set, selected Artefacts, verdict subject hash, and governing authority | `06d:233-234`; `docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md:752-779` |
| `task.pause` / `task.cancel` | Canonical Attempt/process/checkpoint disposition; cancellation occurs only after active attempts stop, abandon, or are declared orphaned | W2 `:536-545` |
| `task.block` / `task.request_input` / `task.resume` | Typed affected-object identity, suspension identity, and exact resolution/supply evidence | W2 `:619-645`; protected `RecordBlocker`, `BlockTask`, `RequestInput`, and `ResumeTask` cannot currently express the complete join |
| `task.close_partial` and reopen | Accepted useful outputs, restrictions, preserved terminal record, and a new execution epoch | W2 `:650-670` |
| `scope.complete` | Exact disposition of every required member after terminal governance outcomes | `06a:49-66`; `06d:222` |
| shared `PartialOutcomeRecorded` | Producer-qualified Task-versus-Attempt binding and reducer routing | protected event discriminant plus `research_system/schema_registry.py:479-490`; current `EXACT_LIFECYCLE_BINDINGS` is event-schema keyed |
| Scope/Task projection | Exact accepted event representation, retained evidence, history, and deterministic rebuild | current Scope replay expects a legacy shape (`research_system/projection/replay.py:176-199`, `:533-541`) |
| human/agent/service authority | Canonical, non-self-attested actor-class proof | W2 `:858-870`; current resolver proves only the bootstrap owner as human (`research_system/authority.py:2166-2183`) |
| `ClaimDispatch` atomic production | One command must build and append ordered Task plus Dispatch events with an exact declared write set | current lifecycle activation excludes `ClaimDispatch`, `_build_event` constructs only `DispatchClaimed`, and ordinary submission appends `[event]` (`research_system/command/service.py:90-109`, `:1221-1245`, `:3290-3292`) |
| `artefact.use_authority` | Exact accepted predicate, Review IDs/hashes, Decision ID/hash, and subject hash | 06i requires these joins (`docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:147-162`), while the protected command admits only a free string predicate plus generic `evidence_refs` (`.research-system/schemas/core/commands/set_artefact_use_authority.schema.json:6-52`) |

The correction is to cut across families at real producer/consumer boundaries. It is
not to discard family ownership, split the work into 85 tickets, or put every row
behind one enormous serial Sol task.

## 4. Upstream semantic-freeze programme

Contract authorship stays upstream of implementation. Each item below is a discrete
exact-byte subject with its own author, fresh reviewer, and owner decision. A campaign
may start only when the subjects in its deadline column are accepted and current at
its exact base.

### 4.1 Semantics already forced by accepted sources

These are closure obligations, not open policy choices:

1. `AmendTask` creates a new revision without silently escaping
   `readiness_pending`; pre-amendment readiness evidence cannot authorize the new
   revision (W2 `:1064`; `06d:224-226`).
2. `ClaimDispatch` remains one command with the ordered two-stream batch
   `[DispatchClaimed, TaskClaimStarted]`; Task and Dispatch ownership are never split
   (`06d:144-172`, `:230`, `:244`).
3. Derived event fields come from named authoritative preimages. Task and Attempt
   Partial production is producer-qualified, with `subject_kind` derived by the
   trusted producer rather than supplied as caller authority.
4. Protected event fields are consumed exactly. Reducers and replay may not normalize
   a valid `ScopeCompleted` event into an incompatible legacy payload.
5. Replay is deterministic, projections are regenerable and non-authoritative, and
   deleting or editing a projection cannot change command acceptance (`06a:133-139`).
6. Artefact registration precedes any Attempt terminal record that cites that
   artefact. Validation and use authority remain separate later dimensions (W2
   `:511-525`, `:672-706`).
7. Reopen is governance history, not backup/restore recovery. Every reopen creates a
   new execution epoch and preserves the original terminal outcome.

### 4.2 Exact successor subjects requiring owner acceptance

| Proposed subject | Minimum content | Required before | Author / reviewer |
|---|---|---|---|
| `actor-identity-proof-v1` | Owner-issued immutable `actor_id -> actor_class` proof; issuer, effective interval, revocation, exact identity/hash, unknown-actor failure; separately versioned lifecycle identities if the accepted envelope cannot bind that proof | C1 | Sol Ultra author/adjudicator; different fresh Sol Ultra reviewer |
| `lifecycle-retry-and-residue-v1` | Stable logical-submission and command-ID rules; current authority/history; retained-artifact integrity; changed-ID conflict; permitted repair; append ordering; full event/receipt/index Cartesian classification | C1 | Sol Ultra; fresh Sol Ultra review |
| `core-lifecycle-projection-v1` | Exact Task, Scope, Lease, Dispatch, Attempt, Blocker, Artefact, Review, Decision, operations, and governance projection records; retained revisions/evidence/history; producer-aware routing; genesis/incremental equivalence | Base section before C1, then campaign-specific sections before C2/C3 | Sol Ultra; fresh Sol Ultra review |
| `readiness-assessment-v1` | Required-set authority, evaluator identity/version, Task revision/hash, freshness/equality rule, Request-versus-Approve separation, invalidation after amendment | C1 | Sol Ultra; fresh Sol Ultra review |
| `campaign-routing-ledger-v1` | Strict machine-enforced packet schema and validator for model/thinking, exact base/branch/root, accepted hashes, literal path ownership, concurrency collision, dependencies, integration owner, validation, stops, and placeholder rejection; includes negative controls | Before any C1 worker fan-out | Sol Ultra contract; Terra Max validator; fresh Sol Ultra review |
| `task-suspension-link-v2` | Exact Task/Attempt/Blocker/Input/suspension identities and versions; record -> suspend -> resolve/supply -> resume order; no cross-object evidence substitution; successor schemas where required | C2 | Sol Ultra; fresh Sol Ultra review |
| `execution-outcome-handoff-v1` | Owner-approved 06i partial-cutover amendment: `RegisterArtefact` recomputes exact immutable provenance and forces initial `candidate` with no use authority; `RequestReview` creates the exact requested Review identity/subject hash; `SubmitForReview` binds the terminal Attempt, registered Artefacts, and requested Reviews; no scientific-review, satisfaction, Decision, or consumer authority is implied | C2 | Sol Ultra; fresh Sol Ultra review |
| `terminal-epoch-v1` | Initial epoch, exact `current + 1` reopen rule, terminal event ID/hash/Task/status binding, immutable prior outcome, allowed return state, and accepted/rejected/partial/cancelled discriminants | C3 | Sol Ultra; fresh Sol Ultra review |
| `artefact-review-decision-authority-v1` | Six independent Artefact dimensions, consumer firewall, scientific Review evidence, Review-versus-Decision separation, 06i Stage A/B ordering, rule-evaluation non-authority, Task acceptance set, correction history; resolve the protected `SetArtefactUseAuthority` evidence-reference insufficiency through separately versioned successor identities rather than same-version reinterpretation | C3 | Sol Ultra; fresh Sol Ultra review |
| `backup-restore-boundary-v1` | Snapshot contents and consistency point, source/store identity, manifest verification, restore rehearsal versus cutover, witness/provenance joins, writer authorization, failure/no-mutation rules | R1 only | Sol Ultra; fresh Sol Ultra review |

Plan acceptance authorizes the manager to materialize and submit these contract
subjects in dependency order. It does not pre-accept bytes that do not yet exist and
does not authorize runtime activation. A second semantic remediation cycle on any
subject is an owner-rescope stop.

### 4.3 Explicit deferrals

- W11 revision 0.5 is not a WP6.1 authority source. Its 81-row materialization,
  runtime transitions, migration, and cutover remain a separate reviewed programme.
- Provider automation and live adapter discovery remain deferred. An unexpected
  provider/credential dependency is a campaign stop.
- General lifecycle frameworks, bulk activation, convenience projections, migration,
  and performance work remain out of scope unless separately authorized.
- Recovery optimization beyond the minimum R1 assurance proof is deferred until R1
  itself is accepted.

## 5. Normative 85-row campaign allocation

Every remaining row appears exactly once below. The allocation is normative for
campaign scope; intra-campaign implementation is by capability layer, never row order.

### 5.1 C1 — Admission to running (23)

`task.request_readiness`, `task.approve_readiness`, `task.claim_start`;

`dispatch.issue`, `dispatch.deliver`, `dispatch.acknowledge`, `dispatch.claim`,
`dispatch.expire_issued`, `dispatch.expire_delivered`,
`dispatch.expire_acknowledged`, `dispatch.withdraw_issued`;

`lease.activate`, `lease.renew`, `lease.release`, `lease.expire`, `lease.revoke`;

`attempt.create`, `attempt.claim`, `attempt.start`;

`operator.request_resource_grant`, `operator.claim_execution_lease`,
`operator.record_heartbeat`, `operator.release_resources`.

### 5.2 C2 — Controlled execution and outcome handoff (28)

`task.block`, `task.request_input`, `task.pause`, `task.submit_review`,
`task.resume`, `task.cancel`;

`dispatch.fulfil`, `dispatch.withdraw_claimed`;

`attempt.complete`, `attempt.fail`, `attempt.partial`, `attempt.pause`,
`attempt.resume`, `attempt.request_stop`, `attempt.abandon`,
`attempt.supersede`, `attempt.retry`;

`checkpoint.record`;

`blocker.record`, `blocker.resolve`;

`artefact.register`;

`review.request`;

`operator.request_pause`, `operator.confirm_pause`, `operator.request_stop`,
`operator.confirm_stop`, `operator.request_resume`, `operator.quarantine_orphan`.

### 5.3 C3 — Evidence to governance closure (32)

`scope.complete`;

`task.accept`, `task.reject`, `task.close_partial`,
`task.reopen_partial`, `task.reopen_rejected`, `task.reopen_cancelled`;

`artefact.availability`, `artefact.regenerability`, `artefact.integrity`,
`artefact.structural_validation`, `artefact.scientific_review`,
`artefact.use_authority`, `artefact.supersede`,
`operator.adopt_late_artefact`;

`review.assign`, `review.start`, `review.record_verdict`,
`review.request_changes`, `review.satisfy`, `review.satisfy_after_changes`,
`review.withdraw`, `review.supersede`;

`decision.propose`, `decision.request_review`, `decision.resolve`,
`decision.reject`, `decision.expire`, `decision.supersede`, `rule.evaluate`,
`decision.amend`, `correction.record`.

### 5.4 R1 — Backup/restore assurance (2)

`operator.create_backup`, `operator.verify_restore`.

### 5.5 Mechanical census result

The plan-author check parsed the 06m crosswalk and compared it with the active set and
the allocation above:

| Check | Result |
|---|---:|
| Catalogue rows / unique rows | `104 / 104` |
| Active rows | `19` |
| Remaining rows | `85` |
| C1 / C2 / C3 / R1 | `23 / 28 / 32 / 2` |
| Allocated rows | `85` |
| Duplicate / missing / extra | `0 / 0 / 0` |

The dispatcher must rerun this comparison against current accepted catalogue bytes.
A count match without exact-set equality is a failure.

## 6. Campaign briefs

### 6.1 Common execution context

- Workflow system: `standalone`.
- Campaign supervision phase: `deliver` only after this reviewed plan and the
  campaign's prerequisite exact contracts are owner-accepted.
- Context: one fresh campaign manager; one serial central implementer; fresh bounded
  parallel tasks; fresh exact-subject reviewer with no author history.
- Branch roles: management state, semantic-contract candidate, campaign integration,
  bounded leaf candidate, fresh review, and later integration closer are distinct.
- Integration base: exact live `main` named at campaign dispatch, with ancestry and
  protected identities reverified before every write.
- External-review owner: Stephen. Campaign tasks neither trigger nor poll CodeRabbit.
- Author-review cycle: one. A proposed second semantic remediation stops for owner
  rescope and a fresh task.
- External-review cap: hard `<100` changed files, target `<=90` per review subject.
- Research-value disposition: canonical lifecycle correctness, provenance,
  reproducibility, and valid research-governance authority are required; unrelated
  hardening is deferred.
- Results rule: no toy, synthetic, or illustrative output is written to `results/`.

Each campaign manager creates a tracked warning-first task-state manifest before its
first worker dispatch. That existing manifest records stale-state claims—task ID,
deliverables, blockers, planned contracts, rooted inputs, and trackable outputs. It
does **not** enforce the routing ledger, and its advisory `ok=True` results never enable
dispatch. Because this is a standalone workflow, it does not invoke the APM-coupled
`manager_dispatch_check` CLI. It calls that module's advisory state-manifest reader
directly:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
@'
from pathlib import Path
from shared.manager_dispatch_check import check_state_manifest

workspace = Path(r'<exact-worktree-root>').resolve()
project = Path(r'C:\Users\steph\TDL').resolve()
manifest = Path(r'<tracked-campaign-state.yaml>').resolve()
checks = check_state_manifest(manifest, workspace, project)
for check in checks:
    print(f'{check.name}: {check.detail}')
'@ | C:/Users/steph/TDL/.venv/Scripts/python.exe -
```

Every warning is retained and dispositioned; this command is never summarized as a
pass merely because it exits zero. Dispatch is blocked separately by the strict
validator in §7.4.

### 6.2 C1 brief — Admission to running

**Goal:** prove through the public command seam that a current Task revision can pass
an authoritative readiness assessment, acquire one valid resource/lease ownership,
be issued/delivered/acknowledged, be atomically claimed with its Task, and start one
Attempt under exact context/root/lease bindings.

**Required upstream contracts:** accepted exact bytes for
`actor-identity-proof-v1`, `lifecycle-retry-and-residue-v1`, the C1 portion of
`core-lifecycle-projection-v1`, and `readiness-assessment-v1`.

**Capability stack:**

1. freeze actor/readiness/retry/projection interfaces and derive the exact positive-
   path writable closure;
2. materialize readiness plus Lease/resource ownership as one admission foundation;
3. materialize Dispatch and the atomic `ClaimDispatch` Task/Dispatch batch;
4. materialize Attempt create/claim/start and prove the complete admission journey;
5. integrate frozen Luna/Spark leaves, then review the exact C1 integration head.

These are layers of one campaign, not separate row completion goals. Layer 3 owns
both `dispatch.claim` and `task.claim_start`; no worker may split them.

**Central implementation:** Terra Ultra. One Terra task owns every changed shared
semantic seam, including any accepted edits to `schema_registry.py`, `authority.py`,
`command/service.py`, `command/lifecycle.py`, `command/reducers.py`,
`projection/replay.py`, shared receipt/lock fixtures, and campaign integration tests.
`EventLedger` remains read-only unless a reviewed red contract proves a missing
accepted capability.

**Parallel leaves after freeze:**

- Luna Max may own one readiness/Lease single-stream leaf or a dedicated, disjoint
  integration-test module. Its literal path list must exclude every central path.
- Spark High may own a 1–3-path literal 23-row census, frozen fixture table, or
  protected-tree assertion packet. It may not derive expected semantics.

**Acceptance capability:** one end-to-end public-seam test reaches a running Attempt;
double claim yields exactly one holder; Task/Dispatch/Lease/Attempt identities and
versions join exactly; Task and Dispatch advance together or neither; readiness
evidence invalidates on amendment; expiry/withdrawal discriminants do not cross;
same-submission retry, changed-ID conflict, residue repair, no-mutation, replay, and
projection equivalence all follow accepted contracts.

**Stops:** unresolved actor/readiness proof, split ClaimDispatch ownership, new lock or
transaction framework, hidden provider dependency, protected-byte mutation, path
collision, incomplete positive-path closure, or a second semantic remediation.

### 6.3 C2 brief — Controlled execution and outcome handoff

**Goal:** prove that a running Attempt can checkpoint, pause/resume, stop, complete,
fail, produce a Partial outcome, abandon, supersede, or retry; that outputs are
registered before terminal citation; that an exact requested Review is created and
the Task enters `review_pending`; that Blocker/Input suspension links cannot be
substituted from any accepted source state; and that Dispatch/Task operational closure
follows canonical evidence.

**Required upstream contracts:** accepted C1 integration subject; accepted
`task-suspension-link-v2`; accepted C2 projection section, including the Artefact view
consumed by orphan quarantine; accepted producer-qualified Task/Attempt Partial
routing; and accepted `execution-outcome-handoff-v1`. This last subject is the exact
owner-approved 06i partial cutover: registration is forced to `candidate`, creates no
consumer authority, and the minimal Review-request/Task-submit path supplies the real
`review_pending` state consumed by Task block/input/pause/resume/cancel edges. The
catalogue's
`reduce_recovery` name for `operator.quarantine_orphan` does not move that row into R1:
it is an operational C2 transition over Attempt/Artefact/operations projections, with
no backup, restore, migration, or cutover authority (`06d:332`).

**Capability stack:**

1. materialize checkpoint, pause/resume, request/confirm stop, and Attempt terminal
   evidence with registered Artefact manifests;
2. create the exact requested Review, submit the Task against terminal Attempt and
   registered Artefact evidence, and prove the public `review_pending` source state;
3. materialize Blocker/Input/suspension links and Task block/input/pause/resume across
   every accepted source state;
4. close claimed Dispatch only from terminal/stop evidence and cancel a Task only
   after every active Attempt is stopped, abandoned, or explicitly orphaned;
5. integrate retry/supersession lineage, late races, Luna/Spark leaves, and the full
   running-to-review-handoff capability proof.

**Central implementation:** Terra Ultra. The same serial Terra owner controls all
shared binding, authority, service, reducer, replay, projection, receipt, checkpoint,
and Task/Attempt/Dispatch integration seams.

**Parallel leaves after freeze:**

- Luna Max leaf A may own a disjoint checkpoint/operator test or family-local module
  after its signatures and caller set are frozen.
- Luna Max leaf B may own a disjoint Blocker/Input/suspension test module after exact
  successor schema identities are accepted.
- Spark High may materialize only literal 28-row, stop-evidence, residue, or protected-
  identity tables in 1–3 paths.

**Acceptance capability:** one end-to-end public-seam journey runs and terminates an
Attempt, registers each cited Artefact as `candidate`, creates the exact requested
Review, submits the Task to `review_pending`, closes the claimed Dispatch, and applies
the appropriate Task operational result. Pause/stop requesters cannot self-confirm when
the contract requires separation; resume proves checkpoint compatibility and current
lease; cancel proves terminal process disposition; unrelated Blocker/Input evidence
cannot resume a Task; Attempt Partial routes to Attempt state; all failure branches
leave ledger, receipts, indexes, projections, authority, locks, and artefact manifests
unchanged.

`task.resume`, block, input, pause, and cancel are tested here through the public seam
from every accepted state class, including the real `review_pending` state produced by
this campaign. C3 carries preservation controls, not a deferred proof of C2 row
closure.

**Stops:** dangling Artefact IDs, direct Task mutation of a Blocker stream, untyped
resume evidence, requester/confirmer collapse, live recovery/cutover, shared-path
collision, or producer-unqualified Partial routing.

### 6.4 C3 brief — Evidence to governance closure

**Goal:** prove the complete research-governance journey from a registered candidate
Artefact and requested Review through independent evidence dimensions, use authority,
Review satisfaction, Decision,
Task terminal governance, reopening, and exact Scope completion.

**Required upstream contracts:** accepted C2 integration subject;
`terminal-epoch-v1`; `artefact-review-decision-authority-v1`; the C3 projection
section; explicit resolution of the 06i Stage A/B and minimum-Decision ordering.

**Capability stack:**

1. advance the requested Review and materialize Decision authority foundations required by scientific Review
   and Artefact-use decisions without allowing either record type to substitute for
   the other;
2. materialize the six non-substitutable Artefact evidence dimensions, supersession,
   late adoption, and direct/transitive consumer firewall;
3. complete Review/Decision/rule/correction lifecycles and their authority races;
4. integrate Task accept/reject/Partial/reopen, preserve every C2 Task-control edge,
   and apply `scope.complete` with exact member dispositions;
5. integrate Luna/Spark leaves and review the entire evidence-to-governance subject.

**Central implementation:** Terra Ultra after Sol Ultra contract freeze. One Terra
owner integrates Artefact, Review, Decision, Task, Scope, authority, consumer,
reducer, replay, and projection seams. Sol does not become an implementation default
merely because the subject is difficult; Sol owns ambiguity resolution and review.

**Parallel leaves after freeze:**

- Luna Max leaf A may own one frozen Artefact evidence-dimension module/test cluster
  with no consumer-firewall or shared authority edit.
- Luna Max leaf B may own one frozen single-stream Review transition/test cluster with
  no Decision, Task-acceptance, or shared reducer/replay edit.
- Spark High may materialize literal 32-row, consumer-census, review/decision
  discriminant, or protected-identity tables in 1–3 paths only.

**Acceptance capability:** no producer self-attestation; all six Artefact dimensions
remain independent; every real consumer fails closed before route/grant/lease/provider
effects when authority is absent/stale; subject-hash drift invalidates Review;
verdict never equals satisfaction, Decision, or Task acceptance; RuleEvaluation never
supplies owner authority; correction appends without rewriting history; Task acceptance
names the exact satisfied Review and selected Artefact set; each reopen advances the
epoch exactly once and preserves the actual terminal record; Scope completion names
the exact revision and a typed disposition for every required member.

**Stops:** incomplete consumer inventory, Review/Decision substitution, inferred owner
acceptance, epoch or terminal-record ambiguity, protected-byte reopening, path count
at 100, or an attempt to import W11 authority.

### 6.5 R1 brief — Backup/restore assurance

R1 remains blocked until Stephen accepts `backup-restore-boundary-v1` against a
current exact store/recovery base. It is not a home for ordinary retry, Task reopen,
Blocker handling, orphan classification, or migration.

After acceptance, Sol Ultra freezes the recovery boundary, Terra Ultra owns the
central implementation, Luna Max may own a disjoint restore-test leaf, and Spark High
may own literal two-row manifest/assertion tables. No task may infer live restore,
cutover, deletion, provider action, or authorization from an older recovery candidate.

## 7. Intelligent model and task routing

Model choice follows semantic risk and path ownership, not quotas. The named model
and thinking level are part of the packet identity.

| Work class | Model / thinking | Why | Never owns |
|---|---|---|---|
| Architecture, unresolved semantics, exact contract authorship, hard-finding adjudication | `gpt-5.6-sol`, Ultra | Highest ambiguity and authority risk | Routine central implementation after freeze; self-review |
| Shared known-pattern implementation and integration | `gpt-5.6-terra`, Ultra (Max only for a demonstrably narrower frozen subject) | Strong sustained implementation across central seams | Owner policy invention; exact-subject review of its own work |
| Bounded frozen leaf with disjoint paths | `gpt-5.6-luna`, Max | Efficient parallel implementation/test work once semantics are fixed | Central bindings, authority, service, reducer/replay/projection joins, concurrency design |
| Purely mechanical 1–3-path packet | `gpt-5.3-codex-spark`, High | Fast literal census, fixture, and protected assertion work | Any semantic inference, activation, authority, state, reducer, replay, projection, concurrency, recovery, protected identity decision, or review |
| Fresh independent exact-subject review | `gpt-5.6-sol`, Ultra | Adversarial semantic and authority review | Remediation or owner acceptance |

### 7.1 Dispatch mechanism

1. The portfolio manager pre-creates one unique task branch at the exact campaign
   integration/freeze commit.
2. Terra, Luna, Spark, and Sol reviewer work run in separate fresh Codex tasks with
   the model and thinking level explicitly set. Luna and Spark are launched as new
   Codex chat/worktree tasks, not silently replaced by ordinary subagents.
3. A task may start detached. Its prompt permits one deterministic switch to the
   pre-created task branch only after detached `HEAD` and the branch ref equal the
   required commit. No fallback branch or different commit is permitted.
4. Every packet names the exact base, capability deliverable, row coverage,
   dependencies, accepted contract hashes, literal allowed and forbidden paths,
   concurrency group, integration owner, validation, stop/escalation conditions, and
   fallback disposition.
5. If the named model/thinking combination is unavailable, the task is not silently
   substituted. The manager records `model_unavailable` and requests an owner-approved
   named replacement or waits.
6. A leaf that discovers a semantic choice or needs a central path stops and returns
   the issue to the Terra integration owner; it does not expand its own scope.

### 7.2 Model routing exercised during plan development

The plan itself was constrained by three fresh, read-only Codex tasks launched from
the exact planning base with explicit models and thinking levels:

| Planning task | Model / thinking | Bounded contribution |
|---|---|---|
| `019fc902-f951-7181-ba24-59c71ec1f527` | Terra Max | Reconstructed current central seams, confirmed the 104/19/85 census, exposed the single-event `ClaimDispatch` gap and the 06i Review/Decision ordering cycle |
| `019fc902-f94f-7530-a114-765611ee18d2` | Luna Max | Reconstructed cross-family producer dependencies and confirmed that safe fan-out is limited to frozen disjoint leaves around one serial central lane |
| `019fc903-ad2c-77d1-9279-5ee8be83ec1c` | Codex Spark High | Mechanically parsed the 104-row set, the 19 active rows, and the P2–P8 85-row partition with zero duplicate, overlap, omission, or extra remaining rows |

These outputs are advisory planning evidence, not repository authority, owner
acceptance, or self-review. Their factual claims were rechecked against the cited
repository sources before inclusion here.

### 7.3 Routing ledger required for every packet

```yaml
packet_id: wp6-1-<campaign>-<lane>
campaign_id: C1 | C2 | C3 | R1
capability_deliverable: <one bounded vertical outcome>
exact_base: <sha>
freeze_subjects:
  - id: <contract-id>
    sha256: <accepted raw bytes>
catalogue_rows: [<exact normalized rows>]
model: gpt-5.6-sol | gpt-5.6-terra | gpt-5.6-luna | gpt-5.3-codex-spark
thinking: ultra | max | high
model_reason: <risk and capability rationale>
branch: <pre-created unique branch>
authorized_root: <exact worktree root>
allowed_paths: [<literal closed list>]
forbidden_paths: [<literal closed list or protected prefix>]
concurrency_group: <serial-central | leaf-wave-N | mechanical-wave-N>
integration_owner: <task/thread id>
dependencies: [<exact commits or packet ids>]
validation: [<exact commands>]
stop_escalation: [<observable conditions>]
fallback: stop_model_unavailable_or_semantic_expansion
```

No task is prompt-ready while a field remains a placeholder.

### 7.4 Strict routing-ledger enforcement

Before any C1 worker fan-out, the accepted `campaign-routing-ledger-v1` package must
materialize exactly:

- `.research-system/contracts/wp6-1-campaign-routing-ledger.schema.json`;
- `shared/campaign_routing_check.py`;
- `tests/provenance/test_campaign_routing_check.py`.

The validator fails closed on a placeholder; unknown or disallowed model/thinking
pair; absent or mismatching base/branch/root; unaccepted or malformed SHA/hash;
catalogue-row mismatch; allowed/forbidden overlap; cross-packet path or generated-
output collision; missing dependency; unowned integration; absent validation/stop;
or any path outside the exact authorized root. Its negative suite contains one control
for each failure class and a positive multi-packet concurrency plan. Live task creation
must additionally return the exact requested model/thinking pair; tool rejection is
`model_unavailable`, never permission to substitute.

Every packet is checked before task creation and again before integration:

```powershell
C:/Users/steph/TDL/.venv/Scripts/python.exe -m shared.campaign_routing_check `
  --campaign-state <tracked-campaign-state.yaml> `
  --ledger <exact-routing-ledger.yaml> `
  --workspace <exact-authorized-worktree-root> `
  --base <exact-sha>
```

There is one bootstrap exception because the validator cannot validate its own first
materialization. A Sol Ultra-authored exact contract and literal three-path brief is
manually certified by the portfolio manager; one serial Terra Max task implements
only the three paths above; a fresh Sol Ultra reviewer verifies the exact subject and
all negative controls. No Luna/Spark task, parallel packet, runtime lifecycle edit, or
second path expansion is allowed during bootstrap. After acceptance, no further
manual exception exists.

## 8. Parallelism and integration topology

Within each campaign:

1. **Freeze:** Sol authors/adjudicates missing upstream semantics; a different fresh
   Sol reviews; Stephen accepts exact bytes. The manager records the accepted hashes.
2. **Trace:** Terra traces one public positive path from protected schema bytes through
   activation, authority, preparation, event construction, append, exact lifecycle
   binding, reducer, replay, projection, and receipt/index recovery. This trace derives
   the actual central writable closure.
3. **Partition:** the manager creates a collision matrix. Terra receives every shared
   path. Luna/Spark receive disjoint literal lists only. Two live tasks never own the
   same path, symbol, generated output, or fixture.
4. **Parallel wave:** Terra advances the central capability while Luna builds frozen
   leaves and Spark builds mechanical artifacts. Parallel tasks do not integrate each
   other and do not write the management/integration branch.
5. **Integrate:** the named campaign integration owner verifies each leaf commit,
   accepted base, ancestry, changed paths, tests, and absence of central-path drift,
   then composes it in the dependency order recorded before dispatch.
6. **Certify:** run the targeted campaign suite once at the exact integrated candidate.
   Expand only for a named shared-caller, generator/schema, API, config, or gate trigger.
7. **Review:** a fresh Sol Ultra task reviews the exact campaign integration subject.
   Review acceptance is not owner acceptance or merge authority.
8. **Handoff:** the campaign goal ends at a durable PR-ready handoff before Stephen's
   CodeRabbit wait. A fresh lightweight closer starts only after Stephen reports that
   external review is complete and separately authorizes the requested integration.

A campaign may be represented by one PR when its exact integrated subject stays at
`<=90` changed files. If the positive-path closure predicts more, the manager declares
a dependency-safe vertical stack before implementation. Each stack member must
preserve the accepted predecessor as an ancestor and remain a capability layer; no
stack may be created by dividing the row list into arbitrary batches.

### 8.1 Pipeline overlap without speculative implementation

The portfolio does not become idle at an owner-controlled external-review boundary.
After a campaign reaches a stable PR-ready handoff:

- its large implementation goal terminates and is not repeatedly reloaded merely to
  poll unchanged state;
- the portfolio coordinator may advance the next campaign's read-only source audit,
  exact contract authorship, fresh contract review, owner-decision packet, branch/path
  design, and mechanical census preparation;
- Luna/Spark leaf packets may be drafted but are not dispatched until their exact
  freeze subject and base exist;
- downstream runtime implementation starts only from the accepted predecessor after
  integration, or from a separately owner-authorized cross-campaign stack whose exact
  ancestry and review boundaries were declared in advance.

This overlaps independent certification work while preserving canonical-transition
ordering. It is neither a one-row queue nor permission to build against prospective
approval.

## 9. Mandatory candidate-readiness evidence

Before a campaign's fresh independent review, its exact candidate contains or is
accompanied by executable evidence for all applicable items:

1. exact campaign row-set equality and active-row non-duplication;
2. accepted contract/raw-byte identities and protected 87/86 tree equality;
3. one complete public positive-path dependency and writable-path trace;
4. a derived-field preimage table for every hash, position, version, actor, subject,
   linkage, epoch, terminal record, receipt, and projection field;
5. row -> command/event/discriminant -> authority -> reducer -> replay -> projection
   census, with producer command for shared event identities;
6. missing/wrong-kind/wrong-subject/wrong-actor/wrong-project/expired/not-yet-
   effective/revoked/stale authority variants through the public seam;
7. the durable canonical-event/standalone-receipt/scoped-index/incoming-command-ID/
   history Cartesian topology, with each cell classified as exact return, permitted
   repair, typed conflict, or integrity failure;
8. explicit source-order tests for authority/history, retained-artifact integrity,
   command identity, repair, append, and receipt/index publication;
9. no-mutation snapshots covering ledger tail/batches/versions, receipts, indexes,
   replay/history, projections, authority state, locks/markers, and campaign-specific
   stores/manifests;
10. every new control labelled before parent execution as changed-behavior red or
    preservation/characterization green;
11. public callers, registries, wrappers, CLI roots, restore/replay roots, factories,
    and transitive consumers dispositioned fixed/already-compliant/exempt-with-reason;
12. the concurrency/path-collision matrix plus actual model/task/thread routing ledger;
13. current-main merge-base, non-mutating merge-tree composition, changed-file count,
    semantic-overlap disposition, and exact integration regressions;
14. one end-to-end proof of the campaign capability named in §6, not only isolated row
    positives.

A producer's assertion that a matrix or caller census is complete is not evidence.
The fresh reviewer reconstructs exact-set membership and samples public negative
paths independently.

### 9.1 Zero-row portfolio closure after C3

C1–C3 completion is followed by one fresh portfolio closure audit. It implements no
new catalogue row and is not a fourth ordinary campaign. The exact composed head must
prove:

- complete-record multiset equality for all 104 normalized catalogue rows and their
  expanded edges;
- exact active binding equality, including the six pre-Message Scope/Task rows, all
  13 Message rows, and every C1–C3 row—no bulk or accidental activation;
- cross-campaign genesis/incremental replay and byte-identical Task, Scope, Dispatch,
  Lease, Attempt, Blocker, Artefact, Review, Decision, operations, and governance
  projections;
- the full authority attack set and exact subject binding across all 104 rows;
- active Message retry/residue controls and the SupersedeTask compatibility touchback;
- preservation of the Gate 5 evaluation corpus, release evidence, and every protected
  command/event byte;
- current-main merge-tree composition, final changed-file census, and no unresolved
  campaign review finding.

A fresh Sol Ultra reviewer records the exact closure verdict. That verdict remains
evidence for a separate owner/KAN-65/Gate 6 decision; it does not make that decision.

## 10. Validation ladder

The exact commands are frozen by each campaign's positive-path trace. The default
ladder is:

1. direct static checks of row/identity/path/contract manifests;
2. exact new red and preservation-green nodes;
3. the campaign's dedicated integration module;
4. exact shared-caller regressions named by changed central symbols;
5. merge-tree integration checks at the final candidate head;
6. a broader module/package suite only when a narrower check fails, a shared
   generator/schema/API/config changes, caller evidence shows wider impact, no
   narrower test exists, or an explicit gate requires it;
7. a full suite only for an explicit final gate or genuinely cross-cutting candidate,
   run once at the final exact head.

Use `C:/Users/steph/TDL/.venv/Scripts/python.exe` directly with bytecode, pytest cache,
and coverage output disabled for bounded linked-worktree validation. A review checkout
that requires historical Git objects uses a history-bearing clone with
`core.autocrlf=false`, `core.longpaths=true`, successful complete checkout, exact
`HEAD`, and clean status.

## 11. Hard stops and non-goals

Stop the campaign and return to the named owner when any of these occurs:

- protected schema/catalogue bytes drift or a same-version edit is proposed;
- an exact successor contract is missing, stale, unreviewed, or not owner-accepted;
- a task would invent authority, derived-field meaning, projection shape, epoch,
  linkage, consumer policy, or recovery semantics;
- a parallel task needs a central path or its path overlaps another live task;
- a second semantic remediation cycle is proposed;
- the exact review subject reaches 100 changed files without a predeclared safe stack;
- a live provider, credential, migration, cutover, Jira, merge, CodeRabbit, or external
  action becomes necessary but was not separately authorized;
- W11, old recovery work, PR/Jira state, or a review verdict is offered as owner
  acceptance;
- a new generic lifecycle, transaction, projection, or authority framework is proposed
  without two implemented-family evidence and explicit owner approval;
- the campaign can demonstrate isolated transitions but not its named end-to-end
  capability.

This plan does not authorize W11 materialization, bulk activation, provider automation,
live restore/cutover, research execution, result claims, Gate 6 closure, Jira changes,
PR creation, CodeRabbit interaction, merge, or owner acceptance by implication.

## 12. Forward obligation register

| Obligation | Disposition | Gate / owner |
|---|---|---|
| Preserve all 173 accepted schema bytes | Hard invariant; successor versions are additive exact subjects only | Every author/reviewer; Stephen accepts any successor identity |
| Preserve the ten-family semantic map | Retained as ownership and invariant map, not execution order | Portfolio manager and every campaign brief |
| Deliver large batches | C1/C2/C3 are 23/28/32-row capability campaigns; rows are census, not tickets | Fresh campaign manager |
| Use Terra, Luna, and Spark intelligently | Explicit routing ledger and separate model-pinned Codex tasks; no quota or silent substitution | Portfolio manager; Stephen approves any substitution |
| Keep central seams serial | One Terra integration owner per campaign | Campaign manager and path-collision gate |
| Close semantic gaps upstream | Every exact successor subject in §4.2 has a just-in-time deadline; none is accepted by plan prose | Sol authors/reviewers, then Stephen |
| Preserve SupersedeTask behavior | Compatibility touchback wherever Task/shared replay changes; never recount the row | C1–C3 candidates/reviewers |
| Keep W11 separate | No W11 row or authority imported; carry only separately accepted bounded policies | Future W11 review/owner gate |
| Keep recovery separate | Only two R1 rows after `backup-restore-boundary-v1` | Stephen; R1 manager |
| Bound external review | Target `<=90`, hard `<100`; no CodeRabbit polling | Campaign manager; Stephen controls service |
| End large goals at PR-ready | Durable exact-state handoff, then fresh closer after owner notice | Campaign manager and later closer |
| Preserve owner authority | Plan, contract review, code review, Jira, PR, and tests never substitute for owner acceptance | Stephen |

## 13. Plan review, acceptance, and fresh-manager handoff

This exact plan candidate receives a fresh Sol Ultra adversarial design review from a
new task with no author history. The reviewer verifies:

- exact base, parent, tree, plan blob, branch, and protected identities;
- the 104/19/85 census and exact 23/28/32/2 allocation;
- producer/consumer edges and campaign capability closure;
- required-versus-deferrable semantic contracts;
- model suitability, literal path ownership requirements, and real concurrency;
- task-brief completeness, validation triggers, PR caps, review independence, owner
  gates, and all non-authorities;
- contradictions with W2, 06a, 06d, 06i, current runtime seams, and active W11 state.

The reviewer writes one durable report and returns `accept`,
`accept_with_required_changes`, or `rework_required`. This author may perform at most
one bounded remediation against exact findings, after which a fresh reviewer checks
the new exact subject. A second remediation request stops for owner rescope.

Once the plan is acceptance-ready, this author writes a neutral handoff containing
only exact repository state, plan/review subjects, unresolved owner gates, and one next
action. A fresh Sol Ultra manager task—not this planning context—then becomes the
portfolio coordinator. It reads the durable plan, review, and handoff; re-resolves
current state; presents any remaining owner acceptance request; and, only after that
acceptance, begins the upstream semantic-freeze programme and C1 as a 23-row campaign.
