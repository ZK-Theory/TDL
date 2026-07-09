# Adversarial Review — ARS P0 WP4.9 Corpus Restore-to-Spec (PR #71)

**Date:** 2026-07-09
**Reviewer:** Adversarial design review (independent, adversarial posture)
**Reviewed artefact:** PR #71, branch `pipe/ars-p0-corpus-restore-to-spec` (commits `8808f1e..ddfd2fe`)
**Plan:** `docs/plans/agentic-research-system/implementation/04b-wp4-9-corpus-restore-to-spec-plan.md`
**Completion walkthrough:** `.gemini/antigravity-ide/brain/881aa45c-08bc-47d1-9bff-ae123421e1d5/walkthrough.md`

**Governing specifications:**

- `05-p0-materialization-and-foundation-implementation-plan.md` (05-plan)
- `04-evaluation-and-p0-fixtures-plan.md` (04-plan)
- `06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md` (06b)
- `06c-gate3-foundation-critical-interface-manifest-2026-07-01.md` (06c)
- `04a-wp4-8-verdict-derivation-and-release-evidence-plan.md` (04a)
- `adversarial-wp4-full-review-2026-07-07.md` (prior adversarial review)

---

## Executive Verdict

**`accept_with_required_changes`**

The implementation delivers its stated goals: F-036 restored to its 06b identity at r2 with three named mutations, all three policy/registry YAML files materialized and load-bearing, quarantine cleared, obligations O7/O8 closed, and aggregate invariants preserved (blocked 14/37, candidate blocked, 122 results). The anti-anchoring rule is observed — the F-036 executor derives from the stimulus payload only. Coverage, calibration, and test evidence is coherent.

Three findings require attention: one Major, two Minor. None is Critical. The strongest attack (circular policy validation) confirms a genuine architectural seam but one whose P0 impact is contained. No fabricated fixtures were found — test assertions bind to independent derivations or package bytes, not to themselves.

---

## Findings

### M-1 (Major): Calibration-policy runtime "cross-check" is a tautology, not a cross-check

**Claim:** 04b obligation R4 states "content verbatim; runtime cross-check against the engine constant". The plan's interface section says `require_calibration_policy` produces a "validated payload" and its docstring says "fail-closed: the file cannot silently authorize weaker calibration than the engine performs".

**Evidence:**
- `research_system/evals/policies.py:12-23` — `_REQUIRED_CALIBRATION` is a hardcoded dict containing `"deterministic_repetitions": 2`.
- `research_system/evals/calibration.py:24` — `DETERMINISTIC_REPETITIONS = 2` is a separately maintained constant.
- `policies.py:76` — `require_calibration_policy` compares the YAML against `_REQUIRED_CALIBRATION`. It never imports or reads `DETERMINISTIC_REPETITIONS` from `calibration.py`.
- `tests/research_system/unit/test_policies.py:34-38` — `test_calibration_policy_matches_engine` imports `DETERMINISTIC_REPETITIONS` and asserts `payload["deterministic_repetitions"] == DETERMINISTIC_REPETITIONS`.

The runtime "cross-check" validates the YAML against a hardcoded copy of the expected values, not against the live engine constant. The claim "cannot silently authorize weaker calibration than the engine performs" is true only if `_REQUIRED_CALIBRATION["deterministic_repetitions"]` and `DETERMINISTIC_REPETITIONS` are manually kept in sync. If someone edits `calibration.py` to change `DETERMINISTIC_REPETITIONS = 3`, the YAML still validates at runtime — `require_calibration_policy` passes — and the engine silently performs three repetitions while the policy file still says `2`. The *test* would catch the drift, but the *runtime path* does not. This is a tautological runtime validation: the runtime code validates the YAML against itself (a copy), not against the engine it claims to cross-check.

**Concrete failure scenario:** An agent edits `calibration.py` to set `DETERMINISTIC_REPETITIONS = 3`. Tests would catch this (assuming they run), but a CI skip, selective test run, or deployment that bypasses `test_policies.py` would leave the runtime accepting a `deterministic_repetitions: 2` policy while the engine performs 3 repetitions. The "fail-closed" claim is falsified for the runtime path.

