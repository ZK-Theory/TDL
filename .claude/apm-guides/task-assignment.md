# APM 1.0.1 - Task Assignment Guide

## 1. Overview

**Reading Agent:** Manager

This guide defines how you construct and deliver Task Prompts for Workers, manage version control workspace isolation, and coordinate bus-based delivery. Task Prompts are self-contained - Workers receive everything needed to execute a Task without referencing the Spec or Plan.

### 1.1 Outputs

- *Task Prompt:* Content written to Task Bus for Worker to receive.
- *Follow-up Task Prompt:* Refined prompt when the review outcome determines retry.
- *Feature branches:* One branch per dispatch unit, created off the base branch.
- *Worktrees:* Isolated working directories under `.apm/worktrees/` for parallel dispatch.

---

## 2. Operational Standards

### 2.1 Dependency Context Standards

Tasks may depend on outputs from previous Tasks. The context you include depends on the Worker's familiarity with the producer's work.

**Same-agent dependencies:** The Worker previously completed the producer Task and has working familiarity. Provide light context - recall anchors, key file paths, brief reference to previous work. Detail increases with dependency complexity.

**Cross-agent dependencies:** A different Worker completed the producer Task. The Worker has zero familiarity. Provide comprehensive context - explicit file reading instructions, output summaries, integration guidance. Assume nothing.

**After Worker Handoff:** The incoming Worker only has current-Stage Task Logs loaded. Current-Stage same-agent dependencies remain same-agent. Previous-Stage same-agent dependencies are reclassified as cross-agent because the incoming Worker lacks that working context. Check cross-agent overrides in the Tracker during dependency analysis to determine which Tasks have been reclassified.

**Dependency identification:** Check the Task's Dependencies field in the Plan. Cross-agent dependencies are bolded. "None" indicates no dependencies.

**Chain reasoning:** Dependencies may have their own dependencies. Trace upstream when ancestors established patterns, schemas, or contracts the current Task must follow. Stop tracing when an intermediate node fully abstracts what came before. When uncertain whether an ancestor is relevant, include rather than risk missing critical context.

### 2.2 Task Prompt Content Standards

Task Prompts must be self-contained. Workers have the same tools as any agent but are intentionally scoped to their Task Prompt, Rules, and accumulated working context to keep them focused on execution. You enforce this scoping by extracting relevant content from the Spec, Plan, and authoritative sources into each prompt rather than referencing those documents by path. Never reference the Spec, Plan, Tracker, or Index by path - Workers should not read them. Task Prompt instructions and objectives do not reference Stage numbers, other Task IDs, or coordination-level concepts (dependency context sections reference producer Tasks by ID as needed). Validation criteria are Worker-scoped.

**Embed** content the Worker cannot discover from the codebase alone: design decisions and constraints from the Spec, Task definitions and guidance from the Plan, Task-relevant coordination context from the Tracker, observations from the Index, corrected findings from previous Tasks, and content from authoritative User documents the Spec references. Preserve specificity with exact constraints, not summaries. Present all embedded content as direct factual context. Never attribute content to its source artifact or use coordination-level vocabulary - Workers should not be aware of the Spec, Plan, Tracker, Index, or Memory - surfacing these concepts breaches their execution-focused scope.

**Reference with reading instructions** content that exists in the codebase: source files, existing patterns, configurations. Point the Worker to specific files and what to look for in them - the Worker reads them directly from their workspace. This applies to both dependency context and Spec content that references codebase patterns. The Manager identifies which files matter and what to look for, rather than embedding their contents.

**Exclude** content relating to other domains, providing background without actionable requirements, or already captured in the Task's Guidance field.

**Compute resource-preflight requirement.** Every Task Prompt that runs long stochastic compute - bootstraps, permutation nulls, MICE-pooled refits, per-individual/per-cluster batteries - must require a production-entry-point benchmark across feasible worker counts, then record the **optimal safe count**: the feasible count with the lowest p75-projected wall time after actual backend parallelism and per-process memory/headroom are verified. Do not prescribe a fixed worker floor or assume that more workers are faster; lower counts, including serial execution, require the recorded preflight rationale. Expose the selected worker count and wall-time budget explicitly, write chunked checkpoints so a halted job resumes rather than restarts, and **flag any job expected to exceed ~30 min as long-running with an up-front wall-time estimate before launch**. Locked in `CONVENTIONS.md` (2026-07-17) after T1.38 measured N=3 as safer and faster than a forced N=4 launch.

