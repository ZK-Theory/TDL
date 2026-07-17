# Adversarial WP6 plan-suite remediation R3 review

**Review date:** 2026-07-17  
**Reviewer posture:** fresh, independent, adversarial remediation re-review  
**Target branch:** `codex/wp6-plan-suite-review-remediation`  
**Target commit:** `3cca017c936a1d2b6a6b2049bc866caf5cb79047`  
**Expected parent:** `79f6b1bfb28a02d6a06d5a4a350bfa7262ec6461`  
**Read-only target:** `C:/Users/steph/.codex/worktrees/132d/TDL`  
**Verdict:** `rework_required`  
**Dispatch status:** **not dispatchable**  

## 1. Executive verdict

The remediation is materially stronger than R2. It closes the owner-source catalogue, live-replacement exact-set, stage-vocabulary, and portable-provenance findings, and it preserves the frozen Gate 5 surface. It does not yet establish a complete, independently anchored P1 activation contract.

This review finds **0 Critical, 6 Major, and 1 Minor** issues. All six Major findings are approval-blocking:

1. the proposed P1 pilot-coverage manifest has no named strict schema contract; and
2. the P1 descriptor hashes are deferred to an unspecified future “semantic copy,” leaving their expected-side producer capable of correlating with the observed descriptor producer;
3. 06d declares versioned command identity but does not independently freeze or propagate the per-command schema identity;
4. 27 catalogue rows omit the semantic authority attacks required by W2’s validation order;
5. the shared `ClaimDispatch` contract does not define W2’s Task-plus-Dispatch concurrency/write-set boundary; and
6. the correction selector has no independently frozen domain or kind-to-projection mapping.

Accordingly, D-G6-3 cannot be approved at this revision. No WP6 implementation, live provider call, state mutation, owner decision, or Gate 6 authorization is justified by this review.

## 2. Exact-object and checkout verification

| Check | Independently observed result |
|---|---|
| Target object type | `commit` |
| Target `HEAD` | `3cca017c936a1d2b6a6b2049bc866caf5cb79047` |
| Target parent | `79f6b1bfb28a02d6a06d5a4a350bfa7262ec6461` |
| Symbolic target branch | `codex/wp6-plan-suite-review-remediation` |
| Target worktree state | clean; no staged or unstaged changes |
| Diff from expected parent | 11 files; 1,535 insertions; 211 deletions |
| Review authority | exact Git objects plus accepted design/implementation objects; not a narrative-only comparison |
| Review-side mutation | none in the target worktree |

The prior reports were treated as finding catalogues, not as proof:

| Artifact | Git blob | SHA-256 of canonical checked-out bytes |
|---|---|---|
| `docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-review-2026-07-17.md` | `b962ed11813ff0a0164a0f8be3eef7e926757e5e` | `0ac3442376fc5d7ddc476b07e71cfc64003e6d4f4c992d0ccc234b7a87196973` |
| `docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r2-review-2026-07-17.md` | `b9b3963ccfc6ef9bceba9177497a1c83f69c3c18` | `6015717b097fec2d02b665e7f22a8647a486590c036b9e74f1f096bda3428f41` |

The review read the three remediation annexes and the controlling decisions/readiness/implementation plans in full, then checked the relevant W2, W4, W6, W7, and W8 accepted design clauses and current schemas/loaders/reducers/CLI behavior. Exact-set results below were reconstructed independently rather than copied from either prior report.

## 3. Findings

### R3-M1 — P1 activation has no strict manifest schema

1. **ID and severity:** `R3-M1`, **Major**.
2. **Claim:** The suite introduces `.research-system/evals/p1-pilot-coverage.yaml` but never names or defines a strict schema that can validate its P1-specific structure and complete 54-obligation binding.
3. **Evidence:** `implementation/06b-wp6-2-live-capability-plan.md:218-227` defines `gate_stage: pilot_promotion`, `evidence_stage: p1_activation`, and the 54 obligations. The only new schema named at `:322-346` is `live-coverage-manifest.schema.json`, whose described 302-entry `frozen_reference`/`live_result` model is T7-specific. The accepted `.research-system/schemas/evals/coverage-manifest.schema.json:5-13,27-31,71` has a closed Gate 5 vocabulary, no `evidence_stage`, and `additionalProperties: false`; it cannot validate the proposed P1 manifest. No alternative P1/stage schema is identified. Current `research_system/cli.py:237-263,611-626` is intentionally P0-only, so implementation cannot inherit a current strict P1 contract.
4. **Failure or bypass scenario:** An implementer can ad hoc widen the accepted Gate 5 schema or build a bespoke P1 loader whose syntax accepts the command examples but does not require all 11 baseline bindings, all 43 activation bindings, the 06f identity, or cross-stage rejection. The plan can appear implemented while its closure is not schema-enforced.
5. **Impact:** D-G6-3 lacks an implementable fail-closed interface. WP6.2 T8 and the proposed stage CLI may accept incomplete, mixed-stage, or weakly bound evidence before state change.
6. **Required disposition:** Define a strict P1 schema before exact-revision approval. Either create a dedicated `p1-activation-manifest.schema.json` or one versioned stage schema with closed `oneOf` branches for `live_capability` and `p1_activation`.
7. **Exact proposed text/interface:** “The P1 loader MUST validate `.research-system/evals/p1-pilot-coverage.yaml` against `<named schema path and version>`. The `p1_activation` branch MUST require `gate_stage: pilot_promotion`, `evidence_stage: p1_activation`, exactly 11 complete six-field baseline result bindings, exactly 43 activation bindings, the accepted 06f repository path/Git blob/SHA-256, the expected event position, and `additionalProperties: false`. Cross-stage rows, P0 manifests, missing/duplicate/extra obligations, and stale 06f identities MUST be rejected before state change.” Add schema and loader negatives for each case.
8. **Affected decisions/work packages:** D-G6-3; P-035 remediation constraints; WP6.2 T8; `06b` §§5-6; the proposed stage loader and CLI. This does not reopen P-031 through P-034.

