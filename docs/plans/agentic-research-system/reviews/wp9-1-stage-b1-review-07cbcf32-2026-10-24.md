# WP9.1 stage B1 review at `07cbcf32`: implementation conformance

**Date:** 2026-10-24<br>
**Subject:** W9 WP9.1 stage B1, the single commit `1024ed00..07cbcf32` on `pipe/w9-wp9-1-catalogue`. It changes 9
files, adding 2,438 lines and removing 22.<br>
**Mode:** Independent adversarial review (`adversarial-design-review`, implementation-conformance mode). The code
is the artefact, and the accepted owner text is the set of claims checked against it. The reviewer did not author
this work and edited nothing except this file.<br>
**Owner text checked against:**
- `transition/w9/wp9-1-stage-b-design-note.md`, revision 3 (confirmed), §§3 and 6;
- `transition/w9/wp9-1-catalogue-owner-annex.yaml`, blob `d8fbda41`, SHA-256 `36a3d1ac…3536fc`, 61 rows;
- P-069 to P-073 in `03-decisions-and-open-questions.md` (lines 4392–4637);
- the review chain `reviews/wp9-1-stage-b-note-*.md` and the reconciliation;
- the W11 precedent, `tools/verify_w11_materialization.py` and `tests/research_system/contracts/test_w11_expected_catalogue.py`.

**Known limit (P-058):** every review in this chain, this one included, runs on one model family. This is recorded
as a limit, not as a finding.

## Executive verdict

**`rework_required`, scoped to the verifier and its test.**

The schema half of B1 conforms:
- the generator;
- the 19 schemas;
- the bootstrap contract's family list;
- the stage A test's 66 controls.

Every note §3 schema change is present. The W9-C rule is encoded correctly as `if`/`then`/`else`. The new record and
the revision import fit P-072 items 3 and 5. The 19 `$defs` blocks are identical, `--check` reproduces every schema
byte for byte, and nothing reaches beyond the named files.

The verifier half does not yet do the job P-072 item 6 and note §6 give it, which is to be the mechanical check
behind Stephen's O-8 acceptance:
- It checks five top-level catalogue keys and the rows, and nothing else. A schema-invalid catalogue with a
  fabricated `content_hash`, fake schema source rows and fake owner identities exits 0 (**B-1**).
- It reads the annex at whatever commit the catalogue names. A catalogue built against the superseded pre-fold annex
  (`8a0d68fc`) exits 0. That annex still carries the confirmation's c-1 Major (**B-2**). This reopens the original
  review's M-2 failure scenario one level down: the catalogue's author now picks the expected side.

Both fixes stay inside `tools/verify_w9_materialization.py` and its test. Neither needs a schema change, so B2's pin
at B1's main commit is unaffected.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 2 | B-1, B-2 |
| Major | 2 | M-1, M-2 |
| Minor | 8 | m-1 to m-8 |
| Info | 8 | i-1 to i-8 |

## Blocking

### B-1 (Blocking). The verifier certifies a catalogue whose non-row fields are unchecked

**Claim.** `compare_catalogue` checks only five things:
- `owner_annex_identity`;
- `global_preconditions`;
- `owner_row_count`;
- `owner_row_range_hash`;
- the rows.

It never validates the catalogue against its schema, never recomputes `content_hash`, and never checks
`schema_source_rows`, `owner_spec_identity`, `owner_plan_identity`, or the record, project and actor identities.

**Evidence.**
- `tools/verify_w9_materialization.py:34` defines `CATALOGUE_SCHEMA`, and nothing in the verifier uses it. Only the
  test reads it (`test_w9_expected_catalogue.py:121-124`).
- `tools/verify_w9_materialization.py:223-255` is the whole catalogue comparison.
- Annex `derivation_rules` item 6: "a content hash is SHA-256 of canonical_bytes over the record without
  content_hash (the W11 rule)". The verifier does not apply it to the catalogue.
- P-072 item 6 and note §6 say B2 adds the catalogue "with every schema source row pinned at B1's main commit". No
  code checks this.
- The test's own fixture shows the gap. `test_w9_expected_catalogue.py:87-117` builds:
  - an owner spec at `docs/w9.md` with zero hashes;
  - a single schema source row `x.schema.json` with zero hashes;
  - `content_hash` set to 64 zeros.

  `test_matching_catalogue_verifies_clean` (line 155) then asserts that this catalogue verifies with no problems.
