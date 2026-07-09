---
name: commit-log
description: Use at session end, after completing work worth committing — drafts the correctly prefixed commit message ([RESULT]/[DECISION]/[NEGATIVE]/[PIPELINE]/[DATA]/[EXPLORE]) and the matching Obsidian vault entry, both copy-paste ready.
---

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

Classify the commit and the knowledge-routing authority separately. A governance,
control-plane, or infrastructure decision may correctly use `[DECISION]` while an explicit
task boundary prohibits changing active research or vault state. When the decision is
already recorded in an accepted repository decision document, use:

```
Vault: not updated — non-research design decision; task boundary prohibits research-state mutation
```

Do not use this exception for research methods, parameters, estimands, or result interpretation.

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

## Delivery notes (Windows / PowerShell 5.1)

When writing the commit message to a temp file for `git commit -F <file>`:

- **Do NOT use `Out-File -Encoding utf8`** — PS 5.1 emits UTF-8 *with BOM*. The
  repo's `prepare-commit-msg` hook reads the first token of line 1 to detect the
  `[PREFIX]`; the BOM makes the token `<BOM>[PREFIX]`, the check fails, and the
  hook prepends its own template over the message.
- **Use instead:**
  ```powershell
  [System.IO.File]::WriteAllText($path, $msg, (New-Object System.Text.UTF8Encoding($false)))
  ```
  The `$false` argument disables the BOM. The `[PREFIX]` must be the very first
  bytes of the file.
- After committing, read the resulting subject (for example, `git log -1 --format=%s`)
  and verify that the intended project prefix and paper identifier survived hook processing.

## Output: two copy-ready blocks

**Block 1** — Commit message
**Block 2** — Vault entry with target file path and insertion point

Use `[TO FILL]` for any number the user has not yet provided.

## Pre-delivery check

- The subject uses an allowed research prefix and paper identifier and is at most 72 characters.
- Vault routing matches the content and the task authority boundary.
- Windows commit-message instructions use UTF-8 without BOM and include post-commit verification.
