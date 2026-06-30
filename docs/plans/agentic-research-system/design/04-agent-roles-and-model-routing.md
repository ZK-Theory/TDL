# W4 — Agent Roles and Model-Routing Specification

**Date:** 2026-06-30<br>
**Status:** Accepted after joint adversarial review and reconciliation<br>
**Specification version:** 0.2<br>
**Design authority:** Accepted W1 v0.3, W2 v0.3, W3 v0.2, W6 catalogue/addenda, D-001–D-008, P-001–P-029, and Stephen's 2026-06-30 acceptance<br>
**Implementation authority:** None; this document creates no profiles, router, provider adapter, model evaluation, dispatch, runtime, migration, or `.research-system/` state<br>
**Review owner:** Stephen; bounded joint W4/W5 adversarial review completed and accepted
**Review evidence:** `../reviews/adversarial-W4-W5-review-2026-06-30.md` and `../reviews/adversarial-W4-W5-review-reconciliation-2026-06-30.md`

## Review record

- **Provider boundary:** Stephen approved a generic provider interface with only Claude and Codex eligible for first-release evaluation.
- **Responsibility boundary:** Stephen approved W5-owned assurance requirements and W4-owned route selection; neither may weaken or absorb the other.
- **Policy mechanics:** Stephen approved eligibility-first routing, non-weakenable fallback, graded independence, and the six bounded role profiles.
- **Written specification:** Joint review returned `accept_with_required_changes`; v0.2 incorporates all four Major and four Minor findings and was accepted by Stephen on 2026-06-30.
- **Implementation:** Prohibited until the complete P-026 gate sequence and a separately approved implementation plan.

## 1. Decision summary

W4 makes routing reproducible from immutable task, assurance, context, capability, provider, and authority evidence.

The specification makes these binding choices, subject to the W4/W5 review gate:

1. W5 emits the assurance and epistemic-risk floor; W4 selects an evaluated route that satisfies it. W4 cannot weaken assurance, and W5 cannot select a provider or model.
2. Routing is eligibility-first. Cost, latency, or convenience may rank only routes that already satisfy every hard gate.
3. An actor, role profile, authority grant, provider/model profile, context packet, and attempt remain distinct identities. A role label alone grants no capability, independence, or authority.
4. Six core role profiles are defined: orchestrator, Manager, implementer, independent verifier, claim reviewer, and operator/auditor.
5. Risk is monotone. W5, operations policy, or human authority may raise a task's risk floor; routing may never lower it to obtain an available model.
6. Independence is computed from evidence, not attested. R2 requires a distinct verifier context plus Manager acceptance; R3 requires cross-family/cross-context review plus Stephen.
7. The first release defines a provider-neutral interface but evaluates only Claude and Codex. Any other provider is ineligible until its adapter and capability profile pass the same gates.
8. Fallback preserves the original risk, assurance, context, tool, sensitivity, and independence requirements. No eligible fallback means a blocking outcome.
9. Multi-agent execution is refused when work is not safely decomposable, authority would become ambiguous, shared mutable state would create races, or nominal delegation would manufacture false independence.
10. Routing decisions and rejections are immutable, explainable records bound to policy, evaluation, context, provider, and task revisions.

These choices freeze the profile, route-eligibility, independence-grade, fallback, and W5 handoff semantics required by W6–W8. They do not choose specific model versions, numerical model-score thresholds, adapter implementation, runtime scheduling, or scientific acceptance.

## 2. Sources and evidence

W4 implements:

- W1 sections 5, 8, 9, 14, 16, and 18: component boundaries, dependency direction, authority, invariants, verification, and W4 constraints;
- W2 actor, authority-grant, dispatch, attempt, review, decision, model/eval-profile, context, and fixture-carrying fields;
- W3 sections 6–17: request/profile fields, risk-specific budgets, two token gates, immutable context, independence evidence, provider accounting, and fail-closed outcomes;
- W5's `AssuranceRequirement` interface and the accepted P-022/P-023/P-028 independence and grading rules;
- W6 F-001–F-005, F-007–F-020, F-022–F-023, F-025–F-030, and S-016, especially wrong-root, guardrail, self-approval, provider drift, correlated review, overflow, and outage cases;
- P-005/P-022 human authority, P-023 independent scientific-property grading, P-025 proportional profiles, P-026 successor boundary, and P-028 token/independence rules.

