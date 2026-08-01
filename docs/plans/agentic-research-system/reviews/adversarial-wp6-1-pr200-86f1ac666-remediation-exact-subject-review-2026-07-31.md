# WP6.1 PR #200 remediation exact-subject semantic review

**Date:** 2026-07-31
**Verdict:** `accept_exact_subject`
**Findings:** 0 Critical, 0 Major, 0 Minor
**Immutable reviewed subject:** `86f1ac6668bbe1aab2b499d3d8b27dcd50f6b097`
**Required base ancestor:** `919a11f0045f810164ea028b29bd2c3b80781619`
**Original implementation subject:** `96e764868eb7b52b4a4543ca3ff0152ac33265fa`
**Prior exact-subject review commit:** `ae817c65344877235709a5300c638a7ba9a4c42f`
**Reviewed branch:** `codex/wp61-scope-task-revisions`
**Remote binding:** `origin/codex/wp61-scope-task-revisions` resolved to the reviewed subject

## 1. Executive verdict

The exact remediation subject closes the prior Major finding. ScopeDefinition
amendments are now derived from committed typed membership rather than accepted
from payload shape alone. Submission and replay reject:

- a non-empty member change whose materialized membership is identical;
- removal or replacement under a `member_kind` different from the committed
  member kind; and
- removal of an absent member.

The same mechanism continues to accept a real disposition change, a typed
addition, and a typed removal. The materialized definition changes only
`revision` and `members`; it retains the definition's original
`amendment_authority` instead of projecting the amendment event's authority or
other amendment-only fields. The immutable amendment object, event payload,
`last_amendment`, and revision-history amendment evidence retain the exact
amendment authority and rationale.

The remediation also keeps supersession membership derived from that committed
revision chain. Exact command/event provenance, immutable object/history
bindings, idempotent exact retry, rejection without event/object side effects,
pre-cutover generic history, and the other five activated WP6.1 rows remain
closed. The owner-accepted 87 command and 86 event schema trees are unchanged at
their accepted Git tree identities.

Direct post-genesis lifecycle-grant enforcement remains explicitly assigned to
WP6.3. It is not a finding in this subject. This verdict is not owner
acceptance, merge authority, or Gate 6 acceptance.

## 2. Exact identity, scope, and authority

The review began and ended with:

- cwd and Git top-level resolving to
  `C:\Users\steph\.codex\worktrees\6f50\TDL`;
- symbolic branch `codex/wp61-scope-task-revisions`;
- local `HEAD` and the remote branch both resolving to
  `86f1ac6668bbe1aab2b499d3d8b27dcd50f6b097`;
- required base `919a11f0045f810164ea028b29bd2c3b80781619`
  confirmed as an ancestor;
- the remediation subject's sole parent resolving to the prior review commit
  `ae817c65344877235709a5300c638a7ba9a4c42f`; and
- only the predeclared Repowise setup changes in `.claude/CLAUDE.md` and
  `.repowise-workspace.yaml` present in the worktree. They were not touched,
  staged, reverted, or used as review evidence.

The required-base-to-subject range contains the original 16-path implementation
and its prior review record. The remediation commit itself changes exactly:

1. `research_system/command/lifecycle.py`;
2. `research_system/command/reducers.py`;
3. `research_system/command/service.py`; and
4. `tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py`.

The governing boundary was reconstructed directly from:

- handoff 32 sections 0, 5A0, 6, and 9;
- implementation plans 06 sections 3, 6, 7, and 9; 06g sections 1-7; and
  06a sections 2-6;
- the accepted WP6.1 owner-source catalogue and schema-identity manifest;
- the stage-2 D-G6-3 owner acceptance record;
- W2 immutable-version and ScopeDefinition rules; and
- the prior exact-subject review committed immediately before remediation.

The owner acceptance record pins exactly 87 command schemas under Git tree
`9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` and 86 event schemas under Git
tree `154ffc4bdde82fe903718734687e7a62797b1f69`, with an explicit
`exact_bytes_only` boundary. Handoff 32 preserves those generated schemas while
requiring complete vertical activation: binding, producer, reducer, projection,
replay, and negative cases together.

## 3. Prior Major finding closure

