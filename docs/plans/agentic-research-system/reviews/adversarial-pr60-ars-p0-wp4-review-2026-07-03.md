# Adversarial Design/Implementation Review — PR #60 (ARS P0 WP4 evaluation foundation)

- **Target:** PR #60 `[PIPELINE] P00: complete ARS P0 WP4 evaluation foundation` (branch `codex/ars-p0-wp4`, base `main`), +8191 / 346 files.
- **Reviewer stance:** fresh-context adversary, direct evidence only. Ran the actual CLI against forged inputs in a throwaway detached worktree.
- **Date:** 2026-07-03
- **Grounding docs:** `docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md`, `.../design/06-evaluation-observability-and-audit.md`, `.../design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md`, `.../05-p0-materialization-and-foundation-implementation-plan.md`.
- **Authority note:** This review does **not** accept the generated `ReleaseGateDecision` as owner approval and does **not** authorize Gate 5. No owner-reserved decision is enacted. No source files were edited (findings-only; the throwaway worktree used for the PoC was removed).

---

## Executive verdict: `rework_required`

The structural spine of the PR is genuinely strong: exact required-result closure defeats every *structural* pass-on-omission variant I threw at it (empty, partial, duplicate, extra, stale-binding, incompatible), the S-014/S-015/S-016 capability restrictions cannot be lifted through data, Gate 5 cannot be self-authorized through the document, and the retention/deletion module derives (rather than accepts) its verdict and enforces registered-location closure in both directions. The PR is also honest: the legitimate run is correctly `blocked`, and the author asked reviewers to attack exactly the surfaces that turned out to matter.

But two foundational invariants of the assurance design are violated by the *runnable* path, and I confirmed both with executable PoCs:

1. **The release gate certifies producer-supplied verdicts it never re-derives.** A structurally-perfect evaluation-runs file with the 18 mandatory `unable_to_grade` (M/H) verdicts flipped to `pass` yields `decision: pass`, rationale `p0_evidence_complete_owner_review_required`. This is precisely "producer pass flag accepted as property proof," which design/05 §metrics sets to a target of `0`.
2. **Graders do not recompute from the fixtures' immutable inputs.** The entire committed fixture data tree (input/expected/source-manifest/required.json across all 37 cases — most of the 8191 lines) is inert: I corrupted a fixture's data files to `{"CORRUPTED": true}` and every grading outcome and the `validate` result were byte-identical. Verdicts come from Python literals switched on `fixture_id`; `source_manifest_hash` is a self-declared YAML string that is never checked against the inputs.

Because this is the *foundation* later gates inherit, these must be closed before the artifact can be relied on as evidence. The closure and retention scaffolding is sound and should be kept.

---

## Critical findings

### C-1 — Release gate anchors on producer-supplied verdicts (pass-on-fabrication)

- **Claim.** `decide_p0_release` decides `pass`/`fail`/`blocked` from the `verdict` string in each row of an on-disk document it does not authenticate or re-derive.
- **Evidence.** `research_system/cli.py:168-182` (`_eval_release` → `_read_json(args.evaluation_runs)` reads an untrusted file) → `research_system/evals/harness.py:169-215`. `decide_p0_release` builds `verdict_by_key` straight from `row.get('verdict')` (harness.py:199-209) and never recomputes it, never cross-checks it against the deterministic `calibrate_fixture`/`_result_rows` ground truth that is available in-process, and never asserts that M/H classes are `unable_to_grade`.
- **Governing invariant.** design/05:365 "the producer's own `passed` flag is ignored"; design/05:31 "producer-emitted pass flags and sanity targets are not proof"; design/06:39 "graders do not trust producer-emitted pass flags … they recompute or independently bound the property from immutable inputs"; design/05:619 target metric "producer pass flag accepted as property proof: `0`".
- **PoC (executed).** From the legitimate `eval run` document (122 results, `blocked`, 18 M/H `unable_to_grade`), I flipped every non-pass verdict to `pass` and set `candidate_status: pass`, leaving `coverage_revision`, all binding fields, `omitted_gate5`, and `gate5_authorized: False` untouched. `eval release` returned:
  ```
  DECISION: pass
  rationale: p0_evidence_complete_owner_review_required
  missing/unexpected/duplicates/incompatible: 0 0 0 0
  ```
