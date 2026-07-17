# W11 — Portfolio and Discovery Lifecycle Specification

**Date:** 2026-07-18
**Status:** `review_pending`; specification only
**Specification version:** 0.1
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
4. `AdmitResearchDossier` validates an independently accepted manifest and exact
   component-hash closure before atomically publishing any portfolio object or
   `ScopeDefinition` reference. Any missing, extra, duplicate, stale, incompatible,
   or tampered component produces zero publication.
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
| `01-current-system-evidence.md` §§1, 2.2, 3.1–3.2, 4.2–4.4, 4.8–4.9, 4.12, 5.1, 5.6, and 7 | Source precedence; strengths to preserve; mutable-state, single-slot, root, self-approval, pending-contract, and missing-eval failure classes. |
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
rubrics, and path registrations. Evidence payloads are a different W2 record class:
`AssayScorecard`, `SpikePlan`, `SpikeVerdict`, `ScoutObservationBatch`,
`DiscoveryAnnotation`, and `ResearchDossierManifest` are immutable external artefacts
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
scored/reviewed -> superseded
```

Spike instances project independently as:

```text
planned -> approval_pending -> authorized -> running -> verdict_recorded
planned/approval_pending/authorized/running -> cancelled | partial
verdict_recorded -> superseded
```

A Candidate state never stands in for the Assay or Spike state. Paired operational
events may project that an authorized Spike started or reported, but no such event
advances the Candidate past a promotion gate without the Decision batch below.

### 4.2 Command/event catalogue

Each command uses the complete W2 envelope, strict versioned payload schema, exact
stream versions/write set, one project writer, and W2 validation order.

| Command | Required authority and principal preconditions | Ordered accepted facts |
|---|---|---|
| `RegisterCandidate` | Scout or Portfolio Steward grant; exact source observations; no identity/alias collision | `CandidateRegistered` |
| `RequestAssay` | Portfolio Steward grant; Candidate `registered` or valid revisitation Decision | `AssayRequested`, `CandidateAssayRequested` |
| `RecordAssayScore` | Assay producer grant; complete accepted rubric closure; exact Candidate revision | `AssayScored`, `CandidateAssayLinked` |
| `RecordAssayPartial` | Assay producer grant; completed/unmet evidence explicit | `AssayPartialRecorded`, `CandidateAssayPartialLinked` |
| `ProposePromotionDecision` | Portfolio Steward grant; exact Assay/Spike evidence; no unresolved proposal at the same gate | `DecisionProposed`, `CandidatePromotionRequested` |
| `ResolveDecision` with `decision_kind=discovery_promotion` | Stephen-attributed grant; exact proposal/subject/evidence hashes | `DecisionResolved`, then `CandidatePromotionApplied` in the same batch |
| `RegisterSpikePlan` | Portfolio Steward grant; Candidate `spike_planning_authorized`; preceding assay-to-spike PROMOTE Decision; locked plan hash | `SpikePlanned`, `CandidateSpikePlanLinked` |
| `ResolveDecision` with `decision_kind=spike_execution_authority` | Stephen-attributed approval of exact SpikePlan; required route/resource/assurance refs present | `DecisionResolved`, `SpikeAuthorized`, `CandidateSpikeAuthorized` |
| `StartSpike` | Operator grant; exact authorized plan/lease/attempt/resource evidence | `SpikeStarted`, `CandidateSpikeStarted` |
| `RecordSpikeVerdict` | Spike producer grant; exact plan and artefact/evidence closure | `SpikeVerdictRecorded`, `CandidateSpikeVerdictLinked` |

No generic `StatusChanged` or `DiscoveryUpdated` event is allowed. Rejection writes no
lifecycle event. A report, annotation, score, verdict, review, or process exit cannot
substitute for the command in the table.

### 4.3 `AssayScorecard`

`ars://portfolio/assay-rubric` is a closed immutable `obj_` definition with exact
rubric ID/revision/hash, domain-pack refs, ordered axis definitions, each axis's closed
kind/value type/bounds or allowed set, required-axis-set hash, evaluation order,
recommendation predicates, forbidden axes, Partial rules, source authority, reviewer,
and accepting authority. A rubric cannot accept its own scorecard.

The prospective `ars://portfolio/assay-scorecard` artefact payload schema is closed and
requires a W2 `art_` manifest plus:

- exact Candidate ID/revision/hash;
- accepted `AssayRubric` ID/revision/hash;
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
PROMOTE recommendation.

