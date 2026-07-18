# W11 — Portfolio and Discovery Lifecycle Specification

**Date:** 2026-07-18
**Status:** `review_pending`; revision 0.5 reconciles the binding R4
`rework_required` review and requires fresh independent R5 review; specification only
**Specification version:** 0.5
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
**R1 review:** exact subject `70074d42eade8460808e4d1d29348b7806eff2d0`;
independent report commit `21ebc46b0c415286e8c525106e8bb9fde92d38c3`;
verdict `rework_required` (2 Critical, 6 Major, 2 Minor).
**R2 review:** exact subject `d24df9d26f0d906d177eafa1eaeabb65a5515004`;
independent report commit `ecbad093182110b8a7474304f20e10f64981d7bd`;
verdict `rework_required` (0 Critical, 5 Major, 0 Minor). Revision 0.3
dispositions every R1/R2 finding but does not accept itself.
**R3 review:** exact subject `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b`;
independent report commit `1175c28f9e09f9bc94dff4a7a82913b985c6c0ef`;
verdict `rework_required` (0 Critical, 6 Major, 0 Minor). Stephen approved the bounded
R3-M2 external Git/blob bootstrap and R3-M6 annotation-epoch decisions on 2026-07-18;
revision 0.4 dispositions every R3 finding but does not accept itself.
**R4 review:** exact subject `4b941326e290582db7be07113d5d7bb78d8b97a3`;
independent report commit `e68d60f4e9d41fd86495c4259cbc5bc84b77d018`;
verdict `rework_required` (0 Critical, 1 Major, 1 Minor). Revision 0.5 dispositions
both R4 findings but requires a fresh independent R5 review.

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
4. `AdmitResearchDossier` validates a candidate `ResearchDossierManifest` against an
   independently authored literal `DossierExpectedSetContent` and its later, external
   `DossierExpectedSetAcceptance`, then
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
7. Future W11 schemas and their complete owner catalogue are reviewed and accepted as
   exact Git paths/blobs/SHA-256 identities before any W11 runtime exists. A separately
   accepted minimal bootstrap contract may later import that immutable envelope through
   one independently verified genesis transaction; W11 runtime cannot produce or accept
   its own prerequisite.
8. Whole-path cutover freezes a registered annotation-inbox epoch. The cutover command
   fences and re-observes that exact epoch before commit, while annotations arriving
   after the fence are routed to a new successor epoch and are not silently stranded.

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

| README criterion | Revision 0.5 disposition |
|---|---|
| 1. Decisions accepted or assumptions explicit | **Satisfied for authorship.** P-004/P-005/P-021/P-022/P-026/P-032/P-034/P-036 are accepted and preserved in §2.1; Stephen approved the bounded external-catalogue bootstrap and annotation-epoch policies; W11-A1 and both D-G6-4 acceptance limbs remain explicitly open. |
| 2. Evidence inputs in the evidence register | **Satisfied.** §2.2 resolves the base audit and the exact dated W11 live evidence to tracked root register §8, including paths, byte hashes, mutability and limitations. |
| 3. Boundaries and consumers identified | **Satisfied.** §2.3 identifies W1/W2/W4/W5/W9/W10, Vault and external-service boundaries and consumers. |
| 4. Independent review owner | **Satisfied for assignment, not acceptance.** The primary author, fresh I1 reviewer, Manager reconciler and Stephen acceptance authority are distinct. R1 through R4 returned `rework_required`; revision 0.5 requires a fresh exact-commit R5 review. |
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

The envelope above applies to portfolio definitions, dependency edges, Assay-rubric and
evidence-scope contents, path registrations, `DossierExpectedSetContent`,
`LegacySourceInventoryContent`, `LegacyTransitionMappingContent`, and
`LegacyCutoverClosureContent` candidates. Review, acceptance, file observation,
staleness, and lifecycle state are external events, never fields inside those candidate
contents. Evidence payloads are a different W2 record class:
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
| Assay | `asy_<lowercase UUIDv7>`; the canonical Assay stream ID is exactly the `assay_id` | Proposed once by `RequestAssay`. `AssayRequested` freezes one Candidate ID/revision/hash, exact rubric/scope contents and file observations, external Assay-bar acceptance, required-axis/scope hashes, prospective=actual producer relation, and the creating command. |
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

### 3.6 Topologically constructible content and acceptance authorities

Every W11 content-addressed authority is a directed acyclic dependency graph (DAG), not
one record that claims its own storage, review, acceptance, or lifecycle state. The
following stages and edges are normative for dossier, Assay-bar, legacy-source,
transition-mapping, cutover-closure, path-registration, and future schema-catalogue
authorities:

| Stage | Immutable node | May depend on | Must not contain |
|---|---|---|---|
| A | Accepted owner requirement or this specification's literal owner row | Earlier accepted owner decisions and source authorities | Any candidate produced at B–F |
| B | `*Content` candidate | Stage-A requirements and independently resolved source identities | Its serialized repository path/blob/file digest; its own review/Decision/event; `accepted`, `reviewed`, `current`, or other lifecycle state |
| C | `W11AuthorityFileObserved` | Exact Stage-B ID/revision/content hash plus bytes independently read after serialization | Its own event hash; any later review, Decision or consumer result |
| D | `ReviewRequested` then `ReviewVerdictRecorded` | Exact B content and C file observation; evidence-derived reviewer relationship | Later Decision/acceptance or consumer result; a verdict inside B |
| E | `DecisionProposed`, `DecisionResolved`, then typed `*Accepted` event | Exact B, C, D and Stage-A subject; the typed acceptance event names the Decision ID and transaction ID | Its own event hash; a sibling event hash; later runtime/schema/manifest/transition output |
| F | Runtime candidate, command or later closure content | Exact accepted Stage-E event plus independently re-resolved B/C bytes and current non-staleness evidence | Authority derived from its own produced or observed output |

`*Content.content_hash` is SHA-256 over P0 canonical JSON excluding only that
`content_hash` field. `W11AuthorityFileObserved` binds `content_id`, revision/hash,
schema ID/version, exact repository path, Git commit/blob, file length and SHA-256 from
an independently opened file. Like every W2 event, its event hash excludes its own
event-hash field. Reviews and acceptance events reference earlier identities/hashes;
they are not serialized into the content they accept. An acceptance transaction may
emit ordered `DecisionResolved` and typed `*Accepted` events, but neither event embeds
the other's event hash; both bind the prior Decision ID, command ID and transaction ID.

Every serialized `*_relation_hash` is computed before the enclosing `content_hash`
over one separately enumerated relation object. Its preimage excludes the relation-hash
field itself, the enclosing `content_hash`, and every file-observation, review,
Decision, acceptance, transaction, record and event hash. The enclosing content may
then carry the derived relation hash as an ordinary field. “Complete row” always means
the named relation fields, never the serialized container or either derived hash. A
materializer must expose the preimage field list and a topological-sort fixture; an
implicit whole-record hash is invalid.

The authority resolver constructs the graph in the displayed order and rejects a
self-edge, backward edge, strongly connected component, missing stage, foreign-valid
substitution, or field that moves review/acceptance state into content. It independently
recomputes every B/C hash and requires the accepted row relation to equal stored event
data. A candidate may be superseded only by a new content candidate that repeats this
sequence; no in-place acceptance flag is mutable.

The catalogue uses a bounded pre-runtime variant of this ordering. This W11 owner annex
fixes logical schema IDs, subjects, events, reducers, projections and tests at Stage A.
A later materialization task creates schema files and `W11SchemaCatalogueContent` at B.
An independent process that executes no W11 command opens the committed bytes and
records their exact Git commit/path/blob, length and SHA-256 at C; a distinct reviewer
reconstructs the complete owner/schema multiset and records a report at D. Stephen then
accepts one external `W11CatalogueAcceptanceEnvelope` at E containing those exact
identities, the review identity, the specification revision, owner-multiset hash and
the separately reviewed bootstrap-contract identities. Only that external acceptance
may authorize runtime implementation at F.

After implementation, the first mutation is one `ImportAcceptedW11CatalogueGenesis`
transaction executed by the independently verified bootstrap mechanism named in the
envelope. It reopens every accepted byte subject, rejects any identity or multiset
delta, writes only the imported catalogue authority and genesis provenance, and cannot
review, accept, amend or regenerate the envelope. Its expected side is the external
envelope, never a W11 runtime registry. No catalogue, schema registry, candidate
manifest, parser, bootstrap importer or runtime enumerator may generate both sides of
its own completeness check.

## 4. Discovery lifecycles, commands, and events

### 4.1 Candidate projection

```text
registered
  -> assay_pending -> assay_scored -> assay_decision_pending
       -> parked | killed | spike_planning_authorized
  -> assay_pending -> assay_partial -> assay_partial_reviewed
       -> assay_revisit_pending -> assay_retry_authorized | parked | killed
  -> assay_pending -> assay_cancelled -> assay_cancelled_reviewed
       -> assay_revisit_pending -> assay_retry_authorized | parked | killed
  -> spike_planning_authorized -> spike_approval_pending -> spike_authorized
       -> spike_running -> spike_verdict_recorded -> spike_decision_pending
       -> parked | killed | preregistration_authorized
  -> spike_running -> spike_partial -> spike_partial_reviewed
       -> spike_revisit_pending -> spike_retry_authorized | parked | killed
  -> spike_approval_pending | spike_authorized | spike_running -> spike_cancelled
       -> spike_cancelled_reviewed
       -> spike_revisit_pending -> spike_retry_authorized | parked | killed
  -> superseded
```

Every displayed arrow has one literal command/event owner row in §4.2. There is no
implicit `partial -> pending`, `cancelled -> pending`, or same-aggregate retry.
`ProposeRevisitDecision` moves only an exact independently reviewed Partial or cancelled
outcome to `*_revisit_pending`. Stephen's `ResolveDecision / discovery_revisit` selects
`RETRY | PARK | KILL`. `RETRY` moves only the Candidate to the typed
`assay_retry_authorized` or `spike_retry_authorized` state. The old aggregate remains
closed until the replacement-creation transaction atomically creates a fresh aggregate
and marks the old one superseded. PARK/KILL uses the existing terminal Candidate states;
PARK requires objective revisit conditions, while KILL never reopens in place.

`parked` may return only through a new exact `discovery_revisit` Decision that names its
prior aggregate, evidence and satisfied revisit predicate; the subsequent request still
creates a new `asy_`/`spk_`. Resuming an already-authorized unchanged Spike attempt is a
separate W8 operational transition and does not reopen a cancelled or completed W11
aggregate. `preregistration_authorized` authorizes drafting/review only.

Assay instances project independently as:

```text
requested -> evidence_collecting -> scored -> reviewed
requested/evidence_collecting -> partial | cancelled
partial -> partial_reviewed
cancelled -> cancelled_reviewed
partial_reviewed/cancelled_reviewed -> revisit_pending -> retry_authorized
revisit_pending --PARK/KILL--> prior terminal outcome + Decision overlay
reviewed/partial_reviewed/cancelled_reviewed/retry_authorized -> superseded
```

Spike instances project independently as:

```text
planned -> approval_pending -> authorized -> running -> verdict_recorded
planned/approval_pending/authorized/running -> cancelled
running -> partial; verdict_recorded -> reviewed; partial -> partial_reviewed
cancelled -> cancelled_reviewed
partial_reviewed/cancelled_reviewed -> revisit_pending -> retry_authorized
revisit_pending --PARK/KILL--> prior terminal outcome + Decision overlay
reviewed/partial_reviewed/cancelled_reviewed/retry_authorized -> superseded
```

A Candidate state never stands in for the Assay or Spike state. Paired operational
events may project that an authorized Spike started or reported, but no such event
advances the Candidate past a promotion gate without the Decision batch below.

#### 4.1.1 Closed recovery and supersession transitions

| From aggregate / Candidate state | Command and exact authority subject | Ordered events and streams | Effect and only recovery |
|---|---|---|---|
| Assay `requested` or `evidence_collecting` / `assay_pending` | `CancelDiscoveryEvaluation / assay`; `assay_cancellation = assay_id + stored relation hash + reason/evidence hash` | `AssayCancelled` on old `asy_`; `CandidateEvaluationCancelled / assay` on Candidate | Old Assay and Candidate become `cancelled`/`assay_cancelled`; no promotion proposal; OR-038/OR-039 review the exact cancellation before revisit. |
| Assay `cancelled` / `assay_cancelled` | `RequestDiscoveryOutcomeReview / assay_cancelled`; exact cancellation event, reason/evidence, aggregate relation and proposed reviewer | `ReviewRequested`; `AssayCancellationReviewRequested` on review/`asy_` streams | Cancellation remains terminal with one unresolved review overlay; only OR-039 may satisfy it. |
| Assay `cancelled` / `assay_cancelled` with unresolved review | `ReviewDiscoveryOutcome / assay_cancelled`; exact OR-038 subject and evidence-derived reviewer relationship | Always `ReviewVerdictRecorded`; only a §4.2.3 policy-satisfying verdict emits `AssayCancellationReviewed`; `CandidateAssayCancellationReviewed` | Satisfying branch becomes `cancelled_reviewed`/`assay_cancelled_reviewed`; every other verdict leaves both outcomes unchanged and the gate closed. |
| Assay `partial` / `assay_partial` | `RequestDiscoveryOutcomeReview / assay_partial`; exact aggregate/Partial/proposed reviewer | `ReviewRequested`; `AssayPartialReviewRequested` on review/`asy_` streams | Aggregate/Candidate remain Partial with an unresolved review overlay; only exact OR-007 may satisfy it. |
| Assay `partial` / `assay_partial` with unresolved review | `ReviewDiscoveryOutcome / assay_partial`; `assay_outcome_review = request + assay_id + relation + Partial artefact + review subject` | Always `ReviewVerdictRecorded`; only a §4.2.3 policy-satisfying verdict emits `AssayPartialReviewed` on `asy_`; `CandidateAssayPartialReviewed` on Candidate | Satisfying branch becomes `partial_reviewed`; every other verdict leaves Partial unchanged and the gate closed; no branch relabels it complete or PROMOTE. |
| Assay `reviewed`, `partial_reviewed` or `cancelled_reviewed` / Candidate `parked`, `assay_partial_reviewed` or `assay_cancelled_reviewed` | `ProposeRevisitDecision / assay`; `discovery_revisit_proposal = Candidate + old assay + exact resolved outcome review + satisfied revisit predicate + proposed dec_id` | `DecisionProposed`; `AssayRevisitRequested` on old `asy_`; `CandidateRevisitRequested / assay` | Both projections become `revisit_pending`; no evidence collection opens. |
| Assay `revisit_pending` / `assay_revisit_pending` | `ResolveDecision / discovery_revisit`; exact prior relation/review/Decision; Stephen | `DecisionResolved`; `AssayRevisitResolved`; `CandidateRevisitResolved / assay` | `RETRY` -> both `retry_authorized`; PARK/KILL -> Candidate terminal and old Assay records option. |
| Assay `retry_authorized` / `assay_retry_authorized` | `RequestAssay` with old `asy_` predecessor plus new `asy_`, newly current accepted Assay bar | On new `asy_`: `AssayRequested`, `AssayEvidenceCollectionOpened`; on old `asy_`: `AssaySuperseded`; Candidate: `CandidateAssayRetryStarted` | One atomic transaction; new aggregate is collecting, old is superseded, Candidate is `assay_pending`. No window has a superseded old Assay without its replacement. |
| Spike `planned`, `approval_pending`, `authorized` or `running` / matching active Candidate state | `CancelDiscoveryEvaluation / spike`; `spike_cancellation = spike_id + plan relation + attempt/lease if any + reason/evidence hash + unresolved execution-proposal ref or null` | `SpikeCancelled`; `SpikeAttemptClosed / cancelled` and lease release when an attempt exists; `SpikeExecutionProposalSupersededByCancellation` when OR-015 is unresolved; `CandidateEvaluationCancelled / spike` | Old Spike/Candidate become `cancelled`/`spike_cancelled`; every attempt, lease and pending execution proposal is retired atomically; OR-040/OR-041 review the exact cancellation before revisit. |
| Spike `cancelled` / `spike_cancelled` | `RequestDiscoveryOutcomeReview / spike_cancelled`; exact cancellation, plan/attempt/lease/proposal-cleanup relation and proposed reviewer | `ReviewRequested`; `SpikeCancellationReviewRequested` on review/`spk_` streams | Cancellation remains terminal with one unresolved review overlay; only OR-041 may satisfy it. |
| Spike `cancelled` / `spike_cancelled` with unresolved review | `ReviewDiscoveryOutcome / spike_cancelled`; exact OR-040 subject and evidence-derived reviewer relationship | Always `ReviewVerdictRecorded`; only a §4.2.3 policy-satisfying verdict emits `SpikeCancellationReviewed`; `CandidateSpikeCancellationReviewed` | Satisfying branch becomes `cancelled_reviewed`/`spike_cancelled_reviewed`; every other verdict leaves cancellation unchanged and the gate closed; no stale attempt, lease or proposal may remain. |
| Spike `partial` / `spike_partial` | `RequestDiscoveryOutcomeReview / spike_partial`; exact aggregate/Partial/proposed reviewer | `ReviewRequested`; `SpikePartialReviewRequested` on review/`spk_` streams | Aggregate/Candidate remain Partial with an unresolved review overlay; only exact OR-021 may satisfy it. |
| Spike `partial` / `spike_partial` with unresolved review | `ReviewDiscoveryOutcome / spike_partial`; exact request/Spike relation/verdict/review subject | Always `ReviewVerdictRecorded`; only a §4.2.3 policy-satisfying verdict emits `SpikePartialReviewed`; `CandidateSpikePartialReviewed` | Satisfying branch becomes `partial_reviewed`; every other verdict leaves Partial unchanged and the gate closed; never PASS/complete; OR-019 already closed attempt/lease. |
| Spike `reviewed`, `partial_reviewed` or `cancelled_reviewed` / Candidate `parked`, `spike_partial_reviewed` or `spike_cancelled_reviewed` | `ProposeRevisitDecision / spike`; exact old Spike, resolved outcome review and satisfied revisit predicate | `DecisionProposed`; `SpikeRevisitRequested`; `CandidateRevisitRequested / spike` | Both become `revisit_pending`; no attempt/lease opens and no superseded execution proposal remains. |
| Spike `revisit_pending` / `spike_revisit_pending` | `ResolveDecision / discovery_revisit`; exact prior relation/review/Decision; Stephen | `DecisionResolved`; `SpikeRevisitResolved`; `CandidateRevisitResolved / spike` | `RETRY` -> both `retry_authorized`; PARK/KILL -> Candidate terminal and old Spike records option. |
| Spike `retry_authorized` / `spike_retry_authorized` | `RegisterSpikePlan` with old `spk_` predecessor plus new `spk_`, new immutable plan and current execution-subject proposal | On new `spk_`: `SpikePlanned`, `SpikeApprovalRequested`; old `spk_`: `SpikeSuperseded`; Candidate: `CandidateSpikeRetryStarted` | One atomic transaction; new aggregate is approval-pending, old is superseded, Candidate is `spike_approval_pending`. |

