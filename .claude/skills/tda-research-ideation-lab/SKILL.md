---
name: tda-research-ideation-lab
description: Use for explicitly speculative TDL idea generation — hypothesis exploration, alternative nulls, robustness-check candidates, future-paper branching, cross-project links — before any verification or implementation.
metadata:
  version: "1.0.0"
  tier: optional
  lanes: []
  roles:
    - orchestrator
    - manager
  runtime: agnostic
---

# TDA Research Ideation Lab

A labelled sandbox for generating and comparing research ideas. Everything
produced here is **speculative by construction** and stays outside the claim
pipeline until verified. The lab widens the funnel; the assurance path narrows
it.

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## Output Categories

Candidate hypothesis · possible method · possible paper section · possible
negative control · possible external dataset · possible reviewer objection ·
possible future paper.

## Mandatory Labels

Every idea carries every applicable label:

`speculative` · `literature-needed` · `data-needed` · `contract-needed` ·
`implementation-needed` · `paper-scope-risk`

## Forbidden Behaviour

- Do not present generated ideas as findings.
- Do not cite unverified literature (leads route to
  `tda-literature-verification`).
- Do not create implementation tasks directly — ideas that survive go through
  `tda-task-brief-from-plan` (or the Discovery Harness: `scout-review` →
  `assay` → `spike` for programme-level candidates).
- Do not attach an idea to a paper section as if scoped — paper boundaries
  (P01-A applied vs P01-B methods) apply to speculation too.

## Output Record

```json
{
  "idea": "",
  "status": "speculative",
  "paper_target": null,
  "evidence_needed": [],
  "literature_needed": [],
  "data_needed": [],
  "method_risks": [],
  "assurance_lanes": [],
  "next_skill": "tda-literature-verification"
}
```

## Self-Test Prompts

- *An ideation pass produces a plausible mechanism story for regime escape;
  the agent drafts it into the P01-A discussion.* → Expected: refuse — it is
  `speculative` + `literature-needed`; no prose until the evidence chain
  exists.
- *A generated hypothesis needs "just a quick run" to check.* → Expected:
  route to `assay`/`spike` or a task brief; the lab does not run compute.

## Related Skills

`assay` / `spike` / `scout-review` (the Discovery Harness — programme-level
idea triage) · `tda-scenario-stress-test` (stress-testing a chosen direction)
· `tda-task-brief-from-plan` · `tda-literature-verification`.