**Impact:** Material ambiguity in the runtime integrity model. The obligation says "runtime cross-check" but the implementation delegates the actual cross-check to the test suite. This is a control that works only when tests run, not at runtime.

**Recommended disposition:** Fix now — import `DETERMINISTIC_REPETITIONS` in `require_calibration_policy` and assert `payload["deterministic_repetitions"] == DETERMINISTIC_REPETITIONS` at runtime. The hardcoded `_REQUIRED_CALIBRATION` dict may remain for full-schema validation, but the engine-constant check should be explicit:

```python
from research_system.evals.calibration import DETERMINISTIC_REPETITIONS

def require_calibration_policy(path: Path | str) -> dict[str, Any]:
    payload = _yaml(Path(path))
    if payload != _REQUIRED_CALIBRATION:
        drift = ...
        raise ConfigurationError(...)
    if payload["deterministic_repetitions"] != DETERMINISTIC_REPETITIONS:
        raise ConfigurationError(
            f"calibration policy says {payload['deterministic_repetitions']} "
            f"repetitions but the engine constant is {DETERMINISTIC_REPETITIONS}"
        )
    return payload
```

**Affected decisions:** R4 of 04b; 04-plan §571 "immutable P0 proposal"; 05-plan §6 "machine-checkable claims".

---

### m-1 (Minor): F-036 stimulus values deviate from the plan without a recorded deviation

**Claim:** 04b Task 2 Step 3 specifies F-036 values as `[2.0, 4.0, 6.0, 8.0]` with `producer_reported_value: 5.2`, `anchor_target: 5.2`, and `fallback_constant: 0.0`. The derivability check states "the honest recomputed mean of `[2.0, 4.0, 6.0, 8.0]` is `5.0`; the producer-reported `5.2` equals the anchor target, so anchoring is detected (`5.2 != 5.0`)".

**Evidence:**
- `tools/ars/materialize_adapter_scientific_fixtures.py:256` — actual values are `[2, 4, 6, 8]` (integers, not floats).
- `tools/ars/materialize_adapter_scientific_fixtures.py:258-259` — `producer_reported_value: 6`, `anchor_target: 6` (not 5.2).
- `.research-system/evals/fixtures/F-036/input/stimulus.json` — confirms `"values":[2,4,6,8]`, `"producer_reported_value":6`, `"anchor_target":6`.
- Walkthrough line 15: "Updated the F-036 materializer `Case` definition to use integer inputs to comply with P0 canonical JSON float restrictions."

The deviation is acknowledged in the walkthrough ("integer inputs to comply with P0 canonical JSON float restrictions"), but it also changes the `producer_reported_value` from `5.2` to `6` and the `anchor_target` from `5.2` to `6`. The arithmetic still works (mean of `[2,4,6,8]` = `5.0`, and `6 != 5.0`, so anchoring is detected), and the change is arguably an improvement (avoids JSON float representation issues). However:

1. The deviation is not recorded in the 04b obligation register's deviation column (R9/R12 style).
2. The specific values `5.2` in the plan were not random — they were chosen so the anchored value was *close to but not equal to* the true mean (5.0 vs 5.2), simulating a realistic anchoring attack. Changing to `6` makes the anchor target equal to one of the input values, which is a weaker test of the "approximate sanity value" incident class described in 06b §2 F-036: "an approximate sanity value is used as a target".

**Concrete failure scenario:** Not a functional failure (the executor still correctly detects anchoring). This is a spec-fidelity issue: the 06b intent is that the anchor target should be an *approximate* value (close to the true answer but not derived from it), not just any wrong value. `6` is exactly the third data point, not an "approximate sanity value" — it's an obvious outlier. A subtler attack (like the original `5.2`, which is only 4% off from the true mean) would better exercise the control.

