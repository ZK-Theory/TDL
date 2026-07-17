# Adversarial Review — Revised ARS WP6 Plan Suite

**Review date:** 2026-07-17  
**Verdict:** `accept_with_required_changes` — the revised suite is not dispatchable  
**Exact reviewed commit:** `45d29dd16cc5e654eb0be086d81eda9771711f11`  
**Reviewed checkout:** `C:/Users/steph/.codex/worktrees/132d/TDL`  
**Reviewed branch:** `codex/wp6-plan-suite-review-remediation`  
**Previous reviewed head:** `4995f63ebb05df311320bd9035f6bb23f32573f0`  
**Reviewer identity/family:** Codex, GPT-5 family, fresh independent task context

## 1. Exact commit and checkout verification

The review preflight passed:

- `git rev-parse HEAD` in the reviewed checkout returned exactly
  `45d29dd16cc5e654eb0be086d81eda9771711f11`.
- `git symbolic-ref --short HEAD` returned
  `codex/wp6-plan-suite-review-remediation`; the checkout was not detached.
- `git status --short --branch` returned only the branch header. The worktree was clean.
- Both unstaged and staged diffs for the four primary files were empty.
- `git cat-file -t 45d29dd...` returned `commit`.
- `4995f63...` is an ancestor of the reviewed commit. The remediation commit itself
  changes only the four primary review targets; its parent is `408f52b...`.

All primary files were read in full from the exact commit. Governing W1/W2/W4/W5/W6/
W7/W8 designs, the accepted F-031–F-038 addendum, Gate 5 plans/reviews/decisions,
current schemas, the fake-only coverage loader, the variant producer, the CLI, fixture
packages, and relevant tests were then checked directly in the same checkout. No
validation from another checkout or commit is credited.

## 2. Independence and authority boundary

I did not author or remediate this revision and did not consult an author transcript,
prior task reasoning, or hidden chain of thought. The original review was used only as
the required condition set. Every disposition below was re-derived from committed
authority and the exact reviewed source.

This is a planning review only. It authorizes no code implementation, provider call,
research computation, state migration, vault mutation, owner decision, pilot, claim
transition, or WP6.1/WP6.2 dispatch. Model/context independence is not independent
human authority. Stephen remains the owner for every reserved decision.

## 3. Executive verdict

The remediation materially improves the suite. C-1, M-3, M-4, M-7, and m-1 are
closed: the secret/cost matrix is pre-issue and provider-specific; live parity is bound
to command/receipt/enforcement evidence; `ModelEvalProfile` now mirrors W4 §§10.2–
10.3; migration paths and writer sets are physically separated; and P-031–P-034 now
satisfy the register protocol without changing decision substance.

The suite nevertheless retains four open Major defects:

1. the unified T1 gate is empirically circular and is not yet supported by an accepted
   owner decision for T2–T4;
2. the WP6.1 owner-source matrix still groups whole command and transition families,
   so an implementation-defined W2 subset can satisfy the named exact-set test;
3. the P1 `11`-row closure counts baseline graders but does not make mutation/
   calibration/activation evidence part of the atomic pilot/claim gate; and
4. T7 says both “rerun 51 obligations” and “one live key per all 302 positions,” while
   neither the proposed manifest nor the current CLI specifies how the remaining 251
   rows are represented without relabelling frozen fake evidence.

The correct verdict is therefore `accept_with_required_changes`. The direction can be
revised, but this exact commit is not eligible for WP6.1/WP6.2 approval or dispatch.

## 4. Major findings

### M-1 — Major — the all-task T1 gate is consistent in prose but circular in evidence and still owner-pending

1. **Claim.** The remediation now reproduces one DAG consistently, but the selected
   edge — accepted T1 policy before T2–T8 — requires an evidence-bearing live-grader
   calibration policy before the plan permits the transport/security work needed to
   generate that evidence. P-033 supports policy closure before R2 research dispatch;
   it does not already authorize this stronger implementation-order edge.
