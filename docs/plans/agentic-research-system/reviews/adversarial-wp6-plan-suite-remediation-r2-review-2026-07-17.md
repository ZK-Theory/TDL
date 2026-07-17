# Adversarial Re-review — Revised ARS WP6 Plan Suite (R2)

**Review date:** 2026-07-17  
**Verdict:** `rework_required` — the exact revision is not dispatchable  
**Exact reviewed commit:** `79f6b1bfb28a02d6a06d5a4a350bfa7262ec6461`  
**Expected parent:** `45d29dd16cc5e654eb0be086d81eda9771711f11` — verified  
**Reviewed branch:** `codex/wp6-plan-suite-review-remediation`  
**Reviewer context:** fresh independent Codex task; planning review only

## 1. Exact commit and checkout verification

The task's writable checkout was not the review target: it was clean and detached at
`408f52bb57e13c6c95c21ff17d4eba979d63943d`. It was not switched because the detached
commit did not equal the required branch tip. Review reads and validation were instead
anchored to the existing read-only target checkout
`C:/Users/steph/.codex/worktrees/132d/TDL` and to Git objects:

- `git rev-parse HEAD` returned exactly
  `79f6b1bfb28a02d6a06d5a4a350bfa7262ec6461`;
- `git symbolic-ref --short HEAD` returned
  `codex/wp6-plan-suite-review-remediation`;
- `git status --short --branch` returned only the branch header;
- unstaged and staged name-only diffs were empty;
- `git cat-file -t HEAD` returned `commit`;
- `git rev-parse HEAD^` returned the expected parent
  `45d29dd16cc5e654eb0be086d81eda9771711f11`.

All five primary files were read in full from the exact commit. Governing W2, W4, W6,
W7, W8, the F-031–F-038 addendum, Gate 5 plans and decisions, current schemas,
calibration code, coverage loader, variant producer, CLI, and relevant tests were checked
directly at the same commit.

The two supplied external worktree paths were absent. Their exact source blobs were
nevertheless recoverable from repository history:

- preceding review: commit `80cc5f2b1103357fcd61bb51a1ee10f8112f5ad5`, blob
  `b962ed11813ff0a0164a0f8be3eef7e926757e5e` — exactly the expected hash;
- original review: commit `db25857c556167d1e6df4c5687bf8e8809902094`, blob
  `c46cf161f4d8ba79bda77ec12a0958e28294477a`.

## 2. Independence and authority boundary

This review did not use the remediation author's reasoning, conclusions, or transcript.
The prior reviews supplied attack conditions only; every disposition below was
re-derived from direct source at the exact target commit.

Stephen's P-035 choices are preserved where evidence supports them. The staged
`T1a → T2 → T3/T4 → T1b → T5 → T6 → T7 → T8` sequence is no longer circular, and the
`251 foundation_release references + 51 live_capability results = 302` composition is
numerically correct. Findings below refine the evidence contracts needed to enact those
choices; none authorizes a replacement owner decision.

This report authorizes no implementation, live provider call, research computation,
canonical-state mutation, vault change, migration, pilot, M/H eligibility transition,
claim transition, or WP6 dispatch. Model/context independence is not independent human
authority. Stephen retains every reserved decision.

## 3. Executive verdict

The revision closes important structural defects:

- the T1a/T1b graph is consistent across the header, tasks, DAG, branches, stops,
  decision register, master plan, and exit checklist;
- the W2/W8 annex really contains 104 unique normalized rows, including all 13 W8
  commands, and its raw canonical SHA-256 is correct;
- the P1 arithmetic is internally `11 + 43 = 54` and the requested one-at-a-time
  negative classes are named;
- Gate 5 independently derives to `40` fixtures, `132` baseline positions, `46` variant
  rows, `170` variant positions, `302` total positions, `31 M + 20 H = 51` unavailable,
  `251` otherwise available, and `15` affected fixtures;
- C-1, M-3, M-4, M-7, and the original m-1 remain closed.

Seven Major defects remain. The catalogue omits exact runtime command identity and can
double-credit shared bindings; T1b has no human-calibration evidence producer; P1 uses
non-canonical shorthand keys and lacks an independent expected-set owner; the claimed
51-row predecessor/replacement map is absent; and `live_capability` is assigned to a
W6 `gate_stage` whose accepted enumeration prohibits it. These are acceptance-contract
defects, not editorial gaps. The exact commit is therefore `rework_required`.