**Cost-model gate (size the test statistic, not just the generation step).** Before sizing any stochastic-compute Task as short/cheap - or before dispatching one whose wall-time you have not bounded - cost the dominant operation explicitly: estimate **(number of test-statistic evaluations) x (measured per-evaluation cost) / workers** and write the projected wall time into the dispatch reasoning. The evaluation count is the *product of every multiplicative design parameter* (e.g. `n_trials x bank_B` pairwise distances, `B x n_pairs` null-null comparisons), not just the count of expensive objects generated. Cache-reuse that eliminates fresh PH/model-fit generation does **not** make a Task near-free if it still performs a large number of distance/statistic evaluations on the cached objects - cost those evaluations separately. When the per-evaluation cost is not already on file (e.g. the gudhi W2 benchmark), require a bounded `--benchmark-only` probe at realistic scale **at dispatch**, not after a Worker session is spent. A `>12h@<N>w` escalation guardrail in the prompt is necessary but not sufficient: it catches the overrun late; the cost-model bounds it early. Added 2026-06-21 after T1.6 was sized "near-free via cache reuse" yet projected 13.8 h - the dispatch costed the avoided PH generation but not the 20,200 retained exact-W2 evaluations (`n_trials=100 x bank_B=200 + bank_B`).

**Benchmark-validity and resource sub-rules (the cost-model is only as honest as its probe).** A `--benchmark-only` projection that times **fewer distances/evaluations than the worker count** is invalid: when the batch is smaller than the pool, every item runs concurrently, so `elapsed / count` understates the true *serial* per-evaluation cost by ~the parallelism factor. Require the probe to time **strictly more evaluations than workers** (>= 2x the pool is safe) before extrapolating, or to measure a genuine serial per-evaluation cost. Two further requirements: (1) **cost memory, not just wall-time** - project peak resident memory as `per-process-peak x workers` and confirm it fits free RAM with headroom; an under-memory run OOMs regardless of wall-time budget. (2) **Verify backend parallelism empirically - do not assume a C-extension releases the GIL.** `--backend threading` gives zero parallelism for GIL-holding native code (e.g. gudhi exact-W2); joblib's default `loky` (multiprocessing) is the parallelising backend used by the rest of the battery. Prefer a memory-preflight that auto-caps the worker count to fit RAM (precedent: `run_t1_5_diagnostics.py`, `run_landmark_sensitivity.py`). Added 2026-06-21 after the T1.6 B=100 re-dispatch: a probe timing 4 distances against 8 threading workers projected 5.86 h for a job that was ~28 h serial (threading parallelised nothing) and OOM'd at trial 0.

**Research assurance content.** For Tasks that touch mathematical, statistical, topological, representation, output, or paper-claim logic, include a Research Assurance Requirements section in the Task Prompt. Classify the touched assurance lanes before prompt construction:
- *Topology:* persistent homology construction, filtration choices, diagram metrics, landscapes, Mapper, zigzag, multipersistence, landmark sampling, and topology-vs-geometry interpretation.
- *Stochastic / Null Model:* permutation exchangeability, Markov order, stratification, label/cohort/order shuffles, null-null construction, bootstrap, RNG/seed propagation, and p-value formulas.
- *Statistical / Panel:* IPW, MICE, FDR/BH/BY, GLMM/Firth/svyglm, Manski bounds, sample denominators, estimands, and eligibility rules.
- *Representation:* PCA/UMAP/scaler fitting, frozen loadings, GMM labels, state recoding, trajectory windows, and embedding comparability.
- *Output / Provenance:* result JSON schema, cache provenance, date-suffixed outputs, no-overwrite constraints, seeds, parameters, and vault traceability.
- *Paper Claim:* pre-registration decision rules, outcome-to-prose mapping, table/figure claims, and disclosure obligations.