Cancellation never deletes evidence, resolves promotion, or silently resumes. A failed
replacement transaction leaves the old aggregate `retry_authorized`, not superseded.
A non-satisfying or withdrawn complete, Partial or cancellation review follows only
§4.2.3's explicit replacement/supersession route; recording that verdict never enables
promotion or revisit.
A conflicting retry cannot create a second replacement because the command binds the
old stream version, Candidate stream version, new aggregate ID, complete write set and
idempotency key. Any new attempt against a superseded, parked or killed aggregate is
rejected; a materially new idea after KILL is a new Candidate with explicit lineage.

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

The normative owner annex uses these exact abbreviations: `C:x`, `E:x`, `R:x`, `U:x`
and `P:x` expand to `ars://portfolio/command/x@1.0.0`,
`ars://portfolio/event/x@1.0.0`, `ars://portfolio/receipt/x@1.0.0`,
`ars://portfolio/reducer/x@1.0.0`, and `ars://portfolio/projection/x@1.0.0`.
`D:<kind>` means the accepted W2 Decision record plus the exact W11 subject-relation
schema `ars://portfolio/relation/<kind>@1.0.0`. `Review:*` similarly means the accepted
W2 review event plus the named W11 subject-relation schema. Stream names are exact IDs,
not aliases. In every row `OR-nnn`, the literal test fields are exactly
`positive_test_id: W11-T01-OR-nnn`,
`negative_mutation_test_id: W11-T03-OR-nnn-owner-row-mutation`, and
`retry_producer_test_id: W11-T11-OR-nnn`, plus the named relation-test family in the
last cell. Thus OR-001 binds all three `...OR-001...` literals and OR-140 binds all
three `...OR-140...` literals; the same textual equality applies to every listed row
in OR-001–OR-041 and OR-101–OR-140. A materialized catalogue contains the expanded
literal strings; there is no runtime-generated, family-wide or aliased test identity.

#### 4.2.1 Lifecycle and operational owner rows

| Owner row | Command/schema; eligible W4 profile and exact authority subject | Preconditions | Ordered events; streams/write set | Reducer → projection; receipt; additional test |
|---|---|---|---|---|
| OR-001 | `RegisterCandidate` (`C:register-candidate`); Scout or Portfolio Steward; `candidate_registration = Candidate ID/revision/hash + source-observation multiset hash` | Observations registered; identity/alias collision-free | `E:candidate-registered`; Candidate stream/object + project portfolio index | `U:candidate` → `P:candidate`; `R:register-candidate`; T12 |
| OR-002 | `SupersedeDiscoveryRecord/candidate` (`C:supersede-discovery-record`); Portfolio Steward; `candidate_supersession = predecessor + registered replacement + lineage/reason hash` | Replacement current; predecessor not terminally superseded | `E:candidate-superseded`; predecessor Candidate + project index | `U:candidate` → `P:candidate`; `R:supersede-discovery-record-candidate`; T04 |
| OR-003 | `RequestAssay/initial` (`C:request-assay`); Portfolio Steward; `assay_request = Candidate + new asy_id + AssayBarAcceptance + actual producer relation` | Candidate exactly `registered`; accepted current bar predates request | `E:assay-requested`, `E:assay-evidence-collection-opened` on new `asy_`; `E:candidate-assay-requested` on Candidate | `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:request-assay-initial`; T04 |
| OR-004 | `RecordAssayScore` (`C:record-assay-score`); Assay producer; `assay_evidence = asy_id + stored relation + scorecard art/hash` | Exact axis closure; producer still equals frozen bar relation | `E:assay-scored` on `asy_`; `E:candidate-assay-linked` on Candidate; artefact-use relation | `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:record-assay-score`; T05 |
| OR-005 | `RecordAssayPartial` (`C:record-assay-partial`); Assay producer; `assay_evidence = asy_id + stored relation + Partial art/hash` | Completed/unmet scope explicit; no PROMOTE; frozen relation equal | `E:assay-partial-recorded`; `E:candidate-assay-partial-linked`; artefact-use relation | `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:record-assay-partial`; T04 |
| OR-006 | `ReviewDiscoveryOutcome/assay_scored` (`C:review-discovery-outcome`); independent verifier; `assay_outcome_review = OR-034 request + asy_id + relation + scorecard + review subject` | Exact unresolved OR-034 request; scorecard exact; independence grade met; verdict evaluated by §4.2.3 | Always W2 `ReviewVerdictRecorded`; only if policy-satisfying, `E:assay-reviewed`; review then `asy_` | Always `U:review` → `P:review`; satisfying branch also `U:assay` → `P:assay`; `R:review-discovery-outcome-assay-scored`; T04 |
| OR-007 | `ReviewDiscoveryOutcome/assay_partial` (`C:review-discovery-outcome`); independent verifier; `assay_outcome_review = OR-035 request + asy_id + relation + Partial art/hash + review subject` | Exact unresolved request; Partial exact; independence grade met; verdict evaluated by §4.2.3 | Always W2 `ReviewVerdictRecorded`; only if policy-satisfying, `E:assay-partial-reviewed`, `E:candidate-assay-partial-reviewed`; review, then `asy_`/Candidate | Always `U:review` → `P:review`; satisfying branch also `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:review-discovery-outcome-assay-partial`; T04 |
| OR-008 | `CancelDiscoveryEvaluation/assay` (`C:cancel-discovery-evaluation`); Portfolio Steward; `assay_cancellation = asy_id + relation + reason/evidence hash` | Assay requested/collecting; not already terminal | `E:assay-cancelled`; `E:candidate-evaluation-cancelled` discriminant `assay`; `asy_`, Candidate | `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:cancel-discovery-evaluation-assay`; T04 |
| OR-009 | `ProposeRevisitDecision/assay` (`C:propose-revisit-decision`); Portfolio Steward; `discovery_revisit_proposal = Candidate + old asy_id + exact resolved outcome review + satisfied revisit predicate + proposed dec_id` | Exact partial-reviewed/cancelled-reviewed outcome or parked Candidate; no unresolved proposal | W2 `DecisionProposed`; `E:assay-revisit-requested`; `E:candidate-revisit-requested/assay`; Decision, `asy_`, Candidate | `U:decision`, `U:assay`, `U:candidate` → `P:decision`, `P:assay`, `P:candidate`; `R:propose-revisit-decision-assay`; T04 |
| OR-010 | `ResolveDecision/discovery_revisit_assay` (`C:resolve-decision`); Stephen; `discovery_revisit = dec_id + Candidate + old asy_id + relation + review` | Exact proposal; `RETRY`, `PARK` or `KILL` predicates | W2 `DecisionResolved`; `E:assay-revisit-resolved`; `E:candidate-revisit-resolved/assay`; Decision, `asy_`, Candidate | `U:decision`, `U:assay`, `U:candidate` → `P:decision`, `P:assay`, `P:candidate`; `R:resolve-decision-discovery-revisit-assay`; T08 |
| OR-011 | `RequestAssay/retry` (`C:request-assay`); Portfolio Steward; `assay_retry = Candidate + old/new asy_id + revisit Decision + current AssayBarAcceptance + producer relation` | Both old/Candidate `retry_authorized`; new ID unused | New `asy_`: requested/opened; old `asy_`: `E:assay-superseded`; Candidate: `E:candidate-assay-retry-started`; all in one batch | `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:request-assay-retry`; T04 |
| OR-012 | `ProposePromotionDecision/assay_to_spike` (`C:propose-promotion-decision`); Portfolio Steward; exact Candidate/asy/reviewed scorecard/proposed dec | Candidate `assay_scored`; no unresolved gate proposal | W2 `DecisionProposed`; `E:candidate-promotion-requested`; Decision, Candidate | `U:decision`, `U:candidate` → `P:decision`, `P:candidate`; `R:propose-promotion-decision-assay-to-spike`; T05 |
| OR-013 | `ResolveDecision/discovery_promotion_assay` (`C:resolve-decision`); Stephen; exact proposal/Candidate/asy/evidence | Option predicate and exact current streams | W2 `DecisionResolved`; `E:candidate-promotion-applied`; Decision, Candidate | `U:decision`, `U:candidate` → `P:decision`, `P:candidate`; `R:resolve-decision-discovery-promotion-assay`; T08 |
| OR-014 | `RegisterSpikePlan/initial` (`C:register-spike-plan`); Portfolio Steward; `spike_plan_registration = Candidate + new spk_id + plan art/hash + assay promotion Decision` | Candidate `spike_planning_authorized`; plan relation complete | New `spk_`: `E:spike-planned`, `E:spike-approval-requested`; Candidate: `E:candidate-spike-plan-linked` | `U:spike`, `U:candidate` → `P:spike`, `P:candidate`; `R:register-spike-plan-initial`; T04 |
| OR-015 | `ProposeSpikeExecutionDecision` (`C:propose-spike-execution-decision`); Portfolio Steward; `spike_execution_proposal = dec_id + spk_id + Candidate + plan + resource/route/assurance refs` | Spike approval-pending; no unresolved proposal | W2 `DecisionProposed`; `E:spike-execution-decision-requested`; Decision, `spk_` | `U:decision`, `U:spike` → `P:decision`, `P:spike`; `R:propose-spike-execution-decision`; T04 |
| OR-016 | `ResolveDecision/spike_execution_authority` (`C:resolve-decision`); Stephen; exact proposal/spk/Candidate/plan | Required route/resource/assurance current | W2 `DecisionResolved`; `E:spike-authorized`; `E:candidate-spike-authorized`; Decision, `spk_`, Candidate | `U:decision`, `U:spike`, `U:candidate` → `P:decision`, `P:spike`, `P:candidate`; `R:resolve-decision-spike-execution-authority`; T08 |
| OR-017 | `StartSpike` (`C:start-spike`); Operator/auditor; `spike_execution = spk_id + plan + authorization + lease/attempt/resource identities` | Authorized plan; live lease; attempt unused | `E:spike-started`; `E:candidate-spike-started`; `spk_`, attempt relation, Candidate | `U:spike`, `U:spike-attempt`, `U:candidate` → `P:spike`, `P:attempt-lease`, `P:candidate`; `R:start-spike`; T05 |
| OR-018 | `RecordSpikeVerdict/complete` (`C:record-spike-verdict`); Spike producer; `spike_evidence = spk_id + plan + attempt + verdict art/hash` | Exact evidence closure; PASS/FAIL truth table | `E:spike-verdict-recorded`; `E:candidate-spike-verdict-linked`; `spk_`, Candidate, artefact-use | `U:spike`, `U:candidate` → `P:spike`, `P:candidate`; `R:record-spike-verdict-complete`; T07 |
| OR-019 | `RecordSpikeVerdict/partial` (`C:record-spike-verdict`); Spike producer; `spike_evidence = spk_id + plan + attempt/lease + PARTIAL verdict art/hash` | Required unable/unmet scope explicit; verdict PARTIAL; attempt/lease live and exact | `E:spike-partial-recorded`; `E:spike-attempt-closed/partial`; lease released; `E:candidate-spike-partial-linked`; `spk_`, attempt/lease, Candidate, artefact-use | `U:spike`, `U:spike-attempt`, `U:candidate` → `P:spike`, `P:attempt-lease`, `P:candidate`; `R:record-spike-verdict-partial`; T07 |
| OR-020 | `ReviewDiscoveryOutcome/spike_verdict` (`C:review-discovery-outcome`); independent verifier; exact OR-036 request/verdict subject | Exact unresolved request; verdict exact; independence grade met; verdict evaluated by §4.2.3 | Always W2 `ReviewVerdictRecorded`; only if policy-satisfying, `E:spike-reviewed`; review then `spk_` | Always `U:review` → `P:review`; satisfying branch also `U:spike` → `P:spike`; `R:review-discovery-outcome-spike-verdict`; T07 |
| OR-021 | `ReviewDiscoveryOutcome/spike_partial` (`C:review-discovery-outcome`); independent verifier; `spike_outcome_review = OR-037 request + spk_id + relation + Partial art/hash + review subject` | Exact unresolved request; Partial exact; independence grade met; verdict evaluated by §4.2.3 | Always W2 `ReviewVerdictRecorded`; only if policy-satisfying, `E:spike-partial-reviewed`, `E:candidate-spike-partial-reviewed`; review, then `spk_`/Candidate | Always `U:review` → `P:review`; satisfying branch also `U:spike`, `U:candidate` → `P:spike`, `P:candidate`; `R:review-discovery-outcome-spike-partial`; T07 |
| OR-022 | `CancelDiscoveryEvaluation/spike` (`C:cancel-discovery-evaluation`); Operator/auditor; `spike_cancellation = spk_id + plan relation + attempt/lease if any + reason/evidence + unresolved OR-015 proposal or null` | Planned/approval/authorized/running; stop evidence current | `E:spike-cancelled`; conditional `E:spike-attempt-closed/cancelled`; lease released; conditional `E:spike-execution-proposal-superseded-by-cancellation`; `E:candidate-evaluation-cancelled/spike`; Decision when present, `spk_`, attempt/lease, Candidate | `U:decision`, `U:spike`, `U:spike-attempt`, `U:candidate` → `P:decision`, `P:spike`, `P:attempt-lease`, `P:candidate`; `R:cancel-discovery-evaluation-spike`; T04 |
| OR-023 | `ProposeRevisitDecision/spike` (`C:propose-revisit-decision`); Portfolio Steward; exact Candidate/old spk/resolved outcome review/satisfied revisit predicate/proposed dec | Partial-reviewed/cancelled-reviewed outcome or parked Candidate; no unresolved or cancellation-superseded proposal | W2 `DecisionProposed`; `E:spike-revisit-requested`; `E:candidate-revisit-requested/spike`; Decision, `spk_`, Candidate | `U:decision`, `U:spike`, `U:candidate` → `P:decision`, `P:spike`, `P:candidate`; `R:propose-revisit-decision-spike`; T04 |
| OR-024 | `ResolveDecision/discovery_revisit_spike` (`C:resolve-decision`); Stephen; exact proposal/Candidate/old spk/relation/review | `RETRY`, `PARK` or `KILL` predicates | W2 `DecisionResolved`; `E:spike-revisit-resolved`; `E:candidate-revisit-resolved/spike`; Decision, `spk_`, Candidate | `U:decision`, `U:spike`, `U:candidate` → `P:decision`, `P:spike`, `P:candidate`; `R:resolve-decision-discovery-revisit-spike`; T08 |
| OR-025 | `RegisterSpikePlan/retry` (`C:register-spike-plan`); Portfolio Steward; exact Candidate/old+new spk/revisit Decision/new plan | Old and Candidate retry-authorized; new ID unused | New `spk_`: planned/approval requested; old `spk_`: `E:spike-superseded`; Candidate: `E:candidate-spike-retry-started`; one batch | `U:spike`, `U:candidate` → `P:spike`, `P:candidate`; `R:register-spike-plan-retry`; T04 |
| OR-026 | `ProposePromotionDecision/spike_to_preregistration` (`C:propose-promotion-decision`); Portfolio Steward; exact Candidate/spk/reviewed verdict/proposed dec | Candidate verdict recorded; no unresolved gate proposal | W2 `DecisionProposed`; `E:candidate-promotion-requested`; Decision, Candidate | `U:decision`, `U:candidate` → `P:decision`, `P:candidate`; `R:propose-promotion-decision-spike-to-preregistration`; T05 |
| OR-027 | `ResolveDecision/discovery_promotion_spike` (`C:resolve-decision`); Stephen; exact proposal/Candidate/spk/evidence | Option predicate and current streams | W2 `DecisionResolved`; `E:candidate-promotion-applied`; Decision, Candidate | `U:decision`, `U:candidate` → `P:decision`, `P:candidate`; `R:resolve-decision-discovery-promotion-spike`; T08 |
| OR-028 | `AdmitResearchDossier` (`C:admit-research-dossier`); Operator/auditor R2; accepted external expected-set subject + candidate manifest | All §5 independent closure checks | `E:research-dossier-admitted`, deterministic `E:portfolio-object-registered`, `E:scope-definition-registered`; dossier/all objects/edges/scopes/project index | `U:dossier-admission`, `U:portfolio-object`, `U:scope-definition`, `U:project-index` → `P:dossier-admission`, `P:portfolio-catalogue`, `P:project-index`; `R:admit-research-dossier`; T09/T10 |
| OR-029 | `IngestScoutObservationBatch` (`C:ingest-scout-observation-batch`); Scout; batch + project + exact Candidate-blueprint multiset | Source/dedup/collision; no judgment | `E:scout-observation-ingested`, then explicit `E:candidate-registered`; batch and Candidate streams | `U:scout-observation`, `U:candidate` → `P:scout-observation`, `P:candidate`; `R:ingest-scout-observation-batch`; T12 |
| OR-030 | `IngestDiscoveryAnnotation` (`C:ingest-discovery-annotation`); Portfolio Steward; annotation bytes/hash + exact target | Attributed inbox writer; target current; dedup | `E:discovery-annotation-ingested`; annotation evidence stream only | `U:annotation` → `P:annotation-audit`; `R:ingest-discovery-annotation`; T13 |
| OR-031 | `RecordLegacyPortfolioObservation` (`C:record-legacy-portfolio-observation`); independent verifier/importer; path registration + physical file identity + bytes + parser | §7.3 handle-bound read; no adoption | `E:legacy-portfolio-path-observed`; observation artefact stream | `U:legacy-observation` → `P:legacy-observation-audit`; `R:record-legacy-portfolio-observation`; T14 |
| OR-032 | `TransitionPortfolioOwnership` (`C:transition-portfolio-ownership`); Operator/auditor; accepted mapping content/acceptance + observation + source row + targets + migration Decision | Exact stored relation; one current owner; versions/tail current | `E:portfolio-item-ownership-transitioned`; item ownership, exact targets, project index; never legacy path | `U:item-ownership`, `U:portfolio-object`, `U:project-index` → `P:successor-discovery`, `P:project-ownership`; `R:transition-portfolio-ownership`; T15/T16 |
| OR-033 | `CutOverDiscoveryPath` (`C:cut-over-discovery-path`); Operator/auditor; accepted cutover closure + cutover Decision + exact annotation epoch/fence | Closure current; §7.3 lock; writer revocation/final observation and pre-fence annotation epoch unchanged | `E:annotation-inbox-epoch-fenced`; `E:successor-annotation-epoch-activated`; `E:legacy-discovery-path-cutover-completed`; `E:path-registration-revised`; annotation/path/project registries | `U:annotation-epoch`, `U:path-registration`, `U:path-cutover` → `P:annotation-audit`, `P:path-registry`, `P:successor-discovery`; `R:cut-over-discovery-path`; T13/T18 |
| OR-034 | `RequestDiscoveryOutcomeReview/assay_scored` (`C:request-discovery-outcome-review`); Portfolio Steward; `assay_review_request = asy_id + relation + scorecard + proposed review ID/reviewer relation + prior-review supersession or null` | Assay scored; no unresolved review request; exact §4.2.3 supersession when a prior review exists; proposed reviewer independence plausible | W2 `ReviewRequested`; `E:assay-review-requested`; review stream, `asy_` | `U:review`, `U:assay` → `P:review`, `P:assay`; `R:request-discovery-outcome-review-assay-scored`; T04 |
| OR-035 | `RequestDiscoveryOutcomeReview/assay_partial` (`C:request-discovery-outcome-review`); Portfolio Steward; `assay_review_request = asy_id + relation + Partial art/hash + proposed review ID/reviewer relation + prior-review supersession or null` | Assay partial; no unresolved review request; exact §4.2.3 supersession when a prior review exists; reviewer independence plausible | W2 `ReviewRequested`; `E:assay-partial-review-requested`; review stream, `asy_` | `U:review`, `U:assay` → `P:review`, `P:assay`; `R:request-discovery-outcome-review-assay-partial`; T04 |
| OR-036 | `RequestDiscoveryOutcomeReview/spike_verdict` (`C:request-discovery-outcome-review`); Portfolio Steward; `spike_review_request = spk_id + relation + verdict art/hash + proposed review ID/reviewer relation + prior-review supersession or null` | Verdict recorded; no unresolved request; exact §4.2.3 supersession when a prior review exists; reviewer independence plausible | W2 `ReviewRequested`; `E:spike-review-requested`; review stream, `spk_` | `U:review`, `U:spike` → `P:review`, `P:spike`; `R:request-discovery-outcome-review-spike-verdict`; T07 |
| OR-037 | `RequestDiscoveryOutcomeReview/spike_partial` (`C:request-discovery-outcome-review`); Portfolio Steward; `spike_review_request = spk_id + relation + Partial art/hash + proposed review ID/reviewer relation + prior-review supersession or null` | Spike partial; no unresolved review request; exact §4.2.3 supersession when a prior review exists; reviewer independence plausible | W2 `ReviewRequested`; `E:spike-partial-review-requested`; review stream, `spk_` | `U:review`, `U:spike` → `P:review`, `P:spike`; `R:request-discovery-outcome-review-spike-partial`; T07 |
| OR-038 | `RequestDiscoveryOutcomeReview/assay_cancelled` (`C:request-discovery-outcome-review`); Portfolio Steward; `assay_cancellation_review_request = asy_id + relation + cancellation event/reason/evidence + proposed review ID/reviewer relation + prior-review supersession or null` | Assay cancelled; no unresolved review request; exact §4.2.3 supersession when a prior review exists; reviewer independence plausible | W2 `ReviewRequested`; `E:assay-cancellation-review-requested`; review stream, `asy_` | `U:review`, `U:assay` → `P:review`, `P:assay`; `R:request-discovery-outcome-review-assay-cancelled`; T04 |
| OR-039 | `ReviewDiscoveryOutcome/assay_cancelled` (`C:review-discovery-outcome`); independent verifier; exact OR-038 cancellation subject | Exact unresolved request; cancellation evidence exact; independence grade met; verdict evaluated by §4.2.3 | Always W2 `ReviewVerdictRecorded`; only if policy-satisfying, `E:assay-cancellation-reviewed`, `E:candidate-assay-cancellation-reviewed`; review, then `asy_`/Candidate | Always `U:review` → `P:review`; satisfying branch also `U:assay`, `U:candidate` → `P:assay`, `P:candidate`; `R:review-discovery-outcome-assay-cancelled`; T04 |
| OR-040 | `RequestDiscoveryOutcomeReview/spike_cancelled` (`C:request-discovery-outcome-review`); Portfolio Steward; `spike_cancellation_review_request = spk_id + plan/attempt/lease/proposal-cleanup relation + cancellation event/reason/evidence + proposed review ID/reviewer relation + prior-review supersession or null` | Spike cancelled; attempts/leases/proposals retired; no unresolved review request; exact §4.2.3 supersession when a prior review exists; reviewer independence plausible | W2 `ReviewRequested`; `E:spike-cancellation-review-requested`; review stream, `spk_` | `U:review`, `U:spike` → `P:review`, `P:spike`; `R:request-discovery-outcome-review-spike-cancelled`; T07 |
| OR-041 | `ReviewDiscoveryOutcome/spike_cancelled` (`C:review-discovery-outcome`); independent verifier; exact OR-040 cancellation subject | Exact unresolved request; cancellation and cleanup evidence exact; independence grade met; verdict evaluated by §4.2.3 | Always W2 `ReviewVerdictRecorded`; only if policy-satisfying, `E:spike-cancellation-reviewed`, `E:candidate-spike-cancellation-reviewed`; review, then `spk_`/Candidate | Always `U:review` → `P:review`; satisfying branch also `U:spike`, `U:candidate` → `P:spike`, `P:candidate`; `R:review-discovery-outcome-spike-cancelled`; T07 |

