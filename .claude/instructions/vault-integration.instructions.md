---
description: Obsidian vault integration workflows and vault-engine MCP usage.
alwaysApply: true
---

## Vault Integration

The TDL research record lives in a separate Obsidian vault at:
`C:\Users\steph\Documents\TDA-Research\`

This repo contains the code. The vault contains theory, methodology, literature, and project management. **They must stay in sync.**

### Vault Structure

| Vault location                    | What's there                                                  |
| --------------------------------- | ------------------------------------------------------------- |
| `03-Papers/[ID]/_project.md`      | Paper status, open items, draft history                       |
| `04-Methods/Computational-Log.md` | Logged results and decisions                                  |
| `04-Methods/Pipeline-Overview.md` | Pipeline architecture description                             |
| `04-Methods/Datasets/`            | Dataset processing notes                                      |
| `02-Notes/Permanent/`             | Crystallised methodological insights                          |
| `CONVENTIONS.md`                  | Always/never rules with rationale — **load at session start** |
| `VAULT-MAP.md`                    | Full vault navigation index                                   |

### Vault-Engine MCP Tools

Access vault via vault-engine MCP server tools:

**Query and Retrieval:**

- `vault_query` — search across vault with wikilink expansion
- `vault_get` — get specific vault page with link context
- `vault_skeleton` — token-efficient summaries of multiple pages
- `vault_graph` — explore wikilink neighborhood around a page

**Status and Health:**

- `vault_status` — dashboard showing vault status, paper pipeline, health metrics
- `cross_vault` — detect shared concepts across TDA-Research and Counting Lives vaults

**Memory and Observations:**

- `vault_observe` — attach a short observation record to a vault page for cross-session retrieval. **This does NOT append content to the page.** Observations surface alongside the linked page in `vault_query` and `vault_get` results. Use only for brief breadcrumbs ("decision X linked to page Y"); never use it as a substitute for actual file edits.

### When Working on Code

**Always cross-check `CONVENTIONS.md` for locked methodological decisions before implementing.**

Any new decision should be added there after locking.

### Session Sync Requirements

Every Task ends with the appropriate vault entry **appended to the relevant vault file via the `Write` or `Edit` tool against an absolute path under `C:\Users\steph\Documents\TDA-Research\`**:

- Computational Tasks write `[RESULT]` → `04-Methods/Computational-Log.md`
- Parameter or method locks write `[DECISION]` → `04-Methods/Computational-Log.md` and (where it locks a rule) `CONVENTIONS.md`
- Informative null findings write `[NEGATIVE]` → `04-Methods/Computational-Log.md` and a permanent note in `02-Notes/Permanent/`
- Pipeline changes write `[PIPELINE]` → `04-Methods/Pipeline-Overview.md`
- Data-processing changes write `[DATA]` → relevant `04-Methods/Datasets/` note

`vault_observe` is not the write path. It stores a separate observation attached to a page; it does not append to the page itself. If an entry must also surface from vault queries against a non-obvious page, follow the `Write`/`Edit` append with a short `vault_observe` linking the entry to that page.

### Pre-Registration Protocol

Pre-registration entries are written _before_ outcome-contingent runs, not after. Each pre-registration records:

- Parameter values
- Decision rule
- Prose-direction rule per outcome
- Timestamp

The post-run `[RESULT]` entry references the pre-registration.

### Vault Access Policy

- **Reads** use the `vault-engine` MCP tools (`vault_get`, `vault_query`, `vault_skeleton`, `vault_status`, `vault_graph`, `cross_vault`). They give wikilink-graph context that raw filesystem reads do not.
- **Writes** use the `Write` and `Edit` tools against absolute paths under `C:\Users\steph\Documents\TDA-Research\`. The vault is on the local filesystem and is editable. There is no MCP `vault_write` tool.
- `vault_observe` is for cross-session breadcrumbs only; it does not append to the page.

### After-Session Sync Workflow

When finishing a session that produced results, decisions, or insights:

1. **In Cowork:** Say "repo bridge" or "log results" to trigger the `tda-repo-bridge` skill.
2. **In Claude Code / Copilot:** Produce the vault entry text and append it to the relevant vault file via `Write` / `Edit` at its absolute path under `C:\Users\steph\Documents\TDA-Research\`.
3. **Optional:** Follow with a `vault_observe` against the same page if the entry should also be discoverable from queries against a related page that does not yet wikilink to it.

**Format for Computational-Log entries:**

```
### YYYY-MM-DD — PXX: [short description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash]`)
**What was done:** [summary]
**Key findings:** [table or bullets]
**Decision:** [if any parameter/method locked]
**Resolves:** [open items closed]
```

### Cross-Reference Requirements

When working on paper code:

- Load `CONVENTIONS.md` at session start for locked decisions
- Reference `03-Papers/[ID]/_project.md` for current paper status
- Update vault entries when completing open items
- Maintain consistency between repo results and vault documentation