For each touched lane, decide whether the assurance is machine-checkable, human-review-only, requires a pre-registration amendment, requires a new or pending contract, requires an output schema, or requires a vault/CONVENTIONS lock. Every machine-checkable research claim should either have a concrete enforcement artifact (contract, binding test, output schema, validation command, smoke/canary, or provenance check) or an explicit note explaining why it is not being mechanized in this Task.

**Contract-Quality Gate.** Before dispatching a Task that authors, modifies, or relies on a contract, confirm the relevant contract set passes gates 1b, 1c, and 2b before the Worker starts. Each formula invariant must carry exactly one of `expression` or `enforced_by`; each `binding.must_assert` lettered clause must be claim-to-assertion covered by the binding test and local validators it calls; each schema `required_key` type/bound must be checked by the validator or binding. Provenance contracts may grandfather pre-existing immutable result files through explicit `legacy_exempt` entries, but Task Prompts must never ask Workers to backfill inferred provenance into historical JSONs.

**Input-Provenance Gate (data exists in the correct form).** Presence-checking an input is not the same as confirming it is the *right* input — co-consumed inputs must share a coherent data vintage. Before dispatching any Task that consumes input data, author (or update) its input-provenance manifest under `contracts/manifests/input-provenance/<task>-inputs.yaml` declaring each input's `path`, `root` (`worktree` → sha256-signed; `proj_root` → vintage-signed, per the two-path rule), and `expected` signature, then run `uv run --env-file .env python -m shared.manager_predispatch_check <manifest>` and **paste its output into the Task Prompt's Input Provenance Ledger section**. This is a mechanical gate, not an envelope claim written from memory: if R-B exits non-zero (a missing, sha256-mismatched, or vintage-incoherent input), the Task is not Ready — resolve the data or surface a User decision before issuing it. The same manifest is re-asserted at the Worker's commit by the `input-provenance-manifest-coherence` contract (set `enforced: true` once the inputs are coherent). Full mechanics: `.claude/rules/apm-outputs.md` § Input-provenance gate. Added 2026-06-22 after the B9 OM-vs-GMM ARI dispatch shipped against a 2026-05-02 OM input incoherent with 2026-04-08 GMM labels (ARI 0.2062 vs committed 0.2611807) — a data-coherence failure the Manager's envelope asserted "Confirmed on disk" without a fresh check.

**Experiment-Change Decision Gate (supersession is a decision, log it like one).** Before dispatching a Task that re-specifies a prior model, supersedes a result under the same basename, or selects among candidate metrics for an existing analysis, require the Task Prompt to instruct the Worker to record a `[DECISION]` entry — not a bare new result — carrying: (1) the old→new artifact pair (basenames + dates); (2) the driving reason (reviewer issue / methodological constraint / decision rule); (3) the superseded artifact marked explicitly do-not-cite (a SUPERSEDED pointer or CONVENTIONS-style note); (4) the consequence to any downstream claim. A new date-suffixed file records *what* changed; only a decision entry records *why* — captured at the moment of change or the reasoning is unrecoverable within weeks. Added 2026-07-06 after three of four audited Wave-1 experiment-changes had no change-time decision entry and the reasoning could not be reconstructed.

**Prose-dispatch register standard (a deliverable inherits the register of the prompt that commissioned it).** Every Task Prompt producing manuscript text must **name the audience and venue** ("manuscript text for a JRSS-B referee who has never seen this repository, this Task, or the reviewer-response plan") and must **state the channel separation**: the section file carries only text that could appear in the submitted PDF; traceability evidence, open items, gaps, provisionality, review status, tracker IDs, and anything addressed to the Manager or User go in the Task Log / bus report. Three Manager-side prohibitions:
- **Never call the deliverable a "working file"** — call it manuscript text for §X. Workers describe the thing you told them they were making.
- **Never pass reviewer-issue IDs (C1/C2/M1–M5/H1/L1) as the organizing frame.** Use them to decide *what* to fix; hand the Worker the *substance* ("v1's ground-metric formula is ℓ∞ and must be ℓ²"), not the tracker label — otherwise they become section headings.
- **Never write a validation criterion that is satisfiable inside the artifact.** "Every numerical claim traces to a results JSON" is a Task Log obligation; say so explicitly, or the Worker proves compliance in the prose ("Every number below is cited to its source JSON").

