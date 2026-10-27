# WP9.1 stage B2 review at `ea989c7e`: the W9 expected catalogue

**Date:** 2026-10-27<br>
**Subject:** B2, the single commit `fc5f356b..ea989c7e` on `pipe/w9-wp9-1-catalogue-b2`. It changes 5 files:
- `.research-system/evals/expected/w9-legacy-integration-v1.json` (new);
- `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml` (one `verification_rules` entry and one
  `forbidden` entry replaced);
- `tests/research_system/contracts/test_w9_contract_materialization.py`;
- `tests/research_system/contracts/test_w9_expected_catalogue.py`;
- `transition/w9/wp9-1-stage-b2-record.md` (new).

**Mode:** An independent adversarial review (`adversarial-design-review`, implementation-conformance mode). The
catalogue was rebuilt by a second derivation that does not call the verifier. Each changed control was checked to fail
when its own guard is removed. The reviewer edited nothing except this file.<br>
**Governing texts:**
- the stage B design note, §3 and §6 (revision 3, as merged in `fc5f356b`);
- the owner annex `transition/w9/wp9-1-catalogue-owner-annex.yaml`, blob `d8fbda41`;
- P-072, P-073 and P-074 in `03-decisions-and-open-questions.md`, with P-065's Boundary line and its extensions;
- `tools/verify_w9_materialization.py`, as merged in B1 (`fc5f356b`).

**Known limit (P-058):** one model family. Recorded as a limit, not as a finding.

## Verdict

**`accept_with_required_changes`.** There is no Blocking or Major finding.

The catalogue is correct. A derivation written for this review reproduces it byte for byte from `fc5f356b`, without
calling the verifier. Its blob, SHA-256, size and `content_hash` match the record. Every schema source row and the
annex identity name `fc5f356b`, which is on `origin/main`. The verifier passes the catalogue and refuses every
mutation tried except those listed in m-2. The test replacements keep their controls live, and no test reads a
branch-only commit. B2 touches no runtime code, nothing under `research_system/`, no store and no accepted text.

One change is required before O-8:
- **m-1.** The B2 record's identity table must give the annex's SHA-256 and full blob. P-072 item 6 says O-8 names
  the annex by those.

The other findings are recommendations or owner decisions:
- m-2 to m-6 are Minor;
- i-1 to i-6 are Info.

m-3 (`created_at`) is an owner decision. It must be settled before O-8, because O-8 freezes the bytes.