### R3-M2 — The P1 descriptor-hash oracle is not independently frozen

1. **ID and severity:** `R3-M2`, **Major**.
2. **Claim:** 06f independently fixes the 54 logical obligation identities, but not the literal descriptor hashes it declares to be expected-side authority.
3. **Evidence:** `implementation/06f-wp6-2-p1-activation-contract.md:9-12` makes 06f the exclusive expected producer; `:41-43` says each activation obligation has a descriptor hash in an accepted semantic copy. The literal rows at `:49-104` contain logical obligations but no descriptor hashes. Lines `:111-117` defer all hashes and binding requirements to a future machine-readable semantic copy without naming its schema, repository identity, producer, reviewer, or acceptor. Lines `:119-126` test changed hashes and expected-set generation from observed rows, but do not require the expected hash producer to be independent of descriptor materialization. `06b:223-227` likewise anticipates a future copy rather than freezing its complete content.
4. **Failure or bypass scenario:** T8 materializes a deficient descriptor, computes the future expected hash from those same deficient bytes, and binds execution to those bytes. Exact expected/observed equality and a simple changed-hash negative both pass because the two sides were correlated at source. A coordinated replacement of descriptor and expected manifest is not presently rejected.
5. **Impact:** The P1 activation evidence can be internally self-consistent but semantically wrong. The suite therefore does not satisfy P-035’s independent expected-source requirement for descriptor identity and cannot support D-G6-3 approval.
6. **Required disposition:** Freeze a strict content-addressed expected manifest containing all 54 complete rows and every literal descriptor hash, accepted before the first observation. Identify its schema/version, repository path, Git blob, SHA-256, producer, independent reviewer, and acceptor. Observed descriptors and executions must not generate, filter, repair, or relabel it.
7. **Exact proposed text/interface:** “Before T8 execution, an owner-accepted `<named manifest>` MUST contain the complete 11 baseline and 43 activation rows, including literal descriptor hashes. Its accepted path, schema ID/version, Git blob, and SHA-256 are immutable expected-side inputs. The descriptor builder, executor, receipts, and live ledger MUST NOT produce or amend the expected manifest. A negative test MUST replace both descriptor bytes and the expected manifest with a self-consistent altered pair and prove rejection before state change.”
8. **Affected decisions/work packages:** D-G6-3; P-035 independent-oracle constraint; `06f` §§2-3; `06b` T8 and §5. R2-M4’s logical-key closure remains closed; R2-M5 is only partially closed until this producer boundary is fixed.

### R3-M3 — Versioned command identity is declared but not independently closed or propagated

