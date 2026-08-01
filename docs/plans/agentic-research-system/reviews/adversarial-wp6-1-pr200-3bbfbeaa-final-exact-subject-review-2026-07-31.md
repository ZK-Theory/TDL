# WP6.1 PR #200 final exact-subject semantic review

**Date:** 2026-07-31
**Verdict:** `rework_required`
**Findings:** 1 Critical, 0 Major, 1 Minor
**Immutable reviewed subject:** `3bbfbeaa87173195e3bfc0c2e6c31f6c40ba5869`
**Required base ancestor:** `919a11f0045f810164ea028b29bd2c3b80781619`
**Subject parent / prior durable acceptance record:** `4317c59fdb908f38a547c069639771edd01ba7c9`
**Accepted remediation ancestor:** `86f1ac6668bbe1aab2b499d3d8b27dcd50f6b097`
**Reviewed branch:** `codex/wp61-scope-task-revisions`
**Remote binding:** both the remote branch and live PR #200 head resolved to the reviewed subject

## 1. Executive verdict

The final runtime changes are not acceptable as an exact subject.
`EventLedger.append` now matches replay's registered-schema precedence by
validating a full recorded event schema before consulting its payload sibling,
but it does so through catalogue presence rather than activation. The inactive
guard exempts every identity that has a `/payload` sibling. Consequently, adding
an unbound full schema for a payload-backed authority event silently changes
append validation from the active payload contract to the unbound full
contract.

An independent runtime-registry probe demonstrated the authority consequence.
With the real payload-only `AuthorityRootInitialized` schema, an empty payload
was rejected and zero batches were written. Adding one unbound permissive full
schema for the same event identity caused the identical invalid event to append
successfully even though `is_active(...)` remained false. One batch was
persisted, and authoritative replay then rejected that batch's empty authority
payload. Catalogue materialization can therefore activate a full authority
schema, bypass the accepted payload contract, and leave unreplayable authority
history. This is Critical.

The other bounded changes also behave as intended:

- malformed legacy `TaskCreated` payloads now fail the revision-history helper
  with `IntegrityError`, while mapping-shaped pre-cutover revision-1 history
  remains readable;
- `ControlPlaneState.stream_states` accurately names its mixed Task and
  ScopeDefinition map, and no checked-in consumer of the former field was
  missed;
- generic ledger tests now select `ars://core/event` explicitly instead of
  accidentally selecting the strict materialized `TaskCreated` schema; and
- the six activated WP6.1 rows, the accepted Scope semantic-delta remediation,
  replay/restore/authority retry, provenance, exact retry/idempotency,
  immutable evidence, and all 173 owner-accepted schema files remain correct.

Separately, one requested documentation cleanup is not exact. The public cross-module
`validate_exact_lifecycle_envelope` helper documents only `ValueError`, but its
canonical payload-hash path also propagates `TypeError`. The authoritative
replay caller explicitly handles both exceptions, and an independent direct
probe reproduced the undocumented one. Under the repository's public-API rule
that raised exceptions be documented, this is one Minor factual documentation
defect.

Direct post-genesis lifecycle grant enforcement remains assigned to WP6.3 and
is not a finding. This review is not owner acceptance, merge authority, or Gate
6 acceptance.

## 2. Exact identity, scope, and protected state

The review verified:

- cwd and Git top-level resolve to
  `C:\Users\steph\.codex\worktrees\6f50\TDL`;
- the symbolic branch is `codex/wp61-scope-task-revisions`;
- local `HEAD`, `origin/codex/wp61-scope-task-revisions`, the live remote branch,
  and `refs/pull/200/head` all resolve to
  `3bbfbeaa87173195e3bfc0c2e6c31f6c40ba5869`;
- required base `919a11f0045f810164ea028b29bd2c3b80781619`
  is the exact merge base and an ancestor;
- the subject's sole parent is
  `4317c59fdb908f38a547c069639771edd01ba7c9`, and accepted remediation
  `86f1ac6668bbe1aab2b499d3d8b27dcd50f6b097` remains in its ancestry; and
- the only pre-existing worktree changes are Repowise setup state in
  `.claude/CLAUDE.md` and `.repowise-workspace.yaml`. They were not touched,
  staged, reverted, or used as evidence.

The final subject changes exactly six paths relative to its parent:

1. `research_system/command/lifecycle.py`;
2. `research_system/command/reducers.py`;
3. `research_system/command/service.py`;
4. `research_system/store/ledger.py`;
5. `tests/research_system/unit/test_command_service.py`; and
6. `tests/research_system/unit/test_store.py`.

