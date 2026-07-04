# ARS P0 WP4 adversarial implementation review

**Date:** 2026-07-04  
**Target:** `codex/ars-p0-wp4` at `f882e29` against `main`  
**Scope:** WP4 Tasks 1–6, the 37-case fixture closure, scenarios A–E, the P0 release path, and retention/deletion integration  
**Reviewer stance:** fresh-context adversarial review using direct source inspection and executable counterexamples  
**Authority boundary:** this report does not approve Gate 5, live providers, a pilot, migration, or a research claim.

## Executive verdict: `rework_required`

WP4 contains useful fail-closed primitives, especially exact result-key closure and evidence-derived deletion status. The runnable P0 path does not, however, establish the assurance claims made by the accepted implementation plan.

Three defects are release-blocking:

1. the public release path can emit `pass` while its own operations status is `blocked` and while the supplied verdict document has not been authenticated or independently re-derived;
2. the committed fixture corpus is largely declarative boilerplate whose inputs, expected outputs, and grader manifests are not consumed by the runtime graders; and
3. four of five “integrated” scenarios return preconstructed success records rather than exercising WP1–WP3 behavior.

The implementation must be split and re-reviewed. The recommended sequence is WP4.1 core contracts/release primitives, WP4.2 retention, WP4.3 fixture authoring infrastructure, three bounded fixture-corpus shards, and a final calibration/integration/release tranche. Each tranche must remain inactive until its prerequisites are present; no partial tranche may claim the 37-case P0 decision.

## Critical findings

### C-1 — The public release path can pass with blocked operations and producer-supplied verdicts

**Claim.** `decide_p0_release()` derives its decision from plain result-row verdict strings and does not make `operations_status` or `parity_status` a decision precondition.

**Evidence.** `research_system/evals/harness.py:169-215` constructs `verdict_by_key` directly from the input document. Lines 211–215 select `blocked`, `fail`, or `pass` before lines 245–246 independently construct parity and operations status. The strict `research_system/evals/release.py::decide_release()` path is not called.

**Executable counterexample.** Starting from `run_p0_coverage()`, changing every result verdict to `pass`, setting `scenario_count` to `0`, removing all scenario records, and setting `candidate_status` to `pass` produced:

```text
decision=pass operations_status=blocked incompatible=()
```

**Failure scenario.** A structurally complete but fabricated evaluation document reaches the human review surface as a P0 pass despite carrying no operations evidence.

**Impact.** Invalid acceptance evidence can be presented to the owner. Gate 5 remains separately unauthorized, but the evidence on which later authorization depends is corrupted.

**Disposition.** **Fix now.** Treat the document as claims, reconstruct typed `GraderResult` records, run one strict validator, and require exact result closure, immutable bindings, parity pass, operations pass, and capability restrictions before `pass`. Add the executable counterexample as a public CLI regression test.

**Proposed interface change.** The final release coordinator must consume a signed or content-bound evaluation snapshot plus per-result immutable bindings and return one `ReleaseAssessment`; it must not maintain a second weaker verdict algorithm.

**Affected decisions/work packages.** P-030; WP4 Tasks 2 and 6; P0 acceptance items 3, 8, 9, 10, and 11.

### C-2 — The 37 fixture packages are not executable incident-specific evidence

**Claim.** The committed `input/`, `expected/`, and `graders/required.json` files do not drive grading. For most fixtures the “oracle” is a boolean generated from whether the caller requested `known_good` or `known_bad`.

**Evidence.** `tools/ars/materialize_p0_fixtures.py:124-145` emits the same generic stimulus and decision shape for every case. `research_system/evals/reference_systems.py:86-127` creates literal evidence keyed by fixture ID and otherwise returns `control_satisfied = subject == 'known_good'`; lines 151–154 grade that same boolean. `load_fixture()` reads only `fixture.yaml` and trusts its declared `source_manifest_hash` (`research_system/evals/catalogue.py:144-164`).

**Failure scenario.** A fixture’s committed stimulus, expected trajectory, or grader manifest can be stale or corrupted while calibration and `eval validate` remain unchanged.

**Impact.** The implementation cannot prove that the historical/specification failure classes are detected. The claimed 37-case closure is a package-count closure, not an executable behavior closure.

**Disposition.** **Reject the current Task 4/5 corpus and rebuild.** Each fixture must encode a minimized input, independent expected property/trajectory, and a grader that consumes those bytes. Package hashes must be recomputed and checked. Generic fallback grading is prohibited for an active fixture.

