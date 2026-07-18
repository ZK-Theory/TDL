# Adversarial remediation R2 review — WP6.2 T1a live-grader calibration protocol

- **Review date:** 2026-07-18
- **Review authority:** fresh distinct-authority R2 statistical/assurance review; the reviewer did not author the subject or R1 report
- **Exact reviewed subject:** `87a44dd888817a5629343520038cf2ec5ac932ec`
- **Review branch:** `review/ars-wp6-2-threshold-protocol-r2`
- **Subject branch / PR:** `pipe/ars-wp6-2-threshold-protocol`; draft PR #122
- **Base authority:** `4e6fd0cb26c04ff9707c3183f663461d752b53b9`
- **Approved normative source:** `fe5f1d40bc8f05f061317c677b5891cea0711249`
- **Review scope:** Gate 6 / WP6.2 T1a protocol only

## Executive verdict

**Verdict: `rework_required`.**

Severity count: **0 Critical, 2 Major, 0 Minor**.

The remediation closes the statistical-inference, seed, current-byte relational-oracle,
execution-freeze, and Windows portability defects identified by R1. The exact current
protocol contains the independently reconstructed 31 M and 20 H obligations, the exact
15-package immutable corpus, M39/H28 case IDs, exact blinded UTF-8/LF subject bytes,
fixture-derived adjudicator-only oracles, prospective allocation, repetition, and
adjudication inputs. Its finite-census acceptance rule is descriptive only: it prohibits
binomial, bootstrap, confidence, prevalence, and future-population inference. No result
instance, provider call, eligibility action, authorization, or research claim exists.

Two material defects nevertheless prevent acceptance:

1. The prospective future-result schema does not enforce the exact execution-slot,
   repetition, human-role, adjudication-case, class-summary, or external acceptance
   relations claimed by the protocol. A candidate with only one repeated model case,
   one repeated human case, one repeated adjudication case, two M summaries, internally
   contradictory zero-error fields, and invented protocol/review/acceptance hashes
   validates with zero schema errors.
2. The three required F-036 mutation cases are different labels and transformation
   hashes over **identical 1,065-byte blinded subjects** with the same subject SHA-256.
   They present the combined pre-control failure rather than isolating expected-value
   anchoring, degenerate fallback, and null-operation invariance one at a time. This
   does not satisfy the approved requirement to calibrate each mutation.

R1-M1 and R1-M2 are therefore only partially remediated. `D-G6-2` remains open. Do not
merge or take the owner gate on this revision. A new content-addressed T1a revision must
fix both Majors, pass a fresh independent review, and only then be presented to Stephen
for exact-hash acceptance. T2–T8 and every M/H eligibility transition remain blocked.

## Exact review identity and provenance

### Commit and PR currency

- The authorized worktree was initially detached. Detached `HEAD` and
  `refs/heads/review/ars-wp6-2-threshold-protocol-r2` both resolved to the required
  subject before the single permitted `git switch` attached the branch.
- Subject parent: `d7238cfb1ae5538e93e917e7b263dcd26d87ef73`; subject tree:
  `d69e29a682ea27d9dcde05c75d1ceba7b5e3857a`.
- At review time draft PR #122 was open and mergeable against base
  `4e6fd0cb26c04ff9707c3183f663461d752b53b9`; its head and
  `origin/pipe/ars-wp6-2-threshold-protocol` both resolved exactly to the subject.
- The full base-to-subject history adds only the five original protocol/schema files,
  the focused test, and the R1 report. It adds no result, call, runtime implementation,
  eligibility, claim, or authorization artifact.

### Reviewed artifact identities

All SHA-256 values below were recomputed from `git show <subject>:<path>` bytes, not from
the mutable checkout.

