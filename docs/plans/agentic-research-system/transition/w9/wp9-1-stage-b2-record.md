# WP9.1 stage B2: the W9 expected catalogue

**Date:** 2026-10-27<br>
**Status:** Accepted. Revision 2 reconciled the review `reviews/wp9-1-stage-b2-review-ea989c7e-2026-10-27.md` (see
`reviews/wp9-1-stage-b2-reconciliation-2026-10-27.md`), and the reviewer's confirmation passed. PR #396 merged as
`7979e85a`. Stephen accepted the catalogue and the annex at that main commit on 2026-10-27 (O-8, P-075).<br>
**Package:** 06v WP9.1, stage B, step B2 (P-072 item 6). B1 is merged as `fc5f356b` (PR #395).<br>
**Implementation authority:** P-065 (WP9.0 and WP9.1 only). The design note's §6 lists what B2 produces and edits.
B2 changes no runtime Python and writes to no store.

## 1. The catalogue

`.research-system/evals/expected/w9-legacy-integration-v1.json` is written with the verifier's own
`expected_catalogue(schema_commit, annex_commit)`, with both commits set to B1's main commit
`fc5f356ba3488d8250180e15bc9b7df8a9a2e12a`. The file is `research_system.canonical.canonical_bytes` of that object,
the same encoding as W11's catalogue.

| Identity | Value |
|---|---|
| Git blob | `d1916ffd380050f193fb2c927bb4d724cd2f8a88` |
| SHA-256 | `f7e2d9e2deac022790c296a4962ea3feb7feb1e646da125edf7819ff8719db8c` |
| Size | 128,583 bytes |
| `content_hash` | `fd94dc94f309106ab5b3f84513b450525eaf23678c1896f7b623dd33681e5676` |
| `record_revision` | 1, superseding nothing |
| Owner rows | 61, LR-001 to LR-061 |
| Schema source rows | 19, every one at `fc5f356b` |
| Owner annex | blob `d8fbda416b016f5e19c03689f336caff3166d0d9`, SHA-256 `36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc`, 85,664 bytes, at main commit `fc5f356ba3488d8250180e15bc9b7df8a9a2e12a` (its only main commit) |

`created_at` is `2026-10-24T00:00:00Z`. That is the verifier's fixed value, the annex's confirmation date, and not the
write date. W11's catalogue uses the same convention (B2 review m-3, Stephen's option (a)).

Stephen's O-8 acceptance (P-075, 2026-10-27) names the catalogue and the annex by main commit, blob and SHA-256. The
main commit is B2's merge commit, `7979e85a075ab6a643a7b201ac4186b0b2090d74`; the blobs and SHA-256s are those in the
table above. Before it, the verifier ran in the canonical checkout on `main` with 0 problems (review i-6). Any change
to either file is now a new catalogue identity and needs a new acceptance. The W9 tests pin both byte strings.

## 2. The §6 edits

| §6 item | What B2 did |
|---|---|
| Write the catalogue with `expected_catalogue` | §1 |
| Run the verifier with `--require-catalogue` | Passes: 61 pinned rows, 0 problems |
| Replace the contract's `forbidden` entry "expected catalogue instance" | Now "any W9 expected catalogue instance other than .research-system/evals/expected/w9-legacy-integration-v1.json". "W9" keeps the entry off W11's catalogue in the same folder, and the full path matches the verification rule (B2 review m-5) |
| Replace the verification rule "no expected catalogue or acceptance instance is materialized in stage A" | Now names the one W9 catalogue, the verifier command that checks it, and that no acceptance instance is in the repository |
| Leave `expected_catalogue` and `acceptance_instance: forbidden_in_stage_a` | Left in place |
| Replace `test_stage_a_materializes_no_catalogue` | Now `test_stage_b_catalogue_verifies`, which runs the verifier with `--require-catalogue` |
| Replace `test_required_absent_catalogue_fails` | Now `test_required_catalogue_passes`. B1 review M-1's absent-catalogue control is kept as `test_required_absent_catalogue_still_fails`, which points the default path at a missing file and asserts the guard's message (B2 review i-2) |

**Controls added after the B2 review:**
- **m-2:** `test_committed_catalogue_is_the_verifier_output_at_b1_main` checks the committed bytes against
  `canonical_bytes(expected_catalogue(fc5f356b, fc5f356b))`. The verifier compares objects, so it would pass a
  re-encoding or a re-signed `created_at`; this test refuses both, and its negative control shows it.
- **m-4:** `test_the_only_tracked_instance_is_the_w9_catalogue` finds every tracked JSON or YAML file outside the
  schema tree whose `schema_id` is the W9 catalogue or the acceptance envelope. It requires exactly the one catalogue,
  which enforces the contract's two absence clauses. A negative control adds a second instance of each kind.

The contract is not a schema source row, and the edits change neither the family nor the owner identities, so the
verifier's `HEAD` checks still hold. The catalogue-acceptance envelope instance stays forbidden. It is written at L-3
in the store, or by WP9.2's `accepted_w9.py`.

## 3. Not done

- No acceptance-envelope instance, no runtime code, nothing under `research_system/`, no store writes.
- The design note's status line still says nothing in it is materialized. It is accepted text, so B2 leaves it.
