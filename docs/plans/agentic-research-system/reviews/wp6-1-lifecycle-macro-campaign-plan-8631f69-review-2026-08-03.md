# WP6.1 lifecycle macro-campaign plan exact-subject adversarial review

**Date:** 2026-08-03
**Verdict:** `rework_required`
**Findings:** 0 Critical, 6 Major, 1 Minor
**Reviewed commit:** `8631f691aac7c501b6badf95632faa721987f656`
**Reviewed parent:** `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e`
**Reviewed tree:** `639017db3d89f8982ade526eeb3c00dddcb91e22`
**Reviewed branch:** `review/wp6-1-macro-plan-8631f69`
**Reviewed plan:** `docs/plans/agentic-research-system/implementation/06p-wp6-1-lifecycle-macro-campaign-execution-plan.md`
**Plan Git blob:** `1ddcadc23464aa075284b475d3941161f37c11a6`
**Plan raw Git-blob SHA-256:** `36A9E233EE1D9F402D5361FB8A10F0F42A227BAA7B76291154D384318B610607`

## 1. Executive conclusion

The macro-campaign architecture is directionally sound. It preserves the accepted
104-row lifecycle catalogue, reconstructs the current 19 active rows correctly,
partitions all 85 remaining rows exactly once as C1/C2/C3/R1 = 23/28/32/2,
keeps central state-writing seams serial, and uses capability campaigns rather than
row-by-row tickets. C2 also intends a real `review_pending` state produced through
the public command path, not a label-only fixture. The model assignments, bounded
parallel leaves, PR cap, independent review, one-remediation limit, protected-byte
invariants, W11 separation, and external non-authorities are suitable.

Six material gaps nevertheless make the plan unsafe to dispatch as written:

1. plan acceptance can be composed into implementation and C1 dispatch without the
   separate owner start record required by existing authority;
2. the C2 handoff does not define the complete initial Artefact authority tuple;
3. the protected Review-request and Task-submit shapes do not enforce the exact joins
   that are supposed to justify `review_pending`;
4. the proposed partial cutover does not bind an exact amendment or satisfaction of
   the still-open 06i/G-RM-14 authority route;
5. the routing ledger validates requested declarations, not independent owner
   acceptance, actual task creation, or the integrated diff; and
6. the claimed post-C3 zero-row closure occurs while the two R1 rows remain inactive.

These are acceptance blockers rather than clarifications. They can be corrected
without abandoning the campaign topology or changing the accepted catalogue.

This review is evidence about one exact plan subject. It is not owner acceptance and
grants no implementation, contract acceptance, dispatch, pull-request, Jira,
provider, credential, CodeRabbit, merge, Gate 6, recovery, or research-execution
authority.

## 2. Exact identity, scope, and protected state

Before review, the linked worktree began detached at the required candidate. The
detached `HEAD` and `refs/heads/review/wp6-1-macro-plan-8631f69` both resolved to
`8631f691aac7c501b6badf95632faa721987f656`. One deterministic switch to that branch
was made, after which cwd, symbolic branch, `HEAD`, parent, tree, and clean status
were reverified.

The reviewed plan is exactly 49,464 bytes, valid UTF-8 without BOM, LF-only, ends in
LF, and has the Git blob and raw SHA-256 recorded above. Relative to its parent, the
candidate adds only that plan.

The protected generated schema trees are unchanged between the parent and candidate:

| Canonical repository path | Candidate tree | Files | Parent equality |
|---|---|---:|---|
| `.research-system/schemas/core/commands` | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | 87 | exact |
| `.research-system/schemas/core/events` | `154ffc4bdde82fe903718734687e7a62797b1f69` | 86 | exact |

The review prompt described these as `src/research_system/command` and
`src/research_system/event`; those literal paths do not exist at the candidate. The
specified tree identities resolve to the canonical generated-schema paths above.
This is a path-label clarification, not protected-byte drift.

The only authorized review write is this report. The reviewed plan, runtime, tests,
schemas, catalogues, decision records, Jira, PR state, provider state, and all other
paths remain untouched.

## 3. Independent reconstruction and positive controls

### 3.1 Exact catalogue and allocation

The census was reconstructed from the accepted 06d owner-source catalogue, its
machine copy, active registry bindings, command lifecycle bindings, and current
implementation. Producer claims in 06p were not used as the authority.

