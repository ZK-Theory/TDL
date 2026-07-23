# Fresh Independent Adversarial Review: Evidence-First Large-Workflow Improvement Plan v2 R1

- **Date:** 2026-07-23
- **Workflow system:** standalone; APM state, skills, Memory Bank, guides, and checkers were not used
- **Lifecycle phase:** design-review
- **Supervision phase:** certify
- **Reviewer task:** `019f8c70-ba2f-7a61-9a14-f85d4d00fa0d`
- **Dispatch source task:** `019f8954-d0cc-7d12-ae83-e8ccb8b61165`
- **Primary skill:** `adversarial-design-review`
- **Meta-skill:** `research-observer`; the observation log was read but not changed because this review authorizes only this report
- **External review:** none; CodeRabbit remained Stephen-owned and was neither triggered nor polled

## 1. Exact subject and source-review identities

The review began only after the detached launch, local review branch, and remote review
branch were independently shown to resolve to the same required commit. The one permitted
same-commit attachment then succeeded.

| Object | Exact identity | Verification |
|---|---|---|
| Reviewed v2 commit | `7c28419bf0a839a0cb2d06d726bbe88dfc228873` | commit object present; local and remote branch equal |
| Reviewed v2 tree | `411e5a36399ea5ea15e0620b715499ba40450dc0` | recomputed from commit |
| Reviewed v2 path | `docs/plans/agentic-research-system/proposals/large-workflow-efficiency-evidence-first-plan-v2-2026-07-23.md` | read from the exact commit |
| Reviewed v2 blob | `2ee2c5c380d335e1341698d04569b969fd1bdbe6` | recomputed from commit/path |
| Reviewed v2 raw SHA-256 | `02b5e1ab0de523fa7f2d97e226742d540b1cf21db799bef269e6f7ba0fcc8258` | recomputed over the 24,599 Git-blob bytes |
| Required review branch | `review/wp6-efficiency-evidence-first-v2-r1` | attached at the reviewed commit after exact equality check |
| Review worktree | `C:\Users\steph\.codex\worktrees\5ebc\TDL` | resolved before the sole authorized write |

The two supplied reviews were also re-resolved from Git rather than trusted through the
v2 summary:

| Direct review source | Exact identity | Result |
|---|---|---|
| Remediation-plan R1 adversarial review; reviewer task `019f8c3e-769d-77a3-9b7a-9d2fa1c24d25` | commit `b32a2253a51c56d08dc509be47730c1f1f96d453`; tree `61d6633056d0990d195b0fa3cef260c7ee167ce1`; blob `e0d7624a63fa41d0c0bab0397a2069d008cd6399`; raw SHA-256 `7199a7b49bc0ee2de6563209ec4b1c5ec52f90605a415af856b5177063eaa3cd` | exact match; verdict `rework_required`, 0 Critical, 7 Major, 3 Minor |
| Historical programme adversarial review; reviewer task `019f8c51-a665-7581-ba15-9f00a1496707` | commit `3f5f65ca698b083b117c50fa84f9ec908ef83839`; tree `54dadecc08291424ffa78c4e5f28a152eb804167`; blob `dddc5d2c7f22cb7dc0fc04752e7ae9f5c63a441d`; raw SHA-256 `b62d1346505adb56d24301410d094290120a7df362c8628f49f83505bdae3bd0` | exact match; verdict `partially_effective`, 0 Critical, 5 Major, 3 Minor |

The rejected R1 plan was read at the immediate parent commit
`03679c1648a04c3393918526b888003048580a04`, tree
`ce2e6bb9b70c108a078326f389c4dc005944ee95`, blob
`2481777cb57f52b151741a1105c37f21e2c4f1fc`, raw SHA-256
`f66428fb12e8837d90d2b82714d528692a24bf6eb45bdb7db6746b4a19c8a237`.
It remains an immutable rejected snapshot.

## 2. Executive verdict

**Verdict: `rework_required`.**

**Severity counts:** 0 Critical, 6 Major, 2 Minor.

V2 is a material improvement over R1. It correctly withdraws the unsupported 80k and
percentage-saving claims, rejects the reusable write lease and generic validation cache,
keeps generated Git facts non-authoritative, preserves fresh exact-subject review, makes
the pilot non-causal, and defers mandatory enforcement. Those controls prevent a
Critical finding at the design-only stage.

The plan nevertheless does not yet provide a closed implementation boundary. Phase
acceptance is undefined; two required evidence sets can still be producer-shaped; the
telemetry prefix and privacy contract lacks a safe acquisition/emission algorithm;
drain mode does not close interrupted mutations or interpretive work; consolidation has
no load-order preservation test; and PR A/PR B/C0/C1 are not topologically ordered.
Each can cause a green-looking phase or pilot to proceed with incomplete authority or
evidence. V2's own section 12 therefore stops further authority while these Majors
remain.

## 3. Critical findings

None. The strongest attacks do not reach Critical because no implementation, merge,
accepted-artifact mutation, telemetry run, pilot, or owner decision is authorized by
this review; v2 also contains explicit hard stops for unresolved Major findings,
unfrozen evidence, producer-supplied authority and verdict, PR B absence, and assurance
regression (v2 section 12, lines 445-458).

## 4. Major findings, ordered by dependency

### MAJ-01 — Phase acceptance, the post-review owner act, and the completion boundary are not executable

1. **ID and severity:** MAJ-01, Major.
2. **Claim:** V2 names deliverables but does not define exact Phase 0, 1, or 2 gate
   records, acceptors, tests, or a plan-completion event. The phrase "minimum Phase 2
   corrections" has no defined member set. Approval is also described as authorizing a
   fresh review even though this report is that review.
