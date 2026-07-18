# W11 — Portfolio and Discovery Lifecycle Specification

**Date:** 2026-07-18
**Status:** `review_pending`; revision 0.2 reconciles the binding
`rework_required` review and requires fresh independent review; specification only
**Specification version:** 0.2
**Design authority:** accepted W1/W2/W4/W5 specifications; P-004, P-005,
P-021, P-022, P-026, P-032, P-034, and P-036; WP6 master revision
`fe5f1d40bc8f05f061317c677b5891cea0711249` approved under P-036
**Implementation authority:** None. This document creates no runtime schema,
command handler, event, object, projection, import, or ownership transition.
**Primary author:** WP6.5 W11 specification Worker
**Independent review owner:** a fresh adversarial reviewer appointed by the Gate 6
Manager, in a distinct session and independently compiled context from the primary
author; the reviewer must establish at least P-022 grade I1.
**Reconciliation owner:** Gate 6 Manager
**Acceptance authority:** Stephen under D-G6-4, after independent review and
reconciliation
**Prior review:** exact subject `70074d42eade8460808e4d1d29348b7806eff2d0`;
independent report commit `21ebc46b0c415286e8c525106e8bb9fde92d38c3`;
verdict `rework_required` (2 Critical, 6 Major, 2 Minor). Revision 0.2
dispositions every finding but does not accept itself; a fresh reviewer must inspect
the new exact commit.

---

## 1. Decision summary and hard boundary

W11 gives the W1 portfolio catalogue strict prospective records and gives the
Candidate → Assay → Spike portion of the master-plan lifecycle explicit commands,
events, authority, failure behaviour, paths, and pre-implementation tests. It also
specifies the dossier-admission boundary that WP6.6 may later implement.

The binding choices are:

1. Programme, paper, hypothesis, Candidate, method, dataset, portfolio Claim, and
   dependency-edge definitions are immutable W2 objects with `obj_` identities.
   Lifecycle state is an event projection, never an editable object field or vault
   status string.
2. `AssayScorecard` and `SpikeVerdict` are evidence objects and mechanical
   `RuleEvaluation` inputs. Neither is a `Decision` and neither may advance a
   Candidate by itself.
3. `PromotionDecision` is a typed W2 Decision with closed options
   `PROMOTE | PARK | KILL`. Every resolution is human-locked to Stephen. `PROMOTE`
   authorizes only the named next design step; it never dispatches work, changes a
   pre-registration, accepts a result, or promotes a claim.
4. `AdmitResearchDossier` validates a candidate `ResearchDossierManifest` against the
   independently authored, reviewed and accepted literal `DossierExpectedSet`, then
   independently resolves exact component and source bytes before atomically publishing
   any portfolio object or `ScopeDefinition` reference. Any missing, extra, duplicate,
   stale, incompatible, foreign or tampered member produces zero publication.
5. Canonical ARS events and objects are authority. Vault pages are either legacy
   authority, successor-generated projections, human annotation inputs, or an
   optional non-authoritative combined view. These roles never share a mutable writer
   path.
6. Legacy-to-successor change is explicit per item and one way. The living legacy
   backlog remains legacy-written until a separate whole-path cutover after every
   item using that path has left `legacy_owned`.

This is WP6.5 only. It does **not** implement W11, perform WP6.6 admission, create
`.research-system/` state, write `00-Meta/ARS/Discovery/`, ingest an annotation or
Scout batch, read a legacy status into authority, transition an item, cut over a path,
begin WP6.6/WP6.7, or mutate any frozen result, evidence, decision, or claim.

## 2. Entry criteria, evidence, boundaries, and consumers

### 2.1 Accepted decisions and assumptions

| Authority | W11 disposition |
|---|---|
| P-004 | Preserved: `legacy_owned`, `successor_owned`, and `closed_reference` are the only ownership modes; `dual_owned` is schema-invalid. |
| P-005 | Preserved and made stricter for Discovery: every PROMOTE/PARK/KILL resolution is Stephen-attributed; pre-registration, R3, decision reversal, and claim promotion retain their separate human gates. |
| P-021 | Preserved: successor projections never share a mutable path with unmodified legacy tooling. |
| P-022 | Preserved: review independence is evidence-derived; this draft does not count its own adversarial check as independent review. |
| P-026 | Preserved: specification may proceed in parallel, but current legacy research is not imported, normalized, written, or promoted. |
| P-032 | Implemented prospectively: ARS owns successor portfolio/Discovery state; the vault becomes a projection/annotation surface only for successor objects. |
| P-034 | Preserved: consolidation is transition-gated, not indefinite dual-running or bulk import. |
| P-036 | Preserved: the exact reviewed WP6 launch-basis constraints remain authoritative; this later W11 draft receives its own review and owner gate. |

One bounded assumption is explicit:

- **W11-A1 — optional combined-view path.** If D-G6-4 elects to create a combined
  human view, the proposed path is `00-Meta/ARS/Discovery-combined/`. It remains
  unregistered and absent unless accepted. A different accepted third path may replace
  it without changing the two non-negotiable authority/projection paths or the
  annotation inbox. Omitting the combined view is conforming.

The first ownership-transition batch is not assumed. Its item membership and exact
manifest remain an open D-G6-4 owner decision.

### 2.2 Direct evidence inputs

The design entry criterion is satisfied against direct sources, not summaries:

| Evidence | Use in W11 |
|---|---|
| Repository evidence register [`../01-current-system-evidence.md`](../01-current-system-evidence.md) §§1, 2.2, 3.1–3.2, 4.2–4.4, 4.8–4.9, 4.12, 5.1, 5.6, 7, and dated W11 addendum §8 | Source precedence; strengths to preserve; mutable-state, single-slot, root, self-approval, pending-contract, and missing-eval failure classes; exact 2026-07-18 live paths, bytes, hashes, mutability, and limitations. |
| `00-master-transition-plan.md` §§5, 6.1, 6.5, 8, and 9–11 | Evidence-before-status; immutable lineage; portfolio fields/lifecycle; initial Portfolio Steward role; migration, pilot, rollback, and human authority. |
| Accepted W1 §§5.1, 6–10, 14, and 18 | Portfolio ownership, canonical/projection split, trust boundaries, compatibility ownership, path collision, and W9/W10 constraints. |
| Accepted W2 §§5–10, 13–16, 18, 20–23, 25, and 28 | Record terminology, `obj_` IDs, immutable objects, command/event envelopes, atomic batches, `ScopeDefinition`, artefact manifests, Decision/RuleEvaluation separation, replay, import, and ownership modes. |
| Accepted W4 §§7–8, 14–15, 19–20, and 23–25 | Role-profile fields, independence, human actions, default-deny permissions, failure behaviour, and role additions. |
| Accepted W5 §§6–8, 10–19, 25–27 | Assurance requirements, lane completeness, contract separation, independent review, Partial, result/claim separation, and claim-promotion authority. |
| Roadmap W9/W10 owner sections | Selective import, rollback, deprecation, reusable project workflow, and non-TDL review gate. |
| `contracts/discovery-harness/assay-scorecard.yaml` and `spike-pre-registration.yaml` | Existing typed legacy rubric and user-approved Spike seam to preserve through explicit mapping, never implicit import. |
| R5 review dated 2026-07-17 | Zero-finding approval of exact WP6 plan revision; path/writer exclusivity and still-open W11/D-G6-4 gates. |
| TDA-scale v1.0.0 programme and package manifest | Concrete evidence of the missing dossier interface: 17 immutable components plus separately hashed sources, planning-only status, and Gate A fail-closed boundary. |
| Living `00-Meta/Discovery/_backlog.md` inspected 2026-07-18 | Current legacy authority shape and active/superseded/decision-pending items; inspection SHA-256 `37eec1ba6bb7929d95d5349ada2f75d93636c8356aad5dffc6a59981fc0269e7`. The hash is a dated observation, not a frozen authority identity. |

The TDA-scale manifest inspected for this draft has SHA-256
`e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf`;
its master component has SHA-256
`277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea`.
Those identities describe evidence inspected by the specification. They are not an
admission decision, and WP6.6 must use a deliberately re-versioned package.

### 2.3 Boundaries and consumers

| Boundary | W11 rule | Consumer |
|---|---|---|
| W1 portfolio catalogue | Owns object definitions, dependency edges, promotion gates, and evidence links; never owns task execution or result acceptance. | Portfolio Steward, Research Designer, context compiler, task authoring, dashboard/projectors. |
| W2 control plane | Sole mutation and atomic publication boundary. | Future WP6.6 handlers, reducers, replay, receipts. |
| W4 routing | Profiles Scout and Portfolio Steward capabilities; grants remain action- and subject-specific. | Router and authority service. |
| W5 assurance/claims | Owns assurance and claim-candidate/promotion semantics. A W11 portfolio Claim cannot declare a result or claim accepted. | Assurance engine, claim reviewer, manuscripts. |
| W9 migration | Owns selective legacy adoption, cutover, rollback, and deprecation sequencing. | Migration authority and legacy adapter. |
| W10 template | Consumes domain-neutral schemas and workflows; no TDL path is mandatory outside the TDL vault path registry. | Project initializer and domain packs. |
| Vault | Legacy authority at the legacy path; generated reading views and human annotation inputs at disjoint successor paths. | Humans and read-only dashboards. |
| External literature services | Untrusted observations only; they cannot write canonical state or decide viability. | Scout ingestion command. |

### 2.4 Design-entry-criteria disposition

| README criterion | Revision 0.2 disposition |
|---|---|
| 1. Decisions accepted or assumptions explicit | **Satisfied for authorship.** P-004/P-005/P-021/P-022/P-026/P-032/P-034/P-036 are accepted and preserved in §2.1; W11-A1 and both D-G6-4 limbs remain explicitly open. |
| 2. Evidence inputs in the evidence register | **Satisfied.** §2.2 resolves the base audit and the exact dated W11 live evidence to tracked root register §8, including paths, byte hashes, mutability and limitations. |
| 3. Boundaries and consumers identified | **Satisfied.** §2.3 identifies W1/W2/W4/W5/W9/W10, Vault and external-service boundaries and consumers. |
| 4. Independent review owner | **Satisfied for assignment, not acceptance.** The primary author, fresh I1 reviewer, Manager reconciler and Stephen acceptance authority are distinct. The prior independent verdict was `rework_required`; revision 0.2 requires a fresh exact-commit review. |
| 5. Acceptance tests before implementation | **Satisfied for specification.** §11 maps 22 invariants to enforcement and §12 freezes 20 test families with complete expected authorities and stored relations; no test or schema is materialized here. |

## 3. Canonical terminology and record family

### 3.1 Terms and rejected collapses

- **Candidate** is a registered proposal for evaluation. It is not yet a hypothesis,
  Task, paper, accepted method, or dispatch authority.
- **Assay** is a bounded evidence-and-score operation against an accepted versioned
  rubric. `AssayScorecard` is its typed output.
- **Spike** is a separately approved, time-bounded feasibility probe under a locked
  `SpikePlan`. `SpikeVerdict` reports PASS/FAIL/PARTIAL against that plan.
- **PromotionDecision** is the human authority record selecting PROMOTE/PARK/KILL at
  a named gate. The scorecard/verdict may recommend; they cannot resolve.
- **Portfolio Claim** is the portfolio catalogue record that points to W5
  `ClaimCandidate`/claim-decision authority. It is not a second claim system and cannot
  promote or strengthen claim text.
- **Admission** is atomic registration of a complete hashed dossier. It is not a bulk
  migration, status inference, or dispatch.
- **Observation** records what a legacy or external source said. **Adoption** is a
  separately authorized successor transition. These terms are never synonyms.

Rejected alternatives are: a generic editable `status`; an `Assay` field that directly
sets PROMOTE; treating PASS as promotion; treating a vault file as both projection and
annotation input; and calling two simultaneously writable copies “single ownership.”