| Set | Count | Unique | Disjoint from active | Disposition |
|---|---:|---:|---:|---|
| accepted catalogue | 104 | 104 | n/a | exact |
| active at the candidate base | 19 | 19 | n/a | exact |
| remaining | 85 | 85 | yes | exact |
| C1 | 23 | 23 | yes | exact |
| C2 | 28 | 28 | yes | exact |
| C3 | 32 | 32 | yes | exact |
| R1 | 2 | 2 | yes | exact |

There are zero duplicates within a campaign, zero overlaps between campaigns, zero
active-row overlaps, zero missing remaining rows, and zero extra rows. The union of
the 19 active rows and all four allocations equals the 104-row catalogue exactly.
The sorted catalogue-set SHA-256 is
`3b4d92934f5789ffbf17a6443b4f69acf1709791f35999c094f544faa8b22466`; the sorted
remaining/allocation-set SHA-256 is
`6931b66a94913b284a1471e09f4303652d049e6398c8e90ae4476483a6b4d4c2`.

The accepted source declares 104 normalized rows and 182 expanded state edges
(`.research-system/contracts/wp6-1-owner-source-catalogue.yaml:75-120`). The active
19 are the six existing Scope/Task rows and 13 Message rows, represented by ten
active command/event pairs (`research_system/schema_registry.py:79-183` and
`research_system/command/lifecycle.py:9-60`). The historical accepted 06m subject at
`0e842969c770811edf5c81dcd7e4f7a647e050ad:docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md`
has the same exact 104-row set. The superseded 06o subject at
`a557ab0e00d5d1497735f21b593823b12a5df866:docs/plans/agentic-research-system/implementation/06o-wp6-1-lifecycle-execution-plan-after-message-pilot.md`
partitions the same 85 rows as 17/9/11/19/9/18/2. The 06p redistribution is exact.

W11 remains a separate 81-row catalogue, inert and non-authoritative for this plan.
Its exclusion at `06p:173-180` is correct.

### 3.2 Dependency and state checks

The accepted W2 state machine defines the real transition
`in_progress + SubmitForReview -> review_pending` and includes `review_pending` in
the relevant block, input, pause, resume, and cancel source classes
(`docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md:390-445`;
`.research-system/contracts/wp6-1-owner-source-catalogue.yaml:77-120`). The C2 public
journey at `06p:411-423` therefore targets a real state and exercises its outgoing
edges. This is a material improvement over the interface-unverified order in 06o.

There is no current C2 runtime path: these commands are absent from the active
lifecycle map, authority subject map, reducers, and replay. That is expected at a
planning base and is not itself a finding. The plan correctly makes missing,
unreviewed, stale, or unaccepted successor contracts a hard stop at `06p:741-744`.

The campaign order also improves producer/consumer closure: C1 establishes the
dispatch/lease/attempt substrate; C2 owns operational completion and the
running-to-review handoff; C3 owns acceptance, authority promotion, Review/Decision
closure, and reopen epochs; R1 stays separately gated. The remaining defects are the
exact contracts at those boundaries, not the high-level order.

### 3.3 Routing, ownership, and review controls that pass

- Current task-tool metadata admits the named Sol Ultra, Terra Ultra/Max, Luna Max,
  and Codex Spark High assignments. Their risk/capability split is reasonable.
- Each campaign has one serial Terra owner for shared service, reducer, replay,
  projection, authority, receipt, and integration seams (`06p:341-344`, `398-400`,
  `450-452`, `484-486`). Luna and Spark leaves are narrow and conditional on frozen
  signatures and literal disjoint paths.
- Rows remain a complete census while dispatch is by bounded vertical capability,
  not one ticket per row (`06p:45-50`, `504-523`).
- The target of at most 90 changed files and hard stop before 100, semantic PR-stack
  boundaries, fresh reviewer with no author history, one remediation limit, and
  PR-ready handoff are explicit (`06p:603-634`, `737-759`, `778-802`).
- Provider, credential, Jira, PR creation, CodeRabbit, merge, owner acceptance,
  Gate 6, and W11 authority are not silently granted, apart from the narrower
  implementation-start composition in M-1.

### 3.4 Direct checks

Two existing exact contract controls were run from the repository virtual environment
with cache and coverage disabled and bytecode writes suppressed:

```text
tests/research_system/contracts/test_wp6_1_contract_materialization.py::test_wp6_1_materialization_binds_exact_104_row_multiset_and_182_expanded_edges
tests/research_system/contracts/test_wp6_1_stage2_owner_acceptance.py::test_wp6_1_stage2_owner_acceptance_preserves_the_accepted_core_tree
```

Result: `2 passed in 13.20s`. These checks support the catalogue and protected-byte
claims only; they do not certify the future contracts identified below.

## 4. Severity-ranked findings

### M-1 - Major - plan acceptance can be composed into implementation and dispatch authority

1. **Claim.** The plan preserves the rule that planning and owner acceptance are
   distinct, but later text makes acceptance sufficient to start contract/test
   materialization and C1. It does not require a separate exact implementation-start
   and dispatch decision.

2. **Direct evidence.** `06p:22-25` says the plan authorizes no runtime or tests.
   `06p:168-171` then says plan acceptance authorizes the manager to materialize and
   submit all successor subjects, including the routing validator and tests named at
   `06p:569-574`. `06p:797-802` says a fresh manager begins the semantic-freeze
   programme and C1 after the remaining plan acceptance. The governing 06a plan says
   its owner-approved content authorizes no implementation and leaves implementation
   and materialization gates open (`06a:4-15`). The accepted stage-2 record is scoped
   to `exact_bytes_only` and sets both `dispatch_authorized` and
   `implementation_start_authorized` false
   (`.research-system/contracts/wp6-1-stage2-owner-acceptance-record.yaml:67-81`).

3. **Failure scenario.** A coordinator obtains owner acceptance of the revised plan,
   treats `06p:168-171` as authority to implement the routing schema/validator/tests,
   obtains exact-byte acceptance of the successor contracts, and treats
   `06p:797-802` as authority to dispatch C1. No separate owner record binds the exact
   base, subject, root, scope, paths, and write owner.

4. **Impact.** Planning approval and byte acceptance become implementation authority
   by composition, crossing the repository's explicit owner boundary.

5. **Required disposition.** Make plan acceptance eligibility evidence only. Require
   separate exact owner authority for validator bootstrap, contract/test
   materialization, and each implementation campaign.

6. **Exact proposed text.** Replace the authorizing sentences with:

   > Acceptance of this plan authorizes no file materialization, validator or test
   > implementation, task creation, or campaign start. A fresh coordinator may prepare
   > exact owner-decision packets only. Every successor acceptance remains exact-bytes-
   > only unless its owner record expressly grants more. Validator bootstrap and each
   > campaign implementation require a separate owner start/dispatch record naming the
   > exact base, subject, authorized root, literal paths, scope, and write owner.

7. **Affected decisions/contracts.** 06a/P-036, D-G6-3, stage-2 exact-byte acceptance,
   `campaign-routing-ledger-v1`, and all successor subject acceptances.

8. **Affected work packages.** WP6.1 semantic freeze, routing bootstrap, C1-C3, and R1.

### M-2 - Major - C2 leaves the initial Artefact authority tuple underdetermined

1. **Claim.** Forcing only `use_authority=candidate` does not define the required
   initial values or derivations for the rest of the protected Artefact authority
   object.

2. **Direct evidence.** `RegisterArtefact` requires the manifest's `authority` object
   and all six authority dimensions plus `accepted_scope` and
   `consumer_restrictions`
   (`.research-system/schemas/core/commands/register_artefact.schema.json:171-208,375-465`;
   the event mirrors the same required shape at
   `.research-system/schemas/core/events/artefact_registered.schema.json:376-465`).
   Values including `integrity=verified`, `structural_validation=passed`, and
   `scientific_review=approved` are schema-valid. 06i only states that registration
   rejects or ignores caller-selected initial use authority and recomputes provenance
   (`06i:140-145`). `06p:163,376-390` forces `candidate` and denies scientific-review
   and consumer authority, but gives no exact initial value, evidence rule, or
   reject/recompute treatment for the other dimensions, scope, or restrictions.

3. **Failure scenario.** A caller supplies `use_authority=candidate` alongside
   `scientific_review=approved`, `integrity=verified`, and
   `structural_validation=passed`. One implementation preserves the schema-valid
   values; another silently overrides them. Both can claim conformance to the plan,
   but they produce materially different replay and projection authority.

