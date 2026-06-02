# APM Research Assurance Integration Plan

Date: 2026-05-28

This is the APM-memory recovery anchor for the APM + Superpowers + TDL
research-assurance integration. A fuller Superpowers-style working plan also
exists locally at:

`docs/superpowers/plans/2026-05-28-apm-research-assurance-integration.md`

Note: `docs/` is ignored by this repo's `.gitignore`, so this APM memory file is
the durable path future Manager sessions should check first.

The broader strategic Manager workflow is preserved at:

`.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`

The matching Worker workflow and skillset design strategies are preserved at:

- `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`
- `.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`

## Current State

> **2026-06-02 update (Manager 6):** The User lifted the T1.37-trial gate and the
> full research-assurance layer was built directly on
> `pipe/research-assurance-implementation`: dual-tree skill sync
> (`tools/sync_agent_skills.py`) + `research-assurance-triage` ported into
> `.claude/skills/`; the RA workflow sections ported into the four
> `.claude/apm-guides/`; all 5 Layer-1 and 6 Layer-2 skills authored and synced to
> both trees; Layer-3 enforcement (`tools/apm_task_prompt_check.py`,
> `.claude/hooks/results-no-overwrite.sh`, and the `null-operation-changes-ph-input`
> + `markov-order-provenance` contracts, both `pending:true`). The hook backlog is
> satisfied directly; the T1.37 trial was superseded. Remaining: transition the two
> pending contracts out of `pending` once their binding tests land.

- Manager dispatch guidance now requires research assurance triage for tasks
  touching mathematical, statistical, topological, representation,
  output-provenance, or paper-claim logic.
- Manager review guidance now treats software tests as insufficient when
  research-assurance requirements are in scope.
- The project-local skill `.agents/skills/research-assurance-triage/SKILL.md`
  defines assurance lanes, Manager dispatch/review checklists, Worker evidence
  expectations, and stop conditions.
- Worker execution/logging guidance now requires `Research Assurance Evidence`
  when a Task Prompt includes `Research Assurance Requirements`.

## Integration Architecture

- APM remains the coordination spine: Manager dispatches and reviews, Worker
  executes and reports, and bus/log artifacts preserve state.
- Superpowers supplies process discipline and durable implementation plans.
- TDL project-local skills, contracts, schemas, and hooks supply
  research-validity checks.
- Hooks are downstream of evidence: do not build a broad hook suite before the
  T1.37 trial identifies which checks are recurring and expensive to review
  manually.

## Next Incremental Step

Use the new workflow on the next T1.37 Worker report.

During Manager review, check whether the Worker supplied lane-by-lane evidence
for the relevant T1.37 lanes:

- Stochastic / Null Model
- Statistical / Panel
- Representation
- Output / Provenance
- Paper Claim, if result interpretation is included

Accept Success only if the objective, validation criteria, and research
assurance requirements are all satisfied. If evidence is missing, issue a
targeted follow-up prompt for the missing evidence rather than broad rework.

## Hook Backlog Gate

After T1.37 review, classify gaps as:

- missing Worker evidence
- unclear Manager dispatch requirement
- missing contract/schema
- missing hook
- human-review-only item needing explicit acceptance
- pre-registration or decision-rule issue

Prioritize hook candidates in this order unless T1.37 evidence points elsewhere:

- p-value denominator and Monte Carlo formula checks
- explicit Markov order, seed, B, L, and null-parameter provenance
- JSON schema completeness for comparison and paper tables
- no-overwrite and distinct cache/result path checks
- frozen/provisional representation comparability checks
- topology invariants for null operations that otherwise leave PH unchanged

## Files To Inspect

- `CLAUDE.md`
- `.codex/apm-guides/task-assignment.md`
- `.codex/apm-guides/task-review.md`
- `.codex/apm-guides/task-execution.md`
- `.codex/apm-guides/task-logging.md`
- `.agents/skills/research-assurance-triage/SKILL.md`
- `docs/superpowers/plans/2026-05-28-apm-research-assurance-integration.md`
- `.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`
- `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`
- `.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`
