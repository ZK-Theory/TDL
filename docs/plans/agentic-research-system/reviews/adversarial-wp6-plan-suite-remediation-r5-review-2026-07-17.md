# Adversarial WP6 plan-suite remediation R5 review

**Review date:** 2026-07-17  
**Reviewer posture:** fresh, independent, adversarial remediation re-review  
**Target repository:** `TDL`  
**Target state:** detached `HEAD`  
**Target commit:** `fe5f1d40bc8f05f061317c677b5891cea0711249`  
**Target parent:** `aa54fe140de8eff3dabe0472758c3514fa673b19`  
**Verdict:** `approved`  
**Finding count:** **0 Critical, 0 Major, 0 Minor**

## 1. Executive verdict

Commit `fe5f1d40bc8f05f061317c677b5891cea0711249` closes R4-M1,
R4-M2, and R4-m1 without regressing the earlier plan-suite closures. The strongest
adversarial attacks now fail for reasons fixed in independently accepted expected-side
contracts rather than because the attacks were omitted:

- `RuleEvaluation` has a distinct authority subject, proposed-record ID source, owner
  projection, reducer, and correction-selector target. Decision and RuleEvaluation
  grants/projections are expressly non-compensable, and candidate-manifest/runtime
  co-corruption is checked against the separately accepted manifest identity.
- `ClaimDispatch` first validates its Dispatch-scoped grant, then loads the accepted
  Dispatch revision before reusing that authority for the Task facet, idempotency
  lookup, version advancement, or position allocation. The payload Task ID/revision,
  stored Dispatch relation, two-stream versions/write set, and active lease subject must
  all agree.
- The R3 provenance report now distinguishes canonical Git-blob UTF-8/LF bytes from the
  Windows CRLF checkout surface, and the revised R3 plus preserved R4 report identities
  are pinned correctly.

No wording was found that permits an implementation to bypass those controls while
still satisfying the complete literal plan. No owner decision, runtime implementation,
live provider call, M/H eligibility transition, pilot evidence, claim promotion, or
Gate 6 dispatch is created by this review.

**Explicit answer:** **Yes.** Commit
`fe5f1d40bc8f05f061317c677b5891cea0711249` is safe to use as the Gate 6 launch
basis. “Safe to use as the basis” is not immediate execution authority: the future
catalogue/schema-identity manifests, the P1 descriptor-hash manifest, D-G6-2 evidence
gates, exact-revision owner approval, and later Gate 6 preflight gates remain mandatory.

## 2. Hard revision precondition and review scope

The authorized deterministic alignment command completed successfully:

```text
git switch --detach fe5f1d40bc8f05f061317c677b5891cea0711249
```

The pre-review verification then returned exact `HEAD`
`fe5f1d40bc8f05f061317c677b5891cea0711249` and empty
`git status --porcelain=v1`. The parent independently resolved to
`aa54fe140de8eff3dabe0472758c3514fa673b19`. The committed Git objects, not an
uncommitted filesystem variant, supplied the review authority.

The complete affected suite was read, including the master, 06a, 06b, 06d, 06e, 06f,
decision register, repository index, R3 report, and preserved R4 report. The prompt's
filenames `06e-wp6-1-contract-matrix.md` and `06f-wp6-1-activation-matrix.md` do not
exist at this commit. The committed canonical files are
`06e-wp6-2-live-replacement-map.md` and
`06f-wp6-2-p1-activation-contract.md`; these are also the paths used by the master,
06b, P-035, and the repository README and were the files reviewed.

Direct owner cross-checks covered accepted W2 §§8, 12, 13, 18, 19 and the W2 review
gate; W4 §§10.2–10.3; W6 §§13, 26–27; W8 §20; and the accepted Gate 5 objects. Earlier
reviews were treated as finding catalogues, not inherited proof.

## 3. Findings

There are no Critical, Major, or Minor findings. Consequently there is no finding for
which a violated invariant, exploit path, detection failure, or remediation is required.
The attack results and exact evidence supporting that conclusion follow.

## 4. R4-M1 — RuleEvaluation versus Decision

### 4.1 Authority, identity, selector, and projection separation