### 3.2 Strict common object envelope

Every W11 object schema is closed (`additionalProperties: false`) and contains exactly
the following common fields plus its kind-specific block:

| Field | Type and rule |
|---|---|
| `schema_id` | Exact registered `ars://portfolio/...` string. |
| `schema_version` | Exact semantic version supported by the reader; initial design value `1.0.0`. |
| `record_id` | `obj_` + lowercase hyphenated UUIDv7. |
| `record_revision` | Integer ≥1. |
| `supersedes_revision` | `null` for revision 1; otherwise exactly `record_revision - 1`. |
| `project_id` | Existing `prj_` ID. |
| `portfolio_kind` | Closed enum named by the schema. |
| `aliases` | Array of `{namespace, value, scope_id}`; aliases never identify authority. |
| `created_at` | UTC RFC 3339 timestamp. |
| `created_by_actor_id` | Existing `act_` ID. |
| `source_refs` | Non-empty array of typed IDs plus revision/hash or external locator/hash. |
| `content_hash` | Lowercase 64-hex SHA-256 over W2 P0 canonical JSON excluding this field. |

Lifecycle status, current evidence status, generated paths, reviewer conclusions, and
mutable “next” prose are forbidden in immutable definitions. Projectors derive them
from accepted events and referenced evidence.

The envelope above applies to portfolio definitions, dependency edges, accepted Assay
rubrics, path registrations, `DossierExpectedSet`, `LegacyPortfolioInventory`, and
`LegacyTransitionMapping` authorities. Evidence payloads are a different W2 record class:
`AssayScorecard`, `SpikePlan`, `SpikeVerdict`, `ScoutObservationBatch`,
`DiscoveryAnnotation`, `ResearchDossierManifest`, and `LegacyRecordObserved` are
immutable external artefacts
registered by `art_` manifests. Each artefact manifest carries the complete W2 §16
identity, production, root/path, byte-hash, inputs, validation, authority, no-overwrite,
and consumer fields; its payload carries the exact closed `ars://portfolio/...` schema
named below. An `art_` artefact does not acquire an `obj_` identity, and registration
does not accept or apply it. `PromotionDecision` remains a W2 `dec_` record.

### 3.3 Portfolio object schemas

All references below require ID plus expected revision and content hash unless the
referenced kind is an immutable one-ID/one-hash artefact.

| Schema / kind | Required kind-specific fields | Authority boundary |
|---|---|---|
| `ars://portfolio/programme` / `programme` | `title`, `research_questions[]`, `intended_contributions[]`, `falsification_value`, `negative_result_value`, `resource_envelope_ref`, `promotion_policy_ref`, `dependency_edge_refs[]` | Organizes work; cannot accept evidence or complete Tasks. |
| `ars://portfolio/paper` / `paper` | `programme_ref`, `research_question`, `intended_contribution`, `hypothesis_refs[]`, `method_refs[]`, `dataset_refs[]`, `claim_refs[]`, `scope_definition_refs[]`, `manuscript_root_ref` | Manuscript locator is not claim authority. |
| `ars://portfolio/hypothesis` / `hypothesis` | `statement`, `estimand_or_object`, `target_population_or_domain`, `falsifiers[]`, `negative_result_value`, `comparator_refs[]`, `paper_refs[]` | A hypothesis does not imply a pre-registration or result. |
| `ars://portfolio/candidate` / `candidate` | `candidate_kind`, `title`, `research_question`, `intended_contribution`, `novelty_claim`, `closest_alternative_refs[]`, `proposed_subject_refs[]`, `data_requirements[]`, `representation_requirements[]`, `estimand_or_object`, `falsification_value`, `negative_result_value`, `feasibility_evidence_refs[]`, `resource_envelope_ref`, `blocking_evidence_refs[]`, `source_observation_refs[]` | Registration creates only the Candidate lifecycle. |
| `ars://portfolio/method` / `method` | `name`, `version_or_revision`, `definition_ref`, `input_types[]`, `output_types[]`, `assumptions[]`, `named_baseline_refs[]`, `limitations[]`, `implementation_artifact_refs[]` | Registration does not establish correctness, novelty, or suitability. |
| `ars://portfolio/dataset` / `dataset` | `name`, `vintage`, `population`, `access_class`, `root_id`, `manifest_ref`, `representation_refs[]`, `permitted_consumers[]`, `prohibited_uses[]` | Contains no restricted rows, credentials, or inferred access grant. |
| `ars://portfolio/claim` / `claim` | `claim_candidate_ref`, `claim_decision_ref_or_null`, `exact_text_hash_or_null`, `result_decision_refs[]`, `paper_consumers[]`, `restriction_refs[]` | This is a portfolio Claim record; W5 records remain the sole claim/claim-promotion authority. |

`candidate_kind` is the closed enum
`hypothesis | method | dataset | paper | programme_extension | other_registered`.
The `other_registered` value requires a registered extension schema and cannot carry
untyped free-form lifecycle semantics.

### 3.4 Dependency edges and relational invariants

`ars://portfolio/dependency-edge` is a first-class immutable `obj_` record with exact
fields `edge_type`, `from_ref`, `to_ref`, `satisfaction_predicate_ref_or_null`,
`required`, `rationale`, `evidence_refs`, and `effective_scope_ref`.

The closed initial `edge_type` set is:

```text
contains | addresses | proposes | tests | uses_method | uses_dataset
supports | contradicts | informs | targets_paper | depends_on | blocks
supersedes | claim_supported_by
```

The following relationships are binding:

- `contains` originates at a programme or paper and cannot target itself.
- `addresses` binds a paper/Candidate to a particular hypothesis revision.
- `uses_method` and `uses_dataset` bind exact revisions; a same-kind foreign but valid
  record is not substitutable.
- `claim_supported_by` targets accepted W5 result/decision evidence, never an Assay,
  Spike, narrative status, or generated view.
- `supersedes` is acyclic and one-directional.
- the subgraph of required `depends_on | blocks` edges is acyclic; cycles fail the
  registration/admission command rather than being projected as “blocked forever.”
- satisfaction is evaluated from the named predicate and exact referenced state. An
  edge cannot self-report its own satisfaction.

### 3.5 Assay and Spike aggregate identities

W11 adds two three-letter W2 first-class identifiers:

| Aggregate | Canonical ID and stream | Creation and immutable relation |
|---|---|---|
| Assay | `asy_<lowercase UUIDv7>`; the canonical Assay stream ID is exactly the `assay_id` | Proposed once by `RequestAssay`. `AssayRequested` freezes one Candidate ID/revision/hash, one already accepted rubric ID/revision/hash, its required-axis-set hash, one accepted evidence-scope identity/hash, and the creating command. |
| Spike | `spk_<lowercase UUIDv7>`; the canonical Spike stream ID is exactly the `spike_id` | Proposed once by `RegisterSpikePlan`. `SpikePlanned` freezes one Candidate ID/revision/hash, one exact `SpikePlan` artefact/hash, the originating Assay ID/scorecard, and the assay-to-spike Decision. |

The IDs are aggregate identities, not aliases and not `art_` identities. Every Assay
event, scorecard, Partial artefact, review, `RuleEvaluation`, promotion proposal, and
promotion Decision carries the same exact `assay_id`. Every Spike event, plan,
execution-approval Decision, attempt, verdict, review, `RuleEvaluation`, promotion
proposal, and promotion Decision carries the same exact `spike_id`. Candidate-side
link events repeat the aggregate ID and exact aggregate stream version; reducers load
both streams and require the stored relation hash to agree.

A superseding scorecard or verdict remains in the same aggregate and names the exact
predecessor artefact/hash. A new revisit creates a new `asy_` or `spk_` aggregate even
when Candidate and rubric/plan content are otherwise identical. Reusing an aggregate
ID, attaching a valid artefact from another aggregate, reducing a Spike by `art_` plan
identity in one implementation and `att_` identity in another, or changing the frozen
Candidate/rubric/plan relation is invalid.

## 4. Discovery lifecycles, commands, and events

### 4.1 Candidate projection

```text
registered
  -> assay_pending -> assayed -> assay_decision_pending
       -> parked | killed | spike_planning_authorized
  -> assay_pending -> assay_partial -> assay_pending | assay_decision_pending
  -> spike_planning_authorized -> spike_authorized
       -> spike_running -> spike_verdict_recorded
       -> spike_decision_pending -> parked | killed | preregistration_authorized
  -> superseded
```

`parked` may return to `assay_pending` or `spike_planning_authorized` only after its
explicit revisit predicate is met and Stephen resolves a new Decision. Resuming an
already-authorized unchanged Spike attempt is a separate W8 operational transition and
does not reopen the Candidate gate. `killed` never reopens in
place; materially new evidence creates a new Candidate with lineage to the killed one.
`preregistration_authorized` authorizes drafting/review of a pre-registration only.

Assay instances project independently as:

```text
requested -> evidence_collecting -> scored -> reviewed
requested/evidence_collecting -> partial | cancelled
partial/scored/reviewed -> superseded
```

Spike instances project independently as:

```text
planned -> approval_pending -> authorized -> running -> verdict_recorded
planned/approval_pending/authorized/running -> cancelled
running -> partial
partial/verdict_recorded -> superseded
```

A Candidate state never stands in for the Assay or Spike state. Paired operational
events may project that an authorized Spike started or reported, but no such event
advances the Candidate past a promotion gate without the Decision batch below.

### 4.2 Command/event catalogue

Each command uses the complete W2 envelope, strict versioned payload schema, exact
stream versions/write set, one project writer, and W2 validation order. A command schema
ID is exactly `ars://portfolio/command/<kebab-command>@1.0.0`; each row has a distinct
`ars://portfolio/receipt/<kebab-command>@1.0.0`. Event schema IDs are exactly
`ars://portfolio/event/<kebab-past-tense-event>@1.0.0`. These identities are reserved
prospectively here; this task does not materialize them.

Every grant stores the literal `authority_subject_kind`, the exact subject IDs,
revisions and hashes shown below, `project_id`, risk ceiling, effective interval and
revocation state. A project-only, path-only, role-only, alias-only or wildcard subject
never satisfies a row. The listed profile is capability eligibility only; the separate
exact-subject grant is always required. Unlisted commands, subjects, roots and write
classes default deny under W4.

