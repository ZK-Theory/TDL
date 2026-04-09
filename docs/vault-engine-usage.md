# Vault-Engine: Usage Guide

**Last updated:** 2026-04-08

Vault-engine is an MCP server that gives AI agents on-device access to the
Obsidian research vaults. It combines three layers:

1. **QMD** — local embeddings for hybrid search (BM25 + vector + reranking)
2. **Wikilink graph** — SQLite index of `[[wikilinks]]` across all vault pages
3. **Skeletonisation** — token-efficient page summaries (80–90% reduction)

The server is configured in `.mcp.json` (VS Code Copilot / Claude Code) and
`claude_desktop_config.json` (Claude Desktop). It runs as a subprocess
launched by the host application — no separate process to manage.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  AI Agent (Copilot / Claude Code / Claude Desktop) │
│                                                 │
│  vault_query ─┐                                 │
│  vault_get  ──┤  MCP protocol (stdio)           │
│  vault_graph ─┤──────────────────────────────────┼──► scripts/vault/mcp_server.py
│  vault_skeleton┤                                │
│  vault_status ─┤                                │
│  cross_vault ──┤                                │
│  vault_observe ┘                                │
└─────────────────────────────────────────────────┘
         │                    │                 │
         ▼                    ▼                 ▼
    QMD (node)         SQLite graph      Vault files (*.md)
    hybrid search      wikilinks         direct read
    3 collections      backlinks         frontmatter
    local embeddings   observations      headings
```

### Data stores

| Store | Location | Purpose |
|---|---|---|
| QMD collections | `~/.local/share/qmd/` | Embedded document chunks for hybrid search |
| Wikilink graph | `~/.cache/vault-engine/graph.sqlite` | Pages, links, frontmatter, observations |
| Vault files | Read directly from disk | Full page content, resolved on demand |

### Vaults

| ID | Path | Contents |
|---|---|---|
| `tda` | `C:\Users\steph\Documents\TDA-Research` | Methodology, literature, paper project management, computational logs |
| `cl` | `C:\Users\steph\Documents\Counting Lives\Counting Lives` | Book manuscript, sources, interviews, research notes |

Paper drafts live in the code repository at `C:\Users\steph\TDL\papers\` — they
are **not** part of the QMD index. The vaults hold methodology, literature, and
project management; the repo holds code and paper drafts.

---

## Tools Reference

### vault_query

**Purpose:** Search across vaults with wikilink graph expansion.

Calls QMD for hybrid retrieval (BM25 + semantic + reranking), then
optionally expands the top results via the wikilink graph to include
related pages as skeletons.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | required | Natural language search query |
| `vault` | string | `None` | Restrict to `"tda"` or `"cl"`. `None` searches all |
| `max_results` | int | `5` | Number of primary results |
| `expand_links` | bool | `True` | Include 1-hop wikilink neighbors as skeletons |

**Returns:** Full content of matched pages, plus skeleton summaries of
linked neighbors. Each result shows vault, path, score, and content.

**Example:**
```
vault_query("Wasserstein distance methodology")
vault_query("chapter structure poverty", vault="cl", max_results=3)
vault_query("BHPS variable coding", expand_links=False)
```

**Note:** First call after server start is slow (~30s) while QMD loads
embedding models. Subsequent calls are fast (<2s).

---

### vault_get

**Purpose:** Read a specific vault page with its link context.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | string | required | Relative path or page stem |
| `vault` | string | `"tda"` | Which vault |
| `include_links` | bool | `True` | Show backlinks and forward links |
| `skeleton` | bool | `False` | Return skeleton instead of full content |

**Returns:** Page content (full or skeleton) with lists of forward links
and backlinks.

**Path resolution:** The `path` parameter is flexible:
- Page stem: `"CONVENTIONS"` → finds `CONVENTIONS.md` anywhere in the vault
- Relative path: `"03-Papers/P01-A/_project.md"` → exact file
- Without `.md`: `"03-Papers/P01-A/_project"` → adds `.md` automatically

**Example:**
```
vault_get("CONVENTIONS", vault="tda")
vault_get("03-Papers/P01-A/_project.md")
vault_get("Computational-Log", skeleton=True)
vault_get("Index", vault="cl", include_links=False)
```

---

### vault_graph

**Purpose:** Explore the wikilink neighborhood around a page.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | string | required | Page stem or relative path |
| `vault` | string | `"tda"` | Which vault |
| `depth` | int | `1` | Hops to traverse (1–3) |
| `format` | string | `"list"` | `"list"` or `"mermaid"` |

**Returns:** Graph summary showing nodes, edges, forward links, and backlinks.
With `format="mermaid"`, returns a Mermaid diagram that renders in Obsidian
or GitHub.

**Example:**
```
vault_graph("CONVENTIONS", vault="tda", depth=2)
vault_graph("Computational-Log", format="mermaid")
vault_graph("Index", vault="cl", depth=1)
```

---

### vault_skeleton

**Purpose:** Get token-efficient summaries of multiple pages in a single call.

Reduces each page to frontmatter + heading tree + first sentence per section.
Typically 80–90% fewer tokens than full content.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pages` | list[string] | required | Page stems or relative paths |
| `vault` | string | `"tda"` | Which vault |

