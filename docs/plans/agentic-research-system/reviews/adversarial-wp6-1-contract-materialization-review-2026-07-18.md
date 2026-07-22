# Adversarial review — WP6.1 contract materialization

**Date:** 2026-07-18
**Verdict:** `rework_required`
**Findings:** 0 Critical, 3 Major, 1 Minor
**Exact subject:** `e2bc89565d7227d271a7bd3098741daec390b2ce`
**Subject branch / PR:** `pipe/ars-wp6-1-task-lifecycle`, draft PR #124
**Review branch:** `review/ars-wp6-1-task-lifecycle-r1b`
**Approved source revision:** `fe5f1d40bc8f05f061317c677b5891cea0711249`
**Approved 06d object:** Git blob `5e2eb60ca4419d1529506de6859fb027cff518af`; canonical UTF-8/LF SHA-256 `96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7`

## 1. Executive verdict

The exact subject is a strong and unusually complete **logical semantic copy** of the
approved 06d rows. An independent parser, reading only the Git object at `fe5f1d40...`,
reconstructed 104 unique normalized rows in the exact 50/41/13 source partition and
182 expanded edges. It found zero mismatches in key order, command type, transition,
ordered events, reducers, projections/selectors, authority subjects, receipts, positive
tests, negative profiles, or annex cells. A separate external matrix rejected 147/147
mutations, including every one of the 104 authority-subject rows, 19 `ClaimDispatch`
relation/race mutations, coordinated expected/runtime substitution, and five runtime-pair
substitutions. Both strict schemas close every object with `additionalProperties: false`.

The exact subject is nevertheless not eligible for D-G6-3 acceptance:

1. its own focused suite fails in the clean Windows checkout because Git converts both
   YAML artifacts to CRLF while the validator rejects any CR byte;
2. the proposed schema-identity manifest contains 210 null future content hashes and
   therefore does not yet materialize the content identities that 06d §1.1 requires the
   owner to accept before runtime implementation; and
3. the committed mutation suite does not persist the full mutation catalogue that 06d
   §5 and 06a T8 require, even though this review's external attacks show that the
   present validator would reject those omitted substitutions.

The row semantics should be preserved. The subject should be revised at a new commit,
retested on Windows and canonical Git bytes, independently re-reviewed, and only then
presented for exact path/schema/blob/SHA owner acceptance. This review does not approve
runtime implementation, registration, merge, Gate 6 work, or any Gate 5 change.

## 2. Scope, independence, and authority

This is a fresh replacement review. It does not rely on the stopped prior reviewer or
on any prior verdict. Prior reviews were used only as locators; all claims below were
re-derived from direct Git objects, the exact subject diff, executable tests, and the
live PR head.

The authoritative expected source is the 06d blob at `fe5f1d40...`, not the current
checkout and not a runtime registry. P-036 accepts that exact plan revision for dispatch
planning while leaving the future WP6.1 manifest, schema-content, review, owner-decision,
runtime, migration, and Gate 6 gates open (`03-decisions-and-open-questions.md`, P-036).

The subject adds exactly seven paths:

- `.research-system/contracts/wp6-1-owner-source-catalogue.yaml`
- `.research-system/contracts/wp6-1-schema-identities.yaml`
- `.research-system/schemas/contracts/wp6-1-owner-source-catalogue.schema.json`
- `.research-system/schemas/contracts/wp6-1-schema-identities.schema.json`
- `tests/research_system/contracts/test_wp6_1_contract_materialization.py`
- `tests/research_system/contracts/test_wp6_1_contract_materialization_mutations.py`
- `tests/research_system/contracts/wp6_1_materialization_validation.py`

There is no production/runtime, shared contract manifest, core command/event schema,
Gate 5 evidence, coverage, decision, fixture, result, or baseline-file change in the
subject diff. Recursive `SchemaRegistry` discovery makes shared manifest wiring
unnecessary. The validator is test-only and explicitly keeps runtime observations
optional until a later accepted boundary.

## 3. Findings

### M-1 — Major — the committed artifacts fail their own validator in a normal Windows checkout

1. **Claim.** The materialization is not checkout-portable. A clean Windows checkout
   produced by the repository's effective Git configuration cannot pass the focused
   semantic test, despite the canonical Git blobs being valid LF artifacts.
