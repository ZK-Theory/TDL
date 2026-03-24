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

Mapper computation complete (run/p02-mapper branch). kmapper 2.1 API fix applied.
Current state: results generated, paper not yet drafted.

## Target

Primary: *Sociological Methods & Research*
Fallback: *Journal of the Royal Statistical Society Series A*

## Key Contribution

VR persistent homology reveals global connectivity; Mapper reveals *interior density structure* — sub-regions within regimes with different escape probabilities. Colouring Mapper nodes by substantive outcomes (escape probability, income endpoint, NS-SEC origin) creates a causal geography of trajectory space that the 7-GMM typology cannot provide.

## Open Items

- [ ] Summarise Mapper results from run/p02-mapper
- [ ] Parameter tuning documentation (overlap fraction, clustering resolution)
- [ ] First draft
- [ ] Identify within-regime sub-clusters with meaningfully different escape probabilities

## Computation

See `run/p02-mapper` branch and `trajectory_tda/topology/` for Mapper code.
Key file: `trajectory_tda/experiments/` (Mapper experiment scripts).
