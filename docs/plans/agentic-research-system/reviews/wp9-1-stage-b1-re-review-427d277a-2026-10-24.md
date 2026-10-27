# WP9.1 stage B1 re-review at `427d277a`: revision 2

**Date:** 2026-10-24<br>
**Subject:** B1 revision 2, the single commit `d6c969fa..427d277a` on `pipe/w9-wp9-1-catalogue`. It changes 9 files,
adding 817 lines and removing 306.<br>
**Mode:** A focused re-review (`adversarial-design-review`, remediation re-review). Each disposition's prescribed
mechanism is bound to code lines, and every control is attacked for whether it can fail for its stated reason. The
reviewer edited nothing except this file.<br>
**Inputs:**
- the review `reviews/wp9-1-stage-b1-review-07cbcf32-2026-10-24.md` (commit `d6c969fa`);
- the reconciliation `reviews/wp9-1-stage-b1-reconciliation-2026-10-24.md`;
- P-074;
- note §§3 and 6.

**Known limit (P-058):** one model family. Recorded as a limit, not as a finding.

## Verdict

**`accept_with_required_changes`.**

Both Blockers are closed:
- The verifier now pins the annex by blob, SHA-256 and size, and pins its row, command and test sets. Probe P2's
  pre-fold catalogue is refused.
- It validates the catalogue against its schema, recomputes `content_hash`, derives the schema source rows and owner
  identities, and pins the record identities.

M-1, m-1 to m-6 and the P-074 schema changes are closed. M-2 is substantially closed. The schema half has not
regressed:
- `--check` is clean;
- the 19 `$defs` blocks are identical;
- the stage A test's 67 controls pass.

Two new Major findings must be fixed before merge. Both are cheap:
- **R-M1.** Note §6 tells B2 to change a contract value that a family schema fixes as a `const`. B2 cannot follow it
  without breaking its own pin at B1's main commit.
- **R-M2.** One new control resolves a commit that exists only on this branch. After the squash merge, it errors in
  any clone that lacks that commit.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | |
| Major | 2 | R-M1, R-M2 |
| Minor | 6 | r-1 to r-6 |
| Info | 6 | ri-1 to ri-6 |

## Closure of the review's findings

| Finding | Prescribed mechanism | Bound to | Result |
|---|---|---|---|
| **B-1** non-row fields | schema validation; `content_hash`; schema source rows on main and unchanged at `HEAD`; owner identities; pinned record IDs | `verify_w9_materialization.py:450-488` | **Closed.** Residuals: r-2 (one check has no control), r-4 (the contract at the chosen commit), r-5 (tracebacks) |
| **B-2** the catalogue chooses its annex | blob, SHA-256 and size constants; commit holds the blob and is on main; set pins; test-only rules moved into `check_annex` | lines 45-90, 181-196, 224-237, 426-448 | **Closed.** The annex is read only by blob (`pinned_annex`). The catalogue's commit choice changes only the `git_commit` field, never the bytes. Residuals: r-1 (a hollow control), R-M2 (a control that is not portable) |
| **M-1** silent green | a missing named catalogue fails; `--require-catalogue` | lines 549-558 | **Closed.** Both CLI runs exit 1 |
| **M-2** per-row controls | 61 W9-C01 and 61 W9-C03 nodes with W11's IDs; a full-path control; a golden row | test lines 104-157 | **Substantially closed.** Residual: r-3 (W9-C01 does not check three derived fields) |
| m-1 duplicate keys | strict loader | lines 136-153 | Closed. The control is at test line 271 |
| m-2 row rules | resolver, `P:`, `U:`, version, schema ID and test-set pins | lines 224-299 | Closed. Each has a control |
| m-3 range hash | W11's definition (P-074 item 1) | line 337; the golden check at test 154-157 uses an independent `json.dumps` | Closed |
| m-4 revision map | `row_supersessions` pairs (P-074 item 2) | `w9_schema_gen.py` revision block | Closed. See ri-3 |
| m-5 annex in the envelope | required `owner_annex_identity` (P-074 item 3) | `w9_schema_gen.py` envelope block | Closed |
| m-6 stale counts | "19" | `w9_schema_gen.py:5-6, 1447` | Closed |
| m-7 B2's edits | named in note §6 | note §6 | **Partly closed.** R-M1, r-6 |
| m-8 CLI edges | `--annex-commit` removed; a non-object catalogue is reported | lines 422-423 | Closed for the top level. r-5 covers inner shapes |
| i-3 runtime obligations | carried in note §6 | note §6 | Closed |
| i-4 `canonical_bytes` | imported | line 36 | Closed |
| i-1, i-2, i-5, i-6, i-7, i-8 | recorded | reconciliation §2 | Closed |

