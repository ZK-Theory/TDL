# APM Research Assurance Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate APM coordination, Superpowers process discipline, and TDL research-assurance checks so mathematical research tasks preserve explicit evidence through dispatch, execution, review, and later hook generation.

**Architecture:** APM remains the coordination spine: Managers dispatch and review, Workers execute and report, and the bus/log artifacts preserve state. Superpowers supplies process discipline and durable plans. TDL project-local skills and hooks supply research validity checks for topology, null models, statistics, representation, provenance, and paper claims.

**Tech Stack:** Markdown APM guides, Codex project-local skills, APM bus/log markdown, YAML contracts, JSON schemas, Python validation commands through `uv run`, and existing repository hooks.

---

## File Structure

- `CLAUDE.md`: Repository-level APM runtime rules. Records when research assurance triage is mandatory.
- `.codex/apm-guides/task-assignment.md`: Manager dispatch guidance. Adds research-assurance lanes and Task Prompt extraction requirements.
- `.codex/apm-guides/task-review.md`: Manager acceptance guidance. Adds research-assurance review requirements before accepting Success.
- `.codex/apm-guides/task-execution.md`: Worker execution guidance. Adds how Workers handle Research Assurance Requirements during validation.
- `.codex/apm-guides/task-logging.md`: Worker logging/reporting guidance. Adds the Research Assurance Evidence log section.
- `.agents/skills/research-assurance-triage/SKILL.md`: Project-local skill that defines the assurance lanes, Manager checklist, Worker evidence expectations, and stop conditions.
- `docs/superpowers/plans/2026-05-28-apm-research-assurance-integration.md`: This durable incremental plan.
- `.apm/memory/plans/2026-05-28-apm-research-assurance-integration.md`: APM-memory recovery anchor, because `docs/` is gitignored in this repo.
- `.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`: Durable strategic Manager workflow target.
- `docs/superpowers/plans/2026-05-28-manager-research-assurance-workflow.md`: Readable local mirror of the strategic workflow.
- `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`: Durable strategic Worker workflow target.
- `docs/superpowers/plans/2026-05-28-worker-research-assurance-workflow.md`: Readable local mirror of the Worker workflow.
- `.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`: Durable independent TDL skillset design target.
- `docs/superpowers/plans/2026-05-28-tdl-research-skillset-design.md`: Readable local mirror of the skillset design.

## Current Status

> **2026-06-02 update (Manager 6):** The User lifted the T1.37-trial gate
> ("we do not need to postpone anything") and the full research-assurance layer
> was built directly. Done and committed on `pipe/research-assurance-implementation`:
> dual-tree skill sync (`tools/sync_agent_skills.py`) + `research-assurance-triage`
> ported into `.claude/skills/`; the RA workflow sections ported into the four
> `.claude/apm-guides/`; all 5 Layer-1 and 6 Layer-2 skills authored and synced to
> both trees; Layer-3 enforcement (`tools/apm_task_prompt_check.py`,
> `.claude/hooks/results-no-overwrite.sh`, and the `null-operation-changes-ph-input`
> + `markov-order-provenance` contracts, both `pending:true`). Task 4's hook
> backlog is therefore satisfied directly rather than driven by T1.37 friction;
> Task 3 (T1.37 trial) was superseded. Remaining: transition the two pending
> contracts out of `pending` once their binding tests land.

- Manager dispatch/review integration is in place.
- The first project-local research assurance skill exists.
- Worker evidence reporting is in place as the smallest matching workflow change.
- Hook generation remains intentionally downstream of the T1.37 trial so the hook backlog is driven by real review friction.
- The full strategic Manager workflow is preserved separately from this early implementation checklist.
- Matching Worker workflow and independent TDL skillset design strategies are now preserved separately too.

### Task 1: Manager Research Assurance Baseline

**Files:**
- Modified: `CLAUDE.md`
- Modified: `.codex/apm-guides/task-assignment.md`
- Modified: `.codex/apm-guides/task-review.md`
- Created: `.agents/skills/research-assurance-triage/SKILL.md`

- [x] **Step 1: Add dispatch-time research assurance triage**

Add a Manager dispatch requirement that classifies touched assurance lanes and embeds machine-checkable and human-review-only requirements in the Task Prompt.

- [x] **Step 2: Add review-time research assurance checks**

Add Manager review checks for parameters, seeds, null model, p-value formula, provenance, output schemas, vault obligations, and paper-facing claims.

- [x] **Step 3: Add repository-level APM rule**

Add a short rule to `CLAUDE.md` stating that software tests alone are insufficient for tasks touching mathematical, statistical, topological, representation, output-provenance, or paper-claim logic.

- [x] **Step 4: Verify the baseline**

