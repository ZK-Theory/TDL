# ARS Work Package 5.2: Variant Execution and W7 Parity-Evidence Implementation Plan

> **For the implementing Worker:** use contract-first-tdd and
> research-assurance-triage. Write one failing public-seam test per behaviour.
> The accepted W6/W7 specifications and this approved dispatch plan are the
> control-plane contract authority; do not author a new mathematical contract.

**Status:** draft for Manager/PR review and Stephen's D-G5-3 approval. This is
not implementation authority.

**Goal:** discharge 04b R8 and 04a O11 by executing every Gate-5 matrix row
against its bound fixture revision through deterministic fake Claude/Codex
paths, and attach a real W7 semantic parity report to release evidence. The
foundation remains capability-restricted and **blocked**; this package neither
accepts Gate 5 nor enables a live capability.

**Architecture:** retain WP5.4's 40-case FOUNDATION_CASES coverage. A typed
matrix seam selects committed execution_stage: gate5 rows, verifies every
fixture/revision binding, and runs each row twice through FakeTransport. It
compares canonical normalized-decision bytes before adding result evidence. The
W7 report is calculated by research_system/adapters/parity.py from the
committed canonical policy and the two fake-adapter evidences. Its identity and
hash, never a caller-supplied boolean, determine parity_status in the release
decision.

**Owner authorization:** Stephen approved Gate 5 scope, D-G5-1(a), and D-G5-4
on 2026-07-10. D-G5-2/O15 remains deferred. D-G5-3 for this package is
approved only when Stephen approves this exact plan after review. **D-G5-5 is
open:** W7 requires a risk/capability applicability mapping that current
canonical policy does not contain; Stephen must approve that mapping before
implementation can produce a passing parity report.

## Dispatch Gate and Global Constraints

- **Never implement from this documentation branch.** Work begins only after PR
  #78 has independent review, CodeRabbit has concluded, and its exact reviewed
  head (currently candidate dependency head
  f6450248bc5a40352ed01a06641012f48188eac7) is merged to main. The Worker
  proves its eventual merge contains that head with git merge-base --is-ancestor,
  creates pipe/ars-gate5-variant-parity with git switch -c from that detached
  merge commit, and reports branch plus exact HEAD before editing.
- Stephen must explicitly approve this WP5.2 plan and its D-G5-3 table before
  the first implementation write. A planning-branch merge is not approval.
- **D-G5-5 is an additional owner gate, not an implementation inference.** W7
  section 17 requires each parity row to name where its control is mandatory,
  but the accepted canonical policy exposes only `semantic_class`, `critical`,
  and `failure_mode`. `semantic_class` is not a risk/capability applicability
  declaration. Before Task 3, Stephen must approve an exact no-wildcard mapping
  in the typed source and schema specified below. If it is absent, stale, or
  lacks an accepted decision reference, the Worker reports Partial and stops;
  it must not assign values such as `all`, derive them from a class name, or
  reuse a fixture label as policy applicability.
- Before every write and commit, verify the intended worktree, branch,
  scope-understood status, and reviewed-WP5.4 merge ancestry. The Worker commits
  and reports; the Manager alone merges after independent review.
- Fake Claude/Codex only: use injected FakeTransport, synthetic fixture roots,
  and committed fake counting/adapter revisions. Never read, copy, or source
  .env; never use credentials, a live provider, local provider CLI, network
  access, or restricted/raw research data.
- D-G5-1(a) is literal: M/H rows remain blocking; no live threshold policy,
  fabricated cross-family identity, fallback, or accepted M/H row. D-G5-2/O15
  is literal: do not add DeleteEvidenceObject or EvidenceDeletionPending.
- gate5_authorized remains false and candidate_status remains blocked. A fake
  parity pass documents only the bounded fake-adapter surface; it cannot
  authorize Gate 5, live providers, or a capability restriction.
- Do not edit the generated matrix, its generator, fixture packages, coverage
  selection, WP5.4 release-tranche implementation, WP5.3 event publication,
  live-grader policy, Gate 6, research results, or paper claims. They are
  verification inputs only.
- Preserve exact result-key closure and anti-anchoring. Missing, stale,
  duplicate, unexpected, or unbound matrix/grader evidence blocks release; no
  oracle, threshold, calibration policy, or expected count is adjusted to pass.
- Use uv run --no-sync. Commit subjects use [PIPELINE] P00: and a
  Co-Authored-By trailer. Write multiline messages to a BOM-free UTF-8 file and
  use git commit -F; never use --no-verify.

## Exact D-G5-3 Re-baseline

This pre-registration is derived from committed artifacts, not estimated.