#### 4.2.2 External authority-lifecycle owner rows

These rows instantiate §3.6. “Content stream” below means the immutable candidate's
`obj_` stream; “authority stream” means the separately keyed acceptance projection.
Every review grant binds the exact content and file-observation identities plus the
reviewer's evidence-derived relationship. Every acceptance grant binds those same
identities, the exact review verdict and Decision subject. Neither role/profile alone
authorizes the row.

Catalogue materialization/review/acceptance is the sole pre-runtime exception and is
defined by §8.2's external Git/blob envelope, not by a self-hosted W11 lifecycle.
OR-140 records only the later one-time genesis import of that already accepted
envelope; it cannot propose, review, resolve or accept catalogue authority.

| Owner row | Command/schema; eligible W4 profile and exact subject | Preconditions | Ordered events; streams/write set | Reducer → projection; receipt; additional test |
|---|---|---|---|---|
| OR-101 | `RegisterAssayRubricContent` (`C:register-assay-rubric-content`); Research Designer; `assay_rubric_content = ID/revision/content hash + requirement refs` | Closed exact rubric; no acceptance fields/self file hash | `E:assay-rubric-content-registered`; rubric content stream | `U:authority-content` → `P:assay-bar-authority`; `R:register-assay-rubric-content`; T01 |
| OR-102 | `RegisterAssayEvidenceScopeContent` (`C:register-assay-evidence-scope-content`); Research Designer; `assay_evidence_scope_content = ID/revision/content hash + requirement refs` | Closed exact scope; no acceptance fields/self file hash | `E:assay-evidence-scope-content-registered`; scope content stream | `U:authority-content` → `P:assay-bar-authority`; `R:register-assay-evidence-scope-content`; T01 |
| OR-103 | `ObserveW11AuthorityFile/assay_rubric` (`C:observe-w11-authority-file`); independent verifier; exact rubric content + repository identity/bytes | Content exists; independent handle read; §3.6 C | `E:w11-authority-file-observed` discriminant `assay_rubric`; observation stream | `U:authority-file-observation` → `P:assay-bar-authority`; `R:observe-w11-authority-file-assay-rubric`; T01 |
| OR-104 | `ObserveW11AuthorityFile/assay_evidence_scope` (`C:observe-w11-authority-file`); independent verifier; exact scope content + repository identity/bytes | Content exists; independent handle read; §3.6 C | `E:w11-authority-file-observed` discriminant `assay_evidence_scope`; observation stream | `U:authority-file-observation` → `P:assay-bar-authority`; `R:observe-w11-authority-file-assay-evidence-scope`; T01 |
| OR-105 | `RequestW11AuthorityReview/assay_bar` (`C:request-w11-authority-review`); Portfolio Steward; exact rubric/scope contents + both file observations + proposed reviewer | Both C nodes current; reviewer unrelated to authors and prospective producer | W2 `ReviewRequested`; review stream | `U:review` → `P:assay-bar-authority`; `R:request-w11-authority-review-assay-bar`; T04 |
| OR-106 | `RecordW11AuthorityReview/assay_bar` (`C:record-w11-authority-review`); independent verifier; exact review subject | Complete rubric/scope/bar reconstruction; I1 relationship | W2 `ReviewVerdictRecorded`; review stream | `U:review` → `P:assay-bar-authority`; `R:record-w11-authority-review-assay-bar`; T04 |
| OR-107 | `ProposeW11AuthorityDecision/assay_bar_acceptance` (`C:propose-w11-authority-decision`); Portfolio Steward; `assay_bar_acceptance = rubric + scope + files + review + prospective producer relation + proposed dec_id` | Positive review current; no unresolved proposal | W2 `DecisionProposed`; Decision stream | `U:decision` → `P:decision`; `R:propose-w11-authority-decision-assay-bar-acceptance`; T04 |
| OR-108 | `ResolveDecision/assay_bar_acceptance` (`C:resolve-decision`); Stephen; exact OR-107 subject | Proposal exact; producer relationship acceptable; bar not stale | W2 `DecisionResolved`; `E:assay-bar-accepted`; Decision + Assay-bar authority streams | `U:decision`, `U:assay-bar` → `P:decision`, `P:assay-bar-authority`; `R:resolve-decision-assay-bar-acceptance`; T04 |
| OR-109 | `RecordAssayBarStaleness` (`C:record-assay-bar-staleness`); authority watcher/operator; `assay_bar_staleness = acceptance event + trigger evidence + effective time` | Accepted bar; exact staleness trigger true | `E:assay-bar-staled`; Assay-bar authority stream | `U:assay-bar` → `P:assay-bar-authority`; `R:record-assay-bar-staleness`; T04 |
| OR-110 | `RegisterDossierExpectedSetContent` (`C:register-dossier-expected-set-content`); Portfolio Steward; exact content + profile/requirement refs | Six literal families closed; no candidate-manifest input/self file hash/acceptance field | `E:dossier-expected-set-content-registered`; content stream | `U:authority-content` → `P:dossier-expected-set-authority`; `R:register-dossier-expected-set-content`; T09 |
| OR-111 | `ObserveW11AuthorityFile/dossier_expected_set` (`C:observe-w11-authority-file`); independent verifier; content + repository identity/bytes | OR-110 exists; independent handle read | `E:w11-authority-file-observed/dossier_expected_set`; observation stream | `U:authority-file-observation` → `P:dossier-expected-set-authority`; `R:observe-w11-authority-file-dossier-expected-set`; T09 |
| OR-112 | `RequestW11AuthorityReview/dossier_expected_set` (`C:request-w11-authority-review`); Portfolio Steward; content + file + reviewer | Reviewer unrelated to author/manifest/runtime producer | W2 `ReviewRequested`; review stream | `U:review` → `P:dossier-expected-set-authority`; `R:request-w11-authority-review-dossier-expected-set`; T09 |
| OR-113 | `RecordW11AuthorityReview/dossier_expected_set` (`C:record-w11-authority-review`); independent verifier; exact six-family subject | Independently reconstruct all rows/source authorities and file bytes | W2 `ReviewVerdictRecorded`; review stream | `U:review` → `P:dossier-expected-set-authority`; `R:record-w11-authority-review-dossier-expected-set`; T09 |
| OR-114 | `ProposeW11AuthorityDecision/dossier_expected_set_acceptance` (`C:propose-w11-authority-decision`); Portfolio Steward; content + file + review + dossier/profile scope + proposed dec | Positive review; candidate manifest not yet produced/observed | W2 `DecisionProposed`; Decision stream | `U:decision` → `P:decision`; `R:propose-w11-authority-decision-dossier-expected-set`; T09 |
| OR-115 | `ResolveDecision/dossier_expected_set_acceptance` (`C:resolve-decision`); Stephen; exact OR-114 subject | Temporal/producer separation current | W2 `DecisionResolved`; `E:dossier-expected-set-accepted`; Decision + expected-set authority streams | `U:decision`, `U:dossier-expected-set-authority` → `P:decision`, `P:dossier-expected-set-authority`; `R:resolve-decision-dossier-expected-set-acceptance`; T09 |
| OR-116 | `RegisterPathRegistrationContent` (`C:register-path-registration-content`); Operator/auditor; exact path content + observed physical identity | §7.2 fields complete; path/writer collisions absent | `E:path-registration-content-registered`; content stream | `U:path-registration` → `P:path-registration-candidate`; `R:register-path-registration-content`; T14 |
| OR-117 | `ObserveW11AuthorityFile/path_registration` (`C:observe-w11-authority-file`); independent verifier; content + canonical stored bytes | OR-116 exists; independent byte/physical identity verification | `E:w11-authority-file-observed/path_registration`; observation stream | `U:authority-file-observation` → `P:path-registration-candidate`; `R:observe-w11-authority-file-path-registration`; T14 |
| OR-118 | `RequestW11AuthorityReview/path_registration` (`C:request-w11-authority-review`); Operator/auditor; content + file + reviewer | Reviewer independent of registrant/projector/writers | W2 `ReviewRequested`; review stream | `U:review` → `P:path-registration-candidate`; `R:request-w11-authority-review-path-registration`; T14 |
| OR-119 | `RecordW11AuthorityReview/path_registration` (`C:record-w11-authority-review`); independent verifier; exact registration subject | Physical alias/writer/race matrix inspected | W2 `ReviewVerdictRecorded`; review stream | `U:review` → `P:path-registration-candidate`; `R:record-w11-authority-review-path-registration`; T14 |
| OR-120 | `ProposeW11AuthorityDecision/path_registration_acceptance` (`C:propose-w11-authority-decision`); Gate 6 Manager; content + file + review + proposed dec | Positive review; no collision/unproven identity | W2 `DecisionProposed`; Decision stream | `U:decision` → `P:decision`; `R:propose-w11-authority-decision-path-registration`; T14 |
| OR-121 | `ResolveDecision/path_registration_acceptance` (`C:resolve-decision`); Stephen; exact OR-120 subject | Exact proposal/current physical identity | W2 `DecisionResolved`; `E:path-registration-accepted`; Decision + path authority streams | `U:decision`, `U:path-registration` → `P:decision`, `P:path-registry`; `R:resolve-decision-path-registration-acceptance`; T14 |
| OR-122 | `RegisterLegacySourceInventoryContent` (`C:register-legacy-source-inventory-content`); migration analyst; exact source-only content + observation + parser/reproducer | Complete final-byte membership; no mapping/transition/cutover state | `E:legacy-source-inventory-content-registered`; content stream | `U:source-inventory` → `P:source-inventory-candidate`; `R:register-legacy-source-inventory-content`; T18 |
| OR-123 | `ObserveW11AuthorityFile/legacy_source_inventory` (`C:observe-w11-authority-file`); independent verifier; content + repository identity/bytes | OR-122 exists; independent file read | `E:w11-authority-file-observed/legacy_source_inventory`; observation stream | `U:authority-file-observation` → `P:source-inventory-candidate`; `R:observe-w11-authority-file-legacy-source-inventory`; T18 |
| OR-124 | `RequestW11AuthorityReview/legacy_source_inventory` (`C:request-w11-authority-review`); Gate 6 Manager; content + file + reviewer | Reviewer independent of inventory/parser producer | W2 `ReviewRequested`; review stream | `U:review` → `P:source-inventory-candidate`; `R:request-w11-authority-review-legacy-source-inventory`; T18 |
| OR-125 | `RecordW11AuthorityReview/legacy_source_inventory` (`C:record-w11-authority-review`); independent verifier; exact inventory subject | Independent final-byte reproduction and byte coverage agree | W2 `ReviewVerdictRecorded`; review stream | `U:review` → `P:source-inventory-candidate`; `R:record-w11-authority-review-legacy-source-inventory`; T18 |
| OR-126 | `ProposeW11AuthorityDecision/legacy_source_inventory_acceptance` (`C:propose-w11-authority-decision`); Gate 6 Manager; content + file + review + proposed dec | Positive review; zero unknown/unparseable/uncovered bytes | W2 `DecisionProposed`; Decision stream | `U:decision` → `P:decision`; `R:propose-w11-authority-decision-legacy-source-inventory`; T18 |
| OR-127 | `ResolveDecision/legacy_source_inventory_acceptance` (`C:resolve-decision`); Stephen; exact OR-126 subject | Proposal and final observation current | W2 `DecisionResolved`; `E:legacy-source-inventory-accepted`; Decision + inventory authority streams | `U:decision`, `U:source-inventory` → `P:decision`, `P:accepted-source-inventory`; `R:resolve-decision-legacy-source-inventory-acceptance`; T18 |
| OR-128 | `RegisterLegacyTransitionMappingContent` (`C:register-legacy-transition-mapping-content`); Portfolio Steward; accepted inventory row + observation + exact targets/collision scan | Source inventory accepted; no transition exists; no acceptance field/back-edge | `E:legacy-transition-mapping-content-registered`; content stream | `U:transition-mapping` → `P:transition-mapping-candidate`; `R:register-legacy-transition-mapping-content`; T15 |
| OR-129 | `ObserveW11AuthorityFile/legacy_transition_mapping` (`C:observe-w11-authority-file`); independent verifier; mapping content + repository identity/bytes | OR-128 exists; independent file read | `E:w11-authority-file-observed/legacy_transition_mapping`; observation stream | `U:authority-file-observation` → `P:transition-mapping-candidate`; `R:observe-w11-authority-file-legacy-transition-mapping`; T15 |
| OR-130 | `RequestW11AuthorityReview/legacy_transition_mapping` (`C:request-w11-authority-review`); Gate 6 Manager; mapping + file + reviewer | Reviewer unrelated to mapper/target producer | W2 `ReviewRequested`; review stream | `U:review` → `P:transition-mapping-candidate`; `R:request-w11-authority-review-legacy-transition-mapping`; T15 |
| OR-131 | `RecordW11AuthorityReview/legacy_transition_mapping` (`C:record-w11-authority-review`); independent verifier; exact source-row/observation/target/collision relation | Independently reload all relation members | W2 `ReviewVerdictRecorded`; review stream | `U:review` → `P:transition-mapping-candidate`; `R:record-w11-authority-review-legacy-transition-mapping`; T15 |
| OR-132 | `ProposeW11AuthorityDecision/migration_authority` (`C:propose-w11-authority-decision`); Gate 6 Manager; mapping + file + review + proposed dec | Positive review; target/collision scan current | W2 `DecisionProposed`; Decision stream | `U:decision` → `P:decision`; `R:propose-w11-authority-decision-migration-authority`; T15 |
| OR-133 | `ResolveDecision/migration_authority` (`C:resolve-decision`); Stephen; exact OR-132 subject | Proposal exact/current | W2 `DecisionResolved`; `E:legacy-transition-mapping-accepted`; Decision + mapping authority streams | `U:decision`, `U:transition-mapping` → `P:decision`, `P:accepted-transition-mapping`; `R:resolve-decision-migration-authority`; T15 |
| OR-134 | `RegisterLegacyCutoverClosureContent` (`C:register-legacy-cutover-closure-content`); migration analyst; accepted inventory + all mappings/acceptances/transitions + revocation/final observation/projection proofs | All per-item transitions complete; no own acceptance/file hash | `E:legacy-cutover-closure-content-registered`; content stream | `U:cutover-closure` → `P:cutover-closure-candidate`; `R:register-legacy-cutover-closure-content`; T18 |
| OR-135 | `ObserveW11AuthorityFile/legacy_cutover_closure` (`C:observe-w11-authority-file`); independent verifier; closure + repository identity/bytes | OR-134 exists; independent file read | `E:w11-authority-file-observed/legacy_cutover_closure`; observation stream | `U:authority-file-observation` → `P:cutover-closure-candidate`; `R:observe-w11-authority-file-legacy-cutover-closure`; T18 |
| OR-136 | `RequestW11AuthorityReview/legacy_cutover_closure` (`C:request-w11-authority-review`); Gate 6 Manager; closure + file + reviewer | Reviewer independent of inventory/mapping/transition/projector producers | W2 `ReviewRequested`; review stream | `U:review` → `P:cutover-closure-candidate`; `R:request-w11-authority-review-legacy-cutover-closure`; T18 |
| OR-137 | `RecordW11AuthorityReview/legacy_cutover_closure` (`C:record-w11-authority-review`); independent verifier; exact closure subject | Rebuild bijection/final bytes/revocation/race proof | W2 `ReviewVerdictRecorded`; review stream | `U:review` → `P:cutover-closure-candidate`; `R:record-w11-authority-review-legacy-cutover-closure`; T18 |
| OR-138 | `ProposeW11AuthorityDecision/legacy_path_cutover` (`C:propose-w11-authority-decision`); Gate 6 Manager; closure + file + review + proposed dec | Positive review; §7.3 identities still current | W2 `DecisionProposed`; Decision stream | `U:decision` → `P:decision`; `R:propose-w11-authority-decision-legacy-path-cutover`; T18 |
| OR-139 | `ResolveDecision/legacy_path_cutover` (`C:resolve-decision`); Stephen; exact OR-138 subject | Proposal/current closure; final lock recheck deferred to OR-033 | W2 `DecisionResolved`; `E:legacy-cutover-closure-accepted`; Decision + closure authority streams | `U:decision`, `U:cutover-closure` → `P:decision`, `P:accepted-cutover-closure`; `R:resolve-decision-legacy-path-cutover`; T18 |
| OR-140 | `ImportAcceptedW11CatalogueGenesis` (`C:import-accepted-w11-catalogue-genesis`); Operator/auditor holding the exact independently verified bootstrap grant; external `W11CatalogueAcceptanceEnvelope` + committed schema/catalogue bytes + bootstrap-contract identities | Stephen's external exact-byte acceptance current; bootstrap implementation independently verified against the accepted contract; no W11 genesis/catalogue state exists | `E:w11-catalogue-genesis-imported`; accepted catalogue authority + genesis provenance, and no review/Decision event | `U:schema-catalogue-genesis` → `P:accepted-schema-catalogue`; `R:import-accepted-w11-catalogue-genesis`; T03/T19 |