| Command / discriminant | Allowed W4 profile; exact authority subject | Principal preconditions | Ordered events; complete authoritative write set |
|---|---|---|---|
| `RegisterCandidate` | Scout or Portfolio Steward; `candidate_registration` = proposed Candidate ID/hash + exact source-observation-set hash | Registered observations; identity/alias collision-free | `CandidateRegistered`; Candidate stream/object plus project portfolio index |
| `SupersedeDiscoveryRecord` / `candidate` | Portfolio Steward; `candidate_supersession` = predecessor Candidate ID/revision/hash + already registered replacement Candidate ID/revision/hash + accepted lineage/reason hash | Replacement exists; predecessor current; no ownership/Decision inference | `CandidateSuperseded`; predecessor Candidate stream and project portfolio index |
| `RequestAssay` | Portfolio Steward; `assay_request` = Candidate ID/revision/hash + proposed `assay_id` + accepted rubric ID/revision/hash + evidence-scope hash | Candidate `registered` or exact revisit Decision; rubric and scope accepted before request | `AssayRequested`, `AssayEvidenceCollectionOpened`, `CandidateAssayRequested`; first two facts on new Assay stream, then Candidate stream |
| `RecordAssayScore` | Implementer with Assay-producer capability; `assay_evidence` = `assay_id` + frozen relation hash + scorecard artefact/hash | Exact complete frozen rubric/axis closure and Candidate relation | `AssayScored`, `CandidateAssayLinked`; Assay then Candidate streams and artefact-use relation |
| `RecordAssayPartial` | Implementer with Assay-producer capability; same `assay_evidence` subject kind with Partial artefact/hash | Completed and unmet evidence explicit; frozen relation equal | `AssayPartialRecorded`, `CandidateAssayPartialLinked`; Assay then Candidate streams and artefact-use relation |
| `RecordAssayReview` | Independent verifier; `assay_review` = `assay_id` + frozen relation hash + scorecard/Partial hash + review ID/subject hash | Exact subject inspected; required independence grade established | `ReviewVerdictRecorded`, `AssayReviewed`; Review then Assay streams |
| `CancelDiscoveryEvaluation` / `assay` | Portfolio Steward; `assay_cancellation` = `assay_id` + frozen relation hash + exact reason/evidence hash | Assay not terminal; cancellation cannot change Candidate gate | `AssayCancelled`, `CandidateAssayCancellationLinked`; Assay then Candidate streams |
| `SupersedeDiscoveryRecord` / `assay` | Portfolio Steward; `assay_supersession` = predecessor `assay_id`/relation hash + replacement `assay_id`/relation hash | Replacement Assay exists under a valid revisit; both relate to exact Candidate | `AssaySuperseded`, `CandidateAssaySupersessionLinked`; predecessor Assay then Candidate streams |
| `ProposePromotionDecision` | Portfolio Steward; `discovery_promotion_proposal` = Candidate ID/revision/hash + gate + exact `assay_id`/`spike_id` + evidence hash + proposed `dec_id` | No unresolved proposal at the same Candidate gate | `DecisionProposed`, `CandidatePromotionRequested`; Decision then Candidate streams |
| `ResolveDecision` / `discovery_promotion` | Stephen-attributed human grant; `discovery_promotion_decision` = `dec_id` + Candidate ID/revision/hash + gate + exact aggregate/evidence hashes | Exact proposal and option-specific predicates | `DecisionResolved`, `CandidatePromotionApplied`; Decision then Candidate streams in one batch |
| `RegisterSpikePlan` | Portfolio Steward; `spike_plan_registration` = Candidate ID/revision/hash + proposed `spike_id` + plan artefact/hash + assay-to-spike Decision | Candidate `spike_planning_authorized`; immutable plan relation complete | `SpikePlanned`, `SpikeApprovalRequested`, `CandidateSpikePlanLinked`; first two facts on new Spike stream, then Candidate stream |
| `ResolveDecision` / `spike_execution_authority` | Stephen-attributed human grant; `spike_execution_decision` = `dec_id` + `spike_id` + Candidate and exact plan hashes | Required route/resource/assurance refs present | `DecisionResolved`, `SpikeAuthorized`, `CandidateSpikeAuthorized`; Decision, Spike, then Candidate streams |
| `StartSpike` | Operator/auditor; `spike_execution` = `spike_id` + plan/hash + authorization Decision + lease/attempt/resource identities | Exact authorized plan and live lease | `SpikeStarted`, `CandidateSpikeStarted`; Spike, attempt relation, then Candidate streams |
| `RecordSpikeVerdict` | Implementer with Spike-producer capability; `spike_evidence` = `spike_id` + plan/hash + attempt + verdict artefact/hash | Exact evidence closure and verdict truth table | `SpikeVerdictRecorded`, `CandidateSpikeVerdictLinked`; Spike then Candidate streams and artefact-use relation |
| `CancelDiscoveryEvaluation` / `spike` | Operator/auditor; `spike_cancellation` = `spike_id` + plan/relation hash + active attempt/lease + exact reason/evidence hash | Spike not terminal; stop/lease evidence current; cancellation cannot resolve promotion | `SpikeCancelled`, `CandidateSpikeCancellationLinked`; Spike, attempt/lease relation, then Candidate streams |
| `SupersedeDiscoveryRecord` / `spike` | Portfolio Steward; `spike_supersession` = predecessor `spike_id`/relation hash + replacement `spike_id`/relation hash | Replacement Spike exists under a valid revisit and exact Candidate/Decision lineage | `SpikeSuperseded`, `CandidateSpikeSupersessionLinked`; predecessor Spike then Candidate streams |
| `ResolveDecision` / `dossier_expected_set_acceptance` | Stephen-attributed human grant after I1 review; `dossier_expected_set` = expected-set ID/revision/hash + repository path/Git blob/file SHA-256 + dossier/profile scope | Literal set accepted before candidate manifest production/observation; reviewer independent of author/runtime producer | `DecisionResolved`, `DossierExpectedSetAccepted`; Decision and expected-set authority streams |
| `AdmitResearchDossier` | Operator/auditor under an R2 admission grant; `dossier_admission` = expected-set ID/revision/hash + manifest artefact/byte hash + dossier logical ID/revision | Accepted expected set/profile; all §5 closure checks | `ResearchDossierAdmitted`, deterministic `PortfolioObjectRegistered` and `ScopeDefinitionRegistered`; dossier, every created object/edge/scope and project index in one batch |
| `IngestScoutObservationBatch` | Scout; `scout_batch_ingestion` = batch artefact/hash + project ID + exact explicit Candidate-blueprint multiset hash | Source, dedup and collision rules pass; no judgment fields | `ScoutObservationIngested`, then zero or more `CandidateRegistered` using the same registration validator/event schema; observation batch and explicit Candidate streams |
| `IngestDiscoveryAnnotation` | Portfolio Steward; `annotation_ingestion` = annotation artefact/bytes/hash + exact target ID/revision/hash | Attributed human inbox writer; current target; dedup/idempotency | `DiscoveryAnnotationIngested`; annotation evidence stream only |
| `RecordLegacyPortfolioObservation` | Independent verifier or importer; `legacy_path_observation` = path-registration ID/revision/hash + opened physical file identity + observed byte hash + parser/reproducer identity | Handle-bound read of exact registered path; no adoption | `LegacyPortfolioPathObserved`; observation artefact/stream only |
| `ResolveDecision` / `legacy_inventory_acceptance` | Stephen-attributed human grant after independent reproduction/review; `legacy_portfolio_inventory` = inventory ID/revision/hash + final source-byte hash + membership hash + parser/reproducer identities | Literal item set complete; unknown/unparseable rows absent; independent reproduction agrees | `DecisionResolved`, `LegacyPortfolioInventoryAccepted`; Decision and inventory-authority streams |
| `ResolveDecision` / `migration_authority` accepting a transition mapping | Stephen-attributed human grant; `legacy_transition_mapping` = proposed `dec_id` + mapping ID/revision/hash + inventory-item row hash + target-set hash | Independent source-item-target review; collision scan current; mapping names the same proposed Decision subject | `DecisionResolved`, `LegacyTransitionMappingAccepted`; Decision and mapping-authority streams in one batch |
| `TransitionPortfolioOwnership` | Operator/auditor; `portfolio_ownership_transition` = accepted mapping ID/revision/hash + observed-record ID/hash + item ID + migration Decision | Exact relation equality; one current owner; versions/tail current | `PortfolioItemOwnershipTransitioned`; item ownership stream, exact target streams and project ownership index; never the legacy path |
| `CutOverDiscoveryPath` | Operator/auditor under Stephen-attributed cutover grant; `legacy_path_cutover` = path-registration ID/revision/hash + accepted inventory ID/revision/hash + final-observation artefact/hash + transition-event-set hash + cutover Decision | Every inventory row closed, writer revocation effective, handle-bound final bytes equal, projections rebuild | `LegacyDiscoveryPathCutoverCompleted`, `PathRegistrationRevised`; path and project registry streams in one batch |

No generic `StatusChanged` or `DiscoveryUpdated` event is allowed. Rejection writes no
lifecycle event. A report, annotation, score, verdict, review, or process exit cannot
substitute for the command in the table. `CandidateRegistered` deliberately has two
producers: `RegisterCandidate` and `IngestScoutObservationBatch`; both invoke one exact
registration validator, event schema, collision rule and reducer. Within W11, every
other W11-specific event has one literal command/discriminant row. Shared W2
`DecisionResolved` and `ReviewVerdictRecorded` retain their owning W2 producer but must
also equal the exact W11 discriminant/subject relation shown here; no implicit W11
producer is allowed.

### 4.3 `AssayScorecard`

`ars://portfolio/assay-rubric` is a closed immutable `obj_` definition with exact
rubric ID/revision/hash, domain-pack refs, ordered axis definitions, each axis's closed
kind/value type/bounds or allowed set, required-axis-set hash, evaluation order,
recommendation predicates, forbidden axes, Partial rules, source authority, reviewer,
and accepting authority. A rubric cannot accept its own scorecard.

Before evidence collection, the rubric and an `AssayEvidenceScope` are independently
reviewed and accepted. `RequestAssay` stores on `AssayRequested` the exact rubric
ID/revision/hash, required-axis-set hash, evidence-scope ID/revision/hash, Candidate
ID/revision/hash, `assay_id`, author/reviewer/acceptor identities, and one canonical
`assay_relation_hash` over those complete fields. The rubric author or scorecard
producer cannot be its sole reviewer/acceptor, and acceptance after any Assay evidence
was observed is invalid for that Assay. `evidence_collecting` begins only after this
relation is recorded by `AssayRequested` and the later-ordered
`AssayEvidenceCollectionOpened` fact commits in the same atomic request batch. Every
later Assay command independently loads the stored relation and requires literal
equality; command values cannot select, swap or narrow the bar.

The prospective `ars://portfolio/assay-scorecard` artefact payload schema is closed and
requires a W2 `art_` manifest plus:

- exact Candidate ID/revision/hash;
- exact `assay_id`, creating `AssayRequested` event/hash, and stored
  `assay_relation_hash`;
- accepted `AssayRubric` ID/revision/hash;
- accepted `AssayEvidenceScope` ID/revision/hash and required-axis-set hash frozen by
  `RequestAssay`;
- ordered `axis_results`, each with exact `axis_id`, closed `axis_kind` of
  `gate | integer_score | registered_measure`, typed `value`, accepted bounds or
  allowed set, rationale, evidence refs, unmet-condition codes, and validator ID/hash;
- exact required-axis-set hash and observed-axis-set hash;
- `mechanical_recommendation: PROMOTE | PARK | KILL | UNABLE_TO_SCORE`;
- `rule_evaluation_ref`, limitations, and prohibited inferences;
- producer actor/profile/context and review requirements.

`AssayScored` is accepted only when the observed axis IDs are a one-to-one exact match
to the accepted rubric: no missing, extra, duplicate, aliased, reordered-as-different,
or wrong-typed axis. Bounds and decision predicates are equality-checked, not copied
from producer prose. An incomplete Assay uses `AssayPartialRecorded` and cannot emit a
PROMOTE recommendation. A late rubric acceptance, post-request rubric/scope/axis-set
swap, scorecard from another Assay for the same Candidate, or coordinated command and
scorecard mutation rejects against the stored request relation.

The closed `ars://portfolio/assay-partial` artefact repeats the exact `assay_id`,
Candidate/rubric/evidence-scope refs and stored request relation hash, then lists
completed axes/evidence, unmet axes/evidence, stable reason codes, limitations and
revisit requirements. It forbids a PROMOTE recommendation and cannot be attached to a
different Assay during revisit or supersession.

The current TDL legacy rubric maps explicitly to one future accepted rubric revision:
Axis 1 is the `topology_earns_its_keep` Boolean gate; Axes 2 and 3 are integers in
`[0,3]`; legacy PROMOTE requires Axis 1 pass, Axis 2 + Axis 3 ≥4, and neither numeric
axis equal to zero. The mapped legacy rubric continues to forbid `programme_fit` as a
scored axis. The legacy `decision` field imports only as a recommendation plus
source evidence. It never imports as a resolved `PromotionDecision`. Domain-neutral
W11 does not hard-code topology into every future rubric.