| Required property | Direct committed evidence | Result |
|---|---|---|
| Distinct authority subject | 06d `:122-124` maps `decision.*` to `decision` and `rule.evaluate` to `rule_evaluation`; 06d `:204-210` makes the records non-compensable | Pass |
| Distinct proposed-record ID source | 06d `:122-124` uses `payload.new_decision_id` versus `payload.new_rule_evaluation_id`; every row also inherits wrong-subject-kind/ID rejection at `:128-139` | Pass |
| Distinct reducer and owner projection | 06d `:303-310` uses `reduce_decision; decision` versus `reduce_rule_evaluation; rule_evaluation, governance` | Pass |
| Distinct correction selector | 06d `:181-198` maps `decision -> decision` and `rule_evaluation -> rule_evaluation`; runtime selector state is comparison input only at `:199-202` | Pass |
| Owning semantic agreement | Accepted W2 `design/02-task-event-and-artifact-schema.md:795-817` says only authorized `ResolveDecision` resolves a Decision and a mechanical RuleEvaluation is not automatically a Decision | Pass |

The lifecycle plan repeats the same non-compensation contract and tests at 06a
`:97-110`; the master makes it part of the machine-checkable closure at `:227-234`, the
forward obligation at `:264-270`, and the Gate 6 exit criterion at `:305-310`. P-035
records it as pending exact-revision owner approval rather than a silently accepted
decision at `03-decisions-and-open-questions.md:472-480`.

### 4.2 Adversarial mutation results

| Attack | Counterexample attempted | Why the literal plan rejects it |
|---|---|---|
| Cross-grant, Decision → RuleEvaluation | Use a valid Decision-scoped grant/ID with `RecordRuleEvaluation` | Subject kind and ID source disagree with 06d `:123`; N0/NA applies wrong kind/ID and authority-rule mutation to every row before version/state checks (`:50-65`, `:128-139`); explicit cross-substitution is required at `:204-210` and `:362-365` |
| Cross-grant, RuleEvaluation → Decision | Use a valid RuleEvaluation-scoped grant/ID with `ResolveDecision` | The inverse non-compensation rule is explicit at 06d `:204-210`; W2 `:795-817` independently reserves resolution to authorized Decision authority |
| Cross-projection | Route `RuleEvaluationRecorded` into Decision, or route `DecisionResolved` into RuleEvaluation | Complete-row comparison binds reducer and projection per logical row (`06d:44-49`, `:349-355`); the selector has distinct literal rows (`:181-198`); wrong projection/selector mutations are mandatory (`:357-365`) |
| Mismatched ID | Correct `rule_evaluation` subject kind with another RuleEvaluation ID, or correct `decision` kind with another Decision ID | The exact subject-ID source is part of every complete row (`06d:104-108`); wrong subject ID is universal and pre-state (`:128-139`) |
| Coordinated expected/runtime corruption | Change the candidate expected mapping and runtime selector together so both call RuleEvaluation a Decision | The accepted semantic manifest is independently produced/reviewed and accepted before runtime implementation (`06d:69-89`, `:199-210`). A coordinated candidate/runtime substitution still differs from the accepted manifest identity and must reject with both projections, governance index, event tail, and receipt acceptance unchanged (`:204-210`, `:363-365`) |

Neither authority can compensate for the other. The expected side is not generated from
the runtime registry, so exact equality cannot self-certify a correlated collapse.
R4-M1 is closed.

## 5. R4-M2 — ClaimDispatch relational authorization

### 5.1 Ordering and relational contract

Accepted W2 says a Dispatch binds one Task revision (`design/02-task-event-and-artifact-
schema.md:451-466`), a claim carries expected Dispatch and Task stream versions (`:479`),
every affected stream supplies an expected version (`:559-563`), and the atomic batch
declares its complete write set (`:565-569`).

The remediation now instantiates those rules at 06d `:141-173`:

1. The payload binds Dispatch ID/version, Task ID/revision/version, expected global
   position, and expected tail hash (`:143-147`).
2. The exact write set is the Dispatch and Task streams, and the exact ordered batch is
   `[DispatchClaimed, TaskClaimStarted]` (`:147-154`).
3. After validating the Dispatch-scoped grant, the service loads the accepted Dispatch
   revision before reusing that authority for the Task facet, idempotency lookup,
   version advancement, or position allocation (`:156-165`).
4. The stored Dispatch `(task_id, task_revision)` must equal the payload pair, and the
   active lease must bind that same Task revision and Dispatch (`:158-165`).