4. **Impact.** A producer can self-attest validation or Review authority, or an
   implementer must invent defaults that the plan itself prohibits at `06p:743-744`.

5. **Required disposition.** Freeze the complete initial authority tuple before C2,
   including scope/restrictions and evidence provenance. Do not rely on later C3
   promotion controls to repair false registration history.

6. **Required interface text.** Add to `execution-outcome-handoff-v1`:

   > For every required Artefact authority field, the contract enumerates the exact
   > initial value or owner-authoritative derivation and states whether a caller value
   > is rejected, recomputed, or evidence-validated. It defines canonical initial
   > accepted scope and consumer restrictions and proves that Review, validation,
   > integrity, regenerability, availability, and consumer status cannot be
   > self-attested. If the protected identity cannot express the accepted semantics,
   > C2 stops for a separately versioned successor identity.

7. **Affected decisions/contracts.** W2 Artefact state, 06i registration authority,
   `execution-outcome-handoff-v1`, and `artefact-review-decision-authority-v1`.

8. **Affected work packages.** C2 registration/replay/projection and C3 authority
   promotion/consumer firewall.

### M-3 - Major - the proposed Review/Task joins cannot yet justify `review_pending`

1. **Claim.** C2 correctly requires a real `review_pending` transition, but neither
   the protected command shapes nor the proposed minimum successor contract defines
   the exact non-empty and current joins required to emit it.

2. **Direct evidence.** `RequestReview` represents subject IDs and hashes as
   independent arrays and does not require non-empty members
   (`.research-system/schemas/core/commands/request_review.schema.json:29-46`). Its
   immutable Review bar includes governing versions, evidence lanes, reviewer
   eligibility, visibility, verdict, and satisfaction authority (W2 `:207-215` and
   `:734-754`). `SubmitForReview` carries independent Artefact ID/hash arrays and
   Review IDs without Review hashes; none has a non-empty or bijection constraint
   (`.research-system/schemas/core/commands/submit_for_review.schema.json:8-57`).
   `06p:163,376-390` says only that the request creates an exact identity/subject hash
   and submission binds a terminal Attempt, registered Artefacts, and requested
   Reviews. C3 separately owns Review/Decision separation and the Task acceptance set
   (`06p:164-165`).

3. **Failure scenario.** A schema-valid request has empty or mismatched subject
   arrays. A submission cites no Artefacts or Reviews, an unrelated Review, mismatched
   Artefact ID/hash cardinalities, or a stale Task revision. A shallow existence check
   still emits `TaskSubmittedForReview`, creating `review_pending` without the claimed
   Attempt/Artefact/Review closure. Alternatively C2 freezes an immutable request bar
   that C3 later rejects.

4. **Impact.** The named C2 end-to-end capability can pass while its central state
   transition lacks authoritative evidence. Replay and projections can preserve a
   false review state rather than detect it.

5. **Required disposition.** Complete the join contract before C2 and either move the
   required Review-request bar upstream or accept the relevant C3 authority section
   before C2.

6. **Required interface text.** Add:

   > The handoff freezes non-empty canonical `(subject_id, subject_hash)` tuples; exact
   > Task revision and hash; terminal Attempt plus terminal event, epoch, and outcome;
   > the exact registered Artefact ID/hash set produced by that Attempt; and the exact
   > current requested Review ID/hash set whose subjects cover the same
   > Task/Attempt/Artefact closure. Cardinality, currency, ownership, completeness,
   > additional-member, order, or hash failure produces no event, receipt, object,
   > projection, index, or lock residue. The immutable Review-request bar and its
   > governing-version identities are fixed before C2 implementation.

7. **Affected decisions/contracts.** W2 Task/Attempt/Artefact/Review state,
   `execution-outcome-handoff-v1`, projection contracts, and the C3 Review authority
   subject.

8. **Affected work packages.** C2 public review handoff and C3 Review/Decision
   satisfaction and acceptance.

### M-4 - Major - the 06i partial cutover has no exact gate amendment or satisfaction witness

1. **Claim.** Calling the future handoff an "owner-approved 06i partial-cutover
   amendment" does not define whether it satisfies or supersedes the current 06i and
   P-044 gate chain.

