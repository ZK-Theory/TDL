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

## Prose work — audience, register, notation, completion

### THE AUDIENCE (read this before writing a single line)

**You are writing manuscript text for a journal referee who has never seen this
repository, this Task, the reviewer-response plan, or Stephen.** P01-A → a JRSS-A
reader; P01-B → a JRSS-B reader; P04 → an AoAS reader. They cannot see your
instructions and will never read your Task report. They are reading a paper.

**You are not writing a status report, a working note, or a hand-off to the
Manager.** If a sentence only makes sense to someone who has read your Task
Prompt, it does not belong in the file.

### SEPARATION OF CHANNELS (mandatory)

A prose Task has **two** outputs with **two different readers**. Put each thought
in the right one:

| Goes in the **section file** | Goes in the **Task Log / bus report** |
|---|---|
| Only text that could appear in the submitted PDF | Everything else, without exception |
| Methods, results, tables, figures, limitations, discussion | Traceability evidence ("every number cites its source JSON") |
| Genuine paper limitations, in the paper's own voice | Open items, gaps, missing inputs, blocked work |
| | Provisionality, review status, "awaiting X" |
| | Task/ISSUE IDs, response-plan mapping |
| | Anything addressed to the Manager or the User |
| | "Out of scope for this Task" |

**The test:** *would a referee reading the submitted PDF see this?* If no, it goes
in the report. The report is not a lesser channel — it is the **correct** channel,
and it is where the Manager actually looks. Surfacing a gap there is worth more
than burying it in the manuscript.

### BANNED IN SECTION FILES (non-exhaustive; the principle governs)

`this working file` · `this file` (as self-reference) · `Task Prompt` · `Manager` ·
`the User` · `ISSUE <ID>` (C1/C2/M1–M5/H1/L1 …) · `response plan` · `v2 assembly` ·
`provisional label` · `awaiting review` · `out of scope for this Task` ·
`flagged as an open item` · `supplied no such input` · `Manager-accepted` ·
`## Issues (for Manager review)` · HTML `EDITORIAL STATUS` / review-status comments ·
result-JSON filenames or repo paths in body text · Task/Stage numbers.

**Internal tracker IDs are scaffolding to dissolve, not structure to mirror.** A
heading is `## Ground metric and Wasserstein distance` — never
`## Ground metric and Wasserstein distance (corrects ISSUE H1)`. The reviewer issue
is *why we wrote it*; the paper only shows *what we concluded*.

### WHERE PROVENANCE GOES

Number-to-file traceability is a **process obligation you satisfy in the Task Log**,
not a property you advertise in the prose. The manuscript cites methods, data, and
results — never `results/.../foo_2026-05-28.json`. (The sole exception is a
reproducibility/data-availability statement, which is a legitimate paper artifact
and states archived resources in the paper's voice.)

### GAPS AND OPEN ITEMS

A gap is exactly one of two things — decide which, then treat it accordingly:
1. **A genuine paper limitation** → write it in the paper's voice, as a limitation.
   No scaffolding, no "flagged for review", no Task references.
2. **A workflow item** (missing recompute, ungated input, pending decision) →
   **report only**. It does not appear in the file at all.

Never a `## Issues` section. Never both channels "to be safe".

### PRE-DELIVERY SELF-CHECK (run before reporting — do not skip)

Re-read the section top to bottom and **delete anything a referee could not read**.
Specifically confirm: no banned tokens; no self-referential preamble; no `## Issues`
section; no tracker IDs in headings; no repo paths or JSON filenames in body text;
no provisionality or review status; every remaining sentence is addressed to the
referee. State in your report that you ran this check.

### Notation, voice, completion

- After **every** prose change, run `/notation-check` against `papers/shared/notation.md`. Never batch notation checks across section edits — check at every change to prevent compounding inconsistency.
- `/humanizer` is a final-pass gate (v2/v3 completion), not a per-section pass. **It does not catch register failures** — it targets AI tells (em-dashes, "delve", listicles). Workflow scaffolding in a manuscript is a wrong-artifact problem, and the self-check above is the only gate for it.
- Writing voice across papers and supplements is academic, professional, and mathematical. Avoid colloquialisms, hedge-stacking, contribution inflation, and the AI-tells `/humanizer` targets.
- For prose Tasks, User per-section review is a validation step — surface the section to the User before marking the Task complete. **Surface it in the report; do not annotate the file with its own review status.**
- Locked notational decisions go in `papers/shared/notation.md`; never let two papers use divergent notation for the same object.

### For the Manager dispatching prose work

- **Never call the deliverable a "working file"** — it is manuscript text for §X. A deliverable inherits the register of the instructions that commissioned it.
- **Never pass reviewer-issue IDs as the organizing frame.** Use them to decide *what to fix*; give the Worker the *substance* ("the ground-metric formula is ℓ∞ in v1 and must be ℓ²"), not the tracker label.
- **Never write a validation criterion that is satisfiable inside the artifact.** "Every numerical claim traces to a results JSON" is a Task Log obligation — say so explicitly, or the Worker will prove compliance in the prose.
- **Always name the audience and venue** in the prompt.
