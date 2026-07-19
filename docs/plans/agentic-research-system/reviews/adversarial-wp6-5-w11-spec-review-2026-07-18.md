# Adversarial WP6.5 W11 specification review

**Review date:** 2026-07-18
**Reviewer posture:** fresh, distinct-authority, adversarial design review
**Target repository:** `TDL`
**Assigned review branch:** `review/ars-wp6-5-w11-spec-r1`
**Exact reviewed commit:** `70074d42eade8460808e4d1d29348b7806eff2d0`
**Exact reviewed parent:** `4e6fd0cb26c04ff9707c3183f663461d752b53b9`
**Subject branch / PR:** `pipe/ars-wp6-5-w11-spec` / draft PR #121
**Review evidence status:** `Complete`
**Verdict:** `rework_required`
**Finding count:** **2 Critical, 6 Major, 2 Minor**

## 1. Executive verdict

Commit `70074d42eade8460808e4d1d29348b7806eff2d0` is **not safe to accept as
the W11 specification revision**. It preserves several important authority boundaries:

- `PromotionDecision` is a W2 Decision, is resolved only through an exact-subject
  Stephen-attributed grant, and cannot be replaced by `AssayScorecard`, `SpikeVerdict`,
  `RuleEvaluation`, a model recommendation, or a Manager action
  (`design/11-portfolio-and-discovery-lifecycle.md:34-40`, `:358-385`; accepted W2
  `design/02-task-event-and-artifact-schema.md:795-817`).
- Candidate -> Assay -> Spike -> pre-registration remains a gated sequence. A Spike is
  separately planned and approved before execution, and PROMOTE authorizes only one
  named next design step (`design/11-portfolio-and-discovery-lifecycle.md:275-286`,
  `:327-385`).
- The legacy backlog, successor projection, human annotation inbox, and optional
  combined view are assigned distinct path roles and writer sets; a partial item
  transition does not itself repurpose the living legacy path (`:521-645`).
- The draft creates no implementation, projection, ingestion, admission, transition,
  migration, result, eligibility, live-call, or claim authority (`:9-17`, `:53-56`,
  `:805-830`).

Those preserved controls do not close the load-bearing interfaces. The independently
accepted dossier expected set is named but never defined as a record, so a package
producer can still supply a self-consistent manifest and command expectations with the
same omission. Whole-path cutover similarly relies on an “independently reproduced
inventory” with no schema, content address, complete expected membership, producer,
reviewer, or accepting authority. Both gaps can turn correlated omissions into canonical
portfolio state or retirement of a still-authoritative legacy path.

The remaining Majors make the proposed tests unenforceable as written: Assay and Spike
instances lack canonical aggregate/stream identities; the Assay rubric is not frozen on
`RequestAssay` before evidence collection; source-dependency bytes are not re-observed;
five authority-bearing commands sit outside the command/event catalogue; a per-item
transition does not bind one observed legacy record to one accepted target relation; and
the Windows path contract has no operation-time handle/file-identity protocol closing a
reparse/junction swap between validation and replace.

**Required disposition:** revise the specification, reconcile every finding, and obtain
a fresh adversarial review of the new exact commit before D-G6-4 limb 1 can be presented
to Stephen. D-G6-4 limb 2, WP6.6, WP6.7, schema/catalogue materialization, and all
implementation or migration remain hard-stopped.

## 2. Review identity, scope, and direct evidence

### 2.1 Hard revision precondition

The Codex worktree initially had detached `HEAD`. Before switching, detached `HEAD` and
`refs/heads/review/ars-wp6-5-w11-spec-r1` independently resolved to
`70074d42eade8460808e4d1d29348b7806eff2d0`; `git status --short` was empty. The one
permitted deterministic command, `git switch review/ars-wp6-5-w11-spec-r1`, succeeded.
The resulting symbolic branch, `HEAD`, cwd, and clean status were rechecked before any
write. The review used the committed subject bytes, not an uncommitted author checkout.

The complete subject diff is three files:

- `docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md`
  (new, 855 lines);
- `docs/plans/agentic-research-system/design/README.md` (W11 index/status addition);
- `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` (non-decision
  W11 status entry).

### 2.2 Owner and evidence sources read

The review read the complete W11 subject and complete WP6 master; the complete affected
diff; the complete R5 review; the complete current-system evidence register; the exact
P-004, P-005, P-021, P-022, P-026, P-032, P-034, and P-036 entries; the W1/W2/W4/W5
owner sections named by W11; the W9/W10 roadmap owner sections; the relevant master
transition-plan sections; and the live legacy/package sources named by W11.

Direct owner anchors include:

- WP6 master WP6.5 scope and hard ordering at
  `implementation/06-wp6-gate6-readiness-and-integration-plan.md:138-178`, D-G6-4 at
  `:214-223`, assurance requirements at `:224-260`, forward obligations at `:262-277`,
  and exit gate at `:290-343`.
- W1 portfolio, authority, projection, compatibility, and downstream ownership at
  `design/01-system-architecture.md:119-133`, `:275-306`, `:363-465`, `:523-542`, and
  `:648-654`.
- W2 record/ID, command/batch, Decision/RuleEvaluation, import, replay, and invariant
  ownership at `design/02-task-event-and-artifact-schema.md:108-227`, `:229-353`,
  `:547-569`, `:672-721`, `:781-817`, `:858-963`, and `:1013-1038`.
- W4 role/profile and authority requirements at
  `design/04-agent-roles-and-model-routing.md:184-213`, `:356-389`, `:449-477`.
- W5 independent requirement/oracle, lane, claim, and authority requirements at
  `design/05-research-assurance-and-independent-review.md:144-220`, `:291-320`,
  `:402-415`, `:431-482`, and `:502-551`.
