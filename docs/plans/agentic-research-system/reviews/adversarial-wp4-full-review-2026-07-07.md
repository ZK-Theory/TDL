# Adversarial review — ARS P0 WP4.1–4.7 full range (ee3472b..ca1f49e)

**Date:** 2026-07-07
**Target:** the seven merged WP4 tranches on `main` — 8f18855 (WP4.1, PR #61), 048f763 (WP4.2, PR #62), f789601 (WP4.3), 719da97 (WP4.4), d755b69 (WP4.5, PR #65), 08a1fae (WP4.6, PR #66), ca1f49e (WP4.7, PR #67); combined diff `ee3472b..ca1f49e` (+12,641 / 381 files).
**Governing specs:** `05-p0-materialization-and-foundation-implementation-plan.md`, `implementation/04-evaluation-and-p0-fixtures-plan.md`, `design/06b-…-2026-06-30.md`, `design/06c-…-2026-07-01.md`.
**Prior reviews consumed (fixes verified against the final diff, not trusted):** `reviews/adversarial-pr60-ars-p0-wp4-review-2026-07-03.md`, `reviews/ars-p0-wp4-adversarial-implementation-review-2026-07-04.md`.
**Reviewer stance:** fresh-context adversary; direct source inspection; test suite and CLI executed at ca1f49e in a throwaway detached worktree (created and removed during this review) and in the live main working tree.
**Authority boundary:** this report approves nothing. No Gate 5, live provider, pilot, migration, or research claim is authorized. No source file was modified; the only file written is this report.

---

## Executive verdict: `rework_required` (scoped)

The split-and-rebuild ordered by the 2026-07-04 review genuinely fixed most of what it named. WP4.1's contract surface closes M-1/M-2/M-6/M-7/M-9 exactly as prescribed; WP4.2's retention module closes M-8 and is the strongest code in the package; WP4.3's `validate_fixture_package` closes M-5 with real per-file schema validation, exact eight-file closure, duplicate-key rejection, hash binding of every declared hash to actual bytes, and wildcard-variant prohibition. The 37-case closure is exact, Gate 5 restrictions cannot be lifted through data, and the legitimate P0 outcome is honestly `blocked`.

But the two assurance claims at the heart of WP4 — that graders derive verdicts from fixture behavior, and that calibration demonstrates known-bad failure, known-good pass, and mutation detection — are still not established, and in two places the evidence for them is **manufactured**:

1. the runnable release path synthesizes every non-M/H grader verdict as an unconditional `pass` without any grader executing (**C-1**), and
2. mutation "calibration" emits hardcoded `detected: True` constants that no code ever computes, while a test named `…executed_twice_and_detected` and a PR bullet claim execution (**C-2**).

The prior review's C-1 was closed by *removing the input* (the release CLI now ignores the supplied verdict document entirely) rather than by *re-deriving the verdicts* as its disposition required. The regression test that guards it asserts a `TypeError` on a dict — the invariant "producer verdict is not proof" is still unmet one level down, because the harness itself is now the producer of unexamined `pass` verdicts. Today the aggregate stays `blocked` only because M/H classes are unavailable; the moment a live M/H threshold policy is accepted, this exact path emits a full 37-case P0 `pass` in which no fixture behavior was ever exercised.

Separately, the live `main` working tree currently fails 8 of the WP4 tests and all four `eval` CLI commands (**M-6**): the fixture corpus on disk is CRLF (checked out under `core.autocrlf=true` before WP4.5's `.gitattributes eol=lf` landed) and no renormalization was ever performed, so every content-hash binding mismatches. A fresh checkout passes; the canonical working copy does not.

**Disposition summary:** keep WP4.1–4.4 primitives and the WP4.5/4.6 corpus *as staged declarative packages*; rework the WP4.7 calibration/harness/scenario evidence before any reliance on it; renormalize the main working tree immediately.

---

## Critical findings

### C-1 — The runnable evaluation path manufactures its own grader verdicts; the strict validator certifies the harness against itself

1. **ID/severity:** C-1, Critical.
2. **Claim.** `run_p0_coverage` fabricates every `GraderResult` in-process: verdict is the literal `"pass"` for every D/T/O/P/R grader and `"unable_to_grade"` for M/H, with no grader, oracle, or calibration ever executing. Every "expected" binding the strict validator checks is copied from the same `fixture.yaml`/package bytes into both the expected side and the observed side of the comparison inside the same function.
3. **Evidence.** `research_system/evals/harness.py:69-120` — `verdict="unable_to_grade" if live else "pass"` (line 100); `subject_hash`, `trace_hash`, `oracle_hash`, `policy_hash`, `threshold_hash` computed once (lines 69-73) and written into both `maps[...]` (the expectations, lines 83-89) and the `GraderResult` (lines 104-108); `independently_recomputed=True` hardcoded (line 110); `producer_family`/`grader_family` set to literals chosen so `validate_grader_result`'s cross-family check passes exactly when it must (lines 111-112). `calibrate_fixture` is never called on this path (`decide_p0_release` → `decide_release` only, harness.py:134-138; `calibrate_fixture` referenced only by `cli.py:163` and unit tests). No module in `research_system/evals/` executes any per-fixture behavior; the per-fixture property graders the plan specified (`grade_f011`…`grade_f014`, 04-plan Task 5) do not exist anywhere in the final tree.
4. **Failure scenario.** Accept a live M/H threshold policy at some later gate (the single change the design anticipates), rerun `eval run`/`eval release`: all 122 required results become `pass`, `decide_release` returns `pass`, and a complete 37-case P0 release decision is presented to the owner although no fixture's known-bad behavior, known-good behavior, or property predicate was ever computed. Equivalently today: any consumer reading the 108 `pass` rows in the run evidence as "these graders passed" is consuming fabricated evidence.
5. **Impact.** Evidence integrity and invalid-acceptance risk — the same class as the 2026-07-04 review's C-1, which prescribed: "reconstruct typed GraderResult records… require exact result closure, immutable bindings… before pass" *derived from re-derivation*. The typed reconstruction landed; the re-derivation did not. The design invariants "graders recompute or independently bound the property from immutable inputs" and "producer pass flags are not proof" remain unimplemented on the runnable path.
6. **Disposition — fix now.** Derive each non-M/H verdict from `calibrate_fixture` (or a real per-fixture grader registry): a fixture whose paired calibration is not (known-bad fails ×2, known-good passes ×2, every declared mutation detected ×2) must yield `fixture_error`, never `pass`. Stop hardcoding `independently_recomputed` and the family literals; carry them from actual execution metadata. Add a regression test in which a fixture package with a deliberately broken oracle produces `fixture_error` (not `pass`) at `eval run`.
7. **Proposed interface change.** `run_p0_coverage(...)` takes an executor/grader registry and maps `PairedCalibration.blocking_verdict`/decisions → per-key verdicts; `EvaluationEvidence` gains the calibration record hashes so release can bind them.
8. **Affected:** WP4.7; 04-plan Tasks 2/5/6; P0 acceptance items 3, 4, 7, 9, 11; every consumer of a future `ReleaseGateDecision`.

### C-2 — Mutation calibration is fabricated constants, asserted by a test and claimed as executed in PR #67

1. **ID/severity:** C-2, Critical.
2. **Claim.** `calibrate_fixture` does not execute or detect any mutation: for every `mutation_id` it constructs two `CalibrationDecision` records with the literals `verdict="pass"`, `reason="mutation_detected"`, `{"mutation_id": …, "detected": True}` (`research_system/evals/calibration.py:141-167`). The known-bad/known-good half is executed twice (prior M-4's shape is fixed) but through `_default_execute`, which returns `{"property_satisfied": subject == "known_good"}` (calibration.py:60-61) — a tautology of the subject label, so "known-bad fails and known-good passes" is true by construction and unfalsifiable.
3. **Evidence.** calibration.py:60-61, 141-167. `tests/research_system/unit/test_calibration.py:59-64` — `test_declared_mutations_are_executed_twice_and_detected` asserts the fabricated constants. PR #67 summary: "execute known-bad, known-good, and declared mutation calibration twice with byte-stable normalized decisions" — false for mutations. The plan's calibration-policy rules (`declared_mutation_requirement: detected_in_every_repetition`, `stochastic_policy_missing: fixture_error`; 04-plan Task 4) have no implementation, and `.research-system/evals/p0-calibration-policy.yaml` itself was never created.
4. **Failure scenario.** Any fixture's declared mutation (`<contract>-violation`) can be undetectable by every real grader forever; calibration will still report it detected twice, byte-stably. 06b §4's F-036 precondition — "calibrate each mutation so the uncontrolled path plausibly passes superficial checks and the controlled path rejects it" — is reported satisfied while nothing was calibrated.
5. **Impact.** This is exactly the fabrication class the fixture programme exists to catch (F-036's own subject matter), reproduced inside the calibration module. It also poisons the CLI evidence: `eval calibrate` output ("37 fixtures, 14 blocked") reads as executed calibration.
6. **Disposition — fix now, or amend the claim explicitly.** Either implement real mutation execution (apply the mutation recipe to the subject, run the grader, require detection twice), or (a) delete the fabricated `MutationCalibration` records and report `mutations: not_calibrated`, (b) rename the test, and (c) correct the WP4.7 completion claim so calibration is recorded as *pending*, mirroring the honest `status: authored` labeling the corpus already carries.
7. **Proposed text change.** In any successor to PR #67's summary: "known-bad/known-good executed twice via an injected executor; **mutation execution not yet implemented; mutation records are placeholders**" — or the code change above.
8. **Affected:** WP4.7; 04-plan Tasks 4-5; 06b §4 preconditions; P0 acceptance items 4 and 8.

---

## Major findings

### M-1 — F-036's accepted identity was rewritten; the plan's scientific property graders were deleted rather than input-bound

- **Claim.** 06b reserves F-036 as "Proof-obligation anti-gaming" with **three** calibrated mutations (expected-value anchoring; degenerate/constant fallback; null invariance), lanes `topology, stochastic, representation, claim`, provenance `domain_coverage / synthetic` (06b §2 row F-036, §4 item 4). The materialized F-036 is a different object: contract `mutation_evidence_recomputation`, **one** generic mutation (`mutation_evidence_recomputation-violation`), lanes `("scientific_review", "governance")`, `incident_basis: "specification"` (`tools/ars/materialize_adapter_scientific_fixtures.py:242-254`, defaults at lines 33-34). 06b's authority clause — reservations "reserve the IDs without rewriting any existing fixture identity, priority, provenance, or oracle" — is violated by the materialization. The anchoring and degenerate-fallback mutation classes now exist nowhere (F-012 covers null invariance; F-011's forbidden list mentions `DegenerateFallback` but has no mutation for it; expected-value anchoring is gone). Additionally, the prior review's disposition for the scientific group — "retain the useful property functions but make them consume package inputs" — was answered by deleting `grade_f011`–`grade_f014` entirely; no per-fixture grader exists in the final tree.
- **Failure scenario.** The three incident classes P0 was chartered to prove detectable (Obs-19/20-class incidents: sanity-value anchoring, plausible-constant fallback) have no fixture coverage; a future gate reads "F-036: covered" and inherits a hole.
- **Impact.** Cross-spec identity violation plus silent coverage loss on the highest-value scientific controls. Also breaches plan acceptance item 8 ("F-036 mutations derived from the deferred F-015/F-016 incident classes").
- **Disposition — fix in the corpus shard:** restore F-036's three named mutations and 06b lanes/provenance, or file an owner-approved amendment to 06b before the corpus is treated as catalogue-conformant.
- **Affected:** 06b §2/§4; WP4.6; P0 acceptance item 8.

### M-2 — The variant matrix, threshold policies, and calibration policy were never materialized; F-021's mandated sizing variant does not exist

- **Claim.** The plan requires `.research-system/evals/p0-variant-matrix.yaml` ("explicit rows, never wildcards": control/store bind provider `none`/`in_process_fake`; context/routing bind the exact reference counter plus each required fake Claude/Codex provider-count/rendering revision; adapter cases bind `claude`/`codex`, adapter profile/revision, and `trivial`/`bounded`/`long_running` operational profiles; scientific cases bind synthetic oracle, seeds, independence class — 04-plan Task 4), plus `threshold-policies.yaml` and `p0-calibration-policy.yaml`. None of the three files exists at ca1f49e. Every one of the 37 packages carries the same single variant row `python313-windows-in-process / provider-neutral` (all three materializers). F-021's `mandatory_closure_sizing` variant — the P-028 obligation the plan restates twice (§4.2; §7.2 W3 row: "sizing matrix records reference count plus exact/evaluated provider-token evidence for every declared variant") and encodes in its own Task 4 test (`fixture.variant == 'mandatory_closure_sizing'`) — is absent; `fixture.yaml` has no variant field and no sizing measurement exists.
- **Failure scenario.** A Claude-vs-Codex parity defect, an operational-profile-specific failure, or a token-gate sizing miss is undetectable by construction: no variant row obliges the differing configuration to be evaluated. The wildcard-prohibition check in `validate_fixture_package` (real, lines 196-207) guards a matrix that has collapsed to one generic row.
- **Impact.** W7 §7.2 obligation ("no wildcard activation" of adapter variants), P-028's two-gate sizing, and the plan's Task 4 acceptance are unimplemented; the fixture corpus's provider/operational coverage claim is one row wide.
- **Disposition — fix before calibration/activation tranche;** if P0 deliberately defers multi-variant binding, record that as an explicit owner-approved plan amendment with a P1 dependency, since it narrows an accepted obligation.
- **Affected:** 04-plan Task 4; 05-plan §7.2 rows W3/W7; F-021/F-022/F-025/F-026 sizing; all adapter fixtures.

### M-3 — `eval release` ignores its input document, and no `ReleaseGateDecision` is ever produced, persisted, or dated

- **Claim.** `_eval_release` reads `--evaluation-runs`, extracts only the `coverage` path, and re-derives everything via `run_p0_coverage` (`research_system/cli.py:184-198`); the manifest's results are never compared, authenticated, or even parsed beyond one key. The prior review's C-1 prescription "treat the document as claims to be checked" became "ignore the document" — fail-closed against forgery, but the command is now semantically identical to `eval run`, and an auditor reading `eval release --evaluation-runs X → decision: blocked` reasonably believes X was assessed. The regression test guards only a type check (`test_forged_producer_document_cannot_enter_release_path` asserts `TypeError` on a dict, `test_release_coordinator.py:34-36`). Moreover the plan's Task 6 deliverable — "`release` … emitting one `ReleaseGateDecision`", with "output paths … explicit, date-suffixed, and non-overwriting" — is absent: `models.ReleaseGateDecision` is constructed only in unit tests, `decide_p0_release` returns a plain dict, nothing records `decided_at`/`parity_status`/`operations_status`/`canonical_event_ref`, and no CLI command writes any output file at all.
- **Failure scenario.** (a) Release evidence exists only as ephemeral stdout — nothing date-suffixed lands in `results/`-style storage, so the P0 decision the owner must accept has no artifact to accept. (b) The scenario/operations dimension (prior review C-1's second half: "release pass can coexist with blocked operations") was resolved by removing operations from the release computation entirely rather than making it a precondition.
- **Disposition — fix in the rework tranche:** construct a real `ReleaseGateDecision` (with parity/operations status derived from executed scenarios), write it to an explicit non-overwriting dated path, and either make `--evaluation-runs` meaningful (verify the supplied document matches the re-derivation, byte-hash-bound) or remove the flag.
- **Affected:** 04-plan Task 6; W6 §25; P0 acceptance items 9 and 11.

### M-4 — The W6 typed contract layer is display-case: models, trace enforcement, lifecycle, and five runtime schemas validate nothing on the runnable path

- **Claim.** `FixtureDefinition`, `GraderRequirement`, `EvaluationRun` (and its retry lineage), `CoverageManifest`, `TraceEnvelope`, and `assert_trace_complete` are instantiated/invoked **only in unit tests** (grep across the tree: no runtime module constructs any of them; `coverage.py`/`harness.py` consume raw YAML dicts). Consequently M-2's fix (issued-resources terminal evidence) and M-9's fix (non-empty `evidence_selectors`) exist as passing contract tests but constrain no execution: no trace envelope is ever built, so trace completeness is never checked for any of the 37 fixtures; `evidence_selectors` are authored into every package and read by nothing. Likewise `evaluation-run`, `trace-envelope`, `grader-result`, `coverage-manifest`, and `release-gate-decision` schemas validate no runtime instance (only unit-test payloads; `test_eval_schema_surface.py` checks filenames).
- **Failure scenario.** Exactly the Obs-26 class: a future consumer assumes "trace completeness is enforced — there's a module and a test for it" while every real evaluation runs without a trace at all.
- **Disposition — fix with C-1's rework** (a real run must build `EvaluationRun` + `TraceEnvelope` and pass `assert_trace_complete` before grading), **or** document the contract layer explicitly as forward-seam-only in the WP4 acceptance record so the coverage claim is not overstated.
- **Affected:** WP4.1 deliverables as consumed by WP4.7; W6 §§19-23.

### M-5 — Scenario A/B evidence remains partly authored: the asserted fields are literals even where real predicates now execute

- **Claim.** The rebuild materially improved on prior C-3: scenarios now call real WP1-WP3 code (`issue_prepared_dispatch`, `select_route`, `stop_confirmation`, `resume_from_checkpoint`, `EventLedger` append/restore, `authorize_operational_surface` — `research_system/evals/scenarios.py:118-210`), and C/D/E derive their asserted fields from those calls. But the fields the A/B tests actually assert are still constants: scenario A's `producer_actor_id="actor-producer"` / `verifier_actor_id="actor-independent-verifier"` (scenarios.py:135-136) makes `producer != verifier` tautological; A appends `"GraderResultRecorded"` and the pre-route event names by hand (lines 123, 133); A's adapter/operations are scenario-local stubs (`_ScenarioAdapter`, `_ScenarioOperations`), not the WP3 fake adapter, so `ProviderCommandIssued` ordering is asserted against a stub's literal; B's `original_requirement_id == reroute_requirement_id` compares one variable to itself (lines 140-152) and `"RerouteRequested"` is never produced by any reroute code. The prior review's interface rule — "no scenario branch may directly construct a passing terminal record" — is still breached for A and B's asserted fields.
- **Disposition — fix in the rework tranche:** derive A's actor identities from the routing/independence records of an actual producer/verifier route pair, drive A through `research_system/adapters/fake.py`, and make B re-evaluate a real second candidate under the preserved `RouteRequest` (assert requirement identity from the emitted route records).
- **Affected:** WP4.7; 06c §§11-12; P0 acceptance item 3 (operations dimension).

### M-6 — The canonical `main` working tree fails its own corpus validation: 8 tests and all four `eval` commands are broken on disk right now

- **Claim.** Executed evidence (2026-07-07): `uv run pytest tests/research_system -q --no-cov` on `main` → **8 failed, 283 passed**; first failure root-caused to `FixtureDefinitionError: source manifest hash mismatch` on F-001; `python -c "os.stat('...')"` shows the on-disk fixture bytes end `\r\n` while the declared hashes are over LF bytes (F-001 declared `22835cfb…`, computed `1b5c7d6a…`). Cause: `core.autocrlf=true` checked the corpus out CRLF **before** WP4.5 added `.gitattributes` (`.research-system/evals/fixtures/** text eol=lf`), and gitattributes does not renormalize already-checked-out files; `git status` shows the files clean, so the drift is invisible. A fresh worktree at ca1f49e passes hash validation (verified) and the suite runs **289 passed** with only 2 environment-sensitive failures (the subprocess-based materializer tests spawn `sys.executable` and assume `research_system` is importable in the bare interpreter — they fail in any non-synced environment, `test_control_store_fixture_corpus.py:121-132`, `test_context_routing_fixture_corpus.py` shard test).
- **Failure scenario.** The plan §8 acceptance commands are un-runnable in the canonical working copy; anyone verifying "WP4 is green on main" today gets fail-closed errors and cannot distinguish tamper from line endings. Every future in-place clone/checkout on Windows without the attributes honored (e.g., older git, `autocrlf` overrides via `-c`) reproduces it.
- **Impact.** Operational, fail-closed (no false pass) — but it blocks the very acceptance run the owner needs, and it demonstrates the corpus integrity gate is coupled to checkout configuration on the project's primary platform.
- **Disposition — fix now (one command, proposed, not executed by this review):** from the repo root on `main`:
  `git rm -r --cached .research-system/evals/fixtures >NUL && git checkout -- .research-system/evals/fixtures` (or `Remove-Item -Recurse .research-system\evals\fixtures; git checkout -- .research-system/evals/fixtures`), then rerun the suite. Additionally make the two subprocess tests robust (`env={**os.environ, "PYTHONPATH": str(ROOT)}` or skip when the package is not importable by `sys.executable`).
- **Affected:** 05-plan §8 acceptance commands; every WP4.4-4.7 integrity test on developer machines.

---

## Minor findings

- **m-1 — Retention class misdeclaration on all 37 packages.** Every `fixture.yaml` declares `retention_class: R2`, `retention_rule_id: R2:minimized_sensitive_excerpt` — a 30-day-expiring restricted class — for synthetic, permanently git-committed packages whose own source manifests state "no restricted data or transcripts". Plan §7: R1/R2 payloads never live in the repository. Either the packages are R0 (correct label, fix the field) or the repo is holding R2 payloads (policy breach). Nothing cross-checks `retention_rule_id` against `retention.RULES` at package validation — an Obs-15-style declared-vs-actual gap. *Fix:* relabel R0 (or R1) and add a `require_retention_rule` lookup to `validate_fixture_package`.
- **m-2 — `DeleteEvidenceObject` is absent.** Plan Task 3 names two WP1-owned commands; only `VerifyEvidenceDeletion` exists (`command/service.py:202-216`). Deletion-as-explicit-command is unimplemented; also the `deletion_manifest_authorizer` is a bare injectable slot — any callable returning `{"status": "verified"}` satisfies it; nothing binds it to `retention.validate_deletion_manifest_for_event`. Fail-closed when unset (good). *Fix:* register the command and bind the authorizer at composition time.
- **m-3 — Catalogue omissions unexplained.** Acceptance item 1 requires the coverage data to "explain every catalogue omission"; `omitted_gate5` explains only S-014/15/16. F-006, F-015–F-019, F-023–F-024, F-029–F-030, F-037–F-038, S-005, S-007 have no rationale rows anywhere in `catalogue.yaml` (4 lines total) or `p0-coverage.yaml`. *Fix:* add an `omitted_p0` block citing 05-plan §4.4.
- **m-4 — Calibration's evidence-comparison branch is semantically inverted.** In `_execute_twice`, `satisfied = observed_evidence == stimulus[f"{subject}_evidence"]` means a known-bad subject that exactly reproduces the authored known-bad evidence — the intended failure — yields `fixture_error` instead of `fail` (calibration.py:76-84; codified by `test_wrong_known_bad_evidence_is_fixture_error`). Harmless while no real executor exists; a trap the moment one does. *Fix together with C-1/C-2 rework.*
- **m-5 — Materializer import/runtime inconsistency.** WP4.4/4.5 use `from fixture_materializer import …` (script-relative), WP4.6 uses `from tools.ars.fixture_materializer import …` (package-relative); combined with the bare-interpreter subprocess tests this produced the two environment-sensitive failures in M-6. *Fix:* one import convention plus explicit env in subprocess tests.
- **m-6 — Fabricated independence metadata.** `independently_recomputed=True` and the `producer_family`/`grader_family` literals in harness.py:110-112 are chosen to satisfy `validate_grader_result`; the independence checks on the runnable path therefore validate the harness's choice of constants (residual of prior M-3/M-4; subsumed by C-1's fix).
- **m-7 — Test names overclaim.** `test_scientific_oracles_recompute_invariants_instead_of_trusting_pass_flags` asserts literals in the authoring dict (`CASES["F-011"].post["fit_calls"] == 0` — nothing recomputes anything); `test_each_package_encodes_its_named_behavior_contract_from_input_bytes` checks string presence and hash distinctness. Rename or implement.
- **m-8 — Positive findings retained (verify held).** `coverage.load_p0_coverage`'s exact-closure/deferral/gate5 checks; `fixture_package.validate_fixture_package` (real hash/schema/identity/closure/wildcard enforcement — the strongest new WP4.3+ code); `retention.py` end-to-end (M-8 pair binding, derived status, location-closure recheck, R3/unregistered-replica prohibition, policy-file cross-check against plan §7 values — all verified against the plan table exactly); `ReleaseGateDecision.__post_init__` exception-policy guard (M-7 fixed); `TraceEnvelope` issued-resources terminal evidence (M-2 fixed at the contract); `start_evaluation` fresh identity (M-6-prior fixed); `decide_release` per-key bindings (M-1-prior fixed); replay's deletion-event handling with `r2_intake_blocked`.

---

## Prior-review fix verification (2026-07-04 findings → final diff)

| Prior finding | Prescribed | Landed? | Where / residue |
|---|---|---|---|
| C-1 release trusts document | re-derive verdicts, one strict validator, ops precondition | **partial → new C-1/M-3** | document now ignored (not verified); verdicts synthesized in-process; operations removed from decision rather than made a precondition |
| C-2 inert fixture corpus | input-derived oracles, hash recomputation, grader registry | **partial** | hashes now recomputed and enforced (WP4.3 ✓); oracles still never consumed by any executing grader (new C-1); no grader registry |
| C-3 literal scenarios | drive real ports | **partial → M-5** | C/D/E largely real; A/B asserted fields still literal |
| M-1 scalar coverage hashes | per-ResultKey maps | **✓** harness.py:20-31, release.py:24-85 |
| M-2 resource terminal evidence | typed issued_resources | **✓ contract-level** (models.py:165, 190-205) — unexercised at runtime (M-4) |
| M-3 calibration fail→pass | unexpected outcome = fixture_error | **✓ shape** (calibration.py:79-84) — unreachable via tautological default executor (C-2) |
| M-4 duplicated repetition | execute twice | **✓ for known-bad/good; fabricated for mutations (C-2)** |
| M-5 inventory-only validate | per-file schema/hash validation | **✓** fixture_package.py |
| M-6 reused run identity | fresh id + lineage | **✓** lifecycle.py |
| M-7 unbound exception_limited | policy id/hash required | **✓** models.py:420-441 |
| M-8 actor/grant cross-pairing | exact pair binding | **✓** retention.py:37-51, 203-206, 257-263 + cross-pair test |
| M-9 missing evidence selectors | non-empty selectors | **✓ contract/schema** — consumed by nothing (M-4) |

## Commit/PR claim audit (attack vector 4)

| Claim | Source | Verdict |
|---|---|---|
| "execute known-bad, known-good, and declared mutation calibration twice" | PR #67 | **False for mutations** (C-2); known-bad/good executed but tautological |
| "route 122 typed grader results through the strict release primitive" | PR #67 | Mechanically true; materially misleading — the "grader results" were produced by no grader (C-1) |
| "drive Gate 3 scenarios through the public issue coordinator, route selector, checkpoint/stop predicates, authorization boundary, and atomic ledger replay" | PR #67 | Substantially true for C/D/E; overstated for A/B (M-5) |
| "producer-shaped dictionaries cannot enter the typed release path" | PR #67 | True (TypeError guard) — but see M-3 for what the release command actually evaluates |
| "290 passed" / "37 valid" / "37 calibrated; 14 blocked" / "122 results; blocked" | PR #67 | Reproduced at ca1f49e in a fresh worktree (289 + 2 env-sensitive failures; CLI outputs match) — **not reproducible on the live main tree** (M-6) |
| "bind each staged package to explicit input-derived oracles" | PR #66 | Overstated: oracles are authored literals, hash-bound to bytes (real) but derived from nothing |
| "enforce cross-family independence for M graders and non-compensable two-key evidence for F-035" | PR #65 | **Declared, not enforced**: the fixture data names the requirements; the only enforcement (`validate_grader_result`) is fed fabricated family metadata (m-6); no two-key logic exists in code |
| "LF-normalized hash-bound fixture files" | PR #65 | True for fresh checkouts; silently false for pre-existing checkouts (M-6) |
| WP4.1 remediation bullets (M-1/M-2/M-7/M-9) | PR #61 | **Verified — all four landed** |
| Retention bullets (pair binding, derived status, trusted authorizer) | PR #62 | **Verified** (m-2 notes the DeleteEvidenceObject gap and unbound authorizer slot) |

## Consistency matrix (invariant → enforcement → test → status)

| Invariant | Enforcement point | Test | Status |
|---|---|---|---|
| Exact 37-case closure, r1, fake transport | `coverage.load_p0_coverage` | test_coverage, test_eval_cli | **holds** |
| Gate 5 deferrals immutable; no self-authorization | coverage.py:101-121 | test_coverage | **holds** |
| Exact required-result closure (empty/partial/dup/extra/stale blocked) | `release.decide_release` | test_release_gate | **holds (structural)** |
| Producer verdict is not proof | should be verdict re-derivation | TypeError guard only | **violated (C-1)** |
| Property recomputed from immutable inputs | none | test names overclaim (m-7) | **violated (C-1/C-2)** |
| Mutations detected in every repetition | none (constants) | asserts the constants | **fabricated (C-2)** |
| Package bytes hash-bound to declarations | `validate_fixture_package` | corpus tests + fresh-worktree run | **holds on fresh checkout; broken on main tree (M-6)** |
| No wildcard variant binding | fixture_package.py:196-207 | unit test | **holds — but matrix is one generic row (M-2)** |
| F-021 P1 at p0_materialization with sizing variant | fixture.yaml priority/gate ✓ | corpus test | **partial — sizing variant absent (M-2)** |
| Trace completeness (commands + resources) | `assert_trace_complete` | unit only | **unexercised at runtime (M-4)** |
| exception_limited requires accepted policy | models.py post_init + schema | test_eval_models | **holds (contract)** |
| R1/R2 rules = plan §7 exactly; R3/unregistered replicas prohibited | retention.RULES + validate_retention_policy | test_retention + CLI | **holds (verified value-by-value)** |
| Deletion status derived; actor/grant pair-bound; closure rechecked | verify_deletion / validate_deletion_manifest_for_event / service.py | test_retention | **holds** (m-2 residuals) |
| EvidenceDeletionVerified only via trusted authorizer | service.py:202-216 | test suite | **holds; authorizer binding unpinned (m-2)** |
| Scenarios derive evidence from composed ports | scenarios.py | test_gate3_scenarios | **partial (M-5)** |
| ReleaseGateDecision emitted, dated, non-overwriting | none | none | **not implemented (M-3)** |
| gate_stage closed enum; retired aliases invalid | models + fixture-definition schema | schema/enum tests | **holds** (06c §9) |
| 06c singular identities (`trace_id`, `grader_result_id`, `routing_evidence_snapshot_id`…) | models.py field names | model tests | **holds** (no alias drift found) |
| F-036 = 06b identity (3 mutations, lanes, provenance) | materializer CASES | none | **violated (M-1)** |

## Scenario disposition

| Scenario | Executes real code? | Asserted fields authored? | Disposition |
|---|---|---|---|
| A | `authorize_operational_surface` + `issue_prepared_dispatch` (with local stubs) | actor IDs, pre-route events, GraderResultRecorded — yes | **rework (M-5)** |
| B | `select_route` hard-gate failure — yes | requirement IDs (self-comparison), RerouteRequested — yes | **rework (M-5)** |
| C | `stop_confirmation` + `resume_from_checkpoint` — yes | initial epoch literal only | **accept as P0 evidence** |
| D | real `EventLedger` write/restore/iterate | none material | **accept as P0 evidence** |
| E | real authorization denial | decision_reason literal (matches actual denial) | **accept as P0 evidence** |

## P0 acceptance checklist disposition (04-plan §"P0 acceptance and independent review")

| Item | Disposition |
|---|---|
| 1. 37 exact + every omission explained | **partial** — 37 exact ✓; only Gate-5 omissions explained (m-3) |
| 2. R1/R2 durations/owners/leads/external root/deletion path; R3 prohibited | **holds** |
| 3. Non-compensable critical/required; exact closure before verdicts | **structural holds; verdict provenance fails (C-1)** |
| 4. Two-repetition calibration; missing stochastic/M-H policy blocks | **fails (C-2)** — also no calibration-policy artifact exists |
| 5. F-021 P1 at P0 materialization | **partial** — staging ✓, sizing variant absent (M-2) |
| 6. No raw UKDA/secrets/hidden reasoning/transcripts | **holds** (corpus inspected; synthetic identifiers throughout) |
| 7. M/H independent or blocking unable_to_grade | **holds on the runnable path** (18 M/H rows blocking; decision `blocked`) |
| 8. Fresh review of F-011/F-012/F-022/F-026/F-035/F-036 incl. F-036 mutations from F-015/F-016 classes | **done here — fails**: all six are declarative; no executable oracle; F-036 identity rewritten (M-1) |
| 9. ReleaseGateDecision records pass/fail/blocked; exception_limited gated | **contract holds; no decision record ever emitted (M-3)** |
| 10. Gate 5 closed until S-014/15/16 + accepted P0 decision | **holds** |
| 11. Stephen accepts P0 evidence before live/pilot/research | **not reached — and must not be, on current evidence** |

## Decision audit

- **Keep:** WP4.1 contract surface and strict release primitive; WP4.2 retention module wholesale; WP4.3 package validator; WP4.4-4.6 corpora *as staged declarative packages* (their honest `status: authored` / `calibration_record_id: null` labeling is a strength); scenario C/D/E execution; Gate-5 restriction machinery.
- **Amend (owner decisions — do not proceed silently):** (a) whether P0 accepts label-tautology calibration and synthesized verdicts as an explicit, documented simplification with a hard dependency before any gate reliance — the fabricated mutation records cannot be accepted even under that amendment; (b) the F-036 identity rewrite (restore or amend 06b); (c) the collapsed variant matrix (implement or amend the plan obligation).
- **Reject:** the WP4.7 completion claim "complete ARS P0 evaluation harness" as evidence that the 37-case closure is *executably* proven; any reading of the 108 `pass` rows in run evidence as grader outcomes; the mutation-calibration test/PR claims.
- **Defer (correctly deferred, verified):** S-014/S-015/S-016 with capability restrictions; live M/H authority; replica-discovery assurance (Gate 5 / S-014).

## Practicality assessment

The tranche discipline (7 PRs, ≤150 files each, review-then-merge) demonstrably worked — WP4.1-4.3 fixes are real and verifiable, and the corpus is inspectable. The remaining rework is concentrated, not diffuse: one executor/grader seam (C-1/C-2), one release-artifact seam (M-3), two scenario methods (M-5), one corpus relabel + matrix (M-1/M-2), one renormalization command (M-6). No new architecture is needed; the strict validator and package validator are the right skeleton to hang real execution on.

## Revision plan

**Immediate (before any further reliance on WP4 evidence):**
1. Renormalize the main working tree and rerun the suite (M-6); harden the two subprocess tests.
2. Remove or truthfully relabel the fabricated mutation records and the `…executed_twice_and_detected` test (C-2, cheapest honest state), pending real implementation.

**Rework tranche (WP4.8, review-then-merge):**
3. Wire verdict derivation: calibration/grader registry → `run_p0_coverage` (C-1, m-6, m-4); broken-oracle regression test.
4. Emit and persist a dated `ReleaseGateDecision` with operations/parity status; make `--evaluation-runs` meaningful or remove it (M-3, M-4 partially).
5. Rebuild scenario A/B evidence from real route/adapter records (M-5).

**Corpus corrections (owner-gated):**
6. Restore F-036's 06b identity or file the 06b amendment (M-1).
7. Materialize the variant matrix + threshold/calibration policy files or amend the plan obligation (M-2).
8. Relabel fixture retention classes; check `retention_rule_id` against `RULES` in the package validator (m-1); add omission rationales (m-3); register `DeleteEvidenceObject` and pin the authorizer (m-2).

## Residual risks

- Until C-1/C-2 close, every green WP4 signal (tests, CLI, contract gate) is compatible with a corpus that detects nothing; treat "blocked" as the only trustworthy output of the current harness.
- The corpus integrity gate is checkout-configuration-coupled on Windows (M-6); any hash-bound tracked artifact set inherits this unless binary-attributed or renormalization is scripted.
- Deterministic fakes still cannot establish live M/H authority; unchanged from prior reviews.

## Verification evidence and change log

- Read in full: the four governing specs, both prior reviews, all `research_system/evals/*` modules, `cli.py` eval section, `command/service.py`, `projection/replay.py`, all three shard materializers + shared helper, corpus/CLI/scenario/calibration/release-coordinator tests, `catalogue.yaml`, `p0-coverage.yaml`, `retention-policy.yaml`, `.gitattributes`, fixture-definition schema surface.
- Executed on `main` working tree (2026-07-07): `uv run pytest tests/research_system -q --no-cov --ignore=TDL` → 8 failed / 283 passed; F-001 declared vs computed source-manifest hash mismatch reproduced; on-disk fixture bytes confirmed CRLF-terminated.
- Executed in throwaway detached worktree at ca1f49e (created for this review, removed afterward): full suite → 289 passed / 2 environment-sensitive failures (both `ModuleNotFoundError: research_system` in spawned bare interpreters); `eval calibrate` → `{"blocked_fixture_count":14,"fixture_count":37}`; `eval run` → `{"candidate_status":"blocked","result_count":122}`; F-001 hash binding verified to match on fresh checkout.
- PR #61/#62/#65/#66/#67 bodies fetched via `gh` and audited above.
- Files changed by this review: this report only. Note: pytest collection on `main` additionally requires ignoring a stray zero-byte unreadable `TDL` entry at the repo root (WinError 1920, likely a WSL socket artifact; untracked, predates this review, left untouched).
