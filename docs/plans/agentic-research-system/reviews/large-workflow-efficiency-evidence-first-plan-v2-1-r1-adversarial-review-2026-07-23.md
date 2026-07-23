# Fresh Focused Adversarial Review: Evidence-First Large-Workflow Improvement Plan v2.1 R1

- **Date:** 2026-07-23
- **Workflow system:** standalone; APM skills, state, Memory Bank, guides, and
  checkers were not used
- **Supervision phase:** certify
- **Lifecycle phase:** `focused_plan_review_v2_1_r1`
- **Reviewer task:** `019f8c84-6d2a-7782-a8de-352b06e6f382`
- **Dispatch source task:** `019f8954-d0cc-7d12-ae83-e8ccb8b61165`
- **Primary skill:** `adversarial-design-review`
- **Meta-skill:** `research-observer`; its OPEN observations and principles were
  read, but its log was not changed because this task authorizes only this report
- **External review:** none; CodeRabbit remained Stephen-owned and was neither
  triggered nor polled

## 1. Exact subject and direct-source identities

The review began detached. Before the one permitted attachment, detached `HEAD`,
the local review branch, the tracking ref, and the live remote branch all resolved
to the required commit. The deterministic same-commit switch then succeeded, and
the checkout was clean on the required symbolic branch.

| Object | Exact identity | Independent verification |
|---|---|---|
| Reviewed v2.1 commit | `80cc1b4472fc04d897f526201b485973c438ee5b` | local and live remote branch equal |
| Reviewed v2.1 tree | `97b26adeab024977cfd7709b2076c83c87144587` | recomputed from commit |
| Reviewed path | `docs/plans/agentic-research-system/proposals/large-workflow-efficiency-evidence-first-plan-v2-1-2026-07-23.md` | read from the exact commit |
| Reviewed blob | `3a8a228d374a42f531b0c4f1a8e534c9eb4428e0` | recomputed from commit/path |
| Reviewed raw SHA-256 | `79d2920307ca3f998d31926cdddcd801066eac4ddd9b5243295ccdb875902b25` | recomputed over 37,970 Git-blob bytes |
| Required review branch | `review/wp6-efficiency-evidence-first-v2-1-r1` | attached only after exact equality check |
| Amendment base/direct parent | `ec1e6ff5e01ee3235449c459e0c80ed97feb13c5` | recomputed from reviewed commit |

The direct v2 review was resolved from its Git object rather than from v2.1's
summary:

| Object | Exact identity | Result |
|---|---|---|
| V2 R1 review commit/tree | `ec1e6ff5e01ee3235449c459e0c80ed97feb13c5`; `641e148337aaaf89a9f403b077855b6bb6980a69` | exact match; direct parent |
| V2 R1 review report | `docs/plans/agentic-research-system/reviews/large-workflow-efficiency-evidence-first-plan-v2-r1-adversarial-review-2026-07-23.md` | read in full |
| V2 R1 review blob/raw SHA-256 | `649f7f86330d3d7a01a2ec26be2df0b30ff05994`; `11d73f9ada1d077f81431514808a26c3df2204e7cda5f1dbef8839adf83bcc7b` | recomputed over 48,404 bytes |
| V2 R1 reviewer/verdict | `019f8c70-ba2f-7a61-9a14-f85d4d00fa0d`; `rework_required` | 0 Critical, 6 Major, 2 Minor |

The other supplied historical objects also matched:

| Source | Commit/tree | Blob/raw SHA-256 | Use in this review |
|---|---|---|---|
| Original v2 subject | `7c28419bf0a839a0cb2d06d726bbe88dfc228873`; `411e5a36399ea5ea15e0620b715499ba40450dc0` | `2ee2c5c380d335e1341698d04569b969fd1bdbe6`; `02b5e1ab0de523fa7f2d97e226742d540b1cf21db799bef269e6f7ba0fcc8258` | read in full to test the v2-review findings against their subject |
| R1-plan review | `b32a2253a51c56d08dc509be47730c1f1f96d453`; `61d6633056d0990d195b0fa3cef260c7ee167ce1` | `e0d7624a63fa41d0c0bab0397a2069d008cd6399`; `7199a7b49bc0ee2de6563209ec4b1c5ec52f90605a415af856b5177063eaa3cd` | 0 Critical, 7 Major, 3 Minor; finding and action registers checked |
| Historical-programme review | `3f5f65ca698b083b117c50fa84f9ec908ef83839`; `54dadecc08291424ffa78c4e5f28a152eb804167` | `dddc5d2c7f22cb7dc0fc04752e7ae9f5c63a441d`; `b62d1346505adb56d24301410d094290120a7df362c8628f49f83505bdae3bd0` | 0 Critical, 5 Major, 3 Minor; findings, interventions, invariants, and decision audit checked |

