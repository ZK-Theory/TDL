# WP9.1 stage B1 reconciliation: revision 2 against the review of `07cbcf32`

**Date:** 2026-10-24<br>
**Author:** the WP9.1 author session<br>
**Review:** `reviews/wp9-1-stage-b1-review-07cbcf32-2026-10-24.md` (commit `d6c969fa`). Verdict rework required, scoped to
the verifier and its test: 2 Blocking, 2 Major, 8 Minor, 8 Info. The schema half conformed.<br>
**Owner decisions:** P-074. Stephen chose the recommended option on m-3, m-4 and m-5.<br>
**Status:** B1 revision 2 is ready for a focused re-review. It is not merged.

## 1. Files

| File | Change |
|---|---|
| `tools/verify_w9_materialization.py` | Rewritten around a pinned, independent expected side. Git reads are cached per process |
| `tests/research_system/contracts/test_w9_expected_catalogue.py` | Rewritten: 168 tests, including per-row W9-C01 and W9-C03 nodes |
| `tools/w9_schema_gen.py` and two schemas | The revision-import row map; the envelope's `owner_annex_identity`; stale "17" counts corrected |
| `tests/research_system/contracts/test_w9_contract_materialization.py` | The revision control uses the map; a new envelope control. 67 tests |
| `transition/w9/wp9-1-stage-b-design-note.md` | §3: the row hashes and the verifier's independent side. §6: B2's anticipated edits and the WP9.2 obligations |
| `03-decisions-and-open-questions.md` | P-074 |

Paths without a leading `tools/` or `tests/` are under `docs/plans/agentic-research-system/`.

## 2. Dispositions

| Finding | Disposition |
|---|---|
| **B-1** non-row fields unchecked | Fixed. Every check below has a refusal control, matched on its message. `verify_catalogue` now does all of the following: <ul><li>validates the catalogue against its schema as committed at the schema commit, with the format checker</li><li>recomputes `content_hash` with `research_system.canonical.canonical_bytes` over the catalogue without itself</li><li>derives `schema_source_rows` from the bootstrap contract's family at one commit. That commit must be an ancestor of the main ref, and every blob must be unchanged at `HEAD`</li><li>derives `owner_spec_identity` and `owner_plan_identity` from the contract's `source_spec` and `source_plan`</li><li>pins the catalogue's record, project and actor IDs, as W11 does</li></ul> |
| **B-2** the catalogue chooses its annex | Fixed. The verifier pins `W9_ANNEX_BLOB`, `W9_ANNEX_SHA256` and `W9_ANNEX_BYTES`, and pins the row-ID set (LR-001 to LR-061), the command-type set and the catalogue-test set. The catalogue's annex commit must hold that blob and be an ancestor of the main ref. The annex is read by blob, never by `HEAD` or the catalogue's choice. The command set, record coverage and the Stephen-submitter rule moved from the tests into `check_annex`. Controls cover the review's probe P2 (the pre-fold annex at `8a0d68fc`), a commit with no annex, and a commit off main |
| **M-1** missing catalogue is green | Fixed. A named `--catalogue` that does not exist fails. `--require-catalogue`, for B2 onward, fails on an absent default. Both have controls |
| **M-2** per-row controls not realized | Fixed. 61 `W9-C01-LR-nnn` nodes compare each row with the annex row read independently, by blob through a plain YAML parse. 61 `W9-C03-LR-nnn-owner-row-mutation` nodes mutate each of the 24 fields and require exactly that one difference. One full-path control re-signs a mutated catalogue and runs `verify_catalogue`. A golden literal check pins LR-020's derived values and the range hash. W9-C11 is a WP9.2 obligation (note §6) |
| **m-1** duplicate YAML keys | Fixed: a strict loader refuses duplicate keys, with a control |
| **m-2** unchecked row rules | Fixed. `check_annex` now checks the resolver enum, the `P:` and `U:` token grammars and `record_schema_version`. It restricts `record_schema_id` to the 14 records plus the two import schemas, and pins the catalogue-test set to P-073's. Each has a control |
| **m-3** range-hash meaning | Fixed by P-074 item 1, on W11's definitions, which are now in note §3 |
| **m-4** revision map | Fixed by P-074 item 2: `row_supersessions` is a list of `{superseded_owner_row_id, replacing_owner_row_id}` pairs |
| **m-5** envelope names the annex | Fixed by P-074 item 3: `owner_annex_identity` is required |
| **m-6** stale counts | Fixed |
| **m-7** B2's forward edits | Named in note §6 |
| **m-8** CLI edges | Fixed. `--annex-commit` is removed, because the annex is pinned. A non-object catalogue is a reported problem, not a traceback |
| i-1, i-2, i-5, i-6, i-8 | Recorded |
| **i-3** runtime obligations | Carried in note §6 |
| **i-4** canonical JSON | `canonical_bytes` is imported, as W11 does |
| **i-7** "any new qualifier" | Noted. It is covered by "a later observation", because a qualifier enters through an observation |

## 3. Performance

The first rewrite spawned `git` many times per verification, and the per-row mutation test called the full verifier
about 1,500 times. The run did not finish within 10 minutes and was stopped. Two changes fixed it:
- immutable Git reads are cached per process;
- the per-row mutation test uses `compare_rows`, which is the comparison `verify_catalogue` itself calls, and one
  full-path control still runs the whole verifier.

The verifier test file now runs in about 12 seconds.

## 4. Not done

- No catalogue, no envelope instance, no runtime code, nothing under `research_system/`.
- Nothing is pushed.
