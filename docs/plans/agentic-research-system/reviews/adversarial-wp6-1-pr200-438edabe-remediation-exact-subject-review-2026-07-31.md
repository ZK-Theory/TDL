# WP6.1 PR #200 remediation exact-subject semantic review

**Date:** 2026-07-31  
**Verdict:** `accept_exact_subject`  
**Findings:** 0 Critical, 0 Major, 0 Minor  
**Immutable reviewed subject:** `438edabe25db39761823756c90452a2ecfd53337`  
**Required base ancestor:** `919a11f0045f810164ea028b29bd2c3b80781619`  
**Remediation parent / prior rework record commit:** `327b2ba0af4f8c857016191d6e77005466748926`  
**Prior finding record:** `docs/plans/agentic-research-system/reviews/adversarial-wp6-1-pr200-3bbfbeaa-final-exact-subject-review-2026-07-31.md`  
**Reviewed branch:** `codex/wp61-scope-task-revisions`  
**Remote binding:** the remote branch and live PR #200 ref both resolved to the reviewed subject

## 1. Executive verdict

`accept_exact_subject`

The remediation closes the prior Critical activation-shadow finding and the
Minor exception-contract finding without changing the 173 owner-accepted
generated schema files.

At both authoritative event-validation seams, the runtime registry now selects
an active event binding by trusted `event_type`, requires the recorded
ID/version to equal that binding, and validates the exact full schema through
`validate_active`. When no event binding exists, a runtime registry validates
the accepted payload sibling before considering any inert full schema. A
full-only unbound runtime identity remains rejected. Catalogue-only registries
retain their explicit full-schema-before-payload behavior without creating an
active binding. Replay preserves historical generic `ars://core/event`
identity rather than reinterpreting it through a future active binding.

The real authority-tree collision control copies the actual schema catalogue,
adds an inert permissive `AuthorityRootInitialized` full schema, and repeats
the case with an additional arbitrary `9.9.9` full version. Both variants
prove activation remains false, append rejects the invalid authority payload,
the batch set is unchanged, and replay rejects the same invalid payload before
application.

Independent source tracing and negative probes also found no new
schema-presence-as-activation path, version-selection bypass, unknown runtime
full-schema acceptance, append/replay selection mismatch, or regression in the
six accepted WP6.1 lifecycle rows. Release and T2 special branches and exact
command provenance remain intact.

This verdict is acceptance of the immutable technical subject only. It is not
owner acceptance, merge authority, Jira transition, or Gate 6 acceptance.
Direct post-genesis lifecycle grant enforcement remains assigned to WP6.3.

## 2. Exact identity, scope, and protected state

The review verified:

- cwd and Git top-level resolve to
  `C:\Users\steph\.codex\worktrees\6f50\TDL`;
- the symbolic branch is `codex/wp61-scope-task-revisions`;
- local `HEAD`, the remote branch, and `refs/pull/200/head` all resolve to
  `438edabe25db39761823756c90452a2ecfd53337`;
- the subject's sole parent is
  `327b2ba0af4f8c857016191d6e77005466748926`;
- required base `919a11f0045f810164ea028b29bd2c3b80781619`
  and remediation parent `327b2ba0af4f8c857016191d6e77005466748926`
  are ancestors of the subject; and
- the only pre-existing worktree changes are Repowise setup state in
  `.claude/CLAUDE.md` and `.repowise-workspace.yaml`. They were not edited,
  staged, reverted, or used as semantic evidence.

The immutable subject changes exactly six paths relative to its parent:

1. `research_system/command/lifecycle.py`;
2. `research_system/projection/replay.py`;
3. `research_system/store/ledger.py`;
4. `tests/research_system/integration/test_authority_grant_source.py`;
5. `tests/research_system/unit/test_replay.py`; and
6. `tests/research_system/unit/test_store.py`.

The generated WP6.1 schema subtrees are byte-identical to the required base:

- 87 command schemas at Git tree
  `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`; and
- 86 event schemas at Git tree
  `154ffc4bdde82fe903718734687e7a62797b1f69`.

The whole `.research-system/schemas` tree is also identical at base and head:
`f550ea5f00213dbb397146cc80d05cbec7c2ffcf`. It contains 276 catalogue
files in both commits; the wider count includes the 173 generated WP6.1 files
plus pre-existing non-generated schema families.

## 3. Findings

### Critical

None.

### Major

None.

### Minor

None.

The strongest attempted counterexamples failed at the intended boundary:

- an active `TaskCreated` identity with a generic-only payload failed exact
  full-schema validation and published no batch;
- an unbound runtime full-only `DispatchClaimed` identity failed append before
  publication and failed replay before application;
- an inert permissive full `AuthorityRootInitialized` schema could not shadow
  the accepted payload sibling at either append or replay, including with an
  additional full version in the catalogue;
- a historical generic `TaskCreated` event remained readable despite the
  future active exact binding; and
- a catalogue-only registry containing both a strict full schema and a
  permissive payload sibling continued to enforce the full schema.

## 4. Prior-finding closure

| Prior finding | Prescribed mechanism | Direct closure evidence | Disposition |
|---|---|---|---|
| C-1: inert full schema shadows accepted authority payload | Active binding selects exact full schema; unbound runtime payload-backed event keeps payload validation; unbound full-only remains inactive; catalogue-only keeps explicit full-before-payload; append and replay agree | Append uses `validate_active` for a bound event and runtime payload-first selection for an unbound event (`research_system/store/ledger.py`, lines 227-273). It rejects unbound full-only runtime identities before validation/publication (`ledger.py`, lines 382-415). Replay applies the same active/runtime/catalogue matrix (`research_system/projection/replay.py`, lines 80-116 and 473-500). The real-tree collision control covers activation false, append, replay, batch immutability, and an arbitrary version (`tests/research_system/integration/test_authority_grant_source.py`, lines 238-310). | Closed |
| m-1: lifecycle helper omits propagated `TypeError` | Document the propagated canonical-JSON `TypeError` without changing runtime behavior | `validate_exact_lifecycle_envelope` now documents `TypeError` for unsupported P0 canonical JSON and keeps the existing `ValueError` contract (`research_system/command/lifecycle.py`, lines 43-74). Replay still normalizes both to `IntegrityError` (`research_system/projection/replay.py`, lines 34-41). | Closed |

The prior finding governed append and replay plus structurally related runtime,
catalogue-only, full-only, payload-backed, versioned, and historical-generic
siblings. Each sibling has a direct disposition above; closure is not inferred
from the original proof-of-concept alone.

## 5. Remediation acceptance matrix

| Required boundary | Enforcement and decisive evidence | Disposition |
|---|---|---|
| 1. Active event bindings select the exact full schema through `validate_active` during append and replay | Append resolves the event binding, requires recorded ID/version equality, then calls `validate_active` (`ledger.py`, lines 254-260 and 383-415). Replay performs the same equality and active validation (`replay.py`, lines 88-102). Independent invalid-active-full probe rejected and left zero batches. | Pass |
| 2. Unbound runtime authority event keeps its accepted payload sibling despite inert full siblings | Runtime append checks `requires_command_provenance` and validates the payload sibling before any full schema (`ledger.py`, lines 262-273). Runtime replay does the same and returns after payload validation (`replay.py`, lines 103-108). The real authority collision control passed for one matching full schema and for an additional `9.9.9` full schema. | Pass |
| 3. Unbound runtime full-only event identities reject on append and replay, publishing no batch | Append's runtime inactive guard requires an active binding, accepted payload sibling, generic core identity, release branch, or T2 branch (`ledger.py`, lines 382-407). Replay raises inactive when no payload sibling exists (`replay.py`, lines 103-108). Durable tests cover both seams (`test_store.py`, lines 441-466; `test_replay.py`, lines 187-201); independent probes confirmed zero append batches. | Pass |
| 4. Catalogue-only registries retain full-before-payload validation without runtime authority | With no active bindings, append checks a registered full schema before its payload sibling (`ledger.py`, lines 262-273); replay mirrors that order (`replay.py`, lines 109-116). The catalogue-only strict-full/permissive-payload test and independent probe both rejected the incomplete payload (`test_store.py`, lines 348-406). | Pass |
| 5. Generic historical core identities are not reinterpreted by future bindings | Replay returns from specific-schema selection when the recorded schema is exactly `ars://core/event` (`replay.py`, lines 84-87), after generic envelope and exact command-provenance validation. Durable and independent probes preserve historical generic `TaskCreated` state (`test_replay.py`, lines 176-184). | Pass |
| 6. Release, T2, and exact command-provenance branches remain intact | Append retains separate T2 and release full-schema returns (`ledger.py`, lines 240-253); replay retains separate T2/release validation (`replay.py`, lines 455-500). Append resolves exact recorded command ID/version/hash before event validation (`ledger.py`, lines 309-317); replay does the same (`replay.py`, lines 459-482). Focused release, T2, replay-drift, authority-retry, and provenance tests passed. | Pass |
| 7. Real authority collision control covers append, replay, activation false, batch immutability, and arbitrary version without schema-byte changes | The test copies the actual schema tree, adds `1.0.0` and optional `9.9.9` inert permissive full schemas, asserts all inactive, rejects empty payload on append and replay, and compares batches before/after (`test_authority_grant_source.py`, lines 238-310). Both parameter rows passed. Base/head generated schema tree identities are equal. | Pass |
| 8. `validate_exact_lifecycle_envelope` documents propagated canonical-JSON `TypeError` | Docstring lines 55-59 accurately name `TypeError` and `ValueError`; the implementation still propagates the canonical call at line 72. | Pass |
| 9. No new bypass, ambiguity, divergence, or six-row compatibility regression | Source-path matrix plus 76-test shared ledger/replay/six-row run, focused authority/release/T2 runs, and five independent negatives found no reachable bypass or append/replay mismatch. | Pass |

