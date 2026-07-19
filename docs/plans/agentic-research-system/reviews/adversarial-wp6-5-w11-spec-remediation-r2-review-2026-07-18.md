# Adversarial WP6.5 W11 remediation R2 review

**Review date:** 2026-07-18
**Reviewer posture:** fresh, distinct-authority, adversarial remediation re-review
**Target repository:** `TDL`
**Assigned review branch:** `review/ars-wp6-5-w11-spec-r2`
**Exact reviewed commit:** `d24df9d26f0d906d177eafa1eaeabb65a5515004`
**Exact reviewed parent:** `7db8b05e99bd24bccf94ffd1b4627c199e1fcd1b`
**Original reviewed subject:** `70074d42eade8460808e4d1d29348b7806eff2d0`
**Subject branch / remote head observed:** `pipe/ars-wp6-5-w11-spec` / `d24df9d26f0d906d177eafa1eaeabb65a5515004`
**Immutable R1 report blob:** `8af8add2bd1853b4aaf6b0178279013256dfb044`
**Review evidence status:** `Complete`
**Verdict:** `rework_required`
**Finding count:** **0 Critical, 5 Major, 0 Minor**

## 1. Executive verdict

Commit `d24df9d26f0d906d177eafa1eaeabb65a5515004` is **not safe to accept as
the W11 specification revision**. The remediation materially improves the original
draft. It defines canonical `asy_` and `spk_` aggregate identities, freezes a rubric at
Assay request time, independently re-resolves dossier source bytes, names the formerly
omitted admission/ingestion/transition/cutover commands, adds an operation-time Windows
handle/file-identity protocol, marks Paper Claim as a governance lane, and adds the
dated root evidence-register entry. Those mechanisms should be preserved.

The strongest re-tests nevertheless expose five blocking design defects:

1. `DossierExpectedSet` requires its own final repository blob/file digest inside the
   authority record without defining a separate post-serialization acceptance envelope.
   The record therefore has no unambiguous acyclic materialization procedure.
2. `LegacyPortfolioInventory` and `LegacyTransitionMapping` content-address each other:
   an inventory item row contains the expected mapping hash while the mapping contains
   the accepted inventory and item-row hashes. The same inventory also mixes
   source-reproducible membership with successor-derived ownership/mapping state.
3. `RequestAssay` names an accepted `AssayEvidenceScope`, but W11 defines neither that
   authority's fields nor the command/event/review lifecycle that accepts the rubric and
   scope relative to the prospective producer.
4. The supposedly complete interface catalogue still leaves exact reducer/projection
   relations, proposal/review/acceptance commands, and several bar-defining authority
   transitions to the future materializer. The future expected catalogue can therefore
   invent owner semantics it is meant only to serialize.
5. Assay/Spike cancellation and Partial/review paths are not executable as one closed
   state machine. Cancellation leaves the Candidate at a gate from which no replacement
   aggregate can be requested, and `RecordAssayReview` accepts a Partial even though the
   Assay state machine has no `partial -> reviewed` edge.

These are Majors rather than Criticals because the literal text most naturally fails
closed or becomes unimplementable; it does not currently provide a conforming path that
demonstrably accepts corrupt authority. They are still acceptance-blocking under W11
section 14 and D-G6-4: implementing around any of them would require hidden design or
authority decisions.

**Required disposition:** revise W11, preserve the mechanisms that passed, reconcile all
five Majors, and obtain a fresh exact-commit adversarial review. D-G6-4 limbs 1 and 2,
WP6.6, WP6.7, strict schema/catalogue materialization, admission, ingestion, ownership
transition, whole-path cutover, and every result/eligibility/claim action remain open or
hard-stopped.

## 2. Review identity, scope, and direct evidence

### 2.1 Hard revision precondition and currency

The authorized worktree initially had detached `HEAD`. Before attachment, detached
`HEAD` and `refs/heads/review/ars-wp6-5-w11-spec-r2` both resolved to exact commit
`d24df9d26f0d906d177eafa1eaeabb65a5515004`, and the worktree was clean. The single
permitted deterministic attachment, `git switch review/ars-wp6-5-w11-spec-r2`,
succeeded. The symbolic branch, exact `HEAD`, cwd, and clean status were rechecked before
the report write.

`git ls-remote` independently returned the subject remote head at the same exact commit.
The R1 report blob is identical at original review commit
`21ebc46b0c415286e8c525106e8bb9fde92d38c3`, remediation-lineage cherry-pick
`7db8b05e99bd24bccf94ffd1b4627c199e1fcd1b`, and reviewed target `d24df9d...`.
No later subject commit or changed R1 bytes were credited.

### 2.2 Complete committed review surface

The review read the complete 1,355-line W11 revision, the complete 688-line immutable R1
report, and every hunk of the 1,083-line W11 remediation patch. It also read the full
companion diffs from `70074d4...` to `d24df9d...`:

- `docs/plans/agentic-research-system/01-current-system-evidence.md`;
- `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`;
- `docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md`;
- `docs/plans/agentic-research-system/design/README.md`; and
- the added immutable R1 report.