| Artifact | Git blob | SHA-256 | Bytes |
|---|---|---|---:|
| `.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml` | `de8acbd93c3e2ffefd0f214298171d1f48082da3` | `f2d73fa3b42bf518a3bd04744835742c559ef63b56365bd83959e8e22d4bce7d` | 585,479 |
| `.research-system/contracts/wp6-2-live-grader-calibration-protocol-identity-manifest.yaml` | `2d5f9b2454cbcd6704fc8de37f75da21a17cdde8` | `1ed929d587d8d632f43159ad8d59c7f3d34cdc17a6dd3cb45a882d8eefe0664c` | 1,892 |
| `.research-system/schemas/contracts/wp6-2-live-grader-calibration-protocol.schema.json` | `73524a0c46e5d79eb9fb82583f138f1e45c52b12` | `e1cad81ee3c7d2362eba75634682091d4c284c79d4469415dc1f13d7bfa633b7` | 92,208 |
| `.research-system/schemas/contracts/wp6-2-live-grader-calibration-protocol-identity-manifest.schema.json` | `98aef9683622f223fd1cb15eb3dd4c6ee3c51508` | `69777e64b645b91921842074c976391a4e43eb6feab070092bdea38d1520d799` | 4,554 |
| `.research-system/schemas/contracts/wp6-2-live-grader-calibration-future-result.schema.json` | `1762a5c18bcc69ec0c89d27c0e42a3c7c61bde5d` | `66003e736bb1e1d75087bb6f28d15e7ba7d75d6aedc0eacf39c5469347c5f64b` | 199,232 |
| `tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py` | `e69b1f66cb4bec9d2517e02236d466ec2800dab0` | `629f116aec1a6354fe8ce9b0c6d59e93127ddb865dbc1729b50904668c70aae4` | 47,316 |

The protocol and manifest declare `1.1.0`; their schemas pin the same IDs and versions.
The future-result schema pins
`ars://contracts/wp6-2-live-grader-calibration-future-result@1.0.0` and protocol
`wp6-2-live-grader-calibration-protocol@1.1.0`. All three schemas are recursively closed,
require every declared property, contain no defaults, and validate the committed
protocol/manifest values.

### R1 identity and disposition source

R1 was independently reproduced rather than adopted from the remediation summary.
Original review commit `e7c30ef75750ddbddbe7761e858f1cda68d9247f` and the history-carried commit
`d7238cfb1ae5538e93e917e7b263dcd26d87ef73` contain the identical report blob
`67a7df66dffd50f6929ec76c428e56a369af815b` with SHA-256
`e07963495032a061f2079b32c4fee44a483ce7d80c9a7d63f7291128409c4af0` (41,342 bytes).
Both commits have exact reviewed parent `fe2962fa9e10eb290dec0b9e53c3b81bd3ac6491`.
The remediation pins those identities correctly and retains R1's `rework_required`
status; it does not treat R1 as acceptance.

### Normative authority verification

All nine `authority_sources` rows were resolved at their declared commits. Every path,
Git blob, and SHA-256 matched. The exact approved 06e authority is:

- path: `docs/plans/agentic-research-system/implementation/06e-wp6-2-live-replacement-map.md`
- revision: `fe5f1d40bc8f05f061317c677b5891cea0711249`
- blob: `a187ff6435f0a170bbb894bbb2a94ce97586fa30`
- SHA-256: `a65c24624bb309558dd29a779b2db5b1c308b9fcd5caff4b5394e365b77e47b8`

The base P0 coverage and variant-matrix blobs are respectively
`c1563b725702d8738597e6b25cc3f3061c51226c` and
`6f2a63c59fcd5a33b0d0f915b1514ba1187fc55d`, exactly as the protocol declares.

The content-address dependency graph is acyclic: approved plans/base fixture Git
objects and the earlier R1 report precede the protocol; the future schema binds the
protocol's execution-freeze/corpus identities; the scoped identity manifest then binds
the protocol and schema blobs. No artifact contains its own final blob/SHA-256 and no
strongly connected hash component exists. Finding R2-M1 concerns later candidate-side
acceptance fields, not a current self-hash cycle.

## R1 disposition matrix