- W9/W10 owner bounds at `02-design-and-deliverables-roadmap.md:194-225`.
- R5's exact approved WP6-plan basis and preserved W11/D-G6-4 deferral at
  `reviews/adversarial-wp6-plan-suite-remediation-r5-review-2026-07-17.md:12-41`,
  `:235-267`, `:280-291`, and `:306-336`.

### 2.3 Live evidence fidelity

The live evidence was accessible read-only; this review is not `Partial`.

| Evidence | W11 claim | Independent observation | Disposition |
|---|---|---|---|
| `C:\Users\steph\TDL\vault\00-Meta\Discovery\_backlog.md` | SHA-256 `37eec1ba...0269e7` at W11 `:100` | 26,392 bytes; SHA-256 exactly `37eec1ba6bb7929d95d5349ada2f75d93636c8356aad5dffc6a59981fc0269e7`; contains the planned/not-dispatchable TDA-scale dossier, registered sheaf item, MCbiF decision-pending item, superseded entries, and legacy PROMOTE/PARK/KILL prose | Pass as a dated observation, not a frozen authority identity |
| Live TDA-scale package manifest | SHA-256 `e20d173b...61cbf` at W11 `:102-107` | 5,843 bytes; exact SHA-256 `e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf` | Pass |
| Live TDA-scale master component | SHA-256 `277f57f9...241ea` at W11 `:102-107` | 28,244 bytes; exact SHA-256 `277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea` | Pass |
| Package manifest source/component rows | 17 immutable components plus three separately hashed sources | All 20 linked source/component files exist and recompute to their declared SHA-256; manifest lines `18-48` | Pass for current evidence fidelity; not an admission decision |
| Legacy assay and Spike contracts | W11 maps the current rubric and user-approved Spike seam | `contracts/discovery-harness/assay-scorecard.yaml:1-70` and `spike-pre-registration.yaml:1-78` require the Boolean topology gate, integer axes, PROMOTE threshold, user approval, toy scope, null, baselines, and `/pre-reg-to-dispatch` | Pass; the legacy `decision` field must remain recommendation-only |

The registered TDL vault path currently traverses a Windows junction:
`C:\Users\steph\TDL\vault` is a `Directory, ReparsePoint` targeting
`C:\Users\steph\Documents\TDA-Research`. The three proposed `00-Meta/ARS/...` paths do
not currently exist. This makes registered-root identity and operation-time reparse
handling a real design requirement, not a hypothetical platform embellishment.

## 3. Findings summary

| ID | Severity | Finding | Blocks |
|---|---|---|---|
| C-1 | Critical | The dossier's independent expected oracle is named but not defined or accepted as a complete literal record | W11-I09/I10; D-G6-4 limb 1; WP6.6 |
| C-2 | Critical | Whole-path cutover has no content-addressed exact inventory authority, so an omitted legacy item can disappear at cutover | W11-I18; D-G6-4 limbs 1/2; WP6.7/W9 |
| M-1 | Major | Assay and Spike projected instances have no canonical aggregate/stream identity | W11-I02/I04-I07; tests 1/4/5 |
| M-2 | Major | `RequestAssay` does not freeze the accepted rubric before evidence collection | W11-I04; Candidate -> Assay ordering |
| M-3 | Major | Dossier source-dependency bytes are included in declared closure but never independently resolved/rehashed | W11-I10; test 9; WP6.6 |
| M-4 | Major | The command/event catalogue omits five later commands and their exact W4 authority subjects | W11-I12/I15-I18; tests 1/3/11-13/18 |
| M-5 | Major | Per-item transition fields are individually typed but lack one stored source-item-target relation | W11-I02/I16; test 15; D-G6-4 limb 2 |
| M-6 | Major | Static path registration does not close operation-time reparse/junction/hardlink races | W11-I14/I18/I20; test 14 |
| m-1 | Minor | Paper Claim is marked N/A although W11 changes claim-governance schema and consumer predicates | Six-lane disposition; W11-I21 |
| m-2 | Minor | New live evidence is not listed in the designated evidence register | `design/README.md` entry criterion 2 |

## 4. Critical findings

### C-1 — The dossier's independent expected oracle is undefined

1. **Claim.** `AdmitResearchDossier` can publish canonical portfolio objects and
   ScopeDefinitions without a defined, independently authored and accepted literal
   expected set. The text names three different things — `ResearchDossierManifest`, an
   “expected-set manifest”, and the W11 interface “expected catalogue” — but defines no
   one record that owns the expected component/source/object/scope/edge rows.
2. **Evidence.** W11 promises an “independently accepted manifest” and exact closure at
   `design/11-portfolio-and-discovery-lifecycle.md:41-44`. Section 5.1 defines the
   dossier producer's `ResearchDossierManifest` at `:389-433`. The command accepts
   expected key-set hashes and counts at `:435-448`. Step 1 then names an
   `expected-set manifest` at `:456-460`, but that object has no schema, record family,
   fields, producer, reviewer, acceptor, lifecycle, path, or event. Section 8 instead
   defines `.research-system/evals/expected/w11-portfolio-discovery-v1.json` as an
   interface catalogue with command/event rows at `:647-670`; it is not a dossier's
   literal component/source/object/scope/edge oracle. W11-I09 then switches terminology
   again to “accepted expected catalogue/admission profile” at `:725`. W5 requires a
   bound independent oracle plus owner, implementer, reviewer, version/hash, and
   fixtures before activation (`design/05-research-assurance-and-independent-review.md:291-320`).
3. **Concrete failure scenario.** A dossier producer omits component `SPEC-02` from both
   its `ResearchDossierManifest` and the command-supplied expected hashes/counts. The
   handler independently rehashes every *supplied* component, recomputes the same
   reduced closure, and passes. A coordinated manifest/command mutation test also
   passes because there is no pre-observation accepted literal oracle against which the
   pair must differ.
4. **Impact.** An incomplete or semantically substituted package can be admitted as
   canonical portfolio and ScopeDefinition authority. This is invalid acceptance, not
   merely weak documentation.
