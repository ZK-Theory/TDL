# W5 — Research Assurance and Independent-Review Specification

**Date:** 2026-06-30<br>
**Status:** Draft complete; written-specification review pending<br>
**Specification version:** 0.1<br>
**Design authority:** Accepted W1 v0.3, W2 v0.3, W3 v0.2, W6 catalogue/addendum, D-001–D-008, P-001–P-028, and Stephen's approved W4/W5 conceptual design<br>
**Implementation authority:** None; this document creates no assurance packs, contracts, graders, reviews, claims, runtime, migration, or `.research-system/` state<br>
**Review owner:** Stephen; bounded joint W4/W5 adversarial review required

## Review record

- **Responsibility boundary:** Stephen approved W5-owned assurance requirements and W4-owned route selection; neither may weaken or absorb the other.
- **Assurance mechanics:** Stephen approved core lanes plus reviewed domain packs, two-key validity, conservative Partial/negative handling, and explicit claim promotion.
- **Authority mechanics:** Stephen approved P-022/P-023 independence, Manager acceptance for verified R2 work, and Stephen-reserved R3/P-005 transitions.
- **Written specification:** Review pending.
- **Implementation:** Prohibited until the complete P-026 gate sequence and a separately approved implementation plan.

## 1. Decision summary

W5 turns research validity from informal prose into versioned requirements, evidence, scientific review, and human decisions without pretending that every judgment is deterministic.

The specification makes these binding choices, subject to the W4/W5 review gate:

1. W5 emits an immutable `AssuranceRequirement`; W4 selects a route that satisfies it. W5 cannot select a provider/model, and W4 cannot weaken the requirement.
2. Core assurance lanes are topology, stochastic/null, statistical/panel, representation, output/provenance, and paper claim. Reviewed domain packs extend lane content without changing core lifecycle or authority.
3. R2/R3 validity uses two non-substitutable keys: deterministic/structural evidence and scientific review/decision. Neither compensates for failure of the other.
4. Every assurance requirement separates machine-checkable claims, model/rubric judgments, and human-authority questions. A structural pass is never scientific acceptance by itself.
5. Pre-registrations, governing designs, amendments, contracts, results, reviews, and claims remain distinct immutable objects with explicit supersession and effective scope.
6. An implementer cannot be the sole author, activator, verifier, reviewer, and acceptor of its own R2/R3 rule or result.
7. Scientific property graders recompute or independently bound properties from immutable inputs; producer-emitted pass flags and sanity targets are not proof.
8. Result acceptance and claim promotion are separate. A result can be accepted for bounded consumers while a stronger claim remains prohibited.
9. Partial, negative, rejected, superseded, and unable-to-grade outcomes are preserved as evidence and never rewritten into Success or silently dropped.
10. Qualitative/non-computational work may mark an inapplicable quantitative validator `not_applicable`; provenance, lifecycle, source boundaries, review, authority, limitations, and claim controls still apply.

These choices freeze W5's assurance-plan, pack, contract, proof-obligation, scientific-review, result-disposition, and claim-promotion semantics. They do not define domain formulas, executable contracts, numerical W6 thresholds, provider routes, runtime, or manuscript claims.

## 2. Sources and research-assurance triage

W5 implements:

- W1 sections 5, 8, 9, 14, 16, and 18: assurance component ownership, dependency direction, authority separation, invariants, verification, and W5 constraints;
- W2 Task assurance requirements, ValidationRecord, Review, Decision, Artefact, Result, Partial, supersession, claim restriction, and consumer fields;
- W3 sections 5–17: governing-source classes, immutable context, omissions, freshness, exact subject hashes, reviewer visibility, and independence evidence;
- W4 risk/profile/route/independence contract without selecting a provider/model;
- W6 F-007–F-019, F-021–F-024, F-026, F-028–F-029, and associated deterministic, trajectory, research, model, human, operational, and privacy graders;
- P-005/P-022 human and review authority, P-023 independent scientific-property grading, P-024 fixture provenance, P-025 proportional qualitative support, P-026 successor boundary, and P-028 context/independence controls.

Research-assurance triage classifies W5 itself as touching all six lanes at the governance/interface level:

| Lane | W5 responsibility | Domain judgment deferred to |
|---|---|---|
| Topology | Require declared object, filtration, homology, metric, benchmark, and interpretation checks | TDA assurance pack and qualified reviewer |
| Stochastic / Null | Require exchangeability/null operation, RNG, denominator, p-value, mutation, and invariance checks | Statistical/TDA pack and qualified reviewer |
| Statistical / Panel | Require estimand, eligibility, denominator, missingness, variance, multiplicity, and sensitivity checks | Statistical/social-research pack and qualified reviewer |
| Representation | Require fit/transform boundary, frozen identity, comparability, recoding, and vintage checks | Representation pack and qualified reviewer |
| Output / Provenance | Require immutable manifests, inputs, parameters, seeds, roots, schemas, no-overwrite, and reproducibility evidence | Core pack plus domain schema/contract |
| Paper Claim | Require result-to-prose trace, allowed strength, limitations, disclosure, and human claim decision | Claim pack and Stephen |

W5 changes no formula, null operation, estimand, representation, topological object, result, or claim in this design pass.

## 3. Scope and non-goals

### 3.1 In scope

- assurance requirement and plan fields, lifecycle, identity, and currency;
- core assurance lanes and reviewed domain-pack interface;
- epistemic-risk floor and required independence relationship;
- pre-registration/design/amendment lifecycle and binding;
- contract ownership, activation, validation, and review separation;
- machine-checkable, model/rubric, and human-review-only claims;
- proof obligations, counterexamples, metamorphic tests, benchmarks, and degeneracy checks;
- assurance execution, evidence sets, verdicts, Partial/negative handling, and supersession;
- result acceptance, consumer restrictions, and claim promotion;
- TDA, statistical/social-research, and qualitative pack requirements;
- W4/W6/W9/W10 interface constraints.

### 3.2 Deferred

- exact domain formulas and project-specific decision rules: domain packs/pre-registrations;
- executable contract schema/library and hook implementation: implementation plan and contract work;
- exact W6 thresholds, grader prompts, calibration corpus, dashboards, and retention;
- provider/model/profile choice and routing: W4;
- provider adapters: W7;
- runtime/resource/checkpoint assurance: W8;
- migration/import and pilot workflows: W9;
- reusable project-pack distribution: W10.

### 3.3 Non-goals

- replacing scientific judgment with JSON schema validation or one model score;
- letting an implementer activate and solely approve its own R2/R3 governing rule;
- treating expected/sanity values as targets to reproduce;
- trusting producer pass flags, nominal role labels, or prose `Success` as scientific evidence;
- inferring causal, novelty, or generality claims from structurally accepted computation;
- requiring quantitative validators for qualitative artefacts where they are conceptually inapplicable;
- copying raw restricted data, secrets, full transcripts, or hidden reasoning into assurance records;
- using active T1.28/APM work as an assurance experiment.

## 4. Options considered

### 4.1 Deterministic contracts as complete assurance

All validity is reduced to executable assertions.

**Benefit:** Fast, reproducible, and easy to gate.<br>
**Cost:** Conceptual direction, estimands, null validity, interpretation, and claim strength cannot be completely encoded; false certainty becomes likely.<br>
**Decision:** Rejected.

### 4.2 Independent model review as complete assurance

A second model judges all scientific adequacy.

**Benefit:** Broad coverage without authoring every property.<br>
**Cost:** Correlated error, non-reproducible judgment, weak calibration, and no protection from plausible producer/model consensus.<br>
**Decision:** Rejected.

### 4.3 Two-key validity with domain packs

Deterministic/structural evidence and independent scientific review are both required where applicable; packs state domain-specific obligations.

**Benefit:** Checkable core, honest human/model limits, domain extensibility, and non-compensable gates.<br>
**Cost:** More explicit records and calibrated review infrastructure.<br>
**Decision:** Selected.

## 5. Shared W4/W3/W2 contract

### 5.1 W5 produces

W5 produces an immutable `AssuranceRequirement` before governed R2/R3 dispatch and whenever policy requires one for R0/R1. It identifies what must be true, what evidence must exist, who may judge it, and what happens if evidence is missing.

### 5.2 W4 consumes

W4 consumes required capabilities, effective risk floor, context/independence relationship, tool/data constraints, and human gates. W4 returns a `RouteDecision` or typed failure. Route success proves only that an eligible actor/profile/model/context can attempt the work; it does not prove the work valid.

### 5.3 W3 supplies

W3 supplies the exact governing sources, subject/evidence hashes, omissions/conflicts, freshness, and producer/verifier visibility needed to grade compliance. Missing or unsafe mandatory context blocks the assurance gate.