Provider marketing, model self-description, benchmark reputation, price, and context-window headline are not capability authority. Eligibility derives from versioned local evaluation evidence and accepted policy.

## 3. Scope and non-goals

### 3.1 In scope

- role-profile identity, fields, permissions, prohibitions, and risk ceilings;
- epistemic and operational risk-floor combination;
- provider/model/evaluation profile identity and lifecycle;
- capability taxonomy and evidence requirements;
- routing request, candidate, decision, rejection, and fallback records;
- eligibility algorithm and deterministic tie-breaking;
- graded context/model/session independence;
- human-reserved and delegated transitions;
- provider outage, accounting failure, and no-eligible-route behavior;
- multi-agent appropriateness and decomposition constraints;
- W6 evaluation gates and W7/W8 interface requirements.

### 3.2 Deferred

- exact model versions and provider adapter mechanics: W7;
- executable model evaluations, confidence thresholds, sample counts, dashboards, and retention: foundation-critical W6;
- assurance-lane content, proof obligations, scientific verdicts, and claim rules: W5;
- process scheduling, resource leases, checkpoints, and operator commands: W8;
- implementation language, package layout, CLI, service, and deployment: implementation plan;
- legacy import and pilot mechanics: W9.

### 3.3 Non-goals

- treating a role name or model name as evidence of competence;
- selecting a cheaper model by lowering risk, dropping a fixture, shrinking mandatory context, or weakening independence;
- making scientific adequacy a scalar model score;
- claiming independent human authorities in a solo programme;
- routing raw restricted data, secrets, transcripts, or hidden reasoning through a model profile;
- allowing an adapter, provider, or model to grant itself tools, roots, authority, or acceptance rights;
- using T1.28 or another active research task as a routing experiment.

## 4. Options considered

### 4.1 Combined routing and assurance policy

One subsystem selects models and decides scientific assurance.

**Benefit:** Fewer records and one policy evaluation.<br>
**Cost:** Capability, scientific adequacy, and acceptance authority become circular; a router can silently choose the assurance it can satisfy.<br>
**Decision:** Rejected.

### 4.2 Router-owned assurance grades

W4 derives assurance solely from task risk and available providers.

**Benefit:** Simple dispatch path.<br>
**Cost:** Availability can redefine validity; domain-specific proof obligations disappear behind a generic tier.<br>
**Decision:** Rejected.

### 4.3 Separate assurance requirement and route decision

W5 states the required assurance and W4 proves that one evaluated route satisfies it.

**Benefit:** Clear authority, deterministic failure, independent evolution, and no capability-to-validity shortcut.<br>
**Cost:** Requires a versioned shared interface and explicit blocked outcomes.<br>
**Decision:** Selected.

## 5. Shared W5/W3/W2 contract

### 5.1 Inputs

W4 consumes immutable references to:

- W2 Task/revision, dispatch purpose, requested risk, authority grant, roots, tool classes, sensitivity, and expected state position;
- W5 `AssuranceRequirement` revision/hash, risk floor, lanes, proof obligations, required reviewer relationship, human gates, and stop/Partial rules;
- W3 compiled but unissued context candidate bytes/hash, profile, reference-token count, provider-capacity requirement, exclusions, and independence relationship;
- W6 evaluation policy and provider/model/profile evidence revision;
- W7 provider/model/adapter availability, tokenizer/count evidence, capabilities, and policy-parity status;
- W8 operational constraints that raise risk or make a route unavailable.

### 5.2 Outputs

W4 produces either:

- an immutable `RouteDecision` naming one eligible route and the evidence satisfying each gate; or
- a typed blocking `RouteFailure` listing every candidate rejection and the exact resume condition.

Neither output mutates Task state. A separately authorized W2 command consumes it to issue or block a dispatch.

### 5.3 No circular authority

- W5 may require capability classes and independence evidence but cannot name a preferred provider/model as scientific authority.
- W4 may select among evaluated implementations but cannot modify W5 lanes, questions, proof obligations, risk floor, or human gates.
- W3 may fail context/accounting but cannot select a weaker route or assurance grade.
- W7 may report provider facts but cannot declare policy eligibility.
- W6 supplies evaluation evidence but cannot issue a dispatch or accept a scientific result.

