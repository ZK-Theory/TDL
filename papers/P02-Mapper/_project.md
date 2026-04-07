---
paper: P02
title: "From Global Topology to Navigable Trajectory Space: Mapper Analysis of UK Employment Trajectories"
status: archived
target-journal: "Sociological Methods & Research"
submitted: null
deadline: 2026-09-01
priority: high
stage: 1
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, mapper, kmapper, trajectory, interior-structure]
---

## Status

Archived on 2026-04-07. Content absorbed into `papers/P01-A-JRSSA/`. The v5
draft, figures, and LaTeX sources remain as the historical source record for the
within-regime anatomy component of the companion JRSS-A paper.

v5 draft complete (v5-2026-04.md). Final revision addressing all outstanding reviewer feedback.

Changes v4→v5:
- §1.3: Strengthened sociological value proposition — now explicitly ties navigability to absorbing-state boundary identification and efficiency targeting for policy interventions
- §2.1: Added specification that X is the 27,280-point cloud in R^20 and k ∈ {1, 2} (reviewer technical correction)
- §3.4: Clarified that consecutive identical states count as no transition for churning rate
- §3.7: Expanded |z| > 1.0 justification with three-part rationale, explicit acknowledgement of non-normality, and note on FDR correction for 14 comparisons
- §4.2: Separated R0 and R6 coverage figures with explicit percentages and noise counts (reviewer technical correction on Table 3 interpretation)
- §4.3: Expanded multi-threshold analysis prose with monotonicity note and clearer FDR/permutation interplay
- §4.4.1 Figure 9: Cross-referenced churning decomposition in §4.4.2 to clarify nature of R3/R5 cycling
- §5.5: Added practitioner considerations paragraph comparing OM vs Mapper tuning complexity
- §5.6: Added paragraph on |z| > 1.0 as exploratory vs individually significant
- Figure 6 caption: Now includes bridge node counts for both panels
- Code Availability: Added Python version, data access note (UK Data Service SN 6614)
- References: Alphabetised (Dorman moved to correct position)
- All "Author (2026a)" → "Dorman (2026a)" confirmed throughout
- All "causal geography" → "outcome geography" confirmed throughout

Previous drafts: v1-2026-03.md, v2-2026-03.md, v3-2026-03.md, v4-2026-04.md.

Results saved to `results/trajectory_tda_mapper/reviewer_response/` (01\u201305 JSON outputs).

## Target

Primary: *Sociological Methods & Research*
Fallback: *Journal of the Royal Statistical Society Series A*

## Key Contribution

VR persistent homology reveals global connectivity; Mapper reveals *interior density structure* — sub-regions within regimes with different escape probabilities. Colouring Mapper nodes by substantive outcomes creates an outcome geography of trajectory space that the 7-GMM typology cannot provide. Sensitivity analysis across 24 configurations separates robust findings (within-regime heterogeneity) from algorithm-dependent findings (noise rate, bridge nodes). Permutation nulls confirm sub-regime structure is not distributional artefact (regime-shuffle: obs=358 vs null mean=86, p<0.01; within-node-shuffle: obs=358 vs null mean=9.4, p<0.01). UMAP-16D robustness check confirms sub-regime findings are embedding-invariant. R3/R5 churning decomposition reveals that both regimes have identical E\u2194I transition rates but differ structurally: R3 churns within employment income bands; R5 churns within inactivity income bands.

## Open Items

The standalone submission is retired. Remaining unchecked items below are kept as
historical context and, where still relevant, should be evaluated inside P01-A
rather than completed in this archived directory.

- [x] Summarise Mapper results from run/p02-mapper
- [x] Parameter tuning documentation
- [x] v1\u2013v3 drafts
- [x] Sensitivity analysis (24 configs)
- [x] Trajectory outcome reconstruction (14 variables)
- [x] LaTeX pipeline and PDF build
- [x] Obsidian vault updated
- [x] Permutation null tests (regime-shuffle, within-node-shuffle, 100 perms each)
- [x] Multi-threshold sub-regime analysis + FDR correction
- [x] UMAP-16D embedding robustness
- [x] Outcome\u2013embedding correlation matrix
- [x] R3/R5 churning decomposition
- [x] OM dendrogram figure (Fig 11)
- [x] v4 draft (all reviewer-response revisions)
- [x] v5 draft (final revision — all feedback items resolved)
- [x] Rebuild LaTeX (main.tex/body.tex) to match v4
- [ ] Rebuild LaTeX from v5 markdown
- [ ] Run /humanizer pass before submission review
- [ ] Final figure quality review (production-ready PNGs/PDFs)
- [ ] Resolve P01 companion paper "causal geography" → "outcome geography" for consistency
- [ ] Supplementary materials (interactive HTML Mapper visualisations)

## Computation

Mapper code: `trajectory_tda/mapper/` (mapper_pipeline.py, node_coloring.py, validation.py, parameter_search.py, permutation_null.py, correlation_analysis.py).
Pipeline script: `trajectory_tda/scripts/run_mapper_from_existing.py`.
Sensitivity sweep: `trajectory_tda/scripts/run_mapper_sensitivity_sweep.py` (24 configs).
Reviewer analyses: `trajectory_tda/scripts/run_p02_reviewer_analyses.py` (UMAP robustness, null tests, multi-threshold FDR, correlation matrix, R3/R5 churning decomp).
OM dendrogram: `trajectory_tda/viz/om_dendrogram_figure.py`.
LaTeX: `papers/P02-Mapper/latex/` (Makefile, main.tex, body.tex, references.bib) — *needs rebuilding for v4*.
Figure generation: `trajectory_tda/scripts/generate_mapper_figures.py` (7 figures).
Results: `results/trajectory_tda_mapper/` (01–08 JSON + HTML) and `results/trajectory_tda_mapper/reviewer_response/` (01–05 JSON).

### Key results (baseline DBSCAN eps=0.5, PCA-2D)
- Graph: 1,060 nodes, 1,774 edges, 223 components, 50.7% coverage
- NMI=0.434, purity=0.999, 0 bridge nodes
- 358 sub-regime nodes on PC1 (|z|>1.0); R6 most heterogeneous (std=1.23)
- Regime-shuffle null: observed=358, null mean=86.3, p<0.01 (0/100 perms \u2265 358)
- Within-node-shuffle null: observed=358, null mean=9.4, p<0.01
- FDR correction: 2/14 regime\u00d7variable tests significant at q<0.05 (both R6)
- PC1\u2013employment\_rate correlation: r=\u22120.921 (high overlap expected)
- PC1\u2013churning\_rate correlation: r=+0.115 (independent dimension)

### Key results (UMAP-16D robustness)
- UMAP-16D + first-2D lens: 1,604 nodes, 100% coverage, NMI=0.422, purity=0.967, 81 bridge nodes, 576 sub-regime nodes
- Qualitative sub-regime and bridge findings confirmed; quantitative differences expected from non-linear embedding