The owner-accepted generated subtrees remain exact:

- 87 command schemas at Git tree
  `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`; and
- 86 event schemas at Git tree
  `154ffc4bdde82fe903718734687e7a62797b1f69`.

Both tree identities equal the required base. The protected schema-identity,
owner-source, and stage-1 acceptance records retain their pinned blobs
`54a2938d34cea9c4a88d23585ce012a86bc3209d`,
`1adc66921ee9c90d8786ff173748150922f1035e`, and
`42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83`.

## 3. Findings

### C-1 — Critical — an unbound full schema can shadow an active authority payload contract and corrupt the ledger

1. **Claim.** The new full-schema precedence lets catalogue presence act as
   runtime authority when the recorded event identity also has a payload
   sibling. An unbound full schema can replace the payload contract without an
   active event binding.

2. **Evidence.**

   - `SchemaRegistry.contains` proves identifier presence only, `validate`
     applies any registered schema, and only `validate_active` requires an
     explicit activation (`research_system/schema_registry.py`, lines 275-313
     and 328-375).
   - Append computes `payload_backed_event` from presence of
     `<event-schema-id>/payload`. The inactive guard then exempts that event
     whenever the sibling exists, regardless of whether a full schema also
     exists or is active (`research_system/store/ledger.py`, lines 381-405).
   - The changed branch next calls ordinary `validate` on the full schema
     whenever `contains(event_schema)` is true and consults the payload sibling
     only when the full schema is absent (`ledger.py`, lines 254-271).
   - The bundled catalogue currently has no identity with both a full event
     schema and a payload sibling. Its authority events are payload-only, so a
     default-checkout test cannot expose this transition.
   - Independent probe, using a temporary copy of the real runtime schema tree:
     the real `AuthorityRootInitialized/payload` schema rejected `{}` and wrote
     zero batches; adding an unbound full `AuthorityRootInitialized` schema
     made the identical event append one batch while
     `is_active("ars://core/event/AuthorityRootInitialized", "1.0.0")` remained
     false.
   - Authoritative replay rejects the persisted empty payload because authority
     root fields and genesis bindings must be exact
     (`research_system/projection/replay.py`, lines 106-146). Append can
     therefore create history that its own recovery path cannot replay.
   - The new unit test uses an inert `SchemaRegistry` and a synthetic permissive
     core envelope. It proves full-before-payload precedence and atomic
     rejection, but never exercises the runtime activation guard
     (`tests/research_system/unit/test_store.py`, lines 348-406).

3. **Concrete failure scenario.** A future reviewed or proposed full authority
   event schema is materialized alongside the existing strict payload sibling
   but is not activated. A raw authority append records that event identity
   with an invalid payload admitted by the unbound full schema. The ledger
   publishes the batch. Restart, restore, or authority resolution then rejects
   the persisted event, blocking deterministic recovery.

4. **Impact.** Catalogue materialization can bypass an accepted authority
   payload contract, persist invalid authority evidence, and create
   unreplayable history. This crosses the activation and authority trust
   boundaries and meets the Critical rubric.

5. **Recommended disposition.** Fix before merge and obtain a fresh independent
   review of the new exact subject. Do not treat full-schema presence as
   activation, and do not weaken the existing authority payload contracts.

6. **Required interface change.** Make validation-target selection
   activation-aware:

   - an active event binding selects its exact full schema through
     `validate_active`;
   - an unbound runtime event with an accepted payload sibling continues to
     validate that payload sibling even if an inert full schema is present;
   - an unbound runtime event with only a full schema remains rejected as
     inactive; and
   - inert catalogue-only test registries may retain explicit full-schema
     validation without conferring runtime authority.

   Apply the same authority-aware selection during replay rather than relying
   on later semantic reducers to repair a schema-authority error. Add a durable
   runtime-registry negative using the real strict
   `AuthorityRootInitialized/payload` sibling plus an unbound permissive full
   sibling: both append and replay must reject, `is_active` must remain false,
   and batch count must remain zero. Include a versioned sibling variant so an
   arbitrary registered version cannot shadow the accepted payload contract.

7. **Affected decisions and contracts.** A0 explicit schema activation; D-G6-3
   `exact_bytes_only`; authority genesis/revocation schema binding; append,
   replay, restore, and exact-retry integrity.

