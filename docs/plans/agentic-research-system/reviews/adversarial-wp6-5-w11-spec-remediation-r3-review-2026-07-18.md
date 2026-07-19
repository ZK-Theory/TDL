# Adversarial WP6.5 W11 remediation R3 review

**Review date:** 2026-07-18
**Reviewer posture:** fresh, distinct-authority, adversarial remediation re-review
**Target repository:** `TDL`
**Assigned review branch:** `review/ars-wp6-5-w11-spec-r3`
**Exact reviewed commit:** `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b`
**Exact reviewed parent / preserved R2-report commit:** `1fc0ca44c4700e6522ac15d04e2cdc622f2263c5`
**Base authority:** `4e6fd0cb26c04ff9707c3183f663461d752b53b9`
**Approved normative WP6 revision:** `fe5f1d40bc8f05f061317c677b5891cea0711249`
**Subject branch / PR:** `pipe/ars-wp6-5-w11-spec` / draft PR #121
**Immutable R1 report blob:** `8af8add2bd1853b4aaf6b0178279013256dfb044`
**Immutable R2 report commit/blob:** `ecbad093182110b8a7474304f20e10f64981d7bd` / `3d15046c937672f3a7a1519f65e739a586374248`
**Review evidence status:** `Complete` (CodeRabbit's current-head substantive scan was skipped because PR #121 is draft; that scanner status is recorded, not treated as review evidence)
**Verdict:** `rework_required`
**Finding count:** **0 Critical, 6 Major, 0 Minor**

## 1. Executive verdict

Commit `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b` is materially stronger than the
R2 subject but is **not safe to accept as the W11 specification revision**. Revision
0.3 successfully separates dossier content from its external observation, review and
acceptance; makes the legacy inventory source-only; defines a concrete pre-request
Assay rubric/scope authority with prospective=actual producer binding and staleness;
enumerates 82 literal owner rows; and adds explicit Partial/cancellation/revisit text.
Those repairs should be preserved.

Fresh reconstruction nevertheless finds six acceptance-blocking defects:

1. kind-specific relation/catalogue hash clauses reintroduce two strongly connected
   hash components and one self-edge beneath the otherwise sound section 3.6 DAG;
2. the schema catalogue must be accepted by W11 commands/reducers/handlers before any
   such runtime may exist, so its own acceptance has no authorized producer;
3. the 82-row owner annex disagrees with the separately closed W4 allowlist and with
   several event/reducer-to-projection relations, and it still does not freeze literal
   per-row negative/mutation test identities;
4. cancelled Assay and Spike outcomes require independent review before revisit, but
   no cancellation-review request/verdict owner rows exist;
5. Spike Partial leaves its attempt/lease open, while cancellation in the pending
   execution-Decision window leaves a proposal that blocks revisit; and
6. a new human annotation can arrive after the accepted cutover closure's empty-set
   observation and before cutover, yet `CutOverDiscoveryPath` does not re-observe or
   fence that namespace.

These are Major rather than Critical because the specification has not been
implemented and its most natural behavior is to fail closed or become unconstructible.
They remain blocking: implementing around them requires new hash-preimage, bootstrap,
authority, projection, review-lifecycle, operational-resource and cutover-epoch
decisions that W11 claims already to have frozen.

**Required disposition:** revise W11 and obtain a fresh exact-commit independent
review. Do not accept D-G6-4 limb 1 for `3e068c1...`; keep limb 2 open; do not merge PR
#121; do not start schema/catalogue materialization, WP6.6, WP6.7, admission,
ingestion, transition or cutover.

## 2. Review identity, direct evidence, and currency

### 2.1 Worktree and exact-revision precondition

The authorized worktree was
`C:\Users\steph\.codex\worktrees\82f8\TDL`. It initially had detached `HEAD`.
Detached `HEAD` and
`refs/heads/review/ars-wp6-5-w11-spec-r3` both resolved exactly to
`3e068c1ee5100e5a6e0bc57d0d047d993b406b2b`; the worktree was clean. The single
permitted deterministic `git switch review/ars-wp6-5-w11-spec-r3` succeeded. Symbolic
branch, exact `HEAD`, cwd and clean status were rechecked before the report write.

`git ls-remote` and PR #121 both reported the subject head at exact commit `3e068c1...`.
The approved normative revision `fe5f1d4...` is an ancestor of base authority
`4e6fd0c...`, which is an ancestor of the reviewed subject.

### 2.2 Immutable prior-review provenance

| Artefact | Original | Preserved lineage | Reviewed target | Result |
|---|---|---|---|---|
| R1 report | commit `21ebc46...`, blob `8af8add...` | cherry-pick lineage `7db8b05...` | blob `8af8add...` at `3e068c1...` | byte-identical |
| R2 report | commit `ecbad09...`, blob `3d15046...` | cherry-pick commit `1fc0ca4...`, blob `3d15046...` | blob `3d15046...` at `3e068c1...` | byte-identical |

The prior reports were read as finding/provenance records, not inherited proof. The
complete 1,765-line W11 subject, both immutable reports, all companion changed files,
and the relevant W1/W2/W4/W5/master owner sections were checked directly.

### 2.3 Live evidence fidelity

| Evidence | Independent R3 observation | Disposition |
|---|---|---|
| TDA-scale package manifest | 5,843 bytes; SHA-256 `e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf` | exact register match |
| TDA-scale master component | 28,244 bytes; SHA-256 `277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea` | exact register match |
| Manifest-linked sources/components | 20 resolved; 20 hash matches; 0 missing/mismatched | direct evidence only, not admission |
| Registered vault root | `Directory, ReparsePoint`; junction to `C:\Users\steph\Documents\TDA-Research` | positive registered-root fixture remains necessary |
| Proposed ARS Discovery namespaces | all three absent | no namespace/state creation |
| Living Discovery backlog | now 27,511 bytes; SHA-256 `c63cc9e67406ad1fa0798f09693964a83d5dbb4c493eb049738c7b6394bb6c1a` | accessible currency divergence from dated 26,392-byte `37eec1...9e7`; correctly non-authoritative |

The backlog divergence is not a defect in the dated register: both the register and
W11 explicitly classify that hash as a mutable observation and require fresh
handle-bound bytes for migration. No live file was written.

### 2.4 PR and scanner state

PR #121 was open, draft, mergeable, and based on `main`, with exact head
`3e068c1...`. Codacy's current-head check run `88072293253` completed `success`, reported
zero annotations and “Codacy found no issues in your code.” CodeRabbit's current-head
status was `success` only because review was skipped for a draft PR. Its one unresolved
thread is outdated and targets `d24df9...`; the malformed table it names now passes the
independent table parser. Three threads are resolved, and three of the four total
threads are outdated. No PR state, comment, checkbox, review request or scanner setting
was changed.

## 3. Findings summary

| ID | Severity | Finding | Reopens / blocks |
|---|---|---|---|
| R3-M1 | Major | Kind-specific relation/catalogue hashes have no acyclic preimage | R2-M2/M4; I02/I04/I12/I16/I18; tests 1/3/4/15/18 |
| R3-M2 | Major | Schema-catalogue acceptance requires the runtime it prohibits until after acceptance | R2-M4; I12/I22; tests 1/3/11; WP6.6 |
| R3-M3 | Major | Owner rows disagree with W4 allowlist/projection/test identity authority | R2-M4/M5; I04/I12; tests 1/3/4/11 |
| R3-M4 | Major | Cancelled outcomes have no independently reviewed route to revisit | R2-M5; I04/I06; tests 4/7/11 |
| R3-M5 | Major | Spike Partial/cancellation do not close attempts and pending Decisions | R2-M5; I06; tests 4/7/11 |
| R3-M6 | Major | Cutover closure can stale on a late human annotation | R1-C2/R2-M2; I18; tests 13/18; D-G6-4 limb 2 |

## 4. Major findings

### R3-M1 — Kind-specific hashes reintroduce cyclic preimages

1. **Claim.** The general section 3.6 authority graph is acyclic, but three later
   “complete row/content” hashes do not define an acyclic preimage. The mapping and
   schema-catalogue clauses create literal hash SCCs; `assay_relation_hash` is stored
   on the same complete row it hashes without an exclusion rule.
2. **Evidence.** The common envelope defines `content_hash` over every canonical field
   except itself at W11 lines 185 and 295–296. A
   `LegacyTransitionMappingContent.transition_relation_hash` is then defined over the
   “complete P0 canonical content row” at line 1148, so common `content_hash` requires
   the relation hash while the relation hash requires both itself and common
   `content_hash`. `W11SchemaCatalogueContent`, also a common `*Content` candidate,
   adds `catalogue_content_hash` that “excludes only itself” at line 1434, creating
   `content_hash <-> catalogue_content_hash`. `AssayRequested` stores an
   `assay_relation_hash` “over the complete row” at line 616 with no named excluded
   field.
3. **Concrete failure scenario.** A materializer serializes mapping content with a
   placeholder relation hash, computes common content hash, inserts both and changes
   both preimages. The catalogue repeats the same fixed-point problem across its two
   full-content hashes. A conforming implementation must omit a required field, invent
   an undeclared preimage subset or accept an arbitrary producer-supplied digest.
4. **Impact.** No literal OR-128 mapping or OR-140 catalogue positive fixture can be
   content-addressed as written; the stored transition/Assay relation that is meant to
   reject foreign-valid substitution is ambiguous. This reopens the R2 hash-DAG and
   catalogue closures.
5. **Required disposition.** **Fix now; fresh review required.** Preserve the external
   content/file/review/acceptance ordering but make every derived-hash preimage a
   separately enumerated acyclic relation.
6. **Exact proposed interface change.** Delete `catalogue_content_hash` and use the
   common `content_hash`, or define it as an equality alias that is not serialized into
   either preimage. For mapping and Assay relations, enumerate the exact relation
   fields and state that the relation digest excludes itself and every enclosing
   record/event hash. Require an independent topological-sort fixture to report zero
   self-edge/SCC.
7. **Affected decisions/work packages.** P-032/P-034; D-G6-4 limbs 1/2; WP6.5–WP6.7;
   R2-M2/R2-M4; W11-I02/I04/I12/I16/I18; tests 1, 3, 4, 15 and 18.
8. **Owner action.** No owner-decision reversal is needed if these are clarified as
   canonical preimage corrections; any choice to retain two independently computed
   full-content hashes requires a new owner-approved staged-identity design.

### R3-M2 — Schema-catalogue acceptance has no authorized producer

1. **Claim.** W11 requires a typed `W11SchemaCatalogueAccepted` event before any W11
   runtime registry, reducer, projector or handler is produced, but that event itself
   can be produced only through W11-specific commands, reducers and projections.
2. **Evidence.** OR-140–OR-145 at lines 532–537 register, observe, review, propose and
   resolve the catalogue through command/event/reducer/projection rows. Section 8.2
   then says OR-141–OR-145 obtain external acceptance and **only after**
   `W11SchemaCatalogueAccepted` may a runtime registry, reducer, projector, handler,
   test-discovery mechanism or observed implementation interface be produced (lines
   1416–1419). W2 is the sole mutation boundary (W11 line 125); a schema file by itself
   does not execute those commands. The approved WP6.1 owner-source precedent instead
   has Stephen accept exact Git paths/blobs/SHA-256 for the schema/catalogue manifests
   under D-G6-3 before runtime implementation (`06a-wp6-1-runtime-task-lifecycle-plan.md`
   lines 157–166); it does not require the gated runtime to emit its own prerequisite.
3. **Concrete failure scenario.** All schema bytes and catalogue content exist. OR-140
   cannot run because its handler/reducer is prohibited pre-acceptance. Creating a
   temporary/bootstrap handler violates step 6 and makes the implementation help
   accept the expected authority that governs it. Recording only a Git review and
   Stephen decision does not satisfy the required OR-145 typed acceptance tuple.
4. **Impact.** The accepted-catalogue prerequisite for every later runtime has no
   topologically earlier producer. WP6.6 and all later authority lifecycles are
   permanently blocked or require an unreviewed bootstrap exception.
5. **Required disposition.** **Fix now; owner choice and fresh review required.** The
   bootstrap trust boundary must be explicit, not inferred by the materializer.
6. **Exact proposed interface change.** Either (a) define a pre-runtime Git/blob review
   and Stephen-Decision acceptance envelope whose exact bytes are the Stage-E authority
   and later import it through an independently verified genesis operation, or (b)
   authorize a minimal generic W2 bootstrap command path already accepted before W11,
   name its exact schemas/handlers/reducers and prove that it cannot derive expected
   rows from W11 runtime. Do not use OR-140–OR-145 before their producer exists.
7. **Affected decisions/work packages.** P-026/P-032/P-036; D-G6-4 limb 1; WP6.5/
   schema materialization/WP6.6; R2-M4; W11-I12/I22; tests 1, 3 and 11.
8. **Owner action.** Stephen must accept the chosen bootstrap authority because it
   changes the acceptance medium and trust sequence, not merely wording.

### R3-M3 — The complete owner catalogue disagrees with its authority surfaces

1. **Claim.** The 82 literal rows are count-complete but not relation-complete: four
   review-request rows are denied by the separately declared complete Portfolio
   Steward allowlist, three Candidate-changing rows omit the Candidate projection, and
   per-row negative/mutation test identities remain abstract.
2. **Evidence.** The independent oracle found exactly 82 unique rows (OR-001–OR-037,
   OR-101–OR-145), five cells per row, 82 unique receipts, 82 implied positive IDs and
   82 implied retry IDs. OR-034–OR-037 assign
   `RequestDiscoveryOutcomeReview/*` to Portfolio Steward at lines 477–480, but the
   profile's “complete W11 command allowlist” at lines 1004–1011 omits that command and
   defaults every unlisted command to deny. OR-004, OR-005 and OR-007 emit Candidate
   events and name `U:candidate` but omit `P:candidate` at lines 447–450. Lines 433–436
   define literal positive/retry IDs, while the future catalogue requires literal
   `negative/mutation/retry test identities` at line 1431; no owner row contains an
   exact per-row negative/mutation ID.
3. **Concrete failure scenario.** A conforming W4 router denies all four review
   requests, so complete Assay/Spike evidence can never be independently reviewed and
   no promotion/revisit can proceed. If implementation widens the allowlist, it invents
   authority. Separately, a reducer advances Candidate state but the accepted owner row
   does not project it. A materializer must also invent negative test names or reuse
   one family ambiguously.
4. **Impact.** Normal and Partial lifecycles are unreachable under default-deny;
   accepted owner semantics and runtime projections can diverge while all row counts
   and unique identities pass.
5. **Required disposition.** **Fix now.** Reconcile the independent owner surfaces and
   repeat the complete-row multiset audit.
6. **Exact proposed interface change.** Add the four exact discriminants to Portfolio
   Steward's W4 allowlist; add `P:candidate` to OR-004/005/007 (or remove the Candidate
   event/reducer under an explicit alternative); and define a literal negative/
   mutation ID convention such as `W11-T<family>-OR-nnn-<mutation>` with at least one
   exact identity per row. Add allowlist-row, reducer-projection and test-ID joins to
   the expected catalogue.
