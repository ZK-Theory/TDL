# WP9.3-1: LR-003 to LR-015, the reader, the segmenter and the W9 identity checks

**Date:** 2026-11-09<br>
**Status:** Revision 1, on branch `pipe/w9-wp9-3-1-observation-reader`, for independent review. Not merged. D-4 is
re-accepted by Stephen in the merge-queue entry, and WP9.3-1 merges alone (note §16).<br>
**Package:** 06v WP9.3, the first of its two PRs (P-081 item 1). The design note is
`transition/w9/wp9-3-design-note.md`, revision 14, merged as `2d9aeddc` (PR #411).<br>
**Authority:** P-080 (WP9.3, note first; the code with its own independent review, CodeRabbit, D-4 and Stephen's
merge) and P-081 (owner points A to M with their dated amendments). Issue #415, option C.<br>
**Base:** `main` at `2d9aeddc`.<br>
**Not authorized (P-080):** WP9.4 to WP9.7; live operations L-0 to L-5, the D-7 export included; a real store, genesis
or a grant on one; any legacy write. Every store in this package's tests is a scratch store under `tmp_path`, and every
source a scratch Git repository under `tmp_path`.

## 1. What landed

| Design note | Code |
|---|---|
| §2.2, §2.3, §15 | `legacy/routes.py`: LR-003 to LR-015 routed (14 routed, 47 deferred). Genesis guard 8 (`validate_legacy_route_registry`) checks an exact partition; the counts are pinned in the route test |
| §4.1, §4.2, §5.2, §5.3 | `legacy/records.py`: the content hash (N-2), the pre-assigned ref hash (owner point M), the derived review context and attempt IDs, the observation subject digest and `record_id` with its count `n`, the signature ref derivation with `#<n>` |
| §4.3, §9.1 | `legacy/identities.py`: the created-ID table (`NON_W9_ID_FIELDS`), W9's fixed identities from the code constants, the collision check the W11, generic and T2 writers share, and the read-only pre-pin check over one `LedgerSnapshot` (`check_w0_pin_candidate`, `select_w0_signature_ref`) |
| §9.1, §11.3 | `legacy/accepted_w9.py`: `ACCEPTED_W0_SIGNATURES` and `ACCEPTED_CL_EXPORT`, both empty, read at call time |
| §4, §5, §6, §9, §14 | `legacy/replay/reducers.py` and `driver.py`: the per-transaction step factored out (`apply_transaction`); the replay checks of §6.2 for LR-003 to LR-015; N-2 in every record reducer; reservations and their conversion; the cross-partition claim refusal; the lapse rule; approve-only satisfaction; §5.5's distinctness; G5 and F-8's first limb; the observation's selector, signature, qualifier and precedence checks; staleness from recorded observations; a supersession of a missing record refused |
| §7 | `legacy/reader.py`: the read modes, the handle-bound protocol on `store/lock.py`'s anchors, the `CONVENTIONS.md` vault alias refused, the importer identity, the fixed non-inferences |
| §8.1 | `legacy/segmentation.py`: `w9-segmentation/1.0.0` for the runtime; `tools/w9_segmentation.py` untouched |
| §8.2 | `legacy/json_families.py`: template §3 rule 1 parsing and rules 2 to 5 |
| §11.1 | `legacy/evidence.py`: the registration manifest and the detector control outputs, read from Git at `git_head` |
| §5.1, §6, §7.2, §7.3 | `legacy/preparers.py`: the seven commands' preparers, the window re-reads, the frozen-copy check through the generic projection |
| §5.3, §5.5, §6, §9.1 | `legacy/runtime.py`: the subject table, the generic projection returned by the pre-command replay, the shadow run, the owner rule, the re-reads and the binding recheck inside the writer lock, each W2 event under its producer binding |
| §4.3, §9.1 | `discovery/routes.py`, `discovery/runtime.py`: the symmetric W9 identity check and the in-lock binding recheck |
| §4.3, §9.1 | `command/service.py`, `command/t2.py`: the same identity check at both generic append sites; the binding recheck at every `CommandService` lock site that can append |
| §9.1 | `discovery/spec.py`: `SpecCoordinator` passes `binding.revalidate` to `DiscoveryRuntime` and to its `CommandService` (§3 item 2) |
| §9.1 | `store/binding_service.py`: the checked ledger head, beside the intent, compared under the advance's writer lock |
| §9.1, §13 | `cli.py`: `ars legacy submit`, `ars legacy observation-id`, `ars store advance-binding --expected-ledger-head`, and `ars submit`'s recheck (§3 item 3) |
| §16 | `schema_registry.py`: seven command rows and four producer rows; `authority.py`: the seven commands' entries |

## 2. Fixed values

- **Command payloads** (§5.1), which the note names by content: see `legacy/preparers.py`'s module docstring.
- **Pre-assigned refs** by kind: a registration's `registration_decision_ref`; a membership table's `review_ref` and
  `acceptance_decision_ref`; an inventory's `independent_reproduction_ref` (a `rev_`).
- **Expected stream versions:** 0 for every claiming step (proposal, review request, Decision proposal, observation),
  1 for a verdict, a resolution and LR-014.
- **The detector list** (W9 §4.4): `main_ruleset` with a `recorded_read`, and `post_merge_first_parent`,
  `vault_computational_log` and `conventions_repository_check` each `watched_to_fail`.
- **The evidence files:** `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/1`) and
  `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`). WP9.5 writes them.
