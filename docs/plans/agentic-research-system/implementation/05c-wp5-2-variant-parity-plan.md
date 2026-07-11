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
approved only when Stephen approves this exact plan after review.

## Dispatch Gate and Global Constraints

- **Never implement from this documentation branch.** Work begins only after PR
  #78 has independent review, CodeRabbit has concluded, and its exact reviewed
  head (currently dependency evidence
  50fa4fffe89ebc6f6069838d5ffe6ea5a024cf95) is merged to main. The Worker
  proves its eventual merge contains that head with git merge-base --is-ancestor,
  creates pipe/ars-gate5-variant-parity with git switch -c from that detached
  merge commit, and reports branch plus exact HEAD before editing.
- Stephen must explicitly approve this WP5.2 plan and its D-G5-3 table before
  the first implementation write. A planning-branch merge is not approval.
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

## File Map

**Create:**

~~~
research_system/evals/variants.py
research_system/policy/loader.py
tests/research_system/integration/test_gate5_variant_execution.py
tests/research_system/unit/test_policy_loader.py
~~~

variants.py owns typed matrix loading, exact row/coverage binding, fake-only
execution, twice-run normalized-decision comparison, and variant result
expansion. loader.py owns loading the committed canonical policy and its
canonical content hash; it never reads provider configuration from the
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
.research-system/schemas/evals/release-gate-decision.schema.json
tests/research_system/unit/test_adapter_parity.py
tests/research_system/unit/test_canonical_ids.py
tests/research_system/unit/test_coverage.py
tests/research_system/unit/test_eval_models.py
tests/research_system/unit/test_release_gate.py
tests/research_system/unit/test_variant_matrix.py
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

## Obligation Register

| ID | Source | Obligation | Owner | Disposition |
|---|---|---|---|---|
| V1 | 04b R8 / Gate 5 scope | Run every Gate-5 matrix row on its exact fixture revision via fake Claude/Codex only | WP5.2 | Tasks 1-2 |
| V2 | 05-plan §7.3 / 04a O1 | Each Gate-5 row runs twice with byte-identical normalized decisions | WP5.2 | Task 2 |
| V3 | W7 §17 / 04a O11 | Field-by-field semantic parity; one missing critical control blocks | WP5.2 | Task 3 |
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
  D-G5-3 table; CONVENTIONS.md.
- **Parameters/seeds:** none. Record matrix/fixture/provider/runtime revisions,
  two normalized-decision hashes, canonical policy bundle ID/revision/hash,
  parity report ID/hash, and source commit.
- **Contract disposition:** no new contracts/ research contract. Accepted W6/W7
  schemas and public-seam negative tests are enforcement artifacts. Assert exact
  values/types, not key presence.
- **Machine-checkable claims:** exact row selection/binding; fake-only twice-run
  equality; exact 302-key closure; one complete W7 row per canonical control;
  required provider dispositions/evidence; critical-gap blocking independent of
  diagnostic percentage; schema-valid report identity/hash; derived parity
  status; invariant smoke.
- **Human-review-only:** whether each fake manifest proves an actual adapter
  behaviour rather than a label; whether the report honestly limits itself to
  fake evidence while retaining every W7 control; whether release provenance
  proves the report rather than reproducing pass.
- **Output provenance:** no research result/cache. Durable evidence is committed
  code/schemas/tests, generated checks, two-run hashes, temporary output
  documents, review/PR, obligation closure, and a top-of-page [PIPELINE] vault
  entry.
- **Partial:** unbound row, live/secrets requirement, missing critical control,
  percentage/caller-forced parity pass, result-key/schema failure, invariant
  drift, or new out-of-scope surface.

## Task 1: Bind Gate-5 rows and variant result keys

**Files:** create variants.py; modify models.py, coverage.py, the two
result-key schemas, and the named matrix/coverage/model/release tests.

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

- [ ] **Step 1: write red tests.** In test_variant_matrix.py assert the exact
  46 rows, binding to selected revisions, and rejection of wildcard/duplicate/
  stale copies before any transport call. In test_coverage.py and
  test_eval_models.py assert six-item keys and schema rejection of a five-item
  key or blank variant.
- [ ] **Step 2: run red.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_variant_matrix.py tests/research_system/unit/test_coverage.py tests/research_system/unit/test_eval_models.py -q --no-cov
~~~

  Record named failures; collection/environment failure is not red evidence.
- [ ] **Step 3: implement only typed loading and key closure.** Canonically
  order full row tuples. Keep all matrix/package bytes unchanged. Do not execute
  an adapter or build parity in this task.
- [ ] **Step 4: run green.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_variant_matrix.py tests/research_system/unit/test_coverage.py tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_release_gate.py -q --no-cov
uv run --no-sync python tools/ars/materialize_p0_variant_matrix.py --check
~~~