The reducer effect in each lifecycle row is the exact from-state/event/to-state edge in
§4.1/§4.1.1; the owner row and that matrix are one indivisible contract. OR-034–OR-038
and OR-040 add an unresolved review overlay without changing the outcome phase, while
OR-006, OR-007, OR-020, OR-021, OR-039 and OR-041 always close that request into its
exact W2 verdict state and update `P:review`; only §4.2.3's `satisfied` branch performs
the displayed outcome transition. Every other branch leaves the aggregate/Candidate
phase unchanged and permits only the policy's exact replacement route. In each ordinary authority row, content registration creates only `candidate`, file
observation adds only `observed`, review request/verdict adds `review_pending` then
the exact W2 policy state, proposal adds `decision_pending`, resolution adds
`accepted|rejected`, and OR-109 alone adds `stale`. OR-140 is different by design: it
imports an already externally accepted immutable envelope once and cannot create any
acceptance state. These are closed reducer states; no
materializer may leave the effect blank or map it to a different projection.

No generic `StatusChanged` or `DiscoveryUpdated` event is allowed. Rejection writes no
lifecycle event. A report, annotation, score, verdict, review, or process exit cannot
substitute for its owner row. The owner-row set is the literal complete W11 command,
event-producer, W4 subject, stream/write-set, reducer, projection, receipt and test
authority. `CandidateRegistered` deliberately has two producers, OR-001 and OR-029;
both invoke one exact registration validator/event schema/collision rule/reducer.
`W11AuthorityFileObserved`, W2 review events and W2 Decision events have only the
explicit discriminants listed in OR-103–OR-139. The catalogue's pre-runtime observation,
review and Stephen acceptance live only in the external envelope; OR-140 produces the
single genesis-import event. Every other W11-specific event has one
literal owner row. A future catalogue serializes these rows and materialized schema
hashes; it cannot add an implicit producer, reducer, projection or authority subject.

#### 4.2.3 Discovery outcome review-verdict effect policy

The closed policy `ars://portfolio/policy/discovery-outcome-review@1.0.0` applies to
exactly `assay_scored | assay_partial | assay_cancelled | spike_verdict |
spike_partial | spike_cancelled`. Recording a W2 verdict and satisfying the W11
lifecycle gate are separate effects. Every OR-006/007/020/021/039/041 execution records
the exact W2 verdict and updates `P:review`; only the policy's `satisfied` branch emits
an Assay/Spike/Candidate `*Reviewed` event or changes an outcome projection.

| W2 verdict | W2 Review projection under this policy | Assay/Spike/Candidate effect | Only next review route |
|---|---|---|---|
| `approve` | `satisfied` | Emit the row's exact `*Reviewed` events; the displayed `reviewed`, `partial_reviewed` or `cancelled_reviewed` transition occurs. | No further review request for the unchanged subject. |
| `approve_with_conditions` with every condition explicitly `non_blocking`, a named condition owner, due/review date and evidence ref, and no condition that changes the reviewed subject or cleanup proof | `satisfied`; conditions remain separately queryable audit obligations | Same satisfying events as `approve`; a condition cannot itself authorize promotion/revisit or amend evidence. | A later condition record is evidence only unless another command consumes it. |
| `approve_with_conditions` with any blocking, unknown, unowned, undated or subject-changing condition | `changes_requested` | No aggregate/Candidate `*Reviewed` event; underlying scored/verdict/Partial/cancelled outcome remains unchanged. | Exact superseding-subject or bounded-delta request below. |
| `changes_requested` | `changes_requested` | No aggregate/Candidate `*Reviewed` event; lifecycle gate remains closed. | Exact superseding-subject or bounded-delta request below. |
| `reject` | `verdict_recorded` and unsatisfied | No aggregate/Candidate `*Reviewed` event; lifecycle gate remains closed. | New request requires a superseding subject hash; same-subject retry is forbidden. |
| `unable_to_verify` | `verdict_recorded` and unsatisfied | No aggregate/Candidate `*Reviewed` event; lifecycle gate remains closed. | New request requires added verification evidence/capability in a superseding subject or explicit bounded delta. |
| `withdrawn` | `withdrawn` | No aggregate/Candidate `*Reviewed` event; lifecycle gate remains closed. | A same-subject replacement is allowed only with the withdrawn request/verdict refs, withdrawal reason and a different eligible reviewer relation. |

For a prior non-satisfying review, OR-034–038/040 requires a
`review_subject_supersession` containing the prior request/verdict IDs and hashes,
prior subject hash, new subject hash, exact changed evidence/condition-resolution refs,
reason, proposed reviewer relation and either `superseding_subject` or
`bounded_delta` mode. `bounded_delta` additionally binds the unchanged-base hash and
the exact accepted delta scope. It is invalid after `reject` without a new subject.
Except for the explicit `withdrawn` replacement above, equal old/new subject hashes
are rejected. A new request supersedes the closed prior review record; it never edits
or relabels that verdict. An unresolved request still forbids another request.

### 4.3 `AssayScorecard`

The Assay bar consists of two Stage-B contents and one later Stage-E acceptance. It is
not an abstract “accepted rubric” reference.

`ars://portfolio/assay-rubric-content` is a closed immutable `obj_` content with these
exact fields in addition to the common envelope:

- `rubric_id`, revision/content hash, accepted owner-requirement refs and domain-pack
  refs;
- ordered `axis_definitions[]`, each with `axis_id`, closed `axis_kind` of
  `gate | integer_score | registered_measure`, value schema/type, bounds or allowed
  set, required flag, evidence-type allowlist, validator schema ID/version and failure
  codes;
- required/forbidden axis sets and their P0 multiset hashes, evaluation order,
  recommendation predicates, hard-gate predicates, Partial predicates, PARK/KILL
  predicates and deterministic `RuleEvaluation` algorithm ID/version/hash;
- rubric source-authority refs, limitations, prohibited inferences and effective
  Candidate kinds/project scope.

`ars://portfolio/assay-evidence-scope-content` is a second closed immutable `obj_`
content with exact fields:

- `scope_id`, revision/content hash, rubric ID/revision/hash and accepted owner-
  requirement refs;
- required assurance lanes and required/optional evidence row sets. Each row fixes
  `evidence_key`, allowed source/artefact classes, exact identity/closure requirement,
  producer-capability/profile/context requirement, freshness interval or governing
  event position, validator ID/version/hash, independent-review grade, permitted
  omissions and stable unmet reason codes;
- closed prohibited-source classes, prohibited producer relationships, no-compensation
  pairs, confidentiality/permitted-consumer rules, stop conditions, Partial conditions,
  evidence-order constraints, scope closure algorithm/hash and effective Candidate
  kind/project/time interval.