5. **Required disposition.** **Fix now; re-review required.** Do not defer the identity
   to WP6.6 because W11 acceptance is meant to freeze the admission interface.
6. **Exact proposed interface change.** Define one closed
   `DossierExpectedSet` record (or one unambiguously named equivalent) containing the
   complete literal component, source, object-blueprint, ScopeDefinition-blueprint,
   edge, and relationship rows; schema ID/version; repository path; Git blob; SHA-256;
   author; producer-relative independent reviewer; accepting authority; accepted event;
   and effective dossier/profile scope. It must be accepted before the dossier manifest
   is produced or first observed. `AdmitResearchDossier` must reference its exact
   ID/revision/hash only; the handler derives expected hashes/counts from that record,
   never from command values. Add a coordinated producer-manifest/command/runtime
   mutation that must still disagree with the frozen expected set.
7. **Affected decisions/work packages.** P-032; D-G6-4 limb 1; WP6.5; WP6.6;
   W11-I09/I10/I11; acceptance tests 3, 9, and 10.

### C-2 — Whole-path cutover can omit a still-legacy item

1. **Claim.** The whole-path gate relies on an “independently reproduced inventory” but
   defines neither a complete expected membership nor an accepted inventory identity.
   Therefore exact completion cannot be proved before the legacy-named path is
   repurposed.
2. **Evidence.** W11 requires every item formerly using the path to be transitioned at
   `design/11-portfolio-and-discovery-lifecycle.md:609-621`, then permits
   `CutOverDiscoveryPath` and a later projector at the legacy-named path at `:623-627`.
   No inventory schema, parser/version, item-key rule, source-byte relation, expected
   membership hash, producer, reviewer, accepting authority, or cutover command field is
   defined. W11-I18 and test 18 only say to “leave one” item and expect rejection
   (`:734`, `:774-775`); a test cannot generate a principled omitted-item case without
   an independent complete universe. P-034 prohibits implicit or bulk status upgrade
   (`03-decisions-and-open-questions.md:422-430`).
3. **Concrete failure scenario.** An inventory builder fails to parse a legacy backlog
   row with an old heading/alias and returns only items that already have transition
   events. A second run of the same parser “independently” reproduces the omission.
   Every listed item is successor-owned or closed, so cutover passes, legacy writer
   authority is revoked, and the legacy-named file becomes generated while the omitted
   item was still `legacy_owned`.
4. **Impact.** The cutover destroys the remaining item's authoritative writer path and
   silently upgrades or strands its authority, violating P-004/P-021/P-032/P-034.
5. **Required disposition.** **Fix now; re-review required.** D-G6-4 limb 2 cannot be
   used as a substitute because the defect is in the gate that makes a batch and path
   complete.
6. **Exact proposed interface change.** Define a content-addressed
   `LegacyPortfolioInventory` with exact final legacy path registration/revision,
   physical identity, bytes/hash, parser/schema version, complete one-to-one item rows,
   alias/source selectors, observed-record IDs/hashes, expected membership hash,
   independent reproducer evidence, reviewer, and accepting authority. The cutover
   command must compare this accepted expected inventory to a fresh independent
   observation of the exact final bytes and to the complete transition-event set. Add
   unknown-row, unparseable-row, alias-collision, coordinated parser/inventory omission,
   and post-inventory legacy-write races.
7. **Affected decisions/work packages.** P-004, P-021, P-032, P-034; D-G6-4 limbs 1
   and 2; WP6.5; WP6.7; future W9; W11-I16/I18/I19; tests 15, 16, and 18.

## 5. Major findings

### M-1 — Assay and Spike lifecycles have no aggregate identity

1. **Claim.** W11 projects independent Assay and Spike state machines but defines no
   canonical Assay/Spike instance ID or stream binding that connects request, plan,
   score/partial, attempt, verdict, supersession, and promotion evidence.
2. **Evidence.** The instance state machines are at
   `design/11-portfolio-and-discovery-lifecycle.md:250-268`; events are at `:275-286`.
   The record-family list at `:170-178` has scorecard/plan/verdict artefacts but no
   Assay or Spike aggregate. `AssayScorecard` carries Candidate and rubric refs but no
   assay request/instance ref (`:300-311`). `SpikeVerdict` carries Candidate, plan, and
   attempt refs but W11 never states that one of those is the Spike stream identity
   (`:339-350`). W2 requires stable first-class IDs and canonical stream/reference
   semantics (`design/02-task-event-and-artifact-schema.md:127-189`, `:307-331`).
3. **Concrete failure scenario.** Two Assays for the same Candidate and rubric are open
   after a revisit. A valid scorecard from request A2 is linked to A1, or a Partial for
   A1 supersedes A2, because all referenced members are valid but no stored request-to-
   scorecard relation exists. The analogous Spike events can be reduced against plan or
   attempt inconsistently across implementations.
4. **Impact.** Foreign-but-valid substitution can corrupt lifecycle and promotion
   evidence; tests 4/5 cannot state a one-to-one oracle.
5. **Required disposition.** **Fix now.** Define stable aggregate identity before schema
   materialization.
6. **Exact proposed interface change.** Add an exact Assay instance ID/stream created by
   `RequestAssay` and required on every Assay artefact/event/Decision. Add a Spike
   instance ID/stream, or explicitly make exact `SpikePlan` identity the aggregate and
   bind every Spike event/attempt/verdict to it. Specify prefix/kind, creation command,
   stream ID, revision rules, supersession, and cross-instance negative tests.
7. **Affected decisions/work packages.** P-032; WP6.5/WP6.6; W11-I02/I04-I07; tests
   1, 4, and 5.

### M-2 — The Assay acceptance bar is not frozen before evidence collection

1. **Claim.** `RequestAssay` does not bind an already accepted rubric revision/hash,
   allowing the acceptance bar to be selected or accepted after Assay evidence has
   begun.