5. Both catalogue facets carry the relation and write set literally (`:227`, `:241`),
   and both must be present with the same ordered batch and effects (`:365-370`).

06a repeats the operational test contract at `:66-81` and the exact relational binding
at `:184-195`. The master hoists it into its assurance closure, forward obligation, and
exit checklist at `:227-234`, `:264-270`, and `:305-310`. P-035 repeats the stored
Dispatch/payload/lease equality and pre-reuse ordering at
`03-decisions-and-open-questions.md:476-479`.

### 5.2 Adversarial mutation results

| Attack | Counterexample attempted | Why the literal plan rejects it |
|---|---|---|
| Valid foreign current Task | Authorized Dispatch D1 binds T1@r1; submit current T2@r1 with its valid stream version | Stored Dispatch relation must equal the payload before reuse/publication (`06d:156-165`); the explicit current-foreign-Task mutation is required at `:167-173` and 06a `:76-80` |
| Stale Dispatch→Task relation | Payload and Task are current, but they no longer equal the Task revision frozen on the accepted Dispatch | Equality is to the loaded accepted Dispatch revision, not to a payload- or registry-supplied relation (`06d:156-165`); stale stored relation is an explicit negative (`:170-173`) |
| Wrong lease subject | Task/Dispatch relation is correct, but lease binds another Task revision or Dispatch | The active lease must bind both exact subjects (`06d:160-165`); wrong lease subject is explicit at `:170-173`, 06a `:77-80` |
| Coordinated valid-record substitution | Substitute valid current T2 and a valid lease for T2 while retaining authorized D1 | The T2/lease pair may be internally valid, but D1's stored T1 relation still fails exact equality. Substituting D2 as well under a D1 grant fails the exact Dispatch authority subject at 06d `:114`, `:128-139`; changing to an actually valid D2 grant/payload/lease is a legitimate D2 claim, not a bypass |
| Idempotency bypass | Pre-seed or reuse an idempotency result so a relationally invalid claim returns a prior receipt | Relation and lease checks precede idempotency lookup (`06d:156-165`); same-payload duplicate and conflicting-payload semantics remain explicit in 06a `:71-80` and the versioned idempotency identity remains bound at 06d `:91-100` |
| Version/position bypass | Supply valid member IDs but stale Task version, incomplete write set, wrong global tail, or Dispatch-only batch/receipt | Both versions, global position/tail, and exact write set are payload fields (`06d:143-154`); omission, staleness, race, extra/missing member, and Dispatch-only batch/receipt all reject atomically (`:167-173`, `:365-370`) |

The individual records cannot compensate for an invalid relation, and a complete set of
valid-looking records cannot bypass subject, stored-relation, lease, version, write-set,
or position equality. R4-M2 is closed.

## 6. R4-m1 — review provenance

R3 `reviews/adversarial-wp6-plan-suite-remediation-r3-review-2026-07-17.md:40-49`
now labels the first remediation report's digest as the canonical Git-blob UTF-8/LF
surface and separately labels its Windows CRLF checkout digest. Independent
reconstruction of blob `b962ed11813ff0a0164a0f8be3eef7e926757e5e` returned:

- canonical UTF-8/LF: 33,507 bytes, zero CR bytes, SHA-256
  `93a79b324a4ec2780496effb58f7b8b75c78b4ac10a9824bddc7a416a9011228`;
- Windows CRLF: 33,951 bytes, SHA-256
  `0ac3442376fc5d7ddc476b07e71cfc64003e6d4f4c992d0ccc234b7a87196973`.

The required current canonical reconstructions are:

| Artifact | Git blob | Canonical UTF-8/LF SHA-256 | Bytes / CR bytes |
|---|---|---|---:|
| `implementation/06d-wp6-1-owner-source-catalogue.md` | `5e2eb60ca4419d1529506de6859fb027cff518af` | `96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7` | 48,175 / 0 |
| R3 report | `69f140d95bbe33c39b3593833e9789ab409af9a9` | `b1a89411496bda995bef9b11211ed1f6078b90babd3bb46f79755e48316e4810` | 42,050 / 0 |
| R4 report | `66e82fdc9a014324c9e433cab431386bc6f8471e` | `87f226204475d51630ceeb71608d7a6d3fca135bdd68ef5a395c445df6d78a0a` | 26,671 / 0 |

