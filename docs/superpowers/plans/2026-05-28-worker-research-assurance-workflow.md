# Worker Research Assurance Workflow Strategy

> **For agentic workers:** This is a strategic workflow reference, not a single implementation task. Use it with the incremental plan in `2026-05-28-apm-research-assurance-integration.md`.

**Goal:** Preserve the Worker-side process for executing APM tasks while carrying Superpowers discipline and TDL research-assurance evidence through validation, logging, and reporting.

**Architecture:** Workers remain scoped to the Task Prompt, `AGENTS.md`, dependency context, and Task Logs. Research assurance changes the evidence Workers must validate and report; it does not give Workers Manager authority over sequencing, worktrees, branches, or acceptance.

**Tech Stack:** APM Worker guides, Task Bus/Report Bus, Task Logs, project-local Codex skills, Superpowers execution/debugging skills, YAML contracts, JSON schemas, Python validation commands, result files, caches, and vault entries.

---

## Recovery Note

`docs/` is ignored in this repository. The durable recovery copy is:

`.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`

## Strategic Workflow

### Worker Step 0: Task Receipt And Workspace Recovery

- Confirm bus identity and assigned workspace.
- Confirm branch/worktree state, but do not create, merge, delete, or rebase.
- Load named handoff or dependency logs.
- Identify whether `Research Assurance Requirements` are present.

### Worker Step 1: Prompt Triage

Classify objective, deliverables, validation criteria, dependencies, output paths,
commit duties, vault duties, and research lanes. If the prompt says "see
Plan/Spec" instead of embedding required content, stop for clarification.

### Worker Step 2: Skill Selection

Core execution skills:

- `test-driven-development` for implementation or behavior changes
- `systematic-debugging` for failing or contradictory behavior
- `verification-before-completion` before pass/done/fixed/ready claims
- `brainstorming` only when explicitly asked to explore or re-scope

Research skills by lane:

| Lane | Existing skills |
|---|---|
| Topology | `validate-topology`, `wasserstein-audit`, `notation-check` |
| Stochastic / Null Model | `markov-null-design`, `validate-topology`, `tda-experiment` |
| Statistical / Panel | `bhps-wave-crosswalk`; future `statistical-design-audit` |
| Representation | `tda-experiment`; future `representation-freeze-audit` |
| Output / Provenance | `tda-experiment`, `vault-sync`, `commit-log`; future `result-provenance-review` |
| Paper Claim | `paper-draft`, `humanizer`, `notation-check`, `vault-sync`; future `paper-claim-trace` |

### Worker Step 3: Dependency Integration

- Read named artifacts.
- Verify interfaces, schemas, paths, and assumptions.
- Stop on missing or contradictory dependencies.
- Confirm prior results are not superseded or statistically invalid.
- Confirm caches match seed, B, L, null model, Markov order, and date suffix.

### Worker Step 4: Execution Planning

For code, identify or write the smallest relevant test/contract. For computation,
confirm inputs, outputs, caches, seeds, B, L, no-overwrite behavior, and smoke
strategy. For writing, trace claims to result files and decision rules.

### Worker Step 5: Execution

Execute incrementally inside assigned scope. Do not silently weaken requirements.
If code reality conflicts with the research assurance block, report Partial. If
results support a weaker conclusion than expected, preserve and report the weaker
conclusion.

### Worker Step 6: Validation

Run autonomous validation: tests, contracts, schemas, smoke/full computations,
output checks, provenance checks, vault checks, and paper/notation checks. Use
`systematic-debugging` for unclear failures or numerical contradictions. Use
`verification-before-completion` before completion claims.

### Worker Step 7: Research Assurance Evidence

When required, Task Logs include:

```markdown
## Research Assurance Evidence

### Lane: <lane>
- Requirement:
- Evidence artifact or command:
- Parameters/seeds/paths verified:
- Result:
- Human-review-only claims:
- Gaps:
```

Unresolved required evidence means Partial unless explicitly scoped otherwise.

### Worker Step 8: Commit, Log, And Report

Commit task-scope work only. Write the Task Log and Report Bus summary. Set
`important_findings: true` for research risks, contradictions, superseded
outputs, or missing assurance artifacts. State whether Research Assurance
Evidence is complete or has gaps.

### Worker Step 9: Batch And Handoff Behavior

Log each batch task before starting the next. Stop on Failed status. Preserve
exact result paths, commits, logs, and unresolved research gaps during recovery
or handoff.

### Worker Step 10: Rule Corrections

Comply with User corrections immediately, record them in Important Findings, and
ask at completion whether they should become general rules.

## T1.37 Trial Expectations

The next T1.37 Worker report should carry evidence for stochastic/null settings,
statistical formula details, representation provenance, output/cache provenance,
schema/no-overwrite behavior, vault obligations, and paper-claim trace if
conclusions are written.