## Checks requested by the brief

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Reproduce the catalogue bytes, blob, SHA-256, size and `content_hash` from `fc5f356b` | **Pass** | §A1. A separate derivation, using `yaml.safe_load`, `hashlib` and a plain `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, rebuilt all 19 schema rows, the annex identity, all 61 rows (24 fields each), `owner_row_range_hash` and `content_hash`. They are equal to the file. The file is also exactly `canonical_bytes` of itself, as W11's is: blob `d1916ffd380050f193fb2c927bb4d724cd2f8a88`, SHA-256 `f7e2d9e2…19db8c`, 128,583 bytes, no trailing newline, no CR. `expected_catalogue(fc5f356b, fc5f356b) == file` |
| 2 | Every schema source row and the annex identity pin `fc5f356b`, and the annex blob is `d8fbda41` | **Pass** | All 19 rows name `fc5f356ba3488d8250180e15bc9b7df8a9a2e12a`. The W9 schema directory at `fc5f356b` holds exactly the contract's 19 family files. `git rev-parse fc5f356b:<annex>` is `d8fbda416b016f5e19c03689f336caff3166d0d9`, 85,664 bytes, SHA-256 `36a3d1ac…3536fc`. `fc5f356b` is the annex's only commit on `origin/main` (`git log origin/main -- <annex>`), so it is the annex's main commit (note §6, "pinned to the annex at its main commit") |
| 3 | `--require-catalogue` passes, and fails under a mutated catalogue | **Pass, with m-2** | §A2. Passes with 0 problems. It refused 17 mutations, each with the expected message. Three variants pass: a changed `created_at` (re-signed), a pretty-printed re-encoding and a CRLF re-encoding. See m-2 |
| 4 | The contract wording is correct and correctly scoped | **Pass, with m-4 and m-5** | Both edits are the two §6 names, and both values are free `arr(TEXT, 1)`. The edited contract validates against its schema at `fc5f356b` and at `ea989c7e`. "W9" keeps the `forbidden` entry off `w11-portfolio-discovery-v1.json`. `expected_catalogue` and `acceptance_instance: forbidden_in_stage_a` are unchanged (lines 17-18). No file pins the contract's old or new blob or SHA-256 (`git grep`). The W11 catalogue, the W11 contract and the W11 schemas are unchanged in this commit |
| 5 | The test replacements keep their controls live; no test reads a branch-only commit | **Pass, with i-1 and i-2** | §A3. Removing the `--require-catalogue` guard in memory turns the kept M-1 control's exit code from 1 to 0, so the control fails. B2 adds no commit literal. The tests' only commit literals were already there: `5d325c5b` and `d660f091` are on `origin/main`, and `8a0d68fc` is held as a literal and never read (B1 re-review R-M2) |
| 6 | No runtime code, `research_system/`, store or accepted-text change beyond §6 | **Pass** | `git diff --name-only fc5f356b ea989c7e` lists the 5 files only. Nothing is under `research_system/` or `.research-system/schemas/`. The edits fall within P-065 "Docs and data files only" and its extensions: P-069/P-070 for the stage A test, and P-072 item 7 for the verifier test. The design note is left alone, and the record says so (§3) |
| 7 | The B2 record's claims are true | **Pass, with m-1 and m-3** | Every value in record §1 was checked against the bytes (§A1). The §2 statement "the verifier's `HEAD` checks still hold" was checked: the contract's family and `source_spec`/`source_plan` are identical at `fc5f356b` and `ea989c7e`. "W9 tests 245 passed" was reproduced (§A4) |

## Findings

### m-1 (Minor, required). The record's identity table gives the annex without its SHA-256

**Claim.** Record §1 gives the annex as "blob `d8fbda41`, 85,664 bytes, at `fc5f356b`". That is an abbreviated blob
with no SHA-256. The same section says "Stephen's O-8 acceptance names the catalogue and the annex by main commit, blob
and SHA-256", as P-072 item 6 requires.<br>
**Evidence.** `transition/w9/wp9-1-stage-b2-record.md` §1, the table's last row; P-072 item 6
(`03-decisions-and-open-questions.md:4571`).<br>
**Failure scenario.** Stephen accepts O-8 from this record. The annex has no SHA-256 in that accepted text, so the
envelope author must take it from somewhere else, such as the verifier constant or a re-hash.<br>
**Impact.** The O-8 deliverable is incomplete.<br>
**Disposition.** Fix now, in the record only.<br>
**Proposed text.** Replace the last table row with:
`| Owner annex | blob `d8fbda416b016f5e19c03689f336caff3166d0d9`, SHA-256 `36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc`, 85,664 bytes, at main commit `fc5f356ba3488d8250180e15bc9b7df8a9a2e12a` (its only main commit) |`<br>
**Affects.** O-8; P-072 item 6.

### m-2 (Minor). The verifier passes byte strings other than the one O-8 accepts

**Claim.** O-8 accepts the catalogue as one blob and SHA-256. The machine gate (`--require-catalogue`, used by both
new tests) accepts more than that:
- `created_at` is not pinned: the verifier never reads it, and the schema only requires a UTC string;
- the file's encoding is not checked: the verifier parses JSON and compares objects.

**Evidence.** Probe §A2:
- `created_at` set to `2030-01-01T00:00:00Z` and re-signed: 0 problems;
- the same object pretty-printed: exit 0;
- the same object CRLF re-encoded: exit 0.

`verify_catalogue` (`tools/verify_w9_materialization.py:430-513`) has no `created_at` or byte check. The W11 verifier
has neither (`verify_w11_materialization.py`: no `created_at` reference). That is parity, not a regression.<br>
**Failure scenario.** After O-8, an edit to the file changes its blob but not its rows. Examples are a reformat by a
tool, or a `created_at` "correction". All W9 tests stay green. The accepted identity and the file now differ, and
nothing machine-checked notices until the L-3 envelope is written. That happens only if its author compares against
the O-8 text by hand. The envelope binds the catalogue by `git_blob` and `file_sha256`
(`w9-catalogue-acceptance-envelope.schema.json`, `catalogue_identity`).<br>
**Impact.** It is an exposure window between O-8 and L-3 that relies on manual vigilance. No accepted record is
corrupted.<br>
**Disposition.** Recommend fixing it in B2 before O-8. The test file is inside P-072 item 7's boundary, and the
check is cheap. Deferring it to WP9.2 with a named obligation is acceptable.<br>
**Proposed change.** Add one test to `test_w9_expected_catalogue.py`:
```python
B1_MAIN = "fc5f356ba3488d8250180e15bc9b7df8a9a2e12a"  # B1's squash commit on main; the catalogue's pin (note §6)