2. **Direct evidence.** 06i makes Stage A conditional on accepted 06h, independent
   exact-subject acceptance, G-RM-3, and an accepted decision-register amendment, then
   separately blocks runtime on G-RM-14 acceptance of exact candidate bytes
   (`06i:9-16,51-92`). P-044 permits only inert candidate authoring and grants no
   Stage B/runtime authority (`03-decisions-and-open-questions.md:875-905`). A later
   exact owner record closes G-RM-3 only and explicitly does not close G-RM-14 or
   dispatch a stage
   (`reviews/rm-lane-pr198-g-rm-3-owner-acceptance-2026-07-31.md:72-86`).
   `06p:163,373-379` names no decision-record ID/hash, exact 06i candidate, G-RM-14
   witness, or supersession mode.

3. **Failure scenario.** One coordinator treats generic owner acceptance of the new
   handoff contract as the 06i amendment and begins C2; another correctly sees the
   current decision register still blocking runtime and stops. The same accepted plan
   therefore produces conflicting authority decisions.

4. **Impact.** C2 can either cross a live owner gate or become indefinitely
   non-dispatchable. Contract review is silently substituted for a distinct policy
   decision.

5. **Required disposition.** Bind one explicit owner-approved gate route and its exact
   evidence before the handoff can count as accepted for C2.

6. **Required interface text.** Require the handoff to carry an accepted decision
   record ID, Git blob/raw hash, effective scope, and `cutover_mode`:

   > `preserve_06i` requires exact evidence for accepted 06h, closed G-RM-3, accepted
   > Stage A bytes, and closed G-RM-14 before bounded runtime use. `supersede_06i`
   > requires a new Stephen-approved decision that names the superseded predicates and
   > grants only the C2 registration/request/submit scope. Generic contract acceptance
   > or review cannot satisfy either route.

7. **Affected decisions/contracts.** P-044, G-RM-3, G-RM-14, 06i Stage A/B, 06h,
   `execution-outcome-handoff-v1`, and the decision register.

8. **Affected work packages.** C2 and the later C3 06i consumer-firewall integration.

### M-5 - Major - the strict routing ledger proves declarations, not authority or actual execution

1. **Claim.** The ledger schema and validator invocation cannot enforce several
   failures they claim to reject because both expected and observed facts come from
   manager-authored declarations.

2. **Direct evidence.** The schema sketch at `06p:541-563` records requested model,
   thinking, base, paths, and integration owner, but no independent owner-acceptance
   witness, routing class, write owner, candidate subject, task/thread ID, observed
   model/thinking, fork/independence receipt, or actual changed/generated paths. The
   command at `06p:585-593` receives only manager state, the ledger, workspace, and
   base. Nevertheless `06p:576-583` claims rejection of unaccepted hashes, routing
   failures, and generated-output collisions, while `06p:682` separately requires an
   actual model/task/thread ledger. Campaign state is explicitly advisory
   (`06p:289-314`), and its current checker verifies state identity/status but returns
   advisory results (`shared/manager_dispatch_check.py:312-323,373-391`).

3. **Failure scenario.** A copied, stale, revoked, or wrong-subject hash appears in
   both the state and ledger and passes equality. A Luna/Max request launches under a
   different model, or a worker changes a generated/out-of-scope path, but no
   independent creation receipt or integration-time diff exists for the validator to
   compare.

4. **Impact.** The central routing and path-collision gate can report success without
   proving accepted authority, actual model routing, reviewer independence, or actual
   ownership of the integrated result.

5. **Required disposition.** Separate planned, launched, and integration validation.
   Keep the manager state advisory; obtain actual facts from independent records and
   Git at the relevant phase.

6. **Required interface changes.** Add:

   - exact owner-acceptance witnesses for every freeze subject, including subject ID,
     blob/raw hash, effective scope, current/revoked state, and accepting owner;
   - `routing_class` with conditional model/thinking/path rules and the complete
     dispatch envelope: exact subject, write owner, root, branch, paths, dependencies,
     validation tiers, review owner/cap/cycles, context/fork policy, and stop rules;
   - a persisted task-creation receipt with actual task/thread ID, model, thinking,
     exact base/root/branch, fork mode, and reviewer/author history identity; and
   - integration-time computation of `HEAD`, ancestry, actual diff, and generated
     paths against the literal allowlist.

   Add negative controls for copied-but-unaccepted hashes, stale/revoked/wrong-subject
   acceptance, requested/observed model mismatch, a valid pair in the wrong routing
   class, reviewer identity/history collision, wrong write owner, and actual
   out-of-allowlist changes. The bounded serial Sol/Terra bootstrap exception at
   `06p:595-601` may remain after its own exact owner start authority is added.