1. **ID and severity:** `R3-M3`, **Major**.
2. **Claim:** 06d declares the command identity to be `(command_type, command-schema schema_version)` and claims that identity propagates through authority, dispatch, event, receipt, and idempotency, but its literal expected rows do not pin the per-command schema ID/version/hash and the named downstream interfaces do not carry that identity.
3. **Evidence:** `implementation/06d-wp6-1-owner-source-catalogue.md:14-25` declares versioned command identity and exact-hash registration. Lines `:43-48` say a complete record includes command/event schema IDs and hashes, but the literal rows contain only shorthand schema paths and command types. The future YAML at `:188-203` copies the annex rows and annex identity; it does not name an independent per-command schema-hash manifest. Current `.research-system/schemas/core/command.schema.json:5-10` identifies only the generic command schema; `research_system/schema_registry.py:37-47` loads `$id` but retains no content hash; `.research-system/schemas/core/authority-grant.schema.json:5-12` and `research_system/authority.py:1033-1041` authorize type strings; `research_system/command/service.py:83-93,826-885` uses only type in idempotency/dispatch propagation; and `research_system/command/models.py:38-46` plus `.research-system/schemas/core/receipt.schema.json:5-27` carry no command-schema identity.
4. **Failure or bypass scenario:** A command schema changes version or bytes while retaining the same `command_type`. It inherits old authority, collides in the old idempotency namespace, and produces events/receipts that cannot prove which schema contract was accepted. A future validator can derive both expected and observed schema metadata from the runtime registry and self-confirm the change.
5. **Impact:** The advertised complete-record comparison does not close the versioned identity boundary, so authority, replay, receipts, and idempotency cannot provide the plan’s claimed exact-contract provenance.
6. **Required disposition:** Pin exact schema ID, schema version, and content hash for every command row in an independently owner-reviewed expected manifest. Either propagate that identity through grants, dispatcher registrations, event envelopes, receipts, and the idempotency tuple, or use an equivalently strict version-specific command-type contract.
7. **Exact proposed text/interface:** “Each catalogue row MUST contain `command_schema_id`, `command_schema_version`, and `command_schema_sha256` from an accepted expected manifest that is not generated from the runtime registry. Authority permissions, accepted event envelopes, receipts, and idempotency keys MUST bind the same versioned command identity. A retained-type/changed-version-or-hash mutation MUST reject before event publication.”
8. **Affected decisions/work packages:** D-G6-3; P-035 exact-binding and independent-expected-source constraints; WP6.1 T1/T2; 06a §3; 06d §§1 and 5; command, authority, receipt, schema-registry, and idempotency contracts. No implementation is authorized by this disposition.

### R3-M4 — Twenty-seven catalogue rows omit required semantic authority attacks

1. **ID and severity:** `R3-M4`, **Major**.
2. **Claim:** The `NE` negative profile excludes missing/wrong/expired authority and prohibited-actor cases even though W2 requires actor and authority validation for every command before version, idempotency, state, and write-set checks.
3. **Evidence:** Accepted W2 `design/02-task-event-and-artifact-schema.md:255-269` fixes the validation order with actor/authority at step 4 and no lifecycle event on any failure. `06d:49-62` makes each negative-profile cell its complete applicable set: `NE` is only `N0` plus illegal edge and invalid subject; only `NA` adds missing/wrong authority, expired grant, and prohibited actor. Independent parsing found 27 `NE` rows, including dispatch acknowledgement/expiry (`06d:92,95-97`), lease release/expiry (`:102-103`), adapter delivery/acknowledgement/failure (`:133-135`), blocker resolution/decision expiry (`:137,159`), and W8 heartbeat/resource release (`:174,180`). The current resolver’s closed subject kinds at `research_system/authority.py:39-42` also show that a future row-to-subject-kind mapping cannot be assumed.
4. **Failure or bypass scenario:** A registration advertises the correct authority rule and passes the complete-record presence comparison, while an expired grant, prohibited actor, wrong scope, or wrong authority subject is accepted behaviorally because those mutations are outside the row’s declared complete test set.
5. **Impact:** Authority defects can survive the catalogue’s exact-set test and reach event publication on 27 commands, including lifecycle, adapter, decision, and operator operations.
6. **Required disposition:** Make semantic authority failures part of the base negative profile inherited by every command, and bind every row to an exact authority subject kind and subject-ID source.
7. **Exact proposed text/interface:** “All 104 catalogue rows inherit missing authority, wrong authority, expired grant, prohibited actor, wrong scope, and wrong authority-subject-kind/ID negatives. Each complete row names the accepted subject kind and subject-ID source. Every authority negative MUST leave the event tail, receipt acceptance state, and all projections unchanged.” Add an authority-rule mutation for every row.
8. **Affected decisions/work packages:** D-G6-3; WP6.1 T1/T2; 06d §§1-5; W2 command validation; W8 operator command bindings; authority resolver/grant schema. The W8 token mapping remains owner-pending.

### R3-M5 — `ClaimDispatch` does not close the Task-plus-Dispatch concurrency boundary