Full rule (auto-loads for any Task touching `papers/`): `.claude/rules/papers.md` § Prose work — audience, register, notation, completion. Added 2026-07-14 after ~16 P01-A/P01-B section files (≈11 already merged) were found carrying `This working file rewrites §X…` preambles, `## Issues (for Manager review before v2 assembly)` sections, and tracker IDs promoted into headings — the Workers were doing exactly what the prompts commissioned. Note `/humanizer` does **not** catch this: it targets AI tells, whereas workflow scaffolding in a manuscript is a wrong-artifact problem.

### 2.3 Follow-Up Standards

Follow-up Task Prompts occur when the review outcome determines retry after investigation. You arrive with: original Task Log findings, investigation results, understanding of what went wrong, and potentially modified planning documents.

**Content principle:** The follow-up is a new prompt - Objective, Instructions, Output, and Validation are refined based on what went wrong. Do not copy the previous prompt. The Worker operated with scoped context; your follow-up bridges the gap between what the Worker saw and what you now know from investigation, other Task completions, and planning document updates. Give the Worker concrete direction rather than restating the original Task Prompt.

**Log path continuity:** Use the same `log_path` as the original. The Worker overwrites the previous log. The Manager captures iteration patterns in Stage summaries when relevant.

### 2.4 Dispatch Standards

Before constructing individual Task Prompts, assess dispatch opportunities across Ready Tasks.

**Task readiness:** A Task is Ready when all its dependencies are Done. Read the Tracker for current statuses; cross-reference the Dependency Graph for newly unblocked Tasks.

**Dispatch modes.** Assess all Ready Tasks, group by Worker, and form dispatch units:
- *Batch:* Multiple Ready Tasks for the same Worker, dispatched together. Candidates either form a sequential chain (each depends only on the previous or already-complete Tasks) or are an independent group (no dependencies between them, all Ready simultaneously). When forming chains, weigh whether external Tasks depend on intermediate results - if so, dispatching individually allows earlier review and unblocks dependent Workers sooner. Soft guidance is 2-3 Tasks per batch.
- *Single:* one Ready Task for a Worker.
- *Parallel:* two or more dispatch units (any mix) with no unresolved cross-agent dependencies among them, dispatched simultaneously. Requires version control workspace isolation.

**Parallel dispatch prerequisites:** Version control must be initialized (established during Manager 1 initiation per `.claude/commands/apm-2-initiate-manager.md` §2.1 First Manager Initiation). If version control is not active, fall back to sequential dispatch. Recommend the User configure platform tool approvals for Workers to minimize interactive wait times during parallel execution.

Before dispatching a ready unit, check whether a pending report would unlock Tasks that combine well with the current unit. If it is the only outstanding report, waiting costs little. If multiple reports are pending or no plausible combination exists, dispatch immediately.

**Wait state:** When no Tasks are Ready but Workers are still active, communicate what was processed, what is pending, and what the User should do next. Direct the User to return the next report - if a pending report would unlock a better dispatch combination, recommend prioritizing that report.

### 2.5 Version Control Standards

Version control provides workspace isolation during parallel dispatch. Each dispatch unit operates on its own feature branch, and you coordinate all merges during Task Review. When multiple repositories are listed in the Tracker's Version Control table, identify which repository each Task operates in from the Spec's Workspace section. If the User initially declined version control but later requests it mid-session, initialize it: run `git init` if needed, detect or confirm the base branch, establish conventions with the User, update Rules and the Tracker, then proceed with branch-based dispatch.

**Branch standards:** Every dispatch unit gets its own feature branch off the base branch per the branch convention in the Tracker. APM terminology (Task IDs, Stage numbers, agent identifiers) does not appear in branch names, commit messages, or worktree directory names - these reflect the actual work, not the framework managing it. A batch of sequential Tasks assigned to the same Worker shares one branch.

**Worktree standards:** Worktrees are created only for parallel dispatch. Each parallel dispatch unit gets its own worktree so all parallel Workers operate in isolated directories and the main working directory remains on the base branch for merge operations. For sequential dispatch, the Worker operates in the main working directory on their feature branch.

