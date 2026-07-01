# Agentic Research System — Master Transition Plan

**Date:** 2026-06-27  
**Revised:** 2026-07-01<br>
**Status:** W1–W5 and Gate 3 W6 v0.3/W7 v0.2/W8 v0.2/06c v0.2 accepted under P-027–P-030; P0 planning is next and implementation remains gated<br>
**Foundation-development point:** After W3–W5 and foundation-critical W6–W8 gates, without waiting for T1.28  
**Legacy migration point:** After the relevant APM work reaches reviewed closeout; no current-paper migration  
**First deployment context:** TDL mathematical and social research  
**Long-term scope:** Domain-general research programmes with optional specialist assurance packs

## 1. Executive conclusion

The current workflow has evolved a strong scientific-assurance layer around a comparatively fragile coordination layer.

Its strongest elements should survive:

- explicit pre-registration and decision rules;
- machine-readable contracts and binding tests;
- input and output provenance;
- frozen representations and parameter locks;
- worktree isolation;
- date-suffixed, non-overwriting outputs;
- resumable long-running computation;
- formal Partial, blocked, and escalation outcomes;
- paper-claim review and human approval at methodological forks.

Its main weaknesses now create avoidable epistemic risk:

- single-slot mutable bus files can be overwritten;
- task identity and attempts are implicit;
- programme history is mixed into oversized mutable Tracker cells;
- session history, durable memory, and per-turn context are not cleanly separated;
- Claude and Codex policies, hooks, and skills have drifted;
- model selection is controlled by which chat is opened rather than task metadata and eval evidence;
- the same Worker can sometimes interpret, implement, test, and effectively approve a methodological contract;
- software and result validation are strong, but the agentic workflow itself has no regression-eval suite;
- resource scheduling and long-run ownership live in prose rather than state;
- the strategic research plan presents a linear roadmap where the actual programme behaves as an evidence-dependent portfolio.

The proposed response is a new **Agentic Research System**, developed as an evolutionary successor to APM. It will use durable task identity, append-only events, typed artefacts, generated views, bounded context compilation, explicit risk/model routing, independent scientific review, and agent-system evals. Provider-specific harnesses become adapters around a provider-neutral research control plane.

## 2. Why this transition point is appropriate

The expected completion of T1.28 creates a natural boundary:

- the first major computational and assurance cycle has accumulated enough real failures and corrections to support evidence-driven redesign;
- Phase 2 work has already been developed in parallel, so transition design can be tested without invalidating it;
- the research programme is expanding beyond one paper and may expand beyond TDA;
- further incremental additions to mutable Tracker and bus files will increase context and synchronization debt;
- the cost of introducing stable task and evidence identities rises as more papers and domains are added.

T1.28 is now expected to remain compute-bound for several days. Under P-026, that makes its completion a legacy-closeout and migration boundary, not a hold on independent successor design. W3–W5, foundation-critical W6–W8 interfaces, and a later non-migrating foundation may advance through their own gates while T1.28 remains entirely APM-owned.

This is not permission to rewrite active history. The old APM material remains authoritative for the work it governed. The new system will import only the decisions and dependencies needed for future work and will reference, rather than normalize, the full historical record.

## 3. Design foundations from the supplied material

The supplied SDLC and context-engineering material identifies six context classes—instructions, knowledge, memory, examples, tools, and guardrails—and treats the harness as a first-class engineered system rather than an incidental prompt wrapper. It also distinguishes:

- deterministic tests from non-deterministic evals;
- static policy from dynamically retrieved context;
- session event history from the context shown to the model on a turn;
- declarative knowledge from procedural memory;
- orchestration from execution;
- communication messages from durable outputs;
- synchronous foreground work from background compaction, indexing, and monitoring.

Those distinctions directly match the repo's current pressure points. The redesign therefore treats context compilation, memory provenance, state transition, and evals as core architecture rather than documentation conventions.

## 4. Scope

### 4.1 In scope

- research portfolio and dependency representation;
- research-question, hypothesis, estimand, and claim identity;
- task specification, dispatch, acknowledgement, execution, checkpoint, review, and closure;
- evidence, artefact, provenance, and decision records;
- context compilation and retrieval;
- session handoff and recovery;
- agent profiles and model/reasoning routing;
- scientific independence and review topology;
- contracts, hooks, policy enforcement, and provider parity;
- deterministic tests and agent evals;
- resource ownership and feasibility gates;
- dashboards and generated human-readable views;
- migration from current APM;
- reusable project templates and optional domain assurance packs.

