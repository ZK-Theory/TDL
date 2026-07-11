# ARS Work Package 5.4: Foundation Release-Tranche Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and result-provenance-review. Write one failing
> public-seam test before each production change. The accepted W2/W6/W8
> specifications are the contract authority; do not invent a
> `DeleteEvidenceObject` payload or event.

**Status:** approved for Worker dispatch; implementation remains isolated and
subject to the review-then-merge gate.

**Goal:** Materialize and execute S-014 backup/restore and machine move, S-015
atomic supersession-cycle rejection, and S-016 R3 provider outage. Extend
deletion verification to every registered backup/restore location while
leaving deletion initiation disabled under the approved D-G5-2 deferral.

**Architecture:** Keep the deterministic fixture-package, calibration, typed
trace, exact grader-result closure, and strict release-decision path. Add the
three scenarios as `RELEASE_TRANCHE_CASES` while preserving the historical
37-case `P0_CASES` set for WP5.2 variant responsibilities. Exercise real
production seams: W8 restore evidence rechecked by the W2 command service before
its writer lock; `VerifyEvidenceDeletion` over the expanded topology; a
revision-qualified `SupersedeTask -> TaskSuperseded` graph with auditable
rejected receipts; and W4/W7 routing/provider-outage evidence consumed by the
strict release path. S-016's H row remains `unable_to_grade`, so the tranche is
blocked-by-design under D-G5-1(a).

**Tech stack:** Python 3.13.5, frozen dataclasses, JSON Schema, YAML fixture
packages, canonical JSON/hashes, pytest, ruff, and existing fake transports.

**Owner authorization:** Stephen approved the Gate 5 scope, D-G5-1 option (a),
and D-G5-4 on 2026-07-10. Stephen approved D-G5-2 deferral on 2026-07-10:
`DeleteEvidenceObject` remains O15-open beyond Gate 5, S-014 scopes around it
using `VerifyEvidenceDeletion`, and deletion initiation stays explicitly
capability-disabled. Stephen approved this complete plan on 2026-07-10, closing
D-G5-3 for WP5.4 only and authorizing the exact 40/15/132 re-baseline.

## Global Constraints

- The implementation branch is `pipe/ars-gate5-release-tranche`, created from
  merged `origin/main` after this plan lands. An app-managed worktree starts
  detached: the Worker's first Git mutation is
  `git switch -c pipe/ars-gate5-release-tranche`; never use `git branch -m`.
  Use injected non-secret configuration for the synthetic fixture run. If an
  approved secret manager is unexpectedly required, stop and escalate; never
  copy a user `.env` into the worktree. The Worker commits and reports; the
  Manager alone reviews and merges.
- The Worker runs as GPT-5.6 Sol with xhigh reasoning. Do not inherit the
  Manager model implicitly.
- Review-then-merge is mandatory. CodeRabbit must conclude before an exact-head
  Manager merge. Never fast-forward the dirty local `main`.
- D-G5-2 is literal: do not add `DeleteEvidenceObject`, do not emit
  `EvidenceDeletionPending`, and do not claim deletion initiation exists. O15
  remains open. Only `VerifyEvidenceDeletion -> EvidenceDeletionVerified` may
  be extended or exercised.
- D-G5-1(a) is literal: no live provider, live M/H threshold policy, fabricated
  cross-family identity, lower-family fallback, or acceptance of an H/M row.
  S-016's H row remains blocking `unable_to_grade`.
- WP5.4 materializes evidence but does not authorize Gate 5. Keep
  `gate5_authorized: false` until WP5.6 produces the integrated decision and
  Stephen accepts it.
- Preserve the historical `P0_CASES` set of 37. Add
  `RELEASE_TRANCHE_CASES = {S-014, S-015, S-016}` and derive the 40-case
  `FOUNDATION_CASES` union. Do not make the P0-only variant matrix require the
  three release-tranche cases.
- Exact post-WP5.4 stop conditions are `fixture_count: 40`,
  `blocked_fixture_count: 15`, `fixtures_with_uncalibrated_mutations: 0`,
  `mutation_calibration: "calibrated"`, `result_count: 132`, and
  `candidate_status: "blocked"`. Any other value is Partial and stops the
  Worker; expected files or oracles must not be changed to make drift pass.