**Impact:** Reduced realism of the mutation scenario; no operational impact since anchoring is still detected. The plan divergence is undocumented in the formal register.

**Recommended disposition:** Accept risk — record the deviation in the 04b obligation register as a documented simplification (like R9/R12). Optionally restore the original `5.2`/`5.2` pair if the canonical JSON serialization permits it (the mean 5.0 would serialize as `5.0` which is valid canonical JSON; the anchor `5.2` is also valid).

**Affected decisions:** R1 of 04b (06b §2 row F-036); anti-anchoring rule.

---

### m-2 (Minor): `require_calibration_policy` accepts extra keys without error

**Claim:** The function's docstring says "any required key is missing or differs" raises `ConfigurationError`. The policy file is described as immutable with "these exact rules" (04-plan §571).

**Evidence:**
- `policies.py:76-82` — the check is `if payload != _REQUIRED_CALIBRATION`. This correctly rejects missing keys, changed values, *and* extra keys.
- However, the drift diagnostic (lines 77-81) only reports keys from `_REQUIRED_CALIBRATION` that differ and extra keys: `{key: (payload[key], None) for key in payload.keys() - _REQUIRED_CALIBRATION.keys()}`.
- Actually, re-reading line 76: `if payload != _REQUIRED_CALIBRATION` — this comparison **does** correctly reject extra keys since `{"a": 1, "b": 2} != {"a": 1}`. The function is correct.

**Retraction:** On closer inspection, this finding is withdrawn. The `!=` comparison is exact; extra keys cause rejection. The diagnostic path is secondary. No finding.

---

### m-2 (Minor, renumbered): Context-routing sizing rows generated for all nine CONTEXT_ROUTING fixtures at Gate 5 but only F-021 at P0

**Claim:** 04b obligation R7 states "F-021 stays P1 but its `mandatory_closure_sizing` variant runs at P0". The variant matrix generator produces sizing rows for all CONTEXT_ROUTING fixtures.

**Evidence:**
- `tools/ars/materialize_p0_variant_matrix.py:113-115`:
  ```python
  for fixture_id in CONTEXT_ROUTING:
      rows.append(_executed_row(root, fixture_id, "bounded"))
      stage = "p0" if fixture_id == "F-021" else "gate5"
      rows.extend(_sizing_rows(root, fixture_id, stage))
  ```
  All nine context-routing fixtures get sizing rows; F-021's are `execution_stage: "p0"`, all others are `execution_stage: "gate5"`.

- `test_variant_matrix.py:17-26` — `test_every_p0_case_has_exactly_one_executed_p0_row_plus_f021_sizing` verifies F-021 has 3 P0 rows and all others have 1. This correctly validates the P0/gate5 split.

- `test_variant_matrix.py:35-51` — F-021 sizing rows verified with recomputable token evidence.

The sizing rows for non-F-021 fixtures are all at `gate5`, which matches the 04b obligation R8 ("executing the fake-claude/fake-codex variant rows... is a named Gate 5 dependency"). However, only F-021's sizing rows have the recomputable token-evidence fields (`reference_count`, `exact_tokens`, `evaluated_tokens`) verified by test. The other eight context-routing fixtures' gate5 sizing rows are generated but not tested for token-evidence correctness.

**Concrete failure scenario:** If a non-F-021 context-routing fixture has incorrect sizing evidence in its gate5 row, no test catches it until Gate 5. This is not a P0 issue since those rows are explicitly deferred, but it's a latent gap.

**Impact:** No P0 impact. Latent Gate 5 risk.

**Recommended disposition:** Defer with dependency — add a gate5-specific sizing-row verification when the gate5 execution stage is implemented. Record as a known gap.

**Affected decisions:** R8 of 04b; 04-plan §586.

---

## Decision Audit