1. **ID and severity:** `R3-M5`, **Major**.
2. **Claim:** The remediation proves that one `DispatchClaimed` event changes both projections, but it does not define how `ClaimDispatch` supplies and atomically validates the Task and Dispatch stream identities/versions required by W2.
3. **Evidence:** Accepted W2 `design/02-task-event-and-artifact-schema.md:479` requires expected Dispatch and Task stream versions for claim; `:561` requires an expected version for each affected stream; and `:565-567` requires the complete atomic write set. 06d registers `task.claim_start` and `dispatch.claim` as separate rows sharing `ClaimDispatch`/`DispatchClaimed` (`06d:79,93`) and at `:210-213` requires the one-member event to reduce into both Task and Dispatch, but does not locate the Task ID/version or complete multi-stream write set. The present factory/envelope seam supplies one target and one expected version and an empty claim payload (`tests/research_system/factories.py:149-175,196-210`); the dispatcher emits one attempt-bearing event (`research_system/command/service.py:841-843`); and replay currently updates only Dispatch (`research_system/projection/replay.py:177-196`).
4. **Failure or bypass scenario:** A claim validates the Dispatch stream version while the Task stream becomes stale concurrently. The event is accepted and drives both projections despite never validating the Task-side semantic intent. A dual-projection positive test still passes in a non-racing case.
5. **Impact:** Claim promotion can violate W2 optimistic concurrency and atomicity, producing Task/Dispatch divergence or accepting stale work ownership.
6. **Required disposition:** Either emit an explicit Task-stream event in the same atomic batch or define an exact cross-stream write-set contract containing Task ID/revision/version and prove its validation before publication.
7. **Exact proposed text/interface:** “`ClaimDispatch` MUST bind `dispatch_id`, `expected_dispatch_stream_version`, `task_id`, `task_revision`, and `expected_task_stream_version`. Its accepted batch MUST declare both affected streams and validate the complete write set atomically. A mutation/race that removes or stales only the Task-side binding MUST reject with no event or projection change.”
8. **Affected decisions/work packages:** D-G6-3; WP6.1 T1/T2; 06a lifecycle contract; 06d `task.claim_start`/`dispatch.claim`; W2 §§12-13; command envelope, dispatcher, event batch, replay, and receipt contracts.

### R3-M6 — Correction selector domain and mapping are not independently frozen

1. **ID and severity:** `R3-M6`, **Major**.
2. **Claim:** 06d names a versioned correction-selector interface but does not define the closed `corrected_record_kind` domain or its one-owner-projection-plus-governance-index mapping.
3. **Evidence:** Accepted W2 `design/02-task-event-and-artifact-schema.md:835-841` requires correction events to name affected projections/consumers and reducers to apply only explicit correction semantics. `06d:163` names `projection_selector/corrected_record_kind/v1` and its intended one owner projection plus governance correction index, but supplies no closed enum or kind-to-projection table. The mutation suite at `:206-209` changes/removes selector identity but does not swap mappings, exercise an unknown kind, force zero/multiple owner matches, or omit the governance index.
4. **Failure or bypass scenario:** The future selector registry supplies both the expected mapping and the observed routing. A swapped or incomplete kind mapping self-confirms, and the existing selector-identity mutation does not expose it.
5. **Impact:** Corrections can update the wrong projection, no owner projection, multiple owner projections, or omit the governance index while the catalogue test still reports a valid selector identity.
6. **Required disposition:** Add a versioned closed mapping table to 06d and its semantic YAML, independently accepted before implementation, and compare observed selector behavior against that literal table.
7. **Exact proposed text/interface:** “`projection_selector/corrected_record_kind/v1` MUST enumerate every accepted `corrected_record_kind` and map it to exactly one owner projection plus the governance correction index. Unknown kinds, swapped mappings, zero/multiple owner projections, and a missing governance-index effect MUST reject before publication and leave all projections unchanged.”
8. **Affected decisions/work packages:** D-G6-3; WP6.1 T1/T2; 06d correction row and selector mutation suite; W2 §19; reducer/projection selector and governance-index contracts.

### R3-m1 — F-037/F-038 error-summary cardinality is misstated

1. **ID and severity:** `R3-m1`, **Minor**.
2. **Claim:** One 06b restatement says each failure summary binds all 22 execution hashes, although the suite assigns 12 executions to F-037 and 10 to F-038.
3. **Evidence:** `implementation/06b-wp6-2-live-capability-plan.md:263` says each F-037/F-038 error summary binds “all 22 applicable execution hashes.” Lines `:279-280` define 6 cases × 2 repetitions = 12 for F-037 and 5 × 2 = 10 for F-038. `06f` correctly requires each summary to bind all executions applicable to that fixture.
4. **Failure or bypass scenario:** A literal implementation can require each summary to contain 22 hashes, forcing cross-fixture contamination or making the otherwise valid 12/10 split impossible.
5. **Impact:** Local ambiguity in T8 evidence validation and test expectations; no change to the independently verified combined total of 22.
6. **Required disposition:** Correct the restatement and add a cardinality assertion per fixture.
7. **Exact proposed text/interface:** “The F-037 error summary binds its 12 execution hashes; the F-038 error summary binds its 10 execution hashes; their combined closure is exactly 22.”
8. **Affected decisions/work packages:** WP6.2 T8 and `06b` §5 only; no owner decision changes.

## 4. R2 finding dispositions