Current global and repository `AGENTS.md`, the authoring sources for
`tda-large-workflow-supervision`, `tda-task-brief-from-plan`, and `tda-handoff`,
the supervision guide, P-039, P-040, and the completed-cycle assessment were read
directly. The accepted T2 candidate independently resolved to tree
`0254c5416925126412867d61b3045ee1563abd0c`, direct parent
`bba49c11ef8cd37dee7fa571f712d77a954f6b16`, and 27 changed paths. Its R3 review
commit `655f4173db93447a068adc6e92621455c4abc85d` is a direct one-report child of
the accepted candidate; the report blob and raw SHA-256 independently matched
`1ad44c1f79ea9738f8ff5e2369bab3a32b4f940d` and
`17906c4ae1916840dfe94aab3f5991d17e8037940802ec1338c49b53f9506fd8`.

## 2. Executive verdict

**Verdict: `rework_required`.**

**Severity counts:** 0 Critical, 3 Major, 0 Minor.

V2.1 materially improves v2. It independently closes the campaign and semantic-
validation sets, supplies rooted same-handle telemetry acquisition, preserves
always-loaded rules with semantic fixtures, holds PR #157 away from `main`, makes
C0 independent of PR B, records structural skill/wait fields, and places a real
claim-specific gate before any quantitative or causal statement.

Three implementation-boundary defects remain. First, the Phase 1 and Phase 2
closing records are required to contain identities that do not exist until after
those same records are frozen and merged. Second, the telemetry contract binds
metrics to stable bytes but never normatively defines how the emitted metrics are
derived from admitted records. Third, the drain machine has no closed state for a
mutating process that remains alive or escapes its launcher after compaction. Each
can make a phase look closed while authority, evidence semantics, or residue is
still unresolved. No Critical is warranted because this remains a proposed plan,
the plan forbids implementation while a Major remains, and no candidate, PR, or
accepted artifact is changed by this review.

## 3. Critical findings

None.

## 4. Major findings

### MAJ-01 - Phase 1 and Phase 2 closure require self-referential or not-yet-existing identities

1. **ID and severity:** MAJ-01, Major.
2. **Claim:** The common phase-closing record must contain the exact required-
   artifact inventory, subject paths/blobs/raw hashes, and package merge commits.
   The Phase 1 and Phase 2 acceptance records are themselves required artifacts
   and are also named as the closing records. Their own final identity and the
   resulting C0/C1 merge commit cannot exist before their bytes are frozen, so the
   specified close is either circular or ordered after an unauthorized merge.
3. **Direct evidence:** V2.1 section 4 requires every closing record to contain
   subject paths/blobs/raw hashes, a required-artifact exact set, the owner
   decision, and package merge commits (reviewed plan lines 88-107). Section 4.1
   includes the Phase 1 and Phase 2 acceptance records in the required path sets
   (lines 118-132). The executable table makes those same files the closing
   records and also requires C0/C1 merge commits (lines 150-156). No separate
   pre-merge acceptance and post-merge integration receipt is defined. P-040
   demonstrates the non-circular pattern the plan should preserve: immutable
   candidate bytes are accepted by a distinct external decision record, and a
   later integration action still requires separate authority
   (`reviews/wp6-2-t2-r3-owner-acceptance-2026-07-22.md`, lines 49-83).
4. **Concrete failure scenario:** Stephen signs the Phase 1 acceptance record
   before C0 merges. Its `package_merge_commit` is unknowable and its own blob is
   absent from the completed exact-set inventory. If C0 merges first, unaccepted
   material reaches the integration target. If the acceptance record is amended
   after merge to add the merge identity, the exact owner-accepted bytes change
   and the named C0 merge no longer contains the final closing record. The same
   cycle repeats for C1 and any conditional global-state record.
5. **Impact:** Authority and provenance can deadlock, be self-attested, or be
   reported green only by mutating an accepted record. Different actors can also
   disagree whether acceptance, merge, or the post-merge record actually closes
   the phase.
6. **Recommended disposition:** Fix now. Retain exact external lifecycle records,
   but split the pre-merge owner act from post-merge integration evidence.
7. **Exact proposed change:** Replace the Phase 1/2 closing rule with:
   "A pre-merge owner-acceptance record binds the immutable package candidate
   commit/tree, every non-self required artifact identity, the independent report,
   and the explicit merge authorization. After integration, a provenance-only
   integration receipt binds that acceptance record, the resulting merge commit,
   base, and reachability checks. The phase closes only when both records exist.
   Neither record is required to contain its own blob/hash; its containing commit
   and delivery handback bind that external identity." Add one exact receipt path
   for C0 and one for C1. This is the smallest adequate control; do not create a
   record per sub-section or per fixture.
8. **Affected decisions/packages:** sections 4, 4.1, 5, 11, 12.2, 12.3, 14, 16,
   and 17; Phase 1/C0, Phase 2/C1, conditional global changes, and the final
   integration head.

### MAJ-02 - The telemetry contract freezes bytes but leaves every metric derivation open

