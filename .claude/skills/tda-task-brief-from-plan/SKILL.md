---
name: tda-task-brief-from-plan
description: Use when converting a research plan, note, review finding, or conversation into agent-ready TDL work — implementation tickets, compute tasks, or patch tasks for Claude Code or Codex.
metadata:
  version: "1.0.0"
  tier: core
  lanes: []
  roles:
    - manager
    - orchestrator
  runtime: agnostic
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

## Execution context
- Workflow system: standalone | apm
- Supervision phase: certify | deliver
- Lifecycle phase: plan | materialize | implement | review | remediate | integrate
- Context mode: fresh | bounded continuation
- Context budget: <tokens or observable rotation condition>
- Fork policy: none | <small positive count with reason>
- Primary skills: <maximum two>
- Conditional skills: <trigger -> skill>
- External-review owner: Stephen | not applicable
- Author-review cycle: <integer, normally 1>

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
  `tda-resource-preflight`: preflight-selected optimal worker count,
  checkpointing, wall-time budget, no-overwrite.
- **Dispatch safety** (mandatory in every brief): bound scope with explicit
  hard stops ("build X only; do NOT proceed to Y/Z"); restate user-decision
  gates as **blocking**, not advisory; forbid toy/synthetic/illustrative
  output in `results/` — that tree is for real, provenance-tracked compute
  only.
- If the brief relies on an inferred property of an external resource
  (a coding rule, a library behaviour, a checkpoint schema), the brief
  includes a verification step — no speculative foundations.

- **Workflow identity comes first.** A standalone brief must not route through
  APM skills, `.apm` campaign state, the APM Memory Bank, or APM guides/checkers.
  Use `tda-large-workflow-supervision` for large standalone campaigns.
- **Budget context deliberately.** Use at most two primary skills and make
  secondary skills conditional on a named artifact or assurance trigger. A
  self-contained implementer or independent reviewer starts without parent
  conversation history; any bounded continuation records why it is needed.
- **Canonical transition closure** is mandatory before implementation of
  canonical state. Resolve every proposed mutation to an accepted writer,
  exact command/event/schema identity, reducer/projection and stream owner,
  idempotency/concurrency rule, and schema-version disposition. A missing row
  requires a separately reviewed authority addendum; the implementer must not
  invent it.
- Stephen triggers and monitors CodeRabbit unless he explicitly delegates that
  operation in the current task. Do not place review polling in the brief.

## Completion Checklist

- [ ] Task is vertical; target paper identified.
- [ ] Workflow system, lifecycle/supervision phase, context/fork budget, skill
      budget, external-review owner, and cycle limit recorded.
- [ ] Assurance lanes marked; contract requirement resolved upstream.
- [ ] Canonical-transition closure recorded for every canonical mutation, or
      the task stops before implementation.
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
`tda-light-task-triage` (low-risk chores that do not need a brief) and
`tda-large-workflow-supervision` (standalone multi-stage supervision).

## Assurance-lane disposition

For every assurance lane named or implied by a plan, record an explicit disposition: required now, deferred with owner and gate, not applicable with rationale, or prohibited only for explicitly out-of-scope lanes with an authorized rationale. Bind each required lane to its authority source, producer, evidence, acceptance condition, and failure state; do not treat aggregate coverage prose as per-lane closure.
