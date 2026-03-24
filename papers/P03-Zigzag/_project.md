---
paper: P03
title: "Topological Business Cycles: Zigzag Persistence and Labour Market Fragmentation in the UK, 1991–2023"
status: in-progress
target-journal: "Sociological Methods & Research"
submitted: null
deadline: 2026-12-01
priority: medium
stage: 1
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, zigzag, business-cycle, time-series-topology]
---

## Status

Zigzag implementation complete via dionysus WSL bridge (run/p03-zigzag, PR #16).
Current state: computation running/complete on run branch; paper not yet drafted.

## Target

Primary: *Sociological Methods & Research*
Fallback: *Journal of Computational Social Science*

## Key Contribution

Tracks how UK trajectory-space topology changes across annual cohort snapshots (1991–2023), capturing topological signatures of recession (1993, 2008), austerity (2010–2015), and pandemic (2020). Tests whether H₀ increases (fragmentation) during recessions and H₁ appears during recovery.

## Open Items

- [ ] Review P03 agent output from run/p03-zigzag
- [ ] Annual snapshot data pipeline verification
- [ ] First draft
- [ ] Null model for zigzag (temporal shuffle of annual snapshots)

## Computation

See `run/p03-zigzag` branch.
Key dependencies: dionysus (zigzag), gudhi (VR PH per snapshot), WSL bridge.
Computational note: hours not minutes; streaming algorithm for RAM efficiency.