7. **Affected decisions/work packages.** P-022/P-032; D-G6-4 limb 1; WP6.5/WP6.6;
   R2-M4/R2-M5; W11-I04/I12; tests 1, 3, 4 and 11.
8. **Owner action.** No human-authority expansion is recommended: the fix should make
   the already stated Portfolio Steward and Candidate effects consistent. Any different
   profile or effect requires explicit owner review.

### R3-M4 — Cancelled outcomes have no review producer

1. **Claim.** Both cancellation routes require an independently reviewed cancelled
   outcome before `ProposeRevisitDecision`, but the closed 82-row universe contains no
   review-request or review-verdict producer for `assay_cancelled` or
   `spike_cancelled`.
2. **Evidence.** Section 4.1 says `ProposeRevisitDecision` moves only an exact
   independently reviewed Partial or cancelled outcome. OR-009 and OR-023 require a
   reviewed outcome and no unresolved proposal (lines 452 and 466). The complete review
   owner set is OR-006/007/020/021/034–037: it covers `assay_scored`, `assay_partial`,
   `spike_verdict` and `spike_partial`, but no cancelled subject. Section 8.1 forbids an
   unlisted supporting command.
3. **Concrete failure scenario.** An Assay is cancelled while collecting. It reaches
   `assay_cancelled`; no authorized command can create the required review request or
   verdict. OR-009 cannot satisfy its reviewed-outcome precondition. Bypassing review
   violates section 4.1 and P-022; reusing the Partial review changes the subject.