2. **Evidence.** T1 must record exact mutation-corpus identity, estimand, repeats,
   uncertainty, false-pass/false-block bounds, and required result/evidence IDs and
   hashes, then pass independent review and Stephen acceptance
   (`implementation/06b-wp6-2-live-capability-plan.md:44-54`). T2–T8 are all downstream
   (`:54`, `:126-142`, `:271`), and no live call may occur before T2 merges and its
   provider-specific negatives pass (`:279-280`). The plan also calls the calibration
   an empirical statistical claim (`:300-305`). W6 requires calibration corpus,
   uncertainty, error trade-off, and calibration records
   (`design/06-evaluation-observability-and-audit.md:543-557`). P-033 requires policy
   and live evidence before R2 research dispatch, not before adapter implementation
   (`03-decisions-and-open-questions.md:399-408`). D-G6-2 is still an owner-decision
   point, not an accepted record (`implementation/06-wp6-gate6-readiness-and-
   integration-plan.md:195-203`).
3. **Executable failure scenario.** Dispatch T1 under the stated graph. The Worker can
   either (a) write thresholds and false-pass/false-block evidence without a permitted
   live grader run, (b) make an unauthorized provider call before T2, or (c) stop
   because the evidence IDs/hashes do not exist. A document-only T1 can still pass
   schema/review checks if it records intended future evidence as though it were
   observed calibration.
4. **Impact.** The first owner gate is circular or invites unsupported empirical
   precision. It can block the programme indefinitely or accept a policy whose stated
   calibration is not evidence-backed.
5. **Disposition:** `regressed`; fix before approving the WP6.2 DAG.
6. **Exact required change.** Split T1 into two typed stages, or explicitly authorize
   an equivalent non-circular source:
   - **T1a:** preregister and independently review the strict calibration protocol,
     corpus, estimand, error bounds, and acceptance rule; no claim of observed
     calibration;
   - **T2 → T3/T4:** establish the secret/cost boundary and bounded independent Claude/
     Codex canary transports;
   - **T1b:** produce immutable calibration results through those protected seams and
     obtain Stephen's acceptance of the exact evidence-bearing policy hash;
   - only T1b acceptance may gate T5–T8 and M/H eligibility.

   If Stephen instead intends T1 acceptance before T2–T4, D-G6-2 must name the already
   existing, independently admissible calibration evidence source and its IDs/hashes.
   The header, DAG, stop conditions, checklist, and dispatch branches must then reflect
   that accepted decision exactly.
7. **Affected decisions/work packages:** D-G6-2, P-029, P-033; W4 §10, W6 §27;
   WP6 master; WP6.2 T1–T8.

### M-2 — Major — the W2 owner-source “exact set” is still grouped and self-defining

1. **Claim.** The proposed matrix schema is useful, and all 13 W8 §20 commands are now
   named, but the plan still presents six grouped owner rows rather than a literal row
   per W2 command/transition. “Every status edge,” state lists, and grouped command
   families leave the expected set to implementation or test-code interpretation.
2. **Evidence.** The future YAML has a singular `command_or_transition` field and is
   said to have “one row per item below” (`implementation/06a-wp6-1-runtime-task-
   lifecycle-plan.md:122-129`), but the table has only six source rows. One row groups
   `CompleteScope`, fourteen Task commands, and “every status edge”; another groups the
   complete dispatch graph and four commands; another groups every attempt edge; and
   the artefact/review/decision row groups six dimensions, eight review states, six
   decision states, `ResolveDecision`, and `RecordCorrection` (`:131-138`). W2 owns
   literal Task edges (`design/02-task-event-and-artifact-schema.md:428-447`), dispatch
   and attempt graphs (`:470-509`), review states/authority (`:752-779`), and decision/
   rule/correction semantics (`:795-841`). W8 names 13 exact operator commands
   (`design/08-resource-checkpoint-and-operations.md:359-379`).
