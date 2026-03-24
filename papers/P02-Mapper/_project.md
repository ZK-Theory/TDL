---
paper: P02
title: "From Global Topology to Navigable Trajectory Space: Mapper Analysis of UK Employment Trajectories"
status: in-progress
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

Mapper computation complete. Pipeline run on 27,280 PCA-20D embeddings from P01 integration results.
Current state: first draft with actual results (v1-2026-03.md). §4 populated with computed outputs (1,060 nodes, NMI=0.434, 358 sub-regime nodes on PC1).
Results saved to `results/trajectory_tda_mapper/`.

## Target

Primary: *Sociological Methods & Research*
Fallback: *Journal of the Royal Statistical Society Series A*

## Key Contribution

VR persistent homology reveals global connectivity; Mapper reveals *interior density structure* — sub-regions within regimes with different escape probabilities. Colouring Mapper nodes by substantive outcomes (escape probability, income endpoint, NS-SEC origin) creates a causal geography of trajectory space that the 7-GMM typology cannot provide.

## Open Items

- [x] Summarise Mapper results from run/p02-mapper
- [x] Parameter tuning documentation (overlap fraction, clustering resolution)
- [x] First draft (v1-2026-03.md)
- [x] Identify within-regime sub-clusters with meaningfully different outcomes (PC1, L2 norm)
- [x] Populate §4 results with computation outputs
- [ ] Generate figures (Mapper graphs coloured by PC1, L2 norm, regime labels)
- [ ] Reconstruct trajectory sequences for integration results (needed for employment rate, final income colouring)
- [ ] Re-run sub-regime analysis with lower DBSCAN eps to resolve churning-regime noise
- [ ] Run /humanizer pass before submission review

## Computation

Mapper code: `trajectory_tda/mapper/` (mapper_pipeline.py, node_coloring.py, validation.py, parameter_search.py).
Pipeline script: `trajectory_tda/scripts/run_mapper_from_existing.py` (uses P01 embeddings directly).
Results: `results/trajectory_tda_mapper/` (01–08 JSON outputs + HTML visualisations).

### Key results
- Best params: PCA-2D, n_cubes=30, overlap=0.5
- Graph: 1,060 nodes, 1,774 edges, 223 components, 50.7% coverage
- NMI=0.434, purity=0.999, 0 bridge nodes
- 358 sub-regime nodes on PC1 (|z|>1.0); R6 most heterogeneous (std=1.23)
- 297 sub-regime nodes on L2 norm