| R1 finding | R2 disposition | Direct result |
|---|---|---|
| R1-M1 — relational identities not enforced | **Partially closed; not accepted** | Current target/case/execution rows equal an external Git-object reconstruction and the test-only semantic oracle rejects coordinated protocol mutations. The future-result public schema still accepts duplicate/omitted slots and coordinated invalid summaries (R2-M1). |
| R1-M2 — executable blinded cases/oracles/allocation absent | **Partially closed; not accepted** | Exact subject bytes, 15 fixture oracles, 51-obligation allocation, roles, repeats, initial views, and adjudication inputs are frozen. Future evidence relations remain shape-only (R2-M1), and F-036's three mutation labels share one combined subject (R2-M2). |
| R1-M3 — unsupported binomial/bootstrap inference | **Closed** | Exact finite-census descriptive counts/proportions only; no sampling model, confidence, prevalence, binomial, or bootstrap claim is permitted. |
| R1-M4 — Windows/CRLF portability | **Closed** | Canonical LF Git bytes and standard Windows CRLF checkout bytes both pass; fresh detached checkout reproduced 28/28. BOM, lone CR, missing terminal LF, and content changes reject. |
| R1-m1 — ambiguous seed extraction | **Closed** | Exact algorithm and vector now yield digest `0cf7de1a…bdf8a` and seed `217570842`. |

## Findings

### R2-M1 — Major — The future-result schema accepts grossly incomplete and self-attested evidence

**Claim.** The protocol requires exact execution-slot/repetition/human-role closure and
externally accepted identities, but the prospective result schema enforces only array
cardinality, whole-object `uniqueItems`, per-record case branches, and 64-hex shapes.
It does not enforce a bijection over required slots or derive summaries and acceptance
from records.

**Evidence.** The protocol claims zero missing/extra/duplicate/reordered items at
`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:8049` and declares
78 model, 112 human-initial, and 28 human-adjudication slots at `:8069-8073`. The schema:

- accepts any string as `execution_slot_id` and either repetition at
  `.research-system/schemas/contracts/wp6-2-live-grader-calibration-future-result.schema.json:37-100`;
- uses only `minItems`, `maxItems`, and whole-record `uniqueItems` for model and human
  arrays at `:190-194` and `:2859-2863`;
- permits any one of the 28 H case IDs per adjudication record, again with only whole-
  record uniqueness, at `:4808-4903`;
- allows two different summary objects with the same class and independently enums
  class/denominator plus unconstrained counts, proportions, and `accepted` at
  `:4906-4961`; and
- accepts arbitrary 64-hex `protocol_canonical_sha256`,
  `required_execution_slot_ids_sha256`, `independent_review_sha256`, and
  `stephen_acceptance_sha256` at `:176-189` and `:4964-4971`.

The only focused future-schema test checks that the 39+28 branch case-ID set equals the
expected case-ID set (`tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py:798-814`).
It does not validate a complete result instance or attack duplicate slot keys, missing
repetitions/roles, duplicate adjudication cases, summary relations, or acceptance
authority.

**Exact reproduction.** Using `jsonschema.Draft202012Validator` against the committed
future schema, the reviewer constructed:

1. 78 distinct JSON objects all using the first model branch, one
   `execution_slot_id`, `rep-01`, and one case; only receipt/output hashes varied.
2. 112 distinct objects all using the first human branch, one slot, `rep-01`,
   `human-initial-grader-01`, and one case.
3. 28 adjudication objects all using one case; only one decision hash varied.
4. Two class summaries both labeled `M`, both with denominator 8, including
   `false_pass_count: 3`, `false_pass_proportion: 0.0`,
   `false_block_proportion: 1.0`, and `accepted: true`.
5. All-zero 64-hex protocol, required-slot-set, independent-review, and Stephen-
   acceptance hashes.

Validation returned **zero errors**. Distinct slot/case counts were 1/1 for both model
and human arrays, one adjudication case, and summary classes `[M, M]`.

**Failure scenario.** T1b emits the required number of syntactically unique records by
varying receipts while omitting 66 cases, all `rep-02` slots, one or both human grader
roles, and 27 adjudication cases. It declares contradictory zero-error proportions and
`accepted: true`, then supplies invented review/acceptance hashes. Schema validation
passes, so a downstream gate that relies on the advertised strict schema can admit an
incomplete or false calibration package.

**Impact.** This is a material evidence and authority bypass. It defeats allocation
closure, repetition, blinded-human diversity, adjudication completeness, finite-census
summary correctness, non-compensation, and external owner/reviewer authority. The
candidate status and later human review reduce immediacy, so severity is Major rather
than Critical; they do not make the machine-checkable claim true.

**Disposition.** Fix now in T1a. Do not defer to T1b implementation.