3. **Executable failure scenario.** Materialize six matrix rows containing grouped
   strings, register only the explicitly implemented subset, and make the test compare
   the registered catalogue with those same grouped matrix entries. The exact-set test
   is green while one suspended Task edge, a review-state transition, artefact
   supersession, or a dispatch expiry edge has no command schema, event, reducer,
   authority rule, or negative test. Alternatively, test code expands “every edge”
   from the implementation registry, reproducing the same self-certification.
4. **Impact.** Gate A A4/A5 can clear while accepted W2 lifecycle semantics remain
   absent. Replay, authority, and atomic-rejection behavior then depend on an
   implementation-defined subset.
5. **Disposition:** `partial`; flatten before WP6.1 dispatch.
6. **Exact required change.** Commit a literal expected-row catalogue in the plan (or a
   content-addressed plan annex) with one row per normalized key:
   `owner_source + command`, or `owner_source + from_state + transition + to_state`.
   Expand every W2 §11–§19 command/edge and every one of the 13 W8 commands. Each row
   must independently name schema, semantic event, event schema, reducer, projections,
   authority/precondition, receipt, positive test, and applicable one-field,
   illegal-transition, stale-version, conflicting-payload, idempotency, independence,
   and atomic-no-side-effect negatives. The test's expected keys must be generated
   from that accepted catalogue, never from runtime registrations or grouped prose.
7. **Affected decisions/work packages:** P-006, P-008–P-013, P-020, P-030; W2 §§10–21;
   W8 §§7–21; WP6.1 T1–T8.

### M-5 — Major — `11` is only the baseline-grader count, not exact P1 activation closure

1. **Claim.** T8 now says materialize, calibrate, activate, and atomically consume
   F-037/F-038, but its only exact required-result set is eleven baseline grader rows.
   The gate does not name the mutation/repetition calibration records, their hashes,
   applicability acceptance, or activation record as required atomic inputs.
2. **Evidence.** The plan defines four F-037 mutations and three F-038 mutations, two
   repetitions, and baseline D/T/R/M/H plus D/T/R/M/H/P rows
   (`implementation/06b-wp6-2-live-capability-plan.md:172-188`), then declares exact
   P1 result closure `0 → 11` (`:243-250`) and says the baseline test asserts exact
   result keys (`:265-266`). The accepted addendum requires calibration of the named
   attacks and declaration of trace predicates, repeats, uncertainty, false acceptance/
   rejection, expiry, and variants before activation
   (`design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md:25-28,
   41-61`). W6 distinguishes `authored`, `calibrated`, and `active`
   (`design/06-evaluation-observability-and-audit.md:109-122`). The current fixture
   schema separately requires `mutation_ids`, `safe_variation_ids`, and
   `calibration_record_id` (`.research-system/schemas/evals/fixture-definition.schema.
   json:15-18,69-75`), while current calibration executes known-bad, known-good, and
   every mutation twice (`research_system/evals/calibration.py:1-7,94-128,131-173`).
3. **Executable failure scenario.** Produce all eleven baseline grader results as pass,
   but omit or stale the calibration record for `auto-promote result into claim`, or
   omit one private-pack leak mutation. A handler that checks the plan's exact eleven
   result keys and current fixture/schema revisions can accept pilot evidence or a
   claim even though the fixture never reached valid `calibrated → active` state.
4. **Impact.** Presence-plus-baseline success substitutes for the non-compensable
   calibration and activation that P-029/W6 require. The first pilot can accept
   evidence or promote claims with an untested critical bypass.
5. **Disposition:** `partial`; complete the activation referent before T8 dispatch.
6. **Exact required change.** Define two separate exact sets:
   - the eleven baseline grader-result keys; and
   - the complete activation closure, including each fixture revision/hash, seven
     mutation IDs/hashes, safe-variation and known-good identities, both repetitions,
     per-mutation verdict/evidence hashes, false-pass/false-block summary, threshold
     policy ID/hash, independently accepted F-038 applicability evidence,
     `calibration_record_id`/hash, and activation record ID/hash.

   Pilot-evidence acceptance and claim-promotion commands must consume the union at one
   expected event position. Add one-at-a-time missing, failed, `unable_to_grade`, stale,
   duplicate, incompatible, omitted-mutation, wrong-repeat, and unapproved-applicability
   negatives with an unchanged event tail, accepted-result set, Decision set, and claim
   set. Do not label eleven baseline rows as the complete activation closure.
