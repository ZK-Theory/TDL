# W3 — Context, Memory, and Retrieval Specification

**Date:** 2026-06-30<br>
**Status:** Accepted written specification under P-028; implementation remains prohibited<br>
**Specification version:** 0.2<br>
**Design authority:** Accepted W1 v0.3, accepted W2 v0.3, accepted W6 v0.2 catalogue plus the 2026-06-30 W3 retrieval-fixture addendum, W0 manifest/addendum, D-001–D-008, and P-001–P-028<br>
**Implementation authority:** None; this document defines contracts and gates but creates no compiler, schemas, indexes, runtime, migration, or `.research-system/` state<br>
**Review owner:** Stephen; adversarial review, approved reconciliation, and bounded delta review completed on 2026-06-30

## Review record

- **Conceptual design:** Approved by Stephen on 2026-06-30.
- **W1/W2/W6 dependency gate:** Passed and recorded in `reviews/w1-w2-w6-review-acceptance-2026-06-30.md`.
- **Written specification:** Adversarial review returned `accept_with_required_changes`; Stephen approved the reconciliation, and revision 0.2 passed the bounded delta review under P-028 on 2026-06-30.
- **Implementation:** Prohibited until the complete P-026 gate sequence and a separately approved implementation plan.

## 1. Decision summary

W3 replaces full-history preloading and unrecorded retrieval with bounded, immutable, source-linked context.

The specification makes these binding choices, subject to the W3 review gate:

1. An issued context consists of one immutable base packet plus zero or more immutable context addenda. Retrieval never mutates a packet already issued.
2. Every packet has a canonical manifest that identifies the task, role, risk, purpose, compiler policy, sources, excerpts, versions, hashes, selection reasons, omissions, conflicts, freshness, security class, size, and delivered-content hash.
3. Mandatory governing evidence is selected before optional material and cannot be summarized away or omitted to meet a budget. If it does not fit, compilation fails and dispatch/review waits.
4. ARS-managed context has hard provisional reference-token ceilings: R0 8,000, R1 16,000, R2 32,000, and R3 48,000. A separate provider-capacity gate reserves at least 20% of usable model input for the active interaction, provider instructions, and tool results.
5. Direct canonical sources outrank optional search, graph, full-text, or vector indexes. An unavailable index triggers recorded direct retrieval, not weaker authority.
6. Event history, canonical projected state, durable declarative memory, procedural memory, examples, and working context remain distinct information classes.
7. Compaction and memory consolidation produce source-linked proposals or aids. They do not supersede governing decisions, pre-registrations, contracts, results, or reviews.
8. When the assurance grade requires a distinct verifier under P-022, reviewer independence is checkable from two different context manifests and their source overlap/exclusion evidence. The exact subject remains visible; producer conclusions and hidden reasoning do not enter an independent verifier packet.
9. Secrets, raw restricted data, full transcripts, and hidden reasoning are prohibited from reusable packets and manifests.

These accepted choices freeze the shared context and independence interface consumed by W4 and W5. They do not choose models, assign authority, define scientific assurance policy, or implement retrieval.

## 2. Sources and evidence

W3 implements:

- W1 sections 5.7, 6, 7, 9, 14, 16, and 18: bounded context, direct-source authority, disposable indexes, trust boundaries, and downstream W3 constraints;
- W2 context references, root binding, subject-hash review, actor/independence evidence, restricted-data exclusion, replay source positions, and the F-021/F-022 carrying fields;
- W6 fixtures F-003–F-006, F-011–F-022, and the P-028 reservations F-025–F-030, especially governing-amendment omission, correlated reviewer contexts, retrieval equivalence, overflow, distractor invariance, and addendum lineage;
- W0 source precedence, stale-projection lessons, no-migration set, and the approximately 80,000-token Manager initialization estimate derived from a simple word-to-token heuristic for generic preload;
- P-020–P-028, including one canonical store, checkable independence, proportional profiles, the P-026 successor lane, accepted W1/W2/W6 interfaces, and the accepted W3 reconciliation;
- the supplied context-engineering distinction among instructions, knowledge, memory, examples, tools, guardrails, event history, and model working context.

The original external whitepapers are terminology and practitioner guidance, not project authority. Direct repository evidence and attributed decisions control this specification.

## 3. Scope and non-goals

### 3.1 In scope