**Can a catalogue still choose or influence its own expected side?**

| Input | Answer |
|---|---|
| Annex | No. Bytes, row set, command set and test set are pinned. Any commit the catalogue names must hold the pinned blob and be on the main ref |
| Schema commit | Only among commits on main whose 19 schema blobs equal `HEAD`'s, so the schema bytes are fixed. The contract at that commit is not tied to `HEAD` (r-4) |
| Owner identities | Read from the contract at the chosen schema commit, so they are bounded by r-4 |
| `content_hash` | No. It is recomputed |
| Record, project and actor IDs | No. They are pinned |
| `created_at` | Free (ri-1, which W11 also leaves free) |
| Main ref | A command-line argument, which the catalogue cannot set |

## Major

### R-M1 (Major). Note §6 tells B2 to replace a clause that a family schema fixes as a `const`

**Claim.** B2 cannot carry out the anticipated edit `expected_catalogue: forbidden_in_stage_a` without changing a
schema. Changing that schema would break B2's own pin at B1's main commit.

**Evidence.**
- Note §6, "B2's anticipated edits": "in the bootstrap contract, B2 replaces three stage A clauses:
  `expected_catalogue: forbidden_in_stage_a`, …".
- `tools/w9_schema_gen.py:1424-1425` and
  `.research-system/schemas/contracts/w9/w9-materialization-bootstrap-contract.schema.json:94, 97` make
  `expected_catalogue` and `acceptance_instance` `{"const": "forbidden_in_stage_a"}`.
- `test_bootstrap_contract_validates_and_matches_owned_values` validates the contract against that schema.
- The verifier refuses a catalogue whose family schema changed after the schema source commit
  (`verify_w9_materialization.py:463-465`). Probe R2 confirms the check fires: schema rows pinned at `07cbcf32` are
  refused for the envelope and the revision import.

**Failure scenario.** B2 follows §6 and edits the contract value. Then either:
- the stage A test fails, because the contract no longer validates; or
- B2 also widens the schema. Then B2's catalogue, pinned at B1's main commit as P-072 item 6 requires, is refused,
  because the bootstrap-contract schema changed after its source commit. The only way out is to pin at B2's own
  commit, which P-072 item 6 forbids.