- *Layout:* Worktrees placed under `.apm/worktrees/` per §4.3 Branch and Worktree Standards.
- *Concurrency limit:* maximum 3-4 concurrent worktrees.
- *Lifecycle:* short-lived - created before dispatch, removed after merge.

Worktrees contain only tracked files; if a Worker needs untracked assets, note this in the Task Prompt. When `.apm/` is tracked (or partially tracked), the worktree may contain `.apm/` files but all APM runtime operations (Task Logs, bus communication) must target the project root's `.apm/`, not the worktree copy. You need to read Task Logs and bus files for review before merging, so they must be accessible from the main working directory. Include this guidance in the Task Prompt's Workspace section for worktree dispatch.

### 2.6 Delivery Standards

Bus directories and files are created by the Planner during the Planning Phase - do not re-create them. Before writing to a Worker's Task Bus, read the Worker's Report Bus (`.apm/bus/<agent-slug>/report.md`) and capture its required `report_id`. Clear it only after its outcome is durably reflected in the Task Log and review state, then immediately re-read the Report Bus and require both the same `report_id` and byte-identical content before the empty write. A changed or missing identity is a collision: fail closed and preserve the slot. Clear by writing an empty file through the normal file-edit/write tool; do not use terminal truncation or shell redirection. If the permission layer denies the clear, preserve the slot and surface the exact denial instead of routing around it. Skip clearing on first Task Prompt to a Worker when no report exists. Read the Task Bus before writing to it per `.claude/skills/apm-communication/SKILL.md` §4 Message Bus Protocol. When dispatching multiple sequential Tasks to the same Worker, send them as a batch in a single Task Bus message per §4.5 Batch Envelope Format.

### 2.7 Non-APM Agent Dispatch

When a non-APM agent has joined the session and you need to assign follow-up work to it, write a plain assignment to its Task Bus - not a full Task Prompt. Include what to do and what to produce, and instruct it to report back. Do not include log paths, logging instructions, or Handoff metadata - non-APM agents do not log to Memory or participate in Worker tracking.

---

## 3. Task Assignment Procedure

Dispatch assessment followed by per-Task analysis and prompt construction for each Task in the dispatch plan. Follow-up prompts use a separate construction path when a review outcome requires retry.

### 3.1 Dispatch Assessment

Assess dispatch opportunities from current project state per §2.4 Dispatch Standards. Before each dispatch decision, assess the current project state visibly in chat under the header **Dispatch Assessment:** covering which Tasks are Ready, what dependency relationships exist among them, and what dispatch mode best serves progress and efficiency. Each dispatch cycle is a fresh assessment.

Perform the following actions:
1. Identify Ready Tasks from the Tracker. Cross-reference the Dependency Graph for newly unblocked Tasks.
2. Check whether a pending report would unlock Tasks that combine well with currently Ready Tasks. If waiting costs little, consider it. Otherwise proceed.
3. Group Ready Tasks by assigned Worker. Form dispatch units per §2.4 Dispatch Standards - assess all three modes (single, batch, parallel) before committing to a dispatch plan.
4. Add a research assurance assessment for each candidate Task: identify which assurance lanes it touches, whether it changes methodology or only executes an existing design, and whether pre-registration, contract, schema, provenance, or paper-claim checks must happen before dispatch.
5. Assess parallel opportunity: if 2+ dispatch units exist with no unresolved cross-agent dependencies - parallel dispatch.
6. Formulate dispatch plan: which Workers receive which units, whether parallel. For each Task, continue to per-Task analysis.

### 3.2 Per-Task Analysis

Execute for each Task in the dispatch plan.

