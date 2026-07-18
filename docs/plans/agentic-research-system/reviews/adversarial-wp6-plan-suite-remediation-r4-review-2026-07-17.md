# Adversarial WP6 plan-suite remediation R4 review

**Review date:** 2026-07-17  
**Reviewer posture:** fresh, independent, adversarial remediation re-review  
**Target repository:** `TDL`  
**Target branch:** `codex/wp6-plan-suite-review-remediation`  
**Target commit:** `aa54fe140de8eff3dabe0472758c3514fa673b19`  
**Target parent:** `3cca017c936a1d2b6a6b2049bc866caf5cb79047`  
**Verdict:** `rework_required`  
**Dispatch status:** **not dispatchable**

## 1. Executive verdict

The R3 remediation materially strengthens the plan suite. At the pre-implementation
contract level it now defines the dedicated strict P1 manifest shape, a fail-closed
future acceptance boundary for the 54-row descriptor-hash oracle, complete versioned
command/event identity propagation, universal authority attacks, a two-stream atomic
claim batch, a closed correction-selector table, and the exact F-037/F-038 12/10 split.

The exact revision is nevertheless not ready for D-G6-3 approval. This review finds
**0 Critical, 2 Major, and 1 Minor** defects:

1. the expected authority and correction-selector mappings collapse
   `RuleEvaluation` into `Decision`, contradicting W2's non-compensable separation; and
2. `ClaimDispatch` binds two valid stream identities but never requires the Task to be
   the Task revision already bound by the Dispatch, so a dispatch-authorized command
   can atomically start an unrelated ready Task.

The Minor is a platform-dependent SHA-256 mislabeled as canonical in the R3 report.
The hash pins used by the revised plans for 06d, 06e, 06f, and R3 itself reproduce.

**Explicit answer:** No. Stephen should not approve this exact revision for D-G6-3 or
proceed to Gate 6 launch planning. A successor exact commit must close R4-M1 and R4-M2,
retain every other closure, pass a fresh independent review, and then receive Stephen's
exact-revision approval. The future schema/expected manifests and D-G6-2 evidence gates
also remain explicit pre-implementation/pre-observation owner actions; this review does
not manufacture or accept them.

## 2. Exact-object, checkout, and review-artifact provenance

| Check | Independently observed result |
|---|---|
| Target object | Git commit `aa54fe140de8eff3dabe0472758c3514fa673b19` |
| Target parent | `3cca017c936a1d2b6a6b2049bc866caf5cb79047` |
| Symbolic branch | `codex/wp6-plan-suite-review-remediation` |
| Target checkout | `C:/Users/steph/.codex/worktrees/132d/TDL` |
| Target Git state before and after review | clean |
| Target commit subject | `[DECISION] P00: close WP6 R3 remediation findings` |
| Review artifact checkout | `C:/Users/steph/.codex/worktrees/577d/TDL`, detached at `0ab9e9ce55a6d572c3d4acfb4f5f013b1b3d4183` |
| Review artifact | this R4 report only |
| Reviewed tracked-file mutations | none |
| Runner-side disclosure | an initial focused pytest invocation updated the ignored target-root `.coverage` database; Git remained clean, but the session was therefore not byte-for-byte read-only at the filesystem level |

The primary R3 report is committed in the target tree. The requested original report,
`adversarial-wp6-plan-suite-review-2026-07-17.md`, is absent from the target tree. It was
inspected directly as reachable Git blob
`c46cf161f4d8ba79bda77ec12a0958e28294477a` (canonical SHA-256
`9c30a02a042da725de509235b9c7b3df6a80fe0987b629570f13be81763e6f61`), introduced by
snapshot commit `db25857c556167d1e6df4c5687bf8e8809902094`. The three committed remediation
reviews were read as finding catalogues, not inherited proof.

## 3. Finding summary