## 6. Six accepted WP6.1 lifecycle rows

| Accepted row | Exact pair | Exact-subject disposition |
|---|---|---|
| `scope.create` | `CreateScopeDefinition -> ScopeDefinitionCreated` | Pass: active ID/version selection, exact full schema, immutable definition, replay, and provenance remain closed. |
| `scope.amend_revision` | `AmendScopeDefinition -> ScopeDefinitionAmended` | Pass: committed typed membership delta, no-op/absent/wrong-kind rejection, exact schema, replay, and atomicity remain closed. |
| `scope.supersede` | `SupersedeScopeDefinition -> ScopeDefinitionSuperseded` | Pass: current replacement, terminal/cycle, exact dispositions, history, and replay remain closed. |
| `task.create` | `CreateTask -> TaskCreated` | Pass: active full schema, rich definition/project/content binding, generic-history separation, replay, and retry remain closed. |
| `task.amend_revision` | `AmendTask -> TaskAmended` | Pass: current consecutive revision, exact typed-field delta, immutable source/replacement, replay, and no-op rejection remain closed. |
| `task.supersede` | `SupersedeTask -> TaskSuperseded` | Pass: compatible current replacement, cycle/terminal/disposition controls, exact/generic provenance, replay, and history remain closed. |

The complete lifecycle module was run because the changed append and replay
helpers are shared by all six accepted rows. No narrower failure triggered a
package or full-repository regression tier.

## 7. Consistency and enforcement matrix

| Invariant | Append enforcement | Replay enforcement | Decisive control |
|---|---|---|---|
| Catalogue presence is not full-schema activation | Bound event uses `validate_active`; unbound runtime event never selects inert full schema | Same binding/runtime split | Real authority collision plus active-invalid and full-only probes |
| Accepted payload authority cannot be shadowed | Runtime payload sibling precedes inert full catalogue entries | Same | Matching and arbitrary-version collision rows |
| Full-only runtime identity is inactive | Explicit pre-publication guard | Explicit inactive error before application | Append/replay `DispatchClaimed` negatives |
| Catalogue-only full-schema semantics remain explicit | Full before payload | Full before payload | Strict-full/permissive-payload test and probe |
| Recorded active identity is exact | Recorded ID/version must equal binding | Same | Six-row lifecycle and replay provenance tests |
| Historical generic identity remains historical | New active appends cannot choose generic identity | Exact generic ID short-circuits future binding | Generic-history durable and independent probes |
| Command provenance is exact | Complete ID/version/hash required and resolved | Complete ID/version/hash required and resolved | Wrong-hash/version tests and authority retry |
| Rejection publishes/applies nothing | Validation precedes temporary batch creation and publication | Validation precedes `apply_event` | Batch equality and zero-batch assertions |
| Release and T2 keep their special contracts | Dedicated exact full-schema branches | Dedicated exact full-schema branches | Focused release and T2 runs |
| Public helper exception docs match behavior | Not applicable | Replay catches both documented exception types | Docstring/source trace |

## 8. Verification evidence

All pytest execution used the pre-existing external interpreter
`C:\Users\steph\TDL\.venv\Scripts\python.exe` with:

- `PYTHONDONTWRITEBYTECODE=1`;
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
- `-o addopts=`; and
- `-p no:cacheprovider`.

### Shared changed-behavior and six-row run