- **The reader:** `research_system.legacy.reader`, version `1.0.0`; the importer hash covers `reader.py` and
  `segmentation.py` at `git_head`.
- **The census:** 273 rows, SHA-256 `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712`.

## 3. Owner rulings made during the code (2026-11-09)

Each was a departure the code needed, brought to Stephen first.

1. **The resolution's `governing_evidence_refs`.** Note §5.2 said "equal to the proposal's", which leads with
   `W9:LR-004` or `W9:LR-009`. The unchanged `assign_row` (`legacy/routes.py`, kept by note §3 row 20) assigns a
   `DecisionResolved` by its one `W9:` ref, so it would have refused the resolution as a row of another command.
   Stephen chose "Option A (row swapped)": the proposal's subject refs with the row ref replaced by the resolution row
   (`W9:LR-005`, `W9:LR-010`). Replay requires exactly that list.
2. **`discovery/spec.py` joins the boundary.** The W11 in-lock recheck needs the binding where production builds
   `DiscoveryRuntime`, which is `SpecCoordinator._discovery`. Stephen chose "Extend to spec.py (Recommended)": two
   constructor arguments, in `_discovery` and `_command_service`, and nothing else in that file.
3. **`ars submit`'s recheck.** Note §9.1 has the CLI pass `CommandService` a binding check where `ars submit` builds it,
   but `ars submit` binds through `ControlBinding.load(--config)`, which has no current binding. Stephen chose "Recheck
   if foundation-named (Recommended)": when the canonical foundation names the configured store, `ars submit` loads its
   current binding (refusing one that does not admit) and passes `revalidate`; a store the foundation does not name is
   local administration and gets none, the recorded `--config` known limit.

These amend P-081 items 3 and 10 in substance; the merge-queue entry should record them.

## 4. Interpretations the reviewer should check

1. **The created-ID table's reach.** It classifies every payload field whose pattern is a W9-claimable kind (`obj_`,
   `rev_`, `dec_`). An ID of any other kind has another prefix and can never equal a W9 identity. W11's `E:` events
   are persisted under `ars://core/event` with no per-type payload schema, so the schema walk cannot reach them; the
   table lists every event type Discovery's reducer registry handles, with the fields its reducer keys a new aggregate
   by, and a test fails on a registry type the table omits. §18's question applies: whether each class is right.
2. **Replay's cross-partition check also covers W9's fixed identities** when the ledger holds a W9 event: a non-W9
   event on `CATALOGUE_STREAM_ID`, a reserved ID or a pinned ref refuses the ledger. So the pre-pin check's replay part
   catches a non-W9 claim of the candidate too, besides the scan (the note expected the scan alone to).
3. **WP9.3-1's full checks run for its own rows only.** The rows of later packages keep WP9.2's reducer rules plus the
   cross-cutting ones (N-2, identity claims, foreign IDs, pinned IDs, supersession of a missing record). Their packages
   add theirs.
4. **LR-014's actor.** Replay requires LR-014's actor to be the inventory's observer (the annex's `eligible_actor`).
5. **An inventory row's selector kind** is enforced by the record schema inside the same replay step, so no reducer
   check repeats it.
