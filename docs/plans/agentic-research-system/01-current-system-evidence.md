# Current-System Evidence and Source Register

**Audit date:** 2026-06-27  
**Purpose:** Preserve the evidence behind the transition plan so later design decisions can be challenged against source material rather than remembered summaries.

## 1. Source hierarchy

When sources disagree, use this order:

1. committed result artefacts, input-provenance manifests, pre-registrations, and active contracts;
2. current code and binding tests;
3. task-specific bus prompts, logs, reports, and decision records;
4. current APM guides and canonical repository rules;
5. Tracker and Plan summaries;
6. consolidated memory and narrative retrospectives;
7. strategic forecasts and external framework guidance.

This order distinguishes evidence of research outcomes from guidance about how work should be performed.

## 2. Supplied source material

### 2.1 Context engineering and agentic SDLC

- `C:\Users\steph\Documents\TDA-Research\02-Notes\Day_1_v3.pdf` — *The New SDLC With Vibe Coding*, Addy Osmani, Hassan Saboo, and Christos Kartakis, Google Agents Whitepaper Series (May 2026).
- `C:\Users\steph\Documents\TDA-Research\02-Notes\2025_Day_3_Rewrite_v1_ContextEngineering.pdf` — *Context Engineering: Sessions, Memory*, John Milam, Michael Gulli, and Kristopher Nawalgaria, Google Agents Whitepaper Series (May 2026).

These are practitioner/vendor whitepapers rather than project authority. They inform terminology and harness-design principles; repository evidence, pre-registrations, contracts, and attributed project decisions outrank them.

Materially relevant principles:

- agentic engineering depends on specifications, tests, evals, guardrails, and human judgment;
- tests assess deterministic properties while evals assess non-deterministic behavior and trajectories;
- context includes instructions, knowledge, memory, examples, tools, and guardrails;
- static and dynamically retrieved context should be separated deliberately;
- skills are procedural memory and need their own lifecycle;
- orchestration, execution, sessions, memory, and external knowledge are distinct components;
- session history is not identical to the context sent to the model on each turn;
- append-only events and mutable state projections serve different purposes;
- compaction and consolidation require provenance back to source events;
- multi-agent systems need explicit history-sharing and artefact-handoff choices;
- model routing should assign the strongest models where uncertainty and consequence are highest.

### 2.2 Research strategy

- `docs/plans/strategy/Meta-Research-Plan-23-03-2026.md`

Relevant findings:

- it provides a coherent four-stage research direction from Paper 1 consolidation through Mapper, zigzag, multipersistence, cross-national work, forecasting, GNNs, CCNNs, and fairness;
- its stage dependencies remain useful as hypotheses about sequencing;
- computational forecasts such as “minutes” have proved insufficiently evidence-based for exact W2 and null work;
- calling Mapper outcome colouring a “causal geography” exceeds what associative structure alone establishes;
- a fixed calendar-stage representation does not match the live programme, where Stage 2 work can complete while Stage 1 assurance remains active;
- methods, data access, software maturity, and comparative representation require explicit feasibility gates before being treated as committed projects.

## 3. Current APM strengths to preserve

### 3.1 Planning and approval

The Planner and Manager structure provides:

- explicit Spec, Plan, Rules, and Tracker artefacts;
- user approval gates;
- work breakdown and dependency tracking;
- self-contained task envelopes;
- worktree and branch isolation;
- task logs, reports, handoffs, and recovery procedures.

### 3.2 Research assurance

The repository has unusually strong research controls:

- pre-registered parameters and decision rules;
- contracts divided into formula, schema, invariant, and output-validation kinds;
- binding-test requirements;
- validation hooks before commit;
- representation-freeze checks;
- explicit null-model, FDR, estimator, and topology audits;
- input-provenance manifests with hashes or vintage rules;
- result provenance, date suffixes, and no-overwrite requirements;
- paper-claim and vault obligations;
- `Partial` and escalation semantics where evidence is missing.

### 3.3 Long-running computation

Current practice includes:

- preflight benchmarks;
- worker and memory projections;
- resumable checkpoints;
- exact-run guardrails;
- observed-equivalence canaries;
- retained per-draw statistics;
- explicit refusal of approximation when it changes the pre-registered statistic.

These controls are not incidental; they are requirements for the successor system.

## 4. Current APM weaknesses and evidence

### 4.1 Context overload

The standard Manager initialization material audited on 2026-06-27 comprised approximately:

| Source | Words |
|---|---:|
| `.apm/spec.md` | 5,354 |
| `.apm/plan.md` | 18,830 |
| `.apm/tracker.md` | 20,239 |
| `.apm/memory/index.md` | 427 |
| `AGENTS.md` | 892 |
| `CLAUDE.md` | 2,291 |
| `CONVENTIONS.md` | 3,814 |
| Codex `task-assignment.md` | 3,855 |
| Codex `task-review.md` | 4,022 |
| `apm-communication/SKILL.md` | 897 |
| **Total** | **60,621** |

This is roughly 80,000 tokens under a simple word-to-token estimate, before task-specific authoritative sources, code, results, contracts, or user discussion.

The Tracker was approximately 164 KB with some individual lines exceeding 14,000 characters. Full histories inside status cells create repetition, contradictory snapshots, poor diffability, and weak retrieval precision.

### 4.2 State and sequence mismatch

Evidence in `.apm/tracker.md` includes:

- Stage 2 marked complete while Stage 1 remains active;
- a Stage 0 task marked “bus overwritten by T0.12”;
- major decisions, corrections, branch state, run details, and review history accumulated in single cells;
- machine/resource scheduling described narratively rather than represented as state.

The problem is not parallel work itself. The problem is that a linear mutable document is being asked to represent a dependency graph, task event log, queue, resource scheduler, and decision register simultaneously.

### 4.3 Single-slot bus

The bus protocol treats files as empty or holding one awaiting message:

- `.apm/bus/<agent>/task.md`
- `.apm/bus/<agent>/report.md`
- optional handoff material

Agent identity is inferred from the directory. The protocol lacks:

- immutable task and dispatch IDs;
- ordered queue semantics;
- acknowledgement and lease;
- attempt identity and retry lineage;
- issued and claimed timestamps;
- schema version;
- idempotency key;
- correlation to context, artefacts, decisions, or resource claims;
- typed error and blocking state;
- atomic prevention of overwrite.

The simplicity is useful and should survive as a human-readable projection, but not as canonical state.

### 4.4 Main-checkout/worktree split

Historical Worker runs demonstrate that:

- the authoritative bus and logs may remain under the main checkout;
- code edits and validations happen in a detached worktree;
- result or checkpoint roots may be project-rooted rather than worktree-rooted;
- a Worker can incorrectly conclude no task exists if it checks only the worktree-local bus.

This is a legitimate architecture, but the roots need explicit typed identities in every dispatch rather than discovery from convention.

### 4.5 Claude/Codex policy drift

The audit found:

- `.claude/settings.json` includes notation, result-no-overwrite, and dispatch-readiness PreToolUse hooks;
- `.codex/hooks.json` includes only notation;
- Claude `task-assignment.md` contains newer cost-model, benchmark-validity, memory, backend, input-provenance, and dispatch-readiness requirements absent from the Codex copy;
- `CLAUDE.md` contains a substantial `APM_RULES` block not mirrored in `AGENTS.md`;
- `CLAUDE.md` refers to APM v0.5.3 and `.apm/Implementation_Plan.md`, while `.apm/metadata.json` records APM v1.0.1 and current files use different paths.

Consequently, model choice currently changes not only model capability but also the safety policy applied to the task.

### 4.6 Unsafe synchronization direction

`tools/sync_agent_skills.py` declares `.agents/skills/` the authoring source of truth and mirrors it into `.claude/`. On 2026-06-27 its check reported divergence in at least:

- `commit-log`, where the Claude side held Windows UTF-8 commit-message guidance;
- `pre-reg-to-dispatch`, where the Claude side held newer planned-contract behavior.

Blind synchronization would erase newer safeguards. The guide check verifies selected marker presence rather than full semantic Claude/Codex parity.

### 4.7 Dispatch gate coverage

`shared/manager_dispatch_check.py` is a strong foundation. It validates worktree/environment setup, cleared report bus, contract validation, and provenance manifests and emits a Dispatch Readiness verdict.

Remaining gaps:

- the blocking dispatch hook is Claude-specific;
- hook failures can fail open;
- task-prompt checking is described as a judgment aid rather than a hard gate;
- current tests cover selected rendering and setup cases rather than full end-to-end dispatch states;
- no test suite exercises bus overwrite, acknowledgement, handoff, recovery, runtime parity, or adapter coverage.

### 4.8 Scientific independence gap

`contracts/README.md` states that a contract should be authored upstream or by a dedicated extraction agent, never by the same agent that writes the implementation.

The T1.28 Worker prompt, however, directs the Worker to:

- author binding tests for pending contracts;
- clear pending flags;
- implement producing code;
- run the computation;
- produce result artefacts.

That may be pragmatically efficient, but it allows one interpretation to define both the rule and proof of compliance. The successor system needs explicit contract ownership and independent approval.

### 4.9 Pending-contract ambiguity

Pending contracts are useful during staged development, but a dispatch gate can pass while new task-specific contracts remain `pending:true`. This permits infrastructure readiness to be confused with scientific authorization.

The redesigned lifecycle should distinguish:

- contract-authoring task;
- contract-review transition;
- implementation task;
- producing-run authorization.

### 4.10 Cost and resource state

T1.28 contains good prose guardrails—preflight, at least four processes, checkpointing, resumability, a 12-hour stop threshold, and awareness that T1.6 owns the machine—but lacks typed resource state or a Manager-side numerical projection in the task record.

Historical evidence also shows:

- a benchmark-only mode can execute full hidden prerequisites;
- timing fewer evaluations than workers can understate serial cost;
- threading can fail to parallelize GIL-holding exact W2 work;
- memory can bind before wall time;
- `B >= 1000` is less reproducible than an exact locked value;
- feasibility and scientific correctness are separate gates.

### 4.11 Agent topology remains shallow

The repository contains detailed skills but few persistent agent profiles. APM Workers are generic roles identified mainly by bus slug. There is no consistently orchestrated topology for:

- independent derivation;
- adversarial null-model review;
- topology benchmark verification;
- representation audit;
- provenance-only review;
- claim-strength review;
- resource-cost review.

These functions exist as skills, but task envelopes do not mechanically require role independence or record reviewer capability.

### 4.12 No harness regression suite

The codebase contains extensive research tests and contracts, but lacks a fixture suite that asks whether:

- a Manager includes the right evidence;
- a Worker stops at a guardrail;
- a context compiler retrieves the governing decision;
- a handoff preserves task state;
- runtime adapters enforce equivalent rules;
- a verifier catches an implementation's conceptual error;
- a model change degrades mathematical or operational performance.

Without such evals, prompt, skill, hook, and model changes are effectively deployed without regression testing.

## 5. Historical lessons to encode as fixtures

### 5.1 Bus routing and closure

- Resolve the authoritative bus before substantive work.
- Distinguish main-checkout control files from worktree code.
- Completion includes logs, report delivery, and bus/state closure.

### 5.2 Hard guardrails

- A projected runtime threshold is a stop condition, not encouragement to continue.
- Green code tests do not override an exceeded research or cost guardrail.
- No final result should be fabricated when the full design was intentionally not run.

### 5.3 Stage-boundary corrections

- Classify a correction as diagram generation, metric aggregation, downstream summary, or provenance repair.
- Do not expand a stochastic design when correcting a downstream metric unless explicitly authorized.
- Reuse valid cached objects and preserve the governing design.

### 5.4 Benchmark integrity

- Cap expensive prerequisites in benchmark modes.
- Emit progress before the first expensive batch.
- Benchmark more work items than available workers or measure serial cost directly.
- Project all multiplicative evaluations and peak process memory.
- Verify the actual parallel backend empirically.

### 5.5 Representation and data vintage

- File presence does not establish vintage coherence.
- Git hashes and timestamps serve different provenance cases.
- Frozen transformations must remain frozen through null and subgroup work.
- A coherent earlier object is preferable to mixing newer inputs with older labels.

### 5.6 Research claims

- Exact result JSON and decision fields outrank narrative reports.
- FDR family, p-value denominator, estimand, and eligibility must match the pre-registration.
- A result may support a weaker claim than the planned prose.
- Associative topology does not itself establish causation.

## 6. External primary-source register

These sources inform architecture but do not override repository research evidence:

- Anthropic, “How we built our multi-agent research system”: https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, “Effective harnesses for long-running agents”: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, “Harness design for long-running application development”: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic, “Scaling Managed Agents: Decoupling the brain from the hands”: https://www.anthropic.com/engineering/managed-agents
- Anthropic, “Demystifying evals for AI agents”: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- OpenAI, Agent evals: https://platform.openai.com/docs/guides/agent-evals
- OpenAI, Trace grading: https://platform.openai.com/docs/guides/trace-grading
- OpenAI, Model optimization: https://platform.openai.com/docs/guides/model-optimization
- A2A protocol specification: https://github.com/a2aproject/A2A/blob/main/docs/specification.md
- METR, measuring AI ability to complete long tasks: https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/

Relevant external conclusions:

- multi-agent work is most useful for independent breadth and explicit artefact handoff, not tightly coupled shared-state work;
- long-running systems benefit from durable progress artefacts, explicit handoff, and context resets;
- session, harness, sandbox, event history, and tools should expose stable interfaces;
- evals should combine outcome, trajectory, deterministic, model, and human grading;
- task identity, context identity, lifecycle state, communication, and output artefacts should be distinct;
- model routing must be calibrated empirically rather than assumed from price or branding.

## 7. Evidence limitations

- The Graphify index emphasized numerical code paths rather than APM documentation and was not authoritative for workflow design.
- The GitNexus index was several commits behind the checkout during the audit; its results were used for navigation and verified against files.
- Tracker summaries contain stale and superseded material; exact claims require checking their referenced artefacts.
- The assumption that T1.28 closes Phase 1 requires live Manager confirmation.
- External agent frameworks evolve quickly; protocol details must be reverified when implementation specifications are written.

## 8. W11 dated live-evidence addendum (2026-07-18)

**Scope:** WP6.5 W11 specification evidence only
**Authority:** dated read-only observations; not admission, implementation, migration,
ownership-transition, result, eligibility, Decision, or claim authority

This addendum records the new live sources used by W11 so design README entry
criterion 2 is literal. The sources are mutable vault evidence; their hashes identify
the bytes observed on the stated date, not a permanently frozen expected side.

### 8.1 Dated live evidence

| Evidence and authority class | Exact observed path / physical context | Bytes and SHA-256 observed 2026-07-18 | Mutability and limitations |
|---|---|---|---|
| Living Discovery backlog; current legacy lifecycle authority under P-004/P-032 | `C:\Users\steph\TDL\vault\00-Meta\Discovery\_backlog.md` | 26,392 bytes; `37eec1ba6bb7929d95d5349ada2f75d93636c8356aad5dffc6a59981fc0269e7` | Mutable and legacy-written. Contains active, superseded and decision-pending prose plus legacy PROMOTE/PARK/KILL labels. The hash is a dated observation only; no row is imported, adopted, transitioned or frozen by W11. A later transition/cutover must make a fresh handle-bound observation and use the accepted inventory/mapping contracts. |
| TDA-scale v1.0.0 package manifest; human-authored planning evidence for the missing admission interface | `C:\Users\steph\TDL\vault\00-Meta\Research Direction Reports\Evidence-Led TDA Scale and Research Programme for ARS - package manifest - v1.0.0 - 2026-07-16.md` | 5,843 bytes; `e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf` | Mutable vault planning document, not an accepted `DossierExpectedSet` or admissible dossier. It declares 17 immutable components and three separately hashed sources; the independent review resolved and rehashed all 20 linked files. WP6.6 must use a deliberately re-versioned package with accepted literal expected rows and fresh hashes. |
| TDA-scale v1.0.0 master programme component; human-authored planning evidence | `C:\Users\steph\TDL\vault\00-Meta\Research Direction Reports\Evidence-Led TDA Scale and Research Programme for ARS - v1.0.0 - 2026-07-16.md` | 28,244 bytes; `277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea` | Mutable planning-only source and Gate A evidence. Its current content does not satisfy W2 object/ScopeDefinition schemas, admission authority, pre-registration, dispatch, result, eligibility or claim gates. |
| Registered vault-root physical-path observation; operational evidence for the W11 path protocol | Registered path `C:\Users\steph\TDL\vault`; observed as `Directory, ReparsePoint`, link type `Junction`, target `C:\Users\steph\Documents\TDA-Research` | No content hash is asserted for a directory link. The accepted path contract must bind the reparse tag/target and target volume/file identities at operation time. | Current filesystem configuration, not a permanent path identity. A string-resolved path or this dated target is insufficient against reparse, hardlink or parent-swap races. The three proposed `00-Meta/ARS/...` namespaces did not exist when independently reviewed. |

### 8.2 Provenance and permitted use

The independent report at
[`reviews/adversarial-wp6-5-w11-spec-review-2026-07-18.md`](reviews/adversarial-wp6-5-w11-spec-review-2026-07-18.md)
re-observed the backlog, manifest and master bytes and reported exact hash agreement.
That review is evidence fidelity, not approval of W11 or any live object.

Permitted use is limited to specification requirements and future synthetic fixture
design. Tests must not depend on these mutable files. No process may use this addendum's
hashes as a dossier expected oracle, final cutover inventory, migration Decision,
ownership mapping, accepted result, eligibility input or paper-claim authority.