### 4.4 `SpikePlan` and `SpikeVerdict`

The `ars://portfolio/spike-plan` artefact payload requires exact `spike_id`, Candidate,
originating `assay_id`, and source-scorecard refs,
the assay-to-spike PromotionDecision, required approving authority, time/resource box,
question, scope, inputs,
method/object, baselines, null/comparator where applicable, success predicates,
failure predicates, kill conditions, Partial rules, planned contracts, outputs,
prohibited work, and outcome-to-next-step mapping. Starting a Spike against a different
plan revision is rejected. Approval state is projected from a later Stephen-attributed
Spike approval Decision/event; it is not a mutable field inside the plan artefact.

The `ars://portfolio/spike-verdict` artefact payload is closed and requires:

| Field | Rule |
|---|---|
| `spike_id`, `candidate_ref`, `originating_assay_ref`, `spike_plan_ref`, `attempt_ref` | Exact IDs/revisions/hashes; all five relationships must equal the stored `SpikePlanned` relation. |
| `verdict` | `PASS | FAIL | PARTIAL`. |
| `success_predicates[]` / `failure_predicates[]` | Every accepted-plan predicate with `passed | failed | unable_to_evaluate` and evidence refs. |
| `kill_conditions[]` | Every accepted-plan kill condition with `triggered | not_triggered | unable_to_evaluate`, evidence refs, and consequence. |
| `artefact_refs[]`, `validation_refs[]` | Exact immutable identities/hashes; producer assertions are not validators. |
| `completed_scope`, `unmet_scope`, `limitations` | Non-empty and typed where PARTIAL or FAIL. |
| `mechanical_recommendation` | `PROMOTE | PARK | KILL | NONE`; evidence only. |
| `prohibited_inferences[]` | Must include no dispatch/result/claim authority. |

PASS requires all required success predicates passed, no failure predicate satisfied,
and every kill condition `not_triggered`. FAIL requires a named failure predicate or
triggered kill condition. Any required `unable_to_evaluate`, missing evidence, or
incomplete scope forces PARTIAL. Neither PASS nor FAIL deletes artefacts; both are
valid evidence outcomes.

### 4.5 `PromotionDecision`

`PromotionDecision` is a strict subtype of the accepted W2 Decision schema, not a new
parallel authority. It requires:

- `decision_kind: discovery_promotion`;
- exact Candidate ID/revision/hash and `gate: assay_to_spike | spike_to_preregistration`;
- exact `assay_id` or `spike_id`, its creating relation hash, and exact AssayScorecard
  or SpikeVerdict plus validation/review refs;
- selected option `PROMOTE | PARK | KILL`;
- option-specific next Candidate state;
- rationale, considered evidence, conditions, effective scope/time, and revisit
  triggers;
- Stephen's actor ID and a valid exact-subject authority grant.

PROMOTE must name exactly one next state (`spike_planning_authorized` or
`preregistration_authorized`). PARK requires at least one objective revisit predicate
and owner; KILL requires at least one satisfied kill/failure condition and prohibits
in-place reopen. The `DecisionResolved` and `CandidatePromotionApplied` events are one
atomic batch. Cross-Candidate, stale-revision, foreign evidence, wrong-gate, model-only,
or non-Stephen substitutions reject before publication.

At `assay_to_spike`, PROMOTE additionally requires a complete Assay whose accepted
rubric permits PROMOTE; Stephen may still select PARK or KILL. An Assay Partial can
only return for more evidence or PARK through a Decision. At
`spike_to_preregistration`, PROMOTE requires `SpikeVerdict=PASS`; PARTIAL can only PARK
pending its named revisit evidence, and a FAIL with a triggered kill condition can only
KILL. A FAIL without a kill condition may PARK or KILL according to the accepted plan.
No human option may compensate for missing required evidence or a triggered hard gate.

## 5. Dossier admission interface

### 5.1 Independently accepted `DossierExpectedSet` authority

`ars://portfolio/dossier-expected-set` is a closed immutable `obj_` authority record,
not the dossier producer's manifest and not the generic W11 interface catalogue. Each
accepted instance applies to exactly one dossier logical ID/revision, package version,
admission-profile ID/revision/hash and effective project/scope. It must literally list
every expected member; globs, discovery rules, count-only claims, optional unlisted
members and producer-populated defaults are forbidden.

The record contains the common object envelope plus:

- `expected_set_id`, revision/hash, dossier/profile scope and effective interval;
- schema ID/version; exact repository path, Git commit/blob, file byte length and
  SHA-256 of the serialized expected set;
- author and producing context; independent reviewer evidence establishing no
  manifest/component/source/runtime production relationship; Stephen as accepting
  authority; exact acceptance Decision/event and times;
- `component_count`, `source_count`, `object_count`, `scope_count`, `edge_count` and
  `relationship_count`, plus an exact P0 canonical multiset hash for each family;
- one complete literal array for each row family below and one overall
  `expected_set_closure_hash` over the complete rows and profile scope;
- an explicit `authored_before_candidate_observation` proof: the accepted expected-set
  commit/blob and acceptance event predate creation or first observation of the
  candidate `ResearchDossierManifest`. Expected component/source identities come from
  the separately accepted dossier/profile requirement and independently observed
  source authorities, never from that candidate manifest or its runtime enumerator.

The six literal row schemas are:

```text
component row:
  component_key, component_kind, schema_id, schema_version, root_id,
  relative_path_or_object_ref, size_bytes, sha256, required, dependency_keys,
  permitted_consumers, confidentiality_class

source row:
  source_key, source_kind, schema_or_media_type, root_id, relative_path_or_locator,
  size_bytes, sha256, source_authority_class, required, permitted_consumers,
  confidentiality_class, independent_resolution_policy_id/hash

object row:
  object_key, portfolio_kind, schema_id, schema_version, proposed_record_id,
  proposed_revision, blueprint_hash, expected_content_hash, source_keys,
  permitted_consumers

ScopeDefinition row:
  scope_key, scope_schema_id, scope_schema_version, proposed_scope_id,
  proposed_revision, blueprint_hash, expected_content_hash, governing_object_keys,
  permitted_consumers

dependency-edge row:
  edge_key, edge_type, proposed_edge_id, proposed_revision, from_key/revision/hash,
  to_key/revision/hash, required, satisfaction_predicate_ref_or_null,
  effective_scope_key, expected_content_hash

relationship row:
  relationship_key, relationship_kind, ordered_member_keys_with_revisions_hashes,
  relation_schema_id/version, relation_hash
```

Object, scope, edge and relationship rows bind semantic members, not merely blueprint
file names. A valid foreign member with the same kind is unequal. The expected set's
author may not derive any row from a candidate manifest, candidate command, runtime
registry or implementation enumerator. Its independent reviewer reconstructs the six
literal multisets from the separately accepted dossier/profile requirement and checks
repository bytes/blob/hash before Stephen resolves
`dossier_expected_set_acceptance`. The `DossierExpectedSetAccepted` event binds the
complete record identity and closure; changing any row requires a new revision, review
and acceptance before any new candidate observation.

This temporal and producer separation is non-compensable. Agreement among a manifest,
command and runtime registry cannot establish completeness when the accepted expected
set is absent, later-authored, producer-related or byte-mismatched.

### 5.2 Strict dossier manifest

The future `ars://portfolio/research-dossier-manifest` artefact payload schema is closed
and contains:

- dossier logical ID, revision, manifest schema ID/version, package version, purpose,
  author, created time, and governing decisions;
- `component_count` and a unique ordered-by-key `components[]` set;
- `source_dependency_count` and a unique ordered-by-key `source_dependencies[]` set;
- unique ordered-by-key `object_blueprints[]`, `scope_definition_blueprints[]`,
  `dependency_edges[]`, and `relationships[]` sets. Each member repeats the complete
  corresponding §5.1 expected row and adds its candidate blueprint path/byte hash;
- exact `object_count`, `scope_count`, `edge_count`, and `relationship_count`;
- accepted admission-profile ID/revision/hash;
- legacy/source ownership declarations and prohibited adoption claims;
- canonical `closure_hash` and no self-hash field.

Each component row is exactly:

```text
component_key, component_kind, schema_id, schema_version,
root_id, relative_path_or_object_ref, size_bytes, sha256,
required, dependency_keys, permitted_consumers, confidentiality_class
```

Source dependencies use the same identity fields plus source-authority class. Mutable
routing records such as the living backlog cannot masquerade as immutable components;
they may be exact observed sources with explicit non-adoption semantics.

The closure hash is:

```text
sha256(P0-canonical-json({
  manifest_schema_id,
  manifest_schema_version,
  package_version,
  admission_profile_hash,
  components: sorted complete component rows,
  source_dependencies: sorted complete source rows,
  objects: sorted complete object rows plus blueprint byte hashes,
  scope_definitions: sorted complete scope rows plus blueprint byte hashes,
  dependency_edges: sorted complete edge rows plus blueprint byte hashes,
  relationships: sorted complete relationship rows
}))
```

The manifest file's own bytes are hashed externally and supplied to the command. The
manifest never hashes itself.

### 5.3 `AdmitResearchDossier` command shape

The command uses the W2 envelope and a strict payload with:

- exact manifest artefact/path, byte length, SHA-256, schema ID/version, and closure
  hash;
- exact accepted `DossierExpectedSet` ID/revision/content hash, repository path, Git
  blob, serialized-file SHA-256, acceptance Decision/event, and accepted
  admission-profile identity;
- proposed portfolio object IDs/revisions/hashes and ScopeDefinition IDs/revisions/
  hashes;
- complete affected stream write set with expected versions;
- expected project global position/tail hash;
- actor, authority grant, idempotency key, reason, and governing Decision refs;
- explicit `ownership_effect: successor_owned_new_objects_only`.

The command supplies no authoritative expected counts, key-set hashes, member rows or
relationship rows. The handler derives all expectations solely from the independently
accepted `DossierExpectedSet`; any duplicate command convenience fields must be absent,
not compared to another producer-controlled copy.

It cannot accept a payload-supplied “validated” flag, infer acceptance from a vault
status, adopt a legacy item, resolve a PromotionDecision, issue a Dispatch, or promote
a claim.

### 5.4 Exact closure and atomic publication algorithm

The future handler must perform these steps in order:

1. Validate the envelope/payload and independently resolve the accepted admission
   profile and `DossierExpectedSet` by exact ID/revision/content hash, repository
   path/schema/version/Git blob/serialized-file SHA-256 and acceptance event. Verify
   author/reviewer/runtime-producer separation and that acceptance predates candidate
   observation. Never call a candidate-side enumerator to populate the expected side.
2. Read manifest bytes from the registered root, verify size/hash/schema, and reject
   traversal, case-fold, Unicode-normalization, symlink, or reparse-point escapes.
3. Compare the expected set to the candidate manifest one-to-one across the complete
   component, source, object, ScopeDefinition, edge and relationship row multisets.
   Missing, extra, duplicate, aliased, reordered-as-different, substituted or
   count-only matches reject.
4. Resolve every component **and every source dependency** independently from its
   registered root or registered external resolver. Read bytes from the verified
   handle; recompute physical identity, byte length, SHA-256, schema/media type and
   source-authority class. Compare every observed row one-to-one to both its accepted
   expected row and candidate-manifest row. The manifest producer's paths, cached
   observations, resolved bytes and validator conclusions are never observed truth.
5. Independently materialize candidate object, ScopeDefinition and edge payloads in
   inert staging and recompute their blueprint/content hashes. Validate every complete
   relationship row, exact revision and hash. A valid foreign member cannot replace
   the member named by a relation.
6. Recompute expected-set and candidate-manifest closures independently. The accepted
   expected-set identity remains fixed while manifest, command and runtime sides are
   mutated; compare the candidate closure with the manifest and accepted expected set.
