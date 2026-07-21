---
name: tda-statistical-analysis-review
description: Use when reviewing statistical output headed for a paper — permutation tests, Markov memory-ladder results, confidence intervals, effect sizes, model fits, or statistical claims in P01-A/P01-B/P04 — after the numbers exist and before prose depends on them.
metadata:
  version: "1.0.0"
  tier: core
  lanes:
    - statistical-panel
    - stochastic-null
  roles:
    - verifier
  runtime: agnostic
---

# TDA Statistical Analysis Review

The claims-facing statistical review pass. It **orchestrates the lane audits
and owns the reporting-completeness checks**; it does not redo design
validity — `statistical-design-audit` owns the design dimensions
(denominator, formula, exchangeability, clustering, eligibility, FDR).
A purely topological computation with no inferential claim goes to
`validate-topology` / `topology-benchmark-review` instead.

## Review Sequence

1. State the inferential claim, its test statistic, and its target paper
   section.
2. Route the design questions to the owning audits:
   - `statistical-design-audit` — denominator, p-value formula, multiple
     comparisons, bootstrap, estimand, eligibility, clustering, null
     exchangeability, Markov order k.
   - `null-operation-invariance-audit` — does the null operation actually
     perturb the object the statistic is computed on?
   - `panel-estimand-audit` — estimand/eligibility/denominator alignment.
   - `representation-freeze-audit` — frozen loadings, embedding comparability.
3. Reporting completeness (owned here):
   - Both the test statistic AND the p-value are reported — never one alone.
   - Markov order k is stated wherever a Markov null is named.
   - Headline diagram-comparison claims report both W2 and persistence
     landscape L2.
   - Sample counts are cited by reference to `sample_provenance.fitted` with
     the stage named — never transcribed from memory or an upstream stage.
   - The multiple-comparison family is acknowledged wherever a family of
     tests exists.
   - An uncertainty interval is present where applicable.
   - PROVISIONAL flags are carried through — a result flagged pending a fix
     (e.g. frozen loadings) may not be reported as final.
4. Paper-language proportionality: the prose claim is no stronger than the
   statistic supports; negative and weaker results are reported honestly.
5. Contract implications: any machine-checkable finding gets a named contract
   update need.

## Output Format

**PASS / CONCERN / FAIL** per item, with the specific statistic, file, or
passage and the required correction for CONCERN/FAIL. This is a review pass
only — fixes happen in a separate pass.

## Completion Checklist

- [ ] Test statistic and null model (with order k) named.
- [ ] Sample stage named and cited by reference.
- [ ] Design dimensions routed to the owning lane audits.
- [ ] Both-statistics rule (statistic + p; W2 + landscape L2) checked.
- [ ] Multiple-comparison burden checked.
- [ ] PROVISIONAL flags traced into the prose.
- [ ] Paper-claim proportionality checked.
- [ ] Contract update needs identified.

## Escalate Or Stop When

- A reviewed claim depends on a result a lane audit invalidates — the claim
  is blocked, not softened.
- Proportionality cannot be fixed by wording — the analysis itself must
  change, which is a User decision.

## Related Skills

`statistical-design-audit` · `null-operation-invariance-audit` ·
`panel-estimand-audit` · `representation-freeze-audit` ·
`paper-claim-trace` (binding surviving claims to result files) ·
`tda-peer-review-panel` (this skill is its Statistical persona) ·
`tda-statistical-modeling-toolkit` (fitting discipline for baseline and
robustness models under review).