The current TDL legacy rubric maps explicitly to one future accepted rubric revision:
Axis 1 is the `topology_earns_its_keep` Boolean gate; Axes 2 and 3 are integers in
`[0,3]`; legacy PROMOTE requires Axis 1 pass, Axis 2 + Axis 3 ≥4, and neither numeric
axis equal to zero. The mapped legacy rubric continues to forbid `programme_fit` as a
scored axis. The legacy `decision` field imports only as a recommendation plus
source evidence. It never imports as a resolved `PromotionDecision`. Domain-neutral
W11 does not hard-code topology into every future rubric.

### 4.4 `SpikePlan` and `SpikeVerdict`

The `ars://portfolio/spike-plan` artefact payload requires exact Candidate and
source-scorecard refs,
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
| `candidate_ref`, `spike_plan_ref`, `attempt_ref` | Exact IDs/revisions/hashes; all three relationships must agree. |
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
- exact AssayScorecard or SpikeVerdict plus validation/review refs;
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

### 5.1 Strict dossier manifest

The future `ars://portfolio/research-dossier-manifest` artefact payload schema is closed
and contains:

- dossier logical ID, revision, manifest schema ID/version, package version, purpose,
  author, created time, and governing decisions;
- `component_count` and a unique ordered-by-key `components[]` set;
- `source_dependency_count` and a unique ordered-by-key `source_dependencies[]` set;
- portfolio-object blueprint refs and `ScopeDefinition` blueprint refs;
- dependency-edge refs and exact cross-component relations;
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
  object_blueprint_hashes: sorted,
  scope_definition_blueprint_hashes: sorted,
  dependency_edge_hashes: sorted
}))
```

The manifest file's own bytes are hashed externally and supplied to the command. The
manifest never hashes itself.

### 5.2 `AdmitResearchDossier` command shape

The command uses the W2 envelope and a strict payload with:

- exact manifest artefact/path, byte length, SHA-256, schema ID/version, and closure
  hash;
- expected accepted admission-profile identity;
- exact expected component/source/object/scope/edge key-set hashes and counts;
- proposed portfolio object IDs/revisions/hashes and ScopeDefinition IDs/revisions/
  hashes;
- complete affected stream write set with expected versions;
- expected project global position/tail hash;
- actor, authority grant, idempotency key, reason, and governing Decision refs;
- explicit `ownership_effect: successor_owned_new_objects_only`.

It cannot accept a payload-supplied “validated” flag, infer acceptance from a vault
status, adopt a legacy item, resolve a PromotionDecision, issue a Dispatch, or promote
a claim.

### 5.3 Exact closure and atomic publication algorithm

The future handler must perform these steps in order:

1. Validate the envelope/payload and resolve the independently accepted admission
   profile and expected-set manifest by exact path/schema/version/Git blob/SHA-256.
2. Read manifest bytes from the registered root, verify size/hash/schema, and reject
   traversal, case-fold, Unicode-normalization, symlink, or reparse-point escapes.
3. Compare expected versus observed component, source, object, scope, and edge key sets
   one-to-one. Missing, extra, duplicate, aliased, or count-only matches reject.
4. Resolve each component independently from its registered root; recompute bytes,
   size, hash, and schema. The manifest producer's cached observations are not used as
   observed truth.
5. Validate every cross-component and portfolio relationship, including exact revisions
   and hashes. A valid foreign member cannot replace the member named by a relation.
6. Recompute closure hash and compare with both the manifest and command.
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
  physical identity;
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

### 7.3 Human annotation ingestion

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

### 7.4 Per-item ownership transition

`TransitionPortfolioOwnership` has a strict payload containing item ID/type, exact
current and target mode, source path registration/revision, source observation bytes/
hash, target object IDs/revisions/hashes, alias mapping, unresolved conflicts, collision
scan identity/hash, governing `migration_authority` Decision, expected source/target
stream versions, event tail, and complete write set.

Allowed active transitions are:

```text
legacy_owned -> successor_owned
legacy_owned -> closed_reference
successor_owned -> closed_reference
```

No transition targets `dual_owned`, returns to `legacy_owned`, infers acceptance, or
changes another item. On success, `PortfolioItemOwnershipTransitioned` records the
before/after owner, source hash, target identities, effective event position, and
attributed authority. The legacy file is not edited by this command. Remaining legacy
items continue to use it as authority; the transitioned item appears only in the
successor projection with an explicit legacy lineage link.

The physical legacy path remains legacy-written during a partial cutover, but its
authority is item-scoped. For a transitioned item, the exact source row/bytes recorded
by the transition become frozen lineage; any later legacy edit to that item's row is a
diagnostic observation only and cannot regain authority or update the successor object.

### 7.5 Whole-path cutover

The legacy backlog path can move from `legacy_active` to `successor_active` only when:

1. an independently reproduced inventory proves every item formerly using the path is
   `successor_owned` or `closed_reference` at exact transition events;
2. no unresolved/duplicate/foreign item or annotation remains;
3. legacy writers are stopped and their write authorities revoked;
4. the final legacy bytes/hash and writer-set snapshot are preserved as evidence;
5. the successor and optional combined projections rebuild successfully from canonical
   state without reading their own output;
6. collision, deletion/rebuild, path-resolution, and concurrent-write tests pass;
7. Stephen resolves the exact whole-path cutover Decision.

`CutOverDiscoveryPath` atomically records `LegacyDiscoveryPathCutoverCompleted` and a
new PathRegistration revision. Only after that event may a separately registered
projector target the legacy-named path. The transition is one way:
`successor_active -> legacy_active` is invalid. Recovery rebuilds successor projections
or stops; it does not re-enable legacy writers.

### 7.6 Collision, deletion, and rebuild behaviour

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

The future independently authored expected catalogue is proposed at
`.research-system/evals/expected/w11-portfolio-discovery-v1.json`. Before first runtime
implementation or observation, Stephen must accept its exact repository path, schema
ID/version, Git blob, and SHA-256 after independent review. The runtime implementer may
not be the sole producer/reviewer of this expected source.

The catalogue must contain one complete row per interface with:

```text
logical_key, schema_id/version/hash, command_type, authority_subject,
payload discriminant, exact preconditions, ordered events, affected streams,
complete write set, reducer, projection targets, receipt identity,
distinct positive test, distinct negative/mutation tests
```

Tests compare a one-to-one multiset of complete rows, not counts or separately derived
field sets. Coordinated mutation of the candidate catalogue and runtime registry must
still differ from the independently accepted expected identity.

## 9. Failure behaviour

| Failure | Required result |
|---|---|
| Candidate/source identity collision | Reject registration; preserve both observations; no Candidate event. |
| Assay axis missing/extra/duplicate/wrong type or rubric stale | Reject `AssayScored` or record explicit Assay Partial; no promotion proposal inferred. |
| Spike plan, attempt, Candidate, or verdict relationship mismatch | Reject verdict; preserve artefacts as unaccepted candidates. |
| Kill condition triggered but verdict PASS/PARTIAL | Reject verdict schema/relational validation. |
| Required Spike condition unable to evaluate | PARTIAL; no PASS or promotion. |
| Promotion resolved by model/Manager or against stale/foreign evidence | Reject before Decision event. |
| PROMOTE attempts to dispatch, lock a pre-registration, accept a result, or promote a claim | Reject complete batch. |
| Dossier missing/extra/duplicate/tampered/stale/incompatible component | Reject atomically; zero object/ScopeDefinition publication. |
| Expected and observed dossier/catalogue values share one producer | Acceptance gate fails; independent expected source required. |
| Legacy prose says Success/Done/PROMOTE | Observation only; no adoption or Decision. |
| Path/writer collision or shared physical target | Reject registration/write/transition; no “last writer wins.” |
| Manual edit to generated view | Drift diagnostic; rebuild from events; never ingest. |
| Annotation targets stale revision | Reject with current identity; human must issue a new annotation. |
| Ownership transition lacks migration authority/collision scan | Reject; item remains under current owner/path. |
| Whole-path cutover has any legacy-owned item or active legacy writer | Reject; legacy path remains legacy authority. |
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
| Paper Claim | **N/A** | W11 specifies a portfolio Claim reference and preserves W5 claim authority but creates, reviews, promotes, or changes no paper-facing claim or wording. Any later claim uses W5 and Stephen's P-005 decision. |

For Output/Provenance, retrospective result-file items such as numerical date suffixes,
seeds, cache parameters, or result-vault filing are not applicable to this specification.
Their absence does not weaken the prospective requirements above.

## 11. Invariant → enforcement point → acceptance-test mapping

| ID | Invariant | Enforcement point | Required test/attack |
|---|---|---|---|
| W11-I01 | Object definitions are immutable and state-free. | Closed object schemas and reducers. | Reject lifecycle/status/path fields and in-place revision mutation. |
| W11-I02 | Every reference binds exact ID/revision/hash. | Schema and relation resolver. | Substitute a valid foreign current record; reject with state unchanged. |
| W11-I03 | Required dependency/block subgraph is acyclic. | Edge-registration/admission validator. | Add direct and multi-hop cycles; reject atomically. |
| W11-I04 | Assay rubric and observed axes close exactly. | `RecordAssayScore`. | Missing, extra, duplicate, alias, wrong type/bound, and stale-rubric mutations. |
| W11-I05 | Assay/Spike evidence cannot resolve promotion. | Decision authority resolver. | Feed PROMOTE recommendation/PASS without Stephen Decision; no state change. |
| W11-I06 | Spike verdict obeys success/failure/kill/Partial logic. | Spike-verdict schema and rule evaluation. | Trigger each kill condition one at a time; force unknown required evidence; reject false PASS. |
| W11-I07 | Promotion is exact-subject, exact-gate, human-locked. | `ResolveDecision` and authority grant. | Wrong actor, Candidate, revision, gate, evidence, option, next state, and stale grant. |
| W11-I08 | PROMOTE authorizes only one named next design step. | `CandidatePromotionApplied` reducer/write set. | Add Dispatch/pre-registration/result/claim event to batch; reject all. |
| W11-I09 | Dossier expected set is independent and content-addressed. | Accepted expected catalogue/admission profile. | Coordinated candidate/runtime or manifest/observed-source mutation; accepted oracle identity remains different. |
| W11-I10 | Dossier closure is exact, not “all supplied passed.” | `AdmitResearchDossier`. | Missing, extra, duplicate, stale, incompatible, tampered, path-escape, and count-only matches. |
| W11-I11 | Dossier admission is atomic. | W2 transaction/write set. | Fail each validation step and inject concurrent tail/version changes; assert zero events/final objects/scopes/projections. |
| W11-I12 | Scout observations are not judgments or authority. | Scout schema/profile and ingestion command. | Add score/promotion/claim fields or direct projection write; reject. |
| W11-I13 | Generated views never authorize their source. | Command source allowlists. | Use successor/combined projection as dossier, annotation, transition, or Decision input; reject. |
| W11-I14 | Legacy, successor, annotation, and combined writer sets are disjoint. | PathRegistration and physical resolver. | Exact/casefold/Unicode/8.3/symlink/reparse/prefix collision matrix. |
| W11-I15 | An annotation is evidence until a separate command acts. | `IngestDiscoveryAnnotation`. | Ingest proposed PROMOTE/object edit; only annotation event appears. |
| W11-I16 | Each active item has exactly one owner. | Ownership schema/reducer. | Attempt `dual_owned`, two simultaneous transitions, or valid foreign item substitution. |
| W11-I17 | Per-item transition never repurposes the legacy path. | Transition write set/path registry. | Transition one item while others remain; assert zero legacy-path write and legacy writer retained. |
| W11-I18 | Legacy-named generation requires complete whole-path cutover. | `CutOverDiscoveryPath`. | Leave one legacy item/writer/collision/unresolved annotation; reject. |
| W11-I19 | Whole-path cutover is one way. | Closed cutover state machine. | Attempt `successor_active -> legacy_active`; reject. |
| W11-I20 | Projection deletion/rebuild is authority-neutral and deterministic. | Projector/replay contract. | Delete/mutate view; rebuild byte-identically at same event/projector identity; authority unchanged. |
| W11-I21 | Portfolio Claim cannot compensate for W5 claim authority. | Portfolio Claim schema and consumer predicate. | Supply accepted-looking Claim without W5 claim Decision; claim consumers reject. |
| W11-I22 | Replay fails closed on unknown/broken W11 records. | W2 replay/projectors. | Unknown major schema/event, broken hash/ref, missing reducer; no authoritative projection. |

## 12. Pre-implementation acceptance tests

The future materialization/implementation plan must bind distinct test identities to the
following minimum set before any runtime code is written:

1. strict positive/negative schema tests for every object, command, event, Decision
   subtype, path, annotation, transition, manifest, and receipt;
2. one-field-at-a-time type/value/enum/pattern/required/additional-property mutations;
3. complete-row exact multiset equality against the independently accepted W11
   expected catalogue, including duplicate/swap/aliased-test/removed-effect attacks;
4. Candidate/Assay/Spike/Promotion legal-transition and illegal-transition matrices;
5. exact Candidate–Assay–Spike–Decision relational substitutions using foreign but
   individually valid current records;
6. TDL legacy assay-rubric compatibility fixture proving the numeric rule while
   proving legacy `decision` is recommendation-only;
7. Spike PASS/FAIL/PARTIAL truth table with every kill condition and unknown condition
   perturbed at the producing seam;
8. PROMOTE/PARK/KILL option-specific requirements and non-Stephen authority negatives;
9. exact dossier positive fixture plus missing/extra/duplicate/tampered/stale/
   incompatible/relationship/path-escape/coordinated-oracle negatives;
10. dossier failure injection at every validation/publication boundary with zero event,
    final-object, ScopeDefinition, and projection publication;
11. idempotent lost-response retry and conflicting-payload retry for every mutating
    command;
12. Scout source/dedup/collision tests and direct-judgment/direct-write permission
    negatives;
13. annotation valid/stale/duplicate/foreign-writer/manual-projection-edit tests;
14. Windows physical path collision suite across exact, case-fold, Unicode, 8.3,
    symlink/reparse, prefix, and concurrent-writer cases;
15. per-item ownership transition race and foreign-valid-record substitutions;
16. partial transition proof that legacy and successor paths remain disjoint and no
    `dual_owned` projection appears;
17. deletion/rebuild and projector-version tests for successor and optional combined
    views;
18. whole-path cutover blockers, exact completion, legacy-writer revocation, no
    legacy-named generated view before cutover, and reverse-transition rejection;
19. genesis and accepted-snapshot replay with projection hashes and unknown-schema
    fail-closed tests;
20. consumer tests proving combined views, projection prose, Assay recommendation,
    Spike verdict, and portfolio Claim cannot satisfy authority gates.

Fixtures must be constructible from committed synthetic/minimized files. They must not
depend on the live mutable backlog, restricted data, gitignored results, or a producer-
generated expected oracle. Passing software tests alone does not satisfy independent
review or D-G6-4.

## 13. Decision and owner-authority audit

| Decision/gate | Disposition in this draft |
|---|---|
| P-004/P-021 | Keep. Exact path/writer and item-ownership invariants are testable. |
| P-005/P-022 | Keep. Every Discovery promotion is human-locked; independent review evidence remains distinct from the author. |
| P-026 | Keep. Specification only; no legacy or successor state mutation. |
| P-032 | Keep. Canonical successor lifecycle plus vault projection/annotation boundaries are defined. |
| P-034 | Keep. Per-item transitions precede final whole-path cutover; no indefinite dual-running. |
| P-036 | Keep. WP6 launch-basis constraints are unchanged; W11 receives a new exact-revision gate. |
| D-G6-4 limb 1 | **Open:** Stephen must accept an exact W11 revision after fresh independent adversarial review and reconciliation. |
| D-G6-4 limb 2 | **Open:** Stephen must approve a content-addressed first ownership-transition batch; no item/path migration is inferred by accepting the spec. |
| W11-A1 | **Open/optional:** accept the proposed combined-view path, substitute another disjoint third path, or omit the view. |

The first transition-batch owner record must identify each item/current owner/source
hash, intended target/target-object hashes, path-registry revision, collision-scan
identity/hash, unresolved conflicts, exact command/write set, reviewer, and rollback/
stop evidence. An empty or descriptive list is not approval.

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
- [x] Scout ingestion plus Scout/Portfolio Steward W4 deltas are specified.
- [x] Legacy/successor/annotation/combined paths and writer sets are disjoint.
- [x] Annotation ingestion, item transition, collision, rebuild, and one-way whole-path
      cutover are specified.
- [x] All six assurance lanes are dispositioned; Output/Provenance is primary.
- [x] Invariants map to enforcement points and pre-implementation attacks.
- [ ] Fresh independent adversarial review completed.
- [ ] Reconciliation completed with no open Critical/Major finding.
- [ ] Stephen accepts the exact W11 revision under D-G6-4.
- [ ] Stephen approves the first exact ownership-transition batch under D-G6-4.
- [ ] Future strict schemas and independent expected catalogue are materialized,
      reviewed, and accepted before implementation.

The unchecked items are intentional hard stops, not incomplete implementation work in
this specification task.
