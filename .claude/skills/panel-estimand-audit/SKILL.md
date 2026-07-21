---
name: panel-estimand-audit
description: Use when a panel/longitudinal analysis defines or changes an estimand — ATE/ATT, escape probability, transition rate, ICC — to confirm the estimand is stated, stable across reruns, and aligned with the eligibility rule and denominator.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - statistical-panel
  roles:
    - verifier
  runtime: agnostic
---

# Panel Estimand Audit

Use this for the Statistical / Panel lane. The failure mode is silent estimand
drift: a rerun framed as routine quietly changes what is being estimated, so the
new number is not comparable to the old one even though both pass their tests.

## Core Check

1. **Estimand stated.** The target quantity is written down explicitly (ATE/ATT,
   escape probability, transition rate, ICC), not left implicit in the code.
2. **Stable across reruns.** The estimand is unchanged from the prior run; if it
   must change, a pre-registration amendment is required (see `pre-reg-to-dispatch`).
3. **Eligibility aligns.** The inclusion/eligibility rule matches the estimand —
   no conditioning that quietly redefines the population.
4. **Denominator aligns.** The denominator is the population the estimand is
   defined over, not a convenience count.
5. **Weighting/clustering consistent.** IPW/MICE/cluster handling matches the
   estimand's identifying assumptions.

## Output Format

Estimand statement + **ALIGNED / DRIFTED / UNDERSPECIFIED**, naming any
mismatch between estimand, eligibility, and denominator.

## Pressure Scenario

A panel rerun framed as routine changed the estimand while keeping the same
eligibility rule, producing a number not comparable to the prior result.

## Related Skills & Contracts

- Pairs with `statistical-design-audit` and `pre-reg-to-dispatch`.
- Enforcing contracts: `normalised-ipw-trimming`, `svyglm-cluster-robust-se`,
  `rubin-pooling`, `mice-convergence-rule`.
