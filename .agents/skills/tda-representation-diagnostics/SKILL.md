---
name: tda-representation-diagnostics
description: Use when checking embedding stability, scaler/PCA/loadings behaviour, UMAP or t-SNE projections, observed/null coordinate-frame alignment, representation drift, or SHAP/feature explanations in TDL.
---

# TDA Representation Diagnostics

The hands-on diagnostic toolkit for embeddings and learned representations.
It guards one of the project's most damaging risk classes: **observed and null
diagrams must not be compared after independently re-fitting PCA / scaler /
loadings** — the frozen-loadings defect that put a battery of Markov and
order-shuffle results under PROVISIONAL flags. Boundary:
`representation-freeze-audit` is the assurance-lane *judgment* pass; this
skill *runs the diagnostics* and produces the record that audit consumes. A
representation change that would alter PH inference goes through
`contract-first-tdd`, never directly from here.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Procedure

1. Identify the representation (e.g. `ngram_pca`, a UMAP projection, a
   fitted scaler) and where it sits in the pipeline.
2. State its status: **inference** (feeds a claim-bearing computation) or
   **visualization-only**. UMAP/t-SNE output is visualization-only unless
   explicitly contracted otherwise.
3. Identify what data the representation is **fit** on.
4. Identify what data it is **applied** to.
5. Check the coordinate frame: do observed and null data share one fitted
   frame (frozen loadings), or is the transform re-fit per draw? Re-fit per
   draw means a distance between them jointly tests generative difference
   AND basis rotation.
6. Check seed, scaler, PCA, and loadings reproducibility (recorded, pinned,
   re-loadable).
7. SHAP or other explanations: associational language only — never causal —
   unless separately justified.
8. Record whether a contract or a representation-lane review is required,
   and emit the output record.

## Output Record

```json
{
  "skill": "tda-representation-diagnostics",
  "paper_id": "P01-B",
  "representation": "ngram_pca",
  "fit_data": "observed_only",
  "transform_data": ["observed", "null_draws"],
  "frozen_loadings": true,
  "inference_status": "claim-bearing | visualization-only",
  "visualization_only": false,
  "risk_flags": [],
  "contract_required": true,
  "recommended_next_skill": "contract-first-tdd"
}
```

## Self-Test Prompts

- *An agent wants to compute VR persistence directly on UMAP coordinates.* →
  Expected: escalate to representation review; UMAP is visualization-only
  unless explicitly contracted, and its distances are not the pipeline metric.
- *Observed and null PCA are re-fitted separately before a W2 comparison.* →
  Expected: flag invalid coordinate-frame comparison (frozen-loadings class);
  results are PROVISIONAL until fixed.
- *SHAP values are described as showing that education "drives" escape.* →
  Expected: prohibit causal phrasing; associational only.

## Escalate Or Stop When

- The diagnostic implies an existing published or committed result sits on an
  invalid frame — that is a defect
  (`tda-diagnosing-computational-defects`) and a PROVISIONAL flag, not a
  quiet re-run.
- A representation change is proposed to fix the issue — route through
  `representation-freeze-audit` + `contract-first-tdd`.

## Related Skills

`representation-freeze-audit` (the lane judgment) · `tda-domain-modeling`
(frozen vs re-fit vocabulary) · `contract-first-tdd` ·
`tda-diagnosing-computational-defects` · `tda-trajectory-baselines` (input
representation comparability).
