# /phase0-status — Phase 0 Status Dashboard

Produce a single-screen status view for P01-A, P01-B, and the shared notation
infrastructure. Reads `_project.md` files, `notation.md`, and draft directories.
Read-only — never modifies files.

## Usage

```
/phase0-status
```

---

## What it reads

| File | What it surfaces |
|---|---|
| `papers/P01-A-JRSSA/_project.md` | Status, open items, resolved items |
| `papers/P01-B-JRSSB/_project.md` | Status, open items, resolved items |
| `papers/shared/notation.md` | Wasserstein audit state |
| `papers/shared/submission-statements.md` | Drafted / not started |
| `papers/P01-A-JRSSA/drafts/` | Latest draft version and date |
| `papers/P01-B-JRSSB/drafts/` | Latest draft version and date |

---

## Programme-level blockers (check first)

1. **Authorship decision** — check if resolved in `_project.md`
2. **Notation standard** — is `notation.md` Wasserstein Audit section complete?
3. **W₁/W₂ audit** — any `W_1` or unsubscripted `W` in active drafts?

---

## Dashboard format

```
═══════════════════════════════════════════════════════
  PHASE 0 STATUS DASHBOARD — YYYY-MM-DD
═══════════════════════════════════════════════════════

PROGRAMME-LEVEL BLOCKERS
[RESOLVED/BLOCKING/PARTIAL] Authorship
[RESOLVED/BLOCKING/PARTIAL] Notation standard
[RESOLVED/BLOCKING/PARTIAL] Wasserstein audit

P01-A — [status] — Latest draft: vN-YYYY-MM.md
  [BLOCKING] • ...
  [NEXT]     • ...
  ✓ ...

P01-B — [status] — Latest draft: vN-YYYY-MM.md
  [BLOCKING] • ...
  [NEXT]     • ...
  ✓ ...

RECOMMENDED NEXT ACTIONS
1. ...

RELEVANT SKILLS
• /wasserstein-audit  /notation-check  /vault-sync
• /paper-draft  /markov-null-design  /paper-repo-extract
═══════════════════════════════════════════════════════
```

## Open-item classification

- `[BLOCKING]` — nothing else can proceed without resolving this
- `[NEXT]` — ready to work on now
- `[PENDING]` — waiting on another item first