1. **ID and severity:** MAJ-02, Major.
2. **Claim:** V2.1 defines safe acquisition and an exhaustive output field class,
   but it does not define the admitted structural record versions, source fields,
   units, aggregation formulae, cumulative-versus-delta semantics, reset/dedup
   behavior, or unknown rule for any emitted metric. Stable bytes can therefore
   produce a schema-valid but semantically wrong baseline.
3. **Direct evidence:** The same-handle algorithm says only to "parse structural
   allowlisted records, and derive metrics" (lines 234-249). The output schema
   lists cached/uncached input, output, peak input, calls, compactions,
   truncations, duration, and wall span (lines 254-272), while the fixtures cover
   acquisition/error cases rather than a normative derivation table (lines
   274-284). Campaign duplicate-cumulative treatment is required (lines 166-181),
   but no formula connects it to an output metric. The Phase 1 gate likewise names
   the acquisition/output contract and fixture verdicts without requiring metric-
   formula closure (lines 152-154). This omission reopens the exact mechanism
   behind historical H1/H4 and R1-plan MAJ-01: inconsistent event cuts and
   cumulative-event treatment produced plausible but incompatible totals.
4. **Concrete failure scenario:** One implementation sums cumulative `token_count`
   records, while another takes only the final value; both use the same frozen
   prefix and emit permitted integer fields. A reset or duplicate cumulative event
   is counted differently, peak input is taken from a session total rather than a
   call, and task duration is confused with wall span. Both outputs pass the
   current structural schema and byte-revalidation checks.
5. **Impact:** Evidence fidelity, comparison validity, and Phase 4 conclusions are
   material. A stable digest would misleadingly strengthen a metric whose semantic
   derivation remains producer-defined. The protected research asset is the
   provenance and validity of efficiency evidence; no cybersecurity expansion is
   needed.
6. **Recommended disposition:** Fix in the existing Phase 1 evidence contract
   before any corrected baseline is accepted.
7. **Exact proposed interface:** Require one normative row per emitted metric:
   `metric_id | admitted_record_type_and_version | source_fields | unit |
   formula | cumulative_delta_reset_semantics | duplicate_rule |
   missing_unknown_rule | overflow_or_invalid_rule | positive_negative_fixtures`.
   Require exact-set closure between emitted metrics and these rows. Unsupported
   versions and absent structural evidence become `unknown` or a closed error,
   never an inferred zero. Add small synthetic fixtures for cumulative, delta,
   reset, duplicate, missing, and incompatible-version cases. This changes the
   already-required contract and catalogue; it requires no parser or live JSONL
   run now.
8. **Affected decisions/packages:** sections 5 Phase 1, 6, 8, 12.2, 13, 15
   MAJ-03 disposition, 16, and 17; corrected baseline manifest, Phase 1 fixtures,
   Phase 3 preregistration, and Phase 4 assessment.

### MAJ-03 - The drain machine has no closed state for a still-running mutating process

1. **ID and severity:** MAJ-03, Major.
2. **Claim:** The four drain states close clean, completed-dirty, bounded read-only,
   and incomplete-interpretation cases, but not a writer/test/helper that remains
   alive, times out while a child survives, or continues holding a lock. Saying
   the process is "allowed only to return" neither bounds it nor prevents a
   successor from racing its residue.
3. **Direct evidence:** The state table contains only `clean_safe_point`,
   `read_only_atomic_in_flight`, `mutation_completed_unverified`, and
   `interpretation_or_draft_incomplete` (lines 297-305). Lines 307-309 say a
   write/process still executing may return and is classified afterward, but
   define no timeout, process identity, liveness check, cancellation authority,
   lock/target inventory, or state when it does not finish cleanly. The neutral
   handback inventory names dirty/untracked/ignored bytes, not live processes or
   open mutation ownership (lines 315-320). The prohibition on starting another
   action (lines 311-313) can also prevent the old task from taking an otherwise
   necessary explicit termination action.
4. **Concrete failure scenario:** A shell launcher times out after spawning a child
   that continues rewriting a generated artifact or holding a lock. The old task
   records a dirty snapshot and stops. A successor sees
   `mutation_completed_unverified`, begins inspection or validation, and races the
   still-running child; later bytes differ from the handback digest and cleanup
   ownership is unknown.
5. **Impact:** Deterministic recovery, provenance, concurrency safety, and the
   promised no-hidden-continuation boundary can fail. The likely operational costs
   are duplicated work, a poisoned validation cut, locked residue, or accidental
   commit of bytes that changed after capture.
6. **Recommended disposition:** Amend the state machine before it becomes
   normative. Preserve the ban on new semantic work.
7. **Exact proposed change:** Add `mutation_or_process_in_flight`. At the trigger,
   the old task may only await the already-running tool call for a predeclared
   bounded interval and capture launcher/child identity, target/lock scope, last
   known status, and residue owner. A successor may not mutate, validate, clean,
   or rely on affected bytes until read-only liveness and byte checks prove the
   process ended. If termination or cleanup requires a new action, return Partial
   and require Stephen or the pre-named rollback owner to authorize that exact
   action. A launcher timeout never maps to `mutation_completed_unverified` while
   a child may still be live.