7. **Affected decisions/work packages:** P-019, P-029, P-033; W5 §§19–20; W6 addendum;
   WP6.2 T8; Gate 6 pilot and claim-promotion seams.

### M-6 — Major — the live 302-row invariant has no executable provenance composition

1. **Claim.** T7 says it reruns the 51 unavailable M/H obligations and preserves frozen
   fake keys, but the invariant table simultaneously requires “one live key per” all
   302 required positions. The plan does not choose between a 251-frozen + 51-live
   composite closure and a complete 302-row live rerun, and it does not define a schema
   or loader that can enforce either interpretation.
2. **Evidence.** T7 creates a new manifest, maps the 51 unavailable obligations to
   actual live provider/adapter result keys, preserves frozen fake keys, and reruns
   “those obligations” (`implementation/06b-wp6-2-live-capability-plan.md:107-117`).
   Section 6.2 then calls the output a new 302-row live closure (`:205-210`) and says
   `result_count=302` because there is “one live key per required coverage position”
   (`:231-237`). The current exact baseline is 132 baseline results plus 170 variant
   results; the variant producer emits one result per required grader per selected
   matrix row (`research_system/evals/variants.py:355-380,383-461`; `research_system/
   evals/harness.py:371-403`). The current CLI and loader are expressly fake-only
   (`research_system/cli.py:237-262`; `research_system/evals/coverage.py:86-99`). The
   generic coverage schema has only a global `provider_variants` set and a six-field
   result key, with no per-key predecessor/replacement/provider/adapter/hash mapping
   (`.research-system/schemas/evals/coverage-manifest.schema.json:5-45,61-69`).
3. **Executable failure scenario.** Implement a manifest with 251 frozen fake results
   plus 51 live results. A count/exact-key smoke passes at 302, but the invariant's
   “one live key per position” is false. Or relabel the 251 old keys as live without
   rerunning them, satisfying the text/count while violating immutable Gate 5
   provenance. A third implementation can dispatch the existing CLI by filename and
   bypass its hard-coded fake exact-set checks for the two new manifests.
4. **Impact.** Capability eligibility can rest on provenance-mixed or relabelled
   evidence while every stated aggregate count is correct. The future CLI can also
   weaken the accepted P0 loader inadvertently.
5. **Disposition:** `partial`; the original count-remediation remains incomplete.
6. **Exact required change.** Choose and pre-register one model:
   - **Composite:** 251 immutable Gate 5 result references plus 51 new live results,
     with a one-to-one replacement map from old M/H key to new key and explicit counts
     `referenced_frozen=251`, `new_live=51`, `aggregate_closure=302`; or
   - **Full live rerun:** 302 genuinely new live result keys with exact per-row execution
     obligations and no reuse claim.

   Define a versioned live-coverage schema with per-key source artifact ID/hash,
   lifecycle stage, fixture/grader/variant, provider/model/adapter revisions and hashes,
   command/receipt, grant/lease, and predecessor/replacement relationship. Define an
   explicit stage-aware loader/CLI dispatch contract that preserves the current P0
   fake-only loader unchanged. Negative tests must reject missing, duplicate, extra,
   stale, incompatible, relabelled, wrong-provider, wrong-adapter, and mixed-lifecycle
   rows before capability status changes. Update the invariant wording and smoke to
   match the selected composition exactly.
7. **Affected decisions/work packages:** D-G5-3/D-G6-3, P-018, P-029, P-030, P-033;
   W6/W7; WP6.2 T7–T8.

## 5. Original finding closure table