4. **Impact.** Assay and Spike cancellation are terminal dead ends despite the stated
   RETRY/PARK/KILL recovery guarantee. This is exactly the R2-M5 failure class.
5. **Required disposition.** **Fix now.** Preserve cancellation evidence and add an
   executable, independent subject-specific review route.
6. **Exact proposed interface change.** Add request/verdict owner rows and relation
   schemas for `assay_cancelled` and `spike_cancelled`, with exact cancellation event,
   reason/evidence, aggregate relation and reviewer independence; or explicitly make a
   separately accepted cancellation record satisfy revisit and remove the contradictory
   “independently reviewed” requirement. Add full review/reject/unable-to-verify and
   RETRY/PARK/KILL tests.
7. **Affected decisions/work packages.** P-022/P-032; D-G6-4 limb 1; WP6.5/WP6.6;
   R2-M5; W11-I04/I06; tests 4, 7 and 11.
8. **Owner action.** If cancellation is allowed to bypass independent review, that is
   an authority-policy change requiring Stephen; adding exact review rows preserves the
   current policy.

### R3-M5 — Spike recovery leaves live operational and Decision state

1. **Claim.** Spike Partial and cancellation do not reconcile every outstanding
   cross-stream resource. Partial leaves the attempt/lease open. Cancellation after
   execution approval is proposed leaves the Decision proposal unresolved, while the
   next revisit command forbids unresolved proposals.
2. **Evidence.** OR-019 carries an exact `attempt` but emits only Spike/Candidate/
   artefact-use effects and has no attempt/lease close event, reducer or write set (line
   462). W11-I06 and test 7 explicitly require Partial/cancellation attempt closure
   (lines 1509 and 1548). OR-015 emits `DecisionProposed`; OR-022 may cancel an
   approval-pending Spike but emits no Decision withdrawal/rejection/supersession;
   OR-023 requires “no unresolved proposal” (lines 458, 465–466).
3. **Concrete failure scenario.** In path A, a running attempt reports PARTIAL and
   remains live while review/revisit begins, permitting lease renewal or another output
   against a terminalized aggregate. In path B, OR-015 proposes execution, OR-022
   cancels before Stephen resolves it, and OR-023 rejects because the proposal remains
   unresolved. Resolving the stale proposal would try to authorize a cancelled Spike.
4. **Impact.** The supposedly closed Partial/cancel state machine has an operational
   race and a deterministic dead end; retry may overlap a live predecessor or require
   hidden Decision cleanup.
5. **Required disposition.** **Fix now.** Every terminalizing edge must close or
   supersede all live attempts, leases and proposals atomically.
6. **Exact proposed interface change.** Add `SpikeAttemptClosed/partial` plus lease
   release and attempt/lease streams to OR-019. When OR-022 cancels in
   `approval_pending`, atomically withdraw/supersede the exact OR-015 Decision proposal
   and record the relation; alternatively prohibit cancellation in that window and
   define a separate authorized proposal-withdrawal command before cancellation. Test
   both race orders and lost-response retries.
7. **Affected decisions/work packages.** P-032; D-G6-4 limb 1; WP6.5/WP6.6; R2-M5;
   W11-I06; tests 4, 7 and 11.
8. **Owner action.** No promotion-authority change is needed if cleanup is mechanical;
   changing whether Stephen must resolve/withdraw a pending execution proposal requires
   an explicit policy decision.

### R3-M6 — Cutover closure can stale on a late human annotation

1. **Claim.** The cutover closure freezes an empty un-ingested annotation set, but
   human writers remain authorized to add inbox files after closure acceptance and the
   final cutover command does not re-observe or fence that set.
2. **Evidence.** The annotation inbox has attributed human writers and is mutable
   evidence at lines 1027–1029. `LegacyCutoverClosureContent` includes an
   “un-ingested-annotation set (necessarily empty)” at line 1285, and acceptance occurs
   through OR-135–OR-139. `CutOverDiscoveryPath` later reloads the DAG, final source
   observation, revocation and bijection under the legacy path lock (lines 1308–1312),
   but does not reload the annotation namespace, bind its source position or revoke/
   fence its writers.
3. **Concrete failure scenario.** Closure C records an empty inbox and is accepted.
   Before OR-033, a human creates a valid annotation targeting a remaining item. Legacy
   bytes and mappings remain unchanged, so OR-033's listed rechecks pass and cutover
   succeeds despite the new un-ingested annotation, contradicting closure condition 5.
4. **Impact.** Whole-path cutover can strand or silently bypass attributed human
   evidence even while claiming exact closure. This is a stale-observation race at the
   irreversible path gate.
5. **Required disposition.** **Fix now; fresh review required.** The annotation epoch
   must be defined relative to cutover without making annotations lifecycle authority.
6. **Exact proposed interface change.** Bind an annotation-inbox event position/
   directory identity and complete pending-set hash into the closure, then re-observe it
   under an accepted cutover fence immediately before commit. Either reject any delta
   or define a cutover epoch after which new annotations target successor state and are
   not part of legacy closure. Add after-closure/before-command and pre-commit race
   injections.
7. **Affected decisions/work packages.** P-004/P-021/P-032/P-034; D-G6-4 limbs 1/2;
   WP6.5/WP6.7/W9; R1-C2/R2-M2; W11-I18; tests 13 and 18.
8. **Owner action.** Stephen must accept the epoch policy because it determines whether
   a late human annotation blocks cutover or belongs to successor processing.

## 5. R2 finding re-test

| R2 finding | R3 disposition | Direct reconstruction |
|---|---|---|
| R2-M1 — dossier expected-set self-addressing | **Closed at specification level** | `DossierExpectedSetContent` has no own file/review/Decision/acceptance field; content -> independent file observation -> review -> Decision/typed acceptance -> later manifest is acyclic. |
| R2-M2 — inventory/mapping cycle | **Not closed; R3-M1** | Source-only inventory -> external acceptance -> mapping -> transition -> later closure is correctly ordered, but `transition_relation_hash` hashes the complete content row that contains both it and common `content_hash`. |
| R2-M3 — abstract Assay bar | **Closed at specification level** | Exact rubric and evidence-scope contents, independent file observations, review request/verdict, Stephen Decision, typed acceptance, prospective=actual producer relation, effective interval and staleness triggers precede `RequestAssay`. |
| R2-M4 — incomplete owner catalogue | **Not closed; R3-M1/M2/M3** | Row count and most tuples are literal, but catalogue hashes/bootstrap are unconstructible, four commands are absent from the closed W4 allowlist, Candidate projection relations drift, and negative identities remain abstract. |
| R2-M5 — cancellation/Partial dead ends | **Not closed; R3-M3/M4/M5** | Fresh aggregate IDs and atomic predecessor supersession pass, but review requests are default-denied, cancelled subjects lack review producers, Partial leaves its attempt open, and pending execution Decisions survive cancellation. |