- context-request, packet, manifest, addendum, omission, conflict, freshness, and delivery contracts;
- role- and risk-sensitive mandatory source classes;
- hard context ceilings and deterministic packing order;
- direct retrieval and optional-index fallback behavior;
- declarative and procedural memory identity, lifecycle, provenance, review, and supersession;
- compaction and consolidation boundaries;
- source staleness, conflict, confidence, and authority classification;
- the context evidence required to assess reviewer independence;
- security, privacy, retention-class, and restricted-source exclusions;
- deterministic tests and retrieval/trajectory evals required before implementation planning.

### 3.2 Deferred

- role permissions, model capability thresholds, provider choice, and exact independence grades: W4;
- assurance-lane requirements, contract ownership, and result-to-claim policy: W5;
- executable fixture/trace/grader schemas, thresholds, and retention periods: foundation-critical and full W6;
- provider tokenizers, delivery surfaces, runtime hooks, and semantic parity: W7;
- process, resource, checkpoint, and operator context: W8;
- migration/import and pilot mechanics: W9.

### 3.3 Non-goals

- implementing a context compiler, memory database, vector store, graph index, or provider adapter;
- copying the full Tracker, vault, paper history, or active task state into a new store;
- treating a summary, embedding hit, search score, or memory item as authority;
- storing raw UKDA data, credentials, `.env` contents, full transcripts, or hidden reasoning;
- using T1.28 or another active research task as an experimental compiler input;
- allowing smaller context to weaken a governing design, hard guardrail, review requirement, or human decision gate.

## 4. Options considered

### 4.1 Full immutable packet only

Compile and retain a complete static packet for the full attempt or review.

**Benefits:** Exact delivered content is easy to prove; simple replay model.
**Costs:** Repeats static material, handles later evidence poorly, and encourages oversized packets.
**Decision:** Rejected as the sole model.

### 4.2 Retrieval-only working context

Retrieve sources on demand and record a manifest after the session.

**Benefits:** Small initial context and flexible exploration.
**Costs:** The manifest can diverge from what the model actually saw; omission and independence are hard to prove; recovery depends on session behavior.
**Decision:** Rejected.

### 4.3 Layered immutable packet plus append-only addenda

Issue a bounded immutable base packet. Later authorized retrieval creates a new immutable addendum linked to the base and records its delivery.

**Benefits:** Exact base context, explicit later retrieval, bounded growth, reproducible independence evidence, and no mutable context object.
**Costs:** Requires packet/addendum lineage and cumulative budget accounting.
**Decision:** Selected.

## 5. Information classes

W3 prohibits collapsing these classes:

| Class | Meaning | Authority |
|---|---|---|
| Event history | Immutable accepted facts and receipts | Canonical for lifecycle facts under W2 |
| Projected state | Current task, artefact, review, and decision views | Rebuildable; authority derives from events |
| Governing source | Pre-registration, contract, decision, accepted result, policy, or scope definition | Authority declared by W0/W1/W2 and source type |
| Declarative memory | Reviewed finding, convention, or reusable lesson | Retrieval aid with explicit scope/confidence; never silently governing |
| Procedural memory | Versioned skill, workflow, example procedure, or tool-use rule | Instructional input subject to canonical policy and task authority |
| Example | Demonstration selected for a declared similarity/purpose | Non-authoritative unless separately governed |
| Working context | Exact bounded content delivered for one purpose | Operational evidence, not research authority by itself |
| Session trace | Messages and allowed tool/trajectory metadata | Audit/eval input under W6 privacy policy |

A summary of an event is not the event. A memory of a decision is not the decision. A procedure that usually works cannot override the current Task or governing amendment.

## 6. Context request and policy profile

### 6.1 Context request

Every compilation request names:

- `context_request_id`, `project_id`, Task/revision, dispatch/review/decision purpose, and expected control-store tail;
- requesting actor, target actor/profile, role, risk tier, and session identity where known;
- assurance lanes and exact governing-object references supplied by the Task;
- packet purpose: `orchestration`, `design`, `implementation`, `verification`, `claim_review`, `operations`, or another registered extension;
- required independence relationship to any producing attempt;
- context-policy version and budget profile;
- explicit roots and access classes;
- required output/decision and expiry or currency triggers.

A request cannot infer project identity, control root, Task, or risk from the current working directory or chat title.

### 6.2 Policy profile

A versioned context policy defines:

- mandatory source classes by purpose, role, risk, and assurance lane;
- allowed summary substitution for non-governing material;
- freshness and expiry rules;
- selection and packing priorities;
- permitted procedural-memory and example classes;
- direct-retrieval and optional-index strategies;
- forbidden content and redaction rules;
- addendum and cumulative-budget rules;
- independence exclusions;
- failure behavior.