8. **Affected work packages.** WP6.1 runtime schema activation and the WP6.3
   authority/control-store dependency. This finding does not require changing
   the 173 accepted schema bytes.

### m-1 — Minor — lifecycle provenance validator omits an exception it actually raises

1. **Claim.** `validate_exact_lifecycle_envelope` does not fully document its
   actual exception contract.

2. **Evidence.**

   - Its Google-style `Raises` section names only `ValueError`
     (`research_system/command/lifecycle.py`, lines 43-58).
   - The helper hashes `canonical_bytes(payload)` without catching its
     exceptions (`lifecycle.py`, lines 63-72).
   - P0 canonical validation raises `TypeError` for unsupported in-memory values
     (`research_system/canonical.py`, lines 10-29).
   - The authoritative replay wrapper already catches both `TypeError` and
     `ValueError` from this helper and normalizes either to `IntegrityError`
     (`research_system/projection/replay.py`, lines 34-41).
   - `CONTRIBUTING.md` defines functions used by other modules as public and
     requires their raised exceptions to be documented in Google-style
     docstrings (`CONTRIBUTING.md`, lines 99-119).
   - A direct exact-event probe with an unsupported payload value produced
     `TypeError: unsupported P0 canonical JSON value: object`.

3. **Concrete failure scenario.** A direct in-memory caller validates an exact
   lifecycle envelope whose payload contains a value outside P0 canonical JSON.
   The caller prepares for the documented `ValueError`, but receives
   `TypeError`. Replay is safe because it already handles both; another direct
   caller relying on the public helper's documentation need not be.

4. **Impact.** This does not corrupt ledger bytes or weaken runtime validation.
   It is a local but factual public-contract error that can produce incorrect
   exception handling in a future cross-module caller.

5. **Recommended disposition.** Fix the docstring on a new exact subject and
   obtain a focused fresh exact-subject review. Do not alter runtime behavior or
   accepted schema bytes for this finding.

6. **Exact proposed text.** Add this entry to the existing `Raises` section:

   ```text
   TypeError: If the payload contains a value unsupported by P0 canonical JSON.
   ```

   An alternative behavior change that normalizes `TypeError` inside the helper
   would be wider than necessary and is not recommended for this bounded
   cleanup.

7. **Affected decisions and contracts.** Repository public-API/docstring
   convention and the PR #200 final lifecycle-helper cleanup. No owner-approved
   lifecycle, authority, schema, or evidence decision changes.

8. **Affected work packages.** WP6.1 first lifecycle slice documentation only.
   WP6.3 grant issuance and later WP6.1 rows are unaffected.

## 4. Final-remediation claim matrix

| Required claim | Direct enforcement evidence | Disposition |
|---|---|---|
| Registered full event schema precedes payload sibling | Append validates core, then an active schema if bound, otherwise the registered full schema, falling back to the payload sibling only when the full schema is absent (`store/ledger.py`, lines 227-271). Replay uses the same presence-based order (`projection/replay.py`, lines 444-472). | **Fail — C-1.** The order mirrors replay but is not activation-aware. |
| Active/core/release/T2 behavior remains distinct | T2 and release return through their existing exact full-schema branches; active events still use `validate_active`; generic events still validate the core envelope. | Pass |
| Inactive materialized schemas remain inert | The guard rejects an unbound full-only `DispatchClaimed`, but exempts any identity with a payload sibling (`store/ledger.py`, lines 382-405). | **Fail — C-1.** An unbound full authority schema changed rejection into one persisted batch. |
| Payload-only authority events remain valid | Current authority events work while only `/payload` siblings exist, and genesis/retry/revocation tests passed. | **Fail under catalogue extension — C-1.** An inert full sibling silently shadows the payload contract. |
| Invalid full-schema append is atomic | Validation normally precedes temporary-file creation and publication (`store/ledger.py`, lines 406-437), and the new unit rejection wrote zero batches. | **Fail at the authority collision — C-1.** The invalid payload is accepted and published instead of rejected. |
| Legacy non-mapping Task payload fails closed | `_revision_graph` raises `IntegrityError` before `.get` access; null, list, and scalar cases passed (`command/service.py`, lines 694-705). | Pass |
| Valid generic revision-1 history remains compatible | Mapping-shaped generic history still defaults missing `revision` to 1, and the named Gate 5 legacy-history seam passed. | Pass |
| Mixed Task/Scope state is named accurately | Both lifecycle branches populate `stream_states`; lineage walkers discriminate by `task_id` versus `scope_definition_id` (`command/reducers.py`, lines 45-86 and 506-536). Exact search found no `.task_states` consumer. | Pass |
| Lifecycle helper documentation matches behavior | Four helper docstrings accurately describe their normal behavior; the provenance validator omits its propagated `TypeError`. | **Fail — m-1** |
| Generic store fixtures choose the generic identity | The affected store tests now pass `schema_id: ars://core/event`; strict exact `TaskCreated` identity is no longer selected by the ledger default. | Pass |