| Decision | Plan Reference | Disposition | Evidence |
|---|---|---|---|
| F-036 restored to 06b identity | R1 (06b §2 row F-036) | **keep** | `fixture.yaml` lanes, provenance, graders, mutations match 06b §2; executor derives from payload only |
| Three mutations calibrated | R2 (06b §4 item 4) | **keep** | `test_f036_three_named_mutations_detected` — each mutation detected in both repetitions; calibration detection rule `observed == pre and observed != post` correctly applied |
| Fixture revisions bump to r2 | R3 (06b authority clause) | **keep** | F-036: r2 in fixture.yaml, coverage, tests; F-021: r2 in fixture.yaml, coverage, tests |
| Calibration policy content verbatim | R4 (04-plan §571) | **amend** — runtime cross-check per M-1 | Content matches §571 exactly; runtime cross-check is tautological (see M-1) |
| Threshold-policy closure | R5 (04-plan Task 4) | **keep** | `test_every_p0_fixture_threshold_policy_resolves` — all 37 fixtures resolve; runtime check in `run_p0_coverage` |
| Variant matrix explicit rows | R6 (04-plan §586) | **keep** | `test_no_wildcard_rows_and_complete_tuples` — no wildcards; `test_package_bindings_are_matrix_rows` — every binding is a matrix row |
| F-021 sizing at P0 | R7 (P-028 / 04-plan §4.2) | **keep** | Two provider-specific sizing rows at `execution_stage: p0`; token evidence recomputed by test |
| Gate 5 adapter variant deferral | R8 | **keep** | Matrix registers gate5 rows; harness variant-aware execution deferred |
| Three-shard materializer deviation | R9 | **keep** | Accepted deviation from 04-plan's single materializer; reviewed and accepted 2026-07-04 |
| O7/O8 delivered | R10 (04a register) | **keep** | Both rows updated with delivered dispositions referencing 04b tasks |
| Aggregate blocked | R11 (05-plan / 04a Global Constraints) | **keep** | `blocked_fixture_count: 14`, `candidate_status: "blocked"`, `result_count: 122` — walkthrough line 62-64 |
| F-021 two provider-specific sizing rows | R12 | **keep** | Delivered with deviation stated verbatim; no-wildcard rule enforced |

---

## Cross-Spec Consistency Matrix

| Invariant | Spec Source | Enforcement Point | Test |
|---|---|---|---|
| F-036 lanes `topology, stochastic, representation, claim` | 06b §2 row F-036 | `materialize_adapter_scientific_fixtures.py:253` | `test_adapter_scientific_fixture_corpus.py:66` |
| F-036 provenance `domain_coverage / synthetic` | 06b §2 row F-036 | `materialize_adapter_scientific_fixtures.py:282-283` | `test_adapter_scientific_fixture_corpus.py:67` |
| F-036 graders D,T,R,M | 06b §2 row F-036 | `materialize_adapter_scientific_fixtures.py:281` | `fixture.yaml:42-81` (four graders), `test_calibration.py:101` (M grader → unable_to_grade) |
| F-036 three named mutations | 06b §4 item 4 | `materialize_adapter_scientific_fixtures.py:286-290` | `test_calibration.py:94-97` |
| Calibration policy verbatim §571 | 04-plan §571 | `p0-calibration-policy.yaml` | `test_policies.py:34-38` (engine match); `policies.py:76` (drift rejection) |
| Threshold policy closure | 04-plan Task 4 | `harness.py:87-91` | `test_policies.py:23-31` |
| Variant matrix no wildcards | 04-plan §586 | `fixture_package.py:231-241` | `test_variant_matrix.py:29-32` |
| F-021 remains P1 | 05-plan §4.2 | `materialize_context_routing_fixtures.py:68` (`"P1"`) | `fixture.yaml:15` (`priority: P1`) |
| F-021 gate_stage p0_materialization | 05-plan §4.2 | `materialize_context_routing_fixtures.py:42` (default) | `fixture.yaml:16` |
| Aggregate blocked at 14 | 05-plan §7 / 04a Global Constraints | `harness.py` → `calibration.py` → `release.py` | Walkthrough: `blocked_fixture_count: 14` |
| Per-package revision equality | 04b Task 2 Step 5 | `coverage.py:102-109` | `test_coverage.py:25-28` (F-021: r2, F-036: r2) |
| Anti-anchoring rule | 04a Global Constraints | `execute_f036` derives from `payload["action"]` only | Code review: L192 `sum(action["values"])` — no oracle read |
| 06c §4 fixture_id / fixture_revision binding | 06c §4 identity list | `fixture.yaml` per-package | `coverage.py:102-109` validates match |
| No fixture_error in corpus | 04b acceptance checklist | `test_executors.py:108-115` | `expected_errors = set()` |