- **Failure scenario.** Any producer, or any process that can write the evaluation-runs JSON the release CLI reads, can manufacture a `p0_evidence_complete` PASS from fixtures that in reality cannot be graded (no live M/H provider). That PASS is the exact input an owner would weigh at Gate 5.
- **Impact (bounded, but material).** The forged PASS still carries `gate5_authorized: False`, `disabled_or_constrained_capability: foundation_release_and_pilot_promotion`, and the intact S-014/15/16 restrictions (altering any of these is caught — see the battery below), so this path does **not** itself authorize Gate 5 or lift capability restrictions. The damage is **evidence integrity**: it misrepresents P0 completeness to the human authority. Under the rubric ("permit invalid acceptance") this is Critical because it corrupts the evidence the owner's acceptance rests on.
- **Disposition — fix now.** In `decide_p0_release`, re-derive the expected verdict set deterministically from `coverage` (`_result_rows`/`calibrate_fixture` are pure and in-process) and treat the document as *claims to be checked*, not evidence: fail closed on any row whose `verdict` (and `required`/`critical`) differs from the re-derivation, and explicitly assert every `M`/`H` key is `unable_to_grade`. Equivalently, route the decision through `release.decide_release` over reconstructed `GraderResult` records (see M-2) so the hash/independence bindings actually run. Bind the document to its producing run (signature or recomputed content hash compared to an expected value) rather than only hashing whatever was supplied.
- **Affected work packages.** WP4 Task "release assessment"; consumers of any emitted `ReleaseGateDecision`.

### C-2 — Graders never read the fixtures' immutable inputs; the fixture data tree is inert

- **Claim.** No code in `research_system/evals/` reads any fixture `input/`, `expected/`, or `graders/required.json` file. The only per-fixture file read at runtime is `fixture.yaml`. Verdicts derive from hardcoded Python evidence keyed on `fixture_id`.
- **Evidence.** `research_system/evals/calibration.py:141-146` calls `build_reference_evidence(fixture.fixture_id, failure_class, subject)` and `build_f036_mutation_evidence(mutation_id, subject)` — both return literal dicts switched on the id (`reference_systems.py:86-181`). `catalogue.py:144-164` `load_fixture` reads `source_manifest_hash` as `str(payload['source_manifest_hash'])` from the YAML — it is **not** computed from `input/source-manifest.json`. A repo-wide search shows the input/expected/required.json paths are written only by the generator `tools/ars/materialize_p0_fixtures.py`, never read by the runtime.
- **Governing invariant.** design/06:39 and design/05:31 require recomputation "from immutable inputs"; design/06:243 states the property predicate as `scientific_property_recomputed(property, input_hashes)`. `oracle_authority: 'fixture_input_recomputation_v1'` (harness.py:123, calibration.py:81) names a recomputation from fixture inputs that does not occur.
- **PoC (executed).** Overwrote `F-012/{input,expected,graders}` files with `{"CORRUPTED": true}` (leaving `fixture.yaml` intact). `eval calibrate` before/after: **no diff** (`37 fixtures, 23 fully_graded, 14 unable_to_grade, status blocked` both times); `eval validate` still `status: valid`.
- **Failure scenario.** A fixture whose committed input/expected data is wrong, stale, or tampered still calibrates and validates cleanly, because the data is decorative. The "37-case catalogue" is, for grading, 37 `fixture.yaml` files plus a `fixture_id` switch.
- **Impact.** Claim-traceability and evidence fidelity: the PR presents an elaborate materialized fixture corpus as the evidentiary basis of P0, but the graders cannot detect any defect in that corpus. Any future confidence that "F-0xx is covered" is unfounded at the input level.
- **Disposition — fix now (or amend the claim).** Either (a) have `grade_reference_evidence`/the F-036 grader load and recompute from the committed `input/`+`expected/` files and have `load_fixture` recompute `source_manifest_hash` over the actual input tree and reject a mismatch; or (b) if literal evidence is an accepted P0 simplification, amend the WP4 acceptance text and rename `oracle_authority` away from `fixture_input_recomputation_v1`, and file a P1 dependency to wire real input recomputation before any gate relies on fixture-level coverage.
- **Affected work packages.** WP4 fixture materialization + calibration; every finding's fixture (F-001…S-013).

---

## Major findings

### M-1 — Finding-specific graders exist only for F-011/F-012/F-013/F-014; F-022/F-026/F-035 (and all other cases) are graded by a generic `control_satisfied` boolean