| Finding | Disposition | Independent basis |
|---|---|---|
| C-1 | **closed** | Typed, identity-bound `SecretReference`/`CostGrant`; pre-issue sentinels cover context, generated adapter, payload, argv/config, event, receipt, object, and fixture/evidence producers; byte-identical canonical stores and zero invocation are required; replay/concurrency and independent Claude/Codex evidence are explicit (`06b:55-79,144-170`). |
| M-1 | **regressed** | Restatements now agree and usability is hoisted (`06:263-299`), but the chosen T1→T2–T8 edge is owner-pending and empirically circular (finding M-1 above). |
| M-2 | **partial** | W8's 13 commands and stronger negatives are explicit, but the W2 source catalogue remains grouped rather than row-exact (finding M-2). |
| M-3 | **closed** | Each provider/control row binds canonical applicability, adapter/model, rendered payload, actual command/receipt, grant/lease, and observed predicate; each critical control is perturbed at the real adapter/transport seam and surface/self-attested evidence is rejected (`06b:80-88`). |
| M-4 | **closed** | T6 reproduces every W4 §10.2 field and §10.3 threshold, including outcome classes, omissions, parity, currentness, suspension, authority, exact one-field negatives, family coverage, and actual-attempt independence (`06b:89-106`; W4 `:264-289`). |
| M-5 | **partial** | Materialize/calibrate/activate and atomic gate language was added, but exact activation closure is still reduced to eleven baseline rows (finding M-5). |
| M-6 | **partial** | Frozen Gate 5 values and stage-specific tables exist, but live result composition/manifest semantics contradict one another (finding M-6). |
| M-7 | **closed** | `_backlog.md`, `00-Meta/ARS/Discovery/`, `00-Meta/ARS/Discovery-annotations/`, and optional aggregate view are distinct; writer sets, ingestion, collision, rebuild, and one-way whole-path cutover are mandatory (`06:122-154`; P-032 `:388-397`). |
| m-1 | **closed** | P-031–P-034 now contain explicit evidence, migration consequence, and complete affected-specification lists; the remediation diff adds metadata only and preserves accepted decision text (`03-decisions:376-418`). |

## 6. Re-run of all ten attack surfaces

| # | Attack surface | Outcome | Disposition |
|---|---|---|---|
| 1 | Gate A mapping accuracy | **holds** | Exact source still has `live_enabled:false` for Claude/Codex, null foundation project/control root, the six-field Task schema, and only the partial reducers (`.research-system/adapters/{claude,codex}.yaml:5`; `.research-system/config/foundation.yaml:3-5`; `.research-system/schemas/core/task.schema.json:5-15`; `research_system/command/reducers.py:16-80`). The A2–A8 map remains accurate. |
| 2 | Owner/dependency touchpoints | **Major M-1** | DAG restatements and WP6.1 usability are aligned, but the all-task policy gate is circular and still requires explicit Stephen disposition. |
| 3 | Credential/cost and live capability | **C-1/M-3/M-4 closed** | Pre-issue, provider-specific secret/cost evidence; execution-bound parity; and complete W4 profile closure are now specified. No post-run scan is used as primary control. |
| 4 | Gate 5 acceptance consistency | **holds, subject to M-6 fix** | Frozen 40/15/0/302/calibrated, blocked candidate, `gate5_authorized=false`, D-G5-1(a), O15 deferral, G5.3-B(a), and S-016 remain explicit. M-6 concerns the new Gate 6 evidence composition, not a present authorization to rewrite Gate 5. |
| 5 | P-031 pilot amendment | **holds** | SCALE-01 changes only the pilot occupant; preflight and inherited first-paper promotion criteria remain. |
| 6 | W11/WP6.5 migration scope | **holds** | Physical path/writer exclusivity, annotation ingestion, deletion/rebuild, per-item transition, and whole-path cutover close the earlier shared-path defect. |
| 7 | Invariant re-baseline | **Major M-5/M-6** | Frozen counts are derivable; the live and P1 “exact” closures do not yet identify all evidence they claim to close. |
| 8 | Binding-test adequacy | **Major M-2/M-5/M-6** | Several producing-seam rows are now strong, but grouped W2 expected rows, eleven-row activation, and count-only live composition can still pass while their properties fail. |
| 9 | Dependency DAG | **Major M-1** | The graph is textually consistent but cannot generate its own T1 evidence under its no-live-before-T2 rule. |
| 10 | Register integrity | **closed** | P-031–P-034 satisfy the register protocol and preserve owner substance. |