**Required interface change.** Freeze the complete required slot projection
`(execution_slot_id, case_id, execution_record_sha256, repetition_id,
initial_grader_role_id)` and enforce exact multiset/bijection equality in a semantic
validator derived from the accepted execution freeze. Enforce one adjudication
disposition per H case and the cross-fields linking disagreement, requiredness, and
decision. Derive class, denominator, counts, proportions, zero-error acceptance, and
non-compensation from the records. Resolve protocol, independent-review, and owner-
acceptance identities from external accepted records; a candidate must not create its
own acceptance. Add public-seam negatives for duplicate slot with varied receipt,
missing rep-02, missing human role, repeated adjudication case, M/M summaries,
class/denominator swap, count/proportion mismatch, accepted-with-error, stale protocol,
and invented review/owner hashes.

**Affected decisions/work packages.** P-035, D-G6-2, WP6.2 T1a/T1b-M/T1b-H, future
T5–T8, M/H eligibility, and the exact-hash owner gate.

### R2-M2 — Major — F-036's three mutation cases do not isolate the three required mutations

**Claim.** The protocol enumerates all three F-036 mutation IDs, but all three execution
cases serialize the same combined pre-control evidence packet. Different labels and
transformation-spec hashes therefore do not demonstrate one-at-a-time mutation
resistance.

**Evidence.** The approved addendum requires that “F-036 calibrates each mutation” at
`docs/plans/agentic-research-system/design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md:48`,
and W6 requires mutations exercising no-op, plausible-constant, fallback, and other
degenerate paths through independent recomputation at
`docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md:315-320`.
The immutable F-036 definition names three mutation IDs at
`.research-system/evals/fixtures/F-036/fixture.yaml:89-92`.

The three protocol rows at
`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:988-1050` all
bind the same pre-control blob `b11d9beb…`, reference SHA-256 `879b8043…`, and expected
subject SHA-256:

`95e8ec5ba4eaf6099a26d0978ea992f4c3d86c860437d8a3285570abda9f2f2e`.

Their execution records at `:3573-3785` contain the same 1,065 base64-decoded subject
bytes. Those bytes simultaneously set anchoring, degenerate-fallback, expected-value-
recomputation, and null-invariance evidence to the combined pre-control values. The
builder explains why: `_expected_subject` special-cases only ambiguity and identifier
renaming; all other transformation IDs use the same source-reference projection
(`tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py:359-390`).

Independent grouping found 39 model records but only 34 unique model subject hashes.
The F-036 negative group alone contains three labels over one subject. The supplied
suite checks each stored byte/hash and ID but has no assertion that the F-036 mutation
subjects differ or isolate the named defect.

**Exact reproduction.** Decode `expected_subject.bytes_base64` for
`M-NEG-F-036-EXPECTED-VALUE-ANCHORING`,
`M-NEG-F-036-DEGENERATE-CONSTANT-FALLBACK`, and
`M-NEG-F-036-NULL-OPERATION-INVARIANCE`; each is 1,065 bytes and each hashes to the
same value above. JSON-decoding any one shows the same five-field combined evidence
object. Grouping all execution records by `expected_subject.sha256` produces one
three-record F-036 group.

**Failure scenario.** A grader recognizes only one conspicuous field in the combined
packet and rejects all three nominal cases for that one reason while remaining unable
to detect an anchored target, a plausible constant fallback, or an invariant null
operation separately. The protocol records three passing negative cases and can still
reach zero-error closure even though two named mutation capabilities were never
tested independently.

**Impact.** This double/triple-credits one observation and weakens the exact negative
fixture census at the anti-gaming boundary. It violates the accepted mutation-specific
calibration requirement and can admit a grader that does not cover all three proof
obligations.

**Disposition.** Fix now in T1a.

**Required interface change.** Materialize three distinct deterministic F-036 blinded
subjects from the immutable stimulus/oracle: each subject must activate only its named
adverse mutation while the other proof-obligation fields are in their controlled state.
Bind each ordered transformation algorithm and exact bytes/hash, recompute dependent
case/record/manifest/freeze/schema identities, and add negative controls proving:
(a) the three subject hashes are distinct; (b) only the named semantic field/path is
adverse in each case; (c) a grader that detects only one mutation cannot pass the other
two; and (d) coordinated relabel/rehash cannot restore validity.