- **Evidence.** `reference_systems.py:130-154` `grade_reference_evidence` special-cases only F-011/012/013/014; everything else returns `pass_or_fail(evidence.get('control_satisfied') is True and observed_failure_class == 'none')`, and `build_reference_evidence:124-127` returns `{'control_satisfied': good, ...}` where `good = subject == 'known_good'`. So the "known_good passes / known_bad fails" behaviour for F-022 (independence actor comparison), F-026 (mandatory-closure retrieval sizing), and F-035 (two-key non-compensation) is a tautology of the subject label, not a test of the mechanism the finding names.
- **Governing spec.** design/02:1065 (F-022 "compares producer/verifier actors, sessions, model families, context manifests, trace visibility"); 06b:23 (F-035 "Both Key A and Key B must pass independently; no producer dispatch … on the weakened record"); design/03 §18.2 (F-026 mandatory-closure sizing under both token gates). None of these predicates is implemented in the graded path.
- **Impact.** The attack surfaces named in the prompt (oracle independence for F-022; two-key non-compensation for F-035; registered-closure sizing for F-026) are not exercised at all — the fixtures pass by construction.
- **Disposition — fix now or defer with explicit claim amendment.** Implement the per-finding predicates, or explicitly scope F-022/F-026/F-035 as "shape-only, mechanism deferred to WP2/W5" in the WP4 acceptance and coverage manifest so the coverage claim is not overstated.

### M-2 — The strong verification apparatus (`release.decide_release` + `validate_grader_result` + `GraderResult`) is not wired to the CLI

- **Evidence.** `research_system/evals/release.py:103-160` `decide_release` performs the real hash/independence/staleness checks via `graders.py::validate_grader_result` (subject/trace/oracle/policy/threshold hashes, `context_relationship`, `independently_recomputed`, cross-family `producer_family != grader_family`). `GraderResult` (models.py:262-311) carries all those fields. But the CLI path (`_eval_release` → `decide_p0_release`) consumes plain dict rows from `_result_rows` (harness.py:94-126) that contain only `fixture_id, result_key, verdict, required, critical, oracle_authority` — none of the hash/independence fields — and `decide_p0_release` never calls `validate_grader_result`. `decide_release` is only reachable in unit tests with hand-built coverage stubs; worse, it cannot run against a real `P0Coverage` because `P0Coverage` (coverage.py:31-48) declares none of the `expected_*`/`required_independence`/`required_criticality` attributes `_incompatibility` looks for (release.py:26-53), so every result would be flagged `coverage bindings missing`.
- **Impact.** The independence and anti-staleness guarantees the design leans on are implemented but dead on the runnable path; C-1 is the direct consequence.
- **Disposition — fix now.** Either populate `P0Coverage` with the per-key expected bindings and route the CLI through `decide_release` over reconstructed `GraderResult`s, or fold the equivalent checks into `decide_p0_release`. Add a test that asserts the *CLI* path rejects a forged all-`pass` document (the C-1 PoC as a regression test).

### M-3 — "Paired calibration, two repetitions" is a single computation duplicated; byte-stability is vacuous

- **Evidence.** `calibration.py:133-165` `_repeated_decisions` computes `property_verdict`/`verdict`/`reason` **once**, then emits `repetitions` copies via a comprehension over `range(1, repetitions+1)`. `_decision`'s `normalized_bytes` (calibration.py:108-120) excludes the repetition index, so both repetitions are byte-identical by construction. `independently_recomputed=True` is hardcoded (calibration.py:117,128) regardless of what happened.
- **Governing spec.** The threshold policy requires `acceptance: exact_property_satisfied_every_repetition` with `repetitions: 2` (enforced in coverage.py:102-108). The intent — detect nondeterminism/flakiness across genuine re-executions — cannot be met, because the grader is not re-executed; the second repetition is a copy of the first.
- **Impact.** The determinism guarantee the two-repetition policy is meant to provide is unfalsifiable. Combined with the hardcoded `independently_recomputed=True`, the "independent recomputation" flag carries no information.
- **Disposition — fix now.** Actually invoke the grader once per repetition and compare the resulting `normalized_bytes` for equality; stop hardcoding `independently_recomputed`.

### M-4 — F-036 mutation grader compares producer-supplied fields; no independent oracle / expected-value derivation

