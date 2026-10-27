# WP9.1 stage B2 reconciliation: revision 2 against the review of `ea989c7e`

**Date:** 2026-10-27<br>
**Author:** the WP9.1 author session<br>
**Review:** `reviews/wp9-1-stage-b2-review-ea989c7e-2026-10-27.md`. Verdict: accept with required changes. No
Blocking or Major findings; 6 Minor and 6 Info.<br>
**Owner decisions:** Stephen chose the recommended option on m-3 and m-2, and took every optional finding (m-4, m-5,
m-6 and i-2) in this revision.<br>
**Status:** B2 revision 2 is ready for a narrow confirmation. It is not merged.

## 1. Files

| File | Change |
|---|---|
| `transition/w9/wp9-1-stage-b2-record.md` | The annex's full identity (m-1); the `created_at` sentence (m-3); the new controls; the status line |
| `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml` | The `forbidden` entry names the catalogue's full path (m-5) |
| `tests/research_system/contracts/test_w9_expected_catalogue.py` | The docstring (m-6); the guard's message (i-2); the byte-identity test (m-2); the instance scan (m-4); negative controls for both |

The catalogue is unchanged: blob `d1916ffd380050f193fb2c927bb4d724cd2f8a88`.

## 2. Dispositions

| Finding | Disposition |
|---|---|
| **m-1** the annex lacks its SHA-256 | Fixed with the review's text: full blob, SHA-256, size and main commit |
| **m-2** the verifier passes other byte strings | Fixed. `test_committed_catalogue_is_the_verifier_output_at_b1_main` requires the committed bytes to equal `canonical_bytes(expected_catalogue(fc5f356b, fc5f356b))`. `test_byte_identity_refuses_a_re_encoding_or_a_new_created_at` is its negative control: a pretty-printed encoding and a re-signed `created_at` both fail the byte check, and the second still passes `verify_catalogue`, which shows why the test is needed. An accepted-identity pin is left until after O-8, as the review suggests |
| **m-3** `created_at` predates the pinned commit | Stephen's option (a). The value stays, and record §1 says it is nominal: the verifier's fixed value, not the write date, as W11's is |
| **m-4** the absence clauses have no enforcement point | Fixed. `test_the_only_tracked_instance_is_the_w9_catalogue` uses `git grep` to find candidates among tracked JSON and YAML files, parses each one, and requires the only file outside `.research-system/schemas/` whose `schema_id` is the W9 catalogue or envelope to be the catalogue. `test_a_second_instance_is_found` is its negative control, once for each kind |
| **m-5** two names for the one catalogue | Fixed: the `forbidden` entry uses the full path |
| **m-6** a stale docstring | Fixed with the review's text, slightly reworded |
| i-1 | Recorded. The two `--require-catalogue` tests need a fetched `origin/main`, which CI provides |
| **i-2** the M-1 control checks only the exit code | Fixed: the control also asserts "no catalogue at" on stderr |
| i-3 | Carried to WP9.2: the row set for `owner_row_multiset_hash` must be chosen and recorded |
| i-4 | Recorded. The contract and test blobs change in this revision, so the envelope cites the merged blobs |
| i-5 | Recorded |
| i-6 | Carried: run `verify_w9_materialization.py --require-catalogue` in the canonical checkout on `main` before O-8 |

## 3. Verification

- `verify_w9_materialization.py --require-catalogue`: 61 pinned rows, 0 problems.
- `w9_schema_gen.py --check`: clean.
- The W9 tests: 250 passed. The stage A test has 67 and the verifier test 183.

## 4. Not done

- No acceptance-envelope instance, no runtime code, nothing under `research_system/`, and no store writes.
- Nothing is pushed.