| R2 finding | R3 disposition | Independent basis |
|---|---|---|
| R2-M1 — T1b could be compensable/incomplete | **Closed** | `06b:47-63,89-105` requires frozen human rubric/version/hash; blinded positive, negative, ambiguous, and producer-correlated cases; attribution/context; disagreement/adjudication/rubric-revision records; currency/expiry/suspension; separate T1b-M and T1b-H results and independent reviews; and one accepted composite. Model evidence cannot clear H and human evidence cannot clear M. Outer sequence agrees across P-035 `03-decisions...:435-442`, readiness `06:195-202`, and `06b:164-183`. |
| R2-M2 — owner-source catalogue not complete-row exact | **Partially closed; residual defects superseded by R3-M3 and R3-M6** | 06d has 104 unique catalogue rows, 13 W8-owned rows, and 182 expanded concrete edges. It closes command-type ambiguity and demands complete-record multiset comparison, but literal per-command schema identities/hashes and the correction-selector mapping are not independently frozen. |
| R2-M3 — catalogue mutations/enforcement incomplete | **Partially closed; residual defects superseded by R3-M4 and R3-M5** | Missing/duplicate/extra/wrong-owner/wrong-command/alias mutations and cardinality/effect-set checks are now explicit. The complete negative profiles still omit authority attacks for 27 rows, and the claim test checks dual projection effects without closing W2’s atomic two-stream version/write-set contract. |
| R2-M4 — P1 canonical expected keys incomplete | **Closed** | 06f fixes 11 unique baseline six-field keys and 43 unique activation IDs A01-A43; `06b` reproduces the baseline list exactly. Totals are `13 + 22 + 8 = 43` and `11 + 43 = 54`. |
| R2-M5 — expected/observed producer independence | **Partially closed; superseded by R3-M2** | Logical expected sets are independent, and 06e explicitly forbids observed-manifest generation of expected rows. Literal P1 descriptor hashes still lack an independently accepted producer and immutable artifact identity. |
| R2-M6 — 51-row live replacement map absent/inexact | **Closed** | Independent Gate 5 derivation produced exactly the 51 06e predecessors; successors are a complete bijection preserving fields 1-5 and prefixing the complete predecessor variant with `live-capability--`. |
| R2-M7 — stage vocabulary drift | **Closed as vocabulary; new schema gap R3-M1** | All current plan uses preserve closed `gate_stage: pilot_promotion` and carry `live_capability`/`p1_activation` in separate `evidence_stage`. No alias drift was found. The missing P1 schema is a distinct enforcement defect. |
| R2-m1 — non-portable prior-review locator | **Closed** | P-035 citations are repository-relative; cited commits exist and cited report blobs match. No foreign worktree path is used as P-035 authority. |

## 5. Regression audit

| Surface | Result | Evidence/conclusion |
|---|---|---|
| Secret and cost preissue controls | Pass | Remains preissue/fail-closed; no remediation text authorizes live calls or budget bypass. |
| Staged evidence graph | Pass | T1a → T1b-M and T1b-H → accepted composite → live-capability T7 → P1 T8 remains ordered and non-compensable. |
| Live parity at actual seam | Pass | T7 binds actual provider/model/adapter, command, receipt, grant, lease, and event evidence rather than relabelling fake Gate 5 outputs. |
| W4 profile completeness/eligibility | Pass | Exact profile evidence and fail-closed eligibility remain required; same-family/ineligible M substitutions are negative cases. |
| Migration path and writer ownership | Pass | No remediation silently moves writer authority; 06d exposes W8-owned mappings for approval. |
| Decision integrity | Pass | P-031 through P-035 remain controlling; D-G6-2 is open for future hashes; D-G6-3 is pending fresh review and exact-revision owner approval; D-G6-4/5 remain deferred. |
| S-016 and O15 | Pass | No downgrade: S-016 H remains blocked until live capability; O15 remains capability-disabled/deferred to a post-Gate-5 owner decision. |
| Frozen Gate 5 | Pass | 40 fixtures, 15 blocked, 0 fixtures with uncalibrated mutations, calibrated mutation set, 302 results, candidate blocked, `gate5_authorized=false`, O15 disabled/deferred. |
| Approval/dispatch language | Pass | Readiness, 06a, 06b, and 06f continue to withhold implementation and Gate 6 authorization pending a fresh no-Major review and owner approval of the exact revision. |

## 6. Invariant-enforcement-binding-test matrix