| Invariant | Post-WP5.4 baseline | WP5.2 target | Exact derivation and smoke assertion |
|---|---:|---:|---|
| fixture_count | 40 | **40** | WP5.2 adds no package; 46 rows re-execute bound selected revisions. Assert 40. |
| blocked_fixture_count | 15 | **15** | Existing fourteen M/H blocks plus S-016's H row remain under D-G5-1(a). Assert 15. |
| result_count | 132 | **302** | 132 + 170. The matrix has 46 rows: 30 adapter/rendering and 16 sizing. Two providers multiply 53 adapter/rendering required-grader rows plus 32 sizing required-grader rows: 2 x (53 + 32) = 170. A terminal variant_id makes them distinct. Assert 302. |
| fixtures_with_uncalibrated_mutations | 0 | **0** | Repetition adds no mutation or calibration relaxation. Assert 0. |
| mutation_calibration | calibrated | **calibrated** | Existing two-repetition calibration stays binding. Assert exact token. |
| candidate_status | blocked | **blocked** | M/H blocks and gate5_authorized=false remain. Assert exact token. |

The 132 baseline is independently proven by the read-only WP5.4 head:
40 selected fixtures plus S-014/S-015/S-016 result tuples 4 + 2 + 4 gives
122 + 10 = 132. The WP5.4 head leaves the shared matrix unchanged. Its 46
Gate-5 rows expand as follows:

- Adapter/rendering fixture grader counts per provider: F-007 through F-014,
  F-020, F-032, F-034, F-036, S-003, S-004, S-013 =
  4+4+4+3+3+4+3+3+3+5+4+4+3+3+3 = 53.
- Sizing fixture grader counts per provider: F-022, F-025 through F-028,
  F-031, F-033, F-035 = 4+4+5+2+3+4+5+5 = 32.
- Added result keys = 2 x (53 + 32) = 170; target = 132 + 170 = 302.

D-G5-3 approval covers only this table. It does not accept Gate 5.

## D-G5-5: Owner-Approved W7 Control Applicability

**Decision required before implementation:** Stephen must approve the exact
W7 control-to-applicability-and-evidence mapping. The accepted W7 text requires
the field but does not supply values for the four current policy controls, so
the Worker cannot derive them from `semantic_class` or fixture names.

The only accepted runtime source is the committed,
schema-validated `.research-system/policies/gate5-policy-control-applicability.yaml`.
It is valid only when all of the following are true:

- its `decision_ref` is the owner-recorded **D-G5-5** decision and its
  `decision_record_hash` equals the accepted decision record;
- it binds the exact canonical policy bundle ID, revision, and content hash;
- it contains each and only each canonical control exactly once, with that
  control's exact revision, non-empty explicit `required_risk_tiers` and
  `required_capabilities`, and no wildcard/default/fallback field;
- for each required fake provider it contains exact evidence selectors:
  `(fixture_id, fixture_revision, variant_id, provider_variant)`, each of
  which resolves to a committed `execution_stage: gate5` matrix row; and
- every selector names the exact post-control assertion property and expected
  evidence hash that the actual execution must satisfy. The source is an
  applicability/evidence map, never a claimed provider disposition.

`.research-system/schemas/adapters/policy-control-applicability.schema.json`
defines that source and rejects missing, extra, stale, duplicate, unknown, or
wildcard controls/selectors. `load_policy_control_applicability` returns its
frozen typed model only after schema and bundle binding validation. There is no
default applicability model. Until D-G5-5 is accepted and this file validates,
the required outcome is **Partial — owner applicability mapping required**.

## File Map

**Create:**

~~~
research_system/evals/variants.py
research_system/adapters/parity_evidence.py
research_system/policy/loader.py
.research-system/policies/gate5-policy-control-applicability.yaml
.research-system/schemas/adapters/fake-adapter-parity-evidence.schema.json
.research-system/schemas/adapters/policy-control-applicability.schema.json
.research-system/schemas/evals/variant-execution-evidence.schema.json
tests/research_system/integration/test_gate5_variant_execution.py
tests/research_system/unit/test_fake_adapter_parity_evidence.py
tests/research_system/unit/test_policy_control_applicability.py
tests/research_system/unit/test_policy_loader.py
~~~

variants.py owns typed matrix loading, exact row/coverage binding, fake-only
execution, twice-run normalized-decision comparison, execution-derived observed
assertion evidence, and variant result expansion. The variant-execution schema
fixes the immutable record and its content-addressed hash.
`parity_evidence.py` owns the frozen fake-parity evidence model and
the sole builder from completed variant execution to control/provider evidence.
loader.py owns loading the committed canonical policy and the D-G5-5
applicability source; it never reads provider configuration from the
environment.

**Modify only for the interfaces below:**

