# /vault-sync — Sync Session Outputs to the Research Vault

Route results, decisions, negative findings, and pipeline changes from the current session
into the correct TDA-Research Obsidian vault files. Replaces the "repo bridge" manual task.

## Usage

```
/vault-sync
/vault-sync [result|decision|negative|pipeline|data|paper]
```

Example: `/vault-sync` (interactive — ask about all output types)
Example: `/vault-sync decision` (focused — only locked-parameter decisions)

---

## Output type → vault destination

| What happened | Commit prefix | Goes in |
|---|---|---|
| Quantitative result (p-value, ARI, W₂ distance…) | `[RESULT]` | `04-Methods/Computational-Log.md` |
| Parameter or method locked | `[DECISION]` | Computational-Log **+** `CONVENTIONS.md` |
| Informative negative result | `[NEGATIVE]` | `02-Notes/Permanent/YYYY-MM-DD-slug.md` (new) |
| Pipeline change | `[PIPELINE]` | `04-Methods/Pipeline-Overview.md` |
| Data processing change | `[DATA]` | `04-Methods/Datasets/[relevant note]` |
| Paper open items resolved | — | `03-Papers/PXX/_project.md` |
| Exploratory only | `[EXPLORE]` | Nothing required |

Vault root: `C:\Users\steph\Documents\TDA-Research\`

---

## Computational-Log entry format

```markdown
### YYYY-MM-DD — PXX: [short description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash]`)
**What was done:** [summary]
**Key findings:**
| Metric | Value | Notes |

**Decision:** [if locked; else omit]
**Resolves:** [open items closed; else omit]
```

## CONVENTIONS.md entry format (DECISION only)

Append within the relevant section:
```markdown
- **[Rule]**: [rationale]. Locked YYYY-MM-DD.
```

## Permanent note format (NEGATIVE only)

Create `02-Notes/Permanent/YYYY-MM-DD-[slug].md`:
```markdown
---
type: permanent-note
paper: PXX
date: YYYY-MM-DD
---
# [Title]
**Context:** / **Finding:** / **Implication:** / **Related:**
```

---

## Commit message output

At the end, output a ready-to-copy commit message:

```
[PREFIX] PXX: [description ≤72 chars]

Vault: updated [files changed]
```

## Constraints

- Do not fabricate numbers — use `[TO FILL]` as placeholder
- Only update CONVENTIONS.md for locked decisions, not provisional findings
- If vault path is unreachable, output the entry text for manual paste