No Critical finding was found.

## 4. Major findings

### R2-M1 — Major — T1b has no explicit human-grader calibration producer

1. **ID/severity:** R2-M1, Major.
2. **Precise claim:** T1b's specified empirical path can calibrate model graders through
   Claude/Codex, but it defines no separate human-calibration evidence closure before
   the same T1b hash unblocks every H transition.
3. **Direct evidence:** 06b T1a/T1b covers grader classes but specifies empirical
   execution through T2 and the T3/T4 provider transports
   (`implementation/06b-wp6-2-live-capability-plan.md:46-57,83-91`). T7 then distinguishes
   real model graders for M from named human authority for H (`:119-132`), and the exact
   table contains 20 H obligations (`:327-344`). W6 separately requires blinded model
   examples and recorded human disagreements/rubric revision
   (`design/06-evaluation-observability-and-audit.md:315-327`). The current threshold
   registry deliberately omits both M/H thresholds
   (`.research-system/evals/threshold-policies.yaml:4-13`), and calibration blocks either
   live class (`research_system/evals/calibration.py:145-164`).
4. **Concrete failure scenario:** T1b runs only Claude/Codex blinded cases, publishes a
   complete-looking model policy, and is accepted. The same hash unblocks 20 H rows even
   though no human rubric/version, blinded case set, disagreement, adjudication, or
   authority evidence was required. A stricter implementer instead stops permanently
   because no admissible H producer exists.
5. **Impact:** Invalid H eligibility can enter the 302 closure, or the staged lifecycle
   becomes non-executable at T1b/T7.
6. **Disposition:** fix before T1b dispatch; refine, not reverse, P-035.
7. **Exact proposed change:** define T1b as the exact non-compensable union of
   `T1b-M` (Claude/Codex provider/model/adapter/command/receipt/grant/lease/context/result
   evidence) and `T1b-H` (rubric/version, exact blinded positive/negative/ambiguous/
   producer-correlated cases, attributed authority/context, disagreements, rubric
   revision/adjudication, results, and evidence). Accept the composite T1b hash only
   when both required sets close; otherwise keep the unsupported class ineligible.
8. **Affected decisions/work packages:** P-029, P-033, P-035, D-G6-2; W6 §§13/27;
   WP6.2 T1a/T1b/T6/T7; Gate 6 M/H eligibility.

### R2-M2 — Major — the catalogue does not bind exact runtime `command_type`

1. **ID/severity:** R2-M2, Major.
2. **Precise claim:** Each annex row names a schema-path shorthand but not the exact
   versioned `command_type` used by the W2 envelope, authority grants, dispatcher,
   events/receipts, and idempotency identity. Alias rejection is therefore untestable.
3. **Direct evidence:** The annex defines `cmd/x` only as a filesystem path and has no
   `command_type` column (`implementation/06d-wp6-1-owner-source-catalogue.md:14-17,
   52,107,156`), despite promising alias rejection (`:7-10,153-154`). W2 makes
   `command_type` a versioned imperative name and part of the idempotency tuple
   (`design/02-task-event-and-artifact-schema.md:229-251,547-557`). The generic schema
   accepts any non-empty string (`.research-system/schemas/core/command.schema.json:5-10`),
   authority compares exact strings (`research_system/authority.py:1033-1041`), and the
   current dispatcher uses PascalCase names (`research_system/command/service.py:831-872`)
   while W8 owns lowercase snake-case tokens (`design/08-resource-checkpoint-and-
   operations.md:359-377`).
4. **Concrete failure scenario:** `operator.request_pause` retains the expected key,
   schema, event, reducer, receipt, and tests but executes as `PauseAttempt` or
   `RequestPause`. The catalogue comparison passes while the accepted grant vocabulary
   does not govern the runtime command, or an alias grant creates a second authority
   surface.
5. **Impact:** Authority and idempotency scope can diverge from the accepted catalogue;
   WP6.1 can claim exact closure under the wrong command identity.
6. **Disposition:** fix before D-G6-3 approval or WP6.1 dispatch.
7. **Exact proposed change:** add exact `command_type` to every row; constrain it with
   `const` in the command-specific schema; require the authority grant, dispatcher,
   event, receipt, and idempotency tuple to use the identical value. Either adopt W8's
   owner tokens directly or record an owner-approved one-to-one mapping. Add an alias
   mutation that changes only `command_type` and must reject before publication.
