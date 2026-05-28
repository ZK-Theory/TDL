# Worker Research Assurance Workflow Strategy

Date: 2026-05-28

This file preserves the strategic Worker workflow for integrating APM execution,
Superpowers process discipline, and TDL research-assurance practice. It is the
Worker-facing companion to:

`.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`

## Purpose

Workers remain execution-scoped: they act from the Task Prompt, `AGENTS.md`,
dependency context, and accumulated Task Logs, not from the Manager's Spec, Plan,
Tracker, or private reasoning. Research assurance changes what Workers must
verify and report; it does not turn Workers into Managers.

## Recovered Design Context

- APM owns coordination. Workers do not create branches, manage worktrees, push,
  merge, or decide held-task sequencing.
- Superpowers supplies execution discipline: TDD for implementation changes,
  systematic debugging for failures, and verification before completion claims.
- TDL research skills supply domain checks for topology, null models,
  statistics, representation, provenance, paper claims, notation, vault logging,
  and dataset harmonisation.
- Worker reports must now include `Research Assurance Evidence` when the Task
  Prompt includes `Research Assurance Requirements`.
- T1.37 is the first intended live trial of this workflow.

## Worker Step 0: Task Receipt And Workspace Recovery

Use normal APM Worker initiation or task retrieval.

Checklist:

- Confirm the bus identity matches the assigned Worker.
- Confirm the workspace path or worktree path from the Task Prompt.
- Confirm branch state, but do not create, merge, delete, or rebase branches.
- If this is a handoff or recovery, load the specific prior Task Logs named by
  the prompt or handoff.
- Identify whether the Task Prompt includes `Research Assurance Requirements`.

Skills:

- APM Worker initiation/check-task skills.
- `verification-before-completion` only when about to make completion claims.

Output:

```text
Task received
Workspace confirmed
Dependencies loaded
Research assurance block present/absent
Initial execution posture
```

## Worker Step 1: Prompt Triage

Before editing or running expensive computation, classify the prompt.

Checklist:

- Objective and deliverables.
- Validation criteria.
- Workspace and output paths.
- Dependencies and integration files.
- Required commits.
- Required vault/report/log duties.
- Research assurance lanes, if present.

If the prompt references coordination-level artifacts such as Plan, Spec,
Tracker, or Manager-private notes, treat that as a prompt defect and ask for
clarification unless the relevant content is embedded in the prompt.

## Worker Step 2: Skill Selection

Workers choose skills by task type, not by broad curiosity.

Core execution skills:

- `test-driven-development`: implementation changes, bug fixes, behavior changes.
- `systematic-debugging`: failing tests, contradictory output, unexpected
  numerical results, or unclear root causes.
- `verification-before-completion`: before claiming pass, done, fixed, accepted,
  or ready.
- `brainstorming`: only when the User/Manager asks the Worker to explore or
  re-scope.

Avoid:

- `using-git-worktrees` unless the Task Prompt explicitly asks; workspace
  isolation is normally Manager-owned.
- Manager routing skills unless the Worker is being explicitly converted into a
  Manager role.

TDL research skills by lane:

| Lane | Existing skills to consider |
|---|---|
| Topology | `validate-topology`, `wasserstein-audit`, `notation-check` |
| Stochastic / Null Model | `markov-null-design`, `validate-topology`, `tda-experiment` |
| Statistical / Panel | `bhps-wave-crosswalk`; future `statistical-design-audit` |
| Representation | `tda-experiment`; future `representation-freeze-audit` |
| Output / Provenance | `tda-experiment`, `vault-sync`, `commit-log`; future `result-provenance-review` |
| Paper Claim | `paper-draft`, `humanizer`, `notation-check`, `vault-sync`; future `paper-claim-trace` |

## Worker Step 3: Dependency Integration

Follow cross-agent dependency instructions exactly.

Checklist:

- Read named files and artifacts.
- Verify interfaces, schemas, paths, and output assumptions.
- If a dependency artifact is missing or contradicts the prompt, stop before
  building on it.
- For same-agent dependencies, refresh referenced paths rather than relying on
  memory alone.
- For broad exploration, use a subagent only when the prompt allows or the APM
  guide recommends it; verify critical claims before using them.

Research-specific dependency checks:

- Prior result files are not superseded or statistically invalid.
- Caches match the intended seed, B, L, null model, Markov order, and date suffix.
- Frozen representation artifacts are the intended source of embeddings/loadings.
- Vault or CONVENTIONS locks cited by the prompt are actually present.

## Worker Step 4: Execution Planning