**Returns:** Concatenated skeletons separated by `---`.

**Example:**
```
vault_skeleton(["CONVENTIONS", "Pipeline-Overview", "Computational-Log"])
vault_skeleton(["Index", "review-personas"], vault="cl")
```

**When to use:** Scanning multiple pages to decide which to read in full.
A 1400-word CONVENTIONS page becomes ~30 lines. Load 10 skeletons in a
single call without blowing your context window.

---

### vault_status

**Purpose:** Dashboard combining vault structure maps and health metrics.

Wraps two hardened scripts:
- `vault_map.py` — generates a structured overview of vault contents
  (paper pipeline status for TDA; manuscript structure for CL)
- `health_check.py` — scans for orphan notes, broken wikilinks, stale TODOs,
  unprocessed Perplexity captures, and index freshness

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `vault` | string | `None` | `"tda"`, `"cl"`, or `None` for both |
| `include_health` | bool | `True` | Run health check |

**Returns:** Vault map + health metrics table.

**Example:**
```
vault_status()                        # both vaults
vault_status(vault="tda")             # TDA only
vault_status(vault="cl", include_health=False)  # CL map, skip health
```

---

### cross_vault

**Purpose:** Detect shared concepts between the TDA-Research and Counting Lives
vaults.

Finds page stems that exist in both vaults and wikilink targets referenced from
both, indicating potential "Two Lenses" connections.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_overlap` | int | `2` | Minimum shared references to report |

**Returns:** Tables of shared page names and shared wikilink targets with
reference counts per vault.

**Example:**
```
cross_vault()
cross_vault(min_overlap=3)
```

---

### vault_observe

**Purpose:** Save an observation linked to a vault page for cross-session memory.

Observations are persisted in the SQLite database and surfaced when the linked
page appears in later query results. Staleness is automatically flagged if the
page has been modified since the observation was recorded.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `observation` | string | required | The insight or note to record |
| `page` | string | `None` | Page stem or path to link to |
| `vault` | string | `"tda"` | Which vault |

**Returns:** Confirmation with any previous observations for the same page
(including staleness warnings).

**Example:**
```
vault_observe("W2 audit confirmed all code paths use order=2", page="CONVENTIONS")
vault_observe("Chapter 3 needs poverty trap framing aligned with P01-A", page="Index", vault="cl")
```

---

## Recommended Workflows

### Session start

Load locked rules and check vault health before doing any work:

```
vault_get("CONVENTIONS", vault="tda")
vault_status(vault="tda")
```

### Paper work

Read the paper's project file before writing or modifying drafts:

```
vault_get("03-Papers/P01-A/_project.md")
```

Paper drafts themselves are in the code repo (`papers/P01-A-JRSSA/`, etc.)
and can be read with normal file tools.

### Methodology questions

Search the vault — results automatically expand via wikilinks:

```
vault_query("persistence landscape distance computation")
vault_query("Markov order selection Wasserstein")
```

### Scanning for context

When you need a broad overview without reading every page in full:

```
vault_skeleton(["CONVENTIONS", "Pipeline-Overview", "Computational-Log",
                "markov-memory-ladder", "_project"])