- Fake transport and synthetic filesystem roots only. Run every fixture twice
  and require byte-identical decisions/evidence after excluding only IDs and
  timestamps already declared noncanonical by the harness.
- Do not touch WP5.2 variant execution/parity, WP5.3 canonical release-event
  publication, live-grader policy, Gate 6, migration, research-paper compute,
  or research claims.
- Preserve anti-anchoring and exact required-result closure. Missing,
  duplicate, stale, incompatible, or unexpected grader rows remain blocking.
- Commit subjects use `[PIPELINE] P00:` and a `Co-Authored-By` trailer. Write
  multi-line messages to a BOM-free UTF-8 file and use `git commit -F`; never
  `--no-verify`.
- Use `uv run --no-sync`. Per-task gates are:

~~~powershell
uv run --no-sync ruff check research_system tools/ars tests/research_system
uv run --no-sync pytest tests/research_system -q --no-cov
~~~

## Exact D-G5-3 Re-baseline

| Invariant | Merged WP5.1 baseline | WP5.4 target | Derivation |
|---|---:|---:|---|
| `fixture_count` | 37 | **40** | Add S-014, S-015, and S-016 once each |
| `blocked_fixture_count` | 14 | **15** | Existing 14 plus S-016's H row under D-G5-1(a) |
| `result_count` | 122 | **132** | S-014 D/T/O/P = 4; S-015 D/T = 2; S-016 D/T/O/H = 4 |
| `fixtures_with_uncalibrated_mutations` | 0 | **0** | Every new mutation calibrates under the two-repetition rule |
| `mutation_calibration` | `calibrated` | **`calibrated`** | No threshold or oracle relaxation |
| `candidate_status` | `blocked` | **`blocked`** | S-016 H is unavailable; Gate 5 remains unauthorized |

Approval is exact. A WP5.2 count change requires its own D-G5-3 plan approval;
WP5.4 must not anticipate or absorb it.

## File Map

**Create:**

