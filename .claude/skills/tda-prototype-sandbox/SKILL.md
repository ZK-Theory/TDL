---
name: tda-prototype-sandbox
description: Use when building a disposable prototype to clarify a TDL design, interface, visualization, CLI, dashboard, or workflow idea without producing research evidence.
metadata:
  version: "1.0.0"
  tier: optional
  lanes: []
  roles:
    - implementer
  runtime: agnostic
---

# TDA Prototype Sandbox

Move fast without contaminating evidence-bearing code. A prototype exists to
answer a design question, then be deleted or explicitly promoted.

## Core Rule

```text
A prototype is not evidence.
A prototype is not a result artifact.
A prototype is not paper-citable.
A prototype cannot write into canonical result directories.
```

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## Use When

- Testing a CLI design, result-browser sketch, or task-state machine.
- Trying a figure layout or dashboard idea.
- Comparing alternative UX/workflow patterns.
- Sketching an analysis flow before committing to a brief.

## Do Not Use When

- Producing paper results or running PH inference for a claim.
- Writing canonical result JSONs or modifying validated pipeline code.
- Creating anything that could be mistaken for an inferential artifact.

## Required Constraints

- Write under `scratch/`, `prototypes/`, or another explicitly disposable
  path — **never** under `results/` (that tree is for real,
  provenance-tracked compute only; a date-stamped synthetic file there is a
  landmine).
- Mark every output exploratory, in the filename or header.
- Do not overwrite canonical artifacts; do not import prototype modules from
  pipeline code.
- Record what question the prototype tested.
- State what promotion to production would require (usually: a task brief,
  a contract, tests, and provenance).

## Output

```text
prototype path · question being tested · what was learned ·
promotion requirements · deletion/retention recommendation
```

## Self-Test Prompts

- *A prototype regime-viewer computed a suspiciously interesting statistic;
  the agent wants to save it to `results/` "for later".* → Expected: refuse;
  re-derive through the pipeline with provenance if it matters.
- *A prototype worked well and the agent starts wiring it into the battery
  script.* → Expected: stop — promotion goes through
  `tda-task-brief-from-plan` and `contract-first-tdd`.

## Related Skills

`tda-task-brief-from-plan` (promotion path) · `contract-first-tdd` ·
`tda-visualisation-and-diagramming` (exploratory figure class) ·
`tda-light-task-triage` (deciding whether the idea deserves a prototype).