| ID | Severity | Finding | Approval effect |
|---|---|---|---|
| R4-M1 | Major | `RuleEvaluation` is mapped to Decision authority and the Decision projection | Blocks D-G6-3; R3-M4/R3-M6 not fully closed |
| R4-M2 | Major | Atomic `ClaimDispatch` omits the Dispatch-to-Task relational equality and wrong-Task attack | Blocks D-G6-3; R3-M5 not fully closed |
| R4-m1 | Minor | R3 labels a CRLF checkout hash as canonical | Correct provenance text; not independently approval-blocking |

## 4. Findings

### R4-M1 — Rule evaluation is collapsed into Decision authority and projection

1. **ID and severity:** `R4-M1`, **Major**.
2. **Precise claim:** The new exact authority table assigns `rule.evaluate` the subject
   kind `decision` and `payload.new_decision_id`; the new correction-selector table maps
   `rule_evaluation` to the `decision` owner projection. Both contradict accepted W2,
   which requires `RuleEvaluation` to remain a distinct mechanical record and requires
   a separate authorized Decision for any governance promotion.
3. **Evidence:** `implementation/06d-wp6-1-owner-source-catalogue.md:122` groups
   `rule.evaluate` under Decision authority. Lines `180-181` map both Decision and
   RuleEvaluation corrections to the Decision projection. The literal catalogue row at
   `:288` names `RecordRuleEvaluation` and `reduce_rule_evaluation` but still lists the
   Decision projection. Accepted W2
   `design/02-task-event-and-artifact-schema.md:795-817` says only an authorized
   `ResolveDecision` resolves a Decision and that a `RuleEvaluation` is not automatically
   a human Decision. The implementation seam is not a rescue: current authority supports
   only its existing closed kinds (`research_system/authority.py:39-42`), and the plan's
   future manifest would copy the erroneous expected mapping before extending it.
4. **Concrete bypass:** An agent holds a grant scoped to a proposed Decision ID and
   submits `RecordRuleEvaluation`. Because the expected manifest says the subject is a
   Decision, the wrong scope is accepted as correct. A later correction with
   `corrected_record_kind: rule_evaluation` is routed to the Decision projection rather
   than a RuleEvaluation projection. The complete-row equality, authority-rule mutation,
   and selector swap tests can all pass because the independently frozen expected side
   itself contains the collapse.
5. **Impact:** Mechanical output and human/governance authority become confusable. This
   can authorize the wrong record, update the wrong owner projection, or make a
   mechanical evaluation appear in the Decision state surface without the separate
   Decision required by W2.
6. **Required disposition:** Fix now. Give RuleEvaluation a distinct authority subject
   and owner projection, then add non-compensation mutations proving that neither a
   Decision grant/projection nor a RuleEvaluation grant/projection can substitute for
   the other.
7. **Exact proposed interface:** Replace the family row with
   ``| `rule.evaluate` | `rule_evaluation` | `payload.new_rule_evaluation_id` |`` and
   replace the selector row with
   ``| `rule_evaluation` | `rule_evaluation` |``. Amend the catalogue row's projection
   set to `rule_evaluation, governance`. Add mutations for Decision-scoped grant on
   `RecordRuleEvaluation`, RuleEvaluation-scoped grant on `ResolveDecision`, and
   coordinated candidate-manifest/runtime selector corruption; every case must reject
   with unchanged event tail, receipt acceptance state, Decision projection,
   RuleEvaluation projection, and governance index.
8. **Affected decisions/work packages:** P-035, D-G6-3, WP6.1 T1/T5, 06a §3, 06d
   §§1.2/1.4/3/5, W2 §18.4 and §19, authority grants, correction selector, replay, and
   projection tests.

### R4-M2 — ClaimDispatch does not prove that the claimed Task belongs to the Dispatch

1. **ID and severity:** `R4-M2`, **Major**.
2. **Precise claim:** The remediation binds valid Dispatch and Task IDs, revisions,
   versions, global position/tail, write set, batch, and receipt, but it does not require
   the payload Task ID/revision to equal the Task revision already bound by the Dispatch.
   It also lacks a foreign-but-current Task mutation.
