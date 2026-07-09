---
name: subagent-driven-development-extras
description: Complement superpowers:subagent-driven-development under a hard token/budget constraint. Use when the per-task reviewer-subagent mandate would exhaust the budget before implementation completes, especially for verbatim-transcription or otherwise machine-checkable tasks.
---

# Subagent-Driven Development Extras

Use alongside superpowers:subagent-driven-development. A budget constraint changes
who verifies a task; it does not authorize skipping verification.

## Budget-Constrained Review Mode

1. Before substituting controller verification for a reviewer subagent, confirm the
   task plan specifies the complete artifact verbatim AND a machine check exists (a
   test, a validator script, or a byte-diff against the plan's verbatim content).
2. If both hold, the controller may verify the task directly — running the machine
   check plus a controller read-review — instead of dispatching a reviewer subagent.
3. Reviewer subagents remain mandatory for any authored or novel code — code the
   plan does not specify verbatim.
4. The whole-branch final review remains mandatory regardless of budget; it is the
   backstop for whatever per-task review was skipped.
5. Record which tasks used budget-constrained verification and why in the task or
   branch report.

## Pre-Delivery Check

- Every task tagged budget-constrained had a verbatim plan artifact and a machine
  check backing the substitution.
- No authored/novel-code task skipped its reviewer subagent.
- The whole-branch final review ran.

## Example Fixture

| Field | Value |
|---|---|
| Budget state | Under 10% of the weekly token budget remaining |
| Task | Transcribe a file verbatim from the accepted plan |
| Verification | Validator script + byte-diff vs. plan content, plus controller read-review |
| Not eligible | A task requiring new logic not specified verbatim in the plan — reviewer subagent still required |

## Pressure Scenario From This Repo

Nexus College Phase 0 execution under a hard 9%-weekly-token constraint: the
controller substituted machine verification + controller read-review for five
verbatim-transcription tasks and one authored task, reserving reviewer subagents
for genuinely novel code. All six tasks passed the final whole-branch review with
zero blocking defects.