- **Evidence.** `reference_systems.py:59-83` `grade_f036_mutation`: for `expected_value_anchoring` it checks `evidence['independently_recomputed'] is True and evidence['observed_value'] == evidence['recomputed_value']` — both `recomputed_value` and the boolean come from the same evidence mapping the producer would supply; the grader derives nothing. `degenerate_fallback` trusts `used_degenerate_fallback`/`support_count`; `null_invariance` trusts the two signatures. In the P0 harness these are fed by the hardcoded `build_f036_mutation_evidence`, so all three mutations do fail their `known_bad` and pass `known_good` — but the grader provides no oracle independent of the evidence author.
- **Governing spec.** 06b:23 requires graders to "derive or challenge the expected value, exercise the real computation and forced fallback, and recompute tested-object identity"; design/05:356 "The verifier independently derives or challenges it. Suspicious agreement triggers an anchoring review." A string-equality of two supplied fields is exactly the anchoring anti-pattern the spec names.
- **Impact.** The anti-gaming guarantee F-036 is supposed to demonstrate is not enforced against a real (or adversarial) producer; it is asserted by fixture bookkeeping.
- **Disposition — fix now or scope-amend.** Have the grader recompute `recomputed_value`/`support_count`/`null_signature` from immutable fixture inputs (ties to C-2), or explicitly mark F-036 as shape-only in WP4 acceptance.

---

## Minor / editorial

- **m-1 (retention, positive with residual).** `retention.py` is the strongest module: `checked_locations()` (retention.py:41-53) cannot be narrowed by callers; `verify_deletion` derives `status` from inspection (retention.py:197-206); `validate_deletion_manifest_for_event` re-derives the location closure and rejects any mismatch (retention.py:253-258); R3 is unstorable and unregistered replicas are prohibited. **Residual:** completeness depends entirely on the injected `discover_replicas`/`inspect_location`/`canonical_payload_scan` callables — an unregistered replica the discovery function does not find is invisible. This is an inherent trust boundary, but it should be documented as a named assumption and the discovery function should itself be an assured component before Gate 5's backup/restore extension (S-014). `require_retention_rule`/`RULES` are not cross-checked to the registry's `retention_policy_ids` beyond membership (retention.py:160-161) — Minor.
- **m-2 (scenarios).** `scenarios.py` A/B/D/E return hardcoded `Gate3ScenarioResult` literals; only C actually executes (`resume_from_checkpoint`). `decide_p0_release` only counts them (`operations_status = 'pass' if scenario_count == 5`, harness.py:246). The "integrated Gate 3 scenarios" do not integrate; they cannot fail. Either drive them through the real event/route/recovery machinery or label them as expected-output fixtures.
- **m-3 (dead seam).** `runner.py::run_fixture` is a generic injected-port coordinator not used by the P0 harness path — either wire it or note it as a forward seam.
- **m-4 (defensive dead code).** In `release.py::_incompatibility`, the scalar `getattr(coverage, 'expected_subject_hash', result.subject_hash)` fallback-to-self (release.py:64-72) is unreachable because the `missing_bindings` guard (release.py:42-55) already rejects absent attributes; harmless but misleading — it reads as if self-anchoring were permitted.

---

## Pass-on-omission battery (executed against `eval release`)

| Variant | Mutation | Decision | Rationale |
|---|---|---|---|
| anchoring (fabricated verdicts) | flip 18 M/H `unable_to_grade`→`pass` | **pass** ✗ | `p0_evidence_complete_owner_review_required` |
| empty | `results: []` | blocked ✓ | `missing_required_results` |
| partial | drop one required row | blocked ✓ | `missing_required_results` |
| duplicate | duplicate a required row | blocked ✓ | `duplicate_results` |
| extra | add `F-999` row | blocked ✓ | `unexpected_results` |
| stale/incompatible | wrong `coverage_revision` | blocked ✓ | `coverage_revision_mismatch` |
| lift S-014 restriction | drop S-014 from `omitted_gate5` | blocked ✓ | `gate5_capability_restrictions_mismatch` |
| self-authorize Gate 5 | `gate5_authorized: true` | blocked ✓ | `gate5_authorized_mismatch` |

**Reading:** the exact-set closure and binding checks are robust; the single hole is verdict fabrication (C-1). S-014/S-015/S-016 cannot be converted to P0 passes or stripped of restrictions through data — that would require editing the code constants `P0_CASES` (catalogue.py:13) and `_EXPECTED_DEFERRED` (coverage.py:17) plus adding fixtures, all of which are code-review-visible. Gate 5 cannot be self-authorized through the document.

---