def test_committed_catalogue_is_the_verifier_output_at_b1_main() -> None:
    data = (REPO_ROOT / V.CATALOGUE_PATH).read_bytes()
    assert data == V.canonical_bytes(V.expected_catalogue(B1_MAIN, B1_MAIN))
```
Its negative control is the probe in §A2: re-encoding or changing `created_at` makes it fail. After O-8, optionally
add an accepted-identity pin as well (blob, SHA-256, length). That would mirror the W9 contract's
`required_w11_catalogue`. It must not go into the bootstrap contract, whose identity the envelope carries; it would
be a test constant.<br>
**Affects.** O-8; WP9.2 (the envelope); the B2 tests.

### m-3 (Minor, owner decision). `created_at` predates the commit the catalogue pins

**Claim.** The catalogue says `created_at: 2026-10-24T00:00:00Z`. Every schema row and the annex identity name
`fc5f356b`, committed `2026-10-27 06:53:53 +0000`. The record claims creation three days before the bytes it cites
existed. The value is the verifier constant (`tools/verify_w9_materialization.py:416`). The record does not mention
it.<br>
**Evidence.** §A1; `git log -1 --format=%ci fc5f356b`. W11 precedent: `created_at: 2026-08-01T00:00:00Z`, with its
schema commit `21fe2657` at `2026-08-01 22:19:12 +0100`. That is also earlier, but on the same day.<br>
**Failure scenario.** A later consumer orders records by `created_at`, or checks that a record does not predate its
sources. A provenance audit reads the date as the write date.<br>
**Impact.** Low. The field is nominal, and no current reader orders by it. O-8 freezes it permanently.<br>
**Disposition.** Owner decision before O-8:
- (a) **Recommended.** Accept it as a nominal fixed value. Add one sentence to record §1: "`created_at` is the
  verifier's fixed value, 2026-10-24 (the annex's confirmation date), not the write date; W11's catalogue uses the
  same convention."
- (b) Change the constant to `2026-10-27T00:00:00Z`. That is a change to a B1 file and gives a new catalogue blob,
  SHA-256 and `content_hash`. The record and this review's identities would then be redone.

**Affects.** O-8; the B2 record.

### m-4 (Minor). The contract's new absence clauses have no enforcement point

**Claim.** The new verification rule says "the only W9 expected catalogue instance is …" and "no acceptance instance
is materialized in the repository". The `forbidden` list says the same. No test enforces either clause. Stage A's
`test_stage_a_materializes_no_catalogue` was the only mechanical check of a stage A absence clause, and B2 replaced
it, as §6 directs, with a positive check of one path. The acceptance-instance clause was never enforced, in stage A or
now.<br>
**Evidence.** A `Grep` of `tests/research_system/contracts/test_w9_*.py` finds no scan of `.research-system/evals/`
or of the tracked files. Both clauses are true at `ea989c7e`: `git grep -l` for the two `ars://legacy/` catalogue and
envelope schema IDs finds only the catalogue, the two schema files, the generator and the verifier.<br>
**Failure scenario.** A later package commits a second W9 catalogue, such as a v2 draft beside v1, or an envelope
instance into the repository. The contract says this is forbidden, and every test stays green.<br>
**Disposition.** Recommend a test, in B2 or WP9.2. It scans `git ls-files '*.json' '*.yaml'` for files whose
`schema_id` is `ars://legacy/w9-schema-catalogue-content` or `ars://legacy/w9-catalogue-acceptance-envelope`. It
asserts exactly `{CATALOGUE_PATH}`, outside `.research-system/schemas/`. Its negative control writes a temp
duplicate.<br>
**Affects.** The bootstrap contract's rules; WP9.2.