Neither content contains a repository file/blob digest, reviewer, verdict, acceptor,
Decision/event reference, `accepted` flag, staleness state, actual Assay evidence or
scorecard identity. `AssayRubricContent` cannot accept a scorecard and
`AssayEvidenceScopeContent` cannot attest that its own evidence exists.

The external `AssayBarAcceptance` authority is formed only by the
`AssayBarAccepted` event from OR-108 after OR-101–OR-107. It binds the exact rubric and
evidence-scope IDs/revisions/content hashes, both independent
file observations, the exact positive review request/verdict, Stephen's Decision ID,
transaction ID, required-axis-set hash, evidence-scope closure hash, effective
Candidate kind/project/time, and one **prospective producer relation** containing the
named actor ID, profile ID/revision/hash, context profile ID/revision/hash, capability
grant ID/revision/hash, prohibited prior relationships and evidence-derived independence
grade. The reviewer is unrelated to both content authors and that prospective producer;
the acceptor is Stephen. Acceptance must occur before OR-003/OR-011 and before any
Assay evidence observation.

`RequestAssay` supplies the actual producer actor/profile/context/grant relation and
must equal the accepted prospective relation exactly. It stores on `AssayRequested` the
bar acceptance event/Decision/transaction, exact rubric/scope contents and file
observations, required-axis/scope hashes, Candidate identity, `assay_id`, producer
relation, and one canonical `assay_relation_hash`. Its preimage is the P0 canonical
`AssayRequestRelation` object containing exactly Candidate ID/revision/content hash,
`assay_id`, Assay-bar acceptance event/Decision/transaction IDs, rubric and scope
IDs/revisions/content hashes, both file-observation IDs/hashes, required-axis-set hash,
scope-closure hash, every prospective/actual producer actor/profile/context/grant ID,
revision and hash, creating command ID and idempotency key. It excludes
`assay_relation_hash`, the enclosing event/record/content hashes and every later
scorecard, review, Decision or acceptance. A missing,
class-only or newly selected producer is unequal. `evidence_collecting` begins only
after this relation and the later-ordered `AssayEvidenceCollectionOpened` commit in the
same request batch. Every later Assay command independently loads the stored relation;
command, scorecard or runtime values cannot select, swap or narrow the bar.

`RecordAssayBarStaleness` is mandatory when any rubric/scope content is superseded;
owner requirement, domain pack, validator or producer grant/profile/context changes;
review evidence expires; the independence relationship changes; or the effective
project/kind/time scope ends. `AssayBarStaled` affects future requests only. A request
fails if staleness predates its commit. An already opened Assay retains its frozen bar
for audit but stops/records Partial if a safety or authority revocation makes continued
collection invalid; it never silently swaps to a later bar.

The prospective `ars://portfolio/assay-scorecard` artefact payload schema is closed and
requires a W2 `art_` manifest plus:

- exact Candidate ID/revision/hash;
- exact `assay_id`, creating `AssayRequested` event/hash, and stored
  `assay_relation_hash`;
- exact `AssayRubricContent` and `AssayEvidenceScopeContent` IDs/revisions/hashes,
  external `AssayBarAcceptance` Decision/event, both file observations, prospective/
  actual producer relation, and required-axis/scope hashes frozen by `RequestAssay`;
- ordered `axis_results`, each with exact `axis_id`, closed `axis_kind` of
  `gate | integer_score | registered_measure`, typed `value`, accepted bounds or
  allowed set, rationale, evidence refs, unmet-condition codes, and validator ID/hash;
- exact required-axis-set hash and observed-axis-set hash;
- `mechanical_recommendation: PROMOTE | PARK | KILL | UNABLE_TO_SCORE`;
- `rule_evaluation_ref`, limitations, and prohibited inferences;
- producer actor/profile/context and review requirements.

`AssayScored` is accepted only when the observed axis IDs are a one-to-one exact match
to the externally accepted rubric content: no missing, extra, duplicate, aliased, reordered-as-different,
or wrong-typed axis. Bounds and decision predicates are equality-checked, not copied
from producer prose. An incomplete Assay uses `AssayPartialRecorded` and cannot emit a
PROMOTE recommendation. A late rubric acceptance, post-request rubric/scope/axis-set
swap, scorecard from another Assay for the same Candidate, or coordinated command and
scorecard mutation rejects against the stored request relation.

The closed `ars://portfolio/assay-partial` artefact repeats the exact `assay_id`,
Candidate/rubric/evidence-scope/Assay-bar-acceptance refs and stored request relation hash, then lists
completed axes/evidence, unmet axes/evidence, stable reason codes, limitations and
revisit requirements. It forbids a PROMOTE recommendation and cannot be attached to a
different Assay during revisit or supersession.

Assay outcome review is two-stage. OR-034/OR-035 fixes an exact scorecard or Partial
artefact, aggregate relation, proposed reviewer and evidence-derived independence
subject in W2 `ReviewRequested`. OR-006/OR-007 can record a verdict only against that
unresolved request. Only a §4.2.3 policy-satisfying verdict makes a complete scorecard
`reviewed` or a Partial `partial_reviewed`; every other verdict changes only the Review
projection and follows the explicit supersession route.

Cancellation review is equally subject-specific. OR-038 freezes the exact
`AssayCancelled` event, reason/evidence hash, aggregate relation and proposed reviewer;
OR-039 alone may satisfy it, and only on a §4.2.3 policy-satisfying verdict does it
project `cancelled_reviewed`. OR-040 freezes the exact
`SpikeCancelled` event together with the plan, attempt/lease closure and any
execution-proposal supersession; OR-041 alone may satisfy it and likewise projects
`cancelled_reviewed` only on the satisfying branch. A Partial review, complete-outcome review or cancellation record
from another aggregate is not substitutable. `ProposeRevisitDecision` accepts only the
resolved exact review appropriate to the terminal outcome whose W2 projection is
`satisfied` under the named policy.

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
| `verdict` | Closed enum `{PASS, FAIL, PARTIAL}`. |
| `success_predicates[]` / `failure_predicates[]` | Every accepted-plan predicate with closed status `{passed, failed, unable_to_evaluate}` and evidence refs. |
| `kill_conditions[]` | Every accepted-plan kill condition with closed status `{triggered, not_triggered, unable_to_evaluate}`, evidence refs, and consequence. |
| `artefact_refs[]`, `validation_refs[]` | Exact immutable identities/hashes; producer assertions are not validators. |
| `completed_scope`, `unmet_scope`, `limitations` | Non-empty and typed where PARTIAL or FAIL. |
| `mechanical_recommendation` | Closed enum `{PROMOTE, PARK, KILL, NONE}`; evidence only. |
| `prohibited_inferences[]` | Must include no dispatch/result/claim authority. |

PASS requires all required success predicates passed, no failure predicate satisfied,
and every kill condition `not_triggered`. FAIL requires a named failure predicate or
triggered kill condition. Any required `unable_to_evaluate`, missing evidence, or
incomplete scope forces PARTIAL. Neither PASS nor FAIL deletes artefacts; both are
valid evidence outcomes.

Spike outcome review follows the same distinct request/satisfaction discipline:
OR-036/OR-037 emit exact W2 `ReviewRequested` subjects for a verdict or Partial;
OR-020/OR-021 alone record the verdict. A Partial review produces
`SpikePartialReviewed`, not `SpikeReviewed`, and never satisfies the PASS predicate.

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
bar permits PROMOTE; Stephen may still select PARK or KILL. An Assay Partial or
cancellation uses only the reviewed `discovery_revisit` path in §4.1.1; RETRY creates a
new Assay and PARK/KILL closes the current route. At
`spike_to_preregistration`, PROMOTE requires `SpikeVerdict=PASS`; PARTIAL can only PARK
or RETRY through the reviewed `discovery_revisit` path, and a FAIL with a triggered kill condition can only
KILL. A FAIL without a kill condition may PARK or KILL according to the accepted plan.
No human option may compensate for missing required evidence or a triggered hard gate.

## 5. Dossier admission interface

### 5.1 `DossierExpectedSetContent` and external acceptance

`ars://portfolio/dossier-expected-set-content` is a closed immutable Stage-B `obj_`
content candidate, not the dossier producer's manifest and not the generic W11
interface catalogue. Each content applies to exactly one dossier logical ID/revision,
package version, admission-profile ID/revision/hash and effective project/scope. It must
literally list every expected member; globs, discovery rules, count-only claims,
optional unlisted members and producer-populated defaults are forbidden.

The content contains the common object envelope plus:

- `expected_set_id`, revision/content hash, dossier/profile scope, effective interval,
  accepted owner-requirement refs and source-authority refs;
- author/producing-context identity, with no review/acceptance claim;
- `component_count`, `source_count`, `object_count`, `scope_count`, `edge_count` and
  `relationship_count`, plus an exact P0 canonical multiset hash for each family;
- one complete literal array for each row family below and one overall
  `expected_set_closure_hash` over the complete rows, owner requirements and profile
  scope.

It expressly forbids its own repository path, Git commit/blob, serialized byte length/
SHA-256, file-observation event, review/Decision/event, acceptor, acceptance time,
`authored_before_candidate_observation` verdict, candidate manifest or runtime registry
identity. Those facts can exist only later in the §3.6 graph.

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
file names. A valid foreign member with the same kind is unequal. The content author may
not derive any row from a candidate manifest, candidate command, runtime registry or
implementation enumerator.

OR-110–OR-115 then construct the external authority in order:

1. `DossierExpectedSetContentRegistered` stores the exact content identity/hash and
   owner-requirement subject without claiming review or acceptance.
2. `W11AuthorityFileObserved/dossier_expected_set` independently reads the serialized
   content and records exact repository path, Git commit/blob, file length/SHA-256 and
   the already-computed content identity/hash. This observation is not inside the file.
3. `ReviewRequested` fixes that content/file pair and a reviewer relationship. The
   independent reviewer reconstructs all six literal multisets from separately accepted
   dossier/profile requirements and source authorities, re-resolves the file, and emits
   `ReviewVerdictRecorded` with relationship evidence. The reviewer is unrelated to the
   content author and to manifest/component/source/runtime producers.
4. `DecisionProposed` fixes the same pair/review/dossier/profile scope. Stephen's
   `ResolveDecision/dossier_expected_set_acceptance` atomically emits
   `DecisionResolved` and `DossierExpectedSetAccepted`. The acceptance event contains
   content ID/revision/hash, file-observation ID/hash, review ID/verdict/hash, Decision
   ID, transaction ID, dossier/profile/project scope, acceptor and effective time. It
   contains no own or sibling event hash.
5. The resolver proves the Stage-B content registration, file observation, positive
   review and acceptance all precede creation or first observation of the candidate
   `ResearchDossierManifest`. Expected component/source identities came from Stage-A
   requirements/source authorities, never from that manifest or its runtime enumerator.

The complete literal acceptance authority is therefore the tuple
`(DossierExpectedSetContent, W11AuthorityFileObserved, ReviewVerdictRecorded,
DossierExpectedSetAccepted)`, with exact identities/hashes and stored relations. A
content-only or acceptance-event-only reference is insufficient. Changing any content
row, serialized byte, owner requirement, file observation, reviewer relationship or
scope requires a new topological sequence before any new candidate observation.

This temporal and producer separation is non-compensable. Agreement among a manifest,
command and runtime registry cannot establish completeness when any external expected
authority stage is absent, later-authored, producer-related, byte-mismatched or cyclic.

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
- exact `DossierExpectedSetContent` ID/revision/content hash, its independent
  file-observation ID/hash and repository/Git/blob/file identity, review ID/verdict/hash,
  external `DossierExpectedSetAccepted` Decision/event/transaction, and accepted
  admission-profile identity;
- proposed portfolio object IDs/revisions/hashes and ScopeDefinition IDs/revisions/
  hashes;
- complete affected stream write set with expected versions;
- expected project global position/tail hash;
- actor, authority grant, idempotency key, reason, and governing Decision refs;
- explicit `ownership_effect: successor_owned_new_objects_only`.

The command supplies no authoritative expected counts, key-set hashes, member rows or
relationship rows. The handler derives all expectations solely from the independently
accepted external expected-set tuple; any duplicate command convenience fields must be
absent, not compared to another producer-controlled copy.

It cannot accept a payload-supplied “validated” flag, infer acceptance from a vault
status, adopt a legacy item, resolve a PromotionDecision, issue a Dispatch, or promote
a claim.

### 5.4 Exact closure and atomic publication algorithm

The future handler must perform these steps in order:

1. Validate the envelope/payload and independently resolve the accepted admission
   profile and complete external expected-set tuple: Stage-A requirement,
   `DossierExpectedSetContent`, its registration event, independent file observation,
   review request/verdict, Decision and `DossierExpectedSetAccepted`. Recompute content
   and file hashes; verify the §3.6 DAG has no self/back edge or SCC, verify author/
   reviewer/runtime-producer separation, and verify acceptance predates candidate
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
6. Recompute expected-content and candidate-manifest closures independently. The
   accepted external expected tuple remains fixed while manifest, command and runtime sides are
   mutated; compare the candidate closure with the manifest and accepted external
   expected-set tuple.
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
external expected-set tuple. Separate attacks cover each source dependency being missing,
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
allowlist is `RegisterCandidate`, `SupersedeDiscoveryRecord/candidate`,
`RequestAssay`, `CancelDiscoveryEvaluation/assay`,
`ProposeRevisitDecision`, `ProposePromotionDecision`, `RegisterSpikePlan`,
`ProposeSpikeExecutionDecision`, `RequestDiscoveryOutcomeReview` with exactly the six
discriminants `assay_scored | assay_partial | assay_cancelled | spike_verdict |
spike_partial | spike_cancelled`, `IngestDiscoveryAnnotation`, and only the content/
review/Decision-proposal rows that explicitly name Portfolio Steward in OR-101–OR-139.
It has no free-standing Assay/Spike supersession permission: OR-011/OR-025 create the
replacement and supersede the old aggregate atomically under the exact revisit
Decision. Preparing a dossier, expected set, inventory, mapping, cutover closure or
transition proposal is content/artefact production, not permission to execute its
acceptance/admission/migration command. The Operator/auditor profile's complete W11
allowlist is `StartSpike`, `CancelDiscoveryEvaluation/spike`,
`AdmitResearchDossier`, `TransitionPortfolioOwnership`, `CutOverDiscoveryPath`,
`RegisterPathRegistrationContent`, `RequestW11AuthorityReview/path_registration`, and
`ImportAcceptedW11CatalogueGenesis`; the final command additionally requires the exact
independently verified bootstrap grant and accepted external envelope bound by OR-140.
The other owner rows use the exact profiles and grants stated there; every unlisted
command remains denied.

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

`ars://portfolio/path-registration-content` is a strict immutable Stage-B content with:

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
- initial-state predicate `legacy_active` for the legacy authority path or
  `not_applicable` for annotation/combined/projection roles, plus the exact Stage-A
  registration requirement. It contains no current cutover state, review, acceptance,
  own serialized-file identity or governing Decision/event.

OR-116–OR-121 externally register, observe, review and accept the content. The accepted
`PathRegistration` authority is the exact content/file/review/acceptance tuple. Its
current state `legacy_active | cutover_pending | successor_active | retired |
not_applicable` is projected only from `PathRegistrationAccepted`, later cutover
proposal/Decision and `PathRegistrationRevised` events.

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

The registered annotation root contains one current epoch directory. Every epoch has
an immutable `annotation_epoch_id`, directory volume/file identity, path-registration
revision/hash, attributed-writer grant-set hash, activation event position and closed
status `active | fenced`. Each annotation payload repeats its epoch ID. Writers resolve
the current epoch from the accepted path registry and may write only that directory;
an old/fenced/foreign epoch is rejected at ingestion. Subdirectories are physical
partitions within the required `00-Meta/ARS/Discovery-annotations/` namespace, not new
authority paths.

`IngestDiscoveryAnnotation` verifies path role, writer attribution, schema, exact bytes,
target identity, dedup/idempotency, and staleness before recording
`DiscoveryAnnotationIngested`. Ingestion preserves the human proposal but does not apply
it. Any object revision, dependency change, promotion, claim action, or migration still
requires its separately authorized command. Projectors never “round-trip” edits from
generated pages.

Whole-path cutover follows §7.6.2: it freezes one observed legacy epoch in the accepted
closure, re-observes it under its directory/registry lock, then atomically fences it and
activates a fresh successor epoch. A pre-fence member delta invalidates the closure.
Post-fence annotations resolve the successor epoch and target successor object
revisions, so they remain ordinary un-ingested evidence after cutover rather than being
lost or retroactively added to the legacy closure.