The policy is provider-neutral. W7 adapters may apply a stricter provider limit but cannot weaken mandatory inclusion or security rules.

## 7. Mandatory source closure

### 7.1 Mandatory classes

Before ranking optional material, the compiler resolves the applicable closure of:

1. exact Task/revision, objective, scope, dependencies, acceptance/Partial criteria, and prohibited shortcuts;
2. authority grant, risk tier request, review topology, human-reserved transitions, and stop/escalation rules;
3. governing pre-registration/design and every effective amendment;
4. applicable contracts, schemas, decision rules, scope definitions, and binding evidence;
5. current blockers, decisions, supersessions, accepted reviews, and claim restrictions;
6. exact input/artefact identities, versions, hashes, vintages, representation locks, and consumer requirements needed by the role;
7. declared control/code/result/cache/paper/vault/data roots and no-overwrite rules;
8. canonical policy and required procedural-memory versions;
9. source-precedence and privacy rules needed to interpret conflicts;
10. purpose-specific subject artefacts and review questions.

Dependency closure stops at a source boundary declared sufficient by policy. It does not recursively preload every narrative that mentions a mandatory source.

### 7.2 Optional classes

After the mandatory closure fits, the compiler may add:

- directly relevant implementation or historical evidence;
- reviewed memory items;
- bounded examples and known failure cases;
- supplementary documentation;
- optional index results that resolve to direct source fragments.

Optional material is ranked by role relevance, risk, dependency distance, authority, freshness, and expected decision value. Retrieval score alone is never authority.

## 8. Budgets and deterministic packing

### 8.1 Provisional hard ceilings

The first W3 profiles use these ARS-managed packet ceilings:

| Risk | Maximum reference tokens | Intended use |
|---|---:|---|
| R0 | 8,000 | Mechanical, deterministic, reversible work |
| R1 | 16,000 | Bounded implementation under stable specification |
| R2 | 32,000 | Research implementation or independent scientific verification |
| R3 | 48,000 | Methodological design, claim review, or other high-consequence work |

Two independent, unit-safe gates apply:

```text
reference-token count <= W3 profile ceiling
bound-provider token count <= floor(0.80 × provider usable input capacity)
```

The first gate uses the versioned W3 reference tokenizer. The second uses the exact versioned tokenizer for the bound provider/model when available. If exact counting is unavailable before issuance, W7 must supply an evaluated conservative upper-bound counter and its evidence version; a route with neither an exact count nor an evaluated upper bound is ineligible. Raw counts from different tokenizers are not compared through one `min(...)` or treated as interchangeable units.

At least 20% of provider usable input remains outside the ARS-managed packet for the active interaction, provider instructions, and tool results. That reserve is not an undocumented tokenizer-drift allowance. W3 records UTF-8 bytes, reference-tokenizer identity/count, and bound-provider tokenizer or upper-bound identity/count so size remains auditable across adapters.

Compilation may reach `compiled` before provider binding, but no packet reaches `validated` or `issued` until both gates pass. These ceilings are hard maximums, not targets. A lower role/task ceiling may be declared. Increasing a profile ceiling requires a versioned policy decision and retrieval-eval evidence; it is not an automatic response to a compilation failure.

### 8.2 Packing order

The deterministic packing order is:

1. mandatory authority, scope, design, amendment, assurance, stop, root, and security material;
2. mandatory task/role procedural memory;
3. exact subject and evidence material required for the purpose;
4. high-value reviewed memory and failure examples;
5. supplementary optional evidence.

Within a class, the policy records stable tie-breakers. Deduplication preserves all source references and authority distinctions even when one excerpt represents identical text.

### 8.3 Overflow behavior

Mandatory content is never truncated, dropped, or replaced by an unapproved summary to meet either gate. If mandatory closure exceeds the reference-token profile ceiling or the bound-provider capacity gate, compilation returns `context_budget_exceeded` with:

- the required sources, UTF-8 size, reference-token count, and provider-token count or evaluated upper bound;
- duplicated or conflicting material identified;
- safe options such as Task decomposition, narrower purpose, policy-approved source compaction, or routing to an evaluated larger-capacity profile;
- no issued packet and no dispatch/review satisfaction.

W4 decides whether a larger evaluated model/profile is available. W3 does not silently route.

## 9. Context packet and manifest

### 9.1 Packet structure

An immutable base packet has ordered sections:

1. identity, purpose, freshness, and authority warning;
2. objective, scope, dependencies, and prohibited actions;
3. governing design, amendments, decisions, and contracts;
4. assurance, review, Partial, and stop requirements;
5. roots, artefacts, inputs, and provenance;
6. role-specific procedures and examples;
7. unresolved conflicts, omissions, and questions;
8. delivery metadata and manifest reference.

The exact rendered packet receives a content hash. Presentation changes that alter delivered bytes create a new packet revision or addendum.

### 9.2 Manifest fields

The manifest records:

- `context_id`, request ID, parent/addendum relationship, schema/version, compiler/policy version, and content hash;
- project, Task/revision, purpose, role/profile, risk, actor/session, and producing-attempt relationship;
- control-store identity and source event position/hash;
- reference-token profile budget, reference-tokenizer identity/count, bound-provider tokenizer identity/count or evaluated upper-bound identity/count, provider usable-input capacity/reserve, UTF-8 bytes, and cumulative addendum size;
- candidate-set digest, retrieval-trace references, included entries, omission entries, conflict entries, confidence summary, freshness verdict, and security/redaction declaration;
- independence visibility/exclusion evidence;
- exact rendered-packet hash and delivery receipt references;
- creation time, expiry/currency triggers, retention class, and supersession lineage.

The canonical manifest is control-plane evidence referenced by the rendered packet; it is not model-visible managed content by default. Any manifest fields deliberately rendered into the packet are included in both token gates. R0 uses the same canonical schema with explicit empty or `not_applicable` values rather than a weaker field-dropping variant; operational overhead must be measured before another schema profile is proposed.

### 9.3 Included-source entry

Every included fragment records:

- source kind and canonical/external ID;
- repository/path/URI or opaque locator and declared root;
- revision, commit/event position, content hash, and source authority class;
- confidence class and evidence basis for non-authoritative memory, index-derived, or external material; retrieval score alone never raises confidence or authority;
- exact excerpt selector and excerpt hash, or an explicit whole-object selection;
- selection rule and human-readable reason;
- freshness and supersession state;
- sensitivity class and redaction action;
- whether it is mandatory, summarized, or optional.

Line numbers alone are insufficient identity. Git-backed excerpts bind commit and file hash; event-backed excerpts bind source position/hash; external sources bind a versioned artefact reference.

### 9.4 Omission entry

The candidate-set digest records what policy considered. Material omissions use typed reasons:

```text
role_irrelevant        duplicate_content       superseded
budget_displaced       unavailable             access_denied
policy_excluded        privacy_excluded        unresolved_conflict
not_selected_by_rule   other_typed_reason
```

A mandatory candidate cannot end as an omission in an issued packet. `budget_displaced` applies only to optional material. Omission reporting is bounded to the policy candidate set; W3 does not pretend every repository file was considered.

## 10. Retrieval and index behavior

### 10.1 Retrieval sequence

1. Resolve project/control-store binding and expected source position.
2. Resolve Task, purpose, role, risk, and authority.
3. Build mandatory dependency closure from canonical IDs and direct files.
4. Verify versions, hashes, supersession, amendments, access class, and freshness.
5. Query optional indexes only for allowed supplementary candidates.
6. Resolve every selected index hit back to a direct source and verify it.
7. Pack deterministically, record omissions/conflicts, apply the reference-token gate, hash the rendered result, and create a `compiled` candidate that is not yet issued.
8. W4 selects an evaluated route; W7 supplies the bound-provider exact token count or evaluated upper bound; W3 applies the provider-capacity, manifest, security, and independence validations.
9. Issue only after every validation succeeds. W7 then delivers the exact issued bytes; mark `delivered` only after a matching content-hash receipt.

### 10.2 Optional indexes

Full-text, graph, vector, and cached search indexes declare source position/hash, builder version, completeness, and staleness. They may propose candidates but cannot establish source authority, freshness, or inclusion.

If an index is missing or stale:

- mandatory retrieval uses direct sources;
- optional retrieval either uses direct bounded search or records degraded optional recall;
- the manifest records the unavailable index and fallback path;
- R2/R3 compilation fails if the direct path cannot establish the mandatory closure.

## 11. Freshness, conflict, and reuse

### 11.1 Freshness states

Each source and packet is one of:

```text
current | stale_known | unverifiable | superseded | conflicted
```

`current` means the source was checked against its declared authority and currency rule at compilation. It does not mean the underlying claim is scientifically accepted unless its authority fields say so. The `conflicted` state is governed by section 11.3 and never implies a resolved precedence decision.