3. **Direct evidence:** V2 section 1 says approval authorizes a fresh review but no
   implementation (lines 11-16). Phase 0 requires the plan plus this review and resolution
   of every new Critical/Major (lines 219-229), without naming the post-review owner record.
   Phase 1 lists four deliverables and telemetry properties but no acceptance owner or
   exact phase-exit test (lines 231-261). Phase 2 likewise lists five deliverables and a
   rollback owner but no acceptance record (lines 263-280). Section 8 requires Phase 1
   and "the minimum Phase 2 corrections" to be accepted and merged before the next
   substantive WP6 task (lines 375-377), but never defines that minimum. Section 9 makes
   Phase 1 synthetic fixtures conditional on tooling authorization (lines 385-392), while
   Phase 1 itself requires synthetic fixtures unconditionally (lines 233-259).
4. **Concrete failure scenario:** PR B merges. C0 adds dated addenda and a partial
   telemetry specification but omits independently accepted session classification; C1
   changes the canonical skill but omits the semantic validation template. A supervisor
   calls these the "minimum" corrections, starts the next WP6 task, and later treats the
   pilot as Phase 3-complete because all listed outputs exist. Nothing identifies the
   missing gate as a failure.
5. **Impact:** Authority, operations, provenance, and generalizability. Different actors
   can select different phase exits; an incomplete evidence contract can become the
   foundation for normative prose; optional Phase 5 has no clean separation from plan
   completion.
6. **Disposition:** Fix now. Do not treat the current document plus this report as an
   implementation-ready Phase 0 acceptance packet.
7. **Exact amendment:** Add a phase-gate table with, for every Phase 0-4: exact required
   artifacts; producer; independent reviewer where applicable; owner/acceptor; required
   tests/evidence; fail state; merge identity; rollback/residue owner; and the record that
   closes the phase. Define `minimum_phase_2` as an exact enumerated set, or remove
   "minimum" and require all Phase 2 deliverables. Resolve whether fixtures are Phase 1
   specification fixtures or conditional Phase 5 implementation fixtures. State:
   "After the fresh review, Stephen either rejects v2, accepts an amended exact v2
   subject, or records an explicit risk acceptance. Phase 1 receives no authority from
   the review alone. The improvement plan completes at the Phase 4 owner decision;
   Phase 5 is a separately authorized follow-on."
8. **Affected decisions/packages:** sections 1, 6, 8, 9, and 12; Phase 0-4; C0 and C1;
   later Phase 5 authorization.

### MAJ-02 — Required campaign and validation sets can still be defined by the intervention producer

1. **ID and severity:** MAJ-02, Major.
2. **Claim:** V2 independently closes the required set for a review bundle, but it does
   not apply the same foundation rule to the campaign-session manifest or semantic-delta
   validation map. Those two objects can define what evidence exists and then certify
   themselves.
3. **Direct evidence:** V2 correctly says review authority/dependency/validation sets
   come from an independently accepted plan, contract, or catalogue and fail on missing,
   extra, duplicate, stale, or incompatible entries (lines 181-195). In contrast, Phase
   1 requires only an "owner-authorized" multi-session manifest (lines 231-246), without
   an independent discovery rule or role-classification owner. The pilot preregisters
   its own session-manifest rule, assurance outcomes, and semantic validation map (lines
   288-297). Section 5.6 creates the semantic-delta map but does not say who derives or
   accepts its required check set (lines 197-215). "One full integration gate" is stated
   as a fixed count rather than a floor derived from the authority/dependency graph
   (lines 205-210). Historical H2/H4 required an exact whole-campaign set; remediation
   review MAJ-04/05 required independently derived dependency and required-set closure.
4. **Concrete failure scenario:** The pilot producer classifies a costly helper task as
   auxiliary and outside the campaign manifest, omits a less obvious invariant from the
   semantic-delta map, runs one convenient integration gate, and passes every declared
   validation and telemetry criterion. The same producer-defined omissions make both
   the assurance comparison and efficiency record look better.
5. **Impact:** Evidence fidelity, research/provenance assurance, selection bias,
   independent-review validity, and false green integration evidence.
6. **Disposition:** Amend before Phase 1 or pilot preregistration.
7. **Exact amendment:** Require two independently accepted required-set contracts.
   The campaign contract must bind root task/session identity, acquisition cut, all
   descendant/parallel/retry discovery rules, role vocabulary, inclusion/exclusion rule,
   and an independent classification/closure verdict. The validation contract must join
   accepted obligations and invariants to changed paths, focused checks, contract gates,
   every required integration boundary, and any independent rerun. Record producer,
   acceptance-bar owner, and reviewer separately. Missing, extra, duplicate, stale, or
   incompatible members fail either set. Replace "one full integration gate" with "all
   integration gates required by the accepted dependency graph, including at least one
   full integration-boundary gate; one is not a ceiling."
8. **Affected decisions/packages:** sections 5.5, 5.6, 6 Phase 1-3, and 7; C0, C1,
   pilot preregistration, pilot acceptance, and any later comparison.

### MAJ-03 — The telemetry allowlist and immutable-prefix design do not yet bind metrics to safe bytes

1. **ID and severity:** MAJ-03, Major.
2. **Claim:** V2 lists the right hazards but does not define a path-resolution,
   stable-read, output-schema, or sanitized-error algorithm. Tests named in prose cannot
   prove a contract whose pass/fail semantics are unspecified.