## 6. R1 control re-test

| R1 finding/control | R3 disposition | Evidence |
|---|---|---|
| C-1 — dossier expected oracle | **Closed at specification level** | Complete six-family literal rows, independent producer/reviewer/acceptor, pre-observation acceptance and coordinated-candidate mutation resistance are defined without self file/acceptance bytes. |
| C-2 — complete whole-path inventory | **Partially closed; R3-M1/M6** | Source-only final-byte inventory, independent parser/reproducer and row bijection pass; mapping hash construction and late-annotation currency still block cutover. |
| M-1 — Assay/Spike aggregate identity | **Closed** | Canonical `asy_`/`spk_` IDs, streams, predecessor relations and fresh retry identities are exact. |
| M-2 — request-time Assay bar | **Closed** | OR-101–OR-109 and section 4.3 freeze exact accepted content/file/review/Decision/producer relations before collection and define expiry/staleness. |
| M-3 — source re-observation | **Closed** | Admission step 4 independently resolves and hashes every component and source; the R3 live oracle rehashed all 20 linked package files successfully. |
| M-4 — complete command/event/W4 catalogue | **Not closed; R3-M2/M3/M4/M5** | Exact count is present, but bootstrap, allowlist, projection, review-subject and resource-cleanup relations remain incomplete. |
| M-5 — stored transition relation | **Not closed; R3-M1** | Exact source-row/observation/target/Decision members are strong, but the stored relation digest has no acyclic preimage. |
| M-6 — Windows operation-time identity | **Closed at specification level** | Registered-root junction exception, no-follow traversal, volume/file IDs, hardlink/link-count checks, held parent, atomic replace, post-verification and phase-specific races remain normative. Required unavailable future coverage remains Partial. |
| m-1 — Paper Claim lane | **Closed** | Paper Claim is Required for governance/consumer non-compensation and authorizes no live claim activity. |
| m-2 — root evidence register | **Closed** | One tracked root register contains the dated addendum and exact limitations. Current backlog drift confirms why its hash is observational only. |

## 7. Exact authority and lifecycle reconstruction

### 7.1 Content/hash dependency DAG

The independent oracle treated `A -> B` as “A cannot be computed before B.” It
constructed 19 named nodes and 19 literal dependencies. The clean dossier sequence was:

```text
DossierExpectedSetContent
  -> independent file observation
  -> review request/verdict
  -> Stephen Decision + DossierExpectedSetAccepted
  -> later ResearchDossierManifest consumer
```

No candidate content contains its own storage, review, Decision, acceptance, lifecycle
state, sibling/later event hash or consumer result. The clean legacy authority order was:

```text
source observation
  -> source-only inventory content/file/review/acceptance
  -> mapping content/file/review/acceptance
  -> per-item transition
  -> later cutover closure content/file/review/acceptance
  -> CutOverDiscoveryPath
```

The oracle found three cyclic components introduced by later derived-hash clauses:

```text
{ mapping.content_hash, mapping.transition_relation_hash }
{ catalogue.content_hash, catalogue.catalogue_content_hash }
{ assay.assay_relation_hash }  # literal complete-row self-edge
```

The first two are explicit SCCs. The third is at minimum an undefined preimage: no
text excludes the stored relation hash from the “complete row” it hashes. No review,
acceptance or consumer-result edge otherwise points backwards.

### 7.2 Dossier and source authority

The exact six expected families are component, source, object, ScopeDefinition,
dependency-edge and relationship. Admission derives no expected count/hash/member from
the manifest, command or runtime; it independently reads both content/file authority
and candidate/source bytes. Missing, extra, duplicate, alias, path escape, stale,
incompatible, valid-foreign and coordinated candidate/runtime mutations are all
specified against the unchanged external expected tuple. Atomic W2 publication and
zero-publication failure remain complete.

### 7.3 Assay-bar authority

The pre-request authority reconstructs as:

```text
accepted W5 owner requirement/domain pack
  -> AssayRubricContent + AssayEvidenceScopeContent
  -> two independent file observations
  -> exact review request + I1 verdict
  -> Stephen assay_bar_acceptance Decision + AssayBarAccepted
  -> RequestAssay prospective=actual producer equality
  -> AssayEvidenceCollectionOpened
```

Rubric fields cover exact axes, value schemas, bounds, predicates, Partial/PARK/KILL
rules and deterministic RuleEvaluation identity. Scope fields cover every lane/evidence
row, source class, identity closure, producer context, freshness, validator, reviewer
grade, omissions, consumer restrictions and expiry. Content cannot assert review or
acceptance. Superseded requirements, domain pack/validator/grant/profile/context,
relationship or effective interval trigger staleness. Abstract, late, stale,
producer-mismatched and self-produced bars are rejected before collection. R3-M1 is
limited to the later `assay_relation_hash` preimage, not the bar authority ordering.

### 7.4 Assay/Spike recovery reachability

| Path | State/relation result | R3 result |
|---|---|---|
| Assay complete -> review -> PROMOTE/PARK/KILL | Exact aggregate/evidence/Decision relation exists | **Blocked operationally by R3-M3 allowlist omission** |
| Assay Partial -> distinct Partial review -> revisit | Partial remains Partial/`partial_reviewed` | **Blocked operationally by R3-M3** |
| Assay cancelled -> reviewed revisit | No cancellation-review owner row | **Dead end; R3-M4** |
| Assay RETRY | Fresh `asy_`; old superseded atomically with replacement | Pass once prior route exists |
| Spike complete -> distinct verdict review -> PROMOTE/PARK/KILL | Exact relation and PASS predicate | **Blocked operationally by R3-M3** |
| Spike Partial -> Partial review -> revisit | Partial stays Partial | **Attempt/lease not closed; R3-M5; review request also R3-M3** |
| Spike cancelled before proposal | Attempt closes when present | **No cancelled review; R3-M4** |
| Spike cancelled after OR-015 proposal | Cancellation leaves Decision pending; revisit forbids unresolved proposal | **Dead end; R3-M5** |
| Spike RETRY | Fresh `spk_`; old superseded atomically with replacement | Pass once prior route exists |
| PARK/KILL | Candidate terminal; no claim/promotion escalation | Pass locally |

No Partial is relabelled PASS/reviewed-complete, no retry reuses an aggregate ID, and
replacement/supersession is atomic. Those preserved controls do not cure the missing
review/resource/overlay transitions.

### 7.5 Whole-path cutover and physical identity

The source-only inventory contains final physical bytes, complete source-only rows,
unknown/unparseable blocker rows, independent parser/reproducer, byte coverage and no
mapping/owner/cutover back-edge. Each mapping binds one accepted inventory row,
observation, target, collision scan and migration authority. The later closure joins
every final row one-to-one to mapping acceptance and transition event after writer
revocation/final observation. `CutOverDiscoveryPath` holds the registered path lock and
rehashes that DAG before the atomic path events.

Windows safeguards are preserved: accepted root junction identity, no-follow nested
traversal, volume/file IDs, file-ID/hardlink/link-count checks, held parent, handle-
relative temporary/replace, post-replace verification, grant/registry/source-position
recheck and race injection after each phase. The unresolved cutover issue is orthogonal:
the separately human-writable annotation namespace is not part of the final locked
re-observation (R3-M6).

## 8. Complete 82-row owner-catalogue audit