7. Verify no legacy observation is being upgraded and every new object is
   `successor_owned`; any existing identity/revision/alias/path collision rejects.
8. Build all objects, dependency edges, and ScopeDefinitions in isolated staging;
   validate the complete write set, stream versions, global tail, authority, and
   idempotency.
9. Publish one atomic batch containing `ResearchDossierAdmitted`, one
   `PortfolioObjectRegistered` per object/edge, and one `ScopeDefinitionRegistered` per
   scope in deterministic manifest order; then return one receipt.

Any ordinary rejection leaves the event tail, every stream, final object path,
ScopeDefinition path, and projection unchanged. A crash may leave only W2-classified
inert staging/orphan candidates; replay and projectors ignore them, and recovery never
promotes them. No partial dossier is visible or retryable under a new idempotency key.

The inspected TDA-scale v1.0.0 package is evidence for this interface, not an admissible
payload. WP6.6 must create a re-versioned package with strict object/ScopeDefinition
blueprints, recomputed hashes, accepted expected closure, and its own authority gate.

The mandatory coordinated-omission attack removes or substitutes the same member from
the candidate manifest, command conveniences and runtime registry, then recomputes all
candidate-side hashes. Admission must still fail against the unchanged accepted
`DossierExpectedSet`. Separate attacks cover each source dependency being missing,
inaccessible, tampered, aliased, path-escaped or valid-but-foreign.

## 6. Scout ingestion and W4 role additions

### 6.1 Scout boundary

Scout gathers neutral literature/source observations. The closed
`ars://portfolio/scout-observation-batch` payload is an immutable `art_` artefact with
source query/version/time, exact returned identifiers,
normalized dedup keys, raw-source refs/hashes, matching facts, omissions/errors, and no
viability judgment.

`IngestScoutObservationBatch` independently verifies the batch and dedup rules, records
`ScoutObservationIngested`, and may atomically emit `CandidateRegistered` only for
explicit Candidate rows. An inbox file, OpenAlex/arXiv response, normalized title, model
summary, or Scout recommendation has no lifecycle effect by itself. Existing legacy
Scout inboxes remain legacy observations until separately ingested after a migration
authority decision; W11 performs none.

Scout must not Assay, rank by viability, resolve PROMOTE/PARK/KILL, authorize a Spike,
change dependencies, ingest human annotations, write a generated projection, or claim
source authority it did not verify.

### 6.2 W4 profile additions

| Role | Purpose and allowed actions | Required context/capability | Prohibited actions |
|---|---|---|---|
| Scout | Gather, deduplicate, and submit attributed external observations; propose Candidate registration through a scoped command. | Source-retrieval provenance, dedup, security/privacy, bounded network read, Output/Provenance capability. | Assay/Spike judgment; promotion; result/claim acceptance; migration; writing canonical stores or any Discovery projection path. |
| Portfolio Steward | Maintain programme object/dependency proposals; request Assays; register approved Spike plans; prepare dossier/transition proposals; reconcile projections and collisions. | Portfolio/dependency reasoning, W2/W5 authority literacy, path registry, provenance, Partial/escalation. | Resolve PromotionDecisions; exercise P-005 authority; accept results/claims; self-review its own R2/R3 evidence; direct event/path writes; implicit legacy adoption. |

Each future profile records every W4 §7 field: ID/version/hash, owner/review state,
purposes, capability/risk ceiling, allowed commands, tool/root/network/write classes,
context profile, lanes, incompatible prior relationships, eval currency, and stop/
Partial/handoff duties. Profile capability never replaces an authority grant.

The Scout profile's complete W11 command allowlist is `RegisterCandidate` and
`IngestScoutObservationBatch`. The Portfolio Steward profile's complete W11 command
allowlist is `RegisterCandidate`, `SupersedeDiscoveryRecord`, `RequestAssay`,
`CancelDiscoveryEvaluation` with `assay`, `ProposePromotionDecision`,
`RegisterSpikePlan`, and `IngestDiscoveryAnnotation`. Its supersession permission is
limited to the `candidate | assay | spike` discriminants and exact predecessor/
replacement relations in §4.2. Preparing a dossier, expected set, inventory, mapping
or transition proposal is artefact production, not permission to execute its
acceptance/admission/migration command. The other §4.2 rows use the existing W4
profiles and exact grants stated there; every unlisted command remains denied.

## 7. Vault path, writer, annotation, and ownership contract

### 7.1 Non-negotiable physical paths and writers

Paths are relative to the registered TDL vault root, then resolved to exact physical
targets before any read or write.

| Path | Role / authority | Allowed mutable writer set before cutover | Forbidden uses |
|---|---|---|---|
| `00-Meta/Discovery/_backlog.md` | Living legacy authority | Existing legacy Discovery workflow and attributed human editors only | ARS projector/ingester writes; successor authority input without explicit observation/adoption; generated view before whole-path cutover. |
| `00-Meta/ARS/Discovery/` | Successor-generated namespace; projection only | One registered ARS Discovery projector service/version | Human/legacy writes; annotation input; command/admission/decision authority. |
| `00-Meta/ARS/Discovery-annotations/` | Human annotation inbox; non-authoritative until typed ingestion | Attributed humans only | Projector/legacy/Scout writes; direct lifecycle effect; combined-view generation. |
| `00-Meta/ARS/Discovery-combined/` if W11-A1 is accepted | Optional combined read-only view | One registered combined-view projector | Input to Scout, annotation ingestion, dossier admission, ownership transition, Decision, or any authority predicate. |

There is no shared mutable writer path and no writer wildcard. Writer identity includes
actor/service ID, implementation/projector version, authority grant, root ID, and
effective interval. A hook or marker is defence in depth, not writer authority.

### 7.2 `PathRegistration`

`ars://portfolio/path-registration` is a strict immutable record with:

- path ID/revision/hash, project/vault root ID, normalized relative path and resolved
  physical identity: canonical target, reparse chain, volume serial number, stable
  directory/file ID, link count where applicable, and case/Unicode/8.3 aliases;
- role enum `legacy_authority | successor_projection | human_annotation_inbox |
  combined_read_only_view`;
- `ownership_mode`: `legacy_owned` for the active legacy authority path and `null` for
  projection/annotation/combined roles, plus allowed writer identities/write classes,
  permitted readers, and prohibited consumers;
- projector/ingester IDs and versions where applicable;
- collision policy (always `fail_closed`), source event position/hash fields for views,
  retention/deletion policy, and rebuild procedure identity;
- cutover state `legacy_active | cutover_pending | successor_active | retired |
  not_applicable` and governing Decision/event refs; annotation and combined roles use
  `not_applicable`.

Registration rejects exact, case-folded, Unicode-normalized, 8.3-name, symlink,
reparse-point, or resolved-prefix collisions that would allow two writer sets to reach
one physical target. A directory registration cannot authorize an unregistered nested
authority file.

### 7.3 Operation-time Windows handle and file-identity protocol

Static registration is necessary but never sufficient. Every authoritative read,
projection publication, annotation ingestion, transition observation and cutover
operation uses this fail-closed protocol at operation time:

1. Open the registered root and bind the operation to its accepted physical target,
   volume serial number and directory file ID. A root junction is allowed only when
   its reparse tag, substitute/print target, target volume/file ID and complete reparse
   chain are explicit in the accepted registration. The currently observed TDL vault
   junction is therefore a positive fixture, not a blanket permission to follow links.
2. Traverse each remaining component with no-follow/open-reparse-point semantics and
   inspect it by handle. Unregistered symlinks, junctions, mount points or other
   reparse points fail. Each component's parent/child file IDs, normalized name and
   resolved target must equal the accepted chain; string prefix checks are not proof.
3. Compare every opened volume/file ID against all registered authority and writer
   paths. Reject a hardlink or file-ID alias, unexpected link count, case/Unicode/8.3
   alias or physical-prefix collision even when path strings differ.
4. For reads, hash bytes read from the verified open handle to final byte, then
   re-query the same handle and parent chain. Size, file ID, last-write/change identity
   and parent identities must be unchanged before the observation can succeed.
5. For writes, hold the verified parent handle and the registered path-operation lock
   from precondition check through temporary creation, flush/close, atomic replacement
   and post-replace verification. Temporary creation and replacement must be
   handle-relative to that parent (or provide an independently reviewed equivalent
   that proves the same identity property). Re-open the final file through the held
   parent and verify volume/file ID, bytes/hash, link count and unchanged parent chain
   before returning success.
6. Recheck authority grant, writer registry revision, path-registration revision and
   source event position immediately before the commit point. A parent/reparse/file
   identity change, concurrent writer, sharing violation, inaccessible required link
   enumeration, or platform adapter unable to prove a required identity returns
   `path_identity_unproven`/Partial and publishes no success event.

Required race injection swaps a symlink, junction/reparse target, hardlink target or
parent directory after each of: initial resolution, component open, temporary write,
pre-replace and post-replace. Every swap rejects without touching another registered
path. Positive coverage must exercise the explicitly registered root junction; negative
coverage must exercise an unregistered nested junction, hardlink alias and parent swap.
Unavailable required Windows identity/race coverage is Partial, never pass.

### 7.4 Human annotation ingestion

Each annotation file in `00-Meta/ARS/Discovery-annotations/` has the closed
`ars://portfolio/discovery-annotation` frontmatter payload schema: annotation ID, author
actor ID, created time, target object ID/revision/hash, annotation kind, proposed action
or `comment_only`, body hash, source refs, and supersession ref. Filename and prose are
aliases; after accepted ingestion the exact file is registered as an `art_` artefact,
and its body bytes/hash are evidence.

`IngestDiscoveryAnnotation` verifies path role, writer attribution, schema, exact bytes,
target identity, dedup/idempotency, and staleness before recording
`DiscoveryAnnotationIngested`. Ingestion preserves the human proposal but does not apply
it. Any object revision, dependency change, promotion, claim action, or migration still
requires its separately authorized command. Projectors never “round-trip” edits from
generated pages.

Manual edits under `00-Meta/ARS/Discovery/` or the combined path produce projection
drift diagnostics and are discarded on rebuild; they are never treated as annotations.

### 7.5 Per-item ownership transition

Observation, mapping acceptance and transition are three distinct authorities:

1. `LegacyRecordObserved` is an immutable `art_` observation produced from a
   handle-bound read. It contains observation ID/hash, exact path registration,
   physical source identity, complete-file bytes/hash, parser ID/version/hash, a typed
   source-item selector (byte range plus raw-row hash), source item ID/type/aliases,
   observed row bytes/hash, observation time and explicit non-inferences. It adopts
   nothing.
2. `ars://portfolio/legacy-transition-mapping` is a closed immutable `obj_` relation.
   Each literal mapping row binds one accepted inventory ID/revision/hash and inventory
   item-row hash, one exact `LegacyRecordObserved` ID/hash and typed selector, source
   path/bytes/item/aliases, one target-mode enum, the complete target object
   ID/revision/content-hash set, alias mapping, collision-scan ID/hash, and the exact
   `migration_authority` Decision subject. Its `transition_relation_hash` is SHA-256
   over that complete P0 canonical row. The mapping author, independent reviewer and
   Stephen-attributed acceptor are recorded; `LegacyTransitionMappingAccepted` binds
   the exact row before execution.
3. `TransitionPortfolioOwnership` references the accepted mapping ID/revision/hash and
   relation hash; it does not resubmit authoritative source/target members. The handler
   independently loads the inventory item, observation, target objects, collision scan,
   mapping, Decision and path registration, recomputes the relation, and requires one
   literal equality before allocating an idempotency outcome, stream version or event
   position.

