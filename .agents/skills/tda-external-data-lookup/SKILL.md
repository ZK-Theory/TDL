---
name: tda-external-data-lookup
description: Use when retrieving external economic, demographic, financial, regulatory, or contextual data — FRED, World Bank, Eurostat, ONS, SEC, market data — to support TDL papers or provide covariates and context.
---

# TDA External Data Lookup

Every external lookup becomes a **provenance artifact**: the query, the
returned metadata, and the retrieval date are stored, and no value is
free-typed into manuscript prose. Not for Understanding Society / BHPS core
data — that goes through official survey documentation and the project's
crosswalk discipline (`bhps-wave-crosswalk`).

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Procedure

1. State why the external data is needed and which claim or section it serves.
2. Identify the source authority (official statistical agency, central bank,
   registry) — prefer the primary publisher over aggregators.
3. Record the query parameters: dataset ID, endpoint, series codes, filters.
4. Retrieve (or prepare the retrieval command) and store the raw response or
   its metadata alongside the derived artifact.
5. Transform only in scripted form — no hand-edited spreadsheets between the
   source and the artifact.
6. Record units, coverage period, version/release, and the missing-data
   handling applied.
7. Classify the use: **contextual** (background prose), **inferential**
   (enters a model), or **illustrative** (figure only). Inferential use pulls
   the full provenance path (date-suffixed artifact, seeds if resampled,
   schema validation).
8. Link the artifact to the paper target and claim.

## Required Output Record

```text
source database · dataset ID · endpoint/query · retrieval date ·
version/release · units · coverage period · transformations ·
missing-data handling · local artifact path · paper target ·
claim supported · use class (contextual/inferential/illustrative)
```

## Self-Test Prompts

- *"UK unemployment was around 4% then" typed into a draft.* → Expected:
  replace with a retrieved, dated, versioned series value stored as an
  artifact and cited by reference.
- *A World Bank series is about to enter a model as a covariate.* → Expected:
  inferential classification — full provenance artifact plus a check that the
  series vintage matches the panel window.

## Escalate Or Stop When

- The needed series exists only from a non-authoritative aggregator —
  surface the sourcing risk rather than quietly using it.
- The external series would redefine an estimand or eligibility rule —
  `panel-estimand-audit` first.

## Related Skills

`bhps-wave-crosswalk` (survey core data — not this skill) ·
`tda-literature-verification` (scholarly sources) · `tda-document-ingestion`
(reports/codebooks) · `result-provenance-review` (artifact discipline).