2. **Evidence.** `RequestAssay` requires only Portfolio Steward grant and Candidate
   state/revisit authority (`design/11-portfolio-and-discovery-lifecycle.md:275-280`).
   The Assay state immediately enters `evidence_collecting` (`:250-255`). Only the later
   scorecard binds an accepted rubric (`:294-316`). The rubric owns axis set, order,
   recommendation predicates, Partial rules, source authority, reviewer, and acceptor
   (`:294-298`). The adversarial-review foundation rule and W5 separation require the
   producer not to define the bar after seeing its output
   (`design/05-research-assurance-and-independent-review.md:291-320`).
3. **Concrete failure scenario.** Evidence under rubric R1 is weak. After observing it,
   an actor accepts R2 with a narrower axis set or easier PROMOTE predicate, then emits a
   scorecard exactly matching R2. Missing/extra/stale-axis tests all pass because they
   compare only to the later accepted rubric, not the rubric frozen when evidence began.
4. **Impact.** Assay viability can be self-defined post-observation, invalidating the
   Candidate -> Assay -> promotion gate.
5. **Required disposition.** **Fix now.** This is an ordering/foundation defect.
6. **Exact proposed interface change.** Require `RequestAssay` to bind the exact
   accepted rubric ID/revision/hash, expected axis-set hash, evidence scope, and
   producer-relative requirement-scope acceptance before `evidence_collecting`.
   `RecordAssayScore`/Partial must equal that stored relation. Add late-rubric,
   post-request rubric swap, and same-Candidate foreign-request mutations.
7. **Affected decisions/work packages.** P-032; WP6.5/WP6.6; W11-I04/I05; tests 4-6.

### M-3 — Source dependencies are never independently re-observed

1. **Claim.** Source-dependency rows contribute hashes to the closure hash, but the
   handler's observation step re-resolves only components.
2. **Evidence.** W11 defines `source_dependencies[]` at
   `design/11-portfolio-and-discovery-lifecycle.md:391-414` and includes their complete
   rows in the closure at `:416-430`. Step 3 compares source keys, but step 4 says only
   “resolve each component independently” and recompute its bytes/size/hash/schema
   (`:462-466`). No later step reads source-dependency bytes. The live package proves
   this is a concrete class: its manifest has three separately hashed source files at
   lines 18-24.
3. **Concrete failure scenario.** A source PDF or citation map changes after the dossier
   manifest is authored. The manifest still contains the expected old source hash;
   component files are unchanged. Key-set and closure checks pass because the handler
   never hashes the current source bytes.
4. **Impact.** An admitted dossier can cite stale/tampered source evidence while
   claiming exact closure and provenance.
5. **Required disposition.** **Fix now.** Do not treat closure-row hashing as observed
   byte verification.
6. **Exact proposed text change.** Replace step 4 with: “Resolve every component **and
   every source dependency** independently from its registered root; recompute physical
   identity, bytes, size, hash, schema/media type, and source-authority class; compare
   each observed row one-to-one with the accepted expected row.” Add source-specific
   missing/inaccessible/tampered/alias/path-escape mutations.
7. **Affected decisions/work packages.** P-032; WP6.5/WP6.6; W11-I09/I10; test 9.

### M-4 — The command/event catalogue is not complete and authority is undefined

1. **Claim.** The section labelled command/event catalogue omits five later mutating
   commands and therefore omits their one-to-one command schema, event schema, authority
   subject, allowed role/profile, receipt, streams, write set, and tests.
2. **Evidence.** The purported catalogue is `design/11-portfolio-and-discovery-lifecycle.md:270-290`.
   Later sections introduce `AdmitResearchDossier` (`:435-477`),
   `IngestScoutObservationBatch` (`:488-503`), `IngestDiscoveryAnnotation` (`:562-576`),
   `TransitionPortfolioOwnership` (`:581-607`), and `CutOverDiscoveryPath`
   (`:609-627`). None appears in the catalogue. The W4 additions describe broad role
   purposes but do not allocate those command types (`:509-519`). W4 requires every
   profile to list exact allowed command types and a separate grant, and defaults all
   unlisted command/root/write classes to deny
   (`design/04-agent-roles-and-model-routing.md:184-200`, `:449-456`). Section 8 promises
   one complete row per interface but gives no closed literal interface inventory
   (`design/11-portfolio-and-discovery-lifecycle.md:647-670`).
3. **Concrete failure scenario.** Materialization assigns annotation ingestion to Scout
   because Scout handles observations, or assigns a generic project grant to dossier
   admission/cutover. Alternatively it omits one command entirely while a count-based
   “every interface” test is generated from the same incomplete registry. The
   `IngestScoutObservationBatch` path emits `CandidateRegistered` without an explicit
   equality contract to `RegisterCandidate`'s collision and authority semantics.
4. **Impact.** Default-deny cannot be configured from the specification, authority-
   bearing mutation can be multiply or incorrectly defined, and exact-row tests lack an
   owner source.
5. **Required disposition.** **Fix now.** The expected catalogue cannot repair an
   undefined owner inventory after implementation begins.
6. **Exact proposed interface change.** Expand one closed catalogue to every W11 object,
   artefact, Decision subtype, command, event, reducer, projection, receipt, and
   authority row. For each command bind exact `command_type`, schema ID/version,
   authority subject kind and ID source, allowed W4 profile, grant scope, preconditions,
   ordered events, complete streams/write set, reducer/projection, receipt, and distinct
   tests. State whether `CandidateRegistered` has two legitimate producers and require
   both to call the same exact registration validator/event schema, or give ingestion a
   distinct event.
7. **Affected decisions/work packages.** P-005, P-022, P-032, P-034; WP6.5/WP6.6/
   WP6.7; W11-I12/I15-I18; tests 1, 3, 11-13, and 18.

### M-5 — Per-item transition lacks a stored relational invariant

1. **Claim.** `TransitionPortfolioOwnership` lists individually valid fields but does
   not bind the item, exact observed legacy record, source selector/bytes, alias map,
   target object set, and migration Decision as one previously accepted relation.
