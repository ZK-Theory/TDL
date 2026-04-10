---
name: wasserstein-audit
version: 1.0.0
description: |
  Audit all manuscript drafts and codebase for Wasserstein distance order consistency.
  Resolves the blocking Phase 0 deliverable: the legacy P01 manuscript writes W_1 in
  several places while the reusable trajectory Wasserstein code paths default to W_2.
  Produces a reconciliation report with file paths, line numbers, and suggested fixes.
  Use before any paper section that cites topological distances is finalised.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - AskUserQuestion
---

# Wasserstein Audit: Resolve W₁ vs W₂ Inconsistencies

You are auditing a TDA research codebase and manuscript set for Wasserstein distance
order consistency. The project mandate is: **W₂ is the primary metric**; W₁ may appear
only where explicitly justified with a written rationale; unsubscripted $W$ is never
acceptable in any manuscript.

## Context

- `papers/shared/notation.md` is the canonical notation standard — read it first.
- The archived P01 source manuscript (`papers/P01-VR-PH-Core/`) may contain legacy W₁ references.
- Active paper drafts live in `papers/P01-A-JRSSA/drafts/`, `papers/P01-B-JRSSB/drafts/`, `papers/P04-Multipers-Poverty/drafts/`.
- Python code paths: `trajectory_tda/topology/`, `trajectory_tda/analysis/`, `shared/`.

## Your Task

### Step 1 — Read the notation standard

Read `papers/shared/notation.md`, focusing on the Wasserstein Order Audit section. Note
the current verified state so your report starts from what is already known.

### Step 2 — Scan manuscript drafts (`.md` files)

Search all `.md` files under `papers/` for:

| Pattern | What to flag |
|---|---|
| `W_1` or `$W_1$` or `W_{1}` | W₁ reference — is it justified? |
| `$W$` (unsubscripted) | Always flag — violates notation standard |
| `W_p` without a stated `p` value nearby | Ambiguous — flag with context |
| `bottleneck` | Flag if it appears without an alongside Wasserstein comparison |
| `wasserstein` (case-insensitive) | Collect all — check each has an explicit order |

### Step 3 — Scan Python code

Search all `.py` files under `trajectory_tda/`, `poverty_tda/`, `financial_tda/`, `shared/` for:

| Pattern | What to flag |
|---|---|
| `wasserstein_distance` or `persim.wasserstein` | Check whether `p=1` or `p=2` is passed; default may differ by library |
| `bottleneck_distance` | Flag — must not be used as sole metric |
| `p=1` near any Wasserstein call | W₁ usage — flag with context |
| `order=1` near any Wasserstein call | Same |
| `hera` or `geom_matching` | Lower-level libraries — check their default order |

### Step 4 — Cross-reference with notation.md

For each flagged instance, note:
- Is it present in the "Verified state" section of notation.md already?
- Is it in code or manuscript?
- What is the correct fix (change order to 2, add subscript, add justification comment)?

### Step 5 — Produce a reconciliation report

Output a structured report in this format:

```
## Wasserstein Audit Report — [DATE]

### Notation Standard Summary
[one sentence on what notation.md requires]

### Manuscript Findings
| File | Line | Found | Issue | Suggested Fix |
|---|---|---|---|---|
| papers/P01-A.../v5... | 47 | $W_1$ | W₁ used as primary metric | Change to $W_2$ |

### Code Findings
| File | Line | Found | Issue | Suggested Fix |
|---|---|---|---|---|
| trajectory_tda/topology/wasserstein.py | 83 | wasserstein_distance(a, b) | No p argument; persim default is p=2, confirm intent | Add p=2 explicitly |

### Status
- Total issues: N
- Manuscript: N₁ issues (N₂ already in notation.md "verified" section)
- Code: N₃ issues
- Blocking Phase 0: [YES / NO — list any remaining W₁ in active drafts]

### Recommended Actions
1. ...
2. ...
```

### Step 6 — Ask before fixing

Do **not** apply changes automatically. Present the report, then ask the user:
- Which manuscript fixes to apply now?
- Which code fixes to apply now?
- Should notation.md "verified state" section be updated to reflect newly audited files?

## Key context

- `persim.wasserstein_distance` uses p=2 by default (this is correct)
- `gudhi.wasserstein.wasserstein_distance` requires explicit `order=` argument;
  default is not guaranteed across versions — always make it explicit
- `giotto-tda` Wasserstein vectorisation uses p=2 by default
- W₁ is sometimes used in theory proofs (stability theorems) — acceptable in a
  Methods section if labelled and distinguished from the computational metric used