## 6. Identity and lifecycle

### 6.1 Core identities

```text
role_profile_id          arp_...
model_eval_profile_id    mep_...
route_request_id         rrq_...
route_candidate_id       rcd_...
route_decision_id        rte_...
route_failure_id         rtf_...
independence_profile_id  ind_...
routing_evidence_snapshot_id res_...
```

IDs are provider-neutral. Provider/model names, aliases, and role slugs are versioned attributes, never identities.

### 6.2 Profile lifecycle

```text
draft -> evaluated -> eligible
draft/evaluated -> rejected
eligible -> suspended -> eligible | retired
eligible -> superseded
```

Any change to provider, model version/family, reasoning setting, tool surface, system policy, context behavior, adapter, or governing eval revision creates a new profile revision or forces reevaluation. Prior decisions retain the exact profile snapshot they used.

Every eligibility or suspension change recomputes the capability-by-family coverage map. If an R3-required capability has fewer than two currently eligible families, W4 records and surfaces `r3_family_coverage_insufficient`, stales affected producer/verifier feasibility evidence, and blocks new dependent R3 dispatch. The loss is not deferred silently until an individual route request.

### 6.3 Route lifecycle

```text
requested -> candidates_built -> evaluated -> selected
requested/candidates_built/evaluated -> blocked
selected -> consumed | expired | superseded
```

A selected route expires when its Task revision, assurance requirement, authority grant, context candidate, provider availability, evaluation profile, adapter policy, or required independence evidence becomes stale.

Every route evaluation binds a versioned `RoutingEvidenceSnapshot`. Availability, reliability, latency, cost, rate/resource state, and their observation times/sources are immutable within that snapshot. A changed or expired observation creates a new snapshot and route evaluation; deterministic equality is asserted only for requests carrying the same snapshot ID/hash.

## 7. Role-profile contract

Every role profile records:

- identity, version/hash, owner, review state, and supersession;
- role purpose and permitted Task purposes;
- capability classes and maximum risk tier;
- allowed command types and whether each requires a separate authority grant;
- permitted tool classes, roots, data sensitivity, network/provider surfaces, and write classes;
- required W3 context profile and prohibited source/trace classes;
- allowed assurance lanes and whether the role may produce, verify, review claims, operate, or accept;
- incompatible prior relationships to the same producing attempt;
- model-eval requirements, reasoning-mode requirements where exposed, and evaluation recency;
- stop, escalation, Partial, and handoff duties;
- prohibited combinations of production, verification, review, acceptance, and human-reserved authority.

Profiles declare capability; authority grants bind allowed commands to a concrete actor, subject scope, risk ceiling, and effective interval. Neither substitutes for the other.

## 8. Core role catalogue

| Role | Primary responsibility | May | Must not |
|---|---|---|---|
| Orchestrator | Decompose accepted scope and build dependency-correct work | Propose Tasks, dependencies, purposes, risks, and route requests | Amend governing scope, accept R2/R3 results, or treat plan completion as evidence completion |
| Manager | Coordinate dispatch, progress, review, and delegated acceptance | Issue authorized R0–R2 commands; accept R0/R1 and R2 after required independent verification | Exercise P-005 transitions, broaden methodology, or accept its own producing work without required evidence |
| Implementer | Produce code, analysis, artefacts, or prose under a governing design | Execute permitted tools and submit evidence/Partial outcomes | Activate or solely approve its own governing R2/R3 contract, scientific verdict, or claim |
| Independent verifier | Inspect the exact subject and independently test declared properties | Emit validation/review evidence and bounded findings | Inherit producer conclusions/hidden reasoning, modify the subject under review, or issue acceptance without a separate grant |
| Claim reviewer | Test result-to-claim mapping, wording, limitations, and disclosure | Recommend allowed/restricted/rejected claim language | Create evidence, silently strengthen the estimand, or promote a claim without Stephen |
| Operator/auditor | Manage or inspect runtime, roots, leases, recovery, receipts, and policy conformance | Perform authorized operational commands and emit audit evidence | Decide scientific adequacy, alter research authority, or convert process success into Task acceptance |

An actor may hold multiple profiles across different attempts, but each action records the active profile. Relationship checks consider prior roles on the same subject/attempt; switching labels does not create independence.