2. **Evidence.** The payload at
   `design/11-portfolio-and-discovery-lifecycle.md:581-587` contains item ID/type,
   source registration/bytes/hash, targets, alias mapping, collision scan, Decision,
   versions, and write set, but no exact `LegacyRecordObserved` ID/revision/hash, typed
   source-row selector, or accepted source-item-target mapping identity. Success records
   the submitted source hash/targets at `:597-607`. W2 requires two-step
   `LegacyRecordObserved` then authorized adoption and forbids inferred authority
   (`design/02-task-event-and-artifact-schema.md:905-935`). W11-I16 and test 15 demand a
   valid-foreign substitution rejection (`design/11-portfolio-and-discovery-lifecycle.md:732`,
   `:769`) but name no stored relation against which equality is checked.
3. **Concrete failure scenario.** Use the exact valid source bytes/alias row from legacy
   item A, valid successor target objects for B, and a valid migration Decision scoped
   to B. Every member and hash is valid; without a stored relation, the command can
   freeze A's provenance onto B or transition the wrong item.
4. **Impact.** Authority and epistemic lineage can be assigned to the wrong item even
   while `dual_owned` remains schema-invalid.
5. **Required disposition.** **Fix now.** The first transition-batch owner record cannot
   compensate for a handler relation the specification does not define.
6. **Exact proposed interface change.** Require an exact accepted
   `LegacyRecordObserved` reference plus typed row/item selector and an independently
   reviewed transition-mapping row that binds source item identity/aliases/hash, target
   object IDs/revisions/hashes, intended mode, path registration, and migration Decision
   subject. Load each record independently and require one relation-hash equality before
   any stream/version/idempotency allocation. Add cross-source, cross-target,
   cross-Decision, and coordinated valid-record substitutions.
7. **Affected decisions/work packages.** P-004, P-032, P-034; D-G6-4 limb 2; WP6.5/
   WP6.7; W11-I02/I16/I17; tests 15/16.

### M-6 — The physical path protocol leaves an operation-time alias race

1. **Claim.** W11 enumerates static path aliases and says to resolve before a read/write,
   but it does not bind the check to the opened directory/file identity through atomic
   replacement. A junction/reparse/hardlink swap can occur after validation.
2. **Evidence.** Paths are resolved to physical targets before access at
   `design/11-portfolio-and-discovery-lifecycle.md:521-526`. `PathRegistration` stores a
   resolved identity and rejects exact/casefold/Unicode/8.3/symlink/reparse/prefix
   collisions at `:539-560`; failure behavior blocks identity mismatches at `:629-640`.
   No step requires no-follow component opens, volume/file IDs, a held parent handle,
   post-open equality, post-replace equality, or hardlink identity. Test 14 lists
   collision classes and a generic concurrent-writer case but not a reparse/junction
   swap between check and replace (`:767-768`). The live registered vault root is itself
   a junction, so “reject reparse” also needs an explicit registered-root exception and
   target identity.
3. **Concrete failure scenario.** After the projector validates
   `00-Meta/ARS/Discovery/`, an actor with parent-directory write access replaces an
   intermediate directory with a junction to `00-Meta/Discovery/` before the atomic
   file replace. The final write reaches the legacy authority path even though the
   pre-check and registry were disjoint. A hardlink alias can create the same file-level
   collision without a reparse point.
4. **Impact.** The successor projector can become a physical writer of legacy authority,
   defeating P-021 and the central partial-cutover guarantee.
5. **Required disposition.** **Fix now.** Implementation details may vary, but the
   security property and acceptance test must be normative here.
6. **Exact proposed interface change.** Require operation-time traversal anchored to the
   registered root's accepted physical target; no-follow opens for each unregistered
   component; volume serial/file ID equality; rejection of unregistered reparse points
   and file-ID/hardlink aliases; a held verified parent handle/lock through temporary
   creation and atomic replace; and post-replace identity verification before success.
   Add registered-root-junction positive coverage plus symlink/junction/reparse swap,
   hardlink alias, parent replacement, case/Unicode/8.3 alias, and concurrent writer
   negatives.
7. **Affected decisions/work packages.** P-021, P-032, P-034; D-G6-4; WP6.5/WP6.6/
   WP6.7; W11-I14/I18/I20; tests 14, 17, and 18.

## 6. Minor findings and editorial corrections

### m-1 — Paper Claim is not N/A

1. **Claim.** Paper Claim is marked `N/A` even though W11 changes claim-governance
   records and consumer predicates.
2. **Evidence.** W11 defines a portfolio Claim schema and authority boundary
   (`design/11-portfolio-and-discovery-lifecycle.md:193`), a `claim_supported_by`
   relation (`:220-221`), W11-I21 (`:737`), and an authority-compensation consumer test
   (`:778-779`), but marks Paper Claim `N/A` at `:707`. Accepted W4 treats prospective
   claim governance as touching the Paper Claim lane even when it changes no claim
   (`design/04-agent-roles-and-model-routing.md:558-562`).
3. **Concrete failure scenario.** A future WP6.6 `AssuranceRequirement` copies W11's
   `N/A`, omits the W5 Claim consumer predicate, and tests only object shape; an
   accepted-looking portfolio Claim then reaches a downstream consumer without the
   required W5 claim Decision.
4. **Impact.** The stated lane disposition contradicts W11-I21 and encourages an
   incomplete future assurance requirement, although the intended guard is otherwise
   present.
5. **Required disposition.** **Fix now as a local classification correction.**
6. **Exact proposed text change.** Replace `Paper Claim | N/A` with
   `Paper Claim | Required — governance/consumer boundary`; retain that W11 creates,
   reviews, promotes, or changes no actual paper-facing claim.
7. **Affected decisions/work packages.** P-005/P-032; W11-I21; test 20; future WP6.6
   assurance requirement.