8. **Affected decisions/work packages:** P-003, P-006, P-020, P-030, D-G6-3; 06a
   T1–T6/T8; WP6.1; Gate A A4/A5.

### R2-M3 — Major — component-set comparisons permit duplicate bindings and missing row effects

1. **ID/severity:** R2-M3, Major.
2. **Precise claim:** The validator compares component sets independently rather than
   complete row bindings one-to-one. Unique logical keys can therefore double-credit
   one implementation while a row-specific discriminator, transition, reducer, or
   projection is missing.
3. **Direct evidence:** Annex §5 specifies separate comparisons with schemas, events,
   reducers, projections, authority rules, receipts, and tests
   (`implementation/06d-wp6-1-owner-source-catalogue.md:172-189`). Sharing is extensive:
   `task.claim_start` and `dispatch.claim` share `cmd/claim_dispatch`/`DispatchClaimed`
   but only the former requires Task reduction/projection (`:65,79`); ten message rows
   share one command/event/reducer with distinct discriminants (`:109-118`); lease and
   operator rows share another binding (`:86,159`); `correction.record` says only
   “affected projections” (`:149`). The pinned implementation's `ClaimDispatch` emits
   only `DispatchClaimed` (`research_system/command/service.py:841-843`) and replay
   updates only the dispatch stream (`research_system/projection/replay.py:177-196`).
4. **Concrete failure scenario:** Two expected keys point to the same ClaimDispatch
   binding. Global schema/event/reducer/projection sets are complete because `reduce_task`
   appears elsewhere, and two test names alias one callable. The exact-set check passes
   although claim never moves Task `ready → in_progress`. Ten message rows can similarly
   exercise only `assignment`.
5. **Impact:** A materially incomplete W2 lifecycle can claim 104-row closure and clear
   A4/A5.
6. **Disposition:** fix before WP6.1 dispatch.
7. **Exact proposed change:** compare a multiset of complete binding records containing
   logical key, exact command type, schema/event IDs and hashes, discriminator, exact
   from/to edge, ordered event set, reducer set, projection set or typed selector,
   authority/receipt identities, and positive/negative test identities. Shared callable
   groups may reuse code but must retain per-row cardinality and effects. Add mutations
   for duplicate binding, swapped keys, aliased tests, removed reducer/projection, and
   changed message discriminant.
8. **Affected decisions/work packages:** P-006, P-008–P-013, P-020, P-030, D-G6-3;
   06a T1–T6/T8; WP6.1 review/merge; Gate A A4/A5.

### R2-M4 — Major — the eleven P1 “literal keys” are not canonical result keys

1. **ID/severity:** R2-M4, Major.
2. **Precise claim:** Labels such as `F-037.baseline.D` omit fixture revision, grader
   ID/version, and the canonical variant position, so they are not the exact grader-result
   keys the plan claims to close.
3. **Direct evidence:** 06b lists eleven class-only labels and calls them literal keys
   (`implementation/06b-wp6-2-live-capability-plan.md:201-213`). The implemented exact
   closure key is the six-tuple `(fixture_id, fixture_revision, grader_id, grader_class,
   grader_version, variant_id)` (`research_system/evals/models.py:358-368`), and the
   owning coverage schema enforces six fields
   (`.research-system/schemas/evals/coverage-manifest.schema.json:61-68`).
4. **Concrete failure scenario:** A stale grader version or a second same-class grader
   is bound behind the same shorthand label. The eleven-label equality and result ID/hash
   presence still pass.
5. **Impact:** M-5's baseline exact set cannot detect stale, aliased, or substituted
   grader identities before pilot evidence or claim promotion.
6. **Disposition:** fix before T8 dispatch.
7. **Exact proposed change:** replace all eleven labels with literal six-field canonical
   tuples, plus the observed result ID/hash, and derive their expected side from a
   content-addressed accepted contract.
8. **Affected decisions/work packages:** P-019, P-029, P-033, D-G6-3; W5/W6; WP6.2
   T8; pilot-evidence and claim-promotion commands.

### R2-M5 — Major — T8 does not separate expected and observed 54-referent producers

1. **ID/severity:** R2-M5, Major.
2. **Precise claim:** The consumer command “declares” the complete sorted 54 set, but no
   independent accepted object is named as the exclusive expected-side producer.