Every corresponding pin reproduces:

- 06a `:147-150` pins the current 06d canonical SHA-256 exactly.
- The decision register `:498-504` pins the revised R3 path/blob/SHA and exact reviewed
  commit.
- The decision register `:505-510` pins the R4 path/blob/SHA and exact reviewed commit.

The R4 report remains historical evidence for target `aa54fe...`, parent `3cca017...`,
and the pre-R4-fix R3 object it actually inspected. Its original target metadata,
formatting, and internal historical hashes were not “corrected.” R4-m1 is closed.

## 7. Regression and completeness audit

### 7.1 Exact-set reconstruction

Independent parsing and production-loader reconstruction returned:

| Surface | Result |
|---|---:|
| 06d W2 lifecycle rows | 50 |
| 06d W2 message/governance rows | 41 |
| 06d retained W8 §20 operator rows | 13 |
| 06d normalized rows / unique keys | 104 / 104 |
| 06d expanded lifecycle edges | 182 |
| 06f baseline obligations | 11 unique |
| 06f activation obligations | 43 unique |
| 06f literal executions | 22 = 12 F-037 + 10 F-038 |
| 06e predecessor/successor rows | 51 unique / 51 unique |
| Gate 5 baseline positions | 132 |
| Gate 5 variant rows / positions | 46 / 170 |
| Gate 5 total positions | 302 |
| Unavailable M / H | 31 / 20 |
| Unavailable total / affected fixtures | 51 / 15 |
| Otherwise-available frozen positions | 251 |

The 182-edge derivation is 104 normalized rows plus 78 closed-class expansions: `+7`
Task amendment; `+18` for block/input/pause; `+14` for the 3×5 resume relation; `+21`
for three Task terminal transitions; `+4` attempt nonterminal; `+3` attempt retryable;
`+8` two review-nonterminal rows; and `+3` three decision-unresolved rows.

The 06e predecessor multiset equals the production-derived 51 unavailable result keys
with zero missing or extra. Every successor preserves fields 1–5 and sets field 6 to
`live-capability--<complete predecessor variant>`.

### 7.2 Frozen Gate 5 invariants

The accepted Gate 5 merge `f49a27fe15ae4df566c9107dc07f7451f51b924a`
exists. Its coverage blob `c1563b725702d8738597e6b25cc3f3061c51226c`, variant
matrix blob `6f2a63c59fcd5a33b0d0f915b1514ba1187fc55d`, and fixtures tree
`84acfbdbb72da2e91986142ae6cd1d8806622e36` exactly equal the corresponding objects
at the reviewed commit.

The production calibration/run smoke returned:

```text
{"blocked_fixture_count":15,"fixture_count":40,"fixtures_with_uncalibrated_mutations":0,"mutation_calibration":"calibrated"}
{"candidate_status":"blocked","result_count":302}
```

The production coverage loader also returned `gate5_authorized=false` and the sole
retained omitted Gate 5 capability as O15 / `delete_evidence_object` /
`capability_disabled` / `post_gate5_owner_decision`. Thus all eight literal Gate 5
invariants in 06a `:202-211` and 06b `:327-338` remain preserved.

### 7.3 Earlier-finding dispositions

