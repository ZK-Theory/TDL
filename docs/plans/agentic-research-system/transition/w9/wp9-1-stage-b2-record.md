# WP9.1 stage B2: the W9 expected catalogue

**Date:** 2026-10-27<br>
**Status:** Written, not reviewed. B2 goes to an independent review, then to Stephen's O-8 acceptance (P-072 item 6).
It is not accepted.<br>
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
| Owner annex | blob `d8fbda41`, 85,664 bytes, at `fc5f356b` |

Stephen's O-8 acceptance names the catalogue and the annex by main commit, blob and SHA-256. The catalogue's main
commit will be B2's merge commit. After acceptance, any row change is a new catalogue identity and a new acceptance.

## 2. The §6 edits

| §6 item | What B2 did |
|---|---|
| Write the catalogue with `expected_catalogue` | §1 |
| Run the verifier with `--require-catalogue` | Passes: 61 pinned rows, 0 problems |
| Replace the contract's `forbidden` entry "expected catalogue instance" | Now "any W9 expected catalogue instance other than w9-legacy-integration-v1.json". "W9" keeps the entry off W11's catalogue in the same folder |
| Replace the verification rule "no expected catalogue or acceptance instance is materialized in stage A" | Now names the one W9 catalogue, the verifier command that checks it, and that no acceptance instance is in the repository |
| Leave `expected_catalogue` and `acceptance_instance: forbidden_in_stage_a` | Left in place |
| Replace `test_stage_a_materializes_no_catalogue` | Now `test_stage_b_catalogue_verifies`, which runs the verifier with `--require-catalogue` |
| Replace `test_required_absent_catalogue_fails` | Now `test_required_catalogue_passes`. B1 review M-1's absent-catalogue control is kept as `test_required_absent_catalogue_still_fails`, which points the default path at a missing file |

The contract is not a schema source row, and the edits change neither the family nor the owner identities, so the
verifier's `HEAD` checks still hold. The catalogue-acceptance envelope instance stays forbidden. It is written at L-3
in the store, or by WP9.2's `accepted_w9.py`.

## 3. Not done

- No acceptance-envelope instance, no runtime code, nothing under `research_system/`, no store writes.
- The design note's status line still says nothing in it is materialized. It is accepted text, so B2 leaves it.
