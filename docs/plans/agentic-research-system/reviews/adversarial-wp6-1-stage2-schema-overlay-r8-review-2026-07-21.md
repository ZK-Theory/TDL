# WP6.1 Stage-2 schema-overlay R8 independent review

## Verdict

**Verdict: rework_required.** Exact subject `bcf45d7905d01f4b3408aefd8887517c7c0e5da5` has no Critical findings, but it has four Majors: incomplete accepted-source authority binding, a mutable-checkout expected-source escape, fourteen unresolved local JSON Schema references, and four red generated-materialization tests. This review neither accepts D-G6-3 nor authorizes runtime, a Gate transition, merge, or any owner decision.

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 4 |
| Minor | 0 |

## Exact review identity and authority

- Review branch: `codex/review-wp61-stage2-r8`; attached once from the clean old review branch and verified at the exact subject.
- Subject branch / draft PR: `pipe/ars-wp6-1-task-lifecycle`, PR #124. Fresh GitHub inspection found `headRefOid == bcf45d7905d01f4b3408aefd8887517c7c0e5da5`, open/draft, merge state `CLEAN`; Codacy is successful. CodeRabbit was not requested or treated as a substantive review.
- Accepted Stage-1 subject: `da94bd62fbf19021f3046c19fae5117c19219c95`.
- Directly reconstructed authority tuple from that commit, not from the Stage-2 helper or the legacy generator:

| Object | Path | Git blob | SHA-256 |
|---|---|---|---|
| Proposal Markdown | `docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md` | `73677f4a49a9752f6536b103321f654cd8575075` | `4b997c85184d8a8842b5524ffe4595473697c3438b70c224685c0b291a4760d0` |
| Proposal YAML | `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml` | `2f55b82f1a84cc0de081d38f8500c73a2083bac4` | `d52c9b4e923d7f31f7201213335a147ff48293f96c0aab7c9eb59f8e7ff96441` |
| Companion schema | `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json` | `d9e82a041337dfa7df65408e93798aaf37841afe` | `7599bf7b2174a2e2e35362427a20ae1357f4c33d13b3d4324a05330ad67c21ec` |

The YAML proposal is `ars://contracts/wp6-1-schema-fact-annex-proposal`, version `1.0.0`. The retained legacy 06d object is only `fe5f1d40bc8f05f061317c677b5891cea0711249` / blob `5e2eb60ca4419d1529506de6859fb027cff518af` / SHA-256 `96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7`.

R7 review record `2237c00b7a4d6df99c53be67bce10cabf5d59c35` is present as blob `df4e163dc1a49893b8cc162204446523a98c12a3`; its text expressly supplies *recommended* owner wording and says acceptance is not inferred. The externally supplied Stage-1 authorization is therefore not a substitute for a content-addressed acceptance record in the subject.

## Independent method and positive evidence

1. Parsed proposal and companion bytes with `git show da94:...`; no expected rows were taken from the Stage-2 span editor, current proposal checkout, legacy 06d materializer, or prior verdict.
2. Reconstructed 104 row bindings, 104 command payload specifications, 106 event fact specifications, and 173 unique identities. Compared each actual schema's path, `$id`, version, root required set, payload branch required set, closure, and SHA-256 against those direct expectations.
3. Independently rehashed all 104 identity rows, all 104 catalogue rows, both multisets, and all 210 row-to-schema raw-byte references. The row/edge outcome is 104 rows and 182 expanded edges; there is no separate DAG-hash field in either accepted proposal or manifest, so the edge count and row/multiset hashes are the applicable graph evidence.
4. Scanned local JSON Pointer references in every one of the 173 JSON schemas; this deliberately does not trust a JSON parse or a producer-side overlay check as schema compilation.
5. Ran direct enum/nullability checks from the accepted proposal. Review verdict has all six values; availability all four; operational profile all three; checkpoint compatibility all three. Root event hash fields (`command_schema_sha256`, `command_payload_hash`, `previous_event_hash`, `event_hash`) are non-null 64-hex strings in all 86 event schemas; 210 row schema hashes are also non-null 64-hex strings. Thus no future-hash/identity-hash null substitution was found.

| Independent check | Result |
|---|---|
| Cardinality / identity / required-set comparison | Pass: 104 command specs, 106 event facts, 87 command + 86 event schemas |
| Raw schema references | Pass: 210/210 manifest raw SHA-256 values match current exact bytes |
| Row content hashes | Pass: 104/104 identity and 104/104 catalogue rows |
| Multiset hashes | Pass: both identity and catalogue multisets |
| Shared mappings | Pass: required splits, normalized merges, discriminator consts, and all 10 PublishMessage/MessagePublished branches are represented |
| High-risk enum closures | Pass: verdict 6, availability 4, operational profile 3, compatibility 3 |
| Strict local-reference closure | **Fail: 14 schemas / 14 dangling local references** |