Manual edits under `00-Meta/ARS/Discovery/` or the combined path produce projection
drift diagnostics and are discarded on rebuild; they are never treated as annotations.

### 7.5 Per-item ownership transition

Observation, source-inventory acceptance, mapping acceptance and transition are
topologically ordered distinct authorities:

1. `LegacyRecordObserved` is an immutable `art_` observation produced from a
   handle-bound read. It contains observation ID/hash, exact path registration,
   physical source identity, complete-file bytes/hash, parser ID/version/hash, a typed
   source-item selector (byte range plus raw-row hash), source item ID/type/aliases,
   observed row bytes/hash, observation time and explicit non-inferences. It adopts
   nothing.
2. An accepted `LegacySourceInventoryContent` from §7.6 binds the source bytes and
   source-only item row. It contains no target, owner-transition, mapping, Decision or
   cutover member.
3. `ars://portfolio/legacy-transition-mapping-content` is a later closed immutable
   Stage-B `obj_` relation. Each literal content binds the accepted source-inventory
   content/file/review/acceptance tuple and one source item-row hash, one exact
   `LegacyRecordObserved` ID/hash and typed selector, source path/bytes/item/aliases,
   one target-mode enum, the complete target object ID/revision/content-hash set, alias
   mapping, collision-scan ID/hash, Stage-A transition-policy refs, and no Decision,
   review, acceptance, transition event or cutover member. Its
   `transition_relation_hash` is SHA-256 over a separate P0 canonical
   `LegacyTransitionRelation` containing exactly the accepted source-inventory
   content/file/review/acceptance IDs and hashes, source-row ID/selector/raw-row hash,
   `LegacyRecordObserved` ID/hash, source path/bytes/item/aliases, target mode, sorted
   target object ID/revision/content-hash set, alias mapping, collision-scan ID/hash and
   transition-policy refs. The preimage excludes `transition_relation_hash`, the
   enclosing `content_hash`, every mapping file/review/Decision/acceptance hash and all
   transition/cutover event hashes.
4. OR-128–OR-133 independently observe/review that content and resolve a separate
   `migration_authority` Decision. `LegacyTransitionMappingAccepted` binds the content,
   file observation, review, Decision, scope and relation hash. It is not serialized
   inside the mapping content and the source inventory has no back-reference to it.
5. `TransitionPortfolioOwnership` references the exact accepted mapping tuple and
   relation hash; it does not resubmit authoritative source/target members. The handler
   independently loads the source-inventory item, observation, target objects,
   collision scan, mapping content/file/review/acceptance, Decision and path
   registration, recomputes the relation, and requires one literal equality before
   allocating an idempotency outcome, stream version or event position.

The strict command payload therefore contains accepted mapping-content and external-
acceptance identities/hashes, item ID, exact current/target mode, observation ID/hash,
governing migration Decision,
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
accepted mapping-content/external-acceptance/relation hashes, source-inventory content/
acceptance/item-row hash, observation/selector/hash,
before/after owner, target identities, migration Decision subject, effective event
position, and attributed authority. The legacy file is not edited by this command.
Remaining legacy items continue to use it as authority; the transitioned item appears
only in the successor projection with an explicit legacy lineage link.

The physical legacy path remains legacy-written during a partial cutover, but its
authority is item-scoped. For a transitioned item, the exact source row/bytes recorded
by the transition become frozen lineage; any later legacy edit to that item's row is a
diagnostic observation only and cannot regain authority or update the successor object.

### 7.6 Whole-path cutover

#### 7.6.1 Source-only inventory authority

`ars://portfolio/legacy-source-inventory-content` is the complete content-addressed
membership description of one exact observed legacy file. It is a Stage-B closed
immutable `obj_` containing:

- inventory ID/revision/content hash; accepted path-registration tuple; registered-root
  and opened physical volume/file identities; source byte length/SHA-256; and exact
  upstream `LegacyPortfolioPathObserved` artefact/event;
- membership-rule ID/revision/content hash; parser schema ID/version; parser
  implementation repository path/Git blob/file SHA-256; independently implemented
  reproducer ID/version/repository blob/file SHA-256 and exact reproducer command/
  environment identity; byte-range/row-selector semantics and structural-byte rules;
- a complete literal one-to-one source-only `items[]` array. Each row has stable source
  row ID, legacy item ID/type, scoped aliases, typed byte selector, raw row length/hash,
  observed-record ID/hash, source order and source-status text as untrusted bytes.
  Unknown/unparseable regions are blocker rows, never omissions;
- item count, ordered item-key hash, row-multiset hash, alias-multiset hash, structural-
  byte multiset hash, uncovered-byte set, unknown/unparseable/duplicate/alias-collision
  sets, parser diagnostics, per-row reproducer results and overall membership closure
  hash; and
- producer actor/profile/context and independently compiled reproducer context.

It contains **no** current/successor owner, target, expected mapping, mapping hash,
Decision, transition state/event, writer revocation, cutover closure, review/acceptance,
own serialized repository path/blob/file digest, or `accepted` field. This exclusion is
schema-enforced, not prose convention.

The independent reproducer opens and reads the same source file to final byte using
§7.3, parses from those bytes rather than the producer inventory, and returns the
complete literal row/structural-byte multisets plus unknown-byte coverage. It must
agree on physical file identity/hash, every selector, item/alias multiset and membership
hash. It may not consume the producer's row list or parser output as its expected side.
A coordinated omission by two invocations of one parser family, missing byte range,
unknown heading, alias collision, overlapping selector or uncovered non-whitespace byte
blocks review/acceptance. The independent reviewer additionally proves that item
selectors plus explicitly classified structural bytes cover the complete file.

OR-122–OR-127 then register the inventory content, independently observe the inventory
file itself, review it and emit external `LegacySourceInventoryAccepted`. The accepted
tuple is content + file observation + review + Decision/acceptance event. The source
observation is an upstream dependency inside content; the inventory-file observation is
a later dependency outside content. They are different records and neither hashes
itself.

#### 7.6.2 Acyclic mapping, transition, and cutover closure

The complete hash/lifecycle DAG is:

```text
per-item branch while legacy remains active:
  source observation -> source-only inventory acceptance
    -> mapping-content acceptance -> transition event

cutover branch after legacy-writer revocation:
  revocation -> independent final source observation
    -> cutover source-only inventory acceptance
    -> any still-missing mapping-content acceptances/transition events

annotation branch before closure:
  accepted annotation-path registration -> legacy annotation-epoch observation
    -> complete member/ingestion/rejection reconciliation -> empty pending-set hash

join only after every cutover-inventory row is closed:
  cutover inventory + all exact mapping acceptances + all transition events
    + revocation + final observation + accepted annotation epoch + rebuild/race proofs
    -> LegacyCutoverClosureContent
    -> closure file observation -> review -> LegacyCutoverClosureAccepted
    -> CutOverDiscoveryPath re-observation/fence -> successor annotation epoch
```

There is no reverse edge. An inventory never names a mapping; a mapping never names its
own acceptance/transition; a transition event never names the later closure; and the
closure never appears inside its own file observation/review/Decision. A topological
sort over exact identities/hashes must yield the displayed order.

For a whole-path campaign, legacy writers are first stopped, handles drained and their
grants/write authorities revoked under a separately observed revocation snapshot. An
independent final observer then holds the §7.3 handle/lock, reads the legacy file to
final byte, records `LegacyPortfolioPathObserved`, and produces/accepts the cutover
`LegacySourceInventoryContent`. Mappings and remaining transitions follow that accepted
source inventory. Earlier partial-transition mappings may reference an earlier accepted
inventory only when their exact source row ID/selector/raw hash is byte-identical to the
cutover inventory row; any post-transition edit to that row blocks cutover and requires
explicit owner remediation, never inferred adoption.

After every row has an accepted mapping and transition event, OR-134 creates
`ars://portfolio/legacy-cutover-closure-content`. This Stage-B content binds:

- the cutover inventory content/file/review/acceptance tuple and final source
  observation, including exact physical identity/bytes/membership closure;
- a literal one-to-one row array binding each cutover-inventory source row to exactly
  one mapping content/file/review/acceptance tuple and exactly one
  `PortfolioItemOwnershipTransitioned` event to `successor_owned|closed_reference`;
- zero-extra/zero-missing multiset hashes across inventory rows, mapping rows and
  transition events, plus all valid earlier-inventory row-equivalence proofs;
- the writer-revocation snapshot, drained-handle proof, collision scan, current
  path-registration acceptance, and one `AnnotationInboxEpochObservation` containing
  the annotation path-registration ID/revision/hash, legacy epoch ID and directory
  volume/file identity, writer-grant-set hash and event position, a complete sorted
  member array of file path/length/SHA-256 plus ingestion-or-rejection event refs, and
  an exact pending-set hash (necessarily the accepted empty-set hash),
  successor/optional-combined rebuild proofs, projector identities, source positions,
  deletion/rebuild results, §7.3 race results and one-way target state; and
- producer identity, effective interval and owner-requirement refs.

It contains no own repository/blob/file hash, review, acceptance, Decision or cutover
event. OR-135–OR-139 separately observe/review/accept it. The legacy backlog can move
from `legacy_active` to `successor_active` only when that accepted closure proves:

1. the cutover source inventory is complete, independently reproduced/reviewed and
   accepted, with no unknown/unparseable/uncovered/duplicate/foreign/alias-collision row;
2. its stored source-row → accepted-mapping → transition-event relation is a bijection,
   every target is `successor_owned|closed_reference`, and there is no extra item/event;
3. legacy writer revocation is effective and every handle is drained;
4. final source bytes/physical identity equal the accepted cutover inventory, and no
   write/rename/parent/reparse/byte change occurred after the final observation;
5. every member of the accepted legacy annotation epoch is ingested or explicitly
   rejected, its pending-set hash is empty, projections rebuild without reading their
   output, and collision/deletion/operation-time race tests pass; and
6. Stephen's exact `legacy_path_cutover` Decision accepts that closure tuple.

`CutOverDiscoveryPath` accepts only the closure content/file/review/acceptance tuple; it
does not accept a caller-supplied inventory/event list. While holding the §7.3 verified
path lock and the registered annotation-epoch parent/directory locks, it reloads and
rehashes the full DAG, final observation, revocation and bijection. It then re-enumerates
the legacy annotation epoch from raw directory handles and requires exact equality of
epoch ID, directory identity, writer-grant/event position, every member identity and the
accepted empty pending-set hash. Any pre-fence delta rejects before publication.

On equality, one atomic registry/event transaction revokes the old epoch's attributed-
writer grants, records `AnnotationInboxEpochFenced`, activates a fresh successor epoch
and grants, records `SuccessorAnnotationEpochActivated`, then records
`LegacyDiscoveryPathCutoverCompleted` and `PathRegistrationRevised`. Human writers
resolve only the registry's current epoch. Files created after the fence therefore name
the successor epoch and successor object revision and are processed after cutover; the
legacy epoch is read-only and cannot receive a late member. The locks are held through
the commit point, so there is no between-observation-and-fence window.

Any missing/back/cyclic edge, omitted item, extra transition, same-parser omission,
post-observation write, annotation-epoch delta, stale byte or writer/reparse race leaves
the legacy path and legacy annotation epoch active and publishes none of the four
events. Only after the atomic cutover may a separately accepted projector target the
legacy-named path. `successor_active -> legacy_active` is invalid; recovery rebuilds
successor projections or stops and never re-enables legacy writers.

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
until a separate materialization task creates strict schemas for every object, content,
artefact, relation, command, event, Decision discriminant, receipt, reducer, projection
and registry named here, then constructs and obtains external acceptance of the
catalogue below. This task creates none.

### 8.1 Closed owner universe

Stage A is this exact accepted specification revision and its **81 literal owner rows**:
OR-001 through OR-041 and OR-101 through OR-140, with no gap inside either range. Every
row already fixes its command schema/discriminant, eligible W4 profile, exact authority
subject, preconditions, ordered event producers, streams/write set, reducer,
projections, receipt and distinct tests. That owner annex is the semantic authority; a
future catalogue may serialize it but cannot fill a blank or invent a binding.

The closed schema families those rows require are:

```text
portfolio object/content:
  programme, paper, hypothesis, candidate, method, dataset, claim, dependency-edge,
  assay-rubric-content, assay-evidence-scope-content, path-registration-content,
  dossier-expected-set-content, legacy-source-inventory-content,
  legacy-transition-mapping-content, legacy-cutover-closure-content,
  w11-schema-catalogue-content

aggregate/relation:
  Candidate, Assay, Spike, assay-request, assay-producer, assay-bar-acceptance,
  assay-outcome-review, assay-cancellation-review, Spike-plan, Spike-attempt,
  Spike-outcome-review, Spike-cancellation-review,
  discovery-promotion, discovery-revisit, authority-content-file-review-acceptance,
  dossier-six-family-closure, legacy-source-row-observation,
  legacy-source-row-target, inventory-mapping-transition-bijection,
  path-physical-identity, writer-revocation, cutover-closure

artefact payload:
  assay-scorecard, assay-partial, spike-plan, spike-verdict,
  scout-observation-batch, discovery-annotation, research-dossier-manifest,
  legacy-record-observed, legacy-portfolio-path-observation,
  authority-file-observation, review-evidence, collision-scan,
  writer-revocation-snapshot, projection-rebuild-proof

Decision discriminant:
  assay_bar_acceptance, discovery_promotion, discovery_revisit,
  spike_execution_authority, dossier_expected_set_acceptance,
  path_registration_acceptance, legacy_source_inventory_acceptance,
  migration_authority, legacy_path_cutover

command/event/receipt/authority:
  every complete OR-001–OR-041 and OR-101–OR-140 row, including every shared W2
  ReviewRequested, ReviewVerdictRecorded, DecisionProposed and DecisionResolved
  discriminant; one distinct receipt per row; CandidateRegistered producers exactly
  OR-001 and OR-029; W11AuthorityFileObserved producers exactly OR-103, OR-104,
  OR-111, OR-117, OR-123, OR-129 and OR-135; catalogue observation/review/acceptance
  exists only in the external Git/blob envelope; genesis import producer exactly OR-140

reducers/projections:
  authority-content, authority-file-observation, review, Decision, Assay-bar,
  Candidate, Assay, Spike, attempt/lease, dossier admission, portfolio object/edge/
  scope/project index, Scout observation, annotation/annotation epoch, legacy observation,
  source inventory, transition mapping, item ownership, cutover closure,
  path registration/cutover, successor Discovery view, optional combined view,
  schema-catalogue genesis/accepted-catalogue projection
```

Any name outside those closed sets requires a new reviewed W11 revision. “Supporting”
proposal/review/acceptance/path commands are not implementation details: their literal
owner rows are part of the 81-row authority and are therefore subject to the same
schema, retry, producer and completeness tests.

### 8.2 Materialization and external catalogue acceptance

The topological creation sequence is mandatory:

1. accept the exact W11 specification/owner annex at Stage A;
2. a schema materializer, in a later authorized task, creates each strict schema file
   and the minimal bootstrap command/schema/verification contract, but no W11 runtime;
3. only after all schema files exist, create `W11SchemaCatalogueContent` at the
   proposed path `.research-system/evals/expected/w11-portfolio-discovery-v1.json`;
4. an independent observer that executes no W11 command records for every schema and
   catalogue file its logical key, schema ID/version, exact repository path, Git
   commit/blob, file length/SHA-256, owner-row IDs and requirement hashes;
5. a distinct reviewer reconstructs the complete schema-source and owner-row
   multisets from the accepted specification, verifies the bootstrap contract, and
   records an exact report identity;
6. Stephen accepts one external `W11CatalogueAcceptanceEnvelope` containing the exact
   specification, schema, catalogue, observation, review, owner-multiset and bootstrap-
   contract identities. That envelope is stored outside the candidate and is the sole
   pre-runtime catalogue acceptance authority;
7. only after the envelope is accepted may a runtime registry, reducer, projector,
   handler, test-discovery mechanism or observed implementation interface be produced;
   and
8. the first authoritative mutation is OR-140's independently verified one-time
   genesis import of that unchanged envelope. Genesis cannot create or amend acceptance.

`W11SchemaCatalogueContent` is a closed Stage-B content candidate. It contains owner-
spec identity/hash; exact row counts/range hashes; `schema_source_rows[]` with each
already-materialized schema's identity/path/blob/file digest and independent
observation; and 81 `owner_contract_rows[]`, each containing:

```text
owner_row_id, logical_key, schema_id/version/file-observation,
command_type, payload discriminant, eligible_profile, exact authority_subject,
exact preconditions, ordered events and producer rows, affected streams,
complete write set, reducer, projection targets, receipt identity,
positive test identity, negative/mutation/retry test identities
```