8. **Affected decisions/packages:** sections 5 Phase 2, 9, 10 fixture 4, 12.3,
   12.4 false-stop/residue measures, 15 MAJ-04 disposition, 16, and 17; canonical
   supervision and handoff semantics.

## 5. Minor findings

None.

## 6. Complete v2-review-finding-to-v2.1 closure audit

| V2-review finding | Independent v2.1 result | Evidence and disposition |
|---|---|---|
| MAJ-01 - executable phase gates and completion | **Not closed; MAJ-01** | Artifacts, roles, acceptors, fail states, completion, and Phase 5 separation are now explicit, but the merging-phase close is self-referential |
| MAJ-02 - producer-defined campaign/validation sets | **Closed** | Sections 3, 6, and 7 separate the bar, producer, independent reconstruction, exact-set comparison, and Stephen acceptance; the pilot cannot redefine membership |
| MAJ-03 - telemetry path/stable bytes/output/errors | **Not closed; MAJ-02** | Root authority, final identity, one-handle/two-digest revalidation, exhaustive field classes, sanitized errors, and platform fixtures are present; normative metric derivations are absent |
| MAJ-04 - dirty/read/interpretive drain states | **Not closed; MAJ-03** | Clean, read-only, completed-dirty, and interpretive states are closed; a live mutating process is not |
| MAJ-05 - load-order and compaction survival | **Closed** | Section 10 defines the always-loaded semantic capsule, load points, reload trigger, ownership-map fields, five semantic negatives, and no-removal gate |
| MAJ-06 - PR #157/PR B/C0/C1 topology | **Closed at plan level** | PR #157 is held and gets one of two owner dispositions; provisional merge is rejected; C0 precedes C1 and is independent of PR B; Phase 3 binds one head containing all three merges |
| MIN-01 - skill identities and wait classes | **Closed** | `loaded_skill_identities` includes bytes or `unknown`; wait classes are closed and include `unknown`; absence is never zero |
| MIN-02 - claim-specific later design gate | **Closed** | Section 13 requires an independently reviewed/accepted protocol with estimand, unit, assignment/matching, equivalence, strata, carryover, missingness, analysis, stopping, multiplicity, and uncertainty |

The plan's own section 15 table is therefore not accepted by self-attestation:
three rows overstate closure, while five withstand independent reconstruction.

## 7. Earlier-review regression audit

| Earlier finding or decision | V2.1 treatment | Regression result |
|---|---|---|
| R1 MAJ-01 / historical H4 - non-atomic, misclassified baseline | Dated addenda, exact campaign contract, frozen corrected manifest | **Preserved direction; derivation gap remains under MAJ-02** |
| R1 MAJ-02 / historical H1 - unmeasured numeric stop | Withdraws 80k and quantitative claims; observable compaction/counter only | **No regression** |
| R1 MAJ-03 - preflight/lease substitutes mechanics for authority | Observer and workflow selector precede discretionary skills; reusable lease rejected | **No regression** |
| R1 MAJ-04 - generic validation reuse | Generic reuse remains prohibited absent a separately accepted hermetic class | **No regression** |
| R1 MAJ-05 - author-defined review bundle | Git facts remain non-authoritative; all required sets are independently reconstructed | **No regression** |
| R1 MAJ-06 / historical H3/H8 - multiplied normative surfaces | One canonical skill, minimum semantic AGENTS capsule, pointer surfaces, semantic fixtures | **No regression** |
| R1 MAJ-07 - unsafe telemetry scope/snapshot/errors | Explicit root, final identity, stable prefix, closed errors, bounded fixtures | **Path/privacy regressions closed; MAJ-02 is a remaining evidence-semantics gap** |
| R1 MIN-01 - PR B undefined | PR B is the T2 integration PR with exact required ancestry/merge fields | **No regression; live identity remains unavailable as declared** |
| R1 MIN-02 - stale PR path count | Recount before create/update/merge, target 90, stop before 100 | **No regression** |
| R1 MIN-03 - rollback/residue owner | Every phase/package names rollback and residue ownership | **No regression, except live-process residue under MAJ-03** |
| Historical H2 - no causal estimate | One pilot is descriptive; separate accepted protocol required | **No regression** |
| Historical H5 - research-value and second-cycle controls late | P-039 six-field gate and owner rescope remain always loaded | **No regression** |
| Historical H6 - avoidable detached stops | One same-commit deterministic switch retained | **No regression; this review exercised it** |
| Historical H7 - skill/no-poll self-report | Structural skill identity/bytes and wait-class/unknown fields added | **No regression** |
| Historical intervention decisions | Lease/cache/author-exhaustive manifest/numeric threshold remain rejected; checker, lock, observer migration, model routing, external utility, and reuse remain deferred | **All preserved** |

## 8. Complete v2.1 decision and action audit

The rows below cover every normative action or grouped inseparable contract in
v2.1. Each row names the credible downside, bearer/timing, and whether the plan's
mitigation is adequate.