## Consistency matrix (invariant → enforcement point → test → status)

| Invariant | Enforcement point | Test | Status |
|---|---|---|---|
| Exact required-result closure; no omission passes | `harness.decide_p0_release` missing/unexpected/duplicate (harness.py:181-183) | battery above | **holds (structural)** |
| Producer pass flag is not proof (05:365, 06:39) | should be `decide_p0_release`/`decide_release` | C-1 PoC | **violated (C-1, M-2)** |
| Property recomputed from immutable inputs (06:243) | should be graders + `load_fixture` hash | C-2 PoC | **violated (C-2)** |
| Two-key non-compensation F-035 (06b:23) | grader for F-035 | none | **not implemented (M-1)** |
| Independence actor comparison F-022 (02:1065) | grader for F-022 | none | **not implemented (M-1)** |
| Anti-anchoring: verifier derives expected value (05:356) | `grade_f036_mutation` | none | **violated (M-4)** |
| Byte-stable determinism across repetitions | `calibration._repeated_decisions` | vacuous | **unfalsifiable (M-3)** |
| M/H = `unable_to_grade`, no sub-threshold fallback (S-016; 06:209) | `_result_rows`/`calibrate_fixture` on legit path | legit run `blocked` | **holds on legit path; forgeable at release (C-1)** |
| S-014/15/16 remain capability-disabled pre-Gate-5 | `coverage.load_p0_coverage` + `decide_p0_release` omission check | battery | **holds** |
| Gate 5 unauthorized; owner acceptance required | coverage.py:161-169; document binding check | battery | **holds** |
| R3 never stored; unregistered replicas prohibited | `retention.validate_retention_policy` / `require_retention_rule` | test_retention | **holds** |
| Deletion status derived, location closure enforced | `retention.verify_deletion` / `validate_deletion_manifest_for_event` | test_retention | **holds (residual m-1)** |

---

## Decision audit

- **Keep:** exact-closure release scaffolding (structural checks); retention/deletion module; coverage/threshold/deferral validators; `GraderResult`/`validate_grader_result` design (once wired).
- **Amend (owner decision):** whether P0 accepts literal-evidence graders and inert fixture data trees (C-2, M-1, M-4) as an explicit, documented simplification with a P1 dependency, or requires input recomputation now. This is the pivotal owner call and I do not decide it.
- **Reject:** treating any generated `ReleaseGateDecision` (`pass` or `blocked`) as owner approval or Gate-5 evidence until C-1/M-2 are fixed.
- **Defer (already correctly deferred):** S-014/S-015/S-016 remain out of P0 with capability restrictions intact — verified.

---

## Revision plan

1. **Immediate (blockers for reliance):** C-1 (re-derive/verify verdicts; regression test on the forged-document PoC), M-2 (wire the real verification path).
2. **Immediate or explicit scope-amendment:** C-2 (recompute from inputs / verify `source_manifest_hash`), M-1 (per-finding graders or scoped claim), M-3 (real re-execution), M-4 (independent oracle or scoped claim).
3. **Owner decisions:** the literal-evidence-vs-recomputation policy for P0 (drives whether C-2/M-1/M-4 are "fix now" or "defer with amendment").
4. **Later-work dependencies:** assured `discover_replicas` before S-014 backup/restore; real scenario execution (m-2); wire `runner.py` (m-3).

## Residual risks

- Even after C-1/M-2, the release gate trusts the *coverage YAML*; that file is git-tracked and code-review-visible, which is an acceptable trust anchor, but the document→coverage binding should be by recomputed content hash, not just field equality.
- The retention guarantee remains only as strong as the injected discovery/inspection callables (m-1).

## Verification evidence

- Throwaway detached worktree `.apm/worktrees/review-pr60` at `origin/codex/ars-p0-wp4` (`0627ef1`); `.env` copied; removed after review.
- Legit `eval run`: 122 results, `candidate_status: blocked`, 18 M/H all `unable_to_grade`.
- Forged `eval release` (C-1): `decision: pass`, `rationale: p0_evidence_complete_owner_review_required`, 0/0/0/0 diagnostics, `gate5_authorized: False` preserved.
- Battery: 7/8 structural variants blocked with the expected rationale; only the fabricated-verdict variant passed.
- Inert-data (C-2): corrupting `F-012` input/expected/graders files produced no diff in `eval calibrate` and `eval validate` stayed `valid`.
- No repository source files were modified by this review.