3. **Direct evidence:** The 54-referent command and negatives are specified at
   `implementation/06b-wp6-2-live-capability-plan.md:246-255`, and the future baseline
   test asserts all keys/hashes (`:385-387`). In contrast, WP6.1 explicitly makes its
   accepted annex the expected source and runtime registrations comparison-only
   (`implementation/06a-wp6-1-runtime-task-lifecycle-plan.md:132-139`). No equivalent
   P1 activation-contract object or expected-side derivation is named.
4. **Concrete failure scenario:** A manifest/command builder derives both expected and
   observed sets from the same loaded activation evidence. One mutation/repetition is
   omitted from the producer; it disappears from both sets and strict equality passes.
5. **Impact:** A superficially exact validator can certify the P1 evidence producer
   against itself, allowing incomplete calibration/activation into pilot or claim gates.
6. **Disposition:** fix before T8 dispatch.
7. **Exact proposed change:** add a content-addressed P1 activation-contract object whose
   accepted logical keys, cases, repetitions, summaries, policy/applicability, calibration,
   and activation obligations exclusively produce the expected set. Derive observed
   IDs/hashes only from ledger/execution records. Add producing-seam omissions before
   observation, not only manifest-dictionary mutations.
8. **Affected decisions/work packages:** P-019, P-029, P-033, D-G6-3; WP6.2 T8;
   F-037/F-038 activation; pilot and claim consumers.

### R2-M6 — Major — the claimed literal 51-row predecessor/replacement map is absent

1. **ID/severity:** R2-M6, Major.
2. **Precise claim:** The plan says expected keys come from “the plan's replacement map”
   but supplies only fixture-level M/H counts, not 51 predecessor-to-successor identities.
3. **Direct evidence:** 06b defines predecessor fields and says the expected 251/51 key
   sets come from frozen coverage and the plan's map
   (`implementation/06b-wp6-2-live-capability-plan.md:295-302`). The only following map
   is a 15-row table of counts (`:327-344`). The source-derived predecessor identities
   are six-field keys including fixture/grader revision and variant identity
   (`research_system/evals/models.py:358-368`).
4. **Concrete failure scenario:** An implementation invents successor variant IDs or
   derives expected and observed successors from the live manifest. Counts, uniqueness,
   and a locally constructed bijection all pass while one frozen obligation is replaced
   by an unrelated live result.
5. **Impact:** M-6 remains count-correct but provenance-underdetermined; relabelled or
   substituted evidence can enter the composite.
6. **Disposition:** fix before T7 dispatch.
7. **Exact proposed change:** add a content-addressed literal 51-row map with each frozen
   predecessor six-tuple, exact successor-key construction, replacement scope, expected
   provider/model/adapter class, and map hash. Derive expected keys only from that map
   and frozen accepted coverage, never the live manifest.
8. **Affected decisions/work packages:** P-018, P-030, P-035, D-G6-3; WP6.2 T7/T8;
   live schema, loader, CLI, and invariant smoke.

### R2-M7 — Major — `live_capability` is prohibited by the owning `gate_stage` contract

1. **ID/severity:** R2-M7, Major.
2. **Precise claim:** The new manifest declares `gate_stage: live_capability`, but W6
   owns a closed enumeration that does not contain that value and requires a versioned
   W6 amendment for aliases/additions.
3. **Direct evidence:** 06b assigns `gate_stage: live_capability`
   (`implementation/06b-wp6-2-live-capability-plan.md:280-284`). W6 permits only
   `interface_review`, `p0_materialization`, `foundation_release`, and `pilot_promotion`
   (`design/06-evaluation-observability-and-audit.md:532-541`), P-030 records the same
   owner rule (`03-decisions-and-open-questions.md:357-370`), and the current coverage
   schema enforces it (`.research-system/schemas/evals/coverage-manifest.schema.json:
   27-31`). P-035 accepts lifecycle composition, not a W6 stage-version amendment
   (`03-decisions-and-open-questions.md:430-470`).
4. **Concrete failure scenario:** The new stage loader rejects the manifest under the
   accepted W6 schema, or silently widens the enum while existing coverage/fixture
   consumers retain the old vocabulary.
5. **Impact:** The plan creates a cross-schema lifecycle inconsistency and a
   non-portable CLI boundary; T7 cannot satisfy both its own plan and accepted W6.