**Affected decisions/work packages.** P-035, D-G6-2, W5 contract activation, W6
calibration, F-036, WP6.2 T1a/T1b-M, and the future composite policy.

## Independent finite census and obligation closure

The 51 obligation rows were parsed directly from the six-tuples in the approved 06e Git
blob, not from the protocol or current checkout. Complete-record equality including
obligation ID, fixture/revision, grader ID/class/version, source variant, and prospective
live variant holds against the current protocol.

**M obligations (31):** `M-005`, `M-006`, `M-007`, `M-011`, `M-012`, `M-013`,
`M-014`, `M-018`, `M-019`, `M-020`, `M-024`, `M-025`, `M-026`, `M-027`, `M-028`,
`M-029`, `M-030`, `M-031`, `M-032`, `M-033`, `M-034`, `M-035`, `M-039`, `M-040`,
`M-041`, `M-045`, `M-046`, `M-047`, `M-048`, `M-049`, `M-050`.

**H obligations (20):** `H-001`, `H-002`, `H-003`, `H-004`, `H-008`, `H-009`,
`H-010`, `H-015`, `H-016`, `H-017`, `H-021`, `H-022`, `H-023`, `H-036`, `H-037`,
`H-038`, `H-042`, `H-043`, `H-044`, `H-051`.

The canonical expected-set SHA-256 values independently recompute to
`4143948f0dd2d82f523d585ad35ca3be9fa6278b5c3d87fab50745e9b6d656e1`
for M and
`32c779cdb0e934cbfba4fba70885506d6e196b7c08a00915f9fa61f7ee6e7694`
for H.

The exact corpus is `F-005`, `F-009`, `F-012`, `F-014`, `F-020`, `F-021`, `F-022`,
`F-025`, `F-026`, `F-031`, `F-032`, `F-033`, `F-035`, `F-036`, and `S-016`.
All 15 package tree identities, selected revisions, fixture blobs, source/stimulus/pre-
control/post-control SHA-256 values, mutation/safe IDs, and fixture-versus-grader-manifest
rows match exact base Git objects. Each package contains exactly the same required eight
files; total closure is 120/120 with no missing or extra package file.

Case-ID reconstruction from base fixture mutation and safe-variation IDs gives exactly:

| Class | Negative | Positive | Safe | Ambiguous | Producer-correlated | Total | Fixture clusters |
|---|---:|---:|---:|---:|---:|---:|---:|
| M | 13 | 11 | 11 | 1 | 3 | 39 | 11 |
| H | 8 | 8 | 8 | 1 | 3 | 28 | 8 |

All 67 case IDs and all 51 allocation obligation IDs match; every obligation appears in
at least one frozen execution record, with no missing or foreign obligation. Internal
canonical hashes for all target bindings, cases, transformation specs, 15 oracles,
blinded views, adjudication manifests, execution records, class manifests, human rubric,
and the execution freeze recompute with zero mismatch. The execution-freeze SHA-256 is
`9615bf58c3d76b3b024192c651c5676043784de31bcfed8f816faa57526d5b4b`.

This exact ID closure does not waive R2-M2: three distinct F-036 IDs still point to one
combined subject.

## Requirement and assurance coverage

