---
paper: P04
title: "Multi-Parameter Persistent Homology for Poverty Trap Detection"
status: idea
target-journal: "JASA Applications and Case Studies"
submitted: null
deadline: null
priority: medium
stage: 2
domain: poverty_tda
data: [USoc, BHPS]
tags: [paper, tda, multipers, bifiltration, poverty-traps]
---

## Status

Idea stage. Existing poverty_tda draft and outline in `notes/` and `drafts/` — these predate the current research plan and may need revisiting.

## Key Contribution

Bi-filtration on distance + income threshold tests whether near-absorbing states cluster distinctively at the low-income level in a way global PH cannot detect. Uses `multipers` library with gudhi backend.

## Computational Requirements

- Local: feasible at 2,000–5,000 landmarks (32GB RAM)
- Cloud: full-scale bifiltration (8,000+ landmarks × fine income discretisation) may need A100 (~4–8 GPU-hrs)

## Dependencies

- P01 complete (for embedding pipeline)
- `multipers` library installed and validated