| ID | Decision/action | Negative consequence, bearer, and timing | Disposition and mitigation adequacy |
|---|---|---|---|
| A01 | Immutable v2.1 replacement plus fresh exact review | Extra review/read cost for reviewer and Stephen now | **Keep.** Direct-subject review is the cheapest independent closure and found material gaps |
| A02 | Hold PR #157; choose amend or close/supersede; reject provisional merge | Delays advisory integration; PR owner bears it at Phase 0 | **Keep.** Prevents known-refuted rules reaching `main`; rollback is simply continued hold/closure |
| A03 | Preserve assurance floor and withdraw 80k/30%-45%/50% claims | Lost ability to advertise a saving; programme owner now | **Keep.** Correct evidentiary consequence, not a cost defect |
| A04 | Retain exact state/review/P-039/certify-first; reject lease/cache/author-manifest/universal threshold | Continued review and identity-check overhead on every large campaign | **Keep.** Evidence supports the assurance benefit; rejected mechanisms cost more than their likely saving |
| A05 | Producer/reviewer/acceptor role separation | More handoffs and Stephen decisions per phase | **Keep.** Necessary against self-definition and self-acceptance; one reviewer and one owner act per phase are sufficient |
| A06 | Common exhaustive phase-closing record | Repeated identities and impossible self/merge references; record author and acceptor at every close | **Amend per MAJ-01.** Use pre-merge acceptance plus post-merge receipt only where a merge exists |
| A07 | Freeze 19 mandatory artifact paths plus one conditional path | Rename/date rigidity and maintenance burden for all phase owners | **Keep with A06 amendment.** The paths represent distinct contract/review/decision roles; do not split sub-sections further |
| A08 | Phase 0 exact review, finding closure, and PR #157 owner disposition | Owner throughput and possible new exact subject | **Keep.** Required before any authority; review alone grants nothing |
| A09 | Phase 1/C0 addenda, campaign contract/manifest, telemetry contract/fixtures, review, acceptance | Largest specification burden falls on evidence producers/reviewer before behavior | **Amend per MAJ-01/02.** Existing grouping is otherwise the smallest adequate evidence package |
| A10 | Phase 2/C1 ownership map, packet/drain/validation contract, semantic fixtures, review, acceptance | Migration, prompt drift, and false-stop risk for all later tasks | **Amend per MAJ-01/03.** Semantic fixtures and rollback to the last accepted capsule are otherwise adequate |
| A11 | One complete advisory Phase 3 pilot | Research time, fragmentation, and opportunity cost after integration | **Keep.** One complete package is proportionate; startup-only or contract fragments cannot claim success |
| A12 | Phase 4 descriptive decision completes plan; Phase 5 separate | Three more decision artifacts and delayed tooling | **Keep.** Cleanly prevents pilot evidence from self-activating enforcement |
| A13 | Independently reconstructed campaign required set | Discovery/classification duplication for producer and reviewer in Phase 1/3 | **Keep.** Exact closure is necessary against selection bias; reuse the accepted contract rather than rediscovering the bar per assessment |
| A14 | Independently reconstructed semantic-validation set | Mapping/review cost before C1 and pilot | **Keep.** Derive once from accepted obligations and update only on exact dependency delta |
| A15 | Opaque root registry, final identity, containment, literal-path override | Windows implementation effort and false rejection of unusual layouts | **Keep.** Owner override plus fail-closed identity is the cheapest adequate privacy/provenance control |
| A16 | One-handle stable prefix and two digest passes | Approximately doubles prefix I/O; evidence owner at each acquisition | **Keep.** Bounded offline I/O is proportionate to active-file stability |
| A17 | Exhaustive output/error schema and synthetic fixture catalogue | Schema/fixture maintenance before any parser exists | **Amend per MAJ-02.** Add derivation rows inside this contract; do not add live probes or another tool |
| A18 | Telemetry security boundary excludes secrets/scans/provider/network work | Residual runtime leakage questions remain deferred to actual runtime owners | **Keep.** P-039 places that evidence at the correct stage |
| A19 | Compaction as observable hard trigger; no unsupported token threshold | False rotation and duplicated context at runtime compaction | **Keep.** Pilot records false stops; no lower numeric claim is made |
| A20 | Four-state drain machine | Live-process residue can outlast the captured state | **Amend per MAJ-03.** Add one process-in-flight state and bounded liveness barrier |
| A21 | Neutral handback plus Stephen-only predeclared exception | Handback burden and Stephen bottleneck at rare exceptional triggers | **Keep.** Identity-only packet and one maximum operation bound the cost |
| A22 | Invariant ownership/load-order map | Map upkeep for workflow-method owner in C1 | **Keep.** One map is cheaper than divergent prose and enables semantic fixtures |
| A23 | Minimum always-loaded semantic capsule and post-compaction reload | Some prompt bytes remain permanently loaded | **Keep.** Every listed rule is needed before selection/write or at the drain trigger; pointer-only would be unsafe |
| A24 | Five semantic negative fixtures; no safety-text removal before pass | Scenario maintenance and possible false failures during C1 | **Keep.** Semantic outcomes, not literal self-checks, are the adequate preservation test |
| A25 | PR #157/C0/C1/PR B DAG and final integration head | Stack coordination and final-seam review for integrator | **Keep.** C0 is not delayed by PR B; known-refuted #157 cannot merge unchanged; owner records still authorize actual dispatches |
| A26 | C0 is evidence-only, no parser/threshold/instruction/gate | Defers convenience tooling and behavior correction until evidence is accepted | **Keep.** Prevents evidence semantics being defined by the behavior they justify |
| A27 | C1 consolidates only rules/pointers/contracts; no checker/cache/lease | Manual compliance remains and migration still costs prompt/review time | **Keep with A10/A20 amendments.** Correct advisory scope |
| A28 | Pilot preregistration binds sets, roles, integration, and descriptive burden measures | Up-front preregistration and closeout work for pilot team | **Keep.** It cannot redefine accepted sets and explicitly records adverse costs |
| A29 | Separate claim-specific evaluation protocol | Potential multi-package study cost for research programme later | **Keep optional.** The claim is prohibited unless its value justifies that cost |
| A30 | C0/C1 separation, 90 target/100 stop, global changes separate | More PRs, merge coordination, backups, and rollback records | **Keep.** External limit and global-state boundary are real; count at create/update/merge only |
| A31 | Optional Phase 5 only after recurring evidence and separate owner gate | Delayed automation; later tool owner bears negatives/positive-signal upkeep | **Keep deferred.** No present evidence supports activation |
| A32 | Forward obligations and hard stops | Repeated checklist cost for dispatchers | **Keep with three Major amendments.** The list otherwise captures PR, set, assurance, review, path-cap, claim, and activation boundaries |