2. **Evidence.** `core.autocrlf=true` comes from the system Git configuration and no
   applicable `.gitattributes` rule pins these paths. The checkout catalogue has 9,832
   CR bytes and SHA-256 `0e8579db77f716c481f23371a1beacd53ae9215504b12b84b9655c6f64a3bbe6`;
   its Git blob is `7fe680f8872e3fcf424cee6f92f405ff812f2f01`, 0 CR bytes, canonical
   SHA-256 `30acfa140c090c27c49b70eddfcf3623abd32e8681199b4488d8cc3a2cb238c4`.
   The checkout identity manifest has 2,535 CR bytes and SHA-256
   `4da9ddcf405b69fbdfd350f652a4257a07f86ba2994c1eff8512a0811cc6d85b`;
   its Git blob is `82a1299f0ed7014e320ffc2b52d5ef88f0c27bfe`, 0 CR bytes, canonical
   SHA-256 `01fb7c7c3f7d49f21ada4a8d7983696983d4d31eeed6b511bf0ca4aeef071223`.
   `_read_yaml()` rejects any `\r` at validator lines 211–223. The exact focused run
   returned `1 failed, 30 passed`: the failure is
   `test_wp6_1_materialization_binds_exact_104_row_multiset_and_182_expanded_edges`.
   Loading the two exact Git-object bytes into an external temporary directory instead
   passes and returns 104/182 with the expected multiset hashes.
3. **Failure scenario.** A reviewer or hook on Windows checks out the exact accepted
   commit with the repository's ordinary Git configuration. Git status is clean, but
   the acceptance test fails before semantic validation. A later operator may be
   tempted to rewrite protected artifacts or waive the test as platform noise.
4. **Impact.** The exact artifact is not operationally reviewable or enforceable across
   the repository's supported Windows workflow. This blocks acceptance and makes future
   hook evidence checkout-dependent.
5. **Disposition.** Fix now; do not waive or normalize the failure in the review.
6. **Exact proposed change.** Add path-specific LF rules for the two YAML artifacts,
   renormalize them, and prove both Git-object and checkout-byte equality on Windows.
   Alternatively, make the validator validate canonical committed bytes through an
   explicit Git-object seam while retaining LF enforcement for temporary candidate
   files. In either design, add a Windows checkout regression that checks raw bytes.
7. **Affected decisions.** D-G6-3 exact-manifest acceptance and P-036's retained future
   hash gate.
8. **Affected work packages.** WP6.1 T1 materialization and T8 binding-suite closure.

### M-2 — Major — the “schema identities” freeze null placeholders, not future schema content

1. **Claim.** The identity manifest is an honest proposal for future identities, but it
   is not the independently content-hashed schema-identity materialization required by
   the approved authority.
2. **Evidence.** Independent enumeration found 210 identity observations: 104 command
   bindings plus 106 event bindings, covering 87 unique command paths and 86 unique
   event paths. All 210 `*_schema_sha256` fields are `null`, all 210
   `*_identity_contract_sha256` fields are non-null hashes of records that themselves
   contain the null placeholder, and none of the 173 unique future schema paths exists.
   Both strict schemas require `null`; validator lines 371–404 derive the non-null
   contract hash with the future content hash set to `None`; lines 516–520 reject if a
   named future schema appears; and the committed test at mutation lines 370–382 asserts
   this durable absence. By contrast, approved 06d §1.1 requires each row to supply the
   SHA-256 of canonical schema bytes and requires the independent reviewer to recompute
   every hash before D-G6-3 acceptance. 06a §3 lines 161–167 likewise requires exact
   path, schema ID/version, Git blob, and SHA-256 acceptance before runtime implementation.
3. **Failure scenario.** Stephen accepts the current manifest blob believing it freezes
   future schema content. A later schema author may create any bytes under the proposed
   path/ID/version; those bytes were not named by the accepted manifest. Updating the
   null to a real hash changes every affected row hash, the identity multiset, the
   identity-manifest blob/SHA, and the catalogue's manifest reference, so the current
   exact acceptance cannot authorize that later content.
4. **Impact.** The central D-G6-3 control—independent content identity before runtime
   implementation—remains open. Calling the current records final “identities” risks an
   authority error even though the proposal is internally content-addressed.
