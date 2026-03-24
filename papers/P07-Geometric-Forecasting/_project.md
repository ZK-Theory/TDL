---
paper: P07
title: "Structure-Respecting Trajectory Forecasting for Labour Market Dynamics"
status: idea
target-journal: "Journal of Machine Learning Research"
submitted: null
deadline: null
priority: low
stage: 3
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, deep-learning, gnn, forecasting, graph-transformer, tda]
---

## Status

Idea stage. Requires P01 complete.

## Key Contribution

GRU/LSTM over state embeddings + GNN layer on 9-node state graph. Topological counterfactuals: simulate trajectories under modified transition matrices and compare PH of simulated cloud to observed.

## Dependencies

- P01 complete
- torch-geometric installed
- RTX 3080 sufficient for training