### 5.4 W2 records

W2 commands/events bind assurance requirements, validation records, reviews, decisions, results, artefacts, claims, and consumer restrictions. W5 never mutates lifecycle from prose or model output.

## 6. Identity and lifecycle

### 6.1 Core identities

```text
assurance_requirement_id  asr_...
assurance_pack_id         asp_...
governing_rule_id         grl_...
proof_obligation_id       pob_...
assurance_evidence_id     aev_...
assurance_verdict_id      avd_...
claim_candidate_id        clm_...
claim_decision_id         cld_...
```

Every object has a revision, content hash, source position, effective scope/time, owner, review state, supersession lineage, and currency triggers. Names, paper sections, Task numbers, and filenames are aliases.

### 6.2 Assurance requirement lifecycle

```text
draft -> review_pending -> accepted
draft/review_pending -> rejected
accepted -> amended | superseded | retired
```

R2/R3 producing work cannot satisfy readiness from a draft requirement. An accepted amendment creates a new revision, stales affected context/route decisions, and pauses or supersedes incompatible work through W2; it never edits the prior rule in place.

### 6.3 Evidence/verdict lifecycle

```text
required -> submitted -> validated -> reviewed -> accepted | rejected | partial
submitted/validated/reviewed -> unable_to_grade
accepted/rejected/partial/unable_to_grade -> superseded
```

Each stage is a separate record. `unable_to_grade` and missing required evidence never become pass. New evidence or reviewer availability creates a new linked submission/verdict that may supersede the earlier record; it never edits `unable_to_grade` in place.

## 7. `AssuranceRequirement` contract

Required fields include:

- identity/revision/hash, Task/revision, purpose, owner, and expected control-store position;
- requested and W5 epistemic risk floor with raising rationale;
- assurance lanes and domain-pack IDs/revisions;
- governing pre-registration/design/amendment/decision/contract/source IDs/hashes;
- subject artefact/result/claim types and expected immutable identity;
- machine-checkable proof obligations and independent-property methods;
- model/rubric questions, hidden oracle references, calibration relationship, and acceptable limitations;
- human-review-only questions and decision authority;
- required review roles, W4 capability classes, and minimum independence grade;
- exact subject/evidence visibility and prohibited producer conclusions/trace exposure;
- parameters, seeds, input vintages, representations, roots, schemas, consumer predicates, and no-overwrite requirements where applicable;
- expected counterexamples, metamorphic tests, benchmarks, degenerate paths, and sanity values as falsification inputs;
- stop, escalation, Partial, negative, supersession, and claim-restriction rules;
- security/sensitivity, expiry, currency triggers, and prohibited actions/claims.

An irrelevant field is explicit `not_applicable` with rationale and authority; it is not silently absent.

## 8. Assurance lanes and pack interface

### 8.1 Core lane contract

Every lane entry declares:

- touched/not-applicable status and rationale;
- governing sources/rules and exact version/hash;
- required inputs/parameters/identities;
- machine-checkable assertions and enforcing artefacts;
- human/model review questions and reviewer capability;
- counterexamples/mutations/benchmarks;
- evidence outputs and consumer restrictions;
- Partial/failure/claim consequence.

### 8.2 Domain packs

A domain pack may add:

- registered lane subtypes and terminology;
- mandatory source classes and pre-registration templates;
- formulas, parameter schemas, property checks, benchmark fixtures, and review rubrics;
- output/claim schemas, disclosure language, and domain-specific prohibited shortcuts;
- required W4 capability classes and W6 fixtures.

A pack cannot:

- change W1/W2 lifecycle, canonical authority, or P-005/P-022 human gates;
- lower W3 context/security requirements or W4 risk/independence evidence;
- override a stronger project pre-registration/amendment;
- declare its own implementation scientifically accepted;
- turn a `not_applicable`, `unable_to_grade`, Partial, or failed proof into pass.

### 8.3 Pack lifecycle

```text
draft -> source_verified -> reviewed -> accepted
draft/reviewed -> rejected
accepted -> superseded | retired
```

Acceptance binds pack version, source authority, supported project classes, required fixtures, known limitations, and approving authority.

## 9. Epistemic risk floor

W5 sets a minimum risk based on scientific consequence:

| Condition | Minimum |
|---|---|
| Purely mechanical/provenance operation with no scientific interpretation | R0 or R1 as policy declares |
| Stable-spec implementation that cannot alter scientific object/estimand/null/representation/claim | R1 |
| Implementation, correction, or verification affecting scientific evidence validity | R2 |
| New/amended methodology or pre-registration; claim promotion; causal/novelty/generalisation decision; P-005 transition | R3 |

When multiple lanes apply, the strongest floor controls. W4/W8 may raise but never lower it. Ambiguity blocks or raises under explicit policy.

## 10. Pre-registration, design, and amendment control

### 10.1 Governing design

An R2/R3 design records:

- research question, estimand/object, population/data, representation, method, null/comparator, parameters, inference, multiplicity, decision rule, outputs, stop/Partial rules, and claim boundary as applicable;
- source authority, author, reviewer, approving authority, effective scope, and amendment policy;
- machine-checkable versus human-review-only obligations;
- uncertainty, limitations, and prohibited shortcuts.

### 10.2 Amendment

An amendment records:

- exact predecessor rule/hash and affected scope;
- reason and new evidence;
- changed and unchanged clauses;
- impact on existing Tasks, contexts, routes, attempts, artefacts, results, and claims;
- required reanalysis/review or allowed grandfathering;
- Stephen's attributed decision where P-005 applies.

An amendment is accepted before dependent producing work continues. Post-hoc changes cannot be disguised as interpretation or a memory update. W3 F-021 and currency rules must surface every effective amendment.

### 10.3 Exploratory work

Exploration may precede a pre-registration only when marked exploratory, kept from confirmatory claim promotion, and governed by an explicit scope/output boundary. It cannot silently become confirmatory evidence.

## 11. Contract ownership and activation

### 11.1 Separation

For R2/R3 work, record distinct authorities for:

- governing design/rule ownership;
- contract/assertion implementation;
- producing implementation/analysis;
- independent property verification;
- scientific review;
- Manager/human acceptance.

One human may occupy several programme roles, but the system records contextual/model separation honestly and does not claim independent humans. No producing actor may solely activate and approve the contract that certifies its own work.

### 11.2 Contract activation

Before activation, a contract must bind:

- governing rule and subject/input/output schemas;
- assertion semantics, tolerances, normal and degenerate regimes;
- independent oracle/recomputation method;
- positive, negative, boundary, mutation, and no-op cases;
- failure consequence and prohibited claims;
- owner, implementer, reviewer, version/hash, and W6 fixtures.

A schema-only check may establish shape and provenance but not a scientific property unless that property is independently recomputed or bounded.

## 12. Claim classification

Every required assertion is classified as one of:

| Class | Meaning | Required evidence |
|---|---|---|
| D — deterministic | Exact identity, schema, formula implementation, invariant, number, path, or independently recomputable property | Versioned executable assertion plus immutable inputs/evidence |
| T — trajectory | Required/forbidden action, order, authority, tool, stop, or lifecycle behavior | Normalized trace predicate |
| R — research rubric | Conceptual direction, validity of method/object/estimand/null, interpretation, limitation | Qualified rubric review with evidence and limitations |
| M — independent model | Bounded judgment useful for calibrated review | Hidden/blinded oracle, declared producer relationship, W4 independence grade |
| H — human authority | Methodological fork, pre-registration change, claim strength, novelty, ethics, or governance | Attributed decision by named authority |
| O/P — operational/privacy | Runtime/resource/recovery or security/restricted-data property | Operational/privacy grader and evidence |

One assertion may require multiple classes. A D/T pass cannot substitute for R/M/H; a model verdict cannot overturn a failed D/T/P gate.

## 13. Proof obligations

### 13.1 Minimum set

Where applicable, an assurance plan includes:

- independent recomputation or analytic bound;
- known-answer/benchmark case from an authoritative or explicitly synthetic source;
- counterexample demonstrating the rule can fail;
- metamorphic property under safe transformations;
- degenerate/no-op/fallback mutation;
- directionality and monotonicity checks;
- input identity/vintage/row/sample coherence;
- sensitivity/robustness comparison;
- provenance/schema/no-overwrite/reproducibility checks;
- conceptual and claim-language review.

### 13.2 Expected values are not targets

Any sanity value, approximate result, prior estimate, or lower/upper bound is recorded with source and epistemic status. The verifier independently derives or challenges it. Suspicious agreement triggers an anchoring review; “matched expectation” is not a stop rule.

### 13.3 Degenerate fallback guard