## 9. Risk classification

### 9.1 Risk tiers

| Tier | Typical work | Minimum assurance/routing behavior |
|---|---|---|
| R0 | Mechanical, deterministic, reversible operation | Deterministic checks; delegated acceptance allowed; no manufactured verifier requirement |
| R1 | Bounded implementation under stable accepted specification | Evaluated implementer profile; scoped tools/roots; deterministic validation and Manager acceptance |
| R2 | Scientific implementation or verification affecting evidence validity | W5 assurance plan; distinct verifier context; independent-property evidence; Manager acceptance |
| R3 | Methodological design, pre-registration change, claim promotion, decision reversal, or other high-consequence work | Cross-family/cross-context review and Stephen's attributed decision |

### 9.2 Combined risk floor

```text
effective_risk = max(task_requested_risk,
                     W5_epistemic_risk_floor,
                     W8_operational_risk_floor,
                     policy_or_human_raise)
```

`W5_epistemic_risk_floor` is the canonical name for the scientific-consequence component owned by W5. `W8_operational_risk_floor` is the resource, security, recovery, and operational component owned by W8. Neither term is a generic substitute for the other.

The ordering is policy-defined, not inferred from provider availability. Ambiguous classification blocks with `risk_classification_required` unless a policy safely raises it. No subsystem may lower a recorded floor. W4 also checks the requested action, governing transition, and declared purpose directly against the R3/P-005 trigger set; an R2 label cannot suppress an R3 or human-reserved action even if an upstream requirement was misclassified.

### 9.3 Risk-raising triggers

Examples include:

- new or amended methodology, pre-registration, estimand, null, representation, topology, or claim rule;
- irreversible or high-cost execution beyond an accepted guardrail;
- restricted-data exposure, new external write surface, or broader root/tool permission;
- result-to-claim promotion or causal/novelty language;
- unresolved scientific conflict, producer-correlated review risk, or unavailable required diversity.

## 10. Capability and evaluation profiles

### 10.1 Capability classes

W4 uses versioned classes rather than vague “smart model” labels:

```text
coordination          implementation       code_review
mathematical_reasoning statistical_reasoning topology_reasoning
representation_review provenance_review    claim_review
tool_use              long_context          constrained_output
```

Domain packs may require registered sub-capabilities but cannot redefine core risk or authority.

### 10.2 Evaluation evidence

Each `ModelEvalProfile` records:

- provider, model/version/family, reasoning mode, adapter/policy version, and evaluation time;
- capability/risk combinations tested and prohibited;
- W6 fixture revisions, variants, mutations, grader results, and coverage omissions;
- deterministic, trajectory, research, model, human, operational, and privacy outcomes;
- repeated-run count, false-accept/false-reject evidence, uncertainty method, and threshold policy;
- token/accounting parity, tool-policy parity, security class, supported roots, and context profiles;
- known limitations, expiry/currency triggers, suspension conditions, and approving authority.

Model self-report, provider benchmark, one successful task, or aggregate score without non-compensable gates is insufficient.

### 10.3 Eligibility threshold semantics

For a capability/risk combination to be eligible:

- every applicable P0 fixture and critical grader passes;
- critical false acceptance is zero in the declared calibration set;
- no required fixture is omitted without an accepted, capability-disabling restriction;
- every required family/context, privacy, policy-parity, and token-accounting gate passes;
- repeated model-graded performance meets the W6-declared threshold using its declared uncertainty rule;
- evidence remains within its review/expiry window.

Exact repeated-run counts and numerical confidence thresholds are a foundation-critical W6 decision. Until accepted, affected model-graded capability/risk combinations remain ineligible; W4 supplies no permissive default.

## 11. Route request and candidate records

### 11.1 `RouteRequest`

Required fields include:

- Task/revision, purpose, requested/effective risk, and expected control-store position;
- requesting actor/profile and required producing/review relationship;
- W5 assurance requirement ID/hash, its requirement-scope acceptance evidence, and required capability classes;
- W3 context request/candidate ID/hash, reference count, provider-capacity requirement, sensitivity, exclusions, and freshness;
- authority-grant requirements, tools, roots, network/write classes, and resource class;
- preferred constraints only when they do not change eligibility;
- policy/eval versions, immutable routing-evidence snapshot ID/hash/expiry, and idempotency key.