Direct owner checks covered the governing WP6.5/D-G6-4 master sections; P-004, P-005,
P-021, P-022, P-026, P-032, P-034, and P-036; W1 portfolio/projection/ownership/path
boundaries; W2 record, identifier, command, transaction, review, Decision, legacy and
replay contracts; W4 profile/grant/default-deny/human-authority rules; W5 requirement
scope, contract activation, provenance, claim and two-key rules; W9/W10 owner bounds;
the two committed Discovery Harness contracts; and the R5 launch-basis review. Earlier
reviews were finding catalogues and provenance evidence, not inherited proof.

### 2.3 Live evidence fidelity and root evidence register

All named live evidence was accessible read-only, so this report is not `Partial`.

| Evidence | Independent observation on 2026-07-18 | Result |
|---|---|---|
| Living Discovery backlog | 26,392 bytes; SHA-256 `37eec1ba6bb7929d95d5349ada2f75d93636c8356aad5dffc6a59981fc0269e7` | Exact match to root register section 8 |
| TDA-scale v1.0.0 package manifest | 5,843 bytes; SHA-256 `e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf` | Exact match |
| TDA-scale master component | 28,244 bytes; SHA-256 `277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea` | Exact match |
| Manifest-linked sources/components | 20 resolved files; 20 SHA-256 matches; 0 missing/mismatched | Exact match; observation only, not admission |
| Registered vault root | `Directory, ReparsePoint`; `Junction` to `C:\Users\steph\Documents\TDA-Research` | Exact match; validates registered-root positive fixture need |
| Proposed ARS Discovery paths | All three absent | Exact match; no namespace was created |

The evidence addendum correctly labels these as dated mutable observations and forbids
their use as an expected oracle, migration inventory, result, eligibility or claim
authority. Relative-link validation across all five changed Markdown files found zero
broken repository-relative links.

### 2.4 External contract gates

Both required gates ran from exact reviewed commit `d24df9d...` with
`PYTHONDONTWRITEBYTECODE=1`, pytest cache/coverage disabled or externally routed, and an
explicit ignored-runner-artifact inventory before and after.