For a normal regime where a degenerate path returns a plausible constant or identity:

- the output contract excludes the degenerate constant/identity when scientifically required;
- a binding test exercises the real computation against an independent oracle;
- a mutation forces the fallback and must fail the relevant fixture;
- the producer's own `passed` flag is ignored.

### 13.4 Null-operation invariance

Any shuffle/permutation/bootstrap/null operation must demonstrate that it perturbs the object used by the test statistic while preserving the intended invariants. A no-op at the tested-object level blocks inference.

## 14. Lane-specific minimum requirements

### 14.1 Topology

- filtration/complex/object and homology dimensions;
- coefficient field, metric/order, threshold/truncation, landmark rule, and essential-class handling;
- benchmark/known cases and scaling/direction checks;
- subject diagram/landscape/Mapper/other identity and interpretation limits;
- explicit distinction between topology, geometry, association, and causal claims.

### 14.2 Stochastic / null

- null hypothesis, operation, exchangeability/conditioning, Markov order/strata, sampling unit, B, seed/RNG, denominator, and p-value formula;
- null-operation tested-object change and independent no-op preflight;
- checkpoint/resume equivalence and multiplicity family where applicable;
- separation of diagnostic null-null quantities from inferential denominators.

### 14.3 Statistical / panel

- estimand, target population, eligibility/denominator, clustering/dependence, missingness/imputation, weights/trimming, variance, multiplicity, and sensitivity;
- formula and software procedure tied to governing design;
- boundary/sparse/separation cases and appropriate robust/alternative method;
- descriptive, associational, predictive, and causal claim distinction.

### 14.4 Representation

- fit versus transform authority, frozen model/loadings/scaler/labels, training population, state recoding, windows, dimensions, and vintages;
- fingerprint/hash and transform-only checks;
- comparability across waves/cohorts/subgroups and prohibited refit/fallback paths;
- representation uncertainty and sensitivity where claim-relevant.

### 14.5 Output / provenance

- immutable artefact/input IDs/hashes, code/environment, parameters, seeds, sample restrictions, roots, date suffix, no-overwrite, schema, cache lineage, and regenerability;
- consumer-required comparison fields and scoped supersession;
- evidence that validation ran against the exact accepted bytes;
- vault/claim routing only when separately authorized.

### 14.6 Paper claim

- exact accepted result/evidence IDs/hashes;
- governing decision rule and whether it was met;
- proposed wording, claim type/strength, population/domain scope, uncertainty, limitations, negative/Partial restrictions, and disclosure;
- independent claim review and Stephen's attributed promotion decision;
- no causal, novelty, or generality escalation beyond identification/evidence.

## 15. Initial domain packs

### 15.1 TDA pack

The first TDA pack combines topology, stochastic/null, representation, provenance, and claim lanes. It references existing contracts/skills by version rather than copying them. It must cover persistence construction, W2 convention, filtration/landmark choices, Markov/null design, tested-object invariance, frozen representation, output schema/provenance, benchmark validation, and topology-to-claim limits.

### 15.2 Statistical/social-research pack

This pack covers panel estimands, eligibility/denominators, weights, missingness/imputation, clustering, multiplicity, longitudinal comparability, harmonisation, sensitivity, and result-to-social-science claim language. It can be used without topology assumptions.

### 15.3 Qualitative/mixed-methods pack

This pack requires source/coding boundaries, provenance, researcher decisions, audit trail, saturation/negative-case handling where claimed, reflexive/interpretive limitations, review lineage, and claim promotion. Quantitative scientific D assertions may be `not_applicable`; source identity, lifecycle, authority, review, privacy, and claim controls may not.

## 16. Independent review

### 16.1 Review request

Every scientific review binds:

- assurance requirement and governing-rule revisions;
- exact subject/input/output/evidence hashes;
- review questions by assertion class and lane;
- required W4 reviewer capability and independence grade;
- allowed governing overlap and excluded producer material;
- required tools/contracts/benchmarks and known limitations;
- acceptable verdicts and authority consuming the verdict.

### 16.2 Review evidence

The review records actor/profile/session/provider/model/family, context manifest, subject hash, producing-attempt relationship, trace visibility, tools/evidence used, findings, limitations, and established independence grade. Self-attestation is not evidence.

### 16.3 Verdicts

```text
pass | fail | approve_with_conditions | unable_to_grade | superseded
```