## 7. Binding-test audit

| Named claim/test | Can it pass while the property fails? | Disposition |
|---|---|---|
| WP6.1 T1 strict Task/Scope schema | **Yes, through M-2.** A strict schema can match a grouped local matrix while an accepted W2 edge is absent. | Flatten the owner-source rows. Scope member/stale-revision negatives themselves are sound. |
| WP6.1 T2 claim/idempotency | **No, if row-exact.** Conflicting claimants, same tuple/different payload, replay, and preserved attempt evidence are explicit. | Keep; bind each transition separately. |
| WP6.1 T3 messages/Partial | **No material bypass found.** Immutable acknowledgement and new-epoch reopen are producing-seam properties. | Closed. |
| WP6.1 T4 artefact consumer predicates | **No material bypass found.** Each dimension is independently tested and producer aggregate/self-assertion cannot authorize use. | Closed. |
| WP6.1 T5 review/Decision/correction | **No material bypass found.** Exact review set, independence, reserved Decision authority, RuleEvaluation separation, subject hash, and history preservation are named. | Closed, subject to row-exact catalogue. |
| WP6.1 T6 every W8 command | **Yes, through M-2.** All 13 names are present, but grouped matrix expansion is not itself a literal accepted set. | Flatten to 13 command rows plus exact W2 mappings. |
| WP6.1 T7 projection rebuild/non-authority | **No material bypass found.** Mutation is ignored as authority, diagnosed, and deletion/rebuild is byte-identical. | Closed. |
| WP6.1 T8 no-change baseline | **No material bypass found for the frozen surface.** It asserts all eight values and tracked Gate 5 bytes. | Closed for WP6.1. |
| WP6.2 T1 policy schema/review | **Yes — M-1.** A document can satisfy field/review checks while its empirical IDs/bounds were never generated by an allowed live seam. | Split protocol from evidence-bearing acceptance. |
| WP6.2 T2 secret/cost matrix | **No material bypass found.** Each rejection is before invocation with zero canonical side effects; positive path binds all identities; replay and concurrent oversubscription are explicit. | C-1 closed. |
| WP6.2 T3 Claude evidence | **No material bypass found.** Full T2 matrix runs against an invocation-counting Claude canary before smoke. | Closed. |
| WP6.2 T4 Codex evidence | **No material bypass found.** Codex repeats the full matrix and cannot inherit Claude/shared-helper success. | Closed. |
| WP6.2 T5 live parity | **No material bypass found.** Real seam perturbation is required before observation for every critical control. | M-3 closed. |
| WP6.2 T6 ModelEvalProfile | **No material bypass found.** Exact field closure and one-field negative classes match W4; actual-attempt independence is recomputed. | M-4 closed. |
| WP6.2 T7 302-key live baseline | **Yes — M-6.** A 251-fake/51-live composite or relabelled set can satisfy aggregate 302 without satisfying “one live key per position.” | Define schema, composition, and stage loader. |
| WP6.2 T8 eleven P1 results | **Yes — M-5.** Eleven baseline results can pass with a missing/stale mutation calibration or activation record. | Gate on complete activation closure. |
| WP6.6 admission exact manifest | **Not presently dispatchable.** The master correctly requires missing/duplicate/extra/stale/incompatible/tampered atomic rejection, but the future child plan must preserve it. | Forward obligation retained. |
| W11 vault projection-only | **No material bypass found at plan level.** Legacy, generated, annotation, and aggregate writer paths are disjoint and cutover is one-way. | M-7 closed. |

## 8. Cross-spec consistency matrix

