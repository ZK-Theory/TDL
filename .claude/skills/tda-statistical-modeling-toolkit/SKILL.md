---
name: tda-statistical-modeling-toolkit
description: Use when fitting or reviewing non-topological statistical models in TDL — GLMs, OLS/logit/probit, survival models, clustered models, bootstrap summaries, Bayesian robustness checks, simulation-based sensitivity checks, or power analysis — as baselines, robustness checks, or empirical context.
---

# TDA Statistical Modeling Toolkit

Support the TDA argument with conventional statistical modelling — baselines,
robustness checks, empirical context, uncertainty estimation, reviewer-facing
clarification. This skill does not replace PH computation, and it does not own
design validity: `statistical-design-audit` owns denominators, formulas,
exchangeability, and FDR; this skill owns model specification and fitting
discipline.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Procedure

1. Identify the paper target: P01-A, P01-B, P04, FIN-01, or later.
2. State the statistical question in one sentence.
3. Classify the model: confirmatory, exploratory, robustness, baseline, or
   diagnostic. The classification bounds the language its results may use.
4. Identify the sample stage and its provenance source — counts come from a
   result JSON's `sample_provenance` block by reference, never from memory.
5. Specify: model family, link function, covariates, weights, clustering or
   strata, missing-data rule.
6. Determine whether the output is result-bearing. If yes, it needs schema /
   provenance validation and the contract path (`contract-first-tdd`).
7. Report effect sizes and uncertainty intervals — a p-value alone is an
   incomplete result.
8. Check the multiple-comparison burden where a family of models exists.
9. State exactly which paper claim the model can and cannot support. No
   causal language unless a causal design (identification strategy, named
   assumptions) has been explicitly specified and reviewed.
10. For Bayesian robustness: priors stated, convergence diagnostics run,
    posterior summaries reported, seeds and software versions recorded.

## Required Output Record

```text
model purpose · paper target · sample stage · estimand · model family ·
link function · covariates · weights/clustering/strata · missing-data rule ·
effect sizes · uncertainty intervals · diagnostics · result artifact path ·
provenance source · claim supported
```

## Self-Test Prompts

- *A logistic model is proposed on "the sample".* → Expected: require the
  fitted-sample provenance reference (stage named, `sample_provenance.fitted`).
- *A result is reported as p = 0.01 with nothing else.* → Expected: require
  the effect size or interval before the result is usable.
- *A P01-B methods task asks for regime-escape interpretation.* → Expected:
  flag the paper-scope violation; applied interpretation belongs to P01-A/P04.

## Escalate Or Stop When

- The model's estimand or eligibility rule is unclear — route to
  `panel-estimand-audit` before fitting.
- The result would become a headline paper claim — full lane review
  (`tda-statistical-analysis-review`) before prose.

## Related Skills

`statistical-design-audit` (design validity) · `tda-statistical-analysis-review`
(claims-facing review) · `panel-estimand-audit` · `contract-first-tdd`
(result-bearing implementations) · `tda-trajectory-baselines` (when the model
is a trajectory baseline) · `tda-resource-preflight` (long fits).