6. **Disposition:** fix before T7 dispatch.
7. **Exact proposed change:** retain a valid W6 `gate_stage` and add a separate typed
   `evidence_stage: live_capability`, or record an explicit versioned W6 amendment and
   update every owner schema, manifest, mapping, loader, and test together.
8. **Affected decisions/work packages:** P-025, P-030, P-035; W6; WP6.2 T7; live
   manifest schema, loader/CLI, and Gate 6 evidence composition.

## 5. Minor and editorial findings

### R2-m1 — Minor — P-035's review citation is not portable from the audited commit

1. **ID/severity:** R2-m1, Minor.
2. **Precise claim:** P-035 cites its evidence through an absolute foreign-worktree path
   and blob hash, but the review is absent from the audited commit tree.
3. **Direct evidence:** `03-decisions-and-open-questions.md:455-459` cites
   `C:/Users/steph/.codex/worktrees/4d28/...`. The cited blob is reachable locally only
   through historical commit `80cc5f2b...` at the canonical repository review path;
   `git show 79f6b1b:<review-path>` fails because the path is not in the target tree.
4. **Concrete failure scenario:** A fresh shallow clone of the audited branch can read
   P-035 but cannot retrieve the review that supplied its M-1/M-6 decision evidence.
5. **Impact:** Decision provenance is not self-contained; decision substance is
   unchanged.
6. **Disposition:** correct as provenance metadata in the remediation revision.
7. **Exact proposed change:** commit the preceding review at its canonical repo-relative
   path and cite that path, containing commit, and blob hash; remove the absolute
   worktree path.
8. **Affected decisions/work packages:** P-035, D-G6-2/D-G6-3; WP6 master and WP6.2.

No additional editorial-only issue warrants a finding.

## 6. Disposition of all previous findings

| Previous finding | R2 disposition | Independent basis |
|---|---|---|
| C-1 secret/cost pre-issue | **closed** | T2 binds `SecretReference`/`CostGrant`; sentinels cover context, generated adapter, payload, argv/config, event, receipt, object, and fixture/evidence producers before invocation; replay/concurrency are explicit (`06b:58-82,166-192`). |
| M-1 staged lifecycle | **structural defect closed; evidence closure still Major R2-M1** | All restatements reproduce T1a→T2→T3/T4→T1b→T5→T6→T7→T8 (`03-decisions:435-442`; master `:79-81,192-195,207,280-285`; 06b `:6-8,46-91,143-164,392-413`). Human calibration remains unproduced. |
| M-2 literal W2/W8 catalogue | **partial; open through R2-M2/R2-M3** | 104 unique rows, 13 W8 rows, correct hash, legal state expansion, and runtime-independent expected prose are real. Exact command identity and one-to-one complete binding comparison are absent. |
| M-3 execution-bound live parity | **closed** | T5 binds canonical applicability, rendered payload, actual command/receipt, grant/lease, and observed enforcement; actual adapter/transport seam perturbation is required (`06b:92-100`). |
| M-4 W4 profile eligibility | **closed** | T6 reproduces W4 §10.2/§10.3 fields, outcome classes, omissions, thresholds, currentness, suspension, approval, one-field negatives, and actual-attempt independence (`06b:101-118`). |
| M-5 complete P1 activation | **arithmetic/negative list improved; open through R2-M4/R2-M5** | The 43 activation referents and 54 union add correctly, and requested negative classes are present, but baseline identities are not canonical and expected/observed producers can collapse. |
| M-6 composite live evidence | **composition choice/counts closed; enforceability open through R2-M6/R2-M7** | 251+51=302 and the binding inventory are correct; the literal 51 map is missing and the proposed `gate_stage` is illegal. |
| M-7 migration path/writer exclusivity | **closed** | Legacy backlog, ARS generated namespace, annotation inbox, and optional aggregate are disjoint; writer registry, collision, rebuild, and one-way cutover tests remain mandatory (`master:127-159`; P-032 `:398-407`). |
| m-1 decision-register integrity | **closed; new provenance Minor R2-m1** | P-031–P-035 carry status, evidence, migration consequence, affected specs, and boundaries. P-035's evidence locator is not portable. |

## 7. Invariant → enforcement → test matrix