| Invariant | Governing authority | Planned enforcement | Status |
|---|---|---|---|
| No credential material reaches context/generated adapter/payload/argv/canonical evidence | W1 §9.6; W7 §21 | T2 matrix + independent T3/T4 canaries | **closed** |
| Every live issue has an atomic bounded cost reservation | W7 ProviderCommand; W8 grant semantics | `CostGrant`, pre-issue reservation, replay/concurrency negatives | **closed** |
| One owner-approved WP6.2 DAG | P-033; D-G6-2 | T1→T2–T8 everywhere | **regressed** — consistent but circular and owner-pending |
| Exact W2/W8 lifecycle | W2 §§10–21; W8 §20 | owner-source matrix | **partial** — grouped W2 rows |
| Live parity binds actual enforcement | W7 §§9–10/17 | actual-seam perturbation + command/receipt evidence | **closed** |
| Profile eligibility derives from complete current evidence | W4 §§10.2–10.3 | strict profile + one-field negatives | **closed** |
| P1 fixtures are calibrated, active, and atomically consumed | P-019/P-029; W6 addendum | eleven result keys + prose activation | **partial** — calibration/activation referents absent |
| Gate 5 evidence remains immutable | D-G5-1(a), D-G5-2, D-G5-3, G5.3-B(a) | separate frozen table + byte assertions | **holds** |
| New live evidence has lifecycle-specific identities | P-018/P-030; W6/W7 | new live manifest | **partial** — 302 composition/schema undefined |
| Provider outage preserves all requirements | S-016; W4 §17 | wait/block/`unable_to_grade`; no lower-grade substitute | **closed** |
| Legacy and successor writers never share a mutable path | P-004/P-021/P-032/P-034 | four-path registry/cutover contract | **closed** |
| P-031–P-034 register fields are complete | register protocol | explicit evidence/migration/affected specs | **closed** |

## 9. Independent invariant derivation

### 9.1 Frozen Gate 5 surface

The exact target's production loader was run read-only from the reviewed checkout with
bytecode writes disabled. It validated the committed package hashes and returned the
following structural derivation (no provider, research, or fixture computation):

| Quantity | Independent derivation | Value |
|---|---|---:|
| selected fixture revisions | `len(p0-coverage.yaml:selected_fixture_revisions)` | 40 |
| baseline result keys | sum of required graders over the 40 selected packages | 132 |
| accepted Gate 5 variant rows | exact `load_gate5_variant_rows` closure | 46 |
| variant result keys | sum of every selected row's fixture grader count | 170 |
| total required result keys | `132 + 170` | 302 |
| unavailable M keys | exact M keys across baseline + selected variants | 31 |
| unavailable H keys | exact H keys across baseline + selected variants | 20 |
| unavailable total | `31 + 20` | 51 |
| otherwise available result positions | `302 - 51` | 251 |
| blocked fixtures | fixtures owning at least one M/H key | 15 |

The by-fixture M/H derivation exactly matches the revised table:

| Fixture | M | H | Fixture | M | H |
|---|---:|---:|---|---:|---:|
| F-005 | 0 | 1 | F-009 | 0 | 3 |
| F-012 | 3 | 0 | F-014 | 0 | 3 |
| F-020 | 3 | 0 | F-021 | 1 | 0 |
| F-022 | 3 | 3 | F-025 | 3 | 3 |
| F-026 | 3 | 0 | F-031 | 3 | 0 |
| F-032 | 3 | 0 | F-033 | 3 | 3 |
| F-035 | 3 | 3 | F-036 | 3 | 0 |
| S-016 | 0 | 1 | **Total** | **31** | **20** |

The accepted Gate 5 review/decision and exact source enforce
`fixtures_with_uncalibrated_mutations=0`, `mutation_calibration=calibrated`,
`candidate_status=blocked`, `gate5_authorized=false`, and O15 disabled/deferred. The
revision preserves these values and does not authorize republishing them.

### 9.2 T7 live evidence

The source-derived obligation set is exactly 51 across 15 fixtures. Zero blocked
fixtures is a valid **conditional expected outcome** only if all 51 new M/H obligations
pass with current policy/profile/parity/independence evidence.

The total `302` is not independently derivable as “302 live results” from the plan.
What is derivable is one of:

- composite closure: 251 frozen references + 51 new live results = 302; or
- full rerun: 302 new live results.