3. **Direct evidence:** Phase 1 accepts a session ID "or path" (lines 241-244), freezes
   byte length, last-complete-newline offset, digest, and acquisition fields "before"
   deriving metrics (lines 245-246), forbids prompts, tool content, commands, and raw
   paths in output including errors (lines 247-248), and requires offline bounded-memory
   parsing (lines 249-254). The fixture list includes locked/growing files, reparse
   points, duplicate events, and concurrent readers (lines 256-259), but the plan does
   not define allowed roots, canonical path handling, file identity, the single-handle
   prefix procedure, post-parse revalidation, enumerated output fields, or error codes.
   Remediation review MAJ-07 required an immutable end-offset digest and privacy-safe
   errors, not merely hazard names.
4. **Concrete failure scenario:** A supplied path resolves through a reparse point to a
   different session root. An exception echoes the resolved path, or the active file is
   replaced/grows between the first digest pass and the metrics pass. The durable record
   contains an allowed digest and allowed numeric fields, but those fields were derived
   from different bytes—or the error leaks a confidential path.
5. **Impact:** The protected research assets are provenance and validity of the
   efficiency evidence; the protected confidential assets are session prompts,
   commands, tool content, and local paths. Existing prose allowlisting is insufficient
   because platform exceptions and two-pass reads can bypass it. This is blocking at
   Phase 1, where evidence acquisition is defined, not a request for runtime
   cybersecurity work.
6. **Disposition:** Fix the specification before any parser or real-session run. The
   cheapest adequate control is a small in-process structural parser contract plus
   synthetic tests; no secret scan, network probe, provider call, or external service is
   justified.
7. **Exact amendment:** Default to session ID resolved under an explicit owner-approved
   set of session roots; allow a literal path only by explicit owner override. Resolve
   and bind the final file identity, reject or explicitly classify root escapes and
   reparse points, open one handle, select the last complete newline at or below the
   frozen length, stream exactly that prefix while deriving both digest and metrics,
   and re-check file identity/length/prefix digest before admission. Define an exhaustive
   emitted-field schema and fixed content-free error enum; never serialize raw exception
   strings or external-tool output. Bound the work to the Phase 1 spec and its listed
   synthetic negative fixtures.
8. **Affected decisions/packages:** Phase 1 telemetry specification and fixtures; C0;
   optional C2 parser; campaign manifest; all Phase 3/4 metric claims.

### MAJ-04 — Compaction drain mode has no closed treatment for interrupted writes, interpretation, or residue

1. **ID and severity:** MAJ-04, Major.
2. **Claim:** Drain mode closes an already-running read-only operation but does not
   specify what happens when compaction lands after a mutation, during review synthesis,
   or with dirty/unverified state. It can therefore abandon evidence, force duplicated
   review, or permit semantic continuation under the label "handback."
3. **Direct evidence:** V2 rotates at one completed author-review-remediation cycle or
   first compaction at the next safe point (lines 150-153). After compaction it forbids
   every new semantic action, edit, claim, or remediation, but permits completion only
   of an atomic read-only operation, exact result capture, state verification, and
   handback (lines 154-160). The packet records clean/dirty state and one next action
   (lines 124-139), but no state transition binds an interrupted edit, partially authored
   report, uncommitted diff, in-flight test, or already interpreted evidence. The current
   supervision skill stops on any post-compaction continuation
   (`.agents/skills/tda-large-workflow-supervision/SKILL.md`, lines 124-159), while the
   handoff skill permits a general handoff record (`tda-handoff`, lines 82-90); v2 does
   not resolve that seam.
4. **Concrete failure scenario:** An author applies a partial schema edit and then the
   context compacts before focused tests. Drain mode forbids completing or reverting the
   edit but only says to verify state and hand back. A successor either trusts dirty
   partial bytes, discards them without authority, or duplicates the whole edit. In a
   review, compaction after source interpretation but before the report forces the
   successor to repeat the evidence or rely on an unreviewed interpretive summary. An
   old task can also call additional synthesis "handback completion" because that term
   is not mechanically bounded.
5. **Impact:** Evidence abandonment, duplicated validation/review, dirty-state
   inheritance, accidental commit of unverified work, and an unenforceable semantic-stop
   boundary.
6. **Disposition:** Amend the drain state machine; retain compaction as a hard rotation
   trigger.
7. **Exact amendment:** Define trigger states for `read_only_atomic_in_flight`,
   `mutation_completed_unverified`, `clean_safe_point`, and
   `interpretation_or_draft_incomplete`. Permit only: bounded completion of the first;
   identity/diff/status capture and explicit `UNVERIFIED_DO_NOT_COMMIT` preservation of
   the second; exact partial-byte identity with no claim credit for the fourth; and a
   neutral handback. The old task may not test, edit, commit, push, accept, remediate, or
   issue a finding after the trigger. The successor must revalidate dirty bytes and
   independently redo incomplete interpretation before use. Name Stephen as the only
   exception owner, record the maximum operation in advance, and require the handback
   to state old/new task IDs so renaming an action cannot evade the stop.
8. **Affected decisions/packages:** sections 5.2, 5.3, 6 Phase 2-4, and 12; canonical
   supervision and handoff rules; pilot false-stop/duplication metrics.

### MAJ-05 — Canonical consolidation has no load-order and compaction-survival preservation gate

1. **ID and severity:** MAJ-05, Major.
2. **Claim:** The ownership map names surfaces but does not identify which invariants
   must be available before skill selection, before a write, or immediately after
   compaction. A pointer-only reduction can therefore remove a safety rule at the point
   where it must fire.