| Invariant | Owning authority / expected source | Planned enforcement | Binding test or negative | R2 status |
|---|---|---|---|---|
| No credential material reaches any pre-issue or canonical surface | W1 §9.6; W7 §§9/21 | T2 sentinel boundary; independent Claude/Codex canaries | one sentinel per producer seam; zero invocation and canonical side effects | **holds at plan level** |
| Live spend is atomically bounded | W7 command; W8 grant | identity-bound `CostGrant` reservation before issue | missing/wrong/zero/exhausted/stale/mismatched/concurrent/replay | **holds at plan level** |
| One executable WP6.2 DAG | P-035; D-G6-2 | exact T1a/T1b serial graph | restatement equality + no pre-T2 live call | **partial** — graph holds, H producer absent |
| Exact W2/W8 lifecycle | W2 §§10–19; W8 §20; annex blob | future 104-row catalogue comparison | exact set, illegal edge, one-field, atomic negatives | **fails** — R2-M2/R2-M3 |
| Live parity proves observed enforcement | W7 §§9–10/17 | typed live parity row | actual post-render adapter/transport perturbation | **holds at plan level** |
| Profile eligibility derives from complete current evidence | W4 §§10.2–10.3 | strict profile and recomputation | missing/stale/duplicate/incompatible/omitted/self-attested/unapproved | **holds at plan level** |
| Eleven P1 baseline results are exact | W6 addendum + accepted activation contract | P1 stage manifest | canonical tuple equality + stale grader/version negatives | **fails** — R2-M4 |
| P1 activation is exact 43 and consumed with baseline as 54 | accepted P1 activation contract | atomic single-writer consumer | all requested one-at-a-time negatives and producing-seam omission | **fails** — expected source absent, R2-M5 |
| T7 composition is exactly 251 frozen + 51 live | frozen coverage + literal replacement map | versioned live manifest and bijection | wrong provider/model/adapter/lifecycle, missing/extra/duplicate/broken map | **fails** — literal map absent, R2-M6 |
| Lifecycle vocabulary obeys W6 | W6/P-030 closed `gate_stage` enum | schema and stage loader | reject unknown stage; cross-boundary CLI negatives | **fails** — R2-M7 |
| Frozen Gate 5 remains immutable | accepted Gate 5 artifacts | separate new evidence; byte assertions | unchanged 40/15/0/calibrated/302, blocked, false, O15 deferred | **holds** |
| Provider outage preserves requirements | S-016; W4 §17 | wait/block/`unable_to_grade` | no lower-grade substitute/provider issue | **holds** |
| Legacy and successor writers never share a mutable path | P-004/P-021/P-032/P-034 | path/writer registry and one-way cutover | collision, mutation, deletion/rebuild, cutover | **holds at plan level** |
| Decision register is auditable | register protocol | explicit fields per P-031–P-035 | field completeness + source reachability | **partial** — R2-m1 only |

## 8. Binding-test bypass audit

Green hooks or the reported “98 contract gates passed” are not credited beyond the
checks they actually define. The WP6 contracts below are prospective; no current test
can substitute for a missing expected source or identity.

| Claim/check | Expected side | Observed side | Same-source bypass? | Disposition |
|---|---|---|---|---|
| 104-row catalogue key count/hash | accepted annex blob | parsed annex/runtime catalogue | **No** for key/hash count | Count/hash holds. |
| Catalogue component completeness | annex component columns | runtime schemas/events/reducers/projections/tests | **Yes** if compared as independent sets | R2-M2/R2-M3: require complete one-to-one records and exact command type. |
| Legal closed state expansion | literal annex class sets | concrete implementation edges | **No** if annex alone expands expected side | Expansion is 182 legal concrete edges; retain annex-only derivation. |
| Eleven baseline keys | class-only plan labels | P1 manifest results | **Yes / aliasable** | R2-M4: use canonical six-tuples from an accepted contract. |
| 43 activation referents / 54 union | currently command/manifest declaration | same loaded evidence objects | **Yes** | R2-M5: separate accepted expected contract from ledger/execution observations. |
| P1 one-at-a-time negatives | named plan list | validator rejection | **Potentially** if only output dictionaries mutate | Perturb the public producer seam before observation and assert all state sets unchanged. |
| 51 predecessor/replacement bijection | frozen coverage plus absent “plan map” | live manifest map | **Yes** for successor construction | R2-M6: commit literal 51-row map. |
| 251 frozen references | accepted Gate 5 result identities | composite manifest references | **No** if hashes/identities are reverified from frozen artifact | Keep; reject relabelling and changed lifecycle. |
| Stage routing boundary | W6 enum + stage-specific schema | CLI argument/manifest | **No**, but planned value is invalid | R2-M7: separate `evidence_stage` or amend W6 explicitly. |
| Frozen Gate 5 values | accepted coverage/decision bytes | pre/post target bytes and derived counts | **No** | Holds; lifecycle-scoped new evidence stays separate. |