| Invariant | Enforcement point named by suite | Required evidence binding | Negative/mutation coverage | R3 result |
|---|---|---|---|---|
| Exact 06d row/key catalogue | strict catalogue loader + reducer/dispatcher registration audit | path, blob, SHA, 104 rows, 13 W8 rows, 182 expanded edges, exact command-type pairs | missing, duplicate, extra, owner/command/alias corruption; unchanged effects/cardinality | Pass for rows/types/counts; incomplete lower-level bindings below |
| Versioned command identity | expected per-command schema identity + authority/dispatch/event/receipt/idempotency propagation | schema ID/version/hash per row and identical downstream binding | retained-type changed version/hash; registry-derived expected values | **Fail — R3-M3** |
| Per-command authority behavior | authority resolver/grant validation before version/state checks | subject kind/ID source, actor, scope, grant, expiry for all 104 rows | missing/wrong/expired grant, prohibited actor, wrong scope/subject | **Fail for 27 `NE` rows — R3-M4** |
| Claim concurrency/write set | command envelope and atomic event batch | Dispatch and Task IDs plus both expected stream versions and complete write set | omit/stale Task-side binding; concurrent Task change | **Fail — R3-M5** |
| Correction selector semantics | accepted closed kind→projection map + selector behavior | exactly one owner projection plus governance correction index | swapped/unknown/zero/multiple/missing-index mappings | **Fail — R3-M6** |
| T1b non-compensation | T1b-M/T1b-H validators + independent reviews + composite acceptance | rubric/version/hash, case/results/evidence, attribution/context, disagreements, adjudication, expiry/suspension, two review identities | model-for-H, human-for-M, omitted class/case, stale/suspended evidence | Pass |
| Gate 5 frozen surface | accepted coverage/variant loaders and release decision | accepted coverage/fixture/variant objects and 302-position result closure | unavailable M/H, O15, unauthorized release remain blocking | Pass |
| 51 live replacements | 06e-exclusive expected map + strict stage loader | 51 complete predecessor/successor rows and actual live identity/command/receipt/grant/lease | omission, duplication, swap, prefix/field/class/provider/scope corruption, expected-from-observed | Pass |
| T7 302-row composite | live-coverage schema + loader relational checks | 251 frozen references + 51 live results; complete-row multiset/bijection | mixed lifecycle, stale/wrong identity, count-only closure, broken bijection | Pass at plan level; implementation must test loader relation, not credit schema alone |
| P1 stage manifest | **no complete enforcement point defined** | proposed 11+43 obligations and 06f identity | prose requires stage rejection but no schema branch fixes the shape | **Fail — R3-M1** |
| P1 logical obligation set | 06f-exclusive expected list | 11 baseline + 43 activation rows; 22 literal executions | missing/duplicate/extra/relabelled/observed-generated logical rows | Pass |
| P1 descriptor hashes | future semantic copy | hashes are promised but not literal or content-addressed | changed-hash case does not defeat coordinated expected+descriptor replacement | **Fail — R3-M2** |
| F-037/F-038 summaries | T8 summary validator | intended 12 and 10 execution hashes | per-fixture cardinality wording conflicts with combined total | Minor — R3-m1 |
| No premature state change | stage loaders/commands | rejection receipt and unchanged grant/lease/task/dispatch/evidence/release sets | all enumerated mutations must reject before transition | Pass in intent; remains an implementation verification condition |

## 7. Expected/observed producer-bypass audit

| Surface | Expected producer | Observed producer | Correlation/bypass assessment |
|---|---|---|---|
| 06d row/key catalogue | accepted content-addressed 06d annex | code registrations, dispatcher/reducer/event/receipt behavior | Separated for the literal rows, types, discriminators, edges, and counts; full-record multiset comparison prevents count-only self-confirmation. |
| Per-command schema identity | no independent literal per-command ID/version/hash manifest | runtime schemas and registry | **Unsafe:** registry can supply both expected and observed schema metadata; downstream type-only bindings cannot distinguish changed schema identity. |
| Authority semantics | row authority-rule label, but 27 rows have a complete profile without semantic authority attacks | resolver/grant/actor behavior | **Unsafe:** declared rule presence can self-confirm while wrong/expired authority behavior remains untested. |
| Claim write-set semantics | W2 accepted design requires two streams; 06d supplies only dual-projection effect prose | command envelope, dispatcher batch, replay | **Unsafe:** a Dispatch-only version check can drive both projections and pass a non-racing positive test. |
| Correction selector map | no literal closed kind→projection map | future selector/registry and projection behavior | **Unsafe:** the same selector producer can define expected and observed mapping. |
| T1a/T1b capability evidence | accepted rubric, case inventory, class protocols, and separate human/model review contracts | model executions, human grading, disagreement/adjudication records | Separated and non-compensable; neither class can manufacture the other class’s clearance. |
| Gate 5 baseline/variant expected bytes | committed fixture expected objects | executor outputs and result events | Separated by current calibration/variant loaders; accepted fake-receipt behavior must not be generalized into live evidence. |
| 06e 51-row replacement map | content-addressed 06e annex plus accepted frozen coverage | live ledger/results at the actual provider/model/adapter seam | Separated; 06e forbids runtime/live artifacts from generating, filtering, repairing, or relabelling expected rows. |
| T7 composite | accepted Gate 5 objects + 06e | 251 frozen references and 51 observed live rows | Separated by entry kind and lifecycle identity; relational loader must enforce the bijection. |
| P1 logical identities | literal 06f logical rows | P1 ledger/execution evidence | Separated for keys and counts. |
| P1 descriptor hashes | unspecified future semantic copy | descriptor builder/executor/receipt path | **Unsafe:** no independent expected producer or accepted exact object; coordinated mutation can self-confirm. |
| P1 manifest shape | no named strict schema branch | proposed loader/CLI input | **Unsafe:** implementer can define the observed and accepted shape together. |