Run:

```powershell
git diff --check -- CLAUDE.md .codex/apm-guides/task-assignment.md .codex/apm-guides/task-review.md
```

Expected: exit code 0, allowing line-ending warnings only.

### Task 2: Worker Research Assurance Evidence Workflow

**Files:**
- Modify: `.codex/apm-guides/task-execution.md`
- Modify: `.codex/apm-guides/task-logging.md`
- Modify: `.agents/skills/research-assurance-triage/SKILL.md`

- [x] **Step 1: Add Worker validation guidance**

In `.codex/apm-guides/task-execution.md`, state that when a Task Prompt includes `Research Assurance Requirements`, Worker validation must produce lane-by-lane evidence rather than only running software tests.

- [x] **Step 2: Add Worker log evidence template**

In `.codex/apm-guides/task-logging.md`, add an optional `Research Assurance Evidence` section to Task Logs and require it when the Task Prompt includes `Research Assurance Requirements`.

- [x] **Step 3: Extend the project-local skill**

In `.agents/skills/research-assurance-triage/SKILL.md`, add Worker evidence expectations so Managers and future Workers share the same return format.

- [x] **Step 4: Verify the Worker workflow docs**

Run:

```powershell
Select-String -Path '.codex/apm-guides/task-execution.md','.codex/apm-guides/task-logging.md','.agents/skills/research-assurance-triage/SKILL.md' -Pattern 'Research Assurance Evidence','Research Assurance Requirements'
git diff --check -- .codex/apm-guides/task-execution.md .codex/apm-guides/task-logging.md .agents/skills/research-assurance-triage/SKILL.md docs/superpowers/plans/2026-05-28-apm-research-assurance-integration.md
```

Expected: `Select-String` finds both phrases in the Worker-facing docs and skill; `git diff --check` exits 0, allowing line-ending warnings only.

### Task 3: T1.37 Trial

**Files:**
- Read: `.apm/bus/<worker>/report.md`
- Read: `.apm/memory/stage-<NN>/task-<NN>-<MM>.log.md`
- Update if needed: `.apm/memory/handoffs/manager/handoff-03.log.md`
- Update if needed: this plan file

- [ ] **Step 1: Review the next T1.37 Worker report**

Use `/apm-5-check-reports <agent-id>` when the Worker reports back. Read the Task Report and Task Log.

- [ ] **Step 2: Apply the Manager review checklist**

Check whether the Worker supplied evidence for the lanes relevant to T1.37: stochastic/null model, statistical, representation, output/provenance, and paper claim if result interpretation is included.

- [ ] **Step 3: Classify gaps**

Record each gap as one of:

- missing Worker evidence
- unclear Manager dispatch requirement
- missing contract/schema
- missing hook
- human-review-only item needing explicit acceptance
- pre-registration or decision-rule issue

- [ ] **Step 4: Decide acceptance or follow-up**

Accept Success only if the objective, validation criteria, and research-assurance requirements are all satisfied. Otherwise issue a follow-up prompt that asks for the specific missing evidence rather than broad rework.

### Task 4: Post-T1.37 Hook Backlog

**Files:**
- Update: this plan file
- Update if needed: `.apm/memory/handoffs/manager/handoff-03.log.md`
- Create later: hook or contract files chosen from the T1.37 gap list

- [ ] **Step 1: Convert repeated review gaps into hook candidates**

After T1.37 review, list only gaps that are recurring, expensive to check manually, or likely to affect paper claims.

- [ ] **Step 2: Prioritize first hook candidates**

Use this priority order unless the T1.37 evidence suggests a stronger need:

- p-value denominator and Monte Carlo formula checks
- explicit Markov order, seed, B, L, and null-parameter provenance
- JSON schema completeness for comparison and paper tables
- no-overwrite and distinct cache/result path checks
- frozen/provisional representation comparability checks
- topology invariants for null operations that otherwise leave PH unchanged

- [ ] **Step 3: Dispatch hook work through APM**

Create focused APM tasks for hook or contract generation. Each task must have its own Research Assurance Requirements block and must not bundle unrelated checks.

### Task 5: Plan Maintenance

**Files:**
- Update: this plan file

- [ ] **Step 1: Mark completed workflow tasks**

When a task in this plan has been implemented and verified, change its checkboxes from `[ ]` to `[x]` in this file.

- [ ] **Step 2: Preserve compact handoff state**

When context compaction risk is high, summarize current status into the active Manager handoff and reference this plan path.

- [ ] **Step 3: Keep hooks downstream of evidence**

Do not add new hook-generation work ahead of T1.37 review unless the user explicitly asks for a specific hook or a failing validation exposes an immediate need.
