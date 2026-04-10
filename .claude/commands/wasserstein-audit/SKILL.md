# /wasserstein-audit — Audit Wasserstein Order Consistency

Scan all manuscript drafts and codebase for W₁ vs W₂ inconsistencies. Resolves the blocking
Phase 0 deliverable: the legacy P01 manuscript uses W₁ in several places while project
convention mandates W₂ as the primary metric.

## Usage

```
/wasserstein-audit
/wasserstein-audit [papers|code|all]
```

Example: `/wasserstein-audit all`

---

## What this does

1. Reads `papers/shared/notation.md` (canonical notation standard, Wasserstein Audit section)
2. Scans manuscript `.md` files under `papers/` for W₁, unsubscripted W, ambiguous W_p
3. Scans Python files under all domain packages for Wasserstein calls without explicit `p=2`
4. Cross-references findings against what notation.md already has "verified"
5. Produces a structured reconciliation report — does **not** fix anything without confirmation

---

## Manuscript patterns that trigger a flag

| Pattern | Issue |
|---|---|
| `W_1` / `$W_1$` / `W_{1}` | W₁ usage — needs justification or must change to W₂ |
| `$W$` (unsubscripted) | Always flag — violates notation standard |
| `bottleneck` without alongside Wasserstein | Sole metric violation |
| `wasserstein` without explicit order nearby | Ambiguous |

## Code patterns that trigger a flag

| Pattern | Issue |
|---|---|
| `wasserstein_distance(a, b)` with no `p=` arg | Default may not be W₂ in all library versions |
| `p=1` or `order=1` near Wasserstein call | Explicit W₁ usage |
| `bottleneck_distance(...)` | Must not be used as sole metric |
| `gudhi.wasserstein.wasserstein_distance` without `order=2` | gudhi default not guaranteed |

---

## Report format

```
## Wasserstein Audit Report — YYYY-MM-DD

### Manuscript Findings
| File | Line | Found | Issue | Suggested Fix |

### Code Findings
| File | Line | Found | Issue | Suggested Fix |

### Status
- Blocking Phase 0: YES / NO
- Total issues: N (manuscript: N₁, code: N₂)

### Recommended Actions
```

## Library defaults (reference)

- `persim.wasserstein_distance` — p=2 by default ✓
- `gudhi.wasserstein.wasserstein_distance` — requires explicit `order=` arg
- `giotto-tda` Wasserstein vectorisation — p=2 by default ✓
- W₁ in theory proofs is acceptable in Methods sections if clearly labelled and
  distinguished from the computational metric used