3. **Direct evidence:** V2 assigns selector and always-loaded safety boundaries to
   repository/global `AGENTS.md` and the procedure to one normative skill (lines
   105-122). Phase 2 allows a conformance test only for repeated literal identifiers
   (lines 263-277). Current global `AGENTS.md` lines 34-52 and repository `AGENTS.md`
   lines 133-162 directly carry standalone/APM exclusion, compaction rotation,
   no-history review, dispatch fields, external-review separation, research-value,
   second-cycle, integration, and certify-before-regenerate rules. The current
   supervision skill repeats these at lines 27-45 and 69-109; the task-brief and handoff
   skills repeat their own dispatch/rotation fields. The plan never supplies a semantic
   preservation test or a minimum always-loaded set.
4. **Concrete failure scenario:** C1 moves the new drain rule and second-cycle stop into
   the canonical supervision skill and leaves only a generic pointer in AGENTS. A task
   is misclassified as small and never loads that skill, or a compaction summary does
   not preserve/reload it. The rule that should stop new semantic work is absent exactly
   when the trigger fires, while all literal pointer checks pass.
5. **Impact:** Silent safety-rule absence, APM/standalone routing leakage, post-compaction
   continuation, external-review ownership drift, and a new single point of failure in
   the canonical skill.
6. **Disposition:** Amend before C1. Consolidation remains the right direction.
7. **Exact amendment:** Extend the authority map with `needed_at`, `canonical_owner`,
   `always_loaded_copy`, `pointer_surfaces`, `reload_trigger`, and
   `negative_fixture`. Enumerate the minimum pre-skill/pre-write/post-compaction
   invariants: workflow-system selection and APM exclusion; observer activation;
   exact-root/branch/HEAD/scope checks; owner gates; external-review ownership; the
   compaction drain trigger; and prohibition on unauthorized semantic continuation.
   Run semantic dispatch fixtures for a wrong workflow, omitted skill load, wrong
   worktree, first compaction, and an undelegated CodeRabbit action. Literal identifier
   conformance may supplement but not replace these tests. Keep dated proposals and the
   guide non-normative.
8. **Affected decisions/packages:** sections 5.1 and 6 Phase 2; C1; global/repository
   AGENTS; the three workflow skills; supervision guide; future checker.

### MAJ-06 — PR A, PR B, C0, and C1 have no single authority-preserving integration DAG

1. **ID and severity:** MAJ-06, Major.
2. **Claim:** V2 acknowledges that PR A needs an owner decision but does not make that
   decision a prerequisite or reconcile it with the older accepted sequence "PR A then
   PR B." Its own sequence can therefore place refuted rules on `main` or make evidence
   correction depend on an unrelated T2 integration.
3. **Direct evidence:** The accepted completed-cycle assessment recommends landing PR A
   first, then creating and merging the T2 integration PR
   (`large-workflow-completed-cycle-assessment-2026-07-23.md`, lines 152-163). V2 records
   PR A open and PR B unidentified (lines 362-373), blocks efficiency implementation
   until PR B merges, and requires Phase 1/minimum Phase 2 before the next substantive
   WP6 task (lines 375-378). It leaves amendment, provisional merge, or supersession of
   PR A to a later owner choice without making that choice a hard predecessor (lines
   380-381). C0/C1 are then based on "then-current main" (lines 383-400). Live state on
   2026-07-23 confirms PR #157 is still open and clean at head
   `5e800c748394f717005e4f5e29140be095509ae3`, base `main`
   `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d`, with 29 files; no PR is associated with
   accepted candidate `391a92753d7f746fa91a6b5455c9ce0fd01baa52`.
4. **Concrete failure scenario:** PR A merges under the older accepted recommendation,
   making the disproven 80k rule and duplicated advisory surfaces active on `main`.
   PR B then merges, and C0/C1 later attempt to supersede those rules. During the gap,
   new tasks follow contradictory authority. Conversely, treating PR B as a prerequisite
   for even dated evidence correction delays correction for reasons unrelated to the
   validity of the historical claims.
5. **Impact:** Contradictory active authority, unclear integration dependencies,
   avoidable migration/review work, and a period in which a known-refuted efficiency
   claim remains normative.
6. **Disposition:** Owner decision and plan amendment required before PR A merge or any
   C0/C1 dispatch. PR B's absence remains a valid Phase 3 hard stop.
7. **Exact amendment:** Add an explicit DAG and owner record. The first node is Stephen's
   disposition of PR A at its exact head: amend before merge, close/supersede, or merge
   as dated provisional history with an explicit non-authority marker and exact C1
   supersession dependency. Allow evidence-only C0 to proceed from an approved current
   base independently of PR B if it changes no behaviour. Require PR B's exact
   URL/head/base/accepted-candidate ancestry/merge commit before Phase 3. Require C1 and
   all always-loaded/global changes to merge before any pilot task consumes the new
   rules. Define the final integration head on which Phase 3 begins.
8. **Affected decisions/packages:** section 8, section 9, hard stops, PR #157, future PR
   B, C0, C1, and Phase 3 dispatch.

## 5. Minor and editorial findings

### MIN-01 — Historical H7's prospective fields are still incomplete

1. **ID and severity:** MIN-01, Minor.
2. **Claim:** V2 says it resolves H7 by measuring skill identities/bytes and wait class,
   but the prospective record carries skill bytes only and no structural wait class.
3. **Direct evidence:** V2's disposition table says "measure identities/bytes and wait
   class prospectively" (line 419). The packet and pilot record dispatch/packet/skill
   bytes (lines 136-139 and 288-297), and section 7 records tool calls and external-review
   owner/status (lines 340-355), but it does not require `loaded_skill_identities` or
   `wait_class`. Historical H7's exact proposed record required
   `loaded_skill_identities`, `loaded_skill_bytes`, and `wait_class` (historical review
   lines 435-461).