The shared-identity pass specifically confirmed command splits `ReopenTask` 3, `ExpireDispatch` 3, `WithdrawDispatch` 2, `SatisfyReview` 2; event splits `TaskReopened` 3, `DispatchExpired` 3, `DispatchWithdrawn` 2, `ReviewSatisfied` 2; the one-branch normalizations for `LeaseGranted`, `ClaimDispatch`, `ClaimExecutionLease`, `DispatchClaimed`, and `TaskClaimStarted`; discriminator consts for `AttemptCreated` and `PartialOutcomeRecorded`; and the ten message branches. ClaimDispatch's two relational facets and Decision/RuleEvaluation's non-compensation surfaces remain separately represented in the catalogue and targeted mutation suite.

## Findings

### M1 — Both Stage-2 manifests omit required accepted-authority bindings

**Evidence.** `.research-system/contracts/wp6-1-schema-identities.yaml` and `wp6-1-owner-source-catalogue.yaml` bind only `source_annex` (the proposal YAML tuple) and `owner_source_annex` (legacy 06d). Neither has a companion-schema tuple, an exact 14-decision identity, or a distinct Stage-1 owner-acceptance record. Their schemas and the validator enforce that incomplete shape.

**Failure scenario / impact.** A later worker can retain the proposal blob tuple while substituting its companion validation rules or treating a review recommendation as owner approval. The manifests cannot prove which full Stage-1 contract was accepted, while 06d is semantically over-weighted rather than retained solely as lineage. This is an authority/provenance gap, not an inference that the external owner authorization is absent.

**Required correction.** Add the same content-addressed accepted Stage-1 object to both manifests: proposal and companion paths/blob/SHA/schema ID/version, ordered or multiset-bound 14 decision IDs, and a distinct content-addressed owner-acceptance record. Label 06d `historical_lineage` only. Update strict manifest schemas and independent tests, retaining Stage-2 `pending_independent_review` and `pending_d_g6_3_owner_acceptance` statuses.

### M2 — Expected-source verification can be coordinated through mutable checkout bytes

**Evidence.** `wp6_1_materialization_validation.py` verifies historical `git show da94:proposal` bytes, but `_verify_stage2_overlay_bytes()` first invokes `build_stage2_overlays()` against the mutable checkout proposal. `wp6_1_schema_expectations._accepted_fact_expectations()` also reads the mutable checkout proposal. The Stage-2 span-editor tests import the same producer. No comparison requires the mutable proposal bytes to equal the accepted blob before deriving overlay expectations.

**Failure scenario / impact.** Coordinated alteration of current proposal YAML, span editor, expectations, and generated schemas can pass the producer-coupled tests while static manifests still claim the da94 proposal tuple. Legacy 06d validation cannot establish every accepted 104/106 fact selection. This defeats the required independent expected-source boundary.

**Required correction.** Derive every Stage-2 expectation from verified `git show da94:<path>` bytes (or first fail closed on byte equality of the checkout path to that exact object) and add an adversarial coordinated-substitution test that changes the current proposal plus helper plus generated schema while retaining the manifest tuple.

### M3 — Fourteen materialized schemas contain unresolved local JSON Schema references

**Evidence.** A direct scan found 14 local `#/$defs/...` pointers whose target is absent. The affected command/event pairs are CreateScopeDefinition/ScopeDefinitionCreated and SupersedeScopeDefinition/ScopeDefinitionSuperseded (`member_disposition`); StartAttempt/AttemptStarted (`root_binding`); RecordReviewVerdict/ReviewVerdictRecorded and RequestReviewChanges/ReviewChangesRequested (`review_gate_condition`); and CreateBackup/BackupCreated plus VerifyRestore/RestoreVerified (`external_artefact_availability`). Independently validating a CreateScopeDefinition payload with `members` raises `PointerToNowhere: '/$defs/member_disposition' does not exist`.

**Failure scenario / impact.** The claimed strict payload schemas cannot validate ordinary instances that exercise these accepted reusable objects. This makes downstream validation fail at runtime rather than rejecting/accepting according to the accepted contract.

**Required correction.** Materialize or inline the exact accepted reusable object definitions in every affected schema, ensure every local reference resolves, then run instance-level positive and negative validation for each of the fourteen schemas.

### M4 — Existing generated-materialization tests are red at the exact subject