- In W11 these are checked in `verify_expected_catalogue` (`tools/verify_w11_materialization.py:376-432`):
  - schema validation (`verify_materialization_document`);
  - pinned record, project and actor IDs;
  - source refs;
  - the owner spec identity, derived from Git;
  - `content_hash` recomputed with `canonical_bytes`, excluding itself;
  - `schema_source_rows` against "the closed foundation byte manifest".

**Probe P1** (in memory, catalogue written only to the scratchpad):
- A catalogue holding only the five compared keys has 12 schema errors, and `compare_catalogue` returns `[]`.
- Adding a bogus `content_hash`, a bogus `owner_spec_identity` and an unknown top-level key still gives `[]`.
- `main(["--catalogue", <that file>])` prints `annex and catalogue: 61 rows at 07cbcf32; 0 problem(s)` and returns
  0.

**Failure scenario.** In B2 the author generates the rows with `expected_rows`, which is correct by construction. The
schema source rows, however, are pinned at a branch commit, or at a schema blob that B2 changed. The `content_hash`
is stale after a late edit. Or the catalogue carries a field the schema forbids. The verifier runs green, and note §6
lists "the verifier run green" as B2's completion evidence. O-8 then rests on a green that covers the rows and none
of the identity fields. The envelope's `catalogue_identity` and `schema_identities` will be checked against those
fields at genesis.

**Impact.** The validity of the accepted catalogue's identity binding. It also loses the W11 parity that the note
claims ("as W11's verifier does", note §3).

**Disposition.** Fix now, in B1.

**Proposed change** (`tools/verify_w9_materialization.py`, with a negative control for each):
1. Validate the catalogue against `w9-schema-catalogue-content`, with the format checker, read at the pinned schema
   commit (item 3), before any comparison.
2. Recompute `content_hash` as `sha256(canonical_bytes(catalogue without content_hash))`. Use
   `research_system.canonical.canonical_bytes`, as W11's verifier does at line 24; the import is read-only.
3. Derive the expected `schema_source_rows` from the 19 family files at a single commit $C$, and require all of:
   - every row names $C$;
   - $C$ is an ancestor of `origin/main`;
   - each blob at $C$ equals the blob at `HEAD`, so a later schema edit is a new identity and not a silent pass.
4. Derive `owner_spec_identity` and `owner_plan_identity` from the bootstrap contract's `source_spec` and
   `source_plan` tuples, which are already pinned and tested (`test_w9_contract_materialization.py:354-366`).
5. Either pin the catalogue's `record_id`, `project_id` and `created_by_actor_id` as W11 does (lines 39-41), or
   record why W9 leaves them free.
6. Controls: one mutation per item above. Each must be refused for its own reason, matched on the message.

**Affects:** P-072 items 6 and 7; note §§3 and 6; O-8; WP9.2 genesis (`import-accepted-w9-catalogue-genesis`).

### B-2 (Blocking). The catalogue chooses the annex commit the verifier compares it against

**Claim.** The verifier takes the annex commit from the catalogue under test. It pins no annex blob or SHA-256 of
its own, and does not require the commit to be on `main`. So a catalogue author can choose the expected side.

**Evidence.**
- `tools/verify_w9_materialization.py:280`:
  `commit = catalogue["owner_annex_identity"]["git_commit"] if catalogue else args.annex_commit`.
- `compare_catalogue` (line 237) then requires `owner_annex_identity` to equal the identity at that same commit, a
  check the catalogue satisfies by construction.
- W11 pins its expected side in the verifier itself (`tools/verify_w11_materialization.py:30-36`):
  - `W11_SPECIFICATION_COMMIT`, `_BLOB`, `_SHA256` and `_BYTES`;
  - the exact owner-row set `_OWNER_ROW_IDS` (lines 74-76), independent of the owner table.
- The original M-2 disposition (`reviews/wp9-1-stage-b-note-review-0cf8acd3-2026-10-24.md:212-220`) reads: "The stage
  B verifier derives expected rows from that blob at its pinned commit, as W11's does."
- Note §6: "each row's `owner_annex_ref` pinned to the annex at its main commit". There is no ancestry check.
- Three annex rules are enforced only by tests, and only on the `HEAD` annex, never on the annex the catalogue pins:
  - the exact command-type set (`test_w9_expected_catalogue.py:136-147`);
  - the record-family coverage;
  - "resolved by Stephen ⇔ submitted by Stephen" (lines 150-152).