7. **Affected decisions/contracts.** `campaign-routing-ledger-v1`, standalone
   dispatch-envelope rules, task creation, integration, and independent review.

8. **Affected work packages.** Routing bootstrap and every C1/C2/C3/R1 packet.

### M-6 - Major - post-C3 is a 102-row audit, not zero-row portfolio closure

1. **Claim.** The plan names the audit after C3 a zero-row closure even though R1's
   two rows remain deliberately inactive.

2. **Direct evidence.** The exact arithmetic is `19 + 23 + 28 + 32 = 102`; R1 retains
   `operator.create_backup` and `operator.verify_restore`. Yet `06p:692-713` calls the
   post-C3 audit portfolio closure, requires evidence across all 104 rows, and makes
   its result evidence for KAN-65/Gate 6. Its active-binding bullet at `06p:700-701`
   enumerates only pre-Message, Message, and C1-C3 rows. No final whole-portfolio audit
   follows accepted R1.

3. **Failure scenario.** The audit passes at the post-C3 composed head while both R1
   rows remain inactive. R1 later changes the runtime after the purported exact
   portfolio closure, with no fresh all-row composed-head audit.

4. **Impact.** A materially incomplete active portfolio can be presented as zero-row
   and as Gate 6 decision evidence; later recovery activation escapes the declared
   final integration check.

5. **Required disposition.** Treat post-C3 as core-lifecycle integration, not final
   portfolio closure. Add final closure only after separately accepted R1.

6. **Exact proposed text.** Rename section 9.1 to `102-row core-lifecycle integration
   audit after C3`; require exact equality for those 102 active rows, assert exactly
   the two named R1 rows remain inactive, and remove zero-row/Gate 6 closure language.
   Add a post-R1 audit on the exact composed head requiring active-binding equality for
   all 104 rows plus the full replay, projection, authority, protected-byte, recovery,
   ancestry, diff-census, and independent-review evidence set.

7. **Affected decisions/contracts.** Catalogue activation, R1 boundary, KAN-65, and
   Gate 6 evidence.

8. **Affected work packages.** C3 integration, R1, and final WP6.1 closure.

### m-1 - Minor - the routing schema path conflicts with repository convention

1. **Claim.** The plan places a JSON Schema in the contract-record directory without
   defining an exception.
2. **Evidence.** `06p:572` names
   `.research-system/contracts/wp6-1-campaign-routing-ledger.schema.json`; current
   contract JSON Schemas are under `.research-system/schemas/contracts`, while the
   record directory contains no `*.schema.json` convention.
3. **Failure scenario.** Discovery, packaging, or registry checks omit the new schema
   because its path is outside the canonical schema tree.
4. **Impact.** This is a local integration and discoverability defect, not an authority
   bypass by itself.
5. **Required disposition.** Use the canonical contract-schema directory or document
   and test an explicit repository-wide exception.
6. **Exact proposed path.** Prefer
   `.research-system/schemas/contracts/wp6-1-campaign-routing-ledger.schema.json`.
7. **Affected contracts.** `campaign-routing-ledger-v1` packaging and discovery.
8. **Affected work packages.** Routing bootstrap only.

## 5. Decision audit

| Candidate decision | Review disposition | Reason / required action |
|---|---|---|
| Replace P2-P8 row order with capability campaigns | retain | Producer/consumer order is materially stronger. |
| Preserve ten-family semantic ownership map | retain | It remains ownership, not dispatch order. |
| Exact 104/19/85 census and 23/28/32/2 allocation | retain | Independently exact, unique, complete, and disjoint. |
| C1 substrate before C2 operational handoff | retain | Dependency direction is sound. |
| C2 creates and exercises real `review_pending` | amend | Retain the goal; close M-2 through M-4 before dispatch. |
| Terra central owner plus bounded Luna/Spark leaves | retain | Suitable if M-5 supplies actual routing/path evidence. |
| Strict routing-ledger bootstrap | amend | Preserve bounded bootstrap; validate authority and actual execution, not declarations alone. |
| Plan acceptance starts freeze/C1 | reject | Replace with separate exact owner start/dispatch records under M-1. |
| Post-C3 zero-row closure | reject | It is a 102-row audit; final closure belongs after R1. |
| R1 stays separately gated | retain | Add the post-R1 whole-portfolio audit. |
| Hard PR cap and independent review | retain | Bounded, enforceable, and correctly separate from owner acceptance. |
| W11/provider/Jira/PR/CodeRabbit/merge non-authorities | retain | Explicit and correctly bounded. |

