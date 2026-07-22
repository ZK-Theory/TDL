# WP6.1 Stage-2 R9 remediation review

**Verdict: `accept_with_required_changes` — 0 Critical / 1 Major / 0 Minor.**

This is a fresh, committed-bytes-only review of Stage-2 remediation subject
`00ca238b2faa33dffe00fd55e10c8702f28268ee` on
`pipe/ars-wp6-1-task-lifecycle` (draft PR #124).  It compares the R8 subject
`bcf45d7905d01f4b3408aefd8887517c7c0e5da5` and the accepted Stage-1 source
revision `da94bd62fbf19021f3046c19fae5117c19219c95`; it does not infer owner
acceptance, D-G6-3, runtime activation, merge authority, or a CodeRabbit
review.

## Review identity and method

The pre-created independent review branch was attached at the exact subject.
All authoritative byte checks used `git show <revision>:<path>`, not a mutable
checkout.  Tests and hook gates ran in an external, short-path checkout at the
same detached subject with `core.autocrlf=false`, because the application
worktree materializes some text files with CRLF while the contract hashes bind
UTF-8/LF committed bytes.  All logs are external under
`C:\Users\steph\.codex\visualizations\2026\07\18\019f7495-7002-7162-a4da-89f5213023c8\wp6-1-stage2-r9-evidence`.

R8 is immutable evidence: at historical commit
`0e1a40a249af8b0fa021090a1cc066643a63aec8`, its report blob is
`c11dd0f965881342a9cfa36156459e231d968b30` and its SHA-256 is
`8c4f1b78bfefd3d5ccbdbbf342842354e772a3b3303ea8b3556c1b17f451d4bd`.
The subject retains that exact blob.

## R8 M1--M4 disposition matrix

| R8 finding | Independent evidence | Disposition |
| --- | --- | --- |
| M1 — complete accepted authority tuple and separate owner record | Both manifests bind the same `da94` proposal YAML (`2f55b82f...` / `d52c9b4e...`), Markdown (`73677f4a...` / `4b997c85...`), and companion schema (`d9e82a04...` / `7599bf7b...`); the YAML is `ars://contracts/wp6-1-schema-fact-annex-proposal` v1.0.0. The record is independently `42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83` / `70a37499528b7d5fdb2fb4627723ae726156c33229aeba5400fd382c752aa648`, contains the R7 supplied owner wording exactly after YAML folding, and has all 14 proposal decision IDs with digest `401f42e827ba8cb75456a879177d0c9b4e1523f7a860a06802910280b6763395`. | Resolved |
| M2 — immutable Stage-2 expectation provenance and coordinated substitution | Normal generation calls `approved_fact_annex_bytes`, which verifies `git show da94:path`, Git blob, SHA-256, UTF-8, and LF. The shipped test’s candidate proposal is not consumed: it monkeypatches unused `span_editor.FACT_ANNEX_PATH`. An independent coordinated attack replacing the helper return, proposal bytes, and matching baseline discriminator produced `CreateScopeAlias` successfully while the manifest tuple was retained. | **Open Major M2** |
| M3 — 14 dangling reusable-object references | Independent scan found 87 command + 86 event schemas, 301 local references all resolving, and every object closed. Exactly the 14 R8 paths now contain the required `member_disposition`, `root_binding`, `review_gate_condition`, or `external_artefact_availability` definition. Public-registry positive and required-field-negative coverage for all 14 passed. | Resolved |
| M4 — four red assertions | Public `SchemaRegistry` tests passed for omission/wrong-type/nested-extra/hybrid rejection, scope variants, message universal facts/body exclusivity, and event new-ID policy including `ScopeDefinitionCreated.new_scope_definition_id`. | Resolved |

The distinct acceptance record contains only `recorded_date: 2026-07-21`, not an
invented timestamp; it contains no self-reference.  Both strict manifests and
the record validate through the public registry and reject a supplied extra
root property.  `06d` is explicitly `historical_lineage`; both governance
records remain `pending_independent_review` and
`pending_d_g6_3_owner_acceptance`.

## Required change — M2

`build_stage2_overlays()` relies on the imported, mutable
`approved_fact_annex_bytes` helper as its only authority boundary.  The
committed test named
`test_wp6_1_coordinated_checkout_substitution_cannot_change_immutable_expectations`
creates a candidate file but changes only `span_editor.FACT_ANNEX_PATH`, a
constant which `build_stage2_overlays()` never reads.  It therefore demonstrates
only that an unused variable cannot alter the result.

The following independent in-memory control was run against committed subject
bytes: substitute the helper return with the alias-modified proposal, supply a
complete baseline map with the matching `CreateScopeAlias` discriminator, then
call `build_stage2_overlays()`.  It returned an overlay containing
`CreateScopeAlias`; it did not fail closed.  This directly covers the required
proposal + helper/expectation + schema coordinated substitution while retaining
the manifest tuple.

Required remediation: make the immutable source verification boundary
non-bypassable for the Stage-2 producer/validator (or independently bind and
verify the helper implementation), and replace the vacuous test with one that
mutates the actually consumed expectation path and proves rejection.  Rerun
this attack after the repair.  No runtime change is authorized or requested.

## Contract, authority, and relation matrix

| Surface | Result |
| --- | --- |
| Accepted direct authority | `da94` committed proposal has 104 owner rows, 104 command bindings, 106 event bindings, 87 command + 86 event identities = 173. Both manifests bind 104 normalized rows / 182 expanded edges. |
| Schema identity and hash cascade | The public materialization seam passed exact paths, IDs, versions, content hashes, separate identity-contract hashes, manifest binding, and same-path-byte mutation controls. Content hashes are real committed schema bytes; no unmaterialized schema is represented with a fabricated content hash. |
| Full authority subjects | Independent all-104 scan matched each catalogue authority kind/source to deterministic binding; every payload-sourced authority field is a required accepted `da94` command fact. |
| Transition and event facts | Public materialization checks passed exact 104-row multiset/order and 182 expanded-edge count, discriminants/from-to, ordered events, reducers, projections/selectors, receipts, positives, expanded negatives, and high-risk state/enum maps. |
| ClaimDispatch | Shared two-facet binding, exact two-member write set, missing facet/binding, stale relation, wrong lease subject, and race controls passed (6 focused mutation tests). |
| Decision and RuleEvaluation | Non-compensation mutation controls passed. |
| Closed schemas | All 173 root/definition object schemas were independently checked for `additionalProperties: false`; local pointers resolve. |

## Scope preservation

`bcf45d7..00ca238` changes exactly 27 paths: the immutable R8 report plus 26
remediation paths — 14 core schemas, 2 manifests, 3 strict contract schemas,
1 acceptance record, and 6 tests/helpers.  There is no production
runtime/registration/dispatch/reducer/projection/migration/hook/Gate5/P0/shared
runtime-manifest path.  The Stage-2 span editor remains a pure test/materializer
seam; no runtime module was used as an expected-set source.

## Validation record

All commands below used the external LF checkout at the exact subject and
`--override-ini addopts=` / no cache provider to avoid coverage overhead.

| Command / control | Result |
| --- | --- |
| Independent committed tuple, record, R8 blob, and 14-ID verifier | Pass |
| Independent 173-schema pointer/closure and all-104 authority scan | Pass: 301 local refs; 14 repaired definitions |
| `test_wp6_1_stage2_span_editor.py` + M3/M4 generated tests | 11 passed in 20.15s |
| `test_wp6_1_contract_materialization.py` | 6 passed in 13.56s |
| Focused ClaimDispatch relation/race tests | 6 passed in 12.34s |
| Decision/RuleEvaluation, identity-hash, and expected-runtime substitution tests | 6 passed in 12.89s |
| `contract_binding_check.py --validate-only` | Pass: all gates against 102 contracts |
| `contract_binding_check.py --no-pytest` | Pass: all gates against 102 contracts |
| Ruff on six changed Python test/helper files | Pass |
| Independent M2 helper/proposal/schema substitution | **Fails closed expectation: attack accepted** |

An earlier combined mutation invocation exceeded the bounded 60-second runner
limit at 32% and was not counted as evidence; the narrower relevant controls
above completed.  No full-repository test run was performed.

## Six-lane disposition

| Lane | Disposition |
| --- | --- |
| A — accepted authority and owner record | Accept |
| B — immutable-source producer seam | **Required change (M2)** |
| C — schema closure and strictness | Accept |
| D — M4 public-registry regression assertions | Accept |
| E — relation/hash/identity mutation controls | Accept |
| F — scope, non-runtime boundary, and gate evidence | Accept, subject to M2 closure |

## Residual boundary

This review does not grant D-G6-3 acceptance, runtime registration, dispatch,
reduction, projection, migration, hooks, PR readiness/merge, or any Gate 6
transition.  CodeRabbit was not substantively reviewed.  The review becomes
eligible for reconsideration after M2 is repaired and the real coordinated
substitution control rejects the attack.