The independent parser authored the expected row universe as OR-001–OR-037 plus
OR-101–OR-145, not from a runtime registry. Results: 82 rows, 82 unique IDs, no gap or
extra, five Markdown cells each, 34 command-schema identities, 82 unique receipt
identities, 82 implied literal positive IDs, 82 implied retry-producer IDs, 86 explicit
W11 event references/82 unique event tokens, and no missing command/reducer/projection/
receipt cell. Shared W2 review/Decision facts were recognized as owner events rather
than falsely counted as absent. No literal per-row negative/mutation ID was present.

`PASS` below means the committed command/schema, profile/subject, precondition,
ordered-event/write-set, reducer/projection, receipt and positive/retry/family binding
were all independently inspected with no additional row-local defect. It does not
authorize implementation. A finding label identifies the exact failed join.

| Row | Command / schema | R3 tuple disposition |
|---|---|---|
| OR-001 | `RegisterCandidate` / `C:register-candidate` | PASS |
| OR-002 | `SupersedeDiscoveryRecord/candidate` / `C:supersede-discovery-record` | PASS |
| OR-003 | `RequestAssay/initial` / `C:request-assay` | PASS |
| OR-004 | `RecordAssayScore` / `C:record-assay-score` | R3-M3: Candidate projection omitted |
| OR-005 | `RecordAssayPartial` / `C:record-assay-partial` | R3-M3: Candidate projection omitted |
| OR-006 | `ReviewDiscoveryOutcome/assay_scored` / `C:review-discovery-outcome` | Locally complete; request producer default-denied by R3-M3 |
| OR-007 | `ReviewDiscoveryOutcome/assay_partial` / `C:review-discovery-outcome` | R3-M3: Candidate projection omitted; request producer denied |
| OR-008 | `CancelDiscoveryEvaluation/assay` / `C:cancel-discovery-evaluation` | R3-M4: output has no cancellation-review producer |
| OR-009 | `ProposeRevisitDecision/assay` / `C:propose-revisit-decision` | R3-M4: reviewed-cancellation precondition is unreachable |
| OR-010 | `ResolveDecision/discovery_revisit_assay` / `C:resolve-decision` | PASS once predecessor exists |
| OR-011 | `RequestAssay/retry` / `C:request-assay` | PASS once predecessor exists |
| OR-012 | `ProposePromotionDecision/assay_to_spike` / `C:propose-promotion-decision` | PASS once review exists |
| OR-013 | `ResolveDecision/discovery_promotion_assay` / `C:resolve-decision` | PASS once proposal exists |
| OR-014 | `RegisterSpikePlan/initial` / `C:register-spike-plan` | PASS |
| OR-015 | `ProposeSpikeExecutionDecision` / `C:propose-spike-execution-decision` | Locally complete; cancellation cleanup absent in R3-M5 |
| OR-016 | `ResolveDecision/spike_execution_authority` / `C:resolve-decision` | PASS absent cancellation race |
| OR-017 | `StartSpike` / `C:start-spike` | PASS |
| OR-018 | `RecordSpikeVerdict/complete` / `C:record-spike-verdict` | PASS for W11 verdict relation |
| OR-019 | `RecordSpikeVerdict/partial` / `C:record-spike-verdict` | R3-M5: attempt/lease closure omitted |
| OR-020 | `ReviewDiscoveryOutcome/spike_verdict` / `C:review-discovery-outcome` | Locally complete; request producer denied by R3-M3 |
| OR-021 | `ReviewDiscoveryOutcome/spike_partial` / `C:review-discovery-outcome` | Locally complete; request producer denied by R3-M3 |
| OR-022 | `CancelDiscoveryEvaluation/spike` / `C:cancel-discovery-evaluation` | R3-M4/M5: no cancelled review; pending Decision not retired |
| OR-023 | `ProposeRevisitDecision/spike` / `C:propose-revisit-decision` | R3-M4/M5: reviewed/no-unresolved guards can be unreachable |
| OR-024 | `ResolveDecision/discovery_revisit_spike` / `C:resolve-decision` | PASS once predecessor exists |
| OR-025 | `RegisterSpikePlan/retry` / `C:register-spike-plan` | PASS once predecessor exists |
| OR-026 | `ProposePromotionDecision/spike_to_preregistration` / `C:propose-promotion-decision` | PASS once review exists |
| OR-027 | `ResolveDecision/discovery_promotion_spike` / `C:resolve-decision` | PASS once proposal exists |
| OR-028 | `AdmitResearchDossier` / `C:admit-research-dossier` | PASS at specification level |
| OR-029 | `IngestScoutObservationBatch` / `C:ingest-scout-observation-batch` | PASS |
| OR-030 | `IngestDiscoveryAnnotation` / `C:ingest-discovery-annotation` | PASS; cutover currency separately R3-M6 |
| OR-031 | `RecordLegacyPortfolioObservation` / `C:record-legacy-portfolio-observation` | PASS |
| OR-032 | `TransitionPortfolioOwnership` / `C:transition-portfolio-ownership` | Blocked by R3-M1 mapping hash; tuple otherwise passes |
| OR-033 | `CutOverDiscoveryPath` / `C:cut-over-discovery-path` | R3-M6: annotation epoch/recheck omitted |
| OR-034 | `RequestDiscoveryOutcomeReview/assay_scored` / `C:request-discovery-outcome-review` | R3-M3: absent from Portfolio Steward allowlist |
| OR-035 | `RequestDiscoveryOutcomeReview/assay_partial` / `C:request-discovery-outcome-review` | R3-M3: absent from Portfolio Steward allowlist |
| OR-036 | `RequestDiscoveryOutcomeReview/spike_verdict` / `C:request-discovery-outcome-review` | R3-M3: absent from Portfolio Steward allowlist |
| OR-037 | `RequestDiscoveryOutcomeReview/spike_partial` / `C:request-discovery-outcome-review` | R3-M3: absent from Portfolio Steward allowlist |
| OR-101 | `RegisterAssayRubricContent` / `C:register-assay-rubric-content` | PASS |
| OR-102 | `RegisterAssayEvidenceScopeContent` / `C:register-assay-evidence-scope-content` | PASS |
| OR-103 | `ObserveW11AuthorityFile/assay_rubric` / `C:observe-w11-authority-file` | PASS |
| OR-104 | `ObserveW11AuthorityFile/assay_evidence_scope` / `C:observe-w11-authority-file` | PASS |
| OR-105 | `RequestW11AuthorityReview/assay_bar` / `C:request-w11-authority-review` | PASS |
| OR-106 | `RecordW11AuthorityReview/assay_bar` / `C:record-w11-authority-review` | PASS |
| OR-107 | `ProposeW11AuthorityDecision/assay_bar_acceptance` / `C:propose-w11-authority-decision` | PASS |
| OR-108 | `ResolveDecision/assay_bar_acceptance` / `C:resolve-decision` | PASS |
| OR-109 | `RecordAssayBarStaleness` / `C:record-assay-bar-staleness` | PASS |
| OR-110 | `RegisterDossierExpectedSetContent` / `C:register-dossier-expected-set-content` | PASS |
| OR-111 | `ObserveW11AuthorityFile/dossier_expected_set` / `C:observe-w11-authority-file` | PASS |
| OR-112 | `RequestW11AuthorityReview/dossier_expected_set` / `C:request-w11-authority-review` | PASS |
| OR-113 | `RecordW11AuthorityReview/dossier_expected_set` / `C:record-w11-authority-review` | PASS |
| OR-114 | `ProposeW11AuthorityDecision/dossier_expected_set_acceptance` / `C:propose-w11-authority-decision` | PASS |
| OR-115 | `ResolveDecision/dossier_expected_set_acceptance` / `C:resolve-decision` | PASS |
| OR-116 | `RegisterPathRegistrationContent` / `C:register-path-registration-content` | PASS |
| OR-117 | `ObserveW11AuthorityFile/path_registration` / `C:observe-w11-authority-file` | PASS |
| OR-118 | `RequestW11AuthorityReview/path_registration` / `C:request-w11-authority-review` | PASS |
| OR-119 | `RecordW11AuthorityReview/path_registration` / `C:record-w11-authority-review` | PASS |
| OR-120 | `ProposeW11AuthorityDecision/path_registration_acceptance` / `C:propose-w11-authority-decision` | PASS |
| OR-121 | `ResolveDecision/path_registration_acceptance` / `C:resolve-decision` | PASS |
| OR-122 | `RegisterLegacySourceInventoryContent` / `C:register-legacy-source-inventory-content` | PASS |
| OR-123 | `ObserveW11AuthorityFile/legacy_source_inventory` / `C:observe-w11-authority-file` | PASS |
| OR-124 | `RequestW11AuthorityReview/legacy_source_inventory` / `C:request-w11-authority-review` | PASS |
| OR-125 | `RecordW11AuthorityReview/legacy_source_inventory` / `C:record-w11-authority-review` | PASS |
| OR-126 | `ProposeW11AuthorityDecision/legacy_source_inventory_acceptance` / `C:propose-w11-authority-decision` | PASS |
| OR-127 | `ResolveDecision/legacy_source_inventory_acceptance` / `C:resolve-decision` | PASS |
| OR-128 | `RegisterLegacyTransitionMappingContent` / `C:register-legacy-transition-mapping-content` | R3-M1: relation-hash preimage cyclic |
| OR-129 | `ObserveW11AuthorityFile/legacy_transition_mapping` / `C:observe-w11-authority-file` | Blocked by R3-M1; tuple otherwise passes |
| OR-130 | `RequestW11AuthorityReview/legacy_transition_mapping` / `C:request-w11-authority-review` | Blocked by R3-M1; tuple otherwise passes |
| OR-131 | `RecordW11AuthorityReview/legacy_transition_mapping` / `C:record-w11-authority-review` | Blocked by R3-M1; tuple otherwise passes |
| OR-132 | `ProposeW11AuthorityDecision/migration_authority` / `C:propose-w11-authority-decision` | Blocked by R3-M1; tuple otherwise passes |
| OR-133 | `ResolveDecision/migration_authority` / `C:resolve-decision` | Blocked by R3-M1; tuple otherwise passes |
| OR-134 | `RegisterLegacyCutoverClosureContent` / `C:register-legacy-cutover-closure-content` | Blocked by R3-M1/M6; tuple otherwise passes |
| OR-135 | `ObserveW11AuthorityFile/legacy_cutover_closure` / `C:observe-w11-authority-file` | Blocked downstream; tuple otherwise passes |
| OR-136 | `RequestW11AuthorityReview/legacy_cutover_closure` / `C:request-w11-authority-review` | Blocked downstream; tuple otherwise passes |
| OR-137 | `RecordW11AuthorityReview/legacy_cutover_closure` / `C:record-w11-authority-review` | Blocked downstream; tuple otherwise passes |
| OR-138 | `ProposeW11AuthorityDecision/legacy_path_cutover` / `C:propose-w11-authority-decision` | Blocked downstream; tuple otherwise passes |
| OR-139 | `ResolveDecision/legacy_path_cutover` / `C:resolve-decision` | Blocked downstream; tuple otherwise passes |
| OR-140 | `RegisterW11SchemaCatalogueContent` / `C:register-w11-schema-catalogue-content` | R3-M1/M2: catalogue hash and bootstrap cycles |
| OR-141 | `ObserveW11AuthorityFile/w11_schema_catalogue` / `C:observe-w11-authority-file` | R3-M2: pre-acceptance producer prohibited |
| OR-142 | `RequestW11AuthorityReview/w11_schema_catalogue` / `C:request-w11-authority-review` | R3-M2: pre-acceptance producer prohibited |
| OR-143 | `RecordW11AuthorityReview/w11_schema_catalogue` / `C:record-w11-authority-review` | R3-M2: pre-acceptance producer prohibited |
| OR-144 | `ProposeW11AuthorityDecision/w11_schema_catalogue_acceptance` / `C:propose-w11-authority-decision` | R3-M2: pre-acceptance producer prohibited |
| OR-145 | `ResolveDecision/w11_schema_catalogue_acceptance` / `C:resolve-decision` | R3-M2: pre-acceptance producer prohibited |

