# Adversarial WP6.3 assurance-contract remediation R3 review

**Review date:** 2026-07-18  
**Reviewer posture:** distinct non-author authority; independent, adversarial, committed-bytes review  
**Exact reviewed commit:** `1550a57c389da00b7c25299e579d27e4916e4383`  
**Subject branch / PR:** `pipe/ars-wp6-3-tda-pack` / draft PR #123  
**Live PR head verified:** `1550a57c389da00b7c25299e579d27e4916e4383`  
**Review branch:** `review/ars-wp6-3-tda-pack-r3c`  
**R2 review source commit:** `29ff7cac9a26a63beaa6ab6a4ea0f8fff74ee614`  
**R2 report Git blob / raw SHA-256:** `9347c80afeb375d68e6c7e161d65c8ec3afea8fb` / `30122ec3a87e74041a136938ff5e40613c1b2eb9e8af3fca7540d191e0b40ad4`  
**Verdict:** `rework_required`  
**Finding count:** **0 Critical, 3 Major, 0 Minor**  
**Evidence accessibility:** complete; this review is **not Partial**

## 1. Executive verdict

The R2 remediation materially improves the proposed upstream contract. It freezes seven
strict versioned external-record schemas, validates each resolved record against its
record-class schema, derives the pending-reference set, binds obligation enforcers to
their lane relations, constructs the future pack review subject from exact raw bytes,
and preserves the proposed-only boundary. In an LF checkout the complete focused suite
passes: **14/14**. The exact current census is 12 references, 52 fixtures, 69 typed
obligations across six lanes, seven external schema rows, and two current pending
references. The future pack file and object remain absent.

The exact revision is nevertheless not acceptable. Three independently reproduced
failures remain:

1. the advertised validator is unusable in the repository's normal Windows checkout,
   because it hashes CRLF working-tree schema bytes against frozen LF Git-object
   identities;
2. the positive external-acceptance fixture and public semantic seam accept placeholder
   contract and pack-schema content addresses rather than the actual committed objects;
3. the candidate's `assurance_requirement_reference.canonical_sha256` is never joined
   to the resolved accepted requirement record, so an arbitrary replacement survives a
   fully rehashed review/owner chain.

These are content-address and authority-binding defects, not missing scientific results.
They require a bounded contract/test remediation and a fresh independent review. Stephen
must not accept this revision, and no future `TDL_private` pack, `asp_<UUID7>` object,
runtime, result, eligibility change, migration, or claim may be created from it.

## 2. Exact revision, provenance, and scope

The review started from a clean authorized worktree. The replacement review branch and
the subject branch both resolved exactly to `1550a57c...` before attachment. The final
subject history is:

| Commit | Role |
|---|---|
| `2ae607803b4cdaef677c2699439e1e1b876856e8` | Initial upstream contract/schema/test |
| `2a247fe...` | Immutable R1 report carried into the subject history |
| `b44971fdd52430afdd87419b29b40a0f9c090ae7` | R1 remediation |
| `d722664f54a55c59466a9923ac5706c7db010081` | Git-native raw-byte identity correction |
| `d6a6501d60fbdbea4c3ea1a88b61108f736e33ab` | Immutable R2 report carried into the subject history |
| `8b974fc3e4f26e6892c409a4df69cd33da85ec7e` | R2 semantic/authority remediation |
| `48b8337...` | Scanner-driven Git SHA-1 context clarification |
| `1550a57c389da00b7c25299e579d27e4916e4383` | Exact final portability-probe subject |

The final diff from the Gate-6 base adds only the upstream contract, the TDL-private pack
schema, the contract schema, the immutable R1/R2 reports, and the focused binding test.
It changes no production runtime, shared authority, Gate 5 state, result, migration,
eligibility, provider, credential, or claim surface.

Committed artifact identities independently verified from Git object bytes:

| Artifact | Git blob | Raw Git-object SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7bfaa1249dd996e99e85474209228d8327ce8182` | `d35cb108b0218477262c06e34afb774e9445fc14430452e7ab3c0a5694b23e2a` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `edf56687b28e6c14150e4119590928903526278a` | `005e3c6e7128d89cb0a1a5d039d9da1111abea412053f1de2cc03c1ca86c966f` |
| `.research-system/schemas/assurance/assurance-pack.schema.json` | `5e9ef138abc69e2830fc6547bb2352293a0ddb43` | `c3f9b5959eb6c5efb4ead4dd30b9091759ce0450ca13d9a19983ad536229c2a1` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `ec3e20790a8f11a5496399b2b06117c4c881ee2c` | `dd1d81b52fbe138b8fc3abad923b49eb4757134d8c8e6c875beadce21b55d0d6` |

## 3. Findings

### R3-M1 - Major - The public validator is not portable to the repository's Windows checkout

1. **Claim.** The contract freezes external record-schema identity from the committed LF
   Git object, but the test/validator loads and hashes mutable working-tree bytes.
2. **Evidence.** `_external_schema_artifact()` reads
   `CONTRACT_SCHEMA_PATH.read_bytes()` and hashes those bytes at test lines 282-287.
   The contract rows freeze blob `edf56687...` and SHA-256 `005e3c6e...`, which are the
   LF Git-object identities. In the authorized Windows checkout `core.autocrlf=true` and
   all four reviewed text files contain CRLF while Git status remains clean.
3. **Reproduction.** The exact focused command in that checkout collected 14 tests and
   produced **11 failed, 3 passed**. Every one of the 11 failures stopped at
   `_external_schema_catalogue()` with `external record schema content identity differs`
   before reaching its intended semantic assertion. A separate `core.autocrlf=false`
   LF checkout at the same exact commit produced **14 passed**.
4. **Impact.** The validation surface is fail-closed but operationally unusable on the
   repository's configured platform. Intended mutation coverage is masked by an earlier
   representation-dependent failure, so Windows users cannot establish or review the
   promised contract binding.
5. **Required correction.** Resolve committed bytes with `git rev-parse HEAD:<path>` plus
   `git cat-file blob <oid>` (or an equivalently exact Git-object oracle), then parse and
   validate those same bytes. Keep a separate explicit negative for dirty or uncommitted
   candidate bytes. Test both CRLF and LF checkouts without weakening raw-byte identity.
6. **Acceptance consequence.** Major; fix and re-review before owner acceptance.

### R3-M2 - Major - The positive acceptance path uses placeholder contract and schema content addresses

1. **Claim.** The executable positive lifecycle proves acceptance only against fixed
   placeholder hashes, not against the exact committed upstream contract and pack schema.
2. **Evidence.** Test lines 62-75 define `EXTERNAL_CONTRACT_REFERENCE` with blob `1` x 40
   and SHA-256 `2` x 64, and `EXTERNAL_SCHEMA_REFERENCE` with blob `3` x 40 and SHA-256
   `4` x 64. `_proposed_pack()` copies those values at lines 422-423. The validator checks
   equality only to those same constants at lines 536-539; no external Git-object or
   accepted registry record resolves either content address.
3. **Reproduction.** The baseline external-acceptance fixture completed successfully
   while retaining all four placeholders. The actual committed identities are:
   contract `7bfaa124...` / `d35cb108...`; pack schema `5e9ef138...` / `c3f9b595...`.
   None equals the accepted fixture values.
4. **Impact.** The public semantic seam can label a future pack accepted while its stated
   upstream contract and schema subjects do not name any committed artifact. Typed actor
   and lifecycle records cannot compensate for a foreign or nonexistent content subject.
5. **Required correction.** Supply the exact contract and schema subjects as external,
   independently resolved inputs. Bind ID, version, path, Git blob, and raw SHA-256 to
   committed/accepted bytes before candidate parsing. Add stale, foreign-valid, swapped,
   and coordinated-replacement negatives; do not freeze a self-hash into the contract.
6. **Acceptance consequence.** Major; the positive fixture is not valid acceptance
   evidence until corrected.

### R3-M3 - Major - The accepted assurance-requirement body hash is not relationally bound

1. **Claim.** The candidate carries an assurance-requirement `canonical_sha256` field,
   but external acceptance never compares it with the resolved accepted requirement.
2. **Evidence.** `_proposed_pack()` sets the field at lines 424-431. The external
   acceptance routine resolves the typed requirement, checks the acceptance-record hash,
   contract subject, requirement ID/revision, producer, actors, outcomes, relations, and
   ordering at lines 831-945, but never reads or validates the candidate's
   `canonical_sha256` field.
3. **Reproduction.** Starting from the asserted-valid eligible fixture, the probe changed
   the field from `55...55` to `aa...aa`, reserialized the raw candidate, recomputed the
   review subject and every affected external record hash, and called the advertised
   `_validate_external_acceptance()` seam. It returned successfully:
   `ACCEPTED_UNRESOLVED_REQUIREMENT_CANONICAL_SHA256`.
4. **Impact.** A hash-valid review and owner chain can accept a candidate whose declared
   assurance-requirement content identity is arbitrary and disagrees with the accepted
   external record. This leaves a coordinated authority-substitution path.
5. **Required correction.** Define the intended byte surface for the requirement record,
   derive its exact canonical/Git identity outside the candidate, and compare that
   resolved identity with every candidate reference field. If the acceptance-record hash
   is the sole intended content identity, remove the redundant unbound field instead of
   retaining two potentially contradictory authorities. Add one-field and coordinated
   rehash negatives.
6. **Acceptance consequence.** Major; fix and re-review before owner acceptance.

## 4. R2 finding retest matrix

| R2 finding | Independent R3 result | Disposition |
|---|---|---|
| C-1 - semantic external authority could be fabricated | Seven strict record schemas, exact record types/outcomes, canonical actors, relationships, owner grant, content hashes, and full temporal order now reject the reproduced R2 attacks. | **Substantive core closed.** R3-M3 is a narrower remaining content-join defect. |
| M-1 - parsed-object hash substituted for raw candidate bytes | Candidate review subject is derived from exact UTF-8/LF raw bytes before parse; byte-distinct equivalent YAML produces distinct subjects. | **Closed.** |
| M-2 - pending relation contradiction | Pending IDs are derived from exact reference rows; the current set is exactly two and the eligible future fixture clears it. | **Closed.** |
| M-3 - obligation enforcers omitted from lane relation | Every obligation enforcer must exist, permit the lane, and belong to its governing relation; the exact six-lane matrix passes. | **Closed.** |

## 5. Census and six-lane matrix

| Surface | Independent count / state | R3 result |
|---|---:|---|
| External record schema rows | 7 | Strict shape and record-class resolution present; Windows byte source fails R3-M1. |
| Exact reference rows | 12 | Complete-row equality and activation relation pass; 2 remain intentionally pending. |
| Exact fixture rows | 52 | Missing/extra/duplicate/alias/swap attacks pass in LF checkout. |
| Topology obligations | 11 | Prospective only; no topology result or claim. |
| Stochastic/null obligations | 11 | Prospective only; no null execution. |
| Statistical/panel obligations | 12 | Prospective only; no estimate or inferential claim. |
| Representation obligations | 10 | Prospective only; no fit/refit/transform. |
| Output/provenance obligations | 11 | Primary lane; exact-byte subject corrected, but R3-M1/M2/M3 block acceptance. |
| Paper-claim obligations | 14 | Prospective only; claim promotion remains separately gated. |

The 69 obligation rows are typed and exact. `unable_to_grade`, `Partial`, failed proof,
and cross-lane compensation cannot become pass. No lane can compensate for the three
content-address failures above.

## 6. Identity, lifecycle, and dependency-DAG review

| Invariant | Result |
|---|---|
| `TDL_private` family distinct from future `asp_<UUID7>` object | Pass |
| TDL-specific pack schema ID/version/path unique and closed | Pass |
| Candidate is `proposed` only; no embedded review/owner acceptance | Pass |
| Requirement accepted -> candidate authored -> independent review -> owner accepted | Pass for typed record ordering |
| Distinct contract author, requirement author, scope reviewer, producer, scientific reviewer, owner | Pass |
| Active canonical Stephen authority grant | Pass |
| Raw candidate bytes define review/owner subject | Pass |
| Pending set derived from exact references | Pass |
| Content-address graph contains no self-hash cycle | Pass structurally |
| Contract/schema graph resolves to actual accepted content | **Fail: R3-M2** |
| Requirement reference has one coherent content authority | **Fail: R3-M3** |
| Validator consumes platform-invariant committed bytes | **Fail: R3-M1** |

The hash dependency graph is topologically constructible: schema/contract authority may
be established before candidate bytes, candidate bytes before review, and review before
owner acceptance. The problem is not a cycle; it is that two upstream nodes are
placeholders and one requirement-content edge is unenforced.

## 7. Validation and scanner evidence

| Check | Result |
|---|---|
| Windows `core.autocrlf=true` focused suite | **11 failed, 3 passed**; R3-M1 reproduced |
| LF checkout, same exact commit, focused suite | **14 passed** |
| Direct placeholder contract/schema acceptance probe | **Accepted**; R3-M2 reproduced |
| Direct requirement-hash substitution plus coordinated rehash | **Accepted**; R3-M3 reproduced |
| `contract_binding_check.py --validate-only` | Pass against **101 contracts** |
| `contract_binding_check.py --no-pytest` | Pass against **101 contracts** |
| Draft PR #123 head/base/state | Exact subject / `main` / open draft |
| Codacy | Success; 0 new issues in live PR summary |
| CodeRabbit | Status success only because review was **skipped: draft detected**; no substantive review |

The two global contract gates validate registry/framework closure; they do not exercise
the WP6.3 cross-record semantics and therefore do not compensate for the three findings.

## 8. Required revision plan

1. Replace working-tree schema hashing with a Git-object byte resolver and retain an
   explicit dirty/uncommitted-byte rejection path.
2. Replace placeholder contract/schema references with external accepted content-address
   records and bind exact ID/version/path/blob/SHA before candidate acceptance.
3. Bind the requirement `canonical_sha256` to the resolved requirement byte surface, or
   remove the redundant field and make the acceptance-record content hash authoritative.
4. Add durable public-seam mutations for Windows CRLF, placeholder/stale/foreign contract
   and schema subjects, one-field requirement-hash alteration, and coordinated rehash.
5. Preserve the R1/R2 reports byte-identically, rerun both platform checkouts and both
   101-contract gates, then obtain a fresh distinct-authority R4 review.
6. Keep PR #123 draft. A substantive CodeRabbit review and Stephen acceptance of the
   exact final revision remain required before merge or future pack materialization.

These corrections are bounded to the upstream WP6.3 contract/schema/binding surface and
do not authorize writing the future pack or implementing WP6.4/runtime behavior.

## 9. Hard stops and final disposition

- No provider/model/API call, credential resolution, or live grader action occurred.
- No research computation, scientific result, assurance result, or paper claim occurred.
- No future `TDL_private` pack file or `assurance_pack` object was created.
- No Gate 5 state, migration, projection, eligibility, authority, or owner decision changed.
- No subject artifact was edited during review; this report is the only durable review change.
- No merge occurred and no acceptance is implied.

**Final disposition:** `rework_required`. WP6.3 remains stopped at the upstream contract
gate. The exact reviewed revision `1550a57c...` must not be owner-accepted or used to
materialize the future pack. Complete the three bounded corrections, obtain fresh R4
independent review, obtain substantive CodeRabbit conclusion, and then request Stephen's
exact-revision acceptance.