## 9. Invariant -> owner/load point -> evidence/test matrix

| Invariant | Owner and load/enforcement point | Evidence/test required by v2.1 | Review result |
|---|---|---|---|
| Standalone never loads APM machinery | Global/repository AGENTS before state; canonical skill | Wrong-workflow semantic fixture | **Closed** |
| Observer activates before task work | Always-loaded AGENTS before discretionary skills | Omitted-observer/skill dispatch behavior | **Closed for design** |
| Exact root/branch/HEAD/scope precedes mutation | Always-loaded capsule and writer | Wrong-root/branch/HEAD/scope fixture plus live pre-write check | **Closed** |
| Producer cannot define and close its own bar | Accepted plan/contract; Stephen; independent reviewer | Separate roles and exact-set reconstruction | **Closed** |
| Phase acceptance is externally durable and non-circular | Stephen and phase-closing records | Candidate, report, acceptance, merge identity | **Open: MAJ-01** |
| Campaign set is complete | Accepted Phase 1 campaign contract and reviewer | Independent seed-free reconstruction; missing/extra/duplicate/stale checks | **Closed** |
| Validation set covers every accepted obligation/dependency | Accepted validation contract and reviewer | Independent exact-set reconstruction and every graph-required gate | **Closed** |
| Metrics derive from exactly the frozen bytes | Phase 1 telemetry contract | Same-handle digest/metric pass plus digest-only replay and identity recheck | **Closed for byte binding** |
| Metric meanings are producer-independent | Phase 1 metric contract | Exact derivation rows and semantic fixtures | **Open: MAJ-02** |
| Telemetry emits no content or raw path | Phase 1 output/error contract | Closed fields/errors; content rejection; platform/path fixtures | **Closed at specification level** |
| Compaction starts no new semantic work | Always-loaded capsule and drain section | Four-state fixtures and successor revalidation | **Open for live process: MAJ-03** |
| Consolidation cannot hide a safety rule | AGENTS capsule, canonical skill, authority map | Five semantic negative fixtures on every proposed surface | **Closed** |
| CodeRabbit remains Stephen-owned | Always-loaded global/repository AGENTS | Undelegated trigger/wait fixture | **Closed** |
| Existing deterministic artifacts are certified first | Task owner at every stage transition | Exact identity/byte comparison before regeneration | **Closed** |
| Known-refuted PR #157 rules cannot reach `main` | Stephen Phase 0 disposition | Live-head record; amend-and-review or close/supersede only | **Closed at plan level** |
| Accepted T2 candidate survives integration | P-040, Stephen, PR B integration owner | Candidate/review/acceptance ancestry and merge reachability | **Closed pre-integration; PR B remains absent** |
| C0 evidence semantics precede C1 rules | C0/C1 integration owners | C0 merge/receipt before C1 candidate acceptance and final seam | **Direction closed; record ordering needs MAJ-01** |
| One pilot cannot activate a mandatory mechanism | Phase 4 owner and separate Phase 5 gate | Allowed Phase 4 decision enum; later owner record and watched negative | **Closed** |
| Quantitative/causal claims require adequate design | Stephen and independent protocol reviewer | Claim-specific preregistration fields and acceptance | **Closed** |

