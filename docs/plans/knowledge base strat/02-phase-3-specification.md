# Phase 3: Advanced Integration Specification

> These build on the Phase 1 and 2 foundations. Each section describes the
> concept, how it maps onto the existing setup, concrete implementation
> steps, and dependencies. Nothing here is urgent — these are the
> capabilities that become valuable as the vaults grow and the workflow
> matures.

---

## 3.1 Ephemeral Research Contexts ("Mini-Knowledge-Bases")

### Concept

Lex Fridman described generating temporary focused knowledge bases from a
larger corpus — extracting just the notes relevant to a specific question,
loading them into a fresh context, and doing deep Q&A. When the question is
answered, the output gets filed back and the ephemeral context dissolves.

### Your version

You already have the building blocks. A focused research context for your
setup would be:

1. **Specify the question** — e.g., "How does the Markov memory ladder
   framework relate to existing work on regime detection in financial time
   series?"

2. **Extract the relevant subset** — the session skill reads VAULT-MAP.md,
   identifies relevant notes (P01 methodology, FIN-01 project file, any
   permanent notes on Markov models, literature notes on regime detection),
   and assembles them into a temporary focused context.

3. **Deep Q&A** — with only the relevant material loaded, the LLM can
   reason over the full content without the noise of the broader vault.

4. **File back** — any synthesis produced gets captured via session-capture
   and the relevant VAULT-MAP entries get updated.

### Implementation

**New skill: `focused-context`**

```
Triggers: "focus on", "deep dive into", "research context for",
          "pull together everything on", "mini knowledge base"

Steps:
1. Parse the research question
2. Read VAULT-MAP.md to identify candidate notes
3. Read the identified notes (aim for 10-20 notes, ~50K tokens)
4. Present the assembled context as a brief:
   "I've pulled together [n] notes covering [topics]. Ready to go deep."
5. Enter focused Q&A mode — answers draw only from loaded material
6. At close, offer session-capture for any synthesis produced
```

**Key constraint:** The ephemeral context must be bounded. Loading the
entire vault defeats the purpose. VAULT-MAP.md is the navigation layer
that makes selective loading possible — this is why the index must be
current.

### Dependencies
- VAULT-MAP.md must exist and be current (Phase 1)
- Session-capture skill must be installed (Phase 1)

---

## 3.2 Cross-Vault Linker

### Concept

Systematic identification of concepts that appear in both vaults but
aren't explicitly connected. This is the foundation for the Two Lenses
UI pattern on the website — every concept that can be read both
mathematically (TDA vault) and politically (CL vault) is a candidate
for a learning path toggle.

### Implementation

**New skill: `cross-vault-linker`**

```
Triggers: "cross-vault", "find connections", "two lenses scan",
          "link the vaults", "bridge the projects"

Steps:
1. Load both VAULT-MAP.md files
2. Extract concept terms from each:
   - TDA: paper topics, method names, dataset names, MOC headings
   - CL: chapter titles, theoretical anchors, key figures, institutions
3. Find overlapping concepts:
   - Exact matches (same term in both vaults)
   - Semantic matches (e.g., "poverty measurement" in CL ↔
     "socioeconomic trajectory embedding" in TDA)
   - Shared Zotero citekeys (same source cited in both vaults)
4. For each connection found:
   - Check whether an explicit link already exists
   - If not, propose a connection with a brief rationale
5. Output:
   - Updated cross-vault tables in both VAULT-MAP.md files
   - A connections report listing new and existing links
   - Candidates for Two Lenses tagging on the website
```

### Two Lenses tagging format

When a cross-vault connection is confirmed, tag the relevant notes in
both vaults with frontmatter:

```yaml
two-lenses:
  mathematical: "04-Methods/persistent-homology-overview.md"  # TDA vault
  political: "01 - Manuscript/Part IV/Ch17/sections/ethics-of-ph.md"  # CL vault
  website-path: "learning/topology-and-justice"  # proposed URL slug
```

This metadata can be consumed by the Astro build to generate the Two
Lenses toggle components.

### Dependencies
- Both VAULT-MAP.md files current
- Access to both vaults in the same session (or sequential runs)

---

## 3.3 Website Content Pipeline

### Concept

The zktheory.org website should be fed by vault content at build time,
not maintained as a separate copy. The PRD already specs Zotero
integration via the Web API v3. This extends the pattern to vault
content more broadly.

### Data flow

```
Obsidian vaults                    Astro build
┌──────────────┐                  ┌──────────────────┐
│ VAULT-MAP.md │──── export ────→ │ content/          │
│ Two Lenses   │                  │   papers.json     │
│   tags       │                  │   chapters.json   │
│ MM Interludes│                  │   learning-paths/ │
└──────────────┘                  │   two-lenses/     │
                                  └──────────────────┘
┌──────────────┐                  ┌──────────────────┐
│ Zotero       │──── Web API ───→ │ content/          │
│ library      │    (at build)    │   bibliography/   │
└──────────────┘                  └──────────────────┘
```

### Implementation steps