5. **Disposition.** Amend the lifecycle and re-materialize before owner acceptance.
6. **Exact proposed change.** Treat this pair explicitly as a non-authoritative proposed
   identity plan. Materialize the future command/event schema bytes (or an independently
   accepted, content-complete schema source), populate every content SHA-256, update the
   strict schema/status model, recompute row/multiset/blob identities, and replace the
   durable `path must not exist` assertion with lifecycle-specific validation. The final
   accepted state must be derived from the separate review and owner-decision records,
   not asserted by the candidate.
7. **Affected decisions.** P-036 boundary and D-G6-3 future exact-hash acceptance.
8. **Affected work packages.** WP6.1 T1 materialization; every later command, grant,
   dispatcher, event, receipt, idempotency, reducer, and projection registration.

### M-3 — Major — the committed mutation suite is materially narrower than the approved mutation contract

1. **Claim.** Exact semantic equality is broad, but the persistent test catalogue does
   not implement all explicit one-field and relational mutations promised by 06d §5 and
   06a T8.
2. **Evidence.** The committed parameter list at mutation lines 156–174 covers missing,
   extra, duplicate, command/test aliases, row swap, two class losses, one projection
   loss, two row-hash changes, and additional properties. Lines 186–238 cover four
   `ClaimDispatch` field substitutions and removal of one named race; lines 255–295
   cover four Decision/RuleEvaluation substitutions; lines 315–337 cover one coordinated
   command alias. It does not persist the required retained-type command/event
   ID/version/content-hash attacks, reducer removal, wrong selector, message
   discriminator, exact edge, event reorder/omission, every-row authority-subject pass,
   full correction-selector owner/cardinality set, the remaining declared
   `ClaimDispatch` mutations, or one-at-a-time runtime-pair fields. This review added no
   subject tests, but its external matrix exercised those gaps and rejected 147/147:
   104 authority rows, 19 ClaimDispatch cases, 4 selector cases, 5 runtime-pair cases,
   coordinated event substitution, schema identity/version/hash changes, reducer,
   projection/selector, discriminator/edge, and ordered-event attacks.
3. **Failure scenario.** A later refactor weakens a comparison field or removes a
   relation while the narrower committed suite remains green. The independent review's
   temporary attack evidence is not a durable regression gate and cannot protect the
   accepted manifest after this session.
4. **Impact.** The subject does not implement the accepted test contract and cannot
   claim T8 closure. Green committed tests would understate future regression risk.
5. **Disposition.** Fix now by promoting the missing external attacks into committed,
   independently named tests.
6. **Exact proposed change.** Add parameterized tests for every mutation named in 06d
   lines 360–373; assert the relevant fail-closed diagnostic where practical so a stale
   hash or schema error cannot mask the intended relational assertion. Keep the 104-row
   authority pass explicit, and keep runtime-pair expected and observed producers
   separate.
7. **Affected decisions.** D-G6-3 exact-set acceptance and P-036's R3/R4 constraints.
8. **Affected work packages.** WP6.1 T1 and T8; later runtime implementation review.

### m-1 — Minor — provenance verifies one annex object but parses another checkout object

1. **Claim.** The validator's immutable provenance source and parsing source are split.
2. **Evidence.** Lines 226–243 run `git show fe5f1d40...:06d` and verify blob/SHA, but
   lines 577–582 then call `_parse_annex(repo_root / path)` on the current checkout. The
   current `HEAD:06d` is later approval-provenance blob
   `eab2eca016583841bc620690a1b29fa7266bf239`, not reviewed blob `5e2eb60...`.
   The fixed row-binding digest rejects a changed table row: the external mutable-source
   attack changed a current parsed row and was rejected. Therefore this is not a proven
   false-acceptance bypass at the exact subject.
3. **Failure scenario.** A later checkout removes, reformats, or damages the current 06d
   path while the exact approved Git object remains available. Validation fails for
   mutable-checkout availability, or non-row prose changes are silently irrelevant to
   the parser even though the provenance message names the approved object.
4. **Impact.** Avoidable availability and audit ambiguity; row substitution is mitigated
   by the fixed digest.
