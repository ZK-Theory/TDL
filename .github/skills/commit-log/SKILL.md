---
name: commit-log
version: 1.0.0
description: |
  Draft a commit message and the corresponding Obsidian vault entry for the
  current session's work. Selects the correct commit prefix ([RESULT],
  [DECISION], [NEGATIVE], [PIPELINE], [DATA], [EXPLORE]), drafts the message
  within the 72-character subject limit, and generates a ready-to-paste vault
  entry in the correct format for the target file. Combines two mental tasks
  that are currently done separately at the end of every session.
allowed-tools:
  - Read
  - Grep
  - AskUserQuestion
---

# Commit Log: Draft Commit Message + Vault Entry

You are producing a commit message and Obsidian vault entry for work just
completed on the TDL codebase. These two outputs go together: every meaningful
commit has a vault counterpart that makes the work findable later.

## Step 1 — Understand what was done

Ask the user (or infer from context):

1. What was produced in this session? Options:
   - Quantitative result (p-values, ARI, Wasserstein distances, benchmark scores)
   - Methodological/parameter decision (something is now locked)
   - Negative/null result
   - Pipeline restructuring or new module
   - Data processing change (new variable, harmonisation, wave coverage)
   - Exploratory/scaffolding only (no fixed outputs)

2. Which paper does this belong to? (`P01-A`, `P01-B`, `P04`, `FIN-01`, or none)

3. Which script or notebook produced the output? (for vault entry `**Script:**` line)

4. Any key numbers to record? (p-values, sample sizes, distances, effect sizes)

5. Is there a git commit hash available? (optional, for vault entry)

---

## Step 2 — Select the commit prefix and vault destination

| What was produced | Prefix | Vault destination |
|---|---|---|
| Quantitative result worth logging | `[RESULT]` | `04-Methods/Computational-Log.md` |
| Parameter or method locked | `[DECISION]` | Computational-Log **+** `CONVENTIONS.md` |
| Informative negative result | `[NEGATIVE]` | `02-Notes/Permanent/YYYY-MM-DD-slug.md` (new) |
| Pipeline change | `[PIPELINE]` | `04-Methods/Pipeline-Overview.md` |
| Data processing change | `[DATA]` | `04-Methods/Datasets/[note]` |
| Exploratory/scaffolding only | `[EXPLORE]` | None required |

If multiple types apply (common): use the highest-priority prefix in the order
above (RESULT > DECISION > NEGATIVE > PIPELINE > DATA > EXPLORE), and write the
vault entry for each type.

---

## Step 3 — Draft the commit message

### Format rules
- Subject line: `[PREFIX] PXX: [description, ≤72 chars total]`
- Body (optional, one sentence): the key number if RESULT, the locked value if DECISION
- Final line: `Vault: updated [comma-separated vault files]`
- No period at the end of the subject

### Examples

```
[RESULT] P01-B: USoc Markov-2 null W₂ p=0.003 (H₁, L=5000, n=500)

Vault: updated 04-Methods/Computational-Log.md
```

```
[DECISION] P01-A: lock UMAP n_components=16, n_neighbors=15

Locks embedding dimensions following stability sweep; see results/...
Vault: updated 04-Methods/Computational-Log.md, CONVENTIONS.md
```

```
[PIPELINE] P01-B: add stratified_markov1 null to standard test battery

Vault: updated 04-Methods/Pipeline-Overview.md
```

```
[EXPLORE] P04: scaffold bifiltration grid search — no results yet
```

---

## Step 4 — Draft the vault entry

### For Computational-Log (RESULT or DECISION)

Append entry in this format (do not overwrite existing content):

```markdown
### YYYY-MM-DD — PXX: [short description matching commit subject]

**Script/notebook:** `C:\Users\steph\TDL\[path\to\script.py]` (commit `[hash]`)
**What was done:** [1–3 sentence summary in past tense]
**Key findings:**
| Metric | Value | Context |
|---|---|---|
| [e.g., W₂ obs vs null mean] | [value ± sd] | [era, L=, n_perms=, seed=] |

**Decision:** [if method/parameter locked; omit if RESULT only]
**Resolves:** [open items from _project.md closed; omit if none]
```

### For CONVENTIONS.md (DECISION only — append to relevant section)

```markdown
- **[Rule]**: [What is locked and why]. Locked [YYYY-MM-DD]. Commit: `[hash]`.
```

### For Pipeline-Overview.md (PIPELINE)

Describe where in the pipeline the change fits. Read the current file to find
the right section before generating the insertion text.

### For Permanent Note (NEGATIVE — create new file)

Filename: `02-Notes/Permanent/YYYY-MM-DD-[slug].md`

```markdown
---
type: permanent-note
paper: PXX
date: YYYY-MM-DD
tags: [negative-result, tda, [domain-tag]]
---

# [Short title describing what was ruled out]

**Context:** [What was being tested and why]
**Finding:** [What happened — quantitative if possible]
**Implication:** [What this rules out; what direction it points toward]
**Related:** [[PXX _project]], [[Computational-Log]]
```

---

## Step 5 — Output

Produce **two ready-to-copy blocks**:

### Block 1: Commit message

```
[copy-ready commit message]
```

### Block 2: Vault entry

```
TARGET FILE: C:\Users\steph\Documents\TDA-Research\[file]
INSERT: [append to end / after section X]

[copy-ready vault entry]
```

If there are multiple vault files (e.g., DECISION → Computational-Log + CONVENTIONS.md),
produce a separate Block 2 for each.

---

## Constraints

- Do not fabricate numbers. Use `[TO FILL]` if the user hasn't provided a value.
- 72-character limit on commit subject: count the characters, truncate if needed.
- Body lines ≤72 characters each.
- Commit messages should describe the *result*, not the action ("add code for X").
  Prefer: `[RESULT] P01-B: H₁ topology exceeds Markov-2 null (p=0.003)` over
  `[RESULT] P01-B: run Markov-2 permutation test`.