The new R3-M2 negative is essential: mutate the descriptor and expected hash source together, keep the pair internally consistent, and require pre-transition rejection. A one-sided “changed descriptor hash” test is insufficient evidence of producer independence.

## 8. Independent counts, identities, and hashes

### 8.1 Remediation annex identities

| Annex | Git blob | SHA-256 | Canonical bytes | Encoding/line ending |
|---|---|---|---:|---|
| `implementation/06d-wp6-1-owner-source-catalogue.md` | `0aeb547c5f17abfdee4001ff3ae99ce5e92ea366` | `e3a26fc6b1d602fe2ce67d4369b6086774fcd1858b4153165dac97018dbd962f` | 36,834 | UTF-8/LF; no CR bytes |
| `implementation/06e-wp6-2-live-replacement-map.md` | `a187ff6435f0a170bbb894bbb2a94ce97586fa30` | `a65c24624bb309558dd29a779b2db5b1c308b9fcd5caff4b5394e365b77e47b8` | 18,338 | UTF-8/LF; no CR bytes |
| `implementation/06f-wp6-2-p1-activation-contract.md` | `bab91be34fd43207f2a95e388fa56d610b571fd2` | `5d459b6b548837425b243e0cd961569c578d258a2dbce211bd6bd3d7375edd84` | 8,047 | UTF-8/LF; no CR bytes |

### 8.2 Independently reconstructed cardinalities

| Set | Result |
|---|---:|
| 06d unique catalogue rows | 104 |
| 06d W8-owned rows | 13 |
| 06d expanded concrete edges | 182 |
| Gate 5 fixtures | 40 |
| Gate 5 baseline six-tuples | 132 |
| Gate 5 variant six-tuples | 170 |
| Gate 5 total result positions | 302 |
| Unavailable predecessor tuples | 51 = 31 M + 20 H across 15 fixtures |
| Otherwise-available frozen positions | 251 |
| 06e predecessors/successors | 51 unique / 51 unique |
| 06f baseline keys | 11 unique |
| 06f activation obligations | 43 unique |
| 06f literal executions | 22 = 11 `rep-01` + 11 `rep-02` |
| P1 total obligations | 54 = 11 + 43 |

The independently derived unavailable set exactly equals the 06e predecessor set: no missing or extra tuple. Every successor preserves tuple fields 1-5 byte-for-byte and sets field 6 to `live-capability--<complete predecessor variant>`. The per-fixture unavailable distribution is:

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

Accepted Gate 5 provenance is stable at the reviewed head: coverage blob `c1563b725702d8738597e6b25cc3f3061c51226c`, variant-matrix blob `6f2a63c59fcd5a33b0d0f915b1514ba1187fc55d`, and fixtures tree `84acfbdbb72da2e91986142ae6cd1d8806622e36`.

## 9. Contract and test verification

The contract-binding inventory contained 98 contracts. Verification was non-mutating and produced these results:

1. `python .claude/hooks/contract_binding_check.py --validate-only` passed Gates 1 and 2 for all 98 contracts.
2. `python .claude/hooks/contract_binding_check.py --no-pytest` passed Gates 1, 2, and 4, including hardening, for all 98 contracts.
3. The hook’s 95 active binding IDs were independently passed to the system Python pytest runner from the exact target checkout with bytecode/cache writes disabled: **97 passed, 2 warnings, 34.28 seconds**.

The stock outer command was also attempted. `uv run --no-sync` could not import `jsonschema` in its environment. A plain outer invocation reached the hook but its nested `uv run pytest` attempted dependency synchronization and failed while building `petls==1.0.1` because of scikit-build-core configuration. These are environment/toolchain failures before test execution, not contract failures; they are recorded rather than hidden. The exact-target checkout remained clean after verification.

## 10. Decision and owner-authority audit

| Decision | R3 treatment |
|---|---|
| P-031 to P-034 | Preserved; no remediation prose silently reopens or changes them. |
| P-035 | Preserved as the governing remediation/approval constraint; its prior-review citations are portable and object-valid. |
| D-G6-2 | Remains open for future exact hashes; this review does not manufacture them. |
| D-G6-3 | **Not approvable at `3cca017c…`** because R3-M1 through R3-M6 are open. |
| D-G6-4 / D-G6-5 | Remain deferred; no implementation/live/owner action is inferred. |
| W8 owner-source mappings | Correctly surfaced as pending owner approval; the review does not choose or enact them. |
| Gate 6 / WP6 dispatch | Not authorized. Stephen’s exact-commit approval remains necessary after a no-Critical/no-Major re-review. |

