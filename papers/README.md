# TDL Research Papers

This directory contains all paper projects for the TDL research programme. Each paper has a dedicated subdirectory following a consistent structure (see below).

## Programme Overview

### Trajectory TDA Programme (P01–P10)

| Paper | Title | Status | Stage | Target Journal |
|---|---|---|---|---|
| **P01-A** | The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries | in-progress | 0 | *JRSS-A* |
| **P01-B** | Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data | in-progress | 0 | *JRSS-B* |
| P04 | Multi-Parameter Persistent Homology Reveals Income-Stratified Career Topology | in-progress | 2 | *Annals of Applied Statistics* |
| P05 | Cross-National Welfare State Topology | idea | 2 | *American Journal of Sociology* |
| P06 | Intergenerational Topological Inheritance | idea | 2 | *British Journal of Sociology* |
| P07 | Geometric Trajectory Forecasting | idea | 3 | *JMLR* |
| P08 | GNNs on Household Social Graphs | idea | 3 | *Computational Social Science* |
| P09 | CCNNs for Multi-Level Social Data | idea | 3 | *NeurIPS* |
| P10 | Topological Fairness Analysis | idea | 3 | *FAccT* |

### Archived Predecessor Papers

| Paper | Status | Archive Note |
|---|---|---|
| P01 | archived | Content redistributed to P01-A and P01-B |
| P02 | archived | Content absorbed into P01-A |
| P03 | archived | Content absorbed into P01-B |

### Financial TDA Programme

| Paper | Title | Status | Target Journal |
|---|---|---|---|
| **FIN-01** | Market Regime Detection via Persistent Homology | in-progress | *Physica A* |

**Status vocabulary:** `idea` → `in-progress` → `submitted` → `under-review` → `published` → `archived`

---

## Paper Directory Structure

Every paper directory follows this layout:

```
PXX-Name/
├── _project.md          ← YAML status + metadata (source of truth for tracking)
├── _outline.md          ← Current argument structure (update as paper evolves)
├── _reviewer-log.md     ← Reviewer comments and response tracking
├── drafts/
│   ├── vN-YYYY-MM.md   ← Versioned full drafts (e.g., v1-2025.md, v5-2026-03.md)
│   └── sections/        ← Section-level working files (optional, for large papers)
├── figures/             ← Exported PD diagrams, Mapper graphs, persistence barcodes
├── submissions/         ← Journal-specific submission packages (optional)
└── notes/               ← Paper-specific scratch: outlines, action plans, handoffs
```

### `_project.md` YAML frontmatter

All `_project.md` files use this schema (Obsidian Dataview-compatible):

```yaml
---
paper: P01                           # paper identifier
title: "Full paper title"
status: in-progress                  # idea|in-progress|submitted|under-review|published|archived
target-journal: "Journal Name"
submitted: null                      # ISO date when submitted, or null
deadline: 2026-06-01                 # target submission date, or null
priority: high                       # high|medium|low
stage: 0                             # 0=consolidate, 1=near-extensions, 2=medium, 3=deep-learning
domain: trajectory_tda               # trajectory_tda|poverty_tda|financial_tda
data: [USoc, BHPS]                   # datasets used
tags: [paper, tda, ...]
---
```

### Draft naming convention

```
v1-2025.md          ← first draft, year only if month unknown
v2-2026-01.md       ← second draft, January 2026
v5-2026-03.md       ← fifth draft, March 2026 (current)
```

### What NOT to commit here

- Raw data files (data/ directories are gitignored)
- Large figure binaries (use figures/.gitkeep as placeholder until figures are finalised)
- Jupyter notebooks (keep in domain topology/ or analysis/ directories)

---

## Stage Map

```
Stage 0 (Months 0–3):   Consolidate and submit P01
Stage 1 (Months 3–12):  P01-A + P01-B companion submissions; P02/P03 retained as archived source papers
Stage 2 (Months 12–24): P04–P06 (P04 prioritised after P01-A/B arXiv posting)
Stage 3 (Months 24–48): P07–P10 (geometric and topological deep learning)
```

See `docs/plans/strategy/Meta-Research-Plan-23-03-2026.md` for full programme detail.