---

## Coverage and Fixture Gap Analysis

### Tests verified present and exercising independent oracles

| Test | Oracle independence |
|---|---|
| `test_f036_three_named_mutations_detected` | Calibration detection rule (`observed == pre and observed != post`) applied to real executor output; oracle is the committed package bytes |
| `test_calibration_policy_matches_engine` | Cross-checks YAML `deterministic_repetitions` against imported `DETERMINISTIC_REPETITIONS` constant — independent sources |
| `test_every_p0_fixture_threshold_policy_resolves` | Loads policies from YAML file, loads definitions from fixture packages, checks set containment — two independent data sources |
| `test_f021_sizing_rows_record_recomputable_token_evidence` | Reads stimulus/oracle bytes from disk, recomputes `ceil(len/divisor)`, compares to matrix rows — independent derivation |
| `test_no_wildcard_rows_and_complete_tuples` | Checks matrix content against a static wildcard set — the matrix is the subject, the set is the invariant |
| `test_package_bindings_are_matrix_rows` | Reads source manifests from disk, compares binding variant_ids to matrix rows — two independent data sources |
| `test_full_corpus_calibration_has_no_fixture_errors` | Runs real calibration over all 37 fixtures; asserts `fixture_error` set is empty |
| `test_tampered_oracle_yields_fixture_error_and_blocked` | Tampers post-control, reruns harness, verifies fixture_error and blocked — active tamper + independent derivation |

### No fixture fabrication detected

All fixture tests bind to committed package bytes or derive evidence from the stimulus payload. No test asserts against a value it also generates.

---

## Practicality Assessment

The implementation is proportionate:

- **Policy files:** 3 new YAML files, one new Python module, 5 new tests. Overhead is minimal; controls are load-bearing at runtime.
- **F-036 restoration:** One Case redefinition + one executor rewrite + fixture regeneration. The executor arithmetic is simple and auditable.
- **Variant matrix:** One new generator + 5 new tests. The generator is deterministic and `--check` verifiable.
- **Obligation closure:** Two register rows edited. Minimal bureaucratic overhead.

The total diff is ~3300 lines, but ~825 of those are the generated `p0-variant-matrix.yaml` (an 825-line YAML file of explicit variant rows). The actual implementation changes are ~350 lines of code + ~150 lines of tests.

---

## Revision Plan

### Immediate corrections (before merge)

1. **M-1:** Add a runtime import of `DETERMINISTIC_REPETITIONS` in `require_calibration_policy` to make the engine-constant cross-check a true runtime guarantee, not just a test-time guarantee.

### Owner decisions (flag in PR)

1. **m-1:** The F-036 `producer_reported_value: 6` is simpler but less realistic than the plan's `5.2`. Owner should confirm this is acceptable or request the original values be restored. Record the decision either way.

### Later-work dependencies

1. **m-2:** Gate 5 sizing-row verification for non-F-021 context-routing fixtures.
2. **O14/O11/O12/O16 (from 04a):** Cross-family independence, parity wiring, canonical event publication, and retention policy source remain Gate 5 dependencies. These are correctly registered and not claimed here.

---

## Residual Risks

1. **Single `_REQUIRED_CALIBRATION` source of truth:** Even after M-1 is fixed, the policy validation relies on a hardcoded expected-value dict. If the 04-plan §571 definition changes, two places must be updated. This is acceptable for P0 (the values are acceptance-frozen) but should be revisited if the calibration policy evolves.

