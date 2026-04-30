# /notation-check — Check Paper Draft Against Notation Standard

Compare a paper draft against `papers/shared/notation.md` and flag symbol drift.
Catches wrong Wasserstein subscripts, divergent persistence diagram symbols, unlabelled
filtration scales, and cross-paper notation leakage before drafts are finalised.

## Usage

```
/notation-check [paper] [draft-file]
/notation-check P01-A
/notation-check P01-B papers/P01-B-JRSSB/drafts/v3-2026-04.md
```

If `draft-file` is omitted, the latest `vN-YYYY-MM.md` in that paper's `drafts/` is used.

---

## Symbols checked

### Wasserstein (highest priority — links to `/wasserstein-audit`)

| Flag | Issue |
|---|---|
| `$W$` unsubscripted | Always wrong |
| `$W_1$` | Must justify or change to `$W_2$` |
| `$W_p$` without $p$ defined nearby | Ambiguous |

### Persistence diagrams

| Canonical | Common drift |
|---|---|
| `$D_q(X)$` | `$PD_q$`, `$\mathcal{D}_q$`, `$\text{dgm}_q$` |
| `$D_q^{\mathrm{obs}}$`, `$D_q^{\mathrm{null}}$` (P01-B only) | `$D_q^{obs}$`, `$D_q^{(0)}$` |

### Complexes and filtrations

| Canonical | Common drift |
|---|---|
| `$K_\varepsilon(X)$` | `$\text{VR}_\varepsilon$`, `$R_\varepsilon$`, `$\mathcal{K}_\varepsilon$` |
| `$K_{\varepsilon,\tau}(X,a)$` (P04 only) | Any variant in P01-A/B — flag leakage |

### Landscapes and birth-death pairs

| Canonical | Common drift |
|---|---|
| `$\lambda_q$` | `$\Lambda_q$`, `$PL_q$` |
| `$b_i, d_i$` | `$(b,d)$`, `$(\alpha_i,\omega_i)$` |

### Markov null models

| Rule | Flag |
|---|---|
| Markov order always written as $k$ explicitly | "Markov null" without stating $k$ |

---

## Report format

```
## Notation Audit — [PAPER] [DRAFT] — YYYY-MM-DD

### Drift Findings
| Category | Line | Found | Canonical | Action |

### Cross-Paper Leakage
| Line | Found | Belongs to | Action |

### Clean Sections
[Sections with no issues]

### Summary
- Total drift: N  |  Wasserstein: N₁  |  Symbol: N₂  |  Leakage: N₃
- Blocking for submission: YES / NO
```

## Notes

- Symbol drift only — for prose quality use `/humanizer`
- For full Wasserstein audit across all papers + code, use `/wasserstein-audit`
- Propose fixes but do not apply without user confirmation
- Notation drift in theorems requires extra care — always ask before editing
