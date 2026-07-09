---
name: tda-paper-dissemination-pack
description: Use only after a TDL paper section or result set is stable — to convert it into public-facing web pages, talks, posters, slide decks, graphical abstracts, or explainer material.
---

# TDA Paper Dissemination Pack

Package **stable** research outputs for public consumption: zktheory.org
pages, talks, posters, graphical abstracts, blog companions. Strictly
downstream of review and verification — dissemination never runs ahead of
the evidence.

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## Do Not Use When

- The result is provisional (PROVISIONAL flags travel with results into
  every derived artifact — a poster of a provisional result is a provisional
  poster nobody will read as provisional).
- Literature sources are unverified.
- Paper claims are still under active review or revision.
- Figures lack regeneration scripts.
- The output would overstate significance — proportionality applies harder
  in public material, not softer.

## Required Inputs

Stable paper draft or section · verified citations · regenerable figures ·
paper target · intended audience · **claims allowed** · **claims prohibited**.
The allowed/prohibited claim lists come from the paper's claim tracing, not
from memory.

## Procedure

1. Confirm stability: which draft version, which result files, any
   PROVISIONAL flags outstanding?
2. Fix the audience and format (web page / talk / poster / abstract /
   explainer).
3. Build the claims budget: what this artifact may assert, at what strength,
   and what it must not touch (e.g. P01-B material never carries applied
   poverty interpretation).
4. Reuse paper figures via their regeneration scripts; public simplifications
   of figures are new figures and get the same provenance treatment.
5. Simplify language without shifting claim strength — "suggests" does not
   become "shows" on a poster.
6. Route the draft artifact through a prose/communication review pass before
   publication; anything on the public web is effectively permanent.

## Self-Test Prompts

- *A talk slide is drafted from a result still flagged PROVISIONAL pending
  the frozen-loadings reruns.* → Expected: refuse or mark the slide
  provisional-and-internal; public material waits for the rerun.
- *A website page rounds p = 0.003 to "conclusive evidence".* → Expected:
  proportionality violation; restate at the statistic's strength.

## Escalate Or Stop When

- Dissemination timing interacts with journal policy (preprint rules,
  embargoes, the P04-after-arXiv sequencing) — User decision.

## Related Skills

`tda-peer-review-panel` + `tda-literature-verification` +
`tda-visualisation-and-diagramming` (all upstream gates) ·
`paper-claim-trace` (the claims budget) · `humanizer` (public prose pass).