### 11.2 `RouteCandidate`

For every considered profile, record:

- exact profile/provider/model/adapter/eval revisions;
- gate-by-gate pass/fail/unavailable evidence;
- provider token count or evaluated upper bound for the exact W3 candidate;
- established independence grade and relationship evidence;
- for an R2/R3 producer candidate, eligible verifier-route witness IDs/hashes, required capability/risk, prospective producer relationship, and witness expiry;
- availability, rate/resource constraints, and expiry;
- expected cost/latency only after hard-gate evaluation;
- rejection codes and resume condition.

Candidate-set completeness is bounded to the registered eligible-profile catalogue at the policy revision. W4 does not claim to consider unregistered providers.

## 12. Eligibility algorithm

For each registered candidate in stable ID order:

1. verify current provider/model/adapter/eval identities and availability;
2. verify role purpose, capability classes, and risk ceiling;
3. verify Task scope, authority-grant compatibility, and human-reserved transitions;
4. verify tool/root/network/write permissions and sensitivity class;
5. verify every W5 lane, reviewer relationship, proof-obligation support, requirement-scope acceptance, and human gate can be satisfied;
6. for each R2/R3 producer candidate, demonstrate at least one currently eligible verifier route that meets the required capability and independence grade relative to that prospective producer under the same policy/eval/snapshot revisions; record the witness or reject the producer candidate with `independence_unavailable`;
7. verify W3 reference-token and provider-capacity gates for the exact candidate;
8. compute independence grade from actor/session/context/model/trace relationships;
9. verify W6 fixture coverage, non-compensable gates, recency, and policy parity;
10. verify W8 operational constraints and resource availability;
11. mark eligible only if every hard gate passes.

An error, unknown, missing field, unavailable accounting method, or stale critical record is not a pass.

A verifier-route witness is a pre-dispatch feasibility proof, not a promise that an unevaluated profile will later qualify and not authorization to dispatch the verifier. If its provider/profile/context/eval/snapshot relationship changes before producer dispatch, the producer decision expires. No R2/R3 producing run begins merely because independent verification might be obtainable later.

## 13. Ranking and deterministic selection

W4 ranks only eligible candidates. The default lexicographic order is:

1. greatest verified margin above the required capability/risk threshold;
2. stronger required independence without unnecessary producer correlation;
3. fewer declared limitations for the exact purpose and sensitivity class;
4. higher provider/adapter reliability for the required tool/context surface from the bound routing-evidence snapshot;
5. lower expected latency from that snapshot;
6. lower expected cost from that snapshot;
7. stable profile ID tie-breaker.

Policy may choose a different versioned order for a project, but cost never precedes adequacy, independence, privacy, or authority. The `RouteDecision` records the full candidate set digest, ranking policy, winning evidence, rejected alternatives, and deterministic tie-break.

Time-varying ranking evidence is never read implicitly during selection. Identical immutable inputs mean the same Task, assurance/context/authority/policy/eval revisions, registered candidate catalogue, and routing-evidence snapshot ID/hash.

## 14. Independence grades

| Grade | Evidence | Allowed use |
|---|---|---|
| I0 — no separate verifier | Producer route only; no claim of independence | R0/R1 where W5 permits delegated acceptance |
| I1 — context-distinct | Different session and independently compiled context; exact subject shared; producer conclusions/hidden reasoning excluded | Minimum R2 verifier relationship under P-022 |
| I2 — family-and-context distinct | I1 plus different model family and required evaluator separation | R2 profiles whose assurance plan requires family diversity |
| I3 — human-reserved cross-family | I2 plus Stephen's attributed decision and any P-005 conditions | R3 and every P-005 transition |

Grades record evidence, not quality labels. The same human operating two model sessions remains one human authority. Shared governing sources are labeled `shared_governance`; producer-derived overlap is classified separately. A policy-bound delta-review exposure lowers or annotates the independence profile exactly as W3 requires.

For pre-dispatch verifier feasibility, the relationship is computed against the prospective producer candidate and its proposed context/profile/family. The final verifier decision must recompute the grade against the actual producing attempt; a feasibility witness cannot itself satisfy review or acceptance.

## 15. Authority and human transitions

### 15.1 Delegated authority

