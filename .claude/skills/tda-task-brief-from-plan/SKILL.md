---
name: tda-task-brief-from-plan
description: Use when converting a research plan, note, review finding, or conversation into agent-ready TDL work — implementation tickets, compute tasks, or patch tasks for Claude Code or Codex.
---

# TDA Task Brief From Plan

Convert a plan into one or more **vertical** task briefs carrying assurance
lanes, contract requirements, machine-checkable acceptance criteria, and
runtime guidance. Two boundaries: an outcome-contingent, **pre-registered**
run is converted by `pre-reg-to-dispatch` (that skill owns the pre-reg →
Task Prompt path, including amendment detection); and a task that is still
conceptually unresolved needs `tda-domain-modeling` or a design conversation
first — a brief cannot fix an unsettled concept.

## Brief Template

```markdown
# Task Brief: <task-id> <title>

## Target paper / project
P01-A | P01-B | P04 | FIN-01 | infrastructure

## Goal
One concrete outcome.

## Non-goals
What this task must not do.

## Assurance lanes
Topology / Stochastic-Null / Statistical-Panel / Representation /
Output-Provenance / Paper Claim — mark each touched lane.

## Required upstream contracts
- Existing: …
- Needed before implementation: …
- Not applicable because: …

## Inputs
Files, data, result artifacts, notes — by path.

## Expected outputs
Files, JSONs, figures, tests, notes — by path.

## Acceptance criteria
Machine-checkable where possible.

## Validation commands
Commands the agent must run.

## Provenance requirements
Sample stage, result path, manifest, parameters, seeds.

## Runtime constraints
Workers, checkpointing, wall-time estimate, no-overwrite rule.

## Paper-claim constraints
Allowed claims, prohibited claims, target section.

## Suggested skills
Which skills the executing agent should invoke.

## Stop conditions
When the agent must stop and ask or escalate.
```

## Rules

- **Vertical slices only** — one concrete outcome per brief, never a broad
  horizontal refactor.
- **Contract authorship stays upstream.** The brief names the contracts the
  implementer *receives*; a needed-but-missing contract is authored before
  dispatch (`schema-contract-design`), never delegated to the implementing
  agent.
- "Tests pass" alone is never an acceptance criterion for a lane-touching
  task — name the enforcement artifact or record why none applies.
- Long stochastic compute carries the runtime constraints from
  `tda-resource-preflight`: workers ≥ 4, checkpointing, wall-time estimate,
  no-overwrite.
- **Dispatch safety** (mandatory in every brief): bound scope with explicit
  hard stops ("build X only; do NOT proceed to Y/Z"); restate user-decision
  gates as **blocking**, not advisory; forbid toy/synthetic/illustrative
  output in `results/` — that tree is for real, provenance-tracked compute
  only.
- If the brief relies on an inferred property of an external resource
  (a coding rule, a library behaviour, a checkpoint schema), the brief
  includes a verification step — no speculative foundations.

## Completion Checklist

- [ ] Task is vertical; target paper identified.
- [ ] Assurance lanes marked; contract requirement resolved upstream.
- [ ] Inputs and outputs named by path.
- [ ] Acceptance criteria machine-checkable where possible.
- [ ] Validation commands listed.
- [ ] Provenance and runtime constraints specified.
- [ ] Paper-claim constraints and suggested skills included.
- [ ] Dispatch-safety elements present (scope stops, blocking gates,
      results/ rule).
- [ ] Stop conditions included.

## Escalate Or Stop When

- The source plan's foundation is unverified ("this is probably true") —
  insert the verification step or surface a User decision; never dispatch on
  speculation.
- The work is outcome-contingent on a decision rule — that is a
  pre-registration, so route to `pre-reg-to-dispatch`.

## Related Skills

`pre-reg-to-dispatch` (pre-registered runs) · `research-assurance-triage`
(lane classification) · `schema-contract-design` (upstream contract
authoring) · `tda-resource-preflight` · `tda-handoff` (carrying an
unfinished brief across sessions) · any tier-2 specialist skill as a
dispatch target (routing table: the SKILL-INDEX in the authoring tree) ·
`tda-light-task-triage` (low-risk chores that do not need a brief).