It uses the common `content_hash` only; `catalogue_content_hash` is forbidden. The
content forbids its own repository path/blob/file digest, observation/review/acceptance/
Decision/event, runtime-registry identity, genesis result or observed runtime row.
Those later facts live in the external envelope and OR-140 genesis provenance. Thus
schema hashes precede catalogue content; catalogue content precedes external byte
observation/review/acceptance; acceptance precedes runtime production; and genesis
imports rather than produces that authority. There is no schema↔catalogue,
content↔acceptance or bootstrap self-cycle.

The external envelope is closed and contains no mutable lifecycle flag. It binds the
W11 specification commit/blob/SHA-256, catalogue path/blob/SHA-256, every schema path/
blob/SHA-256, the complete owner-row multiset hash, independent observation and review
report identities, Stephen's acceptance decision/time/scope, and exact bootstrap
command-schema/validator/test identities. OR-140 accepts no caller-supplied row or
schema list: it resolves the envelope and every committed byte independently, requires
the imported multiset to equal the accepted one, and is idempotent only for the same
envelope hash. Any prior genesis or conflicting payload fails closed.

Tests compare one-to-one multisets of complete schema-source and owner-contract rows,
not counts or separately derived field sets. They reject a self/back edge or SCC,
missing/duplicate row, swapped subject, removed event effect, blank reducer/projection,
aliased test, alternate producer, late schema, runtime-produced expected source, or
coordinated catalogue/runtime mutation. The independent reviewer resolves every row
back to this owner annex and rehashes every schema and catalogue file. A runtime
registry or enumerator may consume the accepted catalogue but may never generate its
expected side.

## 9. Failure behaviour

| Failure | Required result |
|---|---|
| Any authority content contains its own file/review/acceptance state, or the dependency graph has a self/back edge or SCC | `authority_dependency_cycle`; reject candidate/acceptance/consumer action with zero authoritative state change. |
| A derived relation hash omits its enumerated preimage, includes itself/enclosing or later authority, or fails topological sorting | `derived_hash_preimage_cyclic`; reject before content hashing or observation. |
| Any OR-001–OR-041/OR-101–OR-140 field, event producer, reducer, projection, receipt or distinct test is missing/blank/foreign | `owner_contract_incomplete`; fail materialization/acceptance before runtime production. |
| Catalogue acceptance is absent, candidate/runtime-produced, byte-stale, or the bootstrap contract/genesis import differs from the external envelope | `bootstrap_authority_unavailable`; produce no runtime authority or genesis state. |
| Candidate/source identity collision | Reject registration; preserve both observations; no Candidate event. |
| Assay bar is abstract, unaccepted, stale, accepted late, producer-mismatched, swapped after request, or scorecard belongs to another `assay_id` | Reject before evidence linkage; no Assay/Candidate event. |
| Assay axis missing/extra/duplicate/wrong type or rubric stale | Reject `AssayScored` or record explicit Assay Partial; no promotion proposal inferred. |
| Partial/cancelled aggregate has no exact review/revisit path, leaves an attempt/lease/proposal overlay, retry reuses an aggregate, or supersession commits without its replacement | `recovery_overlay_open`/`transition_dead_end`; reject the offending transaction; retain the old recoverable state/evidence. |
| A Discovery outcome review is non-satisfying/withdrawn, has blocking or unowned conditions, or attempts same-subject retry outside the withdrawal exception | `review_gate_unsatisfied`; record only the valid W2 review effect, emit no aggregate/Candidate `*Reviewed` event, and require the exact §4.2.3 replacement/supersession route. |
| Spike plan, attempt, Candidate, or verdict relationship mismatch | Reject verdict; preserve artefacts as unaccepted candidates. |
| Kill condition triggered but verdict PASS/PARTIAL | Reject verdict schema/relational validation. |
| Required Spike condition unable to evaluate | PARTIAL; no PASS or promotion. |
| Promotion resolved by model/Manager or against stale/foreign evidence | Reject before Decision event. |
| PROMOTE attempts to dispatch, lock a pre-registration, accept a result, or promote a claim | Reject complete batch. |
| Expected-set content/file/review/acceptance tuple missing, cyclic, late-authored, producer-related, byte-mismatched, unaccepted, or incomplete | Reject before manifest inspection; zero publication. |
| Dossier component/source/object/scope/edge/relation missing, extra, duplicate, tampered, stale, incompatible or valid-but-foreign | Reject atomically; zero event/object/ScopeDefinition/projection publication. |
| Source dependency cannot be independently resolved and rehashed | Reject atomically; a declared closure row is not observed bytes. |
| Expected and observed dossier/catalogue values share one producer or candidate-side enumerator | Acceptance gate fails; independent expected source required. |
| Legacy prose says Success/Done/PROMOTE | Observation only; no adoption or Decision. |
| Path/writer collision or shared physical target | Reject registration/write/transition; no “last writer wins.” |
| Manual edit to generated view | Drift diagnostic; rebuild from events; never ingest. |
| Annotation targets stale revision | Reject with current identity; human must issue a new annotation. |
| Ownership transition lacks migration authority/collision scan | Reject; item remains under current owner/path. |
| Ownership source/item/target/Decision members do not equal one accepted mapping relation | Reject before allocation; item remains under current owner/path. |
| Source inventory contains a mapping/owner/transition/cutover back-edge, unknown/uncovered bytes, correlated parser/reproducer, membership mismatch, stale bytes or unaccepted revision | Reject inventory/mapping/cutover; legacy path remains active. |
| Cutover closure lacks the source-row→accepted-mapping→transition-event bijection, has any legacy-owned/unmapped item, extra transition, active writer, changed final byte or post-observation race | Reject; legacy path remains legacy authority. |
| Accepted annotation epoch differs before fencing, its pending set is non-empty, the old epoch can still receive writes, or post-fence annotations do not route to the successor epoch | `cutover_epoch_stale`; publish no fence, epoch activation, path cutover or registration revision. |
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
| W11-I02 | Every reference/lifecycle artefact binds exact ID/revision/hash plus canonical `asy_`/`spk_` aggregate/stored relation; every derived-hash preimage is explicitly enumerated and every content/file/review/acceptance dependency is topologically constructible. | Schema, §3.6 DAG validator, aggregate reducers and relation resolver. | Substitute a valid foreign member; add self/back edge or SCC; include a relation/enclosing/later hash in its own preimage; assert rejection with state unchanged. |
| W11-I03 | Required dependency/block subgraph is acyclic. | Edge-registration/admission validator. | Add direct and multi-hop cycles; reject atomically. |
| W11-I04 | Exact closed rubric/scope contents, file observations, independent review, external Assay-bar acceptance and prospective=actual producer relation are frozen before collection; Partial/cancellation has a subject-specific non-dead-end reviewed revisit route, and only a §4.2.3 policy-satisfying verdict clears it. | OR-034–OR-041, §4.2.3, OR-101–OR-109, `RequestAssay`, Assay/Candidate reducers. | Abstract/missing/late/stale bar, producer change, post-request swap, foreign scorecard, axis mutations, all six W2 verdicts for every outcome discriminant, supersession/replacement, every RETRY/PARK/KILL edge and same-ID retry. |
| W11-I05 | Assay/Spike evidence cannot resolve promotion. | Decision authority resolver. | Feed PROMOTE recommendation/PASS without Stephen Decision; no state change. |
| W11-I06 | Spike verdict obeys success/failure/kill/Partial logic, and Partial/cancellation atomically closes attempts/leases and supersedes any pending execution proposal before the subject-specific policy-satisfied reviewed revisit/new-aggregate path. | Spike-verdict schema, rule evaluation, §4.2.3 and OR-019–OR-025/OR-040–OR-041 reducers. | Trigger each kill/unknown condition, all review verdicts and both cancellation/proposal race orders; traverse satisfying and non-satisfying replacement/revisit options; reject false PASS, open lease/proposal, negative-review progression, dead end and same-ID retry. |
| W11-I07 | Promotion is exact-subject, exact-gate, policy-satisfied-review and human-locked. | §4.2.3, `ResolveDecision` and authority grant. | Wrong actor, Candidate, revision, gate, evidence, non-satisfying/withdrawn review, option, next state, and stale grant. |
| W11-I08 | PROMOTE authorizes only one named next design step. | `CandidatePromotionApplied` reducer/write set. | Add Dispatch/pre-registration/result/claim event to batch; reject all. |
| W11-I09 | Complete literal six-family `DossierExpectedSetContent` precedes independent file observation/review/external acceptance, has no self/back edge, and is frozen before candidate observation. | OR-110–OR-115, §3.6 DAG and admission resolver. | Embed own file/acceptance, create SCC, late/related/unaccepted tuple or coordinated candidate-side omission; unchanged external tuple rejects. |
| W11-I10 | Dossier closure is exact, including independently resolved/rehashed component and source bytes, not “all supplied passed.” | `AdmitResearchDossier`. | Per-family missing/extra/duplicate/stale/incompatible/tampered/valid-foreign/path-escape/count-only and source-resolution mutations. |
| W11-I11 | Dossier admission is atomic. | W2 transaction/write set. | Fail each validation step and inject concurrent tail/version changes; assert zero events/final objects/scopes/projections. |
| W11-I12 | Scout observations are not judgments/authority, and all 81 owner rows bind complete command/discriminant, membership in the exact W4 allowlist, conditional event producer, streams/write set, reducer/effect-equivalent projection targets including `P:review`, receipt and three literal per-row test identities. | Scout schema, §4.2 owner annex/policy and externally accepted §8 catalogue. | Add judgment/direct write; omit/blank/swap any owner-row field; remove an allowlist member/projection/test identity or verdict branch; wildcard subject, alternate producer, coordinated catalogue/runtime change or abstract later command; reject. |
| W11-I13 | Generated views never authorize their source. | Command source allowlists. | Use successor/combined projection as dossier, annotation, transition, or Decision input; reject. |
| W11-I14 | Legacy, successor, annotation, and combined writer sets remain physically disjoint from registration through the operation commit point. | PathRegistration plus §7.3 handle/file-identity resolver. | Registered-root junction positive; exact/casefold/Unicode/8.3/symlink/reparse/prefix/hardlink/parent-swap race matrix. |
| W11-I15 | An annotation is evidence until a separate command acts. | `IngestDiscoveryAnnotation`. | Ingest proposed PROMOTE/object edit; only annotation event appears. |
| W11-I16 | Each active item has one owner and one accepted source-observation→source-only-inventory-row→mapping-content→external-Decision→target relation, with no reverse edge. | OR-122–OR-133, §7.5 resolver, ownership reducer and DAG validator. | Put mapping/owner in inventory; add mapping acceptance back-edge; attempt `dual_owned`, simultaneous or cross-member substitutions. |
| W11-I17 | Per-item transition never repurposes the legacy path. | Transition write set/path registry. | Transition one item while others remain; assert zero legacy-path write and legacy writer retained. |
| W11-I18 | Legacy-named generation requires an accepted source-only cutover inventory, mapping/transition completion, later accepted cutover closure with exact row bijection, independent final observation, writer revocation, accepted annotation epoch and race-free epoch fence/cutover. | OR-122–OR-139, `LegacyCutoverClosureContent`, OR-033 and §§7.3–7.6. | Break topological order; omit/alias/unparse row; coordinate parser omission; change final bytes; leave item/writer/collision/annotation; add a pre-fence annotation or write the fenced epoch; swap parent/reparse; reject. |
| W11-I19 | Whole-path cutover is one way. | Closed cutover state machine. | Attempt `successor_active -> legacy_active`; reject. |
| W11-I20 | Projection deletion/rebuild is authority-neutral, deterministic, and published only through the operation-time physical-identity protocol. | Projector/replay and §7.3 contract. | Delete/mutate view; rebuild byte-identically; inject parent/reparse/hardlink races; authority unchanged and no wrong-path write. |
| W11-I21 | Portfolio Claim governance is a required assurance boundary and cannot compensate for W5 claim authority. | Portfolio Claim schema, W5 consumer predicate and Paper Claim governance tests. | Supply accepted-looking Claim without W5 claim Decision; every claim consumer rejects; perform no claim action. |
| W11-I22 | Replay fails closed on unknown/broken W11 records, and the first W11 catalogue state can arise only from the externally accepted exact-byte envelope through the one-time verified genesis importer. | W2 replay/projectors, external envelope resolver and OR-140 bootstrap verifier. | Unknown major schema/event, broken hash/ref, missing reducer, self-produced envelope, stale byte, second/conflicting genesis; no authoritative projection. |

## 12. Pre-implementation acceptance tests

The future materialization/implementation plan must bind distinct test identities to the
following minimum set before any runtime code is written:

1. strict positive/negative schema and §3.6 topological tests for every literal §8
   content/authority, aggregate/relation, artefact, Decision subtype and all 81 owner
   rows, including every unconditional/conditional event producer, stream/write set, reducer/projection, receipt,
   self/back edge, SCC, enumerated relation-hash preimage, external catalogue envelope,
   genesis import and forbidden candidate acceptance field;
2. one-field-at-a-time type/value/enum/pattern/required/additional-property mutations;
3. after schema-file materialization, complete-row equality against the exact external
   `W11CatalogueAcceptanceEnvelope`: reject a schema↔catalogue or content↔acceptance
   cycle, duplicate/swap/aliased-test/blank reducer/removed effect/allowlist omission/
   omitted supporting command/alternate producer/late schema/self-produced envelope/
   stale bootstrap contract/coordinated runtime-catalogue attack and second genesis;
4. closed Candidate/Assay/Spike matrices covering every §4.1.1 state/command/event/
   stream/reducer edge, unique `asy_`/`spk_`, exact accepted Assay-bar and prospective=
   actual producer freeze, late/stale/swap cases, Partial review, subject-specific
   cancellation request/review, all six W2 verdicts for every complete/Partial/cancelled
   subject, non-blocking/blocking condition branches, exact review supersession,
   attempt/lease and pending-proposal closure, both cancellation/proposal race orders,
   RETRY/PARK/KILL, retry-new-aggregate and atomic replacement/supersession;
5. exact Candidate–Assay–Spike–artefact–review–RuleEvaluation–Decision–acceptance
   relation substitutions using foreign but individually valid current records,
   including old/new retry predecessors and acceptance tuples;
6. TDL legacy assay-rubric compatibility fixture proving the numeric rule while
   proving legacy `decision` is recommendation-only;
7. Spike PASS/FAIL/PARTIAL truth table with every kill/unknown condition perturbed at
   the producing seam plus every W2 verdict for complete/Partial/cancellation review,
   proof that only policy `satisfied` emits `*Reviewed`, negative/withdrawn replacement
   routes, attempt/lease closure, pending execution-proposal supersession and no-dead-end
   reachability;
8. PROMOTE/PARK/KILL option-specific requirements and non-Stephen authority negatives;
9. exact dossier positive fixture from a topologically constructed pre-observation
   `DossierExpectedSetContent` + file observation + review + external acceptance, plus
   self/back/SCC and every-family missing/extra/duplicate/tampered/stale/
   incompatible/relationship/path-escape/valid-foreign negatives; independently
   re-resolve/re-hash every source; coordinate manifest/command/runtime omissions while
   the accepted external expected tuple remains fixed;
10. dossier failure injection at every validation/publication boundary with zero event,
    final-object, ScopeDefinition, and projection publication;
11. idempotent lost-response retry/conflicting-payload retry for each of the 81 literal
    owner rows, with exact W4 subject, ordered event producer, streams, complete write
    set, reducer, projection, receipt and exact per-row positive, negative/mutation and
    retry identities; independently join every row to its W4 allowlist and effect-
    equivalent projection targets, including `P:review` and every §4.2.3 verdict branch;
12. Scout source/dedup/collision tests and direct-judgment/direct-write permission
    negatives;
13. annotation valid/stale/duplicate/foreign-writer/manual-projection-edit tests plus
    after-closure/before-fence, locked pre-commit and post-fence successor-routing races;
14. Windows operation-time suite: registered-root-junction positive plus exact,
    case-fold, Unicode, 8.3, symlink/junction/reparse, prefix, hardlink/file-ID,
    parent-replacement and concurrent-writer swaps after every §7.3 phase;
15. source-observation→source-only-inventory→mapping-content→external-acceptance→target
    topological test, per-item race and cross-source/item/target/Decision/coordinated
    foreign-valid substitutions against one stored accepted relation;
16. partial transition proof that earlier and cutover source rows reconcile only by
    exact row hash, legacy/successor paths remain disjoint, no `dual_owned` appears and
    no inventory carries a mapping/current-owner back-edge;