- R0/R1: Manager may accept within an explicit grant and accepted policy.
- R2: Manager may accept only after the required validation/review set passes and the established independence grade meets W5.
- R3: Stephen issues the attributed decision after required cross-family/cross-context evidence.

### 15.2 Human-reserved actions

W4 must route to `input_required`/human decision for:

- pre-registration or governing-method amendment;
- R3 dispatch;
- decision-lock reversal;
- claim promotion;
- upgrading imported evidence from provisional to authoritative;
- migration or another P-005 transition;
- time-bounded exception to a critical W6 gate.

A message such as “looks good”, `Done`, or a provider success flag is not an authority record.

## 16. Provider support boundary

### 16.1 Generic interface

Provider adapters expose the same semantic fields for model identity/family/version, reasoning setting where available, context capacity/counting, tool permissions, delivery receipts, availability, error class, and policy version. Missing provider features are explicit capability absences, not emulated claims.

### 16.2 First-release evaluated set

Only Claude and Codex adapters may be evaluated for first-release eligibility. This does not make either provider universally eligible; each provider/model/profile combination must pass its own capability/risk gates.

The two-family minimum is load-bearing for any R3 capability requiring I3. Evaluation publishes a capability-by-family eligibility map. Suspending, expiring, or retiring either family's last eligible profile for such a capability raises `r3_family_coverage_insufficient`, blocks affected R3 dispatch, and names the missing coverage and resume condition; it is not a silent capability loss.

Another provider may be added only through:

1. a registered adapter/profile revision;
2. W7 semantic and token-accounting parity evidence;
3. applicable W6 fixture/calibration evidence;
4. accepted policy review;
5. no regression in required independence or provider-failure behavior.

## 17. Fallback and outage

Fallback is a new route evaluation under the original immutable request. It preserves:

- effective risk and W5 assurance requirement;
- W3 mandatory context and both token gates;
- role, authority, tools, roots, sensitivity, and human gates;
- required independence/family separation;
- any producer-route verifier-feasibility witness and R3 family-coverage requirement;
- fixture coverage and evaluation threshold.

Typed outcomes include:

```text
provider_unavailable          model_profile_suspended
token_accounting_unavailable  context_budget_exceeded
capability_threshold_unmet    policy_parity_failed
independence_unavailable      authority_required
no_eligible_route
```

W4 may select another eligible route deterministically. If none exists, Task/dispatch waits or becomes blocked/input-required through W2. It never substitutes a lower risk, smaller assurance plan, same-family verifier, unevaluated model, or omitted context.

## 18. When multi-agent execution is inappropriate

Multi-agent work is prohibited or reduced to one accountable actor when:

- the Task cannot be decomposed into independently verifiable artefacts/interfaces;
- agents would concurrently mutate the same non-transactional file, result, or external state;
- one actor must preserve a single mathematical argument or tightly coupled design and handoffs would fragment governing context;
- nominal verifier agents would share producer conclusions, context, family, or hidden trace contrary to the required grade;
- orchestration/context overhead exceeds the bounded task value for R0/R1;
- the work is a human-reserved methodological, ethical, scope, or claim decision;
- permissions or restricted-data access cannot be partitioned safely;
- a single deterministic tool is the appropriate mechanism.

Parallelism is justified by separable state and evidence, not by the number of available model sessions. The route record states the decomposition and merge/acceptance authority.

## 19. Permissions and security

- Default deny every command, tool, root, network, provider, and write class not declared by both profile and authority grant.
- Read access does not imply write, execution, external publication, or decision authority.
- Restricted data remains behind approved tools/opaque references; provider routes never receive raw UKDA records by convenience.
- Secrets, `.env` contents, credentials, full transcripts, and hidden reasoning are prohibited from route/profile/eval records.
- Provider/model output is untrusted until schema/policy/assurance validation.
- A broader permission set raises operational risk and requires reevaluation; it is not inherited from a previous session.

## 20. Failure behavior

