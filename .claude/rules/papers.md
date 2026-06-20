---
paths:
  - "papers/**"
---

# Papers — Structure, Schema, and Prose Rules

All paper projects live in `papers/`, **not** in domain subdirectories. The domain directories hold code only. See `papers/README.md` for full structure documentation.

## Directory layout for each paper

```
papers/PXX-Name/
├── _project.md          ← YAML metadata (status, journal, deadline) — source of truth
├── _outline.md          ← Current argument structure
├── _reviewer-log.md     ← Reviewer comments and response tracking
├── drafts/
│   ├── vN-YYYY-MM.md   ← Versioned full drafts (v1-2025.md, v5-2026-03.md, …)
│   └── sections/        ← Section-level working files (optional)
├── figures/             ← Exported PD diagrams, Mapper graphs, barcodes
└── notes/               ← Scratch: outlines, action plans, handoff notes
```

## `_project.md` YAML schema (mandatory fields)

```yaml
---
paper: P01                    # paper identifier (P01–P10, FIN-01, etc.)
title: "Full paper title"
status: in-progress           # idea | in-progress | submitted | under-review | published | archived
target-journal: "Name"
submitted: null               # ISO date or null
deadline: 2026-06-01          # target submission date or null
priority: high                # high | medium | low
stage: 0                      # 0=consolidate | 1=near | 2=medium | 3=deep-learning
domain: trajectory_tda        # trajectory_tda | poverty_tda | financial_tda
data: [USoc, BHPS]
tags: [paper, tda, ...]
---
```

## Current submission track

| ID | Title | Status | Stage | Target | arXiv |
|---|---|---|---|---|---|
| P01-A | The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries | in-progress | 0 | JRSS-A | stat.AP |
| P01-B | Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data | in-progress | 0 | JRSS-B | stat.ME |
| P04 | Multi-Parameter Persistent Homology Reveals Income-Stratified Career Topology | in-progress | 2 | AoAS | stat.ME, math.AT |

## Later programme papers

| ID | Title | Status | Stage |
|---|---|---|---|
| P05 | Cross-National Welfare State Topology | idea | 2 |
| P06 | Intergenerational Topological Inheritance | idea | 2 |
| P07 | Geometric Trajectory Forecasting | idea | 3 |
| P08 | GNNs on Household Graphs | idea | 3 |
| P09 | CCNNs for Multi-Level Social Data | idea | 3 |
| P10 | Topological Fairness | idea | 3 |
| FIN-01 | Market Regime Detection (financial) | in-progress | — |

Archived source papers preserved as historical record: `papers/P01-VR-PH-Core/`, `papers/P02-Mapper/`, `papers/P03-Zigzag/`.

## Draft naming convention

`vN-YYYY-MM.md` — e.g., `v5-2026-03.md` for the fifth draft written in March 2026. Never overwrite a previous draft; create the next version.

## Rules for agents working on papers

1. **Always** open `papers/PXX/_project.md` first to read current status and open items.
2. **Always** update `_project.md` status and open items after making changes; when a Task completes work on the open-items list, mark items closed and append to draft history if a new draft was produced.
3. New drafts go in `papers/PXX/drafts/` with version prefix — never overwrite a previous draft.
4. Computational results go in `results/` (domain-specific) — never in `papers/`.
5. Figures are placeholders in text `[Figure N]` until the final production pass.
6. After completing a draft, run `/humanizer` before marking the paper `submitted`.

## Start work on a paper

1. Check `papers/PXX/_project.md` — status, open items, current draft path.
2. Read the current draft `papers/PXX/drafts/vN-YYYY-MM.md`.
3. Run required computation in the domain directory; save results to `results/`.
4. Write or update the draft as `papers/PXX/drafts/vN+1-YYYY-MM.md`.
5. Update `_project.md` open items and status.
6. Run `/humanizer` before marking a draft ready for submission review.
7. Branch naming: `paper/pXX-name` for paper writing; `run/pXX-name` for computation.

## Prose work — notation, voice, completion

- After **every** prose change, run `/notation-check` against `papers/shared/notation.md`. Never batch notation checks across section edits — check at every change to prevent compounding inconsistency.
- `/humanizer` is a final-pass gate (v2/v3 completion), not a per-section pass.
- Writing voice across papers and supplements is academic, professional, and mathematical. Avoid colloquialisms, hedge-stacking, contribution inflation, and the AI-tells `/humanizer` targets.
- For prose Tasks, User per-section review is a validation step — surface the section to the User before marking the Task complete.
- Locked notational decisions go in `papers/shared/notation.md`; never let two papers use divergent notation for the same object.