**Disposition.** Fix now, in B1. Choose one:
- **(a), recommended because it is smallest.** Drop that clause from note §6's list. `expected_catalogue:
  forbidden_in_stage_a` stays literally true, since it describes stage A, and W11 left its corresponding text in
  place. B2 then edits only the `forbidden` entry and the verification rule. Those are YAML values the schema leaves
  free (`arr(TEXT, 1)`), so the edit needs no schema change.
- **(b).** Widen the two `const`s in B1 to an enum that admits a stage B value, and regenerate. That is a schema
  change, but it is made before the pin.

**Affects:** note §6; P-072 item 6; B2.

### R-M2 (Major). The pre-fold control resolves a commit that exists only on this branch

**Claim.** `test_catalogue_cannot_choose_the_pre_fold_annex` builds its catalogue with
`V.annex_identity(V.resolve_commit("8a0d68fc"))`. That needs commit `8a0d68fc` to be present in the clone.

**Evidence.**
- `test_w9_expected_catalogue.py:33` sets `PRE_FOLD_ANNEX_COMMIT = "8a0d68fc"`, and lines 203-207 use it.
- `8a0d68fc` is a branch commit. Main is squash-merged: recent commits carry `(#NNN)`, and P-069 item 1 says "a squash
  merge rewrites branch commits".
- After B1 merges, `8a0d68fc` and its annex blob `4e648b7f` are on no main ref. In a fresh clone `resolve_commit`
  returns `None`, and `annex_identity(None)` raises `CalledProcessError` on `git show None:<annex>`. The test then
  errors.

The other refs the tests use are safe:
- `STAGE_A_MAIN` (`5d325c5b`) is on main;
- `HEAD` is safe;
- the blob `d8fbda41` survives the squash.

**Disposition.** Fix now. Build the pre-fold identity from literal values:
- path `ANNEX_PATH`;
- blob `4e648b7f28f8925643ccf3559e943b1e59510491`;
- its SHA-256 and length;
- any 40-hex commit.

The verifier's blob, SHA-256 and size check (lines 432-437) fires before any Git read, so the control keeps its
stated reason. Then check the whole suite for other branch-only SHAs. This review found none besides `8a0d68fc`.

**Affects:** B-2's control; the suite on main after merge.

## Minor

**r-1. `test_annex_at_a_commit_off_main_is_refused` is hollow.**
- The test (line 199-200) passes `main_ref=STAGE_A_MAIN` and asserts `any("is not on" in p …)`.
- With that ref, the schema-source check also emits "the schema source commit is not on 5d325c5b".
- Probe R1 deleted the annex ancestry branch (lines 447-448) in memory. The assertion still held.

Fix: match `"owner_annex_identity.git_commit is not on"`. Better, build a catalogue whose schema commit is on the
ref and whose annex commit is not.

**r-2. The `HEAD`-drift check has no control.**
- Lines 463-465 ("changed after the schema source commit") work: probe R2 refused schema rows pinned at `07cbcf32`.
- Probe R2 also deleted the check in memory. The verifier then accepted those rows, and no test exercises the
  message.

Add a control. To stay portable (R-M2), build source rows for a schema whose blob differs from `HEAD`, using literal
values or a main commit such as `5d325c5b`, where `w9-schema-catalogue-content` differs.

**r-3. W9-C01 does not check three derived fields independently.**
- Per row, W9-C01 (lines 104-113) checks the 17 copied fields, `row_sha256` and the three test identities.
- It does not check `logical_key`, `receipt_identity`, `complete_write_set`, or `owner_annex_ref`'s path, blob and
  SHA-256 against the independent parse. The golden check covers LR-020 only.
- Probe R7 injected a `derive_row` bug, "streams before events" on every row except LR-020. The bug verified clean
  against itself, and no W9-C01-style assertion caught it.

B2 writes the catalogue with `expected_catalogue` (note §6), the same derivation the verifier uses. So these fields
are certified only by the derivation's own code. Fix: add to W9-C01:
- `row["logical_key"] == annex_row["logical_key"]`;
- `row["receipt_identity"] == annex_row["receipt_identity"]`;
- `row["complete_write_set"] == [e["event"] for e in annex_row["ordered_events"]] + annex_row["affected_streams"]`;
- the three `owner_annex_ref` constants.

**r-4. The contract at the chosen schema commit is not tied to `HEAD` or to a pinned family.**
- `family_files` and `expected_owner_identities` read the contract at the catalogue's schema commit (lines 347-376).
- The drift check covers only the schema files the family lists. The verifier never compares the family list with
  `HEAD`'s contract or with a pinned set: `W9_RECORD_KINDS` is used only for the annex, and the bootstrap kinds are
  not pinned.
- Today the contract blob is the same at `07cbcf32` and `HEAD` (probe R6), so there is no live defect.

Once main holds several contract versions, a catalogue could pick an older one. That one might have a shorter family,
or different owner tuples, while every listed schema blob is unchanged. Fix: require
`family_files(schema_commit) == family_files("HEAD")`, require the record part to equal `W9_RECORD_KINDS` and the
bootstrap part to equal a pinned set, and compare the owner identities with `HEAD`'s contract.

**r-5. Malformed inner shapes still raise.**
- `schema_source_rows: ["x"]` raises `AttributeError`, and a list-valued `git_commit` raises `TypeError`. Both come
  from line 452, before schema validation (probe R3).
- This fails closed, but m-8's intent ("a reported problem, not a traceback") covers only the top level.

Fix: validate the schema first, or guard the two comprehensions.

**r-6. Note §6 leaves one B2 edit out.** `test_required_absent_catalogue_fails` (test lines 283-285) asserts that the
catalogue is absent. B2 must change it, as it must change `test_stage_a_materializes_no_catalogue`. Add it to §6's
list.

## Info

- **ri-1.** `created_at` is not pinned (probe R4). W11 does not pin it either. `expected_catalogue` writes a fixed
  `2026-10-24T00:00:00Z`.
- **ri-2.** `owner_row_multiset_hash` (line 342) implements P-074 item 1 but has no test and no consumer in B1. Its
  consumer is the envelope instance (L-3 or WP9.2). Add a golden value when it gets a consumer.
- **ri-3.** `row_supersessions` has `uniqueItems` over pairs only. The schema admits a superseded row listed twice, or
  mapped to itself. That is an importer obligation (WP9.2), not something the schema can fully express.
- **ri-4.** Several main commits may hold the pinned annex blob. The catalogue's commit choice then changes its
  identity, though not its bytes. Stephen's O-8 names the commit, so this is acceptable.
- **ri-5.** Option-shaped commit strings (`--all`, `--git-dir`, `HEAD`, a short SHA) reach only `git rev-parse`, and
  are refused by the full-SHA equality (probe R5).
- **ri-6.** One model family (P-058).

## Schema half: regression check

| Check | Result |
|---|---|
| `w9_schema_gen.py --check` | exit 0 |
| `$defs` identity | 19 files, 1 distinct block |
| Stage A test | 67 passed. The revision control uses the map; there is a new envelope control |
| `superseded_owner_row_ids` stale references | none outside the reviews (`git grep`) |
| `research_system/` changes | none (`git diff --name-only d6c969fa..427d277a -- research_system`) |
| ruff check and format | clean on the four Python files |

The attacks that failed in the first review still fail:
- the row schema's 24 fields, the W9-C `if`/`then`/`else` and the `0..n` rule are unchanged;
- the new record's refs and edges are unchanged.

## Decision audit

| Decision | Disposition |
|---|---|
| P-074 item 1 (W11 hash definitions) | Keep. The range hash is implemented and golden-checked; the multiset hash is implemented but untested (ri-2) |
| P-074 item 2 (revision map) | Keep. Implemented (ri-3) |
| P-074 item 3 (annex in the envelope) | Keep. Implemented |
| P-072 item 6 (pin at B1's main commit; O-8 names the annex) | Keep. B-2 is now enforced. **R-M1** must be reconciled with it |
| P-072 item 7 (verifier boundary) | Keep. The `canonical_bytes` import is read-only. Nothing under `research_system/` changed |
| P-073 item 1 (W9-C rule and test set) | Keep. The test set is now pinned |
| P-058 | Known limit |

## Revision plan

**Before merge (author):**
- R-M1, option (a): one line in note §6;
- R-M2: literal pre-fold identity.

**Recommended in the same pass:** r-1 to r-6. Each is a few lines and comes with its control.

**Re-review:** a narrow confirmation of R-M1 and R-M2, plus whichever Minors are taken, against the new head.

## Commands run (read-only; probes from the scratchpad)

```text
git switch pipe/w9-wp9-1-catalogue                          # HEAD 427d277a
git log --oneline d6c969fa..HEAD; git diff --stat d6c969fa..HEAD
git diff d6c969fa..HEAD -- 03-decisions-and-open-questions.md transition/w9/wp9-1-stage-b-design-note.md \
    tools/w9_schema_gen.py tests/research_system/contracts/test_w9_contract_materialization.py
grep -n forbidden_in_stage_a tools/w9_schema_gen.py <bootstrap-contract schema>    # lines 1424-1425; 94, 97
git grep superseded_owner_row_ids HEAD                      # reviews only
git diff --name-only d6c969fa..HEAD -- research_system      # 0
python -I -m pytest tests/research_system/contracts/test_w9_contract_materialization.py \
    tests/research_system/contracts/test_w9_expected_catalogue.py -q -p no:cacheprovider -o addopts=""   # 235 passed
python -I tools/w9_schema_gen.py --check                    # exit 0
python -I tools/verify_w9_materialization.py                # 61 pinned rows; 0 problems; exit 0
python -I tools/verify_w9_materialization.py --catalogue nope.json   # exit 1
python -I tools/verify_w9_materialization.py --require-catalogue     # exit 1
python -I -c <$defs identity over 19 files>                 # 19 1
ruff check --no-cache <4 files>; ruff format --check --no-cache <4 files>   # clean
python -I <scratchpad>/probe_r2.py <repo>                   # probes R1-R7: in-memory source patches; nothing written
```

`python` is `C:/Users/steph/TDL/.venv/Scripts/python.exe`. `git status` was clean after every command. No store,
vault, `.apm/` or `papers/` path was read for writing, and nothing was pushed.

## Change log

- Added this file only.
