---
name: phase0-status
version: 1.0.0
description: |
  Produce a single-screen Phase 0 status dashboard for P01-A, P01-B, and the
  shared notation standard. Reads all three _project.md files and notation.md,
  extracts blocking deliverables and open items, and renders a prioritised
  status view grouped by: blocking (must resolve before any draft assembly),
  paper-specific open items, and resolved items. Use at the start of a session
  or when deciding what to work on next.
allowed-tools:
  - Read
  - Glob
---

# Phase 0 Status: Current State of P01-A, P01-B, and Shared Infrastructure

You are producing a session-start status dashboard for Phase 0 of the research
programme. Phase 0 is the strategic reorganisation into two companion papers,
P01-A (JRSS-A) and P01-B (JRSS-B), submitted simultaneously with same-day arXiv
posting. The dashboard surfaces what is blocking, what is in progress, and what
has been resolved.

## Step 1 — Read the source files

Read all of these in parallel:

1. `papers/P01-A-JRSSA/_project.md`
2. `papers/P01-B-JRSSB/_project.md`
3. `papers/shared/notation.md` — focus on the Wasserstein Order Audit section
4. `papers/shared/submission-statements.md` — check what is/isn't drafted

Also check for any recent draft files:
- `papers/P01-A-JRSSA/drafts/` — list files and note the latest version
- `papers/P01-B-JRSSB/drafts/` — same

## Step 2 — Extract Phase 0 blocking deliverables

The three known Phase 0 blockers from `CLAUDE.md` / programme plan are:

1. **Authorship / corresponding-author decision** — check if resolved in either `_project.md`
2. **Shared notation standard** — check `notation.md`; is the Wasserstein order audit complete?
3. **Wasserstein-order audit** — is `W_1` vs `W_2` resolved in all active drafts?

For each: report status (Resolved / Partially resolved / Blocking).

## Step 3 — Extract paper-specific open items

From each `_project.md`, extract the **Open Items** checklist:
- Mark items with `[x]` as resolved
- Mark items with `[ ]` as open
- Classify each open item: `BLOCKING` (nothing can proceed without it) | `NEXT` (ready to work on now) | `PENDING` (waiting on another item)

## Step 4 — Check draft status

For each paper:
- What is the latest draft version and file path?
- When was it written (from filename `vN-YYYY-MM.md`)?
- Is there an outline (`_outline.md`)? Read the first few lines.

## Step 5 — Render the dashboard

Output in this format:

```
═══════════════════════════════════════════════════════════
  PHASE 0 STATUS DASHBOARD — [DATE]
═══════════════════════════════════════════════════════════

PROGRAMME-LEVEL BLOCKERS
─────────────────────────────────────────────────────────
[RESOLVED] Authorship decision — single author Stephen Dorman (OU)
[RESOLVED/BLOCKING/PARTIAL] Notation standard — papers/shared/notation.md
[RESOLVED/BLOCKING/PARTIAL] Wasserstein audit — W₁/W₂ in active drafts

SHARED INFRASTRUCTURE
─────────────────────────────────────────────────────────
notation.md:   [summary of status from Wasserstein Audit section]
submission-statements.md:  [drafted / not started / partial]

P01-A (JRSS-A) — The Geometry of UK Career Inequality
─────────────────────────────────────────────────────────
Status:      [status from _project.md]
Latest draft: [path, version, date]
Open items:
  [BLOCKING] • [item]
  [NEXT]     • [item]
  [PENDING]  • [item]
Resolved:
  ✓ [item]

P01-B (JRSS-B) — Structured Hypothesis Testing for PH
─────────────────────────────────────────────────────────
Status:      [status from _project.md]
Latest draft: [path, version, date]
Open items:
  [BLOCKING] • [item]
  [NEXT]     • [item]
  [PENDING]  • [item]
Resolved:
  ✓ [item]

RECOMMENDED NEXT ACTIONS
─────────────────────────────────────────────────────────
1. [Most critical unblocking action]
2. [Next action after that]
3. [Third priority]

AVAILABLE SKILLS FOR CURRENT BLOCKERS
─────────────────────────────────────────────────────────
• /wasserstein-audit  — resolve W₁/W₂ in drafts and code
• /notation-check [paper] [draft] — validate draft notation
• /vault-sync  — log session outputs to vault
• /paper-repo-extract [paper] — when ready for submission
═══════════════════════════════════════════════════════════
```

## Step 6 — Do not modify anything

This skill is read-only. It never modifies `_project.md` or any other file.
If the user wants to act on an item, direct them to the appropriate skill:
- Notation issues → `/notation-check` or `/wasserstein-audit`
- Vault logging → `/vault-sync`
- Null model work → `/markov-null-design`
- Repo preparation → `/paper-repo-extract`
- Writing → `/paper-draft`