### m-2 — Design entry criterion 2 is not literally satisfied

1. **Claim.** W11's new live evidence is not listed in the evidence register required by
   design entry criterion 2.
2. **Evidence.** `design/README.md:5-12` requires evidence inputs to be listed in the
   evidence register. W11 says the criterion is satisfied and lists sources locally at
   `design/11-portfolio-and-discovery-lifecycle.md:84-107`, but the designated
   `01-current-system-evidence.md` ends with its 2026-06-27 evidence limitations at
   `:332-338` and contains neither the 2026-07-16 TDA-scale package nor the 2026-07-18
   backlog observation.
3. **Concrete failure scenario.** A later reviewer follows the repository evidence
   register rather than W11's local table and cannot discover the mutable backlog
   observation's date/hash/authority class or the package manifest's planning-only
   status.
4. **Impact.** Source discovery and currency are fragmented across the spec and register.
   The evidence itself was accessible and matched, so this is traceability rather than
   fabricated evidence.
5. **Required disposition.** **Fix now as a documentation correction.**
6. **Exact proposed text change.** Add a dated evidence-register addendum with source
   authority, exact paths, hashes, mutability, and limitations, or amend the README
   criterion explicitly to permit a specification-local evidence register.
7. **Affected decisions/work packages.** `design/README.md` entry criterion 2; W11
   section 2.2; WP6.5 review provenance.

## 7. Design-entry-criteria audit

| README criterion | Disposition | Evidence / required change |
|---|---|---|
| 1. Governing decisions accepted or assumptions explicit | Pass | P-004/P-005/P-021/P-022/P-026/P-032/P-034/P-036 and W11-A1 are explicit at W11 `:60-82`; D-G6-4 remains correctly open |
| 2. Evidence inputs listed in evidence register | **Amend** | Direct table exists at W11 `:84-107`, but new live sources are absent from `01-current-system-evidence.md`; m-2 |
| 3. Boundaries and consumers identified | Pass | W11 `:109-120` gives W1/W2/W4/W5/W9/W10/Vault/external boundaries and consumers |
| 4. Independent review owner for R2/R3 logic | Pass for assignment; outcome does not accept | W11 `:11-17` requires a fresh I1 reviewer; this review used a distinct session/context and did not inherit the author conclusions |
| 5. Acceptance tests stated before implementation | **Partially pass** | 20 tests are listed at W11 `:740-784`, but C-1/C-2/M-1/M-4/M-5 leave several without an independent expected universe or schema field to assert |

## 8. Complete decision and owner-authority audit

| Decision/gate | Review disposition |
|---|---|
| P-004 / P-021 | **Keep decisions; amend W11.** Exclusive ownership/non-shared paths are correct, but C-2/M-5/M-6 prevent the draft from proving them at transition/cutover time. |
| P-005 / P-022 | **Keep.** Promotion is Stephen-locked and this review is context-distinct. No RuleEvaluation/model/Manager substitution was found. |
| P-026 | **Keep.** The commit is specification-only and performed no legacy/successor mutation. |
| P-032 | **Keep decision; rework interface.** Canonical portfolio/Discovery integration remains the right direction, but C-1/C-2 and the Major identity/authority gaps block acceptance. |
| P-034 | **Keep decision; rework cutover proof.** Per-item transition and final one-way cutover are appropriate; exact inventory and relation oracles are missing. |
| P-036 | **Keep and do not broaden.** It approves only the earlier WP6 plan revision; it does not approve W11 or any new manifest/implementation/migration. |
| D-G6-4 limb 1 | **Remain open.** Current W11 revision is `rework_required`; Stephen should not be asked to accept it. |
| D-G6-4 limb 2 | **Remain open and hard-stopped.** No first batch can be approved until the per-item relation and whole-path inventory contracts are accepted. |
| W11-A1 | **Defer / default omit.** A combined view is not needed to close the core lifecycle. Reconsider only after the physical path resolver and consumer-deny tests pass. |

No owner-approved decision is reversed by this report. The required changes implement
the existing P-004/P-005/P-021/P-022/P-032/P-034 authority boundaries rather than
superseding them.

## 9. Complete invariant -> enforcement -> test disposition

| Invariant | Review disposition | Finding / reason |
|---|---|---|
| W11-I01 | Pass at design level | Closed, state-free immutable object intent is explicit |
| W11-I02 | **Blocked** | M-1/M-5: aggregate and transition relations lack exact stored identities |
| W11-I03 | Pass at design level | Direct/multi-hop required-edge acyclicity and atomic rejection are explicit |
| W11-I04 | **Blocked** | M-1/M-2: no Assay instance relation and rubric not frozen at request |
| W11-I05 | Pass at design level | Assay/Spike outputs are evidence only; Stephen Decision is non-compensable |
| W11-I06 | Pass at design level | PASS/FAIL/PARTIAL and kill/unknown truth conditions are closed |
| W11-I07 | Pass at design level | Exact actor/Candidate/revision/gate/evidence/option/grant requirements are explicit |
| W11-I08 | Pass at design level | PROMOTE batch excludes Dispatch/pre-registration/result/claim effects |
| W11-I09 | **Fail** | C-1: accepted expected dossier set is not a defined record |
| W11-I10 | **Fail** | C-1/M-3: exact expected universe undefined and sources not rehashed |
| W11-I11 | Pass at design level | W2 isolated staging, complete write set, tail/version checks, and atomic batch are explicit |
| W11-I12 | **Partial** | Observation/judgment split is sound; M-4 leaves ingestion authority/interface row undefined |
| W11-I13 | Pass at design level | Projection/combined-view consumer deny rules are explicit |
| W11-I14 | **Blocked** | M-6: static alias checks do not bind operation-time physical identity |
| W11-I15 | **Partial** | Ingestion-only effect is sound; M-4 leaves exact ingester authority row undefined |
| W11-I16 | **Fail** | M-5/C-2: item relation and complete path membership are not independently closed |
| W11-I17 | Pass at design level | Per-item command explicitly performs no legacy-path write |
| W11-I18 | **Fail** | C-2/M-6: complete inventory and operation-time path proof absent |
| W11-I19 | Pass at design level | Reverse cutover state is explicitly invalid |
| W11-I20 | **Partial** | Deterministic authority-neutral rebuild is stated; M-6 applies to physical publication |
| W11-I21 | **Partial** | Consumer predicate/test exists, but m-1 incorrectly marks its assurance lane N/A |
| W11-I22 | Pass at design level | Unknown major schema/event and broken hash/ref stop authoritative replay |

