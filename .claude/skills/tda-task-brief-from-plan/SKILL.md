---
name: tda-task-brief-from-plan
description: Use when converting a research plan, note, review finding, or conversation into agent-ready TDL work — implementation tickets, compute tasks, or patch tasks for Claude Code or Codex.
metadata:
  version: "1.3.0"
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
One bounded contribution to a named end-to-end capability.
## Execution context
- Workflow system: standalone | apm
- Named end-to-end capability: <observable real production/public outcome>
- Capability state: NOT RUNNABLE | RUNNABLE | PROVEN | INTEGRATED | OWNER-BLOCKED
- Completed production path: <real path so far>
- Exact remaining functional gap: <gap>
- Next production action: <action>
- Supervision phase: certify | deliver
- Lifecycle phase: plan | materialize | implement | review | remediate | integrate
- Context mode: fresh | bounded continuation
- Rotation condition: <observable condition; no estimated token threshold>
- Fork policy: none | <small positive count with reason>
- Required skills: <skill -> purpose>
- Conditional skills: <trigger -> skill>
- External-review owner: Stephen | not applicable
- Final acceptance-review cycle: <integer, normally 1>
- Branch role / integration base: <candidate|review|integration> / <exact ref>
- Merge strategy: <preserve accepted ancestor; no squash unless re-authorized>
- External-review file cap: <integer; CodeRabbit hard limit 100>
- Research-value disposition: <required now | deferred stage | separately elevated>

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
## Task-state manifest
YAML path containing `task_id`, `deliverables`, `blockers`,
`planned_contracts`, rooted `inputs`, trackable `outputs`, independently
resolvable `lanes`, production `registries`, `derived_fields` with exact
preimages/semantics, and schema `required_fields` with authoritative sources
and resolution checks; validate with
`python -m shared.manager_dispatch_check ... --state-manifest <yaml>`. During
warning-first calibration,
retain and disposition every warning rather than presenting it as a pass.
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

- **Vertical contributions only** — one concrete contribution per brief,
  never a broad horizontal refactor. The named capability remains the campaign
  deliverable across briefs, slices, and PRs.
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
- **Choose context deliberately.** Load only skills required by the work or a
  named assurance trigger. Independent reviewers start without parent history.
  For implementers, choose fresh context or a bounded continuation according to
  which carries the required evidence with less replay, and record why.
- **Canonical transition closure** is mandatory before implementation of
  canonical state. Resolve every proposed mutation to an accepted writer,
  exact command/event/schema identity, reducer/projection and stream owner,
  idempotency/concurrency rule, and schema-version disposition. A missing row
  requires a separately reviewed authority addendum; the implementer must not
  invent it.
- **Research-value closure** precedes blocking non-research assurance. Record
  the protected research asset, credible failure, insufficiency of current
  controls, cheapest adequate control, evidence stage, and bounded effort/stop.
  Runtime-only evidence defaults to runtime integration; general hardening may
  not consume more than 10% without Stephen's explicit elevation.
- **Integration is a separate lifecycle phase.** Declare management, candidate,
  review, and integration branch roles and preserve an exact accepted candidate
  as a reachable ancestor. Before external review, compute the merge-base file
  count. CodeRabbit cannot review more than 100 files; target at most 90 and
  split dependency-safely when the hard limit would be exceeded.
- Ordinary defects or missing dependencies required by the capability stay in
  the campaign during construction. A second **final acceptance** remediation
  is a stop for finding rescope and owner ruling, followed by a fresh task if
  authorized; it is not a bounded continuation and does not make the capability
  complete.
- Stephen triggers and monitors CodeRabbit unless he explicitly delegates that
  operation in the current task. Do not place review polling in the brief.

- Claims that a deliverable is absent, a blocker remains live, a planned
  contract is ready, an input resolves, or an output is trackable belong in
  the task-state manifest and are rechecked immediately before dispatch.
- Parallel dispatch is valid only when the resolved workspace is the worktree
  that currently owns the required branch. A detached checkout at the same
  commit is not an alternative owner and must not receive the task.

## Completion Checklist

- [ ] Task is a vertical contribution; target paper and named end-to-end
      capability identified.
- [ ] Capability state, completed production path, exact remaining functional
      gap, and next production action are recorded.
- [ ] Workflow system, lifecycle/supervision phase, context/fork policy,
      required skills, external-review owner, and cycle limit recorded.
- [ ] Assurance lanes marked; contract requirement resolved upstream.
- [ ] Canonical-transition closure recorded for every canonical mutation, or
      the task stops before implementation.
- [ ] Blocking non-research assurance has a proportional research-value and
      lifecycle-stage disposition.
- [ ] Branch roles, integration base/strategy, external-review file cap, and
      second final-acceptance-cycle stop are explicit.
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

- The proposed PR exceeds the external reviewer's file cap and no
  dependency-safe stack has been declared.

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