5. **Disposition.** Fix with M-1 rather than accept two-source provenance.
6. **Exact proposed change.** Make the provenance function return the verified Git
   bytes and parse those same bytes through `_parse_annex_bytes`; never reopen the
   checkout path for expected-source reconstruction.
7. **Affected decisions.** D-G6-3 evidence provenance.
8. **Affected work packages.** WP6.1 T1/T8 test-only validation.

## 4. Independent expected-set reconstruction

The independent oracle invoked `git show fe5f1d40...:06d` and did not import the
subject validator. It parsed only the literal §2–§4 tables and the exact closed classes,
profiles, authority mapping, and selector rules in that object.

| Measure | Reconstructed value | Subject comparison |
|---|---:|---|
| W2 lifecycle rows | 50 | exact |
| W2 message/governance rows | 41 | exact |
| W8 operator rows | 13 | exact |
| Normalized rows / unique keys | 104 / 104 | exact order and identity |
| Expanded concrete edges | 182 | exact |
| Distinct positive-test identities | 104 | exact |
| Distinct expanded negative-test identities | 2,407 | exact |
| Command/event identity observations | 210 | exact row/event pairing |
| Catalogue row-field mismatches | 0 | pass |
| Catalogue multiset SHA-256 | `1e7fe6b6e86954d0b0496a6d8d0417774ea25cb5191d2dd1589d44a344c5fa98` | pass |
| Identity-row multiset SHA-256 | `353f93c60c2ed3dc558895cc0fb950dff989b543601bbfc8f0fd4e3a866524e2` | pass |

The 182-edge derivation is 104 base rows plus 78 closed-class expansions: `+7`
for the eight-state Task amendment, `+18` across block/input/pause, `+14` for the
3×5 Task resume cross-product, `+21` across close/cancel/supersede, `+4` attempt
supersede, `+3` attempt retry, `+8` review withdraw/supersede, and `+3` Decision
reject/expire/supersede.

Authority-subject reconstruction matched all 104 rows, including the exception that
`task.claim_start` is Dispatch-scoped because it is a `ClaimDispatch` facet. Coverage
was complete: 4 scope-definition, 17 generic Task, 11 Dispatch, 7 lease, 18 attempt
family/operator, 1 checkpoint-as-attempt, 13 message, 2 blocker, 9 artefact, 9 review,
7 Decision, 1 RuleEvaluation, 1 corrected-record, 2 resource, and 2 project-store rows;
unmatched rows: 0.

## 5. Invariant → enforcement → attack matrix

| Invariant | Approved authority | Subject enforcement | Independent attack/evidence | Disposition |
|---|---|---|---|---|
| Exact approved annex identity | 06a §3; 06d status/§5 | revision/blob/SHA constants and `git show` | reproduced `5e2eb60...` / `96932f...` from Git object | Pass, subject to m-1 |
| 104 row identities and order | 06d §§2–5 | exact row/key list comparison | independent 50/41/13 parser; missing/extra/duplicate/swap reject | Pass |
| 182 concrete edges | 06d closed classes/§5 | literal class map and expansion | independently re-derived 182; class/edge mutations reject | Pass |
| Command/runtime type pairing | 06d §1/rows | exact command type and proposed identity row | alias, retained-type ID/version attacks reject | Pass for proposed logical identity |
| Ordered event/schema pairing | 06d §1/rows | exact ordered event and identity arrays | event ID/version/hash, reorder and omission reject | Pass for proposed logical identity |
| Reducers/projections/selectors | 06d rows/§1.4 | exact per-row lists and closed selector | reducer loss, wrong projection/selector, 4 selector-domain attacks reject | Pass |
| Authority subject/scope/classes | 06d §1.2 | per-row exact object comparison | 104/104 subject-ID mutations reject; external mapping has 0 unmatched rows | Pass |
| Receipts and test identities | 06d §1/rows | receipt literal; unique positive and expanded negative names | 104 positives and 2,407 negatives distinct; alias tests reject | Pass as manifest identities only |
| Strict shape | 06d §1.1 | Draft 2020-12 schemas | 20 catalogue and 6 identity object schemas all close extras; public registry validates | Pass |
| `ClaimDispatch` stored relation | 06d §1.3 | two identical atomic facets | stored Task, revision, lease, write-set, 13 named mutation removals all reject | Pass at contract level |
| `ClaimDispatch` runtime behavior | 06d §1.3 | declarative expected object only | no runtime exists; no event-tail/projection behavior can yet be executed | Deferred by design |
| Decision/RuleEvaluation separation | 06d §1.4 | separate subject/projection/non-compensation object | four committed and external coordinated substitutions reject | Pass at contract level |
| Expected/runtime producer separation | 06d §5 | optional observed tuple compared to fixed annex-derived tuple | coordinated command and event substitutions reject; five runtime-pair fields reject | Pass for current synthetic tuple; runtime seam deferred |
| Future schema content identity | 06d §1.1 | null hash plus hash of null-bearing record | 210/210 future hashes null; 173 future paths absent | **Major gap M-2** |
| Canonical bytes in checkout | 06d §5 | raw `\r` prohibition | canonical Git bytes pass; clean Windows checkout fails | **Major gap M-1** |
| Required persistent mutations | 06d §5; 06a T8 | 30 green focused tests before main failure | 147 external attacks pass but several are not committed | **Major gap M-3** |
| No runtime/shared/Gate 5 change | 06a T8/out-of-scope | seven added lane-owned paths only | exact diff inventory; no protected path changed | Pass |