17. deletion/rebuild and projector-version tests for successor and optional combined
    views;
18. whole-path DAG fixture covering exact final bytes, source-only inventory content +
    external acceptance, complete byte/item membership, independent parser/reproducer,
    mapping/transition completion, later cutover-closure content + external acceptance,
    unknown/unparseable/alias/coordinated-omission/SCC attacks, row-mapping-event
    bijection, post-inventory/final-observation writes, writer revocation, accepted
    annotation epoch, pre-fence delta, successor epoch activation, no legacy-named
    generation before cutover, operation-time races and reverse transition;
19. external-envelope bootstrap, one-time genesis and accepted-snapshot replay with
    exact byte identities, projection hashes, conflicting-genesis and unknown-schema
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
| P-004/P-021 | Keep. Exact path/writer and item ownership bind an acyclic source-inventory→mapping→transition→cutover-closure chain and operation-time physical identities; no shared writer or inferred owner. |
| P-005/P-022 | Keep. Every Discovery promotion is human-locked; independent review evidence remains distinct from the author. |
| P-026 | Keep. Specification only; no legacy or successor state mutation. |
| P-032 | Keep. Canonical closed/recoverable lifecycle, external dossier/Assay/catalogue authorities, complete 81-row command subjects, and vault projection/annotation boundaries are defined prospectively. |
| P-034 | Keep. Accepted source-only inventory and per-item source–item–target relations precede transitions; a later accepted closure binds final observation/bijection and an accepted annotation epoch before atomic fence/cutover. No indefinite dual-running, implicit batch or parser omission. |
| P-036 | Keep. WP6 launch-basis constraints are unchanged; W11 receives a new exact-revision gate. |
| D-G6-4 bounded policy choices | **Accepted 2026-07-18:** catalogue authority is an external exact Git/blob envelope imported later through verified genesis; cutover uses an accepted annotation epoch, atomic fence and successor-epoch routing. This accepts the policies, not the W11 revision or any implementation/migration. |
| D-G6-4 limb 1 | **Open:** revision 0.5 reconciles R4 but is not self-accepted; Stephen may accept its new exact commit only after fresh independent R5 review reports no open Critical/Major. |
| D-G6-4 limb 2 | **Open:** Stephen must approve a content-addressed first ownership-transition batch using the accepted §7.5 relation; no item/path migration is inferred by accepting the spec. |
| W11-A1 | **Open/optional:** accept the proposed combined-view path, substitute another disjoint third path, or omit the view. |

The first transition-batch owner record must identify its accepted source-inventory
tuple and, per item, source-row/observation hash, current owner, intended target/object
hashes, proposed mapping content, path-registration revision, collision scan, unresolved
conflicts, exact command/write set, reviewer and rollback/stop evidence. It must not
precompute the later cutover closure. An empty or descriptive list is not approval.

### 13.1 Binding review reconciliation

The report at
`../reviews/adversarial-wp6-5-w11-spec-review-2026-07-18.md` remains immutable. The R1
author reconciliation below is retained for provenance; R2, R3 and R4 subsequently
identified further defects, so revision 0.5 refines rather than erases those
historical rows:

| Finding | Revision 0.2 disposition | Invariants/tests re-opened for fresh review |
|---|---|---|
| C-1 | Added the complete literal, pre-observation expected-set authority; revision 0.3 splits content from external file/review/acceptance records while preserving the six-family closure and coordinated-omission resistance. | I09–I11; tests 3, 9–11 |
| C-2 | Added exact-byte source inventory, independent parser/reproducer, byte coverage, final handle-bound observation and item/event bijection; revision 0.3 splits source inventory from mapping/transition/cutover closure. | I16–I20; tests 14–18 |
| M-1 | Added canonical `asy_`/`spk_` IDs/streams and bound every artefact, event, RuleEvaluation and Decision relation. | I02, I04–I07; tests 1, 4, 5 |
| M-2 | `RequestAssay` freezes an already accepted exact bar before `evidence_collecting`; revision 0.3 instantiates its closed contents, external lifecycle, producer relation and staleness. | I04–I05; tests 4–6 |
| M-3 | Admission independently resolves and rehashes every component and every source dependency from verified handles/resolvers. | I09–I10; test 9 |
| M-4 | §4.2/§8 list commands/events/authority; revision 0.3 replaced the incomplete summary with its then-current 82 literal owner rows including supporting review-request/authority lifecycle, reducers, projections and tests. Revision 0.4 supersedes that catalogue with the 81-row authority reconciled below. | I12, I15–I18; tests 1, 3, 11–13, 18 |
| M-5 | Added one accepted inventory-item/`LegacyRecordObserved`/source-selector/target/Decision relation hash loaded independently before allocation. | I02, I16–I17; tests 5, 15, 16 |
| M-6 | Added operation-time registered-root, no-follow traversal, handle/file-ID/hardlink, held-parent, atomic-replace and post-verify protocol plus phase-specific races. | I14, I18, I20; tests 14, 17, 18 |
| m-1 | Paper Claim is Required for governance/consumer tests while every actual claim activity remains unauthorized. | I21; test 20 |
| m-2 | Added dated §8 to the tracked plan-suite evidence register with exact live paths, hashes, mutability and limitations; linked it from §2.2/README. | Entry criterion 2 |

The immutable R2 report at
`../reviews/adversarial-wp6-5-w11-spec-remediation-r2-review-2026-07-18.md` reviewed exact
subject `d24df9d26f0d906d177eafa1eaeabb65a5515004`. Revision 0.3 dispositions its complete
finding/matrix audit without claiming acceptance:

| R2 finding | Revision 0.3 disposition | Invariants/tests re-opened for R3 |
|---|---|---|
| R2-M1 — expected-set self-content-address cycle | §3.6/§5 split `DossierExpectedSetContent` from later file observation, review and external acceptance. No candidate contains its own storage/acceptance; admission validates a topologically ordered tuple. | I02, I09–I11; tests 1, 3, 9–11 |
| R2-M2 — inventory↔mapping lifecycle/hash cycle | §7.5–§7.6 define source-only inventory → mapping content → external acceptance → transition → later cutover closure. Inventories have no mapping/owner back-edge; cutover consumes an accepted closure. | I02, I16–I20; tests 1, 3, 14–18 |
| R2-M3 — abstract Assay bar | §4.3 instantiates exact rubric/scope contents, external review/acceptance, prospective=actual producer relation and staleness triggers before `RequestAssay`. | I04–I07; tests 1, 4–8 |
| R2-M4 — incomplete owner catalogue | Revision 0.3 defined its then-current 82 literal owner rows, including outcome-review requests, proposal/review/acceptance/path/catalogue commands and exact subjects, events, reducers, projections, receipts/tests. Revision 0.4 supersedes that catalogue with 81 rows and the external-envelope/genesis sequence reconciled under R3-M2/M3. | I09, I12, I14–I18, I22; tests 1, 3, 9, 11–19 |
| R2-M5 — cancellation/Partial dead ends | §4.1.1 and OR-003–OR-027 give exact Partial review, cancellation, attempt closure, revisit RETRY/PARK/KILL and atomic fresh-aggregate replacement/supersession transitions. | I02, I04–I08; tests 4, 5, 7, 8, 11 |

The immutable R3 report at
`../reviews/adversarial-wp6-5-w11-spec-remediation-r3-review-2026-07-18.md` reviewed exact
subject `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b`. Revision 0.4 dispositions its complete
finding/matrix audit without claiming acceptance:

| R3 finding | Revision 0.4 disposition | Invariants/tests re-opened for R4 |
|---|---|---|
| R3-M1 — cyclic/undefined derived-hash preimages | §3.6 makes every relation digest a separately enumerated preimage that excludes itself, enclosing and later hashes; §4.3 and §7.5 enumerate the Assay and transition relations; §8 removes `catalogue_content_hash`. | I02, I16; tests 1, 3, 4, 15, 18 |
| R3-M2 — catalogue bootstrap requires prohibited runtime | Stephen approved the external exact Git/blob `W11CatalogueAcceptanceEnvelope`; §3.6/§8.2 require observation, independent review and owner acceptance before runtime, followed only by OR-140's verified one-time genesis import. | I12, I22; tests 1, 3, 11, 19 |
| R3-M3 — owner rows disagree with allowlist/projections/tests | §4.2/§6.2 join 81 literal rows to the exact W4 allowlist and effect-equivalent projections; OR-004/005/007 project Candidate; every row has a literal positive, negative/mutation and retry identity. | I04, I12; tests 1, 3, 4, 11 |
| R3-M4 — cancelled outcomes lack a review route | OR-038–OR-041 add exact request/verdict subjects for Assay and Spike cancellation, and §4.1 requires `cancelled_reviewed` before revisit. | I04, I06; tests 4, 7, 11 |
| R3-M5 — Spike Partial/cancel leaves overlays live | OR-019 closes its attempt/lease on PARTIAL; OR-022 atomically closes attempt/lease and mechanically supersedes any unresolved OR-015 proposal before cancellation review/revisit. | I06; tests 4, 7, 11 |
| R3-M6 — late annotation can stale cutover closure | Stephen approved the accepted annotation-epoch policy; §§7.4/7.6 bind the exact legacy epoch, re-observe it under lock, atomically fence it and activate successor routing at cutover. | I18; tests 13, 18 |

The immutable R4 report at
`../reviews/adversarial-wp6-5-w11-spec-remediation-r4-review-2026-07-18.md` reviewed exact
subject `4b941326e290582db7be07113d5d7bb78d8b97a3`. Revision 0.5 dispositions both
findings without claiming acceptance:

| R4 finding | Revision 0.5 disposition | Invariants/tests re-opened for R5 |
|---|---|---|
| R4-M1 — negative/unverifiable outcome review clears the gate | §4.2.3 defines one closed six-discriminant verdict/effect policy. Every verdict updates W2 Review; only `approve` or policy-valid non-blocking `approve_with_conditions` reaches `satisfied` and emits `*Reviewed`. All other verdicts leave the outcome unchanged and require an exact replacement/superseding review relation. | I04, I06, I07, I12; tests 4, 7, 11 |
| R4-m1 — inconsistent Review projections | OR-006/007/021 now join `U:review` to `P:review`, matching OR-020/039/041; every verdict branch updates the Review projection while aggregate/Candidate effects remain conditional. | I12; tests 1, 3, 11 |

The four reviews' complete audits are dispositioned, not narrowed: all five design
entry criteria are now stated as satisfied for authorship; every P-004/P-005/P-021/
P-022/P-026/P-032/P-034/P-036 and D-G6-4/W11-A1 row remains explicit above; all 22
invariants remain in §11; all 20 pre-implementation tests remain in §12; §8 resolves
the literal owner/interface universe and acyclic creation order; §9 retains fail-closed behavior; §10 contains the
complete assurance classification; §13.2 reconciles owner-spec identities; and
§14/§14.1 retain independent review, proportionality and residual-risk gates. Author
checks are reconciliation evidence only.

### 13.2 Cross-spec consistency reconciliation

| Invariant / identity | Owning source | Revision 0.5 binding and disposition |
|---|---|---|
| First-class ID, immutable record and canonical stream/reference semantics | W2 §§5–9 | Portfolio/content records remain immutable `obj_`; Assay/Spike use canonical `asy_`/`spk_`; review/acceptance state is external and every reference is topologically constructible. |
| Decision is not `RuleEvaluation` | W2 §18; P-005/P-022 | Scorecards/verdicts remain evidence; every PROMOTE/PARK/KILL resolution is an exact-subject Stephen Decision and cannot be compensated. |
| Acceptance bar independent of producer and frozen before observation | W5 §§6–11 | `RequestAssay` freezes exact rubric/scope contents, file observations, review, external acceptance and prospective=actual producer relation; dossier acceptance likewise follows content without self-addressing. |
| Complete expected-set closure and producer separation | W5 §11; WP6 master §6 | Six literal dossier row families and the 81-row §4.2/§8 owner universe receive external exact-byte acceptance before runtime; candidate/runtime coordinated omissions remain unequal. |
| Atomic publication | W2 §§8–9/13 | Dossier and promotion batches validate exact relations/write sets first; any failure produces zero authoritative event/object/scope/projection publication. |
| Observation is not adoption | W2 §22; P-032/P-034 | `LegacyRecordObserved` and source-only inventory are evidence; later mapping content, external Decision/acceptance and transition are required for one item. |
| One active owner and no shared physical writer | W1 §§9–10; P-004/P-021 | Acyclic source inventory→mapping→transition→cutover closure plus §7.3 physical identity and the accepted annotation-epoch fence close partial/whole-path cutover without `dual_owned` or stranded evidence. |
| Profile capability is not command authority | W4 §§7/15/19 | Each of 81 literal rows names profile, exact subject, grant, preconditions, events, streams/write set, reducer/effect-equivalent projection and three literal test identities; unlisted rows default deny. |
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
   relational substitutions, every §3.6 self/back edge and SCC, the complete 81-row
   owner multiset and all three literal per-row test identities, the external catalogue
   envelope/one-time-genesis boundary, Assay-bar producer/staleness, every cancellation/
   Partial review and recovery edge, all six W2 verdicts across all six outcome subjects,
   non-blocking/blocking condition ownership, negative/withdrawn review replacement and
   same-subject attacks, attempt/lease/proposal cleanup in both race orders,
   source-inventory/mapping/closure ordering, shared physical writers, partial cutover,
   legacy-named generation, accepted annotation-epoch staleness/fencing/successor routing,
   combined-view feedback, annotation round-tripping, and atomic dossier publication.
4. The primary author may perform a self-adversarial check, but it is recorded only as
   author verification and does not satisfy this independent gate.
5. Reconciliation dispositions every finding and records exact changes. Any material
   post-review change receives fresh review of the new exact revision.
6. Acceptance requires no open Critical or Major finding, explicit disposition of all
   Minor findings, both required contract commands passing, link/path consistency, and
   Stephen's exact-revision D-G6-4 decision.

### 14.1 Proportional controls and residual risks

Controls remain concentrated at their risk boundary: Scout registration uses closed
source/dedup/collision checks; Assay/Spike use externally accepted request/plan relations,
bounded review and explicit recovery; promotion uses the exact Stephen Decision;
dossier admission bears the full independent six-family tuple and byte-rehash cost;
each ownership transition uses one accepted source-row/mapping relation; irreversible
cutover alone bears the later closure, writer revocation, final-byte and filesystem-race
proof. The optional combined view is omitted
unless W11-A1 is accepted after core path tests.

Fresh review and later implementation review must retain these residual risks:

- future schema/expected-catalogue code could reintroduce a hash cycle or derive
  expected/observed sides from one runtime registry; review must topologically sort the
  stored graph, reconstruct both sides separately and run coordinated-pair mutations;
- future lifecycle reducers could omit an owner row or leave a Partial/cancelled state
  unreachable; review must enumerate all 81 rows and perform full state reachability;
- future review reducers could confuse `verdict_recorded` with policy `satisfied`;
  review must enumerate all six W2 verdicts, condition branches and replacement modes
  for every complete/Partial/cancelled Assay/Spike subject and assert zero outcome event
  on every non-satisfying branch;
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
      non-dead-end Partial/cancellation/retry/failure semantics are defined.
- [x] `AdmitResearchDossier` exact closure and zero-publication failure are specified.
- [x] `DossierExpectedSetContent` plus external file/review/acceptance is a complete
      literal acyclic authority accepted before candidate observation; every source
      dependency is independently rehashed.
- [x] Scout ingestion plus Scout/Portfolio Steward W4 deltas are specified.
- [x] Legacy/successor/annotation/combined paths and writer sets are disjoint.
- [x] Annotation ingestion, item transition, collision, rebuild, and one-way whole-path
      cutover are specified.
- [x] Exact acyclic source-inventory→mapping→transition→cutover-closure relations,
      independent final-byte observation and operation-time Windows identity/races are
      specified.
- [x] All six assurance lanes are dispositioned; Output/Provenance is primary.
- [x] Invariants map to enforcement points and pre-implementation attacks.
- [x] R1, R2, R3, and R4 independent adversarial reviews completed with `rework_required`;
      immutable reports incorporated unchanged.
- [x] Primary author reconciliation dispositions every R1/R2/R3/R4 finding and full matrix.
- [ ] Fresh independent R5 review of the new exact commit reports no open Critical/Major.
- [ ] Stephen accepts the exact W11 revision under D-G6-4.
- [ ] Stephen approves the first exact ownership-transition batch under D-G6-4.
- [ ] Future strict schemas and independent expected catalogue are materialized,
      reviewed, and accepted before implementation.

The unchecked items are intentional hard stops, not incomplete implementation work in
this specification task.