No owner decision was made, enacted, or simulated by this review.

## 11. Practicality and proportionality

All six Major remediations are bounded plan-level work and are cheaper to resolve before implementation:

- R3-M1 requires naming and specifying a strict schema branch plus its negative-test matrix; it does not require building the loader now.
- R3-M2 requires freezing the expected descriptor-hash manifest and its independent acceptance boundary; it prevents a much more expensive post-execution provenance dispute.
- R3-M3 requires a literal expected schema-identity manifest and a precise downstream propagation decision; resolving it now prevents incompatible authority/idempotency/receipt implementations.
- R3-M4 requires making the base negative profile inherit W2 authority attacks and adding exact subject bindings; it does not require executing those tests now.
- R3-M5 requires choosing and specifying one W2-conformant two-stream concurrency/write-set interface; it avoids entrenching a Dispatch-only envelope.
- R3-M6 requires a closed correction-kind mapping and mapping mutations; the domain is small and belongs in the pre-implementation expected set.

Neither finding demands live calls, a broad redesign, or premature implementation. The Minor fix is a one-line semantic correction plus a per-fixture assertion. The required assurance is proportional to the fact that these artifacts are intended to authorize stateful and live-capability work.

## 12. Residual risks after remediation

Even after all six Major findings are closed, the following remain legitimate future verification risks rather than current plan defects:

- T1a, T1b-M, and T1b-H evidence and their independent reviews do not yet exist and must not be inferred from plan completeness.
- W4 profile eligibility and live provider/model/adapter behavior remain empirical execution-time claims.
- The stage schemas, loader, CLI, receipts, and relational multiset/bijection checks remain unimplemented and require contract-first tests.
- The command-schema identity, authority subject mapping, multi-stream claim batch, and correction-selector design remain unimplemented; after the plan closes R3-M3 through R3-M6, implementation review must verify the actual propagation and races rather than credit interface names alone.
- JSON Schema conditionals alone cannot generally prove cross-row bijection; implementation review must inspect the loader’s relational check.
- W11 and later authorization remain outside this review.
- Every future approval review must reverify the exact `HEAD`, parent, branch, object hashes, and clean state; content similarity is not exact-revision identity.
- The accepted fake Gate 5 receipt-reference path must remain fenced from live evidence, where expected identity requires a separately accepted producer.

## 13. Exact dispatch conditions

The reviewed suite remains non-dispatchable. A successor exact revision may become eligible for owner consideration only when all of the following are true:

1. R3-M1 is closed with a named, strict P1/stage schema and complete negative tests.
2. R3-M2 is closed with an independently produced, reviewed, accepted, content-addressed 54-row descriptor-hash manifest and coordinated-pair mutation test.
3. R3-M3 is closed with independently frozen per-command schema identities and an exact authority/dispatch/event/receipt/idempotency propagation contract.
4. R3-M4 is closed by applying the semantic authority attack set and exact subject binding to all 104 catalogue rows.
5. R3-M5 is closed with a W2-conformant atomic Task-plus-Dispatch version/write-set contract and Task-side omission/staleness race tests.
6. R3-M6 is closed with an independently frozen correction-kind mapping and the full selector-mapping mutation set.
7. R3-m1 is corrected to the exact F-037=12, F-038=10, combined=22 contract.
8. Every closure credited in §4 and every frozen Gate 5 invariant in §5 remains intact.
9. The complete expected/observed producer separation and pre-transition no-state-change mutations remain explicit.
10. Contract validation and the binding suite pass against the successor exact objects, with any environment exception disclosed.
11. A fresh independent adversarial review of that exact revision reports no open Critical or Major finding.
12. Stephen explicitly approves that exact commit.

Until all twelve conditions are satisfied, do not dispatch WP6, authorize Gate 6, perform live provider calls, mutate research-system state, or enact an owner decision.

## 14. Evidence and change log

- Reviewed target: exact clean branch/worktree named in §2; read-only throughout.
- Review method: direct full-file review, accepted-design cross-check, exact Git-object/hash verification, independent set reconstruction, producer/bypass analysis, and non-mutating contract execution.
- Mutations considered: missing/duplicate/extra/stale rows; owner/command/alias corruption; predecessor/successor swaps; prefix/field/class/provider/model/adapter/scope corruption; mixed lifecycle; expected-from-observed derivation; one-sided hash changes; and the newly required coordinated expected-manifest-plus-descriptor replacement.
- Repository change produced by this task: this R3 review report only, in the authorized current checkout.
- Reviewed target changes: none.
- Implementation, live calls, state mutation, owner decisions, WP6 dispatch, and Gate 6 authorization: none.
