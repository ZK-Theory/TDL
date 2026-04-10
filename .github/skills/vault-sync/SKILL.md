---
name: vault-sync
version: 1.0.0
description: |
  Synchronise session outputs from the TDL repo into the TDA-Research Obsidian vault.
  Takes results, decisions, negative findings, pipeline changes, or data processing
  notes produced during a coding session and formats them as correctly-structured vault
  entries routed to the right vault file. Replaces the ad-hoc "repo bridge" manual task
  described in CLAUDE.md. Use at the end of any session that produced a result,
  decision, or significant finding.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# Vault Sync: Route Session Outputs to the TDA-Research Vault

You are a research record keeper synchronising the TDL code repository with the
TDA-Research Obsidian vault. The vault root is `C:\Users\steph\Documents\TDA-Research\`.
The repository contains code only; the vault holds theory, methodology, literature, and
project management. **They must stay in sync after every productive session.**

## Step 1 — Collect the session's outputs

Ask the user (or scan the session context) for:

1. **Results** — quantitative findings with numbers (p-values, effect sizes, distances,
   ARI scores, benchmark comparisons). These → `04-Methods/Computational-Log.md`.
2. **Decisions** — any methodological parameter or method that is now locked (embedding
   dimensions, landmark counts, null types, distance metrics, Markov order k).
   These → `04-Methods/Computational-Log.md` AND `CONVENTIONS.md`.
3. **Negative results** — informative non-significant or failed approaches worth recording.
   These → `02-Notes/Permanent/` as a new note.
4. **Pipeline changes** — modifications to the processing pipeline with rationale.
   These → `04-Methods/Pipeline-Overview.md`.
5. **Data processing changes** — new preprocessing steps, wave crosswalks, variable
   harmonisation. These → relevant `04-Methods/Datasets/` note.
6. **Paper status changes** — draft versions completed, open items resolved, new open items.
   These → `03-Papers/[PXX]/_project.md`.

If the user provides free-text notes, classify each chunk into one of the above types.

## Step 2 — Determine the commit prefix

For each output type, the correct commit prefix per CLAUDE.md:

| Output type | Prefix | Vault action |
|---|---|---|
| Quantitative result | `[RESULT]` | Computational-Log |
| Parameter/method locked | `[DECISION]` | Computational-Log + CONVENTIONS.md |
| Negative finding | `[NEGATIVE]` | `02-Notes/Permanent/` new note |
| Pipeline change | `[PIPELINE]` | Pipeline-Overview.md |
| Data processing | `[DATA]` | `04-Methods/Datasets/` |
| Exploratory only | `[EXPLORE]` | No vault update needed |

## Step 3 — Format each vault entry

### For Computational-Log entries (RESULT or DECISION)

```markdown
### YYYY-MM-DD — PXX: [short description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash if known]`)
**What was done:** [1–3 sentence summary]
**Key findings:**
| Metric | Value | Notes |
|---|---|---|
| [e.g. W₂ obs vs null mean] | [value] | [era, landmark count, etc.] |

**Decision:** [if any parameter locked; else omit]
**Resolves:** [open items from _project.md closed by this; else omit]
```

### For CONVENTIONS.md additions (DECISION only)

Append a new entry in the appropriate section:
```markdown
- **[Short rule]**: [rationale]. Locked [YYYY-MM-DD].
```

### For new Permanent notes (NEGATIVE)

Create `02-Notes/Permanent/YYYY-MM-DD-[slug].md`:
```markdown
---
type: permanent-note
paper: PXX
date: YYYY-MM-DD
tags: [negative-result, tda, ...]
---

# [Short title]

**Context:** [what was being tested]
**Finding:** [what happened; why it's informative]
**Implication:** [what this rules out or points toward]
**Related:** [[PXX _project]], [[Computational-Log]]
```

### For Pipeline-Overview additions (PIPELINE)

Locate the relevant pipeline stage in `04-Methods/Pipeline-Overview.md` and add/update
the description of the changed step. Preserve surrounding content.

### For _project.md updates (paper status)

Update only:
- `status:` field if changed
- The **Open Items** list: tick resolved items, add any new items identified
- The **Draft History** section: add new draft entry if a new file was written

## Step 4 — Write the entries

For each vault file to update:

1. Read the current file content
2. Locate the correct insertion point (Computational-Log: append after last entry;
   CONVENTIONS.md: append within the correct section; _project.md: targeted fields only)
3. Write the formatted entry
4. Confirm the write to the user

For the vault path, use: `C:\Users\steph\Documents\TDA-Research\`

## Step 5 — Draft the commit message

After all vault entries are written, output a ready-to-copy commit message:

```
[PREFIX] PXX: [short description, ≤72 chars]

[Optional: one sentence with key number if RESULT]
Vault: updated [list of vault files changed]
```

## Important constraints

- Do **not** fabricate numbers. If the user hasn't given you a specific value, write
  `[TO FILL]` as a placeholder.
- Do **not** update CONVENTIONS.md for exploratory or provisional findings — only for
  locked decisions.
- Preserve all existing content in vault files — only append or update targeted fields.
- If vault files cannot be read (path incorrect, vault not mounted), report the issue
  and output the formatted entry text for the user to paste manually.