The strict command payload therefore contains accepted mapping identity/hash, item ID,
exact current/target mode, observation ID/hash, governing migration Decision,
expected source/target stream versions, event tail and complete write set. Any
convenience copy of a source selector, alias or target is equality-checked and has no
authority. Cross-source, cross-item, cross-target, cross-Decision, or coordinated
valid-record substitution rejects even when every substituted member is individually
current and schema-valid.

Allowed active transitions are:

```text
legacy_owned -> successor_owned
legacy_owned -> closed_reference
successor_owned -> closed_reference
```

No transition targets `dual_owned`, returns to `legacy_owned`, infers acceptance, or
changes another item. On success, `PortfolioItemOwnershipTransitioned` records the
accepted mapping/relation hash, inventory/item-row hash, observation/selector/hash,
before/after owner, target identities, migration Decision subject, effective event
position, and attributed authority. The legacy file is not edited by this command.
Remaining legacy items continue to use it as authority; the transitioned item appears
only in the successor projection with an explicit legacy lineage link.

The physical legacy path remains legacy-written during a partial cutover, but its
authority is item-scoped. For a transitioned item, the exact source row/bytes recorded
by the transition become frozen lineage; any later legacy edit to that item's row is a
diagnostic observation only and cannot regain authority or update the successor object.

### 7.6 Whole-path cutover

`ars://portfolio/legacy-portfolio-inventory` is the complete, content-addressed
membership authority for one exact final legacy file. It is a closed immutable `obj_`
record containing:

- inventory ID/revision/content hash; exact path-registration ID/revision/hash;
  registered-root and opened physical volume/file identities; source byte length and
  SHA-256; and its `LegacyPortfolioPathObserved` artefact/event;
- membership-rule ID/revision/hash; parser schema and parser implementation repository
  path/Git blob/SHA-256; exact reproducer command identity; and byte-range/row-selector
  semantics;
- a complete literal one-to-one `items[]` array. Each row has stable legacy item ID and
  type, scoped aliases, typed byte selector, raw row length/hash, observed-record
  ID/hash, current owner, expected mapping identity/hash or explicit unresolved reason,
  and source ordering. Unknown or unparseable bytes are blocker rows, never omissions;
- item count, ordered item-key hash, row-multiset hash, alias-multiset hash, unresolved/
  duplicate/collision sets, parser diagnostics, and overall membership closure hash;
- producer identity; an independent reproducer identity using independently compiled
  context and an implementation/parser family not derived from the producer output;
  per-row reproducer evidence; independent reviewer; Stephen-attributed acceptance
  Decision/event; and all repository path/blob/file hashes.

The independent reproducer opens and reads the exact same source file to final byte
using §7.3, parses from those bytes rather than the producer inventory, and returns the
complete literal row multiset plus unknown-byte coverage. It must agree on file hash,
every byte-range selector, item/alias multiset and membership hash. It may not consume
the producer's item list as its expected side. A coordinated omission by two runs of
the same parser, a missing byte range, unknown heading, alias collision, overlapping
selector or uncovered non-whitespace byte blocks acceptance. The reviewer additionally
checks that the union of item selectors and explicitly classified structural bytes
covers the complete file.

The legacy backlog path can move from `legacy_active` to `successor_active` only when:

1. that exact `LegacyPortfolioInventory` has independent reproduction/review and an
   accepted content identity;
2. every literal inventory item row binds exactly one accepted transition mapping and
   `PortfolioItemOwnershipTransitioned` event to `successor_owned` or
   `closed_reference`; there are no extra transition items;
3. no unknown/unparseable/uncovered byte, unresolved/duplicate/foreign item, alias
   collision or un-ingested annotation remains;
4. legacy writers are stopped, handles drained and their grants/write authorities
   revoked; the revocation snapshot is independently observed;
5. while holding the §7.3 verified path handle/lock, an independent final observer
   reads the file to final byte, records a new `LegacyPortfolioPathObserved` artefact,
   re-runs the accepted membership rule and the independent reproducer, and proves
   exact equality to the accepted inventory's physical identity, byte length/hash,
   literal rows and membership hashes;
6. no write, rename, parent swap, reparse change or byte change occurs between that
   final observation and the atomic event commit; any change requires a new inventory,
   reproduction, review and acceptance;
7. the successor and optional combined projections rebuild successfully from canonical
   state without reading their own output;
8. collision, deletion/rebuild, operation-time path-identity and concurrent-write/race
   tests pass; and
9. Stephen resolves the exact whole-path cutover Decision naming the inventory,
   final-observation, transition-event set, revocation snapshot and target registration.

`CutOverDiscoveryPath` binds those exact identities in its payload and independently
recomputes the inventory-to-final-observation-to-transition-event bijection. It
atomically records `LegacyDiscoveryPathCutoverCompleted` and a new PathRegistration
revision. An omitted item, extra transition, same-parser coordinated omission,
post-inventory/post-observation write, stale final bytes or writer/reparse race leaves
the legacy path active and publishes nothing. Only after that event may a separately
registered projector target the legacy-named path. The transition is one way:
`successor_active -> legacy_active` is invalid. Recovery rebuilds successor projections
or stops; it does not re-enable legacy writers.

### 7.7 Collision, deletion, and rebuild behaviour

- A non-empty foreign file, wrong ownership marker, unexpected source position/hash,
  manual edit, concurrent writer, or path identity mismatch blocks the write and emits
  no canonical lifecycle event.
- Successor and combined views include source event position/hash, projector version,
  content hash, authority label, and rebuild command identity.
- Deleting either generated view changes no authority. Rebuild from canonical records
  at the same source position/projector version must be byte-identical; a different
  projector revision produces a separately identified view.
- ARS never deletes/rebuilds the legacy backlog while `legacy_active` and never writes
  the annotation inbox.
- Deleting an annotation after successful ingestion does not delete its immutable
  evidence/event. An un-ingested deletion has no lifecycle effect.
- The combined view labels each row `legacy_owned | successor_owned |
  closed_reference` and its source position. It is always excluded from authority
  resolvers and ingestion allowlists.

## 8. Prospective schema and expected-source materialization gate

W11 defines interfaces, not implementation-local schema files. WP6.6 may not start
until a separate materialization task creates and reviews strict schemas for every
object, command, event, receipt, reducer, projection, and registry named here.

The future independently authored `W11SchemaExpectedCatalogue` is proposed at
`.research-system/evals/expected/w11-portfolio-discovery-v1.json`. Before first runtime
implementation or observation, Stephen must accept its exact repository path, schema
ID/version, Git blob, and SHA-256 after independent review. The runtime implementer may
not author, review or accept its own expected source. Catalogue authorship and
acceptance must also predate runtime-registry/schema production. This catalogue is the
W11 interface oracle; it is distinct from every dossier-specific
`DossierExpectedSet` and from `LegacyPortfolioInventory`.

Its literal closed interface universe is:

```text
object/authority schemas:
  programme, paper, hypothesis, candidate, method, dataset, claim,
  dependency-edge, assay-rubric, assay-evidence-scope, path-registration,
  dossier-expected-set, legacy-portfolio-inventory, legacy-transition-mapping

aggregate/relation schemas:
  assay aggregate, spike aggregate, assay-request relation, spike-plan relation,
  dossier six-family closure relation, legacy source-item-target transition relation,
  inventory-final-observation-transition-event bijection

artefact payload schemas:
  assay-scorecard, assay-partial, spike-plan, spike-verdict,
  scout-observation-batch, discovery-annotation, research-dossier-manifest,
  legacy-record-observed

Decision discriminants:
  discovery_promotion, spike_execution_authority,
  dossier_expected_set_acceptance, legacy_inventory_acceptance,
  migration_authority (including transition-mapping acceptance),
  legacy_path_cutover

command rows:
  every literal row in §4.2, including AdmitResearchDossier,
  IngestScoutObservationBatch, IngestDiscoveryAnnotation,
  RecordLegacyPortfolioObservation, TransitionPortfolioOwnership and
  CutOverDiscoveryPath, with each ResolveDecision discriminant a separate row

event rows:
  CandidateRegistered, CandidateSuperseded, AssayRequested,
  AssayEvidenceCollectionOpened, CandidateAssayRequested, AssayScored,
  CandidateAssayLinked, AssayPartialRecorded, CandidateAssayPartialLinked,
  ReviewVerdictRecorded, AssayReviewed, AssayCancelled,
  CandidateAssayCancellationLinked, AssaySuperseded,
  CandidateAssaySupersessionLinked,
  DecisionProposed, CandidatePromotionRequested, DecisionResolved,
  CandidatePromotionApplied, SpikePlanned, SpikeApprovalRequested,
  CandidateSpikePlanLinked,
  SpikeAuthorized, CandidateSpikeAuthorized, SpikeStarted, CandidateSpikeStarted,
  SpikeVerdictRecorded, CandidateSpikeVerdictLinked, SpikeCancelled,
  CandidateSpikeCancellationLinked, SpikeSuperseded,
  CandidateSpikeSupersessionLinked, DossierExpectedSetAccepted,
  ResearchDossierAdmitted, PortfolioObjectRegistered, ScopeDefinitionRegistered,
  ScoutObservationIngested, DiscoveryAnnotationIngested,
  LegacyPortfolioPathObserved, LegacyPortfolioInventoryAccepted,
  LegacyTransitionMappingAccepted, PortfolioItemOwnershipTransitioned,
  LegacyDiscoveryPathCutoverCompleted, PathRegistrationRevised

reducers/projections:
  Candidate, Assay, Spike, Decision, expected-set authority, dossier admission,
  portfolio object/edge/scope and project index, Scout observation, annotation,
  legacy observation, inventory authority, mapping authority, item ownership,
  path registration/cutover, successor Discovery view, optional combined view
```

There is one distinct versioned receipt schema for every command/discriminant row and
one authority row copied literally from §4.2. `CandidateRegistered` alone has the two
explicit W11 producers stated there; shared W2 events retain only their explicitly
bound W2 producer and discriminant, and all W11-specific event producer sets are
closed. A later
materializer may add no unreviewed producer, command, event, reducer, projection,
receipt or authority subject and may omit none.

Each catalogue row contains:

```text
logical_key, schema_id/version/hash, command_type, authority_subject,
payload discriminant, exact preconditions, ordered events, affected streams,
complete write set, reducer, projection targets, receipt identity,
distinct positive test, distinct negative/mutation tests
```

Tests compare a one-to-one multiset of complete rows, not counts or separately derived
field sets. Coordinated mutation of the candidate catalogue and runtime registry must
still differ from the independently accepted expected identity. The reviewer resolves
every row back to this literal universe and §4.2; generating expected and observed
sides from one registry or enumerator is invalid even if hashes and row counts agree.

## 9. Failure behaviour