1. **Export script** (Python or Node) that reads VAULT-MAP.md files and
   Two Lenses tags, then generates JSON content files for Astro's content
   collections:
   - `papers.json` — paper pipeline status, abstracts, methodology summaries
   - `chapters.json` — chapter summaries, status, key themes
   - `learning-paths.json` — assembled from Two Lenses tags + MM Interludes

2. **Astro content collections** that consume these JSON files, alongside
   the Zotero bibliography data already specced in the PRD.

3. **Build-time validation** — the build script checks that every Two Lenses
   tag references notes that actually exist in the vaults, and that every
   learning path has sufficient content to render.

### Hardening opportunity (Principle 1)

The export script is a deterministic transformation — it reads structured
markdown and produces JSON. This is exactly the kind of step that should
be hardened into a script rather than done by the LLM each time. Write it
once, test it, and run it as part of the Astro build pipeline.

```bash
# In the website project's package.json
"scripts": {
  "prebuild": "node scripts/export-vault-content.js",
  "build": "astro build"
}
```

### Dependencies
- Two Lenses tagging in place (from cross-vault linker)
- VAULT-MAP.md files current
- Zotero Web API integration (already specced in PRD)
- Astro content collections configured

---

## 3.4 Hardened Scripts (Principle 1 Implementation)

### Concept

The Hardening Principle says: use the LLM to prototype, then replace
deterministic steps with scripts that run identically every time.
Several operations in the current workflow are candidates.

### Candidates for hardening

| Operation | Currently | Harden to | Priority |
|---|---|---|---|
| VAULT-MAP.md regeneration | LLM reads dirs, writes markdown | Python script that scans vault structure | High |
| Health check: orphan detection | LLM scans for backlinks | Python script using regex on `[[wikilinks]]` | High |
| Health check: stale TODO scan | LLM reads files for `- [ ]` | Python script with age threshold | High |
| Perplexity capture: source table | LLM extracts and formats | Partially — extraction is fuzzy, but table format is deterministic | Medium |
| Export vault content for website | LLM reads + transforms | Node/Python script (see 3.3) | High |
| Index freshness check | LLM compares dir listing vs index | Python script returning diff | Medium |

### Implementation pattern

For each hardened script:

1. **Prototype with the LLM** — have a session where the LLM performs
   the operation manually
2. **Extract the deterministic logic** — what parts always work the same way?
3. **Write a Python script** in a `scripts/` folder in the vault or
   in the TDL repo
4. **Test against the actual vault** — run the script and compare output
   to what the LLM produced
5. **Wire into the skill** — the skill calls the script for the
   deterministic part and uses the LLM only for interpretation and
   presentation

```python
# Example: scripts/vault_map.py
# Hardened VAULT-MAP.md generator for TDA-Research

import os
import re
from pathlib import Path
from datetime import datetime

# Files excluded from orphan detection (always-present index/nav files)
EXCLUDED_FILES: set[str] = {"INDEX", "VAULT-MAP", "README"}

def scan_papers(vault_root: Path) -> list[dict]:
    """Read all _project.md files and extract status."""
    papers_dir = vault_root / "03-Papers"
    papers = []
    for project_file in papers_dir.rglob("_project.md"):
        content = project_file.read_text(encoding="utf-8")
        # Extract structured fields...
        papers.append({
            "id": project_file.parent.name,
            "status": extract_status(content),
            "open_items": count_open_items(content),
            "last_modified": datetime.fromtimestamp(
                project_file.stat().st_mtime
            )
        })
    return papers

def find_orphans(vault_root: Path) -> list[str]:
    """Find .md files not referenced by any [[wikilink]]."""
    all_files = {f.stem for f in vault_root.rglob("*.md")}
    all_links = set()
    for md_file in vault_root.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        all_links.update(re.findall(r'\[\[([^\]|]+)', content))
    return sorted(all_files - all_links - EXCLUDED_FILES)

def count_stale_todos(vault_root: Path, days: int = 14) -> list[dict]:
    """Find unchecked TODOs in files not modified for N days."""
    cutoff = datetime.now().timestamp() - (days * 86400)
    stale = []
    for md_file in vault_root.rglob("*.md"):
        if md_file.stat().st_mtime < cutoff:
            content = md_file.read_text(encoding="utf-8")
            todos = re.findall(r'- \[ \] (.+)', content)
            if todos:
                stale.append({
                    "file": str(md_file.relative_to(vault_root)),
                    "todos": todos,
                    "last_modified": datetime.fromtimestamp(
                        md_file.stat().st_mtime
                    )
                })
    return stale
```

### Where scripts live

```
C:\Projects\TDL\
└── scripts\
    └── vault\
        ├── vault_map.py        — VAULT-MAP.md regeneration
        ├── health_check.py     — orphans, stale TODOs, broken links
        ├── index_freshness.py  — compare INDEX.md vs directory contents
        └── export_for_web.py   — export vault content for Astro build
```

These scripts can be called from Cowork skills via bash, or run
independently from the command line. The skill provides the
interpretation layer; the script provides the reliable data.

---

## 3.5 Zotero MCP Integration