Perform the following actions:
1. Read the Task's Dependencies field from the Plan. If "None," skip dependency context steps.
2. For each dependency, determine context depth per §2.1 Dependency Context Standards - check Worker Handoff state and auto-compaction notes in the Tracker, classify as same-agent or cross-agent, check cross-agent overrides, and trace upstream when ancestors are relevant. For Workers that recovered from auto-compaction, provide more comprehensive same-agent dependency context since reconstructed context may lack working nuance.
3. For cross-agent dependencies, read unique producer Task Logs and note key outputs, file paths, and integration details. When multiple Tasks in this dispatch cycle depend on the same producer, read that log once and extract from context for subsequent Tasks.
4. Extract Spec content relevant to this Task per §2.2 Task Prompt Content Standards. The Spec is in context from session start and refreshed on any modification. A fresh read is warranted at the start of a new Stage's first dispatch; per-Task re-reads of an unchanged Spec are not needed.
5. Perform research assurance triage per §2.2 Research assurance content when the Task touches mathematical, statistical, topological, representation, output, or paper-claim logic. Record which lanes are touched and which enforcement artifacts must be included in the prompt.
6. Extract Task definition fields from the Plan: Objective, Steps, Guidance, Output, Validation. When Guidance references Spec sections, resolve those references and extract the referenced content per §2.2 Task Prompt Content Standards. Transform steps into actionable instructions, incorporating Guidance and relevant Spec content.

### 3.3 Task Prompt Construction

Assemble the Task Prompt and deliver via the Message Bus.

Perform the following actions:
1. Construct YAML frontmatter per §4.1 Task Prompt Format.
2. Construct prompt body: Task Reference, Context from Dependencies (if applicable), Objective, Detailed Instructions, Research Assurance Requirements (when applicable), Workspace, Expected Output, Validation Criteria, Instruction Accuracy, Task Iteration, Task Logging instructions, Reporting Instructions.
3. Create a feature branch off the repository's base branch per §2.5 Version Control Standards. For parallel dispatch, create a worktree: `git worktree add .apm/worktrees/<branch-slug> -b <branch-name>`. Include the branch name (sequential) or worktree path (parallel) in the Workspace section.
4. Record the branch name in the Task row's Branch column when updating the Tracker.
5. Clear the incoming Report Bus per §2.6 Delivery Standards.
6. **Run the dispatch-readiness gate and paste its block into the envelope.** `uv run python -m shared.manager_dispatch_check --agent <slug> --branch <branch> --mode <parallel|sequential> [--provenance-manifest <yaml> ...]` verifies that the worktree+`.env` (parallel), the contracts (validate-only), the input-provenance ledger, and a cleared report bus **actually exist on disk** — not merely that the envelope describes them. Paste its `## Dispatch Readiness` output into the prompt body. If it reports FAIL, the Task is not dispatch-ready: create the missing artifact, or surface a User decision (e.g. an unresolved data-vintage choice), before writing the bus. This is enforced — the `dispatch-readiness-guard` PreToolUse hook blocks a Task Prompt bus write whose Dispatch Readiness block is absent or FAIL, so the gate survives context compaction (the procedure here is lazy-loaded and may not be in context post-compaction; the hook is not).
7. Read the Worker's Task Bus, then write the Task Prompt to it: `.apm/bus/<agent-slug>/task.md`. For batches, use §4.5 Batch Envelope Format.
8. Direct the User to the Worker's chat per `.claude/skills/apm-communication/SKILL.md` §2.1 Direct Communication:
   - If the Worker is not yet initialized - direct the User to start a new chat and run `/apm-3-initiate-worker <agent-id>`. The Worker detects the pending Task Prompt during init and begins executing. Only on first dispatch to this Worker.
   - If the Worker is already initialized - direct the User to run `/apm-4-check-tasks` in the Worker's chat.
   - For batch dispatch - summarize what the Worker will receive (number of Tasks, sequential execution).
   - For parallel dispatch - list each Worker with its required action.

### 3.4 Follow-Up Task Prompt Construction

Execute when the review outcome (per `.claude/apm-guides/task-review.md` §3.3 Review Outcome) determines follow-up is needed.

Perform the following actions:
1. Capture follow-up context: what went wrong, investigation findings, required refinement, any planning document modifications.
2. If planning documents were modified, extract relevant updated content per §3.2 Per-Task Analysis.
3. Refine all content sections per §2.3 Follow-Up Standards. Include a follow-up context section explaining the issue and required refinement.
4. Construct the follow-up prompt per §4.2 Follow-Up Format. Same `log_path` as the original.
5. Clear the incoming Report Bus per §2.6 Delivery Standards.
6. Read the Worker's Task Bus, then write to it: `.apm/bus/<agent-slug>/task.md`.
7. Direct the User to the Worker per §3.3 Task Prompt Construction step 7.

---