### 11.2 Currency triggers

A packet becomes stale when any applicable trigger fires:

- Task, scope, authority grant, risk, dispatch, blocker, root, or acceptance criteria change;
- a governing amendment, decision, correction, supersession, review, or claim restriction changes;
- an included artefact receives a new relevant version, integrity result, or availability state;
- canonical policy, required skill, schema, domain pack, or context policy changes;
- the source event position advances on a stream named by the packet's currency set;
- a declared time/access expiry is reached.

Unrelated project events do not invalidate every packet. The manifest records the exact currency set.

### 11.3 Conflict behavior

Conflicts record both sources, their authority classes, versions, hashes, applicable precedence rule, and the authority needed to resolve them.

- A mechanically resolvable lower-authority stale projection is retained as a conflict/omission record and cannot displace the stronger source.
- An unresolved governing conflict blocks issuance.
- R2/R3 packets fail closed on `stale_known`, `unverifiable`, or unresolved governing conflict.
- R0/R1 may tolerate only stale optional non-governing material when policy explicitly allows it and the packet is marked degraded.

## 12. Packet lifecycle and addenda

### 12.1 Lifecycle

```text
requested -> compiling -> compiled -> validated -> issued -> delivered
requested/compiling/compiled -> failed
issued/delivered -> expired | superseded
```

Lifecycle events are W2 extensions and do not alter Task state automatically. `delivered` proves bytes/hash reached the adapter/session; it does not prove comprehension or acceptance.

### 12.2 Addenda

Later retrieval creates a new `ctx_` addendum that records:

- base packet ID/hash;
- triggering message/tool/query;
- new source entries and omissions;
- cumulative reference-token and bound-provider capacity-gate state before/after;
- changed conflict/freshness state;
- rendered addendum hash and delivery receipt.

Addenda cannot silently repair an invalid base packet. If a missing mandatory source is discovered, the base is marked failed/superseded and a new complete packet is compiled before governed work continues.

### 12.3 Reuse

Reuse is allowed only when Task revision, purpose, role/profile, risk, independence relationship, currency set, policy version, required skills, roots, and security class remain compatible. The compiler revalidates all triggers and records a new delivery receipt. Session convenience is not a reuse rule.

## 13. Durable memory and compaction

### 13.1 Declarative memory

A durable memory item records:

- stable identity, claim type, exact source references/hashes, and source authority;
- project/domain scope and consumers;
- author, reviewer, review state, confidence basis, and limitations;
- effective time, currency triggers, expiry/review date, and supersession;
- sensitivity and retention class;
- whether the memory references a governing object and, if so, that object's canonical ID/hash. The memory item itself never carries governing authority and is never a substitute for the referenced decision, pre-registration, contract, result, or review.

Lifecycle:

```text
candidate -> reviewed -> accepted
candidate/reviewed -> rejected
accepted -> stale -> accepted | superseded | retired
```

Most memory is non-governing. A governing decision remains the linked decision/pre-registration/contract object, not the memory item summarizing it.

### 13.2 Procedural memory

Procedural memory entries include skills, workflows, examples, and tool-use rules. Selection records:

- canonical skill/procedure name, version/hash, and source path;
- applicability trigger and why it matched;
- runtime/provider compatibility;
- required dependencies and permissions;
- supersession and review state;
- applicable Task Observer overlays identified by canonical log path, exact title, date, and status, never a bare ordinal.

User instructions, project policy, Task requirements, and governing research authority outrank a procedure. A procedure conflict blocks or creates an explicit omission; it is not resolved by choosing the more recent prose automatically.

### 13.3 Compaction

A compaction summary is an immutable source-linked context artefact containing covered event/message ranges, source hashes, compiler/summarizer identity, omissions, uncertainty, and expiry triggers. It may replace repetitive non-governing narrative in a packet. A compaction summary may never, at any risk tier, replace an exact governing rule, amendment, decision, contract assertion, or review verdict. For R2/R3 work it additionally cannot replace the exact subject artefact required for the purpose.

### 13.4 Consolidation

Session output or repeated retrieval proposes memory; it does not write accepted memory directly. Consolidation:

1. identifies candidate claims and source evidence;
2. deduplicates against current accepted memory;
3. checks authority, contradictions, scope, and sensitivity;
4. requests the required review;
5. accepts, rejects, or supersedes through an attributed command.

No full transcript or hidden reasoning is promoted.