| Required remediation mechanism | Exact implementation evidence | Adversarial disposition |
|---|---|---|
| Derive current typed membership from committed exact history | `CommandService._scope_definition` loads the immutable revision-1 object, checks it against committed creation evidence, loads each immutable amendment object, checks it against its committed event payload, and sequentially materializes membership (`service.py`, lines 839-951). | Closed. Expected membership is not copied from the new candidate. Object/event disagreement raises `IntegrityError`. |
| Reject non-empty identical member change | `materialize_scope_member_changes` compares the candidate materialized list with the committed original and raises on equality (`lifecycle.py`, lines 87-131). Submission maps that failure to a rejected receipt; replay raises before projection (`service.py`, lines 1182-1220; `reducers.py`, lines 388-461). | Closed at both seams. The focused three-case durable test and an independent exact-store probe passed. |
| Reject wrong-kind removal and replacement | The helper resolves an existing member by ID, compares the committed kind before either removal or replacement, and raises on mismatch (`lifecycle.py`, lines 105-111). | Closed. The durable suite covers removal; an independent probe additionally proved wrong-kind replacement rejects at submission with no event/object change and rejects during replay. |
| Reject absent-member removal | An unresolved member ID with `removed_by_amendment` raises instead of silently doing nothing (`lifecycle.py`, lines 101-104). | Closed at submission and replay. |
| Preserve valid changes | Existing typed members may change `required_disposition`; new typed members append; existing correctly typed members may be removed (`lifecycle.py`, lines 96-126). | Closed. Independent end-to-end probes accepted a disposition change, addition, and removal idempotently and replayed the exact resulting membership. |
| Do not project amendment-only fields | `_materialize_scope_definition` spreads the prior definition and changes only `revision` and `members`; it no longer copies amendment `amendment_authority` (`reducers.py`, lines 388-401). | Closed. The definition retained the original creation authority and contained none of `rationale`, `effective_boundary`, `changed_fields`, or `member_changes`. |
| Retain amendment evidence | The immutable revision object and event payload remain the complete amendment payload; reducer state retains it in `last_amendment` and `revision_history[new_revision].amendment` (`service.py`, lines 1657-1665; `reducers.py`, lines 452-461). | Closed. Exact authority values for revisions 2-4 survived replay. |
| Apply the same semantic rule during replay | `reduce_scope` calls the shared pure helper after exact envelope, revision, declared-field, non-empty, and uniqueness checks (`reducers.py`, lines 402-461). Replay routes every exact Scope lifecycle event through that reducer (`projection/replay.py`, lines 246-255). | Closed. Directly appended invalid exact events failed replay for all three prescribed cases plus wrong-kind replacement. |
| Preserve accepted schema bytes | The remediation has no schema or contract path. Git-tree comparison pins the complete command/event subtrees. | Closed. Counts and tree IDs exactly match D-G6-3. |

The helper is shared code, but the evidence is not a producer-generated expected
value compared with itself. Submission derives its source from committed
immutable objects joined to exact event evidence; replay derives state from the
ledger. The negative controls supply independently selected counterexamples,
and the positive probes supply explicit expected memberships.

## 4. Six activated WP6.1 rows

| Accepted row | Exact pair | Disposition at `86f1ac6` |
|---|---|---|
| `scope.create` | `CreateScopeDefinition -> ScopeDefinitionCreated` | Closed: exact active binding, project/subject binding, unique typed membership, immutable object, event provenance, projection, replay, and exact retry remain green. |
| `scope.amend_revision` | `AmendScopeDefinition -> ScopeDefinitionAmended` | **Closed by this remediation:** committed typed-membership derivation, three required submission/replay negatives, valid disposition/add/remove flows, field-projection separation, immutable amendment evidence, and no-side-effect rejection all passed. |
| `scope.supersede` | `SupersedeScopeDefinition -> ScopeDefinitionSuperseded` | Closed: the exact current membership is reconstructed through all amendments. A disposition for a removed member rejects; the exact remaining member set accepts and replays. |
| `task.create` | `CreateTask -> TaskCreated` | Closed: exact schema binding, immutable rich definition, project/content-hash binding, event/object equality, exact retry, and generic-history separation remain green. |
| `task.amend_revision` | `AmendTask -> TaskAmended` | Closed: current consecutive revision, immutable source/replacement binding, exact typed-field delta, replay, and no-op rejection remain green. |
| `task.supersede` | `SupersedeTask -> TaskSuperseded` | Closed: compatible current replacement, cycle/terminal controls, disposition evidence, exact/generic provenance separation, replay, and immutable history remain green. |

The remediation helper's only runtime callers are:

- submission reconstruction and validation in `CommandService`;
- projection/replay materialization in `reduce_scope`; and
- supersession membership reconstruction through
  `CommandService._scope_members`.