Make a small execution plan before changing files or launching computation.

For code tasks:

- Write or identify the smallest relevant test or contract.
- Run the test/contract when practical to establish current behavior.
- Implement narrowly.
- Re-run focused validation before broader validation.

For computation tasks:

- Confirm input paths, output paths, cache paths, seeds, B, L, Markov order, and
  no-overwrite behavior.
- Prefer smoke/canary runs before full runs when the prompt allows.
- Preserve superseded outputs rather than overwriting them.

For writing tasks:

- Identify source result files and decision rules.
- Trace claims to result artifacts.
- Use paper-writing skills for prose, but do not use prose polish to strengthen
  unsupported claims.

## Worker Step 5: Execution

Execute the prompt sequentially and incrementally.

Rules:

- Stay inside the assigned scope.
- Do not weaken research requirements silently.
- Do not replace a missing high-level validation with a weaker check without
  marking the task Partial.
- If code reality conflicts with the prompt's research assurance block, stop and
  report Partial with evidence.
- If a result supports a weaker conclusion than expected, preserve the result and
  report the weaker conclusion; do not tune parameters to chase a desired claim.

## Worker Step 6: Validation

Run all autonomous validation in the Task Prompt.

Validation categories:

- Tests, lint, type checks, or build checks.
- Contract or schema validation.
- Smoke/canary/full computation checks.
- Output existence and no-overwrite checks.
- Result JSON field/provenance checks.
- Vault or CONVENTIONS write checks.
- Paper/notation checks for writing tasks.

Use `systematic-debugging` when:

- A check fails and the cause is unclear.
- Numerical output contradicts expectations.
- A schema passes but a scientific invariant appears wrong.
- Repeated local fixes do not resolve the issue.

Use `verification-before-completion` before:

- saying validation passed
- logging Success
- committing
- telling the User to deliver a report

## Worker Step 7: Research Assurance Evidence

If the Task Prompt included `Research Assurance Requirements`, the Task Log must
include `Research Assurance Evidence`.

Recommended format:

```markdown
## Research Assurance Evidence

### Lane: <Topology | Stochastic / Null Model | Statistical / Panel | Representation | Output / Provenance | Paper Claim>
- Requirement:
- Evidence artifact or command:
- Parameters/seeds/paths verified:
- Result:
- Human-review-only claims:
- Gaps:
```

Evidence must answer:

- What was checked.
- Which command, contract, schema, result file, cache, or code path supports it.
- Which parameters, seeds, null settings, or output paths were verified.
- Which claims remain human-review-only.
- Which gaps remain.

Unresolved required evidence means Partial unless the prompt explicitly scoped the
task to a narrower result.

## Worker Step 8: Commit, Log, And Report

After validation:

- Commit only the task-scope work to the assigned branch.
- Write the Task Log at the provided `log_path`.
- Set `important_findings: true` if the task exposed risks, contradictions,
  superseded outputs, missing assurance artifacts, or possible effects on other
  tasks.
- Set `compatibility_issues: true` if the output conflicts with code, schemas,
  conventions, or downstream expectations.
- Write the Report Bus summary.
- Tell the User which `/apm-5-check-reports` command to run.

Report body should say whether Research Assurance Evidence is complete or whether
gaps remain.

## Worker Step 9: Batch And Handoff Behavior

For batches:

- Execute tasks sequentially.
- Fully validate and log each task before starting the next.
- Stop the batch on Failed status.
- If a task is Partial because research evidence is missing, do not proceed
  unless the prompt explicitly permits continuation after Partial.

For compaction or handoff:

- Mention recovery in the Task Report.
- Preserve exact result paths, commits, logs, and unresolved research gaps.
- Do not rely on chat memory for scientific-risk state; put it in the Task Log.

## Worker Step 10: Rule Corrections

If the User corrects a Worker during execution:

- Comply immediately.
- Record the correction in Important Findings.
- At completion, ask whether it should become a general rule.
- If approved, update `AGENTS.md` and note it in the Task Log.

## T1.37 Trial Expectations

For the next T1.37 Worker report, the Manager should expect Worker evidence for:

- stochastic/null model settings, including null type, Markov order if relevant,
  seeds, B, and L
- statistical formula details, especially p-value denominator and any FDR or
  comparison logic
- representation provenance, including frozen loadings or provisional/frozen
  distinctions
- output/provenance details, including result paths, cache paths, schemas,
  no-overwrite handling, and vault obligations
- paper-claim trace only if the task writes or interprets conclusions

The first trial should reveal which checks need future hooks and which remain
human-review-only.