## 14. Checkable context independence

### 14.1 Shared interface

W3 freezes these independence inputs for W4/W5:

- producer and verifier actor, role, session, model family/version, and context IDs/hashes;
- exact subject artefact/object hashes visible to the verifier;
- compiler run and context-policy versions;
- source-overlap set and overlap classes;
- excluded producer attempt material, conclusions, recommendations, and traces;
- trace-visibility policy and any authorized exceptions;
- shared mandatory governance sources distinguished from producer-derived sources;
- delivery receipts and source positions.

W4 computes the required grade and routing eligibility. W5 decides which assurance gate consumes it. W3 supplies evidence and fails compilation when a declared exclusion cannot be met.

### 14.2 Independent verifier packet rules

- The independent verifier receives the exact subject required for inspection.
- Governing designs, contracts, amendments, and objective evidence may overlap with the producer packet and are labeled `shared_governance`.
- Producer conclusions, answer summaries, recommendations, and hidden reasoning are excluded unless a versioned bounded delta-review policy requires exposure and the use is attributed. Manager may authorize an allowed R2 exposure; Stephen authorizes R3 exposure. Exposure changes the recorded independence profile and never permits hidden-reasoning inheritance.
- The independent verifier packet has a distinct context ID/hash and compiler run.
- Same-source or same-family risk is recorded, never described as independent human review.
- If required diversity or exclusion is unavailable, the review gate returns `unable_to_satisfy_independence`; no independent verifier packet or lower grade is silently substituted.

## 15. Security, privacy, and retention boundary

Packets and manifests must:

- exclude credentials, provider tokens, `.env` contents, and secret values;
- exclude raw UKDA or participant-level restricted data; use opaque access references and approved tools instead;
- exclude full transcripts and hidden chain-of-thought;
- minimize excerpts and retain only what the declared purpose requires;
- classify every source and packet by sensitivity and permitted consumers;
- hash/redact sensitive locators while preserving a stable root/source identity for audit;
- record prompt-injection or untrusted-source classification where applicable;
- obey W6 retention policy once specified.

If a required source cannot be represented safely, compilation fails and reports the access/assurance gap. It does not copy the source into the packet to make progress.

## 16. Failure behavior

| Failure | Required result |
|---|---|
| Mandatory source missing or unreadable | Fail compilation; list source and owning authority |
| Effective amendment omitted | Fail F-021 gate; no readiness/review satisfaction |
| Reference-token profile gate or bound-provider capacity gate fails | `context_budget_exceeded`; report section 8.3 evidence/safe options; no packet issued; W4 may evaluate another eligible route explicitly |
| Exact provider count and evaluated upper bound both unavailable | Route ineligible; no packet issued or delivery attempted |
| Governing conflict unresolved | Fail closed with both sources and decision owner |
| Optional index stale/unavailable | Use direct retrieval and record fallback; never trust stale hit |
| Direct mandatory freshness unverifiable | Fail R2/R3; apply only an explicitly allowed R0/R1 degraded policy |
| Required skill/procedure version unavailable | Fail if mandatory; otherwise omit with typed reason |
| Packet contains prohibited content | Quarantine candidate packet, emit sanitized incident evidence, and do not deliver |
| Independence exclusion cannot be met | No independent verifier packet satisfying the requested grade |
| Base packet discovered incomplete after issue | Mark failed/superseded; compile a new complete packet; do not patch silently |
| Delivery hash mismatch | Reject delivery and preserve diagnostic evidence |

## 17. Shared W4/W5 interface freeze

### 17.1 W4 consumes

- role/profile, purpose, risk tier, policy and budget profile;
- mandatory capability and provider usable-input requirement;
- compiled candidate bytes/hash, UTF-8 size, reference-tokenizer identity/count, and cumulative addendum counts;
- bound-provider tokenizer identity/count or evaluated upper-bound identity/count, usable-input capacity, and reserve outcome supplied through W7;
- context IDs/hashes, actor/session/model metadata, overlap, exclusions, and freshness;
- unavailable-provider, token-accounting-unavailable, context-budget-exceeded, or unable-to-satisfy-independence outcomes.

W3 may expose a compiled, unissued candidate to W4/W7 only for evaluated routing and counting. W4 selects an eligible provider/model/profile; W7 supplies the exact provider count or evaluated upper bound; W3 validates both token gates and issues only after one route passes. A failed candidate returns to W4 explicitly. W4 cannot ask W3 to omit mandatory evidence to fit a weaker model, and W3 does not silently choose another route.

