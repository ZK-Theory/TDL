---
name: statistical-design-audit
description: Use when a TDL task involves p-values, permutation/bootstrap inference, denominators, FDR/multiple comparisons, estimands, eligibility rules, GLMM/Firth/svyglm, MICE, IPW, or Manski bounds — to check the statistical design is valid before trusting the numbers.
---

# Statistical Design Audit

Use this for the Statistical / Panel assurance lane. The canonical failure mode
here is a result that passes every software test while the inference is wrong: a
mis-specified denominator, an unstated estimand, a permutation null that is not
exchangeable, or multiple comparisons with no correction. Audit the design, not
just the code path.

For the catalogue of recurring issues with *how to identify* and *what to require*
for each, read `references/common-statistical-issues.md`.

## Audit Dimensions

Check each dimension that the task touches:

1. **Denominator correctness.** The quantity dividing is the right one. For Monte
   Carlo permutation p-values the denominator is the number of null draws used for
   the p-value, `n = min(B, total_pairs)` — not a diagnostic cap.
2. **p-value formula.** Two-sided Monte Carlo p-value uses the bias-corrected
   `p = (r + 1) / (n + 1)`; minimum achievable p is `1 / (n + 1)`; p is monotone
   non-decreasing in r.
3. **Multiple comparisons.** FDR (Benjamini-Hochberg) is applied and the
   correction family is defined explicitly — which tests are in the family, and why.
4. **Bootstrap.** n=1000 (or stated otherwise), seed recorded, resampling unit
   correct (cluster/individual, not measurement).
5. **Estimand stated.** The target quantity (ATE/ATT, escape probability,
   transition rate, ICC) is written down and unchanged across reruns.
6. **Eligibility / sample restriction.** Inclusion rules match the estimand and
   denominator; no implicit conditioning that changes what is being estimated.
7. **Clustering / ICC.** Repeated observations on the same unit are handled
   (cluster-robust SE, mixed model, or cluster bootstrap), not treated as
   independent.
8. **Null exchangeability.** The permutation/shuffle preserves the structure the
   null is meant to hold fixed and breaks only the association under test.
9. **Markov order k.** Any Markov null states *k* explicitly — "Markov null" alone
   is ambiguous.

## Output Format

Report **PASS / CONCERN / FAIL** per audited dimension, with the specific
statistic or code location and, for CONCERN/FAIL, the required fix. Distinguish
machine-checkable items (denominator, formula — bind to a contract) from
human-review-only judgments (estimand appropriateness, exchangeability rationale).

## Escalate Or Stop When

- A p-value denominator or formula cannot be reconciled with the governing design.
- The estimand changed between runs but the task is framed as a routine rerun.
- A permutation null is invariant to the operation it is supposed to test.

## Pressure Scenarios From This Repo

- T1.36 used a diagnostic null-null cap as the p-value denominator; all software
  tests passed but the Monte Carlo formula was wrong.
- A panel rerun framed as routine silently changed the estimand while keeping the
  same eligibility rule.

## Related Skills & Contracts

- Use `markov-null-design` for Markov-memory ladder design and `panel-estimand-audit`
  for estimand/eligibility alignment.
- Enforcing contracts: `monte-carlo-permutation-p-value`, `icc-cluster-bootstrap`,
  `rubin-pooling`, `normalised-ipw-trimming`, `mice-convergence-rule`,
  `svyglm-cluster-robust-se`.