## 10. Bureaucracy, negative consequences, and proportionality

The exact path table creates 19 mandatory artifacts over Phases 0-4, plus one
conditional global-system record. That is substantial for one advisory pilot, but
most files have distinct jobs: historical addendum, machine-readable manifest,
contract, independent report, preregistration/assessment, or owner decision. The
plan already avoids a file per small rule by placing campaign/telemetry/fixtures in
the Phase 1 contract and ownership/packet/drain/validation/fixtures in the Phase 2
specification. That consolidation should be preserved.

The omnibus closing-record design is the one place where compression exceeds safe
semantics. The smallest adequate correction is not a larger registry or checker: it
is one immutable pre-merge acceptance record and one post-merge receipt for each of
C0 and C1. Those two extra receipts are justified because they remove both the
self-reference and the temptation to merge before acceptance. Their owner is the
integration owner; the burden appears once per package; rollback is the named revert
or superseding record. All sub-section identities remain inventories inside the
existing contract, not new files.

The next-largest burdens are duplicate campaign/validation reconstruction, two-pass
telemetry I/O, four fresh phase reviews, and a complete pilot. They are proportionate
for this one method-certification campaign because they respectively address
selection bias, active-file stability, exact-subject independence, and the inability
of fragments to demonstrate operability. They must not become a generic requirement
for small or non-claim-bearing tasks. The accepted research-value gate and lifecycle
stage remain the controlling scope limit.

No lease, generic validation cache, mandatory checker, convention lock, observer
migration, external telemetry utility, model router, live security programme, or
causal study is needed to close the three findings. Adding any of those now would
cost more than the research value and would violate the plan's own deferrals.

## 11. Strongest unsuccessful attacks and preserved mechanisms

- **Campaign and validation membership cannot be narrowed by the pilot.** The
  accepted contracts precede telemetry/pilot work, producers supply candidates,
  reviewers reconstruct without the supplied membership seed, and exact-set
  differences fail.
- **The rooted telemetry design does not rely on path-string trust.** It binds the
  final opened identity, rejects root escape/reparse ambiguity without a private
  owner override, reads one handle, and revalidates the prefix. The successful
  MAJ-02 attack concerns metric meaning, not privacy or byte stability.
- **Unknown is not silently converted to false zero.** Structural skill/wait fields,
  missing evidence, and unsupported acquisition states explicitly retain `unknown`.
- **Pointer consolidation does not remove the rule before it is needed.** The
  minimum AGENTS capsule is semantic, load timing is explicit, and literal checks
  cannot substitute for behavior fixtures.
- **Known-refuted PR #157 content cannot reach `main` through this plan.** The live
  PR remains unmerged, provisional-history merge is rejected, and either final
  disposition requires accepted C1 content and fresh review.
- **PR B cannot delay evidence correction.** C0 proceeds independently after Phase
  0; PR B gates only the final Phase 3 integration head. P-040 still requires the
  later owner-authorized integration action.
- **The pilot cannot manufacture a causal or billing claim.** Its outputs are
  descriptive, and the later protocol gate is claim-specific and independently
  accepted.
- **Phase 5 cannot activate itself.** Phase 4 closes the plan using only advisory
  dispositions; every mandatory mechanism remains a separate owner decision.
- **No prior assurance mechanism is silently weakened.** Exact subjects, immutable
  accepted bytes, fresh review, P-039, certify-first, graph-complete validation,
  external lifecycle records, and second-cycle owner rescope remain present.

## 12. Immediate amendments, owner decisions, and deferred dependencies

### Immediate amendments before an accepted replacement subject

1. Split Phase 1/2 pre-merge owner acceptance from post-merge integration receipts
   and remove all self-identity requirements (MAJ-01).
2. Add normative record-to-metric derivation rows and semantic metric fixtures to
   the existing Phase 1 contract (MAJ-02).
3. Add the live mutating-process drain state, bounded liveness barrier, and residue/
   cleanup authority (MAJ-03).

### Owner decisions

1. Stephen must reject this exact v2.1 subject or authorize a fresh amended exact
   subject and another independent focused review. This report cannot amend or
   accept it.
2. Stephen must disposition PR #157 at its exact then-current head during any later
   Phase 0; this review makes no PR decision.
3. Stephen must approve the exact C0/C1 acceptance-versus-integration receipt model
   and its two added paths before those packages are dispatched.
4. PR B still requires its separate P-040-compatible integration authority, exact
   URL/head/base/ancestry, and merge receipt. This review neither defines nor creates
   it.
5. A quantitative study remains optional. Stephen should authorize its protocol
   only if the value of the intended claim exceeds the multi-package design and
   analysis burden.

### Properly deferred dependencies

