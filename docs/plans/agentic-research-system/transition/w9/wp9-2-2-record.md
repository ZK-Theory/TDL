# WP9.2-2: the legacy runtime, genesis, shared replay and CLI

**Date:** 2026-10-28<br>
**Status:** Revision 4. The independent review, its re-review and the PR #408 bot comments are disposed in §8. Not
merged, D-4 not accepted.<br>
**Package:** 06v WP9.2, second of its two PRs (P-077 item 4). The design note is `transition/w9/wp9-2-design-note.md`,
revision 3, confirmed and merged as `779fc8bc` (PR #405).<br>
**Authority:** P-076, with P-077. The bootstrap contract was accepted at O-3 (P-078, main `69e9e059`); the catalogue
and annex at O-8 (P-075, main `7979e85a`).<br>
**Base:** `main` at `6ce597ba`.<br>
**Not authorized (P-076):** WP9.3 to WP9.7; live operations L-0 to L-5; a real store, genesis or a grant on one; any
legacy write. Every store in this package's tests is a scratch store under `tmp_path`.

## 1. What landed

| Design note | Code |
|---|---|
| §2 U-7, the four sites | Site 1 and site 4: `research_system/projection/replay.py` (`_replay`). Site 2: `discovery/routes.py` (`shared_event_partition` returns `"legacy"`). Site 3: `discovery/replay/driver.py` (one `continue`). Each imports the predicate lazily |
| §2.1 predicate | `research_system/legacy/commands.py`: `LEGACY_COMMAND_TYPES` (12, a literal) and `is_legacy_projection_event` |
| §3 binding and authority | One `SchemaBinding("ars://core/command", "1.0.0", command_type="ImportAcceptedW9CatalogueGenesis")` in `schema_registry.py`; the genesis command in `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` and as `scope_definition` in `_SCOPED_COMMAND_SUBJECT_KINDS` (`authority.py`) |
| §3 route classes, §4 row assignment | `research_system/legacy/routes.py`: `LEGACY_ROW_ROUTES` (61 rows, generated from the accepted catalogue and checked against it by `validate_legacy_route_registry`); `LEGACY_ROUTED_ROWS` = {LR-001}; `LEGACY_DEFERRED_ROWS` (60, tagged); `assign_row`, `e_only_discriminant`, `w9_row_ref`, `validate_transaction_shape` |
| §5.1, §5.2 | `research_system/legacy/accepted_w9.py`: `ACCEPTED`, `RESERVED_EXTERNAL_REFS`, `ROW_IDS`, `CATALOGUE_STREAM_ID`, `accepted_genesis_payload()` |
| §7.1 to §7.3 | `research_system/legacy/runtime.py`: `LegacyRuntime`, `refuse_gate6_store`, `W9Gate6StoreRefused` (reason code `w9_gate6_store_refused`) |
| §7.4 | `research_system/legacy/replay/driver.py` (`replay_legacy`) and `replay/reducers.py` |
| §8 | `ars legacy status` and `ars legacy show <id>` in `cli.py`, read-only; `legacy` joins `main`'s error set |
| §10 D-4 | See §4 |

## 2. Fixed values

- `CATALOGUE_STREAM_ID` is `obj_01a17eb7-5ae0-7000-8000-000000000001`: the `accepted_at` millisecond prefix of the
  reserved refs, with a fixed tail. The design note fixes only that it is a constant.
- `ACCEPTED` carries the O-8 catalogue and annex identities, the O-3 contract (`69e9e059`, blob `6bbbb14a`,
  `47699ed7…ddb1`, 4,164 bytes) and the envelope (`69e9e059`, blob `9b28528c`, `c26f468c…5999`, 11,185 bytes), the
  multiset hash `a8078818…ffde7` and the Gate 6 identity `5e3b95a9…8d69`.
- `accepted_genesis_payload()` names the amended contract and the envelope at `69e9e059`. Its
  `verification_requirements` are the contract's `verification_rules`, verbatim; a test checks them against the file.
- `ACCEPTED_REVISIONS` is empty: LR-002 is inert in v1.

## 3. Interpretations the reviewer should check

1. **Where the store is bound (§7.2).** `LegacyRuntime` is handed a bound ledger, as `DiscoveryRuntime` is. On every
   `submit`, before the lock, `refuse_gate6_lock_roots` checks every root the lock writes into (review F-4):
   - The ledger's control root must carry a readable manifest whose identity is not refused. A store whose manifest
     cannot be read is refused, because its identity cannot be shown not to be the Gate 6 one.
   - Every lock root, the ledger root included, is refused if any directory at or above it holds a manifest with a
     refused identity. So a scratch manifest nested inside the Gate 6 store does not hide it. A manifest path that
     exists but cannot be read is refused too, such as a directory or a dangling link (CodeRabbit on PR #408).

   It also refuses when `ledger.store_identity` is refused. Constructing the runtime writes nothing. The receipt store,
   which creates the directories the lock takes, is built in `submit` after the refusal. Binding through
   `load_store_manifest` happens where the ledger is built, and building an `EventLedger` creates its directories, so a
   caller must refuse before it binds: the CLI runs `refuse_gate6_store` first and only then calls `_verified_ledger`.
2. **G5 in replay.** A record that a Decision resolves must equal its open proposal exactly (the same pre-assigned ID
   and content) and name the resolving Decision. LR-020's ownership transitions have no proposal of their own (P-072
   item 2), so each claims its own identity. Review satisfaction, the Decision's kind and resolver, and the G3 role
   rules are preparer checks for the packages that admit those commands; WP9.2 admits none. Two more G5 checks are
   recorded in §7 as preparer obligations (review F-8).
3. **W9-T21, reducer half.** Every root, mapping, transition and recovery Decision adds its ref edges to one graph, and
   a self-reference or cycle is refused. A recovery Decision whose evidence names its recovery root is refused
   explicitly. Only a recovery Decision (LR-037) is a source of edges. Other Decisions are targets only, because
   W9-T21 names recovery Decisions, and an ownership or registration Decision names the record it governs as evidence
   while that record names the Decision. Revision 1 added edges for every Decision, so the ordinary LR-053 → LR-054
   flow was refused as a cycle; the reducer tests (review F-3) found it. The cycle check walks from the new edges'
   targets, iteratively, so a long chain cannot raise `RecursionError` (review F-9).
4. **LR-002.** `accepted_revisions` is a runtime and replay parameter, empty in production. With no binding row the
   production runtime refuses it ("inactive W9 command binding"). The catalogue's LR-002 identities run on the test
   registry with one test revision.
5. **The site 3 and site 1 negative controls** are simulated, not source edits. Site 3: a wrapper maps `"legacy"` to an
   unhandled partition, which is what removing the `continue` does. Site 1: the forged W2-typed event is passed to
   `_validate_active_lifecycle_binding` directly, which is the check site 1 skips.
6. **C2's messages.** A W2-typed event recorded under its W2 schema with no producer binding fails the shared replay
   with "inactive event schema"; recorded as `ars://core/event`, as the U-7 probe did, it fails with "unbound event
   producer". Both are asserted.
7. **C4.** The consumer test parses the four files and follows every reference to `shared_event_partition`, bare or
   as an attribute. Each reference must be called. A result may be compared directly, or assigned to a name and
   compared later, as in the Discovery driver. The test also checks that these four are the only consumers under
   `research_system/`. Every partition decision compares against string literals:
   - `==` and `in` select, as the whole test of an `if` with no `else`, or as a comprehension filter;
   - `!=` and `not in` are accepted only as a bare `continue` guard;
   - `== X: continue` followed by a default is accepted only in the Discovery driver, whose default is guarded by its
     own `"legacy"` branch.

   Only one decision names `"legacy"`: U-7 site 3's `continue` in the driver. Accepted and refused consumer shapes are
   its controls. They include the six shapes that the review addendum on `0e0c15dd` showed the first rework still
   accepted. CodeRabbit's nitpick on PR #408 was the start: the first version checked only inline comparisons.
8. **LR-014 (review F-2).** `RecordLegacyLightInventory` has its own reducer, not `reduce_record`. The record must be
   the open LR-011 proposal's exact bytes under the proposal's ID, which LR-011 claimed, so LR-014 claims no identity.
   Its `independent_reproduction_ref` must name a W9 review of that proposal: the request's paired `subject_ids` and
   `subject_hashes` must name the record's ID and `content_hash`, and the verdict must be recorded under LR-013 as
   `approve`. "A positive reproduction review" is read as `approve` only: `approve_with_conditions` is not a
   reproduction.
9. **LR-020's ownership events.** `replay_legacy` validates an `E:` payload against its row's record schema, but
   LR-020's repeated `LegacyOwnershipTransitionedRecorded` events are ownership records, not acceptances. They are now
   validated against `ars://legacy/legacy-ownership-transitioned`. Revision 1 refused every LR-020 transaction with
   an ownership event, and the reducer tests found it.

## 4. D-4 (design note §10)

WP9.2-2 changes these protected identities. Stephen re-accepts them at exact bytes, as they stand in the merge-queue
entry:

| Identity | Before | After |
|---|---|---|
| Runtime-binding census | 261 rows, `f359855bf5e760c3336dd201dd69e765d5bd0a91836dedcb5ddfecaeea0470d7` | 262 rows, `3d6ae37aba22f58e22d334745dfb0f66fa9f80a4a85c7a9fd633eb24963e9f06` |
| 06h manifest YAML (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`) | count, digest and nine append sites | the new count and digest, and one more append site: `research_system/legacy/runtime.py`, `LegacyRuntime._submit_authorized`, `self.ledger`, `legacy_command_producer` |
| Append-site classification (the smoke test's `APPEND_SITE_CLASSIFICATIONS`) | | `legacy_command_producer` added |
| Command and event schema trees | unchanged | unchanged: no core schema changes |
| T2 validator expectations and seal | | unaffected: none reads the census |

`tests/research_system/unit/test_schema_registry.py` pins the count too (261 → 262).

The two 06h files as committed here (the merge-queue bytes are the ones to accept):

| File | Before (blob) | After (blob, SHA-256, bytes) |
|---|---|---|
| `wp6_1_06h_current_append_manifest.yaml` | `7cfc0758744c829dc0a154dc3f37a851bf280b0b` | `adbb334f0cd08d0ca0ceaed34d43018abf2f119d`, `344a341d687c15ae2437eef05c4a90920774823a699e8725ea188e3fb2b7860c`, 6,343 |
| `test_wp6_1_06h_append_path_closure.py` | `315b58a58ce7a9ec1833faee37a6b48f34901212` | `922ae844cf7500484f11c1fe2f736d1da4681252`, `25c511451fa99fe893d7b5b7ad9bf611c4159407e8bf0a371023591862e72748`, 26,480 |

## 5. Tests

| File | What it covers |
|---|---|
| `tests/research_system/contracts/test_w9_legacy_routes.py` (store-free) | `ACCEPTED` equals the independent O-8 and O-3 pins, and the envelope identity read from Git at the O-3 main commit (review F-7); G4's exact subject at grant parsing (role-only, path-only, wildcard); the reserved IDs re-derive from their domain strings; the genesis payload validates and carries the contract's values; `LEGACY_COMMAND_TYPES` equals the catalogue's command set; only genesis is bound; the route registry is exact and refuses five catalogue mutations; the 1/60 partition and every tag; C5; C4; row assignment is a bijection onto the 61 rows (LR-035/LR-038, LR-054/LR-055 and the record-less Decision pairs included); the 18 `E:`-only discriminants; W2 refs; transaction shapes; W9-T5; W9-T11 store half; supersession acyclic; W9-T21 reducer half; W9-C25 and the reserved IDs |
| `tests/research_system/integration/test_w9_legacy_runtime.py` | W9-C01-LR-001 and shared replay (generic, rebuild, Discovery, legacy); W9-C11-LR-001 retry; a second genesis; no W11 genesis; the wrong target; W9-C03-LR-001 mutations refused before binding with the receipt root unchanged; tampered catalogue, annex, contract and envelope bytes; a grant scoped elsewhere, with the resolver's message; the n-4 human-actor guard: a non-owner with an agent-class grant refused, and with a human-class grant accepted (review F-1); W9-T20's three cases with both roots unchanged, directories included, when refused; a receipt root at or below a Gate 6 control root refused; construction writes nothing (review F-4); an unreadable manifest; genesis guards 2, 5 and 8 (review F-6); an unbound W9 command; the §2.5 asymmetry, with its message; the LR-002 three on the test registry, and LR-002 refused in production; the CLI |
| `tests/research_system/integration/test_w9_legacy_replay.py` | The shared replay with a W9 observation and a schema-valid W2-typed W9 event on the test registry; the predicate-removed, site-3-removed and lifecycle-restored negative controls; C1 (its message), C2 (both forms), C3; a deferred row; a schema-invalid payload; a W9 event type under a non-W9 command; replay's second-genesis, payload and no-W11-genesis refusals; the reserved IDs and that no reader dereferences them. The deferred rows' reducers on forged ledgers with every row routed (review F-2, F-3): G5 through LR-003 → LR-005, with other content, no proposal and another Decision refused; a Decision resolved under another family; W9-T5 through LR-054 and LR-055, with a stale `from_mode`, a row of another direction and a not-yet-successor closure refused; LR-020 with its acceptance and an ownership closure; LR-011 → LR-014, with other bytes, a fresh ID, a verdict other than approve, a review of another subject, an approval under another review row (review N-1) and a second LR-014 refused; the LR-035 → LR-038 recovery, with a recovery Decision naming its root, an unresolved Decision and an unrecorded predecessor refused; a cycle through a recovery Decision, a transition and a recovery root; supersession acyclic through LR-060 |

## 6. Verification

Run on the branch's working tree before commit, with `uv run pytest --no-cov -q -p no:cacheprovider`, serially:

| Check | Result |
|---|---|
| The six W9 test files together (materialization, expected catalogue, acceptance envelope, legacy routes, legacy runtime, legacy replay) | 352 passed |
| The regression set: the 06h smoke test, `test_schema_registry.py`, the W11 materialization and catalogue tests, `test_p045_envelope_decision.py`, the Discovery activation and architecture tests, the W9 materialization, catalogue, envelope and legacy-route tests, `test_store.py`, `test_command_service.py`, `test_wp6_2_t2_runtime.py` | 913 passed, 1 skipped (the existing skip in `test_schema_registry.py`) |
| `tests/research_system/integration/test_wp6_6_discovery_runtime.py` (site 2 and site 3 touch its driver) | 100 passed (30 min 31 s) |
| `uv run ruff check` and `uv run ruff format --check` on the changed files | clean |
| `verify_w9_materialization.py --require-catalogue` | 61 pinned rows, 0 problems |

The full suite was not run.

After `5f9bb8f6`, the C4 rework (§3 item 7) replaced one test in `test_w9_legacy_routes.py` with twelve. That file
now gives 51 passed, and ruff is clean. No code under `research_system/` changed.

**Revision 2**, on the working tree before commit:

| Check | Result |
|---|---|
| The regression set above, plus `test_w9_legacy_runtime.py` and `test_w9_legacy_replay.py`, in one run | 1,004 passed, 1 skipped (the existing skip) |
| Mutation checks (scratch script: each mutation applied alone, its test run, the file restored by bytes). The current-mode check, the `_ROW_DIRECTIONS` check, the recovery-root check, G5's content equality, the n-4 human guard, the receipt-root refusal and LR-014's approval check, each deleted or weakened | 7 of 7 caught |
| `uv run ruff check` and `uv run ruff format --check` on the changed files | clean |
| `verify_w9_materialization.py --require-catalogue` | 61 pinned rows, 0 problems |

`test_wp6_6_discovery_runtime.py` was not re-run. Revision 2 changes only `research_system/legacy/`, which the
Discovery runtime reaches only through site 4 when a ledger holds W9 events, and its tests hold none. The full suite
was not run. D-4 is unchanged: the census and both 06h blobs are as in §4.

**Revision 3** changes tests and this record only. Checks:
- The three W9 legacy files (routes, runtime and replay) give 132 passed.
- The scratch mutation script catches the mutation that survived the re-review (LR-014's reproduction-row check
  deleted).
- Ruff is clean.

**Revision 4** changes `legacy/runtime.py`, `cli.py` (`_verified_ledger` gains `read_only`, and other callers are
unchanged), the runtime test and this record. Checks:
- One run of the three W9 legacy files, plus the files that drive `_verified_ledger` through `replay verify`, gives
  258 passed. Those files are `test_replay.py`, `test_store_binding_cli.py`,
  `test_scoped_authority_grant_activation.py`, `test_eval_cli.py` and `test_command_cli.py`.
- Each of the three fixes, reverted alone, fails its new test.
- Ruff is clean.
- D-4 is unchanged.

## 7. Not in this PR

- Commands other than genesis, their binding rows and their D-4 (WP9.3, WP9.4, WP9.6, WP9.7).
- Live operations, including L-3 genesis on a real store. LR-001's two owner preconditions stay L-3 gates: O-8
  current, and the bootstrap implementation independently verified against the accepted contract, which is this PR's
  independent review together with O-3.

**Obligations on later packages (from the review):**
- **WP9.3's mutating CLI (F-4).** Run `refuse_gate6_store` on the target control root before `_verified_ledger` and
  before building any `EventLedger`, as `ars legacy` does. Building a ledger creates its directories.
- **WP9.3 and WP9.4 preparers (F-8).** Two G5 checks that replay does not make:
  - the resolving Decision's proposal named this record, by its pre-assigned ID and exact content hash, as its
    subject;
  - LR-020's ownership records equal the acceptance proposal's list, one per accepted whole-file item and no others.

  Consider adding the LR-020 list check to replay when LR-020 is routed.
- **Preparers generally.** Superseding a record that does not exist is not refused at replay.
- **WP9.3: the W9 record content hash (review N-2).** A W9 record's `content_hash` is self-declared. G5's exact
  content hash and LR-014's proposal hash are compared against that field, and replay never derives it from the
  record's bytes, as Discovery replay does for its subjects. WP9.3 must:
  - fix the W9 record content-hash rule. One candidate is the SHA-256 of the canonical record with `content_hash`
    removed, as `command/lifecycle.py` `content_hash_matches` does for `content_sha256`;
  - have the preparer stamp it;
  - have replay recompute it in `reduce_proposal` and every record reducer, before any subject or G5 comparison.

  This touches deferred rows only: production routes LR-001, and the genesis payload carries no `content_hash`.

**For the L-3 checklist:**
- **R-1.** Run L-3 from a checkout at or after this PR's merge commit, re-verified by bytes. Genesis guard 6
  re-hashes from `repository_root`, and `C:\Users\steph\TDL` was at `779fc8bc` (before `69e9e059`) on 2026-10-28, so
  from there genesis fails closed.
- **R-2.** At L-0, check read-only that `load_store_manifest_unbound` parses the live Gate 6 manifest. If it cannot,
  the refusal is the generic "cannot read the target store identity": still closed, but not the W9 reason code.
- **R-3.** The reserved IDs and `CATALOGUE_STREAM_ID` are protected from W9 pre-assignment only. A Discovery or
  generic command could pre-assign a reserved `dec_` or squat on the stream. A squatted stream makes genesis fail
  closed (a stream conflict or guard 5). This is accepted by design: no reader dereferences the reserved refs.

**Test gaps recorded, not closed:**
- **Guard 5** has no reachable input through `submit`: a version other than 0 meets a stream conflict or guard 3
  first, and no W9 command but genesis writes the catalogue stream. It is tested by calling `_prepare_genesis`
  directly, and it is defence in depth.
- **The §2.5 asymmetry test** runs the two replays over a tampered ledger. It does not append a Discovery command
  over it, which would need a raw ledger rewrite.
- **The CLI read-only test** monkeypatches `_verified_ledger`. Revision 4 tests the read-only binding's refusal of a
  missing event directory with its inputs stubbed. The binding against a real approved foundation is not exercised.
- **The verify-restore replay** (`verify_restore_before_writer_lease`) goes through the generic boundary that
  W9-C01 exercises, but has no test of its own.

## 8. Review dispositions

The independent adversarial review of `5f9bb8f6` and its addendum on `0e0c15dd` gave the verdict accept with required
changes. The report is in the session notes as `wp9-2-2-review.md`. Stephen chose to fix F-1 to F-7 in this PR, with
F-3 option (a) (2026-10-28).

| Finding | Severity | Disposition |
|---|---|---|
| F-1: the genesis human-actor guard untested | Major | Fixed. Non-owner tests: an agent-class grant is refused with the guard's message, and a human-class grant is accepted. The scoped-elsewhere test asserts the resolver's message. G4's exact subject is tested at grant parsing |
| F-2: LR-014 refuses the accepted flow and admits an unbound record | Major (latent) | Fixed: `reduce_light_inventory` (§3 item 8) |
| F-3: the reducers untested through `replay_legacy` | Major | Fixed, option (a): 21 forged-ledger tests with every row routed (§5). They found two more defects, both fixed: Decision edges for non-recovery Decisions (§3 item 3), and LR-020's ownership events validated against the acceptance schema (§3 item 9) |
| F-4: the Gate 6 refusal covers one lock root; construction writes | Minor | Fixed: `refuse_gate6_lock_roots`, the receipt store built after the refusal, and `_tree_bytes` lists directories. The mutating-CLI rule is a WP9.3 obligation (§7) |
| F-5: the C4 test cannot fail for its mutation | Minor | Fixed: `0e0c15dd`, then the addendum's six shapes (§3 item 7) |
| F-6: genesis negatives without a test; controls without a message | Minor | Fixed: guards 2, 5 and 8; messages on the asymmetry, C1 and grant-scope tests. Guard 5's reachability and the other gaps are recorded in §7 |
| F-7: the envelope pin written in the same PR as `ACCEPTED` | Minor | Fixed: read from Git at the O-3 main commit |
| F-8: G5's subject binding and LR-020's list | Minor | Deferred with dependency: preparer obligations in §7 |
| F-9: `_add_edges` quadratic and recursive | Minor | Fixed: iterative check from the new edges' targets |
| R-1 to R-3 | Residual | On the L-3 checklist (§7) |

The re-review of `4ff0d432` (addendum §10) gave the verdict accept. It found F-1 to F-7 and F-9 closed, and its own
mutation probe caught 14 of 15 mutations. Revision 3 disposes its new findings:

| Finding | Severity | Disposition |
|---|---|---|
| N-1: LR-014's reproduction-row check has no test | Minor | Fixed. A review that names the inventory under LR-007 and is approved under LR-008 is refused. The surviving mutation is now caught |
| N-2: the W9 `content_hash` is never recomputed at replay | Minor (latent) | Deferred with dependency: a WP9.3 obligation in §7 |
| Nit: the C4 negative controls match no message | Nit | Fixed: each control asserts its own message |
| Nit: G4's wildcard case matches `"ID"` | Nit | Fixed: it matches the full `validate_id` message, and the path-only case matches exactly |

The review half of LR-001's L-3 precondition was met at `4ff0d432`, and the re-check carried the accept verdict to
`dff6f2b4` (addendum §11).

**PR #408 bot comments on `4ff0d432` and `dff6f2b4`**, disposed in revision 4:

| Comment | Disposition |
|---|---|
| CodeRabbit (Major): the ledger root's ancestors are not scanned, so a scratch ledger nested inside the Gate 6 store passes | Fixed. The ancestor scan covers the ledger root too. Tested by calling `refuse_gate6_lock_roots` directly. The harness's authority root is a sibling of the ledger root (`factories.py`), so its own ancestor scan reaches the ledger root's parents, and a test through `submit` would mask the gap |
| CodeRabbit (Minor): a manifest path that is a directory or a dangling link is skipped by `is_file()` | Fixed: `os.path.lexists`, so the loader reads it and refuses it as unreadable. Tested with a directory; a dangling link needs symlink privileges on Windows |
| Codex (P2): `ars legacy status` and `show` bind through `EventLedger(create_directories=True)`, so a read-only query recreates a missing event directory and reports an empty ledger | Fixed. `_verified_ledger(read_only=True)` refuses a store whose project event directory is missing and binds with `create_directories=False`, as `store/current_binding.py` does. `ars legacy` always binds read-only, which the CLI test asserts; other callers are unchanged |

Each fix, reverted alone, fails its test (scratch mutation script). Revision 4 changes code, so the accept verdict
needs the reviewer's focused re-check at the new head before L-3 relies on it.