4. **Concrete failure scenario:** Two pilots report equal skill bytes and generic wait
   counts, but one loaded a different high-impact skill and the other spent waits on an
   external-review path. The structural record cannot distinguish them.
5. **Impact:** Local evidence fidelity and interpretability; it does not authorize
   external review or change research results.
6. **Disposition:** Fix in the Phase 1 prospective schema.
7. **Exact amendment:** Add `loaded_skill_identities` plus bytes by identity, and
   `wait_class` with the closed enum `process | agent | external_review | other`. Treat
   absence as `unknown`, never as zero. Do not inspect or emit command/tool content to
   derive it.
8. **Affected decisions/packages:** Phase 1 telemetry schema, Phase 3 pilot manifest,
   section 7, and the H7 disposition row.

### MIN-02 — A later quantitative comparison is correctly deferred but has no claim-specific design gate

1. **ID and severity:** MIN-02, Minor.
2. **Claim:** V2 correctly forbids a causal percentage claim from one pilot, but the
   phrase "matched or randomized/crossover comparison" is not yet a design capable of
   supporting any named causal claim.
3. **Direct evidence:** Phase 3 limits one pilot to operability and requires a later
   matched or randomized/crossover comparison for a quantitative claim (lines 302-309).
   The prospective record captures broad workload and assurance dimensions (lines
   340-360), but no unit of assignment, matching variables, estimand, order/carryover
   rule, model/runtime stratification, exclusion rule, equivalence margin, or analysis
   owner is defined. Historical H2 explicitly found unmatched V1/V2 non-causal.
4. **Concrete failure scenario:** Two nominally equivalent work packages differ in
   review findings, model version, or integration state. A post-hoc match reports a
   percentage difference as intervention effect despite uncontrolled scope and order.
5. **Impact:** Future generalizability and statistical validity only. The current pilot
   remains non-causal and therefore safe.
6. **Disposition:** Defer, but add a hard gate before any quantitative claim.
7. **Exact amendment:** State that a separate preregistered evaluation protocol must name
   the estimand, unit, assignment/matching rule, assurance-equivalence margins,
   model/runtime/version strata, crossover order and carryover treatment if applicable,
   missing/exclusion rules, analysis owner, and allowed claim. Without that accepted
   protocol, Phase 4 reports descriptive metrics only.
8. **Affected decisions/packages:** Phase 3 comparison-class field, Phase 4 assessment,
   and any later quantitative publication or normative efficiency claim.

## 6. Complete prior-finding-to-v2 disposition audit

| Prior finding | Independent v2 disposition | Review result |
|---|---|---|
| R1 MAJ-01 / Historical H4 — misclassified, non-atomic baseline and refuted records | Dated addenda and an exact session-role manifest are Phase 1 blockers | **Partly resolved.** Correct direction; phase gate and independent campaign-set closure remain MAJ-01/02 |
| R1 MAJ-02 / Historical H1 — absolute tripwire without safe interruption | 80k withdrawn; observable counter/phase boundary; compaction drain | **Partly resolved.** Numeric claim closed; interrupted non-read work remains MAJ-04 |
| R1 MAJ-03 — preflight/lease authority substitution | Observer first; mechanical state not authority; reusable lease rejected | **Resolved in design** |
| R1 MAJ-04 — generic validation reuse cannot prove dependencies | Generic cache rejected; later hermetic allowlist only | **Partly resolved.** Reuse defect closed; current semantic-map required set remains MAJ-02 |
| R1 MAJ-05 — generated bundle lacks independent required-set closure | Git facts navigation-only; reviewer resolves accepted catalogue and exact set | **Resolved for review bundles;** campaign and validation sets still fail the same foundation attack under MAJ-02 |
| R1 MAJ-06 / Historical H3 and Historical H8 — multiplied normative surfaces | One normative skill; pointer-only reductions; observer work deferred | **Partly resolved.** Load-order and compaction-survival gate missing under MAJ-05; PR A sequence under MAJ-06 |
| R1 MAJ-07 — telemetry privacy/snapshot/platform contract | Explicit session, structural allowlist, prefix digest, offline parser, Windows/concurrency fixtures | **Partly resolved.** Required hazards are named, but stable-read/path/error semantics remain MAJ-03 |
| R1 MIN-01 — PR B undefined | Semantic role defined; live identity remains a hard acquisition | **Resolved in design;** PR B remains absent, correctly blocking Phase 3 |
| R1 MIN-02 — PR path count refresh | Recount before creation/update and merge; 90 target/100 stop | **Resolved** |
| R1 MIN-03 — rollback/residue ownership | Package-specific owner required; Phase 5 explicit; Phase 2 rollback owner named | **Resolved subject to MAJ-01's exact phase records** |
| Historical H2 — no causal estimate | Historical percentages withdrawn; one pilot explicitly non-causal | **Resolved for current claims;** later protocol deferred under MIN-02 |
| Historical H5 — research-value and second-cycle controls arrived late | P-039 intake and second-cycle owner stop retained | **Resolved** |
| Historical H6 — avoidable detached routing stops | One same-commit attachment; mismatched source stops | **Resolved** |
| Historical H7 — skill/no-poll claims unverified | V2 claims identities/bytes and wait class prospectively | **Not fully resolved; MIN-01** |

No prior Critical existed. Every prior Major and Minor is represented above; grouping is
only where the two reviews diagnosed the same mechanism.

## 7. Complete v2 decision and action audit