3. **Evidence:** Accepted W2 states that a Dispatch binds one Task revision
   (`design/02-task-event-and-artifact-schema.md:451-466`) and that claim validates both
   Dispatch and Task versions (`:479`, `:561-567`). The remediation lists the fields and
   two-stream batch at `implementation/06d-wp6-1-owner-source-catalogue.md:142-153` and
   tests Task omission, staleness, race, revision mismatch, write-set defects, and a
   Dispatch-only receipt at `:155-160`; it never states
   `loaded_dispatch.task_id/revision == payload.task_id/revision` and never names a
   wrong-Task-ID mutation. Both claim facets repeat only “exact Task ID/revision/version
   and Dispatch ID/version” at `:206` and `:220`. The authority mapping at `:114` scopes
   both facets only to the Dispatch, making this omitted relation security-relevant.
   Current code illustrates the available failure seam: `ClaimDispatch` builds only one
   `DispatchClaimed` event (`research_system/command/service.py:841-843`) and replay
   changes only the Dispatch stream (`research_system/projection/replay.py:179-196`).
4. **Concrete bypass:** Dispatch `D1` is acknowledged and bound to `T1@r1`. An actor
   authorized for `D1` submits a complete claim payload naming unrelated ready Task
   `T2@r1` with its current stream version. Both stream versions, IDs, write-set members,
   event order, global tail, and receipt are internally valid. None of the named tests is
   a mismatch: `T2@r1` is a real current Task revision. The command can therefore claim
   `D1` while moving `T2` to `in_progress` atomically.
5. **Impact:** Dispatch authority can mutate an unrelated Task, corrupting ownership,
   lease, attempt, and projection lineage while still satisfying the advertised atomic
   batch contract.
6. **Required disposition:** Fix now. Make the stored Dispatch-to-Task-revision relation
   an explicit precondition before authority reuse, idempotency lookup, version
   advancement, or event allocation. Decide explicitly whether Dispatch-scoped authority
   is sufficient only for its stored Task or whether the atomic command must carry a
   two-subject authority binding.
7. **Exact proposed text/interface:** “`ClaimDispatch` MUST load the accepted Dispatch
   revision and require `(dispatch.task_id, dispatch.task_revision) ==
   (payload.task_id, payload.task_revision)`. Its lease subject MUST bind the same Task
   revision and Dispatch. A current foreign Task ID/revision, a stale Dispatch-to-Task
   link, or a lease bound to another Task MUST reject before idempotency lookup or
   publication and leave both streams and all projections unchanged.” Add the D1/T2
   mutation independently of the already named stale-version and wrong-revision cases.
8. **Affected decisions/work packages:** P-035, D-G6-3, WP6.1 T2, 06a §§2-3, 06d
   §§1.2/1.3/2/5, W2 §12 and §13, command envelope, authority, lease, event-batch,
   receipt, idempotency, replay, and concurrency tests.

### R4-m1 — R3 mislabels a CRLF checkout hash as canonical

1. **ID and severity:** `R4-m1`, **Minor**.
2. **Precise claim:** R3's provenance table labels the SHA-256 of a Windows CRLF
   worktree copy as the canonical hash of the first remediation report.
3. **Evidence:** R3 `reviews/adversarial-wp6-plan-suite-remediation-r3-review-2026-07-17.md:42-45`
   gives blob `b962ed11813ff0a0164a0f8be3eef7e926757e5e` and SHA-256 `0ac344...` under
   “canonical checked-out bytes.” Direct hashing shows that blob's canonical LF bytes
   have SHA-256
   `93a79b324a4ec2780496effb58f7b8b75c78b4ac10a9824bddc7a416a9011228`;
   `0ac344...` is the 33,951-byte CRLF checkout hash.