~~~
research_system/adapters/parity.py
research_system/evals/models.py
research_system/evals/coverage.py
research_system/evals/harness.py
research_system/cli.py
.research-system/config/id-kind-registry.yaml
.research-system/schemas/adapters/parity-report.schema.json
.research-system/schemas/evals/coverage-manifest.schema.json
.research-system/schemas/evals/grader-result.schema.json
.research-system/schemas/evals/release-gate-decision.schema.json
tests/research_system/unit/test_adapter_parity.py
tests/research_system/unit/test_canonical_ids.py
tests/research_system/unit/test_coverage.py
tests/research_system/unit/test_eval_models.py
tests/research_system/unit/test_eval_schema_surface.py
tests/research_system/unit/test_release_gate.py
tests/research_system/unit/test_variant_matrix.py
tests/research_system/unit/test_wp3_configuration.py
tests/research_system/integration/test_eval_cli.py
tests/research_system/integration/test_release_coordinator.py
docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md
docs/plans/agentic-research-system/implementation/04b-wp4-9-corpus-restore-to-spec-plan.md
vault/04-Methods/Computational-Log.md
~~~

Do not modify the matrix, any fixture directory, tools/ars/materialize_*.py,
p0-coverage.yaml, provider YAMLs, WP5.4 files, research_system/command,
research_system/projection, or a W2 event surface. If this cannot be done
through the listed W6/W7 schemas and evaluation seams, stop Partial rather than
widen scope.

The existing adapter capability-manifest schema is not a parity-evidence input:
it has no per-control disposition/evidence binding. Do not extend or accept a
duck-typed manifest as a substitute for the new typed D-G5-5 applicability and
fake-adapter evidence surfaces.

## Obligation Register

| ID | Source | Obligation | Owner | Disposition |
|---|---|---|---|---|
| V0 | W7 §17 applicability field | Approve exact control risk/capability and matrix-evidence applicability mapping | Stephen | **D-G5-5 owner gate; Partial/stop until accepted** |
| V1 | 04b R8 / Gate 5 scope | Run every Gate-5 matrix row on its exact fixture revision via fake Claude/Codex only | WP5.2 | Tasks 1-2 |
| V2 | 05-plan §7.3 / 04a O1 | Each Gate-5 row runs twice with byte-identical normalized decisions | WP5.2 | Task 2 |
| V3 | W7 §17 / 04a O11 | Field-by-field semantic parity from typed, bound fake execution evidence; one missing critical control blocks | WP5.2 | Task 3 after V0 |
| V4 | W7 §§16,20-21 | No live provider/secrets; capability absence never drops a control | WP5.2 | Tasks 2-3 |
| V5 | D-G5-3 | Hold exact 40/15/302/0/calibrated/blocked values | Owner/WP5.2 | This table; Task 4 |
| V6 | D-G5-1(a), D-G5-2/O15 | Keep M/H and deletion-initiation restrictions explicit | WP5.2/WP5.6 | All tasks |
| V7 | Review discipline | Generated checks, evidence-backed register/vault closeout, ready PR, independent review | Worker/Manager | Task 4 |

## Research Assurance Requirements

- **Assurance lanes:** Output/Provenance primary; Authority and Operations at
  the W7/W6 adapter boundary. No topology, statistical, representation, or
  paper-claim calculation changes.
- **Sources:** Gate 5 scope §§2-8; 05-plan §§4.4,5,7.2-7.3; 04a O11; 04b R8/R12;
  W7 §§7-10,13-17,19-21,23-24; W6 F-020 and S-016; D-G5-1(a), D-G5-2; this
  D-G5-3 table; the owner-approved D-G5-5 applicability decision/source;
  CONVENTIONS.md.
- **Parameters/seeds:** none. Record matrix/fixture/provider/runtime revisions,
  two normalized-decision hashes, canonical policy bundle ID/revision/hash,
  D-G5-5 applicability ID/hash/decision hash, per-control/provider execution
  evidence IDs/hashes, parity report ID/hash, and source commit.
- **Contract disposition:** no new contracts/ research contract. Accepted W6/W7
  schemas and public-seam negative tests are enforcement artifacts. Assert exact
  values/types, not key presence.
- **Machine-checkable claims:** exact row selection/binding; fake-only twice-run
  equality; exact 302-key closure; one complete W7 row per canonical control;
  required provider dispositions/evidence; typed control-to-provider-to-row
  bindings; rejection of plain/self-attested manifests; critical-gap blocking
  independent of diagnostic percentage; schema-valid evidence/report identity/
  hash; derived parity status; grader-result schema round trip; invariant smoke.
- **Human-review-only:** whether each fake manifest proves an actual adapter
  behaviour rather than a label; whether the report honestly limits itself to
  fake evidence while retaining every W7 control; whether release provenance
  proves the report rather than reproducing pass.