```text
tests/research_system/unit/test_store.py
tests/research_system/unit/test_replay.py
tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py
tests/research_system/unit/test_schema_registry.py::test_runtime_bindings_activate_first_scope_task_slice_and_t2_verticals
```

Result: **76 passed in 38.80s**.

### Real authority collision

```text
test_runtime_authority_payload_schema_cannot_be_shadowed_by_unbound_full_schema
```

Result: **2 passed in 27.22s**, covering `matching-version` and
`additional-arbitrary-version`.

### Authority compatibility

```text
test_genesis_is_atomic_replay_derived_and_exact_retry_is_read_only
test_authority_store_exact_retry_replays_activated_lifecycle_history
test_revoke_payload_schema_rejects_extra_field_before_mutation
```

Result: **3 passed in 23.41s**.

### Release and T2 compatibility

```text
test_authorized_verified_command_publishes_one_self_referential_event
test_closed_family_receipt_v2_reducers_projection_and_legacy_indices
test_replay_rejects_t2_event_schema_or_provenance_drift
```

Result: **4 passed in 16.44s** because the replay-drift node is parameterized.

### Independent negative probes

A temporary external control root and temporary schema catalogues established:

1. active `TaskCreated` plus generic-only payload rejected; zero batches;
2. runtime unbound full-only `DispatchClaimed` append rejected; zero batches;
3. runtime unbound full-only replay rejected before application;
4. future active `TaskCreated` binding did not reinterpret generic history; and
5. catalogue-only strict full schema retained precedence over a permissive
   payload sibling.

All five probes passed.

### Static and exact-byte checks

- Ruff targeted check: `All checks passed!`;
- Ruff targeted format check: `6 files already formatted`;
- `git diff --check 327b2ba..438edabe`: passed;
- base/head whole-schema and generated command/event tree identities: passed;
- remote branch and PR head equality: passed; and
- final code/test diff from immutable subject: empty.

Two preliminary combined seam invocations exceeded the 60-second command
wrapper and were not counted as evidence. Every selected node was rerun in the
bounded successful invocations reported above.

CodeRabbit was not requested, triggered, polled, scheduled, or awaited.

## 9. Decision audit

| Decision or boundary | Disposition |
|---|---|
| Prior C-1 activation-shadow remediation | Accept at exact subject |
| Prior m-1 exception documentation remediation | Accept at exact subject |
| Runtime active event selects exact full schema | Keep |
| Runtime unbound accepted payload sibling outranks inert full catalogue entries | Keep |
| Runtime unbound full-only identity remains inactive | Keep |
| Catalogue-only full-before-payload semantics | Keep |
| Historical generic identity is not retroactively activated | Keep |
| Exact command provenance resolution | Keep |
| Release and T2 special validation branches | Keep |
| Six accepted WP6.1 lifecycle rows | Keep |
| 173 generated WP6.1 schema bytes | Keep unchanged |
| Direct post-genesis lifecycle grants | Defer to WP6.3 exactly as assigned |
| Owner acceptance, merge, Jira, and Gate 6 transition | Remain owner-reserved |

## 10. Coverage, practicality, and residual risk

The correction is proportionate: two shared selection helpers, one factual
docstring line, and focused negatives at the runtime, catalogue-only,
authority, version, append, replay, and historical-generic seams. It does not
regenerate schemas, migrate evidence, fabricate authority, or widen human
approval.

No current coverage gap rises to a finding. Residual risks remain:

- `requires_command_provenance` currently distinguishes a runtime registry
  from a catalogue-only registry by the presence of at least one active
  binding. The production `runtime_schema_registry` always supplies the
  accepted binding set; a future alternative runtime constructor must preserve
  that property or make registry mode explicit.
- T2 continues to use its pre-existing schema-ID prefix branch. Current T2
  identities and versions have focused controls, but any future T2 family
  extension still requires an explicit activation and replay review.
- The arbitrary-version authority collision leaves the recorded event at the
  core-supported `1.0.0`, while adding `9.9.9` to the inert catalogue. This is
  sufficient to prove catalogue multiplicity cannot alter current selection;
  a future generic core event-version expansion would require its own
  compatibility control.
- Direct post-genesis scoped authority grants remain a WP6.3 dependency and
  were not represented as complete here.

No full repository suite was run. The changed modules, every accepted WP6.1
row, and the named authority/release/T2 propagation seams passed; no failure or
shared-generator/schema change triggered the broader tier.

## 11. Final decision

`accept_exact_subject`

Owner acceptance must be requested and recorded separately against this exact
subject. This review does not supply it.