4. **Failure scenario:** A verifier hashes the Git blob or a fresh LF checkout and
   rejects the report identity even though the cited blob is correct.
5. **Impact:** Local provenance ambiguity only. P-035 cites the correct Git blob, and
   the revised decision's R3 blob/SHA pair reproduces.
6. **Required disposition:** Correct the R3 table in a later documentation-only change
   or label both hashes with their exact byte surfaces.
7. **Exact proposed text:** “canonical Git-blob UTF-8/LF SHA-256 `93a79b...`; Windows
   CRLF checkout SHA-256 `0ac344...`.”
8. **Affected decisions/work packages:** R3 review provenance and P-035 evidence
   traceability; no implementation work package.

## 5. R3 finding dispositions

| R3 finding | R4 disposition | Independent basis |
|---|---|---|
| R3-M1 — strict P1 schema | **Closed at pre-implementation contract level** | 06b `:222-241` names a dedicated v1 schema, fixes the two stage constants, exactly 11 ordered baseline and 43 ordered activation bindings, both content identities, expected event position, `items: false`, and `additionalProperties: false`; `:392-405` rejects P0/cross-stage/incomplete/stale/unknown input before invocation or state change without widening W6 `gate_stage`. |
| R3-M2 — independent P1 descriptor oracle | **Closed as an explicit future owner-acceptance gate; artifact not yet accepted** | 06f `:113-129` fixes path/schema/version, role separation, 54 closed rows, descriptor path/hash fields, strictness, and D-G6-3 blob/SHA acceptance before build/observation; `:131-149` prohibits runtime production/amendment and requires the coordinated-pair attack. This is a complete pre-observation boundary, not present execution evidence. |
| R3-M3 — versioned command/event identity | **Closed as an explicit future owner-acceptance gate; artifact not yet accepted** | 06d `:67-100` defines the 104-row strict identity manifest, independent production/review/acceptance, grant/dispatcher/event/receipt/idempotency propagation, and retained-type changed-ID/version/hash rejection before state change. Runtime registries remain observed inputs. |
| R3-M4 — universal authority behavior | **Partially closed; superseded by R4-M1** | N0 now applies missing/wrong/expired authority and wrong actor/scope/subject to every row (`06d:50-65`), and `:102-138` adds exact sources and not-yet-effective/rule mutations. The `rule.evaluate` subject mapping is semantically wrong. |
| R3-M5 — atomic ClaimDispatch | **Partially closed; superseded by R4-M2** | The batch, two versions, global tail, exact write set, event order, dual-version receipt, omissions, races, and atomic no-change behavior are explicit (`06d:140-160`), but the Dispatch-bound Task equality is absent. |
| R3-M6 — correction selector | **Partially closed; superseded by R4-M1** | The domain and mapping are literal and runtime-independent (`06d:162-189`), but `rule_evaluation -> decision` violates the owning semantic separation. |
| R3-m1 — F-037/F-038 cardinality | **Closed** | 06f `:99-100` and 06b `:286-287,318-321` fix 12/10, disjoint union 22, and the separate summary assertions. |

## 6. Earlier finding regression audit

### 6.1 R2 findings

| R2 finding | R4 disposition |
|---|---|
| R2-M1 — T1b human calibration producer | **Closed; remains closed.** Separate T1b-M/T1b-H evidence and non-compensation remain unchanged. |
| R2-M2 — complete-row catalogue identity | **Structurally closed; semantic residual superseded by R4-M1.** The 104-row multiset and versioned identities are explicit, but one frozen subject/projection mapping is wrong. |
| R2-M3 — catalogue mutations/enforcement | **Partially closed; superseded by R4-M1/R4-M2.** Aggregate and one-field attacks are strong; the wrong expected RuleEvaluation mapping and foreign-current-Task attack remain. |
| R2-M4 — canonical P1 keys | **Closed; remains closed.** Eleven unique six-field baseline keys and 43 unique activation IDs reproduce. |
| R2-M5 — expected/observed producer independence | **Closed at plan-contract level; owner acceptance outstanding.** 06e remains literal and 06f now defines the pre-observation accepted manifest boundary. |
| R2-M6 — literal 51-row replacement map | **Closed; remains closed.** The exact predecessor set and successor rule reproduce. |
| R2-M7 — stage vocabulary drift | **Closed; remains closed.** `pilot_promotion` remains the W6 gate stage; `live_capability`/`p1_activation` are separate evidence stages. |
| R2-m1 — portable review locator | **Closed for the P-035 citations.** The original non-remediation report is absent from this tree but was reachable and reviewed as a Git object; P-035 does not rely on it as its portable evidence locator. |