**Proposed interface change.** Introduce a package validator returning content hashes for every required file and a grader registry that has an explicit implementation for every active fixture/revision/variant tuple. Absence is `fixture_error`.

**Affected decisions/work packages.** P-014, P-019, P-027–P-030; WP4 Tasks 4–5; all 37 fixture cases; P0 acceptance items 1, 4, 5, 6, and 7.

### C-3 — Scenarios A, B, D, and E are assertion-shaped constants

**Claim.** Four “integrated” scenarios manufacture the exact fields their tests assert without invoking the owned command, routing, adapter, or recovery flows.

**Evidence.** `research_system/evals/scenarios.py:45-104` returns literal `Gate3ScenarioResult` objects for A, B, D, and E. Only scenario C calls an implementation function (`resume_from_checkpoint`, lines 74–78). `test_gate3_scenarios.py` then asserts those literals.

**Failure scenario.** WP1 command recovery, WP2 routing, or WP3 provider issuance can regress completely while scenarios A, B, D, and E remain green.

**Impact.** Cross-package integration and operations assurance are absent, and the release document can still count five scenarios.

**Disposition.** **Fix in the final integration tranche.** Drive each scenario through real public ports with deterministic fakes, capture emitted events/receipts, and grade those records. Counting records is not evidence.

**Proposed interface change.** `run_gate3_scenario()` accepts an explicit composed foundation and returns evidence derived from its calls; no scenario branch may directly construct a passing terminal record.

**Affected decisions/work packages.** P-030; WP4 Task 6; WP1–WP3 integration consumers; P0 acceptance items 3 and 10.

## Major findings

### M-1 — The strict release primitive uses coverage-wide scalar hashes for per-result evidence

**Claim.** `release._incompatibility()` expects one `expected_subject_hash`, `expected_trace_hash`, and `expected_policy_hash` for every result in a coverage set, even though W6 binds each grader result to its own subject/trace evidence.

**Evidence.** `research_system/evals/release.py:26-87` treats those three bindings as scalars while oracle, threshold, independence, and criticality are keyed by `ResultKey`. A real multi-fixture coverage cannot correctly use one trace hash for all results.

**Failure scenario.** Either all fixtures are incorrectly forced to share one trace/subject hash, or the strict validator is bypassed—as the current harness does.

**Impact.** The strongest validator cannot represent the actual 37-case evidence set.

**Disposition.** **Fix in WP4.1.** Make every immutable result binding a `ResultKey` mapping and fail closed when any key is absent.

**Proposed interface change.** Coverage supplied to `decide_release()` exposes `expected_subject_hashes`, `expected_trace_hashes`, `expected_oracle_hashes`, `expected_policy_hashes`, and `expected_threshold_policy_hashes` keyed by the exact required result tuple.

**Affected decisions/work packages.** W6 §§22, 24–25; WP4 Tasks 1–2.

### M-2 — Trace completeness ignores issued resource grants

**Claim.** Trace completeness checks only `issued_commands`; a resource grant can lack a terminal receipt or explicit missing-evidence record while the trace is accepted.

**Evidence.** W6 §21 requires every issued provider command **and resource grant** to have terminal or missing evidence. `TraceEnvelope.validate_terminal_evidence()` in `models.py` iterates only `issued_commands`; the schema contains only generic `resource_record_ids`.

**Failure scenario.** An execution loses its lease/checkpoint/stop record after resource issuance, yet grading proceeds with `trace_complete=True`.

**Impact.** Operational incompleteness can be misclassified as complete evidence.

**Disposition.** **Fix in WP4.1.** Add typed `issued_resources` terminal bindings to the model/schema and test command and resource omission independently.

**Affected decisions/work packages.** W6 §21; W8 evidence boundary; WP4 Tasks 1–2.

### M-3 — Calibration failures can be translated into passes

**Claim.** `_result_rows()` converts every non-M/H, non-`fixture_error` aggregate to `pass`, including a known-good calibration verdict of `fail`.

**Evidence.** `research_system/evals/harness.py:94-108`. `calibrate_p0_coverage()` at lines 60–90 counts only known-good `unable_to_grade` and `fixture_error`; it does not enforce known-bad failure, known-good pass, mutation detection, or two independent executions.

**Failure scenario.** A defective oracle returns `fail` for the controlled candidate; the result row presented to release says `pass`.

**Impact.** Calibration regression is hidden rather than quarantined.

**Disposition.** **Fix in the calibration/integration tranche.** Validate every repetition and mutation before generating any result. Unexpected calibration outcomes are `fixture_error`.