### 4.2 Out of scope for the first release

- autonomous modification of pre-registrations or paper conclusions;
- automatic publication or external communication;
- a distributed network service when local file transport is sufficient;
- support for every model provider;
- retrospective conversion of every historical Tracker sentence into structured data;
- replacement of Git, result JSONs, research vaults, or domain computation libraries;
- automatic model downgrading for mathematical tasks without eval evidence;
- autonomous scheduling of expensive computation without declared resource ownership and guardrails.

## 5. System principles

### 5.1 Evidence before status

Status is a projection of events and artefacts, not a free-text assertion. A task is not complete because a Worker says it is complete; it is complete when its acceptance evidence and review transition exist.

### 5.2 Append rather than overwrite

Task assignments, attempts, checkpoints, reports, review verdicts, and decisions receive immutable identities. Corrections supersede earlier records while preserving lineage.

### 5.3 Compile context rather than preload history

Each role receives a bounded context packet assembled from canonical sources. The packet records included sources, versions, selection reasons, and omissions.

### 5.4 Separate authorities

Research design, implementation, verification, acceptance, and claim promotion are different authorities even when one person oversees them. R2/R3 work requires independent review appropriate to its risk.

### 5.5 Machine-check what is objective

Schemas, hashes, parameter locks, p-value formulas, FDR families, path rules, result completeness, state transitions, and model metadata should be checked mechanically. Interpretation, novelty, causal warrant, and claim strength remain explicit human or independent-review judgments.

### 5.6 Treat Partial as a valid terminal report

Agents must stop when evidence is insufficient, inputs disagree, cost exceeds a guardrail, or the task asks for an unauthorized methodological change. The control plane must preserve useful partial artefacts without promoting the decision.

### 5.7 Provider-neutral core, evaluated adapters

Canonical policy and schemas must not live exclusively in `CLAUDE.md`, `AGENTS.md`, or provider-specific hook files. Those files are generated or validated adapters.

### 5.8 Domain-neutral core, specialist assurance packs

The core knows about tasks, evidence, estimands, contracts, reviews, artefacts, and claims. It does not hard-code persistent homology. TDA, panel statistics, causal inference, qualitative work, or other domains contribute their own assurance packs.

### 5.9 Observability before autonomy

The system must record what an agent saw, did, produced, and escalated before it is trusted with broader autonomy.

### 5.10 Migration must preserve epistemic lineage

Historical decisions and results retain their original governing files and provenance. Imported summaries point back to those sources and declare whether they are authoritative, provisional, superseded, or unresolved.

## 6. Target architecture

### 6.1 Portfolio layer

The portfolio layer represents research programmes, papers, hypotheses, methods, datasets, claims, and dependencies. It replaces a strictly linear stage narrative with evidence-bearing programme objects.

Each proposed study or paper should record:

- research question and intended contribution;
- novelty claim and closest alternatives;
- target population, data access, and representation requirements;
- estimand or mathematical object;
- falsification and negative-result value;
- specialist-method incremental value;
- feasibility evidence and resource envelope;
- dependencies and blocking evidence;
- promotion, redesign, pause, and abandonment criteria;
- current evidence and claim status.

Recommended lifecycle:

```text
Candidate → Assay → Spike → Pre-registration → Implementation
          → Independent verification → Decision lock → Claim promotion
          → Manuscript integration → Reproducibility release
```

The stages are gates, not dates. Different programme objects may advance in parallel when their dependencies permit.

### 6.2 Task and event layer

Every unit of work receives stable identity and a declared lifecycle. The first state-machine design should support:

```text
draft
  → readiness_pending
  → queued
  → claimed
  → running
  → checkpointed
  → review_pending
  → accepted

running or review_pending
  → input_required
  → blocked
  → partial
  → rejected
  → superseded
  → cancelled
```

Transitions are events with an actor, timestamp, reason, and supporting artefact. A task may have several dispatch attempts; an attempt may not silently replace another attempt.

Required identifiers:

- programme ID;
- research-object or claim ID where relevant;
- task ID;
- context ID for related tasks;
- dispatch ID;
- attempt ID;
- agent-profile ID;
- session/run ID;
- artefact ID;
- review ID;
- decision ID.

The current per-agent `task.md` and `report.md` remain authoritative only for `legacy_owned` work. Successor-owned work uses non-shared ARS-namespaced views. One project-wide command service owns a dedicated linear ledger outside task-worktree branches; worktrees submit commands and never advance canonical history directly.

### 6.3 Artefact and provenance layer

Messages communicate; artefacts carry durable outputs. Artefact manifests should support:

- type and schema version;
- producing task, attempt, model, code commit, and environment;
- input artefact identities and hashes;
- creation time and path;
- parameters, seeds, sample restrictions, and data vintage;
- contract-validation result;
- supersession lineage;
- confidentiality and external-data constraints;
- retention class;
- claim or decision consumers.

Large result files remain in established results locations. The control plane stores their manifest and validation state rather than duplicating them.

### 6.4 Context and memory layer

The system must distinguish four things:

1. **Event history:** append-only record of what happened.
2. **Canonical state:** current task, decision, and artefact projections derived from events.
3. **Durable memory:** consolidated findings, conventions, and lessons with provenance, confidence, and review status.
4. **Working context:** the bounded packet compiled for a particular agent and turn.

A context manifest should record:

- task and role;
- token or size budget;
- included files, fragments, hashes, and versions;
- retrieval query or selection rule;
- reason each item was included;
- material deliberately excluded;
- applicable policies, skills, contracts, and examples;
- unresolved conflicts;
- compiler version.

Compaction summaries must link to source events. They are retrieval aids, not replacements for evidence.

### 6.5 Agent and model layer

Initial role profiles:

| Role | Primary responsibility | Typical model policy |
|---|---|---|
| Portfolio Steward | Programme dependencies, promotion gates, strategic coherence | Highest-reasoning orchestrator |
| Research Designer | Estimand, mathematical specification, pre-registration, decision rule | Highest-reasoning model |
| Feasibility Analyst | Bounded benchmark, cost and memory projection, resource claim | Script-first; strong model for interpretation |
| Implementer | Code, tests, runners, checkpointing, artefact production | Codex-class xhigh for R2/R3 |
| Independent Verifier | Re-derive, challenge assumptions, inspect evidence, test counterexamples | Distinct evidenced context for R2; cross-family and cross-context for R3 |
| Provenance Auditor | Inputs, hashes, vintages, environment, output schema | Deterministic tools plus evaluated model |
| Claim Reviewer | Map result and decision locks to prose strength | Highest-reasoning model plus human approval |
| Operations Agent | State projection, queue, recovery, adapter parity | Deterministic automation where possible |

Agent profiles declare capabilities, permitted tools, context policy, risk ceiling, expected outputs, review requirements, and escalation conditions. A role name is not sufficient evidence of capability or independence. In a solo programme the system records contextual/model independence honestly; it does not claim independent human authorities that do not exist.

### 6.6 Risk and model-routing layer

Proposed epistemic risk tiers:

| Tier | Character | Minimum control |
|---|---|---|
| R0 | Mechanical, deterministic, reversible | Minimal command/event/receipt envelope; script or evaluated lightweight model; deterministic verification |
| R1 | Bounded implementation with stable specification | Implementer plus software review and tests |
| R2 | Formula, estimand, null, representation, inference, or reusable research logic | Independent design lock, xhigh implementation, independent scientific verification |
| R3 | Paper conclusion, decision reversal, causal claim, new methodology, or high-cost irreversible run | Cross-family/cross-context review, Stephen’s explicit approval, complete provenance and trace |

Routing records the actual model version, reasoning effort, context compiler version, and eval profile. Model changes trigger regression evaluation on the relevant task classes.

### 6.7 Research-assurance layer

The current assurance lanes generalise into domain packs:

- mathematical object and derivation;
- stochastic/null design;
- statistical estimand and inference;
- representation and measurement;
- data and output provenance;
- claim and disclosure;

For qualitative or non-computational artefacts, the core still provides provenance, lifecycle, review, authority, and claim controls. Deterministic scientific validation may be `not_applicable`; the assurance burden shifts explicitly to bounded independent/human review rather than implying parity with quantitative validation.
- domain-specific extensions such as topology.

