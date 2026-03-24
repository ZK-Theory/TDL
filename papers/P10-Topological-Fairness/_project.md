---
paper: P10
title: "Topological Fairness: Wasserstein Analysis of Prediction Error Structure Across Demographic Groups"
status: idea
target-journal: "FAccT"
submitted: null
deadline: null
priority: low
stage: 3
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, fairness, wasserstein, prediction-error, demographic, tda]
---

## Status

Idea stage. Requires P07 complete (needs trained forecasting model).

## Key Contribution

Computes Wasserstein distances between persistence diagrams of prediction residuals across gender, ethnic, and class groups. Detects topologically-structured bias invisible to mean-error fairness metrics.

## Computational Requirements

Trivial — CPU-only, hera library, minutes. All cost is having P07 model trained.

## Policy relevance

Universal Credit administration, housing allocation, school placement — algorithmic systems with potentially topologically distinct errors across demographic groups.

## Dependencies

- P07 complete (trained forecasting model)