| Finding family | R5 disposition | Independent basis |
|---|---|---|
| Original C-1 — secret/cost pre-issue | Closed | 06b `:65-89`, `:192-218`, and `:493-508` keep provider-specific sentinel and grant failures before invocation; no post-run scan compensates |
| Original M-1 — staged lifecycle | Closed | P-035 and all plan restatements use the executable `T1a → T2 → T3/T4 → T1b → T5 → T6 → T7 → T8` graph; T1a claims no observed calibration and T1b follows protected producers (`06b:48-106`, `:168-190`) |
| Original M-2 — exact W2/W8 catalogue | Closed | 104 unique complete rows, 13 W8 rows, 182 edges, independent schema identities, per-row cardinality/effects, authority, relation, and selector mutations (`06d:7-100`, `:334-372`) |
| Original M-3 — live semantic parity | Closed | T5 binds actual payload, provider command/receipt, grant/lease, and observed enforcement; actual seam perturbation is mandatory (`06b:107-115`) |
| Original M-4 — W4 profile eligibility | Closed | 06b T6 `:116-133` reproduces W4 `design/04-agent-roles-and-model-routing.md:264-289`, including complete evidence, non-compensable eligibility, currency, and authority |
| Original M-5 — complete P1 activation | Closed | Strict schema plus accepted 54-row expected manifest, 11 baseline + 43 activation, exact 12/10 summaries, producing-seam and coordinated-pair attacks (`06b:220-323`; 06f `:111-150`) |
| Original M-6 — live 302-row provenance | Closed | Exact 251 frozen + 51 live model, content-addressed 06e map, lifecycle-aware schema/loader, and unchanged P0 path (`06b:325-406`) |
| Original M-7 — migration path/writer exclusivity | Closed | Legacy backlog, ARS projection, annotation inbox, and optional combined view remain physically disjoint with writer/cutover tests (`06:135-167`; P-032 `03-decisions:398-407`) |
| Original m-1 — decision-register protocol | Closed | P-031–P-035 retain status, decision, rationale/evidence, boundary, migration consequence, and affected specifications (`03-decisions:386-523`) |
| R2-M1 — human calibration producer | Closed | T1b-M and T1b-H are separately complete and non-compensable, independently reviewed, then bound by one composite owner-accepted hash (`06b:90-106`) |
| R2-M2/R2-M3 — command identity and complete-row effects | Closed | Exact `command_type` plus schema ID/version/hash propagate through grant, dispatch, events, receipt, and idempotency; full records compare one-to-one with duplicate/swap/alias/effect attacks (`06d:14-26`, `:44-100`, `:334-372`) |
| R2-M4/R2-M5 — canonical P1 keys and producer independence | Closed | 06f fixes eleven six-tuples and 43 activation identities; independently accepted manifest contains literal descriptor hashes before observation (`06f:14-45`, `:111-150`) |
| R2-M6 — literal 51-row map | Closed | 06e contains 51 exact predecessor/successor rows and mutation contract; independent comparison found exact equality to the unavailable set (`06e:32-101`) |
| R2-M7 — stage vocabulary | Closed | W6 `gate_stage: pilot_promotion` remains valid; `live_capability`/`p1_activation` are separate typed evidence stages (`06b:220-251`, `:340-406`) |
| R2-m1 — portable review locator | Closed | P-035 uses repository-relative review paths and Git object identities (`03-decisions:487-510`) |
| R3-M1/R3-M2 — strict P1 schema and independent oracle | Closed | Dedicated closed schema and independently produced/reviewed/accepted 54-row literal descriptor-hash manifest precede build/observation (`06b:220-251`; 06f `:111-150`) |
| R3-M3/R3-M4 — versioned command identity and universal authority | Closed | 104-row schema-identity manifest is independent; complete identity propagates; all rows receive the full authority attack set (`06d:50-100`, `:102-139`) |
| R3-M5/R3-M6 — atomic claim and correction selector | Closed | Two-stream relational claim is exact and the selector domain/map is literal, runtime-independent, and mutation-tested (`06d:141-210`) |
| R3-m1 — summary cardinality | Closed | F-037/F-038 bind exactly 12/10 hashes and disjoint union 22 (`06b:286-323`; 06f `:95-109`) |
| R4-M1/R4-M2/R4-m1 | Closed | Detailed in §§4–6 above |

### 7.4 Ambiguity and fail-open pass

No remaining authority alias, projection mismatch, circular evidence dependency,
expected/observed self-confirmation, untestable “complete” claim, permissive stage alias,
count-only closure, migration dual writer, or fail-open provider/grader fallback was
found. The narrowest restatements agree with the master exit checklist. Future material
is explicitly gated by path/schema/blob/SHA identity and independent review rather than
being credited as present evidence.

## 8. Invariant → enforcement → test matrix

