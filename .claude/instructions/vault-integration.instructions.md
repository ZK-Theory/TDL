---
description: Obsidian vault integration workflows and vault-engine MCP usage.
alwaysApply: true
---

## Vault Integration

The TDL research record lives in a separate Obsidian vault at:
`C:\Users\steph\Documents\TDA-Research\`

This repo contains the code. The vault contains theory, methodology, literature, and project management. **They must stay in sync.**

### Vault Structure

| Vault location | What's there |
|---|---|
| `03-Papers/[ID]/_project.md` | Paper status, open items, draft history |
| `04-Methods/Computational-Log.md` | Logged results and decisions |
| `04-Methods/Pipeline-Overview.md` | Pipeline architecture description |
| `04-Methods/Datasets/` | Dataset processing notes |
| `02-Notes/Permanent/` | Crystallised methodological insights |
| `CONVENTIONS.md` | Always/never rules with rationale — **load at session start** |
| `VAULT-MAP.md` | Full vault navigation index |

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
- `vault_observe` — save observations linked to vault pages for cross-session memory

### When Working on Code

**Always cross-check `CONVENTIONS.md` for locked methodological decisions before implementing.**

Any new decision should be added there after locking.

### Session Sync Requirements

Every Task ends with the appropriate vault entry written via `vault_observe`:

- Computational Tasks write `[RESULT]`
- Parameter or method locks write `[DECISION]`
- Informative null findings write `[NEGATIVE]`
- Pipeline changes write `[PIPELINE]`
- Data-processing changes write `[DATA]`

### Pre-Registration Protocol

Pre-registration entries are written *before* outcome-contingent runs, not after. Each pre-registration records:
- Parameter values
- Decision rule
- Prose-direction rule per outcome
- Timestamp

The post-run `[RESULT]` entry references the pre-registration.

### Vault Access Policy

- Vault access is MCP-only via the `vault-engine` server
- Do not attempt direct filesystem reads of the vault path
- Use vault tools consistently for all vault interactions

### After-Session Sync Workflow

When finishing a session that produced results, decisions, or insights:

1. **In Cowork:** Say "repo bridge" or "log results" to trigger the `tda-repo-bridge` skill
2. **In Claude Code / Copilot:** Produce the vault entry text and submit it via `vault_observe` or the `vault-engine` API; do not rely on direct filesystem writes to the vault when MCP access is available
3. **Manually:** Use the vault-engine tools if direct filesystem access is unavailable

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