## 10. Complete pre-implementation test-catalogue disposition

| Test | Disposition | Reason |
|---:|---|---|
| 1 | **Blocked** | M-1/M-4: no closed instance/interface inventory for “every” schema/command/event |
| 2 | Pass as a required materialization pattern | One-field type/value/enum/pattern/additional-property mutations are appropriate |
| 3 | **Blocked** | C-1/M-4: interface catalogue is not a dossier oracle and the interface universe is not literal |
| 4 | **Blocked** | M-1/M-2: aggregate identities and request-time rubric binding absent |
| 5 | **Blocked** | M-1/M-5: schemas lack the stored relations needed to reject all foreign-valid substitutions |
| 6 | Pass at design level | Live legacy numeric rule independently matches W11; `decision` remains recommendation-only |
| 7 | Pass at design level | Every success/failure/kill/unknown seam is specified |
| 8 | Pass at design level | Option-specific and non-Stephen negatives are explicit |
| 9 | **Blocked** | C-1/M-3: no accepted literal dossier expected set; source bytes not observed |
| 10 | Pass at design level | Failure injection and zero-publication assertions map to the W2 transaction boundary |
| 11 | **Partial** | Idempotency semantics are sound, but M-4 leaves the full mutating-command universe open |
| 12 | **Partial** | Scout judgment/direct-write negatives are sound; M-4 leaves exact ingestion authority incomplete |
| 13 | **Partial** | Annotation lifecycle negatives are sound; M-4/M-6 leave authority/physical-write seams incomplete |
| 14 | **Blocked** | M-6: add registered-root junction, reparse swap, parent replacement, and hardlink/file-ID attacks |
| 15 | **Blocked** | M-5: no accepted source-item-target relation to mutate |
| 16 | Partial | No legacy-path write/`dual_owned` is clear; exact item membership depends on M-5/C-2 fixes |
| 17 | Pass at design level | Deletion/rebuild/projector-version behavior is explicit |
| 18 | **Blocked** | C-2/M-6: exact inventory and operation-time physical cutover proof absent |
| 19 | Pass at design level | Genesis/snapshot/unknown-schema replay follows accepted W2 semantics |
| 20 | Pass with m-1 amendment | Consumer non-compensation is specified; Paper Claim lane must be marked touched |

## 11. Cross-spec consistency matrix

| Invariant / identity | Owning source | W11 enforcement claim | Review result |
|---|---|---|---|
| One immutable record class per semantic role | W2 `:108-125`, `:127-189` | W11 object/artefact/Decision split `:146-178` | Mostly coherent; M-1 leaves Assay/Spike aggregate identities undefined |
| Decision != RuleEvaluation | W2 `:795-817`; P-005/P-022 | W11 `:34-40`, `:358-385`; I05/I07 | **Pass.** PromotionDecision is human-locked and non-compensable |
| Acceptance bar independent of producer | W5 `:161-171`, `:291-320` | Assay rubric `:294-316`; dossier expected source `:456-466` | **Fail.** M-2 and C-1 |
| Exact expected-set closure | WP6 master `:253-255`; W5 oracle rule | W11 `:391-477`; I09/I10 | **Fail.** C-1/M-3 |
| Atomic publication | W2 `:282-305`, `:559-569` | W11 `:454-482`; I11 | **Pass at plan level** after expected/source validation is repaired |
| Observation != adoption | W2 `:905-935`; P-032/P-034 | W11 `:139-140`, `:581-607` | **Partial.** M-5 omits the exact observed-record relation |
| One active owner; no shared path | P-004/P-021; W1 `:430-458` | W11 `:521-645`; I14/I16-I20 | **Fail at cutover proof.** C-2/M-5/M-6 |
| Profile capability != command authority | W4 `:184-200`, `:449-456` | W11 role additions `:509-519` | **Partial.** M-4 omits exact command/subject allocation |
| Portfolio Claim != W5 claim authority | W1 `:119-133`; W5 `:502-551` | W11 `:193`, `:220-221`; I21 | Mechanism passes; m-1 lane classification must be amended |
| Specification != implementation/migration authority | P-026/P-036; WP6 master `:279-288` | W11 `:9-17`, `:53-56`, `:805-830` | **Pass.** No hidden authorization found |

## 12. Research-assurance lane disposition

| Lane | W11 disposition | Review disposition |
|---|---|---|
| Output / Provenance | Required — primary | **Keep, but currently blocked.** C-1/C-2/M-3/M-5/M-6 prevent the promised exact prospective provenance gates from being enforceable. |
| Topology | N/A | Keep. W11 defines no topology; future domain rubric/Spike must carry its own accepted pack. |
| Stochastic / Null Model | N/A | Keep. W11 defines no null/RNG/p-value rule; a later SpikePlan must reference the governing design. |
| Statistical / Panel | N/A | Keep. No estimator/eligibility/variance/multiplicity rule is defined. |
| Representation | N/A | Keep. W11 stores representation refs only and asserts no adequacy. |
| Paper Claim | N/A | **Amend to Required — governance/consumer boundary.** W11 defines Claim references and a non-compensation predicate/test even though it creates no actual claim; m-1. |