Conditions satisfy a gate only when policy declares them non-blocking, identifies an owner/deadline, and constrains consumers/claims. `unable_to_grade` blocks required acceptance.

## 17. Two-key validity and acceptance

### 17.1 Key A — checkable evidence

Every required D/T/P/O assertion passes against the exact immutable subject and inputs. Required R properties with independent executable bounds are included here only for the bounded property established.

### 17.2 Key B — scientific authority

Every required R/M/H question receives the declared review/decision with the required W4 independence grade and subject identity. Missing diversity or human authority is blocking.

### 17.3 Pass rule

```text
assurance_pass = all_required_key_A_pass
                 and all_required_key_B_pass
                 and no_forbidden_state_or_claim
```

No weighted score, majority vote, model confidence, operational success, or accepted schema compensates for a failed required key.

### 17.4 Acceptance authority

- R0/R1: Manager may accept under delegated policy; only applicable keys are required.
- R2: Manager accepts after both keys and the required distinct verifier relationship pass.
- R3/P-005: Stephen decides after both keys and required cross-family/cross-context evidence.

## 18. Partial, negative, rejected, and superseded outcomes

### 18.1 Partial

Partial records completed/unmet obligations, valid/invalid/unverified artefacts, blockers, consumer permissions, claim restrictions, and resume/supersession policy. Useful bounded evidence may be accepted for named consumers without satisfying the full Task or claim.

### 18.2 Negative

A well-executed negative result can be accepted as evidence when the governing design, provenance, checks, review, and decision rule pass. It does not become failure merely because the expected effect/topology/association is absent.

### 18.3 Rejected

Rejected work remains immutable with reason, evidence, prohibited consumers/claims, and supersession options. Deletion or silent replacement is prohibited.

### 18.4 Superseded

Supersession is multidimensional. A result may lose claim authority while remaining valid for comparison, audit, or method development. Every consumer class is explicit.

## 19. Result acceptance and claim promotion

### 19.1 Result acceptance

A result decision records:

- accepted/rejected/Partial/superseded status;
- exact artefact/evidence/assurance/verdict IDs/hashes;
- scope, population, method, limitations, and uncertainty;
- allowed and prohibited consumers;
- unresolved conflicts and required future work;
- deciding actor/authority and source position.

Acceptance does not edit the result artefact and does not promote a paper claim automatically.

### 19.2 Claim candidate

A `ClaimCandidate` records:

- exact result/evidence/decision sources;
- proposed text or structured claim;
- claim type: descriptive, associational, predictive, causal, methodological, novelty, generality, or other registered type;
- estimand/object/population/domain and uncertainty;
- governing decision-rule outcome;
- limitations, negative/Partial/sensitivity disclosures, and prohibited stronger language;
- manuscript/table/figure consumers;
- independent review and human-decision requirements.

### 19.3 Promotion

Claim promotion requires:

1. accepted source results for the declared consumer;
2. complete provenance and current governing design/amendments;
3. satisfied claim-lane proof/review obligations;
4. exact wording/strength review;
5. Stephen's attributed decision under P-005;
6. a new immutable claim-decision record.

`RuleEvaluation`, result acceptance, reviewer recommendation, or manuscript prose is not claim-promotion authority.

### 19.4 Claim lifecycle

```text
draft -> review_pending -> approved_wording | restricted | rejected
approved_wording/restricted -> promoted
approved_wording/restricted/rejected/promoted -> superseded
```

Every promoted claim binds the exact approved text/hash, evidence/result set, limitations, consumers, and Stephen's decision. A wording change that alters strength, population, estimand, causal status, novelty, or generality creates a new candidate and review; manuscript editing cannot mutate a promoted claim silently.

## 20. Assurance execution sequence

1. Resolve Task/revision, purpose, current governing sources, and source position.
2. Classify lanes and W5 epistemic risk floor.
3. Resolve accepted domain packs and build the mandatory assurance closure.
4. Classify assertions as D/T/R/M/H/O/P; state `not_applicable` explicitly.
5. Bind proof obligations, evidence outputs, review questions, independence grade, human gates, and Partial/claim rules.
6. Review and accept the `AssuranceRequirement` through attributed authority.
7. W4 selects an eligible route; W3 compiles exact producer/reviewer contexts.
8. Produce immutable artefacts/evidence without self-acceptance.
9. Run independent D/T/P/O checks and bounded scientific-property recomputation.
10. Conduct required R/M/H review against the exact subject.
11. Record both-key status, failures, conditions, limitations, and consumer restrictions.
12. Submit the separately authorized W2 result/Task decision.
13. If requested, create and independently review a claim candidate; Stephen decides promotion.

