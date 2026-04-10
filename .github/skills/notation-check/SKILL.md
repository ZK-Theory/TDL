---
name: notation-check
version: 1.0.0
description: |
  Compare a paper draft against papers/shared/notation.md and flag symbol drift.
  Catches inconsistent notation before draft assembly: wrong Wasserstein subscripts,
  unlabelled filtration scales, divergent persistence diagram symbols, and paper-specific
  context violations. Use before finalising any section that contains mathematical
  notation, and always before sharing a draft externally.
allowed-tools:
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

# Notation Check: Validate Paper Draft Against Shared Notation Standard

You are a notation auditor for a multi-paper TDA research programme. The canonical
notation standard lives in `papers/shared/notation.md`. Your job is to compare a
paper draft against that standard and produce a diff-style report flagging any drift.

## Step 1 — Load the notation standard

Read `papers/shared/notation.md` in full. Extract:
- The **Default Conventions** table (symbols and their canonical meanings)
- The **Paper-Specific Context** table (which paper uses which variant of each concept)
- The **Wasserstein Order Audit** section (current verified state)

## Step 2 — Identify the target paper and draft

Ask the user:
- Which paper: `P01-A`, `P01-B`, `P04`, or specify a custom path
- Which draft file (if omitted, find the latest `vN-YYYY-MM.md` in that paper's `drafts/`)

Read the draft file.

## Step 3 — Scan for notation drift

Check each symbol category in order:

### 3a. Point cloud and embedding symbols

| Canonical | Common drift | Check |
|---|---|---|
| $X \subset \mathbb{R}^d$ | $\mathcal{X}$, $\mathbf{X}$, $\{x_i\}$ | Must match canonical unless paper documents reason |
| $X_t$ for time-indexed subset | $X^t$, $X_{(t)}$, $\mathbf{X}_t$ | Subscript position matters |

### 3b. Complex and filtration symbols

| Canonical | Common drift | Check |
|---|---|---|
| $K_\varepsilon(X)$ | $\text{VR}_\varepsilon(X)$, $\mathcal{K}_\varepsilon$, $R_\varepsilon$ | Must be $K_\varepsilon$ unless paper defines its own |
| $K_{\varepsilon,\tau}(X, a)$ (P04 only) | $K_{\varepsilon}^{\tau}$, $\mathcal{B}_{\varepsilon,\tau}$ | P04-specific; flag in P01-A/B if it appears |

### 3c. Persistence diagram symbols

| Canonical | Common drift | Check |
|---|---|---|
| $D_q(X)$ | $PD_q$, $\mathcal{D}_q$, $\text{dgm}_q$, $H_q$ (for the diagram rather than the group) | Must be $D_q$ |
| $b_i, d_i$ for birth-death pairs | $(b, d)$, $(\alpha_i, \omega_i)$, $(\sigma_i, \tau_i)$ | Must match |
| P01-B: $D_q^{\mathrm{obs}}$, $D_q^{\mathrm{null}}$ | $D_q^{obs}$, $D_q^{(0)}$ | Check upright/roman formatting |

### 3d. Persistence landscape symbols

| Canonical | Common drift | Check |
|---|---|---|
| $\lambda_q$ | $\Lambda_q$, $\mathcal{L}_q$, $PL_q$ | Must be $\lambda_q$ |
| $L^2$ distance on landscapes | $\ell^2$, Euclidean, $\|\cdot\|_2$ without "landscape" qualifier | Must be qualified |

### 3e. Wasserstein distance symbols

| Canonical | Common drift | Check |
|---|---|---|
| $W_p(D, D')$ with explicit $p$ | $W(D, D')$ (unsubscripted) | Always flag unsubscripted |
| $W_2$ for computations | $W_1$ | Flag; cross-reference Wasserstein Audit section |
| $p$ in $W_p$ defined in text | $p$ used without definition in that section | Flag |

### 3f. Statistical and null model symbols

| Canonical | Common drift | Check |
|---|---|---|
| Markov order always written as $k$ | "order" without subscript, "memory" | Flag if $k$ not stated alongside "Markov null" |
| P01-B: null diagrams as $D_q^{\mathrm{null}}$ | Various | Check |

## Step 4 — Check paper-specific context compliance

Using the Paper-Specific Context table from notation.md:
- Verify the paper uses the correct variant for its context
  (e.g., P01-B should use $D_q^{\mathrm{obs}}$ / $D_q^{\mathrm{null}}$ not plain $D_q$)
- Flag any leakage of another paper's variant into this draft

## Step 5 — Produce the notation audit report

```
## Notation Audit Report — [PAPER] [DRAFT FILE] — [DATE]

### Standard Used
papers/shared/notation.md (last updated: [date from file if available])

### Drift Findings
| Category | Line | Found in draft | Canonical form | Action |
|---|---|---|---|---|
| Wasserstein | 47 | $W(D, D')$ | $W_2(D, D')$ | Add subscript 2 |
| Persistence diagram | 83 | $PD_1(X)$ | $D_1(X)$ | Change symbol |
| Landscape | 102 | $\Lambda_0$ | $\lambda_0$ | Change symbol |

### Cross-Paper Leakage
| Line | Found | Belongs to | Action |

### Clean Sections
[List sections with no notation issues — reassures author these are ready]

### Summary
- Total drift instances: N
- Wasserstein order issues: N₁ (cross-reference wasserstein-audit for detailed treatment)
- Symbol drift (non-Wasserstein): N₂
- Cross-paper leakage: N₃
- Blocking for submission: [YES if any W₂ violations or undefined symbols in key equations]
```

## Step 6 — Ask before fixing

Do **not** apply edits without confirmation. Present the report, then ask:
- Apply all non-controversial symbol replacements (pure drift with no ambiguity)?
- For Wasserstein issues: defer to `/wasserstein-audit` for comprehensive treatment?
- Update notation.md with any new symbols introduced in this draft that should be
  added to the standard?

## Important notes

- This skill checks *symbols*, not *prose*. For prose quality, use `/humanizer`.
- For Wasserstein-specific deep audit (code + all papers), use `/wasserstein-audit`.
- Notation drift in theorems and proofs requires more care than in descriptive text —
  always flag but ask the user before editing formal mathematical environments.