## 6. Research-assurance lanes

| Lane | Classification | Evidence and disposition |
|---|---|---|
| Topology | N/A | No filtration, homology, Mapper, persistence, or topology result is changed. |
| Stochastic / Null Model | N/A | No RNG, permutation, bootstrap, Markov, or null construction is changed. |
| Statistical / Panel | N/A | No estimand, denominator, model, p-value, correction, or panel rule is changed. |
| Representation | N/A | No PCA/UMAP/scaler/embedding/state representation is changed. |
| Output / Provenance | **Primary — GAP** | Exact source and row provenance are strong; M-1, M-2, and m-1 prevent accepted downstream use. |
| Paper Claim | N/A for research claims | No paper-facing scientific claim is added. Governance claims were reviewed under the adversarial contract matrix above. |

## 7. Strict-schema and lifecycle audit

Both schemas are registered recursively and validate the exact canonical artifacts.
Every object-shaped node is closed: 20/20 in the catalogue schema and 6/6 in the
identity schema. Unexpected root and nested fields reject. The contract/catalogue
reference is acyclic: the catalogue records the identity-manifest blob/SHA; the identity
manifest does not record the catalogue hash or its own blob.

Candidate governance remains non-authoritative: producer is named, independent review
and D-G6-3 owner acceptance are pending, and no candidate field claims acceptance. This
is correct. The lifecycle defect is narrower: the future content hashes are forced null
and future paths are forced absent, so the present candidate cannot become the final
content-complete identity without changing the accepted bytes.

The two Codacy high-severity annotations point only to SHA-1 used to calculate Git blob
IDs in the validator and its test helper. This is the Git object identity algorithm,
not the integrity acceptance algorithm; the artifacts and source are separately bound
by SHA-256. The warnings are contextual false positives, though the hosted Codacy check
remains `ACTION_REQUIRED`. CodeRabbit did not review the draft PR; its status comment
explicitly says “Review skipped”. Neither hosted status substitutes for this review.

## 8. Validation evidence

| Command/check | Exact result |
|---|---|
| Live PR head / local exact subject | both `e2bc89565d7227d271a7bd3098741daec390b2ce` |
| `python .claude/hooks/contract_binding_check.py --validate-only` | exit 0; all gates passed against 101 contracts |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | exit 0; all gates passed against 101 contracts |
| Focused WP6.1 two-file pytest | **exit 1; 1 failed, 30 passed**; CRLF failure in the main 104/182 test |
| Exact Git-object candidate pair through semantic validator | pass; 104 rows, 182 edges |
| Independent exact-`fe5` oracle | pass; zero row-field mismatches |
| External adversarial matrix | pass; 147/147 rejected, including 104 authority rows |
| `tests/research_system/unit/test_schema_registry.py` | 14 passed |
| Ruff check / format check on three added Python files | pass / 3 files already formatted |
| Exact subject diff boundary | seven added contract/schema/test paths; no production/shared/Gate 5 path |