The focused regression therefore exercised the changed behavior and its complete
demonstrated caller surface without treating the entire package as the focused
unit.

## 5. Consistency and enforcement matrix

| Invariant | Enforcement point | Decisive evidence |
|---|---|---|
| Catalogue presence is not activation | Explicit `_RUNTIME_BINDINGS` contains the six pairs; an adjacent inactive pair remains inert (`schema_registry.py`, lines 77-137). | Runtime-binding unit test passed. |
| Exact command identity reaches every event | Active command validation selects `(schema_id, version, raw-byte SHA-256)`; `_build_event` records all three; replay resolves the recorded SHA before projection (`service.py`, lines 240-263 and 1727-1750; `projection/replay.py`, lines 420-466). | All 31 lifecycle cases and propagation seams passed. |
| Immutable Scope revision evidence binds the ledger | `_scope_revision_object` rejects an object different from committed payload; `_scope_definition` joins every revision object to event evidence (`service.py`, lines 839-942). | Focused committed-object test and independent multi-revision probe passed. |
| Amendments are real typed membership deltas | Shared helper compares against committed ID/kind/disposition records (`lifecycle.py`, lines 87-131). | Three prescribed negatives plus wrong-kind replacement, valid add/remove/disposition probes passed. |
| Definition fields cannot drift through an undeclared amendment | Accepted amendment field set is exactly `{"members"}`; reducer changes only revision and members (`service.py`, lines 1166-1181; `reducers.py`, lines 388-401). | Projection-field separation assertions passed. |
| Amendment authority remains evidence, not a silent definition mutation | Exact payload is written as the immutable amendment object/event and retained in history; materialized definition retains its original field (`service.py`, lines 1657-1665; `reducers.py`, lines 452-461). | Exact authority values survived object reads and replay. |
| Supersession dispositions equal current membership | `_scope_members` derives from the entire committed amendment chain; submitted disposition ID/kind map must equal it (`service.py`, lines 945-951 and 1239-1268). | Removed-member extra disposition rejected; exact remaining set accepted. |
| Rejection has no event/object side effects | Semantic checks run before `_build_event`; object writes occur only after preparation succeeds (`service.py`, lines 375-430 and 1640-1668). | Durable and independent probes compared event tails and object bytes. |
| Exact retry is schema- and payload-bound | Committed match joins actor, grant, command type, idempotency key, schema ID/version/SHA, payload hash, stream, and version (`service.py`, lines 1586-1638). | Every valid lifecycle helper submitted twice with one event; authority-store exact-retry seam passed. |
| Generic history remains readable without rich reinterpretation | Generic events bypass exact lifecycle bindings; recorded schema identity selects rich versus generic revision evidence. | Pre-cutover generic-history seam and rich/generic incompatibility test passed. |
| Accepted generated bytes remain frozen | D-G6-3 tree identities and counts are direct Git objects, independent of checkout EOL. | Command tree `9ea0aec...` with 87 files and event tree `154ffc4...` with 86 files matched exactly. |

## 6. Findings

No Critical, Major, or Minor findings remain on the immutable reviewed subject.

The full required-base-to-subject `git diff --check` reports only the Markdown
two-space hard-break syntax on six metadata lines in the already committed
prior review record. The remediation range
`ae817c65344877235709a5300c638a7ba9a4c42f..86f1ac6668bbe1aab2b499d3d8b27dcd50f6b097`
passes `git diff --check`. The prior report formatting does not change runtime,
authority, evidence, or this semantic verdict and is not elevated into a
finding.

## 7. Verification evidence

### Git and protected-byte checks

- cwd, top-level, symbolic branch, local head, remote head, required-base
  ancestry, sole parent, status, and changed paths: passed.
- Remediation-range `git diff --check`: passed.
- Frozen generated command schemas: 87 tracked files; head tree
  `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`, equal to the owner-accepted
  tree and to the required base.
- Frozen generated event schemas: 86 tracked files; head tree
  `154ffc4bdde82fe903718734687e7a62797b1f69`, equal to the owner-accepted
  tree and to the required base.
- Protected schema-identity manifest, owner-source catalogue, and stage-1
  acceptance record retain owner-pinned Git blobs
  `54a2938d34cea9c4a88d23585ce012a86bc3209d`,
  `1adc66921ee9c90d8786ff173748150922f1035e`, and
  `42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83`.