## 9. Independent count and hash derivations

### 9.1 W2/W8 annex

Raw Git blob evidence for
`implementation/06d-wp6-1-owner-source-catalogue.md`:

| Quantity | Value |
|---|---:|
| Git blob | `5ba1374cd7990810feb454a245055bc428dfc4f2` |
| bytes | 32,313 |
| LF / CRLF / bare CR | 189 / 0 / 0 |
| SHA-256 | `43a689c01b2041d11d67daa790e3b97b51471c7000ca28393c77d3d77df4d14c` |
| normalized rows | 104 |
| unique keys | 104 |
| W8 operator rows | 13 |
| duplicate keys | 0 |

The exact target worktree's on-disk file is also 32,313 bytes, LF-only, and has the same
SHA-256. Row groups are `50 + 41 + 13 = 104`; literal state-class expansion yields 182
concrete edges without illegal suspension self-transitions.

### 9.2 Frozen Gate 5 and T7 composition

A read-only production-loader derivation from the exact target checkout, with bytecode
writes disabled, returned:

| Quantity | Independent derivation | Value |
|---|---|---:|
| selected fixture revisions | P0 coverage exact set | 40 |
| baseline result positions | sum selected fixture grader rows | 132 |
| selected Gate 5 variant rows | `load_gate5_variant_rows` | 46 |
| variant result positions | sum grader rows over selected variants | 170 |
| total positions | `132 + 170` | 302 |
| unavailable M | exact M positions | 31 |
| unavailable H | exact H positions | 20 |
| unavailable total | `31 + 20` | 51 |
| otherwise available | `302 - 51` | 251 |
| affected fixtures | own at least one M/H position | 15 |

The by-fixture distribution exactly matches 06b:327-344. Therefore P-035's chosen
composition is arithmetically valid. R2-M6 concerns the missing identity map, not the
counts or the owner-selected composition.

### 9.3 P1 activation

The plan's proposed cardinalities are internally consistent:

- baseline grader rows: `5 + 6 = 11`;
- fixture revisions: 2;
- mutations: `4 + 3 = 7`;
- known-good identities: 2;
- safe-variation identities: 2;
- case/repetition executions: `11 × 2 = 22`;
- error summaries: 2;
- T1b policy: 1;
- F-038 applicability: 1;
- calibration records: 2;
- activation records: 2;
- activation closure: `2 + 7 + 2 + 2 + 22 + 2 + 1 + 1 + 2 + 2 = 43`;
- atomic union: `11 + 43 = 54`.

R2-M4/R2-M5 concern canonical identities and producer independence, not arithmetic.

## 10. Decision audit

| Decision | Disposition | Reason |
|---|---|---|
| P-031 | **keep** | SCALE-01 changes only pilot occupant; all preflight and first-paper promotion criteria remain. |
| P-032 | **keep** | Path-level legacy/successor/annotation separation and whole-path cutover now preserve P-004/P-021. |
| P-033 | **keep, with R2-M1 evidence clarification** | No degraded R2 path is opened. Human and model live evidence need separate exact producers before the common gate can clear. |
| P-034 | **keep** | Per-item authority transition and final path cutover remain explicit; no migration is authorized here. |
| P-035 sequencing | **keep** | The staged graph is coherent and non-circular. R2-M1 refines T1b's internal evidence branches. |
| P-035 251+51 composition | **keep** | Counts re-derive exactly. R2-M6 requires the literal identity map; R2-M7 corrects an unapproved stage label. |
| D-G6-2 | **open at its stated future hashes** | T1a and composite T1b evidence still require independent review and Stephen acceptance. |
| D-G6-3 | **not approvable at this revision** | Seven Major binding defects prevent literal invariant approval. |
| D-G6-4 / D-G6-5 | **deferred at declared gates** | No migration batch or Gate 6 pilot acceptance follows from this plan review. |

The P-035 owner choices are not superseded. If Stephen chooses to let model-only T1b
evidence unblock H, that would require an explicit superseding decision identifying the
contrary W6 basis, the accepted human-evidence substitute, and its failure controls.

## 11. Practicality and proportionality

