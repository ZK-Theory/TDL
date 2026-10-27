# WP9.1 stage B2 confirmation at `3241f0e9`: revision 2

**Date:** 2026-10-27<br>
**Subject:** B2 revision 2, `ea989c7e..3241f0e9` on `pipe/w9-wp9-1-catalogue-b2`, in two commits:
- `5e10c694`, the review cherry-picked. It is byte-identical to the reviewer's `39adfbb2`, with an empty diff;
- `3241f0e9`, the revision.

The revision changes 4 files: the record, the bootstrap contract, `test_w9_expected_catalogue.py` and the new
reconciliation.<br>
**Mode:** A narrow confirmation (`adversarial-design-review`, remediation re-review). Each disposition in the
reconciliation's §2 is bound to the lines that implement it. Each new control was checked in memory, with its guard
removed or narrowed, to show it fails. The reviewer edited nothing except this file.<br>
**Inputs:**
- the review `reviews/wp9-1-stage-b2-review-ea989c7e-2026-10-27.md`;
- `reviews/wp9-1-stage-b2-reconciliation-2026-10-27.md` §2;
- Stephen's choices: m-3 option (a), m-2 now, and m-4, m-5, m-6 and i-2 in the same pass.

**Known limit (P-058):** one model family. Recorded as a limit, not as a finding.

## Verdict

**`pass`.** m-1 to m-6 and i-2 are closed as the reconciliation states. The confirmation raises no new Blocking,
Major or Minor finding. It has three Info notes (c-i1 to c-i3), and none needs action before merge.

The catalogue is unchanged: blob `d1916ffd380050f193fb2c927bb4d724cd2f8a88` at `3241f0e9`, and
`verify_w9_materialization.py --require-catalogue` reports 61 pinned rows and 0 problems. B2 is ready for Stephen's
merge decision and O-8.

## Finding by finding

| Finding | Disposition | Bound to | Control, and what removing its guard does | Result |
|---|---|---|---|---|
| **m-1** the annex row lacks its SHA-256 | The review's text | Record §1, last table row: full blob `d8fbda41…d0d9`, SHA-256 `36a3d1ac…36fc`, 85,664 bytes, main commit `fc5f356ba348…2e12a` | n/a (docs). Every value was re-checked against `git rev-parse fc5f356b:<annex>` and the blob's bytes | **Closed** |
| **m-2** the gate passes other byte strings | A byte-identity test, now | `test_committed_catalogue_is_the_verifier_output_at_b1_main` and the helper `_is_b1_main_output`. The helper compares the file with `canonical_bytes(expected_catalogue(B1_MAIN, B1_MAIN))`, and `B1_MAIN` is the full `fc5f356b`, an ancestor of `origin/main` | P1: a pretty-printed committed file **fails** the test, while the verifier passes the same file (exit 0). P2: weakening the helper to an object comparison **fails** the negative control `test_byte_identity_refuses_a_re_encoding_or_a_new_created_at`, through its re-encoding leg. The control's `created_at` leg also shows `verify_catalogue` alone returns `[]`, which is why the test is needed | **Closed.** See c-i3 |
| **m-3** `created_at` predates `fc5f356b` | Option (a), nominal | Record §1: "`created_at` is `2026-10-24T00:00:00Z`. That is the verifier's fixed value, the annex's confirmation date, and not the write date." The confirmation review `wp9-1-stage-b-note-confirmation-8a0d68fc-2026-10-24.md` is dated 2026-10-24, so the date is the annex's confirmation date | n/a (docs) | **Closed** |
| **m-4** the absence clauses have no enforcement point | A tracked-instance scan | `test_the_only_tracked_instance_is_the_w9_catalogue`, `_tracked_legacy_candidates` (`git grep -l -F` over `*.json`, `*.yaml`, `*.yml`) and `_legacy_instances` (parses each file and checks its top-level `schema_id`; skips `.research-system/schemas/`). At `3241f0e9` the prefilter finds the catalogue and the two schema files, and only the catalogue survives | P3: deleting `found.add` **fails** the positive test. P4: narrowing the instance check to the catalogue's ID alone **fails** the envelope case of `test_a_second_instance_is_found` and leaves the catalogue case passing, so the per-kind control does what it claims | **Closed.** See c-i1 and c-i2 |
| **m-5** two names for the one catalogue | Full path | Contract line 68 now reads "…other than .research-system/evals/expected/w9-legacy-integration-v1.json", the same path as rule 39. That line is the only change to the contract. No file pins the new contract blob `96a63114` | n/a | **Closed** |
| **m-6** a stale docstring | Reworded | Test module docstring, lines 12-14. Accurate: the B2 tests read the committed catalogue, and the two `--require-catalogue` tests use `origin/main` | n/a | **Closed** |
| **i-2** the M-1 control checks only the exit code | Assert the message | `test_required_absent_catalogue_still_fails` now asserts `"no catalogue at"` on stderr. The phrase occurs once in the verifier, in the guard's own message | P5: changing that guard's message in the verifier **fails** the control. The earlier probe, removing the guard so the exit code becomes 0, still fails it | **Closed** |