| Failure | Required result |
|---|---|
| Candidate/source identity collision | Reject registration; preserve both observations; no Candidate event. |
| Assay rubric/scope accepted late, swapped after request, or scorecard belongs to another `assay_id` | Reject before evidence linkage; no Assay/Candidate event. |
| Assay axis missing/extra/duplicate/wrong type or rubric stale | Reject `AssayScored` or record explicit Assay Partial; no promotion proposal inferred. |
| Spike plan, attempt, Candidate, or verdict relationship mismatch | Reject verdict; preserve artefacts as unaccepted candidates. |
| Kill condition triggered but verdict PASS/PARTIAL | Reject verdict schema/relational validation. |
| Required Spike condition unable to evaluate | PARTIAL; no PASS or promotion. |
| Promotion resolved by model/Manager or against stale/foreign evidence | Reject before Decision event. |
| PROMOTE attempts to dispatch, lock a pre-registration, accept a result, or promote a claim | Reject complete batch. |
| `DossierExpectedSet` missing, late-authored, producer-related, byte-mismatched, unaccepted, or incomplete | Reject before manifest inspection; zero publication. |
| Dossier component/source/object/scope/edge/relation missing, extra, duplicate, tampered, stale, incompatible or valid-but-foreign | Reject atomically; zero event/object/ScopeDefinition/projection publication. |
| Source dependency cannot be independently resolved and rehashed | Reject atomically; a declared closure row is not observed bytes. |
| Expected and observed dossier/catalogue values share one producer or candidate-side enumerator | Acceptance gate fails; independent expected source required. |
| Legacy prose says Success/Done/PROMOTE | Observation only; no adoption or Decision. |
| Path/writer collision or shared physical target | Reject registration/write/transition; no “last writer wins.” |
| Manual edit to generated view | Drift diagnostic; rebuild from events; never ingest. |
| Annotation targets stale revision | Reject with current identity; human must issue a new annotation. |
| Ownership transition lacks migration authority/collision scan | Reject; item remains under current owner/path. |
| Ownership source/item/target/Decision members do not equal one accepted mapping relation | Reject before allocation; item remains under current owner/path. |
| Inventory has unknown/uncovered bytes, parser/reproducer correlation, membership mismatch, stale bytes or unaccepted revision | Reject inventory/cutover; legacy path remains active. |
| Whole-path cutover has any legacy-owned/unmapped item, extra transition, active legacy writer, changed final byte or post-observation race | Reject; legacy path remains legacy authority. |
| Operation-time root/parent/reparse/hardlink/file identity cannot be proved | Reject/Partial with no authoritative success event or wrong-path write. |
| Projector deletion/corruption | Rebuild generated view; canonical state unchanged. |
| Unknown major W11 schema/event | Stop authoritative replay/projection. |

## 10. Research-assurance disposition

This is a prospective specification, not a computational result. The complete six-lane
disposition is nevertheless explicit and must be independently confirmed against the
prospective implementation relationship:

| Lane | Disposition | Rationale and prospective evidence |
|---|---|---|
| Output / Provenance | **Required — primary** | W11's material claims are exact identity/hash closure, immutable source linkage, schema/value/type enforcement, root/path/writer exclusivity, no overwrite, deterministic rebuild, expected/observed producer separation, and downstream consumer restrictions. Future schema/catalogue/path/dossier artifacts bind exact bytes and identities before implementation. |
| Topology | **N/A** | W11 defines no filtration, complex, diagram, homology, metric, or topological interpretation. A TDL Assay rubric may reference topology later through a versioned domain pack; this core spec does not judge it. |
| Stochastic / Null Model | **N/A** | W11 defines no permutation, bootstrap, RNG, p-value, Markov/null, or exchangeability claim. Spike plans carry such refs only when a later accepted domain design requires them. |
| Statistical / Panel | **N/A** | W11 fits no model and specifies no estimand formula, eligibility rule, weighting, imputation, variance, or multiplicity procedure. Dataset/hypothesis records only reference later governing designs. |
| Representation | **N/A** | W11 does not fit or transform PCA/UMAP/scalers/labels/windows. It records representation refs/hashes without asserting their scientific adequacy. |
| Paper Claim | **Required — governance/consumer boundary** | W11 defines portfolio Claim references, `claim_supported_by`, prohibited compensation, and consumer predicates. Prospective tests must prove those records cannot satisfy W5 result/claim authority. This classification authorizes no claim creation, review, wording, promotion, acceptance, manuscript action, or live claim evaluation; every later claim still uses W5 and Stephen's P-005 decision. |

For Output/Provenance, retrospective result-file items such as numerical date suffixes,
seeds, cache parameters, or result-vault filing are not applicable to this specification.
Their absence does not weaken the prospective requirements above.

## 11. Invariant → enforcement point → acceptance-test mapping

| ID | Invariant | Enforcement point | Required test/attack |
|---|---|---|---|
| W11-I01 | Object definitions are immutable and state-free. | Closed object schemas and reducers. | Reject lifecycle/status/path fields and in-place revision mutation. |
| W11-I02 | Every reference and lifecycle artefact binds exact ID/revision/hash plus canonical `asy_`/`spk_` aggregate and stored relation where applicable. | Schema, aggregate reducers, and relation resolver. | Substitute a valid foreign current record/aggregate/artefact/mapping member; reject with state unchanged. |
| W11-I03 | Required dependency/block subgraph is acyclic. | Edge-registration/admission validator. | Add direct and multi-hop cycles; reject atomically. |
| W11-I04 | An independently accepted Assay rubric/evidence scope is frozen by `RequestAssay` before collection, and observed axes close exactly to that relation. | `RequestAssay` and `RecordAssayScore`. | Late acceptance, post-request swap, foreign-Assay scorecard, missing/extra/duplicate/alias/wrong type/bound/stale mutations. |
| W11-I05 | Assay/Spike evidence cannot resolve promotion. | Decision authority resolver. | Feed PROMOTE recommendation/PASS without Stephen Decision; no state change. |
| W11-I06 | Spike verdict obeys success/failure/kill/Partial logic. | Spike-verdict schema and rule evaluation. | Trigger each kill condition one at a time; force unknown required evidence; reject false PASS. |
| W11-I07 | Promotion is exact-subject, exact-gate, human-locked. | `ResolveDecision` and authority grant. | Wrong actor, Candidate, revision, gate, evidence, option, next state, and stale grant. |
| W11-I08 | PROMOTE authorizes only one named next design step. | `CandidatePromotionApplied` reducer/write set. | Add Dispatch/pre-registration/result/claim event to batch; reject all. |
| W11-I09 | The complete literal six-family `DossierExpectedSet` is independently authored/reviewed/accepted, content-addressed, and frozen before candidate observation. | `DossierExpectedSetAccepted` and admission resolver. | Late/related/unaccepted oracle plus coordinated manifest/command/runtime omission; accepted oracle remains unchanged and rejects. |
| W11-I10 | Dossier closure is exact, including independently resolved/rehashed component and source bytes, not “all supplied passed.” | `AdmitResearchDossier`. | Per-family missing/extra/duplicate/stale/incompatible/tampered/valid-foreign/path-escape/count-only and source-resolution mutations. |
| W11-I11 | Dossier admission is atomic. | W2 transaction/write set. | Fail each validation step and inject concurrent tail/version changes; assert zero events/final objects/scopes/projections. |
| W11-I12 | Scout observations are not judgments or authority, and every W11 command has the literal §4.2 W4 profile/grant/subject/write set. | Scout schema plus complete command/event/authority catalogue. | Add score/promotion/claim fields, direct write, omitted command, wildcard subject or alternate event producer; reject. |
| W11-I13 | Generated views never authorize their source. | Command source allowlists. | Use successor/combined projection as dossier, annotation, transition, or Decision input; reject. |
| W11-I14 | Legacy, successor, annotation, and combined writer sets remain physically disjoint from registration through the operation commit point. | PathRegistration plus §7.3 handle/file-identity resolver. | Registered-root junction positive; exact/casefold/Unicode/8.3/symlink/reparse/prefix/hardlink/parent-swap race matrix. |
| W11-I15 | An annotation is evidence until a separate command acts. | `IngestDiscoveryAnnotation`. | Ingest proposed PROMOTE/object edit; only annotation event appears. |
| W11-I16 | Each active item has exactly one owner and one accepted observation–inventory-item–target–Decision relation. | `LegacyTransitionMapping` resolver and ownership reducer. | Attempt `dual_owned`, simultaneous transitions, or cross-source/item/target/Decision coordinated substitutions. |
| W11-I17 | Per-item transition never repurposes the legacy path. | Transition write set/path registry. | Transition one item while others remain; assert zero legacy-path write and legacy writer retained. |
| W11-I18 | Legacy-named generation requires an accepted exact-byte complete inventory, independent final observation, item/event bijection, writer revocation and race-free whole-path cutover. | `LegacyPortfolioInventory` and `CutOverDiscoveryPath`. | Omit/alias/unparse one row, coordinate parser omission, change final bytes, leave item/writer/collision/annotation, or swap parent/reparse; reject. |
| W11-I19 | Whole-path cutover is one way. | Closed cutover state machine. | Attempt `successor_active -> legacy_active`; reject. |
| W11-I20 | Projection deletion/rebuild is authority-neutral, deterministic, and published only through the operation-time physical-identity protocol. | Projector/replay and §7.3 contract. | Delete/mutate view; rebuild byte-identically; inject parent/reparse/hardlink races; authority unchanged and no wrong-path write. |
| W11-I21 | Portfolio Claim governance is a required assurance boundary and cannot compensate for W5 claim authority. | Portfolio Claim schema, W5 consumer predicate and Paper Claim governance tests. | Supply accepted-looking Claim without W5 claim Decision; every claim consumer rejects; perform no claim action. |
| W11-I22 | Replay fails closed on unknown/broken W11 records. | W2 replay/projectors. | Unknown major schema/event, broken hash/ref, missing reducer; no authoritative projection. |

## 12. Pre-implementation acceptance tests

The future materialization/implementation plan must bind distinct test identities to the
following minimum set before any runtime code is written:

1. strict positive/negative schema tests for every literal §8 object/authority,
   aggregate/relation, artefact, command/discriminant, event, Decision subtype, path,
   annotation, transition, manifest, reducer/projection, authority and receipt row;
2. one-field-at-a-time type/value/enum/pattern/required/additional-property mutations;
3. complete-row exact multiset equality against the independently accepted W11
   expected catalogue, including duplicate/swap/aliased-test/removed-effect/omitted-
   command/alternate-producer/coordinated-runtime-catalogue attacks;
4. Candidate/Assay/Spike/Promotion legal/illegal matrices with unique `asy_`/`spk_`
   streams, request-time accepted rubric/scope freeze, late acceptance, post-request
   swap and revisit-new-aggregate cases;
5. exact Candidate–Assay–Spike–artefact–RuleEvaluation–Decision relation substitutions
   using foreign but individually valid current records;
6. TDL legacy assay-rubric compatibility fixture proving the numeric rule while
   proving legacy `decision` is recommendation-only;
7. Spike PASS/FAIL/PARTIAL truth table with every kill condition and unknown condition
   perturbed at the producing seam;
8. PROMOTE/PARK/KILL option-specific requirements and non-Stephen authority negatives;
9. exact dossier positive fixture from a pre-observation accepted literal
   `DossierExpectedSet`, plus every-family missing/extra/duplicate/tampered/stale/
   incompatible/relationship/path-escape/valid-foreign negatives; independently
   re-resolve/re-hash every source; coordinate manifest/command/runtime omissions while
   the accepted expected set remains fixed;
10. dossier failure injection at every validation/publication boundary with zero event,
    final-object, ScopeDefinition, and projection publication;
11. idempotent lost-response retry and conflicting-payload retry for every literal
    mutating command/discriminant in §4.2, with its exact W4 subject, ordered events,
    streams, write set and receipt;
12. Scout source/dedup/collision tests and direct-judgment/direct-write permission
    negatives;
13. annotation valid/stale/duplicate/foreign-writer/manual-projection-edit tests;
14. Windows operation-time suite: registered-root-junction positive plus exact,
    case-fold, Unicode, 8.3, symlink/junction/reparse, prefix, hardlink/file-ID,
    parent-replacement and concurrent-writer swaps after every §7.3 phase;
15. per-item ownership transition race plus cross-source/item/target/Decision and
    coordinated foreign-valid substitutions against one accepted relation hash;
16. partial transition proof that legacy and successor paths remain disjoint and no
    `dual_owned` projection appears;
17. deletion/rebuild and projector-version tests for successor and optional combined
    views;
18. whole-path inventory/cutover fixture covering exact final bytes, complete byte/
    item membership, independent parser/reproducer, unknown/unparseable/alias/
    coordinated-omission attacks, transition-event bijection, post-inventory and
    post-final-observation writes, writer revocation, no legacy-named generated view
    before cutover, operation-time races, and reverse-transition rejection;
