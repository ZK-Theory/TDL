---
paper: P01-A
title: "The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries"
status: in-progress
target-journal: "Journal of the Royal Statistical Society Series A"
submitted: null
deadline: null
priority: high
stage: 0
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, persistent-homology, mapper, career-inequality, jrss-a]
---

## Status

Phase 0 scaffolding created for the journal-targeted reorganisation. This paper
absorbs the applied VR-PH regime analysis from `papers/P01-VR-PH-Core/` and the
Mapper interior-structure analysis from `papers/P02-Mapper/`.

Authorship fixed by programme convention: single author Stephen Dorman
(The Open University, UK).

Planned submission strategy: simultaneous JRSS-A submission, JRSS-B companion
submission, and same-day arXiv posting (`stat.AP`).

## Target

Primary: *Journal of the Royal Statistical Society Series A*

## Source Papers

- `papers/P01-VR-PH-Core/` — global topology, regime identification,
  stratified analyses, BHPS replication
- `papers/P02-Mapper/` — within-regime anatomy, outcome geography,
  Mapper robustness analyses

## Draft History

**v1** — 2026-04-30 — ~9,800 words
Path: `papers/P01-A-JRSSA/drafts/v1-2026-04.md`
Assembled from P01-VR-PH-Core v8 and P02-Mapper v5; ~65% cut from ~29k source words.

## v2 revision under APM v1.0.1 management (locked 2026-05-05)

Comprehensive reviewer-response scope across three independent reviewers:

- **R1** (TDA methodologist): 11 issues H1–L3 plus embedded concerns 10.1–10.5
- **R2** (social scientist): 14 issues S1–S14
- **R3** (biostatistician): 13 issues B1–B13

Plus two prose-vs-code mismatches identified during code audit (Markov-2 Laplace
smoothing absent; ε*=0.70 derivation undocumented).

**Authoritative documents.** All issues itemised with strategy, artefacts, and
verification at:

- `notes/2026-05-01-reviewer-response-plan.md` — master integration
- `notes/2026-05-03-reviewer2-social-scientist-issues.md` — S1–S14 detail
- `notes/2026-05-03-reviewer3-biostatistician-issues.md` — B1–B13 detail

**APM execution.** Decomposed by the Planner into 4 Workers (TDA, Panel
Statistics, Reproducibility, Academic Writing), 5 Stages, 74 Tasks. Spec and
Plan at `.apm/spec.md` and `.apm/plan.md`; APM_RULES block in workspace
`CLAUDE.md`; Message Bus at `.apm/bus/`.

**Subsequent (post-v2 follow-on).** Option A full sample re-extraction (R2 §S1.5
Component 1 with full TDA pipeline rerun on the gap-tolerant 10-of-14 sample)
is in scope as APM Plan Stage 4; original 27,280 sample then demoted to
robustness check.

## Open Items

Detailed checklists are in the response plans (P01-A §12 acceptance criteria,
per-issue verification sub-sections) and in `.apm/plan.md` Tasks 0.x–4.x.
Headline categories:

- [ ] Write the integrated JRSS-A outline and argument arc
- [x] Assemble v1 from P01 v8 and P02 v5 — done 2026-04-30; v1 at ~9,800 words
- [ ] Stage 0: locked `uv` environment + two-machine determinism + code-side
      fixes (Markov-2 smoothing, ε* knee algorithm, W₂ test construction,
      regime-label bug) + harmonised-dataset verification (`jbstat`, income
      concept) + sibling clusters from `xhhrel`
- [ ] Stage 1: full null battery + Tier 1/2/3 GLMM + survey-methodology
      computations under locked environment (28 Tasks)
- [ ] Stage 2: v2 prose drafting (22 section-by-section Tasks), supplements,
      JRSS-spec figures, `/notation-check` per change, `/humanizer` at
      completion
- [ ] Stage 3: standalone reproducibility repo extraction
- [ ] Stage 4: Option A full sample re-extraction (post-v2 follow-on)
- [ ] Generate Supplementary A imputation balance by regime
- [ ] Generate Figure S1 from `embeddings_umap16.npy`
- [ ] Move Mapper sensitivity grid and heavy pipeline detail to the supplement
- [ ] Prepare JRSS-A submission package and arXiv metadata (LaTeX class
      `papers/style_guides/JRSS/statsoc.cls`)