| ID | V2 decision/action | Cost bearer and timing | Disposition |
|---|---|---|---|
| V2-A01 | Evidence first; no implementation from rejected R1 | Plan owner/reviewer before work | **Keep** |
| V2-A02 | Bind both source reviews and keep rejected R1 immutable | Reviewer/provenance owner at Phase 0 | **Keep** |
| V2-A03 | Retain exact-state, fresh review, owner gates, P-039, certify-first, and external-review ownership | Every task; small dispatch/verification cost | **Keep**; strongest direct evidence supports them |
| V2-A04 | Withdraw 80k, percentage savings, causal V1/V2, and routing-failure misclassification | Editorial correction in Phase 1 | **Keep; blocking before reuse** |
| V2-A05 | Non-negotiable assurance floor | Implementer/reviewer at every phase | **Keep** |
| V2-A06 | One canonical normative skill plus pointer surfaces | Workflow-method owner in C1; migration and single-point risk | **Amend** per MAJ-05 |
| V2-A07 | Compact exact-state packet and prospective byte counts | Task owner at each handback; startup/maintenance cost | **Keep with MAJ-04 drain-state fields** |
| V2-A08 | Runtime counter only when exposed; no universal numeric threshold | Task owner at closeout | **Keep** |
| V2-A09 | Rotate coordinator at cycle or compaction; leaf task normally one deliverable | Active task and successor at trigger | **Amend** per MAJ-04 |
| V2-A10 | Observer, mechanical state, triggered skills, independent authority, immediate mutation check | Writer at startup/write boundary | **Keep** |
| V2-A11 | Reject reusable lease; later helper stateless/atomic; race remains open without lock | Writers/tool owner | **Keep**; proportionate |
| V2-A12 | Generated review bundle contains Git facts only | Reviewer/generator at review intake | **Keep** |
| V2-A13 | Independently owned exact required-set closure for review | Catalogue owner/reviewer | **Keep and extend** per MAJ-02 |
| V2-A14 | Every blocking review gets a durable neutral exact-subject report; owner accepts separately | Reviewer and repository maintainers | **Keep** |
| V2-A15 | Reject generic validation cache; certify existing artifacts; map semantic delta; run integration/independent checks | Implementer/integrator/reviewer | **Amend set ownership and integration floor** per MAJ-02 |
| V2-A16 | Phase 0 fresh review and finding resolution | Reviewer/owner now | **Amend exit act** per MAJ-01 |
| V2-A17 | Phase 1 addenda, campaign manifest, telemetry spec/fixtures, authority map | Evidence owner and session owners before behaviour | **Amend** per MAJ-01/02/03 |
| V2-A18 | Phase 2 minimal consolidation and no new mandatory mechanisms | Workflow-method owner in C1 | **Keep direction; amend** per MAJ-01/05 |
| V2-A19 | Phase 3 one complete research/result-facing advisory pilot after T2 integration | Research team and reviewers during one package | **Keep**, subject to MAJ-02/06 gates |
| V2-A20 | Pilot requires completed outcome, assurance, exact state, owner gates, and whole-campaign manifest | Pilot team at closeout | **Keep with independent set closure** |
| V2-A21 | One pilot cannot establish causal percentage saving | Owner/analyst after pilot | **Keep** |
| V2-A22 | Phase 4 descriptive assessment; retain/revise/reject only; no mandatory enforcement | Analyst/owner after pilot | **Keep; define completion record** per MAJ-01 and later claim gate per MIN-02 |
| V2-A23 | Phase 5 only for a demonstrated recurring problem; one tool/PR with negatives, positive signal, rollback/residue owner, review | Tool maintainer and reviewers only if triggered | **Keep deferred** |
| V2-A24 | Prospective record separates work, assurance, context, total use, prompts, tools, time, fragmentation, external review, maintenance | Evidence owner at closeout | **Keep; add MIN-01 fields** |
| V2-A25 | PR A stays non-quantitative; PR B exact identity/ancestry/merge before pilot | Owner/integrator before Phase 3 | **Amend topology** per MAJ-06 |
| V2-A26 | C0/C1 then optional C2/C3+, small semantic PRs from current main | Implementers/reviewers during integration | **Amend prerequisites** per MAJ-01/06; keep semantic splitting |
| V2-A27 | Recount paths; target 90; stop before 100; final integration gate | Integrator before update/review/merge | **Keep**, with MAJ-02's all-required-gates rule |
| V2-A28 | Global changes separate with backup/diff/validation/rollback | Global-system owner | **Keep** |
| V2-A29 | Reject lease/cache/author-exhaustive manifest/absolute stops/universal threshold/historical causal claim | Avoided maintenance and assurance cost | **Keep rejected** |
| V2-A30 | Defer checker, lock, observer migration, ccusage, model routing, hermetic reuse, token hard stop | No current bearer; later owner if reopened | **Keep deferred** |
| V2-A31 | Hard stops in section 12 | Every dispatcher/owner | **Keep and add MAJ-01–06 exit conditions** |

## 8. Invariant → owner/enforcement → evidence/test consistency matrix