## 4. Structural Specifications

### 4.1 Task Prompt Format

Task Prompts are markdown files. Adapt based on Task needs - not all sections are required for every Task.

**YAML Frontmatter Schema:**
```yaml
---
stage: 1
task: 2
agent: frontend-agent
log_path: ".apm/memory/stage-01/task-01-02.log.md"
has_dependencies: true
---
```

**Field Descriptions:**
- `stage`: Stage number.
- `task`: Task number within Stage.
- `agent`: Worker identifier (kebab-case).
- `log_path`: Pre-constructed path for the Task Log. Path pattern: `.apm/memory/stage-<NN>/task-<NN>-<MM>.log.md` (relative to the project root). All Tasks in the same Stage share the same Stage directory. You construct the path; the Worker writes directly to it.
- `has_dependencies`: Whether dependency context is present.

**Prompt Body Sections:**
- *Title.* `#` heading using Task ID and title. Each section uses `##` heading:
- *Task Reference:* Task ID and assigned agent.
- *Context from Dependencies.* Included when `has_dependencies: true`. Format depends on dependency type per §2.1 Dependency Context Standards.
  - *Same-agent.* "Building on your previous work:" intro - `**From Task <N>.<M>:**` with key outputs and recall points - `**Integration Approach:**` with brief guidance.
  - *Cross-agent.* "This Task depends on work completed by [Producer Agent]:" intro - `**Integration Steps:**` numbered file reading instructions - `**Producer Output Summary:**` key features, files, interfaces, constraints - `**Upstream Context:**` for relevant ancestors.
- *Objective:* Single-sentence Task goal, optionally enhanced with coordination-level context.
- *Detailed Instructions:* Plan steps transformed into actionable instructions with integrated Spec content and guidance.
- *Research Assurance Requirements:* Included for Tasks touching mathematical, statistical, topological, representation, output, or paper-claim logic. List touched assurance lanes, governing pre-registration or decision rule, contracts or schemas in scope, parameters and seeds, output/provenance requirements, vault obligations, and any human-review-only claims. Instruct the Worker to report Partial rather than silently weaken or bypass an assurance requirement if implementation reality conflicts with the prompt.
- *Dispatch Readiness:* Required on every Task Prompt (per §3.3 step 6). The pasted `## Dispatch Readiness` output of `manager_dispatch_check.py` — the on-disk verification that the worktree+`.env` (parallel), contracts (validate-only), input-provenance ledger, and cleared report bus exist. Must show PASS; the `dispatch-readiness-guard` hook blocks the bus write otherwise.
- *Input Provenance Ledger:* The input-data component of Dispatch Readiness, for Tasks that consume input data (per §2.2 Input-Provenance Gate). The `manager_predispatch_check.py` output over the Task's input-provenance manifest — each input's path, root, on-disk signature, and coherence verdict — generated from a fresh on-disk check, never from memory. Names the manifest the Worker's commit gate re-asserts.
- *Workspace:* Working directory and branch name for sequential dispatch, or worktree path and project root for parallel dispatch. For worktree dispatch, instruct the Worker to perform code work in the worktree but resolve all `.apm/` paths (Task Log, bus files) from the project root. Worker operates in the specified workspace, commits there, and notes it in the Task Log. Workers do not merge.
- *Expected Output:* Deliverables from Plan Output field.
- *Validation Criteria:* From Plan Validation field.
- *Instruction Accuracy:* The objective and expected output are authoritative - deliver those. However, the detailed instructions and steps were constructed from planning documents and may contain inaccurate details, missed prerequisites, or outdated assumptions about the codebase. When a specific instruction contradicts what the codebase actually shows, validate the actual state rather than persisting with the instruction as written.
- *Task Iteration:* When validation fails, investigate before fixing - read error output, trace the cause, understand what went wrong. Apply one targeted change per iteration. When a fix does not resolve the issue, spawn a debug subagent with structured instructions: the error output, what you investigated and attempted, relevant file paths, and expected vs actual behavior. Direct it to trace the root cause and propose a fix. Validate the subagent's findings before applying. When the root cause could stem from multiple independent areas, spawn separate subagents in parallel. If unresolved after subagent investigation, report with Partial status.
- *Task Logging:* Path and reference to `.claude/apm-guides/task-logging.md` §3.1 Task Log Procedure.
- *Task Report:* Instruction to output a Task Report for User to return to Manager.

