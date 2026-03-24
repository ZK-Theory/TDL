---
paper: P01
title: "Persistent Homology of UK Socioeconomic Life-Course Trajectories"
status: in-progress
target-journal: "Sociological Methodology"
submitted: null
deadline: 2026-06-01
priority: high
stage: 0
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, persistent-homology, markov-ladder, wasserstein, core]
---

## Status

Current draft: `drafts/v5-2026-03.md` (fifth draft)

Key finding: Order-shuffle H₀ rejected (*p* < 0.005, total persistence). Markov-1 rejected under Wasserstein (*p* = 0.002) but not under total persistence (*p* = 1.000). Discrepancy between test statistics is the headline methodological finding.

## Target

Primary: *Sociological Methodology*
Fallback: *Social Forces* / *JASA: Applications & Case Studies*

## Open Items

- [ ] Wasserstein testing on BHPS-era sample (n=8,509) — validates discrepancy cross-era
- [ ] Wasserstein test for full 5-model battery (currently only order-shuffle + Markov-1)
- [ ] Final humaniser pass on v5 before submission
- [ ] Figures: all 14 figures remain as placeholders in text

## Draft History

| Version | File | Date | Key changes |
|---|---|---|---|
| v1 | `drafts/v1-2025.md` | 2025 | Initial draft |
| v2 | `drafts/v2-2025.md` | 2025 | Extended results |
| v3 | `drafts/v3-2026-01.md` | 2026-01 | Full pipeline validation |
| v4 | `drafts/v4-2026-03.md` | 2026-03 | Total-persistence results complete |
| v5 | `drafts/v5-2026-03.md` | 2026-03 | **Wasserstein results integrated; test-statistic discrepancy as headline** |

## Computation

All results in `results/trajectory_tda_integration/`:
- `04_nulls_wasserstein.json` — Wasserstein null test results (P01 Wasserstein run)
- Main pipeline: `trajectory_tda/scripts/bhps_pipeline.py`