| Command | Exit | Exact outcome |
|---|---:|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` | 0 | `Contract framework: all gates passed against 101 contract(s).` |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | 0 | `Contract framework: all gates passed against 101 contract(s).` |

Runner-artifact count remained zero and Git status remained clean. These gates validate
the current repository contract framework; they do not prove the prospective W11
interfaces are constructible or complete.

## 3. Findings summary

| ID | Severity | Finding | Blocks |
|---|---|---|---|
| R2-M1 | Major | `DossierExpectedSet` has no acyclic self-content-addressing/acceptance materialization | Prior C-1; I09-I11; tests 3/9-11; WP6.6 |
| R2-M2 | Major | Inventory and transition mapping have a content-hash and lifecycle cycle | Prior C-2/M-5; I02/I16-I18; tests 5/15/16/18; D-G6-4 limb 2 |
| R2-M3 | Major | The request-time Assay bar has no defined accepted scope authority or producer-relative acceptance lifecycle | Prior M-2; I04/I05; tests 4-6 |
| R2-M4 | Major | The complete catalogue still omits exact prerequisite authority/review/proposal and reducer/projection relations | Prior M-4; I12/I15-I18; tests 1/3/11-13/18 |
| R2-M5 | Major | Cancellation, Partial review, resume and supersession paths are internally non-executable | Prior M-1/M-4; I02/I04-I07; tests 4/5/7/11 |

## 4. Major findings

### R2-M1 — `DossierExpectedSet` has no acyclic materialization

1. **Claim.** The remediation defines complete literal dossier rows, but it places the
   final repository path/Git blob/file length/file SHA-256 inside the
   `DossierExpectedSet` authority record without defining a distinct post-serialization
   acceptance envelope. Read literally, the file must contain the digest of bytes that
   include that digest.
2. **Evidence.** W11 defines one closed immutable expected-set record at
   `design/11-portfolio-and-discovery-lifecycle.md:490-515`. The record contains exact
   repository path, Git commit/blob, byte length and SHA-256 of the serialized expected
   set at `:501-503`, while the common object envelope hashes the record's canonical
   fields excluding only `content_hash` at `:163-181`. The command and handler require
   the same blob/file digest at `:613-646`. W2 makes object files immutable and inert
   until an accepted event references them at
   `design/02-task-event-and-artifact-schema.md:193-217`.
3. **Concrete failure scenario.** The expected-set author serializes the complete rows
   with placeholder blob/SHA fields, computes the repository blob and SHA-256, then
   inserts those values. Inserting them changes the bytes and both digests. Repeating
   does not yield a specified fixed point. A materializer must either omit the required
   fields, exclude undeclared fields from the serialized preimage, or invent a second
   wrapper/event that W11 does not define.
4. **Impact.** No conforming positive dossier fixture or accepted expected authority can
   be constructed from the literal contract. WP6.6 would have to make an unreviewed
   schema/identity decision at the exact boundary intended to prevent correlated
   expected-side substitution.
5. **Required disposition.** **Fix now; fresh re-review required.** The complete six-row
   oracle is valuable and should remain, but its content identity and its acceptance
   provenance need an acyclic creation order.
6. **Exact proposed interface change.** Define (a) a canonical
   `DossierExpectedSetContent` whose hash preimage contains the six literal families and
   scope but no own file/blob digest, and (b) a later
   `DossierExpectedSetAcceptance` Decision/event or manifest that, after the content file
   exists, binds its object ID/revision/content hash, repository path, Git commit/blob,
   file length/SHA-256, reviewer evidence and acceptance. State every excluded field and
   require `AdmitResearchDossier` to resolve both exact records. Alternatively name an
   equally explicit two-object construction; do not leave the split to implementation.
7. **Affected decisions/work packages.** P-032; D-G6-4 limb 1; WP6.5/WP6.6; prior C-1;
   W11-I09-I11; tests 3 and 9-11.

### R2-M2 — Inventory and transition mapping form a content-address/lifecycle cycle

1. **Claim.** The repaired transition relation and whole-path inventory cannot be
   topologically created. Each `LegacyPortfolioInventory.items[]` row contains the
   expected mapping identity/hash, while each `LegacyTransitionMapping` contains the
   accepted inventory ID/revision/hash and inventory item-row hash.
2. **Evidence.** Inventory item rows include `expected mapping identity/hash or explicit
   unresolved reason` at W11 `:893-912`. A mapping row binds an accepted inventory
   ID/revision/hash and exact item-row hash at `:846-854`; transition refuses to allocate
   state until it loads and recomputes that relation at `:855-868`. The common object
   contract includes all record fields in canonical content except `content_hash`
   (`:163-181`). Whole-path cutover then requires every literal final-inventory row to
   bind exactly one accepted mapping/event at `:924-953`.
3. **Concrete failure scenario.** To compute inventory hash `I`, the producer must first
   know mapping hash `M` stored in the item row. To compute `M`, the producer must first
   know accepted `I` and that row's hash. If an initial inventory uses `unresolved`, the
   later mapping can reference it, but revising the final inventory to insert `M`
   changes both `I` and the item-row hash; `M` is now bound to the stale revision. The
   final cutover cannot satisfy the claimed same-row relation without relaxing an exact
   equality.
4. **Impact.** The first per-item transition and the final cutover cannot both conform.
   An implementation that weakens one side can attach a valid mapping/event to the wrong
   inventory revision or item row, reopening the valid-foreign substitution that prior
   M-5 sought to close.
5. **Required disposition.** **Fix now; fresh re-review required.** This is a lifecycle
   feasibility defect, not a reason to remove exact relations.
6. **Exact proposed interface change.** Split the records into an acyclic chain:
   `LegacySourceInventory` (source bytes, complete literal membership, aliases,
   selectors, parser/reproducer and byte coverage only) -> accepted
   `LegacyTransitionMapping` per immutable source row -> transition event ->
   `LegacyCutoverClosure` that binds the accepted source inventory plus the complete
   mapping/event/revocation/final-observation bijection. A mapping may reference the
   source inventory; the source inventory must never reference a mapping. The final
   closure may reference both. Keep ownership and transition-derived fields out of the
   source parser's reproducible row multiset.
7. **Affected decisions/work packages.** P-004/P-021/P-032/P-034; D-G6-4 limbs 1 and 2;
   WP6.5/WP6.7/W9; prior C-2 and M-5; W11-I02/I16-I18; tests 5, 15, 16 and 18.

### R2-M3 — The request-time Assay bar is named but not accepted through a closed authority

1. **Claim.** `RequestAssay` freezes rubric/scope hashes before evidence collection, but
   W11 never defines the `AssayEvidenceScope` fields, its producer-relative independence
   evidence, or the commands/events that make either the rubric or scope accepted.
   The phrase “already accepted” therefore has no W11 owner contract.
2. **Evidence.** `AssayEvidenceScope` appears substantively only at W11 `:376-386` and
   `:388-411`, and as a future schema name at `:993-1004`. Section 4.2 has no
   rubric/scope proposal, review or acceptance row; `RequestAssay` merely tests an
   unspecified accepted state at `:330-356`. The stored relation records
   author/reviewer/acceptor identities but not the prospective producer relationship or
   established independence grade. W5 requires accepted requirement/bar records to bind
   author, scope reviewer, accepting authority, prospective producer and evidence-derived
   relationship/grade, and to stale when that relationship changes
   (`design/05-research-assurance-and-independent-review.md:161-205`, `:291-320`).
3. **Concrete failure scenario.** A future schema materializer creates a minimal
   `AssayEvidenceScope` containing only an ID/hash and treats a generic object-registration
   event as acceptance. The scorecard producer changes after request to the scope author
   or a producer-correlated context. All frozen IDs/hashes still compare equal, yet the
   acceptance bar was never independently confirmed relative to the actual producer and
   no specified stale transition fires.
4. **Impact.** The remediation prevents a late hash swap but not hidden self-definition
   or producer-correlation of the bar. Test 4 can prove identity freeze while missing the
   W5 foundation property that the frozen object is a valid accepted scope.
5. **Required disposition.** **Fix now.** Preserve request-time freezing and add the
   missing authority lifecycle before W11 acceptance.
6. **Exact proposed interface change.** Define closed `AssayRubric` and
   `AssayEvidenceScope` authorities with complete lane/input/evidence-boundary fields,
   author, requirement-scope reviewer, acceptor, prospective producer actor/profile,
   relationship evidence/grade, acceptance/staleness events, and effective scope/time.
   Add literal proposal/review/acceptance command rows. `RequestAssay` must reference the
   accepted revisions/events and producer relationship; an actual-producer change that
   invalidates the grade stales the request before collection.
7. **Affected decisions/work packages.** P-022/P-032; WP6.5/WP6.6; prior M-2;
   W11-I04/I05; tests 4-6.

### R2-M4 — The “complete” catalogue still leaves owner relations to materialization

1. **Claim.** Sections 4.2 and 8 enumerate many more names, but they do not contain the
   promised complete literal one-to-one command/event/reducer/projection/receipt/authority
   records. Required supporting W11 subjects are absent, and per-row reducer/projection
   relations are deferred to `W11SchemaExpectedCatalogue`.
2. **Evidence.** The section 4.2 table at W11 `:314-366` gives profile/subject,
   preconditions and events/write set, but no literal command/event schema hashes,
   reducer identities, projection targets or distinct test IDs. Section 8 lists class
   names and later says each future row will contain those missing fields at `:978-1071`.
   It also says catalogue acceptance must predate runtime-registry/schema production,
   although the rows require schema hashes not fixed by W11. Concrete prerequisite gaps
   include: no proposal command/event for the dossier/inventory/mapping/cutover
   `ResolveDecision` discriminants; no review-request/satisfaction path for
   `RecordAssayReview`; no Spike-review row even though `PromotionDecision` requires
   validation/review refs at `:458-478`; and no initial `PathRegistration` command/event.
   W2 keeps proposal, review verdict, Decision resolution, object revision and accepted
   event authority distinct (`design/02-task-event-and-artifact-schema.md:108-123`,
   `:207-217`, `:734-817`). W4 defaults unlisted commands/subjects to deny
   (`design/04-agent-roles-and-model-routing.md:184-213`, `:449-456`).
3. **Concrete failure scenario.** The future catalogue author invents a generic
   `ProposeDecision` subject for inventory acceptance, a generic review command for a
   Spike verdict, and reducer/projection mappings from the same candidate registry the
   runtime uses. Candidate expected rows and runtime rows agree exactly and all listed
   §8 names are present, but the missing owner relationships were never frozen by W11.
4. **Impact.** Hidden implementation authority remains at review, acceptance and
   projection boundaries. Exact-row tests cannot distinguish a conforming materialization
   from one that selected different producers or projections because the W11 owner side
   has no complete row to compare.
5. **Required disposition.** **Fix now.** A separately accepted future catalogue may
   serialize and content-address W11, but it may not be the first authority that decides
   W11 semantics.
6. **Exact proposed interface change.** Add a literal W11 owner annex/table with one row
   for every W11 command/discriminant and every required shared-W2 supporting command.
   Each row must bind the exact command schema identity, authority subject source,
   proposal/review/acceptance preconditions, ordered event schemas/producers, affected
   streams/write set, reducer, projection targets, receipt and distinct tests. Include
   rubric/scope/path authority creation, all Decision proposals, Assay and Spike review,
   cancel/resume/supersede, dossier/inventory/mapping acceptance, transition and cutover.
   The future expected catalogue must copy these complete rows, not fill blanks.
7. **Affected decisions/work packages.** P-005/P-022/P-032/P-034; WP6.5-WP6.7;
   prior M-4; W11-I12/I15-I18; tests 1, 3, 11-13 and 18.

### R2-M5 — Cancellation and Partial/review paths are not executable

1. **Claim.** The lifecycle diagrams and command catalogue disagree, and cancellation
   creates Candidate/aggregate states with no authorized recovery or terminal path.
2. **Evidence.** The Assay aggregate permits `requested/evidence_collecting -> partial |
   cancelled` and only `partial/scored/reviewed -> superseded` at W11 `:293-299`, but
   `RecordAssayReview` accepts either a scorecard or Partial and emits `AssayReviewed` at
   `:337`. Candidate `assay_partial` may return to `assay_pending` or decision pending at
   `:273-290`, yet no command implements that return. Both cancellation rows say
   cancellation cannot change the Candidate gate (`:338`, `:346`). `RequestAssay`
   accepts only a registered Candidate or an exact revisit Decision, and
   `RegisterSpikePlan` requires `spike_planning_authorized` (`:334`, `:342`). Revisit is
   defined only from `parked`, while PromotionDecision requires scorecard/verdict
   evidence (`:286-290`, `:458-486`). Supersession rows require a replacement aggregate
   already to exist (`:339`, `:347`).
3. **Concrete failure scenario.** Cancel an Assay while evidence is collecting. The
   Assay becomes terminal `cancelled`; the Candidate remains `assay_pending`; there is
   no scorecard/verdict from which to propose PARK, `RequestAssay` cannot create a
   replacement from that state, and supersession cannot run because no replacement
   exists. The analogous Spike cancellation strands the Candidate at
   `spike_authorized` or `spike_running`. Separately, reviewing a Partial requests an
   undefined `partial -> reviewed` Assay transition.
4. **Impact.** Ordinary cancellation, unavailable evidence, or bounded Partial can
   permanently strand a Candidate or force an implementation-specific escape command.
   This undermines W11's fail-closed practicality and makes the supposedly complete
   state/test matrices non-deterministic.
5. **Required disposition.** **Fix now.** Cancellation must remain non-promotional, but
   it needs an explicit Candidate consequence and a lawful new-aggregate/revisit path.
6. **Exact proposed interface change.** Publish one closed transition matrix for
   Candidate, Assay and Spike with one command/event/reducer row per edge. Choose and
   specify whether cancellation atomically parks the Candidate through a separate
   Stephen Decision, creates a typed `*_cancelled` Candidate state followed by an exact
   revisit Decision, or permits a replacement aggregate from a cancellation event.
   Define the Partial path explicitly: review Partial only if `partial -> reviewed` is
   legal, otherwise use a distinct review projection; define whether more evidence
   resumes the same aggregate or creates a new one; and order replacement creation and
   supersession without circular preconditions.
7. **Affected decisions/work packages.** P-005/P-032; WP6.5/WP6.6; prior M-1/M-4;
   W11-I02/I04-I07; tests 4, 5, 7 and 11.

## 5. Prior R1 finding re-test

| Prior finding | R2 disposition | Independent re-test |
|---|---|---|
| C-1 — dossier expected oracle | **Not closed; reclassified blocking Major R2-M1** | Six literal families, temporal separation and coordinated-omission tests are now strong, but the accepted record has no acyclic self-content-addressing procedure. |
| C-2 — whole-path exact universe | **Not closed; reclassified blocking Major R2-M2** | Exact bytes, independent reproduction, unknown-byte coverage and item/event bijection are added, but inventory/mapping hashes and lifecycle form a cycle. |
| M-1 — Assay/Spike aggregate identity | **Identity closure passes; lifecycle still blocked by R2-M5** | `asy_`/`spk_` creation and relation rules reject foreign aggregates; cancellation/Partial/supersession paths remain non-executable. |
| M-2 — request-time rubric | **Not closed; R2-M3** | Rubric/scope IDs are frozen before collection, but the scope and its producer-relative acceptance authority are undefined. |
| M-3 — source re-observation | **Closed at specification level** | Step 4 independently resolves and rehashes every component and source dependency from verified handles/resolvers and includes source-specific attacks. |
| M-4 — command/event/W4 catalogue | **Not closed; R2-M4/R2-M5** | Five formerly omitted commands and review/cancel/supersede rows are added, but prerequisite proposal/review/acceptance and per-row reducer/projection relations remain absent or inconsistent. |
| M-5 — per-item stored relation | **Not closed; R2-M2** | The exact relation fields and valid-foreign attacks exist, but the relation cannot be content-addressed against the inventory in the stated order. |
| M-6 — operation-time Windows identity | **Closed at specification level** | Registered-root junction, no-follow traversal, volume/file IDs, hardlinks, held parent, atomic replace, post-verify and phase-specific race/Partial behavior are normative. |
| m-1 — Paper Claim lane | **Closed** | Paper Claim is Required for governance/consumer non-compensation and authorizes no claim action. |
| m-2 — root evidence register | **Closed** | Tracked section 8 records paths, bytes/hashes, mutability and limitations; current read-only observations match. |

## 6. Design-entry-criteria audit

| README criterion | R2 disposition | Evidence / blocker |
|---|---|---|
| 1. Governing decisions accepted or assumptions explicit | Pass for authorship | P-004/P-005/P-021/P-022/P-026/P-032/P-034/P-036, W11-A1 and both D-G6-4 limbs are explicit. |
| 2. Evidence inputs listed in repository register | Pass | Root register section 8 is tracked, linked, exact and correctly bounded. |
| 3. Boundaries and consumers identified | Pass | W1/W2/W4/W5/W9/W10/Vault/external consumers remain explicit. |
| 4. Independent review owner | Pass for assignment; outcome does not accept | Exact R2 branch/context is distinct; evidence was complete. |
| 5. Acceptance tests stated before implementation | **Fail** | R2-M1-R2-M5 leave multiple positive fixtures, transition matrices and exact owner rows unconstructible or undefined. |

## 7. Decision and owner-authority audit

| Decision/gate | R2 disposition |
|---|---|
| P-004 / P-021 | **Keep; W11 blocked.** Path/writer exclusivity and `dual_owned` prohibition remain correct. R2-M2/R2-M5 prevent a conforming transition sequence; the §7.3 physical protocol itself passes. |
| P-005 / P-022 | **Keep.** Promotion and migration remain human-locked and this review is context-distinct. R2-M3/R2-M4 require exact producer-relative and command authority to implement those decisions. |
| P-026 | **Keep.** The reviewed commit is specification-only and performed no legacy/successor mutation. |
| P-032 | **Keep direction; rework W11.** Canonical portfolio/Discovery integration remains appropriate, but the authority/catalogue/lifecycle gaps block acceptance. |
| P-034 | **Keep direction; rework transition/cutover lifecycle.** No dual-running or implicit import was authorized; R2-M2 prevents the specified per-item-to-final-cutover sequence. |
| P-036 | **Keep and do not broaden.** It approves the earlier WP6 launch basis, not W11, its future schemas, implementation or migration. |
| D-G6-4 limb 1 | **Remain open.** Exact revision `d24df9d...` has five open Majors and must not be presented for acceptance. |
| D-G6-4 limb 2 | **Remain open and hard-stopped.** No first batch can be approved against a cyclic inventory/mapping authority. |
| W11-A1 | **Defer / default omit.** The optional combined view is not needed to repair the blocking authority/lifecycle defects. |

No owner-approved decision is reversed. The required changes make the accepted authority
and ownership decisions executable rather than replacing them.

## 8. Complete invariant -> enforcement -> test disposition

| Invariant | R2 disposition | Reason |
|---|---|---|
| W11-I01 | Pass at design level | Immutable state-free object intent remains explicit. |
| W11-I02 | **Blocked** | Aggregate IDs exist, but inventory/mapping relations and cancel/resume/supersede lifecycle are not constructible (R2-M2/R2-M5). |
| W11-I03 | Pass at design level | Direct/multi-hop required-edge acyclicity and atomic rejection remain explicit. |
| W11-I04 | **Blocked** | Request-time hashes are frozen, but accepted scope authority and Partial/cancel transitions are incomplete (R2-M3/R2-M5). |
| W11-I05 | Pass at design level | Assay/Spike evidence remains non-compensable for Stephen's Decision. |
| W11-I06 | Pass at design level | PASS/FAIL/PARTIAL and kill/unknown truth conditions remain closed. |
| W11-I07 | Pass for promotion authority; lifecycle blocked | Exact actor/subject/gate/evidence rules pass, but some paths cannot reach a proposal lawfully (R2-M5). |
| W11-I08 | Pass at design level | PROMOTE excludes Dispatch/pre-registration/result/claim effects. |
| W11-I09 | **Blocked** | Literal expected rows and independence are strong, but the expected authority has no acyclic accepted identity (R2-M1). |
| W11-I10 | **Partial** | Independent component/source rehash and exact closure pass; positive admission is blocked by R2-M1. |
| W11-I11 | Pass at design level | Isolated staging, complete write set, tail/version checks and atomic batch remain explicit. |
| W11-I12 | **Fail** | The catalogue is not yet the complete W11 owner relation and omits prerequisite authority transitions (R2-M4). |
| W11-I13 | Pass at design level | Generated/combined views remain denied as authority inputs. |
| W11-I14 | Pass at design level | §7.3 closes registration-to-commit physical identity and records unavailable Windows coverage as Partial. |
| W11-I15 | Pass at design level | Annotation remains evidence until a separate authorized command. |
| W11-I16 | **Fail** | Exact relation fields exist but inventory/mapping content identities are cyclic (R2-M2). |
| W11-I17 | Pass at design level | Per-item command performs no legacy-path write. |
| W11-I18 | **Fail** | Complete final inventory cannot be related to mappings/events in the stated acyclic order (R2-M2). |
| W11-I19 | Pass at design level | Reverse cutover remains invalid. |
| W11-I20 | Pass at design level | Deterministic authority-neutral rebuild is now bound to §7.3 physical publication. |
| W11-I21 | Pass at design level | Paper Claim governance is Required and W5 authority remains non-compensable. |
| W11-I22 | Pass at design level | Unknown major schema/event and broken hash/ref stop authoritative replay. |

## 9. Complete pre-implementation test-catalogue disposition

| Test | R2 disposition | Reason |
|---:|---|---|
| 1 | **Blocked** | No literal complete owner row set for all prerequisite commands/reducers/projections (R2-M4). |
| 2 | Pass as required pattern | One-field type/value/enum/pattern/required/additional-property attacks are appropriate. |
| 3 | **Blocked** | Expected catalogue and dossier expected content cannot yet provide constructible complete rows (R2-M1/R2-M4). |
| 4 | **Blocked** | Aggregate IDs pass; accepted scope authority and cancellation/Partial matrices do not (R2-M3/R2-M5). |
| 5 | **Blocked** | Aggregate foreign-substitution tests are specifiable; transition relation is cyclic (R2-M2). |
| 6 | Pass at design level | Legacy numeric rule matches both contracts and `decision` remains recommendation-only. |
| 7 | Pass at design level | Producing-seam PASS/FAIL/PARTIAL/kill/unknown mutations are explicit. |
| 8 | Pass at design level | Option-specific and non-Stephen negatives remain explicit. |
| 9 | **Blocked** | Six-family/source attacks are strong, but no conforming positive expected-set authority exists (R2-M1). |
| 10 | Pass at design level | Failure injection and zero publication map to W2 atomicity. |
| 11 | **Blocked** | “Every literal command” is not a closed owner universe and cancellation paths are incomplete (R2-M4/R2-M5). |
| 12 | Pass at design level | Scout source/dedup/collision/direct-judgment/direct-write negatives are closed. |
| 13 | Pass at design level | Annotation lifecycle and writer/projection negatives are closed. |
| 14 | Pass at design level | Registered-root junction, alias, hardlink/file-ID, parent and phase-specific race suite is explicit. |
| 15 | **Blocked** | Accepted relation hash cannot be constructed against the mutually referencing inventory (R2-M2). |
| 16 | **Partial** | Disjoint paths/zero legacy write/`dual_owned` rejection pass; the transition relation does not. |
| 17 | Pass at design level | Deletion/rebuild/projector-version and physical-publication behavior are explicit. |
| 18 | **Blocked** | Byte/item coverage and race attacks are strong, but final inventory/mapping/event closure is cyclic (R2-M2). |
| 19 | Pass at design level | Genesis/snapshot/unknown-schema replay follows W2. |
| 20 | Pass at design level | Paper Claim consumer non-compensation is explicit and performs no claim action. |

## 10. Cross-spec consistency matrix

| Invariant / identity | Owning source | W11 claim | R2 result |
|---|---|---|---|
| First-class immutable record and canonical stream | W2 §§5-9 | `obj_`, `asy_`, `spk_`, exact references | Aggregate identity passes; some lifecycle edges do not (R2-M5). |
| Decision != RuleEvaluation | W2 §18; P-005/P-022 | Score/verdict evidence cannot resolve promotion | Pass. |
| Acceptance bar independent and frozen before observation | W5 §§6-11 | Request rubric/scope; dossier expected set | Dossier separation is strong but unmaterializable; Assay scope authority is undefined (R2-M1/R2-M3). |
| Complete expected-set closure | W5 §11; WP6 master §6 | Six dossier families and future W11 catalogue | Dossier rows are complete; W11 owner catalogue remains deferred/incomplete (R2-M4). |
| Atomic publication | W2 §§8-9/13 | Dossier/promotion/transition batches | Pass where prerequisites can exist. |
| Review and Decision lifecycle | W2 §§17-19 | §4.2 review/ResolveDecision rows | Fail: prerequisite proposal/review/acceptance rows are incomplete (R2-M4). |
| Observation != adoption | W2 §22; P-032/P-034 | Legacy observation, mapping, transition | Semantic split passes; content-address order fails (R2-M2). |
| One owner; no shared physical writer | W1 §§9-10; P-004/P-021 | §7 paths, relation, inventory and §7.3 | Physical protocol passes; transition sequence blocked (R2-M2). |
| Profile capability != command authority | W4 §§7/15/19 | §4.2 profile and exact subject per row | Partial: named rows are strong, but hidden supporting commands/subjects remain (R2-M4). |
| Portfolio Claim != W5 claim authority | W1 §5.1; W5 §§14/19 | Required Paper Claim governance | Pass. |
| Specification != implementation/migration authority | P-026/P-036; WP6 master | Hard stops and `review_pending` | Pass; no hidden authorization was exercised. |

## 11. Research-assurance lane disposition

| Lane | R2 disposition |
|---|---|
| Output / Provenance | **Required — primary; blocked.** Exact revision/hash, source rehash, no overwrite, path identity and consumer boundaries are strong. R2-M1/R2-M2/R2-M4 prevent the prospective authority chain from being reproducible and owner-complete. |
| Topology | **N/A — keep.** W11 maps the legacy topology gate as compatibility evidence but defines no filtration, PH object, homology or metric judgment. A later domain pack remains required. |
| Stochastic / Null Model | **N/A — keep.** Null/comparator refs are carried prospectively; no null operation, RNG, p-value or exchangeability claim is decided here. |
| Statistical / Panel | **N/A — keep.** No estimand formula, eligibility, weighting, imputation, variance or multiplicity rule is defined. |
| Representation | **N/A — keep.** W11 records representation refs without fitting or judging transformations. |
| Paper Claim | **Required — governance/consumer boundary; pass.** W11 now tests that portfolio records/evidence/views cannot satisfy W5 result/claim authority and performs no live claim action. |

The prospective provenance review therefore passes referent identity, immutable R1
trace, live evidence fidelity, source rehashing, path separation, no-overwrite intent,
and claim routing, while failing constructible content-address and complete owner-command
lineage. Retrospective result-file date suffixes, seeds, B/L, cache lineage and result
vault filing remain genuinely not applicable.

## 12. Failure behavior, practicality, and proportionality

W11's ordinary failure behavior is generally fail-closed and should be preserved:
schema/relation/authority failure writes no lifecycle event; missing Spike evidence is
Partial; model-only promotion fails; dossier validation has zero publication; projection
deletion changes no authority; path identity that cannot be proven is Partial; reverse
cutover is invalid; and unknown major records stop replay.

The five findings expose failure modes absent from section 9:

- `content_address_cycle` / `self_identity_unmaterializable` must block authority
  acceptance rather than invite a hidden excluded-field convention;
- `authority_lifecycle_undefined` must block “accepted rubric/scope/path” predicates;
- `transition_dead_end` must produce an explicit state/resume condition instead of
  stranding a Candidate; and
- an absent owner row must be `owner_contract_incomplete`, not supplied by the runtime
  registry or future expected-catalogue producer.

The smallest proportionate repair remains workload-sensitive:

| Work class | Proportionate control after repair |
|---|---|
| Scout/Candidate | Keep the current small closed source/dedup/collision/grant path. |
| Assay/Spike | One accepted producer-relative rubric/scope or plan relation plus a closed cancel/Partial/revisit matrix; no dossier-scale inventory. |
| Promotion | Keep exact Stephen Decision and one atomic Candidate batch. |
| Dossier admission | Use two-stage content/acceptance identity, complete six-family expected rows, independent source reads and atomic publication. |
| Per-item transition | Use one source-only inventory row -> mapping -> transition chain; do not require final cutover closure per item. |
| Whole-path cutover | Build one later closure over source inventory, mappings/events, writer revocation, final observation and §7.3 races. |
| Generated views | Keep deterministic projector/source-position identity and authority neutrality. |
| Combined view | Omit by default until core lifecycle and path tests pass. |

The controls are still concentrated at appropriate risk boundaries. The repairs reduce
rather than add bureaucracy by replacing impossible mutual hashes and implicit commands
with a topologically ordered authority chain.

## 13. Required revision plan

### Immediate specification corrections

1. Split expected-set content from post-serialization acceptance provenance (R2-M1).
2. Split source inventory from mapping/event cutover closure and remove mutual hashes
   (R2-M2).
3. Define `AssayEvidenceScope` and exact rubric/scope proposal-review-acceptance-staleness
   lifecycle relative to the prospective/actual producer (R2-M3).
4. Freeze the complete W11 owner row catalogue, including supporting W2 proposal/review/
   acceptance and per-row reducer/projection relations, before future serialization
   (R2-M4).
5. Replace narrative lifecycle fragments with one executable Candidate/Assay/Spike
   transition matrix covering cancellation, Partial, review, resume, replacement and
   supersession (R2-M5).
6. Reconcile every affected invariant, test, failure row, decision row and cross-spec
   matrix entry without narrowing the preserved controls.

### Owner decisions

- Do not present D-G6-4 limb 1 for exact revision `d24df9d...`.
- Keep D-G6-4 limb 2 open; no first transition batch can be authored against the cyclic
  inventory/mapping contract.
- Continue to defer/omit W11-A1 combined view.

### Later-work dependencies

- Strict schema and expected-catalogue materialization remains a separate reviewed and
  Stephen-accepted task, but it must serialize complete W11 owner rows rather than
  inventing them.
- WP6.6 remains downstream of accepted W11 and WP6.1.
- WP6.7/W9 remain downstream of the repaired acyclic transition/cutover contracts and a
  separately accepted first batch.

## 14. Residual risks after required revision

- Future expected/runtime implementations may still share an enumerator. Reconstruct
  both sides separately and retain coordinated-pair omissions/substitutions.
- Content-addressed records need an explicit hash-dependency DAG and topological
  materialization test; no self-edge or strongly connected hash component may be hidden
  behind “exact hash” prose.
- Windows junction/reparse/hardlink/file-ID support varies by volume and privilege.
  Required unavailable physical-exclusivity tests remain Partial, not pass.
- Living legacy prose remains mutable. Every later observation/mapping/cutover binds
  fresh bytes; the dated 2026-07-18 hash is not migration authority.
- Generic shared-W2 commands can still hide W11-specific subjects. Materialization review
  must compare the complete subject/discriminant relation, not only command names.
- W9/W10 are downstream and may not narrow W11 or introduce TDL paths into the reusable
  core.
- Passing schemas/relations proves conformance, not scientific adequacy of future Assay
  rubrics, Spike designs, results or claims.

## 15. Validation, hard stops, and change log

### 15.1 Validation evidence

- Both required contract gates passed against 101 contracts with exit 0.
- Ignored runner-artifact inventory was zero before and after; Git stayed clean.
- `git diff --check 70074d4... d24df9d...` passed.
- Relative-link validation across the five changed Markdown files found zero broken
  repository-relative links.
- R1 original/cherry-pick/target blob identity is exactly
  `8af8add2bd1853b4aaf6b0178279013256dfb044`.
- All 20 live package source/component hashes matched; root evidence paths/hashes and
  vault-junction observation matched.

No broad pytest command, provider call, compute, projection, ingestion, dossier
admission, ownership transition, cutover, result/eligibility/claim action, schema
materialization, or vault write was run.

### 15.2 Hard-stop confirmation

This review does **not** accept W11, exercise Stephen's authority, approve either D-G6-4
limb, approve a transition batch, authorize WP6.6/WP6.7, create `.research-system/`
state, materialize schemas/catalogues, write any vault path, ingest Scout/annotation
evidence, admit the TDA-scale package, transition ownership, cut over a path, run a live
model, change eligibility, accept a result, or promote a claim.

### 15.3 Files changed

- `docs/plans/agentic-research-system/reviews/adversarial-wp6-5-w11-spec-remediation-r2-review-2026-07-18.md`
  — this review report only.

Reviewed W11, immutable R1 report, evidence register, README, decision register, owner
specifications, live backlog, package manifest/components, contracts, and vault paths
changed: **none**.

## 16. Final disposition

**Verdict:** `rework_required`
**Exact reviewed commit:** `d24df9d26f0d906d177eafa1eaeabb65a5515004`
**Evidence status:** `Complete`
**Open findings:** `0 Critical / 5 Major / 0 Minor`

The remediation is materially stronger and closes four prior finding families at the
specification level, but W11 cannot be accepted until the five Majors above are repaired
and a fresh exact-commit review reports no open Critical or Major finding.
