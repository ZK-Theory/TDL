# Design and Deliverables Roadmap

**Purpose:** Decompose the transition into independently reviewable design products before implementation.

## 1. Delivery model

The redesign is too broad for one specification. It will be delivered as a coordinated set of bounded specifications. Each specification must define:

- problem and evidence;
- scope and non-goals;
- interfaces and owned state;
- invariants and failure behavior;
- research-assurance implications;
- security and permission boundary where relevant;
- migration behavior;
- deterministic tests and agent evals;
- acceptance criteria;
- unresolved decision references.

Specifications may be developed in parallel only when their interfaces are already locked. Schema and lifecycle work precedes context, routing, and dashboards because those systems consume task and artefact identity.

## 2. Deliverable sequence

### W0 — Legacy closeout and transition manifest

**Purpose:** Define the boundary between authoritative APM history and the successor system.

**Current status (2026-06-28):** Manifest written at `transition/W0-legacy-closeout-transition-manifest-2026-06-28.md`; outcome `PARTIAL — manifest complete, legacy boundary not sealed`. T1.28 and the full Stage 2 scope decision remain open.

**Outputs:**

- Phase 1 closeout inventory;
- T1.28 final-state confirmation;
- Phase 2 authority/provisional-state inventory;
- legacy source map;
- unresolved-task and decision list;
- historical fixture shortlist;
- no-migration list for active runs.

**Review gate:** Current Manager and Stephen agree that the manifest does not silently upgrade, discard, or reinterpret evidence.

### W1 — System architecture specification

**Purpose:** Lock component boundaries and ownership.

**Current status (2026-06-29):** W1 v0.2 integrates the accepted adversarial-review amendments: one project-wide writer, a dedicated linear ledger/control root, non-shared successor compatibility paths, and graded independence/delegated acceptance. Stephen approved the revision; Manager confirmation and final post-T1.28 reconciliation remain pending. Implementation and migration remain prohibited.

**Must define:**

- portfolio, control-plane, execution, assurance, context/memory, evaluation, and adapter components;
- canonical versus projected state;
- trust boundaries;
- filesystem and optional index boundaries;
- dependency direction;
- compatibility surface with `.apm/`.

**Review gate:** Every component has one responsibility and explicit consumers; no provider-specific file is canonical.

### W2 — Task, event, artefact, review, and decision schema

**Purpose:** Eliminate implicit identity and mutable single-slot state.

**Current status (2026-06-29):** W2 v0.2 integrates project-wide writer/store identity, cross-worktree command submission, non-shared compatibility paths, evidence-derived independence, typed RuleEvaluation referents, regenerability, and verified-snapshot replay. Outcome remains Manager-review-pending; implementation and migration are prohibited.

**Must define:**

- identifiers and versioning;
- lifecycle transitions;
- dispatch, claim, lease, retry, cancellation, and idempotency;
- attempt and supersession lineage;
- typed blocking and partial outcomes;
- artefact manifests and validation state;
- review and decision authority;
- deterministic view rebuild.

**Review gate:** Historical overwrite, wrong-root, retry, interruption, and competing-attempt scenarios are representable without information loss.

### W3 — Context, memory, and retrieval specification

**Purpose:** Replace full-history preloading with bounded, source-linked context.

**Must define:**

- event history, state, memory, and working-context distinctions;
- context packet and manifest schema;
- retrieval policy by role and risk;
- conflict, staleness, confidence, and provenance fields;
- compaction and consolidation lifecycle;
- procedural-memory/skill version selection;
- context-size and retrieval-recall evals.

**Review gate:** Representative Manager and Worker tasks retrieve all governing rules and evidence under an explicit size budget.

### W4 — Agent profiles and model-routing specification

**Purpose:** Make capability, risk, and independence explicit.

**Must define:**

- role profiles and permissions;
- epistemic risk tiers;
- model and reasoning metadata;
- routing policy and eval threshold;
- fresh-context and cross-family review requirements;
- fallback and provider-outage behavior;
- human-approval transitions;
- rules for when multi-agent execution is inappropriate.

**Review gate:** Model choice is reproducible from task metadata and eval policy, with no silent reduction in R2/R3 assurance.

### W5 — Research assurance and independent-review specification

**Purpose:** Generalise the strong TDL assurance approach and enforce two-key validity.

**Must define:**

- core assurance lanes and domain-pack interface;
- pre-registration and amendment lifecycle;
- contract ownership and approval;
- machine-checkable and human-review-only claims;
- proof obligations, counterexamples, metamorphic tests, and benchmarks;
- result-to-claim promotion;
- negative and partial outcome handling;
- TDA and general statistical/social-research packs.

**Review gate:** The implementer cannot be the sole approver of an R2/R3 governing rule, and a structurally valid result cannot bypass scientific review.

### W6 — Evaluation, observability, and audit specification

**Purpose:** Regression-test the harness and make failures diagnosable.

**Current status (2026-06-29):** W6 v0.2 reserves F-001–F-024 and S-001–S-016, separates incident basis from input fidelity, requires independent scientific-property grading and declared family/context diversity, and adds qualitative/proportional profiles. Full executable schemas, tooling, thresholds, and retention remain deferred to W3–W5/W7–W8 dependencies.

**Must define:**