- [ ] **Step 5: commit.** Subject: [PIPELINE] P00: bind Gate 5 matrix rows to result closure

## Task 2: Execute every fake variant twice (R8)

**Files:** modify variants.py, harness.py, coverage.py, models.py, and the named
variant/release-coordinator tests; create test_gate5_variant_execution.py.

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
- run_p0_coverage combines 132 baseline results and 170 variant grader results,
  binding every six-element key in the strict maps. The CLI eval run surface
  therefore emits exactly 302 results.

- [ ] **Step 1: write red public-seam tests.** The real coverage/harness seam
  with a FakeTransport spy must show 46 rows, two equal normalized byte strings
  per row, 170 variant plus 132 baseline results, exact release closure, and no
  subprocess/live path. A deliberately changed second fake receipt must block
  before evidence. test_release_coordinator.py must show 302 unique keys and a
  blocked decision from expected capability blocks, not an omitted row.
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

## Task 3: Produce W7 evidence and bind it to release (O11)

**Files:** create policy/loader.py; modify adapters/parity.py, harness.py,
models.py, cli.py, the ID registry, three listed schemas, and named parity/CLI/
model tests.

**Interfaces:**

- load_canonical_policy_bundle reads only
  .research-system/policies/canonical-policy.yaml, calculates canonical content
  hash, and returns every semantic control sorted. The W7 required-risk/
  capability field is the committed control semantic_class; do not invent a
  provider-specific equivalence map.
- build_parity_report is the production seam. It emits exactly one row per
  control with control ID/revision, semantic class, criticality/failure mode,
  fake Claude and fake Codex disposition, evidence identifiers/hashes,
  consequence, and owner/resume condition. It emits ppr_ identity, canonical
  report hash, source bundle ID/revision/hash, sorted blockers, passed, and
  diagnostic-only percentage. Register policy_parity_report: ppr and validate.
- Accepted dispositions are native, generated, adapter_enforced, unsupported,
  and divergent. Missing fake manifest/evidence, duplicate or unknown control,
  unsupported, divergent, or diagnostic_only on a critical control gives that
  row consequence blocked, adds it to blockers, and sets passed=false. A
  percentage never changes that result.
- The report derives from actual fake adapter executions and the canonical
  bundle, never caller status. It discloses fake-only variants and makes no
  live-provider claim.
- EvaluationEvidence carries the typed report. build_release_decision records
  policy_parity_report_id/hash and derives not_evaluated only when no report
  exists, blocked for a valid failing report, and pass only for a schema-valid,
  complete, no-blocker report. No constructor default, CLI flag, percentage, or
  plain dictionary can make pass. The release schema requires report ID/hash
  for parity pass or blocked.

- [ ] **Step 1: write red tests.** test_adapter_parity.py and
  test_policy_loader.py require all four committed controls once with both
  provider dispositions/evidence. Exercise missing Claude, missing Codex,
  missing one critical control, divergent projection, missing evidence hash,
  and high percentage with a critical gap; each blocks. Byte-different but
  semantically complete projections may pass.

  test_eval_cli.py and test_eval_models.py must prove no report is
  not_evaluated, forged passed=true cannot create pass, a complete real fake
  report stores ID/hash, and a missing critical control gives blocked. A valid
  fake report may be parity pass while candidate remains blocked due to M/H.
- [ ] **Step 2: run red.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_policy_loader.py tests/research_system/unit/test_adapter_parity.py tests/research_system/unit/test_canonical_ids.py tests/research_system/unit/test_eval_models.py tests/research_system/integration/test_eval_cli.py -q --no-cov
~~~

- [ ] **Step 3: implement typed report and release binding.** Validate the
  report before it enters EvaluationEvidence and validate release serialization
  after its references are included. A completed fake report cannot lift M/H,
  O15, gate5_authorized, or live-provider restrictions. Do not publish a W2
  canonical event; that is WP5.3.
- [ ] **Step 4: run green.**

~~~
uv run --no-sync pytest tests/research_system/unit/test_policy_loader.py tests/research_system/unit/test_adapter_parity.py tests/research_system/unit/test_canonical_ids.py tests/research_system/unit/test_eval_models.py tests/research_system/integration/test_gate5_variant_execution.py tests/research_system/integration/test_eval_cli.py -q --no-cov
uv run --no-sync ruff check research_system/adapters/parity.py research_system/policy/loader.py research_system/evals/harness.py research_system/evals/models.py research_system/cli.py tests/research_system
~~~

- [ ] **Step 5: commit.** Subject: [PIPELINE] P00: bind W7 parity evidence to release decisions

## Task 4: Verify, close obligations, and hand off

