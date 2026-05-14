# /commit-log — Draft Commit Message and Vault Entry

Produce a correctly prefixed commit message (≤72 chars) and the matching Obsidian vault
entry — both ready to copy-paste — for work just completed. Combines the two tasks that
currently happen separately at session end.

## Usage

```
/commit-log
/commit-log [result|decision|negative|pipeline|data|explore]
```

Example: `/commit-log result` — for a quantitative finding
Example: `/commit-log` — interactive, asks about what was produced

---

## Prefix selector

| What was produced | Prefix | Vault destination |
|---|---|---|
| Quantitative result (p-value, ARI, Wasserstein…) | `[RESULT]` | `04-Methods/Computational-Log.md` |
| Parameter or method locked | `[DECISION]` | Computational-Log **+** `CONVENTIONS.md` |
| Informative negative result | `[NEGATIVE]` | `02-Notes/Permanent/YYYY-MM-DD-slug.md` |
| Pipeline change | `[PIPELINE]` | `04-Methods/Pipeline-Overview.md` |
| Data processing change | `[DATA]` | `04-Methods/Datasets/[note]` |
| Exploratory only | `[EXPLORE]` | Nothing required |

Multiple types? Use highest priority (RESULT > DECISION > NEGATIVE > PIPELINE > DATA > EXPLORE).

---

## Commit message format

```
[PREFIX] PXX: [description ≤72 chars total including prefix+paper]

[Optional one-sentence body: key number, locked value, or rationale]
Vault: updated [file1], [file2]
```

### Good examples

```
[RESULT] P01-B: USoc Markov-2 null W₂ p=0.003 (H₁, L=5000, n=500)

Vault: updated 04-Methods/Computational-Log.md
```

```
[DECISION] P01-A: lock UMAP n_components=16, n_neighbors=15

Vault: updated 04-Methods/Computational-Log.md, CONVENTIONS.md
```

```
[EXPLORE] P04: scaffold bifiltration grid search — no results yet
```

**Describe the result, not the action.** Prefer "H₁ topology exceeds Markov-2 null (p=0.003)"
over "run Markov-2 permutation test".

---

## Vault entry formats

### Computational-Log (RESULT/DECISION)

```markdown
### YYYY-MM-DD — PXX: [description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash]`)
**What was done:** [summary]
**Key findings:**
| Metric | Value | Context |

**Decision:** [if locked; omit otherwise]
**Resolves:** [_project.md items closed; omit if none]
```

### CONVENTIONS.md addition (DECISION only)

```markdown
- **[Rule]**: [rationale]. Locked YYYY-MM-DD. Commit: `[hash]`.
```

### Permanent note (NEGATIVE — new file `02-Notes/Permanent/YYYY-MM-DD-slug.md`)

```markdown
---
type: permanent-note / paper: PXX / date: YYYY-MM-DD
---
**Context:** / **Finding:** / **Implication:** / **Related:**
```

---

## Output: two copy-ready blocks

**Block 1** — Commit message
**Block 2** — Vault entry with target file path and insertion point

Use `[TO FILL]` for any number the user has not yet provided.