Each R2/R3 task should declare:

- touched lanes;
- governing specification, pre-registration, or decision;
- assumptions and proof obligations;
- machine-checkable claims and enforcement artefacts;
- human-review questions;
- counterexamples or metamorphic tests;
- benchmark or known-case validation;
- partial criteria and stop conditions;
- downstream claims that depend on the result.

The contract framework remains central but gains explicit ownership and approval metadata. `pending:true` authorizes contract development, not the producing run. An implementing agent cannot be the sole authority that clears its own methodological contract.

### 6.8 Evaluation and observability layer

The system requires evals for the harness, not only tests for research code.

Evaluation dimensions:

- **Outcome correctness:** required artefacts, numbers, schemas, decisions, and provenance.
- **Trajectory correctness:** required checks were run, forbidden shortcuts avoided, appropriate sources consulted, and escalation occurred at the right boundary.
- **Research quality:** assumptions, estimand, interpretation, and claim strength.
- **Operational quality:** context size, retries, wall time, tool calls, cost, resource use, and recovery.

Initial historical fixtures should cover:

- overwritten bus assignment;
- authoritative bus in a different checkout;
- same-path but wrong-vintage input;
- hidden prerequisite work in a benchmark-only run;
- invalid threading assumption for GIL-holding computation;
- downstream metric correction accidentally expanding PH generation;
- re-fitting a representation that should remain frozen;
- wrong permutation denominator or FDR family;
- a null operation that leaves the tested object invariant;
- result JSON omitting downstream comparison fields;
- a Worker weakening a task after cost or input failure instead of reporting Partial;
- synchronization that overwrites newer provider-specific safeguards;
- prose promotion stronger than the locked result supports.

Metrics should include:

- first-pass acceptance rate;
- task reopen rate;
- user-caught defect rate;
- assurance escape rate;
- provenance failure detection before dispatch versus after execution;
- runtime and memory estimate error;
- checkpoint recovery success;
- context size and stale-context incidence;
- contract self-approval exceptions;
- model/provider performance by risk tier;
- cost per accepted task, not cost per attempted turn.

### 6.9 Resource and long-run control

Resource scheduling becomes explicit state rather than prose. A task may claim:

- worktree and branch;
- CPU workers;
- RAM envelope;
- GPU or accelerator;
- external-data access;
- output namespace;
- expected duration;
- checkpoint cadence;
- stop threshold;
- exclusive or shared machine status.

Feasibility probes must cap all expensive prerequisites, emit progress before expensive work, and project the complete design rather than only the obvious generation step. A guardrail such as `>12h at 4 workers` is a hard state transition to `input_required` or `partial`, not advisory prose.

### 6.10 Provider adapter layer

Canonical policy should live in one provider-neutral source. Claude, Codex, and future adapters translate:

- instruction-file locations;
- hook interfaces and tool names;
- skill discovery and invocation;
- agent profile declarations;
- context injection;
- event emission;
- session recovery;
- permission and sandbox semantics.

Parity tests verify semantic coverage, not byte identity. A source-to-adapter generator must refuse to overwrite a richer target unless the canonical source contains the same requirement or an explicit migration records its removal.

## 7. Options considered

### Option A — Continue patching APM

**Benefits:** Lowest immediate cost; minimal disruption.  
**Weaknesses:** Retains mutable mailbox identity, oversized state files, provider drift, and implicit lifecycle. Every added rule increases context and synchronization burden.  
**Decision:** Not sufficient as the strategic solution, though immediate parity repairs may be backported.

### Option B — Evolve APM into the Agentic Research System

**Benefits:** Preserves proven controls and familiar filesystem operation; allows incremental migration; can be designed around actual failure evidence; remains inspectable and provider-neutral.  
**Weaknesses:** Requires deliberate schema, migration, and eval work; compatibility code must eventually be retired.  
**Decision:** Recommended.

### Option C — Adopt an external multi-agent framework or network protocol wholesale

**Benefits:** Existing task lifecycle, messaging, streaming, and integrations.  
**Weaknesses:** Introduces provider and framework assumptions, operational complexity, and a larger trust surface; does not supply the domain-specific research assurance this repo needs.  
**Decision:** Do not adopt wholesale in the first release. Borrow stable protocol concepts and keep an integration boundary.