### 6.2 Original WP6 findings

| Original finding | R4 disposition |
|---|---|
| C-1 secret/cost pre-issue | **Closed; retained.** |
| M-1 staged lifecycle/dependency graph | **Closed under P-035; retained.** |
| M-2 exact W2/W8 catalogue | **Partial only through R4-M1/R4-M2; no aggregate row-count regression.** |
| M-3 live semantic parity | **Closed; retained.** |
| M-4 W4 profile eligibility | **Closed; retained.** |
| M-5 complete P1 activation | **Closed at plan-contract level; future accepted manifest/evidence still required.** |
| M-6 live 302-row provenance composition | **Closed; retained.** |
| M-7 migration path/writer exclusivity | **Closed; retained.** |
| m-1 decision-register protocol | **Closed; retained.** |

## 7. Mandatory adversarial-check results

| Check | Result |
|---|---|
| A. P1 strict schema | **Pass at plan-contract level.** Dedicated v1 path, valid W6 stage, separate evidence stage, exact 11+43 ordered shape, accepted 06f/expected-manifest identities, expected event position, closed objects/arrays, and pre-invocation/state rejection are explicit. The schema is a future materialization and supplies no present execution evidence. |
| B. Independent P1 descriptor oracle | **Pass as a concrete future owner gate.** Producer/reviewer/acceptor separation, immutable path/schema/blob/SHA acceptance before build, runtime-side prohibitions, and coordinated altered-pair rejection are explicit. The 54 literal descriptor hashes do not yet exist and must be accepted before observation. |
| C. Versioned command/event identities | **Pass as a concrete future owner gate.** The 104-row expected manifest, ordered event identities, authority/dispatcher/event/receipt/idempotency propagation, and retained-type mutations are closed in 06d. Current registries are comparison inputs only. |
| D. Authority behavior for every row | **Fail — R4-M1.** Universal attacks and sources are present, but `rule.evaluate` has the wrong exact subject kind/ID source. |
| E. Atomic ClaimDispatch | **Fail — R4-M2.** Two-stream atomicity is specified, but the Dispatch-bound Task relationship and foreign-current-Task mutation are absent. |
| F. Correction selector | **Fail — R4-M1.** The table is independently frozen, but its `rule_evaluation -> decision` mapping is wrong. |
| G. F-037/F-038 cardinality | **Pass.** Independently parsed execution rows are 12 and 10, disjoint, union 22. |
| H. Retained invariants/provenance | **Pass except R4-m1's provenance label.** All requested counts and primary annex pins reproduce; frozen Gate 5 remains unchanged. |

## 8. Independent cardinality, identity, and hash reconstruction

### 8.1 Catalogue and P1 sets

| Quantity | Independent result |
|---|---:|
| 06d normalized/unique rows | 104 / 104; no duplicate keys |
| 06d row groups | 50 W2 lifecycle + 41 W2 message/governance + 13 W8 operator |
| 06d expanded concrete edges | 182 |
| 06f baseline obligations | 11 unique |
| 06f activation obligations | 43 unique |
| P1 union | 54 |
| Literal executions | 22 = 12 F-037 + 10 F-038; disjoint |