The revision specifies the 51-run behavior but uses the full-rerun wording. M-6 must
resolve the choice before `result_count=302` is an executable invariant.

### 9.3 T8 P1 evidence

The accepted addendum derives:

- selected fixtures: F-037 + F-038 = **2**;
- baseline required grader rows: F-037 D/T/R/M/H = **5**;
- baseline required grader rows: F-038 D/T/R/M/H/P = **6**;
- total baseline grader rows: `5 + 6 =` **11**;
- semantic mutation cases named by the plan: `4 + 3 =` **7**;
- at two repetitions: at least **14 mutation executions**, plus repeated known-good/
  known-bad controls and activation records.

Therefore `0 → 11` is source-derived only as the baseline grader-result count. The
complete activation-evidence cardinality is not derivable until M-5 defines the exact
mutation, repetition, calibration, applicability, and activation record sets.

## 10. Practicality and proportionality

The required corrections are plan-level and bounded. Flattening a catalogue and adding
stage-specific schemas/loaders prevents large implementation rework. Splitting T1
removes a circular approval gate while retaining Stephen's policy authority. Making
calibration and live-evidence identities explicit adds no provider family, cloud
service, research compute, migration, or cryptographic-principal requirement.

No control proposed here weakens D-G5-1(a), D-G5-2/O15, G5.3-B(a), S-016,
`candidate_status=blocked`, or `gate5_authorized=false`.

## 11. Exact dispatch condition set

WP6.1/WP6.2 dispatch-plan approval remains prohibited until all conditions below hold:

1. M-1 is resolved through an explicit non-circular T1a/T1b (or evidence-equivalent)
   DAG, and Stephen records D-G6-2 for the exact policy and exact downstream edge.
2. M-2 is resolved by a literal one-row-per-command/transition W2/W8 catalogue whose
   expected set is independent of implementation registrations.
3. M-5 is resolved by an exact atomic P1 activation closure that includes calibration,
   mutations, repeats, applicability authority, and activation records—not only eleven
   baseline grader rows.
4. M-6 is resolved by an exact live-evidence composition, schema, stage loader, CLI
   dispatch rule, and invariant table. Frozen fake keys remain byte/identity immutable
   and are never relabelled.
5. Every producing-seam negative in the binding audit is implemented, including
   missing/duplicate/extra/stale/incompatible/conflicting and atomic no-side-effect
   cases.
6. The exact corrected revision preserves the frozen Gate 5 40/15/0/302/calibrated
   surface, candidate `blocked`, `gate5_authorized=false`, D-G5-1(a), O15 disabled/
   deferred, G5.3-B(a), and S-016 requirement-preserving outage behavior.
7. Stephen approves the corrected D-G6-3 invariant tables, evaluated profile grades,
   and WP6.1 operator-usability disposition at their stated gates.
8. A fresh independent review of the corrected exact commit finds no open Critical or
   Major item and closes every failed/partial binding row.
9. Only after that review does Stephen explicitly approve that exact reviewed commit.

This review does not approve or dispatch WP6.1 or WP6.2. Even after technical closure,
the exact reviewed commit is eligible only for Stephen's explicit approval.

## 12. Change log and verification evidence

**Repository files changed by this review:** this report only. The reviewed `132d`
checkout, all four primary plans, source, schemas, fixtures, tests, control store, and
vault remained unchanged. The repository-mandated task observer separately appended
Observation 47 to the external global skill-observation log; it is not a repository or
review artifact.

**Read-only verification performed:** exact HEAD/branch/status/diff checks; full primary
file reads from `45d29dd...`; direct governing-spec/source/schema inspection; remediation
diff inspection; and static production-loader derivation of 40 selected fixtures,
132 baseline keys, 46 selected variant rows, 170 variant keys, 302 total keys, 31 M,
20 H, and 15 affected fixtures.

No live provider call, research computation, fixture calibration, state migration,
owner decision, pilot action, or vault write was performed. No software-test result was
used as a substitute for the missing plan contracts.