The catalogue passed missing/extra/duplicate/receipt/positive/retry identity counts but
failed relational authority. Coordinated substitution must therefore mutate the
independently authored allowlist and effect/test relations as well as candidate/runtime
rows; row count and separately correct field sets are insufficient.

## 9. Design-entry-criteria audit

| README criterion | R3 disposition | Evidence / blocker |
|---|---|---|
| 1. Governing decisions accepted or assumptions explicit | Pass for authorship | P-004/P-005/P-021/P-022/P-026/P-032/P-034/P-036, W11-A1 and both D-G6-4 limbs are explicit. |
| 2. Evidence inputs in root register | Pass | One tracked section 8 addendum gives paths/hashes/authority class/limitations. Current backlog drift is correctly non-authoritative. |
| 3. Boundaries and consumers identified | Pass | W1/W2/W4/W5/W9/W10/Vault/external consumers and no-compensation rules are explicit. |
| 4. Independent review owner | Pass for assignment/outcome evidence | R3 is a fresh distinct context on the exact commit; this verdict does not accept it. |
| 5. Acceptance tests stated before implementation | **Fail** | R3-M1–M5 make positive authority/catalogue/recovery fixtures unconstructible or unreachable; R3-M6 leaves cutover currency untestable without a new epoch rule. |

## 10. Decision and gate audit

| Decision/gate | R3 disposition |
|---|---|
| P-004 / P-021 | **Keep; rework W11.** Exclusive ownership/path separation and Windows controls are correct. Mapping construction and late-annotation cutover currency block proof. |
| P-005 / P-022 | **Keep.** Human promotion and independent review remain non-compensable. Missing/denied review routes must be repaired rather than bypassed. |
| P-026 | **Keep.** The subject is specification-only and created no runtime/schema/vault/migration state. |
| P-032 | **Keep direction; rework exact W11 revision.** Canonical portfolio/Discovery integration remains appropriate; six Majors block acceptance. |
| P-034 | **Keep direction; rework mapping/cutover closure.** No dual-running/implicit import was authorized; exact relation preimage and annotation epoch remain open. |
| P-036 | **Keep and do not broaden.** It approves exact WP6 plan revision `fe5f1d4...`, not W11, future schemas/runtime, admission or migration. |
| D-G6-4 limb 1 | **Remain open.** Do not present `3e068c1...` for acceptance until all six Majors are repaired and a fresh exact-commit review has no open Critical/Major. |
| D-G6-4 limb 2 | **Remain open and hard-stopped.** No first batch can use an unconstructible mapping relation or incomplete cutover epoch. |
| W11-A1 | **Defer / default omit.** A combined view is unnecessary to repair the blocking authority and lifecycle defects. |

No accepted decision is reversed. R3-M2 and R3-M6 require new bounded owner choices;
the other repairs can preserve existing authority while making it executable.

## 11. Complete invariant -> enforcement -> test disposition