**Affected decisions/work packages.** WP4 Tasks 5–6; P0 acceptance item 4.

### M-4 — “Two repetitions” duplicate one computed judgment

**Claim.** Calibration calculates the property verdict once and then emits two records; byte equality is guaranteed by construction.

**Evidence.** `calibration.py::_repeated_decisions()` computes evidence and `property_verdict` before its repetition comprehension. `normalized_bytes` intentionally excludes the repetition number.

**Failure scenario.** A nondeterministic subject or grader is never executed twice, so the determinism policy cannot detect it.

**Impact.** The two-run calibration rule is unfalsifiable.

**Disposition.** **Fix in the calibration tranche.** Execute subject and grader independently per repetition, then compare normalized decisions.

**Affected decisions/work packages.** WP4 Task 5; P0 acceptance item 4.

### M-5 — Validation checks inventory, not schema and package integrity

**Claim.** `eval validate` loads catalogue/coverage and reports success without validating every package instance, package hash, variant binding, or oracle file. The schema-surface test checks only schema filenames.

**Evidence.** `harness.validate_p0_catalogue()` at lines 44–57; `catalogue.load_fixture()` at lines 144–164; `test_eval_schema_surface.py:7-18`.

**Failure scenario.** A malformed or tampered fixture file passes validation if `fixture.yaml` remains parseable.

**Impact.** The CLI’s `status: valid` claim overstates what was checked.

**Disposition.** **Fix in WP4.3.** Validate every JSON/YAML instance, recompute hashes, require exact file closure, and emit the checked package/content hashes.

**Affected decisions/work packages.** WP4 Tasks 1 and 4; P0 acceptance items 1 and 6.

### M-6 — Re-execution reuses the same evaluation-run identity

**Claim.** `EvaluationLifecycle.start()` derives `evaluation_run_id` only from fixture/revision/subject, and its test explicitly requires two executions to share an ID.

**Evidence.** `research_system/evals/lifecycle.py:39-50`; `test_eval_runner.py:52`.

**Failure scenario.** Two attempts collide, making terminal hashes and retry lineage ambiguous.

**Impact.** Immutable attempt provenance and deterministic recovery are weakened.

**Disposition.** **Fix in the final integration tranche.** Allocate a new owner-defined run ID for every execution; use `retry_of`/`supersedes` for lineage. Deterministic content hashes remain separate from identity.

**Affected decisions/work packages.** W6 §§19 and 23; WP4 Task 6.

### M-7 — Exception-limited decisions do not bind an accepted exception policy

**Claim.** `ReleaseGateDecision` can be constructed as `exception_limited` by supplying scope, expiry, constrained capability, and authority ID, without a policy identity/hash.

**Evidence.** `models.py::ReleaseGateDecision.__post_init__`; `release-gate-decision.schema.json`. W6 §25 permits this state only when an accepted policy authorizes it.

**Failure scenario.** A caller manufactures a bounded-looking exception without proving that any accepted policy allows it.

**Impact.** An authority bypass surface exists in the core contract.

**Disposition.** **Fix in WP4.1.** Add exact exception-policy identity/hash fields and require them for `exception_limited`; the release coordinator must verify them against its immutable policy bundle. Until such a policy exists, P0 never emits this decision.

**Affected decisions/work packages.** W6 §25; WP4 Tasks 1–2 and 6; P0 acceptance item 8.

### M-8 — Retention authority admits actor/grant cross-pairing

**Claim.** The evidence-store registry stores independent actor and grant lists, so any listed actor can use any listed grant.

**Evidence.** `retention.py:37-38,193-195`; `evidence-store-registry.schema.json:25-26`.

**Failure scenario.** Actor A presents actor B’s still-current grant; both values are separately present and `authority_current=True`.

**Impact.** Deletion verification can be attributed to an unauthorized actor/grant pair.

**Disposition.** **Fix in WP4.2.** Store exact actor/grant bindings and test cross-pair rejection.

**Affected decisions/work packages.** WP4 Task 3; retention/deletion authority boundary.

### M-9 — The required per-grader evidence selector is absent

**Claim.** `GraderRequirement` records class/version/criticality/independence but not the W6-required evidence selector.

**Evidence.** W6 §20 requires grader evidence selectors. `models.py::GraderRequirement` and `$defs.graderRequirement` in the fixture schema omit them.

**Failure scenario.** A grader can choose a convenient subset of the trace without violating its declared contract.

**Impact.** Grader scope is ambiguous and gameable.

**Disposition.** **Fix in WP4.1.** Add a non-empty, immutable evidence-selector tuple and schema coverage.