## 6. Consistency and enforcement matrix

| Invariant | Named enforcement | Direct review result |
|---|---|---|
| 104 normalized rows / 182 expanded edges | accepted catalogue, exact-set tests | pass |
| 19 active / 85 remaining | active registry and lifecycle maps | pass |
| C1/C2/C3/R1 exact partition | independent parser/set comparison | pass |
| protected command/event bytes | Git tree equality and contract test | pass |
| real `review_pending` source and outgoing edges | W2 + 06d + C2 public journey | design passes; exact evidence join blocked by M-3 |
| no producer Artefact authority | future outcome-handoff contract | fail: M-2 |
| 06i owner-gate currency | exact decision record and acceptance witness | fail: M-4 |
| no implementation by plan/byte acceptance | separate exact owner start record | fail: M-1 |
| actual model, task, path, and reviewer routing | strict routing validator | fail: M-5 |
| one serial central owner | campaign path ownership and collision gate | pass in design; actual proof depends on M-5 |
| PR target `<=90`, hard `<100` | pre-integration changed-file census | pass in design |
| final 104-row closure | post-R1 exact composed-head audit | absent: M-6 |
| W11 remains inert and separate | explicit stop/non-authority | pass |

## 7. Required revision sequence

1. Correct the authority composition in M-1 before treating any plan acceptance as a
   work-start signal.
2. Expand `execution-outcome-handoff-v1` to close the full initial Artefact tuple and
   exact Review/Task joins in M-2 and M-3.
3. Obtain or specify the exact owner decision route that preserves or supersedes 06i
   under M-4; do not encode the answer through implementer choice.
4. Redesign the routing package into planned, launched, and integrated evidence phases
   with the negative controls in M-5, and canonicalize its schema path.
5. Rename the post-C3 audit and add the final post-R1 104-row audit under M-6.
6. Bind the revised plan to a new exact commit/tree/blob/raw hash and obtain a fresh
   independent adversarial review. This reviewer must not review its own remediation.

The corrected plan can retain the 23/28/32/2 allocation, current model assignments,
single central owners, bounded leaves, PR cap, capability stacks, protected bytes,
W11 separation, and forward-obligation register.

## 8. Residual risks and non-authorities

Even after plan correction, every proposed successor subject is currently absent and
therefore remains a hard stop until exact bytes exist, are independently reviewed,
and receive the required separate owner decision. The model inventory and current
runtime seams can change before dispatch and must be re-resolved at each exact base.
Future schema materialization does not activate runtime bindings. Passing schema,
catalogue, or contract tests cannot establish authority behavior without public
producer-to-ledger-to-replay/projection evidence.

Acceptance of this review report would accept only the review's exact evidentiary
record. It would not accept a revised plan, any future contract, implementation, PR,
merge, provider operation, Jira transition, CodeRabbit action, Gate 6 transition, R1
cutover, research execution, or result claim.

## 9. Review evidence and change boundary

- Exact Git identity checks: cwd, symbolic branch, candidate, parent, tree, plan blob,
  and clean status.
- Raw-byte audit: size, UTF-8 validity, BOM absence, LF-only endings, terminal LF, and
  SHA-256.
- Historical exact-object checks: accepted 06m and superseded 06o via their pinned
  `SHA:path` identities.
- Static catalogue reconstruction: 104/104 unique, 19 active, 85 remaining,
  23/28/32/2 exact allocation, zero overlap/missing/extra.
- Direct code/schema inspection: registry activation, lifecycle map, authority map,
  W2 states, RequestReview, SubmitForReview, RegisterArtefact, 06a, 06d, 06i, P-044,
  G-RM-3 owner record, W11, and manager dispatch checker.
- Focused immutable-subject controls: two exact tests passed as recorded in section
  3.4.
- Review write boundary: this report only; no remediation and no self-review.
