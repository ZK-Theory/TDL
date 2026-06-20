---
paths:
  - "vault/**"
---

# Vault Entry Formats and Templates

Applies when writing to the research vault (via the `vault/` junction or absolute paths under `C:\Users\steph\Documents\TDA-Research\`). **Insert new entries at the top of the page, just below the `---` header, reverse-chronological** (2026-05-25 vault-discipline `[DECISION]`).

## Ways to file session outputs

1. **In Cowork:** say "repo bridge" / "log results" to trigger the `tda-repo-bridge` skill.
2. **In Claude Code / Copilot:** write the entry directly to `vault/04-Methods/Computational-Log.md` (or the absolute vault path).
3. **Manually:** add the entry to `04-Methods/Computational-Log.md` in the vault.
4. **Consider a daily note** (template below) for the session story.

## Computational-Log entry format

```
### YYYY-MM-DD — PXX: [short description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash]`)
**What was done:** [summary]
**Key findings:** [table or bullets]
**Decision:** [if any parameter/method locked]
**Resolves:** [open items closed]
```

Pre-registration entries (written **before** outcome-contingent runs) record: parameter values, decision rule, prose-direction rule per outcome, timestamp. The post-run `[RESULT]` references the pre-registration.

`[NEGATIVE]` findings also get a permanent note in `02-Notes/Permanent/`.

## Daily note (`vault/05-Daily/YYYY-MM-DD.md`)

Computational-Log entries are reserved for formal artifacts. The session story — judgement calls, dead-ends, surprises, CodeRabbit batches reviewed, "TIL X about library Y" — belongs in a daily note. Draft one at session close if the session produced *any* of: a non-obvious judgement call, a surprise finding not formal enough for the log, a queued open item, a workflow lesson, or a CodeRabbit review batch. Skip for pure execution with no commentary worth preserving.

```markdown
---
date: YYYY-MM-DD
type: daily
tags: [daily]
---

# YYYY-MM-DD — <one-line session-defining headline>

## What landed

- commit `<hash>`: [PREFIX] PXX: <one-line>

## Threads we pulled

- <surprise / dead-end / judgement call, one line of why it mattered>

## Worth remembering (not [DECISION]-worthy)

- <numerical artifact, library quirk, workflow lesson — the kind of thing
  you'd otherwise rediscover painfully next year>

## Open at end of session

- <queued item> → [[03-Papers/P01-A-JRSSA/_project|P01-A open items]]

## Links

[[Computational-Log#YYYY-MM-DD-PXX-...]] · [[CONVENTIONS]]

---

*[[YYYY-MM-DD|← Previous daily note]]*
```

Sections may be omitted when empty. The daily note is a session-history artefact, not a status report — write for future-you reconstructing *why* something landed the way it did.