- **Output provenance:** no research result/cache. Durable evidence is committed
  code/schemas/tests, generated checks, two-run hashes, temporary output
  documents, review/PR, obligation closure, and a top-of-page [PIPELINE] vault
  entry.
- **Partial:** absent/unapproved D-G5-5 mapping, unbound row, live/secrets
  requirement, missing critical control, plain/self-attested parity evidence,
  percentage/caller-forced parity pass, result-key/schema failure, invariant
  drift, or new out-of-scope surface.

## Task 1: Bind Gate-5 rows and variant result keys

**Files:** create variants.py; modify models.py, coverage.py,
grader-result.schema.json, the two result-key schemas, and the named
matrix/coverage/model/schema/release tests.

**Interfaces:**

- load_gate5_variant_rows(matrix_path, coverage) loads only rows with
  execution_stage exactly gate5. It requires fixture_id, fixture_revision,
  variant_id, provider_variant, runtime_variant, os, transport, and
  operational_profile; count rows also retain reference_count, exact_tokens,
  and evaluated_tokens.
- It rejects a missing field, wildcard, duplicate fixture_id/variant_id,
  unknown fake provider revision, stale fixture revision, or fixture outside
  selected 40-case coverage before execution.
- Extend ResultKey with a terminal, non-empty variant_id. Baseline rows use
  literal baseline; Gate-5 rows use their exact matrix variant_id. Update
  GraderResult.result_key, all binding maps, and both W6 schemas from five to
  six items while retaining grader_class at index 3.
- Add `variant_id` as a required, non-empty field of the existing
  `ars://evals/grader-result` schema and to the frozen GraderResult model's
  value validation. The baseline producer at `run_p0_coverage` must emit the
  exact literal `baseline`; the Gate-5 producer must emit exactly the bound
  matrix variant. No caller may omit, blank, or replace that field after
  construction.

- [ ] **Step 1: write red tests.** In test_variant_matrix.py assert the exact
  46 rows, binding to selected revisions, and rejection of wildcard/duplicate/
  stale copies before any transport call. In test_coverage.py and
  test_eval_models.py assert six-item keys and schema rejection of a five-item
  key or blank variant. Add public schema round-trip tests that serialize a
  baseline GraderResult through SchemaRegistry, assert `variant_id ==
  "baseline"`, and reject missing/blank variant_id; a Gate-5 row must round-trip
  with its exact matrix variant.
- [ ] **Step 2: run red.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_variant_matrix.py tests/research_system/unit/test_coverage.py tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_eval_schema_surface.py -q --no-cov
~~~

  Record named failures; collection/environment failure is not red evidence.
- [ ] **Step 3: implement only typed loading and key closure.** Canonically
  order full row tuples. Keep all matrix/package bytes unchanged. Do not execute
  an adapter or build parity in this task.
- [ ] **Step 4: run green.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_variant_matrix.py tests/research_system/unit/test_coverage.py tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_eval_schema_surface.py tests/research_system/unit/test_release_gate.py -q --no-cov
uv run --no-sync python tools/ars/materialize_p0_variant_matrix.py --check
~~~

- [ ] **Step 5: commit.** Subject: [PIPELINE] P00: bind Gate 5 matrix rows to result closure

## Task 2: Execute every fake variant twice (R8)

**Files:** modify variants.py, harness.py, coverage.py, models.py, and the named
variant/release-coordinator tests; create the variant-execution-evidence schema
and test_gate5_variant_execution.py.

**Interfaces:**

- execute_gate5_variant_rows_twice receives typed rows, loaded coverage,
  fixture/schema roots, and a fake transport factory. It runs each row twice
  through the matching fake Claude/Codex adapter or fake counting revision. It
  must never construct SubprocessTransport, invoke a provider CLI, or consult
  live adapter configuration.
- Each attempt emits an identity-free canonical normalized-decision projection:
  full matrix tuple, fixture/oracle/policy/threshold hashes, normalized receipt
  semantics, sorted grader verdicts, and blocking reason. IDs/timestamps are
  excluded only from this declared comparison projection. The two canonical byte
  strings must match; otherwise reject before adding results.
- The runner returns a schema-valid frozen `VariantExecutionEvidence` record
  for each of the 46 rows: exact matrix tuple, first and second
  normalized-decision hashes, equality status, sorted six-element grader result
  keys, sorted `ObservedAssertionEvidence`, and an
  `execution_evidence_hash`. Each observed-assertion record is derived
  independently from the actual normalized result of both fake attempts; it
  binds the exact matrix tuple and fixture revision, assertion property,
  `first_observed_value_hash`, `second_observed_value_hash`, and equality
  status. An observed-value hash is
  `sha256(canonical_bytes({property, canonical_observed_value}))`; neither the
  expected D-G5-5 hash nor a caller-supplied label may populate it. The two
  attempts must have exact assertion-property-set equality and equal hashes
  before evidence is admitted.