- `committed_record_schema_ids()` (line 258) reads the working tree, while the annex is read at the pinned commit, so
  the two sides of that check come from different trees.

**Probe P2.** A catalogue was derived from the annex at `8a0d68fc` (blob `4e648b7f`). That is revision 3 before
Stephen's fold of c-1 to c-4. Rows LR-016, LR-020, LR-035, LR-054 and LR-055 differ from `HEAD`. Run as
`main(["--catalogue", <scratch file>])`, it printed `annex and catalogue: 61 rows at 8a0d68fc; 0 problem(s)` and
returned 0. That annex still holds:
- c-1's Major: LR-016's vacuous stop rule;
- c-2: LR-055's dropped fixtures;
- c-3: LR-020's split projection and reducer names.

**Failure scenario.** This is the original M-2 scenario moved one level down. On B2's branch the author edits an
annex row, for example LR-016's stop rule or a row's `authority_subject`. They commit it and pin the catalogue to
that commit. The verifier passes, because both sides now come from the edited annex. After a squash merge the pinned
commit is not even on `main` (the P-069 item 1 rationale), yet the verifier never asks. The only remaining control is
Stephen comparing the annex blob by eye at O-8.

**Impact.** Self-definition of the acceptance bar ("Foundation" in the skill's lane 2). It defeats the
independent expected side that the review chain's M-2 fix was meant to establish.

**Disposition.** Fix now, in B1. Git blob identity survives a squash merge, so B1 can pin it before B1's main commit
exists.

**Proposed change.**
1. Add verifier constants `W9_ANNEX_BLOB = "d8fbda416b016f5e19c03689f336caff3166d0d9"` and
   `W9_ANNEX_SHA256 = "36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc"`, with its byte length, and
   `W9_OWNER_ROW_IDS = LR-001..LR-061`. Then:
   - require the catalogue's `owner_annex_identity.git_blob` and `file_sha256` to equal those constants;
   - require its `git_commit` to resolve to that blob at `ANNEX_PATH`;
   - require that commit to be an ancestor of `origin/main`, using `merge-base --is-ancestor` as W11's `_is_ancestor`
     does at line 1079.

   Any later annex change is then a reviewed verifier change, consistent with note line 16: "every row change is a new
   catalogue identity and a new acceptance".
2. Move the three test-only rules into `check_annex`, so they apply to the annex the verifier actually reads.
3. Read the schema `$id` set at the pinned schema commit (B-1 item 3), not from the working tree.
4. Without `--catalogue`, verify the pinned blob, not `HEAD`.
5. Controls:
   - the probe-P2 catalogue at `8a0d68fc` is refused;
   - a catalogue naming the right blob at a commit not on `origin/main` is refused;
   - an annex whose command-type set differs is refused.

**Affects:** P-072 item 6; note §§3 and 6; reconciliation M-2; O-8.

## Major

### M-1 (Major). A missing catalogue path is a silent green

**Claim.** If `--catalogue` names a path that does not exist, or if the default catalogue is absent, the verifier
silently falls back to an annex-only run and exits 0.

**Evidence.** `tools/verify_w9_materialization.py:278-279`. The run
`verify_w9_materialization.py --catalogue does/not/exist.json` printed `annex: 61 rows at 07cbcf32; 0 problem(s)`
and exited 0.

**Failure scenario.** In B2 the catalogue path is mistyped in a command, or the catalogue is renamed. "The verifier
run green" (note §6) is then reported with no catalogue checked. This is a silent-absence failure.

**Disposition.** Fix now. If `--catalogue` is given and missing, exit 1. Add a mode flag, such as
`--require-catalogue`, for B2 and later. Add a control for each.

**Affects:** note §6 (B2 completion evidence).

### M-2 (Major). The per-row W9-C01 and W9-C03 controls are claimed but not realised

**Claim.** The owner text and every row name per-row tests. B1 implements one aggregate positive test and a mutation
test on a single row. No test node carries the identities the catalogue will pin.

**Evidence.**
- Note §3 (lines 84-86): "its tests compare row for row (W9-C01, W9-C03), as W11's verifier does".
- Annex `catalogue_tests`: W9-C01 is "per row: W9-C01-LR-nnn"; W9-C03 is "W9-C03-LR-nnn-owner-row-mutation".
- `test_w9_expected_catalogue.py:155-156` is one aggregate test.
- Lines 159-169 mutate only `owner_contract_rows[19]` (LR-020).
- W11 parametrizes each control over every row, with pytest IDs `W11-T01-OR-nnn`, `W11-T03-OR-nnn-owner-row-mutation`
  and `W11-T11-OR-nnn` (`test_w11_expected_catalogue.py:47-96`).
- The positive test is circular. `_catalogue()` (line 77) and `compare_catalogue` both call `expected_rows`, so the
  test proves that `derive_row` agrees with itself. No literal check pins any derived value.

**Mitigating evidence (probe P6).** The verifier itself is sound here:
- every one of the 61 × 24 single-field mutations is detected;
- swapping two rows is detected;
- by independent reading, `derive_row` implements each derivation rule. That includes the row hash, with
  `source_refs`, sorted keys, no whitespace, and `ensure_ascii=False`, which matches `research_system/canonical.py:40-48`.

So this is a test-binding gap, not a verifier defect.

**Impact.** The O-8 catalogue will pin 122 test identities, `W9-C01-LR-nnn` and `W9-C03-LR-nnn-…`, that name no test.
The acceptance envelope's `binding_test_identities` then pins a test file that does not contain them.

**Disposition.** Fix now:
- parametrize the positive and mutation controls over the annex rows, with W11's ID scheme;
- add one golden literal check of a derived row, for example LR-020's `complete_write_set` and `owner_annex_ref`
  shape, so the derivation is not proved only against itself.

W9-C11 (retry) is a runtime test. Record it as a WP9.2 obligation (i-3).

**Affects:** note §3; annex `catalogue_tests`; envelope `binding_test_identities`.

## Minor

**m-1. YAML duplicate keys are silently last-wins.**
- The verifier loads the annex with `yaml.safe_load` (line 118).
- Probe P3 put a second key in LR-005 (`resolver: stephen`, then `resolver: none`). `check_annex` returned `[]`.
- A strict loader refuses it. The committed annex passes a strict loader.

The reviewed text would show both values while the catalogue silently takes the second. The fix is a loader that
refuses duplicate keys, plus a control.

**m-2. `check_annex` leaves some row rules unchecked.** Probe P7 showed `[]` for each of these:
- `resolver: anyone`, `projection_targets: ["not a P token"]` and `reducer: nope`;
- a row whose `record_schema_id` is `ars://legacy/w9-materialization-bootstrap-contract`, a non-record schema;
- `catalogue_tests` with W9-C24 deleted everywhere, since `known_c` is read from the annex itself;
- rewritten `derivation_rules` and `suspension_rule` text, which no code reads.

`record_schema_version` is also not checked against the schema. Most of these close once B-1, which validates
derived rows against the row schema, and B-2, which pins the annex blob, land. The remaining fixes:
- pin the declared test set to P-073 item 1 (W9-C01, W9-C03, W9-C11, W9-C20 to W9-C25);
- restrict `record_schema_id` to the 14 records plus the two import schemas.

**m-3. `owner_row_range_hash` has a new, undefined meaning.**
- The verifier defines it as the hash of the catalogue's own rows (line 243). That is a circular checksum.
- W11 defines it as the hash of the sorted owner row IDs (`verify_w11_materialization.py:428-431`, "non-circular").
- No W9 owner text defines either reading (searched: the note, the annex, 06v, W9 and the review chain).
- The envelope's `owner_row_multiset_hash` is also undefined.

Define both in the note, or in a register line, and make the verifier use that definition.

**m-4. The revision import cannot record "superseded by a named revision row".**
- LR-002's precondition reads "every v1 row unchanged or explicitly superseded by a named revision row".
- `import-accepted-w9-catalogue-revision` carries only `superseded_owner_row_ids` (`tools/w9_schema_gen.py`, revision
  block).
- The import runs under v1's LR-002 row and its pinned 1.0.0 schema, so a mapping field cannot be added later without
  a new v1 identity.

Either add a superseded-to-replacing map now (an ordered array of `{superseded, replacing}` pairs), or record that the
revision catalogue itself carries the mapping and that the importer reads it there.

**m-5. The acceptance envelope does not name the annex directly.**
- P-072 item 6 says O-8 "names the catalogue, and the note's owner-annex blob, by main commit, blob and SHA-256".
- The stage A envelope schema has `catalogue_identity` but no annex identity (`w9_schema_gen.py`, envelope block).
- The annex is named transitively, because the catalogue's `owner_annex_identity` is inside the hashed catalogue
  bytes. That is cryptographically sufficient.

Stephen should confirm the transitive reading in B1, or widen the envelope in B1. Either way it must be settled
before B2 pins the schemas.

**m-6. Stale counts.** `tools/w9_schema_gen.py` lines 5, 6 and 1434 still say "17" schemas and "17 inlined `$defs`".
The family now has 19. This is editorial.

**m-7. B2's forward edits are not recorded.** When B2 adds the catalogue, three stage A artefacts contradict it:
- the contract's `forbidden` entry "expected catalogue instance"
  (`.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml:68`);
- its verification rule at line 39;
- `test_stage_a_materializes_no_catalogue` (`test_w9_contract_materialization.py:331-332`).

W11 left its contract text in place (`w11-materialization-bootstrap-contract.yaml:36, 109`), but the W9 test asserts
absence, so B2 must edit it. Name these edits in note §6, so that B2's diff is anticipated rather than overreach.

**m-8. Rough CLI edges.**
- `--annex-commit` is silently ignored when a catalogue exists (line 280).
- A catalogue that is not a mapping, or that lacks `owner_annex_identity`, raises a traceback instead of reporting a
  problem. It does fail closed.

## Info

- **i-1.** The row schema admits `W9-T0`, `W9-T24` and above, `W9-C26` to `W9-C29`, a multiplicity-`1` event with a
  condition, and a `logical_key` that differs from `payload_discriminant` (probe P5). Draft 2020-12 cannot express the
  last one. Each case is closed by the verifier's equality to the annex plus `check_annex`. No annex row has a `1`
  event with a condition.
- **i-2.** Annex `derivation_rules` item 5 says G1 to G5 are "not repeated per row". In fact G5 is restated in 10 of
  the 13 Stephen-resolved rows, and G1 in LR-001 and LR-002. G5's scope is otherwise consistent: the three Decisions
  that write no record (LR-022, LR-025 and LR-037) omit it. This is owner text, and B1 needs no action.
- **i-3.** Some rules are runtime obligations with no B1 artefact, and should go into the WP9.2 intake:
  - the record content-hash rule;
  - "created_at and created_by_actor_id from the proposal";
  - W9-C11 (retry);
  - W9-C20 to W9-C25 (behavioural).
- **i-4.** `canonical_json` re-implements `canonical_bytes` without its P0 value validation. The output is identical
  for the current annex. Importing `canonical_bytes`, as W11 does, removes the duplication (folded into B-1 item 2).
- **i-5.** The fixture and test ranges F-001 to F-038, S-001 to S-017 and W9-T1 to W9-T23 are verifier literals. They
  match `.research-system/evals/p0-coverage.yaml` and W9 §17 (W9-T23 at line 812).
- **i-6.** Under `python -I`, the venv resolves `research_system` to the main checkout. B1 changes nothing under
  `research_system/`, and main is B1's base, `5d325c5b`, so the test run is equivalent.
- **i-7.** W9 §9 item 5 also lists "any new qualifier" as a suspension trigger, and `suspension_rule` does not name it.
  A qualifier enters through an observation, so the "later observation" input covers it. This is noted for the owner,
  and is not a B1 finding.
- **i-8.** One model family (P-058).

## Attacks that failed (conformance confirmed)

| Brief item | Result | Evidence |
|---|---|---|
| 1. Row fields | All 24 note §3 fields are required, in the note's order | `w9_schema_gen.py` `OWNER_ROW` |
| 1. W9-C rule | `if` reason is null, `then` contains `^W9-T`; `else`, contains no W9-T and contains `^W9-C2`. Probe P5 refused all four violation shapes | schema `allOf` |
| 1. `0..n` | `when(multiplicity = 0..n)` requires a string condition. A null condition is refused (P5), and `check_annex` also refuses it (`test_a_conditional_event_needs_its_condition`) | |
| 1. `owner_annex_ref` row hash | It hashes the full annex row, including `source_refs` and the annex-stated `logical_key` and `receipt_identity`, with sorted keys and no whitespace. `ensure_ascii=False` equals `canonical_bytes` | verifier lines 81-83, 208-214 |
| 1. Derivations | `complete_write_set` is the event tokens, then the streams. `R:` + `logical_key`, and the three test-identity patterns, match the annex text exactly | verifier lines 198-214 |
| 3. New record | `adoption_ref` is a `recordRef` (`obj_`), and `successor_task_ref` is a `taskRef` (`tsk_`). Both are in `REF_FIELDS`, and `adoption_ref → legacy-adoption-decision` is in `RECORD_EDGES`. The closure test walks the schemas, so an omission would fail. The fields match LR-061 and W9 §9 item 1 ("the successor Task re-hashes it at use") | stage A test lines 137-138, 198; W9 §9 |
| 3. Revision import | Inert (`activation_status: not_executed`). It names the superseded catalogue and the revision envelope, refuses the Gate 6 store, and uses an `LR-` grammar for superseded rows. See m-4 | `w9_schema_gen.py` revision block |
| 3. Contract | Both families gained exactly the two new kinds. The contract's blob is pinned nowhere else (searched) | contract lines 58, 64 |
| 4. c-4 control | A row with no W9-T test and no W9-C2x test is refused | test line 200 |
| 4. Mutation detection | 61 × 24 single-field mutations, plus a row swap, all detected (P6) | probe |
| 5. Overreach | 9 files: the generator, 3 schemas, the contract, the stage A note, the stage A test, the verifier and its test. Nothing under `research_system/`, no catalogue, no envelope instance, no runtime code. Each file is within P-069 item 4, P-072 items 6 and 7, or P-065's docs and data | `git diff --stat 1024ed00..07cbcf32` |
| 6. Generator | `--check` exits 0 and compares bytes. All 19 `$defs` blocks are identical (19 files, 1 distinct block). The annex blob equals the working-tree bytes (LF, `eol: lf`) | commands below |
| Lint | `ruff check` and `ruff format --check` are clean on the four Python files | commands below |

## Decision audit

| Decision | Disposition | Note |
|---|---|---|
| P-069 item 1 (two PRs) | Keep | B1 adds no catalogue and no envelope |
| P-069 item 2 (no event schemas; rows name every event) | Keep | Every record kind has a creating `E:` token (probe). The WP9.2 condition stands |
| P-069 item 3 (restricted suffixes) | Keep | Unchanged. The new record carries hashes only, no paths |
| P-069 item 4 (boundary: test and generator) | Keep | Both stay non-runtime. The generator writes only its schema files |
| P-070 (supersession targets) | Keep | Unchanged. `adoption_ref` is not a supersession edge |
| P-071 items 1, 5 and 6 (row shape; `membership_author` and `requester`; W9-C rows) | Keep | Implemented |
| P-072 item 1 (W9-path review and decision rows) | Keep | Command-type set tested on `HEAD` only (B-2 item 2) |
| P-072 item 3 (14th record) | Keep | Conforms |
| P-072 item 5 (inert revision row) | Keep, amend | m-4 |
| P-072 item 6 (B1, then B2; O-8 names the catalogue and annex) | **Amend implementation** | B-1, B-2, m-5, m-7 |
| P-072 item 7 (verifier boundary) | Keep | Read-only and outside `research_system/`. B-1's `canonical_bytes` import stays read-only |
| P-073 item 1 (W9-C20 to W9-C25 and the W9-C rule) | Keep, harden | The schema and the verifier enforce the rule. The declared set is unpinned (m-2) |
| P-073 items 2 to 4 | Keep | Annex content. Not B1 code |
| Reconciliation M-2 (independent expected side) | **Reopened in implementation** | B-2, M-2 |
| Confirmation c-4 (verifier enforces the rule, with a negative control) | Closed | Test line 200 |
| P-058 (one model family) | Known limit | i-8 |

## Consistency matrix (invariant → enforcement → test)

| Invariant (owner) | Enforcement | Test | Gap |
|---|---|---|---|
| Catalogue rows equal annex-derived rows (W9-C01) | `compare_catalogue` | one aggregate test | M-2 (no per-row nodes) |
| Any one field mutation detected (W9-C03) | `compare_catalogue` | row LR-020 only | M-2 |
| Annex read at its accepted pinned commit (M-2 disposition; P-072 item 6) | the commit the catalogue chooses | none | **B-2** |
| Catalogue validates against its schema | none in the verifier | the test validates its own synthetic catalogue | **B-1** |
| Catalogue `content_hash` (annex derivation item 6) | none | none | **B-1** |
| Schema source rows pinned at B1's main commit (P-072 item 6) | none | none | **B-1** |
| W9-C rule (P-073 item 1) | schema `if`/`then`/`else`, plus `check_annex` | three annex controls | none |
| `0..n` needs a condition | schema, plus `check_annex` | one control | none |
| Annex without duplicate keys | none | none | m-1 |
| Declared W9-C test set is exactly P-073 item 1 | none (taken from the annex) | none | m-2 |
| Catalogue present when B2 claims green | none | none | M-1 |
| 19 schemas reproduced, one `$defs` block | generator `--check`; stage A test | yes | none |
| New record refs typed and in the edge graph | `REF_FIELDS` and `RECORD_EDGES` closure | yes | none |

## Revision plan

**Immediate corrections (author, on B1, before merge):**
- B-1 and B-2: pin the annex blob, SHA-256 and row-ID set, and check ancestry; validate the schema, `content_hash`,
  `schema_source_rows` and owner identities.
- M-1: fail on a missing catalogue.
- M-2: per-row controls with W11's ID scheme, plus one golden literal check.
- m-1, m-2, m-3, m-6 and m-8.
- m-7: name B2's contract and test edits in note §6.

Each correction ships with its negative control. A focused re-review should then run against the new head.

**Owner decisions (Stephen):**
- m-4: a revision map in the import schema, or the revision catalogue carries it;
- m-5: transitive annex naming in the envelope, or widen the envelope in B1;
- m-3: which `owner_row_range_hash` reading W9 adopts.

**Later-work dependencies:** i-3 goes into the WP9.2 intake (runtime derivation rules, W9-C11, W9-C20 to W9-C25).

## Residual risks

- The annex is now the single normative source. B-2's pin makes any annex edit a reviewed verifier change. Without
  it, the annex can drift on `main` after O-8 and nothing fires.
- B-1 item 3 ties the schema pins to `origin/main` ancestry. A shallow CI clone would then fail closed rather than
  pass. That is acceptable, and it is the same exposure W11 has.

## Commands run (read-only; probes from the scratchpad)

```text
git switch pipe/w9-wp9-1-catalogue                         # HEAD 07cbcf32 (worktree sweet-volhard-11c89d)
git log --oneline -4; git diff --stat 1024ed00..07cbcf32; git diff --stat 5d325c5b..1024ed00
git diff 1024ed00..07cbcf32 -- tools/w9_schema_gen.py .research-system/contracts docs/ tests/...test_w9_contract_materialization.py
git diff --name-only 5d325c5b..07cbcf32 -- research_system  # 0
git rev-parse {8a0d68fc,1024ed00,07cbcf32}:<annex>          # 4e648b7f, d8fbda41, d8fbda41
git rev-parse {5d325c5b,HEAD}:<bootstrap contract>; git grep <blob prefixes>   # pinned nowhere
git show HEAD:<annex> | sha256sum; sha256sum <annex>; git check-attr -a <annex>
python -I -m pytest tests/research_system/contracts/test_w9_contract_materialization.py \
    tests/research_system/contracts/test_w9_expected_catalogue.py -q -p no:cacheprovider -o addopts=""   # 115 passed
python -I tools/w9_schema_gen.py --check                    # exit 0
python -I tools/verify_w9_materialization.py                # 61 rows at 07cbcf32; 0 problems; exit 0
python -I tools/verify_w9_materialization.py --catalogue does/not/exist.json   # exit 0 (M-1)
python -I tools/verify_w9_materialization.py --annex-commit 5d325c5b           # traceback, exit 1 (m-8)
ruff check --no-cache <4 files>; ruff format --check --no-cache <4 files>     # clean
python -I <scratchpad>/probe_b1.py <repo> <scratchpad>      # probes P1-P7 (in-memory; files only in scratchpad)
python -I -c <$defs identity over 19 files; CR count; event/record coverage>
```

`python` is `C:/Users/steph/TDL/.venv/Scripts/python.exe`. `git status` was clean after every command.

## Change log

- Added this review file only. No other file was edited.