## 5. Six activated WP6.1 rows

| Accepted row | Exact pair | Final disposition at `3bbfbea` |
|---|---|---|
| `scope.create` | `CreateScopeDefinition -> ScopeDefinitionCreated` | Runtime closed: exact active binding, project/subject identity, unique membership, immutable object, event provenance, projection, replay, and retry passed. |
| `scope.amend_revision` | `AmendScopeDefinition -> ScopeDefinitionAmended` | Runtime closed: the accepted `86f1ac6` remediation still derives committed typed membership and rejects identical, absent, and wrong-kind changes at submission and replay. |
| `scope.supersede` | `SupersedeScopeDefinition -> ScopeDefinitionSuperseded` | Runtime closed: current replacement, terminal/cycle, exact member-disposition, history, and replay controls passed. |
| `task.create` | `CreateTask -> TaskCreated` | Runtime closed: exact schema identity, rich definition/project/content hash, immutable object/event equality, generic-history separation, and retry passed. |
| `task.amend_revision` | `AmendTask -> TaskAmended` | Runtime closed: current consecutive revision, immutable source/replacement, exact typed-field delta, replay, and no-op rejection passed. |
| `task.supersede` | `SupersedeTask -> TaskSuperseded` | Runtime closed: compatible current replacement, cycle/terminal/disposition controls, exact/generic provenance, replay, and history passed. |

The one Minor finding concerns the helper's written exception contract. It does
not reopen any runtime row or the prior Scope semantic-delta closure.

## 6. Consistency and enforcement matrix

| Invariant | Enforcement point | Decisive evidence |
|---|---|---|
| Catalogue presence is not runtime activation | Explicit versioned `_RUNTIME_BINDINGS` plus append's inactive-event guard | **Fail — C-1.** Payload-sibling exemption plus `contains(full)` bypasses the binding |
| Recorded event identity selects an authorized contract | Active binding or accepted payload sibling, with versioned identity | **Fail — C-1.** Presence-based full schema shadows the authority payload contract |
| Command provenance is exact and replayable | ID/version/raw-byte SHA resolution on append and replay | Lifecycle, command-service, and replay provenance tests passed |
| Scope amendments are real typed deltas | Shared materializer consumes committed membership at submission and replay | Complete 31-case lifecycle module passed |
| Immutable evidence remains bound | Object/event comparison, revision graphs, and content hashes | Lifecycle and restore/authority exact-retry seams passed |
| Rejection publishes nothing | Validation and semantic preparation precede object/event publication | Pass for reached rejection branches; **C-1 prevents the required authority rejection from being reached** |
| Exact retry is identity- and payload-bound | Committed receipt reconstruction joins command/schema/payload/stream/version | Command-service, lifecycle, and authority exact-retry tests passed |
| Generated schema bytes remain frozen | Git tree identity rather than checkout byte assumptions | Accepted 87/86 counts and tree IDs equal the required base |
| Public helper exception docs are complete | `CONTRIBUTING.md` public-API rule | **Fail only for m-1** |

## 7. Verification evidence

The test environment used the pre-existing
`C:\Users\steph\TDL\.venv\Scripts\python.exe` with:

- `PYTHONDONTWRITEBYTECODE=1`;
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
- `-o addopts=` to disable repository coverage addopts; and
- `-p no:cacheprovider`.

### Changed behavior and named propagation seams

One invocation covered the two changed unit modules, the complete six-row
lifecycle module, explicit runtime bindings, authority-store exact retry,
restore-preflight replay, and mapping-shaped generic Task history:

```text
tests/research_system/unit/test_store.py
tests/research_system/unit/test_command_service.py
tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py
test_runtime_bindings_activate_first_scope_task_slice_and_t2_verticals
test_authority_store_exact_retry_replays_activated_lifecycle_history
test_restore_preflight_replays_exact_lifecycle_history
test_pre_cutover_generic_task_history_remains_replayable_and_resolvable
```

Result: **88 passed in 37.36s**.