**Affected decisions/work packages.** W6 §§20–22; WP4 Tasks 1–2.

## Minor findings and retained strengths

- **m-1 — Hard-coded decision time.** `harness.py` emits `decided_at='2026-07-03T00:00:00Z'`; use an injected trusted clock and bind the clock source.
- **m-2 — Loose schema members.** Several schemas permit arbitrary object-shaped trace items and untyped verdict tuples. Tighten these when the owner records are integrated.
- **m-3 — Retention discovery trust boundary.** Deletion completeness is only as strong as the injected replica discovery and canonical-payload scanner. Preserve this as an explicit Gate 5 dependency for S-014.
- **m-4 — Strong primitive retained.** `release.decide_release()` correctly blocks empty, partial, stale, duplicate, unexpected, incompatible, `unable_to_grade`, and `fixture_error` evidence when supplied a complete keyed binding set.
- **m-5 — Strong retention direction retained.** `verify_deletion()` derives status from inspections and `validate_deletion_manifest_for_event()` rechecks location closure; retain this structure while fixing M-8.
- **m-6 — Gate 5 restrictions retained.** S-014/S-015/S-016 remain explicit capability restrictions and cannot be silently inserted into the 37-case P0 set.

## Task disposition

| WP4 task | Disposition | Reason |
|---|---|---|
| Task 1 — models and schemas | **amend/re-review** | M-2, M-7, M-9 and loose instance validation |
| Task 2 — trace and release closure | **amend/re-review** | M-1 and C-1 integration gap; retain exact-set primitive |
| Task 3 — retention | **amend/re-review** | M-8; retain derived-status/location-closure design |
| Task 4 — fixture packages | **reject/rebuild** | C-2 and M-5 |
| Task 5 — paired calibration | **reject/rebuild** | C-2, M-3, M-4 |
| Task 6 — scenarios and release | **reject/rebuild** | C-1, C-3, M-6 |

## Scenario disposition

| Scenario | Disposition | Direct execution status |
|---|---|---|
| A — R2 production/verification | **reject current evidence** | literal record; no integrated route/provider/grader execution |
| B — provider outage | **reject current evidence** | literal record; no real reroute path |
| C — stop/checkpoint/resume | **amend** | calls checkpoint compatibility code, but not the complete scenario |
| D — writer crash/restore | **reject current evidence** | literal record; no crash-window execution |
| E — restricted-data denial | **reject current evidence** | literal record; no real pre-issue denial path |

## Fixture-catalogue disposition

Every required case has an explicit disposition below. “Rebuild” means retain the accepted ID and failure class but replace the generic package/oracle with executable, input-derived evidence.

| Fixture group | IDs | Disposition |
|---|---|---|
| Control/store | F-001, F-002, F-003, F-004, F-005, S-001, S-002, S-006, S-008, S-009, S-010, S-011, S-012 | **rebuild all 13**; current generic boolean oracle cannot exercise overwrite, root, atomicity, authority, or branch divergence |
| Context/routing | F-021, F-022, F-025, F-026, F-027, F-028, F-031, F-033, F-035 | **rebuild all 9**; F-022/F-026/F-035 need explicit independence, closure-sizing, and two-key predicates |
| Adapter/operations | F-007, F-008, F-009, F-010, F-020, F-032, F-034, S-003, S-004, S-013 | **rebuild all 10**; exercise real fake adapters, receipts, limits, and operational profiles |
| Scientific/anti-gaming | F-011, F-012, F-013, F-014, F-036 | **rebuild all 5**; retain the useful property functions but make them consume package inputs; F-036 must derive rather than trust mutation evidence |

## Cross-spec consistency matrix

| Invariant | Required enforcement | Current evidence | Disposition |
|---|---|---|---|
| Exact required-result tuple closure | keyed coverage vs keyed results | strict primitive passes adversarial omission battery | **keep; fix per-key hashes (M-1)** |
| Trace completeness includes commands and resources | terminal/missing evidence per issuance | commands only | **amend (M-2)** |
| Producer verdict is not proof | typed recomputation and immutable bindings | public path trusts row verdict | **violated (C-1)** |
| Fixture property comes from immutable inputs | package hash + input-derived grader | generic files and boolean fallback | **violated (C-2)** |
| Two repetitions are two executions | execute subject/grader twice | one judgment duplicated | **violated (M-4)** |
| Calibration failure quarantines fixture | exact known-bad/good/mutation checks | known-good fail can become pass | **violated (M-3)** |
| Operations evidence is non-compensable | operations pass required for release pass | pass can coexist with blocked operations | **violated (C-1)** |
| Integrated scenarios exercise WP1–WP3 | real ports + deterministic fakes | four literal records | **violated (C-3)** |
| Every execution has unique identity | new run ID + lineage | deterministic collision | **violated (M-6)** |
| Exception is policy-authorized | accepted policy ID/hash + bounded scope | bounded fields only | **violated (M-7)** |
| Deletion verifier authority is exact | actor/grant pair binding | independent lists | **violated (M-8)** |
| Gate 5 remains unauthorized | explicit restrictions | enforced | **keep** |

