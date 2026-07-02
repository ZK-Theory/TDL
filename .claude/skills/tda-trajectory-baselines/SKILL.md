---
name: tda-trajectory-baselines
description: Use when building or reviewing conventional non-topological baselines for trajectory work — clustering, classification, forecasting, anomaly detection, or survival/duration comparison — to contextualize a persistent-homology result.
---

# TDA Trajectory Baselines

Build conventional baselines that contextualize PH results — for P01-A
interpretation, P01-B methodological comparison, FIN-01 market regimes, or
later forecasting work. A baseline exists in relation to a named TDA claim;
do not use this skill when the baseline would become a main result with no
clear relation to the TDA argument.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Baseline Classes

`descriptive` · `predictive` · `robustness` · `negative-control` ·
`interpretability` — name the class first; it determines the metrics and the
language the comparison may use.

## Procedure

1. Identify the role of the baseline and the PH result it contextualizes
   (by result-file path).
2. Specify the input representation — and whether it is shared with, or
   deliberately different from, the PH pipeline's representation.
3. **Leakage check (be severe):** does any future information enter a
   predictor; is a scaler/PCA fitted on the full dataset before a temporal
   split; do trajectory summaries contain post-outcome information; does the
   split respect the panel structure (person-level, not row-level)?
4. **Sample comparability:** baseline and PH results use comparable samples —
   reconcile against `sample_provenance`, and name the stage. A baseline on a
   different sample is a different claim.
5. Choose metrics appropriate to the task (and report uncertainty, not point
   scores alone).
6. Specify split, random seed, and resampling scheme; record all three.
7. Record failure modes and limitations alongside the scores.
8. Store outputs with provenance (date-suffixed, no overwrite, seeds in the
   result file).

## Required Output Record

```text
baseline type · input representation · target/outcome · train/test split ·
leakage check · metrics · random seed · sample provenance · comparison target
(PH result path) · paper claim supported · limitations
```

## Self-Test Prompts

- *A classifier uses trajectory features summarised over all waves to predict
  an outcome observed mid-panel.* → Expected: flag temporal leakage;
  post-outcome information is in the predictors.
- *A baseline clustering is compared against PH regimes computed on a
  different cohort filter.* → Expected: flag sample non-comparability; align
  stages before comparing.

## Escalate Or Stop When

- The baseline outperforms or contradicts the PH result — that is a finding,
  not a nuisance; route to `tda-statistical-analysis-review` and surface it
  honestly in the paper's comparison section.
- Compute is long/stochastic — `tda-resource-preflight` first.

## Related Skills

`tda-statistical-modeling-toolkit` (model fitting discipline) ·
`tda-representation-diagnostics` (input representation checks) ·
`tda-resource-preflight` · `paper-claim-trace` (binding the comparison claim).