| Requirement | R2 result | Evidence/disposition |
|---|---|---|
| Exact approved obligation census | PASS current bytes | Exact 31 M / 20 H complete-row equality from approved 06e Git object. |
| Immutable corpus/vintage | PASS | 15 exact package trees, 120 required files, coverage/matrix blobs, all declared byte hashes. |
| Independent expected oracle | PASS for frozen current protocol | Expected rows derive from approved 06e/base fixture Git objects; 15 adjudicator-only oracle packets and hashes recompute. No hash cycle. |
| Exact blinded subject bytes | PASS current bytes | 67 valid base64 packets, UTF-8, terminal LF, no CR, length/SHA exact; no case ID, case kind, expected decision, oracle fields, or concrete allocation in initial subject. |
| Allocation concealment and producer/grader separation | PASS protocol / FAIL future enforcement | Frozen roles/families/contexts are distinct and hidden in initial view; future record can self-assert receipts/identity and omit slots (R2-M1). |
| Human disagreement/adjudication | PASS protocol / FAIL future enforcement | Two initial roles, distinct adjudicator rule, exact input manifest frozen; future schema permits repeated cases and contradictory requiredness/decision (R2-M1). |
| Repetitions and ordering | PASS protocol / FAIL future enforcement | `rep-01`/`rep-02` and exact seed/order frozen; future schema permits all records to be `rep-01` (R2-M1). |
| Mutation/invariance resistance | FAIL | F-036's three mutations are one identical combined packet (R2-M2). Other committed coordinated protocol mutations reject. |
| Execution-freeze binding | PASS current protocol | Every dependent hash recomputes; future schema pins the exact freeze hash. Exact slot closure is absent (R2-M1). |
| Schema IDs/versions/closed shape | PASS shape | IDs/versions, no defaults, required properties, `additionalProperties: false`. Shape closure is not relational closure. |
| Prospective-only future semantics | PASS absence / FAIL candidate authority | No result instance exists and status is candidate-pending-review. Candidate may invent protocol/review/acceptance hashes (R2-M1). |
| Expiry/suspension/amendment | PASS protocol | 90-day expiry and identity-change/amendment hard stops are explicit. |
| Outcome permissions | PASS current protocol | T1a acceptance would permit only T2 then T3/T4; no live grading, T5–T8, eligibility, or claim. |

## Statistical-design audit

| Dimension | Disposition | Basis |
|---|---|---|
| Target population | PASS | Complete purposive finite census: exact 11 M and 8 H fixture-revision clusters; no superpopulation. |
| Estimand | PASS | Separate class-specific finite-census false-pass and false-block cluster proportions. |
| Denominator / clustering | PASS | Denominators 11 and 8; case/repetition/human judgments nested within fixture revision; any adverse required item marks the cluster. |
| Acceptance rule | PASS design / FAIL schema enforcement | Zero counts and zero proportions are non-compensable; future summary fields need derived relational enforcement (R2-M1). |
| Sampling / inference | PASS | No probability-sample claim, confidence level, prevalence, IID/exchangeability, or future-fixture inference. |
| Binomial / bootstrap / resampling | PASS | Explicitly prohibited for acceptance and reporting because no sampling model exists. |
| Multiplicity / non-compensation | PASS | FP/FB and M/H remain separate; no weighted aggregate repair. |
| Repetitions/randomness | PASS protocol | Two dependent repetitions; seed/order prospective and result-independent. |
| Eligibility | PASS hard stop | No eligibility decision or activation exists. |

The exact seed material is
`ars://contracts/wp6-2-live-grader-calibration-protocol@1.0.0`; SHA-256 is
`0cf7de1a64e8f19bd027189ba18186a0b85d6dd539d37861c22e3bdad67bdf8a`.
`uint32_be(digest[0:4]) & 0x7fffffff` yields `217570842`, matching the protocol.

## Windows, CRLF, and serialization portability

The repository's effective Windows configuration is `core.autocrlf=true`; no
path-specific `text`, `eol`, or `working-tree-encoding` attribute applies. Git object
bytes are LF-only. Both the review worktree and a fresh detached disposable worktree
materialized the protocol with 8,221 CRLF sequences and raw SHA-256
`e731b577ae4f0cbbe5ee588495157401cf1d9e991176ffc0fc46e54daacb4857`, while canonical
normalization reproduced the accepted LF SHA-256 `f2d73fa3…bce7d`.

Variant results:

| Variant | Result |
|---|---|
| LF Git object | Accepted; exact canonical identity. |
| All CRLF | Accepted after declared LF canonicalization; no false failure. |
| Mixed LF/CRLF | Canonicalizes to the same LF bytes; this is line-ending equivalence, not content equivalence. |
| Lone CR | Rejected. |
| UTF-8 BOM | Rejected. |
| Missing terminal LF | Hash mismatch/rejected. |
| Trailing space or other serialization-content change | Hash mismatch/rejected. |

The exact blinded execution subjects are not checkout text files: their LF bytes are
embedded as base64 with length and SHA-256, so CRLF canonicalization cannot silently
change those packets. The disposable worktree was verified under the exact subject,
then removed; no temporary worktree remains.

