---
name: tda-scenario-stress-test
description: Use when a TDL decision has multiple plausible branches — paper structure, adding a robustness check or baseline, an acceleration strategy, a methods trade-off — and needs structured risk analysis before it becomes a task brief.
---

# TDA Scenario Stress Test

Stress-test a strategic choice **before** committing to it. This is
pre-decision analysis, upstream of `tda-task-brief-from-plan`; it is not
`adversarial-design-review`, which attacks an existing artifact at a review
gate. Do not use it when the decision is already constrained by a locked
convention or contract — locked means locked, and reopening one is a User
decision with a `[DECISION]` entry, not a scenario exercise.

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## Branches (run all six)

- **Best case** — what does success look like, concretely?
- **Likely case** — the honest median outcome.
- **Worst case** — how does this fail, and what does the failure cost?
- **Reviewer-hostile case** — the strongest objection a referee raises
  (pre-registration, cherry-picking, scope creep, multiplicity).
- **Maintenance-cost case** — scripts, provenance, figures, contracts, and
  reruns this choice commits the programme to.
- **Paper-scope-risk case** — does this leak applied interpretation into
  P01-B methods, or methods machinery into P01-A?

## Procedure

1. State the decision as a single question with the options enumerated.
2. Check first: is any option foreclosed by a locked convention, a contract,
   or a pre-registration? If so, say which and remove it.
3. Run the six branches per surviving option.
4. Weigh the branches; recommend one option with the residual risks named.
5. Convert the recommendation into the input for `tda-task-brief-from-plan`
   (or a User decision point if the branches reveal it is genuinely theirs).

## Output Record

```text
decision question · options (with any foreclosed by locks) ·
six branches per option · recommendation · residual risks ·
next step (task brief / user decision / drop)
```

## Self-Test Prompts

- *"Should P01-B include a conventional trajectory-classification baseline?"*
  → Expected: six branches including the reviewer-hostile
  ("why wasn't this pre-registered?") and paper-scope-risk (applied
  interpretation leaking into P01-B) cases, then a scoped recommendation.
- *"Should we switch the headline metric from W2?"* → Expected: refuse the
  scenario framing — the metric is a locked convention; reopening it is a
  User `[DECISION]`, not a stress test.

## Related Skills

`tda-task-brief-from-plan` (downstream) · `adversarial-design-review`
(artifact review at a gate, not pre-decision) · `tda-research-ideation-lab`
(where the options come from) · `tda-peer-review-panel` (the
reviewer-hostile branch made real).