### 17.2 W5 consumes

- assurance lanes and governing design/amendment/contract/decision references;
- exact subject and evidence hashes;
- machine-checkable and human-review-only questions;
- result, Partial, supersession, and claim restrictions;
- included/omitted governing sources and reviewer visibility evidence.

W5 may add domain-specific mandatory source classes through a reviewed pack. It cannot change W3 lifecycle, budget, authority, or security semantics.

### 17.3 Freeze rule

W4 and W5 may proceed in parallel only after W3 review accepts the field meanings and failure behavior in sections 6–17. Later changes to those shared fields require a bounded delta review of both consumers.

## 18. Gate 1 fixtures and acceptance metrics

W3 does not materialize executable fixtures, but it fixes the minimum fixture designs that foundation-critical W6 must implement.

### 18.1 F-025 representative orchestrator fixture

Use a minimized/synthetic reconstruction of the Stage 2 scope-collapse family, not live APM state. The context request must retrieve:

- the exact ScopeDefinition/Plan revision and all required members;
- the stronger evidence that only the Wave-1 subset was accepted;
- W0/addendum source precedence and unresolved scope status;
- the applicable P-026/P-027 successor boundary;
- the decision authority required to amend scope.

Distractor Tracker/memory prose asserts completion. The packet must retain it only as a stale/lower-authority conflict and must not recommend full-stage completion.

### 18.2 F-026 representative implementer fixture

Use a minimized historical/synthetic bundle from F-011/F-012/F-013, not T1.28. The request must retrieve:

- frozen representation and exact transform identity;
- null-operation requirement and independent no-op preflight;
- input vintage/hash coherence;
- parameters/seeds/roots/output schema;
- stop/Partial rules and prohibited refit/approximation shortcuts.

Distractors include an older refitting procedure, a stale input, and a plausible producer-emitted `passed` flag.

### 18.3 Amendment and independence fixtures

- **F-021:** a governing amendment exists but the baseline request retrieves only the earlier design. Pre-control must fail; post-control includes the amendment and records the stale predecessor.
- **F-022:** producer and verifier share producer-derived conclusions. Pre-control independence fails; post-control gives the verifier the exact subject plus shared governance while excluding conclusions/hidden reasoning.
- **F-027:** optional-index deletion must produce the same mandatory packet through direct retrieval.
- **F-028:** either token-gate overflow must fail rather than omit a governing item.
- **F-029:** safe optional distractor variation must not change the mandatory packet or terminal decision.
- **F-030:** addenda preserve immutable lineage and cumulative compliance; an incomplete mandatory base is superseded rather than patched.

### 18.4 Required metrics

For the Gate 1 fixture set:

- mandatory governing-source recall: `1.0`;
- effective-amendment recall: `1.0`;
- manifest provenance completeness for included mandatory fragments: `1.0`;
- prohibited secret/restricted/transcript/hidden-reasoning inclusion: `0`;
- superseded or stale source presented as current authority: `0`;
- mandatory omission in an issued packet: `0`;
- reference-token and bound-provider capacity-gate compliance, including cumulative addenda: `1.0`;
- direct-retrieval equivalence after optional-index deletion: `1.0` for the mandatory fragment set, order, versions, and hashes;
- independence exclusion/overlap classification accuracy: `1.0` on F-022 cases.

The representative orchestrator packet must fit at or below 48,000 reference tokens and the representative R2 implementer/independent-verifier packet at or below 32,000 reference tokens; each must also pass its bound-provider capacity gate. The 48,000 ceiling is nominally 40% below the approximately 80,000-token word-to-token heuristic for generic Manager preload. That baseline is not a like-for-like mandatory-closure measurement and excludes task-specific sources.

Before a context compiler or provider/profile combination passes Gate 1, W6 materialization must empirically size the mandatory closure for F-025, F-026, F-021, and F-022 under both token gates. An over-ceiling closure is a blocking design signal requiring an evidence-backed profile change or explicit decomposition that preserves cross-cutting governing evidence. Written acceptance of W3 does not assert that executable sizing already exists.

Aggregate recall cannot compensate for one missed governing source. Each fixture is a non-aggregated gate.

## 19. Verification programme

### 19.1 Deterministic contract checks

Implementation planning must provide tests for:

- manifest and included/omission/conflict entry schemas;
- canonical source/excerpt hashes and packet/addendum hashes;
- deterministic mandatory closure and packing order;
- reference-token and bound-provider capacity-gate calculation, provider reserve, tokenizer/upper-bound identity, and cumulative addenda;
- source precedence, amendments, supersession, freshness, and currency triggers;
- direct retrieval fallback and index non-authority;
- packet immutability, reuse validation, and delivery receipts;
- memory/procedure lifecycle and source links;
- security/redaction rejection;
- independence overlap/exclusion evidence.

### 19.2 Adversarial review questions

1. Can a packet meet the size ceiling by hiding an omitted governing item?
2. Can an index or summary become authority when direct evidence disagrees?
3. Can a nominal verifier inherit the producer's conclusion while the manifest still claims independence?
4. Can stale memory or a procedure override a current amendment, Task, contract, or decision?
5. Can an unsafe source be copied into context because it is mandatory?
6. Do hard ceilings encourage risky task decomposition or loss of cross-cutting evidence?

### 19.3 Research-assurance classification

W3 directly touches **Output/Provenance** and **Paper Claim governance**. It carries governing-source fields for topology, stochastic/null, statistical/panel, and representation work but changes no formula, estimand, null, representation, topological object, result, or paper claim.

Machine-checkable claims include source identity/version/hash, mandatory closure, amendment inclusion, packet size, omission class, freshness, security exclusion, packet/addendum lineage, subject hash, and independence evidence. Human review decides whether the mandatory source policies and role/risk ceilings are epistemically sufficient and operationally proportionate.

## 20. Constraints passed downstream

### W4

Define role permissions, model/eval thresholds, routing, fallback, and independence grades over W3's frozen request, budget, packet, overlap, and failure fields. No route may weaken a mandatory context rule.

### W5

Define assurance-lane source requirements, domain-pack additions, review questions, and result-to-claim gates using W3 manifests. Governing scientific material cannot be optional for convenience.

### W6

Materialize F-021/F-022 and F-025–F-030 under the dated W6 addendum, normalize traces for compilation/retrieval/delivery, measure mandatory closure under both token gates, calibrate pre/post behavior, and enforce the non-aggregated metrics in section 18.

### W7

Map packet delivery and token accounting to Claude/Codex while preserving exact content hashes, provider reserve, security exclusions, and semantic parity.

### W8

Define operational context for resource grants, checkpoints, process identity, heartbeats, recovery, and operator commands without mixing process state into durable memory.

### W9/W10

Keep legacy imports source-linked and non-authoritative until adoption; provide minimal R0/R1 and non-TDA context profiles without TDL paths or topology assumptions.

## 21. W3 review gate

W3 moved from `review_pending` to `accepted` under P-028 after the adversarial review, approved reconciliation, and bounded delta review confirmed that:

- [x] Immutable base packets plus append-only addenda are the correct working-context model.
- [x] Event history, projected state, declarative memory, procedural memory, examples, working context, and traces remain distinct.
- [x] Mandatory source closure is complete by role/risk/assurance purpose and cannot be displaced by budget.
- [x] R0/R1/R2/R3 reference ceilings, the separate provider-capacity gate, and the 20% reserve are explicit; empirical fixture fit remains a W6 release precondition.
- [x] Packet, manifest, included-source, omission, conflict, freshness, and addendum fields are sufficient for W4/W5.
- [x] Direct sources remain authoritative and F-027 binds optional-index deletion equivalence.
- [x] Compaction and memory cannot supersede governing evidence at any risk tier.
- [x] Staleness, conflict, overflow, delivery mismatch, accounting unavailability, and unsafe-source failures close conservatively.
- [x] Independent verifier packets expose the exact subject while excluding producer conclusions and hidden reasoning except through attributed policy-bound delta exposure.
- [x] Secrets, raw restricted data, full transcripts, and hidden reasoning are excluded.
- [x] F-025–F-030 and the non-aggregated metrics are bound; executable achievement and closure sizing remain W6 materialization gates.
- [x] W3 introduces no runtime, migration, active APM write, or research-claim change.
- [x] W4 and W5 can proceed independently across the frozen interface in section 17.

## 22. W3 outcome

**Outcome:** `ACCEPTED_SPECIFICATION — W3 v0.2 shared interface frozen under P-028; executable Gate 1 evidence and foundation implementation remain gated`.

W4 and W5 may now begin in parallel across section 17. W6 must materialize and size the reserved retrieval fixtures before a context compiler/provider profile can pass Gate 1. Foundation implementation remains prohibited until the remaining P-026 gates and a separately approved implementation plan are complete.