## 21. Failure behavior

| Failure | Required result |
|---|---|
| Governing design/amendment missing or stale | Block readiness/review; identify owner/source |
| Required lane/pack unavailable | `assurance_requirement_incomplete`; no weaker implicit pack |
| Assertion unclassified or `not_applicable` unexplained | Block requirement acceptance |
| Contract/schema lacks independent property method | Structural check may run but cannot certify scientific property |
| Producer controls sole R2/R3 contract activation/review | Fail authority gate |
| Null operation is invariant to tested object | Block inference/result acceptance |
| Degenerate fallback passes plausible constant | Fail mutation/property gate |
| Expected value reproduced without independent derivation | Flag anchoring risk; review incomplete |
| Input/representation/vintage incoherent | Block producing/acceptance as policy declares |
| Required verifier diversity unavailable | `unable_to_grade`; no lower grade |
| Key A or Key B required failure | No assurance pass; preserve evidence and restrictions |
| Runtime/process succeeds but science fails | Task/result remains unaccepted or Partial |
| Negative result meets design | May accept as negative evidence; do not relabel failure |
| Partial lacks consumer/claim restrictions | Partial closeout rejected |
| Claim exceeds result/estimand/identification | Claim rejected/restricted; result remains independently dispositioned |
| Human-reserved decision absent | `input_required`; no promotion/amendment |

## 22. Evaluation and acceptance metrics

W5 consumes the proposed F-031–F-034 routing cases and owns proposed F-035–F-038. The IDs, priorities, and provenance are defined in W4 section 21 and remain unreserved until the joint review, Stephen's reconciliation, and a dated W6 addendum.

Foundation-critical W6 must cover:

- hidden prerequisite/guardrail and invalid-runtime projection F-007–F-009;
- downstream correction scope F-010;
- frozen representation, null invariance, and vintage coherence F-011–F-013;
- self-approved contract F-014;
- anchoring and conceptual-direction F-015–F-016;
- missing comparison fields and scoped supersession F-017–F-018;
- result-to-claim overreach F-019;
- amendment/context omission F-021;
- correlated reviewer contexts F-022;
- ambiguous human approval F-023;
- qualitative lifecycle F-024;
- implementer retrieval F-026 and overflow/distractor controls F-028–F-029;
- new pack-specific counterexamples, degenerate mutations, benchmarks, and Partial/negative/claim cases.

Required non-aggregated metrics include:

- required proof-obligation coverage: `1.0`;
- required governing-source/amendment recall: `1.0`;
- independent scientific-property recomputation/bound evidence: `1.0` where required;
- producer pass flag accepted as property proof: `0`;
- required `unable_to_grade` converted to pass: `0`;
- key-A/key-B compensation: `0`;
- human-reserved transition without attributed decision: `0`;
- unsupported stronger claim promotion: `0`;
- Partial/negative/superseded consumer-restriction completeness: `1.0`;
- qualitative quantitative-validator false requirement: `0` when correctly `not_applicable`;
- restricted data, secrets, transcripts, or hidden reasoning in assurance records: `0`.

## 23. Observability and audit

Normalized traces record:

- assurance requirement/pack/rule/proof/evidence/verdict/claim IDs and hashes;
- Task/attempt/result/artefact/context/route/authority relationships;
- assertion classifications, `not_applicable` reasons, checks, tools, benchmarks, mutations, and outputs;
- reviewer capability, actor/session/provider/model/family/context/trace relationship;
- key-A/key-B status without hidden reasoning;
- conditions, limitations, unable-to-grade, Partial, negative, rejection, and supersession;
- result consumer restrictions and exact claim-decision lineage;
- policy/pack/contract/grader versions and expiry/currency events.

Audit must reconstruct why evidence was accepted for one consumer or claim strength and prohibited for another.

## 24. Security, privacy, and retention

- Assurance records contain minimized excerpts/hashes and opaque restricted-data references, never raw UKDA records by convenience.
- Secrets, credentials, `.env` contents, full transcripts, and hidden reasoning are prohibited.
- Model/human rationale is concise and attributed; scientific evidence is the cited artefact/check/review, not hidden chain-of-thought.
- Domain packs classify permitted consumers and publication boundaries.
- Public template packs contain synthetic/minimized fixtures and no TDL-private paths or data.
- W6 retention policy governs traces/graders; accepted decisions, manifests, and claim lineage remain durable under W1/W2.