```

### After locking a decision

Record it as an observation and update the relevant vault page:

```
vault_observe("Lock n_components=50 for UMAP embedding", page="CONVENTIONS")
```

### Cross-project connections

Find concepts bridging the TDA research and Counting Lives book:

```
cross_vault()
```

---

## QMD Collections

Two collections are indexed:

| Collection | Source | Pages | Purpose |
|---|---|---|---|
| `tda` | TDA-Research vault | ~68 | Methodology, literature, paper management |
| `cl` | Counting Lives vault | ~236 | Book manuscript, sources, research |

Context annotations are attached to each collection so QMD can weight
results appropriately.

### Re-indexing

QMD embeddings are generated once and updated incrementally. If vault content
changes significantly (new pages, restructured folders), re-index:

```bash
qmd embed -c tda
qmd embed -c cl
```

The wikilink graph (SQLite) rebuilds automatically when any `.md` file in
either vault has a newer modification time than the last build.

### Manual search (CLI)

QMD can also be used directly from the command line:

```bash
qmd search "Wasserstein distance" -c tda -n 5     # BM25 only
qmd query "poverty trap detection" -c cl -n 3      # hybrid (BM25 + vector)
qmd query "BHPS variable coding" --json -n 5       # JSON output
```

---

## Configuration

### VS Code Copilot (`.vscode/mcp.json`)

The workspace MCP config lives at `.vscode/mcp.json` (not the root `.mcp.json`).
It uses the `"servers"` key, matching VS Code's native schema.

```json
{
  "servers": {
    "vault-engine": {
      "type": "stdio",
      "command": "python",
      "args": [
        "C:\\Users\\steph\\TDL\\scripts\\vault\\mcp_server.py"
      ],
      "env": {
        "TDA_VAULT_PATH": "C:\\Users\\steph\\Documents\\TDA-Research",
        "CL_VAULT_PATH": "C:\\Users\\steph\\Documents\\Counting Lives\\Counting Lives",
        "LLAMA_CUDA": "0",
        "NODE_LLAMA_CPP_GPU": "false"
      }
    }
  }
}
```

### Claude Code (`.mcp.json`)

Claude Code reads from the root `.mcp.json` with the `"mcpServers"` key.

```json
{
  "mcpServers": {
    "vault-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["C:\\Users\\steph\\TDL\\scripts\\vault\\mcp_server.py"],
      "env": {
        "TDA_VAULT_PATH": "C:\\Users\\steph\\Documents\\TDA-Research",
        "CL_VAULT_PATH": "C:\\Users\\steph\\Documents\\Counting Lives\\Counting Lives",
        "LLAMA_CUDA": "0",
        "NODE_LLAMA_CPP_GPU": "false"
      }
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "vault-engine": {
      "command": "C:\\Users\\steph\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["C:\\Users\\steph\\TDL\\scripts\\vault\\mcp_server.py"],
      "env": {
        "TDA_VAULT_PATH": "C:\\Users\\steph\\Documents\\TDA-Research",
        "CL_VAULT_PATH": "C:\\Users\\steph\\Documents\\Counting Lives\\Counting Lives",
        "LLAMA_CUDA": "0",
        "NODE_LLAMA_CPP_GPU": "false"
      }
    }
  }
}
```

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `TDA_VAULT_PATH` | TDA-Research vault root | `C:\Users\steph\Documents\TDA-Research` |
| `CL_VAULT_PATH` | Counting Lives vault root | `C:\Users\steph\Documents\Counting Lives\Counting Lives` |
| `VAULT_ENGINE_DB` | SQLite database path | `~/.cache/vault-engine/graph.sqlite` |
| `LLAMA_CUDA` | Set to `0` to force CPU-only embeddings | — |
| `NODE_LLAMA_CPP_GPU` | Set to `false` to force CPU-only embeddings | — |

---

## Dependencies

### System

- **Node.js** ≥ 22 — required to run QMD via `node`
- **Python** 3.13 — project runtime

### Python packages

- `mcp[cli]` — MCP SDK (`pip install "mcp[cli]"`)

### Node packages

- `@tobilu/qmd` — installed globally (`npm install -g @tobilu/qmd`)
- QMD entry point: `node ~/AppData/Roaming/npm/node_modules/@tobilu/qmd/dist/cli/qmd.js`

### Vault scripts (bundled)

- `scripts/vault/health_check.py` — orphan detection, broken-link scanning, TODO staleness
- `scripts/vault/vault_map.py` — vault structure maps (TDA paper pipeline, CL manuscript structure)

---

## Troubleshooting

### "No results found" from vault_query

1. Check QMD is installed: `qmd --version` (should print `qmd 2.1.0` or later)
2. Check collections exist: `qmd collections`
3. Re-embed if needed: `qmd embed -c tda && qmd embed -c cl`
4. Check the vault path env vars are set correctly

### Slow first query

Normal. QMD loads embedding models on first use (~30s). Subsequent queries
are fast. The CUDA env vars are set to force CPU mode because
`node-llama-cpp` CUDA bindings have compatibility issues on some systems.

### Wikilink graph not updating

The graph rebuilds when any `.md` file has a newer mtime than the last build.
Force a rebuild by deleting the SQLite database:

```bash
rm ~/.cache/vault-engine/graph.sqlite
```

### MCP server not appearing in agent tools

- **VS Code Copilot:** Check `.vscode/mcp.json` (uses `"servers"` key, not
  `"mcpServers"`). Reload window after changes.
- **Claude Code:** Check `.mcp.json` in the project root. Restart the session.
- **Claude Desktop:** Check `~/AppData/Roaming/Claude/claude_desktop_config.json`.
  Restart Claude Desktop.

### Page not found errors

`vault_get` resolves pages in this order:
1. Exact relative path (e.g. `03-Papers/P01-A/_project.md`)
2. Relative path with `.md` appended
3. Stem search (finds any `*.md` file with matching stem anywhere in the vault)

If a page has a non-unique stem (e.g. multiple `_project.md` files), use the
full relative path.

---

## File layout

```
scripts/vault/
├── mcp_server.py      ← MCP server (7 tools, QMD integration, wikilink graph)
├── health_check.py    ← Vault health scanning (imported by mcp_server)
├── vault_map.py       ← Vault structure maps (imported by mcp_server)
└── __pycache__/

~/.cache/vault-engine/
└── graph.sqlite       ← Wikilink graph + observations + metadata

~/.local/share/qmd/    ← QMD collections + embeddings (managed by QMD)
```