| Invariant | R3 disposition | Reason |
|---|---|---|
| W11-I01 | Pass at design level | Object definitions remain immutable and state-free. |
| W11-I02 | **Fail** | R3-M1 leaves stored relation/catalogue/Assay digests cyclic or undefined. |
| W11-I03 | Pass at design level | Required dependency/block graph acyclicity is explicit. |
| W11-I04 | **Fail** | Assay bar passes, but review requests are denied and cancelled outcomes have no review producer (R3-M3/M4). |
| W11-I05 | Pass at design level | Evidence cannot resolve promotion without Stephen. |
| W11-I06 | **Fail** | Cancel review, attempt/lease closure and pending-Decision cleanup are incomplete (R3-M4/M5). |
| W11-I07 | Partial | Exact human/subject/gate authority passes; required review predecessors can be unreachable (R3-M3/M4). |
| W11-I08 | Pass at design level | PROMOTE cannot add Dispatch/pre-registration/result/claim effects. |
| W11-I09 | Pass at design level | Dossier expected content/file/review/acceptance is acyclic and pre-observation. |
| W11-I10 | Pass at design level | Exact six-family closure and independent component/source reads are complete. |
| W11-I11 | Pass at design level | Atomic staging/write-set/tail/version/zero-publication rules remain explicit. |
| W11-I12 | **Fail** | Catalogue bootstrap and row/allowlist/projection/test joins are incomplete (R3-M2/M3). |
| W11-I13 | Pass at design level | Generated/combined views remain denied as authority inputs. |
| W11-I14 | Pass at design level | Registration-through-commit Windows physical identity protocol is complete prospectively. |
| W11-I15 | Pass at design level | Annotation remains evidence pending a separate authorized command. |
| W11-I16 | **Fail** | Member relation is exact but its mapping relation hash is unconstructible (R3-M1). |
| W11-I17 | Pass at design level | Per-item transition writes no legacy path. |
| W11-I18 | **Fail** | Mapping hash and late-annotation currency block exact cutover closure (R3-M1/M6). |
| W11-I19 | Pass at design level | Reverse cutover remains invalid. |
| W11-I20 | Pass at design level | Deterministic rebuild and operation-time publication controls remain authority-neutral. |
| W11-I21 | Pass at design level | Paper Claim governance is Required; W5 authority cannot be compensated. |
| W11-I22 | Partial | Unknown/broken records fail closed, but catalogue acceptance has no authorized bootstrap producer (R3-M2). |

## 12. Complete pre-implementation acceptance-test disposition

| Test family | R3 disposition | Reason |
|---:|---|---|
| 1 | **Blocked** | Hash SCCs, bootstrap cycle and row joins prevent a constructible complete positive universe (R3-M1–M3). |
| 2 | Pass as required pattern | One-field type/value/enum/pattern/required/additional-property mutations remain appropriate. |
| 3 | **Blocked** | Catalogue content hash/bootstrap and literal negative identities are incomplete (R3-M1–M3). |
| 4 | **Blocked** | Allowlist denial, missing cancellation review and unresolved overlays prevent a closed matrix (R3-M3–M5). |
| 5 | Partial | Exact foreign-valid member relations are strong; Assay/mapping digest and recovery predecessors remain blocked. |
| 6 | Pass at design level | Legacy numeric rule and recommendation-only `decision` mapping are preserved. |
| 7 | **Blocked** | Partial/cancel review and attempt/Decision closure are incomplete (R3-M3–M5). |
| 8 | Pass at design level | Option-specific and non-Stephen negatives are exact. |
| 9 | Pass at design level | Dossier positive DAG, six-family/source mutations and fixed external tuple are constructible. |
| 10 | Pass at design level | Failure injection maps to W2 zero publication. |
| 11 | **Blocked** | All-row retry identities exist, but bootstrap, allowlist, negative IDs and lifecycle cleanup do not (R3-M2–M5). |
| 12 | Pass at design level | Scout source/dedup/collision/judgment/write negatives are complete. |
| 13 | Partial | Annotation ingestion tests pass prospectively; after-closure/pre-cutover annotation race is missing (R3-M6). |
| 14 | Pass at design level | Junction positive and alias/reparse/hardlink/parent/concurrent phase attacks are explicit; future unavailable coverage is Partial. |
| 15 | **Blocked** | Mapping member equality is exact but relation digest cannot be materialized (R3-M1). |
| 16 | Partial | Disjoint paths/no `dual_owned`/row-hash reconciliation pass; accepted mapping relation is blocked by R3-M1. |
| 17 | Pass at design level | Projection deletion/rebuild/version behavior is explicit. |
| 18 | **Blocked** | Mapping digest and late-annotation epoch prevent a complete positive cutover fixture (R3-M1/M6). |
| 19 | Pass at design level | Genesis/snapshot/unknown-major replay behavior follows W2. |
| 20 | Pass at design level | Paper Claim consumer non-compensation is explicit and performs no live claim action. |

## 13. Cross-spec consistency matrix

| Invariant / identity | Owning source | W11 claim | R3 result |
|---|---|---|---|
| Immutable record / canonical stream | W2 §§5–9 | `obj_`, `asy_`, `spk_`, exact references | Aggregate IDs pass; kind-specific digest preimages fail (R3-M1). |
| Decision != RuleEvaluation | W2 §18; P-005/P-022 | Score/verdict evidence cannot resolve promotion | Pass. |
| Bar independent/frozen before observation | W5 §§6–11 | Concrete Assay bar and dossier tuple | Pass for both authority orderings; later Assay relation digest remains R3-M1. |
| Complete expected-set / producer separation | W5 §11; WP6 master §6 | Dossier six-family and W11 82-row expected sources | Dossier passes; catalogue bootstrap/joins fail (R3-M2/M3). |
| Accepted schema bytes -> accepted catalogue -> runtime | P-036; WP6.1 plan lines 157–173 | OR-140–OR-145 typed acceptance before runtime | Fail: W11 requires the prohibited runtime to create its prerequisite instead of using the approved external Git-manifest acceptance pattern (R3-M2). |
| Atomic publication | W2 §§8–9/13 | Dossier/promotion/transition/retry batches | Dossier and retry supersession pass; Spike resource/Decision cleanup fails (R3-M5). |
| Review lifecycle | W2 §17; P-022 | Distinct request/verdict and subject-specific review | Partial remains Partial, but requests are denied and cancelled subjects absent (R3-M3/M4). |
| Observation != adoption | W2 §22; P-032/P-034 | Source inventory -> mapping -> transition | Semantic split passes; mapping digest fails (R3-M1). |
| One owner / no shared physical writer | W1 §§9–10; P-004/P-021 | Disjoint paths plus §7.3 | Physical protocol passes; annotation epoch is stale at cutover (R3-M6). |
| Profile capability != authority | W4 §§7/15/19 | Exact row profile/subject/grant and default deny | Fail: OR-034–037 contradict the complete allowlist (R3-M3). |
| Portfolio Claim != W5 claim authority | W1 §5.1; W5 §§14/19 | Required Paper Claim governance | Pass. |
| Specification != implementation/migration | P-026/P-036; WP6 master | Hard stops and `review_pending` | Pass; no implementation/live action occurred. |

## 14. Research-assurance lane disposition

| Lane | R3 disposition |
|---|---|
| Output / Provenance | **Required — primary; blocked.** Exact revision/report provenance, dossier/source rehashing, Windows identities, no-overwrite intent and consumer restrictions pass. R3-M1–M3/M6 prevent reproducible accepted catalogue/mapping/cutover authority. |
| Topology | **N/A — keep.** No filtration, PH object, homology or metric judgment is defined; later domain packs remain mandatory. |
| Stochastic / Null Model | **N/A — keep.** No null operation, RNG, p-value or exchangeability claim is decided. |
| Statistical / Panel | **N/A — keep.** No estimand, eligibility, weighting, imputation, variance or multiplicity rule is defined. |
| Representation | **N/A — keep.** References are carried without fitting or judging PCA/UMAP/scalers/labels/windows. |
| Paper Claim | **Required — governance/consumer boundary; pass.** Portfolio records, views, Assay and Spike evidence cannot satisfy W5 result/claim authority; no claim was created, reviewed, accepted or promoted. |