- The execution hash is
  `sha256(canonical_bytes({matrix_tuple, first_hash, second_hash,
  sorted(result_key, verdict, trace_hash, oracle_hash, policy_hash,
  threshold_policy_hash), sorted(observed_assertion_evidence)}))`. Typed model
  validation recomputes the hash while the schema fixes the represented fields;
  together they reject a missing, extra, duplicate, stale,
  property-mismatched, fixture-mismatched, or changed assertion record. `VariantExecutionEvidence` is the only execution input
  Task 3 may bind; raw transport stdout, arbitrary dicts, hand-authored manifest
  labels, and the D-G5-5 expected mapping are not observed execution evidence.
- run_p0_coverage combines 132 baseline results and 170 variant grader results,
  binding every six-element key in the strict maps. The CLI eval run surface
  therefore emits exactly 302 results.

- [ ] **Step 1: write red public-seam tests.** The real coverage/harness seam
  with a FakeTransport spy must show 46 rows, two equal normalized byte strings
  per row, schema round-trip of every immutable execution record, independently
  derived and equal observed-assertion evidence from both attempts, 170 variant
  plus 132 baseline results, exact release closure, and no subprocess/live path.
  A deliberately changed second fake receipt or observed assertion must block
  before evidence. Reject missing, extra, duplicate, changed, stale-fixture, or
  matrix-mismatched assertion evidence and an execution hash that omits it.
  test_release_coordinator.py must show 302 unique keys and a blocked decision
  from expected capability blocks, not an omitted row.
- [ ] **Step 2: run red.**

~~~
uv run --no-sync pytest tests/research_system/integration/test_gate5_variant_execution.py tests/research_system/integration/test_release_coordinator.py -q --no-cov
~~~

- [ ] **Step 3: implement minimal fake-only execution.** Reuse current
  calibration/oracle validation. Bind each result to the exact matrix variant_id
  and preserve fake provider/counting revision in evidence. A stale row fails
  before fixture execution.
- [ ] **Step 4: run green.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_variant_matrix.py tests/research_system/integration/test_gate5_variant_execution.py tests/research_system/integration/test_release_coordinator.py tests/research_system/unit/test_release_gate.py -q --no-cov
uv run --no-sync ruff check research_system/evals/variants.py research_system/evals/harness.py research_system/evals/coverage.py research_system/evals/models.py tests/research_system/integration/test_gate5_variant_execution.py
~~~

- [ ] **Step 5: commit.** Subject: [PIPELINE] P00: execute Gate 5 fake provider variants

## Task 3: Produce load-bearing W7 parity evidence and bind it to release (O11)

**Precondition:** D-G5-5 is recorded and the exact applicability source in
this plan validates. Otherwise do not write a parity producer or report
implementation; return **Partial — owner applicability mapping required**.

**Files:** create policy/loader.py, adapters/parity_evidence.py, the D-G5-5
applicability YAML, both new adapter schemas, the Task 2 variant-execution
schema, and the named applicability/evidence tests; modify adapters/parity.py,
harness.py, models.py, cli.py, the
ID registry, parity/release schemas, test_wp3_configuration.py, and named
parity/CLI/model tests.

**Interfaces:**

- load_canonical_policy_bundle reads only canonical-policy.yaml and returns
  sorted controls plus canonical content hash. load_policy_control_applicability
  reads the D-G5-5 YAML, validates the new applicability schema, verifies
  decision and bundle ID/revision/hash equality, and returns a frozen
  PolicyControlApplicability. It never substitutes semantic_class for
  applicability and never reads a provider environment/configuration.
- PolicyControlApplicability contains one ControlApplicability per canonical
  control and exact ProviderEvidenceRequirement values. Each requirement has
  accepted required risk tiers/capabilities, provider variant, matrix selector,
  post-control assertion property, and expected assertion evidence hash. The
  loader rejects missing, extra, stale, duplicate, conflicting, incompatible,
  and wildcard controls/providers/selectors.
- build_fake_adapter_parity_evidence in parity_evidence.py is the sole producer
  accepted by build_parity_report. It accepts frozen VariantExecutionEvidence,
  the typed applicability source, and the loaded canonical bundle; it rejects a
  dict, protocol, duck-typed manifest, precomputed disposition, or raw receipt.
