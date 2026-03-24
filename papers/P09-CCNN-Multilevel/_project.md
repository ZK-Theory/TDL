---
paper: P09
title: "Combinatorial Complex Neural Networks for Multi-Level Social Data"
status: idea
target-journal: "NeurIPS"
submitted: null
deadline: null
priority: low
stage: 3
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, deep-learning, ccnn, cell-complex, multilevel, topomodelx]
---

## Status

Idea stage. Most computationally ambitious paper in the programme.

## Key Contribution

Individuals (0-cells), households (1-cells), neighbourhoods (2-cells), local authorities (3-cells) as hierarchical cell complex. CCNN simultaneously models all four levels. Uses TDA escape-probability labels from P01 as supervision signal.

## Computational Requirements

- 2-level (individual + household): RTX 3080 sufficient
- 3-level: careful memory management, possible cloud
- 4-level: cloud required (~20–40 GPU-hrs on A100)

## Dependencies

- P01 + P07 + P08 complete
- TopoModelX / TopoNetX installed and validated