| Invariant | Owner / enforcement point | Required evidence or test | Result |
|---|---|---|---|
| Standalone never loads APM machinery | Always-loaded AGENTS plus canonical skill | Dispatch negative case and workflow ID | **Consistent now; preserve always loaded** |
| No unsupported efficiency claim becomes normative | Phase 1 evidence owner plus owner acceptance | Dated addenda, exact evidence manifest, accepted claim class | **Gap: MAJ-01/02** |
| Packet is locator, never authority | Canonical skill/handoff; repository/owner records remain primary | Packet predecessor/hash plus independent Git/owner verification | **Consistent** |
| Fresh reviewer has no parent history and exact subject | Dispatcher and review report | Task ID/context mode plus commit/tree/blob/hash | **Consistent; this review demonstrates it** |
| Mathematical/statistical/research assurance is not traded for savings | Accepted plan/contract owners and independent reviewer | Same required assurance outcomes and semantic validation map | **Direction consistent; set ownership gap MAJ-02** |
| P-039 research-value gate remains human and proportional | Stephen/accepted P-039; dispatch intake | Six-field disposition and bounded effort | **Consistent** |
| Compaction starts no new semantic action | Always-loaded trigger plus canonical drain state machine | State transition/handback negative fixtures | **Missing: MAJ-04** |
| Canonical consolidation cannot hide a safety rule | Workflow-method owner plus always-loaded surface | Load-order map and semantic dispatch fixtures | **Missing: MAJ-05** |
| Review required set is independently derived | Accepted plan/contract/catalogue and reviewer | Exact missing/extra/duplicate/stale/incompatible closure | **Consistent for review bundles** |
| Campaign and validation required sets are independently derived | Independent evidence/assurance owners | Session discovery/classification closure; obligation-to-check closure | **Missing: MAJ-02** |
| Telemetry metrics bind exactly the bytes identified | Phase 1 telemetry contract owner | Same-handle prefix digest/metrics and post-read identity check | **Missing: MAJ-03** |
| Telemetry never emits sensitive content or raw paths | Phase 1 emitted-schema owner | Closed field schema and content-free error negative fixtures | **Missing: MAJ-03** |
| Validation covers the semantic delta and every required integration seam | Accepted obligation owner, integrator, independent reviewer | Independently accepted map and all dependency-graph gates | **Gap: MAJ-02** |
| Accepted T2 bytes remain immutable and externally accepted | P-040/owner record; future integration owner | Candidate ancestry, review/acceptance identities, merge commit | **Consistent pre-integration; PR B absent** |
| PR authority is non-contradictory and topologically ordered | Stephen plus integration record | Exact PR A disposition and PR B/C0/C1 DAG | **Missing: MAJ-06** |
| A second ordinary remediation stops for owner rescope and fresh subject | Stephen/canonical skill/dispatch | Cycle count and owner ruling | **Consistent** |
| Blocking review verdict is durable but cannot self-accept | Reviewer report plus separate owner record | Exact report identity and distinct owner decision | **Consistent** |
| Mandatory checker/lock is not self-activated | Stephen/Phase 5 gate | Separate decision, negatives, positive signal, pilot evidence | **Consistent and deferred** |
| Plan has a single completion boundary | Phase gate owner | Exact Phase 4 decision record; Phase 5 separately authorized | **Missing: MAJ-01** |

## 9. Negative-consequence and practicality assessment

| Action | Credible downside | Who bears it / when | Adequacy and cheaper control |
|---|---|---|---|
| Dated addenda and exact manifest | Editorial and classification work | Evidence owner/reviewer in Phase 1 | Necessary; one accepted manifest reused by all assessments is cheapest |
| Telemetry specification/fixtures | Parser/spec maintenance and privacy review | Tool/evidence owner before pilot | Justified only in the bounded MAJ-03 form; no live scans or external tools needed |
| Canonical rule consolidation | Migration risk and single-point failure | Workflow-method owner and all future tasks at C1 | Worthwhile after MAJ-05 map; pointer-only guide/history minimizes bytes |
| Compact packet | Handback creation and lost tacit context | Active task and successor at each rotation | Keep identity-only packet; do not copy authorities; close dirty/partial states per MAJ-04 |
| Compaction rotation | Restart, duplicate review/validation, false stops | Active task/successor at unpredictable trigger | Keep hard trigger, but a closed drain state machine is cheaper than rerunning blindly |
| Fresh independent review | Repeated source reading and prompt bytes | Reviewer at each exact subject | Assurance benefit is directly demonstrated; retain and reduce packet/prompt bytes |
| Semantic validation map | Mapping and independent review overhead | Author, obligation owner, reviewer before execution | Necessary for assurance; derive once from accepted obligations and update by delta |
| Integration validation | Runtime cost | Integrator at seam | Run all required seam gates once; one is a floor, not an arbitrary ceiling |
| One complete pilot | Research time and opportunity cost | WP6 team after prerequisites | Proportionate because it is one advisory, non-causal, complete package |
| Later matched/randomized study | Multiple comparable packages and analysis burden | Research programme only if a numeric claim is valuable | Optional; do not run unless the claim value exceeds the study cost |
| PR separation and path caps | More integration coordination | Integrator before review/merge | External 100-file constraint is real; semantic splits and a DAG are adequate |
| Optional tooling/checker | Maintenance, false positives, drift | Tool owner and all users after activation | Correctly deferred until a recurring observed problem and separate owner decision |

The cheapest assurance-equivalent initial intervention is smaller than R1 and close to
v2's intent: issue the dated corrections; freeze one independently closed campaign
manifest; define the bounded structural telemetry contract; establish the ownership and
always-loaded-rule map; update one canonical skill and pointers; then run one complete
advisory pilot. No lease, generic cache, observer rewrite, external telemetry utility,
mandatory checker, convention lock, or causal percentage study is needed now.

## 10. Strongest unsuccessful attacks and preserved mechanisms

- **The pilot cannot presently manufacture a causal percentage.** V2 expressly limits
  one pilot to operability and observed/descriptive mechanisms. MIN-02 concerns only a
  later claim.
- **Generated Git facts cannot define authority.** Section 5.5 separates navigation
  facts from the accepted catalogue and independent reviewer. The remaining MAJ-02 gap
  is on different required sets.
- **The old unsafe architectures do not survive under another name.** The reusable
  lease and generic cache are rejected; future helpers must be stateless/atomic and
  future reuse must be independently hermetic.
- **The packet does not self-accept.** It points to external owner/repository records,
  and the durable review report remains separate from owner acceptance.