| Invariant | Enforcement point | Required attack/test | R5 result |
|---|---|---|---|
| Decision/RuleEvaluation non-compensation | Accepted owner catalogue and selector manifest; authority resolver; reducer/projection comparison | Cross-grant, cross-ID, cross-projection, coordinated candidate/runtime corruption | Pass at plan-contract level |
| Dispatch-bound Task claim | Loaded accepted Dispatch revision, exact Task relation, same-subject active lease, two-stream batch | Foreign current Task, stale relation, wrong lease, coordinated valid records, omission/race/write-set/version/tail/idempotency attacks | Pass at plan-contract level |
| Exact W2/W8 closure | 104-row owner catalogue plus independently accepted schema-identity manifest | Missing/extra/duplicate/alias/swap/class/effect/test/schema/authority mutations | Pass at plan-contract level; 104 unique / 182 edges |
| P1 activation | Strict P1 schema plus accepted 54-row descriptor-hash expected manifest | Missing/extra/relabelled/stale/observed-derived rows and coordinated descriptor/manifest pair | Pass at plan-contract level; future artifact still owner-gated |
| Live composite | 06e expected map plus live-coverage schema and relational loader | Missing/duplicate/swap/wrong provider/model/adapter/lifecycle/bijection | Pass at plan-contract level; exact 251+51=302 |
| Frozen Gate 5 | Production loaders, immutable accepted objects, baseline smoke | Object equality and exact 40/15/0/calibrated/302/blocked/false/O15 assertions | Pass |

## 9. Decision and owner-authority audit

| Decision | R5 disposition |
|---|---|
| P-031 | Preserved. SCALE-01 changes only the pilot occupant; promotion criteria remain. |
| P-032 | Preserved. Legacy/successor path and writer exclusivity remain closed. |
| P-033 | Preserved. No interim degraded/operator bypass is introduced. |
| P-034 | Preserved. Consolidation remains downstream and transition-gated. |
| P-035 | Preserved. Accepted sequencing/composition is unchanged; R2/R3/R4 mechanisms remain pending exact-revision approval and materialization where stated. |
| D-G6-2 | Still open for the two future exact-hash evidence gates; no protocol or empirical policy hash is inferred. |
| D-G6-3 | Eligible for Stephen's exact-revision approval at `fe5f1d40...`; future WP6.1 and WP6.2 manifests still require their separately specified path/schema/blob/SHA acceptances before implementation or observation. |
| D-G6-4 / D-G6-5 | Deferred. No migration batch or Gate 6 preflight acceptance is authorized by this review. |

## 10. Validation results

The two required commands were run from the exact detached target with bytecode writes
disabled. No broad pytest command was run.

| Command | Exit | Exact outcome |
|---|---:|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` | 0 | `Contract framework: all gates passed against 98 contract(s).` |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | 0 | `Contract framework: all gates passed against 98 contract(s).` |

The additional production coverage-loader and Gate 5 smoke was read-only and is recorded
in §7.2; it was not a pytest run. No repository coverage database was created.

## 11. Residual risks and non-blocking observations

Residual risks are future verification obligations, not defects in this reviewed plan:

- The WP6.1 catalogue/schema-identity manifests and WP6.2 54-row descriptor-hash
  manifest do not yet exist as owner-accepted implementation artifacts. Their future
  producers, independent reviews, hashes, and runtime enforcement must match this plan.
- The current implementation is intentionally pre-WP6. Implementation review must test
  actual grant/ID propagation, selector behavior, two-stream atomicity, concurrency,
  idempotency, and replay rather than credit schema or interface names.
- T1a, T1b-M, T1b-H, live parity, evaluated profiles, P1 calibration, and provider
  behavior remain empirical. Missing or stale evidence remains blocking.
- W11, project binding, dossier admission, migration batches, and Gate 6 preflight retain
  their later review and owner gates.
- A first production-loader reconstruction refreshed ignored Python bytecode caches
  before bytecode suppression was enabled. Git remained clean and no tracked,
  canonical, plan, evidence, or coverage artifact changed; subsequent validation used
  `PYTHONDONTWRITEBYTECODE=1`. This runner-side cache disclosure is not credited as
  evidence.

Non-blocking observation R5-O1: the two 06e/06f filenames in the review request are
stale aliases; the repository index and every controlling plan consistently use the
actual committed paths named in §2. This does not create an implementation ambiguity.

## 12. Final disposition and change log

**Verdict:** `approved`.

**Is commit `fe5f1d40bc8f05f061317c677b5891cea0711249` safe to use as the Gate 6
launch basis?** **Yes**, subject to every still-open materialization, exact-hash,
independent-review, owner-approval, and preflight gate stated above.

**Exact reviewed commit:** `fe5f1d40bc8f05f061317c677b5891cea0711249`  
**Required validation:** both commands passed all gates against 98 contracts with exit
code 0.  
**Files intentionally changed by this task:** this R5 review artifact only.  
**Reviewed plan/runtime tracked files changed:** none.