### 4.2 Follow-Up Format

Follow-up Task Prompts use the same structure as §4.1 Task Prompt Format with these modifications:
- *Title:* `APM Follow-Up Task: <Task Title>`
- *Follow-up context section* after Task Reference - previous issue, investigation findings, required refinement, additional guidance.
- *All content sections* refined based on what went wrong, not copied from the previous attempt.
- *Same `log_path`* as the original Task Prompt.

### 4.3 Branch and Worktree Standards

Branch naming follows the convention recorded in the Tracker Version Control table. Branch names are descriptive of the actual work; for batches, the name reflects the batch scope. Worktrees are placed under `.apm/worktrees/`. Each subdirectory name is derived from the branch name (e.g., replacing `/` with `-`). Each worktree directory contains a full checkout of all tracked files. Untracked files are not present.

### 4.4 Tracker VC Entry Format

VC configuration recorded in the Version Control table within the Tracker, with one row per repository. Branch state is tracked per-Task in the Task table's Branch column - an incoming Manager reads Task rows to rebuild working VC context.

**Format:**

```markdown
## Version Control

| Repository | Base Branch | Branch Convention | Commit Convention |
|-----------|-------------|-------------------|-------------------|
| <repo-name> | <branch-name> | <convention> | <convention> |
```

### 4.5 Batch Envelope Format

When sending multiple Tasks to a Worker in a batch, the Task Bus file uses this structure:

**YAML Frontmatter Schema:**
```yaml
---
batch: true
batch_size: <N>
tasks:
  - stage: 1
    task: 1
    log_path: ".apm/memory/stage-01/task-01-01.log.md"
  - stage: 1
    task: 2
    log_path: ".apm/memory/stage-01/task-01-02.log.md"
---
```

**Field Descriptions:**
- `batch`: Always `true` for batch envelopes.
- `batch_size`: Total Tasks in the batch.
- `tasks[].stage`: Stage number.
- `tasks[].task`: Task number within Stage.
- `tasks[].log_path`: Pre-constructed path for the Task Log, following the same pattern as single Task Prompts.

**Body:** Individual Task Prompts separated by `---` delimiters. Each Task Prompt retains its full structure (YAML frontmatter and body) as if standalone.

---

## 5. Common Mistakes

- *Planning document paths in Task Prompts:* Workers are scoped to their Task Prompt and Rules - the Spec and Plan are not in their context. A reference like "see the Spec" or "check the Plan" breaks self-containedness. Extract and embed the relevant content instead.
- *Under-scoped cross-agent context:* Cross-agent dependencies require comprehensive context regardless of perceived simplicity. Workers do not interact with Memory and have no access to other Workers' work - the only cross-agent context they receive is what you embed in the Task Prompt.
- *Stale dependency classification after Handoff:* When a Worker Handoff is detected, previous-Stage same-agent dependencies must be reclassified as cross-agent. Check the Tracker's cross-agent overrides before constructing dependency context.
- *Shallow dependency chains:* A Task's direct dependency may itself depend on earlier work that established patterns, schemas, or contracts. Trace upstream until an intermediate node fully abstracts what came before.
- *Narrow contract-only thinking:* Contracts are one enforcement artifact, not the whole assurance process. Tasks may also need pre-registration amendments, decision-rule checks, output schemas, smoke/canary runs, provenance review, or human mathematical review.
- *Vague instructions:* "Implement the feature properly" vs "Implement POST /api/users with email validation using express-validator, returning 201 on success."
- *Dispatching before merging dependencies:* If Task B depends on Task A's output and A was on a separate branch, A must be merged before B's branch is created.
- *Assuming base branch name:* Read the base branch from the Tracker's Version Control table for the relevant repository. Do not assume `main` or `master`.
- *Forgetting VC state in Handoff:* Ensure Task rows reflect current branch state before Handoff. Include active branches, worktrees, and pending merges in the Handoff Log.
- *Committing build artifacts:* Do not commit generated files. Create or update `.gitignore` for build directories.

---

**End of Guide**
