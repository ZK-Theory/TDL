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

## Controller Pre-Dispatch Verification Claims

A controller-supplied factual claim that authorizes a broad or cross-cutting
change ("no test relies on X", "nothing else depends on Y") carries the same
verification burden as the edit it licenses.

1. Search the WHOLE relevant surface (every test file that calls the symbol,
   every caller of the function) — not just the nearest or most obvious file.
2. State the exact scope actually checked in the dispatch ("grep of
   `tests/**/*.py` for `pytest.raises` around `main()`"), not an unscoped
   absolute claim.
3. When the surface was not exhaustively verified, prefer scoping the change
   itself (e.g. per-command-group) over an unbounded global edit.

## Resume Brief Construction

When resuming an SDD session at task N, the requirement set for task N is the
UNION of three sources, not the plan alone:

1. The plan's task-N section (the obvious source).
2. The progress ledger's minor-findings roll-up / cross-task decisions.
3. Any RESUME/handoff guide's task-N-specific pointers or carve-outs.

Reconcile all three before writing the brief; fold every carve-out found in the
ledger or resume guide into the brief as a requirement, not a footnote. A brief
built mechanically from the plan text alone silently re-drops exactly the items
a prior session deferred.

## Stalled or Hallucinated Delegation

An implementer subagent given a large, self-contained authoring task can
occasionally imagine it delegated part of the work and end its turn "waiting"
for a background agent that does not exist. A completion message describing
*waiting* rather than reporting status is a stalled agent, not a legitimate
blocked state.

- Resume it via SendMessage to the same agentId with an explicit correction
  ("there is no background agent — do the work yourself in your own context;
  do not spawn subagents"), rather than re-dispatching cold. The agent's
  existing context is already paid for and it typically completes correctly
  once corrected.
- When authoring an implementer prompt, add "do all the work in your own
  context — do not spawn subagents or wait for other agents" to its "Your
  Job" section to pre-empt the failure mode.

## Pre-Delivery Check

- Every task tagged budget-constrained had a verbatim plan artifact and a machine
  check backing the substitution.
- No authored/novel-code task skipped its reviewer subagent.
- The whole-branch final review ran.
- Any dispatch claim licensing a cross-cutting change states the exact search
  scope it was verified against.
- Task N's brief reconciles the plan section, the ledger roll-up, AND any
  resume/handoff guide's carve-outs — not the plan alone.
- No implementer subagent was left "waiting" for a nonexistent delegate
  without being resumed and corrected.

## Example Fixture

| Field | Value |
|---|---|
| Budget state | Under 10% of the weekly token budget remaining |
| Task | Transcribe a file verbatim from the accepted plan |
| Verification | Validator script + byte-diff vs. plan content, plus controller read-review |
| Not eligible | A task requiring new logic not specified verbatim in the plan — reviewer subagent still required |

## Pressure Scenario From This Repo

- Nexus College Phase 0 execution under a hard 9%-weekly-token constraint: the
  controller substituted machine verification + controller read-review for five
  verbatim-transcription tasks, reserving reviewer subagents for the authored/novel-code task and all
  genuinely novel code. All six tasks passed the final whole-branch review with
  zero blocking defects.
- ARS WP4.8 Task 5: the controller authorized a global `try/except` around
  `cli.main()` on the strength of "I confirmed no existing CLI test relies on
  exception propagation" — a claim checked against one test file only.
  `test_replay.py` had three `pytest.raises` around `main()` elsewhere; the
  implementer caught the breakage and rescoped the catch to the affected
  command group mid-task.
- ARS WP4.8 resume at Task 5: the brief was extracted from the plan's Task 5
  section alone, silently dropping a RESUME.md carve-out ("fix the stale
  `cli.py:175` print") that had already fallen through Task 4; recovered only
  when the user pointed back at RESUME.md.
- Nexus College Phase 1: a lesson-authoring implementer stopped after 24 tool
  calls "waiting for the background research agent's completion notification"
  — no such agent existed. SendMessage with an explicit correction resumed it
  in place and it completed correctly.
