---
paper: P08
title: "Relational Trajectory Topology: GNNs on Household Social Graphs"
status: idea
target-journal: "Computational Social Science"
submitted: null
deadline: null
priority: low
stage: 3
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, deep-learning, gnn, household-graphs, relational]
---

## Status

Idea stage. Requires P07 complete or parallel.

## Key Contribution

Individuals as nodes; household membership and geocoded neighbourhood proximity as edges. GNN-learned representations replace n-gram vectors as TDA pipeline input. Tests whether household/neighbourhood relational context changes the topological complexity bound.

## Dependencies

- P01 complete (for topology comparison framework)
- P07 parallel or complete (GNN architecture base)
- torch-geometric