19. genesis and accepted-snapshot replay with projection hashes and unknown-schema
    fail-closed tests;
20. Paper Claim governance/consumer tests proving combined views, projection prose,
    Assay recommendation, Spike verdict, and portfolio Claim cannot satisfy W5 result/
    claim authority; the fixture creates no live claim and performs no claim action.

Fixtures must be constructible from committed synthetic/minimized files. They must not
depend on the live mutable backlog, restricted data, gitignored results, or a producer-
generated expected oracle. Passing software tests alone does not satisfy independent
review or D-G6-4.

## 13. Decision and owner-authority audit

| Decision/gate | Disposition in this draft |
|---|---|
| P-004/P-021 | Keep. Exact path/writer and item ownership now bind accepted mapping/inventory relations and operation-time physical identities; no shared writer or inferred owner. |
| P-005/P-022 | Keep. Every Discovery promotion is human-locked; independent review evidence remains distinct from the author. |
| P-026 | Keep. Specification only; no legacy or successor state mutation. |
| P-032 | Keep. Canonical lifecycle, independent dossier expected authority, complete command subjects, and vault projection/annotation boundaries are defined prospectively. |
| P-034 | Keep. Accepted per-item source–item–target relations precede an accepted complete inventory/final-observation cutover; no indefinite dual-running, implicit batch or parser omission. |
| P-036 | Keep. WP6 launch-basis constraints are unchanged; W11 receives a new exact-revision gate. |
| D-G6-4 limb 1 | **Open:** revision 0.2 reconciles the prior `rework_required` report but is not self-accepted; Stephen must accept its new exact commit only after fresh independent review reports no open Critical/Major. |
| D-G6-4 limb 2 | **Open:** Stephen must approve a content-addressed first ownership-transition batch using the accepted §7.5 relation; no item/path migration is inferred by accepting the spec. |
| W11-A1 | **Open/optional:** accept the proposed combined-view path, substitute another disjoint third path, or omit the view. |

The first transition-batch owner record must identify each item/current owner/source
hash, intended target/target-object hashes, path-registry revision, collision-scan
identity/hash, unresolved conflicts, exact command/write set, reviewer, and rollback/
stop evidence. An empty or descriptive list is not approval.

### 13.1 Binding review reconciliation

The report at
`../reviews/adversarial-wp6-5-w11-spec-review-2026-07-18.md` remains immutable. This
author reconciliation records the following dispositions without claiming independent
acceptance:

| Finding | Revision 0.2 disposition | Invariants/tests re-opened for fresh review |
|---|---|---|
| C-1 | Added the complete literal, pre-observation, independently authored/reviewed/Stephen-accepted `DossierExpectedSet`; `AdmitResearchDossier` derives all expectations from it and coordinated candidate-side omission cannot change it. | I09–I11; tests 3, 9–11 |
| C-2 | Added content-addressed exact-byte `LegacyPortfolioInventory`, independent parser/reproducer, byte coverage, final handle-bound observation, item/event bijection and post-observation race closure. | I16–I20; tests 14–18 |
| M-1 | Added canonical `asy_`/`spk_` IDs/streams and bound every artefact, event, RuleEvaluation and Decision relation. | I02, I04–I07; tests 1, 4, 5 |
| M-2 | `RequestAssay` now freezes an already accepted rubric, axis-set and evidence-scope relation before `evidence_collecting`. | I04–I05; tests 4–6 |
| M-3 | Admission independently resolves and rehashes every component and every source dependency from verified handles/resolvers. | I09–I10; test 9 |
| M-4 | §4.2/§8 now give the literal complete command/event/authority/receipt/reducer/projection universe, including all five formerly omitted commands and exact W4 subjects/write sets. | I12, I15–I18; tests 1, 3, 11–13, 18 |
| M-5 | Added one accepted inventory-item/`LegacyRecordObserved`/source-selector/target/Decision relation hash loaded independently before allocation. | I02, I16–I17; tests 5, 15, 16 |
| M-6 | Added operation-time registered-root, no-follow traversal, handle/file-ID/hardlink, held-parent, atomic-replace and post-verify protocol plus phase-specific races. | I14, I18, I20; tests 14, 17, 18 |
| m-1 | Paper Claim is Required for governance/consumer tests while every actual claim activity remains unauthorized. | I21; test 20 |
| m-2 | Added dated §8 to the tracked plan-suite evidence register with exact live paths, hashes, mutability and limitations; linked it from §2.2/README. | Entry criterion 2 |

The prior review's complete audits are dispositioned, not narrowed: all five design
entry criteria are now stated as satisfied for authorship; every P-004/P-005/P-021/
P-022/P-026/P-032/P-034/P-036 and D-G6-4/W11-A1 row remains explicit above; all 22
invariants remain in §11; all 20 pre-implementation tests remain in §12; §8 resolves
the literal interface universe; §9 retains fail-closed behavior; §10 contains the
complete assurance classification; §13.2 reconciles owner-spec identities; and
§14/§14.1 retain independent review, proportionality and residual-risk gates. Author
checks are reconciliation evidence only.

### 13.2 Cross-spec consistency reconciliation

| Invariant / identity | Owning source | Revision 0.2 binding and disposition |
|---|---|---|
| First-class ID, immutable record and canonical stream/reference semantics | W2 §§5–9 | Portfolio records remain `obj_`; Assay and Spike now have canonical `asy_`/`spk_` aggregate streams and exact artefact/event/Decision relations. |
| Decision is not `RuleEvaluation` | W2 §18; P-005/P-022 | Scorecards/verdicts remain evidence; every PROMOTE/PARK/KILL resolution is an exact-subject Stephen Decision and cannot be compensated. |
| Acceptance bar independent of producer and frozen before observation | W5 §§6–11 | `RequestAssay` freezes accepted rubric/scope before evidence; `DossierExpectedSet` is independently authored/reviewed/accepted before candidate-manifest observation. |
| Complete expected-set closure and producer separation | W5 §11; WP6 master §6 | Six literal dossier row families and the literal §8 interface universe are accepted independently; candidate/runtime coordinated omissions remain unequal. |
| Atomic publication | W2 §§8–9/13 | Dossier and promotion batches validate exact relations/write sets first; any failure produces zero authoritative event/object/scope/projection publication. |
| Observation is not adoption | W2 §22; P-032/P-034 | `LegacyRecordObserved` is evidence only; an independently accepted transition mapping plus migration Decision is required for one item. |
| One active owner and no shared physical writer | W1 §§9–10; P-004/P-021 | Accepted item relation, exact inventory/final observation and §7.3 operation-time physical identity close partial and whole-path cutover. |
| Profile capability is not command authority | W4 §§7/15/19 | Every literal §4.2 row names allowed profile, exact subject IDs/hashes, separate grant, risk/effective scope and complete write set; unlisted rows default deny. |
| Portfolio Claim is not W5 claim authority | W1 §5.1; W5 §§14/19 | Paper Claim lane is Required for governance/consumer tests, while no actual claim activity is authorized and missing W5 authority cannot be compensated. |
| Specification is not implementation or migration authority | P-026/P-036; WP6 master | This revision materializes no schema/catalogue/runtime/projection, performs no live action, and leaves D-G6-4, WP6.6 and WP6.7 hard-stopped. |

## 14. Independent review, reconciliation, and exit gate

Before W11 can be accepted or WP6.6 planned:

1. A fresh independent reviewer reads the exact W11 revision and every direct owner/
   evidence source named in §2, then applies the adversarial-design-review standard.
2. The report is written under `docs/plans/agentic-research-system/reviews/` and includes
   verdict, severity-graded findings, complete decision audit, invariant/enforcement/
   test matrix, path/writer and transition attacks, failure behaviour, practicality,
   residual risks, and exact reviewed commit.
3. The reviewer explicitly attacks expected/observed producer separation, valid-foreign
   relational substitutions, shared physical writers, partial cutover, legacy-named
   generation, combined-view feedback, annotation round-tripping, and atomic dossier
   publication.
4. The primary author may perform a self-adversarial check, but it is recorded only as
   author verification and does not satisfy this independent gate.
5. Reconciliation dispositions every finding and records exact changes. Any material
   post-review change receives fresh review of the new exact revision.
6. Acceptance requires no open Critical or Major finding, explicit disposition of all
   Minor findings, both required contract commands passing, link/path consistency, and
   Stephen's exact-revision D-G6-4 decision.

### 14.1 Proportional controls and residual risks

Controls remain concentrated at their risk boundary: Scout registration uses closed
source/dedup/collision checks; Assay/Spike use frozen request/plan relations and bounded
review; promotion uses the exact Stephen Decision; dossier admission alone bears the
full independent six-family oracle and byte-rehash cost; each ownership transition uses
one accepted mapping row; irreversible cutover alone bears full inventory, writer
revocation, final-byte and filesystem-race proof. The optional combined view is omitted
unless W11-A1 is accepted after core path tests.

Fresh review and later implementation review must retain these residual risks:

- future schema/expected-catalogue code could derive expected and observed sides from
  one runtime registry; review must reconstruct both sides separately and run
  coordinated-pair mutations;
- Windows filesystem features vary by volume and privilege. Tests must record which
  junction/reparse/hardlink/file-ID races executed; any unavailable required test is
  Partial, not pass;
- living legacy prose remains mutable. Every later observation, mapping, transition and
  cutover binds fresh exact bytes; this specification's dated hash is never frozen
  migration authority;
- W9/W10 implementation specifications remain downstream. They may consume these
  domain-neutral contracts but cannot narrow them, introduce shared writers or make a
  TDL vault path mandatory in the reusable core; and
- passing schemas and relationship tests proves interface conformance, not scientific
  adequacy of a future rubric, Spike design, result or claim. Those remain separately
  governed by W5 and their applicable domain packs.

Until those steps complete, status remains `review_pending`. Even after specification
acceptance, the separately produced strict-schema/expected-catalogue review and owner
acceptance in §8 must precede runtime implementation, and the first transition batch
must receive its own D-G6-4 decision.

## 15. Specification exit checklist

- [x] Accepted decisions and bounded assumptions are explicit.
- [x] Direct evidence inputs, boundaries, owners, and consumers are identified.
- [x] Programme, paper, hypothesis, Candidate, method, dataset, portfolio Claim, and
      dependency records are strict prospective objects.
- [x] Candidate/Assay/Spike/Promotion lifecycles, commands, events, authority, and
      Partial/failure semantics are defined.
- [x] `AdmitResearchDossier` exact closure and zero-publication failure are specified.
- [x] `DossierExpectedSet` is a complete literal independent authority accepted before
      candidate observation; every source dependency is independently rehashed.
- [x] Scout ingestion plus Scout/Portfolio Steward W4 deltas are specified.
- [x] Legacy/successor/annotation/combined paths and writer sets are disjoint.
- [x] Annotation ingestion, item transition, collision, rebuild, and one-way whole-path
      cutover are specified.
- [x] Exact accepted transition relations, content-addressed complete inventory,
      independent final-byte observation, and operation-time Windows identity/races are
      specified.
- [x] All six assurance lanes are dispositioned; Output/Provenance is primary.
- [x] Invariants map to enforcement points and pre-implementation attacks.
- [x] Initial independent adversarial review completed with `rework_required`; immutable
      report incorporated.
- [x] Primary author reconciliation dispositions every reported finding.
- [ ] Fresh independent review of the new exact commit reports no open Critical/Major.
- [ ] Stephen accepts the exact W11 revision under D-G6-4.
- [ ] Stephen approves the first exact ownership-transition batch under D-G6-4.
- [ ] Future strict schemas and independent expected catalogue are materialized,
      reviewed, and accepted before implementation.

The unchecked items are intentional hard stops, not incomplete implementation work in
this specification task.