The 182-edge reconstruction was `104 + 7` for the eight-state Task amendment, `+18`
for the three seven-state suspension entries, `+14` for the 3×5 resume relation,
`+21` for three eight-state Task terminal transitions, `+4` attempt-nonterminal,
`+3` attempt-retryable, `+8` two review-nonterminal, and `+3` three
decision-unresolved expansions.

### 8.2 Frozen Gate 5 and live replacements

Production loaders, not plan counts, returned:

| Quantity | Independent result |
|---|---:|
| selected fixtures | 40 |
| baseline result positions | 132 |
| selected Gate 5 variant rows / positions | 46 / 170 |
| total frozen positions | 302 |
| unavailable M / H | 31 / 20 |
| unavailable total / affected fixtures | 51 / 15 |
| otherwise available frozen references | 251 |
| 06e predecessor/successor rows | 51 unique / 51 unique |
| 06e predecessor equality to unavailable set | exact; 0 missing, 0 extra |
| successor construction | all 51 preserve fields 1-5 and prefix the full predecessor variant |
| Gate 5 release surface | 40 fixtures; 15 blocked; 0 uncalibrated; calibrated; 302 results; candidate blocked; `gate5_authorized=false`; O15 disabled/deferred |

The accepted Gate 5 merge `f49a27fe15ae4df566c9107dc07f7451f51b924a` exists.
Its coverage blob `c1563b725702d8738597e6b25cc3f3061c51226c`, variant-matrix blob
`6f2a63c59fcd5a33b0d0f915b1514ba1187fc55d`, and fixtures tree
`84acfbdbb72da2e91986142ae6cd1d8806622e36` exactly equal the target revision's
objects.

### 8.3 Canonical object identities

| Artifact | Git blob | Canonical UTF-8/LF SHA-256 | Bytes |
|---|---|---|---:|
| `implementation/06d-wp6-1-owner-source-catalogue.md` | `31522f6d7242538ff589def27764545390d6198f` | `967c753f5954bd2045e55e0db643c6bdb91d4b58f3af953e82584943158022e6` | 46,315 |
| `implementation/06e-wp6-2-live-replacement-map.md` | `a187ff6435f0a170bbb894bbb2a94ce97586fa30` | `a65c24624bb309558dd29a779b2db5b1c308b9fcd5caff4b5394e365b77e47b8` | 18,338 |
| `implementation/06f-wp6-2-p1-activation-contract.md` | `8e3e625e2cba41a5bd0c66a6763cb4d3c47d036b` | `160f898837df14d3f22ba2592eb117766686b5d5d6e4004cb8669886ea8d670c` | 9,852 |
| R3 review | `64748512357161583a7a459df84afa7ef2f784ae` | `fa3f4b6eede006e59df61f68d8372054be159aff2b9d6858978248ba16cf25ed` | 41,858 |
| R2 review | `b9b3963ccfc6ef9bceba9177497a1c83f69c3c18` | `6015717b097fec2d02b665e7f22a8647a486590c036b9e74f1f096bda3428f41` | 35,841 |

All four revised-plan pins to 06d/06e/06f/R3 reproduce. The target parent pin,
R3 target/parent pin, and R2 target/parent chain also reproduce:
`aa54fe1 -> 3cca017 -> 79f6b1b -> 45d29dd`.

## 9. Contract, targeted-test, and current-seam verification