2. **Gate 5 sizing rows untested:** Eight context-routing fixture sizing rows are generated and committed but not individually verified. Token counts could be wrong without detection until Gate 5 tests run.

3. **F-012 seed unchanged:** The plan states `F-012's seed 20260707 is untouched`. This was verified by absence of changes in the diff. The seed is still protected.

---

## Verification Evidence

**Files examined directly (not via summaries or prior conclusions):**

- `research_system/evals/policies.py` — full file, 84 lines
- `research_system/evals/coverage.py` — full file, 191 lines
- `research_system/evals/harness.py` — full file, 312 lines
- `research_system/evals/calibration.py` — full file, 175 lines
- `research_system/evals/executors/adapter_scientific.py:170-201` — `execute_f036` function
- `tools/ars/materialize_adapter_scientific_fixtures.py:1-65, 230-300` — Case dataclass and F-036 entry
- `tools/ars/materialize_context_routing_fixtures.py:1-70, 380-492` — Case dataclass, F-021 entry, _package function
- `tools/ars/materialize_p0_variant_matrix.py` — full file, 147 lines
- `tests/research_system/unit/test_policies.py` — full file, 60 lines
- `tests/research_system/unit/test_variant_matrix.py` — full file, 78 lines
- `tests/research_system/unit/test_calibration.py` — full file, 104 lines
- `tests/research_system/unit/test_executors.py` — full file, 116 lines
- `tests/research_system/unit/test_coverage.py` — full file, 73 lines
- `tests/research_system/integration/test_adapter_scientific_fixture_corpus.py` — full file, 79 lines
- `tests/research_system/integration/test_release_coordinator.py:35-46`
- `tests/research_system/integration/test_broken_oracle_regression.py` — full file, 54 lines
- `.research-system/evals/fixtures/F-036/fixture.yaml` — full file, 99 lines
- `.research-system/evals/fixtures/F-036/input/stimulus.json` — full file
- `.research-system/evals/fixtures/F-036/expected/pre-control.json` — full file
- `.research-system/evals/fixtures/F-036/expected/post-control.json` — full file
- `.research-system/evals/fixtures/F-021/fixture.yaml` — full file, 88 lines
- `.research-system/evals/fixtures/F-021/input/source-manifest.json` — full file
- `.research-system/evals/p0-coverage.yaml` — full file, 103 lines
- `.research-system/evals/p0-calibration-policy.yaml` — full file, 11 lines
- `.research-system/evals/threshold-policies.yaml` — full file, 14 lines
- `04b-wp4-9-corpus-restore-to-spec-plan.md` — full file, 941 lines
- `04a-wp4-8-verdict-derivation-and-release-evidence-plan.md:55-76` — obligation register
- `06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md` — full file, 68 lines
- `06c-gate3-foundation-critical-interface-manifest-2026-07-01.md` — full file, 340 lines
- `05-p0-materialization-and-foundation-implementation-plan.md:1-200`
- `04-evaluation-and-p0-fixtures-plan.md:1-100, 540-620, 780-812`
- Walkthrough: `.gemini/antigravity-ide/brain/881aa45c-08bc-47d1-9bff-ae123421e1d5/walkthrough.md` — full file, 65 lines
- Git log and diff stats for PR #71

**Arithmetic verification:**
- F-036: `mean([2, 4, 6, 8]) = 20/4 = 5.0`. `producer_reported_value = 6 ≠ 5.0` → anchoring detected ✓. `fallback_constant = 0 ≠ 5.0` → degenerate fallback detected ✓. `object_hash_before == object_hash_after` → null invariance detected ✓. Pre-control oracle: all False + `producer_flag_trusted: True` ✓ (known-bad path). Post-control oracle: all True + `producer_flag_trusted: False` ✓ (controlled path).

**No files were edited by this review.**

---

## Change Log

| Action | Files | Verification |
|---|---|---|
| Created review | `reviews/adversarial-ars-p0-wp49-review-2026-07-09.md` | This file |
| No edits to reviewed artefacts | — | Working tree unchanged except this review |