The two contract-framework commands are regression gates over the repository contract
framework; they do not directly replace the focused WP6.1 test seam. Their green result
therefore does not compensate for M-1.

The first attempted `uv run --no-sync` correctly exposed that this app worktree had no
populated environment and created an ignored `.venv`. That newly created directory was
removed immediately with an exact-target `git clean`; all subsequent tests used the
existing populated primary-checkout environment with bytecode, pytest cache, and
coverage output disabled or routed outside this worktree. No temporary oracle/attack
script remains.

## 9. Decision audit

| Decision/control | Disposition |
|---|---|
| 06d remains the expected source; runtime cannot generate/repair it | Keep; exact-row digest and coordinated attacks are effective |
| 104-row / 182-edge semantic copy | Keep; independently reproduced with zero mismatch |
| Recursive registry discovery; no shared manifest edit | Keep |
| No production/runtime or Gate 5 change in materialization tranche | Keep |
| `ClaimDispatch` two-facet stored Task/lease/write-set relation | Keep |
| Decision and RuleEvaluation non-compensation | Keep |
| Current null-bearing identity manifest as final D-G6-3 object | Reject; retain only as a proposed precursor and supersede with content-complete identities |
| Raw LF enforcement without checkout contract | Amend per M-1 |
| Current mutation suite as T8 closure | Reject until M-3 is committed |
| Checkout-path parsing after immutable provenance verification | Amend per m-1 |
| Owner acceptance or runtime implementation at this subject | Defer; prohibited |

## 10. Revision plan

### Immediate corrections

1. Establish path-specific canonical LF checkout behavior or a canonical Git-object
   validation seam, then prove the focused suite on Windows.
2. Parse the exact verified `fe5` bytes instead of reopening the mutable checkout annex.
3. Promote the missing external attacks into the committed suite with diagnostic-specific
   assertions.

### Required lifecycle/materialization correction

4. Keep current proposed identity rows non-authoritative; materialize or independently
   source the future command/event schema bytes, populate non-null hashes, recompute the
   pair, and submit the new exact blobs/SHA-256 values to a fresh independent review.

### Owner decision after remediation

5. Stephen may record D-G6-3 only over the final exact repository paths, schema
   IDs/versions, Git blobs, and canonical SHA-256 values after a zero-Major review.

### Later-work dependencies

6. Runtime behavior, grant/dispatcher/event/receipt/idempotency propagation, atomic
   two-stream publication, replay, and unchanged-side-effect negatives remain for the
   separately authorized runtime phase. The current synthetic runtime tuple is not
   evidence that those production seams exist.

## 11. Hard stops and residual risks

- Do not accept either current manifest under D-G6-3.
- Do not start runtime command/event schema registration or implementation from this
  exact subject.
- Do not merge PR #124 on the strength of the two green contract-framework commands,
  the draft-skipped CodeRabbit status, or canonical-Git-only validation.
- Do not edit or normalize Gate 5 coverage, fixtures, decisions, results, or release
  evidence as part of remediation.
- After remediation, rerun both framework commands, the complete focused suite in a
  Windows checkout, canonical Git-object validation, the 104-row authority pass, the
  full relational/coordinated/runtime-pair matrix, registry tests, and static checks.

Residual risk after the three Majors close is the intended prospective boundary: there
is still no runtime seam to prove behavioral no-side-effect, concurrency, idempotency,
receipt, replay, reducer, or projection claims. Those remain mandatory future
implementation-review evidence and cannot be inferred from these contracts.

## 12. Change log and completeness gate

- Files written by this review: this report only.
- Reviewed subject files edited: none.
- Production/runtime/shared-manifest/Gate 5 files edited: none.
- Temporary review scripts: created outside the deliverable set and deleted before this
  report; no temporary script remains.
- Prior reviewer output used as verdict evidence: none.

Completeness check: every approved row family, exact-set identity, edge expansion,
schema/identity field, reducer/projection/selector, authority subject, receipt/test
identity, `ClaimDispatch` relation, Decision/RuleEvaluation separation, coordinated
substitution, runtime-pair seam, strict-schema boundary, provenance source, future-hash
lifecycle, checkout-byte contract, protected-path boundary, and six research-assurance
lanes has an explicit disposition above.