The accepted record's historical `core` tree also contained the then-current
generic core envelope. The current whole-core tree legitimately differs because
the already accepted A0 work changed the generic event envelope and added later
non-generated core schemas. The two generated 173-file subtrees named by
D-G6-3 remain exact.

### Focused tests

The test environment used:

- `PYTHONDONTWRITEBYTECODE=1`;
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
- the pre-existing interpreter
  `C:\Users\steph\TDL\.venv\Scripts\python.exe`;
- `-o addopts=` to suppress repository coverage addopts; and
  `-p no:cacheprovider`.

Command:

```text
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q -o addopts= -p no:cacheprovider tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py
```

Result: **31 passed in 36.63s**.

Command:

```text
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q -o addopts= -p no:cacheprovider tests/research_system/unit/test_schema_registry.py::test_runtime_bindings_activate_first_scope_task_slice_and_t2_verticals tests/research_system/integration/test_authority_grant_source.py::test_authority_store_exact_retry_replays_activated_lifecycle_history tests/research_system/integration/test_gate5_release_tranche.py::test_restore_preflight_replays_exact_lifecycle_history tests/research_system/integration/test_gate5_release_tranche.py::test_pre_cutover_generic_task_history_remains_replayable_and_resolvable
```

Result: **4 passed in 52.18s**.

An initial collection-only invocation omitted `-o addopts=` while plugin
autoload was disabled. Pytest correctly stopped before collection because the
project's configured `--cov` arguments then had no registered plugin. No test
ran. The corrected commands above disabled those addopts explicitly.

### Independent exact-store probes

Two read-only review probes used temporary control stores outside the repository:

1. **Membership and evidence probe:** accepted a real disposition change,
   addition, and removal with exact retry; preserved each immutable amendment
   payload; projected only the declared definition delta; retained amendment
   authorities in event/revision evidence; rejected wrong-kind replacement
   without event/object change; and rejected the directly appended invalid event
   during replay. Result: `independent_scope_probe: PASS`.
2. **Supersession membership probe:** reconstructed membership after addition
   and removal, rejected a supersession disposition set that reintroduced the
   removed member, accepted the exact remaining set, replayed `superseded`, and
   preserved the revision-1 object. Result:
   `independent_supersession_membership_probe: PASS`.

Repository status after all tests and probes remained exactly the two
pre-existing Repowise setup changes. Existing ignored `.coverage` and
`.pytest_cache` timestamps predated this review and were unchanged.

CodeRabbit was not requested, triggered, polled, scheduled, or awaited.

## 8. Decision audit and residual risk

| Decision or boundary | Disposition |
|---|---|
| Prior M-1 prescribed mechanism | Keep; fully implemented and independently exercised at submission and replay. |
| Six-row WP6.1 activation boundary | Keep; no additional row was activated by the remediation. |
| D-G6-3 exact generated bytes | Keep; all 173 generated files remain pinned at the two accepted trees. |
| Immutable object and event history | Keep; amendment objects remain exact evidence while materialized state is derived. |
| Direct post-genesis lifecycle grants | Defer to WP6.3 exactly as instructed; no acceptance bypass is inferred. |
| Owner acceptance / PR merge / Gate 6 | Still owner-reserved; this review does not authorize any of them. |

Residual risk is bounded and explicit:

- submission and replay intentionally share one pure membership materializer,
  so future changes to that helper must retain direct counterexample tests at
  both real seams;
- a future ScopeDefinition amendment field requires a separately declared
  `changed_fields` contract and materialization rule rather than being copied
  through the payload;
- the deferred WP6.3 grant-issuance delivery must bind the six command types and
  exact project/subject scopes before direct lifecycle authority can be claimed;
  and
- no full repository suite was run. The complete changed-behavior module plus
  the exact registry, authority-store retry, restore replay, and legacy-history
  seams were the smallest decisive regression set for the demonstrated caller
  surface. No narrower check failed and no broader-suite trigger fired.

## 9. Practicality and revision plan

The remediation is proportionate: one pure typed-membership function is called
from submission reconstruction and replay materialization, while supersession
consumes the same derived definition. It introduces no schema regeneration,
migration, new authority, or alternate writer.

Immediate corrections: none.

Owner decisions: separately accept or reject this exact subject under the
existing review-then-merge process.

Later-work dependency: implement and independently review the WP6.3
post-genesis scoped grant path; do not treat this accepted exact subject as that
authority implementation.

## 10. Final decision

`accept_exact_subject`