| Command/check | Result |
|---|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` | pass; all gates against 98 contracts |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | pass; all gates against 98 contracts |
| Focused command/authority/replay/schema-registry pytest partition with `--no-cov -p no:cacheprovider` | 60 passed in 46.66s |
| Initial eight-file focused pytest aggregate | wrapper timeout at 124s before a recoverable aggregate summary; not credited as a pass |
| Production coverage/variant reconstruction | succeeded; exact 40/132/46/170/302 and 31/20/51/251 counts above |

The current implementation is intentionally pre-WP6 and cannot be mistaken for closure:

- grants still carry `allowed_command_types`, not complete command identities
  (`.research-system/schemas/core/authority-grant.schema.json:5-11`;
  `research_system/authority.py:1038`);
- the schema registry stores `$id -> schema` without content hashes
  (`research_system/schema_registry.py:42-47`);
- receipts do not carry command-schema identity
  (`.research-system/schemas/core/receipt.schema.json:5-27`);
- `ClaimDispatch` currently emits only `DispatchClaimed`
  (`research_system/command/service.py:841-885`); and
- replay currently changes only Dispatch for that event
  (`research_system/projection/replay.py:179-196`).

These are future implementation obligations, not new defects in a non-dispatchable plan.
They reinforce why the accepted expected manifests and the corrected relational
contracts must exist before implementation starts.

## 10. Decision and owner-authority audit

| Decision | R4 disposition |
|---|---|
| P-031 | Preserved. SCALE-01 pilot occupant does not relax pilot-promotion criteria. |
| P-032 | Preserved. Legacy/successor path and writer exclusivity remain closed. |
| P-033 | Preserved. The staged WP6.2 sequence remains executable and non-compensable. |
| P-034 | Preserved. Consolidation remains downstream and does not authorize migration. |
| P-035 | Preserved as the governing remediation/approval boundary, but its R3 authority/claim constraints are not correctly instantiated by this exact revision. |
| D-G6-2 | Open for the two future exact-hash owner acceptances; no protocol/policy hash is inferred here. |
| D-G6-3 | **Not approvable at `aa54fe140de8eff3dabe0472758c3514fa673b19`.** R4-M1 and R4-M2 remain Major. The future WP6.1 and WP6.2 manifests are also not yet materialized or accepted. |
| D-G6-4 / D-G6-5 | Deferred. No W11 migration or Gate 6 preflight acceptance is authorized. |

No owner decision, implementation authority, live call, state transition, or Gate 6
authorization is created by this review.

## 11. Remaining actions and launch recommendation

### Immediate plan corrections

1. Separate RuleEvaluation from Decision in the authority-subject table, catalogue
   projection set, and correction-selector mapping; add non-compensation and coordinated
   expected/runtime mutations.
2. Add the exact Dispatch-bound Task ID/revision equality, lease relation, and
   foreign-current-Task mutation to `ClaimDispatch`.
3. Correct or qualify R3's CRLF/canonical SHA label.

### Required owner actions after a successor review

1. Obtain a fresh independent no-Critical/no-Major review of the successor exact commit.
2. Stephen approves that exact plan revision; no other revision supplies dispatch text.
3. Before WP6.1 runtime implementation, independently produce/review and Stephen accepts
   the catalogue/schema-identity manifests by exact path, schema ID/version, Git blob,
   and SHA-256.
4. Before any P1 descriptor build or observation, independently produce/review and
   Stephen accepts the strict 54-row expected manifest with every literal descriptor
   hash by exact path/schema/blob/SHA identity.
5. Complete the separate D-G6-2 T1a and T1b-M/T1b-H exact-hash acceptance gates, then
   satisfy the remaining Gate A, W11, and Gate 6 preflight owner gates in order.

**Launch recommendation:** `rework_required`. Do not approve D-G6-3, dispatch WP6,
invoke a live provider, mutate ARS state, or begin Gate 6 launch planning from
`aa54fe140de8eff3dabe0472758c3514fa673b19`.

## 12. Evidence and change log

- Reviewed exact clean target commit and direct owner sources W2, W4, W6, W7, and W8.
- Re-read R3 and independently retested every R2/original disposition.
- Reconstructed catalogue rows/edges, P1 obligations/executions, Gate 5/live-replacement
  counts, Git blobs, SHA-256 values, and parent pins without copying prior conclusions.
- Ran the mandated contract checks and focused current-seam tests as recorded in §9.
- Files changed by this task: this R4 report only in the authorized artifact checkout.
- Reviewed target tracked files changed: none.