## Test, gate, and adversarial results

All Python runs set `PYTHONDONTWRITEBYTECODE=1`, routed `PYTHONPYCACHEPREFIX` and
`COVERAGE_FILE` outside the repository, disabled pytest cache, and used `--no-cov` for
focused pytest. Pre/post inventories found no repository `.coverage`, `.pytest_cache`,
or scoped `__pycache__` artifacts; Git remained clean.

| Command / check | Exact result |
|---|---|
| `python -m pytest -q tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py -p no:cacheprovider --no-cov` | **28 collected, 28 passed** in 41.27s in the attached review worktree. |
| Same focused command in a fresh detached disposable worktree at `87a44dd…` | **28 collected, 28 passed** in 40.74s. |
| `python .claude/hooks/contract_binding_check.py --validate-only` | **PASS**, all gates passed against **101 contracts**. |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | **PASS**, all gates passed against **101 contracts**. |
| Independent authority/census/corpus/hash reconstruction | **PASS** current bytes: 9/9 authorities, 51/51 obligations, 15/15 packages, 120/120 files, 67/67 cases/records. |
| Future-result duplicate-slot/self-attestation candidate | **FAIL contract assurance**: invalid candidate validated with zero schema errors (R2-M1). |
| F-036 subject uniqueness/isolation | **FAIL**: three named mutation cases, one exact subject SHA/packet (R2-M2). |

Green committed tests and framework gates do not waive either Major: the focused future-
schema test checks branch-ID presence rather than full candidate closure, and no committed
test requires distinct mutation-specific F-036 subject semantics.

## Draft PR #122 checks (read-only)

At the exact reviewed head:

- PR state: open draft; head `87a44dd…`; base `4e6fd0c…`; GitHub reports mergeable.
- **Codacy Static Code Analysis:** `ACTION_REQUIRED`. The one annotation is a high-
  severity security warning on
  `tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py:69` for use
  of SHA-1. Direct inspection shows that function computes the mandated Git blob object
  ID (`sha1("blob <len>\0" + payload)`) and the contract also binds SHA-256. This is not
  being used as a cryptographic acceptance digest, so the scanner rationale is not an
  additional design finding; the external check remains non-green.
- **CodeRabbit:** status context `SUCCESS`, but the bot's current comment states the
  review limit was reached and no review started for `4e6fd0c…87a44dd`. It supplied no
  substantive remediation review or inline finding. Its green status is therefore not
  positive review evidence.

No PR state, comment, check, review, or branch was altered by this inspection.

## Decision and owner-gate recommendation

| Decision/gate | Recommendation |
|---|---|
| P-035 sequencing/composition | Keep. The protocol/evidence split and non-compensable M/H graph remain correct. |
| P-036 approved normative revision | Keep. All authority pins resolve exactly. |
| D-G6-2 T1a exact-hash gate | **Remain open.** Do not accept `f2d73fa3…bce7d`. |
| T2–T4 permission | **Blocked** until a remediated T1a revision passes fresh independent review and Stephen accepts its exact hash. |
| T1b/T5–T8 and M/H eligibility | **Blocked.** No execution, result, evidence policy, or eligibility action is authorized. |
| Merge recommendation | **Do not merge PR #122 at `87a44dd…`.** Remediate R2-M1 and R2-M2, re-content-address all dependent artifacts, rerun focused/fresh/gate tests, and obtain a new independent review. |

## Hard-stop confirmation and change log

- No credential was resolved and no model, grader, provider, API, or live transport was
  called.
- No research execution, calibration observation, result instance, evidence package,
  eligibility decision, owner acceptance, claim, migration, cache, or vault record was
  created or changed.
- No T2–T8, WP6.3, WP6.4, WP6.5, or owner-gate action occurred.
- No reviewed protocol, identity manifest, schema, test, normative plan, fixture, Gate 5
  artifact, P0 artifact, result, or source file was edited.
- The disposable exact-subject worktree was removed after testing.
- This review adds exactly this one R2 Markdown report. No task-observer observation was
  logged: the two defects instantiate existing OPEN guidance on cross-field semantic
  bindings, exact relational closure, and producing-seam mutation tests rather than a
  new generalizable skill gap.