**Evidence.** The focused run collected 276 tests: 272 passed and four failed in `test_wp6_1_generated_schema_materialization.py`. Failures cover public-registry omission rejection, scope variant facts, message body exclusivity, and the legacy assertion that event facts never carry command-intent new IDs. The last conflicts with the accepted Stage-1 event specification for `ScopeDefinitionCreated`, which requires `new_scope_definition_id`; the other assertions likewise have not been reconciled to the Stage-2 accepted contract.

**Failure scenario / impact.** Codacy green and the two contract-framework gates do not establish a usable exact-head schema suite. A red focused package blocks reliable regression protection and hides whether a correction preserves accepted facts.

**Required correction.** Replace only the obsolete assertions with direct da94-bound expectations; preserve negative coverage for omission, wrong type, nested extras, variant hybrids, and event/command distinctions where the accepted facts actually require them. Do not weaken a test merely to make the current producer green.

## Decision and six-lane disposition

All fourteen frozen decisions are retained, not reopened: `proposal_decision/id_prefixes`, `rule_evaluation_subject_id_grammar`, `resource_operation_id_unions`, `access_mode_vocabulary`, `git_object_identity`, `numeric_policy_bounds`, `open_policy_vocabularies`, `schema_id_scope`, `shared_discriminators`, `retention_and_sensitivity`, `recovery_external_availability`, `correction_subject_union`, `resource_request_profile_discriminator`, and `review_condition_gate_relation`. The failed findings concern materialization, provenance binding, and validation, not a superseding owner decision.

| Assurance lane | Disposition | Evidence / limit |
|---|---|---|
| Evidence fidelity | Fail | M1/M2: complete accepted source and immutable expected-source boundary are not enforced |
| Contract/schema conformance | Fail | M3: 14 unresolved local references; otherwise direct 104/106 and 173-identity comparison passes |
| Relations, reducers, projections, authority | Pass with required regression preservation | ClaimDispatch facets, Decision/RuleEvaluation separation, row effects/order, and 104 authority-subject mutations pass; no runtime authority is granted |
| Output/provenance | Fail | M1/M2 prevent a complete content-addressed Stage-1-to-Stage-2 provenance chain |
| Test/gate assurance | Fail | Both 102-contract gates pass, 11 focused Stage-2/materialization tests pass, 171 targeted mutations pass, but the 276-test run has four failures and producer-coupling remains |
| Scope / lifecycle / practicality | Pass | `bcf45d7` changes only two dead lines relative to `22cf8d9`; no schema/manifest bytes changed, and no runtime registration, dispatch, reduction, projection, migration, hooks, Gate5/P0, or shared-runtime-manifest path changed |

## Scope, byte, and lifecycle audit

`bcf45d7` is the direct child of `22cf8d9`; its entire diff removes only the unused `controlled` assignment and `del controlled` from `tests/research_system/contracts/wp6_1_stage2_span_editor.py`. `git diff --check` passes. The two YAML manifests and their two strict schemas are byte-identical between `22cf8d9` and `bcf45d7`. No key-order or whole-file whitespace churn was found in that delta. The branch was clean before the sole report write.

The legacy `--check`/materializer path was treated as non-authoritative because it still centers 06d and cannot itself bind the accepted proposal-plus-companion tuple. Its retained row/order validation is positive corroboration only.

## Commands and results

| Command / check | Result |
|---|---|
| `contract_binding_check.py --validate-only` | Pass: 102 contracts (gates 1+2) |
| `contract_binding_check.py --no-pytest` | Pass: 102 contracts (gates 1+2+4) |
| Stage-2 span editor + materialization focused tests | Pass: 11 in 19.71 s |
| 104-row authority-subject mutation pass | Pass: 104 in 249.84 s |
| Remaining targeted relation/effect/type/correction/coordinated-substitution mutations | Pass: 67 in 148.49 s |
| Annex + generated-materialization focused run | **272 passed, 4 failed** in 51.49 s |
| Direct da94 schema identity/branch/hash comparison | Pass: 173 identities, 104/106 specs |
| Direct local-reference resolution scan | **Fail: 14 dangling local refs** |

## Required rework and residual limits

Repair M1--M4, regenerate only the necessary exact schema/manifest/test bytes from the accepted Stage-1 tuple, and re-run the direct-byte comparison, pointer-resolution scan, both contract gates, and the full focused WP6.1 set. The correction must remain Stage-2-only: no runtime activation, Gate promotion, self-acceptance, D-G6-3 approval, merge, PR-thread action, or CodeRabbit request is authorized by this report.

This review is exact-head and source-bound. It does not establish that an external owner acceptance record exists beyond the supplied authority statement; it establishes that the subject does not preserve such a record as an independently verifiable artifact.