- For every exact control -> provider -> selector requirement, the producer
  resolves one and only one of the 46 completed execution records. It verifies
  the complete matrix tuple, equal first/second normalized-decision hashes,
  exact sorted six-element grader result keys, and exact completeness of the
  execution-derived observed-assertion set. It then resolves exactly one
  `ObservedAssertionEvidence` record by the D-G5-5-required property and
  compares that record's equal first/second observed-value hash to the
  owner-approved expected hash. The owner mapping is only the comparator: it
  cannot supply or replace observed evidence. The producer may not reread raw
  fixtures, transport output, or caller dictionaries. It emits a frozen
  FakeAdapterParityEvidence record with the Task 2 execution_evidence_hash,
  selected observed-assertion property/hash, and a content-addressed evidence
  ID:

  evidence_id = fpe_ + sha256(canonical_bytes(bundle ID/revision/hash,
  applicability hash, control ID/revision, provider variant, matrix tuple,
  execution evidence hash, selected observed assertion property/hash,
  sorted grader result keys)).

  The fake-evidence schema fixes this relationship and validates the ID/hash
  pair. Fake paths may not claim native. adapter_enforced is derived only after
  every exact bound execution and assertion succeeds; a claimed native or
  adapter_enforced disposition without typed bound evidence is rejected.
- Missing, extra, stale, duplicate, provider-mismatched, result-key-mismatched,
  assertion-missing, assertion-extra, assertion-duplicate,
  assertion-property-mismatched, assertion-hash-mismatched, incompatible, or
  self-attested evidence blocks its control. The producer
  proves a bounded fake adapter surface and makes no live-provider claim.
- build_parity_report(bundle, applicability, evidence_records) accepts only
  those three frozen typed inputs. It requires exact equality between the
  D-G5-5 control/provider requirement set and evidence set, then emits one W7
  row with control ID/revision, accepted risk/capability applicability, fake
  provider disposition, bound evidence IDs/hashes, consequence, and
  owner/resume condition. It emits ppr_ identity, canonical report hash, bundle
  and applicability IDs/hashes, sorted blockers, passed, and diagnostic-only
  percentage. Register policy_parity_report: ppr and validate.
- A missing/unsupported/divergent/diagnostic-only critical control is blocked;
  percentage cannot compensate. The existing capability-manifest interface is
  not accepted as an alternate producer.
- EvaluationEvidence carries the typed report. build_release_decision records
  policy_parity_report_id/hash and the applicability ID/hash; it derives
  not_evaluated only when no report exists, blocked for a valid failing report,
  and pass only for a schema-valid, complete, no-blocker report. No constructor
  default, CLI flag, percentage, or plain dictionary can make pass. The release
  schema requires report ID/hash for parity pass or blocked.

- [ ] **Step 1: write red tests.** test_policy_control_applicability.py and
  test_policy_loader.py require a D-G5-5 decision/bundle-bound source with all
  and only canonical controls and explicit risk/capability fields. Prove that
  absent decision evidence, semantic_class substitution, missing/extra/stale/
  duplicate/wildcard selector, or incompatible policy revision fails before
  any provider execution.

  test_fake_adapter_parity_evidence.py constructs real typed 46-row execution
  evidence and requires every control/provider requirement to resolve to one
  exact record and one execution-derived observed assertion. Reject
  arbitrary/plain manifests, self-attested evidence, missing/extra/stale/
  duplicate/provider-incompatible records, missing/extra/duplicate assertion
  records, changed execution hash, changed grader result key, changed observed
  assertion property/hash, a second-run assertion mismatch, and an owner
  expected hash passed off as an observed hash. Explicitly prove a claimed
  native or adapter_enforced disposition cannot reach a passing report without
  bound execution and observed-assertion evidence.

  test_adapter_parity.py requires complete control/provider/evidence equality,
  critical-gap blocking, and non-compensability by high percentage.
  test_eval_cli.py and test_eval_models.py prove no report is not_evaluated,
  forged passed=true cannot create pass, a complete real fake report stores
  report and applicability IDs/hashes, and a missing critical control gives
  blocked. A valid fake report may be parity pass while candidate remains
  blocked due to M/H.
- [ ] **Step 2: run red.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_policy_loader.py tests/research_system/unit/test_policy_control_applicability.py tests/research_system/unit/test_fake_adapter_parity_evidence.py tests/research_system/unit/test_adapter_parity.py tests/research_system/unit/test_canonical_ids.py tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_wp3_configuration.py tests/research_system/integration/test_eval_cli.py -q --no-cov
~~~

- [ ] **Step 3: implement only after D-G5-5 evidence is present.** Validate
  the applicability source, each fake evidence record, and the report before it
  enters EvaluationEvidence; validate release serialization after report
  references are included. A completed fake report cannot lift M/H, O15,
  gate5_authorized, or live-provider restrictions. Do not publish a W2
  canonical event; that is WP5.3.