## 8. Transition programme

The programme now runs two isolated lanes. The legacy lane closes T1.28 and the two current APM papers under existing authority. The successor lane specifies ARS, then builds a narrow production-intended foundation and pilots it on the first paper initiated after those two. The lanes exchange dated lessons and decisions only; they never share mutable state or canonical ownership.

Phase A may therefore remain open while the design portions of Phases B–E proceed. Foundation implementation requires the specification and review gates in `04-parallel-specification-and-foundation-pilot-plan.md`, but not T1.28 terminal completion.

### Phase A — Closeout and freeze

**Objective:** Establish the historical boundary without disturbing active work.

- confirm T1.28 and remaining Phase 1 status;
- inventory authoritative Phase 1 decisions, contracts, artefacts, and unresolved items;
- classify Phase 2 items as authoritative, provisional, blocked, or superseded;
- snapshot current APM policy sources and known provider differences;
- identify historical failures for eval fixtures;
- declare old APM records read-only after closeout except for explicit corrections.

**Exit condition:** A signed transition manifest identifies the authoritative legacy sources and live work that remains under APM.

### Phase B — Canonical policy and parity

**Objective:** Stop further Claude/Codex drift before larger redesign.

- select a provider-neutral policy source;
- reconcile APM guides and skill differences deliberately;
- represent hook requirements semantically;
- add adapter parity and coverage tests;
- update stale version/path references;
- make synchronization fail safely on unexplained divergence.

**Exit condition:** The same research and dispatch safeguards are demonstrably active for Claude and Codex, with documented provider-specific exceptions.

### Phase C — Typed ledger and generated views

**Objective:** Remove single-slot overwrite and ambiguous task state.

- finalize task, dispatch, attempt, event, artefact, review, and decision schemas;
- implement append-only storage and deterministic projections;
- generate Tracker, inbox, report, and dashboard views;
- add acknowledgement, lease, idempotency, correlation, and recovery rules;
- preserve compatibility with the old bus for imported or still-active work.

**Exit condition:** A simulated task can be dispatched twice without losing either attempt, recovered after interruption, and reconstructed solely from events.

### Phase D — Context compiler and memory provenance

**Objective:** Bound model context while retaining source lineage.

- define role-specific context policies;
- compile versioned packets and manifests;
- separate events, state projections, durable memory, and working context;
- add conflict and staleness indicators;
- implement source-linked compaction and retrieval;
- measure context size and retrieval recall on historical tasks.

**Exit condition:** A Manager and Worker can complete representative fixtures without loading the full Spec, Plan, and Tracker, while retrieving all required governing evidence.

### Phase E — Independent assurance and model routing

**Objective:** Enforce two-key research validity and evaluated model use.

- define agent profiles and risk tiers;
- add contract author, implementer, verifier, and approver identities;
- enforce independent approval for R2/R3 transitions;
- define model-version and reasoning-effort metadata;
- establish exceptions and human approval points;
- calibrate role/model combinations on the eval suite.

**Exit condition:** An agent cannot approve its own R2/R3 methodological contract, and every accepted high-risk result has a traceable independent verdict.

### Phase F — Greenfield pilot and adoption decision

**Objective:** Validate the production-intended foundation on bounded real work without migrating the current papers.

- select the first paper initiated after the two current APM-managed papers;
- initialize it under ARS from inception with one canonical successor authority;
- begin with bounded R0/R1 tasks and one representative R2 workflow before paper-critical computation;
- expose any legacy-style interface only as a non-shared generated view;
- compare context size, evidence recall, defects, recovery, operator burden, and cost;
- perform independent research review;
- decide whether to expand, revise, stop, or roll back the foundation.

**Exit condition:** The greenfield pilot passes its scientific and operational acceptance criteria and Stephen explicitly authorizes wider adoption. No conclusion about migrating the two APM papers follows automatically.

### Phase G — Reusable project template

**Objective:** Extract a specific but generalisable system.

- define a minimal core template;
- package Claude and Codex adapters;
- create project-init and migration commands;
- define domain-pack interfaces;
- produce TDA and general statistical/social-research example packs;
- document maintenance, upgrades, and decommissioning.

