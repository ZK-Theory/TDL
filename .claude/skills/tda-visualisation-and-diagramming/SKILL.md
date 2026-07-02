---
name: tda-visualisation-and-diagramming
description: Use when creating or reviewing paper figures, diagnostic plots, Mapper diagrams, trajectory summaries, pipeline schematics or Mermaid diagrams, or exploratory visualizations — and when checking a figure's provenance and regenerability.
---

# TDA Visualisation & Diagramming

Figure governance: classification, provenance binding, and caption-claim
proportionality. Boundary: `tda-figure-spec` owns the matplotlib publication
*mechanics* for trajectory figures (PUBLICATION_RC, DPI, FIGSIZE_*,
STATE_COLORS, `_save_figure`) — route paper-figure code there; this skill owns
what class of figure something is, what it may claim, and whether it can be
regenerated. A plot never substitutes for a test, and a paper figure that
cannot be regenerated from a script does not exist.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Figure Classes

`paper_figure` · `diagnostic_figure` · `exploratory_figure` ·
`pipeline_diagram` · `reviewer_response_figure` · `website_figure`

A `paper_figure` MUST be bound to a script and an input artifact. An
`exploratory_figure` is labelled exploratory and cannot support a claim until
promoted through validation and provenance.

## Procedure

1. Classify the figure.
2. Identify the input artifact (result-file path) and paper target.
3. Determine whether the plot is evidential or exploratory — evidential
   figures inherit their input's provenance requirements, including
   PROVISIONAL flags.
4. For paper figures: require script-based regeneration (script path + input
   + command reproduces the file), via the `tda-figure-spec` conventions for
   matplotlib work.
5. Record parameters and seeds (layout seeds for graph figures included).
6. Validate labels, captions, units — and check the **caption claim** against
   the underlying result: the visual claim must not exceed the statistic
   (`W2` and landscape L2 conventions apply to captions too).
7. Save figure and metadata together; date-suffix outputs, never overwrite.
8. Pipeline schematics and methodology diagrams (Mermaid or otherwise) are
   `pipeline_diagram` class — no provenance binding needed, but they must
   match the pipeline as implemented, not as remembered.

## Output Record

```json
{
  "skill": "tda-visualisation-and-diagramming",
  "figure_class": "paper_figure",
  "paper_id": "P01-B",
  "script_path": null,
  "input_artifacts": [],
  "output_path": null,
  "parameters": {},
  "seed": null,
  "caption_claim": null,
  "regenerable": false,
  "risk_flags": ["missing_regeneration_script"]
}
```

## Self-Test Prompts

- *A striking exploratory UMAP plot is proposed as Figure 2.* → Expected:
  exploratory class cannot be promoted directly; it needs the representation
  check, a script, an input artifact, and a proportional caption.
- *A caption says "topological structure collapses after 2008" over a figure
  showing one summary statistic dipping.* → Expected: flag caption-claim
  disproportion.

## Escalate Or Stop When

- A figure's input artifact carries a PROVISIONAL flag — the figure carries
  it too; do not typeset it as final.
- A requested figure needs data that exists only in a gitignored intermediate
  — regenerate from the committed script first.

## Related Skills

`tda-figure-spec` (matplotlib publication mechanics) · `tda-peer-review-panel`
(figures reviewed with their sections) · `tda-domain-modeling` (caption
terminology) · `result-provenance-review` (input artifact status).