6. **`non_inferences`** are read-derived (§7.4's fixed strings per kind), so an observation payload may not supply them.
7. **An `inventory_item` observation** re-segments the observed bytes and requires the recorded inventory's rows.
8. **W9-T4's "summary W₂ family unverified"** is carried as a `stale_projection_of` qualifier on the whole-file
   observation, since a whole-file observation has exactly one family.
9. **The runtime-construction census** checks that each allowed construction passes `binding_check=`, as the proxy for
   "takes its binding from a `VerifiedCurrentBinding` that `load_current_binding` returned".
10. **The lock-site census** counts the `CommandService` methods that hold the control-root writer lock:
    `_submission_lock`, `with_locked_authority` and `_recover_scoped_activation_markers`.
11. **The grant-free census** derives the generic command types from `_build_event`'s dispatch and T2's set, minus
    `_AUTHORITY_COORDINATED_COMMAND_TYPES`: `RecordProviderReceipt` and `VerifyEvidenceDeletion`. Only the second can
    take a W9-claimable ID (its target stream is the caller's).

## 5. D-4 (note §16)

| Identity | Before | After |
|---|---|---|
| Runtime-binding census | 262 rows, `3d6ae37aba22f58e22d334745dfb0f66fa9f80a4a85c7a9fd633eb24963e9f06` | 273 rows, `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712` |
| 06h manifest YAML | blob `adbb334f0cd08d0ca0ceaed34d43018abf2f119d` | blob `4c8950421d3a9f25da7cf4b657a358536df42332`, SHA-256 `7b6accbc38792fc707f0dde9574a02db1295189db39ee8683f518a945b05fb24`, 6,343 bytes: the count and digest only; the append sites are unchanged |
| `test_wp6_1_06h_append_path_closure.py` | blob `922ae844cf7500484f11c1fe2f736d1da4681252` | blob `559d684a5d78abc285ce9b50dd23ce071aad32c5`, SHA-256 `33ef58d3828e757f774dd8bd705ac392c2e3f8ec0391dab0f14a8b6643d7b3da`, 26,480 bytes |
| Append-site classification | | unchanged |
| Command and event schema trees | | unchanged: no core schema changes |
| `test_schema_registry.py` count pin | 262 | 273 |

The merge-queue bytes are the ones to accept.

## 6. Tests

| File | What it covers |
|---|---|
| `contracts/test_w9_legacy_routes.py` | The seven command and four producer bindings, the four unbound W9 commands, the 14/47 partition and its tags, guard 8's missing, overlapping and untagged controls |
| `contracts/test_w9_wp9_3_censuses.py` | The runtime-construction census (positive on the tree; direct, alias, `partial`, `getattr` and subclass fixtures fail; an allowed site without its binding check fails); the lock-site census and its fixture; the grant-free census and its fixture; the created-ID table's coverage over every core, T2 and live-issue event schema, with a failing fixture; every Discovery registry event type listed; the bootstrap's IDs disjoint from W9's |
| `integration/test_w9_wp9_3_replay.py` | The whole flow (registration, membership table, inventory, an observation of each selector kind) through the four public replays; 99 forged-ledger controls, each asserting its message: N-2, pre-assigned refs, the W2 fields of §5.2 one by one, cardinality, W9-C20 to W9-C22, lapse, F-8, cross-partition claims in both orders, the observation ID, A then B then A, pins and the cross-pin control, W9-T1, T3, T4, T13, T22, the registration and inventory rows |
| `integration/test_w9_legacy_replay.py` | WP9.2-2's forged-ledger tests rebuilt for N-2 and WP9.3-1's rows. C1 and C2 remove their production row inside the test (§17, m-4). G5's equality control runs on LR-050 → LR-054, where it is still the refusing layer; the LR-014 reducer's own check is unit-tested |
| `integration/test_w9_wp9_3_runtime.py` | Through `submit`: the whole flow and the four replays; W9-C11 for all seven commands; the deferred LR-023 through a bound command; the owner rule; preparer-set fields; the shadow step; the observation ID and its grant (another selector, `n` moved); the frozen-copy seam end to end; a replaced file; W9-T6; the O-33 gap; W9-T11's reader half; W9-T2 and W9-T4 on fixture copies |
| `integration/test_w9_wp9_3_writers.py` | W9 identities refused at the real W11, generic and T2 writers before and after W9 genesis; the in-lock recheck in all three runtimes and on `with_locked_authority`; the pre-pin check's collision, re-derivation and single snapshot; the CLI on Gate 6 and nested roots and on a valid scratch store; `observation-id` writes nothing and prints the preparer's ID |
| `integration/test_w9_wp9_3_binding_head.py` | The head compare (match, moved, resumed after its own event, resumed after another writer, malformed) through the service and the command; the pin release through `load_current_binding` itself; a pin committed in place refused |
| `integration/test_w9_wp9_3_grant_fence.py` | The grant fence on the predecessor commit's own package: revoked and expired refuse a paused W11 submit, live appends |
| `unit/test_w9_runtime_segmentation.py` | The contract's vectors against both implementations; the differential test (seed 20261109, 1,500 inputs, seven selector calls); the reference tool's blob and that no runtime module imports it |
| `unit/test_w9_json_families.py`, `unit/test_w9_reader.py`, `unit/test_w9_evidence.py` | §8.2's vectors; the read modes and handle-bound refusals; the evidence formats |
| `fixtures/w9/` | The W9-T2 and W9-T4 fixture copies with their manifest; a test re-derives each blob |

## 7. Verification

Run on the operator machine (Windows, Python 3.13) on the tree of the commit that adds this record, 2026-11-09 to
2026-11-10. Every store is a scratch store under `tmp_path`.

- **Targeted regression** (39 files: every W9 file, every file in §6, the generic and T2 runtimes and contracts, the
  SPEC, artefact and store-binding suites, the schema registry and the 06h smoke test): **1,256 passed, 1 skipped**,
  in 25,442.8 s (7 h 04 min), one process. The skip is the existing skip in `test_spec_source.py`.
- **W11 suite** (unchanged by this PR, P-081 item 10's pins): 100 passed, 33 min 23 s, against 30 min 31 s on the
  predecessor (+9%).
- **`test_spec_source.py` alone**, this tree against `main` (`44b6f2b5`), both on the same machine, run back to back:
  10 passed, 1 skipped, 1 failed in 646.5 s, against the same result in 540.4 s on `main` (+20%). The failure,
  `test_remote_fetch_with_master_branch` (`'unavailable' == 'resolved'`), fails identically on `main`; it is a
  local-environment failure in Git source resolution, which this PR does not touch, and it passed in the targeted
  run above.
- **Mutation script** (scratch, not committed, as WP9.2-2's was; note §17): 69 mutations, each weakening one new guard
  alone, every one caught by an executed test failure; the worktree restored byte for byte after each. The first run
  missed two, both script faults: the lapse fragment occurred three times (retargeted to `_open_proposal`'s check), and
  the frozen-copy mutation weakened the ref check while the test exercised the bytes check, which its message
  alternation hid. The runtime test now asserts the bytes message alone, and both mutations are caught.
- **Census pins:** the 06h census at 273 rows and the digest in §5; `test_schema_registry.py` at 273.
- **Ruff:** check and format clean on every file this PR changes; pre-commit ran on every commit.

**Runtime growth, escalated, not accepted (the dispatch brief: a growing test runtime is escalated):**
- The SPEC suites are slower by about a fifth (measured on `test_spec_source.py`). The likely cause is the in-lock
  `revalidate` (P-081 item 3, note revision 11) re-running the binding chain's Git checks on every `CommandService`
  submission. The heaviest SPEC tests now take 15 to 20 minutes each (`test_spec_spike_outcome.py`, up to 1,228 s).
  This was not profiled further. Caching the binding check per ledger head, or measuring every SPEC file on both
  trees, is a decision for Stephen.
- `test_w9_wp9_3_binding_head.py` takes about 10 minutes, mostly from real binding-chain fixtures.
- `tools/research_system_durations.json` gives the SPEC files 10 to 40 s of weight against several minutes measured. The
  CI shard balance should be refreshed whatever the decision.

## 8. Not in this PR, and obligations

- **WP9.3-2** (note §2.3): LR-016 to LR-020, the ownership list, the export reader and recheck, the `.apm/` inventories,
  O-25, O-32, O-37, and the WP9.3-2 halves of the O-33 controls.
- **For the independent review** (P-080; owner point I; note §15, §18, §19):
  - re-implement `w9-segmentation/1.0.0` from the contract and reproduce every vector, as the session independent of
    the contract's author and of this implementer;
  - answer §18's created-ID question for each entry of `NON_W9_ID_FIELDS`;
  - re-verify the genesis path at this head, since guard 8's input changed;
  - re-verify the W11 pins: the W11 catalogue, schemas, bindings and census are unchanged.
- **For the L-3 checklist:** record which review verified the genesis code at the checkout L-3 runs from (this PR's,
  or WP9.3-2's). The first W0 pin lands before W9 genesis on any store.
- **For a later pin's checklist:** the grant-free types, `RecordProviderReceipt` and `VerifyEvidenceDeletion`, are its
  known limit; `--expected-ledger-head` is required for a pin release.

**Test gaps recorded, not closed:**
- No valid T2 command names an `obj_`, `rev_` or `dec_` ID, so the T2 site's control injects one through `_events_for`.
- The W11 created-ID control uses a candidate (`obj_`); a W11 review request whose `new_review_id` is a W9-reserved
  `rev_` is not run through `DiscoveryRuntime`, because the W11 review flow needs a full candidate lifecycle.
- The pre-pin check's collision control derives an `obj_` candidate, which the harness's writers can mint.
- The CLI's valid-store tests stub `load_current_binding`; the loader itself is exercised by the pin-release tests.
- The in-lock recheck controls raise from the binding check, as `revalidate` does after an advance; that
  `revalidate` refuses after an advance is shown separately on the v1.2 fixture.

## 9. Review dispositions

None yet.