**Exit condition:** A fresh non-TDA project can instantiate the core, run a sample R0/R2 workflow, and demonstrate provenance, independent review, evals, and recovery without importing TDL-specific assumptions.

## 9. Risks and controls

| Risk | Consequence | Control |
|---|---|---|
| Overengineering the control plane | Research stalls under infrastructure work | Gate every component on historical failure evidence and pilot value |
| Prototype outruns accepted specifications | Rework or hidden governance gaps enter the permanent foundation | Require W3–W5, foundation-critical W6–W8 interfaces, and an approved implementation plan before runtime work |
| Migrating active tasks | Confused authority and broken provenance | Freeze boundary; compatibility adapter; pilot only new work |
| False confidence from schemas | Structurally valid but scientifically wrong work | Independent assurance lanes and human-review questions |
| Model monoculture | Correlated interpretation errors | Fresh context and cross-family review for R3 |
| Excessive multi-agent use | Cost, latency, and coordination failure | Use parallel agents only for independent or breadth work |
| Context compiler omits critical evidence | Agent acts on incomplete rules | Context manifests, retrieval evals, conflict checks, human-readable packet |
| Event log becomes another giant file | Slow queries and merge conflict | Partitioned append-only records and rebuildable indexes |
| Provider adapter drift | Different safeguards across runtimes | Generated adapters plus semantic parity tests |
| Historical import upgrades weak evidence | Unsupported claims become authoritative | Import status and lineage; no implicit promotion |
| Metrics optimize superficial compliance | Agents game visible checks | Combine deterministic, model, and human graders; rotate adversarial fixtures |
| Generalisation erases useful domain rigor | Core becomes generic but scientifically weak | Optional domain packs with binding assurance interfaces |
| Infrastructure loses ownership | Stale schemas and hooks accumulate | Named maintenance role, version policy, and deprecation tests |

## 10. Success criteria

The transition succeeds only if the new system demonstrates:

1. no task or report can be silently overwritten;
2. every accepted result is traceable to task, attempt, code, inputs, model, contracts, and review;
3. R2/R3 methodological work cannot be self-approved by its implementer;
4. Claude and Codex receive equivalent canonical safeguards;
5. task context is materially smaller than the current Manager bundle without reducing governing-evidence recall;
6. interrupted work resumes from explicit state and artefacts rather than conversational memory;
7. hard cost and scientific guardrails produce state transitions and escalation;
8. historical failure fixtures fail before the relevant control and pass after it;
9. the Tracker/dashboard is a projection that can be rebuilt;
10. current Paper 1 and Phase 2 evidence retains its original authority and lineage;
11. a non-TDA pilot can use the core without TDL-specific paths or topology assumptions;
12. operator burden and accepted-task cost are measured, not assumed;
13. Stephen retains explicit authority over methodological forks, decision reversals, and paper claims.

## 11. Stop-doing list

The transition should retire these practices:

- embedding full task history in Tracker status cells;
- treating a single `task.md` as both queue and task identity;
- maintaining Claude and Codex policy trees independently;
- selecting the model solely by opening a particular chat;
- allowing a producing agent to be the only approver of its governing contract;
- declaring resource ownership only in prose;
- trusting benchmark modes that do uncapped prerequisite work;
- loading full programme documents when a task needs a bounded subset;
- accepting Worker narrative instead of inspecting artefacts and decision fields;
- turning a static multi-year roadmap into an implied evidence guarantee;
- describing associative visual structure as causal without a causal design;
- treating framework adoption as a substitute for research assurance.

## 12. Immediate next action

Gate 3 closed under P-030 after joint adversarial review and reconciliation. W6 v0.3, W7 v0.2, W8 v0.2, and 06c v0.2 are accepted written interfaces. The next sequence is:

1. write a separately reviewed P0 materialization and narrow-foundation implementation plan;
2. map every component and implementation step to accepted W1–W8/06c contracts, exact P0 fixture dependencies, deterministic tests, failure behavior, and rollback;
3. obtain Stephen's explicit approval of the exact P0/foundation scope;
4. only then create executable fixture, adapter, resource/process, or runtime artefacts.

No executable P0 evidence, runtime, migration, pilot, or current-paper change is authorized by P-030. T1.28 remains a migration and current-paper boundary, not a successor-planning blocker.
