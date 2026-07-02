---
name: tda-light-task-triage
description: Use when sorting low-risk TDL-adjacent tasks — miscellaneous ideas, GitHub issues, vault cleanup, website tweaks, study tasks, small infrastructure chores — that do not touch research assurance lanes or result-bearing artifacts.
---

# TDA Light Task Triage

A lightweight sorter for the peripheral work that accumulates around the
research programme. It exists so that small chores do not each demand a full
task brief — and so that anything non-trivial gets routed to one instead of
being quietly under-specified.

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## States

`discard` · `defer` · `backlog` · `quick-fix` · `convert-to-task-brief` ·
`convert-to-research-question` · `convert-to-learning-scaffold`

A `quick-fix` is reversible, scoped to minutes, and touches nothing on the
escalation list below. Everything else gets a state and a one-line reason.

## Escalate Immediately (this skill may not process the task) If It Touches

- topology, null models, statistics, or representation
- output/provenance, result JSONs, or sample counts
- paper claims or paper-scope boundaries
- contracts or enforcement hooks

Those route to `tda-task-brief-from-plan` (or `pre-reg-to-dispatch` for
outcome-contingent runs) via research-assurance triage. When in doubt about
whether a task touches a lane, it touches a lane.

## Procedure

1. Collect the loose items (inbox, issue list, conversation residue).
2. Apply the escalation screen first — lane-touching items leave the queue
   immediately.
3. Assign each survivor a state and a one-line rationale.
4. `quick-fix` items: do them now, or bundle into one housekeeping pass.
5. `backlog`/`defer` items: record where they live (issue, vault note) so
   they are findable — an untracked deferral is a discard in disguise.
6. Conversions: hand to the target skill with the one-line context attached.

## Self-Test Prompts

- *"Quick one — bump the FDR q threshold in the battery config."* →
  Expected: escalate; statistics lane, not a chore, regardless of size.
- *"Rename a variable in a viz helper and fix a typo in the README."* →
  Expected: `quick-fix`, bundled housekeeping.

## Related Skills

`tda-task-brief-from-plan` (everything escalated or converted) ·
`research-assurance-triage` (the lane screen) · `tda-learning-scaffold` /
`tda-research-ideation-lab` (conversion targets) · `tda-prototype-sandbox`
(when triage output is "try it disposably first").