## P0 acceptance checklist disposition

| Acceptance item | Disposition |
|---|---|
| Exact 37 cases and explained omissions | **shape holds; executable closure fails C-2** |
| R1/R2 policy, owners and deletion path | **amend M-8; otherwise retain** |
| Non-compensable critical/required results | **strict primitive holds; public path fails C-1** |
| Two-run paired calibration and mutations | **fails M-3/M-4** |
| F-021 remains P1 at P0 materialization | **holds** |
| No raw restricted data/secrets/transcripts | **holds for committed corpus inspected** |
| Independent M/H evidence or blocking | **legitimate run blocks; forged document passes C-1** |
| Only pass/fail/blocked absent accepted exception policy | **fails M-7 contract surface** |
| Gate 5 remains closed | **holds** |
| Fresh review of F-011/F-012/F-022/F-026/F-035/F-036 | **completed here; all require rebuild or input binding** |
| Owner accepts evidence before live use | **not yet reached; no acceptance authorized** |

## Practicality and proportionality

The main overhead is not the core Python surface; it is the 296-file fixture corpus. Preserve the accepted eight-file package layout, but review it in bounded semantic shards rather than hiding it with CodeRabbit path filters. The proposed split keeps each PR below 150 files and makes each review responsibility coherent:

1. WP4.1 core evaluation contracts and exact release primitive;
2. WP4.2 retention/deletion authority;
3. WP4.3 fixture authoring infrastructure;
4. control/store corpus (13 packages, approximately 104 files);
5. context/routing corpus (9 packages, approximately 72 files);
6. adapter/operations/scientific corpus (15 packages, approximately 120 files);
7. calibration, integrated scenarios, coverage activation, release coordinator, and CLI.

Only one PR should be open for review at a time. Every branch starts from the newly merged predecessor on `main`.

## Revision plan

### Immediate corrections

- WP4.1: fix M-1, M-2, M-7, and M-9; add schema instance tests and exact omission/incompatibility attacks.
- WP4.2: bind verifier actor/grant pairs and preserve evidence-derived status.
- WP4.3: implement package/schema/hash/variant validation without claiming active 37-case coverage.

### Corpus reconstruction

- Replace generic stimuli and expected files with minimized behavior-specific packages.
- Remove generic fallback grading for active fixtures.
- Require every package to pass known-bad, known-good, mutation, safe-variation, and tamper tests applicable to its contract.

### Final integration

- Run two actual repetitions.
- Drive scenarios through real WP1–WP3 ports.
- Route release through one typed strict validator.
- Prove the C-1 forged-document counterexample blocks.
- Activate exact 37-case coverage only after all package shards are merged.

## Residual risks

- Deterministic fakes cannot establish live M/H authority; those capabilities remain blocked.
- Replica discovery remains an assured-component dependency before S-014.
- Provider-token evidence remains provider/revision-specific; counts from different tokenizers are not interchangeable.
- A passing WP4.1 does not repair fixture or integration evidence and must not be represented as a P0 decision.

## Verification evidence

- Direct review of all WP4 runtime modules, schemas, policies, fixture generator, representative fixture packages, and WP4 tests at `f882e29`.
- Commit/file inventory: 346 changed files; 296 under `.research-system/evals/fixtures/**`.
- Existing ARS regression suite previously reported 247 passing tests; this does not override the executable counterexamples above.
- Executed C-1 counterexample on 2026-07-04:

```powershell
uv run python -c "from research_system.evals.harness import run_p0_coverage,decide_p0_release; d=run_p0_coverage(); [r.update(verdict='pass') for r in d['results']]; d['scenario_count']=0; d['scenarios']=[]; d['candidate_status']='pass'; a=decide_p0_release(d); print(a.decision.decision, a.decision.operations_status, a.incompatible)"
```

Observed: `pass blocked ()`.

## Change log

- Added this findings-only report.
- No implementation, fixture, policy, runtime, migration, provider, pilot, or research state was changed during the review.