A second invocation exercised payload-only authority genesis/revocation, the
unchanged T2 and release append branches, and replay's registered full-event
validation:

```text
test_genesis_is_atomic_replay_derived_and_exact_retry_is_read_only
test_revoke_payload_schema_rejects_extra_field_before_mutation
test_closed_family_receipt_v2_reducers_projection_and_legacy_indices
test_authorized_verified_command_publishes_one_self_referential_event
test_replay_validates_recorded_specific_event_with_inert_registry
```

Result: **5 passed in 38.06s**.

### Independent probes and static checks

- runtime activation-shadow probe with the real schema tree:
  - payload-only `AuthorityRootInitialized` plus `{}`: rejected with the five
    required payload fields reported absent; zero batches;
  - same tree plus an unbound permissive full schema:
    `is_active(...) == False`, but append succeeded and wrote one batch; and
  - authoritative replay rejected that persisted batch with
    `IntegrityError: authority root payload fields must be exact`;
- mixed Task plus ScopeDefinition `stream_states`, with separate active attempt:
  `PASS`;
- inactive exact `DispatchClaimed` direct append, with zero batch publication:
  `PASS`;
- documented-exception probe: reproduced the undocumented `TypeError`;
- Ruff targeted check: `All checks passed!`;
- Ruff targeted format check: `6 files already formatted`;
- `git diff --check 4317c59..3bbfbea`: passed;
- accepted schema trees/counts and protected blobs: passed; and
- post-test status remained exactly the two pre-existing Repowise setup
  changes.

CodeRabbit was not requested, triggered, polled, scheduled, or awaited.

No full repository suite was run. The complete changed-behavior modules plus
the exact propagation seams above were decisive, and no narrower validation
failed in a way that triggered a broader regression tier.

## 8. Decision audit

| Decision or boundary | Disposition |
|---|---|
| Accepted `86f1ac6` Scope semantic-delta remediation | Keep; direct tests and source trace remain closed |
| Full-event-before-payload append precedence | **Amend under C-1:** a runtime full schema must be authorized, not merely registered |
| Active/core/release/T2 branches | Keep their existing explicit branches; current named seams passed |
| Payload-only authority branch | **Amend under C-1:** preserve it against an inert full sibling |
| Legacy Task non-mapping `IntegrityError` guard | Keep; malformed shapes fail closed and valid mapping history survives |
| `ControlPlaneState.stream_states` rename | Keep; accurate for the mixed map and no checked-in old-field consumer exists |
| Lifecycle-helper docstring cleanup | Amend only the missing `TypeError` entry under m-1 |
| Generic store schema selection | Keep; fixtures now state their actual generic contract |
| D-G6-3 exact generated bytes | Keep; all 173 files remain exact |
| Direct post-genesis lifecycle grants | Defer to WP6.3 exactly as instructed |
| Owner acceptance, merge, and Gate 6 transition | Remain owner-reserved |

## 9. Practicality, revision plan, and residual risk

The Critical correction is bounded to schema-selection authority in append and
replay, plus one durable runtime-registry negative. It requires no schema
regeneration, migration, fabricated authority, or broad unrelated refactor.
The Minor correction is one docstring line.

Immediate correction:

1. make full-event selection activation-aware at append and replay, preserving
   the accepted payload sibling for an unbound authority event;
2. add the real-runtime-tree collision and version negatives specified in C-1;
3. document the propagated `TypeError` on
   `validate_exact_lifecycle_envelope`; and
4. obtain a fresh focused exact-subject review of the resulting immutable head.

Owner decision after correction: separately accept or reject the new exact
subject. This record does not request or imply that acceptance.

Later-work dependency: WP6.3 must still implement and independently validate
post-genesis scoped grants for these lifecycle commands.

After C-1 is fixed, remaining residual risks are bounded:

- the committed `stream_states` assertion covers a dispatch-only empty map;
  independent mixed-state execution passed, but a future durable populated
  mixed-state regression would improve coverage;
- the current catalogue contains no event identity with both a full schema and
  a payload sibling; that is why ordinary checkout tests stayed green, not
  evidence that the activation boundary is safe;
- the T2 prefix branch predates this subject and current known T2 event types
  are explicitly bound; any future T2 materialization still needs an explicit
  activation test rather than prefix authority; and
- future edits to the shared Scope materializer must preserve direct
  counterexample tests at both submission and replay.

None of these residual notes is a current defect on the reviewed subject.

## 10. Final decision

`rework_required`