### Current state

You've been configuring the Zotero MCP server for use with Claude Desktop
on Windows. The vault workflows already use Zotero as the citation source
of truth, with the `@citekey` format in prose and the Zotero Integration
plugin for importing literature notes.

### How it fits the knowledge base architecture

The Zotero MCP server can serve as an additional data source for several
existing workflows:

1. **Health check: Zotero alignment** — query the Zotero library via MCP
   to verify that every `@citekey` in the vaults resolves to an actual
   Zotero entry. Currently the health check can only look at local files;
   with MCP it can cross-reference against the live library.

2. **Perplexity capture: auto-suggest identifiers** — when processing a
   Perplexity capture, use the Zotero MCP to search for claimed sources.
   If a DOI or title match is found in the existing library, flag it as
   "already in Zotero" and skip the verification step for that source.

3. **Literature note generation** — instead of manually importing via the
   Zotero Integration plugin, a skill could read the Zotero entry via MCP
   and generate the literature note directly, following the vault's template.

4. **Website bibliography** — the Zotero Web API v3 integration specced in
   the PRD could be supplemented by MCP queries during development, ensuring
   the build-time export matches the live library.

### Implementation notes

The Zotero MCP server exposes tools for searching, reading, and annotating
items. The key tools for this workflow are:

- `zotero_search_items` — find items by query string
- `zotero_get_item_metadata` — get full metadata for a specific item
- `zotero_search_by_tag` — find items tagged for specific papers
- `zotero_get_annotations` — retrieve annotations for deep reading

To integrate with existing skills, the pattern is:
1. Skill performs its normal vault-based logic
2. At the Zotero checkpoint, skill queries MCP for verification
3. Results are incorporated into the output (health report, capture note, etc.)

This requires that the Zotero MCP server is running during the session.
Skills should degrade gracefully if it's not available — vault-only
operations should still work, with a note that Zotero cross-referencing
was skipped.

---

## 3.6 Claude Code and Tooling Considerations

### jig (session profiles)

The `jig` tool from Forsythe's 10 Principles creates session profiles that
declare which tools, MCP servers, and skills activate per project. This maps
directly onto your two-project setup:

```yaml
# .jig/tda-research.yaml
name: tda-research
tools:
  - zotero-mcp
  - github-copilot
skills:
  - tda-session
  - tda-perplexity-capture
  - tda-repo-bridge
  - session-capture
  - vault-health-check
context:
  - CONVENTIONS.md
  - VAULT-MAP.md
```

```yaml
# .jig/counting-lives.yaml
name: counting-lives
tools:
  - zotero-mcp
skills:
  - chapter-session
  - perplexity-capture
  - counting-lives-humanizer
  - session-capture
  - vault-health-check
context:
  - CONVENTIONS.md
  - VAULT-MAP.md
```

This is the Context Hygiene Principle applied at the session level — each
project loads only what it needs, avoiding context pollution from the other
project's concerns.

If you adopt Claude Code for any part of the workflow (e.g., working on
the website codebase or the TDL Python repo), jig would manage which
context loads for each project. For Cowork sessions, the same principle
applies through which skills are attached to each project.

### Forge (specialist agent teams)

Forge assembles specialist agent teams from a goal description. For your
use case, it would be most relevant for:

- **Paper review:** Assemble a review panel from the personas file, run
  each reviewer, and synthesise findings
- **Website implementation:** Assemble a team for a blueprint (frontend
  developer, accessibility reviewer, content strategist)

This is a future consideration — the review personas file provides the
raw material, and Forge would automate the orchestration.

---

## 3.7 Future: Synthetic Data and Fine-Tuning

Karpathy's longest-term vision: once the wiki is large enough, use it to
generate synthetic training data and fine-tune a smaller model that "knows"
the research in its weights rather than through context windows.

For your setup, this becomes interesting when:
- The combined vaults exceed ~500K words (beyond comfortable context windows)
- You want a model that understands TDA methodology AND the book's
  historical arguments without needing to load either vault
- You want the website's interactive components to use a model that has
  internalised the learning paths

This is premature now but worth designing toward. The structured vault
format, CONVENTIONS.md, and VAULT-MAP.md are all synthetic-data-friendly
— they're clean, structured, and represent verified knowledge. When the
time comes, the fine-tuning corpus is already being assembled.

---

## Phase 3 Priority Order

| Item | Dependency | Effort | Impact |
|---|---|---|---|
| 3.4 Hardened scripts (vault_map, health_check) | Phase 1 installed | Medium | High — reliability |
| 3.1 Ephemeral research contexts | VAULT-MAP current | Low | High — deep work |
| 3.5 Zotero MCP integration | MCP server configured | Medium | Medium — verification |
| 3.2 Cross-vault linker | Both VAULT-MAPs | Medium | High — Two Lenses |
| 3.3 Website content pipeline | Cross-vault links + PRD | High | High — but later |
| 3.6 Claude Code / jig profiles | Claude Code adopted | Low | Medium — context hygiene |
| 3.7 Synthetic data | Vaults at scale | High | Future |