- **Research assurance retains priority.** The exact P-039 record protects research
  validity/provenance and bounds orthogonal hardening. V2 defers runtime/security work
  rather than making it an early blocker.
- **PR B absence is not concealed.** The plan and live GitHub state agree that it is
  unidentified; Phase 3 correctly stops.
- **No Critical is suppressed by green tests.** There is no implementation or test suite
  under review, and this report gives no acceptance authority.

## 11. Immediate amendments, owner decisions, and deferred dependencies

### Immediate amendments before an accepted replacement subject

1. Add executable phase-gate and completion records (MAJ-01).
2. Independently close campaign-session and validation required sets (MAJ-02).
3. Specify the stable-prefix, rooted-path, allowlisted-output, sanitized-error telemetry
   algorithm (MAJ-03).
4. Close every drain-mode state, including dirty and interpretive residue (MAJ-04).
5. Add the load-order/compaction-survival ownership map and semantic fixtures (MAJ-05).
6. Add the exact PR A/PR B/C0/C1 integration DAG (MAJ-06).
7. Add prospective loaded-skill identities and structural wait class (MIN-01).
8. Add a separate preregistration gate before any later quantitative claim (MIN-02).

### Owner decisions

1. Stephen must disposition PR #157 at its exact current head: amend, close/supersede,
   or merge only as explicitly provisional history with a mandatory supersession path.
2. Stephen must accept an amended exact v2 subject after a fresh focused review of these
   Majors; this report does not resolve them on his behalf.
3. The owner must name the Phase 1 evidence-set/telemetry acceptor and the Phase 2
   workflow-method acceptor, distinct from the producing actor where the acceptance bar
   is at issue.
4. Stephen remains the sole exception owner for any bounded post-compaction operation.
5. PR B's exact role, URL, head, base, candidate ancestry, and merge commit remain an
   acquisition decision/gate before Phase 3.

### Properly deferred dependencies

- External `ccusage` or another telemetry utility.
- Mandatory checker/hook/CI and `CONVENTIONS.md` lock.
- Observer entrypoint, append path, or storage migration.
- Model-routing policy.
- Any validation-reuse class until independent hermetic closure is valuable.
- Any quantitative efficiency study until a claim-specific protocol is accepted.
- Runtime/security evidence that belongs to T3/T4 under P-039.

## 12. Residual uncertainty

- No complete research/result-facing pilot exists, so operability and magnitude of any
  saving remain unknown.
- No telemetry implementation exists; the named Windows, encoding, lock, growth,
  reparse-point, and concurrency cases have not been executed.
- The global AGENTS surface is outside repository history and needs a separate scoped
  change if consolidation is later authorized.
- A compact handback cannot preserve all tacit reasoning; the pilot must record duplicate
  work and false stops without treating their absence as proven from self-report.
- Model/runtime token semantics and fixed platform context may change; no cross-model
  threshold or billing claim is supported.
- PR A or remote `main` may change after this dated addendum. Any later head requires a
  fresh live-state check; this review does not grant authority over it.
- No structural session JSONL was read in this review. Exact prior telemetry findings
  were relied on only after their report commit/tree/blob/raw-byte identities were
  verified. This avoids unnecessary handling of sensitive session content but does not
  independently reproduce the prior numeric aggregates.

## 13. Current PR-state addendum

Read-only live checks on 2026-07-23 found no divergence from v2's dated statement:

- `origin/main`: `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d`.
- PR A: [#157](https://github.com/stephendor/TDL/pull/157), open, non-draft,
  merge state `CLEAN`, head `codex/wp6-manager-efficiency-instructions` at
  `5e800c748394f717005e4f5e29140be095509ae3`, base `main` at
  `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d`, 29 changed files.
- GitHub returned no PR associated with accepted T2 candidate
  `391a92753d7f746fa91a6b5455c9ce0fd01baa52`, and no PR for either named T2
  candidate/review branch. PR B remains unidentified and unmerged.

This is a dated addendum only. It does not mutate PR A, define PR B, or make an owner
decision.

## 14. Files changed and verification evidence

Only this report is authorized and intended to change:

- `docs/plans/agentic-research-system/reviews/large-workflow-efficiency-evidence-first-plan-v2-r1-adversarial-review-2026-07-23.md`

Verification completed before report authoring:

- required launch `HEAD`, local branch, and remote branch all resolved to the exact
  reviewed commit before the single deterministic attachment;
- reviewed plan commit/tree/blob/raw SHA-256 matched;
- both prior review commit/tree/blob/raw SHA-256 tuples matched;
- rejected R1 was confirmed at the reviewed commit's immediate parent and read directly;
- current global/repository AGENTS, the three workflow skill sources, supervision guide,
  P-039/P-040 register entries, owner acceptance, and completed-cycle assessment were
  read directly;
- live origin/PR state was queried read-only; and
- no APM, external review, exploit/security probe, provider call, credential test,
  runtime security test, or real-session JSONL subprocess was used.

Final diff, report identity, commit, push, and local/remote equality validation are
recorded in the delivery handback after the report bytes are frozen; embedding the
report's own commit/blob/hash would create a self-reference.

## 15. Remaining unauthorized work

This review authorizes **none** of the following: amendment of v2 or R1; changes to
AGENTS, skills, guides, telemetry, observation logs, code, tests, schemas, contracts,
accepted WP6 artifacts, or global state; PR A mutation; PR B creation; implementation;
pilot execution; external review; remediation; owner acceptance; merge; runtime work;
result/claim/publication work; or resolution of any owner decision above.

The only authorized durable effect is this exact review report and its commit/push on
`review/wp6-efficiency-evidence-first-v2-r1`.