- [ ] **Step 4: run green.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_policy_loader.py tests/research_system/unit/test_policy_control_applicability.py tests/research_system/unit/test_fake_adapter_parity_evidence.py tests/research_system/unit/test_adapter_parity.py tests/research_system/unit/test_canonical_ids.py tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_wp3_configuration.py tests/research_system/integration/test_gate5_variant_execution.py tests/research_system/integration/test_eval_cli.py -q --no-cov
uv run --no-sync ruff check research_system/adapters/parity.py research_system/adapters/parity_evidence.py research_system/policy/loader.py research_system/evals/harness.py research_system/evals/models.py research_system/cli.py tests/research_system
~~~

- [ ] **Step 5: commit.** Subject: [PIPELINE] P00: bind W7 parity evidence to release decisions

## Task 4: Verify, close obligations, and hand off

**Files:** modify only O11's disposition in the 04a register, R8's disposition
in the 04b register, and prepend one reconciled [PIPELINE] entry to
vault/04-Methods/Computational-Log.md after D-G5-5 and all evidence succeed.

- [ ] **Step 1: run generated-input checks.**

~~~
uv run --no-sync python tools/ars/materialize_control_store_fixtures.py --root .research-system/evals/fixtures --check
uv run --no-sync python tools/ars/materialize_context_routing_fixtures.py --root .research-system/evals/fixtures --check
uv run --no-sync python tools/ars/materialize_adapter_scientific_fixtures.py --root .research-system/evals/fixtures --check
uv run --no-sync python tools/ars/materialize_p0_variant_matrix.py --check
uv run --no-sync python tools/ars/materialize_gate5_release_tranche.py --check
~~~

  Every command must be byte-identical. Audit that the matrix, packages, and
  materializers have no scoped diff.
- [ ] **Step 2: run full gates.**

~~~
uv run --no-sync ruff check research_system tools/ars tests/research_system
uv run --no-sync pytest tests/research_system -q --no-cov
uv run --no-sync python -m research_system.cli eval validate --catalogue .research-system/evals/catalogue.yaml
uv run --no-sync python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
git diff --check
~~~

  Assert validate selects 40; calibration emits 40, 15, 0, calibrated; run
  emits candidate_status=blocked and result_count=302.
- [ ] **Step 3: inspect two release documents.** Write two eval run --output
  documents to distinct temporary, non-tracked paths. Both must be schema-valid
  and carry valid ppr_ report and D-G5-5 applicability IDs/hashes,
  parity_status=pass, 302 required verdicts, decision=blocked,
  canonical_event_ref=unpublished:p0, and no authorization. Compare stable
  projections, all 46 normalized-decision hash pairs, and each control ->
  provider -> content-addressed fake-evidence ID/hash binding. Different
  IDs/timestamps are not nondeterminism; declared normalized projections and
  all content-addressed evidence projections must match exactly.
- [ ] **Step 4: run negative controls.** Remove one critical fake Codex
  control/evidence, alter a bound matrix revision, and alter one second-run
  fake receipt. Assert, respectively: parity-blocked release, pre-execution
  matrix rejection, and repeat-mismatch rejection. Also exercise absent D-G5-5
  decision source, semantic_class substituted for applicability, missing/extra/
  stale/duplicate/provider-incompatible evidence, and a claimed native or
  adapter_enforced disposition with no bound execution record. Every case must
  fail before parity pass. Restore test doubles only; do not change a committed
  oracle. No negative path may issue a live call.
- [ ] **Step 5: close only evidence-backed records.** Mark O11 delivered only
  when D-G5-5 applicability and typed report-to-release are present; mark R8
  delivered only when 46 rows have twice-run evidence. The vault entry records
  40/15/302/0/calibrated/blocked, 46/170 derivation, D-G5-5 decision/source
  hash, control/provider evidence IDs/hashes, output/report hashes, commands,
  source merge/branch/commits, fake-only limit, D-G5-1(a), D-G5-2/O15, and
  gate5_authorized=false. It must not claim Gate 5 acceptance or a research
  result.
- [ ] **Step 6: commit, push, and report.** Subject:
  [PIPELINE] P00: close Gate 5 variant-parity obligations. Push a ready PR;
  do not merge. The Worker report includes changed files, exact source merge
  commit, red/green evidence, 46 IDs/two-run hashes, 132+170=302 derivation,
  invariant JSON, D-G5-5 applicability decision/source hash, parity report and
  control/provider evidence IDs/hashes/row count/blockers, generated checks,
  full gate timing, register/vault paths, fake-only/restriction statement, and
  every Partial item.

## Acceptance Criteria