The required corrections are bounded plan work:

- adding `command_type` and converting the annex validator to complete row records is a
  mechanical extension of the existing 104 rows/182 expanded edges;
- a literal 51-row replacement map is finite and can be generated once from frozen
  accepted keys, then reviewed and content-addressed;
- an accepted P1 activation contract reuses the already enumerated 54 obligations;
- separating `gate_stage` from `evidence_stage` is smaller than silently widening every
  W6 consumer;
- human calibration adds work proportional to the 20 H obligations and is necessary
  because W6 makes H non-compensable.

None of these changes adds a provider family, cloud service, research computation,
migration, or autonomous authority. The smallest safe remediation is to strengthen the
plan contracts before implementation, where the cost is far lower than repairing
identity/provenance drift after live evidence exists.

## 12. Residual risks after required changes

- T1a protocol adequacy, T1b-M statistical evidence, and T1b-H human rubric/disagreement
  evidence remain empirical owner-review questions; software closure cannot decide them.
- Specific initial model profiles and claimed capability grades remain future evidence,
  not accepted facts.
- The stage-aware loader/CLI and new schemas do not yet exist; implementation review must
  verify public producing seams and exact cross-boundary rejection.
- W11 is still a future specification and must independently prove path/writer registry,
  annotation ingestion, rebuild, collision, and one-way cutover behavior.
- The frozen Gate 5 surface must be reverified at every later exact commit; validation
  belongs to a commit, not a branch name.

## 13. Exact dispatch condition set

WP6.1/WP6.2 dispatch remains prohibited until all conditions below hold:

1. R2-M1 closes with exact non-compensable T1b-M and T1b-H expected sets, producers,
   evidence identities, review, and composite owner acceptance.
2. R2-M2/R2-M3 close with exact `command_type` and one-to-one complete binding records
   for all 104 catalogue rows/182 concrete edges, including duplicate/alias/effect-loss
   negatives.
3. R2-M4/R2-M5 close with canonical six-field baseline keys and a content-addressed P1
   activation contract independent of observed ledger/execution evidence.
4. R2-M6 closes with a content-addressed literal 51-row predecessor/replacement map and
   exact successor-key construction.
5. R2-M7 closes through a valid W6 stage plus separate evidence-stage field, or an
   explicit versioned W6 amendment propagated to every owner schema and consumer.
6. R2-m1's preceding-review evidence is available at a portable repository-relative
   path with commit and blob identity.
7. Every producing-seam negative in the binding audit is implemented; rejection leaves
   event tail, accepted-result set, activation set, Decision set, capability state, and
   claim set unchanged as applicable.
8. The corrected revision preserves frozen Gate 5 `40 / 15 / 0 / calibrated / 302`,
   candidate `blocked`, `gate5_authorized=false`, D-G5-1(a), O15 disabled/deferred,
   G5.3-B(a), and S-016 requirement-preserving outage behavior.
9. Stephen approves the corrected D-G6-3 tables, T1a/T1b hashes at their future gates,
   model-profile grades, and WP6.1 operator-usability disposition.
10. A fresh independent review of the corrected exact commit finds no open Critical or
    Major item and closes every failed/partial binding row.
11. Only after that review does Stephen explicitly approve that exact reviewed commit;
    only that commit may supply dispatch prompts.

## 14. Change log and verification evidence

**Repository files changed by this review:** this report only. No reviewed plan, design,
schema, source, test, fixture, coverage manifest, control-store artifact, or vault file
was modified.

**Read-only verification performed:**

- exact target HEAD/branch/status/staged/unstaged/type/parent checks;
- full reads of all five primary files from `79f6b1b...`;
- exact historical lookup and hash verification of both prior reviews;
- direct W2/W4/W6/W7/W8, Gate 5, schema, calibration, loader, variant, CLI, and test
  inspection;
- raw Git-blob and target-worktree byte/EOL/SHA-256 checks for 06d;
- independent catalogue row/uniqueness/W8/concrete-edge derivation;
- read-only exact-target production-loader derivation of 40, 132, 46, 170, 302, 31,
  20, 51, 251, and 15;
- independent P1 11/43/54 arithmetic and requested-negative audit;
- binding-test expected/observed producer tracing.

No live provider call, fixture calibration, research computation, migration, canonical
state mutation, owner decision, pilot action, or claim transition was performed. No
green test count was used as a substitute for a missing plan contract.