- Any telemetry parser or live-session acquisition.
- External `ccusage` or another subprocess telemetry utility.
- Mandatory checker/hook/CI or `CONVENTIONS.md` lock.
- Observer entrypoint, append path, or storage migration.
- Model-routing policy.
- Validation reuse until a valuable hermetic class is independently closed.
- Runtime/security evidence belonging to actual T3/T4 surfaces under P-039.
- Any quantitative efficiency study until its claim-specific protocol is accepted.

## 13. Forward-obligation register audit

All section 16 rows were traced to their trigger, owner, and fail state.

| Obligation | Audit result |
|---|---|
| Hold and exactly disposition PR #157 | Present; live state agrees; owner remains Stephen |
| Acquire exact PR B identity and accepted-candidate ancestry | Present; still unavailable; correctly blocks Phase 3, not C0 |
| Dated corrections, no snapshot rewrite | Present and consistent with both earlier reviews |
| No real JSONL content/raw paths | Present and reinforced by section 8's bounded contract |
| Independent campaign/validation closure | Present with separate producer/bar/reviewer roles |
| All Phase 2 artifacts, no selected subset | Present; no `minimum_phase_2` escape remains |
| P-039 before non-research blocking work | Present in assurance floor and always-loaded capsule |
| Second remediation requires owner rescope | Present in forward register and hard stops |
| Certify before regenerate | Present across phase transition and forward register |
| CodeRabbit remains Stephen-owned | Present and semantically fixture-tested |
| 90 path target / stop before 100 | Present at create/update/merge |
| Separate protocol before quantitative claim | Present with exact minimum design fields |
| Mandatory mechanism requires later owner gate | Present; optional Phase 5 remains separate |
| Phase 4 record completes plan, not Phase 5 | Present and unambiguous |

The register is directionally complete, but MAJ-01 requires it to distinguish
`candidate accepted`, `merge authorized`, `integrated`, and `phase closed`; MAJ-03
requires a live-process residue owner; and MAJ-02 requires exact metric derivation
as a Phase 1 obligation. Those additions are amendments to existing rows, not new
programmes.

## 14. Residual uncertainty

- No Phase 1 metric contract or implementation exists, so the proposed derivation
  rows and platform cases have not been executed.
- No complete research/result-facing pilot exists; operability and any efficiency
  magnitude remain unknown.
- Global `AGENTS.md` is outside repository history and currently still contains the
  disputed approximate-80k wording. A later C1 global change therefore needs the
  plan's conditional exact-byte record; this review does not change global state.
- A compact handback cannot preserve tacit interpretation. The successor-redo rule
  is appropriate, but its duplication cost is not yet measured.
- Process liveness and descendant tracking differ across Windows launchers. The
  plan should specify the required semantic state and fail-closed result now; the
  actual mechanism belongs to any later implementation.
- Live PR/main state can change after this dated addendum. Every later phase must
  refresh exact heads and path counts.
- No real session JSONL content was inspected. This preserves confidentiality but
  also means this review does not independently recompute the historical aggregates;
  it verifies the exact historical review objects and attacks the prospective
  contract instead.

## 15. Live PR-state addendum

Read-only checks on 2026-07-23 found no divergence from the amendment-time state:

- `origin/main`: `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d`.
- PR [#157](https://github.com/stephendor/TDL/pull/157): open, non-draft,
  merge state `CLEAN`, head `codex/wp6-manager-efficiency-instructions` at
  `5e800c748394f717005e4f5e29140be095509ae3`, base `main` at
  `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d`, 29 changed files.
- GitHub reports no PR associated with accepted T2 candidate
  `391a92753d7f746fa91a6b5455c9ce0fd01baa52`; no named T2 integration PR was
  found. PR B remains unidentified and unmerged.

This is a dated read-only addendum. It does not mutate PR #157, define PR B, or
make an owner decision.

## 16. Files changed and validation evidence

The only authorized and intended changed path is:

- `docs/plans/agentic-research-system/reviews/large-workflow-efficiency-evidence-first-plan-v2-1-r1-adversarial-review-2026-07-23.md`

Before authoring, the exact launch/branch/remote and every supplied commit/tree/blob/
raw-byte identity were verified. Current authorities and live PR state were read
directly. No APM machinery, external review, real-session content, exploit probe,
secret scan, provider/credential/network test, runtime security test, or telemetry
subprocess was used.

Final `git diff --check`, changed-path isolation, report identity, commit/tree,
push, and local/remote equality are reported in the delivery handback after the
report bytes are frozen. Embedding the report's own final Git/blob/hash identity in
the report would reproduce the self-reference diagnosed in MAJ-01.

## 17. Remaining unauthorized work

This review authorizes **none** of the following: amendment or remediation of v2.1,
v2, or any prior review; changes to AGENTS, skills, guides, telemetry, observations,
code, tests, contracts, accepted WP6 artifacts, or global state; PR #157 mutation or
disposition; PR B definition/creation; owner acceptance; C0/C1; implementation;
pilot; external review; merge; runtime/security work; result/claim/publication work;
or activation of any workflow rule.

The only authorized durable effect is this review report and its commit/push on
`review/wp6-efficiency-evidence-first-v2-1-r1`.