## 25. Downstream constraints

### W4

Route against immutable W5 requirements. Do not choose lanes, lower risk, drop proof obligations, substitute a lower independence grade, or treat route success as acceptance.

### W6

Materialize pack, proof, review, Partial/negative, and claim fixtures; calibrate independent model/human rubrics; preserve non-compensable gates and two-axis provenance.

### W7

Provider adapters expose review/model/context/trace identity and exact subject delivery without leaking producer conclusions or hidden reasoning contrary to W3/W5.

### W8

Operational evidence may satisfy O assertions and raise risk but cannot establish scientific adequacy or weaken stop/Partial rules.

### W9/W10

Migration retains imported evidence as provisional until explicit W5 adoption/review. Project templates provide core plus reviewed domain packs without TDL-specific assumptions.

## 26. Machine and human authority matrix

| Question | Machine may establish | Model reviewer may contribute | Human authority |
|---|---|---|---|
| Exact bytes/schema/parameters/seeds/paths | Yes | Not needed | Reviews policy exceptions |
| Independently recomputable property | Yes, within declared method/tolerance | May challenge method/coverage | Approves governing method where reserved |
| Null/estimand/representation conceptual validity | Partial checks/counterexamples | Qualified bounded review | Decides methodological forks/R3 |
| Interpretation and limitations | Evidence extraction only | Qualified review/recommendation | Accepts consequential interpretation |
| Claim strength/causality/novelty | Trace and prohibited-term checks | Independent claim review | Stephen promotes/rejects |
| Qualitative adequacy | Provenance/lifecycle checks | Independent qualitative review | Decides claim/interpretive authority |

No column silently absorbs another.

## 27. Joint W4/W5 review questions

1. Can W5 encode a provider preference that bypasses W4 evaluation?
2. Can W4 route a capable model while silently dropping a W5 lane, proof, human gate, or independence grade?
3. Can a structurally valid output satisfy both validity keys without scientific review?
4. Can the same producing actor activate, verify, and accept its own R2/R3 contract by changing role labels?
5. Can a negative or Partial result be lost because only positive Success is represented?
6. Can an accepted result be promoted to a stronger causal/novel/general claim without a separate decision?
7. Can a domain pack weaken core lifecycle, authority, privacy, or `unable_to_grade` behavior?
8. Can quantitative assurance be imposed on qualitative work where it is conceptually meaningless while provenance/review gaps remain?

## 28. Review gate

W5 can move from `review_pending` to `accepted` only when Stephen confirms after bounded joint W4/W5 review that:

- [ ] W5 assurance and W4 routing responsibilities are non-circular and independently testable.
- [ ] All six core lanes and domain-pack extension rules are complete and domain-neutral.
- [ ] Risk floors, independence, and human gates match P-005/P-022/P-023/P-025.
- [ ] Pre-registration/design/amendment lifecycle prevents silent post-hoc rule changes.
- [ ] Contract ownership prevents producer self-certification for R2/R3 work.
- [ ] Assertion classes separate deterministic, trajectory, scientific, model, human, operational, and privacy authority.
- [ ] Proof obligations cover anchoring, degenerate fallbacks, null invariance, direction, benchmarks, sensitivity, and provenance.
- [ ] Two-key validity is non-compensable and proportional where validators are not applicable.
- [ ] Partial, negative, rejected, unable-to-grade, and superseded evidence remains durable and correctly restricted.
- [ ] Result acceptance and claim promotion are separate, source-linked decisions.
- [ ] Proposed F-031–F-038 have complete priorities, provenance, oracles, graders, and W6 reservation dispositions.
- [ ] W6–W10 receive sufficient fields and fixture obligations.
- [ ] No runtime, migration, active APM write, result reinterpretation, or paper-claim change is introduced.

## 29. Outcome

**Outcome:** `REVIEW_PENDING — W5 v0.1 assurance/review specification complete; implementation and W4/W5 acceptance remain gated`.

The next action is a bounded joint adversarial review with W4. Foundation implementation remains prohibited until accepted W4/W5, frozen foundation-critical W6–W8 interfaces, combined-interface review, and a separately approved implementation plan.