- fixture format;
- outcome and trajectory graders;
- deterministic, model, and human grading;
- historical failure corpus;
- trace schema and privacy rules;
- operational and scientific metrics;
- model/skill/prompt/hook change gates;
- calibration and false-positive review.

**Review gate:** At least one fixture exists for every material failure class in the evidence register, with expected pre-control failure and post-control success.

### W7 — Runtime adapter and policy-parity specification

**Purpose:** End manual Claude/Codex policy drift.

**Must define:**

- canonical policy representation;
- adapter interface;
- Claude and Codex mappings;
- hook semantic coverage;
- tool and permission differences;
- skill packaging and versioning;
- safe generation and divergence behavior;
- parity tests and upgrade procedure.

**Review gate:** Removing a safeguard from one runtime requires an explicit canonical change and failing parity evidence.

### W8 — Resource, checkpoint, and operations specification

**Purpose:** Represent machine ownership and long-running state mechanically.

**Must define:**

- resource claims and conflicts;
- benchmark and feasibility protocol;
- checkpoint compatibility;
- heartbeat and stale lease behavior;
- stop, pause, resume, partial, and escalation transitions;
- orphan-process and orphan-artefact handling;
- operator commands and recovery evidence.

**Review gate:** The T1.6 and T1.9-style runtime cases can be simulated without relying on prose or session memory.

### W9 — Migration and pilot specification

**Purpose:** Introduce the system without contaminating active research.

**Must define:**

- legacy import format and status mapping;
- `.apm/` compatibility views;
- pilot selection rubric;
- rollback and stop criteria;
- baseline and comparison metrics;
- user review points;
- deprecation path for mutable bus and Tracker state.

**Review gate:** Pilot failure can be rolled back without changing any accepted research artefact or decision.

### W10 — Operations guide and project template

**Purpose:** Make the result reusable beyond TDL.

**Must define:**

- project initialization;
- minimal core directories and schemas;
- role and provider configuration;
- domain-pack installation;
- task authoring and review workflows;
- maintenance, backup, migration, and deprecation;
- sample R0, R2, and R3 workflows;
- non-TDA example.

**Review gate:** A fresh project can demonstrate the lifecycle without referencing TDL-specific paths, paper IDs, or topology concepts.

## 3. Dependency order

```text
W0 Legacy boundary
 └─ W1 Architecture
     ├─ W2 Schemas and lifecycle
     │   ├─ W3 Context and memory
     │   ├─ W4 Roles and routing
     │   ├─ W5 Research assurance
     │   └─ W8 Resources and operations
     ├─ W6 Evals and observability
     └─ W7 Runtime adapters
          └─ W9 Migration and pilot
               └─ W10 Project template
```

W6 begins with fixture collection during W0 but cannot finalize trace contracts until W2. W5 can reuse existing contracts and assurance skills while its general interface is being designed.

## 4. Pilot selection rubric

The first pilot should:

- be new work rather than an active migrated task;
- have a clear mathematical or statistical design;
- be bounded to hours rather than days;
- use inputs whose existence and vintage can be independently verified;
- produce a small set of typed artefacts;
- admit deterministic contracts and at least one human-review question;
- benefit from an independent verifier;
- not sit on the critical path to an imminent paper submission;
- have meaningful negative or Partial outcomes;
- be executable under both compatibility and new views.

Avoid as the first pilot:

- T1.28 while it is active;
- a multi-day null battery;
- a task requiring unresolved data access;
- a paper-claim reversal;
- a large historical import;
- a new distributed or cloud infrastructure dependency.

## 5. Verification programme

### 5.1 Structural verification

- schemas validate;
- IDs and references resolve;
- event replay is deterministic;
- generated views match canonical state;
- adapters cover canonical safeguards;
- migration preserves source links;
- no task/report overwrite is possible.

### 5.2 Scientific verification

- governing rule is locked before producing work;
- formula and implementation are independently checked;
- null operation changes the tested object;
- representation and data vintage are coherent;
- inference and multiplicity match the design;
- result-to-claim mapping is conservative;
- unresolved evidence yields Partial or blocked state.

### 5.3 Operational verification

- interrupted attempts recover;
- stale leases and orphan processes are visible;
- resource conflicts block dispatch;
- benchmark prerequisites are bounded;
- context packets stay within budget;
- provider failure does not corrupt canonical state;
- legacy compatibility views can be retired incrementally.

### 5.4 Human verification

- task and evidence state remain understandable without database tooling;
- Stephen can identify the next required decision from a single-screen view;
- methodological approval is requested only at genuine forks;
- historical provenance remains navigable;
- the workflow reduces rather than increases coordination burden.

## 6. Deliverable completion standard

A design deliverable is complete when:

1. every source and decision it relies on is cited;
2. owned state and external interfaces are explicit;
3. failure and recovery behavior are specified;
4. deterministic tests and agent evals are defined;
5. research-assurance lanes are classified;
6. migration and backwards compatibility are addressed;
7. placeholders and ambiguous modal language have been removed;
8. an independent reviewer has assessed R2/R3 logic;
9. Stephen has accepted any methodological or governance decision it introduces.

## 7. Recommended first specification pass

The first specification pass now comprises the W0 manifest/addendum, W1 v0.2, W2 v0.2, W6 v0.2, the adversarial review, and its reconciliation. The next action is deterministic cross-document verification followed by a bounded delta review; implementation remains out of scope.