**Files:** modify only O11's disposition in the 04a register, R8's disposition
in the 04b register, and prepend one reconciled [PIPELINE] entry to
vault/04-Methods/Computational-Log.md after all evidence succeeds.

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
  and carry a valid ppr_ ID/hash, parity_status=pass, 302 required verdicts,
  decision=blocked, canonical_event_ref=unpublished:p0, and no authorization.
  Compare stable projections and all 46 normalized-decision hash pairs.
  Different IDs/timestamps are not nondeterminism; declared normalized
  projections must match exactly.
- [ ] **Step 4: run negative controls.** Remove one critical fake Codex
  control/evidence, alter a bound matrix revision, and alter one second-run
  fake receipt. Assert, respectively: parity-blocked release, pre-execution
  matrix rejection, and repeat-mismatch rejection. Restore test doubles only;
  do not change a committed oracle. No negative path may issue a live call.
- [ ] **Step 5: close only evidence-backed records.** Mark O11 delivered only
  when report-to-release is present; mark R8 delivered only when 46 rows have
  twice-run evidence. The vault entry records 40/15/302/0/calibrated/blocked,
  46/170 derivation, output/report hashes, commands, source merge/branch/
  commits, fake-only limit, D-G5-1(a), D-G5-2/O15, and gate5_authorized=false.
  It must not claim Gate 5 acceptance or a research result.
- [ ] **Step 6: commit, push, and report.** Subject:
  [PIPELINE] P00: close Gate 5 variant-parity obligations. Push a ready PR;
  do not merge. The Worker report includes changed files, exact source merge
  commit, red/green evidence, 46 IDs/two-run hashes, 132+170=302 derivation,
  invariant JSON, parity report ID/hash/row count/blockers, generated checks,
  full gate timing, register/vault paths, fake-only/restriction statement, and
  every Partial item.

## Acceptance Criteria

1. Work began from the independently reviewed WP5.4 merge, not this plan branch,
   and only after Stephen approved D-G5-3/WP5.2.
2. Each of 46 committed rows binds its selected revision, uses only an injected
   fake Claude/Codex/counting path, and has two byte-identical normalized
   decisions.
3. Strict release closure has 302 unique six-element keys: 132 baseline plus
   170 row-specific variants; no grader result is overwritten or ignored.
4. W7 evidence has one full row per canonical control, both provider
   dispositions/evidence, and non-compensable critical-gap blocking.
5. Release references a schema-valid real report by ID/hash; it cannot retain
   not_evaluated after the real run or default to pass. The normal fake run has
   parity pass yet candidate blocked.
6. Exact 40/15/302/0/calibrated/blocked and gate5_authorized=false hold; M/H
   and O15 restrictions remain explicit.
7. Materializer checks, ruff, full suite, schema validation, two-run inspection,
   generated-input audit, and git diff --check all pass.
8. O11/R8 and the vault entry are evidence-backed; the ready PR has no
   unresolved critical/high Manager or CodeRabbit finding.

## Stop Conditions

Stop Partial and escalate if:

1. PR #78 is unreviewed/unmerged, source merge cannot be proven to contain its
   reviewed head, or Stephen has not approved this plan/D-G5-3 table.
2. Baseline is not exactly 40 fixtures, 15 blocked, 132 results, 0
   uncalibrated, calibrated, blocked; or matrix derivation is not exactly 46
   rows/170 added results.
3. A row is stale, unbound, wildcarded, duplicated, needs a matrix/fixture
   rewrite, or cannot run twice fake-only.
4. Variant identity cannot be carried through accepted W6 schemas without an
   unplanned W6/W2 redesign.
5. A canonical control lacks actual fake evidence; a critical gap is averaged
   away; caller input can force pass; or the report needs live access, secret,
   .env, hidden reasoning, raw transcript, or network.
6. Any invariant drifts, or a test turns green only by weakening an oracle,
   grader, threshold, control, or restriction.
7. WP5.3, WP5.4 code, O15 implementation, live policy, Gate 6, research
   computation, or paper claims become necessary.

## Independent Manager Review Criteria

Before accepting the report or merging, independently verify:

- reviewed WP5.4 merge ancestry and owner approval;
- 40/15/132 baseline and 132+170=302 arithmetic from coverage, matrix, and
  required graders;
- all 46 bindings, fake-only transport evidence, and two-run hash pairs;
- parity schema/ID/hash/full rows plus a critical-gap negative that percentage
  cannot mask;
- release derives parity from the report, preserves canonical_event_ref=
  unpublished:p0, M/H/O15 restrictions, gate5_authorized=false, and blocked;
- generated checks, full gates, scoped diff, register/vault claims, CodeRabbit
  conclusion, and no unresolved critical/high finding.

Approval phrase: **Approved D-G5-3 / WP5.2 plan**. Approval authorizes only
this bounded implementation after the WP5.4 merge; it does not authorize Gate 5
acceptance, live providers, O15 closure, WP5.3 publication, or Manager merge
without independent review.