1. Work began from the independently reviewed WP5.4 merge, not this plan branch,
   and only after Stephen approved D-G5-3/WP5.2 and D-G5-5 applicability.
2. Each of 46 committed rows binds its selected revision, uses only an injected
   fake Claude/Codex/counting path, and has two byte-identical normalized
   decisions.
3. Strict release closure has 302 unique six-element keys: 132 baseline plus
   170 row-specific variants; no grader result is overwritten or ignored.
4. A schema-valid D-G5-5 source supplies accepted risk/capability applicability
   and exact control -> provider -> matrix selector bindings; semantic_class is
   never treated as applicability.
5. Each W7 disposition is produced only from content-addressed typed evidence
   bound to an actual execution record whose immutable hash includes
   independently derived, two-run-equal observed-assertion evidence. The
   owner-approved expected property/hash is only a comparator; arbitrary/
   self-attested manifests, unbound assertions, unbound native claims, and
   unbound adapter_enforced claims are rejected.
6. W7 evidence has one full row per canonical control, both provider
   dispositions/evidence, and non-compensable critical-gap blocking.
7. Release references schema-valid applicability and real report IDs/hashes; it
   cannot retain not_evaluated after the real run or default to pass. The normal
   fake run has parity pass yet candidate blocked.
8. Exact 40/15/302/0/calibrated/blocked and gate5_authorized=false hold; M/H
   and O15 restrictions remain explicit.
9. Materializer checks, ruff, full suite, schema validation, two-run inspection,
   generated-input audit, and git diff --check all pass.
10. O11/R8 and the vault entry are evidence-backed; the ready PR has no
   unresolved critical/high Manager or CodeRabbit finding.

## Stop Conditions

Stop Partial and escalate if:

1. PR #78 is unreviewed/unmerged, source merge cannot be proven to contain its
   reviewed head, Stephen has not approved this plan/D-G5-3 table, or D-G5-5
   is not an accepted exact applicability decision/source.
2. Baseline is not exactly 40 fixtures, 15 blocked, 132 results, 0
   uncalibrated, calibrated, blocked; or matrix derivation is not exactly 46
   rows/170 added results.
3. A row is stale, unbound, wildcarded, duplicated, needs a matrix/fixture
   rewrite, or cannot run twice fake-only.
4. Variant identity cannot be carried through accepted W6 schemas without an
   unplanned W6/W2 redesign.
5. A source derives applicability from semantic_class/fixture labels, permits a
   wildcard/default, lacks decision/bundle binding, or an evidence/assertion
   record is missing/extra/stale/duplicate/incompatible/self-attested; observed
   assertion evidence is not derived independently from both fake runs and
   included in execution_evidence_hash.
6. A canonical control lacks actual fake evidence; a claimed native or
   adapter_enforced disposition lacks its exact bound execution record; a
   critical gap is averaged away; caller input can force pass; or the report
   needs live access, secret, .env, hidden reasoning, raw transcript, or
   network.
7. Any invariant drifts, or a test turns green only by weakening an oracle,
   grader, threshold, control, or restriction.
8. WP5.3, WP5.4 code, O15 implementation, live policy, Gate 6, research
   computation, or paper claims become necessary.

## Independent Manager Review Criteria

Before accepting the report or merging, independently verify:

- reviewed WP5.4 merge ancestry, D-G5-3 approval, and the owner-recorded
  D-G5-5 applicability decision;
- 40/15/132 baseline and 132+170=302 arithmetic from coverage, matrix, and
  required graders;
- all 46 bindings, fake-only transport evidence, and two-run hash pairs;
- D-G5-5 schema/source bundle binding and exact no-wildcard control ->
  provider -> matrix selector applicability, including proof that semantic_class
  was not substituted;
- typed variant-execution and fake-evidence schemas; execution-hash derivation
  from the actual 46 records plus independently derived two-run observed
  assertions; exact expected-property/hash comparison, evidence-ID/hash
  derivation, and requirement/evidence equality; and negatives for
  plain/self-attested, missing/extra/stale/duplicate/incompatible execution or
  assertion evidence and unbound native/adapter_enforced claims;
- parity schema/ID/hash/full rows plus a critical-gap negative that percentage
  cannot mask;
- release derives parity from typed applicability and report evidence, preserves
  canonical_event_ref=unpublished:p0, M/H/O15 restrictions,
  gate5_authorized=false, and blocked;
- generated checks, full gates, scoped diff, register/vault claims, CodeRabbit
  conclusion, and no unresolved critical/high finding.

Approval phrase: **Approved D-G5-3 / WP5.2 plan**. Approval authorizes only
this bounded implementation after the WP5.4 merge; it does not authorize Gate 5
acceptance, live providers, O15 closure, WP5.3 publication, or Manager merge
without independent review.