The prospective provenance check therefore passes immutable report trace, exact subject
identity, source-file rehashing, path separation, no-overwrite intent and Paper Claim
routing, but fails constructible relation/catalogue hashes, bootstrap authority,
owner-surface joins and cutover currency. Result-file date suffix, seeds, B/L, cache and
result-vault items remain genuinely not applicable.

## 15. Failure behavior, practicality, residual risk, and revision plan

### 15.1 Failure and proportionality

The ordinary specified failures remain fail-closed: invalid authority changes no
state; dossier rejection publishes nothing; views are non-authoritative; missing Spike
evidence is Partial; promotion remains human-locked; unknown major records stop replay;
Windows identity uncertainty is Partial; and reverse cutover is invalid.

The six findings require four additional explicit failure classes:

- `derived_hash_preimage_cyclic` for a self-edge/SCC in any kind-specific digest;
- `bootstrap_authority_unavailable` when catalogue acceptance has no pre-authorized
  producer;
- `recovery_overlay_open` when cancel/Partial leaves a review/Decision/attempt/lease;
  and
- `cutover_epoch_stale` when annotation or other closure inputs change after acceptance.

The smallest proportionate repair is localized. Dossier admission needs no new
control. Assay-bar contents need only an exact relation-hash preimage. Normal/Partial/
cancellation paths need missing allowlist/review/resource rows, not a new lifecycle.
Per-item transition needs one non-cyclic relation digest. Catalogue materialization
needs one explicit bootstrap medium. Whole-path cutover alone needs the annotation
epoch/fence.

### 15.2 Required revision plan

Immediate specification corrections:

1. eliminate every derived-hash self-edge/SCC and list exact preimage fields/exclusions;
2. choose and define an authorized pre-runtime catalogue-acceptance bootstrap;
3. reconcile all 82 rows with W4 allowlists, projection effects and literal negative
   test identities;
4. add cancelled-outcome review request/verdict rows;
5. close Spike Partial attempts/leases and cancel-time pending Decisions atomically;
6. define and test the annotation/cutover epoch; and
7. redisposition all affected matrices without narrowing the preserved R1/R2 controls.

Owner decisions:

- select the catalogue bootstrap authority (R3-M2);
- select the late-annotation cutover epoch policy (R3-M6);
- do not present `3e068c1...` for D-G6-4 limb 1 acceptance; and
- keep D-G6-4 limb 2 and W11-A1 open/default-omit.

Later-work dependencies:

- schema/catalogue materialization remains downstream of accepted W11 and the chosen
  bootstrap;
- WP6.6 remains downstream of accepted W11/WP6.1 and a constructible catalogue; and
- WP6.7/W9 remain downstream of accepted mapping/cutover contracts and a separate
  exact first-batch decision.

### 15.3 Residual risks after repair

- expected/runtime code may still share an enumerator; retain coordinated two-sided
  mutation against an independently authored expected source;
- complete row identities can still hide wrong relations; retain allowlist, stored-
  relation and reducer/projection joins;
- filesystem feature/privilege variance must remain recorded as Partial where required
  races cannot execute;
- every mutable legacy/annotation source requires a fresh accepted observation/epoch;
- W9/W10 may not narrow W11 or introduce TDL paths into reusable core; and
- conformance never establishes scientific adequacy of a future rubric, Spike, result
  or claim.

## 16. Validation evidence

### 16.1 Mandatory framework gates

All runner outputs were routed outside the repository to
`C:\Users\steph\AppData\Local\Temp\w11-r3-gates-d2970786ce1e47ca8de0b23ba719f4fb`.
`PYTHONDONTWRITEBYTECODE=1`, external `PYTHONPYCACHEPREFIX`/`COVERAGE_FILE`, and
`PYTEST_ADDOPTS=-p no:cacheprovider --no-cov` were set. Ignored runner-artifact
inventory was zero before and after; delta zero; Git remained clean.

| Command | Exit | Exact result |
|---|---:|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` | 0 | `Contract framework: all gates passed against 101 contract(s).` |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | 0 | `Contract framework: all gates passed against 101 contract(s).` |

These gates validate the existing repository framework, not prospective W11
constructibility.

### 16.2 Independent structural/provenance oracles

| Check | Result |
|---|---|
| Changed surface from base | 6 Markdown files only; no schema/runtime/vault/state file |
| Markdown tables | 45 tables; 483 data rows; 0 column-count defects |
| Relative links | 15 checked; 0 broken |
| Code fences | balanced in all changed files; W11 has 22 fence lines |
| Truncation/conflict markers | 0 |
| Cardinalities | 5 entry criteria; 82/82 unique owner rows; 22/22 invariants; 20/20 test families |
| Owner rows | 82 unique receipts; 34 command schemas; 82 positive + 82 retry IDs; 0 literal per-row negative IDs |
| Hash-dependency oracle | 19 nodes/19 edges; 3 cyclic components listed in §7.1 |
| Live package rehash | 20/20 linked source/component hashes match |
| R1/R2 immutability | R1 `8af8add...` and R2 `3d15046...` identical across original/cherry-pick/target |
| `git diff --check 4e6fd0c... 3e068c1...` | exit 0 |

The first attempted wrapper that combined gates with recursive temp cleanup was
rejected by the command-safety layer before execution; it created no file and produced
no gate result. It was not counted. The successful wrapper above left only its external
audit directory.

### 16.3 Specification-only boundary and hard stops

This review did **not** edit W11, README, decision register, evidence register, either
prior report or any subject byte. It did not materialize a schema/catalogue, create
`.research-system/` state, write a vault path, ingest Scout/annotation evidence, admit
the TDA-scale package, allocate an idempotency outcome, transition ownership, cut over
a path, begin WP6.6/WP6.7, run a live provider/model call, perform research/compute,
change result/eligibility/claim state, exercise Gate 5, approve Gate 6, merge, or alter
PR #121. The only repository change is this R3 report.

## 17. Change log, provenance, and final recommendation

### 17.1 Files changed

- `docs/plans/agentic-research-system/reviews/adversarial-wp6-5-w11-spec-remediation-r3-review-2026-07-18.md`
  — this R3 report only.

Subject specification/index/decision/evidence files and immutable R1/R2 report bytes
changed: **none**. Task-observer observations 64 and 65 were appended to the canonical
external skill-observation log; they are not repository subject/report state.

### 17.2 Report provenance

The reviewed W11 subject is commit
`3e068c1ee5100e5a6e0bc57d0d047d993b406b2b`, Git blob
`1e3deac4935b7e656985658b92c70e4a3e0da46a`, and canonical Git-blob SHA-256
`c186b2381513ccdc1011a8068e7b35e15e4a128702e8179163b68837b787fa5f`
(158,742 bytes). The R2 evidence blob is
`3d15046c937672f3a7a1519f65e739a586374248`.

This report's own commit/blob/file SHA-256 are necessarily post-serialization external
provenance: embedding any of them in the bytes they identify would recreate the exact
self-addressing defect rejected by R3-M1. They are computed after hooks/commit/push and
returned in the task handoff alongside this report path.

### 17.3 Final disposition

**Verdict:** `rework_required`
**Exact reviewed commit:** `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b`
**Evidence status:** `Complete`
**Open findings:** `0 Critical / 6 Major / 0 Minor`

**D-G6-4 recommendation:** do not accept limb 1 for this revision; keep limb 2 open and
do not author/approve a first transition batch.
**Merge recommendation:** keep PR #121 draft and **do not merge**.
**Next required gate:** repair R3-M1–R3-M6 without changing the immutable R1/R2 reports,
then obtain a fresh distinct-authority exact-commit adversarial review. No schema/
runtime/migration/claim action may begin in lieu of that gate.