The reconciliation's dispositions of i-1, i-3, i-4, i-5 and i-6 are recorded or carried. That matches the review's
recommendations:
- i-3 goes to WP9.2;
- i-6 is a run in the canonical checkout before O-8;
- i-4: the envelope must cite the merged contract and test blobs, which changed again in this revision.

## Nothing else changed

`git diff --stat ea989c7e 3241f0e9`, excluding the review file, lists 4 files:
- the contract, with 1 line changed;
- the record;
- `test_w9_expected_catalogue.py`;
- the new reconciliation.

The catalogue and `test_w9_contract_materialization.py` are unchanged. `git diff fc5f356b 3241f0e9` is empty for
`tools/`, `research_system/` and `.research-system/schemas/`, and `w9_schema_gen.py --check` exits 0. No store was
touched.

## Info

- **c-i1. The scan's YAML leg has no control.**
  - With the `*.yaml` and `*.yml` pathspecs removed from `_tracked_legacy_candidates`, every scan test still passes
    (P6).
  - The negative control injects its synthetic file after the prefilter, as a `.json` path. The prefilter is proven
    only by its finding the committed JSON catalogue.
  - There is no tracked YAML instance today, and the contract names a JSON catalogue. Optional: add a `.yaml` case to
    the negative control, through a temporary tracked-file stand-in.
- **c-i2. The prefilter matches the literal ID only.**
  - A JSON instance that writes the ID with escaped slashes (`"ars:\/\/legacy\/…"`) parses to the same `schema_id`
    but is not matched by `git grep -F` (P7).
  - So are an instance nested below the top level and an instance placed under `.research-system/schemas/`.
  - None of these is produced by `canonical_bytes` or by any current W9 tool. This is a known limit of a cheap scan,
    not a defect.
- **c-i3. The byte test follows the verifier's constants.**
  - `_is_b1_main_output` derives the bytes from `expected_catalogue`. A reviewed change to the verifier's
    `created_at` constant, made together with a regenerated file, would keep it green.
  - That is the intended change path before O-8. After O-8, the accepted-identity pin the review left for later
    (blob, SHA-256 and length as test constants) closes it.

## Verification evidence

Probes ran at `3241f0e9`. The script `confirm_probes.py` is in the session scratchpad. It mutates the test or
verifier source in memory only, and no file under the repository changed (`git status` is clean).
```
== unmutated ==
byte identity: passes / byte negative control: passes / only tracked instance: passes
second instance (envelope): passes / second instance (catalogue): passes
candidates: [w9-legacy-integration-v1.json, w9-catalogue-acceptance-envelope.schema.json, w9-schema-catalogue-content.schema.json]
P1 byte identity on a pretty-printed committed file: FAILS      verifier on the same file: 0
P2 helper weakened to object comparison -> byte negative control: FAILS
P4 instance check narrowed to the catalogue id -> second instance (envelope): FAILS; (catalogue): passes
P3 found.add deleted -> only tracked instance: FAILS
P6 YAML pathspecs dropped -> all scan tests: pass                [c-i1]
P7 escaped-slash envelope id parses to the id: True; contains the -F pattern: False   [c-i2]
P5 M-1 control, guard message changed in the verifier: FAILS
```

Other checks at `3241f0e9`:
- `verify_w9_materialization.py --require-catalogue`: "annex and catalogue: 61 pinned rows; 0 problem(s)".
- `w9_schema_gen.py --check`: exit 0.
- Tests, run with coverage disabled:
  - `test_w9_expected_catalogue.py` and `test_w9_contract_materialization.py`: **250 passed** (183 + 67), as the
    reconciliation says;
  - with `tests/tools/test_w9_segmentation.py` added: 287 passed.

## Change log

- 2026-10-27: confirmation written on `review/w9-wp9-1-b2`, rebased onto `3241f0e9`. The reviewer's `39adfbb2`
  dropped as already applied (`5e10c694`). No B2 file was edited.