| Failure | Required result |
|---|---|
| W5 assurance requirement missing/stale | Block route; name required revision/owner |
| W5 requirement floor/lane scope lacks required producer-independent acceptance | Block route; `assurance_requirement_scope_unconfirmed` |
| Risk classification ambiguous | Raise safely if policy permits; otherwise `risk_classification_required` |
| Requested action is R3/P-005 but recorded floor is lower | Raise to R3 and require the human gate; never dispatch under R2 authority |
| Capability/eval evidence absent or expired | Candidate ineligible |
| Applicable P0 or critical grader fails | Candidate/profile ineligible; no aggregate override |
| Provider/model/adapter unavailable or changed | Candidate unavailable; evaluate other eligible candidates only |
| W3 token/accounting gate fails | Candidate rejected before issue; preserve mandatory context |
| Required independence cannot be established | `independence_unavailable`; no lower grade |
| No eligible verifier-route witness exists for an R2/R3 producer candidate | Reject producer candidate before dispatch; `independence_unavailable` |
| R3-required capability has fewer than two eligible families | `r3_family_coverage_insufficient`; block and surface coverage gap |
| Authority grant insufficient | `authority_required`; no command/dispatch |
| Tool/root/sensitivity conflict | Candidate rejected; no permission widening |
| All candidates rejected | `no_eligible_route` with candidate evidence and resume conditions |
| Selected route becomes stale before consumption | Expire decision; rerun against current immutable inputs |
| Adapter reports success without receipt/hash | Delivery/dispatch satisfaction fails |

## 21. Evaluation and acceptance metrics

Accepted addendum `06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md` reserves the following W6 IDs with pre-control setups, post-control/trajectory oracles, grader classes, priorities, two-axis provenance, and dependencies.

| Reserved ID | Design | Priority | Provenance |
|---|---|---:|---|
| F-031 | Deterministic eligibility-first routing and candidate explanations | P0 | `specification` / `synthetic` |
| F-032 | Provider outage/fallback preserves risk, assurance, context, and independence | P0 | `specification` / `synthetic` |
| F-033 | Role-switch and producer-correlation cannot manufacture independence | P0 | `specification` / `synthetic` |
| F-034 | Permission/root/sensitivity conflict and unsafe multi-agent decomposition fail closed | P0 | `specification` / `synthetic` |
| F-035 | Two-key validity is non-compensable | P0 | `specification` / `synthetic` |
| F-036 | Proof-obligation anti-gaming: anchoring, degenerate fallback, and no-op null | P0 | `domain_coverage` / `synthetic` |
| F-037 | Partial/negative/superseded result remains distinct from claim promotion | P1 | `specification` / `synthetic` |
| F-038 | Domain-pack and qualitative `not_applicable` boundary | P1 | `specification` / `synthetic` |

Foundation-critical W6 must implement route fixtures covering:

- deterministic repeatability of candidate set, rejection reasons, ranking, and selected profile;
- determinism against the exact immutable routing-evidence snapshot rather than live cost/latency/reliability reads;
- risk-floor monotonicity and no cost-driven downgrade;
- P0/critical non-compensability;
- R2 distinct-context and declared family-diversity cases;
- R3 cross-family/context plus Stephen requirement;
- producer-independent R2/R3 requirement-floor and lane-scope acceptance;
- demonstrated eligible verifier feasibility before R2/R3 producer dispatch;
- capability-by-family coverage alerts when an R3 capability has fewer than two eligible families;
- provider outage and S-016 no-subthreshold fallback;
- W3 reference/provider token-gate failures and candidate rerouting;
- adapter-policy drift F-020;
- self-approved contract F-014 and correlated review F-022;
- wrong-root/tool/sensitivity denial;
- multi-agent inappropriate/decomposition cases;
- qualitative R0/R1 proportional paths without weakened provenance.

Required non-aggregated metrics include:

- hard-gate violation in selected routes: `0`;
- silent risk/assurance/independence downgrade: `0`;
- deterministic decision equality for identical immutable inputs including routing-evidence snapshot: `1.0`;
- candidate rejection explanation coverage: `1.0`;
- R2/R3 producer dispatch without an eligible verifier-route witness: `0`;
- R3-required capability with fewer than two eligible families surfaced as blocking: `1.0`;
- required provider/accounting/policy evidence completeness: `1.0`;
- critical false acceptance in calibration mutations: `0`;
- human-reserved transition without attributed authority: `0`.

## 22. Observability and audit

Normalized traces record:

- route request/candidate/decision/failure IDs and hashes;
- Task/dispatch/assurance/context/authority/eval/policy revisions;
- all candidates and gate outcomes without hidden model reasoning;
- selected provider/model/family/version/reasoning/profile and adapter;
- token/accounting, availability, permissions, roots, and sensitivity outcomes;
- independence evidence, producer-route verifier-feasibility witnesses, and any attributed delta exposure;
- routing-evidence snapshot, capability-by-family coverage, ranking/tie-break, cost/latency estimates, and actual delivery/attempt outcomes;
- expiry, suspension, reroute, exception, and human-decision events.

Audits can reconstruct why a route was selected and prove that a rejected weaker route was not silently used.

## 23. Downstream constraints

### W5

Emit immutable assurance requirements with capability, risk, independence, review, human, and stop constraints. Do not name provider/model preferences or treat route success as scientific acceptance.

### W6

Define exact repeated-run thresholds, sample sizes, confidence rules, calibration sets, profile expiry, capability-by-family coverage, and route fixtures. Materialize F-031–F-038 only after their dated reservation is accepted. No permissive default exists before these are accepted.

### W7

Implement the generic provider interface and evaluate only Claude/Codex initially. Preserve W3 bytes/hashes, both token gates, tool/permission semantics, model identity, availability, and receipts.

### W8

Supply resource/operational risk floors, availability, leases, and stop/recovery evidence without lowering W5 assurance or W4 capability gates.

## 24. Research-assurance classification

W4 directly touches Output/Provenance and Paper Claim governance because route metadata and independence determine whether scientific review can be trusted. It carries all six W5 assurance lanes but changes no formula, null, estimand, representation, topology, result, or claim.

Machine-checkable claims include identity/version/hash, risk monotonicity, capability/eval coverage, permissions, token gates, candidate completeness, deterministic ranking, independence evidence, authority grants, and fallback equivalence. Human review decides whether capability classifications, W6 thresholds, limitations, and provider diversity are epistemically adequate.

## 25. Joint W4/W5 review questions

1. Can provider availability or cost lower risk, assurance, context, or independence through any route?
2. Can one actor change profile labels and appear independent from its own producing attempt?
3. Can W5 encode a preferred model and turn scientific authority into provider selection?
4. Can W4 select a capable model whose tool/root/sensitivity grant is invalid?
5. Can aggregate evaluation hide one critical false acceptance or policy-parity failure?
6. Can multi-agent decomposition create ambiguous ownership or lose cross-cutting evidence?
7. Does provider-neutral schema overstate support for providers that have never been evaluated?

## 26. Review gate

W4 can move from `review_pending` to `accepted` only when Stephen confirms after bounded joint W4/W5 review that:

- [x] W5 assurance and W4 routing authority are non-circular and cannot weaken each other.
- [x] Role profiles, authority grants, actors, attempts, models, and contexts remain distinct.
- [x] Risk classification is monotone and human-reserved transitions match P-005/P-022.
- [x] Eligibility evaluates every hard capability, assurance, context, permission, independence, provider, and operational gate before ranking.
- [x] Cost/latency rank only already-eligible routes.
- [x] Evaluation thresholds fail closed pending foundation-critical W6 calibration.
- [x] Independence grades are evidence-derived and never claim nonexistent human diversity.
- [x] R2/R3 producer routing proves an eligible verifier route exists before dispatch and recomputes the final relationship against the actual attempt.
- [x] R3 capability-by-family coverage loss is surfaced and blocks dispatch before task-level failure.
- [x] Claude/Codex initial support does not become universal eligibility or block a generic interface.
- [x] Fallback/outage behavior preserves all original requirements.
- [x] Multi-agent refusal rules are proportionate and checkable.
- [x] Accepted addendum 06b reserves F-031–F-038 with complete priorities, provenance, oracles, graders, and dependencies.
- [x] W6/W7/W8 receive sufficient fields to implement and evaluate the design.
- [x] No runtime, migration, active APM write, or research-claim change is introduced.

## 27. Outcome

**Outcome:** `ACCEPTED — W4 v0.2 closes W45-M1–M4 and W45-m5–m8 under P-029; implementation remains gated`.

The next action is to freeze the foundation-critical W6/W7/W8 interfaces and executable evidence, then run the combined-interface review. Foundation implementation remains prohibited until those gates pass and Stephen approves a separately reviewed implementation plan.
