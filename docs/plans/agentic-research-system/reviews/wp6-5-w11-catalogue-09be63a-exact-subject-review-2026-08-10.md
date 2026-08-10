# WP6.5 W11 strict-catalogue exact-subject review — 2026-08-10

## Executive verdict

**Verdict: `accept_exact_subject`.**

This verdict is bound only to commit `09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6`, tree `151e0f8b24ad76913640aa0f1de66cd177a44f8f`, and catalogue blob `8d58818540e04859f929d4b04c71e4cfa0512554` (raw SHA-256 `7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80`, 136,229 bytes). The subject conforms to the accepted W11 Stage-B strict-catalogue contract. It does not accept an external envelope, activate W11 runtime, execute OR-140, authorize WP6.6, or constitute owner acceptance.

## Review identity and scope

- Review worktree: `C:\Users\steph\.codex\review-worktrees\wp65-09be63a-kan83`
- Review branch: `review/wp6-5-w11-09be63a-kan83`
- Subject parent: `5aa533f39351e078fb8d5926f3f70c5015d42bd9`
- Required R1 base: `6febb33538d808e6056c38eedc5c11841c88203f`; verified ancestor of the subject.
- Accepted W11 specification: commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`, blob `f90729d0c42a0de98d064fac0824d1969c871c82`, SHA-256 `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`, 185,214 bytes.
- Foundation schemas/bootstrap: commit `21fe265736834263e9c3094c89fc6a390670be7b`; bootstrap SHA-256 `ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38`.
- Candidate paths are exactly the expected catalogue, two contract-test files, and the inert verifier. No `research_system/**`, `.research-system/schemas/**`, or `.research-system/contracts/**` byte differs from R1.

## Findings

No Critical, Major, Minor, or editorial finding met the eight-field finding threshold. In particular, the catalogue verifier's expected side is resolved from the accepted Git-pinned W11 specification and foundation blobs, while the observed side is the committed catalogue; it is not populated from a runtime registry or from the catalogue itself. The public non-runtime Python admission seam `verify_expected_catalogue` was exercised directly, including decisive tamper controls. The module CLI remains the earlier subject-envelope seam; W11 §8.2 does not require the Stage-B catalogue admission to be exposed as a CLI.

## Exact-set and identity reconstruction

Independent literal extraction from the accepted specification produced exactly `OR-001..OR-041` and `OR-101..OR-140`: 81 entries, 81 unique, no missing, extra, duplicate, or reordered identity. The catalogue matches that ordered set exactly.

The schema-source closure is exactly 61 rows and 61 unique paths/IDs: 16 content, 28 relation, 14 artefact, and 3 bootstrap families. Every row's current bytes equal the exact foundation blob; the catalogue records the corresponding commit, blob, length, SHA-256, and deterministic observation reference. No late schema is admitted.

All 81 owner rows have non-empty command type, payload discriminant, eligible profile, authority subject, preconditions, ordered events, affected streams, complete write set, reducer, projections, receipt, and three literal test identities. Complete-row equality joins those values to the specification-derived expected row and the schema-file observation. Producer-subset checks resolve Candidate registration to OR-001/OR-029, W11 authority-file observation to OR-103/104/111/117/123/129/135, and genesis import to OR-140 only.

The catalogue content hash is recomputed from canonical bytes excluding itself; `catalogue_content_hash` is absent. Source references point only to the accepted specification and foundation bootstrap contract. Self/back-edge, SCC-enabling source substitution, coordinated catalogue/runtime substitution, missing/duplicate row, swapped authority subject, removed effect, blank reducer/projection, aliased test, alternate producer, and late-schema probes all fail admission.

## Expected/observed provenance trace

| Joined value | Expected authority | Observed value | Enforcement/test disposition |
|---|---|---|---|
| owner-row set/order | Git-pinned W11 owner annex | catalogue `owner_contract_rows` | exact 81-row ordered equality; positive and missing/duplicate controls pass |
| command/discriminant/authority | each literal W11 owner-annex row | complete catalogue row | parsed from pinned specification and compared as a complete record; swapped/coordinated mutations reject |
| events/streams/write set | W11 effects cell | complete catalogue row | ordered token/complete-clause comparison; removed effect rejects |
| reducer/projections/receipt | W11 implementation cell | complete catalogue row | complete equality; blank/alias controls reject |
| schema identity and bytes | closed family mapping plus foundation Git blobs | 61 catalogue source rows and current files | one-to-one path/ID/blob/length/SHA comparison; late/drifted file rejects |
| test identities | owner-row identity rule in W11 | three literal fields per row | exact per-row equality and uniqueness; alias/swap rejects |
| catalogue provenance/hash | pinned spec and bootstrap blobs; P0 canonical hash rule | catalogue source refs/content hash | Git raw-byte resolution and independent canonical recomputation; self/back edge rejects |

## Decision and invariant disposition

| Authority item | Disposition | Basis |
|---|---|---|
| P-022, P-026, P-032, P-034, P-036 | Keep | Stage-B catalogue stays inert and does not broaden implementation, migration, provider, or claim authority. |
| D-G6-4 external-envelope/genesis policy | Keep | Candidate records no acceptance envelope and performs no genesis; catalogue provenance is external-source-only. |
| W11-A1 | Defer/unchanged | Optional combined view is not materialized or activated here. |
| W11-I01–I03 | Keep, Stage-B conformant | Closed identities, acyclic hashes, and exact revision/source bindings are represented without runtime action. |
| W11-I04–I08 | Keep, row-binding conformant | Assay/Spike/review/promotion commands, effects, authority, reducers, projections, receipts, and tests are complete in their literal rows; runtime semantics remain later work. |
| W11-I09–I11 | Keep, schema/catalogue conformant | Six-family expected-set and admission identities are bound to strict schema bytes; dossier execution remains inert. |
| W11-I12 | Keep, fully satisfied for Stage B | All 81 complete owner rows and three literal test identities are joined one-to-one to the accepted annex and closed schema set. |
| W11-I13–I21 | Keep, row/schema conformant | Authority-neutral projections, path/ownership/cutover/annotation/claim boundaries are represented in the closed schema and owner-row catalogue; no prohibited runtime is introduced. |
| W11-I22 | Keep, bootstrap-preserved | External-envelope and OR-140 identities are catalogued, while authoritative genesis/replay remains absent. |

## W11 test-catalogue disposition

The specification's tests 1–19 all retain an explicit Stage-B disposition: tests 1 and 3 are directly realized by exact catalogue/schema closure and per-row mutation controls; tests 2 and 4–18 have their command/schema/authority/reducer/projection/test identities completely catalogued but their runtime execution remains correctly deferred; test 19's external-envelope/genesis identities are catalogued while envelope acceptance and genesis remain prohibited. No runtime-test credit is claimed from catalogue tests.

Focused candidate validation exercised 258 catalogue tests: 81 complete-row positives, 81 coordinated per-row mutations, 81 retry-stability cases, and 15 whole-catalogue/closure/provenance/inertness controls. Six additional focused checks covered inert semantic admission, literal-test binding, exact schema closure, bootstrap identity, R1 base stability, and the live WP6.1 census.

## R1 composition and protected-path evidence

- `git merge-base --is-ancestor 6febb335... HEAD` returned success.
- The subject is a three-commit linear descendant of R1: `c5057b2` (catalogue), `5aa533f` (proof), `09be63a` (R1 binding).
- R1-to-subject diff contains only four candidate-owned paths.
- `git diff --quiet 6febb335...HEAD -- research_system` succeeded.
- `git diff --quiet 6febb335...HEAD -- .research-system/schemas .research-system/contracts` succeeded.
- The focused census test independently resolved `104 active / 0 remaining` through the current schema registry.
- Therefore the W11 Stage-B candidate composes by disjoint paths with R1 and preserves its production/runtime seam.

## Validation commands and results

1. `git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git rev-parse 'HEAD^{tree}'; git status --short` — exact worktree/branch/HEAD/tree; clean status before report write.
2. `git merge-base --is-ancestor 6febb33538d808e6056c38eedc5c11841c88203f HEAD` — exit 0.
3. Independent Python raw-byte/JSON/spec-literal probe — catalogue 136,229 bytes; SHA-256 `7e36...60b80`; blob `8d588...2554`; owner `81/81`, missing `[]`, extra `[]`; schema `61/61/61`; family counts `16/28/14/3`; all required row-field blank counts zero; accepted-spec literal IDs `81/81`, exact ordered match true.
4. `python -m pytest -q -o "addopts=" -p no:cacheprovider -p no:cov tests/research_system/contracts/test_w11_expected_catalogue.py` — **258 passed in 30.32s**.
5. Six named focused tests across `test_w11_contract_materialization.py` plus `test_wp6_1_c1_campaign_census.py::test_wp6_1_current_runtime_census_is_104_active_zero_remaining` — **6 passed in 20.91s**.
6. Combined two-file pytest attempt exceeded the 60-second execution wrapper and returned no terminal pytest summary; no aggregate credit is claimed. The narrower completed runs above are decisive for the changed behavior.
7. `git diff --check 6febb335...HEAD` — clean.

Pytest used `C:\Users\steph\TDL\.venv\Scripts\python.exe`, with repository addopts cleared and cache/coverage plugins disabled. No candidate file was changed by review execution.

## Practicality, residual risk, and change log

The Stage-B verifier adds bounded review-time Git reads and complete-record comparisons; its cost is proportionate to a one-time 61-schema/81-row acceptance gate. Runtime cost is zero because no runtime binding exists.

Residual risks are deliberately outside this verdict: the external observation, independent report identity, Stephen acceptance envelope, OR-140 one-time genesis, runtime implementation, WP6.6, and runtime negative paths remain future gated work. A later candidate commit, schema/spec byte change, external-envelope mismatch, or runtime implementation requires its own exact-subject validation and cannot inherit this verdict.

Change log: this review created only this report. It did not modify candidate bytes, Jira, a PR, CodeRabbit state, or owner records.