Prospective Output/Provenance must require exact immutable identities, independent
expected sources accepted before observation, operation-time root/path identity,
complete observed byte rehashing, no overwrite/atomic publication, deterministic
rebuild, consumer deny lists, and exact downstream relation tests. Retrospective result
date suffixes, seeds, B/L, caches, and result-vault entries remain genuinely N/A here.

## 13. Failure behavior and practicality

The rejection/Partial behavior is generally fail-closed and should be preserved:
schema/relation/authority failures emit no lifecycle events; unknown required Spike
evidence forces PARTIAL; model-only promotion fails; dossier validation failure publishes
zero final objects/scopes/projections; projection deletion does not change authority; and
reverse cutover is invalid (`design/11-portfolio-and-discovery-lifecycle.md:672-692`).

The smallest practical control should vary by workload:

| Work class | Proportionate control |
|---|---|
| Scout observation / Candidate registration | R0/R1 closed schema, source/hash/dedup/collision checks, exact scoped grant, no viability or authority fields |
| Assay / Spike evidence | Frozen request/plan relation, domain-pack requirements, exact artefact/RuleEvaluation identity, bounded independent review; no dossier-scale bureaucracy |
| Promotion | Exact Stephen Decision/grant and one atomic Candidate batch; current W11 design is proportionate |
| Dossier admission | Full independently accepted exact-set oracle, byte re-observation, relationship validation, staging, and atomic publication; high overhead is justified because it creates many canonical objects/scopes |
| Per-item transition | One accepted observation-to-target mapping row and one migration Decision per item/batch; avoid reparsing mutable prose inside the command |
| Whole-path cutover | Full final inventory, writer revocation, physical identity/race tests, and Stephen Decision; justified because recovery is deliberately one-way |
| Generated views | One projector identity, source position/hash, byte-deterministic rebuild; no scientific review |
| Combined view | Omit by default. Add only if demonstrated human value exceeds the extra path/consumer-deny surface. |

No hidden implementation or migration authorization was found. The heavy controls are
concentrated at irreversible admission/ownership/cutover boundaries and are broadly
proportionate; the revision should not push them onto reversible Scout or projection
work.

## 14. Required revision plan

### Immediate specification corrections

1. Define and freeze the independent `DossierExpectedSet` record and derive command
   expectations from it (C-1).
2. Define the accepted exact `LegacyPortfolioInventory` and final-observation comparison
   for whole-path cutover (C-2).
3. Define Assay/Spike aggregate identities and bind every request/artefact/event/Decision
   to the exact instance (M-1).
4. Bind an accepted rubric to `RequestAssay` before evidence collection (M-2).
5. Re-observe every source dependency, not only components (M-3).
6. Replace the partial command table with one literal complete interface/authority
   catalogue, including all five later commands (M-4).
7. Bind per-item transition to an accepted observed-record/source-item-target relation
   (M-5).
8. Specify handle/file-identity-bound Windows path resolution and race tests (M-6).
9. Mark Paper Claim touched for governance and update the evidence register (m-1/m-2).

### Owner decisions

- Do not present D-G6-4 limb 1 until the revised exact commit has a fresh independent
  review with no open Critical/Major findings.
- Keep D-G6-4 limb 2 open. Its future batch must use the repaired transition relation;
  it cannot define that relation ad hoc.
- Defer or omit W11-A1 combined view until the core path resolver and consumer-deny
  contract passes.

### Later-work dependencies

- Strict schema and expected-catalogue materialization remains a separate reviewed and
  Stephen-accepted pre-implementation task. It instantiates W11; it must not invent
  missing W11 identities or authority.
- WP6.6 planning/implementation remains downstream of accepted W11 and WP6.1.
- WP6.7 and W9 remain downstream of the exact transition/cutover contracts, T1.28
  closeout gates, and separately accepted migration batches.

## 15. Residual risks after required revision

- The future expected catalogues/schemas may still be produced from runtime registries;
  implementation review must reconstruct expected and observed sides separately and
  run coordinated-pair mutations.
- Windows filesystem behavior varies by volume and permissions. The acceptance corpus
  must record which symlink/junction/hardlink tests ran versus were unavailable; an
  unavailable required physical-exclusivity test is Partial, not pass.
- Live legacy prose remains mutable. Every later admission/transition must bind a fresh
  exact observation without treating this review's matching 2026-07-18 hash as frozen
  authority.
- W9/W10 specifications do not yet exist. W11 may define portfolio-specific contracts,
  but later generic migration/template work must not silently narrow them or introduce
  TDL paths into the reusable core.
- Passing schema/contract tests will prove the materialized interface, not scientific
  adequacy of future Assay rubrics, Spike designs, results, or claims.

## 16. Validation, hard stops, and change log

### 16.1 Contract gates

Both required commands ran from exact reviewed commit
`70074d42eade8460808e4d1d29348b7806eff2d0` with
`PYTHONDONTWRITEBYTECODE=1`, pytest cache/coverage disabled or externally routed, and no
repository runner artefacts before or after:

| Command | Exit | Outcome |
|---|---:|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` | 0 | `Contract framework: all gates passed against 101 contract(s).` |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | 0 | `Contract framework: all gates passed against 101 contract(s).` |

No broad pytest command, live provider call, compute, projection, ingestion, ownership
transition, migration, result, eligibility, or claim action was run. The contract gates
validate the current repository contract framework; they do not close the W11 design
findings above.

### 16.2 Hard-stop confirmation

This review does **not** accept W11, exercise Stephen's authority, approve D-G6-4,
approve a first transition batch, authorize WP6.6/WP6.7, materialize schemas, create
`.research-system/` state, write any vault path, ingest Scout/annotation evidence,
admit the TDA-scale package, transition ownership, cut over a path, run a live model,
change eligibility, accept a result, or promote a claim.

### 16.3 Files changed

- `docs/plans/agentic-research-system/reviews/adversarial-wp6-5-w11-spec-review-2026-07-18.md`
  — this review report only.

Reviewed W11, README, decision register, owner specifications, live backlog, and live
package files changed: **none**.