### m-5 (Minor, editorial). The two restatements of the one-catalogue rule name it differently

**Claim.** The verification rule names the full path. The `forbidden` entry names a bare file name ("other than
w9-legacy-integration-v1.json"). Read literally, the `forbidden` entry allows a W9 catalogue with that name at another
path, which the rule excludes. The rule is the narrower and correct reading.<br>
**Evidence.** Contract lines 39 and 68.<br>
**Disposition.** Optional. If the contract is touched again before O-8, use the full path in line 68:
"any W9 expected catalogue instance other than .research-system/evals/expected/w9-legacy-integration-v1.json". After
O-8, leave it, because the envelope carries the contract's identity.<br>
**Affects.** The bootstrap contract.

### m-6 (Minor, editorial). One test module's docstring still describes B1

**Claim.** `test_w9_expected_catalogue.py` lines 12-13 say: "No catalogue exists in B1. The catalogue under test is
the one the verifier expects for this checkout, built at `HEAD`, with `HEAD` as the main ref." Two tests in that
module now read the committed catalogue with `origin/main` as the main ref. B2 updated the other module's docstring
but not this one.<br>
**Disposition.** Optional. Proposed text: "From B2 the committed catalogue exists. Most controls here use the
catalogue the verifier expects for this checkout, built at `HEAD`, with `HEAD` as the main ref. Two read the
committed catalogue with `origin/main`."<br>
**Affects.** The B2 tests.

### Info

- **i-1. The new tests need a fetched `origin/main`.**
  - `test_stage_b_catalogue_verifies` and `test_required_catalogue_passes` call `main(["--require-catalogue"])`,
    whose default `--main-ref` is `origin/main`. The rest of the module uses `HEAD`.
  - For the committed catalogue, `origin/main` is the right reference: it tests the real admission property.
  - CI's research_system jobs check out with `fetch-depth: 0` (`ci.yml`, `research-system-suite.yml`).
  - A local clone whose `origin/main` predates `fc5f356b` fails with "is not on origin/main". That is correct
    behaviour, not a defect.
- **i-2. The kept M-1 control checks only the exit code.**
  - Removing the guard in memory turns the exit code from 1 to 0 (§A3), so the control is live.
  - It does not assert the guard's own message, "no catalogue at". A future second failure path, such as an annex
    problem, would also give exit 1.
  - Optional hardening: capture stderr and assert that message (obs 2026-10-24-squash-merge-strands-sha-pinned-controls).
- **i-3. `owner_row_multiset_hash` is defined but nothing computes it, and its row set is ambiguous.**
  - P-074 item 1 defines it over "each row", and the verifier's `owner_row_multiset_hash(rows)` is never called.
  - Over the catalogue's 24-field rows it is `a80788184c02b5baa9ea47cf2f1a254f4f14499188e6a0dcbef8d083072ffde7`.
  - Over the annex rows (the `row_sha256` values) it is
    `c55e68dc9bdce6db0ad77a019bc65986bf73bf262c4f0ab6c32591a276e47623`.
  - The envelope author at L-3 or WP9.2 must pick one, and the choice is not written down. W11's runtime is the
    precedent to check.
  - This is not a B2 defect. Defer to WP9.2 with a named obligation.
- **i-4. The envelope will cite identities B2 changed.**
  - The envelope requires `bootstrap_contract_identity`, `verifier_identity`, `binding_test_identities` and
    `schema_generator_identity`.
  - B2 changed the contract and both test files. Their blobs at `ea989c7e` survive a squash merge:
    - contract `7b463b07fea39e43c644effe11bb578633b4554e`, SHA-256 `983af51a…0cb2`, 3,788 bytes;
    - `test_w9_expected_catalogue.py` `19fdfcb28b90116bb9f7821a76d742f3f6e1e29e`;
    - `test_w9_contract_materialization.py` `4133b75ecb296fe3acc8c3e1c3307fb798cf4ad7`.
  - The verifier (`e8bb5085…`) and the generator (`5b068f9d…`) are unchanged from `fc5f356b`.
  - If m-2, m-4 or m-6 is applied, the test blobs change again. The envelope must then cite the merged ones.
- **i-5. W9 diverges from W11's precedent by design.**
  - W11's bootstrap contract still says "no expected catalogue or acceptance instance is materialized" and forbids
    "expected catalogue instance" (`w11-materialization-bootstrap-contract.yaml:36`, `:109`), although its catalogue
    exists.
  - W9 edits its contract instead, as note §6 directs. Both readings are internally consistent.
- **i-6. Re-run the verifier in the canonical checkout after merge.**
  - Run `verify_w9_materialization.py --require-catalogue` in `C:\Users\steph\TDL` on `main` before O-8 (Lane 4).
  - The risk is low: the file is one line with no newline, and `.gitattributes` gives `.research-system/** text eol=lf`.

## Decision audit

| Governing item | B2's conformance | Disposition |
|---|---|---|
| Note §6: write with `expected_catalogue(schema_commit, annex_commit)` | Reproduced: `expected_catalogue(fc5f356b, fc5f356b)` equals the file | Keep |
| Note §6: every schema source row pinned at B1's main commit | 19 out of 19 at `fc5f356b` | Keep |
| Note §6: each `owner_annex_ref` pinned to the annex at its main commit | 61 out of 61 at `fc5f356b`, the annex's only main commit | Keep |
| Note §6: the verifier run green with `--require-catalogue` | 0 problems | Keep (m-2) |
| Note §6: the two contract clauses replaced; schema unchanged | Done; validates at both commits | Keep (m-4, m-5) |
| Note §6: `forbidden_in_stage_a` consts stay | Lines 17-18 unchanged | Keep |
| Note §6: `test_stage_a_materializes_no_catalogue` replaced | `test_stage_b_catalogue_verifies` | Keep |
| Note §6: `test_required_absent_catalogue_fails` replaced (B1 re-review r-6) | `test_required_catalogue_passes`, plus the kept M-1 control | Keep (i-2) |
| Note §3: the verifier's independent side | The annex is read by pinned blob; a branch-only annex commit is refused (§A2) | Keep |
| P-072 item 6: the envelope instance is not a repository file in stage B | None exists | Keep (m-4) |
| P-072 item 6: O-8 names catalogue and annex by main commit, blob, SHA-256 | The catalogue is complete, pending its merge commit. The annex is missing its SHA-256 | **Amend record (m-1)** |
| P-072 item 7 and P-065 Boundary | Data, docs and the two named test files only | Keep |
| P-073 items 1-4 | Carried through the annex rows; reproduced byte for byte | Keep |
| P-074 item 1: `owner_row_range_hash`, canonical JSON | `23f170bf…82b2` is the SHA-256 of the sorted IDs; encoding is `canonical_bytes` | Keep. The multiset hash is i-3 |
| P-074 items 2-3 | Schema-side (B1); unchanged here | n/a |

## Consistency matrix

| Invariant | Enforcement point | Test | Gap |
|---|---|---|---|
| The catalogue rows equal the annex-derived rows | `compare_rows` | W9-C01/C03 per row; `test_stage_b_catalogue_verifies` | none |
| The annex is the pinned blob, on main | `verify_catalogue` B-2 block | B1 controls; §A2 branch-only probe | none |
| The schema rows are at one main commit, unchanged at `HEAD` | `_check_schema_commit` | B1 controls; §A2 | none |
| `content_hash` over the object without itself | `verify_catalogue` | B1 controls; §A2 | none |
| The file is the accepted byte string | none | none | **m-2** |
| `created_at` | schema `utc` only | none | **m-3** |
| Only one W9 catalogue instance | none | none | **m-4** |
| No acceptance instance in the repository | none | none | **m-4** |
| An absent catalogue fails under `--require-catalogue` | `main` | `test_required_absent_catalogue_still_fails` | i-2 |

## Revision plan

**Immediate (author, before O-8):**
- m-1: the record's annex row, as worded above.

**Owner decisions (Stephen, before O-8):**
- m-3: (a) record `created_at` as nominal (recommended), or (b) change the constant and regenerate.
- m-2: add the byte-identity test in B2 now (recommended), or defer it to WP9.2 as a named obligation.

**Optional in B2, or later:** m-4, m-5, m-6, i-2.

**Later-work dependencies (WP9.2 and L-3):**
- i-3: the `owner_row_multiset_hash` row set;
- i-4: the envelope's code identities, after B2's final merge;
- i-6: the canonical-checkout run before O-8.

## Residual risks

- Until the envelope exists, the accepted catalogue identity is bound by the O-8 text alone (m-2).
- The verifier's `HEAD` checks make every later W9 schema or contract-family change fail
  `test_stage_b_catalogue_verifies`. That is the intended identity discipline: such a change needs a new catalogue and
  a new acceptance. Packages touching the W9 family should expect it.

## Verification evidence

The scripts are kept outside the repository, in the session scratchpad:
- `repro.py` is the independent derivation;
- `mutate.py` holds the mutation probes.

Both are read-only.

**§A1. Reproduction** (`repro.py`, at `ea989c7e`):
```
file size 128583 sha256 f7e2d9e2deac022790c296a4962ea3feb7feb1e646da125edf7819ff8719db8c blob(computed) d1916ffd380050f193fb2c927bb4d724cd2f8a88
blob at ea989c7e d1916ffd380050f193fb2c927bb4d724cd2f8a88
trailing newline False has CR False
canon(own) == file bytes: True
canonical_bytes == file bytes: True
content_hash fd94dc94f309106ab5b3f84513b450525eaf23678c1896f7b623dd33681e5676 recomputed match True
annex identity {... 'git_blob': 'd8fbda416b016f5e19c03689f336caff3166d0d9', 'file_length': 85664, 'file_sha256': '36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc'} == catalogue True
schema rows 19 == catalogue True
all schema rows at C True
schema files in dir at C 19 family files 19 dir minus family: []
owner identities match contract at C: True True
contract at ea989c7e owner ids same: True True family same: True
annex rows 61 global_preconditions equal True
row mismatches []
row ids LR-001 LR-061 61 fields per row {24}
range hash True
```

**§A2. Verifier mutations** (`mutate.py`; `verify_catalogue` with `origin/main` unless stated):
```
baseline: pass (0)                                   expected_catalogue(C, C) == file: True
created_at changed, rehashed: PASS (0)                [m-2]
content_hash zeroed: fail   row field changed: fail   rows swapped: fail   row dropped: fail
extra top-level field: fail (schema)   extra row field: fail   record_id: fail   precondition dropped: fail
annex commit = branch-only ea989c7e: fail ("owner_annex_identity.git_commit is not on origin/main")
annex commit = ea989c7e, --main-ref HEAD: pass        (by design: the main ref is the caller's)
schema commit = branch-only ea989c7e: fail ("the schema source commit is not on origin/main")
schema commits mixed: fail   schema row sha: fail   row_sha256 zeroed: fail   owner spec identity: fail
owner_row_count: fail
pretty-printed file via main --catalogue: 0           [m-2]
CRLF re-encoded file via main --catalogue: 0          [m-2]
default --require-catalogue: 0
```

**§A3. The M-1 control with its guard removed:**
```
patched path, no flag: 0
patched path, --require-catalogue: 1
guard `or args.require_catalogue` removed, --require-catalogue: 0   -> the control fails, so it is live
```

**§A4. Tests** (at `ea989c7e`, `C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest`):
- `test_w9_expected_catalogue.py` and `test_w9_contract_materialization.py`: **245 passed**. This matches the commit
  message.
- Related suites, with coverage disabled: **1,549 passed, 3 failed** in 18 min 50 s. They were
  `tests/research_system/contracts/`, `tests/tools/test_w9_segmentation.py` and
  `tests/research_system/unit/test_wp6_6_discovery_activation.py`.
  - All 3 failures are WP6.3 assurance-pack tests: two in `test_wp6_3_tdl_private_assurance_pack_contract.py` and
    `test_assurance_pack_object_allocation.py::test_allocation_binds_the_unmodified_accepted_contract_subject`.
  - All 3 are listed in `tools/research_system_known_failures.txt` (lines 17-19), and none touches a B2 file.
  - This selection is wider than the author's "739 passed, 1 skipped", so the counts are not comparable.

## Change log

- 2026-10-27: review written on `review/w9-wp9-1-b2`, cut from `ea989c7e`. No B2 file was edited.