~~~text
.research-system/schemas/operations/backup-receipt.schema.json
research_system/operations/backups.py
research_system/evals/executors/release_tranche.py
tools/ars/materialize_gate5_release_tranche.py
tests/research_system/integration/test_gate5_release_tranche_fixture_corpus.py
tests/research_system/integration/test_gate5_release_tranche.py
.research-system/evals/fixtures/S-014/**
.research-system/evals/fixtures/S-015/**
.research-system/evals/fixtures/S-016/**
~~~

Each fixture directory contains the existing `fixture.yaml`, `README.md`,
`input/stimulus.json`, `input/source-manifest.json`,
`expected/pre-control.json`, `expected/post-control.json`,
`expected/trajectory.json`, and `graders/required.json` package surface.

**Modify only as required by the bounded interfaces below:**

~~~text
.research-system/evals/p0-coverage.yaml
.research-system/schemas/core/receipt.schema.json
.research-system/schemas/evals/evidence-store-registry.schema.json
research_system/evals/coverage.py
research_system/evals/retention.py
research_system/evals/retention_authorizer.py
research_system/evals/executors/__init__.py
research_system/operations/models.py
research_system/command/models.py
research_system/command/service.py
research_system/command/reducers.py
research_system/projection/replay.py
research_system/store/receipts.py
tests/research_system/unit/test_coverage.py
tests/research_system/unit/test_executors.py
tests/research_system/unit/test_retention.py
tests/research_system/unit/test_replay.py
tests/research_system/unit/test_eval_schema_surface.py
tests/research_system/integration/test_release_coordinator.py
docs/plans/agentic-research-system/implementation/05-wp5-gate5-foundation-acceptance-plan.md
vault/04-Methods/Computational-Log.md
~~~

If implementation requires changing `p0-variant-matrix.yaml`, provider parity,
`research_system/evals/release.py`, release-event publication, live grader
policy, `DeleteEvidenceObject`, or `EvidenceDeletionPending`, stop Partial and
escalate.

## Obligation Register

| ID | Source | Obligation | Owner | Disposition |
|---|---|---|---|---|
| T1 | Gate 5 / 05-plan 4.4 | Materialize S-014/S-015/S-016 as exact executable packages | WP5.4 | Tasks 1-4 |
| T2 | D-G5-3 | Hold exact 40/15/132/0/calibrated/blocked values | Owner/WP5.4 | This plan; Task 5 |
| T3 | D-G5-2 / O15 | Defer deletion initiation and record restriction | Owner/WP5.4/WP5.6 | Global constraint; Task 5 |
| T4 | 05-plan section 7 | Extend deletion verification to registered backup/restore topology | WP5.4 | Task 2 |
| T5 | W6 S-014 / W8 19 | Prove store/project, chain, snapshot, endpoint, and artefacts before writer lease | WP5.4 | Task 2 |
| T6 | W6 S-015 / W2 8,11,19 | Reject revision-qualified cycles atomically; preserve authority; write rejected receipt | WP5.4 | Task 3 |
| T7 | W6 S-016 / W4-W7 | Outage waits/blocks; no sub-threshold fallback or acceptance | WP5.4 | Task 4 |
| T8 | D-G5-1(a) | H row stays blocking and restriction remains explicit | WP5.4/WP5.6 | Tasks 4-5 |
| T9 | W6 grader tuples | Exact D/T/O/P, D/T, D/T/O/H result-key closure | WP5.4 | Tasks 1 and 5 |
| T10 | Review discipline | Full gates, twice-run evidence, records, independent review | Worker/Manager | Task 5 |

## Research Assurance Requirements

- **Lanes:** Output/Provenance, Operations, Privacy, and Authority. No math,
  statistics, topology, representation, or paper-claim formula changes.
- **Sources:** Gate 5 WP5.4; 05-plan sections 4.4 and 7; W2 sections 8, 11,
  19, 21, and 26-27; W6 S-014/S-015/S-016; W8 sections 19-22;
  D-G5-1(a); D-G5-2; this D-G5-3 table.
- **Parameters/seeds:** none; all scenarios are deterministic and synthetic.
- **Contract disposition:** accepted designs define the properties. Schemas,
  typed records, fixture oracles, and negative tests are enforcement artifacts,
  not new `contracts/` research contracts.
- **Machine claims:** exact fixture/result closure; registered topology closure;
  derived deletion status; store/project/tail/snapshot hashes; endpoint
  ownership; artefact hash/availability; preflight before the real writer lock;
  revision-qualified lineage/scope/consumers; no lifecycle mutation plus one
  idempotent rejected receipt on a cycle; typed provider failure/incomplete
  receipt; no fallback dispatch; strict release blocked; exact 40/15/132; and
  twice-run equality.
- **Human questions:** Does restore verification establish the moved store
  instead of caller claims? Is every retained copy discoverable and registered?
  Is lineage derived from committed events? Does outage evidence prove preserved
  requirements rather than merely a failed fake call?
- **Provenance:** no paper result/cache. Durable evidence is committed
  packages/schemas/code/tests, exact CLI JSON, twice-run comparison, PR/review,
  obligation closure, and the top-of-page vault entry.
- **Partial:** self-certified restore, caller-narrowed topology, trusted caller
  lineage, unaudited rejection, partial lifecycle append, reduced-requirement
  fallback, fabricated H pass, invariant drift, or out-of-scope surface need.

## Task 1: Materialize exact corpus and coverage closure

**Files:** create the materializer/packages; modify coverage, executor registry,
and corpus tests.

- Add `RELEASE_TRANCHE_CASES = frozenset({"S-014", "S-015", "S-016"})` and
  `FOUNDATION_CASES = P0_CASES | RELEASE_TRANCHE_CASES`. Keep `P0_CASES` at 37
  and `P0_DEFERRED` unchanged.
- Coverage selects exact 40-case `FOUNDATION_CASES` at a new revision while
  `gate5_authorized` stays false.
- Retire the fixture-shaped `omitted_gate5` rows. Replace them with one exact
  D-G5-2 restriction: `capability_id: delete_evidence_object`,
  `status: capability_disabled`, `obligation: O15`, and
  `required_before: post_gate5_owner_decision`. The loader requires this row.
- Required graders are exact set equality: S-014 D/T/O/P; S-015 D/T; S-016
  D/T/O/H. Every row is critical and required.
- Use specification/synthetic provenance, R0 fixture retention, synthetic
  paths/identities, no credentials, and no transcripts.
- The materializer owns only S-014/S-015/S-016, supports arbitrary-CWD
  `--check`, and rejects missing, extra, stale, or divergent files.
- Each scenario has known-bad, known-good, trajectory, and at least one mutation
  removing the decisive guard; all mutations calibrate twice.

- [ ] Write failing tests for exact 40 selection, three packages, ten result
  keys, grader tuples, D-G5-2 restriction, unauthorized Gate 5, generator
  ownership/CWD, and P0/variant separation.
- [ ] Run red tests; collection/environment failure is not red evidence.

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_coverage.py tests/research_system/unit/test_executors.py tests/research_system/integration/test_gate5_release_tranche_fixture_corpus.py -q --no-cov
~~~

- [ ] Implement packages/coverage minimally; generate and check the shard.
- [ ] Commit `[PIPELINE] P00: materialize Gate 5 release tranche`.

## Task 2: Implement S-014 restore preflight and registered deletion topology

**Files:** create backup schema/module; modify registry schema/model/loader,
command-service writer authorization, tests, and S-014 executor.

**Backup/restore:**

- Add frozen `BackupReceipt` fields required by W8 section 19: receipt
  identity/revision/hash; project/store identity; canonical tail position/hash;
  accepted snapshot identity/hash, source position/hash, state hash, and replay
  range; schema/tool versions; encryption/redaction class; external artefact
  manifest hash, exact artefact ID/hash bindings, explicit availability status,
  and availability-observation evidence; creation/verification
  times/authority; destination class; and source endpoint scheme.
- Add typed `RestorePreflightResult` status `verified` or `diagnostic_only`, with
  exact failed predicates and hashes of receipt, ledger, snapshot, target
  endpoint-ownership evidence, artefact manifest/observations, and registry.
  Enforce the biconditional invariant: status is `verified` if and only if the
  failed-predicates collection is empty; status is `diagnostic_only` if and
  only if one or more predicates failed.
- `verify_restore_before_writer_lease(...)` independently loads the moved store,
  replays chain, verifies snapshot plus tail, checks target endpoint authority,
  and inspects each artefact hash/availability observation. It returns an
  authority-bound, content-hashed result; it does not accept a lease callback.
- The real `CommandService.submit` seam consumes and rechecks that result,
  including the status/failed-predicates biconditional, before entering
  `WriterLock`. A moved root requires a matching `verified` result
  bound to current root, project/store identity, tail, snapshot, endpoint,
  actor/authority, artefacts, and registry hash. Missing, diagnostic, stale,
  mismatched, or hash-invalid evidence fails before lock entry, allocation,
  object/event write, or receipt write. An unchanged store retains the existing
  strict identity/root path and cannot opt into weaker restore handling.
- Inspectors may be injected, but expected values come from the content-hashed,
  authority-bound receipt and committed store, never caller booleans. No
  cryptographic-signature claim is made.

**Deletion topology:**

- Add distinct `backup_roots` and `restore_roots` to `EvidenceStoreRegistry`
  and schema; preserve ordinary `replicas`. All resolved roots are unique and
  disjoint from primary/runtime/staging/temp.
- `checked_locations()` includes every primary/runtime/staging/temp, replica,
  backup, and restore root. Discovery compares against the union of registered
  copies; callers cannot omit a class.
- Deletion stays pending for present payload, inaccessible/reparse location,
  unregistered copy, missing inspection hash, canonical payload, or stale
  authority. `VerifyEvidenceDeletion` rechecks expanded closure before emitting
  unchanged `EvidenceDeletionVerified`.
- Add no delete function or pending-event emission.

- [ ] Write red negatives for wrong store/project, chain/tail, snapshot/schema,
  endpoint authority, inconsistent status/failed-predicate combinations,
  changed/absent artefact, stale/unsupported availability,
  unregistered backup/restore, inaccessible/reparse root, and narrowing. Each
  uses real `CommandService.submit` and proves writer lock not entered and no
  object/event/receipt/deletion event changed.
- [ ] Implement the minimal preflight/topology extension using existing replay,
  canonical hashes, store identity, and deletion authorizer.
- [ ] Make S-014 known-bad attempt writer authority before incomplete evidence;
  post-control verifies all predicates first. Bind exact D/T/O/P evidence.
- [ ] Run targeted tests and twice-run calibration.
- [ ] Commit `[PIPELINE] P00: verify restore and registered deletion topology`.

## Task 3: Implement S-015 atomic supersession-cycle rejection

**Files:** modify receipt model/schema/store, command service, task reducer,
replay, tests, and S-015 executor.

- Register only `SupersedeTask -> TaskSuperseded`. The command targets the
  nonterminal Task revision being superseded and carries exactly
  `replacement_task_id`, positive `replacement_task_revision`, non-empty
  `supersession_scope`, and exact `continuing_consumers` set. Replacement must
  be an existing type-compatible Task revision. A higher revision of the same
  Task ID is valid; only identical `(task_id, revision)` is a self-cycle.
- After acquiring the existing `WriterLock`, reload the committed snapshot and,
  inside that same critical section, derive and validate the revision-qualified
  graph before any event/object write. Reject an edge when the replacement
  reaches the source revision being superseded, when that source revision is
  already terminal, or when the replacement is missing/stale/incompatible.
  A terminal replacement node is still traversed for cycle detection; otherwise
  every back-edge into an existing supersession chain would be masked by a
  generic terminal check and the cycle branch would be unreachable.
- `TaskSuperseded` carries both revision-qualified references, scope,
  continuing consumers, envelope actor/authority, and lineage derived from
  committed graph plus the edge. Reject caller lineage and extra payload keys.
- Replay preserves per-revision history and resolves current replacement. A
  different-Task replacement leaves source revision terminal `superseded`; a
  same-Task higher revision supersedes only the source and makes the existing
  replacement revision current without erasing history. Scope/consumers and
  historical references remain resolvable. Superseded/accepted revisions do
  not reopen. Add no other lifecycle command.
- Within the same writer-lock critical section, a cycle rejection leaves ledger
  bytes/fingerprint/tail, Task object revisions, and lifecycle projection
  byte-identical. It writes exactly one operational `rejected` receipt with
  stable reason `supersession_cycle`, explanation, observed stream version, and
  unmet preconditions, and no event. Stable rejected-receipt lookup and creation
  also occur under that lock, so concurrent submissions cannot validate the same
  pre-cycle graph or create duplicate receipts. Retry of the same logical
  submission/payload returns the original receipt.
- Extend receipt model/schema/store only for W2 section 8.3 rejected fields and
  idempotency. Existing accepted/conflict receipts remain compatible.

- [ ] Build A@1 -> B@1 -> C@1 then submit C@1 -> A@1 while C@1, the source
  revision being superseded, remains nonterminal. Assert the exact
  `supersession_cycle` reason (not terminal-source rejection), unchanged
  lifecycle authority, and one stable rejected receipt; retry returns it. Add
  identical-node cycle, valid A@1 -> A@2, missing/stale/incompatible revision,
  caller-lineage, terminal-source, scope/consumer closure, and acyclic controls.
- [ ] Implement minimal graph, validator, event, reducer, and receipt support.
- [ ] Make S-015 known-bad mutate authority or accept a cycle; post-control
  rejects before append with exact D/T evidence.
- [ ] Run targeted tests and twice-run calibration.
- [ ] Commit `[PIPELINE] P00: reject supersession cycles atomically`.

## Task 4: Implement S-016 provider-outage blocking without fallback

**Files:** extend S-016 executor/integration tests and only the smallest existing
routing/adapter evidence seam. Do not alter thresholds or release acceptance.

- Use immutable R3 route request bindings for capability, risk, independence,
  context, authority, root/tool/sensitivity, policy, and evaluation revisions.
- Exercise (1) pre-dispatch evidence marking the required cross-family provider
  unavailable so eligibility-first routing yields typed failure/no
  `PreparedDispatch`, and (2) a previously eligible provider becoming
  unavailable at issue time so scripted fake transport yields an incomplete
  normalized `ProviderReceipt` with failure code and no output.
- Same-family, unevaluated, below-capability, or below-independence alternatives
  remain rejected; no winner may reduce a hard requirement and no command may
  issue to an ineligible fallback.
- Enforcement is the existing
  `run_p0_coverage -> build_release_decision -> decide_release` path. D/T/O pass;
  H is blocking `unable_to_grade`; strict release is `blocked`. The command
  ledger has no provider-dispatch or Task-acceptance event. The executor may
  describe wait/outage trace but cannot author terminal authority. No accepted
  or exception-limited decision is permitted.

- [ ] Assert exact rejection codes, no prepared/issued fallback, normalized
  outage receipt, no output, unchanged bindings, no canonical dispatch/accept
  event, strict release blocked, and H unable through the named path.
- [ ] Wire only missing production evidence; reuse routing, adapter
  normalization, and strict release. Add no fallback policy.
- [ ] Run targeted tests and twice-run calibration.
- [ ] Commit `[PIPELINE] P00: block R3 provider-outage fallback`.

## Task 5: Integrated acceptance and handoff

- [ ] Run every materializer in `--check`; no generated diff.
- [ ] Run ruff and all deterministic tests.

~~~powershell
uv run --no-sync ruff check research_system tools/ars tests/research_system
uv run --no-sync pytest tests/research_system -q --no-cov
~~~

- [ ] Run calibration and coverage twice, saving JSON outside tracked result
  roots and comparing canonical projections.

~~~powershell
uv run --no-sync python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
~~~

  Both runs report exact 40/15/0/calibrated and blocked/132; any drift stops.
- [ ] Negative controls: removing an S-014 topology root, allowing an S-015
  cycle, or routing an S-016 fallback changes its oracle to fail/fixture_error;
  restoring the guard restores the expected decision without oracle change.
- [ ] Audit no change to variant matrix, parity, release event, live policy,
  deletion command/pending event, research results, or unrelated files.
- [ ] Close T1-T10 with actual evidence. Add a top-of-page vault `[PIPELINE]`
  entry with counts, D-G5-2/O15 restriction, commands/tests, branch/commits, and
  limitations. Do not write a Gate 5 acceptance decision.
- [ ] Commit `[PIPELINE] P00: close Gate 5 release-tranche obligations`.
- [ ] Push and open a ready PR. Report exact commits, tests/timing, twice-run
  hashes, invariant JSON, paths, restrictions, and Partial items. Do not merge.

## Acceptance Criteria

1. S-014/S-015/S-016 are valid deterministic packages selected once with exact
   D/T/O/P, D/T, and D/T/O/H closure.
2. Restore preflight proves store/project, chain/tail, snapshot/replay, endpoint,
   schema, and artefact availability; the real command-service seam rechecks it
   before entering the writer lock.
3. Deletion checks every registered primary/runtime/staging/temp, replica,
   backup, and restore location and blocks on uncertainty/unregistered copies.
4. `DeleteEvidenceObject` and pending-event emission remain absent; D-G5-2 and
   O15-open restriction are explicit.
5. Supersession resolves revision-qualified compatible nodes, preserves
   scope/consumers/history, derives lineage, accepts different-Task and
   same-Task higher-revision acyclic edges, and rejects cycles with no lifecycle
   mutation plus one idempotent W2 rejected receipt.
6. S-016 proves no eligible route and issue-time outage without lowering a hard
   requirement, issuing fallback, or accepting the Task.
7. Exact 40/15/0/calibrated/132/blocked and twice-run equality hold while
   `gate5_authorized` remains false.
8. Ruff/full suite/materializer checks pass; no forbidden or unrelated path
   changes.
9. Register/vault are evidence-backed, PR head stable, CodeRabbit concluded,
   and Manager independent review has no unresolved critical/high finding.

## Stop Conditions

Stop Partial if exact counts require grader/oracle/threshold weakening; S-014
requires deletion initiation or a copy cannot be registered; restore depends on
caller booleans/CWD/self-validation; S-015 requires wider lifecycle redesign or
trusted caller lineage; S-016 needs invented independence, relaxed R3, or H
acceptance; WP5.2/WP5.3/live credentials become necessary; twice-run evidence
differs beyond declared noncanonical fields; or any test/invariant/review/
obligation remains unresolved.

Approval phrase: **Approved D-G5-3 / WP5.4 plan**. Approval authorizes only this
bounded implementation. It does not accept Gate 5, close O15, authorize live
providers, or authorize merge without review.
